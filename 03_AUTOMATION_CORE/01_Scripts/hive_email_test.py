#!/usr/bin/env python3
"""
Hive Mind Email Infrastructure -- End-to-End Test
Tests send/receive for all 40 AI employee email addresses.

Usage:
    python3 hive_email_test.py --mode forwarding    # Test email forwarding
    python3 hive_email_test.py --mode smtp           # Test SMTP send-as
    python3 hive_email_test.py --report              # Show last test results
"""

import argparse
import yaml
import json
import os
import sys
import time
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path

# Paths
CONFIG_PATH = "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/email_config.yaml"
REPORT_PATH = "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports/hive_email_test_report.json"
LOG_PATH = "/mnt/sdcard/AA_MY_DRIVE/_logs/hive_email_test.log"

# Test email subject prefix (for easy filtering)
TEST_PREFIX = "[HIVE-EMAIL-TEST]"


def load_config():
    """Load employee email config from YAML."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def log(msg):
    """Log to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S PT")
    line = f"[{timestamp}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def test_forwarding(config, sender_email=None, sender_password=None, smtp_host=None, smtp_port=None):
    """
    Test forwarding mode: send an email TO each employee address
    and verify it arrives at admin@everlightventures.io.

    Requires a real email account to send from (your personal/admin account).
    """
    employees = config.get("employees", {})
    results = []
    test_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if not sender_email:
        sender_email = os.environ.get("HIVE_TEST_SENDER_EMAIL")
    if not sender_password:
        sender_password = os.environ.get("HIVE_TEST_SENDER_PASSWORD")
    if not smtp_host:
        smtp_host = os.environ.get("HIVE_TEST_SMTP_HOST", "smtp.gmail.com")
    if not smtp_port:
        smtp_port = int(os.environ.get("HIVE_TEST_SMTP_PORT", "587"))

    if not sender_email or not sender_password:
        log("ERROR: Set HIVE_TEST_SENDER_EMAIL and HIVE_TEST_SENDER_PASSWORD env vars")
        log("These should be your admin Gmail + app password")
        return []

    log(f"Starting forwarding test batch: {test_id}")
    log(f"Sending from: {sender_email}")
    log(f"SMTP: {smtp_host}:{smtp_port}")
    log(f"Testing {len(employees)} employee addresses...")
    log("")

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
    except Exception as e:
        log(f"SMTP connection failed: {e}")
        return []

    for emp_key, emp_data in employees.items():
        emp_email = emp_data["email"]
        emp_name = emp_data["name"]
        dept = emp_data["department"]

        subject = f"{TEST_PREFIX} {test_id} -- {emp_name} ({emp_key})"
        body = f"""Hive Mind Email Test

Employee: {emp_name}
Address: {emp_email}
Department: {dept}
Test ID: {test_id}
Timestamp: {datetime.now(timezone.utc).isoformat()}

This is an automated test to verify email forwarding is working.
If you received this at admin@everlightventures.io, forwarding works for {emp_email}.
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = emp_email
        msg["X-Hive-Test-ID"] = test_id
        msg["X-Hive-Employee"] = emp_key

        try:
            server.send_message(msg)
            status = "sent"
            log(f"  SENT -> {emp_email} ({emp_name})")
        except Exception as e:
            status = "send_failed"
            log(f"  FAIL -> {emp_email} ({emp_name}): {e}")

        results.append({
            "employee": emp_key,
            "name": emp_name,
            "email": emp_email,
            "department": dept,
            "send_status": status,
            "receive_status": "pending",
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    server.quit()
    log(f"\nAll {len(results)} test emails sent. Test ID: {test_id}")
    log(f"Wait 2-5 minutes, then run: python3 {sys.argv[0]} --verify {test_id}")

    # Save intermediate results
    save_report(results, test_id)
    return results


def verify_delivery(config, test_id, imap_email=None, imap_password=None, imap_host=None):
    """
    Check admin inbox for forwarded test emails.
    Matches by test_id in subject line.
    """
    if not imap_email:
        imap_email = os.environ.get("HIVE_TEST_SENDER_EMAIL")
    if not imap_password:
        imap_password = os.environ.get("HIVE_TEST_SENDER_PASSWORD")
    if not imap_host:
        imap_host = os.environ.get("HIVE_TEST_IMAP_HOST", "imap.gmail.com")

    if not imap_email or not imap_password:
        log("ERROR: Set HIVE_TEST_SENDER_EMAIL and HIVE_TEST_SENDER_PASSWORD env vars")
        return

    log(f"Verifying delivery for test batch: {test_id}")

    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_email, imap_password)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP connection failed: {e}")
        return

    # Search for test emails
    search_query = f'SUBJECT "{TEST_PREFIX} {test_id}"'
    _, message_numbers = mail.search(None, search_query)

    received_employees = set()
    for num in message_numbers[0].split():
        _, msg_data = mail.fetch(num, "(BODY[HEADER.FIELDS (SUBJECT)])")
        if msg_data[0] is not None:
            header = msg_data[0][1].decode()
            # Extract employee key from subject
            for emp_key in config.get("employees", {}).keys():
                if f"({emp_key})" in header:
                    received_employees.add(emp_key)

    mail.logout()

    # Load previous results and update
    report = load_report(test_id)
    if not report:
        log(f"No report found for test {test_id}")
        return

    passed = 0
    failed = 0
    for result in report:
        if result["employee"] in received_employees:
            result["receive_status"] = "received"
            passed += 1
        else:
            result["receive_status"] = "not_received"
            failed += 1

    save_report(report, test_id)

    log(f"\n{'='*60}")
    log(f"VERIFICATION RESULTS -- Test {test_id}")
    log(f"{'='*60}")
    log(f"Total employees: {len(report)}")
    log(f"Emails received:  {passed}")
    log(f"Emails missing:   {failed}")
    log(f"Success rate:     {passed}/{len(report)} ({100*passed//max(len(report),1)}%)")
    log(f"{'='*60}")

    if failed > 0:
        log("\nFAILED FORWARDING:")
        for r in report:
            if r["receive_status"] == "not_received":
                log(f"  X {r['email']} ({r['name']})")

    log(f"\nFull report: {REPORT_PATH}")


def test_smtp_sendas(config, smtp_host=None, smtp_port=None, smtp_user=None, smtp_password=None):
    """
    Test SMTP send-as mode for tier 1/2 agents.
    Requires SMTP credentials that allow sending as employee addresses.
    """
    send_as = config.get("send_as_priority", {})
    tier1 = send_as.get("tier_1_must_send", [])
    tier2 = send_as.get("tier_2_should_send", [])
    test_agents = tier1 + tier2

    employees = config.get("employees", {})
    admin_email = config.get("master_inbox", "admin@everlightventures.io")

    if not smtp_user:
        smtp_user = os.environ.get("HIVE_SMTP_USER")
    if not smtp_password:
        smtp_password = os.environ.get("HIVE_SMTP_PASSWORD")
    if not smtp_host:
        smtp_host = os.environ.get("HIVE_SMTP_HOST", "mail.privateemail.com")
    if not smtp_port:
        smtp_port = int(os.environ.get("HIVE_SMTP_PORT", "587"))

    if not smtp_user or not smtp_password:
        log("ERROR: Set HIVE_SMTP_USER and HIVE_SMTP_PASSWORD env vars")
        log("These should be your Namecheap Private Email or domain email creds")
        return []

    test_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results = []

    log(f"Starting SMTP send-as test batch: {test_id}")
    log(f"Testing {len(test_agents)} tier 1/2 agents...")

    for emp_key in test_agents:
        if emp_key not in employees:
            log(f"  SKIP -- {emp_key} not in employee config")
            continue

        emp = employees[emp_key]
        emp_email = emp["email"]
        emp_name = emp["name"]
        signature = emp.get("signature", "")

        subject = f"{TEST_PREFIX} SMTP {test_id} -- from {emp_name}"
        body = f"""This email was sent AS {emp_name} ({emp_email}).

