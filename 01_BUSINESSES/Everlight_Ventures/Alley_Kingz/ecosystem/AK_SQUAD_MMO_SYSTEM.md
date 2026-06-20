# ALLEY KINGZ -- SQUAD-MMO SYSTEM (canon; 2026-06-19)
> Companion to AK_MASTER_BLUEPRINT.md + AK_WORLD_BIBLE.md + AK_BUILD_PLAN.md + ALLEY_KINGZ_TODO.md.
> HARD RULE (same as the World Bible): do NOT genericize. "crew" never "clan", "squad" is the 2-5 strike unit INSIDE a crew, "graffiti" never "runes". Urban street culture, NeonReach canon.
> Architecture law (from AK_BUILD_PLAN + ALLEY_KINGZ_CORE/README): no module imports another; everything is an EventBus event contract; we WRAP the done battler, never rewrite it.

## THE VISION (operator's words)
A LIVING MMO, not solo instances. You do not walk NeonReach alone. You roll with a SQUAD -- your real friends, your ride-or-dies -- inside your CREW. You move as a pack, you fight from a SHARED table, you win and lose TOGETHER, and everything you do rolls up into ONE crew score the whole district can see. The battler is the done base; the squad is the social skin that turns "I logged in and played a match" into "the crew is online, get in here."

This is the layer that makes Alley Kingz "GTA of phone games" socially radioactive: not just clans you sit in, but a pack you literally walk and fight as.

---

## (1) PERSISTENT SQUADS
- A SQUAD is a persistent named sub-group INSIDE a crew. It is NOT a temporary matchmaking lobby -- it survives logout and shows in the crew roster.
- SIZE: 2-5 members. **Sweet spot = 3** (tuned for: the shared-table cognitive load, the diamond-formation read, and the role-chain math below). Solo play is always allowed; squad is opt-in.
- CREW-ONLY: every squad member must belong to the SAME crew. You cannot squad across crews (loyalty is the whole point -- World Bible: "your CREW is your life source"). Leaving the crew auto-removes you from your squad.
- 24h SWITCH COOLDOWN: leaving or swapping squads locks you out of joining/forming a new one for 24 hours. Stops squad-hopping to farm the best loot/event teammates; makes squad choice feel like commitment (loss-aversion, Coin Master DNA).
- LEADER: the squad founder is leader (crown marker). Leader can invite/kick, sets the active FORMATION (section 4), and confirms group building-entry. Leadership can be transferred (no cooldown on transfer, only on member churn).
- FORMATION/DISBAND emits `squad.formed{squadId,crewId,leaderId,members[]}` / `squad.disbanded`; role pick emits `squad.role.assigned{playerId,role}`. M04 CREW owns squad state; everything else listens.

---

## (2) THE 5 SQUAD ROLES (derived from the 10 player archetypes)
Each player picks ONE squad role. The 10 NeonReach archetypes (World Bible) collapse cleanly into 5 roles, 2 archetypes each. Role is a COMBAT modifier layer on top of the cards you bring -- it never changes your deck, it changes how your cards behave at the shared table.

| Squad Role | Archetypes (from the 10) | Battlefield job | COMBAT BONUS (applies to the shared pool in co-op combat) |
|---|---|---|---|
| **VANGUARD** | Brawler (tank) + Muscle (enforcer) | Frontline wall, soak, aggro | Front-line units get **+15% max-HP guard shield**; can **intercept** hits aimed at the backline. 2+ Vanguards in a squad = the shield stacks to +25% (the "wall"). |
| **MENDER** | Fixer (support) + Hype (morale) | Sustain, cleanse, morale | **+10% heal-over-time** to the shared pool + **one squad revive per match** (brings back one fallen card at 40% HP). Hype side adds a +5% attack-speed morale aura while above half pool HP. |
| **STRIKER** | Ghost (stealth) + Kid (rookie) | Flank, burst, execute | **+20% damage to targets below 40% HP** (the finisher) + flank bonus from off-formation. Charges the COMBO meter ~30% faster (eager-aggression). |
| **SNIPER** | Slinger (ranged) + Runner (scout) | Range, target priority, structures | **+25% damage to towers/buildings** and can **target the enemy backline directly** (bypass the wall). Runner side reveals one hidden enemy card at match start (intel). |
| **TACTICIAN** | Boss (leader) + Scribe (intel) | Command, draw, formation | Unlocks the **+1 extra shared-hand card** (6th card), can **re-deal** the shared hand once per match, sets/swaps FORMATION mid-match, and grants **+5% to ALL role-chain bonuses** in the squad. Only ONE Tactician benefit applies per squad (no stacking). |

