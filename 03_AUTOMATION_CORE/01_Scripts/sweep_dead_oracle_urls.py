#!/usr/bin/env python3
"""
sweep_dead_oracle_urls.py -- workspace-wide remap of dead Oracle URLs to local.

Usage:
    python3 sweep_dead_oracle_urls.py --dry-run     # default; print proposed changes only
    python3 sweep_dead_oracle_urls.py --apply       # actually write changes

Mapping table (per the 2026-05-12 dashboard reorg):
  http://163.192.19.196:8504              -> http://127.0.0.1:2200
  http://163.192.19.196:8000              -> http://127.0.0.1:2201
  http://129.159.38.250:8504              -> http://127.0.0.1:2200
  http://129.159.38.250:8502              -> http://127.0.0.1:2100
  http://129.159.38.250:8080/lucrex/      -> KEEP + flag (Next.js, future band 2700)
  http://129.159.38.250:1111              -> KEEP + flag (Blinko, planned for e5-mother)
  http://129.159.38.250:5678              -> KEEP + flag (n8n parked permanently)
  http://163.192.19.196:8676              -> http://127.0.0.1:2300
  http://163.192.19.196:8677              -> http://127.0.0.1:2301

Skips: .bak.*, _logs/, cache/, .git/, node_modules/, .pyc, *.html (rendered snapshots)
Refuses to touch .json/.yaml unless --include-config is passed.
Writes diff log to _DASHBOARDS/SWEEP_LOG_<date>.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_PATH = ROOT / "_DASHBOARDS" / f"SWEEP_LOG_{datetime.now().strftime('%Y-%m-%d')}.md"

# (regex, replacement, label) tuples in order of evaluation.
# Order matters: more specific patterns first.
MAPPINGS = [
    (r"http://163\.192\.19\.196:8504", "http://127.0.0.1:2200", "163.196:8504->2200"),
    (r"http://163\.192\.19\.196:8000",  "http://127.0.0.1:2201", "163.196:8000->2201"),
    (r"http://163\.192\.19\.196:8676",  "http://127.0.0.1:2300", "163.196:8676->2300"),
    (r"http://163\.192\.19\.196:8677",  "http://127.0.0.1:2301", "163.196:8677->2301"),
    (r"http://129\.159\.38\.250:8504",  "http://127.0.0.1:2200", "129.250:8504->2200"),
    (r"http://129\.159\.38\.250:8502",  "http://127.0.0.1:2100", "129.250:8502->2100"),
]

# Patterns that get FLAGGED (not remapped) because no local equivalent yet
FLAG_ONLY = [
    (r"http://129\.159\.38\.250:8080/lucrex", "lucrex (Next.js, awaits 2700-band rehome)"),
    (r"http://129\.159\.38\.250:1111",         "blinko RAG (planned for e5-mother)"),
    (r"http://129\.159\.38\.250:5678",         "n8n (parked permanently 2026-04-24)"),
]

SKIP_DIRS = {"__pycache__", "node_modules", ".git", "_logs", "cache",
             "Memphis Property Downloads", ".cache"}
SKIP_SUFFIXES = {".pyc", ".html", ".png", ".jpg", ".jpeg", ".webp",
                 ".sqlite", ".db", ".pdf", ".mp4", ".zip", ".apk", ".key",
                 ".bak", ".whl", ".o", ".so", ".exe"}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".ini"}
SKIP_NAME_PATTERNS = [r"\.bak\.", r"\.swp$"]


def should_skip(path: Path, include_config: bool) -> tuple[bool, str]:
    # Skip self -- mapping table contains the patterns it would otherwise rewrite
    if path.name == "sweep_dead_oracle_urls.py":
        return True, "skip_self"
    parts = set(path.parts)
    for d in SKIP_DIRS:
        if d in parts:
            return True, f"skip_dir:{d}"
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True, f"skip_suffix:{path.suffix}"
    if path.suffix.lower() in CONFIG_SUFFIXES and not include_config:
        return True, f"skip_config:{path.suffix}"
    for pat in SKIP_NAME_PATTERNS:
        if re.search(pat, path.name):
            return True, f"skip_pattern:{pat}"
    # Skip the sweep log itself
    if "SWEEP_LOG" in path.name:
        return True, "skip_sweep_log"
    return False, ""


def process_file(path: Path, apply: bool) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"path": str(path), "error": str(e), "remapped": 0, "flagged": 0}

    original = text
    remapped = 0
    flagged = 0
    remap_log: list[str] = []
    flag_log: list[str] = []

    for pattern, replacement, label in MAPPINGS:
        n = len(re.findall(pattern, text))
        if n:
            text = re.sub(pattern, replacement, text)
            remapped += n
            remap_log.append(f"{label}: {n}")

    for pattern, label in FLAG_ONLY:
        n = len(re.findall(pattern, text))
        if n:
            flagged += n
            flag_log.append(f"{label}: {n}")

    if apply and text != original:
        path.write_text(text, encoding="utf-8")

    return {
        "path": str(path.relative_to(ROOT)),
        "remapped": remapped,
        "flagged": flagged,
        "remap_log": remap_log,
        "flag_log": flag_log,
        "wrote": apply and text != original,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (otherwise dry-run)")
    ap.add_argument("--include-config", action="store_true",
                    help="also touch .json/.yaml/.toml/.ini files")
    ap.add_argument("--limit", type=int, default=0, help="limit files processed (debug)")
    args = ap.parse_args()

    apply = args.apply
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"=== sweep_dead_oracle_urls.py [{mode}] ===")

    # Find candidate files via grep first (fast)
    import subprocess
    grep = subprocess.run(
        ["grep", "-rln", "-E", "163\\.192\\.19\\.196|129\\.159\\.38\\.250", str(ROOT)],
        capture_output=True, text=True
    )
    candidates = [Path(line) for line in grep.stdout.splitlines() if line.strip()]
    print(f"grep candidates: {len(candidates)}")

    results = []
    skipped = []
    for p in candidates:
        skip, reason = should_skip(p, args.include_config)
        if skip:
            skipped.append((p, reason))
            continue
        if args.limit and len(results) >= args.limit:
            break
        r = process_file(p, apply)
        if r.get("remapped") or r.get("flagged") or r.get("error"):
            results.append(r)

    # Write log
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Dead-Oracle URL Sweep -- {mode}",
        f"**Run:** {datetime.now().isoformat()}",
        f"**Mode:** {mode}",
        f"**Candidates from grep:** {len(candidates)}",
        f"**Skipped:** {len(skipped)}  (suffix/dir/config filters)",
        f"**Files with hits:** {len(results)}",
        "",
        "## Mapping table",
        "| Pattern | Replacement | Label |",
        "|---|---|---|",
    ]
    for pat, repl, lbl in MAPPINGS:
        lines.append(f"| `{pat}` | `{repl}` | {lbl} |")
    lines.append("")
    lines.append("## Per-file results")
    lines.append("| File | Remapped | Flagged | Detail |")
    lines.append("|---|---|---|---|")
    total_remapped = 0
    total_flagged = 0
    for r in results:
        if r.get("error"):
            lines.append(f"| `{r['path']}` | ERROR | - | {r['error']} |")
            continue
        detail_parts = r.get("remap_log", []) + [f"FLAG {x}" for x in r.get("flag_log", [])]
        detail = "; ".join(detail_parts) if detail_parts else "-"
        lines.append(f"| `{r['path']}` | {r['remapped']} | {r['flagged']} | {detail} |")
        total_remapped += r["remapped"]
        total_flagged += r["flagged"]
    lines.append("")
    lines.append(f"**TOTALS:** {total_remapped} remapped, {total_flagged} flagged across {len(results)} files.")

    LOG_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"log written to: {LOG_PATH}")
    print(f"TOTALS: {total_remapped} remapped, {total_flagged} flagged across {len(results)} files.")
    if not apply:
        print(f"\nThis was DRY-RUN. Re-run with --apply to commit changes.")


if __name__ == "__main__":
    main()
