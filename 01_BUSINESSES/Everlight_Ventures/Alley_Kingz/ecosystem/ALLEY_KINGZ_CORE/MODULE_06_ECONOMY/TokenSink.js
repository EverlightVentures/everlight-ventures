/* ==========================================================================
   ALLEY KINGZ // MODULE_06_ECONOMY // TokenSink (STUB)
   --------------------------------------------------------------------------
   Owns the 7 burn sinks' split logic and the staker-pool accrual/payout. Does
   NOT hold the ALK balance (CurrencyManager does). It reacts to SINK_CONFIRMED
   (CurrencyManager already debited the player) and decides where the debited ALK
   goes: burned out of supply, routed to treasury, and/or accrued to stakers.

   The 7 sinks (LOCKED numbers, AK_MASTER_BLUEPRINT.md / SPEC.md sec 2):
     prestige 500 | war 200/member | shield 100 | relocate 150 | reroll 50 |
     marketplace 5% (2.5 burn + 2.5 stakers) | mint 25.
   Only `marketplace` splits; the other six are 100% burn.

   ARCHITECTURE LAW: imports NOTHING. EventBus injected via init(bus, opts). All
   comms pub/sub. Headless-safe (no top-level DOM / localStorage). Staker-pool
   accrual is in-game fee-share UTILITY, never a promised on-chain yield
   (SPEC sec 0 / LEGAL GATE 2).
   ========================================================================== */
(function (global) {
  "use strict";

  /**
   * Fixed ALK cost per sink. `marketplace` cost is computed from sale amount
   * (5%), so it is null here and resolved at request time. `war` is per-member,
   * multiplied by meta.memberCount.
   * @const {Object<string, ?number>}
   */
  var SINK_COST = {
    prestige: 500,
    war: 200,        // * memberCount
    shield: 100,
    relocate: 150,
    reroll: 50,
    marketplace: null, // 5% of sale amount, resolved from meta
    mint: 25
  };

  /**
   * Per-sink split in basis points of the debited amount: how much burns vs
   * accrues to the staker pool vs routes to treasury. Must sum to 10000.
   * marketplace = 50% burn + 50% stakers (i.e. of the 5% fee: 2.5 burn + 2.5
   * stakers). The other six are 100% burn.
   * @const {Object<string, {burnBps:number, stakerBps:number, treasuryBps:number}>}
   */
  var SINK_SPLIT = {
    prestige:    { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 },
    war:         { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 },
    shield:      { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 },
    relocate:    { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 },
    reroll:      { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 },
    marketplace: { burnBps: 5000,  stakerBps: 5000, treasuryBps: 0 },
    mint:        { burnBps: 10000, stakerBps: 0,    treasuryBps: 0 }
  };

  /** Marketplace fee rate (5% of sale), matches on-chain FEE+ROYALTY=500bps. @const {number} */
  var MARKETPLACE_FEE_BPS = 500;

  /**
   * TokenSink. Construct, then init(bus, opts) once at boot. Side-effect-free to
   * load.
   * @constructor
   */
  function TokenSink() {
    /** @type {?Object} injected EventBus. */
    this.bus = null;
    /** @type {number} ALK accrued to the staker pool this epoch (awaiting payout). */
    this.stakerPool = 0;
    /** @type {number} total ALK routed to treasury (running). */
    this.treasuryTotal = 0;
    /** @type {number} total ALK burned by this module (running). */
    this.burnedTotal = 0;
  }

  /**
   * Wire to the bus and subscribe. Idempotent-ish: call once.
   * @param {Object} bus  EventBus with emit(name,payload) + on(name,handler).
   * @param {Object} [opts] reserved for treasury-rate / store injection.
   * @returns {TokenSink} this
   */
  TokenSink.prototype.init = function (bus, opts) {
    this.bus = bus;
    this._subscribe();
    return this;
  };

  /**
   * Subscribe to inbound events (SPEC sec 6).
   * @private
   */
  TokenSink.prototype._subscribe = function () {
    if (!this.bus || typeof this.bus.on !== "function") return;
    var self = this;
    this.bus.on("SINK_CONFIRMED", function (p) { self.onSinkConfirmed(p); });
    this.bus.on("STAKER_EPOCH_CLOSE", function (p) { self.onEpochClose(p); });
  };

  /**
   * Resolve the ALK amount a sink consumes. Fixed sinks read SINK_COST; `war`
   * multiplies by meta.memberCount; `marketplace` is MARKETPLACE_FEE_BPS of
   * meta.saleAmount.
   * @param {string} sinkId
   * @param {Object} [meta] {memberCount?, saleAmount?}
   * @returns {number} ALK cost (0 if unknown sink).
   */
  TokenSink.prototype.resolveCost = function (sinkId, meta) {
    meta = meta || {};
    if (sinkId === "war") return (SINK_COST.war || 0) * (meta.memberCount | 0);
    if (sinkId === "marketplace") {
      return Math.floor(((meta.saleAmount | 0) * MARKETPLACE_FEE_BPS) / 10000);
    }
    var c = SINK_COST[sinkId];
    return (typeof c === "number") ? c : 0;
  };

  /**
   * Apply a sink's burn/treasury/staker split. CurrencyManager has ALREADY
   * debited the player; this only routes the debited ALK. Emits ALK_BURNED,
   * TREASURY_CREDITED, and/or STAKER_POOL_CREDITED per the split.
   * @param {{sinkId:string, amount:number, meta?:Object}} p
   *   amount = the ALK CurrencyManager debited (authoritative; use it, do not
   *   re-resolve, so the two modules can never disagree on a value).
   * @returns {void}
   * TODO: look up SINK_SPLIT[sinkId]; compute burn/staker/treasury portions
   *       (last portion = remainder to avoid rounding loss); update running
   *       totals + stakerPool; emit the matching events.
   */
  TokenSink.prototype.onSinkConfirmed = function (p) {
    // STUB
  };

  /**
   * Close a staker epoch: distribute this.stakerPool pro-rata across stakers
   * and reset the pool to 0. Emits one STAKER_POOL_PAYOUT per staker (consumed
   * by CurrencyManager.onStakerPayout). Staker weights come on the event (the
   * staking registry is M06's concern, supplied by the live-ops scheduler) so
   * TokenSink stays import-free.
   * @param {{epochId:string, stakers?:Array<{playerId:string, weight:number}>}} p
   * @returns {void}
   * TODO: sum weights; for each staker emit STAKER_POOL_PAYOUT
   *       {playerId, playerShare = pool * weight/totalWeight}; reset pool.
   */
  TokenSink.prototype.onEpochClose = function (p) {
    // STUB
  };

  // ---- export (global namespace, NOT a module import) ----------------------
  var NS = global.AK_CORE || (global.AK_CORE = {});
  NS.TokenSink = TokenSink;
  NS.SINK_COST = SINK_COST;
  NS.SINK_SPLIT = SINK_SPLIT;
  NS.MARKETPLACE_FEE_BPS = MARKETPLACE_FEE_BPS;
})(typeof window !== "undefined" ? window : globalThis);
