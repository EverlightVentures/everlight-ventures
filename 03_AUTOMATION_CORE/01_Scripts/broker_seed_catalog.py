#!/usr/bin/env python3
"""
Broker OS - Seed Catalog

Populates the OfferListing table directly via Django ORM.
Sources: CSV file + live scout APIs (HN, GitHub, DEV.to).

Usage:
    python3 broker_seed_catalog.py --csv starter_offers.csv
    python3 broker_seed_catalog.py --scout
    python3 broker_seed_catalog.py --csv starter_offers.csv --scout
"""
import argparse
import csv
import json
import logging
import os
import sys
import urllib.request

# Django bootstrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "09_DASHBOARD", "hive_dashboard"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django
django.setup()

from broker_ops.models import OfferListing

logging.basicConfig(level=logging.INFO, format="[SEED] %(message)s")
log = logging.getLogger(__name__)

CATEGORY_MAP = {
    "ai": "ai_saas", "saas": "ai_saas", "ml": "ai_saas", "automation": "ai_saas",
    "llm": "ai_saas", "chatbot": "ai_saas", "gpt": "ai_saas",
    "dev": "dev_service", "api": "dev_service", "devtool": "dev_service",
    "cli": "dev_service", "sdk": "dev_service", "database": "dev_service",
    "fintech": "fintech", "payment": "fintech", "crypto": "fintech",
    "health": "healthtech", "medical": "healthtech",
    "marketing": "marketing", "seo": "marketing", "analytics": "marketing",
    "logistics": "logistics", "shipping": "logistics", "ops": "logistics",
}


def guess_category(text):
    text_lower = text.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in text_lower:
            return cat
    return "ai_saas"


def extract_keywords(text, max_kw=8):
    stops = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "is", "it",
             "with", "on", "at", "by", "from", "your", "that", "this", "are", "was",
             "be", "has", "had", "have", "not", "but"}
    words = [w.strip(".,!?()[]{}\"'").lower() for w in text.split()]
    return list(dict.fromkeys(w for w in words if len(w) > 2 and w not in stops))[:max_kw]


def seed_from_csv(csv_path):
    """Load offers from a CSV file with columns: title, seller_name, seller_email, seller_url, description, category, price_min, price_max, pricing_model, keywords"""
    if not os.path.exists(csv_path):
        log.error(f"CSV not found: {csv_path}")
        return 0

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            seller_email = row.get("seller_email", "").strip()
            if not title:
                continue

            keywords = row.get("keywords", "")
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]

            obj, created = OfferListing.objects.update_or_create(
                title=title,
                seller_email=seller_email or "unknown@example.com",
                defaults={
                    "seller_name": row.get("seller_name", "Unknown"),
                    "seller_url": row.get("seller_url", ""),
                    "description": row.get("description", title),
                    "category": row.get("category", guess_category(title)),
                    "price_min": float(row.get("price_min", 0)),
                    "price_max": float(row.get("price_max", 0)),
                    "pricing_model": row.get("pricing_model", "monthly"),
                    "keywords": keywords,
                    "source": "csv_seed",
                    "status": "active",
                }
            )
            action = "Created" if created else "Updated"
            log.info(f"  {action}: {title}")
            count += 1

    log.info(f"CSV seed complete: {count} offers")
    return count


def scout_hn(limit=15):
    """Fetch Show HN posts about SaaS/tools from HN Algolia API."""
    url = "https://hn.algolia.com/api/v1/search?query=Show%20HN%20SaaS&tags=show_hn&hitsPerPage=" + str(limit)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EverLight-BrokerOS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log.warning(f"HN scout failed: {e}")
        return 0

    count = 0
    for hit in data.get("hits", []):
        title = hit.get("title", "")
        if not title or "Show HN" not in title:
            continue
        clean_title = title.replace("Show HN: ", "").replace("Show HN:", "").strip()
        story_url = hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

        obj, created = OfferListing.objects.update_or_create(
            title=clean_title[:300],
            seller_email=f"hn-{hit.get('objectID', 'unknown')}@placeholder.io",
            defaults={
                "seller_name": hit.get("author", "HN Builder"),
                "seller_url": story_url,
                "description": clean_title,
                "category": guess_category(clean_title),
                "keywords": extract_keywords(clean_title),
                "source": "hacker_news",
                "source_url": story_url,
                "status": "active",
                "price_min": 0,
                "price_max": 0,
                "pricing_model": "monthly",
            }
        )
        if created:
            count += 1
            log.info(f"  HN: {clean_title[:60]}")

    log.info(f"HN scout: {count} new offers")
    return count


