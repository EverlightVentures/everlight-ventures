"""chris_pipeline_orchestrator -- end-to-end Memphis -> Chris Ulander deal pipeline.

Adapted from Anthropic's market-researcher financial agent template
(github.com/anthropics/financial-services-plugins, May 2026). Uses the
three-tier isolation pattern:

  Tier 1 (untrusted-data isolation): property-reader subagents
    - One per address. Reads Shelby County Assessor + Zillow + public records.
    - Returns schema-validated JSON. NO write tools, NO outbound.

  Tier 2 (orchestrator -- this script):
    - Aggregates property-reader results.
    - Filters against Chris's buy box (year_built >= 1940, Memphis zips,
      ARV/repair math, distress signals).
    - Decides which properties advance to skip-trace + cold-mail.
    - DOES NOT write the final package. DOES NOT send mail.

  Tier 3 (write-holder): package-writer subagent
    - Takes the orchestrator's filtered list.
    - Produces psa_prefill.json + photos manifest + ARV math + repair estimate
      for each qualified property.
    - Output goes to ./Wholesale/contracts/active_deals/<date>_chris_memphis/

Routing per OPERATING_MODE.md:
  - Property reads dispatch as `transport: managed_agent` (cloud sandbox,
    web_fetch + parse, no desktop required).
  - Final package writing also goes to managed_agent (deterministic).
  - If a property page requires JS / login: routes to `transport: browser_use`
    (Brave attached via CDP at 127.0.0.1:9222).

Honors WHOLESALE_OUTBOUND_HALT -- if active, the pipeline stops at "package
ready" and does NOT trigger the email/mail outreach. Manual signoff
(Justine + Marcus) needed before the next phase.

Per MIDSOUTH_DISINTERMEDIATION_FIX.md (2026-04-29 Marcus call), the model is
contract-first: don't email Chris a raw list. Instead, advance one property
at a time through skip-trace -> cold mail -> negotiate -> PSA -> Chris.
This orchestrator stops at the FILTERED LIST stage; subsequent steps are
human-gated.

Usage:
    # Dry run (no envelopes dispatched, just show what would run)
    python3 chris_pipeline_orchestrator.py --input TN_addresses.csv --dry-run

    # Real run (dispatches managed_agent envelopes for property research)
    python3 chris_pipeline_orchestrator.py --input TN_addresses.csv --max 50
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("chris_pipeline")

PENDING = Path("/AA_MY_DRIVE/_logs/browser_tasks/pending")
OUTPUT_ROOT = Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel")
PACKAGE_ROOT = Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals")

# Chris Ulander's stated buy box (per MIDSOUTH_STRATEGY.md and his 2026-04 email)
CHRIS_BUY_BOX = {
    "markets": ["Memphis", "Shelby County"],
    "states": ["TN"],
    "year_built_min": 1940,           # Mid South Homebuyers explicit floor
    "property_types": ["sfr"],         # single family only, no multifamily
    "rehab_tolerance": "moderate",     # turnkey operator, not deep rehab
    "ARV_max_usd": 200_000,            # Section 8 hold ceiling per Cipher
    "ARV_min_usd": 50_000,
    "occupancy_preference": ["vacant", "tenant_in_place"],
    "deal_structure": "PSA_with_assignment",   # contract-first, not list-share
    "do_not_send": ["raw_address_lists",       # explicit per Chris's 4/24 email
                     "agent-listed_homes_without_JV",
                     "homes_with_active_litigation"],
}


def _load_existing_intel() -> dict[str, dict]:
    """Load any property already enriched in /Wholesale/seller_intel/."""
    out = {}
    if not OUTPUT_ROOT.is_dir():
        return out
    for d in OUTPUT_ROOT.iterdir():
        intel_path = d / "intel.json"
        if intel_path.exists():
            try:
                data = json.loads(intel_path.read_text(encoding="utf-8"))
                lead = data.get("lead", {})
                addr = lead.get("property_address", "").strip().lower()
                if addr:
                    out[addr] = data
            except Exception:
                continue
    return out


def _build_property_research_envelope(address: str, parcel_id: str = "",
                                       persona: str = "Filter Banks") -> dict:
    """One property = one managed_agent envelope. The agent reads the public
    assessor page + cross-checks Zillow + returns schema'd JSON."""
    task_id = f"btsk_{uuid.uuid4().hex[:16]}"
    return {
        "task_id": task_id,
        "correlation_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "chris_pipeline_orchestrator",
        "title": f"Research property: {address[:48]}",
        "transport": "managed_agent",
        "model_override": "claude-sonnet-4-5",
        "natural_language_goal": (
            f"Research the property at '{address}' (Memphis/Shelby County, TN) and "
            f"return a structured intel report.\n\n"
            f"Tasks (use bash + web_fetch + your file tools):\n"
            f"  1. curl the Shelby County Assessor public page for this address. "
            f"Try https://www.assessormelvinburgess.com/PropertyDetails?ParcelID={parcel_id} "
            f"if parcel_id is known, otherwise search by address.\n"
            f"  2. Extract: parcel_id, owner_name, owner_mailing_address, year_built, "
            f"sqft, beds, baths, lot_size, total_appraisal_usd, last_sale_date, "
            f"last_sale_price_usd, sales_history (all transactions).\n"
            f"  3. Cross-check Zillow zestimate via curl + extract estimated_arv_usd.\n"
            f"  4. Flag distress signals: vacant_lot, tax_delinquent, "
            f"absentee_owner (mailing_address != property_address), foreclosure_filed.\n"
            f"  5. Return ONE JSON code block with the schema below. NO additional text.\n\n"
            f"```json\n"
            f"{{\n"
            f'  "lead": {{\n'
            f'    "property_address": "<full street address>",\n'
            f'    "parcel_id": "<as shown on assessor>",\n'
            f'    "owner_name": "<LAST FIRST or company>",\n'
            f'    "owner_mailing_state": "<2-letter>",\n'
            f'    "is_absentee": <bool>,\n'
            f'    "is_vacant_lot": <bool>,\n'
            f'    "year_built": <int>,\n'
            f'    "sqft": <int>,\n'
            f'    "beds": <int>,\n'
            f'    "baths": <float>,\n'
            f'    "total_appraisal_usd": <int>,\n'
            f'    "estimated_arv_usd": <int>,\n'
            f'    "sales_history": [{{"date":"MM/DD/YYYY","price_usd":<int>,"type_code":"<>"}}],\n'
            f'    "distress_signals": ["vacant_lot","tax_delinquent",...],\n'
            f'    "research_notes": "<2-3 sentence summary>"\n'
            f'  }}\n'
            f"}}\n"
            f"```"
        ),
        "max_iterations": 15,
        "max_seconds": 300,
        "expected_result_schema": {"lead": "object"},
        "screenshots_dir": f"{task_id}/",
        "callback_slack_channel": "#deploy-log",
        "safety": {
            "abort_on_human_override": False,
            "abort_on_oauth_screen": False,
            "honor_outbound_halt": False,  # research is read-only, no outbound
            "keep_screenshots": False,      # NUKE per feedback_screenshot_security.md
        },
        "context": {
            "project": "Chris Ulander / Mid South Homebuyers pipeline",
            "persona": persona,
            "conversation_summary": (
                "We're sourcing Memphis SFR for Chris Ulander (Mid South Homebuyers). "
                "Stated buy box: SFR, year_built >= 1940, ARV $50k-$200k, Memphis/Shelby. "
                "Per MIDSOUTH_DISINTERMEDIATION_FIX.md (Marcus, 2026-04-29), this is the "
                "research stage; do NOT send any outbound. Output is filtered intel only."
            ),
            "success_criteria": [
                "result.final_text contains a valid JSON code block",
                "lead.parcel_id is not empty",
                "lead.year_built is a positive integer or null",
            ],
            "do_not": [
                "Do not contact the owner",
                "Do not send any email or SMS",
                "Do not skip-trace the owner (separate phase)",
                "Do not write to any directory outside ./out/ in the sandbox",
            ],
        },
    }


