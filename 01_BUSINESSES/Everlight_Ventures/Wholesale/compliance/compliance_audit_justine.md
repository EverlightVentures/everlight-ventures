# Compliance Audit -- Per-State Compliance Layer (legal_state.py + state_gates.json)

**Auditor:** Justine Ji-Young Park (via Augustine Crane, Compliance Assistant)
**Date:** 2026-05-12
**Scope:** `osint_api/legal_state.py` + `Wholesale/compliance/state_gates.json`
**Verdict:** SHIP-WITH-FIXES. Foundation is sound, but 4 hard-block citation errors and 1 priority coverage gap must be patched before this renders on a single live OSINT report.

Checklist: 14 of 14 items reviewed. 5 advisory notes attached.

---

## 1. Coverage Gap -- Missing High-Value Wholesale States

State_gates.json covers GA, TX, FL, MO, AZ, IN, TN, NC, CA, OH (10). The following wholesale-target states are MISSING and should be added in priority order based on rental yield, judicial-sale velocity, and existing Hive deal flow:

1. **PA (Pennsylvania)** -- HIGH PRIORITY. Pittsburgh + Philly are top-5 cashflow markets, judicial foreclosure state, no wholesaler-specific licensing as of 2026 but Act 6 (Loan Interest Protection Law) attaches to pre-foreclosure outreach. Buyers exist in Hive's Mid South / national networks.
2. **MI (Michigan)** -- HIGH PRIORITY. Detroit + Flint + Grand Rapids active wholesale corridors. PA 173 of 2018 telemarketing rules + state DNC. Recent legislative chatter on assignment disclosure.
3. **IL (Illinois)** -- HIGH PRIORITY. Cook County tax-deed pipeline; HB 1535 (effective 2019) IMPOSES wholesaler licensing for >1 deal/yr -- this is a near-NC hard block and MUST be encoded before any Chicago lead enters.
4. **AL (Alabama)** -- MEDIUM. Birmingham + Mobile cashflow. No wholesaler license required, friendly assignment law.
5. **SC (South Carolina)** -- MEDIUM. Greenville/Charleston momentum, no licensing barrier, attorney-closing state similar to GA.
6. **NJ (New Jersey)** -- MEDIUM. Wholesaler licensing introduced via Senate 1497 (still in committee per last research). High cashflow but high regulatory risk; encode pre-emptively.
7. **OK (Oklahoma)** -- MEDIUM. Tulsa/OKC active.
8. **KY (Kentucky)** -- LOW-MEDIUM. Louisville niche.

**Recommendation:** Add IL FIRST (it is a near-license-required state per HB 1535 and is the highest litigation risk if encountered uncovered). PA + MI second wave.

---

## 2. Hard-Block Statute Accuracy -- 4 Errors Found

