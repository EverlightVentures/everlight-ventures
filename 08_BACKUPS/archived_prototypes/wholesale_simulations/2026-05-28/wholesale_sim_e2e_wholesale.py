#!/usr/bin/env python3
"""
wholesale_sim_e2e.py -- the REVAMP end-to-end deal simulation. LOCAL ONLY. No Resend,
no real sends. Runs the full lifecycle on one TN address through the NEW stack, validates
the deal against Chris's REAL buy-box, and renders a styled branded HTML showcase you can open.

Stack: tn_deal_tracker (source) -> email enrich (sim) -> chris_buy_box validation ->
llm_compose (persona + market intel + brand) -> conversation_memory -> pipeline_phase_manager
-> Henry negotiate -> contract_renderer (SB909 PSA) -> disposition to Chris -> assignment + payout.

Output: _state transcript + a gold-branded HTML at 09_DASHBOARD/reports/ (auto-opened).
  python3 wholesale_sim_e2e.py
"""
from __future__ import annotations

import json, sys, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
sys.path.insert(0, str(WH / "scripts"))
sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
sys.path.insert(0, str(ROOT / "06_DEVELOPMENT/everlight_os/intel_center"))
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))

TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
TRANSCRIPT = ROOT / "_state" / f"wholesale_sim_e2e_{TS}.md"
SHOWCASE = ROOT / "09_DASHBOARD" / "reports" / f"deal_simulation_{TS}.html"

# In-band lead that actually FITS Chris's buy-box (residential, 1900-1985, $30k-120k).
LEAD = {
    "parcel_id": "026032  00030", "property_address": "1298 ENGLEWOOD ST, MEMPHIS, TN 38107",
    "owner_name": "Ray Vaughn", "land_use": "SINGLE FAMILY", "year_built": 1912,
    "total_appraisal_usd": 38400, "owner_state": "GA",  # absentee
    "email": "ray.vaughn@example.com",  # SIM only
}
BUYER = {"name": "Chris", "firm": "Mid-South Homebuyers", "email": "leads@midsouthhomebuyers.com"}
errors: list = []
T: list = []
SAMPLES: dict = {}  # stage -> rendered content for the HTML showcase


def line(s=""): T.append(s)
def stage(n, title): line(f"\n## Stage {n}: {title}\n")
def check(label, ok, detail=""):
    line(f"- [{'PASS' if ok else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")
    if not ok: errors.append(f"{label}: {detail}")


def buy_box() -> dict:
    try:
        return json.loads((WH / "config" / "chris_buy_box.json").read_text())
    except Exception:
        return {}


def validate_buybox(lead: dict, box: dict) -> list:
    """Return [(criterion, ok, detail)] -- the deal must meet HIS list."""
    p = box.get("property", {})
    a = lead["total_appraisal_usd"]; y = lead["year_built"]; lu = lead["land_use"].upper()
    return [
        ("Residential (not vacant/commercial)", "SINGLE FAMILY" in lu or "RESIDENTIAL" in lu, lu),
        (f"Appraisal in band ${p.get('min_appraisal_usd'):,}-${p.get('max_appraisal_usd'):,}",
         p.get("min_appraisal_usd", 0) <= a <= p.get("max_appraisal_usd", 9e9), f"${a:,}"),
        (f"Year built {p.get('min_year_built')}-{p.get('max_year_built')}",
         p.get("min_year_built", 0) <= y <= p.get("max_year_built", 9999), str(y)),
    ]


def compose(persona, ctx):
    try:
        import llm_compose
        b = llm_compose.compose(persona, ctx, property_facts=LEAD)
        return b, ("llm" if b else "none")
    except Exception as e:
        return None, f"err:{type(e).__name__}"


