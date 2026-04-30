#!/usr/bin/env python3
"""
Hive Deal Orchestrator -- Autonomous pipeline management for all revenue streams.

Checks every pipeline every hour, fires next actions, respects business hours,
tracks deal progression, and reports results.

This is the CEO's right hand. It makes the business run without human intervention.

The Work Engine runs individual tasks. The Shift System handles personality chat.
The Deal Orchestrator is the MANAGER -- it checks what needs to happen next across
ALL revenue pipelines and pushes deals forward through their stages.

Pipeline stages:
  Wholesale:  lead -> scored -> matched -> offer_sent -> response -> negotiating -> contract -> closed -> paid
  Surplus:    scraped -> contacted -> authorized -> filed -> approved -> paid
  Consulting: prospect -> qualified -> outreach -> meeting -> proposal -> signed -> building -> delivered -> retainer
  Bot:        flat -> entry -> position -> exit -> review
  Broker:     scouted -> qualified -> matched -> outreach -> negotiating -> closed -> paid

Cron (Oracle E5):
  10 * * * * source /home/opc/.env && cd /home/opc && python3 hive_deal_orchestrator.py >> /tmp/hive_orchestrator.log 2>&1

CLI:
  python3 hive_deal_orchestrator.py             # Run all pipeline managers
  python3 hive_deal_orchestrator.py --dry-run   # Show what would execute without doing it
  python3 hive_deal_orchestrator.py --status    # Show current state of all pipelines
  python3 hive_deal_orchestrator.py --force     # Run even if already ran this hour
  python3 hive_deal_orchestrator.py --pipeline wholesale   # Run a single pipeline
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Timezone helpers
# ---------------------------------------------------------------------------
PT = timezone(timedelta(hours=-7))  # PDT (switch to -8 for PST)
ET = timezone(timedelta(hours=-4))  # EDT (switch to -5 for EST)

# ---------------------------------------------------------------------------
# Secrets from environment
# ---------------------------------------------------------------------------
def load_env_file(path: str = "/home/opc/.env"):
    """Best-effort .env loader for cron/shells that do not export sourced vars."""
    env_path = Path(path)
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as exc:
        logging.getLogger("hive_deal_orchestrator").warning(
            "Failed to load env file %s: %s", path, exc
        )


load_env_file()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
BLINKO_URL = os.environ.get("BLINKO_URL", "http://129.159.38.250:1111")

# ---------------------------------------------------------------------------
# Slack channel map
# ---------------------------------------------------------------------------
CHANNELS = {
    "war-room": "C0ANAU30UQ2",
    "ft-hunters": "C0AMVEWLT9D",
    "ft-consult": "C0ANEG19WQ4",
    "ft-markets": "C0AP56SFQG0",
    "ft-profit-engine": "C0AN7FT5JBF",
    "ai-consulting": "C0AN8SGAS22",
    "xlm-trading": "C0AN8SG030W",
    "ceo-brief": "C0AP56SQM08",
    "hive-alerts": "C0ANPRCA4AD",
    "broker-pipeline": "C0AN7FTTK2R",
    "deploy-log": "C0ANEG7D7GH",
    "revenue-dashboard": "C0AN8SGRSQY",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEAL_STATE_FILE = Path("/home/opc/hive_deal_state.json")
WORK_LEDGER = Path("/home/opc/hive_work_ledger.json")
LOCK_FILE = Path("/tmp/hive_orchestrator.lock")

# Django + wholesale paths on Oracle
DJANGO_DIR = "/home/opc/hive_django"
WHOLESALE_DIR = "/home/opc/wholesale_agent"
BOT_DIR = "/home/opc/xlm-bot"
BROKER_DIR = "/home/opc/broker_ops"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ORCH] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hive_deal_orchestrator")

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
CMD_TIMEOUT = 60


def run_command(cmd: str, timeout: int = CMD_TIMEOUT) -> str:
    """Run a shell command with timeout. Returns stdout or error string."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        return out or err or "(no output)"
    except subprocess.TimeoutExpired:
        return f"(timeout after {timeout}s)"
    except Exception as e:
        return f"(error: {e})"


def run_django_query(code: str) -> str:
    """Execute Python code inside the Django ORM context."""
    encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
    cmd = (
        f"cd {DJANGO_DIR} && python3 -c \""
        f"import base64,django,os;"
        f"os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings';"
        f"django.setup();"
        f"exec(base64.b64decode('{encoded}').decode('utf-8'))\""
    )
    return run_command(cmd)


def run_django_json(code: str):
    """Execute Django code expected to print one JSON payload."""
    raw = run_django_query(code)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Invalid Django JSON payload: %s", raw[:300])
        return None


def read_json(path: str) -> dict:
    """Safely read a JSON file. Returns empty dict on failure."""
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to read %s: %s", path, e)
    return {}


def load_state() -> dict:
    """Load deal orchestrator state from disk."""
    if DEAL_STATE_FILE.exists():
        try:
            return json.loads(DEAL_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("State file corrupt, starting fresh")
    return {
        "last_run": "",
        "run_count": 0,
        "wholesale": {},
        "surplus": {},
        "bot": {},
        "consulting": {},
        "broker": {},
        "freelance": {},
        "revenue": {},
        "services": {},
    }


def save_state(state: dict):
    """Persist deal state to disk."""
    try:
        state["last_run"] = datetime.now(PT).isoformat()
        state["run_count"] = state.get("run_count", 0) + 1
        DEAL_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except OSError as e:
        log.error("Failed to save state: %s", e)


def resolve_channel_id(channel_name: str) -> str:
    """Look up a Slack channel ID by name and cache it."""
    if not SLACK_BOT_TOKEN:
        return ""
    try:
        r = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"types": "public_channel,private_channel", "limit": 1000},
            timeout=20,
        )
        data = r.json()
        for channel in data.get("channels", []):
            if channel.get("name") == channel_name:
                cid = channel.get("id", "")
                if cid:
                    CHANNELS[channel_name] = cid
                return cid
    except Exception as exc:
        log.warning("Slack channel lookup failed for %s: %s", channel_name, exc)
    return ""


def post_to_slack(channel_name: str, text: str) -> bool:
    """Post to Slack through the standard report publisher, then fall back to raw chat."""
    folder_map = {
        "war-room": "00_Command_Center/War_Room",
        "broker-pipeline": "01_Broker_OS/Deal_Pipeline",
        "ft-markets": "02_XLM_Bot/Daily_Scoreboard",
        "hive-alerts": "00_Command_Center/System_Status",
        "deploy-log": "06_Infrastructure/N8N_Workflow_Logs",
    }
    try:
        try:
            from content_tools.gdocs_bridge import publish_report
        except Exception:
            sys.path.insert(0, "/home/opc/content_tools")
            from gdocs_bridge import publish_report
        lines = [line.strip(" *") for line in str(text).splitlines() if line.strip()]
        title = lines[0][:120] if lines else f"Hive Deal Orchestrator Update ({channel_name})"
        summary = " ".join(lines[:2])[:220] if lines else "Hive deal orchestrator update."
        result = publish_report(
            title=title,
            content=str(text),
            folder=folder_map.get(channel_name, "00_Command_Center/System_Status"),
            slack_channel=f"#{channel_name}",
            summary=summary,
            post_to_slack=True,
            agent="marcus_cole",
        )
        if result.get("slack_posted"):
            return True
    except Exception as exc:
        log.warning("Report publish fallback to raw Slack for %s: %s", channel_name, exc)

    cid = CHANNELS.get(channel_name)
    if not cid or not SLACK_BOT_TOKEN:
        log.warning("Slack skip: channel=%s token=%s", channel_name, bool(SLACK_BOT_TOKEN))
        return False
    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": cid, "text": text},
            timeout=15,
        )
        payload = r.json()
        ok = payload.get("ok", False)
        if not ok and payload.get("error") == "channel_not_found":
            resolved = resolve_channel_id(channel_name)
            if resolved and resolved != cid:
                retry = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={"channel": resolved, "text": text},
                    timeout=15,
                )
                payload = retry.json()
                ok = payload.get("ok", False)
        if not ok:
            log.warning("Slack error: %s", payload.get("error", "unknown"))
        return ok
    except Exception as e:
        log.error("Slack post failed: %s", e)
        return False


try:
    import requests
except ImportError:
    log.error("requests not installed -- pip install requests")
    sys.exit(1)


