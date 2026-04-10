"""
Rex Daily Health Report -- runs at 9 PM PT (5 AM UTC next day) via cron.

Checks every subsystem, counts today's activity, and posts a single
Slack summary to #wholesale-deals.

Cron entry (add with: crontab -e):
  0 5 * * * cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent && python3 rex_health.py

That is 5 AM UTC = 9 PM PT.
"""

import glob
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[Rex Health %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_health")

AGENT_DIR = Path(__file__).parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
# Display in PT for the report
PT_OFFSET = timedelta(hours=-7)  # PDT; use -8 for PST
NOW_PT = datetime.now(timezone.utc) + PT_OFFSET
TODAY_DISPLAY = NOW_PT.strftime("%B %d, %Y")


def post_slack(text: str, title: str = "Rex Daily Health Report"):
    """Post to Slack, creating a GDoc first when possible."""
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title=title,
                content=text,
                folder="01_Broker_OS/Daily_KPI",
                summary=text[:200],
                agent="charles_dawson",
            )
            if result.get("ok"):
                return True
        except Exception:
            pass
    # Fallback: raw text post
    if not SLACK_TOKEN:
        log.info(f"[Slack offline] Would post:\n{text}")
        return False
    try:
        import requests
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": SLACK_CHANNEL, "text": text},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        log.error(f"Slack post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# CHECK: Cron jobs ran today?
# ---------------------------------------------------------------------------

def check_cron_activity() -> dict:
    """Check if key log/output files were updated today."""
    results = {}

    # Check outreach_sent directory for today's logs
    outreach_dir = AGENT_DIR / "outreach_sent"
    today_outreach = list(outreach_dir.glob(f"{TODAY}*"))
    results["sdr_ran"] = len(today_outreach) > 0

    # Check pipeline directory for today's data
    pipeline_dir = AGENT_DIR / "pipeline"
    today_pipeline = list(pipeline_dir.glob(f"{TODAY}*"))
    results["pipeline_ran"] = len(today_pipeline) > 0

    # Check reports directory
    reports_dir = AGENT_DIR / "reports"
    today_reports = list(reports_dir.glob(f"{TODAY}*"))
    results["report_generated"] = len(today_reports) > 0

    # Check buyer outreach
    buyer_dir = AGENT_DIR / "buyer_outreach"
    today_buyer = list(buyer_dir.glob(f"{TODAY}*"))
    results["buyer_outreach_ran"] = len(today_buyer) > 0

    # Check daily leads
    daily_dir = AGENT_DIR / "daily_leads"
    today_daily = list(daily_dir.glob(f"{TODAY}*"))
    results["daily_leads_updated"] = len(today_daily) > 0

    return results


# ---------------------------------------------------------------------------
# CHECK: Emails sent today
# ---------------------------------------------------------------------------

def count_emails_sent() -> dict:
    """Count emails sent today from outreach logs."""
    seller_emails = 0
    buyer_emails = 0

    # Seller outreach
    outreach_dir = AGENT_DIR / "outreach_sent"
    for log_file in outreach_dir.glob(f"{TODAY}*"):
        try:
            lines = log_file.read_text().strip().split("\n")
            seller_emails += len([l for l in lines if l.strip()])
        except Exception:
            pass

    # Buyer outreach
    buyer_dir = AGENT_DIR / "buyer_outreach"
    for log_file in buyer_dir.glob(f"{TODAY}*"):
        try:
            if log_file.suffix == ".jsonl":
                lines = log_file.read_text().strip().split("\n")
                buyer_emails += len([l for l in lines if l.strip()])
            elif log_file.suffix == ".json":
                data = json.loads(log_file.read_text())
                if isinstance(data, list):
                    buyer_emails += len(data)
        except Exception:
            pass

    return {"seller_emails": seller_emails, "buyer_emails": buyer_emails}


# ---------------------------------------------------------------------------
# CHECK: Replies received
# ---------------------------------------------------------------------------

