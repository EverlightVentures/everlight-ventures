#!/usr/bin/env python3
"""
Broker OS - Lead & Offer Ingest Pipeline

Sources (ToS-compliant only):
  SELLERS (offers):
    - Product Hunt API (public, free tier, 10 req/s)
    - IndieHackers RSS feed
    - Hacker News "Show HN" RSS

  BUYERS (leads):
    - Inbound email parsed from mailbox / Gmail label
    - Manual CSV drop in 07_STAGING/Inbox/
    - Webhook from funnel forms (Django funnel app)

Usage:
  python broker_ingest.py --source product_hunt --limit 50
  python broker_ingest.py --source indiehackers --limit 30
  python broker_ingest.py --source hn_show --limit 20
  python broker_ingest.py --source csv --file /path/to/leads.csv --mode leads
  python broker_ingest.py --source all

Outputs: POSTs to Django broker_ops ingest API at DJANGO_BASE_URL.
"""
import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests

# Add broker scripts to path for enrichment module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "broker"))
try:
    from contact_enrichment import enrich_contact
except ImportError:
    enrich_contact = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("broker_ingest")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DJANGO_BASE_URL = os.environ.get("DJANGO_BASE_URL", "http://127.0.0.1:8502")
INGEST_LEAD_URL  = f"{DJANGO_BASE_URL}/broker/api/ingest/lead/"
INGEST_OFFER_URL = f"{DJANGO_BASE_URL}/broker/api/ingest/offer/"
STAGING_INBOX    = "/mnt/sdcard/AA_MY_DRIVE/07_STAGING/Inbox"

# Product Hunt (public GraphQL - no auth required for public posts)
PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"
PH_API_TOKEN   = os.environ.get("PRODUCT_HUNT_API_TOKEN", "")

# Keyword filters for AI/SaaS relevance
RELEVANT_KEYWORDS = [
    "ai", "saas", "automation", "workflow", "api", "agent", "gpt",
    "productivity", "analytics", "dashboard", "crm", "integration",
    "stripe", "supabase", "django", "python", "no-code", "low-code",
    "fintech", "compliance", "b2b", "startup"
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in RELEVANT_KEYWORDS)


def post_offer(payload: dict) -> bool:
    try:
        r = requests.post(INGEST_OFFER_URL, json=payload, timeout=10)
        if r.status_code == 200:
            log.info(f"  -> Offer saved: {payload.get('title', '?')[:50]}")
            return True
        log.warning(f"  -> Offer rejected ({r.status_code}): {r.text[:100]}")
    except Exception as e:
        log.error(f"  -> Offer POST failed: {e}")
    return False


def post_lead(payload: dict) -> bool:
    try:
        r = requests.post(INGEST_LEAD_URL, json=payload, timeout=10)
        if r.status_code == 200:
            log.info(f"  -> Lead saved: {payload.get('name', '?')[:50]}")
            return True
        log.warning(f"  -> Lead rejected ({r.status_code}): {r.text[:100]}")
    except Exception as e:
        log.error(f"  -> Lead POST failed: {e}")
    return False


# ---------------------------------------------------------------------------
# Source: Product Hunt (public GraphQL)
# ---------------------------------------------------------------------------

PH_QUERY = """
query($after: String, $first: Int!) {
  posts(order: VOTES, after: $after, first: $first) {
    pageInfo { endCursor hasNextPage }
    edges {
      node {
        id name tagline description url
        topics { edges { node { name } } }
        votesCount
        website
        user { name profileImage twitterUsername }
      }
    }
  }
}
"""


