"""metrics/voice_consistency.py -- Paper #3 secondary metric.

Same persona, different registers, scored by a held-out LLM judge for "does
this still sound like the same person?". Output is a 0-1 score per probe.
Higher = persona identity preserved across registers.

Judge model + version are recorded in the manifest (SPEC §6) because judge
drift kills the longitudinal comparison.
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class VoiceConsistencyMetric(Metric):
    key = "voice_consistency"
    units = "score_0_1"
    higher_is_better = True

    def __init__(self, judge_model: str = "claude-sonnet-4"):
        self.judge_model = judge_model

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: for each output, call judge_model with rubric prompt;"
            " parse 0-1 score; per_probe = score"
        )
