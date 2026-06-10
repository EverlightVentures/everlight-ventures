"""
Rex Master Pipeline -- the FULL daily automation.

Runs 3 phases every day:
  Phase 1 (8 AM PT): Scout + Score + Outreach sellers + Blast buyers
  Phase 2 (12 PM PT): Follow-up sequences on existing leads
  Phase 3 (5 PM PT): Re-engage cold leads + retry dead letters

Single entry point: python3 rex_master_pipeline.py [phase]
  --phase morning   (default, runs all 3 if no arg)
  --phase followup
  --phase reengage

Cron setup (Oracle):
  0 15 * * * source /home/opc/.env && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase morning
  0 19 * * * source /home/opc/.env && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase followup
  0 0 * * * source /home/opc/.env && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase reengage
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

# Create log dir BEFORE attaching FileHandler (handler opens the file eagerly).
(AGENT_DIR / "logs").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Pipeline %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(AGENT_DIR / "logs" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_pipeline.log"),
    ],
)
log = logging.getLogger("rex_pipeline")

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

# Brain feed is LOCAL-FIRST so it is intact even when e5-mother (the remote vector
# layer) is down. Order: local blinko-lite -> local tunnel -> e5-mother tailnet.
# On total failure we enqueue to the offline drain queue -- a note NEVER vanishes.
# Doctrine: brain-intact-always + [[feedback_offline_first_bidirectional_sync]].
BLINKO_CANDIDATES = [
    "http://127.0.0.1:2700/api/v1/note/upsert",   # local blinko-lite (canonical offline brain)
    "http://127.0.0.1:1111/api/v1/note/upsert",   # local keepalive instance / tunnel
    "http://e5-mother:1111/api/v1/note/upsert",    # remote RAG (when tailnet is up)
]
_BLINKO_QUEUE = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_log_queue")


def post_slack(text: str, title: str = "Rex Master Pipeline"):
    """Post to Slack, creating a GDoc first when possible."""
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title=title,
                content=text,
                folder="01_Broker_OS/Scout_Reports",
                summary=text[:200],
                agent="marcus_cole",
            )
            if result.get("ok"):
                return
        except Exception:
            pass
    # Fallback: raw text post
    try:
        import requests
        if SLACK_TOKEN:
            requests.post("https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
                json={"channel": SLACK_CHANNEL, "text": text}, timeout=10)
    except Exception:
        pass


def log_blinko(summary: str, details: str = ""):
    """Write a session note to the brain, local-first. Falls back to the offline
    queue so the write survives even if every Blinko endpoint is down."""
    import urllib.request
    content = f"# Hive Session: {summary}\n#hive/wholesale #hive/pipeline\n\n{details}"
    body = json.dumps({"content": content, "type": 1}).encode()
    for url in BLINKO_CANDIDATES:
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status < 300:
                    return  # landed in the brain
        except Exception:
            continue
    # Every endpoint failed -- preserve the note in the offline queue (drained later).
    try:
        _BLINKO_QUEUE.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        (_BLINKO_QUEUE / f"wholesale_{stamp}.md").write_text(content)
    except Exception:
        pass


# ===== LANE ROUTING =====
# Each lane maps to: scout module, offer strategy, playbook path.
# Keep this in sync with supabase migration 20260422_wholesale_lanes.sql.
# When `active=False`, the phase_lane() dispatcher skips the lane entirely.
ROUTE_TABLE = {
    "L1": {
        "name": "Code violations / tired landlords",
        "scout_module": "rex_distress_finder",
        "offer_strategy": "seventy_rule",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L1_code_violation.md",
        "active": False,
    },
    "L2": {
        "name": "Pre-foreclosure assignment",
        "scout_module": "rex_zillow_keyword_scraper",
        "offer_strategy": "balance_assignment",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L2_preforeclosure_assignment.md",
        "active": True,
    },
    "L3": {
        "name": "Probate",
        "scout_module": "rex_probate_scout",
        "offer_strategy": "seventy_rule",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L3_probate.md",
        "active": False,
    },
    "L4": {
        "name": "Tax delinquency",
        "scout_module": "rex_tax_delinquency_scout",
        "offer_strategy": "seventy_rule",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L4_tax_delinquency.md",
        "active": False,
    },
    "L5": {
        "name": "Vacant / absentee owner",
        "scout_module": "rex_zillow_keyword_scraper",
        "offer_strategy": "balance_assignment",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L5_vacant_absentee.md",
        "active": False,
    },
    "L6": {
        "name": "Teardown hunt",
        "scout_module": "rex_teardown_finder",
        "offer_strategy": "teardown_80pct",
        "playbook": "../../../01_BUSINESSES/Everlight_Ventures/Wholesale/offers/L6_teardown_hunt.md",
        "active": False,
    },
}

VALID_SCOUT_MODULES = {v["scout_module"] for v in ROUTE_TABLE.values()}


def phase_lane(lane_code: str, dry_run: bool = False):
    """Dispatch a single lane's daily cycle.

    Separate from phase_morning/followup/reengage so existing cron behavior is
    untouched. Once a lane is proven, its call can be folded into phase_morning
    (or kept separate if we want lane-by-lane dispatch for scaling).
    """
    lane = ROUTE_TABLE.get(lane_code.upper())
    if not lane:
        log.error(f"Unknown lane: {lane_code}. Valid: {list(ROUTE_TABLE.keys())}")
        return
    if not lane["active"]:
        log.info(f"Lane {lane_code} is not active yet. Skipping.")
        return

    log.info("=" * 60)
    log.info(f"LANE {lane_code} -- {lane['name']}")
    log.info(f"  scout={lane['scout_module']} offer_strategy={lane['offer_strategy']}")
    log.info("=" * 60)

    scout_module = lane["scout_module"]
    if scout_module not in VALID_SCOUT_MODULES:
        log.error(f"Scout module {scout_module} not in allowlist. Refusing to dispatch.")
        return

    try:
        mod = __import__(scout_module)
    except ImportError as e:
        log.error(f"Lane {lane_code} scout module {scout_module} not importable: {e}")
        return

    if hasattr(mod, "run_lane"):
        try:
            result = mod.run_lane(dry_run=dry_run)
            log.info(f"Lane {lane_code} scout result: {result}")
        except Exception as e:
            log.error(f"Lane {lane_code} scout raised: {e}")
            post_slack(f"*Rex Lane {lane_code} ERROR* -- scout {scout_module} raised: {e}")
            return
    else:
        log.warning(f"Lane {lane_code} scout {scout_module} has no run_lane() -- invoking as script")
        import subprocess
        script_path = AGENT_DIR / f"{scout_module}.py"
        if not script_path.exists():
            log.error(f"Scout script not found: {script_path}")
            return
        try:
            subprocess.run(
                ["python3", str(script_path)],
                cwd=str(AGENT_DIR),
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log.error(f"Scout {scout_module} timed out after 600s")
            return

    post_slack(f"*Rex Lane {lane_code} Complete* -- {lane['name']} ({TODAY})")
    log_blinko(f"Lane {lane_code} run {TODAY}", f"{lane['name']} -- scout {scout_module}")


# ===== PHASE 1: MORNING -- Scout + Score + Outreach + Buyer Blast =====

def phase_morning():
    log.info("=" * 60)
    log.info("PHASE 1: MORNING -- Scout + Score + Outreach + Buyer Blast")
    log.info("=" * 60)

    # Run the existing daily pipeline (which now SENDS buyer blasts)
    try:
        from rex_daily_run import main as daily_run
        daily_run()
    except Exception as e:
        log.error(f"Daily run failed: {e}")
        post_slack(f"*Rex Pipeline ERROR* -- Morning run failed: {e}")
        return

    # Run the SDR fresh outreach (seller emails)
    try:
        from rex_sdr import run_fresh_outreach
        stats = run_fresh_outreach()
        log.info(f"SDR fresh outreach: {stats}")
    except ImportError:
        # SDR might not have run_fresh_outreach as a function, run it directly
        log.info("Running SDR as standalone...")
        import subprocess
        sdr_path = AGENT_DIR / "rex_sdr.py"
        if sdr_path.exists():
            try:
                subprocess.run(["python3", str(sdr_path), "--mode", "fresh"],
                               cwd=str(AGENT_DIR), timeout=600, check=False)
            except subprocess.TimeoutExpired:
                log.error("rex_sdr.py timed out after 600s")
    except Exception as e:
        log.warning(f"SDR fresh outreach error: {e}")

    # Creative finance stream: Rex Batch Offers sends subject-to / owner-finance /
    # lease-option letters to any leads in `apify_leads.json` or `surplus_leads.json`.
    # Gated by daily cap (50 sends/day) and per-address dedup inside rex_batch_offers.
    try:
        from rex_batch_offers import run_batch
        batch_result = run_batch(dry_run=False, offer_type="subject_to")
        log.info(f"Creative finance batch: {batch_result}")
    except ImportError:
        log.debug("rex_batch_offers not importable -- skipping creative finance stream")
    except Exception as e:
        log.warning(f"Creative finance batch error: {e}")

    post_slack(f"*Rex Morning Pipeline Complete* -- {TODAY}\nScout + Score + Outreach + Buyer Blast + Creative Finance done.")
    log_blinko(f"Morning pipeline {TODAY}", "Scouted leads, scored, sent seller outreach, blasted buyers, ran creative finance batch.")


# ===== PHASE 2: MIDDAY -- Follow-up sequences =====

def phase_followup():
    log.info("=" * 60)
    log.info("PHASE 2: MIDDAY -- Follow-up sequences")
    log.info("=" * 60)

    try:
        from rex_sdr import run_followups
        stats = run_followups()
        log.info(f"Follow-ups sent: {stats}")
    except ImportError:
        log.info("Running SDR followup as standalone...")
        os.system(f"cd {AGENT_DIR} && python3 rex_sdr.py --mode followup 2>&1 | tail -20")
    except Exception as e:
        log.warning(f"Follow-up error: {e}")

    post_slack(f"*Rex Follow-up Run* -- {TODAY}")
    log_blinko(f"Follow-up run {TODAY}", "Sent sequence follow-ups to warm leads.")


# ===== PHASE 3: EVENING -- Re-engage + Retry dead letters =====

def phase_reengage():
    log.info("=" * 60)
    log.info("PHASE 3: EVENING -- Re-engage + Retry dead letters")
    log.info("=" * 60)

    # Re-engage cold leads
    try:
        from rex_sdr import run_reengagement
        stats = run_reengagement()
        log.info(f"Re-engagement sent: {stats}")
    except ImportError:
        log.info("Running SDR reengage as standalone...")
        os.system(f"cd {AGENT_DIR} && python3 rex_sdr.py --mode reengage 2>&1 | tail -20")
    except Exception as e:
        log.warning(f"Re-engage error: {e}")

    # Retry dead letters
    retry_dead_letters()

    post_slack(f"*Rex Evening Run* -- {TODAY}\nRe-engaged cold leads + retried dead letters.")
    log_blinko(f"Evening pipeline {TODAY}", "Re-engaged cold leads and retried failed emails.")


def retry_dead_letters():
    """Retry emails that failed due to quota limits."""
    dead_dir = AGENT_DIR / "failed_emails"
    if not dead_dir.exists():
        return

    retried = 0
    failed = 0

    for dead_file in sorted(dead_dir.glob("*_dead_letters.jsonl")):
        remaining = []
        with open(dead_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                to = entry.get("to", "")
                subject = entry.get("subject", "")
                body = entry.get("body", entry.get("text", ""))
                if not to or not subject:
                    continue

                # Try sending
                from rex_daily_run import send_buyer_email
                ok = send_buyer_email(to, subject, body)
                if ok:
                    retried += 1
                    time.sleep(2)
                else:
                    remaining.append(line)
                    failed += 1

                # Don't burn through quota -- cap retries per file
                if retried >= 20:
                    remaining.extend(line for line in f)
                    break

        # Rewrite file with only the still-failed ones
        if remaining:
            with open(dead_file, "w") as f:
                f.write("\n".join(remaining) + "\n")
        else:
            dead_file.unlink()

    if retried > 0:
        log.info(f"  Dead letter retry: {retried} sent, {failed} still failed")
        post_slack(f"*Dead Letter Retry* -- {retried} emails recovered, {failed} still pending")


# ===== MAIN =====

def main():
    parser = argparse.ArgumentParser(description="Rex Master Pipeline")
    parser.add_argument("--phase", default="morning", choices=["morning", "followup", "reengage", "all"])
    parser.add_argument("--lane", default="", help="Run a single lane (L1-L6). Overrides --phase when set.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending or writing.")
    args = parser.parse_args()

    if args.lane:
        phase_lane(args.lane, dry_run=args.dry_run)
        return

    if args.phase == "morning":
        phase_morning()
    elif args.phase == "followup":
        phase_followup()
    elif args.phase == "reengage":
        phase_reengage()
    elif args.phase == "all":
        phase_morning()
        phase_followup()
        phase_reengage()


if __name__ == "__main__":
    main()
