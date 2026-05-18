#!/usr/bin/env python3
"""
PreToolUse guardrails for Claude Code.
Blocks unsafe shell patterns, writes outside allowed roots, and em-dash content.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE").resolve()
MEMORY_DIR = Path("/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory").resolve()
ALLOWED_ROOTS = [WORKSPACE, Path("/tmp").resolve(), MEMORY_DIR]
LOG_DIR = WORKSPACE / "_logs" / "claude_hooks"
LOG_FILE = LOG_DIR / "pretool.jsonl"

# Workspace-root whitelist (enforced 2026-05-17). MUST match
# 03_AUTOMATION_CORE/01_Scripts/workspace_root_audit.py and the cloud routine
# ev-workspace-drift-audit. Any new write at workspace root with a name NOT in
# this set is drift and will be blocked.
WORKSPACE_ROOT_WHITELIST = frozenset({
    # 9 numbered project dirs
    "01_BUSINESSES", "02_CONTENT_FACTORY", "03_AUTOMATION_CORE", "04_MEDIA_LIBRARY",
    "05_PERSONAL", "06_DEVELOPMENT", "07_STAGING", "08_BACKUPS", "09_DASHBOARD",
    # 3 load-bearing hot-state dirs
    "_state", "_logs", "supabase",
    # 10 constitutional / per-AI entry docs
    "CLAUDE.md", "CODEX.md", "GEMINI.md", "AGENTS.md",
    "HIVE_CONSTITUTION.md", "HIVE_MIND.md", "EVERLIGHT_COMMANDMENTS.md",
    "LIVING_PUNCHLIST.md", "WORKSPACE_MANIFEST.md", "MEMORY.md",
})


def _emit_decision(decision: str, reason: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(payload, ensure_ascii=True))


def _write_log(data: dict[str, Any], blocked: bool, reason: str | None) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "blocked": blocked,
        "reason": reason,
        "tool_name": data.get("tool_name") or data.get("toolName"),
        "tool_input": data.get("tool_input") or data.get("toolInput"),
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def _get_input() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _iter_strings(node: Any):
    if isinstance(node, str):
        yield node
        return
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
        return
    if isinstance(node, list):
        for value in node:
            yield from _iter_strings(value)


def _extract_candidate_paths(node: Any):
    keys = {"file_path", "path", "target_file", "old_file_path", "new_file_path"}
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys and isinstance(value, str):
                yield value
            yield from _extract_candidate_paths(value)
    elif isinstance(node, list):
        for value in node:
            yield from _extract_candidate_paths(value)


def _resolve_path(path_text: str) -> Path:
    p = Path(path_text)
    if p.is_absolute():
        return p.resolve()
    return (WORKSPACE / p).resolve()


def _is_allowed_path(path_text: str) -> bool:
    try:
        resolved = _resolve_path(path_text)
    except Exception:
        return False
    for root in ALLOWED_ROOTS:
        if resolved == root or str(resolved).startswith(str(root) + "/"):
            return True
    return False


GENERIC_FILLER_PHRASES = [
    "innovative solution",
    "cutting-edge",
    "leveraging",
    "game-changing",
    "revolutionize",
    "disruptive",
    "world-class",
    "best-in-class",
    "synergies",
    "paradigm shift",
    "thought leader",
    "move the needle",
    "circle back",
    "deep dive into",
    "holistic approach",
    "bleeding edge",
    "scalable solution",
    "unlock value",
    "empower your",
    "next-gen",
]

BRAND_TERM_CORRECTIONS = {
    "beyond the avels": "Beyond the Veil",
    "alley kings": "Alley Kingz",
    "alleykings": "Alley Kingz",
    "hivemind saas": "Hive Mind",
    "onyx pos system": "Onyx POS",
    "everlight venture ": "Everlight Ventures ",
    "sam and robo": "Sam and Robo",
}

THEME_FILE_RULES = {
    "alley_kingz": ["01_BUSINESSES/Everlight_Ventures/Alley_Kingz/"],
    "sam_and_robo": ["01_BUSINESSES/Everlight_Ventures/Everlight_Literature/"],
    "beyond_the_veil": ["01_BUSINESSES/Everlight_Ventures/Everlight_Literature/"],
    "onyx_pos": ["01_BUSINESSES/onyx_pos/"],
    "xlm_bot": ["06_DEVELOPMENT/xlm_bot/"],
    "hive_mind": ["06_DEVELOPMENT/hivemind_saas/", "06_DEVELOPMENT/everlight_os/hive_mind/", "09_DASHBOARD/hive_dashboard/"],
    "brand_identity": ["01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/"],
}


def _check_theme_consistency(tool_input: dict[str, Any]) -> str | None:
    """Warn (not block) on generic filler or brand term mistakes in content writes."""
    all_text = " ".join(_iter_strings(tool_input)).lower()
    if not all_text:
        return None

    for phrase in GENERIC_FILLER_PHRASES:
        if phrase in all_text:
            return f"Brand voice warning: generic filler phrase '{phrase}' detected. Use authentic Everlight voice."

    # Brand term check uses ORIGINAL case (not lowered)
    original_text = " ".join(_iter_strings(tool_input))
    for wrong, correct in BRAND_TERM_CORRECTIONS.items():
        if wrong in original_text.lower() and correct not in original_text:
            return f"Brand term error: '{wrong}' should be '{correct}'."

    return None


def _deny(data: dict[str, Any], reason: str) -> int:
    _write_log(data, blocked=True, reason=reason)
    _emit_decision("deny", reason)
    return 0


def _allow(data: dict[str, Any]) -> int:
    _write_log(data, blocked=False, reason=None)
    return 0


def main() -> int:
    data = _get_input()
    tool_name = (data.get("tool_name") or data.get("toolName") or "").strip()
    tool_input = data.get("tool_input") or data.get("toolInput") or {}

    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        command_l = command.lower()

        blocked_shell_patterns = [
            r"\bgit\s+reset\s+--hard\b",
            r"\bgit\s+clean\s+-fdx\b",
            r"\bmkfs\b",
            r"\bdd\s+if=",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\bpoweroff\b",
            r"\b:\(\)\s*\{",
        ]
        for pat in blocked_shell_patterns:
            if re.search(pat, command_l):
                return _deny(data, f"Blocked risky shell pattern: {pat}")

        if re.search(r"\brm\s+-rf\s+/", command_l):
            return _deny(data, "Blocked destructive rm -rf / pattern.")

    if tool_name in {"Write", "Edit", "MultiEdit"}:
        for path_text in _extract_candidate_paths(tool_input):
            if not _is_allowed_path(path_text):
                return _deny(data, f"Blocked write/edit outside allowed roots: {path_text}")
            # Workspace-root drift check: block writes at workspace root with names
            # not on the whitelist. Hidden dotfiles allowed.
            try:
                resolved = _resolve_path(path_text)
                if resolved.parent == WORKSPACE:
                    name = resolved.name
                    if not name.startswith(".") and name not in WORKSPACE_ROOT_WHITELIST:
                        return _deny(
                            data,
                            f"Blocked root-level write '{name}'. Workspace root is "
                            f"locked to 9 numbered dirs + _state/_logs/supabase + "
                            f"10 doctrine .md files + dotfiles. Route this content "
                            f"to the correct 01-09 folder per WORKSPACE_MANIFEST.md "
                            f"File Save Rules.",
                        )
            except Exception:
                pass

        for text in _iter_strings(tool_input):
            if "—" in text:
                return _deny(data, "Blocked em-dash character in generated content.")

        theme_warning = _check_theme_consistency(tool_input)
        if theme_warning:
            return _deny(data, theme_warning)

    return _allow(data)


if __name__ == "__main__":
    raise SystemExit(main())
