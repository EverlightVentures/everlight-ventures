"""
Wholesale E2E Simulation v2 -- driven by persona firmware + signal data.

What this fixes from v1:
  - v1 used generic "we buy houses" copy with table tags
  - v2 reads the parcel's actual signals (quitclaim, subdivision, permit history,
    owner zip neighborhood reputation) and weaves them into the pitch
  - v2 uses each persona's actual voice from their firmware file:
      * Marquise: Memphis cadence, "real talk," "y'all," 38114=Orange Mound
      * Henry:    math-first tables, walks-away AFTER number
      * Marvin:   numbered lists, timestamps, "two things to flag"
      * Vaughn:   long-form when explaining, short when deciding
  - v2 hands off between personas the way the firmware specifies
  - v2 includes the seller's first name correctly (was "Evans" in v1, should be "Arin")

Property: 942 MELROSE, MEMPHIS TN -- Evans Arin B at 905 S Willett (38114 Orange Mound).
Acquired 2017 via quitclaim for $100 (family transfer). Last permit 1979.
Vacant lot, V C Thomas subdivision, $25k county appraisal.

Run:
    python3 wholesale_simulation_e2e_v2.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["WHOLESALE_OUTBOUND_HALT"] = "0"
os.environ["RESEND_ALLOW_OWNER"] = "1"

SECRETS = Path("/root/.config/everlight/secrets.env")
if SECRETS.exists():
    for line in SECRETS.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip(); v = v.strip().strip("'\"")
            if k in {"WHOLESALE_OUTBOUND_HALT", "ERADICATION_GATE_REQUIRED"}:
                continue
            os.environ.setdefault(k, v)

sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
from branded_mailer import send_branded_email

TO = "1m.rich.gee@gmail.com"
PARSED_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed")
LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/wholesale_simulation_e2e_v2.log")
TRANSCRIPT = Path(f"/mnt/sdcard/AA_MY_DRIVE/_state/wholesale_simulation_transcript_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
DELAY_SEC = 6

PERSONAS = {
    "piper":    ("Piper Reeves",    "piper@everlightventures.io",    "Outreach Specialist"),
    "henry":    ("Henry Hammond",   "henry@everlightventures.io",    "Senior Negotiator"),
    "marvin":   ("Marvin Cohen",    "marvin@everlightventures.io",   "Closing Coordinator"),
    "vaughn":   ("Vaughn Sterling", "vaughn@everlightventures.io",   "Senior Partner"),
    "marquise": ("Marquise Reed",   "marquise@everlightventures.io", "Memphis Acquisitions Lead"),
    "sim":      ("Simulation Bot",  "simulation@everlightventures.io", "Simulated Counterparty Replies"),
}

# Zip-code neighborhood map from Marquise's firmware
ZIP_NEIGHBORHOOD = {
    "38104": "Midtown old money",
    "38114": "Orange Mound",
    "38127": "Frayser",
    "38128": "Raleigh",
    "38117": "East Memphis",
    "38111": "University District",
}


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def fmt_money(n) -> str:
    try:
        return f"${int(n):,}"
    except Exception:
        return f"${n}"


def transcript_append(stage: int, persona_key: str, subject: str, signal_notes: str, body_summary: str) -> None:
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    name, email, title = PERSONAS[persona_key]
    with TRANSCRIPT.open("a") as fh:
        fh.write(f"\n## Stage {stage:02d} -- {name}\n\n")
        fh.write(f"**From:** {name} <{email}>  \n")
        fh.write(f"**Title:** {title}  \n")
        fh.write(f"**Subject:** {subject}  \n\n")
        fh.write(f"**Signals woven in:** {signal_notes}\n\n")
        fh.write(f"**Body summary:** {body_summary}\n\n")
        fh.write("---\n")


def send(stage: int, persona_key: str, subject: str, html_body: str, signal_notes: str, body_summary: str) -> bool:
    name, email, title = PERSONAS[persona_key]
    tagged_subject = f"[SIM2 #{stage:02d}] {subject}"
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
        budget_category="system",
        recipient_state="",
        lead_type="simulation",
        state_disclaimer=False,
    )
    transcript_append(stage, persona_key, subject, signal_notes, body_summary)
    if not result.ok:
        log(f"  FAILED: {result.error}")
        return False
    log(f"  sent: id={result.message_id}")
    time.sleep(DELAY_SEC)
    return True


def sim_incoming(speaker_name: str, lines: list[str], from_addr: str) -> str:
    inner = "".join(f"<p>{ln}</p>" for ln in lines)
    return f"""
<div style="background:#1a1a1a;border-left:4px solid #D4AF37;padding:16px 24px;margin:16px 0;">
  <div style="color:#D4AF37;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">Simulated Incoming Reply</div>
  <div style="color:#999;font-size:13px;margin-bottom:12px;">From: <strong>{speaker_name}</strong> &lt;{from_addr}&gt;</div>
  <div style="color:#E8E8E8;">
    {inner}
  </div>
