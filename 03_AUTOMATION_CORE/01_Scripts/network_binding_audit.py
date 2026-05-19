#!/usr/bin/env python3
"""
Network binding audit.

Walks the workspace and flags every `0.0.0.0` bind that is NOT either:
  * inside an excluded path (08_BACKUPS, .bak, legacy_*, prototype_*,
    06_DEVELOPMENT/everlightventures/, _state/audit_log, .git, node_modules,
    neuromorphic/state/ai_brain_*.json, .claude/learned_bash_allowlist.json),
  * tagged on the same line with one of the approved exception markers:
      # bind:public-by-design
      # bind:managed-platform
      # bind:tailnet-only
      # bind:lan-required
      # bind:legacy-archive

Exit codes:
  0  clean
  1  drift found (offending lines printed to stdout)
  2  internal error

Policy lives at:
  06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md

Usage:
  python3 03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py
  python3 03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py --json
  python3 03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py --strict-md  (also flags doc-only mentions)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE").resolve()
LOG_DIR = ROOT / "_logs" / "network_binding_audit"

BIND_RE = re.compile(r"0\.0\.0\.0(?::\d+)?")
USER_AGENT_RE = re.compile(r"Chrome/120\.0\.0\.0")  # User-Agent strings, not binds

EXCLUDE_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    "08_BACKUPS",
    "Archives",
    ".venv",
    "venv",
    "site-packages",
    ".hive_active",
}

EXCLUDE_PATH_FRAGMENTS = (
    "/08_BACKUPS/",
    "/06_DEVELOPMENT/everlightventures/",  # separate git repo mirror
    "/_state/audit_log/",
    "/_logs/",                              # historical session logs / transcripts
    "/.git/",
    "/node_modules/",
    "/site-packages/",                      # third-party python packages
    "/.venv/",
    "/venv/",
    "/neuromorphic/state/ai_brain_",
    "/.claude/learned_bash_allowlist.json",
    "/.claude/plans/",
    "/06_DEVELOPMENT/Archives/",
    "/06_DEVELOPMENT/everlight_swarms/upstream/",  # vendored upstream code
    "/legacy_jan2026/",
    "/legacy_advanced_py_may2026/",
    "/prototype_dec2025/",
    "/api_v2_may2026/",
    "/operations_MGN_v8/",                  # POS, LAN-required by design
    "/Mountain Gardens Nursery POS/",
    "/Mountain_Gardens/",
    "/onyx_pos/origins/",
    "/02_Training/",                        # personal training notes (Fight_Camp_OS docs)
    "/03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py",  # self-reference
    "/06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md",  # the policy doc itself
)

EXCLUDE_FILENAME_FRAGMENTS = (
    ".bak/",
    ".bak.",
    ".swp",
)

SCAN_EXTENSIONS = {
    ".py", ".sh", ".yml", ".yaml", ".json", ".service",
    ".env", ".conf", ".toml",
}

EXCEPTION_TAGS = (
    "bind:public-by-design",
    "bind:managed-platform",
    "bind:tailnet-only",
    "bind:lan-required",
    "bind:legacy-archive",
)


def should_skip(path: Path) -> bool:
    s = str(path)
    if any(frag in s for frag in EXCLUDE_PATH_FRAGMENTS):
        return True
    if any(frag in s for frag in EXCLUDE_FILENAME_FRAGMENTS):
        return True
    parts = set(path.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    return False


def line_has_exception(line: str) -> str | None:
    for tag in EXCEPTION_TAGS:
        if tag in line:
            return tag
    return None


def is_user_agent_noise(line: str) -> bool:
    return bool(USER_AGENT_RE.search(line)) and "host" not in line.lower() and "bind" not in line.lower() and "address" not in line.lower()


def looks_like_a_bind(line: str) -> bool:
    lower = line.lower()
    needles = (
        "host", "bind", "addr", "listen", "server.address", "server_address",
        "0.0.0.0:",  # URL/port form is almost always a bind or routing rule
    )
    return any(n in lower for n in needles)


def is_doc_comment(line: str) -> bool:
    """Comment lines (and log/echo doc strings) that DESCRIBE 0.0.0.0 rather than configure it."""
    stripped = line.lstrip()
    is_comment_or_logline = (
        stripped.startswith("#")
        or stripped.startswith("//")
        or stripped.startswith("*")
        or stripped.startswith("log ")
        or stripped.startswith("log(")
        or stripped.startswith("echo ")
        or stripped.startswith("print(")
        or stripped.startswith("say ")
    )
    if not is_comment_or_logline:
        return False
    lower = stripped.lower()
    descriptive_markers = (
        "default", "override", "set 0.0.0.0", "ev_bind=0.0.0.0",
        "to expose", "to reach", "for security", "or restrict",
        "see network_binding", "policy:", "bind policy", "private by default",
        "is correct because", "n8n_host=0.0.0.0", "host=0.0.0.0 so",
        "listens on 0.0.0.0", "running on http://0.0.0.0", "default 0.0.0.0",
        "0.0.0.0/0", "moltbook_bind=0.0.0.0", "fcos_bind", "ic_bind",
        "starting novnc on", "tailnet/lan-visible", "source cidr",
        "verify oci", "allow tcp",
    )
    return any(m in lower for m in descriptive_markers)


def is_docstring_or_string_literal(line: str) -> bool:
    """Quoted/docstring occurrences that describe rather than bind."""
    stripped = line.strip()
    if stripped.startswith(('"""', "'''", '"', "'")) and stripped.count("0.0.0.0") == 1:
        return True
    if "url" in stripped.lower() and "http://0.0.0.0" in stripped.lower():
        return True
    # Bash substring replacement: ${VAR/0.0.0.0/something} converts the literal,
    # it is NOT a bind, it's a string transform for display.
    if "${" in line and "/0.0.0.0/" in line:
        return True
    # Module-level docstring continuation lines (no quotes, but indented prose
    # describing the module). Heuristic: line is plain prose (no =, no :, no
    # function call) and the file is .py with 0.0.0.0 embedded in a sentence.
    if "Listens on 0.0.0.0" in line or "default 0.0.0.0" in line:
        return True
    # Django ALLOWED_HOSTS is an HTTP-Host-header whitelist, not a socket bind.
    if "ALLOWED_HOSTS" in line or "allowed_hosts" in line:
        return True
    return False


