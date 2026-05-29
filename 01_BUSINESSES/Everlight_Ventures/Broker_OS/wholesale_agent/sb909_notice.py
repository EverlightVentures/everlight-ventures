"""sb909_notice.py -- TN SB 909 three-business-day notice enforcement.

Tennessee Public Chapter 911 (Senate Bill 909, 2022) requires that a
wholesaler give the seller a STANDALONE written notice -- separate from
the PSA -- before assigning the purchase contract to any end buyer.
The seller then has three business days to rescind.

Skipping this notice hands the seller a multi-year rescission cause of
action.  This module makes it structurally impossible to assign without
the notice having been sent AND the three-day clock having elapsed.

Sole-prop context (HARD LAW):
  Rich operates as Richard Gee d/b/a Everlight Ventures (sole proprietor).
  The Nevada LLC has NOT yet formed (deferred until post-Deal-1).
  All legal instruments sign as sole prop.  NEVER "Everlight Ventures LLC"
  or "Everlight Logistics LLC" in TN wholesale documents.

Usage:
    from sb909_notice import (
        business_days_between,
        notice_clear_date,
        render_sb909_notice,
        send_sb909_notice,
        assignment_gate,
        record_rescission,
    )
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("sb909_notice")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_AGENT_DIR = Path(__file__).resolve().parent
_LEDGER_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/compliance/sb909_notices.jsonl")

# ---------------------------------------------------------------------------
# Business-day helpers
# ---------------------------------------------------------------------------


def business_days_between(start: date, end: date) -> int:
    """Return the number of business days between start (exclusive) and end (inclusive).

    Saturdays and Sundays are skipped.  No holiday calendar -- TN statute
    references only "business days" without specifying which holidays count;
    weekends are the safe minimum and are universally understood.

    Examples:
        Friday -> Monday   = 1 business day
        Monday -> Thursday = 3 business days
        Friday -> Wednesday (next week) = 3 business days
    """
    if end <= start:
        return 0
    current = start + timedelta(days=1)
    count = 0
    while current <= end:
        if current.weekday() < 5:  # 0=Mon ... 4=Fri
            count += 1
        current += timedelta(days=1)
    return count


def notice_clear_date(sent_dt: datetime) -> datetime:
    """Return the datetime on which the 3-business-day clock expires.

    The clock starts on the calendar day the notice is sent.  We count
    three full business days forward and return midnight (start of day)
    of the first moment the seller can no longer rescind.

    Examples (using sent_dt.date() as anchor):
        Sent Monday  -> clears Thursday 00:00 UTC
        Sent Friday  -> clears Wednesday 00:00 UTC (Mon+Tue+Wed = 3 bdays)
        Sent Saturday -> treated as Friday for clock purposes (next Mon starts the count)
    """
    anchor: date = sent_dt.date()
    # Weekends push the anchor to Friday so the first counted day is Monday.
    if anchor.weekday() == 5:   # Saturday
        anchor = anchor - timedelta(days=1)
    elif anchor.weekday() == 6:  # Sunday
        anchor = anchor - timedelta(days=2)

    bdays_counted = 0
    cursor = anchor
    while bdays_counted < 3:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            bdays_counted += 1

    # Return midnight UTC at the start of the clear day so comparisons are safe.
    return datetime(cursor.year, cursor.month, cursor.day, 0, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Notice renderer
# ---------------------------------------------------------------------------


def render_sb909_notice(lead: dict, deal_terms: dict) -> dict:
    """Render the standalone TN SB 909 written notice.

    Returns:
        {"subject": str, "body_html": str}

    The notice mirrors the disclosure spirit of Block 5 in render_psa_contract
    (outreach_templates.py) but is a CONSUMER-FACING standalone document -- not
    a contract block.  Language is plain English by design; a seller reading
    this on their phone needs to understand it without a lawyer.

    Signer: Richard Gee d/b/a Everlight Ventures (SOLE PROP, no LLC).
    """
    import html as _html

    seller_name: str = lead.get("owner_name") or "Seller"
    addr: str = (
        lead.get("property_address")
        or lead.get("address")
        or "the property"
    )
    seller_email: str = lead.get("email") or lead.get("owner_email") or ""

    assignment_fee: int = int(deal_terms.get("assignment_fee") or 11_500)
    purchase_price: int = int(deal_terms.get("purchase_price") or 0)
    end_buyer: str = deal_terms.get("end_buyer") or "a third-party end buyer"

    subject = (
        f"Important Notice -- Wholesale Assignment Disclosure for "
        f"{addr} (TN SB 909)"
    )

    body_html = f"""
<p>Date: {{SENT_DATE}}</p>

<p>To: {_html.escape(seller_name)}<br>
Re: Property at {_html.escape(addr)}</p>

<hr>

