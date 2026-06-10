"""
test_osint_validation_20260515.py -- one-shot validation harness.

Runs macro_enrichment on 3 real parsed parcels (dry-run) + email_discovery
on 3 named Tier-1 leads. Reports structured results so we can tell what
actually worked vs failed before any real outbound send.

Per the no-half-ass-audits + operator-truth doctrines.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(WORKSPACE / "06_DEVELOPMENT/everlight_os/intel_center"))
sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel"))

PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"

# ---------------------------------------------------------------------------
# Phase 1: macro_enrichment on 3 real parcels
# ---------------------------------------------------------------------------
print("=" * 70)
print("PHASE 1 -- macro_enrichment.py dry-run on 3 real parcels")
print("=" * 70)

import macro_enrichment as me

parsed_files = sorted(PARSED_DIR.glob("*.json"))[:3]
pitch_copy = me._load_pitch_copy()
print(f"Loaded pitch_copy categories: {list(pitch_copy.keys())}")
print(f"Selected parcels (first 3 alpha): {[p.name for p in parsed_files]}")
print()

# Bump GDELT timeout in this run to account for slow first response
me.TIMEOUT = 12

phase1_results = []
for pf in parsed_files:
    t0 = time.time()
    try:
        r = me.enrich_parcel(pf, pitch_copy, dry_run=True, force=True)
        r["wall_time_s"] = round(time.time() - t0, 1)
        phase1_results.append(r)
        print(f"PARCEL {pf.stem}")
        print(f"  wall: {r['wall_time_s']}s")
        if r.get("changes"):
            for c in r["changes"]:
                print(f"  + {c}")
        else:
            print(f"  (no macro hits this run)")
        if r.get("new_hooks"):
            print(f"  + {r['new_hooks']} new pitch hooks ready")
        if not r.get("ok"):
            print(f"  ERR: {r.get('error', '?')}")
        print()
    except Exception as e:
        print(f"PARCEL {pf.stem} -- EXCEPTION: {e}")
        traceback.print_exc(limit=2)
        phase1_results.append({"path": pf.name, "ok": False,
                                "exception": str(e)[:200],
                                "wall_time_s": round(time.time() - t0, 1)})
        print()

# ---------------------------------------------------------------------------
# Phase 2: email_discovery on 3 Tier-1 named leads
# ---------------------------------------------------------------------------
print("=" * 70)
print("PHASE 2 -- email_discovery on 3 Tier-1 leads")
print("=" * 70)

import httpx
from osint_api.investigators import email_discovery

LEADS = [
    "HOWARD EDDIE",        # Howard Eddie Estate (TX, top target)
    "LEGGETT BENNIE",      # Bennie Leggett (CA, top target)
    "STOKES MARY",         # Stokes (MS, top target)
]


async def run_email_discovery():
    phase2 = []
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for lead in LEADS:
            t0 = time.time()
            print(f"LEAD: {lead}")
            try:
                r = await email_discovery.run(lead, http)
                wall = round(time.time() - t0, 1)
                print(f"  wall: {wall}s")
                print(f"  ok: {r.get('ok')}")
                print(f"  top_score: {r.get('top_score', '?')}/100")
                print(f"  candidates generated: {r['raw'].get('candidates', 0)}")
                print(f"  candidates verified: {r['raw'].get('verified', 0)}")
                print(f"  top findings:")
                for f in r.get("findings", [])[:3]:
                    print(f"    - {f.get('label')}: {f.get('value')}")
                top_cands = r["raw"].get("top_candidates", [])
                if top_cands:
                    print(f"  ranked candidates: {', '.join(top_cands[:3])}")
                phase2.append({
                    "lead": lead, "ok": r.get("ok"),
                    "top_score": r.get("top_score"),
                    "candidates_generated": r["raw"].get("candidates"),
                    "candidates_verified": r["raw"].get("verified"),
                    "top_candidates": top_cands[:3],
                    "wall_time_s": wall,
                })
                print()
            except Exception as e:
                print(f"  EXCEPTION: {e}")
                traceback.print_exc(limit=2)
                phase2.append({"lead": lead, "ok": False,
                                "exception": str(e)[:200],
                                "wall_time_s": round(time.time() - t0, 1)})
                print()
    return phase2


phase2_results = asyncio.run(run_email_discovery())

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("=" * 70)
print("SUMMARY")
print("=" * 70)

phase1_ok = sum(1 for r in phase1_results if r.get("ok"))
phase1_with_changes = sum(1 for r in phase1_results if r.get("changes"))
phase1_total_hits = sum(r.get("macro_hits", 0) for r in phase1_results if r.get("ok"))

phase2_ok = sum(1 for r in phase2_results if r.get("ok"))
phase2_with_high_score = sum(1 for r in phase2_results
                              if (r.get("top_score") or 0) >= 40)

print(f"Phase 1 (macro_enrichment): {phase1_ok}/{len(phase1_results)} ran ok, "
      f"{phase1_with_changes} produced changes, {phase1_total_hits} total macro hits")
print(f"Phase 2 (email_discovery): {phase2_ok}/{len(phase2_results)} ran ok, "
      f"{phase2_with_high_score} with top_score >= 40 (firable threshold)")

# Write JSON summary for downstream consumption
summary = {
    "test_run": "osint_validation_20260515",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "phase1_macro_enrichment": phase1_results,
    "phase2_email_discovery": phase2_results,
    "totals": {
        "phase1_ok": phase1_ok,
        "phase1_with_changes": phase1_with_changes,
        "phase1_macro_hits": phase1_total_hits,
        "phase2_ok": phase2_ok,
        "phase2_high_score": phase2_with_high_score,
    },
}
out_path = WORKSPACE / "_state/test_osint_validation_results_20260515.json"
out_path.write_text(json.dumps(summary, indent=2, default=str))
print(f"\nFull results: {out_path}")
