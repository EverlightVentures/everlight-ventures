"""
Langfuse Bridge -- LLM observability for all Everlight agent calls.

Wraps Ollama and any LLM API calls with Langfuse tracing so every
agent interaction is tracked: tokens, latency, cost, success/failure.

Setup:
  1. Go to http://129.159.38.250:3100 and create account
  2. Create project "Everlight-Hive"
  3. Copy public/secret keys
  4. Set in .env: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

Uses: Langfuse SDK (MIT license) -- free, open source.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

log = logging.getLogger(__name__)

# Langfuse config (set via env or hardcode after initial setup)
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3100")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")

_langfuse = None
_enabled = False


def _get_langfuse():
    """Lazy init Langfuse client."""
    global _langfuse, _enabled
    if _langfuse is not None:
        return _langfuse

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        log.debug("Langfuse keys not set -- observability disabled")
        _enabled = False
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        _enabled = True
        log.info(f"Langfuse connected: {LANGFUSE_HOST}")
        return _langfuse
    except Exception as e:
        log.warning(f"Langfuse init failed: {e}")
        _enabled = False
        return None


def trace_ollama_call(
    agent_name: str,
    prompt: str,
    model: str = "phi3:mini",
    response: str = "",
    duration_ms: float = 0,
    metadata: dict | None = None,
):
    """Log an Ollama LLM call to Langfuse."""
    lf = _get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(
            name=f"ollama/{agent_name}",
            metadata={
                "agent": agent_name,
                "model": model,
                **(metadata or {}),
            },
        )
        trace.generation(
            name=f"{agent_name}_generation",
            model=model,
            input=prompt,
            output=response,
            metadata={"duration_ms": duration_ms},
        )
        lf.flush()
    except Exception as e:
        log.debug(f"Langfuse trace failed: {e}")


def trace_claude_call(
    agent_name: str,
    prompt: str,
    response: str = "",
    model: str = "claude-opus-4-6",
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: float = 0,
    metadata: dict | None = None,
):
    """Log a Claude API call to Langfuse."""
    lf = _get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(
            name=f"claude/{agent_name}",
            metadata={
                "agent": agent_name,
                "model": model,
                **(metadata or {}),
            },
        )
        trace.generation(
            name=f"{agent_name}_generation",
            model=model,
            input=prompt,
            output=response,
            usage={
                "input": tokens_in,
                "output": tokens_out,
            },
            metadata={"duration_ms": duration_ms},
        )
        lf.flush()
    except Exception as e:
        log.debug(f"Langfuse trace failed: {e}")


def trace_agent_action(
    agent_name: str,
    action: str,
    input_data: dict | None = None,
    output_data: dict | None = None,
    duration_ms: float = 0,
    level: str = "DEFAULT",
):
    """Log any agent action (not just LLM calls) to Langfuse."""
    lf = _get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(
            name=f"agent/{agent_name}/{action}",
            metadata={"agent": agent_name, "action": action},
        )
        trace.span(
            name=action,
            input=input_data,
            output=output_data,
            level=level,
            metadata={"duration_ms": duration_ms},
        )
        lf.flush()
    except Exception as e:
        log.debug(f"Langfuse span failed: {e}")


def call_ollama(
    prompt: str,
    model: str = "phi3:mini",
    agent_name: str = "hive",
    system: str = "",
    temperature: float = 0.7,
) -> str:
    """Call Ollama AND trace it to Langfuse. Drop-in replacement for raw Ollama calls.

    Usage:
        response = call_ollama("Score this lead 0-100: ...", agent_name="filter_banks")
    """
    import urllib.request

    t0 = time.time()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            response_text = result.get("response", "")
            duration_ms = (time.time() - t0) * 1000

            # Trace to Langfuse
            trace_ollama_call(
                agent_name=agent_name,
                prompt=prompt,
                model=model,
                response=response_text,
                duration_ms=duration_ms,
                metadata={
                    "eval_count": result.get("eval_count", 0),
                    "eval_duration_ns": result.get("eval_duration", 0),
                    "total_duration_ns": result.get("total_duration", 0),
                },
            )
            return response_text

    except Exception as e:
        duration_ms = (time.time() - t0) * 1000
        trace_agent_action(
            agent_name=agent_name,
            action="ollama_call_failed",
            input_data={"prompt": prompt[:200], "model": model},
            output_data={"error": str(e)},
            duration_ms=duration_ms,
            level="ERROR",
        )
        log.warning(f"Ollama call failed for {agent_name}: {e}")
        return ""


def get_status() -> dict:
    """Check Langfuse connection status."""
    return {
        "enabled": _enabled,
        "host": LANGFUSE_HOST,
        "has_keys": bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY),
    }
