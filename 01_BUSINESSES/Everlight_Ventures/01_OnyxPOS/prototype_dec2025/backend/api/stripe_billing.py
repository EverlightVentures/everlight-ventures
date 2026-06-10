"""
Stripe Subscription & Billing API
- Create subscriptions
- Manage payment methods
- Handle webhooks
- Billing portal
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from models import Tenant
from datetime import datetime, timedelta
import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

billing_bp = Blueprint('billing', __name__)


# Price IDs - Create these in Stripe Dashboard
# New Pricing: Core $119, Growth $249, Prime $399 + platform fees
STRIPE_PRICES = {
    'core': os.getenv('STRIPE_PRICE_CORE', 'price_core_119'),
    'growth': os.getenv('STRIPE_PRICE_GROWTH', 'price_growth_249'),
    'prime': os.getenv('STRIPE_PRICE_PRIME', 'price_prime_399'),

    # Legacy tier mappings for backward compatibility
    'onyxpos_core': os.getenv('STRIPE_PRICE_CORE', 'price_core_119'),
    'onyxpayroll': os.getenv('STRIPE_PRICE_GROWTH', 'price_growth_249'),
    'onyxos_bundle': os.getenv('STRIPE_PRICE_PRIME', 'price_prime_399'),
    'starter': os.getenv('STRIPE_PRICE_CORE', 'price_core_119'),
    'professional': os.getenv('STRIPE_PRICE_GROWTH', 'price_growth_249'),
    'enterprise': os.getenv('STRIPE_PRICE_PRIME', 'price_prime_399'),
}

# Plan metadata
PLAN_METADATA = {
    'core': {
        'name': 'Core',
        'price': 119,
        'devices': 2,
        'team_size': 6,
        'features': ['Auto-SKU', 'Task Management', 'Auto Scheduling', 'FIFO/COGS']
    },
    'growth': {
        'name': 'Growth',
        'price': 249,
        'devices': 6,
        'team_size': 15,
        'features': ['All Core features', 'Shopify', 'Square', 'Gusto', 'QuickBooks']
    },
    'prime': {
        'name': 'Prime',
        'price': 399,
        'devices': 0,  # Unlimited
        'team_size': 0,  # Unlimited
        'features': ['All Growth features', 'DoorDash', 'UberEats', 'Grubhub', 'Instacart', 'OnyxAI', 'Priority Support']
    }
}


def require_owner(f):
    """Decorator to require owner role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'owner':
            return jsonify({'error': 'Only business owners can manage billing'}), 403
        return f(*args, **kwargs)
    return decorated_function


