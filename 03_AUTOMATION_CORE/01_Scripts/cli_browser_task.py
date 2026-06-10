"""cli_browser_task -- write a browser-task envelope to the pending queue.

Used by Claude CLI to dispatch a browser-clicking task to the desktop runner.

Usage (from CLI):
    python3 cli_browser_task.py \
        --title "Create Resend full-access API key" \
        --goal "Open https://resend.com/api-keys ..." \
        [--max-iterations 30] [--max-seconds 300] \
        [--correlation-id <id>]

Or programmatically:
    from cli_browser_task import write_envelope
    env = write_envelope(title="...", goal="...")
    print(env["task_id"])

Then poll for the result:
    from cli_browser_task import wait_for_result
    result = wait_for_result(task_id, timeout_seconds=600)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/AA_MY_DRIVE/_logs/browser_tasks")
PENDING = ROOT / "pending"
IN_PROGRESS = ROOT / "in_progress"
DONE = ROOT / "done"
FAILED = ROOT / "failed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_excerpt(path: str, max_lines: int = 30) -> str:
    """Read first max_lines of a file, capped at 4KB. Best-effort, returns '' on error."""
    try:
        from pathlib import Path as _P
        p = _P(path)
        if not p.exists() or not p.is_file():
            return ""
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines]
        text = "\n".join(lines)
        return text[:4096]
    except Exception:
        return ""


def _capture_previous_state() -> dict[str, Any]:
    """Auto-snapshot: halt_check, recent commits, recent audit envelopes."""
    state: dict[str, Any] = {}
    import subprocess
    try:
        r = subprocess.run(["bash", "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/halt_check.sh"],
                           capture_output=True, text=True, timeout=10)
        state["halt_check"] = (r.stdout or "")[:1500]
    except Exception:
        pass
    try:
        r = subprocess.run(["git", "-C", "/AA_MY_DRIVE", "log", "--oneline", "-5"],
                           capture_output=True, text=True, timeout=5)
        state["recent_commits"] = (r.stdout or "").splitlines()
    except Exception:
        pass
    try:
        from pathlib import Path as _P
        latest = sorted(_P("/AA_MY_DRIVE/_audit").rglob("*.json"))[-3:]
        state["recent_audit_envelopes"] = [str(p.relative_to("/AA_MY_DRIVE")) for p in latest]
    except Exception:
        pass
    return state


def write_envelope(
    *,
    title: str,
    goal: str,
    correlation_id: Optional[str] = None,
    max_iterations: int = 30,
    max_seconds: int = 300,
    expected_result_schema: Optional[dict] = None,
    created_by: str = "claude_cli",
    safety: Optional[dict] = None,
    project: Optional[str] = None,
    conversation_summary: Optional[str] = None,
    related_files: Optional[list[dict[str, str]]] = None,
    success_criteria: Optional[list[str]] = None,
    do_not: Optional[list[str]] = None,
    auto_capture_state: bool = True,
) -> dict[str, Any]:
    """Write a browser-task envelope to the pending queue. Returns the envelope dict.

    For rich-context envelopes, pass project + conversation_summary + related_files
    + success_criteria + do_not. The desktop agent will receive all of this in its
    system prompt, with file excerpts embedded inline (no filesystem access needed
    mid-task).
    """
    PENDING.mkdir(parents=True, exist_ok=True)
    task_id = f"btsk_{uuid.uuid4().hex[:16]}"

    # Build rich-context block if any context fields provided
    context: dict[str, Any] = {}
    if project:
        context["project"] = project
    if conversation_summary:
        context["conversation_summary"] = conversation_summary[:4000]
    if related_files:
        rf_resolved = []
        for rf in related_files:
            entry = {"path": rf.get("path", ""), "purpose": rf.get("purpose", "")}
            if rf.get("path"):
                entry["excerpt"] = _read_excerpt(rf["path"])
            rf_resolved.append(entry)
        context["related_files"] = rf_resolved
    if success_criteria:
        context["success_criteria"] = success_criteria
    if do_not:
        context["do_not"] = do_not
    if auto_capture_state and context:
        context["previous_state"] = _capture_previous_state()

    envelope = {
        "task_id": task_id,
        "correlation_id": correlation_id or task_id,
        "created_at": _now_iso(),
        "created_by": created_by,
        "title": title,
        "natural_language_goal": goal,
        "max_iterations": max_iterations,
        "max_seconds": max_seconds,
        "expected_result_schema": expected_result_schema or {},
        "screenshots_dir": f"{task_id}/",
        "callback_slack_channel": "#deploy-log",
        "safety": safety or {
            "prohibited_urls": ["chrome://settings", "about:config", "*.bank.*"],
            "abort_on_human_override": True,
            "abort_on_oauth_screen": True,
            "honor_outbound_halt": True,
        },
        "context": context if context else None,
        "status": "pending",
        "result": None,
        "started_at": None,
        "completed_at": None,
    }
    out = PENDING / f"{task_id}.json"
    tmp = PENDING / f".{task_id}.tmp"
    tmp.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    os.replace(tmp, out)
    return envelope


def wait_for_result(task_id: str, *, timeout_seconds: int = 600, poll: float = 2.0) -> dict[str, Any]:
    """Block until the task lands in done/ or failed/. Returns the final envelope."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for d in (DONE, FAILED):
            f = d / f"{task_id}.json"
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8"))
        time.sleep(poll)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout_seconds}s")


def get_status(task_id: str) -> str:
    """Return the current status of a task by checking which dir it's in."""
    for d, status in [(PENDING, "pending"), (IN_PROGRESS, "in_progress"),
                       (DONE, "done"), (FAILED, "failed")]:
        if (d / f"{task_id}.json").exists():
            return status
    return "unknown"


def _cli() -> int:
    p = argparse.ArgumentParser(description="Write a browser-task envelope to the pending queue.")
    p.add_argument("--title", required=True, help="Short title")
    p.add_argument("--goal", required=True, help="Natural-language goal for the agent")
    p.add_argument("--correlation-id", default=None)
    p.add_argument("--max-iterations", type=int, default=30)
    p.add_argument("--max-seconds", type=int, default=300)
    p.add_argument("--expected-key", action="append", default=[],
                   help="Expected result key (can repeat). E.g., --expected-key api_key")
    p.add_argument("--wait", action="store_true", help="Block until done/failed")
    p.add_argument("--timeout", type=int, default=600, help="Wait timeout seconds")
    args = p.parse_args()

    expected = {k: "string" for k in args.expected_key} if args.expected_key else None

    env = write_envelope(
        title=args.title,
        goal=args.goal,
        correlation_id=args.correlation_id,
        max_iterations=args.max_iterations,
        max_seconds=args.max_seconds,
        expected_result_schema=expected,
    )
    print(json.dumps({"task_id": env["task_id"], "status": "pending",
                      "queue_path": str(PENDING / f"{env['task_id']}.json")}, indent=2))
    if args.wait:
        result = wait_for_result(env["task_id"], timeout_seconds=args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "done" else 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
