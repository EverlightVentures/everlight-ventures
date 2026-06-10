"""research_eval_harness -- shared eval scaffolding for the 3-paper bridge portfolio.

One harness, three papers:
    Paper #1: Constitutional Runtime Gates (eradication_gate, confidentiality_gate)
    Paper #2: Roundtable Protocol (multi-agent debate vs. single-pass baselines)
    Paper #3: Voice-Register Confidentiality (5-register classifier vs. vanilla)

Spec: SPEC.md
CLI:  python -m research_eval_harness run --paper N --condition X --seeds K

The harness is deliberately thin -- it owns reproducibility (manifest hashing,
seed control, bootstrap CIs, paired stats) and budget guardrails. Each paper
owns its probes, runners, and paper-specific metrics.
"""
from __future__ import annotations

__version__ = "0.1.0-spec"

PAPERS = (1, 2, 3)

SUPPORTED_CONDITIONS = {
    1: ("fail_closed_gate", "soft_prompt_dnc", "raw_api"),
    2: ("single_pass", "roundtable"),
    3: ("vanilla_persona", "register_classifier"),
}

SUPPORTED_METRICS = {
    1: ("bypass_rate", "false_positive", "latency", "cost"),
    2: ("accuracy_delta", "position_revision", "latency", "cost"),
    3: ("leak_rate", "voice_consistency", "recruiter_experience", "latency", "cost"),
}

__all__ = ["__version__", "PAPERS", "SUPPORTED_CONDITIONS", "SUPPORTED_METRICS"]
