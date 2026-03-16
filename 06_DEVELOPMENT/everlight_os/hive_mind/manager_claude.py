"""Claude execution bridge -- Phase 5 of the Hive Mind.

After Gemini/Codex/Perplexity deliberate and produce recommendations,
Claude reads the war room output and EXECUTES. This closes the loop
from deliberation to action.

Claude uses its full toolset (Bash, Read, Write, Edit, Glob, Grep)
to implement what the hive recommended.
"""

import json
import os
import subprocess
import time
from pathlib import Path

from .config import WORKSPACE
from .contracts import ManagerResult, _now


# Map hive categories to the Claude Code sub-agents best suited to execute
_CATEGORY_AGENTS = {
    "engineering": [
        "everlight_architect",
        "everlight_saas_builder",
        "everlight_qa_gate",
    ],
    "trading": [
        "everlight_trading_risk",
    ],
    "content": [
        "everlight_content_director",
        "everlight_seo_formatter",
        "everlight_qa_gate",
    ],
    "business": [
        "everlight_saas_pm",
        "everlight_saas_growth",
        "everlight_saas_builder",
    ],
    "operations": [
        "everlight_architect",
        "everlight_packager",
    ],
    "research": [
        "everlight_researcher",
    ],
}

_DEFAULT_AGENTS = ["everlight_architect", "everlight_qa_gate"]


def _build_execution_prompt(
    user_query: str,
    combined_summary: str,
    category: str,
    war_room_dir: str,
) -> str:
    """Build the execution prompt for Claude."""

    relevant_agents = _CATEGORY_AGENTS.get(category, _DEFAULT_AGENTS)
    agent_list = ", ".join(relevant_agents)

    prompt = f"""# HIVE MIND EXECUTION ORDER

You are Claude, Chief Operator of the Everlight AI Hive Mind.
The hive has deliberated. Gemini, Codex, and Perplexity have produced
their recommendations. Now YOU execute.

## YOUR ROLE
- Read the hive deliberation output below
- Parse the actionable recommendations from all agents
- EXECUTE the recommendations using your tools (Edit, Write, Bash, etc.)
- Delegate research tasks to sub-agents when appropriate
- Log what you did and what you skipped (with reasons)

## EXECUTION RULES
- DO implement code changes, file edits, and structural updates
- DO run commands that build, test, or verify changes
- DO NOT make destructive changes (rm -rf, drop tables, force push)
- DO NOT execute trades or financial transactions
- DO NOT push to git unless explicitly requested in the original query
- If a recommendation is vague or risky, LOG IT as "deferred" rather than guessing
- Prefer small, verifiable steps over big-bang changes

## RELEVANT SUB-AGENTS FOR THIS TASK
Category: {category}
Recommended agents: {agent_list}
Use the Task tool to delegate to these agents when their expertise is needed.

## WAR ROOM LOCATION
{war_room_dir}

## ORIGINAL USER QUERY
{user_query}

## HIVE DELIBERATION OUTPUT (from Gemini + Codex + Perplexity)

{combined_summary}

## YOUR EXECUTION REPORT FORMAT

After executing, produce this report:

### Executed
- [action 1] -- [result]
- [action 2] -- [result]

### Delegated to Sub-Agents
- [agent_name]: [what was delegated] -- [result]

### Deferred (needs human input)
- [item] -- [reason for deferral]

### Skipped
- [item] -- [why it was skipped]

Now execute.
"""
    return prompt


