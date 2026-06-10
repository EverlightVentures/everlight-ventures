"""State Offer Workflow — state-agnostic end-to-end orchestrator for any configured state.

Last Updated: 2026-05-05 11:00 PT (2026-05-05T11:00:00-07:00)

Generalized from tx_offer_workflow.py. Reads:
    - state_gates.json (canonical state config: license, bond, disclosure rules)
    - title_companies.json (preferred closer per metro)
    - compliance/states/<XX>_PLAYBOOK.md (legal narrative for the operator)
    - compliance/states/<XX>_DISCLOSURE_v1.0_SIGNED.md (counsel-signed sentinel)

Same pipeline as TX: comps → ARV → MAO → offer letter → state-specific PSA → marcus_queue.
The ONLY state-specific overlays are:
    1. The PSA addendum text (option period, title routing, statutory disclosure clause)
    2. The disclosure-counsel sentinel path
    3. The market_code → land-premium multiplier mapping in offer_pricing
    4. The from-agent (Marcus quarterback during build, Hammer once anchor signed)

Hard gates remain identical: PERPLEXITY_API_KEY missing, comp confidence LOW, MAO≤0,
state not active_in_pipeline, counsel-signed sentinel missing → all escalate to Marcus.

This module DOES NOT SEND emails. All artifacts staged in marcus_queue/<deal_id>/ for review.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Repo paths
WORKSPACE = Path("/AA_MY_DRIVE")
WHOLESALE_DIR = WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
BROKER_OS_DIR = WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS"
MARCUS_QUEUE = WHOLESALE_DIR / "marcus_queue"
COMPLIANCE_DIR = WHOLESALE_DIR / "compliance"
STATES_DIR = COMPLIANCE_DIR / "states"
CONTRACTS_DIR = BROKER_OS_DIR / "contracts"

# Module-local paths
sys.path.insert(0, str(BROKER_OS_DIR / "wholesale_agent"))
sys.path.insert(0, str(BROKER_OS_DIR / "wholesale_agent" / "wholesale"))

logging.basicConfig(
    level=logging.INFO,
    format="[State-Offer %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("state_offer_workflow")


# ---------------------------------------------------------------------------
# Pacific timestamp helper (matches Hive timestamp standard)
# ---------------------------------------------------------------------------

def pt_now_iso() -> str:
    pacific = timezone(timedelta(hours=-7))  # PDT (May-Oct). Switch to -8 for PST (Nov-Mar).
    return datetime.now(pacific).isoformat(timespec="seconds")


def pt_now_human() -> str:
    pacific = timezone(timedelta(hours=-7))
    return datetime.now(pacific).strftime("%Y-%m-%d %H:%M PT")


# ---------------------------------------------------------------------------
# State config readers
# ---------------------------------------------------------------------------

def load_state_gates() -> dict:
    """Read the canonical state_gates.json."""
    path = COMPLIANCE_DIR / "state_gates.json"
    return json.loads(path.read_text())


def load_title_companies() -> dict:
    """Read title_companies.json from Broker_OS."""
    path = BROKER_OS_DIR / "wholesale_agent" / "title_companies.json"
    return json.loads(path.read_text())


def state_is_active(state: str) -> tuple[bool, str]:
    """Return (active, reason) for whether this state is cleared for live use."""
    gates = load_state_gates()
    cfg = gates.get(state.upper())
    if not cfg:
        return (False, f"state {state} not in state_gates.json")
    if not cfg.get("active_in_pipeline"):
        return (False, f"state {state} active_in_pipeline=false")
    if cfg.get("wholesale_legal_status") != "legal_unlicensed_with_disclosures":
        return (False, f"state {state} legal_status={cfg.get('wholesale_legal_status')}")
    return (True, "ok")


def disclosure_counsel_signed(state: str) -> bool:
    """Return True only when the per-state v1.0 disclosure has cleared counsel.

    Sentinel file: `compliance/states/<XX>_DISCLOSURE_v1.0_SIGNED.md`. Bernard creates
    after counsel sign-off. Until present, all generated offer letters stage with
    BLOCKED_PENDING_COUNSEL flag and cannot be sent.
    """
    sentinel = STATES_DIR / f"{state.upper()}_DISCLOSURE_v1.0_SIGNED.md"
    return sentinel.exists()


def get_title_partner(state: str, market: str) -> Optional[dict]:
    """Return the preferred title partner record for a state+market.

    market is a key in title_companies.json (e.g., 'dallas', 'memphis', 'atlanta',
    'cleveland', 'st_louis', 'jacksonville', 'houston'). Returns first record with
    handles_assignments=true, or None.
    """
    titles = load_title_companies()
    market_records = titles.get(market.lower(), [])
    for rec in market_records:
        if rec.get("handles_assignments"):
            return rec
    return None


def get_state_disclosure_text(state: str) -> str:
    """Read the per-state disclosure text. Falls back to state_advertising_disclaimers."""
    sentinel = STATES_DIR / f"{state.upper()}_DISCLOSURE_v1.0_DRAFT.md"
    signed = STATES_DIR / f"{state.upper()}_DISCLOSURE_v1.0_SIGNED.md"
    if signed.exists():
        return signed.read_text()
    if sentinel.exists():
        return sentinel.read_text()
    # Fallback to the inline state_advertising_disclaimers.py text
    try:
        sys.path.insert(0, str(COMPLIANCE_DIR))
        from state_advertising_disclaimers import disclaimer_for  # type: ignore
        return disclaimer_for(state.upper())
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Stage 1 — pull comps + validate ARV (delegates to rex_comp_validator)
# ---------------------------------------------------------------------------

def pull_comps(address: str, beds: int, baths: float, sqft: int, market_code: str) -> dict:
    try:
        from rex_comp_validator import validate_arv  # type: ignore
    except ImportError:
        return {"status": "escalate", "reason": "rex_comp_validator import failed"}

    if not os.environ.get("PERPLEXITY_API_KEY"):
        return {"status": "escalate", "reason": "PERPLEXITY_API_KEY missing"}

    try:
        result = validate_arv(address=address, beds=beds, baths=baths, sqft=sqft)
    except Exception as e:
        return {"status": "escalate", "reason": f"validate_arv exception: {e}"}

    if result.get("confidence") not in ("HIGH", "MEDIUM"):
        return {"status": "escalate", "reason": "comp confidence LOW", "raw": result}

    return {
        "status": "ok",
        "arv": result.get("validated_arv"),
        "confidence": result.get("confidence"),
        "comps": result.get("comps", []),
        "notes": result.get("notes", ""),
    }


# ---------------------------------------------------------------------------
# Stage 2 — calculate MAO (delegates to offer_pricing)
# ---------------------------------------------------------------------------

def calculate_mao(arv: float, rehab: float, market_code: str, target_fee: float = 10_000.0) -> dict:
    try:
        from offer_pricing import max_offer  # type: ignore
    except ImportError:
        return {"status": "escalate", "reason": "offer_pricing import failed"}

    try:
        offer = max_offer(
            strategy="seventy_rule",
            arv=arv,
            rehab=rehab,
            market_code=market_code,
            target_fee=target_fee,
        )
    except Exception as e:
        return {"status": "escalate", "reason": f"max_offer exception: {e}"}

    if offer.offer_to_seller <= 0:
        return {"status": "escalate", "reason": "MAO ≤ 0 (underwater)"}

    return {
        "status": "ok",
        "strategy": offer.strategy,
        "offer_to_seller": offer.offer_to_seller,
        "assignment_fee": offer.assignment_fee,
        "buyer_pays": offer.buyer_pays,
        "margin_ok": offer.margin_ok,
        "notes": offer.notes,
    }


# ---------------------------------------------------------------------------
# Stage 3 — generate offer letter (state-aware, Marcus quarterback)
# ---------------------------------------------------------------------------

def _get_option_period_days(state: str) -> int:
    """Default option period per state. TX = 10. Most others negotiated, default 7."""
    return {
        "TX": 10,
        "TN": 7,
        "GA": 7,
        "FL": 7,
        "MO": 7,
        "OH": 7,
        "AZ": 10,  # AZ standard 10-day inspection
    }.get(state.upper(), 7)


def _get_state_disclaimer_block(state: str) -> str:
    """Return the per-state disclosure footer text from state_advertising_disclaimers."""
    try:
        sys.path.insert(0, str(COMPLIANCE_DIR))
        from state_advertising_disclaimers import disclaimer_for  # type: ignore
        return disclaimer_for(state.upper())
    except Exception:
        return ""


def generate_offer_letter(deal: dict, mao: dict) -> str:
    state = deal.get("state", "").upper()
    address = deal.get("address", "[ADDRESS]")
    seller_name = deal.get("seller_name", "[SELLER NAME]")
    arv = mao.get("arv", deal.get("arv", 0))
    offer_amount = mao.get("offer_to_seller", 0)
    option_days = _get_option_period_days(state)
    disclaimer = _get_state_disclaimer_block(state)

    # Title routing per state
    title_partner = get_title_partner(state, deal.get("market", "").lower())
    title_text = (
        f"{title_partner['name']} ({title_partner.get('phone', '')})"
        if title_partner else "[STATE]-licensed title company"
    )

    body = f"""# Offer for {address}

