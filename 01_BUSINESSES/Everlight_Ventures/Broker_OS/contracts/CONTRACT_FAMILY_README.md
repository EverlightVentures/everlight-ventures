# Wholesale Contract Family -- README

**Maintained by:** Contract Attorney, Everlight Hive Mind
**Date:** 2026-04-25 (Pacific Time)
**Status:** DRAFT v0.1, internal Hive research, NOT legal advice. External CA + OH counsel must countersign before first live use.

---

## Purpose

This README documents the relationship between the two base contract templates that drive the wholesale pipeline and the state appendices that attach to them conditionally. Without both base contracts in the pipeline, the wholesale model cannot legally function: the purchase contract creates the equitable interest, and the assignment contract transfers it.

---

## The Two-Contract Spine

```
        STEP 5                              STEP 9
  PURCHASE_CONTRACT_BASE.md  ===>     ASSIGNMENT_CONTRACT_BASE.md
  (Seller --> Marquise)               (Marquise --> End Buyer)
        |                                    |
        v                                    v
  Creates equitable interest          Transfers equitable interest
  under doctrine of equitable         (a chose in action) for an
  conversion, plus EMD wired          assignment fee, payable
  to title agency trust account.      through escrow at closing.
        |                                    |
        +------- equitable interest is the spine. -------+
        |
        |  Without Step 5, Marquise has nothing to assign in Step 9.
        |  ORC 4735 / Cal. B&P 10130 unauthorized-brokerage exposure
        |  attaches if assignment occurs without prior equitable interest.
```

---

## Step Map (13-Step Wholesale Flow)

| Step | Action | Document |
|---|---|---|
| 1 | Lead intake (cold mail, cold email, inbound web) | `Wholesale/compliance/state_gates.json` controls channel by state |
| 2 | State / channel compliance gate | Justine Park pre-send filter |
| 3 | Outreach (Piper / Hammer / Cupid agents) | Branded outbound, OH disclosure footer auto-attached |
| 4 | Seller engagement, ARV / repair estimate | CSPA-compliant qualified estimate, data source on file |
| **5** | **Purchase contract signed by seller** | **`PURCHASE_CONTRACT_BASE.md`** + state appendix |
| 6 | EMD wired to title agency trust account | $1,000 minimum or 1% of contract price (OH guardrail) |
| 7 | Inspection / due diligence period | Minimum 10 calendar days, Buyer's right to terminate |
| 8 | Buyer-list match (assignee identified) | Match Maker agent, JV scout |
| **9** | **Assignment contract signed by Marquise + assignee** | **`ASSIGNMENT_CONTRACT_BASE.md`** + state appendix |
| 10 | RPDF / TDS passthrough to assignee unaltered | OH ORC 5302.30, CA Civ. Code 1102 |
| 11 | Title clearance, payoff, closing scheduled | [TITLE_COMPANY] holds the file |
| 12 | Closing, deed recorded, assignment fee paid through escrow | HUD-1 / closing disclosure on file |
| 13 | Post-close audit, retention 7 years | Justine quarterly audit, Supabase mirror |

---

## State Appendix Attachment Logic

State appendices attach to BOTH base contracts (the purchase contract AND the assignment contract). They are not exclusive to one or the other. The pdf_autofill state-aware fill runs once per generation cycle and attaches the same appendix to both documents in the deal folder.

### Currently Drafted Appendices

| Appendix | File | Attaches When |
|---|---|---|
| CA 1695 (Home Equity Sales Contract) | `Wholesale/compliance/CA_1695_APPENDIX.md` | CA 1-to-4 unit residential AND principal residence AND default condition (NOD recorded, missed payment disclosed, or AB 519 expanded "in default"). Appendix BLOCKS default-stage transactions per current Hive posture, attaches as a fallback if a default condition is discovered post-engagement. |
| OH Principal-Buyer + License Status | `Wholesale/compliance/OH_DISCLOSURE_APPENDIX.md` | Any property located in Ohio. No sub-trigger. Geographic detection at lead-creation time triggers attachment. |

### Appendices To Be Drafted

The following states have active wholesale pipeline activity or are on the 90-day roadmap and will require state appendices before first transaction in that state:

