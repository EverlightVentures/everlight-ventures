"""
Rex Lead Scorer -- score every lead by distress signals before outreach.

Run this before any outreach cycle so Rex contacts HOT leads first.
Reads leads_db.json, applies motivation scoring, sorts descending, saves back.

Scoring tiers:
  > 70  = HOT  (contact immediately, multi-channel)
  40-70 = WARM (standard sequence)
  < 40  = COLD (low priority, batch outreach)
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Scorer %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_scorer")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"

# ---------------------------------------------------------------------------
# SCORING WEIGHTS
# ---------------------------------------------------------------------------

LEAD_TYPE_SCORES = {
    "pre_foreclosure": 40,
    "probate": 35,
    "code_violation": 30,
    "tax_lien": 25,
    "vacant": 25,
    "absentee": 20,
    "expired_listing": 15,
    "divorce": 15,
}

BASE_SCORE = 20


def score_lead(lead: dict) -> int:
    """Calculate motivation score for a single lead."""
    score = BASE_SCORE

    # Lead type distress signal
    lead_type = lead.get("lead_type", "").lower().strip()
    score += LEAD_TYPE_SCORES.get(lead_type, 0)

    # Absentee owner bonus
    if lead.get("is_absentee"):
        score += 30

    # Property value signals
    arv = lead.get("estimated_arv", 0) or 0
    if arv > 150_000:
        score += 20
    elif arv < 50_000 and arv > 0:
        score -= 20

    # Old construction -- likely needs repairs, owner more motivated
    year_built = lead.get("year_built", 0) or 0
    if 0 < year_built < 1970:
        score += 10

    # Multi-channel contact available
    has_phone = bool(lead.get("owner_phone", "").strip())
    has_email = bool(lead.get("owner_email", "").strip())
    if has_phone and has_email:
        score += 15

    return max(score, 0)


def classify(score: int) -> str:
    """Return HOT / WARM / COLD based on score."""
    if score > 70:
        return "HOT"
    if score >= 40:
        return "WARM"
    return "COLD"


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def score_all_leads() -> dict:
    """Score every lead in leads_db.json and sort descending. Returns stats."""
    if not LEADS_DB.exists():
        log.warning("No leads_db.json found -- nothing to score")
        return {"total": 0, "hot": 0, "warm": 0, "cold": 0}

    leads = json.loads(LEADS_DB.read_text())
    if not leads:
        log.info("leads_db.json is empty")
        return {"total": 0, "hot": 0, "warm": 0, "cold": 0}

    hot = warm = cold = 0

    for lead in leads:
        s = score_lead(lead)
        lead["motivation_score"] = s
        lead["motivation_tier"] = classify(s)

        tier = classify(s)
        if tier == "HOT":
            hot += 1
        elif tier == "WARM":
            warm += 1
        else:
            cold += 1

    # Sort by score descending
    leads.sort(key=lambda x: x.get("motivation_score", 0), reverse=True)

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    stats = {"total": len(leads), "hot": hot, "warm": warm, "cold": cold}
    log.info(
        f"Scored {stats['total']} leads: "
        f"{hot} HOT | {warm} WARM | {cold} COLD"
    )
    if leads:
        top = leads[0]
        log.info(
            f"Top lead: {top.get('address', '?')} -- "
            f"score {top['motivation_score']} ({top['motivation_tier']})"
        )

    return stats


if __name__ == "__main__":
    stats = score_all_leads()
    print(json.dumps(stats, indent=2))
