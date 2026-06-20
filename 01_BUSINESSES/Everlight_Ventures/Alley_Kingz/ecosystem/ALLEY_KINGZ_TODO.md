# ALLEY KINGZ -- MASTER TODO (single source of truth for progress)
> READ THIS + AGENT_MAILBOX.md at the START of every session. Update both at the END of every session.
> Legend: [x] done/live | [~] in progress | [ ] todo | [!] blocked | [b] built-not-deployed
> Last updated: 2026-06-19 (session 92cbcbe0). Auto-check-off helper: scripts/ak_todo_sync.py (scans live markers/files -> flips status).

## DEPLOY: SOLVED 2026-06-19
- [x] DEPLOY WORKS. Root cause was NOT a wedge/throttle -- the upload is SLOW (528 blobs ~77MB, ~5-9 min) and I kept KILLING it early. FIX: foreground `timeout 540 ssh e5 '...python3 -u cf_pages_direct_upload.py --dir game --project alley-kingz --exclude assets/maps,assets/hub'` run to [5/5] DEPLOYED. (detached/nohup/tmux all die with empty logs here -- use FOREGROUND.) See reference_e5_upload_chain_of_command memory.
- [x] LIVE NOW: the 1/8s multi-district walkable hub at alleykingz.online/hub_proto (verify with `curl -sL .../hub_proto` -- follow the 308 to the clean URL). Deploy watch-service + watchdog installed on e5.
- [ ] NOTE: AK-HUBGO marker in index.html reads 0 live -- moot once hub becomes root (index.html gets replaced by the hub); the Arena will route to the battler page directly.

## [x] DONE THIS SESSION (2026-06-19) -- verified live unless noted
- [x] Outage recovery (good build restored, run_crown clobber cron killed, git checkpoints)
- [x] Card-art consolidation: single resolver akCardArtRel (canon.js); all cards load in-game/shop/collection
- [x] Cards -> WebP (93% smaller, PNG fallback) live
- [x] All 400 maps (10 cities) live on alley-kingz-maps host
- [x] WebGL Phase-0 juice (additive particle bloom + hit-stop) live
- [x] Result-screen nav (Map / Journal / Main Menu) live
- [x] Walkable hub feel-proto v3 (scrolling 2600x2600 world, 3 districts w/ tint shift, 12 buildings/mode, radar, NPC, tap-to-move + WASD/arrows/Vim/joystick) LIVE at alleykingz.online/hub_proto
- [x] Leonardo bulk gen: 14 hub assets (11 facades + 3 district grounds) -> game/assets/hub/ (not yet deployed/wired)
- [x] Deploy protocol hardened into memory (size-to-payload, always-detached, one-at-a-time, retry hierarchy)
- [x] Plan docs: HUBWORLD_PLAN / PLATFORM_ROADMAP / WORLD_DESIGN / SOCIAL_PHASE2_SPEC / LOADSPEED_PLAN.md
- [x] THIS continuity system (this TODO + AGENT_MAILBOX.md + AK_MASTER_BLUEPRINT.md)

## [ ] NEXT ACTIONS (from blueprint, priority order)
1. [ ] MODULE_01_SPAWN: neutral-spawn fix (no auto-enter-on-load) in the REAL wired hub (proto already does this; port it)
2. [ ] Wire the 14 Leonardo facades/grounds into hub_proto (replace colored rects)
3. [ ] MODULE_03_PVP_RAID: shield + damage math (Clash-of-Clans style: offline raid, building stat loss, shield tiers + cooldowns, revenge 24h)
4. [ ] MODULE_06_ECONOMY: ALK flows + 7 burn sinks + staking
5. [ ] MODULE_11_WHITEOUT: Main Tower as Crew HQ (caps crew size), Reputation Flow (decays/raidable), Crew War Lanes (3 arenas), District-vs-District monthly war, Card Gear (4 slots), Training Grounds (offline)
6. [ ] Onboarding flow (60-second hook; social login first, Web3 opt-in)
7. [ ] ALK smart-contract mock
8. [ ] Referral/invite system
9. [ ] Live-ops calendar template (Monopoly-GO Reward-Flow cadence)
10. [ ] Anti-cheat / server-authoritative validation spec

