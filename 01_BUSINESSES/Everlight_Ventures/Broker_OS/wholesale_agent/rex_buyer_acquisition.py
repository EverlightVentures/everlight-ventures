"""
Rex Buyer Acquisition -- builds the investor list automatically.

Strategy: find PROVEN cash buyers from public county deed records,
then cold email them with a premium institutional pitch.

These are people who already closed cash deals in the last 90 days.
They are real. They have money. They want more deals.

Rex finds them, emails them, and builds the buyer list without
any manual work from you.

Sources (all free, public record):
1. County deed records -- search recent sales with no mortgage = cash buyer
2. County assessor records -- grantee names on recent transfers
3. Google "[investor company name] [city] real estate" for email
4. Skip trace the buyer name via TruePeopleSearch for email

The pitch is NOT "we buy houses" energy.
The pitch is: "Everlight sources institutional-grade off-market properties.
We screen thousands. You see the top 1%."
"""

# (eradication halt block removed after canonical-migration; safe_send_email is now the only send path and it carries the halt + gate internally)

import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[Rex Buyers %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_buyers")

AGENT_DIR = Path(__file__).parent
BUYERS_DIR = AGENT_DIR / "buyer_outreach"
BUYERS_DIR.mkdir(parents=True, exist_ok=True)

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "Harrison Knox <hammer@everlightventures.io>")
REPLY_TO = "hammer@everlightventures.io"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Where to find cash buyers (county recorder search URLs)
CASH_BUYER_SOURCES = {
    "atlanta": {
        "name": "Fulton County, GA",
        "deed_search": "https://www.fultoncountyga.gov/services/clerk-of-superior-court",
        "assessor": "https://www.qpublic.net/ga/fulton/",
        "how": "Search 'Warranty Deed' filings, last 90 days. Cross-reference against mortgage recordings. If no mortgage was filed on the same property within 30 days of deed, it was a cash purchase. The grantee is your cash buyer.",
    },
    "dallas": {
        "name": "Dallas County, TX",
        "deed_search": "https://www.dallascounty.org/departments/countyclerk/",
        "assessor": "https://www.dallascad.org/",
        "how": "Search 'Deed' instruments, last 90 days. Filter for properties under $300k. Look for LLCs and company names -- those are investors. Individual names buying properties they do not live in = absentee investors.",
    },
    "cleveland": {
        "name": "Cuyahoga County, OH",
        "deed_search": "https://recorder.cuyahogacounty.us/",
        "assessor": "https://myplace.cuyahogacounty.gov/",
        "how": "Search recent deed transfers. Cleveland has heavy investor activity. Look for repeat buyers (same name/LLC buying multiple properties).",
    },
    "charlotte": {
        "name": "Mecklenburg County, NC",
        "deed_search": "https://www.mecknc.gov/CountyManagersOffice/ROD/",
        "assessor": "https://property.spatialest.com/nc/mecklenburg/",
        "how": "Search deed recordings, last 90 days. Filter for purchase price $50k-$300k with no deed of trust filed.",
    },
    "st_louis": {
        "name": "St. Louis County, MO",
        "deed_search": "https://www.stlouisco.com/YourGovernment/CountyDepartments/Recorder",
        "assessor": "https://revenue.stlouisco.com/IAS/",
        "how": "Search warranty deeds. St. Louis has the highest avg assignment fee ($25k) -- buyers here are aggressive.",
    },
    "jacksonville": {
        "name": "Duval County, FL",
        "deed_search": "https://www2.duvalclerk.com/",
        "assessor": "https://www.coj.net/departments/property-appraiser",
        "how": "Search OR (Official Records) for 'deed' document type. Florida has strong investor activity.",
    },
}


# ---------------------------------------------------------------------------
# PREMIUM BUYER OUTREACH TEMPLATES
# ---------------------------------------------------------------------------

# These do NOT sound like a wholesaler. They sound like a private acquisitions firm.

