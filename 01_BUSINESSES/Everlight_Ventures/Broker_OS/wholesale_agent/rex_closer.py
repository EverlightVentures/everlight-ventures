"""
Rex Closer -- the deal machine.

When a seller replies interested, Rex:
1. Sends qualifying questions (timeline, mortgage, condition)
2. Validates ARV against real comps (rex_comp_validator)
3. Gets itemized repair estimate (rex_repair_estimator)
4. Calculates offer using validated ARV and real repair numbers
5. Sends the offer with 7-day close promise
6. If seller agrees, generates purchase agreement, saves deal, blasts buyers
7. Posts to Slack on every stage transition

This is the script that turns conversations into assignment fees.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Closer %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_closer")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
DEALS_DIR = AGENT_DIR / "active_deals"
CONTRACTS_DIR = AGENT_DIR / "contracts"
DEALS_DIR.mkdir(parents=True, exist_ok=True)
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "Harrison Knox <hammer@everlightventures.io>")
REPLY_TO = "hammer@everlightventures.io"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

# Contract generation + Stripe invoicing
try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from contract_generator import generate_wholesale_contract, generate_finder_agreement
except ImportError:
    generate_wholesale_contract = None
    generate_finder_agreement = None

try:
    from stripe_invoicer import invoice_deal as stripe_invoice_deal
except ImportError:
    stripe_invoice_deal = None

NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")

# Load title companies for market-specific closings
TITLE_COMPANIES_FILE = AGENT_DIR / "title_companies.json"


def _load_title_companies() -> dict:
    if TITLE_COMPANIES_FILE.exists():
        try:
            return json.loads(TITLE_COMPANIES_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# ---------------------------------------------------------------------------
# EMAIL / SLACK HELPERS
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str, *, state: str = "") -> bool:
    """Delegates to rex_utils.safe_send_email (canonical branded_mailer pipeline).

    Migrated 2026-05-15 after Streubel 2nd-strike. The old body POSTed
    directly to api.resend.com and bypassed render_report. safe_send_email
    routes through branded_mailer which wraps content_html in the gold
    template, re-checks eradication_gate / resend_guard / resend_budget /
    weekly_cadence / phrase_scrub, then sends.
    """
    try:
        from rex_utils import safe_send_email
    except ImportError:
        return False
    _agent_name = globals().get("AGENT_NAME", "Piper Reeves")
    _agent_email = globals().get("AGENT_EMAIL", globals().get("FROM_EMAIL", "piper@everlightventures.io"))
    _agent_title = globals().get("AGENT_TITLE", "Senior Account Executive, Wholesale")
    # FROM_EMAIL may be "Name <addr@x.com>" -- extract addr if so.
    import re as _re
    _m = _re.search(r"<([^>]+)>", _agent_email or "")
    if _m:
        _agent_email = _m.group(1)
    return safe_send_email(
        to, subject, body,
        state=state, action=action,
        agent_name=_agent_name,
        agent_email=_agent_email,
        agent_title=_agent_title,
    )


def _split_from(from_line: str) -> tuple:
    """Parse 'Name <email@x.com>' -> ('Name', 'email@x.com'). Falls back to ('Everlight Ventures', from_line) for bare addresses."""
    import re
    m = re.match(r'^\s*"?([^"<]+?)"?\s*<([^>]+)>\s*$', from_line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "Everlight Ventures", from_line.strip()


def post_slack(text: str, title: str = "Rex Closer Update"):
    """Post to Slack, creating a GDoc first when possible."""
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title=title,
                content=text,
                folder="01_Broker_OS/Deal_Pipeline",
                summary=text[:200],
                agent="harrison_knox",
            )
            if result.get("ok"):
                return
        except Exception:
            pass
    # Fallback: raw text post
    if not SLACK_TOKEN:
        log.info(f"[Slack offline] {text[:300]}")
        return
    import requests
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"channel": SLACK_CHANNEL, "text": text},
            timeout=10,
        )
    except Exception as e:
        log.error(f"Slack post failed: {e}")


# ---------------------------------------------------------------------------
# DEAL STATE
# ---------------------------------------------------------------------------

def load_deal(address_slug: str) -> Optional[dict]:
    path = DEALS_DIR / f"{address_slug}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_deal(deal: dict):
    slug = deal.get("address_slug", "unknown")
    path = DEALS_DIR / f"{slug}.json"
    deal["updated_at"] = NOW.isoformat()
    path.write_text(json.dumps(deal, indent=2, default=str))


def make_slug(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", address.lower()).strip("_")[:80]


# ---------------------------------------------------------------------------
# STEP 1: QUALIFY -- send qualifying questions
# ---------------------------------------------------------------------------

QUALIFYING_MSG = (
    "Great to hear from you! A few quick questions so I can put "
    "together the best possible offer:\n\n"
    "1. What's your ideal timeline to sell?\n"
    "2. Is there a mortgage balance or any liens on the property?\n"
    "3. What condition would you say the property is in (1-10)?\n"
    "4. What would you do with the cash from the sale?\n"
    "5. Have you explored other options like listing with an agent?\n\n"
    "Reply and I'll have a cash offer for you within the hour."
)


def send_qualifying_questions(lead: dict) -> bool:
    """Send qualifying questions when seller shows interest."""
    email = lead.get("owner_email", "")
    addr = lead.get("address", "your property")
    first = lead.get("owner_name", "").split()[0] if lead.get("owner_name") else "there"

    subject = f"Re: Cash offer for {addr}"
    body = f"Hi {first},\n\n{QUALIFYING_MSG}\n\nRich\nEverlight Ventures"

    if send_email(email, subject, body):
        # Create or update deal file
        slug = make_slug(addr)
        deal = load_deal(slug) or {
            "address": addr,
            "address_slug": slug,
            "city": lead.get("city", ""),
            "state": lead.get("state", ""),
            "zip_code": lead.get("zip_code", ""),
            "market": lead.get("market", ""),
            "owner_name": lead.get("owner_name", ""),
            "owner_email": email,
            "owner_phone": lead.get("owner_phone", ""),
            "estimated_arv": lead.get("estimated_arv", 0),
            "lead_type": lead.get("lead_type", ""),
            "created_at": NOW.isoformat(),
            "conversation": [],
        }
        deal["stage"] = "qualifying"
        deal["qualifying_sent_at"] = NOW.isoformat()
        deal["conversation"].append({
            "role": "rex",
            "message": QUALIFYING_MSG,
            "timestamp": NOW.isoformat(),
        })
        save_deal(deal)

        post_slack(
            f"*INTERESTED SELLER* -- qualifying questions sent\n"
            f"Property: {addr}\n"
            f"Owner: {lead.get('owner_name', '?')} ({email})"
        )
        log.info(f"Qualifying questions sent for {addr}")
        return True
    return False


# ---------------------------------------------------------------------------
# STEP 2: CALCULATE OFFER
# ---------------------------------------------------------------------------

def calculate_offer(
    arv: float,
    condition_score: int,
    address: str = "",
    city: str = "",
    state: str = "",
    beds: int = 3,
    baths: float = 2.0,
    sqft: int = 1500,
    year_built: int = 1990,
    property_type: str = "residential",
) -> dict:
    """
    Calculate offer using comp-validated ARV and itemized repairs.

    1. Validates ATTOM ARV against real sold comps
    2. If confidence is LOW, returns a skip result
    3. Gets itemized repair estimate via Perplexity
    4. Checks for tear-down and uses 10520 rule if applicable
    5. Uses the 65% rule on validated ARV minus real repairs

    Falls back to crude estimates if comp/repair modules are unavailable.
    """
    # --- Step 1: Validate ARV against comps ---
    comp_result = None
    validated_arv = arv

    try:
        from rex_comp_validator import validate_arv, calculate_mao, is_tear_down

        if address and city and state:
            comp_result = validate_arv(
                address, city, state, arv, beds, baths, sqft
            )
            validated_arv = comp_result.get("validated_arv", arv)

            # If confidence is LOW, don't make an offer
            if not comp_result.get("should_proceed", True):
                log.warning(
                    f"LOW confidence for {address} -- "
                    f"ATTOM=${arv:,.0f} vs comps=${validated_arv:,.0f} "
                    f"({comp_result.get('deviation_pct', 0):.1f}% off)"
                )
                return {
                    "offer": 0,
                    "skip": True,
                    "skip_reason": (
                        "Comp validation returned LOW confidence -- "
                        "need more research before making an offer"
                    ),
                    "arv": arv,
                    "validated_arv": validated_arv,
                    "comp_result": comp_result,
                    "condition_score": condition_score,
                }
    except ImportError:
        log.warning("rex_comp_validator not available -- using raw ATTOM ARV")

    # --- Step 2: Check for tear-down ---
    teardown = False
    try:
        from rex_comp_validator import is_tear_down
        teardown = is_tear_down(year_built, sqft, validated_arv)
    except ImportError:
        pass

    if teardown:
        property_type = "teardown"

    # --- Step 3: Get itemized repair estimate ---
    repair_result = None
    repair_total = 0

    try:
        from rex_repair_estimator import estimate_repairs

        if address and city and state:
            repair_result = estimate_repairs(
                address, city, state, sqft, year_built, condition_score
            )
            repair_total = repair_result.get("total", 0)
    except ImportError:
        log.warning("rex_repair_estimator not available -- using crude estimate")

    # --- Step 4: Calculate MAO ---
    try:
        from rex_comp_validator import calculate_mao

        mao_result = calculate_mao(
            validated_arv=validated_arv,
            condition_score=condition_score,
            property_type=property_type,
            repair_estimate=repair_total,
            year_built=year_built,
            sqft=sqft,
        )
    except ImportError:
        # Fallback to simple calculation
        if repair_total <= 0:
            if condition_score <= 3:
                repair_total = 40_000
            elif condition_score <= 6:
                repair_total = 25_000
            else:
                repair_total = 10_000

        offer = (validated_arv * 0.65) - repair_total
        offer = max(offer, 0)
        offer = round(offer / 500) * 500

        assignment_fee = max(8_000, int(validated_arv * 0.05))
        assignment_fee = round(assignment_fee / 500) * 500
        buyer_price = offer + assignment_fee
        buyer_profit = validated_arv - buyer_price - repair_total

        mao_result = {
            "offer": offer,
            "repairs": round(repair_total),
            "assignment_fee": assignment_fee,
            "buyer_price": buyer_price,
            "buyer_profit": round(buyer_profit),
            "arv": round(validated_arv),
            "condition_score": condition_score,
            "property_type": property_type,
            "method": "fallback_65_percent",
        }

    # Attach validation metadata
    mao_result["attom_arv"] = arv
    mao_result["validated_arv"] = round(validated_arv)
    if comp_result:
        mao_result["comp_confidence"] = comp_result.get("confidence", "UNKNOWN")
        mao_result["comp_count"] = comp_result.get("comp_count", 0)
        mao_result["comp_deviation_pct"] = comp_result.get("deviation_pct", 0)
    if repair_result:
        mao_result["repair_items"] = repair_result.get("items", {})
        mao_result["repair_method"] = repair_result.get("method", "unknown")
        mao_result["repair_per_sqft"] = repair_result.get("per_sqft", 0)

    return mao_result


# ---------------------------------------------------------------------------
# STEP 3: SEND OFFER
# ---------------------------------------------------------------------------

def send_offer(deal: dict, offer_details: dict) -> bool:
    """Send the cash offer to the seller."""
    email = deal.get("owner_email", "")
    addr = deal.get("address", "")
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    offer_amt = offer_details["offer"]

    subject = f"Your cash offer for {addr}"
    body = (
        f"Hi {first},\n\n"
        f"Based on the property details, I can offer ${offer_amt:,.0f} "
        f"and close in 7 days.\n\n"
        f"No inspections, no agent fees, no repairs needed. I handle everything.\n\n"
        f"If that works, I'll send over the purchase agreement right now "
        f"for your e-signature.\n\n"
        f"Just reply YES and I'll send it over.\n\n"
        f"Harrison Knox\n"
        f"Everlight Ventures\n"
        f"hammer@everlightventures.io"
    )

    if send_email(email, subject, body):
        deal["stage"] = "offer_sent"
        deal["offer"] = offer_amt
        deal["offer_details"] = offer_details
        deal["offer_sent_at"] = NOW.isoformat()
        deal["conversation"].append({
            "role": "rex",
            "message": f"Offer: ${offer_amt:,.0f}",
            "timestamp": NOW.isoformat(),
        })
        save_deal(deal)

        post_slack(
            f"*OFFER SENT*\n"
            f"Property: {addr}\n"
            f"Offer: ${offer_amt:,.0f}\n"
            f"ARV: ${offer_details['arv']:,.0f}\n"
            f"Repairs: ${offer_details['repairs']:,.0f}\n"
            f"Assignment fee: included in purchase price"
        )
        log.info(f"Offer ${offer_amt:,.0f} sent for {addr}")
        return True
    return False


# ---------------------------------------------------------------------------
# STEP 4: SELLER ACCEPTS -- contract + buyer blast
# ---------------------------------------------------------------------------

def generate_purchase_agreement(deal: dict) -> str:
    """Generate a plain-text purchase agreement with all fields filled."""
    addr = deal.get("address", "")
    city = deal.get("city", "")
    state = deal.get("state", "")
    owner = deal.get("owner_name", "")
    offer = deal.get("offer", 0)
    today_str = NOW.strftime("%B %d, %Y")

    agreement = f"""REAL ESTATE PURCHASE AGREEMENT

