"""probes/held_out.py -- Paper #2 TruthfulQA / MATH-adversarial loader.

Wraps a held-out reasoning eval. Each example is `(question, gold_answer)`;
runners produce an answer, metrics compute accuracy. Roundtable treatment
additionally records per-persona positions across phases for
position-revision metric.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from .base import ProbeExample, ProbeFamily

HeldOutSource = Literal["truthful_qa", "math_adversarial"]


class HeldOutProbes(ProbeFamily):
    key = "held_out"
    n_default = 50

    def __init__(self, source: HeldOutSource, dataset_dir: Optional[Path] = None):
        self.source = source
        self.dataset_dir = dataset_dir

    def load(self, n: Optional[int] = None, seed: int = 0) -> list[ProbeExample]:
        raise NotImplementedError("TODO: HF load_dataset OR local mirror per Rich's call (SPEC Q1)")

    def dataset_hash(self) -> str:
        raise NotImplementedError("TODO: sha256 of (source, split, index order)")