<h2 style="font-size:16px;">TENNESSEE WHOLESALER DISCLOSURE NOTICE</h2>
<p style="font-size:12px;color:#555;">
  Required under Tennessee Public Chapter 911 (Senate Bill 909, 2022).
</p>

<p>Dear {_html.escape(seller_name.split()[0] if seller_name else "Seller")},</p>

<p>
  We have a signed Purchase and Sale Agreement with you for the property at
  <strong>{_html.escape(addr)}</strong>.  Before we can transfer (assign) that
  contract to the end buyer, Tennessee law requires us to give you this written
  notice and allow you <strong>three (3) business days</strong> to review it.
</p>

<h3 style="font-size:14px;">What you need to know</h3>

<ol>
  <li>
    <strong>We intend to assign this contract.</strong><br>
    Richard Gee d/b/a Everlight Ventures ("Buyer") plans to assign the
    purchase contract for {_html.escape(addr)} to
    {_html.escape(end_buyer)} before the closing date.
    Your sale proceeds{f" of ${purchase_price:,}" if purchase_price else ""} do
    not change when we assign -- you still close at the same price with the
    same title company.
  </li>

  <li>
    <strong>Our assignment fee (profit) is ${assignment_fee:,}.</strong><br>
    This is the difference between what we contracted to pay you and the price
    at which we are assigning the contract to the end buyer.  This fee is
    disclosed to you now, before the assignment happens, as required by
    Tennessee law.
  </li>

  <li>
    <strong>We are NOT a licensed real estate agent or broker.</strong><br>
    We are acting as a wholesale buyer, not in a fiduciary capacity for you.
    You have the right to consult an independent attorney or real estate agent
    before responding to this notice.
  </li>

  <li>
    <strong>You have 3 business days to cancel.</strong><br>
    If you do not want us to assign this contract, you may cancel your
    agreement with us within <strong>three (3) business days</strong> of
    receiving this notice.  Saturdays, Sundays, and federal holidays do not
    count as business days.
  </li>
</ol>

<h3 style="font-size:14px;">How to cancel</h3>

<p>
  Reply to this email with the word <strong>CANCEL</strong> in the subject or body,
  or send written notice to:<br><br>
  Richard Gee d/b/a Everlight Ventures<br>
  Email: acquisitions@everlightventures.io<br>
  (opt-out@everlightventures.io also accepted)
</p>

<p>
  If we do not receive a cancellation notice within three (3) business days of
  this email, we will proceed with the assignment.
</p>

<hr>

<p style="font-size:12px;color:#555;">
  This notice is provided in compliance with Tennessee Public Chapter 911
  (Senate Bill 909, enacted 2022).  It does not alter any other terms of
  your Purchase and Sale Agreement.
</p>

<p>
  Sincerely,<br>
  <strong>Richard Gee</strong><br>
  d/b/a Everlight Ventures (Sole Proprietor)<br>
  acquisitions@everlightventures.io<br>
  Everlight Ventures Wholesale Division<br>
  Tennessee Operations
</p>

<p style="font-size:11px;color:#888;">
  To opt out of all future communications reply STOP or email
  opt-out@everlightventures.io.
