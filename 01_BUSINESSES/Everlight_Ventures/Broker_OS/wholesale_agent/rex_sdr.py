"""
Rex SDR (Sales Development Rep) -- 100+ outreach touches per day.

A real wholesale sales operation does:
- 100 cold emails per day
- Follow-up sequences (5 touches over 14 days per lead)
- Re-engage dead leads after 30 days
- Track every touch in the pipeline

Rex runs 3x per day:
  8 AM: Fresh outreach (new leads)
  12 PM: Follow-ups (day 3, 7, 10, 14 sequences)
  5 PM: Re-engagement (leads that went cold 30+ days ago)

Daily volume target: 100 emails = 50 fresh + 40 follow-ups + 10 re-engages
"""

import csv
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[Rex SDR %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_sdr")

AGENT_DIR = Path(__file__).parent
PIPELINE_DIR = AGENT_DIR / "pipeline"
OUTREACH_LOG = AGENT_DIR / "outreach_sent"
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
OUTREACH_LOG.mkdir(parents=True, exist_ok=True)

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
FROM_EMAIL = os.environ.get("SMTP_FROM", "Rich Gee <rich@everlightventures.io>")
REPLY_TO = "rich@everlightventures.io"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"

try:
    from gdocs_bridge import publish_report
except ImportError:
    publish_report = None

NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")

# Resend free tier: 100/day. Stay under cap, Gmail overflow handles the rest.
# Total target: ~90 via Resend + overflow via Gmail SMTP (500/day)
DAILY_FRESH_LIMIT = 50
DAILY_FOLLOWUP_LIMIT = 30
DAILY_REENGAGE_LIMIT = 10

# PERSISTENCE MODE: Keep going until we get a reply or close a deal.
# If no replies after a full cycle, pull more leads from ATTOM and try again.
PERSISTENCE_MODE = True


# ---------------------------------------------------------------------------
# LEAD DATABASE (JSON-based, upgrades to Supabase later)
# ---------------------------------------------------------------------------

LEADS_DB = AGENT_DIR / "leads_db.json"


def load_leads() -> list[dict]:
    if LEADS_DB.exists():
        return json.loads(LEADS_DB.read_text())
    return []


def save_leads(leads: list[dict]):
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))


def add_leads(new_leads: list[dict]):
    existing = load_leads()
    existing_addrs = {l.get("address", "").lower() for l in existing}
    added = 0
    for lead in new_leads:
        if lead.get("address", "").lower() not in existing_addrs:
            lead.setdefault("outreach_count", 0)
            lead.setdefault("last_outreach", "")
            lead.setdefault("status", "new")
            lead.setdefault("sequence_step", 0)
            lead.setdefault("created_at", TODAY)
            lead.setdefault("dead_since", "")
            existing.append(lead)
            existing_addrs.add(lead["address"].lower())
            added += 1
    save_leads(existing)
    return added


# ---------------------------------------------------------------------------
# EMAIL SEQUENCES (5-touch drip over 14 days)
# ---------------------------------------------------------------------------

