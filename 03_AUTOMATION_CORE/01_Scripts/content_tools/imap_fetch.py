"""Shared Gmail IMAP fetch + RFC822 parse. Single source for all monitors.

Credentials (read from 03_AUTOMATION_CORE/03_Credentials/.env, env wins):
  GMAIL_IMAP_USER, GMAIL_IMAP_PASS, GMAIL_IMAP_HOST (default imap.gmail.com)
This is the working credential path; critical_email_monitor's old
GMAIL_USER/GMAIL_APP_PASSWORD vars were never set -> it was blind.
"""
from __future__ import annotations

import email
import imaplib
import os
import sys
from datetime import datetime, timedelta
from email.header import decode_header

try:
    from content_tools.env_loader import load_env
except ImportError:  # when the content_tools dir itself is on sys.path
    from env_loader import load_env


def _decode(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    out = []
    for chunk, enc in decode_header(raw):
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", errors="replace"))
            except LookupError:
                out.append(chunk.decode("utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _addr(header_value: str) -> tuple[str, str]:
    """Return (name, email) from a From header."""
    name, addr = email.utils.parseaddr(header_value)
    return _decode(name), addr.lower().strip()


def parse_message(raw: bytes) -> dict:
    """Parse one RFC822 message into a flat dict the pipeline understands."""
    msg = email.message_from_bytes(raw)
    from_name, from_email = _addr(msg.get("From", ""))

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            body = msg.get_payload() or ""

    return {
        "message_id": (msg.get("Message-ID", "") or "").strip(),
        "from_name": from_name,
        "from_email": from_email,
        "subject": _decode(msg.get("Subject", "")),
        "body": body,
        "delivered_to": (msg.get("Delivered-To", "") or msg.get("X-Original-To", "")).lower().strip(),
        "list_unsubscribe": (msg.get("List-Unsubscribe", "") or "").strip(),
        "precedence": (msg.get("Precedence", "") or "").strip().lower(),
        "date": msg.get("Date", ""),
    }


def fetch_recent(days: int = 1, mailbox: str = "INBOX", limit: int = 100) -> list[dict]:
    """Fetch parsed messages from the last `days`. Returns [] on any failure."""
    load_env()
    # Accept either the GMAIL_IMAP_* names or the legacy IMAP_USER/IMAP_PASS
    # names already present in 03_Credentials/.env -- whichever is set wins.
    user = os.environ.get("GMAIL_IMAP_USER") or os.environ.get("IMAP_USER")
    pw = os.environ.get("GMAIL_IMAP_PASS") or os.environ.get("IMAP_PASS")
    host = os.environ.get("GMAIL_IMAP_HOST") or os.environ.get("IMAP_HOST", "imap.gmail.com")
    if not user or not pw:
        return []
    out: list[dict] = []
    try:
        imap = imaplib.IMAP4_SSL(host, 993)
        imap.login(user, pw)
        imap.select(mailbox)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        typ, data = imap.search(None, f'(SINCE "{cutoff}")')
        if typ == "OK":
            for num in data[0].split()[-limit:]:
                try:
                    rtyp, md = imap.fetch(num, "(RFC822)")
                    if rtyp == "OK" and md and md[0]:
                        out.append(parse_message(md[0][1]))
                except Exception as exc:
                    print(f"imap_fetch: skipped message {num!r}: {exc}", file=sys.stderr)
                    continue
    except Exception:
        return out
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return out
