# Everlight Open Deal -- EMD Lock Policy (TIER LADDER)

**Owner:** Rich Gee
**Status:** LOCKED 2026-05-15
**Decision:** Run all 3 options as a buyer commitment ladder. Lower tiers feed into higher ones.

---

## The Ladder

| Tier | Cost to Join | EMD Model on a Lock | Drop Access Timing |
|---|---|---|---|
| **Browser** | Free signup | Stripe Authorization (hold only, $0 charged) | Public feed -- everyone sees at the same time |
| **Buyer-Funds-Verified** | $99 one-time KYC | Stripe Capture, refundable minus **10% house fee** on walks | Same as Browser, plus "Buyer-Funds-Verified" badge in pulse feed (tooltip: "Identity + funds confirmed. Not a representation of buyer creditworthiness, behavior, or fitness.") |
| **Inner Circle** | $49/mo recurring | $99 non-refundable Lock Fee + real EMD wired to Mid South Title | **4 hours early access** before public drop |

### Buyer-Funds-Verified KYC (the $99 one-time fee)

- Government-issued photo ID upload (driver license / passport)
- Proof of funds (bank statement, last 30 days, $50k min liquid)
- LLC formation docs OR personal acquisition history
- **OFAC SDN list screening** (mandatory, 5-min manual check, logged with timestamp -- per Theo Briggs federal audit 2026-05-15)
- Manual review by Marquise + Justine (legal)
- Approved -> "Buyer-Funds-Verified" check next to username with hover tooltip clarifying what it does and does not represent
- **CA buyers blocked from this tier pending Cal. Civ. Code 1671(b) liquidated-damages analysis** (per Theo Briggs audit)
- Filters tire-kickers, gives buyer-quality signal on the pulse feed, creates instant $99 revenue

### Inner Circle ($49/mo)

- Stripe recurring subscription
- 4-hour first-look on every drop before the public feed
- $99 Lock Fees CREDITED to assignment fee at close (effectively free to actual buyers)
- Walks forfeit the $99 ($99/walk pure profit)
- Real EMD ($1,000+) wires straight to Mid South Title -- standard escrow, RESPA-clean
- Chris Ulander auto-enrolled, $49/mo COMPED (anchor relationship)

---

## How a buyer climbs the ladder

```
1. Sees IG / Slack drop teaser -> signs up free as Browser
2. Browses 2-3 drops, sees Verified buyers locking faster -> pays $99 for Verified
3. Locks a deal, walks once (loses $50 of $500 -- the 10% fee)
4. Gets serious -> joins Inner Circle for $49/mo + 4h early access
5. Closes deal -> $99 Lock Fees come back as Assignment Fee credit
```

The page does the buyer qualification for Marquise. By the time someone is in Inner Circle, they've signaled real money three times.

---

## Stripe Flow Per Tier

### Browser
```
On Lock click:
  stripe.paymentIntents.create({
    amount: 50000,                # $500
    currency: 'usd',
    capture_method: 'manual',     # AUTHORIZATION ONLY
    customer: buyer_id,
    metadata: { tier: 'browser', drop_id, ... }
  })
On PSA sign (within 24h):
  stripe.paymentIntents.capture(pi_id, { amount_to_capture: 50000 })
On walk / 24h expire:
  stripe.paymentIntents.cancel(pi_id)
  # No money moved, no refund needed
```

### Buyer-Funds-Verified
```
On Lock click:
  stripe.paymentIntents.create({
    amount: 50000,
    currency: 'usd',
    confirm: true,                # IMMEDIATE CAPTURE
    customer: buyer_id,
    metadata: { tier: 'verified', drop_id, ... }
  })
On PSA sign (within 24h):
  # $500 stays as credit toward EMD on PSA Schedule A
  # No Stripe action needed; reconciliation only
On walk:
  stripe.refunds.create({
    payment_intent: pi_id,
    amount: 45000                 # REFUND $450, KEEP $50 (10% house fee)
  })
  # Stripe also keeps its ~$14.80 from the original capture -- our cost of doing business
  # Net to us per walk: ~$35.20
```

