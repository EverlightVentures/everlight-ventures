"""
osint_enrich.py -- run free OSINT + the confidence gate on owner-enriched leads.

Pre-condition: lead has owner_name (from the assessor harvester) and state.
Post-condition: lead has confidence_tier (send|try|skip),
                confidence_score, candidate_email; for send/try tier we
                also set lead.email (so rex_belfort_sequence will pick it up
                on its next 7-touch run).

Runs on the PHONE (osint_api lives at 06_DEVELOPMENT/everlight_os/intel_center).
Free-only by design. Ledger: _logs/enrichment/osint_enrich.jsonl.

Parallelism: up to 4 OSINT resolve() calls run concurrently via ThreadPoolExecutor.
Results are collected, then merged into leads_db serially on the main thread.
Ledger appends are fine to do per-thread (kernel guarantees atomicity for small writes).

Usage:
    python3 osint_enrich.py                 # process up to 25 ready leads
    python3 osint_enrich.py --limit 50
    python3 osint_enrich.py --dry-run       # plan only, no calls
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # so homeowner_osint + email_confidence_gate import

# Workspace-aware: phone uses /mnt/sdcard/AA_MY_DRIVE (also symlinked on E5);
# else fall back to writing alongside the script. Same pattern as assessor_harvester.
_PHONE_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
_WORKSPACE = _PHONE_ROOT if _PHONE_ROOT.exists() else HERE
LEADS_DB = HERE / "leads_db.json"
LEDGER = _WORKSPACE / "_logs" / "enrichment" / "osint_enrich.jsonl"

_MAX_WORKERS = 4


def _select_ready(leads: list[dict], state: str, limit: int) -> list[dict]:
    """Leads with owner_name, target state, no email enrichment yet."""
    out = []
    for l in leads:
        if not isinstance(l, dict):
            continue
        if (l.get("state") or "").upper() != state.upper():
            continue
        if not l.get("owner_name"):
            continue
        if l.get("best_email") or l.get("confidence_tier"):
            continue
        if not (l.get("address") or l.get("property_address")):
            continue
        out.append(l)
        if len(out) >= limit:
            break
    return out


def _log(rec: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


def _enrich_one(lead: dict, ts: str, resolve_fn, categorize_fn) -> dict:
    """
    Resolve OSINT for a single lead and return an enrichment patch dict.
    Safe to call from a worker thread -- does NOT mutate the lead in place.
    Returns a dict with keys to merge back onto the lead (plus "lead_ref" pointer).
    """
    from email_confidence_gate import TIER_SEND, TIER_TRY, TIER_SKIP

    name = lead.get("owner_name", "")
    addr = lead.get("property_address") or lead.get("address", "")
    city = lead.get("city", "")
    state = lead.get("state", "TN")
    mailing = lead.get("mailing_address", "")
    lead_id = lead.get("lead_id") or lead.get("id") or ""

    patch = {"_lead_ref": id(lead), "_lead_id": lead_id, "_ts": ts}
    try:
        osint = resolve_fn(
            name=name, address=addr, city=city, state=state,
            mailing_address=mailing, lead_id=str(lead_id),
        )
    except TypeError:
        # Older resolve() signature without mailing_address/lead_id
        try:
            osint = resolve_fn(name=name, address=addr, city=city, state=state)
        except Exception as e:
            _log({"ts": ts, "status": "osint_error", "owner": name, "error": str(e)})
            patch["_error"] = str(e)
            return patch
    except Exception as e:
        _log({"ts": ts, "status": "osint_error", "owner": name, "error": str(e)})
        patch["_error"] = str(e)
        return patch

    cands = osint.get("candidate_emails", []) or []
    identity = int(osint.get("identity_score") or 0)
    verdict = categorize_fn(cands, identity)
    tier = verdict["tier"]

    patch["confidence_score"] = verdict["score"]
    patch["confidence_tier"] = tier
    patch["confidence_reason"] = verdict["reason"]
    patch["best_email_candidate"] = verdict.get("best_email") or ""
    patch["osint_at"] = ts

    if tier in {TIER_SEND, TIER_TRY} and verdict.get("best_email"):
        patch["email"] = verdict["best_email"]
        patch["email_source"] = "osint_enrich_" + tier
        patch["confidence_tier_label"] = tier  # alias for rex_belfort compat

    _log({
        "ts": ts, "status": "ok", "owner": name, "address": addr,
        "tier": tier, "score": verdict["score"],
        "best_email": verdict.get("best_email"),
    })
    return patch


def run(args: argparse.Namespace) -> int:
    from homeowner_osint import resolve
    from email_confidence_gate import categorize, TIER_SEND, TIER_TRY, TIER_SKIP

    raw = json.loads(LEADS_DB.read_text())
    is_dict = isinstance(raw, dict)
    leads = list(raw.values()) if is_dict else raw
    ready = _select_ready(leads, args.state, args.limit)
    if not ready:
        print(f"[osint_enrich] No ready leads (state={args.state}, limit={args.limit})")
        return 0

    print(f"[osint_enrich] {len(ready)} ready lead(s) -- dispatching up to {_MAX_WORKERS} workers")
    if args.dry_run:
        for l in ready[:10]:
            print(f"  WOULD: {l.get('owner_name')!r} @ {l.get('property_address') or l.get('address')!r}")
        print("[osint_enrich] DRY-RUN -- no OSINT calls, no writes.")
        return 0

    ts = datetime.now(timezone.utc).isoformat()
    tiers = {TIER_SEND: 0, TIER_TRY: 0, TIER_SKIP: 0}

    # Build a lookup for fast patch merging: id(lead) -> lead
    lead_by_ref = {id(l): l for l in ready}

    # Parallel OSINT resolution -- collect all patches, then merge serially
    patches = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {
            pool.submit(_enrich_one, lead, ts, resolve, categorize): lead
            for lead in ready
        }
        for future in as_completed(futures):
            try:
                patch = future.result()
            except Exception as e:
                name = futures[future].get("owner_name", "?")
                print(f"[osint_enrich] worker error for {name!r}: {e}")
                continue
            patches.append(patch)

    # Serial merge back onto leads (main thread only)
    for patch in patches:
        if "_error" in patch:
            continue
        ref = patch.pop("_lead_ref", None)
        patch.pop("_lead_id", None)
        patch.pop("_ts", None)
        lead = lead_by_ref.get(ref)
        if lead is None:
            continue
        tier = patch.get("confidence_tier", TIER_SKIP)
        tiers[tier] = tiers.get(tier, 0) + 1
        lead.update(patch)

    # Save leads_db back (main thread, after all merges)
    if is_dict:
        keyed = {str(l.get("lead_id") or l.get("id") or ""): l for l in leads}
        LEADS_DB.write_text(json.dumps(keyed, indent=2, default=str))
    else:
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    print(
        f"[osint_enrich] done. "
        f"send={tiers.get(TIER_SEND, 0)} "
        f"try={tiers.get(TIER_TRY, 0)} "
        f"skip={tiers.get(TIER_SKIP, 0)}"
    )
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--state", default="TN")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
