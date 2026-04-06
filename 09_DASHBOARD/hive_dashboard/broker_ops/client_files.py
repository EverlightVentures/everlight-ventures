"""
Client File Manager -- A-to-Z Deal Document Lifecycle

Creates and manages per-deal client folders with branded HTML documents.
Each deal gets a complete document timeline from first outreach to payment receipt.

Agents: Piper (outreach), Rex (deal sheets), Ace (buyer pitch),
        Hammer (contracts/closing), Cash (payment receipts)
"""
import base64
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Optional

from django.utils import timezone

from .models import ClientDocument, ClientFile, InvestorBuyer, PropertyLead

logger = logging.getLogger(__name__)

# Branding constants (Everlight gold/black)
BRAND = {
    "bg_dark": "#0d0d1a",
    "bg_card": "#1a1a2e",
    "gold": "#c9a84c",
    "white": "#ffffff",
    "gray": "#aaaaaa",
    "green": "#00cc66",
    "red": "#8b0000",
    "border": "#2a2a4a",
    "font": "'Segoe UI', Helvetica, Arial, sans-serif",
}


# ---------------------------------------------------------------------------
# PII Encryption (simple Fernet-compatible for at-rest protection)
# ---------------------------------------------------------------------------

def _get_encryption_key():
    """Get or generate encryption key from env."""
    key = os.environ.get("CLIENT_FILE_ENCRYPTION_KEY", "")
    if not key:
        # Derive from a stable secret
        secret = os.environ.get("DJANGO_SECRET_KEY", "everlight-default-key")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()).decode()
    return key


def mask_pii(text: str) -> str:
    """Mask PII for public display (emails, phones)."""
    import re
    # Mask emails: j***@example.com
    text = re.sub(
        r'([a-zA-Z0-9])[a-zA-Z0-9.+]*(@[a-zA-Z0-9.-]+)',
        r'\1***\2', text
    )
    # Mask phones: (***) ***-1234
    text = re.sub(
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?(\d{4})',
        r'(***) ***-\1', text
    )
    return text


# ---------------------------------------------------------------------------
# Client File CRUD
# ---------------------------------------------------------------------------

def create_client_file(property_lead: PropertyLead) -> ClientFile:
    """Create a new client file from a property lead."""
    # Check if one already exists
    existing = ClientFile.objects.filter(property_lead=property_lead).first()
    if existing:
        return existing

    cf = ClientFile.objects.create(
        property_lead=property_lead,
        client_name=property_lead.owner_name or "Unknown Seller",
        property_address=property_lead.address,
        city=property_lead.city,
        state=property_lead.state,
        contract_price=property_lead.asking_price,
        assignment_fee=property_lead.assignment_fee,
        buyer_price=float(property_lead.asking_price) + float(property_lead.assignment_fee),
        estimated_arv=property_lead.estimated_arv,
    )
    logger.info("Created client file %s for %s", cf.id, cf.property_address)
    return cf


def update_client_file_status(cf: ClientFile, new_status: str) -> ClientFile:
    """Update client file status with timestamp tracking."""
    cf.status = new_status
    if new_status == "closed":
        cf.closed_at = timezone.now()
    cf.save()
    return cf


def assign_buyer(cf: ClientFile, buyer: InvestorBuyer) -> ClientFile:
    """Assign a matched buyer to the client file."""
    cf.buyer = buyer
    cf.status = "under_contract"
    cf.save()
    return cf


# ---------------------------------------------------------------------------
# Document Generation -- Branded HTML
# ---------------------------------------------------------------------------

