"""
Broker OS - Wholesale Real Estate Pipeline

Service functions for the distressed-property wholesale workflow:
- Score motivated sellers
- Calculate Maximum Allowable Offer (MAO)
- Match properties to cash buyers
- Import CSV leads from PropStream or similar
- Generate outreach messages (SMS + buyer blasts)
"""
from __future__ import annotations

import csv
import io
import logging
import random
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q

from .models import InvestorBuyer, PropertyLead

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------

def score_property(property_lead: PropertyLead) -> int:
    """
    Score a PropertyLead 0-100 based on motivation signals.

    Higher score = more motivated seller = better wholesale opportunity.
    """
    score = 0
    lt = property_lead.lead_type

    # Lead type signals
    if lt in ("pre_foreclosure", "tax_lien"):
        score += 30
    if lt == "code_violation":
        score += 25
    if lt in ("divorce", "probate"):
        score += 20
    if lt == "absentee" or property_lead.is_absentee:
        score += 15
    if lt == "vacant":
        score += 10
    if lt == "expired_listing":
        score += 10

    # Equity check
    equity_pct = float(property_lead.equity_pct or 0)
    if equity_pct > 50:
        score += 15

    # Days on market
    if property_lead.days_on_market > 90:
        score += 10

    # Contact info availability
    if property_lead.owner_phone:
        score += 5
    if property_lead.owner_email:
        score += 5

    # Land deals -- bonus for buildable lots in good areas
    if property_lead.property_type == "land":
        if property_lead.estimated_arv > 0 and property_lead.asking_price > 0:
            land_ratio = float(property_lead.asking_price) / float(property_lead.estimated_arv)
            if land_ratio < 0.20:  # asking less than 20% of build value = great deal
                score += 20
            elif land_ratio < 0.25:
                score += 10
        # Teardowns and infill lots are high priority
        if lt in ("vacant", "code_violation"):
            score += 5

    # High spread bonus (ARV vs asking)
    if property_lead.estimated_arv and property_lead.asking_price:
        spread_pct = (float(property_lead.estimated_arv) - float(property_lead.asking_price)) / float(property_lead.estimated_arv) * 100
        if spread_pct > 40:
            score += 10
        elif spread_pct > 30:
            score += 5

    return min(score, 100)


# ---------------------------------------------------------------------------
# MAO CALCULATION
# ---------------------------------------------------------------------------

def calculate_mao(
    arv: float,
    repair_cost: float,
    assignment_fee: float = 10000.0,
) -> float:
    """
    Maximum Allowable Offer = ARV * 0.70 - repair_cost - assignment_fee

    The 70% rule is the standard wholesaling formula. It ensures enough
    margin for the end buyer (fix-and-flipper) and our assignment fee.
    """
    return arv * 0.70 - repair_cost - assignment_fee


# ---------------------------------------------------------------------------
# BUYER MATCHING
# ---------------------------------------------------------------------------

def match_property_to_buyers(property_lead: PropertyLead) -> list[dict[str, Any]]:
    """
    Find matching InvestorBuyers for a property lead.

    Matching criteria:
    - Buyer's markets list contains the property's city or state
    - Buyer's property_types contains the property's property_type
    - Property asking price within buyer's budget range
    - Buyer is active and cash_buyer=True

    Returns top 10 matches sorted by deals_closed (proven) then can_close_days (fast).
    """
    buyers = InvestorBuyer.objects.filter(is_active=True, cash_buyer=True)
    asking = float(property_lead.asking_price or 0)
    city = (property_lead.city or "").strip().lower()
    state = (property_lead.state or "").strip().upper()
    ptype = property_lead.property_type or ""

    matches = []

    for buyer in buyers:
        reasons = []

        # Market match -- buyer.markets is a JSON list of strings (cities, states, zips)
        buyer_markets = [m.strip().lower() for m in (buyer.markets or [])]
        market_match = False
        if city and city in buyer_markets:
            market_match = True
            reasons.append(f"Buys in {property_lead.city}")
        if state and state.lower() in buyer_markets:
            market_match = True
            reasons.append(f"Buys in {state}")
        if not market_match:
            continue

        # Property type match
        buyer_ptypes = [p.strip().lower() for p in (buyer.property_types or [])]
        if ptype and ptype.lower() not in buyer_ptypes:
            continue
        reasons.append(f"Wants {ptype}")

        # Budget match
        budget_min = float(buyer.budget_min or 0)
        budget_max = float(buyer.budget_max or 0)
        if asking > 0:
            if budget_max > 0 and asking > budget_max:
                continue
            if budget_min > 0 and asking < budget_min:
                continue
            reasons.append(f"Budget ${budget_min:,.0f}-${budget_max:,.0f}")

        matches.append({
            "buyer_id": str(buyer.id),
            "name": buyer.name,
            "company": buyer.company,
            "email": buyer.email,
            "phone": buyer.phone,
            "buyer_type": buyer.get_buyer_type_display(),
            "deals_closed": buyer.deals_closed,
            "can_close_days": buyer.can_close_days,
            "proof_of_funds": buyer.proof_of_funds,
            "match_reasons": reasons,
        })

    # Sort: most deals closed first, then fastest close time
    matches.sort(key=lambda m: (-m["deals_closed"], m["can_close_days"]))
    return matches[:10]


