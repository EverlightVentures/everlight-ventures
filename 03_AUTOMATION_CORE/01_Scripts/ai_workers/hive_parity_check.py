#!/usr/bin/env python3
"""
Hive Parity Check -- verifies that Claude, Gemini, and Codex are running off the
same agent firmware, skill library, and doctrine.

Walks the three trees, sha256s each file, reports drift. Operator Truth Doctrine:
failures lead, greens follow. Service-active is never proof; identical hashes are.

Exit codes:
    0  -- full parity (or only whitelisted drift)
    1  -- drift detected
    2  -- one or more trees missing entirely
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
CLAUDE_TREE = ROOT / ".claude"
GEMINI_TREE = ROOT / ".gemini"
CODEX_TREE = ROOT / ".codex"
GLOBAL_CLAUDE = Path("/root/.claude")
GLOBAL_PLUGINS = GLOBAL_CLAUDE / "plugins/marketplaces/claude-plugins-official/plugins"

REPORT_PATH = ROOT / "_logs/hive_parity_report.md"

# Categories we expect to be in lockstep across all three CLIs.
MIRRORED_CATEGORIES = ["agents", "skills"]

# Files that exist in Gemini/Codex but NOT in .claude/* on purpose --
# they originate from /root/.claude/ (global) or the plugin marketplace.
# Parity check should treat these as "valid shadow" not orphans.
def is_shadow_path(category: str, rel_path: str) -> bool:
    if category == "skills" and rel_path.startswith("_plugin_skills/"):
        return True
    if category == "agents":
        # File originates from /root/.claude/agents/ if it exists there.
        global_agent = GLOBAL_CLAUDE / "agents" / rel_path
        if global_agent.exists():
            return True
    return False

PT = ZoneInfo("America/Los_Angeles")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:12]


def sha_strip_frontmatter(path: Path) -> str:
    """Hash the file body AFTER stripping leading YAML frontmatter.
    Used to compare Gemini agents (which we wrap with frontmatter on mirror)
    against Claude/Codex agents (no frontmatter)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if raw.startswith("---\n"):
        # Drop the first frontmatter block.
        end = raw.find("\n---\n", 4)
        if end != -1:
            raw = raw[end + 5:]
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def index(tree: Path, category: str) -> dict[str, str]:
    """Map relative file path -> sha for every file under tree/category.
    For agents we compare BODY (frontmatter-stripped) across all three trees,
    because Gemini gets a synthesized frontmatter on files that don't have one
    natively. The body is the semantic content; the frontmatter is metadata."""
    base = tree / category
    if not base.exists():
        return {}
    strip_fm = (category == "agents")
    out: dict[str, str] = {}
    for p in base.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            rel = p.relative_to(base).as_posix()
            out[rel] = sha_strip_frontmatter(p) if strip_fm else sha(p)
    return out


def diff_category(category: str) -> dict:
    c = index(CLAUDE_TREE, category)
    g = index(GEMINI_TREE, category)
    x = index(CODEX_TREE, category)

    all_keys = set(c) | set(g) | set(x)
    drift: list[dict] = []
    missing_in_gemini: list[str] = []
    missing_in_codex: list[str] = []
    hash_mismatch: list[str] = []

    for k in sorted(all_keys):
        if k not in c:
            # Valid shadow (global agent or plugin skill)? Not an orphan.
            if is_shadow_path(category, k):
                # But Gemini and Codex must still agree with each other.
                if k in g and k in x and g[k] != x[k]:
                    hash_mismatch.append(f"{k} [shadow] (gemini={g[k]} codex={x[k]})")
                continue
            drift.append({"file": k, "issue": "exists in gemini/codex but NOT in canonical claude"})
            continue
        if k not in g:
            missing_in_gemini.append(k)
        if k not in x:
            missing_in_codex.append(k)
        if k in g and g[k] != c[k]:
            hash_mismatch.append(f"{k} (claude={c[k]} gemini={g[k]})")
        if k in x and x[k] != c[k]:
            hash_mismatch.append(f"{k} (claude={c[k]} codex={x[k]})")

    return {
        "category": category,
        "claude_count": len(c),
        "gemini_count": len(g),
        "codex_count": len(x),
        "missing_in_gemini": missing_in_gemini,
        "missing_in_codex": missing_in_codex,
        "hash_mismatch": hash_mismatch,
        "extra_orphans": [d for d in drift if d["issue"].startswith("exists")],
    }


def render(results: list[dict]) -> tuple[str, int]:
    stamp = datetime.now(PT).strftime("%Y-%m-%d %H:%M PT")
    lines = [
        f"# Hive Parity Report -- {stamp}",
        "",
        "Failures lead. Greens follow. (Operator Truth Doctrine)",
        "",
    ]

    failures: list[str] = []
    greens: list[str] = []
    exit_code = 0

    for r in results:
        cat = r["category"]
        c, g, x = r["claude_count"], r["gemini_count"], r["codex_count"]

        problems = []
        if r["missing_in_gemini"]:
            problems.append(f"{len(r['missing_in_gemini'])} missing in Gemini")
        if r["missing_in_codex"]:
            problems.append(f"{len(r['missing_in_codex'])} missing in Codex")
        if r["hash_mismatch"]:
            problems.append(f"{len(r['hash_mismatch'])} hash mismatches")
        if r["extra_orphans"]:
            problems.append(f"{len(r['extra_orphans'])} orphans")

        if problems:
            exit_code = max(exit_code, 1)
            failures.append(
                f"### FAIL: {cat}  (claude={c}, gemini={g}, codex={x})\n"
                + "\n".join(f"  - {p}" for p in problems)
            )
            if r["missing_in_gemini"][:5]:
                failures.append("  Sample missing in Gemini: " + ", ".join(r["missing_in_gemini"][:5]))
            if r["missing_in_codex"][:5]:
                failures.append("  Sample missing in Codex: " + ", ".join(r["missing_in_codex"][:5]))
            if r["hash_mismatch"][:5]:
                failures.append("  Sample drift: " + "; ".join(r["hash_mismatch"][:5]))
        else:
            greens.append(f"### OK: {cat}  (claude={c}, gemini={g}, codex={x})  -- full parity")

    if failures:
        lines.append("## Failures")
        lines.extend(failures)
        lines.append("")
    if greens:
        lines.append("## Greens")
        lines.extend(greens)

    if not any([CLAUDE_TREE.exists(), GEMINI_TREE.exists(), CODEX_TREE.exists()]):
        return "FATAL: no CLI trees found", 2

    return "\n".join(lines), exit_code


def main() -> int:
    results = [diff_category(cat) for cat in MIRRORED_CATEGORIES]
    report, exit_code = render(results)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n[parity] full report -> {REPORT_PATH}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
