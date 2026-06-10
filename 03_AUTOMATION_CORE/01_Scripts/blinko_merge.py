#!/usr/bin/env python3
"""
blinko_merge.py -- aggregate + dedupe multiple blinko_lite.db files into ONE
deduped MASTER, losing nothing but exact-content duplicates.

Strategy (per operator: "aggregate merge then delete duplicates, don't just
compare and delete halfway -- organize, combine, then get rid of leftovers"):
  - Read every source's notes in PRIORITY order (first source wins ties).
  - Dedupe by sha256(content.strip()); the first-seen copy keeps its id /
    created_at / tags (so the primary's canonical ids survive).
  - Write a fresh MASTER db with the CORRECT (fixed) FTS schema; the insert
    trigger rebuilds the search index.
  - VERIFY strict-superset: master row count == count of distinct content
    across all sources. Nothing unique is dropped.

Usage:
  python3 blinko_merge.py OUT.db SRC1.db [SRC2.db ...]
    # sources listed highest-priority first (e.g. e5 snapshot, then _state, _logs)
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY, content TEXT NOT NULL, type INTEGER DEFAULT 1,
    tags TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    content, tags, content_rowid='rowid', tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.rowid;
END;
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.rowid;
    INSERT INTO notes_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
END;
"""


def _hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8", "replace")).hexdigest()


def _cols(con: sqlite3.Connection) -> set[str]:
    return {r[1] for r in con.execute("PRAGMA table_info(notes)")}


def _read(path: str) -> list[dict]:
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    have = _cols(con)
    rows = []
    for r in con.execute("SELECT * FROM notes"):
        d = dict(r)
        content = d.get("content")
        if not content or not str(content).strip():
            continue
        rows.append({
            "id": d.get("id"),
            "content": content,
            "type": d.get("type", 1) if "type" in have else 1,
            "tags": d.get("tags", "") if "tags" in have else "",
            "created_at": str(d.get("created_at") or ""),
            "updated_at": str(d.get("updated_at") or d.get("created_at") or ""),
        })
    con.close()
    return rows


def merge(out_path: str, sources: list[str]) -> dict:
    seen: dict[str, str] = {}        # content-hash -> source that first had it
    master: dict[str, dict] = {}     # content-hash -> row
    used_ids: set[str] = set()
    stats = {"sources": {}, "total_read": 0, "dups_dropped": 0}

    for src in sources:
        rows = _read(src)
        new_here = dups_here = 0
        for row in rows:
            stats["total_read"] += 1
            h = _hash(row["content"])
            if h in master:
                dups_here += 1
                stats["dups_dropped"] += 1
                continue
            # guarantee unique primary key across merged sources
            nid = row["id"] or h[:12]
            if nid in used_ids:
                nid = f"{nid}_{h[:6]}"
            row["id"] = nid
            used_ids.add(nid)
            master[h] = row
            seen[h] = src
            new_here += 1
        stats["sources"][src] = {"read": len(rows), "new_unique": new_here, "dup_of_higher_priority": dups_here}

    Path(out_path).unlink(missing_ok=True)
    con = sqlite3.connect(out_path)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO notes(id, content, type, tags, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        [(r["id"], r["content"], r["type"], r["tags"], r["created_at"], r["updated_at"]) for r in master.values()],
    )
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    f = con.execute("SELECT COUNT(*) FROM notes_fts").fetchone()[0]
    con.close()

    # strict-superset verification: master must equal the count of distinct content
    distinct = len({_hash(r["content"]) for s in sources for r in _read(s)})
    stats["master_rows"] = n
    stats["master_fts"] = f
    stats["distinct_content_all_sources"] = distinct
    stats["superset_ok"] = (n == distinct and f == n)
    return stats


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    out, srcs = sys.argv[1], sys.argv[2:]
    import json
    print(json.dumps(merge(out, srcs), indent=2))