- **TX** -- Senate Bill 140 cold-SMS prohibition (already enforced at outreach gate). Purchase / assignment contract appendix needed for property condition disclosure rules and TREC Form 1-4 interaction.
- **FL** -- F.S. 475 brokerage exemption analysis, F.S. 689 statute of frauds, mandatory deed-prep attorney custom in some counties.
- **NC** -- HB 797 wholesaler-marketing prohibition (already enforced at outreach gate). Out-of-state wholesale entirely BLOCKED in NC under current posture.
- **GA** -- O.C.G.A. 43-40 brokerage exemption analysis, county-specific recording rules.
- **TN** -- Tenn. Code 66-5 disclosure form passthrough, Tenn. Code 62-13 wholesaler exemption boundary.
- **AZ** -- A.R.S. 32-2155 brokerage exemption analysis.

External counsel countersign required before each new state goes live.

### Attachment Mechanics (pdf_autofill)

1. Lead is scored and routed; state is determined from property address.
2. `pdf_autofill` resolves the state-aware token set:
   - `[STATE]` -> "California" / "Ohio" / etc.
   - `[STATE_EMD_RULES]` -> CA B&P 10145 paragraph for CA, ORC 3953 paragraph for OH, etc.
   - `[STATE_DISCLOSURE]` -> CA 1102 TDS reference for CA, ORC 5302.30 RPDF reference for OH.
   - `[STATE_INSPECTION_PERIOD]` -> state-default minimum days, never less than 10.
   - `[STATE_CLOSING_REQUIREMENTS]` -> deed-prep attorney requirement (where applicable), wet-funding rule, etc.
   - `[STATE_ESCAPE_CLAUSES]` -> state-mandated rescission windows, foreclosure-rescue carve-outs.
3. State-aware fill checks the state code and pulls the corresponding appendix from `Wholesale/compliance/`.
4. The appendix is appended to BOTH `PURCHASE_CONTRACT_BASE.md` and `ASSIGNMENT_CONTRACT_BASE.md` in the deal folder.
5. Files are stored at `Broker_OS/contracts/generated/{STATE}/{deal_id}/`:
   - `01_purchase_contract.pdf`
   - `01a_state_appendix.pdf`
   - `02_emd_wire_confirm.pdf`
   - `03_property_disclosure.pdf` (RPDF / TDS / equivalent)
   - `04_assignment_contract.pdf`
   - `04a_state_appendix.pdf` (same appendix, mirrored)
   - `05_outbound_log.json`
   - `06_closing_statement.pdf`
   - `07_arv_backup.pdf`

---

## Token Convention (Shared Across Both Base Contracts)

The two base contracts use an identical token convention so `pdf_autofill` can substitute against the same variable map:

| Token | Source | Example |
|---|---|---|
| `[DATE]` | system clock at generation, Pacific Time | 2026-04-25 |
| `[PROPERTY_ADDRESS]` | lead record | 1234 Main St, Cleveland, OH 44101 |
| `[COUNTY]` | lead record (geocode) | Cuyahoga |
| `[STATE]` | lead record (geocode) | Ohio |
| `[PARCEL_ID]` | county assessor lookup | 123-45-678 |
| `[LEGAL_DESCRIPTION]` | county recorder lookup | Lot 12, Block 3, Map ... |
| `[BUYER_ADDRESS]` / `[BUYER_PHONE]` / `[BUYER_EMAIL]` | Marquise's operator profile | (purchase contract) |
| `[SELLER_NAME]` / `[SELLER_ADDRESS]` / `[SELLER_PHONE]` / `[SELLER_EMAIL]` | lead record | |
| `[ASSIGNEE_NAME]` / `[ASSIGNEE_ADDRESS]` / `[ASSIGNEE_PHONE]` / `[ASSIGNEE_EMAIL]` | buyer-list match | (assignment contract) |
| `[PURCHASE_PRICE]` | negotiated, on contract | 80000 |
| `[EMD_AMOUNT]` | $1,000 minimum or 1% of price, whichever greater | 1000 |
| `[ASSIGNMENT_FEE]` | spread between purchase and assignment price | 8500 |
| `[ORIGINAL_PURCHASE_PRICE]` | mirrors `[PURCHASE_PRICE]` for assignment-side disclosure | (assignment contract) |
| `[TITLE_COMPANY]` | seller-selected from offered list of 2-3 | Bonded Title Cleveland |
| `[STATE_EMD_RULES]` | state-aware fill | "ORC 3953" / "Cal. B&P 10145" |
| `[STATE_DISCLOSURE]` | state-aware fill | "ORC 5302.30 RPDF" / "Cal. Civ. Code 1102 TDS" |
| `[STATE_INSPECTION_PERIOD]` | state-aware fill, minimum 10 days | (purchase contract) |
| `[STATE_CLOSING_REQUIREMENTS]` | state-aware fill | (deed prep attorney, wet-funding, etc.) |
| `[STATE_ESCAPE_CLAUSES]` | state-aware fill | (assignment contract) |
| `[CLOSING_DATE]` | computed from EMD clear date + closing days | |
| `[CLOSING_DAYS]` | default 14, configurable | 14 |
| `[INSPECTION_DAYS]` | default 10, never less | 10 |
| `[FINANCING_DAYS]` / `[APPROVAL_DAYS]` | only if applicable | (assignment contract) |
| `[NEGOTIATION_LANGUAGE]` | lead record, default English | English |
| `[ARBITRATION_VENUE]` | state default, JAMS | Cleveland, OH |

