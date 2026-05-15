# Pack Rip Outcome Model -- DECISION REQUIRED

**Owner:** Rich Gee
**Status:** AWAITING DECISION (this file is the binding spec once Rich writes the WHY below)
**Date staged:** 2026-05-15
**Context:** TiltRips + TCG Zen surfaced as trends 2026-05-15. Validates Alley Kingz pack-rip + pulse-feed design. The model below decides smart-contract finalization, Stripe MCC, legal posture, marketplace UX, and $BCRD flow.

---

## Why this matters

The mechanic of "user pays, receives random-tier card, card has tradable value" lives on a spectrum from *pure cosmetic* to *real-money outcome*. Where Alley Kingz sits on that spectrum cascades into:

- Which `BcrdiGameVault.sol` payout function ships
- Whether Stripe Checkout (MCC 5816 digital goods) or full crypto rails (no Stripe) is used for pack purchases
- Whether the marketplace cash-out path is enabled
- Which states/countries get geofenced at signup
- Whether KYC kicks in over $X spend
- Whether seasonal staking rewards are skill-gated (not securities) or time-gated (Howey risk)

---

## Three Valid Approaches

### Option A: Pure Utility + Cosmetic (Splinterlands / Gods Unchained model)

- Packs cost fiat (Stripe) OR $BCRD
- Pulls are NFT cards that go into the GAME
- Marketplace exists, denominated in $BCRD only
- Everlight never operates a USD cash-out desk
- Players who want USD must self-bridge $BCRD on ZilSwap
- **Legal posture: strongest**. Cards have game utility = not gambling. Marketplace is peer-to-peer crypto = not money transmission.
- **Profit ceiling: medium**. No house edge on cash-out. Revenue = pack sales + marketplace take + staking emissions.
- **Time to ship clean: ~14 days**

### Option B: $BCRD Native Economy (Axie Infinity model)

- Packs cost $BCRD only (fiat is for $BCRD purchase via on-ramp partner like Transak)
- Marketplace pays in $BCRD
- Players cash out via their own wallet -> DEX -> off-ramp
- Everlight runs the treasury, never the cash-out
- **Legal posture: medium**. Cleaner separation of "in-game economy" vs "Everlight as financial intermediary." Still loot-box-rules apply.
- **Profit ceiling: high**. Buy-pressure on $BCRD compounds Everlight treasury value.
- **Risk: token-price death spiral if play-to-earn collapses (see Axie 2022). Mitigate by capping emission + skill-gating rewards.**
- **Time to ship clean: ~21 days** (needs Transak or similar onramp integration)

### Option C: Hybrid USD + $BCRD with Everlight cash-out desk (TiltRips path)

- Packs cost USD or $BCRD
- Marketplace pays in either
- Everlight operates a buy-back desk -- card listed for sale, Everlight pays seller in USD via Stripe Transfer / Connect
- **Legal posture: WORST**. Everlight becomes a money transmitter (state-by-state MTL licensing) AND the loot-box gambling argument lands cleanly because outcome has direct monetary value paid by the operator.
- **Profit ceiling: highest IF survived**. House edge on every cash-out. But:
- **DO NOT RECOMMEND** -- this is the path that gave Whatnot 15+ pending arbitration claims and the path TiltRips is on with a Tobique gaming license + KYC + $51M VC cushion to survive enforcement.
- **Time to ship clean: 6+ months** (state MTLs, KYC vendor, surety bonds, legal opinion letters)

---

## Hive Pre-Vote (advisory, non-binding)

- **theo_briggs (General Counsel):** A
- **priya_bhattacharya (Privacy Counsel):** A or B, never C
- **markets / pitch_adler:** B for upside, A for survivability
- **everlight_trading_risk:** A first, B in season 2 once token has 6 months of trade history

---

## Rich's Decision

<!-- TODO: Rich writes 5-10 lines below. Pick A / B / C. Explain the why.
     Once written, this is the binding spec. Hive locks contracts + ships off this. -->

**Decision:** _____ (A / B / C)

**Reasoning (5-10 lines):**

```
[your 5-10 lines here -- what's the moat, what's the risk you accept, what's the
season-2 evolution path, what's the kill-switch trigger that would force you to
pivot between models]
```

**Signed:** Rich Gee, CEO Everlight Ventures
**Date:** _____

---

## On execution lock

The moment this file is filled in:
1. Hive locks the matching `BcrdiGameVault.sol` payout function (cuts the other two branches)
2. Stripe MCC is selected: 5816 (digital goods) for A or B, none for C
3. `/packs` route on everlightventures.io is built against the matching contract ABI
4. Pulse feed schema is finalized (option C needs additional KYC/AML fields)
5. Geofence config ships (WA, MN, HI excluded under loot-box rules + state-by-state under option C)
6. Marquise + Piper + Hammer get re-briefed: this is a real product now, not a research thread
