"""
Inbound Reply Matcher -- detects real seller/buyer replies by cross-referencing
inbound from_email against historical outbound recipients.

Rich's rule (2026-05-17):
  "If any outbound email addresses match any incoming email addresses,
   that is a HUGE indicator someone probably replied to our message.
   And then we have designated agents who actually reach out to the
   right audience. Those emails shouldn't be flagged as promotional
   and they should be sent to folders of the agents who are handling
   those clients."

This module implements that rule.

Reads:
  _logs/resend_budget.jsonl             (every send, all categories)
  _logs/branded_mailer_audit.jsonl      (every gated send, with persona)
  _logs/send_authority_gate.jsonl       (every gate decision, with persona)
  _logs/inbound/hot_inbound.jsonl       (raw inbound stream)

Writes:
  _logs/inbound/real_replies.jsonl      (matched inbound, enriched + routed)
  _state/agent_inboxes/<persona>/<ts>.json
                                        (per-persona reply folder Rich asked for)
  _logs/inbound_reply_matcher.log       (operational log)

Routing logic (in order of trust):
  1. branded_mailer_audit.jsonl  -- canonical, has persona attribution
  2. send_authority_gate.jsonl   -- canonical, has persona attribution
  3. resend_budget.jsonl         -- has recipient + ts but not persona
                                    (older / pre-gate sends fall here)

When a match is found:
  - tag the inbound row with real_reply=True
  - resolve the responsible persona (or "unknown_pre_gate" if pre-Layer-3a)
  - write to that persona's agent_inboxes/ folder
  - append to real_replies.jsonl for Marcus's daily rollup

CLI:
  python inbound_reply_matcher.py --tail        # process new inbound since last run
  python inbound_reply_matcher.py --backfill    # re-scan all hot_inbound history
  python inbound_reply_matcher.py --check <email>  # diagnostic: was email ever contacted?
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("inbound_reply_matcher")

_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
_LOG_DIR = _WORKSPACE / "_logs"
_AUDIT_BRANDED = _LOG_DIR / "branded_mailer_audit.jsonl"
_AUDIT_AUTHORITY = _LOG_DIR / "send_authority_gate.jsonl"
_BUDGET_LEDGER = _LOG_DIR / "resend_budget.jsonl"
_INBOUND_HOT = _LOG_DIR / "inbound" / "hot_inbound.jsonl"
_REAL_REPLIES = _LOG_DIR / "inbound" / "real_replies.jsonl"
_AGENT_INBOXES = _WORKSPACE / "_state" / "agent_inboxes"
_CURSOR_FILE = _WORKSPACE / "_state" / "inbound_reply_matcher_cursor.json"
_OP_LOG = _LOG_DIR / "inbound_reply_matcher.log"


# ----------------------------------------------------------------------------
# Outbound recipient index. The "anyone we ever contacted" lookup table.
# ----------------------------------------------------------------------------
def build_outbound_index() -> dict[str, dict[str, Any]]:
    """Build email -> most-recent send metadata.

    Trust order: branded_mailer_audit > send_authority_gate > resend_budget.
    The last write per email wins, but we prefer richer attribution sources.
    """
    index: dict[str, dict[str, Any]] = {}

    # Pass 1: resend_budget (lowest trust, has recipient + ts but no persona)
    if _BUDGET_LEDGER.exists():
        with open(_BUDGET_LEDGER) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    to = (d.get("to") or "").lower().strip()
                    if not to or "@" not in to:
                        continue
                    if to.endswith("@gmail.com") and "rich.gee" in to:
                        continue  # skip self
                    index[to] = {
                        "source": "resend_budget",
                        "persona_id": "unknown_pre_gate",
                        "subject": d.get("subject", ""),
                        "ts": d.get("ts", ""),
                        "message_id": d.get("message_id", ""),
                        "category": d.get("category", ""),
                    }
                except Exception:
                    continue

    # Pass 2: send_authority_gate audit (has persona, all gate decisions)
    if _AUDIT_AUTHORITY.exists():
        with open(_AUDIT_AUTHORITY) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("verdict") not in {"authorized", "override_granted"}:
                        continue  # only count actually-sent attempts
                    to = (d.get("to") or "").lower().strip()
                    if not to or "@" not in to:
                        continue
                    prior = index.get(to, {})
                    # upgrade record with persona attribution
                    index[to] = {
                        "source": "send_authority_gate",
                        "persona_id": d.get("persona_id", "unknown"),
                        "ts": d.get("ts_utc", prior.get("ts", "")),
                        "state": d.get("state", ""),
                        "caller": d.get("caller", ""),
                    }
                except Exception:
                    continue

    # Pass 3: branded_mailer_audit (highest trust, full attribution)
    if _AUDIT_BRANDED.exists():
        with open(_AUDIT_BRANDED) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    to = (d.get("to") or "").lower().strip()
                    if not to or "@" not in to:
                        continue
                    index[to] = {
                        "source": "branded_mailer_audit",
                        "persona_id": d.get("persona_id", d.get("agent_name", "unknown")),
                        "subject": d.get("subject", ""),
                        "ts": d.get("ts", d.get("ts_utc", "")),
                        "category": d.get("category", ""),
                    }
                except Exception:
                    continue

    return index


# ----------------------------------------------------------------------------
# Cursor management (so --tail only processes new rows)
# ----------------------------------------------------------------------------
def _load_cursor() -> dict[str, Any]:
    if _CURSOR_FILE.exists():
        try:
            return json.loads(_CURSOR_FILE.read_text())
        except Exception:
            pass
    return {"last_line_processed": 0}


def _save_cursor(cur: dict[str, Any]) -> None:
    _CURSOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CURSOR_FILE.write_text(json.dumps(cur, indent=2))


# ----------------------------------------------------------------------------
# Routing -- write per-persona inbox folders
# ----------------------------------------------------------------------------
def _route_to_persona_inbox(persona_id: str, enriched: dict[str, Any]) -> Path:
    persona_dir = _AGENT_INBOXES / (persona_id or "unrouted")
    persona_dir.mkdir(parents=True, exist_ok=True)
    ts = enriched.get("ts_utc", datetime.now(timezone.utc).isoformat())
    safe_ts = ts.replace(":", "").replace(".", "").replace("+", "_")[:20]
    from_email = enriched.get("from_email", "anon").replace("@", "_at_").replace("/", "_")
    out = persona_dir / f"{safe_ts}__{from_email}.json"
    out.write_text(json.dumps(enriched, indent=2))
    return out


# ----------------------------------------------------------------------------
# Core matcher
# ----------------------------------------------------------------------------
def process_inbound(
    *,
    tail: bool = True,
    backfill: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Scan hot_inbound.jsonl and tag/route real replies.

    Returns counts dict.
    """
    index = build_outbound_index()
    log.info("outbound_index_size=%d", len(index))

    if not _INBOUND_HOT.exists():
        log.warning("no hot_inbound.jsonl at %s", _INBOUND_HOT)
        return {"inbound_seen": 0, "matches": 0, "promo": 0}

    cursor = _load_cursor() if (tail and not backfill) else {"last_line_processed": 0}
    start_line = cursor.get("last_line_processed", 0)

    inbound_seen = 0
    matches = 0
    promo = 0
    new_cursor = start_line

    with open(_INBOUND_HOT) as f:
        for idx, line in enumerate(f):
            if idx < start_line and not backfill:
                continue
            new_cursor = idx + 1
            try:
                row = json.loads(line)
            except Exception:
                continue

            inbound_seen += 1
            from_email = (row.get("from_email") or "").lower().strip()
            if not from_email or "@" not in from_email:
                continue

            # exact match
            match = index.get(from_email)

            # domain-fallback match (e.g. reply from a different mailbox at same domain)
            if not match:
                domain = from_email.split("@", 1)[1]
                for known_email, meta in index.items():
                    if known_email.endswith("@" + domain):
                        match = {**meta, "_match_type": "domain_fallback", "_matched_against": known_email}
                        break

            if not match:
                # Optional: tag as promo if from_email looks like a blast sender.
                # We don't auto-discard -- promo classification stays in the
                # downstream classifier, not here.
                promo += 1
                continue

            matches += 1
            persona_id = match.get("persona_id", "unknown_pre_gate")
            enriched = {
                **row,
                "real_reply": True,
                "matched_outbound": {
                    "persona_id": persona_id,
                    "source": match.get("source"),
                    "original_subject": match.get("subject", ""),
                    "original_ts": match.get("ts"),
                    "match_type": match.get("_match_type", "exact"),
                    "matched_against": match.get("_matched_against", from_email),
                },
                "matcher_ts_utc": datetime.now(timezone.utc).isoformat(),
            }

            if dry_run:
                log.info(
                    "DRY-RUN match: from=%s -> persona=%s (subject=%r)",
                    from_email, persona_id, match.get("subject", "")[:60],
                )
                continue

            # Append to real_replies stream
            _REAL_REPLIES.parent.mkdir(parents=True, exist_ok=True)
            with open(_REAL_REPLIES, "a") as out:
                out.write(json.dumps(enriched) + "\n")

            # Route to per-persona inbox
            inbox_path = _route_to_persona_inbox(persona_id, enriched)
            log.info(
                "MATCH: %s -> %s (routed to %s)",
                from_email, persona_id, inbox_path,
            )

            # Apply Gmail label so reply shows up under the persona in phone Gmail UI
            uid = row.get("imap_uid", "")
            if uid:
                try:
                    from gmail_label_router import apply_label
                    label_res = apply_label(uid=uid, persona_id=persona_id)
                    if label_res.get("ok"):
                        log.info("Gmail label applied: uid=%s -> %s", uid, label_res.get("label"))
                    else:
                        log.warning("Gmail label skipped: uid=%s err=%s", uid, label_res.get("error"))
                except Exception as e:
                    log.warning("gmail_label_router unavailable: %s", e)

            # Auto-forward to persona's ImprovMX alias inbox
            try:
                from gmail_label_router import auto_forward_to_alias
                fwd_res = auto_forward_to_alias(
                    persona_id=persona_id,
                    from_email=from_email,
                    from_name=row.get("from_name", ""),
                    subject=row.get("subject", "") or row.get("raw_body_excerpt", "")[:80],
                    body=row.get("raw_body_excerpt", ""),
                )
                if fwd_res.get("ok"):
                    log.info("Auto-forward delivered: %s -> %s", from_email, fwd_res.get("alias"))
                else:
                    log.warning("Auto-forward skipped: %s", fwd_res.get("reason") or fwd_res.get("error"))
            except Exception as e:
                log.warning("auto_forward unavailable: %s", e)

    if tail and not backfill and not dry_run:
        cursor["last_line_processed"] = new_cursor
        cursor["last_run_ts"] = datetime.now(timezone.utc).isoformat()
        cursor["last_run_matches"] = matches
        _save_cursor(cursor)

    return {
        "inbound_seen": inbound_seen,
        "matches": matches,
        "promo_or_no_match": promo,
        "outbound_index_size": len(index),
        "cursor_advanced_to": new_cursor,
    }


def diagnose(email: str) -> dict[str, Any]:
    """CLI helper: was a given inbound address ever in our outbound ledger?"""
    index = build_outbound_index()
    email = email.lower().strip()
    direct = index.get(email)
    domain = email.split("@", 1)[-1] if "@" in email else ""
    domain_hits = [k for k in index if k.endswith("@" + domain)] if domain else []
    return {
        "email": email,
        "exact_match": direct,
        "domain_hits": domain_hits[:10],
        "outbound_index_size": len(index),
    }


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(_OP_LOG),
            logging.StreamHandler(sys.stdout),
        ],
    )

    p = argparse.ArgumentParser(description="Inbound Reply Matcher")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--tail", action="store_true", help="process new inbound rows since last run (default)")
    g.add_argument("--backfill", action="store_true", help="re-scan all hot_inbound history")
    g.add_argument("--check", help="diagnostic: was this email ever in our outbound ledger?")
    p.add_argument("--dry-run", action="store_true", help="show matches without writing")
    args = p.parse_args()

    if args.check:
        result = diagnose(args.check)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)

    result = process_inbound(
        tail=not args.backfill,
        backfill=args.backfill,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
