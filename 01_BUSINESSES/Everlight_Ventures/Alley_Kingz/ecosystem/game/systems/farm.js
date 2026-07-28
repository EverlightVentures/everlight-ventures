/* Alley Kingz -- THE FARM COMPOUND (window.AK_FARM)
 * AK-FARMC 2026-07-18
 *
 * WHAT THIS IS, AND WHAT IT DELIBERATELY IS NOT
 * buildmode.js already contains a complete, parity-safe Sunflower-Land-grade CROP system: 9 crops
 * with seed cost / grow time / yield / reseed / sell / Town Hall gate, real seed and crop items on
 * the profile (p.seeds{} / p.crops{}), deterministic day-weather snapshotted onto each bed at plant
 * so it cannot flip mid-cycle, an econMod world-signal multiplier, builder auto-tend, and district
 * demand. That system is GOOD and this module does NOT reimplement any of it.
 *
 * What was missing was everything AROUND the crops:
 *   1. COOKING     crops had no destination. Nothing turned a harvest into food, so there was no
 *                  food -> worker/hero loop at all.
 *   2. ANIMALS     no barn, no coop, no eggs, no milk. Crops fed nothing.
 *   3. CONTAINER   gardens are beds dropped in the open district. There was no farm COMPOUND you
 *                  walk into, with its own plots and its own storage.
 *   4. RAID MAP    no rule for what a raider can actually take or wreck on the farm.
 *
 * So this module is the ring around the crop core: it CONSUMES crops (via the existing economy) and
 * produces meals, animal goods, and a place to keep them.
 *
 * HARD RULES OBSERVED
 *   - Every profile write goes through AK_ECON.mutateProfile. Never localStorage directly: that is
 *     where a whole class of save-loss bugs came from.
 *   - Seeds, crops, meals, animal goods and materials are CLIENT SOFT currency, consistent with the
 *     existing parity gate in buildmode.js. Nothing here touches gems, which stay server-only.
 *   - Pure data layer, headless-safe, module.exports for tests. No DOM at load. Everything guarded.
 */
