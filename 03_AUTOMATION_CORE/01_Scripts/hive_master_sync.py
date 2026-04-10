#!/usr/bin/env python3
"""Hive Master Sync - keeps phone, Oracle, Supabase, Slack, and Blinko in sync.

Runs after every significant change. Syncs:
1. Workbooks (phone -> Oracle -> Supabase)
2. Report registry (phone -> Oracle -> Supabase)
3. Integration registry (phone -> Oracle -> Supabase)
4. Reports (phone -> Oracle /home/opc/hive_reports/)
5. Posts sync summary to Slack + Blinko

Schedule: every 10 minutes via cron, or manually after builds.

Usage:
    python3 hive_master_sync.py           # full sync
    python3 hive_master_sync.py --quick   # workbooks + registry only
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

# Paths
PHONE_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WHOLESALE_AGENT = PHONE_ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
REPORTS_DIR = PHONE_ROOT / "09_DASHBOARD/reports"
CREDS = PHONE_ROOT / "03_AUTOMATION_CORE/03_Credentials/.env"
XLM_BOT = PHONE_ROOT / "06_DEVELOPMENT/xlm_bot"

ORACLE_IP = "129.159.38.250"
SSH_KEY = "/root/.ssh/oracle_key.pem"
ORACLE_USER = "opc"

# Load env
_env = {}
if CREDS.exists():
    for line in CREDS.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _env[k.strip()] = v.strip()

SUPABASE_URL = _env.get("SUPABASE_URL", "")
SUPABASE_KEY = _env.get("SUPABASE_SERVICE_ROLE_KEY", "")
SLACK_TOKEN = _env.get("SLACK_WARROOM_TOKEN", _env.get("SLACK_BOT_TOKEN", ""))
BLINKO_URL = _env.get("BLINKO_URL", "http://129.159.38.250:1111")


def _ts():
    return datetime.now(timezone.utc).isoformat()


def _scp(local, remote):
    cmd = f"scp -o ConnectTimeout=10 -i {SSH_KEY} {local} {ORACLE_USER}@{ORACLE_IP}:{remote}"
    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
    return r.returncode == 0


def _supabase_upsert(table, data):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        req = Request(
            f"{SUPABASE_URL}/rest/v1/{table}",
            data=json.dumps(data).encode(),
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            method="POST",
        )
        urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def _slack(msg):
    if not SLACK_TOKEN:
        return
    try:
        req = Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": "C0AN4GSTMT5", "text": msg, "unfurl_links": False}).encode(),
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        )
        urlopen(req, timeout=10)
    except Exception:
        pass


def _blinko(summary):
    try:
        req = Request(
            f"{BLINKO_URL}/api/v1/note/upsert",
            data=json.dumps({"content": f"# Hive Sync\n#hive/sync\n\n{summary}", "type": 1}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urlopen(req, timeout=10)
    except Exception:
        pass


def sync_workbooks():
    """Sync wholesale workbooks to Oracle + Supabase."""
    wb_dir = WHOLESALE_AGENT / "data/workbooks"
    synced = []
    if not wb_dir.exists():
        return synced
    for f in wb_dir.glob("*.json"):
        if _scp(str(f), f"/home/opc/wholesale_agent/data/workbooks/{f.name}"):
            synced.append(f.name)
    # Push metrics to Supabase
    metrics_file = wb_dir / "performance_metrics.json"
    if metrics_file.exists():
        try:
            data = json.loads(metrics_file.read_text())
            today = datetime.now(timezone.utc).date().isoformat()
            pipeline = wb_dir / "pipeline_master.json"
            deals = wb_dir / "deal_tracker.json"
            lead_count = 0
            deal_count = 0
            if pipeline.exists():
                pd = json.loads(pipeline.read_text())
                lead_count = len(pd.get("leads", []))
            if deals.exists():
                dd = json.loads(deals.read_text())
                deal_count = len(dd.get("active_deals", []))
            _supabase_upsert("wholesale_metrics", {
                "id": f"wholesale_daily_{today}",
                "date": today,
                "funnel_30d": json.dumps(data.get("funnel_metrics", {}).get("30d", {})),
                "conversion_rates": json.dumps(data.get("conversion_rates", {})),
                "revenue": json.dumps(data.get("revenue", {})),
                "costs": json.dumps(data.get("costs", {})),
                "agent_performance": json.dumps(data.get("agent_performance", {})),
                "active_deals": deal_count,
                "total_leads": lead_count,
            })
        except Exception:
            pass
    return synced


def sync_registries():
    """Sync integration + report registries."""
    synced = []
    reg = REPORTS_DIR / "integration_registry.json"
    if reg.exists():
        _scp(str(reg), "/home/opc/hive_reports/integration_registry.json")
        try:
            data = json.loads(reg.read_text())
            _supabase_upsert("integration_registry", {"id": "master", "data": data})
            synced.append("integration_registry")
        except Exception:
            pass
    rr = REPORTS_DIR / "report_registry.json"
    if rr.exists():
        _scp(str(rr), "/home/opc/hive_reports/report_registry.json")
        synced.append("report_registry")
    return synced


def sync_reports():
    """Sync HTML reports to Oracle."""
    synced = []
    for d in [REPORTS_DIR, WHOLESALE_AGENT]:
        for f in d.glob("*.html"):
            if _scp(str(f), f"/home/opc/hive_reports/{f.name}"):
                synced.append(f.name)
    return synced


def sync_bot_data():
    """Sync XLM bot data files (perplexity context, integration log)."""
    synced = []
    for f in ["data/perplexity_context.json", "data/perplexity_integration_log.json"]:
        path = XLM_BOT / f
        if path.exists():
            if _scp(str(path), f"/home/opc/xlm-bot/{f}"):
                synced.append(path.name)
    return synced


def sync_scripts():
    """Sync key utility scripts."""
    files = [
        (WHOLESALE_AGENT / "gdocs_bridge.py", "/home/opc/wholesale_agent/"),
        (WHOLESALE_AGENT / "report_template.py", "/home/opc/wholesale_agent/"),
        (WHOLESALE_AGENT / "workbook_logger.py", "/home/opc/wholesale_agent/"),
        (WHOLESALE_AGENT / "gdocs_bridge.py", "/home/opc/content_tools/"),
    ]
    synced = []
    for local, remote_dir in files:
        if local.exists() and _scp(str(local), f"{remote_dir}{local.name}"):
            synced.append(local.name)
    return synced


def main():
    quick = "--quick" in sys.argv
    print(f"[SYNC] Starting {'quick' if quick else 'full'} sync at {_ts()}")

    results = {}
    results["workbooks"] = sync_workbooks()
    print(f"  Workbooks: {len(results['workbooks'])} synced")

    results["registries"] = sync_registries()
    print(f"  Registries: {len(results['registries'])} synced")

    if not quick:
        results["reports"] = sync_reports()
        print(f"  Reports: {len(results['reports'])} synced")

        results["scripts"] = sync_scripts()
        print(f"  Scripts: {len(results['scripts'])} synced")

        results["bot_data"] = sync_bot_data()
        print(f"  Bot data: {len(results['bot_data'])} synced")

    total = sum(len(v) for v in results.values())
    summary = f"Sync complete: {total} items across phone/Oracle/Supabase"
    print(f"[SYNC] {summary}")

    _slack(f"*Hive Sync* | {summary}")
    _blinko(summary)

    # Update sync timestamp
    reg = REPORTS_DIR / "integration_registry.json"
    if reg.exists():
        try:
            data = json.loads(reg.read_text())
            data["meta"]["last_synced"] = _ts()
            reg.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


if __name__ == "__main__":
    main()
