"""probes -- pluggable adversarial probe families.

Each probe family loads N examples from a dataset and emits
(prompt, expected_block_flag, metadata) tuples consumed by runners.
"""
from .base import ProbeExample, ProbeFamily

__all__ = ["ProbeExample", "ProbeFamily"]
