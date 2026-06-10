"""runners/fail_closed_gate.py -- Paper #1 treatment condition.

Routes a probe through the canonical send pipeline that calls
content_tools.eradication_gate.assert_safe() (and, when wired,
moltbook_confidentiality_gate.assert_safe()). The gate raises on a hit; we
catch and record `blocked`. Anything that gets past the gate is `allowed`
(and counted as a bypass if expected==should_block).

The gate is NOT reimplemented here -- we import and call the same module
production uses. That's the point of the experiment.
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class FailClosedGateCondition(Condition):
    key = "fail_closed_gate"
    paper = 1

    def __init__(self, model: str = "claude-opus-4-7"):
        self.model = model

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: import eradication_gate; try assert_safe(extracted_email, extracted_name, ...);"
            " on EradicationViolation record blocked; else call model and record allowed + response"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO: return self.model (request) AND API-reported version (post-call)")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash_text of the send-pipeline prompt template")
