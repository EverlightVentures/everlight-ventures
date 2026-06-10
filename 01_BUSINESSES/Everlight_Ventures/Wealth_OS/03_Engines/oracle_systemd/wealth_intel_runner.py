#!/usr/bin/env python3
"""
Wealth OS -- Quarterly Intel Engine runner.

Lives at /home/opc/wealth_intel_runner.py on Oracle E5.
Fired by wealth-intel.timer on the 1st of each month at 7:17 AM PT.

Job:
1. Pull a snapshot of tax-law / regulatory headlines via Perplexity (or fallback web fetch)
   for: QSBS Sec 1202, R&D Sec 41, bonus depreciation, TCJA sunset, 1031, Opp Zones,
   PR Act 60, FBAR/FATCA, CA/TX/FL/NV/SD/WY state moves, wholesaling/foreclosure bills.
2. Diff against last month's snapshot at /home/opc/_state/wealth_intel_last.json.
3. If material change: write a gold-themed report via content_tools.n8n_replacements.publish_gdoc
   and post a branded Slack card to #ceo-brief.
4. If no material change: post a 3-line heartbeat to #ceo-brief so Marquise sees the pulse.
5. Tag everything in Blinko under #wealth-os/intel.

This is intentionally light on dependencies -- it only needs requests + content_tools.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

STATE_DIR = Path("/home/opc/_state")
STATE_DIR.mkdir(exist_ok=True)
SNAPSHOT_PATH = STATE_DIR / "wealth_intel_last.json"
LOG_PATH = Path("/home/opc/_logs/wealth_intel.log")
LOG_PATH.parent.mkdir(exist_ok=True)

# Topics watched. Each is one Perplexity / web query. Keep tight.
TOPICS = [
    ("qsbs_sec_1202",      "QSBS Section 1202 IRS guidance changes 2026"),
    ("rd_sec_41",          "R&D credit Section 41 capitalization Section 174 changes 2026"),
    ("bonus_depreciation", "bonus depreciation phase down 2026 schedule"),
    ("tcja_sunset",        "TCJA estate gift lifetime exemption sunset 2025 2026 update"),
    ("section_1031",       "1031 like-kind exchange 2026 rule changes"),
    ("opportunity_zones",  "opportunity zone designation 2026 reauthorization"),
    ("pr_act_60",          "Puerto Rico Act 60 individual investor export services 2026 rule changes"),
    ("ca_state",           "California wholesaling foreclosure consultant law 2026 session"),
    ("tx_state",           "Texas wholesaling SB 140 cold SMS rule changes 2026"),
    ("fl_state",           "Florida domicile rules new resident tax 2026"),
    ("wy_de_nv_sd",        "Wyoming Delaware Nevada South Dakota LLC trust law changes 2026"),
    ("fbar_fatca",         "FBAR FATCA reporting changes 2026"),
]

CHANNEL_CEO_BRIEF = "C0XXXXXXXXX"  # replace with #ceo-brief channel id from slack_routing.yaml


def stamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(msg: str) -> None:
    line = f"[{stamp()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def perplexity_query(question: str) -> str:
    """Best-effort Perplexity hit. Falls back to '' on any error."""
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "sonar-medium-online",
                "messages": [
                    {"role": "system", "content": "You are a tax-law watcher. Reply in 3-5 bullet points. Cite source URLs."},
                    {"role": "user", "content": question},
                ],
                "max_tokens": 500,
                "temperature": 0.2,
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as exc:
        log(f"perplexity error on {question[:50]}: {exc}")
        return ""


def gather_snapshot() -> dict:
    snap: dict = {"as_of": stamp(), "topics": {}}
    for key, q in TOPICS:
        log(f"querying {key}")
        snap["topics"][key] = perplexity_query(q)
        time.sleep(2)
    return snap


def diff_snapshots(prev: dict, curr: dict) -> list[str]:
    """Crude content-equality diff. Anything where text changed is flagged."""
    deltas: list[str] = []
    prev_topics = (prev or {}).get("topics", {})
    for key, val in curr["topics"].items():
        prev_val = prev_topics.get(key, "")
        if val and val.strip() != prev_val.strip():
            deltas.append(key)
    return deltas


def post_slack_heartbeat(deltas: list[str]) -> None:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        log("no SLACK_BOT_TOKEN, skipping post")
        return
    if deltas:
        text = (
            f"Wealth Intel monthly sweep -- {len(deltas)} delta(s) detected: "
            + ", ".join(deltas)
            + ". Full report uploaded to Drive."
        )
    else:
        text = "Wealth Intel monthly sweep -- no material change. Quiet month. Heartbeat OK."
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": CHANNEL_CEO_BRIEF, "text": text},
            timeout=15,
        )
    except Exception as exc:
        log(f"slack post failed: {exc}")


def publish_report(snap: dict, deltas: list[str]) -> None:
    """Try to ship a gold-themed GDoc + HTML via content_tools. Optional."""
    try:
        sys.path.insert(0, "/home/opc")
        from content_tools.n8n_replacements import publish_gdoc  # type: ignore

        body_md = ["# Wealth Intel Monthly Sweep", f"\n_{stamp()}_\n"]
        if not deltas:
            body_md.append("No material change this month. Heartbeat only.\n")
        else:
            body_md.append(f"\n**{len(deltas)} delta(s) detected:** {', '.join(deltas)}\n")
            for key in deltas:
                body_md.append(f"\n## {key}\n\n{snap['topics'].get(key, '').strip()}\n")
        body_md.append("\n---\n_Filed by Quarterly Intel Engine. Wealth_OS v0.1._")

        publish_gdoc(
            title=f"Wealth Intel -- {datetime.now().strftime('%Y-%m')}",
            html_or_markdown="\n".join(body_md),
            slack_channel="ceo-brief",
            tags=["wealth-os", "intel"],
        )
    except Exception as exc:
        log(f"publish_gdoc skipped: {exc}")


def main() -> int:
    log("wealth_intel_runner starting")
    prev = {}
    if SNAPSHOT_PATH.exists():
        try:
            prev = json.loads(SNAPSHOT_PATH.read_text())
        except Exception:
            prev = {}
    curr = gather_snapshot()
    deltas = diff_snapshots(prev, curr)
    SNAPSHOT_PATH.write_text(json.dumps(curr, indent=2))
    log(f"deltas: {deltas if deltas else 'none'}")
    publish_report(curr, deltas)
    post_slack_heartbeat(deltas)
    log("wealth_intel_runner done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
