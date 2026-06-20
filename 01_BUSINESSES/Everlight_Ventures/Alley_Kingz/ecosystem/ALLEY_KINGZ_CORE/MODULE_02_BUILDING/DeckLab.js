/**
 * @file DeckLab.js
 * @module MODULE_02_BUILDING
 * @summary Alley Kingz Deck Lab. Deck builder + handlers. Extends BuildingBase.
 *
 * @description
 * STUB. Intra-module import of BuildingBase is allowed (same module). No cross-module imports;
 * EventBus is dependency-injected and inherited. Opens `shop/shop.html#deck`.
 * Stat focus: `deckSlots` (unlocked deck/loadout slots) scales with level.
 */
import { BuildingBase } from './BuildingBase.js';

export class DeckLab extends BuildingBase {
  /**
   * @param {import('./BuildingBase.js').EventBus} eventBus
   * @param {Partial<import('./BuildingBase.js').BuildingConfig>} [config]
   */
  constructor(eventBus, config = {}) {
    super(eventBus, {
      type: 'deck_lab',
      label: 'The Deck Lab',
      screen: 'shop/shop.html#deck',
      maxHp: 110,
      stats: { deckSlots: 3 },
      ...config,
      id: config.id || 'deck_lab',
    });
  }

  /**
   * @protected
   * @override
   * @param {number} level Slots start at 3 and add 1 per level above 1.
   * @returns {{deckSlots:number}}
   */
  _statsForLevel(level) { return { deckSlots: 3 + Math.max(0, level - 1) }; }
}

export default DeckLab;
