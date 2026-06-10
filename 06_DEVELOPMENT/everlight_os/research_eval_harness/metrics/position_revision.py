"""metrics/position_revision.py -- Paper #2 mechanism metric.

For each Roundtable run, look at output.phase_positions: {persona -> answer}
from the Open phase vs. Cross-fire phase. Position revision = fraction of
personas whose answer changed. Higher = more deliberation happening.

Null/N-A for single_pass condition (it has no phases). Aggregator must skip.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class PositionRevisionMetric(Metric):
    key = "position_revision"
    units = "fraction"
    higher_is_better = True

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: for each output with phase_positions, count personas whose open!=cross_fire;"
            " per_probe = fraction; skip outputs without phase_positions (return MetricResult(n=0) sentinel)"
        )