def log_action(action: dict):
    """Append an action to the work ledger."""
    try:
        ledger = {}
        if WORK_LEDGER.exists():
            ledger = json.loads(WORK_LEDGER.read_text())
        entries = ledger.get("orchestrator_actions", [])
        entries.append({
            **action,
            "timestamp": datetime.now(PT).isoformat(),
        })
        # Keep bounded
        if len(entries) > 1000:
            entries = entries[-1000:]
        ledger["orchestrator_actions"] = entries
        WORK_LEDGER.write_text(json.dumps(ledger, indent=2, default=str))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Ledger write failed: %s", e)


def log_to_blinko(summary: str, details: str):
    """Log a session to Blinko for knowledge persistence."""
    try:
        requests.post(
            f"{BLINKO_URL}/api/v1/note/upsert",
            headers={"Content-Type": "application/json"},
            json={
                "content": (
                    f"# Hive Orchestrator: {summary}\n"
                    f"#hive/orchestrator #hive/pipeline\n\n"
                    f"{details}"
                ),
                "type": 1,
            },
            timeout=10,
        )
    except Exception:
        pass  # Best effort


def send_email(to: str, subject: str, html_body: str, from_name: str = "Piper Reeves",
               from_email: str = "piper@everlightventures.io",
               budget_category: str = "nurture") -> bool:
    """Send an email via branded_mailer (gold template, budget-gated).

    Defaults to budget_category='nurture' because deal-orchestrator emails are
    follow-ups to existing matches, not cold blasts.
    """
    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        log.error("branded_mailer unavailable, send aborted: %s", exc)
        return False

    result = send_branded_email(
        to=to,
        subject=subject,
        content_html=html_body,
        title=subject,
        from_name=from_name,
        from_email=from_email,
        reply_to=from_email,
        agent_name=from_name,
        agent_title="Deal Orchestrator",
        agent_email=from_email,
        budget_category=budget_category,
    )
    if not result.ok:
        log.warning("branded_mailer deal-email failed for %s: %s", to, result.error)
    return result.ok


# ---------------------------------------------------------------------------
# Business hours enforcement
# ---------------------------------------------------------------------------
def is_business_hours(tz=PT) -> bool:
    """Check if current time is within legal outreach hours (8 AM - 9 PM Mon-Sat)."""
    now = datetime.now(tz)
    return 8 <= now.hour < 21 and now.weekday() < 6


def is_business_hours_et() -> bool:
    """Business hours in Eastern Time."""
    return is_business_hours(ET)


def is_business_hours_for_state(state_abbr: str) -> bool:
    """Check business hours based on a US state abbreviation."""
    eastern_states = {
        "NY", "NJ", "CT", "MA", "PA", "VA", "MD", "DC", "FL", "GA", "NC",
        "SC", "OH", "MI", "IN", "TN", "KY", "WV", "ME", "VT", "NH", "RI",
        "DE", "AL", "MS",
    }
    central_states = {
        "IL", "TX", "WI", "MN", "IA", "MO", "AR", "LA", "OK", "KS", "NE",
        "SD", "ND",
    }
    mountain_states = {"CO", "AZ", "NM", "UT", "MT", "WY", "ID"}
    pacific_states = {"CA", "WA", "OR", "NV", "HI", "AK"}

    s = state_abbr.upper()
    if s in eastern_states:
        return is_business_hours(ET)
    elif s in central_states:
        return is_business_hours(timezone(timedelta(hours=-5)))  # CDT
    elif s in mountain_states:
        return is_business_hours(timezone(timedelta(hours=-6)))  # MDT
    elif s in pacific_states:
        return is_business_hours(PT)
    # Default to PT if unknown
    return is_business_hours(PT)


# ---------------------------------------------------------------------------
# Pipeline 1: Wholesale Real Estate
# ---------------------------------------------------------------------------
def manage_wholesale_pipeline(state: dict, actions: list, dry_run: bool = False):
    """
    Check wholesale pipeline and fire next actions.
    Stages: lead -> scored -> matched -> offer_sent -> response -> negotiating -> contract -> closed -> paid
    """
    ws = state.setdefault("wholesale", {})
    log.info("--- Wholesale Pipeline ---")

    # 1. Pull current pipeline stats from Django
    stats_raw = run_django_query(
        "from broker_ops.models import PropertyLead, InvestorBuyer, WholesaleMatch;"
        "leads = PropertyLead.objects.count();"
        "buyers = InvestorBuyer.objects.count();"
        "new_matches = WholesaleMatch.objects.filter(status='new').count();"
        "offered = WholesaleMatch.objects.filter(status='offer_sent').count();"
        "negotiating = WholesaleMatch.objects.filter(status='negotiating').count();"
        "print(f'{leads},{buyers},{new_matches},{offered},{negotiating}')"
    )
    log.info("  Pipeline stats: %s", stats_raw)

    try:
        parts = stats_raw.split(",")
        leads = int(parts[0])
        buyers = int(parts[1])
        new_matches = int(parts[2])
        offered = int(parts[3])
        negotiating = int(parts[4])
    except (ValueError, IndexError):
        leads = buyers = new_matches = offered = negotiating = 0
        log.warning("  Could not parse pipeline stats: %s", stats_raw)

    ws["leads"] = leads
    ws["buyers"] = buyers
    ws["new_matches"] = new_matches
    ws["offered"] = offered
    ws["negotiating"] = negotiating

    # 2. If outside business hours, queue everything
    if not is_business_hours():
        if new_matches > 0 or offered > 0:
            actions.append({
                "agent": "Rex Blackwell",
                "action": "QUEUED",
                "detail": (
                    f"Outreach queued for business hours. "
                    f"{new_matches} matches need offers, {offered} offers awaiting response."
                ),
                "channel": "ft-hunters",
                "pipeline": "wholesale",
            })
        return

    # 3. Run creative finance underwriting on new matches
    if new_matches > 0:
        top_n = min(new_matches, 5)
        if not dry_run:
            result = run_command(
                f"cd {WHOLESALE_DIR} && python3 creative_finance_engine.py "
                f"--batch --top {top_n} 2>&1 | tail -10"
            )
        else:
            result = f"(dry-run) Would underwrite top {top_n} of {new_matches} matches"
        actions.append({
            "agent": "Rex Blackwell",
            "action": "UNDERWRITE",
            "detail": f"Underwrote top {top_n} of {new_matches} new matches.\n{result[:300]}",
            "channel": "ft-hunters",
            "pipeline": "wholesale",
        })

    # 4. Send offers for underwritten matches that haven't been sent
    unsent_raw = run_django_query(
        "from broker_ops.models import WholesaleMatch;"
        "unsent = WholesaleMatch.objects.filter(status='scored', offer_sent=False)[:5];"
        "for m in unsent:"
        "    print(f'{m.id}|{m.property_lead.address}|{m.investor_buyer.name}|{m.property_lead.state}')"
    )
    if unsent_raw and "Traceback" not in unsent_raw and unsent_raw != "(no output)":
        for line in unsent_raw.strip().split("\n"):
            parts = line.split("|")
            if len(parts) < 4:
                continue
            match_id, address, buyer_name, lead_state = parts[0], parts[1], parts[2], parts[3]

            # Respect recipient timezone
            if lead_state and not is_business_hours_for_state(lead_state):
                actions.append({
                    "agent": "Piper Reeves",
                    "action": "OFFER_QUEUED",
                    "detail": f"Offer to {buyer_name} for {address} queued -- outside business hours in {lead_state}",
                    "channel": "ft-hunters",
                    "pipeline": "wholesale",
                })
                continue

            if not dry_run:
                send_result = run_command(
                    f"cd {WHOLESALE_DIR} && python3 hive_outreach.py "
                    f"--match-id {match_id} --type offer 2>&1 | tail -5"
                )
            else:
                send_result = f"(dry-run) Would send offer for match {match_id}"
            actions.append({
                "agent": "Piper Reeves",
                "action": "OFFER_SENT",
                "detail": f"Sent offer to {buyer_name} for {address}.\n{send_result[:200]}",
                "channel": "ft-hunters",
                "pipeline": "wholesale",
            })

    # 5. Follow up on offers sent > 48 hours ago with no response
    stale_raw = run_django_query(
        "from broker_ops.models import WholesaleMatch;"
        "from django.utils import timezone as tz;"
        "from datetime import timedelta;"
        "cutoff = tz.now() - timedelta(hours=48);"
        "stale = WholesaleMatch.objects.filter(status='offer_sent', offer_sent_at__lt=cutoff, follow_up_count__lt=3)[:5];"
        "for m in stale:"
        "    hrs = int((tz.now() - m.offer_sent_at).total_seconds() / 3600);"
        "    print(f'{m.id}|{m.investor_buyer.name}|{hrs}|{m.follow_up_count}')"
    )
    if stale_raw and "Traceback" not in stale_raw and stale_raw != "(no output)":
        for line in stale_raw.strip().split("\n"):
            parts = line.split("|")
            if len(parts) < 4:
                continue
            match_id, buyer_name, hours_ago, followup_count = (
                parts[0], parts[1], parts[2], parts[3]
            )
            if not dry_run:
                fu_result = run_command(
                    f"cd {WHOLESALE_DIR} && python3 hive_outreach.py "
                    f"--match-id {match_id} --type follow_up 2>&1 | tail -5"
                )
            else:
                fu_result = f"(dry-run) Would follow up on match {match_id}"
            actions.append({
                "agent": "Piper Reeves",
                "action": "FOLLOW_UP",
                "detail": (
                    f"Follow-up #{int(followup_count)+1} to {buyer_name} -- "
                    f"no response in {hours_ago}h.\n{fu_result[:200]}"
                ),
                "channel": "ft-hunters",
                "pipeline": "wholesale",
            })

    # 6. Escalate deals in negotiation to Harrison Knox
    if negotiating > 0:
        neg_raw = run_django_query(
            "from broker_ops.models import WholesaleMatch;"
            "for m in WholesaleMatch.objects.filter(status='negotiating')[:3]:"
            "    print(f'{m.id}|{m.property_lead.address}|{m.investor_buyer.name}')"
        )
        if neg_raw and "Traceback" not in neg_raw and neg_raw != "(no output)":
            for line in neg_raw.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 3:
                    actions.append({
                        "agent": "Harrison Knox",
                        "action": "CLOSE_PUSH",
                        "detail": f"Push to close: {parts[1]} with buyer {parts[2]} (match #{parts[0]})",
                        "channel": "ft-hunters",
                        "pipeline": "wholesale",
                    })

    # 7. Pipeline value estimate
    ws["pipeline_value"] = new_matches * 7500 + offered * 10000 + negotiating * 15000
    log.info("  Pipeline value: $%s", f"{ws['pipeline_value']:,.0f}")


