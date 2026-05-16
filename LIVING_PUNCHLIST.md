# EVERLIGHT VENTURES — LIVING PUNCH LIST

**Last updated:** 2026-05-15 03:15 PT
**Owner:** Rich Gee
**Operating model:** Macro lane (platform/empire vision) runs in parallel via Hive. Micro lane (close Deal 1 with Chris) is the daily focus. Items in CRITICAL PATH are the only ones that gate today.
**Doctrine:** This list is NEVER done. We complete items, we add new items, the list grows. Always.

**Status legend:**
- ☐ Pending
- ◐ In progress
- ☑ Done
- 🔥 Critical / hot path
- ⏸ Deferred (waiting on dependency)
- ⚠ Blocked
- 🆕 Added this session

---

## A. MICRO — Close Deal 1 With Chris (this week)

The only lane that matters today.

1. ☑ Patch `parse_assessor_mhtml.py` to extract owner mailing address + 6 derived signals (`out_of_state`, `absentee`, `is_llc_owner`, `is_long_term_owner`, `years_owned`, `distress_signals` + `pitch_hooks`). Completed 2026-05-15.
2. ☑ Re-parse 30 assessor MHTs in `Wholesale/owner_downloads/archive/`. Result: 114 JSONs, 61 with mailing addresses (was 0), 28 HIGH priority. Completed 2026-05-15.
3. ☑ Generate `SELLER_EMAILS_READY_TO_FIRE_v2.md` with 110 Chris-eligible candidates ranked across 3 tiers. Completed 2026-05-15.
4. ☑ Rotate Gmail App Password. Update `.env` + crontab. Verify IMAP login. Completed 2026-05-15.
5. ⚠ **REVERTED -- DO NOT TOUCH WITHOUT RICH'S CANONICAL ROSTER:** I flipped Piper → Marquise based on a memory rule, Rich corrected me ("Piper is my assistant"), pushed revert as commit 488c619d. Sender stays `piper@everlightventures.io`. New item #61 tracks the canonical roster ask.
6. 🔥☐ **Skip-trace enrichment on Tier 1 + Tier 2 leads** (17 highest-signal owners) for email + phone. Cascade.py exists but per-host scrape impl pending. Decision: run with current cascade fallback OR Phil pattern-guess + MX verification (the path that produced Mikal + Trezden 4/29).
7. 🔥☐ **Fire first batch of outreach** — top 8 Tier 1 out-of-state owners (HOWARD EDDIE ESTATE, LEGGETT BENNIE, STOKES, KEMP, SPILMANN, +3) from `marquise@everlightventures.io` via `branded_mailer.send_branded_email(category="vip_reply")`. Marquise authors, Rich greenlights.
8. ☐ Verify rex_negotiator can auto-reply with arc step M3 (counter-offer) when seller responds. End-to-end test on a non-live deal first.
9. ☐ Documenso self-host (`sign.everlightventures.io`) reachability test. Send a test PSA envelope, verify HMAC webhook fires, verify Deal.stage advances to `psa_signed`.
10. ☐ Chris pitch template — once a PSA is signed, the auto-pitch to chris@midsouthhomebuyers.com should fire. Verify template, verify trigger.
11. ☐ Mid-South Title coordination kickoff — Marvin's call. Letterhead, contact, "we are sending you a deal."
12. ☐ Close + wire + assignment fee tracking. Hive logger record event, Slack `#wholesale-deals` celebration.

---

## B. MACRO — Open Deal Platform (parallel build, post-Deal-1 unlocks gates)

This builds in the background while micro closes the first deal. Hive owns delivery.

