// ==========================================================================
// ALLEY KINGZ CORE -- MODULE_03_PVP_RAID / DamageCalculator.js
// Pure, deterministic raid math: destruction %, per-building stat loss, and
// the loot-steal request from a base snapshot + attacker deck + seed.
//
// ARCHITECTURE LAW (see ../SHARED/EventBus.js): imports the shared EventBus
// ONLY. Never imports ShieldSystem or RaidController. Listens for
// raid.calc.requested, emits raid.calc.result. See ./SPEC.md section 5.
//
// DETERMINISM (anti-cheat, SPEC section 9): NO Math.random anywhere. Any
// jitter is drawn from the passed `seed` via a seedable PRNG so the server can
// re-run seed + input-log and reproduce the exact destruction %.
//
// STATUS: STUB. BUILDING_STAT_LOSS table is authoritative; math is TODO.
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Per-building stat-loss rules. A building only takes its loss once it is
   * "destroyed" (>= destroyThreshold of its HP gone). SPEC section 5.
   *   lossPct  -- stat percentage removed per raid event.
   *   floorPct -- repeated raids cannot push the stat below this.
   * @constant
   */
  var BUILDING_STAT_LOSS = {
    spell_shop:       { lossPct: 10, floorPct: 50, system: 'spell_cards' },
    deck_lab:         { lossPct: 10, floorPct: 50, system: 'deck_xp' },
    main_tower:       { lossPct: 8,  floorPct: 40, system: 'reputation' },
    kennel:           { lossPct: 10, floorPct: 50, system: 'unit_production' },
    training_grounds: { lossPct: 10, floorPct: 50, system: 'offline_xp' }
    // stash_house is loot, not a stat -- handled by lootRequest below.
  };

  /** A building counts as destroyed once this fraction of its HP is gone. */
  var DESTROY_THRESHOLD = 0.5;

  /** Stash House loot rule (SPEC section 5). Cap is supplied by matchmaking. */
  var LOOT_BASE_SLICE = 0.15;

  /**
   * Stateless raid-math service. One instance wires to the bus; the math
   * functions are pure and also exported for direct unit testing.
   *
   * @class
   * @param {Object} bus - EventBus instance (shared AK_EventBus singleton).
   */
  function DamageCalculator(bus) {
    if (!bus || typeof bus.on !== 'function') {
      throw new TypeError('DamageCalculator(bus) requires an EventBus');
    }
    this.bus = bus;
    this._unsubs = [];
    this._unsubs.push(bus.on('raid.calc.requested', this.onCalcRequested, this));
  }

  /**
   * Bus entry point: compute the result for a raid and emit raid.calc.result.
   * @param {{raidId:string, base:Object, deck:Object, seed:(number|string), lootCap:number}} req
   * @returns {void}
   */
  DamageCalculator.prototype.onCalcRequested = function (req) {
    var result = DamageCalculator.compute(req);
    this.bus.emit('raid.calc.result', result);
  };

  /**
   * Seedable PRNG (mulberry32). Deterministic so server re-runs match the
   * client. Folds a string/number seed to a uint32 first.
   * @param {(number|string)} seed
   * @returns {function():number} () -> float in [0,1)
   */
  DamageCalculator.rng = function (seed) {
    var a = (typeof seed === 'number') ? (seed >>> 0) : 0;
    if (typeof seed === 'string') {
      for (var i = 0; i < seed.length; i++) { a = (a * 31 + seed.charCodeAt(i)) >>> 0; }
    }
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  /**
   * PURE: produce the full raid result.
   * @param {Object} req
   * @param {string} req.raidId
   * @param {Object} req.base    - base snapshot {buildings:[{id, hp, maxHp, statPct}], loot}.
   * @param {Object} req.deck    - attacker deck (drives how much HP gets destroyed).
   * @param {(number|string)} req.seed - deterministic seed for any jitter.
   * @param {number} [req.lootCap=Infinity] - per-raid loot cap from matchmaking (anti-whale).
   * @returns {{raidId:string, destructionPct:number,
   *            perBuildingLoss:Array<{buildingId:string,lossPct:number,newStatPct:number}>,
   *            lootRequest:{amount:number}}}
   * @todo run the deterministic battle sim to get HP destroyed per building;
   *       derive destructionPct (weighted HP destroyed / total); for each
   *       building past DESTROY_THRESHOLD apply BUILDING_STAT_LOSS with floor;
   *       compute lootRequest = min(loot*LOOT_BASE_SLICE*frac, lootCap).
   */
  DamageCalculator.compute = function (req) {
    // STUB shape so listeners can be wired/tested before the sim lands:
    return {
      raidId: req && req.raidId,
      destructionPct: 0,
      perBuildingLoss: [],
      lootRequest: { amount: 0 }
    };
  };

  /**
   * PURE helper: apply one raid's stat loss to a building, honoring its floor.
   * @param {string} buildingId
   * @param {number} currentStatPct
   * @returns {{buildingId:string, lossPct:number, newStatPct:number}}
   */
  DamageCalculator.applyStatLoss = function (buildingId, currentStatPct) {
    var rule = BUILDING_STAT_LOSS[buildingId];
    if (!rule) return { buildingId: buildingId, lossPct: 0, newStatPct: currentStatPct };
    var next = Math.max(rule.floorPct, currentStatPct - rule.lossPct);
    return { buildingId: buildingId, lossPct: currentStatPct - next, newStatPct: next };
  };

  /**
   * Detach bus subscriptions. Call on teardown / hot-reload.
   * @returns {void}
   */
  DamageCalculator.prototype.destroy = function () {
    for (var i = 0; i < this._unsubs.length; i++) {
      try { this._unsubs[i](); } catch (_e) { /* ignore */ }
    }
    this._unsubs = [];
  };

  // expose config for tests / balance tooling
  DamageCalculator.BUILDING_STAT_LOSS = BUILDING_STAT_LOSS;
  DamageCalculator.DESTROY_THRESHOLD = DESTROY_THRESHOLD;
  DamageCalculator.LOOT_BASE_SLICE = LOOT_BASE_SLICE;

  // ---- export: UMD-style ----------------------------------------------------
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DamageCalculator: DamageCalculator };
  }
  if (typeof global !== 'undefined') {
    global.AK_DamageCalculator = DamageCalculator;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
