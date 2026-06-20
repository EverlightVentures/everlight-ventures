// ==========================================================================
// ALLEY KINGZ CORE -- MODULE_05_SOCIAL_URGENCY / PushNotificationManager.js [STUB]
// The delivery transport for the socially-radioactive engine.
//
// ARCHITECTURE LAW (see ../README.md and ./SPEC.md):
//   This module imports NOTHING and is imported by NOTHING. All cross-module
//   comms go over window.AK_EventBus. The urgency BRAIN (scoring + scheduling,
//   the 3 tiers, the chat-weapons, the Reward-Flow loop -- see SPEC) decides
//   WHAT to say and WHEN. PushNotificationManager decides HOW it reaches the
//   device and enforces the anti-spam budget. It listens to crew.* / match.* /
//   urgency.* facts and routes notices down the channel ladder:
//     Web Push -> in-app banner -> chat system message -> next-open badge.
//   It never writes the crew DB and never authors weaponized chat copy.
//
// STATUS: documented stub. deliver()/requestPermission() are best-effort no-ops
//   that emit the right facts, so wiring this in cannot break a running build
//   and a denied/unsupported notification permission is a normal state, never
//   an error. Fill in the real service worker + VAPID Web Push later.
//
// BRAND GUARDRAIL (HARD): "attention, not tension." Honors a `tone` flag
//   (hype | competitive | off), quiet hours, and per-tier frequency caps. No
//   PII ever rides a push (crew/handle only, never email).
//
// REUSE MAP (see SPEC Section 3): reads STAGED state (ak_crew_wars.ends_at for
//   countdowns, ak_donation_requests.expires_at for shield nudges, war_streak
//   for streak-crisis); rewards ride the ak_grants rail; chat weapons post via
//   the crew/edge layer. Server-timed push (app fully closed) is a deferred
//   ak-push edge fn + ak_push_subscriptions table; v1 is client/Realtime-driven.
//
// NO BUILD STEP. NO npm. Plain ES5-safe JS so it runs anywhere the game runs.
// ==========================================================================

