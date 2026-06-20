# ALLEY KINGZ CORE

The shared spine of the Alley Kingz ecosystem. This folder holds the small set
of cross-cutting modules that every layer (engine, shop, economy, social,
handlers, art, hub world) is allowed to depend on -- and the law that governs
how those layers talk to each other.

## The Architecture Law (non-negotiable)

1. **No module imports another module.**
   The engine does not `require`/`import` the shop. The shop does not import the
   economy. Nothing in a feature layer reaches into another feature layer's
   internals. The only shared code is what lives in `SHARED/`.

2. **All cross-module communication goes over the EventBus.**
   Modules publish facts (`bus.emit('match.win', payload)`) and subscribe to
   facts (`bus.on('match.win', fn)`). A publisher never knows who is listening;
   a listener never knows who published. This is the one and only contract
   surface between layers.

3. **Adapter pattern: port by swapping the integration adapter.**
   External systems (Supabase, Stripe, the art factory, Solana/`$BCARDD`,
   ElevenLabs, the maps CDN) are reached through a thin adapter that translates
   between the bus and the outside world. To re-platform an integration, you
   swap ONE adapter -- you do not touch any feature layer. Example: moving the
   shop ledger from localStorage to Supabase means rewriting the storage
   adapter that listens for `shop.purchase` and emits `shop.purchase.ok`;
   the engine, HUD, and economy code never change.

The payoff: every layer is independently testable, independently deployable,
and swappable. A layer can be rebuilt (2D canvas -> 2.5D Phaser -> 3D) without
rewriting its neighbors, because neighbors only ever saw events.

```
  +-----------+      emit/on        +-----------+      emit/on     +-----------+
  |  engine   | <-----------------> |  EventBus | <--------------> |   shop    |
  +-----------+                     +-----------+                  +-----------+
        ^                            ^   ^   ^                           ^
        |                            |   |   |                           |
   +---------+   +-----------+  +---------+  +-----------+   +----------------------+
   | economy |   |  social   |  |handlers |  |   art     |   | adapters (Supabase,  |
   +---------+   +-----------+  +---------+  +-----------+   | Stripe, Solana, CDN) |
                                                            +----------------------+
```

## What lives in SHARED/

| File                    | Status        | Responsibility                                                                 |
|-------------------------|---------------|--------------------------------------------------------------------------------|
| `EventBus.js`           | implemented   | Pub/sub nervous system: `emit` / `on` / `off` / `once`, wildcards, error-safe. |
| `DataValidator.js`      | implemented   | Validates event payloads against named schemas (raid.* / economy.* / crew.* / squad.*) before a module acts. Unregistered schema -> `ok:true` (never blocks a build). |
| `ConfigLoader.js`       | implemented   | Loads + caches the tunable cost / shield / crew-cap tables and announces them via `config.ready`. Getters: `costs()`, `shieldTiers()`, `buyableShields()`, `crewMemberCap(lvl)`. |
| `SaveLoadManager.js`    | implemented   | Bridges EventBus state <-> storage. localStorage now / Supabase later behind one swappable adapter. Listens `STATE_SAVE_REQUESTED` / `STATE_LOAD_REQUESTED`. |
| `AntiCheatValidator.js` | stub (server-authority gate) | Trust boundary for economic events. Client-side sanity bounds run now; marks values `trusted:false` until a server re-sim verifier is wired via `setVerifier()`. |

Each module imports NOTHING and is imported by NOTHING. They expose UMD-style
exports so they run in the browser (attach to `window`) and in Node/test
harnesses (`module.exports`) with no build step, matching the existing
`engine.js` / `canon.js` convention.

## EventBus quick reference

```js
// Browser: <script src="SHARED/EventBus.js"></script>
const bus = window.AK_EventBus;          // process-wide shared singleton

const off = bus.on('shop.purchase.ok', (payload, eventName) => {
  // react to the fact; never call back into the shop directly
});

bus.once('config.ready', cfg => boot(cfg));   // fires exactly once
bus.emit('shop.purchase.ok', { sku: 'gems_500', uid: 'u123' });
off();                                          // unsubscribe

// Wildcards:
bus.on('*', (p, name) => log(name, p));         // hears every event
bus.on('unit.*', onUnitEvent);                  // hears unit, unit.spawn, ...

// Isolated instance (tests):
const { EventBus } = require('./SHARED/EventBus.js');
const testBus = new EventBus();
```

### Guarantees

- **Error-safe.** A listener that throws is caught, reported via the `error`
  event and `console.error`, and never blocks the other listeners or the
  emitter. `emit()` returns the count of listeners that ran.
- **Order.** Exact-name listeners fire first (in subscription order), then
  matching `prefix.*` wildcards (longest prefix first), then the global `*`.
- **Re-entrancy safe.** Subscribing/unsubscribing from inside a handler is safe;
  emit works on a snapshot. `once` listeners detach before they are invoked, so
  a re-entrant emit cannot double-fire them.
- **Unsubscribe handles.** `on` and `once` return an unsubscribe function so you
  do not need to keep a reference to the listener.

## Event naming convention

Dot-namespaced, lowercase: `domain.action[.detail]`.

- `match.start`, `match.win`, `match.lose`
- `unit.spawn`, `unit.death`, `unit.spawn.ranged`
- `shop.purchase`, `shop.purchase.ok`, `shop.purchase.fail`
- `economy.grant`, `economy.spend`
- `config.ready`
- `error`  (reserved -- the bus emits this when a listener throws)

## Adding a new layer

1. Create the module under its own folder (outside `SHARED/`).
2. Take the bus from `window.AK_EventBus` (or inject one for tests).
3. Subscribe to the events you care about; emit the facts you produce.
4. Do NOT import any sibling layer. If you need data from another layer, that
   layer must emit it -- add the event to the contract above.
5. For anything external, write an adapter that bridges bus events to the
   outside system. Keep all I/O in the adapter so the layer stays pure.

## Brand + house rules

- Spell the brand **Alley Kingz** (with a Z) everywhere. Never "Alley Kings".
- No em-dash characters in code or docs; use `--` or `-`.
- Stubs stay minimal and JSDoc-documented until their contracts are frozen.