If you see this in admin inbox with the correct From address,
SMTP send-as is working for this agent.

--
{signature}
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = f"{emp_name} <{emp_email}>"
        msg["To"] = admin_email
        msg["Reply-To"] = emp_email

        try:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            status = "sent"
            log(f"  SENT as {emp_email} ({emp_name})")
        except Exception as e:
            status = "send_failed"
            log(f"  FAIL as {emp_email} ({emp_name}): {e}")

        results.append({
            "employee": emp_key,
            "name": emp_name,
            "email": emp_email,
            "department": emp.get("department", ""),
            "send_as_status": status,
            "test_id": test_id,
            "tier": "tier_1" if emp_key in tier1 else "tier_2"
        })

        time.sleep(1)

    save_report(results, f"smtp_{test_id}")
    log(f"\nSMTP test complete. Report: {REPORT_PATH}")
    return results


def save_report(results, test_id):
    """Save test results to JSON report."""
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    report_file = REPORT_PATH.replace(".json", f"_{test_id}.json")
    with open(report_file, "w") as f:
        json.dump({
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(results),
            "results": results
        }, f, indent=2)

    # Also save as latest
    with open(REPORT_PATH, "w") as f:
        json.dump({
            "test_id": test_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(results),
            "results": results
        }, f, indent=2)


