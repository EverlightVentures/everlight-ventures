# MODULE_11_WHITEOUT -- The Urgency Backbone (SPEC)

> Alley Kingz core module. Whiteout Survival DNA: a central life-or-death object
> (Main Tower), heat that decays when you log off (Reputation), alliance
> dependency (Crew Help + War Lanes), and cross-server stakes (District vs
> District). This is the module that makes the game "socially radioactive" --
> friends beg each other to log in and hate each other for betraying the crew.
>
> Companion docs: `../../AK_MASTER_BLUEPRINT.md` (the WHAT/WHY) and
> `../../ALLEY_KINGZ_TODO.md` (the WHEN). This SPEC is the contract for M11.

---

## 0. Architecture Rules (non-negotiable)

1. **No module imports another module.** M11 never `import`s M02/M03/M04/etc.
   Every cross-module conversation is an EventBus publish/subscribe.
2. **The EventBus is injected**, not imported. The bootstrapper passes a single
   bus instance into each system's constructor. Stubs hold a reference; they do
   not reach across the module boundary.
3. **Adapter pattern for portability.** Rendering, storage, push, and chain
   calls go out as events; the M10 INTEGRATION adapters (WebGL today, Unity /
   Blockchain / Mobile / Google Play later) listen. Swapping an adapter leaves
   M11 untouched.
4. **Server-authoritative.** All economic numbers (Reputation balance, raid
   loot, war scores, gear rolls) are validated server-side. The client systems
   here are predictors / presenters; the server is the source of truth. M11
   emits intents; it never mints value on its own.
5. **Data separation.** Game-dynamic state (rep, caps, war scores) is distinct
   from business data. No PII flows through these events.

### Files in this module
| File | Role | Status |
|------|------|--------|
| `SPEC.md` | This contract | done |
| `MainTowerSystem.js` | Main Tower = Crew HQ; caps buildings + crew size | stub |
| `ReputationFlow.js` | Reputation generation / decay / raid / penalties | stub |
| `CrewHelpTimers.js` | "Call Crew" upgrade-timer shaving | planned |
| `CrewWarLanes.js` | 3-arena 5v5 alliance championship | planned |
| `DistrictWar.js` | Monthly District-vs-District (Hype/Siege/Rebuild) | planned |
| `CardGear.js` | 4-slot per-card gear (Frame/Gem/Aura/Finisher) | planned |
| `TrainingGrounds.js` | Offline auto-battle for XP + gear | planned |

---

## 1. Main Tower = Crew HQ (`MainTowerSystem.js`)

The Main Tower is the furnace. It is the single object that gates the entire
crew. It does two jobs: it **caps every other building** and it **caps crew
size**. Upgrading it is the social arms race -- a bigger tower means more
members and stronger buildings, so the crew pressures the leader to keep it
climbing.

### Caps
- **Building cap:** no building may exceed the Main Tower's level. A request to
  upgrade Building X to L(N) is rejected if N > towerLevel. (Enforced by M02
  BUILDING listening to the cap, not by M11 reaching into M02.)
- **Crew-size cap (anchor points, interpolate between):**

  | Tower Level | Max Crew Members |
  |-------------|------------------|
  | L1  | 5   |
  | L10 | 20  |
  | L30 | 100 |

  Between anchors, cap grows piecewise-linearly and rounds down:
  - L1->L10: +~1.67/level (5 -> 20 across 9 levels)
  - L10->L30: +4/level (20 -> 100 across 20 levels)

  The exact per-level table lives in config (`ConfigLoader`), not hardcoded, so
  Live Ops can re-tune without a code push. The anchors above are the contract.

### Behaviour
- Main Tower is **raidable while offline** (Clash-of-Clans DNA): a successful
  raid drops tower output / integrity, which cascades into Reputation
  generation. Damage math lives in M03 PVP_RAID; M11 only reacts to the result.
- Lowering the tower level (via repair-debt or a balance event) **cannot orphan
  members.** If a downgrade would push member count over the new cap, no member
  is auto-kicked; instead the crew is flagged `over_cap` and cannot recruit
  until back under. (Open question O-1 below.)

