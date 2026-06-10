# Runbook: Rotate Gmail App Password (IMAP credentials)

**Triggered by:** orchestrator IMAP step failing with `AUTHENTICATIONFAILED Invalid credentials`.
**Last incident:** 2026-04-24 19:00 PT (per `_logs/broker_ops/orchestrator.log` line "STEP 8b: Checking for replies to outreach... IMAP login failed").
**Owner:** Marquise (Google account holder). 5-minute fix.

---

## Why this matters

Even if cron resurrects, **inbound seller-reply detection stays broken** until IMAP creds are rotated. Plan v3 Wave 1 cannot rely on the orchestrator's reply-loop until this is fixed. Otherwise we'd send cold emails and miss every reply -- exactly the silent-failure pattern Charles Dawson's Operator Truth role exists to catch.

This is a 5-minute fix. Do this before bringing crons back.

---

## Steps

### 1. Sign in to Google account

- Browser: https://myaccount.google.com
- Account: 1m.rich.gee@gmail.com (per workspace context).

### 2. Generate a new App Password

- Navigate to: **Security** > **2-Step Verification** > **App passwords**
  - Direct URL: https://myaccount.google.com/apppasswords
- App name: `Everlight Hive IMAP 2026-04`
- Click **Create**. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`).

> If "App passwords" is not visible: 2-Step Verification must be ON. Enable it first via https://myaccount.google.com/signinoptions/two-step-verification

### 3. Update credential in workspace

The IMAP password lives in `03_Credentials/.env` per memory `credentials_map.md`. Edit:

```bash
# Find the line:
GMAIL_APP_PASSWORD=<old-16-char-password>

# Replace with new value (no spaces):
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
```

Also update on Oracle once Oracle is reachable:

```bash
ssh oracle-e5 'sed -i "s/GMAIL_APP_PASSWORD=.*/GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx/" /home/opc/.env'
```

### 4. Verify

```bash
cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts
python3 -c "
import imaplib, os
from dotenv import load_dotenv
load_dotenv('/mnt/sdcard/AA_MY_DRIVE/03_Credentials/.env')
m = imaplib.IMAP4_SSL('imap.gmail.com')
m.login('1m.rich.gee@gmail.com', os.environ['GMAIL_APP_PASSWORD'])
print('IMAP login: OK')
m.select('INBOX')
print('INBOX selected')
m.logout()
"
```

Expected output:
```
IMAP login: OK
INBOX selected
```

If you see `b'[AUTHENTICATIONFAILED] Invalid credentials'` again, the new password did not save correctly to `.env`. Re-paste, no quotes, no spaces.

### 5. Revoke the old password

Back at https://myaccount.google.com/apppasswords -- find the previous "Everlight Hive IMAP" entry, **Remove**. Reduces blast radius if the old password leaked.

### 6. Confirm in audit log

```bash
echo "$(date -Iseconds): Gmail app password rotated. New entry: Everlight Hive IMAP 2026-04" >> /mnt/sdcard/AA_MY_DRIVE/_logs/credentials_rotation.log
```

This creates a paper trail for SOC 2 posture work later (Move D Deal-2 unlock).

---

## After this fix

Once IMAP works again, the inbound-watch daemon (`01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/inbound_watch_daemon.py`) can poll for replies. Replies trigger:

- Status update on `PropertyLead.status` (warm)
- Slack post to `#wholesale-deals` with reply preview
- Kickoff for hive_deal_orchestrator next step

This is required infra for Penny's 30-day commit (3 signed PSAs in pipeline). Without inbound-reply detection, even successful cold outreach goes silent.

---

## Self-heal recipe (Wave 2 add to plan v3 Move C)

Future state: `hive_self_heal.service` recipe `imap_auth_rotation` detects `AUTHENTICATIONFAILED` in orchestrator log within 5 minutes, posts to `#hive-alerts` with this runbook URL, and pages Marquise. Until that recipe ships, this is a manual-pull task on log monitoring.
