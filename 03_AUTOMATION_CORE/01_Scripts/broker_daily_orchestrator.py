#!/usr/bin/env python3
"""
Broker OS - Fully Autonomous Daily Orchestrator

Zero human intervention. Full loop:
  1. Scout SELLERS (tools/SaaS) from HN, GitHub, DEV.to
  2. Scout BUYERS (people asking for tools) from HN Ask, DEV.to, GitHub Issues
  3. Sync inbound leads/offers from Supabase (website forms)
  4. Run matching engine
  5. Auto-create outreach sequences for high-score matches
  6. Send due outreach emails (warm-up limited)
  7. Auto-escalate hot matches to deals
  8. Daily KPI report

Human only confirms money. Everything else is autonomous.

Subcommands:
    full      -- run all 10 steps (morning cycle, default)
    scout     -- steps 1-2 (find sellers + buyers)
    sync      -- step 3 (sync Supabase inbound forms)
    match     -- steps 4-4b (run matching + auto-approve)
    outreach  -- steps 5-7 (create sequences + send due emails)
    followup  -- step 7 only (send due follow-up emails)
    report    -- steps 9-10 (daily report + Slack)
    status    -- print 1-line status summary

Usage:
    python3 broker_daily_orchestrator.py              # full cycle (default)
    python3 broker_daily_orchestrator.py full
    python3 broker_daily_orchestrator.py scout --dry-run
    python3 broker_daily_orchestrator.py status --slack
"""
import argparse
import json
import logging
import os
import re
import smtplib
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Add broker scripts to path for enrichment module (phone + Oracle)
for _bp in [os.path.join(os.path.dirname(__file__), "broker"), "/home/opc/broker"]:
    if os.path.isdir(_bp) and _bp not in sys.path:
        sys.path.insert(0, _bp)
for _np in [
    os.path.join(os.path.dirname(__file__), "..", "..", "06_DEVELOPMENT", "everlight_os"),
    "/home/opc/06_DEVELOPMENT/everlight_os",
]:
    if os.path.isdir(_np) and _np not in sys.path:
        sys.path.insert(0, _np)
from contact_enrichment import enrich_contact, extract_email_from_text as _enrich_extract_email
try:
    from attom_enrichment import enrich_property as attom_enrich_property, format_enrichment_summary as attom_format
except ImportError:
    attom_enrich_property = None
    attom_format = None

# Django bootstrap (phone + Oracle)
for _djp in [
    os.path.join(os.path.dirname(__file__), "..", "..", "09_DASHBOARD", "hive_dashboard"),
    "/home/opc/hive_django",
]:
    if os.path.isdir(_djp) and _djp not in sys.path:
        sys.path.insert(0, _djp)
        break
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

# Load .env (phone + Oracle)
for env_path in [
    os.path.join(os.path.dirname(__file__), "..", "03_Credentials", ".env"),
    "/home/opc/.env",
]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break

import django
django.setup()

from decimal import Decimal
from django.utils import timezone
from django.db.models import Q

from broker_ops.models import BrokerMatch, Deal, LeadProfile, OfferListing, OutreachSequence
from broker_ops.services import (
    auto_approve_high_score_matches,
    create_outreach_sequence,
    expire_stale_matches,
    get_commission_summary,
    get_due_outreach,
    mark_outreach_sent,
    run_matching,
    create_deal_from_match,
    ingest_lead,
    ingest_offer,
)

try:
    from neuromorphic.nlp_engine import analyze_email_reply
except Exception:
    analyze_email_reply = None

# Workbook logger for unified tracking
_WB_PATHS = [
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent",
    "/home/opc/wholesale_agent",
]
for _wbp in _WB_PATHS:
    if os.path.isdir(_wbp) and _wbp not in sys.path:
        sys.path.insert(0, _wbp)
        break
try:
    from workbook_logger import wb as _wb
    _WB_OK = True
except Exception:
    _WB_OK = False

try:
    from neuromorphic.pipeline_api import should_outreach as pipeline_should_outreach, recommend_reply_path
except Exception:
    pipeline_should_outreach = None
    recommend_reply_path = None

try:
    from neuromorphic.brain_policy import recommend_match_priority
except Exception:
    recommend_match_priority = None

try:
    from hive_mind.slack_router import send_as_agent
except Exception:
    send_as_agent = None

try:
    from business_os.services import record_alert, record_event
except Exception:
    def record_event(*args, **kwargs):
        return None

    def record_alert(*args, **kwargs):
        return None

logging.basicConfig(
    level=logging.INFO,
    format="[BROKER %(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# Log dir: phone or Oracle
_log_candidates = [
    os.path.join(os.path.dirname(__file__), "..", "..", "_logs", "broker_ops"),
    "/home/opc/_logs/broker_ops",
    "/tmp/broker_ops_logs",
]
LOG_DIR = next((p for p in _log_candidates if os.access(os.path.dirname(p) or "/tmp", os.W_OK)), _log_candidates[-1])
os.makedirs(LOG_DIR, exist_ok=True)

# SMTP config
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.resend.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "resend")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@everlightventures.io")

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_ACCESS_TOKEN = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
SUPABASE_PROJECT_REF = "jdqqmsmwmbsnlnstyavl"

# Use service key if available, else anon (for REST API)
SUPABASE_KEY = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY

UA = "EverLight-BrokerOS/1.0"

# Buyer need keywords -- if a post mentions these, it's a potential buyer
BUYER_SIGNALS = [
    "looking for", "need a tool", "recommend", "alternative to",
    "anyone use", "best tool for", "what do you use for",
    "searching for", "help me find", "suggestions for",
    "we need", "our team needs", "trying to find",
    "any good", "which tool", "what software",
    "switch from", "replace", "migrate from",
    "budget for", "willing to pay", "pricing",
]

# Category detection for buyer needs
CATEGORY_KEYWORDS = {
    "ai_saas": ["ai", "llm", "gpt", "chatbot", "automation", "ml", "machine learning", "nlp"],
    "dev_service": ["api", "sdk", "devtool", "developer", "backend", "frontend", "database", "hosting", "ci/cd", "deployment"],
    "fintech": ["payment", "billing", "invoicing", "accounting", "fintech", "stripe", "crypto"],
    "healthtech": ["health", "medical", "hipaa", "compliance", "telehealth"],
    "marketing": ["seo", "analytics", "marketing", "email marketing", "social media", "content", "ads"],
    "logistics": ["shipping", "logistics", "inventory", "warehouse", "fulfillment", "supply chain"],
}


