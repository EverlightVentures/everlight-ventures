"""metrics/accuracy_delta.py -- Paper #2 primary metric.

Per-question correctness 0/1 against gold answer. Aggregator computes the
PAIRED delta (roundtable_correct - single_pass_correct) per question and
runs paired t-test or McNemar's on the pairs.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class AccuracyDeltaMetric(Metric):
    key = "accuracy_delta"
    units = "fraction"
    higher_is_better = True

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: per_probe = 1.0 if output answer matches probe.metadata['gold_answer'] else 0.0;"
            " return MetricResult(point_estimate=mean(per_probe))"
        )
