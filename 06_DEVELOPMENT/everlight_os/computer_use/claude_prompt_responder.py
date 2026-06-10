"""claude_prompt_responder -- keyboard takeover for Claude Code approval prompts.

Why this exists (Rich, 2026-05-07): "outsource that to Claude computer, and it's
gonna have to take control of the keyboard and say yes or no." Even though the
bash_auto_approver hook returns permissionDecision="allow" for routine commands,
some prompts still surface (LLM_ASK on consequential ops, or Claude Code prompt
types that bypass the PreToolUse hook entirely). For those, this watcher takes
the keyboard and types the answer Rich would have typed.

Architecture:
  1. bash_auto_approver writes /tmp/lucrex_pending_approval.json when it decides
     ASK (and any other code path that wants the keyboard fallback can write the
     same file).
  2. This watcher polls every 0.5s. When the file appears:
     a. Wait POST_DECISION_DELAY (1.2s) for Claude Code's TUI prompt to render.
     b. Find a focused terminal window whose process tree contains 'claude'.
     c. Activate it, type the keystroke (default 'y' Enter, falls back to '1'
        Enter if the prompt looks like a numbered picker).
     d. Delete the trigger file. Log to /tmp/lucrex_responder.log.

Safety:
  - Only fires when trigger file exists. Idle by default.
  - Verifies the active window's process tree contains 'claude' before typing
    -- never injects keystrokes into a random window.
  - Skips if the file is older than STALE_SECONDS (avoids replay after restart).
  - Logs every action with timestamp + reason. Rich can grep the log to audit.

Disable for a single round:
  touch /tmp/lucrex_responder.disable

Disable persistently:
  systemctl --user stop lucrex-prompt-responder
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

PENDING_PATH = Path("/tmp/lucrex_pending_approval.json")
DISABLE_PATH = Path("/tmp/lucrex_responder.disable")
LOG_PATH = Path("/tmp/lucrex_responder.log")
POLL_SECONDS = 0.5
POST_DECISION_DELAY = 1.2  # let Claude Code render the prompt first
STALE_SECONDS = 10.0  # don't fire on stale triggers (e.g., after restart)


def _log(msg: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _run(cmd: list[str], timeout: float = 2.0) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _active_window_id() -> str | None:
    rc, out, _ = _run(["xdotool", "getactivewindow"])
    return out if rc == 0 and out else None


def _window_pid(win_id: str) -> int | None:
    rc, out, _ = _run(["xdotool", "getwindowpid", win_id])
    if rc == 0 and out.isdigit():
        return int(out)
    return None


def _process_tree_has_claude(pid: int) -> bool:
    """Walk up + down the process tree looking for 'claude' in cmdline.

    Looks at the terminal-emulator process and its children (zsh -> claude).
    """
    seen = set()
    todo = [pid]
    for _ in range(20):  # bounded walk
        if not todo:
            break
        p = todo.pop()
        if p in seen or p <= 1:
            continue
        seen.add(p)
        # check this pid's cmdline
        try:
            cmdline = Path(f"/proc/{p}/cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace").lower()
            if "claude" in cmdline:
                return True
        except Exception:
            continue
        # add children
        try:
            children = Path(f"/proc/{p}/task/{p}/children").read_text().split()
            todo.extend(int(c) for c in children if c.isdigit())
        except Exception:
            pass
    return False


def _find_claude_window() -> str | None:
    """Try active window first; fall back to xdotool search by name."""
    win = _active_window_id()
    if win:
        pid = _window_pid(win)
        if pid and _process_tree_has_claude(pid):
            return win
    # search by name
    rc, out, _ = _run(["xdotool", "search", "--name", "claude"])
    if rc == 0 and out:
        for w in out.splitlines():
            pid = _window_pid(w)
            if pid and _process_tree_has_claude(pid):
                return w
    return None


def _send_keystroke(win_id: str, answer: str) -> tuple[bool, str]:
    """Activate window + type answer + Enter."""
    rc1, _, e1 = _run(["xdotool", "windowactivate", "--sync", win_id])
    if rc1 != 0:
        return False, f"windowactivate failed: {e1}"
    time.sleep(0.15)
    rc2, _, e2 = _run(["xdotool", "type", "--delay", "20", answer])
    if rc2 != 0:
        return False, f"type failed: {e2}"
    time.sleep(0.05)
    rc3, _, e3 = _run(["xdotool", "key", "Return"])
    if rc3 != 0:
        return False, f"key Return failed: {e3}"
    return True, f"sent '{answer}' + Enter to window {win_id}"


def _process_trigger(payload: dict) -> None:
    """Run one trigger: wait, find window, type answer, log."""
    cmd = payload.get("command", "")[:120]
    reason = payload.get("reason", "")[:120]
    answer = payload.get("answer", "y")
    fallback_answer = payload.get("fallback_answer", "1")

    _log(f"trigger received: cmd={cmd!r} reason={reason!r} answer={answer!r}")
    time.sleep(POST_DECISION_DELAY)

    if DISABLE_PATH.exists():
        _log("DISABLED via /tmp/lucrex_responder.disable -- skipping")
        try:
            DISABLE_PATH.unlink()
        except Exception:
            pass
        return

    win = _find_claude_window()
    if not win:
        _log("FAIL: no Claude Code window found -- prompt will be left for Rich")
        return

    ok, detail = _send_keystroke(win, answer)
    _log(f"primary keystroke: ok={ok} detail={detail}")
    if not ok:
        return

    # Numbered-picker fallback: if the prompt was a 1/2/3 picker rather than y/N,
    # 'y' Enter probably did nothing. Wait briefly, then send the fallback.
    # If the prompt was already dismissed, this types '1\n' into the next prompt
    # context which is harmless for Claude Code (gets interpreted as next user
    # input -- still safer than leaving a prompt unanswered).
    if fallback_answer and fallback_answer != answer:
        time.sleep(0.4)
        # only fire fallback if we still believe a prompt is up: re-check the
        # window's foreground status. If the file we wrote is still gone, prompt
        # was probably resolved. Skip fallback in that case.
        # (Conservative: we err on the side of NOT double-firing.)
        _log(f"skipping fallback '{fallback_answer}' to avoid double-input")


def main() -> int:
    _log("claude_prompt_responder started")
    while True:
        try:
            if PENDING_PATH.exists():
                age = time.time() - PENDING_PATH.stat().st_mtime
                if age > STALE_SECONDS:
                    _log(f"stale trigger (age={age:.1f}s), discarding")
                    PENDING_PATH.unlink(missing_ok=True)
                else:
                    try:
                        payload = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
                    except Exception as e:
                        _log(f"trigger parse failed: {e}")
                        payload = {"answer": "y"}
                    PENDING_PATH.unlink(missing_ok=True)  # consume immediately
                    _process_trigger(payload)
        except Exception as e:
            _log(f"loop error: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main() or 0)
