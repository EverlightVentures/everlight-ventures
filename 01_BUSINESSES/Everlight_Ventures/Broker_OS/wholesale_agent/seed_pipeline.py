"""
One-time pipeline seeder + ongoing enrichment tool.

Usage:
    python seed_pipeline.py               # Enrich existing Django leads
    python seed_pipeline.py --scout       # Run full scout + enrich + skip trace
    python seed_pipeline.py --buyers      # Import buyers from a CSV
    python seed_pipeline.py --export-only # Just export Django leads to leads_db.json
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="[SeedPipeline %(asctime)s] %(message)s",
    datefmt="%H:%M",
)
log = logging.getLogger("seed_pipeline")

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

AGENT_DIR = Path(__file__).parent
LEADS_DB_PATH = AGENT_DIR / "leads_db.json"
DJANGO_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Ensure output dirs
for d in ["pipeline", "skip_traces"]:
    (AGENT_DIR / d).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# DJANGO BOOTSTRAP
# ---------------------------------------------------------------------------

def setup_django():
    """Wire up Django ORM so we can query PropertyLead directly."""
    sys.path.insert(0, str(DJANGO_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

    import django
    django.setup()


# ---------------------------------------------------------------------------
# SKIP TRACE -- TruePeopleSearch
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

JUNK_EMAIL_DOMAINS = [
    "truepeoplesearch", "fastpeoplesearch", "example", "sentry",
    "google", "facebook", "gstatic", "googleapis", "w3.org",
    "schema.org", "jquery", "cloudflare", "cdn", "bootstrap",
    "zillow", "trulia", "zillowstatic",
]

MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.6261.64 Mobile Safari/537.36"
)


def skip_trace_person(owner_name: str, city: str, state: str) -> dict:
    """
    Hit TruePeopleSearch for an owner name + city/state.
    Returns {"phones": [...], "emails": [...], "source": "..."}.
    """
    import requests

    result = {"phones": [], "emails": [], "source": "none"}

    if not owner_name or not owner_name.strip():
        return result

    # Skip generic placeholders
    lower = owner_name.lower()
    if lower.startswith("owner at") or lower in ("unknown", "n/a", ""):
        return result

    name_parts = owner_name.strip().split()
    if len(name_parts) < 2:
        return result

    search_url = (
        f"https://www.truepeoplesearch.com/results"
        f"?name={quote(owner_name)}"
        f"&citystatezip={quote(f'{city}, {state}')}"
    )

    headers = {"User-Agent": MOBILE_UA}

    try:
        resp = requests.get(search_url, headers=headers, timeout=12)
        if resp.status_code != 200:
            log.debug(f"  TPS returned {resp.status_code} for {owner_name}")
            return result

        html = resp.text

        # Extract phone numbers -- 10-digit US numbers only
        raw_phones = PHONE_RE.findall(html)
        clean_phones = []
        for p in raw_phones:
            digits = re.sub(r"\D", "", p)
            if len(digits) == 10:
                formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                if formatted not in clean_phones:
                    clean_phones.append(formatted)
        result["phones"] = clean_phones[:3]

        # Extract email addresses -- filter out site/junk domains
        raw_emails = EMAIL_RE.findall(html)
        clean_emails = []
        for e in raw_emails:
            e_lower = e.lower()
            if any(junk in e_lower for junk in JUNK_EMAIL_DOMAINS):
                continue
            if e_lower.endswith((".png", ".jpg", ".svg", ".css", ".js")):
                continue
            if e_lower not in [x.lower() for x in clean_emails]:
                clean_emails.append(e)
        result["emails"] = clean_emails[:3]

        if result["phones"] or result["emails"]:
            result["source"] = "truepeoplesearch"

    except requests.exceptions.Timeout:
        log.debug(f"  TPS timeout for {owner_name}")
    except Exception as exc:
        log.debug(f"  TPS error for {owner_name}: {exc}")

    return result


# ---------------------------------------------------------------------------
# PART 1: ENRICH EXISTING DJANGO LEADS
# ---------------------------------------------------------------------------

def enrich_django_leads() -> dict:
    """
    Query PropertyLead records that lack email, attempt skip trace,
    update Django records in place.
    """
    setup_django()
    from broker_ops.models import PropertyLead

    # Get leads without email
    leads_no_email = PropertyLead.objects.filter(owner_email="")
    total = leads_no_email.count()
    all_leads = PropertyLead.objects.all().count()

    log.info(f"Django has {all_leads} total PropertyLead records")
    log.info(f"{total} leads have no email -- starting enrichment")

    enriched = 0
    emails_found = 0
    phones_found = 0
    skipped = 0

    for lead in leads_no_email:
        if not lead.owner_name or not lead.owner_name.strip():
            skipped += 1
            log.info(f"  SKIP (no owner name): {lead.address}")
            continue

        log.info(f"  Tracing: {lead.owner_name} -- {lead.city}, {lead.state}")
        trace = skip_trace_person(lead.owner_name, lead.city, lead.state)

        updated = False

        if trace["emails"]:
            lead.owner_email = trace["emails"][0]
            emails_found += 1
            updated = True
            log.info(f"    EMAIL FOUND: {trace['emails'][0]}")

        if trace["phones"] and not lead.owner_phone:
            lead.owner_phone = trace["phones"][0]
            phones_found += 1
            updated = True
            log.info(f"    PHONE FOUND: {trace['phones'][0]}")

        if updated:
            lead.save(update_fields=["owner_email", "owner_phone", "updated_at"])
            enriched += 1

            # Save trace to file for audit trail
            trace_path = AGENT_DIR / "skip_traces" / f"{TODAY}_{lead.owner_name.replace(' ', '_')}.json"
            with open(trace_path, "w") as f:
                json.dump({
                    "owner_name": lead.owner_name,
                    "address": lead.address,
                    "city": lead.city,
                    "state": lead.state,
                    "trace_result": trace,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)

        # Rate limit -- 3 seconds between requests
        time.sleep(3)

    summary = {
        "total_leads": all_leads,
        "leads_without_email": total,
        "skipped_no_name": skipped,
        "enriched": enriched,
        "emails_found": emails_found,
        "phones_found": phones_found,
    }

    log.info("=" * 50)
    log.info(f"Enrichment complete:")
    log.info(f"  {enriched} leads enriched")
    log.info(f"  {emails_found} emails found")
    log.info(f"  {phones_found} phones found")
    log.info(f"  {skipped} skipped (no owner name)")
    log.info("=" * 50)

    return summary


# ---------------------------------------------------------------------------
# PART 2: EXPORT TO SDR leads_db.json
# ---------------------------------------------------------------------------

def export_to_sdr_db() -> int:
    """
    Export all PropertyLead records that have owner_email
    into the SDR's leads_db.json format.
    Merges with any existing leads_db.json without duplicating.
    """
    setup_django()
    from broker_ops.models import PropertyLead

    leads_with_email = PropertyLead.objects.exclude(owner_email="")
    count = leads_with_email.count()

    log.info(f"Exporting {count} leads with email to {LEADS_DB_PATH}")

    # Load existing leads_db.json to merge
    existing = []
    existing_addrs = set()
    if LEADS_DB_PATH.exists():
        try:
            existing = json.loads(LEADS_DB_PATH.read_text())
            existing_addrs = {l.get("address", "").lower() for l in existing}
        except (json.JSONDecodeError, KeyError):
            existing = []

    added = 0
    for lead in leads_with_email:
        if lead.address.lower() in existing_addrs:
            # Update existing entry with new email/phone if we have it
            for ex in existing:
                if ex.get("address", "").lower() == lead.address.lower():
                    if lead.owner_email and not ex.get("owner_email"):
                        ex["owner_email"] = lead.owner_email
                    if lead.owner_phone and not ex.get("owner_phone"):
                        ex["owner_phone"] = lead.owner_phone
                    break
            continue

        entry = {
            "address": lead.address,
            "city": lead.city,
            "state": lead.state,
            "zip_code": lead.zip_code,
            "owner_name": lead.owner_name,
            "owner_email": lead.owner_email,
            "owner_phone": lead.owner_phone,
            "asking_price": float(lead.asking_price),
            "arv": float(lead.estimated_arv),
            "lead_type": lead.lead_type,
            "motivation_score": lead.motivation_score,
            "status": "new",
            "outreach_count": 0,
            "last_outreach": "",
            "sequence_step": 0,
            "created_at": TODAY,
        }

        existing.append(entry)
        existing_addrs.add(lead.address.lower())
        added += 1

    LEADS_DB_PATH.write_text(json.dumps(existing, indent=2, default=str))

    log.info(f"  {added} new leads added to leads_db.json")
    log.info(f"  {len(existing)} total leads in leads_db.json")
    log.info(f"  SDR (rex_sdr.py) can now send emails")

    return added


# ---------------------------------------------------------------------------
# PART 3: HIGH-VOLUME SCOUT MODE
# ---------------------------------------------------------------------------

# Market rotation: Mon=0..Sun=6
DAILY_MARKET_ROTATION = {
    0: "atlanta",       # Monday
    1: "dallas",        # Tuesday
    2: "cleveland",     # Wednesday
    3: "charlotte",     # Thursday
    4: "st_louis",      # Friday
    5: "jacksonville",  # Saturday
    6: "jacksonville",  # Sunday
}

# Top 15 keywords -- the highest-conversion terms for wholesale
TOP_KEYWORDS = [
    "motivated seller", "as-is", "as is", "cash only",
    "investor special", "fixer upper", "needs work",
    "estate sale", "foreclosure", "code violation",
    "vacant", "handyman special", "distressed",
    "must sell", "below market",
]


def run_scout_mode() -> dict:
    """
    High-volume scout: pick today's market, search ALL zips x top keywords,
    enrich each listing from Zillow, skip trace every owner found,
    import to Django + leads_db.json.
    """
    import requests
    from rex_autonomous import fetch_zillow_listings, enrich_listing
    from zillow_scout import MARKETS

    setup_django()
    from broker_ops.models import PropertyLead

    # Pick today's market
    weekday = datetime.now(timezone.utc).weekday()
    market_key = DAILY_MARKET_ROTATION.get(weekday, "atlanta")
    market = MARKETS.get(market_key)
    if not market:
        log.error(f"Unknown market: {market_key}")
        return {}

    log.info("=" * 60)
    log.info(f"SCOUT MODE -- {market['name']} ({market_key})")
    log.info(f"Zips: {len(market['zips'])} | Keywords: {len(TOP_KEYWORDS)}")
    log.info(f"Max searches: {len(market['zips']) * len(TOP_KEYWORDS)}")
    log.info("=" * 60)

    all_zips = market["zips"]        # All 10
    keywords = TOP_KEYWORDS          # Top 15
    total_searches = len(all_zips) * len(keywords)

    leads_found = 0
    leads_enriched = 0
    emails_found = 0
    phones_found = 0
    leads_imported = 0
    seen_urls = set()

    search_count = 0

    for zip_code in all_zips:
        for keyword in keywords:
            search_count += 1
            log.info(f"[{search_count}/{total_searches}] {zip_code} / '{keyword}'")

            # Fetch listing URLs from Google
            raw_listings = fetch_zillow_listings(zip_code, keyword, max_results=5)
            if not raw_listings:
                # Rate limit between Google searches
                time.sleep(2)
                continue

            for raw in raw_listings:
                url = raw.get("listing_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Enrich from Zillow page
                log.info(f"  Enriching: {url[:80]}...")
                details = enrich_listing(url)
                time.sleep(3)  # Rate limit Zillow fetches

                address = details.get("address", raw.get("address_raw", ""))
                city = details.get("city", "")
                state = details.get("state", "")
                zip_c = details.get("zip_code", zip_code)

                if not address:
                    continue

                leads_found += 1

                # Check for duplicate in Django
                existing = PropertyLead.objects.filter(
                    address__iexact=address,
                    city__iexact=city,
                    state__iexact=state,
                ).first()

                if existing:
                    log.info(f"    Already in Django: {address}")
                    # Still try to enrich if missing email
                    if not existing.owner_email and existing.owner_name:
                        trace = skip_trace_person(existing.owner_name, city, state)
                        time.sleep(3)
                        if trace["emails"]:
                            existing.owner_email = trace["emails"][0]
                            emails_found += 1
                        if trace["phones"] and not existing.owner_phone:
                            existing.owner_phone = trace["phones"][0]
                            phones_found += 1
                        if trace["emails"] or trace["phones"]:
                            existing.save(update_fields=["owner_email", "owner_phone", "updated_at"])
                            leads_enriched += 1
                    continue

                # Build PropertyLead
                asking = details.get("asking_price", 0)
                zestimate = details.get("zestimate", 0)
                kw_found = details.get("keywords_found", [])

                # Score motivation
                score = 0
                if kw_found:
                    score += len(kw_found) * 10
                dom = details.get("days_on_market", 0)
                if dom > 90:
                    score += 20
                elif dom > 60:
                    score += 15
                elif dom > 30:
                    score += 10
                if asking and zestimate and zestimate > 0:
                    discount_pct = (zestimate - asking) / zestimate * 100
                    if discount_pct > 20:
                        score += 25
                    elif discount_pct > 10:
                        score += 15
                score = min(score, 100)

                # Create Django record
                pl = PropertyLead(
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_c,
                    property_type=details.get("property_type", "sfr"),
                    bedrooms=details.get("beds", 0),
                    bathrooms=details.get("baths", 0),
                    sqft=details.get("sqft", 0),
                    year_built=details.get("year_built", 0),
                    asking_price=asking,
                    estimated_arv=zestimate,
                    lead_type="zillow",
                    motivation_score=score,
                    days_on_market=dom,
                    source="seed_pipeline_scout",
                    source_url=url,
                    zillow_url=url,
                    status="new",
                    raw_data={
                        "keywords_found": kw_found,
                        "keyword_searched": keyword,
                        "zip_searched": zip_code,
                        "scout_date": TODAY,
                    },
                )

                # Try to get owner name from Zillow description or address heuristic
                # (Zillow rarely exposes owner names, but sometimes in description)
                owner_name = details.get("owner_name", "")

                if owner_name:
                    pl.owner_name = owner_name
                    # Skip trace for contact info
                    log.info(f"    Skip tracing: {owner_name}")
                    trace = skip_trace_person(owner_name, city, state)
                    time.sleep(3)

                    if trace["emails"]:
                        pl.owner_email = trace["emails"][0]
                        emails_found += 1
                        log.info(f"    EMAIL: {trace['emails'][0]}")
                    if trace["phones"]:
                        pl.owner_phone = trace["phones"][0]
                        phones_found += 1
                        log.info(f"    PHONE: {trace['phones'][0]}")

                    leads_enriched += 1

                try:
                    pl.save()
                    leads_imported += 1
                    log.info(f"    IMPORTED: {address}, {city} {state} (score={score})")
                except Exception as exc:
                    log.warning(f"    Save failed for {address}: {exc}")

            # Rate limit between Google searches
            time.sleep(2)

    # After all scouting, export enriched leads to SDR
    exported = export_to_sdr_db()

    summary = {
        "market": market["name"],
        "market_key": market_key,
        "total_searches": total_searches,
        "searches_completed": search_count,
        "leads_found": leads_found,
        "leads_imported": leads_imported,
        "leads_enriched": leads_enriched,
        "emails_found": emails_found,
        "phones_found": phones_found,
        "exported_to_sdr": exported,
    }

    # Save summary
    summary_path = AGENT_DIR / "pipeline" / f"{TODAY}_scout_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Post to Slack
    post_scout_summary(summary)

    log.info("=" * 60)
    log.info(f"SCOUT COMPLETE -- {market['name']}")
    log.info(f"  Leads found:    {leads_found}")
    log.info(f"  Leads imported: {leads_imported}")
    log.info(f"  Emails found:   {emails_found}")
    log.info(f"  Phones found:   {phones_found}")
    log.info(f"  Exported to SDR: {exported}")
    log.info("=" * 60)

    return summary


def post_scout_summary(summary: dict):
    """Post scout results to Slack #wholesale-deals."""
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not slack_token:
        log.info("No SLACK_BOT_TOKEN -- skipping Slack post")
        return

    import requests

    channel = os.environ.get("SLACK_WHOLESALE_CHANNEL", "C0ANLLV8JAC")
    msg = (
        f"*Rex Scout Report -- {TODAY}*\n\n"
        f"*Market:* {summary.get('market', '?')}\n"
        f"*Searches:* {summary.get('searches_completed', 0)}/{summary.get('total_searches', 0)}\n"
        f"*Leads found:* {summary.get('leads_found', 0)}\n"
        f"*Imported to Django:* {summary.get('leads_imported', 0)}\n"
        f"*Emails found:* {summary.get('emails_found', 0)}\n"
        f"*Phones found:* {summary.get('phones_found', 0)}\n"
        f"*Exported to SDR:* {summary.get('exported_to_sdr', 0)}\n\n"
        f"SDR is ready to email. Run `python rex_sdr.py` to start outreach."
    )

    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            },
            json={"channel": channel, "text": msg},
            timeout=10,
        )
    except Exception as exc:
        log.warning(f"Slack post failed: {exc}")


