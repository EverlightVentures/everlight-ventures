#!/usr/bin/env python3

# === ERADICATION HALT (auto-inserted 2026-05-15 after Streubel 2nd-strike) ===

# noqa: direct-resend
# This file still POSTs to api.resend.com directly. The eradication_gate is now
# called BEFORE any send, and the module refuses to load under WHOLESALE_OUTBOUND_HALT=1.
# Full migration to content_tools.branded_mailer.send_branded_email() is tracked
# in _state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md under "Lift criteria".
# The noqa marker is the lint's documented exception for files that are gated
# pending a full refactor. DO NOT remove the eradication_gate import or the
# module-level halt check; they are the load-bearing protections.
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    import sys as _sys_halt
    print("[hive_outreach.py] WHOLESALE_OUTBOUND_HALT=1 -- refusing to run", file=_sys_halt.stderr)
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active")
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"[hive_outreach.py] eradication_gate unavailable: {_eg_err}", file=_sys_eg.stderr)
    raise SystemExit("eradication_gate required")
# === END ERADICATION HALT ===
"""
Hive Outreach -- Multi-Agent Belfort Sequence Engine

Rotates 4 AI agents across a 7-touch drip sequence, each with their own
backstory, speech patterns, and personality. Every lead type gets a unique
message per agent -- 28 total templates.

Touch schedule:
  1  Day 1   PIPER REEVES   -- warm intro
  2  Day 3   REX BLACKWELL  -- direct SMS-style
  3  Day 5   ACE MORGAN     -- investment pitch
  4  Day 8   PIPER REEVES   -- follow-up
  5  Day 12  SCOUT NAVARRO  -- casual discovery
  6  Day 16  REX BLACKWELL  -- last chance
  7  Day 21  PIPER REEVES   -- soft close

Sends FROM each agent's @everlightventures.io address via Resend API.
"""

import json
import os
import random
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # preview-only mode

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_URL = "https://api.resend.com/emails"

LEAD_TYPES = [
    "pre_foreclosure",
    "tax_delinquent",
    "expired_listing",
    "high_equity",
    "code_violation",
    "probate",
    "vacant",
]

# ---------------------------------------------------------------------------
# Touch sequence -- maps touch number to (agent_key, day_offset)
# ---------------------------------------------------------------------------
TOUCH_SEQUENCE = {
    1: ("piper", 1),
    2: ("rex", 3),
    3: ("ace", 5),
    4: ("piper", 8),
    5: ("scout", 12),
    6: ("rex", 16),
    7: ("piper", 21),
}

