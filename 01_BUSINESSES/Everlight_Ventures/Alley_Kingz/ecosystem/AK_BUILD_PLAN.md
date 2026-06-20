# ALLEY KINGZ -- MASTER BUILD PLAN (synthesis; 2026-06-19)

> Companion to AK_MASTER_BLUEPRINT.md (the WHAT/WHY) + ALLEY_KINGZ_TODO.md (the WHEN/status)
> + ALLEY_KINGZ_CORE/README.md (the architecture law) + AGENT_MAILBOX.md (handoff).
> This file is the HOW: build order, the concrete TODO delta, and the integration story
> that wraps the existing 2D battler instead of rewriting it.

Sources cited inline as: [GAP] = the 11-module gap map, [BP] = AK_MASTER_BLUEPRINT.md,
[TODO] = ALLEY_KINGZ_TODO.md, [CORE] = ALLEY_KINGZ_CORE/README.md + scaffolded SPECs.

## GROUND TRUTH (do not relitigate)
- The 2D tower battler is DONE and LIVE (engine.js, canon.js 48 cards, index.html canvas,
  shop/, economy.js, social.js, pass.js, quests.js, handlers_data.js, drip.js). We WRAP it,
  never rewrite it [TODO core-loop, GAP "architectural foundation in place"].
- The spine exists: SHARED/EventBus.js is fully implemented + 11/11 verified; DataValidator.js
  and ConfigLoader.js are documented stubs [CORE]. Law: no module imports another; all comms
  over the bus; re-platform by swapping ONE adapter [CORE, BP module-31].
- Already scaffolded under ALLEY_KINGZ_CORE/: M01 SPAWN (NeutralSpawnController), M02 BUILDING
  (BuildingBase + SpellShop/DeckLab/MainTower), M03 PVP_RAID (RaidController/ShieldSystem/
  DamageCalculator), M04 CREW (CrewManager), M05 SOCIAL_URGENCY (PushNotificationManager),
  M06 ECONOMY (CurrencyManager/TokenSink), M11 WHITEOUT (MainTowerSystem/ReputationFlow) -- all
  with SPEC.md. These are behavior-verified stubs, not finished features.
- HARD constraint from [TODO] active blocker: the hub_proto dwell-to-enter tweak is coded but
  the e5->CF deploy is wedged (Tailscale/ssh). Build does not wait on deploy; code lands on
  phone source-of-truth, ships from e5 when ssh stabilizes.

---

## (1) BUILD ORDER

Dependency rule: a layer may only depend on SHARED/. Everything else is an event contract.
So "depends on" below means "consumes/produces these events", never "imports".

### WAVE 0 -- finish the spine (unblocks everything)
0.1 SHARED/DataValidator.js -- promote from permissive stub to real schema check for the
    high-traffic events (raid.*, economy.*, crew.*). Keep `ok:true` default so wiring never
    breaks a build [CORE]. Depends on: nothing.
0.2 SHARED/ConfigLoader.js -- load ecosystem config (cost tables, shield tiers, crew caps),
    emit `config.ready`. Every later module reads tunables from here, not hardcoded [CORE, BP token-economy].
0.3 SHARED/SaveLoadManager.js + SHARED/AntiCheatValidator.js -- listed in [TODO] SHARED row but
    NOT yet scaffolded. SaveLoad bridges bus state to localStorage now / Supabase later (adapter
    pattern). AntiCheat is the server-authority gate [TODO gap-1, next-action-10]. Stub first.
    Depends on: EventBus only.

### WAVE 1 -- the hub shell (the thing you walk around in)
1.1 M01 SPAWN (NeutralSpawnController) -- WIRE the already-built controller into the REAL hub.
    Port the proven hub_proto.html v3 dwell-to-enter (1/8s) + no-auto-enter guarantee [GAP M01,
    BP spawn-bug, TODO next-action-1]. Reuses: hub_proto.html canvas/district/building layout.
    Produces: `spawn:ready`, `building:enterIntent`. Depends on: M02 emitting `building:registered`.
1.2 M02 BUILDING (BuildingBase + subclasses) -- finish HP/level/stats/state machine + the
    upgrade timer/cost economy hooks. SpellShop -> shop/shop.html, DeckLab -> shop/shop.html#deck,
    MainTower -> index.html?go=match [GAP M02]. Reuses: economy.js cost tables. Produces:
    `building:registered`, `building:enterRequest`. Consumes: `building:enterIntent` (from M01).

