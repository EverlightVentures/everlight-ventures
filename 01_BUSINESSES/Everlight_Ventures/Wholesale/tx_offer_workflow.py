"""TX Offer Workflow — end-to-end orchestrator for a Texas seller inbound.

Last Updated: 2026-05-05 10:20 PT (2026-05-05T10:20:00-07:00)

Triggered by: a TX seller reply parked in `Wholesale/marcus_queue/<deal_id>.json`.
Marcus review required before any artifact is sent.

Pipeline:
    1. Pull comps via rex_comp_validator (Perplexity-backed)
    2. Calculate ARV from validated comps
    3. Calculate MAO using offer_pricing.max_offer (seventy_rule strategy + DAL multiplier)
    4. Generate offer letter (markdown + Marcus-branded HTML)
    5. Generate TX PSA from ASSIGNMENT_CONTRACT_BASE template with TX-specific clauses
    6. Stage all artifacts at `Wholesale/marcus_queue/<deal_id>/` and return a manifest
    7. Post a Slack alert via branded_slack to #ft-consult with the manifest

This module DOES NOT SEND emails. All outbound is staged for Marcus to review and approve.
Once Marcus approves, the orchestrator hands the seller-side §5.0205 disclosure envelope
to resend_manager.send(agent='marcus', state='TX', ...) — and only after the v1.0 disclosure
clears Bernard countersign + external TX counsel sign-off.

Hard gates (any failure = escalate to Marcus, do not auto-advance):
    - PERPLEXITY_API_KEY missing → escalate (no comps = no offer)
    - Comp confidence LOW → escalate (manual review)
    - MAO < 0 → escalate (deal underwater)
    - State != TX → reject (this is the TX-only orchestrator)
    - v1.0 disclosure not yet counsel-signed → block at offer-letter generation step
      (still generates the artifacts but flags BLOCKED_PENDING_COUNSEL on the manifest)
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
CONTRACTS_DIR = BROKER_OS_DIR / "contracts"

# Module-local paths
THIS_DIR = WHOLESALE_DIR
sys.path.insert(0, str(BROKER_OS_DIR / "wholesale_agent"))
sys.path.insert(0, str(BROKER_OS_DIR / "wholesale_agent" / "wholesale"))

logging.basicConfig(
    level=logging.INFO,
    format="[TX-Offer %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("tx_offer_workflow")


# ---------------------------------------------------------------------------
# Pacific timestamp helper (matches Hive timestamp standard)
# ---------------------------------------------------------------------------

def pt_now_iso() -> str:
    """Pacific time, ISO 8601 with offset. Matches workspace timestamp standard."""
    pacific = timezone(timedelta(hours=-7))  # PDT (May-Oct). Switch to -8 for PST (Nov-Mar).
    return datetime.now(pacific).isoformat(timespec="seconds")


def pt_now_human() -> str:
    """Human-readable Pacific timestamp for embedded copy."""
    pacific = timezone(timedelta(hours=-7))
    return datetime.now(pacific).strftime("%Y-%m-%d %H:%M PT")


# ---------------------------------------------------------------------------
# Stage 1 — pull comps + validate ARV
# ---------------------------------------------------------------------------

def pull_comps(address: str, beds: int, baths: float, sqft: int, market: str = "DAL") -> dict:
    """Pull validated comps and return {arv, confidence, comps[], notes}.

    Wraps rex_comp_validator. Returns empty dict if API key missing — caller
    must escalate to manual.
    """
    try:
        from rex_comp_validator import (
            validate_arv,
        )  # type: ignore
    except ImportError:
        log.error("rex_comp_validator not importable — escalate")
        return {"status": "escalate", "reason": "rex_comp_validator import failed"}

    if not os.environ.get("PERPLEXITY_API_KEY"):
        log.warning("PERPLEXITY_API_KEY missing — escalate")
        return {"status": "escalate", "reason": "PERPLEXITY_API_KEY missing"}

    try:
        result = validate_arv(
            address=address,
            beds=beds,
            baths=baths,
            sqft=sqft,
        )
    except Exception as e:
        log.error(f"validate_arv failed: {e}")
        return {"status": "escalate", "reason": f"validate_arv exception: {e}"}

    if result.get("confidence") not in ("HIGH", "MEDIUM"):
        log.warning(f"Comp confidence LOW for {address} — escalate")
        return {"status": "escalate", "reason": "comp confidence LOW", "raw": result}

    return {
        "status": "ok",
        "arv": result.get("validated_arv"),
        "confidence": result.get("confidence"),
        "comps": result.get("comps", []),
        "notes": result.get("notes", ""),
    }


# ---------------------------------------------------------------------------
# Stage 2 — calculate MAO
# ---------------------------------------------------------------------------

def calculate_mao(
    arv: float,
    rehab: float,
    market: str = "DAL",
    target_fee: float = 10_000.0,
    strategy: str = "seventy_rule",
) -> dict:
    """Calculate Maximum Allowable Offer using offer_pricing.max_offer."""
    try:
        from offer_pricing import max_offer  # type: ignore
    except ImportError:
        log.error("offer_pricing not importable — escalate")
        return {"status": "escalate", "reason": "offer_pricing import failed"}

    try:
        offer = max_offer(
            strategy=strategy,
            arv=arv,
            rehab=rehab,
            market_code=market,
            target_fee=target_fee,
        )
    except Exception as e:
        log.error(f"max_offer failed: {e}")
        return {"status": "escalate", "reason": f"max_offer exception: {e}"}

    if offer.offer_to_seller <= 0:
        log.warning(f"MAO ≤ 0 — deal underwater. ARV={arv}, rehab={rehab}")
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
# Stage 3 — check counsel sign-off on v1.0 disclosure
# ---------------------------------------------------------------------------

def disclosure_counsel_signed() -> bool:
    """Returns True only when v1.0 §5.0205 disclosure has cleared counsel.

    Sentinel file: `compliance/TX_5_0205_DISCLOSURE_v1.0_SIGNED.md` (created by Bernard
    after external TX counsel sign-off). Until it exists, all generated offer letters
    are staged with BLOCKED_PENDING_COUNSEL flag and not eligible to send.
    """
    sentinel = COMPLIANCE_DIR / "TX_5_0205_DISCLOSURE_v1.0_SIGNED.md"
    return sentinel.exists()


# ---------------------------------------------------------------------------
# Stage 4 — generate offer letter (markdown)
# ---------------------------------------------------------------------------

def generate_offer_letter(deal: dict, mao: dict) -> str:
    """Render the offer letter for a TX seller. Marcus persona; §5.0205 footer included."""
    address = deal.get("address", "[ADDRESS]")
    seller_name = deal.get("seller_name", "[SELLER NAME]")
    arv = mao.get("arv", deal.get("arv", 0))
    offer_amount = mao.get("offer_to_seller", 0)

    body = f"""# Offer for {address}

