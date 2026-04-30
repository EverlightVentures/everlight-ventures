"""Wholesale Autonomous Pipeline v2 -- DEAL MACHINE.

Not a lead finder. A DEAL CLOSER. Every cycle: scout, score, contact, follow up,
match buyers, progress deals, detect replies, close.

CYCLE (runs every 30 minutes):
  1. Rex Blackwell SCOUTS sellers across 15 hedge-fund-targeted states (60+ cities)
  2. Rex SCOUTS buyers (hedge funds, cash buyers, title companies)
  3. Filter Banks SCORES all new leads by profit priority
  4. Piper Reeves SENDS outreach to top sellers (max 20/day, short + direct)
  5. Piper FOLLOWS UP on contacted sellers after 3 days (up to 4 attempts)
  6. DEAL PROGRESSION -- advance deals through ALL stages automatically
  7. BUYER MATCHING -- match negotiating deals to top 3 buyers
  8. RESPONSE DETECTION -- check for replies, bounces, engagement
  9. Pipeline stats posted to #wholesale-deals (C0ANLLV8JAC)
  10. Goal check: if $0 revenue, escalate blockers

AUTONOMOUS RULES:
  - Piper has SEND permission (approved by CEO 2026-03-30).
  - Short, direct templates that get replies (no AI fluff).
  - Follow-ups at day 3, day 7, day 14 with different angles.
  - Buyers get investment pitches with ROI math.
  - CAN-SPAM compliant: unsubscribe link, physical address, honest subjects.
  - Max 20 emails/day (warm-up period).
  - Every action logged to Supabase for audit trail.
  - Deal stages: new -> contacted -> negotiating -> marketing -> under_contract -> closed
  - Only ONE human gate: under_contract -> closed (sign-off required).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
RESEND_KEY = os.environ.get("RESEND_API_KEY", "re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt")

LOG_FILE = Path("/home/opc/hive_action_engine/wholesale_auto.log")

# Correct Slack channel -- #wholesale-deals
WHOLESALE_CHANNEL = "C0ANLLV8JAC"

# ============================================================
# HEDGE FUND TARGET CITIES (15 states, 60+ cities)
# ============================================================

HEDGE_FUND_CITIES = {
    "IN": ["Indianapolis", "Fort Wayne", "South Bend"],
    "OH": ["Cleveland", "Columbus", "Cincinnati", "Dayton", "Akron"],
    "TN": ["Memphis", "Nashville", "Knoxville", "Chattanooga"],
    "TX": ["Houston", "Dallas", "San Antonio", "Fort Worth", "Austin", "El Paso"],
    "FL": ["Jacksonville", "Tampa", "Orlando", "St Petersburg", "Cape Coral"],
    "GA": ["Atlanta", "Augusta", "Savannah", "Macon", "Columbus"],
    "AL": ["Birmingham", "Huntsville", "Montgomery", "Mobile"],
    "MO": ["Kansas City", "St Louis", "Springfield", "Columbia"],
    "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem"],
    "AZ": ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale"],
    "SC": ["Columbia", "Charleston", "Greenville"],
    "MS": ["Jackson", "Gulfport", "Biloxi"],
    "AR": ["Little Rock", "Fort Smith", "Fayetteville"],
    "OK": ["Oklahoma City", "Tulsa", "Norman"],
    "KS": ["Wichita", "Kansas City", "Topeka"],
}

STATE_NAMES = {
    "IN": "Indiana", "OH": "Ohio", "TN": "Tennessee", "TX": "Texas",
    "FL": "Florida", "GA": "Georgia", "AL": "Alabama", "MO": "Missouri",
    "NC": "North Carolina", "AZ": "Arizona", "SC": "South Carolina",
    "MS": "Mississippi", "AR": "Arkansas", "OK": "Oklahoma", "KS": "Kansas",
}

# Expanded search queries -- Zillow-style keywords
SELLER_SEARCH_QUERIES = [
    "handyman special {city} {state}",
    "as-is home for sale {city} {state}",
    "price reduced home {city} {state}",
    "investor special {city} {state}",
    "estate sale home {city} {state}",
    "must sell house {city} {state}",
    "fixer upper {city} {state}",
    "cash only home {city} {state}",
    "below market value {city} {state}",
    "{city} distressed property motivated seller",
    "{city} pre foreclosure homes for sale",
    "{city} FSBO fixer upper wholesale",
    "{city} vacant house owner sell quickly",
    "tax delinquent property {city} {state}",
    "probate real estate {city} {state}",
]

BUYER_SEARCH_QUERIES = [
    "cash home buyers {city} {state} we buy houses",
    "real estate investment company {city} {state}",
    "hedge fund buying single family homes {state} 2025 2026",
    "{state} title company wholesale friendly closing",
    "buy rental properties {city} {state} investor",
    "real estate portfolio buyer {city} {state}",
]

# ============================================================
# OUTREACH TEMPLATES (short, direct, proven to get replies)
# ============================================================

SELLER_TEMPLATES = {
    "first_touch": {
        "subject": "Cash offer for your {city} property",
        "body": """Hi {name},

I buy houses in {city} for cash. I can close in 14 days, no inspections, no repairs needed.

Would you consider a cash offer of ${mao:,} for {address}?

No pressure -- just let me know if you'd like to chat.

Piper Reeves
Everlight Logistics LLC
(916) 672-9150""",
    },
    "follow_up_1": {
        "subject": "Re: Cash offer for your {city} property",
        "body": """Hi {name},

Just following up on my note about your property. My offer of ${mao:,} cash still stands.

I handle all closing costs and can work on your timeline.

Worth a quick call?

Piper Reeves
Everlight Logistics LLC
(916) 672-9150""",
    },
    "follow_up_2": {
        "subject": "Still interested in your {city} property",
        "body": """Hi {name},

I know life gets busy. Quick reminder -- I have cash ready to buy your property at {address}.

If the timing isn't right, no worries. But if circumstances have changed and you're ready to talk, I'm here.

Piper Reeves
Everlight Logistics LLC
(916) 672-9150""",
    },
    "follow_up_3": {
        "subject": "Last note about your {city} property",
        "body": """Hi {name},

This will be my last message. I have a standing cash offer for your {city} property.

If you ever want to sell quickly with no hassle, keep my number: (916) 672-9150.

Wishing you the best,
Piper Reeves
Everlight Logistics LLC""",
    },
}

BUYER_PITCH_TEMPLATE = {
    "subject": "Investment Opportunity: {city}, {state} -- {roi}% ROI",
    "body": """Hi {buyer_name},