def run():
    box = buy_box()
    line(f"# Wholesale Deal Simulation (REVAMP, LOCAL/DRY-RUN) -- {TS}")
    line(f"*No Resend. Lead {LEAD['property_address']} | {LEAD['owner_name']} (absentee {LEAD['owner_state']}) "
         f"| appraisal ${LEAD['total_appraisal_usd']:,}*")

    stage(1, "SOURCE")
    check("parcel sourced", True, LEAD["property_address"])
    stage(2, "ENRICH (email, digital-only, SIM)")
    check("email resolved", True, f"{LEAD['email']} [SIMULATED]")

    stage(3, "QUALIFY -- does it meet CHRIS's buy-box?")
    bb = validate_buybox(LEAD, box)
    for crit, ok, det in bb:
        check(f"buy-box: {crit}", ok, det)
    appr = LEAD["total_appraisal_usd"]
    exit_pct = box.get("exit", {}).get("all_in_target_pct_of_appraisal", 0.55)
    min_margin = box.get("exit", {}).get("min_margin_to_us_usd", 3000)
    chris_all_in = round(exit_pct * appr)            # most Chris pays all-in
    our_fee = max(min_margin, 4000)                   # our assignment fee
    assign_price = chris_all_in                       # buyer pays this
    seller_agreed = assign_price - our_fee            # we contract seller here
    opening = seller_agreed - 2000                    # open below, negotiate up
    deal_fits = (assign_price <= chris_all_in) and (our_fee >= min_margin) and all(ok for _, ok, _ in bb)
    check("DEAL MEETS CHRIS'S CRITERIA", deal_fits,
          f"all-in ${assign_price:,} <= 55% of appraisal (${chris_all_in:,}); our margin ${our_fee:,} >= ${min_margin:,}")
    line(f"  exit math: Chris all-in target {int(exit_pct*100)}% of ${appr:,} = ${chris_all_in:,}")
    line(f"  -> assign to Chris ${assign_price:,} | our fee ${our_fee:,} | contract seller ~${seller_agreed:,} (open ${opening:,})")
    SAMPLES["buybox"] = bb + [("DEAL FITS CHRIS", deal_fits, f"assign ${assign_price:,}, fee ${our_fee:,}")]
    SAMPLES["econ"] = {"appraisal": appr, "opening": opening, "seller_agreed": seller_agreed,
                       "assign_price": assign_price, "our_fee": our_fee, "exit_pct": exit_pct}

    try:
        import conversation_memory as cm
    except Exception:
        cm = None

    stage(4, "OUTREACH -- Piper touch-1 (llm)")
    pctx = {"name": "Ray", "role": "seller", "subject": "your place on Englewood",
            "facts_we_know": [f"owns {LEAD['property_address']}, lives out of state in {LEAD['owner_state']}, long hold"],
            "must_answer": [], "we_already_asked": [], "our_commitments": [],
            "next_action": "warm intro, ask if open to selling, no pressure"}
    pbody, peng = compose("piper_reeves", pctx)
    check("Piper outreach composed", bool(pbody), f"engine={peng}")
    if cm: cm.record(LEAD["email"], "out", pbody or "", persona="piper_reeves", name="Ray", role="seller", phase="contacted")
    SAMPLES["piper"] = pbody or "[template fallback]"
    line("\n**SAMPLE Piper -> seller:**\n```\n" + (pbody or "") + "\n```")

    stage(5, "SELLER REPLY (sim)")
    sreply = ("Yeah I have thought about offloading it. It is an old rental and I am out in Georgia now. "
              "It needs work. What can you actually do on it?")
    if cm: cm.record(LEAD["email"], "in", sreply, name="Ray", role="seller", phase="engaged")
    check("reply recorded", bool(cm))
    SAMPLES["seller_reply"] = sreply
    line(f"\n**Seller (Ray):**\n> {sreply}")

    stage(6, "NEGOTIATE (seller) -- Henry, MULTI-ROUND (shared negotiation engine)")
    import negotiation
    ceiling = seller_agreed                       # the most we will pay (our walk-away)
    sthread = []
    base = {"name": "Ray", "role": "seller", "subject": "your place on Englewood",
            "facts_we_know": ["old rental that needs work", f"owner in {LEAD['owner_state']}", "open to offloading"],
            "we_already_asked": [], "our_commitments": ["Piper said no pressure, first conversation"]}
    # Round 1 -- Henry opens
    n1 = negotiation.seller_next(1, opening, ceiling)
    c1 = {**base, "must_answer": ["What can you actually do on it?"],
          "next_action": f"open as-is cash at ${n1['offer']:,}, we handle repairs",
          "negotiation": {"our_offer": n1["offer"], "their_counter": None, "action": n1["action"], "round": 1, "walk_away": ceiling}}
    b1, e1 = compose("henry_hammond", c1); sthread.append(("Henry -> Ray (round 1)", b1 or ""))
    if cm: cm.record(LEAD["email"], "out", b1 or "", persona="henry_hammond", phase="negotiating")
    # Seller counters high
    s_counter = round(appr * 0.6)
    sthread.append(("Ray -> us (counter)", f"That is low. I was thinking closer to ${s_counter:,}."))
    if cm: cm.record(LEAD["email"], "in", f"That is low, I want ${s_counter:,}", phase="negotiating")
    # Round 2 -- Henry counters toward the walk-away
    n2 = negotiation.seller_next(2, opening, ceiling, their_counter=s_counter)
    c2 = {**base, "must_answer": [f"seller wants ${s_counter:,}"], "personas_already_introduced": ["henry_hammond"],
          "next_action": f"counter at ${n2['offer']:,}, present it as a strong cash deal, hold near walk-away",
          "negotiation": {"our_offer": n2["offer"], "their_counter": s_counter, "action": n2["action"], "round": 2, "walk_away": ceiling}}
    b2, e2 = compose("henry_hammond", c2); sthread.append(("Henry -> Ray (round 2)", b2 or ""))
    if cm: cm.record(LEAD["email"], "out", b2 or "", persona="henry_hammond", phase="negotiating")
    final = negotiation.seller_next(3, opening, ceiling, their_counter=ceiling)
    seller_agreed = final["offer"]
    sthread.append(("Ray -> us (accept)", f"Alright, ${seller_agreed:,} works. Send the paperwork."))
    check("seller negotiation reached agreement at or under walk-away", seller_agreed <= ceiling,
          f"agreed ${seller_agreed:,} | walk-away ${ceiling:,} | engine={e1}/{e2}")
    SAMPLES["seller_thread"] = sthread
    line(f"\n*Seller negotiation: {len(sthread)} turns -> agreed ${seller_agreed:,} (held the walk-away).*")

    stage(7, "CONTRACT -- SB909 PSA (equitable interest + assignment disclosure)")
    psa_ok, psa_html = False, ""
    try:
        from osint_api.contract_renderer import render_psa, load_global_config
        meta = {"deal_key": "SIM_ENGLEWOOD", "property_address": LEAD["property_address"],
                "parcel_id": LEAD["parcel_id"], "year_built": LEAD["year_built"],
                "seller_name": LEAD["owner_name"], "seller_email": LEAD["email"],
                "buyer_name": "Everlight Ventures Wholesale Acquisitions, LLC",
                "final_to_seller": seller_agreed, "opening_to_seller": opening,
                "emd_usd": 500, "inspection_days": 10, "test_mode": True}
        psa_html = render_psa(meta, load_global_config())
        psa_ok = "assign" in psa_html.lower() and "equitable interest" in psa_html.lower()
    except Exception as e:
        psa_html = f"renderer error: {e}"
    check("SB909 PSA rendered", psa_ok, "equitable interest + assignment fee disclosure present" if psa_ok else psa_html[:80])
    SAMPLES["psa"] = psa_html if psa_ok else ""

    stage(8, "SELLER SIGNS (e-sign, sim)")
    check("seller signature", True, "Documenso [SIMULATED]")

    stage(9, "DISPOSITION + buyer negotiation -- Marvin <-> Chris, MULTI-ROUND")
    check("assignment price fits Chris exit", assign_price <= chris_all_in, f"${assign_price:,} <= ${chris_all_in:,}")
    bfloor = seller_agreed + min_margin       # lowest assignment that still pays us min margin
    bthread = []
    bbase = {"name": "Chris", "role": "buyer", "subject": "Memphis SFR under contract -- Englewood",
             "facts_we_know": ["buys Memphis SFR cash", "deals to leads@midsouthhomebuyers.com", "all-in ~55% of value"],
             "we_already_asked": [], "our_commitments": ["only send deals that fit his box"]}
    negotiation  # already imported in stage 6
    nb1 = negotiation.buyer_next(1, assign_price, bfloor)
    bc1 = {**bbase, "must_answer": [],
           "next_action": f"present 1298 Englewood under contract, assignment ${assign_price:,} (~{int(exit_pct*100)}% of ${appr:,})",
           "negotiation": {"our_offer": assign_price, "their_counter": None, "action": "hold", "round": 1, "walk_away": bfloor}}
    m1, me1 = compose("marvin_cohen", bc1); bthread.append(("Marvin -> Chris (pitch)", m1 or ""))
    if cm: cm.record(BUYER["email"], "out", m1 or "", persona="marvin_cohen", name="Chris", role="buyer", phase="buyer_matched")
    chris_counter = assign_price - 2000
    bthread.append(("Chris -> us (counter)", f"Tight on this one. I can do ${chris_counter:,}."))
    if cm: cm.record(BUYER["email"], "in", f"I can do ${chris_counter:,}", name="Chris", role="buyer", phase="buyer_matched")
    nb2 = negotiation.buyer_next(2, assign_price, bfloor, their_counter=chris_counter)
    bc2 = {**bbase, "must_answer": [f"Chris wants ${chris_counter:,}"], "personas_already_introduced": ["marvin_cohen"],
           "next_action": f"hold at ${nb2['offer']:,}, frame it as a clean strong deal, never below our floor",
           "negotiation": {"our_offer": nb2["offer"], "their_counter": chris_counter, "action": nb2["action"], "round": 2, "walk_away": bfloor}}
    m2, me2 = compose("marvin_cohen", bc2); bthread.append(("Marvin -> Chris (hold)", m2 or ""))
    if cm: cm.record(BUYER["email"], "out", m2 or "", persona="marvin_cohen", phase="buyer_matched")
    assign_final = nb2["offer"]; our_fee = assign_final - seller_agreed
    bthread.append(("Chris -> us (accept)", f"Deal. ${assign_final:,}. Send the assignment."))
    check("buyer negotiation closed >= our floor", assign_final >= bfloor, f"assign ${assign_final:,} | floor ${bfloor:,} | engine={me1}/{me2}")
    check("our margin >= minimum", our_fee >= min_margin, f"fee ${our_fee:,} >= ${min_margin:,}")
    SAMPLES["buyer_thread"] = bthread
    SAMPLES["econ"].update({"assign_price": assign_final, "our_fee": our_fee, "seller_agreed": seller_agreed})
    line(f"\n*Buyer negotiation -> assign ${assign_final:,}, our fee ${our_fee:,}.*")

    stage(10, "BUYER SIGNS ASSIGNMENT (sim)")
    check("assignment signed", True, f"{BUYER['name']} @ ${assign_price:,} [SIMULATED]")

    stage(11, "CLOSE + PAYOUT")
    line(f"  Seller paid ${seller_agreed:,} | Chris pays ${assign_final:,}")
    line(f"  **Operator payout (assignment fee): ${our_fee:,}** (settlement-statement line item, SB909)")
    check("commission booked", our_fee > 0, f"${our_fee:,}")

    stage(12, "VERIFY + REMEMBER")
    check("no broken seams", len(errors) == 0, f"{len(errors)} error(s)")
    if errors:
        line("\n### Errors flagged:")
        for e in errors: line(f"  - {e}")

    TRANSCRIPT.write_text("\n".join(T))
    _showcase()
    try:
        import rex_master_pipeline as r
        r.log_blinko(f"E2E sim {TS} -- 1298 Englewood (fits Chris box)",
                     f"12 stages, {len(errors)} errors. Payout ${our_fee:,}. Showcase {SHOWCASE.name}. #hive/wholesale #hive/sim")
    except Exception:
        pass
    return {"transcript": str(TRANSCRIPT), "showcase": str(SHOWCASE), "errors": errors,
            "payout": our_fee, "seller_agreed": seller_agreed, "assign_price": assign_price,
            "fits_chris": SAMPLES["buybox"][-1][1]}


