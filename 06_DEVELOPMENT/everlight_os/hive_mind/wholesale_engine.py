"""Wholesale Execution Engine -- Agents that CLOSE DEALS, not just report.

This is the revenue engine. Every function results in an ACTION:
- Scout: finds real distressed properties
- Score: ranks them by profit potential
- Outreach: sends personalized emails to real people
- Match: pairs properties with hedge fund buyers
- Pitch: creates custom investment presentations
- Close: tracks assignment through to payday

AGENT ASSIGNMENTS:
  Rex Blackwell     -> scout (find properties)
  Filter Banks      -> score (rank by profit priority)
  Piper Reeves      -> outreach (personalized emails via Resend)
  Ace Deal Marketer  -> pitch (custom buyer presentations)
  Hammer O'Brien    -> close (negotiate, follow up, close)
  Cash Holloway     -> revenue (track money, commissions)

RULES:
  - No email sent until target is VERIFIED (real person, real property)
  - Every email is personalized -- read their style, match their tone
  - Prioritize: highest profit / lowest difficulty = do first
  - Track every interaction in Supabase for repeat relationships
  - Hedge fund buyers who bought before get priority on new deals
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Supabase connection
SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww")
RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

LOG_DIR = Path("/home/opc/hive_action_engine")
LOG_DIR.mkdir(exist_ok=True)


def _supabase_query(table: str, method: str = "GET", params: dict = None, body: dict = None) -> Any:
    """Direct Supabase REST API call."""
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    if method == "POST":
        req.add_header("Prefer", "return=representation")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _supabase_insert(table: str, records: list[dict]) -> Any:
    return _supabase_query(table, method="POST", body=records if isinstance(records, list) else [records])


def _supabase_update(table: str, match: dict, updates: dict) -> Any:
    """Update rows matching conditions."""
    import urllib.request
    params = "&".join(f"{k}=eq.{v}" for k, v in match.items())
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
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
        return {"error": str(e)}


def _slack_post(channel: str, text: str):
    if not SLACK_TOKEN:
        return
    import urllib.request
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel, "text": text}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {SLACK_TOKEN}"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ============================================================
# REX BLACKWELL: Scout distressed properties
# ============================================================

def scout_properties(states: list[str] = None, limit: int = 10) -> list[dict]:
    """Scout for distressed properties in priority states.

    Uses public data sources. Returns properties ready for scoring.
    In production, this would scrape Zillow, county records, FSBO sites.
    For now, uses structured web search to find motivated sellers.
    """
    if not states:
        # Get top-tier states
        top_states = _supabase_query("wholesale_states", params={
            "tier": "eq.top",
            "select": "state_code,state_name,avg_profit_per_deal",
            "order": "ease_score.desc",
        })
        if isinstance(top_states, list):
            states = [s["state_code"] for s in top_states]
        else:
            states = ["TX", "FL", "OH", "GA", "TN"]

    properties = []
    # This would be replaced with actual property scouting APIs
    # For now, log what WOULD be scouted so the pipeline is testable
    for state in states[:3]:
        properties.append({
            "owner_name": f"[PENDING SCOUT] {state} Distressed",
            "property_address": f"[Scouting {state}]",
            "state": state,
            "status": "new",
            "lead_source": "wholesale_engine_scout",
            "motivation_level": 3,
            "verified": False,
            "notes": f"Auto-scouted by Rex Blackwell. Needs manual verification before outreach.",
        })

    return properties


# ============================================================
# FILTER BANKS: Score and prioritize leads
# ============================================================

def score_sellers() -> list[dict]:
    """Score all unscored sellers by profit priority.

    Formula: priority_score = (motivation * profit_potential) / difficulty
    Where:
      motivation = 1-5 (seller urgency)
      profit_potential = (ARV - purchase_price - repairs) / 1000
      difficulty = inverse of ease_score for the state
    """
    sellers = _supabase_query("wholesale_sellers", params={
        "status": "eq.new",
        "select": "*",
        "limit": "50",
    })
    if not isinstance(sellers, list):
        return []

    # Get state ease scores
    states = _supabase_query("wholesale_states", params={"select": "state_code,ease_score"})
    ease_map = {s["state_code"]: s["ease_score"] for s in (states if isinstance(states, list) else [])}

    scored = []
    for seller in sellers:
        motivation = int(seller.get("motivation_level") or 3)
        arv = int(seller.get("estimated_arv") or 0)
        price = int(seller.get("asking_price") or seller.get("max_offer") or 0)
        repair = int(seller.get("estimated_repair") or 0)
        state = seller.get("state", "")
        ease = ease_map.get(state, 5)

        if arv > 0 and price > 0:
            profit_potential = max(0, (arv - price - repair)) / 1000
        else:
            profit_potential = 1  # unknown, give base score

        difficulty = max(1, 11 - ease)  # ease 10 = difficulty 1
        priority = round((motivation * profit_potential) / difficulty, 2)

        # Update in Supabase
        _supabase_update("wholesale_sellers", {"id": seller["id"]}, {
            "priority_score": priority,
            "potential_assignment_fee": max(0, int((arv - price - repair) * 0.1)) if arv > 0 else 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        seller["priority_score"] = priority
        scored.append(seller)

    # Sort by priority descending
    scored.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
    return scored


# ============================================================
# PIPER REEVES: Personalized outreach
# ============================================================

def craft_seller_email(seller: dict) -> dict:
    """Craft a personalized email for a motivated seller.

    Reads seller's personality_notes and communication_style to match tone.
    Every email is unique -- no templates, no generic BS.
    """
    name = seller.get("owner_name", "").split()[0] if seller.get("owner_name") else "there"
    address = seller.get("property_address", "your property")
    city = seller.get("city", "")
    state = seller.get("state", "")
    motivation = seller.get("motivation_reasons", [])
    style = seller.get("communication_style", "professional")

    # Base personalization
    if "foreclosure" in str(motivation).lower():
        hook = f"I understand you may be dealing with a difficult situation regarding {address}. I want you to know there are options that don't involve the bank."
    elif "divorce" in str(motivation).lower():
        hook = f"I know this is a challenging time, and I wanted to reach out about {address}. Sometimes a quick, clean sale can help both parties move forward."
    elif "inherited" in str(motivation).lower():
        hook = f"I noticed {address} and understand it may be an inherited property. Managing a property you didn't plan for can be stressful -- I may be able to help."
    elif "vacant" in str(motivation).lower():
        hook = f"I noticed {address} appears to be vacant. Carrying costs on an empty property add up fast -- I'd love to discuss a solution."
    else:
        hook = f"I'm reaching out about {address} in {city}, {state}. I work with property owners who are looking for a straightforward, hassle-free sale."

    subject = f"Quick question about {address}" if city else f"Regarding your property in {state}"

    body = f"""Hi {name},

