"""
Persona Inbox Orchestrator -- the autonomous wholesale reply engine.

Operator directive (2026-05-17):
  "Those specific agents need to be monitoring those specific folders and
   replying to emails using their personas. Their templates, their sales
   pitch, our OSINT intel, like all of that needs to come into play when
   they read the emails, pull the data and do a response. It can't just be
   like a simple AI reply, right? It's got to use our infrastructure we
   built for this very reason. Personalized custom-tailored offers, swift
   replies, smart decision-making, getting deals."

What this does:

  1. Loops over each persona's inbox folder (_state/agent_inboxes/<persona>/).
  2. For each unprocessed reply file:
     a. Looks up the matching deal_meta by counterparty email.
     b. If deal exists: classifies reply, computes next_step via arc_send,
        fires the next stage with the persona's voice + templates + OSINT.
     c. If no deal: bootstraps a new deal_meta for the address and fires
        Piper's m1_intro -> Henry's m3_open chain.
  3. Marks the file processed (.processed.json) so we don't double-fire.
  4. Logs every action to _logs/persona_orchestrator.jsonl for Marcus rollup.

Hard guarantees:
  - Every send goes through branded_mailer -> send_authority_gate -> Resend.
  - WHOLESALE_OUTBOUND_HALT=1 puts the orchestrator in DRY-RUN mode (logs
    every action but does not send). Lets the operator review before lifting.
  - No persona can act outside their territory (gate enforces).
  - Back-office personas never fire counterparty sends (gate enforces).

CLI:
  python persona_inbox_orchestrator.py              # one cycle, all personas
  python persona_inbox_orchestrator.py --persona piper_reeves
  python persona_inbox_orchestrator.py --dry-run    # never send, log only
  python persona_inbox_orchestrator.py --watch 300  # loop every 5 min
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
_INBOX_ROOT = _WORKSPACE / "_state" / "agent_inboxes"
_DEALS_ROOT = _WORKSPACE / "09_DASHBOARD" / "reports" / "deals"
_OP_LOG = _WORKSPACE / "_logs" / "persona_orchestrator.jsonl"

# Path hookups
_CT = _WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
_OSINT = _WORKSPACE / "06_DEVELOPMENT/everlight_os/intel_center" / "osint_api"
_AUDIT_DIR = _WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"
for p in (str(_CT), str(_OSINT), str(_AUDIT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

log = logging.getLogger("persona_orchestrator")


def _op_log(event: str, **fields) -> None:
    try:
        _OP_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        with open(_OP_LOG, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception as e:
        log.warning("op log write failed: %s", e)


# ---------------------------------------------------------------------------
# Deal-meta lookup -- find an existing deal by counterparty email
# ---------------------------------------------------------------------------
def find_deal_for_counterparty(from_email: str) -> Optional[tuple[dict, str]]:
    """Return (deal_meta, role) where role in {'seller', 'buyer'}, or None."""
    if not _DEALS_ROOT.exists():
        return None
    fe = (from_email or "").lower().strip()
    if not fe:
        return None
    for deal_dir in _DEALS_ROOT.iterdir():
        meta_path = deal_dir / "deal_meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if (meta.get("seller_email", "") or "").lower() == fe:
            return meta, "seller"
        if (meta.get("buyer_email", "") or "").lower() == fe:
            return meta, "buyer"
    return None


# ---------------------------------------------------------------------------
# Stage detection -- what's the last arc step we fired for this deal?
# ---------------------------------------------------------------------------
def get_last_stage(deal_key: str, role: str) -> Optional[str]:
    """Walk deal_execution_log for last M-/C- stage marker."""
    try:
        from deal_execution_log import deal_history  # type: ignore
    except ImportError:
        log.warning("deal_execution_log unavailable")
        return None
    try:
        events = deal_history(deal_key)
    except Exception as e:
        log.warning("deal_history(%s) failed: %s", deal_key, e)
        return None
    prefix = "M" if role == "seller" else "C"
    for evt in reversed(events or []):
        notes = evt.get("notes", "") or ""
        m = re.search(rf"\b({prefix}\d)\b", notes)
        if m:
            return m.group(1)
    return f"{prefix}1"  # default first step


# ---------------------------------------------------------------------------
# Arc fire -- dispatch into the correct arc_send function
# ---------------------------------------------------------------------------
ARC_FN_BY_STAGE: dict[str, str] = {
    "M1": "m1_intro",
    "M3": "m3_open",
    "M5": "m5_meet",
    "M7": "m7_final",
    "M_CONTRACT": "m7_contract",
    "C1": "c1_pitch",
    "C3": "c3_meet",
    "C5": "c5_final",
    "C_ASSIGNMENT": "c_assignment",
}


def fire_arc(deal_key: str, next_stage: str, counter_amount: int = 0, dry_run: bool = False) -> dict:
    """Call the appropriate arc_send function for the computed next stage."""
    fn_name = ARC_FN_BY_STAGE.get(next_stage)
    if not fn_name:
        return {"ok": False, "error": f"unknown_stage:{next_stage}"}
    try:
        import arc_send  # type: ignore
    except ImportError as e:
        return {"ok": False, "error": f"arc_send_unavailable:{e}"}
    fn = getattr(arc_send, fn_name, None)
    if fn is None:
        return {"ok": False, "error": f"arc_fn_missing:{fn_name}"}
    if dry_run:
        return {"ok": True, "dry_run": True, "would_call": f"{fn_name}({deal_key!r})"}
    try:
        # Functions that take counter_amount accept it as kwarg
        if next_stage in {"M5", "M7", "C3", "C5"} and counter_amount:
            result = fn(deal_key, counter_amount=counter_amount)
        else:
            result = fn(deal_key)
        return {"ok": True, "fn": fn_name, "result": result}
    except Exception as e:
        return {"ok": False, "error": f"arc_fn_exception:{e}"}


# ---------------------------------------------------------------------------
# Reply classification (proxy to arc_send for consistency)
# ---------------------------------------------------------------------------
def classify_reply(body: str) -> str:
    try:
        import arc_send  # type: ignore
        return arc_send.classify_reply(body or "")
    except Exception:
        return "unclear"


# ---------------------------------------------------------------------------
# Cold-reply bootstrapping -- when a real reply lands and no deal exists yet
# ---------------------------------------------------------------------------
def bootstrap_cold_reply(persona_id: str, reply_record: dict, dry_run: bool = False) -> dict:
    """A reply matched an outbound send but there's no deal_meta on disk.

    This happens for early-stage outreach -- Piper sent a cold m1_intro but
    we never created a deal record. Action: create a deal_meta + advance to
    m3_open (Henry takes over after first seller reply).
    """
    from_email = reply_record.get("from_email", "")
    if not from_email:
        return {"ok": False, "error": "no_from_email"}

    # Try to extract address + state from the reply body if available
    body = reply_record.get("raw_body_excerpt", "")
    address = ""
    state = ""
    addr_match = re.search(
        r"\b(\d{1,6}\s+[A-Za-z0-9 .'-]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ct|Court|Ln|Lane|Way|Pl|Place|Pkwy|Parkway|Cir|Circle|Trail|Trl))\b",
        body, re.IGNORECASE,
    )
    if addr_match:
        address = addr_match.group(0)
    state_match = re.search(r"\b([A-Z]{2})\b\s*\d{5}\b", body)
    if state_match:
        state = state_match.group(1)

    deal_key = f"cold-{from_email.replace('@','_at_').replace('.','_')}-{int(time.time())}"

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "would_create_deal": deal_key,
            "would_fire": "m3_open (handoff Piper -> Henry)",
        }

    # Create deal_meta
    deal_dir = _DEALS_ROOT / deal_key
    deal_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "deal_key": deal_key,
        "seller_email": from_email,
        "seller_name": reply_record.get("from_name", ""),
        "seller_address": address,
        "seller_state": state,
        "bootstrapped_from_reply": True,
        "bootstrap_persona": persona_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (deal_dir / "deal_meta.json").write_text(json.dumps(meta, indent=2))

    # Fire m3_open (Henry opens with first number)
    return fire_arc(deal_key, "M3", dry_run=False)


# ---------------------------------------------------------------------------
# Per-persona inbox cycle
# ---------------------------------------------------------------------------
def process_persona_inbox(persona_id: str, dry_run: bool = False) -> dict:
    """Process all unread reply files in a persona's inbox folder.

    Mark each as `.processed.json` after handling so we don't double-fire.
    """
    folder = _INBOX_ROOT / persona_id
    if not folder.exists():
        return {"persona": persona_id, "processed": 0, "note": "no inbox folder"}

    counts = {"processed": 0, "deal_advanced": 0, "cold_bootstrap": 0, "errors": 0, "dry_run": dry_run}

    # Files ending in .json that don't already have .processed in the name
    for fpath in sorted(folder.glob("*.json")):
        if ".processed." in fpath.name:
            continue
        try:
            row = json.loads(fpath.read_text())
        except Exception as e:
            log.warning("malformed inbox file %s: %s", fpath, e)
            counts["errors"] += 1
            continue

        from_email = row.get("from_email", "")
        body = row.get("raw_body_excerpt", "")
        reply_class = classify_reply(body)

        deal_lookup = find_deal_for_counterparty(from_email)
        action_taken = None

        if deal_lookup:
            meta, role = deal_lookup
            deal_key = meta["deal_key"]
            last_stage = get_last_stage(deal_key, role) or ("C1" if role == "buyer" else "M1")
            try:
                import arc_send  # type: ignore
                next_stage_raw = arc_send.next_step(deal_key, last_stage, reply_class, role=role)
            except Exception as e:
                next_stage_raw = None
                log.warning("next_step failed: %s", e)

            if next_stage_raw:
                # Strip optional counter_amount suffix (e.g. "M5:21500")
                next_stage = next_stage_raw.split(":")[0]
                counter = 0
                if ":" in next_stage_raw:
                    try:
                        counter = int(next_stage_raw.split(":")[1])
                    except Exception:
                        counter = 0
                fire_result = fire_arc(deal_key, next_stage, counter, dry_run=dry_run)
                action_taken = {
                    "type": "deal_advance",
                    "deal_key": deal_key,
                    "role": role,
                    "last_stage": last_stage,
                    "reply_class": reply_class,
                    "next_stage": next_stage,
                    "counter_amount": counter,
                    "fire_result": fire_result,
                }
                counts["deal_advanced"] += 1
            else:
                action_taken = {
                    "type": "no_next_step",
                    "deal_key": deal_key,
                    "reply_class": reply_class,
                    "last_stage": last_stage,
                }
        else:
            # Cold reply -- bootstrap
            bootstrap_result = bootstrap_cold_reply(persona_id, row, dry_run=dry_run)
            action_taken = {
                "type": "cold_bootstrap",
                "result": bootstrap_result,
            }
            counts["cold_bootstrap"] += 1

        # Log + mark processed
        _op_log(
            "inbox_action",
            persona_id=persona_id,
            from_email=from_email,
            reply_class=reply_class,
            action=action_taken,
            inbox_file=str(fpath),
            dry_run=dry_run,
        )
        counts["processed"] += 1

        if not dry_run:
            processed_path = fpath.with_name(fpath.stem + ".processed.json")
            try:
                fpath.rename(processed_path)
            except Exception as e:
                log.warning("rename to processed failed: %s", e)

    return {"persona": persona_id, **counts}


# ---------------------------------------------------------------------------
# Top-level cycle -- all personas at once
# ---------------------------------------------------------------------------
# Personas that legitimately reply to counterparties (others are internal_only)
COUNTERPARTY_FACING = {
    "piper_reeves", "henry_hammond", "marvin_cohen", "vaughn_sterling",
    "marvin_tn", "atlas_king", "daria_voss", "cleo_vance",
    "jasper_reeves", "phin_reyes", "stella_marquez",
    # Legacy bucket -- catches replies to pre-gate sends
    "unknown_pre_gate",
}


def run_cycle(persona: Optional[str] = None, dry_run: bool = False) -> dict:
    """Run one orchestrator cycle. Returns per-persona stats."""
    # Respect WHOLESALE_OUTBOUND_HALT -- force dry-run if active
    halt = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}
    effective_dry_run = dry_run or halt
    if halt and not dry_run:
        log.warning("WHOLESALE_OUTBOUND_HALT=1 -- forcing dry-run mode")

    targets = [persona] if persona else sorted(COUNTERPARTY_FACING)
    results = []
    for p in targets:
        try:
            results.append(process_persona_inbox(p, dry_run=effective_dry_run))
        except Exception as e:
            log.exception("persona %s cycle failed: %s", p, e)
            results.append({"persona": p, "error": str(e)})

    summary = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "halt_active": halt,
        "dry_run": effective_dry_run,
        "total_processed": sum(r.get("processed", 0) for r in results),
        "total_advanced": sum(r.get("deal_advanced", 0) for r in results),
        "total_bootstrap": sum(r.get("cold_bootstrap", 0) for r in results),
        "per_persona": results,
    }
    _op_log("cycle_complete", **summary)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser(description="Persona Inbox Orchestrator")
    p.add_argument("--persona", help="run for a single persona (default: all counterparty-facing)")
    p.add_argument("--dry-run", action="store_true", help="never send -- log only")
    p.add_argument("--watch", type=int, default=0, help="loop every N seconds (default: one-shot)")
    args = p.parse_args()

    if args.watch:
        log.info("watch loop every %ds -- Ctrl+C to stop", args.watch)
        while True:
            try:
                result = run_cycle(persona=args.persona, dry_run=args.dry_run)
                print(json.dumps({"summary": {k: v for k, v in result.items() if k != "per_persona"}}, indent=2))
            except KeyboardInterrupt:
                log.info("interrupted")
                break
            except Exception as e:
                log.exception("cycle exception: %s", e)
            time.sleep(args.watch)
    else:
        result = run_cycle(persona=args.persona, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))
