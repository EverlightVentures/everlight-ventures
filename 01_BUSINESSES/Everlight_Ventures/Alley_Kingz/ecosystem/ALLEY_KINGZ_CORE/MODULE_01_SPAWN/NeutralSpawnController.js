/**
 * @file NeutralSpawnController.js
 * @module MODULE_01_SPAWN
 * @summary Alley Kingz walkable-hub spawn brain. Owns where the player materializes and
 *          guarantees no building is auto-entered on load. Entry only fires on an intentional
 *          move-and-dwell onto a door (the pattern proven in game/hub_proto.html v3).
 *
 * @description
 * STUB: decision logic only. It does NOT render, move the avatar, or open screens.
 * Architecture rules (see AK_MASTER_BLUEPRINT.md):
 *   - No cross-module imports. This file imports nothing.
 *   - The EventBus is dependency-injected (constructor) -- never reach into another module.
 *   - All comms via EventBus pub/sub. Door positions arrive as `building:registered` events.
 *
 * The three guarantees:
 *   1. Neutral plaza spawn (kept clear of every door).
 *   2. No auto-enter-on-load (entry requires at least one movement input this session).
 *   3. Intentional building trigger (proximity + dwell >= dwellSeconds, leaving resets dwell).
 *
 * @typedef {Object} EventBus
 * @property {(event:string, handler:Function)=>void} on    Subscribe.
 * @property {(event:string, handler:Function)=>void} [off] Unsubscribe (optional).
 * @property {(event:string, payload?:Object)=>void} emit   Publish.
 *
 * @typedef {Object} SpawnPoint
 * @property {number} x
 * @property {number} y
 * @property {string} zoneId
 */

/** @type {Required<SpawnControllerConfig>} Proto-matched defaults (see hub_proto.html). */
const DEFAULTS = {
  spawn: { x: 1300, y: 1320, zoneId: 'home' },
  playerRadius: 23,
  doorPadding: 30,
  dwellSeconds: 0.125,
  requireInputBeforeEntry: true,
};

/**
 * @typedef {Object} SpawnControllerConfig
 * @property {SpawnPoint} [spawn]                  Neutral plaza spawn point.
 * @property {number}     [playerRadius]           Avatar collision radius.
 * @property {number}     [doorPadding]            Extra radius for the "near a door" test.
 * @property {number}     [dwellSeconds]           Hold time on a door before entry fires.
 * @property {boolean}    [requireInputBeforeEntry] Hard no-auto-enter guard (keep true in prod).
 */
export class NeutralSpawnController {
  /**
   * @param {EventBus} eventBus Injected bus. The ONLY way this module talks to the world.
   * @param {SpawnControllerConfig} [config]
   */
  constructor(eventBus, config = {}) {
    /** @private */ this._bus = eventBus || null;
    /** @private */ this._cfg = { ...DEFAULTS, ...config };
    /** @private @type {SpawnPoint} */ this._spawn = { ...this._cfg.spawn };
    /** @private @type {Map<string, {door:{x:number,y:number}, radius:number, screen:string}>} */
    this._doors = new Map();
    /** @private Has the player produced movement input this session (defeats auto-enter). */
    this._hasMoved = false;
    /** @private Current dwell accumulator, in seconds, against `_dwellOn`. */
    this._dwell = 0;
    /** @private @type {?string} Building id the dwell timer is accruing against. */
    this._dwellOn = null;
    /** @private True while an entry is in flight (locked until complete/cancelled). */
    this._entering = false;
    /** @private Bound handlers, kept for dispose(). */
    this._h = null;
    /** @private */ this._inited = false;
  }

  /**
   * Subscribe to the bus, place the avatar at the neutral plaza, and announce it.
   * Idempotent. Emits `spawn:ready`.
   * @returns {void}
   */
  init() {
    if (this._inited) return;
    this._inited = true;
    this._h = {
      reg: (p) => this._onRegistered(p),
      dereg: (p) => this._doors.delete(p && p.buildingId),
      tick: (p) => this._onTick(p),
      done: () => { this._entering = false; this._resetDwell(); },
    };
    const on = this._bus && this._bus.on;
    if (on) {
      this._bus.on('building:registered', this._h.reg);
      this._bus.on('building:deregistered', this._h.dereg);
      this._bus.on('hub:tick', this._h.tick);
      this._bus.on('building:enterComplete', this._h.done);
      this._bus.on('building:enterCancelled', this._h.done);
    }
    this._emit('spawn:ready', { ...this._spawn });
  }