Date: {today_str}

SELLER: {owner}
BUYER: Everlight Logistics LLC (and/or assigns)

PROPERTY ADDRESS: {addr}, {city}, {state}

PURCHASE PRICE: ${offer:,.0f}

TERMS AND CONDITIONS:

1. PURCHASE PRICE: Buyer agrees to purchase the above property for
   ${offer:,.0f} (USD), payable at closing via certified funds or wire transfer.

2. EARNEST MONEY DEPOSIT: Buyer shall deposit $1,000 with the designated
   title company within 3 business days of mutual execution.

3. CLOSING DATE: Closing shall occur within 7 calendar days of mutual
   execution of this agreement, or sooner if mutually agreed.

4. TITLE: Seller shall convey marketable and insurable title to Buyer
   via warranty deed, free and clear of all liens and encumbrances except
   those accepted by Buyer in writing.

5. CONDITION: Property is sold AS-IS. Buyer waives all inspections.
   No repairs or credits are required from Seller.

6. ASSIGNMENT: Buyer reserves the right to assign this contract to a
   third party prior to closing. Seller acknowledges and agrees that
   Buyer may assign this agreement.

7. CLOSING COSTS: Each party pays their own customary closing costs.
   Seller pays for title insurance. Buyer pays for recording fees.

8. DEFAULT: If Buyer defaults, Seller's sole remedy is retention of
   the earnest money deposit. If Seller defaults, Buyer may seek
   specific performance or return of earnest money.

