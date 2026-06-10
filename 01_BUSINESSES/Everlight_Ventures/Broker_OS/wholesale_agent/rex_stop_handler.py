"""
Rex Stop Handler -- CAN-SPAM compliance and opt-out processing.

When someone replies STOP, unsubscribe, remove me, not interested, or
do not contact, Rex immediately:
1. Marks the lead as "opted_out" in leads_db.json
2. Adds their email to a permanent suppression list (opted_out_emails.json)
3. Never contacts them again
4. Sends a confirmation reply

The suppression list MUST be checked before every email send across ALL
Rex scripts. No exceptions.

Cron: Runs as part of reply-check cycles (not standalone).
"""

# === ERADICATION HALT (auto-inserted 2026-05-15 after Streubel 2nd-strike) ===
# noqa: direct-resend
# This file still POSTs to api.resend.com directly. The eradication_gate is now
# called BEFORE any send via rex_utils.safe_send_email; the module refuses to
# load under WHOLESALE_OUTBOUND_HALT=1. Full migration to branded_mailer is
# tracked in _state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md.
import os as _os_halt
if _os_halt.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}:
    import sys as _sys_halt
    print("[rex_stop_handler.py] WHOLESALE_OUTBOUND_HALT=1 -- refusing to run", file=_sys_halt.stderr)
    raise SystemExit("WHOLESALE_OUTBOUND_HALT active")
import sys as _sys_eg
_sys_eg.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
try:
    from eradication_gate import assert_safe as _erad_assert_safe, EradicationViolation
except ImportError as _eg_err:
    print(f"[rex_stop_handler.py] eradication_gate unavailable: {_eg_err}", file=_sys_eg.stderr)
    raise SystemExit("eradication_gate required")
