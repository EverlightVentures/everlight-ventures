"""
Merge-Field Privacy Gate
========================

Single chokepoint for ALL outbound communication merge-field interpolation.
Enforced before any voicemail script, cold email, SMS, or direct mail piece
goes out. Stops accidental privacy-law violations by whitelisting fields
that came from public records and blacklisting fields that came from
skip-trace, financial pulls, medical info, or other regulated sources.

Per Plan v3 user directive (2026-04-28 Mon AM):
  "the bots need to merge that with client knowledge if that makes sense
   without branching any privacy laws"

Same structural pattern as Charles Dawson's Operator Truth gate -- one
chokepoint, whitelist + blacklist, full audit log.

Privacy laws this gate respects (and the rule each one creates):
  - TCPA (FCC 23-107 1-to-1 consent rule, effective 2025): cold-channel
    consent for autodialed/prerecorded; no merging info that could only
    come from skip-trace into a non-consented call.
  - CAN-SPAM (15 USC 7701): cold email needs opt-out + physical address;
    no false header info.
  - HIPAA (45 CFR 160-164): never merge any field that could be PHI.
  - FCRA (15 USC 1681): no merging credit info or eviction reports
    unless a permissible-purpose exemption + disclosure applies.
  - GLBA (15 USC 6801, 16 CFR 314): no financial info from financial
    institutions in any cold-channel script.
  - State spam laws: TX SB 140, FL HB 1383 (pending), CA, NC HB 797 --
    state_gates.json drives per-state language; this module checks
    the gate before merging.

Usage:
    from outreach.merge_field_gate import MergeFieldGate

    gate = MergeFieldGate()
    rendered, audit = gate.render(
        template="Hey {first_name}, saw {street} in {city}, cash offer ready",
        lead=property_lead,
        channel="voicemail_cold",
        state="GA",
    )
    # rendered = "Hey John, saw 123 Main St in Atlanta, cash offer ready"
    # audit = {
    #   "fields_used": ["first_name", "street", "city"],
    #   "fields_blocked": [],
    #   "channel": "voicemail_cold",
    #   "state": "GA",
    #   "state_gate_clear": True,
    #   "timestamp_pt": "2026-04-28T08:47:23-07:00",
    #   "lead_id": "...",
    # }
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


# --------------------------------------------------------------------
# WHITELIST: only public-record fields can merge into cold-contact text.
# Any field NOT in this dict is blocked, even if PropertyLead has it.
# Each entry maps the merge-key to its (a) source category and (b)
# channel scope. Channels: voicemail_cold, voicemail_warm, email_cold,
# email_warm, sms_cold, sms_warm, direct_mail.
# --------------------------------------------------------------------
WHITELIST: dict[str, dict[str, Any]] = {
    "first_name": {
        "source": "public-name-only",
        "channels": ["voicemail_warm", "email_warm", "sms_warm", "direct_mail"],
        # Cold channels: never use first name (it's from skip-trace if owner is
        # not on a public listing). Direct mail is OK because USPS-addressed.
    },
    "street": {
        "source": "public-mls-or-county",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
    "city": {
        "source": "public-mls-or-county",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
    "state": {
        "source": "public-mls-or-county",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
    "zip": {
        "source": "public-mls-or-county",
        "channels": ["direct_mail"],
        # Cold-channel scripts never read out a zip; direct mail uses it for routing.
    },
    "list_price": {
        "source": "public-mls",
        "channels": ["email_cold", "email_warm", "voicemail_warm", "direct_mail"],
        # Cold voicemail does not state numbers (sounds salesy); cold email may.
    },
    "days_on_market": {
        "source": "public-mls",
        "channels": ["email_cold", "email_warm", "direct_mail"],
    },
    "year_built": {
        "source": "public-county-records",
        "channels": ["email_cold", "email_warm", "direct_mail"],
    },
    "sqft": {
        "source": "public-county-records",
        "channels": ["email_cold", "email_warm", "direct_mail"],
    },
    "motivation_tag": {
        "source": "derived-from-public",
        # Allowed values: 'fsbo', 'price-reduction', 'tax-delinq-public',
        # 'pre-foreclosure-filed', 'vacant-90d', 'code-violation-public'.
        # Each value must come from a public-records lookup, not skip-trace.
        "channels": ["email_cold", "email_warm", "direct_mail"],
        # Voicemail never names motivation tag verbatim (sounds creepy);
        # email may reference it tactfully ("noticed it has been listed for...").
    },
    "agent_first_name": {
        # Caller's first name -- always allowed, hardcoded per agent prompt.
        "source": "internal",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
    "agent_callback": {
        # Caller's callback number -- always allowed.
        "source": "internal",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
    "company": {
        # "Everlight Ventures" -- internal brand string.
        "source": "internal",
        "channels": ["voicemail_cold", "voicemail_warm", "email_cold", "email_warm",
                     "sms_cold", "sms_warm", "direct_mail"],
    },
}


# --------------------------------------------------------------------
# BLACKLIST: fields that exist on PropertyLead but MUST NEVER merge
# into any outbound script under any channel. Maps field name to the
# privacy law it would violate.
# --------------------------------------------------------------------
BLACKLIST: dict[str, str] = {
    "phone": "TCPA + general privacy -- reading owner's number back is creepy and signals skip-trace use",
    "email": "general privacy -- same reasoning",
    "last_name": "skip-trace-derived; reading it back signals research the owner did not consent to",
    "owner_age": "GLBA/general -- never relevant to cash offer; signals skip-trace data pull",
    "race_or_ethnicity": "Fair Housing Act 42 USC 3601 -- never permissible in housing solicitation",
    "marital_status": "Fair Housing -- protected class",
    "household_size": "Fair Housing + general privacy",
    "occupation_specific": "general privacy + Fair Housing if it implies protected class",
    "medical_history": "HIPAA -- never. Even if user volunteers, do not store or merge.",
    "credit_score": "FCRA -- requires permissible purpose + disclosure",
    "debt_amount": "FCRA + FDCPA -- creates UDAAP risk if used in solicitation",
    "income": "GLBA + general privacy",
    "bank_balance": "GLBA + criminal exposure if scraped",
    "ssn_last4": "GLBA + identity theft exposure",
    "eviction_record": "FCRA + Fair Housing -- protected use case",
    "criminal_record": "Fair Housing (HUD 2016 guidance) + state ban-the-box laws",
    "court_filings_unverified": "FCRA -- only filed and recorded matters; never docket-only data",
    "skip_trace_phone_secondary": "TCPA -- never use secondary numbers for cold channel",
    "skip_trace_email_secondary": "general privacy -- never use unverified secondary emails",
    "minor_children_info": "COPPA + Fair Housing -- never",
}


@dataclass
class MergeAudit:
    """Per-call audit record. Stored to disk for compliance retention."""
    timestamp_pt: str
    lead_id: str
    channel: str
    state: str
    template_hash: str
    fields_used: list[str] = field(default_factory=list)
    fields_blocked: list[dict[str, str]] = field(default_factory=list)  # {field, reason}
    state_gate_clear: bool = True
    state_gate_reason: str = ""
    rendered_length: int = 0
    privacy_law_flags: list[str] = field(default_factory=list)


class MergeFieldGate:
    """
    Single chokepoint enforcing privacy-law-aware merge-field interpolation.
    Wrap every outbound communication's text-render through this gate.
    """

    # Audit log path -- append-only, never deleted, used for compliance retention.
    AUDIT_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/outreach/merge_audit.jsonl")

    PT = ZoneInfo("America/Los_Angeles")
    FIELD_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

    def __init__(self, state_gates_path: str | None = None):
        self.state_gates_path = state_gates_path or (
            "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/"
            "Wholesale/compliance/state_gates.json"
        )
        self._state_gates_cache: dict[str, Any] | None = None

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------
    def render(
        self,
        template: str,
        lead: dict[str, Any],
        channel: str,
        state: str,
        agent: dict[str, str] | None = None,
    ) -> tuple[str, MergeAudit]:
        """
        Render a template with privacy-law-enforced merge fields.

        Args:
            template: Text with {field_name} placeholders.
            lead: PropertyLead dict (from Supabase / Django).
            channel: One of voicemail_cold, voicemail_warm, email_cold,
                     email_warm, sms_cold, sms_warm, direct_mail.
            state: USPS state code (GA, TX, FL, ...). Drives state_gates.json check.
            agent: {first_name, callback, company} for the calling agent.
                   Defaults to {Piper, +1-707-801-0360, Everlight Ventures}.

        Returns:
            (rendered_text, MergeAudit)
            If state gate is closed for this channel + state, rendered_text
            is empty string and the audit records the block reason.

        Raises:
            ValueError if template contains a blacklisted field name.
                     We fail loud rather than silently strip -- a developer
                     who tries to use {credit_score} in a script needs to
                     hear an alarm, not a quiet substitution.
        """
        agent = agent or {
            "first_name": "Piper",
            "callback": "+1-707-801-0360",
            "company": "Everlight Ventures",
        }

        audit = MergeAudit(
            timestamp_pt=datetime.now(self.PT).isoformat(timespec="seconds"),
            lead_id=str(lead.get("id", "unknown")),
            channel=channel,
            state=state.upper(),
            template_hash=self._hash(template),
        )

        # 1. Detect blacklisted fields in template -- fail loud BEFORE state gate.
        # Developer-error (using a blacklisted field) must fail regardless of
        # which state the test is running against. Otherwise a dev could write
        # {credit_score} into a script and only discover it when shipping to an
        # open state -- exactly the kind of latent fault we're trying to prevent.
        for field_name in self.FIELD_PATTERN.findall(template):
            if field_name in BLACKLIST:
                raise ValueError(
                    f"Template references blacklisted field {{{field_name}}} "
                    f"(law: {BLACKLIST[field_name]}). Refusing to render. "
                    f"If you need this field for a legitimate channel "
                    f"with consent + disclosure, use a separate code path "
                    f"and document the permissible-purpose basis."
                )

        # 2. State gate check (compliance/state_gates.json) -- block if closed.
        gate_clear, gate_reason = self._check_state_gate(state, channel)
        audit.state_gate_clear = gate_clear
        audit.state_gate_reason = gate_reason
        if not gate_clear:
            self._write_audit(audit)
            return "", audit

        # 3. Render whitelisted fields with channel-scope check.
        rendered = template
        for field_name in self.FIELD_PATTERN.findall(template):
            if field_name not in WHITELIST:
                # Unknown field -- block as conservative default.
                audit.fields_blocked.append({
                    "field": field_name,
                    "reason": "unknown-field-not-on-whitelist",
                })
                rendered = rendered.replace("{" + field_name + "}", "[BLOCKED]")
                continue

            scope = WHITELIST[field_name]
            if channel not in scope["channels"]:
                audit.fields_blocked.append({
                    "field": field_name,
                    "reason": f"field-not-allowed-on-channel-{channel}",
                })
                rendered = rendered.replace("{" + field_name + "}", "[CHANNEL-BLOCKED]")
                continue

            # Pull value from lead or agent dict.
            if field_name.startswith("agent_") or field_name == "company":
                value = agent.get(field_name.replace("agent_", "").replace("company", "company"), "")
                if field_name == "company":
                    value = agent.get("company", "Everlight Ventures")
                elif field_name == "agent_first_name":
                    value = agent.get("first_name", "")
                elif field_name == "agent_callback":
                    value = agent.get("callback", "")
            else:
                value = lead.get(field_name, "")

            if value:
                rendered = rendered.replace("{" + field_name + "}", str(value))
                audit.fields_used.append(field_name)
            else:
                # Missing data -- skip this field gracefully but flag it.
                audit.fields_blocked.append({
                    "field": field_name,
                    "reason": "value-missing-in-lead",
                })
                rendered = rendered.replace("{" + field_name + "}", "")

        audit.rendered_length = len(rendered)

        # 4. Final integrity scan -- catch obvious privacy leaks even if
        # the template + lead structure passed checks (e.g. someone stuffed
        # a phone number in a free-form notes field that got merged).
        # Scrub the agent's own callback before scanning so we don't false-flag
        # the intentional rendering.
        flags = self._scan_for_pii(rendered, agent_callback=agent.get("callback", ""))
        audit.privacy_law_flags = flags

        # 5. Persist audit. Append-only. Used for compliance retention + dispute defense.
        self._write_audit(audit)

        return rendered, audit

    # ----------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------
    def _check_state_gate(self, state: str, channel: str) -> tuple[bool, str]:
        """Read state_gates.json and confirm channel is allowed for state.

        Real key names in the file (verified 2026-04-28):
          - active_in_pipeline: bool, master state-level switch
          - cold_call_allowed: bool, voice cold (also covers ringless VM drops)
          - sms_allowed: bool, single SMS flag (no cold/warm distinction)
          - autonomous_bot_call_allowed_cold: bool, AI-generated-voice rule
            (always false everywhere per TCPA; we never use this channel)
          - preforeclosure_outreach_allowed: bool, pre-foreclosure-specific
            (CA CC 2945/1695 closes this)
          - direct_mail_allowed: not present in file; default true (USPS, no state telemarketing law)

        Channel mapping (with reasoning):
          - voicemail_cold -> cold_call_allowed  (FCC Mar 2024: ringless VM is TCPA-class)
          - voicemail_warm -> active_in_pipeline (returning a contact, no extra gate)
          - email_cold -> active_in_pipeline    (CAN-SPAM is federal; states don't bar cold email broadly)
          - email_warm -> active_in_pipeline
          - sms_cold -> sms_allowed
          - sms_warm -> sms_allowed             (file doesn't differentiate; cold is the harder bar)
          - direct_mail -> active_in_pipeline   (USPS works everywhere active_in_pipeline)
        """
        gates = self._load_state_gates()
        s = state.upper()
        state_block = gates.get(s)
        if not state_block:
            return False, f"state-{s}-not-in-state_gates.json"

        if not state_block.get("active_in_pipeline", False):
            return False, f"state-{s}-active_in_pipeline-false"

        channel_to_gate_key = {
            "voicemail_cold": "cold_call_allowed",
            "voicemail_warm": None,  # warm = no extra gate beyond active_in_pipeline
            "email_cold": None,
            "email_warm": None,
            "sms_cold": "sms_allowed",
            "sms_warm": "sms_allowed",
            "direct_mail": None,
        }

        if channel not in channel_to_gate_key:
            return False, f"unknown-channel-{channel}"

        gate_key = channel_to_gate_key[channel]
        if gate_key is None:
            # Channel needs no extra gate beyond active_in_pipeline.
            return True, "clear"

        allowed = state_block.get(gate_key, False)
        if not allowed:
            return False, f"state-{s}-{gate_key}-false"

        # Pre-foreclosure secondary gate: if lead is pre-foreclosure-tagged,
        # additionally require preforeclosure_outreach_allowed. Caller supplies
        # this via lead['pre_foreclosure'] = True. Checked here lazily.
        # (We don't have lead in this method's signature; caller responsibility.)

        return True, "clear"

    def _load_state_gates(self) -> dict[str, Any]:
        """Load state_gates.json. State data is at top-level (no 'states' wrapper).
        Filters out non-state keys (_meta, b2b_vendor_outreach_default)."""
        if self._state_gates_cache is None:
            try:
                with open(self.state_gates_path, "r") as f:
                    raw = json.load(f)
                # State entries are 2-letter uppercase keys at top level.
                self._state_gates_cache = {
                    k: v for k, v in raw.items()
                    if isinstance(k, str) and len(k) == 2 and k.isupper()
                }
            except FileNotFoundError:
                self._state_gates_cache = {}
        return self._state_gates_cache

    def _scan_for_pii(self, text: str, agent_callback: str = "") -> list[str]:
        """Last-line PII scan. Catches: unexpected phone numbers, SSN-shaped, dollar amounts >$10k, dates of birth.

        agent_callback: if provided, all instances of this number are stripped
        before phone-shape scanning so we don't false-positive on the agent's
        own callback (which is intentionally rendered).
        """
        flags: list[str] = []
        scan_text = text
        if agent_callback:
            # Strip the agent's callback in all common formats so it doesn't trip the scanner.
            digits_only = re.sub(r"\D", "", agent_callback)
            for variant in {agent_callback, digits_only, f"+1-{digits_only[-10:]}",
                            f"+1{digits_only[-10:]}", f"({digits_only[-10:-7]}) {digits_only[-7:-4]}-{digits_only[-4:]}",
                            f"{digits_only[-10:-7]}-{digits_only[-7:-4]}-{digits_only[-4:]}",
                            f"{digits_only[-10:-7]}.{digits_only[-7:-4]}.{digits_only[-4:]}"}:
                if variant:
                    scan_text = scan_text.replace(variant, "")
        if re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", scan_text):
            flags.append("phone-shaped-string-detected")
        if re.search(r"\b\d{3}-\d{2}-\d{4}\b", scan_text):
            flags.append("ssn-shaped-string-detected")
        if re.search(r"\$[1-9]\d{4,}\b", scan_text):  # $10k or higher
            flags.append("large-dollar-amount-detected")
        if re.search(r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(19|20)\d{2}\b", scan_text):
            flags.append("dob-shaped-date-detected")
        return flags

    def _write_audit(self, audit: MergeAudit) -> None:
        self.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(self.AUDIT_LOG, "a") as f:
            f.write(json.dumps(asdict(audit)) + "\n")

    @staticmethod
    def _hash(s: str) -> str:
        import hashlib
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------
# Quick smoke test (run with python3 merge_field_gate.py).
# --------------------------------------------------------------------
if __name__ == "__main__":
    gate = MergeFieldGate()
    sample_lead = {
        "id": "lead-test-001",
        "first_name": "John",
        "street": "123 Main St",
        "city": "Atlanta",
        "state": "GA",
        "list_price": 285000,
        "days_on_market": 92,
        "phone": "+14045551212",  # Held but never merged.
        "credit_score": 612,       # Blacklisted -- gate blocks.
    }

    # 1. Cold voicemail -- should NOT merge first_name (cold-channel rule).
    template_cold_vm = "Hey there, {agent_first_name} at {company}, calling about {street} in {city}. Give me a holler at {agent_callback}."
    rendered, audit = gate.render(template_cold_vm, sample_lead, channel="voicemail_cold", state="GA")
    print("=== COLD VM ===")
    print(rendered)
    print(json.dumps(asdict(audit), indent=2))

    # 2. Cold email -- can use list_price + motivation tag.
    sample_lead["motivation_tag"] = "price-reduction"
    template_cold_email = "Saw {street} listed at {list_price}, {days_on_market} days on market. Cash offer ready, no agent fees."
    rendered, audit = gate.render(template_cold_email, sample_lead, channel="email_cold", state="GA")
    print("\n=== COLD EMAIL ===")
    print(rendered)

    # 3. Try to inject a blacklisted field -- should raise ValueError.
    template_evil = "Hey John, your credit score of {credit_score} caught my eye, let's talk."
    try:
        gate.render(template_evil, sample_lead, channel="email_cold", state="GA")
    except ValueError as e:
        print("\n=== BLACKLIST GATE FIRED ===")
        print(str(e))
