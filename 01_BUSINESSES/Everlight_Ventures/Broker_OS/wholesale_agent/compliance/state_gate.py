"""State compliance gate. Reads state_gates.json and returns typed decisions.

Every outreach script must call `check(state, channel, action)` before sending.
Gate returns ok=False with a clear reason when the action is blocked, and a
list of required_disclosures when the action is allowed but gated.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from functools import lru_cache
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger("state_gate")

STATE_GATES_PATH = Path(__file__).resolve().parents[3] / "Wholesale" / "compliance" / "state_gates.json"

# Safety buffers: meet AND exceed the legal bar. Shift windows inward so we're
# never at the edge of a statute. If regulators or plaintiffs ever audit, every
# send logs within the legal bound with room to spare.
SAFETY_BUFFER_MINUTES = 60         # narrow call windows by this much on each end
DNC_SCRUB_DAYS_LEGAL = 31          # federal rule
DNC_SCRUB_DAYS_POLICY = 14         # our ops policy: scrub more than twice as often
OPTOUT_PROCESSING_LEGAL_DAYS = 10  # CAN-SPAM rule
OPTOUT_PROCESSING_POLICY_HOURS = 24  # our policy: within 24 hours


@dataclass
class StateGateDecision:
    ok: bool
    state: str
    channel: str
    action: str
    blocked_reason: str = ""
    required_disclosures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    risk_rating: str = ""


@lru_cache(maxsize=1)
def _load_gates() -> dict:
    if not STATE_GATES_PATH.exists():
        log.error("state_gates.json not found at %s", STATE_GATES_PATH)
        return {}
    try:
        return json.loads(STATE_GATES_PATH.read_text())
    except json.JSONDecodeError as exc:
        log.error("state_gates.json malformed: %s", exc)
        return {}


def reload_gates() -> None:
    """Force-reload after Justine updates the JSON."""
    _load_gates.cache_clear()


def check(state: str, channel: str, action: str = "outreach",
          lead_type: str = "seller") -> StateGateDecision:
    """Return whether `action` is allowed in `state` over `channel`.

    Args:
        state:     two-letter state code (e.g. "TX")
        channel:   "sms" | "call" | "email" | "contract"
        action:    "outreach" | "preforeclosure" | "assignment" | "recording"
        lead_type: "seller" | "homeowner" | "homeowner_distress" | "b2b_vendor"
                   B2B vendor outreach (title companies, lenders, attorneys,
                   contractors, JV wholesalers) follows the b2b_vendor_outreach_default
                   block at the top of state_gates.json and skips per-state
                   consumer-cadence rules. Per Justine Park, 2026-04-26 carve-out.
    """
    state = (state or "").strip().upper()
    channel = (channel or "").strip().lower()
    action = (action or "outreach").strip().lower()
    lead_type = (lead_type or "seller").strip().lower()

    gates = _load_gates()

    # B2B vendor early-return. Lead-type is checked FIRST per the gate-logic
    # precedence Justine added to _meta.gate_logic_precedence in state_gates.json.
    # B2B outreach (vendor onboarding, JV partner intros, MOU letters) does not
    # fall under consumer-protection statutes and skips the per-state cadence.
    if lead_type == "b2b_vendor":
        b2b_default = gates.get("b2b_vendor_outreach_default") or {}
        # Per-state override: a state can BLOCK b2b explicitly via
        # b2b_vendor_outreach_allowed: false. Default is allowed.
        per_state = gates.get(state) or {}
        if per_state.get("b2b_vendor_outreach_allowed", True) is False:
            return StateGateDecision(
                ok=False, state=state, channel=channel, action=action,
                blocked_reason=f"b2b_vendor_outreach explicitly blocked in {state}",
            )
        # Channel-level checks within the b2b lane.
        warnings = []
        required_disclosures = []
        if channel == "email":
            required_disclosures.append("CAN_SPAM_FOOTER")
        elif channel == "call":
            # B2B cold calls are permitted but still require federal DNC scrub
            # under TCPA business-to-business exceptions and no autonomous bot
            # call dialing.
            if b2b_default.get("autonomous_bot_calls_allowed") is False:
                warnings.append("autonomous_bot_calls_blocked_b2b")
            required_disclosures.append("FEDERAL_DNC_SCRUB_31D")
        elif channel == "sms":
            # B2B SMS to a published business number is permitted; to a
            # personal cell is risky. Caller's responsibility to verify.
            warnings.append("verify_recipient_is_business_line_not_personal_cell")
        return StateGateDecision(
            ok=True, state=state, channel=channel, action=action,
            warnings=warnings,
            required_disclosures=required_disclosures,
            risk_rating="low_b2b_default",
        )

    gate = gates.get(state)

    if not gate:
        return StateGateDecision(
            ok=False, state=state, channel=channel, action=action,
            blocked_reason=f"no_gate_for_state:{state}. Add to state_gates.json before operating.",
        )

    if not gate.get("active_in_pipeline", False):
        return StateGateDecision(
            ok=False, state=state, channel=channel, action=action,
            blocked_reason=gate.get("blocked_reason", f"{state} not active in pipeline"),
            risk_rating=gate.get("risk_rating", ""),
        )

    # Action-level gates come first: a blocked action overrides channel rules.
    if action == "preforeclosure" and not gate.get("preforeclosure_outreach_allowed", False):
        return StateGateDecision(
            ok=False, state=state, channel=channel, action=action,
            blocked_reason=gate.get("preforeclosure_blocked_reason", f"{state} pre-foreclosure blocked"),
            risk_rating=gate.get("risk_rating", ""),
        )

    # Channel-level gates.
    warnings = []
    required_disclosures = []

    if channel == "sms":
        if not gate.get("sms_allowed", False):
            return StateGateDecision(
                ok=False, state=state, channel=channel, action=action,
                blocked_reason=gate.get("sms_blocked_reason", f"SMS not allowed in {state}"),
                risk_rating=gate.get("risk_rating", ""),
            )
        required_disclosures.extend(gate.get("sms_conditions", []))
        sms_note = gate.get("sms_risk_note")
        if sms_note:
            warnings.append(sms_note)

    elif channel == "call":
        if not gate.get("cold_call_allowed", False):
            return StateGateDecision(
                ok=False, state=state, channel=channel, action=action,
                blocked_reason=f"cold calling not allowed in {state}",
                risk_rating=gate.get("risk_rating", ""),
            )
        required_disclosures.extend(gate.get("cold_call_conditions", []))
        if gate.get("recording_disclosure_required"):
            required_disclosures.append(
                f"RECORDING_DISCLOSURE:{gate.get('recording_disclosure_text', 'This call may be recorded.')}"
            )

    elif channel == "email":
        required_disclosures.append("CAN_SPAM_FOOTER")

    elif channel == "contract":
        seller_disclosure = gate.get("required_seller_disclosure")
        buyer_disclosure = gate.get("required_buyer_disclosure")
        if seller_disclosure:
            required_disclosures.append(f"SELLER:{seller_disclosure}")
        if buyer_disclosure:
            required_disclosures.append(f"BUYER:{buyer_disclosure}")
        if gate.get("hb2747_required"):
            required_disclosures.append("AZ_HB2747")
        if gate.get("sb1577_required"):
            required_disclosures.append("TX_SB1577")
        if gate.get("sb909_required"):
            required_disclosures.append("TN_SB909_3DAY_NOTICE")

    return StateGateDecision(
        ok=True, state=state, channel=channel, action=action,
        required_disclosures=sorted(set(required_disclosures)),
        warnings=warnings,
        risk_rating=gate.get("risk_rating", ""),
    )


def preferred_closer_id(state: str) -> Optional[str]:
    """Return the preferred title company / closing attorney ID for a state."""
    gate = _load_gates().get((state or "").upper())
    if not gate:
        return None
    return gate.get("preferred_closer_id")


def active_states() -> list:
    """List of state codes currently active in the pipeline."""
    return sorted(
        code for code, gate in _load_gates().items()
        if not code.startswith("_") and gate.get("active_in_pipeline")
    )


STATE_TIMEZONES = {
    "GA": "America/New_York",
    "FL": "America/New_York",
    "NC": "America/New_York",
    "TN": "America/Chicago",
    "TX": "America/Chicago",
    "MO": "America/Chicago",
    "AZ": "America/Phoenix",
    "CA": "America/Los_Angeles",
}


@dataclass
class CallHourDecision:
    ok: bool
    state: str
    local_time: str
    reason: str = ""


def check_call_hour(state: str, when: Optional[datetime] = None) -> CallHourDecision:
    """Return whether it is legal to place an outbound call to a resident of `state` right now.

    Respects state-specific windows and Sunday bans (FL). Federal TCPA window (8am-9pm
    local) is the default floor; state laws narrow the window further.
    """
    state = (state or "").upper()
    gate = _load_gates().get(state, {})
    tz_name = STATE_TIMEZONES.get(state, "America/Los_Angeles")

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return CallHourDecision(ok=False, state=state, local_time="", reason=f"unknown_tz:{tz_name}")

    now = (when or datetime.now()).astimezone(tz) if when else datetime.now(tz)
    local_str = now.strftime("%Y-%m-%d %H:%M %Z (%a)")

    hours = gate.get("outbound_call_hours_local")
    if not hours:
        # Fall back to federal TCPA: 8am-9pm, all days
        if time(8, 0) <= now.time() < time(21, 0):
            return CallHourDecision(ok=True, state=state, local_time=local_str)
        return CallHourDecision(ok=False, state=state, local_time=local_str,
                                reason="outside_federal_tcpa_window_8am_9pm")

    is_sunday = now.weekday() == 6
    is_saturday = now.weekday() == 5

    if is_sunday and not hours.get("sun_allowed", True):
        return CallHourDecision(ok=False, state=state, local_time=local_str,
                                reason="sunday_calls_banned_in_state")

    if is_sunday:
        start = _parse_time(hours.get("sun_start", "08:00"))
        end = _parse_time(hours.get("sun_end", "21:00"))
    elif is_saturday and hours.get("sat_start"):
        start = _parse_time(hours.get("sat_start"))
        end = _parse_time(hours.get("sat_end"))
    else:
        start = _parse_time(hours.get("mon_sat_start", "08:00"))
        end = _parse_time(hours.get("mon_fri_end", hours.get("mon_sat_end", "21:00")))

    # Apply safety buffer: shift window inward so we never run right up against the statute.
    start_buffered = _add_minutes(start, +SAFETY_BUFFER_MINUTES)
    end_buffered = _add_minutes(end, -SAFETY_BUFFER_MINUTES)

    if start_buffered <= now.time() < end_buffered:
        return CallHourDecision(ok=True, state=state, local_time=local_str)

    return CallHourDecision(
        ok=False, state=state, local_time=local_str,
        reason=f"outside_buffered_window_{start_buffered.strftime('%H:%M')}_{end_buffered.strftime('%H:%M')}_local (legal was {start.strftime('%H:%M')}-{end.strftime('%H:%M')}, buffered {SAFETY_BUFFER_MINUTES}min)",
    )


def is_bot_call_allowed(state: str) -> tuple:
    """Return (allowed, reason). Cold autonomous/AI-voice calls require prior express
    written consent under TCPA. Default to False for every state's cold-call path.
    """
    gate = _load_gates().get((state or "").upper(), {})
    allowed = gate.get("autonomous_bot_call_allowed_cold", False)
    reason = gate.get("autonomous_bot_call_reason", "TCPA: prior express written consent required for autodialed/AI-voice calls.")
    return allowed, reason


def _parse_time(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def _add_minutes(t: time, minutes: int) -> time:
    total = t.hour * 60 + t.minute + minutes
    total = max(0, min(23 * 60 + 59, total))
    return time(total // 60, total % 60)
