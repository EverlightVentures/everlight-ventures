"""probes/base.py -- ProbeFamily ABC + ProbeExample schema.

A probe family is a generator of adversarial test cases. Each ProbeExample is
one prompt + an expected behavior flag (block / allow). Runners apply a
condition to the prompt and metrics compare actual vs. expected.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, Optional

ProbeOutcome = Literal["should_block", "should_allow"]
ProbeFamilyKey = Literal[
    "jailbreak",
    "paraphrase",
    "social_engineering",
    "held_out",
]


@dataclass(frozen=True)
class ProbeExample:
    """One adversarial test case. Index is stable across runs for pairing."""

    index: int
    family: ProbeFamilyKey
    prompt: str
    expected: ProbeOutcome
    category: str = ""
    severity: Literal["low", "medium", "high"] = "medium"
    metadata: dict = field(default_factory=dict)


class ProbeFamily(ABC):
    """Abstract base for all probe generators."""

    key: ProbeFamilyKey
    n_default: int

    @abstractmethod
    def load(self, n: Optional[int] = None, seed: int = 0) -> list[ProbeExample]:
        """Return n probe examples. Deterministic given seed."""

    @abstractmethod
    def dataset_hash(self) -> str:
        """Return SHA-256 of the canonical probe set for this family."""

    def iter(self, n: Optional[int] = None, seed: int = 0) -> Iterator[ProbeExample]:
        """Stream examples one at a time. Default impl: load then yield."""
        for ex in self.load(n=n, seed=seed):
            yield ex