**Role-chain rule:** roles are designed to combo. A Striker's execute lands harder when a Sniper has stripped the wall; a Vanguard's intercept buys the Mender time to revive. The Tactician amplifies whatever chains fire. See COMBO/SYNERGY/role-chain bonuses in section 4.

---

## (3) PACK OVERWORLD MOVEMENT
When a squad is online together, they move the NeonReach overworld as ONE pack (this is the "living MMO" read -- you SEE your crew walking with you, not ghosts in separate instances).
- **DIAMOND FORMATION:** the leader anchors front; members trail in a diamond that re-packs as the leader moves. Tap-to-move / WASD / joystick (per the live hub_proto v3 input stack) drives the leader; followers path-follow with light separation so they never overlap.
- **ROLE ICONS:** each pack member renders with their squad-role glyph (Vanguard shield, Mender cross, Striker blade, Sniper scope, Tactician crown-eye) floating above the avatar, so the crew reads its own composition at a glance.
- **LEADER CROWN:** the squad leader wears a crown marker (NeonReach gold-crown motif, reuse the crew-rep crown icon). Crown moves on leadership transfer.
- **BUILDING ENTRY = ALL CONFIRM:** walking the pack onto a building door does NOT auto-enter (respects the MODULE_01 no-auto-enter spawn law). The leader triggers an enter-intent; every online member gets a confirm prompt ("Enter Main Tower with the squad?"). The mode launches only when the squad reaches its confirm threshold (leader + majority, configurable via ConfigLoader). Members who decline stay in the plaza; the pack waits or splits at leader's call.
- **SCALES TO SQUAD SIZE:** a 2-pack is a tight pair (line, not diamond); a 5-pack is a full diamond + tail. Formation geometry, confirm threshold, and camera framing all interpolate by `squad.size`. A solo player is just a 1-pack (no formation overhead).
- Events: `pack.move{leaderPos,memberPos[]}` (throttled), `pack.formation.changed`, `building:enterIntent{buildingId,squadId}` (group variant of the M01 single-player intent), `squad.enter.confirm{playerId}` / `squad.enter.ready` -> M02 emits the existing `building:enterRequest`.

---

## (4) MULTI-DECK CO-OP COMBAT (the shared table)
The headline system. When a squad enters a combat mode together, they fight from a SHARED table instead of N separate boards. This is a NEW consumer of the existing engine sim via the engine adapter -- the battler's combat math is untouched; co-op is a table/hand orchestration layer on top.
- **SHARED ELIXIR/RESOURCE POOL:** 30 per player, pooled. A 3-squad fights off a 90-cap shared pool (regen scales with member count). Spending is first-come from the pool, so a greedy player can starve the squad -- intentional social tension (Betrayal Log fuel).
- **SHARED HAND:** 5 cards drawn from the COMBINED deck pool of all members, +1 extra card if the squad has a Tactician (6-card hand). The hand is visible to everyone; anyone can play any card if the pool can afford it. Next-card preview shown like the solo battler.
- **CARD ATTRIBUTION:** every card on the field is tagged with the player who PLAYED it (avatar pip + role glyph on the unit). This drives the post-match contribution breakdown (who carried, who leeched -- shame/glory, the "come on buddy" engine) and feeds per-player loot.
- **BONUS STACK (three layers, all surfaced as floating combat text):**
  1. **COMBO** -- same player plays a designed card sequence (existing engine synergy hooks). Personal skill expression.
  2. **SYNERGY** -- two DIFFERENT players play cards that pair (e.g. one drops a wall unit, another drops a buff behind it). Rewards coordination/voice.
  3. **ROLE-CHAIN** -- the squad-role bonuses interlock (Sniper strips wall -> Striker execute; Vanguard intercept -> Mender revive). Tactician adds +5% to every role-chain that fires. This is the deepest, highest-ceiling layer.
- **5 FORMATIONS** (Tactician sets/swaps; default for no-Tactician squads = Wedge). Each is a global field posture, not unit micro:
  | Formation | Shape | Effect |
  |---|---|---|
  | **Phalanx** | tight front line | +defense / +Vanguard guard; best vs aggro |
  | **Wedge** | arrow / spearhead | +push speed down one lane; best for a coordinated rush |
  | **Circle** | ring around the Mender/objective | +sustain uptime, protects the backline/healer |
  | **Skirmish** | spread, mobile | +flank/Striker bonus, harder to AoE; best vs clumped enemies |
  | **Blob** | everyone center mass | max burst + max COMBO/SYNERGY density, but punished by AoE (high risk/high reward) |
