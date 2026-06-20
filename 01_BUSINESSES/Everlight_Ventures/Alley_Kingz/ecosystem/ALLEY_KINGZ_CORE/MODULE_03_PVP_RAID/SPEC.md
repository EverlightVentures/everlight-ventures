# ALLEY KINGZ -- MODULE_03_PVP_RAID (build-ready spec)
**Clash-of-Clans DNA: offline base raids, shield economy, per-building stat loss, revenge chains.**
Date: 2026-06-19 | Status: SPEC + STUBS. Numbers are concrete and authoritative.

> Companion to AK_MASTER_BLUEPRINT.md (the WHAT/WHY) and ALLEY_KINGZ_TODO.md (the WHEN).
> Architecture law (see ../SHARED/EventBus.js): **no module imports another. Every
> cross-module conversation goes over the EventBus.** The three files in this module
> (ShieldSystem.js, DamageCalculator.js, RaidController.js) also talk only through the
> bus -- they never `require` one another. Swap the renderer or the backend behind an
> adapter and this raid logic is untouched.

================================================================
## 0. WHAT THIS MODULE OWNS (and what it does NOT)
================================================================
OWNS:
- Whether a base can be attacked right now (shield / guard state).
- How much damage a raid does (destruction %, per-building stat loss, loot stolen).
- What protection a defender earns after being hit (shield grant by destruction tier).
- Buyable shields and their purchase cooldowns.
- The 24h revenge window and revenge eligibility.
- The canonical `CREW_UNDER_SIEGE` siege signal (the social engine listens for it).

DOES NOT OWN (listens/emits across the bus, never reaches in):
- Crew membership, crew chat, push copy -> MODULE_04_CREW / MODULE_05_SOCIAL_URGENCY.
- Token/loot ledgers and burn sinks -> MODULE_06_ECONOMY.
- Long-idle base decay (>14d -5%/day, 30d auto-kick) -> MODULE_07_PROGRESSION.
- Matchmaking / who you get matched against -> MODULE_08_LIVE_OPS scout pool.
- Anti-cheat re-simulation of the battle -> SHARED/AntiCheatValidator.js.

================================================================
## 1. CORE LOOP (Clash of Clans, dog-gang reskin)
================================================================
A base is a set of buildings (Spell Shop, Deck Lab, Main Tower / Crew HQ, Stash House,
Kennel, Training Grounds). While the owner is OFFLINE and UNSHIELDED, another player can
scout and raid it. The raid produces a destruction percentage (0-100%). Destruction drives
three outcomes at once:
1. **Loot** stolen from the Stash House (economy event, capped, anti-whale).
2. **Per-building stat loss** on whatever the attacker actually destroyed.
3. **A defensive shield** auto-granted to the victim, sized by how badly they were hit.

The victim gets a 24h **revenge** window on the attacker. The attacker, by choosing to
raid, gives up their own shield/guard for that action (you cannot loot from behind a wall).

================================================================
## 2. SHIELD TIERS (auto-granted by destruction taken)
================================================================
After a raid resolves, the DEFENDER is automatically shielded. Bigger beating = longer
shield. Tier is chosen by the highest destruction threshold the attacker reached.

| Tier | Trigger (destruction taken) | Shield duration | Internal id |
|------|------------------------------|-----------------|-------------|
| T1   | >= 30% destroyed             | **12h**         | `def_30`    |
| T2   | >= 60% destroyed             | **14h**         | `def_60`    |
| T3   | >= 90% destroyed             | **16h**         | `def_90`    |

Rules:
- Below 30% destruction: **no shield** (a glancing raid does not protect you -- log in and
  defend). This is intentional Clash pressure.
- The granted shield NEVER shortens an existing longer shield. If the defender already
  holds a 16h shield and takes another raid worth T1 (12h), the 16h stands. Take the MAX.
- Shield grant is a fact emitted by RaidController (`raid.shield.grant.requested` with the
  destruction %); ShieldSystem owns the threshold table and decides the tier. The mapping
  lives in ONE place (SHIELD_TIERS in ShieldSystem.js) so balance changes are one edit.

