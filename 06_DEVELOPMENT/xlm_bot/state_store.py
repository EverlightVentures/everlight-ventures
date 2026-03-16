from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    ts: str
    type: str
    payload: dict[str, Any]


class StateStore:
    """
    Minimal durable store for crash recovery.

    We keep JSON state.json for compatibility with the existing dashboard, but also
    persist critical state transitions here so a restart can reconstruct intent.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def set_kv(self, key: str, value: Any) -> None:
        payload = json.dumps(value, separators=(",", ":"), default=str)
        with self._connect() as con:
            con.execute(
                "INSERT INTO kv(key, value_json, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                (key, payload, _utc_now_iso()),
            )

    def get_kv(self, key: str) -> Any | None:
        with self._connect() as con:
            cur = con.execute("SELECT value_json FROM kv WHERE key = ?", (key,))
            row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def log_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        raw = json.dumps(payload, separators=(",", ":"), default=str)
        with self._connect() as con:
            con.execute(
                "INSERT INTO events(ts, type, payload_json) VALUES(?, ?, ?)",
                (_utc_now_iso(), event_type, raw),
            )

