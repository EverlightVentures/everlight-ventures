# Everlight Ventures Financial Plan 2026
**Prepared:** 2026-03-14
**Author:** Everlight Trading Risk Agent (advisory only)
**Scope:** XLM bot revenue integration with Everlight Ventures business engine

---

*DISCLAIMER: This document is a planning framework based on observed bot behavior and business architecture. It does not constitute financial advice. Cryptocurrency derivatives trading involves substantial risk of loss, including loss of the entire principal. Past performance does not guarantee future results. Revenue projections are estimates based on current conditions and are not guarantees. Always consult a licensed financial advisor before making investment decisions.*

---

## Executive Summary

Everlight Ventures is building toward $10,000/month in revenue across six business streams. The XLM perpetual bot is the most active revenue experiment today. The plan below structures three phases across 12 months, with the bot serving as proof-of-concept for the trading SaaS product and a contributor to operating cash flow.

The bot is currently live on Oracle Cloud trading XLP-20DEC30-CDE at 4x leverage with roughly $430 equity. It has a 44% win rate and 0.62 profit factor across 110 trades. Before scaling, one structural fix is required: enforcing the max-hold rule to prevent a repeat of the Feb 25 $64.90 overnight loss that erased two weeks of gains.

---

## Phase 1: Bot Proves Itself (Month 1-3)
**Balance target:** $310 (current) to $600
**Daily goal:** $10-25/day on good days, flat-to-small-loss on bad days
**Monthly goal:** $200-$400 net from bot trading

### What needs to happen first

Before putting more money in or declaring the bot profitable, three things must be true:

1. **Max-hold enforcement confirmed.** The Feb 25 trade held 15 hours and lost $64.90. That one trade wiped out two prior weeks of gains. The `max_hold_hours: 1.5` setting is now in config but must be verified as not bypassable by AI executive mode. This is non-negotiable before scaling.

2. **Daily profit gate built.** Currently the bot trades all day with no concept of "I made enough today, now protect it." A `daily_profit_gate.py` module needs to be added that halts new entries once a daily floor ($10-25) is reached in poor sentiment conditions (F&G < 30).

3. **Oracle Cloud health confirmed.** The dashboard snapshot is 14 days stale as of this writing. SSH in and confirm the bot is actually running.

### Bot revenue projections (Phase 1)

At $430 current equity with 1-2 contracts:
- Best realistic day: $15-30 (trend day, 5-8 good setups)
- Average day: $3-8 (compression, fewer setups)
- Bad day: -$5 to -$15 (choppy, multiple small losses)
- Catastrophic day: -$30+ (only if max-hold is not enforced)

Monthly at $5/day average: ~$150/month
Monthly at $10/day average: ~$300/month
Monthly at -$5/day average (poor conditions): ~-$150/month

**Phase 1 milestone:** Achieve 60 consecutive days with profit factor above 1.0 and no single loss exceeding $15. This proves the bot is controlled before scaling.

### Other revenue streams (Phase 1)

- Onyx POS: 0-2 paying clients at $49/mo = $0-$98/mo
- HIM Loadout affiliate: $0-$100/mo
- Publishing (KDP): $0-$50/mo
- Total non-bot: $0-$250/mo

**Phase 1 total monthly range:** $0-$550

---

## Phase 2: Scale + Operations (Month 3-6)
**Balance target:** $600 to $1,500 (bot plus $500-700 infusion if bot has proven itself)
**Daily goal:** $25/day floor, $50/day target
**Monthly goal:** $500-$1,000 from bot; $500-$1,000 from other streams

### Bot scaling conditions

The bot gets additional capital only if Phase 1 milestones are met:

- At $600 equity: unlock 2-3 contracts intraday, 1-2 overnight. Daily target moves to $25.
- At $1,000 equity: unlock 3-4 contracts. Daily target moves to $50. House Money protocol triggers at $1,200 (2x the $600 starting point).
- At $1,500 equity: begin SaaS investor dashboard work. Bot performance data becomes the product.

### Bot revenue at $1,000 equity

At $1,000 with 3 contracts at 4x leverage:
- Average win per trade: $5-12
- Best day (5 wins): $25-60
- Average day (2-3 wins, 1-2 losses): $10-25
- Bad day: -$10 to -$25 (protected by daily loss cap)

Monthly at $20/day average: ~$600/month
Monthly at $30/day average: ~$900/month

**Phase 2 milestone for bot:** 30 consecutive days with positive P&L, profit factor above 1.2, and at least 14 days hitting the $25 daily target.

### Other streams (Phase 2)

- Onyx POS: 3-8 clients at $49/mo = $147-$392/mo
- Hive Mind SaaS: first tier customers at $29-$49/mo = $100-$300/mo
- Broker OS: first deal at 15-30% finder fee; one deal = $500-$2,000 one-time
- Publishing: $50-$150/mo
- HIM Loadout: $100-$300/mo
- Total non-bot: $500-$1,100/mo

**Phase 2 total monthly range:** $1,000-$2,000

---