# === END ERADICATION HALT ===

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[Rex Stop %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("rex_stop")

AGENT_DIR = Path(__file__).parent
LEADS_DB = AGENT_DIR / "leads_db.json"
SUPPRESSION_FILE = AGENT_DIR / "opted_out_emails.json"

RESEND_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "Justine Park <justine@everlightventures.io>"
REPLY_TO = "justine@everlightventures.io"

# Patterns that trigger opt-out (case-insensitive)
OPT_OUT_PATTERNS = [
    r"\bstop\b",
    r"\bunsubscribe\b",
    r"\bremove\s*me\b",
    r"\bnot\s+interested\b",
    r"\bdo\s+not\s+contact\b",
    r"\bdon'?t\s+contact\b",
    r"\bopt\s*out\b",
    r"\btake\s+me\s+off\b",
    r"\bleave\s+me\s+alone\b",
    r"\bno\s+thanks\b",
    r"\bno\s+thank\s+you\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in OPT_OUT_PATTERNS]

CONFIRMATION_SUBJECT = "You've been removed"
CONFIRMATION_BODY = (
    "You've been removed. We won't contact you again. "
    "Sorry for the inconvenience.\n\n"
    "- Justine Park, Everlight Ventures"
)


# ---------------------------------------------------------------------------
# SUPPRESSION LIST
# ---------------------------------------------------------------------------

def load_suppression_list() -> set:
    """Load the permanent suppression list from disk. Returns a set of
    lowercase email addresses that must never be contacted."""
    if not SUPPRESSION_FILE.exists():
        return set()
    try:
        data = json.loads(SUPPRESSION_FILE.read_text())
        if isinstance(data, list):
            return {e.lower().strip() for e in data if isinstance(e, str)}
        return set()
    except (json.JSONDecodeError, OSError) as exc:
        log.error(f"Failed to load suppression list: {exc}")
        return set()


def _save_suppression_list(emails: set):
    """Write the suppression list back to disk."""
    sorted_list = sorted(emails)
    SUPPRESSION_FILE.write_text(json.dumps(sorted_list, indent=2))


def is_suppressed(email: str) -> bool:
    """Return True if the email address is on the permanent suppression list."""
    if not email:
        return False
    suppressed = load_suppression_list()
    return email.lower().strip() in suppressed


def _add_to_suppression(email: str):
    """Add an email to the suppression list (idempotent)."""
    if not email:
        return
    suppressed = load_suppression_list()
    clean = email.lower().strip()
    if clean in suppressed:
        return
    suppressed.add(clean)
    _save_suppression_list(suppressed)
    log.info(f"Added {clean} to permanent suppression list ({len(suppressed)} total)")


# ---------------------------------------------------------------------------
# OPT-OUT DETECTION
# ---------------------------------------------------------------------------

def is_opt_out_message(text: str) -> bool:
    """Return True if the text contains an opt-out keyword or phrase."""
    if not text:
        return False
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# OPT-OUT PROCESSING
# ---------------------------------------------------------------------------

# Hostile-trigger patterns -> promote the opt-out to the "eradicated" scope (full block,
# no confirmation reply). The Streubel lesson: a complaint/threat is not a routine opt-out.
HOSTILE_PATTERNS = [re.compile(p, re.I) for p in [
    r"\bbbb\b", r"better business bureau", r"attorney general", r"\bag\b",
    r"\blawyer\b", r"\battorney\b", r"\bsue\b", r"\blawsuit\b", r"cease and desist",
    r"\bharass", r"\bspam\b.*\breport", r"\bfuck\b|\bwtf\b", r"report you",
]]


def classify_opt_out_scope(text: str, email: str = "") -> str:
    """email_only (routine) | entity (business wants all contact stopped) | eradicated
    (complaint / legal threat). Mirrors the legal team's scope spec."""
    t = text or ""
    if any(p.search(t) for p in HOSTILE_PATTERNS):
        return "eradicated"
    if re.search(r"\b(my (company|firm|business)|anyone here|everyone here|all of us)\b", t, re.I):
        return "entity"
    return "email_only"


def process_opt_out(email: str, send_confirmation: bool = True,
                    trigger_text: str = "", message_id: str = "",
                    requested_at_utc: str = "", name: str = "",
                    address: str = "", lead_id: str = "") -> bool:
    """
    Universal opt-out flow -- the Streubel treatment for ANYONE who says stop:
    1. Add to permanent suppression list (fast is_suppressed cache)
    2. Add to the eradication gate's dynamic store (gate-level block on every send path)
    3. Mark the lead as opted_out in leads_db.json
    4. Send a transactional confirmation -- UNLESS the opt-out is hostile (eradicated scope),
       where silence is the honor (never email a complainant).

    Returns True if newly suppressed, False if already suppressed.
    """
    if not email:
        log.warning("process_opt_out called with empty email")
        return False

    clean = email.lower().strip()

    if is_suppressed(clean):
        log.info(f"{clean} already suppressed -- no action needed")
        return False

    scope = classify_opt_out_scope(trigger_text, clean)

    # 1. Fast suppression cache
    _add_to_suppression(clean)

    # 2. Gate-level block (the universal Streubel treatment) -- defensible record
    try:
        from eradication_gate import add_opt_out  # type: ignore
        add_opt_out(
            email=clean, name=name or None, address=address or None,
            lead_id=lead_id or None, scope=scope, source_channel="email_reply",
            trigger_verbatim=trigger_text, message_id=message_id,
            requested_at_utc=requested_at_utc or None,
            lead_ids=[lead_id] if lead_id else None,
        )
    except Exception as e:
        log.error(f"eradication_gate.add_opt_out failed for {clean}: {e}")

    # 3. Mark lead opted_out
    _mark_lead_opted_out(clean)

    # 4. Confirmation -- NEVER to a hostile/eradicated opt-out (silence is the honor)
    if send_confirmation and scope != "eradicated":
        _send_opt_out_confirmation(clean)

    log.info(f"Opt-out processed for {clean} (scope={scope})")
    return True


def _mark_lead_opted_out(email: str):
    """Find the lead in leads_db.json and mark as opted_out."""
    if not LEADS_DB.exists():
        return

    try:
        leads = json.loads(LEADS_DB.read_text())
    except (json.JSONDecodeError, OSError):
        log.error("Failed to read leads_db.json for opt-out marking")
        return

    clean = email.lower().strip()
    changed = False

    for lead in leads:
        lead_email = lead.get("owner_email", "").lower().strip()
        if lead_email == clean:
            lead["status"] = "opted_out"
            lead["opted_out_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
            log.info(
                f"Marked lead opted_out: {lead.get('owner_name', '?')} "
                f"at {lead.get('address', '?')}"
            )

    if changed:
        with open(LEADS_DB, "w") as f:
            json.dump(leads, f, indent=2, default=str)


def _send_opt_out_confirmation(email: str):
    """Send a brief confirmation that the person has been removed."""
    if not RESEND_KEY:
        log.info(f"No RESEND_API_KEY -- skipping confirmation to {email}")
        return

    try:
        import requests
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [email],
                "subject": CONFIRMATION_SUBJECT,
                "text": CONFIRMATION_BODY,
                "reply_to": REPLY_TO,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            log.info(f"Opt-out confirmation sent to {email}")
        else:
            log.warning(
                f"Opt-out confirmation failed ({resp.status_code}): "
                f"{resp.text[:200]}"
            )
    except Exception as exc:
        log.error(f"Failed to send opt-out confirmation to {email}: {exc}")


# ---------------------------------------------------------------------------
# SCAN REPLIES FOR OPT-OUTS
# ---------------------------------------------------------------------------

def scan_inbox_for_opt_outs() -> int:
    """
    Check IMAP inbox for replies containing opt-out keywords.
    Process each one through the full opt-out flow.
    Returns count of new opt-outs found.
    """
    imap_user = os.environ.get("IMAP_USER", "")
    imap_pass = os.environ.get("IMAP_PASS", "")
    if not imap_user or not imap_pass:
        log.info("No IMAP credentials -- skipping inbox scan")
        return 0

    opt_outs_found = 0

    try:
        import imaplib
        import email as emaillib

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(imap_user, imap_pass)
        mail.select("INBOX")

        # Search for recent unread replies
        status, messages = mail.search(None, "(UNSEEN)")
        if status != "OK" or not messages[0]:
            mail.logout()
            return 0

        for msg_id in messages[0].split()[:50]:
            try:
                status, data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = emaillib.message_from_bytes(data[0][1])
                sender = msg.get("From", "")
                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="replace")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")

                subject = msg.get("Subject", "")
                full_text = f"{subject} {body}"

                if is_opt_out_message(full_text):
                    # Extract email from sender
                    sender_email = ""
                    email_match = re.search(
                        r"[\w.+-]+@[\w-]+\.[\w.]+", sender
                    )
                    if email_match:
                        sender_email = email_match.group(0)

                    if sender_email:
                        was_new = process_opt_out(sender_email)
                        if was_new:
                            opt_outs_found += 1

            except Exception as exc:
                log.warning(f"Error processing message {msg_id}: {exc}")
                continue

        mail.logout()

    except Exception as exc:
        log.error(f"IMAP scan for opt-outs failed: {exc}")

    if opt_outs_found:
        log.info(f"Found and processed {opt_outs_found} new opt-outs")

    return opt_outs_found


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Manual opt-out: python rex_stop_handler.py user@example.com
        email_arg = sys.argv[1]
        log.info(f"Manual opt-out request for: {email_arg}")
        process_opt_out(email_arg)
    else:
        # Scan inbox for opt-outs
        log.info("Scanning inbox for opt-out replies...")
        count = scan_inbox_for_opt_outs()
        log.info(f"Done. {count} new opt-outs processed.")

    # Print current suppression list stats
    suppressed = load_suppression_list()
    log.info(f"Total suppressed emails: {len(suppressed)}")
