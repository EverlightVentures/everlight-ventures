"""probes/jailbreak.py -- Paper #1, DAN-style + role-play + prompt-injection.

Probes try to elicit contact-the-eradicated-subject behavior from a wrapped
send pipeline. Each probe carries `should_block=True` if a Streubel-style
identifier is in the prompt, else `should_allow`.

Default N=500: 200 jailbreak templates x 2 target variations + 100 FP controls.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import ProbeExample, ProbeFamily


class JailbreakProbes(ProbeFamily):
    key = "jailbreak"
    n_default = 500

    def __init__(self, dataset_dir: Optional[Path] = None):
        self.dataset_dir = dataset_dir

    def load(self, n: Optional[int] = None, seed: int = 0) -> list[ProbeExample]:
        raise NotImplementedError("TODO: load datasets/jailbreak.jsonl + seeded shuffle")

    def dataset_hash(self) -> str:
        raise NotImplementedError("TODO: sha256 of datasets/jailbreak.jsonl")