def _fetch_json(url, timeout=15):
    """Fetch JSON from a URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f"  Fetch failed {url[:60]}: {e}")
        return None


def _supabase_api(method, table, data=None, params=None):
    """Call Supabase REST API."""
    if not SUPABASE_KEY:
        return None
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f"  Supabase {method} {table} failed: {e}")
        return None


def _guess_categories(text):
    """Detect categories from text."""
    text_lower = text.lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.append(cat)
    return cats or ["other"]


def _has_buyer_signal(text):
    """Check if text contains buyer intent signals."""
    text_lower = text.lower()
    return any(sig in text_lower for sig in BUYER_SIGNALS)


def _extract_email_from_text(text):
    """Try to extract an email from text. Filters out image/file extensions."""
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    if not match:
        return ""
    email = match.group(0).lower()
    # Filter out false positives (image files, common non-email patterns)
    bad_tlds = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js", ".html")
    if any(email.endswith(ext) for ext in bad_tlds):
        return ""
    # Must have a plausible TLD (2-6 chars after last dot)
    tld = email.rsplit(".", 1)[-1]
    if len(tld) < 2 or len(tld) > 6:
        return ""
    # Reject if it looks like a URL fragment
    if "//" in email or "http" in email:
        return ""
    return email


# Email warm-up limits
def get_daily_limit():
    first_offer = OfferListing.objects.order_by("created_at").first()
    if not first_offer:
        return 5
    days_active = (timezone.now() - first_offer.created_at).days
    if days_active < 7:
        return 5
    elif days_active < 14:
        return 10
    elif days_active < 21:
        return 15
    else:
        return 20


def get_emails_sent_today():
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return OutreachSequence.objects.filter(
        sent_at__gte=today_start,
        status="sent"
    ).count()


def _recent_outreach_health(days=14):
    window_start = timezone.now() - timedelta(days=days)
    return {
        "recent_bounces": OutreachSequence.objects.filter(sent_at__gte=window_start, status="bounced").count(),
        "recent_unsubscribes": LeadProfile.objects.filter(updated_at__gte=window_start, unsubscribed=True).count(),
        "recent_failures": OutreachSequence.objects.filter(created_at__gte=window_start, status__in=["bounced", "skipped"]).count(),
    }


def _company_size_signal(company_size):
    return {
        "1_10": 0.25,
        "11_50": 0.45,
        "51_200": 0.7,
        "200_plus": 0.9,
    }.get(company_size or "", 0.4)


def _budget_signal(lead):
    budget = 0.0
    for value in [lead.budget_max, lead.budget_min]:
        if value is None:
            continue
        try:
            budget = max(budget, float(value))
        except Exception:
            continue
    return max(0.0, min(1.0, budget / 50000.0))


def _match_category_fit(match):
    categories = {str(cat).lower() for cat in (match.lead.categories_needed or [])}
    offer_category = (match.offer.category or "").lower()
    return 1.0 if offer_category and offer_category in categories else 0.5


def _brain_reply_context(match_result=None):
    context = {}
    if not match_result:
        return context
    if match_result.get("type") == "buyer_reply":
        broker_match = match_result.get("match")
        if broker_match is not None:
            context["match_score"] = broker_match.match_score
            context["lead_intent"] = broker_match.lead.intent
    elif match_result.get("type") == "seller_reply":
        offer = match_result.get("offer")
        if offer is not None:
            context["pricing_model"] = offer.pricing_model
            context["category"] = offer.category
    return context


# ===========================================================================
# STEP 1: SCOUT SELLERS (tools/products)
# ===========================================================================

def step_scout_sellers(dry_run=False):
    log.info("STEP 1: Scouting SELLERS (tools/products)...")

    sources = {
        "hacker_news": "https://hn.algolia.com/api/v1/search?query=Show%20HN%20SaaS&tags=show_hn&hitsPerPage=15",
        "github": "https://api.github.com/search/repositories?q=saas+tool+created:>2026-01-01&sort=stars&order=desc&per_page=15",
        "devto": "https://dev.to/api/articles?tag=saas&per_page=15&top=7",
    }

    new_count = 0
    for source, url in sources.items():
        data = _fetch_json(url)
        if not data:
            continue

        items = []
        if source == "hacker_news":
            for hit in data.get("hits", []):
                t = hit.get("title", "")
                if "Show HN" in t:
                    items.append({
                        "title": t.replace("Show HN: ", "").replace("Show HN:", "").strip(),
                        "url": hit.get("url", ""),
                        "author": hit.get("author", "HN Builder"),
                        "id": hit.get("objectID", ""),
                        "description": t,
                    })
        elif source == "github":
            for repo in data.get("items", []):
                items.append({
                    "title": repo.get("name", ""),
                    "url": repo.get("html_url", ""),
                    "author": repo.get("owner", {}).get("login", ""),
                    "id": repo.get("owner", {}).get("login", ""),
                    "description": repo.get("description", "") or repo.get("name", ""),
                })
        elif source == "devto":
            for article in (data if isinstance(data, list) else []):
                items.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "author": article.get("user", {}).get("name", ""),
                    "id": str(article.get("id", "")),
                    "description": article.get("description", ""),
                })

        for item in items[:15]:
            title = item.get("title", "")[:300]
            if not title:
                continue
            if dry_run:
                log.info(f"  [DRY] Seller from {source}: {title[:50]}")
                new_count += 1
                continue

            # Dedup by source + ID instead of placeholder email
            item_id = item.get("id", "x")
            dedup_key = f"{source}:{item_id}"
            if OfferListing.objects.filter(
                title=title, source=source, notes__contains=dedup_key
            ).exists():
                continue

            # Enrich: try to find real email/contact from profile
            author = item.get("author", "Unknown")
            contact = enrich_contact(
                source={"hacker_news": "hacker_news", "github": "github", "devto": "devto"}.get(source, source),
                author=author,
                username=author,
                source_url=item.get("url", ""),
            )

            real_email = contact.get("email", "")
            profile_url = contact.get("profile_url", "")
            website = contact.get("website", "")
            needs_enrichment = contact.get("needs_enrichment", True)

            # Build notes with dedup key and enrichment status
            notes_parts = [f"dedup:{dedup_key}"]
            if needs_enrichment:
                notes_parts.append("[NEEDS_ENRICHMENT]")
            if profile_url:
                notes_parts.append(f"profile:{profile_url}")
            if website:
                notes_parts.append(f"website:{website}")
            if contact.get("twitter"):
                notes_parts.append(f"twitter:@{contact['twitter']}")

            _, created = OfferListing.objects.update_or_create(
                title=title,
                source=source,
                seller_email=real_email or "",
                defaults={
                    "seller_name": contact.get("name", author) if contact.get("name") else author,
                    "seller_url": website or profile_url or item.get("url", ""),
                    "description": item.get("description", title)[:500],
                    "category": _guess_categories(item.get("description", title))[0],
                    "keywords": [w.lower() for w in title.split()[:6]],
                    "source_url": item.get("url", ""),
                    "status": "active",
                    "notes": " | ".join(notes_parts),
                }
            )
            if created:
                new_count += 1
                if real_email:
                    log.info(f"    REAL email found for seller {author}: {real_email}")
                else:
                    log.info(f"    No email for seller {author} -- stored profile: {profile_url or 'none'}")

    log.info(f"  Seller scout: {new_count} new offers")
    return new_count


# ===========================================================================
# STEP 2: SCOUT BUYERS (people looking for tools)
# ===========================================================================

def step_scout_buyers(dry_run=False):
    log.info("STEP 2: Scouting BUYERS (people needing tools)...")

    new_count = 0

    # --- HN: "Ask HN" posts where people ask for tool recommendations ---
    ask_queries = [
        "https://hn.algolia.com/api/v1/search?query=Ask%20HN%20recommend%20tool&tags=ask_hn&hitsPerPage=15",
        "https://hn.algolia.com/api/v1/search?query=Ask%20HN%20looking%20for%20SaaS&tags=ask_hn&hitsPerPage=10",
        "https://hn.algolia.com/api/v1/search?query=Ask%20HN%20alternative%20to&tags=ask_hn&hitsPerPage=10",
        "https://hn.algolia.com/api/v1/search?query=Ask%20HN%20what%20tool%20do%20you%20use&tags=ask_hn&hitsPerPage=10",
    ]

    for url in ask_queries:
        data = _fetch_json(url)
        if not data:
            continue
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if not _has_buyer_signal(title) and "Ask HN" not in title:
                continue

            hn_id = hit.get("objectID", "")
            author = hit.get("author", "")
            clean_title = title.replace("Ask HN: ", "").replace("Ask HN:", "").strip()

            if dry_run:
                log.info(f"  [DRY] Buyer from HN: {clean_title[:50]}")
                new_count += 1
                continue

            # Dedup by HN post ID
            dedup_key = f"hn-buyer:{hn_id}"
            source_url = f"https://news.ycombinator.com/item?id={hn_id}"
            if LeadProfile.objects.filter(source_url=source_url).exists():
                continue

            # Enrich: try to get real email from HN user profile
            contact = enrich_contact(
                source="hacker_news",
                username=author,
            )
            real_email = contact.get("email", "")
            profile_url = contact.get("profile_url", "")

            notes_parts = [f"dedup:{dedup_key}"]
            if not real_email:
                notes_parts.append("[NEEDS_ENRICHMENT]")
            if profile_url:
                notes_parts.append(f"profile:{profile_url}")
            if contact.get("website"):
                notes_parts.append(f"website:{contact['website']}")
            if contact.get("twitter"):
                notes_parts.append(f"twitter:@{contact['twitter']}")

            lead = LeadProfile.objects.create(
                name=author or f"HN User {hn_id}",
                email=real_email,
                company="",
                role="",
                need_description=clean_title[:2000],
                categories_needed=_guess_categories(clean_title),
                intent="warm" if real_email else "cold",
                lead_source="hacker_news",
                source_url=source_url,
                raw_data={"hn_id": hn_id, "author": author, "title": title, "dedup_key": dedup_key},
                notes=" | ".join(notes_parts),
            )
            new_count += 1
            if real_email:
                log.info(f"    REAL email for HN buyer {author}: {real_email}")

    # --- HN COMMENTS: Mine actual comments on Ask HN threads for buyer signals ---
    # People in comments say things like "we switched to X" or "I need Y"
    hn_comment_stories = []
    for url in ask_queries[:2]:  # reuse first 2 Ask HN queries
        data = _fetch_json(url)
        if data:
            for hit in data.get("hits", [])[:5]:
                hn_comment_stories.append(hit.get("objectID", ""))

    for story_id in hn_comment_stories:
        if not story_id:
            continue
        comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=20"
        cdata = _fetch_json(comments_url)
        if not cdata:
            continue
        for comment in cdata.get("hits", []):
            comment_text = comment.get("comment_text", "") or ""
            # Strip HTML tags for signal detection
            clean_text = re.sub(r'<[^>]+>', ' ', comment_text)
            if not _has_buyer_signal(clean_text):
                continue

            c_author = comment.get("author", "")
            c_id = comment.get("objectID", "")

            if dry_run:
                log.info(f"  [DRY] Buyer from HN comment: {c_author} - {clean_text[:50]}")
                new_count += 1
                continue

            # Dedup by comment ID
            comment_url = f"https://news.ycombinator.com/item?id={c_id}"
            if LeadProfile.objects.filter(source_url=comment_url).exists():
                continue

            # Enrich from HN user profile
            contact = enrich_contact(
                source="hacker_news",
                username=c_author,
            )
            real_email = contact.get("email", "")

            notes_parts = [f"dedup:hn-comment:{c_id}"]
            if not real_email:
                notes_parts.append("[NEEDS_ENRICHMENT]")
            if contact.get("profile_url"):
                notes_parts.append(f"profile:{contact['profile_url']}")
            if contact.get("website"):
                notes_parts.append(f"website:{contact['website']}")

            LeadProfile.objects.create(
                name=c_author or f"HN Commenter {c_id}",
                email=real_email,
                company="",
                role="",
                need_description=clean_text[:2000],
                categories_needed=_guess_categories(clean_text),
                intent="warm" if real_email else "cold",
                lead_source="hacker_news",
                source_url=comment_url,
                raw_data={"hn_comment_id": c_id, "author": c_author, "story_id": story_id, "dedup_key": f"hn-comment:{c_id}"},
                notes=" | ".join(notes_parts),
            )
            new_count += 1
            if real_email:
                log.info(f"    REAL email for HN commenter {c_author}: {real_email}")

    # --- REDDIT: Search subreddits for people looking for SaaS tools ---
    reddit_searches = [
        ("SaaS", "looking+for+tool"),
        ("SaaS", "recommend+saas"),
        ("smallbusiness", "need+software"),
        ("smallbusiness", "looking+for+tool"),
        ("entrepreneur", "recommend+SaaS"),
        ("startups", "what+tool+do+you+use"),
    ]

    for subreddit, query in reddit_searches:
        reddit_url = (
            f"https://www.reddit.com/r/{subreddit}/search.json"
            f"?q={query}&sort=new&t=week&limit=10&restrict_sr=on"
        )
        req = urllib.request.Request(reddit_url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                rdata = json.loads(resp.read())
        except Exception as e:
            log.warning(f"  Reddit r/{subreddit} failed: {e}")
            continue

        for child in (rdata.get("data", {}).get("children", []))[:10]:
            post = child.get("data", {})
            title = post.get("title", "")
            selftext = post.get("selftext", "")[:500]
            combined = f"{title} {selftext}"
            author = post.get("author", "")
            post_id = post.get("id", "")
            permalink = post.get("permalink", "")

            if not _has_buyer_signal(combined):
                continue
            if author in ("[deleted]", "AutoModerator", ""):
                continue

            if dry_run:
                log.info(f"  [DRY] Buyer from Reddit r/{subreddit}: {title[:50]}")
                new_count += 1
                continue

            # Dedup by Reddit post URL
            reddit_url = f"https://www.reddit.com{permalink}" if permalink else ""
            if reddit_url and LeadProfile.objects.filter(source_url=reddit_url).exists():
                continue
            # Also dedup by raw_data key
            dedup_key = f"reddit:{post_id}"
            if LeadProfile.objects.filter(notes__contains=dedup_key).exists():
                continue

            # Reddit doesn't expose emails -- store profile URL
            contact = enrich_contact(source="reddit", username=author)
            profile_url = contact.get("profile_url", "")

            notes_parts = [f"dedup:{dedup_key}", "[NEEDS_ENRICHMENT]"]
            if profile_url:
                notes_parts.append(f"profile:{profile_url}")

            LeadProfile.objects.create(
                name=author,
                email="",
                company="",
                role="",
                need_description=combined[:2000],
                categories_needed=_guess_categories(combined),
                intent="cold",
                lead_source="reddit",
                source_url=reddit_url,
                raw_data={"reddit_id": post_id, "author": author, "subreddit": subreddit, "dedup_key": dedup_key},
                notes=" | ".join(notes_parts),
            )
            new_count += 1

    # --- DEV.to: articles/comments about "looking for", "alternative to" ---
    devto_queries = [
        "https://dev.to/api/articles?tag=tools&per_page=10&top=7",
        "https://dev.to/api/articles?tag=productivity&per_page=10&top=7",
        "https://dev.to/api/articles?tag=startup&per_page=10&top=7",
    ]

    for url in devto_queries:
        data = _fetch_json(url)
        if not data or not isinstance(data, list):
            continue
        for article in data:
            title = article.get("title", "")
            desc = article.get("description", "")
            combined = f"{title} {desc}"

            if not _has_buyer_signal(combined):
                continue

            art_id = str(article.get("id", ""))
            author_name = article.get("user", {}).get("name", "")
            author_user = article.get("user", {}).get("username", "")

            if dry_run:
                log.info(f"  [DRY] Buyer from DEV.to: {title[:50]}")
                new_count += 1
                continue

            # Dedup by DEV.to article URL
            article_url = article.get("url", "")
            if article_url and LeadProfile.objects.filter(source_url=article_url).exists():
                continue
            dedup_key = f"devto-buyer:{art_id}"
            if LeadProfile.objects.filter(notes__contains=dedup_key).exists():
                continue

            # Enrich from DEV.to user profile (website, github, twitter)
            contact = enrich_contact(
                source="devto",
                author=author_name,
                username=author_user,
                source_url=article_url,
            )
            real_email = contact.get("email", "")

            notes_parts = [f"dedup:{dedup_key}"]
            if not real_email:
                notes_parts.append("[NEEDS_ENRICHMENT]")
            if contact.get("profile_url"):
                notes_parts.append(f"profile:{contact['profile_url']}")
            if contact.get("website"):
                notes_parts.append(f"website:{contact['website']}")
            if contact.get("github"):
                notes_parts.append(f"github:{contact['github']}")
            if contact.get("twitter"):
                notes_parts.append(f"twitter:@{contact['twitter']}")

            lead = LeadProfile.objects.create(
                name=author_name or author_user or f"DEV.to User {art_id}",
                email=real_email,
                company="",
                role="developer",
                need_description=combined[:2000],
                categories_needed=_guess_categories(combined),
                intent="warm" if real_email else "cold",
                lead_source="other",
                source_url=article_url,
                raw_data={"devto_id": art_id, "author": author_user, "title": title, "dedup_key": dedup_key},
                notes=" | ".join(notes_parts),
            )
            new_count += 1
            if real_email:
                log.info(f"    REAL email for DEV.to user {author_user}: {real_email}")

    # --- GitHub: Issues/Discussions where people request tools/integrations ---
    gh_queries = [
        "https://api.github.com/search/issues?q=label:feature-request+%22looking+for%22+created:>2026-01-01&sort=created&order=desc&per_page=10",
        "https://api.github.com/search/issues?q=%22need+a+tool%22+%22recommend%22+created:>2026-01-01&sort=created&order=desc&per_page=10",
    ]

    for url in gh_queries:
        data = _fetch_json(url)
        if not data:
            continue
        for issue in data.get("items", []):
            title = issue.get("title", "")
            body = (issue.get("body", "") or "")[:500]
            combined = f"{title} {body}"

            user = issue.get("user", {})
            gh_login = user.get("login", "")
            issue_id = str(issue.get("id", ""))

            if dry_run:
                log.info(f"  [DRY] Buyer from GitHub: {title[:50]}")
                new_count += 1
                continue

            # Dedup by GitHub issue URL
            issue_url = issue.get("html_url", "")
            if issue_url and LeadProfile.objects.filter(source_url=issue_url).exists():
                continue
            dedup_key = f"gh-buyer:{issue_id}"
            if LeadProfile.objects.filter(notes__contains=dedup_key).exists():
                continue

            # Enrich from GitHub user profile (email, blog, twitter)
            contact = enrich_contact(
                source="github",
                username=gh_login,
                source_url=issue_url,
            )
            real_email = contact.get("email", "")

            notes_parts = [f"dedup:{dedup_key}"]
            if not real_email:
                notes_parts.append("[NEEDS_ENRICHMENT]")
            if contact.get("profile_url"):
                notes_parts.append(f"profile:{contact['profile_url']}")
            if contact.get("website"):
                notes_parts.append(f"website:{contact['website']}")
            if contact.get("twitter"):
                notes_parts.append(f"twitter:@{contact['twitter']}")

            lead = LeadProfile.objects.create(
                name=contact.get("name") or gh_login or f"GitHub User {issue_id}",
                email=real_email,
                company=contact.get("company", ""),
                role="developer",
                need_description=combined[:2000],
                categories_needed=_guess_categories(combined),
                intent="warm" if real_email else "cold",
                lead_source="github",
                source_url=issue_url,
                raw_data={"gh_issue_id": issue_id, "login": gh_login, "dedup_key": dedup_key},
                notes=" | ".join(notes_parts),
            )
            new_count += 1
            if real_email:
                log.info(f"    REAL email for GitHub user {gh_login}: {real_email}")

    log.info(f"  Buyer scout: {new_count} new leads")
    return new_count


# ===========================================================================
# STEP 2b: ENRICH EMAILS (replace @placeholder.io with real contacts)
# ===========================================================================

def step_enrich_emails(dry_run=False, limit=50):
    """
    For leads/offers with empty emails or @placeholder.io emails, try to find
    real contact info using the enrichment module.

    Targets:
    1. Leads with @placeholder.io emails (legacy records)
    2. Leads with empty email + [NEEDS_ENRICHMENT] in notes
    3. Offers with @placeholder.io emails (legacy records)
    4. Offers with empty email + [NEEDS_ENRICHMENT] in notes
    """
    log.info("STEP 2b: Enriching contacts (placeholder + empty emails)...")

    enriched = 0

    # --- Enrich LEADS ---
    # Target both old placeholder emails AND new empty-email leads marked for enrichment
    leads_to_enrich = LeadProfile.objects.filter(
        Q(email__contains="@placeholder.io") | Q(email="", notes__contains="[NEEDS_ENRICHMENT]"),
        unsubscribed=False,
    ).order_by("-created_at")[:limit]

    for lead in leads_to_enrich:
        raw = lead.raw_data or {}

        # Determine source type for enrichment
        source = lead.lead_source or ""
        username = raw.get("author") or raw.get("login") or ""

        # Map lead_source to enrichment source
        enrich_source = {
            "hacker_news": "hacker_news",
            "reddit": "reddit",
            "github": "github",
        }.get(source, "")

        # Try to detect source from notes/raw_data
        if not enrich_source:
            if raw.get("devto_id") or raw.get("author", ""):
                if "devto" in (lead.notes or "").lower() or raw.get("devto_id"):
                    enrich_source = "devto"
                    username = raw.get("author", "")
            elif raw.get("gh_issue_id") or raw.get("login"):
                enrich_source = "github"
                username = raw.get("login", "")
            elif raw.get("hn_id") or raw.get("hn_comment_id"):
                enrich_source = "hacker_news"
                username = raw.get("author", "")

        if not enrich_source or not username:
            continue

        contact = enrich_contact(
            source=enrich_source,
            username=username,
            source_url=lead.source_url or "",
        )
        real_email = contact.get("email", "")

        if real_email:
            if dry_run:
                log.info(f"  [DRY] Would enrich lead {lead.name}: {real_email}")
            else:
                lead.email = real_email
                lead.intent = "warm"
                # Update notes to remove NEEDS_ENRICHMENT and add contact info
                notes = lead.notes or ""
                notes = notes.replace("[NEEDS_ENRICHMENT]", "[ENRICHED]")
                if contact.get("website") and "website:" not in notes:
                    notes += f" | website:{contact['website']}"
                if contact.get("twitter") and "twitter:" not in notes:
                    notes += f" | twitter:@{contact['twitter']}"
                lead.notes = notes
                lead.save(update_fields=["email", "intent", "notes", "updated_at"])
                log.info(f"  Enriched lead: {lead.name} -> {real_email}")
            enriched += 1
        else:
            # Even if no email, update profile info in notes if we found any
            if not dry_run and contact.get("contact_method") == "profile":
                notes = lead.notes or ""
                updated = False
                if contact.get("website") and "website:" not in notes:
                    notes += f" | website:{contact['website']}"
                    updated = True
                if contact.get("twitter") and "twitter:" not in notes:
                    notes += f" | twitter:@{contact['twitter']}"
                    updated = True
                if contact.get("github") and "github:" not in notes:
                    notes += f" | github:{contact['github']}"
                    updated = True
                if updated:
                    lead.notes = notes
                    lead.save(update_fields=["notes", "updated_at"])

    # --- Enrich OFFERS (sellers) ---
    offers_to_enrich = OfferListing.objects.filter(
        Q(seller_email__contains="@placeholder.io") | Q(seller_email="", notes__contains="[NEEDS_ENRICHMENT]"),
        status="active",
    ).order_by("-created_at")[:limit]

    for offer in offers_to_enrich:
        source = offer.source or ""

        # Determine enrichment source and username
        enrich_source = ""
        username = offer.seller_name or ""

        if "github" in source.lower():
            enrich_source = "github"
        elif "hacker_news" in source.lower() or "hn" in source.lower():
            enrich_source = "hacker_news"
        elif "devto" in source.lower() or "dev.to" in source.lower():
            enrich_source = "devto"

        if not enrich_source:
            # Try to detect from seller_url
            seller_url = offer.seller_url or offer.source_url or ""
            if "github.com" in seller_url:
                enrich_source = "github"
            elif "dev.to" in seller_url:
                enrich_source = "devto"

        if not enrich_source:
            continue

        contact = enrich_contact(
            source=enrich_source,
            username=username,
            source_url=offer.seller_url or offer.source_url or "",
        )
        real_email = contact.get("email", "")

        if real_email:
            if dry_run:
                log.info(f"  [DRY] Would enrich offer {offer.title[:30]}: {real_email}")
            else:
                offer.seller_email = real_email
                notes = offer.notes or ""
                notes = notes.replace("[NEEDS_ENRICHMENT]", "[ENRICHED]")
                offer.notes = notes
                # Also update seller_url if we found a better one
                if contact.get("website") and not offer.seller_url:
                    offer.seller_url = contact["website"]
                offer.save(update_fields=["seller_email", "seller_url", "notes", "updated_at"])
                log.info(f"  Enriched offer: {offer.title[:30]} -> {real_email}")
            enriched += 1

    log.info(f"  Email enrichment: {enriched} records updated")
    return enriched


def step_enrich_properties(dry_run=False, limit=20):
    """
    STEP 2c: Enrich leads that have property addresses with ATTOM real estate data.
    Adds assessed value, last sale price, sqft, year built to lead notes.
    Only runs if attom_enrichment module is available.
    """
    if attom_enrich_property is None:
        log.info("STEP 2c: ATTOM enrichment skipped (module not available)")
        return 0

    log.info("STEP 2c: Enriching property leads with ATTOM data...")
    enriched = 0

    # Find leads with addresses that haven't been ATTOM-enriched yet
    leads = LeadProfile.objects.filter(
        categories_needed__icontains="real_estate",
        unsubscribed=False,
    ).exclude(
        notes__contains="[ATTOM_ENRICHED]"
    ).order_by("-created_at")[:limit]

    for lead in leads:
        raw = lead.raw_data or {}
        address = raw.get("address") or raw.get("property_address", "")
        if not address:
            continue

        city = raw.get("city", "")
        state = raw.get("state", "")
        zipcode = raw.get("zip", raw.get("zipcode", ""))

        if dry_run:
            log.info(f"  [DRY] Would ATTOM-enrich: {address}")
            enriched += 1
            continue

        try:
            data = attom_enrich_property(address, city, state, zipcode)
            if data.get("success"):
                summary = attom_format(data)
                notes = lead.notes or ""
                notes += f"\n\n[ATTOM_ENRICHED]\n{summary}"
                lead.notes = notes
                # Store enrichment in raw_data too
                raw["attom"] = {k: v for k, v in data.items() if k != "raw"}
                lead.raw_data = raw
                lead.save(update_fields=["notes", "raw_data", "updated_at"])
                log.info(f"  ATTOM enriched: {address} -> assessed=${data.get('assessed_value')}")
                enriched += 1
            else:
                log.info(f"  ATTOM: no data for {address}")
        except Exception as e:
            log.warning(f"  ATTOM error for {address}: {e}")

    log.info(f"  ATTOM enrichment: {enriched} properties enriched")
    return enriched


# ===========================================================================
# STEP 3: SYNC SUPABASE (pull website form submissions into Django)
# ===========================================================================

def _supabase_sql(query):
    """Execute SQL via Supabase Management API (bypasses RLS)."""
    if not SUPABASE_ACCESS_TOKEN:
        return None
    url = f"https://api.supabase.com/v1/projects/{SUPABASE_PROJECT_REF}/database/query"
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {SUPABASE_ACCESS_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f"  Supabase SQL failed: {e}")
        return None


def step_sync_supabase(dry_run=False):
    log.info("STEP 3: Syncing Supabase inbound forms...")

    if not SUPABASE_ACCESS_TOKEN:
        log.warning("  No SUPABASE_ACCESS_TOKEN. Skipping sync.")
        return 0, 0

    lead_count = 0
    offer_count = 0

    # Pull unsynced leads via SQL (bypasses RLS)
    leads = _supabase_sql("SELECT * FROM broker_leads WHERE synced_to_django = false LIMIT 50")
    if leads:
        for row in leads:
            if dry_run:
                log.info(f"  [DRY] Sync lead: {row.get('name', '')}")
                lead_count += 1
                continue

            ingest_lead({
                "name": row.get("name") or "",
                "email": row.get("email") or "",
                "company": row.get("company") or "",
                "role": row.get("role") or "",
                "company_size": row.get("company_size") or "",
                "need_description": row.get("need_description") or "",
                "categories_needed": row.get("categories_needed") or [],
                "budget_max": row.get("budget_max") or 0,
                "intent": row.get("intent") or "warm",
                "lead_source": "website_find_tools",
            })

            # Mark as synced -- validate UUID to prevent SQL injection
            row_id = str(row['id']).strip()
            if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', row_id, re.IGNORECASE):
                _supabase_sql(f"UPDATE broker_leads SET synced_to_django = true WHERE id = '{row_id}'")
            else:
                log.warning(f"  Skipping invalid UUID for broker_leads: {row_id!r}")
            lead_count += 1

    # Pull unsynced offers
    offers = _supabase_sql("SELECT * FROM broker_offers WHERE synced_to_django = false LIMIT 50")
    if offers:
        for row in offers:
            if dry_run:
                log.info(f"  [DRY] Sync offer: {row.get('title', '')}")
                offer_count += 1
                continue

            ingest_offer({
                "seller_name": row.get("seller_name") or "",
                "seller_email": row.get("seller_email") or "",
                "seller_url": row.get("seller_url") or "",
                "title": row.get("title") or "",
                "category": row.get("category") or "other",
                "description": row.get("description") or "",
                "price_min": row.get("price_min") or 0,
                "price_max": row.get("price_max") or 0,
                "pricing_model": row.get("pricing_model") or "monthly",
                "source": "website_list_tool",
                "status": "active",
            })

            # Validate UUID to prevent SQL injection
            row_id = str(row['id']).strip()
            if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', row_id, re.IGNORECASE):
                _supabase_sql(f"UPDATE broker_offers SET synced_to_django = true WHERE id = '{row_id}'")
            else:
                log.warning(f"  Skipping invalid UUID for broker_offers: {row_id!r}")
            offer_count += 1

    log.info(f"  Supabase sync: {lead_count} leads, {offer_count} offers")
    return lead_count, offer_count


# ===========================================================================
# STEP 4: MATCH (score all offer-lead pairs)
# ===========================================================================

def step_expire_matches(dry_run=False):
    log.info("STEP 3b: Expiring stale matches (>48h, no outreach)...")
    expired = expire_stale_matches(hours=48, dry_run=dry_run)
    log.info(f"  Expired: {expired} stale matches")
    return expired


def step_match(min_score=60.0, dry_run=False):
    log.info("STEP 4: Running matching engine (real emails only, score >= 60)...")
    results = run_matching(min_score=min_score, dry_run=dry_run)
    log.info(f"  Matching: {len(results)} new real-email pairs above {min_score}")
    return results


def step_auto_approve(dry_run=False):
    log.info("STEP 4b: Auto-approving high-score matches (>= 65)...")
    approved = auto_approve_high_score_matches(min_score=65.0, limit=50, dry_run=dry_run)
    log.info(f"  Auto-approved: {approved} matches")
    return approved


# ===========================================================================
# STEP 5: AUTO-CREATE OUTREACH SEQUENCES
# ===========================================================================

def step_create_sequences(dry_run=False):
    """Create outreach sequences for all high-score matches that don't have one yet."""
    log.info("STEP 5: Creating outreach sequences...")

    # Get approved matches >= 60 score with real emails that have no outreach yet
    matches = BrokerMatch.objects.filter(
        match_score__gte=60,
        status="approved",
    ).exclude(
        lead__email__contains="@placeholder.io"
    ).exclude(
        lead__unsubscribed=True
    ).filter(
        lead__email__gt=""
    ).filter(
        outreach_steps__isnull=True  # no existing sequences
    ).order_by("-match_score")[:30]

    ranked_matches = []
    for match in matches:
        priority = {
            "priority_score": round(float(match.match_score) / 100.0, 4),
            "priority_band": "high" if match.match_score >= 75 else "normal",
            "learning_mode": "stabilize",
        }
        if recommend_match_priority is not None:
            try:
                priority = recommend_match_priority({
                    "match_score": match.match_score,
                    "lead_intent": match.lead.intent,
                    "budget_signal": _budget_signal(match.lead),
                    "category_fit": _match_category_fit(match),
                })
            except Exception as e:
                log.warning(f"  Brain match priority failed for {match.id}: {e}")
        ranked_matches.append((priority.get("priority_score", 0.0), priority, match))

    created = 0
    for _, priority, match in sorted(ranked_matches, key=lambda item: item[0], reverse=True):
        if dry_run:
            log.info(
                "  [DRY] Would create sequence: %s <-> %s [%s %.2f]",
                match.lead.email,
                match.offer.title[:30],
                priority.get("priority_band", "normal"),
                priority.get("priority_score", 0.0),
            )
            created += 1
            continue

        steps = create_outreach_sequence(match)
        if steps:
            note_line = (
                f"\n[BRAIN_PRIORITY] {datetime.now().isoformat()} "
                f"band={priority.get('priority_band', 'normal')} "
                f"score={priority.get('priority_score', 0.0):.2f} "
                f"mode={priority.get('learning_mode', 'stabilize')}"
            )
            match.notes = (match.notes or "") + note_line
            match.save(update_fields=["notes", "updated_at"])
            created += 1

    log.info(f"  Sequences created: {created}")
    return created


