#!/usr/bin/env python3
"""
Structured Kimi delegation wrapper for Lucrex Legion orchestration.

Mirrors gemx_delegate.py so the router and the `legion` front door can
drive every Mother through one uniform JSON envelope.

Examples:
  kimix --mode plan "Design a migration plan for this repo"
  kimix --mode execute --output-format text "Refactor X and summarize risks"

Kimi headless contract (verified against `kimi --help`, v1.48.0):
  kimi --print --prompt "<text>" --output-format {text,stream-json} -w <dir>
  --print   run non-interactively (auto-approves tool calls for the run)
  --yes     auto-approve everything (execute)
  --plan    start in plan mode -- proposes, does not mutate files (plan/explain)
"""

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from delegate_utils import parse_output, write_delegate_logs


DEFAULT_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")

# Mode -> extra kimi flags. --print is always added (non-interactive).
# execute may edit files; plan/explain stay in read-only plan mode.
MODE_FLAGS = {
    "execute": ["--yes"],
    "plan": ["--plan"],
    "explain": ["--plan"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Kimi headless with mode-aware context and structured output."
    )
    parser.add_argument(
        "--mode",
        choices=["execute", "plan", "explain"],
        default="explain",
        help="Execution mode. Defaults to explain (read-only).",
    )
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Workspace root path. Defaults to AA_MY_DRIVE.",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "stream-json"],
        default="text",
        help="Kimi output format (kimi has no plain 'json' mode).",
    )
    parser.add_argument(
        "--include-directory",
        action="append",
        default=[],
        help="Additional workspace directories to include (repeatable).",
    )
    parser.add_argument(
        "--model",
        help="Optional Kimi model override.",
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
        help="Pass through raw Kimi stdout/stderr instead of wrapper JSON.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable delegation logs under _logs/kimi_delegate.",
    )
    parser.add_argument(
        "prompt",
        nargs="+",
        help="Prompt text (use quotes for multi-word requests).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 2

    prompt = " ".join(args.prompt).strip()

    cmd = [
        "kimi",
        "--print",
        "--prompt",
        prompt,
        "--output-format",
        args.output_format,
        "-w",
        str(workspace),
    ]
    cmd.extend(MODE_FLAGS[args.mode])

    # Universal MCP fleet (shared with Claude/Codex/Gemini) if the config exists.
    kimi_mcp = Path.home() / ".kimi" / "mcp.json"
    if kimi_mcp.exists():
        cmd.extend(["--mcp-config-file", str(kimi_mcp)])

    for include_dir in dict.fromkeys(args.include_directory):
        cmd.extend(["--add-dir", include_dir])

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
        print("kimi binary not found in PATH.", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired as e:
        print(f"Kimi timed out after {args.timeout}s.", file=sys.stderr)
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
        "command": cmd,
        "command_shell": shlex.join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed_output": parsed,
    }

    if not args.no_log:
        payload["log_file"] = write_delegate_logs(workspace, payload, "kimi")

    print(json.dumps(payload, ensure_ascii=True))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
