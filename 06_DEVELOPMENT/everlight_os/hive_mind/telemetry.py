"""
Project BMO Phase 1 -- Specialist Performance Telemetry.

Tracks per-specialist metrics across hive mind sessions so we can:
- Weight specialist contributions by historical performance
- Identify under-performing specialists for persona briefing review
- Feed the roster_feedback loop (Phase 2)

Origin: War room session 2c819143 (2026-02-27), automation_architect recommendation.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import WORKSPACE

TELEMETRY_FILE = WORKSPACE / "everlight_os" / "hive_mind" / "telemetry.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_specialist_reports(response_text: str, employees: list[str]) -> dict:
    """Parse specialist contributions from a manager's response text.

    Returns dict of {specialist_name: {status, findings_count, has_recommendation, has_risk_flag}}
    """
    reports = {}
    for emp in employees:
        # Match patterns like **specialist_name** | STATUS: ACTIVE
        pattern = rf"\*\*{re.escape(emp)}\*\*\s*\|\s*STATUS:\s*(\w+)"
        match = re.search(pattern, response_text or "", re.IGNORECASE)

        if match:
            status = match.group(1).upper()
            # Count findings (lines starting with "- Finding")
            # Look in the section after this specialist until next specialist or section
            start_pos = match.end()
            next_specialist = re.search(r"\*\*\w+\*\*\s*\|\s*STATUS:", response_text[start_pos:])
            end_pos = start_pos + next_specialist.start() if next_specialist else len(response_text)
            section = response_text[start_pos:end_pos]

            findings = len(re.findall(r"-\s*Finding\s*\d+:", section, re.IGNORECASE))
            has_rec = bool(re.search(r"-\s*Recommendation:", section, re.IGNORECASE))
            has_risk = bool(re.search(r"-\s*Risk\s*flag:", section, re.IGNORECASE))

            reports[emp] = {
                "status": status,
                "findings_count": findings,
                "has_recommendation": has_rec,
                "has_risk_flag": has_risk,
            }
        else:
            reports[emp] = {
                "status": "NOT_FOUND",
                "findings_count": 0,
                "has_recommendation": False,
                "has_risk_flag": False,
            }

    return reports


def log_session_telemetry(
    session_id: str,
    manager_key: str,
    employees: list[str],
    response_text: str,
    status: str,
    duration_s: float,
    category: str = "",
) -> None:
    """Log telemetry for all specialists in a manager's response.

    Called after each manager completes in the dispatcher.
    """
    specialist_reports = _extract_specialist_reports(response_text, employees)

    for specialist, report in specialist_reports.items():
        entry = {
            "timestamp": _now(),
            "session": session_id,
            "manager": manager_key,
            "specialist": specialist,
            "category": category,
            "manager_status": status,
            "manager_duration_s": duration_s,
            "specialist_status": report["status"],
            "findings_count": report["findings_count"],
            "has_recommendation": report["has_recommendation"],
            "has_risk_flag": report["has_risk_flag"],
            "implemented": None,  # filled in post-execution (Phase 2)
            "outcome": None,       # filled in post-execution (Phase 2)
        }

        try:
            TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # telemetry is best-effort


def get_specialist_stats(specialist: str, last_n: int = 20) -> dict:
    """Get performance stats for a specialist from recent sessions.

    Returns:
        {
            "sessions": N,
            "active_rate": 0.85,     # % of sessions where ACTIVE (not STANDBY)
            "avg_findings": 1.5,
            "recommendation_rate": 0.70,
            "risk_flag_rate": 0.40,
        }
    """
    if not TELEMETRY_FILE.exists():
        return {"sessions": 0}

    entries = []
    for line in TELEMETRY_FILE.read_text(encoding="utf-8").strip().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("specialist") == specialist:
                entries.append(entry)
        except json.JSONDecodeError:
            continue

    # Take last N entries
    entries = entries[-last_n:]
    if not entries:
        return {"sessions": 0}

    total = len(entries)
    active = sum(1 for e in entries if e.get("specialist_status") == "ACTIVE")
    findings = sum(e.get("findings_count", 0) for e in entries)
    recs = sum(1 for e in entries if e.get("has_recommendation"))
    risks = sum(1 for e in entries if e.get("has_risk_flag"))

    return {
        "sessions": total,
        "active_rate": round(active / total, 2),
        "avg_findings": round(findings / total, 2),
        "recommendation_rate": round(recs / total, 2),
        "risk_flag_rate": round(risks / total, 2),
    }


def get_roster_weights(roster: dict, last_n: int = 20) -> dict:
    """Calculate performance weights for all specialists across all managers.

    Returns dict of {specialist_name: weight} where weight is 0.0-1.0.
    Higher = better performer.
    """
    weights = {}
    for manager_key, conf in roster.get("managers", {}).items():
        employees = conf.get("employees", [])
        for emp in employees:
            stats = get_specialist_stats(emp, last_n)
            if stats["sessions"] == 0:
                weights[emp] = 0.5  # neutral default for new specialists
            else:
                # Weight = active_rate * 0.4 + recommendation_rate * 0.3 + avg_findings_norm * 0.3
                findings_norm = min(stats["avg_findings"] / 3.0, 1.0)  # normalize to 0-1
                weight = (
                    stats["active_rate"] * 0.4
                    + stats["recommendation_rate"] * 0.3
                    + findings_norm * 0.3
                )
                weights[emp] = round(weight, 3)

    return weights
