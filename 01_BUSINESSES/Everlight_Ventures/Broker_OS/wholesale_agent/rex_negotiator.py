"""
Rex's AI Negotiation Engine -- handles seller conversations autonomously.

Rex communicates via email (Resend) and monitors replies via IMAP.
He uses Claude to craft responses, handle objections, and negotiate price.
He only pings you on Slack when he needs deal approval or signature.

Deal flow:
1. Rex sends initial outreach (personalized per property)
2. Seller replies -> Rex reads via IMAP
3. Rex uses Claude to analyze sentiment and craft response
4. Rex negotiates toward MAO, handles objections
5. When seller agrees -> Rex generates contract, pings Slack for your signature
6. After you sign -> Rex blasts to buyers, first one to send EMD gets the deal
7. Title company closes, you get wired the assignment fee

Communication channels:
- Outbound: Resend API (email from piper@everlightventures.io)
- Inbound: IMAP monitoring (reads replies)
- Internal: Slack #wholesale-deals (deal approvals only)
- AI brain: Claude API for negotiation strategy
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="[Rex %(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("rex_negotiator")

AGENT_DIR = Path(__file__).parent
DEALS_DIR = AGENT_DIR / "active_deals"
DEALS_DIR.mkdir(parents=True, exist_ok=True)

RESEND_KEY = os.environ.get("RESEND_API_KEY", os.environ.get("SMTP_PASS", ""))
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = "C0ANLLV8JAC"
FROM_EMAIL = os.environ.get("SMTP_FROM", "Marquise Reed <marquise@everlightventures.io>")
REPLY_TO = "marquise@everlightventures.io"


# ---------------------------------------------------------------------------
# DEAL STATE MACHINE
# ---------------------------------------------------------------------------

class DealState:
    def __init__(self, property_address: str, city: str, state: str):
        self.id = f"deal_{int(time.time())}_{city.lower().replace(' ','')}"
        self.address = property_address
        self.city = city
        self.state = state
        self.status = "outreach_sent"
        self.owner_name = ""
        self.owner_email = ""
        self.owner_phone = ""
        self.asking_price = 0
        self.our_mao = 0
        self.our_offer = 0
        self.arv = 0
        self.repair_estimate = 0
        self.assignment_fee = 10000
        self.conversation = []
        self.seller_sentiment = "unknown"
        self.counter_offers = []
        self.objections_handled = []
        self.buyer_name = ""
        self.buyer_price = 0
        self.buyer_emd = 0
        self.outreach_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_contact = ""

    def save(self):
        path = DEALS_DIR / f"{self.id}.json"
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2, default=str)

    @classmethod
    def load(cls, deal_id: str):
        path = DEALS_DIR / f"{deal_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        deal = cls(data["address"], data["city"], data["state"])
        deal.__dict__.update(data)
        return deal


# ---------------------------------------------------------------------------
# AI NEGOTIATION BRAIN
# ---------------------------------------------------------------------------

NEGOTIATION_SYSTEM_PROMPT = """You are Rex, a professional real estate wholesale negotiator.
You work for Everlight Ventures. You are direct, respectful, and always push for the best price.

Your rules:
- Never go above the MAO (Maximum Allowable Offer) without owner approval
- Always be honest that you intend to assign the contract
- Be empathetic but firm on price
- Handle common objections with proven scripts
- If the seller is hostile, stay calm and professional
- If the seller counters above MAO, explain your math transparently
- Your goal: get the property under contract at or below MAO

You communicate via email. Keep messages short (3-5 sentences max), professional, and warm.
Sign emails as "Everlight Ventures" (not Rex -- Rex is internal only).

Do not use buzzwords or filler. Be plain and direct."""

OBJECTION_PLAYBOOK = {
    "too_low": "I understand that might feel low. Here is how I arrived at that number -- after repairs (estimated at ${repair}), closing costs, and holding costs, ${offer} is the most I can pay and still make this work. I am happy to walk you through the math if that helps.",
    "other_offers": "That is great -- I would never want you to leave money on the table. If those offers work out, wonderful. But if they fall through or take too long, my offer stands and I can close in 7 days with cash. No inspections, no financing contingencies.",
    "not_motivated": "No pressure at all. I will keep your property in my system and if anything changes down the road -- timeline, price, situation -- just reply to this email and we can pick up where we left off.",
    "want_more_info": "Happy to share more. I am a local investor with Everlight Ventures. We buy properties as-is for cash and close quickly through a title company. No realtor commissions on your end. I can send over a proof of funds letter if that would help.",
    "suspicious": "Totally fair to be cautious. We are a registered LLC (Everlight Logistics LLC) and we work with licensed title companies for every transaction. You can verify us at everlightventures.io. The title company holds all funds in escrow -- your money is protected throughout.",
    "needs_time": "Absolutely, take the time you need. My offer is good for 7 days. After that I may need to revisit the numbers depending on market conditions, but I will always reach out before making any changes.",
    "counter_offer": "I appreciate you coming back with a number. Let me run the numbers on ${counter} and I will get back to you within 24 hours.",
}


def generate_negotiation_response(deal: DealState, seller_message: str) -> str:
    context = f"""Deal context:
