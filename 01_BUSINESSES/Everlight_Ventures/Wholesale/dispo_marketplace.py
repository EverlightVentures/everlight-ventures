"""dispo_marketplace -- generate upload-ready deal sheets for backup buyer
marketplaces (MaxDispo, PINetwork, Connected Investors, FB groups).

Why this exists:
  Our own buyer list (currently 19 buyers) might not be deep enough on Deal #1
  to guarantee a winning bid in the 14-21 day close window. Backup channels:

    Free:
      - MaxDispo.com -- email submit form, no fee, takes 24-72h to match
      - Connected Investors marketplace -- free signup
      - Local REIA Facebook groups -- free post
      - PINetwork.com -- free 30-day trial

    Paid (post Deal 1):
      - PropStream marketplace -- $99/mo
      - DealMachine marketplace -- $89/mo

This module:
  1. Takes a Deal id (locked-up contract)
  2. Generates a branded one-page deal sheet HTML (printable)
  3. Generates a plain-text "deal blurb" copy-paste ready for FB groups
  4. Optionally emails to MaxDispo's intake address (buyers@maxdispo.com)
  5. Logs the dispatch to dispo_marketplace_ledger.jsonl

NEVER use this without first running the bid_war_engine. The bid war goes
to YOUR buyer list FIRST. Marketplace is the safety net.

Usage:
  python3 dispo_marketplace.py one-pager --deal-id=<uuid>
  python3 dispo_marketplace.py blurb --deal-id=<uuid>
  python3 dispo_marketplace.py email-maxdispo --deal-id=<uuid>
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/wholesale",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale",
    "/home/opc/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("dispo_marketplace")

OUT_DIR = Path("/home/opc/hive_reports/dispo")
OUT_DIR.mkdir(parents=True, exist_ok=True)
LEDGER = Path("/home/opc/wholesale/_logs/dispo_marketplace.jsonl")
LEDGER.parent.mkdir(parents=True, exist_ok=True)

PUBLIC_BASE = "http://127.0.0.1:2200/reports/dispo"

# Backup marketplace email intakes (verify these before using)
MARKETPLACE_INTAKES = {
    "maxdispo":           "buyers@maxdispo.com",        # confirm via their site
    "pinetwork":          "submit@pinetwork.com",        # confirm
    "connectedinvestors": "deals@connectedinvestors.com",  # confirm
}


def _money(n: float) -> str:
    return f"${n:,.0f}"


def _build_one_pager_html(deal, money_chain) -> str:
    """Branded one-page deal sheet. Print-friendly. Upload to any marketplace."""
    addr = getattr(deal, "property_address", "") or ""
    city = getattr(deal, "property_city", "") or ""
    state = getattr(deal, "property_state", "") or ""
    bedrooms = getattr(deal, "property_bedrooms", 3) or 3
    bathrooms = getattr(deal, "property_bathrooms", 1) or 1
    sqft = getattr(deal, "property_sqft", 1200) or 1200

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>OFF-MARKET DEAL -- {addr} -- {_money(money_chain.buyer_ask)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600;700&display=swap">
<style>
  body {{ font-family: 'Inter', sans-serif; margin: 0; padding: 32px;
         background: #fafaf6; color: #111; }}
  .sheet {{ max-width: 800px; margin: 0 auto; background: #fff;
            padding: 40px; border: 2px solid #D4A843; }}
  .wordmark {{ color: #D4A843; letter-spacing: 4px; font-size: 11px; font-weight: 700; }}
  h1 {{ font-family: 'Playfair Display', serif; color: #0A0A0A;
       margin: 8px 0 4px; font-size: 28px; }}
  .badge {{ background: #0F7B3D; color: #fff; padding: 6px 14px; font-weight: 600;
           letter-spacing: 1px; font-size: 11px; text-transform: uppercase;
           display: inline-block; margin-top: 6px; }}
  .price-box {{ background: #0A0A0A; color: #D4A843; padding: 24px;
                text-align: center; margin: 24px 0; }}
  .price-box .label {{ font-size: 11px; letter-spacing: 3px; text-transform: uppercase; opacity: 0.7; }}
  .price-box .number {{ font-family: 'Playfair Display', serif; font-size: 48px;
                        margin: 8px 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin: 14px 0; }}
  td {{ padding: 6px 12px; }}
  td.k {{ background: #fafafa; color: #666; width: 45%; }}
  td.v {{ font-weight: 600; }}
  .green {{ color: #0F7B3D; font-weight: 700; }}
  .footer {{ margin-top: 24px; padding-top: 14px; border-top: 1px solid #ddd;
             font-size: 11px; color: #666; }}
</style>
</head>
<body>
<div class="sheet">

  <div class="wordmark">EVERLIGHT VENTURES -- OFF-MARKET DEAL SHEET</div>
  <h1>{addr}</h1>
  <div style="color:#666;">{city}, {state} -- {bedrooms}BR / {bathrooms}BA / {sqft:,} sqft</div>
  <div class="badge">UNDER CONTRACT -- ASSIGNABLE</div>

  <div class="price-box">
    <div class="label">CASH BUYER PRICE</div>
    <div class="number">{_money(money_chain.buyer_ask)}</div>
    <div style="color:#888;font-size:13px;">All-in: {_money(money_chain.buyer_ask + money_chain.repair)} (purchase + rehab)</div>
  </div>

  <h2 style="font-family:Playfair Display,serif;color:#D4A843;border-bottom:2px solid #D4A843;padding-bottom:6px;">The math</h2>
  <table>
    <tr><td class="k">ARV (after repairs)</td><td class="v">{_money(money_chain.arv)}</td></tr>
    <tr><td class="k">Purchase price (to seller via assignment)</td><td class="v">{_money(money_chain.seller_offer)}</td></tr>
    <tr><td class="k">Assignment fee (to Everlight)</td><td class="v">{_money(money_chain.assignment_fee)}</td></tr>
    <tr><td class="k">Repair estimate</td><td class="v">{_money(money_chain.repair)}</td></tr>
    <tr><td class="k">Buyer's all-in</td><td class="v">{_money(money_chain.buyer_all_in)}</td></tr>
    <tr><td class="k">FLIP profit (resell at ARV)</td><td class="v green">{_money(money_chain.flip_buyer_profit)}</td></tr>
    <tr><td class="k">BRRRR refi pulls out (75% LTV)</td><td class="v green">{_money(money_chain.brrrr_pulled_out)}</td></tr>
  </table>

  <h2 style="font-family:Playfair Display,serif;color:#D4A843;border-bottom:2px solid #D4A843;padding-bottom:6px;">The terms</h2>
  <table>
    <tr><td class="k">EMD required</td><td class="v">$1,000-$5,000 to title</td></tr>
    <tr><td class="k">Inspection period</td><td class="v">14 days</td></tr>
    <tr><td class="k">Close timeline</td><td class="v">14-21 days from EMD</td></tr>
    <tr><td class="k">POF required</td><td class="v">Yes -- bank statement or hard-money LOI</td></tr>
    <tr><td class="k">Title company</td><td class="v">Buyer's choice OR our preferred GA title co</td></tr>
  </table>

  <h2 style="font-family:Playfair Display,serif;color:#D4A843;border-bottom:2px solid #D4A843;padding-bottom:6px;">Contact</h2>
  <p>
    <strong>Hammer Knox</strong> -- Disposition, Everlight Ventures<br>
    <a href="mailto:henry@everlightventures.io" style="color:#D4A843;">henry@everlightventures.io</a><br>
    (404) 800-4380<br>
    <strong>Reply YES + POF for first look. First credible bid + POF wins.</strong>
  </p>

  <div class="footer">
    Off-market deal. Never going to MLS. Assignable contract held by Everlight Ventures.
    Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d")}.
  </div>
</div>
</body></html>"""


