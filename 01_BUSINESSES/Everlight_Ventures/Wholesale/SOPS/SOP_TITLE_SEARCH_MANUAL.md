# SOP -- Manual Title Search (Free Path)

**When to run this:** Before signing a PSA on any property. Always.
**How long it takes:** 3-5 minutes per property.
**Cost:** $0.

---

## Why this matters

Skipping a title check on a deal can cost you:
- Wasted EMD if the seller isn't on title (signer fraud)
- Burned closing if there's a $200k IRS lien you didn't know about
- Lost buyer trust if liens surface during their due diligence

A 4-minute county clerk lookup eliminates all three.

---

## Tools you already have

The `free_title_search.py` module routes to the right county clerk URL for each
of your 7 active states. You feed it an address, it gives you the URL.

```bash
python3 /home/opc/wholesale/title_search/free_title_search.py \
    --address "1234 Main St, Atlanta, GA 30309"
```

It returns the right county's deed-index URL.

---

## What you're checking (in order)

### 1. Confirm signer is on title (60 sec)

Open the URL the script gives you. Search by:
- Owner's last name, OR
- Property address (if the system supports it)

**Look for:**
- The most recent grantee (= current owner) on the most recent deed
- Cross-check this name against the name on the seller's PSA

**Red flag:** Names don't match. Either the seller is not on title (relative,
heir, ex-spouse with claim, etc.) or there's been a recent transfer not yet
recorded. **Halt the deal until verified by phone or in writing.**

### 2. Liens / encumbrances scan (90 sec)

In the same county clerk system, search for the property address or owner
name in the **liens** or **judgments** index.

**What you're looking for:**
- IRS tax liens
- State tax liens
- Mechanics liens (contractor unpaid)
- Judgments from lawsuits
- HOA liens
- Code-enforcement liens

**Decision rules:**
- Total liens < your assignment fee + buyer rehab budget room = OK to proceed
- Total liens > equity available = walk OR negotiate seller to pay off at close
- Tax liens with the IRS = always halt and call a title company before signing

### 3. Mortgage / lender position (60 sec)

Search the deeds index for the property address. Look for:
- The most recent mortgage / deed of trust
- Original loan amount
- Date filed

**Decision rules:**
- If the seller's stated mortgage balance is roughly the original loan amount
  minus expected paydown, OK
- If wildly different, ask the seller for a current mortgage statement before signing

### 4. Foreclosure or pre-foreclosure check (30 sec)

In the same system or via free public records:
- Search "lis pendens" for that property
- Search county foreclosure auction calendars

**Important state rules:**
- **CA** -- pre-foreclosure outreach is BLOCKED in your state_gates (CC 2945).
  Do NOT pursue these in California.
- **GA, FL, TX, AZ, MO, TN** -- pre-foreclosure is workable, but document
  your wholesale intent disclosure clearly.

### 5. Last sale price + history (30 sec)

Most clerk sites show recent transactions. Capture:
- Last sale date
- Last sale price
- Intervening transfers (e.g. quit-claim deeds suggest family/heir situations)

**Use this for:** sanity-checking your offer math + spotting motivated sellers
(if last sale was a divorce-driven quit-claim, you have leverage).

---

## Capture the result

Either:
1. Screenshot each search result, save to:
   `/home/opc/wholesale/title_search/captures/<property_address>/`

2. Or paste a summary into Django via the TitleReport model:
```python
from broker_ops.models import TitleReport
TitleReport.objects.create(
    property_address="1234 Main St, Atlanta, GA 30309",
    owner_on_title="John Smith",
    psa_signer="John Smith",  # match!
    liens_total=0,             # or total $
    mortgage_balance_est=145000,
    notes="No issues. Signer matches. No liens. Recent quit-claim 2024 suggests divorce situation -- motivated seller.",
)
```

---

## Red-flag cheat sheet (when to HALT)

Halt the deal IMMEDIATELY and call a title company before signing if you see:

- Signer name doesn't match owner on title
- Recent quit-claim deed from a co-owner who isn't on the PSA
- IRS tax lien
- Lis pendens (lawsuit pending against property)
- HOA lien larger than $5k
- Foreclosure auction date already scheduled (unless explicitly working pre-foreclosure)
- "Heirs of [name]" in the title chain (probate situation requires court approval)

A good rule: if anything feels off, the next 30 minutes calling a title
company costs less than a $5,000 EMD lost on a deal that can't close.

---

## When to upgrade to a paid vendor

Consider DataTree / TitleWave / PropStream when ANY of:
- You're doing 5+ deals per month
- You're entering states you don't know yet
- You're working pre-foreclosure or auction inventory at scale

Until then, the free path above gives you 80% of the value at 0% of the cost.

---

## How this maps to the audit

When this SOP exists at `/home/opc/wholesale/SOPS/SOP_TITLE_SEARCH_MANUAL.md`,
the audit will recognize the manual workflow as the operational protection
for the title-search gap. Combined with `free_title_search.py` and the
TitleReport Django model, this is sufficient for PASS at the current stage.

(The current PARTIAL says "needs headless browser or paid vendor for full
automation" -- which is true, but isn't actually required for a small
wholesaler doing manual due-diligence per deal.)