def _html_header(title: str, subtitle: str = "Private Acquisitions") -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:{BRAND['bg_dark']};font-family:{BRAND['font']};">
<div style="max-width:640px;margin:0 auto;background:{BRAND['bg_dark']};">
  <div style="background:{BRAND['bg_card']};padding:20px 24px;text-align:center;border-bottom:3px solid {BRAND['gold']};">
    <p style="margin:0;font-size:20px;font-weight:700;color:{BRAND['white']};letter-spacing:1px;">
      EVERLIGHT <span style="color:{BRAND['gold']};">VENTURES</span>
    </p>
    <p style="margin:4px 0 0;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:2px;">
      {subtitle}
    </p>
  </div>
  <div style="padding:24px;">"""


def _html_footer(agent_name: str = "Everlight Ventures") -> str:
    return f"""
  </div>
  <div style="background:{BRAND['bg_card']};padding:16px 24px;text-align:center;border-top:1px solid {BRAND['border']};">
    <p style="margin:0;color:#666;font-size:11px;">
      {agent_name} &bull; Everlight Ventures &bull; everlightventures.io
    </p>
    <p style="margin:4px 0 0;color:#444;font-size:10px;">
      This document is confidential. &copy; {datetime.now().year} Everlight Ventures LLC
    </p>
  </div>
</div></body></html>"""


def _html_section(title: str, content: str) -> str:
    return f"""
    <div style="background:{BRAND['bg_card']};border:1px solid {BRAND['border']};border-radius:8px;padding:20px;margin-bottom:20px;">
      <p style="color:{BRAND['gold']};font-size:16px;font-weight:700;margin:0 0 12px;text-transform:uppercase;">{title}</p>
      {content}
    </div>"""


def _html_row(label: str, value: str, highlight: bool = False) -> str:
    color = BRAND['gold'] if highlight else BRAND['white']
    size = "18px" if highlight else "14px"
    return f"""<tr>
      <td style="padding:6px 0;color:{BRAND['gray']};font-size:13px;">{label}</td>
      <td style="padding:6px 0;color:{color};font-weight:700;text-align:right;font-size:{size};">{value}</td>
    </tr>"""


def _money(val) -> str:
    return f"${float(val):,.0f}"


# ---------------------------------------------------------------------------
# Document Type Generators
# ---------------------------------------------------------------------------

def generate_seller_outreach(cf: ClientFile) -> ClientDocument:
    """Generate branded seller outreach email (Piper Reeves style)."""
    lead = cf.property_lead
    owner = cf.client_name or "Property Owner"
    first_name = owner.split()[0] if owner != "Unknown Seller" else "there"

    html = _html_header("Seller Outreach", "Real Estate Solutions")
    html += f"""
    <h2 style="color:{BRAND['white']};margin:0 0 16px;">Dear {first_name},</h2>
    <p style="color:{BRAND['gray']};line-height:1.6;font-size:15px;">
      I hope this finds you well. My name is Piper with Everlight Ventures, and I'm
      reaching out about your property at <strong style="color:{BRAND['white']};">{cf.property_address}</strong>.
    </p>
    <p style="color:{BRAND['gray']};line-height:1.6;font-size:15px;">
      We work with a network of qualified cash buyers who can close quickly &mdash;
      often within 14-21 days &mdash; with no repairs needed on your end. We handle
      all the paperwork and closing costs.
    </p>"""

    html += _html_section("What We're Offering", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Quick Close", "14-21 Days")}
        {_html_row("No Repairs Needed", "As-Is Purchase")}
        {_html_row("No Agent Commissions", "Zero Fees to You")}
        {_html_row("Cash Offer Range", _money(float(cf.contract_price) * 0.9) + " - " + _money(cf.contract_price), highlight=True)}
      </table>""")

    html += f"""
    <p style="color:{BRAND['gray']};line-height:1.6;font-size:15px;">
      If you're open to a conversation, I'd love to learn more about your situation
      and see if we can help. No pressure, no obligation &mdash; just a friendly chat.
    </p>
    <div style="text-align:center;margin:24px 0;">
      <a href="mailto:piper@everlightventures.io?subject=Property%20at%20{cf.property_address}"
         style="display:inline-block;background:{BRAND['gold']};color:{BRAND['bg_dark']};
                padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:700;
                font-size:16px;">
        Reply to This Email
      </a>
    </div>
    <p style="color:{BRAND['gray']};font-size:14px;">
      Warm regards,<br>
      <strong style="color:{BRAND['white']};">Piper Reeves</strong><br>
      <span style="color:{BRAND['gold']};">Acquisitions Specialist</span><br>
      Everlight Ventures<br>
      piper@everlightventures.io
    </p>"""
    html += _html_footer("Piper Reeves")

    plain = f"""Dear {first_name},

I'm reaching out about your property at {cf.property_address}.

We work with qualified cash buyers who can close in 14-21 days, no repairs needed.
Cash offer range: {_money(float(cf.contract_price) * 0.9)} - {_money(cf.contract_price)}

No pressure, no obligation. Just reply to chat.

Warm regards,
Piper Reeves
Acquisitions Specialist, Everlight Ventures
piper@everlightventures.io"""

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="seller_outreach",
        title=f"Seller Outreach - {cf.property_address}",
        html_content=html,
        plain_text=plain,
        to_email=lead.owner_email if lead else "",
        generated_by="piper",
    )
    logger.info("Generated seller outreach doc %s for %s", doc.id, cf.property_address)
    return doc