9. ENTIRE AGREEMENT: This document constitutes the entire agreement
   between the parties. No oral agreements are binding.

SELLER SIGNATURE: _________________________ Date: _________
{owner}

BUYER SIGNATURE: _________________________ Date: _________
Everlight Logistics LLC

---
This agreement was prepared by Everlight Ventures for review purposes.
Both parties are advised to consult with legal counsel before signing.
Contact: hammer@everlightventures.io
"""
    return agreement


_CITY_TO_STATE = {
    "atlanta": "GA", "augusta": "GA", "savannah": "GA", "macon": "GA",
    "dallas": "TX", "houston": "TX", "san_antonio": "TX", "fort_worth": "TX", "austin": "TX",
    "jacksonville": "FL", "orlando": "FL", "tampa": "FL", "miami": "FL",
    "charlotte": "NC", "raleigh": "NC",
    "st_louis": "MO", "saint_louis": "MO", "kansas_city": "MO",
    "phoenix": "AZ", "tucson": "AZ", "mesa": "AZ",
    "memphis": "TN", "nashville": "TN", "knoxville": "TN",
}


def _companies_from_entry(entry) -> list[dict]:
    """Normalize a title_companies.json state entry into a ranked list.

    Handles two shapes:
      (a) {"market":..., "companies":[{...},{...}]}     -- current
      (b) [{...}, {...}]                                 -- legacy
    """
    if isinstance(entry, dict) and isinstance(entry.get("companies"), list):
        cos = entry["companies"]
    elif isinstance(entry, list):
        cos = entry
    else:
        return []
    return sorted(cos, key=lambda c: (0 if c.get("primary") else 1, c.get("rank", 999)))


def get_title_companies_ranked(market_or_state: str) -> list[dict]:
    """Return the full ranked list of title companies for a market/state.

    Caller iterates this list -- try rank 1, then 2, 3... until one accepts.
    Each row includes .name, .phone, .email, .website, .rank, .primary (True/False),
    .handles_assignments, .investor_friendly, .notes.
    """
    companies = _load_title_companies()
    key = (market_or_state or "").strip()
    # 2-letter state code? take directly
    if len(key) == 2 and key.upper() in companies:
        return _companies_from_entry(companies[key.upper()])
    k_lower = key.lower().replace(" ", "_").replace(".", "")
    # City -> state lookup
    st = _CITY_TO_STATE.get(k_lower)
    if st and st in companies:
        return _companies_from_entry(companies[st])
    # Legacy: market_key as-is (old city-level keys)
    if k_lower in companies:
        return _companies_from_entry(companies[k_lower])
    # Fallback: national_backup list
    return _companies_from_entry(companies.get("national_backup", []))


def get_title_company(market_or_state: str) -> dict:
    """Return the primary (rank 1) title company for a market/state.

    Kept for backwards compatibility with existing callers. New code should
    call get_title_companies_ranked() and iterate with fallback logic.
    """
    ranked = get_title_companies_ranked(market_or_state)
    if ranked:
        # Prefer primary=y, else rank 1
        for c in ranked:
            if str(c.get("primary", "")).lower() in ("y", "yes", "true", "1"):
                return c
        return ranked[0]
    return {"name": "TBD", "phone": "", "email": ""}


def try_title_companies_with_fallback(market_or_state: str, address: str,
                                       attempt_fn) -> tuple[bool, dict, list[dict]]:
    """Iterate ranked title companies; call attempt_fn(company) until one accepts.

    attempt_fn(company) -> True if that company took the closing, else False.
    Returns (success, accepted_company_or_empty, tried_log[]).
    Logs each attempt with the decline reason so the closer can re-rank later.
    """
    ranked = get_title_companies_ranked(market_or_state)
    tried: list[dict] = []
    for c in ranked:
        log.info("title attempt: rank=%s %s for %s", c.get("rank","?"), c.get("name","?"), address)
        ok = False
        try:
            ok = bool(attempt_fn(c))
        except Exception as e:
            tried.append({"company": c.get("name"), "ok": False, "error": str(e)[:120]})
            continue
        tried.append({"company": c.get("name"), "ok": ok})
        if ok:
            return True, c, tried
    return False, {}, tried


def generate_deal_sheet(deal: dict) -> str:
    """Generate the buyer deal sheet -- this is what gets blasted to investors."""
    addr = deal.get("address", "")
    city = deal.get("city", "")
    state = deal.get("state", "")
    details = deal.get("offer_details", {})
    arv = details.get("arv", 0)
    repairs = details.get("repairs", 0)
    assignment_fee = details.get("assignment_fee", 0)
    contract_price = deal.get("offer", 0)
    buyer_price = contract_price + assignment_fee
    buyer_profit = arv - buyer_price - repairs

    market = deal.get("market", city.lower())
    title_co = get_title_company(market)
    title_info = f"{title_co.get('name', 'TBD')}"
    if title_co.get("phone"):
        title_info += f" | {title_co['phone']}"
    if title_co.get("email"):
        title_info += f" | {title_co['email']}"

    # Build repair breakdown if itemized data is available
    repair_breakdown = ""
    repair_items = details.get("repair_items", {})
    if repair_items:
        repair_breakdown = "\nREPAIR BREAKDOWN:\n"
        for cat, cost in sorted(repair_items.items()):
            if cost > 0:
                cat_label = cat.replace("_", " ").title()
                repair_breakdown += f"  {cat_label}: ${cost:,.0f}\n"

    comp_note = ""
    comp_confidence = details.get("comp_confidence", "")
    if comp_confidence:
        comp_note = f"\n  Comp Confidence: {comp_confidence}"

    prop_type = details.get("property_type", "residential")
    method_note = ""
    if prop_type == "teardown":
        method_note = "\n  NOTE: Tear-down / rebuild opportunity (10520 rule)"

    sheet = f"""PRIVATE DEAL ALERT -- ASSIGNMENT OPPORTUNITY

