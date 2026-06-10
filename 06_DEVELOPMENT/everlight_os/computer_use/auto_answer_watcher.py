"""auto_answer_watcher -- types the picked answer into Claude Code TUI.

Runs as a systemd user service. Polls /tmp/lucrex_auto_answer.json. When a
new entry appears (mtime changed), it:
  1. Counts down 3 seconds (showing notify-send so Rich can intercept).
  2. If a /tmp/lucrex_auto_answer.disable file appears in the countdown,
     aborts and lets Rich answer manually.
  3. Otherwise types the answer into the active Claude Code terminal:
       - Sends Down arrow N times (for choice_index N)
       - Sends Enter
  4. Records the action in /tmp/lucrex_auto_answer.log

Why arrow keys not "1": Claude Code's TUI is an arrow-navigated picker.
Typing "1" doesn't work; Down/Up + Enter is the only reliable input.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ANSWER_PATH = Path("/tmp/lucrex_auto_answer.json")
DISABLE_PATH = Path("/tmp/lucrex_auto_answer.disable")
LOG_PATH = Path("/tmp/lucrex_auto_answer.log")
LAST_PROCESSED_PATH = Path("/tmp/lucrex_auto_answer.last")
COUNTDOWN_SECONDS = 3
POLL_INTERVAL = 0.5


def _log(msg: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] watcher: {msg}\n")
    except Exception:
        pass


def _notify(title: str, body: str, urgency: str = "normal") -> None:
    try:
        subprocess.run(
            ["notify-send", "-t", "3000", "-u", urgency,
             "-i", "input-keyboard", title, body],
            timeout=2, check=False,
        )
    except Exception:
        pass


def _type_answer(choice_index: int) -> bool:
    """Type Down N times + Return into the Claude Code TUI.

    Finding the right window is tricky -- Rich runs Claude Code inside Kitty
    or another terminal whose title doesn't contain 'claude'. Strategy:
      1. Use ACTIVE window (when AskUserQuestion fires, Rich's terminal IS
         the focused window).
      2. Fall back to find-by-title for terminal-emulator names.
      3. Last resort: skip activate, just type into whatever has focus.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import xdotool_safe as xs

    # When AskUserQuestion fires, Rich's terminal IS the focused window
    # (he's interacting with it). xdotool key without --window sends to the
    # focused window. So we DO NOT activate -- doing so could de-focus the
    # terminal (e.g., wid=root reports an empty-named window). Just type.
    active_name = xs.get_active_window_name()
    active_wid = xs.get_active_window_id()
    _log(f"typing into focused window: wid={active_wid!r} name={active_name!r}")

    # Sanity guard: if the active window looks like a known non-terminal
    # (Brave, Firefox, Spectacle, etc), abort -- typing arrows there could
    # navigate something destructive.
    bad_substrings = ("Brave", "Firefox", "Mozilla", "Chromium", "Spectacle",
                      "System Settings", "Plasma")
    if any(b.lower() in active_name.lower() for b in bad_substrings):
        _log(f"REFUSING to type into '{active_name}' -- not a terminal")
        return False

    # Type Down N + Return into focused window
    for _ in range(choice_index):
        xs.key_press("Down")
        time.sleep(0.08)
    ok, det = xs.key_press("Return")
    if not ok:
        _log(f"return key failed: {det}")
        return False
    return True


def main() -> int:
    _log("auto_answer_watcher starting")
    last_mtime = 0.0
    if LAST_PROCESSED_PATH.exists():
        try:
            last_mtime = float(LAST_PROCESSED_PATH.read_text())
        except Exception:
            pass

    while True:
        try:
            if not ANSWER_PATH.exists():
                time.sleep(POLL_INTERVAL)
                continue
            mt = ANSWER_PATH.stat().st_mtime
            if mt <= last_mtime:
                time.sleep(POLL_INTERVAL)
                continue
            # New answer to process
            payload = json.loads(ANSWER_PATH.read_text(encoding="utf-8"))
            ci = payload.get("choice_index", 0)
            label = payload.get("choice_label", "?")
            reasoning = payload.get("reasoning", "")

            _log(f"new answer detected: [{ci}] '{label}' ({reasoning})")
            _notify(
                "🤖 Auto-answer in 3s",
                f"Picking [{ci}] {label}\nTouch /tmp/lucrex_auto_answer.disable to abort",
            )

            # 3-sec countdown with abort check
            aborted = False
            for i in range(COUNTDOWN_SECONDS * 2):
                time.sleep(0.5)
                if DISABLE_PATH.exists():
                    aborted = True
                    try:
                        DISABLE_PATH.unlink()
                    except Exception:
                        pass
                    break

            if aborted:
                _log("ABORTED by disable file -- letting Rich answer manually")
                _notify("⏸ Auto-answer aborted", "Rich is answering manually",
                        urgency="low")
            else:
                ok = _type_answer(ci)
                if ok:
                    _log(f"typed answer [{ci}] successfully")
                    _notify("✓ Auto-answered",
                            f"Picked [{ci}] {label}", urgency="low")
                else:
                    _log("type failed; check /tmp/lucrex_auto_answer.log")

            last_mtime = mt
            LAST_PROCESSED_PATH.write_text(str(mt), encoding="utf-8")
        except Exception as e:
            _log(f"loop error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main() or 0)