# ---------------------------------------------------------------------------
# Pipeline 2: Surplus Funds Recovery
# ---------------------------------------------------------------------------
def manage_surplus_pipeline(state: dict, actions: list, dry_run: bool = False):
    """
    Surplus funds recovery pipeline.
    Stages: scraped -> contacted -> authorized -> filed -> approved -> paid
    """
    sp = state.setdefault("surplus", {})
    log.info("--- Surplus Pipeline ---")

    today = datetime.now(PT).strftime("%Y-%m-%d")

    # 1. Run daily surplus scan if not done today
    last_scan = sp.get("last_scan", "")
    if last_scan != today:
        counties = ["la", "orange", "riverside", "san-bernardino"]
        for county in counties:
            if not dry_run:
                result = run_command(
                    f"cd {WHOLESALE_DIR} && python3 surplus_funds_finder.py "
                    f"--county {county} --min-amount 10000 2>&1 | tail -10",
                    timeout=120,
                )
            else:
                result = f"(dry-run) Would scan {county} county"
            actions.append({
                "agent": "Rex Blackwell",
                "action": "SURPLUS_SCAN",
                "detail": f"{county.upper()} County surplus scan:\n{result[:300]}",
                "channel": "ft-hunters",
                "pipeline": "surplus",
            })
        sp["last_scan"] = today

    # 2. Read surplus claims tracker
    tracker = read_json(f"{WHOLESALE_DIR}/surplus_claims_tracker.json")
    claims = tracker.get("claims", [])
    total_recovered = tracker.get("total_recovered", 0)
    sp["claims_count"] = len(claims)
    sp["total_recovered"] = total_recovered

    # 3. Contact owners for new claims (business hours only, max 5 per hour)
    if is_business_hours():
        pending_contact = [c for c in claims if c.get("status") == "scraped"][:5]
        for claim in pending_contact:
            owner = claim.get("owner", "Unknown")
            amount = claim.get("amount", 0)
            claim_state = claim.get("state", "CA")

            if not is_business_hours_for_state(claim_state):
                actions.append({
                    "agent": "Piper Reeves",
                    "action": "SURPLUS_QUEUED",
                    "detail": f"Outreach to {owner} (${amount:,.0f}) queued -- outside hours in {claim_state}",
                    "channel": "ft-hunters",
                    "pipeline": "surplus",
                })
                continue

            if not dry_run:
                outreach_result = run_command(
                    f"cd {WHOLESALE_DIR} && python3 surplus_outreach_templates.py "
                    f"--owner '{owner}' --amount {amount} --type initial 2>&1 | tail -5"
                )
            else:
                outreach_result = f"(dry-run) Would contact {owner} about ${amount:,.0f}"
            actions.append({
                "agent": "Piper Reeves",
                "action": "SURPLUS_OUTREACH",
                "detail": f"Contacting {owner} about ${amount:,.0f} surplus.\n{outreach_result[:200]}",
                "channel": "ft-hunters",
                "pipeline": "surplus",
            })

    # 4. Follow up on contacted owners who haven't responded in 72 hours
    if is_business_hours():
        contacted = [c for c in claims if c.get("status") == "contacted"]
        for claim in contacted[:3]:
            contacted_at = claim.get("contacted_at", "")
            if not contacted_at:
                continue
            try:
                contact_dt = datetime.fromisoformat(contacted_at)
                hours_since = (datetime.now(PT) - contact_dt.astimezone(PT)).total_seconds() / 3600
            except (ValueError, TypeError):
                hours_since = 0
            if hours_since > 72:
                owner = claim.get("owner", "Unknown")
                amount = claim.get("amount", 0)
                actions.append({
                    "agent": "Piper Reeves",
                    "action": "SURPLUS_FOLLOW_UP",
                    "detail": f"Follow-up to {owner} (${amount:,.0f}) -- no response in {int(hours_since)}h",
                    "channel": "ft-hunters",
                    "pipeline": "surplus",
                })

    # 5. Check claims ready for filing (authorized by owner)
    authorized = [c for c in claims if c.get("status") == "authorized"]
    for claim in authorized[:3]:
        actions.append({
            "agent": "Samuel Navarro",
            "action": "FILE_CLAIM",
            "detail": (
                f"Filing claim for {claim.get('owner', '?')} -- "
                f"${claim.get('amount', 0):,.0f} in {claim.get('county', '?')} County"
            ),
            "channel": "ft-hunters",
            "pipeline": "surplus",
        })

    log.info("  Claims: %d total, $%s recovered", len(claims), f"{total_recovered:,.0f}")


# ---------------------------------------------------------------------------
# Pipeline 3: Creative Finance
# ---------------------------------------------------------------------------
def manage_creative_finance(state: dict, actions: list, dry_run: bool = False):
    """
    Creative finance pipeline (subject-to, owner-finance, lease-option).
    Higher margins than straight wholesale.
    """
    cf = state.setdefault("creative_finance", {})
    log.info("--- Creative Finance Pipeline ---")

    today = datetime.now(PT).strftime("%Y-%m-%d")
    last_batch = cf.get("last_batch_run", "")

    # Run batch underwriting once daily
    if last_batch != today:
        if not dry_run:
            result = run_command(
                f"cd {WHOLESALE_DIR} && python3 creative_finance_engine.py "
                f"--batch --top 10 --strategy all 2>&1 | tail -15",
                timeout=120,
            )
        else:
            result = "(dry-run) Would run batch creative finance underwriting"
        cf["last_batch_run"] = today
        actions.append({
            "agent": "Rex Blackwell",
            "action": "CF_UNDERWRITE",
            "detail": f"Daily creative finance batch underwriting:\n{result[:400]}",
            "channel": "ft-hunters",
            "pipeline": "creative_finance",
        })

    # Send batch offers during business hours
    if is_business_hours():
        unsent = cf.get("unsent_offers", 0)
        if unsent > 0 or last_batch == today:
            if not dry_run:
                result = run_command(
                    f"cd {WHOLESALE_DIR} && python3 hive_outreach.py "
                    f"--type creative_offer --batch --max 3 2>&1 | tail -5"
                )
            else:
                result = "(dry-run) Would send batch creative finance offers"
            actions.append({
                "agent": "Piper Reeves",
                "action": "CF_OFFERS_SENT",
                "detail": f"Batch creative finance offers:\n{result[:200]}",
                "channel": "ft-hunters",
                "pipeline": "creative_finance",
            })


