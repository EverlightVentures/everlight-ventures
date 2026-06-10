# Georgia Principal-Buyer and License-Status Disclosure Appendix

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**

**Filed by:** Justine Park, Compliance Gate
**Date:** 2026-04-26 (Pacific Time)
**Status:** DRAFT v0.1, internal Hive research, NOT legal advice. External GA real estate counsel must countersign before relying on this in any litigation, regulatory, or contested-transaction posture.
**Attaches to:** `Broker_OS/contracts/ASSIGNMENT_CONTRACT_BASE.md`
**Source triage:** `Wholesale/compliance/APPENDIX_TRIAGE.md`
**Trigger:** Any property located in the State of Georgia. Always.

> Marquise Smith must engage Georgia real estate counsel and California real estate counsel before this appendix is used in any actual transaction. OCGA 43-40 unauthorized-brokerage findings carry administrative, civil, and in aggravated cases criminal exposure. OCGA 10-1-393 (Georgia Fair Business Practices Act) violations are independently actionable by the Georgia Attorney General. Until external counsel countersigns, this appendix is the Hive's internal operating posture and nothing more.

---

## When This Appendix Attaches

This appendix attaches to the underlying assignment contract whenever the property is located in the State of Georgia. There is no sub-trigger, no carve-out, and no conditional. **Property in Georgia = this appendix attaches. Always.**

The trigger is geographic, not factual. The principal-buyer position and the lapsed-CA-license disclosure must be on the record of every Georgia file regardless of seller status, deal size, channel of origination, or whether assignment or double-close is the planned exit.

If the property crosses state lines (mixed-state portfolio sale, multi-parcel out-of-state package, or contract restructured to a different state mid-pipeline), this appendix continues to attach to the Georgia parcel and the corresponding state appendix attaches to the other parcel.

---

## Mandatory Disclosure Clause (Verbatim)

The following block is the universalized version of the principal-buyer + lapsed-CA-license disclosure block from `HIVE_OPINION_OH_EQUITABLE_INTEREST.md`, Section (e). It MUST appear unchanged in every Georgia outbound surface listed in the next section. Any edit must be escalated to Justine Park (Compliance Gate) and Bernard Calloway (corporate / regulatory) before send.

> **DISCLOSURE OF PRINCIPAL-BUYER POSITION AND LICENSE STATUS**
>
> Marquise Smith, doing business as Everlight Ventures, is acting as the principal buyer of this property under a written purchase contract. Marquise Smith holds equitable interest in the contract and intends to assign that contract, or close in his own name, at his sole election. Marquise Smith is NOT acting as a real estate agent, broker, or fiduciary on behalf of the seller, and does NOT represent the seller. Marquise Smith is NOT a currently licensed real estate broker or salesperson in Georgia. Marquise Smith holds a California real estate salesperson license that is currently inactive (lapsed). Seller is encouraged to consult independent legal, tax, and real estate counsel of seller's choosing before signing any document. Earnest money is held by a licensed Georgia closing attorney trust account under OCGA 44-14-13 and is refundable per the terms of the purchase contract. This transaction is governed by the laws of the State of Georgia and will close through a licensed Georgia closing attorney.

This is the operative disclosure. Nothing about it is decorative.

---

## Required Placement (Four Surfaces, Non-Negotiable)

The mandatory disclosure clause above must appear on each of the following surfaces. Justine's pre-send filter blocks any Georgia outbound that fails any one of these four placements.

### 1. Purchase Contract

Numbered paragraph above the signature line. Not a footnote, not an exhibit, not a separately initialed addendum that the seller can be steered away from. The clause is paragraph text, in the same body font as the rest of the contract, in the four corners of the document the seller signs.

Recommended numbered-paragraph location: immediately after the "Buyer's Right to Assign" clause and immediately before the signature block. The seller's eye must travel through the disclosure on the way to the signature line.

### 2. Outbound Email (Cold and Warm)

Footer block. Position: above the CAN-SPAM physical mailing address and above the unsubscribe link. The disclosure block is the first piece of footer content the recipient encounters when scrolling past the signature.

