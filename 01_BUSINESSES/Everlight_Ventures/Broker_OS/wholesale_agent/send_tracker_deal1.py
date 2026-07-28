#!/usr/bin/env python3
"""
send_tracker_deal1.py -- fire the Deal-1 first-touch to the owner-confirmed
Memphis leads in tn_deal_tracker.json (status == email_found).

Operator directive 2026-06-11 (Rich): sole-prop, <=3 deals unlicensed, digital-only,
take the risk, GO. Sends route through rex_utils.safe_send_email(state="TN") which
keeps every gate that matters -- eradication/DNC, TN state-gate, resend_budget,
weekly_cadence, branded_mailer gold template -- and appends a DIGITAL opt-out footer
(STOP + opt-out@; NO postal box, per [[feedback_wholesale_digital_only_no_postal_box]]).

Usage:
    set -a; . /root/.config/everlight/secrets.env; set +a
    python3 send_tracker_deal1.py --dry-run     # show who/what, send nothing
    python3 send_tracker_deal1.py               # SEND (respects daily budget)
    python3 send_tracker_deal1.py --limit 5     # cap this run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
WH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
TRACKER = WH / "tn_deal_tracker.json"

from rex_utils import safe_send_email


def _pretty_addr(a: str) -> str:
    return re.sub(r"\s+", " ", (a or "").strip()).title()


def _pitch(addr: str) -> tuple[str, str]:
    """Warm, honest first-touch cash-offer email. Address-led greeting (no name)
    so a mis-parsed assessor name never lands wrong. Plain text; branded_mailer
    wraps it in the gold template and appends the digital opt-out footer."""
    nice = _pretty_addr(addr)
    subject = f"Your property at {nice} -- cash offer?"
    body = (
        f"Hi there,\n\n"
        f"My name's Piper with Everlight Ventures. I'm reaching out directly about "
        f"{nice}. We're buying a few houses in the Memphis area this month, as-is, "
        f"for cash -- no repairs, no agent commissions, no clean-out needed on your end.\n\n"
        f"If you've ever thought about selling, I'd love to make you a straightforward "
        f"cash offer and let you pick the closing date. There's no obligation and no "
        f"pressure -- even if it's a 'maybe someday,' I'm happy to share what we could "
        f"pay so you have the number.\n\n"
        f"Would it be alright if I put together an offer for {nice}? Just reply and let "
        f"me know.\n\n"
        f"Talk soon,\n"
        f"Piper Reeves\n"
        f"Everlight Ventures\n"
        f"piper@everlightventures.io"
    )
    return subject, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tracker = json.loads(TRACKER.read_text())

    # Owner-confirmed, has email, not yet emailed -- de-dup by property address.
    seen, queue = set(), []
    for pid, lead in tracker.items():
        if lead.get("status") != "email_found":
            continue
        email = (lead.get("email") or "").strip()
        if not email or lead.get("outreach_count", 0) > 0:
            continue
        addr_key = re.sub(r"\s+", " ", (lead.get("property_address") or "").upper())
        if addr_key in seen:
            continue
        seen.add(addr_key)
        queue.append((pid, lead))

    batch = queue[:args.limit]
    print("=" * 66)
    print(f"DEAL-1 first-touch -- {len(batch)} owner-confirmed Memphis leads "
          f"({'DRY-RUN' if args.dry_run else 'LIVE SEND'})")
    print("=" * 66)

    sent = blocked = 0
    for i, (pid, lead) in enumerate(batch, 1):
        email = lead["email"].strip()
        addr = lead.get("property_address", "")
        subject, body = _pitch(addr)

        if args.dry_run:
            print(f"  [{i:2d}] WOULD SEND -> {email:32s} {_pretty_addr(addr)}")
            continue

        ok = safe_send_email(
            to=email, subject=subject, body=body,
            state="TN", action="outreach",
            agent_name="Piper Reeves",
            agent_title="Acquisitions, Everlight Ventures",
            agent_email="piper@everlightventures.io",
            from_email="piper@everlightventures.io",
            reply_to="piper@everlightventures.io",
        )
        if ok:
            sent += 1
            lead["status"] = "emailed"
            lead["outreach_count"] = lead.get("outreach_count", 0) + 1
            lead["last_contact"] = datetime.now(timezone.utc).isoformat()
            lead.setdefault("notes", []).append(
                f"Deal-1 first-touch sent {datetime.now(timezone.utc).date()}")
            print(f"  [{i:2d}] SENT ------> {email:32s} {_pretty_addr(addr)}")
        else:
            blocked += 1
            print(f"  [{i:2d}] BLOCKED/QUEUED {email:32s} (gate or budget -- see logs)")
        # checkpoint after each send so a crash never double-sends
        TRACKER.write_text(json.dumps(tracker, indent=1))

    print("\n" + "=" * 66)
    if args.dry_run:
        print(f"DRY-RUN: {len(batch)} would send. Re-run without --dry-run to fire.")
    else:
        print(f"SENT {sent} | blocked/queued {blocked} | tracker updated -> status=emailed")
        print("Replies land in piper@everlightventures.io. Inbound matcher routes to TN lane.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