# ---------------------------------------------------------------------------
# Pipeline 4: XLM Bot Watchdog
# ---------------------------------------------------------------------------
def manage_bot_watchdog(state: dict, actions: list, dry_run: bool = False):
    """
    Monitor XLM bot health, flag issues, recommend adjustments.
    Rex Thornton reviews every cycle.
    """
    bot = state.setdefault("bot", {})
    log.info("--- Bot Watchdog ---")

    # Read bot state
    bot_state = read_json(f"{BOT_DIR}/data/state.json")
    sentiment = read_json(f"{BOT_DIR}/data/sentiment_shift.json")
    onchain = read_json(f"{BOT_DIR}/data/onchain_alerts.json")

    equity = float(bot_state.get("equity_start_usd") or 0)
    pnl_bot = float(bot_state.get("pnl_today_usd") or 0)
    pnl_exchange = float(bot_state.get("exchange_pnl_today_usd") or 0)
    pnl_today = pnl_exchange
    if abs(pnl_today) < 0.01 and abs(pnl_bot) >= 0.01:
        pnl_today = pnl_bot
    pnl_session = bot_state.get("pnl_session", 0)
    consec_losses = int(bot_state.get("consecutive_losses") or 0)
    vol_state = str(bot_state.get("vol_state") or "unknown")
    open_position = bot_state.get("open_position") or {}
    position = str(open_position.get("direction") or "flat")
    trades_today = int(bot_state.get("trades") or bot_state.get("trades_today") or 0)
    max_trades_today = int(bot_state.get("max_trades_today") or bot_state.get("max_losses_today") or 5)
    safe_mode = bool(bot_state.get("safe_mode") or bot_state.get("_safe_mode"))
    safe_mode_reason = (
        bot_state.get("safe_mode_reason")
        or bot_state.get("_safe_mode_reason")
        or ""
    )
    last_exit_time = str(bot_state.get("last_exit_time") or "")
    last_entry_time = str(bot_state.get("last_entry_time") or "")

    bot["equity"] = equity
    bot["pnl_today"] = pnl_today
    bot["position"] = position
    bot["vol_state"] = vol_state
    bot["consec_losses"] = consec_losses
    bot["trades_today"] = trades_today
    bot["safe_mode"] = safe_mode
    bot["safe_mode_reason"] = safe_mode_reason
    bot["last_exit_time"] = last_exit_time
    bot["last_entry_time"] = last_entry_time

    # Check if bot process is alive
    bot_alive = run_command("systemctl is-active xlm-bot.service 2>/dev/null").strip()
    bot["service_status"] = bot_alive

    if bot_alive != "active":
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_DOWN",
            "detail": f"CRITICAL: xlm-bot.service is {bot_alive}. Attempting restart.",
            "channel": "xlm-trading",
            "pipeline": "bot",
            "severity": "critical",
        })
        if not dry_run:
            run_command("sudo systemctl restart xlm-bot.service")

    # Flag consecutive losses >= 3
    if consec_losses >= 3:
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_RISK_ALERT",
            "detail": (
                f"Loss streak detected: {consec_losses} consecutive losses. "
                f"Equity ${equity:.2f}, PnL ${pnl_today:.2f}, "
                f"{trades_today} trades, vol={vol_state}, safe_mode={safe_mode}."
            ),
            "channel": "xlm-trading",
            "pipeline": "bot",
            "severity": "high",
        })

    # Flag if daily P&L exceeds -2% of equity
    if equity > 0 and pnl_today < -(equity * 0.02):
        loss_pct = abs(pnl_today / equity) * 100
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_DRAWDOWN",
            "detail": (
                f"CRITICAL: Daily loss ${pnl_today:.2f} = {loss_pct:.1f}% of equity. "
                f"Exceeds 2% threshold. "
                f"Last entry: {last_entry_time or 'n/a'} | Last exit: {last_exit_time or 'n/a'}"
            ),
            "channel": "xlm-trading",
            "pipeline": "bot",
            "severity": "critical",
        })

    # Flag if trades today exceed max
    if trades_today >= max_trades_today:
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_TRADE_LIMIT",
            "detail": (
                f"Trade limit reached: {trades_today}/{max_trades_today} trades today. "
                f"Position={position}, safe_mode={safe_mode}."
            ),
            "channel": "xlm-trading",
            "pipeline": "bot",
            "severity": "high",
        })

    if safe_mode:
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_SAFE_MODE",
            "detail": (
                f"Bot is in SAFE_MODE. Reason: {safe_mode_reason or 'not provided'}. "
                f"PnL ${pnl_today:.2f}, trades={trades_today}, position={position}."
            ),
            "channel": "xlm-trading",
            "pipeline": "bot",
            "severity": "high",
        })

    # Regular status update (every 4 hours)
    hour = datetime.now(PT).hour
    if hour % 4 == 0:
        sentiment_score = sentiment.get("score", "?")
        sentiment_dir = sentiment.get("direction", "?")
        onchain_signal = onchain.get("signal", "neutral")
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_STATUS",
            "detail": (
                f"Bot Status Report:\n"
                f"  Position: {position} | Vol: {vol_state}\n"
                f"  Equity: ${equity:.2f} | PnL today: ${pnl_today:.2f}\n"
                f"  Trades: {trades_today} | Consec losses: {consec_losses}\n"
                f"  Safe mode: {'ON' if safe_mode else 'OFF'}"
                f"{f' ({safe_mode_reason})' if safe_mode_reason else ''}\n"
                f"  Sentiment: {sentiment_score} ({sentiment_dir})\n"
                f"  On-chain: {onchain_signal}\n"
                f"  Service: {bot_alive}"
            ),
            "channel": "xlm-trading",
            "pipeline": "bot",
        })

    # Weekly P&L review (Sunday at noon)
    now = datetime.now(PT)
    if now.weekday() == 6 and now.hour == 12:
        weekly_log = run_command(
            f"cat {BOT_DIR}/logs/trades.log 2>/dev/null | "
            f"python3 -c \""
            f"import sys; lines=sys.stdin.readlines()[-50:];"
            f"wins=sum(1 for l in lines if 'WIN' in l.upper() or 'PROFIT' in l.upper());"
            f"losses=sum(1 for l in lines if 'LOSS' in l.upper());"
            f"print(f'W/L: {{wins}}/{{losses}} in last 50 trades')\""
        )
        actions.append({
            "agent": "Rex Thornton",
            "action": "BOT_WEEKLY_REVIEW",
            "detail": f"Weekly Bot Review:\n{weekly_log}\nEquity: ${equity:.2f}\nRecommendation pending.",
            "channel": "xlm-trading",
            "pipeline": "bot",
        })


# ---------------------------------------------------------------------------
# Pipeline 5: AI Consulting
# ---------------------------------------------------------------------------
def manage_consulting_pipeline(state: dict, actions: list, dry_run: bool = False):
    """
    AI Consulting pipeline.
    Stages: prospect -> qualified -> outreach -> meeting -> proposal -> signed -> building -> delivered -> retainer
    """
    cs = state.setdefault("consulting", {})
    log.info("--- Consulting Pipeline ---")

    today = datetime.now(PT).strftime("%Y-%m-%d")

    # 1. Scout for new prospects (daily)
    last_scout = cs.get("last_scout", "")
    if last_scout != today:
        if not dry_run:
            # Scout HN, Reddit, Product Hunt for businesses that need AI
            result = run_command(
                f"cd {BROKER_DIR} && python3 -c \""
                f"from broker_mcp import bulk_scout;"
                f"results = bulk_scout(['hn', 'producthunt'], query='need AI automation');"
                f"print(f'Found {{len(results)}} prospects')\" 2>&1 | tail -5"
            )
        else:
            result = "(dry-run) Would scout HN and Product Hunt for AI consulting leads"
        cs["last_scout"] = today
        actions.append({
            "agent": "Ryan Kim",
            "action": "CONSULT_SCOUT",
            "detail": f"Daily prospect scout:\n{result[:300]}",
            "channel": "ft-consult",
            "pipeline": "consulting",
        })

    # 2. Score and qualify new prospects
    score_result = run_django_query(
        "from funnel.models import Lead;"
        "unscored = Lead.objects.filter(source='consulting', score__isnull=True).count();"
        "qualified = Lead.objects.filter(source='consulting', score__gte=70).count();"
        "total = Lead.objects.filter(source='consulting').count();"
        "print(f'{total},{unscored},{qualified}')"
    )
    try:
        total_leads, unscored, qualified = [int(x) for x in score_result.split(",")]
    except (ValueError, IndexError):
        total_leads = unscored = qualified = 0

    cs["total_leads"] = total_leads
    cs["unscored"] = unscored
    cs["qualified"] = qualified

    if unscored > 0:
        actions.append({
            "agent": "Frederick Banks",
            "action": "CONSULT_SCORE",
            "detail": f"{unscored} consulting leads need scoring. Running qualification.",
            "channel": "ft-consult",
            "pipeline": "consulting",
        })

    # 3. Outreach to qualified prospects (business hours)
    if is_business_hours() and qualified > 0:
        outreach_raw = run_django_query(
            "from funnel.models import Lead;"
            "prospects = Lead.objects.filter(source='consulting', score__gte=70, status='qualified')[:3];"
            "for p in prospects:"
            "    print(f'{p.id}|{p.name}|{p.email}|{p.company}')"
        )
        if outreach_raw and "Traceback" not in outreach_raw and outreach_raw != "(no output)":
            for line in outreach_raw.strip().split("\n"):
                parts = line.split("|")
                if len(parts) < 4:
                    continue
                lead_id, name, email, company = parts[0], parts[1], parts[2], parts[3]
                actions.append({
                    "agent": "Piper Reeves",
                    "action": "CONSULT_OUTREACH",
                    "detail": f"Outreach to {name} at {company} ({email}) -- AI consulting pitch",
                    "channel": "ft-consult",
                    "pipeline": "consulting",
                })

    # 4. Post to consulting channel with pipeline summary (every 6 hours)
    hour = datetime.now(PT).hour
    if hour % 6 == 0:
        actions.append({
            "agent": "Ryan Kim",
            "action": "CONSULT_PIPELINE",
            "detail": (
                f"Consulting Pipeline:\n"
                f"  Total leads: {total_leads}\n"
                f"  Unscored: {unscored}\n"
                f"  Qualified: {qualified}\n"
                f"  Target: 1 signed client this month ($2k-5k build + $2k/mo retainer)"
            ),
            "channel": "ft-consult",
            "pipeline": "consulting",
        })


