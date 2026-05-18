"""SEC EDGAR company search -- US public companies + filings."""
from urllib.parse import quote
from ._common import fetch, now_ms

NAME = "SEC EDGAR"
DOMAINS = ["sec.gov", "efts.sec.gov", "data.sec.gov"]
WHEN = ["company"]


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings = []
    raw = {}

    # EDGAR full-text search
    search_url = f"https://efts.sec.gov/LATEST/search-index?q={quote(target)}&dateRange=custom&forms=10-K,10-Q,8-K"
    status, text, err = await fetch(http, search_url, timeout=8)
    raw["fulltext_search"] = {"status": status, "len": len(text), "err": err}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            hits = data.get("hits", {}).get("hits", [])[:6]
            for h in hits:
                src = h.get("_source", {})
                findings.append({
                    "label": src.get("form", "filing").upper(),
                    "value": (src.get("display_names", [""])[0] or "") + " -- " +
                             (src.get("file_date", "")),
                    "url": f"https://www.sec.gov/Archives/edgar/data/{src.get('cik','')}/{src.get('adsh','').replace('-','')}/{src.get('id','')}",
                })
        except Exception as e:
            findings.append({"label": "Parse error", "value": str(e)[:80]})

    # Company tickers JSON (catalog)
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    status, text, err = await fetch(http, tickers_url, timeout=8)
    raw["tickers_catalog"] = {"status": status, "len": len(text), "err": err}
    if status == 200:
        import json as _json
        try:
            data = _json.loads(text)
            target_lc = target.lower()
            for _, entry in list(data.items())[:5000]:
                if target_lc in entry.get("title", "").lower() or \
                   target_lc == entry.get("ticker", "").lower():
                    findings.append({
                        "label": "Ticker " + entry.get("ticker", ""),
                        "value": entry.get("title", "") + f" (CIK {entry.get('cik_str', '')})",
                        "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={entry.get('cik_str','')}",
                    })
                    if len([f for f in findings if "Ticker" in f["label"]]) >= 3:
                        break
        except Exception:
            pass

    return {"ok": len(findings) > 0,
            "findings": findings, "raw": raw,
            "elapsed_ms": now_ms() - t0,
            "investigator": NAME, "investigator_id": "sec_edgar"}
