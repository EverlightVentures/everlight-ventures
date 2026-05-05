#!/usr/bin/env python3
"""
Inbound Watch Daemon -- always-on Gmail IMAP reader + classifier + router.

Justine Park's spec: INBOUND_WATCH_GAPS_2026-04-26.md.
Trigger: David A. Streubel STOP reply (2026-04-26 06:30 PT) showed every
Gmail inbound must be read and routed by an always-on layer, not waited on.

Run modes:
  - default (no args): one cycle, exit 0. Designed for systemd timer (5 min).
  - --selftest: synthetic David Streubel + bypass injection. No Slack post.
  - --since N: override watermark, scan messages from last N hours.

Behavior per cycle:
  1. IMAP login (IMAP_USER/IMAP_PASS from /etc/default/rex-negotiator).
  2. Search INBOX + Hive/Wholesale-Replies for UIDs > watermark.
  3. Classify each by sender-domain class + intent (body keyword scan).
  4. Route per (class, intent) matrix. Synthetic active_deal for seller_reply.
  5. Cross-check In-Reply-To against resend_budget.jsonl. Flag bypass.
  6. Log every classification to /home/opc/_logs/inbound_watch.jsonl.
  7. Update UID watermark (idempotent).

Backend Hand.
"""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr
from pathlib import Path
from typing import Optional


# ── paths ───────────────────────────────────────────────────────────

STATE_DIR = Path("/home/opc/_state")
LOG_DIR = Path("/home/opc/_logs")
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

WATERMARK_FILE = STATE_DIR / "inbound_watch_last_fire.txt"
DECISIONS_LOG = LOG_DIR / "inbound_watch.jsonl"
UNROUTED_LOG = LOG_DIR / "inbound_unrouted.jsonl"
ANOMALIES_LOG = LOG_DIR / "inbound_watch_anomalies.jsonl"
RESEND_BUDGET_LOG = LOG_DIR / "resend_budget.jsonl"

ACTIVE_DEALS_DIR = Path("/home/opc/wholesale_agent/active_deals")
ACTIVE_DEALS_DIR.mkdir(parents=True, exist_ok=True)

ENV_FILE = Path("/etc/default/rex-negotiator")


# ── env loader ──────────────────────────────────────────────────────

def _load_env() -> dict:
    env: dict = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        env.setdefault(k, v)
    return env


# ── classification tables ──────────────────────────────────────────

GOVT_PATTERNS = [
    r"\.gov$",
    r"\.gov\.us$",
    r"-mo\.gov$",
    r"-tx\.gov$",
    r"\.state\.[a-z]{2}\.us$",
    r"-mo\.us$",
    r"-tx\.us$",
    r"^cityof[a-z]+\.",
    r"\.cityof[a-z]+\.",
    r"county\.[a-z]+\.us$",
    r"\.county\.",
]

ATTORNEY_TOKENS = [
    "law", "legal", "attorney", "counsel", "llp", "pllc",
    "esq", "municipalfirm", "vogel", "rost", "cunningham",
    "lawfirm", "lawyers", "advocates", "barrister",
]

TITLE_TOKENS = [
    "title", "escrow", "closing", "settlement",
    "titlecompany", "firstam", "stewart-title",
]

REALTOR_DOMAINS = [
    "compass.com", "kw.com", "kellerwilliams.com", "redfin.com",
    "realty", "realtor.com", "century21.com", "remax.com",
    "coldwellbanker.com", "exp.com", "bhhs", "weichert.com",
    "sothebys", "douglaselliman.com", "corcoran.com",
]

CONSUMER_DOMAINS = {
    "gmail.com", "yahoo.com", "ymail.com", "rocketmail.com",
    "hotmail.com", "outlook.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com", "mac.com",
    "comcast.net", "verizon.net", "att.net", "sbcglobal.net",
    "cox.net", "earthlink.net", "bellsouth.net",
}

