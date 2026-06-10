"""runners/single_pass.py -- Paper #2 baseline.

One Claude completion per question. The control for Roundtable. Measures
single-pass accuracy on the held-out reasoning eval.
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class SinglePassCondition(Condition):
    key = "single_pass"
    paper = 2

    def __init__(self, model: str = "claude-opus-4-7", chain_of_thought: bool = False):
        self.model = model
        self.chain_of_thought = chain_of_thought

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: format probe.prompt as question; one Anthropic call;"
            " parse answer; compare to probe.metadata['gold_answer']; mark answered"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash of question-template + optional CoT instruction")
