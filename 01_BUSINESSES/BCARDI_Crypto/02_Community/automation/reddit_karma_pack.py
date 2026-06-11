#!/usr/bin/env python3
"""
Reddit Karma Pack -- daily DM to the operator with the 5 best live threads to
comment on (ZERO promo) so the account clears crypto-sub karma gates in days.
Reads public RSS (no Reddit creds), delivers via the Telegram bot.

Why not autonomous posting: new-account automated promo = shadowban. This is
the machine doing 95% (find threads, give angles) and the human doing the 5%
Reddit actually polices (typing two genuine sentences).

Cron (e5): 5 16 * * *   (9:05 AM PT daily)
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
    # TG: header, then ONE MESSAGE PER PIECE so long-press copies exactly that piece
    send(f"\U0001F9E0 REDDIT KARMA PACK -- {date.today().isoformat()}\n"
         "Each thread = 2 messages: the link, then the paste text (long-press -> Copy).\n"
         "Tweak a word so it's yours. ZERO coin talk. Dashboard: http://localhost:2600")
    ok = True
    for r in rows:
        ok &= send(f"r/{r['sub']}: {r['title']}\n{r['link']}")
        ok &= send(r["paste"] or ("\U0001F4A1 " + r["hint"]))
    print("pack sent:", ok, f"({len(rows)} threads)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
