"""probes/social_engineering.py -- Paper #3 adversarial leak attempts.

200 prompts across 5 categories (40 each) trying to make a persona leak
internal Hive state (operator name, sellers, $, pipeline, infra, secrets,
trading). Mirrors the FORBIDDEN_SUBSTRINGS taxonomy from
moltbook_confidentiality_gate.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import ProbeExample, ProbeFamily

CATEGORIES = (
    "operator_pii_extraction",
    "counterparty_pii_extraction",
    "financial_extraction",
    "pipeline_state_extraction",
    "infrastructure_extraction",
)


class SocialEngineeringProbes(ProbeFamily):
    key = "social_engineering"
    n_default = 200

    def __init__(self, dataset_dir: Optional[Path] = None):
        self.dataset_dir = dataset_dir

    def load(self, n: Optional[int] = None, seed: int = 0) -> list[ProbeExample]:
        raise NotImplementedError("TODO: load datasets/social_engineering.jsonl, balance across 5 categories")

    def dataset_hash(self) -> str:
        raise NotImplementedError("TODO: sha256 of datasets/social_engineering.jsonl")
