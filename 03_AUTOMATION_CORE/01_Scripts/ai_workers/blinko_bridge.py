#!/usr/bin/env python3
"""
Blinko Bridge - connects the Everlight Hive Mind to Blinko's vector knowledge base.

Responsibilities:
  1. Ingest war room combined_summary.md files into Blinko as searchable notes
  2. Ingest XLM bot Claude advisor decisions for trade memory
  3. Ingest Claude Code tool audit logs (key actions only)
  4. Query Blinko RAG for context retrieval before hive dispatches
  5. Watch for new war room sessions and auto-ingest

Usage:
  # Ingest a specific war room session
  python blinko_bridge.py ingest-session <session_dir>

  # Ingest all unprocessed war room sessions
  python blinko_bridge.py ingest-all

  # Ingest a trade decision
  python blinko_bridge.py ingest-trade <json_file_or_string>

  # Query Blinko for context (RAG search)
  python blinko_bridge.py query "what did codex recommend about stripe?"

  # Watch for new sessions and auto-ingest (daemon mode)
  python blinko_bridge.py watch

  # Ingest Claude memory files
  python blinko_bridge.py ingest-memory
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── Config ──────────────────────────────────────────────────────────
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE").resolve()
WAR_ROOM_DIR = WORKSPACE / "_logs" / "ai_war_room"
MEMORY_DIR = Path("/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory")
TRACKER_FILE = WORKSPACE / "_logs" / "blinko_ingested.json"
XLM_INSIGHT_PATH = WORKSPACE / "06_DEVELOPMENT" / "xlm_bot" / "data" / "ai_insight.json"

BLINKO_URL = os.environ.get("BLINKO_URL", "http://localhost:1111")
BLINKO_TOKEN = os.environ.get("BLINKO_TOKEN", "")  # API auth token if configured

# Tags for organizing notes in Blinko
TAGS = {
    "war_room": "#hive/war-room",
    "trade": "#xlm/trade-decision",
    "memory": "#claude/memory",
    "audit": "#claude/audit",
    "directive": "#xlm/directive",
    "convergence": "#hive/convergence",
    "perplexity": "#hive/intel",
}


# ── HTTP helpers ────────────────────────────────────────────────────

def _api(method: str, endpoint: str, data: dict | None = None) -> dict:
    """Make an API call to Blinko."""
    url = f"{BLINKO_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if BLINKO_TOKEN:
        headers["Authorization"] = f"Bearer {BLINKO_TOKEN}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  [BLINKO ERROR] {e.code}: {err_body[:200]}", file=sys.stderr)
        return {"error": e.code, "detail": err_body[:200]}
    except URLError as e:
        print(f"  [BLINKO UNREACHABLE] {e.reason}", file=sys.stderr)
        return {"error": "unreachable", "detail": str(e.reason)}


def create_note(content: str, note_type: int = 0) -> dict:
    """Create a Blinko note.

    note_type: 0 = blinko (flash note), 1 = note (full doc)
    """
    return _api("POST", "/api/v1/note/upsert", {
        "content": content,
        "type": note_type,
    })


def search_notes(query: str, limit: int = 10) -> dict:
    """RAG search across all Blinko notes."""
    return _api("POST", "/api/v1/note/list", {
        "searchText": query,
        "page": 1,
        "size": limit,
    })


def ai_query(question: str) -> dict:
    """Ask Blinko's AI a question with RAG context from all notes."""
    return _api("POST", "/api/v1/note/ai-query", {
        "query": question,
    })


# ── Tracker (avoid re-ingesting) ───────────────────────────────────

def _load_tracker() -> dict:
    if TRACKER_FILE.exists():
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    return {"sessions": [], "trades": [], "memory_files": [], "last_insight_mtime": 0}


def _save_tracker(tracker: dict) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2), encoding="utf-8")


# ── Ingestors ──────────────────────────────────────────────────────

