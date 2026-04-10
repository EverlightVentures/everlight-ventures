#!/usr/bin/env python3
"""
REAL Skip Tracer + Lead Enrichment Pipeline
Takes 65 property addresses from Supabase, gets ACTUAL owner contact info, updates DB.

Sources (ALL FREE):
1. ATTOM API (free trial) -- owner name, mailing address, property details, assessed value
2. Google search -- phone/email from owner name + address (public info)
3. County assessor sites -- backup for owner names

This script ACTUALLY FETCHES DATA. Not just URLs.

Usage:
    python3 skip_trace_and_enrich.py              # enrich all unenriched leads
    python3 skip_trace_and_enrich.py --limit 10   # enrich 10 leads
    python3 skip_trace_and_enrich.py --report      # just print current stats
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M")
log = logging.getLogger("skip_tracer")

# Load env
for env_path in ["/home/opc/.env", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"]:
    p = Path(env_path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break

SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
ATTOM_API_KEY = os.environ.get("ATTOM_API_KEY", "")
ATTOM_BASE = "https://api.gateway.attomdata.com"

SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# Rate limiting
ATTOM_DELAY = 1.0  # seconds between ATTOM calls (free tier)
GOOGLE_DELAY = 3.0  # seconds between Google searches (avoid blocks)


# ============================================================
# SUPABASE HELPERS
# ============================================================

def sb_get(table, query="", limit=500):
    url = f"{SUPABASE_URL}/{table}?{query}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers=SB_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f"Supabase GET failed: {e}")
        return []


def sb_update(table, record_id, data):
    url = f"{SUPABASE_URL}/{table}?id=eq.{record_id}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={**SB_HEADERS, "Prefer": "return=minimal"}, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except Exception as e:
        log.error(f"Supabase UPDATE failed: {e}")
        return 0


# ============================================================
# ATTOM API -- Owner Name + Property Details (FREE TRIAL)
# ============================================================

def attom_lookup(address: str, city: str, state: str) -> dict:
    """Look up property owner + details from ATTOM API."""
    if not ATTOM_API_KEY:
        return {}

    # Clean address
    address = address.split(",")[0].strip()  # Remove city/state if included

    params = urllib.parse.urlencode({
        "address1": address,
        "address2": f"{city}, {state}",
    })
    url = f"{ATTOM_BASE}/propertyapi/v1.0.0/property/expandedprofile?{params}"

    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "apikey": ATTOM_API_KEY,
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        prop = data.get("property", [{}])[0] if data.get("property") else {}
        if not prop:
            return {}

        lot = prop.get("lot", {})
        building = prop.get("building", {})
        summary = building.get("summary", {})
        rooms = building.get("rooms", {})
        size = building.get("size", {})
        assessment = prop.get("assessment", {})
        assessed = assessment.get("assessed", {})
        market = assessment.get("market", {})
        sale = prop.get("sale", {})
        last_sale = sale.get("amount", {})

        # Owner info -- the key data we need
        owner_info = prop.get("assessment", {}).get("owner", {})
        owner1 = owner_info.get("owner1", {})
        owner_name = ""
        if isinstance(owner1, dict):
            owner_name = owner1.get("fullName", "") or owner1.get("lastName", "")
        elif isinstance(owner1, str):
            owner_name = owner1

        # Mailing address -- single line format in expandedprofile
        mail_address = owner_info.get("mailingAddressOneLine", "")
        if not mail_address:
            mail = owner_info.get("mailingAddress", {})
            if isinstance(mail, dict):
                mail_address = f"{mail.get('line1', '')} {mail.get('line2', '')}".strip()

        return {
            "owner_name": str(owner_name)[:200],
            "mailing_address": mail_address,
            "is_absentee": mail_address and mail_address.lower() != address.lower(),
            "year_built": summary.get("yearBuilt", 0) or 0,
            "sqft": size.get("livingSize", 0) or size.get("universalSize", 0) or 0,
            "bedrooms": rooms.get("bedrooms", 0) or 0,
            "bathrooms": rooms.get("bathsFull", 0) or 0,
            "lot_sqft": lot.get("lotSize1", 0) or 0,
            "assessed_value": assessed.get("assdTtlValue", 0) or 0,
            "market_value": market.get("mktTtlValue", 0) or 0,
            "last_sale_price": last_sale.get("saleAmt", 0) or 0,
            "last_sale_date": sale.get("saleTransDate", "") or "",
            "source": "attom",
        }

    except urllib.error.HTTPError as e:
        if e.code == 404:
            log.debug(f"ATTOM: no data for {address}, {city} {state}")
        else:
            log.warning(f"ATTOM error {e.code} for {address}: {e.reason}")
        return {}
    except Exception as e:
        log.warning(f"ATTOM lookup failed for {address}: {e}")
        return {}


# ============================================================
# GOOGLE SEARCH -- Phone/Email from Owner Name (FREE)
# ============================================================

def google_search_contact(owner_name: str, city: str, state: str) -> dict:
    """Search Google for owner's phone and email. Free, public info."""
    if not owner_name or len(owner_name) < 3:
        return {}

    query = f"{owner_name} {city} {state} phone email"
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=5"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(50000).decode("utf-8", errors="ignore")

        phones = set()
        emails = set()

        # Extract phone numbers (US format)
        phone_patterns = re.findall(r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', html)
        for p in phone_patterns:
            cleaned = re.sub(r'[^\d]', '', p)
            if len(cleaned) == 10 and cleaned[0] not in ('0', '1'):
                phones.add(f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}")

        # Extract emails
        email_patterns = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        for e in email_patterns:
            e = e.lower()
            # Filter out obvious non-personal emails
            if not any(x in e for x in ['google', 'bing', 'yahoo.com/search', 'example',
                                         'schema.org', 'w3.org', 'googleapis', 'gstatic']):
                emails.add(e)

        return {
            "phones": list(phones)[:3],
            "emails": list(emails)[:3],
            "source": "google_search",
        }

    except Exception as e:
        log.debug(f"Google search failed for {owner_name}: {e}")
        return {}


# ============================================================
# MAIN ENRICHMENT PIPELINE
# ============================================================

def parse_address_field(raw: str) -> tuple:
    """Parse 'street city ST zip' or '[Zillow Lead] street city ST zip' into components.

    Returns: (street, city, state, zip)
    """
    # Strip Zillow prefix
    raw = re.sub(r'^\[Zillow Lead\]\s*', '', raw).strip()

    # Known TX cities (check longest first to handle "Fort Worth" before "Worth")
    known_cities = sorted([
        "Fort Worth", "Grand Prairie", "San Antonio", "Corpus Christi",
        "Dallas", "Houston", "Austin", "Arlington", "Plano", "Irving",
        "Garland", "Mesquite", "Denton", "McKinney", "Frisco", "Carrollton",
        "Lewisville", "Allen", "Tyler", "Waco", "Killeen", "Abilene",
        "Beaumont", "Lubbock", "Amarillo", "Laredo", "Brownsville",
        "El Paso", "Midland", "Odessa", "Round Rock", "Cedar Hill",
        "Mansfield", "Burleson", "Haltom City", "Euless", "Bedford",
        "Keller", "Grapevine", "Southlake", "Weatherford",
        # OH cities
        "Cleveland", "Columbus", "Cincinnati", "Akron", "Dayton", "Toledo",
        # FL cities
        "Jacksonville", "Miami", "Tampa", "Orlando", "Fort Lauderdale",
        # GA cities
        "Atlanta", "Savannah", "Augusta", "Macon",
        # TN cities
        "Memphis", "Nashville", "Knoxville", "Chattanooga",
        # IN cities
        "Indianapolis", "Fort Wayne", "Evansville", "South Bend",
    ], key=len, reverse=True)

    # Find state + zip at end
    m = re.search(r'\b([A-Z]{2})\s+(\d{5})\s*$', raw)
    if m:
        prefix = raw[:m.start()].strip()
        st = m.group(1)
        zipcode = m.group(2)

        # Try known cities
        for city_name in known_cities:
            if prefix.lower().endswith(city_name.lower()):
                street = prefix[:len(prefix) - len(city_name)].strip()
                if street:
                    return street, city_name, st, zipcode

        return prefix, "", st, zipcode

    # No zip code -- try just state
    m2 = re.search(r'\b([A-Z]{2})\s*$', raw)
    if m2:
        prefix = raw[:m2.start()].strip()
        st = m2.group(1)
        for city_name in known_cities:
            if prefix.lower().endswith(city_name.lower()):
                street = prefix[:len(prefix) - len(city_name)].strip()
                if street:
                    return street, city_name, st, ""

    return raw, "", "", ""


def enrich_lead(lead: dict) -> dict:
    """Enrich a single seller lead with owner info + contact data.

    Returns dict of fields to update in Supabase.
    """
    lead_id = lead.get("id")
    raw_address = lead.get("property_address", "")
    city = lead.get("city", "")
    state = lead.get("state", "")

    # Parse address field -- always parse to get clean street vs city
    street, parsed_city, parsed_state, zipcode = parse_address_field(raw_address)
    if parsed_city:
        city = parsed_city
    if parsed_state:
        state = parsed_state
    # Use parsed street for ATTOM lookup, fall back to raw
    address = street if street else raw_address

    if not address:
        return {}

    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}

    # Update city/state if we parsed them
    if city and not lead.get("city"):
        updates["city"] = city
    if state and not lead.get("state"):
        updates["state"] = state

    log.info(f"Enriching: {address}, {city} {state}")

    # Step 1: ATTOM lookup for owner name + property details
    attom = attom_lookup(address, city, state)
    if attom:
        owner = attom.get("owner_name", "")
        if owner:
            updates["owner_name"] = owner
            log.info(f"  Owner: {owner}")

            if attom.get("mailing_address"):
                updates["owner_mailing_address"] = attom["mailing_address"]

            # Add property details if we got them
            if attom.get("sqft"):
                updates["sqft"] = attom["sqft"]
            if attom.get("bedrooms"):
                updates["bedrooms"] = attom["bedrooms"]
            if attom.get("bathrooms"):
                updates["bathrooms"] = attom["bathrooms"]
            if attom.get("assessed_value"):
                updates["estimated_arv"] = attom["assessed_value"]
            if attom.get("market_value") and attom["market_value"] > (attom.get("assessed_value") or 0):
                updates["estimated_arv"] = attom["market_value"]

            # Step 2: Google search for phone/email using owner name
            time.sleep(GOOGLE_DELAY)
            contact = google_search_contact(owner, city, state)
            if contact:
                if contact.get("phones"):
                    updates["contact_phone"] = contact["phones"][0]
                    log.info(f"  Phone: {contact['phones'][0]}")
                if contact.get("emails"):
                    updates["contact_email"] = contact["emails"][0]
                    log.info(f"  Email: {contact['emails'][0]}")
        else:
            log.info(f"  No owner found via ATTOM")
    else:
        log.info(f"  ATTOM returned nothing")

    # Mark enrichment status in notes
    has_contact = bool(updates.get("contact_phone") or updates.get("contact_email"))
    has_owner = bool(updates.get("owner_name"))
    notes_addition = f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d')}] Enriched: "
    if has_contact:
        notes_addition += "CONTACT FOUND"
        updates["status"] = "new"  # Ready for outreach
    elif has_owner:
        notes_addition += f"Owner: {updates.get('owner_name')} (no contact yet)"
    else:
        notes_addition += "No data found"

    existing_notes = lead.get("notes", "") or ""
    updates["notes"] = existing_notes + notes_addition

    time.sleep(ATTOM_DELAY)
    return updates


