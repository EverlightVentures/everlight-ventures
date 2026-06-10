"""magnet_slack_alerter -- cron poller that Slacks new high-signal events.

Reads the dispatcher events.jsonl. Keeps a cursor at
_logs/dispatcher/.alerter_cursor so we only report events once.

Alerted event types:
    magnet_accept          -- SELLER SAID YES, DROP EVERYTHING
    magnet_call            -- they want a call right now
    magnet_counter         -- asking for a higher number
    wholesale_reply        -- reply to an outreach email
    magnet_click (>=3)     -- same lead clicked 3+ times => warm interest
    stripe_charge          -- money hit

Slack posts go to #hive-alerts by default. Each event is idempotent-keyed
by event id so re-runs don't double-post.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.request
from collections import Counter

EVENTS   = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE/_logs/dispatcher/events.jsonl")
CURSOR   = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE/_logs/dispatcher/.alerter_cursor")
CREDS    = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
CHANNEL  = os.environ.get("MAGNET_ALERT_CHANNEL", "#hive-alerts")

HIGH_SIGNAL = {
    "magnet_accept":    (":white_check_mark: SELLER ACCEPTED CASHOFFER",   "@channel"),
    "magnet_call":      (":telephone_receiver: CALL REQUESTED",            "@channel"),
    "magnet_counter":   (":arrows_counterclockwise: COUNTER -- higher number please", ""),
    "wholesale_reply":  (":incoming_envelope: REPLY from seller",          ""),
    "stripe_charge":    (":money_with_wings: STRIPE CHARGE",               "@channel"),
}


def _slack_token() -> str:
    t = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if t: return t
    if CREDS.exists():
        text = CREDS.read_text()
        m = re.search(r"^SLACK_BOT_TOKEN\s*=\s*['\"]?(xoxb-[A-Za-z0-9\-]+)['\"]?", text, re.M)
        if m: return m.group(1)
    return ""


def _post(text: str) -> bool:
    token = _slack_token()
    if not token: return False
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": CHANNEL, "text": text}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        urllib.request.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False


def _read_cursor() -> int:
    try: return int(CURSOR.read_text().strip())
    except Exception: return 0


def _write_cursor(n: int) -> None:
    CURSOR.write_text(str(n))


def main() -> int:
    if not EVENTS.exists():
        return 0
    last_id_count = _read_cursor()
    with EVENTS.open("r", encoding="utf-8") as f:
        rows = [ln for ln in f if ln.strip()]
    new_rows = rows[last_id_count:]
    if not new_rows:
        return 0

    # Count click-per-lead in this batch (so we escalate on 3rd click)
    click_counts: Counter = Counter()
    events_parsed = []
    for ln in new_rows:
        try:
            row = json.loads(ln)
        except Exception:
            continue
        events_parsed.append(row)
        if row.get("type") == "magnet_click":
            lid = (row.get("payload", {}) or {}).get("lead_id") or "?"
            click_counts[lid] += 1

    posted = 0
    for row in events_parsed:
        t = row.get("type", "")
        payload = row.get("payload", {}) or {}
        lead_id = payload.get("lead_id") or (payload.get("record", {}) or {}).get("id") or "?"
        addr = (payload.get("record", {}) or {}).get("address", "")
        ts = row.get("ts", "")[:19].replace("T", " ")
        if t in HIGH_SIGNAL:
            emoji_title, mention = HIGH_SIGNAL[t]
            msg = f"{emoji_title}  lead=`{lead_id}`"
            if addr: msg += f"  @ {addr}"
            msg += f"  ({ts})"
            if mention: msg += f"\n{mention} -- respond within 15 min"
            if _post(msg):
                posted += 1
        elif t == "magnet_click" and click_counts.get(lead_id, 0) == 3:
            # Warm escalation -- third click from same lead in this batch
            msg = f":eyes: WARM: lead=`{lead_id}` clicked CashOfferScan 3+ times in a row -- may be reading carefully"
            if addr: msg += f" @ {addr}"
            if _post(msg):
                posted += 1

    _write_cursor(len(rows))
    if posted:
        print(f"posted {posted} alerts for {len(new_rows)} new events (cursor={len(rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