- Property: {deal.address}, {deal.city}, {deal.state}
- Asking price: ${deal.asking_price:,.0f}
- Our MAO (max we can pay): ${deal.our_mao:,.0f}
- Our current offer: ${deal.our_offer:,.0f}
- ARV: ${deal.arv:,.0f}
- Estimated repairs: ${deal.repair_estimate:,.0f}
- Assignment fee target: ${deal.assignment_fee:,.0f}
- Seller name: {deal.owner_name}
- Seller sentiment: {deal.seller_sentiment}
- Objections already handled: {deal.objections_handled}

Conversation history:
"""
    for msg in deal.conversation[-6:]:
        context += f"\n[{msg['role']}]: {msg['message']}"

    context += f"\n\n[SELLER's latest message]: {seller_message}"
    context += "\n\nCraft your response. Short (3-5 sentences), professional, push toward MAO."

    try:
        import requests
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if api_key:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 500,
                    "system": NEGOTIATION_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": context}],
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["content"][0]["text"]

        import shutil
        import subprocess
        claude_bin = shutil.which("claude")
        if claude_bin:
            env = {k: v for k, v in os.environ.items()
                   if k not in ('CLAUDECODE', 'CLAUDE_CODE', 'CLAUDE_CODE_ENTRY_POINT')}
            result = subprocess.run(
                [claude_bin, "-p", "--model", "sonnet"],
                input=f"{NEGOTIATION_SYSTEM_PROMPT}\n\n{context}",
                capture_output=True, text=True, timeout=60, env=env,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

    except Exception as e:
        log.warning(f"AI response failed: {e}, using template")

    return _template_response(deal, seller_message)


def _template_response(deal: DealState, seller_message: str) -> str:
    msg_lower = seller_message.lower()

    if any(w in msg_lower for w in ["too low", "more", "higher", "not enough", "insulting"]):
        return OBJECTION_PLAYBOOK["too_low"].replace("${repair}", f"{deal.repair_estimate:,.0f}").replace("${offer}", f"{deal.our_offer:,.0f}")

    if any(w in msg_lower for w in ["other offer", "another buyer", "someone else"]):
        return OBJECTION_PLAYBOOK["other_offers"]

    if any(w in msg_lower for w in ["not interested", "not selling", "no thanks"]):
        return OBJECTION_PLAYBOOK["not_motivated"]

    if any(w in msg_lower for w in ["who are you", "scam", "legitimate", "real"]):
        return OBJECTION_PLAYBOOK["suspicious"]

    if any(w in msg_lower for w in ["think about", "need time", "talk to", "discuss"]):
        return OBJECTION_PLAYBOOK["needs_time"]

    if any(w in msg_lower for w in ["how about", "counter", "would you do", "i was thinking", "$"]):
        amounts = re.findall(r'\$?([\d,]+)', seller_message)
        if amounts:
            counter = int(amounts[0].replace(",", ""))
            deal.counter_offers.append(counter)
            if counter <= deal.our_mao:
                return f"That works for me. I can do ${counter:,}. I will have my team send over the purchase agreement today. We can close in 7-14 days through a local title company. Sound good?"
            elif counter <= deal.our_mao * 1.05:
                return f"I appreciate you working with me on this. ${counter:,} is a bit above where I need to be. Could you do ${deal.our_mao:,}? That is the highest I can go and still make the numbers work on my end."
            else:
                return OBJECTION_PLAYBOOK["counter_offer"].replace("${counter}", f"{counter:,}")

    if any(w in msg_lower for w in ["yes", "deal", "let's do it", "sounds good", "agree", "okay", "ok"]):
        return f"Wonderful -- I am excited to move forward. I will have our purchase agreement sent over today for your review. We use a licensed title company to handle the closing, so everything is protected. I will be in touch shortly with next steps."

    return f"Thank you for getting back to me about {deal.address}. I am prepared to make a cash offer of ${deal.our_offer:,.0f} and can close in as little as 7 days. No repairs needed on your end, no realtor commissions. Would that work for you?"


# ---------------------------------------------------------------------------
# EMAIL
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> bool:
    if not RESEND_KEY:
        log.warning("No RESEND_API_KEY")
        return False
    try:
        from rex_utils import safe_send_email
        return safe_send_email(to, subject, body)
    except ImportError:
        import requests
        try:
            resp = requests.post("https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [to], "subject": subject, "text": body, "reply_to": REPLY_TO},
                timeout=10)
            return resp.status_code in (200, 201)
        except Exception as e:
            log.error(f"Send failed: {e}")
            return False


def send_initial_outreach(deal: DealState) -> bool:
    subject = f"Cash offer for {deal.address}"
    body = f"""Hi {deal.owner_name.split()[0] if deal.owner_name else 'there'},

