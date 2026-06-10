"""deal_thread_tracker -- mirror pipeline status changes into #wholesale-deals threads.

For each lead, we track the last-seen status in a cursor file. Whenever a
lead transitions (new -> contacted -> negotiating -> verbal_agreement ->
contract_sent -> signed -> buyer_blast -> contract_assigned -> title_hold ->
closed -> funds_received), we:

  1. If no thread exists for that lead, open a new top-level post in
     #wholesale-deals and save the thread_ts.
  2. If a thread exists, post a reply in that thread.

The result: one Slack thread per lead, every status change shows up as a
threaded reply. You get the full history at a glance.

Runs via cron (every 5 min). Idempotent -- unchanged leads produce no Slack
noise.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import sys
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="[deal-track %(asctime)s] %(message)s")
log = logging.getLogger("deal_thread_tracker")

ROOT = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
CURSOR   = ROOT / "_logs" / "deal_thread_cursor.json"
CREDS    = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

CHANNEL  = os.environ.get("DEAL_THREAD_CHANNEL", "C0ANLLV8JAC")   # #wholesale-deals

# Status transitions that warrant a Slack post. Anything not in this map is noise.
STATUS_LINES = {
    "contacted":          (":envelope:",         "First outreach sent. Rex is live on this lead."),
    "negotiating":        (":speech_balloon:",    "Seller replied. Rex is negotiating -- check the thread."),
    "verbal_agreement":   (":handshake:",         "Seller said yes to an offer. Rex is drafting the contract."),
    "contract_sent":      (":page_facing_up:",    "Contract PDF sent to seller for signature."),
    "signed":             (":white_check_mark:",  "Contract signed by seller. Ready to blast to buyers."),
    "buyer_blast":        (":loudspeaker:",       "Disposition deal-sheet blasted to cash buyers."),
    "contract_assigned":  (":key:",               "Buyer committed. Assignment fee locked in."),
    "title_hold":         (":classical_building:","Title company has the contract. Closing in progress."),
    "closed":             (":moneybag:",          "Closed. Assignment fee wired to Everlight."),
    "funds_received":     (":tada:",              "FUNDS LANDED. Deposit confirmed."),
    "dead":               (":soon:",              "Lead marked dead. Recycled to monthly lookback."),
}


def _slack_token() -> str:
    t = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if t: return t
    if CREDS.exists():
        m = re.search(r"^SLACK_BOT_TOKEN\s*=\s*['\"]?(xoxb-[A-Za-z0-9\-]+)['\"]?",
                      CREDS.read_text(), re.M)
        if m: return m.group(1)
    return ""


def _slack_post(text: str, thread_ts: str | None = None) -> str | None:
    """Returns the ts of the posted message (needed for threading)."""
    token = _slack_token()
    if not token: return None
    body = {"channel": CHANNEL, "text": text, "mrkdwn": True}
    if thread_ts:
        body["thread_ts"] = thread_ts
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=8).read()
        resp = json.loads(r)
        if resp.get("ok"):
            return resp.get("ts")
        log.warning("slack err: %s", resp.get("error"))
    except Exception as e:
        log.warning("slack post failed: %s", e)
    return None


def _load_cursor() -> dict:
    try:
        return json.loads(CURSOR.read_text())
    except Exception:
        return {"leads": {}}  # {lead_id: {"status": ..., "thread_ts": ...}}


def _save_cursor(c: dict) -> None:
    CURSOR.write_text(json.dumps(c, indent=2))


def _lead_line(lead: dict) -> str:
    addr = lead.get("address", "?")
    city = lead.get("city", "")
    state = (lead.get("state") or "").upper()
    owner = (lead.get("owner_name") or "Unknown").title()
    arv = lead.get("estimated_arv") or 0
    lt = lead.get("lead_type", "")
    extra = f" *{lt}*" if lt and lt != "generic" else ""
    return f"*{owner}*  @ `{addr}` ({city}, {state})  ARV: ${arv:,}{extra}"


def _open_thread_for(lead: dict) -> str | None:
    """New top-level post to #wholesale-deals for this lead."""
    head = _lead_line(lead)
    status = lead.get("status", "new")
    emoji, line = STATUS_LINES.get(status, (":bell:", f"Status: {status}"))
    msg = f":file_folder: *Deal opened*\n{head}\n\n{emoji} {line}\n_lead_id: `{lead.get('id','')}`_"
    return _slack_post(msg)


def _post_transition(lead: dict, thread_ts: str, new_status: str) -> None:
    emoji, line = STATUS_LINES.get(new_status, (":bell:", f"Status: {new_status}"))
    extra_context = ""
    if new_status == "verbal_agreement":
        extra_context = f"\nARV: ${lead.get('estimated_arv',0):,} -- ready-to-sign offer"
    elif new_status == "contract_sent":
        extra_context = f"\nOffer: ${lead.get('offer_amount','') or '?'}. 14-day inspection period included."
    elif new_status == "signed":
        extra_context = "\n:warning: Your turn -- approve the buyer-blast draft in this thread."
    elif new_status == "title_hold":
        extra_context = "\n:arrow_right: Title company will call you to verify wire. Pick up when they call."
    elif new_status == "funds_received":
        extra_context = "\n:moneybag: You can now mark the deal won in the dashboard."
    _slack_post(f"{emoji} *{new_status}* -- {line}{extra_context}", thread_ts=thread_ts)


def scan() -> dict:
    if not LEADS_DB.exists():
        return {"processed": 0, "new_threads": 0, "transitions": 0}
    leads = json.loads(LEADS_DB.read_text())
    cursor = _load_cursor()
    known = cursor.setdefault("leads", {})

    new_threads = 0
    transitions = 0
    now = datetime.now(timezone.utc).isoformat()

    for lead in leads:
        lid = str(lead.get("id") or lead.get("lead_id") or "")
        if not lid:
            continue
        status = lead.get("status", "new")
        # We only track leads that have moved beyond "new"
        if status == "new":
            continue

        entry = known.get(lid)
        if not entry:
            # First time we see a non-new status. Open a thread.
            thread_ts = _open_thread_for(lead)
            if thread_ts:
                known[lid] = {"status": status, "thread_ts": thread_ts, "last_update": now}
                new_threads += 1
                # Also post the current status line (since _open_thread_for lists it only briefly)
                if status in STATUS_LINES:
                    _post_transition(lead, thread_ts, status)
            continue

        # Known lead -- transition?
        prev = entry.get("status")
        if prev == status:
            continue
        # Transition
        entry["status"] = status
        entry["last_update"] = now
        thread_ts = entry.get("thread_ts")
        if thread_ts:
            _post_transition(lead, thread_ts, status)
            transitions += 1

    cursor["leads"] = known
    _save_cursor(cursor)
    return {"processed": len(leads), "new_threads": new_threads, "transitions": transitions}


def main():
    s = scan()
    print(json.dumps(s))


if __name__ == "__main__":
    main()