> After Wave 1 you can WALK the hub and ENTER the existing battler. That is the minimum
> shippable wrap and the first deploy target.

### WAVE 2 -- the stakes (why you log back in)
2.1 M03 PVP_RAID (RaidController/ShieldSystem/DamageCalculator) -- Clash-of-Clans DNA: offline
    raid, building stat decay, shield tiers + cooldown, 24h revenge [GAP M03, BP core-loop +
    dopamine-engine, TODO next-action-3]. Reuses: economy.js loot tables (TOWER_DROP, CAP_COINS).
    Consumes: M02 building state. Produces: `raid.start`, `raid.result`, `crew.under_siege`.
2.2 M04 CREW (CrewManager) -- WRAP existing social.js (crew create/join/leave/roster/chat already
    live via ak-crew edge fn). Add roles, reinforcement queue, war registration, betrayal flag
    [GAP M04, BP come-on-buddy tier-1/2]. Reuses: social.js model, ak_account.js Supabase client,
    ak-crew edge fn. Consumes: `crew.under_siege` (from M03). Produces: `crew.war.declared`,
    `crew.member.betrayed`.

> Wave 2 needs M02 (buildings to raid) + the EventBus contract from M03 to M04. Build M03 and
> M04 in PARALLEL once M02's events are frozen -- they only meet at `crew.under_siege`.

### WAVE 3 -- the economy + the loop tighteners
3.1 M06 ECONOMY (CurrencyManager/TokenSink) -- ALK flows + the 7 burn sinks + staking model.
    Mock the token (Supabase ledger) behind an adapter so the real ALK contract is a later swap
    [GAP M06, BP token-economy, TODO next-action-4 + 7]. Reuses: economy.js LOOT/CHEST/SCRAP tables,
    social.js grant pipeline. Consumes: `raid.result`, `crew.war.declared` (war-cost sink).
    Produces: `economy.grant`, `economy.burn`, `economy.stake`.
3.2 M05 SOCIAL_URGENCY (PushNotificationManager + crew-chest/betrayal-log/flash-bonus) -- the
    "come on buddy" tier-2/3 engine. Pure listener layer: it reacts to facts other modules already
    emit [GAP M05, BP come-on-buddy + dopamine-engine]. Reuses: social.js mk() builder, quests.js
    claim flow, pass.js reward rail. Consumes: `crew.under_siege`, `crew.member.betrayed`,
    `raid.result`. Produces: notifications only (no new game state).

### WAVE 4 -- depth + the Whiteout backbone
4.1 M07 PROGRESSION -- card levels (cardLvls profile field exists, unused [GAP M07]), prestige
    (burns 500 ALK -> M06 sink), milestones, account XP from matches. Reuses: economy.js
    ensureShape(), pass.js tier-unlock, handlers_data.js mods resolver. Consumes: `match.win`
    (from engine adapter), `economy.burn`. Produces: `progression.levelup`, `progression.prestige`.
4.2 M11 WHITEOUT (MainTowerSystem/ReputationFlow + war lanes / DvD / card gear / training) -- the
    biggest module; build its subsystems in this internal order: MainTower-as-HQ (crew-size cap) ->
    ReputationFlow (heat decay/raidable) -> Crew Help Timer -> Crew War Lanes (3 arenas) -> Card
    Gear (4 slots) -> Training Grounds -> District-vs-District last [GAP M11, BP whiteout-integration,
    TODO next-action-5]. Reuses: engine.js card model, social.js crew context, economy.js rewards,
    handlers_data.js skill-tree pattern for gear unlocks. MainTower subclass from M02 is the anchor.

### WAVE 5 -- platform + monetization surface
5.1 M08 LIVE_OPS -- event calendar + Monopoly-GO Reward-Flow orchestrator + limited-time challenges
    [GAP M08, BP dopamine-engine, TODO next-action-9]. Reuses: quests.js, pass.js, economy.js grants.
5.2 M09 CREATOR_ECONOMY -- UGC 70/25/5 split, creator fund, mint hooks [GAP M09, BP roblox/fortnite].
    Reuses: economy.js burn ledger, social.js grants. Consumes: `economy.*`.
