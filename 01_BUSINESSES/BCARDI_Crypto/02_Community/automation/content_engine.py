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
import urllib.error
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


GEN_MODEL = os.environ.get("BCARDD_GEN_MODEL", "claude-sonnet-4-6")


def ppx(prompt, n_tokens=900, search=False):
    """Generate text via Claude (Anthropic Messages API). Keeps the same name +
    return contract (text or None) so every caller works unchanged. BRAND is the
    system prompt. search=True adds the web_search server tool (SLOW ~1-2min, use
    for the once-daily headline refresh); search=False is a fast direct call
    (~5-10s, use for per-post generation off the cached headlines)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("no ANTHROPIC_API_KEY"); return None
    hdr = {"x-api-key": key, "anthropic-version": "2023-06-01",
           "content-type": "application/json"}
    messages = [{"role": "user", "content": prompt}]
    body = {"model": GEN_MODEL, "max_tokens": max(256, int(n_tokens)),
            "system": BRAND, "messages": messages}
    if search:
        body["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 1}]
    to = 300 if search else 35
    try:
        for _ in range(5):  # follow pause_turn continuations from the search loop
            req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                         data=json.dumps(body).encode(), headers=hdr,
                                         method="POST")
            r = json.load(urllib.request.urlopen(req, timeout=to))
            content = r.get("content", [])
            if r.get("stop_reason") == "pause_turn":
                messages = messages + [{"role": "assistant", "content": content}]
                body["messages"] = messages
                continue
            # Keep ONLY the final answer: discard the "let me search..." narration that
            # precedes each web_search step by resetting on every server-tool block.
            texts = []
            for b in content:
                bt = b.get("type")
                if bt == "text":
                    texts.append(b.get("text", ""))
                elif bt in ("server_tool_use", "web_search_tool_result"):
                    texts = []
            return ("\n".join(t for t in texts if t)).strip() or None
        return None
    except urllib.error.HTTPError as e:
        print("claude err %d: %s" % (e.code, e.read().decode()[:160])); return None
    except Exception as e:
        print("claude err:", repr(e)[:120]); return None


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


def _full_name(t):
    return re.sub(r'\b(the\s+)?(yung\s+)?printz\b', 'The Yung Printz', t, flags=re.I)

def clean(text):
    low = text.lower()
    return _no_leak(text) and not any(b in low for b in xa.BANNED)


# --- TOPICAL LANE: every X slot gets a FRESH take on what's happening NOW ---
# Generated at post time (not refill time) so it's current to the minute.
# The footer is the constant 1-2-3 funnel; the body is never the same twice.

MINT = os.environ.get("BCARDI_CA", "6mjokwXx7NNzo5ocvLDFGmbsGAs7rYHZdVJhKYkapump")
JUP_URL = "jup.ag/tokens/" + MINT

FOOTER_123 = ("\n\n1) join the pack: " + TGL +
              "\n2) tap the heart on $BCARDD: " + JUP_URL +
              "\n3) play: alleykingz.online")

TOPICAL_BODY_MAX = 150  # leaves room for the footer under X's 280 weighted chars


def _words(t):
    return set(re.findall(r"[a-z']{3,}", t.lower()))


def _too_similar(a, b, thresh=0.45):
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) > thresh


def _strip_footer(t):
    return t.split("\n\n1)")[0]


TG_FOOT = ("\n\n--\nX: " + XL + " (like + repost every drop)"
           "\nheart us on Jupiter: " + JUP_URL +
           "\nplay: alleykingz.online")


def _clean_part(t):
    t = re.sub(r"\[\d+\]", "", t or "").strip().strip('"').strip()
    t = re.sub("[\\u2014\\u2013]", "-", t)  # normalize long dashes
    return _full_name(t)


# Operator directive 2026-06-12: tragedy is NEVER promo material. Every autopilot
# post carries the ad footer, so heavy/violent/geopolitical stories are banned as
# subject matter outright -- a human-voice condolence post is the operator's call,
# never the bot's. Hard-checked AFTER generation, belt to the prompt's suspenders.
TOPIC_BLOCKLIST = (
    "war", "airstrike", "strike on", "strikes on", "missile", "bomb", "drone attack",
    "dead", "death", "died", "killed", "kills", "casualt", "fatal", "victims",
    "military", "troops", "soldier", "sailor", "navy", "terror", "shooting",
    "shooter", "hostage", "invasion", "escalation", "ceasefire", "gaza", "iran",
    "israel", "ukraine", "massacre", "genocide", "famine", "earthquake",
    "hurricane", "wildfire", "flood", "overdose", "suicide",
    # divisive politics is also banned as material (operator: "with Trump and
    # the war dude, this is crazy. bad for the brand.")
    "trump", "biden", "president", "white house", "congress", "senate",
    "election", "politic",
)


def _heavy_topic(t):
    low = (t or "").lower()
    return any(w in low for w in TOPIC_BLOCKLIST)


TOPICAL_STATE = HERE / "topical_state.json"

# Rotating content archetypes -- each post takes the NEXT one, so consecutive
# posts feel structurally different (a different rhetorical device + a different
# social-psychology angle) even when the news cycle is thin. Variety of FORM,
# not just topic. THIS is what stops the feed reading like an ad bot.
ARCHETYPES = [
    ("hot_take", "FORM: a sharp, screenshot-worthy ONE-LINER hot take on the story. No setup, no explainer -- just the quotable line. Confident, a little funny."),
    ("curiosity_gap", "PSYCHOLOGY: curiosity gap. Tease a connection between the story and the dog WITHOUT fully explaining it, so people lean in. End on intrigue, never a neat bow."),
    ("social_proof", "PSYCHOLOGY: social proof / FOMO. Imply the sharp, early people are already moving while everyone else just watches the headline. Make outsiders feel late."),
    ("underdog", "NARRATIVE: underdog. Tie the story to the dog rising past the giants (doge walked, shib ran, the Printz takes the throne). Scrappy, inspiring, 'they slept on it.'"),
    ("meme", "FORM: internet-culture meme riff. Lowercase, degen-literate, ride whatever meme format is hot right now. Make the pack laugh, do not pitch."),
    ("question", "FORM: open with a QUESTION that begs a reply (engagement bait) tied to the story. Make answering irresistible -- the pack should want to comment."),
    ("flex", "VOICE: confident brand flex tied to today's win. Swagger, not bragging -- 'while they did X, the dog did Y.'"),
    ("street_wisdom", "FORM: a clever one-line PROVERB / piece of street wisdom the story inspires. Quotable, a little philosophical, dog-flavored."),
    ("insider", "PSYCHOLOGY: in-group identity. Make the pack feel they are in on something outsiders are not, anchored to the story. Us vs the noise."),
]


def _load_topical_state():
    try:
        return json.loads(TOPICAL_STATE.read_text())
    except Exception:
        return {"arch_idx": 0, "mission_idx": 0, "subjects": []}


def _save_topical_state(st):
    try:
        TOPICAL_STATE.write_text(json.dumps(st))
    except Exception:
        pass


def _subject_used(subject, used):
    s = _words(subject)
    if not s:
        return False
    for u in used:
        w = _words(u)
        if w and len(s & w) / max(1, len(s | w)) > 0.4:
            return True
    return False


HEADLINES_CACHE = HERE / "headlines_cache.json"


def refresh_headlines():
    """ONCE-DAILY slow web-search call: cache ~10 current FUN stories so per-post
    generation can be fast (no per-post search). Run from main() before refills."""
    import datetime
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    prompt = (
        "Search the web for the biggest FEEL-GOOD or FUN trending stories happening RIGHT NOW. "
        "Lanes: sports, entertainment/comedy/celebrity, internet culture & memes, tech wins, "
        "science/space wins, wholesome viral moments. HARD-EXCLUDE war, death, disaster, tragedy, "
        "crime, and ALL politics/politicians. List 8 stories, ONE per line, no numbering and no "
        "markdown, EXACTLY in this format:\n"
        "subject :: one concrete fact sentence with a number or name\n"
        "subject :: one concrete fact sentence")
    raw = ppx(prompt, 1500, search=True)
    if not raw:
        return 0
    raw = re.sub(r"\[\d+\]", "", raw)  # strip web-search citation markers
    stories = []
    for ln in raw.splitlines():
        if "::" not in ln:
            continue
        subj, _, fact = ln.partition("::")
        subj = re.sub(r"^[\s\-*\d.)#]+", "", subj).strip().strip("*").strip()
        fact = fact.strip()
        if subj and fact and not _heavy_topic(subj + " " + fact):
            stories.append({"subject": subj[:60], "fact": fact[:240]})
    if not stories:
        print("headlines: no parseable lines"); return 0
    HEADLINES_CACHE.write_text(json.dumps({"date": today, "stories": stories}, indent=1))
    print("headlines refreshed:", len(stories))
    return len(stories)


def _next_story(used):
    """Pick the next fresh cached story not already used; refresh the cache if it's
    missing or stale (a once-a-day slow path)."""
    import datetime
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    try:
        cache = json.loads(HEADLINES_CACHE.read_text())
    except Exception:
        cache = {}
    if cache.get("date") != today or not cache.get("stories"):
        refresh_headlines()
        try:
            cache = json.loads(HEADLINES_CACHE.read_text())
        except Exception:
            cache = {}
    for s in cache.get("stories", []):
        subj = s.get("subject", "")
        if subj and not _heavy_topic(subj + " " + s.get("fact", "")) and not _subject_used(subj, used):
            return s
    return None


def make_topical_trio(recent_texts=None):
    """ONE fresh story, THREE platform renditions (X / Telegram / Phantom wallet),
    written in a ROTATING archetype off the daily headline cache (fast, no per-post
    web search) and screened against a memory of stories already used -- so it never
    repeats a topic OR a format. Returns {'x','tg','wallet'}; 'x' is None on failure
    (caller falls back to the queue)."""
    st = _load_topical_state()
    arch_key, arch_brief = ARCHETYPES[st.get("arch_idx", 0) % len(ARCHETYPES)]
    used_subjects = st.get("subjects", [])[-30:]
    recent = [_strip_footer(t) for t in (recent_texts or [])][:12]
    out = {"x": None, "tg": None, "wallet": None}
    story = _next_story(used_subjects)
    if not story:
        print("topical: no fresh story available"); return out
    subject = story.get("subject", "")[:60]
    prompt = (
        "TODAY'S STORY to riff on -- " + story.get("subject", "") + ": " + story.get("fact", "") + "\n"
        "WRITE IT IN THIS ARCHETYPE -- " + arch_brief + "\n"
        "BRAND: The Yung Printz, a real crowned Dogo Argentino, the next great dog coin after doge "
        "& shib. Witty, street, confident, good-faith, never financial advice. Use the story to "
        "show the dog has insight into the WORLD, not just the coin. Vary your opening words -- "
        "never start two posts the same way.\n"
        "Output EXACTLY this, nothing else:\n"
        "X: <under 150 chars, no links/hashtags/cashtags>\n"
        "===\n"
        "TG: <2-4 sentences, community voice, no links>\n"
        "===\n"
        "WALLET: <under 180 chars, holder voice, ends with: tap the heart on our jupiter page; no links>")
    for attempt in range(2):
        raw = ppx(prompt, 700, search=False)  # FAST: no per-post web search
        if not raw:
            continue
        parts = {}
        for chunk in raw.split("==="):
            cs = re.sub(r"(?im)^\s*subject\s*:.*$", "", chunk).strip()
            m = re.search(r"(?is)\b(X|TG|WALLET)\s*:\s*(.+)", cs)
            if m:
                parts[m.group(1).upper()] = _clean_part(m.group(2))
        if any(_heavy_topic(parts.get(k, "")) for k in ("X", "TG", "WALLET")):
            print("topical rejected: heavy/political"); continue
        body = parts.get("X", "")
        if not body or len(body) > TOPICAL_BODY_MAX + 30 or not clean(body):
            continue
        if any(_too_similar(body, r) for r in recent):
            continue
        full = xa.sanitize_cashtags(body + FOOTER_123)
        ok, reason = xa.compliance_check(full)
        if not ok:
            print("topical rejected:", reason); continue
        out["x"] = full
        tg = parts.get("TG", "")
        if tg and clean(tg):
            out["tg"] = tg
        wallet = parts.get("WALLET", "")
        if wallet and len(wallet) <= 230 and clean(wallet):
            out["wallet"] = wallet
        # commit: advance the archetype + remember this story so neither repeats
        st["arch_idx"] = (st.get("arch_idx", 0) + 1) % len(ARCHETYPES)
        st["subjects"] = (used_subjects + [subject])[-30:]
        _save_topical_state(st)
        print("topical: archetype=%s subject=%s" % (arch_key, subject))
        return out
    return out


def make_topical_x_post(recent_texts=None):
    """Back-compat shim: X rendition only."""
    return make_topical_trio(recent_texts).get("x")


def queue_topical_tg(text):
    """Prepend the day-slot's topical TG rendition so the next TG run (1h after X)
    carries the SAME story. Evergreen queue items become fallback ammo."""
    items = json.loads(TGQ.read_text())
    n = len([i for i in items if str(i.get("id", "")).startswith("topical-tg-")]) + 1
    items.insert(0, {"id": "topical-tg-%03d" % n, "phase": "tg",
                     "text": text + TG_FOOT, "post_at": None, "status": "pending"})
    TGQ.write_text(json.dumps(items, indent=2))


def _tg_operator_send(text):
    """DM the operator via the bot (same rail as the Reddit karma drip)."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TG_OPERATOR_CHAT", "")
    if not tok or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text[:4000],
                       "disable_web_page_preview": True}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot" + tok + "/sendMessage",
                                 body, {"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=20)).get("ok", False)
    except Exception as e:
        print("tg operator send err:", repr(e)[:80])
        return False


def write_wallet_brief(text, notify=False):
    """Drop the Phantom-wallet rendition where the operator can grab it: latest in
    one file, history in a jsonl, and (live slots) a 2-message operator DM --
    header first, then the bare paste so one long-press-copy grabs exactly it."""
    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE / "wallet_brief_latest.txt").write_text(text + "\n")
    with open(HERE / "wallet_briefs.jsonl", "a") as f:
        f.write(json.dumps({"ts": ts, "text": text}) + "\n")
    if notify:
        _tg_operator_send("\U0001F4F2 PHANTOM WALLET BRIEF -- copy the next message, paste into the $BCARDD wallet chat:")
        _tg_operator_send(text)


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
        body = xa.sanitize_cashtags(_full_name(t + ctas[i % len(ctas)]) + "\n$BCARDD")
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
                      "text": _full_name(body) + foot, "post_at": None, "status": "pending"})
        added += 1
    TGQ.write_text(json.dumps(items, indent=2))
    print(f"TG refilled +{added}")
    return added


