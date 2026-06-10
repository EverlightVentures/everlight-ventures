"""cipher_sonar_research.py - Cipher's Perplexity-driven prospect research.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/09_Research_and_Perplexity/perplexity_beginner_to_pro.txt
Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/09_Research_and_Perplexity/perplexity_computer_clearly_explained.txt

Per AI Consulting prospect, generate a sourced research brief using the Perplexity Sonar API.
Briefs are written as markdown into `01_BUSINESSES/Everlight_Ventures/AI_Consulting/research/<slug>/`.
Each brief has: company snapshot, recent news, pain-point hypotheses, tech-stack hints, key people,
sources cited with URLs.

Hammer reads the brief before every discovery call. Piper uses it to personalize outreach.

Usage:
    # Single prospect
    python3 cipher_sonar_research.py --name "Ivy Beauty Clinic" --url "https://ivybeauty.com"

    # Batch from CSV
    python3 cipher_sonar_research.py --batch prospects.csv

    # Weekly refresh of all existing briefs
    python3 cipher_sonar_research.py --refresh-all
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SONAR_URL = "https://api.perplexity.ai/chat/completions"
SONAR_MODEL = "sonar-pro"  # ~$5/1000 queries; adequate for prospect briefs
RESEARCH_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/AI_Consulting/research")

_key_loaded = False
_pplx_key = ""


def _load_key() -> str:
    global _key_loaded, _pplx_key
    if _key_loaded:
        return _pplx_key
    _pplx_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not _pplx_key:
        env = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("PERPLEXITY_API_KEY="):
                    _pplx_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    _key_loaded = True
    return _pplx_key


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s[:60] or "prospect"


def sonar_query(prompt: str, max_tokens: int = 1200) -> dict:
    """Call Sonar API. Returns {content, citations}."""
    key = _load_key()
    if not key:
        return {"content": "", "citations": [], "error": "no api key"}
    payload = {
        "model": SONAR_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "return_citations": True,
    }
    req = urllib.request.Request(
        SONAR_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"content": "", "citations": [], "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"content": "", "citations": [], "error": str(e)}
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    citations = data.get("citations", [])
    return {"content": content, "citations": citations}


def research_prospect(name: str, url: str = "", vertical: str = "", location: str = "") -> dict:
    """Generate a full prospect brief. Returns {snapshot, news, pain_points, tech_stack, people, citations}."""
    context_bits = [f"Business name: {name}"]
    if url:
        context_bits.append(f"Website: {url}")
    if vertical:
        context_bits.append(f"Vertical: {vertical}")
    if location:
        context_bits.append(f"Location: {location}")
    ctx = "\n".join(context_bits)

    prompts = {
        "snapshot": (
            f"{ctx}\n\n"
            "Summarize this business in 4 bullets: "
            "(1) what they do and who they serve, "
            "(2) approximate size and years in operation, "
            "(3) their key differentiator or market position, "
            "(4) any public pricing or service packaging. "
            "Be concise. Cite sources."
        ),
        "news": (
            f"{ctx}\n\n"
            "What are the 3 most recent (last 6 months) news items, announcements, or changes for this business? "
            "Include dates. Cite sources."
        ),
        "pain_points": (
            f"{ctx}\n\n"
            "Based on their industry and any reviews or public signals, what are the 3 most likely operational "
            "pain points this business has around customer communication, lead capture, or scheduling? "
            "Specifically: missed calls, booking friction, after-hours coverage, staffing. Cite sources where evidence exists."
        ),
        "tech_stack": (
            f"{ctx}\n\n"
            "What visible tools or platforms does this business appear to use (website builder, booking system, "
            "CRM, phone system)? Look at their public website for evidence. 3-5 bullets max."
        ),
        "people": (
            f"{ctx}\n\n"
            "Who are the 2-3 key decision-makers or owners? Names, titles, publicly visible LinkedIn or bio. "
            "Do not speculate; only include verifiable names. Cite sources."
        ),
    }

    results = {}
    all_citations: list[str] = []
    for key, prompt in prompts.items():
        r = sonar_query(prompt, max_tokens=700)
        results[key] = r.get("content", "").strip() or f"_(no data: {r.get('error','')})_"
        for c in r.get("citations", []):
            if c not in all_citations:
                all_citations.append(c)
    return {**results, "all_citations": all_citations}


def write_brief(name: str, data: dict, meta: dict) -> Path:
    slug = slugify(name)
    prospect_dir = RESEARCH_DIR / slug
    prospect_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = prospect_dir / f"brief_{today}.md"

    cits = "\n".join(f"- <{c}>" for c in data.get("all_citations", [])) or "_(no citations returned)_"

    md = f"""# Prospect Brief: {name}

