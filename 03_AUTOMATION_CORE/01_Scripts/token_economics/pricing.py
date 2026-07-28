"""Token Economics OS - canonical model pricing (per 1M tokens, USD).

Single source of truth for token cost. Rates verified 2026-06-25 against the
Anthropic pricing reference. Includes prompt-cache multipliers because for an
Opus-heavy agent shop, cache reads/writes dominate the real bill.

NOTE: the older content_tools/swarm_budget.py table is STALE (it prices
opus-4-7 at $15/$75 and haiku-4-5 at $0.80/$4). Use THIS module going forward;
swarm_budget should import from here in a follow-up.
"""
from __future__ import annotations

# model -> (input_per_million_usd, output_per_million_usd)
PRICING = {
    "claude-fable-5": (10.0, 50.0),
    "claude-mythos-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-5": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # non-Anthropic, best-effort estimates for mixed-provider tracking
    "gpt-4o": (5.0, 15.0),
    "gpt-4o-mini": (0.15, 0.60),
    "llama-3.1-8b-free": (0.0, 0.0),
}

# Unknown models default to Opus 4.8 rates so we never UNDER-count COGS.
_DEFAULT = (5.0, 25.0)

# prompt-cache multipliers applied to the INPUT rate
_CACHE_READ_MULT = 0.10
_CACHE_WRITE_MULT = 1.25


def rate(model: str) -> tuple[float, float]:
    return PRICING.get(model, _DEFAULT)


def cost_usd(model: str, input_tokens: int, output_tokens: int,
             cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> float:
    """Dollar cost of one model call. Cache read/write priced off the input rate."""
    in_rate, out_rate = rate(model)
    total = (
        input_tokens * in_rate
        + output_tokens * out_rate
        + cache_read_tokens * in_rate * _CACHE_READ_MULT
        + cache_write_tokens * in_rate * _CACHE_WRITE_MULT
    )
    return total / 1_000_000.0