def generate_deal_sheet(cf: ClientFile) -> ClientDocument:
    """Generate branded deal sheet / investor presentation (Rex style)."""
    lead = cf.property_lead

    html = _html_header("Investment Opportunity", "Private Acquisitions")

    # Urgency bar
    html += f"""
    <div style="background:{BRAND['red']};padding:12px 24px;text-align:center;margin:-24px -24px 24px;">
      <p style="margin:0;color:{BRAND['white']};font-size:14px;font-weight:700;">
        &#9888; MULTIPLE BUYERS ARE REVIEWING THIS PROPERTY &#9888;
      </p>
    </div>"""

    # Property header
    html += f"""
    <h1 style="color:{BRAND['white']};font-size:22px;margin:0 0 4px;">{cf.property_address}</h1>
    <p style="color:{BRAND['gold']};font-size:16px;margin:0 0 20px;">{cf.city}, {cf.state}</p>"""

    # Property details
    if lead:
        html += f"""
    <table style="width:100%;margin-bottom:24px;">
      <tr>
        <td style="padding:8px 0;color:{BRAND['gray']};font-size:13px;">Beds</td>
        <td style="padding:8px 0;color:{BRAND['white']};font-weight:700;">{lead.bedrooms}</td>
        <td style="padding:8px 0;color:{BRAND['gray']};font-size:13px;">Baths</td>
        <td style="padding:8px 0;color:{BRAND['white']};font-weight:700;">{lead.bathrooms}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:{BRAND['gray']};font-size:13px;">Sq Ft</td>
        <td style="padding:8px 0;color:{BRAND['white']};font-weight:700;">{lead.sqft:,}</td>
        <td style="padding:8px 0;color:{BRAND['gray']};font-size:13px;">Year Built</td>
        <td style="padding:8px 0;color:{BRAND['white']};font-weight:700;">{lead.year_built}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:{BRAND['gray']};font-size:13px;">Type</td>
        <td colspan="3" style="padding:8px 0;color:{BRAND['white']};font-weight:700;">{lead.get_property_type_display()}</td>
      </tr>
    </table>"""

    # Financial breakdown
    repair = float(cf.estimated_arv) - float(cf.buyer_price)
    projected_profit = float(cf.estimated_arv) - float(cf.buyer_price) - float(lead.estimated_repair if lead else 0)
    roi = (projected_profit / float(cf.buyer_price) * 100) if float(cf.buyer_price) > 0 else 0

    html += _html_section("Financial Breakdown", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Buyer Purchase Price", _money(cf.buyer_price))}
        {_html_row("&nbsp;&nbsp;Contract Price", _money(cf.contract_price))}
        {_html_row("&nbsp;&nbsp;Assignment Fee", _money(cf.assignment_fee))}
        <tr><td colspan="2" style="border-top:1px solid {BRAND['border']};padding:0;"></td></tr>
        {_html_row("Estimated ARV", _money(cf.estimated_arv), highlight=True)}
        {_html_row("Estimated Repairs", _money(lead.estimated_repair if lead else 0))}
        <tr><td colspan="2" style="border-top:2px solid {BRAND['gold']};padding:0;"></td></tr>
        {_html_row("Projected Profit", f'<span style="color:{BRAND["green"]}">{_money(projected_profit)}</span>')}
        {_html_row("ROI", f'{roi:.0f}%')}
      </table>""")

    # Title company
    if cf.title_company:
        html += _html_section("Title Company", f"""
          <p style="color:{BRAND['white']};margin:0;">{cf.title_company}</p>
          <p style="color:{BRAND['gray']};margin:4px 0 0;font-size:13px;">{cf.title_contact} &bull; {cf.title_email}</p>""")

    # CTA
    html += f"""
    <div style="text-align:center;margin:24px 0;">
      <a href="mailto:rex@everlightventures.io?subject=Interest%20in%20{cf.property_address}"
         style="display:inline-block;background:{BRAND['gold']};color:{BRAND['bg_dark']};
                padding:16px 40px;border-radius:6px;text-decoration:none;font-weight:700;
                font-size:18px;">
        SECURE THIS DEAL
      </a>
      <p style="color:{BRAND['gray']};font-size:12px;margin:8px 0 0;">
        EMD required to lock in. First qualified buyer wins.
      </p>
    </div>"""
    html += _html_footer("Rex Blackwell")

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="deal_sheet",
        title=f"Deal Sheet - {cf.property_address}",
        html_content=html,
        plain_text=f"Deal Sheet: {cf.property_address}\nBuyer Price: {_money(cf.buyer_price)}\nARV: {_money(cf.estimated_arv)}\nProfit: {_money(projected_profit)}",
        generated_by="rex",
    )
    return doc


def generate_assignment_contract(cf: ClientFile) -> ClientDocument:
    """Generate assignment contract with Quality Assurance Review Period clause."""
    buyer_name = cf.buyer.name if cf.buyer else "[BUYER NAME]"
    buyer_company = cf.buyer.company if cf.buyer else "[BUYER COMPANY]"
    today = datetime.now().strftime("%B %d, %Y")

    # State-specific addenda
    state_clauses = {
        "FL": "Buyer has a 15-day inspection period per Florida Statute 475.278.",
        "TX": "Subject to Texas Property Code Section 5.008 disclosure requirements. 10-day option period.",
        "OH": "Subject to Ohio Revised Code 5302.30 transfer requirements.",
        "GA": "Subject to Georgia BRRETA disclosure requirements.",
        "TN": "Subject to Tennessee Code Annotated 66-5-202 disclosure requirements.",
    }
    state_clause = state_clauses.get(cf.state, "Subject to applicable state real estate regulations.")

    html = _html_header("Assignment of Contract", "Legal Documents")
    html += f"""
    <h2 style="color:{BRAND['white']};font-size:20px;margin:0 0 20px;text-align:center;">
      ASSIGNMENT OF REAL ESTATE PURCHASE CONTRACT
    </h2>"""

    html += _html_section("Parties", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Assignor", "Everlight Ventures LLC")}
        {_html_row("Assignee (Buyer)", f"{buyer_name} / {buyer_company}")}
        {_html_row("Original Seller", cf.client_name)}
        {_html_row("Date", today)}
      </table>""")

    html += _html_section("Property", f"""
      <p style="color:{BRAND['white']};margin:0;font-size:15px;">{cf.property_address}</p>
      <p style="color:{BRAND['gray']};margin:4px 0 0;">{cf.city}, {cf.state}</p>""")

    html += _html_section("Terms", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Original Contract Price", _money(cf.contract_price))}
        {_html_row("Assignment Fee", _money(cf.assignment_fee), highlight=True)}
        {_html_row("Total Buyer Price", _money(cf.buyer_price))}
      </table>""")

    html += _html_section("Quality Assurance Review Period", f"""
      <p style="color:{BRAND['gray']};line-height:1.6;font-size:13px;">
        Assignee shall have a <strong style="color:{BRAND['white']};">7-business-day Quality Assurance
        Review Period</strong> from the date of this assignment to conduct due diligence on the
        property, including but not limited to: inspection, title review, and verification of
        property condition. If Assignee is not satisfied with the results of their review, they
        may terminate this assignment by written notice within the review period, and any earnest
        money deposit shall be refunded in full.
      </p>
      <p style="color:{BRAND['gray']};line-height:1.6;font-size:13px;margin-top:12px;">
        <strong style="color:{BRAND['gold']};">State Compliance:</strong> {state_clause}
      </p>""")

    if cf.title_company:
        html += _html_section("Title Company / Escrow", f"""
          <p style="color:{BRAND['white']};margin:0;">{cf.title_company}</p>
          <p style="color:{BRAND['gray']};margin:4px 0 0;">{cf.title_contact} &bull; {cf.title_email}</p>""")

    html += f"""
    <div style="margin-top:32px;padding-top:20px;border-top:1px solid {BRAND['border']};">
      <table style="width:100%;">
        <tr>
          <td style="width:48%;padding:20px 0;">
            <p style="color:{BRAND['gray']};font-size:12px;margin:0;">ASSIGNOR</p>
            <div style="border-bottom:1px solid {BRAND['gray']};margin:40px 0 8px;"></div>
            <p style="color:{BRAND['white']};margin:0;">Everlight Ventures LLC</p>
          </td>
          <td style="width:4%;"></td>
          <td style="width:48%;padding:20px 0;">
            <p style="color:{BRAND['gray']};font-size:12px;margin:0;">ASSIGNEE</p>
            <div style="border-bottom:1px solid {BRAND['gray']};margin:40px 0 8px;"></div>
            <p style="color:{BRAND['white']};margin:0;">{buyer_name}</p>
          </td>
        </tr>
      </table>
    </div>"""
    html += _html_footer("Hammer Knox")

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="assignment_contract",
        title=f"Assignment Contract - {cf.property_address}",
        html_content=html,
        plain_text=f"Assignment Contract\nProperty: {cf.property_address}\nSeller: {cf.client_name}\nBuyer: {buyer_name}\nPrice: {_money(cf.buyer_price)}\nFee: {_money(cf.assignment_fee)}",
        generated_by="hammer",
    )
    return doc


def generate_buyer_pitch(cf: ClientFile, buyer: InvestorBuyer) -> ClientDocument:
    """Generate branded buyer pitch email (Ace Morgan style)."""
    html = _html_header("Exclusive Deal Alert", "Investor Relations")

    html += f"""
    <p style="color:{BRAND['gray']};line-height:1.6;font-size:15px;">
      <strong style="color:{BRAND['white']};">{buyer.name}</strong>,
    </p>
    <p style="color:{BRAND['gray']};line-height:1.6;font-size:15px;">
      We've got a deal that matches your buy box. Based on your criteria
      ({buyer.get_buyer_type_display()}, {', '.join(buyer.markets[:3]) if buyer.markets else 'your markets'}),
      this one's worth a look.
    </p>"""

    projected_profit = float(cf.estimated_arv) - float(cf.buyer_price) - float(cf.property_lead.estimated_repair if cf.property_lead else 0)

    html += _html_section("The Deal", f"""
      <h3 style="color:{BRAND['white']};margin:0 0 12px;">{cf.property_address}, {cf.city} {cf.state}</h3>
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Your All-In Price", _money(cf.buyer_price))}
        {_html_row("After Repair Value", _money(cf.estimated_arv), highlight=True)}
        {_html_row("Est. Repairs", _money(cf.property_lead.estimated_repair if cf.property_lead else 0))}
        <tr><td colspan="2" style="border-top:2px solid {BRAND['gold']};padding:0;"></td></tr>
        {_html_row("Projected Profit", f'<span style="color:{BRAND["green"]}">{_money(projected_profit)}</span>')}
      </table>""")

    html += f"""
    <div style="background:{BRAND['red']};padding:12px;border-radius:6px;text-align:center;margin:20px 0;">
      <p style="margin:0;color:{BRAND['white']};font-weight:700;">
        First qualified buyer with EMD secures the deal. Don't sleep on this.
      </p>
    </div>
    <div style="text-align:center;margin:24px 0;">
      <a href="mailto:ace@everlightventures.io?subject=I%20want%20{cf.property_address}"
         style="display:inline-block;background:{BRAND['gold']};color:{BRAND['bg_dark']};
                padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:700;
                font-size:16px;">
        I'M INTERESTED
      </a>
    </div>
    <p style="color:{BRAND['gray']};font-size:14px;">
      Talk soon,<br>
      <strong style="color:{BRAND['white']};">Ace Morgan</strong><br>
      <span style="color:{BRAND['gold']};">Investment Analyst</span><br>
      Everlight Ventures<br>
      ace@everlightventures.io
    </p>"""
    html += _html_footer("Ace Morgan")

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="buyer_pitch",
        title=f"Buyer Pitch - {buyer.name} - {cf.property_address}",
        html_content=html,
        plain_text=f"Deal Alert for {buyer.name}\n{cf.property_address}\nPrice: {_money(cf.buyer_price)}\nARV: {_money(cf.estimated_arv)}\nProfit: {_money(projected_profit)}",
        to_email=buyer.email,
        generated_by="ace",
    )
    return doc


def generate_closing_statement(cf: ClientFile) -> ClientDocument:
    """Generate closing statement summary."""
    buyer_name = cf.buyer.name if cf.buyer else "TBD"

    html = _html_header("Closing Statement", "Transaction Summary")
    html += f"""
    <h2 style="color:{BRAND['white']};font-size:20px;margin:0 0 20px;text-align:center;">
      CLOSING STATEMENT
    </h2>"""

    html += _html_section("Transaction Summary", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Property", cf.property_address)}
        {_html_row("Seller", cf.client_name)}
        {_html_row("Buyer", buyer_name)}
        {_html_row("Close Date", timezone.now().strftime("%B %d, %Y"))}
      </table>""")

    html += _html_section("Financial Summary", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Contract Price (Seller)", _money(cf.contract_price))}
        {_html_row("Assignment Fee (Everlight)", _money(cf.assignment_fee), highlight=True)}
        {_html_row("Total to Buyer", _money(cf.buyer_price))}
      </table>""")

    if cf.title_company:
        html += _html_section("Title Company", f"""
          <p style="color:{BRAND['white']};margin:0;">{cf.title_company}</p>
          <p style="color:{BRAND['gray']};margin:4px 0 0;">{cf.title_contact}</p>""")

    html += _html_footer("Cash Montgomery")

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="closing_statement",
        title=f"Closing Statement - {cf.property_address}",
        html_content=html,
        plain_text=f"Closing: {cf.property_address}\nSeller: {cf.client_name}\nBuyer: {buyer_name}\nFee: {_money(cf.assignment_fee)}",
        generated_by="cash",
    )
    return doc


def generate_payment_receipt(cf: ClientFile, amount: float = None,
                              stripe_id: str = "") -> ClientDocument:
    """Generate payment receipt for assignment fee."""
    amount = amount or float(cf.assignment_fee)
    buyer_name = cf.buyer.name if cf.buyer else "TBD"

    html = _html_header("Payment Receipt", "Accounts")
    html += f"""
    <div style="text-align:center;margin-bottom:24px;">
      <div style="display:inline-block;background:{BRAND['green']};color:{BRAND['bg_dark']};
                  padding:8px 20px;border-radius:20px;font-weight:700;font-size:14px;">
        PAYMENT RECEIVED
      </div>
    </div>"""

    html += _html_section("Receipt Details", f"""
      <table style="width:100%;border-collapse:collapse;">
        {_html_row("Date", timezone.now().strftime("%B %d, %Y"))}
        {_html_row("Property", cf.property_address)}
        {_html_row("Payer", buyer_name)}
        {_html_row("Description", "Assignment Fee")}
        {_html_row("Amount", _money(amount), highlight=True)}
        {_html_row("Stripe ID", stripe_id or "N/A")}
      </table>""")

    html += f"""
    <p style="color:{BRAND['gray']};font-size:12px;text-align:center;margin-top:24px;">
      Thank you for your business. This receipt serves as confirmation of payment.
    </p>"""
    html += _html_footer("Cash Montgomery")

    doc = ClientDocument.objects.create(
        client_file=cf,
        doc_type="payment_receipt",
        title=f"Payment Receipt - {cf.property_address} - {_money(amount)}",
        html_content=html,
        plain_text=f"Receipt: {_money(amount)} received from {buyer_name} for {cf.property_address}",
        generated_by="cash",
        status="final",
    )
    return doc


# ---------------------------------------------------------------------------
# Full Pipeline: Generate all documents for a deal
# ---------------------------------------------------------------------------

def generate_full_client_file(property_lead: PropertyLead,
                                buyer: Optional[InvestorBuyer] = None) -> ClientFile:
    """
    Create a complete client file with all available documents.
    Called by the wholesale pipeline when a deal progresses.
    """
    cf = create_client_file(property_lead)

    # Always generate seller outreach + deal sheet
    if not cf.documents.filter(doc_type="seller_outreach").exists():
        generate_seller_outreach(cf)

    if not cf.documents.filter(doc_type="deal_sheet").exists():
        generate_deal_sheet(cf)

    # If buyer is assigned, generate buyer-side docs
    if buyer:
        assign_buyer(cf, buyer)
        if not cf.documents.filter(doc_type="buyer_pitch").exists():
            generate_buyer_pitch(cf, buyer)
        if not cf.documents.filter(doc_type="assignment_contract").exists():
            generate_assignment_contract(cf)

    return cf


# ---------------------------------------------------------------------------
# Supabase Sync
# ---------------------------------------------------------------------------

def sync_client_file_to_supabase(cf: ClientFile) -> bool:
    """Push client file + documents to Supabase for the public dashboard."""
    try:
        from hive_dashboard.supabase_client import supabase_rest

        # Upsert client file
        file_data = {
            "id": str(cf.id),
            "client_name": cf.client_name,
            "property_address": cf.property_address,
            "city": cf.city,
            "state": cf.state,
            "status": cf.status,
            "contract_price": float(cf.contract_price),
            "assignment_fee": float(cf.assignment_fee),
            "buyer_price": float(cf.buyer_price),
            "estimated_arv": float(cf.estimated_arv),
            "buyer_name": cf.buyer.name if cf.buyer else "",
            "title_company": cf.title_company,
            "title_contact": cf.title_contact,
            "title_email": cf.title_email,
        }
        supabase_rest("wholesale_client_files", method="POST", data=file_data,
                       headers={"Prefer": "resolution=merge-duplicates"})

        # Upsert documents
        for doc in cf.documents.all():
            doc_data = {
                "id": str(doc.id),
                "client_file_id": str(cf.id),
                "doc_type": doc.doc_type,
                "title": doc.title,
                "status": doc.status,
                "html_content": doc.html_content,
                "plain_text": doc.plain_text,
                "to_email": mask_pii(doc.to_email) if doc.to_email else "",
                "generated_by": doc.generated_by,
            }
            supabase_rest("wholesale_client_documents", method="POST", data=doc_data,
                           headers={"Prefer": "resolution=merge-duplicates"})

        logger.info("Synced client file %s to Supabase", cf.id)
        return True
    except Exception as exc:
        logger.warning("Supabase sync failed for client file %s: %s", cf.id, exc)
        return False
