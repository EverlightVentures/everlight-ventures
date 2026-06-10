# Ohio Principal-Buyer and License-Status Disclosure Appendix

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**

**Filed by:** Contract Attorney, Everlight Hive Mind
**Date:** 2026-04-25 (Pacific Time)
**Status:** DRAFT v0.1, internal Hive posture only, requires CA + OH counsel countersign before first live use
**Attaches to:** `Broker_OS/contracts/ASSIGNMENT_CONTRACT_BASE.md`
**Source opinion:** `Wholesale/legal/HIVE_OPINION_OH_EQUITABLE_INTEREST.md`
**Trigger:** Any property located in the State of Ohio. Always.

> Marquise Smith must engage Ohio real estate counsel and California real estate counsel before this appendix is used in any actual transaction. ORC 4735 unauthorized-brokerage findings carry administrative, civil, and in aggravated cases criminal exposure. ORC 1349.61 (foreclosure rescue) violations are independently actionable. Until external CA + OH counsel countersigns, this appendix is the Hive's internal operating posture and nothing more.

---

## When This Appendix Attaches

This appendix attaches to the underlying assignment contract whenever the property is located in the State of Ohio. There is no sub-trigger, no carve-out, and no conditional. **Property in Ohio = this appendix attaches. Always.**

The trigger is geographic, not factual. The principal-buyer position and the lapsed-CA-license disclosure must be on the record of every Ohio file regardless of seller status, deal size, channel of origination, or whether assignment or double-close is the planned exit.

If the property crosses state lines (mixed-state portfolio sale, multi-parcel out-of-state package, or contract restructured to a different state mid-pipeline), this appendix continues to attach to the Ohio parcel and the corresponding state appendix attaches to the other parcel.

---

## Mandatory Disclosure Clause (Verbatim)

The following block is reproduced verbatim from Section (e) of the source opinion. It MUST appear unchanged in every Ohio outbound surface listed in the next section. Any edit must be escalated to Justine Park (Compliance Gate) and Bernard Calloway (corporate / regulatory) before send.

> **DISCLOSURE OF PRINCIPAL-BUYER POSITION AND LICENSE STATUS**
>
> Marquise Smith, doing business as Everlight Ventures, is acting as the principal buyer of this property under a written purchase contract. Marquise Smith holds equitable interest in the contract and intends to assign that contract, or close in his own name, at his sole election. Marquise Smith is NOT acting as a real estate agent, broker, or fiduciary on behalf of the seller, and does NOT represent the seller. Marquise Smith is NOT a currently licensed real estate broker or salesperson in Ohio. Marquise Smith holds a California real estate salesperson license that is currently inactive (lapsed). Seller is encouraged to consult independent legal, tax, and real estate counsel of seller's choosing before signing any document. Earnest money is held by a licensed Ohio title agency under ORC 3953 and is refundable per the terms of the purchase contract. The Residential Property Disclosure Form required under ORC 5302.30 will be delivered as a passthrough document to any assignee. This transaction is governed by the laws of the State of Ohio.

This is the operative disclosure. Nothing about it is decorative.

---

## Required Placement (Four Surfaces, Non-Negotiable)

The mandatory disclosure clause above must appear on each of the following surfaces. Justine's pre-send filter blocks any Ohio outbound that fails any one of these four placements.

### 1. Purchase Contract

Numbered paragraph above the signature line. Not a footnote, not an exhibit, not a separately initialed addendum that the seller can be steered away from. The clause is paragraph text, in the same body font as the rest of the contract, in the four corners of the document the seller signs.

Recommended numbered-paragraph location: immediately after the "Buyer's Right to Assign" clause and immediately before the signature block. The seller's eye must travel through the disclosure on the way to the signature line.

### 2. Outbound Email (Cold and Warm)

Footer block. Position: above the CAN-SPAM physical mailing address and above the unsubscribe link. The disclosure block is the first piece of footer content the recipient encounters when scrolling past the signature.