| Cited statute (legal_state.py) | Verdict | Correction |
|---|---|---|
| TX SB 140 (cold SMS to consumer) | **PARTIALLY CORRECT.** SB 140 effective 2025-09-01 (per state_gates.json, not 2023). Scope is broader than "cold SMS"; it triggers Texas Secretary of State telephone solicitor registration + $10K bond for cold telephonic solicitation including SMS campaigns. | Update KNOWN_HARD_BLOCKS comment to "TX SB 140 (eff. 2025-09-01) -- requires TX SoS solicitor registration + $10K bond before cold SMS." |
| CA Civ. Code §2945 (foreclosure consultant) | **CORRECT.** Foreclosure consultant ban with 5-day rescission, notarized contracts, Spanish translation if Spanish was the negotiation language. Treble damages + criminal exposure. | No change. |
| CA Civ. Code §1695 (home equity sale rescission) | **CORRECT.** Equity purchaser statute; 5-day rescission; applies when contracting to buy 1-4 unit owner-occupied residential in NOD/NOS status. | No change. |
| NC HB 797 (wholesale RE without license) | **PARTIALLY CORRECT.** Bill number citation is fine but effective date in state_gates.json is 2025-10-01, not 2024 as KNOWN_HARD_BLOCKS implies. Class 1 misdemeanor + $1000/violation + 30-day homeowner cancel. | Update KNOWN_HARD_BLOCKS to "NC HB 797 (eff. 2025-10-01)". |
| FL FTSA / Fla. Stat. §501.059 (cold SMS) | **CORRECT** but Justine should note FTSA was narrowed by HB 761 (2023). Private right of action survives for non-conforming texts; $500-$1500 per violation. State_gates.json captures this in `sms_risk_note`. | No change to citation; add a `narrowed_by` field. |
| TN HB 2537 (Telephone Sales Act) | **WRONG.** Per state_gates.json line 391: "TN HB 2537 -- that's a marriage-officiants bill, unrelated. Cipher correction 2026-04-28." The TN wholesaler statute is **TN SB 909** (signed 2025-03-25, eff. 2025-04-08), Tenn. Code Ann. 66-32-101 et seq. The TN cold-call blocker is **TN TSA 47-18-2002** (Tennessee Solicitation of Charitable Funds Act / Telemarketing Sales Act -- $500/yr registration). | **CRITICAL FIX.** Replace TN HB 2537 entry in KNOWN_HARD_BLOCKS with two entries: (a) `TN TSA 47-18-2002` for cold-call/cold-SMS unregistered telemarketer; (b) `TN SB 909 (Tenn. Code Ann. 66-32-101)` for wholesaler disclosure complexity. Currently the report cites a marriage statute. |
| MO No-Call Law | **TOO VAGUE.** Real cite is **Mo. Rev. Stat. §§407.1095-407.1110** (Missouri No-Call Law, AG-administered). Also note state DNC covers SMS (per state_gates.json line 242 `state_dnc_covers_sms: true`). | Update to "Mo. Rev. Stat. 407.1095-407.1110 -- state DNC covers SMS as well as voice." |

**Hard blocks MISSING that should be in KNOWN_HARD_BLOCKS:**

- **OH ORC 1349.61** (foreclosure rescue, 5-day rescission, criminal penalties) -- pre-foreclosure outreach blocker. Captured in state_gates.json but NOT in KNOWN_HARD_BLOCKS.
- **OH HB 132 (2022)** -- bans marketing property without equitable interest. Not a comms statute but is a hard-block for wholesale practice.
- **TX SB 1577** (equitable interest written disclosure to buyer AND seller) -- not a hard block per se but a per-marketing-piece compliance gate; should surface as a restriction banner.
- **AZ A.R.S. 44-5101** -- contract-must-state-assignment-intent rule; missing from KNOWN_HARD_BLOCKS.
- **FL Fla. Stat. §501.1377** (equity skimming + foreclosure rescue) -- captured in JSON, missing from KNOWN_HARD_BLOCKS.

---

## 3. B2B Carve-Out Logic -- One Latent Bug

Logic flow at lines 117-152 of legal_state.py:

- `b2b = gates.get("b2b_vendor_outreach_default", {})` -- correct.
- `per_state_override = g.get("b2b_vendor_outreach_allowed", b2b.get("permitted_in_all_states", True))` -- correct fallback chain.
- All 10 covered states explicitly set `b2b_vendor_outreach_allowed: true`. No state currently sets it to false. Logic is correct against today's data.

**Latent bug:** when `per_state_override` is true, the returned `channels_allowed` HARD-CODES `sms: False` and `call: True`, ignoring the b2b_vendor_outreach_default's `sms_default: "discouraged_unless_prior_business_relationship"` and `channels_blocked_by_default` (autonomous_bot_call, automated_dialer_voice). The hard-coded TRUE for `call` is fine because manual_human_only is in the conditions, but a future state that sets `b2b_vendor_outreach_allowed: true` WITH a state-specific call restriction (think MA all-party recording for B2B) will be silently overridden. **Recommendation:** read `g.get("b2b_call_allowed", True)` and `g.get("b2b_sms_allowed", False)` instead of hard-coding.

**B2B blocks MISSING:** none of the 10 covered states currently sets `b2b_vendor_outreach_allowed: false`, but **NC** is questionable. NC HB 797 targets residential wholesaling activity; B2B vendor outreach to NC title companies/lenders/attorneys is technically outside HB 797 scope, so leaving B2B open is defensible. However, if Marquise is using B2B outreach to recruit NC JV wholesalers who would then transact in NC, that activity is itself NC-regulated. **Recommendation:** add `b2b_vendor_outreach_allowed: true` to NC explicitly (currently true by default fallback) but add `b2b_jv_wholesaler_outreach_allowed: false` as a sub-key, with a hard block on recruiting NC-resident wholesalers.

