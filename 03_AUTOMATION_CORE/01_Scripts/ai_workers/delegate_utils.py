#!/usr/bin/env python3
"""
Shared utilities for AI delegate wrappers (clx_delegate, gemx_delegate, etc.).

Provides common output parsing and log-writing logic so each delegate
only needs to define its own CLI args and command construction.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_output(output_format: str, stdout_text: str) -> Any:
    """Parse stdout from an AI CLI tool based on format.

    Supports 'json', 'stream-json', and 'text' (returns None for text).
    """
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


def write_delegate_logs(workspace: Path, payload: dict, tool_name: str) -> str:
    """Write delegation run logs to _logs/<tool_name>_delegate/.

    Returns the path to the individual run log file.
    """
    logs_dir = workspace / "_logs" / f"{tool_name}_delegate"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_file = logs_dir / f"{timestamp}_{payload['mode']}.json"
    run_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")

    history_file = logs_dir / "history.jsonl"
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    return str(run_file)
