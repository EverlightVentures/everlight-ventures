#!/usr/bin/env python3
"""
Hive Model Router -- Intelligent model routing for the Everlight Ventures Hive.

Classifies task complexity and routes to the optimal model:
  BASIC    -> Gemini Flash (free) or gpt-4o-mini (cheapest)
  STANDARD -> gpt-4o-mini (mid-tier)
  COMPLEX  -> gpt-4o (best reasoning)

Tracks estimated costs per tier per day in /home/opc/hive_model_costs.json.

Usage:
  from hive_model_router import route_and_call, get_blinko_context

  text = route_and_call(system_prompt, user_prompt, task_type="delegation")

CLI:
  python3 hive_model_router.py --cost-report
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("model_router")

# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------
COST_LOG = Path("/home/opc/hive_model_costs.json")

# Approximate costs per 1M tokens (USD)
TOKEN_COSTS = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
}

# ---------------------------------------------------------------------------
# Model tiers -- configurable
# ---------------------------------------------------------------------------
MODELS = {
    "basic": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 150,
    },
    "standard": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 300,
    },
    "complex": {
        "provider": "openai",
        "model": "gpt-4o",
        "max_tokens": 500,
    },
}

# Override basic tier with Gemini Flash if key is available (free tier: 15 RPM)
if os.environ.get("GEMINI_API_KEY"):
    MODELS["basic"] = {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "max_tokens": 150,
    }

# ---------------------------------------------------------------------------
# Task classification
# ---------------------------------------------------------------------------
BASIC_TASKS = {
    "watercooler", "clock_in", "clock_out", "lunch_break",
    "social", "greeting", "sign_off", "dinner_break",
}

COMPLEX_TASKS = {
    "delegation", "strategic", "underwriting", "analysis",
    "deal_review", "compliance_review", "risk_assessment",
    "cross_team", "executive",
}

# Everything else (standup, checkin, response, etc.) -> standard


def classify_task(task_type: str, context: str = "") -> str:
    """Classify task complexity for model routing.

    Returns one of: 'basic', 'standard', 'complex'.
    """
    task_type = task_type.lower().strip()

    if task_type in BASIC_TASKS:
        return "basic"
    elif task_type in COMPLEX_TASKS:
        return "complex"
    else:
        return "standard"


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _call_openai(system: str, user: str, model: str, max_tokens: int) -> str | None:
    """Call OpenAI chat completions API."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        log.error("OPENAI_API_KEY not set")
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": 0.85,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        log_cost("openai", model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("OpenAI error (%s): %s", model, e)
        return None


