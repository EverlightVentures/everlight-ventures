// ==========================================================================
// ALLEY KINGZ CORE -- SHARED / SaveLoadManager.js
// Bridges EventBus state <-> persistent storage. localStorage NOW, Supabase
// LATER -- swapped behind a single storage adapter (adapter law).
//
// ARCHITECTURE LAW (see ../README.md):
//   This module imports NOTHING and is imported by NOTHING. Feature modules
//   (M11 WHITEOUT et al.) never touch localStorage or Supabase directly; they
//   emit STATE_SAVE_REQUESTED / STATE_LOAD_REQUESTED and listen for STATE_SAVED
//   / STATE_LOADED. SaveLoadManager is the ONLY thing that knows where bytes
//   live. To move from localStorage to Supabase you write a new adapter and
//   call setAdapter() -- no feature module changes (M11 SPEC sec 8).
//
// STATUS: Wave-0 implementation. Default adapter = guarded localStorage with an
//   in-memory fallback (so the node test harness + private-mode browsers never
//   throw). A SupabaseAdapter is a later drop-in: same { get,set,remove,keys }
//   contract, async-capable.
//
// SERVER-AUTHORITY NOTE: localStorage is a client convenience cache only. When
//   the Supabase adapter lands, the server copy is the source of truth and the
//   local copy is a write-through cache reconciled on load. This module already
//   treats every store op as async (Promise) so that swap is invisible.
//
// EVENT CONTRACT:
//   listens: STATE_SAVE_REQUESTED { key, data }
//            STATE_LOAD_REQUESTED { key, fallback? }
//            STATE_REMOVE_REQUESTED { key }
//   emits:   STATE_SAVED  { key, ok, error? }
//            STATE_LOADED { key, ok, data, found }
//            STATE_REMOVED{ key, ok }
//
// API:
//   attach(bus, opts)          wire bus listeners; idempotent
//   setAdapter(adapter)        swap storage backend (localStorage -> Supabase)
//   save(key, data)  -> Promise<{ok, error?}>
//   load(key, fb)    -> Promise<{ok, data, found}>
//   remove(key)      -> Promise<{ok}>
//   keys()           -> Promise<string[]>
// ==========================================================================