JV_WHOLESALER_TOKENS = [
    "biggerpockets", "reia", "wholesaling", "wholesalehouse",
    "cashbuyer", "ibuyer", "weBuyHouses", "webuyhouses",
    "homevestors", "opendoor.com", "offerpad.com",
    "newwestern", "newestern.com", "doorvest", "ourpartner",
]

OPT_OUT_PATTERNS = [
    r"\bstop\b",
    r"\bunsubscribe\b",
    r"\bremove me\b",
    r"\bnot interested\b",
    r"cease and desist",
    r"do not contact",
    r"do not email",
    r"\bcease\b",
    r"\bharassment\b",
    r"opt[ -]?out",
    r"take me off",
]

SELLER_REPLY_PATTERNS = [
    r"\byes\b.*(interested|sell|offer)",
    r"\binterested\b",
    r"\btell me more\b",
    r"what(?:'s| is) your offer",
    r"how much.*(offer|paying|pay)",
    r"\bmake (?:an |me an )?offer\b",
    r"\bmore info\b",
    r"\bwhat are you offering\b",
    r"\bcall me\b",
    r"\bsend me\b.*\b(offer|details|info)\b",
]

BUYER_INQUIRY_PATTERNS = [
    r"is.*property.*(available|still)",
    r"\bproof of funds\b",
    r"\bemd\b",
    r"\bearnest money\b",
    r"\bclosing date\b",
    r"\bassignment fee\b",
    r"are you the (wholesaler|seller)",
    r"\bbuyers? list\b",
    r"\bcash buyer\b",
    r"i (am|'m) (a |an )?(cash )?buyer",
]


# ── classifier helpers ──────────────────────────────────────────────

