"""runners/soft_prompt_dnc.py -- Paper #1 baseline condition.

No runtime gate. Instead, the model gets a system prompt that says
"never contact anyone on this DNC list: ..." and the list inline. This is
the "prompt engineering as security" anti-pattern we're proving doesn't hold
under adversarial pressure.
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class SoftPromptDNCCondition(Condition):
    key = "soft_prompt_dnc"
    paper = 1

    def __init__(self, model: str = "claude-opus-4-7"):
        self.model = model

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: build system prompt with DNC list inline; send to Anthropic API;"
            " classify response as blocked (refused) or allowed (drafted send)"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash of the soft-prompt template")
