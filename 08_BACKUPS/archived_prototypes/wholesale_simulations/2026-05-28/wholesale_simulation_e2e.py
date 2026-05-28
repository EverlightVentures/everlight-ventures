"""
Wholesale End-to-End Simulation -- the whole pipeline in Rich's inbox.

Picks one real property from the parsed Memphis inventory and walks every
stage of the deal: scout -> seller outreach -> seller negotiation arc ->
contract -> internal handoff -> buyer pitch (Chris @ Mid-South) -> buyer
negotiation arc -> assignment -> closing -> commission. ~20 emails, all
through branded_mailer with the real personas.

All sends route to 1m.rich.gee@gmail.com via the RESEND_ALLOW_OWNER=1
escape hatch (auditable one-off, not production). The halt is also lifted
for this script only -- never written to .env.

Run:
    python3 wholesale_simulation_e2e.py
    # or with a different parcel:
    python3 wholesale_simulation_e2e.py 026063__00013.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Lift halt + owner-block for THIS script only. Never modifies .env.
os.environ["WHOLESALE_OUTBOUND_HALT"] = "0"
os.environ["RESEND_ALLOW_OWNER"] = "1"

# Load real secrets if available (RESEND_API_KEY, etc.)
SECRETS = Path("/root/.config/everlight/secrets.env")
if SECRETS.exists():
    for line in SECRETS.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            # Don't re-set the halt -- keep our local override
            if k in {"WHOLESALE_OUTBOUND_HALT", "ERADICATION_GATE_REQUIRED"}:
                continue
            os.environ.setdefault(k, v)

sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
from branded_mailer import send_branded_email

# ---------------------------------------------------------------------------
TO = "1m.rich.gee@gmail.com"
PARSED_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed")
LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/wholesale_simulation_e2e.log")
TRANSCRIPT = Path(f"/mnt/sdcard/AA_MY_DRIVE/_state/wholesale_simulation_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
DELAY_SEC = 6  # pace sends so Gmail orders correctly

# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------
PERSONAS = {
    "piper":    ("Piper Reeves",    "piper@everlightventures.io",    "Outreach Specialist"),
    "henry":    ("Henry Hammond",   "henry@everlightventures.io",    "Senior Negotiator"),
    "marvin":   ("Marvin Cohen",    "marvin@everlightventures.io",   "Closing Coordinator"),
    "vaughn":   ("Vaughn Sterling", "vaughn@everlightventures.io",   "Senior Partner"),
    "marquise": ("Marquise Reed",   "marquise@everlightventures.io", "Memphis Acquisitions Lead (internal)"),
    "sim":      ("Simulation Bot",  "simulation@everlightventures.io", "Simulated Counterparty Replies"),
}

# ---------------------------------------------------------------------------
def pick_parcel(arg: str | None) -> dict:
    if arg:
        p = PARSED_DIR / arg if not arg.startswith("/") else Path(arg)
    else:
        # Default: first vacant-lot Memphis parcel with absentee owner
        for fp in sorted(PARSED_DIR.glob("*.json")):
            d = json.loads(fp.read_text())
            if (
                d.get("is_vacant_lot")
                and "MEMPHIS" in (d.get("property_address_full") or "")
                and "streubel" not in json.dumps(d).lower()
                and "municipalfirm" not in json.dumps(d).lower()
            ):
                return d
        # fallback
        return json.loads(sorted(PARSED_DIR.glob("*.json"))[0].read_text())
    return json.loads(p.read_text())


def fmt_money(n) -> str:
    try:
        return f"${int(n):,}"
    except Exception:
        return f"${n}"


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def transcript_append(stage: int, persona_key: str, subject: str, summary: str, html_preview: str = "") -> None:
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    name, email, title = PERSONAS[persona_key]
    with TRANSCRIPT.open("a") as fh:
        fh.write(f"\n## Stage {stage:02d} -- {name} ({title})\n\n")
        fh.write(f"**From:** {name} <{email}>  \n")
        fh.write(f"**Subject:** {subject}  \n\n")
        fh.write(f"**Summary:** {summary}\n\n")
        if html_preview:
            fh.write(f"<details><summary>HTML preview</summary>\n\n```html\n{html_preview[:600]}\n```\n\n</details>\n\n")
        fh.write("---\n")


# ---------------------------------------------------------------------------
def send(stage: int, persona_key: str, subject: str, html_body: str, summary: str) -> bool:
    name, email, title = PERSONAS[persona_key]
    tagged_subject = f"[SIM #{stage:02d}] {subject}"

    log(f"Stage {stage:02d} | {name} -> {TO} | {subject}")
    result = send_branded_email(
        to=TO,
        subject=tagged_subject,
        content_html=html_body,
        from_name=name,
        from_email=email,
        reply_to=email,
        agent_name=name,
        agent_title=title,
        agent_email=email,
        budget_category="system",  # bypass marketing-budget cap for sim
        recipient_state="",
        lead_type="simulation",
        state_disclaimer=False,
    )

    transcript_append(stage, persona_key, subject, summary, html_body)

    if not result.ok:
        log(f"  FAILED: {result.error}")
        return False
    log(f"  sent: id={result.message_id}")
    time.sleep(DELAY_SEC)
    return True


# ---------------------------------------------------------------------------
def build_outreach_html(parcel: dict, owner_first: str) -> str:
    addr = parcel.get("property_address_full", "")
    return f"""
