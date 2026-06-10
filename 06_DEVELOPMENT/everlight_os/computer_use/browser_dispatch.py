"""browser_dispatch -- one-shot CLI to drop a browser-use envelope from the
currently-active Firefox window.

Bound to Meta+Shift+B in KDE (manual System Settings step):
    /AA_MY_DRIVE/.venv/bin/python3 \\
      /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use/browser_dispatch.py

What it does:
  1. Reads the currently active window title via xdotool / wmctrl.
  2. If it's Firefox, grabs the URL via Ctrl+L + Ctrl+C + clipboard read.
  3. Builds a browser_use envelope and drops it in pending/.
  4. browser_use_runner picks it up within poll cycle.

Flags:
  --goal "..."         Override the natural-language task (default: 'Summarize this page')
  --model claude-...   Override the LLM (default: claude-sonnet-4-5)
  --persona "..."      Optional named-agent persona (e.g. 'Piper Reeves')
  --no-url             Don't try to grab URL (use natural-language goal only)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PENDING = Path("/AA_MY_DRIVE/_logs/browser_tasks/pending")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_window_title() -> str:
    sys.path.insert(0, "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use")
    import xdotool_safe as xs
    return xs.get_active_window_name()


def _grab_firefox_url() -> str:
    """Send Ctrl+L (focus URL bar), Ctrl+C (copy), read clipboard."""
    sys.path.insert(0, "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use")
    import xdotool_safe as xs
    try:
        xs.key_press("ctrl+l")
        time.sleep(0.15)
        xs.key_press("ctrl+c")
        time.sleep(0.25)  # clipboard sync delay
        xs.key_press("Escape")
        url = xs.clipboard_read()
        if url.startswith(("http://", "https://", "about:", "file://")):
            return url
        return ""
    except Exception:
        return ""


def _build_envelope(*, goal: str, target_url: str, model: str,
                    persona: str = "", title_hint: str = "") -> dict:
    task_id = f"btsk_{uuid.uuid4().hex[:16]}"
    now = _now_iso()
    title = title_hint or (f"Browser dispatch: {target_url[:60]}" if target_url
                            else f"Browser task: {goal[:60]}")
    envelope = {
        "task_id": task_id,
        "correlation_id": task_id,
        "created_at": now,
        "created_by": "browser_dispatch_cli",
        "title": title,
        "natural_language_goal": goal,
        "target_url": target_url or None,
        "transport": "browser_use",
        "model_override": model,
        "max_iterations": 25,
        "max_seconds": 300,
        "screenshots_dir": f"{task_id}/",
        "callback_slack_channel": "#deploy-log",
        "safety": {
            "prohibited_urls": [],
            "abort_on_human_override": True,
            "honor_outbound_halt": True,
        },
        "context": {
            "project": "browser_dispatch CLI",
            "persona": persona,
            "conversation_summary": (
                "Rich dispatched this from the keyboard via browser_dispatch.py. "
                f"Active window when dispatched: {title_hint or '(unknown)'}."
            ),
            "success_criteria": [
                "Result includes captured data or a clear status code",
                "No destructive actions taken",
            ],
            "do_not": [
                "Do not delete user data or click destructive buttons",
                "Do not navigate away from the target URL unless the goal requires it",
            ],
        },
    }
    return envelope


def main() -> int:
    p = argparse.ArgumentParser(description="Dispatch a browser_use envelope from active Firefox")
    p.add_argument("--goal", default="Summarize the current page in 3 bullets",
                   help="Natural-language task")
    p.add_argument("--model", default="claude-sonnet-4-5",
                   help="LLM model override (default: claude-sonnet-4-5)")
    p.add_argument("--persona", default="",
                   help="Optional named-agent persona (e.g. 'Piper Reeves')")
    p.add_argument("--no-url", action="store_true",
                   help="Skip URL grab; use --goal only")
    p.add_argument("--url", default="",
                   help="Explicit URL (skips Firefox probe)")
    args = p.parse_args()

    title_hint = _active_window_title()
    target_url = args.url
    if not target_url and not args.no_url:
        if "Firefox" in title_hint or "Mozilla" in title_hint:
            target_url = _grab_firefox_url()
            if not target_url:
                print(f"WARN: could not grab URL from active Firefox window "
                      f"({title_hint}). Dispatching without target_url.",
                      file=sys.stderr)
        else:
            print(f"WARN: active window is not Firefox ({title_hint}). "
                  f"Dispatching with --goal only (use --url to specify).",
                  file=sys.stderr)

    envelope = _build_envelope(
        goal=args.goal,
        target_url=target_url,
        model=args.model,
        persona=args.persona,
        title_hint=title_hint,
    )
    PENDING.mkdir(parents=True, exist_ok=True)
    out = PENDING / f"{envelope['task_id']}.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    print(f"Dispatched {envelope['task_id']}")
    print(f"  target_url: {target_url or '(none)'}")
    print(f"  goal: {args.goal}")
    print(f"  model: {args.model}")
    print(f"  persona: {args.persona or '(none)'}")
    print(f"  envelope: {out}")
    print(f"\nTail logs: tail -f /AA_MY_DRIVE/_logs/browser_use_runner.log")
    print(f"Watch state: ls -t /AA_MY_DRIVE/_logs/browser_tasks/{{pending,in_progress,done,failed}}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
