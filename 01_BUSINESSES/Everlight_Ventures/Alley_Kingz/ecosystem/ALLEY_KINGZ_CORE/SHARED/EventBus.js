// ==========================================================================
// ALLEY KINGZ CORE -- SHARED / EventBus.js
// The single nervous system of the Alley Kingz ecosystem.
//
// ARCHITECTURE LAW (see ../README.md):
//   No module imports another. Every cross-module conversation goes over the
//   EventBus. Modules emit facts and listen for facts; they never reach into
//   each other's internals. This keeps the engine, shop, economy, social,
//   handlers, and art layers swappable behind adapters.
//
// FEATURES:
//   - emit(event, payload)        fire an event to all matching listeners
//   - on(event, fn, ctx)          subscribe; returns an unsubscribe function
//   - once(event, fn, ctx)        subscribe for exactly one delivery
//   - off(event, fn)              unsubscribe a specific handler (or all)
//   - wildcards                   "*" hears everything; "unit.*" hears any
//                                 event whose name starts with "unit."
//   - error-safe                  a listener that throws never blocks the
//                                 other listeners or the emitter
//
// USAGE (browser): include <script src="SHARED/EventBus.js"></script> then
//   const bus = window.AK_EventBus;            // shared singleton
//   const off = bus.on('match.win', d => ...); // subscribe
//   bus.emit('match.win', { winner: 'p1' });   // publish
//   off();                                      // unsubscribe
//
// USAGE (node/tests):
//   const { EventBus, AK_EventBus } = require('./EventBus.js');
//   const bus = new EventBus();   // isolated instance, or use AK_EventBus
//
// NO BUILD STEP. NO npm. Plain ES5-safe JS so it runs anywhere the game runs.
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Tiny, dependency-free publish/subscribe bus.
   *
   * Event names are dot-namespaced strings, e.g. "shop.purchase.ok".
   * Two wildcard forms are supported:
   *   "*"        -- matches every event that is emitted.
   *   "prefix.*" -- matches any event whose name === "prefix" or starts
   *                 with "prefix." (so "unit.*" hears "unit", "unit.spawn",
   *                 "unit.spawn.ranged", etc.)
   *
   * @class
   */
  function EventBus() {
    // Map<eventName, Array<{fn, ctx, once}>>. Exact and wildcard names share
    // this map; matching logic in emit() decides what fires.
    this._handlers = Object.create(null);
  }

  /**
   * Subscribe to an event.
   *
   * @param {string}   event - event name or wildcard ("*", "unit.*").
   * @param {Function} fn    - listener; receives (payload, eventName).
   * @param {Object}  [ctx]  - optional `this` binding for the listener.
   * @returns {Function} unsubscribe - call it to remove this exact listener.
   */
  EventBus.prototype.on = function (event, fn, ctx) {
    if (typeof event !== 'string' || typeof fn !== 'function') {
      throw new TypeError('EventBus.on(event:string, fn:function) required');
    }
    var list = this._handlers[event] || (this._handlers[event] = []);
    list.push({ fn: fn, ctx: ctx || null, once: false });
    var self = this;
    return function unsubscribe() { self.off(event, fn); };
  };

  /**
   * Subscribe for a single delivery, then auto-unsubscribe.
   *
   * @param {string}   event - event name or wildcard.
   * @param {Function} fn    - listener; receives (payload, eventName).
   * @param {Object}  [ctx]  - optional `this` binding.
   * @returns {Function} unsubscribe - cancels before it ever fires.
   */
  EventBus.prototype.once = function (event, fn, ctx) {
    if (typeof event !== 'string' || typeof fn !== 'function') {
      throw new TypeError('EventBus.once(event:string, fn:function) required');
    }
    var list = this._handlers[event] || (this._handlers[event] = []);
    var entry = { fn: fn, ctx: ctx || null, once: true };
    list.push(entry);
    var self = this;
    return function unsubscribe() { self._remove(event, entry); };
  };

  /**
   * Unsubscribe.
   *   off(event, fn) removes that one listener.
   *   off(event)     removes every listener for that event name.
   *   off()          removes every listener on the bus.
   *
   * @param {string}  [event] - event name or wildcard.
   * @param {Function}[fn]    - specific listener to drop.
   * @returns {void}
   */
  EventBus.prototype.off = function (event, fn) {
    if (event == null) { this._handlers = Object.create(null); return; }
    var list = this._handlers[event];
    if (!list) return;
    if (typeof fn !== 'function') { delete this._handlers[event]; return; }
    for (var i = list.length - 1; i >= 0; i--) {
      if (list[i].fn === fn) list.splice(i, 1);
    }
    if (list.length === 0) delete this._handlers[event];
  };

  /**
   * Remove one internal entry object (used by once's unsubscribe handle).
   * @private
   */
  EventBus.prototype._remove = function (event, entry) {
    var list = this._handlers[event];
    if (!list) return;
    var idx = list.indexOf(entry);
    if (idx !== -1) list.splice(idx, 1);
    if (list.length === 0) delete this._handlers[event];
  };

  /**
   * Publish an event. Listeners fire synchronously in subscription order:
   * exact-name listeners first, then matching wildcard listeners.
   *
   * Error-safe: if a listener throws, the error is caught, reported via the
   * "error" event (and console.error), and the remaining listeners still run.
   * The emit() call itself never throws because of a listener.
   *
   * @param {string} event     - event name being published.
   * @param {*}     [payload]  - arbitrary data handed to every listener.
   * @returns {number} count   - how many listeners were invoked.
   */
  EventBus.prototype.emit = function (event, payload) {
    if (typeof event !== 'string') {
      throw new TypeError('EventBus.emit(event:string, payload?) required');
    }
    var matched = this._collect(event);
    var fired = 0;
    for (var i = 0; i < matched.length; i++) {
      var entry = matched[i];
      // once-listeners are detached BEFORE invocation so a re-entrant emit
      // from inside the handler cannot double-fire them.
      if (entry.once) this._remove(entry._event, entry);
      try {
        entry.fn.call(entry.ctx, payload, event);
        fired++;
      } catch (err) {
        this._reportError(err, event, entry);
      }
    }
    return fired;
  };

  /**
   * Build the ordered list of entries that should receive `event`.
   * Exact matches come first, then "prefix.*" matches, then global "*".
   * Snapshots each list so subscribe/unsubscribe during emit is safe.
   * @private
   */
  EventBus.prototype._collect = function (event) {
    var out = [];
    var push = function (list, name) {
      if (!list) return;
      for (var i = 0; i < list.length; i++) {
        // tag each entry with its registration name for _remove()
        list[i]._event = name;
        out.push(list[i]);
      }
    };
    // 1. exact listeners
    push(this._handlers[event], event);
    // 2. prefix wildcards: walk "a.b.c" -> check "a.b.*", "a.*"
    var parts = event.split('.');
    for (var n = parts.length - 1; n >= 1; n--) {
      var wild = parts.slice(0, n).join('.') + '.*';
      if (wild !== event) push(this._handlers[wild], wild);
    }
    // 3. catch-all
    if (event !== '*') push(this._handlers['*'], '*');
    return out;
  };

  /**
   * Centralized error reporting for a throwing listener. Emits an "error"
   * event (guarded against infinite recursion) and falls back to console.
   * @private
   */
  EventBus.prototype._reportError = function (err, event, entry) {
    if (event !== 'error' && this._handlers['error']) {
      // Re-emit as an "error" event so a supervisor can observe failures.
      // Guarded by the event!=='error' check above to prevent loops.
      try {
        this.emit('error', { error: err, sourceEvent: event });
      } catch (_e) { /* swallow -- never let error handling crash */ }
    }
    if (typeof console !== 'undefined' && console && console.error) {
      console.error('[AK_EventBus] listener for "' + event + '" threw:', err);
    }
  };

  /**
   * Diagnostic: how many listeners are registered for an exact name (or for
   * the whole bus when no name is given). Does not count wildcard matches.
   *
   * @param {string} [event] - event name to count, or all when omitted.
   * @returns {number}
   */
  EventBus.prototype.listenerCount = function (event) {
    if (event != null) {
      return this._handlers[event] ? this._handlers[event].length : 0;
    }
    var total = 0;
    for (var k in this._handlers) total += this._handlers[k].length;
    return total;
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  // Process-wide singleton so every module shares one bus by default; tests
  // can still `new EventBus()` for isolation.
  var AK_EventBus = new EventBus();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventBus: EventBus, AK_EventBus: AK_EventBus };
  }
  if (typeof global !== 'undefined') {
    global.AK_EventBus = AK_EventBus;   // shared singleton
    global.AK_EventBus_Class = EventBus; // class, for isolated instances
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
