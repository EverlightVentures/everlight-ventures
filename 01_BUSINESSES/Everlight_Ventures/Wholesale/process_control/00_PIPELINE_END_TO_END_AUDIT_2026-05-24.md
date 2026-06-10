# Wholesale Pipeline -- End-to-End Audit
**Date:** 2026-05-24 PT | **Commander:** Lucrex | **Method:** 4-lane parallel Hive dispatch (engineering wiring / TN legal / deal-flow / brain-feed) with receipts.

> One-line verdict: **The machine is ~85% built and 0% flowing. It is armed, pointed at the wrong market, frozen on purpose, and feeding a brain that is offline. None of that is a code problem -- it is an aim, wiring, and greenlight problem.**

---

## FIXES SHIPPED 2026-05-24 (Option 1 -- wiring, proven with receipts)
1. **Brain made always-on (local-first).** `rex_master_pipeline.log_blinko()` rewritten: writes try local blinko-lite (`127.0.0.1:2700` -> `:1111`) before `e5-mother`, and fall back to the offline queue if all are down. No more silent drops to a dead host. **Receipt:** brain went 618 -> 619 -> 620 notes on live writes while e5-mother is down; test note confirmed in `_logs/blinko_lite.db`.
2. **Scoreboard un-orphaned.** New `workbook_logger.sync_from_leads_db()` derives the funnel from the real `leads_db.json`; wired into the live orchestrator's report stage so it self-heals every run. **Receipt:** `performance_metrics.json` now reads scouted 3163 / scored 3154 / qualified 309 / matched 2469 / outreach 38 / responses 0 / closed 0 (was all-zeros).
3. **Streubel proven scoped, not global.** `eradication_gate.find_hit()` BLOCKS his email/domain/name/address; a normal Memphis seller PASSES. The per-recipient gate is his leash -- the global halt is collateral damage. (Halt NOT lifted -- pending the 6-box checklist + operator greenlight.)
4. **Brain location documented.** `06_DEVELOPMENT/everlight_os/docs/BRAIN_MAP.md` -- the 3-layer map (doctrine memory / RAG notes / session mailbox) + always-on rule. New memory laws: `feedback_brain_intact_local_first`, `feedback_scoped_eradication_not_global_halt`, `reference_brain_location_map`.

**Still open (named, not done):** assessor parse yields property_address + owner_name -> skip-trace for the owner's EMAIL (digital-only: NO mailing address needed, ever); mailbox->Blinko session ingest; the halt-lift checklist (operator-gated); confirm Mid-South buy-box.

---

## 0. Answers to the operator's questions (fast)

| Question | Answer |
|---|---|
| When did we start? | **2026-04-06/07** (~7 weeks). Metrics file created 2026-04-07. |
| Closed a deal? | **No.** Zero closes, zero contracts sent, zero seller replies. |
| Why not? | Four compounding causes (below): wrong-market scouts, dead scout billing, intentional outbound HALT, and unworkable seller inventory. |
| Is TN ready? | **Conditional GO** -- email is legally clear today; the contract/assignment step has 3 real blockers. |
| Brain getting smarter? | **No.** Vector layer (e5-mother) is down 9 days; pipeline writes to a dead host and silently fails. Fed only by accident. |
| Almost finished? | **Built, not finished.** It has never run clean end-to-end on the real target once. |
| Mission statement? | **Created** -> `Wholesale/00_MISSION.md`. |
| Elite-organized? | Not yet. Restructure proposed in §6. |

---

## 1. The pipeline, front to back (what exists)