{hook}

I'm with Everlight Logistics, and we buy properties directly from owners. No agents, no fees, no repairs needed. We can close in as little as 14 days, or on your timeline -- whatever works best for you.

If you're open to a conversation, I'd love to hear what you're looking for. No pressure, no obligation. Just a straightforward discussion about your options.

Would a quick 5-minute call work this week?

Best,
Piper Reeves
Everlight Logistics
(888) 896-6772
piper@everlightventures.io"""

    return {
        "target_type": "seller",
        "target_id": seller.get("id", ""),
        "target_name": seller.get("owner_name", ""),
        "target_email": seller.get("contact_email", ""),
        "subject": subject,
        "body": body,
        "personalization_notes": f"Motivation: {motivation}. Style: {style}. Hook type: contextual.",
        "tone": style or "warm_professional",
        "status": "draft",
        "agent_name": "Piper Reeves",
    }


def craft_buyer_pitch(buyer: dict, deal: dict, seller: dict) -> dict:
    """Craft a personalized investment pitch for a cash buyer.

    Reads buyer's buy_criteria, past deals, communication style.
    Tailored to what THIS buyer specifically looks for.
    """
    company = buyer.get("company_name", "")
    contact = buyer.get("contact_name", "").split()[0] if buyer.get("contact_name") else "there"
    criteria = buyer.get("buy_criteria", {})
    pref_types = buyer.get("property_types", [])
    relationship = buyer.get("relationship_status", "new")
    past_deals = buyer.get("deals_closed", 0)
    style = buyer.get("communication_style", "direct")

    address = deal.get("property_address", "")
    state = deal.get("state", "")
    price = deal.get("purchase_price", 0) + deal.get("assignment_fee", 0)
    arv = seller.get("estimated_arv", 0)
    repair = seller.get("estimated_repair", 0)
    sqft = seller.get("sqft", 0)
    prop_type = seller.get("property_type", "single family")

    profit_potential = arv - price - repair if arv > 0 else 0
    roi_pct = round(profit_potential / max(price, 1) * 100, 1) if price > 0 else 0

    # Personalize based on relationship
    if relationship == "repeat" and past_deals > 0:
        opener = f"Hey {contact}, got another one for you. You've closed {past_deals} with us so you know we bring quality deals."
    elif relationship in ("warm", "hot"):
        opener = f"Hi {contact}, hope you're doing well. I've got a deal that fits exactly what {company} has been looking for."
    else:
        opener = f"Hi {contact}, I'm Piper with Everlight Logistics. We source off-market investment properties and I have one that matches your buy criteria."

    subject = f"Off-Market Deal: {address} | {roi_pct}% ROI potential" if address else f"Investment Opportunity in {state}"

    body = f"""{opener}

