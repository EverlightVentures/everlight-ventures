/* ==========================================================================
   ALLEY KINGZ // MODULE_06_ECONOMY // CurrencyManager (STUB)
   --------------------------------------------------------------------------
   Owns the in-game ALK ledger: balance, locked (staked) balance, the daily
   emission cap, sink validate+debit, staking lock/unlock, and the rolling
   deflation tracker (<2%/mo inflation, 40% staked targets).

   ALK is NOT $BCARDD. ALK is the off-chain server-authoritative in-game token
   (see SPEC.md sec 0). $BCARDD is the on-chain settlement coin and is bridged
   only by a MODULE_10 adapter, never from here.

   ARCHITECTURE LAW: this module imports NOTHING. The EventBus is injected via
   init(bus, opts). All cross-module comms are pub/sub. It reuses the existing
   game economy by EVENT (ECONOMY_EARN -> bootstrapper -> AK_ECON.mutateProfile),
   never by import.

   Headless-safe: no top-level DOM / localStorage. Persistence is delegated to
   the injected opts.store (defaults to an in-memory object) so the node harness
   never throws.
   ========================================================================== */
(function (global) {
  "use strict";

  /**
   * Daily ALK emission ceiling (anti-inflation hard cap, SPEC sec 1). Paid
   * inflows (source:"iap") bypass this; farmed inflows do not. Treasury-tunable.
   * @const {number}
   */
  var DEFAULT_DAILY_EMISSION_CAP = 2000;

  /** Staking lock duration in ms (30-day lock, SPEC sec 3). @const {number} */
  var STAKE_LOCK_MS = 30 * 24 * 60 * 60 * 1000;

  /** Inflation alert threshold, fraction/month (SPEC sec 4). @const {number} */
  var INFLATION_TARGET = 0.02;

  /** Staked-ratio target, fraction of circulating (SPEC sec 4). @const {number} */
  var STAKED_TARGET = 0.40;

  /**
   * @typedef {Object} CurrencyState
   * @property {number} alk        Spendable ALK balance.
   * @property {number} alkLocked  Staked ALK (not spendable until unlockAt).
   * @property {number} unlockAt   Epoch ms when the locked stake matures (0 = none).
   * @property {number} emittedToday Farmed ALK granted in the current UTC day.
   * @property {number} dayKey      UTC day index the emittedToday counter belongs to.
   */

  /**
   * CurrencyManager. Construct, then call init(bus, opts) once at boot.
   * No work happens until init -- the constructor only sets defaults so the
   * file is side-effect-free to load.
   * @constructor
   */
  function CurrencyManager() {
    /** @type {?Object} injected EventBus (must expose .emit(name,payload) and .on(name,fn)) */
    this.bus = null;
    /** @type {CurrencyState} */
    this.state = { alk: 0, alkLocked: 0, unlockAt: 0, emittedToday: 0, dayKey: 0 };
    /** @type {number} */
    this.dailyCap = DEFAULT_DAILY_EMISSION_CAP;
    /** @type {?Object} pluggable persistence: { load():state, save(state):void } */
    this.store = null;
    /** @type {function():number} clock injection for tests (defaults Date.now). */
    this.now = function () { return Date.now(); };
    /** @type {Array<{t:number,emit:number,burn:number}>} trailing 30d ledger for deflation math. */
    this._flowLog = [];
    /** @type {number} total ALK ever burned (reflects ALK_BURNED events). */
    this._burnedTotal = 0;
  }

  /**
   * Wire the module to the bus and load persisted state. Idempotent-ish: call once.
   * @param {Object} bus  EventBus with emit(name,payload) + on(name,handler).
   * @param {Object} [opts]
   * @param {Object}   [opts.store]    persistence adapter {load,save}.
   * @param {number}   [opts.dailyCap] override daily emission cap.
   * @param {function} [opts.now]      clock for tests.
   * @returns {CurrencyManager} this
   */
  CurrencyManager.prototype.init = function (bus, opts) {
    opts = opts || {};
    this.bus = bus;
    if (opts.store) this.store = opts.store;
    if (typeof opts.dailyCap === "number") this.dailyCap = opts.dailyCap;
    if (typeof opts.now === "function") this.now = opts.now;
    if (this.store && typeof this.store.load === "function") {
      try { var s = this.store.load(); if (s) this.state = s; } catch (_) {}
    }
    this._subscribe();
    return this;
  };

  /**
   * Subscribe to every inbound event named in SPEC sec 6. STUB: handlers are
   * wired but their bodies are TODO. Listening to ALK_BURNED keeps the deflation
   * tracker honest (TokenSink owns the actual burn).
   * @private
   */
  CurrencyManager.prototype._subscribe = function () {
    if (!this.bus || typeof this.bus.on !== "function") return;
    var self = this;
    this.bus.on("ECONOMY_EARN", function (p) { self.onEarn(p); });
    this.bus.on("SINK_REQUEST", function (p) { self.onSinkRequest(p); });
    this.bus.on("STAKE_LOCK", function (p) { self.onStakeLock(p); });
    this.bus.on("STAKE_UNLOCK", function (p) { self.onStakeUnlock(p); });
    this.bus.on("STAKER_POOL_PAYOUT", function (p) { self.onStakerPayout(p); });
    this.bus.on("ALK_BURNED", function (p) { self.onBurnObserved(p); });
  };

  // ---- inflows -------------------------------------------------------------

  /**
   * Credit ALK from an inflow. Farmed sources are gated by the daily emission
   * cap; paid (source:"iap") bypasses it. Emits ECONOMY_BALANCE_CHANGED, or
   * ECONOMY_EMISSION_CAPPED when the cap clips the grant.
   * @param {{source:string, amount:number, meta?:Object}} p
   * @returns {void}
   * TODO: roll daily counter on dayKey change; clip to cap; persist; emit.
   */
  CurrencyManager.prototype.onEarn = function (p) {
    // STUB
  };

  // ---- sinks (outflows) ----------------------------------------------------

  /**
   * Validate balance for a sink, debit it, and hand off to TokenSink via
   * SINK_CONFIRMED. On shortfall, debit nothing and emit SINK_DENIED. The split
   * (burn / treasury / staker) is TokenSink's job -- this only moves balance out.
   * @param {{sinkId:string, amount?:number, meta?:Object}} p
   *   amount optional: prestige/war/shield/relocate/reroll/mint carry fixed costs
   *   from TokenSink's COST table; marketplace passes the sale amount in meta.
   * @returns {void}
   * TODO: resolve cost (fixed table vs % vs per-member); compare to this.state.alk;
   *       on ok debit + emit SINK_CONFIRMED; else emit SINK_DENIED {need,have}.
   */
  CurrencyManager.prototype.onSinkRequest = function (p) {
    // STUB
  };

  // ---- staking -------------------------------------------------------------

  /**
   * Move ALK from spendable -> locked for the 30-day lock. Emits STAKE_LOCKED
   * {amount, unlockAt}. Rejects if amount > spendable balance.
   * @param {{amount:number}} p
   * @returns {void}
   * TODO: validate; state.alk -= amount; state.alkLocked += amount;
   *       state.unlockAt = now + STAKE_LOCK_MS; persist; emit STAKE_LOCKED.
   */
  CurrencyManager.prototype.onStakeLock = function (p) {
    // STUB
  };

  /**
   * Return matured staked ALK to spendable balance. No-op (and no event) if the
   * lock has not matured (now < unlockAt). Emits STAKE_UNLOCKED on success.
   * @param {{amount:number}} p
   * @returns {void}
   * TODO: guard now >= unlockAt; move locked -> spendable; persist; emit.
   */
  CurrencyManager.prototype.onStakeUnlock = function (p) {
    // STUB
  };

  /**
   * Credit a staker's epoch dividend (share of the marketplace 2.5% pool) back
   * to spendable balance. This is a fee-share utility reward, NOT a promised
   * yield (SPEC sec 0 / LEGAL GATE 2). Emits ECONOMY_BALANCE_CHANGED.
   * @param {{playerShare:number}} p
   * @returns {void}
   * TODO: state.alk += playerShare; persist; emit ECONOMY_BALANCE_CHANGED.
   */
  CurrencyManager.prototype.onStakerPayout = function (p) {
    // STUB
  };

  // ---- deflation tracking --------------------------------------------------

  /**
   * Record an observed burn (TokenSink emitted ALK_BURNED) into the trailing
   * flow log so the deflation tracker can compute net inflation.
   * @param {{amount:number, sinkId:string}} p
   * @returns {void}
   * TODO: this._burnedTotal += amount; push {t:now, burn:amount} to _flowLog.
   */
  CurrencyManager.prototype.onBurnObserved = function (p) {
    // STUB
  };

  /**
   * Compute the trailing-30d net inflation and current staked ratio, emit
   * DEFLATION_TICK, and DEFLATION_ALERT when inflation breaches INFLATION_TARGET.
   * Called by the live-ops scheduler (M08), not on a self-timer.
   * @returns {{monthlyInflationPct:number, stakedPct:number, circulating:number, burned30d:number}}
   * TODO: window _flowLog to 30d; sum emit/burn; circulating = ledger total;
   *       stakedPct = locked / circulating; emit tick; alert if > target.
   */
  CurrencyManager.prototype.computeDeflation = function () {
    // STUB
    return { monthlyInflationPct: 0, stakedPct: 0, circulating: 0, burned30d: 0 };
  };

  /**
   * @returns {number} current spendable ALK balance (read-only convenience).
   */
  CurrencyManager.prototype.getBalance = function () { return this.state.alk; };

  // ---- export (global namespace, NOT a module import) ----------------------
  var NS = global.AK_CORE || (global.AK_CORE = {});
  NS.CurrencyManager = CurrencyManager;
  NS.ECONOMY_CONST = {
    DEFAULT_DAILY_EMISSION_CAP: DEFAULT_DAILY_EMISSION_CAP,
    STAKE_LOCK_MS: STAKE_LOCK_MS,
    INFLATION_TARGET: INFLATION_TARGET,
    STAKED_TARGET: STAKED_TARGET
  };
})(typeof window !== "undefined" ? window : globalThis);
