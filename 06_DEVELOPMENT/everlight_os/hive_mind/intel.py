"""
Perplexity Intel Scout - runs FIRST before other managers.
Uses direct Perplexity API with Claude WebSearch fallback.

Query strategy: adapts research prompt to the query category instead of
dumping all 8 news beats on every request. Engineering questions get
library/tool research, trading gets market data, etc.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from .config import load_roster, get_wrapper_path, WORKSPACE
from .contracts import ManagerResult, _now

_ENV_FILE = WORKSPACE / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"
_LOG_DIR = WORKSPACE / "_logs" / "intel_debug"


def _log(msg: str) -> None:
    """Debug log for intel failures."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_LOG_DIR / "intel.log", "a") as f:
            f.write(f"[{_now()}] {msg}\n")
    except Exception:
        pass


def _load_api_key() -> str:
    """Load Perplexity API key from .env or environment."""
    if _ENV_FILE.exists():
        try:
            for line in _ENV_FILE.read_text().splitlines():
                if line.startswith("PERPLEXITY_API_KEY="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return os.environ.get("PERPLEXITY_API_KEY", "")


# Category-specific research prompts (matched by router category)
_CATEGORY_PROMPTS = {
    "engineering": (
        "Research the best tools, libraries, and patterns for this technical task. "
        "Focus on: current best-practice solutions, framework comparisons, "
        "recommended packages, architecture patterns, and real-world examples. "
        "Include links to documentation and GitHub repos where available."
    ),
    "trading": (
        "Research current market data and trading intelligence. "
        "Focus on: latest prices, market sentiment, exchange news, "
        "regulatory changes, and technical analysis insights. "
        "Include sourced data with timestamps."
    ),
    "content": (
        "Research content strategy, SEO patterns, and publishing best practices. "
        "Focus on: trending topics, content formats that perform well, "
        "audience engagement tactics, and platform-specific strategies."
    ),
    "business": (
        "Research business strategy, market opportunities, and competitive intelligence. "
        "Focus on: industry trends, competitor analysis, revenue models, "
        "growth strategies, and actionable market data."
    ),
    "research": (
        "Provide comprehensive research findings with sourced data. "
        "Focus on: current facts, recent developments, expert analysis, "
        "and verifiable statistics. Include links and dates."
    ),
    "operations": (
        "Research automation tools, deployment strategies, and workflow optimization. "
        "Focus on: DevOps best practices, CI/CD patterns, infrastructure tools, "
        "and efficiency benchmarks."
    ),
}

_DEFAULT_PROMPT = (
    "Research the following topic thoroughly. Provide current, sourced findings "
    "with links and dates. Focus on the most relevant and actionable information."
)


def _detect_category(user_prompt: str, roster: dict) -> str:
    """Detect the query category using the same keyword logic as the router."""
    rules = roster.get("routing_rules", {})
    prompt_lower = user_prompt.lower()
    scores = {}
    for category, rule in rules.items():
        score = sum(1 for kw in rule.get("keywords", []) if kw.lower() in prompt_lower)
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else "research"


def _build_intel_query(user_prompt: str, roster: dict, category: str = None) -> str:
    """Build a focused research query adapted to the query category."""
    if category is None:
        category = _detect_category(user_prompt, roster)

    ctx = roster.get("user_context", {})
    tz = ctx.get("timezone", "PT")

    focus = _CATEGORY_PROMPTS.get(category, _DEFAULT_PROMPT)

    query = (
        f"{focus}\n\n"
        f"User's question: {user_prompt}\n\n"
        f"Context: User is in {tz}, {ctx.get('location', 'US')}."
    )
    return query


def _call_perplexity_api(query: str, api_key: str, timeout: int = 30) -> str:
    """Direct Perplexity API call."""
    import requests

    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("PERPLEXITY_MODEL", "sonar"),
            "messages": [
                {"role": "system", "content": "Research intelligence officer. Provide sourced, current findings."},
                {"role": "user", "content": query},
            ],
            "temperature": 0.2,
            "max_tokens": 1500,
        },
        timeout=timeout,
    )
    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        if citations:
            content += "\n\nSources:\n"
            for i, c in enumerate(citations, 1):
                content += f"  [{i}] {c}\n"
        return content
    elif resp.status_code == 401:
        raise PermissionError("Perplexity API key expired or revoked (401)")
    else:
        _log(f"Perplexity API returned HTTP {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
    return ""


def _call_websearch_fallback(query: str, timeout: int = 60) -> str:
    """Fallback: use Gemini CLI for research when Perplexity API is down.

    Gemini has built-in web search (Google grounding) and its CLI works
    reliably even from within Claude Code sessions.
    """
    cmd = [
        "gemini", "-p",
        f"Research this topic thoroughly and provide sourced findings with "
        f"links. Be specific with package names, version numbers, and URLs:\n\n{query}",
    ]

    _log(f"Gemini research fallback starting...")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, cwd="/tmp",
        )
        output = result.stdout.strip()
        if output:
            # Filter Gemini hook noise from stdout
            clean_lines = []
            for line in output.splitlines():
                if any(noise in line for noise in [
                    "MCP server", "execution plan", "Expanding hook",
                    "Hook execution", "hooks executed", "/mcp auth",
                    "hook(s) to execute",
                ]):
                    continue
                clean_lines.append(line)
            clean = "\n".join(clean_lines).strip()
            if clean:
                _log(f"Gemini fallback succeeded ({len(clean)} chars)")
                return f"[Research via Gemini]\n{clean}"
        # If we get here, output was empty or all noise
        stderr = result.stderr.strip()
        err_lines = [l for l in stderr.splitlines()
                     if not l.startswith("[ExtensionManager]")]
        _log(f"Gemini fallback empty: rc={result.returncode} err={' '.join(err_lines)[:200]}")
    except FileNotFoundError:
        _log("Gemini fallback failed: gemini CLI not found")
    except subprocess.TimeoutExpired:
        _log(f"Gemini fallback timed out after {timeout}s")
    except Exception as e:
        _log(f"Gemini fallback exception: {e}")

    return ""


