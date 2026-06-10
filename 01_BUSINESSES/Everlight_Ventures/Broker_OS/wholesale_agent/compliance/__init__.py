"""Compliance gate. Every outreach and contract action must call into state_gate.check()
before sending, so state-specific rules are enforced at the code boundary.
"""