Dear {seller_name},

Thank you for replying. I'm Marcus Cole with Everlight Ventures. We received your message
about the property at {address} and I've put together an initial cash offer.

**Offer details:**
- Property: {address}
- Estimated after-repair value (ARV): ${arv:,.0f}
- **Our cash offer: ${offer_amount:,.0f}**
- Earnest money: $1,000 to a Texas-licensed title company
- Closing: 14-21 days through 1st Option Title, Garland TX (or seller's preferred TX-licensed title company)
- Option period: 10 days standard TREC

**How we close:** Everlight Ventures or our assignee will purchase. Our purchase contract
will include a "and/or assigns" provision so we can bring in a partner-buyer if it shortens
your timeline. Earnest money is fully refundable through your option period.

This is an initial offer based on comparable sales near your property. If you have rehab
estimates, recent improvements, or pictures that would change the math, send them my way
and I will revisit.

Two next steps if this works for you:

1. Reply with a good time for a 10-minute call to confirm details.
2. I will send the purchase contract via DocuSign for your review. No obligation to sign.

If the number is too low, tell me what you need and I will see if we can structure
something that works for both sides.

Best,
Marcus Cole
Operations, Everlight Ventures
marcus@everlightventures.io
[Sacramento, CA mailing address on file]

---

**Required by Texas Property Code Section 5.0205:** Everlight Ventures or its assignee
intends to purchase this property and may assign the purchase contract to a third party
before closing. A standalone written Section 5.0205 disclosure will be delivered to seller
and end buyer prior to assignment. Everlight Ventures is a real estate investor, not a
licensed Texas broker.

To stop receiving messages from us, reply STOP and we will remove your contact immediately.
"""
    return body


# ---------------------------------------------------------------------------
# Stage 5 — generate TX PSA from base template
# ---------------------------------------------------------------------------

def generate_tx_psa(deal: dict, mao: dict) -> str:
    """Generate a TX-specific PSA by pre-filling the base assignment contract."""
    base = (CONTRACTS_DIR / "ASSIGNMENT_CONTRACT_BASE.md").read_text()

    # Field replacements
    today = pt_now_human().split(" ")[0]
    replacements = {
        "[DATE]": today,
        "[PROPERTY_ADDRESS]": deal.get("address", "[ADDRESS]"),
        "[COUNTY]": deal.get("county", "[COUNTY]"),
        "[STATE]": "Texas",
        "[LEGAL_DESCRIPTION]": deal.get("legal_description", "[See deed records]"),
        "[ASSIGNOR_ADDRESS]": "[Sacramento, CA mailing address on file]",
        "[PURCHASE_PRICE]": f"${mao.get('offer_to_seller', 0):,.0f}",
        "[ASSIGNMENT_FEE]": f"${mao.get('assignment_fee', 10000):,.0f}",
    }

    out = base
    for placeholder, value in replacements.items():
        out = out.replace(placeholder, value)

    # TX-specific clauses appended
    tx_clauses = f"""

---

## TX-SPECIFIC ADDENDUM

### Option Period (TREC paragraph 23 default)
Buyer's option period is **10 days** from the effective date, with an option fee of $200
non-refundable paid directly to seller. During the option period, buyer may terminate the
contract for any reason. Earnest money is fully refundable during the option period.

### Title Company (TX Insurance Code Chapter 2651)
Closing will occur through **1st Option Title**, 1795 Northwest Hwy, Garland TX 75041
(972-271-1700), unless seller designates an alternate Texas-licensed title company under
Insurance Code Chapter 2651. Earnest money is wired to the named title company at contract
execution. Assignment fees flow through the closing statement, not direct.

### Section 5.0205 Disclosure (Standalone)
A standalone written disclosure satisfying Texas Property Code Section 5.0205 will be
delivered to seller AND any end-buyer/assignee prior to assignment, separate from this
purchase contract. Receipt is acknowledged via DocuSign (or equivalent) audit certificate.
This contract is contingent on delivery and acknowledgement of that standalone disclosure.

### And-or-Assigns Clause
Buyer may assign this contract, in whole or in part, to any third party before closing.
The buyer-side §5.0205 disclosure will accompany any assignment notice delivered to the
assignee.

### Property Code Section 5.008 (Seller's Disclosure of Property Condition)
Seller shall deliver to buyer the Seller's Disclosure of Property Condition (TREC OP-H or
equivalent) within 7 days of contract execution, unless seller is exempt under §5.008(e).
On assignment, buyer will pass the SDN through to the end-buyer/assignee.

