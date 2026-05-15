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

70. 🔥☐ **Build `email_discovery.py`** &mdash; the REAL bottleneck. 114 parsed parcels, 61 with mailing addresses, ZERO with emails. Pipeline: domain harvest (Hunter Domain Search) + pattern permutation + SMTP MAIL FROM probe + EmailRep/HIBP existence cross-check. Expected lift: 30-50% of 61 mailing-equipped parcels → email-firable. **Highest ROI single build on the entire list. Only OSINT item that plausibly accelerates Deal 1.**

71. ☐ FEC API key swap &mdash; replace `DEMO_KEY` with real key (60-second free fix). Currently 429ing in live_log. Register at api.open.fec.gov/developers.

72. ☐ Build `obituary_estate.py` &mdash; Legacy.com / Newspapers.com scrape for heir + executor surfacing. 28 of 114 parsed parcels are estate-flagged. Highest direct-dollar lift in Bombal's canon. S effort, GREEN creep-line.

73. ☐ Build `username_enrichment.py` (WhatsMyName + Maigret wrapper) &mdash; replaces HEAD-only `social_recon.py` shim. Public profiles only, no auth-bypass. Signal stays internal as lead score, never quoted in outbound. S effort.

74. ☐ Build `reverse_whois.py` (WHOXY historical) &mdash; LLC owner → other domains they've registered. High signal for institutional-investor owners. S effort, GREEN.

75. ☐ Build `local_news_archive.py` (Kagi + Newspapers.com) &mdash; hyper-local personalization hooks. M effort, YELLOW guardrails (signal informs segmentation, never language).

76. ☐ Build `wayback_contact_extract.py` &mdash; skip-trace fallback for scrubbed LLC sites via Wayback snapshots. M effort, YELLOW for individuals, GREEN for LLCs.

77. ☐ Beef up `property_records.py` from 32-line stub → RentCast + Zillow + Redfin actual implementation. Unblocks Chris-side valuation talk track. M effort.

78. ☐ Build `macro_context` enrichment pass &mdash; NOAA NWS + USGS + InciWeb + GDELT puller keyed off `owner_mailing_state` + `property_address_full` + `parcel_id`. Appends matches to `pitch_hooks`. M effort, all GREEN sources.

79. ☐ Fix `esign_server.py` hardcoded dev-secret fallback &mdash; security risk before any live PSA send. Anyone with source can forge sign tokens.

80. ☐ Add 10 new `compliance_log.py` event types per Priya memo (hash-chained, doctrine matches `deal_execution_log.py`). Events: license-plate-block, FCRA-purpose-check, social-platform-scope-check, breach-data-block, etc.

81. ☐ Add per-state opt-out footer rendering to `branded_mailer.py`. TX TDPSA (Bus & Com 541) and NV NRS 603A are now active comprehensive privacy laws &mdash; we trigger them. Plain-English opt-out + privacy notice link per state.

82. ⏸☐ **Buyer-side criminal-background flow** for Inner Circle Verified tier &mdash; CONDITIONAL YES under FCRA 1681b(a)(3)(F)(ii). Route through Stripe Identity, add consent checkbox + adverse-action notice template. **POST-DEAL-1 unlock.**

83. ☐ Hard-skip list codified in `legal_scope.py` &mdash; permanent blocks: license plates (DPPA), voter-ID brute, breach CSV enrichment, Wigle, Burp brute, scraping-behind-login, criminal background as FCRA report for seller side, HexStrike external. Doctrine binding on all future agents.

84. ☐ Execute the 5 pre-existing OSINT work orders from `TODO_AGENTS.md` (sitting since 2026-05-12): SpiderFoot install (WO1), HexStrike eval in sandbox VM (WO2), Fabric 5-pattern port (WO3), Google Dorking for prospect discovery (WO4), self-OSINT defensive audit (WO5).

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

---

## HOW TO USE THIS LIST

- I update this file at the end of every session. Status icons change, new items get 🆕, completed items get ☑ + date.
- The numbers ARE stable references. When we talk about item #6 next week, you and I both know what it is.
- Items can move between sections but the number stays.
- The Wins Log at the bottom gets one line per completed item with date.
- If something feels missing, name it and I add it. The list grows by design.