### Events
**Subscribes to**
- `TOWER_UPGRADE_REQUESTED` `{ crewId, byPlayerId, targetLevel }`
- `BUILDING_UPGRADE_REQUESTED` `{ crewId, buildingId, targetLevel }` -- vetoes if target > towerLevel
- `CREW_JOIN_REQUESTED` `{ crewId, playerId }` -- vetoes if at member cap
- `RAID_RESOLVED` `{ targetCrewId, buildingId:'main_tower', integrityDelta }`

**Publishes**
- `TOWER_LEVEL_CHANGED` `{ crewId, fromLevel, toLevel, memberCap, buildingCap }`
- `CREW_CAP_CHANGED` `{ crewId, memberCap }`
- `BUILDING_CAP_CHANGED` `{ crewId, buildingCap }`
- `BUILDING_UPGRADE_VETOED` `{ crewId, buildingId, reason:'tower_cap', cap }`
- `CREW_JOIN_VETOED` `{ crewId, playerId, reason:'member_cap', cap }`
- `TOWER_UNDER_SIEGE` `{ crewId, integrity }` (fan-out to push + crew chat)

---

## 2. Reputation Flow (`ReputationFlow.js`)

Reputation is the heat. The Main Tower **generates rep per hour**; rep **decays
when the crew goes dark**; rep is **raidable**; and dropping **below a level
threshold inflicts crew-wide penalties.** This is the loss-aversion engine.

### Generation
- `repPerHour = base[towerLevel] * (1 + crewHelpBonus) * raidIntegrityFactor`
  - `base[towerLevel]` from config (scales with tower level).
  - `crewHelpBonus` from active-member count (see Section 3, Training boost too).
  - `raidIntegrityFactor` = main-tower integrity / 100 (a damaged tower bleeds).
- Generation accrues into a stored balance, capped at a per-level storage cap
  (overflow is wasted -> nudges "log in and spend" urgency).

### Decay (offline)
- When the crew has **zero active members**, stored rep decays at
  `decayPerHour[towerLevel]` (config). Decay never drops rep below 0.
