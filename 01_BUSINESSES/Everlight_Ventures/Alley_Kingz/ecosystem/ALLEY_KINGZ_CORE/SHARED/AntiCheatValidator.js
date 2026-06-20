// ==========================================================================
// ALLEY KINGZ CORE -- SHARED / AntiCheatValidator.js   [SERVER-AUTHORITY GATE]
// The trust boundary for economic events. Every value that moves loot, ALK,
// reputation, war score, or gear must pass through here before a module acts.
//
// ARCHITECTURE LAW (see ../README.md):
//   This module imports NOTHING and is imported by NOTHING. Feature modules
//   run inbound economic events past it via the bus or the singleton; it never
//   reaches into a module's internals (M03 SPEC sec 9, M11 SPEC sec 8).
//
// THE DOCTRINE (why this exists):
//   The client is never trusted with value. The battle that produces a raid's
//   destructionPct must be re-run server-side from { seed + input-log }; the
//   server number is truth (M03 SPEC sec 9). DamageCalculator is deterministic
//   precisely so that re-run is exact. Until the server validator is wired, the
//   client renders a PREDICTION and this gate marks it UNVERIFIED.
//
// STATUS: Wave-0 stub with REAL client-side sanity bounds. It does two things:
//   1. SANITY BOUNDS (runs now, client-side): rejects values that are
//      physically impossible regardless of server (negative amounts,
//      destructionPct outside 0..100, NaN). These catch trivially-forged
//      payloads and bugs immediately and emit ANTICHEAT_FLAGGED.
//   2. SERVER AUTHORITY (stub): every economic event is marked trusted:false
//      until a real server re-sim is wired via setVerifier(). When the M10
//      INTEGRATION adapter provides a verifier, verify() delegates to it and
//      the server value becomes truth -- a swap, not a rewrite.
//
//   HARD RULE: an UNKNOWN (non-economic) event returns { ok:true } so this gate
//   never blocks a build. Only events in the economic set are bounds-checked.
//
// EVENT CONTRACT:
//   emits: ANTICHEAT_FLAGGED { event, reason, payload, trusted:false }
//
// API:
//   attach(bus, opts)                  bind bus (optional; for emit only)
//   setVerifier(asyncFn)               install the server re-sim adapter
//   isEconomic(event) -> boolean
//   check(event, payload) -> { ok, trusted, errors }      sync sanity gate
//   verify(event, payload) -> Promise<{ ok, trusted, serverValue?, errors }>
//   guard(bus, event) -> (payload) => boolean             sanity-then-emit
//   flag(event, reason, payload)       emit ANTICHEAT_FLAGGED
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Events that carry value and therefore demand server authority. Covers both
   * the dot-namespaced and UPPER_SNAKE families from the economy/raid/whiteout
   * SPECs. Anything not in this set is non-economic and passes ungated.
   * @const {Object<string, boolean>}
   */
  var ECONOMIC_EVENTS = {
    // raid value facts
    'raid.calc.result': true,
    'raid.attack.resolved': true,
    'raid.building.damaged': true,
    'raid.shield.purchase.ok': true,
    // economy ledger facts (dot + UPPER_SNAKE)
    'economy.grant': true, 'economy.burn': true, 'economy.stake': true,
    'ECONOMY_EARN': true, 'SINK_REQUEST': true, 'SINK_CONFIRMED': true,
    'ALK_BURNED': true, 'TREASURY_CREDITED': true, 'STAKER_POOL_CREDITED': true,
    'STAKER_POOL_PAYOUT': true, 'STAKE_LOCK': true, 'STAKE_UNLOCK': true,
    // whiteout reputation / war value
    'REP_RAIDED': true, 'TRAINING_CLAIMED': true, 'CARD_STATS_RECALCULATED': true
  };

  /**
   * Per-field numeric sanity bounds. A present field outside its bound is an
   * impossible client claim -> flag. Absent fields are ignored (shape is the
   * DataValidator's job; this is purely the value-range trust gate).
   * @const {Object<string, {min?:number, max?:number, integer?:boolean}>}
   */
  var FIELD_BOUNDS = {
    amount:         { min: 0 },
    playerShare:    { min: 0 },
    costAlk:        { min: 0 },
    lootStolen:     { min: 0 },
    stolen:         { min: 0 },
    destructionPct: { min: 0, max: 100 },
    lossPct:        { min: 0, max: 100 },
    newStatPct:     { min: 0, max: 100 }
  };

  /**
   * The server-authority trust gate.
   * @class
   * @param {Object} [bus] - optional AK_EventBus to emit ANTICHEAT_FLAGGED on.
   */
  function AntiCheatValidator(bus) {
    /** @private */
    this._bus = bus || (typeof global !== 'undefined' ? global.AK_EventBus : null);
    /** @private @type {?Function} server re-sim adapter: (event,payload)=>Promise<{ok,serverValue?}> */
    this._verifier = null;
  }

  /**
   * Bind a bus (only needed so flag() can emit). Optional.
   * @param {Object} bus
   * @param {Object} [opts] - { verifier } optional server adapter.
   * @returns {AntiCheatValidator} this
   */
  AntiCheatValidator.prototype.attach = function (bus, opts) {
    if (bus) this._bus = bus;
    if (opts && typeof opts.verifier === 'function') this._verifier = opts.verifier;
    return this;
  };

  /**
   * Install the server-side re-simulation adapter (the real authority). When
   * set, verify() delegates to it and the server's returned value is truth.
   * Swapping this in is how the stub becomes a real gate -- no module changes.
   *
   * @param {Function} fn - (event, payload) => Promise<{ok:boolean, serverValue?:*, reason?:string}>
   * @returns {AntiCheatValidator} this
   */
  AntiCheatValidator.prototype.setVerifier = function (fn) {
    this._verifier = typeof fn === 'function' ? fn : null;
    return this;
  };

  /**
   * Is this event one that carries value (and thus demands authority)?
   * @param {string} event
   * @returns {boolean}
   */
  AntiCheatValidator.prototype.isEconomic = function (event) {
    return !!ECONOMIC_EVENTS[event];
  };

  /**
   * Synchronous client-side sanity gate. Runs NOW, no server needed.
   *
   * - Non-economic event  -> { ok:true, trusted:true } (ungated; never blocks a build).
   * - Economic event      -> bounds-checked. Out-of-bounds value => ok:false +
   *                          ANTICHEAT_FLAGGED. In-bounds => ok:true but
   *                          trusted:false (no server has confirmed it yet).
   *
   * @param {string} event
   * @param {*}       payload
   * @returns {{ ok:boolean, trusted:boolean, errors:string[] }}
   */
  AntiCheatValidator.prototype.check = function (event, payload) {
    if (!this.isEconomic(event)) return { ok: true, trusted: true, errors: [] };

    var errors = [];
    if (payload && typeof payload === 'object') {
      for (var field in FIELD_BOUNDS) {
        if (!Object.prototype.hasOwnProperty.call(payload, field)) continue;
        var val = payload[field];
        if (typeof val !== 'number' || isNaN(val) || !isFinite(val)) {
          errors.push('field "' + field + '" must be a finite number');
          continue;
        }
        var b = FIELD_BOUNDS[field];
        if (typeof b.min === 'number' && val < b.min) errors.push('field "' + field + '" below min ' + b.min);
        if (typeof b.max === 'number' && val > b.max) errors.push('field "' + field + '" above max ' + b.max);
        if (b.integer && Math.floor(val) !== val) errors.push('field "' + field + '" must be an integer');
      }
    }

    if (errors.length) {
      this.flag(event, 'sanity_bounds', payload, errors);
      return { ok: false, trusted: false, errors: errors };
    }
    // Passed sanity, but NOT server-confirmed -> trusted:false until verify().
    return { ok: true, trusted: false, errors: [] };
  };

  /**
   * Authoritative verification. Delegates to the installed server verifier when
   * present (server value becomes truth). With no verifier (Wave-0 stub) it
   * runs the sync sanity gate and returns trusted:false -- the honest signal
   * that the client value is a prediction, not server-confirmed.
   *
   * @param {string} event
   * @param {*}       payload
   * @returns {Promise<{ ok:boolean, trusted:boolean, serverValue?:*, errors:string[] }>}
   */
  AntiCheatValidator.prototype.verify = function (event, payload) {
    var self = this;
    var sanity = this.check(event, payload);
    if (!sanity.ok) return Promise.resolve(sanity);

    if (!this._verifier) {
      // No server authority wired yet -- honest about it.
      return Promise.resolve({ ok: true, trusted: false, errors: [] });
    }
    return Promise.resolve().then(function () {
      return self._verifier(event, payload);
    }).then(function (res) {
      res = res || {};
      if (res.ok === false) {
        self.flag(event, res.reason || 'server_rejected', payload);
        return { ok: false, trusted: false, errors: [res.reason || 'server_rejected'] };
      }
      return { ok: true, trusted: true, serverValue: res.serverValue, errors: [] };
    }).catch(function (err) {
      var msg = (err && err.message) || String(err);
      // Verifier failure is NOT a cheat -- it is an infra error. Do not flag the
      // player; report it untrusted so the caller can retry / degrade.
      return { ok: true, trusted: false, errors: ['verifier_error: ' + msg] };
    });
  };

  /**
   * Convenience guard: sanity-check then emit. On a sanity failure it does NOT
   * emit the event (the value is impossible) and ANTICHEAT_FLAGGED has fired.
   *
   * @param {Object} bus   - AK_EventBus instance.
   * @param {string} event - event name to emit on pass.
   * @returns {Function} (payload) => boolean  // true if emitted
   */
  AntiCheatValidator.prototype.guard = function (bus, event) {
    var self = this;
    return function (payload) {
      var res = self.check(event, payload);
      if (!res.ok) return false; // flag already emitted by check()
      if (bus && typeof bus.emit === 'function') bus.emit(event, payload);
      return true;
    };
  };

  /**
   * Emit ANTICHEAT_FLAGGED for a suspected forged / impossible value.
   * @param {string}  event
   * @param {string}  reason
   * @param {*}       payload
   * @param {string[]}[errors]
   * @returns {void}
   */
  AntiCheatValidator.prototype.flag = function (event, reason, payload, errors) {
    if (this._bus && typeof this._bus.emit === 'function') {
      try {
        this._bus.emit('ANTICHEAT_FLAGGED', {
          event: event, reason: reason, payload: payload,
          errors: errors || [], trusted: false, at: Date.now()
        });
      } catch (e) { /* bus is error-safe; guard anyway */ }
    }
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_AntiCheatValidator = new AntiCheatValidator();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      AntiCheatValidator: AntiCheatValidator,
      AK_AntiCheatValidator: AK_AntiCheatValidator,
      ECONOMIC_EVENTS: ECONOMIC_EVENTS
    };
  }
  if (typeof global !== 'undefined') {
    global.AK_AntiCheatValidator = AK_AntiCheatValidator;
    global.AK_AntiCheatValidator_Class = AntiCheatValidator;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
