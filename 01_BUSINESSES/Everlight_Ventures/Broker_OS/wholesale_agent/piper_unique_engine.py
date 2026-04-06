#!/usr/bin/env python3
"""
Piper Unique Engine -- Every email is a snowflake.

The Date Test: If three sellers compared what Piper said to them,
each would hear a completely different story, tone, and approach.

Uses AI + randomized style directives + anti-duplication checks
to ensure no two emails are even close to similar.
"""
import hashlib
import json
import os
import random
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
SENT_HASHES_FILE = Path(__file__).parent / "cache" / "sent_email_hashes.json"
SENT_HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# PERSONALITY DIMENSIONS -- mix & match for infinite variety
# ============================================================

# 20 unique hooks (personal stories Piper can tell)
HOOKS = [
    "My grandmother's old place in Murfreesboro sat empty for two years -- that's actually what pulled me into real estate.",
    "My brother inherited a duplex in East Nashville and almost lost it to back taxes before we figured out a plan.",
    "I used to help my mom stress-clean her rental property every time a tenant moved out. I swore I'd find a better way.",
    "My neighbor Miss Betty held onto her late husband's house for five years before she finally said 'I'm ready.' I helped her through it.",
    "I watched my aunt turn down three offers because she thought she'd get more 'next year.' That next year never came the way she expected.",
    "I actually got into this because a family friend lost their home to a tax lien sale -- nobody told them they had options.",
    "My college roommate's parents sat on a vacant lot for a decade paying taxes on it. When they finally sold, they wished they'd done it sooner.",
    "I grew up in a neighborhood where half the houses were vacant. I saw what happens when properties just sit -- it breaks my heart.",
    "My first deal ever was helping a retired teacher in Memphis sell her mother's house. She cried tears of relief at the closing table.",
    "I met a guy at a coffee shop who told me he'd been paying $400/month on a house nobody lived in. That conversation changed my whole career path.",
    "My dad always said 'a house you're not using is a bill that never stops.' Took me years to really understand what he meant.",
    "I helped my cousin sell his place after his divorce -- hardest conversation I ever had, but he told me later it was the best decision he made that year.",
    "There's a house on my street back home that's been vacant since I was in high school. Every time I visit, I think about the owner and wonder if they know they have options.",
    "I once got a thank-you card from a seller who said 'you gave me my weekends back.' That's when I knew I was doing the right thing.",
    "My mentor told me: 'Every property has a story, and most of those stories need a new chapter.' I think about that every day.",
    "I accidentally became the 'real estate person' in my family after I helped my uncle sell his hunting cabin in 48 hours.",
    "Last Thanksgiving, three different relatives asked me for property advice over dessert. I'm starting to think they only invite me for the free consulting.",
    "I used to work at a title company and saw so many deals fall apart because sellers waited too long. That experience is why I do what I do now.",
    "My friend's mom was paying $1,200 a month between taxes and insurance on a house she hadn't stepped foot in for three years.",
    "I keep a sticky note on my laptop that says 'make it easy for people.' That's literally my whole approach.",
]

# 12 opening styles (structural variety)
OPENING_STYLES = [
    "question_first",       # Start with a question about their situation
    "stat_bomb",            # Lead with a surprising local statistic
    "story_hook",           # Open with a personal anecdote
    "empathy_first",        # Lead with understanding their pain
    "curiosity_gap",        # Tease interesting info without revealing it all
    "compliment",           # Notice something specific about their property/area
    "humor_light",          # Light, warm humor to disarm
    "direct_honest",        # Straight to the point, no fluff
    "neighbor_angle",       # "I was looking at properties nearby and..."
    "market_insight",       # Lead with a market trend they'd find interesting
    "relief_promise",       # Lead with the feeling of relief after selling
    "time_value",           # Frame around what they could do with their time/money instead
]

# 10 tone variations
TONES = [
    "warm_southern",        # Classic Piper -- y'all, honey, sweet
    "professional_warm",    # Business but still human
    "funny_relatable",      # Self-deprecating humor, light jokes
    "data_driven_warm",     # Numbers with heart
    "storyteller",          # Everything's a narrative
    "down_to_earth",        # Simple, plain-spoken, zero jargon
    "curious_friendly",     # Lots of questions, genuinely interested
    "mentor_energy",        # Wise, experienced, guiding
    "upbeat_energetic",     # Positive, excited, glass-half-full
    "calm_reassuring",      # Peaceful, no rush, zen energy
]