# Rotating mission TYPES so the daily order is never the same chore twice.
PACK_MISSIONS = [
    "MEME mission: make or share one Yung Printz meme today and drop it in the chat. funniest gets pinned.",
    "INVITE mission: bring ONE new friend into the back room today. the pack grows by word of mouth, not ads.",
    "HEART mission: tap the heart on the $BCARDD Jupiter page if you haven't. 30 seconds, helps us get verified.",
    "GAME mission: play one round at alleykingz.online and post your score. the game is the moat no other dog coin has.",
    "CLIP mission: screen-record 10 seconds of the game or the dog and post it anywhere, tag the pack.",
    "GM mission: drop a 'GM pack' and your city. let's see how far the alley actually reaches.",
    "SIGNAL mission: leave ONE genuine, smart comment on a big Solana or dog-coin post -- real value, no spam. that's how you get noticed.",
    "FANART mission: sketch, AI-make, or caption one piece of Printz art today. we feature the best.",
    "WELCOME mission: be the first to greet anyone new who walks into the chat today. warm pack = sticky pack.",
    "ORIGIN mission: tell the chat in one line why you joined the pack. realest answer gets love.",
]


def pack_order():
    """Daily raid mission -- ROTATES through diverse mission types so the order
    never reads like the same 'reply to a thread' chore every single day."""
    items = json.loads(TGQ.read_text())
    st = _load_topical_state()
    midx = st.get("mission_idx", 0) % len(PACK_MISSIONS)
    mission = PACK_MISSIONS[midx]
    raw = ppx("Write ONE short, high-energy 'PACK ORDERS' rally (2-3 sentences) for the $BCARDD "
              "army telegram, built around THIS specific mission: " + mission + " Make it feel "
              "like a fresh order from a general with personality. VARY the opening line -- do not "
              "start with the same phrase every time. No links, no financial promises.", 300)
    body = re.sub(r"\[\d+\]", "", raw or "").strip().strip('"')
    body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
    if not body or not clean(body):
        body = "today's order -- " + mission
    head = "\U0001F6A8 PACK ORDERS \U0001F436\n\n"
    foot = f"\n\nDo it now. The dog remembers who shows up.\nX: {XL} | back room is home."
    items.append({"id": f"pack-order-{len([i for i in items if i['id'].startswith('pack-order-')]) + 1:03d}",
                  "phase": "tg", "text": head + _full_name(body) + foot, "post_at": None, "status": "pending"})
    TGQ.write_text(json.dumps(items, indent=2))
    st["mission_idx"] = (midx + 1) % len(PACK_MISSIONS)
    _save_topical_state(st)
    print("pack order queued:", mission[:24])



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
    body = xa.sanitize_cashtags(body[:235] + "\n\nthe pack: " + TGL + "\n$BCARDD")
    xs.append({"id": "sponsor-" + format(len(prior) + 1, "03d"), "phase": "sustain",
               "text": body, "post_at": None, "status": "pending"})
    XQ.write_text(json.dumps(xs, indent=2))
    print("sponsor shoutout queued:", handle)