## Phase 3: $10k/mo Business Engine (Month 6-12)
**Balance target:** $1,500 to $3,000 (bot); business to $10k/mo total
**Daily goal:** $50/day floor, $100/day target on strong trend days
**Monthly goal:** $1,500-$3,000 from bot; $7,000-$8,000 from SaaS and services

### Bot at $2,000 equity

At $2,000 with 4-6 contracts at 4x leverage:
- Average win per trade: $10-20
- $100 day requires: 5-10 wins, 0-2 losses (achievable on strong trend days only)
- $100 days per month realistically: 4-8 days
- $25-50 days: 10-14 days
- Flat or loss days: 8-12 days

Monthly realistic range at $2,000 equity:
- Conservative (50% win rate, PF 1.2): $600-$900/mo
- Moderate (55% win rate, PF 1.5): $1,200-$1,800/mo
- Strong trend month: $2,500-$3,000/mo

**The $100/day every day target is not realistic.** The goal should be 14 days at or above $100 and 14 days at $25-100, netting $1,500-$2,000/month from the bot in a good month.

### Other streams (Phase 3)

- Onyx POS: 15-25 clients at $49/mo = $735-$1,225/mo
- Hive Mind SaaS: 20-50 clients at $29-$149/mo = $580-$7,450/mo (wide range by tier mix)
- Broker OS: 1-3 deals/mo at $500-$5,000 each = $500-$15,000/mo (highly variable)
- Publishing: $150-$500/mo
- Alley Kingz: $0-$500/mo (mobile game, early stage)
- HIM Loadout plus Logistics: $300-$700/mo combined

Phase 3 non-bot floor: $2,265/mo (conservative)
Phase 3 non-bot target: $8,000-$10,000/mo (Hive Mind plus Broker OS at scale)

**Phase 3 total:** $3,000-$12,000/mo depending on which SaaS products gain traction

---

## Key Risk Factors

**Bot risks:**
- XLM contract expiry: XLP-20DEC30-CDE expires Dec 30, 2026. Roll to next contract at least 7 days early.
- Coinbase CDE policy changes could affect margin rules or product availability.
- Single catastrophic trade (like Feb 25) can wipe weeks of gains. Max-hold enforcement is the critical control.
- Bot going offline on Oracle Cloud undetected. Watchdog must be bulletproof.

**Business risks:**
- Hive Mind SaaS depends on acquiring users. No paying users yet means Phase 3 projections are aspirational.
- Broker OS deals are lumpy -- one good month could be followed by two dry months.
- Publishing royalties are small per unit and grow slowly.
- All crypto-adjacent revenue (bot SaaS, Alley Kingz NFT) is subject to regulatory uncertainty.

**What derails the plan:**
- Not fixing max-hold enforcement before scaling capital.
- Scaling too fast before profit factor is above 1.0.
- Neglecting SaaS pipeline while focused on bot tuning.

---

## Milestones Summary

| Milestone | Target Date | Signal |
|---|---|---|
| Oracle Cloud confirmed running | Week 1 | SSH check, fresh snapshot |
| max_hold_hours verified enforced | Week 1-2 | No holds over 2 hours in logs |
| daily_profit_gate.py built and live | Week 2-4 | $25 floor protected on green days |
| 60-day positive PF run | Month 2-3 | PF above 1.0 in rolling_expectancy |
| $600 equity reached | Month 2-3 | Scale to 3 contracts |
| First Onyx POS paying client | Month 1-2 | $49 MRR |
| First Hive Mind SaaS client | Month 3-4 | $29-149 MRR |
| First Broker OS deal closed | Month 4-6 | One-time $500+ |
| $1,000 equity on bot | Month 4-5 | Scale to 4 contracts |
| $2,000 equity on bot | Month 8-10 | $100/day target unlocked |
| $5,000/mo total revenue | Month 9-10 | SaaS plus bot combination |
| $10,000/mo total revenue | Month 12 | Full engine firing |

---

## One-Page Summary

**Right now:** The bot is functional but not yet proven. One bad trade can erase two weeks of wins. Fix max-hold enforcement and add the daily profit gate before anything else.

**Month 1-3:** Prove the bot can make $150-$300/month consistently without catastrophic drawdowns. Start acquiring Onyx POS and Hive Mind clients in parallel.

**Month 3-6:** If the bot is proven, add $500-$700 capital. Scale to 3 contracts. Expect $600-$900/mo from bot. Build other streams to $1,000/mo combined.

**Month 6-12:** Bot at $2,000 equity contributing $1,500-$2,500/mo on good months. SaaS products pulling $5,000-$8,000/mo if Hive Mind gains traction. $10k/mo is achievable but requires the SaaS engine, not just the bot.

**The bot alone will not get to $10k/mo.** It is a proof-of-concept and a cash-flow contributor. The SaaS products (Hive Mind, Onyx POS, Broker OS) are the engine for the $10k target.

---

*DISCLAIMER: This document is for planning purposes only. It does not constitute financial advice. Cryptocurrency derivatives trading involves substantial risk of loss. Revenue projections are estimates, not guarantees. Past performance does not predict future results.*