def run_intel_scout(user_prompt: str, roster: dict = None) -> ManagerResult:
    """Run Perplexity as the intel scout (phase 1). Returns a ManagerResult."""
    if roster is None:
        roster = load_roster()

    timeout = roster["managers"]["perplexity"].get("timeout_seconds", 30)
    category = _detect_category(user_prompt, roster)
    query = _build_intel_query(user_prompt, roster, category)

    result = ManagerResult(
        manager="perplexity",
        role="Intelligence Anchor / News Desk",
        status="running",
        started_at=_now(),
    )
    start = time.time()

    response = ""
    errors = []

    # Method A: Direct Perplexity API
    api_key = _load_api_key()
    if api_key:
        try:
            response = _call_perplexity_api(query, api_key, timeout=timeout)
        except PermissionError as e:
            errors.append(str(e))
            _log(f"Perplexity API: {e}")
        except Exception as e:
            errors.append(f"Perplexity API error: {e}")
            _log(f"Perplexity API: {e}")
    else:
        errors.append("No Perplexity API key found")
        _log("No API key")

    # Method B: Claude WebSearch fallback
    if not response:
        _log(f"Falling back to WebSearch (category={category})")
        try:
            response = _call_websearch_fallback(query, timeout=60)
            if response:
                errors.append("Used WebSearch fallback (Perplexity API unavailable)")
        except Exception as e:
            errors.append(f"WebSearch fallback failed: {e}")
            _log(f"WebSearch fallback: {e}")

    if response:
        result.response_text = response
        result.status = "done"
        result.error = "; ".join(errors) if errors else ""
    else:
        result.status = "failed"
        result.error = "; ".join(errors) if errors else "No intel gathered from any source"
        _log(f"ALL methods failed: {result.error}")

    result.finished_at = _now()
    result.duration_s = round(time.time() - start, 1)
    result.employees_consulted = [
        b["name"] for b in roster["managers"]["perplexity"].get("research_beats", [])
    ]

    return result
