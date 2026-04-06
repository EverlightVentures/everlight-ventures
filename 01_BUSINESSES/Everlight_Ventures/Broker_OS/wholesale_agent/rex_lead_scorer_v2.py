"""
Rex Lead Scorer V2 -- comprehensive 100-point scoring system.

Replaces the basic scorer with granular distress signals, deal quality,
and contact quality metrics. Runs every 6 hours to keep scores fresh.

Scoring breakdown (100-point scale):
  DISTRESS SIGNALS: max 50 points
  DEAL QUALITY:     max 30 points
  CONTACT QUALITY:  max 20 points

Tiers:
  70+  = PRIORITY (contact immediately, multi-channel, top of queue)
  50-69 = HOT     (standard Belfort sequence, high priority)
  30-49 = WARM    (standard sequence)
  <30   = COLD    (batch outreach only, low priority)

Cron: 0 */6 * * *
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Scorer V2 %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_scorer_v2")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"


# ---------------------------------------------------------------------------
# SCORING TABLES
# ---------------------------------------------------------------------------

# Distress signals (max 50 points)
# Multiple signals can stack, but capped at 50
DISTRESS_SCORES = {
    "tax_delinquent":    20,
    "tax_lien":          20,  # alias
    "pre_foreclosure":   20,
    "lis_pendens":       20,  # alias
    "code_violation":    15,
    "probate":           15,
    "estate":            15,  # alias
    "vacant":            12,
    "absentee":          10,
    "divorce":           10,
    "expired_listing":    8,
    "fsbo":               8,
    "price_reduction":    5,
}

# Lead type to distress signal mapping (normalize various formats)
LEAD_TYPE_ALIASES = {
    "pre-foreclosure": "pre_foreclosure",
    "preforeclosure": "pre_foreclosure",
    "tax lien": "tax_lien",
    "tax delinquent": "tax_delinquent",
    "code violation": "code_violation",
    "lis pendens": "lis_pendens",
    "expired listing": "expired_listing",
    "for sale by owner": "fsbo",
    "price reduction": "price_reduction",
    "high_equity": "",  # no distress signal by itself
    "absentee_owner": "absentee",
}


def _score_distress(lead: dict) -> int:
    """Calculate distress signal score (max 50 points)."""
    score = 0
    signals_found = []

    # Primary lead type
    lead_type = lead.get("lead_type", "").lower().strip()
    normalized = LEAD_TYPE_ALIASES.get(lead_type, lead_type)
    if normalized in DISTRESS_SCORES:
        score += DISTRESS_SCORES[normalized]
        signals_found.append(normalized)

    # Boolean flags that indicate additional distress
    if lead.get("is_absentee") and "absentee" not in signals_found:
        score += DISTRESS_SCORES["absentee"]
        signals_found.append("absentee")

    if lead.get("is_vacant") and "vacant" not in signals_found:
        score += DISTRESS_SCORES["vacant"]
        signals_found.append("vacant")

    if lead.get("is_probate") and "probate" not in signals_found:
        score += DISTRESS_SCORES["probate"]
        signals_found.append("probate")

    if lead.get("has_code_violations") and "code_violation" not in signals_found:
        score += DISTRESS_SCORES["code_violation"]
        signals_found.append("code_violation")

    if lead.get("is_tax_delinquent") and "tax_delinquent" not in signals_found:
        score += DISTRESS_SCORES["tax_delinquent"]
        signals_found.append("tax_delinquent")

    if lead.get("is_divorce") and "divorce" not in signals_found:
        score += DISTRESS_SCORES["divorce"]
        signals_found.append("divorce")

    if lead.get("is_expired") and "expired_listing" not in signals_found:
        score += DISTRESS_SCORES["expired_listing"]
        signals_found.append("expired_listing")

    if lead.get("is_fsbo") and "fsbo" not in signals_found:
        score += DISTRESS_SCORES["fsbo"]
        signals_found.append("fsbo")

    if lead.get("price_reductions", 0) and "price_reduction" not in signals_found:
        score += DISTRESS_SCORES["price_reduction"]
        signals_found.append("price_reduction")

    # Tax delinquent 2+ years gets the full 20, single year gets 10
    tax_years = lead.get("tax_delinquent_years", 0)
    if tax_years and "tax_delinquent" not in signals_found:
        if tax_years >= 2:
            score += 20
        else:
            score += 10
        signals_found.append("tax_delinquent")

    return min(score, 50)


def _score_deal_quality(lead: dict) -> int:
    """Calculate deal quality score (max 30 points)."""
    score = 0

    # ARV-based scoring
    arv = lead.get("estimated_arv", 0) or 0
    if arv > 200_000:
        score += 10  # good assignment fee potential
    elif 100_000 <= arv <= 200_000:
        score += 5
    elif 0 < arv < 100_000:
        score -= 5  # thin margins

    # Tear-down candidate detection
    year_built = lead.get("year_built", 0) or 0
    sqft = lead.get("sqft", 0) or 0
    has_new_construction_nearby = lead.get("new_construction_nearby", False)

    is_teardown = (
        0 < year_built < 1960
        and (sqft < 1200 or sqft == 0)
    )
    if is_teardown:
        score += 15
    elif 0 < year_built < 1970:
        # Old but not necessarily teardown -- still motivated
        score += 5

    # High equity (owned 10+ years)
    years_owned = lead.get("years_owned", 0) or 0
    if years_owned == 0:
        # Estimate from year_acquired if available
        year_acquired = lead.get("year_acquired", 0) or 0
        if year_acquired > 0:
            years_owned = datetime.now(timezone.utc).year - year_acquired

    if years_owned >= 10:
        score += 10
    elif years_owned >= 5:
        score += 5

    # Cash-only listing bonus
    if lead.get("is_cash_only") or lead.get("cash_only"):
        score += 5

    return min(max(score, -5), 30)


def _score_contact_quality(lead: dict) -> int:
    """Calculate contact quality score (max 20 points)."""
    has_email = bool(lead.get("owner_email", "").strip())
    has_phone = bool(lead.get("owner_phone", "").strip())

    if has_email and has_phone:
        # Both channels available -- best case
        score = 15
    elif has_email:
        score = 10
    elif has_phone:
        score = 8
    else:
        score = 0

    # Multi-channel bonus (has mail address for direct mail too)
    has_mail = bool(lead.get("mailing_address", "").strip())
    if has_mail and (has_email or has_phone):
        score += 5

    return min(score, 20)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def score_lead(lead: dict) -> int:
    """
    Calculate comprehensive motivation score for a single lead.

    Returns an integer from 0 to 100.
    """
    distress = _score_distress(lead)
    deal = _score_deal_quality(lead)
    contact = _score_contact_quality(lead)

    # OPPORTUNITY ZONE BONUS -- OZ properties attract more buyers willing to pay more
    oz_bonus = 15 if lead.get("opportunity_zone") else 0

    total = distress + deal + contact + oz_bonus
    return max(min(total, 100), 0)


def classify(score: int) -> str:
    """Return tier label based on score."""
    if score >= 70:
        return "PRIORITY"
    if score >= 50:
        return "HOT"
    if score >= 30:
        return "WARM"
    return "COLD"


def score_all_leads() -> dict:
    """
    Score every lead in leads_db.json, update fields, sort descending.
    Returns stats dict.
    """
    if not LEADS_DB.exists():
        log.warning("No leads_db.json found -- nothing to score")
        return {"total": 0, "priority": 0, "hot": 0, "warm": 0, "cold": 0}

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Failed to read leads_db.json: {exc}")
        return {"total": 0, "priority": 0, "hot": 0, "warm": 0, "cold": 0}

    if not leads:
        log.info("leads_db.json is empty")
        return {"total": 0, "priority": 0, "hot": 0, "warm": 0, "cold": 0}

    priority = hot = warm = cold = 0

    for lead in leads:
        s = score_lead(lead)
        tier = classify(s)
        lead["motivation_score"] = s
        lead["motivation_tier"] = tier
        lead["score_breakdown"] = {
            "distress": _score_distress(lead),
            "deal_quality": _score_deal_quality(lead),
            "contact_quality": _score_contact_quality(lead),
        }

        if tier == "PRIORITY":
            priority += 1
        elif tier == "HOT":
            hot += 1
        elif tier == "WARM":
            warm += 1
        else:
            cold += 1

    # Sort by score descending so PRIORITY leads get contacted first
    leads.sort(key=lambda x: x.get("motivation_score", 0), reverse=True)

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    stats = {
        "total": len(leads),
        "priority": priority,
        "hot": hot,
        "warm": warm,
        "cold": cold,
    }

    log.info(
        f"Scored {stats['total']} leads: "
        f"{priority} PRIORITY | {hot} HOT | {warm} WARM | {cold} COLD"
    )

    if leads:
        top = leads[0]
        log.info(
            f"Top lead: {top.get('address', '?')} -- "
            f"score {top['motivation_score']} ({top['motivation_tier']})"
        )
        breakdown = top.get("score_breakdown", {})
        log.info(
            f"  Breakdown: distress={breakdown.get('distress', 0)} "
            f"deal={breakdown.get('deal_quality', 0)} "
            f"contact={breakdown.get('contact_quality', 0)}"
        )

    return stats


def get_priority_leads(n: int = 20) -> list[dict]:
    """
    Return the top N leads by score for immediate outreach.
    Only includes leads with status suitable for contact (new, contacted).
    Excludes opted_out, permanently_dead, closed, etc.
    """
    if not LEADS_DB.exists():
        return []

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    # Load suppression list
    try:
        from rex_stop_handler import is_suppressed
    except ImportError:
        def is_suppressed(email):
            return False

    contactable_statuses = {"new", "contacted", "cooling_off"}
    priority = []

    for lead in leads:
        if lead.get("status", "new") not in contactable_statuses:
            continue
        if is_suppressed(lead.get("owner_email", "")):
            continue
        priority.append(lead)

    # Sort by score descending
    priority.sort(key=lambda x: x.get("motivation_score", 0), reverse=True)

    return priority[:n]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    stats = score_all_leads()
    print(json.dumps(stats, indent=2))

    # Show top 5
    top = get_priority_leads(5)
    if top:
        print("\nTop 5 priority leads:")
        for i, lead in enumerate(top, 1):
            print(
                f"  {i}. [{lead.get('motivation_score', 0)} "
                f"{lead.get('motivation_tier', '?')}] "
                f"{lead.get('address', '?')} | "
                f"{lead.get('owner_name', '?')}"
            )
