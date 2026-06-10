# Purchase and Sale Agreement -- Master Template

_State-specific addenda required for each operating state. This master is the assignable form. Always have an attorney in the operating state review before first use._

---

## PURCHASE AND SALE AGREEMENT

This agreement is made on **{{date}}** between:

**Seller:** {{seller_full_name}}, of {{seller_address}}
**Buyer:** Everlight Ventures LLC and/or assigns, a Delaware limited liability company

For the property at: **{{property_address}}, {{property_city}}, {{property_state}} {{property_zip}}** ("Property").

### 1. Purchase price

Buyer agrees to purchase Property for **${{purchase_price}}** in cash, subject to the terms below.

### 2. Earnest money deposit

Buyer will deposit **${{emd_amount}}** earnest money with **{{title_company_or_attorney}}** within **{{emd_days}} business days** of signing.

### 3. Closing

Closing occurs on or before **{{closing_date}}** at the office of {{title_company_or_attorney}}.

### 4. WHOLESALE INTENT DISCLOSURE (REQUIRED)

Buyer is a real estate investment company. Seller acknowledges that **Buyer may assign this Agreement to a third-party investor before closing**, and the actual purchaser at closing may be a different entity than Everlight Ventures LLC. The assignment fee, if any, is between Buyer and the assignee. Seller is not responsible for and is not entitled to any portion of the assignment fee.

Seller further acknowledges that:
- Buyer is NOT a licensed real estate broker, agent, or salesperson, and does not represent Seller in this transaction.
- Seller has been advised to seek independent counsel (real estate attorney + CPA) before signing.
- This is an arms-length transaction. Seller is selling AS-IS, with all faults and defects.

### 5. Inspection contingency

Buyer has **{{inspection_days}} calendar days** from execution to inspect the Property. Buyer may terminate for any reason during this period and recover the EMD in full.

### 6. Title contingency

Closing is contingent on Seller delivering marketable title, free of liens and encumbrances except those agreed to in writing. Title insurance to be issued at closing through {{title_company_or_attorney}}.

### 7. Default and remedies

If Seller defaults: Buyer may terminate and recover EMD plus actual damages, or sue for specific performance.
If Buyer defaults: Seller's sole remedy is to retain the EMD as liquidated damages.

### 8. Signatures

**Seller:** _______________________ Date: __________

**Buyer (or assigns):** Everlight Ventures LLC, by _______________________ Date: __________

---

## State-specific addenda required

| State | Addendum | Notes |
|-------|----------|-------|
| GA | Lead Paint Disclosure (pre-1978) + Closing Attorney requirement clause | GA requires attorney closing |
| FL | Property Tax Disclosure + Coastal Construction Control Line (if coastal) | |
| TX | TX Property Code Seller's Disclosure (Sec 5.008) -- mandatory | |
| AZ | AZ Affidavit of Disclosure (Sec 33-422) | If sellable real property over 5 acres |
| CA | TDS, NHD, Mello-Roos, Megan's Law disclosures | High disclosure burden; **CA pre-foreclosure outreach BLOCKED per CC 2945** |
| MO | Lead Paint Disclosure | |
| NC | **WHOLESALING BLOCKED per HB 797** -- do not use this template in NC |
| TN | Lead Paint + 30-day Inspection Period | |

## Variables loaded by `contract_generator.py`

```
{{date}}, {{seller_full_name}}, {{seller_address}},
{{property_address}}, {{property_city}}, {{property_state}}, {{property_zip}},
{{purchase_price}}, {{emd_amount}}, {{emd_days}},
{{title_company_or_attorney}}, {{closing_date}}, {{inspection_days}}
```

The contract_generator pulls these from the Deal model + state_gates compliance + the per-state addenda registry.

_DRAFT TEMPLATE -- attorney review required before first use in any state._
