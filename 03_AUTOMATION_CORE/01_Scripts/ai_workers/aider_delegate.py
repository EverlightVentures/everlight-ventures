#!/usr/bin/env python3
"""
Structured Aider delegation wrapper for Lucrex Legion orchestration.

Mirrors gemx_delegate.py / kimi_delegate.py so the router and the `legion`
front door drive every Mother through one uniform JSON envelope.

Aider is model-agnostic and git-native. Unlike Gemini/Kimi it needs an API
key + model, so this wrapper loads the shared credentials .env before
shelling out (same pattern as cx_terminal.py).

Examples:
  aiderx --mode explain "Explain the auth flow in this module"
  aiderx --mode execute --model sonnet "Add input validation to login()"

Aider headless contract (verified against `aider --help`, v0.86.2):
  aider --message "<text>" --model <m> --yes-always --no-auto-commits
        --no-stream --no-pretty --no-check-update --map-tokens 0
  --dry-run is added for plan/explain so Aider never mutates files there.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from delegate_utils import parse_output, write_delegate_logs


DEFAULT_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
ENV_FILE = Path(
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
)

# Modes -> whether Aider is allowed to write. plan/explain are dry-run.
MODE_DRY_RUN = {
    "execute": False,
    "plan": True,
    "explain": True,
}


def load_env() -> None:
    """Load API keys from the shared credentials .env into the environment."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Aider headless with mode-aware context and structured output."
    )
    parser.add_argument(
        "--mode",
        choices=["execute", "plan", "explain"],
        default="explain",
        help="Execution mode. Defaults to explain (dry-run, read-only).",
    )
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Working directory. Point at a specific sub-repo for real edits.",
    )
    parser.add_argument(
        "--output-format",
        choices=["text"],
        default="text",
        help="Aider emits plain text only.",
    )
    parser.add_argument(
        "--model",
        help="Model for Aider (else env AIDER_MODEL / aider config decides).",
    )
    parser.add_argument(
        "--map-tokens",
        type=int,
        default=0,
        help="Repo-map token budget. 0 disables it (safe on huge workspaces).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Optional timeout in seconds. 0 means no timeout.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Pass through raw Aider stdout/stderr instead of wrapper JSON.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable delegation logs under _logs/aider_delegate.",
    )
    parser.add_argument(
        "prompt",
        nargs="+",
        help="Prompt text (use quotes for multi-word requests).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    prompt = " ".join(args.prompt).strip()

    cmd = [
        "aider",
        "--message",
        prompt,
        "--yes-always",
        "--no-auto-commits",
        "--no-stream",
        "--no-pretty",
        "--no-check-update",
        "--map-tokens",
        str(args.map_tokens),
    ]
    if MODE_DRY_RUN[args.mode]:
        cmd.append("--dry-run")
    if args.model:
        cmd.extend(["--model", args.model])

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=args.timeout if args.timeout > 0 else None,
            check=False,
        )
    except FileNotFoundError:
        print("aider binary not found in PATH.", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired as e:
        print(f"Aider timed out after {args.timeout}s.", file=sys.stderr)
        if args.raw and e.stdout:
            print(e.stdout, end="")
        return 124

    if args.raw:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode

    parsed = parse_output(args.output_format, proc.stdout)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ok": proc.returncode == 0,
        "mode": args.mode,
        "workspace": str(workspace),
        "mode_cwd": str(workspace),
        "output_format": args.output_format,
        "dry_run": MODE_DRY_RUN[args.mode],
        "command": cmd,
        "command_shell": shlex.join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed_output": parsed,
    }

    if not args.no_log:
        payload["log_file"] = write_delegate_logs(workspace, payload, "aider")

    print(json.dumps(payload, ensure_ascii=True))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
