# Next Levers -- 2026-04-24

Target: **1 closed deal per week** by end of month. This doc tracks the four
levers that move us toward that number, ranked by expected $/hour.

---

## 1. Skip-trace provider pick  (HIGHEST ROI)

**Problem.** 280 individual leads in the DB, only 77 contactable (26 %). The
other 203 individuals have addresses but no phone/email. Without contact
info, the outreach engine goes nowhere.

**Option A: BatchSkipTracing**
- Pricing: $0.15/hit, $0.08/no-hit. 80-95% hit rate on residential.
- API: REST, documented, batch-upload.
- Monthly estimate: 200 leads/mo x $0.15 = **~$30/mo**.
- Integration time: 1 hour (simple wrapper around existing rex_utils).

**Option B: TLOxp (TransUnion)**
- Pricing: ~$5/search but *extremely* complete (DMV records, associates).
- Access: requires DPPA / GLBA permissible purpose on file.
- Best for: high-value deals where you already have the address + want depth.
- Not a good fit for bulk cold outreach. Skip for now.

**Option C: REI Skip**
- Pricing: $0.10-$0.20/hit, high hit-rate on RE-specific data.
- API: less mature than BatchSkip, more manual workflows.
- Integration time: ~3 hours.

**Recommendation: BatchSkipTracing.** Cheapest per-hit, cleanest API, free
trial available. Wire a `skip_trace_batch.py` that:
  1. Reads leads_db.json, filters `email == "" AND phone == ""`.
  2. POSTs 50 at a time to BatchSkip.
  3. Writes phones/emails back to leads_db.json + per-state CSV.
  4. Fires dispatcher `/event/wholesale_lead_enriched` for each lead that
     gained a contact.

**Expected outcome:** 203 * 0.85 hit rate = ~172 newly-contactable leads
in the first pass (~$26 spent). Total contactable pool jumps from 77 to ~250.

Action: get your BatchSkip API key; I wire the integration next session.

---

## 2. ATTOM fresh pull for AZ + TN

**Problem.** Workable states with zero cached leads: AZ, TN, (CA excluded
for pre-foreclosure per CC 2945). AZ is actually your **easiest** compliance
state after GA -- we should be hunting there aggressively.

**Approach.** ATTOM has discovery endpoints we are not yet using:
- `property/snapshot?postalcode=XXXXX` -- returns all properties in zip.
- `salestrend/snapshot?geoIdV4=...` -- market-level stats.
- `assessment/snapshot?postalcode=XXXXX&minassdttlvalue=X&maxassdttlvalue=Y` --
  filtered by assessed value range (great for wholesale targeting).

**Plan.**
  1. Extend `broker/attom_enrichment.py` with `discover_properties_in_zip(zip)`.
  2. For each of ~15 Phoenix metro zips (AZ) + ~10 Memphis metro zips (TN),
     pull top-200 distressed signals (high equity, recent foreclosure notice,
     absentee owner).
  3. Feed results into `state_property_hunter` -> leads_db.json + CSVs.

**Quota math.** ATTOM free tier ~500 calls/month. 25 zip pulls + 200-lead
discovery per zip = 25 calls. Well within budget. Remaining 475 calls
reserved for enrichment (address -> ARV + owner).

**Expected outcome:** AZ 0 -> 100 leads, TN 0 -> 100 leads. Opens the two
cleanest compliance states we have zero coverage in.

---

## 3. Gmail IMAP IDLE -> replace `rex_negotiator` polling

**Problem.** The 2-min `rex_negotiator.py` cron wakes up 30 times per hour
and finds nothing almost every time. When a real reply comes in, it waits
up to 2 minutes before picking it up. Both wasteful and slow.

**Replacement.** A long-running `rex_imap_idle.py` daemon on the phone that:
  1. Opens IMAP IDLE connection to Gmail for `1m.rich.gee@gmail.com`.
  2. On new message event, grabs the message.
  3. Matches sender domain against known lead emails.
  4. POSTs `/event/wholesale_reply` to the dispatcher with thread_id + lead_id.
  5. Dispatcher fires `rex_negotiator.py --thread-id=X --lead-id=Y`.

**Integration time:** ~2 hours. Supervisor pattern same as mcp_tunnel.sh.

**Crontab change.** Delete the `*/2 rex_negotiator.py` line. Add a
`*/5 rex_imap_idle_supervisor.sh`.

**Expected outcome:** replies answered in seconds instead of minutes.
Bigger deal than it sounds -- in cold outreach, 5-minute response vs
2-hour response correlates with 2-3x call-book rate (Forrester 2024).

---

## 4. Additional reverse lead magnets

CashOfferScan is live (wholesale sellers). The other four verticals each
need their own micro-SaaS magnet to apply the boomerang method.

| Magnet | Vertical | Agent | What it does |
|--------|----------|-------|--------------|
| DealPreviewPack | wholesale buyers (cash funds, hedge funds) | Harrison | 5 pre-vetted properties with ARV + repair + cap rate |
| BuyerMatchPreview | Broker OS (B2B SaaS sellers) | Cupid | 3 qualified acquirer leads with messaging angles drafted |
| StackScanner | AI Consulting | Harrison | Detect company's tech stack, return 3 importable automations |
| MenuMarginAudit | Onyx POS | (tbd persona) | Upload menu photo, return per-item margin analysis |
| ClosingChecklistPreview | title companies | Harrison | Title-ready closing checklist pre-filled |

**Build cadence.** 1 magnet per week, ~45 min each in Claude Code after
CashOfferScan template established. Each one boosts its vertical's reply rate
from 1-2% -> 4-6%.

---

## Timing

- **This week:** skip-trace integration (#1) + ATTOM discovery (#2).
  Unlocks the full GA/AZ/MO/TN/FL pipeline.
- **Next week:** IMAP IDLE (#3) + DealPreviewPack (#4a).
- **Week after:** remaining magnets (#4b-#4e).

Contract math assuming skip-trace unlocks 250 contactable leads at the
boomerang-method 4% reply rate:
  250 * 0.04 = 10 replies/week.
  10 replies * 20% call-book = 2 calls/week.
  2 calls * 30% contract = **0.6 contracts/week expected**.
  Hit rate goes up once magnet-click data trains the personalization.

---

## Rollback / safety notes

- Every new wire uses `state_gate.check()` before send (confirmed 2026-04-24).
- Every new wire uses `resend_guard.assert_external_recipient()` (confirmed).
- Every Supabase write goes through the circuit breaker (no hangs on outage).
- Owner comms stay in Slack -- nothing reaches `1m.rich.gee@gmail.com`
  unless `RESEND_ALLOW_OWNER=1` is explicitly set.