Property: {addr}, {city}, {state}
Contract Price: ${contract_price:,.0f}
Your Purchase Price: ${buyer_price:,.0f} (total purchase price)

NUMBERS:
  ARV (After Repair Value): ${arv:,.0f}
  Estimated Repairs: ${repairs:,.0f}
  Your All-In Cost: ${buyer_price + repairs:,.0f}
  YOUR PROFIT POTENTIAL: ${buyer_profit:,.0f}{comp_note}{method_note}
{repair_breakdown}
DETAILS:
  - Property under contract, ready to assign
  - Close in 7 days through title company
  - Sold AS-IS, no contingencies
  - Clear title confirmed

FIRST BUYER TO WIRE $5,000 EMD GETS IT.
Reply INTERESTED to lock this deal.

Title Company: {title_info}

---
Everlight Ventures -- Acquisitions
hammer@everlightventures.io
everlightventures.io/wholesale
"""
    return sheet


def blast_deal_to_buyers(deal: dict) -> int:
    """Email the deal sheet to all buyers in buyers_db.json + Supabase."""
    deal_sheet = generate_deal_sheet(deal)
    addr = deal.get("address", "")
    city = deal.get("city", "")
    state = deal.get("state", "")
    buyer_price = deal.get("offer", 0) + deal.get("offer_details", {}).get("assignment_fee", 0)

    subject = f"DEAL ALERT: {addr}, {city} {state} -- ${buyer_price:,.0f}"
    sent = 0

    # 1. Local buyers_db.json
    buyers_db = AGENT_DIR / "buyers_db.json"
    if buyers_db.exists():
        try:
            buyers = json.loads(buyers_db.read_text())
            for buyer in buyers:
                if not buyer.get("email"):
                    continue
                # Match by market if buyer has preferences
                buyer_markets = buyer.get("markets", [])
                if buyer_markets:
                    deal_market = f"{city}, {state}".lower()
                    match = any(
                        m.lower() in deal_market or deal_market in m.lower()
                        for m in buyer_markets
                    )
                    if not match:
                        continue
                if send_email(buyer["email"], subject, deal_sheet):
                    sent += 1
                    time.sleep(1)
        except Exception as e:
            log.error(f"Local buyer blast error: {e}")

    # 2. Supabase investor_buyers
    try:
        import requests
        supa_url = os.environ.get(
            "SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co"
        )
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if supa_key:
            resp = requests.get(
                f"{supa_url}/rest/v1/investor_buyers?is_active=eq.true&select=*",
                headers={
                    "apikey": supa_key,
                    "Authorization": f"Bearer {supa_key}",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                for buyer in resp.json():
                    email = buyer.get("email", "")
                    if email and send_email(email, subject, deal_sheet):
                        sent += 1
                        time.sleep(1)
    except Exception as e:
        log.error(f"Supabase buyer blast error: {e}")

    return sent


def process_seller_acceptance(deal: dict) -> bool:
    """Seller said YES -- generate contract, save deal, blast buyers."""
    addr = deal.get("address", "")
    email = deal.get("owner_email", "")
    slug = deal.get("address_slug", make_slug(addr))

    # Generate and save purchase agreement (PDF if available, text fallback)
    pdf_path = None
    if generate_wholesale_contract:
        try:
            pdf_path = generate_wholesale_contract({
                "property_address": addr,
                "seller_name": deal.get("owner_name", ""),
                "seller_email": deal.get("owner_email", ""),
                "buyer_name": "TBD (Assignment)",
                "buyer_email": "",
                "purchase_price": deal.get("offer", 0),
                "assignment_fee": deal.get("assignment_fee", deal.get("offer", 0) * 0.10),
                "earnest_money": min(1000, deal.get("offer", 0) * 0.01),
                "closing_date": deal.get("close_date", "Within 14 days"),
                "title_company": deal.get("title_company", "TBD"),
                "inspection_days": 14,
            })
            log.info(f"PDF contract generated: {pdf_path}")
        except Exception as e:
            log.warning(f"PDF contract generation failed, using text fallback: {e}")

    agreement = generate_purchase_agreement(deal)
    contract_path = CONTRACTS_DIR / f"{slug}_purchase_agreement.txt"
    contract_path.write_text(agreement)

    # Email contract to seller
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    subject = f"Purchase Agreement for {addr}"
    body = (
        f"Hi {first},\n\n"
        f"Here is the purchase agreement for {addr} at ${deal.get('offer', 0):,.0f}.\n\n"
        f"Please review and sign where indicated. If you have any questions, "
        f"just reply to this email.\n\n"
        f"Once signed, we will open escrow with the title company "
        f"and you will have your cash within 7 days.\n\n"
        f"Harrison Knox\n"
        f"Everlight Ventures\n\n"
        f"---\n\n"
        f"{agreement}"
    )
    # COUNTERMEASURE: Pre-qualify buyers BEFORE sending contract to seller
    # Never put a property under contract without a buyer already lined up
    try:
        from rex_buyer_segmenter import match_buyers_to_deal, get_priority_buyers
        matched = get_priority_buyers(deal, top_n=10)
        buyer_count_available = len(matched)
    except ImportError:
        buyers_db = AGENT_DIR / "buyers_db.json"
        all_buyers = json.loads(buyers_db.read_text()) if buyers_db.exists() else []
        market = deal.get("market", deal.get("city", "")).lower()
        matched = [b for b in all_buyers if market in b.get("city", "").lower() or market in b.get("market", "").lower()]
        buyer_count_available = len(matched)

    if buyer_count_available < 2:
        # NOT ENOUGH BUYERS -- don't sign contract, find buyers first
        log.warning(f"HOLD: Only {buyer_count_available} buyers for {addr}. Need at least 2 before contracting.")
        deal["stage"] = "buyer_needed"
        deal["conversation"].append({
            "role": "rex",
            "message": f"Hold on contract -- only {buyer_count_available} buyers available. Recruiting more.",
            "timestamp": NOW.isoformat(),
        })
        save_deal(deal)
        post_slack(
            f"*DEAL ON HOLD -- NEED BUYERS*\n"
            f"Property: {addr}\n"
            f"Offer: ${deal.get('offer', 0):,.0f}\n"
            f"Only {buyer_count_available} buyers in this market. Need 2+ before signing.\n"
            f"Recruiting buyers now."
        )
        # Send a stalling message to seller
        send_email(email,
            f"Re: {addr}",
            f"Hey {first},\n\nThanks for agreeing to the offer. I'm having my team run final "
            f"due diligence on the property -- title search, comps verification, etc. "
            f"I'll have the paperwork ready within 48 hours.\n\nRich"
        )
        return

    log.info(f"Buyer check passed: {buyer_count_available} buyers ready for {addr}")

    send_email(email, subject, body, state=deal.get("state", ""))

    # Generate Ace's custom pitch package (email + SMS + HTML one-pager) so the buyer
    # blast uses branded copy rather than raw deal data. Stored on the deal record.
    try:
        from ace_pitch_engine import pitch_deal
        pitch = pitch_deal(deal)
        deal["ace_pitch"] = {
            "email_pitch": pitch.get("email_pitch", ""),
            "sms_pitch": pitch.get("sms_pitch", ""),
            "one_pager_html": pitch.get("one_pager_html", ""),
            "generated_at": pitch.get("generated_at", ""),
        }
        log.info(f"Ace pitch generated for {addr}")
    except ImportError:
        log.debug("ace_pitch_engine not available -- buyer blast will use default copy")
    except Exception as e:
        log.warning(f"Ace pitch generation failed (non-fatal): {e}")

    # Update deal stage
    deal["stage"] = "under_contract"
    deal["contract_sent_at"] = NOW.isoformat()
    deal["contract_path"] = str(contract_path)
    deal["conversation"].append({
        "role": "rex",
        "message": f"Purchase agreement sent to seller. {buyer_count_available} buyers pre-qualified.",
        "timestamp": NOW.isoformat(),
    })
    save_deal(deal)

    # IMMEDIATELY blast to buyers -- they're already pre-qualified
    buyer_count = blast_deal_to_buyers(deal)

    post_slack(
        f"*DEAL UNDER CONTRACT*\n"
        f"Property: {addr}\n"
        f"Offer: ${deal.get('offer', 0):,.0f}\n"
        f"Contract sent to seller\n"
        f"Blasting deal sheet to {buyer_count} buyers"
    )
    log.info(
        f"DEAL UNDER CONTRACT: {addr} at ${deal.get('offer', 0):,.0f} "
        f"-- blasted to {buyer_count} buyers"
    )
    return True


# ---------------------------------------------------------------------------
# REPLY HANDLER -- called by rex_negotiator when seller replies
# ---------------------------------------------------------------------------

def handle_seller_reply(lead_or_deal: dict, reply_text: str) -> str:
    """
    Route seller reply to the right stage handler.
    Returns the response message sent (or empty string if none).
    """
    addr = lead_or_deal.get("address", "")
    slug = make_slug(addr)
    deal = load_deal(slug)

    msg_lower = reply_text.lower().strip()

    # Check for opt-out
    if any(w in msg_lower for w in ["stop", "unsubscribe", "remove me", "not interested"]):
        if deal:
            deal["stage"] = "dead"
            save_deal(deal)
        return ""

    # If no deal file yet, seller is replying to outreach
    if not deal:
        # Check if interested
        if any(w in msg_lower for w in [
            "interested", "how much", "what can you offer", "tell me more",
            "yes", "what's the offer", "cash offer",
        ]):
            send_qualifying_questions(lead_or_deal)
            return QUALIFYING_MSG

        # Check if seller has company/trust concerns even before deal exists
        try:
            from rex_straight_line import analyze_seller_response
            analysis = analyze_seller_response(reply_text, lead_or_deal)
            if analysis["lowest_axis"] == "company" and analysis["lowest_score"] < 5:
                # Seller is suspicious -- send credibility proof first
                email = lead_or_deal.get("owner_email", "")
                if email and analysis["script"]:
                    send_email(email, "About Everlight Ventures", analysis["script"])
                    return "Credibility proof sent (low company certainty)"
        except ImportError:
            pass

        return ""

    stage = deal.get("stage", "")

    # Stage: qualifying -- seller answered our questions
    if stage == "qualifying":
        return _handle_qualifying_reply(deal, reply_text)

    # Stage: offer_sent -- seller responding to our offer
    if stage == "offer_sent":
        return _handle_offer_reply(deal, reply_text)

    # Stage: under_contract -- post-contract communication
    if stage == "under_contract":
        return _handle_contract_reply(deal, reply_text)

    # Default: send qualifying questions
    send_qualifying_questions(lead_or_deal)
    return QUALIFYING_MSG


def _handle_qualifying_reply(deal: dict, reply_text: str) -> str:
    """Parse seller's qualifying answers and send offer."""
    # Try to extract condition score from reply
    condition = 5  # default mid-range
    condition_match = re.search(r'\b([1-9]|10)\b', reply_text)
    if condition_match:
        condition = int(condition_match.group(1))

    arv = deal.get("estimated_arv", 0) or 0
    if arv <= 0:
        # Fallback -- we need ARV to calculate
        arv = 200_000  # conservative estimate

    offer_details = calculate_offer(
        arv=arv,
        condition_score=condition,
        address=deal.get("address", ""),
        city=deal.get("city", ""),
        state=deal.get("state", ""),
        beds=deal.get("beds", 3),
        baths=deal.get("baths", 2.0),
        sqft=deal.get("sqft", 1500),
        year_built=deal.get("year_built", 1990),
    )

    deal["seller_qualifying_reply"] = reply_text[:1000]
    deal["conversation"].append({
        "role": "seller",
        "message": reply_text[:500],
        "timestamp": NOW.isoformat(),
    })
    save_deal(deal)

    # If comp validation says LOW confidence, defer instead of offering blind
    if offer_details.get("skip"):
        first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
        addr = deal.get("address", "")
        email = deal.get("owner_email", "")
        defer_body = (
            f"Hi {first},\n\n"
            f"Thank you for the details on {addr}. I need to do a bit more "
            f"research on comparable sales in your area before I can give you "
            f"an accurate cash offer.\n\n"
            f"I will follow up within 24 hours with a firm number.\n\n"
            f"Harrison Knox\nEverlight Ventures"
        )
        send_email(email, f"Re: Cash offer for {addr}", defer_body)
        deal["stage"] = "researching"
        deal["conversation"].append({
            "role": "rex",
            "message": "Deferred offer -- low comp confidence, needs research",
            "timestamp": NOW.isoformat(),
        })
        save_deal(deal)
        post_slack(
            f"*DEFERRED OFFER* -- low comp confidence\n"
            f"Property: {addr}\n"
            f"ATTOM ARV: ${arv:,.0f}\n"
            f"Comp ARV: ${offer_details.get('validated_arv', 0):,.0f}\n"
            f"Reason: {offer_details.get('skip_reason', 'unknown')}"
        )
        log.info(f"Deferred offer for {addr} -- low comp confidence")
        return "Deferred -- need more research"

    send_offer(deal, offer_details)
    return f"Offer: ${offer_details['offer']:,.0f}"


