"""
hot_lead_intake.py -- Manual + auto catch for hot seller inbound replies.

Per doctrine `feedback_hot_inbound_must_be_caught.md` (2026-04-28):
ANY inbound reply that signals seller engagement must be captured, structured,
and alerted. Layer 1 = auto via inbound_watch_daemon (Oracle, IMAP). Layer 2 =
manual via this script (Marquise pastes email, script extracts intel).

Both layers feed the same downstream pipeline.

Usage:
  # Manual catch from a pasted email (Marquise's path)
  python3 hot_lead_intake.py --paste

  # Manual catch from a file (after copying email to /tmp/inbound.txt)
  python3 hot_lead_intake.py --file /tmp/inbound.txt --from-name "Chris" \
      --from-email "chris@example.com" --city "Memphis" --state "TN"

  # Test/sample
  python3 hot_lead_intake.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
INBOUND_LOG = WORKSPACE / "_logs/inbound/hot_inbound.jsonl"
HIVE_FAILURE_LOG = WORKSPACE / "_logs/hive_failures/inbound_miss.jsonl"
DEAL_RECORDS_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals"


# ====================================================================
# Field extraction
# ====================================================================

MOTIVATION_PATTERNS = [
    (r"\b(behind|past due|missed payment|catch up|foreclos)", "pre_foreclosure"),
    (r"\b(tax (lien|sale|delinq))", "tax_lien"),
    (r"\b(estate|inherit|passed away|probate|dad|mom|grandma)", "probate"),
    (r"\b(divorce|splitting|separat)", "divorce"),
    (r"\b(vacant|empty|nobody (lives|is in)|abandoned)", "vacant"),
    (r"\b(fire damag|burned|water damag|flood)", "distressed"),
    (r"\b(relocat|moving|new job|out of state)", "motivated_seller"),
    (r"\b(can't afford|underwater|owe more|in over)", "financial_distress"),
    (r"\b(need.*sell|got to sell|gotta sell|must sell|gotta move)", "motivated_seller"),
]

URGENCY_PATTERNS = [
    (r"\b(asap|right away|this week|by friday|by monday)", "immediate"),
    (r"\b(this month|in (30|thirty) days|in a month)", "within_30d"),
    (r"\b(in (60|90|sixty|ninety) days|next month or two|spring|summer)", "within_90d"),
    (r"\b(no (rush|hurry)|whenever|when ready)", "no_rush"),
]

CONDITION_PATTERNS = [
    (r"\b(needs (work|repair|fixing)|fixer|handyman|gut|major repair)", "needs_repair"),
    (r"\b(fire damag|burned|water damag|flood)", "fire_damage"),
    (r"\b(abandoned|condemned|board(ed)? up)", "abandoned"),
    (r"\b(turn.?key|move.?in|recently renovat|fully (updat|remodel))", "livable"),
]

SENTIMENT_PATTERNS = [
    (r"\b(interested|tell me more|what.*offer|how (does|do) (this|you) work|let.s talk)", "positive"),
    (r"\b(not interested|no thank|stop|don't email|remove)", "objection"),
    (r"\b(scam|fraud|bullshit|leave me alone|harass)", "hostile"),
]

ADDRESS_RE = re.compile(r"\b(\d{1,6}\s+[A-Za-z0-9 .'-]+(?:Rd|Road|St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ct|Court|Ln|Lane|Way|Pl|Place|Pkwy|Parkway|Cir|Circle|Trail|Trl))\b", re.IGNORECASE)
CITY_STATE_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?),\s*([A-Z]{2})\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\(?\b([2-9][0-9]{2})\)?[\s\-.]+([2-9][0-9]{2})[\s\-.]+([0-9]{4})\b")


def detect(patterns, text: str, default: str) -> str:
    text = (text or "").lower()
    for pat, tag in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return tag
    return default


def extract_address(text: str) -> str:
    m = ADDRESS_RE.search(text or "")
    return m.group(0) if m else ""


def extract_city_state(text: str) -> tuple[str, str]:
    m = CITY_STATE_RE.search(text or "")
    if m:
        return m.group(1), m.group(2)
    return "", ""


def extract_email(text: str) -> str:
    m = EMAIL_RE.search(text or "")
    return m.group(0) if m else ""


def extract_phone(text: str) -> str:
    m = PHONE_RE.search(text or "")
    if m:
        return f"({m.group(1)}) {m.group(2)}-{m.group(3)}"
    return ""


# ====================================================================
# Parse + structure
# ====================================================================

_OUTBOUND_INDEX_CACHE: dict[str, dict] | None = None


def _outbound_index() -> dict[str, dict]:
    """Lazy-load the outbound recipient ledger via inbound_reply_matcher.

    Returns {lowercase_email: {persona_id, source, subject, ts}}.
    Used by parse_inbound() to distinguish real replies from cold inbound.
    """
    global _OUTBOUND_INDEX_CACHE
    if _OUTBOUND_INDEX_CACHE is not None:
        return _OUTBOUND_INDEX_CACHE
    try:
        import sys as _sys
        _ct = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools"
        if _ct not in _sys.path:
            _sys.path.insert(0, _ct)
        from inbound_reply_matcher import build_outbound_index  # type: ignore
        _OUTBOUND_INDEX_CACHE = build_outbound_index()
    except Exception:
        _OUTBOUND_INDEX_CACHE = {}
    return _OUTBOUND_INDEX_CACHE


_KNOWN_PROMO_DOMAINS = {
    "noreply", "no-reply", "newsletter", "mailer", "marketing", "notification",
    "promos-coming", "funships", "substack.com", "fandango", "ncl.com",
    "battle.net", "venmo.com", "udemy.com", "affirm.com", "doordash.com",
    "bk.com", "gasbuddy.com", "groupon.com", "stockstotrade.com",
    "thehustle.co", "techpresso.com", "uber.com", "groundfloor.us",
    "togos.com", "carnivalcruiselineemail.com", "comms.ed", "edd.ca.gov",
    "alison.com", "comcast-spectacor.com", "america-first-america-always",
    "ablink", "click.email", "email.gasbuddy.com", "students.udemy.com",
}


def _looks_like_promo(from_email: str) -> bool:
    fe = (from_email or "").lower()
    if not fe or "@" not in fe:
        return True
    local, _, domain = fe.partition("@")
    for token in _KNOWN_PROMO_DOMAINS:
        if token in local or token in domain:
            return True
    # Heuristic: 5+ digit local-parts or hyphen-stuffed locals are blast IDs
    if sum(c.isdigit() for c in local) >= 5:
        return True
    return False


_STRICT_SELLER_PATTERNS = [
    # Explicit seller verbs
    (r"\b(i\s+want\s+to\s+sell|i'?d\s+like\s+to\s+sell|interested\s+in\s+selling)\b", "explicit_sell_intent"),
    (r"\b(cash\s+offer|all[- ]cash\s+offer|asking\s+price|how\s+much\s+(can|will)\s+you\s+pay)\b", "monetary_inquiry"),
    (r"\b(my\s+(house|property|land|home))\s+(at|on)\b", "owner_self_reference"),
    # Strong distress signals (require LONG body to count -- promos use single words)
    (r"\b(behind\s+on\s+(payments|mortgage)|foreclosure\s+notice|tax\s+lien|inherited\s+(the\s+)?property)\b", "distress_signal"),
]


def parse_inbound(
    body: str,
    from_name: str = "",
    from_email: str = "",
    city: str = "",
    state: str = "",
    address: str = "",
    source_channel: str = "email",
    catch_path: str = "manual",
    imap_uid: str = "",
) -> dict:
    """Extract structured fields from a pasted seller email.

    STRICT MODE (2026-05-17, per operator directive):
      1. Ledger check FIRST. If from_email is in the outbound ledger, this
         is a REAL REPLY -- mark real_reply=True, route to original persona.
      2. If NOT in ledger AND looks like promo -> motivation=noise,
         minimal action queue, no @-tags.
      3. If NOT in ledger AND body contains STRICT seller-language pattern
         AND body length >= 100 chars -> motivation=cold_seller_inquiry,
         normal action queue.
      4. Drop the unconditional `Tag @hammer @justine` action -- it floods
         Slack with promo garbage.
    """
    if not from_email:
        from_email = extract_email(body)
    if not address:
        address = extract_address(body)
    if not (city and state):
        c, s = extract_city_state(body)
        city = city or c
        state = state or s
    phone = extract_phone(body)

    # === STRICT MODE: ledger check first ===
    ledger = _outbound_index()
    fe_lower = (from_email or "").lower().strip()
    real_reply_match = ledger.get(fe_lower)
    real_reply = real_reply_match is not None
    reply_persona = (real_reply_match or {}).get("persona_id", "")

    # === STRICT MODE: noise vs seller filter ===
    is_promo = _looks_like_promo(from_email)
    body_len = len(body or "")
    seller_signal = None
    if not real_reply:
        for pat, tag in _STRICT_SELLER_PATTERNS:
            if re.search(pat, body or "", re.IGNORECASE):
                seller_signal = tag
                break

    # === Classify motivation ===
    if real_reply:
        motivation = "real_reply"
    elif seller_signal and body_len >= 100 and not is_promo:
        # Use original regex tagger only when strict gate passed
        motivation = detect(MOTIVATION_PATTERNS, body, "cold_seller_inquiry")
    else:
        motivation = "noise"

    urgency = detect(URGENCY_PATTERNS, body, "unspecified") if motivation != "noise" else "unspecified"
    condition = detect(CONDITION_PATTERNS, body, "unknown") if motivation != "noise" else "unknown"
    sentiment = detect(SENTIMENT_PATTERNS, body, "neutral") if motivation != "noise" else "neutral"

    # When noise, drop the address + state heuristics (they false-positive on
    # promo bodies like "Universal City, CA" and "5:00 PM EST")
    if motivation == "noise":
        address = ""
        state = ""
        city = ""

    # Compliance flags (skipped entirely when noise)
    flags = []
    state_upper = state.upper() if state else ""
    if motivation != "noise":
        if state_upper == "TN":
            flags.append("TN_warm_inbound_no_cold_block")
            flags.append("TN_HB_2537_wholesaler_disclosure_required")
            flags.append("TN_Code_62-13-104_surety_bond_check_before_close")
        if state_upper == "NC":
            flags.append("NC_HB_797_BLOCK_DO_NOT_ENGAGE_WITHOUT_BROKER_LICENSE")
        if state_upper == "CA":
            flags.append("CA_check_pre_foreclosure_status_before_engaging")
        if motivation == "pre_foreclosure":
            flags.append("pre_foreclosure_state_specific_compliance_check")
        if motivation == "probate":
            flags.append("probate_check_for_retained_counsel_before_negotiating")

    # Operator action queue (STRICT MODE -- only useful work, no blanket tags)
    actions = []
    if motivation == "noise":
        # Silent. Do not flood Slack with promo tags.
        pass
    elif real_reply:
        # Real reply takes priority over everything else.
        actions.append(f"Real reply matched to outbound persona '{reply_persona}'. Route to that agent's inbox; respond within 30 min.")
        if sentiment == "objection":
            actions.append("Update DNC ledger immediately. Send 1 polite acknowledgment, end thread.")
        if sentiment == "hostile":
            actions.append("Update DNC + add to compliance flag list. Notify Justine. No further contact.")
    else:
        # cold_seller_inquiry path -- strict gate passed
        if sentiment == "positive":
            actions.append("Reply within 30 min with 1 qualifying question + thank-you. Do not pitch number yet.")
        if sentiment == "objection":
            actions.append("Update DNC ledger immediately. Send 1 polite acknowledgment, end thread.")
        if sentiment == "hostile":
            actions.append("Update DNC + add to compliance flag list. Notify Justine. No further contact.")
        if address and state_upper:
            actions.append(f"Pull comps + MAO via /broker/cashoffer/?address={address.replace(' ','+')}.")
        if state_upper:
            actions.append(f"State-specific compliance pre-check via state_gates.json[{state_upper}].")
            if state_upper == "TN" and motivation == "motivated_seller":
                actions.append("Verify Memphis OZ status: opportunityzones.hud.gov -- if OZ, MAO room is higher.")
        actions.append("Tag @hammer in #broker-pipeline + @justine for state-gate review.")

    return {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "catch_path": catch_path,
        "source_channel": source_channel,
        "from_name": from_name,
        "from_email": from_email,
        "phone": phone,
        "address": address,
        "city": city,
        "state": state_upper,
        "motivation": motivation,
        "urgency": urgency,
        "condition": condition,
        "sentiment": sentiment,
        "compliance_flags": flags,
        "operator_action_queue": actions,
        "raw_body_excerpt": (body or "")[:1500],
        "raw_body_length": len(body or ""),
        "imap_uid": str(imap_uid) if imap_uid else "",
        "real_reply": bool(real_reply),
        "real_reply_persona": reply_persona if real_reply else "",
        "is_promo": bool(is_promo),
        "seller_signal": seller_signal,
    }


# ====================================================================
# Persist + alert
# ====================================================================

def write_inbound_log(record: dict) -> Path:
    INBOUND_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(INBOUND_LOG, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return INBOUND_LOG


def upsert_lead(record: dict) -> dict:
    """Add to leads_db.json with status='engaged'. Dedupe by email or address."""
    if not LEADS_DB.exists():
        return {"action": "skip", "reason": "leads_db.json missing"}
    leads = json.loads(LEADS_DB.read_text())

    em = (record.get("from_email") or "").lower()
    addr = (record.get("address") or "").upper()

    matched = None
    for l in leads:
        l_em = (l.get("owner_email") or l.get("email") or "").lower()
        l_addr = (l.get("address") or "").upper()
        if em and l_em == em:
            matched = l
            break
        if addr and l_addr == addr:
            matched = l
            break

    if matched:
        matched["status"] = "engaged"
        matched["last_inbound_ts"] = record["ts_utc"]
        matched["last_inbound_motivation"] = record["motivation"]
        matched["last_inbound_sentiment"] = record["sentiment"]
        matched["catch_path"] = record["catch_path"]
        action = "updated_existing"
    else:
        new_lead = {
            "address": record.get("address", ""),
            "city": record.get("city", ""),
            "state": record.get("state", ""),
            "owner_name": record.get("from_name", ""),
            "owner_email": record.get("from_email", ""),
            "owner_phone": record.get("phone", ""),
            "lead_type": record.get("motivation", "general"),
            "status": "engaged",
            "queue": "email" if record.get("from_email") else ("phone" if record.get("phone") else "needs_enrichment"),
            "source": f"hot_inbound_{record.get('catch_path','manual')}",
            "outreach_count": 0,
            "sequence_step": 0,
            "created_at": record["ts_utc"],
            "last_inbound_ts": record["ts_utc"],
            "last_inbound_motivation": record["motivation"],
            "last_inbound_sentiment": record["sentiment"],
            "catch_path": record["catch_path"],
        }
        leads.append(new_lead)
        action = "created_new"
        matched = new_lead

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    return {"action": action, "lead": matched}


def post_slack_alert(record: dict, lead_action: dict) -> None:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("BROKER_PIPELINE_CHANNEL", "C0ANLLV8JAC")  # placeholder; user can override
    if not token:
        print("(no SLACK_BOT_TOKEN, skipping Slack alert)")
        return

    name = record.get("from_name") or record.get("from_email") or "(unknown)"
    city = record.get("city") or "(city TBD)"
    state = record.get("state") or "??"
    addr = record.get("address") or "(address TBD)"

    text_lines = [
        f":fire: *HOT INBOUND* -- {name}, {city}, {state}",
        f"Address: {addr}",
        f"Channel: {record.get('source_channel','email')}",
        f"Catch path: *{record.get('catch_path','manual')}*",
        f"Motivation: `{record['motivation']}` | Urgency: `{record['urgency']}` | Sentiment: `{record['sentiment']}`",
        f"DB action: {lead_action.get('action','?')}",
        "",
        "*Compliance flags:*",
        *(f"  - {f}" for f in record.get("compliance_flags", [])),
        "",
        "*Action queue (next 30 min):*",
        *(f"  - {a}" for a in record.get("operator_action_queue", [])),
        "",
        "Tagging: <@hammer> (closer) <@justine> (compliance)",
    ]
    text = "\n".join(text_lines)

    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        urllib.request.urlopen(req, timeout=10).read()
        print(f"  Slack alert posted to {channel}")
    except Exception as e:
        print(f"  Slack post failed: {e}")


def write_hive_failure_if_manual(record: dict) -> None:
    """If catch_path=='manual', this is a Layer-1 failure (auto-catch missed it).
    Log to hive_failures so we can postmortem how often Layer 1 misses."""
    if record.get("catch_path") != "manual":
        return
    HIVE_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HIVE_FAILURE_LOG, "a") as f:
        f.write(json.dumps({
            "ts_utc": record["ts_utc"],
            "lead_email": record.get("from_email", ""),
            "lead_state": record.get("state", ""),
            "expected_auto_path": "inbound_watch_daemon (Oracle IMAP poll every 2 min)",
            "actual_catch_path": "manual paste via hot_lead_intake.py",
            "gap_explanation": "Auto-catch dark; Gmail IMAP creds expired since 2026-04-24 + Oracle unreachable from phone. Manual fallback used.",
        }) + "\n")


# ====================================================================
# CLI
# ====================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paste", action="store_true", help="Read email body from stdin")
    parser.add_argument("--file", help="Read email body from file")
    parser.add_argument("--from-name", default="", help="Seller name (if known)")
    parser.add_argument("--from-email", default="", help="Seller email (if known)")
    parser.add_argument("--city", default="", help="Property city (if known)")
    parser.add_argument("--state", default="", help="Property state (if known)")
    parser.add_argument("--address", default="", help="Property address (if known)")
    parser.add_argument("--source-channel", default="email", help="email | sms | voice | web_form")
    parser.add_argument("--catch-path", default="manual", help="manual | auto")
    parser.add_argument("--imap-uid", default="", help="IMAP UID (for Gmail label retro-application)")
    parser.add_argument("--no-slack", action="store_true", help="Skip Slack alert")
    parser.add_argument("--self-test", action="store_true", help="Run with sample Memphis email")
    args = parser.parse_args()

    if args.self_test:
        body = """
