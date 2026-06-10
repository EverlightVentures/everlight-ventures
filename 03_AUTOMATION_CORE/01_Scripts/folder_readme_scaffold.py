#!/usr/bin/env python3
"""
folder_readme_scaffold.py -- make the AA_MY_DRIVE tree self-documenting.

Rich's complaint: you open a folder and nothing explains what's in it, what it's
for, or how it connects to the rest. This walks the meaningful parts of the tree
and drops a standard README.md "outline" into any folder that lacks one.

What each generated README contains:
  - the folder name + a Purpose line (auto-filled from a known-folder map, else a TODO)
  - Status + last-updated date
  - "What's in here" -- an AUTO-GENERATED listing of immediate subfolders + notable
    files (this is the part that answers "what's in the folder" with zero human effort)
  - "Connects to" -- a placeholder for the human/agent to wire relationships
  - a footer pointer back to the spine (00_MASTER_GAMEPLAN) + WORKSPACE_MANIFEST

Design rules:
  - IDEMPOTENT: never overwrites an existing README.md. Safe to re-run forever.
  - SCOPED: only walks the roots you point it at, to a max depth, and skips the
    junk/heavy dirs (archives, backups, caches, vendor, .git) so it documents the
    LIVING tree, not the graveyard.
  - DRY-RUN by default. Pass --apply to actually write.

Usage:
  python3 folder_readme_scaffold.py                 # dry-run, default roots
  python3 folder_readme_scaffold.py --apply          # write the stubs
  python3 folder_readme_scaffold.py --apply --depth 2 --roots 06_DEVELOPMENT
"""
from __future__ import annotations
import argparse
import datetime as _dt
from pathlib import Path

DRIVE = Path("/mnt/sdcard/AA_MY_DRIVE")
TODAY = _dt.date.today().isoformat()

# Folders we never document (graveyard / vendor / regenerable). Matched case-insensitively
# against any path component.
SKIP_NAMES = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".next",
    ".cache", "regenerable_caches", "trash_dedupe", "system_snapshots", "old_phone_dumps",
    "takeout", ".mcp_archive", ".env_archive", "protondrive", ".stfolder",
}
SKIP_SUBSTRINGS = ("archive", "_backup", "backups", "sync_conflicts", "snapshot")

# Default roots to document (the LIVING tree) + how deep to go into each.
DEFAULT_ROOTS = {
    ".": 0,                     # the 12 top-level folders themselves (depth 0 = just them)
    "01_BUSINESSES": 2,
    "02_CONTENT_FACTORY": 1,
    "03_AUTOMATION_CORE": 1,
    "05_PERSONAL": 1,
    "06_DEVELOPMENT": 1,
    "09_DASHBOARD": 1,
    "_state": 1,
}

# Known-folder purpose map -- gives instant real content for the folders that matter.
PURPOSE = {
    "01_BUSINESSES": "All revenue-generating ventures. Everlight_Ventures (the holdco brand) + onyx_pos.",
    "02_CONTENT_FACTORY": "Content pipeline: inbox -> queue -> published, plus brand assets and KDP metadata.",
    "03_AUTOMATION_CORE": "The automation engine: cron scripts, configs, credentials vault, Slack/AI tools. The part that runs while you sleep.",
    "04_MEDIA_LIBRARY": "Media assets: game builds, music, photos, screenshots.",
    "05_PERSONAL": "Rich's personal life: finance (incl. the gameplan + Overhead OS), training, learning, life-admin.",
    "06_DEVELOPMENT": "All code: the XLM bot, everlight_os (Hive + infra), MCP servers, SaaS, the public site.",
    "07_STAGING": "Holding pen for unsorted/incoming files. Sort OUT of here into a real home.",
    "08_BACKUPS": "Cold storage + backups. Not a working area. Do not build here.",
    "09_DASHBOARD": "Dashboards + reports: Django ops center, Streamlit analytics, FastAPI browser, generated reports.",
    "_state": "Live coordination state: AGENT_MAILBOX (cross-device family board), moltbook state, sync queues, blinko outbox.",
    "_logs": "Hive run logs, war-room logs, branded-mailer audit. Machine logs, not docs.",
    "supabase": "Source of truth for production data: SQL migrations + edge functions.",
    "Everlight_Ventures": "The holding company. Each subfolder is a venture or a shared function under the Everlight umbrella.",
    "Wealth_OS": "The wealth architecture (T0-T11 tiers, L1-L7 layers, engines). START at 00_MASTER_GAMEPLAN.md.",
    "Broker_OS": "The wholesale real-estate engine -- the deal matchmaking + Open Deal buyer page. Funds Phase 0 of the gameplan.",
    "Everlight_Caviar": "Caviar brokerage venture (domestic farmed drop-ship). The long-cycle passive tail of the gameplan.",
    "Everlight_Cannabis": "Cannabis grow venture docs. The apex/passion rung -- sealed, separate, years out.",
    "xlm_bot": "LIVE leverage trading bot (Oracle Micro, 24/7). Currently R&D -- net negative, not yet a funding pillar.",
    "everlight_os": "The Hive Mind brain: agent roster, knowledge base, infra stacks, docs, intel center.",
    "mcp_servers": "MCP server implementations -- the auth + logging boundary to external systems.",
    "hivemind_saas": "Hive Mind SaaS product codebase.",
}

