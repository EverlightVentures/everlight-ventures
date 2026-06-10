"""runners/base.py -- Condition ABC + RunnerOutput schema.

A Condition wraps a target pipeline (a gate, a baseline, a roundtable) and
applies it to a probe. The output is normalized to a shared schema so all
metrics consume the same shape regardless of paper or condition.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Optional

from ..probes.base import ProbeExample

ActualOutcome = Literal["blocked", "allowed", "answered", "errored"]


@dataclass
class RunnerOutput:
    """One condition x one probe result. Index matches probe.index for pairing."""

    probe_index: int
    condition: str
    actual: ActualOutcome
    response_text: str = ""
    block_reason: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    error: str = ""
    metadata: dict = field(default_factory=dict)
    # Paper #2 only -- per-phase positions for position-revision metric.
    phase_positions: Optional[dict[str, str]] = None


class Condition(ABC):
    """Abstract base for all experimental conditions."""

    key: str
    paper: int

    @abstractmethod
    def apply(self, probe: ProbeExample) -> RunnerOutput:
        """Apply this condition to a single probe. Return normalized output."""

    @abstractmethod
    def model_version(self) -> str:
        """Return the model identifier this condition uses (for manifest)."""

    @abstractmethod
    def prompt_template_hash(self) -> str:
        """Return SHA-256 of the prompt template this condition uses."""

    def warmup(self) -> None:
        """Optional one-time setup (cache personas, load datasets). Default no-op."""
        return None
