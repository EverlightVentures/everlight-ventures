# Daily 100-Leads Pipeline (Plan-of-Record)

**Status**: PLAN, not built yet. This memo locks the architecture before the build.
**Date**: 2026-05-13
**Goal**: 100 cold-pitched TN leads/day → ~10-30 replies → ~3-8 negotiations in flight → 1-3 contracts/week → batched packages to Chris @ ~$160K cap

---

## Why this exists

Right now we have:
- 32 hand-picked parcels parsed into `owner_downloads/parsed/*.json`
- One ready-to-fire lead (Mikal at 1536 S Third)
- Capacity to manually launch 1 deal at a time via `intel deal launch`

What we need:
- A list of ~1000+ TN addresses (from Rich's existing TN registry list)
- Daily auto-scrape of 100 of those addresses against the Shelby County Assessor
- Auto-vet each against Chris's buy-box criteria
- Auto-launch the cold pitch arc (M1) for each qualified one
- Throttled by Resend daily budget (100/day default cap)
- Parallel negotiation arcs on every replier (the existing arc engine handles this)
- Weekly: package contracts together for Chris when count hits ~10 properties

End state: a single cron job `daily_lead_pipeline.py` that runs at 8 AM PT each business day and orchestrates the whole thing.

---

## Architecture (5 modules)

### 1. `daily_lead_pipeline.py` (orchestrator, ~200 lines)

The cron entry point. Steps per run:

```
1. Load TN address list from `Wholesale/lead_sources/tn_addresses.csv`
2. Filter out: addresses already scraped, addresses already pitched, DNC matches
3. Take next N where N = min(daily_target, RESEND_DAILY_CAP - already_used_today)
4. For each address:
   a. Scrape Shelby Assessor → owner_downloads/parsed/{parcel_id}.json
   b. Vet against Chris's buy-box (call lead_vetting.matches_chris(intel))
   c. If pass: create deal_meta + fire intel deal launch
   d. If fail: log skip reason, move on
5. Print daily summary to Slack #war-room
6. Log every action to deal_execution_log
```

### 2. `tn_registry_scraper.py` (scraper, ~150 lines)

Wraps the existing Shelby Assessor MHTML pattern. We already have parsed JSONs at `owner_downloads/parsed/035093__00032.json` showing the schema. The scraper:

- Takes a parcel_id or street address
- Hits `https://www.assessormelvinburgess.com/propertyDetails?parcelid=...`
- Parses the response into the same JSON schema as existing parsed files
- Saves to `owner_downloads/parsed/{parcel_id}.json`
- Rate-limited: 1 request per 5 seconds (50/min throttle, well below Shelby's tolerance)

Existing infra to reuse:
- The MHTML parser pattern in current parsed JSONs (schema is solid)
- `owner_downloads/inbox/` and `parsed/` directory structure already used

Anti-bot consideration: Shelby Assessor doesn't have aggressive bot detection but use realistic User-Agent + cookie-handling. If it ever blocks, fall back to the manual MHTML download pattern (Rich has done this 32 times already).

### 3. `lead_vetting.py` (Chris's buy-box gate, ~80 lines)

Per `Wholesale/buyers/CHRIS_BATCH_001_DRAFT.json` filter line:
```
"filter": "Memphis + zip in Chris's 15 + status=new"
```

Function `matches_chris(intel: dict) -> tuple[bool, str]`:
- City must equal "MEMPHIS"
- ZIP in Chris's 15 (extract list from CHRIS_BATCH_001 buyer_matches)
- Property class = RESIDENTIAL or vacant lot
- Total appraisal between $5K and $80K (his target range)
- Tax delinquency status known (preferred for motivation)
- Returns (True, "passed") or (False, "<reason>")

### 4. `pitch_factory.py` (per-property OSINT-tailored pitch, ~60 lines)

Wraps existing `pitch_tailor.py` (we built this) + `pitch_generator.py` (existing). Per property:
- Loads parsed intel JSON
- Calls `tailor_for_seller(intel, lead, offer)` to get personalized hook
- Generates Marquise-voiced M1 cold intro using the hook
- Returns the email body ready for `arc_send.m1_intro()`

Already built in `arc_send.m1_intro` — just needs to call `tailor_for_seller` instead of generic template.

### 5. `daily_summary.py` (Slack reporter, ~40 lines)

End-of-day Slack post to #war-room:
- N addresses scraped
- N qualified (passed Chris's filter)
- N pitched (M1 sent)
- N replies received today
- N negotiations active
- N contracts in flight
- N escalations needed Rich
- Top 3 responses with one-liner summary

---

## Resend budget pacing (the rate-limiter)

Existing config in `content_tools/resend_budget.py`:
- Monthly cap: **3,000** sends/month (RESEND_MONTHLY_CAP)
- Daily cap: **100** sends/day (RESEND_DAILY_CAP)
- VIP reserve: **25%** of monthly held back for vip_reply category

Math at default caps:
- 100 cold pitches/day max (uses "bulk" category)
- ~25 reply-replies/day reserved (uses "vip_reply" category, doesn't count against cold cap)
- Monthly: 100 × 22 business days = **2,200 cold pitches/month** (under 3K cap, leaves 800 for follow-ups + system messages)

If we expand: bump to RESEND_MONTHLY_CAP=5000 (Resend Pro plan, $20/mo) for 200/day cold.

The orchestrator queries `resend_budget.check_budget(category="bulk", count=N)` BEFORE firing the daily batch. If today's bulk allowance is already used, it logs and exits.

---

## Daily flow walk-through (a typical day)

```
08:00 PT  Cron fires daily_lead_pipeline.py
08:00:01  Loads tn_addresses.csv (1,247 unscraped rows remaining)
08:00:02  Checks resend_budget.check_budget(bulk, 100) → allowed
08:00:03  Picks next 100 addresses
08:00:04  For each:
            ├─ scrape Shelby Assessor (~5s each = 8 min total for 100)
            ├─ vet against Chris's filter
            └─ if pass → intel deal launch <key>
08:08:00  Done scraping. Summary: 100 scraped, 78 passed Chris's filter, 78 M1 cold pitches fired
08:10:00  Slack post to #war-room with daily summary

09:00-21:00  Phone IMAP poller runs every 2 min
            ├─ Reads replies from any of the 78 cold pitches
            ├─ Classifies + fires next stage automatically (M3/M5/M7 negotiation rounds)
            └─ On accept → fires contract package + esign URLs

End of day:  daily_summary.py posts to Slack:
            ├─ 78 cold pitched
            ├─ 12 replies received (15% reply rate, normal for first-touch)
            ├─ 8 in active negotiation (round 1 or 2)
            ├─ 2 at contract stage (signed PSA)
            ├─ 1 escalation (counterparty hit our wall, Rich review needed)
            └─ Top 3 hottest deals with TLDR

Weekly:     Friday end-of-day, package_for_chris.py runs:
            ├─ Pulls all signed-PSA deals from this week
            ├─ Assembles into a single multi-property package
            ├─ Hammer fires the package to Chris
            └─ Each property gets its own assignment URL
```

---

## Implementation sequence (next session)

| Order | Module | LOC est | Dependency |
|---|---|---|---|
| 1 | `tn_addresses.csv` import (Rich provides the list, just normalize) | 0 (data) | none |
| 2 | `tn_registry_scraper.py` | 150 | requests, beautifulsoup4 (existing) |
| 3 | `lead_vetting.py` | 80 | none |
| 4 | Update `arc_send.m1_intro` to call `pitch_tailor.tailor_for_seller` | 30 | existing pitch_tailor.py |
| 5 | `daily_lead_pipeline.py` orchestrator | 200 | all above + resend_budget + arc_send |
| 6 | `daily_summary.py` Slack reporter | 40 | branded_slack |
| 7 | Add cron line: `0 16 * * 1-5 daily_lead_pipeline.py` (8 AM PT) | 0 | crontab |
| 8 | Build `package_for_chris.py` (Friday weekly) | 100 | arc_send.c_assignment + multi-prop variant |

**Total**: ~600 LOC, one focused build session (~3-4 hours).

---

## Hard prereqs before building

1. **Rich provides the TN address list** (CSV with at minimum: address, city, state, zip).
   Format: `tn_addresses.csv` in `Wholesale/lead_sources/`.
2. **Confirm Chris's exact buy-box criteria** (his 15 ZIPs, target appraisal range).
   Currently in `CHRIS_BATCH_001_DRAFT.json` filter field but should be extracted to its own
   `chris_buy_box.json` for reuse.
3. **Verify Shelby Assessor scraping works at 100/day rate** (test 10 first, watch for blocks).
4. **Set RESEND_MONTHLY_CAP appropriately** if 100/day isn't enough (default fits perfectly).

---

## What this UNLOCKS once built

- Rich goes from "1 manual deal at a time" → "78 cold pitches/day fully autonomous"
- 12 replies/day from 78 sends = ~12% reply rate (industry standard)
- ~8 active negotiations at any given moment running in parallel arcs
- ~3 contracts signed per week
- Weekly multi-property package to Chris (vs one-at-a-time)
- Realistic monthly: 30-60 contracts → batched into 4 weekly packages → Chris pays
- At $3,500 avg per deal × 30/mo = $105K/mo run rate (after ramp)

---

## Risks + open questions

1. **Shelby Assessor rate-limiting**: 100/day is conservative but never tested at scale. If they block, fall back to slower scrape (50/day) or manual MHTML download.
2. **Chris's buy-box may need refinement**: he said up to $160K but we don't know his exact ZIP filter. Need a 15-min call to lock criteria.
3. **Resend deliverability**: 100 cold sends/day from a new domain can hit spam filters. Warm-up the domain over 2 weeks (start at 10/day, grow to 100/day) for best inbox placement.
4. **TN cold-call ban interaction**: M1 emails are FINE per TN cold-email rules. Phone follow-ups still illegal without telemarketer reg.
5. **Multi-property assignment to Chris**: TN SB 909 disclosure must be PER PROPERTY, not bundled. Our package email links to N separate Schedule As, one per property.

---

## When to build

After Deal 1 closes (post-Mikal), Rich confirms Chris's buy-box criteria, and Rich provides
the TN address CSV. Then it's one focused 3-4 hour build session.
