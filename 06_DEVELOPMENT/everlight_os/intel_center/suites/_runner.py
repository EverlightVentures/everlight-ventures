"""
Shared runner for category suites. Each suite is a thin wrapper around `run_category()`
that picks its target category from the resources DB and HTTP-fetches every domain.

Success = HTTP 200-399, recorded in cache/live_log.sqlite via osint_api.live_log.

This is what turns the resource catalogue from a directory into living infrastructure.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center")
DB = ROOT / "database" / "everlight_resources.sqlite"
sys.path.insert(0, str(ROOT))
from osint_api import live_log  # noqa: E402

GOLD = "\033[38;5;179m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


UA_DESKTOP = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
UA_BOT = "Mozilla/5.0 (compatible; EverlightIntel/1.0)"


def _curl_once(scheme: str, domain: str, method: str, ua: str, timeout: int) -> tuple[int, int, str | None]:
    """One curl probe. Returns (code, bytes, error)."""
    flags = ["-sIL"] if method == "HEAD" else ["-sL", "--max-filesize", "200000"]
    size_field = "%{size_header}" if method == "HEAD" else "%{size_download}"
    try:
        r = subprocess.run(
            ["curl", *flags, "--max-time", str(timeout),
             "-A", ua, "-o", "/dev/null",
             "-w", f"%{{http_code}}|{size_field}",
             f"{scheme}://{domain}"],
            capture_output=True, text=True, timeout=timeout + 3,
        )
        out = r.stdout.strip()
        if r.returncode == 0 and "|" in out:
            code, _, size = out.partition("|")
            try:
                return int(code), int(size or 0), None
            except ValueError:
                return 0, 0, "parse-error"
        return 0, 0, f"curl rc={r.returncode}"
    except subprocess.TimeoutExpired:
        return 0, 0, "timeout"
    except Exception as e:
        return 0, 0, str(e)[:60]


def _fetch_one(domain: str, timeout: int = 12) -> tuple[int, int, str | None]:
    """
    Aggressive liveness probe. Try in order:
      1. HTTPS HEAD with desktop UA
      2. HTTPS HEAD with bot UA
      3. HTTPS GET with desktop UA
      4. HTTP HEAD with desktop UA (some old sites HTTPS-broken)
      5. HTTP GET with desktop UA
    First 2xx/3xx wins. 4xx/5xx returned as-is for visibility (the audit
    classifier downstream decides 'auth_gated' vs 'dead').
    """
    attempts = [
        ("https", "HEAD", UA_DESKTOP),
        ("https", "HEAD", UA_BOT),
        ("https", "GET",  UA_DESKTOP),
        ("http",  "HEAD", UA_DESKTOP),
        ("http",  "GET",  UA_DESKTOP),
    ]
    last_code = 0; last_size = 0; last_err = None
    for scheme, method, ua in attempts:
        code, size, err = _curl_once(scheme, domain, method, ua, timeout)
        if 200 <= code < 400:
            return code, size, None
        # Hold onto any non-zero code as the "real" status for downstream classification
        if code and code > last_code:
            last_code, last_size, last_err = code, size, err
    return last_code, last_size, last_err


def run_category(category: str, max_workers: int = 6, timeout: int = 10,
                 only_domains: list[str] | None = None,
                 triggered_by: str | None = None) -> dict:
    """Pull every domain in a category, log results, return summary."""
    if triggered_by is None:
        # Derive from category name as 'suite:news_brief' style
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
        triggered_by = f"suite:{slug}"
    con = sqlite3.connect(DB)
    if only_domains:
        domains = [d.lower() for d in only_domains]
    else:
        domains = [d for (d,) in con.execute(
            "SELECT DISTINCT domain FROM resources WHERE category=? AND domain != ''",
            (category,),
        ).fetchall()]
    con.close()

    if not domains:
        print(f"{RED}No domains for category {category!r}.{RESET}")
        return {"category": category, "total": 0, "ok": 0, "results": []}

    print(f"\n{GOLD}== Suite: {category} =={RESET}")
    print(f"  pulling {len(domains)} domains, {max_workers} workers, {timeout}s timeout each\n")
    t0 = time.time()
    results = []
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one, d, timeout): d for d in domains}
        for fut in cf.as_completed(futures):
            d = futures[fut]
            status, size, err = fut.result()
            live_log.record(d, status_code=status, bytes_received=size,
                            method="HEAD/GET", error=err,
                            triggered_by=triggered_by)
            success = status and 200 <= status < 400
            if success:
                ok += 1
                print(f"  {GREEN}✓{RESET} {GOLD}{d:<32}{RESET} HTTP {status}  {size:>7}b")
            else:
                print(f"  {RED}✗{RESET} {DIM}{d:<32} HTTP {status or '-'}  {err or ''}{RESET}")
            results.append({"domain": d, "status": status, "bytes": size, "error": err})

    elapsed = time.time() - t0
    print(f"\n{GOLD}Done: {ok}/{len(domains)} live ({ok*100//max(len(domains),1)}%) in {elapsed:.1f}s{RESET}")
    return {"category": category, "total": len(domains), "ok": ok,
            "elapsed_sec": round(elapsed, 1), "results": results}


def run_all() -> None:
    """Run every suite in this directory."""
    suites_dir = Path(__file__).parent
    names = [p.stem for p in sorted(suites_dir.glob("*.py"))
             if not p.stem.startswith("_") and p.stem != "__init__"]
    print(f"{GOLD}Running {len(names)} suites: {', '.join(names)}{RESET}\n")
    grand_total = 0
    grand_ok = 0
    for n in names:
        try:
            mod = __import__(f"suites.{n}", fromlist=["main"])
            r = mod.main()
            if r:
                grand_total += r.get("total", 0)
                grand_ok += r.get("ok", 0)
        except Exception as e:
            print(f"{RED}suite {n} crashed: {e}{RESET}")

    print(f"\n{GOLD}{'='*60}{RESET}")
    print(f"{GOLD}TOTAL across all suites: {grand_ok} live / {grand_total} attempted "
          f"({grand_ok*100//max(grand_total,1)}%){RESET}")
    print(f"{GOLD}{'='*60}{RESET}")
    print(f"\nRun {GOLD}intel live-audit{RESET} for the post-suite snapshot.")
