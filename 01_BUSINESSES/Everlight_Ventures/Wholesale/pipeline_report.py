"""pipeline_report -- generate a per-lead Everlight money-flow HTML report.

For every lead the bots touch (cold email, cold text, warm follow-up, AI call),
this module produces a stand-alone HTML page Rich can open at any time to see:

  - Where this specific lead sits in the 10-step pipeline
  - The full money chain (seller, you, buyer, exit math, title co)
  - The exact pitch + offer that went out
  - The source data (live Zillow stats, owner intel, pain points)
  - Three buyer-exit paths (FLIP / BRRRR / HOLD) so Rich knows what the buyer is buying

Output:
  /home/opc/hive_reports/pipelines/<lead_id>_<ts>.html
  Served at http://127.0.0.1:2200/reports/pipelines/<file.html>

The "stacked potential commissions" view (`generate_index()`) lists all
generated reports with sortable columns so Rich can see his entire potential-
revenue pipeline in one place.

Branding:
  - Everlight gold (#D4A843) + dark (#0A0A0A) palette from report_template.py
  - Playfair Display for big numbers, Inter for body
  - Each money block boxed with gold borders (mirrors the ASCII boxes Rich asked for)

Wired into:
  - active_outreach.py cold_email_batch -- one report per send
  - cold_text_consent_ladder -- one report per text
  - bidding_war_engine.trigger -- updated report when deal moves to contract

Usage:
  from pipeline_report import generate_pipeline_html
  url = generate_pipeline_html(lead, status="cold_pitch_sent",
                                pitch_subject="Cash offer for X: $Y, 14-day close")
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/wholesale",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale",
    "/home/opc/wholesale/pitches",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pipeline_report")

REPORT_DIR = Path("/home/opc/hive_reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
# Django's report_detail view serves /reports/<safe_hash>/ from this dir.
# Filenames must use a 'pipeline_' prefix so they're distinguishable +
# discoverable in the report list.
PIPELINE_PREFIX = "pipeline_"
PUBLIC_BASE = "http://127.0.0.1:2200/reports"


# Pipeline stages (the 10-step close flow). Each stage gets a colored badge.
PIPELINE_STAGES = [
    ("cold_pitch_sent",      "Cold pitch sent",         "#888"),
    ("warm_followup_sent",   "Warm follow-up sent",     "#888"),
    ("cold_text_sent",       "Cold text sent",          "#888"),
    ("consent_granted",      "Consent granted",         "#D4A843"),
    ("ai_call_completed",    "AI call completed",       "#D4A843"),
    ("seller_replied",       "Seller replied",          "#D4A843"),
    ("offer_sent_firm",      "Firm offer sent",         "#7a5c00"),
    ("psa_signed",           "PSA signed -- LOCKED",    "#0F7B3D"),
    ("bid_war_open",         "Bid war open",            "#7a5c00"),
    ("bid_war_won",          "Buyer won bid",           "#0F7B3D"),
    ("title_in_escrow",      "Title in escrow",         "#0F7B3D"),
    ("closed_funded",        "CLOSED -- you got paid",  "#0F7B3D"),
    ("dead",                 "Dead lead",               "#C33"),
]


def _money(n: float) -> str:
    return f"${n:,.0f}"


def _stage_color(stage: str) -> str:
    for code, _label, color in PIPELINE_STAGES:
        if code == stage:
            return color
    return "#888"


def _stage_label(stage: str) -> str:
    for code, label, _color in PIPELINE_STAGES:
        if code == stage:
            return label
    return stage


@dataclass
class MoneyChain:
    """The full chain for one lead. All values in dollars."""
    arv: float = 0.0
    repair: float = 0.0
    seller_offer: float = 0.0
    buyer_ask: float = 0.0
    assignment_fee: float = 0.0
    seller_closing_costs: float = 0.0
    buyer_holding_costs: float = 0.0
    title_company_fee: float = 0.0

    @property
    def seller_net(self) -> float:
        return self.seller_offer - self.seller_closing_costs

    @property
    def buyer_all_in(self) -> float:
        return self.buyer_ask + self.repair + self.buyer_holding_costs

    @property
    def your_take(self) -> float:
        return self.assignment_fee

    @property
    def flip_resell_at_arv(self) -> float:
        return self.arv

    @property
    def flip_agent_commission(self) -> float:
        return self.arv * 0.06

    @property
    def flip_concessions(self) -> float:
        return self.arv * 0.018

    @property
    def flip_buyer_net(self) -> float:
        return self.arv - self.flip_agent_commission - self.flip_concessions

    @property
    def flip_buyer_profit(self) -> float:
        return self.flip_buyer_net - self.buyer_all_in

    @property
    def brrrr_refi_proceeds(self) -> float:
        """75% LTV refi at ARV."""
        return self.arv * 0.75

    @property
    def brrrr_pulled_out(self) -> float:
        return max(0.0, self.brrrr_refi_proceeds - self.buyer_all_in)

    @property
    def brrrr_left_in(self) -> float:
        return max(0.0, self.buyer_all_in - self.brrrr_refi_proceeds)


def _estimate_monthly_rent(arv: float) -> float:
    """Rough rent-to-value heuristic: 0.7% monthly of ARV (~8.4% gross yearly)."""
    return arv * 0.007


def _build_money_chain(lead) -> MoneyChain:
    """Build the money chain from a Django PropertyLead.

    Uses the dynamic assignment fee (lowball_pricer._compute_assignment_fee) so
    each lead's commission scales with ARV + distress + motivation tier.
    """
    arv = float(getattr(lead, "estimated_arv", 0) or 0)
    repair = float(getattr(lead, "estimated_repair", 0) or 0)

    # Try the lowball pricer with DYNAMIC fee (assignment_fee=None triggers it)
    seller_offer = 0.0
    buyer_ask = 0.0
    assignment_fee = 15000.0  # fallback only
    try:
        from lowball_pricer import build_offer_for_lead
        pack = build_offer_for_lead(lead, assignment_fee=None, use_dynamic_fee=True)
        seller_offer = float(pack["the_number"])
        buyer_ask = float(pack["buyer_ask"])
        # Pull the dynamic fee out of the pack
        assignment_fee = float(pack.get("fee_breakdown", {}).get("assignment_fee", 15000.0))
        if not arv:
            arv = float(pack["offer"]["arv"])
        if not repair:
            repair = float(pack["offer"]["repair"])
    except Exception:
        pass

    # Fallback rough math if pricer didn't load
    if arv == 0:
        arv = 200000
    if repair == 0:
        sqft = int(getattr(lead, "sqft", 0) or 1200)
        repair = sqft * 25
    if seller_offer == 0:
        seller_offer = max(5000, arv * 0.65 - repair - assignment_fee)
        buyer_ask = seller_offer + assignment_fee

    return MoneyChain(
        arv=arv,
        repair=repair,
        seller_offer=seller_offer,
        buyer_ask=buyer_ask,
        assignment_fee=assignment_fee,
        seller_closing_costs=seller_offer * 0.015,
        buyer_holding_costs=4000,
        title_company_fee=1200,
    )


def _box(title: str, lines: list[tuple[str, str, str]],
         border_color: str = "#D4A843", body_bg: str = "#fff",
         label_color: str = "#7a5c00") -> str:
    """Render one money-flow box. lines = list of (label, value, color)."""
    rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;color:#666;font-size:13px;'>{label}</td>"
        f"<td style='padding:6px 12px;text-align:right;font-family:SF Mono,Monaco,monospace;"
        f"font-size:14px;color:{value_color};font-weight:600;'>{value}</td>"
        f"</tr>"
        for label, value, value_color in lines
    )
    return (
        f"<div style='border:2px solid {border_color};margin:12px 0;background:{body_bg};'>"
        f"<div style='background:{border_color};color:#0A0A0A;padding:8px 14px;"
        f"font-weight:700;letter-spacing:2px;text-transform:uppercase;font-size:12px;'>"
        f"{title}</div>"
        f"<table style='width:100%;border-collapse:collapse;'>"
        f"{rows}"
        f"</table>"
        f"</div>"
    )


def _exit_paths_html(mc: MoneyChain) -> str:
    """The 3 buyer-exit paths."""
    monthly_rent = _estimate_monthly_rent(mc.arv)
    annual_rent = monthly_rent * 12
    annual_noi = annual_rent * 0.55  # 45% expense load (vacancy, repairs, taxes, insurance, mgmt)
    cap_hold = (annual_noi / mc.buyer_all_in * 100) if mc.buyer_all_in else 0
    cap_brrrr = (annual_noi / max(mc.brrrr_left_in, 1) * 100) if mc.brrrr_left_in > 0 else 9999

    flip_html = _box("Path A -- FLIP (sell at retail in 4-6 months)", [
        ("Resell at ARV", _money(mc.flip_resell_at_arv), "#0A0A0A"),
        ("- Agent commission (6%)", f"-{_money(mc.flip_agent_commission)}", "#C33"),
        ("- Concessions / closing", f"-{_money(mc.flip_concessions)}", "#C33"),
        ("Buyer net at sale", _money(mc.flip_buyer_net), "#0A0A0A"),
        ("Buyer's all-in cost", f"-{_money(mc.buyer_all_in)}", "#C33"),
        ("BUYER FLIP PROFIT", _money(mc.flip_buyer_profit), "#0F7B3D"),
    ], border_color="#7a5c00")

    brrrr_html = _box("Path B -- BRRRR (refi + rent forever)", [
        ("Refi at 75% ARV", _money(mc.brrrr_refi_proceeds), "#0A0A0A"),
        ("Buyer pulls out (refi - all-in)", _money(mc.brrrr_pulled_out), "#0F7B3D"),
        ("Buyer leaves in deal", _money(mc.brrrr_left_in), "#7a5c00"),
        ("Monthly rent (est)", f"{_money(monthly_rent)}/mo", "#0A0A0A"),
        ("Annual NOI (after 45% expenses)", _money(annual_noi), "#0A0A0A"),
        ("Cap rate on left-in capital", f"{cap_brrrr:.1f}%", "#0F7B3D"),
    ], border_color="#7a5c00")

    hold_html = _box("Path C -- HOLD (long-term rental, no refi)", [
        ("Monthly rent (est)", f"{_money(monthly_rent)}/mo", "#0A0A0A"),
        ("Annual NOI (after 45% expenses)", _money(annual_noi), "#0A0A0A"),
        ("Cap rate on full all-in", f"{cap_hold:.1f}%", "#0F7B3D"),
    ], border_color="#7a5c00")

    return (
        f"<h2 style='font-family:Playfair Display,Georgia,serif;color:#D4A843;"
        f"border-bottom:2px solid #D4A843;padding-bottom:6px;margin-top:30px;'>"
        f"Buyer's exit -- 3 paths to profit</h2>"
        f"<p style='color:#666;font-size:13px;'>This is what the buyer is actually buying. "
        f"They pay you {_money(mc.buyer_ask)} for the contract because at least one of these "
        f"paths makes them more than that in profit.</p>"
        f"{flip_html}{brrrr_html}{hold_html}"
    )


def generate_pipeline_html(
    lead,
    status: str = "cold_pitch_sent",
    pitch_subject: str = "",
    pitch_body_preview: str = "",
    extra_notes: str = "",
) -> dict:
    """Generate the per-lead pipeline report HTML.

    Returns {"path": str, "url": str, "filename": str, "money_chain": dict}.
    """
    mc = _build_money_chain(lead)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    lead_id = str(getattr(lead, "id", "noid"))
    addr = getattr(lead, "address", "(no address)") or "(no address)"
    addr_short = addr.split(",")[0].strip() if "," in addr else addr
    owner = getattr(lead, "owner_name", "") or "(unknown owner)"
    state = getattr(lead, "state", "") or ""
    city = getattr(lead, "city", "") or ""

    # Owner intel + pains for context
    intel_block = ""
    pains_block = ""
    try:
        from pitch_generator import _identify_seller_pain, _live_stats
        from owner_intel import build_owner_intel
        stats = _live_stats(lead)
        pains = _identify_seller_pain(lead, stats) if _identify_seller_pain else []
        intel = build_owner_intel(lead) if build_owner_intel else None
        if pains:
            pain_items = "".join(
                f"<li>{p.one_liner}</li>" for p in pains[:4]
            )
            pains_block = (
                f"<h2 style='font-family:Playfair Display,Georgia,serif;color:#D4A843;"
                f"border-bottom:2px solid #D4A843;padding-bottom:6px;'>Pain points identified</h2>"
                f"<ul style='font-size:14px;color:#444;line-height:1.7;'>{pain_items}</ul>"
            )
        if intel:
            intel_block = (
                f"<h2 style='font-family:Playfair Display,Georgia,serif;color:#D4A843;"
                f"border-bottom:2px solid #D4A843;padding-bottom:6px;'>Owner intel</h2>"
                f"<table style='width:100%;font-size:13px;color:#444;'>"
                f"<tr><td style='padding:4px 8px;color:#999;'>Motivation tier</td>"
                f"<td><strong>{intel.motivation_tier}/5</strong></td></tr>"
                f"<tr><td style='padding:4px 8px;color:#999;'>Voice register</td>"
                f"<td>{intel.register}</td></tr>"
                f"<tr><td style='padding:4px 8px;color:#999;'>Primary pain hook</td>"
                f"<td>{intel.primary_pain_hook}</td></tr>"
                f"<tr><td style='padding:4px 8px;color:#999;'>Distance from property</td>"
                f"<td>{intel.owner_distance_miles_est} mi</td></tr>"
                f"</table>"
            )
    except Exception:
        pass

    # Money chain blocks
    seller_box = _box(f"SELLER -- {owner[:30]}", [
        ("Receives at close", _money(mc.seller_offer), "#D4A843"),
        ("- Closing costs (~1.5%)", f"-{_money(mc.seller_closing_costs)}", "#C33"),
        ("NET in their pocket", _money(mc.seller_net), "#0F7B3D"),
        ("Time invested", "~3 hours", "#666"),
        ("Their return", "Cash certain, 14 days, $0 commission", "#666"),
    ])

    you_box = _box("YOU -- Everlight Ventures DBA", [
        ("Buyer pays you (via title)", _money(mc.buyer_ask), "#D4A843"),
        ("- You pay seller", f"-{_money(mc.seller_offer)}", "#C33"),
        ("ASSIGNMENT FEE TO YOU", _money(mc.your_take), "#0F7B3D"),
        ("Time invested", "~62 minutes total", "#666"),
        ("Cost", f"{_money(1000)} EMD risk + ~30 min phone", "#666"),
    ], border_color="#0F7B3D", body_bg="#f7faf5")

    buyer_box = _box("BUYER -- cash investor (winning bidder)", [
        ("Pays at close (purchase + assignment)", _money(mc.buyer_ask), "#0A0A0A"),
        ("Pays for rehab (next 60-90 days)", _money(mc.repair), "#0A0A0A"),
        ("Holding costs (taxes, ins., util.)", _money(mc.buyer_holding_costs), "#0A0A0A"),
        ("BUYER ALL-IN", _money(mc.buyer_all_in), "#7a5c00"),
    ])

    title_box = _box("TITLE COMPANY", [
        ("Receives", _money(mc.title_company_fee), "#0A0A0A"),
        ("For", "Title search + insurance + escrow + recording", "#666"),
    ])

    exit_html = _exit_paths_html(mc)

    # Pipeline status badge
    stage_color = _stage_color(status)
    stage_label = _stage_label(status)

    # Pitch preview
    pitch_html = ""
    if pitch_subject or pitch_body_preview:
        body_preview = pitch_body_preview[:600] if pitch_body_preview else ""
        pitch_html = (
            f"<h2 style='font-family:Playfair Display,Georgia,serif;color:#D4A843;"
            f"border-bottom:2px solid #D4A843;padding-bottom:6px;margin-top:30px;'>"
            f"Latest outreach</h2>"
            f"<div style='background:#fafafa;border-left:4px solid #D4A843;padding:14px;'>"
            f"<div style='color:#7a5c00;font-weight:600;font-size:11px;text-transform:uppercase;'>Subject</div>"
            f"<div style='font-size:15px;margin:6px 0 12px;'>{pitch_subject}</div>"
            f"<div style='color:#7a5c00;font-weight:600;font-size:11px;text-transform:uppercase;'>Body preview</div>"
            f"<div style='font-size:13px;color:#444;line-height:1.6;'>{body_preview}...</div>"
            f"</div>"
        )

    notes_html = ""
    if extra_notes:
        notes_html = (
            f"<div style='background:#fffacd;border-left:4px solid #D4A843;padding:14px;margin-top:18px;'>"
            f"<div style='color:#7a5c00;font-weight:600;font-size:11px;text-transform:uppercase;'>Notes</div>"
            f"<div style='font-size:13px;color:#444;margin-top:6px;'>{extra_notes}</div>"
            f"</div>"
        )

    # Build the full HTML page
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Pipeline Report -- {addr_short} -- ${mc.your_take:,.0f}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600;700&display=swap">
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #fafaf6;
         margin: 0; padding: 32px; color: #111; }}
  .wrap {{ max-width: 920px; margin: 0 auto; background: #fff;
          padding: 40px; border: 1px solid #eee; }}
  h1 {{ font-family: 'Playfair Display', Georgia, serif; color: #0A0A0A;
       margin: 0 0 4px; font-size: 32px; }}
  h2 {{ font-family: 'Playfair Display', Georgia, serif; color: #D4A843;
       border-bottom: 2px solid #D4A843; padding-bottom: 6px; margin-top: 30px; }}
  .wordmark {{ color: #D4A843; letter-spacing: 4px; font-size: 11px;
              font-weight: 600; }}
  .badge {{ display: inline-block; padding: 6px 14px; color: #fff;
           font-weight: 600; letter-spacing: 1px; font-size: 11px;
           text-transform: uppercase; }}
  .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr);
               gap: 12px; margin: 18px 0; padding: 14px; background: #fafafa; }}
  .meta-grid .item {{ font-size: 13px; }}
  .meta-grid .label {{ color: #999; font-size: 11px; text-transform: uppercase;
                      letter-spacing: 1px; }}
  .meta-grid .value {{ color: #0A0A0A; font-weight: 600; margin-top: 2px; }}
  .footer {{ margin-top: 40px; padding-top: 14px; border-top: 1px solid #ddd;
            font-size: 11px; color: #888; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="wordmark">EVERLIGHT VENTURES</div>
  <h1>Pipeline Report</h1>
  <div style="color:#666;margin-bottom:6px;">{addr_short} -- {city}, {state}</div>
  <div class="badge" style="background:{stage_color};">{stage_label}</div>

  <div class="meta-grid">
    <div class="item">
      <div class="label">Owner</div>
      <div class="value">{owner[:40]}</div>
    </div>
    <div class="item">
      <div class="label">Lead ID</div>
      <div class="value">{lead_id}</div>
    </div>
    <div class="item">
      <div class="label">Property</div>
      <div class="value">{addr}</div>
    </div>
    <div class="item">
      <div class="label">ARV (after repairs)</div>
      <div class="value">{_money(mc.arv)}</div>
    </div>
    <div class="item">
      <div class="label">Repair estimate</div>
      <div class="value">{_money(mc.repair)}</div>
    </div>
    <div class="item">
      <div class="label">YOUR potential commission</div>
      <div class="value" style="color:#0F7B3D;font-size:20px;">{_money(mc.your_take)}</div>
    </div>
  </div>

  {pitch_html}
  {notes_html}

  <h2>The full money chain</h2>
  <p style="color:#666;font-size:13px;">If this lead closes, this is exactly where every dollar goes.</p>
  {seller_box}
  {you_box}
  {buyer_box}
  {title_box}

  {exit_html}

  {pains_block}
  {intel_block}

  <div class="footer">
    Generated {datetime.now(timezone.utc).isoformat()} UTC.
    Everlight Ventures pipeline report.
    Re-renders automatically on each new outreach touch + when the deal moves through stages.
  </div>
</div>
</body></html>"""

    filename = f"{PIPELINE_PREFIX}{lead_id}_{ts}.html"
    out_path = REPORT_DIR / filename
    out_path.write_text(html)
    safe_hash = filename.replace(".html", "")

    return {
        "path": str(out_path),
        "url": f"{PUBLIC_BASE}/{safe_hash}/",  # Django report_detail serves this
        "filename": filename,
        "lead_id": lead_id,
        "stage": status,
        "your_take": mc.your_take,
        "money_chain": {
            "arv": mc.arv,
            "repair": mc.repair,
            "seller_offer": mc.seller_offer,
            "buyer_ask": mc.buyer_ask,
            "assignment_fee": mc.assignment_fee,
            "buyer_all_in": mc.buyer_all_in,
            "flip_buyer_profit": mc.flip_buyer_profit,
        },
    }


