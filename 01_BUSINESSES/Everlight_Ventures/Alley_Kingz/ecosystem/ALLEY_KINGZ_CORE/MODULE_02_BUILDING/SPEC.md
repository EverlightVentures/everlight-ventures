# MODULE_02_BUILDING -- SPEC

> Part of the Alley Kingz 11-module EventBus architecture (see `AK_MASTER_BLUEPRINT.md`).
> Status: STUB. Defines every interactable structure in the walkable hub: HP / stats / level / owner,
> raidable Clash-of-Clans DNA, and the door metadata the spawn module needs. `SpellShop`, `DeckLab`,
> and `MainTower` extend `BuildingBase`.

## 1. PURPOSE
A `BuildingBase` is the data + behavior contract for a single structure (Spell Shop, Deck Lab, Main
Tower, Arena, etc.). It:
- Holds the persistent state: `id`, `type`, `ownerId`, `level`, `hp`/`maxHp`, `stats`, `position`,
  `door`, `radius`, `screen`, `state`.
- Announces itself to the hub (`register()` -> `building:registered`) so MODULE_01_SPAWN learns the
  door position and the integration layer knows which screen it opens.
- Mediates entry: hears `building:enterIntent`, decides whether entry is allowed (a destroyed or
  under-siege building can reject), and emits `building:enterRequest`.
- Takes raid damage / shields / repairs / upgrades and emits state changes (Clash-of-Clans offline
  raid loop: no shield + attacked = lose building stats, e.g. 100% -> 90%).
- Serializes for save/load.

## 2. ARCHITECTURE RULES
- **No CROSS-module imports.** `BuildingBase.js` imports nothing. The EventBus is dependency-injected.
- **Intra-module inheritance IS allowed.** `SpellShop`/`DeckLab`/`MainTower` import `BuildingBase` from
  this same module (MODULE_02). The blueprint rule forbids reaching into a DIFFERENT module, not
  extending your own base class.
- **All comms via EventBus.** The raid module (MODULE_03) never calls `building.applyDamage()`
  directly -- it emits `raid:applyDamage`, and the matching building applies it to itself.
- **Adapter-portable.** Pure data/logic, no DOM/canvas/renderer. A renderer adapter draws from these
  fields; it is not part of this module.
- **Boot ordering (load-bearing).** The bus does not replay. Listeners that need `building:registered`
  (MODULE_01_SPAWN, the renderer) must subscribe BEFORE the integration layer calls `register()` on
  each building. Listeners before producers.

## 3. EVENT CONTRACT
Naming convention: `domain:eventName`.

### Listens (subscribed in `register()`, filtered to own `id`)
| Event | Payload | Action |
|---|---|---|
| `building:enterIntent` | `{ buildingId }` | If mine: validate, then emit `building:enterRequest` or `building:enterRejected`. |
| `raid:applyDamage` | `{ buildingId, amount, attackerId }` | If mine and unshielded: `applyDamage`. |
| `raid:applyShield` | `{ buildingId, durationMs }` | If mine: `applyShield`. |
| `building:repairRequest` | `{ buildingId, amount }` | If mine: `repair`. |
| `building:upgradeRequest` | `{ buildingId, level? }` | If mine: `setLevel`. |

### Emits
| Event | Payload | When |
|---|---|---|
| `building:registered` | `{ buildingId, type, door:{x,y}, radius, screen, ownerId, level }` | `register()`. |
| `building:deregistered` | `{ buildingId }` | `dispose()`. |
| `building:enterRequest` | `{ buildingId, screen }` | Entry approved. Integration layer opens the screen. |
| `building:enterRejected` | `{ buildingId, reason }` | Entry denied (e.g. `destroyed`, `underSiege`). |
| `building:stateChanged` | `{ buildingId, state, prev }` | Any `state` transition. |
| `building:damaged` | `{ buildingId, hp, maxHp, amount, attackerId }` | After `applyDamage`. |
| `building:destroyed` | `{ buildingId, attackerId }` | `hp` reached 0. |
| `building:repaired` | `{ buildingId, hp, maxHp, amount }` | After `repair`. |
| `building:leveled` | `{ buildingId, level, stats }` | After `setLevel`. |
| `building:shielded` | `{ buildingId, untilTs }` | After `applyShield`. |

