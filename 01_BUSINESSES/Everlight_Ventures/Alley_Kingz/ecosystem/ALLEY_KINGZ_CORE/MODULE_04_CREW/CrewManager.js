// ==========================================================================
// ALLEY KINGZ CORE -- MODULE_04_CREW / CrewManager.js   [STUB]
// The headless brain behind Crew HQ: crews, chat, reinforcements, war, streak.
//
// ARCHITECTURE LAW (see ../README.md and ./SPEC.md):
//   This module imports NOTHING and is imported by NOTHING. Every cross-module
//   conversation goes over window.AK_EventBus. CrewManager owns NO source of
//   truth: it is a thin, server-authoritative client over the STAGED Supabase
//   social layer. All writes go through the ak-crew / ak-chat edge functions
//   (service role); the client only sends intents, renders facts, and EMITS
//   plain "crew.*" facts on the bus. It NEVER decides what is urgent, who to
//   nudge, or what push to fire -- that is MODULE_05_SOCIAL_URGENCY's job.
//
// STATUS: documented stub. Method bodies emit the right facts but perform no
//   real network calls yet, so wiring this in cannot break a running build.
//   Fill in the edge-fn calls (reuse game/social.js's call() pattern) later.
//
// REUSE MAP (see SPEC Section 3):
//   crews/roster   -> ak_crews / ak_crew_members / ak_crew_requests
//   reinforcements -> ak_donation_requests / ak_donations / ak_grants
//   war + streak   -> ak_crew_wars / ak_war_battles (+ ak_crews.war_streak)
//   chat           -> ak_chat_messages (send via ak-chat, recv via Realtime)
//   write path     -> supabase/functions/{ak-crew,ak-chat}
//   shared client  -> AKAccount.client()  (auto-attaches the signed-in JWT)
//
// NO BUILD STEP. NO npm. Plain ES5-safe JS so it runs anywhere the game runs.
// ==========================================================================

