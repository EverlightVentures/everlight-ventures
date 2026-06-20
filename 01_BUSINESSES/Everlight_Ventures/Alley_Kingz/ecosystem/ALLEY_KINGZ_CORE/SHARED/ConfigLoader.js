// ==========================================================================
// ALLEY KINGZ CORE -- SHARED / ConfigLoader.js
// Loads + caches ecosystem config (tunable cost / shield / crew-cap tables,
// feature flags, endpoints) and announces it on the EventBus.
//
// ARCHITECTURE LAW (see ../README.md):
//   This module imports NOTHING and is imported by NOTHING. It is the ONE
//   place that knows where config lives. It loads, normalizes, and then EMITS
//   "config.ready" with the resolved object. Every other module learns its
//   tunables by listening for that event or reading get()/costs()/shieldTiers()/
//   crewMemberCap() here -- never by hardcoding balance numbers.
//   Swap the source (built-in defaults -> remote JSON -> Supabase flags) by
//   changing ONLY this loader; downstream modules never notice.
//
// STATUS: Wave-0 real implementation. Ships the LOCKED balance tables baked in
//   as AK_CONFIG_DEFAULTS so a running build always has real tunables even with
//   no external source. load() deep-merges:  defaults <- opts.defaults <-
//   opts.overrides  and then emits "config.ready" with the resolved config.
//   The numbers trace to the module SPEC.md tables (MODULE_03 / MODULE_06 /
//   MODULE_11) and AK_MASTER_BLUEPRINT.md "TOKEN ECONOMY (ALK)".
//
// API:
//   load(opts) -> Promise<config>     also emits "config.ready"
//   get(key, fallback)                dotted read ("shields.postShieldGuardMin")
//   all()                             whole resolved config
//   isLoaded()                        has load() completed once
//   costs()                           the 7 burn-sink cost table (economy.sinks)
//   shieldTiers()                     defensive shield tier table
//   buyableShields()                  purchasable shield products + cooldowns
//   crewMemberCap(towerLevel)         interpolated max crew size for a tower lvl
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * The LOCKED, tunable ecosystem balance tables. These are the contract
   * defaults; Live Ops re-tunes by supplying overrides to load(), never by
   * editing game-logic code. No balance number lives in a feature module.
   * @const {Object}
   */
  var AK_CONFIG_DEFAULTS = {
    // ---- MODULE_06_ECONOMY: ALK cost / sink / staking tables ----
    economy: {
      // The 7 burn sinks (AK_MASTER_BLUEPRINT.md token-economy; M06 SPEC sec 2).
      sinks: {
        prestige: 500,            // M07 prestige reset           (100% burn)
        warPerMember: 200,        // M04 war declaration / member (100% burn)
        shield: 100,              // M03 emergency shield         (100% burn)
        relocate: 150,            // M02 building relocation      (100% burn)
        reroll: 50,               // M09 cosmetic reroll          (100% burn)
        mint: 25,                 // M09 creator mint             (100% burn)
        marketplaceFeePct: 5      // M09 marketplace fee (split below)
      },
      // Only the marketplace sink splits (FEE_BPS=250 / ROYALTY_BPS=250).
      marketplaceSplit: { burnPct: 2.5, stakerPct: 2.5 },
      staking: { lockDays: 30, epoch: 'weekly' },
      deflation: { inflationTargetPctPerMonth: 2, stakedTargetPct: 40 },
      dailyEmissionCap: 2000      // farmed-inflow ceiling; paid IAP bypasses it
    },

    // ---- MODULE_03_PVP_RAID: shield + raid math tables ----
    shields: {
      // Auto-granted defensive tiers, chosen by destruction TAKEN (SPEC sec 2).
      defensiveTiers: [
        { id: 'def_30', minDestructionPct: 30, durationH: 12, tier: 'T1' },
        { id: 'def_60', minDestructionPct: 60, durationH: 14, tier: 'T2' },
        { id: 'def_90', minDestructionPct: 90, durationH: 16, tier: 'T3' }
      ],
      // Below 30% destruction => no shield (intentional Clash pressure).
      minDestructionForShieldPct: 30,
      // Buyable peace + per-product re-purchase cooldown (SPEC sec 3).
      buyable: [
        { id: 'short',    durationDays: 1, costAlk: 100, cooldownDays: 4,  tier: 'T1' },
        { id: 'lockdown', durationDays: 2, costAlk: 250, cooldownDays: 7,  tier: 'T2' },
        { id: 'deep',     durationDays: 7, costAlk: 700, cooldownDays: 35, tier: 'T3' }
      ],
      // Hours burned off your OWN shield per attack you launch (SPEC sec 4).
      attackThroughPenaltyH: { T1: 3, T2: 4, T3: 5 },
      postShieldGuardMin: 30      // optional 30-min Guard after a shield expires
    },

    raid: {
      // Per-building stat loss on a destroyed building (SPEC sec 5).
      buildingStatLoss: {
        spell_shop:       { lossPct: 10, floorPct: 50 },
        deck_lab:         { lossPct: 10, floorPct: 50 },
        main_tower:       { lossPct: 8,  floorPct: 40 },
        stash_house:      { lootPct: 15 },   // loot slice, not a stat floor
        kennel:           { lossPct: 10, floorPct: 50 },
        training_grounds: { lossPct: 10, floorPct: 50 }
      },
      destroyThresholdPct: 50,    // % of building HP gone to count as "destroyed"
      lootStealSlicePct: 15,      // base slice of available loot a raid can take
      revengeWindowH: 24,         // 24h revenge window (SPEC sec 6)
      repairRegenPctPerHour: 5    // online stat regen (owned by M07; number here)
    },

    // ---- MODULE_11_WHITEOUT / MODULE_04_CREW: crew-cap tables ----
    crew: {
      // Tower-level -> max members anchors; interpolate between (M11 SPEC sec 1).
      memberCapAnchors: [
        { towerLevel: 1,  cap: 5   },
        { towerLevel: 10, cap: 20  },
        { towerLevel: 30, cap: 100 }
      ],
      maxMembersHardCap: 100,
      buildingCapRule: 'tower_level',  // no building may exceed the tower level
      reinforcementWindowH: { min: 3, max: 8 },
      weeklyResetDow: 1,               // Monday
      weeklyResetUtcHour: 8            // 08:00 UTC reset (M04 SPEC sec 6)
    },

    whiteout: {
      starvedHysteresisMarginPct: 10,    // rep must climb this far above thr to clear
      trainingBoostPerActiveMemberPct: 10,
      boostedClaimMaxOfflineH: 24,
      warLanes: { arenas: 3, perArena: 5 },          // 3 x 5v5 (SPEC O-3)
      dvd: { hypeDays: 5, siegeHoldHours: 2.5, rebuildWindowH: 24, supremeBuffWeeks: 2 }
    },

    // ---- feature flags + endpoints (filled by remote source later) ----
    features: { warEnabled: true, marketplaceEnabled: false, web3Enabled: false },
    endpoints: {}
  };

  /**
   * Deep-merge plain objects (source wins). Arrays are replaced, not merged,
   * so an override of a table fully redefines it. ES5-safe, no deps.
   * @private
   * @param {Object} target
   * @param {Object} source
   * @returns {Object} target (mutated)
   */
  function deepMerge(target, source) {
    if (!source || typeof source !== 'object') return target;
    for (var key in source) {
      if (!Object.prototype.hasOwnProperty.call(source, key)) continue;
      var sv = source[key];
      var isPlain = sv !== null && typeof sv === 'object' &&
        Object.prototype.toString.call(sv) !== '[object Array]';
      if (isPlain) {
        if (target[key] === null || typeof target[key] !== 'object' ||
            Object.prototype.toString.call(target[key]) === '[object Array]') {
          target[key] = {};
        }
        deepMerge(target[key], sv);
      } else {
        target[key] = sv;
      }
    }
    return target;
  }

  /**
   * Structured clone of a JSON-safe value (defaults must not be mutated by a
   * later override). ES5-safe.
   * @private
   * @param {*} v
   * @returns {*}
   */
  function clone(v) {
    return v == null ? v : JSON.parse(JSON.stringify(v));
  }

  /**
   * Resolves and caches ecosystem configuration.
   * @class
   * @param {Object} [bus] - optional AK_EventBus to announce "config.ready".
   */
  function ConfigLoader(bus) {
    /** @private The most recently resolved config. */
    this._config = {};
    /** @private @type {boolean} */
    this._loaded = false;
    /** @private Optional bus for announcements. */
    this._bus = bus || (typeof global !== 'undefined' ? global.AK_EventBus : null);
  }

  /**
   * Load config: deep-merge built-in defaults <- opts.defaults <- opts.overrides,
   * cache it, and emit "config.ready" so downstream listeners can boot.
   *
   * The async signature is deliberate: when the source becomes a remote JSON /
   * Supabase flag service, only this body changes (fetch + await) -- callers and
   * the emitted event stay identical (adapter law).
   *
   * @param {Object} [opts]
   * @param {Object} [opts.defaults]  - extra defaults layered over the built-ins.
   * @param {Object} [opts.overrides] - Live Ops tuning layered on top (wins).
   * @returns {Promise<Object>} resolves with the merged config object.
   */
  ConfigLoader.prototype.load = function (opts) {
    var self = this;
    opts = opts || {};
    return Promise.resolve().then(function () {
      var cfg = clone(AK_CONFIG_DEFAULTS);
      if (opts.defaults) deepMerge(cfg, opts.defaults);
      if (opts.overrides) deepMerge(cfg, opts.overrides);
      self._config = cfg;
      self._loaded = true;
      if (self._bus && typeof self._bus.emit === 'function') {
        self._bus.emit('config.ready', self._config);
      }
      return self._config;
    });
  };

  /**
   * Read a single config value. Supports dotted paths ("shields.postShieldGuardMin").
   * Falls back to the baked-in defaults BEFORE load() has run, so early readers
   * still get the locked tables.
   *
   * @param {string} key        - dotted key path.
   * @param {*}      [fallback]  - returned when the key is absent.
   * @returns {*}
   */
  ConfigLoader.prototype.get = function (key, fallback) {
    if (!key) return fallback;
    var root = this._loaded ? this._config : AK_CONFIG_DEFAULTS;
    var node = root;
    var parts = String(key).split('.');
    for (var i = 0; i < parts.length; i++) {
      if (node == null || typeof node !== 'object' || !(parts[i] in node)) {
        return fallback;
      }
      node = node[parts[i]];
    }
    return node === undefined ? fallback : node;
  };

  /**
   * The whole resolved config object (baked defaults until load() completes).
   * @returns {Object}
   */
  ConfigLoader.prototype.all = function () {
    return this._loaded ? this._config : clone(AK_CONFIG_DEFAULTS);
  };

  /**
   * Whether load() has completed at least once.
   * @returns {boolean}
   */
  ConfigLoader.prototype.isLoaded = function () { return this._loaded; };

  // ----- typed convenience getters for the high-traffic tables -------------

  /**
   * The 7 burn-sink cost table.
   * @returns {Object} economy.sinks
   */
  ConfigLoader.prototype.costs = function () { return this.get('economy.sinks', {}); };

  /**
   * The auto-granted defensive shield tier table.
   * @returns {Array<{id,minDestructionPct,durationH,tier}>}
   */
  ConfigLoader.prototype.shieldTiers = function () { return this.get('shields.defensiveTiers', []); };

  /**
   * The purchasable shield products + re-purchase cooldowns.
   * @returns {Array<{id,durationDays,costAlk,cooldownDays,tier}>}
   */
  ConfigLoader.prototype.buyableShields = function () { return this.get('shields.buyable', []); };

  /**
   * Max crew size for a given Main Tower level, piecewise-linearly interpolated
   * between the configured anchors and floored (M11 SPEC sec 1). Clamps to the
   * first/last anchor outside the defined range.
   *
   * @param {number} towerLevel
   * @returns {number} max members
   */
  ConfigLoader.prototype.crewMemberCap = function (towerLevel) {
    var anchors = this.get('crew.memberCapAnchors', []);
    if (!anchors.length) return 0;
    var lvl = typeof towerLevel === 'number' ? towerLevel : parseFloat(towerLevel);
    if (isNaN(lvl)) lvl = anchors[0].towerLevel;
    if (lvl <= anchors[0].towerLevel) return anchors[0].cap;
    var last = anchors[anchors.length - 1];
    if (lvl >= last.towerLevel) return last.cap;
    for (var i = 0; i < anchors.length - 1; i++) {
      var a = anchors[i], b = anchors[i + 1];
      if (lvl >= a.towerLevel && lvl <= b.towerLevel) {
        var span = b.towerLevel - a.towerLevel;
        if (span <= 0) return a.cap;
        var frac = (lvl - a.towerLevel) / span;
        return Math.floor(a.cap + frac * (b.cap - a.cap));
      }
    }
    return last.cap;
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_ConfigLoader = new ConfigLoader();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      ConfigLoader: ConfigLoader,
      AK_ConfigLoader: AK_ConfigLoader,
      AK_CONFIG_DEFAULTS: AK_CONFIG_DEFAULTS
    };
  }
  if (typeof global !== 'undefined') {
    global.AK_ConfigLoader = AK_ConfigLoader;
    global.AK_ConfigLoader_Class = ConfigLoader;
    global.AK_CONFIG_DEFAULTS = AK_CONFIG_DEFAULTS;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