**Arsenal:** ~80 Python modules. This is genuinely deep.
- **Scout (front):** rex_distress_finder, rex_zillow_keyword_scraper, rex_probate_scout, rex_tax_delinquency_scout, rex_teardown_finder, lis_pendens_pipeline, surplus_funds_finder.
- **Score/enrich:** rex_lead_scorer v1/v2, rex_enrichment_engine, skip_trace_and_enrich, free_skip_tracer, rex_comp_validator, rex_repair_estimator, land_analyzer.
- **Offer:** rex_multi_tier, creative_finance_engine, rex_batch_offers, rex_deal_sheet, rex_straight_line.
- **Outreach (front):** piper_* engines, rex_sdr, rex_7touch_sequence, rex_belfort_sequence, hive_outreach, rex_direct_mail, agent_outreach_templates.
- **Negotiate/close (back):** rex_negotiator, rex_closer, contract renderers, gdocs_bridge, deal_slack.
- **Buyer side (back):** rex_buyer_acquisition, rex_buyer_segmenter, buyers_db (84 buyers).
- **Compliance (cross-cutting):** eradication_gate, rex_stop_handler, state_gate, opted_out/dnc stores.
- **Personas:** Piper -> Henry -> Marvin -> Vaughn handoff chain + Marquise (intel) + Lo Hines (TN compliance).

**Data:** 3,163 leads (2,470 TN / 2,444 Memphis), 84 buyers (9 TN incl. Mid-South Homebuyers).

---

## 2. The four fractures (why nothing flows) -- with receipts

### Fracture A -- Wrong market + dead billing (scouts produce 0)
- The live orchestrator (`wholesale_hive_pipeline.py`, 3x daily cron) runs scouts hardcoded to **Atlanta / Cleveland / Dallas / Jacksonville / St. Louis** -- **never Memphis.** Target lists live at the top of each scout (e.g. `rex_distress_finder.py:64 TARGET_MARKETS`).
- All 5 scouts are **100% Perplexity-API-driven**, and the Perplexity account is **out of quota: HTTP 401 `insufficient_quota`** (live probe). Every query returns "" -> 0 properties. The "all zeros since 2026-04-07" timeline matches the quota dying.
- **Silent-success bug:** the orchestrator marks scouts `[PASS]` because it only checks subprocess exit code (`wholesale_hive_pipeline.py:91`), not `properties_found`. A fully dead pipeline reports green.

### Fracture B -- Five orchestrators, one runs, the Memphis one is stalled
- **Canonical/live:** `wholesale_hive_pipeline.py` (the only one in the real crontab). Wrong-market + dead-billing per A.
- **`rex_master_pipeline.py` (edited today) is DEAD on the phone** -- invoked by no cron; only referenced by `deploy_wholesale.sh` which writes an *Oracle-side* crontab. Today's edit had zero runtime effect here.
- `rex_daily_run.py`, `rex_autonomous.py` -> dead / child-only.
- **`Wholesale/scripts/daily_lead_pipeline.py` is the ONLY Memphis-native pipeline** (reads local parcels + `chris_buy_box.json`, needs no paid API) -- but its log froze 2026-05-13; it errors before first write. **This is the engine to revive.**

### Fracture C -- Outbound is HARD-HALTED on purpose
- `WHOLESALE_OUTBOUND_HALT=1` is live in `/root/.config/everlight/secrets.env`. Proof in `_logs/rex_7touch.log`: every hourly run logs `WHOLESALE_OUTBOUND_HALT=1 -- refusing to load`.
- Set after the **Streubel 2nd-strike (2026-05-15)**. Belfort/7touch/hive_outreach all refuse to load. The 38 contacted leads are pre-halt residue; **0 sends since.**
- Lift gate = 6-box checklist in `_state/SELF_AUDIT_2026-05-15_STREUBEL_2ND_STRIKE.md`, all unchecked, **including Rich's explicit greenlight.** This is correct and intentional -- do NOT just flip the env var (that is exactly how the 2nd strike happened).

### Fracture D -- The seller inventory is unworkable
- `leads_db.json` Memphis records are a **mirage**: of 2,470 TN leads, **0 have a mailing address**, only 32 have an owner name, and the 9 with "contact info" share a **fake Faker phone `028-037-3832` + `f@faisalman.com`**. Real reachable TN leads in the DB = **0**.
- The real inventory is `Wholesale/seller_intel/SELLER_EMAILS_READY_TO_FIRE_v2.md`: **110 Chris-eligible, 27 HIGH** with real parcel IDs + owner mailing addresses. **But it is almost all VACANT LOTS** -- and our anchor buyer (Mid-South Homebuyers) buys **houses**. Likely buyer-mismatch on property type. No emails/phones captured yet (direct-mail-ready, not email-ready).

