/**
 * @file BuildingBase.js
 * @module MODULE_02_BUILDING
 * @summary Alley Kingz base class for every interactable hub structure. Holds HP / stats / level /
 *          owner, mediates intentional entry, and takes raid damage / shields / repairs (Clash-of-
 *          Clans offline-raid DNA). SpellShop / DeckLab / MainTower extend this.
 *
 * @description
 * STUB: state + behavior contract only. No rendering, no screen opening, no raid scheduling.
 * Architecture rules (see AK_MASTER_BLUEPRINT.md):
 *   - No CROSS-module imports. This file imports nothing; the EventBus is dependency-injected.
 *   - Intra-module subclasses (SpellShop/DeckLab/MainTower) may import THIS base.
 *   - All comms via EventBus pub/sub. The raid module emits `raid:applyDamage`; the matching
 *     building applies it to itself (no direct cross-module call).
 *
 * @typedef {Object} EventBus
 * @property {(event:string, handler:Function)=>void} on
 * @property {(event:string, handler:Function)=>void} [off]
 * @property {(event:string, payload?:Object)=>void} emit
 *
 * @typedef {('idle'|'shielded'|'underSiege'|'damaged'|'destroyed')} BuildingState
 *
 * @typedef {Object} BuildingConfig
 * @property {string} id                       Stable unique id (required).
 * @property {string} [type='generic']         Building type (subclasses set this).
 * @property {string} [label]                  Display name (defaults to id).
 * @property {?string} [ownerId=null]          Player/crew owner; null = neutral/world.
 * @property {number} [level=1]                Current level.
 * @property {number} [maxLevel=10]            Upgrade ceiling.
 * @property {number} [maxHp=100]              Full HP.
 * @property {number} [hp]                     Current HP (defaults to maxHp).
 * @property {Object} [stats={}]               Generic stat bag.
 * @property {{x:number,y:number}} [position]  World position of the body.
 * @property {{x:number,y:number}} [door]      Door front-bottom-center (MODULE_01 proximity target).
 * @property {number} [radius=0]               Door footprint radius for the spawn proximity test.
 * @property {string} [screen='']              Screen/route this building opens.
 */
export class BuildingBase {
  /**
   * @param {EventBus} eventBus Injected bus. The ONLY way this module talks to the world.
   * @param {BuildingConfig} config
   */
  constructor(eventBus, config = {}) {
    if (!config.id) throw new Error('BuildingBase: config.id is required');
    /** @private */ this._bus = eventBus || null;

    /** @type {string} */ this.id = config.id;
    /** @type {string} */ this.type = config.type || 'generic';
    /** @type {string} */ this.label = config.label || config.id;
    /** @type {?string} */ this.ownerId = config.ownerId != null ? config.ownerId : null;

    /** @type {number} */ this.maxLevel = config.maxLevel != null ? config.maxLevel : 10;
    /** @type {number} */ this.level = this._clamp(config.level != null ? config.level : 1, 1, this.maxLevel);

    /** @type {number} */ this.maxHp = config.maxHp != null ? config.maxHp : 100;
    /** @type {number} */ this.hp = config.hp != null ? this._clamp(config.hp, 0, this.maxHp) : this.maxHp;

    /** @type {Object} */ this.stats = { ...(config.stats || {}) };

    /** @type {{x:number,y:number}} */ this.position = { x: 0, y: 0, ...(config.position || {}) };
    /** @type {{x:number,y:number}} */ this.door = config.door
      ? { x: config.door.x, y: config.door.y }
      : { x: this.position.x, y: this.position.y };
    /** @type {number} */ this.radius = config.radius != null ? config.radius : 0;
    /** @type {string} */ this.screen = config.screen || '';

    /** @type {BuildingState} */ this.state = this.hp <= 0 ? 'destroyed' : (this.hp < this.maxHp ? 'damaged' : 'idle');
    /** @private Timestamp (ms epoch) the active shield expires, or 0. */ this._shieldUntil = 0;
    /** @private */ this._h = null;
    /** @private */ this._registered = false;
  }

  /**
   * Subscribe to the bus and announce this building. Idempotent. Emits `building:registered`.
   * @returns {void}
   */
  register() {
    if (this._registered) return;
    this._registered = true;
    this._h = {
      intent: (p) => { if (this._mine(p)) this.enter(); },
      dmg: (p) => { if (this._mine(p)) this.applyDamage(p.amount, p.attackerId); },
      shield: (p) => { if (this._mine(p)) this.applyShield(p.durationMs); },
      repair: (p) => { if (this._mine(p)) this.repair(p.amount); },
      upgrade: (p) => { if (this._mine(p)) this.setLevel(p.level != null ? p.level : this.level + 1); },
    };
    if (this._bus && this._bus.on) {
      this._bus.on('building:enterIntent', this._h.intent);
      this._bus.on('raid:applyDamage', this._h.dmg);
      this._bus.on('raid:applyShield', this._h.shield);
      this._bus.on('building:repairRequest', this._h.repair);
      this._bus.on('building:upgradeRequest', this._h.upgrade);
    }
    this._emit('building:registered', {
      buildingId: this.id, type: this.type, door: { ...this.door },
      radius: this.radius, screen: this.screen, ownerId: this.ownerId, level: this.level,
    });
  }

