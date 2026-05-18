"""Breach + leak databases: HaveIBeenPwned + Dehashed (links only without API keys)."""
from urllib.parse import quote
from ._common import fetch, head, now_ms

NAME = "Leak Check"
DOMAINS = ["haveibeenpwned.com", "dehashed.com", "intelx.io", "leakcheck.io"]
WHEN = ["email", "domain", "person"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    # HIBP requires user-supplied API key for breach query, but breaches by-domain is web-accessible
    if "@" in target:
        # email -- just provide the search link (HIBP API needs key)
        hibp_url = f"https://haveibeenpwned.com/account/{quote(target)}"
        status = await head(http, hibp_url)
        raw["hibp_account"] = {"status": status}
        findings.append({"label": "HIBP search", "value": f"HTTP {status}", "url": hibp_url})
    else:
        # Treat as domain
        hibp_url = f"https://haveibeenpwned.com/api/v3/breaches?domain={quote(target)}"
        status, text, err = await fetch(http, hibp_url, timeout=8)
        raw["hibp_breaches"] = {"status": status, "len": len(text)}
        if status == 200:
            import json as _json
            try:
                data = _json.loads(text)
                for b in data[:10]:
                    findings.append({
                        "label": b.get("Name", "Breach"),
                        "value": f"{b.get('PwnCount',0):,} accounts · {b.get('BreachDate','')}",
                        "url": f"https://haveibeenpwned.com/PwnedWebsites#{b.get('Name','')}",
                    })
            except Exception:
                pass

    # Dehashed search page (no API)
    deh_url = f"https://dehashed.com/search?query={quote(target)}"
    findings.append({"label": "Dehashed", "value": "Search (login required)", "url": deh_url})
    await head(http, deh_url)
    # Intelligence X
    intelx_url = f"https://intelx.io/?s={quote(target)}"
    findings.append({"label": "Intelligence X", "value": "Search", "url": intelx_url})
    await head(http, intelx_url)

    return {"ok": True, "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "leak_check"}
