/**
 * @file SpellShop.js
 * @module MODULE_02_BUILDING
 * @summary Alley Kingz Spell Shop. Sells spells/items. Extends BuildingBase.
 *
 * @description
 * STUB. Intra-module import of BuildingBase is allowed (same module, MODULE_02). No cross-module
 * imports; the EventBus is dependency-injected and inherited from the base. Opens `shop/shop.html`.
 * Stat focus: `restock` (restock quality / catalog tier) scales with level.
 */
import { BuildingBase } from './BuildingBase.js';

export class SpellShop extends BuildingBase {
  /**
   * @param {import('./BuildingBase.js').EventBus} eventBus
   * @param {Partial<import('./BuildingBase.js').BuildingConfig>} [config]
   */
  constructor(eventBus, config = {}) {
    super(eventBus, {
      type: 'spell_shop',
      label: 'The Spell Shop',
      screen: 'shop/shop.html',
      maxHp: 120,
      stats: { restock: 1 },
      ...config,
      id: config.id || 'spell_shop',
    });
  }

  /**
   * @protected
   * @override
   * @param {number} level
   * @returns {{restock:number}}
   */
  _statsForLevel(level) { return { restock: level }; }
}

export default SpellShop;