def scan_file(path: Path, strict_md: bool) -> list[dict]:
    findings: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return findings
    if "0.0.0.0" not in text:
        return findings
    in_py_docstring = False
    is_python = path.suffix.lower() == ".py"
    for lineno, line in enumerate(text.splitlines(), 1):
        # Track Python module/function docstring state by counting triple-quote toggles.
        if is_python:
            triple_count = line.count('"""') + line.count("'''")
            if in_py_docstring and "0.0.0.0" in line and triple_count == 0:
                # Inside a docstring, descriptive prose.
                continue
            if triple_count % 2 == 1:
                in_py_docstring = not in_py_docstring
                if "0.0.0.0" in line:
                    continue
        if "0.0.0.0" not in line:
            continue
        if is_user_agent_noise(line):
            continue
        if is_doc_comment(line):
            continue
        if is_docstring_or_string_literal(line):
            continue
        if not strict_md and path.suffix.lower() == ".md":
            # By default, .md mentions are documentation, not executable.
            if not looks_like_a_bind(line):
                continue
            # Even bind-like lines in .md are doc/example; only flag with --strict-md.
            continue
        if not looks_like_a_bind(line) and "0.0.0.0/0" not in line:
            continue
        if "0.0.0.0/0" in line:
            # CIDR for firewall doctrine. Only meaningful if it looks like a config rule.
            if path.suffix.lower() in {".md", ".txt"}:
                continue
        tag = line_has_exception(line)
        findings.append({
            "file": str(path.relative_to(ROOT)),
            "line": lineno,
            "text": line.strip()[:200],
            "exception": tag,
        })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Network binding audit")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    ap.add_argument("--strict-md", action="store_true",
                    help="Also flag bind-like lines in .md (off by default)")
    ap.add_argument("--save", action="store_true",
                    help=f"Save report to {LOG_DIR}/")
    args = ap.parse_args()

    if not ROOT.exists():
        print(f"ERROR: workspace root not found: {ROOT}", file=sys.stderr)
        return 2

    untagged: list[dict] = []
    tagged: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Prune excluded directories early
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        p_dir = Path(dirpath)
        if should_skip(p_dir):
            dirnames[:] = []
            continue
        for fn in filenames:
            p = p_dir / fn
            if p.suffix.lower() not in SCAN_EXTENSIONS and p.suffix.lower() != ".md":
                continue
            if should_skip(p):
                continue
            for finding in scan_file(p, strict_md=args.strict_md):
                (tagged if finding["exception"] else untagged).append(finding)

    summary = {
        "scanned_root": str(ROOT),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "untagged_count": len(untagged),
        "tagged_count": len(tagged),
        "untagged": untagged,
        "tagged": tagged,
    }

    if args.save:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        out = LOG_DIR / f"audit_{stamp}.json"
        out.write_text(json.dumps(summary, indent=2))
        print(f"Saved report to {out}")

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0 if not untagged else 1

    print(f"Network Binding Audit @ {summary['timestamp']}")
    print(f"  workspace: {ROOT}")
    print(f"  untagged 0.0.0.0 binds (drift): {len(untagged)}")
    print(f"  tagged 0.0.0.0 binds (approved): {len(tagged)}")
    print()
    if untagged:
        print("DRIFT FOUND. Patch these or add an approved tag")
        print("(# bind:public-by-design | # bind:managed-platform | # bind:tailnet-only | # bind:lan-required | # bind:legacy-archive):")
        print()
        for f in untagged:
            print(f"  {f['file']}:{f['line']}: {f['text']}")
        print()
        print("Policy: 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md")
        return 1

    if tagged:
        print("Approved (tagged) exceptions:")
        for f in tagged:
            print(f"  [{f['exception']}] {f['file']}:{f['line']}")
    print()
    print("Clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