(function (global) {
  'use strict';

  /** Per-tier default daily push budgets (anti-spam; see SPEC Section 7). */
  var DEFAULT_CAPS = { 1: 2, 2: 3, 3: 4 };

  /**
   * Routes urgency notices to the device and enforces permission + budget.
   *
   * @class
   * @param {Object} [bus] - AK_EventBus instance (defaults to the singleton).
   */
  function PushNotificationManager(bus) {
    /** @private Shared event bus -- the ONLY wire to other modules. */
    this._bus = bus || (typeof global !== 'undefined' ? global.AK_EventBus : null);
    /** @private Cached OS permission: default | granted | denied | unsupported. */
    this._permission = 'default';
    /** @private Delivery tone: hype | competitive | off. */
    this._tone = 'hype';
    /** @private Quiet-hours window [startHour, endHour) local time. */
    this._quiet = { start: 22, end: 8 };
    /** @private Per-tier daily caps. */
    this._caps = { 1: DEFAULT_CAPS[1], 2: DEFAULT_CAPS[2], 3: DEFAULT_CAPS[3] };
    /** @private Per-tier fire counts for the current local day. */
    this._fired = { 1: 0, 2: 0, 3: 0 };
    /** @private Per-kind mutes. */
    this._muted = Object.create(null);
    /** @private Idempotent-wiring guard. */
    this._wired = false;
  }

  /**
   * Wire bus listeners + register the service worker. Idempotent.
   * STUB: subscribes to the urgency/push facts but registers no SW yet.
   *
   * @param {Object} [bus]  - bus to use (overrides constructor bus).
   * @param {Object} [opts] - { tone, quietStart, quietEnd, caps } overrides.
   * @returns {PushNotificationManager} this (chainable).
   */
  PushNotificationManager.prototype.attach = function (bus, opts) {
    if (bus) this._bus = bus;
    if (opts) {
      if (opts.tone) this._tone = opts.tone;
      if (typeof opts.quietStart === 'number') this._quiet.start = opts.quietStart;
      if (typeof opts.quietEnd === 'number') this._quiet.end = opts.quietEnd;
      if (opts.caps) this._caps = opts.caps;
    }
    this._detectPermission();
    if (this._wired || !this._bus) return this;
    var self = this;
    // The brain raises an urgency -> we route it to a device channel.
    this._bus.on('urgency.raised', function (u) { self.deliver(self._noticeFromUrgency(u)); });
    // New day (or new user) resets the per-tier budget.
    this._bus.on('auth.changed', function () { self._fired = { 1: 0, 2: 0, 3: 0 }; });
    this._wired = true;
    return this;
  };

  /** @private Read the current Notification permission without prompting. */
  PushNotificationManager.prototype._detectPermission = function () {
    try {
      if (typeof Notification === 'undefined') { this._permission = 'unsupported'; }
      else { this._permission = Notification.permission || 'default'; }
    } catch (_e) { this._permission = 'unsupported'; }
    return this._permission;
  };

  /** @private Emit a fact, swallowing any bus error. */
  PushNotificationManager.prototype._emit = function (event, payload) {
    try { if (this._bus) this._bus.emit(event, payload); } catch (_e) { /* noop */ }
  };

  /** @private Build a delivery notice from an urgency.raised payload. */
  PushNotificationManager.prototype._noticeFromUrgency = function (u) {
    u = u || {};
    return { tier: u.tier || 3, kind: u.kind || 'nudge', title: u.cta || 'Alley Kingz',
      body: u.cta || '', crewId: u.crewId, deadline: u.deadline };
  };

  /** @private Are we inside quiet hours right now (local time)? */
  PushNotificationManager.prototype._inQuietHours = function () {
    var h = new Date().getHours(); var s = this._quiet.start, e = this._quiet.end;
    return s <= e ? (h >= s && h < e) : (h >= s || h < e); // handles wrap past midnight
  };

  /**
   * Request OS notification permission. Should be called AFTER the player has
   * felt value (first crew join / first donation), never on cold load.
   * STUB: resolves the detected state without forcing a prompt offline.
   *
   * @returns {Promise<string>} resolves the resulting permission state.
   */
  PushNotificationManager.prototype.requestPermission = function () {
    var self = this;
    try {
      if (typeof Notification === 'undefined' || typeof Notification.requestPermission !== 'function') {
        self._permission = 'unsupported';
        self._emit('push.permission.changed', { state: self._permission });
        return Promise.resolve(self._permission);
      }
      return Promise.resolve(Notification.requestPermission()).then(function (state) {
        self._permission = state || 'default';
        self._emit('push.permission.changed', { state: self._permission });
        return self._permission;
      });
    } catch (_e) {
      self._permission = 'unsupported';
      self._emit('push.permission.changed', { state: self._permission });
      return Promise.resolve(self._permission);
    }
  };

  /** @returns {string} current permission state (no prompt). */
  PushNotificationManager.prototype.permission = function () { return this._permission; };

  /**
   * Route a notice down the channel ladder, enforcing tone, quiet hours, and the
   * per-tier daily cap. STUB: decides the channel + emits push.* facts but does
   * not actually post the OS notification yet.
   *
   * Decision order (see SPEC Section 7):
   *   tone=off / kind muted        -> suppressed
   *   over per-tier cap            -> downgrade to in-app (suppressed OS push)
   *   quiet hours (non-Tier-1)     -> downgrade to in-app/badge
   *   granted + budget + waking    -> OS push (Web Push when SW is live)
   *   else                         -> in-app banner / next-open badge
   *
   * @param {Object} notice - { tier, kind, title, body, crewId, deadline }.
   * @returns {{channel:string, delivered:boolean}}
   */
  PushNotificationManager.prototype.deliver = function (notice) {
    notice = notice || {}; var tier = notice.tier || 3; var kind = notice.kind || 'nudge';
    this._emit('push.queued', { channel: 'pending', kind: kind, title: notice.title });

    if (this._tone === 'off' || this._muted[kind]) {
      this._emit('push.suppressed', { channel: 'muted', kind: kind, reason: 'tone/mute' });
      return { channel: 'muted', delivered: false };
    }

    var capped = (this._fired[tier] || 0) >= (this._caps[tier] || 0);
    var quiet = this._inQuietHours() && tier !== 1; // Tier-1 siege may break quiet once
    var canOsPush = this._permission === 'granted' && !capped && !quiet;

    var channel;
    if (canOsPush) { channel = 'os_push'; this._fired[tier] = (this._fired[tier] || 0) + 1; }
    else if (tier === 1) { channel = 'inapp_banner'; }   // siege always shows in-app
    else { channel = capped ? 'badge' : 'inapp_banner'; }

    // STUB: real impl shows Notification / posts to the in-app banner here.
    if (channel === 'os_push') this._emit('push.sent', { channel: channel, kind: kind, title: notice.title });
    else this._emit('push.suppressed', { channel: channel, kind: kind, reason: capped ? 'cap' : (quiet ? 'quiet' : 'no-permission') });
    return { channel: channel, delivered: channel === 'os_push' };
  };

  /**
   * Subscribe to Web Push (VAPID + service worker). STUB: resolves null until
   * the SW + the ak-push edge fn / ak_push_subscriptions table are live.
   * @returns {Promise<Object|null>}
   */
  PushNotificationManager.prototype.subscribe = function () {
    // TODO: navigator.serviceWorker.ready -> pushManager.subscribe -> POST to ak-push.
    return Promise.resolve(null);
  };

  /**
   * Mute / unmute a notice kind (e.g. "betrayal", "shield", "war_countdown").
   * @param {string}  kind
   * @param {boolean} on - true to mute, false to unmute.
   * @returns {void}
   */
  PushNotificationManager.prototype.mute = function (kind, on) {
    if (!kind) return;
    if (on) this._muted[kind] = true; else delete this._muted[kind];
  };

  /**
   * Set quiet-hours window (local 24h clock; wraps past midnight).
   * @param {number} start - hour [0-23] quiet begins.
   * @param {number} end   - hour [0-23] quiet ends.
   * @returns {void}
   */
  PushNotificationManager.prototype.setQuietHours = function (start, end) {
    if (typeof start === 'number') this._quiet.start = start;
    if (typeof end === 'number') this._quiet.end = end;
  };

  /**
   * Set delivery tone. "off" silences chat weapons + downgrades all OS pushes.
   * @param {string} tone - hype | competitive | off.
   * @returns {void}
   */
  PushNotificationManager.prototype.setTone = function (tone) {
    if (tone === 'hype' || tone === 'competitive' || tone === 'off') this._tone = tone;
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_PushNotificationManager = new PushNotificationManager();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      PushNotificationManager: PushNotificationManager,
      AK_PushNotificationManager: AK_PushNotificationManager
    };
  }
  if (typeof global !== 'undefined') {
    global.AK_PushNotificationManager = AK_PushNotificationManager;
    global.AK_PushNotificationManager_Class = PushNotificationManager;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