# Pain-point-specific templates per lead type
PAIN_TEMPLATES = {
    "code_violation": {
        "touch1": "Hi {first_name},\n\nI noticed your property at {address}, {city} has some open code issues with the city. I know those fines add up fast and dealing with inspectors is a headache.\n\nI buy properties in {city} as-is -- code violations and all. No repairs needed on your end. I can close in 7 days with cash and the fines stop the day we close.\n\nWould it help to hear what I could offer?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up on {address}. Those city fines do not pause while you decide -- they keep adding up. I can make them stop this week.\n\nCash offer, close in 7 days, I handle everything. Just reply and I will send you a number.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast check-in about {address}. If the code situation has gotten worse, my offer still stands. I take properties as-is and close fast.\n\nIf you have already resolved it, no worries at all. Just reply either way.\n\nRich\nEverlight Ventures",
    },
    "pre_foreclosure": {
        "touch1": "Hi {first_name},\n\nI am reaching out about your property at {address}, {city}. I work with homeowners who are facing tight deadlines and need to sell quickly.\n\nI buy with cash and can close before any auction date. No inspections, no bank approval delays, no commissions. You walk away with a check and your credit intact.\n\nWould you like to hear what I can offer?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up about {address}. If your timeline is getting tight, I want you to know my cash offer can close in as little as 5 business days. That is fast enough to beat most deadlines.\n\nJust reply and I will get you a number today.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nI know this might be a stressful time. I am still able to help with {address} if you need a fast sale. No judgment, just a fair offer and a quick close.\n\nReply anytime. I check email daily.\n\nRich\nEverlight Ventures",
    },
    "tax_lien": {
        "touch1": "Hi {first_name},\n\nI am reaching out about your property at {address}, {city}. I work with property owners who have outstanding tax balances and need a clean exit.\n\nI buy as-is for cash. I handle the back taxes at closing so you walk away free and clear. No repairs, no agents, no waiting.\n\nWould you be open to a conversation?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nQuick follow-up on {address}. Back taxes keep accruing and the county does not wait. I can take this off your plate this month -- cash, fast close, I cover the taxes.\n\nJust reply if you want to hear a number.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast note about {address}. If the tax situation is weighing on you, I am still here to help. I have closed dozens of these deals and I make it simple.\n\nReply anytime.\n\nRich\nEverlight Ventures",
    },
    "probate": {
        "touch1": "Hi {first_name},\n\nI am sorry for your loss. I am reaching out about the property at {address}, {city}. I work with families who have inherited a property and want a simple, fast sale.\n\nI buy as-is for cash -- no cleaning out, no repairs, no showings. I handle everything and close on your timeline.\n\nIf that would be helpful, I would be glad to chat.\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up about {address}. I know dealing with an inherited property can be overwhelming on top of everything else. I can take it off your plate quickly and simply.\n\nNo pressure. Just reply if you want to talk options.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast note about {address}. Whenever you are ready -- whether that is now or months from now -- my offer to buy the property as-is stands. Just reply to this email.\n\nWishing you well.\n\nRich\nEverlight Ventures",
    },
    "vacant": {
        "touch1": "Hi {first_name},\n\nI noticed your property at {address}, {city} appears to be vacant. I know an empty property still costs money every month -- insurance, taxes, maintenance, liability.\n\nI buy vacant properties for cash and close fast. No repairs, no cleanup, no agents. Just a check and one less thing to worry about.\n\nWould you like to hear an offer?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up on {address}. Every month that property sits empty is another month of carrying costs with zero return. I can turn it into cash for you this month.\n\nJust reply and I will send a number.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast check-in about {address}. If you have plans for the property, great. If not, my cash offer still stands. No rush, but the offer is here whenever you are ready.\n\nRich\nEverlight Ventures",
    },
    "absentee": {
        "touch1": "Hi {first_name},\n\nI am reaching out about your property at {address}, {city}. Managing a property from a distance is not easy -- tenant issues, repair calls, finding contractors you trust from far away.\n\nI buy rental properties for cash, as-is. No fixing up, no vacancy risk, no more late-night calls. Just a clean sale and a check.\n\nWould that be worth a conversation?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up on {address}. If managing that property remotely has become more trouble than it is worth, I can take it off your hands quickly. Cash, as-is, I handle the paperwork.\n\nJust reply.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast note about {address}. If you ever decide to sell, I am still buying in {city} and can move fast. Just reply to this email anytime.\n\nRich\nEverlight Ventures",
    },
    "divorce": {
        "touch1": "Hi {first_name},\n\nI understand you may need to sell the property at {address}, {city} quickly. I specialize in fast, clean closings -- cash, no contingencies, close in 7-14 days.\n\nIf a quick sale would help simplify things, I would be happy to make an offer.\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up on {address}. I can close fast and keep things simple. Cash offer, no showings, no drawn-out process. Reply if you want a number.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast note about {address}. My offer stands whenever you are ready. Reply anytime.\n\nRich\nEverlight Ventures",
    },
    "expired_listing": {
        "touch1": "Hi {first_name},\n\nI saw that your property at {address}, {city} was on the market recently but did not sell. That is frustrating -- especially after months of showings and waiting.\n\nI am a different kind of buyer. I pay cash, close in 7-14 days, and buy as-is. No more showings, no more waiting, no more agent fees.\n\nWant to hear what I would offer?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
        "touch2": "Hi {first_name},\n\nFollowing up on {address}. The market did not deliver at list price, but that does not mean the property is not valuable. I am a cash buyer and I see the potential.\n\nReply and I will send you a number today.\n\nRich\nEverlight Ventures",
        "touch3": "Hi {first_name},\n\nLast check-in about {address}. If you relist it, great. If you want a fast cash sale instead, my offer is here. Just reply.\n\nRich\nEverlight Ventures",
    },
}

