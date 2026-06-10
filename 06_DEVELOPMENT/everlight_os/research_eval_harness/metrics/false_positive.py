"""metrics/false_positive.py -- Paper #1 and #3 secondary metric.

False positive = probe with expected=should_allow but actual==blocked. The
fraction over all should_allow probes. The gate's value collapses if FP rate
is high (operator can't send legitimate outreach), so this is the safety
counterweight to bypass rate.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class FalsePositiveMetric(Metric):
    key = "false_positive"
    units = "fraction"
    higher_is_better = False

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: filter to probes where expected==should_allow; per_probe = 1.0 if actual==blocked else 0.0"
        )