## 11 MODULES (scaffolded under ALLEY_KINGZ_CORE/ by master-build wf w58u4obwj; [b]=stub coded, [~]=spec'd)
- [b] M01 SPAWN (NeutralSpawnController scaffolded; wire into real hub, port hub_proto 1/8s dwell)
- [b] M02 BUILDING (BuildingBase + SpellShop/DeckLab/MainTower scaffolded; finish HP/level/upgrade-timer)
- [b] M03 PVP_RAID (RaidController/ShieldSystem/DamageCalculator scaffolded w/ shield-tier + damage math)
- [~] M04 CREW (spec'd; WRAP live social.js + ak-crew edge fn)
- [~] M05 SOCIAL_URGENCY (spec'd; listener-only over social.js/quests.js/pass.js)
- [~] M06 ECONOMY (spec'd; ALK + 7 sinks + staking, Supabase-ledger adapter)
- [~] M11 WHITEOUT (spec'd; MainTower-HQ/ReputationFlow/CrewWarLanes/DvD/CardGear/TrainingGrounds)
- [ ] M07 PROGRESSION | [ ] M08 LIVE_OPS | [ ] M09 CREATOR_ECONOMY (UGC 70/25/5) | [ ] M10 INTEGRATION (adapters)
- SHARED: [x] EventBus.js | [x] DataValidator.js | [x] ConfigLoader.js | [x] SaveLoadManager.js | [x] AntiCheatValidator.js  (Wave-0 spine FINISHED, ~1200 lines, 38/38 tests pass -- wf wfgj1xrg5)

## [ ] CORE WIRING (AK_BUILD_PLAN.md dependency order -- the actual build queue)
- [x] W0.1 DataValidator real schemas | [x] W0.2 ConfigLoader tables -> config.ready | [x] W0.3 SaveLoadManager + AntiCheatValidator (Wave-0 DONE)

## DECISIONS LOCKED 2026-06-19 (operator)
- [ ] HUB = THE HOME SCREEN / ROOT (operator 2026-06-19, CONCRETE): alleykingz.online/ loads the WALKABLE HUB directly (hub_proto becomes / the root). The button-tile lobby UI is COMMENTED OUT -- kept in code as fallback "main logic", NOT shown as UI. Player spawns in the hub + walks into whatever building. The classic tower-battler / arcade lives behind THE ARENA building only. KEEP all custom art + buttons, just relocate their destinations onto the map.
  SUPPORTING SYSTEMS to develop (operator: "include it then"):
  - [ ] hub IS the loaded landing (loading gate reveals INTO the hub, not the lobby) + neutral spawn
  - [ ] persistent HUD over the hub: resources (gold/gems/bones) + player chip (name/level/trophies) + radar/mini-map
  - [ ] wire the 14 facades + generate the rest so buildings are real art, not colored rects
  - [ ] every building -> its real screen (Arena->battler, Garage->deck, Drop->shop, Clan->crew...) + RETURN-TO-HUB from each screen + the result screen
  - [ ] onboarding: first-time spawn + Ol' Scraps NPC guides the player (60-sec hook)
  - [ ] load player state into the hub (deck/profile/level/trophies) so buildings open correctly + Main Tower shows your rank
  - [ ] mobile load/perf (WebP + preload manifest) so the hub-as-home loads fast; persist hub position
  - [ ] classic arcade/battler accessible via the Arena; raidable buildings (M03) live on this same map later
- M07 PROGRESSION/SKILL-POINTS is ALREADY LIVE (economy.js levelUpCard + ak_profile.sp/skills/spec + SKILL_TREE + SPEC_PATHS) -- the "[GAP M07]" was stale; reclassify as polish/expand, not build-from-zero.
- squad.* NAME CONFLICT to reconcile before W2.2/DataValidator freeze: SQUAD = the persistent 2-5 crew sub-unit (squad-MMO vision); the crew-war 3-arena assignment = rename to lane.*/warlane.* (not squad.*).
- New docs from wf wfgj1xrg5: AK_EXECUTION_STATUS / AK_SQUAD_MMO_SYSTEM / AK_AUDIO_MASTERPLAN / AK_ART_QUEUE (~311 ready assets) / AK_SHOP_INTEGRATION / AK_PROGRESSION_SKILLPOINTS.md. Canonical JSON handoffs in handoffs/.
- [ ] W1.1 wire NeutralSpawnController into REAL hub (port 1/8s dwell) | [ ] W1.2 finish BuildingBase HP/level/upgrade-timer + 3 subclasses | [ ] FIRST DEPLOY: walk hub -> enter battler
- [ ] W2.1 Raid shield-tier+damage+24h-revenge (anti-whale cap) | [ ] W2.2 CrewManager roles/reinforce/war/betrayal (wrap social.js)
- [ ] W3.1 ALK CurrencyManager+TokenSink (Supabase ledger) | [ ] W3.2 SOCIAL_URGENCY push/crew-chest/betrayal-log (listener-only)
- [ ] W4.1 PROGRESSION cardLvls+prestige-burn+XP | [ ] W4.2 WHITEOUT HQ-cap->ReputationFlow->help-timer->war-lanes->gear->training->DvD
- [ ] W5 LIVE_OPS + CREATOR_ECONOMY + INTEGRATION adapters | [ ] ENGINE ADAPTER (engine.js emits match.start/win/lose; read-only bridge, never rewrite battler)

## [ ] ART PRODUCTION (47 maps / 340 assets / style guide in AK_ART_PORTFOLIO.md; route Leonardo bulk + Seedance hero)
- [~] Hub facades+grounds: 14 Leonardo assets generated (game/assets/hub/), not wired/deployed
- [ ] PHASE 1 (vertical slice): MAP_01 Core District, INT_01 Main Tower interior, UI_01 HUD, 5 avatars, 15 common cards, 8 core building exteriors, MINI_01 Card Clash, UI_05 Crew Chest anim, 5 spell FX, MAP_02 Outskirts
- [ ] PHASE 2 (beta): Outskirts buildings 6, rare cards 15, mini-games 6, clan missions 5, UI screens 3
- [ ] PHASE 3 (launch): Neon Abyss, epic+legendary cards 20, remaining mini-games 6 + clan missions 5, NFT assets 25, cinematics 10

## [ ] MINER / PRESTIGE / WORLD SYSTEMS (Bitcoin-Miner DNA + NeonReach canon -- full detail in AK_WORLD_BIBLE.md)
- [ ] Time-locked DISTRICTS 4-10 (silhouettes + countdowns; unlock @30/60/90d or war wins) -> M07/M08/M11
- [ ] Territory-control STIPEND (conquered district = daily ALK to crew; living political map, colors advance/retreat) -> M06/M11
- [ ] CREW ASCENSION prestige (reset buildings, keep collection/gear/emblem/rep-mult; 6 tiers Bronze->Crown) -> M07 + 500 ALK burn (M06)
- [ ] BARRIER system between districts (Collapsed Bridge / Gang Blockade / Police Checkpoint / Magical Ward; wait/rally/pay) -> M01/M08
- [ ] CREW STRATEGIES (daily rotate: Aggressive/Defensive/Economic/Diplomatic; reskins crew UI; pay-to-recon) -> M04
- [ ] CREW LIEUTENANTS (offline automation: Enforcer/Dealer/Scout, Common->Legendary) -> M04
- [ ] ALLEY CRATES (overworld pickups, respawn timer, Wooden/Metal/Neon/Golden; crew marks) -> M01/M02/M06
- [ ] WORLD CANON locked in (NeonReach: Surface vs Alleys; 4 factions Crowned/Rusted/Hologhosts/Unbound; 3 currencies ALK/Satoshi-Fragments/Crew-Rep; 10 archetypes) -- do NOT genericize (crew not clan, graffiti not runes)
- [ ] DEEP character customization (operator: "dogs + personal info" -- pets, tags, backstory, crew bonds)
- [ ] ART: 6 ASCENSION TIERS per building/card-frame/emblem (massive scope) + locked-district silhouettes (Docks/Undercity/Skyport) -> AK_ART_PORTFOLIO.md

## [ ] 12 GAPS TO CLOSE (operator's "account for what I'm not saying")
- [ ] anti-cheat/server-authority | [ ] server costs (Firebase->dedicated) | [ ] regulatory (crypto+gambling geo-block + play-for-fun mode) | [ ] onboarding friction (social login first) | [ ] data privacy (GDPR/CCPA) | [ ] offline decay (>14d -5%/day, 30d auto-kick) | [ ] regional pricing (APAC) | [ ] voice-chat safety (proximity + automod) | [ ] creator moderation (AI+report+manual) | [ ] token volatility hedging (stablecoin pairs/treasury) | [ ] anti-whale (cap raid dmg vs lower levels) | [ ] responsible-gambling safeguards

## [ ] PLATFORM ROADMAP (port via adapter swap; core modules unchanged)
- [x] Now: WebGL/Three.js/browser | [ ] Q3'26 Unity (PC/Mac) | [ ] Q4'26 Web3/crypto | [ ] Q1'27 Google Play/iOS | [ ] Q2'27 Console
- Long arc (platform-vision memory): V1.25(now) -> V2(2.5D walkable hub) -> V3(full 3D + redone art) -> V4(app/metaverse)

## BUSINESS STRUCTURE (keep business data != game dynamic data)
- everlightventures.io = parent LLC (legal/IP/funding) | alleykingz.online = product | alley-kingz.pages.dev = staging