# Default templates for lead types not in the pain library
DEFAULT_TEMPLATES = {
    "touch1": "Hi {first_name},\n\nI am reaching out about your property at {address}, {city}, {state}. I buy properties for cash and can close in 7-14 days -- no repairs, no commissions, no hassle.\n\nWould you be open to hearing an offer?\n\nRich\nEverlight Ventures\nrich@everlightventures.io",
    "touch2": "Hi {first_name},\n\nFollowing up on my note about {address}. I am still interested in making a cash offer if you are open to it.\n\nNo pressure -- just reply whenever works.\n\nRich\nEverlight Ventures",
    "touch3": "Hi {first_name},\n\nLast check-in about {address}. Cash offer still stands. Reply anytime.\n\nRich\nEverlight Ventures",
}


def get_pain_template(lead_type: str, touch: int) -> str:
    """Get the right template based on lead type and touch number."""
    templates = PAIN_TEMPLATES.get(lead_type, DEFAULT_TEMPLATES)
    if touch <= 1:
        return templates.get("touch1", DEFAULT_TEMPLATES["touch1"])
    elif touch <= 3:
        return templates.get("touch2", DEFAULT_TEMPLATES["touch2"])
    else:
        return templates.get("touch3", DEFAULT_TEMPLATES["touch3"])


# Build SEQUENCE from pain templates (backward compatible with the SDR runner)
SEQUENCE = [
    {"step": 1, "day": 0, "subject": "Cash offer for {address}", "templates": ["PAIN_AWARE"]},
    {"step": 2, "day": 3, "subject": "Quick follow-up -- {address}", "templates": ["PAIN_AWARE"]},
    {"step": 3, "day": 7, "subject": "Still interested in {address}", "templates": ["PAIN_AWARE"]},
    {"step": 4, "day": 10, "subject": "Last note -- {address}", "templates": ["PAIN_AWARE"]},
    {"step": 5, "day": 14, "subject": "Closing the loop on {address}", "templates": ["PAIN_AWARE"]},
]

REENGAGE_TEMPLATES = ["PAIN_AWARE"]


# ---------------------------------------------------------------------------
# EMAIL SENDER
# ---------------------------------------------------------------------------

_resend_sent_today = 0
_mx_cache = {}

def _verify_mx(email_addr: str) -> bool:
    """Check if domain has valid MX records before wasting a send."""
    domain = email_addr.split("@")[-1].lower()
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        import subprocess, socket
        result = subprocess.run(["host", "-t", "MX", domain], capture_output=True, text=True, timeout=5)
        valid = "mail" in result.stdout.lower() or "mx" in result.stdout.lower()
        if not valid:
            socket.getaddrinfo(domain, 25, socket.AF_INET)
            valid = True
    except:
        valid = False
    _mx_cache[domain] = valid
    return valid

def send_email(to: str, subject: str, body: str) -> bool:
    """Send via Resend first. If quota exceeded, overflow to Gmail SMTP. $0 = 600/day."""
    global _resend_sent_today
    if not to:
        return False

    if not _verify_mx(to):
        return False

    # Try Resend first (100/day free tier)
    if RESEND_KEY and _resend_sent_today < 95:
        try:
            import requests
            resp = requests.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [to], "subject": subject, "text": body, "reply_to": REPLY_TO},
                timeout=10)
            if resp.status_code in (200, 201):
                _resend_sent_today += 1
                return True
            elif resp.status_code == 429 or "rate" in resp.text.lower() or "quota" in resp.text.lower():
                _resend_sent_today = 100  # force overflow to Gmail
            else:
                return False
        except Exception:
            pass

    # Overflow: Gmail SMTP (500/day free)
    gmail_user = os.environ.get("IMAP_USER", "")
    gmail_pass = os.environ.get("IMAP_PASS", "")
    if gmail_user and gmail_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = to
            msg["Reply-To"] = REPLY_TO
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)
            return True
        except Exception:
            return False

    return False


