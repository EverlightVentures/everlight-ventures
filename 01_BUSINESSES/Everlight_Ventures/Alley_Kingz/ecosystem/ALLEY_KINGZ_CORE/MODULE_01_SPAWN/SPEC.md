# MODULE_01_SPAWN -- SPEC

> Part of the Alley Kingz 11-module EventBus architecture (see `AK_MASTER_BLUEPRINT.md`).
> Status: STUB. Owns where the player materializes in the walkable hub and the rule that
> NO building is auto-entered on load. Reference implementation of the feel: `game/hub_proto.html` (v3).

## 1. PURPOSE (the "spawn bug" fix, as a module)
The original hub bug: the player loaded straight INTO a building (auto-enter on the first frame).
MODULE_01_SPAWN exists so that can never happen again. Its whole job is three guarantees:

1. **Neutral plaza spawn.** The avatar materializes in an open plaza, deliberately kept clear of
   every building door. No door is within entry range of the spawn point.
2. **No auto-enter-on-load.** Entry can only fire AFTER the player has produced at least one
   movement input this session. On the load frame there is no input, so entry is impossible.
3. **Intentional building trigger.** Entry fires only when the player intentionally moves onto a
   door and holds there (proximity + a short dwell timer), exactly like `hub_proto.html`:
   `Math.hypot(dx, dy) < playerRadius + doorPadding` then `dwell > 0.125s` (1/8s, operator-tuned --
   1/2s felt too long). Leaving the door zone resets the dwell.

This module does NOT render anything, does NOT move the avatar, and does NOT open screens. It is the
decision brain. The host loop feeds it ticks; MODULE_02_BUILDING / the integration layer act on the
intent it emits.

## 2. ARCHITECTURE RULES (inherited from the blueprint)
- **No cross-module imports.** This file imports nothing. The EventBus is dependency-injected via the
  constructor (`new NeutralSpawnController(eventBus, config)`). It never reaches into MODULE_02 or any
  other module directly.
- **All comms via EventBus pub/sub.** It learns door positions from `building:registered` events
  (emitted by MODULE_02_BUILDING), not from a building reference.
- **Adapter-portable.** Pure logic, no DOM/canvas/Phaser/Three.js. Port by swapping the host loop that
  feeds `hub:tick`; the controller is untouched.
- **Boot ordering (load-bearing).** The bus does not replay. The integration layer must call
  `spawnController.init()` BEFORE any building calls `register()`, or the controller will miss the
  `building:registered` events and have no door table. Listeners before producers.

## 3. EVENT CONTRACT
Event naming convention across AK Core: `domain:eventName` (lowerCamel event).

### Listens (subscribes in `init()`)
| Event | Payload | Why |
|---|---|---|
| `building:registered` | `{ buildingId, door:{x,y}, radius, screen }` | Build the door table for proximity checks. |
| `building:deregistered` | `{ buildingId }` | Drop a door from the table (zone unload). |
| `hub:tick` | `{ dt, player:{x,y}, hasInput }` | Per-frame proximity + dwell evaluation. |
| `building:enterComplete` | `{ buildingId }` | Release the entry lock after a screen swap. |
| `building:enterCancelled` | `{ buildingId }` | Release the entry lock if entry was aborted/rejected. |

### Emits
| Event | Payload | When |
|---|---|---|
| `spawn:ready` | `{ x, y, zoneId }` | Once, after placing the avatar at the neutral plaza. |
| `building:enterIntent` | `{ buildingId }` | Dwell threshold crossed on a door AND player has moved this session. |
| `spawn:autoEnterBlocked` | `{ buildingId, reason }` | Telemetry: an entry was suppressed (e.g. before first input). |

### The decoupled entry chain
`SPAWN emits building:enterIntent` -> `MODULE_02_BUILDING validates + emits building:enterRequest`
-> `MODULE_10_INTEGRATION opens the real screen + emits building:enterComplete`. No module calls
another; each only hears the bus.

## 4. CONFIG (constructor `config`, all optional with proto-matched defaults)
| Key | Default | Meaning |
|---|---|---|
| `spawn` | `{ x:1300, y:1320, zoneId:'home' }` | Neutral plaza spawn point (proto plaza center). |
| `playerRadius` | `23` | Avatar collision radius (proto `me.r`). |
| `doorPadding` | `30` | Extra radius added to a door for the "near" test (proto value). |
| `dwellSeconds` | `0.125` | Hold time on a door before entry fires (proto 1/8s). |
| `requireInputBeforeEntry` | `true` | Hard no-auto-enter guard. Leave `true` in production. |

## 5. PUBLIC API
- `constructor(eventBus, config?)`
- `init()` -- subscribe to the bus, place the avatar, emit `spawn:ready`. Idempotent.
- `getSpawnPoint()` -> `{ x, y, zoneId }`
- `setSpawnPoint(point)` -- move the neutral spawn (e.g. Home Turf levels up).
- `isArmed()` -> boolean (has the player moved this session yet).
- `dispose()` -- unsubscribe, clear state.

## 6. TEST HOOKS (for the SHARED test harness)
- Spawn point is asserted to be farther than `playerRadius + doorPadding` from every registered door.
- Feeding `hub:tick` with `hasInput:false` sitting on a door must NEVER emit `building:enterIntent`
  (emits `spawn:autoEnterBlocked` instead). This is the regression test for the original spawn bug.
- After one `hasInput:true` tick, holding on a door for >= `dwellSeconds` emits exactly one
  `building:enterIntent`; the lock prevents a second until `building:enterComplete`/`Cancelled`.

## 7. OUT OF SCOPE (other modules)
Avatar art / walk cycle, camera, radar, fade-to-black transition, the actual screen open, raid state.
