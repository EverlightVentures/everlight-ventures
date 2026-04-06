# Everlight Arcade -- Blockchain Strategy

**Author:** Everlight Ventures Strategy Team
**Date:** 2026-03-11
**Status:** Research Complete -- Awaiting Legal Review
**Related Docs:** SOCIAL_CASINO_LEGAL_RESEARCH.md, SOCIAL_CASINO_GTM_STRATEGY.md, BRAND_UNIFICATION_STRATEGY.md

---

## Executive Summary

Base (Coinbase L2) is the recommended blockchain for Everlight Arcade -- not Zilliqa. The decision comes down to ecosystem scale, developer tooling, and strategic alignment.

Key factors:

- **Ecosystem size:** Zilliqa has roughly 500K wallets. Base has 40M+. That is an 80x difference in addressable audience.
- **EVM compatibility:** Both chains support Solidity, but Base is EVM-native from day one while Zilliqa only added EVM support via its 2.0 upgrade (Feb 2026 hard fork).
- **Existing relationship:** The XLM bot already runs on Coinbase infrastructure. Base is Coinbase's own L2. The onramp, custody, and compliance tooling are already familiar.
- **Stripe stays primary:** Blockchain is an additional monetization funnel, not a replacement. Stripe handles chip bundles, VIP subscriptions, and cosmetic purchases. Crypto expands the funnel for Web3-native users.
- **Legal posture:** All tokens remain non-transferable (soulbound) until a gaming attorney reviews and greenlights transferability. This is the single most important guardrail in this entire strategy.

---

## Chain Comparison

| Factor              | Zilliqa 2.0          | Base (Coinbase L2)       | Polygon PoS            | Solana                  |
|---------------------|----------------------|--------------------------|------------------------|-------------------------|
| **Tx Cost**         | ~$0.01               | Sub-cent (<$0.01)        | ~$0.0075               | ~$0.00025               |
| **EVM Compatible**  | Yes (new, as of 2.0) | Yes (native)             | Yes (native)           | No (Rust/Anchor)        |
| **Gaming Ecosystem**| Small, emerging      | 244+ games, 7M gamers    | Massive, mature        | Large, growing          |
| **Wallet Users**    | ~500K                | 40M+                     | 200M+                  | 100M+                   |
| **Stripe Integration** | Manual/custom     | Native Coinbase onramp   | Easy (multiple bridges)| Medium complexity        |
| **Developer Tools** | Scilla + Solidity    | Full Ethereum toolchain  | Full Ethereum toolchain| Anchor, Seahorse        |
| **Grants/Funding**  | Small ecosystem fund | Coinbase ecosystem support| Polygon Ventures       | Solana Foundation       |

**Verdict:** Base wins on every metric that matters for Everlight Arcade. Polygon is a strong second choice if we ever need a multi-chain strategy. Solana is out due to non-EVM architecture. Zilliqa only makes sense if substantial grants or BCARDI strategic alignment justify the smaller ecosystem.

---

## Smart Contract Architecture

### Core Principle: Off-Chain Game, On-Chain Economy

Game logic stays entirely off-chain in Supabase and Lovable. The blockchain layer handles only the economy -- token minting, reward distribution, and NFT issuance. This keeps gameplay fast, cheap, and easy to update while giving players real ownership of earned assets.

```
+---------------------+       +------------------------+
|   LOVABLE / SUPABASE |       |    BASE L2 (ON-CHAIN)  |
|                     |       |                        |
|  Blackjack Engine   |       |  AlleyChip.sol (ERC-20)|
|  Slot Machine Logic |       |  VIPPass.sol (ERC-721) |
|  Rewards System     | ----> |  AchievementBadge.sol  |
|  Leaderboards       |       |  RewardVault.sol       |
|  User Profiles      |       |  GameOracle.sol        |
|                     |       |                        |
+---------------------+       +------------------------+
        |                              ^
        v                              |
  +-------------+              +----------------+
  | Stripe API  |              | Coinbase Onramp|
  +-------------+              +----------------+
```

### Contract Inventory

| Contract               | Standard            | Purpose                                        |
|------------------------|---------------------|------------------------------------------------|
| **AlleyChip.sol**      | ERC-20              | Utility token ($CHIP) -- earned by playing, spent on cosmetics and tournaments |
| **VIPPass.sol**        | ERC-721             | VIP membership NFT -- minted on subscription, burned on expiry |
| **AchievementBadge.sol** | Soulbound ERC-721 | Non-transferable badges minted on milestone completion |
| **RewardVault.sol**    | Custom              | Escrow contract for tournament prizes and reward distribution |
| **GameOracle.sol**     | Custom              | Bridge between off-chain game results and on-chain state updates |

