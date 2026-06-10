"""
Scheduled Tasks API
Endpoints for automated tasks (weekly digests, alerts, etc.)
Can be triggered by cron jobs or manual admin actions
"""
from flask import Blueprint, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from datetime import datetime, timedelta
from models import Tenant, User
from services.owner_analytics import OwnerAnalytics
from services.email_service import EmailService
import sys

scheduled_bp = Blueprint('scheduled', __name__)


def require_owner(f):
    """Decorator to require owner role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'owner':
            return jsonify({'error': 'Only business owners can access this endpoint'}), 403
        return f(*args, **kwargs)
    return decorated_function


@scheduled_bp.route('/digest/preview', methods=['GET'])
@jwt_required()
@require_owner
def preview_digest():
    """
    Preview weekly digest for current tenant
    Shows what would be sent in the email
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Get 7-day period for digest
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Gather digest data
        summary = OwnerAnalytics.get_executive_summary(g.db, tenant_id)
        top_items = OwnerAnalytics.get_top_items_by_profit(g.db, tenant_id, limit=10, start_date=start_date, end_date=end_date)
        labor = OwnerAnalytics.get_labor_analysis(g.db, tenant_id, start_date, end_date)
        inventory = OwnerAnalytics.get_inventory_valuation(g.db, tenant_id)

        digest_data = {
            'summary': summary,
            'top_items': top_items,
            'labor': labor,
            'inventory': inventory
        }

        return jsonify({
            'message': 'Digest preview generated',
            'business_name': tenant.business_name,
            'owner_email': tenant.owner_email,
            'digest_data': digest_data,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }), 200

    except Exception as e:
        print(f"Error generating digest preview: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500


@scheduled_bp.route('/digest/send', methods=['POST'])
@jwt_required()
@require_owner
def send_digest_to_owner():
    """
    Send weekly digest to current tenant owner
    Allows owners to manually trigger their digest
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Get 7-day period for digest
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Gather digest data
        summary = OwnerAnalytics.get_executive_summary(g.db, tenant_id)
        top_items = OwnerAnalytics.get_top_items_by_profit(g.db, tenant_id, limit=10, start_date=start_date, end_date=end_date)
        labor = OwnerAnalytics.get_labor_analysis(g.db, tenant_id, start_date, end_date)
        inventory = OwnerAnalytics.get_inventory_valuation(g.db, tenant_id)

        digest_data = {
            'summary': summary,
            'top_items': top_items,
            'labor': labor,
            'inventory': inventory
        }

        # Send email
        email_sent = EmailService.send_weekly_digest(
            to=tenant.owner_email,
            business_name=tenant.business_name,
            digest_data=digest_data
        )

        if email_sent:
            return jsonify({
                'message': f'Weekly digest sent to {tenant.owner_email}',
                'status': 'sent'
            }), 200
        else:
            return jsonify({
                'message': 'Email service not configured. Digest generated but not sent.',
                'status': 'not_sent',
                'digest_data': digest_data
            }), 200

    except Exception as e:
        print(f"Error sending digest: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500


@scheduled_bp.route('/digest/send-all', methods=['POST'])
def send_all_digests():
    """
    Send weekly digests to all active tenants
    Protected endpoint for cron jobs (no auth required)

    Security: This should be protected by IP whitelist or API key in production
    For now, no auth to allow cron job access
    """
    from database import Session
    db = Session()

    try:
        # Get all active tenants with active subscriptions
        tenants = db.query(Tenant).filter(
            Tenant.is_active == True
        ).all()

        results = {
            'total_tenants': len(tenants),
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        for tenant in tenants:
            try:
                # Skip if no owner email
                if not tenant.owner_email:
                    results['skipped'] += 1
                    continue

                # Gather digest data
                summary = OwnerAnalytics.get_executive_summary(db, tenant.id)
                top_items = OwnerAnalytics.get_top_items_by_profit(db, tenant.id, limit=10, start_date=start_date, end_date=end_date)
                labor = OwnerAnalytics.get_labor_analysis(db, tenant.id, start_date, end_date)
                inventory = OwnerAnalytics.get_inventory_valuation(db, tenant.id)

                digest_data = {
                    'summary': summary,
                    'top_items': top_items,
                    'labor': labor,
                    'inventory': inventory
                }

                # Send email
                email_sent = EmailService.send_weekly_digest(
                    to=tenant.owner_email,
                    business_name=tenant.business_name,
                    digest_data=digest_data
                )

                if email_sent:
                    results['sent'] += 1
                    print(f"✅ Digest sent to {tenant.business_name} ({tenant.owner_email})")
                else:
                    results['skipped'] += 1
                    print(f"⚠️ Email service unavailable for {tenant.business_name}")

            except Exception as tenant_error:
                results['failed'] += 1
                error_msg = f"{tenant.business_name}: {str(tenant_error)}"
                results['errors'].append(error_msg)
                print(f"❌ Failed to send digest to {tenant.business_name}: {tenant_error}", file=sys.stderr)

        return jsonify({
            'message': f'Batch digest job completed',
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        print(f"Error in batch digest job: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@scheduled_bp.route('/digest/test-email', methods=['POST'])
@jwt_required()
@require_owner
def test_email_service():
    """
    Test email service with sample data
    Helps owners verify their email configuration
    """
    try:
        user_id = get_jwt().get('sub')
        user = g.db.query(User).filter_by(id=user_id).first()
        tenant = g.db.query(Tenant).filter_by(id=g.tenant_id).first()

        if not user or not tenant:
            return jsonify({'error': 'User or tenant not found'}), 404

        # Create sample digest data
        sample_data = {
            'summary': {
                'today': {
                    'revenue': 1250.00,
                    'vs_yesterday': 150.00,
                    'vs_yesterday_percent': 13.6
                },
                'this_week': {
                    'revenue': 7840.00,
                    'profit': 3920.00,
                    'margin_percent': 50.0,
                    'transaction_count': 87
                },
                'labor': {
                    'cost_percent': 28.5,
                    'status': 'good',
                    'total_cost': 2234.40
                },
                'inventory': {
                    'total_value': 15600.00,
                    'dead_stock_count': 2
                },
                'action_items': [
                    {
                        'priority': 'medium',
                        'category': 'inventory',
                        'message': '2 items with no sales in 90 days',
                        'action': 'Consider markdowns or discontinuing slow items'
                    }
                ]
            },
            'top_items': {
                'top_performers': [
                    {'name': 'Sample Product A', 'revenue': 450.00, 'profit': 225.00, 'margin_percent': 50.0},
                    {'name': 'Sample Product B', 'revenue': 380.00, 'profit': 190.00, 'margin_percent': 50.0}
                ]
            },
            'labor': {
                'status': 'good',
                'cost_percent': 28.5,
                'total_cost': 2234.40
            },
            'inventory': {
                'total_value': 15600.00,
                'unique_items': 42,
                'dead_stock_count': 2,
                'dead_stock_items': [
                    {'name': 'Slow Item X', 'quantity': 15, 'value': 120.00},
                    {'name': 'Slow Item Y', 'quantity': 8, 'value': 64.00}
                ]
            }
        }

        # Send test email
        email_sent = EmailService.send_weekly_digest(
            to=user.email,
            business_name=tenant.business_name + " (TEST)",
            digest_data=sample_data
        )

        if email_sent:
            return jsonify({
                'message': f'Test digest sent to {user.email}',
                'status': 'sent'
            }), 200
        else:
            return jsonify({
                'message': 'Email service not configured. Set RESEND_API_KEY environment variable.',
                'status': 'not_configured'
            }), 200

    except Exception as e:
        print(f"Error sending test email: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500