13. ☑ `EMD_LOCK_POLICY.md` — 3-tier ladder (Browser / Buyer-Funds-Verified / Inner Circle) + Chris auto-comp + Stripe flow per tier. Completed 2026-05-15.
14. ☑ `BUYER_DISCLOSURE_LOCK_FEE.md` — TN governing law, principal-buyer exemption cite, refund mechanics per tier. Completed 2026-05-15.
15. ☑ `OPEN_DEAL_BUILD_SPEC.md` — 12-14 day Hive sprint plan. Completed 2026-05-15.
16. ☑ `REINVENTION_THESIS.md` — Apple Store of off-market RE positioning, unfair-advantage stack named. Completed 2026-05-15.
17. ☑ `VOLUME_PLAN_AND_DAILY_LIMITS.md` — scale-first, multi-state day 1, 30-day target $20-30k/mo run rate. Completed 2026-05-15.
18. ☑ `LEGAL_PATCHES_2026-05-15.md` — synthesized 5-agent legal audit. 12 patches applied inline, 3 post-Deal-1 unlocks. Completed 2026-05-15.
19. ⏸☐ Hive dispatch the 12-14 day build sprint (62 frontend architect, 67 backend, 64 component, 74 growth, 68 devops in parallel). DEFERRED until Rich greenlights — macro/micro split says micro first.
20. ⏸☐ Form **Everlight Ventures Wholesale Acquisitions, LLC** (NV parent + TN sub + state subs). $300 NV + $50/yr agent. Funded by Deal 1. POST-DEAL-1 UNLOCK.
21. ⏸☐ Mid-South Title Coordination Letter signature. Heck Aurelio drafts, Marvin drives signature. RESPA Section 8 paper trail. POST-DEAL-1 UNLOCK.
22. ⏸☐ Theo Briggs TREC public-platform memo. Required before Verified + IC tier go public. Browser tier ships behind signup-wall in the meantime. POST-DEAL-1 UNLOCK.

---

## C. INFRASTRUCTURE — Watchdogs, Self-Awareness, Verified-Running State

🆕 New category Rich named this session. Every autonomous service needs a watchdog. Every watchdog needs its own watchdog OR a heartbeat to Slack that you'll notice when it stops.

23. ☑ Auto-resolver for sync conflicts: `sync_conflict_resolver.sh` + `install_acemagician_triggers.sh`. udev rule on Z Fold 7 USB plug, systemd timer hourly fallback. Completed 2026-05-15.
24. 🔥☐ **Watchdog for the broker orchestrator** — when last successful run > N hours old, post to Slack `#hive-alerts` AND attempt restart. Self-aware so the 21-day-dead-cron silent failure can never happen again.
25. ☐ **Watchdog-of-watchdog** — cron on a SEPARATE host (Oracle when available, AceMagician otherwise) that pings the primary watchdog and alerts if IT stops. Two-level redundancy.
26. ☐ **Heartbeat dashboard** — every named service writes a "last alive" timestamp to a central file (Supabase row OR `_state/heartbeats.json`). One page that shows red/green for every cron + daemon. fastfetch banner-style at shell login.
27. ☐ **`hive_self_heal.py` deploy** — already written per memory, 5 recipes (ATTOM key rotation, Resend rate-limit retry, OAuth refresh, cron stall restart, disk cleanup) + circuit breaker. Needs systemd timer install once Oracle reachable.
28. ☐ **Operator Truth dashboard** — Charles Dawson veto layer materialized as a `:8504/audit/` widget that compares claimed work to verified-running state. Per `operator_truth.py` already written.

---

## D. AUTONOMOUS LEAD FLOW — 100 New Leads / Day

🆕 Rich's vision for the cycle: assessor list → scrape → parse → enrich → outreach, all autonomous, 100 fresh leads daily without manual MHT downloads.

29. ◐ Current state: Rich manually opens browser, searches assessormelvinburgess.com, saves MHTs, drops in `owner_downloads/archive/`. Parser then turns MHTs into JSONs. **Bottleneck = the manual browser step.**
30. ☐ **Hermes browser harness** (per memory `hermes_browser_outreach`) — self-improving browser-use agent on Hostinger VPS. Hostinger is the existing budget host. Run as a daily cron firing N parcel lookups against assessormelvinburgess.com.
31. ☐ **Phone-side alternative:** Termux-side `playwright` or `selenium` headed-browser run on a daily cron that does the assessor scraping locally. Trade-off: phone resources + Android RAM. Cleaner: Oracle or AceMagician runs it.
32. ☐ **Source list of parcels to lookup** — the autonomous scraper needs a target list per day (tax-delinquent rolls, code violations, FSBO, absentee owner pools). Source list pipeline needs its own scraper. Memory `reference_tn_lead_pipeline_sources` names some sources.
33. ☐ **Output pipeline** — scraper writes MHT to `owner_downloads/inbox/`, parser cron auto-processes inbox, enrichment cron skip-traces new mailing addresses, branded_mailer queue picks up new outreach candidates. Full chain.
34. ☐ **Daily metrics**: leads added, leads enriched, outreach sent, replies received, deals advanced. Branded HTML report at 5 AM PT to Marquise + Rich. Per existing `branded_calloway` agent.
35. ☐ **Throttle awareness** — assessor site has rate limits. Browser harness needs polite-crawl discipline (delays, random user-agent, cooldown on 429).