def community_post():
    """Daily inclusion post: pull dog-owners into the pack (widens TAM beyond crypto)."""
    xs = json.loads(XQ.read_text())
    prior = [i for i in xs if i['id'].startswith('community-')]
    raw = ppx("Write ONE short X post (under 180 chars) that makes EVERY dog owner feel "
              "included in $BCARDD -- their real dog is royalty too, a young prince/princess, "
              "part of the pack. Warm + inclusive, real-dog-owner life, not crypto-jargon. "
              "Invite them to show/crown their dog. Return only the post.", 200)
    body = (raw or '').strip().strip('\"')
    if not body or not clean(body):
        body = ("DOGE and SHIB were cartoons. The Yung Printz is a real dog -- and so is yours. "
                "every good boy is royalty. show us your prince. \U0001F436\U0001F451")
    body = xa.sanitize_cashtags(_full_name(body)[:230] + "\n\nthe pack: " + TGL + "\n$BCARDD")
    xs.append({'id': 'community-' + format(len(prior) + 1, '03d'), 'phase': 'sustain',
               'text': body, 'post_at': None, 'status': 'pending'})
    XQ.write_text(json.dumps(xs, indent=2))
    print('community post queued')


def main():
    refresh_headlines()   # once-daily slow web search -> warm the headline cache
    refill_x()
    refill_tg()
    pack_order()
    sponsor_shoutout()
    community_post()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