BUYER_COLD_EMAIL_TEMPLATES = [
    {
        "subject": "Off-market deal flow -- {city} distressed properties",
        "body": """Hi {first_name},

I noticed your recent acquisition at {their_property} and wanted to introduce myself.

I run the acquisitions desk at Everlight Ventures. We screen over 2,000 distressed properties per week across 6 markets and surface the top 1% to a small group of qualified buyers.

Our current pipeline in {city}:
- {count} pre-screened off-market properties
- Average ARV discount: 30-40% below market
- All verified distress signals (code violations, pre-foreclosure, tax delinquent)
- Assignment or double close, 7-14 day turnaround

If you are actively acquiring in {city}, I would like to add you to our deal flow. No fee to receive alerts -- we earn our assignment fee only when you close.

Reply with your buy box (property types, price range, preferred areas) and I will start matching.

Rich
Everlight Ventures -- Acquisitions
hammer@everlightventures.io
everlightventures.io/wholesale""",
    },
    {
        "subject": "Qualified off-market pipeline -- {city}",
        "body": """Hi {first_name},

I source off-market distressed properties in {city} for a select group of cash buyers. Our AI screens county records daily for code violations, lis pendens, and tax delinquent properties, then ranks them by investment potential.

I saw you recently closed on {their_property} and thought our pipeline might be a fit.

What we deliver:
- Pre-screened deals with verified ARV and repair estimates
- Owner contact already made -- properties are under or near contract
- Assignment structure, clean title, fast close

No cost to receive deal alerts. We only earn when you close.

Interested? Reply with your criteria and I will get you on the list.

Rich
Everlight Ventures
hammer@everlightventures.io""",
    },
    {
        "subject": "Private deal flow for {city} investors",
        "body": """{first_name},

Quick note -- I run acquisitions at Everlight Ventures and we are expanding our buyer network in {city}.

We source 50+ off-market distressed properties per week (code violations, pre-foreclosures, estate sales) and match them to qualified cash buyers. Our system uses AI scoring to surface only the deals with real spread.

Saw your name on a recent deed recording and thought you might be a good fit.

If you are buying in {city}, reply with your buy box and I will start sending deals your way. No strings.

Rich
Everlight Ventures
everlightventures.io/wholesale""",
    },
]

BUYER_FOLLOWUP_TEMPLATES = [
    {
        "subject": "Re: Off-market deals in {city}",
        "body": """Hi {first_name},

Following up on my note about our {city} deal pipeline. We just locked up {hot_count} new properties this week and are looking for qualified buyers.

If you are actively acquiring, I would love to include you. Just reply with your criteria.

Rich
Everlight Ventures""",
    },
]


# ---------------------------------------------------------------------------
# BUYER DATABASE
# ---------------------------------------------------------------------------

BUYERS_DB = AGENT_DIR / "buyers_db.json"


def load_buyers() -> list[dict]:
    if BUYERS_DB.exists():
        return json.loads(BUYERS_DB.read_text())
    return []


def save_buyers(buyers: list[dict]):
    BUYERS_DB.write_text(json.dumps(buyers, indent=2, default=str))


def add_buyer_leads(new_buyers: list[dict]) -> int:
    existing = load_buyers()
    existing_emails = {b.get("email", "").lower() for b in existing}
    added = 0
    for buyer in new_buyers:
        email = buyer.get("email", "").lower()
        if email and email not in existing_emails:
            buyer.setdefault("status", "new")
            buyer.setdefault("outreach_count", 0)
            buyer.setdefault("last_outreach", "")
            buyer.setdefault("responded", False)
            buyer.setdefault("on_deal_list", False)
            buyer.setdefault("created_at", TODAY)
            existing.append(buyer)
            existing_emails.add(email)
            added += 1
    save_buyers(existing)
    return added


