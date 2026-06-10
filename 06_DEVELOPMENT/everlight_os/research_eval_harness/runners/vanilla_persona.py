"""runners/vanilla_persona.py -- Paper #3 baseline.

Single-shot persona via a stock LLM (default GPT-4o per the paper spec, but
also runnable on Claude for ablation). NO register classifier. NO
confidentiality gate. Tests whether a persona alone resists leak attempts.
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class VanillaPersonaCondition(Condition):
    key = "vanilla_persona"
    paper = 3

    def __init__(self, model: str = "gpt-4o", persona_key: str = "piper_reeves"):
        self.model = model
        self.persona_key = persona_key

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: load persona dossier; build system prompt; call LLM (Anthropic or OpenAI);"
            " scan response for FORBIDDEN_SUBSTRINGS (from moltbook_confidentiality_gate) to detect leak"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash of persona-dossier + system-prompt template")
