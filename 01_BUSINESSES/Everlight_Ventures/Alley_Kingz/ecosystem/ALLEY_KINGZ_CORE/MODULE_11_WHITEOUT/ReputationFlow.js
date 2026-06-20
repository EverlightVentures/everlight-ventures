/**
 * ReputationFlow -- Alley Kingz MODULE_11_WHITEOUT
 * ================================================
 * Reputation is the heat / loss-aversion engine:
 *   - The Main Tower GENERATES reputation per hour (scales with tower level,
 *     crew-help bonus, and tower integrity).
 *   - Reputation DECAYS when the crew goes dark (zero active members); one
 *     active member halts decay -- the "come on buddy" hook.
 *   - Reputation is RAIDABLE (a capped, anti-whale-scaled slice can be stolen).
 *   - Dropping BELOW a level threshold puts the crew in STARVED state: members
 *     earn less, become poachable, and all buildings run at -50% output. Cleared
 *     only with hysteresis (rep must climb a margin ABOVE threshold).
 *
 * ARCHITECTURE: imports NO other module. The EventBus is injected via the
 * constructor; all cross-module comms are publish/subscribe. Time-based accrual
 * is driven by an external CLOCK_TICK, never a local wall-clock timer (testable
 * + server-reconcilable). See ./SPEC.md section 2.
 *
 * STATUS: stub. Method bodies are intentionally unimplemented (TODO).
 */

/** Crew reputation lifecycle states. */
const REP_STATE = Object.freeze({ OK: 'OK', STARVED: 'STARVED' });

/** Event names this system touches. Local copy (no cross-module import). */
const EVENTS = Object.freeze({
  // subscribes
  TOWER_LEVEL_CHANGED: 'TOWER_LEVEL_CHANGED',
  CREW_PRESENCE_CHANGED: 'CREW_PRESENCE_CHANGED',
  RAID_RESOLVED: 'RAID_RESOLVED',
  CREW_HELP_APPLIED: 'CREW_HELP_APPLIED',
  CLOCK_TICK: 'CLOCK_TICK',
  // publishes
  REP_TICK: 'REP_TICK',
  REP_THRESHOLD_BREACHED: 'REP_THRESHOLD_BREACHED',
  REP_RESTORED: 'REP_RESTORED',
  REP_RAIDED: 'REP_RAIDED',
  CREW_STARVED_PENALTY: 'CREW_STARVED_PENALTY',
});

class ReputationFlow {
  /**
   * @param {object} bus    Injected EventBus with on(event, handler) and
   *                         emit(event, payload). Never imported across modules.
   * @param {object} [config] Balance config (base/decay/threshold/storage per
   *                          level, raid steal pct + abs cap, hysteresis margin,
   *                          STARVED multipliers) from ConfigLoader.
   */
  constructor(bus, config = {}) {
    /** @private */ this.bus = bus;
    /** @private */ this.config = config;
    /** @private @type {Map<string, {stored:number, perHour:number, state:string,
     *                                threshold:number, storageCap:number,
     *                                activeCount:number, integrity:number,
     *                                crewHelpBonus:number, lastTickAt:number}>} */
    this.crews = new Map();
  }

  /** Subscribe to inbound events. Called once by the bootstrapper. */
  attach() {
    // TODO: wire subscriptions, e.g.
    //   this.bus.on(EVENTS.CLOCK_TICK, (p) => this.tick(p.now));
    //   this.bus.on(EVENTS.TOWER_LEVEL_CHANGED, (p) => this.onTowerLevel(p));
    //   this.bus.on(EVENTS.CREW_PRESENCE_CHANGED, (p) => this.onPresence(p));
    //   this.bus.on(EVENTS.RAID_RESOLVED, (p) => this.onRaid(p));
    //   this.bus.on(EVENTS.CREW_HELP_APPLIED, (p) => this.onHelp(p));
    throw new Error('ReputationFlow.attach: not implemented');
  }

  /** Remove all subscriptions (teardown / hot-reload). */
  detach() {
    // TODO: unsubscribe everything wired in attach().
    throw new Error('ReputationFlow.detach: not implemented');
  }

  /**
   * Current reputation generated per hour for a crew:
   *   base[towerLevel] * (1 + crewHelpBonus) * (integrity / 100).
   * Server is authoritative; this is the client predictor.
   * @param {string} crewId
   * @returns {number} reputation per hour
   */
  repPerHour(crewId) {
    // TODO: compute from config base, crewHelpBonus, and integrity factor.
    throw new Error('ReputationFlow.repPerHour: not implemented');
  }

  /**
   * Advance all crews by the elapsed time since their last tick. Accrues
   * generation (capped at storageCap) when active; applies decay when the crew
   * has zero active members. Emits REP_TICK and STARVED transitions.
   * @param {number} now epoch ms from the Live Ops clock adapter
   */
  tick(now) {
    // TODO: for each crew, accrue or decay, clamp [0, storageCap], then
    //       evaluateThreshold(crewId) and emit REP_TICK.
    throw new Error('ReputationFlow.tick: not implemented');
  }

  /**
   * Evaluate STARVED entry/exit with hysteresis. Enter when stored < threshold;
   * exit only when stored climbs past threshold + margin (no flicker). Emits
   * REP_THRESHOLD_BREACHED / REP_RESTORED and CREW_STARVED_PENALTY on entry.
   * @param {string} crewId
   */
  evaluateThreshold(crewId) {
    // TODO: compare stored vs threshold (+/- hysteresis margin), flip state,
    //       emit penalty payload { earnMult, buildingOutputMult, poachable }.
    throw new Error('ReputationFlow.evaluateThreshold: not implemented');
  }

  /**
   * Apply a reputation raid: steal min(stored * raidStealPct, raidStealAbsCap),
   * anti-whale-scaled. Emits REP_RAIDED. Burn/attacker-credit split is owned by
   * M06 ECONOMY (see SPEC O-2).
   * @param {{targetCrewId:string, byCrewId:string, type:string, amount:number}} payload
   */
  onRaid(payload) {
    // TODO: if type === 'reputation' -> deduct stolen, emit REP_RAIDED, then
    //       evaluateThreshold(targetCrewId).
    throw new Error('ReputationFlow.onRaid: not implemented');
  }

  /**
   * Update active-member count; one active member halts decay.
   * @param {{crewId:string, activeCount:number}} payload
   */
  onPresence(payload) {
    // TODO: store activeCount for the crew (used by tick() decay branch).
    throw new Error('ReputationFlow.onPresence: not implemented');
  }

  /**
   * Re-scale base / threshold / storage cap when the tower level changes.
   * @param {{crewId:string, toLevel:number}} payload
   */
  onTowerLevel(payload) {
    // TODO: refresh per-level config values for the crew.
    throw new Error('ReputationFlow.onTowerLevel: not implemented');
  }

  /**
   * Update the crew-help generation bonus.
   * @param {{crewId:string, activeBonus:number}} payload
   */
  onHelp(payload) {
    // TODO: set crewHelpBonus for the crew.
    throw new Error('ReputationFlow.onHelp: not implemented');
  }
}

export default ReputationFlow;
export { EVENTS, REP_STATE };