def _email_card(sender, to, subj, body):
    body_html = (body or "").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
    return (f'<div style="border:1px solid #1A1A1A;border-left:3px solid #D4AF37;background:#0d0d0d;'
            f'padding:18px 22px;margin:14px 0;border-radius:6px;">'
            f'<div style="color:#888;font-size:12px;margin-bottom:10px;">'
            f'<b style="color:#D4AF37;">From:</b> {sender} &nbsp; <b style="color:#D4AF37;">To:</b> {to}<br>'
            f'<b style="color:#D4AF37;">Subject:</b> {subj}</div>'
            f'<div style="color:#E8E8E8;font-size:14px;line-height:1.6;">{body_html}</div></div>')


def _showcase():
    """Render the styled, openable branded HTML of the whole deal."""
    try:
        from report_template import render_report
    except Exception:
        return
    e = SAMPLES.get("econ", {})
    parts = []
    parts.append("<h2>The Deal</h2>")
    parts.append(f"<p><strong>{LEAD['property_address']}</strong> &middot; {LEAD['owner_name']} "
                 f"(absentee, {LEAD['owner_state']}) &middot; single family, built {LEAD['year_built']} "
                 f"&middot; appraisal <strong>${LEAD['total_appraisal_usd']:,}</strong></p>")
    parts.append("<h2>Does it meet Chris's buy-box?</h2><table><tr><th>Criterion</th><th>Result</th><th>Detail</th></tr>")
    for crit, ok, det in SAMPLES.get("buybox", []):
        parts.append(f"<tr><td>{crit}</td><td>{'PASS' if ok else 'FAIL'}</td><td>{det}</td></tr>")
    parts.append("</table>")
    parts.append("<h2>Economics</h2><table>"
                 f"<tr><th>Appraisal</th><td>${e.get('appraisal',0):,}</td></tr>"
                 f"<tr><th>Opening offer to seller</th><td>${e.get('opening',0):,}</td></tr>"
                 f"<tr><th>Seller agreed</th><td>${e.get('seller_agreed',0):,}</td></tr>"
                 f"<tr><th>Assign to Chris</th><td>${e.get('assign_price',0):,} (~{int(e.get('exit_pct',0)*100)}% of appraisal)</td></tr>"
                 f"<tr><th>Operator payout (assignment fee)</th><td><strong>${e.get('our_fee',0):,}</strong></td></tr></table>")
    def _quote(who, txt):
        return (f'<div style="color:#bbb;font-style:italic;padding:8px 22px;border-left:2px solid #555;'
                f'margin:8px 0;background:#111;">{who}: {txt}</div>')
    parts.append("<h2>The Conversation (actual generated content)</h2>")
    parts.append("<h3 style='color:#D4AF37'>1. Outreach</h3>")
    parts.append(_email_card("Piper Reeves &lt;piper@everlightventures.io&gt;", LEAD["owner_name"],
                             "your place on Englewood", SAMPLES.get("piper", "")))
    parts.append(_quote(LEAD["owner_name"], SAMPLES.get("seller_reply", "")))
    parts.append("<h3 style='color:#D4AF37'>2. Seller negotiation (multi-round, Henry holds the walk-away)</h3>")
    for who, txt in SAMPLES.get("seller_thread", []):
        parts.append(_email_card(who + " &lt;henry@everlightventures.io&gt;", LEAD["owner_name"],
                                 "Re: your place on Englewood", txt) if "Henry" in who else _quote(who, txt))
    parts.append("<h3 style='color:#D4AF37'>3. Buyer negotiation (multi-round, Marvin holds our floor)</h3>")
    for who, txt in SAMPLES.get("buyer_thread", []):
        parts.append(_email_card(who + " &lt;marvin@everlightventures.io&gt;", "Chris @ Mid-South",
                                 "Memphis SFR under contract -- Englewood", txt) if "Marvin" in who else _quote(who, txt))
    if SAMPLES.get("psa"):
        parts.append("<h2>Contract (TN SB909 PSA -- equitable interest + assignment-fee disclosure)</h2>")
        parts.append('<div style="border:1px solid #1A1A1A;background:#fff;color:#111;padding:10px;'
                     'max-height:420px;overflow:auto;border-radius:6px;">' + SAMPLES["psa"] + "</div>")
    parts.append(f"<h2>Result</h2><p>Errors flagged: <strong>{len(errors)}</strong>. "
                 f"Every send routes llm_compose -> branded_mailer -> sender_identity. No Resend used in this run.</p>")
    html = render_report(title="Wholesale Deal Simulation (revamp, local)",
                         content_html="\n".join(parts), agent_name="Everlight Ventures Wholesale",
                         agent_title="End-to-End Deal Engine", confidential=True)
    SHOWCASE.parent.mkdir(parents=True, exist_ok=True)
    SHOWCASE.write_text(html)


if __name__ == "__main__":
    s = run()
    print(json.dumps(s, indent=2))
    try:
        subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d",
                        f"file://{SHOWCASE}", "-t", "text/html"], timeout=10,
                       capture_output=True)
    except Exception:
        pass
