# Everlight Wholesale -- State Compliance Matrix

**As of 2026-04-22. Refresh monthly or on any new state bill.**

This is the human-readable companion to `state_gates.json`. The JSON is what the pipeline reads; this file is what Rich and Justine read before approving a campaign.

---

## Master Matrix

| State | Wholesale Legal? | SMS? | Cold Call? | State DNC | Solicitor Reg | Recording | Preforecl OK? | Risk |
|---|---|---|---|---|---|---|---|---|
| **GA** | YES | YES | YES | No | No | 1-party | YES | MED |
| **TX** | YES (SB 1577 disclosure) | **BLOCKED** (SB 140) | YES | YES | YES ($10K bond) | 1-party | YES | HIGH |
| **FL** | YES | YES (manual only) | YES | YES | YES | **ALL-party** | YES | HIGH |
| **MO** | YES | YES | YES | YES (covers SMS) | No | 1-party | YES | MED |
| **AZ** | YES (HB 2747 disclosure) | YES | YES | No | No | 1-party | YES | MED |
| **TN** | YES (HB 2537 disclosure + 3-day notice) | YES | YES | YES ($500/yr) | YES | 1-party | YES | MED-HIGH |
| **NC** | **NO (HB 797)** | n/a | n/a | n/a | n/a | n/a | n/a | **DO NOT OPERATE** |
| **CA** | YES | YES | YES | No | No | **ALL-party** | **NO (CC 2945)** | HIGH |

---

## Per-State Operational Bottom Line

### Georgia (Risk: MED)
Legal unlicensed. No state DNC, no solicitor registration, one-party recording. Attorney-closing state. Market contract rights, never the property itself. Unlicensed brokerage (O.C.G.A. 43-40) is the primary enforcement theory, so marketing copy matters: no MLS, no yard signs, no property photos in cold outreach. SMS and cold call allowed with federal DNC scrub + STOP opt-out.

### Texas (Risk: HIGH)
Legal unlicensed **with mandatory SB 1577 disclosure** (equitable-interest statement to BOTH seller and buyer in every marketing piece). The big new danger is **SB 140 effective 2025-09-01** which extended telephone solicitor registration to cold SMS. Registration costs $200 + $10K bond at TX SoS. Until we register, **SMS to TX numbers is blocked** by the pipeline. Voice and direct mail remain open. TX maintains its own DNC list -- scrub that in addition to federal.

### Florida (Risk: HIGH)
Legal unlicensed. Two live threats: **FTSA (FS 501.059)** which gives a private right of action with $500-$1500 per SMS and **FS 934.03** all-party recording consent with felony exposure for violations. Pipeline rule: FL SMS is manual-click-to-send only (no autodialer pattern), and every FL call opens with the recording disclosure. Florida also has its own state DNC list. Foreclosure-consultant statute (FS 501.1377) applies to pre-foreclosure pitches -- follow the contract template with required disclosures.

### Missouri (Risk: MED)
Legal unlicensed. Missouri runs its own DNC list (RSMo 407.1098) that **covers SMS as well as voice** -- scrub both channels. One-party recording, no solicitor registration. Preferred closer is Investors Title Co STL.

### Arizona (Risk: MED)
Legal unlicensed **with mandatory HB 2747 (A.R.S. 44-5101) disclosure**: the contract must state the buyer is a wholesale buyer with intent to assign, and the seller retains cancellation rights until close if the disclosure is missing. No state DNC, no solicitor registration, one-party recording. SMS and cold call allowed.

### Tennessee (Risk: MED-HIGH)
Legal unlicensed **with mandatory HB 2537 disclosure** (bold-font equitable interest statement to seller AND assignee, plus a 3-business-day notice to seller before assignment executes). TN DNC list applies ($500/yr solicitor registration). One-party recording.

### North Carolina (Risk: DO NOT OPERATE)
As of 2025-10-01, HB 797 requires a NC real estate broker license to wholesale residential property. 30-day non-waivable homeowner cancel window. Class 1 misdemeanor + $1000/violation + NCREC cease-and-desist. Dropped from the L2 starter list. Revisit only if we license a NC broker or partner with one.

### California (Risk: HIGH)
Domicile state. Legal unlicensed in principle, but **pre-foreclosure outreach is blocked** by the pipeline because of CC 2945 (foreclosure consultant) and CC 1695 (equity purchaser): notarized 5-day rescission contracts, Spanish translation if Spanish was spoken, criminal exposure, treble damages. All-party recording state (CIPA Penal Code 632). For non-pre-foreclosure work (teardown, vacant, absentee) CA is workable but treat every call as recorded and every contract as strict-liability.

---

## Top 10 Sue-or-Jail Risks (Ranked)

1. **Cold-texting Texas residents without SOS registration (post 9/1/25).** Mitigation: geo-block TX from SMS blast until registered + bonded.
2. **Pre-foreclosure outreach to California homeowners.** Mitigation: CA NODs excluded from every scout.
3. **FTSA class action in Florida.** Mitigation: FL SMS is manual-click-to-send only, no autodialer pattern; 30-day cure template on standby.
4. **Recording a CA or FL call without disclosure.** Mitigation: every call opens with the recording disclosure.
5. **Unlicensed brokerage charge (any state) for marketing the property vs the contract.** Mitigation: marketing copy says "assignment of contract rights in real property" + no property photos to cold sellers.
6. **Missing TX SB 1577 or TN HB 2537 disclosure.** Mitigation: contract template has hard-coded disclosure boxes and the pipeline refuses to send an assignment without them.
7. **Foreign LLC not registered in the state where we sign a contract.** Mitigation: register Everlight Ventures LLC as foreign entity in FL, TX, GA, MO, AZ, TN before first contract in each.
8. **Federal + state DNC stack violations.** Mitigation: scrub every 31 days against federal + FL + TX + MO + TN lists; maintain internal DNC.
9. **Fair Housing disparate impact from filtering by owner name.** Mitigation: lead filters operate on property characteristics only (equity, NOD status, tax delinquency, vacancy). Never filter by owner name or demographic proxies.
10. **Stating a specific ARV in writing to a seller.** Mitigation: to sellers, use ranges from public comps with a "not an appraisal" disclaimer; save exact ARV numbers for buyer-facing pitches.

---

## Required Disclosures Library

Per-state required-disclosure text lives in `DISCLOSURE_TEMPLATES.md`. Contract generator (`contract_generator.py`) pulls from there.

## Pipeline Enforcement

Every outreach script must call `compliance.state_gate.check(state, channel, action)` before sending. The gate returns a `StateGateDecision` dataclass with `allowed: bool`, `blocked_reason: str`, and `required_disclosures: list[str]`. See `compliance/state_gate.py`.

## Refresh Protocol

Justine Park reviews this matrix on the 1st of each month. If any state passes a new wholesaling or telemarketing bill, she updates both `state_gates.json` and this file, and posts a summary to `#compliance`.
