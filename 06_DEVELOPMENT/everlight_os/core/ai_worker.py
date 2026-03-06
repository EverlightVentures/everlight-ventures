"""
Everlight OS — Unified AI worker.
Calls OpenAI, Perplexity, and (future) other services via API.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"))
except ImportError:
    pass

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


def call_openai(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    """Call OpenAI chat completion API. Returns response text."""
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set")
        return "[ERROR: OPENAI_API_KEY not configured]"
    if not requests:
        return "[ERROR: requests library not installed]"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return f"[ERROR: OpenAI call failed — {e}]"


def call_perplexity(
    query: str,
    model: str = "sonar",
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Call Perplexity API for research. Returns response text with citations."""
    if not PERPLEXITY_API_KEY:
        logger.error("PERPLEXITY_API_KEY not set")
        return "[ERROR: PERPLEXITY_API_KEY not configured]"
    if not requests:
        return "[ERROR: requests library not installed]"

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a research assistant. Provide thorough, factual answers with sources.",
            },
            {"role": "user", "content": query},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        # Append citations if available
        citations = data.get("citations", [])
        if citations:
            text += "\n\n## Sources\n"
            for i, c in enumerate(citations, 1):
                text += f"{i}. {c}\n"
        return text
    except Exception as e:
        logger.error(f"Perplexity API error: {e}")
        return f"[ERROR: Perplexity call failed — {e}]"


def call_anthropic(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "claude-sonnet-4-6",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    use_cache: bool = False,
    use_thinking: bool = False,
    thinking_budget: int = 5000,
) -> str:
    """Call Anthropic /v1/messages API natively.

    Supports prompt caching (use_cache=True) and extended thinking
    (use_thinking=True). Uses the Anthropic Messages API directly
    -- no OpenAI compatibility layer needed.

    Args:
        prompt: User message content.
        system: System prompt. Set use_cache=True to cache it.
        model: Claude model ID (e.g. claude-sonnet-4-6, claude-opus-4-6).
        temperature: Sampling temperature (ignored when use_thinking=True).
        max_tokens: Max output tokens.
        use_cache: Attach cache_control to system prompt for prompt caching.
        use_thinking: Enable extended thinking (claude-3-7+ only).
        thinking_budget: Token budget for thinking block.
    """
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return "[ERROR: ANTHROPIC_API_KEY not configured]"
    if not requests:
        return "[ERROR: requests library not installed]"

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # System prompt - optionally cached
    if use_cache:
        system_block: Any = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    else:
        system_block = system

    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_block,
        "messages": [{"role": "user", "content": prompt}],
    }

    if use_thinking:
        # Extended thinking uses streaming thinking blocks
        headers["anthropic-beta"] = headers.get("anthropic-beta", "") + ",interleaved-thinking-2025-05-14"
        headers["anthropic-beta"] = headers["anthropic-beta"].lstrip(",")
        payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        # temperature must be 1 when thinking is enabled
        payload["temperature"] = 1
    else:
        payload["temperature"] = temperature

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Extract text from content blocks (thinking blocks are skipped)
        text_parts = [
            block["text"]
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_parts) if text_parts else "[empty response]"
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return f"[ERROR: Anthropic call failed -- {e}]"


def call_groq(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "llama-3.1-70b-versatile",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Call Groq for sub-second inference. Best for fast classification and triage.

    Groq uses the OpenAI-compatible API format.
    Typical latency: 200-500ms for short responses.
    Good models: llama-3.1-70b-versatile, mixtral-8x7b-32768
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set")
        return "[ERROR: GROQ_API_KEY not configured]"
    if not requests:
        return "[ERROR: requests library not installed]"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"[ERROR: Groq call failed -- {e}]"


def call_worker(
    worker: str,
    prompt: str,
    system: str = "",
    **kwargs,
) -> str:
    """Dispatch to the right AI service by worker name.

    Supported workers:
      anthropic / claude  -> native Anthropic Messages API (prompt caching, thinking)
      openai / gpt        -> OpenAI chat completions
      perplexity / ppx    -> Perplexity research with citations
      groq                -> Groq fast inference (classification, triage)
      local               -> pass-through (no API call)
    """
    if worker in ("anthropic", "claude"):
        return call_anthropic(prompt, system=system or "You are a helpful assistant.", **kwargs)
    elif worker in ("openai", "gpt"):
        return call_openai(prompt, system=system or "You are a helpful assistant.", **kwargs)
    elif worker in ("perplexity", "ppx"):
        return call_perplexity(prompt, **kwargs)
    elif worker == "groq":
        return call_groq(prompt, system=system or "You are a helpful assistant.", **kwargs)
    elif worker == "local":
        # For steps that don't need AI (file parsing, metric computation)
        return prompt
    else:
        logger.warning(f"Unknown worker '{worker}', falling back to Anthropic")
        return call_anthropic(prompt, system=system or "You are a helpful assistant.", **kwargs)
