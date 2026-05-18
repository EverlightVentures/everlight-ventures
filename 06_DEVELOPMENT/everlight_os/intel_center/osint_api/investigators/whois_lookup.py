"""WHOIS lookup via free public APIs."""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "WHOIS Lookup"
DOMAINS = ["rdap.verisign.com", "rdap.org", "who.is"]
WHEN = ["domain", "company"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}
    # If target looks like a domain, query RDAP. If a company, derive likely TLD.
    domain = target.strip().lower()
    if " " in domain:
        # Company name -- try .com first
        domain = domain.split()[0].replace(",", "") + ".com"

    rdap_url = f"https://rdap.verisign.com/com/v1/domain/{quote(domain)}"
    status, text, err = await fetch(http, rdap_url, timeout=8)
    raw["rdap_verisign"] = {"status": status, "len": len(text), "err": err}

    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            findings.append({"label": "Domain", "value": data.get("ldhName", domain),
                             "url": f"https://{domain}"})
            for ev in data.get("events", [])[:3]:
                findings.append({"label": ev.get("eventAction", "event").title(),
                                 "value": ev.get("eventDate", "")})
            for entity in data.get("entities", [])[:5]:
                roles = ", ".join(entity.get("roles", []))
                handle = entity.get("handle", "")
                findings.append({"label": f"Entity ({roles})",
                                 "value": handle})
        except Exception as e:
            findings.append({"label": "Parse error", "value": str(e)[:80]})

    # Fallback hint: who.is HTML scrape (most domains)
    fallback_url = f"https://who.is/whois/{quote(domain)}"
    findings.append({"label": "Detail link", "value": fallback_url, "url": fallback_url})
    await fetch(http, fallback_url, timeout=8, method="HEAD")

    return {"ok": status == 200 or len(findings) > 0,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "whois"}
