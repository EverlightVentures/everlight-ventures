# ALLEY KINGZ -- MASTER EXECUTION STATUS (consolidated; 2026-06-19)

> The single roll-up of the multi-domain pass just completed (squad-MMO, foundation
> code, audio, art queue, shop + skills, deploy). Reconciles AK_BUILD_PLAN.md (the HOW /
> wave order), ALLEY_KINGZ_TODO.md (the WHEN / status), and ALLEY_KINGZ_CORE/README.md
> (the architecture law). Companion to AK_MASTER_BLUEPRINT.md (WHAT/WHY) +
> AK_WORLD_BIBLE.md (canon) + AGENT_MAILBOX.md (handoff).
>
> Law honored across every pass: EventBus pub/sub only, no module imports another,
> wrap-not-rewrite the done 2D battler, brand "Alley Kingz", no em-dashes.
>
> Legend: [x] done/live | [~] wip | [ ] todo | [!] blocked | [b] built-not-deployed

---

## (1) WHAT IS NOW DONE / WIRED THIS PASS

Everything below is real code or real docs on the phone source-of-truth. "Wired" means
code-level integration over the EventBus, not live in production (see the gate in section 3).

### A. SHARED spine -- FINISHED (Wave 0 complete)
Pass: foundation-code. Dir: `ALLEY_KINGZ_CORE/SHARED/`.
- [x] `EventBus.js` -- already done, 11/11 verified (pre-existing).
- [x] `DataValidator.js` -- PROMOTED stub -> real (343 lines). Declarative schema check.
  Contracts registered for `raid.*` / `economy.*` (dot + UPPER_SNAKE) / `crew.*` / `squad.*`
  from the MODULE_03/04/06/11 SPEC event tables, plus verbatim `CREW_UNDER_SIEGE` +
  `crew.under_siege` alias. HARD rule kept: an UNREGISTERED schema returns `{ok:true}` so
  wiring never breaks a build; only registered contracts can report `ok:false`.
- [x] `ConfigLoader.js` -- PROMOTED stub -> real (309 lines). LOCKED tunables baked in as
  `AK_CONFIG_DEFAULTS`: 7 burn sinks (prestige 500, war 200/member, shield 100, relocate
  150, reroll 50, mint 25, marketplace 5% split), staking 30d, deflation 2%/40%, emission
  cap 2000; shield tiers (def 12/14/16h, buyable short/lockdown/deep, attack-through
  -3/-4/-5h); raid stat-loss + floors; crew caps L1=5..L10=20..L30=100 (piecewise-linear,
  verified L20=60); whiteout war lanes 3x5v5 + DvD phases. `load()` deep-merges
  defaults<-opts.defaults<-overrides, emits `config.ready`; convenience getters
  costs()/shieldTiers()/buyableShields()/crewMemberCap().
- [x] `SaveLoadManager.js` -- NEW (310 lines). Bus<->storage bridge. Listens
  STATE_SAVE/LOAD/REMOVE_REQUESTED, emits STATE_SAVED/LOADED/REMOVED. LocalStorageAdapter
  default + in-memory fallback (node/private-mode safe). `setAdapter()` is the Supabase swap
  point; all ops Promise-based so the swap is invisible. Namespaced `ak.save.*`, never throws.
- [x] `AntiCheatValidator.js` -- NEW (257 lines). Server-authority gate stub + trust boundary.
  Client sanity bounds run now (amount>=0, pct 0..100, finite), emit `ANTICHEAT_FLAGGED` on
  impossible values; economic events pass `trusted:false` until `setVerifier()` wires the M10
  re-sim adapter; non-economic events return `{ok:true}` so the gate never blocks a build.
- [x] `ALLEY_KINGZ_CORE/README.md` SHARED table updated for the 2 promotions + 2 new modules.

All five Node-syntax-clean; 38/38 behavioral assertions pass. This CLOSES Wave 0 of
AK_BUILD_PLAN (0.1 DataValidator, 0.2 ConfigLoader, 0.3 SaveLoad + AntiCheat).