def _call_gemini(system: str, user: str, model: str, max_tokens: int) -> str | None:
    """Call Google Gemini API (free tier: 15 RPM for Flash)."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        log.error("GEMINI_API_KEY not set")
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": f"{system}\n\n{user}"}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.85,
                },
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        # Extract token counts from usageMetadata if present
        usage = data.get("usageMetadata", {})
        log_cost("gemini", model, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        log.error("Gemini error (%s): %s", model, e)
        return None


def _call_anthropic(system: str, user: str, model: str, max_tokens: int) -> str | None:
    """Call Anthropic messages API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set")
        return None
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        log_cost("anthropic", model, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return data["content"][0]["text"].strip()
    except Exception as e:
        log.error("Anthropic error (%s): %s", model, e)
        return None


# Provider dispatch table
_PROVIDERS = {
    "openai": _call_openai,
    "gemini": _call_gemini,
    "anthropic": _call_anthropic,
}

# Fallback chain: if primary provider fails, try these in order
_FALLBACK_CHAIN = {
    "gemini": [("openai", "gpt-4o-mini")],
    "anthropic": [("openai", "gpt-4o-mini")],
    "openai": [],  # OpenAI is the last resort
}


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

def log_cost(provider: str, model: str, input_tokens: int, output_tokens: int):
    """Log estimated cost for monitoring. Appends to daily cost log."""
    costs = TOKEN_COSTS.get(model, {"input": 0, "output": 0})
    est_cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000

    today = datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")

    try:
        data = json.loads(COST_LOG.read_text()) if COST_LOG.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    if today not in data:
        data[today] = {"calls": 0, "total_cost": 0.0, "by_model": {}}

    day = data[today]
    day["calls"] += 1
    day["total_cost"] = round(day["total_cost"] + est_cost, 6)

    if model not in day["by_model"]:
        day["by_model"][model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}

    m = day["by_model"][model]
    m["calls"] += 1
    m["input_tokens"] += input_tokens
    m["output_tokens"] += output_tokens
    m["cost"] = round(m["cost"] + est_cost, 6)

    # Keep only last 30 days
    if len(data) > 30:
        oldest = sorted(data.keys())[0]
        del data[oldest]

    try:
        COST_LOG.write_text(json.dumps(data, indent=2))
    except OSError as e:
        log.warning("Failed to write cost log: %s", e)


# ---------------------------------------------------------------------------
# Blinko shared memory
# ---------------------------------------------------------------------------

BLINKO_URL = "http://129.159.38.250:1111"


def get_blinko_context(query: str, max_notes: int = 3) -> str:
    """Pull relevant context from Blinko for complex tasks.

    Gives agents 'shared memory' -- they can reference what happened in
    previous sessions, deals, pipeline status, etc.
    """
    try:
        r = requests.post(
            f"{BLINKO_URL}/api/v1/note/list",
            json={"searchText": query, "page": 1, "pageSize": max_notes},
            timeout=5,
        )
        r.raise_for_status()
        notes = r.json().get("items", [])
        if not notes:
            return ""
        return "\n---\n".join(n.get("content", "")[:200] for n in notes)
    except Exception as e:
        log.debug("Blinko context fetch failed: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Main routing function
# ---------------------------------------------------------------------------

def route_and_call(
    system: str,
    user: str,
    task_type: str = "standard",
    max_tokens: int | None = None,
) -> str | None:
    """Route to optimal model based on task type, then call.

    Args:
        system: System prompt.
        user: User prompt.
        task_type: One of the known task types (watercooler, delegation, etc.)
                   or 'basic'/'standard'/'complex' directly.
        max_tokens: Override max tokens. Uses tier default if None.

    Returns:
        Generated text, or None if all providers fail.
    """
    tier = classify_task(task_type)
    model_config = MODELS[tier]

    tokens = max_tokens or model_config["max_tokens"]
    provider = model_config["provider"]
    model = model_config["model"]

    log.debug("Routing: task=%s tier=%s provider=%s model=%s tokens=%d",
              task_type, tier, provider, model, tokens)

    # Try primary provider
    call_fn = _PROVIDERS.get(provider)
    if call_fn:
        result = call_fn(system, user, model, tokens)
        if result:
            return result

    # Fallback chain
    for fb_provider, fb_model in _FALLBACK_CHAIN.get(provider, []):
        log.info("Falling back: %s/%s -> %s/%s", provider, model, fb_provider, fb_model)
        fb_fn = _PROVIDERS.get(fb_provider)
        if fb_fn:
            result = fb_fn(system, user, fb_model, tokens)
            if result:
                return result

    # Last resort: OpenAI gpt-4o-mini
    if provider != "openai" or model != "gpt-4o-mini":
        log.info("Last resort fallback to gpt-4o-mini")
        return _call_openai(system, user, "gpt-4o-mini", tokens)

    return None


# ---------------------------------------------------------------------------
# CLI: cost report
# ---------------------------------------------------------------------------

def print_cost_report():
    """Print today's model usage and estimated costs."""
    if not COST_LOG.exists():
        print("No cost data found at", COST_LOG)
        return

    try:
        data = json.loads(COST_LOG.read_text())
    except (json.JSONDecodeError, OSError):
        print("Failed to read cost log.")
        return

    today = datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Hive Model Router -- Cost Report")
    print(f"{'='*60}")

    # Show today first, then recent days
    days_to_show = sorted(data.keys(), reverse=True)[:7]

    for day in days_to_show:
        d = data[day]
        marker = " <-- TODAY" if day == today else ""
        print(f"\n  {day}{marker}")
        print(f"  Total calls: {d['calls']}  |  Est. cost: ${d['total_cost']:.4f}")

        if d.get("by_model"):
            for model_name, m in sorted(d["by_model"].items()):
                in_tok = m.get("input_tokens", 0)
                out_tok = m.get("output_tokens", 0)
                print(f"    {model_name:30s}  calls={m['calls']:4d}  "
                      f"in={in_tok:7,}  out={out_tok:7,}  ${m['cost']:.4f}")

    # Summary
    total_calls = sum(d["calls"] for d in data.values())
    total_cost = sum(d["total_cost"] for d in data.values())
    print(f"\n{'='*60}")
    print(f"  All-time: {total_calls} calls, ${total_cost:.4f} est. cost")
    print(f"  Tracking {len(data)} days (max 30)")

    # Show current tier config
    print(f"\n  Current routing config:")
    for tier_name, cfg in MODELS.items():
        print(f"    {tier_name:10s} -> {cfg['provider']}/{cfg['model']} (max {cfg['max_tokens']} tokens)")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--cost-report" in sys.argv:
        print_cost_report()
    else:
        print("Hive Model Router")
        print("Usage: python3 hive_model_router.py --cost-report")
        print()
        print("Import usage:")
        print("  from hive_model_router import route_and_call, get_blinko_context")
        print()
        print("Current config:")
        for tier, cfg in MODELS.items():
            print(f"  {tier:10s} -> {cfg['provider']}/{cfg['model']} (max {cfg['max_tokens']} tokens)")