The branded_mailer template `content_tools/branded_mailer.py` carries an `oh_disclosure_footer` slot for this. State-detection on the lead record at send time triggers the slot fill. If state is not yet resolved (cold OOS sweep), default ON for any footer that could land in an Ohio inbox.

### 3. Direct Mail (Postcards and Letters)

Body or back side. Minimum font size 8pt. The disclosure cannot live in a separate insert that can be discarded; it must be on the same physical sheet of paper that carries the offer or the call to action.

For postcards: back side, 8pt minimum, full disclosure block. For letters: body, after the call to action, before the signature. For yellow letters and handwritten-style mail: type-set the disclosure even if the rest of the piece is handwritten. Handwritten disclosure is illegible at 8pt and fails the surface requirement.

### 4. Landing Pages (OH-Targeted)

Every landing page that an Ohio seller can reach via geo-targeted ad, mailed QR code, or state-specific URL. Disclosure block in the page footer, above the privacy policy link, in the same color and size class as the rest of the footer. Not in a collapsible accordion. Not behind a "more info" link. Visible on first paint, all viewport widths.

Pages that route Ohio traffic to an out-of-state path (national lander with state-conditional content) must show the disclosure on the Ohio path.

---

## ORC 5302.30 Residential Property Disclosure Form Passthrough

For any 1-to-4 unit residential transaction in Ohio, the seller-completed Residential Property Disclosure Form required under ORC 5302.30 must pass through the assignment unaltered.

Operational requirements:

1. Seller signs the RPDF at the same sitting as the purchase contract. The RPDF is collected before EMD is wired.
2. The RPDF is delivered to the assignee as a passthrough document. Marquise does not edit, redact, summarize, or re-key any field on the form. The original seller-completed PDF is the document delivered.
3. Failure to deliver the RPDF gives the end buyer a 3-business-day rescission right under ORC 5302.30(K). Justine's audit pulls the RPDF from the deal folder on every closed Ohio file.
4. If the property is exempt from RPDF (new construction, transfers between co-owners, court-ordered transfers, certain trust transfers), the exemption basis is documented in the deal folder under `03_rpdf_exemption_memo.pdf` with the specific ORC subsection cited.

The RPDF is a statutory passthrough. The Hive does not opine on any disclosure the seller makes on the form. The Hive's only role is delivery integrity.

---

## ORC 1349.61 Timeline-Language Guardrail

