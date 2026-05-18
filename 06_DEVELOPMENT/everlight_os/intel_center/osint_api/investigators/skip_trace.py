"""
Skip-trace -- wraps the existing Wholesale/skip_trace/cascade.py if available,
falls back to URL-generation for the operator to manually open.
"""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "Skip-Trace"
DOMAINS = ["truepeoplesearch.com", "fastpeoplesearch.com", "zabasearch.com",
           "thatsthem.com", "spokeo.com", "whitepages.com"]
WHEN = ["person", "phone"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    # Generate skip-trace URLs for every public source (HEAD-ping each so live_log fires)
    name = target.strip().replace(" ", "%20")
    sources = [
        ("TruePeopleSearch", f"https://www.truepeoplesearch.com/results?name={name}"),
        ("FastPeopleSearch", f"https://www.fastpeoplesearch.com/name/{name.replace('%20','-').lower()}"),
        ("ZabaSearch", f"https://www.zabasearch.com/people/{name.replace('%20','+')}"),
        ("ThatsThem", f"https://thatsthem.com/name/{name.replace('%20','-')}"),
        ("Whitepages", f"https://www.whitepages.com/name/{name.replace('%20','-')}"),
    ]
    for label, url in sources:
        status = await __import__("osint_api.investigators._common", fromlist=["head"]).head(http, url, timeout=6)
        raw[label] = {"status": status}
        findings.append({
            "label": label,
            "value": f"HTTP {status}{' (open in browser)' if status >= 400 else ''}",
            "url": url,
        })

    # Try the existing cascade.py wrapper if installed
    try:
        import sys
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/skip_trace")
        import cascade  # type: ignore
        if hasattr(cascade, "trace"):
            r = cascade.trace(target)
            if r:
                findings.insert(0, {"label": "cascade.py result",
                                    "value": str(r)[:200]})
    except Exception:
        pass

    return {"ok": True,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "skip_trace"}
