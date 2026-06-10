# Distressed Homeowner Lead Sources -- Shortlist

**For:** Marquise / Everlight Ventures Wholesale
**Date:** 2026-04-26
**Compiled by:** Researcher, Hive Mind
**Constraint set:** sole-prop DBA, no LLC, broke-until-first-deal, Cleveland-OH primary, ATL + Dallas/Houston secondary, automation-friendly

---

## RANKED SHORTLIST (best-fit first)

### 1. PropStream -- Essentials Plan ($99/mo, FREE 7-day trial)
- **URL:** https://www.propstream.com/pricing
- **Data type:** Pre-foreclosure, NOD, tax-delinquent, vacant absentee, code violations, probate, divorce, inherited, high-equity. 20 pre-built lead lists, 165+ filters.
- **Geographic coverage:** All 3 metros. 160M+ U.S. properties. Cleveland (Cuyahoga), Atlanta (Fulton/DeKalb/Gwinnett), Dallas/Houston (Harris/Dallas/Tarrant) all in dataset.
- **Pricing:** $99/mo Essentials (50 free skip-trace credits + 7-day trial), $199/mo Pro, List Automator add-on $27/mo.
- **Email + phone enrichment:** YES via skip trace, $0.12-$0.15 per record on Essentials, bundled higher on Pro.
- **API access:** PARTIAL. Documented push-to-BatchDialer API sync. No public developer API for raw data. Workaround: scheduled CSV exports via List Automator into Supabase.
- **Skip trace included:** Pay-per-record on Essentials, baked-in volume on Pro.
- **Wholesaler-friendly signal:** HIGH. Marketing copy explicitly references "wholesalers seeking distressed properties."
- **Why #1:** Cheapest entry point that produces contact-enriched distressed leads in all 3 metros. Free 7-day trial means $0 to validate before committing.

### 2. BatchLeads -- Growth Plan ($71/mo)
- **URL:** https://batchleads.io/pricing
- **Data type:** Pre-foreclosure, vacant, absentee, tax-delinquent, high-equity, list stacking. Same data lake as BatchData.
- **Geographic coverage:** All 3 metros. 155M property records.
- **Pricing:** Growth $71/mo, Professional $209/mo, Scale $449/mo.
- **Email + phone enrichment:** YES, included in plan. Skip-tracing bundled at no extra cost on every tier.
- **API access:** YES via parent BatchData ($500/mo for 20K Property Search records, $2K/mo Skip Tracing entry tier). Out of budget at API tier; UI delivers exports.
- **Skip trace included:** YES, bundled (key differentiator vs PropStream).
- **Wholesaler-friendly signal:** HIGH. Brand positioning is investor/wholesaler-first.
- **Why #2:** Cheapest plan that includes skip-trace. Beats PropStream Essentials on contact-data unit economics if skip-tracing more than 200 records/mo.

### 3. DealMachine -- Starter ($49/mo annual)
- **URL:** https://www.dealmachine.com/pricing
- **Data type:** Driving-for-dollars + 150M property database, distressed/vacant filters, pre-foreclosure list.
- **Geographic coverage:** All 3 metros, nationwide.
- **Pricing:** Starter $49/mo (annual, 1 driver, 500 leads/mo), Pro $99/mo (1,000 leads), Elite $249/mo (10,000 leads).
- **Email + phone enrichment:** YES, unlimited skip tracing bundled, up to 3 phones + 3 emails per owner.
- **API access:** Zapier + InvestorFuse + Launch Control integrations only. No documented open REST API.
- **Skip trace included:** YES, unlimited (strongest skip-trace economics in shortlist).
- **Wholesaler-friendly signal:** HIGH. Built around D4D wholesaler workflow.
- **Why #3:** Cheapest entry price ($49) and unlimited skip trace, but credit system can balloon costs and API automation is weakest of the three.

### 4. Cuyahoga / Harris / Fulton County Public Records -- FREE
- **URLs:** Cuyahoga: https://cuyahogacounty.gov/treasury/delinquency, Harris: https://www.hctax.net/Property/DelinquentTax, Fulton: https://www.fultonclerk.org/363/Records-Real-Estate-Services
- **Data type:** Tax-delinquent, pre-foreclosure court filings, foreclosure auction lists.
- **Pricing:** $0 (public records).
- **Email + phone enrichment:** NO. Parcel + owner name + mailing only. Requires separate skip trace.
- **Skip trace included:** NO. Pair with BatchData ($0.20/result), DealMachine, or REISift ($0.12-$0.17/record).
- **Why #4:** Free top-of-funnel for the niche, but operationally expensive (3 county scrapers + skip trace pipeline). Use as enrichment layer to validate paid lists, not as primary engine while broke.

