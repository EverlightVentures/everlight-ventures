"""
_test_lead -- synthetic smoke test for the verified enricher pipeline.

Run: cd Wholesale && python3 -m skip_trace._test_lead

Creates a mock lead context, runs intel_enricher.enrich_after_trace, and
prints both the raw and verified blocks side-by-side so you can SEE the
verifier rejecting findings that don't belong to this specific person.
"""
import json
import sys
from pathlib import Path

# Ensure we can import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skip_trace.intel_enricher import enrich_after_trace  # type: ignore


def main():
    # Synthetic Linda Smith in Sacramento, CA
    lead_ctx = dict(
        owner_name="Linda Smith",
        address="123 Maple St",
        city="Sacramento",
        state="CA",
        email=None,
        phone=None,
        lead_id=None,  # not persisting to DB
        triggered_by="smoke_test:_test_lead",
    )

    print(f"\n=== Synthetic Lead Context ===")
    for k, v in lead_ctx.items():
        print(f"  {k:<14} {v}")

    print(f"\n=== Running enrichment (verified + DNC + OSINT) ===\n")
    result = enrich_after_trace(**lead_ctx)

    print(f"\n=== DNC Status ===")
    print(f"  dnc_blocked: {result['dnc_blocked']}")
    print(f"  dnc_reason:  {result['dnc_reason']}")

    print(f"\n=== Verification Summary ===")
    vs = result['verification_summary']
    print(f"  total_findings: {vs.get('total_findings')}")
    print(f"  verified:       {vs.get('verified')}")
    print(f"  rejected:       {vs.get('rejected')}")
    print(f"  avg_confidence: {vs.get('avg_confidence')}")
    print(f"  threshold:      {vs.get('threshold')}")

    print(f"\n=== RAW counts (everything we found, regardless of identity match) ===")
    raw = result['raw']
    for k in ("social_profiles_found", "breach_flags", "properties_owned", "red_flags"):
        print(f"  {k:<24} {len(raw.get(k, []))}")

    print(f"\n=== VERIFIED counts (only confidence >= threshold) ===")
    ver = result['verified']
    for k in ("social_profiles_found", "breach_flags", "properties_owned", "red_flags"):
        print(f"  {k:<24} {len(ver.get(k, []))}")

    # Detail: per-finding confidence on raw social profiles
    print(f"\n=== Sample raw social profiles + their confidence scores ===")
    for p in raw.get("social_profiles_found", [])[:5]:
        v = p.get("verification", {})
        conf = v.get("confidence", "?")
        sigs = ", ".join(v.get("matched_signals", []))
        rej = " [REJECTED]" if v.get("rejected") else " [ACCEPTED]"
        print(f"  {p.get('platform','?'):<12} conf={conf:<4} signals=[{sigs}]{rej}")

    print(f"\n=== Output JSON snippet (first 600 chars) ===")
    s = json.dumps(result, indent=2)
    print(s[:600] + ("..." if len(s) > 600 else ""))

    print(f"\n=== Sanity ===")
    if result['dnc_blocked']:
        print("  DNC blocked -- downstream consumers must refuse outreach.")
    elif (vs.get('verified', 0) or 0) == 0:
        print(f"  All {vs.get('total_findings', 0)} findings rejected. Confidence < {vs.get('threshold')}.")
        print(f"  This is the EXPECTED outcome for a generic 'Linda Smith' query:")
        print(f"  the public web has many Linda Smiths and we have no proof")
        print(f"  any of them match the Sacramento, CA lead.")
    else:
        print(f"  {vs.get('verified')}/{vs.get('total_findings')} findings passed verification.")


if __name__ == "__main__":
    main()
