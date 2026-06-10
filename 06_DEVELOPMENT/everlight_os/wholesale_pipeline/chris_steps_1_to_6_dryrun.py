"""chris_steps_1_to_6_dryrun -- run the Chris Ulander pipeline steps 1-6
WITHOUT contacting anyone.

Workflow per /Wholesale/buyers/MIDSOUTH_DISINTERMEDIATION_FIX.md:

  Step 1: Filter Banks picks top-priority property (already done by
          chris_pipeline_orchestrator -- this reads the latest qualified
          dossier and selects #1 by composite score).
  Step 2: Rex Blackwell skip-traces the owner (cascade.py if available,
          else managed_agent envelope dispatched for research).
  Step 3: Piper Reeves drafts cold-mail outreach (HTML email + postcard
          content). DRY RUN: rendered to local file, NOT sent.
  Step 4: Hammer Ortiz simulates negotiation -- cash offer math
          (~70% ARV - repair). Outputs offer JSON.
  Step 5: PSA prefill + TN SB 909 disclosure rendered as JSON+PDF stubs.
  Step 6: Penny Vance assembles the deal package (HTML report) ready for
          Chris -- but per Rich's directive, NOT sent.

All outputs land in:
  /Wholesale/contracts/active_deals/<date>_chris_qualified/<step>/

Honors WHOLESALE_OUTBOUND_HALT: steps 3 + 7 (the "send" steps) are gated.
This orchestrator never reaches step 7.

Persona narration applied per agent (Filter Banks, Rex, Piper, Hammer, Penny).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("chris_steps")

PACKAGE_ROOT = Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals")


def _latest_dossier() -> Path:
    """Return path to the most recent qualified_dossier.json."""
    for d in sorted(PACKAGE_ROOT.glob("*chris_qualified*"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        if (d / "qualified_dossier.json").exists():
            return d
    raise FileNotFoundError("no qualified_dossier.json found -- run chris_pipeline_orchestrator first")


def _composite_score(prop: dict) -> float:
    """Score a qualified property. Higher = better deal candidate."""
    score = 0.0
    arv = prop.get("arv") or 0
    # Sweet spot: $80k-$120k (most deal-able for Chris's Section 8 hold)
    if 80_000 <= arv <= 120_000:
        score += 30
    elif 60_000 <= arv <= 150_000:
        score += 20
    elif arv > 0:
        score += 10
    # Distress signals weight heavy
    distress = prop.get("distress") or []
    score += len(distress) * 15
    # Absentee owner = motivated seller
    if prop.get("is_absentee"):
        score += 25
    # Year built sweet spot
    yb = prop.get("year_built")
    if yb and 1940 <= yb <= 1980:
        score += 10
    return score


# ── Step 1: Pick high-priority property ──────────────────────────


def step_1_pick(dossier_dir: Path) -> dict:
    log.info("STEP 1 -- Filter Banks: picking highest-score property")
    dossier = json.loads((dossier_dir / "qualified_dossier.json").read_text())
    qualified = dossier.get("addresses", [])
    if not qualified:
        log.error("no qualified properties in dossier")
        return {}
    scored = sorted(qualified, key=_composite_score, reverse=True)
    pick = scored[0]
    log.info(f"  picked: {pick.get('address')} (score={_composite_score(pick):.0f})")
    out = dossier_dir / "step_1_pick.json"
    out.write_text(json.dumps({
        "agent": "Filter Banks",
        "narration": (
            f"Numbers don't lie. Out of {len(qualified)} qualified, "
            f"{pick.get('address')} scores highest -- ARV ${pick.get('arv') or '?'}, "
            f"distress signals: {pick.get('distress') or 'none'}, "
            f"absentee: {pick.get('is_absentee')}. Pick this one."
        ),
        "pick": pick,
        "ranked_pool": scored,
    }, indent=2))
    log.info(f"  wrote {out}")
    return pick


# ── Step 2: Skip-trace owner ─────────────────────────────────────


def step_2_skip_trace(dossier_dir: Path, pick: dict) -> dict:
    log.info("STEP 2 -- Rex Blackwell: skip-tracing owner")
    address = pick.get("address", "")
    owner = pick.get("owner", "")
    parcel = pick.get("parcel_id", "")
    # Load full intel from seller_intel/ for the mailing address
    intel_path = Path(
        f"/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel/"
        f"{parcel.replace('  ', '__')}/intel.json"
    )
    intel = {}
    if intel_path.exists():
        intel = json.loads(intel_path.read_text()).get("lead", {})
    mailing_street = intel.get("owner_mailing_street", "")
    mailing_city = intel.get("owner_mailing_city")
    mailing_state = intel.get("owner_mailing_state")
    mailing_zip = intel.get("owner_mailing_zip")

    is_entity = any(t in owner.upper() for t in
                     ["LLC", "INC", "CHURCH", "TRUST", "CORP", "LP ", "ESTATE", "PARTNERS"])

    result = {
        "agent": "Rex Blackwell",
        "owner": owner,
        "is_entity": is_entity,
        "mailing": {
            "street": mailing_street,
            "city": mailing_city,
            "state": mailing_state,
            "zip": mailing_zip,
        },
        "phone_candidates": [],
        "email_candidates": [],
        "skip_trace_method": "deferred -- managed_agent dispatch needed",
        "narration": "",
    }
    if is_entity:
        result["narration"] = (
            f"Entity owner: '{owner}'. TPS/FastPeopleSearch don't work on "
            f"entities -- those are person searches. For a church, I'd run "
            f"a TN Secretary of State business filing lookup + scrape the "
            f"church's website (likely public). Mailing on file: "
            f"{mailing_street}. City/state/zip MISSING -- need to pull "
            f"that from the assessor page directly. Recommendation: dispatch "
            f"a managed_agent envelope to research the church online."
        )
    else:
        result["narration"] = (
            f"Natural person: '{owner}'. Cascade order: TPS -> FastPeopleSearch "
            f"-> ZabaSearch -> county records. Realistic 35-45% E2E hit rate. "
            f"Need ProxyScrape for Cloudflare bypass. Currently DEFERRED -- "
            f"dispatch via cascade.py once proxy is provisioned."
        )

    # Address completeness check
    gaps = []
    if not mailing_city: gaps.append("mailing_city missing")
    if not mailing_state: gaps.append("mailing_state missing")
    if not mailing_zip: gaps.append("mailing_zip missing")
    if intel.get("year_built") is None: gaps.append("year_built missing")
    if intel.get("sqft") is None: gaps.append("sqft missing")
    if intel.get("beds") is None: gaps.append("beds missing")
    result["data_gaps"] = gaps

    out = dossier_dir / "step_2_skip_trace.json"
    out.write_text(json.dumps(result, indent=2))
    log.info(f"  wrote {out} (gaps: {gaps})")
    return result


# ── Step 3: Piper outreach (DRY RUN) ─────────────────────────────


def step_3_outreach(dossier_dir: Path, pick: dict, skip: dict) -> dict:
    log.info("STEP 3 -- Piper Reeves: drafting outreach (DRY RUN, NOT sent)")
    address = pick.get("address", "")
    owner = skip.get("owner", "")
    is_entity = skip.get("is_entity", False)
    mailing = skip.get("mailing", {})

    # Check halt flag
    halt_active = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").lower() in ("1", "true", "yes")

    # Postcard text (warm, Tennessee-specific, TN SB 909 compliant)
    if is_entity:
        salutation = f"To the {owner.title()} Property Committee,"
    else:
        salutation = f"Hello {owner.split()[-1].title() if owner else 'Owner'},"

    postcard_text = (
        f"{salutation}\n\n"
        f"My name is Piper Reeves with Everlight Ventures. I noticed your "
        f"property at {address.title()}, Memphis TN. We work with "
        f"local Memphis investors who buy properties as-is, cash, no repairs "
        f"required. If you've ever thought about selling -- or just want to "
        f"know what your property's worth in today's market -- I'd love to "
        f"have a quick conversation.\n\n"
        f"No pressure. No obligation. I just like meeting Memphis property "
        f"owners.\n\n"
        f"Call or text anytime: <PHONE>\n"
        f"Or email: piper@everlightventures.io\n\n"
        f"Warmly,\n"
        f"Piper Reeves\n"
        f"Everlight Ventures\n\n"
        f"---\n"
        f"You're receiving this postcard because of public property records. "
        f"To stop receiving mail from us, reply STOP via mail or email. "
        f"TN-SB909 compliance: this is not a foreclosure-rescue offer."
    )

    email_html = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: Inter, sans-serif; color: #E8E8E8; background: #0A0A0A;
       max-width: 600px; margin: 0 auto; padding: 32px; }}
h2 {{ font-family: 'Playfair Display', serif; color: #D4A843; margin-top: 0; }}
.signature {{ color: #D4A843; font-style: italic; }}
.disclaimer {{ font-size: 11px; color: #999999; margin-top: 32px;
              border-top: 1px solid #1A1A1A; padding-top: 16px; }}
</style></head>
<body>
<h2>Quick note about your Memphis property</h2>
<p>{salutation.replace(chr(10), '<br>')}</p>
<p>I'm Piper with Everlight Ventures. We work with Memphis investors who buy
properties as-is, cash, no repairs needed.</p>
<p>I came across your property at <strong>{address.title()}</strong> and
wanted to reach out -- not to pressure you, just to introduce myself.</p>
<p>If you've ever thought about selling, or just want a no-obligation
conversation about what your property's worth, I'd love to chat.</p>
<p>You can reach me anytime:</p>
<ul>
<li>Email: piper@everlightventures.io</li>
<li>Reply to this email</li>
</ul>
<p class="signature">Warmly,<br>Piper Reeves<br>Everlight Ventures</p>
<p class="disclaimer">
You're receiving this email because of public property records. To stop,
reply STOP. TN-SB909 compliance: this is not a foreclosure-rescue offer.
Everlight Ventures is not a licensed real estate broker.
</p>
</body></html>
"""

    result = {
        "agent": "Piper Reeves",
        "halt_active": halt_active,
        "would_send": False,
        "channel_eligibility": {
            "tn_cold_call": "BLOCKED -- TN telephone solicitor rules",
            "tn_sms": "BLOCKED -- TN telephone solicitor rules",
            "tn_mail": "ALLOWED with TN-SB909 disclaimer",
            "tn_email": "ALLOWED with CAN-SPAM disclaimer + opt-out",
        },
        "postcard_text": postcard_text,
        "email_html": email_html,
        "narration": (
            f"Y'all, I drafted the postcard and email. {'Skipping send -- ' + ('halt active' if halt_active else 'dry-run mode')}. "
            f"Once Justine + Marcus signoff lifts the halt, I'll fire it through "
            f"branded_mailer with budget_category=nurture. Postcard goes through Lob "
            f"to {mailing.get('street','<unknown>')} -- need city/state/zip filled "
            f"in first or it bounces."
        ),
    }
    out_dir = dossier_dir / "step_3_outreach"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "postcard.txt").write_text(postcard_text)
    (out_dir / "email.html").write_text(email_html)
    (out_dir / "metadata.json").write_text(json.dumps(result, indent=2))
    log.info(f"  wrote {out_dir}/{{postcard.txt, email.html, metadata.json}}")
    log.info(f"  halt_active={halt_active}, would_send=False (DRY RUN)")
    return result


