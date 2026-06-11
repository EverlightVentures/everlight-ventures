#!/usr/bin/env python3
"""
$BCARDD Telegram autopilot -- hands-off channel drip.

Mirrors x_autopilot: same queue (x_content_queue.json), same compliance gate,
same <CA>/<PUMP_LINK> placeholder rendering. Keeps its OWN sent-ledger
(tg_sent.json) and never mutates queue item status -- x_autopilot stays the
owner of the queue lifecycle.

Env:
  TELEGRAM_BOT_TOKEN   BotFather token (required)
  TELEGRAM_CHAT_ID     @channelusername or numeric id (required; bot must be admin)
  BCARDI_CA / BCARDI_PUMP_URL  same placeholders as x_autopilot

Usage:
  python3 telegram_autopilot.py --once     # send the next unsent item (cron target)
  python3 telegram_autopilot.py --status   # ledger summary

Cron (e5, offset from the X slots):  0 17,22,3 * * *
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import x_autopilot as xa  # compliance_check, render, load_queue

SENT = HERE / "tg_sent.json"
TG_QUEUE = HERE / "tg_content_queue.json"


def load_items():
    """TG-native queue when present; falls back to the shared X queue."""
    if TG_QUEUE.exists():
        return json.loads(TG_QUEUE.read_text())
    return xa.load_queue()


def load_sent():
    return set(json.loads(SENT.read_text())) if SENT.exists() else set()


def save_sent(ids):
    SENT.write_text(json.dumps(sorted(ids)))


def post(text, token, chat):
    import urllib.request
    body = json.dumps({"chat_id": chat, "text": text,
                       "disable_web_page_preview": False}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", body,
        {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=20))
    return r.get("ok"), r


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    sent = load_sent()
    items = load_items()

    if "--status" in sys.argv:
        pending = [i for i in items if i["id"] not in sent
                   and i.get("status") in ("pending", "posted")]
        print(f"tg sent: {len(sent)} | sendable: {len(pending)} | "
              f"token: {'set' if token else 'MISSING'} | chat: {chat or 'MISSING'}")
        return 0

    if not token or not chat:
        print("idle: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured")
        return 0

    for it in items:
        if it["id"] in sent or it.get("status") not in ("pending", "posted"):
            continue
        text = xa.render(it["text"])
        if text is None:
            continue  # placeholder unfilled
        # banned-word gate shared with X; length cap is Telegram's own (4096)
        low = text.lower()
        hits = [b for b in xa.BANNED if b in low]
        ok, reason = (False, "banned: " + ",".join(hits)) if hits else \
                     (False, f"over 4096 chars ({len(text)})") if len(text) > 4096 else (True, "")
        if not ok:
            print(f"SKIP {it['id']}: {reason}")
            sent.add(it["id"])  # never retry a blocked item
            save_sent(sent)
            continue
        ok, resp = post(text, token, chat)
        if ok:
            sent.add(it["id"])
            save_sent(sent)
            print(f"SENT {it['id']}")
        else:
            print(f"ERROR {it['id']}: {resp}")
        return 0 if ok else 1
    print("nothing to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
