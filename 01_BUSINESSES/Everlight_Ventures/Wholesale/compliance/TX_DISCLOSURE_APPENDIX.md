# Texas Principal-Buyer and License-Status Disclosure Appendix

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**

**Filed by:** Justine Park, Compliance Gate
**Date:** 2026-04-26 (Pacific Time)
**Status:** DRAFT v0.1, internal Hive research, NOT legal advice. External TX real estate counsel must countersign before relying on this in any litigation, regulatory, or contested-transaction posture.
**Attaches to:** `Broker_OS/contracts/ASSIGNMENT_CONTRACT_BASE.md`
**Source triage:** `Wholesale/compliance/APPENDIX_TRIAGE.md`
**Trigger:** Any property located in the State of Texas. Always.

> Marquise Smith must engage Texas real estate counsel and California real estate counsel before this appendix is used in any actual transaction. TX Property Code Sec. 5.086 and Sec. 5.0865 (SB 1577 expansion, 2023) carry per-violation civil penalties and seller-rescission rights; non-compliance is independently actionable by the seller and by the Texas Attorney General. Until external counsel countersigns, this appendix is the Hive's internal operating posture and nothing more.

---

## When This Appendix Attaches

This appendix attaches to the underlying assignment contract whenever the property is located in the State of Texas. There is no sub-trigger, no carve-out, and no conditional. **Property in Texas = this appendix attaches. Always.**

The trigger is geographic, not factual. The principal-buyer position, the SB 1577 wholesaler-name disclosure, and the lapsed-CA-license disclosure must be on the record of every Texas file regardless of seller status, deal size, channel of origination, or whether assignment or double-close is the planned exit.

If the property crosses state lines (mixed-state portfolio sale, multi-parcel out-of-state package, or contract restructured to a different state mid-pipeline), this appendix continues to attach to the Texas parcel and the corresponding state appendix attaches to the other parcel.

---

## Mandatory Disclosure Clause (Verbatim)

The following block is the Texas-adapted version of the principal-buyer + lapsed-CA-license disclosure block from `HIVE_OPINION_OH_EQUITABLE_INTEREST.md`, Section (e), expanded to incorporate the wholesaler-intent disclosure required by TX Property Code Sec. 5.086 and the SB 1577 (2023) expansion at Sec. 5.0865. It MUST appear unchanged in every Texas outbound surface listed in the next section. Any edit must be escalated to Justine Park (Compliance Gate) and Bernard Calloway (corporate / regulatory) before send.

> **DISCLOSURE OF PRINCIPAL-BUYER POSITION, WHOLESALER INTENT, AND LICENSE STATUS (TEXAS)**
>
> Marquise Smith, doing business as Everlight Ventures, is acting as the principal buyer of this property under a written purchase contract. Marquise Smith holds equitable interest in the contract and intends to assign that contract, or close in his own name, at his sole election. Marquise Smith is NOT acting as a real estate agent, broker, or fiduciary on behalf of the seller, and does NOT represent the seller. Marquise Smith is NOT a currently licensed real estate broker or sales agent in Texas. Marquise Smith holds a California real estate salesperson license that is currently inactive (lapsed). **Pursuant to Texas Property Code Sec. 5.086, Marquise Smith hereby discloses in writing, before any contract is signed, that he is acquiring an equitable interest in the property for the purpose of assigning the contract to a third party for profit, and that he intends to profit from the assignment of the contract rather than from acquiring fee simple title to the property. Pursuant to Texas Property Code Sec. 5.0865 (SB 1577, 2023), this same disclosure is provided in writing to any prospective assignee acquiring contract rights from Marquise Smith, with the affirmative statement that the assignee is acquiring contract rights and not the property itself.** Seller is encouraged to consult independent legal, tax, and real estate counsel of seller's choosing before signing any document. Earnest money is held by a Texas title company licensed under Texas Insurance Code Chapter 2651 and is refundable per the terms of the purchase contract and the option period. This transaction is governed by the laws of the State of Texas and will close through a Texas-licensed title company.

This is the operative disclosure. Nothing about it is decorative. The bolded segment is the SB 1577 statutory body and is non-negotiable.

---

## Required Placement (Four Surfaces, Non-Negotiable)

The mandatory disclosure clause above must appear on each of the following surfaces. Justine's pre-send filter blocks any Texas outbound that fails any one of these four placements.

### 1. Purchase Contract

Numbered paragraph above the signature line. Not a footnote, not an exhibit, not a separately initialed addendum that the seller can be steered away from. The clause is paragraph text, in the same body font as the rest of the contract, in the four corners of the document the seller signs.

Recommended numbered-paragraph location: immediately after the "Buyer's Right to Assign" clause and immediately before the signature block. The seller's eye must travel through the disclosure on the way to the signature line. SB 1577 imposes the same requirement on the assignment-of-contract document delivered to the assignee, so the disclosure clause appears in BOTH the purchase contract (seller-side) and the assignment of contract (buyer-side / assignee-side).