def _handle_offer_reply(deal: dict, reply_text: str) -> str:
    """
    Seller responding to our offer -- routed through Straight Line system.

    Uses rex_straight_line to:
    1. Analyze certainty on product/company/person axes
    2. Calculate counter-offers using ARV-based rules
    3. Apply psychological close tactics
    4. Enforce 24-hour silence after initial offer
    """
    msg_lower = reply_text.lower().strip()

    deal["conversation"].append({
        "role": "seller",
        "message": reply_text[:500],
        "timestamp": NOW.isoformat(),
    })

    # Acceptance signals -- check before Straight Line analysis
    if any(w in msg_lower for w in [
        "yes", "ok", "deal", "agreed", "let's do it",
        "sounds good", "send it", "i accept",
    ]):
        # Use the nibble tactic to improve terms on acceptance
        try:
            from rex_straight_line import get_nibble_message
            nibble_msg = get_nibble_message(deal)
            email = deal.get("owner_email", "")
            addr = deal.get("address", "")
            send_email(email, f"Re: {addr}", nibble_msg)
            deal["conversation"].append({
                "role": "rex",
                "message": "Nibble tactic: requested 14-day close",
                "timestamp": NOW.isoformat(),
            })
        except ImportError:
            pass

        process_seller_acceptance(deal)
        return "Contract sent + buyers notified (nibble applied)"

    # Route through Straight Line system
    try:
        from rex_straight_line import (
            generate_response,
            should_enforce_silence,
            analyze_seller_response,
            calculate_counter,
        )

        # Check 24-hour silence window
        if should_enforce_silence(deal):
            save_deal(deal)
            log.info(f"Silence enforced for {deal.get('address', '?')}")
            return "Silence -- waiting 24h after offer"

        # Generate Straight Line response
        sl_result = generate_response(deal, reply_text)
        action = sl_result["action"]
        certainty = sl_result["certainty"]

        # Log certainty scores to deal
        deal["certainty_scores"] = certainty
        deal["last_tactic"] = sl_result["tactic_used"]

        # Handle acceptance from counter-negotiation
        if action == "accept":
            counter_details = sl_result.get("counter_details", {})
            accepted_price = counter_details.get("price", deal.get("offer", 0))
            deal["offer"] = accepted_price
            if deal.get("offer_details"):
                deal["offer_details"]["offer"] = accepted_price
            save_deal(deal)
            process_seller_acceptance(deal)
            return f"Accepted at ${accepted_price:,} -- contract sent"

        # Handle walk-away
        if action == "walk":
            deal["stage"] = "dead"
            deal["dead_reason"] = "price_too_high"
            deal["conversation"].append({
                "role": "rex",
                "message": f"Walk-away: {sl_result['tactic_used']}",
                "timestamp": NOW.isoformat(),
            })
            save_deal(deal)

            if sl_result["should_send"] and sl_result["response_text"]:
                email = deal.get("owner_email", "")
                addr = deal.get("address", "")
                send_email(email, f"Re: {addr}", sl_result["response_text"])

            post_slack(
                f"*DEAL WALKED* -- price too high\n"
                f"Property: {deal.get('address', '?')}\n"
                f"Certainty: P={certainty['product']}, "
                f"C={certainty['company']}, S={certainty['person']}"
            )
            return "Walk-away -- graceful exit sent"

        # Handle counter, address_product, address_company, address_person
        if sl_result["should_send"] and sl_result["response_text"]:
            email = deal.get("owner_email", "")
            addr = deal.get("address", "")
            send_email(email, f"Re: Cash offer for {addr}", sl_result["response_text"])
            deal["conversation"].append({
                "role": "rex",
                "message": (
                    f"Straight Line ({sl_result['tactic_used']}): "
                    f"certainty P={certainty['product']}, "
                    f"C={certainty['company']}, S={certainty['person']}"
                ),
                "timestamp": NOW.isoformat(),
            })
            save_deal(deal)

            counter_details = sl_result.get("counter_details")
            if counter_details and counter_details.get("counter_price"):
                return f"Counter: ${counter_details['counter_price']:,.0f} (tactic: {sl_result['tactic_used']})"
            return f"Response sent (tactic: {sl_result['tactic_used']})"

        save_deal(deal)
        return f"Holding -- {sl_result['tactic_used']}"

    except ImportError:
        log.warning("rex_straight_line not available -- using legacy negotiation")
        return _handle_offer_reply_legacy(deal, reply_text)