def scout_github(limit=15):
    """Fetch trending repos related to SaaS tools from GitHub Search API."""
    url = f"https://api.github.com/search/repositories?q=saas+tool+created:>2026-01-01&sort=stars&order=desc&per_page={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EverLight-BrokerOS/1.0", "Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log.warning(f"GitHub scout failed: {e}")
        return 0

    count = 0
    for repo in data.get("items", []):
        name = repo.get("name", "")
        desc = repo.get("description", "") or name
        owner = repo.get("owner", {})

        obj, created = OfferListing.objects.update_or_create(
            title=name[:300],
            seller_email=f"gh-{owner.get('login', 'unknown')}@placeholder.io",
            defaults={
                "seller_name": owner.get("login", "GitHub Builder"),
                "seller_url": repo.get("html_url", ""),
                "description": desc[:500],
                "category": guess_category(desc),
                "keywords": extract_keywords(f"{name} {desc}"),
                "source": "github",
                "source_url": repo.get("html_url", ""),
                "status": "active",
                "price_min": 0,
                "price_max": 0,
                "pricing_model": "monthly",
            }
        )
        if created:
            count += 1
            log.info(f"  GH: {name[:60]}")

    log.info(f"GitHub scout: {count} new offers")
    return count


def scout_devto(limit=15):
    """Fetch recent SaaS-related articles from DEV.to."""
    url = f"https://dev.to/api/articles?tag=saas&per_page={limit}&top=7"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EverLight-BrokerOS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log.warning(f"DEV.to scout failed: {e}")
        return 0

    count = 0
    for article in data:
        title = article.get("title", "")
        if not title:
            continue

        obj, created = OfferListing.objects.update_or_create(
            title=title[:300],
            seller_email=f"devto-{article.get('id', 'unknown')}@placeholder.io",
            defaults={
                "seller_name": article.get("user", {}).get("name", "DEV.to Author"),
                "seller_url": article.get("url", ""),
                "description": article.get("description", title)[:500],
                "category": guess_category(title),
                "keywords": extract_keywords(title),
                "source": "devto",
                "source_url": article.get("url", ""),
                "status": "active",
                "price_min": 0,
                "price_max": 0,
                "pricing_model": "monthly",
            }
        )
        if created:
            count += 1
            log.info(f"  DEV: {title[:60]}")

    log.info(f"DEV.to scout: {count} new offers")
    return count


def main():
    parser = argparse.ArgumentParser(description="Seed Broker OS offer catalog")
    parser.add_argument("--csv", help="Path to starter offers CSV")
    parser.add_argument("--scout", action="store_true", help="Run live scouts (HN, GitHub, DEV.to)")
    parser.add_argument("--limit", type=int, default=15, help="Max results per scout source")
    args = parser.parse_args()

    if not args.csv and not args.scout:
        parser.print_help()
        print("\nAt least one of --csv or --scout required.")
        sys.exit(1)

    total = 0

    if args.csv:
        log.info(f"Seeding from CSV: {args.csv}")
        total += seed_from_csv(args.csv)

    if args.scout:
        log.info("Running live scouts...")
        total += scout_hn(args.limit)
        total += scout_github(args.limit)
        total += scout_devto(args.limit)

    before = OfferListing.objects.filter(status="active").count()
    log.info(f"\nDone. {total} offers processed. Total active offers in DB: {before}")


if __name__ == "__main__":
    main()
