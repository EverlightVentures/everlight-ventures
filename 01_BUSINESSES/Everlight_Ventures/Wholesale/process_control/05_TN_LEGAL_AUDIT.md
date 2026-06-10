# TN Wholesale Legal Audit -- Memphis 30-Property Push

**Audit date:** 2026-04-29 (PT)
**Auditor:** contract_attorney (AI Hive agent, NOT licensed counsel -- informational only)
**Scope:** Full pipeline steps 1-9 for the Memphis 30-property push (25 vacant lots + 5 SFRs, target buyer Chris @ Mid South Homebuyers)
**Operator under audit:** Marquise / Richard Gee, sole proprietor d/b/a Everlight Ventures, Memphis-based, TN RE license INACTIVE, zero deals closed
**Files audited:**
- 01_PRECALL_EMAIL_TEMPLATE.md
- 02_OFFER_MATH_AND_BACK_TAX.md
- 03_DUE_DILIGENCE_CLAUSE.md
- contracts/PSA_v3_boilerplate.md
- compliance/state_gates.json (TN block)

---

## 1. Executive Verdict

**LEGAL but with gaps.**

The pipeline as written is structurally lawful in TN if -- and ONLY if -- four conditions hold simultaneously: (a) no cold phone calls to TN-resident sellers, (b) the SB 909 wholesaler disclosure (Schedule A) is signed at or before PSA execution, (c) closing flows through a RESPA-compliant title firm in escrow with no advance fees, (d) the assignment fee is disclosed on the closing settlement statement. Three steps in the pipeline are currently BLOCKED for TN-resident sellers (cold call, cold SMS, pre-foreclosure outreach). Several steps are AT RISK due to operator structure rather than process language: sole-prop signatory line means Marquise is personally on the hook for any post-closing claim, and the TN telemarketer registration ($500/yr) plus surety bond ($50k at deal 3) are NOT yet posted. None of the gaps are deal-killers tonight, but two of them become deal-killers before Deal 3.

**Risk-of-suit summary:** non-trivial in three scenarios (named below), but none catastrophic if the SB 909 schedule and DD clause are executed clean. Personal-asset exposure exists because there is no LLC -- this is the largest single risk vector.

---

## 2. Per-Step Compliance Table

