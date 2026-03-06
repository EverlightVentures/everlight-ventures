"""
Convergence - collect results, write war room files, build summary, notify Slack.

Includes cross-agent synthesis: identifies agreement/disagreement across
managers, merges overlapping recommendations, and flags conflicts.
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .config import WORKSPACE
from .contracts import HiveSession


def write_war_room_files(session: HiveSession, roster: dict) -> Path:
    """Write individual manager reports to _logs/ai_war_room/."""
    war_room_base = roster.get("war_room_dir", "_logs/ai_war_room")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    session_dir = WORKSPACE / war_room_base / f"hive_{session.id}_{ts}"
    session_dir.mkdir(parents=True, exist_ok=True)

    for i, mgr in enumerate(session.managers):
        fname = f"{i:02d}_{mgr.manager}_report.md"
        report = f"# {mgr.manager.upper()} ({mgr.role})\n"
        report += f"**Status**: {mgr.status} | **Duration**: {mgr.duration_s}s\n\n"
        if mgr.employees_consulted:
            active, standby = _count_active_specialists(mgr.response_text)
            total = len(mgr.employees_consulted)
            report += f"**Specialists**: {active} active / {total} on team\n"
            report += f"**Team**: {', '.join(mgr.employees_consulted)}\n\n"
        report += "---\n\n"
        report += mgr.response_text or f"*No response ({mgr.error})*"
        report += "\n"
        (session_dir / fname).write_text(report, encoding="utf-8")

    # Combined summary
    summary = build_combined_summary(session)
    (session_dir / "combined_summary.md").write_text(summary, encoding="utf-8")

    # Session metadata (written early; re-written after completion by dispatcher)
    (session_dir / "session.json").write_text(session.to_json(), encoding="utf-8")

    return session_dir


def update_war_room_session(session: HiveSession) -> None:
    """Re-write session.json in the war room after status updates."""
    if not session.war_room_dir:
        return
    session_json = Path(session.war_room_dir) / "session.json"
    if session_json.parent.is_dir():
        session_json.write_text(session.to_json(), encoding="utf-8")


def _count_active_specialists(response_text: str) -> tuple:
    """Count how many specialists reported ACTIVE vs STANDBY in a response."""
    if not response_text:
        return 0, 0
    active = response_text.count("STATUS: ACTIVE")
    standby = response_text.count("STANDBY")
    return active, standby


def _extract_recommendations(response_text: str) -> list:
    """Extract recommendation lines from a manager response."""
    if not response_text:
        return []
    recs = []
    # Match numbered recommendations and bullet points with specialist tags
    for line in response_text.splitlines():
        stripped = line.strip()
        # Pattern: "1. `[specialist]` -> Action" or "- Recommendation: text"
        if re.match(r'^\d+\.\s*`', stripped) or re.match(r'-\s*Recommendation:', stripped, re.IGNORECASE):
            recs.append(stripped)
        # Pattern: bullet points under "Prioritized Recommendations" or "Consolidated Findings"
        elif stripped.startswith("- ") and len(stripped) > 20:
            # Only include substantive bullet points
            recs.append(stripped)
    return recs


def _extract_risks(response_text: str) -> list:
    """Extract risk flags from a manager response."""
    if not response_text:
        return []
    risks = []
    in_risk_section = False
    for line in response_text.splitlines():
        stripped = line.strip()
        if "risk" in stripped.lower() and ("###" in stripped or "**" in stripped):
            in_risk_section = True
            continue
        if in_risk_section:
            if stripped.startswith("###") or stripped.startswith("## "):
                in_risk_section = False
                continue
            if stripped.startswith("- ") and len(stripped) > 15:
                risks.append(stripped)
        # Also catch inline risk flags
        if re.match(r'-\s*Risk\s*flag:', stripped, re.IGNORECASE):
            risks.append(stripped)
    return risks


def _build_cross_agent_synthesis(session: HiveSession) -> list:
    """Analyze responses across agents and identify convergence/divergence."""
    lines = []
    successful = [
        m for m in session.managers
        if m.status == "done" and m.response_text and m.manager != "perplexity"
    ]

    if len(successful) < 2:
        return lines  # Need at least 2 agents for cross-synthesis

    lines.append("")
    lines.append("=" * 60)
    lines.append("  CROSS-AGENT SYNTHESIS")
    lines.append("=" * 60)

    # Collect recommendations per agent
    all_recs = {}
    all_risks = {}
    for mgr in successful:
        all_recs[mgr.manager] = _extract_recommendations(mgr.response_text)
        all_risks[mgr.manager] = _extract_risks(mgr.response_text)

    # Agreement signal: count agents that produced recommendations
    active_count = len(successful)
    total_recs = sum(len(r) for r in all_recs.values())
    total_risks = sum(len(r) for r in all_risks.values())

    lines.append(f"  Agents contributing: {active_count}")
    lines.append(f"  Total recommendations: {total_recs}")
    lines.append(f"  Total risk flags: {total_risks}")

    # Show top recommendations from each agent (deduped)
    if total_recs > 0:
        lines.append("")
        lines.append("  TOP RECOMMENDATIONS (cross-agent):")
        seen = set()
        for mgr_name, recs in all_recs.items():
            for rec in recs[:3]:  # Top 3 per agent
                # Simple dedup: skip if very similar to one already seen
                rec_key = rec.lower()[:60]
                if rec_key not in seen:
                    seen.add(rec_key)
                    lines.append(f"    [{mgr_name.upper()}] {rec}")

    # Show consolidated risks
    if total_risks > 0:
        lines.append("")
        lines.append("  RISK CONSENSUS:")
        seen_risks = set()
        for mgr_name, risks in all_risks.items():
            for risk in risks[:2]:  # Top 2 per agent
                risk_key = risk.lower()[:60]
                if risk_key not in seen_risks:
                    seen_risks.add(risk_key)
                    lines.append(f"    [{mgr_name.upper()}] {risk}")

    # Reliability signal
    lines.append("")
    failed = [m for m in session.managers if m.status in ("failed", "timeout") and m.manager != "perplexity"]
    if failed:
        lines.append(f"  AGENTS DOWN: {', '.join(m.manager.upper() for m in failed)}")
        lines.append(f"  Synthesis confidence: REDUCED (missing {len(failed)} perspective(s))")
    else:
        lines.append(f"  Synthesis confidence: HIGH (all {active_count} agents contributed)")

    return lines


def build_combined_summary(session: HiveSession) -> str:
    """Build the terminal-friendly combined summary with specialist activation stats
    and cross-agent synthesis."""
    lines = []
    lines.append("=" * 60)
    lines.append("  E PLURIBUS UNUM -- HIVE MIND DELIBERATION")
    lines.append("=" * 60)
    lines.append(f"  Session: {session.id} | Mode: {session.mode}")
    prompt_preview = session.prompt[:70]
    if len(session.prompt) > 70:
        prompt_preview += "..."
    lines.append(f"  Prompt: {prompt_preview}")
    lines.append(f"  Routed to: {', '.join(session.routed_to)}")
    lines.append(f"  Total time: {session.total_duration_s}s")

    # Specialist activation summary
    total_specialists = 0
    total_active = 0
    for mgr in session.managers:
        if mgr.manager == "perplexity":
            continue  # Intel scout, not a manager with specialists
        n_employees = len(mgr.employees_consulted)
        active, standby = _count_active_specialists(mgr.response_text)
        if n_employees > 0:
            total_specialists += n_employees
            total_active += active
            lines.append(
                f"  {mgr.manager.upper()} specialists: "
                f"{active} active / {n_employees} total"
            )

    if total_specialists > 0:
        lines.append(f"  TOTAL ACTIVATION: {total_active}/{total_specialists} specialists")

    lines.append("=" * 60)

    icons = {"claude": "C", "gemini": "G", "codex": "X", "perplexity": "P"}
    status_icons = {"done": "+", "failed": "!", "timeout": "T", "pending": "?"}

    for mgr in session.managers:
        icon = icons.get(mgr.manager, "?")
        si = status_icons.get(mgr.status, "?")
        lines.append("")
        header = f"--- [{icon}] {mgr.manager.upper()} ({mgr.role}) [{si}] {mgr.duration_s}s"
        if mgr.employees_consulted:
            header += f" | Team: {len(mgr.employees_consulted)} specialists"
        header += " ---"
        lines.append(header)

        if mgr.status == "done" and mgr.response_text:
            resp_lines = mgr.response_text.splitlines()
            for rl in resp_lines[:40]:
                lines.append(f"  {rl}")
            if len(resp_lines) > 40:
                lines.append(f"  ... ({len(resp_lines) - 40} more lines in war room)")
        elif mgr.error:
            lines.append(f"  ERROR: {mgr.error}")
        else:
            lines.append("  (no output)")

    # Cross-agent synthesis section
    synthesis = _build_cross_agent_synthesis(session)
    lines.extend(synthesis)

    lines.append("")
    lines.append("=" * 60)
    if session.war_room_dir:
        lines.append(f"  Full reports: {session.war_room_dir}")
    lines.append("=" * 60)

    return "\n".join(lines)


def log_session(session: HiveSession, roster: dict) -> None:
    """Append session to hive_sessions.jsonl and notify Slack."""
    # JSONL log
    log_path = roster.get("session_log", "_logs/hive_sessions.jsonl")
    log_file = WORKSPACE / log_path
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "id": session.id,
        "prompt": session.prompt[:200],
        "mode": session.mode,
        "routed_to": session.routed_to,
        "status": session.status,
        "total_duration_s": session.total_duration_s,
        "manager_statuses": {
            m.manager: {"status": m.status, "duration_s": m.duration_s}
            for m in session.managers
        },
        "war_room_dir": session.war_room_dir,
        "timestamp": session.created,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Slack notification (fire-and-forget)
    _notify_slack(session, roster)


def _notify_slack(session: HiveSession, roster: dict) -> None:
    """Post hive session summary to Slack war room channel. Fails silently."""
    # Priority: war room webhook > env var > xlm_bot config > everlight.yaml
    webhook_url = os.environ.get("SLACK_WAR_ROOM_WEBHOOK_URL", "")

    if not webhook_url:
        # Try xlm_bot config (has dedicated war_room_webhook_url)
        try:
            import yaml
            bot_cfg = WORKSPACE / "xlm_bot" / "config.yaml"
            if bot_cfg.exists():
                with open(bot_cfg) as f:
                    cfg = yaml.safe_load(f)
                slack_cfg = cfg.get("slack", {})
                webhook_url = slack_cfg.get("war_room_webhook_url", "")
                if not webhook_url:
                    webhook_url = slack_cfg.get("webhook_url", "")
        except Exception:
            pass

    if not webhook_url:
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")

    if not webhook_url:
        # Fallback to everlight.yaml
        try:
            import yaml
            cfg_path = WORKSPACE / "everlight_os" / "configs" / "everlight.yaml"
            if cfg_path.exists():
                with open(cfg_path) as f:
                    cfg = yaml.safe_load(f)
                webhook_url = cfg.get("slack", {}).get("webhook_url", "")
        except Exception:
            pass

    if not webhook_url:
        return  # No Slack configured, skip silently

    # Build Slack message
    manager_lines = []
    for mgr in session.managers:
        si = {"done": "+", "failed": "!", "timeout": "T"}.get(mgr.status, "?")
        manager_lines.append(f"  [{si}] {mgr.manager.upper()} - {mgr.duration_s}s")

    text = (
        f"*Hive Mind Session {session.id}*\n"
        f"Mode: {session.mode} | Duration: {session.total_duration_s}s\n"
        f"Prompt: _{session.prompt[:100]}_\n"
        f"Routed to: {', '.join(session.routed_to)}\n\n"
        f"```\n" + "\n".join(manager_lines) + "\n```\n"
        f"War Room: `{session.war_room_dir}`"
    )

    # Try to create a Slack Canvas deep link from the combined summary
    if session.war_room_dir:
        try:
            summary_file = Path(session.war_room_dir) / "combined_summary.md"
            if summary_file.exists():
                import sys as _sys
                canvas_tools = str(WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools")
                if canvas_tools not in _sys.path:
                    _sys.path.insert(0, canvas_tools)
                from slack_canvas_bridge import create_native_canvas
                canvas_content = summary_file.read_text(encoding="utf-8")
                canvas_title = f"Hive {session.id} | {session.prompt[:60]}"
                deep_link = create_native_canvas(canvas_content, canvas_title, "warroom")
                if deep_link:
                    text += f"\n\ud83d\udcd1 <{deep_link}|Open Canvas Report>"
        except Exception:
            pass  # Canvas creation is optional; falls through to plain text post

    try:
        import json as _json
        from urllib.request import Request, urlopen
        req = Request(
            url=webhook_url,
            data=_json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(req, timeout=10)
    except Exception:
        pass  # Fire and forget