---

## E. COMMS BRIDGE — Reply → Auto-Response Loop Verification

36. ☑ IMAP detection alive — rex_negotiator cron every 2 min, password rotated. Completed 2026-05-15.
37. 🔥☐ End-to-end test of rex_negotiator's auto-reply: send a test seller email, verify rex parses it, verify it drafts an M3 counter, verify it sends via Resend without human-in-loop, OR verify it pings Slack when stuck. Confirm the bridge works before any real send.
38. ☐ Slack notif config for `#wholesale-deals` channel — verify the channel ID `C0ANLLV8JAC` is correct and the bot has post permission. Tests the "Rex pings you" path.
39. ☐ Documenso webhook smoke test — fire a synthetic PSA, verify `/broker/webhook/documenso/` advances Deal.stage and Slack-posts.
40. ☐ Inbound classifier (per memory `recipient_classifier`) — verify it's running and accurately distinguishing seller-yes / seller-no / question / objection. Reject any David-Streubel-style misroute.

---

## F. PERSONAL / OPS

41. ⚠☐ **ElevenLabs $22 subscription failed twice on Visa 4582** (email today). Decision: cancel or update payment. Real money, your call.
42. 🆕☐ Send-domain deliverability — verify SPF / DKIM / DMARC on `everlightventures.io` for `marquise@`, `piper@`, `rich@`. Without proper records, cold outreach lands in spam. Free fix via Resend dashboard.
43. 🆕☐ Sender warmup — new aliases (marquise@) need slow-warm send volume (5/day -> 20/day -> 50/day over 2 weeks) or domain reputation tanks. Don't blast 75 cold sends on day 1.
44. 🆕☐ Bulk-archive 1.6 GB of historical sync-conflict backlog (May 8 + May 13 + May 14). Manifest pass first per the >100 MB rule. Reversible move to `08_BACKUPS/sync_conflicts_archive_2026-05-15/`.

---

## G. BRAND + QUALITY BAR

Per `REINVENTION_THESIS.md`. Apple-grade always, MVP-grade never.

45. ☐ Branded postcard template — wait, scratch that. **No postcards.** Removing this item entirely. Channel doctrine = digital only.
46. ☐ `everlightventures.io` audit — Lighthouse 95+? Mobile responsive? Brand-consistent? Currently a Cloudflare Pages site, last verified state unknown.
47. ☐ Email template gold-on-dark visual audit — branded_mailer output rendered on Gmail, Apple Mail, Outlook. All three look correct. Screenshot pass.
48. ☐ Slack post visual audit — branded_slack Block Kit rendering, all 6 categories (report, alert, deal, intel, ops, system).
49. ☐ DocuSign / Documenso envelope branding — gold accent bar, Playfair Display, Inter body, agent attribution footer.
49a. ☐ **Moltbook.com public AI-network presence** (MACRO, post-Deal-1 unlock unless Rich greenlights early). Wave 1 of 8 personas (Lucrex, Marcus Cole, Cipher Wolfe, Bull Archer, Helix Patel, Nova Ling, Pitch Adler, Solomon Vale) staged in dry-run 2026-05-15. Bios passed `moltbook_confidentiality_gate.py`. **Blockers before live**: (a) `@EverlightVentures` X handle created + handle written to `_state/moltbook/x_handle.txt`, (b) operator approval of bios as-shown, (c) verification tweets per persona once registered. Helper: `03_AUTOMATION_CORE/01_Scripts/moltbook/moltbook_register.py --live --confirm`.