# ---------------------------------------------------------------------------
# Pipeline 6: Broker OS / SaaS Deals
# ---------------------------------------------------------------------------
def manage_broker_pipeline(state: dict, actions: list, dry_run: bool = False):
    """
    SaaS Broker pipeline.
    Stages: scouted -> qualified -> matched -> outreach -> negotiating -> closed -> paid
    """
    br = state.setdefault("broker", {})
    log.info("--- Broker OS Pipeline ---")

    today = datetime.now(PT).strftime("%Y-%m-%d")
    stats = run_django_json(
        "import json;"
        "from datetime import timedelta;"
        "from django.utils import timezone;"
        "from broker_ops.models import OfferListing, LeadProfile, BrokerMatch, Deal, OutreachSequence;"
        "cutoff = timezone.now() - timedelta(hours=24);"
        "real_leads = LeadProfile.objects.filter(unsubscribed=False).exclude(email='')"
        ".exclude(email__iendswith='@placeholder.io')"
        ".exclude(email__iendswith='@example.com')"
        ".exclude(email__iendswith='@example.org')"
        ".exclude(email__iendswith='@example.net')"
        ".exclude(email__istartswith='test@')"
        ".exclude(email__istartswith='demo@')"
        ".exclude(email__istartswith='sample@')"
        ".exclude(email__istartswith='noreply@')"
        ".exclude(email__istartswith='no-reply@');"
        "real_outreach = OutreachSequence.objects.filter(status='pending', scheduled_at__lte=timezone.now(), match__lead__unsubscribed=False)"
        ".exclude(to_email__iendswith='@placeholder.io')"
        ".exclude(to_email__iendswith='@example.com')"
        ".exclude(to_email__iendswith='@example.org')"
        ".exclude(to_email__iendswith='@example.net')"
        ".exclude(to_email__istartswith='test@')"
        ".exclude(to_email__istartswith='demo@')"
        ".exclude(to_email__istartswith='sample@')"
        ".exclude(to_email__istartswith='noreply@')"
        ".exclude(to_email__istartswith='no-reply@');"
        "payload = {"
        "'offers': OfferListing.objects.filter(status='active').count(),"
        "'fresh_offers': OfferListing.objects.filter(status='active', created_at__gte=cutoff).count(),"
        "'contactable_leads': real_leads.count(),"
        "'fresh_leads': real_leads.filter(created_at__gte=cutoff).count(),"
        "'pending_matches': BrokerMatch.objects.filter(status='pending').count(),"
        "'approved_matches': BrokerMatch.objects.filter(status='approved').count(),"
        "'converted_matches': BrokerMatch.objects.filter(status='converted').count(),"
        "'due_outreach': real_outreach.count(),"
        "'active_deals': Deal.objects.filter(stage__in=['intro','negotiating','contracted','active']).count(),"
        "'closed_won': Deal.objects.filter(stage='closed_won').count()"
        "};"
        "print(json.dumps(payload))"
    ) or {}

    br.update({
        "offers": int(stats.get("offers") or 0),
        "fresh_offers": int(stats.get("fresh_offers") or 0),
        "contactable_leads": int(stats.get("contactable_leads") or 0),
        "fresh_leads": int(stats.get("fresh_leads") or 0),
        "pending_matches": int(stats.get("pending_matches") or 0),
        "approved_matches": int(stats.get("approved_matches") or 0),
        "converted_matches": int(stats.get("converted_matches") or 0),
        "due_outreach": int(stats.get("due_outreach") or 0),
        "active_deals": int(stats.get("active_deals") or 0),
        "closed_won": int(stats.get("closed_won") or 0),
    })

    if br["fresh_offers"] == 0 and br["fresh_leads"] == 0 and br.get("last_scout") != today:
        actions.append({
            "agent": "Sebastian Navarro",
            "action": "BROKER_INTAKE_GAP",
            "detail": (
                "No fresh broker intake in the last 24h. "
                f"Active offers={br['offers']}, contactable leads={br['contactable_leads']}."
            ),
            "channel": "broker-pipeline",
            "pipeline": "broker",
            "severity": "high",
        })
    br["last_scout"] = today

    if br["offers"] > 0 and br["contactable_leads"] > 0:
        match_run = run_django_json(
            "import json;"
            f"from broker_ops.services import run_matching; results = run_matching(min_score=60.0, dry_run={str(dry_run)});"
            "top = [{'offer': r.get('offer', '')[:80], 'lead': r.get('lead', '')[:80], 'score': r.get('score')} for r in results[:3]];"
            "print(json.dumps({'count': len(results), 'top': top}, default=str))"
        ) or {"count": 0, "top": []}
        match_count = int(match_run.get("count") or 0)
        br["last_match_run"] = today
        br["last_match_count"] = match_count
        if match_count > 0:
            top_lines = [
                f"{item.get('score', '?')}% -> {item.get('offer', 'offer')} -> {item.get('lead', 'lead')}"
                for item in (match_run.get("top") or [])
            ]
            actions.append({
                "agent": "Frederick Banks",
                "action": "BROKER_MATCH_RUN",
                "detail": (
                    f"{'Scored' if dry_run else 'Created/updated'} {match_count} broker matches at 60+ score.\n"
                    + ("\n".join(top_lines[:3]) if top_lines else "Top matches unavailable.")
                ),
                "channel": "broker-pipeline",
                "pipeline": "broker",
            })

        approve_run = run_django_json(
            "import json;"
            f"from broker_ops.services import auto_approve_high_score_matches; count = auto_approve_high_score_matches(min_score=70.0, limit=20, dry_run={str(dry_run)});"
            "print(json.dumps({'count': count}))"
        ) or {"count": 0}
        approved_now = int(approve_run.get("count") or 0)
        br["last_auto_approved"] = approved_now
        if approved_now > 0:
            actions.append({
                "agent": "Frederick Banks",
                "action": "BROKER_AUTO_APPROVE",
                "detail": f"{'Would auto-approve' if dry_run else 'Auto-approved'} {approved_now} high-confidence matches for outreach.",
                "channel": "broker-pipeline",
                "pipeline": "broker",
            })

        sequence_run = run_django_json(
            "import json\n"
            "from broker_ops.models import BrokerMatch\n"
            "from broker_ops.services import create_outreach_sequence\n"
            "created = []\n"
            "matches = BrokerMatch.objects.filter(status='approved').exclude("
            "lead__email__contains='@placeholder.io'"
            ").exclude(lead__email='').select_related('lead', 'offer').prefetch_related('outreach_steps')[:10]\n"
            "for match in matches:\n"
            "    if match.outreach_steps.exists():\n"
            "        continue\n"
            "    steps = create_outreach_sequence(match)\n"
            "    if steps:\n"
            "        created.append({'match_id': str(match.id), 'lead': match.lead.email, 'steps': len(steps), 'score': match.match_score})\n"
            "print(json.dumps({'count': len(created), 'items': created}, default=str))"
        ) or {"count": 0, "items": []}
        sequences_created = int(sequence_run.get("count") or 0)
        br["last_sequences_created"] = sequences_created
        if sequences_created > 0:
            seq_preview = [
                f"{item.get('score', '?')}% -> {item.get('lead', 'lead')} ({item.get('steps', 0)} steps)"
                for item in (sequence_run.get("items") or [])[:3]
            ]
            actions.append({
                "agent": "Piper Reeves",
                "action": "BROKER_SEQUENCE_BUILD",
                "detail": (
                    f"{'Would build' if dry_run else 'Built'} outreach sequences for {sequences_created} approved matches.\n"
                    + ("\n".join(seq_preview) if seq_preview else "Sequence preview unavailable.")
                ),
                "channel": "broker-pipeline",
                "pipeline": "broker",
            })

    due_steps = run_django_json(
        "import json;"
        "from broker_ops.models import OutreachSequence;"
        "from django.utils import timezone;"
        "steps = OutreachSequence.objects.filter(status='pending', scheduled_at__lte=timezone.now(), match__lead__unsubscribed=False)"
        ".exclude(to_email__iendswith='@placeholder.io')"
        ".exclude(to_email__iendswith='@example.com')"
        ".exclude(to_email__iendswith='@example.org')"
        ".exclude(to_email__iendswith='@example.net')"
        ".exclude(to_email__istartswith='test@')"
        ".exclude(to_email__istartswith='demo@')"
        ".exclude(to_email__istartswith='sample@')"
        ".exclude(to_email__istartswith='noreply@')"
        ".exclude(to_email__istartswith='no-reply@')"
        ".select_related('match', 'match__lead', 'match__offer').order_by('scheduled_at')[:5];"
        "payload = [{"
        "'id': str(step.id),"
        "'to_email': step.to_email,"
        "'subject': step.subject,"
        "'body': step.body,"
        "'lead_name': step.match.lead.name,"
        "'offer_title': (step.match.offer.title if step.match.offer else ''),"
        "'scheduled_at': step.scheduled_at.isoformat()"
        "} for step in steps];"
        "print(json.dumps(payload, default=str))"
    ) or []
    br["due_outreach"] = len(due_steps)

    if due_steps and not is_business_hours():
        actions.append({
            "agent": "Piper Reeves",
            "action": "BROKER_OUTREACH_QUEUED",
            "detail": f"{len(due_steps)} outreach emails are due but outside legal business hours. They remain queued.",
            "channel": "broker-pipeline",
            "pipeline": "broker",
        })
    elif due_steps and not RESEND_API_KEY:
        actions.append({
            "agent": "Piper Reeves",
            "action": "BROKER_OUTREACH_BLOCKED",
            "detail": f"{len(due_steps)} outreach emails are due but RESEND_API_KEY is missing, so nothing can send.",
            "channel": "broker-pipeline",
            "pipeline": "broker",
            "severity": "critical",
        })
    elif due_steps:
        sent = 0
        sent_preview = []
        failures = []
        for step in due_steps:
            if dry_run:
                sent += 1
                sent_preview.append(f"{step.get('to_email')} <- {step.get('offer_title') or 'offer'}")
                continue
            ok = send_email(
                step.get("to_email", ""),
                step.get("subject", "Everlight Ventures intro"),
                step.get("body", "").replace("\n", "<br>"),
            )
            if ok:
                mark_result = run_django_query(
                    "from broker_ops.models import OutreachSequence;"
                    "from broker_ops.services import mark_outreach_sent;"
                    f"step = OutreachSequence.objects.select_related('match', 'match__lead').get(id='{step.get('id', '')}');"
                    "mark_outreach_sent(step);"
                    "print('ok')"
                )
                if "ok" in mark_result:
                    sent += 1
                    sent_preview.append(f"{step.get('to_email')} <- {step.get('offer_title') or 'offer'}")
                else:
                    failures.append(f"{step.get('to_email')}: mark failed")
            else:
                failures.append(f"{step.get('to_email')}: send failed")

        if sent > 0:
            br["due_outreach"] = max(br["due_outreach"] - sent, 0)
            actions.append({
                "agent": "Piper Reeves",
                "action": "BROKER_OUTREACH_SENT",
                "detail": (
                    f"{'Would send' if dry_run else 'Sent'} {sent} broker outreach emails.\n"
                    + "\n".join(sent_preview[:5])
                ),
                "channel": "broker-pipeline",
                "pipeline": "broker",
            })
        if failures:
            actions.append({
                "agent": "Piper Reeves",
                "action": "BROKER_OUTREACH_FAIL",
                "detail": "\n".join(failures[:5]),
                "channel": "broker-pipeline",
                "pipeline": "broker",
                "severity": "high",
            })

    actions.append({
        "agent": "Sebastian Navarro",
        "action": "BROKER_SUMMARY",
        "detail": (
            "Broker OS live snapshot:\n"
            f"  Offers: {br['offers']} ({br['fresh_offers']} new/24h)\n"
            f"  Contactable leads: {br['contactable_leads']} ({br['fresh_leads']} new/24h)\n"
            f"  Matches: pending {br['pending_matches']} | approved {br['approved_matches']} | converted {br['converted_matches']}\n"
            f"  Outreach due now: {br['due_outreach']}\n"
            f"  Deals: active {br['active_deals']} | won {br['closed_won']}"
        ),
        "channel": "broker-pipeline",
        "pipeline": "broker",
    })


