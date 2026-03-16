"""Codex manager adapter - uses the codex CLI binary (codex exec).

Prompt is piped via stdin to avoid OS argument-length limits on the
massive E Pluribus Unum specialist prompts.

When Codex hits API rate limits (429), falls back to Claude as a
stand-in engineering brain (same prompt, different engine).
"""

import os
import subprocess
import time

from .config import WORKSPACE
from .contracts import ManagerResult, _now


def _run_codex(prompt: str, timeout: int, env: dict) -> subprocess.CompletedProcess:
    """Execute codex exec with stdin piping."""
    cmd = [
        "codex", "exec",
        "--full-auto",
        "-",
    ]
    return subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout + 30,
        cwd=str(WORKSPACE),
        env=env,
    )


def _run_claude_fallback(prompt: str, timeout: int, env: dict) -> subprocess.CompletedProcess:
    """Fallback: run the Codex prompt through Claude when Codex is unavailable."""
    cmd = [
        "claude",
        "-p",
        "--model", "sonnet",
    ]
    return subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout + 30,
        cwd=str(WORKSPACE),
        env=env,
    )


def _parse_stderr(stderr: str) -> str:
    """Filter codex header/echo noise from stderr to find the real error."""
    err_lines = []
    past_header = False
    for line in stderr.splitlines():
        if line.startswith("--------") and past_header:
            err_lines = []
            continue
        if line.startswith("--------"):
            past_header = True
            continue
        err_lines.append(line)
    cleaned = "\n".join(err_lines).strip()
    return cleaned or stderr


def _is_rate_limited(stderr: str) -> bool:
    """Detect Codex API rate limit errors (429)."""
    lower = stderr.lower()
    return (
        "429" in lower
        or "usage_limit_reached" in lower
        or "usage limit" in lower
        or "rate limit" in lower
    )


def run(prompt: str, timeout: int = 120) -> ManagerResult:
    """Run Codex via `codex exec` and return a ManagerResult.

    The prompt is piped through stdin. If Codex hits API rate limits,
    automatically falls back to Claude (sonnet) to keep the Engineering
    team online.
    """
    result = ManagerResult(
        manager="codex",
        role="Engineering Foreman / Profit Maximizer",
        status="running",
        started_at=_now(),
    )

    start = time.time()

    # Clean environment
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)
    env.pop("CLAUDE_CODE_ENTRY_POINT", None)

    try:
        proc = _run_codex(prompt, timeout, env)
        output = proc.stdout.strip()

        if output:
            result.response_text = output
            result.status = "done"
        elif proc.returncode == 0:
            result.response_text = "(empty response)"
            result.status = "done"
        else:
            stderr = proc.stderr.strip()
            parsed_err = _parse_stderr(stderr)

            # If rate limited, fall back to Claude
            if _is_rate_limited(stderr):
                try:
                    fb_proc = _run_claude_fallback(prompt, timeout, env)
                    fb_output = fb_proc.stdout.strip()
                    if fb_output:
                        result.response_text = (
                            "[Codex rate-limited -- Claude standing in as Engineering Foreman]\n\n"
                            + fb_output
                        )
                        result.status = "done"
                        result.error = "Codex 429 rate limit; used Claude fallback"
                    else:
                        result.status = "failed"
                        result.error = f"Codex rate-limited + Claude fallback empty: {parsed_err[:500]}"
                except subprocess.TimeoutExpired:
                    result.status = "timeout"
                    result.error = f"Codex rate-limited + Claude fallback timed out after {timeout}s"
                except FileNotFoundError:
                    result.status = "failed"
                    result.error = "Codex rate-limited and claude binary not found for fallback"
            else:
                result.status = "failed"
                result.error = parsed_err[:2000]

    except subprocess.TimeoutExpired:
        result.status = "timeout"
        result.error = f"Codex timed out after {timeout}s"
    except FileNotFoundError:
        result.status = "failed"
        result.error = "codex binary not found in PATH"

    result.finished_at = _now()
    result.duration_s = round(time.time() - start, 1)
    return result
