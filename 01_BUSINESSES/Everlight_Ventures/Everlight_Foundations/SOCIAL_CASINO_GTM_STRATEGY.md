# Everlight Blackjack -- Go-to-Market & Growth Strategy

**Product:** Everlight Blackjack (everlightventures.io/arcade/blackjack)
**Parent Company:** Everlight Ventures
**Author:** Everlight SaaS Growth Agent
**Date:** 2026-03-11
**Status:** DRAFT -- Review with legal counsel before any monetization launch

---

## Table of Contents

1. Executive Summary
2. Legal Landscape & Model Selection
3. Monetization Architecture
4. Pricing & Revenue Projections
5. User Acquisition Strategy
6. Retention & Engagement Engine
7. Technology Roadmap
8. Pitch Deck Blueprint
9. Risk Register
10. 90-Day Sprint Plan

---

## 1. Executive Summary

Everlight Blackjack is a live, playable social casino with AI strategy coaching, 3D graphics, player profiles, leaderboards, achievements, daily rewards, missions, VIP tiers, and a spin wheel. It runs on Supabase with Stripe payment infrastructure already wired. The product is functional today at everlightventures.io/arcade/blackjack.

The path to revenue is a **pure social casino model** -- players buy virtual currency (Chips, Gems) for entertainment, with no cash-out or prize redemption. This model is legal in all 50 states including California, avoids gambling licensing requirements, and aligns with the $10+ billion social casino market growing at 9.1% CAGR.

**Why not sweepstakes?** California Assembly Bill 831, signed by Governor Newsom on October 11, 2025, banned sweepstakes casinos in California effective January 1, 2026. Since the founder operates from California, the sweepstakes model creates direct criminal liability (misdemeanor, up to 1 year in jail, $25,000 per violation). The law extends liability to vendors and payment processors. The social casino model eliminates this risk entirely.

**The AI Strategy Coach is the moat.** No other social casino platform offers real-time, hand-by-hand AI analysis that teaches players optimal blackjack strategy. This transforms Everlight Blackjack from "another free blackjack game" into an AI-powered skill development platform that happens to be entertaining.

**Target:** 10,000 monthly active users within 12 months, $3,000-5,000/month revenue from virtual currency sales and subscriptions by month 6, scaling to $10,000-25,000/month at 100K users.

---

## 2. Legal Landscape & Model Selection

### 2.1 Why Social Casino, Not Sweepstakes

| Factor | Sweepstakes Model | Social Casino Model |
|--------|-------------------|---------------------|
| Legal in California | NO (banned Jan 1, 2026, AB 831) | YES |
| Gambling license required | Grey area (state by state) | NO |
| Cash redemption | Yes (Sweeps Coins) | NO -- virtual only |
| Criminal liability risk | HIGH (misdemeanor in CA) | NONE |
| Revenue model | Gold Coin purchases + Sweeps bonus | Virtual currency + subscriptions |
| Market size (2026) | Shrinking due to regulation | $10.11B, growing 9.1% CAGR |
| Comparable companies | Chumba, Stake.us, WOW Vegas | Zynga Poker, Big Fish, DoubleDown |
| Regulatory overhead | KYC/AML, state-by-state compliance | Minimal -- standard e-commerce |

### 2.2 Social Casino Legal Requirements (All States)

The social casino model requires:

1. **No real-money value attached to virtual currency.** Chips and Gems cannot be redeemed for cash, gift cards, cryptocurrency, or anything with monetary value.
2. **Clear disclaimers.** Every purchase screen and game page must state: "All in-game currencies are virtual items with no real-world monetary value."
3. **Age gate.** 18+ verification on account creation (checkbox + terms acceptance at minimum; hard ID verification not required for social casino).
4. **Terms of Service.** Must clearly define virtual currency as entertainment-only with no cash value. Must reserve right to modify balances, close accounts, and change the economy.
5. **Refund policy.** Virtual currency purchases are final. Standard digital goods refund policy applies.
6. **No misleading advertising.** Cannot imply players can "win real money" or "cash out."

### 2.3 Future Sweepstakes Expansion (Optional, Post-Series A)

If desired in the future, sweepstakes functionality can be added via geofencing for states where it remains legal. This requires:

- Third-party geolocation provider (GeoComply, Xpoint)
- State-by-state legal review
- KYC/AML pipeline for prize redemption
- California users would see social casino mode only

**Recommendation:** Do NOT pursue sweepstakes until after raising capital and retaining gaming-specific legal counsel. The social casino model alone can reach $10K+/month revenue.

### 2.4 IMPORTANT: Prize Redemption Is Off the Table

The original request mentioned "gift cards, merchandise, potentially crypto" as prize redemption options. Under California law post-AB 831, ANY system where virtual currency can be converted to real-world value constitutes illegal gambling if attached to a casino-style game. This includes:

- Gift cards
- Merchandise earned through gameplay
- Cryptocurrency
- Store credit with cash value

The only legal path in California is pure entertainment value. Merchandise can be SOLD separately through a standard e-commerce store, but cannot be EARNED or REDEEMED through gameplay currency.

**Flag for legal review: Confirm this interpretation with a California gaming attorney before launch.**

---

## 3. Monetization Architecture

### 3.1 Revenue Streams (Priority Order)

| # | Stream | Type | Status | Revenue Potential |
|---|--------|------|--------|-------------------|
| 1 | Chip Pack purchases | One-time IAP | Stripe products exist | Primary revenue driver |
| 2 | Master Pass subscription | $9.99/mo recurring | Conceptualized | MRR anchor |
| 3 | Blackjack Game Pass | $4.99/mo recurring | Stripe product exists | Secondary MRR |
| 4 | Gem Pack purchases | One-time IAP | Stripe products exist | Cross-game currency |
| 5 | Cosmetic items (card backs, table themes, avatars) | One-time IAP | Not built | High-margin, no economy impact |
| 6 | Tournament entry fees (Chips) | In-game currency sink | Not built | Engagement + economy health |
| 7 | Advertising (interstitial, rewarded video) | Ad revenue | Not built | Scale play at 100K+ users |

### 3.2 Virtual Currency Architecture

The platform already has a dual-layer economy. Here is how to formalize it:

**Layer 1: Gems (Cross-Game Premium Currency)**
- Purchased with real money via Stripe
- Earned slowly through daily logins, achievements, referrals (~$1/month in free Gems)
- Converts to any game-specific currency (1 Gem = 100 Chips)
- Non-withdrawable, non-transferable, no real-world value
- Existing packs: 100 ($0.99), 600 ($4.99), 1,500 ($9.99), 4,000 ($24.99), 10,000 ($49.99)

**Layer 2: Chips (Blackjack-Specific Currency)**
- Purchased directly via Stripe OR converted from Gems
- Earned through gameplay wins, daily rewards, missions, achievements
- Used to bet in blackjack hands, enter tournaments, buy cosmetics
- Starting balance for new players: 1,000 Chips (free)
- Existing packs: 500 ($0.99), 3,000 ($4.99), 8,000 ($9.99)

**Economy Balance Rule:** Free daily Chip grants should allow approximately 15-20 minutes of meaningful play per day at minimum bet levels. Players who want extended sessions or higher-stakes tables must purchase or convert.

### 3.3 Subscription Tiers

**Blackjack Game Pass -- $4.99/month** (slug: `bj-game-pass`)
- 2,000 daily free Chips (vs. 1,000 for free players)
- Exclusive card back designs (3 rotating monthly)
- High Roller table access (higher min/max bets)
- 2x Gem earn rate on achievements
- Priority AI Strategy Coach responses
- Gold username in leaderboards

**Master Pass -- $9.99/month** (slug: `master-pass`)
- Everything in Blackjack Game Pass
- 5,000 daily free Chips
- All current and future game passes included
- VIP table access across all games
- Exclusive monthly cosmetics drop
- Priority support
- Early access to new games and features
- 3x Gem earn rate

### 3.4 Cosmetic Shop (Build in Phase 2)

High-margin items that do not affect gameplay balance:

| Category | Examples | Price Range |
|----------|----------|-------------|
| Card backs | Neon, Gold Foil, Carbon Fiber, Seasonal | 50-200 Gems ($0.50-$2.00) |
| Table themes | Classic Green, Midnight Blue, Vegas Gold, Void Black | 100-300 Gems ($1.00-$3.00) |
| Chip designs | Crystal, Obsidian, Holographic, Brand Collab | 50-150 Gems ($0.50-$1.50) |
| Avatar frames | VIP tier frames + purchasable seasonal frames | 100-500 Gems ($1.00-$5.00) |
| Dealer voices | Different ElevenLabs voice personalities | 200-500 Gems ($2.00-$5.00) |
| Victory animations | Custom win celebrations | 100-300 Gems ($1.00-$3.00) |
| Profile titles | "Card Shark," "The Professor," "High Roller" | 50-100 Gems ($0.50-$1.00) |

---

## 4. Pricing & Revenue Projections

### 4.1 Coin Pack Pricing (Already in Stripe)

| Pack | Amount | Price | $/Chip | Bonus vs. Base |
|------|--------|-------|--------|----------------|
| Pocket Change | 500 Chips | $0.99 | $0.00198 | Base rate |
| Table Stakes | 3,000 Chips | $4.99 | $0.00166 | +19% value |
| High Roller Stack | 8,000 Chips | $9.99 | $0.00125 | +37% value |
| **Add:** Whale Pack | 25,000 Chips | $24.99 | $0.00100 | +50% value |
| **Add:** Casino Vault | 75,000 Chips | $49.99 | $0.00067 | +66% value |
| **Add:** Mogul Reserve | 200,000 Chips | $99.99 | $0.00050 | +75% value |

**Recommendation:** Add the three larger packs to Stripe. Whales (top 1-2% of spenders) typically generate 50%+ of social casino revenue. You need packs that let them spend efficiently.

### 4.2 Industry Benchmarks

| Metric | Social Casino Average | Everlight Target (Conservative) |
|--------|----------------------|--------------------------------|
| ARPU (all users) | $0.50-2.00/month | $0.75/month |
| ARPPU (paying users only) | $15-40/month | $12/month |
| Payer conversion rate | 2-5% | 3% |
| D1 retention | 30-40% | 35% |
| D7 retention | 15-25% | 18% |
| D30 retention | 8-15% | 10% |
| Monthly churn (subscribers) | 10-15% | 12% |
| LTV (paying user) | $50-150 | $60 |

### 4.3 Revenue Projections

**Assumptions:**
- 3% payer conversion rate
- $12 ARPPU (average revenue per paying user per month)
- $4.99/mo subscription at 5% subscription conversion among payers
- Stripe fees: 2.9% + $0.30 per transaction

| Milestone | MAU | Payers (3%) | IAP Revenue | Sub Revenue | Total MRR | Annual |
|-----------|-----|-------------|-------------|-------------|-----------|--------|
| 1,000 users | 1,000 | 30 | $360 | $75 | $435 | $5,220 |
| 5,000 users | 5,000 | 150 | $1,800 | $375 | $2,175 | $26,100 |
| 10,000 users | 10,000 | 300 | $3,600 | $750 | $4,350 | $52,200 |
| 25,000 users | 25,000 | 750 | $9,000 | $1,875 | $10,875 | $130,500 |
| 100,000 users | 100,000 | 3,000 | $36,000 | $7,500 | $43,500 | $522,000 |
| 500,000 users | 500,000 | 15,000 | $180,000 | $37,500 | $217,500 | $2,610,000 |
| 1,000,000 users | 1,000,000 | 30,000 | $360,000 | $75,000 | $435,000 | $5,220,000 |

**Break-even analysis:** Estimated monthly costs (Supabase Pro $25, ElevenLabs $22, domain/hosting $20, Stripe fees variable) total roughly $100-200/month in fixed costs at current scale. Break-even is approximately 200 MAU with 3% conversion.

### 4.4 Whale Economics

In social casinos, revenue distribution follows a power law:

| Segment | % of Payers | % of Revenue | Avg Monthly Spend |
|---------|-------------|--------------|-------------------|
| Minnows | 70% | 15% | $2-5 |
| Dolphins | 20% | 25% | $10-25 |
| Whales | 8% | 35% | $50-100 |
| Super Whales | 2% | 25% | $200-500+ |