# ---------------------------------------------------------------------------
# Pipeline 7: Revenue Tracker
# ---------------------------------------------------------------------------
def manage_revenue_tracking(state: dict, actions: list, dry_run: bool = False):
    """Track revenue across all streams and post updates."""
    rv = state.setdefault("revenue", {})
    log.info("--- Revenue Tracking ---")

    hour = datetime.now(PT).hour
    if hour % 4 != 0:
        return  # Every 4 hours only

    bot_state = read_json(f"{BOT_DIR}/data/state.json")
    surplus_tracker = read_json(f"{WHOLESALE_DIR}/surplus_claims_tracker.json")
    broker_revenue = run_django_json(
        "import json;"
        "from broker_ops.services import get_commission_summary;"
        "print(json.dumps(get_commission_summary(), default=str))"
    ) or {}

    wholesale_value = state.get("wholesale", {}).get("pipeline_value", 0)
    bot_pnl = float(bot_state.get("exchange_pnl_today_usd") or 0.0)
    if abs(bot_pnl) < 0.01:
        bot_pnl = float(bot_state.get("pnl_today_usd") or 0.0)
    surplus_recovered = surplus_tracker.get("total_recovered", 0)
    surplus_claims = len(surplus_tracker.get("claims", []))
    earned_total = float(broker_revenue.get("earned_total") or 0.0)
    paid_total = float(broker_revenue.get("paid_total") or 0.0)
    pending_total = float(broker_revenue.get("pending_total") or 0.0)
    active_deals = int(broker_revenue.get("active_deals") or 0)
    closed_won = int(broker_revenue.get("closed_won") or 0)

    rv["broker_earned_total"] = earned_total
    rv["broker_paid_total"] = paid_total
    rv["broker_pending_total"] = pending_total
    rv["broker_active_deals"] = active_deals
    rv["broker_closed_won"] = closed_won
    rv["bot_pnl_today"] = bot_pnl
    rv["surplus_recovered"] = surplus_recovered
    rv["wholesale_pipeline_value"] = wholesale_value

    total_earned = earned_total + surplus_recovered
    if bot_pnl > 0:
        total_earned += bot_pnl

    # Calculate days left in month and daily target
    now = datetime.now(PT)
    days_in_month = 30
    days_left = days_in_month - now.day
    monthly_target = 10000
    daily_target = (monthly_target - total_earned) / max(days_left, 1)

    actions.append({
        "agent": "Penny Vance",
        "action": "REVENUE_REPORT",
        "detail": (
            f"Revenue Report ({now.strftime('%b %d')}):\n"
            f"  Total earned this month: ${total_earned:,.2f}\n"
            f"  Broker earned: ${earned_total:,.2f} | paid: ${paid_total:,.2f} | pending: ${pending_total:,.2f}\n"
            f"  Broker deals: active {active_deals} | won {closed_won}\n"
            f"  Surplus recovered: ${surplus_recovered:,.2f} ({surplus_claims} claims)\n"
            f"  Bot PnL today: ${bot_pnl:,.2f}\n"
            f"  Wholesale pipeline: ${wholesale_value:,.0f}\n"
            f"  ---\n"
            f"  Monthly target: ${monthly_target:,.0f}\n"
            f"  Gap: ${max(monthly_target - total_earned, 0):,.2f}\n"
            f"  Days left: {days_left} | Daily target: ${daily_target:,.2f}"
        ),
        "channel": "ft-profit-engine",
        "pipeline": "revenue",
    })