- A single active member halts decay (alliance dependency: "we need someone
  online"). This is the "come on buddy" hook -- the crew streak crisis push.

### Raidable
- A successful raid (M03) can **steal a capped slice** of stored rep:
  `stolen = min(storedRep * raidStealPct, raidStealAbsCap)`, with **anti-whale**
  scaling (attacker far above defender steals less). Numbers from config.
- Stolen rep is partially burned and partially credited to the attacker
  (mirrors the marketplace-fee burn philosophy; exact split in M06 ECONOMY).

### Below-threshold penalties
When `storedRep < threshold[towerLevel]` the crew enters **STARVED** state:
- Members **earn less** (currency/loot multiplier < 1.0, config).
- Members become **poachable** -- rival crews get a recruit ping (M04/M05).
- All buildings run at **-50% output** until rep recovers above threshold.
STARVED is sticky with hysteresis: it clears only when rep climbs a configurable
margin **above** the threshold (no flicker).

### Events
**Subscribes to**
- `TOWER_LEVEL_CHANGED` `{ crewId, toLevel }` -- rescale base/threshold/storage
- `CREW_PRESENCE_CHANGED` `{ crewId, activeCount }` -- start/stop decay
- `RAID_RESOLVED` `{ targetCrewId, type:'reputation', amount }` -- apply theft
- `CREW_HELP_APPLIED` `{ crewId, activeBonus }` -- adjust generation bonus
- `CLOCK_TICK` `{ now }` -- the accrual/decay heartbeat (driven by Live Ops clock adapter)

**Publishes**
- `REP_TICK` `{ crewId, storedRep, repPerHour, state }`
- `REP_THRESHOLD_BREACHED` `{ crewId, storedRep, threshold }` -> enter STARVED
- `REP_RESTORED` `{ crewId, storedRep, threshold }` -> exit STARVED
- `REP_RAIDED` `{ crewId, stolen, byCrewId }`
- `CREW_STARVED_PENALTY` `{ crewId, earnMult, buildingOutputMult, poachable:true }`

---

## 3. Crew Help Timers (`CrewHelpTimers.js`)

Alliance-help mechanic. A "Call Crew" button on any in-progress upgrade lets
crewmates shave the timer. Active crews finish faster, which compounds into
bigger towers, higher rep, and more wins -- the flywheel that punishes dead
crews.

- Each help from a distinct crewmate reduces the remaining timer by a fixed
  amount or percent (config), up to a **per-upgrade help cap**.
- Each helper has a **per-target cooldown** (can't spam-help one timer).
- Help requests broadcast to crew chat (urgency: "buddy needs a hand").
- Aggregate "active help" feeds `ReputationFlow.crewHelpBonus` and the Training
  Grounds boost.

**Subscribes:** `UPGRADE_STARTED`, `CREW_HELP_REQUESTED`, `CREW_HELP_GIVEN`
**Publishes:** `UPGRADE_TIMER_REDUCED { upgradeId, secondsShaved, remaining }`,
`CREW_HELP_APPLIED { crewId, activeBonus }`, `CREW_HELP_AVAILABLE { crewId, upgradeId }`

---

## 4. Crew War Lanes (`CrewWarLanes.js`)

The alliance championship. The recurring PvP event that creates strategy, blame,
and glory.

- **3 arenas, 5v5 each.** Three simultaneous lanes; five players from each crew
  per lane (15 players per crew committed overall).
- **Win 2 of 3 arenas** to win the war.
- **Rank-based fight order** inside each arena: players are seeded and clash in
  seed order, so a crew can stack or sandbag a lane deliberately.
- **Leader assigns players to arenas** -- the strategic lever. Good assignment =
  glory; a blown call = the crew remembers (ties into the Betrayal/MVP log, M05).
- **Decks lock at registration.** Once a player registers for the war, their
  deck is frozen for the duration -- no swapping to counter what you see.

**Subscribes:** `WAR_DECLARED`, `WAR_REGISTRATION_OPEN`, `PLAYER_REGISTERED_FOR_WAR`,
`ARENA_ASSIGNMENT_SET`, `BATTLE_RESOLVED`
**Publishes:** `DECK_LOCKED { playerId, deckHash }`, `ARENA_MATCH_READY { arena, seatA, seatB }`,
`ARENA_WON { warId, arena, crewId }`, `WAR_RESULT { warId, winnerCrewId, arenaScore }`

---

## 5. District vs District (DvD) Monthly War (`DistrictWar.js`)

Whiteout's SvS, ported. A monthly cross-district war in three phases. Highest
stakes in the game; a real-time contribution leaderboard turns it into public
shame and glory.

### Phase 1 -- Hype (5 days)
- **5 daily tasks** per player generate district contribution points.
- Builds the war chest and seeds the contribution leaderboard before any shots
  fire. (Reward Flow / Monopoly-GO cadence: every task points at the next.)

### Phase 2 -- Siege
- Goal: **capture the Central Tower and hold it for 2.5 hours.**
- **VIP buffs are OFF during Siege** -- the fairness window so whales can't
  simply buy the capture. Skill + coordination + numbers decide it.
- Holding the timer to zero = capture; contested holds reset / extend per config.

### Phase 3 -- Rebuild (24h window)
- A **24-hour repair window** to rebuild what the war broke.
- **Miss the window = permanent loss** (loss aversion at the district scale).

### Spoils
- **Winner = "Supreme Crew" title + district buffs for 2 weeks.**
- Real-time contribution leaderboard is public the whole time (glory + shame).

**Subscribes:** `DVD_SCHEDULED`, `HYPE_TASK_COMPLETED`, `SIEGE_TOWER_CAPTURED`,
`SIEGE_TOWER_LOST`, `CLOCK_TICK`
**Publishes:** `DVD_PHASE_CHANGED { warId, phase }`, `DVD_HYPE_POINTS { districtId, playerId, points }`,
`SIEGE_HOLD_TICK { warId, holderCrewId, secondsHeld }`, `SIEGE_CAPTURED { warId, crewId }`,
`REBUILD_WINDOW_OPEN { warId, closesAt }`, `REBUILD_MISSED { crewId, lostAssets }`,
`DVD_RESULT { warId, supremeCrewId, districtBuffsUntil }`

---

## 6. Card Gear (`CardGear.js`)

Per-card gear, Whiteout's hero-gear system mapped onto cards. Four slots per
card, each tuned to a different stat axis:

| Slot | Stat axis |
|------|-----------|
| **Frame** | attack + hp |
| **Ability Gem** | spell power |
| **Aura** | defense + hp |
| **Finisher** | crit |

- **Two gear systems by context:**
  - **Tower Battles** use gear levels **L1-5** (the core 3-5 min battler stays
    tight and readable).
  - **World Raids** unlock gear **L6+** (the deeper progression sink for the
    overworld / raid layer).
- Gear is rolled / upgraded server-side; M11 emits equip intents and presents
  the resulting stat deltas.

**Subscribes:** `GEAR_EQUIP_REQUESTED`, `GEAR_UNEQUIP_REQUESTED`, `GEAR_UPGRADED`,
`BATTLE_CONTEXT_SET { context:'tower'|'world_raid' }`
**Publishes:** `CARD_STATS_RECALCULATED { cardId, stats }`, `GEAR_EQUIPPED { cardId, slot, gearId }`,
`GEAR_EQUIP_VETOED { cardId, slot, reason }` (e.g. L6+ gear in a Tower Battle)

---

## 7. Training Grounds (`TrainingGrounds.js`)

The exploration / idle layer. Assign a deck and it **auto-battles offline** for
XP + gear, so logging off still moves you forward -- but logging in is always
better.

- Assign a deck to a Training slot; it grinds while you are away.
- **24h-offline "Boosted Claim":** stay gone up to ~24h and the accumulated
  reward gets a boost multiplier on claim (rewards return, punishes infinite AFK
  past the cap).
- **Crew members boost each other +10% per active member** (capped) -- alliance
  dependency again: an active crew trains faster.

**Subscribes:** `TRAINING_DECK_ASSIGNED`, `TRAINING_CLAIM_REQUESTED`,
`CREW_PRESENCE_CHANGED`, `CLOCK_TICK`
**Publishes:** `TRAINING_PROGRESS { slotId, xp, gearRolls }`,
`TRAINING_BOOSTED_CLAIM_READY { slotId, multiplier }`,
`TRAINING_CLAIMED { slotId, xp, gear }`

---

## 8. Shared Event Heartbeat & State

- A single `CLOCK_TICK` from the Live Ops clock adapter (M08/M10) drives every
  time-based accrual here (rep, decay, siege hold, training). M11 systems never
  run their own wall-clock timers -- testable + server-reconcilable.
- Persistent state per crew is owned by `SaveLoadManager` (SHARED) and reached
  via `STATE_LOAD_REQUESTED` / `STATE_SAVED` events, not direct file/db calls.
- Every inbound economic event is run past `AntiCheatValidator` (SHARED) before
  M11 trusts it; failures emit `ANTICHEAT_FLAGGED`.

### Canonical crew-state shape (M11 slice)
```
crew.whiteout = {
  towerLevel, memberCap, buildingCap,
  reputation: { stored, perHour, state /* 'OK'|'STARVED' */, threshold, storageCap },
  war:      { activeWarId|null, arenaAssignments, lockedDecks },
  dvd:      { warId|null, phase, hypePoints, siegeSecondsHeld },
  training: { slots: [ { slotId, deck, accruedXp, lastTickAt } ] }
}
```

---

## 9. Open Questions (for Lucrex / operator)
- **O-1 Downgrade-over-cap:** when a tower downgrade pushes members over the new
  cap, freeze recruiting (current spec) vs. soft-kick lowest-contributors? Spec
  says freeze; confirm.
- **O-2 Rep theft split:** burn vs. attacker-credit ratio on raided rep -- owned
  by M06 ECONOMY, needs a number.
- **O-3 War Lane size:** task fixed this at **3 arenas x 5v5** (15 committed per
  crew). Earlier blueprint shorthand said "15v15"; this SPEC treats 3x5v5 as the
  contract and 15v15 as the aggregate description.
- **O-4 Boosted-Claim curve:** exact 24h boost multiplier + whether it tapers
  past 24h or hard-caps.

## 10. Definition of Done (M11)
- [ ] All 7 systems implemented behind the event taxonomy above (no cross-module imports).
- [ ] Config-driven caps/curves (no hardcoded balance numbers in code).
- [ ] Server-authoritative validation on every economic event.
- [ ] Unit tests for cap math, rep generation/decay/threshold hysteresis, war
      best-of-3 resolution, siege hold timing, training boosted-claim.
- [ ] `ak_todo_sync.py` flips **M11 WHITEOUT** (dir + a `.js` present). [done on stub landing]
