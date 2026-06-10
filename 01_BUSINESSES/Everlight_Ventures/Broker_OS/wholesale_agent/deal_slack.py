"""deal_slack -- shared helper: every outreach action posts to the lead's
Slack thread in #wholesale-deals.

One thread per lead. First touch opens the thread. Subsequent emails, SMS,
replies, clicks, status transitions reply inside the same thread. Anyone
watching the channel sees exactly what went to whom, when, and by which agent.

Usage from any sender:
    from deal_slack import post_touch
    post_touch(lead=lead, agent="Piper", channel="email",
               subject=subj, body=body, outcome="sent")

Cursor is shared with deal_thread_tracker.py -- single source of truth for
thread_ts per lead_id.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import threading
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger("deal_slack")

ROOT = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE")
CURSOR = ROOT / "_logs" / "deal_thread_cursor.json"
CREDS  = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"
CHANNEL = os.environ.get("DEAL_THREAD_CHANNEL", "C0ANLLV8JAC")  # #wholesale-deals

_CURSOR_LOCK = threading.Lock()


def _slack_token() -> str:
    t = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if t:
        return t
    if CREDS.exists():
        m = re.search(r"^SLACK_BOT_TOKEN\s*=\s*['\"]?(xoxb-[A-Za-z0-9\-]+)['\"]?",
                      CREDS.read_text(), re.M)
        if m:
            return m.group(1)
    return ""


def _post(body: dict) -> dict | None:
    token = _slack_token()
    if not token:
        return None
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=8).read()
        resp = json.loads(r)
        return resp if resp.get("ok") else None
    except Exception as e:
        log.warning("slack post err: %s", e)
        return None


def _load_cursor() -> dict:
    try:
        return json.loads(CURSOR.read_text())
    except Exception:
        return {"leads": {}}


def _save_cursor(c: dict) -> None:
    CURSOR.write_text(json.dumps(c, indent=2))


def _get_or_open_thread(lead: dict) -> str | None:
    lid = str(lead.get("id") or lead.get("lead_id") or "")
    if not lid:
        return None
    with _CURSOR_LOCK:
        cursor = _load_cursor()
        known = cursor.setdefault("leads", {})
        entry = known.get(lid)
        if entry and entry.get("thread_ts"):
            return entry["thread_ts"]

        # Open thread
        owner = (lead.get("owner_name") or "Unknown").title()
        addr = lead.get("address", "?")
        city = lead.get("city", "")
        state = (lead.get("state") or "").upper()
        arv = lead.get("estimated_arv") or 0
        lt = lead.get("lead_type") or "generic"
        distress = lead.get("detected_distress") or lt
        source = lead.get("source", "")

        head = (
            f":file_folder: *New deal opened* -- `{lid}`\n"
            f"*{owner}* @ `{addr}`\n"
            f":round_pushpin: {city}, {state}   :house:  {lt}   :dollar:  ARV ~${arv:,}\n"
            f":label: {distress}    :inbox_tray: source: {source}"
        )
        resp = _post({"channel": CHANNEL, "text": head, "mrkdwn": True})
        if not resp:
            return None
        thread_ts = resp.get("ts")
        known[lid] = {
            "status": lead.get("status", "new"),
            "thread_ts": thread_ts,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }
        _save_cursor(cursor)
        return thread_ts


def _trim(s: str, n: int = 280) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def post_touch(lead: dict, agent: str, channel: str, *,
               subject: str = "", body: str = "",
               to_address: str = "", outcome: str = "sent",
               magnet_url: str = "") -> bool:
    """Post a per-touch update to the lead's deal thread.

    channel: "email" | "sms" | "call" | "reply" | "click" | "accept" | "counter" | "call_request" | "signed" | "buyer_blast" | "contract_assigned" | "title_hold" | "closed"
    outcome: "sent" | "received" | "declined" | "queued" | "blocked:<reason>"
    """
    thread_ts = _get_or_open_thread(lead)
    if not thread_ts:
        return False

    owner = (lead.get("owner_name") or "Unknown").title()
    to = to_address or lead.get("email") or lead.get("owner_email") or lead.get("phone") or "?"

    emoji = {
        "email": ":envelope:",
        "sms": ":phone:",
        "call": ":telephone_receiver:",
        "reply": ":incoming_envelope:",
        "click": ":eyes:",
        "accept": ":white_check_mark:",
        "counter": ":arrows_counterclockwise:",
        "call_request": ":telephone_receiver:",
        "signed": ":pencil2:",
        "buyer_blast": ":loudspeaker:",
        "contract_assigned": ":key:",
        "title_hold": ":classical_building:",
        "closed": ":moneybag:",
    }.get(channel, ":bell:")

    header = f"{emoji} *{channel}* ({outcome}) by *{agent}*"
    if to and channel in ("email", "sms", "call", "reply"):
        header += f"  ->  `{_trim(to, 60)}`"

    chunks = [header]
    if subject:
        chunks.append(f":small_blue_diamond: *Subject:* {_trim(subject, 120)}")
    if body:
        chunks.append(f"```{_trim(body, 450)}```")
    if magnet_url:
        chunks.append(f":link: <{magnet_url}|CashOfferScan link>")
    msg = "\n".join(chunks)

    resp = _post({"channel": CHANNEL, "text": msg, "mrkdwn": True,
                  "thread_ts": thread_ts})
    return bool(resp)


def post_stage(lead: dict, new_status: str, detail: str = "") -> bool:
    """Post a stage transition into the lead's thread + update cursor status."""
    lid = str(lead.get("id") or lead.get("lead_id") or "")
    thread_ts = _get_or_open_thread(lead)
    if not thread_ts:
        return False

    emoji, line = {
        "negotiating":       (":speech_balloon:",    "Seller replied. Rex negotiating."),
        "verbal_agreement":  (":handshake:",         "Seller said YES. Contract being drafted."),
        "contract_sent":     (":page_facing_up:",    "Contract sent for signatures."),
        "signed":            (":pencil2:",           "Contract signed by both parties."),
        "buyer_blast":       (":loudspeaker:",       "Deal sheet blasted to cash buyers."),
        "contract_assigned": (":key:",               "Buyer committed. Assignment locked in."),
        "title_hold":        (":classical_building:","Title company has the contract."),
        "closed":            (":moneybag:",          "Closed. Wire on its way."),
        "funds_received":    (":tada:",              "FUNDS LANDED."),
        "dead":              (":soon:",              "Lead dead -- recycled for monthly lookback."),
    }.get(new_status, (":bell:", f"Status: {new_status}"))

    msg = f"{emoji} *stage -> {new_status}*  {line}"
    if detail:
        msg += f"\n{detail}"
    resp = _post({"channel": CHANNEL, "text": msg, "mrkdwn": True,
                  "thread_ts": thread_ts})
    if not resp:
        return False

    # Update cursor
    with _CURSOR_LOCK:
        cursor = _load_cursor()
        known = cursor.setdefault("leads", {})
        entry = known.setdefault(lid, {"status": new_status, "thread_ts": thread_ts})
        entry["status"] = new_status
        entry["last_update"] = datetime.now(timezone.utc).isoformat()
        _save_cursor(cursor)
    return True
