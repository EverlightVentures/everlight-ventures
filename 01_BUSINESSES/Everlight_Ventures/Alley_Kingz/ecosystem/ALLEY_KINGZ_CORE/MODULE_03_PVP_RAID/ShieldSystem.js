// ==========================================================================
// ALLEY KINGZ CORE -- MODULE_03_PVP_RAID / ShieldSystem.js
// Clash-of-Clans shield economy: defensive shields by destruction tier,
// buyable shields with per-product purchase cooldowns, and the
// attack-through-shield time penalty.
//
// ARCHITECTURE LAW (see ../SHARED/EventBus.js): this file imports the shared
// EventBus ONLY. It never imports DamageCalculator or RaidController. All
// coordination is facts on the bus. See ./SPEC.md sections 2, 3, 4.
//
// STATUS: STUB. Config tables below are authoritative (the real spec values);
// method bodies are wiring + TODO. No backend, no ledger touch.
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Defensive shield tiers, auto-granted to a DEFENDER by how badly they were
   * raided. Pick the highest threshold the attacker reached. Below 30% = none.
   * SPEC section 2. Durations in milliseconds.
   * @constant
   */
  var SHIELD_TIERS = [
    { id: 'def_90', minDestructionPct: 90, durationMs: 16 * 3600e3, penaltyHours: 5 },
    { id: 'def_60', minDestructionPct: 60, durationMs: 14 * 3600e3, penaltyHours: 4 },
    { id: 'def_30', minDestructionPct: 30, durationMs: 12 * 3600e3, penaltyHours: 3 }
  ];

  /**
   * Buyable shields. Cooldown is per-product and starts at purchase time
   * (not at expiry). SPEC section 3. `penaltyHours` mirrors the tier it maps
   * to for the attack-through-shield deduction (SPEC section 4).
   * @constant
   */
  var SHIELD_PRODUCTS = {
    short:    { durationMs: 1 * 86400e3, costAlk: 100, cooldownMs: 4 * 86400e3,  penaltyHours: 3 },
    lockdown: { durationMs: 2 * 86400e3, costAlk: 250, cooldownMs: 7 * 86400e3,  penaltyHours: 4 },
    deep:     { durationMs: 7 * 86400e3, costAlk: 700, cooldownMs: 35 * 86400e3, penaltyHours: 5 }
  };

  /** Optional post-shield Guard window (SPEC section 4). */
  var GUARD_MS = 30 * 60e3;

  /**
   * Owns shield state for every player and enforces the shield economy.
   *
   * Listens:
   *   raid.shield.grant.requested  {playerId, destructionPct, source}
   *   raid.shield.purchase.requested {playerId, product}
   *   raid.attack.launched         {attackerId}  (bills the through-shield penalty)
   * Emits:
   *   raid.shield.activated | raid.shield.reduced | raid.shield.expired
   *   raid.shield.purchase.ok | raid.shield.purchase.denied
   *
   * @class
   * @param {Object} bus - an EventBus instance (the shared AK_EventBus singleton).
   */
  function ShieldSystem(bus) {
    if (!bus || typeof bus.on !== 'function') {
      throw new TypeError('ShieldSystem(bus) requires an EventBus');
    }
    this.bus = bus;
    /** @type {Object<string,{tier:string,expiresAt:number,penaltyHours:number}>} */
    this._shields = Object.create(null);
    /** @type {Object<string,Object<string,number>>} playerId -> product -> cooldownEndsAt */
    this._cooldowns = Object.create(null);
    this._unsubs = [];
    this._wire();
  }

  /**
   * Subscribe to the bus. Each subscription handle is kept so destroy() can
   * cleanly detach (important for hot-reload and tests).
   * @private
   * @returns {void}
   */
  ShieldSystem.prototype._wire = function () {
    this._unsubs.push(this.bus.on('raid.shield.grant.requested', this.grantDefensive, this));
    this._unsubs.push(this.bus.on('raid.shield.purchase.requested', this.purchase, this));
    this._unsubs.push(this.bus.on('raid.attack.launched', this.applyAttackPenalty, this));
  };

  /**
   * Map a destruction percentage to a defensive tier (highest threshold met).
   * SPEC section 2.
   * @param {number} destructionPct - 0..100.
   * @returns {?Object} the SHIELD_TIERS entry, or null below 30%.
   */
  ShieldSystem.prototype.tierForDestruction = function (destructionPct) {
    for (var i = 0; i < SHIELD_TIERS.length; i++) {
      if (destructionPct >= SHIELD_TIERS[i].minDestructionPct) return SHIELD_TIERS[i];
    }
    return null;
  };

  /**
   * Grant a DEFENSIVE shield after a raid, sized by destruction taken.
   * Never shortens a longer existing shield (take the MAX). Emits
   * raid.shield.activated on grant.
   * @param {{playerId:string, destructionPct:number, source:string}} d
   * @returns {void}
   * @todo apply MAX-duration rule against existing shield; emit activated.
   */
  ShieldSystem.prototype.grantDefensive = function (d) {
    // STUB: var tier = this.tierForDestruction(d.destructionPct); if (!tier) return;
    // compute expiresAt; keep the later of existing vs new; store; emit activated.
    throw new Error('ShieldSystem.grantDefensive: not implemented (stub)');
  };

  /**
   * Buy a shield. Denies (reason 'cooldown') if the product is still cooling
   * down. On success, starts the product cooldown NOW and emits
   * raid.shield.purchase.ok so MODULE_06_ECONOMY can debit + burn the ALK.
   * @param {{playerId:string, product:('short'|'lockdown'|'deep')}} d
   * @returns {void}
   * @todo check _cooldowns, validate product, set cooldown, activate, emit ok/denied.
   */
  ShieldSystem.prototype.purchase = function (d) {
    // STUB: var p = SHIELD_PRODUCTS[d.product]; if (!p) emit denied 'bad_product';
    // if (now < cooldownEndsAt) emit denied 'cooldown' {cooldownEndsAt}; else activate.
    throw new Error('ShieldSystem.purchase: not implemented (stub)');
  };

  /**
   * Bill the attack-through-shield penalty against the ATTACKER's own shield
   * (-3h/-4h/-5h by their current tier). Floors at zero -> raid.shield.expired.
   * No-op if the attacker holds no shield. SPEC section 4.
   * @param {{attackerId:string}} d
   * @returns {void}
   * @todo look up holder tier, subtract penaltyHours, emit reduced or expired.
   */
  ShieldSystem.prototype.applyAttackPenalty = function (d) {
    // STUB: var s = this._shields[d.attackerId]; if (!s) return;
    // remaining -= penaltyHours; if <=0 expire+emit expired; else emit reduced.
    throw new Error('ShieldSystem.applyAttackPenalty: not implemented (stub)');
  };

  /**
   * Is this player currently protected from being raided?
   * @param {string} playerId
   * @param {number} [now=Date.now()]
   * @returns {boolean}
   */
  ShieldSystem.prototype.isShielded = function (playerId, now) {
    var s = this._shields[playerId];
    return !!(s && s.expiresAt > (now || Date.now()));
  };

  /**
   * Detach every bus subscription. Call on teardown / hot-reload.
   * @returns {void}
   */
  ShieldSystem.prototype.destroy = function () {
    for (var i = 0; i < this._unsubs.length; i++) {
      try { this._unsubs[i](); } catch (_e) { /* ignore */ }
    }
    this._unsubs = [];
  };

  // expose config for tests / balance tooling
  ShieldSystem.SHIELD_TIERS = SHIELD_TIERS;
  ShieldSystem.SHIELD_PRODUCTS = SHIELD_PRODUCTS;
  ShieldSystem.GUARD_MS = GUARD_MS;

  // ---- export: UMD-style, matches EventBus.js / engine.js convention --------
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ShieldSystem: ShieldSystem };
  }
  if (typeof global !== 'undefined') {
    global.AK_ShieldSystem = ShieldSystem;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
