"""
Each investigator module exports:
    NAME: human-readable name
    DOMAINS: list of domains this investigator HTTP-calls (so live_log records them)
    WHEN: list of entity types it handles ("company", "person", "domain", "email", "address", "phone", "*")
    async def run(target: str, http: httpx.AsyncClient) -> dict
        returns {"ok": bool, "findings": [{label, value, url?}], "raw": {...}, "elapsed_ms": int}
"""
from . import (
    archive_org,
    comment_scan,
    consumer_signals,
    domain_intel,
    email_discovery,
    google_dorks,
    leak_check,
    obituary_estate,
    opencorporates,
    philanthropy_civic,
    property_records,
    public_records,
    resource_lookup,
    reverse_whois,
    sec_edgar,
    skip_trace,
    social_bio_scraper,
    social_recon,
    username_enrichment,
    wayback_contact_extract,
    whois_lookup,
)

ALL = [
    archive_org,
    comment_scan,
    consumer_signals,
    domain_intel,
    email_discovery,
    google_dorks,
    leak_check,
    obituary_estate,
    opencorporates,
    philanthropy_civic,
    property_records,
    public_records,
    resource_lookup,
    reverse_whois,
    sec_edgar,
    skip_trace,
    social_bio_scraper,
    social_recon,
    username_enrichment,
    wayback_contact_extract,
    whois_lookup,
]


def for_target(target: str, kind: str | None = None) -> list:
    """Pick investigators that handle this entity type. If kind is None, all match."""
    out = []
    for mod in ALL:
        when = getattr(mod, "WHEN", ["*"])
        if "*" in when or (kind and kind in when):
            out.append(mod)
    return out


def all_domains() -> list[str]:
    """Every domain across all investigators -- used by live_log alignment."""
    seen = set()
    for mod in ALL:
        for d in getattr(mod, "DOMAINS", []):
            seen.add(d.lower())
    return sorted(seen)