I am reaching out about your property at {deal.address}, {deal.city}, {deal.state}.

I buy properties for cash and can close in 7-14 days. No repairs, no commissions, no hassle on your end. I am prepared to make an offer of ${deal.our_offer:,.0f}.

If you are open to a quick conversation, just reply to this email.

Best,
Piper Reeves
Everlight Ventures | Wholesale
piper@everlightventures.io"""

    if send_email(deal.owner_email, subject, body):
        deal.status = "outreach_sent"
        deal.outreach_count += 1
        deal.last_contact = datetime.now(timezone.utc).isoformat()
        deal.conversation.append({"role": "rex", "message": body, "timestamp": deal.last_contact})
        deal.save()
        log.info(f"Outreach sent to {deal.owner_email} for {deal.address}")
        return True
    return False


def handle_seller_reply(deal: DealState, seller_message: str) -> str:
    deal.conversation.append({"role": "seller", "message": seller_message, "timestamp": datetime.now(timezone.utc).isoformat()})

    # Post the incoming reply to the deal thread so the owner sees it immediately.
    try:
        from deal_slack import post_touch, post_stage
        lead_like = {
            "id": getattr(deal, "id", ""),
            "owner_name": getattr(deal, "owner_name", "") or deal.owner_email.split("@")[0],
            "address": deal.address, "city": deal.city, "state": deal.state,
            "email": deal.owner_email,
            "lead_type": getattr(deal, "lead_type", "generic"),
            "detected_distress": getattr(deal, "distress", ""),
        }
        post_touch(lead=lead_like, agent="Seller", channel="reply",
                   body=seller_message, to_address=deal.owner_email,
                   outcome="received")
    except Exception:
        pass

    msg_lower = seller_message.lower()
    old_status = deal.status
    if any(w in msg_lower for w in ["yes", "deal", "agree", "let's do it", "sounds good"]):
        deal.seller_sentiment = "eager"
        deal.status = "verbal_agreement"
        alert_deal_closing(deal)
    elif any(w in msg_lower for w in ["interested", "tell me more", "how much"]):
        deal.seller_sentiment = "interested"
        deal.status = "negotiating"
    elif any(w in msg_lower for w in ["too low", "not enough", "counter"]):
        deal.seller_sentiment = "resistant"
        deal.status = "negotiating"
    elif any(w in msg_lower for w in ["not interested", "no", "stop", "remove"]):
        deal.seller_sentiment = "hostile"
        deal.status = "dead"
        deal.save()
        try:
            from deal_slack import post_stage
            post_stage(lead_like, "dead", detail=f"Seller wrote: _{seller_message[:150]}_")
        except Exception:
            pass
        return ""
    else:
        deal.seller_sentiment = "neutral"
        deal.status = "negotiating"

    response = generate_negotiation_response(deal, seller_message)
    subject = f"Re: Cash offer for {deal.address}"
    if send_email(deal.owner_email, subject, response):
        deal.conversation.append({"role": "rex", "message": response, "timestamp": datetime.now(timezone.utc).isoformat()})
        deal.last_contact = datetime.now(timezone.utc).isoformat()
        # Thread post the auto-response so the owner sees what Piper sent back.
        try:
            from deal_slack import post_touch
            post_touch(lead=lead_like, agent="Piper Reeves (auto)", channel="email",
                       subject=subject, body=response,
                       to_address=deal.owner_email, outcome="auto-reply sent")
        except Exception:
            pass
    deal.save()

    # Fire stage transition if status changed
    if old_status != deal.status:
        try:
            from deal_slack import post_stage
            post_stage(lead_like, deal.status)
        except Exception:
            pass
    return response


# ---------------------------------------------------------------------------
# SLACK ALERTS
# ---------------------------------------------------------------------------

def alert_deal_closing(deal: DealState):
    if not SLACK_TOKEN:
        log.info(f"DEAL CLOSING: {deal.address} -- seller agreed at ${deal.our_offer:,.0f}")
        return
    import requests
    msg = (
        f"*DEAL CLOSING -- Rex needs your signature*\n\n"
        f"*Property:* {deal.address}, {deal.city}, {deal.state}\n"
        f"*Seller:* {deal.owner_name} ({deal.owner_email})\n"
        f"*Our offer:* ${deal.our_offer:,.0f}\n"
        f"*ARV:* ${deal.arv:,.0f}\n"
        f"*Assignment fee:* ${deal.assignment_fee:,.0f}\n"
        f"*Seller said:* \"{deal.conversation[-1]['message'][:200]}\"\n\n"
        f"Reply *SIGN* to authorize. Deal ID: {deal.id}"
    )
    requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_CHANNEL, "text": msg}, timeout=10)


def alert_buyer_found(deal: DealState, buyer_name: str, buyer_price: float):
    if not SLACK_TOKEN:
        return
    import requests
    profit = buyer_price - deal.our_offer
    msg = (
        f"*BUYER FOUND -- assignment ready*\n\n"
        f"*Property:* {deal.address}\n"
        f"*Our price:* ${deal.our_offer:,.0f}\n"
        f"*Buyer:* {buyer_name} at ${buyer_price:,.0f}\n"
        f"*Your profit:* ${profit:,.0f}\n\n"
        f"Reply *ASSIGN* to execute."
    )
    requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_CHANNEL, "text": msg}, timeout=10)


# ---------------------------------------------------------------------------
# BUYER DISPOSITION
# ---------------------------------------------------------------------------

def blast_to_buyers(deal: DealState) -> int:
    """Email all matching investors with Ace's custom pitch -- not a generic template."""
    sent = 0
    try:
        import requests
        from ace_pitch_engine import pitch_deal

        # Generate Ace's custom pitch for this specific deal
        deal_data = {
            "address": deal.address,
            "city": deal.city,
            "state": deal.state,
            "asking_price": deal.our_offer,
            "arv": deal.arv,
            "estimated_arv": deal.arv,
            "repair_estimate": deal.repair_estimate,
            "assignment_fee": deal.assignment_fee,
            "lead_type": getattr(deal, "lead_type", "distressed"),
            "property_type": "sfr",
        }
        pitch = pitch_deal(deal_data)
        email_body = pitch["email_pitch"]

        supabase_url = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not service_key:
            return 0

        resp = requests.get(
            f"{supabase_url}/rest/v1/investor_buyers?is_active=eq.true&select=*",
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            timeout=10)

        if resp.status_code != 200:
            return 0

        buyers = resp.json()
        buyer_price = deal.our_offer + deal.assignment_fee

        for buyer in buyers:
            buyer_markets = buyer.get("markets", []) or []
            deal_market = f"{deal.city}, {deal.state}".lower()
            market_match = any(m.lower() in deal_market or deal_market in m.lower() for m in buyer_markets)
            if not market_match and buyer_markets:
                continue

            subject = f"Private deal alert: {deal.address}, {deal.city} {deal.state} -- ${buyer_price:,.0f}"
            if send_email(buyer.get("email", ""), subject, email_body):
                sent += 1

    except Exception as e:
        log.error(f"Buyer blast failed: {e}")
    return sent


