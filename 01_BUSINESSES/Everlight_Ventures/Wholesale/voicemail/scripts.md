# Voicemail Scripts -- Privacy-Law-Aware

**Owner:** Piper Reeves (recording + delivery). Hammer Ortiz (warm callbacks).
**Engine:** All scripts route through `outreach/merge_field_gate.py`. No raw text sends.
**Plan reference:** v3 Move G + Dispatch #7.
**Privacy enforcement:** TCPA, FCC 23-107, CAN-SPAM-equivalent voice rules, Fair Housing Act, HIPAA, FCRA, state-level (TX SB 140, FL HB 1383 pending, CA, NC closed).

---

## How merge-field gate decides what fills `{...}`

For each template variable, the gate checks:

1. **Field is on the WHITELIST** (public-records-only data: street, city, list_price, days_on_market, year_built, sqft, motivation_tag, agent_*, company, first_name on warm only).
2. **Field is allowed for THIS channel** (cold voicemail has different scope than warm callback).
3. **State gate is clear** (GA call_cold_allowed = true, NC call_cold_allowed = false post-HB-797, etc.).
4. **Field has a value in the PropertyLead** (skips gracefully if missing).
5. **Final PII scan** catches accidental phone-shaped / SSN-shaped / DOB-shaped text in free-form fields that got merged.

If ANY check fails, the field is replaced with `[BLOCKED]` or `[CHANNEL-BLOCKED]` or empty string, and the audit log records what was blocked and why.

If the template contains a BLACKLISTED field (credit_score, debt_amount, race, household_size, etc.), the gate throws a hard ValueError and refuses to render. We fail loud so a developer who writes `{credit_score}` into a script hears an alarm, not a quiet substitution.

---

## Cold seller intro (12 sec, ringless drop via Slybroadcast)

**Channel:** `voicemail_cold`. State gate: must have `call_cold_allowed: true` for the lead's state.
**Allowed merge fields on this channel:** `street`, `city`, `state`, `agent_first_name`, `agent_callback`, `company`. Note: `first_name` (the OWNER'S first name) is **NOT** allowed cold -- it would only come from skip-trace and reading it back signals research the owner did not consent to.

```
Hey there. {agent_first_name} at {company}.
Calling about {street} in {city}. I buy houses for cash, no agent.
Give me a holler back at {agent_callback}. Take care.
```

**Realistic render** (Atlanta lead):

> Hey there. Piper at Everlight Ventures.
> Calling about 123 Main Street in Atlanta. I buy houses for cash, no agent.
> Give me a holler back at 707-801-0360. Take care.

**Length check:** ~12 seconds at Piper's natural Nashville cadence.
**Drop conditions:** outbound call rings >=4 times unanswered; auto-trigger Slybroadcast drop; log to `PropertyLead.last_vm_dropped` + Slack #wholesale-deals.

---

## Warm callback (8 sec, when the seller called us first)

**Channel:** `voicemail_warm`. State gate: warm channel is universally allowed (we're returning a contact they initiated).
**Allowed merge fields (expanded vs cold):** all cold fields PLUS `first_name` (owner's first name from caller-ID match), `list_price` (if they referenced it).

```
Hey {first_name}, {agent_first_name} at {company} returning your call about {street}. Catch me at {agent_callback}. Talk soon.
```

**Realistic render** (warm callback):

> Hey John, Piper at Everlight Ventures returning your call about 123 Main Street. Catch me at 707-801-0360. Talk soon.

**Length check:** ~8 seconds.
**Trigger:** Inbound call to Piper's line goes to VM, auto-fires this script with caller-ID lookup matched to PropertyLead.

---

## Live-pickup cold opener (when they answer)

**Channel:** `call_cold` (live, not VM). Same merge whitelist as cold VM.
**Goal:** establish consent + interest in <30 sec, otherwise drop politely.

```
Hi, {agent_first_name} at {company}. I work with cash buyers in {city}.
Real quick -- are you the owner of {street}, and would a no-fee cash offer be useful right now?
```

**Branch tree:**

- **Yes, owner, interested** -> warm transfer to Hammer if available, else schedule callback within 24 hr.
- **Yes, owner, not interested** -> "Totally fair. Mind if I send a one-page offer summary just in case?" -- consent for follow-up email. Log consent in `PropertyLead.email_consent`.
- **Yes, owner, do not call** -> "Got it, I'll mark you off." Update `PropertyLead.dnc_phone = true` immediately (TCPA enforcement). Log to ConsentLedger.
- **No, not the owner** -> "Apologies for the misdial. Have a good one." End. Update lead with note: caller-ID mismatch.
- **Voicemail picks up** -> drop the cold VM script above.

---

## State-specific overrides

The merge-field gate cross-references `state_gates.json` per call. Examples:

- **NC**: `call_cold_allowed: false` (HB 797). Gate returns empty string. **No call placed.**
- **CA**: `call_cold_allowed: true` BUT `pre_foreclosure_solicit_allowed: false` (CC 2945). If `PropertyLead.pre_foreclosure: true`, gate blocks with reason `state-CA-pre_foreclosure_solicit_allowed-false`.
- **TX**: `sms_cold_allowed: false` (SB 140 + bond not posted). VM is `call`-class so allowed; SMS would block.
- **GA**: All cold channels green for non-pre-foreclosure leads.
- **FL**: Watch HB 1383 weekly (Cipher dispatch #23). If passes, fall back to NC posture.

---

## Audit trail

Every render writes one line to `_logs/outreach/merge_audit.jsonl`:

```json
{
  "timestamp_pt": "2026-04-28T08:47:23-07:00",
  "lead_id": "lead-atl-002",
  "channel": "voicemail_cold",
  "state": "GA",
  "template_hash": "a3f9c2e1b8d4...",
  "fields_used": ["agent_first_name", "company", "street", "city", "agent_callback"],
  "fields_blocked": [],
  "state_gate_clear": true,
  "state_gate_reason": "clear",
  "rendered_length": 168,
  "privacy_law_flags": []
}
```

If TCPA / FCRA / Fair Housing enforcement asks "what data did you read to this person," the JSONL is our defense. **Append-only, retained per HIPAA standard 7 years even though we are not a covered entity** -- because regulated SMB consulting clients (Move D) will require similar logging and the same engine ships there.

---

## What the BOTS add to the script (per Marquise direction)

The script is the **template + privacy gate**. The agent (Piper or Hammer) adds judgment at the merge boundary:

- Tone calibration: Piper's "y'all" lands warmer in TN/GA than NJ/NY. Engine doesn't enforce dialect; agent does.
- Motivation tag interpretation: a `tax-delinq-public` tag in the lead means Piper should be MORE empathetic, not more aggressive. Engine merges the tag; agent decides how to talk to it.
- State law nuance: the engine blocks a clearly closed channel, but the AGENT also re-checks the call hours window (state_gates.json has per-state call-hour buffers). 9 AM PT in CA is 6 AM CA-time -- below 8 AM call-hours floor, agent should not place call even though channel is "open."
- Inflection on the second sentence ("I buy houses for cash, no agent") -- delivered as statement, not pitch. The script is the words; the agent is the voice.

The merge-field gate is the **floor**, not the **ceiling**. Privacy law gets enforced. Quality of contact is human judgment.