### B. Squad-MMO system -- DESIGNED + CANON (new social layer)
Pass: squad-mmo. Doc: `AK_SQUAD_MMO_SYSTEM.md` (9 sections, wrap-not-rewrite, EventBus).
- Persistent squads (2-5, sweet-spot 3, crew-only, 24h switch cooldown, leader crown);
  M04 owns `squad.*`.
- 5 squad roles from the 10 archetypes (2 each) with combat bonuses: VANGUARD / MENDER /
  STRIKER / SNIPER / TACTICIAN; role-chain interlock layer.
- Pack overworld movement (diamond formation, role icons, leader crown, no-auto-enter
  all-confirm building entry, scale-to-size geometry); `pack.*` on M01.
- Multi-deck co-op combat (shared pool 30/player, shared hand 5 +1 Tactician, per-card
  attribution, COMBO->SYNERGY->ROLE-CHAIN bonus stack, 5 formations); new `coop.*` consumer
  of the existing engine sim -- no engine.js edits.
- Enemy + loot scaling (everyone-gets-loot, contribution-weighted + floor, via ak_grants).
- Mini-teams (Tower Batters / Raiders / Warlords / Bankers / Connectors) -> crew-score slices.
- Major crew events -> TOTAL CREW SCORE (Gauntlet weekly, Crew Games monthly, DvD monthly,
  Crew War Season quarterly, Ascension Ceremony); crew score is a derived read-model listener.
- NOTE: design carries an unresolved squad-meaning flag -- the foundation pass independently
  defined `squad.*` as the war-lane (3x5v5) / 2v2 sub-roster lifecycle, while the squad-MMO
  pass defines squads as a persistent crew sub-unit. RECONCILE before W2.2 (see TODO delta).

### C. Audio + 4-channel sensory feedback -- SPEC'd (verified against real engine)
Pass: audio. Doc: `AK_AUDIO_MASTERPLAN.md`.
- Mapped SFX / haptics / shake-or-pulse / music-duck-crossfade for all 9 master-plan systems
  to REAL engine primitives verified in `game/engine.js`: `sfx()` sample-first/synth-fallback
  dispatcher + `SFX_NAMES`/`SFX_BUF`, `haptic()` + `HAPTIC_PAT`, `game.shake`, `_bgm` A/B deck.
- New pure-listener AudioDirector (modeled on M05 SOCIAL_URGENCY) subscribes to canonical
  events (`CREW_UNDER_SIEGE`, `raid.attack.launched`, `crew.reinforcement.*`,
  `building:damaged/destroyed/repaired`, `progression.prestige`) -- nothing calls audio directly.
- 9 systems cued (siege alert, crew-chest, war countdown, reinforce, ascension 6-tier, DvD,
  squad synergy, building damage, alley-crate). Tool routing per AUDIO_TOOL_DECISION.md
  (ElevenLabs SFX + Suno music, ZzFX for $0 UI ticks, procedural `tone()` always-on fallback).
- Ships verbatim gen commands: `MANIFEST.update({...})` for `art/generate_sfx.py`, a
  `bakeMetaUiSfx()` ZzFX block, Suno prompts (locked Persona), plus additive engine deltas
  (SFX_NAMES additions, 5 new HAPTIC_PAT, `AK.haptic` export, AudioDirector wiring sketch).

### D. Art generation queue -- BUILT + RUNNABLE
Pass: art-queue. Doc: `AK_ART_QUEUE.md`. Sourced from AK_ART_PORTFOLIO + AK_WORLD_BIBLE +
the real `art/art_factory.py --enqueue` signature.
- Prioritized P0->P3 queue, each section a copy-paste bash loop over a modifier array
  (faction/tier/role) with the literal `$NEON` palette + `$FINISH` tokens.
- P0 vertical slice (~51 assets): 3 maps + 3 district silhouettes + 10 archetypes + 8 Bronze
  buildings + 12 HUD/currency icons + skill-point token + 4 node frames + 10 squad role auras.
- P1 (interiors, 40 faction skins, props, crates); P2 (the 6-tier ascension scope: 96 buildings,
  24 emblems, 24 card frames + Crown set); P3 (NFT plates/skins/cinematics).
