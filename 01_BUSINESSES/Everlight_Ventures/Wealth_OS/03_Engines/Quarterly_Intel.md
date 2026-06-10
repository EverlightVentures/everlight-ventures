# Quarterly Intel Engine
## The Always-On Law-Change Hunter

**Tax law changes constantly. State legislatures pass new laws every session. The IRS issues revenue rulings every month. New cases set precedents. Sunset clauses approach. Without an active intelligence system, you find out about law changes 18 months after they happen, often too late to optimize.**

**This engine runs forever.**

---

## What It Monitors

### Federal Tax Law Changes
- TCJA sunset provisions and extensions/replacements
- SECURE Act 2.0 phase-ins and modifications
- R&D capitalization (Sec 174) status
- Bonus depreciation phase-down schedule
- Estate / gift / GST exemption inflation adjustments
- 7520 rate / AFR rate monthly updates
- Opportunity Zone designation changes
- New credits (clean energy, semiconductor, etc.)
- Sunset of existing credits

### IRS Activity
- Revenue Rulings, Revenue Procedures
- Notices and Announcements
- Dirty Dozen list updates
- Tax Court memorandum opinions
- Regulations (proposed, temporary, final)
- Audit campaign focus areas

### State Tax / Legal Changes
- California: FTB rule changes, residency audit positions, AB 5 / contractor reclassification
- Wyoming/Nevada/Delaware: LLC and trust law amendments
- South Dakota: trust law modifications, dynasty trust modifications
- Florida/Texas: domicile-friendly law changes
- Puerto Rico: Act 60 modifications (frequent, watched closely)

### Real Estate Specific
- Cost segregation safe harbor updates
- 1031 like-kind exchange definition changes
- Opportunity Zone new designations
- REPS qualification audit positions
- Short-term rental tax position updates

### Crypto / Digital Asset
- Wash sale rule application to crypto (current loophole closing date)
- Staking taxation rulings
- DeFi position guidance
- Reporting requirement changes (1099-DA, etc.)

### International
- FBAR / FATCA reporting changes
- FEIE inflation adjustments
- Treaty modifications
- Transfer pricing safe harbors
- GILTI / Subpart F modifications

---

## How It Operates

### Monthly Cadence
- 1st of every month: Hive agent scans changes since last run
- Sources: IRS.gov, Tax Notes Today, Bloomberg Tax, Journal of Accountancy, JCT reports, state revenue departments, ABA Tax Section, AICPA, ProPublica, Tax Foundation
- Posts deltas to `#ceo-brief` Slack channel
- Saves findings to `04_Dispatch_Log/Intel_YYYY-MM.md`

### Quarterly Deep Dive
- Each quarter (Jan, Apr, Jul, Oct): comprehensive review of changes since last quarter
- Stress test against current tier moves
- Recommend updates to OS files if law has shifted
- Schedule professional consultations for any major change requiring action

### Annual Recalibration
- November of each year: forward-looking annual planning session
- Year-end deduction push opportunities
- Roth conversion analysis based on YTD income
- Charitable bunching analysis
- Equipment / bonus depreciation push (especially as bonus phases down)
- Lifetime exemption usage decisions for the new year

---

## Critical Active Watch List (As of 2026-04-25)

| Item | Deadline | Action If Triggered |
|---|---|---|
| **TCJA estate exemption sunset** | Dec 31, 2025 | If trajectory crosses $7M, deploy SLAT/Dynasty Trust pre-sunset |
| **TCJA individual rate sunset** | Dec 31, 2025 | Defer income to 2026+ if rates rise; accelerate to 2025 if rates extended |
| **199A QBI deduction sunset** | Dec 31, 2025 | Push pass-through income into 2025 if possible |
| **Bonus depreciation: 60% (2025) -> 40% (2026)** | Phasing | Front-load equipment and cost-seg studies |
| **Section 174 R&D capitalization** | Watch for restoration | If restored to immediate expensing, refile amended returns |
| **PR Act 60 modifications** | Ongoing | Major rewrites have happened; watch carefully if PR is in plan |
| **SECURE Act 2.0 RMD age** | Phasing to 75 by 2033 | Plan retirement withdrawal sequencing |
| **Wash sale rule for crypto** | Possible legislation | Stop using crypto wash sale loophole if/when law changes |

---

## How To Use This Engine

1. **Monthly review:** Read the auto-posted summary in `#ceo-brief`. Spend 5 minutes.
2. **Flag actions:** If any item requires action, schedule with appropriate professional within 30 days.
3. **Quarterly deep-dive:** Block 1 hour per quarter to review the full intelligence drop.
4. **Annual planning:** Block 1 day per year for comprehensive OS recalibration.

---

## Sources Index (For Manual Lookup)

- **IRS:** https://www.irs.gov/newsroom (free)
- **Tax Notes Today:** https://www.taxnotes.com (paid, ~$3k/yr -- worth it at T4+)
- **Bloomberg Tax:** https://www.bloomberglaw.com/tax (paid, expensive)
- **Journal of Accountancy:** https://www.journalofaccountancy.com (free)
- **AICPA:** https://www.aicpa-cima.com (free for many resources)
- **JCT (Joint Committee on Taxation):** https://www.jct.gov (free)
- **Tax Foundation:** https://taxfoundation.org (free)
- **ProPublica IRS reporting:** https://www.propublica.org (free, sporadic)
- **State revenue department websites:** vary

---

## Manual Schedule Setup (Until Hive Agent Activated)

Add to your calendar:
- 1st Monday of each month: 30 min "Quarterly Intel scan" (review IRS news, save to log)
- 1st Monday of Jan/Apr/Jul/Oct: 1 hour "Quarterly Deep Dive"
- 2nd Monday of November: 1 day "Annual Recalibration"
