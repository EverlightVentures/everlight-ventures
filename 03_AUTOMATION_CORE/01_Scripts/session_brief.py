#!/usr/bin/env python3
"""Session-start rehydration: the read counterpart to session_export_to_mailbox.py.

`/exit` writes a handoff into _state/AGENT_MAILBOX.md at session end. Until this
script existed nothing read it back, so every export wrote into a void and each
new session started blank. This assembles the arrival briefing.

Sources, in order of how much they change:
  1. AGENT_MAILBOX.md   -- the last N session handoffs (what happened)
  2. DECISION_LOG.md    -- why forks went the way they did (the unrecoverable part)
  3. LIVING_PUNCHLIST   -- hot items only (what is on fire)
  4. git                 -- branch, last commit, uncommitted count (real repo state)

Usage:
    python3 session_brief.py                # default: 3 sessions, 5 decisions
    python3 session_brief.py --sessions 5
    python3 session_brief.py --json         # machine-readable
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
MAILBOX = WORKSPACE / "_state" / "AGENT_MAILBOX.md"
DECISIONS = WORKSPACE / "_state" / "DECISION_LOG.md"
PUNCHLIST = WORKSPACE / "LIVING_PUNCHLIST.md"

SESSION_HEADER = re.compile(r"^## \[(.+?)\] Session: (.*)$")
DECISION_HEADER = re.compile(r"^## \[(.+?)\] (.*)$")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _split_entries(text: str, pattern: re.Pattern) -> list[dict]:
    """Split a log file into entries keyed by its `## [stamp] title` headers."""
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            if current:
                entries.append(current)
            current = {"stamp": m.group(1), "title": m.group(2).strip(), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current:
        entries.append(current)
    for e in entries:
        e["body"] = "\n".join(e["body"]).strip()
    return entries


def _tail(entries: list[dict], n: int) -> list[dict]:
    """Last n entries. Guards the `lst[-0:]` trap, which returns everything."""
    return entries[-n:] if n > 0 else []


def recent_sessions(n: int) -> list[dict]:
    return _tail(_split_entries(_read(MAILBOX), SESSION_HEADER), n)


def recent_decisions(n: int) -> list[dict]:
    return _tail(_split_entries(_read(DECISIONS), DECISION_HEADER), n)


def hot_punchlist() -> list[str]:
    """Numbered items flagged hot or blocked and not yet done.

    Only numbered items count. Bullet lines starting with the same emoji are the
    status legend at the top of the file, not work. Items carrying the done mark
    are dropped even when flagged hot, since `70. hot-done` is finished work.
    """
    DONE, FIRE, BLOCKED = "\N{BALLOT BOX WITH CHECK}", "\N{FIRE}", "\N{WARNING SIGN}"
    out = []
    for line in _read(PUNCHLIST).splitlines():
        s = line.strip()
        if not re.match(r"^\d+[a-z]?\.", s):
            continue
        if DONE in s:
            continue
        if FIRE in s or BLOCKED in s:
            out.append(re.sub(r"\s+", " ", s)[:200])
    return out


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=WORKSPACE, capture_output=True,
                text=True, timeout=30,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    porcelain = run("status", "--porcelain")
    state = {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "last_commit": run("log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M"),
        "uncommitted": len([l for l in porcelain.splitlines() if l.strip()]),
    }
    # A stale index.lock silently fails every commit. It cost 16 days in July 2026,
    # so the briefing checks for it every single session now.
    lock = WORKSPACE / ".git" / "index.lock"
    state["stale_lock"] = lock.exists()
    return state


def render(sessions: list[dict], decisions: list[dict], hot: list[str], git: dict) -> str:
    L: list[str] = ["# SESSION BRIEF", ""]

    L.append("## Repo state")
    L.append(f"- Branch: `{git['branch']}`  |  Uncommitted: **{git['uncommitted']}**")
    L.append(f"- Last commit: {git['last_commit'] or 'unknown'}")
    if git["stale_lock"]:
        L.append("- **WARNING: .git/index.lock exists.** If no git process is running, "
                 "this is stale and every commit will fail silently. Clear it.")
    L.append("")

    L.append(f"## Last {len(sessions)} session(s)")
    if not sessions:
        L.append("- Mailbox empty. No prior handoff to load.")
    for s in sessions:
        L.append(f"### [{s['stamp']}] {s['title']}")
        keep = [ln for ln in s["body"].splitlines()
                if ln.strip().startswith(("-", "#")) and len(ln.strip()) > 3]
        L.extend(keep[:14])
        L.append("")

    L.append(f"## Last {len(decisions)} decision(s) and why")
    if not decisions:
        L.append("- Decision log empty. Reasoning from prior sessions is unrecovered.")
    for d in decisions:
        L.append(f"- **{d['title']}** ({d['stamp']})")
        for ln in d["body"].splitlines():
            if ln.strip().lower().startswith(("**why", "- **why", "why:")):
                L.append(f"  {ln.strip()}")
    L.append("")

    L.append("## Hot / blocked on the punch list")
    if not hot:
        L.append("- Nothing flagged hot.")
    L.extend(f"- {h}" for h in hot[:12])
    L.append("")

    L.append("## Read before acting")
    L.append("- Status above is what the files claim. Verify anything load-bearing "
             "against the live system before trusting it.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble the session-start briefing.")
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--decisions", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sessions = recent_sessions(args.sessions)
    decisions = recent_decisions(args.decisions)
    hot = hot_punchlist()
    git = git_state()

    if args.json:
        print(json.dumps({
            "ok": True, "sessions": sessions, "decisions": decisions,
            "hot": hot, "git": git,
            "sources": {
                "mailbox": str(MAILBOX), "decisions": str(DECISIONS),
                "punchlist": str(PUNCHLIST),
            },
        }, indent=2))
    else:
        print(render(sessions, decisions, hot, git))
    return 0


if __name__ == "__main__":
    sys.exit(main())
