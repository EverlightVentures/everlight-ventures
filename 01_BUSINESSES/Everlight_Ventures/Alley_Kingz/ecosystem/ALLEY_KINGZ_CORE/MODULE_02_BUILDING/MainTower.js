/**
 * @file MainTower.js
 * @module MODULE_02_BUILDING
 * @summary Alley Kingz Main Tower -- the Crew HQ / "furnace" (Whiteout Survival DNA, MODULE_11).
 *          The apex raid target. Extends BuildingBase.
 *
 * @description
 * STUB. Intra-module import of BuildingBase is allowed (same module). No cross-module imports;
 * EventBus is dependency-injected and inherited. Opens `index.html?go=match` (the Arena/battle).
 * Whiteout DNA: the Main Tower caps crew size by level and generates Reputation Flow. The actual
 * crew-size enforcement + reputation decay cadence live in MODULE_04_CREW / MODULE_11_WHITEOUT;
 * this class only exposes the stats and emits the level changes those modules listen for.
 * Stats: `crewCap` (max crew members) and `repPerHour` (Reputation Flow generation) scale with level.
 */
import { BuildingBase } from './BuildingBase.js';

/** Crew-size caps by level, per the blueprint (L1=5, L10=20, L30=100). Index 0 unused. */
const CREW_CAP = [0, 5, 7, 9, 11, 13, 15, 16, 18, 19, 20];

export class MainTower extends BuildingBase {
  /**
   * @param {import('./BuildingBase.js').EventBus} eventBus
   * @param {Partial<import('./BuildingBase.js').BuildingConfig>} [config]
   */
  constructor(eventBus, config = {}) {
    super(eventBus, {
      type: 'main_tower',
      label: 'The Main Tower',
      screen: 'index.html?go=match',
      maxHp: 300,
      maxLevel: 30,
      stats: { crewCap: 5, repPerHour: 10 },
      ...config,
      id: config.id || 'main_tower',
    });
  }

  /**
   * @protected
   * @override
   * @param {number} level
   * @returns {{crewCap:number, repPerHour:number}}
   */
  _statsForLevel(level) {
    const cap = CREW_CAP[Math.min(level, CREW_CAP.length - 1)] || (5 + level * 3);
    return { crewCap: cap, repPerHour: 10 * level };
  }
}

export default MainTower;
