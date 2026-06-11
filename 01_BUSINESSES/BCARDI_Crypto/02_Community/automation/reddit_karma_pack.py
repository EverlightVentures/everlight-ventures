#!/usr/bin/env python3
"""
Reddit Karma Pack -- daily DM to the operator with the 5 best live threads to
comment on (ZERO promo) so the account clears crypto-sub karma gates in days.
Reads public RSS (no Reddit creds), delivers via the Telegram bot.

Why not autonomous posting: new-account automated promo = shadowban. This is
the machine doing 95% (find threads, give angles) and the human doing the 5%
Reddit actually polices (typing two genuine sentences).

Crons (e5):
  0 16 * * *            --generate  (build the day's pack, send header)
  5 16-23,0-3 * * *     --drip      (deliver ONE thread+paste per hour --
                                     matches Reddit's ~1-comment-per-10-min
                                     new-account rate limit with margin)
Env: TELEGRAM_BOT_TOKEN + TG_OPERATOR_CHAT (Rich's DM chat id)
"""
import json
import os
import re
import urllib.request
from datetime import date

SUBS = [
    # (sub, angle hint -- genuine participation only, never mention the coin)
    ("solana", "genuine take or question on the topic. you actually use Solana daily -- speak from that."),
    ("CryptoCurrency", "balanced 2-sentence opinion. no tickers, no links. upvotes come from sounding sane."),
    ("dogs", "Dogo Argentino owner content is gold here. share real dog experience, photos win."),
    ("memecoins", "comment on OTHER coins' threads with sharp takes. build name recognition, sell nothing."),
    ("pumpfun", "trader-to-trader observations. what you actually see on the platform."),
]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0"


def fetch(sub, n=2):
    req = urllib.request.Request(
        f"https://www.reddit.com/r/{sub}/hot.rss", headers={"User-Agent": UA})
    xml = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    items = []
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        t = re.search(r"<title>(.*?)</title>", e, re.S)
        l = re.search(r'<link href="([^"]+)"', e)
        if not t or not l:
            continue
        title = re.sub(r"&amp;", "&", t.group(1)).strip()
        if title.lower().startswith(("welcome to", "daily discussion", "moronic monday")):
            continue
        items.append((title[:90], l.group(1)))
        if len(items) >= n:
            break
    return items


def draft_comment(sub, title):
    """Perplexity drafts a paste-ready comment per thread. Falls back to None."""
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        return None
    prompt = (f"Write ONE reddit comment (1-2 short sentences) for this r/{sub} thread: "
              f"\"{title}\". Sound like a regular human redditor: casual, specific, "
              "lowercase is fine. Genuinely engage with the topic. ABSOLUTE RULES: "
              "no cryptocurrency promotion, no coin names or tickers, no links, no emojis, "
              "no questions back unless natural, never mention being an AI. "
              "Reply with the comment text only.")
    body = json.dumps({"model": "sonar", "max_tokens": 90,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.perplexity.ai/chat/completions", body,
                                 {"Content-Type": "application/json",
                                  "Authorization": "Bearer " + key})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30))
        text = r["choices"][0]["message"]["content"].strip().strip('"')
        return re.sub(r"\[\d+\]", "", text)[:400] or None  # strip citation marks
    except Exception:
        return None


def main():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TG_OPERATOR_CHAT", "")
    if not tok or not chat:
        print("missing TELEGRAM_BOT_TOKEN/TG_OPERATOR_CHAT"); return 1
    def send(text):
        body = json.dumps({"chat_id": chat, "text": text[:4000],
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     body, {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=20)).get("ok")

    rows = []
    for sub, hint in SUBS:
        try:
            for title, link in fetch(sub):
                rows.append({"sub": sub, "title": title, "link": link,
                             "paste": draft_comment(sub, title), "hint": hint})
        except Exception as e:
            print(f"r/{sub} fetch failed: {repr(e)[:60]}")
    # dashboard source of truth (phone dashboard pulls this over ssh)
    from pathlib import Path
    Path("karma_pack.json").write_text(json.dumps(
        {"date": date.today().isoformat(), "rows": rows}, indent=1))
    Path("karma_drip_state.json").write_text(json.dumps({"date": date.today().isoformat(), "idx": 0}))
    send(f"\U0001F9E0 KARMA PACK READY -- {date.today().isoformat()} ({len(rows)} threads)\n"
         "One mission lands per hour (Reddit rate-limit pace). Do it when it dings.\n"
         "Cockpit anytime: http://localhost:2600")
    print("pack generated:", len(rows), "threads")
    return 0


def drip():
    """Send the NEXT unsent thread+paste as its own task. One per cron tick."""
    from pathlib import Path
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TG_OPERATOR_CHAT", "")
    if not (tok and chat and Path("karma_pack.json").exists()):
        return 0
    pack = json.loads(Path("karma_pack.json").read_text())
    st = json.loads(Path("karma_drip_state.json").read_text()) if Path("karma_drip_state.json").exists() else {"date": "", "idx": 0}
    if st.get("date") != pack.get("date"):
        st = {"date": pack.get("date"), "idx": 0}
    rows = pack.get("rows", [])
    if st["idx"] >= len(rows):
        return 0  # day's pack done, stay silent
    r = rows[st["idx"]]
    n = st["idx"] + 1

    def send(text):
        body = json.dumps({"chat_id": chat, "text": text[:4000],
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     body, {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=20)).get("ok")

    send(f"\U0001F3AF KARMA MISSION {n}/{len(rows)} -- r/{r['sub']}\n{r['title']}\n{r['link']}")
    send(r["paste"] or ("\U0001F4A1 " + r["hint"]))
    st["idx"] = n
    Path("karma_drip_state.json").write_text(json.dumps(st))
    print(f"dripped {n}/{len(rows)}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(drip() if "--drip" in sys.argv else main())