- Totals: ~311 hand-enqueued assets P0-P2 (~285 Leonardo bulk, ~26 Seedance hero). Drain via
  the existing 15:17 UTC `art_factory_cron.sh` (queue->cards->maps), idempotent, auto-deploys.
- Two load-bearing notes baked in: leave the gritty house auto-tail ON (palette held by hex,
  grit lifts off "kiddish"); sequence P0 first against the free cap, gate P2 ascension batch.

### E. Shop integration + progression / skill-points -- SPEC'd, key finding: MOSTLY ALREADY LIVE
Pass: shop+skills. Docs: `AK_SHOP_INTEGRATION.md` + `AK_PROGRESSION_SKILLPOINTS.md`.
- Grounded in line-level reads of live code (not stale plans): the AK_BUILD_PLAN "[GAP M07]
  cardLvls unused" gap is CLOSED. `game/economy.js levelUpCard()` + index.html AK-VIS/AK-GARAGE
  drive a working card-level system (cardLvls 1-10, copies, UP_COPIES/UP_COINS per rarity,
  linear `levelMult` through `computePerks().cardLevels` with engine clamps).
- Skill-Points system is also LIVE: `ak_profile.sp/spEarned/skills/spec`, the 3-branch Street
  Code tree (`SKILL_TREE`), Lv10 specializations (`SPEC_PATHS`). M07 is far more built than the
  plan claimed -- the remaining M07 work is prestige burn + match-XP source + milestones.

### F. Deploy -- runbook/protocol hardened
Pass: deploy. The deploy protocol is captured in CHECKPOINTS.md + memory (size-to-payload,
always-detached nohup ship.sh, one-at-a-time, retry hierarchy, deploy ONLY from e5 `~/ak_deploy`
via ship.sh, verify on the live edge with Playwright not the tool exit code). AK sole-deployer
rule remains in force.

---

## (2) WHAT IS QUEUED + BUILD ORDER (tied to AK_BUILD_PLAN waves)

Wave 0 is now DONE (section 1A). The critical path resumes at Wave 1.

