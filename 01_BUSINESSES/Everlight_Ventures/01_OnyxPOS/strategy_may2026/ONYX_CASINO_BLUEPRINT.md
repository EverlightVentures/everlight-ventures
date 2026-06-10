# ONYX CASINO -- Legal Online Casino Blueprint
## From Blackjack Game to Full Casino Using Existing Infrastructure

---

## WHAT YOU ALREADY HAVE

Before building anything, here's what's already done:

| Asset | Status | Casino Application |
|-------|--------|-------------------|
| Blackjack game (server-authoritative) | Built (Django, 1,423 LOC) | Core game #1 |
| Player profiles (ranks, XP, achievements) | Built | Player identity system |
| Virtual currency (Chips + Gems) | Built | Dual currency = sweepstakes ready |
| Cosmetics store (100+ items) | Built | Monetization layer |
| Stripe integration (gem purchases) | Built | Payment processing |
| Supabase (auth, database, realtime) | Built | Player data + leaderboards |
| Oracle E5 server | Running | Game server |
| FastAPI backend (72 endpoints) | Built | Casino API foundation |
| Onyx wallet + loyalty points | Built | Casino wallet |
| Prediction market | Built | Sports betting foundation |
| Social feed + clout system | Built | Casino social features |
| AI chat (Claude) | Built | Player support + game host |
| everlightventures.io (Cloudflare) | Live | Casino frontend host |

**You're closer than you think.** The hardest parts (server-authoritative
game logic, dual currency, payments, player progression) are DONE.

---

## THE 3 PATHS TO A LEGAL CASINO

### PATH A: SWEEPSTAKES CASINO (Fastest, cheapest, US-legal)
**Model:** Chumba Casino, Stake.us, Pulsz, WOW Vegas
**Timeline:** 4-8 weeks
**Cost:** $5,000-$15,000 (legal) + dev time
**Market:** ~44 US states (excludes CA, NJ, NV, CT, NY, MT, IN, ME)
**Revenue potential:** Industry did $10.6B in 2024

### PATH B: ANJOUAN LICENSE (Crypto casino, international)
**Model:** Stake.com, Roobet, BC.Game
**Timeline:** 6-8 weeks
**Cost:** ~$25,000-$30,000 year 1
**Market:** Global minus US/UK/AU
**Revenue potential:** Crypto gambling is $100B+/year

### PATH C: BOTH (Maximum coverage)
Sweepstakes for US market + Anjouan for international.
Two brands or one brand with geo-routing.
**This is what Stake does:** Stake.com (Curacao, international) + Stake.us (sweepstakes, US)

**Recommended: PATH C.** Maximum market coverage. Use existing infrastructure for both.

---

## PATH A: SWEEPSTAKES CASINO (Deep Dive)

### How It Works Legally

US law says gambling = prize + chance + consideration (payment).
Remove "consideration" → it's a sweepstakes, not gambling. Legal.

**The dual-currency trick:**
- **Gold Coins (GC):** Purchased with real money. Play-money. No cash value.
  Like buying chips at Dave & Buster's. Entertainment only.
- **Sweeps Coins (SC):** CANNOT be purchased. Given FREE with GC purchases
  or via free entry (mail-in, social media promo, daily login bonus).
  SC can be redeemed for real cash prizes (1 SC = $1).

Because SC are free, there's no "consideration." The games use chance.
The prizes are real. But it's not gambling because you didn't pay to enter.

**Critical legal requirement:** Must offer a free Alternate Method of Entry
(AMOE). Usually: mail a stamped envelope to a PO box → receive free SC.
This is the legal escape hatch. It MUST be real and accessible.

### YOUR BLACKJACK IS ALREADY 80% SWEEPSTAKES-READY

Look at what you have:
- **Chips** (free currency, earned via play) = Gold Coins equivalent
- **Gems** (premium currency, purchased via Stripe) = Gold Coin purchases
- **Server-authoritative game logic** = required for sweepstakes legitimacy
- **Player profiles with KYC fields** = needed for prize redemption

What you need to ADD:
1. **Sweeps Coins** as a third currency (redeemable for cash)
2. **Free SC distribution** (daily login, mail-in AMOE, social media promo)
3. **SC redemption flow** (cash out to bank/PayPal/crypto when SC ≥ $50)
4. **Sweepstakes terms of service** (lawyer drafts, ~$5K-$15K)
5. **State blocking** (CA, NJ, NV, CT, NY, MT, IN, ME) via IP geolocation
6. **More games** beyond blackjack

