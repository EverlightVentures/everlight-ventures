"""
seller_intel_deepdive.py -- legal, free, open-source intel deepdive on a single seller.

Purpose: Hammer + Piper write a TAILORED first-contact for each seller, not a
form letter. The free-tier intel cascade pulls public-record signals (probate,
deeds, court filings, obit, public social, prior addresses) into a one-page
profile + pitch hooks.

Sources tier:
  AUTO        -- runs from terminal via WebSearch / WebFetch
  BROWSER     -- requires JS-rendered page; output URL list for MHTML drop
  PAID_SKIP   -- excluded by free-path-only rule

Usage:
  python3 seller_intel_deepdive.py --parcel "024057  00012"
  python3 seller_intel_deepdive.py --owner "HOWARD EDDIE" --mailing "1919 JAMAR 230, SAN ANTONIO TX 78226"

Output:
  seller_intel/{parcel_safe}/intel.md          -- human-readable summary
  seller_intel/{parcel_safe}/intel.json        -- structured signals
  seller_intel/{parcel_safe}/browser_queue.md  -- URLs to MHTML manually
  seller_intel/{parcel_safe}/pitch_draft.md    -- proposed first-contact copy

Privacy / legal guardrails (do NOT remove):
  - Public records ONLY (no GLBA-protected financial, no DPPA-protected DMV,
    no HIPAA, no sealed records).
  - No protected-class profiling (race, religion, age, family-status,
    disability, national origin, sex, sexual orientation).
  - Pitch hooks reference SITUATIONAL signals (out-of-state, estate status,
    long ownership, code enforcement) NOT identity attributes.
  - All sourced facts cite their public origin.
  - Output is internal-use; never reproduced verbatim to seller.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
INTEL_ROOT = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel"
INTEL_ROOT.mkdir(parents=True, exist_ok=True)


def lookup_by_parcel(parcel_id: str) -> dict | None:
    if not LEADS_DB.exists():
        return None
    leads = json.loads(LEADS_DB.read_text())
    target = parcel_id.strip()
    for l in leads:
        if (l.get("parcel_id") or "").strip() == target:
            return l
    return None


def detect_signals(lead: dict) -> dict:
    """Pull situational signals from the lead record. These shape pitch hook selection."""
    signals = {
        "is_estate": False,
        "estate_decedent_name": None,
        "is_absentee_outofstate": False,
        "is_absentee_instate": False,
        "owner_mailing_apartment": False,
        "is_llc_owner": False,
        "is_religious_org_owner": False,
        "is_long_term_owner": False,
        "ownership_years": None,
        "is_high_value": False,
        "is_vacant_lot": bool(lead.get("is_vacant_lot")),
        "tax_delinquent_years": None,
        "multiple_sales_in_history": False,
    }
    owner = (lead.get("owner_name") or "").upper()
    if "ESTATE OF" in owner or owner.endswith(" ESTATE"):
        signals["is_estate"] = True
        # Memphis assessor format is "LASTNAME FIRSTNAME (ESTATE OF)"
        m = re.match(r"^([A-Z &']+?)\s*\(\s*ESTATE OF\s*\)", owner)
        if m:
            signals["estate_decedent_name"] = m.group(1).strip()
    if "LLC" in owner or " INC" in owner or " CORP" in owner:
        signals["is_llc_owner"] = True
    if any(t in owner for t in [" CHURCH", " MINISTRIES", " MINISTRY", " TEMPLE", " MOSQUE"]):
        signals["is_religious_org_owner"] = True

    mz = lead.get("owner_mailing_zip") or ""
    mc = (lead.get("owner_mailing_city") or "").upper()
    mailing_st = (lead.get("owner_mailing_street") or "").upper()
    if mz and not mz.startswith("381") and not mz.startswith("38"):  # 38 = TN, 381xx = Memphis core
        signals["is_absentee_outofstate"] = True
    elif mz and mz.startswith("38") and not mz.startswith("381"):
        signals["is_absentee_instate"] = True  # TN but not Memphis (e.g., Cordova 38016, Collierville 38017)

    # Apartment / unit detection in mailing address
    if re.search(r"#\s*\d+|APT|UNIT|\s\d{3,4}\s*$", mailing_st):
        signals["owner_mailing_apartment"] = True

    # Sales-history derived signals
    sh = lead.get("sales_history") or []
    if len(sh) >= 5:
        signals["multiple_sales_in_history"] = True
    if sh:
        first_year = lead.get("first_sale_year")
        last_year = lead.get("last_sale_year")
        if first_year:
            signals["ownership_years"] = datetime.now().year - last_year if last_year else None
            if signals["ownership_years"] and signals["ownership_years"] >= 20:
                signals["is_long_term_owner"] = True

    # Tax delinquency cohort: TS2202 = 2022 tax year sale = 4+ years delinquent
    ts = lead.get("tax_sale_marker") or ""
    if ts == "TS2202":
        signals["tax_delinquent_years"] = "4+"
    elif ts == "TS2301":
        signals["tax_delinquent_years"] = "3+"

    # High value
    if (lead.get("total_appraisal_usd") or 0) > 100000:
        signals["is_high_value"] = True

    return signals


def build_browser_queue(lead: dict, signals: dict) -> list[dict]:
    """Generate the URLs Marquise should browser-MHTML for browser-only sources."""
    owner = (lead.get("owner_name") or "").strip()
    # Strip "ESTATE OF" wrapper for searches
    owner_clean = re.sub(r"\s*\(\s*ESTATE OF\s*\)\s*", "", owner).strip()
    decedent = signals.get("estate_decedent_name") or owner_clean
    last_first = " ".join(reversed(decedent.split())) if " " in decedent else decedent

    mailing_city = (lead.get("owner_mailing_city") or "").strip()
    mailing_state = (lead.get("owner_mailing_state") or "").strip()
    prop_addr = (lead.get("property_address") or "").strip()

    queue = []

    # --- Probate court (browser, decedent search) ---
    if signals["is_estate"]:
        queue.append({
            "label": f"Shelby County Probate Court -- search for decedent '{decedent}'",
            "url": "https://probatedata.shelbycountytn.gov/ProbateCourt/",
            "instructions": f"Search by name. Try '{last_first}' AND '{decedent}'. Save the case-list result as MHTML. We want: case number, executor name, executor address, opening date, status (open/closed).",
            "priority": "CRITICAL",
        })

    # --- Register of Deeds (all parties' deeds in Shelby County) ---
    queue.append({
        "label": f"Shelby Register of Deeds -- all deeds in '{owner_clean}' name",
        "url": "https://search.register.shelby.tn.us/search/",
        "instructions": f"Name search '{owner_clean}'. Save MHTML of result list. Tells us if owner has OTHER properties in Shelby County (= portfolio = sophisticated investor).",
        "priority": "HIGH",
    })

    # --- Find-a-Grave (decedent search if estate) ---
    if signals["is_estate"]:
        queue.append({
            "label": f"Find-a-Grave -- {decedent} death record",
            "url": f"https://www.findagrave.com/memorial/search?firstname={quote_plus(decedent.split()[-1] if ' ' in decedent else decedent)}&lastname={quote_plus(decedent.split()[0])}&location=Tennessee",
            "instructions": "Free, returns death year + cemetery + sometimes spouse/relatives. MHTML the result page.",
            "priority": "HIGH",
        })

    # --- Obituary search (Legacy.com + Tribute Archive via Google) ---
    queue.append({
        "label": f"Obit search -- Google site:legacy.com '{decedent}' Memphis",
        "url": f"https://www.google.com/search?q=site%3Alegacy.com+%22{quote_plus(decedent)}%22+Memphis+OR+Tennessee",
        "instructions": "Click any hit, MHTML the obit. Tells us: death date, age, surviving family names + cities (= heir candidates).",
        "priority": "HIGH" if signals["is_estate"] else "LOW",
    })

    # --- Public Facebook search (current user) ---
    queue.append({
        "label": f"Facebook public search -- {owner_clean} in {mailing_city or 'Memphis'}",
        "url": f"https://www.facebook.com/public/{quote_plus(owner_clean)}",
        "instructions": "If profile public, tells us age range, employer, family, recent posts. Don't friend; just look. MHTML the search result page.",
        "priority": "MEDIUM",
    })

    # --- LinkedIn (employment intel) ---
    queue.append({
        "label": f"LinkedIn search -- {owner_clean} {mailing_city}",
        "url": f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(owner_clean + ' ' + mailing_city)}",
        "instructions": "Profession, employer, tenure. Helps frame the pitch (busy professional = lead with time-saving; recent retiree = lead with simplicity).",
        "priority": "MEDIUM" if not signals["is_estate"] else "LOW",
    })

    # --- Cross-state assessor (does owner have property in mailing state too?) ---
    if signals["is_absentee_outofstate"]:
        queue.append({
            "label": f"County assessor for {mailing_city} {mailing_state} -- check if owner has property there too",
            "url": f"https://www.google.com/search?q=%22{quote_plus(owner_clean)}%22+{quote_plus(mailing_city)}+{quote_plus(mailing_state)}+property+assessor+OR+deed",
            "instructions": "If owner has primary residence in mailing city, that's another contact path + tells us their financial position.",
            "priority": "MEDIUM",
        })

    # --- Court records (eviction / foreclosure / civil suits) ---
    queue.append({
        "label": "TN Public Notice + Court Records -- civil/foreclosure history",
        "url": f"https://www.tncourts.gov/courts/public-notices",
        "instructions": f"Search '{owner_clean}'. Civil suits, eviction filings, foreclosure starts = financial pressure signals.",
        "priority": "MEDIUM",
    })

    # --- Obituary cross-search for any potential heir name patterns ---
    if signals["is_estate"] and decedent:
        # Common first-name possibilities for the decedent
        queue.append({
            "label": f"Newspaper archive: Daily Memphian search -- '{decedent}'",
            "url": f"https://www.google.com/search?q=site%3Adailymemphian.com+%22{quote_plus(decedent)}%22",
            "instructions": "Sometimes Daily Memphian publishes paid notices / community news. Death notices contain heir names + cities.",
            "priority": "LOW",
        })

    return queue


def build_pitch_hooks(lead: dict, signals: dict) -> list[dict]:
    """
    Translate intel signals into permitted pitch frames.
    Each hook = one ANGLE the offer can lead with. Hammer picks one based on intel + context.
    """
    hooks = []
    addr = (lead.get("property_address") or "").strip()
    city = (lead.get("owner_mailing_city") or "").strip().title()
    state = (lead.get("owner_mailing_state") or "").strip()
    appr = lead.get("total_appraisal_usd") or 0

    if signals["is_estate"]:
        hooks.append({
            "name": "estate_burden_relief",
            "angle": "Empathy for the estate process + we close direct with executor",
            "lead_line": f"I understand the family may still be settling the estate, and out-of-state real estate paperwork can drag on. We close direct with the executor in 14 days — no agent, no inspection, no out-of-pocket cost to the estate.",
            "use_when": "Always lead with this if estate is open in probate.",
        })

    if signals["is_absentee_outofstate"]:
        hooks.append({
            "name": "outofstate_convenience",
            "angle": "Distance is the pain; we handle 100% remotely",
            "lead_line": f"Managing a Memphis property from {city} {state} is its own kind of work — tax notices, code letters, occasional weed-cutting bills. We handle the full close-out by mail and wire. You don't fly in.",
            "use_when": "Out-of-state, non-estate, no portfolio signals.",
        })

    if signals["owner_mailing_apartment"]:
        hooks.append({
            "name": "modest_residence_simple_offer",
            "angle": "Simple, clean, no surprises (matches modest-residence framing)",
            "lead_line": f"Cash, in your hand at closing. We pay the back property tax at closing — you don't owe a dime out of pocket. We'll mail the offer + closing paperwork. Fourteen days.",
            "use_when": "Owner mailing is an apartment number / shared-housing — frame for clarity not sophistication.",
        })

    if signals["is_llc_owner"]:
        hooks.append({
            "name": "investor_to_investor",
            "angle": "Peer-to-peer, no sales pitch needed",
            "lead_line": f"Saw the LLC in title. We're investor-to-investor — no agent commission, fast assignment-friendly close, RESPA-clean Memphis title. Happy to package this with any other Memphis lots if you're looking to thin inventory.",
            "use_when": "LLC / corporate owner, vacant lot or low-yield SFR.",
        })

    if signals["is_religious_org_owner"]:
        hooks.append({
            "name": "ministry_clean_close",
            "angle": "Ministries hold real estate that's not central to the mission",
            "lead_line": f"Ministries sometimes end up holding lots that aren't central to the mission. We can close clean and quick, freeing the funds for ministry work. Cash, no commission, 14-day close.",
            "use_when": "Church / ministry / nonprofit owner.",
        })

    if signals["is_long_term_owner"]:
        years = signals.get("ownership_years") or "many"
        hooks.append({
            "name": "long_ownership_dignified_close",
            "angle": "Honor the time; clean exit",
            "lead_line": f"You've held this property for {years} years — that's a long time. Memphis values have shifted and so has the cost of carrying property. We can offer a clean, no-surprise close.",
            "use_when": "Owner held property >=20 years, no estate.",
        })

    if signals["tax_delinquent_years"] == "4+":
        hooks.append({
            "name": "back_tax_relief",
            "angle": "We pay the back tax — you walk clean",
            "lead_line": f"We see the property's been on the back-tax list for a few years. We pay every dollar of back tax + penalty at closing — out of OUR side, not yours. You walk away clean.",
            "use_when": "TS2202 lead. Strong on absentee owners with no plan to develop.",
        })

    if signals["is_vacant_lot"]:
        hooks.append({
            "name": "vacant_lot_quick_cash",
            "angle": "Lots are inert assets; we move fast",
            "lead_line": f"Vacant lots aren't easy to sell — agents don't want them, builders take months. We'll wire cash for {addr} in 14 days. No fix-up. No inspection. As-is.",
            "use_when": "Vacant lot, any owner type.",
        })

    if not hooks:
        hooks.append({
            "name": "generic_cash_close",
            "angle": "Standard cash close",
            "lead_line": "Cash, no agent, 14-day close. We pay back tax. You walk with clean money.",
            "use_when": "Fallback if no other signals.",
        })

    return hooks


def render_intel_md(lead: dict, signals: dict, queue: list[dict], hooks: list[dict]) -> str:
    parcel = (lead.get("parcel_id") or "?").strip()
    owner = lead.get("owner_name") or "?"
    addr = lead.get("property_address") or "?"
    city = lead.get("owner_mailing_city") or "?"
    state = lead.get("owner_mailing_state") or "?"
    zc = lead.get("owner_mailing_zip") or "?"

    out = []
    out.append(f"# Seller Intel: {owner}")
    out.append(f"**Property:** {addr}, MEMPHIS, TN | **Parcel:** `{parcel}`")
    out.append(f"**Owner mailing:** {lead.get('owner_mailing_street','?')}, {city} {state} {zc}")
    out.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    out.append("")
    out.append("## Signals detected")
    for k, v in signals.items():
        if v not in (False, None, ""):
            out.append(f"- **{k.replace('_',' ').title()}:** `{v}`")
    out.append("")
    out.append("## Pitch hooks (Hammer picks ONE that fits)")
    for h in hooks:
        out.append(f"### {h['name']}  --  *{h['angle']}*")
        out.append(f"> {h['lead_line']}")
        out.append(f"_Use when:_ {h['use_when']}")
        out.append("")
    out.append("## Browser-MHTML queue (do these to enrich)")
    for q in sorted(queue, key=lambda x: {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}.get(x["priority"],9)):
        out.append(f"### [{q['priority']}] {q['label']}")
        out.append(f"- URL: {q['url']}")
        out.append(f"- {q['instructions']}")
        out.append("")
    out.append("---")
    out.append("_Privacy/legal: only public-record signals listed. No protected-class profiling. Pitch hooks reference SITUATIONAL not IDENTITY attributes._")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parcel", help="Parcel ID to look up in leads_db.json")
    ap.add_argument("--owner", help="Owner name (alternative to --parcel)")
    ap.add_argument("--mailing", help="Owner mailing address (alternative to --parcel)")
    args = ap.parse_args()

    if args.parcel:
        lead = lookup_by_parcel(args.parcel)
        if not lead:
            print(f"No lead found for parcel '{args.parcel}'")
            return
    else:
        if not args.owner:
            print("Provide --parcel or --owner + --mailing")
            return
        lead = {"owner_name": args.owner, "owner_mailing_street": args.mailing or "?",
                "parcel_id": "manual", "property_address": "?"}

    signals = detect_signals(lead)
    queue = build_browser_queue(lead, signals)
    hooks = build_pitch_hooks(lead, signals)

    parcel_safe = re.sub(r"[^a-zA-Z0-9]", "_", lead.get("parcel_id", "manual"))
    out_dir = INTEL_ROOT / parcel_safe
    out_dir.mkdir(exist_ok=True)

    intel_md = render_intel_md(lead, signals, queue, hooks)
    (out_dir / "intel.md").write_text(intel_md)
    (out_dir / "intel.json").write_text(json.dumps({
        "lead": {k: lead.get(k) for k in ["parcel_id","property_address","owner_name",
            "owner_mailing_street","owner_mailing_city","owner_mailing_state","owner_mailing_zip",
            "is_vacant_lot","total_appraisal_usd","sales_history","tax_sale_marker"]},
        "signals": signals,
        "browser_queue": queue,
        "pitch_hooks": hooks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2, default=str))

    print(f"Intel saved to: {out_dir}")
    print()
    print(intel_md)


if __name__ == "__main__":
    main()