def generate_index() -> dict:
    """Build the master 'all my potential commissions stacked' index page.

    Lists every pipeline report ever generated, sortable by stage + your_take,
    with a total at the top.
    """
    reports = []
    total_potential = 0.0
    funded_total = 0.0
    for f in sorted(REPORT_DIR.glob(f"{PIPELINE_PREFIX}*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
        if "index" in f.name:
            continue
        try:
            content = f.read_text()
            # Crude extraction of the commission number from the title
            import re
            m = re.search(r"\$([\d,]+)", content[:500])
            commission = float(m.group(1).replace(",", "")) if m else 0
            stage_match = re.search(r"badge.*?>([^<]+)<", content)
            stage = stage_match.group(1).strip() if stage_match else "?"
            addr_match = re.search(r"<title>Pipeline Report -- ([^-]+)--", content)
            addr = addr_match.group(1).strip() if addr_match else f.name
            reports.append({
                "filename": f.name,
                "addr": addr,
                "commission": commission,
                "stage": stage,
                "url": f"{PUBLIC_BASE}/{f.name.replace('.html', '')}/",
                "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
            total_potential += commission
            if "CLOSED" in stage.upper():
                funded_total += commission
        except Exception:
            continue

    rows = "".join(
        f"<tr>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'><a href='{r['url']}' style='color:#D4A843;text-decoration:none;'>{r['addr'][:60]}</a></td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #eee;font-size:12px;color:#666;'>{r['stage']}</td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;font-family:SF Mono,Monaco,monospace;color:#0F7B3D;font-weight:600;'>${r['commission']:,.0f}</td>"
        f"<td style='padding:8px 12px;border-bottom:1px solid #eee;font-size:11px;color:#999;'>{r['mtime']}</td>"
        f"</tr>"
        for r in reports
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Everlight Pipeline -- All Potential Commissions</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;600&display=swap">
<style>
  body {{ font-family: 'Inter', sans-serif; background: #fafaf6; padding: 32px; color: #111; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; background: #fff; padding: 40px; border: 1px solid #eee; }}
  h1 {{ font-family: 'Playfair Display', serif; color: #0A0A0A; margin: 0; }}
  .wordmark {{ color: #D4A843; letter-spacing: 4px; font-size: 11px; font-weight: 600; }}
  .totals {{ display: flex; gap: 18px; margin: 24px 0; }}
  .total-card {{ flex: 1; padding: 18px; background: #0A0A0A; color: #D4A843; }}
  .total-card .label {{ color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; }}
  .total-card .value {{ font-family: 'Playfair Display', serif; font-size: 36px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
  th {{ text-align: left; padding: 10px 12px; background: #fafafa; font-size: 11px;
       text-transform: uppercase; letter-spacing: 1px; color: #666; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="wordmark">EVERLIGHT VENTURES</div>
  <h1>Pipeline -- All Potential Commissions</h1>
  <p style="color:#666;">Every lead the bots have touched, with the assignment fee waiting on each one.</p>

  <div class="totals">
    <div class="total-card">
      <div class="label">Total potential</div>
      <div class="value">${total_potential:,.0f}</div>
      <div style="color:#888;font-size:12px;margin-top:4px;">{len(reports)} leads in pipeline</div>
    </div>
    <div class="total-card" style="background:#0F7B3D;color:#fff;">
      <div class="label" style="color:#cfeed3;">Funded (closed)</div>
      <div class="value" style="color:#fff;">${funded_total:,.0f}</div>
      <div style="color:#cfeed3;font-size:12px;margin-top:4px;">in your bank already</div>
    </div>
  </div>

  <table>
    <thead><tr>
      <th>Property</th>
      <th>Stage</th>
      <th style="text-align:right;">Your commission</th>
      <th>Last touch</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <div style="margin-top:30px;padding-top:14px;border-top:1px solid #ddd;font-size:11px;color:#888;">
    Generated {datetime.now(timezone.utc).isoformat()} UTC.
    Refresh this page after each cron cycle to see new reports appear.
  </div>
</div>
</body></html>"""

    index_path = REPORT_DIR / "pipeline_index.html"
    index_path.write_text(html)
    return {
        "path": str(index_path),
        "url": f"{PUBLIC_BASE}/pipeline_index/",
        "total_potential": total_potential,
        "funded_total": funded_total,
        "lead_count": len(reports),
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["one", "all-leads", "index"])
    ap.add_argument("--lead-id", default="")
    ap.add_argument("--state", default="GA")
    args = ap.parse_args()

    if args.cmd == "one" and args.lead_id:
        from broker_ops.models import PropertyLead
        lead = PropertyLead.objects.get(id=args.lead_id)
        result = generate_pipeline_html(lead)
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd == "all-leads":
        from broker_ops.models import PropertyLead
        n = 0
        for lead in PropertyLead.objects.filter(state=args.state)[:50]:
            try:
                generate_pipeline_html(lead)
                n += 1
            except Exception as exc:
                log.warning(f"failed for lead {lead.id}: {exc}")
        idx = generate_index()
        print(json.dumps({"reports_generated": n, "index": idx}, indent=2, default=str))
    elif args.cmd == "index":
        result = generate_index()
        print(json.dumps(result, indent=2, default=str))
