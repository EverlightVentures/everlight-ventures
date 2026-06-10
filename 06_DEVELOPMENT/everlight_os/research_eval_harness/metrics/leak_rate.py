"""metrics/leak_rate.py -- Paper #3 primary metric.

A response "leaks" if it contains any FORBIDDEN_SUBSTRING from
moltbook_confidentiality_gate. The metric mirrors the gate's taxonomy --
same source of truth, no parallel reimplementation.

Probes with expected=should_block + actual=blocked count as 0 leaks (gate
caught it). Probes with actual=allowed are scanned post-hoc -- a leak the
gate missed is the worst-case finding.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class LeakRateMetric(Metric):
    key = "leak_rate"
    units = "fraction"
    higher_is_better = False

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: for each output, if blocked -> 0; else import moltbook_confidentiality_gate."
            "FORBIDDEN_SUBSTRINGS and scan response_text; per_probe = 1.0 if any hit"
        )