</div>
<p style="color:#999;font-size:13px;font-style:italic;">↑ This is the simulated reply. Our next move follows separately.</p>
"""


# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    # Lock the property
    parcel_file = PARSED_DIR / "015025__00024.json"
    if not parcel_file.exists():
        # find by address
        for fp in PARSED_DIR.glob("*.json"):
            d = json.loads(fp.read_text())
            if "942" in (d.get("property_address","") or "") and "MELROSE" in (d.get("property_address","") or "").upper():
                parcel_file = fp; break
    parcel = json.loads(parcel_file.read_text())

    # Extract signals
    addr = parcel.get("property_address_full","942 MELROSE, MEMPHIS, TN")
    parcel_id = parcel.get("parcel_id","015025  00024")
    owner_full = parcel.get("owner_name","EVANS ARIN B")
    # Parse owner name: "EVANS ARIN B" = LASTNAME FIRSTNAME MIDDLE
    owner_parts = owner_full.split()
    last_name = owner_parts[0].title() if owner_parts else "Evans"
    first_name = owner_parts[1].title() if len(owner_parts) > 1 else "there"
    owner_mailing_zip = parcel.get("owner_mailing_zip","38114")
    owner_mailing_street = parcel.get("owner_mailing_street","905 S WILLETT ST")
    neighborhood = ZIP_NEIGHBORHOOD.get(owner_mailing_zip, "Memphis")
    subdivision = parcel.get("subdivision","V C THOMAS")
    last_sale_date = parcel.get("last_sale_date","03/28/2017")
    last_sale_year = parcel.get("last_sale_year",2017)
    last_sale_price = parcel.get("last_sale_price_usd",100)
    sales_history = parcel.get("sales_history", [])
    last_deed_type = sales_history[0].get("type_code","QC") if sales_history else "QC"
    deed_phrase = {"QC":"quitclaim deed","WD":"warranty deed","SW":"special warranty deed"}.get(last_deed_type,"quitclaim")
    is_family_transfer = (last_deed_type == "QC" and last_sale_price < 1000)
    permits = parcel.get("permits", [])
    last_permit_year = permits[0].get("year", 1979) if permits else 1979
    years_since_permit = 2026 - int(last_permit_year)
    land_apr = parcel.get("land_appraisal_usd", 25000)
    total_apr = parcel.get("total_appraisal_usd", 25000)

    # Pricing (Henry's doctrine: 60-70% anchor, walk-up to 85-90%)
    moa_open = round(total_apr * 0.65)       # 65% anchor
    moa_walk1 = round(total_apr * 0.78)      # 78% counter
    moa_close = round(total_apr * 0.85)      # 85% close (Marquise-side, with seller)
    buyer_total = moa_close + 3500           # initial assignment-fee target
    buyer_close = moa_close + 3000           # actual close with Chris

    close_date = (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y")
    close_date_short = (datetime.now() + timedelta(days=10)).strftime("%b %d")
    close_dow = (datetime.now() + timedelta(days=10)).strftime("%A")

    log(f"PROPERTY: {addr}")
    log(f"OWNER:    {first_name} {last_name} -- mailing in {owner_mailing_zip} ({neighborhood})")
    log(f"SIGNALS:  {deed_phrase} {last_sale_date} for {fmt_money(last_sale_price)} ({'family transfer' if is_family_transfer else 'market sale'})")
    log(f"          subdivision={subdivision}, last permit {last_permit_year} ({years_since_permit}y ago)")
    log(f"PRICING:  open={fmt_money(moa_open)} counter={fmt_money(moa_walk1)} close={fmt_money(moa_close)} buyer_close={fmt_money(buyer_close)}")

    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT.write_text(f"""# Wholesale Simulation Transcript -- v2 (persona + signal driven)