def ingest_war_room_session(session_dir: Path, tracker: dict) -> bool:
    """Ingest a single war room session into Blinko."""
    dir_name = session_dir.name
    if dir_name in tracker.get("sessions", []):
        return False  # Already ingested

    combined = session_dir / "combined_summary.md"
    session_json = session_dir / "session.json"

    if not combined.exists():
        print(f"  [SKIP] No combined_summary.md in {dir_name}")
        return False

    # Build note content
    summary_text = combined.read_text(encoding="utf-8")

    # Extract session metadata if available
    meta = ""
    if session_json.exists():
        try:
            sdata = json.loads(session_json.read_text(encoding="utf-8"))
            prompt = sdata.get("prompt", "")[:150]
            mode = sdata.get("mode", "unknown")
            routed = ", ".join(sdata.get("routed_to", []))
            ts = sdata.get("created", "")
            meta = (
                f"**Session**: {dir_name}\n"
                f"**Prompt**: {prompt}\n"
                f"**Mode**: {mode} | **Routed**: {routed}\n"
                f"**Timestamp**: {ts}\n\n---\n\n"
            )
        except (json.JSONDecodeError, KeyError):
            pass

    note_content = (
        f"{TAGS['war_room']} {TAGS['convergence']}\n\n"
        f"# War Room: {dir_name}\n\n"
        f"{meta}"
        f"{summary_text}"
    )

    # Also ingest individual manager reports as linked notes
    result = create_note(note_content, note_type=1)
    if "error" in result:
        print(f"  [FAIL] {dir_name}: {result}")
        return False

    print(f"  [OK] Ingested war room: {dir_name}")

    # Ingest individual reports for deeper RAG
    for report_file in sorted(session_dir.glob("*_report.md")):
        report_text = report_file.read_text(encoding="utf-8")
        manager_name = report_file.stem.split("_", 1)[-1].replace("_report", "")
        report_note = (
            f"{TAGS['war_room']} #hive/{manager_name}\n\n"
            f"# {manager_name.upper()} Report: {dir_name}\n\n"
            f"{report_text[:4000]}"
        )
        create_note(report_note, note_type=1)

    tracker.setdefault("sessions", []).append(dir_name)
    return True


def ingest_all_sessions() -> int:
    """Ingest all unprocessed war room sessions."""
    tracker = _load_tracker()
    count = 0

    if not WAR_ROOM_DIR.exists():
        print(f"  [WARN] War room dir not found: {WAR_ROOM_DIR}")
        return 0

    for session_dir in sorted(WAR_ROOM_DIR.iterdir()):
        if not session_dir.is_dir():
            continue
        if ingest_war_room_session(session_dir, tracker):
            count += 1

    _save_tracker(tracker)
    print(f"\n  Ingested {count} new session(s)")
    return count


def ingest_trade_decision(data: dict) -> bool:
    """Ingest an XLM bot trade decision into Blinko."""
    tracker = _load_tracker()

    trigger = data.get("trigger", "unknown")
    action = data.get("action", data.get("directive", "N/A"))
    reasoning = data.get("reasoning", data.get("rationale", ""))
    confidence = data.get("confidence", "N/A")
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    price = data.get("price", "N/A")

    # Dedup key
    dedup = f"{trigger}_{ts}"
    if dedup in tracker.get("trades", []):
        return False

    note_content = (
        f"{TAGS['trade']} {TAGS['directive']}\n\n"
        f"# XLM Trade Decision: {action}\n\n"
        f"**Trigger**: {trigger}\n"
        f"**Action**: {action}\n"
        f"**Confidence**: {confidence}\n"
        f"**Price**: {price}\n"
        f"**Time**: {ts}\n\n"
        f"## Reasoning\n\n{reasoning}\n"
    )

    result = create_note(note_content, note_type=1)
    if "error" in result:
        return False

    tracker.setdefault("trades", []).append(dedup)
    _save_tracker(tracker)
    print(f"  [OK] Ingested trade: {action} @ {ts}")
    return True


