"""
Rex's Free Skip Tracer -- finds owner contact info using $0 public sources.

Replaces paid services like Tracerfy ($0.02/lead) and BatchSkipTracing ($0.20/lead).

Sources (all free):
1. TruePeopleSearch.com -- name + address -> phone, email, relatives
2. FastPeopleSearch.com -- similar to above
3. County voter registration records -- name, address, DOB, phone
4. Facebook/LinkedIn search by name + city
5. Google search "[owner name] [city] phone"

Usage:
    from free_skip_tracer import skip_trace_owner, bulk_skip_trace
"""

import json
import logging
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkipTraceResult:
    """Results from skip tracing an owner."""
    owner_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    phones: list = field(default_factory=list)
    emails: list = field(default_factory=list)
    relatives: list = field(default_factory=list)
    source: str = ""
    confidence: str = "low"  # low, medium, high
    search_urls: dict = field(default_factory=dict)


def generate_search_urls(owner_name: str, city: str, state: str, address: str = "") -> dict:
    """
    Generate free lookup URLs for manual or automated skip tracing.
    Rex opens these in a browser or fetches them programmatically.
    """
    name_encoded = urllib.parse.quote(owner_name)
    city_state = urllib.parse.quote(f"{city}, {state}")
    address_encoded = urllib.parse.quote(address) if address else ""

    urls = {
        # Free people search engines
        "truepeoplesearch": f"https://www.truepeoplesearch.com/results?name={name_encoded}&citystatezip={city_state}",
        "fastpeoplesearch": f"https://www.fastpeoplesearch.com/name/{owner_name.replace(' ', '-').lower()}_{city.lower()}-{state.lower()}",
        "whitepages": f"https://www.whitepages.com/name/{owner_name.replace(' ', '-')}/{city}-{state}",

        # Social media
        "facebook": f"https://www.facebook.com/search/people/?q={name_encoded}%20{city_state}",
        "linkedin": f"https://www.linkedin.com/search/results/people/?keywords={name_encoded}%20{city_state}",

        # Google search for contact info
        "google_phone": f"https://www.google.com/search?q={name_encoded}+{city_state}+phone+number",
        "google_email": f"https://www.google.com/search?q={name_encoded}+{city_state}+email",

        # County records (generic -- replace with specific county URLs)
        "county_assessor": f"https://www.google.com/search?q={city_state}+county+assessor+property+records",
        "voter_records": f"https://www.google.com/search?q={city_state}+voter+registration+lookup",
    }

    # If we have the address, add reverse address lookup
    if address:
        urls["reverse_address"] = f"https://www.truepeoplesearch.com/results?streetaddress={address_encoded}&citystatezip={city_state}"

    return urls


def skip_trace_owner(
    owner_name: str,
    address: str = "",
    city: str = "",
    state: str = "",
) -> SkipTraceResult:
    """
    Generate skip trace search URLs for an owner.

    This doesn't auto-scrape (that would violate ToS) -- it generates
    the URLs that Rex or a VA clicks through manually to find contact info.
    The results get entered back into the PropertyLead record.

    For automation: use the Google search URLs + a WebFetch agent to
    extract phone numbers from search results (public info, fair use).
    """
    urls = generate_search_urls(owner_name, city, state, address)

    return SkipTraceResult(
        owner_name=owner_name,
        address=address,
        city=city,
        state=state,
        source="free_skip_trace",
        search_urls=urls,
        confidence="pending",  # needs manual lookup
    )


def bulk_skip_trace(leads: list[dict]) -> list[SkipTraceResult]:
    """
    Generate skip trace URLs for a batch of leads.

    Input: list of dicts with keys: owner_name, address, city, state
    Output: list of SkipTraceResult with search URLs ready to click
    """
    results = []
    for lead in leads:
        result = skip_trace_owner(
            owner_name=lead.get("owner_name", ""),
            address=lead.get("address", ""),
            city=lead.get("city", ""),
            state=lead.get("state", ""),
        )
        results.append(result)
    return results