def count_replies() -> int:
    """Count replies received today from IMAP or logs."""
    replies_dir = AGENT_DIR / "replies"
    count = 0

    # Check for reply logs
    for reply_file in replies_dir.glob(f"{TODAY}*"):
        try:
            if reply_file.suffix == ".jsonl":
                lines = reply_file.read_text().strip().split("\n")
                count += len([l for l in lines if l.strip()])
            elif reply_file.suffix == ".json":
                data = json.loads(reply_file.read_text())
                if isinstance(data, list):
                    count += len(data)
        except Exception:
            pass

    # Also try a live IMAP check (non-destructive -- peek only)
    try:
        from rex_utils import safe_imap_check
        # Note: this marks messages as seen, so we only do it if no
        # other process is checking. For health report, just count files.
    except ImportError:
        pass

    return count


# ---------------------------------------------------------------------------
# CHECK: ATTOM API calls remaining
# ---------------------------------------------------------------------------

def check_attom_status() -> dict:
    """Check ATTOM API usage from rate tracker."""
    try:
        from rex_utils import attom_rate_check
        return attom_rate_check()
    except ImportError:
        # Read directly from cache file
        rate_file = AGENT_DIR / "cache" / "attom_rate_tracker.json"
        if rate_file.exists():
            try:
                tracker = json.loads(rate_file.read_text())
                today_data = tracker.get(TODAY, {"calls": 0})
                calls = today_data.get("calls", 0)
                limit = 250
                return {
                    "today_calls": calls,
                    "limit": limit,
                    "pct_used": round(calls / limit * 100, 1),
                }
            except Exception:
                pass
        return {"today_calls": 0, "limit": 250, "pct_used": 0}


# ---------------------------------------------------------------------------
# CHECK: Pipeline status
# ---------------------------------------------------------------------------

def check_pipeline() -> dict:
    """Count leads by status in the pipeline."""
    leads_db = AGENT_DIR / "leads_db.json"
    if not leads_db.exists():
        return {"total": 0}

    try:
        leads = json.loads(leads_db.read_text())
    except Exception:
        return {"total": 0, "error": "corrupt leads_db.json"}

    status_counts = {}
    with_email = 0
    with_phone = 0

    for lead in leads:
        status = lead.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if lead.get("owner_email"):
            with_email += 1
        if lead.get("owner_phone"):
            with_phone += 1

    return {
        "total": len(leads),
        "with_email": with_email,
        "with_phone": with_phone,
        "by_status": status_counts,
    }


# ---------------------------------------------------------------------------
# CHECK: Buyer pipeline
# ---------------------------------------------------------------------------

def check_buyers() -> dict:
    """Count buyers by status."""
    buyers_db = AGENT_DIR / "buyers_db.json"
    if not buyers_db.exists():
        return {"total": 0}

    try:
        buyers = json.loads(buyers_db.read_text())
    except Exception:
        return {"total": 0, "error": "corrupt buyers_db.json"}

    responded = sum(1 for b in buyers if b.get("responded"))
    qualified = sum(1 for b in buyers if b.get("on_deal_list"))
    with_email = sum(1 for b in buyers if b.get("email"))

    return {
        "total": len(buyers),
        "with_email": with_email,
        "responded": responded,
        "qualified": qualified,
    }


# ---------------------------------------------------------------------------
# CHECK: Errors in logs
# ---------------------------------------------------------------------------

def check_errors() -> list[str]:
    """Scan today's log files for errors."""
    errors = []

    # Check dead letter queue
    failed_dir = AGENT_DIR / "failed_emails"
    if failed_dir.exists():
        for dl_file in failed_dir.glob(f"{TODAY}*"):
            try:
                lines = dl_file.read_text().strip().split("\n")
                count = len([l for l in lines if l.strip()])
                if count:
                    errors.append(f"Dead letters: {count} failed emails")
            except Exception:
                pass

    # Check for any error logs
    for log_file in AGENT_DIR.glob(f"*{TODAY}*.log"):
        try:
            content = log_file.read_text()
            error_lines = [l for l in content.split("\n") if "ERROR" in l.upper()]
            if error_lines:
                errors.append(f"{log_file.name}: {len(error_lines)} errors")
        except Exception:
            pass

    return errors


# ---------------------------------------------------------------------------
# CHECK: System dependencies
# ---------------------------------------------------------------------------

