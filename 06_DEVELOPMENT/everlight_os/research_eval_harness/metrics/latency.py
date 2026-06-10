"""metrics/latency.py -- shared metric across all papers.

Per-probe wall-clock in milliseconds. Drawn straight from RunnerOutput.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class LatencyMetric(Metric):
    key = "latency"
    units = "ms"
    higher_is_better = False

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: per_probe = [o.latency_ms for o in outputs]; point_estimate = median (robust to outliers)"
        )