def _handle_offer_reply_legacy(deal: dict, reply_text: str) -> str:
    """Legacy counter-offer logic (fallback if Straight Line is unavailable)."""
    # Counter offer
    amounts = re.findall(r'\$?([\d,]+)', reply_text)
    if amounts:
        counter = int(amounts[0].replace(",", ""))
        arv = deal.get("estimated_arv", 0) or deal.get("offer_details", {}).get("arv", 200_000)
        max_offer = arv * 0.70  # absolute ceiling

        if counter <= max_offer:
            deal["offer"] = counter
            deal["offer_details"]["offer"] = counter
            process_seller_acceptance(deal)
            return f"Accepted counter at ${counter:,} -- contract sent"
        else:
            our_max = round((arv * 0.65) / 500) * 500
            first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
            addr = deal.get("address", "")
            body = (
                f"Hi {first},\n\n"
                f"I appreciate you coming back with a number on {addr}. "
                f"${counter:,} is a bit above where I can make the numbers work.\n\n"
                f"The highest I can go is ${our_max:,.0f}. That accounts for "
                f"repairs, closing costs, and holding costs on my end.\n\n"
                f"If ${our_max:,.0f} works for you, I can have the purchase "
                f"agreement over today and close within 7 days.\n\n"
                f"Harrison Knox\nEverlight Ventures"
            )
            email = deal.get("owner_email", "")
            send_email(email, f"Re: Cash offer for {addr}", body)
            deal["conversation"].append({
                "role": "rex",
                "message": f"Counter-negotiation: our max ${our_max:,.0f}",
                "timestamp": NOW.isoformat(),
            })
            save_deal(deal)
            return f"Counter-negotiated to ${our_max:,.0f}"

    # Unclear reply
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    addr = deal.get("address", "")
    offer = deal.get("offer", 0)
    body = (
        f"Hi {first},\n\n"
        f"Thanks for getting back to me. Just to confirm -- my offer for "
        f"{addr} is ${offer:,.0f}, cash, close in 7 days.\n\n"
        f"Would you like me to send over the purchase agreement?\n\n"
        f"Harrison Knox\nEverlight Ventures"
    )
    email = deal.get("owner_email", "")
    send_email(email, f"Re: Cash offer for {addr}", body)
    save_deal(deal)
    return "Clarification sent"


