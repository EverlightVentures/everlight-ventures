"""runners/roundtable.py -- Paper #2 treatment.

Calls the 5-phase Hive Roundtable engine on each held-out question and
records per-phase persona positions so position_revision metric can score
how much agents updated under cross-fire.

The Roundtable orchestrator is NOT reimplemented -- we import roundtable()
from 06_DEVELOPMENT/everlight_os/hive_mind/roundtable/roundtable.py and let
it do its 5 phases (Open / Cross-fire / Probe / Synthesis / Publish, with
publish=False during eval to skip Slack/Gdoc spam).
"""
from __future__ import annotations

from .base import Condition, RunnerOutput
from ..probes.base import ProbeExample


class RoundtableCondition(Condition):
    key = "roundtable"
    paper = 2

    def __init__(
        self,
        participants: list[str] | None = None,
        process: str = "research_evaluation",
        model: str = "claude-opus-4-7",
    ):
        self.participants = participants or []
        self.process = process
        self.model = model

    def apply(self, probe: ProbeExample) -> RunnerOutput:
        raise NotImplementedError(
            "TODO: import roundtable.roundtable; call with question=probe.prompt, publish=False, mock=False;"
            " extract phase positions, final synthesis answer; compare to gold"
        )

    def model_version(self) -> str:
        raise NotImplementedError("TODO")

    def prompt_template_hash(self) -> str:
        raise NotImplementedError("TODO: hash of the 5 phase-prompt templates concatenated")