### 2. Outbound Email (Cold and Warm)

Footer block. Position: above the CAN-SPAM physical mailing address and above the unsubscribe link. The disclosure block is the first piece of footer content the recipient encounters when scrolling past the signature.

The branded_mailer template `content_tools/branded_mailer.py` carries a `state_disclosure_footer` slot for this. State-detection on the lead record at send time triggers the slot fill with the Texas variant. If state is not yet resolved (cold OOS sweep), default ON for any footer that could land in a Texas inbox. SB 1577 expressly extends the disclosure obligation to marketing communications, so the footer is mandatory on every Texas-bound email regardless of warmth tier.

### 3. Direct Mail (Postcards and Letters)

Body or back side. Minimum font size 8pt. The disclosure cannot live in a separate insert that can be discarded; it must be on the same physical sheet of paper that carries the offer or the call to action.

For postcards: back side, 8pt minimum, full disclosure block. For letters: body, after the call to action, before the signature. For yellow letters and handwritten-style mail: type-set the disclosure even if the rest of the piece is handwritten. Handwritten disclosure is illegible at 8pt and fails the surface requirement. SB 1577 covers off-market marketing, which includes direct mail offers extended before any contract is in place.

### 4. Landing Pages (TX-Targeted)

Every landing page that a Texas seller can reach via geo-targeted ad, mailed QR code, or state-specific URL. Disclosure block in the page footer, above the privacy policy link, in the same color and size class as the rest of the footer. Not in a collapsible accordion. Not behind a "more info" link. Visible on first paint, all viewport widths.

Pages that route Texas traffic to an out-of-state path (national lander with state-conditional content) must show the disclosure on the Texas path. Buyer-side landing pages (assignee acquisition) carry the same disclosure; SB 1577 extends to both sides of the transaction.

---

## TX Property Code Sec. 5.086 -- Wholesaler-Name Disclosure

TX Property Code Sec. 5.086 is the foundational Texas wholesaler-disclosure statute. It requires that a person who has entered into a contract to purchase real property and who intends to assign that contract for profit must disclose, in writing and before the seller signs, the wholesaler's name and the wholesaler's intent to assign the contract for profit.

Operational requirements:

1. The disclosure language is delivered in writing to the seller BEFORE the seller signs the purchase contract. Pre-contract, not at-contract, not post-contract. Operationally this means the disclosure is in the offer letter or LOI, not deferred to the purchase contract body.
2. The disclosure includes Marquise's full legal name, the Everlight Ventures DBA, and the affirmative statement of wholesaler intent (acquiring equitable interest, intending to assign for profit, profit comes from assignment not from fee simple ownership).
3. The disclosure is on the operator's letterhead or in the email body itself, not buried in an attachment the seller has to open. Treat it as a first-paragraph disclosure of intent, not a closing-paragraph footnote.
4. The Hive standard: every Texas-bound seller-facing communication carries the disclosure block from the first cold touch through every follow-up. There is no warm-tier carve-out under Sec. 5.086.

The Sec. 5.086 disclosure is the gating compliance step for a Texas wholesale assignment. Failure to deliver the disclosure pre-contract creates a seller-rescission right and exposes the operator to civil penalties under the Texas Deceptive Trade Practices Act, TX Bus. & Com. Code Sec. 17.

---

## TX Property Code Sec. 5.0865 -- SB 1577 Expansion (Buyer-Side and Off-Market)

SB 1577 (2023, codified at TX Property Code Sec. 5.0865) extends the Sec. 5.086 disclosure obligation in two material ways:

1. **Both sides of the transaction.** The disclosure must be delivered in writing to BOTH the seller (the original property owner) AND the assignee (the third-party buyer of the contract rights). The buyer-side disclosure includes the affirmative statement that the assignee is acquiring contract rights, not the property itself, and that closing of the property purchase remains contingent on the underlying purchase-contract terms.
2. **Off-market marketing.** The disclosure obligation extends to off-market marketing of equitable-interest contracts, including buyer-list email blasts, JV wholesaler shares, and pocket-list distribution. Marketing the contract rights to a Texas-domiciled assignee triggers the buyer-side Sec. 5.0865 disclosure even if the seller-side disclosure has already been delivered.

Operational requirements:

1. The buyer-side disclosure is in the assignment of contract document, in the assignment marketing email body, and in any buyer-list distribution that includes Texas contract-rights inventory.
2. The buyer-side disclosure is captured by the `required_buyer_disclosure: equitable_interest_written_TX` flag in `state_gates.json` and is enforced on every TX assignment record before the contract rights are marketed to any assignee.
3. ARV figures to the seller in writing remain BLOCKED in Texas per `state_gates.json` (`arv_in_writing_to_seller_allowed: false`). The seller-side disclosure does not unlock written ARV delivery to the seller; it is a separate compliance flag and stays off.
4. SB 1577 imposes per-violation civil penalties and a seller-rescission right that survives closing. The 24-month clock on a SB 1577 rescission claim is one of the longest in any state wholesale statute, so the disclosure record is retained for the full 7-year recordkeeping window without exception.

---

## TX Insurance Code Sec. 2651 -- Title Agency Closing Requirements

TX Insurance Code Chapter 2651 governs the licensing of Texas title insurance agencies and the conduct of escrow officers. Texas is a title-company-closing state (not an attorney-state), and EMD plus closing flows through a licensed Texas title agency.

Operational requirements:

1. EMD on every Texas file is wired to a Texas title company licensed under Insurance Code Chapter 2651, named in the purchase contract by company name, escrow officer name, and license number. Per `state_gates.json`, the preferred Texas closer is `texas_title_dal`. The deal record carries the specific routing instructions.
2. EMD is fully refundable to the buyer through expiration of the option period (TREC paragraph 23 default). Post-option, EMD release is governed by mutual written instruction or court order. No unilateral release.
3. Closing occurs at the Texas title agency, with the title agency issuing the closing statement and the title insurance commitment. The assignment fee is disbursed through the closing statement, NOT direct from the assignee to Marquise outside escrow. Direct-pay outside escrow is the textbook TX TREC and Texas Department of Insurance enforcement trigger.
4. The Sec. 2651 licensure of the named title agency is verified at deal-creation time. Justine's pre-close audit confirms the title agency's license is current with the Texas Department of Insurance before EMD is wired.

---

## Channel Restrictions Cross-Reference (TX SB 140 and TX Bus. & Com. Code 302)

Outside the four-corners of this contract-level appendix, the operator must comply with Texas channel restrictions logged in `state_gates.json`:

1. **Cold SMS is BLOCKED in Texas** until the operator registers as a telephone solicitor with the Texas Secretary of State and posts the $10,000 bond required by TX SB 140 (effective 2025-09-01). The deal record reflects this; SMS is not a permitted seller-contact channel for cold Texas leads.
2. **Cold autodialer / AI-voice calls are BLOCKED** under TCPA prior-express-written-consent requirements and TX Bus. & Com. Code Sec. 302. Manual human voice only on cold Texas calls.
3. **Manual cold voice calls and direct mail** are the permitted cold channels for Texas seller leads. Email is permitted with the SB 1577 disclosure footer installed.

These channel restrictions are operational background to this appendix. The appendix is contract-level; the channel restrictions are pre-contract. Both must be in compliance for a Texas file to ship.

---

## Timeline-Language Guardrail (DTPA Adjacent)

Independent of any default trigger, the Texas Deceptive Trade Practices Act (TX Bus. & Com. Code Sec. 17) disfavors any seller-facing language that promises or implies a fixed close date. Any close-date statement in any Texas outbound, contract, or follow-up correspondence MUST be qualified as follows:

> Any close date stated in this communication or in the underlying purchase contract is a target date, subject to title clearance, lien resolution, the option period under TREC paragraph 23, and the satisfaction of all closing conditions in the purchase contract. No party guarantees a specific close date. Closing occurs when title is clear and all conditions are met, on the earliest date the title agency can schedule.

Phrases that violate the guardrail and must be scrubbed by Justine's pre-send filter:

- "Close in 7 days" without the target-subject-to-title qualifier
- "Guaranteed close date"
- "Cash close, no delays"
- Any countdown timer on a landing page tied to a close date
- Any "we close on your timeline" copy that promises seller-controlled timing of closing-condition resolution

The qualifier is not optional. It is the difference between an aspirational marketing statement and an actionable misrepresentation under DTPA Sec. 17.46.

---

## Counterpart Execution and Effective Date

This appendix and the underlying assignment contract together constitute one agreement.

1. Both documents must be signed by both parties on the same date. The "transaction date" for purposes of any Texas statutory calculation is the date the seller signs the purchase contract, not the date Marquise countersigns.
2. Counterpart execution is permitted. Electronic signature is permitted under TX Bus. & Com. Code Sec. 322 (Texas UETA) and the federal E-SIGN Act, 15 U.S.C. 7001. PDF + DocuSign + Documenso + Dropbox Sign are acceptable.
3. If the negotiation was conducted primarily in a language other than English (Spanish is the operative cross-language case in Texas), a written translation of this appendix in that language must be delivered to the seller before signing. The translated copy and the English copy together constitute one instrument. This Spanish-translation requirement is the practical mirror of the CA Civil Code 1632 obligation and is observed in Texas as a defensive default.
4. The effective date of the appendix is the date the seller signs. Any prior-dated appendix copy in the deal folder is invalid and must be re-executed at the same sitting as the contract.
5. If the underlying assignment contract is amended at any point before closing, this appendix is re-executed alongside the amendment. The disclosure clause cannot drift behind the contract version.