def _handle_contract_reply(deal: dict, reply_text: str) -> str:
    """Post-contract communication -- usually questions or signing confirmation."""
    deal["conversation"].append({
        "role": "seller",
        "message": reply_text[:500],
        "timestamp": NOW.isoformat(),
    })
    save_deal(deal)

    addr = deal.get("address", "")
    post_slack(
        f"*POST-CONTRACT REPLY* from seller on {addr}:\n"
        f'"{reply_text[:300]}"'
    )
    return ""


# ---------------------------------------------------------------------------
# MAIN -- process all leads that have replied
# ---------------------------------------------------------------------------

def process_interested_leads():
    """
    Scan leads_db.json for leads marked as 'replied' and route them
    through the closer pipeline.
    """
    if not LEADS_DB.exists():
        return

    leads = json.loads(LEADS_DB.read_text())
    processed = 0

    for lead in leads:
        if lead.get("status") != "replied":
            continue

        addr = lead.get("address", "")
        slug = make_slug(addr)
        deal = load_deal(slug)

        if not deal:
            # New interested lead -- send qualifying questions
            send_qualifying_questions(lead)
            lead["status"] = "negotiating"
            processed += 1
        else:
            # Deal exists -- check stage
            if deal.get("stage") in ("under_contract", "closed", "dead"):
                continue
            processed += 1

    if processed:
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    log.info(f"Processed {processed} interested leads")