def ingest_product_hunt(limit: int = 50) -> int:
    if not PH_API_TOKEN:
        log.warning("PRODUCT_HUNT_API_TOKEN not set. Skipping Product Hunt ingest.")
        log.info("Get a free token at https://www.producthunt.com/v2/oauth/applications")
        return 0

    headers = {"Authorization": f"Bearer {PH_API_TOKEN}", "Content-Type": "application/json"}
    saved = 0
    after = None

    while saved < limit:
        batch = min(20, limit - saved)
        variables = {"first": batch, "after": after}
        try:
            resp = requests.post(PH_GRAPHQL_URL, json={"query": PH_QUERY, "variables": variables},
                                  headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            log.error(f"Product Hunt API error: {e}")
            break

        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        if not edges:
            break

        for edge in edges:
            node = edge["node"]
            combined = f"{node['name']} {node['tagline']} {node.get('description','')}"
            if not is_relevant(combined):
                continue

            topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
            keywords = topics + [w for w in node["tagline"].lower().split() if len(w) > 3]

            # Try to enrich contact from PH user data + website
            seller_name = node["user"]["name"] if node.get("user") else node["name"]
            seller_email = ""
            seller_website = node.get("website", "")
            notes_parts = [f"PH votes: {node.get('votesCount', 0)}. Auto-ingested."]

            if enrich_contact and node.get("user"):
                contact = enrich_contact(
                    source="product_hunt",
                    author=seller_name,
                    profile_data=node.get("user", {}),
                )
                seller_email = contact.get("email", "")
                if contact.get("twitter"):
                    notes_parts.append(f"twitter:@{contact['twitter']}")
                if not seller_email:
                    notes_parts.append("[NEEDS_ENRICHMENT]")

            payload = {
                "seller_name":    seller_name,
                "seller_email":   seller_email,
                "title":          node["name"],
                "category":       _guess_category(combined),
                "description":    f"{node['tagline']}. {node.get('description','')[:500]}",
                "keywords":       list(set(keywords))[:20],
                "price_min":      0,
                "price_max":      0,
                "pricing_model":  "monthly",
                "commission_pct": 20.0,
                "status":         "draft",
                "source":         "product_hunt",
                "source_url":     node.get("url", seller_website),
                "notes":          " | ".join(notes_parts),
            }
            if post_offer(payload):
                saved += 1
            time.sleep(0.1)

        page_info = data.get("data", {}).get("posts", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        after = page_info["endCursor"]

    log.info(f"Product Hunt: {saved} offers ingested")
    return saved


# ---------------------------------------------------------------------------
# Source: IndieHackers RSS
# ---------------------------------------------------------------------------

def ingest_indiehackers(limit: int = 30) -> int:
    try:
        import xml.etree.ElementTree as ET
        RSS_URL = "https://www.indiehackers.com/feed.xml"
        resp = requests.get(RSS_URL, timeout=15)
        root = ET.fromstring(resp.text)
    except Exception as e:
        log.error(f"IndieHackers RSS error: {e}")
        return 0

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)
    saved = 0

    for item in items[:limit]:
        title_el = item.find("title") or item.find("atom:title", ns)
        link_el  = item.find("link")  or item.find("atom:link", ns)
        desc_el  = item.find("description") or item.find("atom:summary", ns)

        title = title_el.text if title_el is not None else ""
        link  = link_el.text or link_el.get("href", "") if link_el is not None else ""
        desc  = desc_el.text or "" if desc_el is not None else ""

        combined = f"{title} {desc}"
        if not is_relevant(combined):
            continue

        payload = {
            "seller_name":    "IndieHacker",
            "seller_email":   "",
            "title":          title[:200],
            "category":       _guess_category(combined),
            "description":    desc[:1000],
            "keywords":       [w for w in title.lower().split() if len(w) > 3][:15],
            "price_min":      0,
            "price_max":      0,
            "pricing_model":  "monthly",
            "commission_pct": 20.0,
            "status":         "draft",
            "source":         "indiehackers",
            "source_url":     link,
            "notes":          "[NEEDS_ENRICHMENT]",
        }
        if post_offer(payload):
            saved += 1
        time.sleep(0.05)

    log.info(f"IndieHackers: {saved} offers ingested")
    return saved


# ---------------------------------------------------------------------------
# Source: Hacker News "Show HN" (public Algolia API)
# ---------------------------------------------------------------------------

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def ingest_hn_show(limit: int = 20) -> int:
    params = {
        "query":  "Show HN saas ai automation",
        "tags":   "show_hn",
        "hitsPerPage": min(limit, 50),
    }
    try:
        resp = requests.get(HN_SEARCH_URL, params=params, timeout=15)
        hits = resp.json().get("hits", [])
    except Exception as e:
        log.error(f"HN API error: {e}")
        return 0

    saved = 0
    for hit in hits:
        title = hit.get("title", "")
        url   = hit.get("url", "")
        text  = hit.get("story_text", "") or ""
        combined = f"{title} {text}"

        if not is_relevant(combined):
            continue

        author = hit.get("author", "HN User")
        seller_email = ""
        notes_parts = [f"HN points: {hit.get('points', 0)}"]

        if enrich_contact and author:
            contact = enrich_contact(source="hacker_news", username=author)
            seller_email = contact.get("email", "")
            if contact.get("profile_url"):
                notes_parts.append(f"profile:{contact['profile_url']}")
            if contact.get("website"):
                notes_parts.append(f"website:{contact['website']}")
            if contact.get("twitter"):
                notes_parts.append(f"twitter:@{contact['twitter']}")
            if not seller_email:
                notes_parts.append("[NEEDS_ENRICHMENT]")

        payload = {
            "seller_name":    author,
            "seller_email":   seller_email,
            "title":          title[:200],
            "category":       _guess_category(combined),
            "description":    text[:500] or title,
            "keywords":       [w for w in title.lower().split() if len(w) > 3][:15],
            "price_min":      0,
            "price_max":      0,
            "pricing_model":  "monthly",
            "commission_pct": 20.0,
            "status":         "draft",
            "source":         "hn_show",
            "source_url":     url,
            "notes":          " | ".join(notes_parts),
        }
        if post_offer(payload):
            saved += 1
        time.sleep(0.05)

    log.info(f"HN Show: {saved} offers ingested")
    return saved


# ---------------------------------------------------------------------------
# Source: CSV drop (leads or offers)
# ---------------------------------------------------------------------------

def ingest_csv(filepath: str, mode: str = "leads") -> int:
    saved = 0
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()}
                if mode == "leads":
                    payload = {
                        "name":             row.get("name", ""),
                        "email":            row.get("email", ""),
                        "company":          row.get("company", ""),
                        "role":             row.get("role", ""),
                        "need_description": row.get("need_description") or row.get("notes", ""),
                        "categories_needed": [row.get("category", "ai_saas")] if row.get("category") else [],
                        "budget_min":       float(row.get("budget_min", 0) or 0),
                        "budget_max":       float(row.get("budget_max", 0) or 0),
                        "intent":           row.get("intent", "warm"),
                        "lead_source":      row.get("lead_source", "direct"),
                        "raw_data":         row,
                    }
                    if payload["name"] or payload["email"]:
                        if post_lead(payload):
                            saved += 1
                else:
                    payload = {
                        "seller_name":    row.get("seller_name", ""),
                        "seller_email":   row.get("seller_email", ""),
                        "title":          row.get("title", ""),
                        "category":       row.get("category", "ai_saas"),
                        "description":    row.get("description", ""),
                        "keywords":       row.get("keywords", "").split(",") if row.get("keywords") else [],
                        "price_min":      float(row.get("price_min", 0) or 0),
                        "price_max":      float(row.get("price_max", 0) or 0),
                        "commission_pct": float(row.get("commission_pct", 20) or 20),
                        "status":         "active",
                        "source":         "direct",
                    }
                    if payload["title"] and payload["seller_email"]:
                        if post_offer(payload):
                            saved += 1
    except Exception as e:
        log.error(f"CSV ingest error: {e}")

    log.info(f"CSV ({mode}): {saved} records ingested from {filepath}")
    return saved