The branded_mailer template `content_tools/branded_mailer.py` carries a `state_disclosure_footer` slot for this. State-detection on the lead record at send time triggers the slot fill with the Georgia variant. If state is not yet resolved (cold OOS sweep), default ON for any footer that could land in a Georgia inbox.

### 3. Direct Mail (Postcards and Letters)

Body or back side. Minimum font size 8pt. The disclosure cannot live in a separate insert that can be discarded; it must be on the same physical sheet of paper that carries the offer or the call to action.

For postcards: back side, 8pt minimum, full disclosure block. For letters: body, after the call to action, before the signature. For yellow letters and handwritten-style mail: type-set the disclosure even if the rest of the piece is handwritten. Handwritten disclosure is illegible at 8pt and fails the surface requirement.

### 4. Landing Pages (GA-Targeted)

Every landing page that a Georgia seller can reach via geo-targeted ad, mailed QR code, or state-specific URL. Disclosure block in the page footer, above the privacy policy link, in the same color and size class as the rest of the footer. Not in a collapsible accordion. Not behind a "more info" link. Visible on first paint, all viewport widths.

Pages that route Georgia traffic to an out-of-state path (national lander with state-conditional content) must show the disclosure on the Georgia path.

---

## OCGA 44-14-13 -- Earnest Money Trust Account Routing

OCGA 44-14-13 governs the handling of trust funds in Georgia real estate transactions. Wholesaler-held earnest money is one of the most common enforcement triggers under the Georgia Real Estate Commission's interpretation of the statute when read in conjunction with OCGA 43-40.

Operational requirements:

1. EMD on every Georgia file is wired to a licensed Georgia closing attorney's trust account named in the purchase contract. EMD is NEVER deposited into a personal account, an Everlight Ventures business operating account, or any non-attorney-controlled escrow.
2. The closing attorney trust account is identified by name, attorney name, and Georgia bar number on the face of the purchase contract. Per `state_gates.json`, the preferred Georgia closer is `georgia_title_escrow_atl`. The deal record carries the specific routing instructions.
3. EMD release is governed by mutual written instruction or by court order. No unilateral release. Any dispute over EMD is escalated to the closing attorney for resolution per OCGA 44-14-13.
4. Hive minimum EMD on Georgia files is $1,000 or 1% of contract price, whichever is greater, mirroring the Ohio standard. Sub-$1,000 EMD is the textbook prosecutor exhibit and must not ship.

The EMD trust-account routing is the documentary evidence of equitable interest. Without it, the principal-buyer defense degrades substantially under Georgia Real Estate Commission scrutiny.

---

## OCGA 13-1-7 -- Default Damages Cap and Attorney-Fee Scope

OCGA 13-1-7 imposes limits on contract-level damages and constrains the scope of attorney-fee shifting in private commercial agreements. The Hive position is that the assignment fee in any Georgia wholesale contract must be stated plainly as an assignment fee, not disguised as liquidated damages or as a default-triggered fee, in order to stay clear of OCGA 13-1-7 enforceability questions.

Operational requirements:

1. The assignment fee is named and quantified in the purchase contract and in the assignment of contract document. It is NOT structured as liquidated damages on seller default, NOT structured as a fee that scales with contract price beyond the named amount, and NOT structured as an attorney-fee recovery clause.
2. Any attorney-fee shifting clause in the purchase contract is limited to actual attorney fees reasonably incurred in enforcing the contract, capped at 15 percent of the principal sum in dispute per OCGA 13-1-11 (the closely-related attorney-fee cap statute). Open-ended "all attorney fees" language is scrubbed.
3. EMD forfeiture on seller default is treated as actual damages (the buyer's out-of-pocket transaction cost), not as liquidated damages, and the contract states this. Per OCGA 13-1-7, liquidated damages clauses must reflect a reasonable estimate of probable actual loss; EMD denominated as "liquidated damages" without that documentation is a 13-1-7 invalidation magnet.
4. No clause that purports to recover lost-profit damages on the assignment fee in the event of seller default. Recovery is limited to EMD plus actual out-of-pocket expense.

---

## OCGA 43-40 -- Real Estate License Law (Principal-Buyer Carve-Out)

OCGA 43-40 governs the licensing and conduct of Georgia real estate brokers and salespersons. The statute does NOT impose a license requirement on a person acting on his or her own behalf as a principal buyer or principal seller of real property. The principal-buyer carve-out is the legal foundation of the Georgia wholesale assignment model.

Operational requirements:

1. Marquise Smith signs every Georgia purchase contract as principal buyer in his own name (or in the name of Everlight Ventures DBA, with Marquise as the natural-person principal). EMD is wired from his own funds (or DBA funds) to the GA closing attorney trust account. Equitable title vests in him, not in any third party for whom he is acting.
2. Marketing is contract-rights-only and post-signature. No "for sale" listings, no Zillow-style postings, no buyer-list blasts of the property until the purchase contract is fully executed and EMD is on deposit. The principal-buyer carve-out evaporates the moment the operator markets property he does not control.
3. The mandatory disclosure clause above states explicitly that Marquise is NOT a Georgia-licensed broker or salesperson, NOT acting on behalf of the seller, and NOT a fiduciary of the seller. This affirmative non-licensure disclosure is the protective firewall against any Georgia Real Estate Commission inquiry that begins with "did you hold yourself out as a licensee."
4. Marquise's lapsed California real estate salesperson license is disclosed verbatim in the same clause. A lapsed CA license is a CA Department of Real Estate matter, not a Georgia matter. The Hive position: disclose anyway. A Georgia seller who later searches "Marquise Smith real estate license" and finds a CA record is owed advance disclosure or the principal-buyer defense degrades into a holding-out exposure.

---

## OCGA 10-1-393 -- Georgia Fair Business Practices Act

OCGA 10-1-393 (Georgia Fair Business Practices Act, "GFBPA") imposes a fair-dealing standard on consumer-facing transactions. Wholesale outreach to a Georgia homeowner is consumer-facing for purposes of the GFBPA regardless of the size of the transaction. The Georgia Attorney General has independent authority to act on consumer behalf and to seek civil penalties.

Operational requirements:

1. No guaranteed close dates. Any close-date language in any Georgia outbound, contract, or follow-up correspondence MUST be qualified per the timeline-language guardrail below.
2. No deceptive ARV claims. Any ARV figure delivered to a Georgia seller must be accompanied by a "this is an estimate, not an appraisal, no warranty" qualifier and a specific data source (county comp pull, MLS comp set with date, paid AVM with provider name).
3. No bait-and-switch on price. The contract price stated in the first written offer is the price on the contract the seller signs. Any price reduction post-signature for inspection findings is a written addendum signed by both parties, not an oral renegotiation at the closing table.
4. No fictitious urgency. "Sign by Friday or the offer expires" language is GFBPA-magnetic if the offer is in fact open beyond Friday. Justine's pre-send filter scrubs any urgency language not tied to a documented deadline.

---

## Timeline-Language Guardrail (GFBPA + OCGA 13-1-7 Adjacent)

Independent of any default trigger, the GFBPA disfavors any seller-facing language that promises or implies a fixed close date. Any close-date statement in any Georgia outbound, contract, or follow-up correspondence MUST be qualified as follows:

> Any close date stated in this communication or in the underlying purchase contract is a target date, subject to title clearance, lien resolution, and the satisfaction of all closing conditions in the purchase contract. No party guarantees a specific close date. Closing occurs when title is clear and all conditions are met, on the earliest date the closing attorney can schedule.

Phrases that violate the guardrail and must be scrubbed by Justine's pre-send filter:

- "Close in 7 days" without the target-subject-to-title qualifier
- "Guaranteed close date"
- "Cash close, no delays"
- Any countdown timer on a landing page tied to a close date
- Any "we close on your timeline" copy that promises seller-controlled timing of closing-condition resolution

The qualifier is not optional. It is the difference between an aspirational marketing statement and an actionable misrepresentation under OCGA 10-1-393.

---

## Counterpart Execution and Effective Date

This appendix and the underlying assignment contract together constitute one agreement.

1. Both documents must be signed by both parties on the same date. The "transaction date" for purposes of any Georgia statutory calculation is the date the seller signs the purchase contract, not the date Marquise countersigns.
2. Counterpart execution is permitted. Electronic signature is permitted under OCGA 10-12 (Georgia Uniform Electronic Transactions Act) and the federal E-SIGN Act, 15 U.S.C. 7001. PDF + DocuSign + Documenso + Dropbox Sign are acceptable.
3. If the negotiation was conducted primarily in a language other than English, a written translation of this appendix in that language must be delivered to the seller before signing. The translated copy and the English copy together constitute one instrument.
4. The effective date of the appendix is the date the seller signs. Any prior-dated appendix copy in the deal folder is invalid and must be re-executed at the same sitting as the contract.
5. If the underlying assignment contract is amended at any point before closing, this appendix is re-executed alongside the amendment. The disclosure clause cannot drift behind the contract version.

---

## Filing Instructions for the Operator

1. The signed appendix is stored at `Broker_OS/contracts/generated/GA/{deal_id}/00_ga_disclosure_appendix.signed.pdf`. The `00_` prefix puts it at the top of the deal folder file list, ahead of the purchase contract itself, because it is the document that controls the entire posture of the transaction.
2. The signed appendix is also mirrored to Supabase under the `ga_compliance_artifacts` table with the deal_id foreign key, the SHA-256 hash of the PDF, and the seller-signature date.
3. The appendix attaches at the moment a property is identified as Georgia-located. Geographic detection runs at lead-creation time. The appendix template populates with the deal-level variables (deal_id, property address, seller name, contract date) at the same moment the underlying purchase contract is generated.
4. The appendix is delivered to the seller in the same envelope, email thread, or e-sign packet as the purchase contract. Never as a separate later send.
5. Re-review of any signed appendix is triggered by any of the conditions in the next section. Justine's quarterly audit also pulls a random 10% sample for fresh review.
6. Retention: 7 years from close, matching the Ohio appendix recordkeeping schedule. Cold-storage backup monthly.

---

## Re-Review Triggers

This appendix is operational until any one of the following fires, at which point Justine Park re-opens the file and either re-issues or escalates to Bernard Calloway. The single trigger that fires first determines the next review date.

1. **Any amendment to OCGA 43-40** (Georgia Real Estate License Law).
2. **Any amendment to OCGA 44-14-13** (trust account routing).
3. **Any amendment to OCGA 13-1-7 or OCGA 13-1-11** (damages cap and attorney-fee scope).
4. **Any amendment to OCGA 10-1-393** (Georgia Fair Business Practices Act).
5. **Any new HB or SB targeting wholesalers in Georgia.** The Georgia General Assembly biennial sessions are the trigger watch. Justine's quarterly intel cron flags this.
6. **A Bernard Calloway opinion that supersedes this one.** A superseding opinion replaces this appendix in full and Justine re-issues the operational template against the new opinion.
7. **Every 18 months from the date of last review**, regardless of statutory activity. The 18-month clock from this filing date expires 2027-10-26.

The earliest of triggers 1 through 7 is the operative re-review date. Justine's quarterly intel cron monitors the Georgia General Assembly bill tracker and the OCGA chapter-amendment feed for triggers 1 through 5.

---

## Counsel Review Required Before First Use

Before this appendix is used in a live deal:

1. Engage California real estate counsel (Carlos Moreno, RE specialty) to review the lapsed-CA-license disclosure language and confirm it does not create CA holding-out risk.
2. Engage Georgia real estate counsel to review the principal-buyer disclosure, OCGA 44-14-13 trust-account mechanics, OCGA 13-1-7 / 13-1-11 damages and attorney-fee language, the GFBPA timeline-language guardrail, and the four-surface placement requirements against current Georgia Real Estate Commission guidance.
3. Both counsel return one-page sign-off letters on firm letterhead acknowledging the appendix as compliant for the operator's first Georgia use.
4. Bernard Calloway and Justine Park countersign the appendix as internal sign-off after external review.
5. Re-engage both counsel on every re-review trigger above.

This is internal Hive posture until external CA + GA counsel countersigns. Until that signature lands, this appendix is operational guidance and nothing more. It is not legal advice. It is not a litigation-grade document. It is the Hive's good-faith reading of Georgia law as of the filing date, designed to keep the Atlanta-metro pipeline moving while external counsel is engaged.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**
**DRAFT v0.1. Internal Hive posture only. Pending external CA + GA counsel countersign.**

Justine Park, Compliance Gate.
2026-04-26, Pacific Time
