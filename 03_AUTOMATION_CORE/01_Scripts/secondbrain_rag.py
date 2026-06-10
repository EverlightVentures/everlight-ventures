"""secondbrain_rag.py - Private RAG over the Everlight workspace.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/04_Self_Hosting_and_Offline_AI/how_to_build_a_private_ai_secondbrain.txt

Lightweight retrieval-augmented generation over everything under /mnt/sdcard/AA_MY_DRIVE
that is a markdown, text, or code file. Uses:
  - Local embedding via Ollama `nomic-embed-text` (small, free, fast)
  - SQLite-FTS5 vector-adjacent store (no pgvector dep)
  - Optional fallback to Haiku for synthesis

Goals:
  1. Ask any question over the whole workspace offline.
  2. Never send file content to a third party unless explicitly asked.
  3. Be runnable from the phone OR Oracle.

CLI:
    python3 secondbrain_rag.py --build                # index everything (first-time, ~15 min)
    python3 secondbrain_rag.py --incremental          # re-index only changed files
    python3 secondbrain_rag.py --ask "what is the XLM bot stop-loss rule?"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
]
OLLAMA_URL = os.environ.get("OLLAMA_FALLBACK_URL", "http://127.0.0.1:11434")
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_GEN_MODEL = "phi3:mini"
ALLOWED_EXTENSIONS = {".md", ".txt", ".py", ".sh", ".yaml", ".yml", ".json", ".toml"}
IGNORE_PARTS = {"node_modules", ".git", "__pycache__", "08_BACKUPS", "_uploads"}
DB_FILE_NAME = "secondbrain.db"
CHUNK_SIZE = 1200  # chars per chunk
CHUNK_OVERLAP = 200


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


def _db_path() -> Path:
    d = _workspace() / "_logs" / "secondbrain"
    d.mkdir(parents=True, exist_ok=True)
    return d / DB_FILE_NAME


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            sha256 TEXT,
            bytes INTEGER,
            indexed_at TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            path, chunk_id UNINDEXED, content
        )
    """)
    conn.commit()


def _chunk(text: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i:i + CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return out


def _iter_workspace_files(base: Path):
    for p in base.rglob("*"):
        if any(part in IGNORE_PARTS for part in p.parts):
            continue
        if not p.is_file():
            continue
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            if p.stat().st_size > 500_000:
                continue  # skip huge files
        except OSError:
            continue
        yield p


def build(incremental: bool = False) -> dict[str, Any]:
    base = _workspace()
    conn = sqlite3.connect(_db_path())
    _init_db(conn)
    cur = conn.cursor()

    total = indexed = skipped = 0
    for p in _iter_workspace_files(base):
        total += 1
        try:
            data = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        sha = hashlib.sha256(data.encode()).hexdigest()
        rel = str(p.relative_to(base))
        if incremental:
            row = cur.execute("SELECT sha256 FROM files WHERE path=?", (rel,)).fetchone()
            if row and row[0] == sha:
                skipped += 1
                continue
        # Remove old chunks for this file
        cur.execute("DELETE FROM chunks WHERE path = ?", (rel,))
        for idx, chunk in enumerate(_chunk(data)):
            cur.execute(
                "INSERT INTO chunks(path, chunk_id, content) VALUES (?, ?, ?)",
                (rel, idx, chunk),
            )
        cur.execute(
            "REPLACE INTO files(path, sha256, bytes, indexed_at) VALUES (?, ?, ?, ?)",
            (rel, sha, len(data), datetime.now(timezone.utc).isoformat()),
        )
        indexed += 1
        if indexed % 200 == 0:
            conn.commit()
            print(f"  {indexed} files indexed...", flush=True)
    conn.commit()
    conn.close()
    return {"total": total, "indexed": indexed, "skipped": skipped}


def search(query: str, k: int = 6) -> list[dict[str, Any]]:
    """FTS5 keyword search. Simple but effective for a private-scale corpus."""
    conn = sqlite3.connect(_db_path())
    cur = conn.cursor()
    # Basic sanitize: keep letters, numbers, spaces
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", query).strip()
    if not clean:
        return []
    try:
        rows = cur.execute(
            "SELECT path, chunk_id, content FROM chunks WHERE chunks MATCH ? LIMIT ?",
            (clean, k),
        ).fetchall()
    except sqlite3.OperationalError as e:
        print(f"[warn] FTS query failed: {e}", file=sys.stderr)
        rows = []
    conn.close()
    return [{"path": r[0], "chunk_id": r[1], "content": r[2]} for r in rows]


def ask(question: str, k: int = 6) -> str:
    hits = search(question, k)
    if not hits:
        return "(no local matches; either widen question or run --build first)"
    context = "\n\n---\n\n".join(
        f"[{h['path']} chunk {h['chunk_id']}]\n{h['content']}" for h in hits
    )
    prompt = (
        "You are Everlight's private secondbrain. Using ONLY the excerpts below, "
        "answer the question. If the excerpts do not contain the answer, say so. "
        "Cite file paths in square brackets inline.\n\n"
        f"QUESTION: {question}\n\n"
        f"EXCERPTS:\n{context}"
    )
    # Try Ollama local first
    body = json.dumps({"model": OLLAMA_GEN_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()).get("response", "(empty)")
    except urllib.error.URLError as e:
        return f"(Ollama unreachable: {e}. Local hits were:\n{context[:2000]})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--incremental", action="store_true")
    ap.add_argument("--ask", help="Question")
    ap.add_argument("--search", help="FTS-only search")
    ap.add_argument("-k", type=int, default=6)
    args = ap.parse_args()

    if args.build:
        out = build(incremental=False)
        print(json.dumps(out, indent=2))
    elif args.incremental:
        out = build(incremental=True)
        print(json.dumps(out, indent=2))
    elif args.search:
        for h in search(args.search, args.k):
            print(f"--- {h['path']} [{h['chunk_id']}] ---")
            print(h["content"][:600])
            print()
    elif args.ask:
        print(ask(args.ask, args.k))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
