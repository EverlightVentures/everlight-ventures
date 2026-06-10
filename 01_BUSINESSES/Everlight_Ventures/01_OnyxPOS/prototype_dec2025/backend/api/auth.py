"""
Authentication API
- Tenant signup
- User login/logout
- JWT token management
- Google OAuth
"""
from flask import Blueprint, request, jsonify, g, redirect
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from models import Tenant, User
from database import Session
import re
import sys
import os
import requests
import secrets

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.email_service import EmailService

auth_bp = Blueprint("auth", __name__)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/v1/auth/google/callback")

# Temporary state storage (in production, use Redis)
oauth_states = {}


def is_valid_email(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def generate_subdomain(business_name):
    """Generate subdomain from business name"""
    # Remove special characters, convert to lowercase, replace spaces with hyphens
    subdomain = re.sub(r"[^a-z0-9-]", "", business_name.lower().replace(" ", "-"))
    # Remove consecutive hyphens
    subdomain = re.sub(r"-+", "-", subdomain)
    # Remove leading/trailing hyphens
    subdomain = subdomain.strip("-")
    return subdomain


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register new tenant and owner user
    Creates a business account with 14-day free trial
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ["business_name", "email", "password", "first_name", "last_name"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate email
        if not is_valid_email(data["email"]):
            return jsonify({"error": "Invalid email format"}), 400

        # Validate password strength
        if len(data["password"]) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400

        # Generate subdomain
        subdomain = data.get("subdomain") or generate_subdomain(data["business_name"])

        # Check if subdomain is already taken
        existing_tenant = g.db.query(Tenant).filter_by(subdomain=subdomain).first()
        if existing_tenant:
            return jsonify({"error": "Business name already taken. Please choose a different name."}), 409

        # Check if email is already registered
        existing_user = g.db.query(User).filter_by(email=data["email"]).first()
        if existing_user:
            return jsonify({"error": "Email already registered"}), 409

        # Create tenant with Core plan (14-day trial)
        tenant = Tenant(
            business_name=data["business_name"],
            subdomain=subdomain,
            owner_email=data["email"],
            plan_tier="core",  # Start with Core plan ($119/mo + platform fees)
            subscription_status="trial",
            trial_ends_at=datetime.utcnow() + timedelta(days=14)
        )
        g.db.add(tenant)
        g.db.flush()  # Get tenant ID

        # Create owner user
        owner = User(
            tenant_id=tenant.id,
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role="owner",
            is_active=True
        )
        owner.set_password(data["password"])
        g.db.add(owner)

        g.db.commit()

        # Send welcome email
        try:
            EmailService.send_welcome_email(
                to=owner.email,
                business_name=tenant.business_name,
                user_name=owner.full_name
            )
        except Exception as email_error:
            # Log error but don't fail registration
            print(f"Failed to send welcome email: {email_error}")

        # Create JWT tokens
        access_token = create_access_token(
            identity=owner.id,
            additional_claims={"tenant_id": tenant.id, "role": owner.role}
        )
        refresh_token = create_refresh_token(
            identity=owner.id,
            additional_claims={"tenant_id": tenant.id}
        )

        return jsonify({
            "message": "Registration successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": owner.id,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": owner.role
            },
            "tenant": {
                "id": tenant.id,
                "business_name": tenant.business_name,
                "subdomain": tenant.subdomain,
                "plan_tier": tenant.plan_tier,
                "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    User login - returns JWT tokens
    """
    try:
        data = request.json

        # Validate required fields
        if not data.get("email") or not data.get("password"):
            return jsonify({"error": "Email and password required"}), 400

        # Find user by email
        user = g.db.query(User).filter_by(email=data["email"]).first()

        if not user or not user.check_password(data["password"]):
            return jsonify({"error": "Invalid credentials"}), 401

        # Check if user is active
        if not user.is_active:
            return jsonify({"error": "Account deactivated. Contact support."}), 403

        # Get tenant
        tenant = g.db.query(Tenant).filter_by(id=user.tenant_id).first()

        # Check if tenant subscription is active
        if not tenant.is_active:
            return jsonify({
                "error": "Subscription inactive. Please update billing information.",
                "subscription_status": tenant.subscription_status
            }), 403

        # Update last login
        user.last_login_at = datetime.utcnow()
        g.db.commit()

        # Create JWT tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={"tenant_id": tenant.id, "role": user.role}
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims={"tenant_id": tenant.id}
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            },
            "tenant": {
                "id": tenant.id,
                "business_name": tenant.business_name,
                "subdomain": tenant.subdomain,
                "plan_tier": tenant.plan_tier,
                "subscription_status": tenant.subscription_status,
                "trial_days_remaining": tenant.trial_days_remaining if tenant.is_trial else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token
    """
    try:
        current_user_id = get_jwt_identity()
        jwt_data = get_jwt()

        # Create new access token
        access_token = create_access_token(
            identity=current_user_id,
            additional_claims={
                "tenant_id": jwt_data.get("tenant_id"),
                "role": jwt_data.get("role")
            }
        )

        return jsonify({
            "access_token": access_token
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Get current user profile
    """
    try:
        user_id = get_jwt_identity()
        user = g.db.query(User).filter_by(id=user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        tenant = g.db.query(Tenant).filter_by(id=user.tenant_id).first()

        return jsonify({
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "role": user.role,
                "phone": user.phone
            },
            "tenant": {
                "id": tenant.id,
                "business_name": tenant.business_name,
                "subdomain": tenant.subdomain,
                "plan_tier": tenant.plan_tier,
                "subscription_status": tenant.subscription_status
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============= GOOGLE OAUTH =============

@auth_bp.route("/google", methods=["GET"])
def google_oauth_init():
    """
    Initiate Google OAuth flow

    Query params:
    - mode: 'signup' or 'login' (default: login)
    """
    try:
        if not GOOGLE_CLIENT_ID:
            return jsonify({"error": "Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable."}), 500

        # Generate state token
        state = secrets.token_urlsafe(32)
        mode = request.args.get("mode", "login")

        # Store state temporarily (in production, use Redis with expiry)
        oauth_states[state] = {
            "mode": mode,
            "created_at": datetime.utcnow().isoformat()
        }

        # Build Google OAuth URL
        google_oauth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            "response_type=code&"
            "scope=openid email profile&"
            f"state={state}&"
            "access_type=offline&"
            "prompt=consent"
        )

        return jsonify({
            "auth_url": google_oauth_url,
            "state": state
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/google/callback", methods=["GET"])
def google_oauth_callback():
    """Handle Google OAuth callback"""
    try:
        # Get authorization code and state
        code = request.args.get("code")
        state = request.args.get("state")
        error_param = request.args.get("error")

        if error_param:
            return jsonify({"error": f"Google OAuth error: {error_param}"}), 400

        if not code or not state:
            return jsonify({"error": "Missing code or state"}), 400

        # Verify state
        if state not in oauth_states:
            return jsonify({"error": "Invalid state token"}), 400

        mode = oauth_states[state]["mode"]
        del oauth_states[state]  # Clean up

        # Exchange code for tokens
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            return jsonify({"error": "Failed to exchange code for token", "details": token_response.text}), 500

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info from Google
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_info_response.status_code != 200:
            return jsonify({"error": "Failed to get user info"}), 500

        user_info = user_info_response.json()
        google_email = user_info.get("email")
        given_name = user_info.get("given_name", "")
        family_name = user_info.get("family_name", "")

        if not google_email:
            return jsonify({"error": "Email not provided by Google"}), 400

        if mode == "signup":
            # Check if user already exists
            existing_user = g.db.query(User).filter_by(email=google_email).first()
            if existing_user:
                return jsonify({"error": "Email already registered. Please login instead."}), 409

            # Extract business name from name
            business_name = f"{given_name}'s Business"

            # Generate subdomain
            subdomain = generate_subdomain(business_name)
            existing_tenant = g.db.query(Tenant).filter_by(subdomain=subdomain).first()
            counter = 1
            while existing_tenant:
                subdomain = f"{generate_subdomain(business_name)}{counter}"
                existing_tenant = g.db.query(Tenant).filter_by(subdomain=subdomain).first()
                counter += 1

            # Create tenant
            tenant = Tenant(
                business_name=business_name,
                subdomain=subdomain,
                owner_email=google_email,
                plan_tier="core",
                subscription_status="trial",
                trial_ends_at=datetime.utcnow() + timedelta(days=14)
            )
            g.db.add(tenant)
            g.db.flush()

            # Create owner user
            owner = User(
                tenant_id=tenant.id,
                email=google_email,
                first_name=given_name,
                last_name=family_name,
                role="owner",
                is_active=True
            )
            owner.set_password(secrets.token_urlsafe(32))  # Random password

            g.db.add(owner)
            g.db.commit()

            # Create JWT tokens
            jwt_access_token = create_access_token(
                identity=owner.id,
                additional_claims={"tenant_id": tenant.id, "role": owner.role}
            )
            jwt_refresh_token = create_refresh_token(
                identity=owner.id,
                additional_claims={"tenant_id": tenant.id}
            )

            return jsonify({
                "message": "Registration successful via Google",
                "access_token": jwt_access_token,
                "refresh_token": jwt_refresh_token,
                "user": {
                    "id": owner.id,
                    "email": owner.email,
                    "full_name": owner.full_name,
                    "role": owner.role
                },
                "tenant": {
                    "id": tenant.id,
                    "business_name": tenant.business_name,
                    "subdomain": tenant.subdomain,
                    "plan_tier": tenant.plan_tier
                }
            }), 201

        else:  # mode == "login"
            user = g.db.query(User).filter_by(email=google_email).first()

            if not user:
                return jsonify({"error": "No account found. Please sign up first."}), 404

            if not user.is_active:
                return jsonify({"error": "Account deactivated"}), 403

            tenant = g.db.query(Tenant).filter_by(id=user.tenant_id).first()

            if not tenant.is_active:
                return jsonify({"error": "Subscription inactive"}), 403

            user.last_login_at = datetime.utcnow()
            g.db.commit()

            jwt_access_token = create_access_token(
                identity=user.id,
                additional_claims={"tenant_id": tenant.id, "role": user.role}
            )
            jwt_refresh_token = create_refresh_token(
                identity=user.id,
                additional_claims={"tenant_id": tenant.id}
            )

            return jsonify({
                "message": "Login successful via Google",
                "access_token": jwt_access_token,
                "refresh_token": jwt_refresh_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                },
                "tenant": {
                    "id": tenant.id,
                    "business_name": tenant.business_name,
                    "plan_tier": tenant.plan_tier
                }
            }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500
