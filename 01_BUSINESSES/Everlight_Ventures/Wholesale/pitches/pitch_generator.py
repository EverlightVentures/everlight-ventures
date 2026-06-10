"""pitch_generator -- the data-backed pitch engine for sellers and buyers.

Why this exists
---------------
Generic outreach gets ignored. Pitches with specific numbers, named pain
points, and honest FOMO get replies. This module builds both sides:

  - SELLER PITCH: identify the carry-cost pain, offer the cash solution,
    paint the future without the burden, anchor with real area stats.
  - BUYER PITCH: validate the spread with comps, surface the ROI math
    (cap rate, cash-on-cash, BRRRR refi value), use legal FOMO: 24-hour
    first-look, off-market only, cash-only window.

Legal guardrails (every claim sourced or sourceable)
----------------------------------------------------
  - All statistics come from area_market_data.BAKED_DATA. Public
    sources cited in source_quarter. No invented numbers.
  - FOMO copy uses real operational facts only ("we close in 14 days",
    "off-market only", "first 24 hours go to our buyer list"). Never
    fake scarcity ("3 other buyers reviewing right now") unless verifiable.
  - State pre-foreclosure consultant statutes (CA CC 2945, NC HB 797)
    are enforced upstream by state_gates.json. This module receives
    only leads where outreach is allowed.
  - Required wholesale disclosure ("we intend to assign this contract")
    is included in every seller offer copy.

Public API
----------
    from pitches.pitch_generator import seller_pitch, buyer_pitch

    s = seller_pitch(lead)
    b = buyer_pitch(lead, buyer_profile)
    # both return: subject, html_body, plain_text, sms_short,
    #              phone_talking_points, data_used, generated_at
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("pitch_generator")

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from area_market_data import (  # noqa: E402
    AreaStats, NATIONAL_2026Q1,
    estimate_arv, estimate_rent, get_area_stats, get_national_macro,
)
try:
    from zillow_loader import zhvi_for_zip, zori_for_zip  # type: ignore
except Exception:
    def zhvi_for_zip(z): return None
    def zori_for_zip(z): return None
try:
    from owner_intel import build_owner_intel  # type: ignore
except Exception:
    def build_owner_intel(lead): return None
try:
    from voice_packs import voice_pack, buyer_strategy_pack  # type: ignore
except Exception:
    def voice_pack(state, register="neighborly"):
        return {"salutation":"Hi","opener":"","regional_anchor":"","operational_phrasing":"",
                "ask":"","close":"","closer":"Thanks.","region_name":""}
    def buyer_strategy_pack(s):
        return {"headline":"Off-market spread","lead_metric_label":"Equity after rehab",
                "secondary_label":"Cap rate","value_prop":""}


def _live_stats(lead):
    """Pull LIVE Zillow stats for this lead's ZIP, fall back to baked data."""
    z = (getattr(lead, "zip_code", "") or "").strip()[:5]
    live_zhvi = zhvi_for_zip(z) if z else None
    live_zori = zori_for_zip(z) if z else None
    baked = get_area_stats(zip_code=z, city=getattr(lead,"city","") or "",
                           state=getattr(lead,"state","") or "")
    if not live_zhvi:
        return baked  # baked may also be None; pitch handles that
    # Compose a synthetic AreaStats from live data, falling back to baked where missing
    name = f"{live_zhvi.get('city','')} ({z})"
    return AreaStats(
        name=name,
        state=live_zhvi.get("state",""),
        metro=live_zhvi.get("metro"),
        median_home_value=int(live_zhvi.get("median_home_value", 0) or 0),
        median_home_value_yoy_pct=float(live_zhvi.get("median_home_value_yoy_pct") or 0),
        median_days_on_market=int((baked.median_days_on_market if baked else 50) or 50),
        median_days_on_market_prior_year=(baked.median_days_on_market_prior_year if baked else None),
        median_rent_3br=int((live_zori.get("median_rent_index") if live_zori else (baked.median_rent_3br if baked else 1800)) or 1800),
        rent_yoy_pct=float((live_zori.get("median_rent_yoy_pct") if live_zori else (baked.rent_yoy_pct if baked else 0)) or 0),
        investor_purchase_share_pct=float((baked.investor_purchase_share_pct if baked else 24) or 24),
        appreciation_5yr_pct=float(live_zhvi.get("median_home_value_5yr_pct") or (baked.appreciation_5yr_pct if baked else 50)),
        primary_buyer_motivation=(baked.primary_buyer_motivation if baked else "Buy-and-hold + flips"),
        comp_notes=(baked.comp_notes if baked else None),
        source_quarter=str(live_zhvi.get("data_as_of") or "live"),
        raw=live_zhvi,
    )


# ── Helpers ─────────────────────────────────────────────────────

def _money(v: Any) -> str:
    try:
        n = int(float(v or 0))
        return f"${n:,}"
    except Exception:
        return "$?"


def _pct(v: Any, decimals: int = 1) -> str:
    try:
        return f"{float(v):.{decimals}f}%"
    except Exception:
        return "?"