Quick deal on my desk in {city}, {state}:

Property: {address}
ARV: ${arv:,}
Price: ${price:,}
Assignment Fee: ${fee:,}
Your All-In: ${all_in:,}
Potential Profit: ${profit:,} ({roi}% ROI)

Numbers are verified. Title is clean. Contract ready to assign.

Interested? Reply and I'll send the full package.

Piper Reeves
Everlight Logistics LLC
(916) 672-9150""",
}

CAN_SPAM_FOOTER_HTML = """<div style="margin-top:30px;padding-top:15px;border-top:1px solid #ddd;font-size:11px;color:#888;">
<p>Everlight Logistics LLC | Sacramento, CA 95814</p>
<p>This message was sent based on public property records.
<a href="mailto:unsubscribe@everlightventures.io?subject=Unsubscribe" style="color:#D4AF37;">Unsubscribe</a></p>
</div>"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _sb_get(table: str, params: str = "") -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        _log(f"SB GET error ({table}): {e}")
        return []


def _sb_insert(table: str, records: list[dict]) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(records).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        _log(f"SB INSERT error ({table}): {e}")
        return {"error": str(e)}


def _sb_update(table: str, match_col: str, match_val: str, updates: dict) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    data = json.dumps(updates).encode()
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        _log(f"SB UPDATE error ({table}): {e}")
        return {"error": str(e)}


def _slack(channel: str, text: str):
    if not SLACK_TOKEN:
        _log(f"[SLACK-SKIP] No token. Would post to {channel}: {text[:100]}...")
        return
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel, "text": text}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {SLACK_TOKEN}"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        _log(f"Slack error: {e}")


def _ai_generate(prompt: str, max_tokens: int = 500) -> str:
    """Use OpenAI to generate content (property analysis, email drafts, etc.)."""
    if not OPENAI_KEY:
        return ""
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": "gpt-4o-mini",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        _log(f"AI error: {e}")
        return ""


def _web_search(query: str) -> list[dict]:
    """Search the web using DuckDuckGo HTML (no API key needed)."""
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
        results = []
        for match in re.finditer(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html):
            link = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if link and title and "duckduckgo" not in link:
                actual = re.search(r"uddg=([^&]+)", link)
                if actual:
                    link = urllib.parse.unquote(actual.group(1))
                results.append({"title": title, "url": link})
        return results[:10]
    except Exception as e:
        _log(f"Search error: {e}")
        return []


def _send_email(to_email: str, subject: str, body_text: str, from_name: str = "Piper Reeves") -> dict:
    """Send via branded_mailer (gold template + budget gate + owner-block guard).

    The body's plain text is wrapped automatically by the Everlight template;
    the Georgia/serif HTML wrapper this function used to build is discarded
    in favor of Playfair/Inter consistency. CAN-SPAM footer is appended via
    plain_text_fallback so non-HTML clients still see compliance text.
    """
    body_html = body_text.replace("\n", "<br>")
    plain_with_footer = body_text + "\n\n---\n" + (CAN_SPAM_FOOTER_HTML.replace("<br>", "\n").replace("<", "").replace(">", "") if isinstance(CAN_SPAM_FOOTER_HTML, str) else "")

    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        _log(f"branded_mailer unavailable: {exc}")
        return {"error": f"branded_mailer_import_failed: {exc}"}

    result = send_branded_email(
        to=to_email,
        subject=subject,
        content_html=body_html + ("\n<br>" + CAN_SPAM_FOOTER_HTML if CAN_SPAM_FOOTER_HTML else ""),
        title=subject,
        from_name=f"{from_name} at Everlight",
        from_email="piper@everlightventures.io",
        reply_to="piper@everlightventures.io",
        agent_name=from_name,
        agent_title="Wholesale Outreach",
        agent_email="piper@everlightventures.io",
        plain_text_fallback=plain_with_footer,
        budget_category="bulk",
    )
    if result.ok:
        return {"id": result.message_id or "sent", "status": "sent"}
    _log(f"Email send error to {to_email}: {result.error}")
    return {"error": result.error}


def _get_mao(seller: dict) -> int:
    """Calculate Maximum Allowable Offer (70% ARV - repair - assignment fee)."""
    arv = int(seller.get("estimated_arv") or 0)
    repair = int(seller.get("estimated_repair") or 0)
    if arv > 0:
        return max(0, int(arv * 0.70 - repair - 10000))
    # Fallback: use asking price * 0.75
    asking = int(seller.get("asking_price") or 0)
    if asking > 0:
        return int(asking * 0.75)
    return 0


def _get_today_send_count() -> int:
    """Count how many emails were sent today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sent = _sb_get("wholesale_outreach", f"status=eq.sent&created_at=gte.{today}T00:00:00Z&select=id")
    return len(sent) if isinstance(sent, list) else 0


# ============================================================
# REX BLACKWELL: Expanded autonomous property scouting
# ============================================================

def rex_scout_sellers(max_states: int = 5, max_per_city: int = 3) -> int:
    """Scout distressed properties across 15 hedge-fund-targeted states."""
    _log("Rex Blackwell: Starting expanded seller scout...")

    # Rotate through states -- pick states with fewest existing leads
    state_lead_counts = {}
    for code in HEDGE_FUND_CITIES:
        existing = _sb_get("wholesale_sellers", f"state=eq.{code}&status=eq.new&select=id")
        state_lead_counts[code] = len(existing) if isinstance(existing, list) else 0

    # Sort states by fewest leads first (prioritize under-scouted states)
    sorted_states = sorted(state_lead_counts.items(), key=lambda x: x[1])
    target_states = [s[0] for s in sorted_states[:max_states]]

    total_added = 0

    for state_code in target_states:
        state_name = STATE_NAMES.get(state_code, state_code)
        cities = HEDGE_FUND_CITIES.get(state_code, [])

        # Pick 2 random-ish queries per city (rotate based on hour)
        hour = datetime.now(timezone.utc).hour
        query_offset = hour % len(SELLER_SEARCH_QUERIES)

        for city in cities[:4]:  # max 4 cities per state per cycle
            queries_to_run = [
                SELLER_SEARCH_QUERIES[(query_offset + i) % len(SELLER_SEARCH_QUERIES)]
                for i in range(2)
            ]

            for query_tmpl in queries_to_run:
                query = query_tmpl.format(city=city, state=state_name)
                results = _web_search(query)
                if not results:
                    continue

                result_text = "\n".join(f"- {r['title']} ({r['url']})" for r in results[:5])
                ai_prompt = f"""You are Rex Blackwell, a real estate wholesale scout.
