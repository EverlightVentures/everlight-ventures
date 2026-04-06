"""
LLM Gateway -- LiteLLM-powered universal model router.

One API for every LLM. Cheap queries go to Ollama (free), important
ones go to Claude (paid). Agents never know which model they're using.

Usage:
    from llm_gateway import ask, ask_agent
    response = ask("Score this lead", model="fast")    # -> Ollama
    response = ask("Write a proposal", model="smart")  # -> Claude
    response = ask_agent("piper_reeves", "Draft outreach for Dr. Smith")

Routes:
    "fast"   -> ollama/phi3:mini  (free, 30s, good for scoring/classification)
    "smart"  -> claude-sonnet-4-6 (paid, 3s, good for writing/reasoning)
    "best"   -> claude-opus-4-6   (paid, 5s, good for complex analysis)
    "local"  -> ollama/phi3:mini  (explicit local)

All calls auto-traced to Langfuse when keys are set.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

log = logging.getLogger(__name__)

# Model aliases
MODEL_ROUTES = {
    "fast": "ollama/phi3:mini",
    "local": "ollama/phi3:mini",
    "smart": "claude-sonnet-4-6",
    "best": "claude-opus-4-6",
    "cheap": "ollama/phi3:mini",
}

# Env
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OLLAMA_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")


def ask(
    prompt: str,
    model: str = "fast",
    system: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    agent_name: str = "hive",
) -> str:
    """Universal LLM call. Routes to the right model automatically.

    Args:
        prompt: The question/instruction
        model: "fast" (free Ollama), "smart" (Claude Sonnet), "best" (Claude Opus)
        system: System prompt
        temperature: 0-1
        max_tokens: Max response length
        agent_name: For Langfuse tracing

    Returns:
        Response text
    """
    import litellm

    resolved_model = MODEL_ROUTES.get(model, model)
    is_ollama = resolved_model.startswith("ollama/")

    # Configure LiteLLM
    if is_ollama:
        litellm.api_base = OLLAMA_BASE
    if ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    t0 = time.time()
    try:
        response = litellm.completion(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        duration_ms = (time.time() - t0) * 1000

        # Trace to Langfuse
        try:
            from langfuse_bridge import trace_ollama_call, trace_claude_call
            if is_ollama:
                trace_ollama_call(agent_name, prompt[:500], resolved_model, text[:500], duration_ms)
            else:
                usage = response.usage
                trace_claude_call(
                    agent_name, prompt[:500], text[:500], resolved_model,
                    tokens_in=usage.prompt_tokens if usage else 0,
                    tokens_out=usage.completion_tokens if usage else 0,
                    duration_ms=duration_ms,
                )
        except Exception:
            pass

        return text

    except Exception as e:
        log.warning(f"LLM call failed ({resolved_model}): {e}")
        # Fallback: if smart/best fails, try local
        if not is_ollama:
            log.info("Falling back to local Ollama")
            return ask(prompt, model="local", system=system, temperature=temperature,
                       max_tokens=max_tokens, agent_name=agent_name)
        return f"[LLM Error: {e}]"


def ask_agent(
    agent_slug: str,
    prompt: str,
    model: str = "fast",
    include_personality: bool = True,
) -> str:
    """Ask a question AS a specific agent (with their personality).

    The agent's personality and role are loaded from their profile
    and injected as the system prompt.
    """
    system = ""
    if include_personality:
        try:
            from pathlib import Path
            profiles_path = Path(__file__).parent.parent / "hive_mind" / "agent_profiles" / "all_profiles.json"
            if not profiles_path.exists():
                profiles_path = Path("/home/opc/06_DEVELOPMENT/everlight_os/hive_mind/agent_profiles/all_profiles.json")
            if profiles_path.exists():
                for p in json.loads(profiles_path.read_text()):
                    if p.get("slug") == agent_slug:
                        system = (
                            f"You are {p['name']}, {p['title']} at Everlight Ventures. "
                            f"{p.get('bio', '')} "
                            f"Personality: {', '.join(p.get('personality', []))}. "
                            f"Respond in character. Be concise and actionable."
                        )
                        break
        except Exception:
            pass

    return ask(prompt, model=model, system=system, agent_name=agent_slug)


def get_available_models() -> list[dict]:
    """List available models and their routes."""
    models = []
    for alias, model in MODEL_ROUTES.items():
        is_ollama = model.startswith("ollama/")
        models.append({
            "alias": alias,
            "model": model,
            "provider": "ollama" if is_ollama else "anthropic",
            "cost": "free" if is_ollama else "paid",
        })
    return models
