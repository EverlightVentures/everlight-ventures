"""
Trial Reminder Job
Runs daily to send trial expiring reminders

Reminder Schedule:
- 3 days before trial ends: Send reminder email
- 1 day before trial ends: Send final reminder
- Trial ends: Status handled by webhook
"""
from datetime import datetime, timedelta
from database import Session
from models import Tenant
from services.email import send_trial_expiring_email
import sys


def run_trial_reminders(dry_run=False):
    """
    Send trial expiring reminders

    Args:
        dry_run: If True, report but don't send emails

    Returns:
        dict: Summary of reminders sent
    """
    print("\n" + "=" * 60)
    print("  OnyxPOS Trial Reminder Check")
    print(f"  Run Date: {datetime.utcnow().isoformat()}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60 + "\n")

    db = Session()
    summary = {
        'trial_tenants': 0,
        'reminders_sent': 0,
        'errors': 0,
        'results': []
    }

    try:
        # Get all tenants in trial
        tenants = db.query(Tenant).filter(
            Tenant.subscription_status == 'trial',
            Tenant.trial_ends_at != None
        ).all()

        summary['trial_tenants'] = len(tenants)
        print(f"Found {len(tenants)} tenants in trial\n")

        for tenant in tenants:
            result = process_trial_reminder(tenant, dry_run)
            if result:
                summary['results'].append(result)
                if result['sent']:
                    summary['reminders_sent'] += 1
                if result.get('error'):
                    summary['errors'] += 1

        # Print summary
        print("\n" + "=" * 60)
        print("  Trial Reminder Summary")
        print("=" * 60)
        print(f"  Trial Tenants:      {summary['trial_tenants']}")
        print(f"  Reminders Sent:     {summary['reminders_sent']}")
        print(f"  Errors:             {summary['errors']}")
        print("=" * 60 + "\n")

        return summary

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        summary['fatal_error'] = str(e)
        return summary

    finally:
        db.close()


def process_trial_reminder(tenant, dry_run):
    """
    Check if tenant needs trial reminder

    Args:
        tenant: Tenant model instance
        dry_run: Boolean

    Returns:
        dict: Result or None if no reminder needed
    """
    try:
        days_remaining = tenant.trial_days_remaining

        # Send reminder at 3 days and 1 day
        if days_remaining in [3, 1]:
            print(f"⏰ {tenant.business_name}: Trial ends in {days_remaining} day(s)")

            if not dry_run:
                send_trial_expiring_email(tenant, days_remaining)
                print(f"   ✉️  Reminder sent to {tenant.owner_email}")
            else:
                print(f"   📧 Would send reminder to {tenant.owner_email}")

            print()

            return {
                'tenant_id': tenant.id,
                'business_name': tenant.business_name,
                'days_remaining': days_remaining,
                'sent': not dry_run
            }

        return None

    except Exception as e:
        print(f"❌ {tenant.business_name}: Error - {e}\n")
        return {
            'tenant_id': tenant.id,
            'business_name': tenant.business_name,
            'error': str(e),
            'sent': False
        }


if __name__ == '__main__':
    """
    Run from command line:
        python -m jobs.trial_reminders
        python -m jobs.trial_reminders --dry-run
    """
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    summary = run_trial_reminders(dry_run=dry_run)

    if summary.get('errors', 0) > 0 or summary.get('fatal_error'):
        sys.exit(1)
    else:
        sys.exit(0)
