#!/usr/bin/env python3
"""
Hive Mind CLI - dispatch prompts to all AI managers simultaneously.
Enforced Policy: No raw text in Slack. All reports use Native Canvases.
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

# Import the bridge directly from its path
BRIDGE_PATH = f"{ROOT_DIR}/03_AUTOMATION_CORE/01_Scripts/content_tools"
if BRIDGE_PATH not in sys.path:
    sys.path.append(BRIDGE_PATH)
import slack_canvas_bridge

def _post_hive_to_war_room(session, prompt: str) -> None:
    """Post hive session results as Native Canvases ONLY."""
    session_id = session.id or "unknown"
    war_dir = Path(session.war_room_dir) if session.war_room_dir else None
    
    if not war_dir or not war_dir.exists():
        return

    # 1. Canvas the Combined Summary first
    summary_file = war_dir / "combined_summary.md"
    if summary_file.exists():
        slack_canvas_bridge.create_native_canvas(
            summary_file.read_text(encoding="utf-8"),
            summary_file.stem,
            "warroom"
        )

    # 2. Canvas each individual agent report
    report_files = sorted(war_dir.glob("*.md"))
    for rf in report_files:
        if rf.name == "combined_summary.md":
            continue
        slack_canvas_bridge.create_native_canvas(
            rf.read_text(encoding="utf-8"),
            rf.stem,
            "warroom"
        )

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
