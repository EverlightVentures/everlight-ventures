# Pricing Strategy -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

---

## Strategic Positioning

Hive Mind is positioned as an AI Chief of Staff, not an automation tool. This framing supports premium pricing. The relevant competitive frame is: "What would a fractional COO or virtual assistant cost?" (Answer: $1,500-$4,000/mo). Against that benchmark, $49-$399/mo is deeply compelling.

The pricing strategy is value-anchored, not cost-plus. The goal is not to recover LLM costs + margin. The goal is to capture a small fraction of the value created (hours of work automated, revenue generated from AI-drafted outreach, etc.).

---

## Recommended Pricing Tiers

---

### Tier 1 -- Spark: $49/month

Designed for: The solopreneur who wants to test value before committing fully. Limited enough to create upgrade pressure, generous enough to see real results.

Included:
- 1 user seat
- 100 hive sessions per month (resets on billing date)
- 3 connected integrations (e.g., OpenAI key + Slack + one more)
- Access to all 12 session templates
- Slack audit logging (1 channel)
- Session history (30-day retention)
- Email digest (weekly)
- Standard support (48-hour response target)
- 7-day free trial, no credit card required

Not included:
- Webhook trigger endpoints
- Scheduled recurring sessions (manual run only)
- Mindmaps
- Multi-user workspaces
- Priority support

Upgrade trigger: Running out of 100 sessions/month (achievable after about 3-4 sessions per day). At that point, Hive at $129/mo is a clear upgrade.

Annual price: $470/year ($39.17/mo effective -- saves $118 vs monthly).

Positioning note: Do not call this a "starter" tier -- the connotation is "not serious." "Spark" implies beginning the ignition. Use language like "Get started with the hive" not "Entry level."

COGS per customer (monthly):
- LLM tokens: ~$1.50 (100 sessions x avg 1,000 tokens x $0.003 blended)
- Infrastructure: ~$0.80
- Gross margin: ~95%

---

### Tier 2 -- Hive: $129/month

Designed for: The primary conversion target. This is the plan that 60-70% of paying customers should be on. Priced to feel reasonable relative to the value delivered, high enough to be worth serving.

Included:
- 5 user seats
- Unlimited sessions
- 20 connected integrations
- All session templates + the ability to create custom templates
- Slack audit logging (up to 3 channels)
- Webhook trigger endpoints (up to 10)
- Scheduled recurring sessions
- Interactive mindmap viewer (Phase 2)
- Session history (unlimited retention)
- Email and Slack notifications
- Priority support (12-hour response target)
- Cost estimation before every session
- Monthly usage reports
- 7-day free trial, no credit card required

Not included:
- White-label
- Custom domain
- Unlimited users
- Dedicated support rep
- SLA guarantee

Annual price: $1,238/year ($103.17/mo effective -- saves $310 vs monthly).

Annual upsell moment: After 60 days, show a modal: "You have run 47 sessions. Switch to annual and save $310 -- that is 2.4 months free."

COGS per customer (monthly):
- LLM tokens: ~$1.20 (avg 80 sessions x 3,000 tokens x $0.005 blended)
- Infrastructure: ~$0.80
- Gross margin: ~98%

---

### Tier 3 -- Enterprise: $399/month

Designed for: Agencies (2-15 person teams), established small businesses spending $2,000+/mo on tools, or anyone who needs white-label capability.

Included:
- Unlimited user seats
- Unlimited sessions
- Unlimited integrations
- Everything in Hive
- White-label (custom domain, logo, colors)
- Dedicated Slack support channel with direct founder access
- SLA: 99.5% uptime guarantee with service credits
- Custom integrations (up to 2 per year built by Everlight team)
- Onboarding call (60-minute setup session with Everlight)
- Quarterly business review (Phase 2)
- Data export on demand (CSV + JSON)
- Invoicing payment option (net-30, for qualifying accounts)
- SAML SSO (Phase 2 -- Okta/Google Workspace)
- Audit log export
- 7-day free trial, no credit card required

Annual price: $3,830/year ($319.17/mo effective -- saves $958 vs monthly).

Note on Enterprise pricing: $399/mo is the self-serve price. Accounts with over 5 team members or specific compliance needs should be directed to a sales conversation at $600-$1,500/mo depending on scope. This is a Phase 2 motion.

COGS per customer (monthly):
- LLM tokens: ~$40-80 (heavy usage, variable)
- Infrastructure + dedicated resources: ~$15
- Gross margin: ~81%

---

## Annual Discount Strategy

Standard annual discount: 20% off (shown as "2 months free" in marketing).