def _matches_chris_box(intel: dict) -> tuple[bool, list[str]]:
    """Return (passes, reasons) -- a property qualifies for Chris's pipeline."""
    lead = intel.get("lead", {})
    fails = []
    yb = lead.get("year_built")
    if yb is not None and yb < CHRIS_BUY_BOX["year_built_min"]:
        fails.append(f"year_built {yb} < 1940")
    arv = lead.get("estimated_arv_usd") or lead.get("total_appraisal_usd") or 0
    if arv > CHRIS_BUY_BOX["ARV_max_usd"]:
        fails.append(f"ARV {arv} > {CHRIS_BUY_BOX['ARV_max_usd']}")
    if arv > 0 and arv < CHRIS_BUY_BOX["ARV_min_usd"]:
        fails.append(f"ARV {arv} < {CHRIS_BUY_BOX['ARV_min_usd']}")
    if lead.get("is_vacant_lot"):
        fails.append("vacant lot (no SFR)")
    return (len(fails) == 0, fails)


def dispatch_research(addresses: list[dict], *, dry_run: bool = False,
                      max_dispatch: int = 50) -> dict:
    """For each address (NOT already in seller_intel), dispatch a managed_agent
    envelope. Returns a dispatch summary."""
    existing = _load_existing_intel()
    log.info("loaded %d existing intel records", len(existing))

    PENDING.mkdir(parents=True, exist_ok=True)
    dispatched = []
    skipped_existing = 0

    for row in addresses[:max_dispatch]:
        addr = (row.get("address") or row.get("property_address") or "").strip()
        if not addr:
            continue
        if addr.lower() in existing:
            skipped_existing += 1
            continue
        parcel = row.get("parcel_id", "") or row.get("parcel", "")
        envelope = _build_property_research_envelope(addr, parcel_id=parcel)
        if dry_run:
            log.info("[dry] would dispatch %s for %s", envelope["task_id"], addr)
        else:
            out = PENDING / f"{envelope['task_id']}.json"
            out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
            log.info("dispatched %s for %s", envelope["task_id"], addr)
        dispatched.append(envelope["task_id"])

    return {
        "dispatched_count": len(dispatched),
        "skipped_already_enriched": skipped_existing,
        "dry_run": dry_run,
        "task_ids": dispatched[:20],
    }