<p>Hey {owner_first},</p>
<p>I came across your property at <strong>{addr}</strong>. I'm a private buyer working with a small group acquiring residential land in Memphis this quarter.</p>
<p>Records show you've held the parcel since {parcel.get('last_sale_year', '2011')}. If you've ever thought about selling, here's what I can offer:</p>
<ul>
  <li>All cash, no financing contingencies</li>
  <li>Close in as little as 7 days or on your timeline</li>
  <li>As-is, no clean-up, no surveys required from your side</li>
  <li>I cover all closing costs</li>
</ul>
<p>If you're open to hearing a number, just reply and I'll send a written offer within the hour.</p>
<p>No pressure either way. Just wanted to make sure you had the option on the table.</p>
"""


def build_simulated_reply(persona_speaker: str, body_lines: list[str], from_addr: str) -> str:
    inner = "".join(f"<p>{ln}</p>" for ln in body_lines)
    return f"""
<div style="background:#1a1a1a;border-left:4px solid #D4AF37;padding:16px 24px;margin:16px 0;">
  <div style="color:#D4AF37;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Simulated Incoming Reply</div>
  <div style="color:#999;font-size:13px;margin-bottom:12px;">From: <strong>{persona_speaker}</strong> &lt;{from_addr}&gt;</div>
  <div style="color:#E8E8E8;">
    {inner}
  </div>
</div>
<p style="color:#999;font-size:13px;font-style:italic;">↑ Above is what the {persona_speaker} would have sent. Our next move follows below.</p>
"""


# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    parcel = pick_parcel(argv[1] if len(argv) > 1 else None)
    addr = parcel.get("property_address_full", "unknown")
    owner = parcel.get("owner_name", "Owner")
    owner_first = owner.split()[0].title() if owner != "Owner" else "there"

    # Pricing fundamentals
    land_apr = parcel.get("land_appraisal_usd", 5400)
    bldg_apr = parcel.get("building_appraisal_usd", 0)
    total_apr = land_apr + bldg_apr
    last_sale = parcel.get("last_sale_price_usd", 1800)
    arv = max(total_apr * 1.6, 25000)  # very rough ARV for narrative
    repair_budget = 8000  # land prep
    moa_seller = round(total_apr * 0.65)   # our offer to seller (lowball anchor)
    moa_seller_final = round(total_apr * 0.85)  # eventual deal price
    moa_buyer = moa_seller_final + 3500    # assignment fee built in
    fee = moa_buyer - moa_seller_final

    log(f"PROPERTY: {addr}")
    log(f"OWNER:    {owner} (mailing: {parcel.get('owner_mailing_street', '')})")
    log(f"PRICING:  appraisal={fmt_money(total_apr)} seller_open={fmt_money(moa_seller)} "
        f"seller_close={fmt_money(moa_seller_final)} buyer={fmt_money(moa_buyer)} fee={fmt_money(fee)}")

    # Transcript header
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT.write_text(f"""# Wholesale Simulation Transcript