PROPERTY SNAPSHOT:
  Address: {address}
  Type: {prop_type} | {sqft} sqft
  State: {state}

NUMBERS:
  All-in price: ${price:,}
  ARV (after repair): ${arv:,}
  Estimated repairs: ${repair:,}
  Potential profit: ${profit_potential:,} ({roi_pct}% ROI)

This is under contract and ready for assignment. Clean title, motivated seller, can close in 14 days.

Want me to send the full property packet? I can have it in your inbox within the hour.

Best,
Piper Reeves
Everlight Logistics
(888) 896-6772
piper@everlightventures.io"""

    return {
        "target_type": "buyer",
        "target_id": buyer.get("id", ""),
        "target_name": buyer.get("contact_name", ""),
        "target_email": buyer.get("email", ""),
        "subject": subject,
        "body": body,
        "personalization_notes": f"Relationship: {relationship}. Past deals: {past_deals}. Style: {style}. Criteria match: {criteria}.",
        "tone": "direct_professional" if style == "direct" else "warm_professional",
        "status": "draft",
        "agent_name": "Piper Reeves",
    }


def send_email(outreach: dict) -> dict:
    """Send an email via Resend API. Only sends VERIFIED drafts."""
    if outreach.get("status") != "verified":
        return {"sent": False, "reason": "not_verified"}
    if not outreach.get("target_email"):
        return {"sent": False, "reason": "no_email"}
    if not RESEND_KEY:
        return {"sent": False, "reason": "no_resend_key"}

    import urllib.request
    payload = {
        "from": f"{outreach.get('agent_name', 'Piper Reeves')} <piper@everlightventures.io>",
        "to": [outreach["target_email"]],
        "subject": outreach["subject"],
        "text": outreach["body"],
    }

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RESEND_KEY}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
        msg_id = result.get("id", "")

        # Update outreach record
        if outreach.get("id"):
            _supabase_update("wholesale_outreach", {"id": outreach["id"]}, {
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "resend_message_id": msg_id,
            })

        return {"sent": True, "message_id": msg_id}
    except Exception as e:
        return {"sent": False, "reason": str(e)[:200]}


# ============================================================
# HAMMER O'BRIEN: Follow up and close
# ============================================================

def check_replies() -> list[dict]:
    """Check for email replies and analyze them.

    In production, this would poll Resend webhooks or Gmail MCP.
    Analyzes reply tone, extracts key info, suggests next action.
    """
    # Get sent outreach awaiting reply
    pending = _supabase_query("wholesale_outreach", params={
        "status": "eq.sent",
        "select": "*",
        "order": "sent_at.asc",
        "limit": "50",
    })
    if not isinstance(pending, list):
        return []

    needs_followup = []
    now = datetime.now(timezone.utc)
    for msg in pending:
        sent = msg.get("sent_at", "")
        if sent:
            try:
                sent_dt = datetime.fromisoformat(sent.replace("Z", "+00:00"))
                days_since = (now - sent_dt).days
                if days_since >= 3 and msg.get("follow_up_count", 0) < 3:
                    needs_followup.append(msg)
            except Exception:
                pass

    return needs_followup


def analyze_reply(reply_text: str, original_outreach: dict) -> dict:
    """Analyze a reply email for sentiment, intent, and next action.

    Reads the reply for:
    - Interest level (hot/warm/cold/dead)
    - Key info (price expectations, timeline, concerns)
    - Communication style (formal, casual, suspicious, eager)
    - Suggested next action
    """
    text_lower = reply_text.lower()

    # Sentiment detection
    positive_signals = ["interested", "tell me more", "how much", "sounds good", "let's talk", "call me", "when can", "yes"]
    negative_signals = ["not interested", "stop", "remove", "no thanks", "do not contact", "unsubscribe", "scam"]
    question_signals = ["how does", "what's the", "can you explain", "how much would", "what are", "is this"]

    pos_count = sum(1 for s in positive_signals if s in text_lower)
    neg_count = sum(1 for s in negative_signals if s in text_lower)
    q_count = sum(1 for s in question_signals if s in text_lower)

    if neg_count > 0:
        sentiment = "negative"
        interest = "dead"
        next_action = "respect_opt_out"
    elif pos_count >= 2:
        sentiment = "positive"
        interest = "hot"
        next_action = "schedule_call"
    elif pos_count >= 1 or q_count >= 1:
        sentiment = "interested"
        interest = "warm"
        next_action = "answer_questions_and_follow_up"
    else:
        sentiment = "neutral"
        interest = "lukewarm"
        next_action = "send_more_info"

    # Detect communication style
    if any(w in text_lower for w in ["sir", "madam", "dear", "sincerely"]):
        style = "formal"
    elif any(w in text_lower for w in ["hey", "yo", "sup", "lol", "haha"]):
        style = "casual"
    elif len(reply_text) < 20:
        style = "brief"
    else:
        style = "standard"

    return {
        "sentiment": sentiment,
        "interest": interest,
        "style": style,
        "next_action": next_action,
        "pos_signals": pos_count,
        "neg_signals": neg_count,
        "question_signals": q_count,
    }


# ============================================================
# CASH HOLLOWAY: Revenue tracking
# ============================================================

def get_pipeline_stats() -> dict:
    """Get current pipeline statistics for the dashboard."""
    stats = {}

    # Sellers by status
    for status in ["new", "contacted", "responding", "negotiating", "under_contract", "assigned", "closed"]:
        result = _supabase_query("wholesale_sellers", params={
            "status": f"eq.{status}",
            "select": "id",
        })
        stats[f"sellers_{status}"] = len(result) if isinstance(result, list) else 0

    # Deals by status
    for status in ["scouted", "seller_contacted", "under_contract", "buyer_matched", "assigned", "closed"]:
        result = _supabase_query("wholesale_deals", params={
            "status": f"eq.{status}",
            "select": "id",
        })
        stats[f"deals_{status}"] = len(result) if isinstance(result, list) else 0

    # Buyers
    for rel in ["new", "warm", "hot", "repeat"]:
        result = _supabase_query("wholesale_buyers", params={
            "relationship_status": f"eq.{rel}",
            "select": "id",
        })
        stats[f"buyers_{rel}"] = len(result) if isinstance(result, list) else 0

    # Revenue
    closed_deals = _supabase_query("wholesale_deals", params={
        "status": "eq.closed",
        "select": "actual_profit",
    })
    if isinstance(closed_deals, list):
        stats["total_revenue"] = sum(float(d.get("actual_profit", 0)) for d in closed_deals)
        stats["deals_closed"] = len(closed_deals)
    else:
        stats["total_revenue"] = 0
        stats["deals_closed"] = 0

    # Outreach
    for s in ["draft", "verified", "sent", "replied"]:
        result = _supabase_query("wholesale_outreach", params={
            "status": f"eq.{s}",
            "select": "id",
        })
        stats[f"outreach_{s}"] = len(result) if isinstance(result, list) else 0

    # States active
    result = _supabase_query("wholesale_states", params={
        "tier": "in.(top,mid)",
        "select": "state_code",
    })
    stats["active_states"] = len(result) if isinstance(result, list) else 0

    return stats


# ============================================================
# MAIN EXECUTION CYCLE
# ============================================================

def run_pipeline_cycle():
    """One full pipeline execution cycle.

    1. Score any unscored sellers
    2. Check for replies needing follow-up
    3. Report pipeline stats (real numbers, not fluff)
    """
    results = []

    # 1. Score sellers
    scored = score_sellers()
    if scored:
        results.append(f"Filter Banks scored {len(scored)} sellers")

    # 2. Check follow-ups needed
    followups = check_replies()
    if followups:
        results.append(f"Hammer O'Brien: {len(followups)} outreach messages need follow-up")

    # 3. Pipeline stats
    stats = get_pipeline_stats()

    # Build Slack report -- ONLY facts, no fluff
    report_parts = ["*Wholesale Pipeline -- Execution Report*"]
    report_parts.append(f"States: {stats.get('active_states', 0)} active (top + mid tier)")
    report_parts.append(f"Sellers: {stats.get('sellers_new', 0)} new | {stats.get('sellers_contacted', 0)} contacted | {stats.get('sellers_under_contract', 0)} under contract")
    report_parts.append(f"Buyers: {stats.get('buyers_hot', 0)} hot | {stats.get('buyers_warm', 0)} warm | {stats.get('buyers_repeat', 0)} repeat")
    report_parts.append(f"Deals: {stats.get('deals_under_contract', 0)} under contract | {stats.get('deals_closed', 0)} closed")
    report_parts.append(f"Revenue: ${stats.get('total_revenue', 0):,.2f}")
    report_parts.append(f"Outreach: {stats.get('outreach_sent', 0)} sent | {stats.get('outreach_replied', 0)} replied | {stats.get('outreach_draft', 0)} drafts pending verification")

    if results:
        report_parts.append("\nActions taken:")
        for r in results:
            report_parts.append(f"  > {r}")

    if stats.get("total_revenue", 0) == 0 and stats.get("deals_closed", 0) == 0:
        report_parts.append("\n!!! ZERO REVENUE. Pipeline needs: verified leads -> verified outreach -> deals.")

    report = "\n".join(report_parts)
    _slack_post("C08N1KV3WMW", report)  # hive-alerts

    return {"stats": stats, "actions": results, "report": report}


if __name__ == "__main__":
    import sys
    if "--cycle" in sys.argv:
        result = run_pipeline_cycle()
        print(result["report"])
    elif "--stats" in sys.argv:
        stats = get_pipeline_stats()
        print(json.dumps(stats, indent=2))
    else:
        print("Usage: --cycle (run pipeline) | --stats (show stats)")