  /**
   * Validate and request entry. A destroyed or under-siege building rejects.
   * Emits `building:enterRequest` or `building:enterRejected`.
   * @returns {boolean} Whether entry was approved.
   */
  enter() {
    if (this.state === 'destroyed') { this._emit('building:enterRejected', { buildingId: this.id, reason: 'destroyed' }); return false; }
    if (this.state === 'underSiege') { this._emit('building:enterRejected', { buildingId: this.id, reason: 'underSiege' }); return false; }
    this._emit('building:enterRequest', { buildingId: this.id, screen: this.screen });
    return true;
  }

  /**
   * Apply raid damage. Ignored while shielded (Clash shield rule).
   * Emits `building:damaged`, and `building:destroyed` if HP hits 0.
   * @param {number} amount
   * @param {?string} [attackerId]
   * @returns {void}
   */
  applyDamage(amount, attackerId = null) {
    if (this.isShielded()) return;
    const dmg = Math.max(0, Number(amount) || 0);
    if (dmg === 0) return;
    this.hp = this._clamp(this.hp - dmg, 0, this.maxHp);
    this._emit('building:damaged', { buildingId: this.id, hp: this.hp, maxHp: this.maxHp, amount: dmg, attackerId });
    if (this.hp <= 0) { this._setState('destroyed'); this._emit('building:destroyed', { buildingId: this.id, attackerId }); }
    else { this._setState('damaged'); }
  }

  /**
   * Restore HP. Emits `building:repaired`.
   * @param {number} amount
   * @returns {void}
   */
  repair(amount) {
    const heal = Math.max(0, Number(amount) || 0);
    if (heal === 0) return;
    this.hp = this._clamp(this.hp + heal, 0, this.maxHp);
    this._emit('building:repaired', { buildingId: this.id, hp: this.hp, maxHp: this.maxHp, amount: heal });
    this._setState(this.hp >= this.maxHp ? 'idle' : 'damaged');
  }

  /**
   * Activate a protective shield for `durationMs`. Emits `building:shielded`.
   * @param {number} durationMs
   * @returns {void}
   */
  applyShield(durationMs) {
    const ms = Math.max(0, Number(durationMs) || 0);
    this._shieldUntil = Date.now() + ms;
    this._setState('shielded');
    this._emit('building:shielded', { buildingId: this.id, untilTs: this._shieldUntil });
  }

  /** @returns {boolean} Whether a shield is currently active. */
  isShielded() { return this.state !== 'destroyed' && Date.now() < this._shieldUntil; }

  /**
   * Set the level (clamped 1..maxLevel), recompute stats via the subclass hook.
   * Emits `building:leveled`.
   * @param {number} level
   * @returns {void}
   */
  setLevel(level) {
    this.level = this._clamp(Number(level) || this.level, 1, this.maxLevel);
    this.stats = { ...this.stats, ...this._statsForLevel(this.level) };
    this._emit('building:leveled', { buildingId: this.id, level: this.level, stats: { ...this.stats } });
  }

  /**
   * Offline / Reputation-Flow decay hook. MODULE_06/11 drives the cadence; this just applies it.
   * @param {number} amount HP to shave.
   * @returns {void}
   */
  decay(amount) { if (!this.isShielded()) this.applyDamage(amount, 'decay'); }

  /**
   * Stat recompute hook. Override per building so `setLevel` scales correctly.
   * @protected
   * @param {number} _level
   * @returns {Object} Stat bag to merge.
   */
  _statsForLevel(_level) { return this.stats; }

  /** @returns {Object} A plain snapshot (no bus, no handlers). */
  getState() {
    return {
      id: this.id, type: this.type, label: this.label, ownerId: this.ownerId,
      level: this.level, maxLevel: this.maxLevel, hp: this.hp, maxHp: this.maxHp,
      stats: { ...this.stats }, position: { ...this.position }, door: { ...this.door },
      radius: this.radius, screen: this.screen, state: this.state, shieldUntil: this._shieldUntil,
    };
  }

  /** @returns {Object} Serializable form (alias of getState for SaveLoadManager). */
  toJSON() { return this.getState(); }

  /**
   * Rebuild a building from a serialized snapshot.
   * @param {EventBus} eventBus
   * @param {Object} data Output of toJSON()/getState().
   * @returns {BuildingBase}
   */
  static fromJSON(eventBus, data) {
    const b = new this(eventBus, data);
    if (data && typeof data.shieldUntil === 'number') b._shieldUntil = data.shieldUntil;
    if (data && data.state) b.state = data.state;
    return b;
  }

  /** Unsubscribe and announce removal. Emits `building:deregistered`. @returns {void} */
  dispose() {
    if (this._bus && this._bus.off && this._h) {
      this._bus.off('building:enterIntent', this._h.intent);
      this._bus.off('raid:applyDamage', this._h.dmg);
      this._bus.off('raid:applyShield', this._h.shield);
      this._bus.off('building:repairRequest', this._h.repair);
      this._bus.off('building:upgradeRequest', this._h.upgrade);
    }
    this._registered = false;
    this._emit('building:deregistered', { buildingId: this.id });
  }

  // --- internals ---------------------------------------------------------

  /** @private */ _mine(p) { return p && p.buildingId === this.id; }

  /** @private Transition state and emit `building:stateChanged` on a real change. */
  _setState(next) {
    if (next === this.state) return;
    const prev = this.state;
    this.state = next;
    this._emit('building:stateChanged', { buildingId: this.id, state: next, prev });
  }

  /** @private */ _clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  /** @private Safe emit (no-op without a bus). */
  _emit(event, payload) { if (this._bus && this._bus.emit) this._bus.emit(event, payload); }
}

export default BuildingBase;
