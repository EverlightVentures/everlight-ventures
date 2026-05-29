#!/usr/bin/env python3
"""
placeholder_truth_audit.py -- catch placeholders masquerading as real.

Born 2026-05-29 from the chris_buy_box.json incident: a config file labeled its
own values "Placeholder ... Rich to confirm" yet the live daily pipeline filtered
real leads against those guessed zips/year/price for weeks. Operator: "there has
to be some sort of system audit to recognize all of these similar inconsistencies."

This scans config + data + code for things that ANNOUNCE they are not real (or
look fake), so provisional values never silently drive production. It is the
enforcement arm of the "Prove real, don't claim it" doctrine.

Stdlib only (runs on the phone proot). Cron-friendly. Exit code = CRITICAL count
(0 = clean), so it can gate CI / fire a Slack alert like the other audits.

Usage:
    python3 placeholder_truth_audit.py [--root DIR] [--json OUT.json] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DEFAULT = "/mnt/sdcard/AA_MY_DRIVE"

# Directories we never scan (noise, not production truth).
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "08_BACKUPS", "regenerable_caches", ".cache", "dist", "build",
    "site-packages", ".next", ".pytest_cache", "04_MEDIA_LIBRARY",
}

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".sh"}
DATA_EXT = {".json", ".csv", ".yaml", ".yml", ".env"}
DOC_EXT = {".md", ".txt"}

# (regex, severity, why). CRITICAL = provisional value that can drive production.
# Case-insensitive. Order matters only for first-match labeling.
PATTERNS = [
    (r"\bplace ?holder\b", "CRITICAL", "explicitly a placeholder"),
    (r"\bbest[- ]?guess\b", "CRITICAL", "value is a guess"),
    (r"\b(rich|operator) to (confirm|refine|replace|verify|fill)", "CRITICAL", "awaiting operator confirmation"),
    (r"\b(confirm|replace) with .* actual\b", "CRITICAL", "real value not yet substituted"),
    (r"\b(dummy|fake|sample|mock|fixture) data\b", "CRITICAL", "non-real data"),
    (r"\bnot (yet )?(real|wired|implemented|live)\b", "HIGH", "declared not-real"),
    (r"\bhardcoded (default|placeholder|value)\b", "HIGH", "hardcoded provisional value"),
    (r"raise NotImplementedError", "HIGH", "unimplemented code path"),
    (r"#\s*(MOCK|STUB|FAKE)\b", "HIGH", "stub/mock marker"),
    (r"\bTODO\b|\bFIXME\b|\bXXX\b", "MEDIUM", "unfinished marker"),
    (r"\bchange ?me\b|\byour[-_](api[-_]?key|token|domain|secret)\b", "MEDIUM", "unfilled template token"),
    (r"<(your|insert|replace|fill)[^>]*>", "MEDIUM", "angle-bracket template token"),
    (r"\blorem ipsum\b", "MEDIUM", "lorem placeholder text"),
]

# Fake-looking values that matter MORE inside data/config than in docs/code.
DATA_FAKE = [
    (r"@example\.(com|org|net)\b", "CRITICAL", "example.com address in data"),
    (r"@(test|fake|dummy)\.[a-z]{2,}\b", "CRITICAL", "fake email domain in data"),
    (r"\b555-?01\d\d\b|\b555-?555-?\d{4}\b", "HIGH", "555 fake phone in data"),
    (r"\bfaisalman\.com\b", "CRITICAL", "known scraper-placeholder domain"),
    (r"\b(123-?456-?7890|000-?000-?0000)\b", "HIGH", "obviously fake phone"),
    (r"\b(John|Jane) Doe\b", "MEDIUM", "placeholder name in data"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), sev, why) for p, sev, why in PATTERNS]
COMPILED_DATA = [(re.compile(p, re.IGNORECASE), sev, why) for p, sev, why in DATA_FAKE]

# Lines that are legitimate, NOT defects -- exclude before flagging.
IGNORE_LINE = [
    re.compile(r"placeholder\s*[=:]", re.IGNORECASE),       # HTML/JSX/CSS input placeholder attr
    re.compile(r"placeholder-for-preset-env"),               # npm package name
    re.compile(r"::?placeholder\b"),                          # CSS ::placeholder selector
    re.compile(r"setplaceholder|getplaceholder|placeholdertext", re.IGNORECASE),
]
# Files that are not our production truth (third-party / lockfiles).
IGNORE_FILE = re.compile(r"(package-lock\.json|yarn\.lock|pnpm-lock|\.min\.(js|css)$|composer\.lock)")

SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
MAX_LINE = 240  # skip minified / data blob lines longer than this


def _iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            if ext in CODE_EXT or ext in DATA_EXT or ext in DOC_EXT:
                yield Path(dirpath) / fn, ext


def scan_file(path: Path, ext: str) -> list[dict]:
    hits = []
    if IGNORE_FILE.search(str(path)):
        return hits
    is_data = ext in DATA_EXT
    is_doc = ext in DOC_EXT
    is_code = ext in CODE_EXT
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except Exception:
        return hits
    for n, raw in enumerate(lines, 1):
        if len(raw) > MAX_LINE:
            continue
        if any(ig.search(raw) for ig in IGNORE_LINE):
            continue  # legit UI placeholder attr / CSS selector / npm name
        checks = COMPILED + (COMPILED_DATA if is_data else [])
        for rx, sev, why in checks:
            m = rx.search(raw)
            if not m:
                continue
            eff_sev = sev
            # Context-sensitive severity for the bare word "placeholder":
            #   data/config -> CRITICAL (can drive production with fake values)
            #   code        -> HIGH     (a stub/unfinished path, real but lower urgency)
            #   doc         -> MEDIUM   (docs may legitimately discuss placeholders)
            if why == "explicitly a placeholder":
                eff_sev = "CRITICAL" if is_data else ("HIGH" if is_code else "MEDIUM")
            elif is_doc and sev == "CRITICAL":
                eff_sev = "MEDIUM"
            hits.append({
                "file": str(path),
                "line": n,
                "severity": eff_sev,
                "why": why,
                "match": m.group(0)[:60],
                "snippet": raw.strip()[:160],
            })
            break  # one hit per line is enough
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT_DEFAULT)
    ap.add_argument("--json", default="")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    all_hits: list[dict] = []
    for path, ext in _iter_files(root):
        all_hits.extend(scan_file(path, ext))

    all_hits.sort(key=lambda h: (SEV_RANK.get(h["severity"], 9), h["file"], h["line"]))
    crit = [h for h in all_hits if h["severity"] == "CRITICAL"]
    high = [h for h in all_hits if h["severity"] == "HIGH"]
    med = [h for h in all_hits if h["severity"] == "MEDIUM"]

    if args.json:
        Path(args.json).write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "root": str(root),
            "counts": {"critical": len(crit), "high": len(high), "medium": len(med)},
            "hits": all_hits,
        }, indent=2))

    if not args.quiet:
        print("=" * 72)
        print("PLACEHOLDER / TRUTH AUDIT  --  'Prove real, don't claim it'")
        print(f"root: {root}")
        print(f"CRITICAL={len(crit)}  HIGH={len(high)}  MEDIUM={len(med)}")
        print("=" * 72)
        # CRITICAL in full (these can drive production with fake values)
        print("\n--- CRITICAL (provisional/fake value that can drive production) ---")
        for h in crit[:60]:
            rel = h["file"].replace(str(root) + "/", "")
            print(f"  {rel}:{h['line']}  [{h['why']}]")
            print(f"      > {h['snippet']}")
        if len(crit) > 60:
            print(f"  ... +{len(crit) - 60} more CRITICAL")
        # HIGH summarized by file
        if high:
            print(f"\n--- HIGH ({len(high)}) by file ---")
            byfile: dict[str, int] = {}
            for h in high:
                rel = h["file"].replace(str(root) + "/", "")
                byfile[rel] = byfile.get(rel, 0) + 1
            for f, c in sorted(byfile.items(), key=lambda x: -x[1])[:25]:
                print(f"  {c:3d}  {f}")
        print(f"\nMEDIUM: {len(med)} (TODO/FIXME/template tokens -- run with --json for full list)")

    return len(crit)


if __name__ == "__main__":
    sys.exit(main())