Annual billing rationale:
- Reduces churn dramatically (annual contracts churn at ~20% the rate of monthly).
- Improves cash flow (12 months of revenue upfront).
- Increases LTV by approximately 2.5x vs monthly when combined with retention benefits.

Annual promotion windows:
- Launch week: Offer 25% off annual for the first 30 customers ("Founding Annual" badge).
- Black Friday / Cyber Monday: 25% off annual for one week.
- Monthly plan holders at 60 days: In-app modal showing the annual savings calculation based on their actual usage.

Annual price table:

| Plan | Monthly | Annual Total | Monthly Equivalent | Savings |
|------|---------|--------------|-------------------|---------|
| Spark | $49 | $470 | $39.17 | $118 |
| Hive | $129 | $1,238 | $103.17 | $310 |
| Enterprise | $399 | $3,830 | $319.17 | $958 |

---

## Free Trial and Freemium Strategy

### Recommended: 7-Day Free Trial, No Credit Card Required

Rationale: Requiring a credit card upfront reduces trial starts by 30-50% (Stripe data, 2024). The addressable market (solopreneurs who will pay $49-$129/mo) is large enough that optimizing trial start rate outweighs the risk of non-converting trials.

Trial terms:
- 7 days of full Hive tier access (unlimited sessions, all features).
- No credit card until trial ends.
- Day 3 email: "You have been running the hive for 3 days. Here is what you built."
- Day 5 email: "Your trial ends in 2 days. Here is how to keep going."
- Day 7: sessions are blocked, history remains accessible.
- After trial: 14-day extension available once per account if the user requests it (show this offer on the expiry screen -- it rescues 10-15% of lapsed trials).

Activation definition: A trial user is "activated" when they have connected at least 1 integration AND run at least 1 session to completion. Target activation rate: 50% of trial starts. Activated users should convert at 40%+.

Why 7 days, not 14: Long trials delay the conversion decision. Most users decide in the first 3-5 days whether the product is valuable. 7 days is enough time to run 10+ sessions and feel the value. 14 days creates procrastination and inflated trial numbers.

### No Freemium Tier (MVP Decision)

Freemium would require serving AI-powered sessions at zero revenue. At our LLM cost structure, a "free" tier with even 5 sessions/month would cost approximately $0.20-$0.50/user/month in API fees. At 1,000 free users (plausible within 3 months of a PH launch), that is $200-$500/month in losses with no guarantee of conversion.

Freemium may be revisited at Phase 3 with either:
a) A severely limited "1 session/month" tier to maintain brand touchpoints, or
b) A community tier that uses only GPT-4o-mini to minimize cost basis.

---

## Usage-Based Overage Pricing

Spark plan tenants who exceed 100 sessions/month can pay for overage sessions rather than being hard-blocked:

Overage rate: $0.75 per session (charged at end of billing period).

Rationale: $0.75 per session at 10-20 minutes of work automated per session is a clear ROI for the buyer. Overage usage also signals strong engagement -- overage tenants are prime upgrade candidates.

Overage alert: At 80 sessions used, show an in-app banner: "You have 20 sessions remaining this month. Sessions beyond 100 cost $0.75 each, or upgrade to Hive for unlimited sessions."

Maximum overage cap: $30/month (40 overage sessions) before a hard block with an upgrade prompt. This prevents bill shock and forces the upgrade conversation.

Hive and Enterprise plans: no session overage (unlimited). Future overage consideration is AI API cost-pass-through if a tenant runs extremely expensive sessions (more than $5 in AI API costs per single session) -- handle case-by-case at launch, not automated.

---

## Add-On Pricing

These are sold as optional upgrades to existing plan holders, not as separate tiers.

| Add-On | Price | Description |
|--------|-------|-------------|
| Extra AI Token Budget | $10/mo | For platform-key users: adds $10 in AI API credit at cost basis |
| Extended Session History | $15/mo | Extends Spark 30-day retention to unlimited |
| Priority Support Upgrade | $29/mo | Hive-tier 12-hour support SLA for Spark users |
| White-Label Add-On | $99/mo | Custom domain + brand colors for Hive users |
| Extra Webhook Endpoints | $9/mo | Adds 10 webhook trigger endpoints for Spark users |
| Mindmap Export (PNG/PDF) | $10/mo | Export session mindmaps as image files |
| Extra Slack Channels | $5/channel/mo | Additional audit log destinations beyond plan limit |
| Dedicated Session Worker | $29/mo | Priority queue for faster session execution |
| Monthly AI Strategy Call | $99/call | 1-hour live session with Everlight founder |

---

## Competitive Analysis Table

