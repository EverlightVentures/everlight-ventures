#!/usr/bin/env python3
"""
PostToolUse logger for Claude Code hooks.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE").resolve()
LOG_DIR = WORKSPACE / "_logs" / "claude_hooks"
LOG_FILE = LOG_DIR / "posttool.jsonl"


def _load_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def main() -> int:
    payload = _load_payload()
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tool_name": payload.get("tool_name") or payload.get("toolName"),
        "tool_input": payload.get("tool_input") or payload.get("toolInput"),
        "tool_response": payload.get("tool_response") or payload.get("toolResponse"),
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