# ---------------------------------------------------------------------------
# IMAP REPLY MONITOR
# ---------------------------------------------------------------------------

def check_replies() -> list[dict]:
    """Check for seller/buyer replies via IMAP with retry logic."""
    try:
        from rex_utils import safe_imap_check
        return safe_imap_check()
    except ImportError:
        pass

    # Fallback without retry
    imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    imap_user = os.environ.get("IMAP_USER", "")
    imap_pass = os.environ.get("IMAP_PASS", "")
    if not imap_user or not imap_pass:
        return []

    import imaplib
    import email as emaillib

    replies = []
    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX")
        # Search ALL unseen -- catches replies to Belfort, SDR, closer, any Rex email
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            return []

        # Load known lead emails to filter relevant replies
        leads_file = Path(__file__).parent / "leads_db.json"
        known_emails = set()
        if leads_file.exists():
            import json as jmod
            for l in jmod.loads(leads_file.read_text()):
                if l.get("owner_email"):
                    known_emails.add(l["owner_email"].lower())

        # Also load buyer emails
        buyers_file = Path(__file__).parent / "buyers_db.json"
        if buyers_file.exists():
            for b in jmod.loads(buyers_file.read_text()):
                if b.get("email"):
                    known_emails.add(b["email"].lower())

        for msg_id in messages[0].split()[-50:]:  # last 50 unseen to avoid overload
            status, data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            msg = emaillib.message_from_bytes(data[0][1])
            sender = msg["From"] or ""
            subject = msg["Subject"] or ""
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            # Filter: only process emails from known leads/buyers
            sender_email = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', sender)
            if not sender_email:
                continue
            sender_addr = sender_email.group(0).lower()
            if sender_addr not in known_emails:
                continue  # not from a lead or buyer -- skip

            # Skip spam/promo/bounce
            if any(x in sender_addr for x in ["mailer-daemon", "postmaster", "noreply", "no-reply"]):
                continue

            # Extract address from any Rex subject pattern
            address = ""
            for pattern in [r"Re: .*?(?:on|for|about) (.+)", r"Re: (.+)"]:
                addr_match = re.search(pattern, subject, re.IGNORECASE)
                if addr_match:
                    address = addr_match.group(1).strip()
                    break

            replies.append({"from": sender, "subject": subject, "body": body.strip(), "address": address, "sender_email": sender_addr})

        mail.logout()
    except Exception as e:
        log.debug(f"IMAP check failed: {e}")
    return replies


