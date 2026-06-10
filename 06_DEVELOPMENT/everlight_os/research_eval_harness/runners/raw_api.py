"""runners/raw_api.py -- Paper #1 no-defense control.

Calls the model directly with no system prompt and no gate. Establishes the
ceiling for how often the unguarded model would draft a forbidden send.
Useful for showing soft-prompt's marginal improvement is small.
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class RawAPICondition(Condition):
    key = "raw_api"
    paper = 1

    def __init__(self, model: str = "claude-opus-4-7"):
        self.model = model

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError("TODO: bare Anthropic call, no system prompt, no gate; classify response")

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash of the (empty) template -- well-known constant")