def load_report(test_id):
    """Load a test report by ID."""
    report_file = REPORT_PATH.replace(".json", f"_{test_id}.json")
    if os.path.exists(report_file):
        with open(report_file, "r") as f:
            data = json.load(f)
            return data.get("results", [])
    return None


def show_report():
    """Display the latest test report."""
    if not os.path.exists(REPORT_PATH):
        log("No test reports found. Run a test first.")
        return

    with open(REPORT_PATH, "r") as f:
        data = json.load(f)

    log(f"\n{'='*60}")
    log(f"LATEST TEST REPORT -- {data['test_id']}")
    log(f"Timestamp: {data['timestamp']}")
    log(f"Total employees tested: {data['total']}")
    log(f"{'='*60}")

    by_dept = {}
    for r in data["results"]:
        dept = r.get("department", "unknown")
        if dept not in by_dept:
            by_dept[dept] = {"passed": 0, "failed": 0, "pending": 0}

        status = r.get("receive_status", r.get("send_as_status", "unknown"))
        if status in ("received", "sent"):
            by_dept[dept]["passed"] += 1
        elif status in ("not_received", "send_failed"):
            by_dept[dept]["failed"] += 1
        else:
            by_dept[dept]["pending"] += 1

    for dept, counts in by_dept.items():
        total = counts["passed"] + counts["failed"] + counts["pending"]
        log(f"\n{dept}:")
        log(f"  Passed:  {counts['passed']}/{total}")
        log(f"  Failed:  {counts['failed']}/{total}")
        log(f"  Pending: {counts['pending']}/{total}")

    # Show failures
    failures = [r for r in data["results"]
                if r.get("receive_status") == "not_received"
                or r.get("send_as_status") == "send_failed"]
    if failures:
        log(f"\nFAILURES ({len(failures)}):")
        for f_item in failures:
            log(f"  X {f_item['email']} -- {f_item['name']}")


def dns_check():
    """Quick DNS check for the domain's MX records."""
    log("Checking DNS MX records for everlightventures.io...")
    try:
        import subprocess
        result = subprocess.run(
            ["dig", "+short", "MX", "everlightventures.io"],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            log(f"MX records found:\n{result.stdout}")
        else:
            log("WARNING: No MX records found. Email forwarding may not work.")
            log("Set up MX records in Namecheap DNS or enable email forwarding.")
    except FileNotFoundError:
        # Try nslookup if dig not available
        try:
            result = subprocess.run(
                ["nslookup", "-type=MX", "everlightventures.io"],
                capture_output=True, text=True, timeout=10
            )
            log(result.stdout)
        except FileNotFoundError:
            log("Neither dig nor nslookup available. Skipping DNS check.")
    except Exception as e:
        log(f"DNS check failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Hive Mind Email Test Suite")
    parser.add_argument("--mode", choices=["forwarding", "smtp"], default="forwarding",
                        help="Test mode: forwarding (default) or smtp send-as")
    parser.add_argument("--verify", metavar="TEST_ID",
                        help="Verify delivery for a previous test batch")
    parser.add_argument("--report", action="store_true",
                        help="Show latest test report")
    parser.add_argument("--dns", action="store_true",
                        help="Check DNS MX records")
    parser.add_argument("--dry-run", action="store_true",
                        help="List all emails without sending")

    args = parser.parse_args()

    config = load_config()

    if args.dns:
        dns_check()
        return

    if args.report:
        show_report()
        return

    if args.verify:
        verify_delivery(config, args.verify)
        return

    if args.dry_run:
        employees = config.get("employees", {})
        log(f"\nDRY RUN -- {len(employees)} employee emails:\n")
        for emp_key, emp_data in employees.items():
            auto = "AUTO-REPLY" if emp_data.get("auto_reply") else ""
            log(f"  {emp_data['email']:40s} {emp_data['name']:20s} {emp_data['department']:20s} {auto}")

        log(f"\nGroup aliases:")
        for alias_key, alias_data in config.get("group_aliases", {}).items():
            log(f"  {alias_data['email']:40s} -> {len(alias_data['members'])} members")

        log(f"\nSend-as priority:")
        for tier, agents in config.get("send_as_priority", {}).items():
            log(f"  {tier}: {', '.join(agents)}")
        return

    if args.mode == "forwarding":
        test_forwarding(config)
    elif args.mode == "smtp":
        test_smtp_sendas(config)


if __name__ == "__main__":
    main()