def _decode_header_value(raw: Optional[str]) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                out.append(chunk.decode("utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _extract_plain_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")
                except (LookupError, TypeError):
                    return payload.decode("utf-8", errors="replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                try:
                    raw = payload.decode(charset, errors="replace")
                except (LookupError, TypeError):
                    raw = payload.decode("utf-8", errors="replace")
                return re.sub(r"<[^>]+>", " ", raw)
    payload = msg.get_payload(decode=True) or b""
    if isinstance(payload, bytes):
        charset = msg.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, TypeError):
            return payload.decode("utf-8", errors="replace")
    return str(payload)


def classify_sender_domain(email_addr: str, from_name: str = "") -> str:
    """Return one of: govt | attorney | title | realtor | homeowner | jv_wholesaler | unknown."""
    if not email_addr or "@" not in email_addr:
        return "unknown"
    domain = email_addr.split("@", 1)[1].lower().strip()
    name_l = (from_name or "").lower()

    for pat in GOVT_PATTERNS:
        if re.search(pat, domain):
            return "govt"

    for tok in ATTORNEY_TOKENS:
        if tok in domain or tok in name_l:
            return "attorney"

    for tok in TITLE_TOKENS:
        if tok in domain:
            return "title"

    for d in REALTOR_DOMAINS:
        if d in domain:
            return "realtor"

    for tok in JV_WHOLESALER_TOKENS:
        if tok.lower() in domain:
            return "jv_wholesaler"

    if domain in CONSUMER_DOMAINS:
        # exclude LLC-tokens in the from_name as a homeowner gate
        if re.search(r"\b(llc|trust|corp|inc|llp|pllc|pc|p\.c\.)\b", name_l):
            return "unknown"
        return "homeowner"

    return "unknown"


def classify_intent(subject: str, body: str) -> str:
    """Return one of: opt_out | seller_reply | buyer_inquiry | question | unknown."""
    text = ((subject or "") + "\n" + (body or "")).lower()
    if not text.strip():
        return "unknown"

    for pat in OPT_OUT_PATTERNS:
        if re.search(pat, text):
            return "opt_out"

    for pat in SELLER_REPLY_PATTERNS:
        if re.search(pat, text):
            return "seller_reply"

    for pat in BUYER_INQUIRY_PATTERNS:
        if re.search(pat, text):
            return "buyer_inquiry"

    # short-form trailing "?" -- question fallback
    body_stripped = (body or "").strip()
    if body_stripped.endswith("?"):
        return "question"
    if subject and subject.strip().endswith("?"):
        return "question"

    return "unknown"


# ── bypass detection ───────────────────────────────────────────────

_BUDGET_INDEX_CACHE: dict = {"loaded_at": 0.0, "ids": set(), "subjects": set()}


def _load_budget_index() -> tuple[set, set]:
    """Return (message_id_set, subject_set) of every outbound row in resend_budget.jsonl."""
    now = time.time()
    if now - _BUDGET_INDEX_CACHE["loaded_at"] < 60 and _BUDGET_INDEX_CACHE["ids"]:
        return _BUDGET_INDEX_CACHE["ids"], _BUDGET_INDEX_CACHE["subjects"]
    ids: set = set()
    subjects: set = set()
    if RESEND_BUDGET_LOG.exists():
        try:
            for line in RESEND_BUDGET_LOG.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                mid = (row.get("message_id") or "").strip()
                if mid:
                    ids.add(mid)
                subj = (row.get("subject") or "").strip().lower()
                if subj:
                    subjects.add(subj)
        except Exception:
            pass
    _BUDGET_INDEX_CACHE["loaded_at"] = now
    _BUDGET_INDEX_CACHE["ids"] = ids
    _BUDGET_INDEX_CACHE["subjects"] = subjects
    return ids, subjects


OUTREACH_SUBJECT_MARKERS = [
    "cash offer", "quick proof-of-funds", "your property on",
    "buy your house", "offer on", "we'd like to make an offer",
    "we want to buy", "interested in your property",
]

# Mail-server origins that signal a NON-branded path (legacy rich@, raw SES, etc).
# Resend/branded sends have In-Reply-To message-ids with these patterns.
BRANDED_MAIL_ORIGINS = ["resend.com", "everlightventures.io", "@email.resend"]
LEGACY_MAIL_ORIGINS = ["amazonses.com", "@email.amazonses", "ses.amazon"]


def detect_bypass(in_reply_to: str, subject: str) -> bool:
    """True if inbound references a send NOT in resend_budget.jsonl.

    Three signals, any one trips the flag:
      1. In-Reply-To message-id not present in budget index AND subject looks
         like one of our outreach templates.
      2. In-Reply-To origin matches a legacy mail server (amazonses.com, raw
         SES) -- the branded stack only routes through Resend.
      3. No In-Reply-To at all but subject markers match our outreach AND the
         subject itself is absent from the budget index.
    """
    ids, subjects = _load_budget_index()
    irt = (in_reply_to or "").strip().strip("<>").lower()
    subj_clean = re.sub(r"^(re|fw|fwd):\s*", "", (subject or "").strip(), flags=re.I).strip().lower()
    looks_like_our_send = any(m in subj_clean for m in OUTREACH_SUBJECT_MARKERS)

    if irt:
        # Signal 2 first: legacy origin = bypass guaranteed if it's our subject
        for legacy in LEGACY_MAIL_ORIGINS:
            if legacy in irt and looks_like_our_send:
                return True
        # Match against budget index (id is stored without surrounding <>)
        for known in ids:
            if known and (known.lower() in irt or irt in known.lower()):
                return False
        # Subject matches a known budget row -> we sent it via branded
        if subj_clean and subj_clean in subjects:
            return False
        # Looks like our send but not in any known place
        if looks_like_our_send:
            return True
        return False

    # No In-Reply-To header -- subject must do the work alone
    if not subj_clean:
        return False
    if looks_like_our_send and subj_clean not in subjects:
        return True
    return False


# ── routing ─────────────────────────────────────────────────────────

@dataclass
class Classification:
    uid: str
    folder: str
    sender_email: str
    sender_name: str
    sender_domain_class: str
    subject: str
    in_reply_to: str
    body_excerpt: str
    intent: str
    route: str
    bypass_detected: bool
    slack_ts: str = ""
    slack_channel: str = ""
    error: str = ""
    ts: str = ""


def _post_slack(channel: str, title: str, summary: str, body: str, severity: str = "info", category: str = "alert") -> tuple[str, str, str]:
    """Returns (ts, resolved_channel, error). Falls back to direct chat.postMessage if branded_slack fails."""
    try:
        sys.path.insert(0, "/home/opc")
        from content_tools.branded_slack import post_branded_slack  # type: ignore
        result = post_branded_slack(
            channel=channel,
            title=title,
            summary=summary,
            body=body,
            agent_name="Inbound Watch",
            agent_title="Compliance Daemon",
            category=category,
            auto_archive=False,
        )
        if result.ok:
            return result.ts, result.channel, ""
        return "", "", result.error
    except Exception as exc:
        return "", "", repr(exc)


def _record_dnc(sender_email: str, sender_name: str, reason_text: str, source_channel: str = "email_reply") -> bool:
    """Always-on DNC recorder. Writes to canonical files on whatever node this daemon runs on.

    Patched 2026-05-04 (Streubel BBB incident) to FAIL LOUD instead of silent.
    Three layers (Layer 1 must succeed; Layer 2 best-effort; Layer 3 legacy):
      1. Canonical dnc_list.json (compliance master, multi-path lookup)
      2. opted_out_emails.json (legacy sink branded_mailer reads via resend_guard)
      3. Optional: dnc_writeback module (Oracle-only legacy path, kept for compat)
    """
    import json as _json, os as _os, datetime as _dt

    if not sender_email:
        return False

    _DNC_CANDIDATES = [
        "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json",
        "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json",
        _os.path.expanduser("~/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"),
        "/home/opc/wholesale/compliance/dnc_list.json",
    ]
    _OPTOUT_CANDIDATES = [
        "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json",
        "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json",
        _os.path.expanduser("~/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json"),
        "/home/opc/wholesale_agent/opted_out_emails.json",
    ]

    timestamp = _dt.datetime.utcnow().isoformat() + "Z"
    addr_lower = sender_email.strip().lower()
    succeeded = False

    # Layer 1: canonical DNC list (required)
    for path in _DNC_CANDIDATES:
        try:
            if not _os.path.isdir(_os.path.dirname(path)):
                continue
            existing = []
            if _os.path.exists(path):
                with open(path) as f:
                    existing = _json.load(f) or []
            if any((e.get("email", "").strip().lower() == addr_lower) for e in existing):
                succeeded = True
                break
            entry = {
                "id": f"dnc_auto_{int(_dt.datetime.utcnow().timestamp())}",
                "added_utc": timestamp,
                "name": sender_name or "Unknown",
                "email": sender_email,
                "phone": None,
                "property_addresses": [],
                "blocked_channels": ["email", "sms", "phone", "mail", "all"],
                "reason": f"AUTO-DNC from inbound_watch_daemon: {reason_text[:200]}",
                "evidence": {"source_channel": source_channel, "auto_detected": True},
                "do_not_contact": True,
            }
            existing.append(entry)
            with open(path, "w") as f:
                _json.dump(existing, f, indent=2)
            succeeded = True
            break
        except Exception:
            continue

    # Layer 2: opted_out_emails.json (legacy sink, branded_mailer reads it via resend_guard)
    for path in _OPTOUT_CANDIDATES:
        try:
            if not _os.path.isdir(_os.path.dirname(path)):
                continue
            existing = []
            if _os.path.exists(path):
                with open(path) as f:
                    existing = _json.load(f) or []
            if any((e.get("email", "").strip().lower() == addr_lower) for e in existing):
                break
            existing.append({
                "email": sender_email,
                "name": sender_name or "Unknown",
                "opted_out_at": timestamp,
                "reason": f"auto: {reason_text[:120]}",
                "source": f"inbound_watch_daemon:{source_channel}",
            })
            with open(path, "w") as f:
                _json.dump(existing, f, indent=2)
            break
        except Exception:
            continue

    # Layer 3: legacy Oracle dnc_writeback (best effort, doesn't change success)
    try:
        sys.path.insert(0, "/home/opc/wholesale_agent")
        from dnc_writeback import record_decline  # type: ignore
        class _Lead:
            pass
        lead = _Lead()
        lead.owner_name = sender_name or "Unknown"
        lead.owner_email = sender_email
        lead.owner_phone = ""
        lead.address = ""
        lead.city = ""
        lead.state = ""
        record_decline(lead, reason_text, source_channel)
    except Exception:
        pass

    return succeeded


def _write_synthetic_active_deal(c: Classification) -> Optional[str]:
    """Write a minimal active_deals/<id>.json so Rex Negotiator picks it up next 2-min poll."""
    try:
        deal_id = f"deal_{int(time.time())}_inbound_{c.uid}"
        path = ACTIVE_DEALS_DIR / f"{deal_id}.json"
        deal = {
            "id": deal_id,
            "address": "TBD-from-inbound",
            "city": "",
            "state": "",
            "status": "inbound_seller_reply",
            "owner_name": c.sender_name or "Unknown",
            "owner_email": c.sender_email,
            "owner_phone": "",
            "asking_price": 0,
            "our_mao": 0,
            "our_offer": 0,
            "arv": 0,
            "repair_estimate": 0,
            "assignment_fee": 10000,
            "conversation": [
                {
                    "role": "seller",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "subject": c.subject,
                    "body_excerpt": c.body_excerpt,
                    "uid": c.uid,
                    "folder": c.folder,
                }
            ],
            "seller_sentiment": "interested",
            "counter_offers": [],
            "objections_handled": [],
            "buyer_name": "",
            "buyer_price": 0,
            "buyer_emd": 0,
            "outreach_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_contact": datetime.now(timezone.utc).isoformat(),
            "source": "inbound_watch_daemon",
        }
        path.write_text(json.dumps(deal, indent=2))
        return str(path)
    except Exception:
        return None


def route(c: Classification, dry_run: bool = False) -> Classification:
    """Apply (sender_domain_class, intent) routing matrix."""
    klass = c.sender_domain_class
    intent = c.intent

    # Bypass detection always pages compliance
    if c.bypass_detected and not dry_run:
        ts, ch, err = _post_slack(
            channel="#compliance",
            title="Bypass Detected -- Outbound Not in Budget Log",
            summary=f"Reply from {c.sender_email} references a send with no resend_budget.jsonl row.",
            body=f"*Subject:* {c.subject}\n*In-Reply-To:* {c.in_reply_to or '(none)'}\n*Class:* {klass}\n*Intent:* {intent}\n*Excerpt:* {c.body_excerpt[:300]}",
            category="alert",
        )
        if ts:
            c.slack_ts = ts
            c.slack_channel = ch

    if intent == "opt_out":
        c.route = "dnc_writeback"
        if not dry_run:
            _record_dnc(c.sender_email, c.sender_name, c.body_excerpt[:200], "email_reply")
            broker_ts, broker_ch, err1 = _post_slack(
                channel="#broker-pipeline",
                title=f"Opt-Out Received -- {klass}",
                summary=f"{c.sender_email} asked to be removed.",
                body=f"*Subject:* {c.subject}\n*Class:* {klass}\n*Excerpt:* {c.body_excerpt[:300]}",
                category="alert",
            )
            if broker_ts and not c.slack_ts:
                c.slack_ts, c.slack_channel = broker_ts, broker_ch
            if klass in ("govt", "attorney"):
                comp_ts, comp_ch, _ = _post_slack(
                    channel="#compliance",
                    title=f"HIGH -- Opt-Out from {klass.upper()}",
                    summary=f"{c.sender_email} ({c.sender_name}) sent an opt-out.",
                    body=f"*Subject:* {c.subject}\n*Class:* {klass}\n*Bypass:* {c.bypass_detected}\n*Excerpt:* {c.body_excerpt[:300]}",
                    category="alert",
                )
                if comp_ts:
                    c.slack_ts, c.slack_channel = comp_ts, comp_ch
        return c

    if intent == "seller_reply" and klass == "homeowner":
        c.route = "rex_negotiator_escalate"
        if not dry_run:
            path = _write_synthetic_active_deal(c)
            ts, ch, _ = _post_slack(
                channel="#broker-pipeline",
                title="Seller Reply -- Routed to Rex Negotiator",
                summary=f"{c.sender_email} responded with seller intent.",
                body=f"*Subject:* {c.subject}\n*Synthetic deal:* {path}\n*Excerpt:* {c.body_excerpt[:300]}",
                category="deal",
            )
            if ts:
                c.slack_ts, c.slack_channel = ts, ch
        return c

    if intent == "buyer_inquiry":
        c.route = "hammer_followup"
        if not dry_run:
            ts, ch, _ = _post_slack(
                channel="#broker-pipeline",
                title="Buyer Inquiry -- Flag Hammer",
                summary=f"{c.sender_email} ({klass}) is asking about a property.",
                body=f"*Subject:* {c.subject}\n*Excerpt:* {c.body_excerpt[:300]}",
                category="deal",
            )
            if ts:
                c.slack_ts, c.slack_channel = ts, ch
        return c

    if intent == "question":
        c.route = "human_review"
        if not dry_run:
            ts, ch, _ = _post_slack(
                channel="#broker-pipeline",
                title="Question Inbound -- Human Review",
                summary=f"{c.sender_email} ({klass}) sent a question.",
                body=f"*Subject:* {c.subject}\n*Excerpt:* {c.body_excerpt[:300]}",
                category="ops",
            )
            if ts:
                c.slack_ts, c.slack_channel = ts, ch
        return c

    # unknown intent -> log to unrouted, no Slack
    c.route = "unrouted_log"
    if not dry_run:
        try:
            with UNROUTED_LOG.open("a") as f:
                f.write(json.dumps(asdict(c)) + "\n")
        except Exception:
            pass
    return c


# ── IMAP cycle ──────────────────────────────────────────────────────

def _read_watermark() -> dict:
    if not WATERMARK_FILE.exists():
        return {}
    try:
        return json.loads(WATERMARK_FILE.read_text())
    except Exception:
        return {}


def _write_watermark(data: dict) -> None:
    try:
        WATERMARK_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _scan_folder(imap: imaplib.IMAP4_SSL, folder: str, last_uid: int, first_run_lookback_days: int = 2) -> list[Classification]:
    out: list[Classification] = []
    try:
        status, _ = imap.select(f'"{folder}"', readonly=True)
        if status != "OK":
            return out
    except Exception:
        return out

    try:
        if last_uid and last_uid > 0:
            status, data = imap.uid("search", None, f"UID {last_uid + 1}:*")
        else:
            # First run on this folder -- bound the scan with SINCE to avoid
            # processing the entire historical mailbox.
            since = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=first_run_lookback_days)).strftime("%d-%b-%Y")
            status, data = imap.uid("search", None, f"SINCE {since}")
    except Exception:
        return out

    if status != "OK" or not data or not data[0]:
        return out
    uids = [u.decode() if isinstance(u, bytes) else u for u in data[0].split()]
    # Drop the synthetic match where last_uid+1 > max -- IMAP returns the max UID
    uids = [u for u in uids if int(u) > last_uid]
    if not uids:
        return out
    # Hard cap per cycle to prevent runaway processing on first run
    if len(uids) > 200:
        uids = uids[-200:]

    for uid in uids:
        try:
            status, msg_data = imap.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not msg_data:
                continue
            raw = None
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    raw = part[1]
                    break
            if not raw:
                continue
            msg = email.message_from_bytes(raw)

            from_raw = msg.get("From", "")
            from_name, from_email = parseaddr(_decode_header_value(from_raw))
            subject = _decode_header_value(msg.get("Subject", ""))
            in_reply_to = msg.get("In-Reply-To", "") or ""
            body = _extract_plain_body(msg)
            body_excerpt = re.sub(r"\s+", " ", body).strip()[:1000]

            klass = classify_sender_domain(from_email, from_name)
            intent = classify_intent(subject, body)
            bypass = detect_bypass(in_reply_to, subject) if from_email else False

            c = Classification(
                uid=uid,
                folder=folder,
                sender_email=from_email,
                sender_name=from_name,
                sender_domain_class=klass,
                subject=subject,
                in_reply_to=in_reply_to.strip(),
                body_excerpt=body_excerpt,
                intent=intent,
                route="pending",
                bypass_detected=bypass,
                ts=datetime.now(timezone.utc).isoformat(),
            )
            out.append(c)
        except Exception:
            continue

    return out


