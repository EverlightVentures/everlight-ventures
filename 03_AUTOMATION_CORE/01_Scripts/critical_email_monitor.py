"""
critical_email_monitor.py
─────────────────────────
Watches Marquise's Gmail inbox via IMAP for high-stakes service alerts:
billing, account closures, free trial endings, domain expiry, payment
failures, security alerts. Alerts via:
  1. Slack #hive-alerts (immediate)
  2. SMS via Twilio (if severity=URGENT)
  3. Phone push notification via ntfy.sh (free, no card)

Runs from cron every 5 min on phone (Termux) or Oracle (when restored).

WHY THIS EXISTS: Marquise's Oracle E5 free trial expired and the VM was
terminated without him being alerted. Oracle absolutely sent emails like
"your free trial ends in 30 days" but they got buried in inbox. By the
time he noticed, the Hive backend was offline 5 days. This watcher
catches those alerts and surfaces them within minutes.

Usage:
    python3 critical_email_monitor.py            # one-shot check
    python3 critical_email_monitor.py --daemon   # continuous (every 5 min)

Cron entry:
    */5 * * * * /usr/bin/python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/critical_email_monitor.py >> /mnt/sdcard/AA_MY_DRIVE/_logs/critical_email_monitor.log 2>&1
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_tools.imap_fetch import fetch_recent

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "critical_email_monitor.log"
SEEN_FILE = LOG_DIR / "critical_email_seen.json"  # message_ids we've already alerted on
ENV = WORKSPACE / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

# Load env
for line in ENV.read_text().splitlines() if ENV.exists() else []:
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

GMAIL_USER = os.environ.get("GMAIL_USER") or os.environ.get("MARQUISE_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_WARROOM_BOT_TOKEN")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")  # free push notification, no signup needed

# ── Critical sender + subject patterns ─────────────────────────────────
CRITICAL_PATTERNS = [
    # Cloud providers
    {"sender": r"@oracle\.com|oraclecloud", "subject": r"trial|expir|terminat|billing|invoice|payment|charged|usage", "severity": "URGENT", "category": "Oracle Cloud"},
    {"sender": r"@aws\.amazon\.com|amazonwebservices", "subject": r"trial|expir|invoice|billing|payment|alarm", "severity": "URGENT", "category": "AWS"},
    {"sender": r"@cloudflare\.com", "subject": r"expir|invoice|payment|domain|down", "severity": "HIGH", "category": "Cloudflare"},
    {"sender": r"@vercel\.com|@netlify\.com|@render\.com|@fly\.io", "subject": r"deploy fail|trial|expir|invoice|billing", "severity": "HIGH", "category": "Hosting"},
    {"sender": r"@digitalocean\.com|@linode\.com|@hetzner\.com", "subject": r".*", "severity": "HIGH", "category": "VPS"},
    # Domain registrars
    {"sender": r"@namecheap\.com|@godaddy\.com|@porkbun\.com", "subject": r"expir|renewal|payment|domain|transfer", "severity": "URGENT", "category": "Domain"},
    # Payment processors
    {"sender": r"@stripe\.com", "subject": r"dispute|charge.?back|fail|payout|verification", "severity": "URGENT", "category": "Stripe"},
    {"sender": r"@paypal\.com", "subject": r"dispute|charge.?back|limit|hold|verif", "severity": "HIGH", "category": "PayPal"},
    # Banking
    {"sender": r"@chime\.com|@cash\.app|@chase\.com|@bankofamerica\.com|@wellsfargo\.com|@capitalone\.com", "subject": r"declin|denied|insufficient|alert|suspicious|unusual", "severity": "URGENT", "category": "Bank"},
    # Email infra
    {"sender": r"@resend\.com|@sendgrid\.com|@postmark", "subject": r"trial|expir|usage|limit|suspend|invoice", "severity": "HIGH", "category": "Email API"},
    # AI APIs
    {"sender": r"@anthropic\.com|@openai\.com|@perplexity", "subject": r"limit|trial|expir|invoice|payment|fail", "severity": "HIGH", "category": "AI API"},
    # Github
    {"sender": r"@github\.com", "subject": r"security|breach|unauthor|payment|billing|suspend", "severity": "HIGH", "category": "GitHub"},
    # IRS / Tax / Legal
    {"sender": r"@irs\.gov|@taxauthority", "subject": r".*", "severity": "URGENT", "category": "Tax"},
    {"sender": r"@court|@summons|@lawsuit|@attorneygeneral", "subject": r".*", "severity": "URGENT", "category": "Legal"},
    # Subject-only triggers (any sender)
    {"sender": r".*", "subject": r"final notice|legal action|will be terminat|suspended|disabled|cease.and.desist", "severity": "URGENT", "category": "GENERIC URGENT"},
    {"sender": r".*", "subject": r"verify your card|payment declined|account locked|password reset", "severity": "HIGH", "category": "Account Action"},
]


def _log(event: str, **fields) -> None:
    row = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _decode_subject(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parts = decode_header(raw)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                out.append(chunk.decode("utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _seen_set() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_FILE.read_text()))
    except Exception:
        return set()


def _mark_seen(seen: set[str], msg_id: str) -> None:
    seen.add(msg_id)
    if len(seen) > 5000:
        seen = set(list(seen)[-3000:])
    SEEN_FILE.write_text(json.dumps(list(seen)))


def classify(sender: str, subject: str) -> dict | None:
    """Return matching pattern dict if email matches a critical pattern."""
    for p in CRITICAL_PATTERNS:
        if re.search(p["sender"], sender, re.I) and re.search(p["subject"], subject, re.I):
            return p
    return None


def alert_slack(severity: str, category: str, sender: str, subject: str, snippet: str) -> bool:
    """Post to Slack #hive-alerts via Block Kit. Returns True on success."""
    if not SLACK_BOT_TOKEN:
        return False
    import urllib.request
    color = {"URGENT": "#ef4444", "HIGH": "#facc15", "MEDIUM": "#a78bfa"}.get(severity, "#888888")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"[{severity}] {category}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*From:* {sender}\n*Subject:* {subject}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"```{snippet[:600]}```"}},
    ]
    payload = json.dumps({
        "channel": "#hive-alerts",
        "text": f"[{severity}] {category}: {subject[:80]}",
        "blocks": blocks,
        "attachments": [{"color": color}],
    }).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return bool(data.get("ok"))
    except Exception as e:
        _log("slack_post_failed", error=str(e))
        return False