Dear {seller_name},

Thank you for replying. I'm Marcus Cole with Everlight Ventures. We received your message
about the property at {address} and I've put together an initial cash offer.

**Offer details:**
- Property: {address}
- Estimated after-repair value (ARV): ${arv:,.0f}
- **Our cash offer: ${offer_amount:,.0f}**
- Earnest money: $1,000 to a {state}-licensed title company
- Closing: 14-21 days through {title_text} (or seller's preferred {state}-licensed title company)
- Option period: {option_days} days

**How we close:** Everlight Ventures or our assignee will purchase. Our purchase contract
will include a "and/or assigns" provision so we can bring in a partner-buyer if it shortens
your timeline. Earnest money is fully refundable through your option period.

This is an initial offer based on comparable sales near your property. If you have rehab
estimates, recent improvements, or pictures that would change the math, send them my way
and I will revisit.

Two next steps if this works for you:

1. Reply with a good time for a 10-minute call to confirm details.
2. I will send the purchase contract via Documenso for your review. No obligation to sign.

If the number is too low, tell me what you need and I will see if we can structure
something that works for both sides.

Best,
Marcus Cole
Operations, Everlight Ventures
marcus@everlightventures.io
[Sacramento, CA mailing address on file]

---

{disclaimer}

To stop receiving messages from us, reply STOP and we will remove your contact immediately.
"""
    return body


# ---------------------------------------------------------------------------
# Stage 4 — generate state-specific PSA from base template
# ---------------------------------------------------------------------------

def _build_state_addendum(deal: dict, mao: dict, gates: dict) -> str:
    """Compose the per-state PSA addendum dynamically from state_gates + title_companies."""
    state = deal.get("state", "").upper()
    cfg = gates.get(state, {})
    option_days = _get_option_period_days(state)
    title_partner = get_title_partner(state, deal.get("market", "").lower())

    title_block = (
        f"**{title_partner['name']}**, {title_partner.get('website', '')} "
        f"(phone: {title_partner.get('phone', 'TBD')})"
    ) if title_partner else f"a {state}-licensed title company"

    closing_type = cfg.get("closing_type", "title_company")
    state_disclosure_required = cfg.get("required_seller_disclosure", "")
    sb_required = "Yes" if cfg.get("sb1577_required") else "No (state-specific disclosure rules apply)"

    # Per-state statute citations
    state_statute_block = {
        "TX": (
            "Texas Property Code §5.0205 (wholesaler equitable-interest disclosure, eff. 2024-01-01)\n"
            "Texas Insurance Code Chapter 2651 (title agency licensing)\n"
            "Texas Bus. & Com. Code §17.46 (DTPA)"
        ),
        "TN": (
            "TN SB 909 (wholesaler disclosure)\n"
            "TN Code 62-13-104 (real estate brokerage — license + surety bond if engaged in business)\n"
            "TN TSA 47-18-2002 (telephone solicitor registration)"
        ),
        "GA": (
            "OCGA §43-40 (real estate brokerage)\n"
            "GA equitable-interest doctrine + standard disclosure"
        ),
        "FL": (
            "FL Statute Chapter 475 (real estate brokerage)\n"
            "FL doc-stamp tax under Chapter 201"
        ),
        "MO": (
            "MO Statute Chapter 339 (real estate brokerage)\n"
            "MO equitable-interest doctrine"
        ),
        "OH": (
            "OH Equitable Interest Doctrine (case law + ORC Chapter 4735 broker rules)"
        ),
        "AZ": (
            "Arizona Revised Statutes §33-422 (Affidavit of Disclosure)\n"
            "ARS §32-2101 (real estate brokerage exemption for principal)"
        ),
    }.get(state, f"[{state} statute citations — see compliance/states/{state}_PLAYBOOK.md]")

    addendum = f"""

---

## {state}-SPECIFIC ADDENDUM

### Option Period
Buyer's option period is **{option_days} days** from the effective date. Buyer pays a
non-refundable option fee of $200 directly to seller. During the option period, buyer may
terminate the contract for any reason. Earnest money is fully refundable during the option
period.

### Title Company
Closing will occur through {title_block}, unless seller designates an alternate
{state}-licensed title company. Earnest money is wired to the named title company at
contract execution. Assignment fees flow through the closing statement, not direct.

### State Disclosure (Pre-Assignment Standalone)
A standalone written disclosure satisfying {state} statutory requirements ({state_disclosure_required})
will be delivered to seller AND any end-buyer/assignee prior to assignment, separate from this
purchase contract. Receipt is acknowledged via Documenso (or equivalent) audit certificate.
This contract is contingent on delivery and acknowledgement of that standalone disclosure.

### And-or-Assigns Clause
Buyer may assign this contract, in whole or in part, to any third party before closing.
The buyer-side disclosure will accompany any assignment notice delivered to the assignee.

### Disclosure Statute Reference
{state_statute_block}

### Wholesale Legal Status
Per `state_gates.json`: {cfg.get('wholesale_legal_status', 'unknown')}. Closing model:
{closing_type}. Statutory disclosure required: {sb_required}.

### Timeline Language Guardrail (DTPA-adjacent)
Any close date stated in this contract or related communications is a target date, subject
to title clearance, lien resolution, the option period, and satisfaction of all closing
conditions. No party guarantees a specific close date.

---

**Effective Date:** _________________________
**Seller Signature:** _________________________ Date: _____________
**Buyer (Marquise Smith / Everlight Ventures):** _________________________ Date: _____________

**Generated:** {pt_now_iso()} by state_offer_workflow.py for state={state}
"""
    return addendum


def generate_state_psa(deal: dict, mao: dict) -> str:
    base = (CONTRACTS_DIR / "ASSIGNMENT_CONTRACT_BASE.md").read_text()
    today = pt_now_human().split(" ")[0]
    state = deal.get("state", "").upper()

    replacements = {
        "[DATE]": today,
        "[PROPERTY_ADDRESS]": deal.get("address", "[ADDRESS]"),
        "[COUNTY]": deal.get("county", "[COUNTY]"),
        "[STATE]": state,
        "[LEGAL_DESCRIPTION]": deal.get("legal_description", "[See deed records]"),
        "[ASSIGNOR_ADDRESS]": "[Sacramento, CA mailing address on file]",
        "[PURCHASE_PRICE]": f"${mao.get('offer_to_seller', 0):,.0f}",
        "[ASSIGNMENT_FEE]": f"${mao.get('assignment_fee', 10000):,.0f}",
    }
    out = base
    for placeholder, value in replacements.items():
        out = out.replace(placeholder, value)

    gates = load_state_gates()
    return out + _build_state_addendum(deal, mao, gates)


# ---------------------------------------------------------------------------
# Stage 5 — orchestrate + stage
# ---------------------------------------------------------------------------

def run(deal: dict) -> dict:
    """Run the full state-aware offer workflow and stage artifacts.

    Args:
        deal: dict with required keys deal_id, address, state, seller_name,
              beds, baths, sqft, county. Optional: rehab_estimate, market.

    Returns:
        manifest dict with stage statuses + artifact paths + final verdict
    """
    state = deal.get("state", "").upper()
    if not state:
        return {"status": "rejected", "reason": "missing state"}

    # Stage 0 — state config gate
    active, reason = state_is_active(state)
    if not active:
        return {"status": "rejected", "reason": reason}

    deal_id = deal.get("deal_id") or f"{state.lower()}_{int(datetime.now().timestamp())}"
    deal_dir = MARCUS_QUEUE / deal_id
    deal_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "deal_id": deal_id,
        "started_at": pt_now_iso(),
        "address": deal.get("address"),
        "state": state,
        "stages": {},
        "artifacts": [],
        "verdict": "pending",
    }

    # Stage 1 — comps
    market_code = deal.get("market_code", state)  # e.g., "DAL", "ATL", "MEM"
    log.info(f"[{deal_id}] Stage 1: pulling comps (state={state})")
    comps_result = pull_comps(
        address=deal["address"],
        beds=deal.get("beds", 3),
        baths=deal.get("baths", 2),
        sqft=deal.get("sqft", 1500),
        market_code=market_code,
    )
    manifest["stages"]["comps"] = comps_result
    if comps_result["status"] != "ok":
        manifest["verdict"] = "ESCALATE_TO_MARCUS"
        manifest["escalation_reason"] = comps_result.get("reason")
        _save_manifest(deal_dir, manifest)
        return manifest

    arv = comps_result["arv"]

    # Stage 2 — MAO
    log.info(f"[{deal_id}] Stage 2: calculating MAO (ARV={arv})")
    rehab = deal.get("rehab_estimate", 30_000)
    mao_result = calculate_mao(arv=arv, rehab=rehab, market_code=market_code)
    manifest["stages"]["mao"] = mao_result
    if mao_result["status"] != "ok":
        manifest["verdict"] = "ESCALATE_TO_MARCUS"
        manifest["escalation_reason"] = mao_result.get("reason")
        _save_manifest(deal_dir, manifest)
        return manifest

    mao_result["arv"] = arv

    # Stage 3 — counsel-signed disclosure gate
    counsel_signed = disclosure_counsel_signed(state)
    manifest["stages"]["counsel_gate"] = {
        "state": state,
        "v1_0_disclosure_signed": counsel_signed,
        "blocking": not counsel_signed,
    }

    # Stage 4 — generate offer letter
    log.info(f"[{deal_id}] Stage 4: generating offer letter")
    offer_letter = generate_offer_letter(deal, mao_result)
    offer_path = deal_dir / "01_offer_letter.md"
    offer_path.write_text(offer_letter)
    manifest["artifacts"].append(str(offer_path))

    # Stage 5 — generate state-specific PSA
    log.info(f"[{deal_id}] Stage 5: generating {state} PSA")
    psa = generate_state_psa(deal, mao_result)
    psa_path = deal_dir / "02_state_psa.md"
    psa_path.write_text(psa)
    manifest["artifacts"].append(str(psa_path))

    # Stage 6 — verdict
    if not counsel_signed:
        manifest["verdict"] = "BLOCKED_PENDING_COUNSEL"
        manifest["blocking_reason"] = (
            f"{state}_DISCLOSURE_v1.0 not yet counsel-signed. Artifacts staged for review "
            "but cannot be sent. Bernard countersign + (best-practice) external counsel "
            "sign-off required. See compliance/states/MASTER_STATE_HANDBOOK.md step 7."
        )
    else:
        manifest["verdict"] = "READY_FOR_MARCUS_REVIEW"

    manifest["completed_at"] = pt_now_iso()
    _save_manifest(deal_dir, manifest)
    log.info(f"[{deal_id}] Complete. Verdict: {manifest['verdict']}")
    return manifest


def _save_manifest(deal_dir: Path, manifest: dict) -> None:
    (deal_dir / "00_manifest.json").write_text(json.dumps(manifest, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="State Offer Workflow")
    parser.add_argument("--deal-json", help="Path to a deal JSON file")
    parser.add_argument("--demo", choices=["TX", "TN", "GA", "FL", "MO", "OH", "AZ"], help="Run demo for state")
    parser.add_argument("--check-state", help="Print state_gates active status for a given state")
    args = parser.parse_args()

    if args.check_state:
        active, reason = state_is_active(args.check_state)
        print(json.dumps({"state": args.check_state, "active": active, "reason": reason}, indent=2))
    elif args.demo:
        demo_deals = {
            "TX": {"deal_id": "tx_demo_001", "address": "1234 Oak St, Dallas, TX 75201", "state": "TX",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1500,
                   "county": "Dallas", "market": "dallas", "market_code": "DAL", "rehab_estimate": 35_000},
            "TN": {"deal_id": "tn_demo_001", "address": "5678 Elm St, Memphis, TN 38104", "state": "TN",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1400,
                   "county": "Shelby", "market": "memphis", "market_code": "MEM", "rehab_estimate": 25_000},
            "GA": {"deal_id": "ga_demo_001", "address": "9012 Peachtree, Atlanta, GA 30309", "state": "GA",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1600,
                   "county": "Fulton", "market": "atlanta", "market_code": "ATL", "rehab_estimate": 30_000},
            "FL": {"deal_id": "fl_demo_001", "address": "3456 Beach Dr, Jacksonville, FL 32202", "state": "FL",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1500,
                   "county": "Duval", "market": "jacksonville", "market_code": "JAX", "rehab_estimate": 28_000},
            "MO": {"deal_id": "mo_demo_001", "address": "7890 Forest, St. Louis, MO 63108", "state": "MO",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1450,
                   "county": "St. Louis", "market": "st_louis", "market_code": "STL", "rehab_estimate": 22_000},
            "OH": {"deal_id": "oh_demo_001", "address": "1357 Lake Ave, Cleveland, OH 44102", "state": "OH",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1380,
                   "county": "Cuyahoga", "market": "cleveland", "market_code": "CLE", "rehab_estimate": 35_000},
            "AZ": {"deal_id": "az_demo_001", "address": "2468 Cactus, Phoenix, AZ 85001", "state": "AZ",
                   "seller_name": "Test Seller", "beds": 3, "baths": 2.0, "sqft": 1600,
                   "county": "Maricopa", "market": "phoenix", "market_code": "PHX", "rehab_estimate": 30_000},
        }
        result = run(demo_deals[args.demo])
        print(json.dumps(result, indent=2))
    elif args.deal_json:
        deal = json.loads(Path(args.deal_json).read_text())
        result = run(deal)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
