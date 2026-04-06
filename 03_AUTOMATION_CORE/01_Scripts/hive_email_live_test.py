#!/usr/bin/env python3
"""
Hive Mind Email Live Test -- Resend API
Sends test emails FROM each of the 40 AI employees using Resend.
Verifies delivery to admin inbox.

Usage:
    python3 hive_email_live_test.py --dry-run          # Preview all emails
    python3 hive_email_live_test.py --send-only         # Send all 40, skip verify
    python3 hive_email_live_test.py                     # Send + verify after 60s delay
    python3 hive_email_live_test.py --verify-only ID    # Check receipt for previous test
    python3 hive_email_live_test.py --report            # Show latest report
    python3 hive_email_live_test.py --delay 120         # Custom verify delay (seconds)
"""

import argparse
import json
import os
import sys
import time
import imaplib
import email as email_lib
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENV_PATH = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
CONFIG_PATH = "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/email_config.yaml"
REPORT_DIR = "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports"
LOG_PATH = "/mnt/sdcard/AA_MY_DRIVE/_logs/hive_email_live_test.log"

RESEND_API_URL = "https://api.resend.com/emails"
TEST_RECIPIENT = "admin@everlightventures.io"
TEST_PREFIX = "[HIVE-LIVE-TEST]"

# Gmail IMAP settings for verification
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_env():
    """Load .env file into dict."""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    return env


def load_config():
    """Load employee email config from YAML."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def log(msg):
    """Log to console and file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S PT")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Send via Resend API
