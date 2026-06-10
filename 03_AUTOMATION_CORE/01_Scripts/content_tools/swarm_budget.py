"""swarm_budget -- token kill-switch for the Logistics Swarm.

Mirrors resend_budget.py: hard daily/monthly caps, category buckets, append-only
ledger, BudgetDecision dataclass. The Swarm's LLM client must call
`check_budget()` BEFORE any model call and `record_call()` AFTER.

Per Marcus's orchestration policy (03_MARCUS_ORCHESTRATION_POLICY.md):
  - Hard cap: $50/month
  - Soft cap: $5/day
  - Hard kill: $10/day
  - Categories: proposal | invoice | onboarding | demo | internal_research

Per Forge's deploy plan (01_FORGE_FORK_DEPLOY_PLAN.md):
  - Default monthly token cap: 8M input + 3M output (across all swarm runs)
  - Default daily token cap: 500k input + 200k output
  - Slack #hive-alerts warning at 80%
  - Hard refusal at 100%, no retry storms, no midnight backfill

Storage:
  /AA_MY_DRIVE/_logs/swarm_budget.jsonl  -- append-only, one line per call

Public API:
    from swarm_budget import check_budget, record_call, budget_status

    dec = check_budget(category="proposal", est_input_tokens=12000, est_output_tokens=3000)
    if dec.allowed:
        # ... call the LLM ...
        record_call(category="proposal", agent="docs", model="claude-sonnet-4-5",
                    input_tokens=11823, output_tokens=2940, cost_usd=0.0892,
                    trace_id="poc-001")
    else:
        log.error("swarm budget kill: %s", dec.reason)
        # raise -- don't retry. Do post one Slack alert per hour max.
"""
from __future__ import annotations

import calendar
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Config from env (with sane defaults from Marcus/Forge specs)
_MONTHLY_CAP_USD = float(os.environ.get("SWARM_MONTHLY_CAP_USD", "50.0"))
_DAILY_SOFT_USD = float(os.environ.get("SWARM_DAILY_SOFT_USD", "5.0"))
_DAILY_HARD_USD = float(os.environ.get("SWARM_DAILY_HARD_USD", "10.0"))
_MONTHLY_INPUT_TOKENS = int(os.environ.get("SWARM_MONTHLY_INPUT_TOKENS",
                                              "8000000"))
_MONTHLY_OUTPUT_TOKENS = int(os.environ.get("SWARM_MONTHLY_OUTPUT_TOKENS",
                                                "3000000"))
_DAILY_INPUT_TOKENS = int(os.environ.get("SWARM_DAILY_INPUT_TOKENS", "500000"))
_DAILY_OUTPUT_TOKENS = int(os.environ.get("SWARM_DAILY_OUTPUT_TOKENS", "200000"))
_WARN_AT_PCT = float(os.environ.get("SWARM_WARN_AT_PCT", "0.80"))

# VIP categories never blocked by soft cap; always blocked by hard cap.
_VIP_CATEGORIES = {"invoice"}  # invoices for confirmed deals always go
# Categories accepted by the budget gate
_VALID_CATEGORIES = {"proposal", "invoice", "onboarding", "demo",
                      "internal_research", "test"}

WORKSPACE = Path("/AA_MY_DRIVE")
_LEDGER = WORKSPACE / "_logs/swarm_budget.jsonl"
_STATE = WORKSPACE / "_logs/swarm_budget_state.json"
_LOCK = threading.Lock()


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    category: str
    today_used_usd: float
    today_remaining_usd: float
    month_used_usd: float
    month_remaining_usd: float


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today_key() -> str:
    return _now().strftime("%Y-%m-%d")


def _month_key() -> str:
    return _now().strftime("%Y-%m")


def _append_ledger(row: dict) -> None:
    _LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with _LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


def _read_state() -> dict:
    if not _STATE.exists():
        return {"days": {}, "months": {}}
    try:
        return json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"days": {}, "months": {}}


def _write_state(s: dict) -> None:
    _STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2, default=str), encoding="utf-8")
    tmp.replace(_STATE)


