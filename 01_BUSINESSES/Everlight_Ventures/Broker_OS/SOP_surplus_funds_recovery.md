# SOP: Surplus Funds Recovery Pipeline

**Division:** Broker OS -- Surplus Recovery Division
**Owner:** Piper Reeves (Outreach), Rex Blackwell (Lead Scout)
**Compliance:** Samuel Navarro (Legal), Justine Park (Ethics Review)
**Last Updated:** 2026-03-24
**Status:** Active

---

## 1. What Are Surplus Funds?

When a county forecloses on a property and sells it at auction, the sale price sometimes exceeds the total liens owed (back taxes, mortgages, etc.). The difference -- called **excess proceeds** or **surplus funds** -- legally belongs to the former property owner.

**Example:**
- Property sold at auction for $180,000
- Total liens owed: $120,000
- Surplus funds: $60,000 (belongs to former owner)

Most former owners never learn these funds exist. Counties are required to hold them but are not required to actively locate owners. The funds sit unclaimed until the statutory deadline passes, at which point they revert to the county.

---

## 2. Legal Basis

### California Statutes

- **Revenue and Taxation Code Section 4675**: Former owners have the right to claim excess proceeds from tax sales. Claims must be filed within one year of the recorded date of the tax deed.
- **Revenue and Taxation Code Section 4676**: Establishes the priority of claims (former owner, then lienholders).
- **Code of Civil Procedure Section 1542**: General waiver provisions -- relevant when signing recovery authorization.
- **Civil Code Section 2295**: Defines agency relationships. Our recovery authorization form creates a limited agency to file claims on behalf of the former owner.

### Surplus Recovery Agent Legality

California law does **not** prohibit surplus recovery agents from charging a contingency fee to locate and assist former owners in claiming excess proceeds. This is a standard finder's fee arrangement, not a legal services engagement.

**Key compliance points:**
- We do NOT provide legal advice. We provide claims assistance.
- We do NOT represent clients in court. If litigation is needed, we refer to licensed counsel.
- Our fee is a contingency commission -- no upfront cost to the owner.
- All agreements must be in writing and clearly state the fee percentage.
- We must disclose that the owner can file the claim themselves at no cost.

---

## 3. Commission Structure

| Surplus Amount | Commission Rate | Rationale |
|----------------|----------------|-----------|
| $10,000 - $25,000 | 30% | Higher effort-to-value ratio; small claims need same work |
| $25,001 - $50,000 | 25% | Sweet spot for both parties |
| $50,001 - $100,000 | 20% | Larger amounts justify lower percentage |
| $100,001+ | 15% | Negotiate per deal; high value justifies reduced rate |

**Minimum commission:** $3,000 per claim (if 30% of surplus is less than $3,000, the claim may not be worth pursuing unless batched with others in the same county).

**Payment timing:** Commission is collected when the county disburses funds to the owner. We invoice the owner per the signed agreement, or the county sends our portion directly if the authorization specifies split disbursement.

---

## 4. Step-by-Step Process

### Phase 1: Lead Generation (Rex Blackwell + Filter Banks)

1. **Run the surplus finder script** weekly:
   ```bash
   cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent
   python surplus_funds_finder.py --county la --min-amount 10000
   ```

2. **Review output** in `surplus_leads.json`. Filter Banks scores leads by:
   - Surplus amount (higher = better)
   - Contact info availability (phone/email found = higher priority)
   - Deadline proximity (closer deadline = more urgent)

3. **County sources to check manually** (if scraper misses data):
   - LA County: https://ttc.lacounty.gov/excess-proceeds/
   - Orange County: https://www.ttc.ocgov.com/
   - San Bernardino: https://www.sbcounty.gov/atc/
   - Riverside: https://www.countyofriverside.us/
   - San Diego: https://www.sdttc.com/

4. **Enrich leads**: The script auto-enriches with property address and skip trace data. For leads missing contact info, run manual skip traces using the URLs generated in the lead notes.

### Phase 2: Outreach (Piper Reeves)

5. **Initial contact** -- Send within 48 hours of finding the lead:
   ```bash
   python surplus_outreach_templates.py --leads-file surplus_leads.json --stage initial --channel email
   ```

6. **Follow-up sequence** (7-touch over 21 days):
   - Day 0: Initial SMS + Email
   - Day 3: Follow-up email (follow_up_1)
   - Day 7: Phone call + voicemail drop
   - Day 10: Follow-up SMS (follow_up_1)
   - Day 14: Second follow-up email (follow_up_2)
   - Day 18: Direct mail letter
   - Day 21: Final phone call