### Security Considerations

- GameOracle.sol uses a multisig admin pattern -- no single key can push fraudulent results
- RewardVault.sol has time-locked withdrawals and rate limits
- All contracts audited before mainnet deployment (budget: $5K-15K for a Base-focused auditor)
- Upgradeable proxy pattern (UUPS) so we can patch without redeploying

---

## Token Economics (Dual Token Model)

### $CHIP -- Utility Token

| Property       | Value                                     |
|----------------|-------------------------------------------|
| **Type**       | ERC-20 on Base                            |
| **Supply**     | Uncapped (inflationary with burn sinks)   |
| **Earned by**  | Playing games, daily login, missions      |
| **Spent on**   | Cosmetics, tournament entries, power-ups  |
| **Burn events**| Cosmetic purchases, tournament rake, seasonal resets |

### $ALLEY -- Governance/Premium Token

| Property       | Value                                     |
|----------------|-------------------------------------------|
| **Type**       | ERC-20 on Base                            |
| **Supply**     | Fixed 100M cap (deflationary)             |
| **Earned by**  | Competitive leaderboards, special events  |
| **Purchased**  | Stripe or Coinbase onramp                 |
| **Utility**    | VIP access, governance votes, staking     |
| **Staking**    | 500 $ALLEY staked = VIP status (alternative to $4.99/mo Stripe) |

### Tokenomics Safeguards

The single biggest lesson from Axie Infinity's collapse: **burn sinks must exceed emission at all times.** If players earn faster than the economy absorbs, token value craters and the game dies.

Burn mechanisms:
- Cosmetic shop purchases (permanent burn)
- Tournament entry fees (partial burn, partial prize pool)
- Seasonal resets (unclaimed $CHIP expires)
- Upgrade forging (combine 3 common NFTs into 1 rare -- burns the commons)

Emission caps:
- Daily earning cap per player (prevents botting)
- Diminishing returns after X hours of play per day
- Anti-sybil measures tied to wallet + account verification

### VIP Dual Path

Players can access VIP through either:
1. **Stripe:** $4.99/mo subscription (simple, fiat, no crypto needed)
2. **Staking:** Lock 500 $ALLEY tokens (crypto-native path, earns staking rewards)

Both paths grant identical perks. This ensures crypto is never a barrier.

---

## Legal Risk Assessment

### The Core Legal Question

Social casinos are legal because chips have no real-world value. The moment chips become transferable on a blockchain, regulators may classify them as real-money gambling instruments.

### Key Legal Landscape (as of March 2026)

| Factor                          | Risk Level | Notes                                           |
|---------------------------------|------------|--------------------------------------------------|
| Social casino (no transfers)    | LOW        | Legal in all US states                           |
| Soulbound/non-transferable NFTs | LOW        | No monetary value, purely cosmetic/achievement   |
| Transferable utility tokens     | HIGH       | Could be classified as gambling instrument        |
| Token with secondary market     | VERY HIGH  | Almost certainly triggers gambling regulations    |
| California AB 831               | CRITICAL   | Killed sweepstakes casinos in CA effective Jan 2026 |
| Federal Wire Act                | MEDIUM     | Interstate online gambling restrictions           |

### California AB 831 -- What It Means for Us

California Assembly Bill 831, effective January 2026, banned sweepstakes casino models in the state. This law specifically targets platforms where virtual currency can be redeemed for prizes or has any path to real-world value. Since Everlight Ventures operates from California, this is directly relevant.

**Impact on our strategy:**
- Soulbound tokens and achievement NFTs are NOT affected (no redemption value)
- Transferable tokens with any buy/sell market WOULD be affected
- We must not enable any "cash out" mechanism without full legal clearance

### Safest Legal Path

1. **Phase 1-3:** All tokens are soulbound/non-transferable. Zero legal risk.
2. **Phase 4 (transfers):** Only proceed after gaming attorney review. Budget $3K-8K for a proper legal opinion.
3. **Cosmetic NFTs:** Always safe -- they are digital art, not gambling instruments.
4. **Achievement badges:** Always safe -- soulbound, non-transferable, no monetary value.

### Attorney Consultation Checklist

Before enabling any token transfers, get written legal opinions on:
- [ ] State-by-state gambling classification of transferable game tokens
- [ ] California AB 831 applicability to our specific model
- [ ] Federal Wire Act implications for cross-state token transfers
- [ ] SEC token classification (utility vs. security)
- [ ] KYC/AML requirements if tokens become transferable
- [ ] Age verification requirements for crypto-enabled gaming

