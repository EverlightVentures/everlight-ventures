#!/usr/bin/env python3
"""
Reddit Monitor Agent -- Watches subreddits for buyer signals, drafts replies,
alerts Slack for human posting.

Strategy: Monitor -> Detect -> Draft -> Alert -> Human Posts -> Lead Captured

Why not auto-post?
  - Reddit bans bots that comment promotionally (Responsible Builder Policy)
  - CA SB 243 requires bot disclosure for commercial interactions
  - Human-posted helpful replies convert 10x better than bot spam

Modes:
    watch     -- continuous monitoring (run as daemon)
    scan      -- one-time scan of recent posts
    status    -- show monitoring stats

Usage:
    python3 reddit_monitor.py              # one-time scan (default)
    python3 reddit_monitor.py watch        # continuous daemon
    python3 reddit_monitor.py status
"""
import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# Django bootstrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "09_DASHBOARD", "hive_dashboard"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", "03_Credentials", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import django
django.setup()

from broker_ops.models import LeadProfile
from broker_ops.services import ingest_lead

logging.basicConfig(
    level=logging.INFO,
    format="[REDDIT-MONITOR %(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

UA = "EverLight-BrokerOS/1.0 (Reddit Monitor)"
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_logs", "broker_ops")
os.makedirs(LOG_DIR, exist_ok=True)
DB_PATH = os.path.join(LOG_DIR, "reddit_monitor.db")

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Subreddits to monitor with their focus areas
MONITORED_SUBREDDITS = {
    "SaaS": {
        "queries": ["looking for tool", "recommend", "alternative to", "need software", "best tool"],
        "priority": "high",
    },
    "smallbusiness": {
        "queries": ["need software", "looking for tool", "POS system", "best app for", "recommend"],
        "priority": "high",
    },
    "entrepreneur": {
        "queries": ["recommend SaaS", "best tool for", "looking for software", "automate"],
        "priority": "medium",
    },
    "startups": {
        "queries": ["what tool do you use", "recommend", "looking for", "alternative"],
        "priority": "medium",
    },
    "Entrepreneur": {
        "queries": ["need a tool", "software recommendation", "best platform"],
        "priority": "low",
    },
    "selfhosted": {
        "queries": ["looking for", "alternative to", "recommend", "self hosted"],
        "priority": "low",
    },
}

# Buyer intent signals -- post must contain at least one
BUYER_SIGNALS = [
    "looking for", "need a tool", "recommend", "alternative to",
    "anyone use", "best tool for", "what do you use for",
    "searching for", "help me find", "suggestions for",
    "we need", "our team needs", "trying to find",
    "any good", "which tool", "what software",
    "switch from", "replace", "migrate from",
    "budget for", "willing to pay", "what's the best",
    "need software", "pos system", "crm", "automation tool",
    "project management", "invoicing", "scheduling software",
]

# Category detection
CATEGORY_KEYWORDS = {
    "ai_saas": ["ai", "llm", "gpt", "chatbot", "automation", "ml", "machine learning"],
    "dev_service": ["api", "sdk", "devtool", "developer", "backend", "hosting", "ci/cd"],
    "fintech": ["payment", "billing", "invoicing", "accounting", "fintech", "stripe"],
    "marketing": ["seo", "analytics", "marketing", "email marketing", "social media", "ads"],
    "logistics": ["shipping", "logistics", "inventory", "warehouse", "pos", "point of sale"],
}

# Reply templates -- helpful first, link natural
REPLY_TEMPLATES = {
    "recommendation": """Hey! I've been tracking tools in this space. Based on what you're describing, here are a few options worth checking out:

{recommendations}

If you want, I run a free tool-matching service at everlightventures.io/find-tools -- you tell us what you need and we match you with vetted options. No cost, no spam. Just saves you the research time.

Happy to dig deeper if you share more about your specific setup.""",

    "alternative": """Good question -- I've seen a few teams make this switch recently. The main alternatives people are looking at:

{recommendations}

We actually help businesses find the right fit at everlightventures.io/find-tools -- free matching, no commitment. Might save you some trial-and-error.

What's your main pain point with the current tool?""",

    "general_help": """This comes up a lot. A few things to consider:

{recommendations}

I help match businesses with tools at everlightventures.io/find-tools if you want a curated shortlist. Free service, just trying to help people avoid the endless Google rabbit hole.

What's your team size and budget range? That usually narrows it down fast.""",
}


# ---------------------------------------------------------------------------
# DATABASE (track seen posts to avoid duplicates)
# ---------------------------------------------------------------------------

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_posts (
            post_id TEXT PRIMARY KEY,
            subreddit TEXT,
            title TEXT,
            author TEXT,
            url TEXT,
            score REAL,
            draft_reply TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            alerted_at TEXT,
            posted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitor_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT DEFAULT CURRENT_TIMESTAMP,
            posts_scanned INTEGER,
            matches_found INTEGER,
            alerts_sent INTEGER
        )
    """)
    conn.commit()
    return conn


def _is_seen(conn, post_id):
    row = conn.execute("SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,)).fetchone()
    return row is not None


def _mark_seen(conn, post_id, subreddit, title, author, url, score, draft_reply):
    conn.execute(
        "INSERT OR IGNORE INTO seen_posts (post_id, subreddit, title, author, url, score, draft_reply) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (post_id, subreddit, title, author, url, score, draft_reply)
    )
    conn.commit()


def _mark_alerted(conn, post_id):
    conn.execute(
        "UPDATE seen_posts SET status = 'alerted', alerted_at = ? WHERE post_id = ?",
        (datetime.utcnow().isoformat(), post_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# REDDIT API (public JSON, no auth needed)
# ---------------------------------------------------------------------------

def fetch_subreddit_new(subreddit, limit=25):
    """Fetch newest posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", {}).get("children", [])
    except Exception as e:
        log.warning(f"Failed to fetch r/{subreddit}: {e}")
        return []


def fetch_subreddit_search(subreddit, query, limit=10):
    """Search a subreddit for specific terms."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://www.reddit.com/r/{subreddit}/search.json"
        f"?q={encoded}&sort=new&t=week&limit={limit}&restrict_sr=on"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", {}).get("children", [])
    except Exception as e:
        log.warning(f"Failed to search r/{subreddit} for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# SIGNAL DETECTION & SCORING
# ---------------------------------------------------------------------------

def score_post(title, selftext, subreddit):
    """Score a Reddit post for buyer intent (0-100)."""
    combined = f"{title} {selftext}".lower()
    score = 0.0
    signals_found = []

    # Buyer signal matches (up to 50 pts)
    signal_count = 0
    for signal in BUYER_SIGNALS:
        if signal in combined:
            signal_count += 1
            signals_found.append(signal)
    score += min(50, signal_count * 10)

    # Category relevance (up to 20 pts)
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            score += 5

    # Question format bonus (people asking = buyers)
    if "?" in title:
        score += 10
        signals_found.append("question_format")

    # Subreddit priority bonus
    priority = MONITORED_SUBREDDITS.get(subreddit, {}).get("priority", "low")
    if priority == "high":
        score += 15
    elif priority == "medium":
        score += 10

    # Length bonus (longer = more detail = more serious)
    if len(selftext) > 200:
        score += 5
        signals_found.append("detailed_post")

    return min(100, score), signals_found


def guess_categories(text):
    """Detect product categories from text."""
    text_lower = text.lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.append(cat)
    return cats or ["other"]


# ---------------------------------------------------------------------------
# REPLY DRAFTING
# ---------------------------------------------------------------------------

def draft_reply(title, selftext, subreddit, categories):
    """Draft a helpful reply that naturally mentions everlightventures.io."""
    combined = f"{title} {selftext}".lower()

    # Pick template based on content
    if "alternative" in combined or "switch" in combined or "replace" in combined:
        template_key = "alternative"
    elif "recommend" in combined or "best" in combined or "suggest" in combined:
        template_key = "recommendation"
    else:
        template_key = "general_help"

    # Generate contextual recommendations based on categories
    rec_lines = []
    cat_recs = {
        "ai_saas": [
            "For AI/automation, check out n8n (open source workflows) or Zapier for simpler stuff",
            "If you need an AI chatbot, Chatwoot is solid and open source",
        ],
        "dev_service": [
            "For dev tooling, Hatchet (task orchestration) and Infisical (secrets management) are worth a look",
            "Cal.com for scheduling, Papermark for document sharing -- both open source",
        ],
        "fintech": [
            "Lago is great for usage-based billing, and Stripe is still the standard for payments",
            "For invoicing specifically, check out Invoice Ninja or FreshBooks",
        ],
        "marketing": [
            "Plausible for privacy-friendly analytics, Formbricks for surveys/feedback",
            "For email marketing, Resend has great developer experience",
        ],
        "logistics": [
            "For POS, there are some good open-source options depending on your industry",
            "Inventory management: check out Inventree or ERPNext",
        ],
    }

    for cat in categories[:2]:
        recs = cat_recs.get(cat, [
            "Hard to recommend without knowing more about your stack and team size",
            "A few options exist depending on your budget and technical needs",
        ])
        rec_lines.extend(recs[:2])

    if not rec_lines:
        rec_lines = [
            "Hard to recommend without knowing more specifics",
            "Budget and team size usually narrow it down fast",
        ]

    recommendations = "\n".join(f"- {r}" for r in rec_lines[:3])
    template = REPLY_TEMPLATES[template_key]
    return template.format(recommendations=recommendations)


# ---------------------------------------------------------------------------
# SLACK ALERTING
# ---------------------------------------------------------------------------

def send_slack_alert(post_data, score, signals, draft, subreddit):
    """Send a Slack notification with the Reddit post + draft reply."""
    if not SLACK_WEBHOOK_URL:
        log.warning("No SLACK_WEBHOOK_URL set. Skipping alert.")
        return False

    title = post_data.get("title", "")[:100]
    author = post_data.get("author", "unknown")
    permalink = post_data.get("permalink", "")
    selftext = (post_data.get("selftext", "") or "")[:300]
    post_url = f"https://www.reddit.com{permalink}" if permalink else ""

    msg = (
        f"*REDDIT BUYER ALERT* (score: {score:.0f})\n"
        f"*r/{subreddit}* | by u/{author}\n"
        f"*{title}*\n"
        f"{selftext[:200]}{'...' if len(selftext) > 200 else ''}\n\n"
        f"Signals: {', '.join(signals[:5])}\n"
        f"Post: {post_url}\n\n"
        f"--- DRAFT REPLY (copy-paste to Reddit) ---\n"
        f"```{draft[:1500]}```\n"
        f"---\n"
        f"_Reply at: {post_url}_"
    )

    payload = json.dumps({"text": msg}).encode()
    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": UA}
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        log.error(f"Slack alert failed: {e}")
        return False


# ---------------------------------------------------------------------------
# LEAD INGESTION
# ---------------------------------------------------------------------------

def ingest_reddit_lead(post_data, subreddit, score, categories):
    """Create a LeadProfile from a Reddit post."""
    author = post_data.get("author", "")
    post_id = post_data.get("id", "")
    title = post_data.get("title", "")
    selftext = post_data.get("selftext", "") or ""
    permalink = post_data.get("permalink", "")

    if author in ("[deleted]", "AutoModerator", ""):
        return None

    placeholder_email = f"reddit-{post_id}@placeholder.io"
    if LeadProfile.objects.filter(email=placeholder_email).exists():
        return None

    lead = LeadProfile.objects.create(
        name=author,
        email=placeholder_email,
        company="",
        role="",
        need_description=f"{title}\n\n{selftext}"[:2000],
        categories_needed=categories,
        intent="warm",
        lead_source="reddit",
        source_url=f"https://www.reddit.com{permalink}" if permalink else "",
        raw_data={
            "reddit_id": post_id,
            "author": author,
            "subreddit": subreddit,
            "score": score,
        },
    )
    return lead


# ---------------------------------------------------------------------------
# SCAN CYCLE
# ---------------------------------------------------------------------------

def scan_subreddits(conn, min_score=30, dry_run=False):
    """Scan all monitored subreddits for buyer signals."""
    total_scanned = 0
    matches_found = 0
    alerts_sent = 0

    for subreddit, config in MONITORED_SUBREDDITS.items():
        log.info(f"Scanning r/{subreddit}...")

        # Fetch new posts
        posts = fetch_subreddit_new(subreddit, limit=25)

        # Also search for specific queries
        for query in config.get("queries", [])[:3]:
            search_posts = fetch_subreddit_search(subreddit, query, limit=10)
            # Deduplicate by post ID
            seen_ids = {p["data"]["id"] for p in posts}
            for sp in search_posts:
                if sp["data"]["id"] not in seen_ids:
                    posts.append(sp)

        for child in posts:
            post = child.get("data", {})
            post_id = post.get("id", "")
            title = post.get("title", "")
            selftext = post.get("selftext", "") or ""
            author = post.get("author", "")

            total_scanned += 1

            # Skip already seen
            if _is_seen(conn, post_id):
                continue

            # Skip deleted/mod posts
            if author in ("[deleted]", "AutoModerator", ""):
                continue

            # Score the post
            post_score, signals = score_post(title, selftext, subreddit)

            if post_score < min_score:
                continue

            # This is a buyer signal!
            matches_found += 1
            categories = guess_categories(f"{title} {selftext}")

            # Draft a reply
            reply = draft_reply(title, selftext, subreddit, categories)

            permalink = post.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink else ""

            log.info(f"  MATCH [{post_score:.0f}pts] r/{subreddit}: {title[:60]}...")

            # Save to DB
            _mark_seen(conn, post_id, subreddit, title, author, post_url, post_score, reply)

            if dry_run:
                log.info(f"  [DRY] Would alert + ingest: u/{author}")
                continue

            # Ingest as lead
            lead = ingest_reddit_lead(post, subreddit, post_score, categories)
            if lead:
                log.info(f"  Lead created: {lead.name} ({lead.lead_source})")

            # Alert to Slack
            if send_slack_alert(post, post_score, signals, reply, subreddit):
                _mark_alerted(conn, post_id)
                alerts_sent += 1
                log.info(f"  Slack alert sent for u/{author}")

        # Rate limit: wait between subreddits to avoid Reddit throttling
        time.sleep(2)

    # Log stats
    conn.execute(
        "INSERT INTO monitor_stats (posts_scanned, matches_found, alerts_sent) VALUES (?, ?, ?)",
        (total_scanned, matches_found, alerts_sent)
    )
    conn.commit()

    log.info(f"Scan complete: {total_scanned} posts scanned, {matches_found} matches, {alerts_sent} alerts")
    return total_scanned, matches_found, alerts_sent


# ---------------------------------------------------------------------------
# CONTINUOUS WATCH MODE
# ---------------------------------------------------------------------------

def watch_loop(interval_minutes=15, min_score=30):
    """Continuously monitor subreddits at intervals."""
    log.info(f"Starting Reddit watch daemon (interval: {interval_minutes}m, min_score: {min_score})")
    conn = _init_db()

    while True:
        try:
            scan_subreddits(conn, min_score=min_score)
        except Exception as e:
            log.error(f"Scan cycle failed: {e}")

        log.info(f"Sleeping {interval_minutes} minutes...")
        time.sleep(interval_minutes * 60)


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

def show_status():
    """Show monitoring stats."""
    conn = _init_db()

    total_seen = conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]
    alerted = conn.execute("SELECT COUNT(*) FROM seen_posts WHERE status = 'alerted'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM seen_posts WHERE status = 'pending'").fetchone()[0]

    last_scan = conn.execute(
        "SELECT scan_time, posts_scanned, matches_found, alerts_sent FROM monitor_stats ORDER BY id DESC LIMIT 1"
    ).fetchone()

    # Recent matches
    recent = conn.execute(
        "SELECT subreddit, title, author, score FROM seen_posts ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    print(f"Reddit Monitor: {total_seen} posts seen | {alerted} alerted | {pending} pending")
    if last_scan:
        print(f"Last scan: {last_scan[0]} | {last_scan[1]} scanned | {last_scan[2]} matches | {last_scan[3]} alerts")
    if recent:
        print("\nRecent matches:")
        for r in recent:
            print(f"  [{r[3]:.0f}pts] r/{r[0]} | u/{r[2]} | {r[1][:50]}")

    # Django lead count from Reddit
    reddit_leads = LeadProfile.objects.filter(lead_source="reddit").count()
    print(f"\nReddit leads in Django: {reddit_leads}")

    conn.close()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Reddit Monitor Agent")
    parser.add_argument(
        "command", nargs="?", default="scan",
        choices=["scan", "watch", "status"],
        help="Mode: scan (one-time), watch (daemon), status"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting/alerting")
    parser.add_argument("--min-score", type=float, default=30, help="Minimum buyer signal score (default: 30)")
    parser.add_argument("--interval", type=int, default=15, help="Watch interval in minutes (default: 15)")
    args = parser.parse_args()

    if args.command == "status":
        show_status()
        return

    if args.command == "watch":
        watch_loop(interval_minutes=args.interval, min_score=args.min_score)
        return

    # One-time scan
    conn = _init_db()
    scan_subreddits(conn, min_score=args.min_score, dry_run=args.dry_run)
    conn.close()


if __name__ == "__main__":
    main()
