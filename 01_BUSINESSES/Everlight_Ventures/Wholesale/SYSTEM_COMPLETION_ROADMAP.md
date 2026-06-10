# System Completion Roadmap -- Everlight Ventures Wholesale Stack

**Compiled:** 2026-04-26 by Hive Operating Desk
**For:** Marquise Smith
**Definition of complete:** all 13 pipeline steps have working code with raw-evidence verification, all compliance gates are live, all inbound is watched by named agents in real-time, all counterparty-only dependencies are documented and ready for human action.

---

## P0 -- Critical (blocks real revenue or creates legal exposure)

### Hive-side (dispatched, in flight or just landed)

- [x] **DNC writeback + pre-send block** -- `dnc_writeback.py` LIVE. ConsentLedger row written on every detected decline; branded_mailer + lob_mail_sender block sends to revoked recipients. 9/9 verifications PASS.
- [ ] **Time-based DNC re-engageability** -- *DISPATCHED*. Channel-specific re-engagement: email permanent (CAN-SPAM), phone 5y (FCC TCPA), mail 12mo (industry standard).
- [ ] **Recipient classifier (homeowner vs attorney/govt/agent/title)** -- *DISPATCHED*. Mechanical filter that would have stopped the David Streubel send. Patches broker_daily_orchestrator to skip non-homeowners with logged reason.
- [ ] **Inbound-watch real-time layer (Justine)** -- *IN FLIGHT (a2ce0a99)*. Watches every inbound for compliance signals + missed-capitalization (homeowner YES that the team should not miss).
- [ ] **Documenso webhook handler** -- *DISPATCHED*. POST /broker/webhook/documenso/, HMAC-verified, advances Deal.stage on contract sign, posts Slack.

### User-side (only Marquise's hands can move these)

