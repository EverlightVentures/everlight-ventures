# Open Deal -- Scale-First Volume Plan + Daily Limit Discipline

**Owner:** Rich Gee
**Status:** Scale-first. Multi-state from day 1. 30-day target = wholesale-king pace.
**Date:** 2026-05-15 (rewritten from honest-but-throttled v1 same day after Rich called the goalpost-move)

---

## The two questions, separated

| Question | Answer |
|---|---|
| **CAPACITY** -- can the platform handle 5,000 buyers across 8 states? | **YES, from day 1.** Cloudflare Pages, Supabase, Stripe Identity, OFAC API, branded_mailer-via-Resend-Pro all scale horizontally with zero refactor. |
| **ACQUISITION SPEED** -- how fast can we fill that capacity? | **30 days realistic, 90 days conservative, to 500+ Browsers across 8 states.** |

The previous v1 of this file confused those. Capacity is engineered for the ceiling. Acquisition is the slope. Building for 200 was the cage; building for 5,000 is the plan.

---

## Today's state of the buyer DB (truth audit unchanged)

- 84 buyer records (74 contacted, 0 responded, 0 closed) -- the legacy pipeline list
- 9 TN buyers including Mid-South Homebuyers (Chris's company)
- Distributed: GA 24, TX 20, OH 12, TN 9, FL 6, NC 5, MO 5, AZ 3
- **All 8 of those states have a designated Everlight state agent already** (Marvin TN, Atlas GA, Daria TX, Cleo OH, Jasper FL, Phin AZ, Stella MO, plus NC inherits from Marvin until we name an agent)
- All 8 have state_gates.json entries
- All 8 are about to have state-buddy legal audits per the legal team dispatched 2026-05-15

That's not 9 TN buyers -- that's an 8-state launch on day 1.

---

## 30-day target (multi-state launch)

| Metric | Day 1 | Day 30 | Day 60 | Day 90 |
|---|---|---|---|---|
| States active (Browser tier) | 8 (TN, GA, TX, OH, FL, NC, MO, AZ) | 8 + 2 added | 12 | 15 |
| States with Verified+IC unlocked | 1 (TN) | 4 (TN, GA, TX, FL) | 8 | 12 |
| Browsers | 0 | 300-500 | 800-1,200 | 1,500-2,500 |
| Buyer-Funds-Verified | 0 | 30-60 | 100-200 | 300-500 |
| Inner Circle (paid $49/mo) | 1 (Chris comped) | 8-15 paying | 30-50 | 80-150 |
| Drops live per week | 2-3 | 8-12 | 20-30 | 40-60 |
| Closed deals per month | 0 | 3-5 | 8-15 | 20-30 |
| Net revenue / mo (run rate) | $0 | **$20-30k** | **$60-90k** | **$150-220k** |

The $17,500/mo number that I framed as a "200-buyer goal" is hit in the first **30 days** at this pace, not 12 months. Wrong cage off.

---

## What changes to lift the cage

### 1. Resend free tier -> Resend Pro on day 1 ($20/mo, 50,000/mo cap)

- Existing daily cap: 100/day (3,000/mo free)
- Pro daily cap: ~1,650/day (50,000/mo)
- **16x outreach capacity for $20/mo.** Triggers the moment the build ships.
- 25% VIP reserve doctrine preserved: 412 VIP slots/day, 1,238 outreach slots/day.

### 2. Stripe Identity for automated KYC ($1.50/check)

- Replaces Marquise+Justine manual review on Buyer-Funds-Verified ($99 tier)
- Verifies government ID + selfie + sanctions screening in one call
- Auto-approves clean checks; flags edge cases to Marquise
- **Removes the 3-5/day manual bottleneck.** Could process 100+ KYC checks/day on day 1.

### 3. Auto-OFAC SDN screening via Treasury API (free)

- Required per Theo Briggs federal audit 2026-05-15. Strict liability, criminal exposure.
- Treasury OFAC SDN list is published, downloadable, queryable -- no fee.
- Stripe Identity returns sanctions hit/no-hit; we double-check against the live SDN download nightly.
- **Logged with timestamp on every Verified + Inner Circle applicant.**

### 4. Multi-state Browser tier from day 1

- 8 states open at Browser tier immediately (TN, GA, TX, OH, FL, NC, MO, AZ).
- Geofence is opt-IN by state as compliance audits clear, not opt-OUT-to-TN-only.
- TN clears first (already audited). GA, TX, FL, AZ next (state buddies already audited per round-3 work).
- OH, MO, NC follow within 14 days.
- **CA blocked at every tier** pending Cal. Civ. Code 1671(b) liquidated-damages analysis (per Theo Briggs audit).
- EU/UK/EEA blocked at Cloudflare Worker edge, return HTTP 451 (per Priya Bhattacharya audit).

### 5. Acquisition channels turned on simultaneously

- **InvestorLift listings**: every drop posted there too. Single listing = thousands of cash-buyer eyeballs. Free tier first.
- **Connected Investors + PropStream cash-buyer scrape**: harvest recent-cash-transaction buyers in 8 states. Cold outreach within Resend Pro budget.
- **REIA monthly meetings**: 8 markets, 8 state agents attending or sending packets. ~50-80 signups/month combined.
- **Affiliate program**: Inner Circle members get a referral code. $50 credit per Verified buyer they bring. Compounds Chris's network.
- **IG / Twitter content factory**: existing factory writes drop teasers, no email cost.
- **Slack #broker-pipeline + #ft-markets**: every drop cross-posts via branded_slack.
- **Paid FB/IG ads** ($100-500/mo opt-in by Rich): target "cash buyer real estate" in 8 cities. Disabled by default until Rich greenlights.

### 6. Affiliate / referral rails

- Inner Circle members (and Chris specifically) get a unique referral URL.
- New buyer signs up via URL -> referrer gets $50 credit applicable to future Lock Fees or one month's IC sub waiver.
- Tracked in Supabase, paid out monthly by Stripe credit memo.
- Caps: max $500/mo credit per referrer per month (Stripe-side fraud guard).

---

## Daily limit budget with Resend Pro

| Bucket | Daily Cap (Pro) | Monthly Cap | Use |
|---|---|---|---|
| **VIP reply** | 412/day reserved | ~12,375/mo | Hammer + Cupid 1-1 buyer replies |
| **Nurture** | 412/day | ~12,375/mo | Browser drip, Verified onboarding, IC monthly digest |
| **Outreach (bulk)** | 500/day | ~15,000/mo | Cold cash-buyer harvests, REIA invites |
| **System** | 326/day | ~10,250/mo | Stripe receipts, KYC status, transactional |
| **Total** | 1,650/day | 50,000/mo | Hard cap, Pro tier |

**Doctrine unchanged**: 25% VIP reserve, branded_mailer chokepoint, DNC eradication, no rogue Resend API calls. Just bigger numbers.

---

## Cost ledger (multi-state launch, recurring)

| Item | One-time | Monthly | When triggered |
|---|---|---|---|
| Domain | $0 (own) | $0 | already |
| Cloudflare Pages + Workers | $0 | $0 (free tier holds to ~10M req/mo) | day 1 |
| Supabase | $0 | $25 Pro (recommend day 1 -- 8-state row volume) | day 1 |
| Stripe | $0 | 2.9% + $0.30 per txn only | day 1 |
| Stripe Identity | $0 | $1.50/check (~$150/mo at 100 KYC/mo) | day 1 |
| Resend Pro | $0 | $20 | day 1 |
| PostHog | $0 | $0 | free tier to 1M events |
| Slack | $0 | $0 | free tier |
| InvestorLift | $0 | $0 free tier first | day 1 |
| Connected Investors | $0 | $0 free first; $39/mo if upgraded | day 30 conditional |
| PropStream | $0 | $99/mo trial-only first; cancel | day 1-7 trial only |
| FB/IG ads (optional) | $0 | $100-500/mo (Rich-greenlit) | day 30+ |
| **Fixed monthly cost at launch** | **$0** | **~$45 ($20 Resend + $25 Supabase) + variable KYC** | day 1 |
| **Fixed monthly cost at scale (day 90)** | **$0** | **~$200/mo + variable** | day 90 |

Variable costs (Stripe % + KYC) only scale with revenue. The structural cost to launch a 5,000-buyer national platform is under $50/month.

---

## Post-Day-10 phases (the "phases 10+" Rich mentioned)

The build sprint (Days 1-10) ships the v1. After that, sequential phases compound:

### Phase 11: TN -> GA + TX + FL state activation (Day 11-21)
- State-buddy disclosure appendices ship for GA (Ellie Vaughn), TX (Mags Diaz), FL (Mona Castile), AZ (Lupe Salazar)
- Geofence on `/verify` and `/inner-circle` opens to those states
- State agents (Atlas, Daria, Jasper, Phin) start warm activation of their state buyer lists
- First InvestorLift listing in each state

### Phase 12: KYC automation hardening (Day 14-25)
- Stripe Identity webhook automation
- Daily OFAC SDN-list refresh cron on Oracle
- Auto-OFAC double-check (Stripe + Treasury) reconciled to a Supabase ledger
- Manual review queue ONLY for edge cases (PEP, sanctions hits, doc quality issues)

### Phase 13: Referral / affiliate program ship (Day 18-25)
- Unique referral URLs per Inner Circle member
- Stripe Connect or credit-memo wiring
- Chris pilot first; expand to 10 ICs by Day 30

### Phase 14: OH + MO + NC + AZ activation (Day 22-35)
- Remaining state agents + state-buddy audits
- 8 states fully active at Verified + Inner Circle tier
- First multi-state monthly revenue report

### Phase 15: Paid acquisition layer (Day 30-45, Rich-greenlit only)
- FB/IG ad creative writing by content factory
- $100/state/mo initial test ($800/mo total)
- A/B test landing pages on `/drops`
- Re-evaluate at Day 60 based on CAC vs LTV math

### Phase 16: National expansion plan (Day 45-90)
- Add states 9-15: AL, MS, AR, KY, MI, IN, SC
- Per-state legal audit via state buddies + cross-check
- Geographic sequence per CarMax-of-wholesaling thesis: deep South first, then Mid-Atlantic, then West

### Phase 17: Institutional capital layer (Day 90+)
- First institutional buyer (REIT, hedge fund REI desk) onboarded as a special Inner Circle++ tier
- Higher Lock Fees ($500-1,000), priority drop access, bulk-deal pricing
- Justine + Theo Briggs run the institutional KYC and AML compliance

### Phase 18: Wholesale King v1 (Day 90-120)
- Definition: 1,500+ active Browsers, 300+ Verified, 80+ Inner Circle paying members
- Monthly run rate: $150-220k net
- Multi-state deal flow filtering 30+ closes/month
- This is when Rich becomes the wholesale king of his target markets.

---

## Stop-loss triggers (unchanged from v1)

Same triggers, scaled to the new pace:

- **Day 14**: fewer than 50 Browsers signed up after launch -> the offer isn't landing in any state, rework
- **Day 21**: zero Verified upgrades from 100+ Browsers -> $99 pricing is wrong
- **Day 30**: zero closed deals from any platform lock -> the buyer-to-deal handoff is broken
- **Day 45**: walk rate over 50% -> 24h too short or tier pricing wrong

---

## What this means for the build sprint

Day 1-10 build sprint expands by ~2 days to absorb the scale-first additions:

- Stripe Identity integration (Day 4 work, added to existing flow)
- Treasury OFAC SDN-list nightly cron (Day 5 work, simple curl + diff)
- Multi-state geofence routing logic (Day 6 work, lookup table per state)
- EU/UK/EEA 451 block at CF Worker edge (Day 7 work, ~10 LOC)
- Affiliate URL routing + credit ledger (Day 8 work, ~40 LOC)
- CAN-SPAM footer in branded_mailer drop template (Day 9 work, copy + template)
- Privacy policy public render at /legal/privacy (Day 9 work)
- CA + EU/UK geofence on all paid tiers (Day 10 work, config-only)

**New sprint length: 10-12 days.** Still well under 14.

Cost still essentially zero to launch (~$45 fixed/mo, then variable).
