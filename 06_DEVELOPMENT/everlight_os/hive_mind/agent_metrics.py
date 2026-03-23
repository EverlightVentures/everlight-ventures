"""
Hive Mind Agent Performance Metrics -- Supabase-backed (Meta performance review pattern).

Tracks per-agent task performance so the dashboard can show:
- Agent leaderboards
- Success rates and average durations
- Weekly performance reports

Table: agent_performance in Supabase.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

# Lazy Supabase client to avoid import errors when supabase isn't available
_supabase = None


def _get_supabase():
    """Get or create Supabase client."""
    global _supabase
    if _supabase is not None:
        return _supabase

    try:
        from supabase import create_client
        url = os.environ.get(
            "SUPABASE_URL",
            "https://jdqqmsmwmbsnlnstyavl.supabase.co",
        )
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if not key:
            # Try reading from .env file
            env_path = os.path.join(
                os.environ.get("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE"),
                ".env",
            )
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("SUPABASE_ANON_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        if url and key:
            _supabase = create_client(url, key)
        return _supabase
    except Exception:
        return None


def log_agent_performance(
    agent_name: str,
    department: str,
    session_id: str,
    task_type: str = "",
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    success: bool = False,
    duration_s: float = 0.0,
    findings_count: int = 0,
    recommendations_count: int = 0,
) -> bool:
    """Write a performance record to Supabase agent_performance table.

    Returns True if successfully written, False otherwise.
    """
    sb = _get_supabase()
    if sb is None:
        return False

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "agent_name": agent_name,
        "department": department,
        "session_id": session_id,
        "task_type": task_type,
        "started_at": started_at or now,
        "completed_at": completed_at or now,
        "success": success,
        "duration_s": round(duration_s, 2),
        "findings_count": findings_count,
        "recommendations_count": recommendations_count,
    }

    try:
        sb.table("agent_performance").insert(record).execute()
        return True
    except Exception:
        return False


def get_agent_scorecard(agent_name: str, days: int = 30) -> dict:
    """Pull agent performance stats for the dashboard.

    Returns:
        {
            "agent_name": str,
            "total_tasks": int,
            "success_rate": float,
            "avg_duration_s": float,
            "total_findings": int,
            "total_recommendations": int,
        }
    """
    sb = _get_supabase()
    if sb is None:
        return {"agent_name": agent_name, "total_tasks": 0, "error": "no_supabase"}

    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        resp = (
            sb.table("agent_performance")
            .select("*")
            .eq("agent_name", agent_name)
            .gte("created_at", cutoff)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return {"agent_name": agent_name, "total_tasks": 0}

        total = len(rows)
        successes = sum(1 for r in rows if r.get("success"))
        durations = [r.get("duration_s", 0) for r in rows if r.get("duration_s")]
        findings = sum(r.get("findings_count", 0) for r in rows)
        recs = sum(r.get("recommendations_count", 0) for r in rows)

        return {
            "agent_name": agent_name,
            "total_tasks": total,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
            "total_findings": findings,
            "total_recommendations": recs,
        }
    except Exception as e:
        return {"agent_name": agent_name, "total_tasks": 0, "error": str(e)}


def get_all_agent_scorecards(days: int = 30) -> list[dict]:
    """Pull scorecards for all agents with activity in the past N days."""
    sb = _get_supabase()
    if sb is None:
        return []

    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        resp = (
            sb.table("agent_performance")
            .select("*")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(1000)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return []

        # Group by agent
        by_agent = {}
        for r in rows:
            name = r.get("agent_name", "unknown")
            by_agent.setdefault(name, []).append(r)

        scorecards = []
        for name, agent_rows in by_agent.items():
            total = len(agent_rows)
            successes = sum(1 for r in agent_rows if r.get("success"))
            durations = [r.get("duration_s", 0) for r in agent_rows if r.get("duration_s")]
            dept = agent_rows[0].get("department", "unknown")

            scorecards.append({
                "agent_name": name,
                "department": dept,
                "total_tasks": total,
                "success_rate": round(successes / total * 100, 1) if total else 0,
                "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
                "total_findings": sum(r.get("findings_count", 0) for r in agent_rows),
                "total_recommendations": sum(r.get("recommendations_count", 0) for r in agent_rows),
            })

        scorecards.sort(key=lambda s: s["success_rate"], reverse=True)
        return scorecards
    except Exception:
        return []
