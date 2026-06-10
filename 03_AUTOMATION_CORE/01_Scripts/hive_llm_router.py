"""hive_llm_router.py - Smart LLM routing for the Everlight Hive.

Built from 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/claude_code_plus_openrouter_free.txt.

ROUTING RULES:
- HIGH_STAKES (trading, compliance, contracts, money-movement) -> Opus direct via Anthropic
- MEDIUM_STAKES (broker outreach, wholesale pitches, agent synthesis) -> Sonnet via Anthropic
- LOW_STAKES (slack replies, log summaries, tag creation) -> Haiku or OpenRouter fallback
- RESEARCH (factual Q&A, sourced answers) -> Perplexity Sonar if available, else Haiku

The XLM bot's claude_advisor.py is NEVER touched. Executive decisions stay Opus.

Usage:
    from hive_llm_router import ask

    # Low-stakes -> cheapest
    text = ask("Summarize this log in 3 bullets", stakes="low", text=log)

    # High-stakes -> Opus
    text = ask("Review this contract for compliance issues", stakes="high", text=contract)

    # Research -> sourced answer
    text = ask("What is the current XLM circulating supply?", stakes="research")
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

STAKES_TO_MODEL: dict[str, dict[str, Any]] = {
    "high": {
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "max_tokens": 2000,
    },
    "medium": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "max_tokens": 1500,
    },
    "low": {
        "provider": "openrouter",
        "model": "anthropic/claude-haiku-4.5",  # OpenRouter slug for Haiku
        "fallback_model": "meta-llama/llama-3.1-8b-instruct:free",  # free tier if Haiku unavailable
        "max_tokens": 800,
    },
    "research": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
    },
}

_env_loaded = False
_keys: dict[str, str] = {}


def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    for k in ["ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
        _keys[k] = os.environ.get(k, "")
    if not _keys.get("ANTHROPIC_API_KEY"):
        env_file = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" not in line or line.startswith("#"):
                    continue
                k, _, v = line.partition("=")
                if k.strip() in {"ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"}:
                    _keys[k.strip()] = v.strip().strip('"').strip("'")
    _env_loaded = True


def _call_anthropic(model: str, prompt: str, max_tokens: int) -> str:
    _load_env()
    key = _keys.get("ANTHROPIC_API_KEY", "")
    if not key:
        return ""
    body = json.dumps(
        {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    ).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode())
        return data.get("content", [{}])[0].get("text", "")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""


def _call_openrouter(model: str, prompt: str, max_tokens: int, fallback_model: str = "") -> str:
    _load_env()
    key = _keys.get("OPENROUTER_API_KEY", "")
    if not key:
        # Degrade: if no OpenRouter key, try Anthropic Haiku directly
        return _call_anthropic("claude-haiku-4-5-20251001", prompt, max_tokens)
    for m in [model, fallback_model]:
        if not m:
            continue
        body = json.dumps(
            {
                "model": m,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://everlightventures.io",
                "X-Title": "Everlight Hive",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
    return ""


def ask(
    instruction: str,
    *,
    stakes: str = "low",
    text: str = "",
    max_tokens: int | None = None,
) -> str:
    """Route an LLM request based on stakes level.

    Args:
        instruction: What you want the model to do.
        stakes: "high" | "medium" | "low" | "research". Governs model + provider.
        text: Optional context to attach (document, log, data blob).
        max_tokens: Override the default max_tokens for this stakes tier.

    Returns:
        Model text response. Empty string on total failure.
    """
    cfg = STAKES_TO_MODEL.get(stakes, STAKES_TO_MODEL["low"])
    prompt = f"{instruction}\n\n{text}" if text else instruction
    tokens = max_tokens or cfg["max_tokens"]

    if cfg["provider"] == "anthropic":
        return _call_anthropic(cfg["model"], prompt, tokens)
    if cfg["provider"] == "openrouter":
        return _call_openrouter(cfg["model"], prompt, tokens, cfg.get("fallback_model", ""))
    return ""


def estimate_savings(monthly_opus_spend: float) -> dict[str, Any]:
    """Rough projection: if you move 40% of calls to Haiku/OpenRouter, how much you save."""
    # Opus = ~$15/M input, Sonnet ~$3/M, Haiku ~$1/M. Assume avg 40% of volume is low-stakes.
    low_volume_share = 0.40
    opus_rate = 15.0  # per 1M tokens, rough
    haiku_rate = 1.0
    savings_ratio = (opus_rate - haiku_rate) / opus_rate
    monthly_savings = monthly_opus_spend * low_volume_share * savings_ratio
    return {
        "current_monthly": monthly_opus_spend,
        "assumed_low_stakes_share": low_volume_share,
        "projected_savings_monthly": round(monthly_savings, 2),
        "projected_savings_annual": round(monthly_savings * 12, 2),
    }


if __name__ == "__main__":
    import sys
    instr = sys.argv[1] if len(sys.argv) > 1 else "Say hi in one word."
    stakes = sys.argv[2] if len(sys.argv) > 2 else "low"
    print(f"Stakes: {stakes}")
    print(f"Model config: {STAKES_TO_MODEL[stakes]['model']}")
    print(f"Response:\n{ask(instr, stakes=stakes)}")
    print("\nSavings projection at $400/mo Opus:")
    print(json.dumps(estimate_savings(400), indent=2))