# ---------------------------------------------------------------------------
# Category guesser
# ---------------------------------------------------------------------------

def _guess_category(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["fintech", "compliance", "stripe", "payment", "bank", "crypto", "supabase"]):
        return "fintech"
    if any(k in t for k in ["health", "hipaa", "clinic", "medical", "patient"]):
        return "healthtech"
    if any(k in t for k in ["marketing", "seo", "social", "content", "email"]):
        return "marketing"
    if any(k in t for k in ["logistic", "shipping", "supply", "fulfillment"]):
        return "logistics"
    if any(k in t for k in ["ai", "gpt", "agent", "llm", "automation", "saas"]):
        return "ai_saas"
    if any(k in t for k in ["dev", "api", "backend", "frontend", "code"]):
        return "dev_service"
    return "other"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Broker OS ingest pipeline")
    parser.add_argument("--source", default="all",
                        choices=["product_hunt", "indiehackers", "hn_show", "csv", "all"],
                        help="Which source to ingest")
    parser.add_argument("--limit", type=int, default=50, help="Max records per source")
    parser.add_argument("--file",  default="",   help="CSV file path (for --source csv)")
    parser.add_argument("--mode",  default="leads", choices=["leads","offers"],
                        help="CSV mode: leads or offers")
    args = parser.parse_args()

    total = 0
    if args.source in ("product_hunt", "all"):
        total += ingest_product_hunt(args.limit)
    if args.source in ("indiehackers", "all"):
        total += ingest_indiehackers(args.limit)
    if args.source in ("hn_show", "all"):
        total += ingest_hn_show(args.limit)
    if args.source == "csv":
        if not args.file:
            log.error("--file required for csv source")
            sys.exit(1)
        total += ingest_csv(args.file, args.mode)

    log.info(f"Total records ingested this run: {total}")


if __name__ == "__main__":
    main()
