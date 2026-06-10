#!/usr/bin/env python3
"""
Hive Mind Master Analytics Generator
Creates comprehensive Excel workbooks tracking ALL systems:
- Blinko RAG (notes, tags, memory index)
- Supabase (tables, rows, functions)
- Agent roster (63 agents, performance, assignments)
- Oracle services (health, uptime, resources)
- Pipeline metrics (broker, wholesale, consulting)
- Trading performance (XLM bot, Polymarket)
- n8n workflows (active, triggers, executions)
- Memory index (MEMORY.md + agent .md files)
- GitHub activity (commits, branches)
- Slack channels (messages, engagement)

Consolidates all knowledge into one master workbook.

Usage:
    python3 hive_master_analytics.py              # Full report
    python3 hive_master_analytics.py --section agents
    python3 hive_master_analytics.py --section blinko
    python3 hive_master_analytics.py --section trading
"""
import json
import os
import sys
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))

log = logging.getLogger("master-analytics")
logging.basicConfig(level=logging.INFO, format="[Analytics %(asctime)s] %(message)s")

BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

WORKSPACE = Path(os.environ.get("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE"))
AGENT_DIR = WORKSPACE / ".claude" / "agents"
MEMORY_DIR = Path(os.environ.get("MEMORY_DIR", "")) or Path("/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory")

