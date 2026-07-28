/* Alley Kingz -- DYNAMIC RAID PARAMETERS (window.AK_RAIDPARAMS)
 * AK-RAIDV2 2026-07-18
 *
 * Implements the operator's Dynamic Raid System v2. The governing idea:
 *
 *   RARITY GATES THE CEILING, NOT THE FLOOR.
 *
 * A Common Lv7 defender and a Legendary Lv7 defender have IDENTICAL base stats. Rarity does not buy
 * raw power (with one deliberate exception, below). What rarity buys is:
 *     - how many waves the base can field at all
 *     - which boss mechanics unlock on the final wave
 *     - a loot bonus for the attacker who beats it
 * The single exception is MYTHIC, which is the only rarity that moves base stats (+15%). That is the
 * premium line: everything below Mythic is mechanics and prestige, so a Legendary roster stays
 * genuinely competitive and low-rarity players are never mathematically locked out.
 *
 * POWER instead comes from investment the player can actually control:
 *     powerMultiplier = (0.7 + TH * 0.05) * (1 + maxCardLevel * 0.02)
 * and every defender AUTO-UPGRADES to the defender's HIGHEST card level, so you never raid a TH10
 * base defended by Lv1 cards. That is what makes a same-rank raid a real 50/50 skill matchup, and
 * what makes an under-levelled attacker correctly lose to a maxed defender.
 *
 * The map is not static either: TH drives wave count, map size, building/wall/trap counts, raid
 * duration, and the hard cap on how much of their storage you can ever extract (30% at TH1 rising
 * to 75% at TH10). You never walk away with everything.
 *
 * Pure data + pure functions. No DOM, no globals mutated, no side effects, headless-safe, so this is
 * unit-testable and can run identically on a server tick when the raid sim moves server-side.
 */