def export_skip_trace_csv(results: list[SkipTraceResult], output_path: str) -> str:
    """Export skip trace URLs to CSV for batch manual lookup."""
    import csv
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "owner_name", "address", "city", "state",
            "truepeoplesearch_url", "fastpeoplesearch_url",
            "facebook_url", "google_phone_url", "reverse_address_url",
        ])
        for r in results:
            writer.writerow([
                r.owner_name, r.address, r.city, r.state,
                r.search_urls.get("truepeoplesearch", ""),
                r.search_urls.get("fastpeoplesearch", ""),
                r.search_urls.get("facebook", ""),
                r.search_urls.get("google_phone", ""),
                r.search_urls.get("reverse_address", ""),
            ])
    return output_path


# ---------------------------------------------------------------------------
# FREE COUNTY DATA SOURCES (by target market)
# ---------------------------------------------------------------------------

COUNTY_DATA_SOURCES = {
    "st_louis": {
        "name": "St. Louis, MO",
        "assessor": "https://revenue.stlouisco.com/IAS/",
        "recorder": "https://www.stlouisco.com/YourGovernment/CountyDepartments/Recorder",
        "code_violations": "https://www.stlouis-mo.gov/government/departments/public-safety/building/code-enforcement/",
        "tax_delinquent": "https://collector.stlouisco.com/",
        "notes": "City and county are separate jurisdictions -- check both",
    },
    "atlanta": {
        "name": "Atlanta / Fulton County, GA",
        "assessor": "https://www.qpublic.net/ga/fulton/",
        "recorder": "https://www.fultoncountyga.gov/services/clerk-of-superior-court",
        "code_violations": "https://aca-prod.accela.com/Atlanta/",
        "tax_delinquent": "https://www.fultoncountytaxcommissioner.org/",
        "notes": "Fulton County qPublic has free property search with owner info",
    },
    "dallas": {
        "name": "Dallas / Tarrant County, TX",
        "assessor": "https://www.dallascad.org/",
        "recorder": "https://www.dallascounty.org/departments/countyclerk/",
        "code_violations": "https://gcc.dallascityhall.com/",
        "tax_delinquent": "https://www.dallascounty.org/departments/tax/",
        "notes": "DCAD has excellent free property search + owner data",
    },
    "charlotte": {
        "name": "Charlotte / Mecklenburg County, NC",
        "assessor": "https://property.spatialest.com/nc/mecklenburg/",
        "recorder": "https://www.mecknc.gov/CountyManagersOffice/ROD/",
        "code_violations": "https://charlottenc.gov/nbs/Code/Pages/default.aspx",
        "tax_delinquent": "https://www.mecknc.gov/TaxCollections/",
        "notes": "Polaris property search is free and detailed",
    },
    "cleveland": {
        "name": "Cleveland / Cuyahoga County, OH",
        "assessor": "https://myplace.cuyahogacounty.gov/",
        "recorder": "https://recorder.cuyahogacounty.us/",
        "code_violations": "https://www.clevelandohio.gov/CityHall/BuildingHousing",
        "tax_delinquent": "https://treasurer.cuyahogacounty.us/",
        "notes": "myPlace has free property lookup with delinquent tax info",
    },
    "jacksonville": {
        "name": "Jacksonville / Duval County, FL",
        "assessor": "https://www.coj.net/departments/property-appraiser",
        "recorder": "https://www2.duvalclerk.com/",
        "code_violations": "https://www.coj.net/departments/neighborhoods/municipal-code-compliance",
        "tax_delinquent": "https://www.coj.net/departments/tax-collector",
        "notes": "Duval County has free online property records with owner names",
    },
}


def get_county_sources(market_key: str) -> dict:
    """Get free county data source URLs for a target market."""
    return COUNTY_DATA_SOURCES.get(market_key, {})


def print_all_sources():
    """Print all free data sources for all markets."""
    for key, market in COUNTY_DATA_SOURCES.items():
        print(f"\n{'='*60}")
        print(f"  {market['name']}")
        print(f"{'='*60}")
        print(f"  Assessor:        {market['assessor']}")
        print(f"  Recorder:        {market['recorder']}")
        print(f"  Code Violations: {market['code_violations']}")
        print(f"  Tax Delinquent:  {market['tax_delinquent']}")
        print(f"  Notes:           {market['notes']}")
