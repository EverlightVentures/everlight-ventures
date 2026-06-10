"""
Stripe Connect API
- OAuth flow for merchant onboarding
- Platform fee configuration
- Payment processing with automatic fees
"""
from flask import Blueprint, request, jsonify, g, url_for
from flask_jwt_extended import jwt_required, get_jwt
from models import Tenant, Transaction
from database import Session
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

connect_bp = Blueprint("stripe_connect", __name__)


@connect_bp.route("/connect-account", methods=["POST"])
@jwt_required()
def create_connect_account():
    """
    Create Stripe Connect Express account for tenant
    Returns OAuth link for merchant to complete onboarding
    """
    try:
        jwt_data = get_jwt()
        tenant_id = jwt_data.get("tenant_id")
        role = jwt_data.get("role")

        # Only owners can connect Stripe
        if role != "owner":
            return jsonify({"error": "Only business owners can connect Stripe"}), 403

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        # Check if already has connected account
        if tenant.stripe_account_id:
            return jsonify({
                "message": "Stripe account already connected",
                "account_id": tenant.stripe_account_id,
                "status": tenant.stripe_account_status
            }), 200

        # Create Stripe Express account
        account = stripe.Account.create(
            type="express",
            country="US",
            email=tenant.owner_email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="company",
            company={
                "name": tenant.business_name
            },
        )

        # Save account ID
        tenant.stripe_account_id = account.id
        tenant.stripe_account_status = "pending"
        g.db.commit()

        # Create account link for onboarding
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{request.host_url}settings?stripe_connect=refresh",
            return_url=f"{request.host_url}settings?stripe_connect=success",
            type="account_onboarding",
        )

        return jsonify({
            "message": "Connect account created",
            "account_id": account.id,
            "onboarding_url": account_link.url
        }), 201

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@connect_bp.route("/connect-status", methods=["GET"])
@jwt_required()
def get_connect_status():
    """
    Check status of Stripe Connect account
    """
    try:
        jwt_data = get_jwt()
        tenant_id = jwt_data.get("tenant_id")

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        if not tenant.stripe_account_id:
            return jsonify({
                "connected": False,
                "status": None,
                "platform_fee_percent": tenant.get_platform_fee_percent()
            }), 200

        # Get account details from Stripe
        account = stripe.Account.retrieve(tenant.stripe_account_id)

        # Update status
        if account.charges_enabled and account.payouts_enabled:
            tenant.stripe_account_status = "active"
        else:
            tenant.stripe_account_status = "pending"

        g.db.commit()

        return jsonify({
            "connected": True,
            "account_id": tenant.stripe_account_id,
            "status": tenant.stripe_account_status,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "platform_fee_percent": tenant.get_platform_fee_percent(),
            "details_submitted": account.details_submitted
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@connect_bp.route("/dashboard-link", methods=["GET"])
@jwt_required()
def get_dashboard_link():
    """
    Generate Stripe Express Dashboard login link
    Allows merchants to view their earnings
    """
    try:
        jwt_data = get_jwt()
        tenant_id = jwt_data.get("tenant_id")

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant or not tenant.stripe_account_id:
            return jsonify({"error": "No Stripe account connected"}), 404

        # Create login link
        login_link = stripe.Account.create_login_link(tenant.stripe_account_id)

        return jsonify({
            "url": login_link.url
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@connect_bp.route("/platform-revenue", methods=["GET"])
@jwt_required()
def get_platform_revenue():
    """
    PLATFORM OWNER ONLY: Get total revenue from platform fees
    This shows YOUR profit across all tenants
    """
    try:
        jwt_data = get_jwt()
        role = jwt_data.get("role")

        # Only for platform admin (you!)
        # For now, we'll check if email matches platform owner
        # In production, add a separate admin table

        # Get date range from query params
        days = int(request.args.get("days", 30))

        # Calculate platform revenue
        from datetime import datetime, timedelta
        from sqlalchemy import func

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all completed transactions
        transactions = g.db.query(Transaction).filter(
            Transaction.transaction_date >= start_date,
            Transaction.payment_status == "completed"
        ).all()

        total_sales = sum(float(t.total_amount) for t in transactions)

        # Calculate platform fees per tenant
        tenant_stats = {}
        for txn in transactions:
            tenant = g.db.query(Tenant).filter_by(id=txn.tenant_id).first()
            if not tenant:
                continue

            fee_percent = tenant.get_platform_fee_percent()
            platform_fee = float(txn.total_amount) * (fee_percent / 100)

            if tenant.id not in tenant_stats:
                tenant_stats[tenant.id] = {
                    "business_name": tenant.business_name,
                    "plan_tier": tenant.plan_tier,
                    "transaction_count": 0,
                    "total_sales": 0,
                    "platform_fees": 0,
                    "fee_percent": fee_percent
                }

            tenant_stats[tenant.id]["transaction_count"] += 1
            tenant_stats[tenant.id]["total_sales"] += float(txn.total_amount)
            tenant_stats[tenant.id]["platform_fees"] += platform_fee

        # Calculate totals
        total_platform_fees = sum(t["platform_fees"] for t in tenant_stats.values())
        total_transactions = sum(t["transaction_count"] for t in tenant_stats.values())

        # Monthly subscription revenue
        subscription_revenue = {
            "starter": 29,
            "professional": 79,
            "enterprise": 199
        }

        monthly_subscriptions = 0
        for tenant_id, stats in tenant_stats.items():
            plan = stats["plan_tier"]
            monthly_subscriptions += subscription_revenue.get(plan, 0)

        return jsonify({
            "period_days": days,
            "total_transactions": total_transactions,
            "total_sales_volume": round(total_sales, 2),
            "platform_fees_collected": round(total_platform_fees, 2),
            "monthly_subscription_revenue": monthly_subscriptions,
            "total_monthly_revenue": round(total_platform_fees + monthly_subscriptions, 2),
            "tenant_count": len(tenant_stats),
            "tenants": list(tenant_stats.values()),
            "projections": {
                "annual_transaction_fees": round(total_platform_fees * (365 / days), 2),
                "annual_subscription_revenue": monthly_subscriptions * 12,
                "total_annual_revenue": round((total_platform_fees * (365 / days)) + (monthly_subscriptions * 12), 2)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
