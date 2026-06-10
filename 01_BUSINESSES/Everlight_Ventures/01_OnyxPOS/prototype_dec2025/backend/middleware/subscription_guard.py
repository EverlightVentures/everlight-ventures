"""
Subscription Access Guard Middleware
Blocks access to POS features if subscription is suspended or canceled
"""
from flask import g, jsonify, request
from models import Tenant
from datetime import datetime


def check_subscription_access():
    """
    Middleware to check if tenant has valid subscription

    Grace Period Logic:
    - trial: Full access during trial
    - active: Full access
    - past_due: 10-day grace period, then suspend
    - suspended: Blocked from POS features, can access billing/settings
    - canceled: Blocked from all features except billing
    """
    # Skip check for health, webhook, auth, and public endpoints
    exempt_paths = [
        '/health',
        '/',
        '/api/v1/auth/',
        '/api/v1/billing/webhook',
        '/api/v1/billing/pricing-tiers',  # Public pricing info
    ]

    for path in exempt_paths:
        if request.path.startswith(path):
            return None

    # Only check authenticated requests with tenant_id
    if not hasattr(g, 'tenant_id') or not g.tenant_id:
        return None

    try:
        tenant = g.db.query(Tenant).filter_by(id=g.tenant_id).first()

        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Check subscription status
        status = tenant.subscription_status

        # Active subscriptions: full access
        if status in ['trial', 'active']:
            return None

        # Past due: Check grace period (10 days)
        if status == 'past_due':
            grace_period_days = 10

            # If current_period_end is more than grace_period_days ago, suspend
            if tenant.current_period_end:
                days_overdue = (datetime.utcnow() - tenant.current_period_end).days

                if days_overdue > grace_period_days:
                    # Auto-suspend
                    tenant.subscription_status = 'suspended'
                    g.db.commit()
                    status = 'suspended'
                else:
                    # Still in grace period
                    return None
            else:
                # No period end set, allow access for now
                return None

        # Suspended: Block POS features, allow billing/settings
        if status == 'suspended':
            allowed_paths = [
                '/api/v1/billing',
                '/api/v1/diagnostics',
            ]

            for path in allowed_paths:
                if request.path.startswith(path):
                    return None

            return jsonify({
                'error': 'Subscription suspended',
                'message': 'Your account is suspended due to payment failure. Please update your payment method.',
                'code': 'SUBSCRIPTION_SUSPENDED',
                'action': 'update_payment',
            }), 402  # 402 Payment Required

        # Canceled: Block all features except billing
        if status == 'canceled':
            if request.path.startswith('/api/v1/billing'):
                return None

            return jsonify({
                'error': 'Subscription canceled',
                'message': 'Your subscription has been canceled. Reactivate to continue using OnyxPOS.',
                'code': 'SUBSCRIPTION_CANCELED',
                'action': 'reactivate',
            }), 403

        # Unknown status: block access for safety
        return jsonify({
            'error': 'Invalid subscription status',
            'message': 'Please contact support.',
            'code': 'INVALID_STATUS',
        }), 500

    except Exception as e:
        print(f"❌ Subscription guard error: {e}")
        # On error, allow access to prevent lockout (fail open)
        return None