(function (global) {
  'use strict';

  function econ() { try { return global.AK_ECON || null; } catch (_e) { return null; } }
  function profile() { try { var E = econ(); return (E && E.loadProfile) ? E.loadProfile() : null; } catch (_e) { return null; } }
  function mutate(fn) {
    try { var E = econ(); if (E && typeof E.mutateProfile === 'function') { E.mutateProfile(fn); return true; } } catch (_e) {}
    return false;
  }
  function now() { return Date.now(); }
  function th(p) { return Math.max(1, (p && p.townHall) | 0 || 1); }

  // Crop table comes from the LIVE source of truth, never a local copy, so rebalancing crops in
  // economy.js or buildmode.js automatically rebalances cooking.
  function CROPS() {
    try { if (global.AK_ECON && AK_ECON.CROPS && Object.keys(AK_ECON.CROPS).length) return AK_ECON.CROPS; } catch (_e) {}
    try { if (global.AK_BUILDMODE && AK_BUILDMODE.CROPS) return AK_BUILDMODE.CROPS; } catch (_e) {}
    return {};
  }
  function cropCount(p, key) {
    try { if (global.AK_ECON && AK_ECON.cropCount) return AK_ECON.cropCount(p, key) | 0; } catch (_e) {}
    return Math.max(0, (p && p.crops && p.crops[key]) | 0);
  }

  /* ================================================================
   * 1. COOKING  -- crops finally have a destination
   * Recipes are tiered to mirror the crop tiers, so a fast cheap crop makes a fast cheap meal and
   * the overnight crops make the meals worth waiting for. Meals are the food -> worker/hero loop:
   * eating grants XP and morale rather than raw gold, so farming feeds PROGRESSION, not the wallet.
   * ================================================================ */
  var RECIPES = {
    scrapstew:  { name: 'Scrap Stew',      station: 'KITCHEN', needs: { catnip: 3, berry: 2 },      time: 180000,   out: 1, xp: 12,  morale: 6,  heal: 0,  th: 1 },
    cornmash:   { name: 'Corn Mash',       station: 'KITCHEN', needs: { corn: 4 },                  time: 300000,   out: 1, xp: 20,  morale: 8,  heal: 0,  th: 1 },
    blockbread: { name: 'Block Bread',     station: 'BAKERY',  needs: { corn: 3, pumpkin: 2 },      time: 600000,   out: 2, xp: 34,  morale: 12, heal: 5,  th: 2 },
    cabbagepie: { name: 'Cabbage Pie',     station: 'BAKERY',  needs: { cabbage: 3, corn: 2 },      time: 1200000,  out: 2, xp: 55,  morale: 16, heal: 10, th: 3 },
    beetbrew:   { name: 'Beet Brew',       station: 'DELI',    needs: { beetroot: 4 },              time: 1800000,  out: 2, xp: 78,  morale: 20, heal: 14, th: 3 },
    chiliplate: { name: 'Firehouse Plate', station: 'DELI',    needs: { chili: 3, cabbage: 2 },     time: 3600000,  out: 3, xp: 120, morale: 28, heal: 22, th: 4 },
    kingsteak:  { name: 'Kingz Steak',     station: 'DELI',    needs: { kingweed: 2, chili: 2 },    time: 7200000,  out: 3, xp: 190, morale: 36, heal: 30, th: 5 },
    goldplate:  { name: 'Goldroot Roast',  station: 'DELI',    needs: { goldroot: 2, kingweed: 2 }, time: 14400000, out: 4, xp: 320, morale: 50, heal: 45, th: 7 }
  };

  var STATIONS = {
    KITCHEN: { name: 'The Kitchen',  th: 1, slots: 1, sprite: 'assets/sprites/struct_garden.png' },
    BAKERY:  { name: 'The Bakery',   th: 2, slots: 2, sprite: 'assets/sprites/struct_planter.png' },
    DELI:    { name: 'The Deli',     th: 3, slots: 2, sprite: 'assets/sprites/struct_planter.png' },
    SMITH:   { name: 'The Blacksmith', th: 3, slots: 2, sprite: 'assets/sprites/struct_metal.png' }
  };

  function recipesFor(p) {
    var lv = th(p), out = [];
    for (var k in RECIPES) if (RECIPES[k].th <= lv) out.push(k);
    return out;
  }
  function canCook(p, id) {
    var r = RECIPES[id];
    if (!r) return { ok: false, reason: 'NO_RECIPE' };
    if (r.th > th(p)) return { ok: false, reason: 'TH_LOCKED', need: r.th };
    for (var c in r.needs) {
      if (cropCount(p, c) < r.needs[c]) return { ok: false, reason: 'MISSING_CROP', crop: c, need: r.needs[c], have: cropCount(p, c) };
    }
    return { ok: true };
  }
  // Start a cook. Consumes the crops NOW so the cost is committed, and stamps a ready time.
  function cook(id) {
    var res = { ok: false };
    var p0 = profile(); if (!p0) return res;
    var chk = canCook(p0, id); if (!chk.ok) { res.reason = chk.reason; res.detail = chk; return res; }
    var r = RECIPES[id];
    mutate(function (p) {
      if (!p.crops) p.crops = {};
      for (var c in r.needs) p.crops[c] = Math.max(0, (p.crops[c] | 0) - r.needs[c]);
      if (!Array.isArray(p.cooking)) p.cooking = [];
      p.cooking.push({ id: id, at: now(), done: now() + r.time, out: r.out });
    });
    res.ok = true; res.readyAt = now() + r.time;
    return res;
  }
  // Collect anything finished. Meals land as real items on p.meals{}.
  function collectMeals() {
    var got = {}, n = 0;
    mutate(function (p) {
      if (!Array.isArray(p.cooking)) { p.cooking = []; return; }
      if (!p.meals) p.meals = {};
      var keep = [], t = now();
      for (var i = 0; i < p.cooking.length; i++) {
        var job = p.cooking[i];
        if (job && job.done <= t) {
          p.meals[job.id] = (p.meals[job.id] | 0) + (job.out | 0);
          got[job.id] = (got[job.id] | 0) + (job.out | 0); n += (job.out | 0);
        } else keep.push(job);
      }
      p.cooking = keep;
    });
    return { ok: n > 0, meals: got, count: n };
  }
  /* Eat a meal. THIS is the food -> worker/hero loop: XP and morale, not gold. Morale is handed to
   * systems/needs.js when it is present (another lane owns that file, so we only CALL it, never
   * edit it) and always recorded on the profile so nothing is lost if needs.js is absent. */
  function eat(id) {
    var r = RECIPES[id], res = { ok: false };
    if (!r) { res.reason = 'NO_RECIPE'; return res; }
    var p0 = profile();
    if (!p0 || ((p0.meals && p0.meals[id]) | 0) < 1) { res.reason = 'NO_MEAL'; return res; }
    mutate(function (p) {
      if (!p.meals) p.meals = {};
      p.meals[id] = Math.max(0, (p.meals[id] | 0) - 1);
      p.xp = (p.xp | 0) + r.xp;
      if (!p.farm) p.farm = {};
      p.farm.morale = Math.max(0, Math.min(100, (p.farm.morale == null ? 50 : p.farm.morale) + r.morale));
    });
    try { if (global.AK_NEEDS && AK_NEEDS.feed) AK_NEEDS.feed(id, r); } catch (_e) {}
    res.ok = true; res.xp = r.xp; res.morale = r.morale; res.heal = r.heal;
    return res;
  }

  /* ================================================================
   * 2. ANIMALS  -- crops feed something that feeds you back
   * A pen holds animals. You feed it a crop, it runs a cycle, you collect goods. Goods are items
   * (p.goods{}) that cooking and the market can both consume, which is what closes the web:
   * crop -> animal -> good -> meal -> XP/morale -> better farming.
   * ================================================================ */
  var ANIMALS = {
    chicken: { name: 'Alley Hen',   pen: 'COOP', feed: { catnip: 2 },  cycle: 900000,  out: { egg: 3 },     th: 1, cap: 6 },
    goat:    { name: 'Lot Goat',    pen: 'BARN', feed: { corn: 3 },    cycle: 2700000, out: { milk: 4 },    th: 2, cap: 4 },
    pig:     { name: 'Yard Hog',    pen: 'BARN', feed: { pumpkin: 3 }, cycle: 5400000, out: { grease: 3 },  th: 3, cap: 4 },
    cow:     { name: 'Block Cow',   pen: 'BARN', feed: { cabbage: 4 }, cycle: 10800000, out: { milk: 9 },   th: 4, cap: 3 }
  };
  var PENS = {
    COOP: { name: 'The Coop', th: 1, slots: 2, sprite: 'assets/sprites/struct_planter.png' },
    BARN: { name: 'The Barn', th: 2, slots: 3, sprite: 'assets/sprites/struct_garden.png' }
  };

  function animalsFor(p) {
    var lv = th(p), out = [];
    for (var k in ANIMALS) if (ANIMALS[k].th <= lv) out.push(k);
    return out;
  }
  function canFeed(p, key) {
    var a = ANIMALS[key];
    if (!a) return { ok: false, reason: 'NO_ANIMAL' };
    if (a.th > th(p)) return { ok: false, reason: 'TH_LOCKED', need: a.th };
    for (var c in a.feed) if (cropCount(p, c) < a.feed[c]) return { ok: false, reason: 'MISSING_CROP', crop: c, need: a.feed[c], have: cropCount(p, c) };
    return { ok: true };
  }
  function feedAnimal(key) {
    var res = { ok: false };
    var p0 = profile(); if (!p0) return res;
    var chk = canFeed(p0, key); if (!chk.ok) { res.reason = chk.reason; res.detail = chk; return res; }
    var a = ANIMALS[key];
    mutate(function (p) {
      if (!p.crops) p.crops = {};
      for (var c in a.feed) p.crops[c] = Math.max(0, (p.crops[c] | 0) - a.feed[c]);
      if (!Array.isArray(p.pens)) p.pens = [];
      p.pens.push({ a: key, at: now(), done: now() + a.cycle });
    });
    res.ok = true; res.readyAt = now() + a.cycle;
    return res;
  }
  function collectGoods() {
    var got = {}, n = 0;
    mutate(function (p) {
      if (!Array.isArray(p.pens)) { p.pens = []; return; }
      if (!p.goods) p.goods = {};
      var keep = [], t = now();
      for (var i = 0; i < p.pens.length; i++) {
        var pen = p.pens[i], a = ANIMALS[pen && pen.a];
        if (pen && a && pen.done <= t) {
          for (var g in a.out) { p.goods[g] = (p.goods[g] | 0) + a.out[g]; got[g] = (got[g] | 0) + a.out[g]; n += a.out[g]; }
        } else keep.push(pen);
      }
      p.pens = keep;
    });
    return { ok: n > 0, goods: got, count: n };
  }

  /* ================================================================
   * 3. THE COMPOUND  -- a place you walk INTO, with its own storage
   * The farm is a sub-map, not beds scattered in the open district. It has a plot grid sized by
   * Town Hall, and its own store, so what is kept on the farm is distinct from what you carry.
   * That separation is what makes the raid rule below meaningful.
   * ================================================================ */
  var PLOT_KINDS = ['BED', 'COOP', 'BARN', 'KITCHEN', 'BAKERY', 'DELI', 'SMITH'];
  function plotsFor(p) { return 6 + Math.floor(th(p) * 1.5); }   // TH1 = 7 plots, TH10 = 21

  function farmState() {
    var p = profile() || {};
    var f = p.farm || {};
    return {
      plots: Array.isArray(f.plots) ? f.plots : [],
      capacity: plotsFor(p),
      morale: (f.morale == null ? 50 : f.morale) | 0,
      store: f.store || {},
      cooking: Array.isArray(p.cooking) ? p.cooking.length : 0,
      pens: Array.isArray(p.pens) ? p.pens.length : 0
    };
  }
  function build(kind, slot) {
    var res = { ok: false };
    var p0 = profile(); if (!p0) return res;
    if (PLOT_KINDS.indexOf(kind) < 0) { res.reason = 'BAD_KIND'; return res; }
    var def = STATIONS[kind] || PENS[kind] || { th: 1 };
    if ((def.th || 1) > th(p0)) { res.reason = 'TH_LOCKED'; res.need = def.th; return res; }
    var st = farmState();
    if (st.plots.length >= st.capacity) { res.reason = 'NO_PLOTS'; res.capacity = st.capacity; return res; }
    mutate(function (p) {
      if (!p.farm) p.farm = {};
      if (!Array.isArray(p.farm.plots)) p.farm.plots = [];
      p.farm.plots.push({ kind: kind, slot: (slot == null ? p.farm.plots.length : slot), hp: 100, at: now() });
    });
    res.ok = true;
    return res;
  }
  // Farm store is deliberately SEPARATE from the carried bag: this is the stuff a raider can reach.
  function storeAdd(item, n) {
    n = n | 0; if (!item || n <= 0) return false;
    return mutate(function (p) {
      if (!p.farm) p.farm = {};
      if (!p.farm.store) p.farm.store = {};
      p.farm.store[item] = (p.farm.store[item] | 0) + n;
    });
  }

  /* ================================================================
   * 4. RAID DESTRUCTION  -- what a raider can actually take and wreck
   * Mirrors the raid loot ceiling model already in raidparams.js: you never lose everything, and how
   * much is exposed scales with how far the attacker got. Structures take damage rather than being
   * deleted, so a raided farm is rebuilt, not restarted.
   * ================================================================ */
  function raidLoss(pct) {
    pct = Math.max(0, Math.min(1, +pct || 0));
    // stolen share of the farm STORE, capped well under total: greed has a ceiling here too
    var steal = Math.min(0.45, 0.10 + pct * 0.35);
    // structure damage: partial at low clear, heavy at a full clear, never destruction
    var dmg = Math.min(0.70, pct * 0.70);
    return { stealFrac: +steal.toFixed(3), damageFrac: +dmg.toFixed(3) };
  }
  function applyRaid(pct) {
    var r = raidLoss(pct), taken = {};
    mutate(function (p) {
      if (!p.farm) p.farm = {};
      var s = p.farm.store || {};
      for (var k in s) {
        var lose = Math.floor((s[k] | 0) * r.stealFrac);
        if (lose > 0) { s[k] = (s[k] | 0) - lose; taken[k] = lose; }
      }
      p.farm.store = s;
      var plots = Array.isArray(p.farm.plots) ? p.farm.plots : [];
      for (var i = 0; i < plots.length; i++) {
        plots[i].hp = Math.max(5, Math.round((plots[i].hp == null ? 100 : plots[i].hp) * (1 - r.damageFrac)));
      }
      p.farm.plots = plots;
      // a raided farm loses heart, which slows it until you feed the crew again
      p.farm.morale = Math.max(0, Math.min(100, (p.farm.morale == null ? 50 : p.farm.morale) - Math.round(pct * 30)));
    });
    return { ok: true, taken: taken, stealFrac: r.stealFrac, damageFrac: r.damageFrac };
  }
  // Morale is the farm's output multiplier: fed crew work faster. Consumed by production.
  function moraleMult() {
    var st = farmState();
    return +(0.75 + (st.morale / 100) * 0.5).toFixed(3);   // 0.75x at 0 morale, 1.25x at 100
  }

  var api = { id: 'farm', init: function () {}, onTick: function () {}, onDrawWorld: function () {} };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_FARM = {
    RECIPES: RECIPES, STATIONS: STATIONS, ANIMALS: ANIMALS, PENS: PENS, PLOT_KINDS: PLOT_KINDS,
    recipesFor: recipesFor, canCook: canCook, cook: cook, collectMeals: collectMeals, eat: eat,
    animalsFor: animalsFor, canFeed: canFeed, feedAnimal: feedAnimal, collectGoods: collectGoods,
    farmState: farmState, plotsFor: plotsFor, build: build, storeAdd: storeAdd,
    raidLoss: raidLoss, applyRaid: applyRaid, moraleMult: moraleMult
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_FARM;
})(typeof window !== 'undefined' ? window : this);