@billing_bp.route('/create-checkout-session', methods=['POST'])
@jwt_required()
@require_owner
def create_checkout_session():
    """
    Create Stripe Checkout session for subscription
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        plan_tier = data.get('plan_tier', 'core')

        if plan_tier not in STRIPE_PRICES:
            return jsonify({'error': 'Invalid plan tier. Choose: core, growth, or prime'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Create or get Stripe customer
        if not tenant.stripe_customer_id:
            customer = stripe.Customer.create(
                email=tenant.owner_email,
                metadata={
                    'tenant_id': tenant_id,
                    'business_name': tenant.business_name,
                }
            )
            tenant.stripe_customer_id = customer.id
            g.db.commit()

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICES[plan_tier],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=data.get('success_url', 'http://localhost:3000/billing?success=true'),
            cancel_url=data.get('cancel_url', 'http://localhost:3000/billing?canceled=true'),
            metadata={
                'tenant_id': tenant_id,
                'plan_tier': plan_tier,
            },
        )

        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/create-portal-session', methods=['POST'])
@jwt_required()
@require_owner
def create_portal_session():
    """
    Create Stripe Customer Portal session
    Allows customers to manage their subscription
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant.stripe_customer_id:
            return jsonify({'error': 'No Stripe customer found'}), 404

        portal_session = stripe.billing_portal.Session.create(
            customer=tenant.stripe_customer_id,
            return_url=request.json.get('return_url', 'http://localhost:3000/billing'),
        )

        return jsonify({
            'portal_url': portal_session.url,
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/subscription-status', methods=['GET'])
@jwt_required()
def get_subscription_status():
    """
    Get current subscription status for tenant
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        subscription_info = {
            'plan_tier': tenant.plan_tier,
            'subscription_status': tenant.subscription_status,
            'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            'current_period_end': tenant.current_period_end.isoformat() if tenant.current_period_end else None,
            'trial_days_remaining': tenant.trial_days_remaining if tenant.is_trial else None,
        }

        # Get usage stats
        subscription_info['usage'] = {
            'transactions_this_month': tenant.transaction_count_current_month,
            'active_users': tenant.user_count,
            'locations': tenant.location_count,
        }

        # Get plan limits and platform fees
        plan_limits = {
            'core': {
                'max_devices': 2,
                'max_team_size': 6,
                'features': PLAN_METADATA['core']['features']
            },
            'growth': {
                'max_devices': 6,
                'max_team_size': 15,
                'features': PLAN_METADATA['growth']['features']
            },
            'prime': {
                'max_devices': 0,  # Unlimited
                'max_team_size': 0,  # Unlimited
                'features': PLAN_METADATA['prime']['features']
            },
        }

        subscription_info['limits'] = plan_limits.get(tenant.plan_tier, plan_limits['core'])

        # Add platform fee calculation
        gmv = float(tenant.gmv_current_month or 0)
        platform_fee = tenant.calculate_usage_fee(gmv)
        subscription_info['platform_fees'] = {
            'current_month_gmv': round(gmv, 2),
            'platform_fee': platform_fee,
            'subscription_fee': PLAN_METADATA.get(tenant.plan_tier, {}).get('price', 119),
            'total_monthly_cost': round(PLAN_METADATA.get(tenant.plan_tier, {}).get('price', 119) + platform_fee, 2)
        }

        return jsonify(subscription_info), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhooks
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        handle_checkout_completed(event['data']['object'])

    elif event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])

    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])

    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])

    elif event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])

    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])

    return jsonify({'status': 'success'}), 200


def handle_checkout_completed(session):
    """Handle successful checkout"""
    from database import Session
    db = Session()

    try:
        tenant_id = session['metadata']['tenant_id']
        plan_tier = session['metadata']['plan_tier']

        tenant = db.query(Tenant).filter_by(id=tenant_id).first()
        if tenant:
            tenant.plan_tier = plan_tier
            tenant.subscription_status = 'active'
            tenant.stripe_subscription_id = session.get('subscription')
            db.commit()

            print(f"✅ Checkout completed for {tenant.business_name}")
    finally:
        db.close()


def handle_subscription_created(subscription):
    """Handle subscription creation"""
    from database import Session
    db = Session()

    try:
        customer_id = subscription['customer']
        tenant = db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()

        if tenant:
            tenant.stripe_subscription_id = subscription['id']
            tenant.subscription_status = subscription['status']
            tenant.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            db.commit()

            print(f"✅ Subscription created for {tenant.business_name}")
    finally:
        db.close()


def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    from database import Session
    db = Session()

    try:
        customer_id = subscription['customer']
        tenant = db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()

        if tenant:
            tenant.subscription_status = subscription['status']
            tenant.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])

            # Update plan tier based on price
            price_id = subscription['items']['data'][0]['price']['id']
            for tier, pid in STRIPE_PRICES.items():
                if pid == price_id:
                    tenant.plan_tier = tier
                    break

            db.commit()

            print(f"✅ Subscription updated for {tenant.business_name}")
    finally:
        db.close()


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    from database import Session
    db = Session()

    try:
        customer_id = subscription['customer']
        tenant = db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()

        if tenant:
            tenant.subscription_status = 'canceled'
            db.commit()

            print(f"⚠️ Subscription canceled for {tenant.business_name}")
    finally:
        db.close()


def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    from database import Session
    from services.email import send_payment_succeeded_email
    db = Session()

    try:
        customer_id = invoice['customer']
        tenant = db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()

        if tenant:
            tenant.subscription_status = 'active'
            db.commit()

            print(f"✅ Payment succeeded for {tenant.business_name}")

            # Send confirmation email
            invoice_amount = invoice.get('amount_paid', 0) / 100  # Convert cents to dollars
            send_payment_succeeded_email(tenant, invoice_amount)
    finally:
        db.close()


def handle_payment_failed(invoice):
    """Handle failed payment"""
    from database import Session
    from services.email import send_payment_failed_email
    db = Session()

    try:
        customer_id = invoice['customer']
        tenant = db.query(Tenant).filter_by(stripe_customer_id=customer_id).first()

        if tenant:
            tenant.subscription_status = 'past_due'
            db.commit()

            print(f"❌ Payment failed for {tenant.business_name}")

            # Send failure notification email
            invoice_amount = invoice.get('amount_due', 0) / 100  # Convert cents to dollars
            send_payment_failed_email(tenant, invoice_amount)
    finally:
        db.close()


@billing_bp.route('/cancel-subscription', methods=['POST'])
@jwt_required()
@require_owner
def cancel_subscription():
    """
    Cancel subscription at period end
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant.stripe_subscription_id:
            return jsonify({'error': 'No active subscription'}), 404

        # Cancel at period end (not immediately)
        subscription = stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            cancel_at_period_end=True
        )

        return jsonify({
            'message': 'Subscription will be canceled at period end',
            'period_end': datetime.fromtimestamp(subscription['current_period_end']).isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/reactivate-subscription', methods=['POST'])
@jwt_required()
@require_owner
def reactivate_subscription():
    """
    Reactivate a canceled subscription
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        if not tenant.stripe_subscription_id:
            return jsonify({'error': 'No subscription found'}), 404

        # Remove cancellation
        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            cancel_at_period_end=False
        )

        tenant.subscription_status = 'active'
        g.db.commit()

        return jsonify({'message': 'Subscription reactivated'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/upgrade', methods=['POST'])
@jwt_required()
@require_owner
def upgrade_plan():
    """
    Upgrade subscription to a higher tier
    """
    try:
        tenant_id = g.tenant_id
        data = request.json
        new_tier = data.get('new_tier')

        if new_tier not in ['core', 'growth', 'prime']:
            return jsonify({'error': 'Invalid tier. Choose: core, growth, or prime'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Validate upgrade path
        tier_order = {'core': 1, 'growth': 2, 'prime': 3}
        current_order = tier_order.get(tenant.plan_tier, 0)
        new_order = tier_order.get(new_tier, 0)

        if new_order <= current_order:
            return jsonify({'error': f'Cannot upgrade from {tenant.plan_tier} to {new_tier}. Use /downgrade instead.'}), 400

        # If no Stripe subscription, create checkout session
        if not tenant.stripe_subscription_id:
            return jsonify({
                'error': 'No active subscription. Use /create-checkout-session instead.',
                'action': 'create_checkout'
            }), 400

        # Update Stripe subscription
        subscription = stripe.Subscription.retrieve(tenant.stripe_subscription_id)

        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': STRIPE_PRICES[new_tier],
            }],
            proration_behavior='always_invoice',  # Charge immediately for upgrade
        )

        # Update tenant
        tenant.plan_tier = new_tier
        g.db.commit()

        return jsonify({
            'message': f'Successfully upgraded to {new_tier} plan',
            'new_plan': PLAN_METADATA[new_tier],
            'prorated_charge': 'Prorated amount will appear on your next invoice'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/downgrade', methods=['POST'])
@jwt_required()
@require_owner
def downgrade_plan():
    """
    Downgrade subscription to a lower tier (applies at period end)
    """
    try:
        tenant_id = g.tenant_id
        data = request.json
        new_tier = data.get('new_tier')

        if new_tier not in ['core', 'growth', 'prime']:
            return jsonify({'error': 'Invalid tier. Choose: core, growth, or prime'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Validate downgrade path
        tier_order = {'core': 1, 'growth': 2, 'prime': 3}
        current_order = tier_order.get(tenant.plan_tier, 0)
        new_order = tier_order.get(new_tier, 0)

        if new_order >= current_order:
            return jsonify({'error': f'Cannot downgrade from {tenant.plan_tier} to {new_tier}. Use /upgrade instead.'}), 400

        if not tenant.stripe_subscription_id:
            return jsonify({'error': 'No active subscription'}), 404

        # Check if downgrade will violate limits
        new_limits = {
            'core': {'devices': 2, 'team': 6},
            'growth': {'devices': 6, 'team': 15},
            'prime': {'devices': 0, 'team': 0}
        }

        from models import DeviceSession, User
        active_devices = g.db.query(DeviceSession).filter_by(
            tenant_id=tenant_id, is_active=True
        ).count()
        active_team = g.db.query(User).filter_by(
            tenant_id=tenant_id, is_active=True
        ).count()

        violations = []
        if new_limits[new_tier]['devices'] > 0 and active_devices > new_limits[new_tier]['devices']:
            violations.append(f"You have {active_devices} active devices but {new_tier} plan allows {new_limits[new_tier]['devices']}")
        if new_limits[new_tier]['team'] > 0 and active_team > new_limits[new_tier]['team']:
            violations.append(f"You have {active_team} team members but {new_tier} plan allows {new_limits[new_tier]['team']}")

        if violations:
            return jsonify({
                'error': 'Cannot downgrade due to limit violations',
                'violations': violations,
                'action_required': 'Please remove excess devices/team members before downgrading'
            }), 400

        # Schedule downgrade at period end
        subscription = stripe.Subscription.retrieve(tenant.stripe_subscription_id)

        stripe.Subscription.modify(
            tenant.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': STRIPE_PRICES[new_tier],
            }],
            proration_behavior='none',  # No refund for downgrade
        )

        return jsonify({
            'message': f'Downgrade to {new_tier} plan scheduled',
            'new_plan': PLAN_METADATA[new_tier],
            'effective_date': datetime.fromtimestamp(subscription['current_period_end']).isoformat(),
            'note': 'Downgrade will take effect at the end of your current billing period'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/plans', methods=['GET'])
def get_available_plans():
    """
    Get all available subscription plans with pricing
    """
    return jsonify({
        'plans': [
            {
                'tier': 'core',
                'name': PLAN_METADATA['core']['name'],
                'price': PLAN_METADATA['core']['price'],
                'devices': PLAN_METADATA['core']['devices'],
                'team_size': PLAN_METADATA['core']['team_size'],
                'features': PLAN_METADATA['core']['features'],
                'platform_fees': {
                    'description': 'Tiered platform fees based on monthly sales',
                    'tiers': [
                        {'range': 'First $10,000', 'rate': '10%'},
                        {'range': '$10,001 - $50,000', 'rate': '5%'},
                        {'range': 'Over $50,000', 'rate': '1%'}
                    ],
                    'minimum': '$1,000/month'
                }
            },
            {
                'tier': 'growth',
                'name': PLAN_METADATA['growth']['name'],
                'price': PLAN_METADATA['growth']['price'],
                'devices': PLAN_METADATA['growth']['devices'],
                'team_size': PLAN_METADATA['growth']['team_size'],
                'features': PLAN_METADATA['growth']['features'],
                'platform_fees': {
                    'description': 'Same tiered platform fees as Core',
                    'tiers': [
                        {'range': 'First $10,000', 'rate': '10%'},
                        {'range': '$10,001 - $50,000', 'rate': '5%'},
                        {'range': 'Over $50,000', 'rate': '1%'}
                    ],
                    'minimum': '$1,000/month'
                }
            },
            {
                'tier': 'prime',
                'name': PLAN_METADATA['prime']['name'],
                'price': PLAN_METADATA['prime']['price'],
                'devices': 'Unlimited',
                'team_size': 'Unlimited',
                'features': PLAN_METADATA['prime']['features'],
                'platform_fees': {
                    'description': 'Same tiered platform fees as other plans',
                    'tiers': [
                        {'range': 'First $10,000', 'rate': '10%'},
                        {'range': '$10,001 - $50,000', 'rate': '5%'},
                        {'range': 'Over $50,000', 'rate': '1%'}
                    ],
                    'minimum': '$1,000/month'
                }
            }
        ]
    }), 200


# ============================================
# TESTING ENDPOINTS (For development only)
# ============================================

@billing_bp.route('/test/simulate-subscription', methods=['POST'])
@jwt_required()
@require_owner
def simulate_subscription():
    """
    TESTING ONLY: Simulate a subscription purchase without Stripe
    This allows testing the subscription flow without actual payment
    """
    try:
        tenant_id = g.tenant_id
        data = request.json
        plan_tier = data.get('plan_tier', 'core')

        if plan_tier not in ['core', 'growth', 'prime']:
            return jsonify({'error': 'Invalid tier'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Simulate subscription activation
        tenant.plan_tier = plan_tier
        tenant.subscription_status = 'active'
        tenant.current_period_end = datetime.utcnow() + timedelta(days=30)

        # Create fake Stripe IDs for testing
        if not tenant.stripe_customer_id:
            tenant.stripe_customer_id = f'cus_test_{tenant_id[:8]}'
        if not tenant.stripe_subscription_id:
            tenant.stripe_subscription_id = f'sub_test_{tenant_id[:8]}'

        g.db.commit()

        return jsonify({
            'success': True,
            'message': f'Simulated {plan_tier} subscription activated',
            'subscription': {
                'plan_tier': tenant.plan_tier,
                'status': tenant.subscription_status,
                'period_end': tenant.current_period_end.isoformat(),
                'monthly_cost': PLAN_METADATA[plan_tier]['price']
            },
            'note': 'This is a test subscription. No actual payment was processed.'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/test/add-sales', methods=['POST'])
@jwt_required()
@require_owner
def test_add_sales():
    """
    TESTING ONLY: Add test sales to simulate GMV and platform fees
    """
    try:
        tenant_id = g.tenant_id
        data = request.json
        amount = float(data.get('amount', 0))

        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Add to current month GMV
        current_gmv = float(tenant.gmv_current_month or 0)
        new_gmv = current_gmv + amount
        tenant.gmv_current_month = new_gmv

        g.db.commit()

        # Calculate platform fee
        platform_fee = tenant.calculate_usage_fee(new_gmv)

        return jsonify({
            'success': True,
            'message': f'Added ${amount:.2f} in test sales',
            'gmv': {
                'previous': round(current_gmv, 2),
                'added': round(amount, 2),
                'total': round(new_gmv, 2)
            },
            'fees': {
                'subscription_fee': PLAN_METADATA.get(tenant.plan_tier, {}).get('price', 119),
                'platform_fee': platform_fee,
                'total_monthly_cost': round(PLAN_METADATA.get(tenant.plan_tier, {}).get('price', 119) + platform_fee, 2)
            },
            'breakdown': {
                'first_10k': round(min(new_gmv, 10000) * 0.10, 2),
                'next_40k': round(max(0, min(new_gmv - 10000, 40000)) * 0.05, 2),
                'over_50k': round(max(0, new_gmv - 50000) * 0.01, 2),
                'minimum_applied': platform_fee == 1000.00
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/test/upgrade', methods=['POST'])
@jwt_required()
@require_owner
def test_upgrade():
    """
    TESTING ONLY: Upgrade subscription tier without Stripe
    This allows testing the upgrade flow without actual payment
    """
    try:
        tenant_id = g.tenant_id
        data = request.json
        new_tier = data.get('new_tier')

        if new_tier not in ['core', 'growth', 'prime']:
            return jsonify({'error': 'Invalid tier. Choose: core, growth, or prime'}), 400

        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Validate upgrade path
        tier_order = {'core': 1, 'growth': 2, 'prime': 3}
        current_order = tier_order.get(tenant.plan_tier, 0)
        new_order = tier_order.get(new_tier, 0)

        if new_order <= current_order:
            return jsonify({'error': f'Cannot upgrade from {tenant.plan_tier} to {new_tier}'}), 400

        # Update tenant plan
        tenant.plan_tier = new_tier
        g.db.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully upgraded to {new_tier} plan',
            'upgraded': True,
            'subscription': {
                'plan_tier': tenant.plan_tier,
                'status': tenant.subscription_status,
                'monthly_cost': PLAN_METADATA[new_tier]['price'],
                'limits': {
                    'devices': PLAN_METADATA[new_tier]['devices'],
                    'team_size': PLAN_METADATA[new_tier]['team_size']
                }
            },
            'note': 'This is a test upgrade. No actual payment was processed.'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/test/reset-subscription', methods=['POST'])
@jwt_required()
@require_owner
def test_reset_subscription():
    """
    TESTING ONLY: Reset subscription and GMV to start fresh
    """
    try:
        tenant_id = g.tenant_id
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()

        # Reset subscription
        tenant.plan_tier = 'core'
        tenant.subscription_status = 'trialing'
        tenant.gmv_current_month = 0.0
        tenant.stripe_customer_id = None
        tenant.stripe_subscription_id = None

        g.db.commit()

        return jsonify({
            'success': True,
            'message': 'Subscription reset to defaults',
            'tenant': {
                'plan_tier': 'core',
                'subscription_status': 'trialing',
                'gmv': 0.0
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
