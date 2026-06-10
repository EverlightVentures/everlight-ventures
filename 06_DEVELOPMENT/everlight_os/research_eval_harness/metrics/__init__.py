"""metrics -- pluggable scorers.

Each Metric consumes (probes, outputs) and emits a MetricResult with point
estimate + per-probe values for downstream bootstrap CIs in aggregator.py.
"""
from .base import Metric, MetricResult

__all__ = ["Metric", "MetricResult"]