| Product | Monthly Price | Sessions | Multi-AI Hive | Slack Audit | Autonomous | Notable Gap |
|---------|--------------|---------|--------------|------------|------------|------------|
| Hive Mind Spark | $49 | 100/mo | Yes (4 models) | Yes | Manual only | -- |
| Hive Mind Hive | $129 | Unlimited | Yes (4 models) | Yes | Yes | -- |
| Hive Mind Enterprise | $399 | Unlimited | Yes (4 models) | Yes | Yes | -- |
| Zapier Teams | $69 | Action-based | Thin AI layer | No | Yes (no reasoning) | No true AI |
| Make.com Core | $10.59 | 10k ops | No | No | Yes (no reasoning) | No AI native |
| Notion AI Team | $20/user | Unlimited | No (1 model) | No | No | Locked to Notion |
| Relevance AI Starter | $19 | 100 runs | Yes | No | Partial | No audit trail |
| ChatGPT Team | $30/user | Unlimited | No (1 model) | No | No | Not autonomous |
| Lindy.ai | $49 | Variable | Partial | No | Yes | No multi-model hive |
| Jasper | $59 | Unlimited | Partial | No | No | Content-only |
| n8n Cloud | $24 | 2.5k runs | No | No | Yes (no reasoning) | No AI reasoning |
| AutoGPT Cloud | $29 | Variable | No | No | Yes | No managed hosting |

Key insight: No competitor combines all four properties that define Hive Mind: multi-AI hive routing, Slack audit logging, autonomous scheduling, and an SMB-accessible price point. The closest threats are Relevance AI (no audit log) and Lindy.ai (single-model). Neither has the "Chief of Staff" positioning or the Slack-native audit trail.

---

## Gross Margin Analysis

### Revenue per Customer (Monthly)

Blended ARPU target at Month 6:
- 40% of customers on Spark ($49): contributes $19.60
- 50% of customers on Hive ($129): contributes $64.50
- 10% of customers on Enterprise ($399): contributes $39.90
- Blended ARPU: ~$124/customer

### LLM Cost per Customer (Monthly)

Hive plan customer: 80 sessions/month at 3,000 average tokens per session.

Token cost by model (February 2026 pricing):
- Claude Sonnet 4.6: ~$0.006/1k tokens blended (input + output)
- GPT-4o: ~$0.005/1k tokens blended
- Gemini 1.5 Pro: ~$0.0025/1k tokens blended
- Perplexity Pro: ~$0.001 per research query

Average session cost (blended across models): ~$0.015 per session
Monthly AI cost for Hive customer: 80 sessions x $0.015 = $1.20/month

### Infrastructure Cost per Customer (at 100 customers)
- Compute (Vercel + Supabase): ~$0.50/customer
- Redis + BullMQ: ~$0.10/customer
- Monitoring, logging, transactional email: ~$0.20/customer
- Total: ~$0.80/customer

### Gross Margin by Plan

Spark plan:
- Revenue: $49.00
- AI cost (100 sessions): $1.50
- Infrastructure: $0.80
- COGS: $2.30
- Gross Margin: 95.3%

Hive plan:
- Revenue: $129.00
- AI cost (80 sessions avg): $1.20
- Infrastructure: $0.80
- COGS: $2.00
- Gross Margin: 98.4%

Enterprise plan:
- Revenue: $399.00
- AI cost (heavy usage): $60.00
- Infrastructure: $15.00
- COGS: $75.00
- Gross Margin: 81.2%

Blended gross margin at Month 6 plan mix: ~95%.

This is exceptional. Software SaaS benchmarks at 70-80% gross margin. The "LLM costs will destroy margins" concern is not realized at typical SMB usage levels and these price points.

Important caveat: If tenants use Everlight-managed platform keys (not their own API keys), the platform bears the LLM cost. At $0.015/session and a $0.10/session markup charged via the add-on, the margin on platform key sessions is still ~85%. Model this carefully before enabling platform keys at scale -- a single heavy-usage tenant could consume significant API credit.

### Break-Even Analysis
- Monthly fixed costs (infrastructure, tooling, Stripe fees): ~$200/month
- Break-even customers: ~2 Hive customers or ~5 Spark customers
- $1,000 MRR: ~8 Hive customers or ~21 Spark customers
- $10,000 MRR: ~78 customers at blended $128 ARPU

Revenue projections (conservative, 5% monthly churn):

| Month | Customers | MRR | ARR |
|-------|-----------|-----|-----|
| 1 | 10 | $790 | $9,480 |
| 2 | 22 | $1,738 | $20,856 |
| 3 | 40 | $3,160 | $37,920 |
| 6 | 100 | $7,900 | $94,800 |
| 12 | 250 | $19,750 | $237,000 |
| 24 | 600 | $47,400 | $568,800 |

---

## GTM -- First 10 Customers Acquisition Strategy