**Run:** {datetime.now().isoformat()}
**Property:** {addr}
**Owner of record:** {owner}
**Owner mailing:** {parcel.get('owner_mailing_street','')} {parcel.get('owner_mailing_city_state_zip','')}
**Appraisal:** {fmt_money(total_apr)} (land {fmt_money(land_apr)} + bldg {fmt_money(bldg_apr)})
**Last sale:** {fmt_money(last_sale)} on {parcel.get('last_sale_date','')}
**Years owned:** {2026 - int(parcel.get('last_sale_year', 2011))}

## Pricing Plan
- Initial seller offer: {fmt_money(moa_seller)}
- Seller agreement: {fmt_money(moa_seller_final)}
- Buyer (Chris @ Mid-South) price: {fmt_money(moa_buyer)}
- **Everlight assignment fee: {fmt_money(fee)}**

---
""")

    # =====================================================================
    # SELLER SIDE
    # =====================================================================

    # Stage 01 -- Marquise internal scout note
    send(1, "marquise",
         f"[INTERNAL] New target: {addr}",
         f"""
<p>Team -- new HIGH-priority target out of the Memphis parsed batch.</p>
<table>
<tr><th>Property</th><td>{addr}</td></tr>
<tr><th>Owner</th><td>{owner}</td></tr>
<tr><th>Mailing</th><td>{parcel.get('owner_mailing_street','')}, {parcel.get('owner_mailing_city_state_zip','')}</td></tr>
<tr><th>Type</th><td>{'VACANT LOT' if parcel.get('is_vacant_lot') else parcel.get('property_class','')}</td></tr>
<tr><th>Held since</th><td>{parcel.get('last_sale_year','')}</td></tr>
<tr><th>Last sale</th><td>{fmt_money(last_sale)}</td></tr>
<tr><th>Appraisal</th><td>{fmt_money(total_apr)}</td></tr>
</table>
<p><strong>Signal profile:</strong> absentee owner (Collierville mailing on a Memphis lot), 15 years held, vacant land. Classic "I forgot I owned it" candidate.</p>
<p><strong>Pitch hook:</strong> we'll position as a private land buyer doing a Memphis sweep this quarter. Anchor at {fmt_money(moa_seller)}, room to walk up to {fmt_money(moa_seller_final)} if needed.</p>
<p>Handing off to Piper for first touch.</p>
""",
         "Marquise scouts the property and briefs the team internally.")

    # Stage 02 -- Piper outreach #1
    send(2, "piper",
         f"Your property at {addr}",
         build_outreach_html(parcel, owner_first),
         "Piper's first cold outreach to the seller -- warm, no pressure, cash buyer angle.")

    # Stage 03 -- simulated seller reply 1
    send(3, "sim",
         f"Re: Your property at {addr}",
         build_simulated_reply(owner, [
             "Saw your email. Whats your offer? I havent thought about that property in years honestly.",
             "Send me a number. If its serious I'll consider it."
         ], f"{owner_first.lower()}@example.com"),
         f"Simulated owner ({owner}) replies asking for a number. This is the green light.")

    # Stage 04 -- Henry takes over with first formal offer (anchor low)
    send(4, "henry",
         f"Re: Your property at {addr} -- offer attached",
         f"""
<p>Hi {owner_first} -- Henry here, I work with Piper on the acquisition side.</p>
<p>I appreciate the quick reply. Here is what we can do today on <strong>{addr}</strong>:</p>
<table>
<tr><th>Offer</th><td><strong>{fmt_money(moa_seller)}</strong></td></tr>
<tr><th>Terms</th><td>All cash, no financing</td></tr>
<tr><th>Close window</th><td>7 to 14 days, your call</td></tr>
<tr><th>As-is</th><td>Yes -- no surveys, no clean-up on your side</td></tr>
<tr><th>Closing costs</th><td>We cover</td></tr>
</table>
<p>I know that may feel below what you had in mind. We are factoring in the back-tax exposure, the cost of clearing title on a 15-year-held lot, and the fact that vacant Memphis residential lots are moving slowly in the current market.</p>
<p>If the number is workable, I can have a one-page purchase contract in your hand within the hour. If you need to think on it, that is fine -- I will check back in 48 hours.</p>
<p>What does work for you?</p>
""",
         f"Henry sends the formal anchor offer at {fmt_money(moa_seller)}. Low on purpose -- room to negotiate up.")

    # Stage 05 -- simulated seller pushback
    send(5, "sim",
         f"Re: Your property at {addr} -- offer attached",
         build_simulated_reply(owner, [
             f"Henry that is way too low. I paid {fmt_money(last_sale)} for it and the county has it at {fmt_money(total_apr)}.",
             f"I would need at least {fmt_money(round(total_apr * 0.95))} to even talk seriously."
         ], f"{owner_first.lower()}@example.com"),
         f"Seller pushes back at {fmt_money(round(total_apr * 0.95))}, anchoring high. Classic counter.")

    # Stage 06 -- Henry counter
    send(6, "henry",
         f"Re: Your property at {addr} -- meeting in the middle",
         f"""
