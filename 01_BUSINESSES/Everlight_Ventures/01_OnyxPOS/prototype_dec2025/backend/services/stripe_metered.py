"""
Stripe Metered Billing Service
Handles usage record submission for GMV-based fees
"""
import stripe
import os
from datetime import datetime
from models import Tenant

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def record_gmv_usage(tenant, gmv_amount, billing_period):
    """
    Record GMV usage to Stripe for metered billing

    Args:
        tenant: Tenant model instance
        gmv_amount: GMV amount for the period (float)
        billing_period: String like "2025-01" for idempotency

    Returns:
        dict: {
            'success': bool,
            'usage_record_id': str,
            'amount_billed': float,
            'cap_reached': bool,
            'error': str (if failed)
        }
    """
    try:
        if not tenant.stripe_subscription_id:
            return {
                'success': False,
                'error': 'No Stripe subscription found'
            }

        # Get subscription to find usage-based price item
        subscription = stripe.Subscription.retrieve(tenant.stripe_subscription_id)

        # Find the metered price item (look for usage_type = 'metered')
        metered_item = None
        for item in subscription['items']['data']:
            price = item['price']
            if price.get('recurring', {}).get('usage_type') == 'metered':
                metered_item = item
                break

        if not metered_item:
            return {
                'success': False,
                'error': 'No metered price item found in subscription'
            }

        # Calculate usage fee with cap
        usage_fee = tenant.calculate_usage_fee(gmv_amount)
        cap = tenant.get_variable_fee_cap()
        uncapped_fee = gmv_amount * (tenant.get_platform_fee_percent() / 100)
        cap_reached = cap > 0 and uncapped_fee > cap

        # Stripe Usage Records use quantity (not dollar amount)
        # We need to define the price per unit in Stripe Dashboard
        # For GMV billing, we'll use cents as the unit
        # Example: $150 usage fee = 15000 cents quantity
        quantity = int(usage_fee * 100)  # Convert dollars to cents

        # Create idempotency key: tenant_id + billing_period
        idempotency_key = f"gmv_{tenant.id}_{billing_period}"

        # Submit usage record to Stripe
        usage_record = stripe.SubscriptionItem.create_usage_record(
            metered_item['id'],
            quantity=quantity,
            timestamp=int(datetime.utcnow().timestamp()),
            action='set',  # 'set' replaces previous value, 'increment' adds to it
            idempotency_key=idempotency_key
        )

        return {
            'success': True,
            'usage_record_id': usage_record['id'],
            'amount_billed': usage_fee,
            'quantity': quantity,
            'cap_reached': cap_reached,
            'savings': round(uncapped_fee - usage_fee, 2) if cap_reached else 0,
        }

    except stripe.error.StripeError as e:
        return {
            'success': False,
            'error': f'Stripe error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error: {str(e)}'
        }


def get_usage_summary(tenant):
    """
    Get usage summary from Stripe for current billing period

    Args:
        tenant: Tenant model instance

    Returns:
        dict: Usage summary or error
    """
    try:
        if not tenant.stripe_subscription_id:
            return {'error': 'No subscription found'}

        subscription = stripe.Subscription.retrieve(tenant.stripe_subscription_id)

        # Find metered item
        metered_item = None
        for item in subscription['items']['data']:
            if item['price'].get('recurring', {}).get('usage_type') == 'metered':
                metered_item = item
                break

        if not metered_item:
            return {'error': 'No metered item found'}

        # Get usage record summaries
        summaries = stripe.SubscriptionItem.list_usage_record_summaries(
            metered_item['id'],
            limit=10
        )

        return {
            'success': True,
            'summaries': summaries['data']
        }

    except Exception as e:
        return {'error': str(e)}