---

## Revenue Projections (1K MAU Baseline)

These projections assume 1,000 monthly active users with a 5-10% conversion rate on paid features. Conservative estimates based on social casino industry benchmarks.

| Revenue Stream              | Monthly Low | Monthly High | Notes                              |
|-----------------------------|-------------|--------------|-------------------------------------|
| Chip bundles (Stripe)       | $500        | $2,000       | Core monetization, fiat payments    |
| VIP subscriptions           | $200        | $500         | $4.99/mo, 40-100 subscribers        |
| Cosmetic NFT sales          | $100        | $500         | Skins, themes, card backs           |
| NFT marketplace royalties   | $50         | $200         | 5% royalty on secondary sales       |
| Tournament entries          | $100        | $300         | Buy-in tournaments, rake model      |
| **Monthly recurring total** | **$950**    | **$3,500**   |                                     |
| Token sale (one-time)       | $5,000      | $50,000      | $ALLEY initial distribution event   |

### Scaling Model

| MAU     | Est. Monthly Revenue | Notes                           |
|---------|---------------------|---------------------------------|
| 1,000   | $950 - $3,500       | Launch phase                    |
| 5,000   | $4,750 - $17,500    | Linear scale with network effects |
| 10,000  | $12,000 - $45,000   | VIP and NFT revenue accelerates |
| 50,000  | $75,000 - $250,000  | Marketplace and tournaments dominate |

---

## Phased Rollout

### Phase 1: Foundation (Now)

**Timeline:** Current
**Blockchain involvement:** None
**Focus:** Ship the game, get users, prove retention

- Stripe handles all payments (chip bundles, VIP, cosmetics)
- Supabase handles all game state, user data, leaderboards
- Lovable handles all frontend UI
- Zero smart contracts, zero wallets, zero crypto complexity
- **Success metric:** 500+ MAU, 5%+ conversion rate

### Phase 2: Soulbound Achievement NFTs (1-2 Months Out)

**Timeline:** After Phase 1 success metrics hit
**Blockchain involvement:** Light -- read-only for most users
**Focus:** Add Web3 flavor without legal risk

- Deploy AchievementBadge.sol on Base (soulbound ERC-721)
- Optional "Connect Wallet" button in profile settings
- Mint achievement badges when milestones are completed
- Badges are non-transferable, purely cosmetic bragging rights
- Players without wallets still earn achievements (stored in Supabase)
- Wallet users get the on-chain version as a bonus
- **Success metric:** 20%+ wallet connection rate, positive user sentiment

### Phase 3: Non-Transferable $CHIP Token (3-6 Months Out)

**Timeline:** After Phase 2 and initial legal consultation
**Blockchain involvement:** Medium -- economy layer on-chain
**Focus:** Tokenize the chip economy without enabling transfers

- Deploy AlleyChip.sol on Base (ERC-20 with transfer restrictions)
- Stripe purchases mint $CHIP to player wallet
- $CHIP can be spent in-game but NOT transferred between wallets
- Deploy RewardVault.sol for tournament prize distribution
- Deploy GameOracle.sol for off-chain to on-chain result bridging
- Coinbase onramp as alternative to Stripe for purchasing chips
- **Success metric:** 30%+ of purchases through crypto onramp

### Phase 4: Full Economy (6-12 Months Out, After Legal)

**Timeline:** Only after gaming attorney greenlights
**Blockchain involvement:** Full -- open economy
**Focus:** Unlock the flywheel

- Enable $CHIP transfers between wallets
- Launch $ALLEY governance token (fixed 100M supply)
- Deploy VIPPass.sol (stake 500 $ALLEY for VIP)
- Open NFT marketplace with 5% royalty on secondary sales
- Cosmetic NFT trading between players
- Staking rewards for $ALLEY holders
- Community governance votes on game features
- **Success metric:** Positive token economics (burns > emissions), active secondary market

---

## Technical Implementation Notes

### Wallet Integration

- Use **Coinbase Wallet SDK** for seamless Base integration
- Support **WalletConnect** as fallback for MetaMask, Rainbow, etc.
- Never require a wallet -- always offer Stripe as the fiat alternative
- Embedded wallet option (Coinbase creates wallet for user, no seed phrase friction)

### Gas Abstraction

- Use **Base Paymaster** for sponsored transactions -- players never see gas fees
- Batch NFT mints during off-peak hours to minimize costs
- GameOracle posts batched results (e.g., every 10 minutes, not per-game)

