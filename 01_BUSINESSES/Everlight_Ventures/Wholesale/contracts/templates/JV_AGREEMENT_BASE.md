# Joint Venture Agreement -- Wholesale Real Estate Partnership

**Template version:** v1.0
**Last updated:** 2026-04-26
**Maintained by:** Lucrex / Justine Park, Compliance Gate
**Purpose:** Protect Everlight Ventures when partnering with another wholesaler, agent, or investor on a single deal. The party who brings the OTHER HALF (buyer if we have contract, contract if we have buyer) cannot work around us once introduced.

> **NOTICE:** This is informational. NOT legal advice. Have an attorney in the operating state review before first use. The non-circumvention + liquidated damages clauses are written aggressive on purpose -- adjust only on counsel's signoff.

---

## JOINT VENTURE AGREEMENT FOR REAL ESTATE WHOLESALE TRANSACTION

**Effective Date:** {{effective_date}}

**Property Address:** {{property_address}}, {{property_city}}, {{property_state}} {{property_zip}}

**County of Property:** {{property_county}}

**Legal Description:** {{legal_description}} (or as recorded in the {{property_county}} County Recorder/Clerk records)

---

### PARTIES

**Party A** -- {{party_a_name}} (the "Originator" -- party who brings the property under contract)
{{party_a_address}}
Phone: {{party_a_phone}}
Email: {{party_a_email}}
Role: {{party_a_role}}  // e.g., "Property Originator" or "Buyer Originator"

**Party B** -- {{party_b_name}} (the "Counterpart")
{{party_b_address}}
Phone: {{party_b_phone}}
Email: {{party_b_email}}
Role: {{party_b_role}}  // e.g., "Buyer Originator" or "Property Originator"

(One party MUST be Everlight Ventures or its DBA "Everlight Logistics" -- this template is from our perspective.)

**Designated Investor/End-Buyer:** {{end_buyer_name}} (introduced by {{introducing_party}})

---

### RECITALS

**WHEREAS**, Party A has either (a) executed a Purchase and Sale Agreement with the seller of the Property, or (b) introduced an end-investor capable of purchasing the Property; and

**WHEREAS**, Party B has the complementary side of the transaction (the buyer or the contract, respectively); and

**WHEREAS**, neither party can complete this assignment transaction profitably without the other; and

**WHEREAS**, the parties wish to formalize a single-deal joint venture, agree on the profit split, and protect each other from circumvention;

**NOW THEREFORE**, in consideration of the mutual promises below, the parties agree:

---

### 1. JOINT VENTURE PURPOSE

The parties form a single-purpose joint venture (the "JV") solely to facilitate the assignment, sale, and closing of the Property to the Designated Investor/End-Buyer. This JV is **not a partnership for any other property or any other transaction** unless extended in writing.

### 2. CONTRIBUTIONS

**Party A contributes:** {{party_a_contribution}} (e.g., "the executed Purchase and Sale Agreement dated {{psa_date}} with the seller, including all rights of assignment").

**Party B contributes:** {{party_b_contribution}} (e.g., "the introduction of {{end_buyer_name}} as the qualified cash end-buyer, plus negotiation of final assignment fee with end-buyer").

Each party warrants their contribution is real, exclusive to this JV during the term, and free of competing claims.

### 3. PROFIT SPLIT

Total assignment fee from the Designated Investor/End-Buyer: **${{total_assignment_fee}}** ("Total Fee").

Distribution at closing through the title/escrow agent:
- Party A: **{{party_a_split_pct}}%** = **${{party_a_amount}}**
- Party B: **{{party_b_split_pct}}%** = **${{party_b_amount}}**

Default split where this template applies: **50% / 50%** unless modified above. The split is **gross of any individual party's marketing or sourcing costs** -- each party absorbs their own out-of-pocket. There is no expense reimbursement before the split.

Disbursement is via the title/escrow agent, not party-to-party. **Each party authorizes the title/escrow agent to wire their share directly to their named bank account on the closing statement.** Neither party shall act as a pass-through for the other's share.

### 4. EXCLUSIVITY (90 DAYS)

For ninety (90) days from the Effective Date (the "Exclusivity Period"), each party agrees:

(a) Not to assign or attempt to assign the underlying Purchase and Sale Agreement to any party other than the Designated Investor/End-Buyer or a permitted assignee mutually agreed in writing;