The token list is shared. Any new token introduced in one base contract MUST be added to the other if it could plausibly attach.

---

## Compliance Spine (Why This Matters)

The two-contract structure is the operational compliance posture for unauthorized-brokerage risk. Without the purchase contract:

1. **No equitable interest.** Doctrine of equitable conversion requires a written purchase contract plus EMD. No contract = no equitable interest = nothing to assign.
2. **Unauthorized brokerage exposure.** Marketing and assigning a property without holding equitable interest is brokerage of someone else's property under ORC 4735.02 (OH), Cal. B&P 10130 (CA), and parallel statutes. Administrative and in aggravated cases criminal exposure.
3. **HB 226 / HB 132 fact pattern.** The 2024 Ohio wholesaler-scrutiny update specifically targets wholesalers who market without equitable interest. The purchase contract on file is the documentary defense.
4. **Lapsed CA license + holding-out risk.** The principal-buyer disclosure in Paragraph 9 of the purchase contract is the affirmative disclosure that the disclosure section of the OH appendix mandates. Without the purchase contract carrying the disclosure, the four-surface placement requirement in OH_DISCLOSURE_APPENDIX.md fails on Surface 1 (the contract itself).
5. **Step 5 of the 13-step flow.** The pipeline's automated handoff from Piper (outreach) to Hammer (follow-up) to closing assumes Step 5 produces an executed PDF. Without `PURCHASE_CONTRACT_BASE.md`, Step 5 is a manual gap and the pipeline cannot run autonomously.

---

## File Locations

| Document | Path |
|---|---|
| Purchase contract base | `01_BUSINESSES/Everlight_Ventures/Broker_OS/contracts/PURCHASE_CONTRACT_BASE.md` |
| Assignment contract base | `01_BUSINESSES/Everlight_Ventures/Broker_OS/contracts/ASSIGNMENT_CONTRACT_BASE.md` |
| CA 1695 appendix | `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/CA_1695_APPENDIX.md` |
| OH disclosure appendix | `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/OH_DISCLOSURE_APPENDIX.md` |
| OH equitable-interest opinion | `01_BUSINESSES/Everlight_Ventures/Wholesale/legal/HIVE_OPINION_OH_EQUITABLE_INTEREST.md` |
| State outreach gates | `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/state_gates.json` |
| Generated deal folders | `01_BUSINESSES/Everlight_Ventures/Broker_OS/contracts/generated/{STATE}/{deal_id}/` |
| Audit reports | `01_BUSINESSES/Everlight_Ventures/Broker_OS/contracts/audits/AUDIT_{YYYY-MM-DD}.md` |

---

## Re-Review Triggers

This README is operational until any one of the following fires:

1. A new state appendix is drafted and added to the family.
2. Either base contract is materially edited (paragraph added, removed, or restructured).
3. External CA or OH counsel countersignature changes the operational posture.
4. A regulatory development (state legislation, federal rule, court decision) affects the equitable-interest doctrine, the principal-buyer defense, or the assignment-fee mechanism.
5. Every 18 months from the date of last review, regardless of the above. The 18-month clock from this filing date expires 2027-10-25.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**
**DRAFT v0.1, internal Hive posture only. External CA + OH counsel must countersign before first live use.**

Contract Attorney, Everlight Hive Mind
2026-04-25, Pacific Time