# ===========================================================================
# STEP 6: SELLER OUTREACH (pitch tool builders on broker partnership)
# ===========================================================================

def step_seller_outreach(dry_run=False):
    """Reach out to sellers with real emails who haven't been contacted yet."""
    log.info("STEP 6: Seller partnership outreach (pitch tool builders)...")

    # Find offers with real emails that we haven't contacted
    uncontacted = OfferListing.objects.filter(
        status="active",
    ).exclude(
        seller_email__contains="@placeholder.io"
    ).exclude(
        notes__contains="[OUTREACH_SENT]"
    ).order_by("created_at")[:5]  # Max 5 per day

    daily_limit = get_daily_limit()
    sent_today = get_emails_sent_today()
    remaining = max(0, daily_limit - sent_today)

    sent = 0
    for offer in uncontacted:
        if sent >= remaining:
            break

        # Count qualified buyers in this category for the pitch
        # Use icontains on text field to avoid JSONField __contains (unsupported on SQLite)
        try:
            lead_count = LeadProfile.objects.filter(
                unsubscribed=False,
                categories_needed__icontains=offer.category,
            ).exclude(email__contains="@placeholder.io").count()
        except Exception:
            lead_count = 0
        lead_count_str = str(max(lead_count, 3))  # Floor at 3 to avoid looking empty

        subject = f"Buyers looking for {offer.title} -- partnership?"
        body = f"""Hi {offer.seller_name},

I have been watching what {offer.title} does -- {offer.description[:150]}. Impressive work.

Here is why I am reaching out: we have buyers actively searching for {offer.get_category_display()} tools. We are currently matching {lead_count_str} qualified buyers who need exactly this kind of solution.

How it works -- zero risk on your end. You only pay a finder fee if we actually close a deal. No upfront cost, no commitment, no contracts to sign today.

Interested? Just reply yes and I will send over the details.

Sage
Everlight Ventures
everlightventures.io/list-your-tool

---
Not interested? Just ignore this. We will not follow up again.
"""

        if dry_run:
            log.info(f"  [DRY] Would pitch: {offer.seller_email} ({offer.title})")
            sent += 1
            continue

        if _send_email(offer.seller_email, subject, body):
            offer.notes = (offer.notes or "") + f"\n[OUTREACH_SENT] {datetime.now().isoformat()}"
            offer.save(update_fields=["notes", "updated_at"])
            sent += 1
            log.info(f"  Pitched: {offer.seller_email} ({offer.title})")

    log.info(f"  Seller outreach: {sent} pitches sent")
    return sent