def run(
    user_query: str,
    combined_summary: str,
    category: str = "full",
    war_room_dir: str = "",
    timeout: int = 300,
) -> ManagerResult:
    """Run Claude as the executor via `claude -p` and return a ManagerResult."""
    result = ManagerResult(
        manager="claude",
        role="Chief Operator / Executor",
        status="running",
        started_at=_now(),
    )

    start = time.time()

    prompt = _build_execution_prompt(
        user_query=user_query,
        combined_summary=combined_summary,
        category=category,
        war_room_dir=war_room_dir,
    )

    # Build claude command -- use sonnet for speed, full tool access
    # Pipe prompt via stdin to avoid shell escaping issues with long prompts
    cmd = [
        "claude",
        "-p",
        "--model", "sonnet",
        "--allowedTools",
        "Bash,Read,Write,Edit,Glob,Grep,Task",
    ]

    # Must unset these env vars or claude refuses to run (nested session error)
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)
    env.pop("CLAUDE_CODE_ENTRY_POINT", None)

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
            cwd=str(WORKSPACE),
            env=env,
        )
        output = proc.stdout.strip()
        if output:
            result.response_text = output
            result.status = "done"
        elif proc.returncode == 0:
            result.response_text = "(empty response)"
            result.status = "done"
        else:
            result.status = "failed"
            result.error = proc.stderr.strip()[:500]
    except subprocess.TimeoutExpired:
        result.status = "timeout"
        result.error = f"Claude execution timed out after {timeout}s"
    except FileNotFoundError:
        result.status = "failed"
        result.error = "claude binary not found in PATH"

    result.finished_at = _now()
    result.duration_s = round(time.time() - start, 1)

    # Write execution report to war room
    if war_room_dir and result.response_text:
        _write_execution_report(result, war_room_dir)

    return result


def run_detached(
    user_query: str,
    combined_summary: str,
    category: str = "full",
    war_room_dir: str = "",
    timeout: int = 300,
) -> None:
    """Fire-and-forget: launch Claude execution as a detached subprocess.

    Used when the dispatcher should not block waiting for Claude to finish.
    The execution report gets written to the war room when complete.
    """
    prompt = _build_execution_prompt(
        user_query=user_query,
        combined_summary=combined_summary,
        category=category,
        war_room_dir=war_room_dir,
    )

    # Write prompt to a file the detached process reads
    ts = int(time.time())
    prompt_file = Path("/tmp") / f".hive_exec_{ts}.txt"
    prompt_file.write_text(prompt, encoding="utf-8")

    report_path = ""
    if war_room_dir:
        report_path = str(Path(war_room_dir) / "05_claude_execution_report.md")

    # Runner script reads prompt, calls claude, saves output, notifies Slack
    runner = Path("/tmp") / f".hive_exec_runner_{ts}.sh"
    watcher_script = str(
        WORKSPACE
        / "03_AUTOMATION_CORE"
        / "01_Scripts"
        / "ai_workers"
        / "war_room_watcher.py"
    )
    runner_script = f"""#!/usr/bin/env bash
unset CLAUDECODE CLAUDE_CODE CLAUDE_CODE_ENTRY_POINT

OUTPUT=$(cat "{prompt_file}" | claude -p --model sonnet \\
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Task" \\
  2>/tmp/.hive_exec_stderr.log) || true

if [ -n "$OUTPUT" ] && [ -n "{report_path}" ]; then
    cat > "{report_path}" << 'ENDREPORT'
# CLAUDE EXECUTION REPORT

**Status**: done

---

ENDREPORT
    echo "$OUTPUT" >> "{report_path}"

    # Trigger watcher scan so Slack notification fires immediately
    python3 "{watcher_script}" --once --no-execute 2>/dev/null &
fi

rm -f "{prompt_file}" "{runner}"
"""
    runner.write_text(runner_script, encoding="utf-8")
    runner.chmod(0o755)

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)
    env.pop("CLAUDE_CODE_ENTRY_POINT", None)

    subprocess.Popen(
        ["bash", str(runner)],
        cwd=str(WORKSPACE),
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _write_execution_report(result: ManagerResult, war_room_dir: str) -> None:
    """Write Claude's execution report to the war room."""
    try:
        report_path = Path(war_room_dir) / "05_claude_execution_report.md"
        report = "# CLAUDE EXECUTION REPORT\n\n"
        report += f"**Status**: {result.status} | **Duration**: {result.duration_s}s\n\n"
        report += "---\n\n"
        report += result.response_text or "(no output)"
        report += "\n"
        report_path.write_text(report, encoding="utf-8")
    except Exception:
        pass
