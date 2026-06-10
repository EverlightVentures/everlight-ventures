#!/usr/bin/env python3
"""
gmail_organizer.py -- Inbox triage daemon for 1m.rich.gee@gmail.com.

Why this exists:
  Marquise's Gmail INBOX is mixing Hive ops (Piper outreach replies, Stripe,
  Slack alerts, Resend events) with promo blast (Carnival Cruise, Hard Rock,
  Groupon, LinkedIn newsletters, DoorDash). Hive replies get lost.
  This script creates a Gmail label tree and classifies INBOX messages into
  it. Labels in Gmail = folders in IMAP, with the bonus that Gmail keeps a
  copy in INBOX visible until we explicitly move it.

Behavior:
  - Idempotent. Safe to run repeatedly.
  - Connects via IMAP (Gmail app password from env).
  - CREATEs labels if missing.
  - Walks INBOX (last N days, default 30) and classifies each message by
    rules (sender, subject, list-unsubscribe header).
  - APPLIES the matching label via APPEND to the label folder, then EXPUNGE
    from INBOX so the inbox view shows only unclassified messages.
  - Logs counts per label.

Run-modes:
  one-shot:   python3 gmail_organizer.py            (default 30-day backfill)
  daemon:     python3 gmail_organizer.py --daemon   (loops every 5 min)
  dry-run:    python3 gmail_organizer.py --dry-run  (classify but don't move)

Env required:
  IMAP_USER  (default 1m.rich.gee@gmail.com)
  IMAP_PASS  (Gmail app password)

Wire as Oracle systemd timer for ongoing filtering. See INSTALL_GMAIL_ORG.sh.
"""

from __future__ import annotations

import argparse
import email
import imaplib
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from email.header import decode_header

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("gmail_organizer")

USER = os.environ.get("IMAP_USER", "1m.rich.gee@gmail.com")
PWD = os.environ.get("IMAP_PASS", "dqyo wjlb jyzo mbmg")  # app password
HOST = "imap.gmail.com"

# Label tree we want to exist. Hive/* under [Gmail] is fine; Gmail allows
# nested labels via slash separator.
LABELS = [
    "Hive",
    "Hive/Piper-Outbound",      # cash offers we sent (BCC self loop / receipts)
    "Hive/Wholesale-Replies",   # seller / agent responses to our outreach
    "Hive/Stripe",              # payment receipts, customer signups
    "Hive/Hive-Alerts",         # ops alerts, deploys, health
    "Hive/Hive-Reports",        # gold-themed reports + GDoc shares
    "Hive/Slack-Notifications",
    "Hive/Resend-Events",       # bounce, delivery, complaint
    "Hive/AI-Consulting",       # client emails on AI builds
    "Hive/Trading-Bot",         # Coinbase + bot alerts
    "Promo",
    "Promo/Travel",             # Carnival, Resorts World, Hard Rock
    "Promo/Shopping",           # Groupon, DoorDash, Atlas Mastercard
    "Promo/Newsletters",        # LinkedIn, beehiiv, Uncovering AI
    "Promo/Other",
    "Personal",                 # facebook login, family, friends
]

# Classification rules. Order matters: first match wins.
# Each rule: (label, predicate(headers, raw_subject_lower, raw_from_lower))
def is_unsub(headers: dict) -> bool:
    return any(h.lower() == "list-unsubscribe" for h in headers.keys())


def make_rules():
    promo_travel = ["carnivalcruiselineemail", "rwlasvegas", "hardrock.com",
                    "marriott", "hotels.com", "expedia"]
    promo_shop = ["groupon", "doordash", "atlasfin", "amazon.com", "ebay.com",
                  "uber.com", "lyftmail"]
    promo_news = ["linkedin.com", "beehiiv.com", "substack.com",
                  "pulse.linkedin", "messages.doordash", "newsletters-noreply"]
    hive_alerts = ["hive-alerts", "alerts@", "n8n@", "noreply@github.com",
                   "cloudflare", "vercel.com"]
    hive_reports = ["docs.google.com", "drive-shares-noreply", "docs-noreply"]
    hive_slack = ["slackbot@", "no-reply@slack.com", "bot@slack.com",
                  "@slack.com"]
    resend_events = ["resend.com", "no-reply@resend"]
    stripe = ["stripe.com", "no-reply@stripe"]
    trading = ["coinbase", "binance", "kraken"]
    consulting = ["mobile_bar", "stark_ai"]
    personal = ["facebookmail", "instagram.com", "twitter.com",
                "x.com", "tiktokmail"]

    def has(needle_list, hay):
        return any(n in hay for n in needle_list)

    rules = [
        ("Hive/Resend-Events", lambda h, s, f: has(resend_events, f)),
        ("Hive/Stripe",        lambda h, s, f: has(stripe, f)),
        ("Hive/Slack-Notifications", lambda h, s, f: has(hive_slack, f)),
        ("Hive/Hive-Alerts",   lambda h, s, f: has(hive_alerts, f) or "alert" in s),
        ("Hive/Hive-Reports",  lambda h, s, f: has(hive_reports, f) or "shared" in s and "doc" in s),
        ("Hive/Trading-Bot",   lambda h, s, f: has(trading, f) or "bot fill" in s),
        ("Hive/AI-Consulting", lambda h, s, f: has(consulting, f)),
        # Piper outbound (notifications from the system to Marquise OR receipts from cold sends).
        # Check BEFORE Wholesale-Replies so internal "Wholesale Property Opportunity" subjects
        # don't get mis-classed as seller replies.
        ("Hive/Piper-Outbound",
            lambda h, s, f: ("piper@everlightventures" in f or "everlightventures.io" in f)),
        # Wholesale replies: property-keyword subject from a NOT-self, NOT-promo sender.
        ("Hive/Wholesale-Replies",
            lambda h, s, f: bool(re.search(r"\b(re:|reply|cash offer|14-day close|wholesale|assignment|emd|psa)\b", s))
                            and not has(promo_travel + promo_shop + promo_news, f)
                            and "piper@everlightventures" not in f
                            and "1m.rich.gee" not in f),
        # Promo buckets
        ("Promo/Travel",       lambda h, s, f: has(promo_travel, f)),
        ("Promo/Shopping",     lambda h, s, f: has(promo_shop, f)),
        ("Promo/Newsletters",  lambda h, s, f: has(promo_news, f)),
        ("Personal",           lambda h, s, f: has(personal, f)),
        ("Promo/Other",        lambda h, s, f: is_unsub(h)),
    ]
    return rules


