#!/usr/bin/env python3
"""
Lead Enrichment Pipeline -- Scrapy + Trafilatura + spaCy + LeadScorer

Scrapes each new lead's website, extracts key info with NLP,
and feeds it to the ML LeadScorer for better predictions.

Cron: 0 */4 * * * cd /home/opc && source .env && python3 lead_enrichment.py >> /tmp/lead_enrichment.log 2>&1
"""
import json
import logging
import os
import sys
import time
from datetime import datetime

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
sys.path.insert(0, "/home/opc/hive_django")
sys.path.insert(0, "/home/opc/06_DEVELOPMENT/everlight_os/neuromorphic")

import django
django.setup()

from broker_ops.models import LeadProfile
from django.utils import timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lead_enrichment")

# Slack notification
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("SLACK_ENRICHMENT_CHANNEL", "C0AN4GSTMT5")


def enrich_lead(lead):
    """Enrich a single lead with web scraping + NLP + ML scoring."""
    result = {"lead_id": lead.id, "name": lead.name, "enriched": False}

    # Step 1: Scrape website with Trafilatura (lightweight, no browser)
    website_text = ""
    source_url = lead.source_url or ""
    if source_url and source_url.startswith("http"):
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(source_url)
            if downloaded:
                website_text = trafilatura.extract(downloaded) or ""
                result["website_chars"] = len(website_text)
                log.info(f"  Scraped {source_url}: {len(website_text)} chars")
        except Exception as e:
            log.warning(f"  Scrape failed for {source_url}: {e}")

    # Step 2: NLP analysis with spaCy
    analysis = {}
    text_to_analyze = f"{lead.name} {lead.company or ''} {lead.need_description or ''} {website_text[:2000]}"
    try:
        from nlp_engine import analyze_text, extract_lead_features
        analysis = analyze_text(text_to_analyze).to_dict()
        features = extract_lead_features(text_to_analyze)
        result["nlp"] = {
            "sentiment": analysis.get("sentiment_label"),
            "organizations": analysis.get("organizations", []),
            "is_interested": analysis.get("is_interested"),
            "urgency": analysis.get("urgency_score"),
            "key_phrases": analysis.get("key_phrases", [])[:5],
        }
    except Exception as e:
        log.warning(f"  NLP failed: {e}")
        features = {}

    # Step 3: ML scoring
    try:
        from ml_models import get_toolkit
        toolkit = get_toolkit()
        ml_score = toolkit.score_lead(features)
        result["ml_score"] = round(ml_score, 1)
    except Exception as e:
        log.warning(f"  ML scoring failed: {e}")
        ml_score = None

    # Step 4: Update lead in Django
    enrichment_data = {
        "enriched_at": datetime.utcnow().isoformat(),
        "website_text_length": len(website_text),
        "nlp_sentiment": analysis.get("sentiment_label", ""),
        "nlp_organizations": analysis.get("organizations", []),
        "nlp_key_phrases": analysis.get("key_phrases", [])[:5],
        "ml_score": ml_score,
    }

    # Store in lead's raw_data JSON field
    existing_raw = {}
    if lead.raw_data:
        try:
            existing_raw = json.loads(lead.raw_data) if isinstance(lead.raw_data, str) else lead.raw_data
        except Exception:
            existing_raw = {}

    existing_raw["enrichment"] = enrichment_data
    lead.raw_data = json.dumps(existing_raw, default=str)
    lead.save(update_fields=["raw_data", "updated_at"])

    result["enriched"] = True
    return result


def run_enrichment(limit=20):
    """Enrich leads that haven't been enriched yet."""
    log.info("=== LEAD ENRICHMENT PIPELINE ===")

    # Find leads without enrichment data
    leads = LeadProfile.objects.all().order_by("-created_at")[:200]

    unenriched = []
    for lead in leads:
        raw = {}
        if lead.raw_data:
            try:
                raw = json.loads(lead.raw_data) if isinstance(lead.raw_data, str) else (lead.raw_data or {})
            except Exception:
                raw = {}
        if "enrichment" not in raw:
            unenriched.append(lead)

    log.info(f"Found {len(unenriched)} unenriched leads (of {leads.count()} total)")

    results = []
    for lead in unenriched[:limit]:
        log.info(f"Enriching: {lead.name} ({lead.email})")
        try:
            r = enrich_lead(lead)
            results.append(r)
        except Exception as e:
            log.error(f"  Failed: {e}")
            results.append({"lead_id": lead.id, "error": str(e)})
        time.sleep(1)  # Rate limit

    enriched = sum(1 for r in results if r.get("enriched"))
    log.info(f"Enriched {enriched}/{len(results)} leads")

    # Slack notification
    if enriched > 0 and SLACK_TOKEN:
        try:
            import urllib.request
            msg = f"Lead Enrichment: {enriched} leads scraped + scored"
            top = [r for r in results if r.get("ml_score")]
            if top:
                top.sort(key=lambda x: x.get("ml_score", 0), reverse=True)
                msg += f"\nTop: {top[0]['name']} (score: {top[0]['ml_score']})"

            req = urllib.request.Request(
                "https://slack.com/api/chat.postMessage",
                data=json.dumps({"channel": SLACK_CHANNEL, "text": msg}).encode(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {SLACK_TOKEN}"},
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    return results


if __name__ == "__main__":
    run_enrichment(limit=20)