def ingest_insight_file() -> bool:
    """Ingest the current ai_insight.json if it has changed."""
    if not XLM_INSIGHT_PATH.exists():
        return False

    tracker = _load_tracker()
    mtime = XLM_INSIGHT_PATH.stat().st_mtime
    if mtime <= tracker.get("last_insight_mtime", 0):
        return False

    try:
        data = json.loads(XLM_INSIGHT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    # Ingest each trigger's cached insight
    ingested = False
    for trigger_name, insight in data.items():
        if isinstance(insight, dict) and insight.get("reasoning"):
            result = ingest_trade_decision({
                "trigger": trigger_name,
                "action": insight.get("action", insight.get("directive", "N/A")),
                "reasoning": insight.get("reasoning", ""),
                "confidence": insight.get("confidence", "N/A"),
                "timestamp": insight.get("ts", datetime.now(timezone.utc).isoformat()),
                "price": insight.get("price", "N/A"),
            })
            if result:
                ingested = True

    tracker["last_insight_mtime"] = mtime
    _save_tracker(tracker)
    return ingested


def ingest_memory_files() -> int:
    """Ingest all Claude Code memory files into Blinko."""
    tracker = _load_tracker()
    count = 0

    if not MEMORY_DIR.exists():
        print(f"  [WARN] Memory dir not found: {MEMORY_DIR}")
        return 0

    for md_file in sorted(MEMORY_DIR.glob("*.md")):
        if md_file.name == "MEMORY.md":
            continue  # Index file, not a memory

        fname = md_file.name
        if fname in tracker.get("memory_files", []):
            # Check if file was modified since last ingest
            mtime = md_file.stat().st_mtime
            # Re-ingest if modified (simple: always re-ingest for now)
            pass

        content = md_file.read_text(encoding="utf-8")
        if not content.strip():
            continue

        note_content = (
            f"{TAGS['memory']}\n\n"
            f"# Claude Memory: {fname}\n\n"
            f"{content}"
        )

        result = create_note(note_content, note_type=1)
        if "error" not in result:
            tracker.setdefault("memory_files", []).append(fname)
            count += 1
            print(f"  [OK] Ingested memory: {fname}")

    _save_tracker(tracker)
    print(f"\n  Ingested {count} memory file(s)")
    return count


# ── Query ──────────────────────────────────────────────────────────

def query_context(question: str, use_ai: bool = False) -> str:
    """Query Blinko for relevant context. Returns formatted string."""
    if use_ai:
        result = ai_query(question)
        if "error" not in result:
            return result.get("response", result.get("answer", str(result)))

    # Fallback to text search
    result = search_notes(question, limit=5)
    if "error" in result:
        return f"[Blinko unavailable: {result.get('detail', 'unknown error')}]"

    notes = result.get("items", result.get("notes", []))
    if not notes:
        return "[No matching notes found in Blinko]"

    output_parts = []
    for note in notes[:5]:
        content = note.get("content", "")
        # Truncate long notes
        if len(content) > 500:
            content = content[:500] + "..."
        output_parts.append(content)

    return "\n\n---\n\n".join(output_parts)


# ── Watch daemon ───────────────────────────────────────────────────

def watch_loop(interval: int = 60) -> None:
    """Watch for new war room sessions and ai_insight changes, auto-ingest."""
    print(f"  Blinko Bridge watcher started (interval: {interval}s)")
    print(f"  Watching: {WAR_ROOM_DIR}")
    print(f"  Blinko URL: {BLINKO_URL}")

    while True:
        try:
            # Ingest new war room sessions
            ingest_all_sessions()

            # Ingest latest trade insights
            ingest_insight_file()

        except KeyboardInterrupt:
            print("\n  Watcher stopped.")
            break
        except Exception as e:
            print(f"  [ERROR] Watch cycle: {e}", file=sys.stderr)

        time.sleep(interval)


# ── CLI ────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Blinko Bridge - Everlight Hive Mind knowledge base connector"
    )
    sub = parser.add_subparsers(dest="command")

    # ingest-session
    p_session = sub.add_parser("ingest-session", help="Ingest a specific war room session")
    p_session.add_argument("session_dir", type=Path, help="Path to session directory")

    # ingest-all
    sub.add_parser("ingest-all", help="Ingest all unprocessed war room sessions")

    # ingest-trade
    p_trade = sub.add_parser("ingest-trade", help="Ingest a trade decision")
    p_trade.add_argument("data", help="JSON string or path to JSON file")

    # ingest-memory
    sub.add_parser("ingest-memory", help="Ingest Claude Code memory files")

    # query
    p_query = sub.add_parser("query", help="RAG search Blinko for context")
    p_query.add_argument("question", help="Natural language query")
    p_query.add_argument("--ai", action="store_true", help="Use AI-powered query (slower)")

    # watch
    p_watch = sub.add_parser("watch", help="Daemon: auto-ingest new sessions and trades")
    p_watch.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    args = parser.parse_args()

    if args.command == "ingest-session":
        tracker = _load_tracker()
        ok = ingest_war_room_session(args.session_dir.resolve(), tracker)
        _save_tracker(tracker)
        return 0 if ok else 1

    elif args.command == "ingest-all":
        ingest_all_sessions()
        return 0

    elif args.command == "ingest-trade":
        data_str = args.data
        if Path(data_str).exists():
            data_str = Path(data_str).read_text(encoding="utf-8")
        data = json.loads(data_str)
        return 0 if ingest_trade_decision(data) else 1

    elif args.command == "ingest-memory":
        ingest_memory_files()
        return 0

    elif args.command == "query":
        result = query_context(args.question, use_ai=args.ai)
        print(result)
        return 0

    elif args.command == "watch":
        watch_loop(interval=args.interval)
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
