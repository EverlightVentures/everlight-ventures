"""osint_skiptrace.py - Free / FOSS skip-trace helper for wholesale leads.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/top_7_osint_tools_revealed.txt
Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/how_to_find_anyone_online.txt

Consolidates several public lookups into one call so Rex Blackwell and Filter Banks
have a free first-pass before paying SkipGenius. Not a replacement for paid
skip-trace at scale; a budget booster.

Sources queried:
- Google (via Places details and Programmable Search) -- if key available
- Hunter.io (free tier) -- emails tied to a domain
- theHarvester CLI -- if installed locally
- SpiderFoot CLI -- if installed locally

CLI:
    python3 osint_skiptrace.py --name "John Smith" --city "Atlanta" --state "GA"
    python3 osint_skiptrace.py --domain "example.com"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_env_loaded = False


def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    env = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    _env_loaded = True


def query_hunter(domain: str) -> dict[str, Any]:
    _load_env()
    api_key = os.environ.get("HUNTER_API_KEY", "")
    if not api_key:
        return {"source": "hunter", "skipped": "no HUNTER_API_KEY set"}
    url = f"https://api.hunter.io/v2/domain-search?domain={urllib.parse.quote(domain)}&api_key={api_key}&limit=10"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        emails = [e["value"] for e in data.get("data", {}).get("emails", [])]
        return {"source": "hunter", "emails": emails, "count": len(emails)}
    except Exception as e:
        return {"source": "hunter", "error": str(e)}


def query_the_harvester(domain: str) -> dict[str, Any]:
    """theHarvester CLI. Pip install: theHarvester. Free."""
    try:
        result = subprocess.run(
            ["theHarvester", "-d", domain, "-b", "bing,duckduckgo,rapiddns", "-l", "50"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        emails = [line.strip() for line in result.stdout.splitlines()
                  if "@" in line and len(line.strip()) < 80]
        return {"source": "theHarvester", "emails": emails[:50], "count": len(emails)}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"source": "theHarvester", "skipped": str(e)}


def query_spiderfoot(target: str) -> dict[str, Any]:
    """SpiderFoot CLI. Needs `spiderfoot` installed + a running instance or cli mode."""
    try:
        result = subprocess.run(
            ["sf-cli", "-m", "sfp_whois,sfp_dnsraw", "-t", target],
            capture_output=True,
            text=True,
            timeout=90,
        )
        return {"source": "spiderfoot", "raw": result.stdout[:4000]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"source": "spiderfoot", "skipped": str(e)}


def skiptrace_by_name(name: str, city: str = "", state: str = "") -> dict[str, Any]:
    """Light search: use Google Programmable Search engine if PLACES key exists,
    else return instructions for manual lookup.
    """
    _load_env()
    q = " ".join(x for x in [name, city, state] if x)
    # We do NOT want to run open-web scraping here; return pointer URLs only
    return {
        "source": "manual_lookup_pointers",
        "google_search": f"https://www.google.com/search?q={urllib.parse.quote(q)}",
        "linkedin_search": f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(q)}",
        "truepeoplesearch": f"https://www.truepeoplesearch.com/results?name={urllib.parse.quote(name)}&citystatezip={urllib.parse.quote(f'{city} {state}')}",
        "fastpeoplesearch": f"https://www.fastpeoplesearch.com/name/{urllib.parse.quote(name.replace(' ', '-'))}_{state}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--city", default="")
    ap.add_argument("--state", default="")
    ap.add_argument("--domain")
    args = ap.parse_args()

    results: list[dict[str, Any]] = []
    if args.domain:
        results.append(query_hunter(args.domain))
        results.append(query_the_harvester(args.domain))
        results.append(query_spiderfoot(args.domain))
    if args.name:
        results.append(skiptrace_by_name(args.name, args.city, args.state))

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
