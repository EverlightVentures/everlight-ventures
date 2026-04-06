#!/usr/bin/env python3
"""
Wholesale Hive Pipeline -- Daily Orchestrator
Runs the 12-person wholesale crew through 7 pipeline stages.

Usage:
    python3 wholesale_hive_pipeline.py                    # Full daily run
    python3 wholesale_hive_pipeline.py --stage scout      # Run one stage
    python3 wholesale_hive_pipeline.py --dry-run           # Preview only
    python3 wholesale_hive_pipeline.py --report            # Show last run

Schedule (crontab):
    0 8 * * * python3 /path/to/wholesale_hive_pipeline.py >> /tmp/wholesale_pipeline.log 2>&1
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Paths
WHOLESALE_DIR = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
SCRIPTS_DIR = WHOLESALE_DIR
REPORT_DIR = "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports"
LOG_DIR = "/mnt/sdcard/AA_MY_DRIVE/_logs"
ENV_PATH = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
PIPELINE_STATE = os.path.join(WHOLESALE_DIR, "pipeline/hive_pipeline_state.json")
FAILURE_LOG = os.path.join(LOG_DIR, "wholesale_pipeline_failures.jsonl")

# Slack webhook for #wholesale-deals
SLACK_WEBHOOK = None  # loaded from env


def load_env():
    """Load environment variables from .env file."""
    env = dict(os.environ)
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    return env


def log(msg, level="INFO"):
    """Log with timestamp and level."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S PT")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "wholesale_hive_pipeline.log")
    with open(log_file, "a") as f:
        f.write(line + "\n")


def run_script(script_name, args=None, env=None, timeout=300):
    """Run a Rex script and capture output."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        return {"status": "missing", "error": f"Script not found: {script_path}"}

    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=SCRIPTS_DIR,
        )
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout_lines": len(result.stdout.splitlines()),
            "stderr_preview": result.stderr[:500] if result.stderr else "",
            "output_preview": result.stdout[-500:] if result.stdout else "",
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"Script timed out after {timeout}s"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def slack_post(text, env=None):
    """Post to #wholesale-deals via Slack webhook."""
    webhook = (env or {}).get("SLACK_WEBHOOK_URL")
    if not webhook:
        log("No Slack webhook configured, skipping post", "WARN")
        return
    try:
        import requests
        requests.post(webhook, json={"text": text}, timeout=10)
    except Exception as e:
        log(f"Slack post failed: {e}", "WARN")