(function (global) {
  'use strict';

  /** Namespace prefix so AK state never collides with other localStorage keys. */
  var KEY_PREFIX = 'ak.save.';

  // ----- default storage adapter ------------------------------------------

  /**
   * Guarded localStorage adapter with an in-memory fallback. Every method
   * returns a value or a Promise; SaveLoadManager wraps both with Promise.resolve
   * so a future async (Supabase) adapter is a transparent swap.
   *
   * Contract every adapter must satisfy:
   *   get(key)        -> string|null            (raw stored string)
   *   set(key, value) -> void|Promise           (value is a string)
   *   remove(key)     -> void|Promise
   *   keys()          -> string[]|Promise        (full prefixed keys)
   *
   * @constructor
   */
  function LocalStorageAdapter() {
    /** @private in-memory fallback when localStorage is unavailable. */
    this._mem = Object.create(null);
    /** @private @type {?Storage} */
    this._ls = null;
    try {
      if (typeof localStorage !== 'undefined') {
        var probe = '__ak_probe__';
        localStorage.setItem(probe, '1');
        localStorage.removeItem(probe);
        this._ls = localStorage;
      }
    } catch (e) {
      this._ls = null; // private mode / quota / node -- fall back to memory
    }
  }
  LocalStorageAdapter.prototype.get = function (key) {
    if (this._ls) { try { return this._ls.getItem(key); } catch (e) { /* fall through */ } }
    return Object.prototype.hasOwnProperty.call(this._mem, key) ? this._mem[key] : null;
  };
  LocalStorageAdapter.prototype.set = function (key, value) {
    if (this._ls) {
      try { this._ls.setItem(key, value); return; }
      catch (e) { /* quota -> mirror to memory so the session keeps working */ }
    }
    this._mem[key] = value;
  };
  LocalStorageAdapter.prototype.remove = function (key) {
    if (this._ls) { try { this._ls.removeItem(key); } catch (e) { /* ignore */ } }
    delete this._mem[key];
  };
  LocalStorageAdapter.prototype.keys = function () {
    var out = [];
    if (this._ls) {
      try {
        for (var i = 0; i < this._ls.length; i++) {
          var k = this._ls.key(i);
          if (k && k.indexOf(KEY_PREFIX) === 0) out.push(k);
        }
        return out;
      } catch (e) { /* fall through to memory */ }
    }
    for (var mk in this._mem) {
      if (Object.prototype.hasOwnProperty.call(this._mem, mk) && mk.indexOf(KEY_PREFIX) === 0) out.push(mk);
    }
    return out;
  };

  // ----- manager -----------------------------------------------------------

  /**
   * EventBus <-> storage bridge.
   * @class
   * @param {Object} [bus]     - optional AK_EventBus; defaults to the singleton.
   * @param {Object} [adapter] - optional storage adapter; defaults to localStorage.
   */
  function SaveLoadManager(bus, adapter) {
    /** @private */
    this._bus = bus || (typeof global !== 'undefined' ? global.AK_EventBus : null);
    /** @private */
    this._adapter = adapter || new LocalStorageAdapter();
    /** @private @type {boolean} guards double-wiring. */
    this._attached = false;
    /** @private unsubscribe handles. @type {Function[]} */
    this._offs = [];
  }

  /**
   * Build the namespaced storage key for a logical key.
   * @private
   * @param {string} key
   * @returns {string}
   */
  SaveLoadManager.prototype._k = function (key) { return KEY_PREFIX + String(key); };

  /**
   * Wire bus listeners so feature modules can save/load by event. Idempotent:
   * a second call with the same (or default) bus is a no-op.
   *
   * @param {Object} [bus]  - AK_EventBus to bind to.
   * @param {Object} [opts] - { adapter } optional adapter override.
   * @returns {SaveLoadManager} this
   */
  SaveLoadManager.prototype.attach = function (bus, opts) {
    if (bus) this._bus = bus;
    if (opts && opts.adapter) this._adapter = opts.adapter;
    if (this._attached || !this._bus || typeof this._bus.on !== 'function') return this;
    var self = this;

    this._offs.push(this._bus.on('STATE_SAVE_REQUESTED', function (p) {
      if (!p || typeof p.key === 'undefined') return;
      self.save(p.key, p.data);
    }));
    this._offs.push(this._bus.on('STATE_LOAD_REQUESTED', function (p) {
      if (!p || typeof p.key === 'undefined') return;
      self.load(p.key, p.fallback);
    }));
    this._offs.push(this._bus.on('STATE_REMOVE_REQUESTED', function (p) {
      if (!p || typeof p.key === 'undefined') return;
      self.remove(p.key);
    }));

    this._attached = true;
    return this;
  };

  /**
   * Tear down bus listeners (mostly for tests).
   * @returns {void}
   */
  SaveLoadManager.prototype.detach = function () {
    for (var i = 0; i < this._offs.length; i++) {
      try { this._offs[i](); } catch (e) { /* ignore */ }
    }
    this._offs = [];
    this._attached = false;
  };

  /**
   * Swap the storage backend (localStorage today, Supabase later). The new
   * adapter only needs the { get, set, remove, keys } contract; methods may be
   * sync or return Promises.
   *
   * @param {Object} adapter
   * @returns {SaveLoadManager} this
   */
  SaveLoadManager.prototype.setAdapter = function (adapter) {
    if (adapter) this._adapter = adapter;
    return this;
  };

  /**
   * Persist a JSON-serializable value under a logical key and emit STATE_SAVED.
   *
   * @param {string} key  - logical key (namespaced internally).
   * @param {*}      data - JSON-serializable value.
   * @returns {Promise<{ok:boolean, error?:string}>}
   */
  SaveLoadManager.prototype.save = function (key, data) {
    var self = this;
    return Promise.resolve().then(function () {
      var raw = JSON.stringify({ v: 1, savedAt: Date.now(), data: data });
      return self._adapter.set(self._k(key), raw);
    }).then(function () {
      self._emit('STATE_SAVED', { key: key, ok: true });
      return { ok: true };
    }).catch(function (err) {
      var msg = (err && err.message) || String(err);
      self._emit('STATE_SAVED', { key: key, ok: false, error: msg });
      return { ok: false, error: msg };
    });
  };

  /**
   * Load a value by logical key and emit STATE_LOADED. Missing keys resolve to
   * the supplied fallback with found:false (never throws on absent / corrupt).
   *
   * @param {string} key       - logical key.
   * @param {*}      [fallback] - returned when absent or unparseable.
   * @returns {Promise<{ok:boolean, data:*, found:boolean}>}
   */
  SaveLoadManager.prototype.load = function (key, fallback) {
    var self = this;
    return Promise.resolve().then(function () {
      return self._adapter.get(self._k(key));
    }).then(function (raw) {
      var data = fallback, found = false;
      if (raw != null && raw !== '') {
        try {
          var parsed = JSON.parse(raw);
          // accept either the wrapped envelope or a bare value (forward-compat)
          data = (parsed && typeof parsed === 'object' && 'data' in parsed) ? parsed.data : parsed;
          found = true;
        } catch (e) {
          data = fallback; found = false; // corrupt -> treat as absent
        }
      }
      self._emit('STATE_LOADED', { key: key, ok: true, data: data, found: found });
      return { ok: true, data: data, found: found };
    }).catch(function (err) {
      var msg = (err && err.message) || String(err);
      self._emit('STATE_LOADED', { key: key, ok: false, data: fallback, found: false, error: msg });
      return { ok: false, data: fallback, found: false };
    });
  };

  /**
   * Remove a key and emit STATE_REMOVED.
   * @param {string} key
   * @returns {Promise<{ok:boolean}>}
   */
  SaveLoadManager.prototype.remove = function (key) {
    var self = this;
    return Promise.resolve().then(function () {
      return self._adapter.remove(self._k(key));
    }).then(function () {
      self._emit('STATE_REMOVED', { key: key, ok: true });
      return { ok: true };
    }).catch(function (err) {
      var msg = (err && err.message) || String(err);
      self._emit('STATE_REMOVED', { key: key, ok: false, error: msg });
      return { ok: false, error: msg };
    });
  };

  /**
   * List all AK-namespaced logical keys (prefix stripped).
   * @returns {Promise<string[]>}
   */
  SaveLoadManager.prototype.keys = function () {
    var self = this;
    return Promise.resolve().then(function () {
      return self._adapter.keys();
    }).then(function (full) {
      var out = [];
      full = full || [];
      for (var i = 0; i < full.length; i++) {
        if (full[i].indexOf(KEY_PREFIX) === 0) out.push(full[i].slice(KEY_PREFIX.length));
      }
      return out;
    }).catch(function () { return []; });
  };

  /**
   * Safe emit -- never lets a missing bus throw.
   * @private
   */
  SaveLoadManager.prototype._emit = function (event, payload) {
    if (this._bus && typeof this._bus.emit === 'function') {
      try { this._bus.emit(event, payload); } catch (e) { /* bus is error-safe; belt + suspenders */ }
    }
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_SaveLoadManager = new SaveLoadManager();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      SaveLoadManager: SaveLoadManager,
      AK_SaveLoadManager: AK_SaveLoadManager,
      LocalStorageAdapter: LocalStorageAdapter
    };
  }
  if (typeof global !== 'undefined') {
    global.AK_SaveLoadManager = AK_SaveLoadManager;
    global.AK_SaveLoadManager_Class = SaveLoadManager;
    global.AK_LocalStorageAdapter = LocalStorageAdapter;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
