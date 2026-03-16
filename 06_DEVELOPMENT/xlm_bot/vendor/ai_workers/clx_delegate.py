#!/usr/bin/env python3
"""Minimal Claude delegate for cloud/Docker deployment.

Drop-in replacement for 03_AUTOMATION_CORE clx_delegate.py that works
without the full AA_MY_DRIVE workspace. Just calls 'claude -p' directly.

Requires: claude CLI installed + ANTHROPIC_API_KEY env var set.
"""
import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Minimal Claude CLI delegate")
    p.add_argument("--raw", action="store_true", help="Raw output mode")
    p.add_argument("--mode", default="execute", help="Execution mode (ignored, kept for compat)")
    p.add_argument("--output-format", default="text", help="Output format (ignored)")
    p.add_argument("--model", default="opus", help="Claude model to use")
    p.add_argument("--allowed-tool", action="append", dest="allowed_tools", default=[])
    p.add_argument("prompt", nargs="+", help="Prompt text")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    prompt_text = " ".join(args.prompt)

    # Map short model names to full IDs
    model_map = {
        "opus": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }
    model = model_map.get(args.model, args.model)

    cmd = ["claude", "-p", "--model", model]
    for tool in (args.allowed_tools or []):
        cmd += ["--allowedTools", tool]
    cmd.append(prompt_text)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout, end="")
    else:
        print(result.stderr, file=sys.stderr, end="")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