# ── Step 4: Negotiation math ─────────────────────────────────────


def step_4_negotiate(dossier_dir: Path, pick: dict) -> dict:
    log.info("STEP 4 -- Hammer Ortiz: cash offer math (simulated)")
    arv = pick.get("arv") or 0
    # Default repair estimate per sqft -- use $30/sqft moderate rehab
    # Without sqft data, assume 1200 sqft (Memphis SFR median for under-$100k)
    sqft = pick.get("sqft") or 1200
    repair_per_sqft = 30
    repair_estimate = sqft * repair_per_sqft

    # Chris's MAO (max allowable offer) is ~70% ARV - repair
    chris_mao = (arv * 0.70) - repair_estimate
    # Our offer to seller = Chris's MAO - assignment_fee (target ~$5k margin)
    target_assignment_fee = 5000
    seller_cash_offer = chris_mao - target_assignment_fee
    spread_ok = seller_cash_offer > 0 and target_assignment_fee >= 2500

    result = {
        "agent": "Hammer Ortiz",
        "math": {
            "ARV_usd": arv,
            "sqft_assumed": sqft,
            "repair_per_sqft_usd": repair_per_sqft,
            "repair_estimate_usd": repair_estimate,
            "chris_MAO_70pct_ARV_minus_repair_usd": round(chris_mao),
            "target_assignment_fee_usd": target_assignment_fee,
            "seller_cash_offer_usd": round(seller_cash_offer),
            "spread_viable": spread_ok,
        },
        "negotiation_floor": round(seller_cash_offer * 0.85),  # walk-away
        "negotiation_ceiling": round(chris_mao - 2500),  # min margin
        "narration": (
            f"Champ, ARV ${arv:,}, repair est ${repair_estimate:,}. "
            f"Chris's max is ${chris_mao:,.0f}. Target margin $5k. "
            f"Seller offer: ${seller_cash_offer:,.0f}. "
            + ("VIABLE -- ship it." if spread_ok else
               "MARGIN TOO TIGHT -- need better data (real sqft + condition) "
               "OR pass on this property.")
        ),
    }
    out = dossier_dir / "step_4_negotiate.json"
    out.write_text(json.dumps(result, indent=2))
    log.info(f"  wrote {out} (viable={spread_ok})")
    return result


