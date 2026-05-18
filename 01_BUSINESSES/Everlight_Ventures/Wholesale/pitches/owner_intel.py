"""owner_intel -- read every signal we have about the owner.

Each pitch personalizes around three axes: who the owner is, what their
likely pain looks like, and how motivated they probably are. This module
infers as much as we can from the public data already in PropertyLead.

What we infer (legally + transparently)
---------------------------------------
  - Absentee status (out-of-state phone area code on owner_phone)
  - Approximate distance from property (state-of-phone vs state-of-property)
  - Likely age cohort (very rough, based on first-name decade-popularity)
  - Years owned (if `last_sale_date` exists)
  - Equity tier (asking_price vs estimated_arv)
  - Motivation tier 1-5 (composite score)
  - Best language register (formal, neighborly, urgent, professional)

We do NOT infer race, religion, marital status, family size, or anything
covered by Fair Housing protected classes. Our pitches address the property
and the financial situation, never the person.

Public API
----------
    from owner_intel import build_owner_intel

    intel = build_owner_intel(lead)
    # -> {
    #     "first_name": "Linda",
    #     "is_likely_absentee": True,
    #     "owner_distance_miles_est": 1100,
    #     "likely_age_cohort": "55-70",
    #     "motivation_tier": 4,  # 1=cold to 5=hot
    #     "register": "neighborly",
    #     "primary_pain_hook": "absentee_carry",
    #     "second_pain_hook": "vacancy",
    #     ...
    # }
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


# ── Area code -> state distance ────────────────────────────────

# Compact mapping of major area codes to state for distance estimation.
# Not exhaustive but covers the common ones we see in property leads.
AC_TO_STATE = {
    # GA
    "404":"GA","470":"GA","678":"GA","770":"GA","762":"GA",
    # FL
    "305":"FL","321":"FL","352":"FL","386":"FL","407":"FL","561":"FL","727":"FL",
    "754":"FL","772":"FL","786":"FL","813":"FL","850":"FL","863":"FL","904":"FL",
    "941":"FL","954":"FL",
    # TX
    "210":"TX","214":"TX","254":"TX","281":"TX","325":"TX","346":"TX","361":"TX",
    "409":"TX","430":"TX","432":"TX","469":"TX","512":"TX","682":"TX","713":"TX",
    "726":"TX","737":"TX","806":"TX","817":"TX","830":"TX","832":"TX","903":"TX",
    "915":"TX","936":"TX","940":"TX","956":"TX","972":"TX","979":"TX",
    # AZ
    "480":"AZ","520":"AZ","602":"AZ","623":"AZ","928":"AZ",
    # CA
    "209":"CA","213":"CA","279":"CA","310":"CA","323":"CA","341":"CA","408":"CA",
    "415":"CA","424":"CA","442":"CA","510":"CA","530":"CA","559":"CA","562":"CA",
    "619":"CA","626":"CA","628":"CA","650":"CA","657":"CA","661":"CA","669":"CA",
    "707":"CA","714":"CA","747":"CA","760":"CA","805":"CA","818":"CA","820":"CA",
    "831":"CA","840":"CA","858":"CA","909":"CA","916":"CA","925":"CA","949":"CA",
    "951":"CA",
    # MO
    "314":"MO","417":"MO","573":"MO","636":"MO","660":"MO","816":"MO","975":"MO",
    # NC
    "252":"NC","336":"NC","472":"NC","704":"NC","743":"NC","828":"NC","910":"NC",
    "919":"NC","980":"NC","984":"NC",
    # TN
    "423":"TN","615":"TN","629":"TN","731":"TN","865":"TN","901":"TN","931":"TN",
    # NY
    "212":"NY","315":"NY","332":"NY","347":"NY","363":"NY","516":"NY","518":"NY",
    "585":"NY","607":"NY","631":"NY","646":"NY","680":"NY","716":"NY","718":"NY",
    "838":"NY","845":"NY","914":"NY","917":"NY","929":"NY","934":"NY",
    # IL
    "217":"IL","224":"IL","309":"IL","312":"IL","331":"IL","447":"IL","464":"IL",
    "618":"IL","630":"IL","708":"IL","730":"IL","773":"IL","779":"IL","815":"IL",
    "847":"IL","861":"IL","872":"IL",
    # MI
    "231":"MI","248":"MI","269":"MI","313":"MI","517":"MI","586":"MI","616":"MI",
    "679":"MI","734":"MI","810":"MI","906":"MI","947":"MI","989":"MI",
    # OH
    "216":"OH","220":"OH","234":"OH","283":"OH","326":"OH","330":"OH","380":"OH",
    "419":"OH","436":"OH","440":"OH","513":"OH","567":"OH","614":"OH","740":"OH",
    "937":"OH",
    # DE / NJ / VA / PA
    "302":"DE","201":"NJ","551":"NJ","609":"NJ","640":"NJ","732":"NJ","848":"NJ",
    "856":"NJ","862":"NJ","908":"NJ","973":"NJ",
    "276":"VA","434":"VA","540":"VA","571":"VA","686":"VA","703":"VA","757":"VA","804":"VA","826":"VA","948":"VA",
    "215":"PA","223":"PA","267":"PA","272":"PA","412":"PA","445":"PA","484":"PA",
    "570":"PA","582":"PA","610":"PA","717":"PA","724":"PA","814":"PA","835":"PA","878":"PA",
    # AL / SC / IN
    "205":"AL","251":"AL","256":"AL","334":"AL","483":"AL","659":"AL","938":"AL",
    "803":"SC","839":"SC","843":"SC","854":"SC","864":"SC",
    "219":"IN","260":"IN","317":"IN","463":"IN","574":"IN","765":"IN","812":"IN","930":"IN",
}

# State centroid coords (lat, lon) for distance estimation.
STATE_CENTROIDS = {
    "AL":(32.806671,-86.791130),"AZ":(34.048928,-111.093731),"AR":(34.969704,-92.373123),
    "CA":(36.116203,-119.681564),"CO":(39.059811,-105.311104),"CT":(41.597782,-72.755371),
    "DE":(39.318523,-75.507141),"FL":(27.766279,-81.686783),"GA":(33.040619,-83.643074),
    "ID":(44.240459,-114.478828),"IL":(40.349457,-88.986137),"IN":(39.849426,-86.258278),
    "IA":(42.011539,-93.210526),"KS":(38.526600,-96.726486),"KY":(37.668140,-84.670067),
    "LA":(31.169546,-91.867805),"ME":(44.693947,-69.381927),"MD":(39.063946,-76.802101),
    "MA":(42.230171,-71.530106),"MI":(43.326618,-84.536095),"MN":(45.694454,-93.900192),
    "MS":(32.741646,-89.678696),"MO":(38.456085,-92.288368),"MT":(46.921925,-110.454353),
    "NE":(41.125370,-98.268082),"NV":(38.313515,-117.055374),"NH":(43.452492,-71.563896),
    "NJ":(40.298904,-74.521011),"NM":(34.840515,-106.248482),"NY":(42.165726,-74.948051),
    "NC":(35.630066,-79.806419),"ND":(47.528912,-99.784012),"OH":(40.388783,-82.764915),
    "OK":(35.565342,-96.928917),"OR":(44.572021,-122.070938),"PA":(40.590752,-77.209755),
    "RI":(41.680893,-71.511780),"SC":(33.856892,-80.945007),"SD":(44.299782,-99.438828),
    "TN":(35.747845,-86.692345),"TX":(31.054487,-97.563461),"UT":(40.150032,-111.862434),
    "VT":(44.045876,-72.710686),"VA":(37.769337,-78.169968),"WA":(47.400902,-121.490494),
    "WV":(38.491226,-80.954453),"WI":(44.268543,-89.616508),"WY":(42.755966,-107.302490),
    "DC":(38.897438,-77.026817),
}


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    import math
    r = 3959.0  # earth radius in miles
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p)
         * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 2 * r * math.asin(math.sqrt(a))


# ── Name -> rough age cohort (US Social Security data, generalized) ──

# First names that peaked in popularity in specific decades. Coarse but
# useful for picking "Mr." vs first-name register, and pacing of language.
NAMES_PRE_1960 = {
    "robert","james","john","william","richard","david","charles","thomas","ronald",
    "donald","george","frank","kenneth","paul","gerald","walter","harold","arthur",
    "albert","jerry","gary","carl","henry","ralph","roy","eugene","raymond","russell",
    "wayne","clarence","billy","fred","stanley","leroy","francis","joe","melvin","earl",
    "leo","glenn","floyd","alvin","leon","clyde","oscar","milton","willard","calvin",
    "norman","leonard","virgil","wilbur","ernest","edward","theodore","stephen","sherman",
    "linda","mary","barbara","patricia","carol","sandra","sharon","betty","margaret",
    "nancy","helen","dorothy","ruth","elizabeth","janet","janice","jean","gloria","kathleen",
    "ann","virginia","beverly","peggy","frances","martha","sandra","joyce","judith","carolyn",
    "alice","marie","doris","evelyn","mildred","anita",
}
NAMES_60S_70S = {
    "michael","christopher","kevin","brian","scott","steven","timothy","jason","jeffrey",
    "matthew","jeremy","todd","gregory","douglas","craig","tony","aaron","keith","randy",
    "lisa","kimberly","susan","cynthia","cindy","debra","deborah","laura","julie","diane",
    "donna","brenda","cheryl","theresa","tracy","stacy","jennifer","tammy","lori","amy",
}
NAMES_80S_90S = {
    "joshua","tyler","brandon","austin","cody","cole","jordan","dylan","caleb","ryan",
    "ashley","amanda","sarah","stephanie","megan","heather","melissa","jessica","emily",
    "christine","nicole","rebecca","jennifer","kayla","crystal","tiffany","brittany",
}
NAMES_2000S_PLUS = {
    "jacob","ethan","aiden","liam","mason","noah","jackson","oliver","logan","elijah",
    "olivia","emma","ava","sophia","isabella","mia","charlotte","amelia","harper","aria",
}


def _likely_age_cohort(first: str) -> str:
    f = (first or "").lower().strip()
    if not f:
        return "unknown"
    if f in NAMES_PRE_1960:
        return "55-80"
    if f in NAMES_60S_70S:
        return "45-65"
    if f in NAMES_80S_90S:
        return "30-45"
    if f in NAMES_2000S_PLUS:
        return "18-30"
    return "unknown"


def _pick_register(age_cohort: str, is_absentee: bool, lead_type: str) -> str:
    """Choose tone: formal, neighborly, urgent, professional."""
    if lead_type in ("pre_foreclosure", "tax_lien"):
        return "urgent"  # they need a real solution
    if age_cohort in ("55-80",):
        return "formal"  # older audience prefers respectful tone
    if is_absentee:
        return "professional"  # business-like, time-respecting
    return "neighborly"  # default warm


def _motivation_tier(lead: Any, is_absentee: bool) -> int:
    """Composite motivation score 1-5 (cold to hot). Augmented with cached OSINT signals."""
    score = 0
    lt = (getattr(lead, "lead_type", "") or "").lower()
    if lt in ("pre_foreclosure", "tax_lien"):
        score += 2
    if lt in ("divorce", "probate", "code_violation"):
        score += 2
    if lt == "vacant" or "vacant" in lt:
        score += 1
    if is_absentee:
        score += 1
    repair = float(getattr(lead, "estimated_repair", 0) or 0)
    if repair > 25000:
        score += 1
    days_on_market = int(getattr(lead, "days_on_market", 0) or 0)
    if days_on_market > 90:
        score += 1
    if int(getattr(lead, "motivation_score", 0) or 0) >= 50:
        score += 1
    # OSINT signal augmentation -- if we have a cached VERIFIED investigation with red flags
    # (bankruptcy, lawsuit, multi-property exposure), bump the tier.
    # DNC always wins: dnc_blocked records contribute ZERO motivation bumps; downstream
    # consumers must refuse to draft outreach anyway.
    osint = fetch_cached_investigation(getattr(lead, "owner_name", "") or "")
    if osint and not osint.get("dnc_blocked"):
        # Use ONLY verified findings (confidence >= threshold). Raw is stored
        # for transparency but never feeds motivation_tier.
        verified = osint.get("verified", {}) or osint
        red = len(verified.get("red_flags", []))
        if red >= 3:
            score += 2
        elif red >= 1:
            score += 1
        if len(verified.get("properties_owned", [])) >= 2:
            score += 1
    return min(5, max(1, score))


def fetch_cached_investigation(owner_name: str) -> Optional[dict]:
    """
    Look up the latest cached OSINT investigation for an owner.

    PREFERRED: read the lead's `intel_enrichment_json` column (already has the
    verifier-scored verified/raw blocks + DNC flag).
    FALLBACK: pull from 06_DEVELOPMENT/everlight_os/intel_center/cache/investigations.sqlite
    (unscored -- only useful for back-compat; doesn't include verification).

    Lazy import + best-effort -- never raises into the caller.
    """
    if not owner_name or not owner_name.strip():
        return None

    # --- Preferred path: leads_db.sqlite intel_enrichment_json ---
    try:
        import json as _json
        import sqlite3 as _sql
        from pathlib import Path as _P
        leads_db = _P("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/leads_db.sqlite")
        if leads_db.exists():
            con = _sql.connect(leads_db)
            try:
                row = con.execute(
                    "SELECT intel_enrichment_json FROM leads "
                    "WHERE LOWER(owner_name)=LOWER(?) AND intel_enrichment_json IS NOT NULL "
                    "ORDER BY id DESC LIMIT 1",
                    (owner_name.strip(),)
                ).fetchone()
            except _sql.OperationalError:
                row = None
            con.close()
            if row and row[0]:
                try:
                    return _json.loads(row[0])
                except _json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # --- Fallback: raw investigations cache (no verification scores) ---
    try:
        import json as _json
        import sqlite3 as _sql
        from pathlib import Path as _P
        db = _P("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/investigations.sqlite")
        if not db.exists():
            return None
        con = _sql.connect(db)
        row = con.execute(
            "SELECT file_path FROM investigations WHERE LOWER(target)=LOWER(?) "
            "ORDER BY started_at DESC LIMIT 1",
            (owner_name.strip(),)
        ).fetchone()
        con.close()
        if not row:
            return None
        path = _P(row[0])
        if not path.exists():
            return None
        full = _json.loads(path.read_text())
        red_flags = []; properties = []; social = []; breaches = []
        for inv in full.get("results", []):
            iid = inv.get("investigator_id", "")
            for f in inv.get("findings", []):
                label = (f.get("label") or "").lower()
                if iid == "social_recon" and label.startswith("✓"):
                    social.append(f)
                elif iid == "leak_check" and "breach" in label:
                    breaches.append(f)
                elif iid == "property_records":
                    properties.append(f)
                elif iid in ("opencorporates", "sec_edgar"):
                    red_flags.append(f)
        return {
            "investigation_id": full.get("investigation_id"),
            "raw": {
                "social_profiles_found": social,
                "breach_flags": breaches,
                "properties_owned": properties,
                "red_flags": red_flags,
            },
            "verified": {  # fallback path = unverified; treat conservatively
                "social_profiles_found": [],
                "breach_flags": [],
                "properties_owned": [],
                "red_flags": [],
            },
            "verification_summary": {
                "verified": 0,
                "total_findings": sum(map(len, [social, breaches, properties, red_flags])),
                "note": "no_lead_context_available_fallback",
            },
            "dnc_blocked": False,
        }
    except Exception:
        return None


def _phone_state(phone: str) -> Optional[str]:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) >= 10:
        ac = digits[-10:][:3]
        return AC_TO_STATE.get(ac)
    return None


@dataclass
class OwnerIntel:
    full_name: str
    first_name: str
    last_name: str
    phone: str
    phone_state: Optional[str]
    property_state: Optional[str]
    is_likely_absentee: bool
    owner_distance_miles_est: Optional[int]
    likely_age_cohort: str
    motivation_tier: int
    register: str
    primary_pain_hook: str
    second_pain_hook: Optional[str]
    notes: list[str]


def build_owner_intel(lead: Any) -> OwnerIntel:
    full = (getattr(lead, "owner_name", "") or "").strip()
    parts = full.split()
    if len(parts) >= 2 and "," in full:
        # "LAST, FIRST" pattern
        last, first = full.split(",", 1)
        first = first.strip().split()[0] if first.strip() else ""
        last = last.strip()
    else:
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""

    phone = (getattr(lead, "owner_phone", "") or "").strip()
    p_state = _phone_state(phone)
    prop_state = (getattr(lead, "state", "") or "").upper().strip() or None

    is_absentee = bool(
        getattr(lead, "is_absentee", False)
        or (p_state and prop_state and p_state != prop_state)
    )

    distance = None
    if p_state and prop_state and p_state != prop_state:
        c1 = STATE_CENTROIDS.get(p_state)
        c2 = STATE_CENTROIDS.get(prop_state)
        if c1 and c2:
            distance = int(_haversine_miles(c1[0], c1[1], c2[0], c2[1]))

    age_cohort = _likely_age_cohort(first)
    lt = (getattr(lead, "lead_type", "") or "").lower()
    register = _pick_register(age_cohort, is_absentee, lt)
    motivation = _motivation_tier(lead, is_absentee)

    # Primary + secondary pain hooks
    pain_order: list[str] = []
    if lt == "pre_foreclosure":
        pain_order.append("preforeclosure")
    if lt == "tax_lien":
        pain_order.append("tax_lien")
    if lt in ("divorce", "probate"):
        pain_order.append("life_event")
    if is_absentee:
        pain_order.append("absentee_carry")
    if lt == "vacant" or "vacant" in lt:
        pain_order.append("vacancy")
    if lt == "code_violation":
        pain_order.append("code_violation")
    if float(getattr(lead, "estimated_repair", 0) or 0) > 15000:
        pain_order.append("repair_burden")
    if not pain_order:
        pain_order = ["retail_friction"]

    notes: list[str] = []
    if is_absentee and distance and distance > 500:
        notes.append(f"Owner is ~{distance} miles from the property")
    if age_cohort != "unknown":
        notes.append(f"Likely age cohort {age_cohort} based on first name")
    if motivation >= 4:
        notes.append(f"High motivation tier ({motivation}/5)")
    elif motivation <= 2:
        notes.append(f"Cold (tier {motivation}/5) -- expect lower reply rate")

    return OwnerIntel(
        full_name=full,
        first_name=first.title(),
        last_name=last.title(),
        phone=phone,
        phone_state=p_state,
        property_state=prop_state,
        is_likely_absentee=is_absentee,
        owner_distance_miles_est=distance,
        likely_age_cohort=age_cohort,
        motivation_tier=motivation,
        register=register,
        primary_pain_hook=pain_order[0],
        second_pain_hook=pain_order[1] if len(pain_order) > 1 else None,
        notes=notes,
    )


def _cli() -> int:
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="LINDA J HARRIS")
    ap.add_argument("--phone", default="(214) 555-0199")
    ap.add_argument("--state", default="GA")
    ap.add_argument("--lead-type", default="absentee")
    ap.add_argument("--repair", type=float, default=22000.0)
    args = ap.parse_args()

    class Lead:
        owner_name = args.name
        owner_phone = args.phone
        state = args.state
        lead_type = args.lead_type
        is_absentee = False
        estimated_repair = args.repair
        days_on_market = 0
        motivation_score = 0

    print(json.dumps(asdict(build_owner_intel(Lead())), indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