def personalize(template: str, lead: dict) -> str:
    """Fill in template variables. If template is PAIN_AWARE, select based on lead_type."""
    if template == "PAIN_AWARE":
        lead_type = lead.get("lead_type", "")
        step = lead.get("sequence_step", 0) + 1
        template = get_pain_template(lead_type, step)

    owner = lead.get("owner_name", "")
    first_name = owner.split()[0] if owner else "there"
    return template.format(
        first_name=first_name,
        address=lead.get("address", "your property"),
        city=lead.get("city", "the area"),
        state=lead.get("state", ""),
    )


# ---------------------------------------------------------------------------
# SDR RUNS
# ---------------------------------------------------------------------------

def run_fresh_outreach():
    """Send first-touch emails to new leads. Target: 50/day."""
    log.info("=== FRESH OUTREACH ===")
    leads = load_leads()
    new_leads = [l for l in leads if l["status"] == "new" and l.get("owner_email")]
    random.shuffle(new_leads)

    sent = 0
    for lead in new_leads[:DAILY_FRESH_LIMIT]:
        seq = SEQUENCE[0]
        template = random.choice(seq["templates"])
        body = personalize(template, lead)
        subject = personalize(seq["subject"], lead)

        if send_email(lead["owner_email"], subject, body):
            lead["status"] = "contacted"
            lead["outreach_count"] = 1
            lead["sequence_step"] = 1
            lead["last_outreach"] = TODAY
            sent += 1
            # Rate limit: 1 email per 2 seconds to avoid spam flags
            time.sleep(2)

    save_leads(leads)
    log.info(f"Sent {sent} fresh outreach emails")
    return sent


def run_followups():
    """Send follow-up emails based on sequence timing. Target: 40/day."""
    log.info("=== FOLLOW-UPS ===")
    leads = load_leads()
    sent = 0

    for lead in leads:
        if sent >= DAILY_FOLLOWUP_LIMIT:
            break
        if lead["status"] not in ("contacted", "followed_up"):
            continue
        if not lead.get("owner_email"):
            continue

        current_step = lead.get("sequence_step", 1)
        last_outreach = lead.get("last_outreach", "")
        if not last_outreach:
            continue

        # Find next sequence step
        next_seq = None
        for seq in SEQUENCE:
            if seq["step"] == current_step + 1:
                next_seq = seq
                break

        if not next_seq:
            # Finished all 5 steps -- mark as exhausted
            lead["status"] = "sequence_complete"
            continue

        # Check if enough days have passed
        try:
            last_date = datetime.strptime(last_outreach, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since = (NOW - last_date).days
        except ValueError:
            continue

        days_needed = next_seq["day"] - SEQUENCE[current_step - 1]["day"]
        if days_since < days_needed:
            continue

        # Send follow-up
        template = random.choice(next_seq["templates"])
        body = personalize(template, lead)
        subject = personalize(next_seq["subject"], lead)

        if send_email(lead["owner_email"], subject, body):
            lead["outreach_count"] = lead.get("outreach_count", 0) + 1
            lead["sequence_step"] = next_seq["step"]
            lead["last_outreach"] = TODAY
            lead["status"] = "followed_up"
            sent += 1
            time.sleep(2)

    save_leads(leads)
    log.info(f"Sent {sent} follow-up emails")
    return sent


def run_reengagement():
    """Re-engage leads that completed the sequence 30+ days ago. Target: 10/day."""
    log.info("=== RE-ENGAGEMENT ===")
    leads = load_leads()
    sent = 0

    for lead in leads:
        if sent >= DAILY_REENGAGE_LIMIT:
            break
        if lead["status"] != "sequence_complete":
            continue
        if not lead.get("owner_email"):
            continue

        last_outreach = lead.get("last_outreach", "")
        if not last_outreach:
            continue

        try:
            last_date = datetime.strptime(last_outreach, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since = (NOW - last_date).days
        except ValueError:
            continue

        if days_since < 30:
            continue

        template = random.choice(REENGAGE_TEMPLATES)
        body = personalize(template, lead)
        subject = f"Checking in -- {lead.get('address', 'your property')}"

        if send_email(lead["owner_email"], subject, body):
            lead["outreach_count"] = lead.get("outreach_count", 0) + 1
            lead["last_outreach"] = TODAY
            lead["status"] = "reengaged"
            lead["sequence_step"] = 1  # restart sequence
            sent += 1
            time.sleep(2)

    save_leads(leads)
    log.info(f"Sent {sent} re-engagement emails")
    return sent


def post_slack_summary(fresh: int, followups: int, reengages: int):
    leads = load_leads()
    total = len(leads)
    with_email = sum(1 for l in leads if l.get("owner_email"))
    active = sum(1 for l in leads if l["status"] in ("contacted", "followed_up", "reengaged"))

    msg = (
        f"*Rex SDR Daily Summary -- {TODAY}*\n"
        f"Emails sent today: {fresh + followups + reengages}\n"
        f"  Fresh outreach: {fresh}\n"
        f"  Follow-ups: {followups}\n"
        f"  Re-engagements: {reengages}\n\n"
        f"Pipeline: {total} total leads | {with_email} with email | {active} active conversations"
    )
    # Try branded GDoc first
    if publish_report is not None:
        try:
            result = publish_report(
                title="Rex SDR Daily Summary",
                content=msg,
                folder="01_Broker_OS/Outreach_Logs",
                summary=msg[:200],
                agent="piper_reeves",
            )
            if result.get("ok"):
                return
        except Exception:
            pass
    # Fallback: raw text post
    if not SLACK_TOKEN:
        return
    import requests
    requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_CHANNEL, "text": msg}, timeout=10)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_sdr_cycle(mode: str = "all"):
    """
    Run Rex's SDR cycle.
    mode: "fresh" (8 AM), "followup" (12 PM), "reengage" (5 PM), "all"
    """
    log.info(f"Rex SDR starting -- mode: {mode}")

    fresh = followups = reengages = 0

    if mode in ("fresh", "all"):
        fresh = run_fresh_outreach()
    if mode in ("followup", "all"):
        followups = run_followups()
    if mode in ("reengage", "all"):
        reengages = run_reengagement()

    total = fresh + followups + reengages
    log.info(f"Rex SDR complete -- {total} emails sent today")

    if mode == "all" or mode == "reengage":
        post_slack_summary(fresh, followups, reengages)

    return total


