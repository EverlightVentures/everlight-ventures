#!/usr/bin/env python3
"""
$BCARDD X (Twitter) autopilot -- hands-off content drip + compliance gate.

Posts queued tweets to X on a schedule so Rich does not have to touch it.
Designed to run on e5-mother via cron (the phone proot cannot host long-lived
processes -- PRoot kill-on-exit trap). NO secrets live in this file: the X API
creds are read from the environment (sourced from Proton Pass / a .env on e5).

Env (OAuth 1.0a user context -- required to POST tweets):
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
Optional:
  BCARDI_CA        contract address; substituted for the <CA> token once live
  BCARDI_PUMP_URL  pump.fun coin link; substituted for <PUMP_LINK>
  ANTHROPIC_API_KEY enables --refill (auto-generate fresh on-brand tweets)
  X_AUTOPILOT_DRY  if set, never posts (also auto-on when creds are missing)

Usage:
  python3 x_autopilot.py --once        # post the next due item (cron target)
  python3 x_autopilot.py --dry-run     # show what WOULD post, post nothing
  python3 x_autopilot.py --status      # queue summary
  python3 x_autopilot.py --refill 8    # AI-generate 8 fresh sustain tweets

Cron (on e5-mother, 3 drips/day at 9a/2p/7p PT):
  0 16,21,2 * * *  cd <this dir> && /usr/bin/python3 x_autopilot.py --once >> x_autopilot.cron.log 2>&1
"""
import os
import re
import sys
import json
import datetime
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "x_content_queue.json")
LOG = os.path.join(HERE, "x_autopilot.log.jsonl")

# Legal + brand guardrail. A post containing any of these never goes out.
# Mirrors the COPY_PACK "NEVER SAY" list. hype the dog, not the money.
BANNED = [
    "guaranteed", "guarantee", "returns", "profit", "roi", "get rich",
    "will moon", "1000x guaranteed", "financial freedom", "passive income",
    "can't lose", "cannot lose", "risk free", "risk-free",
    # trademark distance (renamed 2026-06-03) + gambling decouple (2026-06-08 memo):
    # the coin is $BCARDD, never "Bacardi"; no casino/gambling framing, ever.
    "bacardi", "blackjack", "casino", "jackpot", "gamble", "gambling",
    "betting", "wager", "sweepstakes",
]
MAX_LEN = 280


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def load_queue():
    if not os.path.exists(QUEUE):
        return []
    with open(QUEUE) as f:
        return json.load(f)


def save_queue(items):
    tmp = QUEUE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(items, f, indent=2)
    os.replace(tmp, QUEUE)


def log_event(rec):
    rec["ts"] = now().isoformat()
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def compliance_check(text):
    low = text.lower()
    for w in BANNED:
        if w in low:
            return False, "banned phrase: " + w
    if len(text) > MAX_LEN:
        return False, "over %d chars (%d)" % (MAX_LEN, len(text))
    return True, "ok"


CASHTAG_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]*)")


def sanitize_cashtags(text):
    """X rejects posts with >1 cashtag (403). Keep the first $TAG, demote the rest to #TAG."""
    seen = [0]

    def repl(m):
        seen[0] += 1
        return m.group(0) if seen[0] == 1 else "#" + m.group(1)

    return CASHTAG_RE.sub(repl, text)


def render(text):
    """Fill launch placeholders from env. Returns None if a required token is unset."""
    ca = os.environ.get("BCARDI_CA", "")
    pump = os.environ.get("BCARDI_PUMP_URL", "")
    if "<CA>" in text:
        if not ca:
            return None  # launch tweet not ready -- skip until coin exists
        text = text.replace("<CA>", ca)
    if "<PUMP_LINK>" in text:
        if not pump:
            return None
        text = text.replace("<PUMP_LINK>", pump)
    return text


def have_creds():
    return all(os.environ.get(k) for k in
               ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))


def post_to_x(text):
    """Post via tweepy (OAuth1 user context). Returns (ok, info)."""
    dry = os.environ.get("X_AUTOPILOT_DRY") or not have_creds()
    if dry:
        print("[DRY] would post (%d chars):\n  %s" % (len(text), text))
        return True, "dry-run"
    try:
        import tweepy  # pip install tweepy   (on e5, not the phone)
    except ImportError:
        return False, "tweepy not installed (pip install tweepy on e5)"
    try:
        client = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"],
        )
        resp = client.create_tweet(text=text)
        return True, "tweet_id=" + str(resp.data.get("id"))
    except Exception as e:  # one retry, then give up loudly
        try:
            resp = client.create_tweet(text=text)
            return True, "tweet_id=" + str(resp.data.get("id")) + " (retry)"
        except Exception as e2:
            return False, "post failed: %s / %s" % (e, e2)