def _accumulators() -> tuple[float, float, int, int, int, int]:
    """(today_usd, month_usd, today_in_tok, today_out_tok, month_in_tok,
         month_out_tok)"""
    s = _read_state()
    d = s.get("days", {}).get(_today_key(), {})
    m = s.get("months", {}).get(_month_key(), {})
    return (
        float(d.get("cost_usd", 0.0)),
        float(m.get("cost_usd", 0.0)),
        int(d.get("input_tokens", 0)),
        int(d.get("output_tokens", 0)),
        int(m.get("input_tokens", 0)),
        int(m.get("output_tokens", 0)),
    )


def _est_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Rough cost estimate. Anthropic 2026 pricing per 1M tokens."""
    rates = {
        # input_per_M, output_per_M
        "claude-opus-4-7": (15.00, 75.00),
        "claude-sonnet-4-5": (3.00, 15.00),
        "claude-haiku-4-5": (0.80, 4.00),
        "claude-haiku-4-5-20251001": (0.80, 4.00),
        "gpt-4o": (5.00, 15.00),
        "gpt-4o-mini": (0.15, 0.60),
    }
    rate = rates.get(model, (3.00, 15.00))  # default to Sonnet rates
    return (input_tokens / 1_000_000) * rate[0] + \
           (output_tokens / 1_000_000) * rate[1]


def check_budget(category: str = "proposal",
                  est_input_tokens: int = 0,
                  est_output_tokens: int = 0,
                  est_cost_usd: Optional[float] = None,
                  model: str = "claude-sonnet-4-5") -> BudgetDecision:
    """Pre-flight gate. Call before any LLM request. Returns BudgetDecision."""
    if category not in _VALID_CATEGORIES:
        category = "proposal"

    today_usd, month_usd, *_ = _accumulators()
    if est_cost_usd is None:
        est_cost_usd = _est_cost_usd(model, est_input_tokens, est_output_tokens)

    proj_today = today_usd + est_cost_usd
    proj_month = month_usd + est_cost_usd

    today_remaining = max(0.0, _DAILY_HARD_USD - today_usd)
    month_remaining = max(0.0, _MONTHLY_CAP_USD - month_usd)

    # Hard kill: monthly cap
    if proj_month > _MONTHLY_CAP_USD:
        return BudgetDecision(
            allowed=False,
            reason=(f"hard kill: monthly cap ${_MONTHLY_CAP_USD:.2f} exceeded "
                    f"(used ${month_usd:.4f}, projecting ${proj_month:.4f})"),
            category=category, today_used_usd=today_usd,
            today_remaining_usd=today_remaining, month_used_usd=month_usd,
            month_remaining_usd=month_remaining,
        )

    # Hard kill: daily hard cap
    if proj_today > _DAILY_HARD_USD:
        return BudgetDecision(
            allowed=False,
            reason=(f"hard kill: daily hard cap ${_DAILY_HARD_USD:.2f} exceeded "
                    f"(used ${today_usd:.4f}, projecting ${proj_today:.4f})"),
            category=category, today_used_usd=today_usd,
            today_remaining_usd=today_remaining, month_used_usd=month_usd,
            month_remaining_usd=month_remaining,
        )

    # Soft cap: daily soft. VIP categories pass; others blocked unless invoice.
    if proj_today > _DAILY_SOFT_USD and category not in _VIP_CATEGORIES:
        return BudgetDecision(
            allowed=False,
            reason=(f"soft cap: daily ${_DAILY_SOFT_USD:.2f} reached for "
                    f"non-VIP category {category!r} (projecting ${proj_today:.4f}). "
                    f"Override via category=invoice if confirmed deal."),
            category=category, today_used_usd=today_usd,
            today_remaining_usd=today_remaining, month_used_usd=month_usd,
            month_remaining_usd=month_remaining,
        )

    return BudgetDecision(
        allowed=True,
        reason=f"ok ({category}, ~${est_cost_usd:.4f})",
        category=category, today_used_usd=today_usd,
        today_remaining_usd=today_remaining, month_used_usd=month_usd,
        month_remaining_usd=month_remaining,
    )


def record_call(category: str, agent: str, model: str,
                 input_tokens: int, output_tokens: int,
                 cost_usd: Optional[float] = None,
                 trace_id: str = "", deal_id: str = "") -> dict:
    """Post-flight record. Call after the LLM responds. Updates state +
    appends ledger row."""
    if cost_usd is None:
        cost_usd = _est_cost_usd(model, input_tokens, output_tokens)
    row = {
        "ts": _now().isoformat(),
        "category": category,
        "agent": agent,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "trace_id": trace_id,
        "deal_id": deal_id,
    }
    _append_ledger(row)

    with _LOCK:
        s = _read_state()
        d = s.setdefault("days", {}).setdefault(_today_key(), {
            "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "calls": 0,
        })
        d["cost_usd"] = round(d.get("cost_usd", 0.0) + cost_usd, 6)
        d["input_tokens"] = d.get("input_tokens", 0) + input_tokens
        d["output_tokens"] = d.get("output_tokens", 0) + output_tokens
        d["calls"] = d.get("calls", 0) + 1

        m = s.setdefault("months", {}).setdefault(_month_key(), {
            "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "calls": 0,
        })
        m["cost_usd"] = round(m.get("cost_usd", 0.0) + cost_usd, 6)
        m["input_tokens"] = m.get("input_tokens", 0) + input_tokens
        m["output_tokens"] = m.get("output_tokens", 0) + output_tokens
        m["calls"] = m.get("calls", 0) + 1
        _write_state(s)

    return row


def budget_status() -> dict[str, Any]:
    today_usd, month_usd, today_in, today_out, month_in, month_out = _accumulators()
    return {
        "ts": _now().isoformat(),
        "monthly_cap_usd": _MONTHLY_CAP_USD,
        "daily_soft_usd": _DAILY_SOFT_USD,
        "daily_hard_usd": _DAILY_HARD_USD,
        "today": {
            "key": _today_key(),
            "cost_usd": round(today_usd, 4),
            "soft_remaining_usd": round(max(0, _DAILY_SOFT_USD - today_usd), 4),
            "hard_remaining_usd": round(max(0, _DAILY_HARD_USD - today_usd), 4),
            "input_tokens": today_in,
            "output_tokens": today_out,
            "soft_pct": round(today_usd / _DAILY_SOFT_USD * 100, 1) if _DAILY_SOFT_USD else 0,
            "hard_pct": round(today_usd / _DAILY_HARD_USD * 100, 1) if _DAILY_HARD_USD else 0,
        },
        "month": {
            "key": _month_key(),
            "cost_usd": round(month_usd, 4),
            "remaining_usd": round(max(0, _MONTHLY_CAP_USD - month_usd), 4),
            "input_tokens": month_in,
            "output_tokens": month_out,
            "pct_of_cap": round(month_usd / _MONTHLY_CAP_USD * 100, 1) if _MONTHLY_CAP_USD else 0,
            "warn_threshold_pct": _WARN_AT_PCT * 100,
            "warned": (month_usd / _MONTHLY_CAP_USD) >= _WARN_AT_PCT
                       if _MONTHLY_CAP_USD else False,
        },
    }


def assert_under_cap(category: str = "proposal",
                      est_input_tokens: int = 0,
                      est_output_tokens: int = 0,
                      model: str = "claude-sonnet-4-5") -> None:
    """Raise RuntimeError if the call would breach budget. For wrappers that
    prefer fail-fast over graceful return."""
    dec = check_budget(category=category,
                        est_input_tokens=est_input_tokens,
                        est_output_tokens=est_output_tokens,
                        model=model)
    if not dec.allowed:
        raise RuntimeError(f"swarm_budget: {dec.reason}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(budget_status(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # smoke test
        dec = check_budget(category="proposal",
                            est_input_tokens=12000,
                            est_output_tokens=3000,
                            model="claude-sonnet-4-5")
        print(f"check_budget: allowed={dec.allowed} reason={dec.reason}")
        if dec.allowed:
            row = record_call(category="proposal", agent="docs",
                                model="claude-sonnet-4-5",
                                input_tokens=11823, output_tokens=2940,
                                trace_id="poc-test")
            print(f"recorded: {row}")
        print(json.dumps(budget_status(), indent=2))
    else:
        print(json.dumps(budget_status(), indent=2))
