#!/usr/bin/env python3
"""Everlight daily marketing brief -- prepares the day's content queue.

Reads the locked brand foundation, checks the Deal-1 receipts gate, rotates the
5 content pillars, scans for fresh receipts, and writes an approval-ready brief
to the content queue. Posts a branded Slack ping when available.

Doctrine guardrail (researcher market call, 2026-05-24): the billionaire-arc
brand does NOT launch publicly until Deal 1 closes. Until then this runs in
PREPARE mode -- it stocks the queue, it never publishes. Flip the gate in
_state/marketing_gate.json the day the first verified receipt lands.

Matches the existing daily-brief cron pattern (build_daily_brief.py / ceo_daily_brief.py).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
FOUNDATION = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/Social_Network/01_BRAND_FOUNDATION.md"
GATE_FILE = WORKSPACE / "_state/marketing_gate.json"
QUEUE_DIR = WORKSPACE / "02_CONTENT_FACTORY/01_Queue/everlight/marketing_briefs"
LOG_FILE = WORKSPACE / "_logs/marketing_brief.log"

PT = timezone(timedelta(hours=-8))  # Pacific, per operator preference

# The 5 pillars, with the days they lead and the channels they suit.
# Cadence lands ~80% proof/journey, ~20% offer, and Lucrex-voice ~1-in-7.
PILLARS = {
    "The Build": {
        "desc": "Behind-the-scenes of building the company in the open. Process, not polish.",
        "voice": "Everlight Ventures (we)",
        "channels": ["X thread", "Discord", "LinkedIn"],
        "prelaunch_ok": True,
    },
    "The Teach": {
        "desc": "Free value: AI / automation / real-estate / trading how-tos.",
        "voice": "Everlight Ventures (we)",
        "channels": ["X thread", "IG carousel", "LinkedIn"],
        "prelaunch_ok": True,
    },
    "The Wins": {
        "desc": "Deals closed, results, verified receipts. Proof over claims.",
        "voice": "Everlight Ventures (we)",
        "channels": ["IG", "X", "Discord #wins"],
        "prelaunch_ok": False,  # needs a real receipt -- gated to Deal 1
    },
    "The Voice": {
        "desc": "Lucrex (AI CEO) conviction line. The screenshot-able take. Rare, so it stays loud.",
        "voice": "Lucrex (I) -- attributed 'from the CEO'",
        "channels": ["X", "Discord"],
        "prelaunch_ok": True,
    },
    "The Offer": {
        "desc": "Products, soft and hard CTAs (Hive Mind, Lighthouse, Borealis, books).",
        "voice": "Everlight Ventures (we)",
        "channels": ["IG", "LinkedIn", "Telegram"],
        "prelaunch_ok": False,  # no offer push until there is proof to back it
    },
}

# Weekday -> leading pillar (0 = Monday).
WEEK_MAP = {
    0: "The Build",
    1: "The Teach",
    2: "The Wins",
    3: "The Voice",
    4: "The Offer",
    5: "The Build",
    6: "The Teach",
}


def load_gate() -> dict:
    """Read the receipts gate. Default: closed (prepare-only) and not launched."""
    default = {"deal_1_closed": False, "public_launch": False}
    try:
        return {**default, **json.loads(GATE_FILE.read_text())}
    except (FileNotFoundError, json.JSONDecodeError):
        GATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        GATE_FILE.write_text(json.dumps(default, indent=2))
        return default


def fresh_receipts(since_hours: int = 48) -> list[str]:
    """Scan pipeline logs for recently touched proof. Honest about emptiness."""
    cutoff = datetime.now().timestamp() - since_hours * 3600
    hits: list[str] = []
    pipeline = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/pipeline"
    for log in sorted(pipeline.glob("*_log.jsonl")) if pipeline.exists() else []:
        try:
            if log.stat().st_mtime >= cutoff and log.stat().st_size > 0:
                hits.append(log.name)
        except OSError:
            continue
    return hits


def pick_pillar(gate: dict, weekday: int) -> tuple[str, str]:
    """Choose today's pillar; redirect gated pillars to a safe one pre-launch."""
    lead = WEEK_MAP[weekday]
    if not gate["public_launch"] and not PILLARS[lead]["prelaunch_ok"]:
        # The Wins / The Offer need proof -- swap to process content until Deal 1.
        return "The Build", f"{lead} is gated until Deal 1 closes -- swapped to The Build (process)."
    return lead, ""


