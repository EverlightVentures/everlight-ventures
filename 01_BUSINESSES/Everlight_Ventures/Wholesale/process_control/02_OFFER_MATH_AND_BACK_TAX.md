# Offer Math + Back Tax: How It Actually Works

**Purpose:** Marquise asked "if I'm saying they don't pay the taxes, who will that fall back on. I don't wanna pay em." This document explains the standard wholesale closing math so the answer is correct: **back tax comes out of seller's proceeds at the title firm, not out of our pocket OR seller's pocket directly.**

---

## How wholesale closing actually flows

The title firm (Mid-South Title) holds ALL the money in escrow. They distribute it per the closing settlement statement.

```
                BUYER (Chris) wires $2,500 to title escrow
                              |
                              v
              +-----------------------------+
              |  TITLE FIRM ESCROW ACCOUNT  |
              +-----------------------------+
                              |
        +---------------------+---------------------+
        |                                            |
        v                                            v
  Pays expenses out                          Pays remaining
  of escrow (NOT out                         to seller and to us
  of seller's pocket):                       (per assignment math)
                                                    |
  - Back property tax     ($350)               +-----+-----+
  - Recording fees         ($25)               |           |
  - Prorated current tax   ($30)         Seller     Assignor
  - Half title insurance  ($200)         net check  (Everlight)
  - Half escrow fee        ($75)          $1,120       $700
                                          (their      (our fee)
                                           offer:
                                           $1,800
                                           minus
                                           closing
                                           costs)
```

**Key fact:** seller never writes a check at closing. They sign documents, the title firm hands them a wire or check for their net.

---

## Worked example: 117 FARROW AVE

| Item | Amount | Who | Notes |
|---|---:|---|---|
| Buyer wire to escrow | $2,500 | Chris Ulander (Mid South) | Total deal price |
| **Out of escrow (split):** | | | |
| -- Back property tax (Shelby Trustee) | -$350 | comes out of seller's side per standard | |
| -- Recording fee (deed) | -$25 | seller's side | |
| -- Prorated current-year tax | -$30 | seller's side | |
| -- Title insurance (half) | -$200 | seller's side | typical split |
| -- Escrow fee (half) | -$75 | seller's side | |
| -- Assignment fee | -$700 | to Everlight Ventures | gap between $2,500 and $1,800 |
| **Net to seller** | **$1,120** | wired/checked to seller | (=$1,800 contract - $680 seller closing costs) |

**Marquise's takeaway:**
- We do NOT pay back taxes.
- Seller does NOT write a check for back taxes.
- Back taxes are paid OUT of seller's proceeds at closing, by the title firm.
- Our $700 fee is preserved.

---

## How to phrase it to the seller (honest, not deceptive)

**WRONG (what we said in v1):**
> "We pay every dollar of back tax + penalty at closing -- out of OUR side, not yours. You walk away clean."

**RIGHT:**
> "Back taxes are handled at the title firm out of the closing proceeds. You don't write a check or owe anything out of pocket. Your net check at closing will be approximately $1,100-1,200 after the standard back-tax payoff and recording fees. The title firm will give you the exact itemized statement 24 hours before closing."

The seller still walks away with a clean check. They still don't pay back tax out of pocket. But we're not lying about WHO pays.

---

## When to bump the gross offer to keep seller's net at target

If you want seller to NET $1,800 (their target), gross offer needs to be:

```
Gross offer = Target net + estimated closing costs (seller side)
            = $1,800 + ~$680
            = $2,480
```

Then Chris's price needs to be: $2,480 + assignment fee = $3,180.

**Decision rule (Penny):**
- If seller is FIXED on gross offer #: leave $1,800 contract, explain net.
- If seller is FIXED on net check #: bump contract to $2,480, push Chris to $3,180.
- If both fixed: Penny decides if margin holds, else walk.

---

## Closing-cost variability

These are TYPICAL costs for a Memphis vacant lot under $5k appraisal. Real numbers can shift:

| Cost | Range | Notes |
|---|---|---|
| Back property tax | $200-2,000 | depends on years delinquent. TS2202 = 4 yrs ~$200-500 typical for lots |
| Recording fees | $20-50 | flat per document |
| Prorated current-year tax | $0-100 | depends on month closed |
| Title insurance (seller half) | $150-300 | flat low-end for cheap lots |
| Escrow fee | $50-150 | Mid-South charges $150 split |
| Doc prep / wire | $25-50 | minor |

**Verifying the back tax exact figure:**
- Browser-MHTML: https://www.shelbycountytrustee.com/ (search by parcel)
- Returns: total delinquent years, principal + interest + penalty per year
- Save into intel folder, attach to PSA so seller sees the actual number before signing