5.3 M10 INTEGRATION -- adapter stubs: RendererAdapterBase + UnityRendererAdapter, BlockchainMint
    Validator, GooglePlayAdapter, AntiCheatValidator wiring [GAP M10, TODO platform-roadmap +
    next-action-10]. Reuses: engine.js window.AK contract, shop.js api() pattern, ak_account.js client.
    This is what makes Q3'26 Unity / Q4'26 Web3 / Q1'27 Play a swap, not a rewrite.

### CRITICAL PATH (shortest route to a shippable wrap)
WAVE 0.1-0.2 -> M01 -> M02 -> first deploy (walk + enter battler) -> M03 + M04 (parallel) ->
M06 -> M05 -> then depth (M07, M11) -> then platform (M08, M09, M10).

---

## (2) TODO DELTA -- changes to make in ALLEY_KINGZ_TODO.md

Flip / add the following (legend: [x] done | [~] wip | [ ] todo | [!] blocked | [b] built-not-deployed):

### SHARED row (line ~36) -- correct to reality
- FLIP `SaveLoadManager.js` and `AntiCheatValidator.js` from implied-done to `[ ]` (NOT scaffolded yet).
- ADD note: `EventBus.js [x] (11/11 verified) | DataValidator.js [~] (permissive stub) |
  ConfigLoader.js [~] (stub) | SaveLoadManager.js [ ] | AntiCheatValidator.js [ ]`.

### 11 MODULES row (line ~35) -- reflect scaffolding
- M01 SPAWN: `[x] -> [b]` (NeutralSpawnController coded + verified, NOT wired to real hub yet).
- M02 BUILDING: `[ ] -> [b]` (BuildingBase + SpellShop/DeckLab/MainTower stubs verified).
- M03 PVP_RAID: `[ ] -> [b]` (RaidController/ShieldSystem/DamageCalculator scaffolded).
- M04 CREW: `[ ] -> [~]` (CrewManager stub scaffolded; wraps live social.js).
- M05 SOCIAL_URGENCY: `[ ] -> [~]` (PushNotificationManager stub scaffolded).
- M06 ECONOMY: `[ ] -> [~]` (CurrencyManager/TokenSink stubs scaffolded).
- M11 WHITEOUT: `[ ] -> [~]` (MainTowerSystem/ReputationFlow stubs scaffolded).
- M07/M08/M09/M10: leave `[ ]` (not scaffolded).

### NEW checklist block to append under "NEXT ACTIONS"
```
## [ ] CORE WIRING (from AK_BUILD_PLAN.md, dependency order)
- [ ] W0.1 DataValidator: real schemas for raid.* / economy.* / crew.* (keep ok:true default)
- [ ] W0.2 ConfigLoader: load cost/shield/crew-cap tables -> emit config.ready
- [ ] W0.3 SaveLoadManager + AntiCheatValidator stubs (SHARED/, EventBus-only deps)
- [ ] W1.1 Wire NeutralSpawnController into REAL hub (port hub_proto 1/8s dwell, no auto-enter)
- [ ] W1.2 Finish BuildingBase HP/level/upgrade-timer + register 3 subclass instances in hub
- [ ] FIRST DEPLOY: walk hub -> enter existing battler via building:enterRequest -> index.html?go=match
- [ ] W2.1 RaidController shield-tier + damage + 24h-revenge math (Clash DNA)
- [ ] W2.2 CrewManager: roles + reinforcement queue + war registration + betrayal flag (wrap social.js)
- [ ] W3.1 CurrencyManager + TokenSink: ALK flows + 7 burn sinks + staking (Supabase ledger adapter)
- [ ] W3.2 SOCIAL_URGENCY: push + crew-chest timer + betrayal-log + flash-bonus (listener-only)
- [ ] W4.1 PROGRESSION: activate cardLvls field + prestige burn + milestones + match XP
- [ ] W4.2 WHITEOUT subsystems in order: HQ cap -> ReputationFlow -> help-timer -> war-lanes -> gear -> training -> DvD
- [ ] W5.1 LIVE_OPS event calendar + Reward-Flow orchestrator
- [ ] W5.2 CREATOR_ECONOMY 70/25/5 split + mint hooks
- [ ] W5.3 INTEGRATION adapter stubs (Unity / Blockchain / GooglePlay / AntiCheat wiring)
- [ ] ENGINE ADAPTER: emit match.start/match.win/match.lose/unit.* from engine.js (read-only bridge)
```