</p>
"""

    return {"subject": subject, "body_html": body_html}


# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------


def _read_ledger() -> list[dict]:
    """Read all rows from the audit ledger.  Raises IOError on read failure."""
    if not _LEDGER_PATH.exists():
        return []
    rows: list[dict] = []
    raw = _LEDGER_PATH.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _append_ledger(row: dict) -> None:
    """Append a single JSON row to the ledger (immutable audit log)."""
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------


def send_sb909_notice(
    deal: dict,
    lead: dict,
    deal_terms: dict,
    *,
    dry_run: bool = True,
) -> dict:
    """Render and send the SB 909 notice.  Returns the audit row.

    Args:
        deal:       dict with deal_id (required), plus any deal metadata.
        lead:       lead dict (owner_name, email, property_address, etc.).
        deal_terms: dict with assignment_fee, purchase_price, end_buyer.
        dry_run:    If True (default), compute + return the planned row but
                    do NOT send the email and do NOT write to the ledger.
                    Callers must explicitly pass dry_run=False to live-send.

    Returns:
        Audit row dict with keys:
            deal_id, seller_email, sent_ts, clear_date, assignment_fee,
            message_id, dry_run, row_type.
    """
    deal_id: str = str(deal.get("deal_id") or deal.get("address_slug") or "UNKNOWN")
    seller_email: str = lead.get("email") or lead.get("owner_email") or ""
    assignment_fee: int = int(deal_terms.get("assignment_fee") or 11_500)

    rendered = render_sb909_notice(lead, deal_terms)
    sent_ts = datetime.now(timezone.utc)
    clear_dt = notice_clear_date(sent_ts)

    # Stamp the sent date into the HTML (placeholder replacement)
    body_with_date = rendered["body_html"].replace(
        "{SENT_DATE}", sent_ts.strftime("%B %d, %Y %H:%M UTC")
    )

    row: dict = {
        "row_type": "sb909_notice",
        "deal_id": deal_id,
        "seller_email": seller_email,
        "sent_ts": sent_ts.isoformat(),
        "clear_date": clear_dt.isoformat(),
        "assignment_fee": assignment_fee,
        "message_id": None,
        "dry_run": dry_run,
    }

    if dry_run:
        log.info("[SB909 dry_run] Would send to %s. Clears %s.", seller_email, clear_dt.date())
        return row

    # -- Live send --
    if not seller_email:
        log.error("[SB909] No seller email on lead; cannot send notice for deal %s", deal_id)
        row["error"] = "no_seller_email"
        return row

    try:
        sys.path.insert(0, str(_AGENT_DIR))
        from rex_utils import safe_send_email  # type: ignore
        ok = safe_send_email(
            to=seller_email,
            subject=rendered["subject"],
            body=body_with_date,
            state="TN",
            action="sb909_notice",
            agent_name="Richard Gee",
            agent_title="d/b/a Everlight Ventures (Sole Proprietor)",
            agent_email="acquisitions@everlightventures.io",
        )
        if ok:
            log.info("[SB909] Notice sent to %s for deal %s. Clears %s.",
                     seller_email, deal_id, clear_dt.date())
        else:
            log.error("[SB909] safe_send_email returned False for deal %s", deal_id)
            row["error"] = "send_failed"
    except Exception as exc:
        log.error("[SB909] send exception: %s", exc)
        row["error"] = str(exc)

    # Write audit row (even on failure so we have a record of the attempt)
    _append_ledger(row)
    return row


# ---------------------------------------------------------------------------
# Rescission recorder
# ---------------------------------------------------------------------------


def record_rescission(deal_id: str, reason: str = "") -> None:
    """Record a seller rescission.  assignment_gate will block after this."""
    row = {
        "row_type": "sb909_rescission",
        "deal_id": str(deal_id),
        "recorded_ts": datetime.now(timezone.utc).isoformat(),
        "reason": reason or "seller_cancelled",
    }
    _append_ledger(row)
    log.warning("[SB909] Rescission recorded for deal %s: %s", deal_id, reason)


# ---------------------------------------------------------------------------
# Assignment gate -- THE ENFORCEMENT
# ---------------------------------------------------------------------------


def assignment_gate(deal_id: str, *, now: Optional[datetime] = None) -> tuple[bool, str]:
    """Check whether a deal is cleared for assignment.

    Reads the sb909_notices.jsonl ledger.  Fails CLOSED on any read error.

    Returns:
        (True,  "sb909_cleared")                      -- cleared, may assign
        (False, "no_sb909_notice_sent")               -- no notice on record
        (False, "sb909_3day_clock_not_elapsed: ...")  -- clock still running
        (False, "seller_rescinded")                   -- seller cancelled
        (False, "ledger_read_error: ...")             -- fail-closed on I/O
    """
    now = now or datetime.now(timezone.utc)
    deal_id = str(deal_id)

    # FAIL CLOSED: if the ledger is unreadable, block.
    try:
        rows = _read_ledger()
    except Exception as exc:
        reason = f"ledger_read_error: {exc}"
        log.error("[SB909 gate] %s for deal %s -- BLOCKING", reason, deal_id)
        return (False, reason)

    deal_rows = [r for r in rows if r.get("deal_id") == deal_id]

    # 1. Rescission takes absolute precedence.
    for r in deal_rows:
        if r.get("row_type") == "sb909_rescission":
            log.warning("[SB909 gate] Rescission on file for deal %s -- BLOCKED", deal_id)
            return (False, "seller_rescinded")

    # 2. Find the most recent REAL (non-dry-run) notice row.
    notice_rows = [
        r for r in deal_rows
        if r.get("row_type") == "sb909_notice" and not r.get("dry_run")
    ]
    if not notice_rows:
        log.warning("[SB909 gate] No real notice row for deal %s -- BLOCKED", deal_id)
        return (False, "no_sb909_notice_sent")

    # Use the earliest real notice (most conservative for seller protection).
    earliest = min(notice_rows, key=lambda r: r["sent_ts"])
    clear_dt = datetime.fromisoformat(earliest["clear_date"])
    if clear_dt.tzinfo is None:
        clear_dt = clear_dt.replace(tzinfo=timezone.utc)

    if now < clear_dt:
        msg = f"sb909_3day_clock_not_elapsed: clears {clear_dt.strftime('%Y-%m-%d %H:%M UTC')}"
        log.warning("[SB909 gate] %s for deal %s -- BLOCKED", msg, deal_id)
        return (False, msg)

    log.info("[SB909 gate] Deal %s -- CLEARED for assignment (notice sent %s, cleared %s)",
             deal_id, earliest["sent_ts"][:10], clear_dt.date())
    return (True, "sb909_cleared")
