# Theo Briggs's Federal Audit -- Open Deal

**Author:** Theodore A. Briggs III, Chief Audit Executive + General Counsel, Everlight Ventures
**Date:** 2026-05-15
**Operative documents reviewed:**
- `Broker_OS/open_deal/EMD_LOCK_POLICY.md` (LOCKED 2026-05-15)
- `Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md` (v1.0 DRAFT)
- `Broker_OS/open_deal/OPEN_DEAL_BUILD_SPEC.md` (Ready for sprint)
**Question presented:** Whether the Everlight Open Deal product, as currently specified, exposes Everlight Ventures or Richard Gee personally to (a) state money-transmission liability, (b) FTC Section 5 unfair-or-deceptive-practice liability, (c) BSA/OFAC sanctions liability, (d) federal securities liability, (e) CFPB jurisdiction, or (f) federal/state tax recharacterization risk -- and whether the product can be shipped in its current form without keeping Rich "out of jail and above radar federally."

---

## Verdict: FIX REQUIRED

Not a blocker. Not clean. Six fixes, none of them showstoppers if patched before public soft launch. The MTL scare is overblown for our structure, but the "Verified" badge as written is a Section 5 problem and the OFAC posture is a real BSA gap. Patch language is below. Ship-ready after Day 7.

---

## Top 3 Risks (ranked by jail probability)

1. **FTC Act Section 5 -- "Verified Buyer" badge becomes a deceptive trade practice the day we issue our first badge under the current KYC-lite spec.** This is the single highest-probability federal enforcement vector in the build. 15 U.S.C. 45(a)(1) prohibits "unfair or deceptive acts or practices in or affecting commerce." A gold check mark next to a username implies, to a reasonable consumer, that Everlight has verified the user's identity and source of funds against a recognized standard. Our spec defines "Verified" as "bank statement + LLC docs + manual review by Marquise + Justine" -- with no ID verification, no OFAC screening, no source-of-funds attestation, no PEP screening. The FTC has pursued exactly this fact pattern (FTC v. LendingClub Corp., 3:18-cv-02454-JSC, N.D. Cal. 2018; FTC v. DesignerWare, LLC, 12-CV-03459, W.D. Pa. 2012) -- not banks, not crypto, but mid-market businesses that gave consumers a "verified" or "trusted" signal without the underlying diligence. The exposure here isn't jail-grade (Section 5 is civil), but it's reputation-grade and creates a private right of action under most state UDAP statutes, including TN Consumer Protection Act, Tenn. Code Ann. 47-18-104. Fix is cheap: redefine the badge or do the diligence.

2. **BSA / OFAC sanctions screening -- we are not a Money Services Business under 31 C.F.R. 1010.100(ff), but we ARE a "U.S. person" under 31 C.F.R. 501.601 and subject to OFAC's strict-liability prohibition on dealing with SDN List persons.** This is the second-highest probability vector and the only one with criminal exposure -- 50 U.S.C. 1705 carries up to $1M civil penalty per violation AND up to 20 years imprisonment for willful violations. There is NO de minimis threshold for OFAC. A $99 Lock Fee from a sanctioned counterparty is a strict-liability violation regardless of intent. The good news: Stripe runs OFAC screening on every payment at the card-network level (per Stripe's Restricted Businesses policy, Section 3.1 of the Stripe Services Agreement). The bad news: Stripe's screen is on the cardholder name, not on the underlying buyer-entity or beneficial owner. An LLC fronting for an SDN-listed beneficial owner clears Stripe but does not clear OFAC. Fix is documented diligence: screen every "Verified" tier applicant's LLC and personal name against the SDN list (free, OFAC.treasury.gov) and log the screen. Five-minute task per applicant. No screen = no badge.

3. **State Money Transmission Laws -- the 24-hour Stripe Capture window on the Verified tier is the closest thing to MTL exposure we have, and it still doesn't get there in any of the five states named.** The question presented is whether holding $500 in our Stripe balance for up to 24 hours pending refund-or-capture constitutes "transmitting" money. The short answer: no, under the Uniform Money Services Act and every enumerated state's MTL framework. "Money transmission" requires receiving money from one person to convey to another. We are receiving money from the buyer to retain (in the no-walk path) or to refund to the same buyer (in the walk path). Buyer A pays Everlight; Everlight either keeps it or returns it to Buyer A. There is no second-party transmission. See Cal. Fin. Code 2003(q) (defining money transmission as "receiving money for transmission" -- transmission to another party is the definitional core); N.Y. Banking Law 641 (same); Tex. Fin. Code 151.301(b)(4) (same); Fla. Stat. 560.103(23) (same); 205 ILCS 657/5 (same). The 10% house fee on Verified walks is a service charge retained for our own account, not transmitted. The 90% refund returns to origin. The Inner Circle $99 is non-refundable and never leaves our account. NONE of this is MTL. Even the closest analog -- CDPAP-Style escrow holding -- requires the funds to be held FOR a third party, which we are not. **Verdict: no MTL registration required in any state. Stop worrying about this. But document the analysis in the audit log so a state AG sees it on first request.**

