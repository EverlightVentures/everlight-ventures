"""metrics/cost.py -- shared metric across all papers.

Per-probe USD spend. Multiplies (input_tokens, output_tokens) by the model's
rates from budget.yaml. The Roundtable condition aggregates across all
phase calls per question.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class CostMetric(Metric):
    key = "cost"
    units = "usd"
    higher_is_better = False

    def __init__(self, model_prices: dict[str, dict[str, float]]):
        self.model_prices = model_prices

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: for each output compute (input/1000*input_per_1k + output/1000*output_per_1k);"
            " point_estimate = total USD across all probes"
        )