def build_brief(now: datetime, gate: dict) -> str:
    weekday = now.weekday()
    pillar, note = pick_pillar(gate, weekday)
    p = PILLARS[pillar]
    receipts = fresh_receipts()
    mode = "LIVE (publish-approved)" if gate["public_launch"] else "PREPARE-ONLY (queue, do not publish)"

    lines = [
        f"# Everlight Marketing Brief -- {now.strftime('%A, %B %d, %Y')} (PT)",
        "",
        f"**Mode:** {mode}",
        f"**Deal-1 gate:** {'OPEN' if gate['deal_1_closed'] else 'CLOSED -- receipts-or-silence'}",
        "",
        "---",
        "",
        f"## Today's pillar: {pillar}",
        f"_{p['desc']}_",
        "",
        f"- **Voice:** {p['voice']}",
        f"- **Channels:** {', '.join(p['channels'])}",
    ]
    if note:
        lines.append(f"- **Note:** {note}")
    lines += [
        "",
        "## Suggested angle (draft -- approve or rewrite)",
        f"- {angle_for(pillar, gate)}",
        "",
        "## Fresh receipts in the last 48h",
    ]
    if receipts:
        lines += [f"- {r}" for r in receipts]
    else:
        lines.append("- None yet. Pre-Deal-1 this is expected -- lead with process and lessons, not results.")
    lines += [
        "",
        "## Approval",
        "- [ ] Approve as-is   - [ ] Rewrite   - [ ] Skip today",
        "",
        "---",
        "_Generated by the Everlight marketing engine. Lucrex = AI CEO byline; "
        "Everlight Ventures = company voice. Confidentiality envelope binds: no names, "
        "no dollar figures, no pipeline state in public copy._",
    ]
    return "\n".join(lines)


def angle_for(pillar: str, gate: dict) -> str:
    """A starting angle per pillar. Deterministic now; LLM-pluggable later."""
    book = {
        "The Build": "What got built today and the one decision behind it. Show the work, name the tradeoff.",
        "The Teach": "One thing most people get wrong about [automation / wholesale / AI], and the fix.",
        "The Voice": "A short conviction line on building in the open. Attribute to the CEO. Keep it rare.",
        "The Wins": "A verified receipt with the number front and center. Wins and losses both build trust.",
        "The Offer": "Soft CTA tied to a result already shown this week. Lead with proof, not the product.",
    }
    return book.get(pillar, "Draft per the brand foundation.")


def post_slack(now: datetime, queue_path: Path) -> bool:
    """Branded ping that the day's brief is ready. Degrades gracefully."""
    sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))
    try:
        from content_tools.branded_slack import post_branded_slack  # type: ignore
    except Exception:
        return False
    try:
        post_branded_slack(
            channel="#content-factory",
            category="ops",
            header="Marketing brief ready",
            summary=f"Today's content brief is queued for approval ({now.strftime('%b %d')}).",
            body=f"File: {queue_path.name}",
            agent="Marketing Engine",
        )
        return True
    except Exception:
        return False


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(PT).strftime("%Y-%m-%d %H:%M:%S PT")
    with LOG_FILE.open("a") as fh:
        fh.write(f"[{stamp}] {msg}\n")


def main() -> int:
    now = datetime.now(PT)
    gate = load_gate()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = QUEUE_DIR / f"marketing_brief_{now.strftime('%Y-%m-%d')}.md"
    out.write_text(build_brief(now, gate))
    slacked = post_slack(now, out)
    log(f"brief written: {out.name} | gate_open={gate['public_launch']} | slack={slacked}")
    print(f"Wrote {out}")
    print(f"Mode: {'LIVE' if gate['public_launch'] else 'PREPARE-ONLY'} | Slack ping: {slacked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
