#!/usr/bin/env python3
"""
Hive Mind CLI - dispatch prompts to all AI managers simultaneously.
Enforced Policy: publish report links (Google Docs/Canvas) in Slack.
"""

import argparse
import json
import sys
import threading
import os
from pathlib import Path

# Ensure imports work from the new consolidated path
ROOT_DIR = "/mnt/sdcard/AA_MY_DRIVE"
DEV_DIR = f"{ROOT_DIR}/06_DEVELOPMENT"
if DEV_DIR not in sys.path:
    sys.path.insert(0, DEV_DIR)

from everlight_os.hive_mind.dispatcher import dispatch

# Import the Google Docs bridge (replaces Slack Canvas)
BRIDGE_PATH = f"{ROOT_DIR}/03_AUTOMATION_CORE/01_Scripts/content_tools"
if BRIDGE_PATH not in sys.path:
    sys.path.append(BRIDGE_PATH)
try:
    from gdocs_bridge import publish_report as _gdocs_publish
except ImportError:
    _gdocs_publish = None

def _post_hive_to_war_room(session, prompt: str) -> None:
    """Post hive session results as Google Docs with Slack summary links."""
    session_id = session.id or "unknown"
    war_dir = Path(session.war_room_dir) if session.war_room_dir else None

    if not war_dir or not war_dir.exists():
        return

    if _gdocs_publish:
        # Google Docs mode: publish combined summary + individual reports
        summary_file = war_dir / "combined_summary.md"
        if summary_file.exists():
            content = summary_file.read_text(encoding="utf-8")
            first_lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")][:2]
            _gdocs_publish(
                title=f"Hive Session {session_id}",
                content=content,
                folder="05_AI_Workers/Hive_Mind_Logs",
                summary=" ".join(first_lines)[:150] or "Hive mind session complete",
            )

        report_files = sorted(war_dir.glob("*.md"))
        for rf in report_files:
            if rf.name == "combined_summary.md":
                continue
            _gdocs_publish(
                title=rf.stem,
                content=rf.read_text(encoding="utf-8"),
                folder="05_AI_Workers/Hive_Mind_Logs",
                summary=f"Agent report: {rf.stem}",
                slack_channel="#gpt_bot_30",
            )
    else:
        # Canvas fallback removed: keep reports in war room files when bridge is unavailable.
        print(f"[HIVE] gdocs_bridge unavailable; reports saved at: {war_dir}", file=sys.stderr)

def main() -> int:
    parser = argparse.ArgumentParser(description="Hive Mind multi-agent deliberation")
    parser.add_argument("prompt", nargs="*", help="The prompt for the hive")
    parser.add_argument("--mode", choices=["full", "lite", "all"], default="full")
    parser.add_argument("--lite", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--no-slack", action="store_true")
    parser.add_argument("--query-file", type=str, default=None,
                        help="Path to file containing the prompt (avoids argv limits)")
    args = parser.parse_args()

    mode = "lite" if args.lite else ("all" if args.all else args.mode)
    if args.query_file:
        qf = Path(args.query_file)
        if not qf.exists():
            print(f"[HIVE] ERROR: query file not found: {args.query_file}", file=sys.stderr)
            return 1
        prompt = qf.read_text(encoding='utf-8').strip()
    elif args.prompt:
        prompt = " ".join(args.prompt).strip()
    else:
        print("[HIVE] ERROR: no prompt provided (use positional args or --query-file)", file=sys.stderr)
        return 1

    session = dispatch(prompt, mode=mode, verbose=args.verbose and not args.quiet, session_id=args.session_id)

    print(session.combined_summary)

    if not args.no_slack:
        t = threading.Thread(target=_post_hive_to_war_room, args=(session, prompt), daemon=True)
        t.start()
        t.join(timeout=60)

    return 0

if __name__ == "__main__":
    sys.exit(main())
