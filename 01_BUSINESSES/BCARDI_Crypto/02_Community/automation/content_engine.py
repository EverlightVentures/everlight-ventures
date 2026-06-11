#!/usr/bin/env python3
"""
$BCARDD INFINITE CONTENT ENGINE -- the DOGE-killer fire hose.

The queues were FINITE (8 sustain posts that loop = stale = dead). This makes
them INFINITE: every day it generates fresh on-brand aggressive posts via
Perplexity (already on e5), bakes in the cross-links + heart CTA, runs them
through the shared compliance gate, and tops up BOTH queues so they never
repeat and never run dry.

Also fires the daily PACK ORDER -- one concrete raid mission for the army
(the literal SHIB-army mechanic) into the Telegram queue.

Runs daily on e5 BEFORE the post crons. Auto-refills when pending < threshold.
Cron: 30 9 * * *   (refill the day's ammo at 9:30 UTC, before 10:00 UTC first post)
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import x_autopilot as xa  # compliance_check, BANNED

XQ = HERE / "x_content_queue.json"
TGQ = HERE / "tg_content_queue.json"
TGL = "t.me/b_card_d"
XL = "x.com/B_CARD_D"
LOW_WATER = 12  # refill when fewer pending than this

BRAND = "You write posts for $BCARDD, a Solana meme coin. The mascot is THE YUNG PRINTZ: a REAL Dogo Argentino, a crowned street prince in American-flag glasses. What the audience knows him for: he pilots a battle RIG, he blows stuff up, he runs the alley, he has his own playable game at alleykingz.online, and his dev bag is locked on-chain. He is a real dog, a prince, a warrior, and a coin. SECRET (TEASE ONLY, NEVER STATE): the Printz has a hidden second life. You may drop SUBTLE foreshadowing (tricks nobody has seen yet, a sly grin, something up his sleeve) but NEVER say he deals cards / is a dealer / shuffles / runs the table / has a deck. That reveal comes later, do NOT spoil it. VOICE: aggressive crypto-twitter degen energy, confident, funny, street, lowercase ok. POSITIONING (push hard, most posts): the next great dog coin in the lineage of the giants. 2013 had $DOGE, 2021 had $SHIB, 2026 is THE PRINTZ. doge walked, shib ran, the printz takes the throne. it is the dog's year. shiba-killer / doge-killer energy. claim it, never beg. HARD RULES: never promise profit/returns/gains/moon/pump/1000x; no financial advice; no investment; never the words blackjack/casino/gambling/bet/bacardi/dealer/shuffle/deck/cards. ANONYMITY: never first-person as a creator/dev/founder; the coin and dog just EXIST, faceless like Satoshi; the dog is a real Dogo Argentino, never someone's dog."


def ppx(prompt, n_tokens=900):
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        return None
    body = json.dumps({"model": "sonar", "max_tokens": n_tokens,
                       "messages": [{"role": "system", "content": BRAND},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.perplexity.ai/chat/completions", body,
                                 {"Content-Type": "application/json",
                                  "Authorization": "Bearer " + key})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=40))
        return r["choices"][0]["message"]["content"]
    except Exception as e:
        print("ppx err:", repr(e)[:80]); return None


def parse_lines(text):
    """Pull clean one-liners from an LLM list (numbered/bulleted/quoted)."""
    out = []
    for ln in (text or "").splitlines():
        ln = re.sub(r"^\s*[\d.\-*)\"']+\s*", "", ln).strip().strip('"').strip()
        ln = re.sub(r"\[\d+\]", "", ln)  # strip citations
        if 8 < len(ln) < 250 and not ln.lower().startswith(("here", "sure", "these")):
            out.append(ln)
    return out



SECRET_LEAK = ("dealer", "shuffle", "deck", "deals the card", "deal the card",
               "deals you in", "runs the table", "at the table", "card-dealing", "deals cards")


def _no_leak(t):
    low = t.lower()
    return not any(w in low for w in SECRET_LEAK)

def clean(text):
    low = text.lower()
    return _no_leak(text) and not any(b in low for b in xa.BANNED)


def refill_x():
    items = json.loads(XQ.read_text())
    pending = [i for i in items if i.get("status") == "pending"]
    if len(pending) >= LOW_WATER:
        print(f"X queue healthy ({len(pending)} pending), skip"); return 0
    raw = ppx("Write 14 punchy standalone X posts, each UNDER 180 characters. Mix: "
              "dog-dealer teases, DOGE/SHIB lineage flexes ('every cycle has its dog'), "
              "receipts/locked-bag confidence, and 'you're early' FOMO. "
              "Return ONLY the posts, one per line, no numbering.")
    lines = [l for l in parse_lines(raw or "") if clean(l)]
    base = len([i for i in items if i["id"].startswith("gen-x-")])
    added = 0
    for i, t in enumerate(lines):
        # bake the funnel into every post (rotate the CTA so it never reads canned)
        ctas = [f"\n\nthe pack: {TGL}", f"\n\nback room: {TGL} -- like + repost",
                f"\n\n{TGL} | search $BCARDD on Jupiter, tap the heart"]
        body = t + ctas[i % len(ctas)] + "\n$BCARDD"
        if len(body) > 280 or not clean(body):
            continue
        items.append({"id": f"gen-x-{base + added + 1:03d}", "phase": "sustain",
                      "text": body, "post_at": None, "status": "pending"})
        added += 1
    XQ.write_text(json.dumps(items, indent=2))
    print(f"X refilled +{added}")
    return added


def refill_tg():
    items = json.loads(TGQ.read_text())
    sent = set(json.loads((HERE / "tg_sent.json").read_text())) if (HERE / "tg_sent.json").exists() else set()
    live = [i for i in items if i["id"] not in sent and i.get("status", "pending") == "pending"]
    if len(live) >= 6:
        print(f"TG queue healthy ({len(live)} live), skip"); return 0
    raw = ppx("Write 4 medium Telegram posts (3-6 sentences each) for the $BCARDD community "
              "channel. Topics: the DOGE-killer thesis, why a locked bag + a real game beats "
              "every jpeg coin, a hype 'state of the pack' rally, and the lore of the Yung Printz. "
              "Separate each post with a line containing only ===.", 1100)
    foot = f"\n\n--\nX: {XL} (like + repost every drop) | tap the heart on $BCARDD's Jupiter page.\nIn DOGO we trust."
    base = len([i for i in items if i["id"].startswith("gen-tg-")])
    added = 0
    for chunk in (raw or "").split("==="):
        body = re.sub(r"\[\d+\]", "", chunk)
        body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
        body = re.sub(r"(?im)^\s*post\s*\d+\s*[-:—].*$", "", body)
        body = body.replace("—", "-").replace("–", "-")
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if len(body) < 60 or not clean(body):
            continue
        items.append({"id": f"gen-tg-{base + added + 1:03d}", "phase": "tg",
                      "text": body + foot, "post_at": None, "status": "pending"})
        added += 1
    TGQ.write_text(json.dumps(items, indent=2))
    print(f"TG refilled +{added}")
    return added


def pack_order():
    """Daily raid mission -- turns the audience into the army."""
    items = json.loads(TGQ.read_text())
    raw = ppx("Write ONE short daily 'PACK ORDERS' rally for the $BCARDD army telegram: a single "
              "concrete free action the community should do today to spread the word (examples: "
              "reply to a big Solana/dog-coin post, drop the dog in a trending thread, share the "
              "game with one friend, tag someone). Make it feel like a mission from a general, "
              "high energy, 2-3 sentences. No links needed, no financial promises.", 300)
    body = re.sub(r"\[\d+\]", "", raw or "").strip()
    if not body or not clean(body):
        body = ("\U0001F6A8 PACK ORDERS: find ONE big dog-coin post on X today and drop a \U0001F436 + "
                "\"the new dog deals now\" in the replies. Bring one degen to the back room. "
                "Every cycle has its dog -- this one's ours.")
    head = "\U0001F6A8 PACK ORDERS \U0001F436\n\n"
    foot = f"\n\nDo it now. The dog remembers who shows up.\nX: {XL} | back room is home."
    items.append({"id": f"pack-order-{len([i for i in items if i['id'].startswith('pack-order-')]) + 1:03d}",
                  "phase": "tg", "text": head + body + foot, "post_at": None, "status": "pending"})
    TGQ.write_text(json.dumps(items, indent=2))
    print("pack order queued")



# --- THE SPONSORS LANE: shout out the chain of command, ride their reach ---
# Tagging big ecosystem accounts = their followers + algo see us. Gratitude, not begging.
SPONSORS = [
    ("@solana", "the chain the dog runs on -- fast, cheap, where the culture lives"),
    ("@pumpdotfun", "the launchpad that let a real dog deal his own cards"),
    ("@JupiterExchange", "the aggregator + the verification layer keeping it honest"),
    ("@StreamflowFi", "where the dev bag is locked, public, on-chain"),
    ("@phantom", "the wallet the whole pack carries"),
    ("@dexscreener", "where degens watch the dog\'s chart in real time"),
]


def sponsor_shoutout():
    """Queue a gratitude shoutout tagging an ecosystem giant (rotates daily)."""
    xs = json.loads(XQ.read_text())
    prior = [i for i in xs if i["id"].startswith("sponsor-")]
    handle, why = SPONSORS[len(prior) % len(SPONSORS)]
    raw = ppx("Write ONE short X post (under 200 chars) thanking " + handle + " -- " + why + ". "
              "Genuine gratitude with dog swagger, frame $BCARDD as proudly built on/with them. "
              "Tag them naturally. No financial promises. Return only the post.", 220)
    body = (raw or "").strip().strip('"').replace("\u2014", "-")
    if not body or not clean(body) or handle not in body:
        body = "shoutout to " + handle + " -- " + why + ". \U0001F436\U0001F0CF the dog is proud to be built here. $BCARDD"
    body = body[:235] + "\n\nthe pack: " + TGL + "\n$BCARDD"
    xs.append({"id": "sponsor-" + format(len(prior) + 1, "03d"), "phase": "sustain",
               "text": body, "post_at": None, "status": "pending"})
    XQ.write_text(json.dumps(xs, indent=2))
    print("sponsor shoutout queued:", handle)


def main():
    refill_x()
    refill_tg()
    pack_order()
    sponsor_shoutout()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