| # | Step | Status | Rationale |
|---|------|--------|-----------|
| 1 | Pre-call email to seller | **COMPLIANT** | CAN-SPAM elements present (sender ID, opt-out "reply STOP", honest subject, real reply-to). Memphis address goes in Resend footer via branded_mailer. Estate version names decedent appropriately. NO advance-fee, NO debt-collection language, NO foreclosure-rescue language. **One AT RISK sub-element:** physical mailing address must be a real address Marquise controls -- if Resend default footer shows a generic relay, swap to operator's PO Box or registered DBA address. |
| 2 | Phone call to seller -- TN-resident | **BLOCKED** | TN TSA 47-18-2002 makes cold telemarketing without TN Telemarketer Registration ($500/yr) an unfair/deceptive act. Marquise is NOT registered (state_gates.json line 403 confirms). Cold-call to TN sellers is illegal as currently structured. **Workaround:** email-first opens the door, and once seller replies/engages, the relationship is no longer "cold" -- a follow-up call to a responding seller is permitted. The pre-call email pathway is the legal door. |
| 2b | Phone call to seller -- out-of-state heir | **AT RISK** | Federal TCPA call hours apply (8am-9pm recipient-local). TN call hours (8am-9pm local) inherit. If recipient is in CA, all-party recording disclosure required. If recipient is in FL, all-party + Sunday-no. Federal DNC scrub at <31 days mandatory. Pipeline relies on a manual scrub gate -- if any number on the 30-list is on federal DNC and not scrubbed, single-violation TCPA exposure is $500-$1,500 per call. |
| 3 | Offer math + back tax handling | **COMPLIANT** | The corrected language ("back taxes are handled at the title firm out of closing proceeds, not out of pocket") is truthful and TN UDAP-safe. The v1 phrasing ("we pay every dollar of back tax out of OUR side") was deceptive and would have been a 47-18-104 violation; v2 fixes that. Itemized closing settlement statement 24 hrs pre-close meets material-disclosure standard. **One AT RISK note:** the phrase "RESPA-compliant Memphis title firm (Mid-South Title)" in the email is fine as long as Mid-South Title is genuinely RESPA-clean and Marquise is NOT receiving any kickback / referral fee from them -- RESPA Section 8 prohibits unearned fees for referrals between settlement service providers. |
| 4 | PSA execution | **COMPLIANT WITH ONE GAP** | PSA v3 boilerplate hits the TN-mandatory blocks: (a) sole-prop signatory line names Richard Gee individually, (b) Block 3 equitable-interest + assignment language is verbatim-strong, (c) Block 4 dual-remedy clause caps seller liquidated damages, (d) Block 5 Wholesaler Disclosure Exhibit fires for TN automatically, (e) 7-day minimum DD per HB 2537 is honored (we run 14). **GAP:** PSA generator is supposed to refuse if no clean RESPA-verified title firm row exists for the metro. There is currently no `TitleCompany` Django row marked `respa_clean_verified=True` for `metro=Memphis`. The boilerplate's own gate (line 235 of PSA_v3_boilerplate.md) would refuse generation. **Action: add Mid-South Title row + verify RESPA-clean (no kickback agreement) BEFORE first PSA generates.** |
| 4b | SB 909 Schedule A wholesaler disclosure | **COMPLIANT IF EXECUTED -- GAP IF SKIPPED** | TN Code Ann. 66-32-101 et seq. (effective 2025-04-08) requires (1) wholesaler disclosure BEFORE or contemporaneously with PSA, (2) disclosure must state wholesaler does NOT represent seller, intends to assign, profit may exceed seller proceeds. Block 5 of PSA v3 covers items 1-3 of the statute. Implementation per state_gates: "Signed as Schedule A in same DocuSign envelope as PSA." **Statutory penalty if missed:** seller can rescind PSA + recover $10,000 statutory damages + attorneys' fees. This is the single highest-dollar TN-specific risk in the pipeline. |
| 5 | EMD wire to Mid-South Title escrow ($100) | **COMPLIANT** | $100 EMD into a third-party title firm IOLTA / escrow account is the correct flow. NOT into Marquise's personal account (would trigger advance-fee statutes + RESPA Section 10 escrow rules). EMD must remain refundable per DD clause until Day 14. Mid-South Title must be a TN-licensed title agency under TCA Chapter 56-35; verify license# before first wire. Escrow agreement should be in writing (one-page acknowledgment) so the title firm's fiduciary duty is documented. |
| 6 | Due diligence period (14 days) | **COMPLIANT** | DD clause as drafted (03_DUE_DILIGENCE_CLAUSE.md) covers items (a)-(g) including the wholesale-critical (f) "buyer confirmation of an end-buyer or assignee." 14 calendar days exceeds TN HB 2537 7-day minimum. Written-notice termination via email is sufficient under UETA. EMD-refundable structure documented. **Best-practice recommendation:** add to the clause a default "if Buyer fails to deliver written termination by 11:59pm CT on Day 14, this Agreement continues" -- the current clause says "prior to expiration" which is fine but a hard time stamp removes ambiguity. |
| 7 | Package to buyer Chris (or backup) | **COMPLIANT** | Buyer-side outreach to Mid South Homebuyers is B2B vendor outreach (lead_type=jv_wholesaler / investor_fund), inherits the b2b_vendor_outreach_default carve-out. No consumer-telemarketing rules apply. Email/voice OK during business hours. **AT RISK note:** the "buyers list" itself must NOT include skip-traced personal data on principals -- merge_field_gate.py is the safety; verify it is in the loop for any buyer outreach. CCPA does not apply to TN-resident buyers but applies if Chris stores any CA-resident principal data. |
| 8 | Assignment + closing wire to Richard Gee dba Everlight Ventures | **AT RISK -- structural** | The assignment is legal (TN allows assignment of contract rights). The closing wire to "Richard Gee d/b/a Everlight Ventures" is legal -- a sole prop's DBA wire is the operator's personal-tax wire. **Risk vector:** the wire is taxable income on Marquise's personal Schedule C. There is NO entity buffer between the deal proceeds and Marquise's personal assets. Any post-closing claim (seller rescission under SB 909, IRS audit, slander-of-title from a fourth-party heir) reaches Marquise's personal bank account, personal credit score, and any future-acquired personal assets. The assignment fee MUST also be disclosed on the closing settlement statement per Block 3 of the PSA -- if the title firm does NOT show the assignment fee on the seller's settlement statement, that is the single most common TN UDAP claim ("hidden middleman profit"). Verify Mid-South Title will show assignment fee on the seller side of the HUD-1 / closing disclosure BEFORE first close. |
| 9 | Tax handling -- Schedule C, Q2 estimate | **COMPLIANT** | Sole-prop wholesale income flows on Schedule C (line 1 gross / line 28 expenses / line 31 net). If first wire lands in May 2026, Q2 federal estimate is due June 15, 2026 (Form 1040-ES). TN has no state income tax on wages or assignment-fee income (Hall income tax repealed 2021), so no TN state estimate. Memphis municipal: gross-receipts tax under $100k/yr on consulting/service fees has zero filing requirement; if commissions cross $100k cumulative across the year, Memphis business tax license + filing kicks in (Memphis municipal business license required for any business operating from a Memphis address regardless of revenue -- $15-30/yr). **GAP:** Memphis municipal business license / Shelby County privilege tax not yet confirmed filed. Required for any business entity operating from a Memphis address, sole prop or LLC. Budget: ~$15 + $22 county = $37, one-time on first deal. |

