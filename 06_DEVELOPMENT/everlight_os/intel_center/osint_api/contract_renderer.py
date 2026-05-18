"""
contract_renderer.py -- render the 5 deal contract HTMLs from deal_meta.

Eliminates the "test_self had no contracts" bug class. Every deal that
loads via intel deal new <key> now auto-renders:
  01_PSA.html
  02_Schedule_A_TN_SB909.html
  03_EMD_Wire_Acknowledgment.html
  04_Assignment_Agreement_Chris.html
  05_Settlement_Statement_Preview.html
  index.html

Schema separation:
  - Per-deal facts (deal_meta.json):    seller, buyer, parcel, prices, property facts
  - Global config (title_firm.json):    Mid South Title address, buyer DBA name, RA, etc.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
DEALS_DIR = ROOT / "09_DASHBOARD" / "reports" / "deals"
GLOBAL_CONFIG = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "config"
GLOBAL_CONFIG.mkdir(parents=True, exist_ok=True)

# Make contract_template importable from sister module
import sys
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "serve_helpers"))
from contract_template import wrap  # noqa: E402

# ---------------------------------------------------------------------
# Global config -- title firm, buyer DBA, etc. Override by editing the JSON.
# ---------------------------------------------------------------------
DEFAULT_GLOBAL = {
    "buyer_legal_name": "Richard Gee",
    "buyer_dba": "Everlight Ventures",
    "buyer_filing_state": "California (DBA on file)",
    "buyer_address": "Memphis, Tennessee (operating)",
    "title_firm_name": "Mid South Title, LLC",
    "title_firm_address": "[Mid South Title street address -- pull from intake call follow-up]",
    "title_firm_metro": "Memphis",
    "title_firm_state": "Tennessee",
    "title_firm_iolta_bank": "[Mid South Title escrow bank -- populated at PSA generation]",
    "title_firm_aba_routing": "[ABA routing -- populated at PSA generation]",
    "title_firm_account_no": "[escrow account number -- populated at PSA generation]",
    "back_tax_estimate_usd": 1800,
    "title_insurance_estimate_usd": 185,
    "recording_estimate_usd": 42,
    "title_closing_fee_estimate_usd": 450,
    "buyer_assignee_name": "Mid South Homebuyers, LLC",
    "buyer_assignee_signer": "Chris Ulander",
}


def load_global_config() -> dict:
    cfg_path = GLOBAL_CONFIG / "title_firm.json"
    if cfg_path.exists():
        return {**DEFAULT_GLOBAL, **json.loads(cfg_path.read_text())}
    cfg_path.write_text(json.dumps(DEFAULT_GLOBAL, indent=2))
    return DEFAULT_GLOBAL.copy()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _money(n: int | float) -> str:
    return f"${int(n):,}"


def _money_dec(n: int | float) -> str:
    return f"${int(n):,}.00"


def _close_date(inspection_days: int) -> str:
    return (datetime.now() + timedelta(days=inspection_days)).strftime("%B %d, %Y")


def _addr_short(full_addr: str) -> str:
    return full_addr.split(",")[0].strip()


# ---------------------------------------------------------------------
# Per-doc renderers (each takes meta + global, returns HTML string)
# ---------------------------------------------------------------------
def render_psa(meta: dict, g: dict) -> str:
    final = int(meta["final_to_seller"])
    emd = int(meta.get("emd_usd", 250))
    days = int(meta.get("inspection_days", 14))
    close_date = _close_date(days)
    eff = datetime.now().strftime("%B %d, %Y")
    parcel = meta.get("parcel_id", "")
    addr = meta.get("property_address", "")
    seller = meta.get("seller_name", "")
    seller_addr = meta.get("seller_mailing_address",
                           meta.get("owner_mailing_address", "[seller mailing address]"))
    beds = meta.get("bedrooms", "?"); baths = meta.get("bathrooms", "?")
    yb = meta.get("year_built", "?"); sqft = meta.get("land_sqft", "?")

    body = f"""
<div class="banner">DRAFT for e-signature ◆ Generated {datetime.now().strftime('%Y-%m-%d')} ◆ DocuSign envelope pending</div>

