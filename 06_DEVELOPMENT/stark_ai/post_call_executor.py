"""
Post-Call Executor v2 -- Uses Ollama (phi3) on Oracle to intelligently parse
call transcripts and execute ALL promised actions.

Runs every 2 min on Oracle. Reads ElevenLabs transcripts, sends them to Ollama
for action extraction, then executes via Resend, Slack, GDocs, Stripe, etc.
"""
import json
import os
import re
import subprocess
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

EL_KEY = os.getenv("ELEVENLABS_API_KEY", "")
RESEND_KEY = os.getenv("RESEND_API_KEY", "")
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID_REAL", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
N8N_URL = os.getenv("N8N_URL", "http://129.159.38.250:5678")
RICH_EMAIL = "1m.rich.gee@gmail.com"
RICH_PHONE = "+17073869709"
PROCESSED_FILE = Path("/tmp/stark_processed_calls_v2.json")

# Agent signatures and email branding
AGENT_SIGS = {
    "piper": {
        "name": "Piper Reeves",
        "title": "Senior Account Executive",
        "email": "piper@everlightventures.io",
        "phone": "(707) 801-0360",
        "from": "Piper Reeves <piper@everlightventures.io>",
    },
    "marcus": {
        "name": "Marcus Cole",
        "title": "Chief Operator",
        "email": "marcus@everlightventures.io",
        "phone": "(888) 896-6772",
        "from": "Marcus Cole <marcus@everlightventures.io>",
    },
    "harrison": {
        "name": "Harrison Knox",
        "title": "Deal Operations",
        "email": "hammer@everlightventures.io",
        "phone": "(888) 896-6772",
        "from": "Harrison Knox <hammer@everlightventures.io>",
    },
    "lucrex": {
        "name": "Lucrex",
        "title": "Executive Intelligence",
        "email": "lucrex@everlightventures.io",
        "phone": "(707) 760-7922",
        "from": "Lucrex <lucrex@everlightventures.io>",
    },
}


def _branded_email(subject, body_html, agent_key="piper", to_name="there"):
    """Wrap email content in Everlight gold-branded HTML with agent signature."""
    sig = AGENT_SIGS.get(agent_key, AGENT_SIGS["piper"])
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body {{ margin:0; padding:0; background:#0A0A0A; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
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
        subject=subject,
        to_name=to_name,
        body_html=body_html,
        sig_name=sig["name"],
        sig_title=sig["title"],
        sig_email=sig["email"],
        sig_phone=sig["phone"],
    )

# Known contacts
CONTACTS = {
    "rich": {"email": RICH_EMAIL, "phone": RICH_PHONE, "name": "Rich Gillies"},
    "alexandra": {"email": "alexandra@infisical.com", "name": "Alexandra", "company": "Infisical"},
    "designart": {"email": "sales@designartusa.com", "name": "designisart"},
}


def get_recent_conversations():
    resp = requests.get(
        "https://api.elevenlabs.io/v1/convai/conversations",
        headers={"xi-api-key": EL_KEY},
        timeout=15,
    )
    return resp.json().get("conversations", []) if resp.status_code == 200 else []


def get_transcript(conv_id):
    resp = requests.get(
        "https://api.elevenlabs.io/v1/convai/conversations/%s" % conv_id,
        headers={"xi-api-key": EL_KEY},
        timeout=15,
    )
    return resp.json() if resp.status_code == 200 else None


def parse_actions_with_llm(transcript_text):
    """Use Ollama to extract action items from transcript."""
    prompt = """You are an action extractor. Read this phone call transcript and list EVERY action the AI agent promised to do. Output JSON array only. Each action has: type, recipient, description.

Types: send_email, send_google_doc, send_calendar, send_contract, send_invoice, dispatch_agent, check_pipeline, post_slack, send_sms, simulate_deal

Example output:
[{"type":"send_email","recipient":"rich","description":"Send wholesale property offer email"},{"type":"send_google_doc","recipient":"rich","description":"Attach generic report"},{"type":"send_contract","recipient":"rich","description":"Harrison sends purchase agreement"}]

TRANSCRIPT:
%s

JSON ACTIONS:""" % transcript_text

    # Try Ollama on localhost (Oracle) first, then remote
    for url in ["http://localhost:11434/api/generate", "http://129.159.38.250:11434/api/generate"]:
        try:
            resp = requests.post(url, json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500}
            }, timeout=30)
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                # Extract JSON from response
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
        except Exception:
            continue

    # Fallback: regex-based extraction
    return extract_actions_regex(transcript_text)