### Gaps cross-link (line ~38 block)
- Tie `anti-cheat/server-authority` gap to W0.3 + W5.3; tie `offline decay` gap to M11 ReputationFlow;
  tie `anti-whale` gap to M03 DamageCalculator (cap raid dmg vs lower levels).

---

## (3) INTEGRATION STORY -- how hub + raid + crew wrap the existing battler

The existing battler (engine.js + index.html canvas) is treated as ONE module behind ONE adapter.
We do not edit its combat sim. We add a thin, read-only ENGINE ADAPTER that:
- LISTENS to nothing it shouldn't, and EMITS the battler's facts onto the bus:
  `match.start`, `match.win`, `match.lose`, `unit.spawn`, `unit.death`. These already exist as
  internal state on window.AK; the adapter just publishes them [GAP M10 reuse: engine.js window.AK].
- That single bridge is the only contact point. Everything downstream (progression XP, crew war
  scoring, economy grants) consumes those events. The battler never learns who is listening.

### The hub wraps the battler (M01 + M02)
1. The hub canvas (ported from hub_proto.html v3) boots and M02 registers each building, emitting
   `building:registered{id,type,door,screen}`. M01's NeutralSpawnController learns door positions
   ONLY from these events -- it imports nothing [GAP M01/M02, CORE].
2. Player spawns in the neutral plaza (no auto-enter guaranteed by M01). On intentional dwell over
   the MainTower door, M01 emits `building:enterIntent{buildingId}`.
3. M02's MainTower hears the intent, validates state (not destroyed/under-siege), and emits
   `building:enterRequest{screen:'index.html?go=match'}`. The hub's renderer adapter performs the
   actual screen transition into the EXISTING battler. The battler launches unchanged.
4. On battle end, the engine adapter emits `match.win`/`match.lose`. The hub returns the player to
   the plaza. The wrap is complete: the battler is a room you walk into, not the whole app.

### The raid layer wraps it (M03)
- While the player is OFFLINE, M03 RaidController runs the SAME engine sim headless (engine.js is
  already headless-safe per [GAP foundation]) to resolve an attacker-vs-defender-deck raid, OR runs
  the lightweight DamageCalculator formula. It reads the defender's building state from M02, applies
  ShieldSystem rules (no-op while shielded), decays building stats, and emits `raid.result` +
  `crew.under_siege`. No battler code changes -- raid is a new consumer of the same sim contract.

### The crew layer wraps it (M04 + M05 + M11)
- M04 CrewManager WRAPS the live social.js (crew create/join/chat already shipping via the ak-crew
  edge fn) by subscribing to its events and adding war/reinforcement/betrayal state on top [GAP M04].
  It hears `crew.under_siege` from M03 and emits `crew.war.declared` / `crew.member.betrayed`.
- M05 SOCIAL_URGENCY is a pure listener: it hears `crew.under_siege` and fires the "BUDDY'S BASE IS
  BURNING" push, hears `crew.member.betrayed` and auto-composes the Traitor message into crew chat
  via social.js's existing mk() builder [GAP M05, BP come-on-buddy]. It produces no game state.
- M11 MainTowerSystem makes the MainTower building (an M02 subclass) the crew HQ: its level caps
  crew size (L1=5..L30=100) and ReputationFlow generates heat/hour that decays offline and is
  raidable by M03. War Lanes assign crew members (from M04 roster) to 3 arenas, each arena resolving
  through the same engine adapter. Card Gear modifies the card model engine.js already reads, using
  the handlers_data.js mods-resolver pattern [GAP M11].

### Why this is a wrap, not a rewrite
Every new layer touches the battler only through `match.*` / `unit.*` events emitted by one adapter,
and touches storage/Supabase/Stripe/Solana only through adapters. Re-platforming the renderer
(2D canvas -> 2.5D Phaser -> Unity) means writing a new RendererAdapter that performs screen
transitions and publishes the same events -- the hub, raid, crew, economy, and progression layers
never change [CORE adapter law, BP module-31, TODO platform-roadmap]. That is the whole point of the
EventBus spine: the done battler stays done.