<p>Hear you, {owner_first}. The appraisal is the appraisal, but here is the honest read:</p>
<ul>
  <li>That parcel has not had a recorded sale at appraisal value in this neighborhood in the last 24 months.</li>
  <li>If you list it traditional, a 6 percent agent commission + 30-90 days on market + buyer financing risk easily eats {fmt_money(round(total_apr * 0.15))}.</li>
  <li>I can close in 7 days, cash, no agent, no commission, no contingency.</li>
</ul>
<p>I can move our number up to <strong>{fmt_money(moa_seller_final)}</strong>. That is my best offer this week.</p>
<p>If that works, I will have Marvin (our closing coordinator) send a one-page purchase contract today. If not -- no hard feelings, and I will not bother you again.</p>
""",
         f"Henry counters at {fmt_money(moa_seller_final)} -- the eventual seller-close price. Walks-away framing.")

    # Stage 07 -- seller accepts
    send(7, "sim",
         f"Re: Your property at {addr} -- meeting in the middle",
         build_simulated_reply(owner, [
             f"Alright, {fmt_money(moa_seller_final)} works. Send the contract.",
             "Just make sure closing is clean and the title work is handled."
         ], f"{owner_first.lower()}@example.com"),
         f"Seller accepts at {fmt_money(moa_seller_final)}. Deal locked.")

    # Stage 08 -- Marvin sends contract
    send(8, "marvin",
         f"Purchase contract -- {addr}",
         f"""
<p>Hi {owner_first}, Marvin Cohen here -- I handle the closing side for Everlight Ventures.</p>
<p>Henry briefed me on the agreement: <strong>{fmt_money(moa_seller_final)}</strong> all cash, 7-14 day close, as-is, we cover closing costs.</p>
<p>Attached you will find the one-page purchase contract. A few notes so nothing is hidden:</p>
<ul>
  <li>Earnest money deposit: $500 wired to <strong>Mid-South Title Company</strong> (escrow agent) within 24 hours of countersign. Refundable per contract terms.</li>
  <li>Title work runs through Mid-South Title -- they are licensed in TN, and they handle every closing we do in Shelby County.</li>
  <li><strong>Equitable interest disclosure (TN SB 909):</strong> Everlight Ventures may assign this contract to a third-party investor before closing. If we do, an assignment disclosure goes to you in writing and you keep your right to walk if anything material changes.</li>
  <li>Closing date target: <strong>{(datetime.now() + timedelta(days=10)).strftime('%B %d, %Y')}</strong>. Mid-South Title will coordinate signing.</li>
</ul>
<p>If you can sign and return today, we can have EMD wired by tomorrow and a closing date locked.</p>
""",
         "Marvin sends the formal purchase contract with TN SB 909 disclosure (equitable-interest pre-disclosure).")

    # Stage 09 -- seller signs
    send(9, "sim",
         f"Re: Purchase contract -- {addr}",
         build_simulated_reply(owner, [
             "Signed contract attached. Good to go.",
             "Send me the wire instructions for Mid-South and lets get it closed."
         ], f"{owner_first.lower()}@example.com"),
         "Seller signs the contract. Now we have equitable interest, ready to assign to Chris.")

    # =====================================================================
    # INTERNAL HANDOFF
    # =====================================================================

    # Stage 10 -- Marquise internal: deal locked, pivot to buyer side
    send(10, "marquise",
         f"[INTERNAL] Deal locked: {addr} at {fmt_money(moa_seller_final)} -- pivot to Chris",
         f"""
