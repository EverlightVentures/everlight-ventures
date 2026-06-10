"""metrics/base.py -- Metric ABC + MetricResult schema.

A Metric scores (probe set, runner outputs) -> MetricResult. The per_probe
field is the array of per-example numerics; aggregator.py bootstraps CIs
from it and pairs across conditions for significance tests.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


@dataclass
class MetricResult:
    """One metric x one (probe set, condition) tuple."""

    metric: str
    condition: str
    point_estimate: float
    n: int
    per_probe: list[float] = field(default_factory=list)
    units: str = ""
    higher_is_better: bool = False
    notes: str = ""
    # Filled in by aggregator after bootstrap.
    ci_low_95: Optional[float] = None
    ci_high_95: Optional[float] = None


class Metric(ABC):
    """Abstract base for all metrics."""

    key: str
    units: str
    higher_is_better: bool

    @abstractmethod
    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        """Compute the metric. probes[i].index must match outputs[i].probe_index."""
