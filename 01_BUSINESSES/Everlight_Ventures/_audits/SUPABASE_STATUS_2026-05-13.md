# Supabase Status Audit -- 2026-05-13 (CORRECTED)

**Project URL:** `https://jdqqmsmwmbsnlnstyavl.supabase.co`
**Anon key + service role key:** present in `03_AUTOMATION_CORE/03_Credentials/.env`
**Auditor:** Hive (Loop 7 + correction from Rich, 2026-05-13)
**Status:** ALIVE AND HEAVILY USED -- 105 tables, 55 active, 182,575 rows

---

## CORRECTION FROM THE INITIAL DRAFT

The first version of this memo (saved earlier today) said Supabase was "functionally
empty with 2 rows in `leads`." **That was wrong.** I probed with the anon key and
Row Level Security correctly hid 104 of 105 tables from me. Rich pushed back: "no
way Supabase is empty, we've been pushing to that." Re-probing with the service
role key revealed the real state.

**Lesson logged:** memory rule `feedback_verify_source_of_truth.md` -- always probe
authoritative systems with the right auth context, and especially with RLS-protected
PostgREST projects, anon-key enumeration is meaningless. Re-test with service role
before drawing conclusions.

---

## Real state

| Metric | Value |
|---|---|
| Tables total | 105 |
| Tables with > 0 rows | 55 |
| Total rows across project | 182,575 |
| Most active writer | `xlm_bot_timeseries` (67,293 rows; last write today) |

### Top 15 by row count

| Table | Rows | Last write |
|---|---:|---|
| `xlm_bot_timeseries` | 67,293 | 2026-05-13 07:07 UTC (LIVE) |
| `xlm_bot_feature_snapshots` | 49,020 | (frequent) |
| `xlm_market_intel_runs` | 38,637 | (frequent) |
| `xlm_bot_report_history` | 23,022 | (frequent) |
| `xlm_market_intel_claims` | 1,487 | -- |
| `xlm_market_intel_documents` | 653 | -- |
| `hive_master_log` | 510 | 2026-04-09 |
| `player_events` | 413 | -- |
| `flip_intel` | 254 | 2026-04-24 |
| `wholesale_buyers` | 201 | 2026-04-05 |
| `blackjack_hands` | 163 | -- |
| `xlm_bot_trade_labels` | 160 | -- |
| `player_sessions` | 111 | -- |
| `rex_pipeline` | 93 | 2026-03-21 |
| `wholesale_sellers` | 65 | -- |

### Schema groupings

- **XLM bot telemetry (8 tables, 178K rows)**: live, written every few seconds
  by the bot on Oracle Micro. Source of truth for trading PnL, market intel,
  report history. **Do NOT migrate** -- volume is too high; if Supabase free
  tier limits hit, this is the first thing that breaks.
- **Hive operational logs (15 tables, ~700 rows)**: `hive_master_log`,
  `hive_agent_registry`, `hive_duty_roster`, `hive_error_ledger`, etc. Cold
  since Apr 9 -- the local Django dashboard hasn't been writing here since
  it went dark.
- **Wholesale operational (6 tables, ~400 rows)**: `wholesale_buyers`,
  `wholesale_sellers`, `wholesale_outreach`, `wholesale_states`, etc. Cold
  since early Apr -- we pivoted to local SQLite for the deal audit chain.
- **Broker / consulting (5 tables, ~50 rows)**: `broker_offers`, `broker_leads`,
  `broker_knowledge`, `customers`, `download_tokens`. Cold since Mar 13.
- **Gaming (10 tables, ~700 rows)**: blackjack + arcade. Vantaris production.
- **Field Ops + Flip (5 tables, ~300 rows)**: waitlist + flip inventory.

---

## What this means for production

### Surfaces currently relying on Supabase (KEEP)

- **XLM bot reporting** -- the live `xlm_bot_*` tables are the source of truth.
  Don't touch.
- **`everlightventures.io` public site** -- the `leads` contact-form catcher
  is one of the 105.
- **Vantaris / blackjack / arcade** -- Vantaris frontend reads from Supabase.

### Surfaces that pivoted to local SQLite (intentional)

- **Deal audit chain** (`deal_execution_log.py` -> local sqlite). The hash chain
  needs absolute write integrity that's harder to guarantee through Supabase.
  Keep local.
- **Hive Master Log on the phone** (cold in Supabase since Apr 9) -- not a
  problem because Hive sessions land in Blinko (local + e5-mother) instead.

### Decision: keep both, dual-write where useful

For new ops surfaces that need cross-device read access (Marquise's PC, the
public site dashboards we haven't built yet), mirror writes into both:
1. Local SQLite / JSON (immediate, audit-grade)
2. Supabase REST (cross-device, public-readable)

The dual-write pattern is already in use for some xlm_bot writes. The same
pattern can extend to broker / wholesale ops once we have a reason to
(public deal-track-record page, multi-device coordination, etc.).

---

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Update CLAUDE.md "Supabase is source of truth for ALL production data" to nuance: source of truth for XLM bot telemetry + Vantaris + public-facing surfaces; local SQLite is source of truth for deal audit chain | Rich + Hive | TODO next session |
| 2 | Confirm xlm_bot writes are still flowing (last write was 7 min ago at audit time -- ALL GOOD) | -- | DONE |
| 3 | Reactivate hive_master_log writes from active services -- the gap since 2026-04-09 means the master log is missing the last 5 weeks of ops | Hive sessions | TODO -- add a daily heartbeat row from cron |
| 4 | Add `wholesale_outreach` and `wholesale_buyers` writes from `arc_send.py` outbound sends so the live deal flow lands in Supabase too (NOT replacing local audit chain, additive) | Hive | DEFERRED -- after Deal 1 ships |
| 5 | Apologize + correct earlier memo. | Hive | DONE |

---

## Lesson logged

This is exactly the failure mode memory rule `feedback_verify_source_of_truth.md`
exists to prevent. The fix going forward:

- Treat anon-key probe outputs as "what an unauthenticated visitor can see," not
  "what's in the database."
- For Supabase / any RLS-protected PostgREST project, always re-probe with service
  role when auditing schema or row counts.
- For ANY system-of-truth audit, probe at the highest legitimate auth context
  first.

**Bonus rule:** before claiming a system is "empty" or "dead," ask the user
"does that match what you'd expect?" Rich's pushback caught this in 5 minutes
what could have led to a bad doctrine update.