---

## H. PUSH HYGIENE

50. ☑ **Push today's work to a side branch FIRST** per doctrine. Pushed to `parser-resolver-punchlist-2026-05-15` (commits a07235a0 + 82c58785) on 2026-05-15. Awaiting prod-branch promotion after review.
51. ☐ Git status currently shows 626 modified/untracked files. Selective commit only — don't push the entire pending set. Today's targeted scope: parser, scripts, specs, memory.

---

## I. SCALE & FUTURE (Q3-Q4 2026)

52. ☐ Multi-state Verified + IC tier unlock as state-buddy audits clear (GA, TX, FL, AZ → OH, MO, NC).
53. ☐ Affiliate / referral program for Inner Circle members. $50 credit per Verified buyer referral.
54. ☐ Stripe Identity integration for auto-KYC at the $99 Verified upgrade flow.
55. ☐ Treasury OFAC SDN nightly cron + reconciliation ledger.
56. ☐ Cal. Civ. Code 1671(b) liquidated-damages analysis before CA can join paid tiers.
57. ☐ Privacy policy publication at `/legal/privacy` per Priya audit.
58. ☐ KYC retention runbook (3yr / 1yr ID images, TX CUBI alignment).
59. ☐ Cross-channel STOP revocation (FCC 24-24) — STOP on SMS revokes email too.
60. ☐ Institutional Inner Circle++ tier (REIT, hedge fund REI desk) at higher Lock Fees.

---

## J. ROSTER + CLARIFICATIONS

61. ☑ **Canonical team roster v2 locked.** FOUR external personas: Piper Reeves (outreach), Henry Hammond (negotiation), Marvin Cohen (closing), Vaughn Sterling (senior partner). Back-of-house: Marquise Reed (Memphis intel), Cupid, Filter Banks, Chart, Cash. Counterparties: Chris @ Mid-South Homebuyers, Mid-South Title. Supersedes prior single-voice rule + agent_alias_send_rule. 2026-05-15.

62. 🆕🔥☐ **Set up the 3 new email aliases on `everlightventures.io`**: `henry@`, `marvin@`, `vaughn@`. SPF, DKIM, DMARC records via Resend dashboard. Then 2-week staggered warmup (5/day → 20/day → 50/day per alias) so deliverability holds.

63. ☑ **Write `WHOLESALE_PERSONA_TEMPLATES.md`** — all 4 personas profiled with zodiac, backstory, voice, OSINT interpretive lens, signature, handoff phrasing, don't-say list. Saved 2026-05-15 to `Broker_OS/wholesale_agent/WHOLESALE_PERSONA_TEMPLATES.md`.

64. 🆕🔥☐ **Refactor `rex_negotiator.py` for per-stage sender selection.** Stage detection (outreach / negotiation / closing / partner-rescue) drives which persona's alias + Claude prompt + signature gets used. Explicit handoff message inserted at each transition.

65. 🆕☐ **Branded `branded_mailer.py` voice routing**: every send specifies persona, mailer picks alias + prompt + signature. Code change ~30 LOC.

66. 🆕☐ **Slack persona channels**: `#piper-outreach`, `#henry-negotiation`, `#marvin-closing`, `#vaughn-partner` so internal handoff is visible. (Optional polish, not blocking.)

67. 🆕☐ **Test the full handoff chain end-to-end** with a synthetic seller email before any real send. Verify: Piper opens, Henry takes over on reply, handoff phrasing renders correctly, From: line + signature flip per persona.

---

## K. OSINT & PERSONALIZATION ENGINE

🆕 New section 2026-05-15. Result of the 3-agent OSINT dispatch (everlight_researcher / 55_competitive_intel / legal_priya_bhattacharya). Full synthesis at `09_DASHBOARD/reports/osint_audit_and_roadmap_2026-05-15.html`. Source files in `_state/audit_log/`. Doctrine: Google-grade personalization, signal invisible, output relevant. Apple-Store-of-wholesaling quality bar.

68. ☑ **Parser patched with `macro_context` slots** (`parse_assessor_mhtml.py` ~line 360). Forward-compatible. 7 enrichment slots (weather/earthquake/wildfire/news/infrastructure + status + ts). Completed 2026-05-15.