# ── Step 5: PSA + TN SB 909 disclosure ───────────────────────────


def step_5_psa(dossier_dir: Path, pick: dict, negotiate: dict) -> dict:
    log.info("STEP 5 -- Hammer + Marquise: PSA prefill + TN SB 909 disclosure")
    address = pick.get("address", "")
    owner = pick.get("owner", "")
    parcel = pick.get("parcel_id", "")
    cash_offer = negotiate["math"]["seller_cash_offer_usd"]

    psa = {
        "doc_type": "Purchase and Sale Agreement (TN)",
        "buyer": "Everlight Ventures, LLC (with right to assign)",
        "seller": owner,
        "property_address": address,
        "parcel_id": parcel,
        "purchase_price_usd": cash_offer,
        "earnest_money_usd": 100,    # $100 token EMD per dossier guidance
        "emd_holder": "Mid-South Title Company",
        "closing_date_target": (datetime.now() +
                                  __import__("datetime").timedelta(days=21)).strftime("%Y-%m-%d"),
        "inspection_period_days": 7,
        "financing_contingency": "NONE -- cash purchase",
        "title_contingency": "Buyer's option, marketable title required",
        "occupancy_at_closing": "Vacant unless seller and buyer agree otherwise in writing",
        "assignment_clause": (
            "Buyer may assign this contract to any third party without "
            "seller's consent, provided assignee assumes all buyer obligations."
        ),
        "tn_sb909_disclosure": {
            "doc_type": "TN SB 909 Wholesale Disclosure",
            "statute": "T.C.A. Title 66, Chapter 35 (effective 2024-07-01)",
            "disclosure_text": (
                "Pursuant to Tennessee Senate Bill 909 (2024), Buyer "
                "(Everlight Ventures, LLC) discloses to Seller that Buyer "
                "may assign this contract to a third-party purchaser for "
                "an assignment fee. Buyer is not a licensed Tennessee real "
                "estate broker and is not representing Seller in this "
                "transaction. Seller has the right to consult independent "
                "legal counsel before signing."
            ),
            "assignment_fee_disclosed_usd": negotiate["math"]["target_assignment_fee_usd"],
            "rescission_period_days": 5,  # TN cooling-off
        },
        "agent": "Hammer + Marquise",
        "narration": (
            f"PSA prefilled. Cash $${cash_offer}, EMD $100, 21-day close, "
            f"7-day inspection. TN SB 909 disclosure attached -- assignment "
            f"fee disclosed at ${negotiate['math']['target_assignment_fee_usd']}. "
            f"Mid-South Title holds EMD. Once seller signs, EMD wires same day."
        ),
    }
    out = dossier_dir / "step_5_psa_prefill.json"
    out.write_text(json.dumps(psa, indent=2))
    log.info(f"  wrote {out}")
    return psa