- Events: `coop.match.start{squadId,members[],poolCap}`, `coop.card.played{playerId,cardId,role}`, `coop.combo`, `coop.synergy{players[]}`, `coop.role_chain{chain,tactician:bool}`, `coop.formation.set{formation}`, `coop.match.result{perPlayerContribution[]}`. The engine adapter still emits `match.win/lose`; co-op just enriches the payload.

---

## (5) ENEMY + LOOT SCALING
- **ENEMY SCALING:** co-op encounters (PvE raids, event bosses, Gauntlet waves) scale HP/count/aggression to `squad.size` and average squad power so a 5-pack is not trivializing content a solo player sweats. PvP co-op matches against another squad are size-matched where possible (fall back to power-bracket + handicap if no equal squad queues).
- **EVERYONE GETS LOOT (hard rule):** loot is NOT split/diluted. Every participating member receives a FULL personal loot roll from the shared win, weighted by their attributed contribution (section 4) but with a floor so no one walks away empty (anti-resentment -- keeps friends inviting the rookie/Kid). Crew-tier bonus loot rolls for full-squad participation.
- Reuses economy.js LOOT/CHEST/SCRAP tables and the social.js grant pipeline; pays via the existing `ak_grants` rail (per the handler/Fortnite-layer doctrine -- reuse the grant rail, never bolt on a new one).
- Events: `loot.rolled{playerId,items[]}` per member, `loot.distributed{squadId}`, consumed by M06 ECONOMY (`economy.grant`).

---

## (6) MINI-TEAMS WITHIN THE CREW
Above the squad (the strike unit) sits a soft specialization layer: a crew sorts its members into MINI-TEAMS by what they're best at. A player can hold more than one. Each carries a TITLE (social currency, shown on profile + crew roster) and routes that member's contribution into the right slice of the crew score.
| Mini-team | Focus | Title | Feeds |
|---|---|---|---|
| **Tower Batters** | core tower-battler ladder / PvP wins | "Batter" | match score, ladder rank |
| **Raid Specialists** | offline raids + revenge + shield breaks (Clash DNA, M03) | "Raider" | raid score, buildings cracked |
| **Territory Warriors** | DvD + war-lane + district capture (M11) | "Warlord" | territory/war score, stipend held |
| **Economists** | ALK flows, marketplace, staking, crew-chest funding (M06) | "Banker" | economy score, treasury growth |
| **Social Connectors** | recruiting, onboarding rookies, chat morale, event mustering | "Connect" | retention/social score, mustered headcount |
- Mini-team is assigned by the crew leadership or self-claimed then ratified; it is a crew-org tool, distinct from the per-match SQUAD ROLE. (Squad role = how you fight a match; mini-team = what you do for the crew long-term.)
- Events: `crew.miniteam.assigned{playerId,team,title}`, contributions tagged with `team` so the crew score (section 7) can break down by lane.

---

## (7) MAJOR CREW EVENTS -> TOTAL CREW SCORE
Everything aggregates upward into ONE number: **TOTAL CREW SCORE.** Every match, raid, deal, capture, and event finish contributes a weighted slice. The crew score is the district-wide leaderboard rank, the prestige gate, and the public shame/glory board. Mini-teams (section 6) each own a slice; the events below are the recurring engines that pump it.

| Event | Cadence | What it is | Scores |
|---|---|---|---|
| **The Gauntlet** | WEEKLY | Escalating co-op wave survival for squads -- how deep can your pack push. The squad-MMO showcase mode (multi-deck table + formations + role-chains vs scaling waves). | Gauntlet depth -> crew score; weekly reset, per-squad leaderboard. |
| **Crew Games** | MONTHLY | Olympics-style multi-event tournament -- mini-events mapped to each mini-team (a batter bracket, a raid sprint, an economy challenge, a recruiting drive). Whole crew participates; medals tally. | Medal count -> big crew-score injection; inter-crew ranking. |
| **District vs District (DvD)** | MONTHLY | The Whiteout SvS war (M11): Hype -> Siege (capture Central Tower, hold 2.5h) -> Rebuild. Crew vs crew for district control + stipend. | War result + contribution -> crew score; winner = Supreme Crew + 2-week district buffs. |
| **Crew War Season** | QUARTERLY | The long arc -- a season-long ladder of war lanes + DvD results + Gauntlet bests, with a seasonal reset and a Season Champion crown. The "playoffs" over the monthly cadence. | Season standings -> the headline crew-score season rank + seasonal rewards/cosmetics. |
| **Ascension Ceremony** | ON PRESTIGE (event-framed) | The Crew Ascension prestige moment (World Bible 6-tier Bronze->Crown) staged as a CEREMONY the whole crew witnesses -- leader burns 500 ALK, buildings reset, the crew advances a visual tier. A status spectacle, not a quiet menu click. | Locks in the tier multiplier; permanent crew-score prestige bonus + ceremony cosmetics. |