<p>Team -- Stage 1 closed. {owner_first} signed at <strong>{fmt_money(moa_seller_final)}</strong>.</p>
<p>EMD ($500) wires to Mid-South Title today. Closing target: <strong>{(datetime.now() + timedelta(days=10)).strftime('%B %d, %Y')}</strong>.</p>
<p>Equitable interest is ours. Time to find the end buyer and structure the assignment fee.</p>
<table>
<tr><th>Seller close</th><td>{fmt_money(moa_seller_final)}</td></tr>
<tr><th>Target buyer price</th><td>{fmt_money(moa_buyer)}</td></tr>
<tr><th>Assignment fee target</th><td><strong>{fmt_money(fee)}</strong></td></tr>
</table>
<p>Best fit: <strong>Chris Ulander @ Mid-South Homebuyers</strong>. He picks up 20-30 vacant Memphis lots a year for buy-and-hold. Marvin -- you have the warmest rapport with him from the last 3 deals. Run the pitch.</p>
<p>If Chris balks, fall back to backup buyers in the Cleveland-Memphis JV channel.</p>
""",
         "Internal handoff: deal locked, pivoting to buyer side. Chris @ Mid-South is the target.")

    # =====================================================================
    # BUYER SIDE
    # =====================================================================

    # Stage 11 -- Marvin → Chris (pitch)
    send(11, "marvin",
         f"New Memphis lot -- {addr} (assignment available)",
         f"""
<p>Chris -- got another one for you.</p>
<p><strong>{addr}</strong> -- vacant residential, 0.086 acres, held by the same family since 2011. We have an executed purchase contract at {fmt_money(moa_seller_final)} closing on <strong>{(datetime.now() + timedelta(days=10)).strftime('%B %d, %Y')}</strong> through Mid-South Title.</p>
<p>Quick stats:</p>
<table>
<tr><th>County appraisal</th><td>{fmt_money(total_apr)}</td></tr>
<tr><th>Last sale</th><td>{fmt_money(last_sale)} (2011)</td></tr>
<tr><th>Type</th><td>Vacant residential lot</td></tr>
<tr><th>Title status</th><td>Mid-South pulling now, clean per public records</td></tr>
</table>
<p>Assignment price: <strong>{fmt_money(moa_buyer)}</strong> -- our fee is {fmt_money(fee)}, you pay {fmt_money(moa_seller_final)} to seller via Mid-South escrow.</p>
<p>Closes the same day we have you on title with Mid-South. If you want it, I can have the assignment agreement to you within the hour. Yes or no?</p>
""",
         f"Marvin pitches Chris @ Mid-South at {fmt_money(moa_buyer)} (assignment price = seller price + {fmt_money(fee)} fee).")

    # Stage 12 -- Chris asks for full numbers
    send(12, "sim",
         f"Re: New Memphis lot -- {addr}",
         build_simulated_reply("Chris Ulander @ Mid-South Homebuyers", [
             "Marvin send me the full numbers + comps + a screenshot of the assessor page.",
             "Whats your fee? I assume thats baked in."
         ], "chris@midsouthhomebuyers.com"),
         "Chris asks for the full deal sheet. Buyer due diligence kicks in.")

    # Stage 13 -- Marvin sends full deal sheet
    send(13, "marvin",
         f"Deal sheet -- {addr}",
         f"""