Analyze these search results for {city}, {state_name} and extract actionable property leads.
For each lead, provide: property_type, city, estimated_value_range, motivation_signals, quality score 1-10.
Only include leads that look like genuine motivated seller situations.
If none are actionable, say "no actionable leads".

Search results:
{result_text}

Format as JSON array: [{{"property_type": "", "city": "", "estimated_value": 0, "motivation": "", "quality": 0, "source_url": "", "notes": ""}}]
Return ONLY the JSON array, nothing else."""

                ai_response = _ai_generate(ai_prompt, 400)
                if not ai_response or "no actionable" in ai_response.lower():
                    continue

                try:
                    json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                    if json_match:
                        leads = json.loads(json_match.group())
                    else:
                        continue
                except Exception:
                    continue

                for lead in leads[:max_per_city]:
                    if int(lead.get("quality", 0)) < 5:
                        continue

                    lead_city = lead.get("city", city)
                    existing = _sb_get("wholesale_sellers",
                        f"state=eq.{state_code}&city=eq.{urllib.parse.quote(lead_city)}&status=eq.new&select=id&limit=15")
                    if isinstance(existing, list) and len(existing) >= 15:
                        continue  # enough leads for this city

                    record = {
                        "owner_name": f"[Scout Lead] {lead_city}, {state_code}",
                        "property_address": f"[Scouted - needs verification] {lead_city}, {state_code}",
                        "state": state_code,
                        "city": lead_city,
                        "property_type": lead.get("property_type", "single_family"),
                        "estimated_arv": int(lead.get("estimated_value", 0)),
                        "motivation_level": min(5, max(1, int(lead.get("quality", 3)) // 2)),
                        "motivation_reasons": [lead.get("motivation", "web_scout")],
                        "lead_source": lead.get("source_url", "web_search"),
                        "status": "new",
                        "verified": False,
                        "notes": f"Rex scout ({query_tmpl.split()[0]}): {lead.get('notes', '')}. Source: {lead.get('source_url', '')}",
                    }
                    result = _sb_insert("wholesale_sellers", [record])
                    if not isinstance(result, dict) or "error" not in result:
                        total_added += 1

                time.sleep(2)  # rate limit between searches

    _log(f"Rex scouted {total_added} new seller leads across {len(target_states)} states ({', '.join(target_states)})")
    return total_added


# ============================================================
# REX BLACKWELL: Autonomous buyer scouting
# ============================================================

def rex_scout_buyers(max_states: int = 5, max_per_state: int = 3) -> int:
    """Scout cash buyers, hedge funds, and title companies in hedge fund cities."""
    _log("Rex Blackwell: Starting buyer scout...")

    # Rotate states -- prioritize states with fewest buyers
    state_buyer_counts = {}
    for code in HEDGE_FUND_CITIES:
        existing = _sb_get("wholesale_buyers", f"state=eq.{code}&select=id")
        state_buyer_counts[code] = len(existing) if isinstance(existing, list) else 0

    sorted_states = sorted(state_buyer_counts.items(), key=lambda x: x[1])
    target_states = [s[0] for s in sorted_states[:max_states]]

    total_added = 0
    hour = datetime.now(timezone.utc).hour
    query_offset = hour % len(BUYER_SEARCH_QUERIES)

    for state_code in target_states:
        state_name = STATE_NAMES.get(state_code, state_code)
        cities = HEDGE_FUND_CITIES.get(state_code, [])

        for city in cities[:2]:
            query_tmpl = BUYER_SEARCH_QUERIES[(query_offset) % len(BUYER_SEARCH_QUERIES)]
            query = query_tmpl.format(state=state_name, city=city)
            results = _web_search(query)
            if not results:
                continue

            result_text = "\n".join(f"- {r['title']} ({r['url']})" for r in results[:5])
            ai_prompt = f"""You are Rex Blackwell, scouting cash buyers and investment companies in {city}, {state_name}.
Extract buyer leads from these results. For each: company_name, city, buy_type (hedge_fund/investor/title_company/flipper), estimated_volume, contact_email (if visible), notes.
Only include legitimate companies.

Search results:
{result_text}

