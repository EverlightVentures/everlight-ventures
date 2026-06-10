"""budget.py -- pre-flight cost gate.

Loads budget.yaml. Pre-flight estimate before any API call. Hard abort if
estimate > cap, override with --force-budget. Hard-abort floor always enforced.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class BudgetExceeded(Exception):
    """Raised when an estimated or actual run cost exceeds cap."""


@dataclass
class BudgetConfig:
    max_usd_per_run: float
    max_usd_per_paper: float
    daily_cap_usd: float
    hard_abort_usd_per_run: float
    model_prices: dict[str, dict[str, float]]


@dataclass
class CostEstimate:
    model: str
    n_calls: int
    avg_input_tokens: int
    avg_output_tokens: int
    estimate_usd: float


def load(path: Path) -> BudgetConfig:
    """Load budget.yaml into a BudgetConfig."""
    raise NotImplementedError("TODO: yaml.safe_load + BudgetConfig(**raw)")


def estimate(
    model: str,
    n_calls: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    cfg: BudgetConfig,
) -> CostEstimate:
    """Compute expected USD spend for a planned batch."""
    raise NotImplementedError("TODO: lookup prices, return CostEstimate")


def assert_within(
    estimate_usd: float,
    cfg: BudgetConfig,
    paper_running_total_usd: float = 0.0,
    day_running_total_usd: float = 0.0,
    force: bool = False,
) -> None:
    """Raise BudgetExceeded if any cap is breached. hard_abort overrides --force."""
    raise NotImplementedError("TODO: check per-run, per-paper, per-day, hard_abort")


def record_actual(run_dir: Path, model: str, input_tokens: int, output_tokens: int, cfg: BudgetConfig) -> float:
    """Append one API call's actual cost to run_dir/cost.jsonl. Return USD for this call."""
    raise NotImplementedError("TODO: append jsonl, return USD")


def total_actual(run_dir: Path) -> float:
    """Sum all entries in run_dir/cost.jsonl."""
    raise NotImplementedError("TODO: sum cost.jsonl")