- **TOTAL CREW SCORE** = weighted sum of match + raid + territory/war + economy + social/retention slices (one per mini-team), modulated by the Ascension tier multiplier. Decays slowly on inactivity (rep-decay DNA -- inactive crews fall the board).
- Events: `event.gauntlet.result`, `event.crewgames.result`, `event.dvd.result`, `event.season.standings`, `event.ascension.performed`, all -> `crew.score.updated{crewId,total,breakdown{match,raid,territory,economy,social},tier}`.

---

## (8) ARCHITECTURE / EVENTBUS TIE-INS (wrap, don't rewrite)
The squad-MMO system adds NO new combat math and NO edits to engine.js. It is orchestration + event contracts across existing modules:
- **M04 CREW** -- owns squad lifecycle (form/disband/role/cooldown/leader) and mini-team assignment. WRAPS the live social.js + ak-crew edge fn (squads are a new table/field on the crew model). Owns `squad.*`, `crew.miniteam.*`.
- **M01 SPAWN** -- pack overworld movement (diamond formation, role icons, leader crown, group enter-intent). Extends the NeutralSpawnController with a follower path-follow + the no-auto-enter group-confirm gate. Owns `pack.*`, the group `building:enterIntent`.
- **M02 BUILDING** -- group entry: same `building:enterRequest` it already emits, gated on `squad.enter.ready`.
- **ENGINE ADAPTER (M10)** -- the multi-deck co-op table is a new orchestration mode that feeds the SAME engine sim and consumes the same `match.*`/`unit.*` facts; it adds the shared-pool/shared-hand/attribution layer ABOVE the sim. Emits `coop.*`.
- **M06 ECONOMY** -- loot scaling + everyone-gets-loot via the `ak_grants` rail; consumes `loot.*`, emits `economy.grant`. Ascension burn (500 ALK) is the existing M06 sink.
- **M08 LIVE_OPS** -- the event calendar/orchestrator that fires Gauntlet (weekly), Crew Games (monthly), DvD (monthly), Season (quarterly), Ascension (on-prestige). Owns `event.*`.
- **M11 WHITEOUT** -- DvD, war lanes, war season, MainTower-as-HQ crew-size cap (which also caps how many squads a crew can field). Crew War Season is the seasonal wrapper over its war lanes.
- **M07 PROGRESSION** -- Ascension tier multiplier feeds the crew-score modulator.
- **Crew score** is a derived read-model: a listener that subscribes to `match.win`, `raid.result`, `event.*`, `economy.*` and recomputes `crew.score.updated`. No module writes the score directly.
- DataValidator schemas needed for the new high-traffic events: `squad.*`, `coop.card.played`, `pack.move` (throttle these), `loot.rolled`, `crew.score.updated`.

---

## (9) OPEN QUESTIONS / GAPS (account-for-what-I'm-not-saying)
- **Squad-vs-crew-size interplay:** MainTower level caps crew size (L1=5..L30=100); does it also cap squad COUNT, or just total members? Proposal: squads = floor(crewSize / 3), gated by tower level. Needs operator confirm.
- **Cross-crew co-op:** hard-banned for squads (loyalty). But do friend-of-friend "guest" slots exist for the Gauntlet only? Lean NO for V1 (keeps it crew-radioactive).
- **Pool-griefing safeguard:** shared 30/player pool can be hogged. Proposal: soft per-player spend cap that the Tactician can lift, + the Betrayal Log auto-flags a hogger. Needs balance pass.
- **Loot floor vs whales:** the no-empty-handed floor must not let a leech AFK-farm a carry's squad. Proposal: contribution floor requires a minimum cards-played / pool-spent threshold to qualify.
- **Realtime transport:** pack movement + shared table imply realtime sync (the social-layer P3 "realtime 2v2 on e5" milestone). V1 can ship async/ghost-pack (see cards) and turn-gated co-op; true realtime is the e5/Web3 milestone. Decide V1 fidelity.
- **Voice/proximity safety:** pack voice = the existing 12-gap voice-chat-safety item (proximity + automod). Tie squad voice to that gap.