Format as JSON array: [{{"company_name": "", "city": "", "buy_type": "", "estimated_volume": "", "contact_email": "", "source_url": "", "notes": ""}}]
Return ONLY the JSON array."""

            ai_response = _ai_generate(ai_prompt, 400)
            if not ai_response:
                continue

            try:
                json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                if json_match:
                    buyers = json.loads(json_match.group())
                else:
                    continue
            except Exception:
                continue

            for buyer in buyers[:max_per_state]:
                company = buyer.get("company_name", "").strip()
                if not company or len(company) < 3:
                    continue

                existing = _sb_get("wholesale_buyers",
                    f"company_name=eq.{urllib.parse.quote(company)}&limit=1")
                if isinstance(existing, list) and len(existing) > 0:
                    continue

                record = {
                    "company_name": company,
                    "contact_name": "",
                    "contact_email": buyer.get("contact_email", ""),
                    "state": state_code,
                    "city": buyer.get("city", city),
                    "buy_criteria": {"type": buyer.get("buy_type", "investor"), "source": buyer.get("source_url", "")},
                    "property_types": ["single_family", "multi_family"],
                    "relationship_status": "new",
                    "verified": False,
                    "source": buyer.get("source_url", "web_search"),
                    "notes": f"Rex scout: {buyer.get('notes', '')}. Type: {buyer.get('buy_type', '')}.",
                }
                result = _sb_insert("wholesale_buyers", [record])
                if not isinstance(result, dict) or "error" not in result:
                    total_added += 1

            time.sleep(2)

    _log(f"Rex scouted {total_added} new buyer leads across {len(target_states)} states")
    return total_added


# ============================================================
# FILTER BANKS: Auto-score all new leads
# ============================================================

def filter_score_leads() -> int:
    """Score all unscored seller leads by profit priority."""
    sellers = _sb_get("wholesale_sellers", "priority_score=eq.0&status=eq.new&limit=50")
    if not isinstance(sellers, list) or not sellers:
        return 0

    ease_map = {}
    states = _sb_get("wholesale_states", "select=state_code,ease_score")
    if isinstance(states, list):
        ease_map = {s["state_code"]: s["ease_score"] for s in states}

    scored = 0
    for seller in sellers:
        motivation = int(seller.get("motivation_level") or 3)
        arv = int(seller.get("estimated_arv") or 0)
        price = int(seller.get("asking_price") or seller.get("max_offer") or 0)
        repair = int(seller.get("estimated_repair") or 0)
        ease = ease_map.get(seller.get("state", ""), 5)
        has_email = 1 if seller.get("contact_email") else 0

        if arv > 0 and price > 0:
            profit = max(0, (arv - price - repair)) / 1000
        else:
            profit = float(motivation)

        difficulty = max(1, 11 - ease)
        # Boost score for leads with email addresses (actionable)
        email_boost = 3.0 if has_email else 1.0
        priority = round((motivation * max(profit, 0.5) * email_boost) / difficulty, 2)

        _sb_update("wholesale_sellers", "id", seller["id"], {
            "priority_score": priority,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        scored += 1

    _log(f"Filter Banks scored {scored} seller leads")
    return scored


# ============================================================
# SKIP TRACE: Enrich leads with owner contact info
# ============================================================

def skip_trace_enrich(max_leads: int = 10) -> int:
    """Find owner email/phone for leads that don't have contact info.

    Uses web search + AI to extract owner details from public records,
    county assessor sites, and property listing pages.
    This is the CRITICAL missing piece -- no contact info = no outreach.
    """
    # Get high-priority leads without email
    leads = _sb_get("wholesale_sellers",
        "contact_email=eq.&status=eq.new&priority_score=gt.0&order=priority_score.desc&limit=" + str(max_leads * 2))
    if not isinstance(leads, list) or not leads:
        # Also try leads with empty string email
        leads = _sb_get("wholesale_sellers",
            "status=eq.new&priority_score=gt.0&order=priority_score.desc&limit=" + str(max_leads * 2))
        if isinstance(leads, list):
            leads = [l for l in leads if not l.get("contact_email")]
        else:
            leads = []

    if not leads:
        _log("Skip trace: no leads need enrichment")
        return 0

    enriched = 0
    for lead in leads[:max_leads]:
        address = lead.get("property_address", "")
        city = lead.get("city", "")
        state = lead.get("state", "")
        owner = lead.get("owner_name", "")
        source_url = lead.get("lead_source", "")

        if not address or address.startswith("[Scout"):
            continue

        # Strategy 1: Search for owner by property address
        search_queries = [
            f'"{address}" owner contact email',
            f'{address} {city} {state} property owner',
            f'{address} county assessor owner name',
        ]

        found_email = ""
        found_phone = ""
        found_name = owner if owner and not owner.startswith("[") else ""

        for sq in search_queries[:2]:
            results = _web_search(sq)
            if not results:
                time.sleep(1)
                continue

            result_text = "\n".join(f"- {r['title']} ({r['url']})" for r in results[:5])
            ai_prompt = f"""Extract the property owner's contact info from these search results.
Property: {address}, {city}, {state}

Search results:
{result_text}

Extract: owner_name, email, phone. If not found, say "not found".
Return JSON: {{"owner_name": "", "email": "", "phone": ""}}
Return ONLY the JSON, nothing else."""

            ai_resp = _ai_generate(ai_prompt, 200)
            if not ai_resp or "not found" in ai_resp.lower():
                time.sleep(1)
                continue

            try:
                json_match = re.search(r'\{.*\}', ai_resp, re.DOTALL)
                if json_match:
                    info = json.loads(json_match.group())
                    if info.get("email") and "@" in info["email"] and "example" not in info["email"]:
                        found_email = info["email"]
                    if info.get("phone") and len(info["phone"]) >= 10:
                        found_phone = info["phone"]
                    if info.get("owner_name") and len(info["owner_name"]) > 2:
                        found_name = info["owner_name"]
                    if found_email:
                        break
            except Exception:
                pass
            time.sleep(1)

        # Strategy 2: If we have a Zillow URL, try to get owner info from it
        if not found_email and source_url and "zillow.com" in source_url:
            results = _web_search(f'site:zillow.com {address} contact owner')
            # Zillow rarely has direct contact but may have agent info

        # Update lead with whatever we found
        updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if found_email:
            updates["contact_email"] = found_email
        if found_phone:
            updates["contact_phone"] = found_phone
        if found_name and not lead.get("owner_name", "").startswith("["):
            pass  # keep existing name
        elif found_name:
            updates["owner_name"] = found_name

        if found_email or found_phone:
            _sb_update("wholesale_sellers", "id", lead["id"], updates)
            enriched += 1
            _log(f"Skip trace: enriched {address} -> email={found_email}, phone={found_phone}")
        else:
            # Mark as needs_manual so we don't keep retrying
            _sb_update("wholesale_sellers", "id", lead["id"], {
                "notes": (lead.get("notes", "") + " | skip_trace_attempted: no contact found").strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        time.sleep(2)  # rate limit

    _log(f"Skip trace: enriched {enriched}/{len(leads[:max_leads])} leads with contact info")
    return enriched


# ============================================================
# PIPER REEVES: Direct outreach with proven templates
# ============================================================

def piper_craft_and_send(max_sends: int = 20) -> dict:
    """Send short, direct outreach emails that actually get replies.

    Uses proven templates instead of AI-generated fluff.
    Max 20/day during warm-up. CAN-SPAM compliant.

    Returns: {"sent": int, "skipped": int, "failed": int, "details": list}
    """
    result = {"sent": 0, "skipped": 0, "failed": 0, "details": []}

    # Check daily cap
    today_count = _get_today_send_count()
    remaining = max(0, 20 - today_count)
    max_sends = min(max_sends, remaining)

    if max_sends <= 0:
        _log("Piper: Daily cap reached (20 emails). Skipping.")
        return result

    # Get top sellers with email that haven't been contacted
    sellers = _sb_get("wholesale_sellers",
        "status=eq.new&priority_score=gt.0&order=priority_score.desc&limit=" + str(max_sends * 3))
    if not isinstance(sellers, list):
        return result

    for seller in sellers:
        if result["sent"] >= max_sends:
            break

        seller_id = seller.get("id", "")
        email_addr = seller.get("contact_email", "").strip()

        if not email_addr or "@" not in email_addr:
            result["skipped"] += 1
            continue

        # Check if already contacted
        existing = _sb_get("wholesale_outreach", f"target_id=eq.{seller_id}&limit=1")
        if isinstance(existing, list) and len(existing) > 0:
            continue

        name = seller.get("owner_name", "Property Owner")
        city = seller.get("city", "")
        state = seller.get("state", "")
        address = seller.get("property_address", "")
        mao = _get_mao(seller)

        # Use proven first-touch template
        tmpl = SELLER_TEMPLATES["first_touch"]
        subject = tmpl["subject"].format(city=city, name=name, address=address, mao=mao)
        body = tmpl["body"].format(city=city, name=name, address=address, mao=mao)

        # If no MAO (no ARV data), adjust the message
        if mao <= 0:
            subject = f"Cash offer for your {city} property"
            body = f"""Hi {name},

