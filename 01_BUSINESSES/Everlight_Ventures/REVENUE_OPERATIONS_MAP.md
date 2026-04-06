# Everlight Ventures -- Revenue Operations Map
## Updated: 2026-03-24 | Compiled by Lucrex (AI CEO)

---

## Revenue Streams (9 active paths to money)

### 1. WHOLESALE REAL ESTATE ($5k-25k per deal)
**How it makes money:** Find distressed properties, get them under contract at discount, assign the contract to a cash buyer for a fee.
**Status:** Pipeline loaded (436 leads, 20 buyers, 4,872 matches). Zero deals closed.
**Team:**
- Rex Blackwell -- Scout leads, underwrite properties
- Piper Reeves -- Outreach to sellers and buyers
- Harrison Knox -- Close deals, manage contracts
- Frederick Banks -- Score and qualify leads
- Calvin Osei -- Match leads to buyers
- Justine Park -- Contract review, compliance

**What's automated:** Lead scoring, matching engine, offer letter generation
**What's NOT automated:** Sending offers, following up on responses, negotiating, signing contracts, collecting assignment fees
**Missing:** Nobody is actually sending offers or following up. The pipeline is full but nothing moves without a human or an orchestrator pushing it forward.

### 2. SURPLUS FUNDS RECOVERY ($1,500-3,000 per claim)
**How it makes money:** Find unclaimed foreclosure surplus at counties, contact former owners, become their recovery agent, file claim, take 15-30% commission.
**Status:** Scraper built, outreach templates ready. Zero claims filed.
**Team:**
- Rex Blackwell -- Scout county excess proceeds
- Piper Reeves -- Contact former property owners
- Samuel Navarro -- File claims with county
- Justine Park -- Review agent authorization forms

**What's automated:** County scraping (when it runs)
**What's NOT automated:** Everything after scraping -- contacting owners, signing authorization, filing claims, collecting commission
**Missing:** The scraper hasn't successfully found any claims yet (needs debugging). No claims in progress.

### 3. CREATIVE FINANCE ($7k-15k per deal)
**How it makes money:** Instead of cash wholesale, structure subject-to, owner-finance, or lease-option deals. Higher margins.
**Status:** Underwriting engine built and tested. Zero offers sent.
**Team:**
- Rex Blackwell -- Source properties, run underwriting
- Piper Reeves -- Send offer letters
- Harrison Knox -- Negotiate and close
- Penny Vance -- Verify deal math

**What's automated:** Underwriting calculations, offer letter generation
**What's NOT automated:** Batch sending offers, tracking responses, negotiating
**Missing:** Nobody is running the batch offer sender daily.

### 4. XLM TRADING BOT ($50-500 per scalp)
**How it makes money:** Automated trading on Coinbase XLM perpetual futures. Scalps small moves.
**Status:** LIVE on Oracle Micro. Down $100 last week. Currently flat in COMPRESSION.
**Team:**
- Rex Thornton -- Risk analysis, parameter review
- Miguel Reyes -- Derivatives/volatility analysis
- Market intel layer (sentiment, on-chain, correlation) -- running every 5 min

**What's automated:** Trade execution, market intel gathering, AI entry/exit decisions
**What's NOT automated:** Parameter adjustment when bot is losing, human override on bad trades, weekly performance review
**Missing:** NOBODY IS WATCHING THE BOT. It lost $100 and nobody stepped in. Rex Thornton should be reviewing trades and recommending parameter changes. The bot should NOT be left unsupervised.

### 5. AI CONSULTING ($2k-5k builds + $2k/mo retainers)
**How it makes money:** Build AI automations for small businesses. Charge for the build, then monthly retainer.
**Status:** Landing page built, outreach templates exist. Zero clients.
**Team:**
- Ryan Kim -- GTM, sales, pipeline
- Frederick Banks -- Qualify leads
- Raymond Harper -- Build automations
- Patrick Donovan -- QA deliverables

**What's automated:** Scout for leads (broker-os MCP scouts HN, Product Hunt, etc.)
**What's NOT automated:** Outreach, sales calls, closing, building, delivering
**Missing:** Nobody is actively prospecting or closing consulting deals.

### 6. FREELANCE REVENUE ($1k-3k/week)
**How it makes money:** Sell AI automation, content writing, data scraping, dashboards on Fiverr/Upwork.
**Status:** Gig templates written. No accounts created. Zero revenue.
**Team:**
- Ryan Kim -- Create profiles, list gigs
- Raymond Harper -- Fulfill orders
- Patrick Donovan -- QA before delivery