ITAL = "(describe this folder's purpose -- one or two sentences, then delete this line)"


def should_skip(p: Path) -> bool:
    name = p.name.lower()
    if name in SKIP_NAMES:
        return True
    return any(s in name for s in SKIP_SUBSTRINGS)


def listing(folder: Path) -> str:
    """Auto-generated 'what's in here' from immediate children."""
    subdirs, files = [], []
    try:
        for child in sorted(folder.iterdir()):
            if child.name.startswith(".") or child.name == "README.md":
                continue
            if child.is_dir():
                if not should_skip(child):
                    subdirs.append(child.name)
            else:
                files.append(child.name)
    except PermissionError:
        return "_(could not read folder contents)_\n"
    lines = []
    if subdirs:
        lines.append("**Subfolders:**")
        for d in subdirs:
            lines.append(f"- `{d}/` -- (what it holds)")
        lines.append("")
    if files:
        notable = [f for f in files if f.lower().endswith((".md", ".py", ".html", ".yaml", ".yml", ".json", ".sh"))]
        shown = notable[:15] if notable else files[:15]
        lines.append(f"**Key files** ({len(files)} total):")
        for f in shown:
            lines.append(f"- `{f}`")
        if len(files) > len(shown):
            lines.append(f"- ... and {len(files) - len(shown)} more")
        lines.append("")
    if not subdirs and not files:
        lines.append("_(empty)_\n")
    return "\n".join(lines)


def render(folder: Path) -> str:
    name = folder.name if folder != DRIVE else "AA_MY_DRIVE (root)"
    purpose = PURPOSE.get(folder.name, ITAL)
    rel_root = "../" * (len(folder.relative_to(DRIVE).parts)) or "./"
    return f"""# {name}

**Purpose:** {purpose}
**Status:** Active
**Last updated:** {TODAY}

## What's in here

{listing(folder)}
## Connects to

- (which other folders feed this one, or read from it -- wire these in)

---
*Map: [`WORKSPACE_MANIFEST.md`]({rel_root}WORKSPACE_MANIFEST.md) -- the full tree.
Gameplan spine: `01_BUSINESSES/Everlight_Ventures/Wealth_OS/00_MASTER_GAMEPLAN.md`.
This README was scaffolded by `folder_readme_scaffold.py`; fill the Purpose + Connects-to by hand.*
"""


def walk(root: Path, max_depth: int):
    base_depth = len(root.relative_to(DRIVE).parts)
    if max_depth == 0:
        yield root
        return
    yield root
    for p in root.rglob("*"):
        if not p.is_dir() or should_skip(p):
            continue
        if any(should_skip(parent) for parent in p.relative_to(DRIVE).parents):
            continue
        depth = len(p.relative_to(DRIVE).parts) - base_depth
        if 0 < depth <= max_depth:
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry-run)")
    ap.add_argument("--depth", type=int, default=None, help="override max depth for all roots")
    ap.add_argument("--roots", nargs="*", default=None, help="override root list")
    args = ap.parse_args()

    roots = DEFAULT_ROOTS
    if args.roots is not None:
        roots = {r: (args.depth if args.depth is not None else 1) for r in args.roots}
    elif args.depth is not None:
        roots = {r: args.depth for r in DEFAULT_ROOTS}

    seen, created, skipped = set(), 0, 0
    for root_name, max_depth in roots.items():
        root = DRIVE if root_name == "." else DRIVE / root_name
        if not root.exists():
            continue
        # for ".", document the 12 top-level dirs themselves
        targets = [DRIVE] if root_name == "." else []
        if root_name == ".":
            targets += [d for d in sorted(DRIVE.iterdir())
                        if d.is_dir() and not d.name.startswith(".") and not should_skip(d)]
        else:
            targets = list(walk(root, max_depth))
        for folder in targets:
            if folder in seen:
                continue
            seen.add(folder)
            readme = folder / "README.md"
            if readme.exists():
                skipped += 1
                continue
            rel = folder.relative_to(DRIVE)
            if args.apply:
                readme.write_text(render(folder), encoding="utf-8")
                created += 1
                print(f"  + {rel}/README.md")
            else:
                created += 1
                print(f"  [dry-run] would create {rel}/README.md")

    mode = "WROTE" if args.apply else "DRY-RUN (use --apply to write)"
    print(f"\n{mode}: {created} READMEs, {skipped} already had one, {len(seen)} folders scanned.")


if __name__ == "__main__":
    main()
