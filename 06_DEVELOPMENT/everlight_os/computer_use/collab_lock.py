"""collab_lock -- shared turn-taking lock between Claude CLI and desktop_runner.

Problem: Claude CLI sometimes asks Rich for confirmation ("press 1 or 2", "y/n").
While Rich is typing the answer into his terminal, the desktop_runner is blindly
clicking through Firefox -- stealing focus, blocking his keystrokes, frustrating.

Solution: a tiny file-based lock at /tmp/lucrex_collab_lock. Two states:
  - File absent OR contents='free' = desktop_runner can take actions
  - File contents='cli_active' = desktop_runner pauses until cleared

CLI side: call cli_taking_floor() before any AskUserQuestion / ExitPlanMode /
prompts that need Rich's keyboard input. Call cli_yielded_floor() after.

Desktop side: desktop_agent.run_task() checks the lock at the start of EVERY
iteration. If 'cli_active', sleeps 2s and rechecks (no API call, no token cost).
Resumes when cleared.

Both sides also write a small "who" + "since" envelope so debugging is easy.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

LOCK_PATH = Path("/tmp/lucrex_collab_lock.json")
PAUSE_PATH = Path("/tmp/lucrex_collab_lock.pause")  # presence-only fast-check


def _write_lock(state: str, holder: str, reason: str = "") -> None:
    """Write the lock atomically. holder = 'cli' or 'desktop_agent'."""
    payload = {
        "state": state,            # 'free' | 'cli_active' | 'desktop_active'
        "holder": holder,
        "reason": reason,
        "since": time.time(),
        "since_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    tmp = LOCK_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(LOCK_PATH)
    if state == "cli_active":
        PAUSE_PATH.touch()
    else:
        try:
            PAUSE_PATH.unlink()
        except FileNotFoundError:
            pass


def cli_taking_floor(reason: str = "human_input_needed") -> None:
    """CLI: 'I need Rich's keyboard for the next prompt -- desktop, please pause.'
    Call this RIGHT BEFORE any AskUserQuestion / interactive read."""
    _write_lock("cli_active", holder="cli", reason=reason)


def cli_yielded_floor() -> None:
    """CLI: 'I'm done with Rich's input -- desktop, you can resume.'
    Call this RIGHT AFTER getting the user's answer."""
    _write_lock("free", holder="cli", reason="answer_received")


def desktop_taking_floor(reason: str = "agent_action") -> None:
    """Desktop agent: optional, marks that we're actively driving the screen."""
    _write_lock("desktop_active", holder="desktop_agent", reason=reason)


def desktop_yielded_floor() -> None:
    """Desktop agent: marks we're done with the screen."""
    _write_lock("free", holder="desktop_agent", reason="task_complete")


def is_paused_for_cli() -> bool:
    """Fast-path check used inside the desktop_agent loop. Returns True if
    the desktop agent should hold off on the next action."""
    if not PAUSE_PATH.exists():
        return False
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        return data.get("state") == "cli_active"
    except Exception:
        return PAUSE_PATH.exists()


def wait_until_clear(*, max_wait: float = 600.0, poll: float = 1.5) -> bool:
    """Block until the lock clears (CLI yields). Returns True if clear, False
    if max_wait was exceeded. max_wait defaults to 10 minutes."""
    start = time.time()
    while is_paused_for_cli():
        if time.time() - start > max_wait:
            return False
        time.sleep(poll)
    return True


def get_state() -> dict:
    """Return current lock state for diagnostics."""
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"state": "free", "holder": None, "reason": "no_lock_file"}


if __name__ == "__main__":
    # Tiny CLI for shell integration.
    #   collab_lock.py pause "fixing typo in prompt"
    #   collab_lock.py resume
    #   collab_lock.py state
    import sys
    if len(sys.argv) < 2 or sys.argv[1] == "state":
        print(json.dumps(get_state(), indent=2))
    elif sys.argv[1] == "pause":
        reason = " ".join(sys.argv[2:]) or "manual"
        cli_taking_floor(reason)
        print(f"PAUSED -- desktop_runner will yield. Reason: {reason}")
    elif sys.argv[1] in ("resume", "clear"):
        cli_yielded_floor()
        print("RESUMED -- desktop_runner can take actions again.")
    else:
        print(f"usage: collab_lock.py [state|pause [reason]|resume]", file=sys.stderr)
        sys.exit(1)