---

## Filing Instructions for the Operator

1. The signed appendix is stored at `Broker_OS/contracts/generated/TX/{deal_id}/00_tx_disclosure_appendix.signed.pdf`. The `00_` prefix puts it at the top of the deal folder file list, ahead of the purchase contract itself, because it is the document that controls the entire posture of the transaction.
2. The signed appendix is also mirrored to Supabase under the `tx_compliance_artifacts` table with the deal_id foreign key, the SHA-256 hash of the PDF, and the seller-signature date. The buyer-side Sec. 5.0865 disclosure record is stored alongside under `tx_compliance_artifacts.assignee_disclosure_blob` so the dual-side audit trail is on one row.
3. The appendix attaches at the moment a property is identified as Texas-located. Geographic detection runs at lead-creation time. The appendix template populates with the deal-level variables (deal_id, property address, seller name, contract date) at the same moment the underlying purchase contract is generated.
4. The appendix is delivered to the seller in the same envelope, email thread, or e-sign packet as the purchase contract. Never as a separate later send. The Sec. 5.086 pre-contract disclosure obligation is satisfied by the offer-letter / LOI-stage delivery before the contract packet arrives; the appendix at-contract is the second layer.
5. Re-review of any signed appendix is triggered by any of the conditions in the next section. Justine's quarterly audit also pulls a random 10% sample for fresh review.
6. Retention: 7 years from close, matching the Ohio appendix recordkeeping schedule. Cold-storage backup monthly. SB 1577 long-tail rescission risk justifies the full 7-year window without exception.

---

## Re-Review Triggers

This appendix is operational until any one of the following fires, at which point Justine Park re-opens the file and either re-issues or escalates to Bernard Calloway. The single trigger that fires first determines the next review date.

1. **Any amendment to TX Property Code Sec. 5.086** (wholesaler-name disclosure).
2. **Any amendment to TX Property Code Sec. 5.0865** (SB 1577 expansion).
3. **Any new Texas SB or HB amending wholesaler disclosure obligations.** Texas legislature meets biennially (odd years); the 2027 session is the next live trigger window. Justine's quarterly intel cron flags this.
4. **Any amendment to TX Insurance Code Chapter 2651** (title agency licensure).
5. **Any amendment to TX Bus. & Com. Code Sec. 17** (DTPA fair-dealing standard) materially affecting wholesale outreach.
6. **Any amendment to TX SB 140 or TX Bus. & Com. Code Sec. 302** affecting cold-channel restrictions, even though those statutes are operational rather than contract-level.
7. **A Bernard Calloway opinion that supersedes this one.** A superseding opinion replaces this appendix in full and Justine re-issues the operational template against the new opinion.
8. **Every 18 months from the date of last review**, regardless of statutory activity. The 18-month clock from this filing date expires 2027-10-26.

The earliest of triggers 1 through 8 is the operative re-review date. Justine's quarterly intel cron monitors the Texas Legislature bill tracker and the TREC / TDI rule-amendment feed for triggers 1 through 6.

---

## Counsel Review Required Before First Use

Before this appendix is used in a live deal:

1. Engage California real estate counsel (Carlos Moreno, RE specialty) to review the lapsed-CA-license disclosure language and confirm it does not create CA holding-out risk.
2. Engage Texas real estate counsel to review the principal-buyer disclosure, the Sec. 5.086 / Sec. 5.0865 SB 1577 disclosure language for both seller-side and buyer-side surfaces, the Insurance Code Chapter 2651 title-agency mechanics, the DTPA timeline-language guardrail, and the four-surface placement requirements against current TREC and Texas Department of Insurance guidance.
3. Both counsel return one-page sign-off letters on firm letterhead acknowledging the appendix as compliant for the operator's first Texas use.
4. Bernard Calloway and Justine Park countersign the appendix as internal sign-off after external review. **Bernard escalation flag: SB 1577's dual-side disclosure obligation and the 24-month rescission tail are above the typical Hive risk envelope; Bernard's review is mandatory, not advisory, before first Texas use.**
5. Re-engage both counsel on every re-review trigger above.

This is internal Hive posture until external CA + TX counsel countersigns. Until that signature lands, this appendix is operational guidance and nothing more. It is not legal advice. It is not a litigation-grade document. It is the Hive's good-faith reading of Texas law as of the filing date, designed to keep the Dallas / Houston / San Antonio metro pipeline moving while external counsel is engaged.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**
**DRAFT v0.1. Internal Hive posture only. Pending external CA + TX counsel countersign.**

Justine Park, Compliance Gate.
2026-04-26, Pacific Time
