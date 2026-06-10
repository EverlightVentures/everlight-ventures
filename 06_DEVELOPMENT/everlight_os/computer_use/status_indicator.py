"""status_indicator -- writes the current Lucrex hive state to /tmp/lucrex_status.json.

Runs as a systemd service. Polls every 2s. Reports:
  - Which runners are currently DRIVING the PC (in_progress envelopes)
  - Queue depths (pending / done / failed)
  - BT/audio state
  - collab_lock state (CLI floor vs free)
  - Last action timestamp from each runner's log

Output JSON is consumed by lucrex_floating_status.py (the visible widget)
and any other UI surface (Plasma widget, web dashboard, etc).

CRITICAL purpose per Rich (2026-05-07): the live indicator tells him whether
the PC is actively being driven by an agent so he doesn't accidentally
interrupt by moving his mouse / typing. State 'BUSY_DRIVING' = HANDS OFF.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path("/tmp/lucrex_status.json")
COLLAB_LOCK_PATH = Path("/tmp/lucrex_collab_lock.json")
TASKS_ROOT = Path("/AA_MY_DRIVE/_logs/browser_tasks")
POLL_INTERVAL = 2.0


def _is_active(svc: str) -> bool:
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", svc],
                           capture_output=True, text=True, timeout=2)
        return r.stdout.strip() == "active"
    except Exception:
        return False


def _ls(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    return [f.name for f in d.glob("*.json")]


def _latest_log_age(p: Path) -> float | None:
    if not p.exists():
        return None
    return time.time() - p.stat().st_mtime


def _in_progress_task() -> dict | None:
    """Return the active envelope (if any) -- the one currently being executed."""
    in_prog = TASKS_ROOT / "in_progress"
    if not in_prog.is_dir():
        return None
    files = sorted(in_prog.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        env = json.loads(files[0].read_text(encoding="utf-8"))
        return {
            "task_id": env.get("task_id"),
            "title": env.get("title", "")[:80],
            "transport": env.get("transport") or (
                "browser_use" if env.get("target_url") else "computer_use"
            ),
            "started_at": env.get("started_at"),
            "model_override": env.get("model_override"),
            "envelope_path": str(files[0]),
        }
    except Exception:
        return None


def _collab_state() -> str:
    """free | cli_active | unknown"""
    if not COLLAB_LOCK_PATH.exists():
        return "free"
    try:
        d = json.loads(COLLAB_LOCK_PATH.read_text(encoding="utf-8"))
        return d.get("state", "unknown")
    except Exception:
        return "unknown"


def compute_state() -> dict:
    """The big-picture status snapshot."""
    pending = _ls(TASKS_ROOT / "pending")
    in_progress = _ls(TASKS_ROOT / "in_progress")
    done = _ls(TASKS_ROOT / "done")
    failed = _ls(TASKS_ROOT / "failed")

    # auto_answer_watcher intentionally NOT required -- the hook does the
    # answering directly via permissionDecision (v13). Keeping the watcher
    # disabled prevents keystroke injection into Rich's terminal.
    runners = {
        "desktop": _is_active("lucrex-desktop-runner.service"),
        "browser_use": _is_active("lucrex-browser-use-runner.service"),
        "managed_agent": _is_active("lucrex-managed-agent-runner.service"),
        "bt_levn": _is_active("bt-levn-keeper.service"),
        "blinko": _is_active("blinko-lite.service"),
        "status_indicator_self": True,  # if we're running, this is true
    }

    active_task = _in_progress_task()

    # Determine the "headline" state for the indicator:
    #   BUSY_DRIVING_PC  -- desktop or browser_use task running (touches keyboard/mouse)
    #   BUSY_CLOUD       -- managed_agent task running (no PC interference)
    #   ASKING_RICH      -- collab_lock=cli_active (CLI awaits answer)
    #   IDLE             -- all runners up, nothing in progress
    #   DEGRADED         -- some runner down
    if _collab_state() == "cli_active":
        headline = "ASKING_RICH"
    elif active_task:
        transport = active_task.get("transport", "")
        if transport in ("computer_use", "browser_use"):
            headline = "BUSY_DRIVING_PC"
        else:
            headline = "BUSY_CLOUD"
    elif not all(runners.values()):
        headline = "DEGRADED"
    else:
        headline = "IDLE"

    # Log freshness for "is this stuck?" heuristic
    log_ages = {
        "desktop": _latest_log_age(Path("/AA_MY_DRIVE/_logs/desktop_runner.log")),
        "browser_use": _latest_log_age(Path("/AA_MY_DRIVE/_logs/browser_use_runner.log")),
        "managed_agent": _latest_log_age(Path("/AA_MY_DRIVE/_logs/managed_agent_runner.log")),
    }

    return {
        "ts": time.time(),
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "headline": headline,
        "active_task": active_task,
        "queue": {
            "pending": len(pending),
            "in_progress": len(in_progress),
            "done": len(done),
            "failed": len(failed),
        },
        "runners": runners,
        "runners_all_active": all(runners.values()),
        "log_ages_seconds": log_ages,
        "collab_state": _collab_state(),
    }


def main() -> int:
    while True:
        try:
            state = compute_state()
            tmp = STATE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
            tmp.replace(STATE_PATH)
        except Exception as e:
            sys.stderr.write(f"status_indicator error: {e}\n")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main() or 0)