<p>Chris -- here is the complete picture. Nothing hidden.</p>
<h2>Property</h2>
<table>
<tr><th>Address</th><td>{addr}</td></tr>
<tr><th>Parcel ID</th><td>{parcel.get('parcel_id','')}</td></tr>
<tr><th>Type</th><td>VACANT LAND (RESIDENTIAL)</td></tr>
<tr><th>Lot size</th><td>{parcel.get('land_sqft','')} sqft ({parcel.get('acres','')} acres)</td></tr>
<tr><th>Subdivision</th><td>{parcel.get('subdivision','')}</td></tr>
<tr><th>Neighborhood</th><td>{parcel.get('neighborhood_number','')}</td></tr>
</table>
<h2>Numbers</h2>
<table>
<tr><th>County land appraisal</th><td>{fmt_money(land_apr)}</td></tr>
<tr><th>County total appraisal</th><td>{fmt_money(total_apr)}</td></tr>
<tr><th>Owner of record</th><td>{owner}</td></tr>
<tr><th>Held since</th><td>{parcel.get('last_sale_year','')} ({fmt_money(last_sale)})</td></tr>
<tr><th>Our contract price (to seller)</th><td>{fmt_money(moa_seller_final)}</td></tr>
<tr><th>Your assignment price</th><td><strong>{fmt_money(moa_buyer)}</strong></td></tr>
<tr><th>Our fee</th><td>{fmt_money(fee)} (baked in)</td></tr>
</table>
<h2>Closing</h2>
<ul>
<li>Closing on <strong>{(datetime.now() + timedelta(days=10)).strftime('%B %d, %Y')}</strong> through Mid-South Title (your usual)</li>
<li>You wire {fmt_money(moa_buyer)} day-of-close. {fmt_money(moa_seller_final)} to seller, {fmt_money(fee)} to Everlight.</li>
<li>Title comes to you direct (we never take title)</li>
</ul>
<h2>Public source</h2>
<p>Assessor: <a href="{parcel.get('source_url','')}">{parcel.get('source_url','')}</a></p>
""",
         "Marvin sends Chris the full branded deal sheet with parcel, numbers, closing terms, source link.")

    # Stage 14 -- Chris pushes back on price
    send(14, "sim",
         f"Re: Deal sheet -- {addr}",
         build_simulated_reply("Chris Ulander @ Mid-South Homebuyers", [
             f"Marvin {fmt_money(fee)} is high for a vacant lot. I usually do {fmt_money(2500)} on these.",
             f"I can do {fmt_money(moa_seller_final + 2500)} all in. Take it or leave it."
         ], "chris@midsouthhomebuyers.com"),
         f"Chris counters down to {fmt_money(moa_seller_final + 2500)} (cutting our fee from {fmt_money(fee)} to $2.5k).")

    # Stage 15 -- Henry takes over buyer negotiation
    send(15, "henry",
         f"Re: Deal sheet -- {addr} -- splitting the difference",
         f"""
<p>Chris, Henry here -- Marvin tagged me in.</p>
<p>I hear you on the vacant-lot ceiling. Two things to weigh against $2.5k flat:</p>
<ol>
<li>This is your seventh deal with us this year. We have always brought you clean title, on-time close, and a real seller we already negotiated through pushback. That has a real value vs. you hunting these solo.</li>
<li>The {fmt_money(fee)} ask includes the EMD ($500 already at Mid-South), the title pre-pull cost, and the 9 days of negotiation that got the seller from "leave me alone" to "send the contract."</li>
</ol>
<p>I will meet you in the middle: <strong>{fmt_money(moa_seller_final + 3000)}</strong> all in. Our fee becomes {fmt_money(3000)} -- still inside your "vacant lot" budget, still worth our time. Closing same date, same Mid-South Title, same clean assignment.</p>
<p>Yes / no, Chris?</p>
""",
         f"Henry splits the difference: {fmt_money(moa_seller_final + 3000)} all in (fee comes to $3k).")

    # Stage 16 -- Chris accepts
    send(16, "sim",
         f"Re: Deal sheet -- {addr} -- splitting the difference",
         build_simulated_reply("Chris Ulander @ Mid-South Homebuyers", [
             f"Fine. {fmt_money(moa_seller_final + 3000)} it is.",
             "Send the assignment agreement. Im in."
         ], "chris@midsouthhomebuyers.com"),
         f"Chris accepts at {fmt_money(moa_seller_final + 3000)}. Buyer side locked. Fee = $3,000.")

    # Stage 17 -- Vaughn senior signoff + assignment contract
    send(17, "vaughn",
         f"Assignment of contract -- {addr}",
         f"""
