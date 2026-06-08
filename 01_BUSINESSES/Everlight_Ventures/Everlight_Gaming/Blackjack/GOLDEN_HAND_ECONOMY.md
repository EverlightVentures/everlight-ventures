# Golden Hand (RIDE IT) -- mechanics + exposure model
**Locked 2026-06-08 with Rich.** Answers "if they split aces then double both, that's
up to ~1000x -- how do we account for it in gold prices + the gold/SC-free ratio?"

## The mechanic (locked)
- **RIDE IT** arms the NEXT hand as the **Golden Hand**. It **auto-arms**: the game
  auto-places a bet = the player's **QTD average bet** (not their last bet) and shows a
  **"GOLDEN HAND 200x"** marker on the felt. No re-betting; they just play it.
- **The 200x rides like a real bet** (Rich's pick = blend of "scales" + "covered by economy"):
  - Win the Golden Hand -> **200x** the avg bet.
  - **Double** -> **400x** (the bonus doubles with the bet).
  - **Split** -> each resulting hand is its own Golden Hand (its own 200x).
  - **Double after split** -> 400x on that hand.
- **Caps (house-safe):** each hand caps at **888 x bet-multiplier** (888 single / 1,776
  doubled). **Hard ceiling on the whole event = 1,776** ("two lucky-8s") so the rare
  4-way-split-and-double monster can never exceed it -- the reserve is always bounded.
- Lose / push / bust the Golden Hand = **0** (they gambled away the guaranteed 100x TAKE).
- Chips (Gold) in social mode; SC in sweeps mode. Per-hand + total caps apply to both.

## Why the compounding is covered (the money answer)
Let **B** = the player's avg bet (the payout basis; floored at the table minimum).

| Quantity | Value | Note |
|---|---|---|
| B-Card frequency | ~1 per **370,000 hands** | 1 in 1,854,799 cards / ~5 cards a hand |
| House edge banked between hits | **~18,500 x B** | ~5% edge x 370k hands x B |
| Typical Golden Hand payout | **~100 x B** | most RIDEs don't split-and-double-and-win |
| Worst-case payout (hard ceiling) | **1,776 x B** | 4-way split + double all + win all |
| Cushion at worst case | **~10x** | 18,500 / 1,776 |
| Reserve to hold | **~2,664 x B** | 1,776 x 1.5 safety |

So even the nightmare compounding case is a **~10x cushion** against what the house already
banked since the last B-Card -- and that case requires hitting a 1-in-370k card, choosing
RIDE, splitting to 4, doubling all, AND winning all (probability ~vanishing). Expected cost
is ~100xB. **No change to gold package prices** -- the existing house edge funds it.

## Gold prices + gold/SC-free ratio (what it means for us)
- **Gold prices: unchanged.** The Rookie..Kingpin packages stay; the edge on gold play is
  the funding source (the 18,500xB cushion is the same at any volume -- it's a ratio).
- **The avg-bet basis is the natural governor.** Payouts scale off avg bet, and avg bet is
  driven by GOLD SPEND. A free player bets tiny -> their Golden Hand pays tiny. Only buyers
  build an avg bet big enough to approach 888/1,776 -- and their own play already fed the
  edge that covers it. Self-balancing.
- **Keep the free-SC drip small.** SC payouts are the only ones with cash cost (redeemable).
  Because they're avg-bet-based and free SC is a thin trickle, free players' SC Golden Hands
  are worth pennies. Hold reserve = ~2,664 x (median SC avg bet) on the SC side only.
- **Net:** the compounding is a branding/excitement upside, not a reserve threat. The 1,776
  hard ceiling is the single number to size the reserve against.

## Build checklist -- BUILT 2026-06-08 (commit 6b9244b)
1. [x] Auto-arm: newRound when goldenHandActive -> betAmount = qtdAvgBet; GOLDEN HAND banner.
2. [x] Golden bonus rides per-hand (`goldenHandHandBonus`), scales w/ double, stacks across
       splits, capped 888/hand (x2 doubled) + `GOLDEN_EVENT_CAP` 1,776 total ceiling.
3. [x] Pays on EVERY winning settle path (main loop iterates home-seat hand+splitHand;
       opening-BJ path; doubled-bust clears goldenHandActive so it can't leak forward).
4. [x] Celebration: gated on `bcardPayoutAmount > 0` (was reading goldenHandActive after clear).
5. [x] Landscape: social/emoji + fullscreen -> fixed top-right cluster (safe-area inset).
Owner-gated test (B-Card beta = owner-only). Verify, then flip BCARD_BETA_MODE=false to launch.