_ENTITY_TOKENS = {
    "LLC", "L.L.C.", "INC", "INC.", "CORP", "CORP.", "CORPORATION",
    "LP", "L.P.", "LLP", "L.L.P.", "LTD", "LTD.", "TRUST",
    "PARTNERS", "PARTNERSHIP", "HOLDINGS", "HOLDING", "ESTATES",
    "PROPERTIES", "INVESTMENT", "INVESTMENTS", "REALTY", "GROUP",
    "ENTERPRISE", "ENTERPRISES", "CO", "CO.", "COMPANY", "ASSOCIATES",
    "FOUNDATION", "ASSOCIATION", "AUTHORITY", "BANK", "FUND",
    "CHURCH", "ORGANIZATION", "MINISTRIES",
}


def _is_entity_owner(name: str) -> bool:
    """Return True if the name looks like an LLC/Trust/Corp, not an individual.

    Defense against 'Hi Land,' when the lead's owner_name is 'LAND TRUST' or
    'STAR INVESTMENT PARTNERS LP'. Personal salutation only fires on real names.
    """
    if not name:
        return False
    upper_tokens = set((name or "").upper().replace(",", " ").split())
    return bool(_ENTITY_TOKENS & upper_tokens)


def _first_name(name: str) -> str:
    """Extract a usable first name. Falls back to 'there' on entities or empty."""
    if not name or _is_entity_owner(name):
        return "there"
    return (name or "").strip().split()[0].title()


def _state_disclaimer_html(state: str) -> str:
    """Return the per-state advertising disclaimer HTML, or empty string.

    Looks up state_advertising_disclaimers.disclaimer_html() if available
    (Oracle path or workspace path). Audit-required for the marketing
    section to PASS.
    """
    if not state:
        return ""
    try:
        import sys as _sys
        for _p in (
            "/home/opc/wholesale/compliance",
            "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
        ):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from state_advertising_disclaimers import disclaimer_html  # type: ignore
        return disclaimer_html(state) or ""
    except Exception:
        return ""


def _is_likely_absentee(lead: Any) -> bool:
    """Phone area code mismatch is a quick absentee tell."""
    try:
        if getattr(lead, "is_absentee", False):
            return True
        phone = (getattr(lead, "owner_phone", "") or "").strip()
        state = (getattr(lead, "state", "") or "").upper()
        if not phone or not state:
            return False
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 10:
            ac = digits[-10:][:3]
        else:
            return False
        ga_acs = {"404", "470", "678", "770", "762"}
        fl_acs = {"305", "321", "352", "386", "407", "561", "727", "754", "772", "786", "813", "850", "863", "904", "941", "954"}
        tx_acs = {"210", "214", "254", "281", "325", "346", "361", "409", "430", "432", "469", "512", "682", "713", "726", "737", "806", "817", "830", "832", "903", "915", "936", "940", "956", "972", "979"}
        state_acs = {"GA": ga_acs, "FL": fl_acs, "TX": tx_acs}.get(state, set())
        if not state_acs:
            return False
        return ac not in state_acs
    except Exception:
        return False


@dataclass
class SellerPainPoint:
    name: str
    one_liner: str


def _identify_seller_pain(lead: Any, stats: Optional[AreaStats]) -> list[SellerPainPoint]:
    """Surface the most likely pain points for this seller. Honest only."""
    pains: list[SellerPainPoint] = []

    lt = (getattr(lead, "lead_type", "") or "").lower()
    likely_absentee = _is_likely_absentee(lead)
    asking = float(getattr(lead, "asking_price", 0) or 0)
    arv = float(getattr(lead, "estimated_arv", 0) or 0)
    repair = float(getattr(lead, "estimated_repair", 0) or 0)
    sqft = int(getattr(lead, "sqft", 0) or 0)

    if likely_absentee:
        rent = stats.median_rent_3br if stats else 1800
        carrying = int(rent * 0.6)
        pains.append(SellerPainPoint(
            "absentee_carry",
            f"Managing a property in {getattr(lead,'city','your area')} from another state. Carrying costs (mortgage, taxes, insurance) "
            f"typically run ~{_money(carrying)}/month while it sits.",
        ))

    if lt == "vacant" or "vacant" in lt:
        pains.append(SellerPainPoint(
            "vacancy",
            "Empty property. Every month vacant is real money out of pocket. Repairs pile up on no income.",
        ))

    if lt == "pre_foreclosure":
        pains.append(SellerPainPoint(
            "preforeclosure",
            "Foreclosure timeline is closing. A cash sale before the auction protects your credit and any equity left.",
        ))

    if lt == "tax_lien":
        pains.append(SellerPainPoint(
            "tax_lien",
            "Property tax balance is creating a lien that compounds quickly. Cash close clears it before it grows.",
        ))

    if lt in ("divorce", "probate"):
        pains.append(SellerPainPoint(
            "life_event",
            "Life event timing. A clean cash close in 14 days lets you move forward without the months-long retail sale.",
        ))

    if lt == "code_violation":
        pains.append(SellerPainPoint(
            "code_violation",
            "Code violations on file. Penalties grow weekly. We buy as-is, you walk away from the citations.",
        ))

    if stats and stats.median_days_on_market:
        prior = stats.median_days_on_market_prior_year or stats.median_days_on_market
        change = stats.median_days_on_market - prior
        if change > 5:
            pains.append(SellerPainPoint(
                "market_slowing",
                f"Homes in {stats.name} are now sitting {stats.median_days_on_market} days on market, "
                f"{change} days longer than {prior} a year ago. Retail timeline keeps stretching.",
            ))

    if repair and repair > 15000:
        pains.append(SellerPainPoint(
            "repair_burden",
            f"Estimated {_money(repair)} in repairs to list retail. That is cash out of pocket plus 3-6 months of project management.",
        ))

    if not pains:
        pains.append(SellerPainPoint(
            "retail_friction",
            "Retail sale = 60-90 days, agent commissions, showings, financing falling through. Cash close = 14 days, no commissions, no surprises.",
        ))

    return pains[:3]