### 5. US Probate Leads ($80/mo per county)
- **URL:** https://www.usprobateleads.com/quote/
- **Data type:** Probate court filings.
- **Pricing:** $80/mo per county; bulk historical $0.35-$1.00/lead.
- **Email + phone enrichment:** Often includes attorney + executor mailing. Phone/email skip-trace separate.
- **API access:** Email/CSV delivery only.
- **Why #5:** Niche, low volume, slow burn. Defer until Cleveland niche is producing.

---

## DEFERRED FOR PHASE 1 (out of budget today)

- **BatchData API direct ($500-$2,000/mo)** -- best raw-data + skip-trace API in market, revisit after first deal
- **ATTOM Data Solutions** -- enterprise pricing, custom quote
- **REsimpli ($69-$599/mo)** -- CRM-first, better as Phase 2 upgrade
- **REIPro ($109/mo)** -- weaker data filtering vs PropStream
- **REISift ($49-$97/mo)** -- list-management layer once we have list volume from PropStream + counties

---

## 5-Step Engagement Sequence

**Step 1 (next 24 hours):** Sign up for **PropStream Essentials with the 7-day free trial** at https://www.propstream.com/pricing. Burn the 50 free skip-trace credits on a Cleveland (Cuyahoga + Lake + Lorain) pre-foreclosure + tax-delinquent + high-equity stacked list. Cost: $0 for 7 days.

**Step 2 (day 2-7):** Export to CSV. Push through `compliance/state_gate` (OH is OPEN per state_gates.json). Enrich the 50 skip-traced records. Hand to Piper for branded outreach via `branded_mailer.send_branded_email(category='bulk')`. Measure reply rate + contact-rate before the trial expires.

**Step 3 (day 7-14):** If reply rate >= 2% on the trial list, keep PropStream at $99/mo and add List Automator at $27/mo for auto-refresh. Total: $126/mo. If reply rate < 1%, switch to BatchLeads Growth ($71/mo, skip-trace bundled) and re-test before scaling.

**Step 4 (day 14-30):** Layer in free county data. Build a Cuyahoga delinquent-tax scraper. Stack against PropStream output to remove already-marketed parcels. Zero cost, removes duplicate effort.

**Step 5 (day 30+, post-first-deal):** With closed-deal cash, evaluate BatchData API ($500/mo) for fully programmatic pulls into Supabase. Add US Probate Leads ($80/mo) for a single Cleveland county to test probate niche.

---

## First 24-Hour Action

**Sign up for PropStream Essentials 7-day free trial at https://www.propstream.com/pricing. Zero dollars committed.**

**Rationale grounded in constraints:**
- Sole-prop DBA, no LLC: PropStream has no entity verification, sign up with personal email + DBA name
- Broke until first deal: 7-day trial = $0 outflow
- Cleveland-first: PropStream covers Cuyahoga + adjacent counties out of the box
- Automation-friendly: List Automator + CSV export pipes into existing Supabase + branded_mailer stack
- Data type: pre-foreclosure + NOD + tax-delinquent + vacant absentee in one query, fixes the "309 leads / 3 real emails" problem in week one

---

## Risks / Uncertainties

- PropStream public REST API for raw data pulls is unverified. Documented integrations are Zapier + BatchDialer push-sync. Call PropStream sales to confirm. If REST is closed, drop to scheduled CSV-export workflow.
- Foreclosure.com 2026 pricing did not surface in public search.
- DealMachine "credit system" can balloon costs above sticker. Watch the meter.
- Skip-trace match rates vary by provider (50-70% typical industry range). Plan for ~50% effective contact rate on first run, not 100%.
- US Probate Leads API access is unverified. Expect CSV/email-only delivery on cheap tier.
- This is research, not legal advice. State gates OH, GA, TX are OPEN per state_gates.json. Justine compliance must clear any new template before send.

---

**Researcher, Hive Mind.**