---

## 3. TN legal readiness (Lo Hines + Heck Aurelio)

**VERDICT: CONDITIONAL GO -- email-first, one deal, hand-rendered contract.**

- **Email TODAY = clear.** The branded_mailer gate chain (eradication -> send_authority TN-lockdown -> resend_guard -> state disclaimer -> budget -> cadence -> phrase_scrub) is real and fail-closed. CAN-SPAM elements present. Piper can send a compliant TN seller email now.
- **Cold call / SMS = BLOCKED** (correctly) -- TN telemarketer registration ($500/yr) not filed; `state_gates.json` enforces `cold_call_allowed:false`.
- **Streubel eradication = enforced, fail-closed**, hardcoded in `eradication_gate.py` as Layer-2 first check.

**REAL contract/assignment blockers (gate the close, not the email):**
1. **Two contract generators -- only one is compliant.** Use `intel_center/osint_api/contract_renderer.py` (real SB 909 Schedule A, already shipped on the Hakeem deal). The `Broker_OS/contract_generator.py` that produced the **117 Farrow Ave PDF has NO Schedule A** -- its `tn_sb909_schedule_a_bundled:true` flag is hand-set. **Do not send 117 Farrow to a seller.** Add code gate: `assert state != "TN" or schedule_a_present`.
2. **Mid-South Title RESPA-clean verification** + signed "no referral fee" acknowledgment before first PSA.
3. **Title firm confirms assignment fee as a settlement-statement line item** (SB 909 item 4). One phone call.

**Post-Deal-1 (not blockers):** Shelby County business license ($37, file on close day), TN LLC formation, $50K surety bond (triggers at Deal 3). TN telemarketer reg only if we ever cold-call.

---

## 4. The brain / vector DB (is the "neural network" being fed?)

**VERDICT: Fed partially and by accident, not by design.**
- **Vector layer is DARK.** e5-mother Blinko (`:1111`, the real RAG) + agentmemory MCP (`:3108`) = **HTTP 000, down 9 days** (`last_mother_sync` = 2026-05-15). What's live is **local blinko-lite (SQLite FTS5, 618 notes, 127.0.0.1:2700 + :1111)** -- text search, **not embeddings**. There is no live vector brain right now.
- **Pipeline -> brain feed is BROKEN.** `rex_master_pipeline.log_blinko()` hardcodes the dead `e5-mother:1111` and wraps the POST in `try/except: pass` -- silent failure, no fallback, no queue. Every run writes nothing.
- **leads_db -> brain = no path exists.** Deal outcomes never reach RAG. The brain cannot learn from lead data.
- **Mailbox -> brain = not wired.** Session exports only `file_replace` the mailbox to a dead host; content is never ingested as searchable notes. The `sync_queue.jsonl` retry queue is **jammed** (same payload re-queuing, all targeting the down host) -- working as designed, just blocked on e5-mother.
- **Dead-cron drift:** `blinko_log_ingest.sh` (3:30 AM) still targets the **old dead mother `129.159.38.250`**.
- **Stale memory correction:** the note `feedback_offline_first_bidirectional_sync` says phone->cloud is "NOT YET WIRED" -- it IS wired, just blocked on e5-mother. Update it.

---

## 5. Tools / skills / repos -- are we using everything? What to build?