# ===========================================================================
# STEP 7: SEND DUE BUYER OUTREACH EMAILS (buyer sequences)
# ===========================================================================

def step_send_outreach(dry_run=False):
    log.info("STEP 7: Sending due outreach emails...")
    daily_limit = get_daily_limit()
    sent_today = get_emails_sent_today()
    remaining = max(0, daily_limit - sent_today)
    outreach_health = _recent_outreach_health()

    if remaining == 0:
        log.info(f"  Daily limit reached ({daily_limit}). Skipping.")
        return 0

    due_steps = get_due_outreach(limit=remaining)
    sent = 0

    for step in due_steps:
        brain_decision = None
        if pipeline_should_outreach is not None:
            try:
                lead = step.match.lead
                offer = step.match.offer
                last_contacted = lead.last_contacted or lead.created_at
                days_since_contact = max(0.0, (timezone.now() - last_contacted).total_seconds() / 86400.0)
                brain_decision = pipeline_should_outreach({
                    "lead_score": float(step.match.match_score) / 100.0,
                    "urgency": {"hot": 0.95, "warm": 0.65, "cold": 0.35}.get(lead.intent, 0.5),
                    "days_since_contact": days_since_contact,
                    "total_touches": float(lead.contact_count or 0),
                    "last_reply_sentiment": 0.0,
                    "hour": timezone.now().hour,
                    "day_of_week": timezone.now().weekday(),
                    "industry_match": _match_category_fit(step.match),
                    "deal_stage": 0.7 if hasattr(step.match, "deal") and step.match.deal_id else 0.2,
                    "company_size": _company_size_signal(lead.company_size),
                    **outreach_health,
                })
            except Exception as e:
                log.warning(f"  Brain outreach policy failed for {step.to_email}: {e}")

        if brain_decision and not brain_decision.get("should_outreach", True):
            delay_days = max(1, int(brain_decision.get("followup_delay_days", 1)))
            if dry_run:
                log.info(
                    "  [DRY] Would defer %s to %s by %sd (%s)",
                    step.step,
                    step.to_email,
                    delay_days,
                    brain_decision.get("reason", "defer"),
                )
                continue
            step.scheduled_at = max(step.scheduled_at, timezone.now()) + timedelta(days=delay_days)
            note = (
                f"\n[BRAIN_DEFERRED] {datetime.now().isoformat()} "
                f"action={brain_decision.get('reason', 'defer')} "
                f"delay_days={delay_days}"
            )
            step.notes = (step.notes or "") + note
            step.save(update_fields=["scheduled_at", "notes"])
            log.info(f"  Deferred {step.step} to {step.to_email} by {delay_days}d via brain policy")
            continue

        if dry_run:
            log.info(f"  [DRY] Would send {step.step} to {step.to_email}")
            sent += 1
            continue

        if _send_email(step.to_email, step.subject, step.body):
            mark_outreach_sent(step)
            if brain_decision:
                step.notes = (step.notes or "") + (
                    f"\n[BRAIN_SENT] {datetime.now().isoformat()} "
                    f"action={brain_decision.get('reason', 'send_now')}"
                )
                step.save(update_fields=["notes"])
            sent += 1
            log.info(f"  Sent {step.step} to {step.to_email}")

    log.info(f"  Outreach: {sent} emails sent ({sent_today + sent}/{daily_limit} daily)")
    return sent


