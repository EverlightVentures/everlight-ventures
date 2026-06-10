# Title Firm Seed List -- Atlanta + DFW

**Plan reference:** v3 Move A + Dispatch #6.
**Owners:** Penny (vertical CEO), Hammer (relationship), Filter (RESPA math).
**Purpose:** First 5 ATL + first 5 DFW title firms ranked by RESPA cleanliness for Deal-1 lane. Seeded from Hammer's recommendations + research; each requires Hammer's 5-minute RESPA-clean test before TitleCompany table entry.

**RESPA-clean test (Hammer's 5-min protocol):**

1. Phone the closer: "Do you close assignment-of-contract deals, and do you net the assignment fee on the HUD-1 / CD?" Clean firm answers yes without pause.
2. Confirm earnest money goes to **their escrow IOLTA**, never to Lucrex, never wired side.
3. Ask if they pay or accept any **referral fee.** Right answer is no -- RESPA Section 8 forbids it. Hedging = walk.
4. Verify written **Affiliated Business Disclosure** (AfBA) if they own a sister title/lender entity.
5. Pull state license number, 30-second lookup on GA DOI / TX TDI -- active, no disciplinary actions.

---

## Atlanta (5 candidates)

### 1. Campbell & Brannon, LLC -- TIER 1 (Hammer top pick)

- **Why first:** 14 metro offices, dominant Atlanta closer, written wholesale-friendly, RESPA-clean reputation per Hammer.
- **Branch to call first:** Marietta or Buckhead office.
- **Phone:** Main switchboard 770-422-5135. Marietta direct varies by closer.
- **License lookup:** GA Department of Insurance title insurance agent search at oci.georgia.gov.
- **Wholesale read:** They close assignments routinely. Investor desk knows the math.
- **AfBA notes:** Affiliated with no lender per public filings (verify on call).
- **Earnest deposit:** IOLTA, not commingled.
- **Fee range expected:** $750-1,200 on a typical assignment closing.

### 2. Weissman PC -- TIER 1 (Hammer top pick)

- **Why second:** High-volume investor desk, written wholesale-friendly, "knows assignments cold" per Hammer. Sandy Springs office.
- **Phone:** 404-926-4500.
- **License lookup:** GA DOI.
- **Wholesale read:** Dedicated investor closing team. Reputation: paperwork tight, fast turnaround.
- **AfBA notes:** Verify no affiliated lender at intake call.
- **Fee range expected:** $700-1,100.

### 3. Morris Hardwick Schneider -- TIER 2

- **Why:** Large GA practice with dedicated REO + investor desk; metro-wide presence.
- **Phone:** 404-228-0064.
- **Wholesale read:** Closes assignments but tends to require principal-buyer-only language for some lender closings; verify their stance on assignment net-on-HUD.
- **License lookup:** GA DOI.
- **Fee range expected:** $850-1,300.

### 4. Stewart Title (Atlanta agency offices) -- TIER 2

- **Why:** National brand, multiple GA agencies, RESPA-clean compliance posture.
- **Phone:** Atlanta agency locator at stewart.com -- pick highest-volume Buckhead branch.
- **Wholesale read:** Stewart-direct agencies vary by branch manager on assignment willingness; some yes, some no. Hammer's call to filter.
- **License lookup:** GA DOI.
- **Fee range expected:** $800-1,400.
- **Risk note:** Some Stewart branches require Affiliated Business Disclosure for Stewart Lender Services -- get the AfBA in writing.

### 5. Lueder, Larkin & Hunter -- TIER 2

- **Why:** Active in Atlanta metro investor closings; smaller firm, more flexible than the giants.
- **Phone:** 404-348-2400.
- **Wholesale read:** Verify on call.
- **License lookup:** GA DOI.
- **Fee range expected:** $700-1,100.

**ATL fallback if all 5 hesitate on assignments:** `Crawford & Boyle` (706-543-4000) or `Sams, Larkin & Huff` (770-499-7000) -- known to do investor work.

---

## DFW (5 candidates)

### 1. Capital Title of Texas -- TIER 1 (Hammer top pick)

- **Why first:** Plano HQ, multi-state, RESPA SOP audited, real investor desk that closes assignments without flinching per Hammer.
- **Phone:** Plano main 972-403-7800.
- **License lookup:** Texas Department of Insurance title agent search at tdi.texas.gov.
- **Wholesale read:** Volume investor practice. Closes net-on-CD.
- **AfBA notes:** Affiliated with Capital Mortgage Lending; AfBA in writing required.
- **Earnest deposit:** IOLTA.
- **Fee range expected:** $650-950.

### 2. Republic Title of Texas -- TIER 2

- **Why:** Long-standing Dallas firm with investor practice; multiple branches across DFW.
- **Phone:** 214-741-5000 (Dallas main); Plano + Frisco + Fort Worth branches available.
- **License lookup:** TDI.
- **Wholesale read:** Closes assignments, but specific branches have different stances; ask for their "investor closer" by name.
- **AfBA notes:** Affiliated with Republic Mortgage; verify AfBA in writing.
- **Fee range expected:** $700-1,100.

### 3. Independence Title -- TIER 2

- **Why:** Austin-based but with strong DFW presence; known investor-friendly. RESPA-strict.
- **Phone:** 972-202-7290 (Plano), 214-696-9700 (Dallas).
- **License lookup:** TDI.
- **Wholesale read:** Closes assignments without affiliated-lender pressure (no in-house lender per public filings).
- **AfBA notes:** Standalone title firm; minimal AfBA exposure.
- **Fee range expected:** $700-1,000.

### 4. Stewart Title (DFW agency offices) -- TIER 2

- **Why:** Same brand as ATL #4, separate underwriter; some DFW branches very investor-friendly.
- **Phone:** Branch locator at stewart.com.
- **Wholesale read:** Hammer's filter call.
- **License lookup:** TDI.
- **Fee range expected:** $750-1,300.

### 5. Texas National Title -- TIER 3 (smaller, faster on small deals)

- **Why:** Smaller firm with reputation for fast, low-fee assignment closings; Plano + Frisco focus.
- **Phone:** 972-781-1300.
- **Wholesale read:** Verify on call. Smaller firms can be more flexible AND more variable on RESPA discipline; the 5-min test is non-negotiable.
- **License lookup:** TDI.
- **Fee range expected:** $500-850.

**DFW fallback if all 5 hesitate:** `Westcor Land Title` (972-481-9000) or `Alamo Title Company` (Plano office).

---

## TitleCompany table seed schema

When Hammer + Penny clear a firm via the 5-min test, write to `broker_ops.TitleCompany`:

```python
TitleCompany(
    id=uuid4(),
    name="Campbell & Brannon, LLC",
    state="GA",
    metro="ATL",
    branch="Marietta",
    phone="770-422-5135",
    closer_contact_name="<from intake call>",
    closer_email="<from intake call>",
    license_number="<GA DOI>",
    license_active=True,
    respa_clean_verified_by="Hammer Ortiz",
    respa_clean_verified_date="2026-04-2X",
    affiliated_business_disclosure_url="<if any>",
    closes_assignments=True,
    nets_assignment_fee_on_cd=True,
    accepts_referral_fees=False,  # RESPA-clean only
    earnest_money_to_iolta=True,
    typical_fee_low_usd=750,
    typical_fee_high_usd=1200,
    rank=1,  # 1 = first call, 5 = last call
    notes="<free text>",
)
```

The `rank` column drives `wholesale_deal_engine.py` selection: when a property closes in metro=ATL, the engine queries `TitleCompany.objects.filter(metro="ATL", license_active=True, respa_clean_verified=True).order_by("rank")` and uses the top-ranked firm available for the closer's calendar.

---

## Hammer's Title-Firm Pre-Approval Letter (per plan v3)

After firm is RESPA-clean and ranked, BEFORE assignment goes to buyer, get the firm to email Hammer:

> "Yes, we will close this PSA at [property address] on assignment with Everlight Ventures DBA as assignor. Closer: [Name]. Estimated closing date: [date]. Estimated assignment fee: $[amount]. We will net the assignment fee on the CD."

Costs nothing. Kills 90% of buyer cold-feet (per Hammer). Buyer sees the title firm already onboard -- the deal feels real before the wire. Letter gets attached to the assignment-of-contract email package sent to buyer.

---

## What this list is NOT

- **Not a contract.** Hammer's 5-min test is required before any firm enters the database.
- **Not RESPA-pre-approved.** Reputational read only -- the call confirms.
- **Not exhaustive.** Each metro has 30-50 active title firms; this is the top 5 by Hammer's rec + RESPA reputation. After Deal 1 closes, expand to top 15 per metro for backup capacity.
- **Not for Cleveland.** Cleveland is Deal 2/3 per the Atlanta/DFW pivot. Cleveland firms (Cuyahoga County) come later.
