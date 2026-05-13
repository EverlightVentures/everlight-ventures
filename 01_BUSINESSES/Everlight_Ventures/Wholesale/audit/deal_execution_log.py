"""
deal_execution_log.py -- immutable audit log of every deal-execution event.

Captures who did what, when, and with what artifact, in a SQLite table that
NEVER gets updated (only inserted into). Each row gets a SHA-256 of the prior
row's hash + this row's content, so tampering is detectable.

Events logged:
  - email_sent        every outbound (links to Resend message_id)
  - doc_rendered      every contract HTML/PDF generated (with sha256 of file)
  - doc_delivered     when a contract link is sent to a counterparty
  - sig_received      when a counterparty's signed doc comes back
  - wire_sent         outbound wire (EMD, balance) with bank confirmation #
  - wire_received     inbound wire (GFAD, payoff) with bank confirmation #
  - settlement_signed at-close settlement statement signed
  - deed_recorded     post-close, deed recorded at county

If something goes to court 3 years from now, this table is the chain of custody.

Usage:
    from deal_execution_log import log_event
    log_event(
        deal_key="2026-05-12_mikal_hakeem_1536_s_third",
        event="email_sent",
        actor="Marquise Reed",
        counterparty="Mikal Hakeem <mhakeem@timemphis.org>",
        artifact_ref="resend:f0f318eb-fe3e-48a5-8b89-f99042de9e84",
        notes="M5 negotiated meet at $9,500",
        amount_usd=9500,
    )
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/audit/deal_execution.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS deal_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    deal_key        TEXT NOT NULL,
    event           TEXT NOT NULL,
    actor           TEXT NOT NULL,
    counterparty    TEXT,
    artifact_ref    TEXT,
    artifact_sha256 TEXT,
    notes           TEXT,
    amount_usd      INTEGER,
    state           TEXT DEFAULT 'TN',
    statute_ref     TEXT,
    prev_hash       TEXT,
    row_hash        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deal_events_deal ON deal_events(deal_key);
CREATE INDEX IF NOT EXISTS idx_deal_events_event ON deal_events(event);
CREATE INDEX IF NOT EXISTS idx_deal_events_ts ON deal_events(ts);
"""


def _ensure_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def _hash_row(prev_hash: str, payload: dict) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or "").encode("utf-8"))
    h.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()


def _file_sha256(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def log_event(
    deal_key: str,
    event: str,
    actor: str,
    counterparty: str | None = None,
    artifact_ref: str | None = None,
    artifact_path: str | None = None,
    notes: str | None = None,
    amount_usd: int | None = None,
    state: str = "TN",
    statute_ref: str | None = None,
) -> dict:
    """
    Append a row. Returns the inserted row dict.
    Hash chain: row.row_hash = sha256(prev_hash + canonical(this_payload))
    """
    _ensure_db()
    ts = datetime.utcnow().isoformat() + "Z"
    artifact_sha256 = _file_sha256(artifact_path) if artifact_path else ""

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT row_hash FROM deal_events ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    prev_hash = row[0] if row else ""

    payload = {
        "ts": ts, "deal_key": deal_key, "event": event, "actor": actor,
        "counterparty": counterparty or "", "artifact_ref": artifact_ref or "",
        "artifact_sha256": artifact_sha256, "notes": notes or "",
        "amount_usd": amount_usd or 0, "state": state, "statute_ref": statute_ref or "",
    }
    row_hash = _hash_row(prev_hash, payload)
    payload["prev_hash"] = prev_hash
    payload["row_hash"] = row_hash

    cur.execute("""
        INSERT INTO deal_events
        (ts, deal_key, event, actor, counterparty, artifact_ref, artifact_sha256,
         notes, amount_usd, state, statute_ref, prev_hash, row_hash)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ts, deal_key, event, actor, counterparty, artifact_ref, artifact_sha256,
          notes, amount_usd, state, statute_ref, prev_hash, row_hash))
    con.commit()
    rid = cur.lastrowid
    con.close()
    payload["id"] = rid
    return payload


def verify_chain(deal_key: str | None = None) -> dict:
    """Replay the hash chain. Returns {ok, broken_at, total_rows}."""
    _ensure_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    q = "SELECT * FROM deal_events"
    args = ()
    if deal_key:
        q += " WHERE deal_key = ?"
        args = (deal_key,)
    q += " ORDER BY id ASC"
    rows = list(con.execute(q, args))
    con.close()

    prev = ""
    for r in rows:
        payload = {k: r[k] for k in ("ts", "deal_key", "event", "actor", "counterparty",
                                       "artifact_ref", "artifact_sha256", "notes",
                                       "amount_usd", "state", "statute_ref")}
        # Convert None to "" / 0 for canonicalization
        for k in ("counterparty", "artifact_ref", "artifact_sha256", "notes", "statute_ref"):
            if payload[k] is None: payload[k] = ""
        if payload["amount_usd"] is None: payload["amount_usd"] = 0
        expected = _hash_row(prev, payload)
        if expected != r["row_hash"]:
            return {"ok": False, "broken_at": r["id"], "total_rows": len(rows)}
        if (r["prev_hash"] or "") != prev:
            return {"ok": False, "broken_at": r["id"], "total_rows": len(rows),
                    "reason": "prev_hash mismatch"}
        prev = r["row_hash"]
    return {"ok": True, "total_rows": len(rows)}


def deal_history(deal_key: str) -> list[dict]:
    _ensure_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = list(con.execute("SELECT * FROM deal_events WHERE deal_key = ? ORDER BY id ASC", (deal_key,)))
    con.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        result = verify_chain()
        print(json.dumps(result, indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "history":
        events = deal_history(sys.argv[2])
        print(json.dumps(events, indent=2))
    else:
        print("usage: deal_execution_log.py {verify | history <deal_key>}")