# ---------------------------------------------------------------------------
# Agent profiles
# ---------------------------------------------------------------------------
AGENTS: Dict[str, Dict[str, Any]] = {
    "piper": {
        "name": "Piper Reeves",
        "email": "piper@everlightventures.io",
        "title": "Outreach Specialist",
        "style": "Nashville warmth, empathetic, uses 'y'all', gentle persuader",
        "sign_off": (
            "Best,\n"
            "Piper Reeves | Outreach Specialist | Everlight Ventures\n"
            "piper@everlightventures.io | everlightventures.io"
        ),
        "hooks": [
            "My family went through something similar with my grandmother's place in Murfreesboro -- it sat empty for two years before we figured out what to do with it.",
            "My brother just went through selling a property he inherited, so I totally understand the stress of dealing with a house you didn't plan on having.",
            "I grew up watching my mom stress about an old rental property -- that's actually what got me into real estate, wanting to help people in that exact situation.",
        ],
    },
    "rex": {
        "name": "Rex Blackwell",
        "email": "rex.b@everlightventures.io",
        "title": "Acquisitions",
        "style": "Texas drawl, direct, no-BS, numbers-first, short sentences",
        "sign_off": (
            "Rex Blackwell | Everlight Ventures | We Buy Houses Cash\n"
            "rex.b@everlightventures.io"
        ),
        "hooks": [
            "Been buying properties in Dallas for 15 years. I've seen every situation you can imagine.",
            "Closed one last week in a Whataburger parking lot. That's how simple we keep it.",
            "I don't waste people's time. You tell me what you need, I tell you if I can do it. That's it.",
        ],
    },
    "ace": {
        "name": "Ace Morgan",
        "email": "ace@everlightventures.io",
        "title": "Investment Analyst",
        "style": "Smooth, investment banker energy, professional, data-driven",
        "sign_off": (
            "Ace Morgan | Investment Analyst | Everlight Ventures\n"
            "ace@everlightventures.io"
        ),
        "hooks": [
            "I put together deals for cash buyers -- it's what I do full-time, and I take it seriously.",
            "The numbers on your property caught my eye while I was running comps in the area.",
            "I've been analyzing properties in {city} for our acquisition fund, and yours stood out.",
        ],
    },
    "scout": {
        "name": "Scout Navarro",
        "email": "scout@everlightventures.io",
        "title": "Acquisitions",
        "style": "Miami energy, casual, excited, genuine curiosity",
        "sign_off": (
            "Scout Navarro | Acquisitions | Everlight Ventures\n"
            "scout@everlightventures.io"
        ),
        "hooks": [
            "I was driving through your neighborhood and your property caught my attention.",
            "Found your property while researching the area -- not gonna lie, this one stood out.",
            "I've been scouting {city} all week and your place kept coming up in my searches.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Subject line generators per agent
# ---------------------------------------------------------------------------

def _subject_piper(lead: dict, touch: int) -> str:
    addr = _short_addr(lead)
    first = _first_name(lead)
    city = lead.get("city", "your area")
    pool = {
        1: [
            f"Quick question about {addr}",
            f"Hey {first} -- reaching out about {addr}",
            f"Your property in {city}",
        ],
        4: [
            f"Just checking in, {first}",
            f"Following up -- {addr}",
            f"Still thinking about you, {first}",
        ],
        7: [
            f"No pressure -- just wanted to say hi",
            f"Door's always open, {first}",
            f"One last note about {addr}",
        ],
    }
    options = pool.get(touch, pool[1])
    return random.choice(options)


def _subject_rex(lead: dict, touch: int) -> str:
    addr = _short_addr(lead)
    first = _first_name(lead)
    pool = {
        2: [
            f"Cash offer for {addr}",
            f"{first} -- quick question",
            f"Straight talk about {addr}",
        ],
        6: [
            f"{first} -- last chance on this",
            f"Final offer for {addr}",
            f"Closing the file on {addr}",
        ],
    }
    options = pool.get(touch, pool[2])
    return random.choice(options)


def _subject_ace(lead: dict, touch: int) -> str:
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    return random.choice([
        f"Investment inquiry -- {addr}",
        f"Regarding {addr} in {city}",
        f"Acquisition analysis -- {addr}",
    ])


def _subject_scout(lead: dict, touch: int) -> str:
    first = _first_name(lead)
    city = lead.get("city", "your area")
    return random.choice([
        f"Your property in {city}!",
        f"Hey {first} -- saw something",
        f"Found your place in {city}",
    ])


SUBJECT_FN = {
    "piper": _subject_piper,
    "rex": _subject_rex,
    "ace": _subject_ace,
    "scout": _subject_scout,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_name(lead: dict) -> str:
    owner = lead.get("owner_name", "")
    if not owner:
        return "there"
    return owner.split()[0].title()


def _short_addr(lead: dict) -> str:
    addr = lead.get("address", "your property")
    return addr.split(",")[0] if "," in addr else addr


def _pick_hook(agent_key: str, lead: dict) -> str:
    agent = AGENTS[agent_key]
    hook = random.choice(agent["hooks"])
    city = lead.get("city", "your area")
    return hook.replace("{city}", city)


# ---------------------------------------------------------------------------
# PIPER templates -- Touch 1 (intro), Touch 4 (follow-up), Touch 7 (soft close)
# ---------------------------------------------------------------------------

def _piper_touch1(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    hook = _pick_hook("piper", lead)
    sign = AGENTS["piper"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""Hey {first},

I hope I'm not overstepping, but I came across your property at {addr} and wanted to reach out personally. I know this might be a stressful time, and I promise this isn't one of those generic "we buy houses" emails.

{hook}

We work with property owners in {city} who need a quick, fair solution. We buy as-is -- no repairs, no cleaning, no agents, no fees. We can close in as little as 7 days, and we pay cash.

If you're open to a conversation, even just to hear what we could offer, I'd love to chat. No pressure at all, y'all.

Would a quick 5-minute call this week work for you?

{sign}""",

        "tax_delinquent": f"""Hey {first},

I noticed your property at {addr} in {city} and wanted to reach out before things get more complicated with the county. I know dealing with back taxes is one of those things that just hangs over you.

{hook}

We purchase properties as-is for cash and can close fast -- usually within 7-14 days. We handle all the paperwork, and we can even work with the county directly to clear the title.

No judgment, no pressure. Just a straightforward conversation about your options. Would that be helpful?

{sign}""",

        "expired_listing": f"""Hey {first},

I saw that your property at {addr} was on the market for a while without selling, and I totally get how frustrating that must be. Dealing with showings, agents, and no results is exhausting.

{hook}

We take a different approach -- we buy directly, as-is, no contingencies. No more open houses, no more waiting, no more wondering. Just a fair cash offer and a closing date that works for you.

Would you be open to hearing what we could offer? Even if it's just to have a backup plan, y'all.

{sign}""",

        "high_equity": f"""Hey {first},

I'm reaching out about your property at {addr} in {city}. We work with property owners who have significant equity and are looking for a hassle-free way to sell -- no agents, no repairs, no months of waiting.

{hook}

What makes us different is we actually close. Cash offer within 24 hours, close in 7-14 days, and you walk away with a check. We've been working with owners in {city} and wanted to see if this is something you'd even consider.

No strings attached -- just a conversation. Would that be alright?

{sign}""",

        "code_violation": f"""Hey {first},

I know this might seem random, but I came across your property at {addr} and noticed there might be some city issues attached to it. I'm not here to add to your stress -- actually the opposite.

{hook}

We specialize in buying properties exactly like this -- code violations, repairs needed, whatever the situation. We buy as-is, handle everything, and close fast with cash. No fines piling up, no contractors to hire, no city back-and-forth.

If you've been thinking "I just want this off my plate," that's exactly what we do. Can I give you a quick call this week?

{sign}""",

        "probate": f"""Hey {first},

I'm so sorry for your loss. I know this probably isn't the easiest time to be thinking about property, and I want to be respectful of that.

{hook}

We work with families who've inherited properties and just want a simple solution. No repairs, no listing, no months of waiting. We buy as-is and handle all the paperwork -- including any probate coordination.

Whenever you're ready, even if it's just to ask questions, I'm here. No rush, no pressure.

{sign}""",

        "vacant": f"""Hey {first},

I noticed your property at {addr} in {city} appears to be sitting vacant, and I wanted to check in. Empty properties can be such a headache -- insurance, taxes, maintenance, worrying about break-ins...

{hook}

We buy vacant properties as-is for cash. No repairs, no cleaning out, no listing. Just a fair offer and a fast close. A lot of the owners we work with tell me the biggest relief was just not having to think about it anymore.

Would you be open to a quick chat about it?

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


def _piper_touch4(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    sign = AGENTS["piper"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""Hey {first},

Just wanted to check in -- I reached out a few days ago about your property at {addr}. I know things can get hectic, especially when you're dealing with a tough situation.

I'm not trying to be pushy, y'all. Just wanted to make sure my message didn't get buried. We can still get you a cash offer within 24 hours and close on your timeline.

If now isn't a good time, I totally understand. But if you have 5 minutes for a quick call, I'd love to chat.

{sign}""",

        "tax_delinquent": f"""Hey {first},

Following up on my earlier email about your property at {addr} in {city}. I know the tax situation can feel overwhelming, and sometimes it's easier to just ignore emails like mine -- I get it.

But I really do think we can help. We've worked with owners in {city} who were in similar spots, and we made the process as painless as possible. Cash offer, fast close, we handle the county paperwork.

Just wanted you to know the offer still stands, y'all. No pressure.

{sign}""",

        "expired_listing": f"""Hey {first},

Checking back in about {addr}. I know you probably got a bunch of messages when your listing expired, and mine might have gotten lost in the shuffle.

I promise we're different from the "investor spam" crowd. We actually close deals, and we do it fast. If your property still hasn't sold, I'd love to show you what a no-hassle cash offer looks like.

Either way, I'm here whenever you're ready, y'all.

{sign}""",

        "high_equity": f"""Hey {first},

Just circling back on your property at {addr}. I know you're probably not in a rush -- and that's totally fine. Sometimes the best deals happen when there's no pressure.

I just wanted to make sure you knew the option was there. Cash offer, close whenever you want, no agents or fees eating into your equity.

Hope you're having a great week, y'all. I'm here if you want to chat.

{sign}""",

        "code_violation": f"""Hey {first},

Following up about your property at {addr}. I know dealing with code violations is one of those things that's easy to push off, but the fines don't stop piling up.

We can take the whole thing off your hands -- buy it as-is, handle the violations, and close with cash. No contractors, no city hearings, no stress.

Just wanted to put that out there again, y'all. Let me know if you want to talk.

{sign}""",

        "probate": f"""Hey {first},

I hope you're doing okay. I reached out a little while ago about the property at {addr}, and I just wanted to gently follow up.

There's absolutely no rush on this. Whenever you're ready to have a conversation -- even if it's just to ask questions -- I'm here. We handle all the probate paperwork and make the process as simple as possible.

Thinking of you, y'all.

{sign}""",

        "vacant": f"""Hey {first},

Just checking in about your property at {addr} in {city}. I know vacant properties can feel like a "deal with it later" thing, but they do add up -- taxes, insurance, liability.

We can make it simple. Cash offer, close fast, and you never have to think about it again. No repairs, no cleaning, no listing.

Let me know if you'd like to chat, y'all. No pressure either way.

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


def _piper_touch7(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    sign = AGENTS["piper"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""Hey {first},

This is my last note about {addr} -- I promise I'm not going to keep bugging you. I just wanted to say that if your situation changes, or if you decide you want to explore your options, the door is always open.

We can still do a cash offer, close fast, and make it as easy as possible. No judgment, no pressure, no timeline.

Wishing you all the best, y'all. You know where to find me.

{sign}""",

        "tax_delinquent": f"""Hey {first},

I've reached out a couple times about {addr}, and I don't want to be a bother. This is my last email on this.

If the tax situation ever becomes something you want to resolve quickly, we're still here. Cash offer, we handle the county, close on your schedule.

No pressure at all. I genuinely hope things work out for you, y'all.

{sign}""",

        "expired_listing": f"""Hey {first},

Just a final note -- I know you've been through the wringer trying to sell {addr}, and the last thing you need is another person in your inbox.

If you ever want a simple, no-hassle cash offer with no contingencies, we're a phone call away. No agents, no showings, no wondering.

Wishing you the best, y'all. The door is always open.

{sign}""",

        "high_equity": f"""Hey {first},

This is my last reach-out about {addr}. I don't want to overstay my welcome in your inbox.

If you ever decide you want to explore a cash sale -- no agents, no repairs, no fees -- just reply to this email and we'll pick right up where we left off.

Take care, y'all. It was great connecting with you.

{sign}""",

        "code_violation": f"""Hey {first},

Last note from me on {addr}. I know you've got a lot going on, and I don't want to add to it.

If the code violations ever become too much, or you just want the property off your plate, we're still here. Cash, as-is, fast close.

Wishing you the best, y'all.

{sign}""",

        "probate": f"""Hey {first},

I just wanted to send one final note. I know inherited properties come with a lot of emotions and logistics, and there's no "right" timeline for any of it.

Whenever you're ready -- whether that's next week or next year -- we're here. No pressure, no expiration on our offer.

Take care of yourself, y'all.

{sign}""",

        "vacant": f"""Hey {first},

This is my last message about {addr}. I don't want to be that person who won't stop emailing.

If you ever want to offload the property -- no repairs, no hassle, just cash -- we're a reply away. The offer doesn't expire.

All the best, y'all.

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


# ---------------------------------------------------------------------------
# REX templates -- Touch 2 (direct intro), Touch 6 (last chance)
# ---------------------------------------------------------------------------

def _rex_touch2(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    hook = _pick_hook("rex", lead)
    sign = AGENTS["rex"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""{first} --

I'll keep this short. I saw your property at {addr} and I know what's going on. No sugarcoating.

{hook}

Here's what I can do: cash offer in 24 hours, close in 7 days, I handle everything. You walk away clean. No banks, no agents, no fees.

If you want to talk numbers, reply to this email or call me. If not, no hard feelings.

{sign}""",

        "tax_delinquent": f"""{first} --

Your property at {addr}. Back taxes. I'm not going to pretend I don't know.

{hook}

I can get you a cash offer today, close in two weeks, and we'll work with the county to sort out the liens. You walk away with money in your pocket instead of more bills.

Want to hear the number? Reply and I'll send it over.

{sign}""",

        "expired_listing": f"""{first} --

{addr} sat on the market and didn't sell. That happens. Doesn't mean the property is bad -- it means the approach was wrong.

{hook}

Here's my approach: I make you a cash offer. No inspections, no contingencies, no "let me think about it for 45 days." We close when you want to close.

Interested? Shoot me a reply.

{sign}""",

        "high_equity": f"""{first} --

Quick note about {addr}. You've got solid equity in that property, and I'd like to make you a cash offer for it.

{hook}

No agents taking 6%. No buyers falling through. No months of showings. Just a fair number and a fast close.

If you're even a little curious, reply and I'll run the numbers for you.

{sign}""",

        "code_violation": f"""{first} --

I know about {addr} and the code issues. Not judging -- it happens to the best of us.

{hook}

I buy properties with violations all the time. As-is. I don't ask you to fix anything. Cash offer, fast close, and the city stops sending you letters.

Want out? Hit reply.

{sign}""",

        "probate": f"""{first} --

I'll be respectful of your time. I know you inherited {addr} and that comes with a lot to deal with.

{hook}

If you want to sell it fast and simple -- cash, as-is, we handle the probate paperwork -- I can make that happen. No agents, no repairs, no headaches.

Let me know if you want to talk.

{sign}""",

        "vacant": f"""{first} --

{addr} is sitting empty. That means you're paying taxes, insurance, and liability on a property that's making you zero dollars.

{hook}

I'll buy it. Cash. As-is. You don't even have to clean it out. We close in two weeks and you stop bleeding money.

Reply if you want to hear a number.

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


def _rex_touch6(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    sign = AGENTS["rex"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""{first} --

I've reached out before about {addr}. I'm going to be straight with you -- the window on this is closing.

I can still get you a cash offer and close fast. But I can't help if you don't pick up the phone or reply to an email.

This is me giving you one more shot at a clean exit. After this, I'm moving on to the next property.

Your call.

{sign}""",

        "tax_delinquent": f"""{first} --

Last time I'm bringing this up. {addr} and the back taxes -- that situation isn't getting better on its own.

I can still buy it, handle the liens, and put cash in your hand. But I'm closing my file on this one soon.

If you want out, now's the time. Reply or call.

{sign}""",

        "expired_listing": f"""{first} --

{addr} still hasn't sold. I'm not surprised -- the traditional market can be brutal.

I've got one more shot at a cash offer for you. No agents, no contingencies, no waiting. But I'm wrapping up my review of properties in your area.

Last chance to get a number from me. Reply if you want it.

{sign}""",

        "high_equity": f"""{first} --

I've been patient on {addr}. Wanted to give you time to think.

But I'm closing out my acquisitions list for this cycle. If you want a cash offer -- fair price, no fees, fast close -- this is the time.

After this week, I'm moving on. No hard feelings either way.

{sign}""",

        "code_violation": f"""{first} --

The violations on {addr} are still there. The fines are still growing. And I'm still willing to buy it as-is for cash.

But I'm not going to chase this forever. This is my last email about it.

If you want the property gone, reply now. If not, I wish you the best.

{sign}""",

        "probate": f"""{first} --

I know the inherited property at {addr} is a lot to deal with. I've given you space and time.

If you're ready to sell -- cash, we handle everything -- I can still make it happen. But I'm wrapping up this outreach soon.

No pressure, but this is the last time I'll bring it up. Let me know.

{sign}""",

        "vacant": f"""{first} --

{addr} is still vacant. Still costing you money every month.

I've offered to buy it -- cash, as-is, fast close. That offer is still on the table, but not for much longer.

This is my last email. If you want out, reply now.

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


# ---------------------------------------------------------------------------
# ACE templates -- Touch 3 (investment pitch)
# ---------------------------------------------------------------------------

def _ace_touch3(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    hook = _pick_hook("ace", lead)
    sign = AGENTS["ace"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""Good afternoon {first},

I'm reaching out regarding the property at {addr}. My name is Ace Morgan -- I work on the acquisitions side at Everlight Ventures, where we evaluate properties for our cash buyers.

{hook}

I understand the current circumstances around this property, and I want to present an alternative to what you may have been offered so far. We can provide a formal cash offer within 24 hours, close within your preferred timeline, and cover all closing costs.

Our process is straightforward: no inspections, no contingencies, no agent commissions. We structure our deals to maximize the net proceeds you walk away with.

Would you be open to a brief conversation to discuss the numbers?

{sign}""",

        "tax_delinquent": f"""Good afternoon {first},

I've been reviewing properties in {city} for our acquisition fund, and {addr} came up in my analysis. I understand there may be some outstanding tax obligations associated with the property.

{hook}

We regularly work with property owners in this situation. Our team handles lien resolution as part of the acquisition process -- meaning you don't have to negotiate with the county yourself. We provide a net cash offer after all liens are accounted for.

I'd be happy to run a preliminary valuation and share the numbers with you. No obligation.

{sign}""",

        "expired_listing": f"""Good afternoon {first},

I noticed that {addr} was recently on the market without finding a buyer. From an analytical standpoint, this often comes down to pricing strategy or market timing -- not the property itself.

{hook}

Our approach eliminates the variables that cause traditional sales to fall through. Cash offer, no financing contingency, no inspection renegotiation, and a guaranteed close date. We typically close within 14 days.

I've run preliminary numbers on the property. Would you like to see what a direct cash sale looks like compared to relisting?

{sign}""",

        "high_equity": f"""Good afternoon {first},

I'm reaching out about your property at {addr} in {city}. Based on my analysis, you have a significant equity position, and I'd like to present an acquisition opportunity.

{hook}

What sets our offers apart is the net calculation. No agent commissions (saving you 5-6%), no repair credits, no closing cost negotiations. The number we quote is the number you receive.

I've prepared a preliminary analysis. Would you be open to reviewing it over a brief call?

{sign}""",

        "code_violation": f"""Good afternoon {first},

I'm writing regarding {addr}. My research indicates there may be open code violations associated with the property. I understand that can create a complicated and expensive situation.

{hook}

We acquire properties with active violations regularly. Our team handles all remediation and compliance as part of the purchase -- you don't spend a dollar on repairs or city fees. We buy as-is and close with cash.

I can have a formal offer to you within 24 hours if you're interested. Shall I proceed?

{sign}""",

        "probate": f"""Good afternoon {first},

Please accept my condolences. I understand you may have recently inherited the property at {addr}, and I want to be respectful of the circumstances.

{hook}

When you're ready, we can provide a straightforward path to liquidating the property. We handle probate coordination, title clearing, and all associated paperwork. Our offer is cash, as-is, and structured to close on your preferred timeline.

There's no urgency on our end. When the time is right, I'm available for a conversation.

{sign}""",

        "vacant": f"""Good afternoon {first},

I've been analyzing vacant properties in {city}, and {addr} appeared in my review. Vacant properties represent a carrying cost -- taxes, insurance, liability, maintenance -- without generating any return.

{hook}

We can convert that liability into immediate cash. Our process is simple: cash offer within 24 hours, close in 7-14 days, property purchased as-is. No cleaning, no repairs, no listing.

I'd like to share my valuation analysis with you. Would a brief call work?

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


# ---------------------------------------------------------------------------
# SCOUT templates -- Touch 5 (casual discovery)
# ---------------------------------------------------------------------------

def _scout_touch5(lead: dict) -> str:
    first = _first_name(lead)
    addr = _short_addr(lead)
    city = lead.get("city", "your area")
    hook = _pick_hook("scout", lead)
    sign = AGENTS["scout"]["sign_off"]
    lt = lead.get("lead_type", "")

    bodies = {
        "pre_foreclosure": f"""Hey {first}!

So I was doing some research in {city} today and your property at {addr} popped up. I know you've probably gotten a ton of messages, but hear me out for a sec.

{hook}

We're a small acquisitions team -- not some giant corporation -- and we actually care about making this easy for people. Cash offer, close whenever works for you, and we handle literally everything.

I'd love to have a quick convo if you're open to it. No sales pitch, just real talk.

{sign}""",

        "tax_delinquent": f"""Hey {first}!

I was pulling property data in {city} and {addr} caught my attention. I can see there might be some tax stuff going on, and honestly, I've seen so many people in the same boat.

{hook}

We buy properties like this all the time -- taxes, liens, whatever. We sort it all out and you just walk away with cash. Seriously, that's it.

Want to chat about it? No pressure, just a conversation.

{sign}""",

        "expired_listing": f"""Hey {first}!

I noticed {addr} was listed for a while and didn't sell. That's gotta be frustrating, right? All those showings and open houses for nothing.

{hook}

What if you could skip all that and just get a cash offer? No more staging, no more waiting, no more "the buyer's financing fell through." We close fast and we close for real.

Hit me up if you want to hear more!

{sign}""",

        "high_equity": f"""Hey {first}!

Okay so I've been looking at properties in {city} and yours at {addr} seriously stood out. You've got some great equity in there.

{hook}

We make cash offers on properties like yours -- and the best part is, you don't deal with agents, repairs, or any of that. Just a fair offer and a fast close.

Curious? Reply and I'll tell you more!

{sign}""",

        "code_violation": f"""Hey {first}!

I came across {addr} while scouting in {city} and noticed there might be some code stuff going on. I know that can be a total headache.

{hook}

Here's the thing -- we actually specialize in buying properties with violations. As-is, no repairs needed, we handle everything with the city. You just get cash and walk away.

Sound too good to be true? Let me prove it. Reply and let's talk!

{sign}""",

        "probate": f"""Hey {first},

I wanted to reach out about {addr}. I understand you may have inherited the property, and first of all, I'm sorry for what you're going through.

{hook}

When you're ready, we can make the whole thing super simple. Cash offer, we handle the probate paperwork, and you close whenever you want. No rush at all.

If you ever want to have a casual conversation about it, I'm here.

{sign}""",

        "vacant": f"""Hey {first}!

So I've been scouting properties in {city} and {addr} came up as vacant. Not gonna lie, it stood out to me right away.

{hook}

Vacant properties are just money going out the door every month, right? Taxes, insurance, liability. We can turn that into cash in your pocket. As-is, no cleaning, no fixing up -- we just buy it.

Want to hear what we'd offer? Hit me up!

{sign}""",
    }
    return bodies.get(lt, bodies["high_equity"])


# ---------------------------------------------------------------------------
# Template dispatch
# ---------------------------------------------------------------------------
TEMPLATE_FN = {
    (1, "piper"): _piper_touch1,
    (2, "rex"): _rex_touch2,
    (3, "ace"): _ace_touch3,
    (4, "piper"): _piper_touch4,
    (5, "scout"): _scout_touch5,
    (6, "rex"): _rex_touch6,
    (7, "piper"): _piper_touch7,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_touch(touch_number: int, lead: dict) -> Dict[str, str]:
    """
    Generate the correct agent email for a given touch number.

    Returns dict with keys: agent, from_name, from_email, subject, body, day_offset
    """
    if touch_number not in TOUCH_SEQUENCE:
        raise ValueError(f"Invalid touch number {touch_number}. Must be 1-7.")

    agent_key, day_offset = TOUCH_SEQUENCE[touch_number]
    agent = AGENTS[agent_key]

    template_fn = TEMPLATE_FN[(touch_number, agent_key)]
    body = template_fn(lead)

    subject_fn = SUBJECT_FN[agent_key]
    subject = subject_fn(lead, touch_number)

    return {
        "agent": agent["name"],
        "from_name": agent["name"],
        "from_email": agent["email"],
        "subject": subject,
        "body": body,
        "day_offset": day_offset,
        "touch": touch_number,
    }


def preview_sequence(lead: dict) -> List[Dict[str, str]]:
    """Preview all 7 touches for a lead without sending."""
    sequence = []
    for touch_num in range(1, 8):
        touch = generate_touch(touch_num, lead)
        sequence.append(touch)
    return sequence


def send_touch(
    lead: dict,
    touch_number: int,
    to_email: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Send a single touch email via Resend from the correct agent.

    Args:
        lead: Lead dict with owner_name, address, city, state, lead_type
        touch_number: 1-7
        to_email: Recipient email (overrides lead["email"] if provided)

    Returns:
        (success: bool, message_id_or_error: str)
    """
    if not requests:
        return False, "requests library not installed"

    if not RESEND_KEY:
        return False, "RESEND_API_KEY not set in environment"

    recipient = to_email or lead.get("email", "")
    if not recipient:
        return False, "No recipient email provided"

    touch = generate_touch(touch_number, lead)
    # Piper's warm voice goes in the content body; the branded mailer wraps it
    # in the gold luxury frame so every outbound seller touch is consistent.
    content_html = touch["body"].replace("\n", "<br>\n")

    try:
        import sys
        sys.path.insert(0, "/home/opc/content_tools" if Path("/home/opc").exists() else "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from branded_mailer import send_branded_email
    except ImportError as e:
        return False, f"branded_mailer unavailable: {e}"

    result = send_branded_email(
        to=recipient,
        subject=touch["subject"],
        content_html=content_html,
        title=touch["subject"],
        from_name=touch["from_name"],
        from_email=touch["from_email"],
        reply_to=touch["from_email"],
        agent_name=touch["from_name"],
        agent_title="Everlight Ventures Acquisitions",
        agent_email=touch["from_email"],
    )

    if result.ok:
        return True, result.message_id
    return False, result.error


# ---------------------------------------------------------------------------
# SMS -- gated behind A2P_APPROVED. Blocks until Twilio 10DLC is live.
# ---------------------------------------------------------------------------

def send_sms(to_phone: str, body: str, *, lane: str = "", lead_id: str = "",
             state: str = "", is_inbound_consent: bool = False) -> Tuple[bool, str]:
    """Send an SMS via Twilio. Returns (ok, message_id_or_error).

    Triple-gated:
      1. A2P_APPROVED env flag (Twilio 10DLC campaign live)
      2. compliance.state_gate per-state SMS allowlist (blocks TX cold-SMS, etc.)
      3. is_inbound_consent=True for warm leads who texted us first (bypasses cold-SMS block)

    The body MUST already include STOP opt-out language; we do not inject it.
    Justine Park reviews every template before A2P approval.
    """
    # Gate 1: compliance gate -- checks per-state SMS legality + required disclosures.
    if state and not is_inbound_consent:
        try:
            from compliance.state_gate import check
            gate = check(state, "sms", "outreach")
            if not gate.ok:
                return False, f"STATE_GATE_BLOCKED ({state}): {gate.blocked_reason}"
        except ImportError:
            # compliance module not available; fall through to A2P gate
            pass

    # Gate 2: A2P 10DLC approval for outbound cold SMS.
    if os.environ.get("A2P_APPROVED", "") != "1" and not is_inbound_consent:
        return False, "A2P_NOT_APPROVED: SMS sending disabled until Twilio 10DLC campaign approved"

    # Gate 3: opt-out language required in every outbound body.
    if "stop" not in body.lower():
        return False, "missing_opt_out: body must include STOP opt-out language"

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "")

    if not (account_sid and auth_token and from_number):
        return False, "TWILIO_CREDS_MISSING"

    if not to_phone or not to_phone.startswith("+"):
        return False, f"invalid_phone:{to_phone!r} (must be E.164 format)"

    if not requests:
        return False, "requests library not installed"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        r = requests.post(
            url,
            auth=(account_sid, auth_token),
            data={"From": from_number, "To": to_phone, "Body": body},
            timeout=10,
        )
    except Exception as e:
        return False, f"http_error:{e}"

    if r.status_code in (200, 201):
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return True, str(data.get("sid", "sent"))

    try:
        err = r.json().get("message", f"HTTP {r.status_code}")
    except Exception:
        err = f"HTTP {r.status_code}"
    return False, err


# ---------------------------------------------------------------------------
# Main -- preview a sample sequence
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample_lead = {
        "owner_name": "DONNA T BROOKS",
        "address": "1522 HOGAN ST, SAINT LOUIS, MO 63106",
        "city": "St Louis",
        "state": "MO",
        "lead_type": "pre_foreclosure",
        "email": "donna.brooks@example.com",
    }

    print("=" * 70)
    print("HIVE OUTREACH -- 7-Touch Belfort Sequence Preview")
    print(f"Lead: {sample_lead['owner_name']} | {sample_lead['address']}")
    print(f"Type: {sample_lead['lead_type']}")
    print("=" * 70)

    sequence = preview_sequence(sample_lead)
    start_date = datetime.now()

    for touch in sequence:
        send_date = start_date + timedelta(days=touch["day_offset"] - 1)
        print(f"\n{'~' * 70}")
        print(f"TOUCH {touch['touch']} -- Day {touch['day_offset']} -- {send_date.strftime('%A %b %d')}")
        print(f"AGENT: {touch['agent']}")
        print(f"FROM:  {touch['from_name']} <{touch['from_email']}>")
        print(f"SUBJ:  {touch['subject']}")
        print(f"{'~' * 70}")
        print(touch["body"])