def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            try:
                out.append(chunk.decode(enc or "utf-8", "replace"))
            except Exception:
                out.append(chunk.decode("utf-8", "replace"))
        else:
            out.append(chunk)
    return "".join(out)


def gmail_quote(label: str) -> str:
    # Gmail wants nested labels with forward slashes and quoted if spaces.
    return '"' + label.replace('"', '\\"') + '"'


def ensure_labels(m: imaplib.IMAP4_SSL):
    typ, data = m.list()
    existing = set()
    for line in data:
        if isinstance(line, bytes):
            line = line.decode("utf-8", "replace")
        # Each line: '(\\HasNoChildren) "/" "INBOX"'
        match = re.search(r'"([^"]+)"$', line)
        if match:
            existing.add(match.group(1))
    for label in LABELS:
        if label not in existing:
            typ, _ = m.create(gmail_quote(label))
            log.info(f"created label: {label} ({typ})")
        else:
            log.debug(f"label exists: {label}")


def classify(headers: dict, subj: str, frm: str, rules) -> str | None:
    s = subj.lower()
    f = frm.lower()
    for label, pred in rules:
        try:
            if pred(headers, s, f):
                return label
        except Exception:
            continue
    return None


def organize(days: int = 30, dry_run: bool = False):
    log.info(f"connecting to {HOST} as {USER}")
    m = imaplib.IMAP4_SSL(HOST)
    m.login(USER, PWD)

    ensure_labels(m)

    m.select("INBOX")
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    typ, data = m.search(None, f'(SINCE "{since}")')
    if typ != "OK" or not data or not data[0]:
        log.info("no messages found in window")
        m.logout()
        return

    ids = data[0].split()
    log.info(f"INBOX messages last {days}d: {len(ids)}")
    rules = make_rules()
    counts = {}

    for i in ids:
        typ, msg_data = m.fetch(i, "(BODY.PEEK[HEADER])")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        try:
            msg = email.message_from_bytes(raw)
        except Exception:
            continue
        headers = {k: v for k, v in msg.items()}
        subj = decode_str(msg.get("Subject", ""))
        frm = decode_str(msg.get("From", ""))
        label = classify(headers, subj, frm, rules)
        if not label:
            continue
        counts[label] = counts.get(label, 0) + 1
        if dry_run:
            log.info(f"[DRY] {label}  {frm[:50]}  | {subj[:60]}")
            continue
        # Copy to label, then mark deleted in INBOX. EXPUNGE at end.
        try:
            m.copy(i, gmail_quote(label))
            m.store(i, "+FLAGS", "\\Deleted")
        except Exception as exc:
            log.warning(f"copy/store failed on msg {i}: {exc}")

    if not dry_run:
        m.expunge()

    m.close()
    m.logout()

    log.info("---- summary ----")
    for label in sorted(counts.keys()):
        log.info(f"  {label}: {counts[label]}")
    log.info(f"  total moved: {sum(counts.values())}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="lookback window in days (default 30)")
    ap.add_argument("--dry-run", action="store_true",
                    help="classify but do not move")
    ap.add_argument("--daemon", action="store_true",
                    help="loop every 5 min instead of one-shot")
    ap.add_argument("--interval", type=int, default=300,
                    help="daemon poll interval seconds (default 300)")
    args = ap.parse_args()

    if args.daemon:
        while True:
            try:
                organize(days=2, dry_run=args.dry_run)
            except Exception as exc:
                log.error(f"organize loop error: {exc}")
            time.sleep(args.interval)
    else:
        organize(days=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