Hi Rich,

Thanks for reaching out. Yeah I might be interested -- the property is in
Memphis on South Parkway. My dad passed away last year and we're still
sorting probate. Place needs work, hasn't been lived in for about 8 months.
I'm not in a huge rush but I'd love to hear what you can offer.

You can reach me at chris.smith@example.com or 901-555-0173.

Chris
"""
        args.from_name = "Chris Smith"
        args.from_email = "chris.smith@example.com"
        args.state = "TN"
        args.city = "Memphis"
    elif args.file:
        body = Path(args.file).read_text()
    elif args.paste:
        print("Paste email body, then Ctrl+D:")
        body = sys.stdin.read()
    else:
        print("Need --paste, --file, or --self-test", file=sys.stderr)
        sys.exit(1)

    record = parse_inbound(
        body,
        from_name=args.from_name,
        from_email=args.from_email,
        imap_uid=args.imap_uid,
        city=args.city,
        state=args.state,
        address=args.address,
        source_channel=args.source_channel,
        catch_path=args.catch_path,
    )

    print("=== STRUCTURED INTAKE ===")
    print(json.dumps({k: v for k, v in record.items() if k != "raw_body_excerpt"}, indent=2, default=str))

    log_path = write_inbound_log(record)
    print(f"\nInbound log: {log_path}")

    lead_action = upsert_lead(record)
    print(f"leads_db action: {lead_action.get('action','?')}")

    write_hive_failure_if_manual(record)

    if not args.no_slack:
        post_slack_alert(record, lead_action)
    else:
        print("(--no-slack, skipping)")

    print()
    print("=== NEXT 30 MIN ACTIONS ===")
    for a in record["operator_action_queue"]:
        print(f"  [ ] {a}")


if __name__ == "__main__":
    main()