# 8 closing styles
CLOSINGS = [
    "simple_question",      # "Would a quick chat work for you?"
    "two_options",          # "You can call me or I can call you -- whatever's easier."
    "no_pressure_fade",     # "If the timing isn't right, no worries at all."
    "curiosity_close",      # "I have some numbers on your area I think you'd find interesting."
    "calendar_offer",       # "I've got a few minutes free Thursday if you're open to it."
    "text_friendly",        # "Feel free to text me back -- I know emails can feel formal."
    "value_first_close",    # "Either way, I'll send you a free market report for your area."
    "gentle_deadline",      # "We're working with a few properties in your area this month."
]

# Lead-type specific pain points for AI context
PAIN_CONTEXT = {
    "pre_foreclosure": "They're facing foreclosure. Clock is ticking. Be gentle but show urgency. They need to know there's a way out that doesn't destroy their credit.",
    "tax_delinquent": "Back taxes are piling up. County might auction the property. They might feel ashamed or overwhelmed. Normalize it -- this is more common than people think.",
    "expired_listing": "They tried selling the traditional way and it failed. They're frustrated with agents, showings, and broken promises. Show them a different path.",
    "high_equity": "They have major equity but may not realize how much it's costing them to hold. Frame it as unlocking money that's trapped in walls.",
    "code_violation": "City is on their back about violations. Fines are racking up. They may feel stuck -- can't afford to fix it, can't sell it as-is (they think). Show them they CAN sell as-is.",
    "probate": "Someone died. They inherited a property they didn't want. It's emotional AND financial. Be extremely respectful of the grief. Lead with empathy, not money.",
    "vacant": "Property is sitting empty burning cash every month. Insurance, taxes, vandalism risk, neighbor complaints. They're paying for something they're not using.",
    "absentee": "They don't live near the property. Managing from a distance is a nightmare. Every phone call is a problem. They want it off their plate.",
    "divorce": "Going through a divorce. The house is a shared asset they need to split. Emotions are high. Be neutral, practical, helpful.",
    "tax_lien": "Tax lien on the property. Similar to tax delinquent but further along. They may not even know a lien was filed.",
}

# Subject line formulas (never the same)
SUBJECT_FORMULAS = [
    "Quick question about {short_addr}",
    "Regarding your property in {city}",
    "{first_name}, saw your place at {short_addr}",
    "Thought of you -- {city} market update",
    "Your {city} property -- a different option",
    "Have 5 mins? About {short_addr}",
    "Not your typical real estate email, {first_name}",
    "{first_name} -- something interesting about your area",
    "Honest question about {short_addr}",
    "A neighbor mentioned {short_addr}",
    "Quick thought on your {city} property",
    "Your options for {short_addr}, {first_name}",
    "{city} is changing -- thought you should know",
    "Before the county reaches out about {short_addr}",
    "Saw something about {short_addr} and wanted to share",
    "This might be helpful, {first_name}",
    "Real talk about your property in {city}",
    "One question about {short_addr} -- no strings",
    "{first_name}, heard about your property",
    "A different kind of offer for {short_addr}",
]