### Target: 10 paying customers within 30 days of public launch

### Channel 1: Direct Outreach (Expected yield: 5-7 customers)

The fastest path to the first 10 customers is personal, direct outreach to people already known to be in the ICP. This is not cold email. It is warm messages to people who know and trust the founder.

Action plan:
1. List every solopreneur, agency owner, and small business operator in your network. Target 50 names minimum.
2. Send a personal message (not a mass email): "I built something I think would help you. Can I show you 15 minutes of it? If you like it, I want your honest feedback and I will give you the first month free."
3. Run a live demo showing a session running end-to-end with the Slack audit log posting in real time. The Slack log is the demo's most compelling moment -- it makes the AI feel real and controllable.
4. Ask: "What would you pay for this if it saved you 5 hours a week?" Then show them the pricing is far below their answer.
5. Offer the Founding Member deal: $39/mo for Hive plan forever (locked in for the first 10 customers who pay and stay).

### Channel 2: Twitter/X and LinkedIn (Expected yield: 2-4 customers)

Post a "Build in Public" thread showing:
- Before: "I was spending 3 hours a week on [specific repeatable task]."
- After: "Now the hive does it in 45 seconds while I sleep. Here is the Slack log."
- Include a screen recording of the session running and the Slack audit log appearing.

This content format is highly shareable in the solopreneur and indie maker communities.

Post schedule for launch week:
- Day 1: Tease with a screenshot. Link to a waitlist landing page.
- Day 3: Full demo video thread showing the complete flow.
- Day 5: "The first 10 people to sign up get Founding Member pricing. Link in bio."
- Day 7: "5 spots left." Update with early social proof.

### Channel 3: Indie Hacker and ProductHunt (Expected yield: 30-60 customers from PH)

Post to Indie Hackers: "I built an AI Chief of Staff SaaS in 8 weeks. Here is what I learned."

ProductHunt launch: Schedule for a Tuesday at 12:01 AM PT. Prepare 5 genuine supporters to leave early comments. Aim for top 5 of the day. A strong PH launch drives 200-400 trial signups. At 15% trial-to-paid conversion, that is 30-60 paying customers from a single day.

Note: ProductHunt launch is a Month 2 event -- after polish and first customer validation.

### Channel 4: Niche Communities (Expected yield: 2-3 customers per community)

Target subreddits and Slack/Discord communities where the ICP gathers:
- r/Entrepreneur (3.2M members), r/smallbusiness (2M members)
- Agency owner Slack communities (AgencyHive, Communitech)
- Creator economy Discord servers
- Digital nomad and online business communities

Approach: Find active threads where people describe the exact problems Hive Mind solves. Answer genuinely. Mention the product only when directly relevant. Offer a free trial link.

### Founding Member Pricing Incentive

"Founding Member" offer for the first 10 customers:
- Hive plan locked at $39/mo forever (normally $129/mo) as long as they remain subscribed.
- Creates strong retention incentive: cancelling means permanently losing the founding price.
- Creates social proof, word-of-mouth, and urgency for fence-sitters.
- Cost: ~$90/mo x 10 customers = $900/mo in foregone revenue vs standard pricing. This is a $900/mo marketing spend, not a loss. These 10 customers become vocal advocates.

Implementation: Use Stripe coupon with a defined expiry date. Must subscribe (not just sign up) within 7 days of receiving the offer. No code needed by the customer -- the coupon is applied automatically via a unique link.

---

## Long-Term Pricing Considerations

Price increase path: Once the product has 200+ paying customers and NPS above 50, raise Spark from $49 to $69 and Hive from $129 to $169. Grandfather existing customers for 12 months. This is standard and accepted practice for growing SaaS products and is expected by buyers.

Volume discounts for agencies: An agency managing 5+ client workspaces should get a bulk rate. Proposal: $99/workspace/month for 5+ workspaces (vs $129 each). This incentivizes agency scale-out while remaining strongly profitable.

Enterprise custom pricing: Any prospect asking for contract value above $5,000/year should go through a sales conversation, not self-serve checkout. Do not list prices above $399/mo publicly. Use "Contact Sales" for all enterprise custom requests.

Pricing philosophy summary:
1. Price to value, not to cost. An AI Chief of Staff replacing $2,000/mo of contractor labor is worth $400/mo easily.
2. Keep Spark affordable to build trust and customer volume.
3. Hive is the "obvious choice" -- most features, moderate price. This is where the majority of revenue should come from.
4. Enterprise is for agencies reselling to their own clients and teams needing white-label.
5. Never race to the bottom on price. Margin funds better AI quality and faster development.
6. Review pricing every 6 months. Key inputs: conversion rate by plan, churn by plan, gross margin by plan, competitor moves.