================================================================
## 3. BUYABLE SHIELDS + PURCHASE COOLDOWNS
================================================================
A player can BUY peace. Each purchasable shield triggers a **cooldown** before that same
shield can be bought again -- the longer the shield, the longer you are locked out. This is
the Clash "personal break" anti-abuse mechanic that stops permanent turtling.

| Product        | Shield duration | Cost (ALK burn) | Re-purchase cooldown |
|----------------|-----------------|-----------------|----------------------|
| Short Cover    | **1 day**       | 100 ALK         | **4 days**           |
| Lockdown       | **2 days**      | 250 ALK         | **7 days**           |
| Deep Freeze    | **7 days**      | 700 ALK         | **35 days**          |

Cooldown semantics (`1d -> 4d`, `2d -> 7d`, `7d -> 35d`):
- The cooldown clock starts the MOMENT the shield is purchased, not when it expires. So a
  1-day buy locks the 1-day product for 4 days total (3 days after it lapses).
- Cooldowns are **per product**, tracked independently. Buying Short Cover does not lock
  Lockdown. (A whale could chain different tiers; the 35d Deep Freeze cooldown is the real
  governor and the ALK cost is the second governor.)
- ALK cost routes to MODULE_06_ECONOMY as a burn (emergency-shield sink). ShieldSystem does
  NOT touch the ledger -- it emits `raid.shield.purchase.ok` and economy debits/burns.
- A purchase is DENIED (with `raid.shield.purchase.denied`, reason `cooldown`) if the
  product is still cooling down; the payload carries `cooldownEndsAt` for the UI countdown.
- A bought shield stacks with a defensive shield by MAX duration, same rule as section 2.

================================================================
## 4. ATTACK-THROUGH-SHIELD PENALTY
================================================================
You may attack while you are personally shielded (you want loot now). Doing so does not pop
your shield, but it **burns hours off it** -- the price of breaking peace. The penalty scales
with the tier of shield you currently hold (a bigger shield costs more per swing).

| Shield you hold while attacking | Time removed per attack |
|---------------------------------|-------------------------|
| T1 (12h, `def_30` or Short Cover-class) | **-3h** |
| T2 (14h, `def_60` or Lockdown-class)    | **-4h** |
| T3 (16h, `def_90` or Deep Freeze-class) | **-5h** |

Rules:
- Penalty applies once per attack you LAUNCH, deducted immediately from your own remaining
  shield. It never goes below zero; if the deduction would zero it out, the shield ends and
  `raid.shield.expired` fires.
- The penalty is keyed off the holder's CURRENT highest tier, recomputed each attack (so as
  a 16h shield decays under -5h hits it does not silently drop to the -3h rate mid-session;
  it stays T3 until duration crosses the tier boundary, then re-rates down).
- Revenge attacks (section 6) are still attacks: taking revenge while shielded costs you the
  same -3h/-4h/-5h. Defending your own base (you did not launch) costs nothing.

Optional post-shield Guard (recommended, can ship in v2): when any shield expires, grant a
30-minute **Guard** during which the base cannot be raided but the player keeps full attack
freedom with no penalty. Stops the "wake up already raided" feel-bad. Events reserved:
`raid.shield.guard.started` / `raid.shield.guard.ended`.

================================================================
## 5. PER-BUILDING STAT-LOSS MATH
================================================================
A raid does not just chip a number -- it degrades the SYSTEM that building powers. When a
building is destroyed in a raid it drops its **stat percentage** by a fixed chunk (Clash
"100% -> 90%"), flooring so repeated raids cannot zero a player out in one shield cycle. The
loss is felt as a debuff on the linked game system until repaired.

| Building          | Powers (game system)        | Loss per raid | Floor | Linked debuff while degraded                |
|-------------------|-----------------------------|---------------|-------|---------------------------------------------|
| **Spell Shop**    | spell-card stock / power    | **-10%**      | 50%   | -10% spell cards available (the canon example) |
| **Deck Lab**      | card upgrade + deck XP gain | **-10%**      | 50%   | -10% deck XP, upgrade timers +10%           |
| **Main Tower**    | Crew HQ: reputation/hour    | **-8%**       | 40%   | -8% rep output/hr, crew earns less, poachable |
| **Stash House**   | loot vault (ALK/Gold/Scrap) | **-15% looted** | n/a | attacker steals up to the cap (see below)   |
| **Kennel**        | unit production rate        | **-10%**      | 50%   | -10% unit production, queued units lost      |
| **Training Grounds** | offline XP / gear accrual | **-10%**     | 50%   | -10% offline XP+gear claim                   |

