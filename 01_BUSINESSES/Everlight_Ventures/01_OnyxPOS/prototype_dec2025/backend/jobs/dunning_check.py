"""
Dunning Check Job
Runs daily to enforce dunning rules and grace periods

Dunning Flow:
- Day 0: Payment fails → status = past_due (handled by webhook)
- Day 1-7: Stripe auto-retries payment (Smart Retries)
- Day 7: Send "Past Due" warning email
- Day 10: Grace period ends → status = suspended, send email
- Day 30: Auto-cancel → status = canceled, send email

This job runs daily to:
1. Check past_due tenants and enforce grace period
2. Send reminder emails at day 7
3. Auto-suspend at day 10
4. Auto-cancel at day 30
"""
from datetime import datetime, timedelta
from database import Session
from models import Tenant
from services.email import send_payment_failed_email, send_account_suspended_email
import sys


def run_dunning_check(dry_run=False):
    """
    Execute daily dunning check

    Args:
        dry_run: If True, report actions but don't execute

    Returns:
        dict: Summary of dunning actions
    """
    print("\n" + "=" * 60)
    print("  OnyxPOS Dunning Check")
    print(f"  Run Date: {datetime.utcnow().isoformat()}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60 + "\n")

    db = Session()
    summary = {
        'past_due_tenants': 0,
        'warnings_sent': 0,
        'suspended': 0,
        'canceled': 0,
        'errors': 0,
        'actions': []
    }

    try:
        # Get all past_due or suspended tenants
        tenants = db.query(Tenant).filter(
            Tenant.subscription_status.in_(['past_due', 'suspended'])
        ).all()

        print(f"Found {len(tenants)} tenants in past_due/suspended status\n")

        for tenant in tenants:
            action = process_tenant_dunning(tenant, dry_run, db)
            if action:
                summary['actions'].append(action)

                if action['action'] == 'warning_sent':
                    summary['warnings_sent'] += 1
                elif action['action'] == 'suspended':
                    summary['suspended'] += 1
                elif action['action'] == 'canceled':
                    summary['canceled'] += 1
                elif action['action'] == 'error':
                    summary['errors'] += 1

        summary['past_due_tenants'] = len(tenants)

        # Print summary
        print("\n" + "=" * 60)
        print("  Dunning Check Summary")
        print("=" * 60)
        print(f"  Past Due Tenants:   {summary['past_due_tenants']}")
        print(f"  Warnings Sent:      {summary['warnings_sent']}")
        print(f"  Suspended:          {summary['suspended']}")
        print(f"  Canceled:           {summary['canceled']}")
        print(f"  Errors:             {summary['errors']}")
        print("=" * 60 + "\n")

        if dry_run:
            print("⚠️  DRY RUN - No actions were taken\n")
        else:
            print("✅ Dunning check complete\n")

        return summary

    except Exception as e:
        print(f"❌ Fatal error during dunning check: {e}")
        summary['fatal_error'] = str(e)
        return summary

    finally:
        db.close()


def process_tenant_dunning(tenant, dry_run, db):
    """
    Process dunning for a single tenant

    Args:
        tenant: Tenant model instance
        dry_run: Boolean
        db: Database session

    Returns:
        dict: Action taken or None if no action needed
    """
    try:
        # Calculate days overdue
        if not tenant.current_period_end:
            return None

        days_overdue = (datetime.utcnow() - tenant.current_period_end).days

        if days_overdue < 0:
            # Not actually overdue yet
            return None

        print(f"📊 {tenant.business_name}:")
        print(f"   Status: {tenant.subscription_status}")
        print(f"   Days Overdue: {days_overdue}")

        # Day 7: Send warning email
        if days_overdue == 7 and tenant.subscription_status == 'past_due':
            print(f"   ⚠️  Day 7: Sending past due warning email")

            if not dry_run:
                # Get most recent invoice amount (estimate)
                invoice_amount = tenant.get_total_monthly_cost()
                send_payment_failed_email(tenant, invoice_amount)

            print(f"   ✉️  Warning email sent to {tenant.owner_email}")
            print()

            return {
                'tenant_id': tenant.id,
                'business_name': tenant.business_name,
                'action': 'warning_sent',
                'days_overdue': days_overdue
            }

        # Day 10: Suspend account
        elif days_overdue >= 10 and tenant.subscription_status == 'past_due':
            print(f"   🚫 Day {days_overdue}: Suspending account (grace period ended)")

            if not dry_run:
                tenant.subscription_status = 'suspended'
                db.commit()
                send_account_suspended_email(tenant)

            print(f"   ✉️  Suspension email sent to {tenant.owner_email}")
            print()

            return {
                'tenant_id': tenant.id,
                'business_name': tenant.business_name,
                'action': 'suspended',
                'days_overdue': days_overdue
            }

        # Day 30: Auto-cancel
        elif days_overdue >= 30 and tenant.subscription_status in ['past_due', 'suspended']:
            print(f"   ❌ Day {days_overdue}: Auto-canceling subscription")

            if not dry_run:
                tenant.subscription_status = 'canceled'
                db.commit()

                # Note: Should also cancel Stripe subscription here
                # stripe.Subscription.delete(tenant.stripe_subscription_id)

            print(f"   🗑️  Subscription canceled")
            print()

            return {
                'tenant_id': tenant.id,
                'business_name': tenant.business_name,
                'action': 'canceled',
                'days_overdue': days_overdue
            }

        # Already suspended, no action needed
        elif tenant.subscription_status == 'suspended':
            print(f"   ℹ️  Already suspended, monitoring for day 30")
            print()
            return None

        # Within grace period, no action needed
        else:
            print(f"   ⏳ Within grace period, no action needed")
            print()
            return None

    except Exception as e:
        print(f"❌ {tenant.business_name}: Error - {e}\n")
        return {
            'tenant_id': tenant.id,
            'business_name': tenant.business_name,
            'action': 'error',
            'error': str(e)
        }


if __name__ == '__main__':
    """
    Run from command line:
        python -m jobs.dunning_check
        python -m jobs.dunning_check --dry-run
    """
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv

    summary = run_dunning_check(dry_run=dry_run)

    # Exit with error code if there were errors
    if summary.get('errors', 0) > 0 or summary.get('fatal_error'):
        sys.exit(1)
    else:
        sys.exit(0)