  /** @returns {SpawnPoint} A copy of the current neutral spawn point. */
  getSpawnPoint() { return { ...this._spawn }; }

  /**
   * Move the neutral spawn (e.g. Home Turf upgrades). Re-emits `spawn:ready`.
   * @param {SpawnPoint} point
   * @returns {void}
   */
  setSpawnPoint(point) {
    if (!point) return;
    this._spawn = { x: point.x, y: point.y, zoneId: point.zoneId || this._spawn.zoneId };
    this._emit('spawn:ready', { ...this._spawn });
  }

  /** @returns {boolean} Whether entry is allowed yet (player has moved this session). */
  isArmed() { return !this._cfg.requireInputBeforeEntry || this._hasMoved; }

  /** Unsubscribe and clear all state. @returns {void} */
  dispose() {
    const off = this._bus && this._bus.off;
    if (off && this._h) {
      this._bus.off('building:registered', this._h.reg);
      this._bus.off('building:deregistered', this._h.dereg);
      this._bus.off('hub:tick', this._h.tick);
      this._bus.off('building:enterComplete', this._h.done);
      this._bus.off('building:enterCancelled', this._h.done);
    }
    this._doors.clear();
    this._resetDwell();
    this._inited = false;
  }

  // --- internals ---------------------------------------------------------

  /**
   * @private
   * @param {{buildingId:string, door:{x:number,y:number}, radius:number, screen:string}} p
   */
  _onRegistered(p) {
    if (!p || !p.buildingId || !p.door) return;
    this._doors.set(p.buildingId, {
      door: { x: p.door.x, y: p.door.y },
      radius: typeof p.radius === 'number' ? p.radius : 0,
      screen: p.screen || '',
    });
  }

  /**
   * Per-frame evaluation. The whole no-auto-enter + intentional-trigger rule lives here.
   * @private
   * @param {{dt:number, player:{x:number,y:number}, hasInput:boolean}} p
   */
  _onTick(p) {
    if (!p || !p.player) return;
    if (p.hasInput) this._hasMoved = true;
    if (this._entering) return;

    const near = this._nearestDoor(p.player.x, p.player.y);

    // Not on a door -> reset the dwell and bail.
    if (!near) { this._resetDwell(); return; }

    // GUARD: never enter before the player has moved this session (kills auto-enter-on-load).
    if (this._cfg.requireInputBeforeEntry && !this._hasMoved) {
      this._emit('spawn:autoEnterBlocked', { buildingId: near, reason: 'no-input-yet' });
      this._resetDwell();
      return;
    }

    // Accrue dwell against the door the player is standing on.
    if (this._dwellOn !== near) { this._dwellOn = near; this._dwell = 0; }
    this._dwell += Math.max(0, p.dt || 0);

    if (this._dwell >= this._cfg.dwellSeconds) {
      this._entering = true;            // lock until enterComplete/Cancelled
      this._emit('building:enterIntent', { buildingId: near });
      this._resetDwell();
    }
  }

  /**
   * Nearest door whose (radius + playerRadius + doorPadding) contains the player.
   * @private
   * @returns {?string} buildingId or null.
   */
  _nearestDoor(px, py) {
    let best = null, bestD = Infinity;
    const pad = this._cfg.playerRadius + this._cfg.doorPadding;
    for (const [id, b] of this._doors) {
      const dx = px - b.door.x, dy = py - b.door.y;
      const d = Math.hypot(dx, dy);
      if (d < pad + b.radius && d < bestD) { best = id; bestD = d; }
    }
    return best;
  }

  /** @private */
  _resetDwell() { this._dwell = 0; this._dwellOn = null; }

  /** @private Safe emit (no-op without a bus). */
  _emit(event, payload) { if (this._bus && this._bus.emit) this._bus.emit(event, payload); }
}

export default NeutralSpawnController;