---

## 3. Five Specific Suit Risks (ranked by probability x severity)

### Risk #1 -- TN SB 909 disclosure missed or signed late
**Probability:** MEDIUM (operator-error vector; first deal is highest-risk)
**Severity:** HIGH ($10,000 statutory damages + attorneys' fees + PSA rescission)
**Scenario:** Seller signs PSA. Schedule A disclosure not in the same envelope, or signed 2 days later, or the language doesn't track the statute (must state: wholesaler does NOT represent seller + intends to assign + profit may exceed seller proceeds). Seller's family lawyer notices post-close, files Tenn. Code Ann. 66-32-101 demand. Marquise pays $10k + fees out of personal account because there is no LLC.
**Already mitigated by:** Block 5 of PSA v3 boilerplate IF the contract_generator.py gate fires. **Residual risk:** if any PSA goes out manually (bypassing the generator), Schedule A could be omitted. Manual PSA = highest single-issue risk in the entire pipeline.

### Risk #2 -- Cold call to a TN-resident seller without telemarketer registration
**Probability:** MEDIUM-HIGH (Marquise is in Memphis, will be tempted to dial a TN number that didn't reply to email)
**Severity:** MEDIUM ($1,000-$2,500 per violation under TN TSA 47-18-2002 + 47-18-104 UDAP treble damages possible)
**Scenario:** Day 1 noon, seller didn't open the email. Marquise dials. Seller tapes the call (TN one-party, but THEY can record). Seller files complaint with TN Division of Consumer Affairs. Each call can be a separate violation. Stacking 30 properties x 3 attempts each = 90 potential violations if pattern is found.
**Already mitigated by:** state_gates.json TN cold_call_allowed=false flag. **Residual risk:** the gate is enforced in code (rex_belfort + rex_utils per memory `wholesale_boomerang_apr23`); if the operator dials manually from a personal phone bypassing the system, the gate doesn't catch it. **Hard rule for tonight: NO COLD CALLS to TN sellers, period. Email-first only. Phone only after seller replies.**

### Risk #3 -- Personal-asset exposure on any post-close claim (no LLC)
**Probability:** LOW per individual deal, MEDIUM cumulative across 30 properties
**Severity:** HIGH (uncapped -- reaches personal bank, personal credit, future-acquired property)
**Scenario:** Heir #2 of an estate didn't actually sign the PSA (heir #1 forged it, didn't have probate authority). Estate sues to void the deed and claw back. Buyer Chris sues Marquise for breach. Marquise has no LLC; judgment attaches to personal assets. Even a $5,000 settlement is a wipe-out at current cash position.
**Already mitigated by:** PSA Block 7 (notary recommended for TN even though not statutorily required) + estate authority verification at intel stage. **Residual risk:** sole-prop status. The 3-Deal Wealth Roadmap puts LLC AFTER Deal 1 commission -- this means Deals 1-2 are unprotected. Acceptable risk per operator decision but must be acknowledged.

### Risk #4 -- RESPA Section 8 / Section 10 violation via title firm referral
**Probability:** LOW
**Severity:** HIGH (federal exposure: 1 yr prison + $10,000 fine per violation, plus civil treble damages)
**Scenario:** Mid-South Title has an undisclosed referral arrangement with Marquise (kickback per closed deal, free leads, anything of value). Seller's attorney pulls the closing file for an unrelated dispute, finds the referral pattern, files HUD complaint.
**Already mitigated by:** Pipeline language "RESPA-compliant" assertion in the email. **Residual risk:** the assertion must be TRUE. Required action: confirm in writing with Mid-South Title that there is NO referral fee, NO marketing-services agreement, NO desk rental, NO anything-of-value flowing from them to Marquise. Get a one-page "no referral fee acknowledgment" signed before first close. This is cheap insurance.

### Risk #5 -- Federal Fair Housing claim (estate / out-of-state targeting)
**Probability:** LOW
**Severity:** HIGH (HUD complaint + civil penalties + state AG)
**Scenario:** A protected-class plaintiff alleges the targeting of estates with deceased Black homeowners in majority-Black ZIP codes constitutes disparate-impact discrimination. The pipeline's situational-signal language (estate, out-of-state, vacant) is FH-safe on its face. The risk is in the SOURCING upstream of the email -- if the property list was filtered using race-correlated proxies (ZIP, surname), that filter creates the disparate impact.
**Already mitigated by:** PRECALL email template explicitly notes "references SITUATIONAL signals (estate, out-of-state, vacant) NOT identity." **Residual risk:** verify the upstream property-filter logic. If it filters by ZIP, ensure ZIP selection is documented as economic (low-end vacant lots, not race), and keep the audit trail.

---

## 4. Five Hardening Actions, Ordered by Deadline

| # | Action | Deadline | Cost | Owner |
|---|--------|----------|------|-------|
| 1 | Verify Mid-South Title is RESPA-clean and create the `TitleCompany` row marked `respa_clean_verified=True, license_active=True` for metro=Memphis. Get a one-page "no referral fee" acknowledgment signed by Mid-South Title before first PSA generates. | **BEFORE first PSA** (this week) | $0 | Marquise (operator call) + Hammer (paperwork) |
| 2 | Confirm the contract_generator.py SB 909 Schedule A bundle fires automatically in the same DocuSign envelope. Manual override of PSA generation is BANNED for TN deals. Add a code gate: `assert lead.state != "TN" or schedule_a_in_envelope, "TN PSA without Schedule A is illegal"`. | **BEFORE first PSA** (this week) | $0 | Forge / engineering_foreman |
| 3 | File Memphis municipal business license + Shelby County privilege tax. Required regardless of revenue for any Memphis-operating business; filing now removes a free legal challenge surface. | **Within 30 days** of first deal | ~$37 one-time | Marquise |
| 4 | Form Tennessee LLC (or convert California LLC to TN-foreign-registered LLC) with a separate business bank account. Move all Deal 2+ contracts to LLC signatory. This collapses Risk #3 from HIGH-severity to LOW-severity. Per the 3-Deal Wealth Roadmap this is a Post-Deal-1 action. | **Post-Deal-1 commission** (after first $700+ wire lands) | $300 (TN LLC filing) + $25/yr registered agent | Marquise + Justine |
| 5 | Register as TN Telemarketer ($500/yr) AND post the $50k surety bond required at Deal 3 under TCA 62-13-104 (per Justine working interpretation in state_gates.json). Until both are posted, the pipeline cap is 2 closed deals before TN cold-call channel is forced shut. | **Before Deal 3** (per state_gates surety_bond_required_at_deal=3) | $500/yr telemarketer + $500-$1,500/yr surety bond premium | Marquise + Justine |

---

## 5. Where We EXCEED Minimum Requirements

These are areas where the pipeline goes beyond the statutory floor -- worth knowing because they are defensible if challenged.

1. **DD period 14 days, not the TN-minimum 7.** Doubles the seller's cool-off window beyond what HB 2537 requires. UDAP-defensive: cannot be characterized as a high-pressure sale.
2. **Dual-remedy clause caps Seller liquidated damages at EMD.** TN does not require this. Most wholesale PSAs leave seller-side damages uncapped, exposing buyer to actual + consequential. Our Block 4 caps seller's recovery at $100 EMD as the default election. This is a meaningful protection against runaway damages claims.
3. **Wholesaler Disclosure Exhibit (Block 5) is signed as a STANDALONE document, not just a paragraph buried in the PSA.** Goes beyond "contemporaneous" to "separately acknowledged." Disarms the most common buyer claim ("I didn't know they were a wholesaler") cleanly.
4. **Pre-call email creates a written paper trail BEFORE the phone call.** TN one-party recording state means we don't need consent to record, but the email establishes that Marquise made first contact via written channel -- which is consistent with the unregistered-telemarketer carve-out (the call follows an established written touch, not a cold call out of nowhere).
5. **Itemized closing settlement statement delivered 24 hours pre-close.** TN requires it 1 hour pre-close on TILA-covered loans (cash deals are exempt entirely). 24 hours is hotel-grade transparency. Hard to characterize the deal as deceptive.
6. **Branded mailer has CAN-SPAM elements baked in (resend_guard, resend_budget, physical address footer, one-click unsubscribe).** Not just present -- enforced at the mailer level so an operator cannot send a non-compliant email even by mistake.
7. **No autonomous bot calls anywhere in the pipeline.** TCPA prior-express-written-consent rule is the single biggest non-trivial-suit vector for wholesalers nationally; we don't expose to it.
8. **Pre-foreclosure outreach BLOCKED in TN at the gate level.** Even though TN doesn't have a foreclosure-rescue statute, SB 909 disclosure complexity for distress-stage sellers is high. We sidestep entirely.

---

## 6. Audit Checklist Summary

| # | Check | Verdict | Deal-killer? |
|---|-------|---------|--------------|
| 1 | Statute of Frauds (writing + signature) | PASS | No |
| 2 | Wholesaler-not-broker scope (TN SB 909) | PASS if Schedule A fires | YES if missed (Risk #1) |
| 3 | CAN-SPAM (email) | PASS | No |
| 4 | TCPA call hours + DNC scrub | PASS conditionally (no cold-call to TN) | YES if breached (Risk #2) |
| 5 | TN UDAP 47-18-104 (deceptive practices) | PASS (v2 honest language) | No |
| 6 | TN telemarketer registration 47-18-2002 | BLOCKED -- not registered | Only if cold-call (Risk #2) |
| 7 | TN surety bond TCA 62-13-104 | DEFERRED to Deal 3 | YES at Deal 3 |
| 8 | RESPA Section 8 / Section 10 | PASS conditionally (verify no kickback) | YES if breached (Risk #4) |
| 9 | Federal Fair Housing | PASS (situational signals only) | Low risk (Risk #5) |
| 10 | TN Probate Code (estate authority) | PASS at intel stage | Yes if forged-heir (Risk #3) |
| 11 | Memphis municipal business license | GAP -- not yet filed | No, post-deal cure OK |
| 12 | Personal-asset exposure (no LLC) | AT RISK | YES (Risk #3) |

**Totals:** 8 PASS, 1 BLOCKED, 1 DEFERRED, 1 GAP, 1 AT RISK

---

## 7. Single Highest-Priority Action Tonight

**Verify the TN PSA template auto-includes the SB 909 Schedule A disclosure in the same DocuSign envelope, and add a code-level assertion that blocks PSA generation if state=TN and Schedule A is missing.**

This is one engineering task (~30 min for Forge) that turns the highest-severity TN-specific risk ($10k statutory damages + PSA rescission) from a operator-error vector into a structural impossibility. Every other gap can wait until post-Deal-1; this one cannot, because the first PSA is the highest-risk PSA in the pipeline -- new operator, new template, new state.

---

## Disclaimer

This audit is informational analysis from an AI compliance agent operating under the Everlight Hive. It is NOT legal advice. Recommend human Tennessee real-estate attorney review before Deal 1 closes -- a 30-minute consult ($150-$300) on the SB 909 disclosure language and the title firm RESPA acknowledgment is cheap insurance against any of the five named suit risks.
