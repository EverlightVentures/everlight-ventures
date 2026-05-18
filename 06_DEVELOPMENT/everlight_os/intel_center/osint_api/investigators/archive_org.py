"""Archive.org Wayback availability + recent snapshots."""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "Archive.org / Wayback"
DOMAINS = ["archive.org", "web.archive.org", "wayback-api.archive.org"]
WHEN = ["domain", "company", "person"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}
    q = target.strip()
    # If target has spaces, search archive search; else assume URL
    if " " not in q:
        url = q if q.startswith("http") else f"https://{q}"
        avail_url = f"https://archive.org/wayback/available?url={quote(url)}"
        status, text, err = await fetch(http, avail_url, timeout=8)
        raw["wayback_available"] = {"status": status, "len": len(text), "err": err}
        if status == 200:
            import json as _json
            try:
                data = _json.loads(text)
                snap = data.get("archived_snapshots", {}).get("closest", {})
                if snap:
                    findings.append({"label": "Wayback snapshot",
                                     "value": snap.get("timestamp", ""),
                                     "url": snap.get("url", "")})
                    findings.append({"label": "Snapshot HTTP",
                                     "value": str(snap.get("status", "?"))})
            except Exception:
                pass
    # Also: archive.org item search
    search_url = f"https://archive.org/advancedsearch.php?q={quote(q)}&fl[]=identifier&fl[]=title&output=json&rows=5"
    status, text, err = await fetch(http, search_url, timeout=8)
    raw["search"] = {"status": status, "len": len(text)}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            for d in data.get("response", {}).get("docs", [])[:5]:
                findings.append({"label": "Archive item",
                                 "value": d.get("title", "")[:100],
                                 "url": f"https://archive.org/details/{d.get('identifier','')}"})
        except Exception:
            pass

    return {"ok": len(findings) > 0,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "archive_org"}