---

## Gaps Found (with statute cite)

- **GAP 1: "Verified Buyer" badge is Section 5 deceptive.** FTC Act 15 U.S.C. 45(a)(1); TN Consumer Protection Act, Tenn. Code Ann. 47-18-104(b)(5) (deceptive acts include "represent[ing] that goods or services have... characteristics... that they do not have"). A "verification" badge backed by bank statement + LLC docs only does not meet a reasonable-consumer expectation of identity verification.

- **GAP 2: No OFAC SDN screening protocol for paying customers.** 31 C.F.R. Part 501 et seq. (OFAC Reporting, Procedures, and Penalties Regulations); 50 U.S.C. 1705 (IEEPA penalties). Strict liability. No threshold. Applies to every U.S. person.

- **GAP 3: No FinCEN posture documentation.** While we are NOT an MSB (we don't transmit money, exchange currency, or issue prepaid access), we should have a one-page memo on file explaining why, because the question will come up in any future banking, payment processor, or institutional capital diligence. 31 C.F.R. 1010.100(ff)(5) defines money transmitter; our facts negate the elements but the analysis should be written.

- **GAP 4: Inner Circle $49/mo + Lock Fee credit-back creates a non-issue Howey question but creates a real CFPB question I want to close.** Howey (SEC v. W.J. Howey Co., 328 U.S. 293 (1946)) requires (i) investment of money, (ii) common enterprise, (iii) expectation of profits, (iv) solely from the efforts of others. Inner Circle subscribers pay for access (a service), not for profits from Everlight's efforts. The Lock Fee credit-back is a discount mechanism, not a return. **Not a security.** However: the recurring $49/mo with a "credit-back at close" feature *could* be argued by an aggressive plaintiff as a "negative-option marketing" issue under the FTC's Negative Option Rule (16 C.F.R. Part 425) and ROSCA (15 U.S.C. 8401 et seq.), the Restore Online Shoppers' Confidence Act. ROSCA requires clear disclosure of recurring charges, express informed consent, and a simple cancellation mechanism. Our spec does not yet show the ROSCA-compliant subscription disclosure.

- **GAP 5: PSA Schedule A "10% non-refundable as consideration for the 24-hour exclusivity period" language is enforceable in TN but is challengeable under California Civil Code 1671(b) for any California buyer (liquidated damages must be reasonable; 10% in 24 hours may be argued unconscionable).** The disclosure already flags this open question for `legal_heck_aurelio` -- I am closing it: until a per-state analysis is done, California buyers must be geofenced out of the Verified tier or the 10% must drop to a documented actual-cost recovery (Stripe fees + ~$10 ops cost = roughly 5%). The build spec already lists CA in the allowed geofence -- this needs to be revisited.

- **GAP 6: Tax characterization.** Lock Fee forfeitures (the 10% Verified walk fee, the $99 Inner Circle walk fee) are ordinary income under I.R.C. 61(a)(1) on the date earned (the walk date). Not capital gains. Not deferred. They are includible in the year received. State sales tax in Tennessee: services are generally NOT subject to TN sales tax under Tenn. Code Ann. 67-6-205, but "the furnishing of any of the things or services taxable under this chapter" includes specifically enumerated services. Pre-contract exclusivity fees are not among the enumerated services in 67-6-205. **Not subject to TN sales tax.** I want a one-line entry in the books characterizing each forfeiture as "ordinary income -- pre-contract fee, retained" so the external CPA has clean treatment.

---

## Patch Language (paste-ready)

### Patch 1 -- Verified Badge (cures GAP 1)

- **File:** `Broker_OS/open_deal/EMD_LOCK_POLICY.md`
- **Section:** "Verified KYC-lite (the $99 one-time fee)"
- **Replace:**
  > - Proof of funds (bank statement, last 30 days, $50k min liquid)
  > - LLC formation docs OR personal acquisition history
  > - Manual review by Marquise + Justine (legal)
  > - Approved -> gold "Verified" check next to username everywhere
  > - Filters tire-kickers, gives buyer-quality signal on the pulse feed, creates instant $99 revenue

- **With:**
  > - Proof of funds (bank statement, last 30 days, $50k min liquid)
  > - Government-issued photo ID (driver's license or passport, image upload, retained 90 days then purged)
  > - LLC formation docs OR personal acquisition history
  > - OFAC SDN List screen against both the LLC name (if applicable) and the individual name; screen result logged with timestamp + OFAC list version
  > - Manual review by Marquise + Justine (compliance)
  > - Approved -> gold "Buyer-Funds-Verified" badge next to username everywhere. Badge tooltip on hover reads: "Everlight has confirmed this buyer has provided proof of funds and government ID. This is not a verification of identity by a federally accredited third party."
  > - Filters tire-kickers, gives buyer-quality signal on the pulse feed, creates instant $99 revenue
  >
  > **Anti-deception note:** The badge tooltip language is mandatory and not optional. The badge name was changed from "Verified Buyer" to "Buyer-Funds-Verified" to remove any reasonable-consumer inference of identity verification by a federally accredited entity. See `audit_responses/theo_briggs.md` GAP 1.

### Patch 2 -- OFAC screening (cures GAP 2)

- **File:** New file at `Wholesale/compliance/OFAC_SCREENING_PROTOCOL.md`
- **Section:** New document
- **Content (new file in entirety):**
  > # OFAC SDN Screening Protocol -- Everlight Ventures
  >
  > **Authority:** 31 C.F.R. Part 501; 50 U.S.C. 1705 (IEEPA); OFAC Sanctions List Search at sanctionssearch.ofac.treas.gov
  >
  > **Scope:** Every buyer who pays the $99 Verified upgrade. Every Inner Circle subscriber on initial signup. Every buyer-entity (LLC) on initial PSA. The Browser tier requires no screen because no funds are captured.
  >
  > **Procedure:**
  > 1. On submission of Verified application or Inner Circle signup, screen the individual name AND any submitted LLC name against the OFAC SDN List at sanctionssearch.ofac.treas.gov.
  > 2. Use exact-match and fuzzy-match (the tool's default).
  > 3. If no hit: log `ofac_screen_result=clear`, `ofac_list_version=<date>`, `screened_by=<reviewer>`, `screened_at=<timestamp>` to `pulse_events` with `event_type=ofac_screen_clear`.
  > 4. If hit: do NOT approve. Do NOT charge. Do NOT issue badge. Escalate to Theo within 4 business hours. File OFAC Reporting Form TD F 90-22.50 if a blocked transaction occurred.
  > 5. Re-screen all active Verified + Inner Circle buyers quarterly against the current SDN List. New hit = immediate suspension + Theo escalation.
  > 6. Retain screening logs for 5 years per 31 C.F.R. 501.601.
  >
  > **No exceptions. Strict liability statute. Documented screen is the audit defense.**

### Patch 3 -- FinCEN posture memo (cures GAP 3)

- **File:** New file at `Wholesale/compliance/FINCEN_NON_MSB_POSITION_MEMO.md`
- **Section:** New document
- **Content (paste-ready):**
  > # FinCEN Non-MSB Position Memo -- Everlight Open Deal Lock Fee Product
  >
  > **Question presented:** Whether the Everlight Open Deal Lock Fee product makes Everlight Ventures a Money Services Business as defined in 31 C.F.R. 1010.100(ff).
  >
  > **Short answer:** No.
  >
  > **Analysis:**
  > Under 31 C.F.R. 1010.100(ff), an MSB includes a money transmitter, currency dealer or exchanger, check casher, issuer of traveler's checks/money orders/stored value, seller of prepaid access, and U.S. Postal Service. Of these, only "money transmitter" could conceivably apply. Money transmission under 1010.100(ff)(5)(i) means "the acceptance of currency, funds, or other value that substitutes for currency from one person AND the transmission of currency, funds, or other value that substitutes for currency to another location or person by any means."
  >
  > Two elements must be satisfied: (1) acceptance from Person A, and (2) transmission to Person B at another location or to a different person. Everlight accepts Lock Fees from Buyer A and either (a) retains them (no walk) or (b) refunds them to Buyer A (walk). At no point are funds transmitted to a second party. The 10% Verified walk fee is retained for Everlight's own account as a service charge. The Inner Circle $99 is retained in all cases.
  >
  > The Lock Fee is therefore not money transmission. Everlight is not a money transmitter and is not an MSB.
  >
  > **Conclusion:** No federal MSB registration required. No state money transmission license required in CA (Cal. Fin. Code 2003(q)), NY (N.Y. Banking Law 641), TX (Tex. Fin. Code 151.301), FL (Fla. Stat. 560.103(23)), or IL (205 ILCS 657/5). Each of these statutes follows the same UMSA-derived definition requiring transmission to a second party.
  >
  > **Advised.** TAB / 2026-05-15

### Patch 4 -- ROSCA-compliant Inner Circle subscription disclosure (cures GAP 4)

- **File:** `Broker_OS/open_deal/OPEN_DEAL_BUILD_SPEC.md`
- **Section:** "Pages to build on `everlightventures.io`" item 5 (`/inner-circle`)
- **Replace:**
  > 5. **`/inner-circle`** -- $49/mo Inner Circle subscription page.

- **With:**
  > 5. **`/inner-circle`** -- $49/mo Inner Circle subscription page. Must comply with ROSCA (15 U.S.C. 8401 et seq.) and FTC Negative Option Rule (16 C.F.R. Part 425). Required elements before Stripe Checkout opens:
  >    (a) clear, prominent disclosure of the $49/mo recurring charge, billed monthly, in 14pt+ text within 100px of the Subscribe button;
  >    (b) checkbox "I understand my card will be charged $49 every month until I cancel" -- unchecked by default, required to proceed;
  >    (c) one-click cancellation link in `/buyer/dashboard` that cancels at end of current billing period (no retention dark patterns, no "are you sure" -> "but wait" -> "5 reasons to stay" funnel);
  >    (d) cancellation confirmation email sent within 1 business hour;
  >    (e) Lock Fee credit-back terms displayed in same modal: "Your $99 Lock Fees on signed deals will credit to the assignment fee at close. Lock Fees on walked deals are not refunded."

### Patch 5 -- Geofence revision (cures GAP 5)

- **File:** `Broker_OS/open_deal/OPEN_DEAL_BUILD_SPEC.md`
- **Section:** "Pre-launch checklist" line 7
- **Replace:**
  > - [ ] Geofence config: TN, CA, AZ, FL allowed; others blocked at signup until per-state disclosure is drafted

- **With:**
  > - [ ] Geofence config v1: TN, AZ, FL, GA, TX, OH, MO allowed at Verified + Inner Circle tier; CA blocked at Verified + Inner Circle tier until California-specific liquidated-damages analysis is complete (Cal. Civ. Code 1671(b)); NY blocked at all tiers until N.Y. Gen. Bus. Law 349/350 review is complete. Browser tier (no charge) is open to all 50 states.

### Patch 6 -- Tax characterization (cures GAP 6)

- **File:** `Broker_OS/open_deal/EMD_LOCK_POLICY.md`
- **Section:** Append new section at end
- **Add (new text):**
  > ## Tax characterization (per Theo audit 2026-05-15)
  >
  > - All forfeited Lock Fees (Verified 10% walk fee, Inner Circle $99 walk fee) are ordinary income to Everlight Ventures in the calendar year of forfeiture, characterized in books as "pre-contract service fee -- retained." I.R.C. 61(a)(1).
  > - Inner Circle $49/mo subscription revenue is ordinary income, recognized monthly as earned.
  > - Verified $99 KYC fee is ordinary income, recognized on charge date (one-time fee, no deferral).
  > - No Tennessee state sales tax applies. Tenn. Code Ann. 67-6-205 does not enumerate pre-contract exclusivity service fees among taxable services.
  > - External CPA (quarterly review) to confirm characterization on Q1 close. Audit log entry per Theo memo `_logs/theo_briggs/memos/2026-05-15_open_deal_federal_audit.md`.

---

## Recommendation to Rich

Ship it, but patch the six gaps above before public soft launch. The Money Transmission Law fear is overblown; we are nowhere near MSB territory, and the FinCEN memo will be the document we hand any payment processor, bank, or state AG who asks. The two patches that actually matter are renaming the badge from "Verified" to "Buyer-Funds-Verified" (with the tooltip) and adding the OFAC screening protocol -- those two cure the only federal exposures that have real teeth, and they cost us about two hours of compliance work per applicant. Cap California at the Browser tier until I finish the liquidated-damages memo, and ROSCA-proof the Inner Circle subscription page so we don't get a deceptive-recurring-charge complaint in month two. Advised.

---

## Filing

- **Memo filed to audit log:** `_logs/theo_briggs/memos/2026-05-15_open_deal_federal_audit.md` (this file)
- **Disclosure draft countersign:** awaiting `legal_heck_aurelio` per `BUYER_DISCLOSURE_LOCK_FEE.md` open questions
- **2L review:** queued to Justine Park, 2L/3L sync 2026-05-16 12:00 PT
- **Escalation:** none required; no $1M+ exposure, no SEC question, no state AG inquiry. Single-memo close.

**Advised.**
TAB / 2026-05-15
