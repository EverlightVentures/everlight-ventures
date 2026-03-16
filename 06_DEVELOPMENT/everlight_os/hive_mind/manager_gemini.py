"""Gemini manager adapter - uses gemini CLI directly.

Gemini dumps extension/hook noise to stdout mixed with real content.
We strip all that noise before returning the response.

For large E Pluribus Unum prompts, the prompt is written to a temp file
and piped via stdin to avoid OS argument-length limits.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

from .config import WORKSPACE
from .contracts import ManagerResult, _now

# Lines containing any of these are Gemini CLI noise, not real output
_NOISE_PATTERNS = (
    "MCP server",
    "/mcp auth",
    "execution plan for Session",
    "Expanding hook command",
    "Hook execution for Session",
    "hooks executed",
    "hook(s) to execute",
    "[ExtensionManager]",
    "Loading extension:",
    "supports tool updates",
    "supports resource updates",
    "supports prompt updates",
    "Listening for changes",
    "Loaded cached credentials",
    "Error during discovery",
    "Error loading extension",
    "Extension error",
)


def _clean_output(raw: str) -> str:
    """Strip Gemini CLI noise (hooks, MCP, extensions) from output."""
    lines = []
    for line in raw.splitlines():
        if any(noise in line for noise in _NOISE_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def run(prompt: str, timeout: int = 120, mode: str = "plan") -> ManagerResult:
    """Run Gemini via `gemini -p` and return a ManagerResult.

    For large prompts (>4000 chars), writes to a temp file and pipes via
    stdin to avoid shell argument-length issues. Timeout is controlled by
    roster.yaml (default bumped to 300s to handle hook loading overhead).
    """
    result = ManagerResult(
        manager="gemini",
        role="Logistics Commander / Executor",
        status="running",
        started_at=_now(),
    )

    start = time.time()

    # Clean environment: remove Claude Code nesting vars
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)
    env.pop("CLAUDE_CODE_ENTRY_POINT", None)

    # For large prompts, write to temp file and pipe via stdin
    # Gemini's -p accepts: stdin content + -p "additional text"
    # So we pipe the bulk via stdin and use -p with a minimal marker
    prompt_file = None
    try:
        if len(prompt) > 4000:
            prompt_file = Path(tempfile.mktemp(suffix=".txt", prefix=".hive_gemini_"))
            prompt_file.write_text(prompt, encoding="utf-8")
            # Use shell to pipe: cat file | gemini -y -p "Respond to stdin:"
            cmd = f'cat "{prompt_file}" | gemini -y -p "Process the following deliberation request:"'
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout + 30,
                cwd=str(WORKSPACE),
                env=env,
            )
        else:
            cmd = ["gemini", "-y", "-p", prompt]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 30,
                cwd=str(WORKSPACE),
                env=env,
            )

        output = _clean_output(proc.stdout)
        if output:
            result.response_text = output
            result.status = "done"
        elif proc.returncode == 0:
            result.response_text = "(empty response)"
            result.status = "done"
        else:
            result.status = "failed"
            stderr = proc.stderr.strip()
            err_lines = [
                l for l in stderr.splitlines()
                if not any(n in l for n in _NOISE_PATTERNS)
            ]
            result.error = "\n".join(err_lines)[:2000] if err_lines else stderr[:2000]
    except subprocess.TimeoutExpired:
        result.status = "timeout"
        result.error = f"Gemini timed out after {timeout}s"
    except FileNotFoundError:
        result.status = "failed"
        result.error = "gemini binary not found in PATH"
    finally:
        # Clean up temp file
        if prompt_file and prompt_file.exists():
            try:
                prompt_file.unlink()
            except OSError:
                pass

    result.finished_at = _now()
    result.duration_s = round(time.time() - start, 1)
    return result
