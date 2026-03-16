#!/usr/bin/env python3
"""
Structured Gemini delegation wrapper for Codex-style orchestration.

Examples:
  gmx --mode plan "Design a migration plan for this repo"
  gmx --mode execute --output-format json "Refactor X and summarize risks"
"""

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
MODE_DIRS = {
    "execute": DEFAULT_WORKSPACE,
    "plan": DEFAULT_WORKSPACE / ".gemini" / "plan",
    "explain": DEFAULT_WORKSPACE / ".gemini" / "explain",
}
MODE_APPROVAL = {
    "execute": "auto_edit",
    "plan": "plan",
    "explain": "default",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gemini headless with mode-aware context and structured JSON output."
    )
    parser.add_argument(
        "--mode",
        choices=["execute", "plan", "explain"],
        default="execute",
        help="Execution mode. Defaults to execute.",
    )
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Workspace root path. Defaults to AA_MY_DRIVE.",
    )
    parser.add_argument(
        "--approval-mode",
        choices=["default", "auto_edit", "plan", "yolo"],
        help="Override approval mode. Defaults depend on --mode.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text", "stream-json"],
        default="json",
        help="Gemini output format.",
    )
    parser.add_argument(
        "--include-directory",
        action="append",
        default=[],
        help="Additional workspace directories to include (repeatable).",
    )
    parser.add_argument(
        "--allowed-tool",
        action="append",
        default=[],
        help="Additional --allowed-tools values (repeatable).",
    )
    parser.add_argument(
        "--model",
        help="Optional Gemini model override.",
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
        help="Pass through raw Gemini stdout/stderr instead of wrapper JSON.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable delegation logs under _logs/gemini_delegate.",
    )
    parser.add_argument(
        "prompt",
        nargs="+",
        help="Prompt text (use quotes for multi-word requests).",
    )
    return parser.parse_args()


def parse_gemini_output(output_format: str, stdout_text: str):
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


def ensure_mode_dir(mode_dir: Path) -> None:
    if mode_dir.exists() and mode_dir.is_dir():
        return
    raise FileNotFoundError(
        f"Mode directory not found: {mode_dir}. Create .gemini mode folders first."
    )


def write_logs(workspace: Path, payload: dict) -> str:
    logs_dir = workspace / "_logs" / "gemini_delegate"
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
    mode_dir = MODE_DIRS[args.mode] if args.workspace == str(DEFAULT_WORKSPACE) else (
        workspace if args.mode == "execute" else workspace / ".gemini" / args.mode
    )
    ensure_mode_dir(mode_dir)

    prompt = " ".join(args.prompt).strip()
    approval_mode = args.approval_mode or MODE_APPROVAL[args.mode]

    include_dirs = [str(workspace)] + args.include_directory
    include_dirs = list(dict.fromkeys(include_dirs))

    cmd = [
        "gemini",
        "-p",
        prompt,
        "--output-format",
        args.output_format,
        "--approval-mode",
        approval_mode,
    ]

    for include_dir in include_dirs:
        cmd.extend(["--include-directories", include_dir])

    if args.model:
        cmd.extend(["--model", args.model])

    for allowed_tool in args.allowed_tool:
        cmd.extend(["--allowed-tools", allowed_tool])

    try:
        proc = subprocess.run(
            cmd,
            cwd=mode_dir,
            capture_output=True,
            text=True,
            timeout=args.timeout if args.timeout > 0 else None,
            check=False,
        )
    except FileNotFoundError:
        print("gemini binary not found in PATH.", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired as e:
        print(f"Gemini timed out after {args.timeout}s.", file=sys.stderr)
        if args.raw and e.stdout:
            print(e.stdout, end="")
        return 124

    if args.raw:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode

    parsed = parse_gemini_output(args.output_format, proc.stdout)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ok": proc.returncode == 0,
        "mode": args.mode,
        "workspace": str(workspace),
        "mode_cwd": str(mode_dir),
        "approval_mode": approval_mode,
        "output_format": args.output_format,
        "command": cmd,
        "command_shell": shlex.join(cmd),
        "include_directories": include_dirs,
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
