"""Hive Roundtable -- Solomon Vale's 5-phase persona orchestration.

Convenes structured debates among N personas (Hive members + optional ad-hoc
guests), surfaces disagreement, and synthesizes without consensus-bias.

Constitutional guards baked in:
  - eradication_gate.assert_safe() runs on every input
  - hive_logger.start() registers every session as a HiveArtifact
  - publish_gdoc() applies the Everlight gold theme + branded Slack card
  - All inference stays inside the Anthropic API (no third-party AI vendor)

Public API:
    from hive_mind.roundtable import roundtable
    result = roundtable(question="...", participants=["piper_reeves", ...])
"""
from .roundtable import roundtable, RoundtableError

__all__ = ["roundtable", "RoundtableError"]
