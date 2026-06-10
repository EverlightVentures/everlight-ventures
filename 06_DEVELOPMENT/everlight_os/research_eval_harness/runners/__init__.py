"""runners -- pluggable conditions applied to probes.

A Condition takes a ProbeExample and produces a RunnerOutput recording what
the system did (blocked / allowed / answered) and the cost / latency / model.
"""
from .base import Condition, RunnerOutput

__all__ = ["Condition", "RunnerOutput"]