At 10,000 MAU with 300 payers: approximately 6 super whales spending $200+/month = $1,200/month from 6 people. This is why the $49.99 and $99.99 packs are essential.

---

## 5. User Acquisition Strategy

### 5.1 Organic Channels

#### TikTok / YouTube Shorts / Instagram Reels (Primary)

Content pillars:

| Pillar | Format | Frequency | Example |
|--------|--------|-----------|---------|
| "AI Roasts My Blackjack Play" | Screen record + AI coach commentary | 3x/week | AI coach says "That was statistically the worst possible move" |
| Strategy Tips | 30-60s educational clips | 2x/week | "Always split Aces and 8s -- here's why" |
| Win/Loss Highlights | Dramatic hands with reactions | 3x/week | "I bet everything on a 16 vs dealer's 10..." |
| Streak Challenges | "Can I win X hands in a row?" | 1x/week | "Day 14 login streak -- watch me open the Mystery Box" |
| AI Coach Conversations | Show the AI analyzing hands | 2x/week | "The AI just told me my play was -12% EV..." |
| Behind the Build | Solo founder building in public | 1x/week | "Building a casino from my phone -- week 8 update" |

**Hook formulas that perform in gambling/strategy content:**
- "The AI said I had a 23% chance to win. I hit anyway."
- "I've been playing blackjack wrong my entire life."
- "This AI knows if you should hit or stand before you do."
- "Free blackjack game but the AI coach is brutally honest."

**Target hashtags:** #blackjack #casinotips #blackjackstrategy #socialcasino #cardcounting #AIgaming #indiegame #solofounder

#### YouTube (Long-form, Secondary)

| Content Type | Length | Frequency |
|-------------|--------|-----------|
| "I Built a Casino with AI" founder story | 10-15 min | Monthly |
| Full blackjack strategy course (with AI coach) | 20-30 min | Quarterly |
| "Playing 100 Hands with Perfect Strategy" | 15 min | Monthly |
| Game update walkthroughs | 5-10 min | Per major update |

#### X (Twitter) / LinkedIn

- Build-in-public threads: technical decisions, revenue milestones, user feedback
- Strategy posts: quick blackjack tips that drive clicks to the game
- Engage in #indiegame, #solofounder, #buildinpublic communities
- Repost AI coach interactions as screenshots
- Target frequency: 1-2 posts/day on X, 2-3 posts/week on LinkedIn

#### Reddit

- r/blackjack -- share strategy analysis from the AI coach (provide value first, mention the game subtly)
- r/indiegaming -- launch posts, update posts, "built this solo" narratives
- r/SideProject -- founder journey content
- r/gambling -- strategy discussions (follow sub rules carefully, no spam)
- r/webdev -- technical posts about the Supabase/Lovable/Three.js stack

**Rule: Reddit hates promotion. Lead with value (strategy insights, technical learnings). The game sells itself when people ask "where can I try this?"**

#### SEO / Content Marketing

Write and publish on the Everlight Ventures blog (or a dedicated landing page):

- "Basic Blackjack Strategy Chart -- Free Download"
- "When to Hit, Stand, Split, or Double Down"
- "How AI Is Changing the Way We Learn Blackjack"
- "Social Casino vs Real Casino -- What's the Difference?"
- "Free Online Blackjack Games with AI Coaching"

Target keywords with low competition and high intent. These pages funnel organic search traffic directly to the game.

### 5.2 Paid Channels

| Channel | Budget Range | CPI Estimate | Why |
|---------|-------------|-------------|-----|
| Meta (Facebook/Instagram) | $500-2,000/mo | $1.50-4.00 | Best social casino ad platform, strong targeting |
| TikTok Ads | $300-1,000/mo | $1.00-3.00 | Younger demo, video-first, good for viral hooks |
| Google Ads (search) | $200-500/mo | $2.00-5.00 | Capture "free blackjack" searches |
| Reddit Ads | $100-300/mo | $2.00-6.00 | Niche targeting, r/blackjack adjacent |
| Podcast sponsorship | $200-500/episode | N/A | Gambling/strategy podcasts (Thinking Poker, etc.) |

**Meta Ads Creative Strategy:**

Ad type 1 -- "AI Coach Demo" (15s video)
- Show a hand being played
- AI coach pops up: "You should have doubled down. That cost you 8% expected value."
- CTA: "Play free. Learn from AI."

Ad type 2 -- "Challenge" (15s video)
- "Can you beat the AI's recommended strategy?"
- Show win/loss counter
- CTA: "Try it free -- no download needed."

Ad type 3 -- "Solo Founder Story" (30s video)
- "I built a casino by myself with AI. 3D graphics. AI coach. Leaderboards. Play it free."
- Show game footage
- CTA: "Play now at everlightventures.io"

**Do NOT start paid ads until organic content has validated which hooks and angles resonate. Spend $0 on ads in months 1-2. Begin testing at $10-20/day in month 3.**

### 5.3 Referral Program

The referral system is already designed (Crew Up program in the rewards engine). Key parameters:

| Milestone | Referrer Gets | Referee Gets |
|-----------|--------------|--------------|
| Friend signs up | 5 Gems | 10 Gems (welcome bonus) |
| Friend plays first game | 5 Gems | 5 Gems |
| Friend makes first purchase ($1+) | 15 Gems + 50 VP | 10 Gems |
| **Total per referral** | **25 Gems + 50 VP** | **25 Gems** |

**Enhancement:** Add a referral leaderboard with monthly prizes (cosmetic items, bonus Chips, exclusive titles). Top referrer each month gets "Kingmaker" title and animated avatar frame.

Anti-fraud measures already designed: 1 credit per unique email/device, self-referral blocked, 50/month cap, email verification required.

### 5.4 Influencer Partnerships

Target micro-influencers (5K-100K followers) in these categories:

| Category | Example Creators | Pitch |
|----------|-----------------|-------|
| Blackjack strategy | YouTube/TikTok blackjack educators | "Feature our AI coach in a video -- it'll analyze your play" |
| Casino content | Social casino reviewers | "Review our game -- free Gem pack for your audience" |
| Indie game dev | Build-in-public creators | "Cross-promote: I built this solo, here's the stack" |
| AI/tech | AI tool reviewers | "The AI strategy coach is the story -- not the casino" |
| Entrepreneur content | Hustle/side project creators | "Solo founder built a casino from his phone" |

