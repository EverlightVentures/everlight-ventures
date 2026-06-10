"""
recipient_classifier.py -- Mechanical filter that prevents wholesale outreach
from going to non-homeowner recipients (attorneys, government employees,
real-estate agents, title companies, brokerages, B2B partners).

Background -- the "David Streubel disaster":
    On 2026-04-25, the wholesale outreach engine sent a homeowner-distress
    pitch ("we buy houses cash") to David A. Streubel, an attorney for the
    City of St Louis whose work email lives on a municipal-law-firm domain.
    No filter said "this isn't a homeowner, skip." The class of mistake was
    a missing classifier, not a bad lead -- the lead was correctly tagged as
    a person, but no module ever asked "is this person actually a homeowner
    we should be cold-pitching?"

This module exists so that mistake is mechanically impossible going forward.
The orchestrator's _send_email() chokepoint calls classify_recipient() before
every seller-side send. Anything that is not 'homeowner_likely' gets skipped
and logged to /home/opc/_logs/recipient_classifier_skips.jsonl.

Public surface -- one function:
    classify_recipient(email, name, phone=None) -> dict

    {
      'is_homeowner_likely': bool,
      'recipient_class':     str,    # taxonomy entry below
      'confidence':          float,  # 0.0 -- 1.0
      'reason':              str,    # human-readable why
    }

Recipient class taxonomy:
    'attorney_firm'       -- law firm domain or "Esq" in name. THE DAVID CASE.
    'government_employee' -- .gov / .us / municipal pattern.
    'real_estate_agent'   -- known brokerage domain or "agent/broker/realtor" title.
    'title_company'       -- title / closing / escrow domain (B2B partner).
    'business_other'      -- catchall business domain.
    'homeowner_likely'    -- gmail/yahoo/aol/hotmail/outlook/icloud, no biz markers.
    'unknown'             -- not enough signal.

is_homeowner_likely is True ONLY for the 'homeowner_likely' class.

Sign off: Backend Hand.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Domain pattern tables. Conservative -- prefer false negative (skip a real
# homeowner) over false positive (pitch a lawyer). The cost of skipping a
# legit lead is one lost touch. The cost of pitching a lawyer is a brand
# blowup and possible bar complaint.
# ---------------------------------------------------------------------------

# Personal / consumer email providers. ONLY these flip to homeowner_likely.
PERSONAL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "ymail.com",
    "rocketmail.com",
    "aol.com",
    "hotmail.com",
    "live.com",
    "outlook.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "comcast.net",
    "sbcglobal.net",
    "verizon.net",
    "att.net",
    "bellsouth.net",
    "cox.net",
    "earthlink.net",
    "charter.net",
    "frontier.com",
    "centurylink.net",
    "mail.com",
    "gmx.com",
    "protonmail.com",
    "proton.me",
    "pm.me",
    "tutanota.com",
    "fastmail.com",
    "zoho.com",
    "yandex.com",
}

# Law firm signal -- domain or local part. Substring match on the FULL email
# address (lowercased). Conservative: any of these markers fires the class.
LAWFIRM_DOMAIN_SUBSTRINGS = (
    ".law",
    "lawfirm",
    "law-firm",
    "lawgroup",
    "law-group",
    "legal",
    "attorneys",
    "attorney",
    "counsel",
    "esquire",
    "litigation",
    "advocates",
    "barrister",
    "solicitor",
    "paralegal",
    "lawpc",
    "lawllc",
    "lawllp",
)

# Known law firms / patterns flagged in past outreach reviews. Add to this
# list whenever a new "we sent to a lawyer" disaster lands in a postmortem.
KNOWN_LAWFIRM_TOKENS = (
    "cunninghamvogel",   # The David Streubel firm.
    "stllaw",
    "stlouislaw",
    "stlcity",
    "municipalfirm",
    "citylaw",
    "publicdefender",
    "districtattorney",
    "stateattorney",
    "uslaw",
)

LAWFIRM_TLDS = (".pc", ".pllc", ".llp", ".plc")

LAWFIRM_NAME_TOKENS = (
    "esq",
    "esq.",
    "esquire",
    "attorney",
    "atty",
    "counselor",
    "j.d.",
    "jd,",
)

# Government / public-sector signal. .gov is hard. .us is soft -- many
# personal mail servers use .us, so we require an additional municipal
# token.
GOV_HARD_TLDS = (".gov", ".mil")

GOV_DOMAIN_SUBSTRINGS = (
    "city-of-",
    "cityof",
    ".ci.",          # ci.<city>.<state>.us pattern
    "county.",
    "countyof",
    "stateof",
    ".state.",
    "publicworks",
    "municipal",
    "school",
    "schools",
    "k12",
    "courts",
    "court",
    "dmv",
    "dot.",
)

# Brokerages / iBuyers / large real-estate platforms. Anyone on these
# domains is in the industry, not a homeowner we should cold-pitch.
BROKERAGE_DOMAINS = {
    "compass.com",
    "kw.com",                 # Keller Williams
    "kellerwilliams.com",
    "century21.com",
    "remax.com",
    "remax-results.com",
    "remax-realty.com",
    "redfin.com",
    "zillow.com",
    "zillowgroup.com",
    "trulia.com",
    "realtor.com",
    "movecorp.com",
    "exprealty.com",
    "exitrealty.com",
    "betterhomesgardens.com",
    "bhgrealestate.com",
    "coldwellbanker.com",
    "cbrealty.com",
    "cb.com",
    "sothebysrealty.com",
    "sothebys.com",
    "douglaselliman.com",
    "elliman.com",
    "berkshirehathaway.com",
    "bhhsrealty.com",
    "weichert.com",
    "howardhanna.com",
    "longandfoster.com",
    "windermere.com",
    "johnlscott.com",
    "edwardjones.com",
    "opendoor.com",
    "offerpad.com",
    "homevestors.com",
    "weBuyUgly.com",
    "webuyhouses.com",
    "ibuyer.com",
}

BROKERAGE_DOMAIN_SUBSTRINGS = (
    "realty",
    "realtor",
    "realestate",
    "real-estate",
    "homes",
    "properties",
    "property",
    "brokerage",
    "broker",
    "sothebys",
    "kellerwilliams",
    "remax",
    "century21",
    "coldwellbanker",
    "berkshirehathaway",
)

BROKERAGE_NAME_TOKENS = (
    "agent",
    "realtor",
    "broker",
    "listing specialist",
    "realtor®",
)

# Title / escrow / closing companies. B2B partners, not homeowner targets.
TITLE_DOMAIN_SUBSTRINGS = (
    "title",
    "closing",
    "closings",
    "escrow",
    "settlement",
    "settlements",
    "abstract",
    "trustee",
    "fidelity",          # Fidelity National Title is the giant
    "stewart",           # Stewart Title
    "firstam",           # First American
    "chicagotitle",
    "oldrepublic",
    "landamerica",
)

# Generic business markers used as last-resort signal. Anything on a
# domain that isn't personal AND isn't matched above falls into
# 'business_other' if it has these tokens, else 'unknown'.
BUSINESS_DOMAIN_SUBSTRINGS = (
    "corp",
    "inc",
    "llc",
    "group",
    "partners",
    "capital",
    "ventures",
    "holdings",
    "investments",
    "investment",
    "associates",
    "consulting",
    "consultants",
    "services",
    "solutions",
    "enterprises",
    "industries",
    "co.",
    ".biz",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@([^\s@]+\.[^\s@]+)$")


def _split_email(email: str) -> tuple[str, str]:
    """Return (local, domain) lowercased. Empty strings on parse failure."""
    if not email or not isinstance(email, str):
        return "", ""
    e = email.strip().lower()
    if "@" not in e:
        return "", ""
    local, _, domain = e.rpartition("@")
    return local, domain


def _domain_endswith_any(domain: str, suffixes: tuple[str, ...]) -> bool:
    return any(domain.endswith(s) for s in suffixes)


def _contains_any(haystack: str, needles) -> bool:
    return any(n in haystack for n in needles)


def _name_contains_any(name: str, tokens: tuple[str, ...]) -> bool:
    if not name:
        return False
    n = " " + name.strip().lower() + " "
    n = n.replace(",", " ").replace(".", ". ")
    return any((" " + t) in n or (t + " ") in n for t in tokens)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_recipient(
    email: str,
    name: str = "",
    phone: Optional[str] = None,
) -> dict:
    """Classify a recipient. Returns a dict the caller can act on.

    Conservative-by-design: only flips to 'homeowner_likely' when the
    domain is a known personal/consumer provider AND no business markers
    fire on the name. Everything else gets a non-homeowner class.

    Args:
        email: recipient email address.
        name:  display name (e.g. "David A. Streubel" or "John Smith Esq.").
        phone: not used in v1, reserved for future TCPA carrier-lookup.

    Returns:
        dict with keys:
            is_homeowner_likely (bool)
            recipient_class     (str)
            confidence          (float, 0.0 -- 1.0)
            reason              (str)
    """
    _ = phone  # reserved -- silence linters

    name = (name or "").strip()
    local, domain = _split_email(email)

    # No parseable email -> we cannot classify, return unknown / not-homeowner.
    if not domain:
        return {
            "is_homeowner_likely": False,
            "recipient_class": "unknown",
            "confidence": 0.0,
            "reason": "no_parseable_email",
        }

    full = f"{local}@{domain}"

    # ----- 1. Attorney / law firm -----
    # Name token check first because it is the strongest signal.
    if _name_contains_any(name, LAWFIRM_NAME_TOKENS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "attorney_firm",
            "confidence": 0.95,
            "reason": f"name_contains_attorney_token:{name}",
        }
    if _contains_any(domain, KNOWN_LAWFIRM_TOKENS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "attorney_firm",
            "confidence": 0.95,
            "reason": f"domain_matches_known_lawfirm:{domain}",
        }
    if _contains_any(domain, LAWFIRM_DOMAIN_SUBSTRINGS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "attorney_firm",
            "confidence": 0.9,
            "reason": f"domain_contains_lawfirm_substring:{domain}",
        }
    if _domain_endswith_any(domain, LAWFIRM_TLDS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "attorney_firm",
            "confidence": 0.85,
            "reason": f"domain_uses_lawfirm_tld:{domain}",
        }

    # ----- 2. Government / public sector -----
    if _domain_endswith_any(domain, GOV_HARD_TLDS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "government_employee",
            "confidence": 0.99,
            "reason": f"domain_uses_gov_tld:{domain}",
        }
    if _contains_any(domain, GOV_DOMAIN_SUBSTRINGS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "government_employee",
            "confidence": 0.9,
            "reason": f"domain_contains_gov_substring:{domain}",
        }
    # .us TLD is soft signal -- many municipal addresses are
    # <user>@<dept>.<city>-<state>.us or <user>@<city>.<state>.us.
    if domain.endswith(".us") and ("." in domain.replace(".us", "")):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "government_employee",
            "confidence": 0.7,
            "reason": f"domain_uses_us_tld_with_subdomain:{domain}",
        }

    # ----- 3. Real-estate agent / brokerage -----
    if domain in BROKERAGE_DOMAINS:
        return {
            "is_homeowner_likely": False,
            "recipient_class": "real_estate_agent",
            "confidence": 0.95,
            "reason": f"domain_known_brokerage:{domain}",
        }
    if _name_contains_any(name, BROKERAGE_NAME_TOKENS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "real_estate_agent",
            "confidence": 0.85,
            "reason": f"name_contains_agent_token:{name}",
        }
    if _contains_any(domain, BROKERAGE_DOMAIN_SUBSTRINGS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "real_estate_agent",
            "confidence": 0.8,
            "reason": f"domain_contains_realestate_substring:{domain}",
        }

    # ----- 4. Title / escrow / closing -----
    if _contains_any(domain, TITLE_DOMAIN_SUBSTRINGS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "title_company",
            "confidence": 0.85,
            "reason": f"domain_contains_title_substring:{domain}",
        }

    # ----- 5. Personal / consumer email -----
    if domain in PERSONAL_DOMAINS:
        # Even on gmail, a name with "Esq" should not be pitched.
        if _name_contains_any(name, LAWFIRM_NAME_TOKENS):
            return {
                "is_homeowner_likely": False,
                "recipient_class": "attorney_firm",
                "confidence": 0.9,
                "reason": f"personal_domain_but_name_has_attorney:{name}",
            }
        if _name_contains_any(name, BROKERAGE_NAME_TOKENS):
            return {
                "is_homeowner_likely": False,
                "recipient_class": "real_estate_agent",
                "confidence": 0.8,
                "reason": f"personal_domain_but_name_has_agent:{name}",
            }
        return {
            "is_homeowner_likely": True,
            "recipient_class": "homeowner_likely",
            "confidence": 0.9,
            "reason": f"personal_email_provider:{domain}",
        }

    # ----- 6. Generic business catchall -----
    if _contains_any(domain, BUSINESS_DOMAIN_SUBSTRINGS):
        return {
            "is_homeowner_likely": False,
            "recipient_class": "business_other",
            "confidence": 0.75,
            "reason": f"domain_contains_business_substring:{domain}",
        }

    # ----- 7. Unknown -----
    # Anything we cannot place. Default to not-homeowner -- safer to
    # skip a possibly-legit lead than to pitch a possibly-business one.
    return {
        "is_homeowner_likely": False,
        "recipient_class": "unknown",
        "confidence": 0.4,
        "reason": f"domain_not_recognized:{domain}",
    }


# ---------------------------------------------------------------------------
# CLI smoke test -- run `python3 recipient_classifier.py` for the four
# verification cases the postmortem demands.
# ---------------------------------------------------------------------------


def _smoke_test() -> int:
    cases = [
        ("Dave@municipalfirm.com", "David A. Streubel"),
        ("john.smith@gmail.com",   "John Smith"),
        ("kathy.green@dallas.gov", "Kathy Green"),
        ("luis@bigrealty.com",     "Luis"),
    ]
    failures = 0
    for email, name in cases:
        r = classify_recipient(email, name)
        line = (
            f"{email:40s}  name={name:25s}  "
            f"class={r['recipient_class']:22s}  "
            f"homeowner={r['is_homeowner_likely']!s:5s}  "
            f"conf={r['confidence']:.2f}  reason={r['reason']}"
        )
        print(line)
        # Sanity asserts so a regression here screams.
        if email.endswith("@gmail.com"):
            if not r["is_homeowner_likely"]:
                failures += 1
        else:
            if r["is_homeowner_likely"]:
                failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(_smoke_test())
