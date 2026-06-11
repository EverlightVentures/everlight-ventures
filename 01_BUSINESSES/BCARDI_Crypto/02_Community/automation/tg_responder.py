#!/usr/bin/env python3
"""
$BCARDD Telegram responder -- the bot's brain. Long-polls getUpdates and answers
DMs (and discussion-group messages, when a group is linked) with deterministic,
receipts-backed answers. No LLM calls: keyword FAQ from the canon = $0, no
hallucinations, compliance-safe by construction (no price talk anywhere).

Run as a daemon on e5 (singleton-guarded). Watchdog cron relaunches if dead:
  */10 * * * * cd ~/bcardi/automation && . ./.env && flock -n /tmp/tg_responder.lock -c "nohup python3 tg_responder.py >> tg_responder.log 2>&1" || true
"""
import fcntl
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OFFSET_FILE = HERE / "tg_responder.offset"
LOCK_FILE = "/tmp/tg_responder.pylock"

CA = "6mjokwXx7NNzo5ocvLDFGmbsGAs7rYHZdVJhKYkapump"
ANSWERS = [
    (("ca", "contract", "address", "mint"),
     "Official contract (the ONLY real one):\n\n" + CA +
     "\n\nAlways match the full address. Any other mint with this name or this dog is fake. \U0001F436"),
    (("lock", "rug", "dump", "dev bag", "locked"),
     "Dev bag = LOCKED. 90,000,000 tokens (the founder allocation) sit in a public Streamflow "
     "contract for 6 months -- it physically cannot be dumped on you:\n"
     "https://app.streamflow.finance/contract/solana/mainnet/3d4gwe8w1v5CC3Z34PQfxR229vRZrrTofo1VPMdGRnAY\n\n"
     "Mint + freeze revoked, RugCheck zero flags. Receipts: https://alleykingz.online/bcardd"),
    (("buy", "where", "purchase", "get it", "ape"),
     "The table's at pump.fun:\nhttps://pump.fun/coin/" + CA +
     "\n\nFor fun, not financial advice. Never spend what you can't afford to lose. \U0001F0CF"),
    (("game", "play", "arcade", "alley kingz", "alleykingz"),
     "The only dog coin with a real game you can play right now -- free, no wallet needed:\n"
     "https://alleykingz.online \U0001F3AE"),
    (("spam", "flag", "phantom", "verif", "verified", "warning"),
     "That spam tag is the AUTO-flag every brand-new coin gets -- a robot, not a review. "
     "Verification is in motion. Speed it up in 10 seconds: tap the heart on our Jupiter page:\n"
     "https://jup.ag/tokens/" + CA + "\n\nReal holder hearts are the signal that clears it. \U0001F436"),
    (("chart", "price", "mcap", "market cap"),
     "Live chart: https://www.geckoterminal.com/solana/pools/8YF5XLYohuWRmZt18rPLr18S7jtME5YcL32cyQxNEgCi\n"
     "The dog doesn't talk price. The dog deals. \U0001F0CF"),
    (("who", "what is", "dog", "yung printz", "dogo", "about"),
     "$BCARDD -- The Yung Printz, a real Dogo Argentino. A crowned street prince who runs the alley, "
     "pilots a battle rig, and has his own playable game. Real dog, real game, locked bag. "
     "Doge and Shib were cartoons -- this one's real, and so is yours. In DOGO we trust. \U0001F436\U0001F451"),
    (("gm", "hello", "hi", "start", "sup", "yo"),
     "\U0001F436 You found the back room. Receipts: https://alleykingz.online/bcardd | "
     "Game: https://alleykingz.online | Say 'ca' for the contract, 'lock' for the lock proof."),
]
FALLBACK = ("The dog heard you. \U0001F436 Try: 'ca' (contract) · 'lock' (proof the bag can't dump) · "
            "'buy' · 'game' · 'chart' · 'spam flag'. Everything else: https://alleykingz.online/bcardd")
RATE = {}  # chat_id -> last reply ts

CHANNEL_ID = -1003556473637  # the Back Room channel
REF_FILE = HERE / "referrals.json"


def _load_refs():
    import json as _j
    if REF_FILE.exists():
        return _j.loads(REF_FILE.read_text())
    return {"by_user": {}, "by_link": {}}  # by_user[uid]={link,name,count}; by_link[link]=uid


def _save_refs(d):
    import json as _j
    REF_FILE.write_text(_j.dumps(d))


def get_or_make_invite(token, uid, uname):
    """Create (once) a tracked invite link for this user to the channel."""
    refs = _load_refs()
    u = refs["by_user"].get(str(uid))
    if u and u.get("link"):
        return u["link"], u.get("count", 0)
    r = api(token, "createChatInviteLink", chat_id=CHANNEL_ID,
            name=("ref-" + str(uid))[:32])
    link = (r.get("result") or {}).get("invite_link")
    if not link:
        return None, 0
    refs["by_user"][str(uid)] = {"link": link, "name": uname or str(uid), "count": 0}
    refs["by_link"][link] = str(uid)
    _save_refs(refs)
    return link, 0


