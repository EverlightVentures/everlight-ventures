"""Property records search -- public county records + Zillow link generators."""
from urllib.parse import quote
from ._common import fetch, head, now_ms

NAME = "Property Records"
DOMAINS = ["zillow.com", "realtor.com", "redfin.com", "trulia.com", "homes.com"]
WHEN = ["address"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}
    addr = target.strip().replace(" ", "+")

    sources = [
        ("Zillow", f"https://www.zillow.com/homes/{addr}_rb/"),
        ("Realtor", f"https://www.realtor.com/realestateandhomes-search/{addr}"),
        ("Redfin", f"https://www.redfin.com/stingray/do/location-autocomplete?location={addr}"),
        ("Trulia", f"https://www.trulia.com/home/{addr}"),
        ("Homes.com", f"https://www.homes.com/{addr}/"),
    ]
    for label, url in sources:
        status = await head(http, url, timeout=6)
        raw[label] = status
        findings.append({"label": label,
                         "value": f"HTTP {status}{' (open)' if status else ''}",
                         "url": url})

    return {"ok": True, "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "property_records"}