def _build_blurb_text(deal, money_chain) -> str:
    """Plain-text deal blurb for FB groups, Slack, marketplace forms."""
    addr = getattr(deal, "property_address", "") or ""
    city = getattr(deal, "property_city", "") or ""
    state = getattr(deal, "property_state", "") or ""
    bedrooms = getattr(deal, "property_bedrooms", 3) or 3
    bathrooms = getattr(deal, "property_bathrooms", 1) or 1
    sqft = getattr(deal, "property_sqft", 1200) or 1200

    return f"""OFF-MARKET DEAL -- {city}, {state}

{addr}
{bedrooms}BR / {bathrooms}BA / {sqft:,} sqft

PRICE: {_money(money_chain.buyer_ask)} (your all-in: {_money(money_chain.buyer_ask + money_chain.repair)} including ~{_money(money_chain.repair)} rehab)
ARV: {_money(money_chain.arv)}
FLIP profit: {_money(money_chain.flip_buyer_profit)}
BRRRR refi pulls: {_money(money_chain.brrrr_pulled_out)}

Assignable contract. EMD $1k-$5k to title. 14-day inspection. 14-21d close.
First credible cash bid + POF wins.

DM or email henry@everlightventures.io
(404) 800-4380

#{state.lower()}wholesale #offmarket #cashbuyer"""