def credit_join(invite_link):
    """A user joined via invite_link -> credit its creator. Returns (name,count) or None."""
    if not invite_link:
        return None
    refs = _load_refs()
    uid = refs["by_link"].get(invite_link)
    if not uid:
        return None
    refs["by_user"][uid]["count"] = refs["by_user"][uid].get("count", 0) + 1
    _save_refs(refs)
    u = refs["by_user"][uid]
    return u["name"], u["count"]


def leaderboard_text():
    refs = _load_refs()
    rows = sorted(refs["by_user"].values(), key=lambda x: -x.get("count", 0))
    rows = [r for r in rows if r.get("count", 0) > 0][:10]
    if not rows:
        return ("\U0001F3C6 PACK LEADERBOARD\n\nNobody's brought anybody yet. Be the first. "
                "DM me /invite to get your link and start recruiting. The dog remembers who builds the pack.")
    lines = ["\U0001F3C6 PACK LEADERBOARD -- top recruiters\n"]
    medals = ["\U0001F947", "\U0001F948", "\U0001F949"]
    for i, r in enumerate(rows):
        tag = medals[i] if i < 3 else f"  {i+1}."
        lines.append(f"{tag} {r['name']}: {r['count']} brought in")
    lines.append("\nDM me /invite for your link. Top recruiters get remembered when the dog rewards the pack.")
    return "\n".join(lines)


INVITE_HELP = ("\U0001F517 YOUR PERSONAL PACK LINK\n\nShare this exact link. Everyone who joins through it "
               "counts as YOURS on the leaderboard:\n\n{link}\n\nBring the pack. The dog remembers who shows up. "
               "\U0001F436 (see /leaderboard)")


def api(token, method, **params):
    body = json.dumps(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", body,
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=40))


def answer_for(text):
    t = (text or "").lower()
    for keys, ans in ANSWERS:
        if any(k in t for k in keys):
            return ans
    return FALLBACK


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("no TELEGRAM_BOT_TOKEN"); return 1
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0  # another instance is alive
    offset = int(OFFSET_FILE.read_text()) if OFFSET_FILE.exists() else 0
    print(f"responder up, offset={offset}")
    while True:
        try:
            r = api(token, "getUpdates", offset=offset + 1, timeout=30,
                    allowed_updates=["message", "chat_member"])
            for u in r.get("result", []):
                offset = max(offset, u["update_id"])
                OFFSET_FILE.write_text(str(offset))
                cm = u.get("chat_member")
                if cm:
                    newm = cm.get("new_chat_member") or {}
                    oldm = cm.get("old_chat_member") or {}
                    if newm.get("status") in ("member", "administrator") and \
                       oldm.get("status") in ("left", "kicked", None):
                        res = credit_join((cm.get("invite_link") or {}).get("invite_link"))
                        if res:
                            name, cnt = res
                            try:
                                api(token, "sendMessage", chat_id=CHANNEL_ID,
                                    text=f"\U0001F436 a new paw joined the pack -- brought by {name} (now {cnt} recruited). welcome in. \U0001F451")
                            except Exception:
                                pass
                    continue
                m = u.get("message") or {}
                if m.get("from", {}).get("is_bot"):
                    continue
                chat = m.get("chat", {})
                if chat.get("type") == "channel":
                    continue  # never reply inside the broadcast channel
                text = m.get("text", "")
                if not text:
                    continue
                low = text.strip().lower()
                if low.startswith(("/invite", "/refer", "/mylink", "/link")):
                    uid = (m.get("from") or {}).get("id")
                    uname = (m.get("from") or {}).get("first_name") or (m.get("from") or {}).get("username")
                    link, _c = get_or_make_invite(token, uid, uname)
                    msg = INVITE_HELP.format(link=link) if link else \
                          "Couldn't make your link right now -- try again in a minute. \U0001F436"
                    api(token, "sendMessage", chat_id=chat["id"], text=msg)
                    print("invite link issued to", uid)
                    continue
                if low.startswith(("/leaderboard", "/lb", "/top")):
                    api(token, "sendMessage", chat_id=chat["id"], text=leaderboard_text())
                    continue
                # in groups, only answer when mentioned or a keyword hits hard
                if chat.get("type") in ("group", "supergroup"):
                    if "bcardd_x_bot" not in text.lower() and not any(
                            k in text.lower() for keys, _ in ANSWERS[:6] for k in keys):
                        continue
                now = time.time()
                if now - RATE.get(chat.get("id"), 0) < 20:
                    continue  # max 1 reply / 20s / chat
                RATE[chat.get("id")] = now
                api(token, "sendMessage", chat_id=chat["id"], text=answer_for(text),
                    reply_to_message_id=m.get("message_id"))
                print(f"replied in {chat.get('id')}: {text[:40]!r}")
        except Exception as e:
            print("loop err:", repr(e)[:120])
            time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