# ---------------------------------------------------------------------------
# Pipeline 8: Self-Healing Monitor
# ---------------------------------------------------------------------------
def manage_self_healing(state: dict, actions: list, dry_run: bool = False):
    """Check all services and auto-restart failures."""
    sv = state.setdefault("services", {})
    log.info("--- Self-Healing Monitor ---")

    # Services on Oracle E5
    e5_services = [
        "blinko", "n8n", "hive-django", "hive-dashboard",
        "hive-voice", "hive-slack-agent",
    ]

    for svc in e5_services:
        status = run_command(f"systemctl is-active {svc}.service 2>/dev/null").strip()
        sv[svc] = status
        if status != "active":
            if not dry_run:
                restart_result = run_command(f"sudo systemctl restart {svc}.service 2>&1")
                # Verify it came back
                time.sleep(2)
                new_status = run_command(f"systemctl is-active {svc}.service 2>/dev/null").strip()
                detail = (
                    f"ALERT: {svc} was {status}. Restarted -> now {new_status}.\n"
                    f"{restart_result[:200]}"
                )
            else:
                detail = f"(dry-run) Would restart {svc} (currently {status})"
                new_status = status
            actions.append({
                "agent": "Quinn Sharp",
                "action": "SERVICE_RESTART",
                "detail": detail,
                "channel": "hive-alerts",
                "pipeline": "infra",
                "severity": "high" if new_status != "active" else "medium",
            })

    # Check bot services on Oracle Micro (remote check via SSH)
    bot_services = ["xlm-bot", "xlm-dashboard"]
    for svc in bot_services:
        status = run_command(
            f"ssh -o ConnectTimeout=5 -i /root/.ssh/oracle_key.pem "
            f"opc@163.192.19.196 'systemctl is-active {svc}.service' 2>/dev/null"
        ).strip()
        if not status or "ssh" in status.lower():
            status = "unreachable"
        sv[svc] = status
        if status not in ("active", "unreachable"):
            if not dry_run:
                run_command(
                    f"ssh -o ConnectTimeout=5 -i /root/.ssh/oracle_key.pem "
                    f"opc@163.192.19.196 'sudo systemctl restart {svc}.service' 2>/dev/null"
                )
            actions.append({
                "agent": "Quinn Sharp",
                "action": "BOT_SERVICE_RESTART",
                "detail": f"ALERT: {svc} on Oracle Micro was {status}. Restarted.",
                "channel": "hive-alerts",
                "pipeline": "infra",
                "severity": "high",
            })

    # Disk check
    disk_raw = run_command("df -h / | tail -1 | awk '{print $5}' | tr -d '%'").strip()
    try:
        disk_pct = int(disk_raw)
    except ValueError:
        disk_pct = 0
    sv["disk_pct"] = disk_pct

    if disk_pct > 85:
        if not dry_run:
            # Clean up old logs
            cleanup = run_command(
                "find /tmp -name '*.log' -mtime +7 -delete 2>/dev/null; "
                "find /home/opc -name '*.log' -size +50M -exec truncate -s 10M {} \\; 2>/dev/null; "
                "df -h / | tail -1 | awk '{print $5}'"
            )
        else:
            cleanup = f"(dry-run) Would clean logs. Disk at {disk_pct}%."
        actions.append({
            "agent": "Quinn Sharp",
            "action": "DISK_CLEANUP",
            "detail": f"Disk at {disk_pct}%. Cleaned old logs.\n{cleanup[:200]}",
            "channel": "hive-alerts",
            "pipeline": "infra",
            "severity": "high",
        })

    # Check for error patterns in key log files
    log_files = {
        "/tmp/hive_shift.log": "Shift System",
        "/tmp/hive_work.log": "Work Engine",
        "/tmp/hive_orchestrator.log": "Orchestrator",
    }
    for logfile, label in log_files.items():
        error_count = run_command(
            f"tail -200 {logfile} 2>/dev/null | grep -c 'ERROR\\|FAIL\\|Traceback' || echo 0"
        ).strip()
        try:
            errors = int(error_count)
        except ValueError:
            errors = 0
        if errors > 10:
            # Get sample errors
            sample = run_command(
                f"tail -200 {logfile} 2>/dev/null | grep 'ERROR\\|FAIL\\|Traceback' | tail -3"
            )
            actions.append({
                "agent": "Quinn Sharp",
                "action": "LOG_ALERT",
                "detail": (
                    f"{label} ({logfile}) has {errors} errors in last 200 lines.\n"
                    f"Sample:\n{sample[:300]}"
                ),
                "channel": "hive-alerts",
                "pipeline": "infra",
            })

    # Memory check
    mem_raw = run_command("free -m | awk '/Mem:/ {printf \"%.0f\", $3/$2*100}'").strip()
    try:
        mem_pct = int(mem_raw)
    except ValueError:
        mem_pct = 0
    sv["mem_pct"] = mem_pct

    if mem_pct > 90:
        actions.append({
            "agent": "Quinn Sharp",
            "action": "MEM_ALERT",
            "detail": f"Memory at {mem_pct}%. Consider restarting heavy services.",
            "channel": "hive-alerts",
            "pipeline": "infra",
            "severity": "high",
        })


# ---------------------------------------------------------------------------
# Pipeline 9: Freelance / Content (Lighter touch)
# ---------------------------------------------------------------------------
def manage_freelance_pipeline(state: dict, actions: list, dry_run: bool = False):
    """
    Freelance revenue pipeline. Lighter automation -- mainly status checks.
    """
    fl = state.setdefault("freelance", {})
    log.info("--- Freelance Pipeline ---")

    # Only check twice daily (9 AM and 3 PM)
    hour = datetime.now(PT).hour
    if hour not in (9, 15):
        return

    # Check for any gig platform activity (future: Fiverr/Upwork API)
    actions.append({
        "agent": "Ryan Kim",
        "action": "FREELANCE_CHECK",
        "detail": (
            "Freelance pipeline check:\n"
            "  Fiverr: Not yet listed (needs human account setup)\n"
            "  Upwork: Not yet listed (needs human account setup)\n"
            "  Action: Human needs to create accounts and list gigs.\n"
            "  Templates ready at: wholesale_agent/ace_pitch_engine.py"
        ),
        "channel": "ft-consult",
        "pipeline": "freelance",
    })


# ---------------------------------------------------------------------------
# Pipeline 10: Publishing / Content (Passive, weekly check)
# ---------------------------------------------------------------------------
def manage_publishing_pipeline(state: dict, actions: list, dry_run: bool = False):
    """Publishing revenue -- weekly check on KDP stats and content queue."""
    pb = state.setdefault("publishing", {})
    log.info("--- Publishing Pipeline ---")

    # Only run Mondays at 10 AM
    now = datetime.now(PT)
    if now.weekday() != 0 or now.hour != 10:
        return

    actions.append({
        "agent": "Marcus Cole",
        "action": "PUBLISHING_REVIEW",
        "detail": (
            "Weekly Publishing Review:\n"
            "  Books live: Sam's First Superpower, Sam's Second Superpower, Beyond the Veil\n"
            "  Action items:\n"
            "  - Check KDP dashboard for royalties\n"
            "  - Review content factory queue for new material\n"
            "  - Consider social media promotion push"
        ),
        "channel": "ft-profit-engine",
        "pipeline": "publishing",
    })


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
PIPELINE_MANAGERS = {
    "wholesale": manage_wholesale_pipeline,
    "surplus": manage_surplus_pipeline,
    "creative_finance": manage_creative_finance,
    "bot": manage_bot_watchdog,
    "consulting": manage_consulting_pipeline,
    "broker": manage_broker_pipeline,
    "revenue": manage_revenue_tracking,
    "infra": manage_self_healing,
    "freelance": manage_freelance_pipeline,
    "publishing": manage_publishing_pipeline,
}