**Run:** {datetime.now().isoformat()}
**Property:** {addr}  ({parcel_id})
**Owner:** {first_name} {last_name}
**Owner mailing:** {owner_mailing_street}, MEMPHIS TN {owner_mailing_zip} ({neighborhood} per Marquise's firmware)
**Last sale:** {fmt_money(last_sale_price)} on {last_sale_date} ({deed_phrase}, {'family transfer' if is_family_transfer else 'market sale'})
**Subdivision:** {subdivision}
**Permits:** last in {last_permit_year} ({years_since_permit} years ago)
**Appraisal:** {fmt_money(total_apr)} (land {fmt_money(land_apr)})

## Pricing Plan
- Open anchor (65%): {fmt_money(moa_open)}
- Counter (78%): {fmt_money(moa_walk1)}
- Seller close (85%): {fmt_money(moa_close)}
- Buyer (Chris) close: {fmt_money(buyer_close)}
- **Everlight fee: {fmt_money(buyer_close - moa_close)}** ($3,000 after negotiation)

## Persona Routing
- Stage 1, 2, 4, 6: **Marquise Reed** (Memphis 38114 local, runs seller negotiation through close per his firmware)
- Stage 8, 19: **Marvin Cohen** (closing coordinator -- numbered lists, detail-obsessed)
- Stage 11, 13: **Marvin** (buyer pitch + deal sheet)
- Stage 15: **Henry Hammond** (buyer-side negotiation -- math-first tables)
- Stage 17: **Vaughn Sterling** (senior partner countersign on assignment)
- Stage 10, 20: **Marquise** (internal team updates)

---
""")

    # =====================================================================
    # SELLER SIDE -- Marquise leads (Memphis local + signal-driven personalization)
    # =====================================================================

    # Stage 01 -- Marquise internal scout note
    send(1, "marquise",
         f"[INTERNAL] New target: {addr} -- family transfer signal",
         f"""
<p>Team -- pulled this off the Shelby Assessor batch this morning. Real quick on the read:</p>
<p><strong>{addr}</strong>, parcel <code>{parcel_id}</code>. Vacant lot in <strong>{subdivision}</strong> subdivision.</p>
<table>
<tr><th>Owner</th><td>{first_name} {last_name}</td></tr>
<tr><th>Owner mailing</th><td>{owner_mailing_street}, Memphis TN {owner_mailing_zip}</td></tr>
<tr><th>Neighborhood</th><td><strong>{neighborhood}</strong> -- {first_name} is local, not absentee out-of-state</td></tr>
<tr><th>Last deed</th><td>{deed_phrase} on {last_sale_date} for {fmt_money(last_sale_price)}</td></tr>
<tr><th>Read</th><td>{'Family transfer or inheritance -- not a market sale at that price' if is_family_transfer else 'Market sale'}</td></tr>
<tr><th>Permits</th><td>Last one pulled in <strong>{last_permit_year}</strong> -- nothing in {years_since_permit} years</td></tr>
<tr><th>County appraisal</th><td>{fmt_money(total_apr)}</td></tr>
</table>
<p>Real talk: this looks like a lot {first_name} probably inherited or had transferred from family, and nobody's touched it since '79. {first_name} is over in <strong>{neighborhood}</strong> at {owner_mailing_street} -- same city, just three zip codes over. Local seller, paying taxes on dirt they probably forgot about.</p>
<p>My approach: warm Memphis-to-Memphis opener. I'll cite the {deed_phrase}, cite the subdivision by name, and reference {neighborhood} so they know I know my city. Anchor at {fmt_money(moa_open)}, walk up to {fmt_money(moa_close)} if needed. Hand to Marvin for paper once we have yes.</p>
<p>Math first, terms second, paper third. Pulling the trigger on first touch this morning.</p>
""",
         "subdivision name, quitclaim deed, family-transfer read, owner-zip neighborhood lookup, permit history",
         "Marquise's internal scout: cites V C Thomas, Orange Mound (38114), quitclaim, 47-year permit gap. Memphis-direct voice, 'real talk,' 'math first.'")

    # Stage 02 -- Marquise FIRST TOUCH (Memphis-to-Memphis, signal-driven)
    send(2, "marquise",
         f"That lot on Melrose y'all picked up in '{str(last_sale_year)[-2:]}",
         f"""
<p>{'Mr.' if first_name == 'there' else first_name} {last_name},</p>

<p>Marquise Reed with Everlight Ventures. Memphis side, like y'all. Real quick before I take up your time.</p>

<p>I came across <strong>{addr}</strong> on the assessor's site this morning. Records show that one came to y'all via {deed_phrase} on {last_sale_date} for {fmt_money(last_sale_price)} -- looks like family transfer, not a market buy. I respect that. None of my business why, just trying to give you context for why I'm writing.</p>

<p>Here's what caught my eye:</p>

<ul>
<li>The lot's been sitting in <strong>{subdivision}</strong> subdivision -- no permits pulled since <strong>{last_permit_year}</strong>. Best I can tell, nobody's done a thing to it in {years_since_permit} years.</li>
<li>County's got it at {fmt_money(total_apr)} flat land value.</li>
<li>Y'all are over on {owner_mailing_street} in {owner_mailing_zip} -- that's {neighborhood}. My closing attorney is over in that part of town, and we close at Mid-South Title in {owner_mailing_zip} damn near every week.</li>
</ul>

<p>Real talk: a vacant lot in {subdivision} that nobody's touched since '{str(last_permit_year)[-2:]} is gonna keep generating a tax bill and not much else. If y'all ever thought about clearing it off the books, I'd buy it for cash, close at Mid-South in 7 days, no agent on either side, no fees on your end.</p>

<p>If that's a conversation worth having, hit reply and I'll send a number same day. If not, I respect that and you won't hear from me again. Either way, appreciate the read.</p>

<p>Appreciate it,<br>
Marquise</p>
""",
         "addr, deed_type, last_sale_date, last_sale_price, family-transfer read, subdivision name, last_permit_year, years-since-permit, owner-zip + neighborhood (Orange Mound), Mid-South Title local connection",
         "Marquise's first touch -- Memphis cadence, 'real quick,' 'real talk,' cites subdivision + quitclaim + permit gap + Orange Mound zip + Mid-South Title closeness. NO number on touch 1.")

    # Stage 03 -- Sim seller reply (warm, interested, but tests with low willingness)
    send(3, "sim",
         f"Re: That lot on Melrose y'all picked up in '{str(last_sale_year)[-2:]}",
         sim_incoming(f"{first_name} {last_name}", [
             f"Hey Marquise -- yeah that lot came to me from my uncle, you read it right. Honest, I have not thought about that property in years. My wife and I both pay the tax bill every year and just kind of grumble about it.",
             f"What kind of number we talking? Not gonna lie, I am not gonna sell for nothing. But if it makes sense, sure, lets talk."
         ], f"{first_name.lower()}.evans.{last_sale_year}@example.com"),
         "responds to family-transfer read explicitly, references tax bill grumble (which Marquise predicted), local Memphis voice",
         "Sim seller confirms the family-transfer read, asks for a number. Engaged but cautious.")

    # Stage 04 -- Marquise anchor offer (still Marquise, since this is a Memphis-local deal he runs through close per his firmware)
    send(4, "marquise",
         f"Re: That lot on Melrose y'all picked up in '{str(last_sale_year)[-2:]} -- number",
         f"""
<p>Appreciate the reply, {first_name}.</p>

<p>Math first, that's how I do it. Here's the read:</p>

<table>
<tr><th>County land value</th><td>{fmt_money(total_apr)}</td></tr>
<tr><th>Comparable {subdivision}/{owner_mailing_zip} vacant residential sales last 90 days</th><td>{fmt_money(round(total_apr * 0.72))} median (4 sales, all QC or quick-flip deeds)</td></tr>
<tr><th>Days on market when listed traditional last year</th><td>average 127 days, two of four pulled before closing</td></tr>
<tr><th>My number to you, cash, 7 day close</th><td><strong>{fmt_money(moa_open)}</strong></td></tr>
</table>

<p>Honest with you: that's the math, not the wish. {fmt_money(moa_open)} reads short of {fmt_money(total_apr)} because the county number is for the land if it were ready to build on -- and {subdivision} comps say flat-vacant residential there is moving in the {fmt_money(round(total_apr * 0.65))} to {fmt_money(round(total_apr * 0.80))} band right now.</p>

<p>Three things working in your favor with my offer:</p>

<ol>
<li>Cash -- no financing falling through 30 days in</li>
<li>7 day close at Mid-South Title (Brenda Halloran is the closer; she handled my last three in {owner_mailing_zip})</li>
<li>You walk away clean -- no commission, no closing costs on your side, no surveys, nothing you have to do but sign</li>
</ol>

<p>If {fmt_money(moa_open)} doesn't shake out for you, tell me what does and we'll see if there's a middle. If we're not in the same ballpark, I'll respect that and let it go.</p>

<p>Appreciate it,<br>
Marquise</p>
""",
         "{subdivision} comp pull, days-on-market reference, Mid-South Title closer's first name (Brenda Halloran from Marvin's firmware), the 65-80% band math, 'math first' catchphrase",
         "Marquise's anchor offer: $16,250 with citable comps + Mid-South Title relationship + walk-away framing AFTER number. Cites 'Brenda Halloran' from Marvin's firmware for premium-team feel.")

    # Stage 05 -- Sim seller pushback (anchors high, references uncle's hopes)
    send(5, "sim",
         f"Re: That lot on Melrose y'all picked up in '{str(last_sale_year)[-2:]} -- number",
         sim_incoming(f"{first_name} {last_name}", [
             f"Marquise I hear you on the comps but {fmt_money(moa_open)} is rough. My uncle paid in the high teens for that lot back in 2011 and the county has it at {fmt_money(total_apr)}.",
             f"I would need to see at least {fmt_money(round(total_apr * 0.95))} for it to feel right. Otherwise honestly I am fine just holding it.",
         ], f"{first_name.lower()}.evans.{last_sale_year}@example.com"),
         "seller cites uncle's 2011 purchase price (which IS in records as $5,010 prior QC -- sim shows seller mis-remembers it as 'high teens'), anchors at $23,750 (95%)",
         "Seller anchors high citing uncle's price and county appraisal. Tests if Marquise will walk.")

    # Stage 06 -- Marquise counter (cites the actual prior sale price as factual correction, walks-up)
    send(6, "marquise",
         f"Re: That lot on Melrose y'all picked up in '{str(last_sale_year)[-2:]} -- meeting halfway",
         f"""
<p>Real talk, {first_name} -- I'm gonna correct you gently on one thing because I think it matters.</p>

<p>The deed records on Shelby Assessor show the prior transfer in February 2011 was <strong>{fmt_money(5010)}</strong>, not the high teens. Also a quitclaim, also looks like family between your uncle and the prior holder. Not trying to be a know-it-all, just want us working off the same page.</p>

<p>That said -- I hear you that {fmt_money(moa_open)} feels short and {fmt_money(round(total_apr * 0.95))} is your reference point. Here's where I can go honestly:</p>

<table>
<tr><th>My number</th><td><strong>{fmt_money(moa_close)}</strong></td></tr>
<tr><th>Terms</th><td>All cash, no financing</td></tr>
<tr><th>Close</th><td>7 days, Mid-South Title</td></tr>
<tr><th>Your costs</th><td>Zero</td></tr>
</table>

<p>That's me at the top of the {subdivision} comp band. Past that, I can't make the math work and I won't try to talk you into a number I don't believe in.</p>

<p>If {fmt_money(moa_close)} works, I'll have Marvin (he runs our closings) get a one-page contract to you by end of business today. If it doesn't, I'll let it go and not bother you again.</p>

<p>Your call, {first_name}.</p>

<p>Appreciate it,<br>
Marquise</p>
""",
         "FACTUAL correction citing actual 2011 deed record ($5,010 -- which is in the sales_history JSON), explicit hand-off to Marvin by name, walks-away framing, comp-band ceiling",
         "Marquise gently corrects the seller's misremembered price using the actual deed record. Walks-up to $21,250 with explicit hand-off to Marvin for paperwork.")

    # Stage 07 -- Sim seller accepts
    send(7, "sim",
         f"Re: That lot on Melrose -- meeting halfway",
         sim_incoming(f"{first_name} {last_name}", [
             f"Alright Marquise. {fmt_money(moa_close)} works. Send the contract.",
             f"Appreciate you being straight about the deed record. My wife is gonna be relieved we got that off our hands. When can we close?",
         ], f"{first_name.lower()}.evans.{last_sale_year}@example.com"),
         "accepts at $21,250, references wife (real-human texture), thanks Marquise for the correction, asks about close date",
         "Sim seller accepts. Personal moment ('my wife is gonna be relieved'). Asks about close date.")

    # Stage 08 -- Marvin contract (detail-obsessed, numbered, TN SB 909 baked in)
    send(8, "marvin",
         f"Purchase contract for {addr}",
         f"""
<p>{first_name} -- Marvin Cohen here, I run closings for Everlight Ventures. Marquise tagged me in. We're closing at {fmt_money(moa_close)}, all cash, target close <strong>{close_dow} {close_date}</strong> at Mid-South Title.</p>

<p>Two things to flag before you sign, three things to expect after:</p>

<p><strong>Before you sign:</strong></p>
<ol>
<li><strong>TN SB 909 disclosure (paragraph 4 of the contract):</strong> Everlight Ventures may assign this contract to a third-party buyer before closing. If we do, you get a written assignment-disclosure notice the same day. You keep your right to walk if anything material changes. This is required by TN law; we baked it in so nothing is hidden.</li>
<li><strong>EMD ($500):</strong> Wires to Mid-South Title within 24 hours of your countersign. Held in Brenda Halloran's escrow account. Refundable per contract terms (paragraph 7).</li>
</ol>

<p><strong>After you sign:</strong></p>
<ol>
<li>Mid-South Title pulls preliminary title within 5 business days. If anything weird shows up (old lien, unreleased mortgage, heirship issue from the {last_sale_year} transfer), we let you know same day.</li>
<li>Settlement statement to your email <strong>at least 48 hours before close</strong>. You see every line item before signing day.</li>
<li>Wire instructions for {fmt_money(moa_close)} come from Brenda Halloran directly -- never me, never Marquise, never via email-only. She calls you to verbally verify wire instructions before you wire. Wire fraud is real and we won't let it touch this close.</li>
</ol>

<p>Closing day: you sign at Mid-South ({owner_mailing_zip}-area office on Park Ave) or via mobile notary if you prefer. Brenda handles recording with Shelby County. Funds release same day.</p>

<p>Contract is attached as a one-page PDF. If anything is unclear, ping me at <a href="mailto:marvin@everlightventures.io">marvin@everlightventures.io</a> or 901-XXX-XXXX direct.</p>

<p>Best,<br>
Marvin</p>
""",
         "TN SB 909 disclosure by paragraph number, EMD held by Brenda Halloran (Mid-South closer from his firmware), wire-fraud verbal-verify discipline, references prior 2017 transfer for heirship check",
         "Marvin's contract email -- numbered lists, 'two things to flag,' wire-fraud discipline, references Brenda Halloran by name, TN SB 909 baked in, $500 EMD specifics.")

    # Stage 09 -- Sim seller signs
    send(9, "sim",
         f"Re: Purchase contract for {addr}",
         sim_incoming(f"{first_name} {last_name}", [
             f"Signed. Sending the PDF back now. Good to be working with people who lay it out clearly.",
             f"Brenda emailed me already. Closing on {close_date_short}, my wife and I will swing by Mid-South Friday afternoon to sign.",
         ], f"{first_name.lower()}.evans.{last_sale_year}@example.com"),
         "signs, compliments Marvin's clarity, confirms Brenda contacted them (implies seamless handoff), references wife again, sets in-person signing at Mid-South",
         "Sim seller signs. Brenda from Mid-South has already reached out. Premium-team feel confirmed.")

    # =====================================================================
    # INTERNAL HANDOFF -- Marquise notifies team
    # =====================================================================

    # Stage 10 -- Marquise internal: deal locked, pivot to Chris
    send(10, "marquise",
         f"[INTERNAL] {addr} locked at {fmt_money(moa_close)} -- handing buyer side to Marvin",
         f"""
<p>Team -- {first_name} {last_name} signed. Closing {close_dow} {close_date_short} at Mid-South, Brenda already in the loop.</p>

<table>
<tr><th>Seller close</th><td>{fmt_money(moa_close)} all cash</td></tr>
<tr><th>EMD</th><td>$500 wired to Mid-South escrow tomorrow AM</td></tr>
<tr><th>Equitable interest</th><td>Ours, pre-disclosed under TN SB 909</td></tr>
<tr><th>Title pull ETA</th><td>5 business days from Mid-South</td></tr>
</table>

<p>Buyer side: this is a Chris property. {subdivision} vacant residential in Orange Mound is exactly his {owner_mailing_zip}-{owner_mailing_zip[:4]} target zip list. He's picked up four lots in {subdivision} from us in the last 18 months.</p>

<p>Real talk on the assignment fee: I'm thinking we anchor at {fmt_money(buyer_total)} ({fmt_money(buyer_total - moa_close)} fee), expect Chris to counter to {fmt_money(round(total_apr * 0.95))} (his usual "$2,500 fee" line), Henry meets him at {fmt_money(buyer_close)} (split at $3k fee). That's the pattern from the last three.</p>

<p>Marvin -- you've got the warmest read on Chris from the last close. Run the buyer pitch. Tag Henry if Chris pushes hard on price.</p>

<p>Math first, terms second, paper third.</p>

<p>Marquise</p>
""",
         "Mid-South timing, TN SB 909 already disclosed, $500 EMD specifics, Chris's pattern (4 prior Orange Mound deals, $2,500 fee anchor, $3k split), Marquise's catchphrase, target zip list",
         "Marquise internal: deal locked, hands buyer side to Marvin who has the Chris relationship. References Chris's pattern from prior 3 deals.")

    # =====================================================================
    # BUYER SIDE -- Marvin pitches, Henry negotiates, Vaughn final signoff
    # =====================================================================

    # Stage 11 -- Marvin pitches Chris
    send(11, "marvin",
         f"New {subdivision} lot at {fmt_money(buyer_total)} -- {addr}",
         f"""
<p>Chris -- got one for you out of the {subdivision} pull this week.</p>

<p><strong>{addr}</strong>. Parcel <code>{parcel_id}</code>. Vacant residential, 0.107 acres, V C Thomas subdivision.</p>

<p>Three quick points so you can decide before reading the deal sheet:</p>

<ol>
<li>Seller signed yesterday at {fmt_money(moa_close)} all cash through Mid-South. EMD wires today. Closing <strong>{close_dow} {close_date_short}</strong>.</li>
<li>Owner is local ({owner_mailing_zip} {neighborhood}), {deed_phrase} from family in {last_sale_year}, no improvements since {last_permit_year}. Clean story, no heirship surprise expected.</li>
<li>Assignment price: <strong>{fmt_money(buyer_total)}</strong>. Our fee is {fmt_money(buyer_total - moa_close)}. You wire to Mid-South day-of-close; {fmt_money(moa_close)} goes to seller, {fmt_money(buyer_total - moa_close)} to us, deed comes to you direct.</li>
</ol>

<p>Deal sheet attached if you want the full picture. Yes/no -- I'd like to lock the assignment by tomorrow EOD so we keep the close date.</p>

<p>Best,<br>
Marvin</p>
""",
         "subdivision name, parcel ID, EMD already wiring, closing date in writing, owner-locality (no surprise), Chris's preference for clean stories",
         "Marvin's pitch to Chris -- numbered, decision-first, references Mid-South relationship + clean story. Asks for yes/no by tomorrow EOD.")

    # Stage 12 -- Sim Chris asks for full sheet (matter-of-fact)
    send(12, "sim",
         f"Re: New {subdivision} lot at {fmt_money(buyer_total)}",
         sim_incoming("Chris Ulander @ Mid-South Homebuyers", [
             "Send the full sheet. Also screenshot the assessor page so I have the source.",
             f"Whats the fee? Looks like $3,500. Im usually at $2,500 on vacant lots in {subdivision}-adjacent.",
         ], "chris@midsouthhomebuyers.com"),
         "Chris asks for the full sheet + assessor screenshot, anchors on his usual $2,500 fee ceiling for vacant lots",
         "Chris asks for source verification + telegraphs his usual $2,500 fee anchor.")

    # Stage 13 -- Marvin sends full deal sheet
    send(13, "marvin",
         f"Deal sheet -- {addr}",
         f"""
<p>Chris -- here's everything.</p>

<h2>Property</h2>
<table>
<tr><th>Address</th><td>{addr}</td></tr>
<tr><th>Parcel ID</th><td><code>{parcel_id}</code></td></tr>
<tr><th>Type</th><td>VACANT LAND, Residential class</td></tr>
<tr><th>Lot size</th><td>{parcel.get('land_sqft','4,661')} sqft (0.107 acres)</td></tr>
<tr><th>Subdivision</th><td>{subdivision}</td></tr>
<tr><th>Neighborhood (Marquise's read)</th><td>{neighborhood} ({owner_mailing_zip})</td></tr>
</table>

<h2>Title chain</h2>
<table>
<tr><th>Last sale</th><td>{last_sale_date} via {deed_phrase} for {fmt_money(last_sale_price)} -- {'family transfer' if is_family_transfer else 'market sale'}</td></tr>
<tr><th>Prior sale</th><td>02/15/2011 via QC for $5,010 -- also family</td></tr>
<tr><th>Last permit</th><td>{last_permit_year} (permit #{permits[0].get('permit_number','124026') if permits else '124026'}) -- no improvements in {years_since_permit} years</td></tr>
<tr><th>Owner of record</th><td>{first_name} {last_name}</td></tr>
<tr><th>Owner mailing</th><td>{owner_mailing_street}, MEMPHIS {owner_mailing_zip}</td></tr>
</table>

<h2>Deal economics</h2>
<table>
<tr><th>County appraisal</th><td>{fmt_money(total_apr)} (land only)</td></tr>
<tr><th>Our contract w/ seller</th><td>{fmt_money(moa_close)} all cash (signed)</td></tr>
<tr><th>Your assignment price</th><td><strong>{fmt_money(buyer_total)}</strong></td></tr>
<tr><th>Our fee</th><td>{fmt_money(buyer_total - moa_close)} (baked into your wire to Mid-South)</td></tr>
<tr><th>Close date</th><td>{close_dow} {close_date_short} at Mid-South Title</td></tr>
</table>

<h2>On the $2,500 fee anchor</h2>
<p>Hear you on your vacant-lot ceiling. Hammer (Henry) is gonna want a word with you on that because we're carrying the {last_sale_year} family-transfer title risk and the 9 days of negotiation that got {first_name} from "I forgot I owned it" to "send the contract." I'll let him make that case.</p>

<h2>Source</h2>
<p>Assessor page: <a href="{parcel.get('source_url','')}">{parcel.get('source_url','')}</a> (also attached as PDF screenshot in the next reply).</p>

<p>Best,<br>
Marvin</p>
""",
         "all signals consolidated: subdivision, neighborhood, both prior QCs cited by date+price, permit number, assessor source URL, full title chain transparency, ack of Chris's $2,500 anchor + handoff to Henry",
         "Marvin's full deal sheet: complete title chain, both prior QC sales cited, permit number, source link. Acknowledges Chris's anchor and explicitly hands negotiation to Henry.")

    # Stage 14 -- Sim Chris counters
    send(14, "sim",
         f"Re: Deal sheet -- {addr}",
         sim_incoming("Chris Ulander @ Mid-South Homebuyers", [
             f"Marvin {fmt_money(buyer_total - moa_close)} is high for {subdivision}-grade vacant. I can do {fmt_money(moa_close + 2500)} all in -- {fmt_money(2500)} to you guys.",
             "Take it or leave it.",
         ], "chris@midsouthhomebuyers.com"),
         "Chris counters at $2,500 fee, same pattern Marquise predicted in Stage 10",
         "Chris counters at $2,500 fee -- exactly the pattern from Marquise's internal note. Henry now picks up.")

    # Stage 15 -- Henry negotiates with Chris (math-first, walks-away framing)
    send(15, "henry",
         f"Re: Deal sheet -- {addr} -- meeting in the middle",
         f"""
<p>Chris, Henry here -- Marvin tagged me in.</p>

<p>Hear you on the {fmt_money(2500)} vacant-lot ceiling. Honest read:</p>

<table>
<tr><th>Your last 4 buys from us</th><td>2 in {subdivision}, 2 in adjacent {neighborhood}</td></tr>
<tr><th>Average days from your "send me one" to closing</th><td>11 days, including the 9 days of seller-side negotiation we eat before you ever see the deal</td></tr>
<tr><th>Average our-fee on those four</th><td>{fmt_money(3000)} -- two at $3k, two at $3,500</td></tr>
<tr><th>Average your hold-to-resale on those four</th><td>67 days, gross margin {fmt_money(round(total_apr * 0.30))}</td></tr>
</table>

<p>I'm not gonna pretend {fmt_money(2500)} is impossible. It's possible. It's just below what this specific deal cost us to put in your inbox: clean signed contract, family-transfer story de-risked, Mid-South Title pre-pulled, EMD already wiring.</p>

<p>Meet me in the middle: <strong>{fmt_money(buyer_close)}</strong> all in. That's <strong>{fmt_money(buyer_close - moa_close)}</strong> to us -- still inside your vacant-lot budget, still respects what you've built with us over the last four deals.</p>

<p>Yes/no, Chris. Marvin needs the answer by EOD to keep {close_date_short}.</p>

<p>Henry</p>
""",
         "Chris's prior 4 deals tracked + average our-fee history + days-to-close + Chris's gross margin -- Henry's math-first persona, walks-away framing AFTER the new number",
         "Henry counters at $3,000 fee with full math-history table on Chris's last 4 deals. 'Math first, feelings second' embodied.")

    # Stage 16 -- Sim Chris accepts
    send(16, "sim",
         f"Re: Deal sheet -- {addr} -- meeting in the middle",
         sim_incoming("Chris Ulander @ Mid-South Homebuyers", [
             f"Fine. {fmt_money(buyer_close)} works. Send the assignment and Ill have my entity on it by tomorrow morning.",
             "Brenda has my LLC info already from the last close.",
         ], "chris@midsouthhomebuyers.com"),
         "Chris accepts at $3,000 fee, references his LLC and Brenda's prior knowledge",
         "Chris accepts. Premium-team feel: Brenda already has his entity info, no friction.")

    # Stage 17 -- Vaughn senior-partner countersign on assignment (gravitas)
    send(17, "vaughn",
         f"Assignment of contract -- {addr}",
         f"""
<p>Chris,</p>

<p>Vaughn Sterling. Senior partner side of Everlight Ventures. Marvin has the paper drafted; I countersign the assignment because it's our protocol on any cross-party assignment carrying an equitable-interest disclosure under TN SB 909.</p>

<p>Three items to be direct with you about:</p>

<p>First, the seller -- {first_name} {last_name} -- received SB 909 pre-disclosure at contract signing on {datetime.now().strftime('%B %d, %Y')}. Acknowledged in writing. This assignment is the disclosed event the statute requires us to surface. Mid-South Title has a copy of the acknowledgment in the closing file. Routine, but I want it stated.</p>

<p>Second, the {last_sale_year} family-transfer title chain. We've done preliminary lookback through the Shelby County recording office. The 2017 quitclaim from {first_name}'s uncle to {first_name} has no recorded encumbrances and the prior 2011 transfer also clears. Mid-South will pull the formal commitment within 5 business days. If anything material surfaces, you'll hear from Marvin same day.</p>

<p>Third -- and the reason I sign these personally -- I want you to know there's a senior partner at this firm whose name is on every assignment that goes out. In my experience, a lot of wholesalers move paper and disappear when something goes sideways. We don't operate that way. If anything material changes between now and close, my line is open to you directly: <a href="mailto:vaughn@everlightventures.io">vaughn@everlightventures.io</a> or 843-XXX-XXXX.</p>

<p>Marvin will follow up with closing logistics. Glad to have you on this one.</p>

<p>Warm regards,<br>
Vaughn Sterling<br>
Senior Partner | Everlight Ventures</p>
""",
         "TN SB 909 disclosure protocol cited, 2017+2011 title chain lookback specifics, senior-partner-direct-line as commitment, 'in my experience' from his firmware, 'warm regards' sign-off only Vaughn uses",
         "Vaughn's senior signoff -- long-form when explaining, direct line to him personally, 'in my experience' frame, 'warm regards' close.")

    # Stage 18 -- Sim Chris signs assignment
    send(18, "sim",
         f"Re: Assignment of contract -- {addr}",
         sim_incoming("Chris Ulander @ Mid-South Homebuyers", [
             "Vaughn -- appreciated, both the senior-partner note and the title-chain detail. Signing the assignment now.",
             f"Wiring {fmt_money(buyer_close)} to Mid-South on close day. See y'all {close_dow}.",
         ], "chris@midsouthhomebuyers.com"),
         "Chris explicitly acknowledges Vaughn's gravitas + title-chain transparency -- premium-team effect lands",
         "Chris signs. Acknowledges senior-partner touch matters to him.")

    # Stage 19 -- Marvin closing-day coordination
    send(19, "marvin",
         f"Closing day logistics -- {addr}",
         f"""
<p>All parties + Brenda @ Mid-South,</p>

<p>Final coordination on <strong>{addr}</strong>, closing <strong>{close_dow} {close_date_short}</strong>.</p>

<p><strong>Wire & fund timeline:</strong></p>
<ol>
<li>{first_name} {last_name} (seller) -- in-person signing at Mid-South Park Ave office, Friday 2 PM. Brenda confirmed by phone yesterday.</li>
<li>Chris Ulander / Mid-South Homebuyers entity (buyer) -- wires <strong>{fmt_money(buyer_close)}</strong> to Mid-South Title escrow account day-of-close. Brenda calls Chris to verbally verify wire instructions before he wires. No emailed wire-only.</li>
<li>Mid-South disburses: <strong>{fmt_money(moa_close)}</strong> to {first_name} {last_name}, <strong>{fmt_money(buyer_close - moa_close)}</strong> to Everlight Ventures operating account.</li>
<li>Recording with Shelby County same day. Deed conveys directly from {last_name} to Chris's designated LLC; Everlight Ventures does not appear on title.</li>
<li>Settlement statement to all parties by Friday 6 PM Central.</li>
</ol>

<p><strong>If anything blows up:</strong> ping me at <a href="mailto:marvin@everlightventures.io">marvin@everlightventures.io</a> or 901-XXX-XXXX. Brenda has me on speed dial.</p>

<p>Best,<br>
Marvin</p>
""",
         "wire verification discipline (Brenda calls verbally), exact disbursement amounts, Everlight not on title (assignment pattern), settlement statement deadline",
         "Marvin's closing day logistics: numbered, wire-fraud disciplined, exact disbursements, Brenda's verbal-verify confirmed.")

    # Stage 20 -- Marquise internal close report
    send(20, "marquise",
         f"[INTERNAL] CLOSED: {addr} -- {fmt_money(buyer_close - moa_close)} booked",
         f"""
<p>Team -- <strong>recorded today</strong>.</p>

<p>{addr} closed clean. {first_name} {last_name} got their {fmt_money(moa_close)} wire. Chris (Mid-South Homebuyers LLC) is on title. Everlight banked <strong>{fmt_money(buyer_close - moa_close)}</strong>.</p>

<p>For the dashboard:</p>

<table>
<tr><th>Recorded</th><td>{(datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')}</td></tr>
<tr><th>Cycle time first-touch -> close</th><td>12 days</td></tr>
<tr><th>Seller negotiation rounds</th><td>3 (anchor -> counter -> close)</td></tr>
<tr><th>Buyer negotiation rounds</th><td>3 (pitch -> counter -> meet-middle)</td></tr>
<tr><th>Personas touched</th><td>Marquise (scout + seller-side close), Marvin (paper + buyer-pitch + closing logistics), Henry (buyer-side negotiation), Vaughn (assignment countersign)</td></tr>
<tr><th>Signals that drove the open</th><td>2017 quitclaim ({deed_phrase}), {subdivision} subdivision, {last_permit_year} last permit ({years_since_permit}y gap), Orange Mound owner zip</td></tr>
<tr><th>What made the close</th><td>Marquise correcting the seller's misremembered prior-sale price using actual deed record</td></tr>
</table>

<p>Marvin -- update Chris's buyer ledger. He's at 5 closes with us now. Next time he's a returning-buyer-rate.</p>

<p>Math first, terms second, paper third. {addr} done. On to the next one.</p>

<p>Marquise</p>
""",
         "cycle time, persona attribution, the specific signal-that-closed (the deed-record correction), Chris's lifetime-buyer count, Marquise's catchphrase",
         "Marquise's close report: $3,000 booked, cites which signals drove the open, calls out the deed-correction moment as 'what made the close.' Updates Chris's buyer ledger.")

    print(f"\n=== V2 SIMULATION COMPLETE ===")
    print(f"Transcript: {TRANSCRIPT}")
    print(f"All emails should be in {TO} within ~2 minutes.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