- **GitHub repos to the max:** the paid Perplexity scout layer is the failing piece. Repo catalog already sanctions **`scrapy`** as the free scraping upgrade. **Action:** rebuild scouts on free OSS (scrapy + county-record sources) OR (faster) revive the local Memphis parcel parser that needs no API at all.
- **Skills underused:** `karpathy_rag_intake` (3-tier knowledge discipline) should govern the mailbox->brain ingest. `observability_first` / `canonical_log_line` should govern the scoreboard wiring. `hermes_browser_outreach` is a built browser-scraper harness that could replace dead Perplexity scouts.
- **To build ourselves (no purchase):** (a) `scout_markets.json` single config so all scouts read one market list; (b) `wb.sync_from_leads_db()` to un-orphan the scoreboard; (c) a `leads_db -> blinko` outcome-ingest; (d) free skip-trace cascade completion on the 27 HIGH parcels.

---

## 6. Organization verdict -- "elite-organized?"

**Not yet -- it is a brilliant arsenal in a messy armory.** Symptoms: 5 competing orchestrators, target market hardcoded in 5 places, a placeholder contract generator sitting next to the real one, a scoreboard nothing writes to, and a "live" edit today (`rex_master_pipeline.py`) that runs nowhere.

**Elite structure (proposed):**
1. **ONE orchestrator, one config.** Canonize `daily_lead_pipeline.py` (Memphis-native) as the engine; quarantine/label the other 4 (per No-Trash-Until-Deal-1, label don't delete). One `scout_markets.json`, one buy-box, one metrics call.
2. **ONE contract path.** Route all TN through `contract_renderer.py`; tombstone `Broker_OS/contract_generator.py` for TN with the assert gate.
3. **Mission on top.** `00_MISSION.md` now sits above `process_control/01-08`. Reread at sprint start.
4. **Scoreboard is law.** Wire `workbook_logger` so every scout/send/stage-change bumps `performance_metrics.json`. If it is not on the scoreboard, it did not happen.
5. **One status command.** `rex_health.py` should report: leads reachable, sends today, halt state, brain reachable, scoreboard funnel -- one screen of truth.

---

## 7. Path to Deal 1 (the only thing that matters)

**Steps 1-2 need NO halted system and NO money -- start today:**
1. **Confirm Mid-South Homebuyers' buy-box** (email `leads@midsouthhomebuyers.com`): houses vs lots, ZIPs, max ARV, proof-of-funds. If lots are out, the entire READY_TO_FIRE list is dead for Chris -> pivot to distressed houses.
2. **Hand-build 10 real, reachable Memphis HOUSE leads** (tax-delinquent / probate SFRs) with owner mailing + skip-traced phone. The 3,163-lead DB is a mirage; build small and real.
3. **Clear the 6-box HALT lift checklist** (code boxes are quick) + **get Rich's explicit greenlight.** Never flip the env var alone.
4. **Work 5-10 sellers by EMAIL only** (digital-only law -- NO physical mail, ever). Skip-trace each parcel for the owner's email from name + property; if no email, skip-trace harder or wait -- never fall back to mail. Branded email via Piper once the halt lifts.
5. **Lock seller** on assignable PSA via the COMPLIANT renderer (+ inspection contingency exit).
6. **Assign to the matched Memphis buyer, collect the spread.** That is Deal 1.

---

## 8. Receipts
- Scout 401: live Perplexity probe returned `{"type":"insufficient_quota","code":401}`.
- Halt: `_logs/rex_7touch.log` "WHOLESALE_OUTBOUND_HALT=1 -- refusing to load" every hourly run.
- Brain down: e5-mother `:1111` HTTP 000; `last_mother_sync.txt` = 2026-05-15; local blinko-lite `/health` 200, 618 notes.
- Scoreboard orphaned: only `workbook_logger._bump_metric` writes funnel; no production script calls the funnel loggers; `funnel_metrics` all-zero vs 3,163 real leads.
- Fake leads: TN contact records share phone `028-037-3832` + `f@faisalman.com`.
- Compliant Schedule A proof: `09_DASHBOARD/reports/deals/2026-05-12_mikal_hakeem_1536_s_third/02_Schedule_A_TN_SB909.html`.

*Generated by Lucrex Hive 4-lane dispatch. Agent IDs on file for continuation.*
