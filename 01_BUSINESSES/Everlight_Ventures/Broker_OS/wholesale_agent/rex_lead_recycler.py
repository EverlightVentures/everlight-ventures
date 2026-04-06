"""
Rex Lead Recycler -- bring dead leads back to life.

80% of wholesale deals come from follow-up touches 3-12. Rex was marking
leads as "dead" after the 5-day Belfort sequence and never touching them
again. This script fixes that.

Recycling logic:
- "dead" leads dormant 30+ days -> recycle back to "new", sequence_step=0
- "cooling_off" leads past their cooling_until date -> back to "new"
- Each recycle uses a different messaging angle so the lead sees fresh copy
- After 3 full recycles (90 days total), mark as "permanently_dead"

Recycle angles:
  recycle_count=0 -> "standard" (original Belfort sequence)
  recycle_count=1 -> "new_investor" (new buyer in the area)
  recycle_count=2 -> "market_update" (property values have changed)
  recycle_count=3 -> permanently_dead, no more contact

Cron: 0 16 * * 0 (Sundays at 8 AM PT / 16:00 UTC)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Recycler %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_recycler")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"

NOW = datetime.now(timezone.utc)

# Days a lead must be "dead" before each recycle
RECYCLE_THRESHOLDS = {
    0: 30,   # First recycle after 30 days dead
    1: 60,   # Second recycle after 60 days dead (cumulative)
    2: 90,   # Third recycle after 90 days dead (cumulative)
}

MAX_RECYCLES = 3

ANGLE_MAP = {
    0: "standard",
    1: "new_investor",
    2: "market_update",
}


# ---------------------------------------------------------------------------
# ALTERNATIVE BELFORT ANGLES
# ---------------------------------------------------------------------------
# These are imported by rex_belfort_sequence.py to select the right
# messaging template based on recycle_angle.

BELFORT_ANGLE_NEW_INVESTOR = {
    0: {
        "channel": "sms",
        "delay_hours": 0,
        "subject": "{address}",
        "body": (
            "Hey {first_name}, I recently started acquiring properties "
            "in {city}. Came across yours at {address}. Any interest in "
            "a quick cash sale? - Rich"
        ),
    },
    1: {
        "channel": "email",
        "delay_hours": 4,
        "subject": "New buyer interested in {address}",
        "body": (
            "Hi {first_name},\n\n"
            "I'm a new investor actively buying in {city} this quarter. "
            "Your property at {address} fits what I'm looking for.\n\n"
            "I can offer:\n"
            "  - All cash, close in 10 days or on your schedule\n"
            "  - As-is condition -- no repairs needed\n"
            "  - I cover closing costs\n"
            "  - Zero commissions or fees\n\n"
            "If you'd consider a no-obligation cash offer, just reply "
            "and I'll have a number for you today.\n\n"
            "Best,\n"
            "Rich Gee\n"
            "Everlight Ventures | Private Acquisitions\n"
            "rich@everlightventures.io\n\n"
            "Not interested? Reply STOP and I will remove you immediately."
        ),
    },
    2: {
        "channel": "sms",
        "delay_hours": 24,
        "subject": "Re: {address}",
        "body": (
            "Hey {first_name}, following up on {address}. I'm closing "
            "on two other properties in {city} this week. Would love to "
            "add yours. Quick chat? - Rich"
        ),
    },
    3: {
        "channel": "email",
        "delay_hours": 48,
        "subject": "Properties we just closed in {city}",
        "body": (
            "Hi {first_name},\n\n"
            "Quick update -- I just closed on two properties near "
            "{address} this month. Both sellers had cash in hand "
            "within 10 days.\n\n"
            "I still have capital allocated for {city} and your "
            "property is on my short list. If you've been thinking "
            "about selling, I'd love to make you a no-obligation "
            "offer.\n\n"
            "Just reply \"interested\" and I'll send a written offer "
            "within the hour.\n\n"
            "Best,\n"
            "Rich Gee\n"
            "Everlight Ventures | Private Acquisitions\n"
            "rich@everlightventures.io"
        ),
    },
    4: {
        "channel": "sms",
        "delay_hours": 72,
        "subject": "Re: {address}",
        "body": (
            "{first_name} -- wrapping up my {city} acquisitions this "
            "week. Still have room for {address} if you're open to it. "
            "Cash, your timeline. - Rich"
        ),
    },
    5: {
        "channel": "email",
        "delay_hours": 96,
        "subject": "Last call -- {address}",
        "body": (
            "Hi {first_name},\n\n"
            "I'm closing out my {city} property search this week. "
            "Wanted to give you one last chance to hear a cash offer "
            "for {address} before I move on.\n\n"
            "No pressure at all -- just didn't want you to miss the "
            "opportunity.\n\n"
            "Reply anytime if you'd like to revisit this down the "
            "road.\n\n"
            "Respectfully,\n"
            "Rich Gee\n"
            "Everlight Ventures\n\n"
            "Reply STOP to opt out."
        ),
    },
    6: {
        "channel": "sms",
        "delay_hours": 120,
        "subject": "Last note -- {address}",
        "body": (
            "{first_name}, closing my file on {address}. If you ever "
            "want a cash offer, I'm here -- rich@everlightventures.io. "
            "Best of luck. - Rich"
        ),
    },
}

BELFORT_ANGLE_MARKET_UPDATE = {
    0: {
        "channel": "sms",
        "delay_hours": 0,
        "subject": "{address}",
        "body": (
            "Hey {first_name}, property values in {zip_code} have "
            "shifted since we last connected. Wanted to see if an "
            "updated cash offer might interest you for {address}."
        ),
    },
    1: {
        "channel": "email",
        "delay_hours": 4,
        "subject": "Market update for {address}",
        "body": (
            "Hi {first_name},\n\n"
            "I wanted to reach out because property values in your "
            "area ({zip_code}) have changed recently. Based on updated "
            "comps, your property at {address} may be worth more than "
            "when we last spoke.\n\n"
            "If you'd like to hear what a current cash offer looks "
            "like, I'm happy to run the numbers and send you a "
            "no-obligation figure.\n\n"
            "Here's what hasn't changed:\n"
            "  - All cash, no financing delays\n"
            "  - Close on your timeline\n"
            "  - As-is condition, no repairs\n"
            "  - I cover closing costs\n\n"
            "Just reply and I'll have an updated offer for you "
            "within 24 hours.\n\n"
            "Best,\n"
            "Rich Gee\n"
            "Everlight Ventures | Private Acquisitions\n"
            "rich@everlightventures.io\n\n"
            "Not interested? Reply STOP and I will remove you immediately."
        ),
    },
    2: {
        "channel": "sms",
        "delay_hours": 24,
        "subject": "Re: {address}",
        "body": (
            "Hey {first_name}, sent you a market update on {address} "
            "yesterday. Comparable sales in {zip_code} have moved. "
            "Worth a quick look? - Rich"
        ),
    },
    3: {
        "channel": "email",
        "delay_hours": 48,
        "subject": "Recent sales near {address}",
        "body": (
            "Hi {first_name},\n\n"
            "I've been tracking sales in {zip_code} closely. Several "
            "properties near {address} have sold recently, and the "
            "numbers are looking favorable for sellers.\n\n"
            "I've already done the comp analysis on your property. "
            "If you're curious what it could fetch in a private cash "
            "sale, just reply and I'll share what I found.\n\n"
            "No obligation, no pressure -- just data.\n\n"
            "Best,\n"
            "Rich Gee\n"
            "Everlight Ventures | Private Acquisitions\n"
            "rich@everlightventures.io"
        ),
    },
    4: {
        "channel": "sms",
        "delay_hours": 72,
        "subject": "Re: {address}",
        "body": (
            "{first_name} -- market window for {zip_code} is open "
            "right now. I've got updated numbers for {address} if "
            "you want to see them. No strings. - Rich"
        ),
    },
    5: {
        "channel": "email",
        "delay_hours": 96,
        "subject": "Closing out -- {address} market review",
        "body": (
            "Hi {first_name},\n\n"
            "This is my last note about the market update for "
            "{address}.\n\n"
            "Property values shift, and I wanted to make sure you "
            "had the latest information before I close this review. "
            "If selling is something you'd consider -- even down the "
            "road -- just reply and I'll keep your property flagged "
            "for future updates.\n\n"
            "Otherwise, no worries at all. Wishing you well.\n\n"
            "Respectfully,\n"
            "Rich Gee\n"
            "Everlight Ventures\n\n"
            "Reply STOP to opt out."
        ),
    },
    6: {
        "channel": "sms",
        "delay_hours": 120,
        "subject": "Last note -- {address}",
        "body": (
            "{first_name}, wrapping up my market review for "
            "{zip_code}. Door's always open if you want an updated "
            "offer -- rich@everlightventures.io. All the best. - Rich"
        ),
    },
}


def get_angle_touches(recycle_angle: str) -> dict:
    """Return the Belfort touch sequence dict for a given angle."""
    if recycle_angle == "new_investor":
        return BELFORT_ANGLE_NEW_INVESTOR
    if recycle_angle == "market_update":
        return BELFORT_ANGLE_MARKET_UPDATE
    # "standard" or unknown -- caller should use the default BELFORT_TOUCHES
    return {}


# ---------------------------------------------------------------------------
# RECYCLER LOGIC
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime:
    """Parse an ISO date string or YYYY-MM-DD into a UTC datetime."""
    if not date_str:
        raise ValueError("empty date string")
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _days_since(date_str: str) -> int:
    """Return the number of days since the given date string."""
    try:
        dt = _parse_date(date_str)
        return (NOW - dt).days
    except (ValueError, TypeError):
        return 0


def recycle_leads() -> dict:
    """
    Scan leads_db.json and recycle eligible dead/cooling_off leads.

    Returns stats dict with counts of recycled, permanently_dead, etc.
    """
    if not LEADS_DB.exists():
        log.warning("No leads_db.json found -- nothing to recycle")
        return {"recycled": 0, "permanently_dead": 0, "cooling_reactivated": 0}

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Failed to read leads_db.json: {exc}")
        return {"recycled": 0, "permanently_dead": 0, "cooling_reactivated": 0}

    # Load suppression list to skip opted-out leads
    from rex_stop_handler import is_suppressed

    recycled = 0
    permanently_dead = 0
    cooling_reactivated = 0

    for lead in leads:
        status = lead.get("status", "")
        email = lead.get("owner_email", "")

        # Never recycle suppressed leads
        if is_suppressed(email):
            if status not in ("opted_out", "permanently_dead"):
                lead["status"] = "opted_out"
            continue

        # Handle cooling_off leads
        if status == "cooling_off":
            cooling_until = lead.get("cooling_until", "")
            if cooling_until:
                try:
                    cool_dt = _parse_date(cooling_until)
                    if NOW >= cool_dt:
                        lead["status"] = "new"
                        lead["sequence_step"] = 0
                        lead["last_outreach"] = ""
                        cooling_reactivated += 1
                        log.info(
                            f"Cooling-off reactivated: "
                            f"{lead.get('owner_name', '?')} "
                            f"({lead.get('address', '?')})"
                        )
                except (ValueError, TypeError):
                    pass
            continue

        # Handle dead leads
        if status != "dead":
            continue

        recycle_count = lead.get("recycle_count", 0)

        # Already maxed out recycles
        if recycle_count >= MAX_RECYCLES:
            if status != "permanently_dead":
                lead["status"] = "permanently_dead"
                lead["permanently_dead_at"] = NOW.isoformat()
                permanently_dead += 1
                log.info(
                    f"Permanently dead (3 recycles exhausted): "
                    f"{lead.get('owner_name', '?')} "
                    f"({lead.get('address', '?')})"
                )
            continue

        # Check if enough time has passed
        dead_since = lead.get("last_outreach", lead.get("created_at", ""))
        days_dead = _days_since(dead_since)
        required_days = RECYCLE_THRESHOLDS.get(recycle_count, 999)

        if days_dead < required_days:
            continue

        # Recycle this lead
        new_count = recycle_count + 1
        new_angle = ANGLE_MAP.get(new_count, "standard")

        lead["status"] = "new"
        lead["sequence_step"] = 0
        lead["last_outreach"] = ""
        lead["recycle_count"] = new_count
        lead["recycle_angle"] = new_angle
        lead["recycled_at"] = NOW.isoformat()
        recycled += 1

        log.info(
            f"Recycled (count={new_count}, angle={new_angle}): "
            f"{lead.get('owner_name', '?')} "
            f"({lead.get('address', '?')}) -- "
            f"dead {days_dead} days"
        )

    # Save
    with open(LEADS_DB, "w") as f:
        json.dump(leads, f, indent=2, default=str)

    stats = {
        "recycled": recycled,
        "permanently_dead": permanently_dead,
        "cooling_reactivated": cooling_reactivated,
    }

    log.info(
        f"Recycle run complete: {recycled} recycled, "
        f"{cooling_reactivated} cooling reactivated, "
        f"{permanently_dead} permanently dead"
    )

    # Post to Slack if anything happened
    if recycled or cooling_reactivated:
        _post_slack_summary(stats)

    return stats


def _post_slack_summary(stats: dict):
    """Post recycle summary to Slack."""
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not slack_token:
        return

    import os as _os
    text = (
        f"*Rex Lead Recycler*\n"
        f"Recycled: {stats['recycled']} leads (new messaging angle)\n"
        f"Cooling reactivated: {stats['cooling_reactivated']}\n"
        f"Permanently dead: {stats['permanently_dead']}\n"
        f"Dead leads get a second chance. Never stop following up."
    )

    try:
        import requests
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            },
            json={"channel": "C0ANLLV8JAC", "text": text},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    log.info("=== Rex Lead Recycler -- Sunday run ===")
    stats = recycle_leads()
    print(json.dumps(stats, indent=2))