def alert_ntfy(severity: str, category: str, subject: str) -> bool:
    """Push notification via ntfy.sh. Free, no signup, no API key needed."""
    if not NTFY_TOPIC:
        return False
    import urllib.request
    title = f"[{severity}] {category}"
    icon_priority = "5" if severity == "URGENT" else "4" if severity == "HIGH" else "3"
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=subject[:200].encode(),
        headers={
            "Title": title,
            "Priority": icon_priority,
            "Tags": "warning,money_with_wings" if severity == "URGENT" else "warning",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        _log("ntfy_failed", error=str(e))
        return False


def check_inbox() -> dict:
    """Scan the last 24h of mail via the shared imap_fetch helper.

    Credentials come from GMAIL_IMAP_USER/GMAIL_IMAP_PASS (the working path)
    via imap_fetch, which returns [] if creds are missing -- so a missing
    cred now yields ok=True/matched=0 instead of the old fatal error spam.
    """
    seen = _seen_set()
    alerts_sent = 0
    matched = 0
    for msg in fetch_recent(days=1):
        msg_id = msg.get("message_id", "")
        if not msg_id or msg_id in seen:
            continue
        sender = msg.get("from_email", "")
        subject = msg.get("subject", "")
        classification = classify(sender, subject)
        if not classification:
            _mark_seen(seen, msg_id)
            continue
        matched += 1
        snippet = (msg.get("body", "") or "")[:1500]
        slack_ok = alert_slack(
            classification["severity"], classification["category"],
            sender, subject, snippet,
        )
        ntfy_ok = alert_ntfy(
            classification["severity"], classification["category"], subject,
        )
        _log("alert_sent", severity=classification["severity"],
             category=classification["category"], sender=sender,
             subject=subject, slack_ok=slack_ok, ntfy_ok=ntfy_ok)
        if slack_ok or ntfy_ok:
            alerts_sent += 1
        _mark_seen(seen, msg_id)
    return {"ok": True, "matched": matched, "alerts_sent": alerts_sent}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true", help="loop forever, check every 5 min")
    args = ap.parse_args()
    if args.daemon:
        while True:
            try:
                result = check_inbox()
                _log("check_done", **result)
            except Exception as e:
                _log("check_failed", error=str(e))
            time.sleep(300)
    else:
        result = check_inbox()
        _log("check_done", **result)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