def pick_next(items):
    """Next pending item that is due now (post_at null = drip immediately)."""
    n = now()
    for it in items:
        if it.get("status") != "pending":
            continue
        pa = it.get("post_at")
        if pa:
            try:
                due = datetime.datetime.fromisoformat(pa)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=datetime.timezone.utc)
                if n < due:
                    continue
            except ValueError:
                pass
        return it
    return None


def cmd_once():
    items = load_queue()
    it = pick_next(items)
    if not it:
        print("nothing due to post.")
        return 0
    text = render(it["text"])
    if text is None:
        # launch placeholder unfilled -- skip this one, mark as held, try the next
        it["status"] = "held_needs_ca"
        save_queue(items)
        log_event({"event": "held", "id": it["id"], "reason": "BCARDI_CA/PUMP unset"})
        print("held item %s (needs contract address); run again for next." % it["id"])
        return 0
    text = sanitize_cashtags(text)
    ok, reason = compliance_check(text)
    if not ok:
        it["status"] = "blocked"
        it["block_reason"] = reason
        save_queue(items)
        log_event({"event": "blocked", "id": it["id"], "reason": reason})
        print("BLOCKED %s: %s" % (it["id"], reason))
        return 1
    ok, info = post_to_x(text)
    if info == "dry-run":
        return 0  # dry run never consumes the queue or logs
    it["status"] = "posted" if ok else "error"
    it["result"] = info
    it["posted_at"] = now().isoformat()
    save_queue(items)
    log_event({"event": "post", "id": it["id"], "ok": ok, "info": info, "text": text})
    print(("POSTED " if ok else "ERROR ") + it["id"] + ": " + info)
    return 0 if ok else 1


def cmd_status():
    items = load_queue()
    from collections import Counter
    c = Counter(it.get("status", "pending") for it in items)
    print("queue: %d items" % len(items))
    for k, v in c.items():
        print("  %-16s %d" % (k, v))
    nxt = pick_next(items)
    print("next up:", (nxt["id"] + " -- " + nxt["text"][:60]) if nxt else "none due")
    print("creds present:", have_creds(), "| dry:", bool(os.environ.get("X_AUTOPILOT_DRY") or not have_creds()))


def cmd_refill(n):
    """Auto-generate n fresh on-brand sustain tweets via Anthropic, gate them, queue them."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY not set -- cannot refill.")
        return 1
    prompt = (
        "Write %d short tweets for $BCARDD, a Solana DOG meme coin about a real dog named "
        "Bacardi who deals blackjack. Voice: confident, funny, street-smart, dog + casino energy. "
        "Hard rules: under 270 characters each; NEVER promise profit/returns/gains/moon; no "
        "financial advice; no corporate buzzwords. Return ONLY a JSON array of strings." % n
    )
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=40))
        text = resp["content"][0]["text"]
        start, end = text.find("["), text.rfind("]")
        tweets = json.loads(text[start:end + 1])
    except Exception as e:
        print("refill failed:", e)
        return 1
    items = load_queue()
    base = len([i for i in items if i["id"].startswith("auto-")])
    added = 0
    for i, t in enumerate(tweets):
        ok, reason = compliance_check(t)
        if not ok:
            log_event({"event": "refill_reject", "reason": reason, "text": t})
            continue
        items.append({"id": "auto-%03d" % (base + i + 1), "phase": "sustain",
                      "text": t, "post_at": None, "status": "pending"})
        added += 1
    save_queue(items)
    print("refill: added %d / %d (rest failed compliance)." % (added, len(tweets)))
    return 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--once":
        return cmd_once()
    if args[0] == "--dry-run":
        os.environ["X_AUTOPILOT_DRY"] = "1"
        return cmd_once()
    if args[0] == "--status":
        cmd_status()
        return 0
    if args[0] == "--refill":
        return cmd_refill(int(args[1]) if len(args) > 1 else 8)
    print("unknown arg:", args[0])
    return 1


if __name__ == "__main__":
    sys.exit(main())