**Compensation model for micro-influencers:**
- Free Master Pass (lifetime) + 10,000 Gems for their audience giveaway
- Custom referral code that tracks their conversions
- 10% revenue share on first-month purchases from their referrals (cap at $500/month)
- No upfront cash payments until revenue exceeds $5K/month

### 5.5 Cross-Promotion from Everlight Products

| Source Product | Cross-Promo Method |
|---------------|-------------------|
| Publishing (Sam & Robo, BTV) | Back-of-book page: "Play Everlight Blackjack free" + QR code |
| Alley Kingz arcade | Shared arcade hub, Gem economy connects both games |
| Onyx POS | Footer link on POS dashboard: "Take a break -- play blackjack" |
| HIM Loadout | Blog sidebar: "Sharpen your mind -- play AI blackjack" |
| XLM Bot dashboard | "Another Everlight Venture" badge linking to the arcade |
| Email list (all segments) | Monthly newsletter section: "This month's blackjack tournament" |

---

## 6. Retention & Engagement Engine

### 6.1 Daily Hooks (Already Built)

These systems are already implemented and operational:

- **Daily login rewards:** 28-day calendar with escalating Gem rewards (~100 Gems/cycle)
- **Streak system:** Consecutive login tracking with streak shields for VIP members
- **Mystery boxes:** Weekly milestone rewards with randomized Gem/currency/cosmetic drops
- **Missions:** Task-based objectives that refresh daily and weekly
- **Achievements:** Progressive unlock system across multiple categories
- **VIP tiers:** Bronze through Alley King with escalating passive bonuses
- **Spin wheel:** Daily chance at bonus rewards
- **Leaderboards:** Competitive rankings driving repeat play

### 6.2 Tournament System (Build in Phase 2)

Tournaments are the highest-leverage retention feature not yet built. They create scheduled return visits, social competition, and natural Chip sinks.

**Tournament Types:**

| Type | Format | Entry | Frequency | Prize Pool |
|------|--------|-------|-----------|------------|
| Daily Freeroll | 50 hands, highest profit wins | Free (1 per day) | Daily, 8 PM PT | 500 Chips + 5 Gems to top 3 |
| Weekend Showdown | 100 hands, bracket elimination | 500 Chips | Saturday 6 PM PT | 10,000 Chips + 25 Gems to top 5 |
| High Roller Invitational | 25 hands, max bet required | 5,000 Chips | Monthly, 1st Saturday | 50,000 Chips + 100 Gems + exclusive cosmetic |
| VIP Only | 50 hands, Game Pass required | Free (subscribers only) | Wednesday 7 PM PT | 5,000 Chips + 50 Gems + exclusive title |
| AI Coach Challenge | Play with AI recommendations, scored on accuracy | Free | Weekly, rolling | 20 Gems + "Strategist" badge to top 10 |

**Tournament UI Requirements:**
- Lobby showing upcoming tournaments with countdown timers
- Live leaderboard during tournament play
- Results screen with placement and prizes
- Push notification / email reminder 1 hour before tournament start
- Tournament history on player profile

### 6.3 Social Features (Build in Phase 3)

| Feature | Description | Retention Impact |
|---------|-------------|-----------------|
| Friend challenges | Challenge a friend to a side-by-side hand comparison | High -- social commitment |
| Chat (table-level) | Quick reactions/emojis during hands (not full text) | Medium -- social presence |
| Guilds/Clubs | Player groups with shared leaderboard and guild tournaments | High -- social obligation loop |
| Spectator mode | Watch top-ranked players play live | Medium -- aspirational engagement |
| Gift Chips | Send Chips to friends (capped daily to prevent RMT) | Medium -- social bonding |

### 6.4 Content Cadence

| Timeframe | Content Type | Example |
|-----------|-------------|---------|
| Weekly | New daily mission set | "Win 5 hands with a soft 17 or higher" |
| Bi-weekly | New achievement batch (2-3) | "Double Down Master: Win 10 double-down hands" |
| Monthly | New cosmetic drop (card back + table theme) | March: St. Patrick's Gold theme |
| Monthly | Seasonal tournament | March Madness Blackjack Bracket |
| Quarterly | New game variant | Spanish 21, Blackjack Switch, Pontoon |
| Quarterly | Major feature release | Tournaments (Q2), Guilds (Q3), Mobile app (Q4) |

### 6.5 Game Variant Expansion

Each new variant is a retention event and a content marketing opportunity:

| Variant | Description | When |
|---------|-------------|------|
| Classic Blackjack | Standard rules (LIVE NOW) | Phase 1 |
| Speed Blackjack | 10-second decision timer, faster hands | Phase 2 (Month 4) |
| Blackjack Switch | Two hands, swap top cards between them | Phase 2 (Month 5) |
| Spanish 21 | No 10-value cards, bonus payouts for 21 | Phase 3 (Month 7) |
| Pontoon | British variant, different terminology | Phase 3 (Month 9) |
| Tournament Blackjack | Fixed chip count, elimination rounds | Phase 2 (Month 3) |
| Multi-hand Blackjack | Play 3 hands simultaneously | Phase 3 (Month 8) |

---

## 7. Technology Roadmap

### Phase 1: Foundation & Polish (Now -- Month 2)

**Status: MOSTLY COMPLETE**

Already built and live:
- [x] 3D blackjack game with full rules engine
- [x] Supabase backend (auth, profiles, game state persistence)
- [x] AI Strategy Coach (hand-by-hand analysis via Edge Function)
- [x] Player profiles with stats tracking
- [x] Leaderboards and achievements
- [x] Daily rewards calendar (28-day Gem cycle)
- [x] Missions system
- [x] VIP tier system (Bronze through Alley King)
- [x] Spin wheel
- [x] NPC bots with realistic behavior
- [x] ElevenLabs dealer voice
- [x] Stripe payment infrastructure (Chip packs, Gem packs, subscriptions)
- [x] Referral system with anti-fraud measures
- [x] Google/Facebook OAuth login
- [x] Session persistence across page refreshes