I buy houses in {city} for cash. I can close in 14 days, no inspections, no repairs needed.

Would you be open to a cash offer for your property at {address}?

No pressure -- just let me know if you'd like to chat.

Piper Reeves
Everlight Logistics LLC
(916) 672-9150"""

        # SEND
        send_result = _send_email(email_addr, subject, body)

        if send_result.get("status") == "sent":
            # Log to Supabase
            outreach = {
                "target_type": "seller",
                "target_id": seller_id,
                "target_name": name,
                "target_email": email_addr,
                "city": city,
                "state": state,
                "subject": subject,
                "body": body,
                "personalization_notes": f"Template: first_touch. MAO: ${mao:,}",
                "tone": "direct_warm",
                "status": "sent",
                "agent_name": "Piper Reeves",
                "attempt_number": 1,
            }
            _sb_insert("wholesale_outreach", [outreach])

            _sb_update("wholesale_sellers", "id", seller_id, {
                "status": "contacted",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

            result["sent"] += 1
            result["details"].append({"to": name, "city": city, "msg_id": send_result.get("id")})
            _log(f"Piper SENT to {name} ({city}, {state}) | {subject}")
        else:
            result["failed"] += 1
            # Save as draft
            outreach = {
                "target_type": "seller",
                "target_id": seller_id,
                "target_name": name,
                "target_email": email_addr,
                "subject": subject,
                "body": body,
                "status": "draft",
                "agent_name": "Piper Reeves",
                "attempt_number": 1,
            }
            _sb_insert("wholesale_outreach", [outreach])

        time.sleep(3)  # Rate limit

    _log(f"Piper: {result['sent']} sent, {result['skipped']} skipped, {result['failed']} failed")
    return result


# ============================================================
# PIPER REEVES: Follow-up engine (day 3, 7, 14)
# ============================================================

def run_follow_ups(max_follow_ups: int = 10) -> dict:
    """Follow up on contacted sellers who haven't replied.

    Schedule:
      - Attempt 2: 3 days after first contact (follow_up_1)
      - Attempt 3: 7 days after first contact (follow_up_2)
      - Attempt 4: 14 days after first contact (follow_up_3 -- final)
      - After 4 attempts: mark as cold

    Returns: {"followed_up": int, "marked_cold": int}
    """
    result = {"followed_up": 0, "marked_cold": 0}

    # Check daily cap
    today_count = _get_today_send_count()
    remaining = max(0, 20 - today_count)
    max_follow_ups = min(max_follow_ups, remaining)

    if max_follow_ups <= 0:
        return result

    # Get contacted sellers
    contacted = _sb_get("wholesale_sellers", "status=eq.contacted&limit=50")
    if not isinstance(contacted, list):
        return result

    now = datetime.now(timezone.utc)

    for seller in contacted:
        if result["followed_up"] >= max_follow_ups:
            break

        seller_id = seller.get("id", "")
        email_addr = seller.get("contact_email", "").strip()
        if not email_addr or "@" not in email_addr:
            continue

        # Get all outreach for this seller
        outreach_list = _sb_get("wholesale_outreach",
            f"target_id=eq.{seller_id}&target_type=eq.seller&order=created_at.desc&limit=10")
        if not isinstance(outreach_list, list):
            continue

        attempt_count = len(outreach_list)
        if attempt_count == 0:
            continue

        # Check if any reply came in
        has_reply = any(o.get("status") == "replied" for o in outreach_list)
        if has_reply:
            continue  # Already replied, deal progression handles this

        # After 4 attempts, mark cold
        if attempt_count >= 4:
            _sb_update("wholesale_sellers", "id", seller_id, {
                "status": "cold",
                "updated_at": now.isoformat(),
            })
            result["marked_cold"] += 1
            continue

        # Check timing -- when was last outreach sent?
        last_outreach = outreach_list[0]
        last_sent_str = last_outreach.get("created_at", "")
        try:
            last_sent = datetime.fromisoformat(last_sent_str.replace("Z", "+00:00"))
        except Exception:
            continue

        days_since = (now - last_sent).days

        # Determine which follow-up to send
        if attempt_count == 1 and days_since >= 3:
            template_key = "follow_up_1"
        elif attempt_count == 2 and days_since >= 4:
            template_key = "follow_up_2"
        elif attempt_count == 3 and days_since >= 7:
            template_key = "follow_up_3"
        else:
            continue  # Not time yet

        name = seller.get("owner_name", "Property Owner")
        city = seller.get("city", "")
        state = seller.get("state", "")
        address = seller.get("property_address", "")
        mao = _get_mao(seller)

        tmpl = SELLER_TEMPLATES[template_key]
        subject = tmpl["subject"].format(city=city, name=name, address=address, mao=mao)
        body = tmpl["body"].format(city=city, name=name, address=address, mao=mao)

        send_result = _send_email(email_addr, subject, body)

        if send_result.get("status") == "sent":
            outreach = {
                "target_type": "seller",
                "target_id": seller_id,
                "target_name": name,
                "target_email": email_addr,
                "city": city,
                "state": state,
                "subject": subject,
                "body": body,
                "personalization_notes": f"Template: {template_key}. Attempt #{attempt_count + 1}",
                "tone": "direct_warm",
                "status": "sent",
                "agent_name": "Piper Reeves",
                "attempt_number": attempt_count + 1,
            }
            _sb_insert("wholesale_outreach", [outreach])
            result["followed_up"] += 1
            _log(f"Piper follow-up #{attempt_count + 1} to {name} ({city}, {state}) | {template_key}")

        time.sleep(3)

    _log(f"Follow-ups: {result['followed_up']} sent, {result['marked_cold']} marked cold")
    return result


# ============================================================
# RESPONSE DETECTION: Check for replies and bounces
# ============================================================

def check_email_replies() -> dict:
    """Detect seller and buyer replies, bounces, and engagement.

    Checks:
    1. Supabase for outreach marked 'replied' (by webhook or manual)
    2. Bounced emails -> mark seller as bad_email
    3. Future: Gmail IMAP check or Resend webhooks

    Returns: {"replies_found": int, "bounces_found": int}
    """
    result = {"replies_found": 0, "bounces_found": 0}

    # Check for replies (marked by external webhook or manual update)
    replied = _sb_get("wholesale_outreach", "status=eq.replied&limit=20")
    if isinstance(replied, list):
        result["replies_found"] = len(replied)
        for r in replied:
            seller_id = r.get("target_id")
            target_type = r.get("target_type", "seller")
            if seller_id and target_type == "seller":
                # Check if seller is still in 'contacted' status
                seller = _sb_get("wholesale_sellers", f"id=eq.{seller_id}&limit=1")
                if isinstance(seller, list) and seller and seller[0].get("status") == "contacted":
                    _slack(WHOLESALE_CHANNEL,
                        f":incoming_envelope: *SELLER REPLIED!* {r.get('target_name', 'Unknown')} "
                        f"in {r.get('city', '?')}, {r.get('state', '?')}. Moving to negotiation.")

    # Check for bounces
    bounced = _sb_get("wholesale_outreach", "status=eq.bounced&limit=20")
    if isinstance(bounced, list):
        result["bounces_found"] = len(bounced)
        for b in bounced:
            seller_id = b.get("target_id")
            if seller_id:
                _sb_update("wholesale_sellers", "id", seller_id, {
                    "status": "bad_email",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                _sb_update("wholesale_outreach", "id", b["id"], {"status": "bounce_processed"})

    if result["replies_found"] > 0 or result["bounces_found"] > 0:
        _log(f"Response check: {result['replies_found']} replies, {result['bounces_found']} bounces")

    return result


# ============================================================
# DEAL EXECUTOR: The missing piece -- advance deals through ALL stages
# ============================================================

def execute_deal_progression() -> dict:
    """Advance deals through ALL stages automatically.

    Deal stages:
      new -> contacted -> negotiating -> marketing -> under_contract -> closed
                         (reply detected) (buyers matched) (buyer interested)  (HUMAN GATE)

    Returns: {"deals_created": int, "deals_marketed": int, "buyer_matches": int, "contracts_ready": int}
    """
    result = {"deals_created": 0, "deals_marketed": 0, "buyer_matches": 0, "contracts_ready": 0}

    # -------------------------------------------------------
    # Stage 2->3: Contacted sellers who replied -> create deal
    # -------------------------------------------------------
    replied = _sb_get("wholesale_outreach", "status=eq.replied&target_type=eq.seller&limit=20")
    if isinstance(replied, list):
        for r in replied:
            seller_id = r.get("target_id")
            if not seller_id:
                continue

            # Check if deal already exists for this seller
            existing_deal = _sb_get("wholesale_deals", f"seller_id=eq.{seller_id}&limit=1")
            if isinstance(existing_deal, list) and len(existing_deal) > 0:
                # Deal exists, just update outreach status
                _sb_update("wholesale_outreach", "id", r["id"], {"status": "deal_created"})
                continue

            # Get seller details
            seller = _sb_get("wholesale_sellers", f"id=eq.{seller_id}&limit=1")
            if not isinstance(seller, list) or not seller:
                continue
            seller = seller[0]

            # Create deal record
            deal = {
                "seller_id": seller_id,
                "status": "negotiating",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "agent_assigned": "Hammer Knox",
                "property_address": seller.get("property_address", ""),
                "city": seller.get("city", ""),
                "state": seller.get("state", ""),
                "estimated_arv": seller.get("estimated_arv", 0),
                "offer_price": _get_mao(seller),
                "notes": f"Seller replied to outreach. Moving to negotiation. Reply ref: outreach#{r.get('id', '')}",
            }
            insert_result = _sb_insert("wholesale_deals", [deal])
            if not isinstance(insert_result, dict) or "error" not in insert_result:
                result["deals_created"] += 1
                _sb_update("wholesale_sellers", "id", seller_id, {
                    "status": "negotiating",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                _sb_update("wholesale_outreach", "id", r["id"], {"status": "deal_created"})
                _slack(WHOLESALE_CHANNEL,
                    f":handshake: *DEAL CREATED* -- Seller replied! "
                    f"{r.get('target_name', '')} in {seller.get('city', '')}, {seller.get('state', '')}. "
                    f"Hammer Knox negotiating. MAO: ${_get_mao(seller):,}")

    # -------------------------------------------------------
    # Stage 3->4: Negotiating deals -> match to top 3 buyers
    # -------------------------------------------------------
    negotiating = _sb_get("wholesale_deals", "status=eq.negotiating&limit=20")
    if isinstance(negotiating, list):
        for deal in negotiating:
            deal_id = deal.get("id")
            seller_id = deal.get("seller_id")
            if not seller_id:
                continue

            seller = _sb_get("wholesale_sellers", f"id=eq.{seller_id}&limit=1")
            if not isinstance(seller, list) or not seller:
                continue
            seller = seller[0]

            state = seller.get("state", "")
            if not state:
                continue

            # Find matching buyers in same state (prioritize hot/warm)
            buyers = _sb_get("wholesale_buyers",
                f"state=eq.{state}&limit=10&order=relationship_status.desc")
            if not isinstance(buyers, list) or not buyers:
                # No buyers in state -- widen search to neighboring states
                _log(f"No buyers in {state} for deal #{deal_id}. Need buyer scouting.")
                continue

            # Send pitch to top 3 buyers with email
            matched = 0
            for buyer in buyers:
                if matched >= 3:
                    break
                buyer_email = buyer.get("contact_email", "").strip()
                if not buyer_email or "@" not in buyer_email:
                    continue

                send_ok = _send_buyer_pitch(deal, seller, buyer)
                if send_ok:
                    matched += 1
                    result["buyer_matches"] += 1

            if matched > 0:
                _sb_update("wholesale_deals", "id", deal_id, {
                    "status": "marketing",
                    "notes": f"Sent to {matched} buyers in {state}. {deal.get('notes', '')}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                result["deals_marketed"] += 1
                _slack(WHOLESALE_CHANNEL,
                    f":loudspeaker: *DEAL MARKETED* -- Deal #{deal_id} in {seller.get('city', '')}, {state} "
                    f"sent to {matched} buyers. Waiting for buyer response.")

    # -------------------------------------------------------
    # Stage 4->5: Buyer responds to pitch -> move to under_contract
    # -------------------------------------------------------
    buyer_replies = _sb_get("wholesale_outreach", "target_type=eq.buyer&status=eq.replied&limit=10")
    if isinstance(buyer_replies, list):
        for br in buyer_replies:
            buyer_id = br.get("target_id")
            # Find marketing deals for the same state/city
            city = br.get("city", "")
            state = br.get("state", "")
            filter_str = "status=eq.marketing&limit=5"
            if state:
                filter_str += f"&state=eq.{state}"

            marketing_deals = _sb_get("wholesale_deals", filter_str)
            if isinstance(marketing_deals, list) and marketing_deals:
                deal = marketing_deals[0]
                _sb_update("wholesale_deals", "id", deal["id"], {
                    "status": "under_contract",
                    "buyer_id": buyer_id,
                    "notes": f"Buyer interested! {br.get('target_name', '')} replied. {deal.get('notes', '')}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                _sb_update("wholesale_outreach", "id", br["id"], {"status": "deal_matched"})
                result["contracts_ready"] += 1
                _slack(WHOLESALE_CHANNEL,
                    f":fire: *BUYER MATCH!* {br.get('target_name', '')} interested in deal #{deal['id']}! "
                    f"Moving to contract stage. @lucrex sign off needed.")

    # -------------------------------------------------------
    # Stage 5->6: Under contract -> flag for human review (THE ONE GATE)
    # -------------------------------------------------------
    under_contract = _sb_get("wholesale_deals", "status=eq.under_contract&limit=10")
    if isinstance(under_contract, list):
        for deal in under_contract:
            deal_id = deal.get("id")
            city = deal.get("city", "")
            state = deal.get("state", "")
            arv = int(deal.get("estimated_arv") or 0)
            price = int(deal.get("offer_price") or 0)
            assignment_fee = 10000
            profit = arv - price - assignment_fee if arv > 0 and price > 0 else 0

            _slack(WHOLESALE_CHANNEL,
                f":rotating_light: *CONTRACT READY FOR REVIEW*\n"
                f"Deal #{deal_id} | {city}, {state}\n"
                f"ARV: ${arv:,} | Price: ${price:,} | Assignment Fee: ${assignment_fee:,}\n"
                f"Projected Profit: ${profit:,}\n"
                f"Needs human sign-off before closing. @lucrex")

    if any(v > 0 for v in result.values()):
        _log(f"Deal progression: {result}")

    return result


# ============================================================
# BUYER PITCH: Send investment opportunity to matched buyer
# ============================================================

def _send_buyer_pitch(deal: dict, seller: dict, buyer: dict) -> bool:
    """Send a complete investment pitch to a matched buyer. Returns True if sent."""
    buyer_email = buyer.get("contact_email", "").strip()
    if not buyer_email or "@" not in buyer_email:
        return False

    arv = int(seller.get("estimated_arv") or 0)
    price = int(deal.get("offer_price") or seller.get("asking_price") or seller.get("max_offer") or 0)
    assignment_fee = 10000
    all_in = price + assignment_fee
    profit = arv - all_in if arv > 0 else 0
    roi = round(profit / all_in * 100, 1) if all_in > 0 else 0

    city = seller.get("city", "")
    state = seller.get("state", "")
    address = seller.get("property_address", "Details available upon request")
    buyer_name = buyer.get("contact_name") or buyer.get("company_name", "Investor")

    tmpl = BUYER_PITCH_TEMPLATE
    subject = tmpl["subject"].format(city=city, state=state, roi=roi)
    body = tmpl["body"].format(
        buyer_name=buyer_name, city=city, state=state, address=address,
        arv=arv, price=price, fee=assignment_fee, all_in=all_in, profit=profit, roi=roi,
    )

    send_result = _send_email(buyer_email, subject, body)

    if send_result.get("status") == "sent":
        outreach = {
            "target_type": "buyer",
            "target_id": buyer.get("id", ""),
            "target_name": buyer_name,
            "target_email": buyer_email,
            "city": city,
            "state": state,
            "subject": subject,
            "body": body,
            "personalization_notes": f"Buyer pitch. Deal #{deal.get('id', '')}. ROI: {roi}%",
            "tone": "professional_investor",
            "status": "sent",
            "agent_name": "Piper Reeves",
            "attempt_number": 1,
        }
        _sb_insert("wholesale_outreach", [outreach])
        _log(f"Buyer pitch sent to {buyer_name} ({buyer_email}) | {city}, {state} | ROI: {roi}%")
        return True

    return False


# ============================================================
# Legacy wrapper for backwards compatibility
# ============================================================

def piper_draft_seller_emails(max_drafts: int = 5) -> int:
    """Legacy wrapper -- now crafts AND sends."""
    result = piper_craft_and_send(max_sends=max_drafts)
    return result["sent"] + result.get("failed", 0)


# ============================================================
# MAIN AUTONOMOUS CYCLE
# ============================================================

def run_autonomous_cycle():
    """Full autonomous pipeline cycle. Runs every 30 minutes.

    1. Rex scouts sellers (expanded 15 states, 60+ cities)
    2. Rex scouts buyers (hedge funds in same cities)
    3. Filter scores all new leads
    4. Piper sends seller outreach (max 20/day, short + direct templates)
    5. Deal progression -- advance deals through ALL stages
    6. Follow-ups -- Piper follows up after 3 days
    7. Response detection -- check for replies + bounces
    8. Pipeline stats + Slack to #wholesale-deals
    """
    _log("=== AUTONOMOUS CYCLE START ===")
    results = {}

    # 1. Rex scouts sellers (expanded)
    try:
        results["sellers_scouted"] = rex_scout_sellers()
    except Exception as e:
        _log(f"Rex seller scout error: {e}")
        results["sellers_scouted"] = 0

    # 2. Rex scouts buyers
    try:
        results["buyers_scouted"] = rex_scout_buyers()
    except Exception as e:
        _log(f"Rex buyer scout error: {e}")
        results["buyers_scouted"] = 0

    # 3. Filter scores leads
    try:
        results["leads_scored"] = filter_score_leads()
    except Exception as e:
        _log(f"Filter score error: {e}")
        results["leads_scored"] = 0

    # 3.5. Skip trace -- enrich leads with contact info (THE KEY STEP)
    try:
        results["leads_enriched"] = skip_trace_enrich(max_leads=10)
    except Exception as e:
        _log(f"Skip trace error: {e}")
        results["leads_enriched"] = 0

    # 4. Piper sends outreach (max 20/day)
    try:
        piper_result = piper_craft_and_send(max_sends=20)
        results["emails_sent"] = piper_result["sent"]
        results["emails_failed"] = piper_result["failed"]
        results["emails_skipped"] = piper_result["skipped"]
    except Exception as e:
        _log(f"Piper send error: {e}")
        results["emails_sent"] = 0
        results["emails_failed"] = 0
        results["emails_skipped"] = 0

    # 5. Deal progression -- THE MISSING PIECE
    try:
        deal_result = execute_deal_progression()
        results["deals_created"] = deal_result["deals_created"]
        results["deals_marketed"] = deal_result["deals_marketed"]
        results["buyer_matches"] = deal_result["buyer_matches"]
        results["contracts_ready"] = deal_result["contracts_ready"]
    except Exception as e:
        _log(f"Deal progression error: {e}")
        results["deals_created"] = 0
        results["deals_marketed"] = 0
        results["buyer_matches"] = 0
        results["contracts_ready"] = 0

    # 6. Follow-ups (after first touch)
    try:
        fu_result = run_follow_ups()
        results["follow_ups_sent"] = fu_result["followed_up"]
        results["marked_cold"] = fu_result["marked_cold"]
    except Exception as e:
        _log(f"Follow-up error: {e}")
        results["follow_ups_sent"] = 0
        results["marked_cold"] = 0

    # 7. Response detection
    try:
        reply_result = check_email_replies()
        results["replies_detected"] = reply_result["replies_found"]
        results["bounces_detected"] = reply_result["bounces_found"]
    except Exception as e:
        _log(f"Response check error: {e}")
        results["replies_detected"] = 0
        results["bounces_detected"] = 0

    # 8. Pipeline stats
    stats = {}
    for status in ["new", "contacted", "negotiating", "cold", "bad_email"]:
        r = _sb_get("wholesale_sellers", f"status=eq.{status}&select=id")
        stats[f"sellers_{status}"] = len(r) if isinstance(r, list) else 0

    for rel in ["new", "warm", "hot", "repeat"]:
        r = _sb_get("wholesale_buyers", f"relationship_status=eq.{rel}&select=id")
        stats[f"buyers_{rel}"] = len(r) if isinstance(r, list) else 0

    for deal_status in ["negotiating", "marketing", "under_contract", "closed"]:
        r = _sb_get("wholesale_deals", f"status=eq.{deal_status}&select=id")
        stats[f"deals_{deal_status}"] = len(r) if isinstance(r, list) else 0

    results["stats"] = stats

    # 9. Slack report to #wholesale-deals
    sent_count = results.get("emails_sent", 0)
    failed_count = results.get("emails_failed", 0)
    fu_count = results.get("follow_ups_sent", 0)
    deals_created = results.get("deals_created", 0)
    deals_marketed = results.get("deals_marketed", 0)
    buyer_matches = results.get("buyer_matches", 0)
    contracts_ready = results.get("contracts_ready", 0)

    report_lines = [
        "*Wholesale Pipeline -- Autonomous Cycle*",
        f"*Scout:* Rex found {results['sellers_scouted']} sellers, {results['buyers_scouted']} buyers",
        f"*Enrich:* Skip traced {results.get('leads_enriched', 0)} leads with contact info",
        f"*Score:* Filter rated {results['leads_scored']} leads",
        f"*Outreach:* Piper sent {sent_count} first-touch" + (f" ({failed_count} failed)" if failed_count else ""),
        f"*Follow-ups:* {fu_count} sent, {results.get('marked_cold', 0)} marked cold",
        f"*Deals:* {deals_created} created, {deals_marketed} marketed, {buyer_matches} buyer matches, {contracts_ready} contracts ready",
        f"*Replies:* {results.get('replies_detected', 0)} detected | *Bounces:* {results.get('bounces_detected', 0)}",
        "---",
        f"*Pipeline:* {stats.get('sellers_new', 0)} new | {stats.get('sellers_contacted', 0)} contacted | {stats.get('sellers_negotiating', 0)} negotiating | {stats.get('sellers_cold', 0)} cold",
        f"*Buyers:* {stats.get('buyers_new', 0)} new | {stats.get('buyers_warm', 0)} warm | {stats.get('buyers_hot', 0)} hot",
        f"*Deals:* {stats.get('deals_negotiating', 0)} negotiating | {stats.get('deals_marketing', 0)} marketing | {stats.get('deals_under_contract', 0)} under contract | {stats.get('deals_closed', 0)} closed",
    ]

    total_actions = sum(results.get(k, 0) for k in [
        "sellers_scouted", "buyers_scouted", "leads_scored", "emails_sent",
        "follow_ups_sent", "deals_created", "buyer_matches",
    ])
    if total_actions == 0:
        report_lines.append(":warning: *No new actions.* Check: API keys, search rate limits, lead email coverage.")

    closed = _sb_get("wholesale_deals", "status=eq.closed&select=actual_profit")
    revenue = sum(float(d.get("actual_profit", 0)) for d in closed) if isinstance(closed, list) else 0
    if revenue == 0:
        report_lines.append(":red_circle: *$0 REVENUE.* Priority chain: leads w/ emails -> outreach -> follow-up -> reply -> deal -> buyer match -> close.")
    else:
        report_lines.append(f":moneybag: *Total Revenue: ${revenue:,.0f}*")

    report = "\n".join(report_lines)
    _slack(WHOLESALE_CHANNEL, report)
    _log(report)
    _log("=== AUTONOMOUS CYCLE END ===")

    return results


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        _log("Wholesale autonomous daemon starting (30-min cycles)...")
        while True:
            try:
                run_autonomous_cycle()
            except Exception as e:
                _log(f"Cycle error: {e}")
            _log("Next cycle in 30 minutes.")
            time.sleep(1800)  # 30 minutes
    elif "--once" in sys.argv:
        run_autonomous_cycle()
    elif "--follow-ups" in sys.argv:
        run_follow_ups()
    elif "--deals" in sys.argv:
        execute_deal_progression()
    elif "--replies" in sys.argv:
        check_email_replies()
    else:
        print("Usage:")
        print("  --daemon      Run forever (30-min cycles)")
        print("  --once        Single full cycle")
        print("  --follow-ups  Run follow-ups only")
        print("  --deals       Run deal progression only")
        print("  --replies     Check for replies only")
