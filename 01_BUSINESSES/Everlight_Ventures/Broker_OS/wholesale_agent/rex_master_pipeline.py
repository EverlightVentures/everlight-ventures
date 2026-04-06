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

# Ensure log dir exists
(AGENT_DIR / "logs").mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

BLINKO_URL = "http://129.159.38.250:1111/api/v1/note/upsert"


def post_slack(text: str):
    try:
        import requests
        if SLACK_TOKEN:
            requests.post("https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
                json={"channel": SLACK_CHANNEL, "text": text}, timeout=10)
    except Exception:
        pass


def log_blinko(summary: str, details: str = ""):
    try:
        import requests
        content = f"# Hive Session: {summary}\n#hive/wholesale #hive/pipeline\n\n{details}"
        requests.post(BLINKO_URL,
            headers={"Content-Type": "application/json"},
            json={"content": content, "type": 1}, timeout=10)
    except Exception:
        pass


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
        os.system(f"cd {AGENT_DIR} && python3 rex_sdr.py --mode fresh 2>&1 | tail -20")
    except Exception as e:
        log.warning(f"SDR fresh outreach error: {e}")

    post_slack(f"*Rex Morning Pipeline Complete* -- {TODAY}\nScout + Score + Outreach + Buyer Blast done.")
    log_blinko(f"Morning pipeline {TODAY}", "Scouted leads, scored, sent seller outreach, blasted buyers.")


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
    args = parser.parse_args()

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
