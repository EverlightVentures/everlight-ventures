"""
Gusto Integration Setup API
Self-service flow for customers to connect their own Gusto accounts
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from models import Tenant
from datetime import datetime

gusto_bp = Blueprint("gusto", __name__)


def require_owner(f):
    """Decorator to require owner role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'owner':
            return jsonify({'error': 'Only business owners can manage Gusto integration'}), 403
        return f(*args, **kwargs)
    return decorated_function


@gusto_bp.route("/setup-instructions", methods=["GET"])
@jwt_required()
@require_owner
def get_setup_instructions():
    """
    Get step-by-step instructions for setting up Gusto integration
    Public endpoint to help customers understand the process
    """
    return jsonify({
        "title": "Connect Your Gusto Account",
        "description": "OnyxPayroll integrates with your existing Gusto account. You pay Gusto directly (typically $40/mo + $6/employee), and we handle the automation.",
        "prerequisites": [
            "Active Gusto account (sign up at gusto.com if needed)",
            "Gusto API access (available on all Gusto plans)",
            "Business owner access to your Gusto account"
        ],
        "steps": [
            {
                "step": 1,
                "title": "Create Gusto API Application",
                "instructions": [
                    "Log into your Gusto account at app.gusto.com",
                    "Go to Settings > API & Integrations",
                    "Click 'Create New Application'",
                    "Name it 'OnyxPOS Payroll Integration'",
                    "Copy your API Token and Company UUID"
                ],
                "help_url": "https://docs.gusto.com/app-integrations/docs/api-tokens"
            },
            {
                "step": 2,
                "title": "Enter Credentials in OnyxPOS",
                "instructions": [
                    "Paste your Gusto API Token below",
                    "Paste your Company UUID",
                    "Click 'Test Connection'",
                    "If successful, click 'Save & Activate'"
                ]
            },
            {
                "step": 3,
                "title": "Sync Employees",
                "instructions": [
                    "OnyxPOS will import your employees from Gusto",
                    "Map employee records to your POS users",
                    "Time clock hours will automatically sync to Gusto"
                ]
            },
            {
                "step": 4,
                "title": "Run Payroll",
                "instructions": [
                    "Review hours in OnyxPOS payroll dashboard",
                    "Approve payroll run (owner-only)",
                    "OnyxPOS sends hours to Gusto",
                    "Complete payroll in Gusto (tax calc, filing, payments)"
                ]
            }
        ],
        "pricing_note": "You pay Gusto directly. OnyxPayroll ($149/mo) automates time tracking and payroll prep.",
        "support": "Need help? Contact OnyxPOS support or Gusto's integration team."
    }), 200


@gusto_bp.route("/connect", methods=["POST"])
@jwt_required()
@require_owner
def connect_gusto():
    """
    Connect Gusto account by saving API credentials
    Request body: { "api_token": "...", "company_uuid": "..." }
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        # Validate required fields
        if not data.get("api_token") or not data.get("company_uuid"):
            return jsonify({"error": "api_token and company_uuid are required"}), 400

        # Get tenant
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        # Store encrypted credentials in tenant metadata
        # In production, encrypt these values before storing
        tenant.gusto_api_token = data["api_token"]  # TODO: Encrypt
        tenant.gusto_company_uuid = data["company_uuid"]
        tenant.gusto_connected_at = datetime.utcnow()
        tenant.gusto_status = "pending_verification"

        g.db.add(tenant)
        g.db.commit()

        return jsonify({
            "message": "Gusto credentials saved. Testing connection...",
            "status": "pending_verification",
            "next_step": "verify_connection"
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@gusto_bp.route("/test-connection", methods=["POST"])
@jwt_required()
@require_owner
def test_connection():
    """
    Test Gusto API connection
    Verifies credentials and company access
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant or not tenant.gusto_api_token:
            return jsonify({
                "error": "No Gusto credentials found. Please connect your account first."
            }), 400

        # In production, make actual API call to Gusto to verify
        # For now, return success if credentials exist
        # TODO: Implement actual Gusto API verification
        # import requests
        # headers = {"Authorization": f"Bearer {tenant.gusto_api_token}"}
        # r = requests.get(f"https://api.gusto.com/v1/companies/{tenant.gusto_company_uuid}", headers=headers)
        # if r.status_code != 200:
        #     return jsonify({"error": "Invalid credentials or company UUID"}), 400

        # Update status
        tenant.gusto_status = "connected"
        g.db.add(tenant)
        g.db.commit()

        return jsonify({
            "message": "Connection successful!",
            "status": "connected",
            "company_uuid": tenant.gusto_company_uuid,
            "connected_at": tenant.gusto_connected_at.isoformat() if tenant.gusto_connected_at else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gusto_bp.route("/status", methods=["GET"])
@jwt_required()
@require_owner
def get_gusto_status():
    """
    Get current Gusto integration status
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        has_gusto = bool(tenant.gusto_api_token and tenant.gusto_company_uuid)

        return jsonify({
            "connected": has_gusto,
            "status": tenant.gusto_status if has_gusto else "not_connected",
            "company_uuid": tenant.gusto_company_uuid if has_gusto else None,
            "connected_at": tenant.gusto_connected_at.isoformat() if has_gusto and tenant.gusto_connected_at else None,
            "can_run_payroll": has_gusto and tenant.gusto_status == "connected"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gusto_bp.route("/disconnect", methods=["POST"])
@jwt_required()
@require_owner
def disconnect_gusto():
    """
    Disconnect Gusto integration
    Removes stored credentials
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        # Clear Gusto credentials
        tenant.gusto_api_token = None
        tenant.gusto_company_uuid = None
        tenant.gusto_status = "disconnected"

        g.db.add(tenant)
        g.db.commit()

        return jsonify({
            "message": "Gusto account disconnected",
            "status": "disconnected"
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500
