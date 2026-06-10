# $BCARDD LAUNCH-DAY RUNBOOK
**Date:** 2026-06-08 | **Chain:** Solana | **Venue:** pump.fun fair launch
**Operator does every on-chain action (keys). Lucrex/AI is off-chain only (prep, never signs).**

> Live pump.fun params below were filled from a source-cited research pass (2026-06-08). Re-verify the fee doc + SOL price at launch time -- pump.fun can change fees without notice.

## GATE 0 -- your go/no-go (operator-controlled; legal is ADVISORY, not a blocker)
- [ ] **Legal = insight only (operator call 2026-06-08):** Wen + Theo advise, they do NOT sign off. Read `BCARDD_LEGAL_DECOUPLE_MEMO_2026-06-08.md` so you know the risks, then YOU decide. Not a launch blocker.
- [ ] **THE one design rule that actually protects you -- money stays separate:** no casino->$BCARDD payout and no $BCARDD->sweeps-entry path. Shared MASCOT/lore across Alley Kingz + B-CARDD BET is fine and encouraged; a shared MONEY rail is not. Confirm none exists in the build.
- [ ] **Wallet security:**
  - [ ] Gmail on the launch wallet uses **passkey / authenticator 2FA (NOT SMS)**.
  - [ ] Launch wallet **private key exported to Proton Pass** as lockout backup (per `reference_crypto_seed_vault`). Never in a repo file.
  - [ ] Confirm it is the **fresh** launch wallet `2ef4VfuyRNYwu6WMW9TCz8cXpiqi23MSd8y8ZFyUmrBg`, isolated from any exposed seed.
- [ ] **Brand:** spec/socials say `$BCARDD` (rename swept 2026-06-08); pick final X/TG handle (suggest @bcardd / @bcarddcoin / @bcardddog -- check availability, avoid plain "bacardi").
- [ ] **Lock tool = Jupiter Lock** (lock.jup.ag): free, open-source, audited twice (OtterSec + Sec3), lock is publicly verifiable so you can post a proof link. Streamflow only if you later need multi-recipient vesting (~0.117 SOL/lock). **NOTE: LP needs NO lock** -- pump.fun auto-burns the LP at graduation. You only lock the **founder bag**.

## STEP 1 -- Fund the launch wallet
- [ ] Send **~3.5 SOL** to the launch wallet (~$235 at SOL=$67; covers: dev-buy ~2.78 SOL + Jito bundle tip ~0.001-0.05 + tx/deploy fees + cushion). Confirm balance on-chain before continuing.
  - **Dev-buy for 9% (90M of 1B) = ~2.78 SOL** (incl. the 1% bonding-curve fee). At **SOL ~$67 (2026-06-08) that is ~$186.** The SOL amount is FIXED by the curve math; the USD just tracks SOL price, so re-check spot at launch.

## STEP 2 -- Deploy + dev-buy (atomic, block 0)
- [ ] Create the coin on pump.fun: name **$BCARDD** ("B-Card-D" / B-Card Dog), ticker **BCARDD**, the dog art, the one-line story (fun/utility, NOT investment).
- [ ] **At launch, set creator fees to YOUR wallet.** The alternative ("Cashback Coins," fees redirected to traders) is **LOCKED FOREVER** once chosen -- pick creator-to-you. (Creator fee is dynamic: ~0.95%/trade at $88k-$300k cap, scaling down to 0.05% past $20M, paid in SOL, claimable anytime.)
- [ ] Acquire **~9% (90M)** via an **atomic Jito bundle** that lands the mint + your buy in the **SAME block (block 0)** -- this blocks snipers from wedging in front of you.
  - **Do NOT "ladder" across transactions:** the curve is path-independent, so splitting gives the SAME total SOL and SAME average price -- zero benefit. (Splitting across multiple WALLETS only changes holder-concentration optics and carries its own bundle-detection reputational risk. Decide that deliberately; do not default to it.)
- [ ] Verify: founder wallet holds ~9%, public curve holds the rest. Screenshot.
  - **Floor impact:** the first public buyer after you enters ~19% above absolute floor (a function of the 9% size, not how you buy it).

## STEP 3 -- Lock the founder bag IMMEDIATELY + post proof
- [ ] Lock/vest the ~9% for **3-6 months** via **Jupiter Lock** (lock.jup.ag, free + audited).
- [ ] Grab the **public lock link** and post it before any price hype. This is the trust anchor.

## STEP 4 -- Treasury
- [ ] Move **3% (30M)** to a clearly **labeled treasury wallet** (airdrops/rewards/utility). Keep it separate from the founder bag and the personal wallet.

## STEP 5 -- Seed socials (decoupling + disclaimer baked in)
- [ ] X + Telegram live. Pin: the story, the lock link, and the disclaimer (Theo's language).
- [ ] Messaging: $BCARDD is the **Alley Kingz** utility/fun coin. **Never** mention the casino, payouts, or "investment." Use the existing `02_Community` copy (now $BCARDD-renamed) run through the copy guard.

## STEP 6 -- Turn on the engine
- [ ] **Creator-fee faucet:** claim accrued SOL anytime via pump.fun profile -> rewards (never expires).
- [ ] Optional: use **Creator Fee Sharing** (Jan 2026, up to 10 wallets) to auto-route a slice of creator fees straight to the labeled treasury wallet.
- [ ] Stand up the **fee -> buyback-burn + airdrop** loop (off-chain automation can schedule/notify; you sign claims).
- [ ] **Graduation (info):** at ~$69k cap (~85 SOL of net buys) the curve completes and liquidity auto-migrates to **PumpSwap** (not Raydium anymore), where **LP is locked + burned automatically** -- free, irreversible, rug-proof. Point skeptics at the burned LP as proof. Post-graduation trade fee ~0.25% on PumpSwap; your creator fee continues.

## NORTH STAR (honest math -- keep visible)
- Target: **~$18-22M sustained cap -> ~$1M cashable** to you (`0.09 x cap x ~0.5` gradual-sell haircut). A $1M *cap* is NOT the goal.
- Income = the locked bag (gradual, telegraphed sells after unlock) + the creator-fee faucet (SOL per trade, no sell pressure).
- Moat = Alley Kingz utility. The game shipping first IS the strategy.

## ROLLBACK / ABORT
- Pre-deploy: abort costs nothing. Post-deploy you cannot un-launch -- so GATE 0 + STEP 3 (lock) are the irreversible-decision guards. If anything in GATE 0 is unresolved, STOP.
