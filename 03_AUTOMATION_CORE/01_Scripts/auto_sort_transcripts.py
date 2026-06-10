#!/usr/bin/env python3
"""
auto_sort_transcripts.py

Hybrid classifier for new transcripts dropped into 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/.
Runs keyword match first; falls back to Claude Haiku only on ambiguity.

For each unclassified .txt or .md file at the root level:
  1. Score against the keyword map (per-folder weighted keywords).
  2. If top score leads runner-up by >= CONFIDENCE_MARGIN, route deterministically.
  3. Else call Claude Haiku with first 2000 chars + folder list; pick folder + 2-sentence synopsis.
  4. Rename to clean snake_case based on title extracted from first line or filename.
  5. Move to the target folder.
  6. Append to the folder's SUMMARY.md under a "Recent Additions" section.
  7. Generate a suggested work order appended to TODO_AGENTS.md (as DRAFT, human-gated).
  8. Log to Blinko with the correct fire-team tag.

Safe to run repeatedly. Only processes files in Trranscripts/ root (ignores folders).

Usage:
    python3 auto_sort_transcripts.py              # dry run
    python3 auto_sort_transcripts.py --apply      # actually move + update

Env:
    ANTHROPIC_API_KEY   required for LLM fallback (optional; without it, skips ambiguous files)
    BLINKO_URL          default http://163.192.19.196:1111
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import urllib.request as _rq
    import urllib.error as _re_err
except ImportError:
    sys.exit("Need python stdlib urllib. This script runs on Oracle E5 or phone Termux.")

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts")
LOGFILE = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/auto_sort_transcripts.log")
BLINKO_URL = os.environ.get("BLINKO_URL", "http://163.192.19.196:1111")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-haiku-4-5-20251001"
CONFIDENCE_MARGIN = 3  # top score must beat runner-up by this margin

# ---------------------------------------------------------------------------
# KEYWORD MAP: folder -> list of (keyword, weight) pairs.
# Weight 3 = strong signal, 2 = moderate, 1 = weak.
#
# >>> TUNE THIS MAP TO YOUR BUSINESS BIAS. <<<
# For example, if you want every transcript mentioning "XLM" to go to
# 01_Claude_and_Codex (because Rex T handles it), add ("xlm", 3) there.
# Your edits here override my default taxonomy.
# ---------------------------------------------------------------------------
KEYWORD_MAP: dict[str, list[tuple[str, int]]] = {
    "01_Claude_and_Codex": [
        ("claude code", 3), ("openrouter", 3), ("codex", 3), ("anthropic", 2),
        ("claude mythos", 3), ("opus 4", 2), ("sonnet", 2), ("claude in finance", 3),
        ("any model any app", 2),
    ],
    "02_AI_Agents_and_Swarms": [
        ("hermes agent", 3), ("agent swarm", 3), ("browser harness", 3),
        ("browser use", 2), ("multi-agent", 2), ("autonomous agent", 3),
        ("mirofish", 3), ("prediction swarm", 2), ("slack ai agent", 3),
        ("self-improving", 2), ("swarm intelligence", 3),
    ],
    "03_Slack_and_Communication": [
        ("slack tutorial", 3), ("slack channel", 2), ("slack canvas", 3),
        ("google chat", 2), ("remote work", 2), ("team communication", 2),
        ("master slack", 3), ("async communication", 2),
    ],
    "04_Self_Hosting_and_Offline_AI": [
        ("ollama", 3), ("offline", 2), ("kiwix", 3), ("wikipedia offline", 3),
        ("jellyfin", 3), ("paperclip", 3), ("self-hosted", 3), ("hostinger", 2),
        ("private ai", 3), ("secondbrain", 3), ("open webui", 2),
        ("local llm", 3), ("prepper", 2), ("download the internet", 3),
    ],
    "05_OSINT_and_Security": [
        ("osint", 3), ("spiderfoot", 3), ("maltego", 3), ("theharvester", 3),
        ("recon-ng", 3), ("shodan", 2), ("hexstrike", 3), ("fabric opensource", 3),
        ("google dorking", 3), ("find anyone online", 3), ("pen test", 3),
        ("security testing", 2), ("skip trace", 2), ("doxxing", 2),
    ],
    "06_Knowledge_Management": [
        ("obsidian", 3), ("ideaverse", 3), ("maps of content", 3), ("moc", 2),
        ("note-taking", 2), ("zettelkasten", 2), ("file over app", 3),
        ("nick milo", 3), ("logseq", 2), ("101 ways to use ai", 3),
    ],
    "07_Content_Creation_Video": [
        ("capcut", 3), ("sora", 3), ("suno", 3), ("nano banana", 3),
        ("google flow", 2), ("video generation", 2), ("faceless youtube", 3),
        ("scrape leads", 3), ("monetize ai video", 3), ("tiktok shop", 2),
        ("ai commerce", 3), ("ai affiliate", 3), ("dropship", 2),
    ],
    "08_Spreadsheets_and_Ops": [
        ("excel", 3), ("chatgpt for excel", 3), ("google sheets", 2),
        ("grist", 3), ("libreoffice", 2), ("spreadsheet", 2),
        ("formula", 1), ("pivot table", 2),
    ],
    "09_Research_and_Perplexity": [
        ("perplexity", 3), ("perplexity spaces", 3), ("sonar api", 3),
        ("perplexity computer", 3), ("comet browser", 2), ("answer engine", 2),
    ],
    "10_Sales_and_Services": [
        ("ai receptionist", 3), ("vapi", 3), ("retell", 3), ("elevenlabs", 2),
        ("shopify", 2), ("woocommerce", 2), ("medusa", 2), ("launch a store", 3),
        ("dropshipping", 2), ("cryptocurrency", 3), ("smart contract", 2),
        ("erc-20", 3), ("$4500", 3),
    ],
}

FIRE_TEAM_MAP: dict[str, str] = {
    "01_Claude_and_Codex": "Forge",
    "02_AI_Agents_and_Swarms": "Forge + Piper",
    "03_Slack_and_Communication": "Marcus + Cupid",
    "04_Self_Hosting_and_Offline_AI": "Forge + Cipher",
    "05_OSINT_and_Security": "Cipher + Justine",
    "06_Knowledge_Management": "Marcus + Cipher",
    "07_Content_Creation_Video": "Piper + writer",
    "08_Spreadsheets_and_Ops": "Penny + Filter",
    "09_Research_and_Perplexity": "Cipher",
    "10_Sales_and_Services": "Hammer + Forge",
}


def _log(msg: str) -> None:
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with LOGFILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _slugify(name: str, max_len: int = 80) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^Default_medium_", "", stem)
    stem = re.sub(r"_[A-Za-z0-9_-]{11}$", "", stem)
    stem = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower()
    return stem[:max_len] or "untitled_transcript"


def score_keywords(text: str) -> dict[str, int]:
    blob = text.lower()
    scores: dict[str, int] = {k: 0 for k in KEYWORD_MAP}
    for folder, pairs in KEYWORD_MAP.items():
        for kw, weight in pairs:
            if kw in blob:
                scores[folder] += weight
    return scores


def classify_keywords(text: str) -> tuple[str, str] | None:
    scores = score_keywords(text)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, runner = ranked[0], ranked[1]
    if top[1] == 0:
        return None
    if top[1] - runner[1] >= CONFIDENCE_MARGIN:
        return top[0], f"keyword match (score {top[1]} vs {runner[1]})"
    return None


def classify_llm(text: str) -> tuple[str, str] | None:
    if not ANTHROPIC_KEY:
        _log("  SKIP: no ANTHROPIC_API_KEY set; ambiguous file left in place")
        return None
    folders_list = "\n".join(f"- {k}" for k in KEYWORD_MAP)
    prompt = (
        f"You are classifying a video transcript into exactly ONE topic folder.\n\n"
        f"Available folders:\n{folders_list}\n\n"
        f"Transcript excerpt (first 2000 chars):\n{text[:2000]}\n\n"
        f"Respond as JSON only. Shape: "
        f'{{"folder":"<exact folder name>","synopsis":"<2 sentences>","reason":"<one phrase>"}}'
    )
    body = json.dumps(
        {
            "model": MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    req = _rq.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with _rq.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (_re_err.URLError, TimeoutError, json.JSONDecodeError) as exc:
        _log(f"  ERR: LLM call failed: {exc}")
        return None
    content = data.get("content", [])
    if not content:
        return None
    raw = content[0].get("text", "")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    folder = parsed.get("folder", "").strip()
    if folder not in KEYWORD_MAP:
        return None
    return folder, f"LLM classification: {parsed.get('reason', 'unknown')}"


def extract_synopsis(text: str) -> str:
    para = text.strip().split("\n")[0][:400]
    return para.strip() or "(no synopsis extracted)"


def append_to_summary(folder: Path, entry: dict[str, str]) -> None:
    summary = folder / "SUMMARY.md"
    if not summary.exists():
        _log(f"  WARN: {summary} missing; skipping summary update")
        return
    marker = "## Recent Additions (Auto-Classified)"
    existing = summary.read_text(encoding="utf-8")
    block = (
        f"\n- `{entry['filename']}` ({entry['date']}) "
        f"[{entry['reason']}] - {entry['synopsis'][:200]}\n"
    )
    if marker in existing:
        existing = existing.replace(marker, marker + block, 1)
    else:
        existing += f"\n\n{marker}\n{block}"
    summary.write_text(existing, encoding="utf-8")


def append_to_todo(folder: Path, entry: dict[str, str]) -> None:
    todo = folder / "TODO_AGENTS.md"
    if not todo.exists():
        return
    fire_team = FIRE_TEAM_MAP.get(folder.name, "Marcus")
    marker = "## Auto-Generated Draft Work Orders"
    existing = todo.read_text(encoding="utf-8")
    block = (
        f"\n### DRAFT - Review {entry['filename']} ({entry['date']})\n"
        f"**Suggested owner**: {fire_team}\n\n"
        f"1. Read `{entry['filename']}`\n"
        f"2. Decide: port any pattern into Hive, evaluate-only, or skip\n"
        f"3. If porting: write the full WO, assign owner, move this DRAFT out\n"
        f"4. Log decision to Blinko with tag `#hive/{folder.name.lower()}`\n"
    )
    if marker in existing:
        existing = existing.replace(marker, marker + block, 1)
    else:
        existing += f"\n\n{marker}\n{block}"
    todo.write_text(existing, encoding="utf-8")


def log_blinko(folder_name: str, filename: str, synopsis: str, reason: str) -> None:
    fire_team = FIRE_TEAM_MAP.get(folder_name, "Marcus")
    content = (
        f"# Transcript Auto-Classified: {filename}\n\n"
        f"#hive/transcript #hive/auto-sort #hive/{folder_name.lower()}\n\n"
        f"**Folder**: {folder_name}\n"
        f"**Assigned**: {fire_team}\n"
        f"**Reason**: {reason}\n\n"
        f"**Synopsis**: {synopsis}\n\n"
        f"Draft WO appended to {folder_name}/TODO_AGENTS.md for human review."
    )
    body = json.dumps({"content": content, "type": 1}).encode("utf-8")
    req = _rq.Request(
        f"{BLINKO_URL}/api/v1/note/upsert",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with _rq.urlopen(req, timeout=10) as _:
            pass
    except Exception as exc:
        _log(f"  WARN: Blinko log failed: {exc}")


def process_file(path: Path, apply: bool) -> None:
    _log(f"Processing: {path.name}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log(f"  ERR: read failed: {exc}")
        return

    hit = classify_keywords(text)
    if not hit:
        _log("  keyword ambiguous; trying LLM")
        hit = classify_llm(text)
    if not hit:
        _log("  UNCLASSIFIED: leaving in place for manual review")
        return

    folder_name, reason = hit
    dest_dir = ROOT / folder_name
    if not dest_dir.exists():
        _log(f"  ERR: destination folder missing: {dest_dir}")
        return

    slug = _slugify(path.name)
    dest = dest_dir / f"{slug}{path.suffix}"
    synopsis = extract_synopsis(text)

    entry = {
        "filename": dest.name,
        "folder": folder_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "synopsis": synopsis,
        "reason": reason,
    }

    _log(f"  -> {folder_name}/{dest.name} ({reason})")

    if not apply:
        _log("  DRY RUN: no changes written")
        return

    if dest.exists():
        dest = dest.with_name(f"{slug}_{int(time.time())}{path.suffix}")
    shutil.move(str(path), str(dest))
    append_to_summary(dest_dir, entry)
    append_to_todo(dest_dir, entry)
    log_blinko(folder_name, dest.name, synopsis, reason)
    _log("  done")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually move + update; omit for dry run")
    args = parser.parse_args()

    if not ROOT.exists():
        _log(f"ROOT missing: {ROOT}")
        return 1

    candidates = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in {".txt", ".md"}]
    candidates = [p for p in candidates if p.name not in {"MASTER_PRIORITIZATION.md", "SYSTEM_STATE.md", "USAGE_GUIDE.md"}]

    if not candidates:
        _log("No new transcripts at root. Clean.")
        return 0

    _log(f"Found {len(candidates)} candidate(s). Apply={args.apply}")
    for p in candidates:
        process_file(p, args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
