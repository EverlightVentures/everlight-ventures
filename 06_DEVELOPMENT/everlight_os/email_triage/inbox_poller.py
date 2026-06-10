"""inbox_poller -- reads new unseen emails from Gmail via IMAP. Returns a list
of dict messages: {thread_id, msg_id, sender, subject, body, received_at}.

Uses GMAIL_IMAP_USER + GMAIL_IMAP_PASS from .env (app password, not OAuth, for
daemon simplicity). State file tracks which msg_ids have been processed so we
don't re-classify on every poll.
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import time
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

STATE_PATH = Path("/AA_MY_DRIVE/_logs/email_triage/processed_msgs.json")
LOG_PATH = Path("/AA_MY_DRIVE/_logs/email_triage/poller.log")


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"version": 1, "processed_msg_ids": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "processed_msg_ids": []}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # cap to last 5000 ids
    state["processed_msg_ids"] = state.get("processed_msg_ids", [])[-5000:]
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _decode(s: str | None) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get("Content-Disposition", "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
        # fallback to first text/html
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8",
                                          errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8",
                                  errors="replace")
    return ""


def fetch_new_messages(host: str = None, user: str = None,
                        password: str = None, mailbox: str = "INBOX",
                        max_messages: int = 50,
                        only_unseen: bool = True) -> list[dict]:
    """Connect to Gmail IMAP, fetch unseen messages, return list of dicts.
    Marks them as Seen after fetch (so we don't refetch).
    """
    host = host or os.environ.get("IMAP_HOST", "imap.gmail.com")
    user = user or os.environ.get("GMAIL_IMAP_USER") or os.environ.get("IMAP_USER")
    password = password or os.environ.get("GMAIL_IMAP_PASS") or os.environ.get("IMAP_PASS")

    if not user or not password:
        _log("FAIL: GMAIL_IMAP_USER + GMAIL_IMAP_PASS not set in env")
        return []

    state = _load_state()
    seen_ids = set(state.get("processed_msg_ids", []))

    try:
        m = imaplib.IMAP4_SSL(host, 993, timeout=30)
        m.login(user, password)
        m.select(mailbox, readonly=False)

        criterion = "UNSEEN" if only_unseen else "ALL"
        typ, data = m.search(None, criterion)
        if typ != "OK" or not data or not data[0]:
            _log(f"no {criterion} messages in {mailbox}")
            m.logout()
            return []

        ids = data[0].split()[-max_messages:]  # cap
        _log(f"found {len(ids)} {criterion} messages")

        out = []
        for num in ids:
            typ, msg_data = m.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            msg_id = msg.get("Message-Id", f"no-id-{num.decode()}").strip()
            if msg_id in seen_ids:
                continue
            sender_name, sender_email = parseaddr(_decode(msg.get("From")))
            subject = _decode(msg.get("Subject"))
            try:
                received_at = parsedate_to_datetime(
                    msg.get("Date", "")).isoformat()
            except Exception:
                received_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            body = _extract_body(msg)

            out.append({
                "thread_id": msg.get("Thread-Id") or msg_id,
                "msg_id": msg_id,
                "imap_uid": num.decode(),
                "sender_email": sender_email,
                "sender_name": sender_name,
                "subject": subject,
                "body": body,
                "received_at": received_at,
            })
            seen_ids.add(msg_id)

        m.close()
        m.logout()

        state["processed_msg_ids"] = list(seen_ids)
        _save_state(state)
        _log(f"returning {len(out)} new messages")
        return out
    except Exception as e:
        _log(f"FAIL: {e}")
        return []


if __name__ == "__main__":
    import sys
    msgs = fetch_new_messages(only_unseen=True)
    print(f"fetched {len(msgs)} new messages:")
    for m in msgs[:5]:
        print(f"  {m['received_at']} | {m['sender_email']:35} | {m['subject'][:60]}")