**Generated**: {today} (UTC)
**Source**: Perplexity Sonar (sonar-pro)
**Owner**: Cipher
**Use**: Hammer reads this before every discovery call. Piper personalizes Email 1 from this.

---

## Meta

- Vertical: {meta.get("vertical", "") or "(unknown)"}
- Website: {meta.get("url", "") or "(unknown)"}
- Location: {meta.get("location", "") or "(unknown)"}
- Slug: `{slug}`

## Company snapshot

{data.get("snapshot", "(none)")}

## Recent news (last 6 months)

{data.get("news", "(none)")}

## Likely pain points

{data.get("pain_points", "(none)")}

## Visible tech stack

{data.get("tech_stack", "(none)")}

## Key people

{data.get("people", "(none)")}

## Sources cited

{cits}

---

## Next actions for Hammer

- [ ] Read this brief end-to-end
- [ ] Pick ONE pain point to anchor the discovery call around
- [ ] Prepare one question per section that goes beyond what this brief tells you
- [ ] Cross-check in Blinko: `grep "{slug}"` for any prior Hive notes on this prospect

## Next actions for Piper

- [ ] Incorporate one snapshot sentence into the Email 1 personalization hook
- [ ] Reference a recent-news item if one exists and is flattering
- [ ] If no visible CRM, the pitch should lead with "you have no central place for leads"
"""
    md_path.write_text(md, encoding="utf-8")
    # Also write JSON for programmatic use
    (prospect_dir / f"brief_{today}.json").write_text(json.dumps({**data, **meta}, indent=2))
    print(f"  wrote {md_path}")
    return md_path


def refresh_all() -> int:
    """Re-generate briefs for every prospect folder older than 7 days."""
    if not RESEARCH_DIR.exists():
        print("no research dir yet")
        return 0
    count = 0
    for slug_dir in RESEARCH_DIR.iterdir():
        if not slug_dir.is_dir():
            continue
        meta_path = slug_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            continue
        # Find most recent brief
        briefs = sorted(slug_dir.glob("brief_*.json"))
        if briefs:
            # Skip if last brief < 7 days old
            try:
                date_str = briefs[-1].stem.replace("brief_", "")
                last = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - last).days < 7:
                    continue
            except ValueError:
                pass
        name = meta.get("name") or slug_dir.name
        print(f"Refreshing {name}...")
        data = research_prospect(name, meta.get("url", ""), meta.get("vertical", ""), meta.get("location", ""))
        write_brief(name, data, meta)
        count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--url", default="")
    ap.add_argument("--vertical", default="")
    ap.add_argument("--location", default="")
    ap.add_argument("--batch", help="CSV with columns: name,url,vertical,location")
    ap.add_argument("--refresh-all", action="store_true")
    args = ap.parse_args()

    if args.refresh_all:
        n = refresh_all()
        print(f"refreshed {n} prospects")
        return 0

    prospects: list[dict] = []
    if args.name:
        prospects.append({
            "name": args.name,
            "url": args.url,
            "vertical": args.vertical,
            "location": args.location,
        })
    elif args.batch:
        with open(args.batch, newline="", encoding="utf-8") as f:
            prospects = list(csv.DictReader(f))
    else:
        ap.error("supply --name or --batch or --refresh-all")

    for p in prospects:
        name = p.get("name") or ""
        if not name:
            continue
        print(f"Researching {name}...")
        slug = slugify(name)
        slug_dir = RESEARCH_DIR / slug
        slug_dir.mkdir(parents=True, exist_ok=True)
        meta = {k: p.get(k, "") for k in ("name", "url", "vertical", "location")}
        (slug_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        data = research_prospect(name, p.get("url", ""), p.get("vertical", ""), p.get("location", ""))
        write_brief(name, data, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