def push_buyer_to_supabase(buyer: dict) -> bool:
    """Push a confirmed buyer to Supabase investor_buyers table."""
    try:
        import requests
        supabase_url = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not service_key:
            return False

        resp = requests.post(
            f"{supabase_url}/rest/v1/investor_buyers",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={
                "name": buyer.get("name", ""),
                "email": buyer.get("email", ""),
                "company": buyer.get("company", ""),
                "buyer_type": buyer.get("buyer_type", "fix_flip"),
                "markets": buyer.get("markets", []),
                "cash_buyer": True,
                "source": "rex_outreach",
            },
            timeout=10,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SEND BUYER OUTREACH
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> bool:
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


def outreach_to_buyers(max_per_run: int = 20):
    """Send premium cold emails to uncontacted cash buyers."""
    buyers = load_buyers()
    new_buyers = [b for b in buyers if b["status"] == "new" and b.get("email")]
    random.shuffle(new_buyers)

    sent = 0
    for buyer in new_buyers[:max_per_run]:
        template = random.choice(BUYER_COLD_EMAIL_TEMPLATES)
        first_name = buyer.get("name", "").split()[0] if buyer.get("name") else "there"

        subject = template["subject"].format(
            city=buyer.get("market", buyer.get("city", "your market")),
            first_name=first_name,
        )
        body = template["body"].format(
            first_name=first_name,
            city=buyer.get("market", buyer.get("city", "your market")),
            their_property=buyer.get("recent_purchase", "a recent property"),
            count=random.randint(8, 15),
            hot_count=random.randint(3, 7),
        )

        if send_email(buyer["email"], subject, body):
            buyer["status"] = "contacted"
            buyer["outreach_count"] = 1
            buyer["last_outreach"] = TODAY
            sent += 1
            time.sleep(2)

    save_buyers(buyers)
    log.info(f"Sent {sent} buyer outreach emails")
    return sent


def handle_buyer_reply(buyer_email: str, reply_text: str):
    """Process a buyer's reply -- add them to the deal list."""
    buyers = load_buyers()
    for buyer in buyers:
        if buyer.get("email", "").lower() == buyer_email.lower():
            buyer["responded"] = True
            buyer["on_deal_list"] = True
            buyer["status"] = "qualified"
            buyer["buy_box"] = reply_text[:500]

            # Push to Supabase so they get deal blasts
            push_buyer_to_supabase(buyer)

            log.info(f"Buyer qualified: {buyer.get('name', buyer_email)}")

            # Notify Slack
            if SLACK_TOKEN:
                import requests
                requests.post("https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
                    json={"channel": SLACK_CHANNEL, "text": f"*New qualified buyer:* {buyer.get('name', buyer_email)}\nMarket: {buyer.get('market', '?')}\nBuy box: {reply_text[:200]}"}, timeout=10)
            break

    save_buyers(buyers)


# ---------------------------------------------------------------------------
# IMPORT BUYERS FROM COUNTY RECORDS (manual CSV for now)
# ---------------------------------------------------------------------------

def import_buyer_csv(csv_path: str) -> int:
    """
    Import cash buyers from a CSV.
    Expected columns: name, email, company, market, recent_purchase, buyer_type
    """
    import csv
    new_buyers = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email"):
                new_buyers.append({
                    "name": row.get("name", ""),
                    "email": row["email"].strip(),
                    "company": row.get("company", ""),
                    "market": row.get("market", row.get("city", "")),
                    "recent_purchase": row.get("recent_purchase", row.get("address", "")),
                    "buyer_type": row.get("buyer_type", "fix_flip"),
                    "markets": [row.get("market", "")] if row.get("market") else [],
                })
    return add_buyer_leads(new_buyers)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_buyer_outreach():
    log.info(f"=== Rex Buyer Acquisition -- {TODAY} ===")

    buyers = load_buyers()
    total = len(buyers)
    qualified = sum(1 for b in buyers if b.get("on_deal_list"))
    new = sum(1 for b in buyers if b["status"] == "new")

    log.info(f"Buyer pipeline: {total} total | {qualified} qualified | {new} unsent")

    if new > 0:
        sent = outreach_to_buyers(max_per_run=40)
        log.info(f"Sent {sent} premium outreach emails to cash buyers")
    else:
        log.info("No new buyers to contact -- need more leads from county records")

    # Post summary
    if SLACK_TOKEN:
        import requests
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
            json={"channel": SLACK_CHANNEL, "text": f"*Rex Buyer Pipeline -- {TODAY}*\n{total} buyers tracked | {qualified} qualified | {new} in queue"}, timeout=10)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "import":
        csv_path = sys.argv[2] if len(sys.argv) > 2 else ""
        if csv_path:
            added = import_buyer_csv(csv_path)
            print(f"Imported {added} buyers")
        else:
            print("Usage: python rex_buyer_acquisition.py import buyers.csv")
    else:
        run_buyer_outreach()
