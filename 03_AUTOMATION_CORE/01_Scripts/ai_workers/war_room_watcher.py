#!/usr/bin/env python3
"""
War Room Watcher - auto-execute and notify on new hive sessions.
Enforced Policy: No raw text in Slack. All reports use Native Canvases.
"""

import argparse
import json
import os
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

# Ensure imports work from any cwd
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(WORKSPACE))

# Import the bridge directly from its path
sys.path.append(f"{WORKSPACE}/03_AUTOMATION_CORE/01_Scripts/content_tools")
import slack_canvas_bridge

WAR_ROOM_DIR = WORKSPACE / "_logs" / "ai_war_room"
STATE_FILE = WORKSPACE / "_logs" / ".war_room_watcher_state.json"
POLL_INTERVAL = 30  # seconds

def _post_slack_canvas(file_path, channel="war-room"):
    """Trigger the canvas bridge for a specific log file."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        title = Path(file_path).stem
        slack_canvas_bridge.create_native_canvas(content, title, "warroom")
    except Exception as e:
        print(f"[WATCHER] Canvas Bridge failed: {e}")

def _load_state():
    """Load watcher state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"sessions": {}, "last_check": None}

def _save_state(state):
    """Atomically save watcher state."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.rename(STATE_FILE)

def _is_actionable(summary_text):
    """Heuristic: does the summary contain actionable recommendations?"""
    action_keywords = ["recommend", "implement", "create", "update", "fix", "add", "deploy", "build", "write", "modify"]
    lower = summary_text.lower()
    matches = sum(1 for kw in action_keywords if kw in lower)
    return matches >= 2

def _dispatch_claude_execution(session_dir, summary_text, user_query):
    """Dispatch Claude to execute recommendations from a hive session."""
    print(f"[WATCHER] Dispatching Claude execution for {session_dir.name}")
    reports = []
    for f in sorted(session_dir.glob("*.md")):
        if f.name != "session.json":
            reports.append(f.read_text(encoding="utf-8"))
    combined = "\n\n---\n\n".join(reports)
    
    category = "full"
    session_json = session_dir / "session.json"
    if session_json.exists():
        try:
            sj = json.loads(session_json.read_text())
            category = sj.get("category", "full")
        except Exception: pass

    try:
        from everlight_os.hive_mind.manager_claude import run_detached
        run_detached(user_query=user_query, combined_summary=combined, category=category, war_room_dir=str(session_dir), timeout=300)
        return True
    except Exception as e:
        print(f"[WATCHER] Claude dispatch failed: {e}")
        return False

def _extract_query(session_dir):
    """Extract the original user query from session.json."""
    session_json = session_dir / "session.json"
    if session_json.exists():
        try:
            sj = json.loads(session_json.read_text())
            return sj.get("prompt", sj.get("query", ""))
        except Exception: pass
    summary = session_dir / "combined_summary.md"
    if summary.exists():
        for line in summary.read_text().splitlines():
            if "Prompt:" in line: return line.split("Prompt:", 1)[1].strip()
    return "(unknown query)"

def scan_once(state, auto_execute=True, notify=True, verbose=False):
    """Scan for new/updated sessions and CANVAS them."""
    if not WAR_ROOM_DIR.exists(): return state
    sessions = state.setdefault("sessions", {})

    for session_dir in sorted(WAR_ROOM_DIR.iterdir()):
        if not session_dir.is_dir() or not session_dir.name.startswith("hive_"): continue
        dir_name = session_dir.name
        combined = session_dir / "combined_summary.md"
        exec_report = session_dir / "05_claude_execution_report.md"

        if not combined.exists(): continue
        entry = sessions.get(dir_name, {})

        # -- New session found --
        if not entry.get("summary_notified"):
            if verbose: print(f"[WATCHER] New session: {dir_name}. Canvassing...")
            if notify:
                # Trigger Canvas for the summary
                threading.Thread(target=_post_slack_canvas, args=(combined, "war-room")).start()

            if auto_execute and not exec_report.exists():
                summary_text = combined.read_text(encoding="utf-8")
                if _is_actionable(summary_text):
                    query = _extract_query(session_dir)
                    entry["execution_dispatched"] = _dispatch_claude_execution(session_dir, summary_text, query)

            entry["summary_notified"] = True
            entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            sessions[dir_name] = entry

        # -- Execution report arrived --
        if not entry.get("execution_notified") and exec_report.exists():
            if verbose: print(f"[WATCHER] Execution report found: {dir_name}. Canvassing...")
            if notify:
                # Trigger Canvas for the execution report
                threading.Thread(target=_post_slack_canvas, args=(exec_report, "war-room")).start()
            entry["execution_notified"] = True
            sessions[dir_name] = entry

    state["last_check"] = datetime.now(timezone.utc).isoformat()
    return state

def run_daemon(auto_execute=True, notify=True, verbose=False):
    """Run the watcher as a polling daemon."""
    print(f"[WATCHER] Starting war room watcher (poll every {POLL_INTERVAL}s)")
    state = _load_state()
    while True:
        try:
            state = scan_once(state, auto_execute=auto_execute, notify=notify, verbose=verbose)
            _save_state(state)
        except Exception as e: print(f"[WATCHER] Scan error: {e}")
        time.sleep(POLL_INTERVAL)

def main():
    parser = argparse.ArgumentParser(description="War Room Watcher daemon")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.once:
        state = scan_once(_load_state(), auto_execute=not args.no_execute, notify=not args.no_notify, verbose=True)
        _save_state(state)
        return

    if args.daemon:
        if os.fork() > 0: return
        os.setsid()
        log_path = WORKSPACE / "_logs" / "war_room_watcher.log"
        with open(log_path, "a") as log_fd:
            os.dup2(log_fd.fileno(), 1)
            os.dup2(log_fd.fileno(), 2)
        run_daemon(auto_execute=not args.no_execute, notify=not args.no_notify, verbose=args.verbose)
    else:
        run_daemon(auto_execute=not args.no_execute, notify=not args.no_notify, verbose=args.verbose)

if __name__ == "__main__":
    main()