### DTPA-Adjacent Timeline Language
Any close date stated in this contract or related communications is a target date, subject
to title clearance, lien resolution, the option period, and satisfaction of all closing
conditions. No party guarantees a specific close date.

---

**Effective Date:** _________________________
**Seller Signature:** _________________________ Date: _____________
**Buyer (Marquise Smith / Everlight Ventures):** _________________________ Date: _____________

**Generated:** {pt_now_iso()} by tx_offer_workflow.py
"""
    return out + tx_clauses


# ---------------------------------------------------------------------------
# Stage 6 — orchestrate + stage
# ---------------------------------------------------------------------------

def run(deal: dict) -> dict:
    """Run the full TX offer workflow and stage artifacts. Returns a manifest.

    Args:
        deal: dict with required keys:
            - deal_id (str)
            - address (str)
            - state (str, must be 'TX')
            - seller_name (str)
            - beds (int), baths (float), sqft (int)
            - county (str)
            Optional:
            - rehab_estimate (float, default 30000)
            - legal_description (str)
            - market (str, default 'DAL')

    Returns:
        manifest dict with stage statuses + artifact paths + final verdict
    """
    if deal.get("state", "").upper() != "TX":
        return {"status": "rejected", "reason": "not a TX deal"}

    deal_id = deal.get("deal_id") or f"tx_{int(datetime.now().timestamp())}"
    deal_dir = MARCUS_QUEUE / deal_id
    deal_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "deal_id": deal_id,
        "started_at": pt_now_iso(),
        "address": deal.get("address"),
        "state": "TX",
        "stages": {},
        "artifacts": [],
        "verdict": "pending",
    }

    # Stage 1 — comps
    log.info(f"[{deal_id}] Stage 1: pulling comps")
    comps_result = pull_comps(
        address=deal["address"],
        beds=deal.get("beds", 3),
        baths=deal.get("baths", 2),
        sqft=deal.get("sqft", 1500),
        market=deal.get("market", "DAL"),
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
    mao_result = calculate_mao(
        arv=arv,
        rehab=rehab,
        market=deal.get("market", "DAL"),
    )
    manifest["stages"]["mao"] = mao_result
    if mao_result["status"] != "ok":
        manifest["verdict"] = "ESCALATE_TO_MARCUS"
        manifest["escalation_reason"] = mao_result.get("reason")
        _save_manifest(deal_dir, manifest)
        return manifest

    mao_result["arv"] = arv  # for offer letter

    # Stage 3 — counsel gate check
    counsel_signed = disclosure_counsel_signed()
    manifest["stages"]["counsel_gate"] = {
        "v1_0_disclosure_signed": counsel_signed,
        "blocking": not counsel_signed,
    }

    # Stage 4 — generate offer letter
    log.info(f"[{deal_id}] Stage 4: generating offer letter")
    offer_letter = generate_offer_letter(deal, mao_result)
    offer_path = deal_dir / "01_offer_letter.md"
    offer_path.write_text(offer_letter)
    manifest["artifacts"].append(str(offer_path))

    # Stage 5 — generate PSA
    log.info(f"[{deal_id}] Stage 5: generating TX PSA")
    psa = generate_tx_psa(deal, mao_result)
    psa_path = deal_dir / "02_tx_psa.md"
    psa_path.write_text(psa)
    manifest["artifacts"].append(str(psa_path))

    # Stage 6 — verdict
    if not counsel_signed:
        manifest["verdict"] = "BLOCKED_PENDING_COUNSEL"
        manifest["blocking_reason"] = (
            "TX_5_0205_DISCLOSURE_v1.0 not yet counsel-signed. Artifacts staged for review "
            "but cannot be sent. Bernard countersign + external TX counsel sign-off required."
        )
    else:
        manifest["verdict"] = "READY_FOR_MARCUS_REVIEW"

    manifest["completed_at"] = pt_now_iso()
    _save_manifest(deal_dir, manifest)
    log.info(f"[{deal_id}] Complete. Verdict: {manifest['verdict']}")
    return manifest


def _save_manifest(deal_dir: Path, manifest: dict) -> None:
    """Save manifest as JSON at the top of the deal dir."""
    (deal_dir / "00_manifest.json").write_text(json.dumps(manifest, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TX Offer Workflow")
    parser.add_argument("--deal-json", help="Path to a deal JSON file")
    parser.add_argument("--demo", action="store_true", help="Run with a Dallas demo deal")
    args = parser.parse_args()

    if args.demo:
        deal = {
            "deal_id": "tx_demo_dallas_001",
            "address": "1234 Oak St, Dallas, TX 75201",
            "state": "TX",
            "seller_name": "Test Seller",
            "beds": 3,
            "baths": 2.0,
            "sqft": 1500,
            "county": "Dallas",
            "market": "DAL",
            "rehab_estimate": 35_000,
        }
        result = run(deal)
        print(json.dumps(result, indent=2))
    elif args.deal_json:
        deal = json.loads(Path(args.deal_json).read_text())
        result = run(deal)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
