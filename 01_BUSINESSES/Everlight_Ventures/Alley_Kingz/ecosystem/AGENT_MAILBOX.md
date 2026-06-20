# ALLEY KINGZ -- AGENT MAILBOX (cross-session handoff log)
> Protocol (operator directive 2026-06-19): At SESSION START, read this + ALLEY_KINGZ_TODO.md so you know exactly where we are -- never re-do done work or re-ask solved questions. At SESSION END, append a dated entry here (done / decisions / blockers / next) and flip statuses in the TODO. This is the all-in-one-chat continuity rail.

---
## 2026-06-19 (session 92cbcbe0) -- THE BIG SESSION

### Shipped + live (verified)
Card-art consolidation (single resolver), cards->WebP (93% smaller), all 400 maps, WebGL Phase-0 juice (bloom+hit-stop), result-screen nav (Map/Journal/Main Menu), and the walkable hub feel-proto v3 (scrolling 2600x2600 world, 3 districts with real-time tint shift, 12 buildings/mode wired to navigate, radar, NPC, tap-to-move + WASD/arrows/Vim/joystick) at alleykingz.online/hub_proto. 14 Leonardo hub assets generated (game/assets/hub/, not yet wired).

### Decisions locked
- Tech for the hub: 2.5D / canvas2D now (reuses engine.js stack, no Three.js for V2). Three.js look = V3 art upgrade. Do NOT port the juiced engine.js battler.
- Deploy doctrine hardened (reference_e5_upload_chain_of_command memory): size-to-payload, ALWAYS detached (</dev/null), ONE upload at a time, retry hierarchy, verify on the live CDN edge.
- Leonardo = bulk/cheap (API, facades/grounds/props). Seedance = premium hero art (operator does manually): Arena facade, dog-pilot avatar, door-reveal splash (prompts in chat).
- Brand: business data (everlightventures.io LLC) stays separate from game dynamic data.

### Open blocker (HANDOFF)
hub_proto 1/8s-dwell tweak + Arena->battle `?go=match` handler are CODED + committed (fbf3eae) but the e5->CF deploy is wedged (SSH drops on multi-sec cmds; cf_pages first-call hang despite CF api=90ms; phone proot SSL aborts). UNBLOCK: operator restarts e5, then `ssh e5 'cd ~/ak_deploy && source cf.env && nohup python3 -u cf_pages_direct_upload.py --dir game --project alley-kingz --branch main --exclude assets/maps,assets/hub >/tmp/cf.log 2>&1 </dev/null &'` (instant launch, detached) + verify CDN.

### Next session: start here
Read ALLEY_KINGZ_TODO.md "NEXT ACTIONS". Top of queue: land the blocked deploy (after e5 restart), then MODULE_01_SPAWN port + wire the 14 facades, then MODULE_03 raid system. The MASTER WORKFLOW (launched this session) maps current code vs the blueprint + scaffolds the 11-module EventBus architecture -- fold its output into the TODO.

### 16:35 update -- master build + art portfolio landed
- Master-build workflow (w58u4obwj) DONE: scaffolded ALLEY_KINGZ_CORE/ (8 modules + SHARED, 25 files = EventBus + stubs + per-module SPEC.md for M01/M02/M03/M06/M11/M04-05) + wrote AK_BUILD_PLAN.md (5-wave build order + TODO delta + integration story). Statuses folded into the TODO ([b]=stub, [~]=spec'd). Critical path: W0 spine -> M01 -> M02 -> FIRST DEPLOY -> M03+M04 -> M06 -> M05 -> M07/M11 -> M08/09/10.
- Art portfolio landed: AK_ART_PORTFOLIO.md (47 maps, 340 assets, style guide, prompt templates, 3 production phases). Routes Leonardo bulk + Seedance hero. Added as ART PRODUCTION section in the TODO.
- Continuity system live + verified: ALLEY_KINGZ_TODO.md (52 items, 28% done), this mailbox, AK_MASTER_BLUEPRINT.md, AK_ART_PORTFOLIO.md, scripts/ak_todo_sync.py (auto-flips ONLY live-verifiable items, e.g. the deploy markers; module status set manually from AK_BUILD_PLAN.md). Read-at-session-start rule in core memory.
- NOTE: ecosystem/ already holds ~80 prior planning docs (MASTER_STRATEGY, PLATFORM_GAP_AND_ROADMAP, CARD_EXPANSION, etc.) -- the TODO is now the index/tracker over all of it.

### 16:45 update -- handoff ingested: Bitcoin-Miner DNA + NeonReach world bible
- New canon doc AK_WORLD_BIBLE.md: NeonReach world (Surface vs Alleys; 4 factions Crowned/Rusted/Hologhosts/Unbound; 3 currencies ALK/Satoshi-Fragments/Crew-Rep; 10 player archetypes), the 7 Bitcoin-Miner systems (time-locked districts, territory stipend, Crew Ascension 6-tier prestige, barriers, crew strategies, lieutenants, alley crates), tailored map canon (real-city inspirations), and the HARD "do not genericize" rule (crew not clan, graffiti not runes).
- TODO gained a MINER/PRESTIGE/WORLD SYSTEMS section (10 items) tied to the module plan. Art scope flagged: 6 ascension tiers per building/card/emblem.
- Operator is in HANDOFF-DUMP mode ("keep this a running task list, I've got a few more to hand off"). Protocol: ingest each pasted handoff into a reference doc + add TODO items + note here. Do NOT lose any of it.

### 17:20 update -- canonical handoff JSONs preserved + master-execution workflow launched
- The 3 source-of-truth JSONs are now in ecosystem/handoffs/ (operator downloaded them; copied off Downloads so they survive): alley_kings_master_blueprint.json, alley_kings_art_portfolio.json (FULL -- 65 enumerated art prompts, 5 map tiers, 12 categories, 3 production phases), alley_kings_squad_mmo_update.json (9-section squad spec). These are the canonical artist/dev source; the .md docs are the working summaries.
- Master-execution workflow wfgj1xrg5 running (all domains): squad-mmo capture, Wave-0/1 foundation CODE, audio masterplan, art queue, shop+skill-points integration, deploy runbook -> AK_EXECUTION_STATUS.md + TODO delta. Fold its output when it lands.
- "Wired vs live": everything advances at code/doc level; going LIVE is gated on the e5 deploy unblock (operator restart). hub_proto v3 multi-district world IS already live.

### Operator directives standing
"Socially radioactive" (friends beg/hate each other to log in) | "Come on buddy" urgency mechanics | prime for Unity+crypto+Google Play | "no strays" (modular, EventBus, clean data) | "account for what I'm not saying" (fill gaps proactively) | research best-of-the-best | Whiteout Survival DNA (furnace/Main-Tower urgency + alliance dependency + cross-server war).
