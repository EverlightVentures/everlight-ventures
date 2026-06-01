# DEAL PROTECTION AND CLOSING SOP -- Everlight Ventures Wholesale Division

**Version:** 1.0
**Effective Date:** 2026-03-24
**Prepared by:** Justine Park (Legal/Compliance) with contract_attorney AI audit
**Reviewed by:** Marcus Cole (COO)

**DISCLAIMER:** This document is for internal operational guidance only. It is NOT legal advice. All contracts and procedures should be reviewed by a licensed California attorney before execution. Everlight Logistics LLC should retain a real estate attorney admitted to the California Bar for deal-specific review.

---

## TABLE OF CONTENTS

1. [Business Model Overview](#1-business-model-overview)
2. [Assignment Contract Protection Clauses](#2-assignment-contract-protection-clauses)
3. [Earnest Money Structure and Timeline](#3-earnest-money-structure-and-timeline)
4. [Escape Clauses -- How We Back Out](#4-escape-clauses----how-we-back-out)
5. [California Wholesale Compliance](#5-california-wholesale-compliance)
6. [Title Company Requirements Per Market](#6-title-company-requirements-per-market)
7. [Assignment vs. Double Close](#7-assignment-vs-double-close)
8. [Step-by-Step Closing Process](#8-step-by-step-closing-process)
9. [Role Assignments -- Who Does What](#9-role-assignments----who-does-what)
10. [Template Clauses for Every Contract](#10-template-clauses-for-every-contract)
11. [Harrison's Pre-Close Checklist](#11-harrisons-pre-close-checklist)
12. [Risk Register and Escalation](#12-risk-register-and-escalation)

---

## 1. BUSINESS MODEL OVERVIEW

Everlight Ventures operates a real estate wholesale business:

1. **We find distressed or motivated sellers** in 8 target markets (STL, Cleveland, DFW, Atlanta, Phoenix, Charlotte, Jacksonville, Las Vegas).
2. **We get the property under a purchase and sale agreement (PSA)** at a price below market value.
3. **We assign that contract to a cash buyer** for an assignment fee (typically $5,000--$25,000).
4. **We never own the property.** We sell the contract, not the house.

The legal posture is a **sole proprietorship**: **Richard Gee**, an individual, doing business as **Everlight Ventures** (a California sole proprietor). The Everlight Ventures LLC is in reinstatement-pending status and is NOT the contracting entity until reinstated -- every contract is signed by Richard Gee personally until then. Canonical source: `entity_identity.py` / `BUSINESS_ENTITY_STATUS.md`.

**Critical distinction:** We are NOT acting as real estate agents or brokers. We are principals -- we are the buyer in the original PSA, and we assign our contractual rights to a third party. This is a legal and important distinction under California law.

---

## 2. ASSIGNMENT CONTRACT PROTECTION CLAUSES

### 2a. Preventing Buyer Backout

The following clauses MUST appear in every Assignment of Contract Agreement between Everlight and the end buyer (assignee):

#### Non-Refundable Earnest Money Deposit (EMD)

> **EARNEST MONEY DEPOSIT.** Within two (2) business days of the execution of this Assignment Agreement, Assignee shall deposit the sum of $_______ ("Earnest Money Deposit" or "EMD") with the Escrow Agent identified in Section ___ of this Agreement. The EMD shall be held in a trust or escrow account by the Escrow Agent.
>
> **EMD GOES HARD.** The EMD shall become non-refundable upon the expiration of the Inspection Period defined in Section ___. After the EMD goes hard, the EMD shall be released to Assignor (Everlight Logistics LLC) as liquidated damages in the event Assignee fails to close for any reason other than a material title defect or Assignor's default.
>
> **EMD AS CREDIT.** If the transaction closes, the EMD shall be credited toward the Assignment Fee at closing.

**Standard EMD amounts by deal size:**

| Assignment Fee | Recommended EMD | Notes |
|---|---|---|
| $5,000--$10,000 | $1,000--$2,000 | Minimum to keep buyer serious |
| $10,000--$15,000 | $2,500--$3,000 | Standard wholesale range |
| $15,000--$25,000 | $3,000--$5,000 | Larger deals justify larger EMD |
| $25,000+ | $5,000--$10,000 | Institutional buyers expect this |

#### Specific Performance Clause

> **SPECIFIC PERFORMANCE AND REMEDIES.** In the event Assignee fails or refuses to close the transaction contemplated by this Assignment Agreement after the Inspection Period has expired and the EMD has gone hard, Assignor shall be entitled, at Assignor's sole election, to:
>
> (a) Retain the Earnest Money Deposit as liquidated damages, the parties agreeing that actual damages from such breach would be difficult to ascertain and that the EMD represents a reasonable estimate of such damages; OR
>
> (b) Pursue specific performance of this Assignment Agreement, compelling Assignee to close the transaction on the terms set forth herein; OR
>
> (c) Pursue actual damages, including but not limited to the full Assignment Fee, lost opportunity costs, carrying costs incurred during the delay, and reasonable attorneys' fees.
>
> The election of one remedy shall not preclude the pursuit of another if the elected remedy proves inadequate. This provision shall survive termination of this Agreement.

#### Liquidated Damages for Post-Hard EMD Backout

> **LIQUIDATED DAMAGES.** The parties acknowledge that if Assignee fails to close after the Inspection Period has expired, Assignor will suffer damages that are difficult or impossible to calculate with certainty, including lost assignment fees, opportunity costs, damage to seller relationships, and carrying costs. The parties therefore agree that:
>
> (a) If Assignee defaults after the EMD goes hard, Assignor shall retain the full EMD as liquidated damages; and
>
> (b) If Assignor's actual damages exceed the EMD (including but not limited to the full Assignment Fee), Assignor may pursue the difference as additional damages.
>
> This liquidated damages provision is intended as a genuine pre-estimate of damages and is not a penalty. The parties have negotiated this provision at arm's length and agree that it is reasonable under the circumstances as they exist at the time of contract formation.
>
> **California Civil Code Section 1671 compliance:** The parties acknowledge that this liquidated damages clause is valid under California Civil Code Section 1671(b), which provides that a liquidated damages clause in a contract that does not involve a consumer is presumed valid. The amount represents the parties' reasonable endeavor to estimate fair compensation for the harm caused by the breach.

#### Short Inspection / Due Diligence Period

> **INSPECTION PERIOD.** Assignee shall have a period of five (5) calendar days from the Effective Date of this Assignment Agreement (the "Inspection Period") to conduct any and all inspections, investigations, and due diligence on the Property that Assignee deems necessary or desirable.
>
> During the Inspection Period, Assignee may terminate this Agreement for any reason or no reason by delivering written notice to Assignor, in which case the EMD shall be refunded to Assignee in full within three (3) business days.
>
> If Assignee does not deliver written notice of termination before 11:59 PM Pacific Time on the last day of the Inspection Period, the Inspection Period shall be deemed expired, the EMD shall go hard and become non-refundable, and Assignee shall be obligated to close the transaction.
>
> **Time is of the essence.** All deadlines in this Agreement are strict deadlines. No extensions shall be granted without the prior written consent of Assignor.

**Why 5 days, not 7-10:** Cash buyers already know what they are buying. They have their own rehab teams. Five days is industry standard for wholesale assignments. If a buyer asks for more than 7 days, they are not a serious cash buyer -- walk away or require a larger EMD.

---

### 2b. Closing Date and Funding Deadline

> **CLOSING DATE.** The closing of this transaction shall occur on or before _______ (the "Closing Date"), which shall be no later than _____ calendar days from the Effective Date of this Assignment Agreement. Time is of the essence with respect to the Closing Date.
>
> **FUNDING DEADLINE.** Assignee shall deliver cleared funds to the Escrow Agent no later than 12:00 PM Pacific Time on the business day immediately preceding the Closing Date. Failure to deliver funds by this deadline constitutes a material breach.
>
> **EXTENSIONS.** Any extension of the Closing Date requires the prior written consent of Assignor. If Assignor consents to an extension, Assignee shall pay an additional non-refundable deposit of $_______ per day of extension, which shall be credited to the Assignment Fee at closing.

**Standard closing timelines:**

| Buyer Type | Recommended Closing Window | Notes |
|---|---|---|
| Cash buyer (individual) | 14--21 days | Standard for wholesale |
| Cash buyer (fund/institutional) | 10--14 days | They move fast |
| Hard money buyer | 21--30 days | Loan approval adds time |
| Conventional financing | DO NOT ACCEPT | Wholesale only works with cash/hard money |

---

## 3. EARNEST MONEY STRUCTURE AND TIMELINE

### Timeline of Key Dates

```
Day 0: Assignment Agreement executed
Day 0-2: Assignee deposits EMD with Escrow Agent (title company)
Day 0-5: Inspection Period (buyer does due diligence)
Day 5: EMD goes hard (non-refundable)
Day 5-14: Title work, closing prep
Day 12: Funding deadline (cleared funds to escrow)
Day 14: Closing Date (or earlier)
Day 14-16: Assignment fee disbursed to Everlight
```

### EMD Handling Rules

1. **EMD is ALWAYS held by the title company**, never by Everlight directly. This protects both parties and avoids commingling issues.
2. **EMD must be in the form of a cashier's check or wire transfer.** No personal checks.
3. **EMD receipt must be confirmed in writing** by the title company within 24 hours of deposit.
4. **If EMD is not deposited within 2 business days**, the Assignment Agreement is voidable at Everlight's election.
5. **After EMD goes hard**, only two events allow refund: (a) material title defect discovered after the Inspection Period, or (b) Everlight's default under the original PSA.

### EMD Disbursement Scenarios

| Scenario | EMD Goes To | Additional Damages? |
|---|---|---|
| Buyer closes | Credited to Assignment Fee | No |
| Buyer backs out during Inspection Period | Refunded to Buyer | No |
| Buyer backs out after EMD goes hard | Retained by Everlight | Yes -- full Assignment Fee |
| Title defect discovered post-inspection | Refunded to Buyer | No |
| Seller defaults on original PSA | Refunded to Buyer | No -- deal falls apart |
| Everlight cancels (our escape clause) | Refunded to Buyer | No |

---

## 4. ESCAPE CLAUSES -- HOW WE BACK OUT

These clauses go in the **Purchase and Sale Agreement** between Everlight (as buyer) and the seller. They protect Everlight's ability to walk away from a bad deal without losing our earnest money.

### 4a. Inspection Contingency

> **INSPECTION CONTINGENCY.** This Agreement is contingent upon Buyer's satisfaction, in Buyer's sole and absolute discretion, with the results of any inspections, investigations, studies, or assessments of the Property that Buyer elects to conduct during the Inspection Period. The Inspection Period shall be _____ calendar days from the Effective Date.
>
> If Buyer is not satisfied with the results of any inspection for any reason whatsoever, Buyer may terminate this Agreement by delivering written notice to Seller before the expiration of the Inspection Period, and Buyer's earnest money deposit shall be returned in full.
>
> "Inspections" includes but is not limited to: physical inspection of the Property, environmental assessments, structural evaluations, pest inspections, review of property condition disclosures, review of liens and encumbrances, review of zoning and land use restrictions, and analysis of repair costs.

**Key language:** "sole and absolute discretion" -- this means we can cancel for ANY reason during the inspection period. We do not have to justify our decision.

### 4b. Partner Approval / Feasibility Contingency

> **PARTNER APPROVAL CONTINGENCY.** This Agreement is contingent upon the approval of Buyer's managing member, investment partner, or funding source (collectively, "Partner"), which approval shall be obtained within _____ calendar days of the Effective Date (the "Feasibility Period"). If Partner approval is not obtained within the Feasibility Period, Buyer may terminate this Agreement by written notice and Buyer's earnest money deposit shall be returned in full.
>
> Partner approval shall be determined in the sole and absolute discretion of Buyer's Partner. No reason for disapproval need be stated.

**Why this works:** Everlight is an LLC. The "partner" or "managing member" can decline ANY deal. This is our clean exit if we cannot find an end buyer in time. Courts have upheld these clauses because LLCs genuinely do require member approval for major purchases.

**Best practice:** Do NOT use this clause frivolously. If you invoke it on every deal, sellers and title companies will stop working with you. Use it as a genuine escape valve, not a habit.

### 4c. Clear Title Contingency

> **TITLE CONTINGENCY.** This Agreement is contingent upon Buyer's receipt and approval of a preliminary title report from a title company of Buyer's choosing, showing the Property is free and clear of all liens, encumbrances, easements, restrictions, and defects that are not acceptable to Buyer. Buyer shall have _____ calendar days from receipt of the preliminary title report to object to any title exceptions.
>
> If any title exceptions exist that are unacceptable to Buyer and cannot be cured by Seller within ten (10) calendar days of Buyer's written objection, Buyer may terminate this Agreement and Buyer's earnest money deposit shall be returned in full.

**Standard title issues that kill deals:**

- Tax liens (IRS, state, county)
- Mechanics liens from prior contractors
- Judgment liens against the seller
- Unpaid HOA assessments
- Boundary disputes
- Unrecorded easements
- Lis pendens (pending lawsuits)
- Estate/probate issues (seller doesn't have clear authority to sell)

### 4d. Assignment Clause

> **ASSIGNMENT.** Buyer may assign this Agreement, in whole or in part, to any third party (an "Assignee") without the prior consent of Seller. Upon a valid assignment, Assignee shall assume all of Buyer's rights and obligations under this Agreement. Buyer shall remain liable for the performance of this Agreement unless Seller provides written consent to release Buyer from further obligation.
>
> Buyer shall provide Seller with written notice of any assignment within three (3) business days of such assignment, including the name and contact information of the Assignee.

**Critical:** This clause MUST be in the original PSA with the seller. Without it, we cannot wholesale the deal. Some sellers or their agents will try to remove it -- Harrison and Justine must ensure it stays in.

### 4e. Financing Contingency (Backup)

> **FINANCING CONTINGENCY.** This Agreement is contingent upon Buyer obtaining financing on terms acceptable to Buyer, in Buyer's sole discretion, within _____ calendar days of the Effective Date. If Buyer is unable to obtain satisfactory financing within this period, Buyer may terminate this Agreement and Buyer's earnest money deposit shall be returned in full.

**Note:** We typically do not use this clause because we are assigning, not financing. But it is available as an additional escape valve for complex deals where we might need transactional funding for a double close.

---

## 5. CALIFORNIA WHOLESALE COMPLIANCE

### 5a. Do You Need a Real Estate License to Wholesale in California?

**Short answer:** It depends on HOW you wholesale, but the safest position is: Everlight should operate as a principal buyer, not a middleman.

**The legal framework:**

- **California Business and Professions Code Section 10131** defines a "real estate broker" as a person who, for compensation, assists others in buying, selling, or leasing real property. If you are finding deals and connecting buyers and sellers for a fee without being a principal party, you may be operating as an unlicensed broker.

- **The principal exemption:** If you are the actual buyer (your name is on the PSA), and you then assign your contractual rights, you are selling your own interest -- not brokering for someone else. This is legal without a license.

- **Key risk area:** If Everlight never intends to close and is solely in the business of flipping contracts, a court or the California Department of Real Estate (DRE) could argue this constitutes brokerage activity. The defense is that Everlight is a principal who has an equitable interest in the property via the PSA and is selling that interest.

**Best practices for staying on the right side:**

1. **Always be the named buyer** in the original PSA. Never structure the deal as "Seller, meet Buyer -- pay us a fee."
2. **Have genuine intent and ability to close.** Maintain a transactional funding relationship so you CAN close if assignment fails.
3. **Record the memorandum of contract** (optional but helpful) to establish equitable interest.
4. **Do not advertise the property for sale** as if you own it or are the seller. Market the CONTRACT, not the property.
5. **Disclose your intent to assign.** Transparency protects you.

### 5b. California Disclosure Requirements

**Required disclosures in the PSA with the seller:**

1. **Buyer's intent to assign.** The seller must know that "Buyer intends to assign this contract to a third party and will earn a fee from such assignment."

2. **Buyer is not a licensed real estate agent** (unless someone on the team holds a license -- if so, additional disclosures apply under CA Bus & Prof Code 10176).

3. **No fiduciary duty.** The seller must understand that Everlight is acting in its own interest, not as the seller's agent or advisor.

4. **Assignment fee disclosure.** While not explicitly required by statute for principals, best practice is to disclose that "Buyer may earn an assignment fee from the assignment of this contract." This prevents fraud claims.

**Template disclosure paragraph for every PSA:**

> **DISCLOSURE OF INTENT.** Buyer discloses and Seller acknowledges the following:
>
> (a) Buyer is a real estate investment company that acquires properties for investment purposes, including through the assignment of purchase contracts to third-party investors.
>
> (b) Buyer intends to assign this Purchase and Sale Agreement to a third-party buyer (the "Assignee") and will earn an assignment fee in connection with such assignment.
>
> (c) Buyer is NOT a licensed real estate broker or agent and is NOT acting as Seller's agent, fiduciary, or advisor. Buyer is acting solely as a principal in this transaction, in Buyer's own interest.
>
> (d) Seller is encouraged to seek independent legal counsel and/or representation by a licensed real estate agent before executing this Agreement.
>
> (e) The purchase price offered by Buyer may be below the fair market value of the Property. Seller has the right to obtain independent appraisals, comparable sales data, or other opinions of value before accepting this offer.

### 5c. AB 1850 and Other California Wholesale Laws

**AB 1850 (2020):** This bill primarily codified the ABC test for independent contractor classification (reinforcing AB5). It is relevant to Everlight's relationship with any contractors or agents we engage, but does not directly regulate wholesale transactions.

**SB 1079 (2020):** Gives tenants and certain entities the right to match the winning bid on foreclosed properties at auction. Relevant if Everlight acquires properties at auction.

**Key statutes to monitor:**

| Statute | What It Covers | Relevance |
|---|---|---|
| CA Bus & Prof Code 10131 | Definition of broker activity | Defines what requires a license |
| CA Bus & Prof Code 10176 | Grounds for discipline of licensees | Applies if anyone on team is licensed |
| CA Civil Code 1102-1102.18 | Transfer Disclosure Statement (TDS) | Required for residential sales (seller obligation) |
| CA Civil Code 1671 | Liquidated damages enforceability | Validates our EMD-as-damages clauses |
| CA Civil Code 1624 | Statute of Frauds | Real estate contracts must be in writing |
| CA Penal Code 532a | Theft by false pretenses | Anti-fraud -- do not misrepresent your role |

### 5d. Anti-Fraud Provisions

Include the following in every contract to protect Everlight from fraud claims:

> **ANTI-FRAUD DISCLOSURE AND REPRESENTATIONS.**
>
> (a) Buyer represents that it is a real estate investment company and that this transaction is an arm's-length business transaction.
>
> (b) Buyer has not made and does not make any representations regarding the value of the Property, the condition of the Property, or the potential resale value of the Property.
>
> (c) Seller has had the opportunity to seek independent legal counsel, a licensed real estate agent, or an appraiser before entering into this Agreement.
>
> (d) Seller is entering into this Agreement voluntarily, without duress, undue influence, or coercion.
>
> (e) Seller understands that the purchase price may be below the fair market value of the Property and has accepted this price freely.
>
> (f) Buyer has not engaged in any conduct intended to deceive, defraud, or take unfair advantage of Seller.
>
> (g) Seller acknowledges that Buyer may profit from this transaction through resale, assignment, or other disposition of the Property or Buyer's rights under this Agreement.

---

## 6. TITLE COMPANY REQUIREMENTS PER MARKET

### What We Need From a Title Company

1. **Willingness to handle assignment transactions.** Many title companies will NOT process assignments because they view them as risky or unusual. We need title companies that understand wholesale.
2. **Escrow services.** EMD must be held in a trust account by the title company.
3. **Preliminary title report** within 5--7 business days of opening escrow.
4. **Closing coordination** -- title company handles the closing, records the deed, and disburses funds.
5. **Assignment fee disbursement.** The title company must be willing to add a line item on the settlement statement (HUD-1 or ALTA) for the assignment fee payable to Everlight.

### Double Close Capability

Some title companies will not process assignments but WILL do a "double close" (also called simultaneous close or back-to-back close). In a double close:

- **Close 1 (A-to-B):** Everlight buys from Seller. Title transfers to Everlight.
- **Close 2 (B-to-C):** Everlight immediately sells to End Buyer. Title transfers to End Buyer.
- Both closings happen the same day, often within hours.
- Everlight may need **transactional funding** to close the A-to-B side (typically 1--3 days of funding at 1--2% of purchase price).

See TITLE_COMPANY_RESEARCH.md for specific title companies by market.

### Timeline: Signed Contract to Close

| Phase | Timeline | Responsible |
|---|---|---|
| PSA signed with seller | Day 0 | Harrison Knox |
| Earnest money deposited | Day 0--3 | Harrison Knox |
| Preliminary title report ordered | Day 1 | Harrison Knox (via title company) |
| Find and assign to end buyer | Day 1--10 | Rex Blackwell / Filter Banks |
| Assignment Agreement signed | Day 5--10 | Justine Park (review), Harrison Knox (execute) |
| Buyer EMD deposited | Day 7--12 | Harrison Knox (confirms with title co) |
| Buyer inspection period | Day 7--12 (5 days) | End Buyer |
| Buyer EMD goes hard | Day 12 | Harrison Knox (confirms) |
| Clear-to-close from title | Day 10--15 | Title company |
| Buyer funds wire to escrow | Day 13 | End Buyer |
| Closing | Day 14--21 | Title company |
| Assignment fee disbursed | Day 14--23 (1--2 days post-close) | Carlos Moreno (confirms receipt) |

### Who Pays What at Closing

| Cost | Typically Paid By | Notes |
|---|---|---|
| Title insurance (owner's policy) | Varies by state/custom | See market-specific notes below |
| Title search | Buyer (or split) | $200--$400 |
| Escrow fee | Split 50/50 (or buyer pays) | $500--$1,500 |
| Recording fees | Buyer | $50--$200 |
| Transfer taxes | Varies by state | Some states have none |
| Assignment fee | Buyer (to Everlight) | This is our profit |
| Seller closing costs | Per PSA | Negotiate seller to pay their own |
| Transactional funding (double close only) | Everlight | 1--2% for 1--3 days |

**State-specific closing customs:**

| Market | Title Insurance Paid By | Transfer Tax | Notes |
|---|---|---|---|
| St. Louis, MO | Seller (custom) | ~$1.50/$500 | Missouri -- seller pays title insurance by custom |
| Cleveland, OH | Seller or negotiable | $4/$1,000 (conveyance fee) | Varies by county |
| Dallas, TX | Seller (custom) | None | Texas has no state transfer tax |
| Atlanta, GA | Negotiable | $1/$1,000 | Georgia -- negotiable |
| Phoenix, AZ | Seller (custom in Maricopa) | $2 flat recording fee | Arizona -- seller typically pays |
| Charlotte, NC | Buyer pays lender's, Seller pays owner's | $2/$500 (excise tax) | North Carolina custom |
| Jacksonville, FL | Seller (custom) | $0.70/$100 (doc stamps) | Florida -- seller pays doc stamps by custom |
| Las Vegas, NV | Seller (custom in Clark County) | $1.95/$500 (transfer tax) | Nevada -- seller pays by custom |

---

## 7. ASSIGNMENT VS. DOUBLE CLOSE

### When to Use Assignment (Preferred)

- Assignment fee is under $10,000 or less than 20% of the purchase price
- Title company is comfortable with assignments
- Seller knows about the assignment and does not object
- End buyer is not concerned about seeing Everlight's contract price

**Pros:** No transactional funding needed, lower closing costs, faster, simpler.

**Cons:** Assignment fee is visible on settlement statement (buyer and seller see your profit), some title companies refuse to process assignments, some sellers object when they see the markup.

### When to Use Double Close

- Assignment fee is large (over $10,000 or more than 20% of purchase price)
- You do not want seller or buyer to see your spread
- Title company does not handle assignments
- More complex deal structure (multiple parcels, multiple sellers, etc.)

**Pros:** Privacy -- neither seller nor buyer sees your profit. More title companies accept double closes. Looks more professional for larger deals.

**Cons:** Requires transactional funding (1--2% cost). Two sets of closing costs. More paperwork. Slightly longer process.

### Transactional Funding Sources

If we need short-term funding for double closes:

| Source | Cost | Terms | Notes |
|---|---|---|---|
| Best Transaction Funding | 1--2% of loan amount | 1--3 day terms | besttransactionfunding.com |
| Fund That Flip / Kiavi | Varies | Short-term bridge loans | kiavi.com |
| Private money lender (local) | 2--3 points | Case by case | Build relationships in each market |
| Self-fund | $0 | If capital available | Best option if we have the cash |

---

## 8. STEP-BY-STEP CLOSING PROCESS

### Phase 1: Deal Acquisition (Days 0--3)

1. **Harrison Knox** negotiates PSA with seller, with all Everlight protection clauses (inspection, partner approval, title, assignment).
2. **Justine Park** reviews every PSA before Harrison signs. Checks for: assignment clause present, all escape clauses intact, proper disclosure language, correct entity name (Everlight Logistics LLC and/or assigns).
3. **Harrison Knox** deposits EMD with title company within 3 business days. Amount: typically $500--$1,000 on the seller side (keep exposure low).
4. **Harrison Knox** orders preliminary title report from title company. Expected turnaround: 3--7 business days.
5. **Samuel Navarro** creates deal file in Broker OS. Uploads signed PSA, EMD receipt, title order confirmation.

### Phase 2: Disposition / Finding End Buyer (Days 1--10)

6. **Rex Blackwell** and **Filter Banks** market the deal to our buyer list (see REAL_CASH_BUYERS.md). Channels: InvestorLift, direct outreach, REIA groups, Facebook groups.
7. **Piper Reeves** sends buyer outreach emails for larger deals.
8. Interested buyers submit proof of funds (POF) and sign the Assignment Agreement.
9. **Justine Park** reviews Assignment Agreement. Confirms: EMD amount, inspection period length, closing date, liquidated damages clause, all protection clauses.
10. **Harrison Knox** collects buyer EMD (wired to title company).

### Phase 3: Due Diligence and Title (Days 5--15)

11. **Harrison Knox** monitors buyer inspection period. Tracks expiration date.
12. If buyer terminates during inspection: refund EMD, find next buyer (go back to Phase 2).
13. If buyer does NOT terminate: EMD goes hard. Harrison confirms with title company.
14. **Justine Park** reviews preliminary title report. Flags any issues (liens, encumbrances, clouds).
15. Title company works to clear any title exceptions. Harrison coordinates between title company and seller.
16. **Samuel Navarro** ensures all disclosures are signed: seller disclosure, buyer acknowledgment, assignment notice.

### Phase 4: Closing (Days 14--21)

17. Title company issues "clear to close" once title is clean and all documents are in order.
18. **Harrison Knox** confirms buyer has wired closing funds to escrow.
19. Closing occurs. Title company records the deed, disburses funds.
20. Assignment fee is wired to Everlight Logistics LLC bank account.
21. **Carlos Moreno** confirms receipt of assignment fee. Reconciles with deal file.
22. **Samuel Navarro** archives completed deal file with all documents.

### Phase 5: Post-Close (Days 21--30)

23. **Carlos Moreno** records revenue in accounting. Issues any applicable 1099s.
24. **Chart Dawson** updates pipeline analytics in Broker OS dashboard.
25. **Harrison Knox** sends thank-you to seller and buyer. Requests testimonials.
26. **Marcus Cole** reviews deal P&L and team performance.

---

## 9. ROLE ASSIGNMENTS -- WHO DOES WHAT

### Justine Park -- Legal & Compliance (PRIMARY ROLE)

**Title:** General Counsel / Compliance Officer
**Reports to:** Marcus Cole (COO)

**Responsibilities:**
- Reviews EVERY contract before any party signs. No exceptions.
- Adds and verifies protection clauses (EMD, liquidated damages, inspection period, assignment clause).
- Ensures California disclosure compliance on every deal.
- Reviews preliminary title reports for legal issues.
- Maintains relationships with title companies in all 8 markets.
- Monitors changes in California real estate law affecting wholesale operations.
- Conducts quarterly audit of all contract templates.
- Escalates any deal with unusual legal risk to outside counsel.
- Maintains the "approved clause library" -- pre-vetted language that Harrison can use.

**Authority:**
- Can VETO any deal for legal/compliance reasons.
- Can require additional disclosures or contract modifications before a deal proceeds.
- Cannot be overridden by Harrison or any non-executive team member.

**Metrics:**
- Contracts reviewed within 24 hours of submission.
- Zero deals closed without Justine's sign-off.
- Zero regulatory complaints or DRE inquiries.

### Harrison Knox -- Deal Closer

**Title:** Director of Acquisitions & Dispositions
**Reports to:** Marcus Cole (COO)

**Responsibilities:**
- Manages every deal from accepted offer through closing.
- Negotiates PSA terms with sellers (price, inspection period, closing date).
- Coordinates with title company (orders title, deposits EMD, schedules closing).
- Tracks all deal deadlines: inspection period expiration, EMD hard date, closing date, funding deadline.
- Collects buyer EMD and confirms deposit with title company.
- Communicates with all parties (seller, buyer, title company, Everlight team).
- Sends closing reminders 5 days, 2 days, and 1 day before each deadline.
- Escalates any deal at risk of falling through to Marcus Cole immediately.

**Authority:**
- Can negotiate deal terms within pre-approved parameters.
- Cannot sign contracts without Justine's review and approval.
- Can request deadline extensions from counterparties.

**Metrics:**
- Close rate: target 70%+ of deals that go under contract.
- Average days from PSA to close: target 21 days or less.
- Zero missed deadlines.
- EMD collection rate: 100% within 2 business days.

### Samuel Navarro -- Compliance Gate / Paralegal

**Title:** Compliance Administrator
**Reports to:** Justine Park

**Responsibilities:**
- Creates and maintains the deal file for every transaction.
- Ensures ALL disclosures are signed before closing (seller disclosure, buyer acknowledgment, assignment notice, anti-fraud disclosure).
- Files paperwork with title company as directed by Harrison.
- Maintains document checklist for every deal (see Section 11).
- Archives completed deal files with all documents for 7-year retention.
- Tracks all signed documents and flags any missing signatures.
- Generates deal status reports for weekly pipeline review.

**Authority:**
- Can hold a deal from closing if required documents are missing.
- Cannot sign contracts on behalf of Everlight.

**Metrics:**
- 100% document completion rate before closing.
- Zero deals closed with missing disclosures.
- Deal files archived within 5 business days of closing.

### Carlos Moreno -- Finance & Audit

**Title:** Controller / Revenue Auditor
**Reports to:** Marcus Cole (COO)

**Responsibilities:**
- Tracks every assignment fee received.
- Reconciles assignment fee wire receipts with bank deposits within 2 business days.
- Records revenue in Everlight's accounting system.
- Generates monthly revenue report for Marcus Cole.
- Issues 1099-MISC or 1099-NEC to any contractors paid in connection with deals.
- Monitors deal profitability (assignment fee minus costs: EMD, title fees, transactional funding, marketing).
- Flags any payment discrepancies or missing funds immediately.

**Authority:**
- Can hold disbursements if accounting does not reconcile.
- Reports directly to Marcus on all financial matters.

**Metrics:**
- All revenue recorded within 48 hours of receipt.
- Monthly P&L report by the 5th of each month.
- Zero unreconciled transactions.

---

## 10. TEMPLATE CLAUSES FOR EVERY CONTRACT

Justine Park must ensure the following clauses appear in EVERY contract Everlight executes. These are the "non-negotiable" clauses.

### In the PSA (Everlight as Buyer, with Seller)

1. **Assignment clause** -- "Buyer and/or assigns" language in the buyer name field AND a standalone assignment clause.
2. **Inspection contingency** -- minimum 10 calendar days, "sole and absolute discretion."
3. **Partner approval contingency** -- 14 calendar days from Effective Date.
4. **Title contingency** -- property must be free and clear of unacceptable encumbrances.
5. **Disclosure of intent** -- Buyer discloses intent to assign and earn a fee.
6. **Anti-fraud representations** -- Seller acknowledges arm's-length transaction, below-market possibility, right to counsel.
7. **Entity name** -- Always "Everlight Logistics LLC and/or assigns" as the buyer.
8. **Governing law** -- State of California (for our internal protections) OR the state where the property is located (for enforceability of property-related terms). Justine decides per deal.
9. **Written modification only** -- No oral amendments.
10. **Time is of the essence** -- All deadlines are strict.

### In the Assignment Agreement (Everlight as Assignor, with End Buyer)

1. **EMD amount and hard date** -- EMD goes hard after 5-day inspection period.
2. **Liquidated damages** -- EMD retained as liquidated damages, plus right to pursue additional damages.
3. **Specific performance** -- Everlight can compel buyer to close.
4. **Short inspection period** -- 5 calendar days max.
5. **Closing date** -- Fixed date, time is of the essence.
6. **Funding deadline** -- Cleared funds 1 business day before closing.
7. **No financing contingency** -- Cash buyers only. No mortgage contingency allowed.
8. **Buyer proof of funds** -- Required before Assignment Agreement is executed.
9. **Extension penalty** -- Additional non-refundable deposit for any extension.
10. **Acknowledgment of assignment fee** -- Buyer acknowledges the assignment fee and agrees it will be paid at closing through the settlement statement.

---

## 11. HARRISON'S PRE-CLOSE CHECKLIST

Harrison Knox runs this checklist 5 business days before every scheduled closing. If any item is not checked, the deal does not close until it is resolved.

### Document Checklist

- [ ] Original PSA -- fully executed, all signatures, all initials
- [ ] Assignment Agreement -- fully executed
- [ ] Buyer Proof of Funds -- verified (bank statement, LOC letter, or fund letter)
- [ ] Buyer EMD -- confirmed deposited and held by title company
- [ ] EMD hard date -- confirmed passed (EMD is non-refundable)
- [ ] Seller Disclosure Statement -- signed by seller
- [ ] Anti-Fraud Disclosure -- signed by seller
- [ ] Assignment Notice to Seller -- delivered and acknowledged
- [ ] Preliminary Title Report -- reviewed by Justine, issues cleared
- [ ] Clear-to-Close letter from title company -- received
- [ ] Settlement Statement (HUD-1 or ALTA) -- reviewed by Justine and Carlos
- [ ] Assignment fee correctly listed on settlement statement
- [ ] Wire instructions for Everlight confirmed with title company
- [ ] Buyer's closing funds -- confirmed wired to escrow (check day before closing)

### Deadline Tracker

- [ ] Inspection period expiration date: __________
- [ ] EMD hard date: __________
- [ ] Title objection deadline: __________
- [ ] Closing date: __________
- [ ] Funding deadline: __________

### Communication Checklist

- [ ] Seller confirmed closing date and time
- [ ] Buyer confirmed closing date and time
- [ ] Title company confirmed all parties are ready
- [ ] Closing agent confirmed location (or virtual closing details)
- [ ] Justine Park has given final legal sign-off
- [ ] Carlos Moreno has confirmed wire instructions are correct

### Post-Close Actions

- [ ] Assignment fee received in bank -- confirmed by Carlos
- [ ] Deal file archived by Samuel
- [ ] Revenue recorded in accounting by Carlos
- [ ] Pipeline updated in Broker OS by Chart Dawson
- [ ] Thank-you communications sent to seller and buyer

---

## 12. RISK REGISTER AND ESCALATION

### Known Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Buyer backs out after EMD goes hard | Medium | Medium | EMD retained as liquidated damages. Specific performance clause. Find backup buyer. |
| Seller backs out after PSA signed | Low | High | Specific performance against seller (if we want to enforce). Lis pendens filed if necessary. |
| Title issues discovered late | Medium | High | Order title immediately (Day 1). Use experienced title companies. |
| DRE inquiry about unlicensed activity | Low | Very High | Maintain principal buyer status. Full disclosures. Retain CA real estate attorney. |
| Assignment fee not disbursed correctly | Low | Medium | Carlos reviews every settlement statement before closing. Wire instructions confirmed. |
| Market downturn -- buyer renegotiates | Medium | Medium | Short closing timelines. EMD goes hard quickly. No financing contingency. |
| Seller claims fraud or misrepresentation | Low | Very High | Full anti-fraud disclosures. Encourage seller to get independent counsel. Written documentation of all communications. |

### Escalation Procedures

| Severity | Trigger | Who Handles | Timeline |
|---|---|---|---|
| LOW | Minor document issue, small deadline adjustment | Harrison Knox | Resolve within 24 hours |
| MEDIUM | Buyer requests extension, title issue found, EMD dispute | Harrison + Justine | Resolve within 48 hours |
| HIGH | Party threatens to walk, legal threat received, DRE inquiry | Marcus Cole + Justine + Outside Counsel | Immediate response |
| CRITICAL | Lawsuit filed, regulatory action, fraud allegation | Marcus Cole + Outside Counsel | Same-day response |

---

## APPENDIX A: RECOMMENDED OUTSIDE COUNSEL

Everlight should retain a California-licensed real estate attorney for:
- Review of all template contracts (one-time, then annual review)
- Deal-specific advice on complex transactions
- Response to any regulatory inquiry from the California DRE
- Any dispute or threatened litigation

**Selection criteria:**
- Licensed in California
- Experience with real estate investment, wholesale, and assignment transactions
- Familiar with California DRE enforcement actions
- Available for rapid response (24-hour turnaround for urgent matters)

**Budget:** $2,000--$5,000 for initial template review. $500--$1,500 per deal for complex transactions. Retainer recommended.

---

## APPENDIX B: ENTITY AND SIGNATURE BLOCK

All contracts should use the following entity identification:

> **EVERLIGHT LOGISTICS LLC**
> a California Limited Liability Company
> doing business as EVERLIGHT VENTURES
>
> By: ___________________________
> Name: [Authorized Signatory]
> Title: Managing Member
> Date: ___________________________

**Important:** Only authorized signatories may execute contracts on behalf of Everlight Logistics LLC. Currently authorized: [CEO name]. Harrison Knox should be authorized via LLC operating agreement amendment if he will be signing PSAs on behalf of the company.

---

*This SOP is a living document. Justine Park is responsible for quarterly review and updates. Next review date: 2026-06-24.*

*This document does not constitute legal advice. Consult a licensed attorney before executing any real estate transaction.*