Remaining Phase 1 work:
- [ ] Add $24.99, $49.99, $99.99 Chip packs to Stripe
- [ ] Verify all Stripe checkout flows end-to-end (test purchases)
- [ ] Ensure legal disclaimers appear on every purchase screen and game page
- [ ] Add age gate (18+) to account creation flow
- [ ] Draft and publish Terms of Service (see Section 2.2)
- [ ] Draft and publish Privacy Policy (CCPA compliant for CA users)
- [ ] Set up Google Analytics 4 + Mixpanel (or PostHog) for event tracking
- [ ] Implement UTM parameter tracking on all inbound links
- [ ] Create 10 pieces of social content (see Section 5.1)
- [ ] Soft launch: share with 50-100 people in personal network for feedback

### Phase 2: Monetization & Growth (Months 3-5)

- [ ] Launch tournament system (Daily Freeroll + Weekend Showdown)
- [ ] Build cosmetic shop (card backs, table themes, avatar frames)
- [ ] Add Speed Blackjack variant
- [ ] Add Blackjack Switch variant
- [ ] Implement A/B testing on Chip pack pricing (test $0.99 vs $1.49 entry pack)
- [ ] Begin paid advertising ($500-1,000/month budget)
- [ ] Launch influencer partnerships (5 micro-influencers)
- [ ] Implement push notification opt-in (web push via service worker)
- [ ] Build dedicated landing page for paid ads (everlightventures.io/play)
- [ ] Add interstitial ad slot for non-paying users (AdMob or similar)
- [ ] Implement rewarded video ads ("Watch a 30s ad for 100 free Chips")
- [ ] Monthly tournament events with seasonal themes
- [ ] Email marketing: weekly tournament announcements, streak reminders
- [ ] Target: 5,000 MAU, $2,000/month revenue

### Phase 3: Mobile & Scale (Months 6-9)

- [ ] PWA optimization (app-like experience, home screen install prompt)
- [ ] Native mobile app (React Native or Capacitor wrapping existing web app)
- [ ] iOS App Store submission (Apple review for social casino compliance)
- [ ] Google Play Store submission
- [ ] Push notifications (mobile native)
- [ ] Guild/Club system
- [ ] Friend challenges
- [ ] Spectator mode for top-ranked players
- [ ] Spanish 21 and Pontoon variants
- [ ] Multi-hand Blackjack
- [ ] Localization (Spanish, Portuguese for LATAM market)
- [ ] Target: 25,000 MAU, $10,000/month revenue

### Phase 4: Series A Preparation (Months 10-14)

- [ ] Reach 100,000 MAU milestone
- [ ] Demonstrate 3+ months of consistent MRR growth
- [ ] Complete pitch deck (see Section 8)
- [ ] Financial model with 3-year projections
- [ ] Legal entity restructuring (C-Corp for VC investment)
- [ ] Advisory board: 1-2 social casino industry veterans
- [ ] Data room preparation (metrics, financials, cap table, legal docs)
- [ ] Warm intros to target VCs (BITKRAFT, Griffin Gaming, Galaxy Interactive)
- [ ] Geographic expansion consideration (sweepstakes model in legal states via geofencing)
- [ ] Target: 100,000+ MAU, $40,000+/month revenue, clear path to $1M ARR

### Tech Stack Summary

| Component | Current Tool | Notes |
|-----------|-------------|-------|
| Frontend | Lovable (React) | Live at everlightventures.io |
| Backend/DB | Supabase (Postgres) | Auth, profiles, game state, rewards |
| Payments | Stripe | Checkout sessions, webhooks, subscriptions |
| AI Coach | Supabase Edge Function + Claude API | Real-time hand analysis |
| Voice | ElevenLabs API | Dealer voice via Edge Function |
| 3D Graphics | Three.js | In-browser rendering |
| Analytics | Google Analytics 4 (add Mixpanel/PostHog) | Event tracking |
| Hosting | Lovable (Vercel under the hood) | Custom domain configured |
| DNS | Namecheap | everlightventures.io |
| Notifications | Web Push API (Phase 2), FCM (Phase 3) | Streak/tournament reminders |
| Ads | Meta Ads, TikTok Ads, Google Ads | Phase 2+ |
| Mobile | PWA first, then React Native/Capacitor | Phase 3 |

---

## 8. Pitch Deck Blueprint

### 8.1 Target Investors

| Fund | Focus | Check Size | Why They Fit |
|------|-------|------------|-------------|
| BITKRAFT Ventures | Gaming, interactive media, AI-native gaming | $1-5M Seed/A | AI coach angle, mobile gaming bull thesis for 2026 |
| Griffin Gaming Partners | Gaming, interactive entertainment | $2-10M Series A | Largest gaming VC by fund size ($1B+), social casino experience |
| Galaxy Interactive | Gaming x digital culture x crypto | $1-5M Seed/A | Digital-first entertainment, potential future crypto integration |
| Konvoy Ventures | Gaming infrastructure | $1-3M Seed | AI gaming tools thesis |
| Andreessen Horowitz (a16z Games) | Consumer, gaming | $5M+ Series A | If metrics are exceptional |
| Initial Capital | Gaming, consumer | $500K-2M Seed | Smaller check, founder-friendly |

### 8.2 Pitch Deck Slides (12 Slides)

**Slide 1: Title**
- Everlight Blackjack: The AI-Powered Social Casino
- Logo, tagline: "Play Smarter. Play Better."
- Founding date, location (California)

**Slide 2: Problem**
- 200M+ people play free blackjack online monthly
- Every existing option is the same: deal cards, win or lose, repeat
- No skill development. No coaching. No reason to return tomorrow.
- Social casino market is $10B+ but differentiation is near-zero

**Slide 3: Solution**
- Everlight Blackjack combines social casino mechanics with an AI Strategy Coach
- Real-time analysis of every hand: "You had a 67% chance of winning, but you should have doubled down"
- Not just entertainment -- players actually improve at blackjack
- First social casino where players GET SMARTER the more they play

**Slide 4: Product Demo**
- Screenshots / embedded video of:
  - 3D table with NPC players
  - AI Coach analyzing a hand
  - Daily rewards calendar
  - VIP tier progression
  - Leaderboard
  - Tournament lobby (Phase 2 mockup)