<h2>Block 1: Parties and Effective Date</h2>
<div class="clause">
  <div class="clause-id">Block 1</div>
  This Purchase and Sale Agreement (the "Agreement") is entered into on <strong>{eff}</strong> (the "Effective Date") between:<br><br>
  <strong>SELLER:</strong> {seller}, an individual, of {seller_addr}<br><br>
  and<br><br>
  <strong>BUYER (or Buyer's assignee):</strong> {g['buyer_legal_name']}, an individual doing business as {g['buyer_dba']}, a sole proprietorship registered in {g['buyer_filing_state']}, with principal address in {g['buyer_address']}.
</div>

<h2>Block 2: Property and Earnest Money</h2>
<table class="terms-table">
  <tr><td>Property address</td><td>{addr}</td></tr>
  <tr><td>County</td><td>Shelby County, Tennessee</td></tr>
  <tr><td>Parcel ID</td><td>{parcel}</td></tr>
  <tr><td>Property type</td><td>{beds}BR / {baths}BA SFR, built {yb}, {sqft} sqft lot</td></tr>
  <tr><td>Purchase price</td><td><span class="money">{_money(final)}</span> U.S. Dollars, all cash</td></tr>
  <tr><td>Earnest money deposit</td><td><span class="money">{_money(emd)}</span>, payable by wire to {g['title_firm_name']} escrow within 3 business days of execution</td></tr>
  <tr><td>Effective date</td><td>{eff}</td></tr>
  <tr><td>Target close date</td><td>on or before <strong>{close_date}</strong></td></tr>
  <tr><td>Inspection period</td><td>{days} calendar days from Effective Date</td></tr>
</table>

<h2>Block 3: Equitable Interest and Assignment</h2>
<div class="clause">
  <div class="clause-id">Block 3</div>
  Buyer shall hold an equitable interest in the Property as of the Effective Date by virtue of this Agreement. Buyer reserves the right to assign this Agreement, in whole or in part, to a third-party assignee (the "Assignee") prior to closing, with written notice to Seller and the closing agent. Seller acknowledges that Buyer may receive an assignment fee from the Assignee, the amount of which shall be disclosed on the closing settlement statement at the time of closing.
</div>

<h2>Block 4: Dual Remedy / Liquidated Damages</h2>
<div class="clause">
  <div class="clause-id">Block 4</div>
  In the event Seller defaults under this Agreement, Buyer's remedies shall be limited, at Buyer's election, to either (a) specific performance, or (b) return of the Earnest Money Deposit plus reasonable transaction costs incurred up to the date of default. In the event Buyer defaults, Seller's remedies shall be limited to retention of the Earnest Money Deposit as liquidated damages, which the parties stipulate is a reasonable estimate of Seller's actual damages.
</div>

<h2>Block 5: Wholesaler Disclosure (TN SB 909)</h2>
<div class="clause">
  <div class="clause-id">Block 5 ◆ Statutory ◆ Tenn. Code Ann. § 66-32-101 et seq. (eff. April 8, 2025)</div>
  Buyer hereby discloses to Seller, and Seller hereby acknowledges, that:
  <ul>
    <li>(i) Buyer is acting as a real estate wholesaler and not on behalf of Seller;</li>
    <li>(ii) Buyer intends to assign or otherwise transfer Buyer's rights under this Agreement to a third-party Assignee;</li>
    <li>(iii) Buyer's net profit from the assignment may exceed the proceeds received by Seller at closing;</li>
    <li>(iv) Seller has been provided this disclosure in writing prior to or contemporaneously with the execution of this Agreement, and Seller has had the opportunity to consult independent counsel.</li>
  </ul>
  This Block 5 disclosure is also restated in <em>Schedule A</em>, signed by Seller as a separate document in the same envelope as this Agreement.
</div>

<h2>Block 6: Title and Closing</h2>
<div class="clause">
  <div class="clause-id">Block 6</div>
  Closing shall occur at the offices of <strong>{g['title_firm_name']}</strong>, {g['title_firm_metro']}, {g['title_firm_state']}, a RESPA-compliant Tennessee licensed title agency, on or before <strong>{close_date}</strong>. The Earnest Money Deposit and any subsequent assignment deposit shall be held in {g['title_firm_name']}'s IOLTA escrow account. All back property tax owed against the Property as of the closing date shall be paid by Buyer out of Buyer's side of the closing settlement statement; Seller shall not be required to pay any back tax out of pocket.
</div>

<h2>Block 7: Signatures</h2>
<div class="sig-block">
  <div class="sig-block-title">Seller signature</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{seller}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name<br><strong>SELLER</strong></div></div>
  </div>
  <div class="sig-block-title" style="margin-top:1.5rem;">Buyer signature</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{g['buyer_legal_name']}, dba {g['buyer_dba']}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name<br><strong>BUYER (or Buyer's assignee)</strong></div></div>
  </div>
</div>
"""
    deal_meta_for_wrap = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"{seller} (Seller) ◆ {g['buyer_legal_name']} dba {g['buyer_dba']} (Buyer/Assignor)",
    }
    return wrap("Purchase and Sale Agreement", body, deal_meta_for_wrap, doc_label="PSA · Document 1 of 3")


def render_schedule_a(meta: dict, g: dict) -> str:
    parcel = meta.get("parcel_id", ""); addr = meta.get("property_address", "")
    seller = meta.get("seller_name", "")
    body = f"""
<div class="banner">Statutory Disclosure ◆ Tenn. Code Ann. § 66-32-101 ◆ Eff. April 8, 2025</div>

<h2>Wholesaler Disclosure</h2>
<p>This <strong>Schedule A</strong> is executed contemporaneously with the Purchase and Sale Agreement (the "Agreement") of even date between {seller} (Seller) and {g['buyer_legal_name']} dba {g['buyer_dba']} (Buyer) for the property at <strong>{addr}</strong>, parcel <strong>{parcel}</strong>.</p>

<p>This Schedule A is the wholesaler disclosure required by Tennessee Senate Bill 909, codified at Tenn. Code Ann. § 66-32-101 et seq., effective April 8, 2025.</p>

<h2>Statutory Acknowledgments</h2>
<div class="clause">
  <div class="clause-id">§ 66-32-102(a) — Required disclosures</div>
  Seller acknowledges that Seller has read, understood, and received in writing prior to or contemporaneously with execution of the Agreement, each of the following disclosures:
  <ul>
    <li><strong>1.</strong> Buyer is acting as a real estate wholesaler. Buyer is not acting on behalf of Seller in any capacity.</li>
    <li><strong>2.</strong> Buyer intends to assign or otherwise transfer Buyer's rights under the Agreement to a third-party purchaser (the "Assignee") prior to closing.</li>
    <li><strong>3.</strong> The amount Buyer will receive from the Assignee may exceed the proceeds received by Seller at closing.</li>
    <li><strong>4.</strong> The assignment fee paid to Buyer by the Assignee shall be disclosed as a line item on the closing settlement statement issued by the title company.</li>
    <li><strong>5.</strong> Seller has had the opportunity to consult independent legal counsel of Seller's choosing prior to execution.</li>
  </ul>
</div>

<h2>Right to Rescind</h2>
<div class="clause">
  <div class="clause-id">§ 66-32-103 — Rescission window</div>
  If this Schedule A is not delivered to Seller in writing prior to or contemporaneously with execution of the Agreement, or if any of the disclosures above are materially false at the time of execution, Seller shall have the right to rescind the Agreement and recover statutory damages of up to ten thousand dollars ($10,000) plus reasonable attorneys' fees, pursuant to § 66-32-103.
</div>

<h2>Acknowledgment of Receipt</h2>
<p>By signing below, Seller acknowledges receipt of this Schedule A in writing, prior to or contemporaneously with execution of the Purchase and Sale Agreement, and acknowledges each of the disclosures set forth above.</p>

<div class="sig-block">
  <div class="sig-block-title">Seller acknowledgment</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{seller}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name<br><strong>SELLER</strong></div></div>
  </div>
  <div class="sig-block-title" style="margin-top:1.5rem;">Buyer acknowledgment</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{g['buyer_legal_name']}, dba {g['buyer_dba']}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name<br><strong>BUYER (Wholesaler)</strong></div></div>
  </div>
</div>
"""
    deal_meta_for_wrap = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"{seller} (Seller) ◆ {g['buyer_legal_name']} dba {g['buyer_dba']} (Buyer/Assignor)",
    }
    return wrap("Schedule A ◆ TN SB 909 Wholesaler Disclosure", body, deal_meta_for_wrap,
                 doc_label="Schedule A · Document 2 of 3")


def render_emd_ack(meta: dict, g: dict) -> str:
    emd = int(meta.get("emd_usd", 250))
    days = int(meta.get("inspection_days", 14))
    parcel = meta.get("parcel_id", ""); addr = meta.get("property_address", "")
    seller = meta.get("seller_name", "")
    body = f"""
<div class="banner">Wire instructions ◆ {g['title_firm_name']} escrow ◆ {_money(emd)} EMD due in 3 business days</div>

<h2>Earnest Money Wire Acknowledgment</h2>
<p>Pursuant to <strong>Block 2</strong> of the Purchase and Sale Agreement of even date between {seller} (Seller) and {g['buyer_legal_name']} dba {g['buyer_dba']} (Buyer), Buyer shall wire the earnest money deposit of <span class="money">{_money(emd)}</span> to the following escrow account within three (3) business days of mutual execution of the Agreement.</p>

<h2>Wire Instructions</h2>
<table class="terms-table">
  <tr><td>Beneficiary</td><td>{g['title_firm_name']} ◆ IOLTA escrow account</td></tr>
  <tr><td>Beneficiary address</td><td>{g['title_firm_address']}</td></tr>
  <tr><td>Bank name</td><td>{g['title_firm_iolta_bank']}</td></tr>
  <tr><td>Routing (ABA)</td><td>{g['title_firm_aba_routing']}</td></tr>
  <tr><td>Account number</td><td>{g['title_firm_account_no']}</td></tr>
  <tr><td>Wire reference / memo</td><td>{_addr_short(addr)} / {seller.split()[0] if seller else 'Seller'}-Gee EMD / Deal {meta['deal_key']}</td></tr>
  <tr><td>Amount</td><td><span class="money">{_money_dec(emd)}</span> U.S. Dollars</td></tr>
  <tr><td>Wire by</td><td>3 business days from mutual execution of the PSA</td></tr>
</table>

<h2>Conditions of Refund</h2>
<div class="clause">
  <div class="clause-id">EMD refund conditions</div>
  The Earnest Money Deposit shall remain refundable to Buyer through the {days}-day inspection period. Buyer may terminate the Agreement and recover the EMD in full upon written notice to Seller and the closing agent ({g['title_firm_name']}) prior to the expiration of the inspection period for any reason.
</div>

<div class="clause">
  <div class="clause-id">Post-DD non-refund</div>
  After expiration of the {days}-day inspection period, the EMD becomes non-refundable to Buyer except in the event of Seller default or failure of clear and marketable title. Otherwise the EMD shall be released to Seller as liquidated damages pursuant to Block 4 of the Agreement.
</div>

<div class="sig-block">
  <div class="sig-block-title">Buyer wire acknowledgment</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{g['buyer_legal_name']}, dba {g['buyer_dba']}<br><strong>Date wire initiated</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Wire confirmation #<br><strong>BUYER</strong></div></div>
  </div>
</div>
"""
    deal_meta_for_wrap = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"{seller} (Seller) ◆ {g['buyer_legal_name']} dba {g['buyer_dba']} (Buyer/Assignor)",
    }
    return wrap("Earnest Money Wire Acknowledgment", body, deal_meta_for_wrap,
                 doc_label="EMD Ack · Document 3 of 3")


def render_assignment(meta: dict, g: dict) -> str:
    final_seller = int(meta["final_to_seller"])
    chris_pays = int(meta.get("final_to_buyer", final_seller + 3590))
    assignment_fee = chris_pays - final_seller
    gfad = int(meta.get("gfad_usd", 1000))
    days = int(meta.get("inspection_days", 14))
    close_date = _close_date(days)
    parcel = meta.get("parcel_id", ""); addr = meta.get("property_address", "")
    seller = meta.get("seller_name", "")
    eff = datetime.now().strftime("%B %d, %Y")

    body = f"""
<div class="banner">Assignment package ◆ Buyer side ◆ Sent to {g['buyer_assignee_signer']} after Seller signs PSA</div>

<h2>Property Summary</h2>
<table class="terms-table">
  <tr><td>Property</td><td>{addr}</td></tr>
  <tr><td>Parcel ID</td><td>{parcel}</td></tr>
  <tr><td>Owner of record</td><td>{seller}</td></tr>
  <tr><td>Seller PSA price</td><td><span class="money">{_money(final_seller)}</span> cash to Seller</td></tr>
  <tr><td>Title firm</td><td>{g['title_firm_name']} ◆ RESPA verified</td></tr>
  <tr><td>Inspection period</td><td>{days} days from PSA effective date {eff}</td></tr>
  <tr><td>Target close</td><td>on or before {close_date}</td></tr>
</table>

<h2>Assignee Terms</h2>
<table class="terms-table">
  <tr><td>Assignee pays at closing</td><td><span class="money">{_money(chris_pays)}</span> total to {g['title_firm_name']}</td></tr>
  <tr><td>Of which to Seller</td><td>{_money(final_seller)}</td></tr>
  <tr><td>Of which to Assignor (Everlight)</td><td><span class="money">{_money(assignment_fee)}</span> assignment fee</td></tr>
  <tr><td>Good-Faith Assignment Deposit</td><td><span class="money">{_money(gfad)}</span> to {g['title_firm_name']} escrow within 48 hours of executing this Assignment Agreement</td></tr>
</table>

<h2>Assignment Agreement Clauses</h2>

<div class="clause">
  <div class="clause-id">Clause 2.1 — Assignment Fee + Payment Trigger</div>
  Assignor ({g['buyer_legal_name']} dba {g['buyer_dba']}) hereby assigns all right, title, and interest in the Real Estate Purchase Agreement dated {eff} for the property at {addr} to Assignee ({g['buyer_assignee_name']}), in exchange for an Assignment Fee of <span class="money">{_money(assignment_fee)}</span>, payable as follows:
  <ul>
    <li>(a) Good-Faith Assignment Deposit of <span class="money">{_money(gfad)}</span>, paid by Assignee to {g['title_firm_name']} escrow within 48 hours of execution of this Assignment Agreement;</li>
    <li>(b) Balance of <span class="money">{_money(assignment_fee - gfad)}</span> paid at closing of the underlying transaction, disbursed by the closing agent to Assignor on the closing settlement statement.</li>
  </ul>
</div>

<div class="clause">
  <div class="clause-id">Clause 2.4 — GFAD Refund Conditions</div>
  The Good-Faith Assignment Deposit shall be refunded to Assignee only if (i) title is unmarketable and Seller cannot cure within 14 days, (ii) the underlying PSA is terminated by Seller's default, or (iii) force majeure occurs prior to closing. In all other circumstances the GFAD shall be forfeited to Assignor as liquidated damages.
</div>

<div class="clause">
  <div class="clause-id">Clause 2.6 — Anti-Circumvention (24 months)</div>
  Assignee agrees that for a period of <strong>twenty-four (24) months</strong> following execution, Assignee shall not, directly or indirectly: (a) contact, solicit, or transact with the Seller named in the underlying PSA outside the scope of this Assignment; (b) acquire the Property from any source other than through this Assignment without paying Assignor's full Assignment Fee; (c) disclose the Seller's identity, contact information, or PSA terms to any third party. Breach entitles Assignor to injunctive relief plus liquidated damages equal to <strong>two (2) times</strong> the Assignment Fee, plus reasonable attorneys' fees.
</div>

<div class="sig-block">
  <div class="sig-block-title">Assignor signature</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{g['buyer_legal_name']}, dba {g['buyer_dba']}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name<br><strong>ASSIGNOR</strong></div></div>
  </div>
  <div class="sig-block-title" style="margin-top:1.5rem;">Assignee signature</div>
  <div class="sig-row">
    <div><div class="sig-line"></div><div class="sig-label">{g['buyer_assignee_signer']}, {g['buyer_assignee_name']}<br><strong>Date</strong></div></div>
    <div><div class="sig-line"></div><div class="sig-label">Print name + Title<br><strong>ASSIGNEE</strong></div></div>
  </div>
</div>
"""
    chris_meta = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"{g['buyer_legal_name']} dba {g['buyer_dba']} (Assignor) ◆ {g['buyer_assignee_name']} (Assignee)",
    }
    return wrap("Assignment Agreement ◆ Everlight → " + g['buyer_assignee_name'],
                 body, chris_meta, doc_label="Chris Package · Buyer Side")


def render_settlement_preview(meta: dict, g: dict) -> str:
    final_seller = int(meta["final_to_seller"])
    chris_pays = int(meta.get("final_to_buyer", final_seller + 3590))
    assignment_fee = chris_pays - final_seller
    gfad = int(meta.get("gfad_usd", 1000))
    emd = int(meta.get("emd_usd", 250))
    days = int(meta.get("inspection_days", 14))
    close_date = _close_date(days)
    parcel = meta.get("parcel_id", ""); addr = meta.get("property_address", "")
    back_tax = int(g.get("back_tax_estimate_usd", 1800))
    title_ins = int(g.get("title_insurance_estimate_usd", 185))
    recording = int(g.get("recording_estimate_usd", 42))
    title_fee = int(g.get("title_closing_fee_estimate_usd", 450))
    chris_balance = chris_pays - gfad
    total_buyer_wire = chris_balance + back_tax + title_ins + recording + title_fee
    assignor_total = assignment_fee - gfad + emd

    body = f"""
<div class="banner">PREVIEW ◆ Closing in 24 hours ◆ {g['title_firm_name']} generates the official version</div>

<h2>Closing Summary</h2>
<table class="terms-table">
  <tr><td>Property</td><td>{addr}</td></tr>
  <tr><td>Parcel</td><td>{parcel}</td></tr>
  <tr><td>Closing date</td><td>{close_date}</td></tr>
  <tr><td>Closing agent</td><td>{g['title_firm_name']} ◆ {g['title_firm_metro']}, {g['title_firm_state']}</td></tr>
</table>

<h2>Buyer Side (Assignee)</h2>
<table class="terms-table">
  <tr><td>Total purchase consideration</td><td><span class="money">{_money_dec(chris_pays)}</span></td></tr>
  <tr><td>Less: GFAD already in escrow</td><td>({_money_dec(gfad)})</td></tr>
  <tr><td>Cash due at closing from Buyer</td><td><span class="money">{_money_dec(chris_balance)}</span></td></tr>
  <tr><td>Plus: back property tax</td><td>est. {_money_dec(back_tax)}</td></tr>
  <tr><td>Plus: title insurance</td><td>est. {_money_dec(title_ins)}</td></tr>
  <tr><td>Plus: recording fees</td><td>est. {_money_dec(recording)}</td></tr>
  <tr><td>Plus: closing fee</td><td>est. {_money_dec(title_fee)}</td></tr>
  <tr><td><strong>Total wire from Buyer</strong></td><td><span class="money"><strong>{_money_dec(total_buyer_wire)}</strong></span></td></tr>
</table>

<h2>Seller Side</h2>
<table class="terms-table">
  <tr><td>Gross purchase price</td><td><span class="money">{_money_dec(final_seller)}</span></td></tr>
  <tr><td>Net cash to Seller</td><td><span class="money"><strong>{_money_dec(final_seller)}</strong></span> (no closing costs charged to seller)</td></tr>
</table>

<h2>Assignor Side (Everlight)</h2>
<table class="terms-table">
  <tr><td>Assignment fee earned</td><td><span class="money">{_money_dec(assignment_fee)}</span></td></tr>
  <tr><td>Less: GFAD received</td><td>({_money_dec(gfad)})</td></tr>
  <tr><td>Plus: EMD refund</td><td>+ {_money_dec(emd)}</td></tr>
  <tr><td><strong>Total Assignor receives at close</strong></td><td><span class="money"><strong>{_money_dec(assignor_total)}</strong></span></td></tr>
</table>

<p>The actual settlement statement will be generated by {g['title_firm_name']} on the day of closing. All numbers above are estimates based on agreed terms; the title firm will reconcile against the final ALTA settlement statement at closing. You will sign a copy before any wire releases.</p>
"""
    deal_meta_for_wrap = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"Seller ◆ Buyer/Assignee ◆ {g['buyer_dba']} (Assignor)",
    }
    return wrap("Settlement Statement Preview", body, deal_meta_for_wrap,
                 doc_label="Settlement Statement · Preview")


def render_index(meta: dict, g: dict) -> str:
    final_seller = int(meta["final_to_seller"])
    chris_pays = int(meta.get("final_to_buyer", final_seller + 3590))
    assignment_fee = chris_pays - final_seller
    gfad = int(meta.get("gfad_usd", 1000))
    parcel = meta.get("parcel_id", ""); addr = meta.get("property_address", "")
    seller = meta.get("seller_name", "")
    days = int(meta.get("inspection_days", 14))
    close_date = _close_date(days)
    eff = datetime.now().strftime("%B %d, %Y")

    body = f"""
<div class="banner">Active Deal ◆ Negotiated {_money(final_seller)} ◆ Pending signatures</div>

<h2>Deal Snapshot</h2>
<table class="terms-table">
  <tr><td>Property</td><td>{addr}</td></tr>
  <tr><td>Parcel</td><td>{parcel}</td></tr>
  <tr><td>Seller</td><td>{seller}</td></tr>
  <tr><td>Buyer</td><td>{g['buyer_legal_name']} dba {g['buyer_dba']}</td></tr>
  <tr><td>Assignee</td><td>{g['buyer_assignee_name']} ({g['buyer_assignee_signer']})</td></tr>
  <tr><td>Negotiated price</td><td><span class="money">{_money(final_seller)}</span> to Seller</td></tr>
  <tr><td>Assignee pays</td><td><span class="money">{_money(chris_pays)}</span></td></tr>
  <tr><td>Our assignment fee</td><td><span class="money">{_money(assignment_fee)}</span></td></tr>
  <tr><td>Effective date</td><td>{eff}</td></tr>
  <tr><td>Target close</td><td>on or before {close_date}</td></tr>
</table>

<h2>Seller Documents (signs first)</h2>
<ol>
  <li><a href="01_PSA.html">Purchase and Sale Agreement</a></li>
  <li><a href="02_Schedule_A_TN_SB909.html">Schedule A ◆ TN SB 909 Wholesaler Disclosure</a></li>
  <li><a href="03_EMD_Wire_Acknowledgment.html">Earnest Money Wire Acknowledgment</a></li>
</ol>

<h2>Buyer Documents (signs after)</h2>
<ol start="4">
  <li><a href="04_Assignment_Agreement_Chris.html">Assignment Agreement</a></li>
  <li><a href="05_Settlement_Statement_Preview.html">Settlement Statement Preview</a></li>
</ol>
"""
    deal_meta_for_wrap = {
        "deal_id": meta["deal_key"],
        "property": f"{addr}, parcel {parcel}",
        "parties": f"{seller} ◆ {g['buyer_legal_name']} ◆ {g['buyer_assignee_signer']}",
    }
    return wrap(f"Deal: {_addr_short(addr)}", body, deal_meta_for_wrap,
                 doc_label="Active Deal Index")


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def render_all_contracts(deal_key: str, force: bool = False) -> dict:
    """Render the 5 contract HTMLs + index for a deal. Returns paths written."""
    meta_path = DEALS_DIR / deal_key / "deal_meta.json"
    if not meta_path.exists():
        return {"ok": False, "error": f"deal_meta.json not found at {meta_path}"}
    meta = json.loads(meta_path.read_text())
    g = load_global_config()

    deal_dir = DEALS_DIR / deal_key
    deal_dir.mkdir(parents=True, exist_ok=True)

    docs = {
        "01_PSA.html": render_psa,
        "02_Schedule_A_TN_SB909.html": render_schedule_a,
        "03_EMD_Wire_Acknowledgment.html": render_emd_ack,
        "04_Assignment_Agreement_Chris.html": render_assignment,
        "05_Settlement_Statement_Preview.html": render_settlement_preview,
        "index.html": render_index,
    }
    written = []
    skipped = []
    for filename, fn in docs.items():
        path = deal_dir / filename
        if path.exists() and not force:
            skipped.append(filename); continue
        path.write_text(fn(meta, g))
        written.append(filename)
    return {"ok": True, "deal_dir": str(deal_dir), "written": written, "skipped": skipped}


def ensure_contracts(deal_key: str) -> dict:
    """Render contracts only if they don't already exist (idempotent)."""
    return render_all_contracts(deal_key, force=False)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: contract_renderer.py <deal_key> [--force]")
        sys.exit(1)
    force = "--force" in sys.argv
    result = render_all_contracts(sys.argv[1], force=force)
    print(json.dumps(result, indent=2))
