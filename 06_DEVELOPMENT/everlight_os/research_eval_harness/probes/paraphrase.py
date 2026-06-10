"""probes/paraphrase.py -- robustness mutator.

Takes a base probe set and emits paraphrased + back-translated variants. Used
to test whether the gate generalizes beyond exact-substring matches.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import ProbeExample, ProbeFamily


class ParaphraseProbes(ProbeFamily):
    key = "paraphrase"
    n_default = 200

    def __init__(self, base_family: ProbeFamily, mutator_model: str = "claude-haiku-4-5"):
        self.base_family = base_family
        self.mutator_model = mutator_model

    def load(self, n: Optional[int] = None, seed: int = 0) -> list[ProbeExample]:
        raise NotImplementedError("TODO: load base + run mutator + return paraphrased")

    def dataset_hash(self) -> str:
        raise NotImplementedError("TODO: sha256(base_hash + mutator_model + seed)")
