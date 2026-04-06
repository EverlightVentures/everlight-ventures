"""
Rex Straight Line System -- Jordan Belfort's negotiation framework for Rex.

The Straight Line selling system applied to wholesale real estate:
1. Every seller must reach 10/10 certainty on three axes before they sell
2. Qualifying questions establish motivation, urgency, and equity
3. Counter-negotiation follows strict ARV-based rules
4. Psychological close tactics auto-apply based on conversation stage

This module is the negotiation brain. rex_closer.py calls these functions
to decide what to say and when to say it.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="[Rex StraightLine %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_straight_line")

AGENT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# THE THREE CERTAINTIES (1-10 scale)
# ---------------------------------------------------------------------------
# 1. PRODUCT  -- "Is this cash offer fair?"
# 2. COMPANY  -- "Is Everlight Ventures legit?"
# 3. PERSON   -- "Can I trust Rich / this operation?"
#
# If any axis is below 7, the deal will NOT close. Rex targets whichever
# is lowest and addresses it with the right tactic.
# ---------------------------------------------------------------------------

CERTAINTY_THRESHOLD = 7  # minimum score to close

# Keywords that signal certainty levels per axis
PRODUCT_POSITIVE = [
    "fair", "reasonable", "makes sense", "good offer", "close to what",
    "not bad", "could work", "in the ballpark",
]
PRODUCT_NEGATIVE = [
    "too low", "lowball", "insulting", "worth more", "not enough",
    "way too low", "ridiculous", "no way", "more than that", "higher",
]
COMPANY_POSITIVE = [
    "legit", "website", "reviews", "other deals", "been around",
    "how long", "references", "professional",
]
COMPANY_NEGATIVE = [
    "scam", "fraud", "never heard", "suspicious", "how do i know",
    "trust", "who are you", "sketchy", "not sure about your company",
]
PERSON_POSITIVE = [
    "appreciate", "helpful", "straightforward", "honest", "thanks",
    "like dealing with you", "responsive", "good to work with",
]
PERSON_NEGATIVE = [
    "pushy", "aggressive", "stop calling", "pressure", "salesman",
    "used car", "don't trust you", "leave me alone",
]


# ---------------------------------------------------------------------------
# QUALIFYING QUESTIONS (discovery phase)
# ---------------------------------------------------------------------------

QUALIFYING_QUESTIONS = {
    "timeline": "What's your ideal timeline to sell?",
    "mortgage": "Is there a mortgage balance or any liens on the property?",
    "condition": "What condition would you say the property is in, 1-10?",
    "motivation": "What would you do with the cash from the sale?",
    "competition": "Have you explored other options like listing with an agent?",
    "close_trigger": "What would need to happen for you to say yes today?",
}


def get_qualifying_message(first_name: str = "there") -> str:
    """Build the full qualifying message for initial contact."""
    questions = (
        f"Hi {first_name},\n\n"
        "Great to hear from you! A few quick questions so I can put "
        "together the best possible offer:\n\n"
        f"1. {QUALIFYING_QUESTIONS['timeline']}\n"
        f"2. {QUALIFYING_QUESTIONS['mortgage']}\n"
        f"3. {QUALIFYING_QUESTIONS['condition']}\n"
        f"4. {QUALIFYING_QUESTIONS['motivation']}\n"
        f"5. {QUALIFYING_QUESTIONS['competition']}\n\n"
        "Reply and I'll have a cash offer for you within the hour.\n\n"
        "Rich\nEverlight Ventures"
    )
    return questions


# ---------------------------------------------------------------------------
# CERTAINTY ANALYZER
# ---------------------------------------------------------------------------

def _score_axis(message: str, positive_kw: list, negative_kw: list) -> int:
    """Score a single certainty axis from 1-10 based on keyword signals."""
    msg = message.lower()
    pos_hits = sum(1 for kw in positive_kw if kw in msg)
    neg_hits = sum(1 for kw in negative_kw if kw in msg)

    # Base score is 5 (neutral). Shift up or down based on signals.
    score = 5 + (pos_hits * 2) - (neg_hits * 2)
    return max(1, min(10, score))


def analyze_seller_response(message: str, deal: dict) -> dict:
    """
    Analyze a seller's reply and return certainty scores + recommended action.

    Returns:
        {
            "certainty": {"product": int, "company": int, "person": int},
            "lowest_axis": str,
            "lowest_score": int,
            "recommended_action": str,
            "script": str,
            "tactic": str,
        }
    """
    product_score = _score_axis(message, PRODUCT_POSITIVE, PRODUCT_NEGATIVE)
    company_score = _score_axis(message, COMPANY_POSITIVE, COMPANY_NEGATIVE)
    person_score = _score_axis(message, PERSON_POSITIVE, PERSON_NEGATIVE)

    certainty = {
        "product": product_score,
        "company": company_score,
        "person": person_score,
    }

    # Find lowest axis
    lowest_axis = min(certainty, key=certainty.get)
    lowest_score = certainty[lowest_axis]

    # Determine recommended action
    action = "continue"
    script = ""
    tactic = ""

    addr = deal.get("address", "the property")
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    offer = deal.get("offer", 0)

    if lowest_score >= CERTAINTY_THRESHOLD:
        # All three axes are high enough -- push for close
        action = "close"
        tactic = "assumptive_close"
        script = (
            f"Hi {first},\n\n"
            f"Great -- it sounds like we're on the same page about {addr}. "
            f"I'll have the purchase agreement sent over today for your signature. "
            f"Once you sign, we can close within 7 days and you'll have your "
            f"cash in hand.\n\n"
            f"Anything else you need from me before we move forward?\n\n"
            f"Rich\nEverlight Ventures"
        )

    elif lowest_axis == "product":
        # They think the offer is too low
        action = "address_product"
        tactic = "reframe_value"
        script = (
            f"Hi {first},\n\n"
            f"I hear you on wanting more for {addr}. Let me break down "
            f"how I got to my number:\n\n"
            f"- Cash offer, no bank delays or appraisal risk\n"
            f"- I cover all closing costs (saves you 3-6%)\n"
            f"- No repairs needed -- I buy as-is\n"
            f"- Close in 7 days vs. 60-90 days on the open market\n\n"
            f"When you factor in agent commissions (6%), repairs, carrying costs, "
            f"and time on market, my offer nets you about the same -- but you "
            f"get certainty and speed.\n\n"
            f"What number would make this work for you?\n\n"
            f"Rich\nEverlight Ventures"
        )

    elif lowest_axis == "company":
        # They don't know if we're legit
        action = "address_company"
        tactic = "credibility_proof"
        script = (
            f"Hi {first},\n\n"
            f"Completely fair question. Everlight Ventures is a registered "
            f"real estate investment company based in Georgia. Here's why "
            f"sellers work with us:\n\n"
            f"- We've closed deals across GA, TX, OH, MO, and FL\n"
            f"- Licensed, insured, and we use a reputable title company "
            f"for every transaction\n"
            f"- We put up earnest money -- real skin in the game\n"
            f"- You can verify us at everlightventures.io\n\n"
            f"I'm happy to provide references from sellers we've worked with. "
            f"Would that help?\n\n"
            f"Rich\nEverlight Ventures"
        )

    elif lowest_axis == "person":
        # They don't trust the salesperson
        action = "address_person"
        tactic = "rapport_build"
        script = (
            f"Hi {first},\n\n"
            f"I appreciate your candor. I know getting unsolicited offers "
            f"can feel off. Here's my approach -- no pressure, no gimmicks. "
            f"I look at properties that might benefit from a quick cash sale "
            f"and reach out to see if the timing is right.\n\n"
            f"If it's not the right time, I respect that completely. "
            f"But if you're even a little curious about what your property "
            f"could sell for today, I'm happy to walk you through the numbers "
            f"with zero obligation.\n\n"
            f"What questions can I answer for you?\n\n"
            f"Rich\nEverlight Ventures"
        )

    result = {
        "certainty": certainty,
        "lowest_axis": lowest_axis,
        "lowest_score": lowest_score,
        "recommended_action": action,
        "script": script,
        "tactic": tactic,
    }

    log.info(
        f"Certainty analysis for {addr}: "
        f"product={product_score}, company={company_score}, person={person_score} "
        f"-- action={action}"
    )
    return result


# ---------------------------------------------------------------------------
# COUNTER-NEGOTIATION LOGIC
# ---------------------------------------------------------------------------

def calculate_counter(seller_ask: float, mao: float, arv: float) -> dict:
    """
    Calculate the counter-offer strategy based on seller's asking price
    relative to ARV.

    Args:
        seller_ask: what the seller wants
        mao: our maximum allowable offer
        arv: after repair value

    Returns:
        dict with action, counter_price, max_price, script
    """
    if arv <= 0:
        return {
            "action": "skip",
            "script": "Cannot calculate -- ARV is zero or unknown.",
        }

    spread = seller_ask / arv  # what % of ARV they want

    if spread <= 0.70:
        # Under 70% ARV -- ACCEPT IMMEDIATELY
        log.info(f"Seller ask ${seller_ask:,.0f} is {spread:.0%} of ARV -- ACCEPTING")
        return {
            "action": "accept",
            "price": seller_ask,
            "script": "",
        }

    elif spread <= 0.75:
        # 70-75% -- counter at 68%, settle at 72%
        counter = round(arv * 0.68 / 500) * 500
        max_price = round(arv * 0.72 / 500) * 500
        return {
            "action": "counter",
            "counter_price": counter,
            "max_price": max_price,
            "script": (
                f"I appreciate the number. Based on my analysis, the most "
                f"I can do is ${counter:,.0f}. That accounts for repairs "
                f"and carrying costs. Can we meet somewhere around there?"
            ),
        }

    elif spread <= 0.80:
        # 75-80% -- counter at 70%, walk if they won't budge
        counter = round(arv * 0.70 / 500) * 500
        max_price = round(arv * 0.73 / 500) * 500
        return {
            "action": "counter",
            "counter_price": counter,
            "max_price": max_price,
            "script": (
                f"I want to make this work, but at ${seller_ask:,.0f} the "
                f"numbers don't pencil. My max is ${counter:,.0f}. If that "
                f"works, I can have paperwork to you today."
            ),
        }

    else:
        # Over 80% -- graceful exit with door open
        log.info(f"Seller ask ${seller_ask:,.0f} is {spread:.0%} of ARV -- WALKING")
        return {
            "action": "walk",
            "script": (
                "I respect your position. At that price point, a traditional "
                "listing might serve you better. If circumstances change, my "
                "offer stands. I wish you the best."
            ),
        }


# ---------------------------------------------------------------------------
# PSYCHOLOGICAL CLOSE TACTICS
# ---------------------------------------------------------------------------

TACTICS = {
    "takeaway": {
        "name": "Takeaway Close",
        "when": "seller_hesitates",
        "template": (
            "I understand, {first}. I actually have two other properties "
            "I'm looking at this week, so no pressure at all. If this one "
            "doesn't work out, I'll move on to those. But if you change "
            "your mind, my number is the same."
        ),
    },
    "split_difference": {
        "name": "Split the Difference",
        "when": "spread_5_to_10_pct",
        "template": (
            "Look, I'm at ${our_price:,.0f} and you're at ${their_price:,.0f}. "
            "Let's meet in the middle at ${split_price:,.0f} and get this done "
            "today. That's a fair deal for both of us."
        ),
    },
    "silence": {
        "name": "Post-Offer Silence",
        "when": "offer_just_sent",
        "template": "",  # no message -- the silence IS the tactic
        "wait_hours": 24,
    },
    "nibble": {
        "name": "The Nibble",
        "when": "after_agreement",
        "template": (
            "Great, {first} -- one last thing. Since I'm covering all closing "
            "costs on my end, can we push the close date to 14 days instead "
            "of 30? That actually saves us both money on carrying costs."
        ),
    },
    "urgency": {
        "name": "Urgency Injection",
        "when": "seller_stalling",
        "template": (
            "Just a heads up, {first} -- my investment group has capital "
            "allocated through end of month. After that, I can't guarantee "
            "this offer holds. Want to lock it in while the funds are "
            "available?"
        ),
    },
    "pain_amplify": {
        "name": "Pain Amplification",
        "when": "distress_signal_present",
        "template": (
            "I know dealing with {distress_type} is stressful, {first}. "
            "Every month that passes is another month of {pain_detail}. "
            "The sooner we close, the sooner that stops. Let me take this "
            "off your plate."
        ),
    },
}

# Distress type to pain detail mapping
PAIN_DETAILS = {
    "pre_foreclosure": "missed payments and damaged credit",
    "code_violation": "fines piling up from the city",
    "tax_lien": "tax penalties accruing interest",
    "tax_delinquent": "tax debt growing with interest and penalties",
    "probate": "legal fees and estate carrying costs",
    "divorce": "shared financial obligations on a property neither party wants",
    "vacant": "vandalism risk, insurance costs, and property deterioration",
    "lis_pendens": "legal proceedings hanging over the property",
}


def get_close_tactic(deal: dict, conversation_history: list = None) -> dict:
    """
    Determine which close tactic to use based on deal stage and history.

    Args:
        deal: the deal dict with stage, offer, distress info
        conversation_history: list of conversation entries

    Returns:
        dict with tactic_key, tactic_name, message (ready to send)
    """
    if conversation_history is None:
        conversation_history = deal.get("conversation", [])

    stage = deal.get("stage", "")
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    offer = deal.get("offer", 0)
    lead_type = deal.get("lead_type", "")

    # Count seller messages to gauge engagement
    seller_msgs = [c for c in conversation_history if c.get("role") == "seller"]
    rex_msgs = [c for c in conversation_history if c.get("role") == "rex"]

    # --- TACTIC SELECTION LOGIC ---

    # 1. Just sent offer -- enforce 24h silence
    if stage == "offer_sent" and len(seller_msgs) == 0:
        return {
            "tactic_key": "silence",
            "tactic_name": "Post-Offer Silence",
            "message": "",
            "wait_hours": 24,
            "action": "wait",
        }

    # 2. Seller just agreed -- nibble for better terms
    if stage == "accepted" or any(
        w in (seller_msgs[-1]["message"].lower() if seller_msgs else "")
        for w in ["yes", "deal", "agreed", "let's do it", "sounds good"]
    ):
        msg = TACTICS["nibble"]["template"].format(first=first)
        return {
            "tactic_key": "nibble",
            "tactic_name": "The Nibble",
            "message": msg,
            "action": "send",
        }

    # 3. Seller countered -- check if split-the-difference applies
    last_seller_msg = seller_msgs[-1]["message"] if seller_msgs else ""
    amounts = re.findall(r'\$?([\d,]+)', last_seller_msg)
    if amounts and offer > 0:
        their_price = int(amounts[0].replace(",", ""))
        gap_pct = abs(their_price - offer) / max(offer, 1)
        if 0.05 <= gap_pct <= 0.15:
            split_price = round((offer + their_price) / 2 / 500) * 500
            msg = TACTICS["split_difference"]["template"].format(
                our_price=offer,
                their_price=their_price,
                split_price=split_price,
            )
            return {
                "tactic_key": "split_difference",
                "tactic_name": "Split the Difference",
                "message": msg,
                "action": "send",
            }

    # 4. Distress signal present -- amplify pain
    if lead_type and lead_type in PAIN_DETAILS:
        pain = PAIN_DETAILS[lead_type]
        distress_label = lead_type.replace("_", " ")
        msg = TACTICS["pain_amplify"]["template"].format(
            first=first,
            distress_type=distress_label,
            pain_detail=pain,
        )
        return {
            "tactic_key": "pain_amplify",
            "tactic_name": "Pain Amplification",
            "message": msg,
            "action": "send",
        }

    # 5. Multiple messages with no progress -- takeaway
    if len(rex_msgs) >= 3 and stage == "offer_sent":
        msg = TACTICS["takeaway"]["template"].format(first=first)
        return {
            "tactic_key": "takeaway",
            "tactic_name": "Takeaway Close",
            "message": msg,
            "action": "send",
        }

    # 6. Default -- urgency injection
    msg = TACTICS["urgency"]["template"].format(first=first)
    return {
        "tactic_key": "urgency",
        "tactic_name": "Urgency Injection",
        "message": msg,
        "action": "send",
    }


# ---------------------------------------------------------------------------
# FULL RESPONSE GENERATOR
# ---------------------------------------------------------------------------

def generate_response(deal: dict, seller_message: str) -> dict:
    """
    Generate the full response to a seller message using the Straight Line system.

    Combines certainty analysis, counter-negotiation, and close tactics into
    a single recommended response.

    Args:
        deal: the deal dict
        seller_message: the seller's latest message

    Returns:
        {
            "response_text": str,        -- the email body to send
            "action": str,               -- accept/counter/walk/address_*/close/wait
            "certainty": dict,            -- certainty scores
            "tactic_used": str,           -- which tactic was applied
            "counter_details": dict|None, -- counter-offer details if applicable
            "should_send": bool,          -- False if silence tactic is active
        }
    """
    addr = deal.get("address", "the property")
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    offer = deal.get("offer", 0)
    arv = deal.get("estimated_arv", 0) or deal.get("offer_details", {}).get("arv", 0)

    # Step 1: Analyze certainty
    analysis = analyze_seller_response(seller_message, deal)
    action = analysis["recommended_action"]
    certainty = analysis["certainty"]

    response_text = ""
    counter_details = None
    tactic_used = analysis.get("tactic", "")
    should_send = True

    # Step 2: Check for counter-offer in seller's message
    amounts = re.findall(r'\$?([\d,]+)', seller_message)
    seller_counter = None
    if amounts:
        parsed = int(amounts[0].replace(",", ""))
        # Only treat as a counter if it looks like a property price
        if parsed >= 20_000:
            seller_counter = parsed

    # Step 3: Route to appropriate handler

    # 3a. Seller gave a counter-offer number
    if seller_counter and arv > 0:
        mao = deal.get("offer_details", {}).get("offer", offer)
        counter_details = calculate_counter(seller_counter, mao, arv)
        counter_action = counter_details["action"]

        if counter_action == "accept":
            response_text = (
                f"Hi {first},\n\n"
                f"${seller_counter:,.0f} works for me. I'll have the "
                f"purchase agreement for {addr} sent over today. Once you "
                f"sign, we close within 7 days.\n\n"
                f"Rich\nEverlight Ventures"
            )
            action = "accept"

        elif counter_action == "counter":
            counter_price = counter_details["counter_price"]
            # Check if split-the-difference applies
            gap_pct = abs(seller_counter - counter_price) / max(counter_price, 1)
            if 0.05 <= gap_pct <= 0.15:
                split = round((counter_price + seller_counter) / 2 / 500) * 500
                response_text = (
                    f"Hi {first},\n\n"
                    f"I appreciate you coming back with a number on {addr}. "
                    f"I'm at ${counter_price:,.0f} and you're at "
                    f"${seller_counter:,.0f}. Let's meet in the middle at "
                    f"${split:,.0f} and get this done today.\n\n"
                    f"If that works, I'll have the paperwork over within "
                    f"the hour.\n\n"
                    f"Rich\nEverlight Ventures"
                )
                tactic_used = "split_difference"
            else:
                response_text = (
                    f"Hi {first},\n\n"
                    f"{counter_details['script']}\n\n"
                    f"Rich\nEverlight Ventures"
                )
            action = "counter"

        elif counter_action == "walk":
            response_text = (
                f"Hi {first},\n\n"
                f"{counter_details['script']}\n\n"
                f"Rich\nEverlight Ventures"
            )
            action = "walk"

    # 3b. Certainty-based response (no counter-offer number)
    elif action == "close":
        response_text = analysis["script"]
        tactic_used = "assumptive_close"

    elif action in ("address_product", "address_company", "address_person"):
        response_text = analysis["script"]

    else:
        # Use close tactic to generate response
        tactic_result = get_close_tactic(deal)
        tactic_used = tactic_result["tactic_key"]

        if tactic_result["action"] == "wait":
            should_send = False
            response_text = ""
        else:
            response_text = (
                f"Hi {first},\n\n"
                f"{tactic_result['message']}\n\n"
                f"Rich\nEverlight Ventures"
            )

    result = {
        "response_text": response_text,
        "action": action,
        "certainty": certainty,
        "tactic_used": tactic_used,
        "counter_details": counter_details,
        "should_send": should_send,
    }

    log.info(
        f"Straight Line response for {addr}: "
        f"action={action}, tactic={tactic_used}, send={should_send}"
    )
    return result


# ---------------------------------------------------------------------------
# SILENCE ENFORCEMENT -- check if we should hold off on outreach
# ---------------------------------------------------------------------------

def should_enforce_silence(deal: dict) -> bool:
    """
    Returns True if the 24-hour post-offer silence window is still active.
    After sending an offer, do NOT follow up for 24 hours.
    """
    offer_sent_at = deal.get("offer_sent_at")
    if not offer_sent_at:
        return False

    try:
        sent_dt = datetime.fromisoformat(offer_sent_at)
        now = datetime.now(timezone.utc)
        hours_since = (now - sent_dt).total_seconds() / 3600
        if hours_since < 24:
            log.info(
                f"Silence enforced for {deal.get('address', '?')} -- "
                f"{hours_since:.1f}h since offer sent (need 24h)"
            )
            return True
    except (ValueError, TypeError):
        pass

    return False


# ---------------------------------------------------------------------------
# NIBBLE -- post-acceptance term improvement
# ---------------------------------------------------------------------------

def get_nibble_message(deal: dict) -> str:
    """
    After the seller agrees, send the nibble to improve terms.
    Typically: push close date from 30 to 14 days (saves carrying costs
    and reduces seller's window to back out).
    """
    first = deal.get("owner_name", "").split()[0] if deal.get("owner_name") else "there"
    addr = deal.get("address", "the property")

    return (
        f"Hi {first},\n\n"
        f"Glad we could make {addr} work. One last thing -- since I'm "
        f"covering all closing costs on my end, can we push the close date "
        f"to 14 days instead of 30? That actually saves us both money on "
        f"carrying costs and gets you your cash faster.\n\n"
        f"I'll have the updated agreement over shortly.\n\n"
        f"Rich\nEverlight Ventures"
    )


if __name__ == "__main__":
    # Quick test with sample data
    sample_deal = {
        "address": "123 Main St",
        "owner_name": "John Smith",
        "estimated_arv": 200_000,
        "offer": 120_000,
        "stage": "offer_sent",
        "lead_type": "pre_foreclosure",
        "conversation": [],
        "offer_details": {"arv": 200_000, "offer": 120_000},
    }

    # Test certainty analysis
    print("--- Test: Seller thinks offer is too low ---")
    result = analyze_seller_response(
        "That's way too low. The house is worth more than that.",
        sample_deal,
    )
    print(json.dumps(result, indent=2))

    # Test counter calculation
    print("\n--- Test: Seller counters at 75% ARV ---")
    counter = calculate_counter(150_000, 120_000, 200_000)
    print(json.dumps(counter, indent=2))

    # Test full response
    print("\n--- Test: Full response generation ---")
    resp = generate_response(sample_deal, "I was thinking more like $160,000")
    print(json.dumps(resp, indent=2, default=str))
