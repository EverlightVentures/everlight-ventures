"""Domain threat intel: VirusTotal, urlscan, AlienVault OTX, crt.sh, SecurityTrails."""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "Domain Intel"
DOMAINS = ["virustotal.com", "urlscan.io", "otx.alienvault.com",
           "crt.sh", "securitytrails.com", "shodan.io", "censys.io"]
WHEN = ["domain"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}
    domain = target.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")

    # crt.sh -- free SSL cert transparency log
    crt_url = f"https://crt.sh/?q={quote(domain)}&output=json"
    status, text, err = await fetch(http, crt_url, timeout=10)
    raw["crt_sh"] = {"status": status, "len": len(text)}
    if status == 200 and text and text.startswith("["):
        import json as _json
        try:
            data = _json.loads(text)
            seen_names = set()
            for entry in data[:50]:
                for nm in (entry.get("name_value", "") or "").split("\n"):
                    if nm and nm not in seen_names:
                        seen_names.add(nm)
            findings.append({"label": "Subdomains (crt.sh)",
                             "value": f"{len(seen_names)} certificates",
                             "url": crt_url.replace("&output=json", "")})
            for nm in list(seen_names)[:8]:
                findings.append({"label": "Subdomain", "value": nm})
        except Exception:
            pass

    # urlscan public search (no auth)
    urlscan_url = f"https://urlscan.io/api/v1/search/?q=domain:{quote(domain)}&size=5"
    status, text, err = await fetch(http, urlscan_url, timeout=8)
    raw["urlscan"] = {"status": status, "len": len(text)}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            for r in data.get("results", [])[:5]:
                p = r.get("page", {})
                findings.append({
                    "label": "URLscan submission",
                    "value": p.get("url", "")[:120],
                    "url": r.get("result", ""),
                })
        except Exception:
            pass

    # AlienVault OTX pulses
    otx_url = f"https://otx.alienvault.com/api/v1/indicators/domain/{quote(domain)}/general"
    status, text, err = await fetch(http, otx_url, timeout=8)
    raw["otx"] = {"status": status, "len": len(text)}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            pulse_count = data.get("pulse_info", {}).get("count", 0)
            findings.append({"label": "OTX threat pulses", "value": str(pulse_count),
                             "url": f"https://otx.alienvault.com/indicator/domain/{domain}"})
        except Exception:
            pass

    # HEAD-ping VirusTotal + SecurityTrails public pages
    vt_url = f"https://www.virustotal.com/gui/domain/{quote(domain)}"
    findings.append({"label": "VirusTotal", "value": "Open in browser", "url": vt_url})
    await fetch(http, vt_url, timeout=6, method="HEAD")
    st_url = f"https://securitytrails.com/domain/{quote(domain)}"
    findings.append({"label": "SecurityTrails", "value": "Open in browser", "url": st_url})
    await fetch(http, st_url, timeout=6, method="HEAD")

    return {"ok": len(findings) > 2,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "domain_intel"}
