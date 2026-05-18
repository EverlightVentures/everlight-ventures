"""Investigation persistence + index for past investigations browser."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/investigations.sqlite")
DIR = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/investigations")


def _con():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS investigations (
            id TEXT PRIMARY KEY,
            target TEXT,
            kind TEXT,
            started_at TEXT,
            finished_at TEXT,
            elapsed_ms INTEGER,
            total_findings INTEGER,
            investigators_run INTEGER,
            file_path TEXT
        )
    """)
    # Idempotent attribution columns -- legacy rows get NULL.
    for col, decl in [
        ("triggered_by", "TEXT"),
        ("lead_id", "INTEGER"),
        ("verification_summary", "TEXT"),
        ("business_purpose", "TEXT"),
    ]:
        try:
            con.execute(f"ALTER TABLE investigations ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # already exists
    con.execute("CREATE INDEX IF NOT EXISTS idx_inv_target ON investigations(target)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_inv_started ON investigations(started_at)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_inv_triggered ON investigations(triggered_by)")
    return con


def save_investigation(payload: dict) -> None:
    inv_id = payload["investigation_id"]
    file_path = str(DIR / f"{inv_id}.json")
    con = _con()
    vs = payload.get("verification_summary")
    vs_json = None
    if vs:
        import json as _json
        try:
            vs_json = _json.dumps(vs)
        except (TypeError, ValueError):
            vs_json = None
    con.execute("""
        INSERT OR REPLACE INTO investigations
        (id, target, kind, started_at, finished_at, elapsed_ms, total_findings,
         investigators_run, file_path, triggered_by, lead_id,
         verification_summary, business_purpose)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (inv_id, payload.get("target"), payload.get("kind"),
          payload.get("started_at"), payload.get("finished_at"),
          payload.get("elapsed_ms"), payload.get("total_findings"),
          payload.get("investigators_run"), file_path,
          payload.get("triggered_by"), payload.get("lead_id"), vs_json,
          payload.get("business_purpose")))
    con.commit()
    con.close()


def list_investigations(limit: int = 50) -> list[dict]:
    con = _con()
    rows = con.execute("""
        SELECT id, target, kind, started_at, total_findings, investigators_run, elapsed_ms
        FROM investigations ORDER BY started_at DESC LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    return [
        {"id": i, "target": t, "kind": k, "started_at": s,
         "total_findings": tf, "investigators_run": ir, "elapsed_ms": e}
        for i, t, k, s, tf, ir, e in rows
    ]


def load_investigation(inv_id: str) -> dict | None:
    file_path = DIR / f"{inv_id}.json"
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text())