- WAVE 1 -- the hub shell (NEXT):
  - W1.1 M01 SPAWN: wire NeutralSpawnController into the REAL hub; port the proven hub_proto
    v3 1/8s dwell-to-enter + no-auto-enter guarantee. Also wire the 14 Leonardo facades/grounds
    (already generated to `game/assets/hub/`) to replace the colored rects.
  - W1.2 M02 BUILDING: finish BuildingBase HP/level/upgrade-timer + register 3 subclass
    instances (SpellShop->shop.html, DeckLab->shop.html#deck, MainTower->index.html?go=match).
  - GATE: FIRST DEPLOY = walk hub -> enter the existing battler. Minimum shippable wrap.
- WAVE 2 -- the stakes (build M03 + M04 in PARALLEL once M02 events freeze; they meet at
  `crew.under_siege`):
  - W2.1 M03 PVP_RAID: shield-tier + damage + 24h-revenge math (Clash DNA), anti-whale cap.
  - W2.2 M04 CREW: roles + reinforcement queue + war registration + betrayal flag (wrap live
    social.js). RECONCILE the two `squad.*` definitions here (see TODO delta).
- WAVE 3 -- economy + loop tighteners:
  - W3.1 M06 ECONOMY: ALK flows + 7 burn sinks + staking (Supabase ledger adapter; tunables
    already in ConfigLoader).
  - W3.2 M05 SOCIAL_URGENCY: push + crew-chest timer + betrayal-log + flash-bonus (listener-only;
    AudioDirector from the audio pass mounts here).
- WAVE 4 -- depth + Whiteout backbone:
  - W4.1 M07 PROGRESSION: card levels + skill-points are LIVE; remaining = prestige 500-ALK
    burn + match-XP source + milestones.
  - W4.2 M11 WHITEOUT in order: HQ cap -> ReputationFlow -> help-timer -> war-lanes -> card
    gear -> training -> DvD last.
- WAVE 5 -- platform + monetization surface:
  - W5.1 M08 LIVE_OPS (event calendar + Reward-Flow + the squad-MMO crew-event calendar:
    Gauntlet/Crew Games/DvD/War Season/Ascension Ceremony).
  - W5.2 M09 CREATOR_ECONOMY (UGC 70/25/5 split + mint hooks).
  - W5.3 M10 INTEGRATION adapters (RendererAdapter / Unity / Blockchain / GooglePlay +
    AntiCheat verifier wiring -- the swap point that makes Q3'26 Unity / Q4'26 Web3 a swap).
- CROSS-CUTTING: ENGINE ADAPTER -- emit `match.start/win/lose` + `unit.*` from engine.js as a
  read-only bridge; never rewrite the battler. The squad co-op `coop.*` layer and the crew-score
  read-model both consume this. Required before W4.1 XP and W2 crew-war scoring can land.

Art runs in parallel on its own cron lane: drain P0 (51 assets) against the free cap to fill
the W1 hub + vertical slice, gate the 144-asset P2 ascension batch behind P0+P1.

---

## (3) THE WIRED-VS-LIVE GATE

Everything in section 1 is WIRED at the code/doc level on the phone source-of-truth. Nothing
new in this pass is LIVE in production. The single blocker is deploy, not code.

- [!] ACTIVE BLOCKER (carried from TODO): the hub_proto 1/8s dwell + Arena->battle tweak
  (`?go=match` / `AK-HUBGO`) is CODED + git-committed (checkpoint fbf3eae) but NOT deployed.
  e5->CF upload is wedged (phone<->e5 SSH drops on multi-sec commands; cf_pages script hangs on
  first call; phone proot SSL aborts on direct CF deploy).
- UNBLOCK = operator restarts e5 (shared infra; I am blocked from rebooting it) OR ssh
  stabilizes. Per the e5 chain-of-command, try PRIMARY `ssh e5` (direct public IP, Tailscale-
  independent, fast) before `ssh e5-mother` (Tailscale, flaky). AK deploys ONLY from e5
  `~/ak_deploy` via ship.sh.
- Implication: the SHARED spine, squad-MMO design, audio spec, art queue, and shop/skills specs
  do NOT require deploy to be considered done at this stage -- they are code + design artifacts.
  They go LIVE in sequence behind the same e5 deploy unblock, starting with the W1 FIRST DEPLOY
  (walk hub -> enter battler). The v3 multi-district walkable world is ALREADY live at
  alleykingz.online/hub_proto; only the dwell tweak + the new wiring are pending the unblock.
- Verify-on-edge rule stands: confirm every deploy in a real browser (Playwright on e5), never
  on the tool exit code.

---

## (4) TODO DELTA -- concrete changes to make in ALLEY_KINGZ_TODO.md

### SHARED row (line ~43) -- flip to reality (Wave 0 now done)
- FLIP: `DataValidator.js [~] -> [x]` (real schemas, 343 lines, ok:true default preserved).
- FLIP: `ConfigLoader.js [~] -> [x]` (real, 309 lines, locked tunables + config.ready).
- FLIP: `SaveLoadManager.js [ ] -> [x]` (310 lines, adapter pattern, Supabase swap point).
- FLIP: `AntiCheatValidator.js [ ] -> [x]` (257 lines, server-authority gate stub).
- Net: SHARED row becomes all `[x]` -- the spine is complete.

### CORE WIRING block (line ~46) -- flip Wave 0
- FLIP W0.1 / W0.2 / W0.3 from `[ ] -> [x]`. Add note: "Wave 0 spine complete 2026-06-19;
  38/38 assertions pass." W1.1 is now the active front of the critical path.

### NEXT ACTIONS (line ~22) -- reprioritize
- Item 1 (M01 neutral-spawn wire) + item 2 (wire 14 Leonardo facades) stay top; they ARE W1.1.
- Add cross-ref on item 4 (M06): "tunables already baked into ConfigLoader; M06 reads them, no
  hardcoding." Add cross-ref on item 10 (anti-cheat): "AntiCheatValidator stub landed (W0.3);
  remaining = setVerifier() server re-sim in W5.3."

### MAPS / AUDIO / GAMEPLAY / SKINS / SHOP / BUILDING-ART / SKILL-POINTS / SQUAD deltas
Add a new "MULTI-DOMAIN PASS 2026-06-19" section:
- MAPS: `[ ] wire AK_ART_QUEUE P0.1 (3 maps L+S) + P0.2 (3 district silhouettes Docks/Undercity/
  Skyport)` -- queue is runnable; drain against free cap first.
- AUDIO: `[ ] add AudioDirector pure-listener (AK_AUDIO_MASTERPLAN) + apply additive engine
  deltas (SFX_NAMES, 5 HAPTIC_PAT, AK.haptic export)`; `[ ] run generate_sfx.py MANIFEST block
  + bakeMetaUiSfx() ZzFX`; `[ ] commission Suno DvD + ascension anthems (locked Persona)`.
- GAMEPLAY: `[ ] multi-deck co-op combat coop.* layer (shared pool/hand, COMBO->SYNERGY->
  ROLE-CHAIN, 5 formations) -- engine adapter consumer, NO engine.js edits`; `[ ] ENGINE ADAPTER
  emits match.*/unit.* (read-only bridge) -- prerequisite for XP + crew-war + co-op scoring`.
- SKINS: `[ ] AK_ART_QUEUE P1 40 faction skins (10x4) + in-match cosmetic = card alt-art swap
  (reuses Fortnite-layer rail)`.
- SHOP: `[x] confirm M07 card-level + skill-point shop flows already LIVE (economy.js
  levelUpCard + AK-VIS/AK-GARAGE)`; `[ ] apply AK_SHOP_INTEGRATION spec deltas`.
- BUILDING-ART: `[ ] AK_ART_QUEUE P0.4 8 Bronze exteriors -> wire to M02 subclasses`; `[ ] gate
  P2 6-tier ascension building set (96) behind P0+P1`.
- SKILL-POINTS: `[x] mark Skill-Points system LIVE (ak_profile.sp/skills/spec + SKILL_TREE +
  SPEC_PATHS)`; `[ ] add skill-point token + 4 node-frame art (AK_ART_QUEUE P0.6)`.
- SQUAD: append the full SQUAD-MMO checklist from AK_SQUAD_MMO_SYSTEM.md section 9 (persistent
  squads in M04, 5 roles + role-chain, pack movement in M01, co-op combat, enemy+loot scaling,
  mini-teams, major crew events in M08, total crew score read-model, DataValidator schemas for
  squad.*/coop.card.played/pack.move/loot.rolled/crew.score.updated).

### RECONCILE flag (open, blocks W2.2)
- `[!] squad.* meaning conflict`: foundation pass defined `squad.*` = war-lane (3x5v5)/2v2
  sub-roster lifecycle; squad-MMO pass defined squads = persistent 2-5 crew sub-unit with roles.
  Operator must confirm ONE meaning before M04 / DataValidator squad schemas are frozen.

### Gaps cross-link (line ~71)
- `anti-cheat/server-authority` -> AntiCheatValidator stub DONE (W0.3); verifier pending W5.3.
- `voice-chat safety` -> ties to squad-MMO open question (voice/proximity safety on pack play).

---

## CITED PASSES (this consolidation)
- squad-mmo: AK_SQUAD_MMO_SYSTEM.md (9 sections)
- foundation-code: ALLEY_KINGZ_CORE/SHARED/{DataValidator,ConfigLoader,SaveLoadManager,
  AntiCheatValidator}.js + README.md (Wave 0 complete, 38/38 assertions)
- audio: AK_AUDIO_MASTERPLAN.md (AudioDirector + 9-system 4-channel feedback)
- art-queue: AK_ART_QUEUE.md (~311 P0-P2 assets, runnable bash loops)
- shop+skills: AK_SHOP_INTEGRATION.md + AK_PROGRESSION_SKILLPOINTS.md (M07 mostly already LIVE)
- deploy: CHECKPOINTS.md + memory (e5 ship.sh protocol, AK sole-deployer, verify-on-edge)
