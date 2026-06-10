# MFA Setup Guide -- Django Dashboard (`:8504`)

The dashboard currently uses Django's default password authentication. For a wholesale operation handling property contracts, EMD records, and consumer PII, MFA on staff accounts is the audit-required minimum.

## 1-hour install plan

### Step 1: install on Oracle

```bash
ssh -F /root/.ssh/config oracle-bot
cd /home/opc/hive_django
pip install --user django-otp qrcode
```

### Step 2: settings.py

```python
INSTALLED_APPS += ['django_otp', 'django_otp.plugins.otp_totp']
MIDDLEWARE += ['django_otp.middleware.OTPMiddleware']  # AFTER AuthMW
OTP_TOTP_ISSUER = "Everlight Ventures"
```

### Step 3: migrate + admin override

```bash
python3 manage.py migrate django_otp
```

In `hive/admin.py`:
```python
from django_otp.admin import OTPAdminSite
admin.site.__class__ = OTPAdminSite
```

### Step 4: enroll Rich's account

1. Restart Django: `sudo systemctl restart hive-django`
2. Visit `:8504/admin/` -- expect MFA lockout
3. CLI: `python3 manage.py addstatictoken admin --token 12345678 --token 87654321`
4. Login with static token, enroll TOTP device at `/admin/otp_totp/totpdevice/add/`
5. Burn the static tokens

### Step 5: enforce on all future staff

Every Django staff account must enroll TOTP within 24h of creation. Documented in CODE_OF_CONDUCT.md as a hiring requirement.

## Why we have not flipped this on yet

Flagged HIGH in wholesale audit. On next-week shortlist. Until we add a second staff member the practical risk is bounded (Rich = only admin from his devices). The moment a VA or contractor joins, MFA enforcement goes in the same hour.

_Owner: Rich. Effort: 1 hour. Trigger: before first VA hire OR within 30 days, whichever first._