# ---------------------------------------------------------------------------
# DEAL CLOSE -- buyer accepts assignment, invoice goes out
# ---------------------------------------------------------------------------

def close_deal(deal: dict, buyer: dict) -> dict:
    """
    Close a wholesale deal: generate finder agreement PDF, send Stripe invoice.

    Args:
        deal: deal dict with address, offer, assignment_fee, etc.
        buyer: dict with name, email, company

    Returns: dict with contract_path, invoice_result
    """
    addr = deal.get("address", "")
    slug = deal.get("address_slug", make_slug(addr))
    assignment_fee = deal.get("assignment_fee", deal.get("offer", 0) * 0.10)
    buyer_name = buyer.get("name", buyer.get("company", ""))
    buyer_email = buyer.get("email", "")

    result = {"contract_path": None, "invoice": None}

    # 1. Generate finder fee agreement PDF
    if generate_finder_agreement:
        try:
            contract_path = generate_finder_agreement({
                "client_name": buyer_name,
                "client_contact": buyer_name,
                "client_email": buyer_email,
                "scope": "Real estate wholesale assignment - %s" % addr,
                "commission_pct": 0,
                "deal_value": deal.get("offer", 0),
                "term_months": 12,
                "state": "California",
            })
            result["contract_path"] = contract_path
            log.info("Finder agreement PDF: %s" % contract_path)
        except Exception as e:
            log.error("Finder agreement generation failed: %s" % e)

    # 2. Send Stripe invoice for assignment fee
    if stripe_invoice_deal and buyer_email:
        try:
            inv = stripe_invoice_deal({
                "client_name": buyer_name,
                "client_email": buyer_email,
                "deal_type": "wholesale_assignment",
                "scope": "Assignment fee - %s" % addr,
                "deal_value": deal.get("offer", 0),
                "commission_amount": assignment_fee,
                "due_days": 3,
                "auto_send": True,
            })
            result["invoice"] = inv
            if inv.get("success"):
                log.info("Stripe invoice sent: %s ($%.2f)" % (inv["invoice_id"], inv["amount_usd"]))
            else:
                log.error("Stripe invoice failed: %s" % inv.get("error"))
        except Exception as e:
            log.error("Stripe invoicing error: %s" % e)

    # 3. Update deal stage
    deal["stage"] = "closed"
    deal["buyer_name"] = buyer_name
    deal["buyer_email"] = buyer_email
    deal["assignment_fee"] = assignment_fee
    deal["closed_at"] = datetime.now(timezone.utc).isoformat()
    deal["invoice_id"] = (result.get("invoice") or {}).get("invoice_id")
    deal["invoice_url"] = (result.get("invoice") or {}).get("invoice_url")
    deal["conversation"].append({
        "role": "rex",
        "message": "DEAL CLOSED. Buyer: %s. Assignment fee: $%s. Invoice sent." % (
            buyer_name, "{:,.0f}".format(assignment_fee)
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_deal(deal)

    # 4. Post to Slack
    invoice_url = (result.get("invoice") or {}).get("invoice_url", "")
    post_slack(
        "*DEAL CLOSED*\n"
        "Property: %s\n"
        "Purchase Price: $%s\n"
        "Assignment Fee: $%s\n"
        "Buyer: %s\n"
        "Invoice: %s\n"
        "Contract: %s" % (
            addr,
            "{:,.0f}".format(deal.get("offer", 0)),
            "{:,.0f}".format(assignment_fee),
            buyer_name,
            invoice_url or "Manual",
            result.get("contract_path", "N/A"),
        )
    )

    log.info("DEAL CLOSED: %s | Buyer: %s | Fee: $%s" % (
        addr, buyer_name, "{:,.0f}".format(assignment_fee)
    ))
    return result


if __name__ == "__main__":
    process_interested_leads()
