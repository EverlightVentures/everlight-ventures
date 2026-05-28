"""
osint_enrich.py -- run free OSINT + the confidence gate on owner-enriched leads.

Pre-condition: lead has owner_name (from the assessor harvester) and state.
Post-condition: lead has confidence_tier (auto_email|review|directmail),
                confidence_score, candidate_email; for auto_email tier we
                also set lead.email (so rex_belfort_sequence will pick it up
                on its next 7-touch run).

Runs on the PHONE (osint_api lives at 06_DEVELOPMENT/everlight_os/intel_center).
Free-only by design. Ledger: _logs/enrichment/osint_enrich.jsonl.

Usage:
    python3 osint_enrich.py                 # process up to 25 ready leads
    python3 osint_enrich.py --limit 50
    python3 osint_enrich.py --dry-run       # plan only, no calls
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # so homeowner_osint + email_confidence_gate import

LEADS_DB = HERE / "leads_db.json"
LEDGER = HERE.parent.parent.parent.parent / "_logs" / "enrichment" / "osint_enrich.jsonl"


def _select_ready(leads: list[dict], state: str, limit: int) -> list[dict]:
    """Leads with owner_name, target state, no best_email yet."""
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


def run(args: argparse.Namespace) -> int:
    from homeowner_osint import resolve
    from email_confidence_gate import categorize

    raw = json.loads(LEADS_DB.read_text())
    is_dict = isinstance(raw, dict)
    leads = list(raw.values()) if is_dict else raw
    ready = _select_ready(leads, args.state, args.limit)
    if not ready:
        print(f"[osint_enrich] No ready leads (state={args.state}, limit={args.limit})")
        return 0

    print(f"[osint_enrich] {len(ready)} ready lead(s)")
    if args.dry_run:
        for l in ready[:10]:
            print(f"  WOULD: {l.get('owner_name')!r} @ {l.get('property_address') or l.get('address')!r}")
        print("[osint_enrich] DRY-RUN -- no OSINT calls, no writes.")
        return 0

    tiers = {"auto_email": 0, "review": 0, "directmail": 0}
    ts = datetime.now(timezone.utc).isoformat()
    for lead in ready:
        name = lead.get("owner_name", "")
        addr = lead.get("property_address") or lead.get("address", "")
        city = lead.get("city", "")
        state = lead.get("state", "TN")
        print(f"[osint_enrich] resolving: {name!r} @ {addr!r}")
        try:
            osint = resolve(name=name, address=addr, city=city, state=state)
        except Exception as e:
            _log({"ts": ts, "status": "osint_error", "owner": name, "error": str(e)})
            continue
        cands = osint.get("candidate_emails", []) or []
        identity = int(osint.get("identity_score") or 0)
        verdict = categorize(cands, identity)
        tier = verdict["tier"]
        tiers[tier] = tiers.get(tier, 0) + 1

        lead["confidence_score"] = verdict["score"]
        lead["confidence_tier"] = tier
        lead["confidence_reason"] = verdict["reason"]
        lead["best_email_candidate"] = verdict.get("best_email") or ""
        lead["osint_at"] = ts
        if tier == "auto_email" and verdict.get("best_email"):
            lead["email"] = verdict["best_email"]   # rex_belfort picks this up
            lead["email_source"] = "osint_enrich_auto"
        _log({"ts": ts, "status": "ok", "owner": name, "address": addr,
              "tier": tier, "score": verdict["score"],
              "best_email": verdict.get("best_email")})

    # save leads_db back
    if is_dict:
        keyed = {str(l.get("lead_id") or l.get("id") or ""): l for l in leads}
        LEADS_DB.write_text(json.dumps(keyed, indent=2, default=str))
    else:
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    print(f"[osint_enrich] done. tiers={tiers}")
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