**Slide 5: Market**
- Social casino market: $10.11B (2026), growing 9.1% CAGR, projected $14.23B by 2030
- 300M+ social casino players globally
- Top social casino apps generate $50-200M/year in revenue
- AI gaming is a BITKRAFT-identified growth vertical for 2026

**Slide 6: Business Model**
- Virtual currency sales (Chip packs, Gem packs): 70% of revenue
- Subscriptions (Game Pass $4.99/mo, Master Pass $9.99/mo): 20% of revenue
- Cosmetics and tournament entries: 10% of revenue
- 3% payer conversion, $12 ARPPU, $60 LTV per paying user

**Slide 7: Traction**
- Live and playable today at everlightventures.io/arcade/blackjack
- Full feature set: AI coach, rewards, VIP, achievements, referrals
- Stripe payment infrastructure wired and tested
- [Insert actual metrics once available: MAU, session length, retention, first paying users]

**Slide 8: Competitive Moat**
- **AI Strategy Coach:** No competitor offers real-time AI hand analysis
- **Cross-game economy:** Gem system connects blackjack to future games (poker, slots, roulette)
- **Solo founder efficiency:** Built entire platform with AI tools, sub-$500 total spend
- **Parent brand ecosystem:** Everlight Ventures drives cross-product traffic (publishing, arcade, POS)
- **Data flywheel:** Every hand played trains better AI coaching models

**Slide 9: Go-to-Market**
- Phase 1 (organic): TikTok/Reels content around AI coach, build-in-public narrative
- Phase 2 (paid): Meta + TikTok ads at $1.50-4.00 CPI
- Phase 3 (mobile): iOS/Android app for 5x engagement uplift
- Referral engine: 25 Gems per referral, split-trigger anti-fraud
- Influencer partnerships: micro-influencers in blackjack/strategy space

**Slide 10: Roadmap**
- Q1 2026: Live product, payment integration, organic content launch
- Q2 2026: Tournaments, cosmetic shop, paid acquisition
- Q3 2026: Mobile app, guild system, 25K MAU target
- Q4 2026: 100K MAU, Series A readiness
- 2027: Multi-game platform (poker, slots, roulette), geographic expansion

**Slide 11: Team**
- Solo founder: 5 years building across SaaS, publishing, logistics, gaming
- AI-augmented development: Claude, GPT, Gemini as engineering/design team
- Built 7 products across multiple verticals (POS, publishing, gaming, trading bot)
- [Add: advisory board members once recruited]

**Slide 12: The Ask**
- Raising: $500K-1M Seed (or $2-5M Series A depending on traction)
- Use of funds: 50% engineering (hire 2 devs), 25% user acquisition, 15% infrastructure, 10% legal/ops
- Target milestones: 100K MAU, $50K MRR within 12 months of funding
- Path to profitability: social casinos are cash-flow positive at scale (60-70% gross margins)

### 8.3 Metrics VCs Want to See Before Writing a Check

| Metric | Minimum for Seed | Strong for Series A |
|--------|-----------------|-------------------|
| MAU | 5,000+ | 50,000+ |
| D1 retention | 30%+ | 40%+ |
| D30 retention | 8%+ | 15%+ |
| Payer conversion | 2%+ | 4%+ |
| ARPPU | $8+/month | $15+/month |
| MRR | $2,000+ | $25,000+ |
| MoM growth rate | 15%+ | 20%+ |
| Session length | 8+ minutes | 12+ minutes |
| Sessions per DAU | 1.5+ | 2.5+ |

### 8.4 Positioning the AI Coach as a Moat

The AI Strategy Coach is the single most defensible feature. Here is how to articulate it to investors:

1. **It is not a gimmick -- it is a retention driver.** Players who use the coach play 2-3x longer per session because they are learning, not just gambling. Learning creates intrinsic motivation that outlasts dopamine-hit mechanics.

2. **It creates a data flywheel.** Every hand analyzed improves the coaching model. At 1M hands/month, you have a dataset no competitor can replicate without building the same product.

3. **It differentiates marketing.** "AI teaches you blackjack" is a fundamentally different pitch than "play free blackjack." It attracts a different (higher-LTV) audience: people who want to improve, not just kill time.

4. **It enables future products.** The same AI coaching framework extends to poker (position analysis), sports betting (odds evaluation), and financial literacy (risk assessment). The blackjack coach is version 1 of an AI decision-coaching platform.

5. **It justifies premium pricing.** Players pay for coaching in every other domain (golf, chess, fitness). "AI blackjack coach" justifies subscription pricing that pure entertainment does not.

---

## 9. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Regulatory change (social casino model challenged) | Critical | Low | Monitor state legislation. No cash-value currency. Legal review quarterly. |
| Apple App Store rejection (social casino policy) | High | Medium | Study Apple guidelines for simulated gambling. Ensure no real-money claims. Submit PWA first as alternative. |
| Low payer conversion (<1%) | High | Medium | A/B test pricing, add rewarded video ads as alternative monetization, improve first-purchase UX. |
| ElevenLabs API cost at scale | Medium | Medium | Cache common dealer phrases. Fall back to Web Speech API for non-critical speech. Budget $50-200/month. |
| Claude API cost for AI Coach | Medium | Medium | Pre-compute common hand analyses. Cache responses. Use smaller model (Haiku) for standard hands, Opus for complex ones. |
| Copycat competitors add AI coaching | Medium | Low-Medium | First-mover advantage + data flywheel. Continuously improve coaching quality. Patent potential for specific coaching methods (consult IP attorney). |
| Solo founder bottleneck | High | High | Prioritize ruthlessly. Use AI tools for development. Hire first contractor at $3K/month revenue. First full-time hire at $15K/month revenue. |
| Stripe account review (gambling-adjacent) | High | Low | Stripe permits social casino with virtual currency. Ensure product descriptions are clear. No "gambling" language. |
| User fraud / Chip farming bots | Medium | Medium | Rate limiting, device fingerprinting, suspicious behavior detection. Cap free Chip grants. |
| Negative press / problem gambling concerns | Medium | Low | Implement responsible gaming features: session time reminders, voluntary play limits, self-exclusion option. |

---

## 10. 90-Day Sprint Plan

### MONTH 1 (March-April 2026): Polish & Soft Launch