# ---------------------------------------------------------------------------
def send_test_email(api_key, from_email, from_name, to_email, subject, body, signature):
    """Send one email via Resend HTTP API. Returns (status_code, response_json)."""
    html_body = f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
{body}
<br>
<p style="color: #666; border-top: 1px solid #ddd; padding-top: 10px;">
--<br>
{signature}
</p>
</div>"""

    resp = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        },
        timeout=15,
    )
    return resp.status_code, resp.json()


def run_send(config, api_key, dry_run=False):
    """Send test emails from all employees. Returns (test_id, results_list)."""
    employees = config.get("employees", {})
    test_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results = []

    log(f"{'DRY RUN -- ' if dry_run else ''}Starting live email test: {test_id}")
    log(f"Sending FROM each employee TO {TEST_RECIPIENT}")
    log(f"Testing {len(employees)} employees...\n")

    for emp_key, emp in employees.items():
        emp_email = emp["email"]
        emp_name = emp["name"]
        dept = emp.get("department", "unknown")
        title = emp.get("title", "")
        sig = emp.get("signature", f"{emp_name} | Everlight Ventures")

        subject = f"{TEST_PREFIX} {test_id} -- from {emp_name} ({emp_key})"
        body = (
            f"<p>This is an automated Hive Mind email delivery test.</p>"
            f"<table style='border-collapse:collapse; margin:10px 0;'>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Employee:</td>"
            f"<td>{emp_name}</td></tr>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Title:</td>"
            f"<td>{title}</td></tr>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Address:</td>"
            f"<td><code>{emp_email}</code></td></tr>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Department:</td>"
            f"<td>{dept}</td></tr>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Test ID:</td>"
            f"<td><code>{test_id}</code></td></tr>"
            f"<tr><td style='padding:2px 10px 2px 0; font-weight:bold;'>Timestamp:</td>"
            f"<td>{datetime.now(timezone.utc).isoformat()}</td></tr>"
            f"</table>"
            f"<p>If you received this, send-as is working for "
            f"<code>{emp_email}</code>.</p>"
        )

        result = {
            "employee": emp_key,
            "name": emp_name,
            "email": emp_email,
            "department": dept,
            "title": title,
            "test_id": test_id,
        }

        if dry_run:
            log(f"  [DRY] {emp_email:40s} {emp_name} ({title})")
            result["status"] = "dry_run"
        else:
            try:
                status_code, resp = send_test_email(
                    api_key, emp_email, emp_name, TEST_RECIPIENT,
                    subject, body, sig
                )
                if status_code in (200, 201):
                    log(f"  OK    {emp_email:40s} {emp_name}")
                    result["status"] = "sent"
                    result["resend_id"] = resp.get("id", "")
                else:
                    log(f"  FAIL  {emp_email:40s} {emp_name} -- {status_code}: {resp}")
                    result["status"] = "failed"
                    result["error"] = str(resp)
            except Exception as e:
                log(f"  ERR   {emp_email:40s} {emp_name} -- {e}")
                result["status"] = "error"
                result["error"] = str(e)

            # Rate limit -- Resend free tier is 100 emails/day, ~1/sec
            time.sleep(1.1)

        results.append(result)

    save_report(results, test_id)

    sent = sum(1 for r in results if r["status"] == "sent")
    failed = sum(1 for r in results if r["status"] in ("failed", "error"))
    dry = sum(1 for r in results if r["status"] == "dry_run")
    log(f"\nDone. Sent: {sent}, Failed: {failed}, Dry: {dry}, Total: {len(results)}")
    log(f"Test ID: {test_id}")
    log(f"Report: {REPORT_DIR}/hive_live_test_{test_id}.json")

    return test_id, results


# ---------------------------------------------------------------------------
# Gmail IMAP verification
# ---------------------------------------------------------------------------
def verify_receipt_imap(env, test_id, expected_employees):
    """
    Connect to Gmail IMAP inbox and search for test emails by test_id.
    Returns dict mapping employee_key -> True/False.
    """
    imap_user = env.get("GMAIL_IMAP_USER", "1m.rich.gee@gmail.com")
    imap_pass = env.get("GMAIL_APP_PASSWORD", "")

    if not imap_pass:
        log("WARNING: GMAIL_APP_PASSWORD not set in .env -- skipping IMAP verification.")
        log("To enable, add GMAIL_APP_PASSWORD=<your-app-password> to .env")
        log("Generate one at: https://myaccount.google.com/apppasswords")
        return None

    log(f"Connecting to Gmail IMAP as {imap_user}...")
    found = {}

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX")

        # Search for emails with our test prefix + test_id in subject
        search_query = f'(SUBJECT "{TEST_PREFIX} {test_id}")'
        status, data = mail.search(None, search_query)

        if status != "OK":
            log(f"IMAP search failed: {status}")
            mail.logout()
            return None

        msg_ids = data[0].split()
        log(f"Found {len(msg_ids)} matching emails in inbox.")

        for msg_id in msg_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            subj = msg.get("Subject", "")
            from_addr = msg.get("From", "")

            # Extract employee key from subject: "... -- from Name (key)"
            for emp_key in expected_employees:
                if f"({emp_key})" in subj:
                    found[emp_key] = True
                    break

        mail.logout()

    except imaplib.IMAP4.error as e:
        log(f"IMAP error: {e}")
        return None
    except Exception as e:
        log(f"IMAP connection error: {e}")
        return None

    return found


def run_verify(env, test_id, config):
    """Run IMAP verification for a given test_id and update the report."""
    employees = config.get("employees", {})
    emp_keys = list(employees.keys())

    found = verify_receipt_imap(env, test_id, emp_keys)
    if found is None:
        log("Verification skipped -- no IMAP credentials or connection failed.")
        return

    received = 0
    missing = 0
    for key in emp_keys:
        emp = employees[key]
        if found.get(key):
            received += 1
        else:
            missing += 1
            log(f"  MISS  {emp['email']:40s} {emp['name']} -- not found in inbox")

    log(f"\nVerification: {received}/{len(emp_keys)} received, {missing} missing")

    # Update report file if it exists
    report_path = os.path.join(REPORT_DIR, f"hive_live_test_{test_id}.json")
    if os.path.exists(report_path):
        with open(report_path) as f:
            report = json.load(f)

        report["verification"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "received": received,
            "missing": missing,
            "total": len(emp_keys),
            "details": {k: found.get(k, False) for k in emp_keys},
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Also update latest
        latest = os.path.join(REPORT_DIR, "hive_live_test_latest.json")
        with open(latest, "w") as f:
            json.dump(report, f, indent=2)

        log(f"Report updated: {report_path}")


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def save_report(results, test_id):
    """Save test results to JSON report."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Group by department for summary
    by_dept = {}
    for r in results:
        d = r.get("department", "unknown")
        if d not in by_dept:
            by_dept[d] = {"sent": 0, "failed": 0, "dry_run": 0}
        by_dept[d][r["status"]] = by_dept[d].get(r["status"], 0) + 1

    report = {
        "test_id": test_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recipient": TEST_RECIPIENT,
        "total": len(results),
        "sent": sum(1 for r in results if r["status"] == "sent"),
        "failed": sum(1 for r in results if r["status"] in ("failed", "error")),
        "dry_run": sum(1 for r in results if r["status"] == "dry_run"),
        "by_department": by_dept,
        "results": results,
    }

    path = os.path.join(REPORT_DIR, f"hive_live_test_{test_id}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)

    # Also save as latest
    latest = os.path.join(REPORT_DIR, "hive_live_test_latest.json")
    with open(latest, "w") as f:
        json.dump(report, f, indent=2)


def show_report():
    """Show latest test report in a readable format."""
    latest = os.path.join(REPORT_DIR, "hive_live_test_latest.json")
    if not os.path.exists(latest):
        log("No test reports found.")
        return

    with open(latest) as f:
        data = json.load(f)

    log(f"\n{'=' * 65}")
    log(f"HIVE MIND LIVE EMAIL TEST REPORT")
    log(f"{'=' * 65}")
    log(f"Test ID:    {data['test_id']}")
    log(f"Timestamp:  {data['timestamp']}")
    log(f"Recipient:  {data.get('recipient', TEST_RECIPIENT)}")
    log(f"Total:      {data['total']}")
    log(f"Sent:       {data.get('sent', 0)}")
    log(f"Failed:     {data.get('failed', 0)}")
    log(f"Dry run:    {data.get('dry_run', 0)}")
    log(f"{'-' * 65}")

    # Department breakdown
    by_dept = data.get("by_department", {})
    if by_dept:
        log(f"\nBy Department:")
        for dept, counts in sorted(by_dept.items()):
            total = sum(counts.values())
            sent = counts.get("sent", 0)
            failed = counts.get("failed", 0) + counts.get("error", 0)
            dry = counts.get("dry_run", 0)
            status = f"sent={sent}" if sent else f"dry={dry}" if dry else f"failed={failed}"
            log(f"  {dept:25s} {total:3d} employees -- {status}")

    # Verification results
    verif = data.get("verification")
    if verif:
        log(f"\nIMPA Verification:")
        log(f"  Received: {verif['received']}/{verif['total']}")
        log(f"  Missing:  {verif['missing']}")
        if verif["missing"] > 0:
            details = verif.get("details", {})
            missing_list = [k for k, v in details.items() if not v]
            for k in missing_list:
                log(f"    X {k}")

    # Show failures
    failures = [r for r in data["results"] if r["status"] in ("failed", "error")]
    if failures:
        log(f"\nFailures ({len(failures)}):")
        for item in failures:
            err = item.get("error", item["status"])
            log(f"  X {item['email']:40s} {item['name']} -- {err}")

    log(f"{'=' * 65}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hive Mind Live Email Test -- Resend API + Gmail IMAP"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview all emails without sending"
    )
    parser.add_argument(
        "--send-only", action="store_true",
        help="Send all emails, skip IMAP verification"
    )
    parser.add_argument(
        "--verify-only", metavar="TEST_ID",
        help="Only verify receipt for a previous test ID"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Show the latest test report"
    )
    parser.add_argument(
        "--delay", type=int, default=60,
        help="Seconds to wait before IMAP verification (default: 60)"
    )
    args = parser.parse_args()

    # Report mode -- just show results and exit
    if args.report:
        show_report()
        return

    env = load_env()
    config = load_config()
    api_key = env.get("RESEND_API_KEY")

    # Verify-only mode -- check inbox for a previous test
    if args.verify_only:
        log(f"Verify-only mode for test ID: {args.verify_only}")
        run_verify(env, args.verify_only, config)
        show_report()
        return

    # Require API key for actual sends
    if not api_key and not args.dry_run:
        log("ERROR: RESEND_API_KEY not found in .env")
        log(f"Expected in: {ENV_PATH}")
        sys.exit(1)

    # Validate config
    employees = config.get("employees", {})
    if not employees:
        log("ERROR: No employees found in config.")
        log(f"Config path: {CONFIG_PATH}")
        sys.exit(1)

    log(f"Loaded {len(employees)} employees from config.")

    # Send phase
    test_id, results = run_send(config, api_key, dry_run=args.dry_run)

    if args.dry_run:
        log(f"\nDry run complete. No emails sent.")
        log(f"Run without --dry-run to send for real.")
        return

    if args.send_only:
        log(f"\nSend-only mode -- skipping verification.")
        log(f"To verify later: python3 {__file__} --verify-only {test_id}")
        return

    # Verify phase -- wait, then check inbox
    sent_count = sum(1 for r in results if r["status"] == "sent")
    if sent_count == 0:
        log("No emails were sent successfully -- skipping verification.")
        return

    log(f"\nWaiting {args.delay}s for delivery before IMAP check...")
    time.sleep(args.delay)

    run_verify(env, test_id, config)
    show_report()


if __name__ == "__main__":
    main()