### Currency Mapping

| Current System | Sweepstakes Equivalent | Change Needed |
|---------------|----------------------|---------------|
| Chips (free, earned) | Gold Coins (GC) | Rename. Allow purchase. |
| Gems (paid via Stripe) | Gold Coin packages | Bundle SC with every GC purchase |
| -- (doesn't exist yet) | Sweeps Coins (SC) | Add. 1 SC = $1. Redeemable. |
| XP / Rank progression | Unchanged | Keep as engagement layer |
| Cosmetics store | GC-only purchases | Cosmetics never cost SC |

### Revenue Model

Player buys 10,000 Gold Coins for $9.99.
→ They also receive 10 FREE Sweeps Coins (the SC are "free" legally).
→ Player plays blackjack with GC (entertainment) and SC (prize-eligible).
→ Player wins 25 SC playing blackjack.
→ Player redeems 25 SC for $25 cash (to their bank account).

**Your margin:** You sold $9.99 in GC. You paid out $25 in SC prizes.
Sounds like a loss? No -- the MATH works because:
- House edge on blackjack = 0.5-2% (you keep the edge)
- Not every SC is redeemed (breakage, ~15-20%)
- Players buy MORE GC to keep playing (repeat purchases)
- Industry operator margin: 30-35% of GC revenue after prizes

**At scale:** 10,000 players × $50/month average GC purchases = $500K/month
gross. At 30% margin = **$150K/month profit.**

### Games to Add (Beyond Blackjack)

You need more games to retain players. Options:

| Game | Build vs Buy | Difficulty | House Edge |
|------|-------------|-----------|------------|
| **Blackjack** | BUILT | Done | 0.5-2% |
| **Slots** (video slots) | Build or license | Medium | 2-15% |
| **Roulette** | Build | Easy | 2.7-5.3% |
| **Baccarat** | Build | Easy | 1.06-14.4% |
| **Video Poker** | Build | Medium | 0.5-5% |
| **Crash** (crypto-native) | Build | Easy | 1-4% |
| **Plinko** | Build | Easy | 1-3% |
| **Dice** | Build | Trivial | 1-2% |
| **Mines** (Minesweeper gambling) | Build | Easy | 1-3% |
| **Keno** | Build | Easy | 20-40% |
| **Live Dealer** (via API) | License (Ezugi, Evolution) | Easy integration | 0.5-5% |

**MVP recommendation:** Blackjack (done) + Roulette + Crash + Dice + Plinko.
These 5 games cover all player types and are buildable in 2-3 weeks.

### Sweepstakes Legal Checklist

- [ ] Sweepstakes attorney review ($5K-$15K)
- [ ] Terms of Service (sweepstakes rules, AMOE, state restrictions)
- [ ] Privacy Policy (CCPA + state-specific)
- [ ] AMOE mechanism (PO box + mail-in form on website)
- [ ] IP geolocation blocking (restricted states)
- [ ] KYC for SC redemption (ID verification at cashout)
- [ ] Responsible gambling features (self-exclusion, deposit limits, session limits)
- [ ] Age verification (18+ or 21+ depending on state)
- [ ] SC redemption processor (not Stripe -- use PayPal, Skrill, or crypto)

---

## PATH B: ANJOUAN CRYPTO CASINO (Deep Dive)

### Why Anjouan

| Factor | Anjouan | Curacao | Costa Rica |
|--------|---------|---------|-----------|
| Cost year 1 | ~$25K | ~$55K | ~$10K |
| Timeline | 2-4 weeks | 3-6 months | 5-6 weeks |
| Credibility | Low-medium | Medium | Very low |
| Crypto-friendly | Yes | Yes | Yes |
| US players | No | No | Technically no |
| Upgrade path | → Curacao | → Malta/MGA | → Curacao |

### How Stake.com Does It

Stake operates as Medium Rare N.V., registered in Curacao. They:
1. Accept crypto deposits only (BTC, ETH, LTC, DOGE, XRP, etc.)
2. No fiat. No bank accounts. No Visa/MC.
3. IP-block US, UK, AU, FR, NL
4. Games are provably fair (on-chain verification of RNG)
5. Revenue: estimated $2.6B in 2023. Two Australian founders.

**You can replicate this model** with Anjouan license + CoinsPaid integration.

### Crypto Casino Tech Stack (Using Your Infrastructure)

| Component | What You Use | Casino Application |
|-----------|-------------|-------------------|
| Supabase Auth | Player accounts | Player registration + KYC |
| FastAPI | Game API | Game logic server |
| Oracle E5 | Hosting | Game server + wallet |
| Django blackjack | Game logic | Blackjack (provably fair) |
| Onyx wallet system | Point balances | Crypto wallet (BTC, ETH, XLM) |
| Prediction market | Sports betting | Sportsbook (with proper license) |
| Social feed | Player community | Casino social features |
| CoinsPaid (ADD) | Crypto payments | Deposit/withdraw |
| Provably fair RNG (ADD) | Fairness verification | On-chain seed verification |

### Provably Fair System

Crypto casinos use "provably fair" instead of traditional RNG certification.
The mechanism:
1. Server generates a secret seed BEFORE the game
2. Server gives player a HASH of the seed (commitment)
3. Player provides their own seed (or uses a random one)
4. Game plays using combined seeds
5. After the game, server REVEALS the original seed
6. Player can verify: hash(revealed_seed) == committed_hash

This is cryptographically impossible to fake. Players can verify every
single hand/spin/roll was fair. No need for expensive GLI certification.

**Implementation:** ~200 lines of Python. SHA-256 hashing. Deterministic
game outcomes from combined seeds. Already standard in the industry.

---

## PATH C: BOTH (The Full Play)

### Brand Architecture

```
ONYX GAMING (parent)
├── OnyxCasino.io (sweepstakes, US market, ~44 states)
│   ├── Gold Coins + Sweeps Coins
│   ├── Blackjack, Roulette, Crash, Dice, Slots
│   ├── Stripe for GC purchases
│   ├── PayPal/Skrill for SC redemption
│   └── IP blocks: CA, NJ, NV, CT, NY, MT, IN, ME
│
├── OnyxBet.io (crypto casino, international)
│   ├── Anjouan license → upgrade to Curacao
│   ├── BTC, ETH, XLM, USDT, DOGE
│   ├── CoinsPaid for deposits/withdrawals
│   ├── Provably fair games
│   ├── Sports betting (prediction market evolved)
│   └── IP blocks: US, UK, AU, FR, NL
│
└── Shared Infrastructure
    ├── Same game engine (Django blackjack + new games)
    ├── Same Supabase database (separate schemas)
    ├── Same Oracle E5 server
    ├── Same AI (Claude for dealer chat, support)
    ├── Same social features (feed, streaks, leaderboards)
    └── Same cosmetics/progression system
```

### Revenue Projections (Both Paths Combined)

| Metric | Sweepstakes (US) | Crypto (International) | Combined |
|--------|-----------------|----------------------|----------|
| Players (Year 1) | 5,000 | 10,000 | 15,000 |
| Avg monthly spend | $50 | $200 | -- |
| Gross revenue/mo | $250K | $2M | $2.25M |
| Operator margin | 30% | 3-5% (house edge) | -- |
| Net revenue/mo | $75K | $60-100K | $135-175K |
| Annual net | $900K | $720K-$1.2M | $1.6-2.1M |

---

## HOW ONYX PLATFORM FEEDS THE CASINO

This is where your monopoly architecture becomes the moat:

| Onyx Feature | Casino Application |
|-------------|-------------------|
| **Onyx Wallet** | Casino wallet. Deposit/withdraw. Already built. |
| **Loyalty Points** | Casino rewards currency. Earn playing, spend in shop. |
| **Prediction Market** | IS the sportsbook. Evolve points → crypto/SC bets. |
| **Social Feed** | Casino social. "Big win!" posts. Leaderboard shares. |
| **Streaks** | Daily login bonus. Consecutive day bonuses. |
| **Tiers (Bronze→Obsidian)** | VIP program. Higher tiers = higher limits, better rakeback. |
| **Receipt Lottery** | Scratch-off mechanic already built. Reuse for casino bonus cards. |
| **AI Chat** | Claude as dealer personality. AI game host. Support bot. |
| **Cosmetics Store** | Avatar outfits, card backs, table felts. Already 100+ items. |
| **QR Receipts** | Affiliate/referral codes for casino signups. |
| **Merchant Network** | Bars/restaurants as casino AFFILIATES. Play at the bar. |
| **Drops** | Limited-edition casino cosmetics. Rare card backs. VIP events. |
| **NFC/Wallet Pass** | Casino loyalty card in Apple/Google Wallet. |

**The key insight:** Your Onyx neighborhood commerce platform drives
PLAYER ACQUISITION for the casino. Onyx merchants become affiliates.
Every Onyx customer is a potential casino player. The prediction market
is the gateway drug. The social feed normalizes gaming. The wallet
already holds their money. The tier system already tracks engagement.

**You're not building a casino from scratch. You're adding casino games
to an existing platform with 12 engagement systems already running.**

---

## INFRASTRUCTURE MAP

### What You Have (reuse)

```
Oracle E5 (129.159.38.250)
├── FastAPI (game server) ← already handles 72 endpoints
├── Django (blackjack app) ← server-authoritative, Stripe, profiles
├── Supabase client ← auth, database, realtime
├── n8n ← automated promotions, win notifications
├── Blinko ← player support knowledge base
└── Hive agents ← 24/7 operations, fraud detection, support
```

### What You Add

| Component | Purpose | Cost | Timeline |
|-----------|---------|------|----------|
| **Provably fair module** | RNG verification for crypto casino | $0 (build, 200 LOC) | 1 day |
| **CoinsPaid integration** | Crypto deposits/withdrawals | 0.8% per tx | 3 days |
| **SC redemption flow** | Sweeps Coins → bank/PayPal | PayPal fees | 1 week |
| **Geolocation/IP blocking** | State + country restrictions | MaxMind GeoIP2 ($0-$100) | 1 day |
| **New games: Roulette** | Second casino game | $0 (build) | 3 days |
| **New games: Crash** | Third casino game (crypto-native) | $0 (build) | 2 days |
| **New games: Dice** | Fourth casino game | $0 (build) | 1 day |
| **New games: Plinko** | Fifth casino game | $0 (build) | 2 days |
| **Sweepstakes legal** | Attorney review + ToS | $5K-$15K | 2-4 weeks |
| **Anjouan license** | International operations | ~$25K | 2-4 weeks |
| **Casino frontend** | React UI for all games | $0 (build) | 2 weeks |
| **TOTAL** | | **$30K-$40K** | **4-8 weeks** |

### Server Architecture for Casino

```
                    ┌─────────────────┐
                    │   Cloudflare    │ ← CDN, DDoS protection, geo-routing
                    │   (already own) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────┴───┐  ┌──────┴──────┐  ┌───┴──────────┐
    │ OnyxCasino  │  │  OnyxBet    │  │  Onyx POS    │
    │ .io (US)    │  │  .io (Intl) │  │  (merchants) │
    │ Sweepstakes │  │  Crypto     │  │  Commerce    │
    └──────┬──────┘  └──────┬──────┘  └──────┬───────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                   ┌────────┴────────┐
                   │  Oracle E5 VM   │
                   │  FastAPI + Django│
                   │                 │
                   │ ┌─────────────┐ │
                   │ │ Game Engine │ │ ← Blackjack, Roulette, Crash, etc.
                   │ │ (provably   │ │
                   │ │  fair RNG)  │ │
                   │ └─────────────┘ │
                   │ ┌─────────────┐ │
                   │ │   Wallet    │ │ ← GC, SC, BTC, ETH, XLM, USDT
                   │ │   Engine    │ │
                   │ └─────────────┘ │
                   │ ┌─────────────┐ │
                   │ │  Anti-Fraud │ │ ← Hive agents monitor patterns
                   │ │  + AML      │ │
                   │ └─────────────┘ │
                   └────────┬────────┘
                            │
                   ┌────────┴────────┐
                   │    Supabase     │
                   │  (all tables)   │
                   │                 │
                   │ players         │
                   │ game_sessions   │
                   │ wallets         │
                   │ transactions    │
                   │ bets            │
                   │ leaderboards    │
                   │ cosmetics       │
                   │ kyc_records     │
                   └─────────────────┘
```

---

## EXECUTION TIMELINE

### Week 1-2: Legal + Foundation
- [ ] Hire sweepstakes attorney (US market)
- [ ] Apply for Anjouan license (international market)
- [ ] Build provably fair RNG module
- [ ] Build Sweeps Coin currency into existing Chips/Gems system
- [ ] Set up CoinsPaid account for crypto processing
- [ ] Set up MaxMind GeoIP2 for geo-blocking

### Week 3-4: Games
- [ ] Build Roulette (server-authoritative, provably fair)
- [ ] Build Crash game
- [ ] Build Dice game
- [ ] Build Plinko game
- [ ] Add all games to existing Django app

### Week 5-6: Frontend + Integration
- [ ] Casino frontend (React, on separate domain)
- [ ] Wallet integration (GC/SC for sweepstakes, crypto for international)
- [ ] SC redemption flow (KYC → cashout → PayPal/bank)
- [ ] Social features (big win feed, leaderboards)
- [ ] Responsible gambling tools (limits, self-exclusion)

### Week 7-8: Launch
- [ ] Legal review complete, ToS published
- [ ] Anjouan license received
- [ ] AMOE mechanism live (mail-in form on website)
- [ ] Geo-blocking tested for all restricted jurisdictions
- [ ] Soft launch (invite-only, 100 players)
- [ ] Marketing: Onyx platform cross-promotion
- [ ] Hard launch

### Month 3+: Scale
- [ ] Add slots (license from game provider or build)
- [ ] Add live dealer (Ezugi or Evolution API)
- [ ] Upgrade to Curacao license ($55K/yr)
- [ ] Launch sportsbook (evolution of prediction market)
- [ ] Onyx merchant affiliate program (bars show casino on screens)
- [ ] Mobile app (Expo, casino module within Onyx super-app)

---

## THE MONOPOLY TIE-IN

The casino doesn't stand alone. It plugs into ALL 7 chokepoints:

1. **Payment Rail:** Casino wallet IS the Onyx wallet. Money flows through YOUR rail.
2. **Identity:** Casino profile IS the Onyx profile. One identity, one tier, one wallet.
3. **Demand Routing:** Onyx app recommends the casino to engaged users. YOU control discovery.
4. **Financial Stack:** Casino revenue funds Onyx Capital (merchant loans). The casino FINANCES the commerce platform.
5. **Social Graph:** Casino wins post to the Onyx social feed. Friends see wins → download → play.
6. **Logistics:** Onyx merchants become casino affiliates. Physical bars + digital casino = hybrid.
7. **Linguistic:** "Play on Onyx" / "Bet on Onyx" / "Won on Onyx" -- same verb, expanded meaning.

**The casino is not a separate business. It's another vertical
on the Onyx platform that shares infrastructure, users, identity,
wallet, social graph, and brand with everything else.**

Every Onyx user is a potential casino player.
Every casino player is a potential Onyx commerce user.
Every Onyx merchant is a potential casino affiliate.
The flywheel spins in both directions.

---

## RISK MATRIX

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Sweepstakes model banned in more states | High | Medium | Diversify with international crypto casino |
| Anjouan license loses credibility | Medium | Low | Upgrade to Curacao within 6 months |
| Payment processor drops you | Medium | High | Crypto-first, multiple processor redundancy |
| Player fraud / bonus abuse | High | Medium | AI fraud detection (Hive agents), velocity limits |
| Regulatory action | Low-Med | High | Compliant legal structure, attorney on retainer |
| Competition (Stake.us, Chumba) | High | Medium | Differentiation via Onyx ecosystem (commerce + casino = unique) |

---

## COMPETITIVE ADVANTAGE OVER EVERY OTHER CASINO

Every other online casino is JUST a casino. You have:

- A commerce platform feeding player acquisition (for free)
- A merchant network as physical affiliate distribution
- A social feed normalizing gambling behavior
- A prediction market as gateway to sports betting
- A loyalty system that spans commerce AND gambling
- An AI layer providing personalized game recommendations
- A creator economy producing casino content organically
- 42 AI agents running operations 24/7

**Stake has games. Chumba has sweepstakes.
You have an entire neighborhood commerce operating system
that HAPPENS to also have a casino in it.**

That's the monopoly applied to gambling.