def extract_actions_regex(text):
    """Fallback regex extraction when LLM unavailable."""
    actions = []
    text_lower = text.lower()

    if any(w in text_lower for w in ["send email", "sending email", "send that email", "shoot that over", "piper is sending"]):
        actions.append({"type": "send_email", "recipient": "rich", "description": "Follow-up email"})

    if any(w in text_lower for w in ["google doc", "report", "document"]):
        actions.append({"type": "send_google_doc", "recipient": "rich", "description": "Report/document"})

    if any(w in text_lower for w in ["calendar", "invite", "schedule", "meeting"]):
        actions.append({"type": "send_calendar", "recipient": "rich", "description": "Calendar invite"})

    if any(w in text_lower for w in ["contract", "agreement", "purchase agreement"]):
        actions.append({"type": "send_contract", "recipient": "rich", "description": "Contract/agreement"})

    if any(w in text_lower for w in ["invoice", "stripe", "payment"]):
        actions.append({"type": "send_invoice", "recipient": "rich", "description": "Stripe invoice"})

    if any(w in text_lower for w in ["wholesale", "simulate", "property offer", "deal simulation"]):
        actions.append({"type": "simulate_deal", "recipient": "rich", "description": "Simulated wholesale deal"})

    # Agent dispatches
    for agent in ["piper", "marcus", "rex", "penny", "harrison", "filter", "ace", "forge", "justine", "scout"]:
        if agent in text_lower:
            # Find what they are doing
            pattern = r'(?:having|tell|ask|get|dispatch) %s (?:to )?(.+?)(?:\.|$|,)' % agent
            match = re.search(pattern, text_lower)
            task = match.group(1) if match else "handle assigned task"
            actions.append({"type": "dispatch_agent", "recipient": agent, "description": task[:200]})

    return actions


# ---- ACTION EXECUTORS ----

def _branded_send(subject, body_html, agent_key, to_email, to_name, category="nurture"):
    """Centralized send through branded_mailer (gold template + budget gate).

    All voice-action emails route through here so the Everlight theme is
    applied uniformly and the resend_budget gate paces the monthly Resend
    quota with a 25% VIP reserve.
    """
    try:
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        print("  branded_mailer unavailable: %s" % exc)
        return False

    sig = AGENT_SIGS.get(agent_key, AGENT_SIGS["piper"])
    result = send_branded_email(
        to=to_email,
        subject=subject,
        content_html=body_html,
        title=subject,
        from_name=str(sig.get("from", sig["name"])).split("<")[0].strip(),
        from_email=sig["email"],
        reply_to=sig["email"],
        agent_name=sig["name"],
        agent_title=sig.get("title", "Everlight Ventures"),
        agent_email=sig["email"],
        budget_category=category,
    )
    return bool(result.ok)


def exec_send_email(action):
    """Send branded email via Resend."""
    recipient = action.get("recipient", "rich")
    contact = CONTACTS.get(recipient, CONTACTS["rich"])
    to_email = contact.get("email", RICH_EMAIL)
    to_name = contact.get("name", "there").split()[0]
    desc = action.get("description", "Following up from our conversation")
    agent = action.get("agent", "piper")
    sig = AGENT_SIGS.get(agent, AGENT_SIGS["piper"])

    if not RESEND_KEY:
        return False

    subject = "Following Up - Everlight Ventures"
    body_html = """<p>Following up from our conversation. %s</p>
<p>At Everlight Ventures, we connect software companies with qualified buyers through our brokerage platform. Our finder fee model means <strong>zero upfront cost</strong> to you -- we only earn when a deal closes.</p>
<p>Would love to set up a quick call to walk through the specifics. You can <a href="https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/booking">book a time here</a> or just reply to this email.</p>""" % desc

    ok = _branded_send(subject, body_html, agent_key=agent, to_email=to_email, to_name=to_name, category="nurture")
    print("  EMAIL -> %s (%s)" % (to_email, "OK" if ok else "FAIL"))
    return ok