(function (global) {
  'use strict';

  /**
   * Headless crew/social data manager. Caches the player's crew snapshot and
   * brokers every crew action to the server, emitting facts on the bus.
   *
   * @class
   * @param {Object} [bus] - AK_EventBus instance (defaults to the singleton).
   */
  function CrewManager(bus) {
    /** @private Shared event bus used for ALL cross-module comms. */
    this._bus = bus || (typeof global !== 'undefined' ? global.AK_EventBus : null);
    /** @private Cached snapshot: the crew the player belongs to (or null). */
    this._crew = null;
    /** @private Cached membership role: leader | co | elder | member | null. */
    this._role = null;
    /** @private Cached roster array. */
    this._members = [];
    /** @private Whether attach() already wired listeners (idempotent guard). */
    this._wired = false;
    /** @private Optional injected caller for the edge fns; see attach(opts). */
    this._call = null;
  }

  /**
   * Wire bus listeners and Realtime subscriptions. Idempotent: calling twice is
   * a no-op. STUB: registers the listener shape only; no Realtime yet.
   *
   * @param {Object} [bus]  - bus to use (overrides constructor bus).
   * @param {Object} [opts] - { call } optional edge-fn invoker
   *                          (payload-in, Promise<result>-out) for tests / DI.
   * @returns {CrewManager} this (chainable).
   */
  CrewManager.prototype.attach = function (bus, opts) {
    if (bus) this._bus = bus;
    if (opts && typeof opts.call === 'function') this._call = opts.call;
    if (this._wired || !this._bus) return this;
    var self = this;
    // Refresh + re-claim grants whenever auth changes.
    this._bus.on('auth.changed', function () { self.mine(); });
    // Forward ladder results into an active war (server decides if it counts).
    this._bus.on('match.win', function () { self.reportWarResult('win'); });
    this._bus.on('match.loss', function () { self.reportWarResult('loss'); });
    this._wired = true;
    return this;
  };

  /**
   * Invoke an edge function. STUB: if no invoker was injected via attach(opts),
   * resolves an offline result so callers never throw. Real impl forwards to
   * AKAccount.client().functions.invoke(fn, { body }) per game/social.js.
   *
   * @private
   * @param {string} fn   - edge function name ("ak-crew" | "ak-chat").
   * @param {Object} body - action payload.
   * @returns {Promise<Object>} resolves { ok, ... }; never rejects.
   */
  CrewManager.prototype._invoke = function (fn, body) {
    if (typeof this._call === 'function') {
      try { return Promise.resolve(this._call(fn, body)); }
      catch (e) { return Promise.resolve({ ok: false, error: String(e && e.message || e) }); }
    }
    // TODO: wire AKAccount.client().functions.invoke. For now: graceful offline.
    void fn; void body;
    return Promise.resolve({ ok: false, error: 'offline' });
  };

  /** @private Emit a fact, swallowing any bus error (never blocks callers). */
  CrewManager.prototype._emit = function (event, payload) {
    try { if (this._bus) this._bus.emit(event, payload); } catch (_e) { /* noop */ }
  };

  /** @private Standard error shape + "crew.error" fact for a failed action. */
  CrewManager.prototype._fail = function (action, res) {
    var out = { ok: false, error: (res && res.error) || 'error' };
    this._emit('crew.error', { action: action, error: out.error });
    return out;
  };

  /**
   * Create a crew. On success the founder becomes leader (server-enforced).
   * @param {Object} spec - { name, tag, faction, privacy, description, region }.
   * @returns {Promise<{ok:boolean, crew?:Object, error?:string}>}
   */
  CrewManager.prototype.create = function (spec) {
    var self = this;
    return this._invoke('ak-crew', { action: 'create', /* spread */ name: (spec || {}).name,
      tag: (spec || {}).tag, faction: (spec || {}).faction, privacy: (spec || {}).privacy,
      description: (spec || {}).description, region: (spec || {}).region }).then(function (r) {
      if (!r || !r.ok) return self._fail('create', r);
      self._crew = r.crew || null; self._role = 'leader'; self._members = (r.crew && r.crew.members) || [];
      self._emit('crew.created', { crewId: r.crew && r.crew.id, name: r.crew && r.crew.name,
        tag: r.crew && r.crew.tag, faction: r.crew && r.crew.faction, leaderId: r.crew && r.crew.created_by });
      self._emit('crew.roster.updated', { crewId: r.crew && r.crew.id, members: self._members });
      return { ok: true, crew: self._crew };
    });
  };

  /**
   * Join (or request to join) a crew.
   * @param {string} crewId
   * @returns {Promise<{ok:boolean, requested?:boolean, error?:string}>}
   */
  CrewManager.prototype.join = function (crewId) {
    var self = this;
    return this._invoke('ak-crew', { action: 'join', crew_id: crewId }).then(function (r) {
      if (!r || !r.ok) return self._fail('join', r);
      self._emit('crew.joined', { crewId: crewId, requested: !!r.requested });
      if (!r.requested) self.mine();
      return { ok: true, requested: !!r.requested };
    });
  };

  /**
   * Leave the player's current crew (server handles succession / disband).
   * @returns {Promise<{ok:boolean, error?:string}>}
   */
  CrewManager.prototype.leave = function () {
    var self = this; var prevId = this._crew && this._crew.id;
    return this._invoke('ak-crew', { action: 'leave' }).then(function (r) {
      if (!r || !r.ok) return self._fail('leave', r);
      self._crew = null; self._role = null; self._members = [];
      self._emit('crew.left', { crewId: prevId, disbanded: !!r.disbanded });
      return { ok: true };
    });
  };

  /**
   * Browse / search the crew directory.
   * @param {string} [query]
   * @returns {Promise<{ok:boolean, crews?:Array, error?:string}>}
   */
  CrewManager.prototype.list = function (query) {
    var self = this;
    return this._invoke('ak-crew', { action: 'list', q: query || '' }).then(function (r) {
      if (!r || !r.ok) return self._fail('list', r);
      self._emit('crew.directory.loaded', { crews: r.crews || [] });
      return { ok: true, crews: r.crews || [] };
    });
  };

  /**
   * Load the player's own crew snapshot and cache it.
   * @returns {Promise<{ok:boolean, crew?:Object, role?:string, members?:Array}>}
   */
  CrewManager.prototype.mine = function () {
    var self = this;
    return this._invoke('ak-crew', { action: 'mine' }).then(function (r) {
      if (!r || !r.ok) return self._fail('mine', r);
      self._crew = r.crew || null; self._role = r.role || null; self._members = r.members || [];
      self._emit('crew.loaded', { crew: self._crew, role: self._role, members: self._members });
      return { ok: true, crew: self._crew, role: self._role, members: self._members };
    });
  };

  /**
   * Send a chat message (server gates rate-limit + profanity + ban-check).
   * @param {string} scope - "world" | "crew".
   * @param {string} body  - message text (1-200 chars; server-enforced).
   * @returns {Promise<{ok:boolean, message?:Object, error?:string}>}
   */
  CrewManager.prototype.sendChat = function (scope, body) {
    var self = this; var faction = this._crew ? this._crew.faction : null;
    return this._invoke('ak-chat', { action: 'send', scope: scope, body: body, faction: faction }).then(function (r) {
      if (!r || !r.ok) return self._fail('sendChat', r);
      if (r.message) self._emit('crew.chat.message', {
        id: r.message.id, scope: scope, crewId: self._crew && self._crew.id,
        userId: r.message.user_id, name: r.message.name, faction: r.message.faction,
        body: r.message.body, at: r.message.created_at });
      return { ok: true, message: r.message };
    });
  };

  /**
   * Post a reinforcement (donation) request to the crew.
   * @param {string} cardId
   * @param {number} qty
   * @returns {Promise<{ok:boolean, error?:string}>}
   */
  CrewManager.prototype.requestReinforcement = function (cardId, qty) {
    var self = this;
    return this._invoke('ak-crew', { action: 'don-request', card_id: cardId, qty_req: qty }).then(function (r) {
      if (!r || !r.ok) return self._fail('requestReinforcement', r);
      self._emit('crew.reinforcement.requested', { requestId: r.id, crewId: self._crew && self._crew.id,
        cardId: cardId, qtyReq: qty, expiresAt: r.expires_at });
      return { ok: true };
    });
  };

  /**
   * Fill (donate to) an open reinforcement request.
   * @param {string} requestId
   * @returns {Promise<{ok:boolean, filled?:number, error?:string}>}
   */
  CrewManager.prototype.fillReinforcement = function (requestId) {
    var self = this;
    return this._invoke('ak-crew', { action: 'don-fill', request_id: requestId }).then(function (r) {
      if (!r || !r.ok) return self._fail('fillReinforcement', r);
      self._emit('crew.reinforcement.filled', { requestId: requestId, donorId: r.donor_id,
        recipientId: r.recipient_id, cardId: r.card_id, qty: r.filled });
      return { ok: true, filled: r.filled };
    });
  };

  /**
   * Forward a ladder result into the active crew war. The server decides if it
   * counts (war state, tickets) and returns the new score. STUB: no-op offline.
   * @param {string} result - "win" | "loss".
   * @returns {Promise<{ok:boolean, score?:number, error?:string}>}
   */
  CrewManager.prototype.reportWarResult = function (result) {
    var self = this;
    if (!this._crew) return Promise.resolve({ ok: false, error: 'no-crew' });
    return this._invoke('ak-crew', { action: 'war-report', result: result }).then(function (r) {
      if (!r || !r.ok) return { ok: false, error: (r && r.error) || 'no-war' };
      self._emit('crew.war.scored', { warId: r.war_id, score: r.score, oppScore: r.opp_score,
        fameDelta: r.fame_delta, userId: r.user_id });
      if (r.ended) self._emit('crew.war.ended', { warId: r.war_id, won: !!r.won, streak: r.streak });
      if (typeof r.streak === 'number') self._emit('crew.streak.updated',
        { crewId: self._crew && self._crew.id, streak: r.streak, broken: !!r.streak_broken });
      return { ok: true, score: r.score };
    });
  };

  /**
   * Synchronous snapshot of the cached crew state (no network).
   * @returns {{crew:(Object|null), role:(string|null), members:Array}}
   */
  CrewManager.prototype.state = function () {
    return { crew: this._crew, role: this._role, members: this._members };
  };

  // ---- export: UMD-style, matches engine.js / canon.js convention ----------
  var AK_CrewManager = new CrewManager();

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CrewManager: CrewManager, AK_CrewManager: AK_CrewManager };
  }
  if (typeof global !== 'undefined') {
    global.AK_CrewManager = AK_CrewManager;
    global.AK_CrewManager_Class = CrewManager;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