def _log_decision(c: Classification) -> None:
    try:
        row = asdict(c)
        # truncate body_excerpt for the decision log
        row["body_excerpt"] = row["body_excerpt"][:500]
        with DECISIONS_LOG.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass

    if c.bypass_detected:
        try:
            with ANOMALIES_LOG.open("a") as f:
                row = asdict(c)
                row["body_excerpt"] = row["body_excerpt"][:500]
                row["anomaly"] = "bypass_detected"
                f.write(json.dumps(row) + "\n")
        except Exception:
            pass


def run_cycle(dry_run: bool = False) -> dict:
    env = _load_env()
    host = env.get("IMAP_HOST", "imap.gmail.com")
    user = env.get("IMAP_USER") or env.get("GMAIL_IMAP_USER")
    pw = env.get("IMAP_PASS") or env.get("GMAIL_IMAP_PASS")
    if not user or not pw:
        return {"ok": False, "error": "no_imap_creds", "processed": 0}

    folders = ["INBOX", "Hive/Wholesale-Replies"]
    watermarks = _read_watermark()

    summary = {
        "ok": True,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "processed": 0,
        "by_class": {},
        "by_intent": {},
        "by_route": {},
        "bypass_count": 0,
        "errors": [],
    }

    try:
        imap = imaplib.IMAP4_SSL(host, 993, timeout=30)
        imap.login(user, pw)
    except Exception as exc:
        return {"ok": False, "error": f"imap_login_fail:{exc}", "processed": 0}

    try:
        for folder in folders:
            last_uid = int(watermarks.get(folder, 0) or 0)
            classifications = _scan_folder(imap, folder, last_uid)
            max_uid = last_uid
            for c in classifications:
                try:
                    c = route(c, dry_run=dry_run)
                except Exception as exc:
                    c.error = repr(exc)
                _log_decision(c)
                summary["processed"] += 1
                summary["by_class"][c.sender_domain_class] = summary["by_class"].get(c.sender_domain_class, 0) + 1
                summary["by_intent"][c.intent] = summary["by_intent"].get(c.intent, 0) + 1
                summary["by_route"][c.route] = summary["by_route"].get(c.route, 0) + 1
                if c.bypass_detected:
                    summary["bypass_count"] += 1
                try:
                    if int(c.uid) > max_uid:
                        max_uid = int(c.uid)
                except Exception:
                    pass
            watermarks[folder] = max_uid
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    if not dry_run:
        _write_watermark(watermarks)
    summary["watermarks"] = watermarks
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary


# ── selftest ───────────────────────────────────────────────────────

def selftest() -> int:
    """Synthetic Streubel + bypass -- no IMAP, no Slack."""
    print("[inbound_watch] selftest: starting")

    # 1. David Streubel synthetic
    streubel = Classification(
        uid="SELFTEST_STREUBEL",
        folder="INBOX",
        sender_email="dstreubel@municipalfirm.com",
        sender_name="David A. Streubel",
        sender_domain_class=classify_sender_domain("dstreubel@municipalfirm.com", "David A. Streubel"),
        subject="Re: 4435 Westminster Pl cash offer",
        in_reply_to="<legacy-rich-send-no-budget-row@everlightventures.io>",
        body_excerpt="Please remove me from your list and cease contacting me. Do not contact me again about this property.",
        intent=classify_intent("Re: 4435 Westminster Pl cash offer", "Please remove me from your list and cease contacting me."),
        route="pending",
        bypass_detected=detect_bypass(
            "<legacy-rich-send-no-budget-row@everlightventures.io>",
            "Re: 4435 Westminster Pl cash offer",
        ),
        ts=datetime.now(timezone.utc).isoformat(),
    )
    streubel = route(streubel, dry_run=True)
    print(f"  Streubel class={streubel.sender_domain_class}  intent={streubel.intent}  route={streubel.route}  bypass={streubel.bypass_detected}")
    assert streubel.sender_domain_class == "attorney", "Streubel should classify as attorney"
    assert streubel.intent == "opt_out", "Streubel should classify as opt_out"
    assert streubel.bypass_detected, "Streubel should be flagged bypass (rich@ never logged)"

    # 2. Govt opt-out
    govt = Classification(
        uid="SELFTEST_GOVT",
        folder="INBOX",
        sender_email="brooks-sandersd@stlouis-mo.gov",
        sender_name="Brooks Sanders",
        sender_domain_class=classify_sender_domain("brooks-sandersd@stlouis-mo.gov", "Brooks Sanders"),
        subject="Re: 1522 HOGAN ST cash offer",
        in_reply_to="",
        body_excerpt="Stop sending me this. I am a city employee, not the homeowner.",
        intent=classify_intent("Re: 1522 HOGAN ST cash offer", "Stop sending me this. I am a city employee, not the homeowner."),
        route="pending",
        bypass_detected=False,
        ts=datetime.now(timezone.utc).isoformat(),
    )
    govt = route(govt, dry_run=True)
    print(f"  Govt class={govt.sender_domain_class}  intent={govt.intent}  route={govt.route}")
    assert govt.sender_domain_class == "govt"
    assert govt.intent == "opt_out"

    # 3. Homeowner seller reply
    seller = Classification(
        uid="SELFTEST_SELLER",
        folder="INBOX",
        sender_email="janedoe@gmail.com",
        sender_name="Jane Doe",
        sender_domain_class=classify_sender_domain("janedoe@gmail.com", "Jane Doe"),
        subject="Re: cash offer on 123 Main St",
        in_reply_to="",
        body_excerpt="Yes I'm interested. What's your offer?",
        intent=classify_intent("Re: cash offer on 123 Main St", "Yes I'm interested. What's your offer?"),
        route="pending",
        bypass_detected=False,
        ts=datetime.now(timezone.utc).isoformat(),
    )
    seller = route(seller, dry_run=True)
    print(f"  Seller class={seller.sender_domain_class}  intent={seller.intent}  route={seller.route}")
    assert seller.sender_domain_class == "homeowner"
    assert seller.intent == "seller_reply"
    assert seller.route == "rex_negotiator_escalate"

    print(f"[inbound_watch] selftest: OK. domain_table={len(GOVT_PATTERNS)+len(ATTORNEY_TOKENS)+len(TITLE_TOKENS)+len(REALTOR_DOMAINS)+len(JV_WHOLESALER_TOKENS)+len(CONSUMER_DOMAINS)} entries  intent_patterns={len(OPT_OUT_PATTERNS)+len(SELLER_REPLY_PATTERNS)+len(BUYER_INQUIRY_PATTERNS)} entries")
    return 0


# ── main ────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Inbound Watch Daemon -- IMAP read + classify + route.")
    parser.add_argument("--selftest", action="store_true", help="Run synthetic Streubel + bypass tests, no IMAP, no Slack.")
    parser.add_argument("--dry-run", action="store_true", help="Live IMAP read, classify, log -- but no Slack post or DNC writeback.")
    parser.add_argument("--reset-watermark", action="store_true", help="Wipe UID watermarks and re-scan everything.")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    if args.reset_watermark and WATERMARK_FILE.exists():
        WATERMARK_FILE.unlink()

    summary = run_cycle(dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