ORC 1349.61 (Ohio's foreclosure-rescue statute, mirror of CA Civil Code 2945) controls any transaction where the seller is in default. The Hive position is that NOD-recorded sellers remain attorney-only and the Ohio outreach gate in `state_gates.json` continues to block default-stage outbound.

Independent of the default trigger, ORC 1349.61 disfavors any seller-facing language that promises or implies a fixed close date. Any close-date statement in any Ohio outbound, contract, or follow-up correspondence MUST be qualified as follows:

> Any close date stated in this communication or in the underlying purchase contract is a target date, subject to title clearance, lien resolution, and the satisfaction of all closing conditions in the purchase contract. No party guarantees a specific close date. Closing occurs when title is clear and all conditions are met, on the earliest date the title agency can schedule.

Phrases that violate the guardrail and must be scrubbed by Justine's pre-send filter:

- "Close in 7 days" without the target-subject-to-title qualifier
- "Guaranteed close date"
- "Cash close, no delays"
- "Close before [foreclosure date]" (this language is a 1349.61 magnet even if the seller is not yet in default)
- Any countdown timer on a landing page tied to a close date
- Any "we close on your timeline" copy that promises seller-controlled timing of closing-condition resolution

The qualifier is not optional. It is the difference between an aspirational marketing statement and an actionable misrepresentation under ORC 1345 (CSPA) and ORC 1349.61.

---

## Counterpart Execution and Effective Date

This appendix and the underlying assignment contract together constitute one agreement.

1. Both documents must be signed by both parties on the same date. The "transaction date" for purposes of any Ohio statutory calculation is the date the seller signs the purchase contract, not the date Marquise countersigns.
2. Counterpart execution is permitted. Electronic signature is permitted under ORC 1306 (Ohio UETA) and the federal E-SIGN Act, 15 U.S.C. 7001. PDF + DocuSign + Dropbox Sign are acceptable.
3. If the negotiation was conducted primarily in a language other than English, a written translation of this appendix in that language must be delivered to the seller before signing. The translated copy and the English copy together constitute one instrument.
4. The effective date of the appendix is the date the seller signs. Any prior-dated appendix copy in the deal folder is invalid and must be re-executed at the same sitting as the contract.
5. If the underlying assignment contract is amended at any point before closing, this appendix is re-executed alongside the amendment. The disclosure clause cannot drift behind the contract version.

---

## Filing Instructions for the Operator

1. The signed appendix is stored at `Broker_OS/contracts/generated/OH/{deal_id}/00_oh_disclosure_appendix.signed.pdf`. The `00_` prefix puts it at the top of the deal folder file list, ahead of the purchase contract itself, because it is the document that controls the entire posture of the transaction.
2. The signed appendix is also mirrored to Supabase under the `oh_compliance_artifacts` table with the deal_id foreign key, the SHA-256 hash of the PDF, and the seller-signature date.
3. The appendix attaches at the moment a property is identified as Ohio-located. Geographic detection runs at lead-creation time. The appendix template populates with the deal-level variables (deal_id, property address, seller name, contract date) at the same moment the underlying purchase contract is generated.
4. The appendix is delivered to the seller in the same envelope, email thread, or e-sign packet as the purchase contract. Never as a separate later send.
5. Re-review of any signed appendix is triggered by any of the conditions in the next section. Justine's quarterly audit also pulls a random 10% sample for fresh review.
6. Retention: 7 years from close, matching the source opinion's recordkeeping schedule. Cold-storage backup monthly.

---

## Re-Review Triggers

This appendix is operational until any one of the following fires, at which point Justine Park re-opens the file and either re-issues or escalates to Bernard Calloway. The single trigger that fires first determines the next review date.

1. **Any amendment to ORC 4735** (Ohio Real Estate Brokers Act).
2. **Any amendment to ORC 1349.61** (Ohio foreclosure-rescue statute).
3. **Any amendment to ORC 5302.30** (Residential Property Disclosure Form).
4. **Any amendment to Ohio HB 132** or successor wholesaler-marketing legislation.
5. **Any amendment to Ohio HB 226** (2024 wholesaler-scrutiny update) or successor.
6. **A Bernard Calloway opinion that supersedes this one.** A superseding opinion replaces this appendix in full and Justine re-issues the operational template against the new opinion.
7. **Every 18 months from the date of last review**, regardless of statutory activity. The 18-month clock from this filing date expires 2027-10-25.

The earliest of triggers 1 through 7 is the operative re-review date. Justine's quarterly intel cron monitors the Ohio General Assembly bill tracker and the ORC chapter-amendment feed for triggers 1 through 5.

---

## Counsel Review Required Before First Use

Before this appendix is used in a live deal:

1. Engage California real estate counsel (Carlos Moreno, RE specialty) to review the lapsed-CA-license disclosure language and confirm it does not create CA holding-out risk.
2. Engage Ohio real estate counsel to review the principal-buyer disclosure, ORC 5302.30 passthrough mechanics, ORC 1349.61 timeline-language guardrail, and the four-surface placement requirements against current Ohio Division of Real Estate guidance.
3. Both counsel return one-page sign-off letters on firm letterhead acknowledging the appendix as compliant for the operator's first Ohio use.
4. Bernard Calloway and Justine Park countersign the appendix as internal sign-off after external review.
5. Re-engage both counsel on every re-review trigger above.

This is internal Hive posture until external CA + OH counsel countersigns. Until that signature lands, this appendix is operational guidance and nothing more. It is not legal advice. It is not a litigation-grade document. It is the Hive's good-faith reading of Ohio law as of the filing date, designed to keep the Cleveland pipeline moving while external counsel is engaged.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**
**DRAFT v0.1. Internal Hive posture only. Pending external CA + OH counsel countersign.**

Contract Attorney, Everlight Hive Mind
2026-04-25, Pacific Time
