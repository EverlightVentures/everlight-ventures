#!/usr/bin/env python3
"""
run_wheel.py -- the yin-yang wheel, end to end, ONE command.

Merges the pieces that were built separately but never chained:

  ATTOM/Shelby TN properties
        |
        v   (stage 3) build_chris_fit_list.fits_chris()  -- filter to Chris's REAL buy-box
  Chris-fit list (List B)
        |
        v   (stage 4) homeowner_osint.resolve()           -- YOUR O-cent: cross-verify + score
        v            email_confidence_gate.categorize()   -- tier: send | try | skip
  ready_to_contact.json  (tiered, scored, with best candidate email)
        |
        v   (stage 5) rex_belfort_sequence                 -- custom pitch (gated, warmed)

This script does stages 3-4 and writes the ready-to-contact pool. It does NOT send
(sending stays behind Belfort's warming caps + your go-ahead). Free-only.

O-cent resolve is ~60s/lead, so default batch is small. Scale with --limit once
you've watched a batch.

Usage:
    python3 run_wheel.py --limit 8                 # enrich top-8 Chris-fit, tier them
    python3 run_wheel.py --limit 25 --min-score 0  # bigger batch
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES/Everlight_Ventures/Wholesale"
AGENT = ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
FIT_LIST = WH / "config/_generated/chris_fit_list.json"
OUT = WH / "config/_generated/ready_to_contact.json"

for p in (str(WH), str(AGENT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _ensure_fit_list() -> list[dict]:
    """(Re)build List B if missing, then load it."""
    if not FIT_LIST.exists():
        import build_chris_fit_list
        build_chris_fit_list.main()
    return json.loads(FIT_LIST.read_text())["chris_fit"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8, help="how many Chris-fit owners to O-cent this run")
    ap.add_argument("--prefer-no-email", action="store_true",
                    help="prioritize owners that still need an email (the 1,012)")
    args = ap.parse_args()

    fit = _ensure_fit_list()
    # Prioritize: owners that need an email first (that's the whole point of O-cent),
    # unless they already have one and we just want to verify.
    def needs_email(l):
        return not (l.get("email") or l.get("owner_email") or "").strip()
    queue = sorted(fit, key=lambda l: (0 if needs_email(l) else 1) if args.prefer_no_email else 0)
    batch = queue[:args.limit]

    import homeowner_osint as ho
    from email_confidence_gate import categorize, TIER_SEND, TIER_TRY, TIER_SKIP

    print("=" * 64)
    print(f"RUN WHEEL -- Chris-fit={len(fit)}  enriching this batch={len(batch)}")
    print("=" * 64)

    ready = []
    tiers = {TIER_SEND: 0, TIER_TRY: 0, TIER_SKIP: 0}
    for i, lead in enumerate(batch, 1):
        name = lead.get("owner_name", "")
        addr = lead.get("property_address") or lead.get("address", "")
        t0 = time.time()
        try:
            osint = ho.resolve(name=name, address=addr,
                               city=lead.get("city", "Memphis"), state="TN",
                               mailing_address=lead.get("mailing_address", "") or "")
        except Exception as e:
            print(f"  [{i}/{len(batch)}] {name!r}: O-cent error {type(e).__name__}")
            continue
        cands = osint.get("candidate_emails", []) or []
        verdict = categorize(cands, int(osint.get("identity_score") or 0))
        tier = verdict["tier"]
        tiers[tier] = tiers.get(tier, 0) + 1
        rec = {
            "owner_name": name, "address": addr,
            "zip": lead.get("zip") or lead.get("zip_code"),
            "lead_id": lead.get("lead_id") or lead.get("id"),
            "tier": tier, "score": verdict["score"],
            "best_email": verdict.get("best_email") or "",
            "identity_score": osint.get("identity_score"),
            "reason": verdict.get("reason"),
        }
        if tier in (TIER_SEND, TIER_TRY) and verdict.get("best_email"):
            ready.append(rec)
        print(f"  [{i}/{len(batch)}] {name[:28]:28s} -> {tier:4s} "
              f"score={verdict['score']:3d} id={osint.get('identity_score'):>2} "
              f"{verdict.get('best_email') or '(no email)'}  ({time.time()-t0:.0f}s)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "batch": len(batch), "chris_fit_total": len(fit),
        "tiers": tiers, "ready_to_contact": ready,
    }, indent=2, default=str))

    print(f"\ntiers: send={tiers[TIER_SEND]} try={tiers[TIER_TRY]} skip={tiers[TIER_SKIP]}")
    print(f"ready-to-contact (send/try with an email): {len(ready)}")
    print(f"wrote -> {OUT}")
    print("\nNOTE: candidate emails on thin-footprint owners are PERMUTATIONS (free-OSINT")
    print("ceiling). Send small + warmed; bounces self-clean. Sending stays gated in Belfort.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