### Inner Circle
```
On Lock click:
  stripe.paymentIntents.create({
    amount: 9900,                 # $99 NON-REFUNDABLE Lock Fee
    currency: 'usd',
    confirm: true,
    customer: buyer_id,
    metadata: { tier: 'inner_circle', drop_id, fee_type: 'non_refundable_lock_fee' }
  })
  # SEPARATE: trigger Mid South Title wire instruction email to buyer
On PSA sign (within 24h):
  # Buyer wires EMD ($1000+) directly to Mid South Title trust account
  # $99 Lock Fee credits to Assignment Fee at close (refund-and-recharge OR ledger entry)
On walk:
  # Keep $99 entirely. Refund EMD via Mid South Title (their process, not ours).
```

---

## What this means for the contracts

PSA Schedule A gets ONE new line per tier:

- **Browser:** standard EMD language (no change)
- **Verified:** "Buyer has authorized a Lock Fee deposit of $___. Of this Lock Fee, ten percent (10%) is non-refundable as consideration for the 24-hour exclusivity period granted to Buyer. The remaining ninety percent (90%) is refundable if Buyer terminates this Agreement within the 24-hour Lock Period."
- **Inner Circle:** "Buyer has paid a non-refundable Lock Fee of $99 USD as consideration for the 24-hour exclusivity period granted to Buyer. Earnest Money Deposit shall be deposited with Mid South Title Co. per Schedule B."

`legal_heck_aurelio` to countersign all three lines before they go live in v3 PSA template.

---

## What this means for the website

Three components on everlightventures.io:

1. **`/drops`** -- public live feed (the buyer war page). Drop cards with photos, numbers, "X buyers viewing now," "Lock 24h" button.
2. **`/drops/[id]`** -- single drop detail page. Lock button routes through tier-appropriate Stripe flow.
3. **`/buyer/dashboard`** -- buyer's locked deals, Verified KYC status, Inner Circle subscription mgmt.
4. **`/legal/lock-fee-disclosure`** -- public-facing rendering of `BUYER_DISCLOSURE_LOCK_FEE.md`. Linked from EVERY Lock button.
5. **`/verify`** -- Verified tier upgrade flow ($99 + KYC doc upload).
6. **`/inner-circle`** -- Inner Circle subscription page ($49/mo).

---

## Chris Ulander handling (specific call-out)

Chris is the anchor TN cash buyer per `state_marvin_tn` 2026-04-27 confirmation. The Open Deal page does NOT replace his relationship -- it ENHANCES it:

- Chris account: Inner Circle, COMPED indefinitely (Stripe Coupon `INNER_CIRCLE_CHRIS_FOREVER`)
- Lock Fee: WAIVED on first 10 locks per quarter (Stripe Coupon `CHRIS_FREE_LOCKS_10Q`)
- Drop notification: Chris gets Slack DM the moment a drop is created, BEFORE the 4-hour Inner Circle window opens. **SMS rail OFF** until both (a) Prior Express Written Consent record on file per FCC 23-107, AND (b) Deal 3 closes (TN state_gates.json SMS gate). This is the "Chris-first" rule already in his current contractor arrangement; Slack DM is sufficient given his existing tunnel into our channels.
- Public pulse feed labels Chris as "ANCHOR" (gold crown icon) -- other buyers see his interest as a signal of quality.

Marvin owns the Chris re-brief: "this is on top of your current arrangement, you get more deals faster, $0 cost to you."

---

## Revenue projection per tier

Conservative monthly projection at 200 active buyers across all tiers:

| Tier | Active Buyers | Cost to Join | Avg Walks/mo | Walk Revenue | Subscription Revenue |
|---|---|---|---|---|---|
| Browser | 150 | $0 | 30 | $0 | $0 |
| Verified | 40 | $99 one-time | 15 | $525 ($35 × 15) | $396 (4 new × $99/mo run rate) |
| Inner Circle | 10 + Chris | $49/mo | 8 | $792 ($99 × 8) | $441 ($49 × 9 paying) |
| **Total** | **200** | -- | **53** | **$1,317** | **$837** |

Add: 1 deal/week closing × $4,000 assignment fee = $16,000/mo.

**Total Open Deal monthly run rate at 200 buyers: ~$18,154 gross, ~$17,500 net after Stripe.**

---

## Build sprint

See `OPEN_DEAL_BUILD_SPEC.md` for the 7-10 day Hive build plan. Disclosure copy in `BUYER_DISCLOSURE_LOCK_FEE.md`.