def dispatch(deal_id: str, send_to: Optional[str] = None) -> dict:
    """Generate one-pager + blurb + (optional) email to marketplace intake."""
    from broker_ops.models import Deal
    try:
        deal = Deal.objects.get(id=deal_id)
    except Deal.DoesNotExist:
        return {"error": f"deal not found: {deal_id}"}

    # Build money chain via pipeline_report
    try:
        from pipeline_report import _build_money_chain
        # Pipeline report uses PropertyLead, not Deal. Bridge:
        class _LeadShim:
            id = getattr(deal, "id", "")
            address = getattr(deal, "property_address", "")
            city = getattr(deal, "property_city", "")
            state = getattr(deal, "property_state", "")
            estimated_arv = float(getattr(deal, "estimated_arv", 0) or 0)
            estimated_repair = float(getattr(deal, "estimated_repair", 0) or 0)
            sqft = getattr(deal, "property_sqft", 1200)
            owner_name = ""
        mc = _build_money_chain(_LeadShim())
    except Exception as exc:
        return {"error": f"money chain build failed: {exc}"}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"deal_{deal_id}_{ts}"

    one_pager = _build_one_pager_html(deal, mc)
    one_pager_path = OUT_DIR / f"{base}.html"
    one_pager_path.write_text(one_pager)

    blurb = _build_blurb_text(deal, mc)
    blurb_path = OUT_DIR / f"{base}.txt"
    blurb_path.write_text(blurb)

    sent = []
    if send_to:
        intakes = MARKETPLACE_INTAKES.get(send_to)
        if intakes:
            try:
                from branded_mailer import send_branded_email  # type: ignore
                # Wrap the blurb + one-pager link in an email
                addr = getattr(deal, "property_address", "")
                body_html = (
                    f"<p>Off-market deal -- assignable contract held by Everlight Ventures.</p>"
                    f"<p><strong>One-page deal sheet:</strong> "
                    f"<a href='{PUBLIC_BASE}/{base}.html'>{PUBLIC_BASE}/{base}.html</a></p>"
                    f"<pre style='font-family:monospace;background:#fafafa;padding:12px;'>{blurb}</pre>"
                )
                result = send_branded_email(
                    to=intakes,
                    subject=f"Off-market: {addr} -- {_money(mc.buyer_ask)} -- assignable",
                    content_html=body_html,
                    plain_text_fallback=blurb,
                    agent_name="Hammer Knox",
                    agent_title="Disposition",
                    agent_email="henry@everlightventures.io",
                    from_name="Hammer Knox",
                    from_email="henry@everlightventures.io",
                    budget_category="vip_reply",
                )
                sent.append({"marketplace": send_to, "to": intakes, "ok": result.ok, "error": result.error})
            except Exception as exc:
                sent.append({"marketplace": send_to, "ok": False, "error": str(exc)})

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "deal_id": str(deal_id),
        "buyer_ask": mc.buyer_ask,
        "one_pager_url": f"{PUBLIC_BASE}/{base}.html",
        "blurb_url": f"{PUBLIC_BASE}/{base}.txt",
        "marketplace_sends": sent,
    }
    LEDGER.open("a").write(json.dumps(record) + "\n")

    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["one-pager", "blurb", "email-maxdispo", "dispatch"])
    ap.add_argument("--deal-id", required=True)
    ap.add_argument("--marketplace", default="")
    args = ap.parse_args()

    if args.cmd in ("one-pager", "blurb", "dispatch"):
        result = dispatch(args.deal_id, send_to=args.marketplace or None)
    elif args.cmd == "email-maxdispo":
        result = dispatch(args.deal_id, send_to="maxdispo")

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