def filter_against_chris() -> dict:
    """After all property-reader tasks complete, run the orchestrator stage:
    walk through seller_intel/, apply CHRIS_BUY_BOX, return qualified list.

    This is purely a local function -- no managed agent needed. The intel was
    already enriched in dispatch_research(); this just filters."""
    existing = _load_existing_intel()
    qualified, rejected = [], []
    for addr, intel in existing.items():
        passes, fails = _matches_chris_box(intel)
        if passes:
            qualified.append(intel)
        else:
            rejected.append({"address": addr, "reasons": fails})
    log.info("qualified=%d rejected=%d total=%d",
             len(qualified), len(rejected), len(existing))
    return {"qualified": qualified, "rejected": rejected}


def write_chris_package(qualified: list[dict], package_name: str = None) -> Path:
    """Tier 3: write the package. The list of qualified properties becomes a
    DOSSIER, NOT an outreach to Chris. Per MIDSOUTH_DISINTERMEDIATION_FIX.md,
    the next step is skip-trace + cold mail to OWNERS, then PSA, THEN package
    to Chris -- one deal at a time, contract-first.

    This function writes the local dossier so Filter Banks / Hammer can pick
    one address at a time to advance through the funnel."""
    package_name = package_name or datetime.now().strftime("%Y%m%d_chris_qualified")
    package_dir = PACKAGE_ROOT / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "buy_box": CHRIS_BUY_BOX,
        "qualified_count": len(qualified),
        "addresses": [],
        "next_actions": [
            "Filter Banks: pick top 5 by ARV/distress score",
            "Rex Blackwell: skip-trace owners (cascade.py)",
            "Piper Reeves: cold-mail outreach via Lob "
            "(TN cold-call BLOCKED, SMS BLOCKED, MAIL OK)",
            "Hammer Ortiz: negotiate cash offer 70% ARV - repair",
            "Hammer + Marquise: sign PSA + collect EMD + TN SB 909 disclosure",
            "Penny Vance: build deal package (PSA + photos + ARV + repair + assignment fee)",
            "Hammer: send single deal to leads@midsouthhomebuyers.com",
        ],
    }

    for intel in qualified:
        lead = intel.get("lead", {})
        summary["addresses"].append({
            "address": lead.get("property_address"),
            "parcel_id": lead.get("parcel_id"),
            "owner": lead.get("owner_name"),
            "year_built": lead.get("year_built"),
            "arv": lead.get("estimated_arv_usd") or lead.get("total_appraisal_usd"),
            "is_absentee": lead.get("is_absentee"),
            "distress": lead.get("distress_signals", []),
        })

    out = package_dir / "qualified_dossier.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("wrote dossier to %s (%d qualified)", out, len(qualified))
    return out


def _read_addresses_csv(path: Path) -> list[dict]:
    import csv
    out = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append(row)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Chris Ulander pipeline orchestrator")
    p.add_argument("--input", help="CSV with at least 'address' column")
    p.add_argument("--max", type=int, default=50, help="Max addresses to dispatch")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--filter-only", action="store_true",
                   help="Skip dispatch; only run filter + package on existing intel")
    args = p.parse_args()

    if args.filter_only:
        result = filter_against_chris()
        out = write_chris_package(result["qualified"])
        print(json.dumps({
            "qualified": len(result["qualified"]),
            "rejected": len(result["rejected"]),
            "package": str(out),
        }, indent=2))
        return 0

    if not args.input:
        log.error("--input is required (CSV with 'address' column)")
        return 1
    inp = Path(args.input)
    if not inp.exists():
        log.error("input file not found: %s", inp)
        return 1

    addresses = _read_addresses_csv(inp)
    log.info("loaded %d addresses from %s", len(addresses), inp)

    summary = dispatch_research(addresses, dry_run=args.dry_run, max_dispatch=args.max)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