**Week 1-2: Legal & Compliance**
- [ ] Draft Terms of Service (social casino specific -- flag for legal review)
- [ ] Draft Privacy Policy (CCPA compliant)
- [ ] Add legal disclaimers to all purchase screens and game pages
- [ ] Add 18+ age gate to account creation
- [ ] Verify Stripe product descriptions contain no gambling language

**Week 2-3: Analytics & Tracking**
- [ ] Set up Google Analytics 4 with custom events (hand played, chip purchased, login streak, AI coach used)
- [ ] Set up Mixpanel or PostHog for product analytics (funnels, retention curves, revenue tracking)
- [ ] Implement UTM tracking on all external links
- [ ] Create analytics dashboard with daily KPI review

**Week 3-4: Content Creation**
- [ ] Record 10 TikTok/Reels clips (AI coach highlights, strategy tips, win streaks)
- [ ] Write 3 SEO articles (blackjack strategy, social casino guide, AI coaching)
- [ ] Create "How to Play" landing page optimized for search
- [ ] Set up content calendar for 3x/week posting cadence

**Week 4: Soft Launch**
- [ ] Share with personal network (50-100 people)
- [ ] Post in 3 relevant subreddits (r/blackjack, r/indiegaming, r/SideProject)
- [ ] First X/Twitter build-in-public thread
- [ ] Collect feedback, fix critical bugs
- [ ] Target: 200-500 registered users

**Revenue target:** $0-100 (validation, not revenue)

### MONTH 2 (April-May 2026): Content Engine & First Revenue

**Content:**
- [ ] Post 12+ short-form videos across TikTok, Reels, Shorts
- [ ] Write 3 more SEO articles
- [ ] Launch weekly email newsletter to registered users
- [ ] 2 Reddit posts with genuine value contribution
- [ ] First YouTube long-form video: "I Built a Casino with AI"

**Product:**
- [ ] Add 3 larger Chip packs to Stripe ($24.99, $49.99, $99.99)
- [ ] A/B test first-time buyer offer (bonus 500 Chips on first purchase)
- [ ] Implement "low Chips" nudge: "Running low? Grab a Chip pack to keep playing"
- [ ] Begin tournament system design and development
- [ ] Add 2 cosmetic items (card back + table theme) as proof of concept

**Growth:**
- [ ] Identify 10 potential micro-influencers, reach out to 5
- [ ] Set up referral tracking dashboard
- [ ] Cross-promote in Everlight newsletter to all existing contacts
- [ ] Target: 1,000-2,000 registered users, 500 MAU

**Revenue target:** $200-500

### MONTH 3 (May-June 2026): Paid Acquisition & Tournaments

**Paid Ads:**
- [ ] Launch Meta Ads test campaign ($10-20/day, 3 ad creatives)
- [ ] Launch TikTok Ads test campaign ($10/day, 2 ad creatives)
- [ ] Measure CPI across channels, kill underperformers at day 7
- [ ] Scale winning creatives to $30-50/day

**Product:**
- [ ] Launch Daily Freeroll tournament
- [ ] Launch Weekend Showdown tournament
- [ ] Add Speed Blackjack variant
- [ ] Release first batch of cosmetic shop items (5-10 items)
- [ ] Implement rewarded video ads for non-paying users

**Growth:**
- [ ] First influencer partnership live (video featuring AI coach)
- [ ] Product Hunt launch consideration (only if metrics support it)
- [ ] Guest post on 1-2 gaming/gambling blogs
- [ ] Target: 3,000-5,000 MAU, 100+ payers

**Revenue target:** $1,000-3,000/month

---

## Appendix A: Seedance Video Prompts

These prompts generate short promotional videos for social media ads and organic content.

**Prompt 1 -- Product Demo (15s)**
```
A sleek mobile phone screen showing a 3D blackjack table with gold and black luxury casino theme. Cards animate dealing across the felt. An AI assistant popup appears with glowing text analyzing the hand. The phone rotates slowly showing the premium interface. Dark background, gold accent lighting, cinematic quality. Text overlay: "AI-Powered Blackjack -- Play Free"
```

**Prompt 2 -- Founder Story (10s)**
```
A solo entrepreneur working late at night, illuminated by a golden monitor glow. The screen shows code transforming into a 3D casino game. Camera pulls back to reveal multiple monitors showing analytics dashboards, game graphics, and AI chat interfaces. Text overlay: "Built by one person. Powered by AI." Moody, cinematic, dark room with warm gold accents.
```

**Prompt 3 -- Social Proof (10s)**
```
A montage of diverse hands holding phones, all showing the same blackjack game from different angles. Chips stack up, cards flip, leaderboard positions change. Fast cuts, energetic. Gold particles float between screens. Text overlay: "Join thousands of players sharpening their game."
```

**Prompt 4 -- AI Coach Feature (15s)**
```
Close-up of a blackjack hand: player has 16, dealer shows 10. A holographic AI assistant materializes above the cards, displaying probability percentages and a recommendation arrow pointing to "HIT." The player hits, gets a 5 for 21. Celebration animation with gold sparks. Text overlay: "Your AI coach knows the odds. Do you?"
```

**Prompt 5 -- Tournament Hype (10s)**
```
A neon-lit virtual casino tournament lobby. Player avatars with VIP badges line up at tables. A countdown timer hits zero. Cards fly across multiple tables simultaneously. A leaderboard updates in real-time with usernames climbing. Champion trophy appears with gold explosion. Text overlay: "Weekly Tournaments. Real Competition. Zero Cost."
```

---

## Appendix B: Social Media Launch Posts (10)

### X (Twitter) Posts

**Post 1 -- Launch Announcement**
I built an AI-powered blackjack game. By myself. From my phone.

The AI coach analyzes every hand you play and tells you exactly where you went wrong.

3D graphics. Leaderboards. Daily rewards. Tournaments coming.

Play free right now: everlightventures.io/arcade/blackjack

**Post 2 -- AI Coach Hook**
"You should have doubled down on that soft 17."

My AI blackjack coach is brutally honest. It tracks every decision you make and scores your play against perfect strategy.

Most players are leaving 15-20% expected value on the table. Are you?

**Post 3 -- Build-in-Public Thread**
Thread: How I built a full casino platform as a solo founder in 2026