# ---------------------------------------------------------------------------
# CSV IMPORT
# ---------------------------------------------------------------------------

# Column mapping: csv_column -> model_field
_PROPSTREAM_MAP = {
    "address": "address",
    "property address": "address",
    "city": "city",
    "state": "state",
    "zip": "zip_code",
    "zip code": "zip_code",
    "zipcode": "zip_code",
    "property type": "property_type",
    "property_type": "property_type",
    "beds": "bedrooms",
    "bedrooms": "bedrooms",
    "baths": "bathrooms",
    "bathrooms": "bathrooms",
    "sqft": "sqft",
    "square feet": "sqft",
    "year built": "year_built",
    "year_built": "year_built",
    "owner name": "owner_name",
    "owner_name": "owner_name",
    "owner phone": "owner_phone",
    "owner_phone": "owner_phone",
    "owner email": "owner_email",
    "owner_email": "owner_email",
    "asking price": "asking_price",
    "asking_price": "asking_price",
    "list price": "asking_price",
    "estimated value": "estimated_arv",
    "estimated_value": "estimated_arv",
    "arv": "estimated_arv",
    "lead type": "lead_type",
    "lead_type": "lead_type",
}

# Property type normalization
_PTYPE_NORMALIZE = {
    "single family": "sfr",
    "single-family": "sfr",
    "sfr": "sfr",
    "multi-family": "multi",
    "multi family": "multi",
    "multifamily": "multi",
    "duplex": "multi",
    "triplex": "multi",
    "quadplex": "multi",
    "condo": "condo",
    "townhouse": "condo",
    "land": "land",
    "vacant land": "land",
    "commercial": "commercial",
    "mobile": "mobile",
    "mobile home": "mobile",
    "apartment": "apartment",
}

# Lead type normalization
_LEAD_TYPE_NORMALIZE = {
    "pre-foreclosure": "pre_foreclosure",
    "pre foreclosure": "pre_foreclosure",
    "preforeclosure": "pre_foreclosure",
    "tax lien": "tax_lien",
    "tax delinquent": "tax_lien",
    "probate": "probate",
    "estate": "probate",
    "absentee": "absentee",
    "absentee owner": "absentee",
    "divorce": "divorce",
    "code violation": "code_violation",
    "high equity": "high_equity",
    "tired landlord": "high_equity",
    "vacant": "vacant",
    "fsbo": "fsbo",
    "for sale by owner": "fsbo",
    "expired": "expired_listing",
    "expired listing": "expired_listing",
    "zillow": "zillow",
}


def _safe_decimal(val: Any) -> Decimal:
    """Convert a value to Decimal, returning 0 on failure."""
    if val is None:
        return Decimal("0")
    try:
        cleaned = str(val).replace(",", "").replace("$", "").strip()
        if not cleaned:
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _safe_int(val: Any) -> int:
    """Convert a value to int, returning 0 on failure."""
    try:
        cleaned = str(val).replace(",", "").strip()
        if not cleaned:
            return 0
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