### Decoupled entry chain
`MODULE_01 building:enterIntent` -> `BuildingBase building:enterRequest` ->
`MODULE_10_INTEGRATION` opens screen -> `building:enterComplete` (releases the spawn lock).

## 4. STATE MODEL
`state in { 'idle', 'shielded', 'underSiege', 'damaged', 'destroyed' }`.
- `idle`        full or partial HP, no active shield, not being raided.
- `shielded`    protected; `raid:applyDamage` is ignored until `untilTs`.
- `underSiege`  actively targeted (set by MODULE_03); may reject entry.
- `damaged`     hp below `maxHp` (informational; still enterable).
- `destroyed`   hp == 0; entry rejected; needs repair/rebuild.

## 5. CONFIG (constructor `config`)
| Key | Default | Meaning |
|---|---|---|
| `id` | required | Stable unique id (e.g. `'spell_shop'`). |
| `type` | `'generic'` | Subclasses set this (`'spell_shop'`, `'deck_lab'`, `'main_tower'`). |
| `label` | `id` | Display name. |
| `ownerId` | `null` | Player/crew owner; `null` = neutral/world. |
| `level` | `1` | 1..`maxLevel`. |
| `maxLevel` | `10` | Upgrade ceiling. |
| `maxHp` | `100` | Full HP. |
| `hp` | `maxHp` | Current HP. |
| `stats` | `{}` | Generic stat bag (output, defense, capacity ...). |
| `position` | `{x:0,y:0}` | World position of the building body. |
| `door` | `position` | Door front-bottom-center (proximity target for MODULE_01). |
| `radius` | `0` | Door footprint radius added to the spawn proximity test. |
| `screen` | `''` | The screen/route this building opens (consumed by integration). |

## 6. PUBLIC API
- `constructor(eventBus, config)`
- `register()` -- subscribe to the bus, emit `building:registered`. Idempotent.
- `enter()` -- validate + emit `building:enterRequest` / `building:enterRejected`.
- `applyDamage(amount, attackerId)` -- reduce hp, emit `building:damaged` (and `building:destroyed`).
- `repair(amount)` -- restore hp, emit `building:repaired`.
- `applyShield(durationMs)` -- set `shielded`, emit `building:shielded`.
- `setLevel(level)` -- clamp 1..maxLevel, recompute stats hook, emit `building:leveled`.
- `decay(amount)` -- offline/Reputation-Flow decay hook (MODULE_06/11 drives the cadence).
- `getState()` -> plain snapshot. `toJSON()` / `static fromJSON(eventBus, data)`.
- `dispose()` -- unsubscribe, emit `building:deregistered`.

### Subclass hook
`_statsForLevel(level)` -> stat bag. Override per building so `setLevel` recomputes correctly.
Base returns the configured `stats` unchanged.

## 7. SUBCLASSES (this module)
| Class | type | Opens (screen) | Notes |
|---|---|---|---|
| `SpellShop` | `spell_shop` | `shop/shop.html` | Sells spells/items. Output stat = restock quality. |
| `DeckLab` | `deck_lab` | `shop/shop.html#deck` | Deck builder + handlers. Capacity stat = deck slots. |
| `MainTower` | `main_tower` | `index.html?go=match` | Crew HQ / furnace (Whiteout DNA, MODULE_11). Caps crew size by level; generates Reputation Flow; the apex raid target. |

## 8. TEST HOOKS
- `applyDamage` while `shielded` is a no-op (Clash shield rule).
- `applyDamage` to 0 -> `state==='destroyed'` + one `building:destroyed`.
- `enter()` on a destroyed building emits `building:enterRejected`, never `building:enterRequest`.
- `register()` emits a `building:registered` whose `door`/`radius` MODULE_01 can consume.
- `toJSON()` round-trips through `fromJSON()`.

## 9. OUT OF SCOPE (other modules)
Raid scheduling/matchmaking + shield economy (M03), the ALK economy + decay cadence (M06/M11),
rendering, and the actual screen open (M10). This module only holds state and speaks the bus.
