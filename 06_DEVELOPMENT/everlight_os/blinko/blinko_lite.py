#!/usr/bin/env python3
"""
BlinkoLite - Lightweight Python-native knowledge base with RAG-style search.

Drop-in replacement for Blinko that runs on PRoot/Android without Docker.
Uses SQLite FTS5 for full-text semantic search + TF-IDF ranking.

API endpoints (compatible with blinko_bridge.py):
  POST /api/v1/note/upsert    - Create or update a note
  POST /api/v1/note/list       - Search notes (text search + FTS5)
  POST /api/v1/note/ai-query   - Search with formatted response
  GET  /api/v1/note/stats      - Database statistics
  GET  /health                 - Health check

Runs on port 1111 by default.
"""
from __future__ import annotations

import json
import os
import re
import signal
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# -- Config -------------------------------------------------------------------
PORT = int(os.environ.get("BLINKO_PORT", "1111"))
DB_PATH = Path(os.environ.get(
    "BLINKO_DB",
    "/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.db"
))
LOG_PATH = Path(os.environ.get(
    "BLINKO_LOG",
    "/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_lite.log"
))
PID_FILE = Path("/tmp/blinko_lite.pid")

# -- Logging ------------------------------------------------------------------

def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# -- Database -----------------------------------------------------------------

_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    """Initialize the database schema."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            type INTEGER DEFAULT 1,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            content,
            tags,
            content_rowid='rowid',
            tokenize='porter unicode61'
        );

        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, content, tags)
            VALUES (new.rowid, new.content, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, content, tags)
            VALUES ('delete', old.rowid, old.content, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, content, tags)
            VALUES ('delete', old.rowid, old.content, old.tags);
            INSERT INTO notes_fts(rowid, content, tags)
            VALUES (new.rowid, new.content, new.tags);
        END;
    """)
    conn.commit()
    conn.close()
    _log(f"Database initialized: {DB_PATH}")


def upsert_note(content: str, note_type: int = 1, note_id: str | None = None) -> dict:
    """Create or update a note."""
    now = datetime.now(timezone.utc).isoformat()
    nid = note_id or str(uuid.uuid4())[:12]

    # Extract tags from content (lines starting with #)
    tags = " ".join(re.findall(r'#[\w/\-]+', content))

    with _db_lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT INTO notes (id, content, type, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     content = excluded.content,
                     tags = excluded.tags,
                     updated_at = excluded.updated_at""",
                (nid, content, note_type, tags, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    return {"id": nid, "status": "ok"}


def search_notes(query: str, page: int = 1, size: int = 10) -> dict:
    """Full-text search with FTS5 ranking."""
    offset = (page - 1) * size

    # Clean query for FTS5 (escape special chars, add prefix matching)
    fts_query = re.sub(r'[^\w\s#/\-]', '', query).strip()
    if not fts_query:
        return {"items": [], "total": 0}

    # Convert to FTS5 query with OR between words for broader matching
    words = fts_query.split()
    fts_terms = " OR ".join(f'"{w}"' for w in words if len(w) > 1)
    if not fts_terms:
        fts_terms = f'"{fts_query}"'

    conn = _get_db()
    try:
        # Try FTS5 search first
        try:
            rows = conn.execute(
                """SELECT n.id, n.content, n.type, n.tags, n.created_at, n.updated_at,
                          rank
                   FROM notes_fts fts
                   JOIN notes n ON n.rowid = fts.rowid
                   WHERE notes_fts MATCH ?
                   ORDER BY rank
                   LIMIT ? OFFSET ?""",
                (fts_terms, size, offset),
            ).fetchall()
        except sqlite3.OperationalError:
            # Fallback to LIKE search if FTS query is malformed
            like_pattern = f"%{query}%"
            rows = conn.execute(
                """SELECT id, content, type, tags, created_at, updated_at, 0 as rank
                   FROM notes
                   WHERE content LIKE ?
                   ORDER BY updated_at DESC
                   LIMIT ? OFFSET ?""",
                (like_pattern, size, offset),
            ).fetchall()

        # Get total count
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM notes_fts WHERE notes_fts MATCH ?",
                (fts_terms,),
            ).fetchone()[0]
        except sqlite3.OperationalError:
            total = len(rows)

    finally:
        conn.close()

    items = [
        {
            "id": r["id"],
            "content": r["content"],
            "type": r["type"],
            "tags": r["tags"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

    return {"items": items, "total": total}


def get_stats() -> dict:
    """Get database statistics."""
    conn = _get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        latest = conn.execute(
            "SELECT updated_at FROM notes ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_notes": total,
        "db_size_mb": round(db_size / (1024 * 1024), 2),
        "db_path": str(DB_PATH),
        "latest_update": latest["updated_at"] if latest else None,
        "uptime_s": int(time.time() - _START_TIME),
    }


# -- HTTP Server --------------------------------------------------------------

_START_TIME = time.time()


class BlinkoHandler(BaseHTTPRequestHandler):
    """HTTP request handler for BlinkoLite API."""

    def log_message(self, fmt, *args):
        """Suppress default logging; we use our own."""
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "blinko-lite", "pid": os.getpid()})
        elif self.path == "/api/v1/note/stats":
            self._send_json(get_stats())
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        data = self._read_json()

        if self.path == "/api/v1/note/upsert":
            content = data.get("content", "")
            if not content.strip():
                self._send_json({"error": "content required"}, 400)
                return
            result = upsert_note(
                content=content,
                note_type=data.get("type", 1),
                note_id=data.get("id"),
            )
            self._send_json(result)

        elif self.path == "/api/v1/note/list":
            query = data.get("searchText", data.get("query", ""))
            if not query.strip():
                self._send_json({"items": [], "total": 0})
                return
            result = search_notes(
                query=query,
                page=data.get("page", 1),
                size=data.get("size", 10),
            )
            self._send_json(result)

        elif self.path == "/api/v1/note/ai-query":
            query = data.get("query", "")
            if not query.strip():
                self._send_json({"response": "No query provided"})
                return
            results = search_notes(query, size=5)
            if not results["items"]:
                self._send_json({"response": f"No notes found matching: {query}"})
                return
            parts = []
            for i, item in enumerate(results["items"], 1):
                content = item["content"][:600]
                parts.append(f"**Result {i}** ({item['created_at'][:10]}):\n{content}")
            response = (
                f"Found {results['total']} matching notes:\n\n"
                + "\n\n---\n\n".join(parts)
            )
            self._send_json({"response": response})

        else:
            self._send_json({"error": "not found"}, 404)


def run_server() -> None:
    """Start the BlinkoLite HTTP server."""
    # Write PID file
    PID_FILE.write_text(str(os.getpid()))

    # Handle graceful shutdown
    def _shutdown(signum, frame):
        _log(f"Received signal {signum}, shutting down...")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Initialize database
    init_db()

    server = HTTPServer(("0.0.0.0", PORT), BlinkoHandler)
    _log(f"BlinkoLite started on port {PORT} (PID {os.getpid()})")
    _log(f"Database: {DB_PATH}")
    _log(f"Health: http://localhost:{PORT}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        PID_FILE.unlink(missing_ok=True)
        _log("BlinkoLite stopped.")


# -- CLI ----------------------------------------------------------------------

if __name__ == "__main__":
    run_server()
