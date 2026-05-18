"""
compliance_log -- single sqlite-backed audit trail for every Intel Center action.

Every investigation, every report view, every export, every purge gets one row.
The wholesale pipeline + OSINT API + dashboard ALL write here. Used by:
  - intel team-usage (audit trail report)
  - Per-state compliance audits (Justine, Brief Calloway, Contract Attorney)
  - Operator review when something goes wrong

Per Operator Truth doctrine: the log is the record. No exception, no skipping.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/compliance.sqlite")

VALID_ACTIONS = {
    "investigate",       # An investigation was kicked off
    "view_report",       # Someone opened a /report/<id> URL
    "view_address",      # Someone opened an /address/<slug> URL
    "export_report",     # Report exported to file/PDF/email
    "save_to_clients",   # Target tagged for the Clients dashboard
    "purge",             # Right-to-purge action
    "policy_violation",  # Pipeline detected an attempt that hit a hard block
    "audit",             # Hive compliance team ran an audit
}


def _con():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS compliance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            actor TEXT,
            lead_id INTEGER,
            business_purpose TEXT,
            ip_addr TEXT,
            user_agent TEXT,
            state TEXT,
            state_rules_consulted TEXT,
            notes TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_cl_ts ON compliance_log(ts)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cl_action ON compliance_log(action)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cl_target ON compliance_log(target)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cl_actor ON compliance_log(actor)")
    return con


def log_action(*, action: str, target: str = "", actor: str = "unknown",
               lead_id: int | None = None, business_purpose: str = "",
               ip_addr: str = "", user_agent: str = "", state: str = "",
               state_rules: dict | None = None, notes: str = "") -> int:
    """
    Append a compliance event. Returns the new row id.
    Best-effort -- never raises into the caller (pipeline must keep moving).
    """
    if action not in VALID_ACTIONS:
        notes = f"[unknown_action={action}] {notes}"
        action = "policy_violation"
    try:
        con = _con()
        rules_json = ""
        if state_rules:
            try: rules_json = json.dumps(state_rules)
            except (TypeError, ValueError): rules_json = ""
        cur = con.execute("""
            INSERT INTO compliance_log
              (ts, action, target, actor, lead_id, business_purpose,
               ip_addr, user_agent, state, state_rules_consulted, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), action, target, actor, lead_id,
              business_purpose, ip_addr, user_agent, state, rules_json, notes))
        new_id = cur.lastrowid
        con.commit()
        con.close()
        return new_id
    except Exception:
        return 0


def recent(limit: int = 50, action: str | None = None) -> list[dict]:
    try:
        con = _con()
        if action:
            rows = con.execute(
                "SELECT * FROM compliance_log WHERE action=? ORDER BY id DESC LIMIT ?",
                (action, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM compliance_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        cols = [d[0] for d in con.execute("PRAGMA table_info(compliance_log)").fetchall()]
        # Use column names from cursor description
        cols = [d[0] for d in con.execute("SELECT * FROM compliance_log LIMIT 0").description]
        con.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def stats() -> dict:
    try:
        con = _con()
        total = con.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        by_action = dict(con.execute(
            "SELECT action, COUNT(*) FROM compliance_log GROUP BY action ORDER BY 2 DESC"
        ).fetchall())
        by_actor = dict(con.execute(
            "SELECT actor, COUNT(*) FROM compliance_log WHERE actor != '' GROUP BY actor ORDER BY 2 DESC LIMIT 10"
        ).fetchall())
        by_state = dict(con.execute(
            "SELECT state, COUNT(*) FROM compliance_log WHERE state != '' GROUP BY state ORDER BY 2 DESC"
        ).fetchall())
        con.close()
        return {"total": total, "by_action": by_action, "by_actor": by_actor, "by_state": by_state}
    except Exception:
        return {"total": 0, "by_action": {}, "by_actor": {}, "by_state": {}}


if __name__ == "__main__":
    log_action(action="audit", target="self_test", actor="cli_user",
               business_purpose="smoke test compliance_log module",
               state="CA", state_rules={"test": True})
    print(json.dumps(stats(), indent=2))
