#!/usr/bin/env python3
"""
Structured Claude delegation wrapper for Codex-style orchestration.

Examples:
  clx --mode plan "Design a migration plan for this repo"
  clx --mode execute --output-format json "Implement X and summarize rollback"
"""

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
MODE_PERMISSION = {
    "execute": "acceptEdits",
    "plan": "plan",
    "review": "plan",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Claude headless with mode-aware prompts and structured output."
    )
    parser.add_argument(
        "--mode",
        choices=["execute", "plan", "review"],
        default="execute",
        help="Execution mode. Defaults to execute.",
    )
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Workspace root path. Defaults to AA_MY_DRIVE.",
    )
    parser.add_argument(
        "--permission-mode",
        choices=["acceptEdits", "bypassPermissions", "default", "dontAsk", "plan"],
        help="Override permission mode.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text", "stream-json"],
        default="json",
        help="Claude output format.",
    )
    parser.add_argument(
        "--settings",
        help="Optional settings file path (defaults to workspace .claude/settings.json if present).",
    )
    parser.add_argument(
        "--mcp-config",
        help="Optional MCP config file (defaults to workspace .mcp.json if present).",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        help="Additional directories to allow tool access to (repeatable).",
    )
    parser.add_argument(
        "--allowed-tool",
        action="append",
        default=[],
        help='Allowed tool entries passed to --allowedTools (repeatable, e.g. "Bash(git:*)").',
    )
    parser.add_argument(
        "--agent",
        help="Optional agent name for this run.",
    )
    parser.add_argument(
        "--model",
        help="Optional model alias/name (e.g. sonnet, opus).",
    )
    parser.add_argument(
        "--json-schema",
        help="Optional JSON schema string for structured output validation.",
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
        help="Pass through raw Claude stdout/stderr instead of wrapper JSON envelope.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable delegation logs under _logs/claude_delegate.",
    )
    parser.add_argument(
        "prompt",
        nargs="+",
        help="Prompt text (use quotes for multi-word requests).",
    )
    return parser.parse_args()


def parse_output(output_format: str, stdout_text: str):
    clean = stdout_text.strip()
    if not clean:
        return None

    if output_format == "json":
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            return None

    if output_format == "stream-json":
        events = []
        for line in stdout_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"type": "raw", "data": line})
        return events

    return None


def write_logs(workspace: Path, payload: dict) -> str:
    logs_dir = workspace / "_logs" / "claude_delegate"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_file = logs_dir / f"{timestamp}_{payload['mode']}.json"
    run_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")

    history_file = logs_dir / "history.jsonl"
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    return str(run_file)


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    prompt = " ".join(args.prompt).strip()
    permission_mode = args.permission_mode or MODE_PERMISSION[args.mode]

    settings_path = Path(args.settings).resolve() if args.settings else workspace / ".claude" / "settings.json"
    mcp_path = Path(args.mcp_config).resolve() if args.mcp_config else workspace / ".mcp.json"
    mode_prompt_file = workspace / ".claude" / "modes" / f"{args.mode}.md"

    add_dirs = [str(workspace)] + args.add_dir
    add_dirs = list(dict.fromkeys(add_dirs))

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        args.output_format,
        "--permission-mode",
        permission_mode,
    ]

    if settings_path.exists():
        cmd.extend(["--settings", str(settings_path)])

    if mcp_path.exists():
        cmd.extend(["--mcp-config", str(mcp_path)])

    if mode_prompt_file.exists():
        mode_prompt = mode_prompt_file.read_text(encoding="utf-8").strip()
        if mode_prompt:
            cmd.extend(["--append-system-prompt", mode_prompt])

    if args.agent:
        cmd.extend(["--agent", args.agent])

    if args.model:
        cmd.extend(["--model", args.model])

    if args.json_schema:
        cmd.extend(["--json-schema", args.json_schema])

    for add_dir in add_dirs:
        cmd.extend(["--add-dir", add_dir])

    for allowed_tool in args.allowed_tool:
        cmd.extend(["--allowedTools", allowed_tool])

    try:
        proc = subprocess.run(
            cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=args.timeout if args.timeout > 0 else None,
            check=False,
        )
    except FileNotFoundError:
        print("claude binary not found in PATH.", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired as e:
        print(f"Claude timed out after {args.timeout}s.", file=sys.stderr)
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
        "permission_mode": permission_mode,
        "output_format": args.output_format,
        "command": cmd,
        "command_shell": shlex.join(cmd),
        "add_directories": add_dirs,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed_output": parsed,
    }

    if not args.no_log:
        payload["log_file"] = write_logs(workspace, payload)

    print(json.dumps(payload, ensure_ascii=True))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
