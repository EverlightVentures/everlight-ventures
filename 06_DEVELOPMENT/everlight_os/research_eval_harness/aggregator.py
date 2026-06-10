"""aggregator.py -- bootstrap CIs + paired stats + summary emission.

Consumes one or more (probes, runner_outputs, metric_results) tuples and
produces:
    - bootstrap 95% CIs on each MetricResult
    - paired significance tests across conditions (per-probe pairing)
    - manifest.json with reproducibility info
    - summary.md with the headline table (point estimates + CIs + p-values)
    - branded Google Doc + Slack card via content_tools.n8n_replacements.publish_gdoc

Significance test selection:
    - binary outcome (bypass / leak / correct) + paired -> McNemar's test
    - continuous outcome (latency / cost / voice score) + paired -> paired t-test
    - if scipy not present, fallback to permutation test
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from .metrics.base import MetricResult
from .probes.base import ProbeExample
from .runners.base import RunnerOutput

TestKind = Literal["mcnemar", "paired_t", "permutation"]


@dataclass
class PairedResult:
    """Result of comparing two conditions on the same metric."""

    metric: str
    condition_a: str
    condition_b: str
    delta: float
    test_kind: TestKind
    p_value: float
    n_pairs: int
    note: str = ""


@dataclass
class AggregateReport:
    paper: int
    metrics: list[MetricResult] = field(default_factory=list)
    paired: list[PairedResult] = field(default_factory=list)
    n_seeds: int = 0
    cost_actual_usd: float = 0.0
    cost_estimate_usd: float = 0.0
    summary_md_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    gdoc_url: Optional[str] = None
    slack_ts: Optional[str] = None


def bootstrap_ci(values: list[float], n_resamples: int = 10_000, alpha: float = 0.05) -> tuple[float, float]:
    """Return (low, high) 95% bootstrap CI on the mean of `values`."""
    raise NotImplementedError("TODO: scipy.stats.bootstrap with confidence_level=1-alpha")


def mcnemar(paired_outcomes: list[tuple[int, int]]) -> float:
    """Paired binary test. Input: [(a_i, b_i), ...] both 0/1. Returns p-value."""
    raise NotImplementedError("TODO: scipy.stats.contingency.mcnemar with exact=True when small n")


def paired_t(a: list[float], b: list[float]) -> float:
    """Paired t-test on two same-length numeric arrays. Returns two-sided p-value."""
    raise NotImplementedError("TODO: scipy.stats.ttest_rel")


def permutation_paired(a: list[float], b: list[float], n_perm: int = 10_000) -> float:
    """Fallback paired permutation test when scipy is unavailable."""
    raise NotImplementedError("TODO: random sign-flip on (a-b), count |diff| >= observed")


def aggregate(
    paper: int,
    metric_results_by_condition: dict[str, list[MetricResult]],
    condition_pairs: list[tuple[str, str]],
    out_dir: Path,
    publish: bool = False,
) -> AggregateReport:
    """Bootstrap CIs on every metric, run paired tests on requested pairs,
    write summary.md, optionally publish branded Google Doc + Slack card.
    """
    raise NotImplementedError(
        "TODO: 1) bootstrap CIs into each MetricResult; 2) for each (a,b) pair pick test_kind and run;"
        " 3) write summary.md table; 4) if publish: publish_gdoc + branded_slack; 5) return AggregateReport"
    )


def write_summary_md(report: AggregateReport, path: Path) -> None:
    """Render the headline table as markdown to `path`."""
    raise NotImplementedError("TODO: jinja-free f-string template, one row per metric, paired-test footnotes")
