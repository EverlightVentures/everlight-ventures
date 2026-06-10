# $BCARDD -- Solana Fair-Launch Spec
**Date:** 2026-06-02 · **Owner:** Rich (Everlight Ventures) · **Status:** APPROVED design, pre-build
**Supersedes:** the stalled 2025 Cronos launch (legacy contract `0xc7AdBbA52EA64B008a7e5d7666876628Dc391d69`, low/no liquidity -- kept as legacy, not revived)

---

## 1. One-liner
A **dog meme coin** on **Solana**, launched fair via **pump.fun**, named after Rich's real dog **Bacardi**, built on top of existing assets (coin art, live AI blackjack dealer, NFT video). Goal: give Rich a **realistically ~$1M-cashable** founder position while staying reputable enough that strangers actually buy.

## 2. Decisions locked (from brainstorming 2026-06-02)
| Decision | Choice | Why |
|---|---|---|
| Chain | **Solana** | Where meme liquidity + attention live in 2026 |
| Vehicle | **pump.fun** fair launch | Standardized trusted contract, auto-LP to Raydium, creator-fee faucet, ~$2 to deploy |
| Name | **$BCARDD**, own-the-character | Real dog = original use, strong trademark defense; rides dog-coin meta |
| Founder bag | **9% (90M)**, publicly locked/vested 3-6mo | Bigger upside; lock keeps it from reading as a rug |
| Treasury | **3% (30M)**, labeled wallet | Funds airdrops/rewards/utility |
| Launch wallet | **Fresh Phantom**, seed only ever in Proton Pass | Exposed wallets are compromised; never launch from one |
| North Star | Coin holds **~$18-22M cap** then ~$1M cashable to Rich | Honest: not $1B (lottery), not $1M (won't clear the goal) |

## 3. Positioning & brand
- **Narrative:** "Bacardi the dog" -- real photo, real name, real story. Dog-coin lineage (DOGE/SHIB/BONK/WIF).
- **Disclaimer (everywhere):** *"$BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited."*
- **Assets on hand:** `Official_BCARDI.png`, `BCARDI_OFFICIAL_COIN.mp4`, `Official_BCARDI_LIVE_DEALER.mp4` (NFT candidate). Need a 512x512 logo crop.
- **No rum/bottle imagery** -- keeps it clearly the dog, not the liquor.

## 4. Economics -- how the money actually works
- **Supply:** 1,000,000,000 fixed (pump.fun standard; dev cannot mint more).
- **No pre-mint exists on pump.fun.** All tokens start in the bonding curve. The founder bag is acquired via a **dev buy** (see section 5) -- Rich buys ~9% at launch-floor price like everyone else. This transparency is *why* the model is trusted.
- **Two income streams:**
  1. **The bag** (9%) -- sold *gradually* into real liquidity. Illiquid early; paper value is not cash.
  2. **Creator fees** -- pump.fun pays the creator a slice of every trade in SOL (no selling, no sell-pressure). Scales with *volume*; hot coins trade 10-100x their cap. Funds buyback-burn + airdrops AND pays Rich.
- **North Star math (9% bag):** cashable is approximately `0.09 x cap x ~0.5` (gradual-sell haircut). $1M means **cap ~= $18-22M sustained**, plus fee income.

## 5. Pre-launch build checklist
- [ ] **Fresh Phantom wallet** created; seed saved ONLY to Proton Pass; funded with a little SOL.
- [ ] 512x512 logo + coin `.mp4` + dealer NFT staged.
- [ ] **X account** + **Telegram** with disclaimer in bio.
- [ ] One-page site (reuse Everlight/Cloudflare infra) -- story, how-to-buy, disclaimer, socials.
- [ ] Lock tool chosen (Streamflow or Jupiter Lock) + lock duration set (3-6mo, linear vest).
- [ ] **Dev-buy size calculated** against the LIVE bonding curve to land ~9% (see Build-time verifications).

## 6. Launch-day runbook
1. Create coin on pump.fun (name, ticker $BCARDD, logo, description + disclaimer, socials).
2. **Dev buy ~9%** in the first transaction (cheapest price the coin will ever be).
3. **Lock/vest the bag immediately** and post the lock link publicly.
4. Move 3% to the labeled treasury wallet.
5. Seed X + Telegram; pin the story + lock proof + disclaimer.
6. First airdrop wave to early holders / blackjack players.
7. Turn on the **fee then buyback-burn** loop.

## 7. Post-launch flywheel
Creator fees feed (a) **buyback + burn** $BCARDD (deflation, "number go up"), (b) **airdrops** to holders/players, (c) **game utility**: $BCARDD as chips, holder-only tables, dealer skins, NFT as OG badge. Utility is the moat -- almost no meme coin has a real product behind it; Rich does.

## 8. Risks & legal guardrails (non-negotiable)
- **Most meme coins go to zero.** Only commit SOL Rich can afford to lose.
- **The bag is illiquid** -- selling fast = self-rug. Realizing value means gradual, telegraphed sells into depth.
- **Market as fun + game, NEVER as an investment with promised returns.** Promising profit creates real legal liability. Hype the dog + dealer, not "get rich."
- **Fresh wallet only.** Rotate exposed wallets (see `reference_crypto_seed_vault`).
- Keep the **disclaimer** on every surface.

## 9. Division of labor
- **AI (off-chain only):** asset prep, site, X/Telegram copy, airdrop tooling, lock/launch checklist, fee-to-buyback automation spec, game-integration spec. **Never touches keys or deploys on-chain.**
- **Rich (on-chain, his money/keys):** create + fund wallet, click launch, execute dev buy, sign the lock, run the shredder/import for security.

## 10. Build-time verifications (confirm live before launch -- params have changed historically)
- Current pump.fun **creator-fee rate** + payout mechanics (PumpSwap vs bonding-curve era).
- Current **graduation threshold** + bonding-curve pricing, then exact SOL for a ~9% dev buy (and whether to split/time it to limit price-spike on entry).
- Lock tool that pump.fun/Raydium LPs + SPL holdings support cleanly.
- Whether a one-tx 9% dev buy spikes entry price unacceptably; consider laddering.

---
*Brainstormed + approved 2026-06-02. Next: implementation plan (writing-plans). Memory: [[project_bcardi_meme_coin]], [[reference_crypto_seed_vault]].*