69. ☑ **OSINT audit + roadmap synthesized** &mdash; 3-agent dispatch (Bombal methodology, tool teardown, compliance lines). HTML at `09_DASHBOARD/reports/osint_audit_and_roadmap_2026-05-15.html`. Source markdowns in `_state/audit_log/`. Completed 2026-05-15.

70. 🔥☑ **Built `email_discovery.py`** &mdash; the bottleneck closer. Person + LLC name → pattern permutation across major providers, MX records check, EmailRep reputation + HIBP existence cross-check, ranked candidates with confidence_score 0-100. Hunter Domain Search wired for paid path. Top-N candidates flow to pitch_tailor. Completed 2026-05-15.

71. ☐ FEC API key swap &mdash; replace `DEMO_KEY` with real key (60-second free fix). Currently 429ing in live_log. Register at api.open.fec.gov/developers.

72. ☑ **Built `obituary_estate.py`** &mdash; estate/trust detection, Legacy.com obituary scrape, executor + family extraction, pitch_hooks synthesis (internal-only, never quoted in outbound per creep-line doctrine). Targets the 28 estate-flagged parcels. Companion to public_records.py's Find-A-Grave. Completed 2026-05-15.

73. ☑ **Built `username_enrichment.py`** &mdash; replaces HEAD-only social_recon shim. Network-first fetch of WhatsMyName JSON catalog (500+ platforms) per the new HARD LAW; 30-platform hardcoded fallback. Multi-handle sweep with probe budget. Logs `platform_source` so operator sees live vs fallback path. Completed 2026-05-15.

74. ☑ **Built `reverse_whois.py`** &mdash; WHOXY API (paid path, env-keyed) + ViewDNS scrape (free fallback). LLC owner → all domains they've registered, with creation date + registrar. High signal for institutional-investor owners. Completed 2026-05-15.

75. ☐ Build `local_news_archive.py` (Kagi + Newspapers.com) &mdash; hyper-local personalization hooks. Already partially covered by public_records.py's Google News extractor + macro_enrichment.py's GDELT puller. Tighten only if explicit-county news is too thin.

76. ☑ **Built `wayback_contact_extract.py`** &mdash; Wayback CDX API for historical snapshots, regex email + phone extraction from oldest 3 snapshots, filters out generic locals + Wayback toolbar. Skip-trace fallback for scrubbed LLC sites. Completed 2026-05-15.

77. ☐ Beef up `property_records.py` from 32-line stub → RentCast + Zillow + Redfin actual implementation. Unblocks Chris-side valuation talk track. M effort.