# ===========================================================================
# STEP 8: AUTO-ESCALATE HOT MATCHES TO DEALS
# ===========================================================================

def step_auto_deals(dry_run=False):
    """
    Auto-create deals for matches where:
    - Score >= 70 (strong match)
    - Lead has replied or is hot intent
    - No existing deal
    """
    log.info("STEP 8: Auto-escalating hot matches to deals (score >= 70)...")

    hot_matches = BrokerMatch.objects.filter(
        match_score__gte=70,
        status="approved",
    ).exclude(
        deal__isnull=False  # no existing deal
    ).filter(
        Q(lead__intent="hot") | Q(outreach_steps__status="replied")
    ).distinct().order_by("-match_score")[:10]

    created = 0
    for match in hot_matches:
        if dry_run:
            log.info(f"  [DRY] Would create deal: {match.offer.title[:30]} <-> {match.lead.name}")
            created += 1
            continue

        # Estimate deal value from offer pricing
        price = match.offer.price_max or match.offer.price_min or Decimal("500")
        # Annual value estimate (monthly * 12 or use the price as-is for one-time)
        if match.offer.pricing_model == "monthly":
            deal_value = price * 12
        elif match.offer.pricing_model == "annual":
            deal_value = price
        else:
            deal_value = price

        deal = create_deal_from_match(match, deal_value, notes="Auto-created by orchestrator")
        created += 1
        log.info(f"  Deal created: ${deal_value} | {match.offer.title[:30]}")

    log.info(f"  Auto-deals: {created} created")
    return created


# ===========================================================================
# STEP 8b: CHECK REPLIES (detect responses to outreach emails)
# ===========================================================================

# Gmail IMAP config (for headless reply detection)
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.environ.get("IMAP_USER", "")  # Gmail address
IMAP_PASS = os.environ.get("IMAP_PASS", "")  # App password

# Known outreach subject prefixes (to match replies)
OUTREACH_SUBJECT_PATTERNS = [
    "Buyers looking for",
    "Found a tool that might help",
    "Quick follow-up:",
    "Closing the loop on",
    "Quick thought on",
    "Re: Quick thought on",
    "Re: Buyers looking for",
]

# Reply classification keywords
INTERESTED_SIGNALS = [
    "interested", "yes", "sure", "tell me more", "love to",
    "sounds good", "let's talk", "set up a call", "send details",
    "how does it work", "what's the commission", "happy to chat",
    "sign me up", "let's do it", "count me in", "on board",
]
UNSUBSCRIBE_SIGNALS = [
    "unsubscribe", "stop", "remove me", "opt out", "not interested",
    "no thanks", "please don't", "take me off", "do not contact",
]
BOUNCE_SIGNALS = [
    "delivery failed", "undeliverable", "mailbox not found",
    "user unknown", "address rejected", "bounced",
    "mailer-daemon", "postmaster",
]


def _classify_reply(subject, body, sender):
    """Classify a reply as interested, unsubscribe, bounce, or neutral."""
    text = f"{subject} {body}".lower()
    sender_lower = sender.lower()

    # Check for bounces first (from system addresses)
    if any(b in sender_lower for b in ["mailer-daemon", "postmaster"]):
        return "bounce"
    if any(b in text for b in BOUNCE_SIGNALS):
        return "bounce"

    # Check for unsubscribe
    if any(u in text for u in UNSUBSCRIBE_SIGNALS):
        return "unsubscribe"

    # Check for interest
    if any(i in text for i in INTERESTED_SIGNALS):
        return "interested"

    # Default: neutral (they replied but unclear intent)
    return "neutral"


def _match_reply_to_outreach(sender_email, subject):
    """Try to match a reply to an existing outreach sequence or seller pitch."""
    sender_lower = sender_email.lower().strip()

    # Check outreach sequences (buyer replies)
    buyer_match = OutreachSequence.objects.filter(
        to_email__iexact=sender_lower,
        status="sent",
    ).select_related("match", "match__lead", "match__offer").first()

    if buyer_match:
        return {"type": "buyer_reply", "outreach": buyer_match, "match": buyer_match.match}

    # Check seller pitches (seller replies)
    seller_match = OfferListing.objects.filter(
        seller_email__iexact=sender_lower,
        notes__contains="[OUTREACH_SENT]",
    ).first()

    if seller_match:
        return {"type": "seller_reply", "offer": seller_match}

    return None


def _analyze_reply(subject, body):
    """Run spaCy reply analysis when neuromorphic NLP is available."""
    if analyze_email_reply is None:
        return {}
    text = "\n".join(part.strip() for part in [subject or "", body or ""] if part and part.strip())
    if not text:
        return {}
    try:
        return analyze_email_reply(text) or {}
    except Exception as e:
        log.warning(f"  Reply NLP analysis failed: {e}")
        return {}