---

## 4. Unknown-State Default -- CORRECT, Reinforce It

Returning `warning="STATE UNKNOWN -- consult Justine"`, `channels_allowed={}`, `covered=False`, AND `is_hard_blocked()` returning True for unknown states is the right default. This is fail-closed behavior, which matches Operator Truth Doctrine and the state_gates.json `_meta.principle`: "If a flag is false or missing, the pipeline MUST NOT perform that action in this state."

Soft-warn-but-allow would be unsafe -- TCPA + state telemarketing exposure ranges from $500/text (FL FTSA) to $40K/call (TCPA willful), and we have no way of knowing what statutes a non-covered state has without explicit research. The render layer should display the UNKNOWN warning as a RED banner identical to a hard block.

**Recommendation:** keep the default. Add a downstream gate in `report_renderer.py` that refuses to render outreach CTAs when `covered=False` -- currently the renderer might still draw a "Send email" button. Belt-and-suspenders.

---

## 5. Concrete Recommendations Summary (One Per Critical Issue)

1. **TN citation fix (CRITICAL):** replace `TN HB 2537` in KNOWN_HARD_BLOCKS with `TN TSA 47-18-2002` (cold-call) + `TN SB 909 / Tenn. Code Ann. 66-32-101` (wholesaler disclosure). Current code cites a marriage-officiants bill; this is publicly embarrassing if it ships in a client-facing report.
2. **IL coverage (CRITICAL):** add IL to state_gates.json marked `wholesale_legal_status: license_required` per HB 1535, mirror NC's `active_in_pipeline: false` block. Highest-risk uncovered state.
3. **OH hard blocks missing:** add ORC 1349.61 (pre-foreclosure) + HB 132 (no-marketing-without-equitable-interest) to KNOWN_HARD_BLOCKS["OH"]. Both are in state_gates.json but invisible to the renderer banner logic.
4. **MO citation precision:** update KNOWN_HARD_BLOCKS["MO"] to `Mo. Rev. Stat. 407.1095-407.1110` and note state DNC covers SMS.
5. **B2B logic refactor:** replace hard-coded `sms: False, call: True` in legal_state.py lines 137-138 with reads from per-state b2b_* keys to prevent silent overrides when MA/IL/PA-style B2B carve-outs get added.

---

## Advisory Notes

- **AN-1:** Reload cadence in state_gates.json says "monthly or whenever a state passes new legislation." `_load_gates()` uses `lru_cache(maxsize=1)` -- the cache is process-lifetime, so a state_gates.json edit will NOT refresh until the worker restarts. Add a `_load_gates.cache_clear()` hook on file mtime change, OR document a deploy-restart requirement.
- **AN-2:** TX cold SMS is encoded as a hard block via KNOWN_HARD_BLOCKS, but state_gates.json TX entry sets `sms_allowed: false` explicitly. The override-loop at lines 189-195 will doubly-set `sms: False` -- harmless but redundant. Trust the JSON.
- **AN-3:** The OH `equitable_interest_opinion_status` is "internal_hive_pending_external_counsel_countersignature" -- until counsel signs, OH outbound should carry an additional `OPINION_PENDING_COUNSEL` warning in the renderer, not just the lapsed-license disclosure.
- **AN-4:** TN gate_notes references "HB 2537 (2025-04-08)" inside the JSON itself even though SB 909 is the correct cite. State_gates.json contradicts itself: the `tn_specific_2026_update` block correctly identifies SB 909, but `gate_notes` still says HB 2537. Clean both.
- **AN-5:** No statute currently encoded for **IN solicitor registration real-estate exemption** (IC 24-5-12). State_gates.json IN entry flags it as `_research_verification_pending`. Mark IN as `wholesale_legal_status: legal_unlicensed_with_disclosures_PENDING_VERIFICATION` until cleared.

---

**Checklist complete. 14 of 14 items pass with 5 critical fixes required and 5 advisory notes attached.**

Augustine Crane / Compliance Assistant
For Justine Ji-Young Park / Compliance Lead
2026-05-12
