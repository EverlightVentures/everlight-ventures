/**
 * MainTowerSystem -- Alley Kingz MODULE_11_WHITEOUT
 * ================================================
 * The Main Tower is the crew furnace. It does two jobs:
 *   1. Caps every other building (no building may exceed the tower level).
 *   2. Caps crew size (L1=5, L10=20, L30=100 members; interpolated between).
 * Upgrading it is the social arms race that gates the whole crew.
 *
 * ARCHITECTURE: this system imports NO other module. The EventBus is injected
 * via the constructor; all cross-module communication is publish/subscribe.
 * See ./SPEC.md section 1 for the full contract.
 *
 * STATUS: stub. Method bodies are intentionally unimplemented (TODO). Wiring,
 * config-driven cap curves, and server-authoritative validation come later.
 */

/** Crew-size cap anchor points. Between anchors the cap interpolates linearly
 *  and rounds down. Live values come from ConfigLoader; these are the contract.
 *  @type {Array<{level:number, cap:number}>} */
const MEMBER_CAP_ANCHORS = [
  { level: 1, cap: 5 },
  { level: 10, cap: 20 },
  { level: 30, cap: 100 },
];

/** Event names this system touches. Local copy (no cross-module import). */
const EVENTS = Object.freeze({
  // subscribes
  TOWER_UPGRADE_REQUESTED: 'TOWER_UPGRADE_REQUESTED',
  BUILDING_UPGRADE_REQUESTED: 'BUILDING_UPGRADE_REQUESTED',
  CREW_JOIN_REQUESTED: 'CREW_JOIN_REQUESTED',
  RAID_RESOLVED: 'RAID_RESOLVED',
  // publishes
  TOWER_LEVEL_CHANGED: 'TOWER_LEVEL_CHANGED',
  CREW_CAP_CHANGED: 'CREW_CAP_CHANGED',
  BUILDING_CAP_CHANGED: 'BUILDING_CAP_CHANGED',
  BUILDING_UPGRADE_VETOED: 'BUILDING_UPGRADE_VETOED',
  CREW_JOIN_VETOED: 'CREW_JOIN_VETOED',
  TOWER_UNDER_SIEGE: 'TOWER_UNDER_SIEGE',
});

class MainTowerSystem {
  /**
   * @param {object} bus    Injected EventBus with on(event, handler) and
   *                         emit(event, payload). Never imported across modules.
   * @param {object} [config] Optional balance config (cap curves, etc.) from
   *                          ConfigLoader. Falls back to MEMBER_CAP_ANCHORS.
   */
  constructor(bus, config = {}) {
    /** @private */ this.bus = bus;
    /** @private */ this.config = config;
    /** @private @type {Map<string, {towerLevel:number, integrity:number}>} */
    this.towers = new Map();
  }

  /** Subscribe to inbound events. Called once by the bootstrapper after construction. */
  attach() {
    // TODO: wire subscriptions, e.g.
    //   this.bus.on(EVENTS.BUILDING_UPGRADE_REQUESTED, (p) => this.vetoBuildingIfOverCap(p));
    //   this.bus.on(EVENTS.CREW_JOIN_REQUESTED, (p) => this.vetoJoinIfFull(p));
    //   this.bus.on(EVENTS.TOWER_UPGRADE_REQUESTED, (p) => this.upgradeTower(p));
    //   this.bus.on(EVENTS.RAID_RESOLVED, (p) => this.onRaidResolved(p));
    throw new Error('MainTowerSystem.attach: not implemented');
  }

  /** Remove all subscriptions (teardown / hot-reload). */
  detach() {
    // TODO: unsubscribe everything wired in attach().
    throw new Error('MainTowerSystem.detach: not implemented');
  }

  /**
   * Max crew members allowed at a given tower level (piecewise-linear between
   * the anchor points, rounded down). Server is authoritative; this is the
   * client-side predictor.
   * @param {number} towerLevel
   * @returns {number} member cap
   */
  memberCapForLevel(towerLevel) {
    // TODO: interpolate across MEMBER_CAP_ANCHORS (or config curve).
    throw new Error('MainTowerSystem.memberCapForLevel: not implemented');
  }

  /**
   * Building cap == tower level. A building may never exceed it.
   * @param {string} crewId
   * @returns {number} max allowed building level
   */
  buildingCapForCrew(crewId) {
    // TODO: return this.towers.get(crewId)?.towerLevel.
    throw new Error('MainTowerSystem.buildingCapForCrew: not implemented');
  }

  /**
   * Apply a tower level change. Emits TOWER_LEVEL_CHANGED + cap-change events.
   * Does NOT auto-kick members on downgrade-over-cap (freeze recruiting instead;
   * see SPEC O-1).
   * @param {{crewId:string, byPlayerId:string, targetLevel:number}} payload
   */
  upgradeTower(payload) {
    // TODO: validate, mutate state, emit TOWER_LEVEL_CHANGED / CREW_CAP_CHANGED /
    //       BUILDING_CAP_CHANGED.
    throw new Error('MainTowerSystem.upgradeTower: not implemented');
  }

  /**
   * Veto a building upgrade if its target exceeds the tower cap.
   * @param {{crewId:string, buildingId:string, targetLevel:number}} payload
   */
  vetoBuildingIfOverCap(payload) {
    // TODO: if targetLevel > buildingCap -> emit BUILDING_UPGRADE_VETOED.
    throw new Error('MainTowerSystem.vetoBuildingIfOverCap: not implemented');
  }

  /**
   * Veto a join request if the crew is at its member cap.
   * @param {{crewId:string, playerId:string}} payload
   */
  vetoJoinIfFull(payload) {
    // TODO: if memberCount >= memberCap -> emit CREW_JOIN_VETOED.
    throw new Error('MainTowerSystem.vetoJoinIfFull: not implemented');
  }

  /**
   * React to a resolved raid on the Main Tower (integrity drop -> siege ping).
   * Raid damage math is owned by M03 PVP_RAID; this only reacts.
   * @param {{targetCrewId:string, buildingId:string, integrityDelta:number}} payload
   */
  onRaidResolved(payload) {
    // TODO: if buildingId === 'main_tower' -> update integrity, emit TOWER_UNDER_SIEGE.
    throw new Error('MainTowerSystem.onRaidResolved: not implemented');
  }
}

export default MainTowerSystem;
export { EVENTS, MEMBER_CAP_ANCHORS };