### Supabase to On-Chain Bridge

```
Player wins blackjack
  -> Supabase records result
  -> Edge function queues reward
  -> Cron job (every 10 min) batches pending rewards
  -> GameOracle.sol posts batch to Base
  -> RewardVault.sol distributes $CHIP
  -> Player sees balance update in-app
```

This batching pattern keeps gas costs near zero while maintaining a trustworthy on-chain record.

---

## Zilliqa 2.0 Notes

Zilliqa is not the recommended chain, but the research is documented here for completeness and future reference -- particularly if BCARDI strategic alignment becomes relevant.

### Current State (March 2026)

- Zilliqa 2.0 mainnet launched June 2025
- Transitioned from Proof-of-Work to Proof-of-Stake
- February 2026 hard fork brought Cancun-era EVM compatibility
- Both Scilla (Zilliqa's native language) and Solidity are now supported
- ZRC-6 is Zilliqa's NFT standard (similar to ERC-721)

### Gaming Relevance

- Zilliqa has a Unity SDK for game integration (relevant for Alley Kingz mobile game if it ever goes native)
- Ecosystem grants are available but the developer community remains small
- Transaction costs are low (~$0.01) but not as low as Base or Solana

### When Zilliqa Makes Sense

Zilliqa only becomes the right choice if:
1. Substantial ecosystem grants are offered (>$50K) that offset the smaller user base
2. BCARDI token strategy requires Zilliqa-native deployment
3. The Unity SDK proves significantly superior for a future native mobile build

Until one of those conditions is met, Base remains the clear winner.

---

## Risk Matrix

| Risk                              | Likelihood | Impact   | Mitigation                                |
|-----------------------------------|------------|----------|-------------------------------------------|
| Legal challenge on token transfers | Medium     | Critical | Keep soulbound until attorney clears       |
| Token economics collapse (Axie)  | Medium     | High     | Burn > emission mandate, daily caps        |
| Smart contract exploit            | Low        | Critical | Audit before mainnet, UUPS upgradeable     |
| Low wallet adoption               | Medium     | Low      | Stripe always available, wallet optional   |
| Base network congestion           | Low        | Medium   | Batch transactions, gas abstraction        |
| Regulatory change (new state laws)| Medium     | High     | Modular design -- can disable transfers per region |
| Coinbase policy change            | Low        | High     | Contracts are on-chain, not Coinbase-dependent |

---

## Decision Log

| Date       | Decision                                    | Rationale                                      |
|------------|---------------------------------------------|------------------------------------------------|
| 2026-03-11 | Base over Zilliqa as primary chain          | 80x wallet base, native Coinbase integration   |
| 2026-03-11 | Soulbound tokens first, transfers later     | Legal safety -- CA AB 831 risk                  |
| 2026-03-11 | Dual token model ($CHIP + $ALLEY)           | Separates utility from governance/premium       |
| 2026-03-11 | Off-chain game, on-chain economy            | Speed, cost, and updatability                   |
| 2026-03-11 | Stripe stays primary, crypto is additive    | Never gate features behind wallet ownership     |

---

## Sources

- Zilliqa 2.0 FAQ and Documentation (zilliqa.com)
- CryptoPotato -- Zilliqa 2.0 coverage and analysis
- BlockNuggets -- Zilliqa gaming ecosystem reports
- Zilliqa Blog -- 2.0 mainnet and hard fork announcements
- ZRC-6 NFT Standard -- GitHub (Zilliqa)
- Stripe Crypto Onramp Documentation (stripe.com/docs)
- CoinDesk -- Tempo/Zilliqa integration reporting
- SolCard -- Solana payment integration analysis
- Fingerlakes1 -- Social casino legal landscape (US state laws)
- RotoWire -- Online gambling regulation tracker
- CoinPaper -- Legal analysis of crypto gaming tokens
- Mevx -- Base L2 gaming ecosystem data
- Coinbase Developer Docs -- Base gaming statistics and SDK
- Kreonit -- Tokenomics design patterns for gaming

---

## Next Actions

1. [ ] Ship Phase 1 (Stripe + Supabase, no blockchain) -- in progress
2. [ ] Hit 500 MAU milestone before any blockchain work
3. [ ] Budget $3K-8K for gaming attorney consultation
4. [ ] Research Base Paymaster and gas sponsorship pricing
5. [ ] Draft AlleyChip.sol and AchievementBadge.sol contracts (testnet only)
6. [ ] Evaluate Coinbase Wallet SDK embedded wallet UX
7. [ ] Set up Base Sepolia testnet environment for Phase 2 development
