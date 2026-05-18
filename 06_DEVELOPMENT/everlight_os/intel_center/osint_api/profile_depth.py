"""
profile_depth -- score how much we actually know + identify gaps.

Operator critique: "deep dive" doesn't mean RUNNING more investigators -- it
means the OPERATOR can see at a glance how thin the profile actually is and
what's missing to make it usable.

Outputs a depth score 0-100 + a list of "next-step" recommendations.
"""
from __future__ import annotations


# Each axis we want to score
AXES = [
    ("identity_match",     "Do findings link to OUR specific person (state/city/email match)?"),
    ("interest_diversity", "How many distinct interest categories detected?"),
    ("life_event_signal",  "Any life events (move, divorce, retirement, foreclosure)?"),
    ("profession_known",   "Job title / employer captured?"),
    ("financial_signal",   "Multi-property / distress / business filings detected?"),
    ("contact_verified",   "Phone OR email verified by OSINT?"),
    ("media_presence",     "News mentions / public articles found?"),
    ("civic_engagement",   "FEC / nonprofit / patent / public records?"),
    ("consumer_behavior",  "Yelp / Goodreads / Strava / public reviews?"),
    ("location_confirmed", "City + state confirmed across 2+ sources?"),
]


def score(personality: dict, sections: dict, verification_summary: dict) -> dict:
    if not isinstance(personality, dict): personality = {}
    if not isinstance(sections, dict): sections = {}
    if not isinstance(verification_summary, dict): verification_summary = {}

    interests = personality.get("interests", {}) or {}
    life_events = personality.get("life_events", {}) or {}
    profession = personality.get("profession", []) or []
    financial = personality.get("financial_signals", []) or []
    red_flags = personality.get("red_flags", []) or []

    contact = sections.get("contact", []) or []
    online = sections.get("online", []) or []
    business = sections.get("business", []) or []
    risk = sections.get("risk", []) or []

    breakdown = {}
    breakdown["identity_match"] = 100 if verification_summary.get("verified", 0) >= 3 else \
                                   60 if verification_summary.get("verified", 0) >= 1 else 0
    breakdown["interest_diversity"] = min(100, len(interests) * 25)
    breakdown["life_event_signal"] = min(100, len(life_events) * 50)
    breakdown["profession_known"] = 80 if profession else 0
    breakdown["financial_signal"] = min(100, len(financial) * 40)
    breakdown["contact_verified"] = min(100, len([c for c in contact
                                                     if (c.get("confidence") or 0) >= 60]) * 40)
    breakdown["media_presence"] = min(100, sum(1 for o in online
                                                if "news" in (o.get("label") or "").lower()) * 25)
    breakdown["civic_engagement"] = 100 if any(("FEC" in (o.get("label") or "") or
                                                 "Patent" in (o.get("label") or "") or
                                                 "Nonprofit" in (o.get("label") or ""))
                                                for o in (online + business)) else 0
    breakdown["consumer_behavior"] = min(100, sum(1 for o in online
                                                   if any(k in (o.get("label") or "").lower()
                                                          for k in ("yelp", "goodreads", "strava",
                                                                     "untappd", "letterboxd", "spotify"))) * 25)
    breakdown["location_confirmed"] = 100 if "city_match" in (
        verification_summary.get("highest_confidence_per_signal", {}) or {}
    ) else 0

    overall = round(sum(breakdown.values()) / len(breakdown))
    gaps = [(k, v) for k, v in breakdown.items() if v < 50]
    gaps.sort(key=lambda x: x[1])

    # Recommendations to deepen the gaps
    recs = []
    for axis, score_v in gaps[:5]:
        recs.append({
            "axis": axis,
            "score": score_v,
            "what": dict(AXES).get(axis, ""),
            "next_step": _next_step_for(axis),
        })

    return {
        "overall_score": overall,
        "breakdown": breakdown,
        "gaps": [g[0] for g in gaps],
        "recommendations": recs,
        "verdict": _verdict(overall),
    }


def _verdict(score: int) -> str:
    if score >= 75: return "Strong profile -- ready for outreach"
    if score >= 55: return "Workable profile -- consider 1-2 deepening moves before outreach"
    if score >= 35: return "Thin profile -- recommend more lead context before crafting pitch"
    return "Bare profile -- run with more verification context (state/city/email/phone)"


def _next_step_for(axis: str) -> str:
    return {
        "identity_match": "Re-run investigation with --verify-state, --verify-city, --verify-email, --verify-phone",
        "interest_diversity": "Run consumer_signals + social_bio_scraper -- need more public-source coverage",
        "life_event_signal": "Pull from public_records (court + news + obit) for life events",
        "profession_known": "Try social_bio_scraper -- LinkedIn / About.me / GitHub bios usually reveal job",
        "financial_signal": "Run opencorporates + sec_edgar -- business filings show financial pattern",
        "contact_verified": "Cross-reference phone area code with state via owner_intel.AC_TO_STATE",
        "media_presence": "Run public_records (Google News + Bing News pull)",
        "civic_engagement": "Run philanthropy_civic for FEC/990/patents",
        "consumer_behavior": "Run consumer_signals (Yelp/Goodreads/Strava/Untappd)",
        "location_confirmed": "Add --verify-city when running investigation",
    }.get(axis, "Re-run with more context")
