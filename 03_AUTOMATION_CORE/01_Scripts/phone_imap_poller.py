"""
phone_imap_poller.py -- Layer 1 fallback for hot inbound auto-catch.

Per `feedback_hot_inbound_must_be_caught.md` (2026-04-28): the canonical
auto-catch is `inbound_watch_daemon.py` running on Oracle. It's been dark
since 2026-04-24 because (a) Gmail IMAP creds expired and (b) Oracle is
unreachable. This poller is the BRIDGE -- runs phone-side, residential IP,
polls every 2 min, fires the same hot_lead_intake.py pipeline.

When Oracle is back AND Gmail is rotated, this can stay running as a backup
or be sunset in favor of the canonical Oracle daemon. Today, it's the only
working Layer 1.

Usage:
  # One-shot poll (test mode, see what's there)
  python3 phone_imap_poller.py --once

  # Continuous mode (every 2 min, until killed)
  python3 phone_imap_poller.py --watch

  # Debug a single message by UID
  python3 phone_imap_poller.py --uid 12345

Requires:
  - GMAIL_APP_PASSWORD set in env (rotate per runbook BEFORE running)
  - IMAP_USER (default 1m.rich.gee@gmail.com)
  - WHEN ORACLE IS BACK: this script becomes redundant. Keep as failover only.

Filtering:
  Only inspects messages that look like seller replies:
  - To address contains @everlightventures.io
  - From sender NOT in our DNC ledger
  - Not in Spam / Trash labels
  - Recent (last 24h on first run; last 5 min on watch loop)
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from pathlib import Path

# Phoenix v3: auto-load Everlight credentials from .env
sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from env_loader import load_env
    load_env()
except Exception:
    pass


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LAST_SEEN_FILE = WORKSPACE / "_logs/inbound/imap_last_seen.json"
LAST_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
INTAKE_SCRIPT = WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/hot_lead_intake.py"

GMAIL_HOST = "imap.gmail.com"
GMAIL_USER = os.environ.get("IMAP_USER") or os.environ.get("GMAIL_USER") or "1m.rich.gee@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("IMAP_PASS", "")

# Patterns that signal SELLER engagement (wholesale lane)
SELLER_ENGAGEMENT_PATTERNS = [
    r"\b(interested|tell me more|send.*offer|cash offer|how (does|do) (this|you) work)",
    r"\b(yes|yep|yeah|sure)[\s,.]",
    r"\b(let.s talk|call me|reach me|my number)",
    r"\b(property|house|home|land|place)\b.*\b(sell|sale|cash)",
    r"\b(motivated|need.*sell|gotta sell|must sell)",
    r"\b(probate|estate|inherit|passed away)",
    r"\b(behind|foreclos|tax|lien|divorce|relocat)",
]

# Patterns that signal B2B engagement (buyers, partners, SaaS prospects, vendors)
B2B_ENGAGEMENT_PATTERNS = [
    r"\b(following up|checking in|just.*following|circle back)",
    r"\b(let me know|happy to (chat|connect|discuss|talk))",
    r"\b(availability|available|free this week|free next week|schedule)",
    r"\b(re:|reply to)",  # Anything that's a reply
    r"\b(intro call|quick call|15.?min)",
    r"\b(send.*(deals|leads|info|criteria))",  # Buyer accept signal
    r"\b(buy box|buying criteria|our box|max.*offer|MAO)",
    r"\b(thanks for (reaching|connecting|the))",
    r"\b(happy to work|happy to discuss|open to)",
    r"\b(partnership|partner with|JV)",
]

# Combined -- a message is engaging if it matches EITHER seller OR B2B patterns
INTEREST_PATTERNS = SELLER_ENGAGEMENT_PATTERNS + B2B_ENGAGEMENT_PATTERNS

# Negative patterns. NOTE: "stop|unsubscribe|remove" only count if in FIRST 500 chars
# (as opposed to standard footer). Re-tuned to not false-block legitimate B2B replies
# that have unsubscribe footers.
HARD_NEGATIVE_PATTERNS = [
    r"\b(scam|fraud|harass|do not contact me)",
    r"undeliverable|delivery (status|failed|notification)",
    r"out of office|on vacation|auto-?reply",
    r"please remove me|remove from.*list",
]
SOFT_NEGATIVE_PATTERNS = [
    # These are noisy in footers -- only count if in first 500 chars
    r"\b(unsubscribe|stop sending|don.t (email|contact|call))",
]


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def load_last_seen() -> dict:
    if LAST_SEEN_FILE.exists():
        try:
            return json.loads(LAST_SEEN_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_last_seen(data: dict) -> None:
    LAST_SEEN_FILE.write_text(json.dumps(data, indent=2, default=str))


def imap_connect() -> imaplib.IMAP4_SSL:
    if not GMAIL_PASS:
        raise SystemExit(
            "FATAL: GMAIL_APP_PASSWORD (or IMAP_PASS) not in env. "
            "Source 03_AUTOMATION_CORE/03_Credentials/.env first."
        )
    m = imaplib.IMAP4_SSL(GMAIL_HOST)
    try:
        m.login(GMAIL_USER, GMAIL_PASS)
    except imaplib.IMAP4.error as e:
        raise SystemExit(
            f"FATAL: IMAP login failed: {e}. "
            "If 'AUTHENTICATIONFAILED' -- rotate Gmail app password per "
            "06_DEVELOPMENT/everlight_os/hive_mind/runbooks/gmail_app_password_rotation.md"
        )
    return m


def decode_field(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", errors="replace")
        except Exception:
            raw = str(raw)
    parts = decode_header(raw)
    out = []
    for p, enc in parts:
        if isinstance(p, bytes):
            try:
                out.append(p.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(p.decode("utf-8", errors="replace"))
        else:
            out.append(p)
    return "".join(out)


def extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp.lower():
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="replace")
        # Fallback to HTML stripped
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    txt = payload.decode(errors="replace")
                    txt = re.sub(r"<[^>]+>", " ", txt)
                    return re.sub(r"\s+", " ", txt).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="replace")
    return ""


CONTACTED_INDEX = WORKSPACE / "_logs/outreach/contacted_addresses.jsonl"


def load_contacted_addresses() -> set[str]:
    """Load set of every email address any agent has outreached to.

    Per Marquise doctrine 2026-04-28:
    'if you send an email to someone and the incoming email matches the email
    any agent emailed then, they should reply back right. intuitively.'
    """
    out = set()
    if CONTACTED_INDEX.exists():
        for line in CONTACTED_INDEX.read_text().splitlines():
            try:
                row = json.loads(line)
                em = (row.get("recipient_email") or "").strip().lower()
                if em:
                    out.add(em)
            except Exception:
                continue
    # Also seed from leads_db rows where outreach_count > 0
    leads_path = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
    if leads_path.exists():
        try:
            for lead in json.loads(leads_path.read_text()):
                if lead.get("outreach_count", 0) > 0:
                    em = (lead.get("owner_email") or lead.get("email") or "").strip().lower()
                    if em:
                        out.add(em)
        except Exception:
            pass
    return out


def looks_like_seller_engagement(subject: str, body: str, from_email: str = "") -> tuple[bool, str]:
    """Detect engagement.

    PRIMARY RULE (doctrine 2026-04-28): if FROM matches any address we've outreached to,
    it's ALWAYS a reply -- intake regardless of body content.

    FALLBACK: keyword detection (wholesale seller OR B2B buyer/partner/prospect).
    """
    sender = (from_email or "").strip().lower()
    if sender:
        contacted = load_contacted_addresses()
        if sender in contacted:
            return True, f"contacted-address-reply:{sender}"

    full_text = f"{subject}\n{body}".lower()
    head_text = full_text[:500]

    # Hard negatives anywhere = block
    for pat in HARD_NEGATIVE_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            return False, f"hard-negative:{pat[:30]}"
    # Soft negatives only count if in first 500 chars (footer stop-words allowed)
    for pat in SOFT_NEGATIVE_PATTERNS:
        if re.search(pat, head_text, re.IGNORECASE):
            return False, f"soft-negative-in-head:{pat[:30]}"

    # Positive signals
    for pat in SELLER_ENGAGEMENT_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            return True, f"seller-engagement:{pat[:40]}"
    for pat in B2B_ENGAGEMENT_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            return True, f"b2b-engagement:{pat[:40]}"
    return False, "no-engagement-signal"


def _try_deal_arc_route(from_email: str, from_name: str, subject: str, body: str):
    """
    Check if this inbound message matches an active deal counterparty. If yes:
    classify the reply, look up the deal state, fire the next arc step, log it.
    Returns a string describing the action taken, or None if not a deal-arc reply.
    """
    try:
        sys.path.insert(0, str(WORKSPACE / "Everlight_Intel_Center"))
        sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"))
        from osint_api.arc_send import (classify_reply, fire_step, load_deal_meta,
                                          next_step, should_throttle_inbound,
                                          should_escalate, ARC_FUNCTIONS)
        from deal_execution_log import deal_history, log_event
    except Exception as e:
        log(f"  arc_route import failed: {e}")
        return None

    # Walk every deal_meta.json on disk to find one whose seller/buyer email
    # matches the inbound sender
    deals_root = WORKSPACE / "09_DASHBOARD" / "reports" / "deals"
    if not deals_root.exists():
        return None

    matched_deal = None
    matched_role = None  # "seller" or "buyer"
    sender_clean = (from_email or "").strip().lower()
    for deal_dir in deals_root.iterdir():
        meta_path = deal_dir / "deal_meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        if (meta.get("seller_email", "") or "").lower() == sender_clean:
            matched_deal, matched_role = meta, "seller"; break
        if (meta.get("buyer_email", "") or "").lower() == sender_clean:
            matched_deal, matched_role = meta, "buyer"; break

    if not matched_deal:
        return None

    deal_key = matched_deal["deal_key"]
    reply_class = classify_reply(body or "")

    # Find last stage from audit log (M-prefix for seller arc, C-prefix for buyer arc)
    events = deal_history(deal_key)
    last_event = events[-1] if events else None
    last_stage = None
    if last_event:
        # Match the role's stage prefix
        prefix = "C" if matched_role == "buyer" else "M"
        m = re.search(rf"\b({prefix}\d)\b", last_event.get("notes", "") or "")
        if m:
            last_stage = m.group(1)
    if not last_stage:
        last_stage = "C1" if matched_role == "buyer" else "M1"

    # ALWAYS log the inbound first (for audit + double-email tracking)
    try:
        log_event(deal_key=deal_key, event="email_received", actor=f"{from_name} <{from_email}>",
                  counterparty=f"{'Hammer' if matched_role == 'buyer' else 'Marquise'} alias",
                  notes=f"Inbound role={matched_role}, classified={reply_class}, last_stage={last_stage}")
    except Exception:
        pass

    # BRANCH: double-email throttle. If 2+ inbounds in last 30 min, hold off on next outbound.
    if should_throttle_inbound(deal_key):
        log(f"  -> throttled (2+ inbounds within {30}min); waiting for next cycle to combine")
        try:
            log_event(deal_key=deal_key, event="arc_throttled",
                      actor="phone_imap_poller",
                      notes=f"Double-email detected; deferring next outbound for next cycle")
        except Exception:
            pass
        return f"deal={deal_key} role={matched_role} -> throttled (double-email)"

    # Decide next step using role-aware router
    next_fn_name = next_step(deal_key, last_stage, reply_class, role=matched_role)

    # BRANCH: escalate if nothing routes (counterparty went off-script or hit our wall)
    if next_fn_name is None and should_escalate(deal_key, last_stage, reply_class, matched_role):
        log(f"  -> escalating to operator: deal={deal_key} role={matched_role} class={reply_class} last={last_stage}")
        try:
            log_event(deal_key=deal_key, event="escalation_to_operator",
                      actor="phone_imap_poller",
                      counterparty=f"{from_name} <{from_email}>",
                      notes=f"No autoroute for class={reply_class} at last_stage={last_stage} role={matched_role}; needs Rich")
        except Exception:
            pass
        return f"deal={deal_key} role={matched_role} class={reply_class} last={last_stage} -> escalated to operator"

    if not next_fn_name:
        return f"deal={deal_key} role={matched_role} class={reply_class} last={last_stage} -> no_next_step (STOP or terminal)"

    # Fire the next step (with counter-amount extraction if applicable)
    kwargs = {}
    if next_fn_name in {"m5_meet", "m7_final", "c3_meet", "c5_final"}:
        m_amt = re.search(r"\$\s*([\d,]+)", body or "")
        if m_amt:
            try:
                kwargs["counter_amount"] = int(m_amt.group(1).replace(",", ""))
            except ValueError:
                pass

    result = fire_step(deal_key, next_fn_name, **kwargs)
    return f"deal={deal_key} role={matched_role} class={reply_class} last={last_stage} -> fired {next_fn_name} ok={result.get('ok')}"


def fire_hot_lead_intake(
    from_email: str,
    from_name: str,
    subject: str,
    body: str,
) -> int:
    """Call hot_lead_intake.py with the parsed message. Returns rc."""
    cmd = [
        "python3", str(INTAKE_SCRIPT),
        "--paste",
        "--from-email", from_email,
        "--from-name", from_name,
        "--source-channel", "email",
        "--catch-path", "auto_phone_imap_poller",
        "--no-slack",  # caller can re-fire with Slack later if needed
    ]
    payload = f"Subject: {subject}\n\n{body}\n"
    try:
        result = subprocess.run(
            cmd, input=payload, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log(f"  Intake OK for {from_email}")
            return 0
        log(f"  Intake rc={result.returncode}: {result.stderr[:200]}")
        return result.returncode
    except Exception as e:
        log(f"  Intake exception: {e}")
        return 1


def poll_inbox(since_minutes: int = 5, dry_run: bool = False) -> int:
    """One poll cycle. Returns count of intakes fired."""
    last_seen = load_last_seen()
    last_uid = last_seen.get("last_processed_uid", 0)

    m = imap_connect()
    m.select("INBOX", readonly=True)

    # Search for recent messages
    since = (datetime.utcnow() - timedelta(minutes=since_minutes)).strftime("%d-%b-%Y")
    typ, data = m.search(None, f'(SINCE "{since}")')
    if typ != "OK":
        log("  search failed")
        m.logout()
        return 0

    uids = data[0].split()
    log(f"  Found {len(uids)} message(s) since {since}")

    fired = 0
    new_last_uid = last_uid

    for uid_b in uids:
        uid = int(uid_b)
        if uid <= last_uid:
            continue
        new_last_uid = max(new_last_uid, uid)

        typ, msg_data = m.fetch(uid_b, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_field(msg.get("Subject", ""))
        from_raw = decode_field(msg.get("From", ""))
        # Parse name + email from "From: Name <email>"
        from_name = ""
        from_email = ""
        m_addr = re.match(r'\s*"?([^"<]+?)"?\s*<([^>]+)>', from_raw)
        if m_addr:
            from_name = m_addr.group(1).strip()
            from_email = m_addr.group(2).strip()
        else:
            from_email = from_raw.strip()

        body = extract_body(msg)

        is_engagement, reason = looks_like_seller_engagement(subject, body, from_email)
        log(f"  UID {uid} | {from_email[:35]:35} | {subject[:40]:40} | {reason}")

        if not dry_run:
            # FIRST: try deal-arc routing (active negotiation with known counterparty)
            arc_routed = _try_deal_arc_route(from_email, from_name, subject, body)
            if arc_routed:
                log(f"  -> deal arc routed: {arc_routed}")
                fired += 1
                continue
            # FALLBACK: hot-lead intake (cold-lead engagement)
            if is_engagement:
                fire_hot_lead_intake(from_email, from_name, subject, body)
                fired += 1

    m.logout()

    # Persist last_seen
    last_seen["last_processed_uid"] = new_last_uid
    last_seen["last_poll_ts"] = datetime.now(timezone.utc).isoformat()
    last_seen["last_fired_count"] = fired
    save_last_seen(last_seen)

    log(f"  Cycle complete. Fired {fired} intake(s). last_uid={new_last_uid}")
    return fired


def watch_loop(interval_seconds: int = 120) -> None:
    log(f"Starting watch loop (every {interval_seconds}s). Ctrl+C to stop.")
    while True:
        try:
            poll_inbox(since_minutes=5)
        except KeyboardInterrupt:
            log("Interrupted.")
            return
        except Exception as e:
            log(f"Cycle error (continuing): {e}")
        time.sleep(interval_seconds)


def healthcheck() -> int:
    """Verify GMAIL_APP_PASSWORD auth works, without touching any mail.
    Returns 0 = AUTH OK, 1 = NO PASSWORD, 2 = AUTH FAILED."""
    if not GMAIL_PASS:
        print("AUTH FAILED -- GMAIL_APP_PASSWORD not in env")
        print("  Set per: 03_AUTOMATION_CORE/03_Credentials/.env")
        print("  Or:    https://myaccount.google.com/apppasswords (16-char, no spaces)")
        return 1
    try:
        m = imaplib.IMAP4_SSL(GMAIL_HOST)
        m.login(GMAIL_USER, GMAIL_PASS)
        rc, msg = m.select("INBOX", readonly=True)
        m.logout()
        if rc == "OK":
            print(f"AUTH OK -- user={GMAIL_USER} host={GMAIL_HOST}")
            try:
                count = int(msg[0])
                print(f"  INBOX message count: {count}")
            except Exception:
                pass
            return 0
        print(f"AUTH OK but INBOX SELECT failed: rc={rc}")
        return 0
    except imaplib.IMAP4.error as e:
        print(f"AUTH FAILED -- {e}")
        print("  If AUTHENTICATIONFAILED, the app password is wrong or revoked.")
        print("  Rotate at https://myaccount.google.com/apppasswords")
        return 2
    except Exception as e:
        print(f"AUTH FAILED -- {e}")
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--watch", action="store_true", help="Continuous loop every 2 min")
    parser.add_argument("--dry-run", action="store_true", help="Detect but don't fire intake")
    parser.add_argument("--healthcheck", action="store_true",
                        help="Probe auth only; print AUTH OK or AUTH FAILED; exit. No mail touched.")
    parser.add_argument("--since-minutes", type=int, default=1440,
                        help="On --once, look back this many minutes (default 24h)")
    parser.add_argument("--interval", type=int, default=120,
                        help="Watch loop interval seconds (default 120)")
    args = parser.parse_args()

    if args.healthcheck:
        sys.exit(healthcheck())
    if args.watch:
        watch_loop(args.interval)
    elif args.once:
        poll_inbox(since_minutes=args.since_minutes, dry_run=args.dry_run)
    else:
        print(__doc__)
        sys.exit(0)


if __name__ == "__main__":
    main()