def check_systems() -> dict:
    """Quick check of all external systems."""
    results = {}

    # Resend API key present
    results["resend_key"] = "SET" if os.environ.get("RESEND_API_KEY") or os.environ.get("SMTP_PASS") else "MISSING"

    # IMAP credentials
    results["imap_creds"] = "SET" if os.environ.get("IMAP_USER") and os.environ.get("IMAP_PASS") else "MISSING"

    # ATTOM API key
    results["attom_key"] = "SET" if os.environ.get("ATTOM_API_KEY") else "MISSING"

    # Slack token
    results["slack_token"] = "SET" if SLACK_TOKEN else "MISSING"

    # Supabase
    results["supabase_key"] = "SET" if os.environ.get("SUPABASE_SERVICE_ROLE_KEY") else "MISSING"

    return results


# ---------------------------------------------------------------------------
# MAIN: Build and post health report
# ---------------------------------------------------------------------------

def run_health_check() -> str:
    """Run all checks and post summary to Slack."""
    log.info("Running Rex daily health check...")

    # Gather all data
    cron = check_cron_activity()
    emails = count_emails_sent()
    replies = count_replies()
    attom = check_attom_status()
    pipeline = check_pipeline()
    buyers = check_buyers()
    errors = check_errors()
    systems = check_systems()

    # Determine overall status
    issues = []
    if pipeline.get("with_email", 0) == 0:
        issues.append("seller emails needed")
    if not cron.get("sdr_ran") and emails["seller_emails"] == 0:
        issues.append("SDR did not run")
    if errors:
        issues.append(f"{len(errors)} error(s)")
    if systems.get("resend_key") == "MISSING":
        issues.append("no Resend key")
    if systems.get("attom_key") == "MISSING":
        issues.append("no ATTOM key")

    if not issues:
        overall = "HEALTHY"
    elif len(issues) <= 2:
        overall = f"OK ({', '.join(issues)})"
    else:
        overall = f"NEEDS ATTENTION ({', '.join(issues[:3])})"

    # Build status counts
    pipeline_status = pipeline.get("by_status", {})
    status_line = ", ".join(
        f"{pipeline_status.get(s, 0)} {s}"
        for s in ["new", "contacted", "followed_up", "negotiating", "under_contract", "closed"]
        if pipeline_status.get(s, 0) > 0
    ) or "empty"

    # Build the report
    report = (
        f"*Rex Health Check -- {TODAY_DISPLAY}*\n\n"
        f"*Emails sent:* {emails['seller_emails']} seller / {emails['buyer_emails']} buyer\n"
        f"*Replies:* {replies}\n"
        f"*Pipeline:* {status_line} ({pipeline.get('total', 0)} total, "
        f"{pipeline.get('with_email', 0)} with email)\n"
        f"*Buyers:* {buyers.get('total', 0)} total, "
        f"{buyers.get('qualified', 0)} qualified, "
        f"{buyers.get('responded', 0)} responded\n"
        f"*ATTOM:* {attom.get('today_calls', 0)}/{attom.get('limit', 250)} calls "
        f"({attom.get('pct_used', 0)}%)\n"
    )

    if errors:
        report += f"*Errors:* {'; '.join(errors)}\n"
    else:
        report += f"*Errors:* 0\n"

    # Cron status
    cron_items = []
    if cron.get("sdr_ran"):
        cron_items.append("SDR")
    if cron.get("pipeline_ran"):
        cron_items.append("pipeline")
    if cron.get("buyer_outreach_ran"):
        cron_items.append("buyer outreach")
    if cron.get("daily_leads_updated"):
        cron_items.append("daily leads")
    cron_line = ", ".join(cron_items) if cron_items else "none detected"
    report += f"*Cron jobs today:* {cron_line}\n"

    # Systems
    missing_systems = [k for k, v in systems.items() if v == "MISSING"]
    if missing_systems:
        report += f"*Missing keys:* {', '.join(missing_systems)}\n"

    report += f"\n*Status: {overall}*"

    # Post to Slack
    log.info(report.replace("*", ""))
    post_slack(report)

    return report


if __name__ == "__main__":
    run_health_check()
