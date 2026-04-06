#!/usr/bin/env python3
"""
AI Consulting Prospect Scraper -- finds SMBs via Google Maps Places API.

Targets: dentists, home services, agencies in California.
Outputs leads to Django broker_ops API with category 'ai_consulting'.

Usage:
    python3 prospect_scraper.py --vertical dentist --location "Los Angeles, CA" --limit 20
    python3 prospect_scraper.py --vertical "hvac contractor" --location "San Diego, CA"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Add broker scripts to path for enrichment module (works on phone + Oracle)
_WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc"),
]
WORKSPACE = next((p for p in _WORKSPACE_CANDIDATES if p.exists()), _WORKSPACE_CANDIDATES[0])

for _bp in [
    WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "broker",
    Path("/home/opc/broker"),
]:
    if _bp.exists():
        sys.path.insert(0, str(_bp))
        break
from contact_enrichment import extract_email_from_text, _fetch_text

# Load .env if not already in environment
_env_candidates = [
    WORKSPACE / "03_AUTOMATION_CORE" / "03_Credentials" / ".env",
    Path("/home/opc/.env"),
]
for _ef in _env_candidates:
    if _ef.exists():
        for line in _ef.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break

LOG_DIR = WORKSPACE / "_logs" / "ai_consulting"
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Target verticals with search queries
VERTICALS = {
    "dentist": ["dentist", "dental practice", "dental office"],
    "hvac": ["hvac contractor", "heating and cooling", "air conditioning repair"],
    "plumber": ["plumber", "plumbing service", "plumbing contractor"],
    "electrician": ["electrician", "electrical contractor", "electrical service"],
    "agency": ["digital marketing agency", "web design agency", "seo agency"],
    "legal": ["law firm", "attorney", "legal practice"],
    "real_estate": ["real estate agent", "real estate team", "realtor"],
}


def search_places(query: str, location: str, limit: int = 20) -> list[dict]:
    """Search Google Maps Places API for businesses."""
    if not GOOGLE_API_KEY:
        print("[ERROR] GOOGLE_MAPS_API_KEY not set. Set it in your environment.")
        return []

    text_query = f"{query} in {location}"
    url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        + urllib.parse.urlencode({
            "query": text_query,
            "key": GOOGLE_API_KEY,
            "type": "establishment",
        })
    )

    results = []
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for place in data.get("results", [])[:limit]:
            results.append({
                "business_name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
                "google_rating": place.get("rating", 0),
                "review_count": place.get("user_ratings_total", 0),
                "place_id": place.get("place_id", ""),
                "category": query,
                "location": location,
                "types": place.get("types", []),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        print(f"[ERROR] Places API: {e}")

    return results


def enrich_website_email(website: str) -> str:
    """Scrape a business website for email addresses on main, contact, and about pages."""
    if not website:
        return ""
    # Normalize
    if not website.startswith("http"):
        website = f"https://{website}"

    # Try main page first, then common contact pages
    pages_to_try = [
        website.rstrip("/"),
        website.rstrip("/") + "/contact",
        website.rstrip("/") + "/about",
        website.rstrip("/") + "/contact-us",
        website.rstrip("/") + "/about-us",
    ]

    for page_url in pages_to_try:
        try:
            html = _fetch_text(page_url, timeout=8, max_bytes=20000)
            if not html:
                continue
            email = extract_email_from_text(html)
            if email:
                return email
        except Exception:
            continue
    return ""


def get_place_details(place_id: str) -> dict:
    """Get detailed info (website, phone) for a place, including email extraction."""
    if not GOOGLE_API_KEY:
        return {}

    url = (
        "https://maps.googleapis.com/maps/api/place/details/json?"
        + urllib.parse.urlencode({
            "place_id": place_id,
            "fields": "website,formatted_phone_number,opening_hours,reviews",
            "key": GOOGLE_API_KEY,
        })
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("result", {})
        website = result.get("website", "")
        details = {
            "website": website,
            "phone": result.get("formatted_phone_number", ""),
            "has_hours": bool(result.get("opening_hours")),
            "review_snippets": [
                r.get("text", "")[:200]
                for r in (result.get("reviews") or [])[:3]
            ],
        }

        # Extract email from business website
        if website:
            email = enrich_website_email(website)
            if email:
                details["email"] = email
                print(f"  [EMAIL] Found: {email} from {website}")
            else:
                print(f"  [EMAIL] None found on {website}")

        return details
    except Exception:
        return {}


def ingest_to_django(leads: list[dict], django_url: str = "http://127.0.0.1:8504") -> dict:
    """Push leads to Django broker_ops API as LEADS (buyers needing AI consulting)."""
    results = {"ingested": 0, "with_email": 0, "without_email": 0, "errors": 0}
    for lead in leads:
        has_email = bool(lead.get("email"))
        payload = json.dumps({
            "name": lead["business_name"],
            "email": lead.get("email", ""),
            "category": "ai_consulting",
            "need_description": (
                f"SMB needing AI automation. Vertical: {lead['category']}. "
                f"Location: {lead['address']}. "
                f"Rating: {lead['google_rating']} ({lead['review_count']} reviews). "
                f"Website: {lead.get('website', 'N/A')}. Phone: {lead.get('phone', 'N/A')}."
            ),
            "source": "google_maps_scraper",
            "keywords": [lead["category"], "ai_consulting", "smb"],
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{django_url}/broker/api/ingest/lead/",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10):
                results["ingested"] += 1
                if has_email:
                    results["with_email"] += 1
                else:
                    results["without_email"] += 1
        except Exception as e:
            results["errors"] += 1
            print(f"[WARN] Failed to ingest {lead['business_name']}: {e}")

    return results


def enrich_existing_leads(django_url: str = "http://127.0.0.1:8504") -> dict:
    """Backfill emails for existing leads that have a website but no email.

    Reads leads from Django API, scrapes their websites for emails, and updates them.
    This is the fix for the 241/243 leads with no email problem.
    """
    print("[ENRICH] Backfilling emails for existing leads...")
    results = {"checked": 0, "enriched": 0, "already_has_email": 0, "no_website": 0}

    # Try to read leads from Django
    try:
        req = urllib.request.Request(
            f"{django_url}/broker/api/leads/?format=json&limit=500",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            leads = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Could not fetch leads from Django: {e}")
        print("[FALLBACK] Trying Django ORM directly...")
        # Fallback: use Django ORM if we're on the same machine
        try:
            django_project = str(WORKSPACE / "09_DASHBOARD" / "hive_dashboard")
            if django_project not in sys.path:
                sys.path.insert(0, django_project)
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
            import django
            django.setup()
            from broker_ops.models import LeadProfile

            leads_qs = LeadProfile.objects.filter(email="").exclude(need_description="")
            print(f"[ENRICH] Found {leads_qs.count()} leads without email")

            for lead in leads_qs:
                results["checked"] += 1
                # Extract website from need_description
                website = ""
                desc = lead.need_description or ""
                if "Website:" in desc:
                    website = desc.split("Website:")[1].split(".")[0].strip()
                    # Try to reconstruct URL
                    if website and website != "N/A":
                        if not website.startswith("http"):
                            website = f"https://{website}"

                if not website or website == "N/A":
                    results["no_website"] += 1
                    continue

                email = enrich_website_email(website)
                if email:
                    lead.email = email
                    lead.save(update_fields=["email", "updated_at"])
                    results["enriched"] += 1
                    print(f"  [OK] {lead.name}: {email}")

            return results
        except Exception as e2:
            print(f"[ERROR] Django ORM fallback also failed: {e2}")
            return results

    return results


def main():
    parser = argparse.ArgumentParser(description="AI Consulting Prospect Scraper")
    parser.add_argument("--vertical", default="dentist", help="Target vertical")
    parser.add_argument("--location", default="Los Angeles, CA", help="Target location")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--ingest", action="store_true", help="Push to Django")
    parser.add_argument("--details", action="store_true", help="Fetch place details (includes email enrichment)")
    parser.add_argument("--enrich-existing", action="store_true", help="Backfill emails for existing leads")
    parser.add_argument("--django-url", default="http://127.0.0.1:8504", help="Django API URL")
    args = parser.parse_args()

    # Backfill mode
    if args.enrich_existing:
        results = enrich_existing_leads(args.django_url)
        print(f"\n[ENRICH RESULTS] Checked: {results['checked']} | "
              f"Enriched: {results['enriched']} | "
              f"No website: {results['no_website']}")
        return

    queries = VERTICALS.get(args.vertical, [args.vertical])
    all_leads = []

    for query in queries:
        print(f"[SCRAPE] Searching: '{query}' in {args.location}")
        leads = search_places(query, args.location, args.limit)
        print(f"  Found {len(leads)} results")

        # Always fetch details + email enrichment for new scrapes
        for lead in leads:
            details = get_place_details(lead["place_id"])
            lead.update(details)

        all_leads.extend(leads)

    # Dedupe by place_id
    seen = set()
    unique = []
    for lead in all_leads:
        pid = lead.get("place_id", lead["business_name"])
        if pid not in seen:
            seen.add(pid)
            unique.append(lead)

    with_email = sum(1 for l in unique if l.get("email"))
    print(f"\n[TOTAL] {len(unique)} unique leads | {with_email} with email ({with_email/max(len(unique),1)*100:.0f}%)")

    # Save to log
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"prospects_{args.vertical}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    log_file.write_text(json.dumps(unique, indent=2), encoding="utf-8")
    print(f"[SAVED] {log_file}")

    if args.ingest:
        results = ingest_to_django(unique, args.django_url)
        print(f"[INGEST] {results['ingested']}/{len(unique)} pushed to Django | "
              f"{results['with_email']} with email | {results['errors']} errors")


if __name__ == "__main__":
    main()