def import_csv_leads(csv_file_path: str, source: str = "propstream") -> dict:
    """
    Parse a PropStream or generic CSV export and create PropertyLead records.

    Accepts a file path to a CSV. Skips rows where address is missing or
    where a lead with the same address+city+state already exists.

    Returns: {"created": N, "skipped": N, "errors": [str]}
    """
    created = 0
    skipped = 0
    errors: list[str] = []

    try:
        with open(csv_file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except FileNotFoundError:
        return {"created": 0, "skipped": 0, "errors": [f"File not found: {csv_file_path}"]}
    except Exception as exc:
        return {"created": 0, "skipped": 0, "errors": [f"Read error: {exc}"]}

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return {"created": 0, "skipped": 0, "errors": ["CSV has no header row"]}

    # Build column mapping from the actual headers
    col_map: dict[str, str] = {}
    for header in reader.fieldnames:
        normalized = header.strip().lower()
        if normalized in _PROPSTREAM_MAP:
            col_map[header] = _PROPSTREAM_MAP[normalized]

    for row_num, row in enumerate(reader, start=2):
        try:
            data: dict[str, Any] = {}
            for csv_col, model_field in col_map.items():
                data[model_field] = (row.get(csv_col) or "").strip()

            address = data.get("address", "")
            city = data.get("city", "")
            state = data.get("state", "")

            if not address:
                skipped += 1
                continue

            # Deduplicate by address + city + state
            if PropertyLead.objects.filter(
                address__iexact=address,
                city__iexact=city,
                state__iexact=state,
            ).exists():
                skipped += 1
                continue

            # Normalize property type
            raw_ptype = data.get("property_type", "").lower()
            property_type = _PTYPE_NORMALIZE.get(raw_ptype, "sfr")

            # Normalize lead type
            raw_ltype = data.get("lead_type", "").lower()
            lead_type = _LEAD_TYPE_NORMALIZE.get(raw_ltype, "other")

            lead = PropertyLead(
                address=address,
                city=city,
                state=state[:2].upper() if state else "",
                zip_code=data.get("zip_code", "")[:10],
                property_type=property_type,
                bedrooms=_safe_int(data.get("bedrooms")),
                bathrooms=_safe_decimal(data.get("bathrooms")),
                sqft=_safe_int(data.get("sqft")),
                year_built=_safe_int(data.get("year_built")),
                owner_name=data.get("owner_name", "")[:200],
                owner_phone=data.get("owner_phone", "")[:20],
                owner_email=data.get("owner_email", "")[:254],
                asking_price=_safe_decimal(data.get("asking_price")),
                estimated_arv=_safe_decimal(data.get("estimated_arv")),
                lead_type=lead_type,
                source=source,
                status="new",
                raw_data=row,
            )

            # Score the lead before saving
            lead.motivation_score = score_property(lead)
            lead.save()
            created += 1

        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    logger.info("CSV import complete: created=%d skipped=%d errors=%d", created, skipped, len(errors))
    return {"created": created, "skipped": skipped, "errors": errors}


def import_csv_leads_from_upload(file_obj, source: str = "propstream") -> dict:
    """
    Same as import_csv_leads but accepts a Django UploadedFile (InMemoryUploadedFile).

    Reads the file content directly from memory instead of a file path.
    """
    created = 0
    skipped = 0
    errors: list[str] = []

    try:
        content = file_obj.read().decode("utf-8-sig")
    except Exception as exc:
        return {"created": 0, "skipped": 0, "errors": [f"Read error: {exc}"]}

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return {"created": 0, "skipped": 0, "errors": ["CSV has no header row"]}

    col_map: dict[str, str] = {}
    for header in reader.fieldnames:
        normalized = header.strip().lower()
        if normalized in _PROPSTREAM_MAP:
            col_map[header] = _PROPSTREAM_MAP[normalized]

    for row_num, row in enumerate(reader, start=2):
        try:
            data: dict[str, Any] = {}
            for csv_col, model_field in col_map.items():
                data[model_field] = (row.get(csv_col) or "").strip()

            address = data.get("address", "")
            city = data.get("city", "")
            state = data.get("state", "")

            if not address:
                skipped += 1
                continue

            if PropertyLead.objects.filter(
                address__iexact=address,
                city__iexact=city,
                state__iexact=state,
            ).exists():
                skipped += 1
                continue

            raw_ptype = data.get("property_type", "").lower()
            property_type = _PTYPE_NORMALIZE.get(raw_ptype, "sfr")

            raw_ltype = data.get("lead_type", "").lower()
            lead_type = _LEAD_TYPE_NORMALIZE.get(raw_ltype, "other")

            lead = PropertyLead(
                address=address,
                city=city,
                state=state[:2].upper() if state else "",
                zip_code=data.get("zip_code", "")[:10],
                property_type=property_type,
                bedrooms=_safe_int(data.get("bedrooms")),
                bathrooms=_safe_decimal(data.get("bathrooms")),
                sqft=_safe_int(data.get("sqft")),
                year_built=_safe_int(data.get("year_built")),
                owner_name=data.get("owner_name", "")[:200],
                owner_phone=data.get("owner_phone", "")[:20],
                owner_email=data.get("owner_email", "")[:254],
                asking_price=_safe_decimal(data.get("asking_price")),
                estimated_arv=_safe_decimal(data.get("estimated_arv")),
                lead_type=lead_type,
                source=source,
                status="new",
                raw_data=row,
            )

            lead.motivation_score = score_property(lead)
            lead.save()
            created += 1

        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    logger.info("CSV upload import complete: created=%d skipped=%d errors=%d", created, skipped, len(errors))
    return {"created": created, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# OUTREACH GENERATION
# ---------------------------------------------------------------------------

_SMS_TEMPLATES = {
    "pre_foreclosure": [
        "Hi {name}, I buy houses for cash in {city}. I may be able to help with your property at {address}. Interested? -Rich, Everlight. Reply STOP to opt out",
    ],
    "tax_lien": [
        "Hi {name}, I noticed your {city} property may have tax issues. I buy as-is for cash -- no fees. Want to chat? -Rich, Everlight. Reply STOP to opt out",
    ],
    "absentee": [
        "Hi {name}, are you looking to sell your investment property at {address}? I buy for cash, quick close. -Rich, Everlight. Reply STOP to opt out",
    ],
    "vacant": [
        "Hi {name}, I noticed your property at {address} may be vacant. I buy houses as-is. Interested in a cash offer? -Rich. Reply STOP to opt out",
    ],
    "divorce": [
        "Hi {name}, I help homeowners in {city} sell quickly for cash -- no repairs needed. Want a no-obligation offer on {address}? -Rich. Reply STOP to opt out",
    ],
    "probate": [
        "Hi {name}, I help families sell inherited properties fast for cash. Interested in an offer on {address}? -Rich, Everlight. Reply STOP to opt out",
    ],
    "default": [
        "Hi {name}, I'm a cash buyer in {city}. Would you consider selling {address}? Quick close, no fees. -Rich, Everlight. Reply STOP to opt out",
        "Hi {name}, I buy properties in {city} for cash. Interested in an offer on {address}? -Rich. Reply STOP to opt out",
    ],
}


def generate_outreach_sms(property_lead: PropertyLead) -> str:
    """
    Generate a compliant SMS message for a motivated seller.

    Messages vary by lead_type. All include opt-out language and
    stay under 160 characters where possible.
    """
    templates = _SMS_TEMPLATES.get(property_lead.lead_type, _SMS_TEMPLATES["default"])
    template = random.choice(templates)

    name = (property_lead.owner_name or "").split()[0] if property_lead.owner_name else "there"
    city = property_lead.city or "your area"

    # Shorten address if needed to stay under 160 chars
    address = property_lead.address or "your property"
    if len(address) > 40:
        address = address[:37] + "..."

    msg = template.format(name=name, city=city, address=address)

    # Hard cap at 160 chars -- truncate before opt-out if needed
    if len(msg) > 160:
        opt_out = " Reply STOP to opt out"
        available = 160 - len(opt_out)
        msg = msg[:available].rstrip() + opt_out

    return msg


def generate_buyer_blast(property_lead: PropertyLead, assignment_fee: float = 10000.0) -> str:
    """
    Generate an email/SMS blast to send to matched investors.

    Includes property details, deal numbers, and contact info.
    """
    arv = float(property_lead.estimated_arv or 0)
    asking = float(property_lead.asking_price or 0)
    repair = float(property_lead.estimated_repair or 0)
    mao = calculate_mao(arv, repair, assignment_fee)

    ptype = property_lead.get_property_type_display()
    beds = property_lead.bedrooms
    baths = property_lead.bathrooms
    sqft = property_lead.sqft

    lines = [
        "** NEW WHOLESALE DEAL **",
        "",
        f"Property: {property_lead.address}",
        f"City/State: {property_lead.city}, {property_lead.state} {property_lead.zip_code}",
        f"Type: {ptype} | {beds}bd/{baths}ba | {sqft:,} sqft",
        "",
        f"ARV: ${arv:,.0f}",
        f"Asking: ${asking:,.0f}",
        f"Est. Repairs: ${repair:,.0f}",
        f"Assignment Fee: ${assignment_fee:,.0f}",
        f"MAO: ${mao:,.0f}",
        "",
        f"Cash only -- close in 14 days.",
        "",
        "Contact: Rich @ Everlight Ventures",
        "Phone: (text preferred)",
        "Email: deals@everlightventures.io",
        "",
        "Reply YES if interested. First qualified buyer gets it.",
    ]

    return "\n".join(lines)
