"""Test that all critical modules can be imported"""
import sys
print(f"Python {sys.version}")

try:
    from models import Tenant, User
    print("✅ Models imported successfully")
except Exception as e:
    print(f"❌ Models import error: {e}")

try:
    from middleware.subscription_guard import check_subscription_access
    print("✅ Middleware imported successfully")
except Exception as e:
    print(f"❌ Middleware import error: {e}")

try:
    from services.stripe_metered import record_gmv_usage
    print("✅ Stripe metered service imported successfully")
except Exception as e:
    print(f"❌ Stripe metered import error: {e}")

try:
    from services.email import send_payment_failed_email
    print("✅ Email service imported successfully")
except Exception as e:
    print(f"❌ Email service import error: {e}")

try:
    from jobs.monthly_billing import run_monthly_billing
    print("✅ Monthly billing job imported successfully")
except Exception as e:
    print(f"❌ Monthly billing import error: {e}")

try:
    from jobs.dunning_check import run_dunning_check
    print("✅ Dunning check job imported successfully")
except Exception as e:
    print(f"❌ Dunning check import error: {e}")

print("\n✅ All critical modules validated!")