def run_enrichment(limit: int = 0):
    """Pull unenriched leads from Supabase, enrich them, update DB."""

    # Get leads without contact info
    query = "select=*&order=created_at.desc"
    leads = sb_get("wholesale_sellers", query)

    if not isinstance(leads, list):
        log.error("Failed to fetch leads")
        return

    # Filter to leads needing enrichment (no owner name or no contact)
    needs_enrichment = []
    for lead in leads:
        owner = lead.get("owner_name", "") or ""
        email = lead.get("contact_email", "") or ""
        phone = lead.get("contact_phone", "") or ""
        # Skip if already has contact info
        if email and "@" in email:
            continue
        if phone and len(phone) > 5:
            continue
        needs_enrichment.append(lead)

    if limit > 0:
        needs_enrichment = needs_enrichment[:limit]

    log.info(f"Total leads: {len(leads)} | Need enrichment: {len(needs_enrichment)}")

    if not needs_enrichment:
        log.info("All leads already enriched!")
        return

    stats = {"total": len(needs_enrichment), "enriched": 0, "with_contact": 0,
             "with_owner": 0, "failed": 0}

    for i, lead in enumerate(needs_enrichment):
        log.info(f"\n--- Lead {i+1}/{len(needs_enrichment)} ---")
        try:
            updates = enrich_lead(lead)
            if updates:
                status = sb_update("wholesale_sellers", lead["id"], updates)
                if status in (200, 204):
                    stats["enriched"] += 1
                    if updates.get("contact_phone") or updates.get("contact_email"):
                        stats["with_contact"] += 1
                    elif updates.get("owner_name"):
                        stats["with_owner"] += 1
                else:
                    stats["failed"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            log.error(f"  Error enriching lead {lead.get('id')}: {e}")
            stats["failed"] += 1

    log.info(f"\n{'='*50}")
    log.info(f"ENRICHMENT COMPLETE")
    log.info(f"  Processed: {stats['total']}")
    log.info(f"  Enriched:  {stats['enriched']}")
    log.info(f"  With contact info: {stats['with_contact']}")
    log.info(f"  With owner only:   {stats['with_owner']}")
    log.info(f"  Failed:    {stats['failed']}")
    log.info(f"{'='*50}")

    return stats


def print_report():
    """Print current pipeline status -- the honest truth."""
    leads = sb_get("wholesale_sellers", "select=*")
    buyers = sb_get("wholesale_buyers", "select=*")
    deals = sb_get("wholesale_deals", "select=*")
    outreach = sb_get("wholesale_outreach", "select=*")

    if not isinstance(leads, list):
        leads = []
    if not isinstance(buyers, list):
        buyers = []
    if not isinstance(deals, list):
        deals = []
    if not isinstance(outreach, list):
        outreach = []

    # Seller stats
    with_email = sum(1 for s in leads if s.get("contact_email") and "@" in str(s.get("contact_email", "")))
    with_phone = sum(1 for s in leads if s.get("contact_phone") and len(str(s.get("contact_phone", ""))) > 5)
    with_owner = sum(1 for s in leads if s.get("owner_name") and len(str(s.get("owner_name", ""))) > 2)
    contactable = sum(1 for s in leads if
                       (s.get("contact_email") and "@" in str(s.get("contact_email", ""))) or
                       (s.get("contact_phone") and len(str(s.get("contact_phone", ""))) > 5))

    # Buyer stats
    buyer_emails = sum(1 for b in buyers if b.get("email") and "@" in str(b.get("email", "")))

    # Outreach stats
    sent = sum(1 for o in outreach if o.get("status") == "sent")
    replied = sum(1 for o in outreach if o.get("status") == "replied")
    drafted = sum(1 for o in outreach if o.get("status") == "draft")

    # Deal stats
    by_status = {}
    for d in deals:
        st = d.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1

    print("\n" + "=" * 60)
    print("  WHOLESALE PIPELINE -- HONEST STATUS REPORT")
    print("  %s" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 60)

    print("\nSELLER LEADS: %d total" % len(leads))
    print("  With owner name:  %d" % with_owner)
    print("  With email:       %d" % with_email)
    print("  With phone:       %d" % with_phone)
    print("  CONTACTABLE:      %d  <-- this is what matters" % contactable)
    print("  Need enrichment:  %d" % (len(leads) - contactable))

    print("\nBUYER LIST: %d total" % len(buyers))
    print("  With email:       %d" % buyer_emails)
    print("  WITHOUT email:    %d  <-- useless without contact" % (len(buyers) - buyer_emails))

    print("\nOUTREACH: %d total" % len(outreach))
    print("  Actually sent:    %d" % sent)
    print("  Replies:          %d" % replied)
    print("  Still in draft:   %d  <-- never sent" % drafted)

    print("\nDEALS: %d total" % len(deals))
    for k, v in sorted(by_status.items()):
        print("  %s: %d" % (k, v))

    print("\nREVENUE: $0.00")
    print("\nBLOCKERS:")
    if contactable == 0:
        print("  [CRITICAL] Zero contactable sellers. Run enrichment first.")
    if buyer_emails == 0:
        print("  [CRITICAL] Zero contactable buyers. Need real buyer list.")
    if sent == 0:
        print("  [CRITICAL] Zero outreach sent. Pipeline is idle.")
    print("=" * 60)


if __name__ == "__main__":
    if "--report" in sys.argv:
        print_report()
    else:
        limit = 0
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        run_enrichment(limit=limit)