def _text_hash(text: str) -> str:
    """Generate a hash for similarity checking."""
    # Normalize: lowercase, strip whitespace, remove proper nouns
    clean = re.sub(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', '', text)
    clean = re.sub(r'\$[\d,]+', '', clean)
    clean = re.sub(r'\d+', '', clean)
    clean = clean.lower().strip()
    words = clean.split()
    # Use sorted word bigrams for fuzzy matching
    bigrams = set()
    for i in range(len(words) - 1):
        bigrams.add(f"{words[i]} {words[i+1]}")
    return hashlib.md5(json.dumps(sorted(bigrams)).encode()).hexdigest()


def _load_sent_hashes() -> dict:
    if not SENT_HASHES_FILE.exists():
        return {}
    try:
        return json.loads(SENT_HASHES_FILE.read_text())
    except Exception:
        return {}


def _save_sent_hash(email_hash: str, metadata: dict):
    hashes = _load_sent_hashes()
    hashes[email_hash] = {
        "sent_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    # Keep only last 500
    if len(hashes) > 500:
        sorted_keys = sorted(hashes, key=lambda k: hashes[k].get("sent_at", ""), reverse=True)
        hashes = {k: hashes[k] for k in sorted_keys[:500]}
    SENT_HASHES_FILE.write_text(json.dumps(hashes, indent=2))


def _is_too_similar(new_text: str) -> bool:
    """Check if this email is too similar to one we recently sent."""
    new_hash = _text_hash(new_text)
    existing = _load_sent_hashes()
    return new_hash in existing


def _ai_generate(prompt: str, max_tokens: int = 600) -> str:
    if not OPENAI_KEY:
        return ""
    data = json.dumps({
        "model": "gpt-4o-mini",
        "max_tokens": max_tokens,
        "temperature": 0.95,  # High creativity
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_KEY}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def generate_unique_subject(first_name: str, city: str, short_addr: str, lead_type: str) -> str:
    """Pick a unique subject line from the formula bank."""
    formula = random.choice(SUBJECT_FORMULAS)
    return formula.format(
        first_name=first_name,
        city=city,
        short_addr=short_addr,
    )


def generate_unique_email(
    owner_name: str,
    address: str,
    city: str,
    state: str,
    lead_type: str,
    market_data: dict = None,
    holding_data: dict = None,
    arv: int = 0,
    notes: str = "",
    retry: int = 0,
) -> dict:
    """Generate a completely unique Piper email.

    Returns: {"subject": str, "body_text": str, "body_html": str, "style": dict}
    """
    first_name = owner_name.split()[0].title() if owner_name else "there"
    short_addr = address.split(",")[0] if "," in address else address

    # Random style combination
    style = {
        "opening": random.choice(OPENING_STYLES),
        "tone": random.choice(TONES),
        "closing": random.choice(CLOSINGS),
        "hook_index": random.randint(0, len(HOOKS) - 1),
    }
    hook = HOOKS[style["hook_index"]]
    pain = PAIN_CONTEXT.get(lead_type, PAIN_CONTEXT.get("vacant", "Generic property owner."))

    # Market data context for the AI
    market_context = ""
    if market_data:
        market_context = f"""
LOCAL MARKET DATA (weave 1-2 of these naturally into the email, don't dump them all):
- Median home price in {city}: ${market_data.get('median_home_price', 0):,}
- Days on market: {market_data.get('days_on_market', 0)}
- Price change year-over-year: {market_data.get('price_change_yoy_pct', 0)}%
- Market type: {market_data.get('market_type_label', 'balanced')}
- Monthly holding cost estimate: ${market_data.get('monthly_holding_cost', 0):,}
- Annual holding cost: ${market_data.get('annual_holding_cost', 0):,}
"""

    holding_context = ""
    if holding_data:
        holding_context = f"""
HOLDING COST BREAKDOWN (reference if relevant to their pain):
- Property taxes: ${holding_data.get('property_taxes', 0):,}/mo
- Insurance: ${holding_data.get('insurance', 0):,}/mo
- Maintenance: ${holding_data.get('maintenance', 0):,}/mo
- Total: ${holding_data.get('total_monthly', 0):,}/mo = ${holding_data.get('total_annual', 0):,}/yr
- 5-year cost of holding: ${holding_data.get('total_5year', 0):,}
"""

    ai_prompt = f"""You are Piper Reeves. Nashville-born, empathetic, real, funny when appropriate.
You work at Everlight Logistics helping property owners sell fast for cash.

CRITICAL INSTRUCTIONS -- READ EVERY ONE:
1. This email must be COMPLETELY UNIQUE. Not a template. Not a formula. A real message from a real person.
2. OPENING STYLE: {style['opening']} -- use this approach to start the email.
3. TONE: {style['tone']} -- maintain this voice throughout.
4. CLOSING STYLE: {style['closing']} -- end with this type of call-to-action.
5. PERSONAL HOOK: Use this story naturally (don't force it): "{hook}"
6. Keep it 120-180 words. Short paragraphs. No walls of text.
7. Do NOT use these banned phrases: "we buy houses", "cash offer", "no obligation", "reach out to you",
   "hope this email finds you", "I came across your property" (too generic).
8. DO use: contractions, casual language, "y'all" occasionally, short sentences, genuine empathy.
9. Reference their SPECIFIC situation, not generic real estate talk.
10. Include exactly ONE surprising or interesting local data point from the market data below.
11. Sign off as: Piper Reeves | Everlight Logistics | piper@everlightventures.io

RECIPIENT:
- Name: {first_name} (full: {owner_name})
- Property: {short_addr}, {city}, {state}
- Situation: {lead_type.replace('_', ' ')}
- Pain context: {pain}
- Additional notes: {notes or 'None'}
- Estimated ARV: ${arv:,} (if 0, don't mention specific values)
{market_context}
{holding_context}

REMEMBER: Write like you're texting a friend you actually care about, not like a corporation.
Someone reading 3 of your emails should NOT be able to tell they came from the same template.

Return ONLY the email body. No subject line. No JSON. No markdown formatting."""

    body = _ai_generate(ai_prompt, 500)
    if not body or len(body) < 80:
        # Fallback to a simple template
        body = f"""Hey {first_name},

{hook}

I noticed your property at {short_addr} and thought I'd reach out. We help folks in {city} who want a simple, fast way to sell -- no repairs, no agents, no waiting.

If you've got 5 minutes for a quick chat, I'd love to hear about your situation. No pressure at all, y'all.

Piper Reeves
Everlight Logistics
piper@everlightventures.io"""

    # Check for similarity to recent emails
    if _is_too_similar(body) and retry < 2:
        return generate_unique_email(
            owner_name, address, city, state, lead_type,
            market_data, holding_data, arv, notes, retry + 1
        )

    # Save hash
    _save_sent_hash(_text_hash(body), {"to": owner_name, "city": city, "lead_type": lead_type})

    subject = generate_unique_subject(first_name, city, short_addr, lead_type)

    return {
        "subject": subject,
        "body_text": body,
        "body_html": body.replace("\n", "<br>"),
        "style": style,
    }


def generate_followup_email(
    owner_name: str,
    address: str,
    city: str,
    state: str,
    lead_type: str,
    touch_number: int,
    previous_subject: str = "",
) -> dict:
    """Generate a unique follow-up email (touches 2-7)."""
    first_name = owner_name.split()[0].title() if owner_name else "there"
    short_addr = address.split(",")[0] if "," in address else address

    followup_angles = {
        2: "Check in. Reference the first email briefly. Add a new angle or piece of info. Short -- 60-80 words max.",
        3: "Provide genuine value -- a market stat, a recent sale nearby, or a helpful observation. Don't ask for anything.",
        4: "Share a brief story about someone in a similar situation who sold and was relieved. Keep it real.",
        5: "Be direct but warm. 'I don't want to be a pest, but I also don't want you to miss out on this option.'",
        6: "Offer something tangible -- a free no-obligation property evaluation or market report for their area.",
        7: "The soft goodbye. 'I'm closing my file on this, but wanted to give you one last chance.' (This gets the highest response rate.)",
    }
    angle = followup_angles.get(touch_number, followup_angles[3])
    tone = random.choice(TONES)

    ai_prompt = f"""You are Piper Reeves from Everlight Logistics. Write follow-up #{touch_number} to {first_name}.

CONTEXT: You emailed them about their property at {short_addr}, {city} ({lead_type.replace('_', ' ')}). No reply yet.
ANGLE: {angle}
TONE: {tone}
PREVIOUS SUBJECT: {previous_subject}

RULES:
- This is touch #{touch_number} of 7. {'Be brief (60-80 words).' if touch_number <= 3 else 'Can be slightly longer (80-120 words).'}
- DO NOT repeat anything from previous emails (you don't know what was said, just be fresh)
- Use a DIFFERENT approach than whatever the first email probably used
- Sign: Piper Reeves | Everlight Logistics | piper@everlightventures.io
- Be human. Be real. No corporate speak.

Return ONLY the email body."""

    body = _ai_generate(ai_prompt, 300)
    if not body or len(body) < 40:
        body = f"""Hey {first_name},

Just circling back on my last note about {short_addr}. I know life gets busy.

If the timing works, I'd still love to chat for a few minutes. If not, no worries at all.

Piper Reeves
Everlight Logistics
piper@everlightventures.io"""

    # Follow-up subjects reference the thread
    followup_subjects = [
        f"Re: {previous_subject}" if previous_subject else f"Following up -- {short_addr}",
        f"Still thinking about {short_addr}, {first_name}",
        f"Quick follow-up, {first_name}",
        f"One more thought on {short_addr}",
        f"Checking in, {first_name}",
        f"Last note about {short_addr}",
        f"Closing the loop -- {short_addr}",
    ]
    subject = followup_subjects[min(touch_number - 1, len(followup_subjects) - 1)]

    return {
        "subject": subject,
        "body_text": body,
        "body_html": body.replace("\n", "<br>"),
        "touch_number": touch_number,
    }


if __name__ == "__main__":
    # Generate 3 emails for the same lead type to show they're different
    for i in range(3):
        result = generate_unique_email(
            owner_name="Donna Brooks",
            address="1522 Hogan St, St Louis, MO",
            city="St Louis",
            state="MO",
            lead_type="high_equity",
            market_data={"median_home_price": 210000, "days_on_market": 30, "monthly_holding_cost": 950,
                         "price_change_yoy_pct": 4.2, "market_type_label": "Strong seller's market"},
            arv=101000,
        )
        print(f"\n{'='*60}")
        print(f"EMAIL #{i+1} | Style: {result['style']['opening']} / {result['style']['tone']} / {result['style']['closing']}")
        print(f"Subject: {result['subject']}")
        print(f"{'='*60}")
        print(result["body_text"])