78. ☑ **Built `macro_enrichment.py`** &mdash; standalone enrichment puller at `Wholesale/seller_intel/macro_enrichment.py`. Walks parsed/*.json, queries NOAA NWS alerts + USGS earthquakes (Shelby/DFW centroid) + InciWeb wildfires + GDELT county news; fills parser's `macro_context` dict; appends pitch_hooks from `macro_pitch_copy.yaml` on hits; recomputes outreach_priority. 7-day TTL (re-enrich on stale). stdlib-only HTTP (cron-friendly). Completed 2026-05-15.

79. ☐ Fix `esign_server.py` hardcoded dev-secret fallback &mdash; security risk before any live PSA send. Anyone with source can forge sign tokens.

80. ☐ Add 10 new `compliance_log.py` event types per Priya memo (hash-chained, doctrine matches `deal_execution_log.py`). Events: license-plate-block, FCRA-purpose-check, social-platform-scope-check, breach-data-block, etc.

81. ☐ Add per-state opt-out footer rendering to `branded_mailer.py`. TX TDPSA (Bus & Com 541) and NV NRS 603A are now active comprehensive privacy laws &mdash; we trigger them. Plain-English opt-out + privacy notice link per state.

82. ⏸☐ **Buyer-side criminal-background flow** for Inner Circle Verified tier &mdash; CONDITIONAL YES under FCRA 1681b(a)(3)(F)(ii). Route through Stripe Identity, add consent checkbox + adverse-action notice template. **POST-DEAL-1 unlock.**

83. ☑ **Hard-skip list codified in `legal_scope.py`** &mdash; 8 new OUT_OF_SCOPE entries added: license plate lookup, voter ID brute, breach CSV enrichment, WiFi geolocation, form brute force, login-walled scraping, HexStrike external, FCRA seller-side. Each with statutory citation, examples, and the carve-out (where one exists). Doctrine binding on all future agents. Completed 2026-05-15.

84. ☐ Execute the 5 pre-existing OSINT work orders from `TODO_AGENTS.md` (sitting since 2026-05-12): SpiderFoot install (WO1), HexStrike eval in sandbox VM (WO2), Fabric 5-pattern port (WO3), Google Dorking for prospect discovery (WO4), self-OSINT defensive audit (WO5).

85. 🆕☑ **Built `macro_pitch_copy.yaml`** &mdash; pitch phrasing template at `Wholesale/seller_intel/macro_pitch_copy.yaml`. 5 macro categories x 1-3 personas (Piper, Marquise, Henry) x 3-5 draft phrasings each. All marked DRAFT until Rich + persona team overwrites with conversion-tested copy. Creep-line guardrails block embedded in file. macro_enrichment.py reads from here. Completed 2026-05-15.

86. 🆕☑ **Registered 5 new investigators in `osint_api/investigators/__init__.py`** &mdash; email_discovery, obituary_estate, reverse_whois, username_enrichment, wayback_contact_extract now part of ALL[] list and for_target() routing. Completed 2026-05-15.

87. 🆕☑ **End-to-end test PASSED** &mdash; ran `_state/test_osint_validation_20260515.py`. **Phase 1 (macro_enrichment, 3 parcels):** 3/3 ran, 1 real macro hit on parcel 015011__00011 (GDELT news_catalyst: "Shelby/Davidson Tennessee counties..."), pitch_hook auto-appended from yaml. **Phase 2 (email_discovery, 3 Tier-1 leads):** 3/3 ok=True after threshold fix (25/100 cold-prospect ceiling, MX confirmed), ranked candidates ready: eddie.howard@gmail.com / .yahoo / .outlook for HOWARD EDDIE; bennie.leggett.* for LEGGETT BENNIE; mary.stokes.* for STOKES MARY. **obituary_estate verified** on HOWARD EDDIE ESTATE: correctly normalizes "Eddie Howard," produces internal pitch hooks even when Legacy.com scrape returns 0. Pipeline is firable. Results JSON at `_state/test_osint_validation_results_20260515.json`. Completed 2026-05-15.

88. ⏸☐ ~~HIBP API key~~ &mdash; DEFERRED post-Deal-1. Rich called the macro drift 2026-05-15: building our own equivalent requires breach-corpus ingestion which is HARD-SKIP per `legal_scope.OUT_OF_SCOPE["breach_csv_enrichment"]`. We don't need it. Bounce-watch is the free-path substitute. Revisit only if Deal-2+ outreach volume exposes a real ceiling problem.

89. ⏸☐ ~~Hunter API key~~ &mdash; DEFERRED post-Deal-1. Same reasoning as #88. Free-path = sender uses owner_name pattern guesses + bounce-watch + iterate. Hunter buys speed at volume; pre-Deal-1 we're sending tens, not thousands.

90. 🆕☐ Install `dnspython` (`pip install dnspython`) for proper MX record validation in `email_discovery.py`. **FREE, 30 seconds.** Currently falls back to socket A-record (approximate). Do this before the bounce test.

91. 🔥☐ **THE single next move.** Real-network bounce test &mdash; one email from `marquise@everlightventures.io` to `eddie.howard@gmail.com` (top candidate, HOWARD EDDIE ESTATE, TX). Via `branded_mailer.send_branded_email(category="vip_reply")`. Either outcome teaches: delivery = first real seller email captured by our pipeline; bounce = iterate to `.yahoo.com`. This is what closes Deal 1.

---

## WINS LOG (this session, 2026-05-15)

- Fixed assessor parser → 0 mailing addresses → 61.
- 28 HIGH-priority leads ranked, top 8 are out-of-state.
- Identified Bennie Leggett (CA), Howard Eddie Estate (TX) as the strongest first-shots.
- IMAP password rotated, broker reply detection back online after 21 days dead.
- Read 4 unseen Gmail messages — zero seller replies (window was outbound-dead too).
- Sync conflict auto-resolver shipped + USB-plug trigger designed.
- 5-agent legal audit completed, all FIX REQUIRED, no BLOCKERS, 12 patches applied inline.
- Caught and corrected: Chris ≠ title company; LLC name = Wholesale Acquisitions LLC; digital-only doctrine; macro/micro split.
- Memory grew by 14+ HARD LAW entries.
- Fixed rex_negotiator sender alias Piper → Marquise (item #5, commit 82c58785).
- Pushed side branch `parser-resolver-punchlist-2026-05-15` per doctrine (item #50, commits a07235a0 + 82c58785).
- This Punch List was born.
- 3-agent OSINT dispatch (everlight_researcher + 55_competitive_intel + legal_priya_bhattacharya) shipped 3 source memos in `_state/audit_log/` + 1 synthesized HTML deliverable at `09_DASHBOARD/reports/osint_audit_and_roadmap_2026-05-15.html`. Discovered the real bottleneck: 114 parsed parcels → 61 mailing → 0 emails. Email discovery is the highest single-ROI build on the entire list.
- Parser shipped `macro_context` slots (weather/quake/wildfire/news/infrastructure) ready for the enrichment puller. Forward-compatible.
- Compliance lines drawn: license plates HARD NO (DPPA), criminal HARD NO seller / CONDITIONAL YES buyer (FCRA), social media CONDITIONAL YES (hiQ v. LinkedIn). Hard skip list codified.
- Section K born in punchlist (16 new items, #68-#84).
- 5 new investigators built and registered: `email_discovery.py` (the bottleneck closer), `obituary_estate.py` (estate-flagged parcel synthesis), `username_enrichment.py` (replaces HEAD-only social_recon, network-first WhatsMyName fetch), `reverse_whois.py` (WHOXY + ViewDNS fallback), `wayback_contact_extract.py` (Wayback CDX skip-trace fallback). Registered in `osint_api/investigators/__init__.py`.
- `macro_enrichment.py` shipped &mdash; the puller that fills parser's macro_context slots from NOAA + USGS + InciWeb + GDELT. stdlib-only HTTP, cron-friendly.
- `macro_pitch_copy.yaml` shipped with DRAFT phrasings per persona; creep-line guardrails embedded; Rich + persona team to overwrite drafts with conversion-tested copy.
- 8 hard-skip OSINT categories codified in `legal_scope.py` OUT_OF_SCOPE (license plates, voter brute, breach CSV, WiFi geo, form brute, login-walled scraping, HexStrike external, FCRA seller-side). Each with statutory cite.
- New HARD LAW saved: network-first / no-clone-required. Builds default to runtime fetch from GitHub raw URLs + public APIs. Phone-on = default state. Modifies `reuse_existing_infra_first` to include upstream public catalogs.
- Validation harness ran live against real data: macro_enrichment caught 1 real GDELT news_catalyst on parcel 015011__00011 ("Shelby/Davidson Tennessee counties..."), pitch_hook auto-appended from yaml; email_discovery returned ranked top candidates for all 3 Tier-1 leads (eddie.howard@gmail|yahoo|outlook, etc.); obituary_estate fires internal pitch hooks for estate-flagged owners. 2 real bugs caught and fixed in-flight: (a) email_discovery threshold lowered from 40 to 25 (cold-prospect MX-only ceiling), (b) GDELT empty-body now logged as `_source_status.gdelt` degraded instead of silent zero. Test harness at `_state/test_osint_validation_20260515.py`, JSON results at `_state/test_osint_validation_results_20260515.json`.

---

## HOW TO USE THIS LIST

- I update this file at the end of every session. Status icons change, new items get 🆕, completed items get ☑ + date.
- The numbers ARE stable references. When we talk about item #6 next week, you and I both know what it is.
- Items can move between sections but the number stays.
- The Wins Log at the bottom gets one line per completed item with date.
- If something feels missing, name it and I add it. The list grows by design.
