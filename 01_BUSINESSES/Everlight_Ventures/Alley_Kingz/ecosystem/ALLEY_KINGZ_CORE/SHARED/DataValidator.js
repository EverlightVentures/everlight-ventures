// ==========================================================================
// ALLEY KINGZ CORE -- SHARED / DataValidator.js
// Schema / shape validation for payloads crossing the EventBus.
//
// ARCHITECTURE LAW (see ../README.md):
//   This module imports NOTHING and is imported by NOTHING. Modules that want
//   validation listen on the bus or call the singleton; they do not `require`
//   each other. DataValidator's job is to guarantee that an event payload
//   matches the agreed contract BEFORE a module acts on it -- so a bad shop
//   payload can never corrupt the engine, and vice versa.
//
// STATUS: Wave-0 real implementation. Schemas are registered for the
//   high-traffic event families the build plan locks first:
//     raid.*     (MODULE_03_PVP_RAID SPEC sec 8)
//     economy.*  (MODULE_06_ECONOMY SPEC sec 6, both dot + UPPER_SNAKE forms)
//     crew.*     (MODULE_04_CREW SPEC sec 8)
//     squad.*    (war-lane / 2v2 squad lifecycle; designed, not yet canon)
//
//   HARD RULE (build plan W0.1): validate() of an UNREGISTERED schema returns
//   { ok:true } so wiring a validator in can never break a running build.
//   Only an explicitly registered contract can ever report ok:false.
//
// SCHEMA SHAPE (declarative, ES5-safe):
//   {
//     fields: {
//       attackerId: { type: 'string',  required: true  },
//       deck:       { type: 'array',   required: false },
//       isRevenge:  { type: 'boolean', required: false },
//       season:     { type: ['string','number'], required: false }
//     }
//   }
//   Supported types: 'string' | 'number' | 'int' | 'boolean' | 'object' |
//                    'array' | 'function' | 'any'  (or an array of allowed types).
//   Unknown extra fields on a payload are tolerated (forward-compatible).
//
// API:
//   registerSchema(name, schema)         register one contract
//   registerSchemas({name: schema, ...}) register a map of contracts
//   hasSchema(name) -> boolean
//   validate(name, payload) -> { ok, errors }   (ok:true if name unregistered)
//   guard(bus, name, event) -> (payload) => boolean   validate-then-emit helper
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Validates EventBus payloads against named schemas.
   * @class
   */
  function DataValidator() {
    /** @private @type {Object<string, ?Object>} compiled schemas by name. */
    this._schemas = Object.create(null);
    this._registerDefaults();
  }

  // ----- type checking -----------------------------------------------------

  /**
   * Test one value against one declared type token.
   * @private
   * @param {*} value
   * @param {string} type - one supported type token.
   * @returns {boolean}
   */
  DataValidator.prototype._isType = function (value, type) {
    switch (type) {
      case 'any':      return true;
      case 'string':   return typeof value === 'string';
      case 'number':   return typeof value === 'number' && !isNaN(value);
      case 'int':      return typeof value === 'number' && isFinite(value) && Math.floor(value) === value;
      case 'boolean':  return typeof value === 'boolean';
      case 'function': return typeof value === 'function';
      case 'array':    return Object.prototype.toString.call(value) === '[object Array]';
      case 'object':
        return value !== null && typeof value === 'object' &&
               Object.prototype.toString.call(value) !== '[object Array]';
      default:
        return false; // unknown type token => never matches (caught at register time conceptually)
    }
  };

  /**
   * Test a value against a field's allowed type(s).
   * @private
   * @param {*} value
   * @param {string|string[]} types
   * @returns {boolean}
   */
  DataValidator.prototype._matchesAny = function (value, types) {
    if (Object.prototype.toString.call(types) === '[object Array]') {
      for (var i = 0; i < types.length; i++) {
        if (this._isType(value, types[i])) return true;
      }
      return false;
    }
    return this._isType(value, types);
  };

  // ----- registration ------------------------------------------------------

  /**
   * Register a payload contract under a name (usually the event name).
   *
   * @param {string} name   - schema id.
   * @param {Object} schema - { fields: { key: { type, required } } }.
   * @returns {void}
   */
  DataValidator.prototype.registerSchema = function (name, schema) {
    if (typeof name !== 'string' || !name) return;
    this._schemas[name] = schema && schema.fields ? schema : (schema ? { fields: schema } : null);
  };

  /**
   * Register many contracts at once.
   * @param {Object<string, Object>} map - { name: schema, ... }.
   * @returns {void}
   */
  DataValidator.prototype.registerSchemas = function (map) {
    if (!map || typeof map !== 'object') return;
    for (var name in map) {
      if (Object.prototype.hasOwnProperty.call(map, name)) {
        this.registerSchema(name, map[name]);
      }
    }
  };

  /**
   * Whether a schema is registered for this name.
   * @param {string} name
   * @returns {boolean}
   */
  DataValidator.prototype.hasSchema = function (name) {
    return !!this._schemas[name];
  };

  // ----- validation --------------------------------------------------------

  /**
   * Validate a payload against a registered schema.
   *
   * If `schemaName` is NOT registered, returns { ok:true, errors:[] } -- the
   * permissive default that keeps wiring from ever breaking a build (W0.1).
   * Extra/unknown fields are allowed. Missing required fields and wrong types
   * are reported.
   *
   * @param {string} schemaName - registered schema id.
   * @param {*}       payload   - data to check.
   * @returns {{ ok: boolean, errors: string[] }}
   */
  DataValidator.prototype.validate = function (schemaName, payload) {
    var schema = this._schemas[schemaName];
    if (!schema) return { ok: true, errors: [] }; // unregistered => permissive

    var errors = [];
    if (payload === null || typeof payload !== 'object' ||
        Object.prototype.toString.call(payload) === '[object Array]') {
      return { ok: false, errors: ['payload must be a plain object'] };
    }

    var fields = schema.fields || {};
    for (var key in fields) {
      if (!Object.prototype.hasOwnProperty.call(fields, key)) continue;
      var rule = fields[key] || {};
      var present = Object.prototype.hasOwnProperty.call(payload, key) && payload[key] !== undefined;

      if (!present) {
        if (rule.required) errors.push('missing required field "' + key + '"');
        continue;
      }
      var types = rule.type || 'any';
      if (!this._matchesAny(payload[key], types)) {
        errors.push('field "' + key + '" must be ' +
          (Object.prototype.toString.call(types) === '[object Array]' ? types.join('|') : types));
      }
    }
    return { ok: errors.length === 0, errors: errors };
  };

  /**
   * Convenience guard: returns a function that validates then forwards to the
   * bus, re-emitting "error" on failure instead of throwing.
   *
   * @param {Object} bus        - an AK_EventBus instance.
   * @param {string} schemaName - schema to enforce.
   * @param {string} event      - event name to emit on success.
   * @returns {Function} (payload) => boolean  // true if emitted
   */
  DataValidator.prototype.guard = function (bus, schemaName, event) {
    var self = this;
    return function (payload) {
      var res = self.validate(schemaName, payload);
      if (!res.ok) {
        if (bus && typeof bus.emit === 'function') {
          bus.emit('error', { sourceEvent: event, schema: schemaName, errors: res.errors });
        }
        return false;
      }
      if (bus && typeof bus.emit === 'function') bus.emit(event, payload);
      return true;
    };
  };

  // ----- default contracts (grounded in the module SPECs) ------------------

  /**
   * Register the Wave-0 schema set: raid.* / economy.* / crew.* / squad.*.
   * Numbers/shapes trace to the SPEC.md event tables in each module dir.
   * @private
   */
  DataValidator.prototype._registerDefaults = function () {
    var S = function (fields) { return { fields: fields }; };
    var req = function (type) { return { type: type, required: true }; };
    var opt = function (type) { return { type: type, required: false }; };

    this.registerSchemas({
      // ---- MODULE_03_PVP_RAID (SPEC sec 8) -- dot-namespaced raid.* ----
      'raid.attack.requested': S({
        attackerId: req('string'), defenderId: req('string'),
        deck: opt('array'), targetBuildings: opt('array'),
        isRevenge: opt('boolean'), originalRaidId: opt('string')
      }),
      'raid.revenge.requested': S({ avengerId: req('string'), originalRaidId: req('string') }),
      'raid.calc.requested': S({ raidId: req('string'), base: req('object'), deck: opt('array'), seed: opt(['number', 'string']) }),
      'raid.calc.result': S({
        raidId: req('string'), destructionPct: req('number'),
        perBuildingLoss: opt('array'), lootRequest: opt('object')
      }),
      'raid.attack.resolved': S({
        raidId: req('string'), attackerId: req('string'), defenderId: req('string'),
        destructionPct: req('number'), lootStolen: opt('number'), buildingsHit: opt('array')
      }),
      'raid.building.damaged': S({
        defenderId: req('string'), buildingId: req('string'),
        lossPct: req('number'), newStatPct: req('number')
      }),
      'raid.revenge.available': S({
        defenderId: req('string'), attackerId: req('string'),
        raidId: req('string'), expiresAt: req('number')
      }),
      'raid.revenge.expired': S({ raidId: req('string') }),
      'raid.shield.grant.requested': S({ playerId: req('string'), destructionPct: req('number'), source: opt('string') }),
      'raid.shield.purchase.requested': S({ playerId: req('string'), product: req('string') }),
      'raid.shield.activated': S({
        playerId: req('string'), tier: req('string'), source: opt('string'),
        durationMs: req('number'), expiresAt: req('number')
      }),
      'raid.shield.reduced': S({ playerId: req('string'), hoursRemoved: req('number'), remainingMs: req('number') }),
      'raid.shield.expired': S({ playerId: req('string') }),
      'raid.shield.purchase.ok': S({
        playerId: req('string'), product: req('string'),
        costAlk: req('number'), cooldownEndsAt: req('number')
      }),
      'raid.shield.purchase.denied': S({
        playerId: req('string'), product: req('string'),
        reason: req('string'), cooldownEndsAt: opt('number')
      }),
      // The blueprint-mandated cross-module rally signal (kept verbatim).
      'CREW_UNDER_SIEGE': S({
        defenderId: req('string'), crewId: req('string'), attackerId: req('string'),
        raidId: req('string'), baseSnapshotId: opt('string'), startedAt: opt('number')
      }),
      // build-plan lowercase alias (AK_BUILD_PLAN.md W2.1 / integration story).
      'crew.under_siege': S({
        defenderId: req('string'), crewId: req('string'), attackerId: req('string'),
        raidId: req('string'), baseSnapshotId: opt('string'), startedAt: opt('number')
      }),

      // ---- MODULE_06_ECONOMY -- dot-namespaced (AK_BUILD_PLAN.md) ----
      'economy.grant': S({ source: opt('string'), amount: req('number'), playerId: opt('string'), meta: opt('object') }),
      'economy.burn':  S({ amount: req('number'), sinkId: opt('string') }),
      'economy.stake': S({ amount: req('number'), playerId: opt('string') }),
      // ---- MODULE_06_ECONOMY -- canonical UPPER_SNAKE (SPEC sec 6) ----
      'ECONOMY_EARN': S({ source: req('string'), amount: req('number'), meta: opt('object') }),
      'SINK_REQUEST': S({ sinkId: req('string'), amount: opt('number'), meta: opt('object') }),
      'SINK_CONFIRMED': S({ sinkId: req('string'), amount: req('number'), meta: opt('object') }),
      'SINK_DENIED': S({ sinkId: req('string'), need: req('number'), have: req('number') }),
      'ECONOMY_BALANCE_CHANGED': S({ balance: req('number'), locked: opt('number'), delta: opt('number'), reason: opt('string') }),
      'ECONOMY_EMISSION_CAPPED': S({ source: req('string'), requested: req('number'), granted: req('number') }),
      'STAKE_LOCK': S({ amount: req('number') }),
      'STAKE_LOCKED': S({ amount: req('number'), unlockAt: req('number') }),
      'STAKE_UNLOCK': S({ amount: req('number') }),
      'STAKE_UNLOCKED': S({ amount: req('number') }),
      'ALK_BURNED': S({ amount: req('number'), sinkId: opt('string') }),
      'TREASURY_CREDITED': S({ amount: req('number'), sinkId: opt('string') }),
      'STAKER_POOL_CREDITED': S({ amount: req('number'), sinkId: opt('string') }),
      'STAKER_POOL_PAYOUT': S({ playerId: opt('string'), playerShare: req('number') }),
      'DEFLATION_TICK': S({ monthlyInflationPct: req('number'), stakedPct: opt('number'), circulating: opt('number'), burned30d: opt('number') }),
      'DEFLATION_ALERT': S({ monthlyInflationPct: req('number') }),

      // ---- MODULE_04_CREW (SPEC sec 8) -- crew.* ----
      'crew.loaded': S({ crew: req('object'), role: opt('string'), members: opt('array') }),
      'crew.directory.loaded': S({ crews: req('array') }),
      'crew.created': S({ crewId: req('string'), name: req('string'), tag: req('string'), faction: opt('string'), leaderId: opt('string') }),
      'crew.joined': S({ crewId: req('string'), userId: req('string'), requested: opt('boolean') }),
      'crew.left': S({ crewId: req('string'), userId: req('string'), disbanded: opt('boolean') }),
      'crew.member.promoted': S({ crewId: req('string'), userId: req('string'), byUserId: opt('string'), role: opt('string') }),
      'crew.member.demoted': S({ crewId: req('string'), userId: req('string'), byUserId: opt('string'), role: opt('string') }),
      'crew.member.kicked': S({ crewId: req('string'), userId: req('string'), byUserId: opt('string'), role: opt('string') }),
      'crew.roster.updated': S({ crewId: req('string'), members: opt('array') }),
      'crew.chat.message': S({
        id: opt('string'), scope: req('string'), crewId: opt('string'), userId: req('string'),
        name: opt('string'), faction: opt('string'), body: req('string'), at: opt('number')
      }),
      'crew.reinforcement.requested': S({
        requestId: req('string'), crewId: req('string'), userId: req('string'),
        cardId: req('string'), qtyReq: opt('number'), expiresAt: opt('number')
      }),
      'crew.reinforcement.filled': S({
        requestId: req('string'), donorId: req('string'), recipientId: req('string'),
        cardId: req('string'), qty: opt('number')
      }),
      'crew.grant.claimed': S({ kinds: opt('array'), totals: opt('object') }),
      'crew.war.started': S({ warId: req('string'), crewId: req('string'), oppCrewId: opt('string'), season: opt(['string', 'number']), endsAt: opt('number'), tickets: opt('number') }),
      'crew.war.scored': S({ warId: req('string'), score: req('number'), oppScore: opt('number'), fameDelta: opt('number'), userId: opt('string') }),
      'crew.war.ended': S({ warId: req('string'), won: req('boolean'), streak: opt('number') }),
      'crew.streak.updated': S({ crewId: req('string'), streak: req('number'), broken: opt('boolean') }),
      'crew.member.betrayed': S({ crewId: req('string'), userId: req('string'), context: opt('string') }),
      'crew.war.declared': S({ crewId: req('string'), oppCrewId: opt('string'), memberCount: opt('number') }),
      'crew.error': S({ action: opt('string'), error: req('any') }),

      // ---- SQUAD lifecycle (war-lane 5v5 / 2v2; designed, awaiting canon) ----
      // A "squad" is a sub-roster committed to one war-lane arena or a 2v2
      // ghost match. Distinct from a crew (the whole social graph).
      'squad.formed': S({ squadId: req('string'), warId: opt('string'), arena: opt('int'), leaderId: req('string'), memberIds: opt('array') }),
      'squad.member.joined': S({ squadId: req('string'), userId: req('string') }),
      'squad.member.left': S({ squadId: req('string'), userId: req('string') }),
      'squad.ready': S({ squadId: req('string'), ready: opt('boolean') }),
      'squad.disbanded': S({ squadId: req('string'), reason: opt('string') })
    });
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_DataValidator = new DataValidator();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DataValidator: DataValidator, AK_DataValidator: AK_DataValidator };
  }
  if (typeof global !== 'undefined') {
    global.AK_DataValidator = AK_DataValidator;
    global.AK_DataValidator_Class = DataValidator;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