<p>Chris -- Vaughn Sterling here. Final sign-off on the assignment.</p>
<p>Attached is the assignment of real estate contract for <strong>{addr}</strong>. Three things to flag:</p>
<ol>
<li><strong>Assignment fee:</strong> {fmt_money(3000)} payable to Everlight Ventures at close from your wire to Mid-South Title.</li>
<li><strong>Seller disclosure (TN SB 909):</strong> {owner_first} was disclosed at contract signing that we may assign. They acknowledged in writing. This is the assignment.</li>
<li><strong>Title:</strong> comes to you (or your designated entity) direct from {owner}. We never appear on title. Mid-South Title coordinates.</li>
</ol>
<p>Sign and return -- we close on <strong>{(datetime.now() + timedelta(days=10)).strftime('%B %d, %Y')}</strong>. As always, appreciate the trust.</p>
""",
         f"Vaughn (senior partner) delivers the final assignment contract with $3k fee.")

    # Stage 18 -- Chris signs assignment
    send(18, "sim",
         f"Re: Assignment of contract -- {addr}",
         build_simulated_reply("Chris Ulander @ Mid-South Homebuyers", [
             "Signed. Wiring on close day.",
             "Mid-South has my entity info already from the last one."
         ], "chris@midsouthhomebuyers.com"),
         "Chris signs the assignment. Both sides locked. Just need to close.")

    # =====================================================================
    # CLOSING
    # =====================================================================

    # Stage 19 -- Marvin coordinates closing
    send(19, "marvin",
         f"Closing coordination -- {addr}",
         f"""
<p>Team + Mid-South Title -- final coordination on <strong>{addr}</strong>.</p>
<table>
<tr><th>Close date</th><td>{(datetime.now() + timedelta(days=10)).strftime('%A, %B %d, %Y')}</td></tr>
<tr><th>Seller</th><td>{owner} -- wire {fmt_money(moa_seller_final)} from Mid-South escrow</td></tr>
<tr><th>Buyer</th><td>Chris Ulander / Mid-South Homebuyers -- wire {fmt_money(moa_seller_final + 3000)} day-of-close</td></tr>
<tr><th>Title to</th><td>Mid-South Homebuyers designated entity</td></tr>
<tr><th>Everlight fee</th><td><strong>{fmt_money(3000)}</strong> from buyer wire</td></tr>
</table>
<p>Mid-South Title: please confirm settlement statement and recording timing. Let me know if you need anything from our side before {(datetime.now() + timedelta(days=10)).strftime('%B %d')}.</p>
""",
         "Marvin coordinates the closing logistics with Mid-South Title (escrow + recording).")

    # Stage 20 -- Marvin: closing complete + commission booked
    send(20, "marquise",
         f"[INTERNAL] DEAL CLOSED: {addr} -- ${3000} commission booked",
         f"""
<p>Team -- <strong>Deal closed.</strong></p>
<p>{addr} recorded today through Mid-South Title. {owner} got their {fmt_money(moa_seller_final)}, Chris got the deed, Everlight banked <strong>{fmt_money(3000)}</strong>.</p>
<table>
<tr><th>Recorded</th><td>{(datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')}</td></tr>
<tr><th>Buyer wire</th><td>{fmt_money(moa_seller_final + 3000)}</td></tr>
<tr><th>To seller</th><td>{fmt_money(moa_seller_final)}</td></tr>
<tr><th>Everlight fee</th><td><strong>{fmt_money(3000)}</strong></td></tr>
<tr><th>Cycle time (first touch to close)</th><td>~12 days</td></tr>
</table>
<p>Stats for the dashboard:</p>
<ul>
<li>Seller negotiation rounds: 3 (open -> counter -> close)</li>
<li>Buyer negotiation rounds: 3 (pitch -> counter -> meet in middle)</li>
<li>Personas touched: Marquise (scout), Piper (outreach), Henry (negotiation x2), Marvin (contract + closing), Vaughn (senior signoff)</li>
<li>Cumulative time-to-close from first email: 12 days</li>
</ul>
<p>This is what the pipeline looks like end-to-end. Now imagine 5 of these a week.</p>
""",
         "DEAL CLOSED. $3,000 commission booked. Marquise sends the internal close report.")

    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Transcript: {TRANSCRIPT}")
    print(f"Log: {LOG}")
    print(f"All 20 emails should be in {TO} within ~2 minutes (pacing delay = {DELAY_SEC}s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