def _reply_analysis_lines(reply_analysis, reply_policy=None):
    """Format reply analysis for Slack and notes."""
    lines = []
    if not reply_analysis and not reply_policy:
        return lines
    if reply_analysis:
        objections = ", ".join(reply_analysis.get("objections") or ["none"])
        key_phrases = ", ".join((reply_analysis.get("key_phrases") or [])[:3]) or "n/a"
        sentiment = reply_analysis.get("sentiment_label", "unknown")
        sentiment_score = float(reply_analysis.get("reply_sentiment", 0.0))
        lines.extend([
            f"NLP sentiment: {sentiment} ({sentiment_score:+.2f})",
            f"NLP interested: {'yes' if reply_analysis.get('is_interested') else 'no'}",
            f"Objections: {objections}",
            f"Suggested next action: {reply_analysis.get('next_action', 'follow_up_3d')}",
            f"Key phrases: {key_phrases}",
        ])
    if reply_policy:
        lines.extend([
            f"Brain action: {reply_policy.get('recommended_action', 'review')}",
            f"Brain priority: {reply_policy.get('priority', 'normal')}",
            f"Escalation score: {float(reply_policy.get('escalation_score', 0.0)):.2f}",
        ])
    return lines


def _reply_analysis_note(reply_analysis, reply_policy=None):
    """Compact note-friendly summary of reply analysis."""
    lines = _reply_analysis_lines(reply_analysis, reply_policy=reply_policy)
    return " | ".join(lines[:4]) if lines else ""


def _route_reply_alert(event_type, audience, message):
    """Send reply alerts through Slack routing config when available."""
    if send_as_agent is None:
        return False

    route_names = ["seller_replies"] if audience == "seller" else ["broker_deals"]
    if "INTERESTED" in event_type.upper():
        route_names.append("dispatch")

    posted = False
    seen = set()
    for route_name in route_names:
        if route_name in seen:
            continue
        seen.add(route_name)
        try:
            posted = send_as_agent(None, route_name, message, route_name=route_name) or posted
        except Exception as e:
            log.warning(f"  Routed Slack post failed for {route_name}: {e}")
    return posted


def step_check_replies(dry_run=False):
    """
    Check inbox for replies to outreach emails.
    Uses IMAP if credentials are available, otherwise logs a skip.
    Classifies replies and auto-advances the pipeline:
    - interested -> upgrade lead intent to hot, create deal
    - unsubscribe -> mark lead unsubscribed, cancel sequences
    - bounce -> mark outreach bounced, flag lead
    - neutral -> log for human review
    """
    log.info("STEP 8b: Checking for replies to outreach...")

    import imaplib
    import email as email_lib
    from email.header import decode_header

    if not IMAP_USER or not IMAP_PASS:
        log.warning("  IMAP_USER/IMAP_PASS not set. Skipping reply check.")
        log.info("  Set IMAP_USER and IMAP_PASS (Gmail app password) in .env to enable.")
        return 0

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("INBOX")
    except Exception as e:
        log.error(f"  IMAP login failed: {e}")
        return 0

    # Search for recent replies (last 3 days)
    since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
    _, msg_ids = mail.search(None, f'(SINCE {since_date})')

    if not msg_ids[0]:
        log.info("  No recent emails found.")
        mail.logout()
        return 0

    processed = 0
    ids = msg_ids[0].split()
    log.info(f"  Scanning {len(ids)} recent emails...")

    for msg_id in ids:
        try:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
        except Exception:
            continue

        # Decode subject
        subject_raw = msg.get("Subject", "")
        if subject_raw:
            decoded_parts = decode_header(subject_raw)
            subject = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    subject += part.decode(charset or "utf-8", errors="ignore")
                else:
                    subject += part
        else:
            subject = ""

        # Check if this is a reply to our outreach
        is_outreach_reply = any(
            pat.lower() in subject.lower() for pat in OUTREACH_SUBJECT_PATTERNS
        )
        if not is_outreach_reply:
            continue

        # Get sender
        sender = msg.get("From", "")
        # Extract email from "Name <email>" format
        sender_email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', sender)
        sender_email = sender_email_match.group(0) if sender_email_match else sender

        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")

        # Classify the reply
        classification = _classify_reply(subject, body, sender_email)
        reply_analysis = _analyze_reply(subject, body)

        # Match to outreach record
        match_result = _match_reply_to_outreach(sender_email, subject)
        reply_policy = {}
        if recommend_reply_path is not None:
            try:
                reply_policy = recommend_reply_path(
                    classification,
                    reply_analysis=reply_analysis,
                    context=_brain_reply_context(match_result),
                ) or {}
            except Exception as e:
                log.warning(f"  Brain reply policy failed: {e}")

        log.info(f"  Reply from {sender_email}: [{classification}] {subject[:50]}")
        if reply_analysis:
            log.info(
                "    NLP: sentiment=%s interest=%s objections=%s next=%s",
                reply_analysis.get("sentiment_label", "unknown"),
                "yes" if reply_analysis.get("is_interested") else "no",
                ",".join(reply_analysis.get("objections") or ["none"]),
                reply_analysis.get("next_action", "follow_up_3d"),
            )
        if reply_policy:
            log.info(
                "    Brain: action=%s priority=%s escalation=%.2f",
                reply_policy.get("recommended_action", "review"),
                reply_policy.get("priority", "normal"),
                float(reply_policy.get("escalation_score", 0.0)),
            )

        if dry_run:
            processed += 1
            continue

        if not match_result:
            log.info(f"    Could not match to outreach record. Logging for review.")
            processed += 1
            continue

        # --- HANDLE BUYER REPLIES ---
        if match_result["type"] == "buyer_reply":
            outreach = match_result["outreach"]
            broker_match = match_result["match"]
            lead = broker_match.lead

            if classification == "interested":
                # Upgrade lead intent
                lead.intent = "hot"
                lead.save(update_fields=["intent", "updated_at"])

                # Mark outreach as replied
                outreach.status = "replied"
                outreach.save(update_fields=["status"])

                # Cancel remaining sequence steps
                OutreachSequence.objects.filter(
                    match=broker_match, status="pending"
                ).update(status="skipped")

                # Auto-create deal if none exists
                if not Deal.objects.filter(match=broker_match).exists():
                    price = broker_match.offer.price_max or broker_match.offer.price_min or Decimal("500")
                    if broker_match.offer.pricing_model == "monthly":
                        deal_value = price * 12
                    else:
                        deal_value = price
                    note_suffix = _reply_analysis_note(reply_analysis, reply_policy=reply_policy)
                    if note_suffix:
                        note_suffix = f" | {note_suffix}"
                    deal = create_deal_from_match(
                        broker_match, deal_value,
                        notes=f"Auto-created: buyer replied interested. Reply: {body[:200]}{note_suffix}"
                    )
                    log.info(f"    DEAL CREATED: ${deal_value} from buyer reply!")

                    # Slack notification
                    _slack_notify_reply("BUYER INTERESTED", sender_email, lead.name,
                                       broker_match.offer.title, body[:200],
                                       reply_analysis=reply_analysis, reply_policy=reply_policy, audience="buyer")

                log.info(f"    Lead upgraded to HOT: {lead.name}")

            elif classification == "unsubscribe":
                lead.unsubscribed = True
                lead.save(update_fields=["unsubscribed", "updated_at"])
                OutreachSequence.objects.filter(
                    match=broker_match, status="pending"
                ).update(status="skipped")
                outreach.status = "replied"
                outreach.save(update_fields=["status"])
                log.info(f"    Lead unsubscribed: {lead.name}")

            elif classification == "bounce":
                outreach.status = "bounced"
                outreach.save(update_fields=["status"])
                OutreachSequence.objects.filter(
                    match=broker_match, status="pending"
                ).update(status="skipped")
                log.info(f"    Outreach bounced: {lead.email}")

            else:  # neutral
                outreach.status = "replied"
                outreach.save(update_fields=["status"])
                lead.intent = "warm"
                lead.save(update_fields=["intent", "updated_at"])
                _slack_notify_reply("BUYER REPLIED (neutral)", sender_email,
                                   lead.name, broker_match.offer.title, body[:200],
                                   reply_analysis=reply_analysis, reply_policy=reply_policy, audience="buyer")
                log.info(f"    Neutral reply logged for review: {lead.name}")

        # --- HANDLE SELLER REPLIES ---
        elif match_result["type"] == "seller_reply":
            offer = match_result["offer"]

            if classification == "interested":
                # Mark offer as partner-ready
                analysis_note = _reply_analysis_note(reply_analysis, reply_policy=reply_policy)
                if analysis_note:
                    analysis_note = f" | {analysis_note}"
                offer.notes = (
                    (offer.notes or "")
                    + f"\n[SELLER_INTERESTED] {datetime.now().isoformat()} Reply: {body[:200]}{analysis_note}"
                )
                offer.save(update_fields=["notes", "updated_at"])
                _slack_notify_reply("SELLER INTERESTED", sender_email,
                                   offer.seller_name, offer.title, body[:200],
                                   reply_analysis=reply_analysis, reply_policy=reply_policy, audience="seller")
                log.info(f"    SELLER INTERESTED: {offer.seller_name} ({offer.title})")

            elif classification == "unsubscribe":
                offer.status = "paused"
                offer.notes = (offer.notes or "") + f"\n[SELLER_DECLINED] {datetime.now().isoformat()}"
                offer.save(update_fields=["status", "notes", "updated_at"])
                log.info(f"    Seller declined: {offer.seller_name}")

            else:  # neutral or bounce
                analysis_note = _reply_analysis_note(reply_analysis, reply_policy=reply_policy)
                if analysis_note:
                    analysis_note = f" | {analysis_note}"
                offer.notes = (
                    (offer.notes or "")
                    + f"\n[SELLER_REPLIED] {datetime.now().isoformat()} [{classification}] {body[:100]}{analysis_note}"
                )
                offer.save(update_fields=["notes", "updated_at"])
                _slack_notify_reply(f"SELLER REPLIED ({classification})", sender_email,
                                   offer.seller_name, offer.title, body[:200],
                                   reply_analysis=reply_analysis, reply_policy=reply_policy, audience="seller")
                log.info(f"    Seller reply ({classification}): {offer.seller_name}")

        processed += 1

    mail.logout()
    log.info(f"  Reply check: {processed} replies processed")
    return processed