def check_for_deals() -> bool:
    """Check if we have any active deals or replies. Returns True if deal found."""
    deals_dir = AGENT_DIR / "active_deals"
    if deals_dir.exists():
        deals = list(deals_dir.glob("*.json"))
        if deals:
            return True
    # Check if any leads have replied
    leads = load_leads()
    replied = [l for l in leads if l.get("status") in ("replied", "negotiating", "under_contract", "closed")]
    return len(replied) > 0


def auto_refill_pipeline():
    """If pipeline is running low, pull more ATTOM leads, skip trace, convert phones to SMS.
    Rex makes his own decisions -- no human input needed."""
    import subprocess, requests, re as refill_re

    leads = load_leads()
    unsent = [l for l in leads if l.get("outreach_count", 0) == 0 and l.get("owner_email")]

    if len(unsent) >= 40:
        log.info(f"Pipeline healthy ({len(unsent)} unsent). No refill needed.")
        return

    log.info(f"Pipeline low ({len(unsent)} unsent). Auto-refilling...")

    ATTOM_KEY = os.environ.get("ATTOM_API_KEY", "")
    PPLX_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

    if not ATTOM_KEY:
        log.warning("No ATTOM key -- can't refill")
        return

    # Step 1: Pull properties -- PRIORITIZE Opportunity Zone zips (higher buyer demand)
    import random, time
    oz_zips = ["30310","30311","30314","30315","30318","30354",  # Atlanta OZ
               "44102","44103","44104","44105","44106","44108","44109","44110","44113","44115",  # Cleveland OZ
               "63106","63107","63112","63113","63115","63116","63118","63120",  # St. Louis OZ
               "32202","32204","32205","32206","32207","32208","32209","32210","32211"]  # Jacksonville OZ
    non_oz = ["75203","75215","75216","75217","75227",  # Dallas (no OZ data)
              "30305","30306","30307","30316","30317"]  # Atlanta non-OZ
    # OZ zips first (70%), then non-OZ (30%)
    all_zips = oz_zips + non_oz
    random.shuffle(oz_zips)
    random.shuffle(non_oz)
    all_zips = oz_zips[:15] + non_oz[:5]  # 75% OZ priority

    new_leads = []
    headers = {"apikey": ATTOM_KEY, "Accept": "application/json"}
    for zc in all_zips[:20]:
        try:
            r = requests.get(f"https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/basicprofile?postalcode={zc}&pagesize=10",
                headers=headers, timeout=15)
            if r.status_code == 200:
                for p in r.json().get("property", []):
                    addr = p.get("address", {}).get("oneLine", "")
                    name = ((p.get("assessment", {}).get("owner", {}) or {}).get("owner1", {}) or {}).get("fullName", "")
                    if addr and name and not refill_re.search(r'\b(LLC|INC|CORP|TRUST|BANK|CITY OF)\b', name.upper()):
                        new_leads.append({"address": addr, "owner_name": name,
                            "city": p.get("address", {}).get("locality", ""),
                            "state": p.get("address", {}).get("countrySubd", ""),
                            "zip_code": zc, "owner_phone": "", "owner_email": ""})
            time.sleep(0.5)
        except:
            pass

    log.info(f"Pulled {len(new_leads)} new properties from ATTOM")

    # Step 2: Skip trace for phones via Perplexity
    if PPLX_KEY and new_leads:
        found = 0
        for lead in new_leads:
            try:
                r = requests.post("https://api.perplexity.ai/chat/completions",
                    headers={"Authorization": f"Bearer {PPLX_KEY}", "Content-Type": "application/json"},
                    json={"model": "sonar", "max_tokens": 100, "temperature": 0.1,
                        "messages": [{"role": "system", "content": "Find phone. Return ONLY phone number or say not found."},
                            {"role": "user", "content": f"{lead['owner_name']}, {lead['city']}, {lead['state']}. Phone?"}]},
                    timeout=15)
                if r.status_code == 200:
                    answer = r.json()["choices"][0]["message"]["content"]
                    phones = refill_re.findall(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', answer)
                    if phones:
                        lead["owner_phone"] = phones[0]
                        found += 1
                time.sleep(0.3)
            except:
                pass
        log.info(f"Skip traced: {found} phones found from {len(new_leads)} lookups")

    # Step 3: Convert phones to SMS gateway emails + add to pipeline
    sms_gateways = [("{phone}@txt.att.net", "att"), ("{phone}@vtext.com", "verizon"), ("{phone}@tmomail.net", "tmobile")]
    existing_addrs = {l.get("address", "").upper() + "|" + l.get("owner_email", "").lower() for l in leads}

    added = 0
    for lead in new_leads:
        if lead.get("owner_phone"):
            phone = refill_re.sub(r'\D', '', lead["owner_phone"])
            if len(phone) == 11 and phone.startswith("1"):
                phone = phone[1:]
            if len(phone) == 10:
                # SMS GATEWAYS DISABLED (TCPA)
            # for template, carrier in sms_gateways:
                    sms_email = template.format(phone=phone)
                    key = f"{lead['address'].upper()}|{sms_email.lower()}"
                    if key not in existing_addrs:
                        leads.append({**lead, "owner_email": sms_email, "source": f"refill_sms_{carrier}",
                            "status": "new", "outreach_count": 0, "sequence_step": 0, "created_at": TODAY})
                        existing_addrs.add(key)
                        added += 1

    save_leads(leads)
    log.info(f"Refill complete: {added} new SMS leads added to pipeline")


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if PERSISTENCE_MODE and mode == "all":
        # PERSISTENCE MODE: keep grinding until we get a deal
        if check_for_deals():
            log.info("DEAL FOUND -- persistence mode satisfied. Running normal cycle.")
            run_sdr_cycle(mode)
        else:
            log.info("NO DEALS YET -- persistence mode active. Maximizing outreach.")
            # Check if pipeline needs refill
            auto_refill_pipeline()
            # Run full cycle
            total = run_sdr_cycle(mode)
            if total == 0:
                log.info("No emails sent (pipeline empty or all contacted). Triggering refill for next run.")
                auto_refill_pipeline()
    else:
        run_sdr_cycle(mode)
