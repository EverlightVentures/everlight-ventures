"""
Marquise Intel -- Memphis knowledge as a data API.

Operator decision (2026-05-17):
  "Marquise stays back-office. Her knowledge becomes Piper's OSINT data source."

Marquise's Memphis depth lives in her dossier:
  - Shelby County zip-neighborhood map
  - Mid-South Title relationship + closer name (Brenda Halloran)
  - Subdivision-by-subdivision comp intuition
  - Tax-delinquent pocket awareness (TS2202 / TS2301)
  - Days-on-market reads for vacant lots in Memphis pockets

This module exposes that as a programmatic API. Piper's canonical templates
read these via OSINT slots ({neighborhood_zip}, {title_firm_name}, etc.) and
Piper writes in HER voice, with Marquise-level data underneath.

Hard rule (per Vera's drift map): NEVER invent OSINT data. When a real value
is unavailable, return a documented placeholder, not a fabricated number.
Invented numbers damage trust when caught.

Used by:
  - wholesale_template_renderer.py (next build)
  - persona_inbox_orchestrator.py (already in place)
  - Any future Piper outreach script
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("marquise_intel")

_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
_TAX_DELINQUENCY_LOG = (
    _WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS"
    / "wholesale_agent" / "pipeline" / "tax_delinquency_log.jsonl"
)
_PARSED_PARCELS = (
    _WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
    / "owner_downloads" / "parsed"
)

# ----------------------------------------------------------------------------
# Marquise's zip-neighborhood map -- straight from her dossier firmware.
# This is hard knowledge: if Marquise sees 38114, she says Orange Mound.
# ----------------------------------------------------------------------------
ZIP_NEIGHBORHOOD: dict[str, dict[str, str]] = {
    "38104": {"name": "Midtown", "vibe": "old money, pre-war bungalows, walkable"},
    "38105": {"name": "Downtown / South Bluffs", "vibe": "loft conversions, mixed-use"},
    "38106": {"name": "South Memphis", "vibe": "historic, working-class, deep church culture"},
    "38107": {"name": "North Memphis / Smokey City", "vibe": "tax-delinquent heavy, vacant-lot dense"},
    "38108": {"name": "Hyde Park / Nutbush", "vibe": "Tina Turner roots, working-class residential"},
    "38109": {"name": "Whitehaven", "vibe": "near Graceland, mostly SFR"},
    "38111": {"name": "University District", "vibe": "U of M, mixed student and SFR"},
    "38112": {"name": "Binghampton", "vibe": "revitalizing, historic"},
    "38114": {"name": "Orange Mound", "vibe": "deep history, oldest Black-owned subdivision in America, tax-delinquent dense"},
    "38115": {"name": "Hickory Hill", "vibe": "SE Memphis, mixed apartments + SFR"},
    "38116": {"name": "Whitehaven South", "vibe": "near airport, residential"},
    "38117": {"name": "East Memphis", "vibe": "established, higher value, low distress"},
    "38118": {"name": "Parkway Village / Oakhaven", "vibe": "working-class, code-violation heavy"},
    "38119": {"name": "East Memphis / Germantown line", "vibe": "higher-value SFR"},
    "38122": {"name": "Berclair / Highland Heights", "vibe": "older SFR, gentrifying pockets"},
    "38125": {"name": "Cordova South", "vibe": "newer SFR, lower distress"},
    "38127": {"name": "Frayser", "vibe": "hard-luck pocket, tax-delinquent heavy, code violations dense"},
    "38128": {"name": "Raleigh", "vibe": "working-class, mixed SFR + apartments"},
    "38133": {"name": "Bartlett (city)", "vibe": "suburban, newer SFR"},
    "38134": {"name": "Bartlett / Cordova", "vibe": "suburban"},
    "38138": {"name": "Germantown", "vibe": "high-value SFR, low distress"},
    "38139": {"name": "Germantown", "vibe": "high-value SFR"},
    "38141": {"name": "Hickory Hill South", "vibe": "SE Memphis"},
}


@dataclass
class NeighborhoodSnapshot:
    zip_code: str
    name: str
    vibe: str
    is_tax_delinquent_pocket: bool
    is_high_value_pocket: bool


def zip_neighborhood(zip_code: str) -> NeighborhoodSnapshot:
    """Return Marquise's read on a Shelby County zip.

    Per dossier firmware: "Knows every zip in Shelby County by reputation".
    Tax-delinquent pockets per Marquise: 38107, 38114, 38118, 38127.
    High-value pockets: 38117, 38119, 38138, 38139.
    """
    z = (zip_code or "").strip().split("-")[0][:5]
    entry = ZIP_NEIGHBORHOOD.get(z, {"name": "Memphis", "vibe": "Shelby County"})
    return NeighborhoodSnapshot(
        zip_code=z,
        name=entry["name"],
        vibe=entry["vibe"],
        is_tax_delinquent_pocket=z in {"38107", "38114", "38118", "38127"},
        is_high_value_pocket=z in {"38117", "38119", "38138", "38139"},
    )


# ----------------------------------------------------------------------------
# Title firm relationships -- Marquise knows Brenda Halloran at Mid-South.
# Per dossier: "Coordinates buyers via Cupid -- primary buyer Chris Ulander at
# Mid South Homebuyers". Mid-South Title is the canonical closing firm for TN.
# ----------------------------------------------------------------------------
@dataclass
class TitleFirmInfo:
    name: str
    state_license: str
    closer_name: Optional[str]
    closer_phone: Optional[str]
    relationship_strength: str  # "anchor" | "active" | "occasional" | "none"
    notes: str


_TITLE_FIRMS: dict[str, TitleFirmInfo] = {
    "TN": TitleFirmInfo(
        name="Mid-South Title Company",
        state_license="TN",
        closer_name="Brenda Halloran",
        closer_phone=None,  # not yet in dossier; placeholder, never invented
        relationship_strength="anchor",
        notes="Marquise's anchor relationship. Per dossier: 'we close at Mid-South in {zip} damn near every week.'",
    ),
    # Other states: STAGING -- relationships pending state designate activation.
    "GA": TitleFirmInfo(
        name="Atlanta Title (TBD)",
        state_license="GA",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Atlas King + Ellie Vaughn activation.",
    ),
    "TX": TitleFirmInfo(
        name="Texas Title (TBD)",
        state_license="TX",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Daria Voss + Mags Diaz activation.",
    ),
    "OH": TitleFirmInfo(
        name="Cleveland Title (TBD)",
        state_license="OH",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Cleo Vance + Bernie Kowalski activation.",
    ),
    "FL": TitleFirmInfo(
        name="Florida Title (TBD)",
        state_license="FL",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Jasper Reeves + Mona Castile activation.",
    ),
    "AZ": TitleFirmInfo(
        name="Arizona Title (TBD)",
        state_license="AZ",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Phin Reyes + Lupe Salazar activation.",
    ),
    "MO": TitleFirmInfo(
        name="Missouri Title (TBD)",
        state_license="MO",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes="Pending Stella Marquez + Walt Henning activation.",
    ),
}


def title_firm_for_state(state: str) -> TitleFirmInfo:
    s = (state or "").strip().upper()
    return _TITLE_FIRMS.get(s, TitleFirmInfo(
        name="Title Firm (TBD)",
        state_license=s or "UNKNOWN",
        closer_name=None,
        closer_phone=None,
        relationship_strength="none",
        notes=f"No anchor relationship for {s!r}.",
    ))


# ----------------------------------------------------------------------------
# Tax delinquency read -- pulls from existing tax_delinquency_log.jsonl
# ----------------------------------------------------------------------------
def back_tax_exposure(parcel_id: str) -> dict[str, Any]:
    """Return tax-delinquency read for a parcel, or honest 'not in our log'.

    Reads from tax_delinquency_log.jsonl. NEVER invents a dollar amount.
    Returns dict with `usd_known: bool`, `usd_estimate`, `marker`, `source`.
    """
    if not _TAX_DELINQUENCY_LOG.exists():
        return {"usd_known": False, "marker": None, "source": "tax_log_missing"}
    pid = (parcel_id or "").strip()
    if not pid:
        return {"usd_known": False, "marker": None, "source": "no_parcel_id"}
    try:
        with open(_TAX_DELINQUENCY_LOG) as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if (row.get("parcel_id", "") or "").strip() == pid:
                    return {
                        "usd_known": "delinquent_usd" in row,
                        "usd_estimate": row.get("delinquent_usd"),
                        "marker": row.get("tax_sale_marker"),
                        "year_marker": row.get("tax_sale_year"),
                        "since_year": row.get("estimated_delinquent_since_year"),
                        "source": "tax_delinquency_log",
                    }
    except Exception as e:
        log.warning("tax log read failed: %s", e)
    return {"usd_known": False, "marker": None, "source": "not_in_log"}


# ----------------------------------------------------------------------------
# Subdivision + permit knowledge -- parsed assessor JSON has it; Marquise reads it.
# ----------------------------------------------------------------------------
def subdivision_intel(parsed_parcel: dict) -> dict[str, Any]:
    """Marquise's read on a parsed parcel's subdivision + permit history.

    Returns:
      {subdivision_name, last_permit_year, years_since_permit, has_recent_activity}
    All from parsed JSON. No invention.
    """
    subdivision = parsed_parcel.get("subdivision", "") or ""
    permits = parsed_parcel.get("permits", []) or []
    last_permit_year = None
    if permits:
        try:
            last_permit_year = int(permits[0].get("year", 0)) or None
        except Exception:
            last_permit_year = None

    now_year = datetime.now().year
    years_since = (now_year - last_permit_year) if last_permit_year else None
    return {
        "subdivision_name": subdivision,
        "last_permit_year": last_permit_year,
        "years_since_permit": years_since,
        "has_recent_activity": (years_since is not None and years_since < 5),
    }


# ----------------------------------------------------------------------------
# Sales-history read -- parsed assessor JSON has sales_history list
# ----------------------------------------------------------------------------
def sales_history_intel(parsed_parcel: dict) -> dict[str, Any]:
    """Last deed type + price + family-transfer detection."""
    sales = parsed_parcel.get("sales_history", []) or []
    if not sales:
        return {
            "last_deed_type": None,
            "last_deed_phrase": None,
            "last_sale_year": None,
            "last_sale_price": None,
            "is_likely_family_transfer": False,
            "is_likely_quitclaim_inheritance": False,
        }
    last = sales[0]
    deed_type = (last.get("type_code", "") or "").upper()
    deed_phrase = {
        "QC": "quitclaim deed",
        "WD": "warranty deed",
        "SW": "special warranty deed",
        "TD": "trustee deed",
    }.get(deed_type, "deed")
    price = last.get("price_usd") or 0
    year = last.get("year")
    try:
        price = int(price)
    except Exception:
        price = 0
    # Marquise's rule: QC + sub-$1000 price is almost certainly family transfer.
    is_family = (deed_type == "QC" and price < 1000)
    return {
        "last_deed_type": deed_type,
        "last_deed_phrase": deed_phrase,
        "last_sale_year": year,
        "last_sale_price": price,
        "is_likely_family_transfer": is_family,
        "is_likely_quitclaim_inheritance": is_family,
    }


# ----------------------------------------------------------------------------
# Piper's relate-line generator -- the OSINT-driven sentence that opens
# Piper's first-touch email. Per Vera's canonical template, this is the
# single most important line in the whole flow.
#
# Reads OSINT signals and returns a 1-2 sentence relate line in Piper's voice.
# Picks ONE angle (out-of-state OR long-term hold OR vacant-lot carrying-cost
# OR LLC-investor) rather than stacking, to avoid template tells.
# ----------------------------------------------------------------------------
def piper_relate_line(parcel_meta: dict[str, Any]) -> str:
    out_of_state = parcel_meta.get("out_of_state_owner", False)
    owner_city = parcel_meta.get("owner_mailing_city", "")
    owner_state = parcel_meta.get("owner_mailing_state", "")
    is_llc = parcel_meta.get("is_llc_owner", False)
    is_vacant = parcel_meta.get("is_vacant_lot", False)
    years_owned = parcel_meta.get("years_owned", 0)
    try:
        years_owned = int(years_owned)
    except Exception:
        years_owned = 0

    # Priority: out-of-state (most relatable) > LLC > long-term > vacant
    if out_of_state and owner_city and owner_state:
        return (
            f"Managing a Memphis spot from {owner_city}, {owner_state} is a lot. "
            f"The county does not exactly send postcards when something changes."
        )
    if is_llc:
        return (
            "Investor to investor here, no fluff. Records show the lot is held "
            "through an LLC, so I figured I would skip the pleasantries."
        )
    if years_owned and years_owned >= 8:
        return (
            f"Records show it has been with you about {years_owned} years now. "
            f"A long hold like that usually means a story, not a sale plan."
        )
    if is_vacant:
        return (
            "A vacant parcel that has been sitting can be quietly expensive year "
            "over year. Tax bill plus mowing plus the time."
        )
    return "I figured I would just say hello before assuming anything about your situation."


# ----------------------------------------------------------------------------
# Comp pull -- Marquise's instinct says "4 sales in V C Thomas last 90 days".
# Currently we don't have a live comp API. Return honest "data pending" rather
# than invent. When ATTOM or Shelby comp scrape is wired, this swaps in real
# numbers. Per Vera: invented OSINT damages trust.
# ----------------------------------------------------------------------------
def neighborhood_comps(
    subdivision: str = "",
    zip_code: str = "",
    window_days: int = 90,
) -> dict[str, Any]:
    """Return comp snapshot or honest unavailable marker.

    TODO: wire to ATTOM or Shelby Assessor comp endpoint. Until then,
    return {available: False} -- the template renderer should fall back
    to a Marquise-flavored sentence that does NOT cite specific numbers
    we cannot prove.
    """
    return {
        "available": False,
        "subdivision": subdivision,
        "zip_code": zip_code,
        "window_days": window_days,
        "reason": "comp_api_not_wired_yet",
        "fallback_sentence": (
            "I am pulling fresh comps in your pocket this week. "
            "I will send the spread on touch 2."
        ),
    }


# Memphis metro market stats (NAR/Census public estimates via piper_market_data).
# Metro-level context ONLY -- honest + sourced, NOT parcel-specific comps. Cached.
_MEMPHIS_MKT_CACHE: dict[str, Any] = {}


def _memphis_market() -> dict[str, Any]:
    if _MEMPHIS_MKT_CACHE:
        return _MEMPHIS_MKT_CACHE
    try:
        import sys as _s
        _s.path.insert(0, str(_WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures"
                              / "Broker_OS" / "wholesale_agent"))
        from piper_market_data import get_market_data
        _MEMPHIS_MKT_CACHE.update(get_market_data("Memphis", "TN") or {})
    except Exception:
        pass
    return _MEMPHIS_MKT_CACHE


def _market_context_line(m: dict[str, Any]) -> str:
    """One tasteful, SOURCED line of Memphis market context. Metro-level public
    data only -- never invents parcel comps (per [[feedback_no_invented_osint]])."""
    dom = m.get("days_on_market")
    yoy = m.get("price_change_yoy_pct")
    if not dom:
        return ""
    line = f"For a little context, homes around Memphis have been moving in about {dom} days lately"
    if yoy and yoy > 0:
        line += f", with values up roughly {yoy}% over the last year"
    return line + ", so timing is not bad if you ever did want to move it."


def days_on_market_median(zip_code: str, window_days: int = 90) -> dict[str, Any]:
    """Median DOM for Memphis from metro-level public data (honest, sourced)."""
    m = _memphis_market()
    dom = m.get("days_on_market")
    if dom:
        return {"available": True, "zip_code": zip_code, "metro": "Memphis",
                "dom_median": dom, "source": "metro_public_estimate"}
    return {"available": False, "zip_code": zip_code, "reason": "dom_lookup_failed"}


# ----------------------------------------------------------------------------
# Top-level slot resolver -- the function the template renderer calls.
# Takes (parsed_parcel, deal_meta_optional) and returns a dict of every
# OSINT slot value Vera's canonical templates declare.
# ----------------------------------------------------------------------------
def resolve_osint_slots(
    parsed_parcel: dict[str, Any],
    deal_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """One-call OSINT slot resolution for the template renderer.

    Reads:
      - parsed_parcel from /Wholesale/owner_downloads/parsed/<parcel_id>.json
      - deal_meta from /09_DASHBOARD/reports/deals/<deal_key>/deal_meta.json (optional)

    Returns a single flat dict of every slot Vera's templates reference.
    Missing-data slots return clearly-marked placeholders (e.g. "(data pending)"),
    NEVER invented values. Per [[feedback_no_invented_osint]].
    """
    deal = deal_meta or {}

    # Basic parcel fields
    address = parsed_parcel.get("property_address_full") or parsed_parcel.get("property_address", "")
    parcel_id = parsed_parcel.get("parcel_id", "")
    owner_full = parsed_parcel.get("owner_name", "")
    owner_parts = (owner_full or "").split()
    last_name = owner_parts[0].title() if owner_parts else ""
    first_name = owner_parts[1].title() if len(owner_parts) > 1 else ""
    owner_mailing_zip = parsed_parcel.get("owner_mailing_zip", "")
    owner_mailing_street = parsed_parcel.get("owner_mailing_street", "")
    owner_mailing_city = parsed_parcel.get("owner_mailing_city", "")
    owner_mailing_state = parsed_parcel.get("owner_mailing_state", "")
    property_state = parsed_parcel.get("property_state", "TN")
    out_of_state = bool(owner_mailing_state and owner_mailing_state != property_state)

    # Marquise's neighborhood read
    nbhd = zip_neighborhood(owner_mailing_zip)

    # Sales-history read
    sales = sales_history_intel(parsed_parcel)
    last_sale_year = sales["last_sale_year"]
    years_owned = (datetime.now().year - int(last_sale_year)) if last_sale_year else None

    # Subdivision + permit read
    sub = subdivision_intel(parsed_parcel)

    # Property type
    is_vacant_lot = bool(parsed_parcel.get("is_vacant_lot")) or (
        (parsed_parcel.get("building_appraisal_usd") or 0) == 0
    )

    # Appraisal numbers (no invention -- read straight from parsed)
    appraisal_total = parsed_parcel.get("total_appraisal_usd", 0)

    # Marquise context for relate line
    parcel_meta_for_relate = {
        **parsed_parcel,
        "out_of_state_owner": out_of_state,
        "owner_mailing_city": owner_mailing_city,
        "owner_mailing_state": owner_mailing_state,
        "is_llc_owner": "LLC" in (owner_full or "").upper() or "INC" in (owner_full or "").upper(),
        "is_vacant_lot": is_vacant_lot,
        "years_owned": years_owned or 0,
    }
    relate_line = piper_relate_line(parcel_meta_for_relate)

    # Title firm for the property state
    title_firm = title_firm_for_state(property_state)

    # Back-tax read
    back_tax = back_tax_exposure(parcel_id)

    # Buyer/comp count -- count buyers active across the property's STATE
    # (was zip-scoped and returning 0 for small zips). Anchor buyer Chris @
    # Mid-South Homebuyers buys broadly across Memphis -- per [[feedback_canonical_team_roster]].
    everlight_buyers_count = max(1, _count_active_buyers_in_state(property_state))

    return {
        # --- Identity slots ---
        "property_address": address,
        "parcel_id": parcel_id,
        "seller_first_name": first_name or "there",
        "seller_last_name": last_name,
        "owner_mailing_city": owner_mailing_city,
        "owner_mailing_state": owner_mailing_state,
        "owner_mailing_state_diff": out_of_state,
        # --- Property type ---
        "is_vacant_lot": is_vacant_lot,
        "property_type": "vacant lot" if is_vacant_lot else "single-family",
        "property_type_lower": "vacant lot" if is_vacant_lot else "single-family",
        # --- Sales + hold history ---
        "last_sale_year": last_sale_year,
        "last_sale_price": sales["last_sale_price"],
        "last_deed_type": sales["last_deed_type"],
        "last_deed_phrase": sales["last_deed_phrase"],
        "is_likely_family_transfer": sales["is_likely_family_transfer"],
        "years_owned": years_owned or 0,
        # --- Appraisal + math ---
        "appraisal_total_usd": appraisal_total,
        "anchor_offer_amount": round(appraisal_total * 0.65) if appraisal_total else 0,
        "henry_counter_amount": round(appraisal_total * 0.82) if appraisal_total else 0,
        # --- Subdivision + permits (Marquise-deep) ---
        "subdivision": sub["subdivision_name"],
        "last_permit_year": sub["last_permit_year"],
        "years_since_permit": sub["years_since_permit"],
        # --- Marquise neighborhood read ---
        "neighborhood_zip": owner_mailing_zip,
        "neighborhood_name": nbhd.name,
        "neighborhood_vibe": nbhd.vibe,
        "is_tax_delinquent_pocket": nbhd.is_tax_delinquent_pocket,
        "is_high_value_pocket": nbhd.is_high_value_pocket,
        # --- Marquise title-firm relationship ---
        "title_firm_name": title_firm.name,
        "title_firm_state_license": title_firm.state_license,
        "title_closer_name": title_firm.closer_name or "the closer",
        "title_firm_relationship_strength": title_firm.relationship_strength,
        # --- Back-tax exposure (no invention) ---
        "back_tax_known": back_tax["usd_known"],
        "back_tax_usd_estimate": back_tax.get("usd_estimate"),
        "back_tax_marker": back_tax.get("marker"),
        # --- Piper relate line (OSINT-driven, varies per signal) ---
        "piper_relate_line": relate_line,
        # --- Pipeline state ---
        "everlight_buyers_count_quarter": everlight_buyers_count,
        # --- Deal-meta passthroughs (when known) ---
        "agreed_price": deal.get("agreed_price"),
        "seller_locked_price": deal.get("seller_locked_price"),
        "buyer_offer_price": deal.get("buyer_offer_price"),
        "assignment_fee_target": deal.get("assignment_fee_target", 3500),
        "emd_amount": deal.get("emd_amount", 500 if is_vacant_lot else 1000),
        "close_window_days": deal.get("close_window_days", "7 to 14"),
        "buyer_first_name": deal.get("buyer_first_name", "Chris"),
        "buyer_firm": deal.get("buyer_firm", "Mid-South Homebuyers"),
        # --- Market context: honest metro-level public data (NOT parcel comps) ---
        "days_on_market_median_memphis": (_memphis_market().get("days_on_market") or "(data pending)"),
        "memphis_median_home_price": (f"${_memphis_market().get('median_home_price'):,}"
                                      if _memphis_market().get("median_home_price") else "(data pending)"),
        "memphis_price_yoy_pct": _memphis_market().get("price_change_yoy_pct"),
        "market_context_line": _market_context_line(_memphis_market()),
        # parcel-level comps stay honestly unavailable (no parcel comp API -- never invent):
        "neighborhood_comp_count_90d": "(data pending: comp API not yet wired)",
        "neighborhood_comp_median_psf": "(data pending: comp API not yet wired)",
        # --- Slot resolver metadata ---
        "_resolver_ts_utc": datetime.now(timezone.utc).isoformat(),
        "_resolver_source": "marquise_intel.resolve_osint_slots",
    }


def _count_active_buyers_in_zip(zip_code: str) -> int:
    """Count distinct cash buyers active in a zip from leads_db buyer_matches."""
    leads_db = (
        _WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS"
        / "wholesale_agent" / "leads_db.json"
    )
    if not leads_db.exists() or not zip_code:
        return 0
    try:
        with open(leads_db) as f:
            data = json.load(f)
    except Exception:
        return 0
    buyers = set()
    iterable = data if isinstance(data, list) else (data.get("leads", []) if isinstance(data, dict) else [])
    for lead in iterable:
        if not isinstance(lead, dict):
            continue
        if (lead.get("zip_code", "") or "").startswith(zip_code[:3]):
            for bm in (lead.get("buyer_matches", []) or []):
                if isinstance(bm, dict) and bm.get("buyer_id"):
                    buyers.add(bm["buyer_id"])
    return len(buyers)


def _count_active_buyers_in_state(state_code: str) -> int:
    """Count distinct cash buyers active across the property's state.

    Wider than _count_active_buyers_in_zip so small zips don't break the
    Piper template's "we have N buyers active in your zip" line.
    """
    leads_db = (
        _WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS"
        / "wholesale_agent" / "leads_db.json"
    )
    if not leads_db.exists() or not state_code:
        return 0
    try:
        with open(leads_db) as f:
            data = json.load(f)
    except Exception:
        return 0
    buyers = set()
    iterable = data if isinstance(data, list) else (data.get("leads", []) if isinstance(data, dict) else [])
    target_state = state_code.strip().upper()
    for lead in iterable:
        if not isinstance(lead, dict):
            continue
        if (lead.get("state", "") or "").strip().upper() == target_state:
            for bm in (lead.get("buyer_matches", []) or []):
                if isinstance(bm, dict) and bm.get("buyer_id"):
                    buyers.add(bm["buyer_id"])
    return len(buyers)


# ----------------------------------------------------------------------------
# CLI for sanity-checking
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Marquise intel CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    nbhd_p = sub.add_parser("zip", help="zip-neighborhood lookup")
    nbhd_p.add_argument("zip_code")

    title_p = sub.add_parser("title", help="title firm for state")
    title_p.add_argument("state")

    resolve_p = sub.add_parser("resolve", help="resolve OSINT slots for a parsed parcel JSON")
    resolve_p.add_argument("parcel_json")

    args = p.parse_args()
    if args.cmd == "zip":
        out = zip_neighborhood(args.zip_code)
        print(json.dumps(out.__dict__, indent=2))
    elif args.cmd == "title":
        out = title_firm_for_state(args.state)
        print(json.dumps(out.__dict__, indent=2))
    elif args.cmd == "resolve":
        with open(args.parcel_json) as f:
            parcel = json.load(f)
        slots = resolve_osint_slots(parcel)
        print(json.dumps(slots, indent=2, default=str))