def run_orchestrator(
    dry_run: bool = False,
    force: bool = False,
    pipeline: str | None = None,
):
    """Main orchestrator loop. Runs all pipeline managers, executes actions, reports."""
    now = datetime.now(PT)

    # Lock check -- prevent overlapping runs
    if not force and LOCK_FILE.exists():
        try:
            lock_ts = float(LOCK_FILE.read_text().strip())
            age_min = (time.time() - lock_ts) / 60
            if age_min < 55:  # Lock valid for 55 min
                log.info("Orchestrator already ran %.0f min ago. Use --force to override.", age_min)
                return 0
        except (ValueError, OSError):
            pass

    # Write lock
    try:
        LOCK_FILE.write_text(str(time.time()))
    except OSError:
        pass

    state = load_state()
    actions: list[dict] = []

    log.info("=" * 70)
    log.info("DEAL ORCHESTRATOR | %s | Run #%d", now.strftime("%Y-%m-%d %I:%M %p PT"), state.get("run_count", 0) + 1)
    if dry_run:
        log.info("MODE: DRY RUN -- no actions will be executed")
    if pipeline:
        log.info("PIPELINE FILTER: %s only", pipeline)
    log.info("=" * 70)

    # Run pipeline managers
    managers_to_run = (
        {pipeline: PIPELINE_MANAGERS[pipeline]}
        if pipeline and pipeline in PIPELINE_MANAGERS
        else PIPELINE_MANAGERS
    )

    for name, manager in managers_to_run.items():
        try:
            manager(state, actions, dry_run=dry_run)
        except Exception as e:
            log.error("Pipeline %s crashed: %s", name, e)
            actions.append({
                "agent": "Quinn Sharp",
                "action": "PIPELINE_CRASH",
                "detail": f"Pipeline '{name}' crashed: {e}",
                "channel": "hive-alerts",
                "pipeline": name,
                "severity": "critical",
            })

    # Execute actions: post to Slack and log
    executed = 0
    high_priority = 0
    critical = 0

    for action in actions:
        severity = action.get("severity", "normal")
        if severity == "high":
            high_priority += 1
        elif severity == "critical":
            critical += 1

        # Slack message formatting
        severity_prefix = ""
        if severity == "critical":
            severity_prefix = "[CRITICAL] "
        elif severity == "high":
            severity_prefix = "[HIGH] "

        msg = f"*{action['agent']}* [{action['action']}] {severity_prefix}\n{action['detail']}"

        if not dry_run:
            post_to_slack(action["channel"], msg)
            log_action(action)
        else:
            log.info("  DRY-RUN -> #%s: %s", action["channel"], msg[:120])

        executed += 1
        time.sleep(0.5)  # Light rate limiting on Slack

    # War room summary
    if executed > 0:
        summary_parts = [
            f"*Deal Orchestrator* -- {executed} actions this cycle.",
        ]
        if critical > 0:
            summary_parts.append(f"{critical} CRITICAL.")
        if high_priority > 0:
            summary_parts.append(f"{high_priority} high priority.")

        # Per-pipeline breakdown
        pipeline_counts: dict[str, int] = {}
        for a in actions:
            p = a.get("pipeline", "other")
            pipeline_counts[p] = pipeline_counts.get(p, 0) + 1
        breakdown = " | ".join(f"{k}: {v}" for k, v in sorted(pipeline_counts.items()))
        summary_parts.append(f"Breakdown: {breakdown}")

        summary = " ".join(summary_parts)
        if not dry_run:
            post_to_slack("war-room", summary)
        else:
            log.info("  DRY-RUN SUMMARY -> %s", summary)

    # Log to Blinko (best effort)
    if executed > 0 and not dry_run:
        log_to_blinko(
            f"{executed} actions, {critical} critical",
            f"Run #{state.get('run_count', 0)+1} at {now.strftime('%I:%M %p PT')}\n"
            f"Pipelines: {', '.join(managers_to_run.keys())}\n"
            f"Critical: {critical} | High: {high_priority} | Normal: {executed - high_priority - critical}"
        )

    save_state(state)
    log.info("Orchestrator complete: %d actions (%d critical, %d high)", executed, critical, high_priority)

    # Cleanup lock
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass

    return executed


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------
def print_status():
    """Print the current state of all pipelines."""
    state = load_state()
    now = datetime.now(PT)

    print("=" * 70)
    print(f"DEAL ORCHESTRATOR STATUS -- {now.strftime('%Y-%m-%d %I:%M %p PT')}")
    print(f"Last run: {state.get('last_run', 'never')}")
    print(f"Total runs: {state.get('run_count', 0)}")
    print(f"Business hours (PT): {'YES' if is_business_hours() else 'NO'}")
    print(f"Business hours (ET): {'YES' if is_business_hours_et() else 'NO'}")
    print("=" * 70)

    # Wholesale
    ws = state.get("wholesale", {})
    print(f"\n  WHOLESALE REAL ESTATE")
    print(f"    Leads: {ws.get('leads', '?')} | Buyers: {ws.get('buyers', '?')}")
    print(f"    New matches: {ws.get('new_matches', '?')} | Offered: {ws.get('offered', '?')} | Negotiating: {ws.get('negotiating', '?')}")
    print(f"    Pipeline value: ${ws.get('pipeline_value', 0):,.0f}")

    # Surplus
    sp = state.get("surplus", {})
    print(f"\n  SURPLUS FUNDS")
    print(f"    Claims: {sp.get('claims_count', 0)} | Recovered: ${sp.get('total_recovered', 0):,.0f}")
    print(f"    Last scan: {sp.get('last_scan', 'never')}")

    # Bot
    bt = state.get("bot", {})
    print(f"\n  XLM BOT")
    print(f"    Service: {bt.get('service_status', '?')}")
    print(f"    Position: {bt.get('position', '?')} | Vol: {bt.get('vol_state', '?')}")
    print(f"    Equity: ${bt.get('equity', 0):.2f} | PnL today: ${bt.get('pnl_today', 0):.2f}")
    print(f"    Trades: {bt.get('trades_today', '?')} | Consec losses: {bt.get('consec_losses', '?')}")

    # Consulting
    cs = state.get("consulting", {})
    print(f"\n  AI CONSULTING")
    print(f"    Leads: {cs.get('total_leads', 0)} | Unscored: {cs.get('unscored', 0)} | Qualified: {cs.get('qualified', 0)}")
    print(f"    Last scout: {cs.get('last_scout', 'never')}")

    # Broker
    br = state.get("broker", {})
    print(f"\n  BROKER OS")
    print(f"    Offers: {br.get('offers', 0)} | Contactable leads: {br.get('contactable_leads', 0)}")
    print(f"    Matches: pending {br.get('pending_matches', 0)} | approved {br.get('approved_matches', 0)} | converted {br.get('converted_matches', 0)}")
    print(f"    Outreach due: {br.get('due_outreach', 0)} | Active deals: {br.get('active_deals', 0)} | Won: {br.get('closed_won', 0)}")
    print(f"    Last scout: {br.get('last_scout', 'never')}")

    # Revenue
    rv = state.get("revenue", {})
    print(f"\n  REVENUE")
    print(f"    Broker earned: ${rv.get('broker_earned_total', 0):,.2f} | pending: ${rv.get('broker_pending_total', 0):,.2f}")
    print(f"    Surplus recovered: ${rv.get('surplus_recovered', 0):,.2f}")
    print(f"    Bot PnL today: ${rv.get('bot_pnl_today', 0):,.2f}")
    print(f"    Wholesale pipeline: ${rv.get('wholesale_pipeline_value', 0):,.0f}")

    # Services
    sv = state.get("services", {})
    if sv:
        print(f"\n  INFRASTRUCTURE")
        for svc, status in sorted(sv.items()):
            if isinstance(status, str):
                tag = "OK" if status == "active" else "DOWN"
                print(f"    [{tag}] {svc}: {status}")
            elif isinstance(status, (int, float)):
                print(f"    {svc}: {status}%")

    # Recent actions from ledger
    if WORK_LEDGER.exists():
        try:
            ledger = json.loads(WORK_LEDGER.read_text())
            orch_actions = ledger.get("orchestrator_actions", [])
            if orch_actions:
                print(f"\n  RECENT ACTIONS (last 10):")
                print(f"  " + "-" * 60)
                for entry in orch_actions[-10:]:
                    ts = entry.get("timestamp", "?")
                    agent = entry.get("agent", "?")
                    action_type = entry.get("action", "?")
                    detail = entry.get("detail", "")[:80].replace("\n", " ")
                    print(f"    {ts}  {agent} [{action_type}] {detail}")
        except (json.JSONDecodeError, OSError):
            pass

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hive Deal Orchestrator -- autonomous pipeline management for all revenue streams"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would execute without doing it",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current state of all pipelines",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Run even if already ran this hour",
    )
    parser.add_argument(
        "--pipeline", type=str, default=None,
        choices=list(PIPELINE_MANAGERS.keys()),
        help="Run a single pipeline only",
    )
    args = parser.parse_args()

    if args.status:
        print_status()
    else:
        run_orchestrator(
            dry_run=args.dry_run,
            force=args.force,
            pipeline=args.pipeline,
        )


if __name__ == "__main__":
    main()