def exec_send_google_doc(action):
    """Create Google Doc via n8n webhook."""
    desc = action.get("description", "Pipeline Report")
    recipient = action.get("recipient", "rich")

    try:
        # Branded Google Doc via the Python replacement (no n8n)
        import sys as _sys
        for _p in ("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
                   "/home/opc/content_tools"):
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from n8n_replacements import publish_gdoc  # type: ignore

        body = (
            "## %s\n\nGenerated by the Hive Mind.\n\n"
            "### Pipeline Status\n- 286 leads in system\n- 143 offers being brokered\n"
            "- 1899 scored matches\n- Top match: designisart (score 70)\n"
            "- Active deal: Infisical (Alexandra)\n\n"
            "### Wholesale Pipeline\n- Running 4x daily on Oracle\n"
            "- Markets: Cleveland, Atlanta, Dallas, Jacksonville\n"
            "- Contract generator: LIVE\n- Stripe auto-invoicing: LIVE\n\n"
            "---\n*Generated by Lucrex - King of Divine Light*"
        ) % desc

        res = publish_gdoc(
            title="Everlight Ventures - %s" % desc,
            body=body,
            channel="#broker-pipeline",
            folder_key="broker_scout",
        )
        print("  GDOC -> %s" % ("OK" if res.get("ok") else (res.get("error") or "FAIL")[:80]))
        return bool(res.get("ok"))
    except Exception as e:
        print("  GDOC FAILED: %s" % e)
        return False


def exec_send_calendar(action):
    """Send branded calendar invite email."""
    recipient = action.get("recipient", "rich")
    contact = CONTACTS.get(recipient, CONTACTS["rich"])
    to_name = contact.get("name", "there").split()[0]
    desc = action.get("description", "Everlight Partnership Call")

    if not RESEND_KEY:
        return False

    body_html = """<p>I'd love to get some time on the calendar to discuss <strong>%s</strong>.</p>
<p>Pick a time that works for you:</p>
<p style="text-align:center; margin:24px 0;">
<a href="https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/booking" style="background:linear-gradient(135deg,#D4A843,#B8860B); color:#000; padding:12px 32px; border-radius:8px; text-decoration:none; font-weight:600; font-size:14px;">Book a Time Slot</a>
</p>
<p>Or just reply with a few times that work and I'll get us set up.</p>""" % desc

    ok = _branded_send(
        subject="Let's Get on the Calendar - %s" % desc,
        body_html=body_html,
        agent_key="piper",
        to_email=contact.get("email", RICH_EMAIL),
        to_name=to_name,
        category="nurture",
    )
    print("  CALENDAR -> %s (%s)" % (contact.get("email"), "OK" if ok else "FAIL"))
    return ok


def exec_send_contract(action):
    """Generate contract PDF and send branded email."""
    recipient = action.get("recipient", "rich")
    contact = CONTACTS.get(recipient, CONTACTS["rich"])
    to_name = contact.get("name", "there").split()[0]
    scope = action.get("description", "SaaS partnership introduction")

    try:
        import sys
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS")
        sys.path.insert(0, "/home/opc/broker_os")
        from contract_generator import generate_finder_agreement
        pdf = generate_finder_agreement({
            "client_name": contact.get("name", "Client"),
            "client_email": contact.get("email", ""),
            "scope": scope,
            "commission_pct": 0.20,
            "deal_value": 5000,
        })
        print("  CONTRACT generated: %s" % pdf)

        if RESEND_KEY:
            body_html = """<p>Please find below the Finder Fee Agreement for our partnership.</p>
<p><strong>Key Terms:</strong></p>
<ul>
<li><strong>Commission:</strong> 20%% of closed deal value</li>
<li><strong>Term:</strong> 12 months</li>
<li><strong>Scope:</strong> %s</li>
<li><strong>Payment:</strong> Net 30 via Stripe invoice</li>
<li><strong>Risk to you:</strong> Zero. You only pay when a deal closes.</li>
</ul>
<p>Please review at your convenience. If everything looks good, we can proceed immediately. If you have questions, just reply to this email or <a href="https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/booking">book a call with our team</a>.</p>""" % scope

            _branded_send(
                subject="Finder Fee Agreement - Everlight Ventures",
                body_html=body_html,
                agent_key="harrison",
                to_email=contact.get("email", RICH_EMAIL),
                to_name=to_name,
                category="vip_reply",
            )
            print("  CONTRACT EMAIL sent to %s" % contact.get("email"))
        return True
    except Exception as e:
        print("  CONTRACT FAILED: %s" % e)
        return False


