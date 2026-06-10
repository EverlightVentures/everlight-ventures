"""context_loader -- pulls Rich's local config + memory + recent state into a
single text block the desktop_agent can drop into its system prompt.

Per Rich (2026-05-06): the agent should KNOW his aliases, configs, shortcuts,
settings, memory files, workspace tree, and Blinko before it tries to operate.

Sources (in priority order):
  1. ~/.claude/projects/-AA-MY-DRIVE/memory/MEMORY.md  (index of feedback/project memories)
  2. Selected feedback memories that affect agent behavior
  3. ~/.zshrc filtered for agent-relevant aliases
  4. /AA_MY_DRIVE/CLAUDE.md doctrine excerpts (high-level only)
  5. Recent git log (last 5 commits) -- shows what's just changed
  6. Recent task completions (last 3 done/failed envelopes)
  7. Blinko (best-effort, skipped if unreachable -- Oracle E5 may be dead)

Output: a markdown block, ~2-4k tokens, ready to embed in system prompt.
Cache_control wrapping is the caller's job.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

WORKSPACE = Path("/AA_MY_DRIVE")
MEMORY_DIR = Path.home() / ".claude/projects/-AA-MY-DRIVE/memory"
ZSHRC = Path.home() / ".zshrc"
CLAUDE_MD = WORKSPACE / "CLAUDE.md"
MANIFEST = WORKSPACE / "WORKSPACE_MANIFEST.md"
TASKS_ROOT = WORKSPACE / "_logs/browser_tasks"
BLINKO_URL = "http://163.192.19.196:1111/api/v1/note/list"  # Oracle E5

# Keep the prompt under control
MAX_BYTES_PER_SECTION = 2000


def _read_truncated(p: Path, max_bytes: int = MAX_BYTES_PER_SECTION) -> str:
    """Read a file but truncate at max_bytes."""
    if not p.exists():
        return ""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) <= max_bytes:
            return text
        return text[:max_bytes] + f"\n... [truncated at {max_bytes} bytes; full at {p}]"
    except Exception:
        return ""


def _filter_aliases(zshrc_text: str) -> str:
    """Pull only agent/runner/lucrex-relevant aliases from .zshrc."""
    lines = []
    for line in zshrc_text.splitlines():
        s = line.strip()
        if not s.startswith("alias "):
            continue
        if any(k in s.lower() for k in ("agent-", "runner-", "lucrex", "hive", "psc")):
            lines.append(line)
    return "\n".join(lines) if lines else "(no agent-related aliases found)"


def _git_log_recent(n: int = 5) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(WORKSPACE), "log", "--oneline", "--no-decorate", f"-{n}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return "(git log unavailable)"


def _recent_tasks(n: int = 3) -> str:
    """List the last N completed/failed browser tasks for context."""
    rows = []
    for state in ("done", "failed"):
        d = TASKS_ROOT / state
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:n]:
            try:
                d_ = json.loads(p.read_text(encoding="utf-8"))
                title = (d_.get("title") or "")[:60]
                res = d_.get("result") or {}
                status = res.get("status", state)
                iters = res.get("iterations", "?")
                rows.append(f"  - {state}: {p.name[:24]} '{title}' status={status} iters={iters}")
            except Exception:
                continue
    rows.sort(reverse=True)
    return "\n".join(rows[:n]) if rows else "(no recent tasks)"


def _blinko_recent(n: int = 5) -> str:
    """Best-effort Blinko fetch. If Oracle E5 is dead, returns a note."""
    try:
        import urllib.request, urllib.error
        req = urllib.request.Request(
            BLINKO_URL, method="POST",
            data=json.dumps({"page": 1, "size": n, "isArchived": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode())
            notes = data.get("data") or data
            if not isinstance(notes, list):
                return "(Blinko returned unexpected schema)"
            rows = []
            for note in notes[:n]:
                if isinstance(note, dict):
                    title = (note.get("content") or "")[:80].replace("\n", " ")
                    rows.append(f"  - {title}")
            return "\n".join(rows) if rows else "(no Blinko notes)"
    except Exception as e:
        return f"(Blinko unreachable: {type(e).__name__})"


def _select_memory_files(max_files: int = 6) -> list[Path]:
    """Pick the highest-value memory files for the agent's context."""
    if not MEMORY_DIR.is_dir():
        return []
    # Priority order: index first, then feedback that affects behavior
    priority_keywords = (
        "MEMORY",                  # the index
        "feedback_workflow",        # vim hjkl, em-dash rules, etc
        "feedback_autonomous",      # do everything except OAuth
        "feedback_capture",         # never refuse, always capture
        "feedback_compliance",      # green light = ship
        "feedback_trust",           # trust the setup
        "project_outbound_halt",    # current critical project
    )
    files = list(MEMORY_DIR.glob("*.md"))
    selected = []
    for kw in priority_keywords:
        for f in files:
            if kw.lower() in f.name.lower() and f not in selected:
                selected.append(f)
                if len(selected) >= max_files:
                    return selected
    return selected


def build_operational_context(*, include_blinko: bool = True,
                                include_manifest_excerpt: bool = True) -> str:
    """Return a single markdown block ready to inject into the agent's system
    prompt. Roughly 2-4k tokens depending on what's available."""
    parts = ["<RICH_OPERATIONAL_CONTEXT>"]
    parts.append("This block is loaded from Rich's local configs at task dispatch.\n"
                 "Use it to operate consistently with how he runs his system.\n")

    # 1. Memory index + selected feedback memories
    mem_index = MEMORY_DIR / "MEMORY.md"
    if mem_index.exists():
        parts.append("## Memory index (Rich's persistent preferences)")
        parts.append(_read_truncated(mem_index, 1500))
    selected = _select_memory_files(6)
    if selected:
        parts.append("\n## Key feedback memories (read in full)")
        for f in selected:
            if f.name == "MEMORY.md":
                continue
            parts.append(f"\n### {f.name}")
            parts.append(_read_truncated(f, 1200))

    # 2. Filtered aliases
    if ZSHRC.exists():
        parts.append("\n## Agent-relevant shell aliases")
        parts.append("```bash")
        parts.append(_filter_aliases(ZSHRC.read_text(encoding="utf-8", errors="replace")))
        parts.append("```")

    # 3. Workspace manifest excerpt (top of file = routing rules)
    if include_manifest_excerpt and MANIFEST.exists():
        parts.append("\n## Workspace routing rules (top of WORKSPACE_MANIFEST.md)")
        parts.append(_read_truncated(MANIFEST, 1500))

    # 4. Recent git activity
    parts.append("\n## Recent commits (last 5)")
    parts.append("```")
    parts.append(_git_log_recent(5))
    parts.append("```")

    # 5. Recent task history
    parts.append("\n## Recent desktop_runner task history")
    parts.append(_recent_tasks(5))

    # 6. Blinko (best-effort)
    if include_blinko:
        parts.append("\n## Blinko recent notes (knowledge base)")
        parts.append(_blinko_recent(5))

    parts.append("\n</RICH_OPERATIONAL_CONTEXT>")
    return "\n".join(parts)


if __name__ == "__main__":
    # CLI: print the context for debugging
    print(build_operational_context())