Formula (per building the attacker actually destroys):
```
newStatPct = max(floor, currentStatPct - lossPerRaid)
```
- Only buildings reduced past their own destroy threshold (default 50% of building HP gone)
  count as "destroyed" and trigger their stat loss. A grazed building takes no stat loss.
- Loss is **per raid event**, not per percent. One raid that flattens the Spell Shop = a
  single -10%, regardless of overstomp. This keeps the math legible and the floor meaningful.
- **Repair / recovery** (owned by MODULE_07_PROGRESSION, we only emit the fact): stats
  regenerate on login at +5%/hr while online, or instantly via an ALK repair purchase. We
  emit `raid.building.damaged {buildingId, lossPct, newStatPct}`; progression schedules the
  heal. Raid module never mutates the heal timeline.

Stash House loot (anti-whale, MODULE_06 owns the ledger; we compute the request):
```
lootStolen = min( availableLoot * 0.15 * destructionFraction, perRaidCap )
```
- `destructionFraction` = destruction% / 100 (a 50% raid steals half of the 15% slice).
- `perRaidCap` is set by MODULE_08 matchmaking and SCALED DOWN when the attacker out-levels
  the defender (anti-whale directive). Raid module passes the cap through; it does not invent
  loot. Loot stolen leaves the defender and credits the attacker via two economy events.

================================================================
## 6. REVENGE (24h window)
================================================================
When you are raided, you may strike back at that specific attacker for **24 hours**.

- On every resolved raid, RaidController emits `raid.revenge.available {defenderId,
  attackerId, raidId, expiresAt}` where `expiresAt = now + 24h`.
- The window is per-raid: a fresh raid by the same attacker opens a NEW 24h window and
  refreshes the entry; multiple distinct attackers stack as independent revenge entries.
- Revenge is consumed by ONE successful counter-attack (`raid.revenge.requested ->
  raid.attack.resolved`); after that the entry closes. An unused window emits
  `raid.revenge.expired {raidId}` at the deadline.
- Revenge still respects shields: if the original attacker is now shielded, you either wait,
  or break your peace and eat the section-4 attack-through-shield penalty. You cannot raid a
  shielded base for free just because it is "revenge."
- Revenge raids follow ALL normal rules (destruction tiers grant the original attacker a
  defensive shield if you hit them hard enough -- the chain continues). This is the Coin
  Master / Dark War Survival revenge-chain retention hook.

================================================================
## 7. THE CANONICAL SIEGE SIGNAL: `CREW_UNDER_SIEGE`
================================================================
The blueprint names this exact event: *"RaidController emits CREW_UNDER_SIEGE -> CrewChat +
PushNotificationManager listen."* We honor that contract verbatim.

- Emitted by RaidController the instant a raid STARTS against a base whose owner is in a crew
  (not when it resolves -- the point is to rally the crew while there is still time to react
  with reinforcements / a donated shield).
- Payload: `{ defenderId, crewId, attackerId, raidId, baseSnapshotId, startedAt }`.
- Listeners (other modules, never imported): MODULE_04_CREW chat ("BUDDY'S BASE IS BURNING"),
  MODULE_05_SOCIAL_URGENCY push escalation, MODULE_04 reinforcement / emergency-shield-donate
  flow. Raid module fires the fact and forgets; it does not know who is listening.

================================================================
## 8. EVENT CONTRACT (the bus is the API)
================================================================
Naming: granular raid facts use the dot-namespaced `raid.*` house style (matches
SHARED/EventBus.js docs and its wildcard matching). The ONE cross-module rally signal keeps
its blueprint-mandated name `CREW_UNDER_SIEGE`. A subscriber can listen `raid.*` to hear
every raid fact for logging / anti-cheat.

