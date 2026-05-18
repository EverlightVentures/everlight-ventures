"""
legal_state -- per-state compliance lookup for Everlight Intel Center reports.

Reads the canonical source of truth at:
    01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/state_gates.json

Returns a normalized rules dict ready for the report renderer to display.
Per Operator Truth + per-state-compliance doctrine: NEVER generalize. If the
state isn't covered, return an explicit "consult Justine" status rather than
fabricating defaults.

Public API:
    state_rules_for(state_code: str, lead_type: str = "homeowner") -> dict
    is_hard_blocked(state_code: str, action: str, lead_type: str = "homeowner") -> bool
    list_covered_states() -> list[str]
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

GATES_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/state_gates.json")

# Per-state HARD BLOCKS we know about by statute (for red banners on the report)
KNOWN_HARD_BLOCKS = {
    # Justine 2026-05-12 audit: TX SB 140 eff. 2025-09-01 (NOT 2023)
    "TX": [
        {"action": "cold_sms_to_consumer",
         "statute": "TX SB 140 (eff. 2025-09-01)",
         "summary": "Texas bans cold SMS to consumers without prior business relationship"},
        {"action": "equitable_interest_disclosure",
         "statute": "TX SB 1577",
         "summary": "Wholesalers must disclose equitable-interest assignment, not direct property sale"},
    ],
    "CA": [
        {"action": "preforeclosure_cold_outreach",
         "statute": "Cal. Civ. Code §2945",
         "summary": "California foreclosure-consultant ban + 5-day rescission window"},
        {"action": "home_equity_sale_cold",
         "statute": "Cal. Civ. Code §1695",
         "summary": "California home equity sales of pre-foreclosure property: 5-day rescission required"},
    ],
    # Justine 2026-05-12 audit: NC HB 797 eff. 2025-10-01 (NOT 2024)
    "NC": [{
        "action": "wholesale_unlicensed",
        "statute": "NC HB 797 (eff. 2025-10-01)",
        "summary": "North Carolina effectively bans wholesale RE without a real estate license",
    }],
    "FL": [
        {"action": "cold_sms_telemarketing",
         "statute": "FTSA -- Fla. Stat. §501.059",
         "summary": "Florida Telephone Solicitation Act: prior express written consent for cold marketing SMS"},
        {"action": "equity_skimming",
         "statute": "Fla. Stat. §501.1377",
         "summary": "Florida equity skimming statute applies to distressed-homeowner transactions"},
    ],
    # Justine 2026-05-12 audit: HB 2537 was a marriage-officiants bill. Correct cites below.
    "TN": [
        {"action": "cold_call_unregistered",
         "statute": "TN TSA -- Tenn. Code Ann. §47-18-2002",
         "summary": "Tennessee Telephone Solicitation Act: cold-call/SMS requires solicitor registration"},
        {"action": "wholesaler_disclosure",
         "statute": "TN SB 909 / Tenn. Code Ann. §66-32-101",
         "summary": "Tennessee wholesaler disclosure requirement on RE assignments"},
    ],
    "MO": [{
        "action": "state_dnc_violation",
        "statute": "Mo. Rev. Stat. §407.1095-§407.1110 (MO No-Call)",
        "summary": "Missouri state DNC scrub required before any cold outbound; covers SMS",
    }],
    "OH": [
        {"action": "preforeclosure_consultant",
         "statute": "Ohio Rev. Code §1349.61",
         "summary": "Ohio foreclosure-rescue/consultant statute restricts pre-foreclosure outreach"},
        {"action": "no_equitable_interest_marketing",
         "statute": "Ohio HB 132",
         "summary": "Ohio bans marketing a property to third parties without equitable interest"},
    ],
    "AZ": [{
        "action": "assignment_intent_disclosure",
        "statute": "A.R.S. §44-5101",
        "summary": "Arizona requires assignment-intent disclosure in wholesale contracts",
    }],
    "IL": [{
        "action": "wholesale_repeat_unlicensed",
        "statute": "IL HB 1535",
        "summary": "Illinois wholesaler licensing required for >1 deal/year (near-NC hard block)",
    }],
}


@lru_cache(maxsize=1)
def _load_gates() -> dict:
    if not GATES_PATH.exists():
        return {}
    try:
        return json.loads(GATES_PATH.read_text())
    except Exception:
        return {}


def list_covered_states() -> list[str]:
    gates = _load_gates()
    return sorted([k for k in gates if k.isupper() and len(k) == 2])


def state_rules_for(state_code: str | None, lead_type: str = "homeowner") -> dict:
    """
    Returns normalized per-state rules:
        {
          "state": "CA",
          "name": "California",
          "covered": True,
          "lead_type": "homeowner",
          "channels_allowed": {"email": True, "sms": True, "call": "consent_required", "mail": True, "autonomous_bot_call": False},
          "channel_conditions": {"sms": [...], "call": [...]},
          "wholesale_legal_status": "legal_unlicensed_but_high_risk",
          "active_restrictions": [{"action":..., "statute":..., "summary":...}, ...],
          "active_in_pipeline": True,
          "active_for_preforeclosure": False,
          "outbound_call_hours_local": {...},
          "recording_disclosure_required": True,
          "recording_disclosure_text": "...",
          "citations": [...],
          "warning": "" | "STATE UNKNOWN -- consult Justine before any contact",
        }
    """
    gates = _load_gates()
    state = (state_code or "").strip().upper()

    if not state or state not in gates:
        return {
            "state": state or "UNKNOWN",
            "name": "Unknown state",
            "covered": False,
            "lead_type": lead_type,
            "channels_allowed": {},
            "channel_conditions": {},
            "wholesale_legal_status": "unknown",
            "active_restrictions": [],
            "warning": "STATE UNKNOWN -- consult Justine before any contact. No outreach permitted.",
            "citations": [],
        }

    g = gates[state]
    # B2B vendor carve-out
    if lead_type == "b2b_vendor":
        b2b = gates.get("b2b_vendor_outreach_default", {})
        per_state_override = g.get("b2b_vendor_outreach_allowed", b2b.get("permitted_in_all_states", True))
        if not per_state_override:
            return {
                "state": state, "name": g.get("name", state),
                "covered": True, "lead_type": lead_type,
                "channels_allowed": {"email": False, "sms": False, "call": False, "mail": False},
                "channel_conditions": {},
                "wholesale_legal_status": g.get("wholesale_legal_status", "unknown"),
                "active_restrictions": [{"action": "b2b_vendor_outreach", "statute": state + " override",
                                          "summary": "B2B vendor outreach explicitly disallowed in this state"}],
                "warning": f"BLOCKED: {state} explicitly disallows B2B vendor outreach.",
                "citations": [],
            }
        return {
            "state": state, "name": g.get("name", state),
            "covered": True, "lead_type": lead_type,
            "channels_allowed": {
                "email": True, "sms": False, "call": True, "mail": True,
                "autonomous_bot_call": False,
            },
            "channel_conditions": {
                "email": b2b.get("can_spam_conditions", []),
                "call": ["business_hours_only", "manual_human_only"],
            },
            "wholesale_legal_status": g.get("wholesale_legal_status", "unknown"),
            "active_restrictions": [],
            "active_in_pipeline": g.get("active_in_pipeline", False),
            "outbound_call_hours_local": b2b.get("call_hours_local"),
            "recording_disclosure_required": b2b.get("recording_disclosure_required", True),
            "recording_disclosure_text": "All B2B calls -- disclose if recording.",
            "citations": [],
            "warning": "",
        }

    # Consumer/homeowner path -- read state's per-channel allowlist
    channels_allowed = {
        "email": True,  # Federal CAN-SPAM applies, but email is permitted broadly
        "sms": bool(g.get("sms_allowed", False)),
        "call": bool(g.get("cold_call_allowed", False)),
        "mail": True,  # No federal/state ban on direct mail in covered states
        "autonomous_bot_call": bool(g.get("autonomous_bot_call_allowed_cold", False)),
    }
    channel_conditions = {
        "email": g.get("email_conditions", ["include_physical_address", "honest_subject", "one_click_unsub"]),
        "sms": g.get("sms_conditions", []),
        "call": g.get("cold_call_conditions", []),
    }

    # Pre-foreclosure: bring in the active_for_preforeclosure flag
    if g.get("active_for_preforeclosure") is False:
        channels_allowed["preforeclosure_outreach"] = False
    elif g.get("active_for_preforeclosure"):
        channels_allowed["preforeclosure_outreach"] = True

    # Hard blocks from KNOWN_HARD_BLOCKS
    restrictions = list(KNOWN_HARD_BLOCKS.get(state, []))

    # Pull citation candidates from state record
    citations = []
    for k in ("preforeclosure_statute", "wholesale_statute", "sms_statute", "telemarketing_statute"):
        v = g.get(k)
        if v: citations.append(v)

    # Build a clear warning string for any HARD BLOCK
    warning = ""
    if restrictions:
        warning = "; ".join(r["statute"] for r in restrictions)

    # Hard blocks override channel allowlists
    for r in restrictions:
        a = r["action"]
        if "sms" in a: channels_allowed["sms"] = False
        if "call" in a: channels_allowed["call"] = False
        if "preforeclosure" in a: channels_allowed["preforeclosure_outreach"] = False
        if "wholesale_unlicensed" in a:
            for ch in channels_allowed: channels_allowed[ch] = False

    return {
        "state": state, "name": g.get("name", state),
        "covered": True, "lead_type": lead_type,
        "channels_allowed": channels_allowed,
        "channel_conditions": channel_conditions,
        "wholesale_legal_status": g.get("wholesale_legal_status", "unknown"),
        "active_restrictions": restrictions,
        "active_in_pipeline": g.get("active_in_pipeline", False),
        "active_for_preforeclosure": g.get("active_for_preforeclosure", None),
        "outbound_call_hours_local": g.get("outbound_call_hours_local"),
        "recording_disclosure_required": g.get("recording_disclosure_required", False),
        "recording_disclosure_text": g.get("recording_disclosure_text", ""),
        "state_dnc_list": g.get("state_dnc_list", False),
        "solicitor_registration_required": g.get("solicitor_registration_required", False),
        "solicitor_bond_usd": g.get("solicitor_bond_usd", 0),
        "citations": citations,
        "warning": warning,
    }


def is_hard_blocked(state_code: str, action: str, lead_type: str = "homeowner") -> bool:
    """
    Quick check: does this action hit a known hard block in this state?
    `action` examples: 'sms', 'call', 'preforeclosure_outreach', 'wholesale_unlicensed'
    """
    rules = state_rules_for(state_code, lead_type)
    if not rules.get("covered"):
        return True  # unknown state -> default to blocked
    if rules["channels_allowed"].get(action) is False:
        return True
    return any(action in r["action"] for r in rules.get("active_restrictions", []))


if __name__ == "__main__":
    import sys
    state = sys.argv[1] if len(sys.argv) > 1 else "CA"
    rules = state_rules_for(state)
    print(json.dumps(rules, indent=2))
