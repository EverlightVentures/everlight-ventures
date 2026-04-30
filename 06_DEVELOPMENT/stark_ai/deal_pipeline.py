"""
Deal Pipeline -- Full end-to-end deal execution.
Called by post_call_executor when a deal needs to progress.

Stages:
1. INTEREST  -- prospect shows interest (reply, call, booking)
2. COMPLIANCE -- Justine Park reviews for legal/regulatory issues
3. CONTRACT  -- Harrison Knox generates and sends finder agreement
4. TITLE     -- Title company coordination (wholesale only)
5. CLOSE     -- Money changes hands, commission collected
6. COMPLETE  -- Logged, tallied, added to portfolio

Each stage fires emails, Slack posts, and updates Supabase.
"""
import json
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load creds
_env = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
if not _env.exists():
    _env = Path("/home/opc/.env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

RESEND_KEY = os.getenv("RESEND_API_KEY", "")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")
N8N_URL = os.getenv("N8N_URL", "http://129.159.38.250:5678")
RICH_EMAIL = "1m.rich.gee@gmail.com"

# Title companies by market
TITLE_COMPANIES = {
    "cleveland": {"name": "First American Title - Cleveland", "email": "closings@firstam-cle.com", "phone": "(216) 555-0100"},
    "atlanta": {"name": "Stewart Title - Atlanta", "email": "closings@stewart-atl.com", "phone": "(404) 555-0200"},
    "dallas": {"name": "Chicago Title - Dallas", "email": "closings@chicagotitle-dal.com", "phone": "(214) 555-0300"},
    "jacksonville": {"name": "Fidelity National Title - JAX", "email": "closings@fidelity-jax.com", "phone": "(904) 555-0400"},
    "st louis": {"name": "Old Republic Title - STL", "email": "closings@oldrepublic-stl.com", "phone": "(314) 555-0500"},
    "default": {"name": "First American Title", "email": "closings@firstam.com", "phone": "(800) 555-0100"},
}


def _send_branded_email(from_agent, to_email, to_name, subject, body_html):
    """Send Everlight branded email."""
    agents = {
        "piper": {"from": "Piper Reeves <piper@everlightventures.io>", "name": "Piper Reeves", "title": "Senior Account Executive", "email": "piper@everlightventures.io", "phone": "(707) 801-0360"},
        "harrison": {"from": "Harrison Knox <hammer@everlightventures.io>", "name": "Harrison Knox", "title": "Deal Operations", "email": "hammer@everlightventures.io", "phone": "(888) 896-6772"},
        "justine": {"from": "Justine Park <justine@everlightventures.io>", "name": "Justine Park", "title": "Compliance Officer", "email": "justine@everlightventures.io", "phone": "(888) 896-6772"},
        "marcus": {"from": "Marcus Cole <marcus@everlightventures.io>", "name": "Marcus Cole", "title": "Chief Operator", "email": "marcus@everlightventures.io", "phone": "(888) 896-6772"},
    }
    sig = agents.get(from_agent, agents["piper"])

    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body {{ margin:0; padding:0; background:#0A0A0A; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
.wrap {{ max-width:600px; margin:0 auto; background:#0A0A0A; }}
.hdr {{ background:linear-gradient(135deg,#0A0A0A,#1A1A1A); border-bottom:2px solid #D4A843; padding:24px 32px; text-align:center; }}
.logo {{ font-size:11px; letter-spacing:4px; color:#D4A843; text-transform:uppercase; margin-bottom:4px; }}
.hdr h1 {{ font-size:18px; color:#E8E8E8; font-weight:600; margin:0; }}
.body {{ padding:32px; color:#E8E8E8; font-size:15px; line-height:1.7; }}
.body p {{ margin-bottom:16px; }}
.body strong {{ color:#D4A843; }}
.body ul {{ margin:0 0 16px 20px; }}
.body li {{ margin-bottom:8px; }}
.body a {{ color:#D4A843; }}
.sig {{ margin-top:32px; padding-top:20px; border-top:1px solid #222; }}
.sig-name {{ color:#D4A843; font-weight:600; font-size:15px; }}
.sig-role {{ color:#999; font-size:13px; }}
.sig-contact {{ color:#999; font-size:12px; margin-top:4px; }}
.ftr {{ text-align:center; padding:24px; color:#666; font-size:11px; border-top:1px solid #1a1a1a; }}
.ftr .brand {{ color:#D4A843; font-size:12px; letter-spacing:2px; }}
</style></head>
<body><div class="wrap">
<div class="hdr">
  <div class="logo">Everlight Ventures</div>
  <h1>{subject}</h1>
</div>
<div class="body">
  <p>Hey {to_name},</p>
  {body_html}
  <div class="sig">
    <div class="sig-name">{sig_name}</div>
    <div class="sig-role">{sig_title}</div>
    <div class="sig-contact">{sig_email} | {sig_phone}<br>everlightventures.io</div>
  </div>
</div>
<div class="ftr">
  <div class="brand">EVERLIGHT VENTURES</div>
  <p style="margin-top:6px;">The Mind Behind the Money</p>
</div>
</div></body></html>""".format(
        subject=subject, to_name=to_name, body_html=body_html,
        sig_name=sig["name"], sig_title=sig["title"],
        sig_email=sig["email"], sig_phone=sig["phone"],
    )

    # Owner-bound notifications go to Slack, not Resend (owner directive 2026-04-23).
    # Resend is reserved for external candidates: sellers, buyers, title companies, clients.
    try:
        import sys as _sys
        _sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from resend_guard import is_owner_recipient
        if is_owner_recipient(to_email):
            _post_slack(
                "[{agent}] {subj} -- would-have-emailed {to} (owner -> slack-only)\n{body}".format(
                    agent=sig["name"], subj=subject, to=to_email, body=body_html[:500]
                ),
            )
            return True  # treat as delivered via Slack
    except Exception:
        pass

    # Route through branded_mailer (master Everlight template, budget gate, owner guard).
    # The inline "html" we built is now ignored -- branded_mailer wraps body_html
    # with the canonical Playfair/Inter gold theme via report_template.render_report().
    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
    except Exception:
        return False

    result = send_branded_email(
        to=to_email,
        subject=subject,
        content_html=body_html,
        title=subject,
        from_name=sig.get("from", sig["name"]).split("<")[0].strip(),
        from_email=sig["email"],
        reply_to=sig["email"],
        agent_name=sig["name"],
        agent_title=sig["title"],
        agent_email=sig["email"],
        budget_category="nurture",
    )
    return bool(result.ok)


def _post_slack(msg, channel="C0ANLLV8JAC"):
    if SLACK_TOKEN:
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer %s" % SLACK_TOKEN, "Content-Type": "application/json"},
            json={"channel": channel, "text": msg}, timeout=10)


def _create_gdoc(title, body_md):
    """Publish a branded Google Doc via the Python replacement (no n8n).

    Routes through gdocs_bridge.publish_report() which applies the Everlight
    gold Playfair/Inter template and posts a branded link to Slack.
    """
    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from n8n_replacements import publish_gdoc  # type: ignore
    except Exception:
        return False
    res = publish_gdoc(title=title, body=body_md, channel="#broker-pipeline", folder_key="broker_scout")
    return bool(res.get("ok"))


# ====================================================================
# STAGE 1: INTEREST -- Prospect shows interest
# ====================================================================

def stage_interest(deal):
    """Prospect replied interested. Notify team, DO NOT send anything to prospect yet.
    Only proceed when interest is confirmed."""
    prospect = deal.get("prospect_name", "Unknown")
    email = deal.get("prospect_email", "")
    source = deal.get("source", "outreach reply")
    deal_type = deal.get("deal_type", "finder_fee")

    # Notify Rich
    _send_branded_email("marcus", RICH_EMAIL, "Rich",
        "New Interest - %s" % prospect,
        """<p><strong>%s</strong> (%s) has shown interest via %s.</p>
<p>Deal type: <strong>%s</strong></p>
<p>Next step: Justine runs compliance check, then Piper follows up.</p>
<p>Pipeline is handling this automatically.</p>""" % (prospect, email, source, deal_type))

    _post_slack("*NEW INTEREST* %s (%s) via %s\nJustine: compliance check\nPiper: follow-up pending compliance" % (prospect, email, source))

    # Auto-advance to compliance
    deal["stage"] = "compliance"
    return stage_compliance(deal)


# ====================================================================
# STAGE 2: COMPLIANCE -- Justine Park reviews
# ====================================================================

def stage_compliance(deal):
    """Justine reviews the deal for legal/regulatory issues."""
    prospect = deal.get("prospect_name", "Unknown")
    email = deal.get("prospect_email", "")
    deal_type = deal.get("deal_type", "finder_fee")

    # Compliance checklist
    issues = []
    if not email or "@" not in email:
        issues.append("No valid email address")
    if deal_type == "wholesale_assignment":
        state = deal.get("state", "").upper()
        # States where wholesale needs a license
        licensed_states = {"IL", "OK", "SC", "OR"}
        if state in licensed_states:
            issues.append("State %s requires RE license for wholesale assignments" % state)
    if deal.get("deal_value", 0) > 50000 and deal_type == "finder_fee":
        issues.append("High-value deal (>$50k) - recommend legal review of finder agreement")

    if issues:
        # Flag for human review
        _send_branded_email("justine", RICH_EMAIL, "Rich",
            "Compliance Flag - %s" % prospect,
            """<p>I flagged some issues on the <strong>%s</strong> deal:</p>
<ul>%s</ul>
<p>Recommend holding on outreach until resolved. Reply to this email to override.</p>""" % (prospect, "".join("<li>%s</li>" % i for i in issues)))

        _post_slack("*COMPLIANCE FLAG* from Justine Park\nDeal: %s\nIssues:\n%s" % (prospect, "\n".join("- %s" % i for i in issues)))
        deal["stage"] = "compliance_hold"
        deal["compliance_issues"] = issues
        return deal

    # Clean - advance to contract
    _post_slack("*COMPLIANCE CLEAR* Justine approved: %s. Advancing to contract stage." % prospect)
    deal["stage"] = "contract"
    return stage_contract(deal)


# ====================================================================
# STAGE 3: CONTRACT -- Harrison Knox sends agreement
# ====================================================================

def stage_contract(deal):
    """Generate and send the appropriate contract."""
    prospect = deal.get("prospect_name", "Unknown")
    email = deal.get("prospect_email", "")
    deal_type = deal.get("deal_type", "finder_fee")
    deal_value = deal.get("deal_value", 5000)
    commission_pct = deal.get("commission_pct", 0.20)
    scope = deal.get("scope", "Partnership introduction")

    # Generate PDF
    try:
        import sys
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS")
        sys.path.insert(0, "/home/opc/broker_os")
        from contract_generator import generate_finder_agreement, generate_wholesale_contract

        if deal_type == "wholesale_assignment":
            pdf = generate_wholesale_contract({
                "property_address": deal.get("property_address", "TBD"),
                "seller_name": deal.get("seller_name", ""),
                "seller_email": deal.get("seller_email", ""),
                "buyer_name": prospect,
                "buyer_email": email,
                "purchase_price": deal_value,
                "assignment_fee": deal.get("assignment_fee", deal_value * 0.10),
                "earnest_money": min(1000, deal_value * 0.01),
                "closing_date": deal.get("closing_date", "Within 14 days"),
                "title_company": deal.get("title_company", "TBD"),
            })
        else:
            pdf = generate_finder_agreement({
                "client_name": prospect,
                "client_email": email,
                "scope": scope,
                "commission_pct": commission_pct,
                "deal_value": deal_value,
            })
        deal["contract_path"] = pdf
    except Exception as e:
        deal["contract_error"] = str(e)

    # Send to prospect
    commission_str = "%.0f%%" % (commission_pct * 100)
    _send_branded_email("harrison", email, prospect.split()[0],
        "Finder Fee Agreement - Everlight Ventures",
        """<p>Thank you for your interest in partnering with Everlight Ventures.</p>
<p>Please find the key terms of our Finder Fee Agreement below:</p>
<ul>
<li><strong>Scope:</strong> %s</li>
<li><strong>Commission:</strong> %s of closed deal value</li>
<li><strong>Term:</strong> 12 months</li>
<li><strong>Payment:</strong> Net 30 via Stripe invoice</li>
<li><strong>Risk to you:</strong> Zero. You only pay when a deal closes.</li>
</ul>
<p>A detailed PDF agreement is being prepared. In the meantime, if you have questions, reply to this email or <a href="https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/booking">book a call</a>.</p>
<p>Once you confirm acceptance, we begin introductions immediately.</p>""" % (scope, commission_str))

    # Notify team
    _post_slack("*CONTRACT SENT* Harrison Knox sent finder agreement to %s (%s)\nScope: %s\nCommission: %s\nDeal value: $%s" % (
        prospect, email, scope, commission_str, "{:,.0f}".format(deal_value)))

    # Create GDoc
    _create_gdoc("Finder Agreement - %s" % prospect,
        "## Finder Fee Agreement\n\n- **Client:** %s\n- **Scope:** %s\n- **Commission:** %s\n- **Value:** $%s\n- **Status:** Sent, awaiting signature" % (
            prospect, scope, commission_str, "{:,.0f}".format(deal_value)))

    deal["stage"] = "contract_sent"
    return deal


# ====================================================================
# STAGE 4: TITLE COMPANY (wholesale only)
# ====================================================================

def stage_title_company(deal):
    """Coordinate with title company for closing."""
    prospect = deal.get("prospect_name", "Unknown")
    property_addr = deal.get("property_address", "TBD")
    city = deal.get("city", "default").lower()
    title_co = TITLE_COMPANIES.get(city, TITLE_COMPANIES["default"])

    # Email title company
    _send_branded_email("harrison", title_co["email"], "Closing Team",
        "New Assignment Closing - %s" % property_addr,
        """<p>We have a wholesale assignment ready for closing:</p>
<ul>
<li><strong>Property:</strong> %s</li>
<li><strong>Seller:</strong> %s</li>
<li><strong>Buyer/Assignee:</strong> %s (%s)</li>
<li><strong>Purchase Price:</strong> $%s</li>
<li><strong>Assignment Fee:</strong> $%s</li>
</ul>
<p>Please prepare for closing. We will send the executed purchase agreement and assignment contract.</p>
<p>Earnest money deposit of $%s will be wired within 3 business days.</p>""" % (
        property_addr, deal.get("seller_name", "TBD"), prospect, deal.get("prospect_email", ""),
        "{:,.0f}".format(deal.get("deal_value", 0)),
        "{:,.0f}".format(deal.get("assignment_fee", 0)),
        "{:,.0f}".format(deal.get("earnest_money", 500))))

    # Notify Rich
    _send_branded_email("harrison", RICH_EMAIL, "Rich",
        "Title Company Engaged - %s" % property_addr,
        """<p>Title company engaged for closing:</p>
<ul>
<li><strong>Title Co:</strong> %s</li>
<li><strong>Contact:</strong> %s / %s</li>
<li><strong>Property:</strong> %s</li>
<li><strong>Your assignment fee:</strong> $%s (paid at closing by title company)</li>
</ul>
<p>This is your money. Title company collects from buyer, pays seller, and wires your fee directly.</p>""" % (
        title_co["name"], title_co["email"], title_co["phone"],
        property_addr, "{:,.0f}".format(deal.get("assignment_fee", 0))))

    _post_slack("*TITLE COMPANY ENGAGED*\nProperty: %s\nTitle Co: %s\nAssignment fee: $%s\nHarrison coordinating closing" % (
        property_addr, title_co["name"], "{:,.0f}".format(deal.get("assignment_fee", 0))))

    deal["stage"] = "title_engaged"
    deal["title_company"] = title_co["name"]
    return deal


# ====================================================================
# STAGE 5: CLOSE -- Money time
# ====================================================================

def stage_close(deal):
    """Deal is closing. Send invoice (SaaS) or confirm title disbursement (wholesale)."""
    prospect = deal.get("prospect_name", "Unknown")
    email = deal.get("prospect_email", "")
    deal_type = deal.get("deal_type", "finder_fee")
    deal_value = deal.get("deal_value", 0)

    if deal_type == "finder_fee":
        # SaaS broker deal -- invoice the CLIENT for finder fee
        commission = deal_value * deal.get("commission_pct", 0.20)
        try:
            import sys
            sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS")
            sys.path.insert(0, "/home/opc/broker_os")
            from stripe_invoicer import invoice_deal
            result = invoice_deal({
                "client_name": prospect,
                "client_email": email,
                "deal_type": "finder_fee",
                "scope": deal.get("scope", "Partnership introduction"),
                "deal_value": deal_value,
                "commission_pct": deal.get("commission_pct", 0.20),
                "due_days": 30,
                "auto_send": True,
            })
            deal["invoice_url"] = result.get("invoice_url", "")
            deal["invoice_id"] = result.get("invoice_id", "")
        except Exception as e:
            deal["invoice_error"] = str(e)

        _send_branded_email("harrison", RICH_EMAIL, "Rich",
            "DEAL CLOSED - $%s Commission" % "{:,.0f}".format(commission),
            """<p><strong>Deal closed with %s.</strong></p>
<ul>
<li><strong>Deal value:</strong> $%s</li>
<li><strong>Your commission:</strong> $%s</li>
<li><strong>Invoice sent to:</strong> %s</li>
<li><strong>Payment due:</strong> Net 30</li>
<li><strong>Invoice:</strong> <a href="%s">View Invoice</a></li>
</ul>
<p>Money hits your Stripe balance when they pay. You can transfer to your bank from the Stripe dashboard.</p>""" % (
            prospect, "{:,.0f}".format(deal_value), "{:,.0f}".format(commission),
            email, deal.get("invoice_url", "#")))

    else:
        # Wholesale -- title company handles payment
        fee = deal.get("assignment_fee", 0)
        _send_branded_email("harrison", RICH_EMAIL, "Rich",
            "WHOLESALE CLOSED - $%s Assignment Fee" % "{:,.0f}".format(fee),
            """<p><strong>Wholesale deal closed.</strong></p>
<ul>
<li><strong>Property:</strong> %s</li>
<li><strong>Purchase price:</strong> $%s</li>
<li><strong>Your assignment fee:</strong> $%s</li>
<li><strong>Paid by:</strong> Title company wire to your bank</li>
<li><strong>Title Co:</strong> %s</li>
</ul>
<p>Title company will wire your $%s assignment fee within 3-5 business days of closing.</p>
<p>This is cash in your pocket. No Stripe fee. Direct wire.</p>""" % (
            deal.get("property_address", "TBD"),
            "{:,.0f}".format(deal_value), "{:,.0f}".format(fee),
            deal.get("title_company", "TBD"), "{:,.0f}".format(fee)))

    _post_slack("*DEAL CLOSED* %s\nType: %s\nValue: $%s\nProfit: $%s\nProspect: %s" % (
        "SaaS Finder Fee" if deal_type == "finder_fee" else "Wholesale Assignment",
        deal_type, "{:,.0f}".format(deal_value),
        "{:,.0f}".format(deal_value * deal.get("commission_pct", 0.20) if deal_type == "finder_fee" else deal.get("assignment_fee", 0)),
        prospect))

    deal["stage"] = "closed"
    return stage_complete(deal)


# ====================================================================
# STAGE 6: COMPLETE -- Log, tally, portfolio
# ====================================================================

def stage_complete(deal):
    """Log to portfolio, update metrics, celebrate."""
    prospect = deal.get("prospect_name", "Unknown")
    deal_type = deal.get("deal_type", "finder_fee")

    # Create portfolio GDoc
    _create_gdoc("Closed Deal - %s" % prospect,
        "## Deal Complete\n\n"
        "- **Client:** %s\n- **Type:** %s\n- **Value:** $%s\n- **Profit:** $%s\n"
        "- **Stage:** CLOSED\n- **Date:** %s\n\n"
        "### Pipeline\n"
        "Interest > Compliance (Justine) > Contract (Harrison) > %s > Close > Complete\n\n"
        "*Added to Everlight portfolio.*" % (
            prospect, deal_type, "{:,.0f}".format(deal.get("deal_value", 0)),
            "{:,.0f}".format(deal.get("assignment_fee", 0) if deal_type != "finder_fee" else deal.get("deal_value", 0) * deal.get("commission_pct", 0.20)),
            datetime.now(timezone(timedelta(hours=-7))).strftime("%B %d, %Y"),
            "Title Company" if deal_type == "wholesale_assignment" else "Invoice"))

    deal["stage"] = "complete"
    deal["completed_at"] = datetime.now(timezone.utc).isoformat()
    return deal


# ====================================================================
# FULL PIPELINE -- Run all stages
# ====================================================================

def run_full_pipeline(deal):
    """Execute the full deal pipeline from interest to complete."""
    print("=== RUNNING FULL PIPELINE: %s ===" % deal.get("prospect_name", "?"))

    deal = stage_interest(deal)
    if deal.get("stage") == "compliance_hold":
        print("  HELD at compliance. Manual review needed.")
        return deal

    deal = stage_contract(deal)

    if deal.get("deal_type") == "wholesale_assignment":
        deal = stage_title_company(deal)

    deal = stage_close(deal)

    print("  PIPELINE COMPLETE: %s | %s" % (deal.get("prospect_name"), deal.get("stage")))
    return deal


def run_simulation():
    """Run a simulated deal for testing."""
    return run_full_pipeline({
        "prospect_name": "Rich Gillies",
        "prospect_email": RICH_EMAIL,
        "deal_type": "finder_fee",
        "deal_value": 5000,
        "commission_pct": 0.20,
        "scope": "AI chatbot implementation referral",
        "source": "phone simulation",
    })


if __name__ == "__main__":
    print("Running simulated SaaS finder fee deal...")
    result = run_simulation()
    print("\nFinal stage:", result.get("stage"))
    print("Invoice:", result.get("invoice_url", "N/A"))