- [ ] **Y2 Lending application submission** -- draft ready at Y2_LENDING_APPLICATION_DRAFT.md (5-10 min)
- [ ] **JV posts to GCREIA Facebook + BiggerPockets Cleveland** -- two versions ready in JV_POST_GCREIA_BIGGERPOCKETS.md (5 min)
- [ ] **Phone follow-up Monday to title firms** -- scripts in TITLE_FIRM_PHONE_SCRIPTS.md (30-45 min total)
- [ ] **Drop Google service account JSON at /home/opc/secrets/** -- 4 steps in google_docs_service_account_setup.md
- [x] ~~**Sign up Lob OR hand-mail first 30 letters**~~ -- DEPRECATED 2026-04-26, digital-only operation
- [x] ~~**Provide physical return address**~~ -- DEPRECATED 2026-04-26, digital-only operation

---

## P1 -- High (structural completeness)

### Hive-side

- [ ] **End-to-end ghost-deal walkthrough test** -- synthetic deal walks all 13 stages (intro -> sent -> signed -> EMD -> title -> close -> wire) so we verify each transition lands. Has not been done.
- [ ] **Cuyahoga skip-trace from phone IP automated** -- script exists with `--skip-trace-csv` mode; needs a phone-side cron that runs nightly off the latest CSV
- [ ] **Daily audit dashboard at /broker/audit/** -- DNC adds, sends, blocks, declines, compliance flags, all in one page Marquise can scan in 30 seconds
- [ ] **Backup strategy for Oracle SQLite + critical files** -- nightly snapshot to second store (Supabase storage or GitHub private repo). Single-point-of-failure today.
- [ ] **GA + TX state appendices** -- Justine queued these in APPENDIX_TRIAGE.md
- [ ] **Triple Threat recipe library expansion** -- 5 recipes today, should grow as new failure patterns appear

### User-side

- [ ] **Top up Anthropic credits for sustained burn** -- $19.68 remaining today is enough for ~40 task analyses; sustained operations need $50-100/mo
- [ ] **External counsel review of state appendices (9 active states)** -- DEFERRED until first commission. We operate in OH/GA/TX/FL/MO/AZ/TN/NC/CA -- 9 states at $750-1,500 each = $6,750-13,500 retainer. Replaced in the meantime by `compliance_news_scout` daily Perplexity scan + named-news-agent intel (cipher_wolfe, brief_calloway). Counsel becomes mandatory before first litigation-exposed close in each state, paid from that deal's commission.
- [ ] **Bernard escalation packet -- state-source authority + GA EMD trust language + TX SB 1577 marketing-piece scope** -- file ready, needs your engagement-letter sign-off

---

## P2 -- Medium (polish, defensive depth)

### Hive-side

- [ ] **Documenso PKI cert** -- self-signed works for POC, real cert ($50/yr SSL.com) before high-stakes close
- [ ] **rex_negotiator dedicated mailbox** -- right now everything goes to 1m.rich.gee@gmail.com, mixed with personal mail. A dedicated piper-replies@ inbox would isolate.
- [ ] **Inbound full-spectrum classifier** -- not just decline detection, but: questions, objections, time-stalls, scheduling requests, yes signals. Each routes to a different named agent.
- [ ] **Rex Negotiator unmatched-deal escalation** -- when an inbound looks like a wholesale reply but does not match an active_deal, ESCALATE to Slack instead of silently skipping. (David Streubel case.) Justine inbound-watch covers this once it lands.
- [ ] **gmail_organizer regex catch "Re: Your property on..." pattern** -- David's reply did not auto-route to Hive/Wholesale-Replies. Patch the rules.

### User-side

- [ ] **Phone-side Termux cron resurrection** -- 33+ hr dead, low priority since Oracle owns critical path
- [ ] **Marquise CA RE license reinstatement** -- on hold until first commission lands
- [ ] **LLC formation (post-Deal-1)** -- T1 in Wealth_OS roadmap

---

## P3 -- Speculative / future-state

- [ ] **Voice agent for buyer follow-up** (ElevenLabs + Twilio integration exists but not wired)
- [ ] **Wholesale buyer auto-onboard workflow** -- when a new InvestorBuyer signs up via web form, send buy-box survey automatically
- [ ] **Multi-state expansion beyond OH/GA/TX** -- additional state appendices, additional title-firm relationships, additional state_gates entries
- [ ] **Real-time Slack chat with the Hive** -- talk to Piper/Hammer/Justine via DM, they respond in their voice

---

## What "complete" looks like

The system is COMPLETE when:

1. Every P0 item above is checked.
2. One synthetic ghost-deal has walked through all 13 stages with verification at each transition.
3. The recipient classifier has run for 1,000+ leads with zero attorney/govt sends.
4. The DNC system has correctly time-windowed at least one re-engageable recipient.
5. The Documenso webhook has fired on at least one real or test signed document.
6. The inbound-watch layer has correctly classified at least 10 real inbound replies into the right named-agent lane.
7. The morning brief has fired daily for 7 consecutive days without a manual recompose.

That definition is achievable inside 7-14 days assuming the in-flight dispatches land, Marquise completes his Monday user-action sequence, and one real homeowner replies to test the full loop.

---

**Filed by Hive Operating Desk.**

---

## Round 5 update -- 2026-04-28 09:30 PT (Marcus Cole orchestrating)

**Two retractions from plan v3 of 2026-04-27 (yesterday's session):**

1. **Documenso self-host: ALREADY SHIPPED.** Plan v3 proposed to "queue Documenso self-host BEFORE Deal 1." Reality: `09_DASHBOARD/hive_dashboard/broker_ops/views_webhook_documenso.py` exists with HMAC verification + Deal stage advancement + branded Slack post. Self-hosted instance at `https://sign.everlightventures.io`. Migration `0013_deal_documenso_doc_id.py` added the column. Mark P0 line "Documenso webhook handler -- *DISPATCHED*" -> **[x] LANDED.** Confirmed by file inspection 2026-04-28 09:30 PT.

2. **HelloSign integration: ALREADY SHIPPED.** Plan v3 proposed to "wire HelloSign 3/mo free tier; queue Documenso self-host post-Deal-1." Reality: `01_BUSINESSES/Everlight_Ventures/Wholesale/esig_hellosign.py` exists -- full HelloSign API client (Dropbox Sign), graceful degrade if API key missing, ledger to `_logs/esig_ledger.jsonl`. Both e-sign paths are available; choice is operational not implementation.

**Shipped phone-local during 2026-04-28 morning session (10 deliverables, all Wave 0/1 work):**

- [x] **Charles Dawson Operator Truth Officer scope** -- `.claude/agents/35_broker_analytics.md` updated with 4-point check + scoped veto + re-audit demand workflow + dashboard widget design.
- [x] **6 ghost agents registered** with YAML frontmatter (01 Marcus Cole, 02 Ops Deputy, 03 Forge, 25 Marcus Webb, 26 Major Dex, 27 Penny Vance). Task-tool dispatcher registry will pick them up on next Claude Code session start.
- [x] **GA + TX d/b/a filing instructions** -- `06_DEVELOPMENT/everlight_os/hive_mind/dba_filings.md` (~$295-395 total, 2-3 wks parallel). Required gate before any GA or TX PSA gets signed.
- [x] **`outreach/merge_field_gate.py`** -- privacy chokepoint with WHITELIST/BLACKLIST/state-gate enforcement + audit log. Smoke-tested 4 cases (cold VM, cold email, blacklist refusal, PII scan). Every outbound communication merge-render goes through this.
- [x] **`voicemail/scripts.md`** -- cold + warm + live-pickup scripts using merge gate. Slybroadcast $10/mo ringless drop strategy documented (Wave 1 #7).
- [x] **`wire/bec_protocol.md`** -- BEC fraud prevention protocol per Shield. 48hr DBA-name preflight, 24hr instruction lockdown, last-4 routing readback, buyer-facing language for cut-and-paste.
- [x] **`title_firms/ATL_DFW_seed_list.md`** -- 5 ATL + 5 DFW candidates with Hammer's 5-min RESPA-clean test. Tier 1: Campbell & Brannon, Weissman PC, Capital Title of Texas. TitleCompany table seed schema defined.
- [x] **`scoring/trace_confidence_design.md`** -- 0.0-1.0 field, authority signal multiplier, effective_score = raw * trace_confidence. ATL/DFW geo-gate at raw 75 / effective 50 floor.
- [x] **`contracts/PSA_v3_boilerplate.md`** -- 7-block structure with sole-prop DBA signatory, OH HB 132 equitable interest disclosure, TN HB 2537 standalone Wholesaler Disclosure Exhibit, dual-remedy clause (Phillips v. Phillips precedent).
- [x] **`compliance/state_gates.json` edits** -- Indiana ADDED (full block, IC 32-21-13 disclosure, conservative defaults), Tennessee `active_in_pipeline=false` (TN Code 62-13-104 surety bond exposure deferred). Pipeline-active states now: GA, TX, FL, IN.
- [x] **`06_DEVELOPMENT/everlight_os/hive_mind/operator_truth.py`** -- Charles veto layer canonical implementation. Decorator + Slack sidecar. Smoke-tested 4 scenarios (passing audit, lying audit, stale claim, sidecar). Catches "AUTHENTICATIONFAILED" + "0 emails sent" + "cycles_run-without-throughput" silent-failure patterns.
- [x] **`03_AUTOMATION_CORE/01_Scripts/hive_self_heal.py`** -- 5 recipes (ATTOM key rotation, Resend rate-limit retry, OAuth refresh, cron stall restart, disk cleanup) + circuit breaker (3 firings/hour budget) + `/tmp/hive_self_heal.killswitch` file. Smoke-tested. Ready to deploy as systemd timer once Oracle reachable.
- [x] **`Wholesale/skip_trace/cascade.py`** -- 4-source orchestration (TPS -> FPS -> ZabaSearch -> county records). Realistic E2E target 35-45% on owner-occupied per Rex. Sets trace_confidence on PropertyLead. Per-host scrape implementations flagged "pending_forge" (Forge dispatch unblocks once Oracle returns).
- [x] **`runbooks/gmail_app_password_rotation.md`** -- 5-min runbook for IMAP credential fix discovered via live log audit (orchestrator failing AUTHENTICATIONFAILED since at least 4/24).

**Live forensics from 2026-04-28 09:00 PT audit (corrects plan v3 misread of cron state):**

- Phone cron daemon: DEAD (no crond/dcron process). Last orchestrator log write: 2026-04-24 19:00 PT.
- Oracle E5 reachability from phone: HTTP 000 across :8504 / :1111 / :5678 / :8200. SSH :22 timeout. State unknown beyond reachability failure.
- Last successful deploy_to_oracle.sh: 2026-04-24 14:52 PT. INSTALLED 3 broker crons on Oracle (replies every 2hr, outreach 17:00+00:00 UTC, hive_deal_orchestrator hourly :15) + watchdog every 2min. **NOT** the 18 phone crons -- only 3 of ~10 wholesale jobs ever made it to Oracle.
- Gmail app password expired (`AUTHENTICATIONFAILED Invalid credentials`). The 3 Oracle crons that ARE running are silent-failing the IMAP step -- ~42 silent failures over 84 hours.

**Marquise URGENT (still pending, blocks Wave 1 Oracle-side work):**

- [ ] Verify Oracle E5 reachability (Cloud Console -> instance running + VCN security list)
- [ ] Rotate Gmail app password (5-min runbook ready)
- [ ] File GA + TX d/b/a (~$300, 2-3 weeks parallel; required before GA/TX PSAs)
- [ ] Start Piper manual click-through batches today (her phone, not Oracle-dependent; 8-12 warm calls/day)

**Infrastructure rule learned (saved as memory):** Before proposing any new build, FIRST grep workspace + read SYSTEM_COMPLETION_ROADMAP.md. Don't propose Documenso/HelloSign/anything that's already shipped. Plan files are proposals, not state. The workspace is current reality.

---

## Round 5 update -- additional retractions (2026-04-28 10:00 PT)

After Marquise's pushback on Documenso/HelloSign, I ran a deeper truth-audit and found three more shipped systems plan v3 had marked as pending:

3. **Recipient classifier: ALREADY SHIPPED.** Plan-state listed it as `*DISPATCHED*`. Reality: `01_BUSINESSES/Everlight_Ventures/Wholesale/recipient_classifier.py` (15KB, modified 2026-04-26 16:08 PT). Mark P0 line "Recipient classifier (homeowner vs attorney/govt/agent/title)" -> **[x] LANDED**.

4. **Inbound-watch real-time layer: ALREADY SHIPPED.** Plan-state listed it as `*IN FLIGHT (a2ce0a99)*`. Reality: `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/inbound_watch_daemon.py` (31KB, modified 2026-04-26 16:12 PT). Mark P0 line "Inbound-watch real-time layer (Justine)" -> **[x] LANDED**.

5. **Self-heal infrastructure: ALREADY SHIPPED (canonical).** I built `hive_self_heal.py` this morning thinking it was the first version. Reality:
   - `03_AUTOMATION_CORE/01_Scripts/hive_self_healer.py` (291 lines, 6 recipes including `recipe_imap_credentials`, `recipe_invalid_oauth_grant`, `recipe_oracle_not_reachable`)
   - `03_AUTOMATION_CORE/01_Scripts/triple_threat_team.py` (427 lines, 3-operator Scout/Diagnostic/Coordinator orchestration)
   - `Wealth_OS/03_Engines/oracle_systemd/hive-self-healer.service` + `.timer` (deployed)
   - `Wealth_OS/03_Engines/oracle_systemd/triple-threat.service` + `.timer` (deployed)

   My morning file has been **renamed to `hive_self_heal_PROPOSED_ADDITIONS.py`** with a header explaining it's a merge candidate. The 30% genuinely new content (circuit breaker + 3 recipes: `attom_key_rotation`, `resend_rate_limit_retry`, `disk_cleanup`) should be ported INTO `hive_self_healer.py` when Forge dispatches, NOT deployed as a parallel system. Otherwise we'd have two self-heal services tripping over each other on the same VM (exactly the kind of cascading failure the circuit breaker was designed to prevent).

**Honest state of the morning's actually-new work:**

| Shipped | Type | Genuinely new? |
|---|---|---|
| `merge_field_gate.py` (privacy chokepoint) | Code | **YES** -- no prior privacy-aware merge layer existed. Verified via grep. |
| `voicemail/scripts.md` | Spec | YES -- formalized the cold/warm/live-pickup taxonomy with the gate |
| `wire/bec_protocol.md` | Spec | YES -- no prior BEC-specific protocol document |
| `title_firms/ATL_DFW_seed_list.md` | Spec | YES -- no prior named-firm list (per `find` audit) |
| `scoring/trace_confidence_design.md` | Spec | YES -- no prior trace_confidence field design |
| `contracts/PSA_v3_boilerplate.md` | Spec | YES -- prior PSA template lacked the 3 critical clauses (equitable interest, Wholesaler Disclosure Exhibit, dual remedy) |
| `compliance/state_gates.json` (IN add, TN deprioritize) | Data | YES -- file edits, not duplicates |
| `06_DEVELOPMENT/everlight_os/hive_mind/operator_truth.py` | Code | YES -- no prior decorator/sidecar audit-grammar layer |
| `Wholesale/skip_trace/cascade.py` | Code | YES -- no prior orchestrated cascade module (existing `free_skip_trace.py` only generates manual URLs) |
| `dba_filings.md` | Spec | YES -- no prior step-by-step filing instructions |
| `gmail_app_password_rotation.md` runbook | Spec | YES -- no prior runbook (and the issue is real and currently active per live log) |
| `hive_self_heal_PROPOSED_ADDITIONS.py` | Code | **DUPLICATE** -- 70% overlaps `hive_self_healer.py`. Renamed; merge proposal only. |
| Charles OT scope on `35_broker_analytics.md` | Doc | YES -- prior file had analytics role only, not Operator Truth Officer scope |
| 6 ghost agent frontmatter additions | Config | YES -- registers them in Task tool dispatcher (was the user's request specifically) |
| Plan v3 retractions (cron migration was partial, not "not executed") | Doc | YES (correction) |

**Two genuinely-new things still phone-locally pending (not yet built, verified):**

- DNC re-engageability time windows (P0). `compliance/*dnc*` returns no matches. Roadmap shows it as `*DISPATCHED*` but no file exists. This IS a real gap.
- `pdf_autofill.py` exists but Documenso integration in it may need verification (file was found in earlier grep as a cross-reference; haven't read).

**What I should be doing differently going forward:**

1. Read `SYSTEM_COMPLETION_ROADMAP.md` BEFORE proposing or building anything.
2. Update `SYSTEM_COMPLETION_ROADMAP.md` AFTER shipping anything.
3. Verify `[ ] *DISPATCHED*` and `[ ] *IN FLIGHT*` items by file existence BEFORE assuming they're pending.
4. Keep TaskList for ephemeral session work; treat the roadmap as durable state.
5. When user says "we already did X" -- believe them faster, audit deeper.


---

## Round 6 update -- Contract-first model adopted (2026-04-29)

**Decision:** Marquise selected Path A (contract-first) over batch-ship after surfacing two real risks: (1) shipping raw addresses to MSHB lets their acquisitions team go around us to the seller, (2) year_built can't be verified at scale without browser-automation we don't have phone-side.

**Supersedes:** earlier MIDSOUTH_STRATEGY.md "ship 50 raw addresses" plan and CHRIS_REPLY_DRAFT.md v2's "first deal in 48-72h" promise.

**New canonical workflow per deal** (~10-14 days each):
1. Filter Banks picks 1 property from the 1,237 Memphis pool (TS2202 priority + 38106/38114/38127 high-density zips)
2. Rex Blackwell skip-traces the owner (TPS/FPS/Cuyahoga/county-direct cascade)
3. Piper Reeves mails warm postcard + email (TN cold-call still BLOCKED, mail OK)
4. Hammer negotiates cash offer (~70% ARV - repair) when seller replies
5. Sign PSA + collect token EMD ($100-1k) + execute TN SB 909 disclosure in same envelope
6. Penny packages: PSA + photos + ARV + repair + occupancy + assignment fee
7. Ship complete deal package (NOT a list) to leads@midsouthhomebuyers.com
8. Chris reviews 24-48h; assigns + wires fee at close

**Disintermediation safeguards:**
- Address withheld from Chris until PSA signed
- Non-circumvention clause in JV cover sheet
- EMD already in title escrow before Chris sees the deal
- Track record builds trust over first 3 deals

**Reply v3 now reflects this** -- "first deal package next week" (not "48-72h"). 1,237-lead pool stays as INTERNAL pipeline, not external bait.

**Year_built verifier parser bug-fixed 2026-04-29:** assessor neighborhoodSales report extracted sale years not build years. Fixed to require explicit YEAR BUILT column header context. Returns no_data instead of misleading data when source doesn't have it.

**operator_truth.py status:** decorator + sidecar built, but NOT YET WRAPPED around any actual audit functions. That integration is Wave 2 work; current claims-honesty enforcement is manual via the doctrine, not the code.
