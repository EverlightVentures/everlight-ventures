"""OpenCorporates company search (free tier, no auth required)."""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "OpenCorporates"
DOMAINS = ["opencorporates.com", "api.opencorporates.com"]
WHEN = ["company"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    api_url = f"https://api.opencorporates.com/v0.4/companies/search?q={quote(target)}"
    status, text, err = await fetch(http, api_url, timeout=10)
    raw["api_search"] = {"status": status, "len": len(text), "err": err}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            results = data.get("results", {}).get("companies", [])[:8]
            for c in results:
                co = c.get("company", {})
                findings.append({
                    "label": co.get("jurisdiction_code", "?").upper() + " — " +
                             (co.get("company_type", "") or "company"),
                    "value": (co.get("name", "") + " · " + (co.get("incorporation_date", "") or "")),
                    "url": co.get("opencorporates_url", ""),
                })
        except Exception as e:
            findings.append({"label": "Parse error", "value": str(e)[:80]})

    # HTML search fallback (works without API limits)
    html_url = f"https://opencorporates.com/companies?q={quote(target)}&utf8=%E2%9C%93"
    findings.append({"label": "HTML search",
                     "value": "Open in browser",
                     "url": html_url})
    await fetch(http, html_url, timeout=8, method="HEAD")

    return {"ok": len(findings) > 1,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "opencorporates"}