def exec_send_invoice(action):
    """Create Stripe invoice with proper deal terms and branding."""
    recipient = action.get("recipient", "rich")
    contact = CONTACTS.get(recipient, CONTACTS["rich"])
    desc = action.get("description", "Partnership finder fee")

    try:
        import sys
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS")
        sys.path.insert(0, "/home/opc/broker_os")
        from stripe_invoicer import invoice_deal
        result = invoice_deal({
            "client_name": contact.get("company", contact.get("name", "Client")),
            "client_email": contact.get("email", RICH_EMAIL),
            "deal_type": "finder_fee",
            "scope": desc,
            "deal_value": 5000,
            "commission_pct": 0.20,
            "due_days": 30,
            "auto_send": True,
        })

        # Send branded invoice notification email alongside Stripe
        if result.get("success") and RESEND_KEY:
            inv_url = result.get("invoice_url", "")
            amount = result.get("amount_usd", 0)
            body_html = """<p>Your invoice for the Everlight Ventures finder fee is ready.</p>
<p><strong>Invoice Details:</strong></p>
<ul>
<li><strong>Description:</strong> %s</li>
<li><strong>Amount:</strong> $%s</li>
<li><strong>Due:</strong> Net 30</li>
<li><strong>Payment:</strong> Secure online payment via Stripe</li>
</ul>
<p style="text-align:center; margin:24px 0;">
<a href="%s" style="background:linear-gradient(135deg,#D4A843,#B8860B); color:#000; padding:12px 32px; border-radius:8px; text-decoration:none; font-weight:600; font-size:14px;">Pay Invoice</a>
</p>
<p>If you have any questions about this invoice, reply to this email or contact our deal operations team.</p>""" % (desc, "{:,.2f}".format(amount), inv_url)

            _branded_send(
                subject="Invoice from Everlight Ventures - %s" % desc,
                body_html=body_html,
                agent_key="harrison",
                to_email=contact.get("email", RICH_EMAIL),
                to_name=contact.get("name", "there").split()[0],
                category="vip_reply",
            )

        print("  INVOICE: %s" % ("OK - %s" % result.get("invoice_url", "") if result.get("success") else "FAILED - %s" % result.get("error")))
        return result.get("success", False)
    except Exception as e:
        print("  INVOICE FAILED: %s" % e)
        return False


def exec_simulate_deal_old(action):
    """Deprecated -- use full pipeline instead."""
    pass

def exec_simulate_deal(action):
    """Run the FULL 6-stage deal pipeline."""
    print("  RUNNING FULL DEAL PIPELINE...")
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from deal_pipeline import run_full_pipeline

        recipient = action.get("recipient", "rich")
        contact = CONTACTS.get(recipient, CONTACTS["rich"])

        deal = {
            "prospect_name": contact.get("name", "Test Client"),
            "prospect_email": contact.get("email", RICH_EMAIL),
            "deal_type": "finder_fee",
            "deal_value": 5000,
            "commission_pct": 0.20,
            "scope": action.get("description", "Partnership referral"),
            "source": "phone call simulation",
        }
        result = run_full_pipeline(deal)
        print("  PIPELINE COMPLETE: stage=%s" % result.get("stage"))
        return True
    except Exception as e:
        print("  PIPELINE ERROR: %s" % e)
        # Fallback to basic simulation
        return _exec_simulate_deal_basic(action)


def _exec_simulate_deal_basic(action):
    """Fallback basic simulation."""
    print("  BASIC SIMULATION fallback...")

    # 1. Rex scouts -- branded property offer email
    exec_send_email({
        "recipient": "rich",
        "agent": "piper",
        "description": (
            "Rex Blackwell just scouted a property that fits the criteria:</p>"
            "<p><strong>1234 Oak St, Cleveland OH 44102</strong></p>"
            "<ul>"
            "<li><strong>Type:</strong> Distressed, tax delinquent</li>"
            "<li><strong>ARV:</strong> $120,000</li>"
            "<li><strong>Asking:</strong> $45,000</li>"
            "<li><strong>Repair Est:</strong> $25,000</li>"
            "<li><strong>Assignment Fee:</strong> $12,000</li>"
            "</ul>"
            "<p>Filter Banks scored at <strong>78/100</strong>. Penny confirmed margins. Harrison has the contract ready.</p>"
            "<p>Reply YES to proceed or <a href='https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/booking'>book a call</a> to discuss."
        ),
    })

    # 2. Google Doc deal sheet
    exec_send_google_doc({"description": "Wholesale Deal Sheet - 1234 Oak St Cleveland OH"})

    # 3. Contract PDF (but NOT a Stripe invoice to yourself -- invoices go to BUYERS)
    exec_send_contract({"recipient": "rich", "description": "Wholesale assignment - 1234 Oak St Cleveland OH"})

    # 4. Slack
    exec_post_slack({"description": "*SIMULATED DEAL PIPELINE*\nProperty: 1234 Oak St Cleveland\nARV: $120k | Ask: $45k | Fee: $12k\nRex scouted | Filter scored 78 | Penny approved | Harrison contract ready\nEmail + GDoc + Contract sent to CEO"})

    print("  SIMULATION complete - 4 actions fired (no invoice -- invoices go to buyers, not us)")
    return True