INBOUND (this module subscribes):
| Event | Owner-listener | Payload |
|-------|----------------|---------|
| `raid.attack.requested`        | RaidController   | `{attackerId, defenderId, deck, targetBuildings, isRevenge?, originalRaidId?}` |
| `raid.revenge.requested`       | RaidController   | `{avengerId, originalRaidId}` (sugar that re-emits as an attack) |
| `raid.calc.requested`          | DamageCalculator | `{raidId, base, deck, seed}` |
| `raid.shield.grant.requested`  | ShieldSystem     | `{playerId, destructionPct, source:'defense'}` |
| `raid.shield.purchase.requested`| ShieldSystem    | `{playerId, product:'short'|'lockdown'|'deep'}` |
| `raid.attack.launched`         | ShieldSystem     | `{attackerId}` (to bill the attack-through-shield penalty) |

OUTBOUND (this module emits):
| Event | Emitter | Payload |
|-------|---------|---------|
| `CREW_UNDER_SIEGE`             | RaidController   | `{defenderId, crewId, attackerId, raidId, baseSnapshotId, startedAt}` |
| `raid.calc.result`             | DamageCalculator | `{raidId, destructionPct, perBuildingLoss:[{buildingId,lossPct,newStatPct}], lootRequest}` |
| `raid.attack.resolved`         | RaidController   | `{raidId, attackerId, defenderId, destructionPct, lootStolen, buildingsHit}` |
| `raid.building.damaged`        | RaidController   | `{defenderId, buildingId, lossPct, newStatPct}` (one per destroyed building) |
| `raid.revenge.available`       | RaidController   | `{defenderId, attackerId, raidId, expiresAt}` |
| `raid.revenge.expired`         | RaidController   | `{raidId}` |
| `raid.shield.activated`        | ShieldSystem     | `{playerId, tier, source, durationMs, expiresAt}` |
| `raid.shield.reduced`          | ShieldSystem     | `{playerId, hoursRemoved, remainingMs}` |
| `raid.shield.expired`          | ShieldSystem     | `{playerId}` |
| `raid.shield.purchase.ok`      | ShieldSystem     | `{playerId, product, costAlk, cooldownEndsAt}` (economy debits) |
| `raid.shield.purchase.denied`  | ShieldSystem     | `{playerId, product, reason, cooldownEndsAt?}` |

================================================================
## 9. ANTI-WHALE + SAFETY HOOKS (gaps the operator did not say but we cover)
================================================================
- **Anti-whale:** `perRaidCap` and a destruction haircut scale down when attacker level
  >> defender level. Raid module consumes the cap from matchmaking; it never lets a whale
  zero out a minnow. (Directive: "cap raid dmg vs lower levels.")
- **Regulatory:** raids are play-for-fun. ALK shield purchases route through ECONOMY which
  enforces geo-block + play-for-fun mode. Raid module emits intent only.
- **Anti-cheat:** the battle that produces `destructionPct` must be server-validated. The
  client may render a prediction; SHARED/AntiCheatValidator re-runs `seed + input-log` and
  the server destruction% is truth. DamageCalculator is deterministic (no `Math.random`;
  any jitter is drawn from the passed `seed`) precisely so this re-run is exact.
- **Offline decay** (>14d) is PROGRESSION's job, not raids. We do not double-penalize.

================================================================
## 10. FILES IN THIS MODULE
================================================================
- `SPEC.md`             -- this document.
- `ShieldSystem.js`     -- shield state, tiers, buyable shields + cooldowns, attack-through
                           penalty. Listens shield/attack events, emits shield facts.
- `DamageCalculator.js` -- pure, deterministic. destruction% + per-building stat loss +
                           loot request from a base snapshot + deck + seed. No state.
- `RaidController.js`   -- orchestrator. Turns an attack request into resolved facts, fires
                           `CREW_UNDER_SIEGE`, manages the 24h revenge window. Coordinates
                           ShieldSystem and DamageCalculator ONLY via the EventBus.

All three obtain the shared bus from `window.AK_EventBus` (browser) or
`require('../SHARED/EventBus.js')` (node/tests). They import the bus -- never each other.