# ---------------------------------------------------------------------------
# MAIN: Rex negotiation cycle (run every 2 min via cron)
# ---------------------------------------------------------------------------

def _match_reply_to_lead(address: str) -> dict:
    """Find matching lead in leads_db.json by address."""
    try:
        from rex_sdr import load_leads
        leads = load_leads()
        for lead in leads:
            if address.lower() in lead.get("address", "").lower():
                return lead
    except Exception:
        pass
    return {}


def run_negotiation_cycle():
    log.info("Checking for seller/buyer replies...")
    replies = check_replies()
    if not replies:
        log.info("No new replies")
        return

    log.info(f"Found {len(replies)} new replies")

    # Try to use the closer pipeline for interested sellers
    try:
        from rex_closer import handle_seller_reply as closer_handle
        has_closer = True
    except ImportError:
        has_closer = False

    for reply in replies:
        address = reply["address"]

        # Check for buyer interest
        if "i want it" in reply["body"].lower() or "interested" == reply["body"].lower().strip():
            # Check active deals for buyer matching
            for deal_file in DEALS_DIR.glob("*.json"):
                d = DealState.load(deal_file.stem)
                if d and address.lower() in d.address.lower():
                    d.buyer_name = reply["from"]
                    alert_buyer_found(d, reply["from"], d.our_offer + d.assignment_fee)
                    d.save()
                    break
            continue

        # Try closer pipeline first (handles qualifying, offers, contracts)
        if has_closer:
            lead = _match_reply_to_lead(address)
            if lead:
                result = closer_handle(lead, reply["body"])
                if result:
                    log.info(f"Closer handled reply for {address}: {result}")
                    # Update lead status in leads_db
                    try:
                        from rex_sdr import load_leads, save_leads
                        leads = load_leads()
                        for l in leads:
                            if address.lower() in l.get("address", "").lower():
                                l["status"] = "negotiating"
                                break
                        save_leads(leads)
                    except Exception:
                        pass
                    continue

        # Fallback: existing deal-based negotiation
        deal = None
        for deal_file in DEALS_DIR.glob("*.json"):
            d = DealState.load(deal_file.stem)
            if d and address.lower() in d.address.lower():
                deal = d
                break

        if not deal:
            log.warning(f"No deal found for: {address}")
            continue

        response = handle_seller_reply(deal, reply["body"])
        if response:
            log.info(f"Responded to seller for {deal.address}")


if __name__ == "__main__":
    run_negotiation_cycle()