**What's automated:** Nothing
**What's NOT automated:** Everything -- account creation requires human, gig listing, order fulfillment, delivery
**Missing:** Needs human to create Fiverr account (requires ID verification). Then orders can be semi-automated.

### 7. BROKER OS / SaaS DEALS ($500-2k per finder fee)
**How it makes money:** Match SaaS sellers with SaaS buyers. Take 15-30% finder fee.
**Status:** 61 deals scouted from HN/dev.to/GitHub. Zero qualified, zero matched.
**Team:**
- Sebastian Navarro -- Scout deals
- Frederick Banks -- Qualify
- Calvin Osei -- Match
- Piper Reeves -- Outreach
- Harrison Knox -- Close

**What's automated:** Scouting (broker-os MCP bulk_scout)
**What's NOT automated:** Qualification, outreach, negotiation, closing
**Missing:** Nobody is working the SaaS broker pipeline.

### 8. EVERLIGHT FIELD OPS (future -- $11k/mo by month 4)
**How it makes money:** AI-to-human field task marketplace. 18% platform take rate + API subscriptions.
**Status:** Product spec, schema, API, React page all built. Waitlist tables live. Pre-revenue.
**Missing:** Need to launch, get workers signed up, get businesses posting tasks. This is a medium-term play.

### 9. PUBLISHING / CONTENT (passive income)
**How it makes money:** Amazon KDP books (Sam & Robo series, Beyond the Veil). Passive royalties.
**Status:** Books published. Revenue trickles in.
**Missing:** No active marketing. Content factory dormant.

---

## What's Missing (The Gap Analysis)

### A. No Orchestrator That Actually Executes
The shift system posts chat. The work engine runs scripts. But NOBODY:
- Checks if outreach emails got replies
- Follows up when a buyer doesn't respond in 48 hours
- Escalates when a deal stalls
- Adjusts bot parameters when it's losing
- Moves deals from "matched" to "under contract" to "closed"

### B. No Revenue Tracking Dashboard
We have Django with payments/broker_ops apps, but:
- No real-time revenue counter
- No "money in the bank" tracker
- No deal stage progression (lead -> contact -> offer -> contract -> closed -> paid)
- No commission tracking for surplus claims

### C. No Compliance Guardrails
- Outreach should ONLY fire during 8 AM - 9 PM local time of the recipient
- Every email needs CAN-SPAM footer (physical address, unsubscribe)
- Every text needs TCPA compliance (opt-in or established relationship)
- DNC list scrubbing before any phone outreach
- Contract templates need Justine's review stamp

### D. No Bot Supervision
- Weekly P&L review should trigger parameter adjustments
- Consecutive loss limit should pause the bot and alert Rex Thornton
- Position size should scale with equity (currently static)
- Someone should review the AI's reasoning on every losing trade

### E. No Self-Healing
- When a service dies, Quinn should restart it AND page Marcus
- When a cron fails 3 times in a row, it should escalate
- When outreach gets bounced emails, it should flag the lead as bad
- When a buyer doesn't respond in 72 hours, next buyer gets the deal

---

## Revenue Target: $10k/month -> $100k/month

### Month 1 (This Week)
- Close 1 wholesale deal: $5k-10k
- File 1 surplus claim: $1,500-3,000
- Bot scalps: $200-500
- Total target: $7k-13k

### Month 2
- 2-3 wholesale deals: $10k-25k
- 3-5 surplus claims: $4,500-15,000
- AI consulting client: $2k-5k
- Freelance gigs: $2k-4k
- Bot: $500-1,000
- Total target: $19k-50k

### Month 3
- Scale wholesale to 4-6 deals: $20k-50k
- Surplus pipeline running in 5+ counties: $10k-30k
- 2 consulting retainers: $4k/mo recurring
- Freelance: $3k-6k
- Bot: $1k-2k
- Total target: $38k-92k

---

## What Needs to Be Built Next

1. **Autonomous Deal Orchestrator** -- A script that checks deal stages every hour, fires next actions automatically (send offer, follow up, escalate), and tracks everything in the work ledger. This is the "manager" that makes the team actually do work.

2. **Business Hours Compliance Layer** -- Wrapper that checks recipient timezone before any outreach. Queues messages for legal hours. Adds CAN-SPAM footers automatically.

3. **Bot Watchdog with Human Override** -- Rex Thornton reviews every trade, flags patterns, recommends parameter changes. Posts weekly P&L review. Can pause the bot if losses exceed threshold.

4. **Revenue Dashboard** -- Real-time counter in Django showing money earned, deals in progress, pipeline value, projected revenue.

5. **Self-Healing Monitor** -- Quinn Sharp watches all services and crons. Auto-restarts failures. Pages Marcus via Slack if something can't be auto-fixed.