# ---------------------------------------------------------------------------
# PART 4: IMPORT BUYERS FROM CSV
# ---------------------------------------------------------------------------

def import_buyers(csv_path: str):
    """
    Import cash buyers from a CSV into the buyers pipeline.
    Expected columns: name, company, email, phone, city, state, buy_criteria
    """
    import csv

    if not os.path.exists(csv_path):
        log.error(f"File not found: {csv_path}")
        return 0

    buyers_path = AGENT_DIR / "buyers_db.json"
    existing = []
    if buyers_path.exists():
        try:
            existing = json.loads(buyers_path.read_text())
        except json.JSONDecodeError:
            existing = []

    existing_emails = {b.get("email", "").lower() for b in existing}
    added = 0

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").strip()
            if not email or email.lower() in existing_emails:
                continue

            buyer = {
                "name": row.get("name", "").strip(),
                "company": row.get("company", "").strip(),
                "email": email,
                "phone": row.get("phone", "").strip(),
                "city": row.get("city", "").strip(),
                "state": row.get("state", "").strip(),
                "buy_criteria": row.get("buy_criteria", "").strip(),
                "added_date": TODAY,
                "deals_sent": 0,
                "deals_closed": 0,
            }
            existing.append(buyer)
            existing_emails.add(email.lower())
            added += 1

    buyers_path.write_text(json.dumps(existing, indent=2))
    log.info(f"Imported {added} buyers ({len(existing)} total in buyers_db.json)")
    return added


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed and enrich the wholesale pipeline"
    )
    parser.add_argument(
        "--scout", action="store_true",
        help="Run full scout mode: search all zips x keywords, enrich, skip trace, import"
    )
    parser.add_argument(
        "--buyers", type=str, metavar="CSV_PATH",
        help="Import buyers from a CSV file"
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="Only export Django leads to leads_db.json (skip enrichment)"
    )
    args = parser.parse_args()

    if args.buyers:
        import_buyers(args.buyers)
        return

    if args.export_only:
        export_to_sdr_db()
        return

    if args.scout:
        log.info("Starting high-volume scout mode...")
        run_scout_mode()
        return

    # Default: enrich existing Django leads, then export
    log.info("Enriching existing Django leads...")
    enrich_summary = enrich_django_leads()

    log.info("Exporting enriched leads to SDR leads_db.json...")
    exported = export_to_sdr_db()

    log.info("")
    log.info("PIPELINE STATUS:")
    log.info(f"  Total Django leads:     {enrich_summary['total_leads']}")
    log.info(f"  Emails found this run:  {enrich_summary['emails_found']}")
    log.info(f"  Phones found this run:  {enrich_summary['phones_found']}")
    log.info(f"  Exported to SDR:        {exported}")
    log.info("")
    log.info("Next step: run 'python rex_sdr.py' to start sending emails")


if __name__ == "__main__":
    main()