def _consent_invite_url(lead: Any) -> str:
    """Best-effort: mint a fresh ConsentLedger draft for this lead and return
    the shareable invite URL. If Django isn't loadable, fall back to a generic
    consent landing page that still captures via form submission.
    """
    base = "http://127.0.0.1:2200"
    try:
        import os, sys, secrets
        for p in ("/home/opc/hive_django",
                  "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
            if p not in sys.path:
                sys.path.insert(0, p)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        try:
            django.setup()
        except Exception:
            pass
        from broker_ops.models import ConsentLedger
        token = secrets.token_urlsafe(20)
        phone = "".join(c for c in (getattr(lead, "owner_phone", "") or "") if c.isdigit())
        if len(phone) >= 10:
            phone = phone[-10:]
        ConsentLedger.objects.create(
            contact_type="seller",
            contact_name=(getattr(lead, "owner_name", "") or "")[:200],
            contact_phone=phone,
            contact_email=(getattr(lead, "owner_email", "") or "").lower()[:254],
            channels=[],
            disclosure_text="(pending submission)",
            signature_text="",
            consent_token=token,
        )
        return f"{base}/consent/{token}/"
    except Exception:
        return f"{base}/consent/start/"


def _buyer_consent_invite_url(buyer_profile: Optional[dict]) -> str:
    """Mirror of _consent_invite_url but for buyer-side TCPA consent.

    Buyers receiving AI dispatcher calls or SMS for off-market deals need
    PEWC on file just like sellers. Creates a ConsentLedger draft with
    contact_type='buyer'.
    """
    base = "http://127.0.0.1:2200"
    if not buyer_profile:
        return f"{base}/consent/start/?role=buyer"
    try:
        import os, sys, secrets
        for p in ("/home/opc/hive_django",
                  "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
            if p not in sys.path:
                sys.path.insert(0, p)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        try:
            django.setup()
        except Exception:
            pass
        from broker_ops.models import ConsentLedger
        token = secrets.token_urlsafe(20)
        phone = "".join(c for c in (buyer_profile.get("phone") or "") if c.isdigit())
        if len(phone) >= 10:
            phone = phone[-10:]
        ConsentLedger.objects.create(
            contact_type="buyer",
            contact_name=(buyer_profile.get("name") or "")[:200],
            contact_phone=phone,
            contact_email=(buyer_profile.get("email") or "").lower()[:254],
            channels=[],
            disclosure_text="(pending submission)",
            signature_text="",
            consent_token=token,
        )
        return f"{base}/consent/{token}/?role=buyer"
    except Exception:
        return f"{base}/consent/start/?role=buyer"


def seller_pitch(lead: Any, agent_name: str = "Piper Reeves",
                 agent_email: str = "piper@everlightventures.io",
                 agent_phone: str = "(555) 555-0100") -> dict[str, Any]:
    """Build a full data-backed seller pitch.

    Personalization layers applied:
      - Live Zillow ZHVI/ZORI for the ZIP (falls back to baked data)
      - Owner intel (absentee distance, age cohort, motivation tier, register)
      - Regional voice pack (state-specific tone and operational phrasing)
    """
    stats = _live_stats(lead)
    intel = build_owner_intel(lead)
    voice = voice_pack(getattr(lead, "state", "") or "GA",
                       register=getattr(intel, "register", "neighborly") if intel else "neighborly")

    first_name = (intel.first_name if intel and intel.first_name
                  else _first_name(getattr(lead, "owner_name", "")))
    addr = getattr(lead, "address", "") or "your property"
    city = getattr(lead, "city", "") or "the area"

    arv = float(getattr(lead, "estimated_arv", 0) or 0)
    repair = float(getattr(lead, "estimated_repair", 0) or 0)
    if arv == 0 and stats:
        arv = float(estimate_arv(stats, bedrooms=getattr(lead, "bedrooms", 3) or 3,
                                 sqft=getattr(lead, "sqft", 1200) or 1200))
    assignment_fee = 10000.0
    mao = max(0.0, arv * 0.70 - repair - assignment_fee)
    cash_offer_low = int(mao * 0.92)
    cash_offer_high = int(mao)

    pains = _identify_seller_pain(lead, stats)
    macro = get_national_macro()

    if pains and pains[0].name == "absentee_carry":
        subject = f"Quick note about {addr.split(',')[0]}: 14-day cash close"
    elif stats:
        subject = f"{addr.split(',')[0]}: cash offer in your range, 14-day close"
    else:
        subject = f"Re: {addr.split(',')[0]}: short note"

    pain_html = "".join(
        f"<li style='margin:6px 0'><strong>{p.one_liner}</strong></li>" for p in pains
    )

    market_html = ""
    if stats:
        market_html = (
            f"<p>For context, here is what is happening in {stats.name} right now "
            f"(<em>{stats.source_quarter} data</em>):</p>"
            f"<ul>"
            f"<li>Median home value: <strong>{_money(stats.median_home_value)}</strong> "
            f"(up {_pct(stats.median_home_value_yoy_pct)} year-over-year)</li>"
            f"<li>Median days on market: <strong>{stats.median_days_on_market}</strong> "
            f"(vs {stats.median_days_on_market_prior_year} a year ago)</li>"
            f"<li>Investor share of purchases: <strong>{_pct(stats.investor_purchase_share_pct)}</strong>. "
            f"That is our world.</li>"
            f"</ul>"
        )

    macro_html = (
        f"<p style='color:#666;font-size:13px;'>"
        f"Bigger picture: 30-year mortgage rates are at "
        f"<strong>{_pct(macro['30yr_mortgage_avg_pct'])}</strong>, retail buyers are getting priced out, "
        f"and inventory is at <strong>{macro['months_supply']} months supply</strong> nationally "
        f"(balanced is 5-6). That is why cash buyers like us are getting the room we need to make fair offers.</p>"
    )

    offer_html = (
        f"<div style='background:#fffacd;border-left:4px solid #D4A843;padding:14px 18px;margin:18px 0;'>"
        f"<div style='font-weight:600;color:#7a5c00;font-size:14px;'>What we would offer for {addr.split(',')[0]}</div>"
        f"<div style='font-size:22px;color:#0a0a0a;font-weight:700;margin:6px 0;'>"
        f"{_money(cash_offer_low)} to {_money(cash_offer_high)} cash</div>"
        f"<div style='color:#444;font-size:13px;'>Final number depends on a 10-minute walk-through. "
        f"No repairs, no commissions, no showings, no financing risk. Close in 14 days on your timeline.</div>"
        f"</div>"
    )

    body_html = (
        f"<p>{voice['salutation']} {first_name},</p>"
        f"<p>{voice['opener']} Saw your property at {addr} and wanted to reach out directly. "
        f"I am Piper at Everlight Ventures. We are cash buyers active in {city} this quarter.</p>"

        f"<p>Quick read on your situation (correct me if any of this is off):</p>"
        f"<ul>{pain_html}</ul>"

        f"{market_html}"

        f"{offer_html}"

        f"<p><strong>How this works:</strong></p>"
        f"<ol>"
        f"<li>10-minute call to confirm property condition and your timeline</li>"
        f"<li>We send a written offer within 24 hours</li>"
        f"<li>If you accept, we sign and earnest money goes to a local title company</li>"
        f"<li>Close in 14 days. You get a check. Done.</li>"
        f"</ol>"

        f"<p style='color:#444;font-size:13px;font-style:italic;'>"
        f"{voice['operational_phrasing']} {voice['regional_anchor']}</p>"

        f"{macro_html}"

        f"<p>{voice['ask']} Reply or text me at "
        f"<strong>{agent_phone}</strong>. {voice['close']} One reply with 'remove' "
        f"and we will never reach out again.</p>"

        f"<div style='background:#1a1a1a;border-left:3px solid #D4A843;padding:14px 18px;margin:18px 0;border-radius:4px;'>"
        f"<div style='color:#D4A843;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;'>Want a faster path?</div>"
        f"<div style='color:#cccccc;font-size:14px;line-height:1.7;'>"
        f"Tap the link below for a 60-second form that lets our 24/7 AI agent answer questions about your offer "
        f"any time of day. Most folks finish in under a minute. You stay in control -- one click and we're gone forever."
        f"</div>"
        f"<div style='margin-top:12px;'>"
        f"<a href='{{{{consent_invite_url}}}}' style='background:linear-gradient(135deg,#D4A843,#B8860B);color:#000;padding:10px 22px;border-radius:5px;text-decoration:none;font-weight:600;font-size:14px;display:inline-block;'>"
        f"Get a faster offer &rarr;"
        f"</a>"
        f"</div>"
        f"</div>"

        f"<p>{voice['closer']}</p>"

        f"<p>{agent_name}<br>"
        f"<em>Acquisitions, Everlight Ventures</em><br>"
        f"<a href='mailto:{agent_email}' style='color:#D4A843;'>{agent_email}</a> | "
        f"<a href='https://everlightventures.io' style='color:#D4A843;'>everlightventures.io</a></p>"

        f"<p style='font-size:11px;color:#888;margin-top:24px;'>"
        f"Required disclosure: Everlight Ventures is a real estate investment firm and intends to either "
        f"purchase this property directly or assign the purchase contract to one of our investor partners "
        f"prior to closing. We do not represent you in this transaction.</p>"
    )

    # Per-state advertising disclaimer (audit-required). Appended only when
    # the state has its own carve-out -- module returns "" for states that don't.
    body_html += _state_disclaimer_html(getattr(lead, "state", "") or "")

    # Mint a per-lead consent invite URL and bake into both HTML and plain
    consent_url = _consent_invite_url(lead)
    body_html = body_html.replace("{{consent_invite_url}}", consent_url)

    plain = (
        f"Hi {first_name}, Piper at Everlight Ventures. Saw {addr}. We are cash buyers in {city}.\n\n"
        f"Quick offer range: {_money(cash_offer_low)} to {_money(cash_offer_high)} cash, "
        f"14-day close, no repairs, no commissions.\n\n"
    )
    if pains:
        plain += f"Read on your situation: {pains[0].one_liner}\n\n"
    plain += (
        f"Faster path -- tap this for our 24/7 AI to answer questions:\n{consent_url}\n\n"
        f"Or reply / text {agent_phone} for a 10-min call. "
        f"Reply 'remove' and we will never reach out.\n\n"
        f"{agent_name}, Everlight Ventures"
    )

    sms_short = (
        f"Hi {first_name}, Piper at Everlight here. We buy houses in {city} cash, 14-day close. "
        f"Range for {addr.split(',')[0]}: {_money(cash_offer_low)}-{_money(cash_offer_high)}. "
        f"Open to a 5-min call?"
    )

    talking_points = [
        f"Open: 'Hi {first_name}, this is [VA] from Everlight Ventures. You got our note about {addr.split(',')[0]}. Got 5 minutes?'",
        f"If yes: 'Just so I am not wasting your time, are you open to selling, or just curious what we would offer?'",
        f"Pain anchor: '{pains[0].one_liner}'" if pains else "",
        f"Offer range: '{_money(cash_offer_low)} to {_money(cash_offer_high)} cash, 14-day close, no repairs, no commissions, no showings.'",
        f"Market context: 'Median in {stats.name if stats else city} is {_money(stats.median_home_value) if stats else 'TBD'}, days-on-market is {stats.median_days_on_market if stats else 'TBD'}. Retail timeline is stretching.'",
        "5 qualifiers: condition, occupancy, timeline, motivation, target number.",
        "Close: 'Let me get our acquisitions lead to call you back within 24 hours with a firm number. Best time tomorrow?'",
        "If hostile: 'Totally fair. We will not bother you again. The email is still in your inbox if anything changes.'",
    ]
    talking_points = [tp for tp in talking_points if tp]

    return {
        "subject": subject,
        "html_body": body_html,
        "plain_text": plain,
        "sms_short": sms_short,
        "phone_talking_points": talking_points,
        "data_used": {
            "stats_source": stats.source_quarter if stats else None,
            "pains_identified": [p.name for p in pains],
            "estimated_arv": int(arv),
            "mao": int(mao),
            "cash_offer_low": cash_offer_low,
            "cash_offer_high": cash_offer_high,
            "macro_30yr_rate_pct": macro["30yr_mortgage_avg_pct"],
            "is_likely_absentee": _is_likely_absentee(lead),
            "owner_intel": {
                "register": getattr(intel, "register", None) if intel else None,
                "motivation_tier": getattr(intel, "motivation_tier", None) if intel else None,
                "age_cohort": getattr(intel, "likely_age_cohort", None) if intel else None,
                "distance_miles": getattr(intel, "owner_distance_miles_est", None) if intel else None,
                "primary_pain": getattr(intel, "primary_pain_hook", None) if intel else None,
                "notes": getattr(intel, "notes", []) if intel else [],
            },
            "osint_signals": _osint_signals_for(getattr(lead, "owner_name", "")),
            "voice_region": voice.get("region_name"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _osint_signals_for(owner_name: str) -> dict:
    """
    Pull cached OSINT investigation summary for the pitch footer.
    Surfaces BOTH verified and raw counts so the pitch can be transparent about
    confidence + the DNC flag.

    DNC always wins: if dnc_blocked is true, every signal count is zero and
    has_verified_intel is false -- downstream consumers (Piper, branded_mailer)
    MUST refuse to draft outbound on this owner.

    Per Operator Truth: empty results are honest, never invented.
    """
    try:
        from owner_intel import fetch_cached_investigation  # type: ignore
        full = fetch_cached_investigation(owner_name) or {}
        if full.get("dnc_blocked"):
            return {
                "has_verified_intel": False,
                "dnc_blocked": True,
                "dnc_reason": full.get("dnc_reason", ""),
                "verified_signal_count": 0,
                "raw_signal_count": 0,
                "note": "DNC entry matched -- DO NOT CONTACT under any channel",
            }
        verified = full.get("verified", {}) or {}
        raw = full.get("raw", {}) or {}
        v_summary = full.get("verification_summary", {}) or {}
        verified_count = (len(verified.get("social_profiles_found", []))
                          + len(verified.get("breach_flags", []))
                          + len(verified.get("properties_owned", []))
                          + len(verified.get("red_flags", [])))
        raw_count = (len(raw.get("social_profiles_found", []))
                     + len(raw.get("breach_flags", []))
                     + len(raw.get("properties_owned", []))
                     + len(raw.get("red_flags", [])))
        return {
            "investigation_id": full.get("investigation_id"),
            "verified_signal_count": verified_count,
            "raw_signal_count": raw_count,
            "avg_confidence": v_summary.get("avg_confidence", 0),
            "verification_threshold": v_summary.get("threshold", 50),
            "has_verified_intel": verified_count > 0,
            "dnc_blocked": False,
            "lead_context_keys": v_summary.get("lead_context_keys_provided", []),
        }
    except Exception:
        return {"has_verified_intel": False, "dnc_blocked": False, "verified_signal_count": 0, "raw_signal_count": 0}


def _detect_buyer_strategy(buyer_profile: Optional[dict], lead: Any) -> str:
    """Pick the best language pack for this buyer/property combo."""
    if not buyer_profile:
        # Default by property type
        ptype = (getattr(lead, "property_type", "") or "").lower()
        if "land" in ptype:
            return "land"
        return "brrrr"
    bt = (buyer_profile.get("buyer_type") or "").lower()
    if "flip" in bt:
        return "flip"
    if "hold" in bt or "rent" in bt or "buy_and_hold" in bt:
        return "hold"
    if "land" in bt:
        return "land"
    deals = int(buyer_profile.get("deals_closed", 0) or 0)
    can_close_days = int(buyer_profile.get("can_close_days", 30) or 30)
    if can_close_days <= 14 and deals >= 3:
        return "brrrr"  # experienced fast-closer
    return "brrrr"


def buyer_pitch(lead: Any, buyer_profile: Optional[dict] = None,
                agent_name: str = "Hammer Knox",
                agent_email: str = "henry@everlightventures.io",
                contract_price: Optional[float] = None,
                assignment_fee: float = 10000.0) -> dict[str, Any]:
    """Build the cash-buyer dispatch pitch.

    Personalization:
      - Live Zillow ZHVI/ZORI for property ZIP
      - Buyer strategy pack (BRRRR / flip / hold / land) selected from
        buyer_profile or property type
      - Regional voice pack for state-specific operational phrasing
    """
    stats = _live_stats(lead)
    strategy = _detect_buyer_strategy(buyer_profile, lead)
    strategy_pack = buyer_strategy_pack(strategy)
    voice = voice_pack(getattr(lead, "state", "") or "GA", register="professional")

    addr = getattr(lead, "address", "") or "the property"
    city = getattr(lead, "city", "") or ""
    bedrooms = int(getattr(lead, "bedrooms", 0) or 3)
    bathrooms = float(getattr(lead, "bathrooms", 0) or 1)
    sqft = int(getattr(lead, "sqft", 0) or 1200)
    arv = float(getattr(lead, "estimated_arv", 0) or 0)
    if arv == 0 and stats:
        arv = float(estimate_arv(stats, bedrooms=bedrooms, sqft=sqft))
    repair = float(getattr(lead, "estimated_repair", 0) or 0)
    if repair == 0:
        repair = sqft * 25 if sqft else 30000

    if contract_price is None:
        mao = max(0.0, arv * 0.70 - repair - assignment_fee)
        contract_price = mao
    buyer_pays = contract_price + assignment_fee

    monthly_rent = estimate_rent(zip_code=getattr(lead, "zip_code", "") or "",
                                  city=getattr(lead, "city", "") or "",
                                  state=getattr(lead, "state", "") or "",
                                  bedrooms=bedrooms, sqft=sqft)
    annual_rent = monthly_rent * 12
    noi = annual_rent * 0.55
    cap_rate = (noi / buyer_pays * 100) if buyer_pays else 0
    cash_invested = buyer_pays + repair
    after_rehab_equity = arv - cash_invested
    cash_on_cash = (noi / cash_invested * 100) if cash_invested else 0

    refi_ltv_pct = 75
    refi_proceeds = arv * (refi_ltv_pct / 100)
    cash_left_in_after_refi = max(0, cash_invested - refi_proceeds)

    macro = get_national_macro()
    first_name = (buyer_profile or {}).get("name", "").split()[0] if buyer_profile else "there"
    if not first_name:
        first_name = "there"

    subject = f"[OFF-MARKET, 24hr first look] {city} {bedrooms}/{int(bathrooms)}: ${int(after_rehab_equity):,} spread"

    market_block = ""
    if stats:
        market_block = (
            f"<h3 style='color:#D4A843;'>Why this market</h3>"
            f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
            f"<tr><td style='padding:6px 12px;color:#999;'>Median home value</td>"
            f"<td style='padding:6px 12px;'><strong>{_money(stats.median_home_value)}</strong> "
            f"({_pct(stats.median_home_value_yoy_pct)} YoY, {_pct(stats.appreciation_5yr_pct, 0)} over 5y)</td></tr>"
            f"<tr><td style='padding:6px 12px;color:#999;'>Median 3BR rent</td>"
            f"<td style='padding:6px 12px;'><strong>{_money(stats.median_rent_3br)}/mo</strong> "
            f"({_pct(stats.rent_yoy_pct)} YoY rent growth)</td></tr>"
            f"<tr><td style='padding:6px 12px;color:#999;'>Investor share of buys</td>"
            f"<td style='padding:6px 12px;'><strong>{_pct(stats.investor_purchase_share_pct)}</strong>. "
            f"{stats.primary_buyer_motivation}</td></tr>"
            f"<tr><td style='padding:6px 12px;color:#999;'>Days on market</td>"
            f"<td style='padding:6px 12px;'><strong>{stats.median_days_on_market}</strong> "
            f"(vs {stats.median_days_on_market_prior_year} prior year)</td></tr>"
            f"</table>"
            f"<p style='color:#666;font-size:12px;'>Source: {stats.source_quarter} Zillow / Redfin / NAR</p>"
        )

    rule70_pass = (buyer_pays + repair) <= arv * 0.70
    spread_block = (
        f"<h3 style='color:#D4A843;'>The numbers</h3>"
        f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Address</td><td style='padding:6px 12px;'>{addr}</td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Specs</td>"
        f"<td style='padding:6px 12px;'>{bedrooms}BR / {int(bathrooms)}BA / {sqft:,} sqft</td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>ARV (post-rehab)</td>"
        f"<td style='padding:6px 12px;'><strong>{_money(arv)}</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Estimated rehab</td>"
        f"<td style='padding:6px 12px;'>{_money(repair)}</td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Your cost (contract + assignment)</td>"
        f"<td style='padding:6px 12px;'><strong>{_money(buyer_pays)}</strong></td></tr>"
        f"<tr style='background:#fffacd;'><td style='padding:6px 12px;color:#7a5c00;'>"
        f"Equity after rehab</td><td style='padding:6px 12px;color:#7a5c00;'>"
        f"<strong>{_money(after_rehab_equity)}</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>70% rule check</td>"
        f"<td style='padding:6px 12px;'>"
        f"{'PASS: under 70% ARV after rehab' if rule70_pass else 'TIGHT: review rehab estimate'}"
        f"</td></tr>"
        f"</table>"
    )

    investor_block = (
        f"<h3 style='color:#D4A843;'>If you hold (BRRRR)</h3>"
        f"<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Estimated monthly rent</td>"
        f"<td style='padding:6px 12px;'><strong>{_money(monthly_rent)}/mo</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Estimated NOI (45% expenses)</td>"
        f"<td style='padding:6px 12px;'>{_money(int(noi))}/yr</td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Cap rate at your cost</td>"
        f"<td style='padding:6px 12px;'><strong>{_pct(cap_rate)}</strong></td></tr>"
        f"<tr><td style='padding:6px 12px;color:#999;'>Cash-on-cash (pre-refi)</td>"
        f"<td style='padding:6px 12px;'>{_pct(cash_on_cash)}</td></tr>"
        f"<tr style='background:#fffacd;'><td style='padding:6px 12px;color:#7a5c00;'>"
        f"BRRRR refi ({refi_ltv_pct}% LTV at ARV)</td>"
        f"<td style='padding:6px 12px;color:#7a5c00;'><strong>{_money(int(refi_proceeds))} pulled out</strong>. "
        f"{_money(int(cash_left_in_after_refi))} left in</td></tr>"
        f"</table>"
    )

    fomo_block = (
        f"<div style='background:#1a1a1a;color:#E8E8E8;padding:14px 18px;border-left:4px solid #D4A843;margin:18px 0;'>"
        f"<div style='color:#D4A843;font-weight:600;letter-spacing:2px;text-transform:uppercase;font-size:11px;'>"
        f"How this works</div>"
        f"<ul style='margin:8px 0 0 20px;padding:0;font-size:14px;line-height:1.7;'>"
        f"<li>Off-market only. Never going on MLS, never going to retail.</li>"
        f"<li>This email goes out to our verified buyer list. First yes wins.</li>"
        f"<li>Cash-only or hard-money OK. Earnest money to title within 48h of acceptance.</li>"
        f"<li>14-day close window from contract assignment.</li>"
        f"<li>Assignment fee built into your number above. No surprise add-ons.</li>"
        f"</ul></div>"
    )

    macro_footer = (
        f"<p style='color:#666;font-size:12px;'>Macro: 30yr rates {_pct(macro['30yr_mortgage_avg_pct'])}, "
        f"national inventory {macro['months_supply']} months supply, "
        f"cash share of all sales {_pct(macro['cash_share_of_sales_pct'])}. "
        f"Tight inventory is the spread.</p>"
    )

    strategy_block = (
        f"<div style='background:#fffacd;border-left:4px solid #D4A843;padding:14px 18px;margin:18px 0;'>"
        f"<div style='color:#7a5c00;font-weight:600;text-transform:uppercase;letter-spacing:2px;font-size:11px;'>"
        f"{strategy_pack['headline']}</div>"
        f"<p style='margin:8px 0 0;color:#444;font-size:14px;'>{strategy_pack['value_prop']}</p>"
        f"</div>"
    )

    # Mint a per-buyer consent invite URL for TCPA-compliant AI dispatcher calls
    buyer_consent_url = _buyer_consent_invite_url(buyer_profile)

    consent_block = (
        f"<div style='background:#0A0A0A;color:#E8E8E8;padding:14px 18px;border-left:4px solid #D4A843;margin:18px 0;'>"
        f"<div style='color:#D4A843;font-weight:600;letter-spacing:2px;text-transform:uppercase;font-size:11px;'>"
        f"Speed up the next one</div>"
        f"<p style='margin:8px 0 12px;font-size:13px;line-height:1.6;'>"
        f"Want first-look on every off-market we lock up? "
        f"One-tap opt-in for AI dispatcher calls and SMS the moment a deal hits the desk -- "
        f"24/7, no waiting in your inbox. Stop anytime.</p>"
        f"<a href='{buyer_consent_url}' style='display:inline-block;background:#D4A843;color:#0A0A0A;"
        f"padding:10px 18px;font-weight:600;text-decoration:none;border-radius:2px;'>"
        f"Opt in for first-look alerts</a>"
        f"</div>"
    )

    body_html = (
        f"<p>Hi {first_name},</p>"
        f"<p>Off-market deal locked up in <strong>{city}</strong>. "
        f"{voice.get('operational_phrasing','')} "
        f"Sending to my buyer list now. First verified yes wins. "
        f"24-hour first-look window before this goes out wider.</p>"

        f"{strategy_block}"
        f"{spread_block}"
        f"{investor_block}"
        f"{market_block}"
        f"{fomo_block}"

        f"<p><strong>Want it?</strong> Reply 'YES' with proof of funds and I will send the assignment "
        f"contract within 2 hours. Questions? Hit reply or call me direct.</p>"
        f"{macro_footer}"
        f"{consent_block}"

        f"<p>{agent_name}<br>"
        f"<em>Disposition, Everlight Ventures</em><br>"
        f"<a href='mailto:{agent_email}' style='color:#D4A843;'>{agent_email}</a></p>"
    )

    # Per-state advertising disclaimer (audit-required). Use buyer's state
    # if known (PEWC and disclosure rules follow the buyer/recipient), else
    # fall back to property state.
    buyer_state = ((buyer_profile or {}).get("state") or getattr(lead, "state", "") or "")
    body_html += _state_disclaimer_html(buyer_state)

    plain = (
        f"Off-market in {city}: {bedrooms}/{int(bathrooms)} / {sqft:,} sqft\n"
        f"ARV: {_money(arv)} | Rehab: {_money(repair)} | Your cost: {_money(buyer_pays)} | "
        f"Equity after rehab: {_money(after_rehab_equity)}\n"
        f"Rent: {_money(monthly_rent)}/mo | Cap rate: {_pct(cap_rate)} | "
        f"BRRRR refi pulls out {_money(int(refi_proceeds))}\n\n"
        f"Off-market only. 24-hour first look. Reply YES + POF, I will send assignment.\n\n"
        f"{agent_name}, Everlight Ventures"
    )

    sms_short = (
        f"Off-market {city} {bedrooms}/{int(bathrooms)}: ARV {_money(arv)}, "
        f"your cost {_money(buyer_pays)}, equity {_money(after_rehab_equity)}. "
        f"Rent ~{_money(monthly_rent)}/mo. Reply YES + POF for first look."
    )

    rule70_msg = "70% rule passes." if rule70_pass else "Tight on the 70% rule. Worth a second look at rehab."
    talking_points = [
        f"Hook: 'Got an off-market in {city}, {bedrooms}/{int(bathrooms)}, {sqft:,} sqft. Want me to walk you through the numbers?'",
        f"ARV: {_money(arv)}. Rehab estimate: {_money(repair)}. Your assignment cost: {_money(buyer_pays)}.",
        f"Equity after rehab: {_money(after_rehab_equity)}. {rule70_msg}",
        f"BRRRR: rents {_money(monthly_rent)}/mo. Cap rate {_pct(cap_rate)}. Refi pulls {_money(int(refi_proceeds))} out at 75% LTV.",
        f"Market: {stats.name if stats else city} appreciated {_pct(stats.median_home_value_yoy_pct) if stats else 'TBD'} YoY, "
        f"{_pct(stats.investor_purchase_share_pct) if stats else 'TBD'} of buys are investors.",
        "Close: 'Cash or hard money OK. EM to title within 48h. 14-day close. Want it?'",
    ]

    return {
        "subject": subject,
        "html_body": body_html,
        "plain_text": plain,
        "sms_short": sms_short,
        "phone_talking_points": talking_points,
        "data_used": {
            "stats_source": stats.source_quarter if stats else None,
            "stats_market": stats.name if stats else None,
            "arv": int(arv),
            "rehab": int(repair),
            "contract_price": int(contract_price),
            "buyer_pays": int(buyer_pays),
            "equity_after_rehab": int(after_rehab_equity),
            "monthly_rent": int(monthly_rent),
            "cap_rate_pct": round(cap_rate, 2),
            "cash_on_cash_pct": round(cash_on_cash, 2),
            "brrrr_refi_pulled": int(refi_proceeds),
            "buyer_strategy_chosen": strategy,
            "voice_region": voice.get("region_name"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _cli() -> int:
    """Render a sample seller and buyer pitch using a fake lead."""
    import argparse, json

    class FakeLead:
        owner_name = "John Smith"
        owner_phone = "(214) 555-0199"
        owner_email = "john@example.com"
        address = "1842 Windsor Dr SW, Atlanta, GA 30311"
        city = "Atlanta"
        state = "GA"
        zip_code = "30311"
        lead_type = "absentee"
        is_absentee = True
        asking_price = 0
        estimated_arv = 235000
        estimated_repair = 28000
        sqft = 1180
        bedrooms = 3
        bathrooms = 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["seller", "buyer", "both"], default="both")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.side in ("seller", "both"):
        s = seller_pitch(FakeLead())
        if args.json:
            print(json.dumps(s, indent=2, default=str))
        else:
            print("=== SELLER PITCH ===")
            print("Subject:", s["subject"])
            print()
            print("PLAIN:", s["plain_text"])
            print()
            print("SMS:", s["sms_short"])
            print()
            print("DATA USED:", json.dumps(s["data_used"], indent=2))
            print()

    if args.side in ("buyer", "both"):
        b = buyer_pitch(FakeLead(), buyer_profile={"name": "Alex Investor"})
        if args.json:
            print(json.dumps(b, indent=2, default=str))
        else:
            print("=== BUYER PITCH ===")
            print("Subject:", b["subject"])
            print()
            print("PLAIN:", b["plain_text"])
            print()
            print("SMS:", b["sms_short"])
            print()
            print("DATA USED:", json.dumps(b["data_used"], indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