(b) Not to introduce the Designated Investor/End-Buyer to any other deal involving the Property or any contiguous parcel without the other party's written consent;

(c) Not to introduce the seller of the Property to any other buyer for the same Property; and

(d) Not to relist, re-market, or re-introduce the Property to any third-party buyer outside this JV.

If closing has not occurred within 90 days due to seller default, market conditions, or buyer financing failure (none of which is a party's breach), the parties may extend the Exclusivity Period in writing or mutually terminate.

### 5. NON-CIRCUMVENTION (THE TEETH)

For a period of **twenty-four (24) months** from the Effective Date, neither party shall, directly or indirectly:

(a) Contact, transact with, or attempt to acquire the Property from the seller or the seller's heirs/successors outside of this JV;

(b) Contact, transact with, or attempt to sell ANY property to the Designated Investor/End-Buyer outside of this JV without the introducing party's written consent and agreed compensation;

(c) Use the contact information, motivation profile, financial capacity, or any other intelligence shared in this JV for the benefit of any party other than this JV;

(d) Disclose to any third party the identity of the seller, the end-buyer, the assignment fee amount, or the deal terms except to legal counsel, accountant, or as required by law;

(e) Contract a third party (employee, broker, runner, family member, related entity, or affiliate) to do anything the party itself is forbidden from doing under this Section 5.

**Each party acknowledges this Non-Circumvention clause is the bargained consideration for sharing the deal intelligence; without it, neither party would have shared.**

### 6. LIQUIDATED DAMAGES (FULL DEAL VALUE)

The parties agree that actual damages for breach of Section 4 (Exclusivity) or Section 5 (Non-Circumvention) are difficult to calculate but easily exceed any reasonable estimate. Therefore, in the event of breach by either party, the breaching party shall pay the non-breaching party as liquidated damages:

**(i) The greater of:**

- The full purchase price the seller actually received (or contracted to receive) from any buyer the breaching party introduced or steered toward the Property in violation of this Agreement; OR
- The full assignment fee or commission the breaching party received (or contracted to receive) from any buyer it introduced or steered in violation of this Agreement; OR
- **${{liquidated_damages_floor}}** (default: $25,000)

**(ii) PLUS** all attorney fees, court costs, recording fees, expert fees, and reasonable investigation costs incurred by the non-breaching party;

**(iii) PLUS** pre-judgment interest at the maximum legal rate from the date of breach.

The parties stipulate this measure is reasonable, agreed in advance, and not a penalty. The breaching party waives the defense that this measure is excessive.

**If both parties' shares would have been paid out at closing under Section 3, the liquidated damages amount shall NOT be reduced by the breaching party's notional share** -- the entire amount is owed to the non-breaching party as the cost of the breach.

### 7. MEMORANDUM OF JV (RECORDABLE NOTICE)

Concurrent with execution of this Agreement, the parties shall sign a separate **Memorandum of Joint Venture** in recordable form (template attached as Exhibit A or generated by `contract_generator.py --type=memo_of_jv`).

Either party may record the Memorandum in the {{property_county}} County recorder's office to give constructive notice of the JV's interest in the Property. The Memorandum clouds title until closing or release.

The Memorandum will be released by the recording party within five (5) business days of:
- Closing of the assignment to the Designated Investor/End-Buyer; OR
- Mutual written termination of this Agreement; OR
- A court order requiring release.

If the recording party fails to release as required, that failure is itself a breach subject to Section 6.

### 8. ASSIGNMENT FEE DISCLOSURE TO END-BUYER

The end-buyer shall be advised that this is a JV between two wholesalers and that the assignment fee is being split between them. This is not a hidden fee; it appears on the closing statement as "Assignment Fee to {{jv_entity_or_dba}}" and is then disbursed per Section 3. Hiding the JV from the end-buyer or seller is a breach of this Agreement and a breach of state law in most operating jurisdictions.

### 9. TITLE COMPANY / ESCROW AGENT

The parties shall use **{{title_company}}** as the closing/escrow agent. Default expectation: title fees are paid by the BUYER through normal closing costs. Neither party to this JV pays the title company on the wholesale side.

**If the title company requires a wholesale-side fee:** the parties shall first negotiate to move the fee to the buyer or seller side. If unsuccessful, the parties shall accept the fee, deduct it from the gross assignment fee on the closing statement BEFORE the Section 3 split, and proceed to close -- so long as the resulting net to the parties remains positive.

**The deal closes unless** (a) wholesale-side fees would push the parties' combined net below zero, or (b) the structure is illegal (RESPA Section 8 referral kickbacks, advance fees demanded before work performed, undisclosed deductions surfaced at the table after execution). In either case the parties may walk and substitute a different title company or void this Agreement without breach.

The parties expressly agree this JV does not break over title-fee disputes when the deal is profitable. Revenue beats principle until a clear pattern emerges that justifies tighter standards in a future JV.

### 10. STATE COMPLIANCE (PROPERTY GOVERNS)

This Agreement shall be governed by, and the underlying assignment performed in compliance with, the laws of **the state where the Property is located** ({{property_state}}). The state-specific addendum for {{property_state}} (loaded automatically by `contract_generator.py` when state matches) is incorporated by reference and controls in any conflict.

If the underlying Purchase and Sale Agreement does not satisfy the property state's wholesaling rules (including but not limited to OH HB 132/HB 226 disclosure, GA OCGA 44-14-13 EMD trust account routing, or TX SB 1577 marketing-piece scope), the parties shall cure the deficiency in writing before closing.

### 11. CONFIDENTIALITY

All deal-specific information shared between the parties is confidential and may not be disclosed except to legal counsel, accountant, or as required by law. This obligation survives termination of this Agreement for the same 24-month period as Section 5.

### 12. NO EMPLOYMENT, AGENCY, OR PARTNERSHIP

Nothing in this Agreement creates an employer/employee, principal/agent, or general partnership relationship. Neither party may bind the other to any third party. This is a single-purpose JV for one transaction only.

### 13. INDEPENDENT COUNSEL

Each party acknowledges they had the opportunity to have this Agreement reviewed by independent legal counsel and either did so or knowingly waived that right. Lucrex, Justine Park, or any Everlight agent is **not the counterparty's lawyer**. Neither party will later argue this Agreement is invalid because they did not have a lawyer.

### 14. NOTICES

All notices shall be in writing, delivered by:
- Email to the address shown above (effective on send if no bounce within 24 hours), AND
- Either certified mail or Documenso/HelloSign envelope with read receipt.

Notice to Everlight Ventures: **operations@everlightventures.io** with copy to **marquise@everlightventures.io**.

### 15. DISPUTE RESOLUTION & VENUE

Any dispute arising from this Agreement shall be resolved by:

(a) **Step 1 -- 7-day written negotiation.** Either party may initiate by sending a written notice of claim. Parties shall meet (in person or by video) within 7 days.

(b) **Step 2 -- Mediation** in the county where the Property is located, with a mediator mutually selected within 14 days of failed negotiation. Each party bears their own cost; mediator fees split 50/50.

(c) **Step 3 -- Litigation.** If mediation fails, suit may be filed in the state or county court of the county where the Property is located. The prevailing party is entitled to attorney fees and costs in addition to any other remedy.

The parties expressly do **not** consent to arbitration. Either party retains the right to file suit immediately for injunctive relief (e.g., to halt a closing that violates Section 4 or 5) without first completing Steps 1-2.

### 16. INJUNCTIVE RELIEF AVAILABLE

The parties acknowledge that money damages alone may be inadequate for breach of Section 4, 5, 7, or 11, and that the non-breaching party is entitled to seek a temporary restraining order, preliminary injunction, or specific performance from a court of competent jurisdiction without posting bond, in addition to any other remedy.

### 17. SEVERABILITY

If any provision is held invalid or unenforceable, the remainder of this Agreement remains in effect. The court is requested to reform the invalid provision to the closest enforceable version.

### 18. ENTIRE AGREEMENT

This Agreement (with the underlying Purchase and Sale Agreement, the Memorandum of JV, and the state-specific addendum incorporated by reference) is the entire agreement between the parties. No prior or contemporaneous oral or written promise survives execution. Modifications must be in writing signed by both parties.

### 19. ELECTRONIC EXECUTION & COUNTERPARTS

This Agreement may be signed in counterparts via Documenso, HelloSign, DocuSign, or any other electronic signature platform compliant with the federal ESIGN Act and the operating state's UETA. Counterparts together constitute one Agreement. PDF signatures are originals.

### 20. SIGNATURES

**Party A:**

Signature: ___________________________  Date: ___________
Print Name: {{party_a_signer_name}}, {{party_a_signer_title}}
For: {{party_a_name}}

**Party B:**

Signature: ___________________________  Date: ___________
Print Name: {{party_b_signer_name}}, {{party_b_signer_title}}
For: {{party_b_name}}

---

## Exhibit A -- Memorandum of Joint Venture (Recordable Form)

**TO BE EXECUTED CONCURRENTLY WITH THIS AGREEMENT.**

**Recording requested by and after recording return to:**
{{recording_party_name}}
{{recording_party_address}}

---

**MEMORANDUM OF JOINT VENTURE**

THIS MEMORANDUM is made on {{effective_date}} between **{{party_a_name}}** and **{{party_b_name}}** ("the Parties").

The Parties have entered into a Joint Venture Agreement of even date relating to the real property described below. This Memorandum is recorded to give constructive notice of the Parties' interests.

**Property:** {{property_address}}, {{property_city}}, {{property_state}} {{property_zip}}

**County:** {{property_county}}

**Parcel ID / Tax Map No.:** {{parcel_id}}

**Term of Joint Venture Interest:** From {{effective_date}} until closing of the underlying assignment to the designated end-buyer or until released by the recording party.

The full Joint Venture Agreement is held by the Parties and is available on request to any party with a legitimate title interest. This Memorandum does not modify the underlying Joint Venture Agreement.

**Party A:**
Signature: ___________________________
Print: {{party_a_signer_name}}
Notary acknowledgment required.

**Party B:**
Signature: ___________________________
Print: {{party_b_signer_name}}
Notary acknowledgment required.

---

## Variables loaded by `contract_generator.py --type=jv`

```
{{effective_date}}, {{property_address}}, {{property_city}}, {{property_state}}, {{property_zip}}, {{property_county}}, {{legal_description}}, {{parcel_id}},
{{party_a_name}}, {{party_a_address}}, {{party_a_phone}}, {{party_a_email}}, {{party_a_role}}, {{party_a_contribution}}, {{party_a_split_pct}}, {{party_a_amount}}, {{party_a_signer_name}}, {{party_a_signer_title}},
{{party_b_name}}, {{party_b_address}}, {{party_b_phone}}, {{party_b_email}}, {{party_b_role}}, {{party_b_contribution}}, {{party_b_split_pct}}, {{party_b_amount}}, {{party_b_signer_name}}, {{party_b_signer_title}},
{{end_buyer_name}}, {{introducing_party}}, {{psa_date}}, {{total_assignment_fee}}, {{liquidated_damages_floor}},
{{title_company}}, {{jv_entity_or_dba}}, {{recording_party_name}}, {{recording_party_address}}
```

`liquidated_damages_floor` defaults to $25,000 if not supplied.

---

**FILING CHECKLIST FOR EVERY JV USE:**

1. Send Memorandum of JV to county recorder within 24 hours of execution. Cost: $20-50 typical. The cloud on title is your single biggest leverage.
2. Save signed counterparts in `client_files/{{deal_id}}/jv_agreement_signed.pdf` + the Memorandum receipt PDF.
3. If counterparty later attempts to circumvent: file the Memorandum (if not already), send 7-day notice of breach via Documenso, then file in {{property_county}} county court for injunctive relief + Section 6 damages.
4. The counterparty's lender (if any) will see the recorded Memorandum during title work. Their title insurance underwriter will demand release before clearing the file. That is your leverage to enforce the JV terms or kill their deal.

---

**THIS IS A DRAFT TEMPLATE. ATTORNEY REVIEW REQUIRED IN EACH OPERATING STATE BEFORE FIRST USE.**

The aggressive teeth in Sections 5, 6, 7, and 16 are written to maximize deterrence of circumvention. They are enforceable in most US jurisdictions but specific liquidated-damages floors may be reduced by a court if the floor is found unconscionable for a small-fee deal. State-specific counsel review will calibrate the floor and tighten the wording for the operating state's contract law.

**Drafted by:** Lucrex, on behalf of Justine Park (Compliance Gate)
**For:** Everlight Ventures, Marquise Smith
**Reviewing counsel:** _________________________ (sign here when retained)