def record_failure(script_name, stage_id, result):
    """Append a failure record to the JSONL failure log for trend tracking."""
    os.makedirs(os.path.dirname(FAILURE_LOG), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": script_name,
        "stage": stage_id,
        "error": result.get("error") or result.get("stderr_preview", "")[:500],
        "status": result.get("status", "unknown"),
        "returncode": result.get("returncode"),
        "retry_attempted": True,
    }
    try:
        with open(FAILURE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log(f"  Failure recorded in {FAILURE_LOG}", "WARN")
    except Exception as e:
        log(f"  Could not write failure log: {e}", "ERROR")


# ============================================
# PIPELINE STAGES
# ============================================

STAGES = [
    {
        "id": "scout",
        "name": "Stage 1: Property Scouting",
        "team_member": "Rex Blackwell (Gemini/Scout)",
        "description": "Find distressed properties across 6 target markets",
        "scripts": [
            {"name": "rex_zillow_keyword_scraper.py", "timeout": 600},
            {"name": "rex_autonomous.py", "args": ["--wave", "morning"], "timeout": 600},
            {"name": "rex_distress_finder.py", "timeout": 300},
            {"name": "rex_tax_delinquency_scout.py", "timeout": 300},
            {"name": "rex_probate_scout.py", "timeout": 300},
            {"name": "rex_teardown_finder.py", "timeout": 300},
        ],
    },
    {
        "id": "qualify",
        "name": "Stage 2: Lead Qualification",
        "team_member": "Filter Banks (Codex/Qualifier) + Penny Vance (Codex/Profit)",
        "description": "Score, enrich, and run money math on all new leads",
        "scripts": [
            {"name": "rex_lead_scorer_v2.py", "timeout": 300},
            {"name": "rex_enrichment_engine.py", "timeout": 600},
            {"name": "rex_comp_validator.py", "timeout": 300},
            {"name": "rex_repair_estimator.py", "timeout": 300},
        ],
    },
    {
        "id": "match",
        "name": "Stage 3: Buyer Matching",
        "team_member": "Cupid Osei (Codex/Matcher)",
        "description": "Match qualified properties to cash buyers from investor list",
        "scripts": [
            {"name": "rex_buyer_segmenter.py", "timeout": 300},
        ],
    },
    {
        "id": "pitch",
        "name": "Stage 4: Deal Marketing",
        "team_member": "Ace Morgan (Gemini/Marketing)",
        "description": "Create custom investment pitches for hot deals",
        "scripts": [
            {"name": "rex_deal_sheet.py", "timeout": 300},
        ],
    },
    {
        "id": "outreach",
        "name": "Stage 5: Outreach",
        "team_member": "Piper Reeves (Gemini/Outreach)",
        "description": "Send seller outreach + buyer blasts",
        "scripts": [
            {"name": "rex_sdr.py", "args": ["--mode", "fresh"], "timeout": 300},
            {"name": "rex_buyer_acquisition.py", "timeout": 300},
        ],
    },
    {
        "id": "followup",
        "name": "Stage 6: Follow-Up & Nurture",
        "team_member": "Piper Reeves (Gemini/Outreach) + Hammer Knox (Codex/Closer)",
        "description": "Follow up on warm leads, push deals toward close",
        "scripts": [
            {"name": "rex_sdr.py", "args": ["--mode", "followup"], "timeout": 300},
            {"name": "rex_sdr.py", "args": ["--mode", "reengage"], "timeout": 300},
            {"name": "rex_closer.py", "timeout": 300},
        ],
    },
    {
        "id": "report",
        "name": "Stage 7: Pipeline Report",
        "team_member": "Chart Dawson (Gemini/Analytics) + Cash Moreno (Claude/Auditor)",
        "description": "Generate daily pipeline stats and post to Slack",
        "scripts": [
            {"name": "rex_health.py", "timeout": 120},
        ],
    },
]


def run_stage(stage, env, dry_run=False):
    """Run all scripts in a pipeline stage with self-healing (God Mode Layer 4).

    Self-healing behavior:
    1. Auto-retry -- if a script fails, retry once after 10 seconds.
    2. Route around failure -- if a script fails twice, skip it and continue.
    3. Slack alert -- post to Slack when a script fails after retry.
    4. Failure tracking -- append to JSONL log for recurring failure detection.
    """
    stage_id = stage["id"]
    log(f"\n{'='*60}")
    log(f"{stage['name']}")
    log(f"Team: {stage['team_member']}")
    log(f"Purpose: {stage['description']}")
    log(f"{'='*60}")

    results = []
    skipped = []
    stage_start = time.time()

    for script_info in stage["scripts"]:
        script_name = script_info["name"]
        script_args = script_info.get("args")
        timeout = script_info.get("timeout", 300)

        if dry_run:
            log(f"  [DRY] Would run: {script_name} {' '.join(script_args or [])}")
            results.append({"script": script_name, "status": "dry_run"})
            continue

        log(f"  Running: {script_name} {' '.join(script_args or [])}...")
        start = time.time()
        result = run_script(script_name, args=script_args, env=env, timeout=timeout)
        elapsed = round(time.time() - start, 1)

        status = result["status"]

        # -- Self-healing: auto-retry on first failure --
        if status != "success":
            log(f"  [RETRY] {script_name} failed ({status}), retrying in 10s...", "WARN")
            if result.get("stderr_preview"):
                log(f"        stderr: {result['stderr_preview'][:200]}", "WARN")
            time.sleep(10)

            log(f"  [RETRY] Re-running: {script_name}...")
            retry_start = time.time()
            result = run_script(script_name, args=script_args, env=env, timeout=timeout)
            elapsed = round(time.time() - retry_start, 1)
            result["retried"] = True
            status = result["status"]

            # -- Self-healing: route around failure after second attempt --
            if status != "success":
                log(f"  [SKIP] {script_name} failed twice -- routing around it", "WARN")
                if result.get("stderr_preview"):
                    log(f"        stderr: {result['stderr_preview'][:200]}", "WARN")

                # Slack alert on double failure
                alert_msg = (
                    f"*Pipeline Alert* -- `{script_name}` failed twice in "
                    f"*{stage['name']}*\n"
                    f"Status: {status} | Stage: {stage_id}\n"
                    f"Error: {(result.get('error') or result.get('stderr_preview', ''))[:300]}"
                )
                slack_post(alert_msg, env)

                # Record failure for trend analysis
                record_failure(script_name, stage_id, result)
                skipped.append(script_name)

        emoji = "OK" if status == "success" else "FAIL" if status == "failed" else "SKIP"
        log(f"  [{emoji}] {script_name} -- {status} ({elapsed}s)")

        result["script"] = script_name
        result["elapsed_sec"] = elapsed
        results.append(result)

    stage_elapsed = round(time.time() - stage_start, 1)
    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] in ("failed", "error", "timeout", "missing"))

    summary = f"\n  Stage complete: {succeeded} passed, {failed} failed ({stage_elapsed}s)"
    if skipped:
        summary += f" | Routed around: {', '.join(skipped)}"
    log(summary)

    return {
        "stage_id": stage_id,
        "stage_name": stage["name"],
        "team_member": stage["team_member"],
        "elapsed_sec": stage_elapsed,
        "scripts_run": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


def run_pipeline(stages_to_run=None, dry_run=False):
    """Run the full pipeline or specific stages."""
    env = load_env()
    pipeline_start = time.time()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    log(f"\n{'#'*60}")
    log(f"WHOLESALE HIVE PIPELINE -- Run {run_id}")
    log(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    log(f"{'#'*60}")

    stage_results = []
    for stage in STAGES:
        if stages_to_run and stage["id"] not in stages_to_run:
            log(f"\nSkipping {stage['name']} (not in --stage list)")
            continue
        result = run_stage(stage, env, dry_run=dry_run)
        stage_results.append(result)

    pipeline_elapsed = round(time.time() - pipeline_start, 1)
    total_scripts = sum(r["scripts_run"] for r in stage_results)
    total_passed = sum(r["succeeded"] for r in stage_results)
    total_failed = sum(r["failed"] for r in stage_results)

    # Build summary
    summary = f"""Wholesale Hive Pipeline -- {run_id}
Stages run: {len(stage_results)}/{len(STAGES)}
Scripts run: {total_scripts}
Passed: {total_passed} | Failed: {total_failed}
Total time: {pipeline_elapsed}s

Stage breakdown:"""

    for r in stage_results:
        status_icon = "PASS" if r["failed"] == 0 else "WARN"
        summary += f"\n  [{status_icon}] {r['stage_name']} -- {r['team_member']} ({r['elapsed_sec']}s)"

    log(f"\n{summary}")

    # Save report
    report = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "pipeline_elapsed_sec": pipeline_elapsed,
        "stages_run": len(stage_results),
        "total_scripts": total_scripts,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "stages": stage_results,
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"wholesale_pipeline_{run_id}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    latest_path = os.path.join(REPORT_DIR, "wholesale_pipeline_latest.json")
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2)

    # Post to Slack
    if not dry_run:
        slack_msg = f"*Wholesale Pipeline Complete* -- {run_id}\n"
        slack_msg += f"Scripts: {total_passed}/{total_scripts} passed"
        if total_failed > 0:
            slack_msg += f" | {total_failed} FAILED"
        slack_msg += f" | {pipeline_elapsed}s total"
        slack_post(slack_msg, env)

    # Publish pipeline report to Google Docs
    if not dry_run:
        try:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from content_tools.gdocs_bridge import publish_report as gdocs_publish

            # Build markdown from results
            md_lines = [f"# Wholesale Pipeline Report -- {run_id}", ""]
            md_lines.append(f"**Stages:** {len(stage_results)}/7 | **Scripts:** {total_passed}/{total_scripts} passed | **Time:** {pipeline_elapsed}s")
            md_lines.append("")
            md_lines.append("| Stage | Team | Status | Time |")
            md_lines.append("|-------|------|--------|------|")
            for r in stage_results:
                status = "PASS" if r["failed"] == 0 else "FAIL"
                md_lines.append(f"| {r['stage_name']} | {r['team_member']} | {status} | {r['elapsed_sec']}s |")

            gdocs_result = gdocs_publish(
                title=f"Wholesale_Pipeline_{run_id}",
                content="\n".join(md_lines),
                folder="01_Broker_OS/Deal_Pipeline",
                summary=f"Pipeline: {total_passed}/{total_scripts} passed in {pipeline_elapsed}s",
                app="warroom",
            )
            if gdocs_result.get("ok"):
                log(f"Published to Google Docs: {gdocs_result.get('doc_link', '')}")
        except Exception:
            pass

    log(f"\nReport saved: {report_path}")
    return report


def show_report():
    """Show the latest pipeline report."""
    latest = os.path.join(REPORT_DIR, "wholesale_pipeline_latest.json")
    if not os.path.exists(latest):
        log("No pipeline reports found. Run the pipeline first.")
        return

    with open(latest) as f:
        data = json.load(f)

    log(f"\n{'='*60}")
    log(f"LATEST PIPELINE REPORT -- {data['run_id']}")
    log(f"Time: {data['timestamp']}")
    log(f"Mode: {data['mode']}")
    log(f"Scripts: {data['total_passed']}/{data['total_scripts']} passed, {data['total_failed']} failed")
    log(f"Duration: {data['pipeline_elapsed_sec']}s")
    log(f"{'='*60}")

    for stage in data["stages"]:
        status = "PASS" if stage["failed"] == 0 else "FAIL"
        log(f"\n[{status}] {stage['stage_name']}")
        log(f"       Team: {stage['team_member']}")
        log(f"       Scripts: {stage['succeeded']}/{stage['scripts_run']} passed ({stage['elapsed_sec']}s)")
        for script_result in stage["results"]:
            s = script_result["status"]
            icon = "OK" if s == "success" else "X " if s in ("failed", "error") else "--"
            elapsed = script_result.get("elapsed_sec", 0)
            log(f"         [{icon}] {script_result['script']} ({elapsed}s)")


def main():
    parser = argparse.ArgumentParser(description="Wholesale Hive Pipeline")
    parser.add_argument("--stage", nargs="+",
                        choices=[s["id"] for s in STAGES],
                        help="Run specific stages only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview pipeline without running scripts")
    parser.add_argument("--report", action="store_true",
                        help="Show latest pipeline report")
    parser.add_argument("--list", action="store_true",
                        help="List all pipeline stages and scripts")
    args = parser.parse_args()

    if args.report:
        show_report()
        return

    if args.list:
        log("\nWholesale Hive Pipeline -- 7 Stages, 12 Team Members\n")
        for i, stage in enumerate(STAGES, 1):
            log(f"Stage {i}: {stage['name']}")
            log(f"  Team: {stage['team_member']}")
            log(f"  Scripts: {len(stage['scripts'])}")
            for s in stage["scripts"]:
                log(f"    - {s['name']} {' '.join(s.get('args', []))}")
            log("")
        return

    run_pipeline(stages_to_run=args.stage, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
