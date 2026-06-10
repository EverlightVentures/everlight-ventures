"""metrics/recruiter_experience.py -- Paper #3 user-facing metric.

Blinded LLM-judge (or human panel per Rich's call -- SPEC Q3) scores whether
the persona's response would make a recruiter want to engage. 1-5 Likert
flattened to 0-1.

Higher = better recruiter experience. The interesting finding is whether
the confidentiality gate degrades this vs. vanilla_persona (we expect ~no
degradation -- that's the paper's pitch).
"""
from __future__ import annotations

from .base import Metric, MetricResult
from ..probes.base import ProbeExample
from ..runners.base import RunnerOutput


class RecruiterExperienceMetric(Metric):
    key = "recruiter_experience"
    units = "likert_0_1"
    higher_is_better = True

    def __init__(self, judge_model: str = "claude-sonnet-4", n_judges: int = 1):
        self.judge_model = judge_model
        self.n_judges = n_judges

    def score(self, probes: list[ProbeExample], outputs: list[RunnerOutput]) -> MetricResult:
        raise NotImplementedError(
            "TODO: blinded Likert prompt; average across n_judges; per_probe = (mean-1)/4"
        )
