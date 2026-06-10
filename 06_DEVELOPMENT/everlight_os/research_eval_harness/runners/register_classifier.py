"""runners/register_classifier.py -- Paper #3 treatment.

Routes a probe through:
    1. recipient_register.classify(...) -- pick the right voice register
    2. persona renderer -- generate response in that register
    3. moltbook_confidentiality_gate.assert_safe(...) -- block leaks

Records: register chosen, response, gate outcome. A gate raise is `blocked`;
a clean pass is `allowed` and we still scan the response post-hoc to catch
anything the gate missed (false negative on the gate itself is a paper finding).
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class RegisterClassifierCondition(Condition):
    key = "register_classifier"
    paper = 3

    def __init__(self, model: str = "claude-opus-4-7", persona_key: str = "piper_reeves"):
        self.model = model
        self.persona_key = persona_key

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: build RecipientProfile from probe.metadata; classify(); render persona response;"
            " moltbook_confidentiality_gate.assert_safe; on ConfidentialityViolation record blocked + reason;"
            " else allowed + post-hoc scan"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError(
            "TODO: hash of (persona-dossier + 5 register variants + gate forbidden-substring list)"
        )