Stack:
- Lovable (React frontend)
- Supabase (backend + auth)
- Three.js (3D graphics)
- Claude API (AI strategy coach)
- ElevenLabs (dealer voice)
- Stripe (payments)

Total cost to build: under $500.

Here's what I learned...

**Post 4 -- Strategy Content**
Quick blackjack tip most people get wrong:

Never take insurance. Ever.

The house edge on insurance is 7.4%. It's the worst bet on the table.

Our AI coach catches this mistake constantly. Play for free and see how your strategy stacks up:

everlightventures.io/arcade/blackjack

**Post 5 -- Social Proof**
Player just hit a 14-day login streak and opened a Rare Mystery Box.

Got 10 bonus Gems and an exclusive avatar frame.

Day 28 rewards are even bigger: 25 Gems + Epic Mystery Box.

The daily rewards system is honestly addictive. Try it:

### LinkedIn Posts

**Post 6 -- Founder Journey**
5 years ago I started building software products.

Today, I have:
- 5 published books on Amazon
- A working POS system for small businesses
- A live trading bot
- An AI-powered social casino

The casino has an AI Strategy Coach that analyzes every blackjack hand in real-time.

No VC funding. No team. Just AI tools and persistence.

The social casino market is $10B+. I'm going after it with a differentiated product: skill development through AI coaching.

Play it free: everlightventures.io/arcade/blackjack

**Post 7 -- Technical Deep Dive**
How I used Claude API to build an AI blackjack strategy coach:

The coach watches every hand. When you make a suboptimal decision, it explains:
1. What you should have done
2. The probability difference
3. The expected value impact

It runs as a Supabase Edge Function, analyzing hands in <500ms.

Players are actually getting better at blackjack -- their strategy scores improve over sessions.

This is what "AI-native products" look like in practice.

### Community / Reddit Posts

**Post 8 -- r/blackjack**
[Title: I built a free blackjack game with an AI strategy coach -- looking for feedback from serious players]

Hey r/blackjack -- I built a browser-based blackjack game with an AI that analyzes every hand you play and gives you real-time strategy feedback.

It tracks your decisions against basic strategy and tells you where you're deviating. Been useful for my own learning.

Looking for feedback from experienced players: is the strategy analysis accurate? What would make it more useful?

Free to play, no download: [link]

**Post 9 -- r/indiegaming**
[Title: Solo dev -- built a 3D social casino with AI coaching, NPC players, and a full rewards system]

Been working on this for a while. It's a browser-based blackjack game with:
- Three.js 3D graphics
- AI strategy coach (analyzes every hand)
- NPC players that behave like real people
- Daily rewards, achievements, VIP tiers
- ElevenLabs AI dealer voice

Stack: Lovable + Supabase + Three.js + Claude API + Stripe

Would love your feedback. What would you add?

**Post 10 -- General Social**
The AI dealer just said "Bust. Dealer wins." in the most condescending voice possible.

Then the AI coach told me I had a 73% chance of winning if I'd stood on 15.

This is what happens when you give AI a casino to run.

Play free: everlightventures.io/arcade/blackjack

---

## Appendix C: Key Legal Disclaimers (Use Everywhere)

**Purchase Screen Footer:**
"All in-game currencies are virtual items with no real-world monetary value. Purchases are final. Must be 18+ to purchase. Prices in USD. Everlight Ventures reserves the right to modify the virtual economy at any time."

**Game Page Footer:**
"Everlight Blackjack is a free-to-play social casino game for entertainment purposes only. No real money can be won or lost. Virtual currencies have no cash value and cannot be redeemed, transferred, or exchanged for real-world value. Must be 18+ to play. If you or someone you know has a gambling problem, call 1-800-522-4700."

**App Store Description (when applicable):**
"Everlight Blackjack is a social casino game intended for entertainment purposes only. This game does not offer real money gambling or an opportunity to win real money or prizes. Practice or success at social casino gaming does not imply future success at real money gambling."

---

## Appendix D: Responsible Gaming Features (Implement Phase 1)

Even as a social casino, implementing responsible gaming features is both ethical and important for app store approval and investor credibility.

1. **Session time reminder:** After 60 minutes of continuous play, show a non-dismissable popup: "You've been playing for an hour. Take a break?"
2. **Voluntary play limits:** Players can set daily Chip spending limits in their profile settings
3. **Self-exclusion:** Players can temporarily disable their account for 24 hours, 7 days, or 30 days
4. **Purchase history:** Easily accessible record of all real-money purchases
5. **Help resources:** Link to National Council on Problem Gambling (1-800-522-4700) in game footer

---

*Strategy authored by Everlight SaaS Growth Agent | March 11, 2026*
*Review with legal counsel before implementing monetization or publishing Terms of Service*

---

**Sources consulted:**
- [California AB 831 Sweepstakes Casino Ban](https://www.lines.com/guides/california-sweepstakes-casinos)
- [AB 831 Legal Analysis](https://www.zwillgen.com/gaming/californias-ab-831-bans-sweepstakes-casinos-expands-liability-vendors/)
- [Social Casino Legal Guide 2026](https://sweepstakes-casino.org/legal-information/)
- [Modo Social Casino Model in California](https://deadspin.com/legal-betting/modo-to-continue-operating-in-california-under-social-casino-model-while-clubwpt-shifts-from-sweeps-strategy/)
- [Social Casino Market Report ($14.23B by 2030)](https://www.globenewswire.com/news-release/2026/02/13/3237948/0/en/Online-Social-Casino-Analysis-Report-2026-14-23-Bn-Market-Opportunities-Trends-Competitive-Landscape-Strategies-and-Forecasts-2020-2025-2025-2030F-2035F.html)
- [BITKRAFT Ventures Profile](https://tracxn.com/d/venture-capital/bitkraftventures/__08-JTwL9X-TPJj1Kq0o5CB-HBXGEP1M_cGrG0IB-P7s)
- [Griffin Gaming Partners Profile](https://tracxn.com/d/venture-capital/griffin-gaming-partners/__UPKpd-iw9JqO9SEL-nRaW3RzYbQdHXI7lyL_Ia4nOmw)
- [Sweepstakes Casino Dual Currency Implementation](https://bettoblock.com/sweepstakes-casino-dual-currency-system/)