# ── Step 6: Penny deal package for Chris ─────────────────────────


def step_6_package(dossier_dir: Path, pick: dict, skip: dict, negotiate: dict,
                   psa: dict) -> dict:
    log.info("STEP 6 -- Penny Vance: assembling Chris-ready deal package")
    address = pick.get("address", "")
    parcel = pick.get("parcel_id", "")
    arv = pick.get("arv") or 0
    cash_offer = negotiate["math"]["seller_cash_offer_usd"]
    assignment_fee = negotiate["math"]["target_assignment_fee_usd"]
    chris_total = cash_offer + assignment_fee

    # Build the HTML report
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body {{ font-family: Inter, sans-serif; color: #E8E8E8; background: #0A0A0A;
       max-width: 800px; margin: 0 auto; padding: 32px; line-height: 1.5; }}
h1, h2 {{ font-family: 'Playfair Display', serif; color: #D4A843; }}
h1 {{ border-bottom: 2px solid #D4A843; padding-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th {{ background: #1A1A1A; color: #D4A843; text-align: left; padding: 8px;
     border-bottom: 1px solid #D4A843; }}
td {{ padding: 8px; border-bottom: 1px solid #1A1A1A; }}
.callout {{ background: #1A1A1A; padding: 16px; border-left: 4px solid #D4A843;
           margin: 16px 0; }}
.gap-warning {{ color: #ff6b6b; }}
.signature {{ color: #D4A843; font-style: italic; margin-top: 32px; }}
</style></head>
<body>
<h1>Memphis Wholesale Deal Package</h1>
<p><strong>Compiled:</strong> {datetime.now(timezone.utc).isoformat()}<br>
<strong>For:</strong> Chris Ulander, Mid South Homebuyers, LLC<br>
<strong>From:</strong> Penny Vance, Everlight Ventures</p>

<h2>Property</h2>
<table>
<tr><th>Address</th><td>{address}, Memphis TN 38106</td></tr>
<tr><th>Parcel ID</th><td>{parcel}</td></tr>
<tr><th>Owner</th><td>{pick.get('owner', '?')}</td></tr>
<tr><th>ARV (est)</th><td>${arv:,}</td></tr>
<tr><th>Year built</th><td>{pick.get('year_built') or '<span class="gap-warning">UNKNOWN -- pull from assessor</span>'}</td></tr>
<tr><th>Sqft</th><td>{negotiate['math']['sqft_assumed']:,} <em>(assumed -- need verification)</em></td></tr>
</table>

<h2>The Numbers</h2>
<table>
<tr><th>ARV</th><td>${arv:,}</td></tr>
<tr><th>Repair estimate ({negotiate['math']['sqft_assumed']:,} sqft x ${negotiate['math']['repair_per_sqft_usd']}/sqft)</th><td>${negotiate['math']['repair_estimate_usd']:,}</td></tr>
<tr><th>Chris's MAO (70% ARV - repair)</th><td>${negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd']:,}</td></tr>
<tr><th>Our offer to seller</th><td>${cash_offer:,}</td></tr>
<tr><th>Assignment fee (Everlight)</th><td>${assignment_fee:,}</td></tr>
<tr><th>Chris's all-in cost</th><td><strong>${chris_total:,}</strong></td></tr>
</table>

<div class="callout">
<strong>Spread analysis:</strong> Chris's MAO is ${negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd']:,}.
Our seller offer ${cash_offer:,} + our assignment fee ${assignment_fee:,} =
${chris_total:,}. Spread for Chris vs his MAO: ${negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd'] - chris_total:,}.
</div>

<h2>Contract Status</h2>
<p>PSA prefilled, NOT YET SIGNED. Pending steps before sending to Chris:</p>
<ul>
<li>Step 3: Outreach to seller (currently DRY RUN -- halt lift required)</li>
<li>Step 4: Seller reply + negotiation</li>
<li>Step 5: PSA + TN SB 909 disclosure signed by seller</li>
<li>EMD ($100) wired to Mid-South Title</li>
</ul>

<h2>Data Gaps</h2>
<ul>
{chr(10).join(f'<li class="gap-warning">{g}</li>' for g in skip.get('data_gaps', []))}
</ul>

<p class="signature">-- Penny Vance, Everlight Ventures<br>
penny@everlightventures.io</p>
</body></html>
"""

    out_dir = dossier_dir / "step_6_chris_package"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "package.html").write_text(html)
    (out_dir / "summary.json").write_text(json.dumps({
        "agent": "Penny Vance",
        "would_send_to_chris": False,  # gated; only after step 5 signed
        "package_path": str(out_dir / "package.html"),
        "spread_for_chris_usd": negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd'] - chris_total,
        "narration": (
            f"Package built. Chris's MAO ${negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd']:,}, "
            f"our all-in for him ${chris_total:,}, his spread "
            f"${negotiate['math']['chris_MAO_70pct_ARV_minus_repair_usd'] - chris_total:,}. "
            f"NOT shipping until: (a) seller signs PSA, (b) Justine + Marcus "
            f"signoff lifts WHOLESALE_OUTBOUND_HALT. Both gates open before "
            f"this hits leads@midsouthhomebuyers.com."
        ),
    }, indent=2))
    log.info(f"  wrote {out_dir}/{{package.html, summary.json}}")
    return {"package_dir": str(out_dir)}


# ── Main ─────────────────────────────────────────────────────────


def main() -> int:
    dossier_dir = _latest_dossier()
    log.info(f"running steps 1-6 against dossier: {dossier_dir}")

    pick = step_1_pick(dossier_dir)
    if not pick:
        return 1
    skip = step_2_skip_trace(dossier_dir, pick)
    outreach = step_3_outreach(dossier_dir, pick, skip)
    negotiate = step_4_negotiate(dossier_dir, pick)
    psa = step_5_psa(dossier_dir, pick, negotiate)
    package = step_6_package(dossier_dir, pick, skip, negotiate, psa)

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "dossier_dir": str(dossier_dir),
        "property": pick.get("address"),
        "viable": negotiate["math"]["spread_viable"],
        "data_gaps": skip.get("data_gaps", []),
        "halt_blocking_send": outreach["halt_active"],
        "package_html": package["package_dir"] + "/package.html",
        "next_steps": [
            "Fix data gaps (year_built, sqft, beds, baths, mailing city/state/zip)",
            "Justine + Marcus signoff to lift WHOLESALE_OUTBOUND_HALT",
            "Then: actually send Step 3 outreach via branded_mailer + Lob",
        ],
    }
    out = dossier_dir / "STEPS_1_TO_6_SUMMARY.json"
    out.write_text(json.dumps(summary, indent=2))
    log.info(f"DONE -- summary at {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