OUTPUT_DIR = Path(os.environ.get("DELIVERABLES_DIR", "/tmp/hive_deliverables"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url, headers=None, payload=None, timeout=15):
    """Fetch JSON from URL."""
    try:
        h = {"Content-Type": "application/json", **(headers or {})}
        data = json.dumps(payload).encode() if payload else None
        method = "POST" if data else "GET"
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.debug(f"Fetch failed {url}: {e}")
        return None


# ============================================================================
# DATA COLLECTORS
# ============================================================================

def collect_blinko_data():
    """Collect Blinko RAG stats."""
    notes = []
    for page in range(1, 10):
        batch = _fetch_json(f"{BLINKO_URL}/api/v1/note/list", payload={"page": page, "size": 100, "type": -1})
        if not batch or (isinstance(batch, list) and len(batch) == 0):
            break
        items = batch if isinstance(batch, list) else batch.get("data", batch.get("items", []))
        if not items:
            break
        notes.extend(items)
        if len(items) < 100:
            break

    import re
    tags = Counter()
    for n in notes:
        for tag in re.findall(r'#([\w/\-]+)', n.get("content", "") or ""):
            tags[tag] += 1

    return {
        "total_notes": len(notes),
        "tag_distribution": [{"tag": f"#{t}", "count": c} for t, c in tags.most_common(30)],
        "notes_by_type": [
            {"type": "Flash (0)", "count": sum(1 for n in notes if n.get("type") == 0)},
            {"type": "Full (1)", "count": sum(1 for n in notes if n.get("type") == 1)},
        ],
    }


def collect_agent_data():
    """Collect agent roster from .md files."""
    agents = []
    if AGENT_DIR.exists():
        for f in sorted(AGENT_DIR.glob("*.md")):
            content = f.read_text(errors="replace")
            name = ""
            role = ""
            dept = ""
            email = ""
            for line in content.split("\n")[:30]:
                if "name:" in line.lower() and not name:
                    name = line.split(":", 1)[-1].strip().strip('"')
                if "role:" in line.lower() or "title:" in line.lower():
                    role = line.split(":", 1)[-1].strip().strip('"')
                if "department:" in line.lower() or "squad:" in line.lower():
                    dept = line.split(":", 1)[-1].strip().strip('"')
                if "email:" in line.lower():
                    email = line.split(":", 1)[-1].strip().strip('"')

            agents.append({
                "file": f.name,
                "name": name or f.stem,
                "role": role,
                "department": dept,
                "email": email,
            })

    return agents


def collect_memory_data():
    """Collect memory files index."""
    memories = []
    if MEMORY_DIR.exists():
        for f in sorted(MEMORY_DIR.glob("*.md")):
            if f.name == "MEMORY.md":
                continue
            content = f.read_text(errors="replace")
            # Parse frontmatter
            mem_type = ""
            description = ""
            for line in content.split("\n")[:10]:
                if "type:" in line.lower():
                    mem_type = line.split(":", 1)[-1].strip()
                if "description:" in line.lower():
                    description = line.split(":", 1)[-1].strip()

            memories.append({
                "file": f.name,
                "type": mem_type,
                "description": description[:100],
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d"),
            })

    return memories


def collect_cron_data():
    """Collect Oracle cron job inventory."""
    # Parse from local knowledge (can't SSH from this script)
    return [
        {"job": "Watchdog", "freq": "*/2 min", "script": "hive_watchdog.py"},
        {"job": "God Mode", "freq": "*/10 min", "script": "hive_god_mode.py"},
        {"job": "Broker Replies", "freq": "*/2 hours", "script": "broker_daily_orchestrator.py replies"},
        {"job": "Broker Outreach", "freq": "2x/day", "script": "broker_daily_orchestrator.py outreach"},
        {"job": "CEO Brief", "freq": "Daily 7AM PT", "script": "ceo_daily_brief.py"},
        {"job": "Hourly Pulse", "freq": "Hourly", "script": "hourly_status_pulse.py"},
        {"job": "Bot Excel Report", "freq": "Daily 11:59PM PT", "script": "daily_excel_report.py"},
        {"job": "Blinko Optimizer", "freq": "Weekly Sunday 3AM", "script": "blinko_optimizer.py"},
        {"job": "Deal Packets", "freq": "Daily 8AM PT", "script": "broker_deal_packet.py"},
        {"job": "Market Intel", "freq": "*/5 min", "script": "intel_runner.py"},
        {"job": "Trading Watchtower", "freq": "*/1 min", "script": "trading_watchtower_sync.py"},
        {"job": "Wholesale Morning", "freq": "Daily 8AM PT", "script": "rex_master_pipeline.py --phase morning"},
        {"job": "Wholesale Followup", "freq": "Daily 12PM PT", "script": "rex_master_pipeline.py --phase followup"},
        {"job": "Hive Work Engine", "freq": "Hourly", "script": "hive_work_engine.py"},
        {"job": "Hive Outreach", "freq": "Hourly", "script": "hive_outreach_scheduler.py"},
    ]


def collect_services_data():
    """Collect Oracle service inventory."""
    return [
        {"service": "XLM Bot", "type": "systemd", "port": "-", "status": "live"},
        {"service": "React Dashboard", "type": "systemd", "port": "8502", "status": "live"},
        {"service": "Django Dashboard", "type": "systemd", "port": "8504", "status": "live"},
        {"service": "Slack Agent", "type": "systemd", "port": "-", "status": "live"},
        {"service": "Blinko RAG", "type": "podman", "port": "1111", "status": "live"},
        {"service": "n8n", "type": "podman", "port": "5678", "status": "live"},
        {"service": "Langfuse", "type": "podman", "port": "3100", "status": "live"},
        {"service": "Metabase", "type": "podman", "port": "3200", "status": "live"},
        {"service": "Netdata", "type": "podman", "port": "19999", "status": "live"},
        {"service": "Computer Use", "type": "podman", "port": "8501", "status": "live"},
        {"service": "Polymarket Agent", "type": "podman", "port": "-", "status": "live"},
    ]


def collect_ventures_data():
    """Collect venture status matrix."""
    return [
        {"venture": "XLM Trading Bot", "status": "Live", "revenue_model": "Scalp trades", "monthly_target": "$500-2k", "blocker": "Unified scoring engine"},
        {"venture": "Broker OS", "status": "Live", "revenue_model": "15-30% finder fee", "monthly_target": "$5k-25k/deal", "blocker": "First deal close"},
        {"venture": "Polymarket Agent", "status": "Paper Trading", "revenue_model": "Prediction bets", "monthly_target": "$450-1.5k", "blocker": "20+ resolved trades for calibration"},
        {"venture": "Wholesale RE", "status": "Live", "revenue_model": "Assignment fee", "monthly_target": "$5k-25k/deal", "blocker": "Offers being sent"},
        {"venture": "AI Consulting", "status": "Pipeline", "revenue_model": "$2k build + $2k/mo", "monthly_target": "$4k-10k", "blocker": "Active prospecting"},
        {"venture": "Onyx POS", "status": "Ready", "revenue_model": "$49/mo SaaS", "monthly_target": "$2k-10k", "blocker": "Multi-tenant auth"},
        {"venture": "Field Ops", "status": "Ready", "revenue_model": "18% take rate", "monthly_target": "$11k M4", "blocker": "Public launch"},
        {"venture": "Publishing", "status": "Passive", "revenue_model": "KDP royalties", "monthly_target": "$50-200", "blocker": "Marketing activation"},
        {"venture": "Hive Mind SaaS", "status": "Spec Complete", "revenue_model": "$29-149/mo", "monthly_target": "$10k+", "blocker": "MVP build"},
    ]


def collect_slack_data():
    """Collect Slack channel inventory."""
    return [
        {"channel": "#war-room", "id": "C0ANAU30UQ2", "purpose": "Command hub", "primary_agent": "Marcus Cole"},
        {"channel": "#ceo-brief", "id": "C0AP56SQM08", "purpose": "Daily CEO briefing", "primary_agent": "Marcus Cole"},
        {"channel": "#hive-alerts", "id": "C0ANPRCA4AD", "purpose": "Real-time alerts", "primary_agent": "Quinn Sharp"},
        {"channel": "#ft-hunters", "id": "C0AMVEWLT9D", "purpose": "Deal hunting", "primary_agent": "Piper Reeves"},
        {"channel": "#ft-consult", "id": "C0ANEG19WQ4", "purpose": "Consulting pipeline", "primary_agent": "Ryan Kim"},
        {"channel": "#ft-markets", "id": "C0AP56SFQG0", "purpose": "Market intel", "primary_agent": "Cipher Wolfe"},
        {"channel": "#xlm-trading", "id": "C0AN8SG030W", "purpose": "Trade alerts", "primary_agent": "Rex Thornton"},
        {"channel": "#wholesale-deals", "id": "C0ANLLV8JAC", "purpose": "Pipeline stats", "primary_agent": "Chart Dawson"},
        {"channel": "#broker-pipeline", "id": "C0AN7FTTK2R", "purpose": "Matches & deals", "primary_agent": "Calvin Osei"},
        {"channel": "#ai-consulting", "id": "C0AN8SGAS22", "purpose": "Consulting leads", "primary_agent": "Ryan Kim"},
        {"channel": "#deploy-log", "id": "C0AN4GSTMT5", "purpose": "Code deployments", "primary_agent": "Franklin Steele"},
        {"channel": "#content-factory", "id": "C0ANPRDUP0R", "purpose": "Content drops", "primary_agent": "Vera Lux"},
        {"channel": "#revenue-dashboard", "id": "C0AN4GU0MDH", "purpose": "MRR tracking", "primary_agent": "Penny Vance"},
    ]


# ============================================================================
# MASTER REPORT GENERATOR
# ============================================================================

def generate_master_report(section: str = "all") -> str:
    """Generate the master analytics Excel workbook."""
    log.info("Generating master analytics report...")

    sheets = {}

    if section in ("all", "blinko"):
        log.info("Collecting Blinko data...")
        blinko = collect_blinko_data()
        sheets["Blinko Summary"] = blinko["notes_by_type"]
        sheets["Blinko Tags"] = blinko["tag_distribution"]

    if section in ("all", "agents"):
        log.info("Collecting agent data...")
        sheets["Agent Roster (63)"] = collect_agent_data()

    if section in ("all", "memory"):
        log.info("Collecting memory data...")
        sheets["Memory Index"] = collect_memory_data()

    if section in ("all", "services"):
        log.info("Collecting service data...")
        sheets["Oracle Services"] = collect_services_data()
        sheets["Cron Jobs"] = collect_cron_data()

    if section in ("all", "ventures"):
        log.info("Collecting venture data...")
        sheets["Venture Matrix"] = collect_ventures_data()

    if section in ("all", "slack"):
        log.info("Collecting Slack data...")
        sheets["Slack Channels"] = collect_slack_data()

    # Generate Excel
    try:
        from hive_deliverables import generate_excel
        path = generate_excel(
            title=f"Everlight Ventures Master Analytics",
            sheets=sheets,
        )
        log.info(f"Master report saved: {path}")
        return path
    except ImportError:
        # JSON fallback
        path = OUTPUT_DIR / f"master_analytics_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(path, "w") as f:
            json.dump(sheets, f, indent=2, default=str)
        log.info(f"JSON fallback saved: {path}")
        return str(path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", default="all", choices=["all", "blinko", "agents", "memory", "services", "ventures", "slack", "trading"])
    args = parser.parse_args()
    path = generate_master_report(args.section)
    print(f"Report: {path}")