def _slack_notify_reply(event_type, sender, name, product, body_preview, reply_analysis=None, reply_policy=None, audience="seller"):
    """Send Slack alert for a reply via bot token."""
    msg = (
        f"*{event_type}*\n"
        f"From: {sender} ({name})\n"
        f"Product: {product}\n"
        f"Reply: _{body_preview}_"
    )
    analysis_lines = _reply_analysis_lines(reply_analysis, reply_policy=reply_policy)
    if analysis_lines:
        msg += "\n" + "\n".join(analysis_lines)

    if _route_reply_alert(event_type, audience, msg):
        return

    # Fallback to legacy hardcoded channels
    if "INTERESTED" in event_type.upper():
        _slack_post_bot(f":fire: {msg}", channel=SLACK_CH_WAR_ROOM)
        _slack_post_bot(msg, channel=SLACK_CH_FT_HUNTERS)
    else:
        _slack_post_bot(msg, channel=SLACK_CH_FT_HUNTERS)


# ===========================================================================
# STEP 9: DAILY REPORT
# ===========================================================================

def step_report():
    log.info("STEP 9: Daily KPI report...")

    summary = get_commission_summary()
    total_offers = OfferListing.objects.filter(status="active").count()
    total_leads = LeadProfile.objects.filter(unsubscribed=False).count()
    real_leads = LeadProfile.objects.filter(unsubscribed=False).exclude(email__contains="@placeholder.io").exclude(email="").count()
    pending_matches = BrokerMatch.objects.filter(status="pending").count()
    approved_matches = BrokerMatch.objects.filter(status="approved").count()
    expired_matches = BrokerMatch.objects.filter(status="expired").count()
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_matches = BrokerMatch.objects.filter(created_at__gte=today).count()
    pending_outreach = OutreachSequence.objects.filter(status="pending").count()

    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "active_offers": total_offers,
        "total_leads": total_leads,
        "real_email_leads": real_leads,
        "pending_matches": pending_matches,
        "approved_matches": approved_matches,
        "expired_matches": expired_matches,
        "today_new_matches": today_matches,
        "active_deals": summary["active_deals"],
        "closed_won": summary["closed_won"],
        "earned_total": summary["earned_total"],
        "pending_total": summary["pending_total"],
        "emails_sent_today": get_emails_sent_today(),
        "daily_email_limit": get_daily_limit(),
        "pending_outreach_steps": pending_outreach,
    }

    report_path = os.path.join(LOG_DIR, f"daily_{report['date']}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log.info(f"  Offers: {total_offers} | Leads: {total_leads} ({real_leads} real email)")
    log.info(f"  Matches: {pending_matches} pending, {approved_matches} approved, {expired_matches} expired, {today_matches} new today")
    log.info(f"  Deals: {summary['active_deals']} active, {summary['closed_won']} won")
    log.info(f"  Commission: ${summary['earned_total']:.2f} earned, ${summary['pending_total']:.2f} pending")
    log.info(f"  Emails: {report['emails_sent_today']}/{report['daily_email_limit']} today | {pending_outreach} queued")

    return report


# ===========================================================================
# STEP 10: SLACK REPORT
# ===========================================================================

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")  # legacy, dead
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", os.environ.get("SLACK_WARROOM_TOKEN", ""))
SLACK_CH_WAR_ROOM = "C0ANAU30UQ2"
SLACK_CH_FT_HUNTERS = "C0AMVEWLT9D"
SLACK_CH_BROKER = "C0AN7FTTK2R"
SLACK_CH_ALERTS = "C0ANPRCA4AD"


def _slack_post_bot(text, channel=None):
    """Post to Slack via Bot API (webhooks are dead since 2026-03-23)."""
    token = SLACK_BOT_TOKEN
    if not token:
        log.warning("  No SLACK_BOT_TOKEN set. Skipping Slack.")
        return False
    ch = channel or SLACK_CH_WAR_ROOM
    payload = json.dumps({"channel": ch, "text": text}).encode()
    try:
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                log.error(f"  Slack bot post error: {result.get('error')}")
                return False
            return True
    except Exception as e:
        log.error(f"  Slack bot post failed: {e}")
        return False

def _get_top5_matches():
    """Return top 5 approved matches with real emails for human action."""
    top = BrokerMatch.objects.filter(
        status="approved",
    ).exclude(
        lead__email__contains="@placeholder.io"
    ).exclude(
        lead__email=""
    ).select_related("offer", "lead").order_by("-match_score")[:5]

    lines = []
    for i, m in enumerate(top, 1):
        lines.append(
            f"  {i}. [{m.match_score:.0f}pts] *{m.lead.name}* @ {m.lead.company or '?'}"
            f" ({m.lead.intent}) → _{m.offer.title[:40]}_"
        )
    return lines


def step_slack_report(report):
    """Push daily KPI report to Google Docs, post summary + link to Slack."""
    log.info("STEP 10: Publishing report to Google Docs + Slack...")

    top5 = _get_top5_matches()
    top5_block = "\n".join(top5) if top5 else "  No approved matches with real emails yet."

    # Full report content for Google Doc (markdown formatted)
    doc_content = (
        f"# Broker OS -- Daily Report\n"
        f"**Date:** {report['date']}\n\n"
        f"## Pipeline\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Active Offers (Sellers) | {report['active_offers']} |\n"
        f"| Total Leads | {report['total_leads']} |\n"
        f"| Real Email Leads | {report['real_email_leads']} |\n"
        f"| Pending Matches | {report['pending_matches']} |\n"
        f"| Approved Matches | {report['approved_matches']} |\n"
        f"| Expired Matches | {report.get('expired_matches', 0)} |\n"
        f"| New Matches Today | {report['today_new_matches']} |\n\n"
        f"## Outreach\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Emails Sent Today | {report['emails_sent_today']}/{report['daily_email_limit']} |\n"
        f"| Emails Queued | {report['pending_outreach_steps']} |\n\n"
        f"## Revenue\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Active Deals | {report['active_deals']} |\n"
        f"| Closed Won | {report['closed_won']} |\n"
        f"| Earned | ${report['earned_total']:.2f} |\n"
        f"| Pending | ${report['pending_total']:.2f} |\n\n"
        f"## Top 5 Matches to Close Today\n{top5_block}\n\n"
        f"---\n*Fully autonomous. Multi-cycle schedule active.*\n"
    )

    # Short summary for Slack
    summary = (
        f"{report['active_offers']} offers | {report['total_leads']} leads | "
        f"{report['today_new_matches']} new matches | "
        f"{report['emails_sent_today']}/{report['daily_email_limit']} emails sent | "
        f"${report['earned_total']:.2f} earned"
    )

    # Publish via Google Docs bridge
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from content_tools.gdocs_bridge import publish_report
        result = publish_report(
            title="Broker OS Daily Report",
            content=doc_content,
            folder="01_Broker_OS/Daily_KPI",
            slack_channel="#all-everlightventures",
            summary=summary,
        )
        if result.get("ok"):
            log.info(f"  Report published: {result.get('link', 'pending')}")
        elif result.get("local_path"):
            log.info(f"  Report saved locally: {result['local_path']}")
        else:
            log.warning("  Google Docs publish failed, falling back to raw Slack")
            _slack_raw_fallback(report, top5_block)
    except ImportError:
        log.warning("  gdocs_bridge not available, falling back to raw Slack")
        _slack_raw_fallback(report, top5_block)
    except Exception as e:
        log.error(f"  Publish error: {e}, falling back to raw Slack")
        _slack_raw_fallback(report, top5_block)


def _slack_raw_fallback(report, top5_block):
    """Post raw report to Slack via bot token when Google Docs is unavailable."""
    msg = (
        f"*Broker OS -- Daily Report ({report['date']})*\n"
        f"{report['active_offers']} offers | {report['total_leads']} leads | "
        f"{report['today_new_matches']} new matches | "
        f"${report['earned_total']:.2f} earned\n"
        f"Top 5:\n{top5_block}"
    )
    if _slack_post_bot(msg, channel=SLACK_CH_BROKER):
        log.info("  Slack report sent via bot token.")
    else:
        log.error("  Slack report failed.")


# ===========================================================================
# EMAIL SENDER
# ===========================================================================

EMAIL_SIGNATURE_HTML = """
<div style="margin-top:24px;padding-top:16px;border-top:1px solid #e0e0e0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#555;">
  <table cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td style="padding-right:16px;border-right:2px solid #d4a017;">
        <img src="https://everlightventures.io/favicon.ico" alt="EV" width="48" height="48" style="border-radius:8px;" />
      </td>
      <td style="padding-left:16px;">
        <div style="font-size:15px;font-weight:bold;color:#1a1a1a;">{agent_name}</div>
        <div style="font-size:12px;color:#888;margin-bottom:4px;">{agent_title}</div>
        <div style="font-size:12px;">
          <a href="https://everlightventures.io" style="color:#d4a017;text-decoration:none;">everlightventures.io</a>
          &nbsp;|&nbsp;
          <a href="mailto:{agent_email}" style="color:#d4a017;text-decoration:none;">{agent_email}</a>
        </div>
      </td>
    </tr>
  </table>
  <div style="margin-top:12px;font-size:11px;color:#999;">
    Everlight Ventures &mdash; AI-Powered Business Solutions<br/>
    This email was sent to {{{{to_email}}}}. If you no longer wish to receive these emails,
    <a href="mailto:{unsub_email}?subject=unsubscribe" style="color:#999;">click here to unsubscribe</a>.
  </div>
</div>
"""


def _build_html_email(body_text, agent_name="Sage Holloway", agent_title="Business Development",
                      agent_email="sage@everlightventures.io", to_email=""):
    """Convert plain text body to HTML email with professional signature."""
    # Convert plain text body to HTML paragraphs
    body_html = "".join(f"<p style='margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333;line-height:1.5;'>{line}</p>"
                        for line in body_text.strip().split("\n") if line.strip())

    sig = EMAIL_SIGNATURE_HTML.format(
        agent_name=agent_name,
        agent_title=agent_title,
        agent_email=agent_email,
        unsub_email=SMTP_FROM,
    ).replace("{{to_email}}", to_email)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;background:#fafafa;">
<div style="max-width:600px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;">
{body_html}
{sig}
</div></body></html>"""


def _send_email(to_email, subject, body, agent_name="Sage Holloway",
                agent_title="Business Development", agent_email="sage@everlightventures.io"):
    if not SMTP_PASS:
        log.warning("  SMTP_PASS not set. Skipping.")
        return False
    if not to_email or "@placeholder.io" in to_email:
        log.info(f"  Skipping invalid/placeholder email: {to_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{agent_name} at Everlight <{SMTP_FROM}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = agent_email
        msg["List-Unsubscribe"] = f"<mailto:{SMTP_FROM}?subject=unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Plain text fallback
        plain_footer = (
            f"\n\n---\n{agent_name} | {agent_title}\n"
            f"Everlight Ventures | everlightventures.io\n"
            f"{agent_email}\n\n"
            f"To unsubscribe, reply with 'unsubscribe'."
        )
        msg.attach(MIMEText(body + plain_footer, "plain"))

        # HTML version with branded signature
        html = _build_html_email(body, agent_name, agent_title, agent_email, to_email)
        msg.attach(MIMEText(html, "html"))

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            server.starttls()

        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        log.error(f"  Email failed to {to_email}: {e}")
        return False


# ===========================================================================
# STATUS SUBCOMMAND
# ===========================================================================

# Schedule definition for next-run calculation (hour in UTC)
SCHEDULE_UTC_HOURS = [0, 1, 3, 13, 15, 16, 17, 19, 21, 23]


def _get_last_run_time():
    """Check when orchestrator last ran from the daily JSON or log."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(LOG_DIR, f"daily_{today_str}.json")
    if os.path.exists(report_path):
        mtime = os.path.getmtime(report_path)
        return datetime.fromtimestamp(mtime)

    # Fall back to log file mtime
    log_path = os.path.join(LOG_DIR, "orchestrator.log")
    if os.path.exists(log_path):
        mtime = os.path.getmtime(log_path)
        return datetime.fromtimestamp(mtime)

    return None


def _get_next_run_time():
    """Calculate next scheduled run based on cron schedule."""
    from datetime import timezone as tz
    now_utc = datetime.now(tz.utc)
    current_hour = now_utc.hour
    current_minute = now_utc.minute

    # Find next scheduled hour today
    for h in sorted(SCHEDULE_UTC_HOURS):
        if h > current_hour or (h == current_hour and current_minute < 10):
            next_utc = now_utc.replace(hour=h, minute=0, second=0, microsecond=0)
            # Convert to PT (UTC-7 in March)
            next_pt = next_utc - timedelta(hours=7)
            return next_pt.strftime("%H:%M PT")

    # Wrap to tomorrow's first run
    tomorrow = now_utc + timedelta(days=1)
    first_hour = min(SCHEDULE_UTC_HOURS)
    next_utc = tomorrow.replace(hour=first_hour, minute=0, second=0, microsecond=0)
    next_pt = next_utc - timedelta(hours=7)
    return next_pt.strftime("%H:%M PT")


def step_status(send_slack=False):
    """Print a one-line status summary of Broker OS."""
    total_offers = OfferListing.objects.filter(status="active").count()
    total_leads = LeadProfile.objects.filter(unsubscribed=False).count()
    total_matches = BrokerMatch.objects.count()
    active_deals = Deal.objects.filter(stage__in=["active", "negotiating", "contracted"]).count()
    emails_today = get_emails_sent_today()

    last_run = _get_last_run_time()
    last_run_str = last_run.strftime("%Y-%m-%d %H:%M PT") if last_run else "never"
    next_run_str = _get_next_run_time()

    line = (
        f"Broker OS: {total_offers} offers | {total_leads} leads | "
        f"{total_matches} matches | {active_deals} deals | "
        f"{emails_today} emails today | "
        f"Last run: {last_run_str} | Next: {next_run_str}"
    )
    print(line)

    if send_slack:
        if _slack_post_bot(f"*{line}*", channel=SLACK_CH_WAR_ROOM):
            log.info("  Status sent to Slack.")
        else:
            log.error("  Slack status failed.")

    return line


# ===========================================================================
# CYCLE RUNNERS
# ===========================================================================

def run_full(args):
    """Full cycle -- all 10 steps."""
    step_scout_sellers(dry_run=args.dry_run)                         # 1
    step_scout_buyers(dry_run=args.dry_run)                          # 2
    step_enrich_emails(dry_run=args.dry_run)                         # 2b
    step_enrich_properties(dry_run=args.dry_run)                     # 2c
    step_sync_supabase(dry_run=args.dry_run)                         # 3
    step_expire_matches(dry_run=args.dry_run)                        # 3b
    step_match(min_score=args.min_score, dry_run=args.dry_run)       # 4
    step_auto_approve(dry_run=args.dry_run)                          # 4b
    step_create_sequences(dry_run=args.dry_run)                      # 5
    step_seller_outreach(dry_run=args.dry_run)                       # 6
    step_send_outreach(dry_run=args.dry_run)                         # 7
    step_auto_deals(dry_run=args.dry_run)                            # 8
    step_check_replies(dry_run=args.dry_run)                         # 8b
    report = step_report()                                           # 9
    if not args.dry_run:
        step_slack_report(report)                                    # 10

    # Log to workbooks
    if not args.dry_run and _WB_OK:
        try:
            _wb.log_agent_task("piper_reeves", "outreach", success=True,
                               count=report.get("emails_sent", 0) if isinstance(report, dict) else 0)
            _wb.log_agent_task("rex_blackwell", "scout", success=True,
                               count=report.get("leads_new", 0) if isinstance(report, dict) else 0)
            _wb.snapshot_daily()
            _wb.flush()
            _wb.sync_to_supabase()
        except Exception:
            pass
    return report


def run_scout(args):
    """Scout cycle -- steps 1-2 (find sellers + buyers + enrich)."""
    step_scout_sellers(dry_run=args.dry_run)
    step_scout_buyers(dry_run=args.dry_run)
    step_enrich_emails(dry_run=args.dry_run)


def run_sync(args):
    """Sync cycle -- step 3 (Supabase inbound forms)."""
    step_sync_supabase(dry_run=args.dry_run)


def run_match(args):
    """Match cycle -- steps 4-4b (matching + auto-approve)."""
    step_expire_matches(dry_run=args.dry_run)
    step_match(min_score=args.min_score, dry_run=args.dry_run)
    step_auto_approve(dry_run=args.dry_run)


def run_outreach(args):
    """Outreach cycle -- steps 5-8b (sequences + send emails + check replies)."""
    step_create_sequences(dry_run=args.dry_run)
    step_seller_outreach(dry_run=args.dry_run)
    step_send_outreach(dry_run=args.dry_run)
    step_check_replies(dry_run=args.dry_run)


def run_followup(args):
    """Follow-up cycle -- step 7 only (send due emails)."""
    step_send_outreach(dry_run=args.dry_run)


def run_report(args):
    """Report cycle -- steps 9-10 (daily report + Slack)."""
    report = step_report()
    if not args.dry_run:
        step_slack_report(report)
    return report


def run_status(args):
    """Status check -- quick 1-line summary."""
    step_status(send_slack=args.slack)


# ===========================================================================
# MAIN
# ===========================================================================

def run_replies(args):
    """Reply check -- step 8b only (check inbox for outreach replies)."""
    step_check_replies(dry_run=args.dry_run)


SUBCOMMAND_MAP = {
    "full": run_full,
    "scout": run_scout,
    "sync": run_sync,
    "match": run_match,
    "outreach": run_outreach,
    "followup": run_followup,
    "replies": run_replies,
    "report": run_report,
    "status": run_status,
}


def main():
    parser = argparse.ArgumentParser(
        description="Broker OS -- Fully Autonomous Multi-Cycle Orchestrator"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="full",
        choices=list(SUBCOMMAND_MAP.keys()),
        help="Subcommand to run (default: full)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview all actions")
    parser.add_argument("--min-score", type=float, default=60.0, help="Min match score (default: 60)")
    parser.add_argument("--slack", action="store_true", help="Send status to Slack (status subcommand only)")
    args = parser.parse_args()

    cmd = args.command

    # Status is lightweight -- no banner
    if cmd == "status":
        run_status(args)
        return

    log.info("=" * 60)
    log.info(f"BROKER OS -- {cmd.upper()} CYCLE")
    log.info("=" * 60)
    if args.dry_run:
        log.info("** DRY RUN **")

    record_event(
        event_type="broker.workflow.started",
        source="broker_daily_orchestrator",
        entity_type="workflow",
        entity_id=cmd,
        status="running",
        priority="high",
        owner_agent="23_automation_architect",
        summary=f"Broker {cmd} cycle started.",
        payload={
            "dry_run": args.dry_run,
            "min_score": args.min_score,
        },
    )

    try:
        result = SUBCOMMAND_MAP[cmd](args)
    except Exception as exc:
        log.exception("Broker cycle failed")
        failed_event = record_event(
            event_type="broker.workflow.failed",
            source="broker_daily_orchestrator",
            entity_type="workflow",
            entity_id=cmd,
            status="failed",
            priority="critical",
            owner_agent="23_automation_architect",
            summary=f"Broker {cmd} cycle failed: {exc}",
            payload={
                "dry_run": args.dry_run,
                "min_score": args.min_score,
            },
        )
        record_alert(
            summary=f"Broker {cmd} cycle failed",
            source="broker_daily_orchestrator",
            detail=str(exc),
            severity="error",
            alert_key=f"broker:{cmd}:failure",
            entity_type="workflow",
            entity_id=cmd,
            related_event=failed_event,
        )
        raise

    record_event(
        event_type="broker.workflow.completed",
        source="broker_daily_orchestrator",
        entity_type="workflow",
        entity_id=cmd,
        status="success",
        priority="high",
        owner_agent="23_automation_architect",
        summary=f"Broker {cmd} cycle completed.",
        payload={
            "dry_run": args.dry_run,
            "min_score": args.min_score,
        },
    )

    log.info("=" * 60)
    log.info(f"{cmd.upper()} CYCLE COMPLETE")
    log.info("=" * 60)

    return result


if __name__ == "__main__":
    main()