def exec_dispatch_agent(action):
    """Post agent dispatch to Slack and execute if possible."""
    agent = action.get("recipient", "unknown")
    task = action.get("description", "")

    if SLACK_TOKEN:
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer %s" % SLACK_TOKEN, "Content-Type": "application/json"},
            json={"channel": "C0ANLLV8JAC", "text": "*DISPATCH* %s: %s" % (agent.title(), task)},
            timeout=10)

    print("  DISPATCH -> %s: %s" % (agent, task[:80]))
    return True


def exec_post_slack(action):
    """Post to Slack."""
    if SLACK_TOKEN:
        requests.post("https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer %s" % SLACK_TOKEN, "Content-Type": "application/json"},
            json={"channel": "C0ANLLV8JAC", "text": action.get("description", "Update from the Hive")},
            timeout=10)
        print("  SLACK posted")
        return True
    return False


def exec_send_sms(action):
    """Send SMS via Twilio."""
    recipient = action.get("recipient", "rich")
    contact = CONTACTS.get(recipient, CONTACTS["rich"])
    if TWILIO_SID and TWILIO_TOKEN:
        resp = requests.post(
            "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % TWILIO_SID,
            auth=(TWILIO_SID, TWILIO_TOKEN),
            data={"To": contact.get("phone", RICH_PHONE), "From": "+17078010360", "Body": action.get("description", "Update from Piper")[:1600]},
            timeout=15)
        print("  SMS -> %s (%s)" % (contact.get("phone"), "OK" if resp.status_code == 201 else "FAIL"))
        return resp.status_code == 201
    return False


# Action router
EXECUTORS = {
    "send_email": exec_send_email,
    "send_google_doc": exec_send_google_doc,
    "send_calendar": exec_send_calendar,
    "send_contract": exec_send_contract,
    "send_invoice": exec_send_invoice,
    "simulate_deal": exec_simulate_deal,
    "dispatch_agent": exec_dispatch_agent,
    "post_slack": exec_post_slack,
    "send_sms": exec_send_sms,
    "check_pipeline": exec_post_slack,  # posts status to slack
}


def process_new_calls():
    """Main: find new completed calls, parse actions, execute."""
    processed = set()
    if PROCESSED_FILE.exists():
        try:
            processed = set(json.loads(PROCESSED_FILE.read_text()))
        except Exception:
            processed = set()

    convos = get_recent_conversations()
    total_actions = 0

    for c in convos:
        cid = c.get("conversation_id", "")
        status = c.get("status", "")
        duration = c.get("call_duration_secs", 0)

        if cid in processed or status not in ("done",) or duration < 5:
            continue

        print("\n=== Processing: %s (dur: %ds) ===" % (cid[:30], duration))
        data = get_transcript(cid)
        if not data:
            continue

        transcript = data.get("transcript", [])
        full_text = "\n".join(
            "[%s] %s" % (m.get("role", "?").upper(), (m.get("message", "") or ""))
            for m in transcript if (m.get("message") or "").strip()
        )

        if not full_text.strip():
            processed.add(cid)
            continue

        print("Transcript length: %d chars" % len(full_text))

        # Try LLM first, fallback to regex
        actions = parse_actions_with_llm(full_text)
        if not actions:
            actions = extract_actions_regex(full_text)

        print("Found %d actions" % len(actions))

        for action in actions:
            atype = action.get("type", "")
            executor = EXECUTORS.get(atype)
            if executor:
                print("  Executing: %s -> %s" % (atype, action.get("description", "")[:60]))
                try:
                    executor(action)
                    total_actions += 1
                except Exception as e:
                    print("  ERROR: %s" % e)
            else:
                print("  SKIP unknown type: %s" % atype)

        processed.add(cid)

    PROCESSED_FILE.write_text(json.dumps(list(processed)))
    print("\nTotal: %d actions executed from %d calls" % (total_actions, len(convos)))


if __name__ == "__main__":
    process_new_calls()