7. **Handle responses**:
   - YES/interested: Move to Phase 3 (signing)
   - Questions: Piper answers directly; escalate legal questions to Samuel
   - STOP/not interested: Immediately remove from outreach, log opt-out
   - No response after 21 days: Mark as "dead" unless deadline is far out

### Phase 3: Signing (Piper Reeves + Samuel Navarro)

8. **Send the Recovery Authorization Form** (see Section 7 below) via:
   - DocuSign or HelloSign for e-signatures
   - Email PDF for print-and-scan
   - In-person if local

9. **Required documents from the owner**:
   - Signed Recovery Authorization Form
   - Government-issued photo ID (driver's license, passport)
   - Proof of former ownership (old deed, tax bill, or we pull county records)

10. **Samuel Navarro reviews** all signed agreements before filing:
    - Verify fee disclosure is clear
    - Confirm owner identity matches county records
    - Check for competing claims or liens

### Phase 4: Filing (Samuel Navarro)

11. **Prepare the county claim**:
    - Complete the county's official claim form (each county has its own)
    - Attach: signed authorization, owner ID, proof of ownership, our W-9
    - Include cover letter requesting split disbursement (owner's share + our commission)

12. **File with the county**:
    - LA County: Mail to Tax Collector's office or file online if available
    - Include tracking number for all mailed claims
    - Log filing date in `surplus_claims_tracker.json`

13. **Follow up with county** every 2 weeks until resolved:
    - Call the county surplus funds department
    - Request status updates in writing
    - Typical processing time: 30-90 days

### Phase 5: Recovery (Cash Carter)

14. **Receive disbursement**: County sends check(s) -- either one check to owner (who then pays us) or split checks per the authorization.

15. **Invoice the owner** if single check was sent:
    - Send invoice for agreed commission percentage
    - Payment due within 10 business days of receiving county funds
    - Accept: wire, ACH, check, Zelle

16. **Log the recovery** in `surplus_claims_tracker.json`:
    ```json
    {
      "parcel_id": "1234-567-890",
      "surplus_amount": 15234.56,
      "commission_rate": 0.30,
      "commission_earned": 4570.37,
      "disbursement_date": "2026-06-15",
      "status": "recovered"
    }
    ```

17. **Post win to Slack** #ft-hunters and #revenue-dashboard.

---

## 5. Compliance Notes

### Mandatory Disclosures (Samuel Navarro / Justine Park)

Every outreach communication and every signed agreement MUST include:

1. **Self-filing disclosure**: "You have the right to file this claim yourself directly with the county at no cost."
2. **Fee disclosure**: "Our fee is [X]% of the recovered amount, payable only upon successful recovery."
3. **No legal advice disclaimer**: "Everlight Ventures provides claims assistance, not legal advice. For legal questions, consult a licensed attorney."
4. **Opt-out language**: All SMS/email must include opt-out instructions.

### Do Not Contact

- If an owner says STOP, NO, or asks not to be contacted: immediately cease all outreach and log the opt-out.
- Maintain an opt-out list at `wholesale_agent/opted_out_surplus.json`.
- Check the opt-out list before every outreach run.

### Record Retention

- Keep all signed agreements for 7 years minimum.
- Keep all outreach logs indefinitely (they are small).
- Keep all county correspondence and claim filings for 7 years.

### CAN-SPAM / TCPA Compliance

- Email: Include physical address and unsubscribe mechanism.
- SMS: Only send to numbers where we have a reasonable basis for contact (they are the named former owner on a public county list).
- Phone: Comply with Do Not Call registry. Check numbers before calling.

---

## 6. Team Responsibilities

| Team Member | Role | Responsibilities |
|-------------|------|------------------|
| **Rex Blackwell** | Lead Scout | Run surplus finder, identify new counties, manual research |
| **Filter Banks** | Lead Scoring | Score and prioritize leads by value and contactability |
| **Piper Reeves** | Outreach | All owner communications (SMS, email, phone, mail) |
| **Samuel Navarro** | Compliance | Review agreements, file claims, county correspondence |
| **Justine Park** | Ethics Review | Audit outreach for compliance, review disclosures |
| **Cash Carter** | Revenue Ops | Track disbursements, invoicing, commission collection |
| **Chart Dawson** | Analytics | Pipeline metrics, conversion rates, revenue forecasting |
| **Hammer Kovacs** | Follow-up | Persistent follow-up on unresponsive leads |

---

## 7. Recovery Authorization Form Template

```
SURPLUS FUNDS RECOVERY AUTHORIZATION

This Agreement is entered into on ____________, 20____ between:

PRINCIPAL (Former Property Owner):
Name: _________________________________
Address: _______________________________
Phone: ________________________________
Email: ________________________________

AGENT (Recovery Firm):
Everlight Ventures
Email: piper@everlightventures.io
Phone: (888) 555-0199

PROPERTY AND CLAIM DETAILS:
County: ________________________________
Parcel Number: _________________________
Property Address: ______________________
Estimated Surplus Amount: $______________

TERMS:

1. AUTHORIZATION: Principal hereby authorizes Agent to act on Principal's
   behalf to file a claim for excess proceeds with the above-named county,
   and to take all reasonable steps necessary to recover said funds.

2. COMPENSATION: Agent shall receive ____% of the gross amount recovered
   as compensation for services rendered. This fee is contingent upon
   successful recovery -- if no funds are recovered, no fee is owed.

3. DISBURSEMENT: Principal authorizes the county to issue [check one]:
   [ ] A single check payable to Principal (Principal will pay Agent's
       fee within 10 business days of receipt)
   [ ] Split checks: one payable to Principal for their share, and one
       payable to Everlight Ventures for the agreed commission

4. DISCLOSURE: Principal acknowledges that:
   a. They have the right to file this claim directly with the county
      at no cost.
   b. Agent is not providing legal advice or legal representation.
   c. Agent's fee is ____% of the recovered amount.
   d. This agreement may be cancelled within 5 business days of signing
      by providing written notice to Agent.

5. TERM: This agreement shall remain in effect until the claim is resolved
   or for a period of 12 months from the date of signing, whichever comes
   first. Either party may terminate with 30 days written notice.

6. GOVERNING LAW: This agreement is governed by the laws of the State
   of California.


_________________________________    _______________
Principal Signature                  Date

_________________________________
Print Name


_________________________________    _______________
Agent Signature                      Date
Piper Reeves, Everlight Ventures
```

---

## 8. How to File a Claim with LA County

1. **Download the claim form** from https://ttc.lacounty.gov/excess-proceeds/ or request by calling (213) 974-2111.

2. **Complete the form** with:
   - Claimant name (the former owner)
   - Parcel number
   - Sale date and amount
   - Basis for claim (former owner of record)

3. **Attach supporting documents**:
   - Signed Recovery Authorization Form
   - Owner's government-issued photo ID (copy)
   - Proof of ownership (grant deed, tax bill, or assessor records)
   - Agent's W-9 (if requesting split disbursement)
   - Power of attorney or authorization letter

4. **Submit the claim** via:
   - Mail: LA County Tax Collector, Excess Proceeds Unit, 225 N Hill St, Room 130, Los Angeles, CA 90012
   - In person at the above address (Mon-Fri, 8 AM - 5 PM)

5. **Processing timeline**: Typically 30-90 days. The county will:
   - Verify the claim and identity
   - Check for competing claims
   - Issue disbursement if approved

6. **Follow up** every 2 weeks by calling (213) 974-2111 and referencing the parcel number.

---

## 9. Scaling to Additional Counties

Once the LA County pipeline is proven, expand to:

1. **Orange County** -- High property values, significant surplus amounts
2. **San Diego County** -- Large market, active auction calendar
3. **San Bernardino County** -- High foreclosure volume
4. **Riverside County** -- Growing market
5. **Sacramento County** -- State capital, good data availability

For each new county:
- Research their specific excess proceeds publication process
- Add a new scraper function in `surplus_funds_finder.py`
- Verify claim filing procedures and forms
- Samuel Navarro to confirm any county-specific regulations

---

## 10. Revenue Projections

**Conservative estimate (first 90 days):**
- 50 leads identified per month across LA County
- 20% contact rate = 10 conversations per month
- 30% sign rate = 3 signed clients per month
- Average surplus: $25,000
- Average commission (25%): $6,250 per recovery
- Monthly revenue potential: $18,750

**Break-even:** First successful recovery covers all operational costs (scripts, skip trace, postage).

**Target:** $10,000/month from surplus recovery within 6 months.