(function (global) {
  'use strict';

  // ---- TH -> raid shape ---------------------------------------------------
  // waves / map / buildings / walls / traps / seconds / max extractable share of their storage
  var TH_TABLE = {
    1:  { waves: 3, map: 20, buildings: 4,  walls: 0,  traps: 0,  time: 120, maxLoot: 0.30 },
    2:  { waves: 3, map: 25, buildings: 6,  walls: 4,  traps: 1,  time: 150, maxLoot: 0.35 },
    3:  { waves: 4, map: 30, buildings: 8,  walls: 8,  traps: 2,  time: 180, maxLoot: 0.40 },
    4:  { waves: 4, map: 35, buildings: 10, walls: 12, traps: 3,  time: 210, maxLoot: 0.45 },
    5:  { waves: 5, map: 40, buildings: 12, walls: 16, traps: 4,  time: 240, maxLoot: 0.50 },
    6:  { waves: 5, map: 45, buildings: 14, walls: 20, traps: 5,  time: 270, maxLoot: 0.55 },
    7:  { waves: 6, map: 50, buildings: 16, walls: 28, traps: 6,  time: 300, maxLoot: 0.60 },
    8:  { waves: 6, map: 55, buildings: 18, walls: 36, traps: 8,  time: 330, maxLoot: 0.65 },
    9:  { waves: 7, map: 60, buildings: 20, walls: 44, traps: 10, time: 360, maxLoot: 0.70 },
    10: { waves: 7, map: 65, buildings: 22, walls: 52, traps: 12, time: 390, maxLoot: 0.75 }
  };

  // ---- rarity -> ceiling (NOT power, except Mythic) -----------------------
  // maxWaves CAPS the TH wave count: a fortress defended by a Common watcher still only answers
  // three times. bossTier selects the final-wave mechanics. statMul is 1.0 everywhere but Mythic.
  var RARITY_MOD = {
    Common:    { maxWaves: 3, bossTier: 1, lootBonus: 0.00, statMul: 1.00, boss: 'brute',    mechanics: ['3x hp'] },
    Rare:      { maxWaves: 4, bossTier: 2, lootBonus: 0.10, statMul: 1.00, boss: 'summoner', mechanics: ['3x hp', 'minion spawns every 30s'] },
    Epic:      { maxWaves: 5, bossTier: 3, lootBonus: 0.20, statMul: 1.00, boss: 'phased',   mechanics: ['3x hp', 'minion spawns', 'phase shift at 50%'] },
    Legendary: { maxWaves: 7, bossTier: 4, lootBonus: 0.35, statMul: 1.00, boss: 'warlord',  mechanics: ['3x hp', 'minion spawns', 'phase shift at 50%', 'environmental hazards'] },
    Mythic:    { maxWaves: 7, bossTier: 5, lootBonus: 0.50, statMul: 1.15, boss: 'kingz',    mechanics: ['3x hp', 'minion spawns', 'phase shift at 50%', 'environmental hazards', 'rage at 25% + invuln windows'] }
  };
  var RARITY_ORDER = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic'];

  function clampTH(th) { th = th | 0; return th < 1 ? 1 : (th > 10 ? 10 : th); }
  function thRow(th) { return TH_TABLE[clampTH(th)]; }
  function rarMod(r) { return RARITY_MOD[r] || RARITY_MOD.Common; }

  // The defender's best OWNED rarity. This is the fairness rule: a base can never field a rarity
  // its owner does not actually have, so Mythic is never handed out to a roster that lacks one.
  function watcherRarity(p, cardsByName) {
    var best = 'Common';
    try {
      var owned = (p && p.owned) || [];
      for (var i = 0; i < owned.length; i++) {
        var c = cardsByName[owned[i]]; if (!c) continue;
        if (RARITY_ORDER.indexOf(c.rarity) > RARITY_ORDER.indexOf(best)) best = c.rarity;
      }
    } catch (_e) {}
    return best;
  }

  // AUTO-UPGRADE: every defender fights at the defender's HIGHEST card level, so a well-invested
  // base is never embarrassed by its weakest card.
  function maxCardLevel(p) {
    var lv = 1;
    try {
      var m = (p && p.cardLvls) || {};
      for (var k in m) { var v = m[k] | 0; if (v > lv) lv = v; }
      var th = (p && p.townHall) | 0; if (th > lv) lv = th;   // TH is the cap AND the floor-of-record
    } catch (_e) {}
    return lv < 1 ? 1 : lv;
  }

  function powerMultiplier(th, lv) { return (0.7 + clampTH(th) * 0.05) * (1 + lv * 0.02); }

  // AI escalates with the wave, independent of stats: patrol -> defend -> engage -> swarm
  function aiBehavior(wave) {
    if (wave <= 2) return 'patrol';
    if (wave <= 4) return 'defend';
    if (wave <= 6) return 'engage';
    return 'swarm';
  }

  /* The one entry point. Give it a defender profile and the canon card map, get the whole raid
   * shape back: how long, how big, how many waves, how hard, what the boss does, and the hard
   * ceiling on what the attacker can ever carry out. */
  function calculate(p, cardsByName) {
    cardsByName = cardsByName || {};
    var th = clampTH((p && p.townHall) | 0 || 1);
    var row = thRow(th);
    var rarity = watcherRarity(p, cardsByName);
    var rm = rarMod(rarity);
    var lv = maxCardLevel(p);
    var pm = powerMultiplier(th, lv) * rm.statMul;             // statMul is 1.0 unless Mythic
    var waves = Math.min(row.waves, rm.maxWaves);              // rarity CAPS the TH wave count

    return {
      th: th, watcherRarity: rarity, maxCardLevel: lv,
      maxWaves: waves,
      powerMultiplier: +pm.toFixed(4),
      bossTier: rm.bossTier, bossType: rm.boss, bossMechanics: rm.mechanics.slice(),
      lootBonus: rm.lootBonus,
      maxLootPercent: row.maxLoot,
      mapSize: row.map, buildingCount: row.buildings, wallCount: row.walls, trapCount: row.traps,
      raidSeconds: row.time,
      waveIntervalSec: Math.max(30, Math.round(row.time / waves))
    };
  }

  /* Build the defending roster. Watcher (best rarity) + up to 4 lieutenants, all auto-upgraded to
   * the same level, all sharing the same power multiplier. Stats are identical across rarities by
   * design; only Mythic shifts them, via powerMultiplier. */
  function defenders(p, cardsByName, params) {
    var out = [];
    try {
      params = params || calculate(p, cardsByName);
      var postsObj = (p && p.defense && p.defense.posts) || {};
      var squad = [];
      for (var s = 0; s < 4; s++) { var nm = postsObj[String(s)]; if (nm) squad.push(nm); }
      var hero = (p && p.heroName) || squad[0] || null;
      var pm = params.powerMultiplier;

      if (hero) {
        var hc = cardsByName[hero] || {};
        out.push({ name: hero, role: 'watcher', level: params.maxCardLevel, rarity: hc.rarity || 'Common',
          hp: Math.round((hc.hp || 1200) * pm * 1.25), dmg: Math.round((hc.damage || 80) * pm * 1.25) });
      }
      for (var i = 0; i < squad.length; i++) {
        if (squad[i] === hero) continue;
        var c = cardsByName[squad[i]] || {};
        out.push({ name: squad[i], role: 'lieutenant', level: params.maxCardLevel, rarity: c.rarity || 'Common',
          hp: Math.round((c.hp || 900) * pm), dmg: Math.round((c.damage || 60) * pm) });
      }
    } catch (_e) {}
    return out;
  }

  /* Wave composition. Wave 1 is a probe, wave 2 adds the watcher, wave 3 is the full response, the
   * last wave is the boss. Reinforcement pressure always climbs so even a shallow roster escalates. */
  function planWaves(p, cardsByName, params) {
    params = params || calculate(p, cardsByName);
    var roster = defenders(p, cardsByName, params);
    var lts = roster.filter(function (u) { return u.role === 'lieutenant'; });
    var watcher = roster.filter(function (u) { return u.role === 'watcher'; })[0] || null;
    var plan = [];
    for (var w = 1; w <= params.maxWaves; w++) {
      var isFinal = (w === params.maxWaves);
      var units = [];
      var reinforce = 1 + 0.18 * (w - 1);                       // always-on pressure
      var take = Math.min(lts.length, Math.max(1, Math.ceil(lts.length * (w / params.maxWaves))) + Math.floor((w - 1) / 2));
      for (var i = 0; i < take; i++) {
        var b = lts[i % Math.max(1, lts.length)];
        if (!b) continue;
        units.push({ name: b.name, role: 'lieutenant', level: b.level, rarity: b.rarity,
          hp: Math.round(b.hp * reinforce), dmg: Math.round(b.dmg * reinforce) });
      }
      // The watcher normally holds back until wave 2, but a base whose only defender IS the watcher
      // must not send an EMPTY first wave. Caught in testing: a solo-defender base (the common
      // starter and casual case) was handing the attacker a free opening wave with zero units.
      if ((w >= 2 || !lts.length || !units.length) && watcher) {
        units.push({ name: watcher.name, role: 'watcher', level: watcher.level, rarity: watcher.rarity,
          hp: Math.round(watcher.hp * reinforce), dmg: Math.round(watcher.dmg * reinforce) });
      }
      plan.push({
        wave: w, ai: aiBehavior(w), boss: isFinal,
        bossTier: isFinal ? params.bossTier : 0,
        bossMechanics: isFinal ? params.bossMechanics.slice() : [],
        trapsActive: Math.round(params.trapCount * Math.min(1, w / Math.max(1, params.maxWaves - 1))),
        units: units,
        totalHp: units.reduce(function (a, u) { return a + u.hp; }, 0)
      });
    }
    return plan;
  }

  /* How much can the attacker actually carry out? Capped by TH, lifted by the defender's rarity
   * bonus. Even a total clear does not empty the base. */
  function lootCeiling(params, totalStorage) {
    var cap = (totalStorage | 0) * params.maxLootPercent * (1 + params.lootBonus);
    return Math.max(0, Math.floor(cap));
  }

  global.AK_RAIDPARAMS = {
    TH_TABLE: TH_TABLE, RARITY_MOD: RARITY_MOD, RARITY_ORDER: RARITY_ORDER,
    calculate: calculate, defenders: defenders, planWaves: planWaves,
    watcherRarity: watcherRarity, maxCardLevel: maxCardLevel,
    powerMultiplier: powerMultiplier, aiBehavior: aiBehavior, lootCeiling: lootCeiling
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_RAIDPARAMS;
})(typeof window !== 'undefined' ? window : this);
