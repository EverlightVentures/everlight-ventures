/* game/systems/buildmode.js -- AK_SYSTEMS module: BUILD MODE + DEFENSE + BUILDERS + GARDENS.
 *
 * Implements AK_RESOURCE_ECONOMY_DESIGN.md secs 5 (Builders=Dogs) + 6 (Gardens) for
 * the buildmode lane. ALL ADDITIVE -- no engine.js / economy.js edits; every JS hook
 * + DOM id preserved (#ak-bm-btn / #ak-bm-bar / #ak-bm-mats / #ak-bm-demo / #ak-bm-row,
 * AK_BUILDMODE.open/close/toggle/isActive/STRUCT/mountButton).
 *
 * WHAT IT DOES (real, not a stub):
 *   - BUILD MODE toggled by a floating HUD button (#ak-bm-btn) / AK_BUILDMODE.toggle().
 *     Bottom palette (#ak-bm-bar) lists placeable STRUCTURES. Tap a tile, then tap the
 *     GROUND (right ~55%; left stays the joystick) to drop it on a snapped grid cell.
 *   - BUILDERS = DOGS (design sec 5): X builder slots per Town Hall level
 *     (builderCap(TH) = clamp(1+floor(TH/2),1,6)). The player ASSIGNS an owned dog card
 *     to a builder slot (the "CREW" panel / the Foreman). The assigned card's LEVEL x the
 *     Town Hall LEVEL set that builder's SPEED:
 *        builderSpeed(cardLvl,TH) = (1+0.08*(cardLvl-1)) * (1+0.05*(TH-1))
 *     A faction-matched dog adds a small (+10%, capped) bonus to harvested produce/loot.
 *   - Placement is NO LONGER instant. place() enqueues a TIMED builder job: it consumes a
 *     free builder slot, the structure renders "under construction" (non-solid) for
 *        build_time = base_time(family) / builderSpeed   (sec 5.6: wall/barricade 30s, deco/bed 10s)
 *     and onTick reconciles finished jobs back to live + frees the slot. Gems can SKIP the
 *     timer (parity-safe: skip-only, server-gated; the <=2min band is a free auto-finish).
 *   - GARDENS = SUNFLOWER LAND GROW CYCLE (design sec 6 + AK-FARM): the flat +gold/+produce
 *     trickle is GONE. Seeds + crops are now REAL soft items (AK_ECON p.seeds{} / p.crops{}).
 *     A bed is plant -> grow-timer -> harvest. PLANT consumes a SEED item (auto-buys one with
 *     gold if you hold none); HARVEST grants the CROP item + BONUS SEEDS (crop.reseed -- the
 *     "reproduce" lever, so a bed self-sustains). Crops SELL for gold or USE -> produce (the
 *     BARN panel). A simple deterministic-by-day WEATHER (sun/rain/drought) scales grow time
 *     + yield, SNAPSHOTTED onto the bed (b.wx) at plant so it never flips mid-cycle. Crop
 *     state rides the build entry (b.crop / b.plantedAt / b.wx -- no new array); growthStage
 *     art + a ripe pulse. A builder on task 'tend' auto-plants + harvests its zone at speed.
 *     (A Plants-vs-Zombies garden-defense mini-game is stubbed -- AK_BUILDMODE.gardenDefense,
 *     sec 6b -- to wire later via arcade.js; reads this module's bed/crop state, no engine edit.)
 *   - DEFENSE: solid completed structures feed window.AK_COLLISION (we wrap obstaclesFor)
 *     so a placed wall blocks the player. Under-construction structures are NON-solid.
 *   - AK-ROTATE: any rect structure can be turned 90deg before you drop it (R key or the
 *     ROTATE tap-target on the build bar -- mobile-first). entry.rot is 0..3 (falsy-safe,
 *     always read as (entry.rot||0)); odd values SWAP width<->height for collision, draw +
 *     grid-snap alike so the footprint + hitbox never disagree. Real-life logic: the shape
 *     turns around its own center, so left stays left -- only the long axis swaps direction.
 *     rot rides the build entry (p.builds[i].rot) so a rotated piece redraws correctly after
 *     save/reload.
 *   - AK-ISOEDIT 2026-07-18: EDIT MODE -- the Clash-style BASE EDITOR (sec 11). The in-world
 *     path (walk your dog, tap inside 360px, top-down host camera) is UNCHANGED. EDIT opens a
 *     DETACHED camera on its own canvas (#ak-bm-edit-cv): pan, pinch zoom, 90deg view snaps,
 *     drawn ISOMETRIC (2:1 dimetric, Canvas2D -- never a WebGL context, see sec 11 for why).
 *     A palette drags out a ghost with green/red validity on the same GRID, and -- the thing
 *     in-world placement CANNOT do -- you DRAG AN EXISTING STRUCTURE to reposition it.
 *     REFLECTION PAIR: the editor has NO mirror array. place() / moveBuild() / demolishAt()
 *     all write the SAME p.builds[] through the SAME ctx.econ.mutateProfile, so a wall you
 *     move in the editor stands moved in the hub world (onDrawWorld -> drawStruct) and in raid
 *     defense (buildRects -> AK_COLLISION.obstaclesFor) with no sync step.
 *   - DISTRICT DEMAND (CAPTIVATION P8): each of OUR 9 districts runs a Fence ORDER BOARD --
 *     it DEMANDS its signature crop + a primary build mat; FORTIFY + PRODUCTION draw down its
 *     stock and REOPEN demand; you FILL orders for a premium that banks into the floating
 *     Fence. Demand is PERISHABLE (resets each LOCAL-PT day) + scales with AK_ECON.econMod
 *     (dear Fence => hungrier district). Crop yields now read the same econMod (snapshotted on
 *     the bed at plant, b.em). Exposes window.AK_BUILDMODE.districtDemand(zid) + p.districtDemand.
 *
 * CRYPTO/PARITY GATE (HARD LAW): produce/materials/gold/seeds/crops are 100% client soft
 * currency; NO $BCARDD/ALK anywhere. Gems skip TIMERS + buy cosmetics only -- never raise a
 * builder cap, a level, a tool tier, a crop yield, or loot quality. grant('gems') stays a
 * no-op (server-only); buySeed/buyTool refuse payWith:'gems'.
 *
 * ZERO-STATE BYTE-IDENTICAL (HARD): nothing is written to the profile until the player
 * ACTS. p.crew / p.produce / b.uc / b.crop / b.wx are falsy-default + lazily created on first
 * assign / plant / build; p.seeds{} / p.crops{} are falsy-default {} (backfilled in
 * economy.js ensureShape alongside p.scrap/p.copies). init() + onTick write nothing.
 *
 * Headless-safe: no DOM / localStorage at load; all storage via AK_ECON. Bails on pages
 * without the registry (battler / node harness). 60fps: progress rings are alpha/transform
 * only, no per-frame shadowBlur; the ripe pulse honours prefers-reduced-motion.
 */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;                 // hub-only module

  /* ---------------------------------------------------------------------- *
   * STRUCTURE CATALOG -- materials from worldverbs (wood/stone/metal).
   * ---------------------------------------------------------------------- */
  var STRUCT = {
    WALL:      { name: 'Wood Wall',    glyph: 'WOOD',  sprite: 'assets/sprites/struct_wall.png',      solid: true,  shape: 'rect',   cw: 84, ch: 48, dw: 76, dh: 42, hp: 200,  cost: { wood: 10 },           family: 'wall' },
    STONE:     { name: 'Stone Wall',   glyph: 'STONE', sprite: 'assets/sprites/struct_stone.png',     solid: true,  shape: 'rect',   cw: 84, ch: 48, dw: 76, dh: 42, hp: 500,  cost: { stone: 12 },          family: 'wall' },
    METAL:     { name: 'Metal Wall',   glyph: 'METAL', sprite: 'assets/sprites/struct_metal.png',     solid: true,  shape: 'rect',   cw: 84, ch: 48, dw: 76, dh: 42, hp: 1200, cost: { metal: 10, stone: 4 }, family: 'wall' },
    BARRICADE: { name: 'Barricade',    glyph: 'BAR',   sprite: 'assets/sprites/struct_barricade.png', solid: true,  shape: 'rect',   cw: 80, ch: 44, dw: 72, dh: 38, hp: 120,  cost: { wood: 18 },           family: 'barricade' },
    PATH:      { name: 'Path Tile',    glyph: 'PATH',  sprite: 'assets/sprites/struct_path.png',     solid: false, shape: 'rect',   cw: 64, ch: 64, dw: 60, dh: 60, hp: 0,    cost: { stone: 3 },           family: 'deco' },
    GARDEN:    { name: 'Sunflower Bed', glyph: 'BED',  sprite: 'assets/sprites/struct_garden.png',    solid: false, shape: 'rect',  cw: 60, ch: 50, dw: 58, dh: 46, hp: 0,    cost: { wood: 12 },           family: 'garden' },
    PLANTER:   { name: 'Neon Planter', glyph: 'POT',   sprite: 'assets/sprites/struct_planter.png',   solid: true,  shape: 'circle', cr: 24,                dw: 42, dh: 42, hp: 0, cost: { stone: 6 },           family: 'deco' }
  };
  /* AK-NOFORT 2026-07-20 (operator: "remove all builder elements like metal walls, steel barricades,
   * they don't belong on this map anymore -- that's what the 2D sunflower land aka Silo building is
   * for"). The DISTRICT is a city street you walk down, not a base you fortify. Fortification moved
   * inside THE SILO (the garden / Sunflower Land world), so the wall and barricade families leave
   * the district palette. The catalog entries are NOT deleted -- the Silo build mode still needs
   * them, and deleting them would orphan every structure a player has already placed. They are
   * simply not offered here. */
  var DISTRICT_BANNED = { wall: 1, barricade: 1 };
  var ORDER = ['PATH', 'GARDEN', 'PLANTER'];
  var ORDER_ALL = ['WALL', 'STONE', 'METAL', 'BARRICADE', 'PATH', 'GARDEN', 'PLANTER'];
  var MATS  = ['wood', 'stone', 'metal'];

  /* ---- AK-STRUCTART: lazy image cache (headless-safe -> null -> procedural draw) ---- */
  var _imgCache = {};
  function spriteImg(path) {
    if (!path || typeof Image === 'undefined') return null;
    var im = _imgCache[path];
    if (im === undefined) { im = new Image(); im.onerror = function () { _imgCache[path] = null; }; im.src = path; _imgCache[path] = im; }
    return im;
  }
  function spriteReady(im) { return !!(im && im.complete && im.naturalWidth > 0); }

  var GRID = 64;                 // placement snap (world units)
  var BUILD_RANGE = 360;         // build radius around your dog
  var MAT_LABEL = { wood: 'WOOD', stone: 'STONE', metal: 'METAL' };
  // AK-NOEMOJI 2026-07-02: material chip art (custom icons) replaces the old android emoji glyphs.
  var MAT_ICON = { wood: 'assets/icons/chip_wood.png', stone: 'assets/icons/chip_stone.png', metal: 'assets/icons/chip_metal.png' };
  var GOLD = '#e8c55a', GOLD_DK = '#c9a84c', DIM = '#b9a76a', GREEN = '#7CFFB0';

  // one-time starter materials so build mode is demonstrable (gated by p.builds_seeded ->
  // a FRESH profile stays byte-identical until the operator OPENS build mode).
  var SEED = { wood: 80, stone: 60, metal: 40 };

  /* ====================================================================== *
   * ECONOMY LAW (AK_RESOURCE_ECONOMY_DESIGN secs 5 + 6 + 7.3). Prefer the
   * shared AK_ECON copies when the economy module exports them (single source
   * of truth); else use these design-exact local constants so this module +
   * its harness run standalone.
   * ====================================================================== */
  // sec 5.1 builder cap per Town Hall. SHARED CONTRACT = AK_ECON.builderCap(th); the
  // local fallback is the design cap TABLE [TH1..TH10] = 1,1,2,2,3,3,4,4,5,6
  // (CoC's 5 builders + a 6th "Top Dog" foreman slot at TH10). Note: the doc's
  // companion one-line formula 1+floor(TH/2) disagrees with this table at TH2/4/6/8 --
  // the TABLE is the law per the task ("builder cap = the TH table").
  function builderCap(th) {
    try { if (global.AK_ECON && AK_ECON.builderCap) return AK_ECON.builderCap(th); } catch (_) {}
    th = Math.max(1, Math.min(10, th | 0));
    return [1, 1, 2, 2, 3, 3, 4, 4, 5, 6][th - 1];
  }
  // AK-BUILDERS 2026-06-30: effective cap = TH design cap + hired (gold-bought) builder slots
  // (p.bonusBuilders, falsy-safe). Prefer AK_ECON.effectiveBuilderCap (single source) when present.
  function effCap(p) {
    try { if (global.AK_ECON && AK_ECON.effectiveBuilderCap) return AK_ECON.effectiveBuilderCap(p) | 0 || 1; } catch (_) {}
    return builderCap(thOf(p)) + (((p && p.bonusBuilders) | 0));
  }
  // sec 5.2 builderSpeed: (1 + 0.08*(cardLvl-1)) * (1 + 0.05*(TH-1)).
  function builderSpeed(cardLvl, th) {
    try { if (global.AK_ECON && AK_ECON.builderSpeed) return AK_ECON.builderSpeed(cardLvl, th); } catch (_) {}
    cardLvl = Math.max(1, cardLvl | 0); th = Math.max(1, th | 0);
    return (1 + 0.08 * (cardLvl - 1)) * (1 + 0.05 * (th - 1));
  }
  // sec 7.3 gem-skip ladder. SHARED CONTRACT unit = SECONDS remaining
  // (AK_ECON.gemSkipCost(seconds)); the local fallback mirrors the design table.
  function gemSkipCost(secRemaining) {
    try { if (global.AK_ECON && AK_ECON.gemSkipCost) return AK_ECON.gemSkipCost(secRemaining); } catch (_) {}
    var s = secRemaining;
    if (s <= 120) return 0;        // <= 2 min: free auto-finish band
    if (s <= 600) return 2;        // <= 10 min
    if (s <= 1800) return 5;       // <= 30 min
    if (s <= 3600) return 9;       // <= 1 h
    if (s <= 14400) return 24;     // <= 4 h
    if (s <= 43200) return 60;     // <= 12 h
    return 100;                    // <= 24 h (cap)
  }
  // sec 6.1 + AK-FARM CROP table (Sunflower model). ONE source of truth = AK_ECON.CROPS;
  // this LOCAL mirror is the headless-harness fallback (buildmode loaded without economy.js).
  // Fields: name, glyph, seed (gold/seed), grow (ms), yield (crops/harvest), reseed (bonus
  // seeds/harvest -- the reproduce lever), sell (gold/crop), th (Town Hall gate). MUST mirror
  // economy.js CROPS exactly so the standalone harness reads the same numbers.
  var LOCAL_CROPS = {
    catnip:   { name: 'Catnip',           glyph: '', seed: 5,   grow: 120000,   yield: 3,   reseed: 2, sell: 5,  th: 1 },
    berry:    { name: 'Block Berries',    glyph: '', seed: 10,  grow: 300000,   yield: 5,   reseed: 2, sell: 7,  th: 1 },
    corn:     { name: 'Street Corn',      glyph: '', seed: 20,  grow: 720000,   yield: 9,   reseed: 2, sell: 8,  th: 1 },
    pumpkin:  { name: 'Pumpkin',          glyph: '', seed: 60,  grow: 1800000,  yield: 20,  reseed: 1, sell: 9,  th: 2 },
    cabbage:  { name: 'Concrete Cabbage', glyph: '', seed: 100, grow: 3600000,  yield: 30,  reseed: 1, sell: 12, th: 2 },
    beetroot: { name: 'Beetroot',         glyph: '', seed: 140, grow: 7200000,  yield: 46,  reseed: 1, sell: 16, th: 3 },
    chili:    { name: 'Firehouse Chili',  glyph: '', seed: 220, grow: 12600000, yield: 70, reseed: 1, sell: 22, th: 4 },
    kingweed: { name: 'Kingweed',         glyph: '', seed: 320, grow: 21600000, yield: 110, reseed: 1, sell: 30, th: 5 },
    goldroot: { name: 'Goldroot',         glyph: '', seed: 700, grow: 57600000, yield: 230, reseed: 1, sell: 40, th: 7 }
  };
  var CROPS = (global.AK_ECON && AK_ECON.CROPS && typeof AK_ECON.CROPS === 'object' && Object.keys(AK_ECON.CROPS).length) ? AK_ECON.CROPS : LOCAL_CROPS;
  // crop keys ordered by grow-time ascending (cheapest/fastest first for auto-tend pick)
  var CROP_ORDER = Object.keys(CROPS).sort(function (a, b) { return (CROPS[a].grow || 0) - (CROPS[b].grow || 0); });

  /* ---- AK-FARM weather: deterministic-by-day grow/yield modifier. Prefer the
   * shared AK_ECON copy (single source); else mirror the design wheel so this
   * module + its harness run standalone. A crop SNAPSHOTS the weather key at
   * plant time (b.wx) so its grow/yield never flip mid-cycle (parity-safe). ---- */
  var LOCAL_WEATHER = {
    sun:     { label: 'Clear Skies', glyph: 'SUN',  grow: 1.00, yield: 1.00 },
    rain:    { label: 'Rain',        glyph: 'RAIN', grow: 0.80, yield: 1.15 },
    drought: { label: 'Drought',     glyph: 'DRY',  grow: 1.30, yield: 0.85 }
  };
  function curWeather() {
    try { if (global.AK_ECON && AK_ECON.gardenWeather) return AK_ECON.gardenWeather(); } catch (_) {}
    var wheel = ['sun', 'rain', 'sun', 'drought', 'sun', 'rain'];
    var day = Math.floor(Date.now() / 86400000), h = ((day * 1103515245 + 12345) >>> 0) % wheel.length;
    var key = wheel[h], w = LOCAL_WEATHER[key] || LOCAL_WEATHER.sun;
    return { key: key, label: w.label, glyph: w.glyph, growMult: w.grow, yieldMult: w.yield, day: day };
  }
  function weatherMods(key) {
    try { if (global.AK_ECON && AK_ECON.weatherMods) return AK_ECON.weatherMods(key); } catch (_) {}
    var w = LOCAL_WEATHER[key] || LOCAL_WEATHER.sun; return { growMult: w.grow, yieldMult: w.yield };
  }
  function seedCountOf(p, key) { try { if (global.AK_ECON && AK_ECON.seedCount) return AK_ECON.seedCount(p, key); } catch (_) {} return Math.max(0, (p && p.seeds && p.seeds[key]) | 0); }
  function cropCountOf(p, key) { try { if (global.AK_ECON && AK_ECON.cropCount) return AK_ECON.cropCount(p, key); } catch (_) {} return Math.max(0, (p && p.crops && p.crops[key]) | 0); }

  // AK-ECONMOD tie-in (CAPTIVATION P8): the live WORLD-SIGNAL crop multiplier folds the
  // active chapter/season + weather + day/night into ONE number (AK_ECON.econMod). A bed
  // SNAPSHOTS this at plant (b.em) so its yield never flips mid-cycle (parity-safe, exactly
  // like the b.wx weather snapshot). The same read drives the DEMAND price floor below
  // (.fence). Standalone fallback (no economy.js) = weather-only yieldMult so the headless
  // harness reads the same model. Deterministic by the world clock -> identical per player.
  function econModNow() {
    try { if (global.AK_ECON && AK_ECON.econMod) return AK_ECON.econMod(); } catch (_) {}
    var w = curWeather(); return { crop: w.yieldMult || 1, fence: 1, chapter: '', season: '', weather: w.key, phase: 'day', phaseFrac: 0 };
  }
  function matSell(mat) { try { if (global.AK_ECON && AK_ECON.sellMaterial) return AK_ECON.sellMaterial(mat); } catch (_) {} var L = { wood: 2, stone: 3, metal: 5 }; return L[mat] || 0; }
  function ptDay() { try { if (global.AK_ECON && AK_ECON.ptDayIndex) return AK_ECON.ptDayIndex(); } catch (_) {} return Math.floor((Date.now() - 28800000) / 86400000); }   // LOCAL-PT day bucket (UTC-8 fixed offset, parity-safe)

  // sec 5.6 base build time (pre-speed): walls/barricades 30s, deco/beds 10s.
  function baseBuildMs(def) { var f = def && def.family; return (f === 'wall' || f === 'barricade') ? 30000 : 10000; }

  // sec 3.2 / 5.4 faction affinity: a faction-matched dog gives a small (+10%, capped)
  // bonus to harvested produce/loot. Cosmetic-driven, earned (never gems), parity-safe.
  // Maps the design's "Unbound -> produce/wood" affinity onto the canon roster.
  var FACTION_AFFINITY = { tend: 'leashbreak_tactix', gather: null };
  var FACTION_BONUS = 0.10;
  function cardFaction(name) { try { var c = BM.ctx && BM.ctx.cards && BM.ctx.cards()[name]; return (c && (c.factionId || c.faction)) || ''; } catch (_) { return ''; } }
  function factionBonus(name, task) { if (!name) return 0; var want = FACTION_AFFINITY[task]; if (!want) return 0; return cardFaction(name) === want ? FACTION_BONUS : 0; }

  /* ====================================================================== *
   * DISTRICT SIGNATURE CROPS -- each of OUR 9 districts favors ONE crop.
   * ====================================================================== *
   * Additive to the existing farm. A bed grown in its HOME district yields a
   * SIGNATURE BONUS (+SIGNATURE_BONUS) on top of weather + faction. Crop names
   * stay the established street/dog-flavored CROPS keys (no new names) -- this
   * just maps each canon district to the crop it grows best. The bed carries its
   * zone (b.zone, set at place) so harvest knows where it grew. Parity HARD LAW:
   * the bonus is on a SOFT crop item only, never gems, never $BCARDD/ALK. */
  var DISTRICT_CROP = {
    HOME_TURF:     'catnip',   // The Lot      -- home orchard rows, the starter green
    DOWNTOWN:      'berry',    // Downtown     -- Block Berries off the block
    THE_STRIP:     'corn',     // The Strip    -- Street Corn off the vendor strip
    THE_YARDS:     'cabbage',  // The Yards    -- Concrete Cabbage in the lots
    THE_OVERLOOK:  'pumpkin',  // The Overlook -- the harvest vista
    THE_DOCKS:     'beetroot', // The Docks    -- roots shipped through the docks
    FACTORY_ROW:   'chili',    // Factory Row  -- Firehouse Chili by the forge
    NEON_HEIGHTS:  'kingweed', // Neon Heights -- Kingweed, the crowned green up high
    THE_UNDERCITY: 'goldroot'  // The Undercity-- Goldroot pulled from the deep
  };
  var DISTRICT_NAME = {
    HOME_TURF: 'The Lot', DOWNTOWN: 'Downtown', THE_STRIP: 'The Strip',
    NEON_HEIGHTS: 'Neon Heights', THE_OVERLOOK: 'The Overlook', THE_YARDS: 'The Yards',
    FACTORY_ROW: 'Factory Row', THE_DOCKS: 'The Docks', THE_UNDERCITY: 'The Undercity'
  };
  var SIGNATURE_BONUS = 0.25;   // +25% harvest yield for a district's signature crop, grown at home
  function districtName(zid) { return DISTRICT_NAME[zid] || (zid ? String(zid).replace(/_/g, ' ') : 'The Block'); }
  function signatureCropFor(zid) { return (zid && DISTRICT_CROP[zid]) || null; }
  function isSignatureCrop(zid, cropKey) { return !!cropKey && signatureCropFor(zid) === cropKey; }
  function signatureBonus(zid, cropKey) { return isSignatureCrop(zid, cropKey) ? SIGNATURE_BONUS : 0; }

  /* ====================================================================== *
   * FORTIFY -- spend wood + stone to raise a district's raid DEFENSE level.
   * ====================================================================== *
   * p.fortify = { "<zoneId>": level }  (falsy-default {}, lazily created on the
   * FIRST fortify -- zero-state byte-identical until the operator acts). Level
   * 0..FORTIFY_MAX. The cost is wood + stone ONLY (the design's defensive sink,
   * canon sec 6) and RISES with the level you are buying. The RAID layer reads
   * p.fortify[zoneId] -> fortifyDefense(level): a higher fortify makes the
   * district harder to take (tougher walls / core), so a raid does less Town-Hall
   * damage and your deck stays max level. Parity HARD LAW: materials are 100% soft
   * currency; gems NEVER raise a fortify level (gems skip build TIMERS only). */
  var FORTIFY_MAX = 10;
  function fortifyLevel(p, zid) { return Math.max(0, Math.min(FORTIFY_MAX, (p && p.fortify && p.fortify[zid]) | 0)); }
  function fortifyCost(nextLevel) {
    var n = Math.max(1, Math.min(FORTIFY_MAX, nextLevel | 0));
    return { wood: 20 + 30 * n, stone: 16 + 24 * n };       // rises each level -- the wood/stone sink
  }
  // raid-defense multiplier the raid layer reads: each level adds +15% (cap +150%).
  function fortifyDefense(level) { return 1 + 0.15 * Math.max(0, Math.min(FORTIFY_MAX, level | 0)); }
  function affordCost(p, cost) { for (var k in cost) if (cost.hasOwnProperty(k) && (((p && p[k]) | 0)) < cost[k]) return false; return true; }
  function costLabel(cost) { var s = []; for (var k in cost) if (cost.hasOwnProperty(k)) s.push(cost[k] + ' ' + (MAT_LABEL[k] || k.toUpperCase())); return s.join(' + '); }
  // Raise the active district's fortify by one level (spends wood + stone). Atomic.
  function fortifyDistrict(zid) {
    zid = zid || (BM.ctx && BM.ctx.zoneId);
    if (!zid) return { ok: false, error: 'NO_ZONE' };
    var p0 = freshProfile(), cur = fortifyLevel(p0, zid);
    if (cur >= FORTIFY_MAX) { if (BM.ctx) BM.ctx.showBanner('MAX FORTIFIED -- ' + districtName(zid).toUpperCase(), 1.2); return { ok: false, error: 'MAXED', level: cur }; }
    var cost = fortifyCost(cur + 1);
    if (!affordCost(p0, cost)) { if (BM.ctx) BM.ctx.showBanner('NEED ' + costLabel(cost), 1.3); return { ok: false, error: 'CANT_AFFORD', cost: cost }; }
    BM.ctx.econ.mutateProfile(function (p) {
      for (var k in cost) if (cost.hasOwnProperty(k)) p[k] = Math.max(0, ((p[k] | 0)) - cost[k]);
      if (!p.fortify || typeof p.fortify !== 'object') p.fortify = {};
      p.fortify[zid] = Math.min(FORTIFY_MAX, (p.fortify[zid] | 0) + 1);
      // P8: a raised wall DRAWS DOWN the district's mat stock -> records CONSUMED, which
      // REOPENS the district's Fence demand for that mat (the self-feeding loop). Same atomic
      // mutation; lazily creates p.districtDemand (zero-state byte-identical until you act).
      if (!p.districtDemand || typeof p.districtDemand !== 'object') p.districtDemand = {};
      var dr = p.districtDemand[zid] || (p.districtDemand[zid] = {});
      if (!dr.consumed || typeof dr.consumed !== 'object') dr.consumed = {};
      for (var ck in cost) if (cost.hasOwnProperty(ck) && MAT_LABEL[ck]) dr.consumed[ck] = Math.max(0, Math.min(DEMAND_CONSUMED_CAP, (dr.consumed[ck] | 0) + cost[ck]));
    });
    bump();
    if (BM.ctx) BM.ctx.showBanner(districtName(zid).toUpperCase() + ' FORTIFIED -- DEF LV ' + (cur + 1), 1.4);
    refreshBar(); refreshFortifyPanel(); refreshBarnPanel();
    return { ok: true, zone: zid, level: cur + 1, defense: fortifyDefense(cur + 1) };
  }

  /* ====================================================================== *
   * DISTRICT CROP DEMAND (CAPTIVATION P8) -- the self-feeding economy loop.
   * ====================================================================== *
   * Each of OUR 9 districts runs a standing Fence ORDER BOARD: it DEMANDS its
   * SIGNATURE CROP + a primary BUILD MAT (wood/stone/metal, tiered by district).
   * Demand is PERISHABLE -- it resets every LOCAL-PT day (a daily reason to farm
   * + trade) -- and SCALES with econMod.fence: when the chapter/weather/night make
   * the Fence dear, the district is hungrier AND pays more. FORTIFY (and production,
   * via recordConsumption) DRAW DOWN the district's stock -> the mats eaten are
   * banked as CONSUMED, which reopens demand. You FILL an order by delivering crops
   * /mats you farmed/mined -> the Fence pays a PREMIUM over the plain sell price (the
   * buy-order), and the sale is banked into the floating-Fence ring so the price
   * responds to your supply (the EVE/RuneScape "second game").
   *
   * p.districtDemand = { "<zoneId>": { day:<ptDay>, filled:{crop,wood,stone,metal},
   *   consumed:{wood,stone,metal} } } -- falsy-default {}, lazily created on the FIRST
   * fill / fortify-consume (zero-state byte-identical; NOT in ensureShape). The base
   * demand + prices are PURE reads of econMod + the canon tables; only the filled
   * /consumed ledger writes. Parity HARD LAW: orders pay GOLD (soft currency) ONLY --
   * never gems, never $BCARDD/ALK, never power; cosmetic-gem rule untouched. */
  var DISTRICT_MAT = {
    HOME_TURF:    'wood',  DOWNTOWN:     'wood',  THE_STRIP:    'wood',    // the low blocks run on lumber
    THE_YARDS:    'stone', THE_OVERLOOK: 'stone', THE_DOCKS:    'stone',   // mid blocks lay stone
    FACTORY_ROW:  'metal', NEON_HEIGHTS: 'metal', THE_UNDERCITY:'metal'    // the high/industrial blocks forge metal
  };
  var DEMAND_BASE_CROP    = 12;     // crops a district wants per PT day (pre-econMod)
  var DEMAND_BASE_MAT     = 30;     // mats a district wants per PT day (pre-econMod)
  var DEMAND_PREMIUM      = 1.35;   // a buy-order pays +35% over the plain Fence sell value
  var DEMAND_CONSUMED_CAP = 400;    // cap the fortify/production draw-down backlog (anti-runaway)

  // read-only ledger snapshot (filled resets each PT day; consumed persists as backlog)
  function demandRec(p, zid) {
    var rec = p && p.districtDemand && p.districtDemand[zid], day = ptDay();
    return { day: day, filled: (rec && rec.day === day && rec.filled) ? rec.filled : {}, consumed: (rec && rec.consumed) ? rec.consumed : {} };
  }
  // PURE getter -- the live order board for a district. No profile write.
  function districtDemand(zid) {
    zid = zid || (BM.ctx && BM.ctx.zoneId);
    if (!zid) return null;
    var p = freshProfile(), em = econModNow(), fenceM = (em && isFinite(em.fence)) ? em.fence : 1, rec = demandRec(p, zid);
    var cropKey = signatureCropFor(zid), crop = cropKey && CROPS[cropKey], matKey = DISTRICT_MAT[zid] || 'wood';
    var wantCrop = Math.max(0, Math.round(DEMAND_BASE_CROP * fenceM));
    var consumedMat = Math.max(0, Math.min(DEMAND_CONSUMED_CAP, (rec.consumed[matKey] | 0)));
    var wantMat = Math.max(0, Math.round(DEMAND_BASE_MAT * fenceM) + consumedMat);
    var openCrop = Math.max(0, wantCrop - ((rec.filled.crop) | 0));
    var openMat  = Math.max(0, wantMat - ((rec.filled[matKey]) | 0));
    var cropUnit = crop ? Math.max(1, Math.round((crop.sell || 0) * DEMAND_PREMIUM * fenceM)) : 0;
    var matUnit  = Math.max(1, Math.round(matSell(matKey) * DEMAND_PREMIUM * fenceM));
    var haveCrop = cropKey ? cropCountOf(p, cropKey) : 0, haveMat = Math.max(0, (p && p[matKey]) | 0);
  // AK-NOFORT 2026-07-20: single source of truth for 'may this be placed/rendered on a district
  // street'. world3d.planPlayerStructs and the instancing lane both consult THIS, so the rule
  // cannot drift between the palette and the renderer.
  function isDistrictBanned(type) {
    var d = STRUCT && STRUCT[type];
    return !!(d && DISTRICT_BANNED[d.family]);
  }

    return {
      isDistrictBanned: isDistrictBanned, DISTRICT_BANNED: DISTRICT_BANNED, ORDER_ALL: ORDER_ALL,
      zone: zid, name: districtName(zid), day: rec.day,
      fenceMult: fenceM, chapter: (em && em.chapter) || '', weather: (em && em.weather) || '',
      crop: cropKey ? { key: cropKey, name: crop.name, glyph: crop.glyph || '', want: wantCrop, open: openCrop, unit: cropUnit, have: haveCrop, fillable: Math.min(haveCrop, openCrop) } : null,
      mat: { key: matKey, label: MAT_LABEL[matKey] || matKey.toUpperCase(), glyph: '', icon: MAT_ICON[matKey] || '', want: wantMat, open: openMat, unit: matUnit, have: haveMat, fillable: Math.min(haveMat, openMat) },
      openOrders: (openCrop > 0 ? 1 : 0) + (openMat > 0 ? 1 : 0)
    };
  }
  // FILL an order: deliver crops ('crop') or a build mat ('wood'|'stone'|'metal') into the
  // district's open demand for PREMIUM gold. Atomic; lazily creates p.districtDemand. Banks
  // the sale into the floating-Fence ring. n==null fills the max you can. Parity: gold only.
  function fillDemand(zid, kind, n) {
    zid = zid || (BM.ctx && BM.ctx.zoneId);
    if (!zid) return { ok: false, error: 'NO_ZONE' };
    var d = districtDemand(zid); if (!d) return { ok: false, error: 'NO_DEMAND' };
    var isCrop = (kind === 'crop'), slot = isCrop ? d.crop : ((d.mat && d.mat.key === kind) ? d.mat : null);
    if (!slot) return { ok: false, error: 'NOT_DEMANDED' };
    var maxFill = slot.fillable | 0, qty = (n == null) ? maxFill : Math.min(maxFill, Math.max(0, n | 0));
    if (qty <= 0) { if (BM.ctx) BM.ctx.showBanner(slot.have <= 0 ? 'NOTHING TO DELIVER' : 'ORDER FILLED -- BACK TOMORROW', 1.2); return { ok: false, error: slot.have <= 0 ? 'NO_STOCK' : 'NO_OPEN', open: slot.open, have: slot.have }; }
    var unit = slot.unit | 0, gold = unit * qty, day = ptDay(), resKey = isCrop ? d.crop.key : kind;
    BM.ctx.econ.mutateProfile(function (p) {
      if (isCrop) { if (!p.crops || typeof p.crops !== 'object') p.crops = {}; p.crops[resKey] = Math.max(0, (p.crops[resKey] | 0) - qty); }
      else { p[kind] = Math.max(0, (p[kind] | 0) - qty); }
      p.coins = Math.max(0, (p.coins | 0) + gold);
      if (!p.districtDemand || typeof p.districtDemand !== 'object') p.districtDemand = {};
      var rec = p.districtDemand[zid] || (p.districtDemand[zid] = {});
      if (rec.day !== day) { rec.day = day; rec.filled = {}; }                       // perishable: filled resets each PT day
      if (!rec.filled || typeof rec.filled !== 'object') rec.filled = {};
      var fk = isCrop ? 'crop' : kind;
      rec.filled[fk] = (rec.filled[fk] | 0) + qty;
      if (!isCrop && rec.consumed && (rec.consumed[kind] | 0) > 0) rec.consumed[kind] = Math.max(0, (rec.consumed[kind] | 0) - qty);   // delivering pays down the fortify backlog
    });
    try { if (global.AK_ECON && AK_ECON.recordFenceFill) AK_ECON.recordFenceFill(resKey, unit); } catch (_e) {}   // supply signal -> the floating Fence price responds
    bump();
    if (BM.ctx) BM.ctx.showBanner(districtName(zid).toUpperCase() + ' ORDER -- +' + gold + 'g (' + qty + ' ' + (isCrop ? d.crop.name : (MAT_LABEL[kind] || kind)) + ')', 1.5);
    refreshBar(); refreshBarnPanel();
    return { ok: true, zone: zid, kind: isCrop ? 'crop' : kind, qty: qty, gold: gold, unit: unit };
  }
  // PUBLIC hook (production.js + any consumer): record a district drawing down a build mat
  // so its Fence demand REOPENS. Atomic; capped. Returns {ok,...}. Parity-safe (no currency).
  function recordConsumption(zid, mat, n) {
    zid = zid || (BM.ctx && BM.ctx.zoneId); n = n | 0;
    if (!zid || n <= 0 || !MAT_LABEL[mat]) return { ok: false, error: 'BAD_ARGS' };
    if (!BM.ctx || !BM.ctx.econ) return { ok: false, error: 'NO_CTX' };
    BM.ctx.econ.mutateProfile(function (p) {
      if (!p.districtDemand || typeof p.districtDemand !== 'object') p.districtDemand = {};
      var rec = p.districtDemand[zid] || (p.districtDemand[zid] = {});
      if (!rec.consumed || typeof rec.consumed !== 'object') rec.consumed = {};
      rec.consumed[mat] = Math.max(0, Math.min(DEMAND_CONSUMED_CAP, (rec.consumed[mat] | 0) + n));
    });
    bump(); refreshBarnPanel();
    return { ok: true, zone: zid, mat: mat, consumed: n };
  }

  function thOf(p) { try { if (global.AK_ECON && AK_ECON.townHallLevel) return AK_ECON.townHallLevel(p); } catch (_) {} return Math.max(1, Math.min(10, (p && p.townHall | 0) || 1)); }
  function cardLevelOf(p, name) { try { if (global.AK_ECON && AK_ECON.cardLevel) return AK_ECON.cardLevel(p, name); } catch (_) {} var v = p && p.cardLvls && p.cardLvls[name]; return Math.max(1, Math.min(10, Math.floor(v || 1))); }

  function fmtTime(ms) { var s = Math.max(0, Math.round(ms / 1000)); if (s < 60) return s + 's'; var m = Math.floor(s / 60), ss = s % 60; if (m < 60) return m + ':' + (ss < 10 ? '0' : '') + ss; var h = Math.floor(m / 60); return h + 'h ' + (m % 60) + 'm'; }

  /* ---------------------------------------------------------------------- *
   * MODULE STATE (no DOM here)
   * ---------------------------------------------------------------------- */
  var BM = {
    ctx: null, active: false, sel: null, demolish: false, tend: false,
    rot: 0,                      // AK-ROTATE: pending placement rotation 0..3 (0/90/180/270deg), falsy-safe
    bar: null, btn: null, listening: false, reduce: false,
    ghost: null,                 // {x,y} snapped world pos under the finger
    ver: 0,                      // bumps whenever p.builds/p.crew changes (this module owns it)
    _p: null, _pv: -1,           // ver-cached profile read
    obsCache: {},                // zoneId -> {ver, base, full}
    clock: 0,                    // anim clock (ripe pulse / build ring)
    tendAcc: {},                 // module-mem per-slot auto-tend accumulator (NOT profile)
    crewPanel: null, cropPanel: null, cardPicker: null, barnPanel: null, fortPanel: null, cropTarget: -1, pickSlot: -1,
    edit: null                   // AK-ISOEDIT 2026-07-18: iso base-editor state, lazily built by editState() -- null until the operator opens it
  };
  var coll = null, origObsFor = null;
  var TEND_PERIOD = 3.0;          // seconds of (speed-scaled) work per auto-tend action
  var TEND_GOLD_FLOOR = 50;       // auto-tend never spends gold below this on seed

  function freshProfile() { try { return BM.ctx && BM.ctx.econ ? BM.ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function prof() { if (BM._pv !== BM.ver || !BM._p) { BM._p = freshProfile(); BM._pv = BM.ver; } return BM._p; }
  function bump() { BM.ver++; BM.obsCache = {}; }

  /* ====================================================================== *
   * (1) DEFENSE -- feed COMPLETED solid structures into AK_COLLISION
   * ====================================================================== */
  function isUnderConstruction(b) { return !!(b && b.uc && Date.now() < (b.uc.t0 + b.uc.dur)); }
  function buildRects(zid) {
    var arr = [], p = prof(), builds = (p && p.builds) || [];
    for (var i = 0; i < builds.length; i++) {
      var b = builds[i]; if (b.zone !== zid) continue;
      if (isUnderConstruction(b)) continue;                       // scaffolding is non-solid
      var d = STRUCT[b.type]; if (!d || !d.solid) continue;
      if (d.shape === 'circle') arr.push({ type: 'circle', x: b.x, y: b.y, r: d.cr || 24, kind: 'build' });
      else { var rot = b.rot || 0, w = fw(d, rot), h = fh(d, rot); arr.push({ type: 'rect', x: b.x - w / 2, y: b.y - h / 2, w: w, h: h, kind: 'build' }); }
    }
    return arr;
  }
  function installCollisionWrap() {
    coll = global.AK_COLLISION;
    if (!coll || coll.__bmWrapped || typeof coll.obstaclesFor !== 'function') return;
    var orig = coll.obstaclesFor; origObsFor = orig;
    coll.obstaclesFor = function (zone) {
      var base = orig(zone) || [];
      var zid = zone && zone.id; if (!zid) return base;
      var c = BM.obsCache[zid];
      if (c && c.ver === BM.ver && c.base === base) return c.full;
      var ext = buildRects(zid);
      var full = ext.length ? base.concat(ext) : base;
      BM.obsCache[zid] = { ver: BM.ver, base: base, full: full };
      return full;
    };
    coll.__bmWrapped = true;
  }

  /* ====================================================================== *
   * (2) PLACEMENT VALIDATION
   * ====================================================================== */
  function snap(v) { return Math.round(v / GRID) * GRID; }
  // AK-ROTATE: rot is 0..3 (0/90/180/270deg), ALWAYS read falsy-safe via (entry.rot||0).
  // Odd rotations swap width<->height for collision (fw/fh -- cw/ch) and draw (effDW/effDH
  // -- dw/dh) alike, so a structure's hitbox and its drawn shape never disagree. Rotating
  // swaps the footprint around the SAME center point -- real-life logic: left stays left,
  // only the long axis turns.
  function rotSwap(rot) { return ((rot | 0) & 1) === 1; }
  function fw(def, rot) { return def.shape === 'circle' ? (def.cr || 24) * 2 : (rotSwap(rot) ? (def.ch || 66) : (def.cw || 66)); }
  function fh(def, rot) { return def.shape === 'circle' ? (def.cr || 24) * 2 : (rotSwap(rot) ? (def.cw || 66) : (def.ch || 66)); }
  function effDW(def, rot) { return def.shape === 'circle' ? (def.dw || 42) : (rotSwap(rot) ? (def.dh || fh(def, rot)) : (def.dw || fw(def, rot))); }
  function effDH(def, rot) { return def.shape === 'circle' ? (def.dh || 42) : (rotSwap(rot) ? (def.dw || fw(def, rot)) : (def.dh || fh(def, rot))); }
  function overlap(ax, ay, aw, ah, bx, by, bw, bh) { return Math.abs(ax - bx) * 2 < (aw + bw) && Math.abs(ay - by) * 2 < (ah + bh); }
  // AK-ISOEDIT 2026-07-18: optional `exclude` index -- a structure being DRAGGED must not
  // collide with the copy of itself it is leaving behind. Falsy-safe: existing callers pass
  // nothing, undefined never matches an index, so the in-world path is unchanged.
  function buildAt(zid, x, y, exclude) {
    var p = prof(), builds = (p && p.builds) || [];
    for (var i = builds.length - 1; i >= 0; i--) {
      if (i === exclude) continue;
      var b = builds[i]; if (b.zone !== zid) continue; var d = STRUCT[b.type]; if (!d) continue;
      var rot = b.rot || 0, w = effDW(d, rot) + 6, h = effDH(d, rot) + 6;
      if (Math.abs(x - b.x) <= w / 2 && Math.abs(y - b.y) <= h / 2) return i;
    }
    return -1;
  }
  // AK-ISOEDIT 2026-07-18: opts is OPTIONAL + falsy-safe (existing callers pass nothing).
  //   opts.ignoreRange -- the EDITOR camera is detached, so the 360px walk radius does not
  //                       apply there (you are editing the base, not reaching from the dog).
  //                       The in-world path never passes it and keeps the radius rule.
  //   opts.exclude     -- build index to skip in the overlap test (the piece being dragged).
  function placeReason(ctx, def, x, y, rot, opts) {
    var zone = ctx.activeZone, ZW = ctx.world.WORLD_W, ZH = ctx.world.WORLD_H;
    var w = fw(def, rot), h = fh(def, rot), m = 40;
    if (x < m || x > ZW - m || y < m || y > ZH - m) return 'OUT OF BOUNDS';
    if (!(opts && opts.ignoreRange) && ctx.world.distToMe(x, y) > BUILD_RANGE) return 'TOO FAR -- WALK CLOSER';
    var bs = (zone && zone.buildings) || [];
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i]; var by = b.y + (b.h || 0) / 4;
      if (overlap(x, y, w + 22, h + 44, b.x, by, (b.w || 0) + 22, (b.h || 0) + 60)) return 'BLOCKED BY A BUILDING';
    }
    if (buildAt(zone && zone.id, x, y, (opts && opts.exclude != null) ? opts.exclude : -1) >= 0) return 'SPOT TAKEN';
    try {
      if (coll && coll.blocks) {
        var starter = origObsFor ? origObsFor(zone) : (coll.obstaclesFor ? coll.obstaclesFor(zone) : []);
        if (coll.blocks(x, y, Math.max(w, h) / 2, starter)) return 'DEBRIS IN THE WAY';
      }
    } catch (_e) {}
    try {
      if (coll && coll.validPlacement && !coll.validPlacement(zone, { id: def.name, x: x, y: y, w: w, h: h }, 0)) return 'NO ROOM HERE';
    } catch (_e2) {}
    return null;
  }
  function costStr(def) { var s = []; for (var k in def.cost) if (def.cost.hasOwnProperty(k)) s.push(def.cost[k] + ' ' + (MAT_LABEL[k] || k.toUpperCase())); return s.join(' + '); }
  function canAfford(p, def) { for (var k in def.cost) if (def.cost.hasOwnProperty(k)) { if ((((p && p[k]) | 0)) < def.cost[k]) return false; } return true; }

  /* ====================================================================== *
   * (3) BUILDERS = DOGS  (design sec 5)  -- slot state + assignment
   * ====================================================================== *
   * p.crew = { "<slot>": { card, task, target, started, dur } }  (falsy-default)
   *   task: 'build' (idle / takes one-shot build jobs) | 'gather' | 'tend' | 'train' | 'guard'
   *   gather/tend/train/guard = STATIONED (continuous, occupies the slot).
   *   'guard' STATIONS the dog as a defender of c.target (a district id) -- the
   *   defense layer (systems/guard.js) reads these crew slots as patrol defenders
   *   alongside the placed p.guards deck cards. Occupies a builder slot (a guarding
   *   dog cannot also build), parity-safe (no gold/gem cost -- it is a posting).
   *   started/dur = set while running a one-shot build job (mirrors the build's b.uc).
   * A build job rides the placed structure: b.uc = { slot, t0, dur }. */
  function isStationed(c) { return !!(c && (c.task === 'gather' || c.task === 'tend' || c.task === 'train' || c.task === 'guard')); }
  // slot indices currently running an incomplete build job -> { slot:true }
  function activeJobSlots(p) {
    var out = {}, builds = (p && p.builds) || [], now = Date.now();
    for (var i = 0; i < builds.length; i++) { var b = builds[i]; if (b.uc && now < b.uc.t0 + b.uc.dur) out[b.uc.slot] = true; }
    return out;
  }
  function builderState(p) {
    var cap = effCap(p), crew = (p && p.crew) || {}, jobs = activeJobSlots(p);
    var busyBuild = 0, stationed = 0;
    for (var s = 0; s < cap; s++) { var c = crew[s]; if (isStationed(c)) stationed++; else if (jobs[s]) busyBuild++; }
    return { cap: cap, free: Math.max(0, cap - busyBuild - stationed), busyBuild: busyBuild, stationed: stationed, jobs: jobs };
  }
  function pickFreeSlot(p) {
    var st = builderState(p), crew = (p && p.crew) || {};
    for (var s = 0; s < st.cap; s++) { var c = crew[s]; if (isStationed(c)) continue; if (st.jobs[s]) continue; return s; }
    return -1;
  }
  // Read-only snapshot of all builder slots (for the Foreman / crew.js UI).
  function buildersList(p) {
    p = p || freshProfile(); var cap = effCap(p), crew = (p && p.crew) || {}, jobs = activeJobSlots(p), th = thOf(p), out = [];
    for (var s = 0; s < cap; s++) {
      var c = crew[s] || {}, card = c.card || null, lvl = card ? cardLevelOf(p, card) : 1;
      var building = !!jobs[s], remain = 0;
      if (building) { var b = jobForSlot(p, s); if (b) remain = Math.max(0, b.b.uc.t0 + b.b.uc.dur - Date.now()); }
      out.push({ slot: s, card: card, lvl: lvl, task: isStationed(c) ? c.task : 'build', target: c.target || null,
        speed: builderSpeed(lvl, th), building: building, stationed: isStationed(c), remainMs: remain });
    }
    return out;
  }
  // Assign (or re-assign) an owned card + task to a builder slot. Refuses while the slot
  // is mid-build (cancel via demolish first). Atomic; lazily creates p.crew on first use.
  function assignBuilder(slot, cardName, task, target) {
    slot = slot | 0; if (slot < 0) return { ok: false, error: 'BAD_SLOT' };
    var p0 = freshProfile(); var cap = effCap(p0);
    if (slot >= cap) return { ok: false, error: 'OVER_CAP', cap: cap };
    if (cardName && p0 && Array.isArray(p0.owned) && p0.owned.indexOf(cardName) < 0) return { ok: false, error: 'CARD_NOT_OWNED' };
    if (activeJobSlots(p0)[slot]) return { ok: false, error: 'BUSY_BUILDING' };
    task = (task === 'gather' || task === 'tend' || task === 'train' || task === 'guard') ? task : 'build';
    BM.ctx.econ.mutateProfile(function (p) {
      if (!p.crew || typeof p.crew !== 'object') p.crew = {};
      var c = p.crew[slot] || (p.crew[slot] = {});
      c.card = cardName || null; c.task = task;
      if (target != null) c.target = target;
      if (task === 'gather' || task === 'tend' || task === 'guard') c.started = Date.now(); else { c.started = 0; c.dur = 0; }
    });
    BM.tendAcc[slot] = 0; bump(); refreshCrewPanel();
    return { ok: true, slot: slot, card: cardName || null, task: task };
  }
  function unassignBuilder(slot) {
    slot = slot | 0; var p0 = freshProfile();
    if (activeJobSlots(p0)[slot]) return { ok: false, error: 'BUSY_BUILDING' };
    BM.ctx.econ.mutateProfile(function (p) { if (p.crew && p.crew[slot]) delete p.crew[slot]; });
    bump(); refreshCrewPanel(); return { ok: true, slot: slot };
  }

  /* ====================================================================== *
   * (4) PLACE / DEMOLISH  -- placement is now a TIMED builder job
   * ====================================================================== */
  // AK-ISOEDIT 2026-07-18: opts is OPTIONAL (falsy-safe). The EDITOR calls this SAME function
  // with {rot, ignoreRange} so there is exactly ONE write path into p.builds -- the editor
  // cannot drift from the in-world placement rules, the costs, or the builder-job timing.
  function place(ctx, key, x, y, opts) {
    var def = STRUCT[key]; if (!def) return false;
    var rot = (opts && opts.rot != null) ? ((opts.rot | 0) & 3) : (BM.rot | 0);
    var sx = snap(x), sy = snap(y);
    var reason = placeReason(ctx, def, sx, sy, rot, opts);
    if (reason) { ctx.showBanner(reason, 1.1); return false; }
    var p0 = freshProfile();
    if (!canAfford(p0, def)) { ctx.showBanner('NEED ' + costStr(def), 1.3); return false; }
    var slot = pickFreeSlot(p0);
    if (slot < 0) { ctx.showBanner('ALL BUILDERS BUSY', 1.3); return false; }
    var cardName = (p0.crew && p0.crew[slot] && p0.crew[slot].card) || null;
    var spd = builderSpeed(cardName ? cardLevelOf(p0, cardName) : 1, thOf(p0));
    var dur = Math.max(1000, Math.round(baseBuildMs(def) / spd));
    var now = Date.now();
    ctx.econ.mutateProfile(function (p) {
      for (var k in def.cost) if (def.cost.hasOwnProperty(k)) p[k] = Math.max(0, ((p[k] | 0)) - def.cost[k]);
      if (!Array.isArray(p.builds)) p.builds = [];
      var entry = { type: key, x: sx, y: sy, hp: def.hp | 0, maxHp: def.hp | 0, zone: ctx.zoneId, t: now, uc: { slot: slot, t0: now, dur: dur } };
      if (rot) entry.rot = rot;                       // AK-ROTATE: falsy-safe -- only written when non-zero, persists across save/reload
      p.builds.push(entry);
      if (!p.crew || typeof p.crew !== 'object') p.crew = {};
      var c = p.crew[slot] || (p.crew[slot] = {}); c.started = now; c.dur = dur;
    });
    bump();
    ctx.showBanner(def.name.toUpperCase() + ' STARTED -- ' + fmtTime(dur), 1.2);
    refreshBar();
    return true;
  }
  function demolishAt(ctx, x, y) {
    var idx = buildAt(ctx.zoneId, x, y);
    if (idx < 0) { ctx.showBanner('NOTHING HERE', 0.9); return false; }
    ctx.econ.mutateProfile(function (p) {
      var b = p.builds && p.builds[idx]; if (!b) return;
      var def = STRUCT[b.type];
      if (def) for (var k in def.cost) if (def.cost.hasOwnProperty(k)) p[k] = Math.max(0, ((p[k] | 0)) + Math.floor(def.cost[k] / 2)); // 50% refund
      if (b.uc && p.crew && p.crew[b.uc.slot]) { p.crew[b.uc.slot].started = 0; p.crew[b.uc.slot].dur = 0; }  // cancel job -> free builder
      p.builds.splice(idx, 1);
    });
    bump();
    ctx.showBanner('SCRAPPED (50% back)', 1.0);
    refreshBar();
    return true;
  }
  // AK-ISOEDIT 2026-07-18: REPOSITION an already-placed structure (the one thing in-world
  // placement cannot do). Same validation as place() minus the walk radius, same
  // ctx.econ.mutateProfile write, same p.builds[] entry -- we only move x/y/rot on the
  // EXISTING record, so hp/uc/crop/plantedAt/zone all ride along untouched. Free (no
  // materials): CoC-style rearranging is a layout decision, not a purchase.
  function moveBuild(ctx, idx, x, y, rot) {
    if (!ctx || !ctx.econ) return { ok: false, error: 'NO_CTX' };
    var p0 = freshProfile(), b = p0 && p0.builds && p0.builds[idx | 0];
    if (!b) return { ok: false, error: 'NO_BUILD' };
    if (b.zone !== ctx.zoneId) return { ok: false, error: 'OTHER_ZONE' };
    var def = STRUCT[b.type]; if (!def) return { ok: false, error: 'BAD_TYPE' };
    var nrot = (rot == null ? (b.rot || 0) : (rot | 0)) & 3;
    var sx = snap(x), sy = snap(y);
    if (sx === b.x && sy === b.y && nrot === (b.rot || 0)) return { ok: true, moved: false, x: sx, y: sy, rot: nrot };
    var reason = placeReason(ctx, def, sx, sy, nrot, { ignoreRange: true, exclude: idx | 0 });
    if (reason) { ctx.showBanner(reason, 1.1); return { ok: false, error: reason, x: b.x, y: b.y }; }
    ctx.econ.mutateProfile(function (p) {
      var e = p.builds && p.builds[idx | 0]; if (!e) return;
      e.x = sx; e.y = sy;
      if (nrot) e.rot = nrot; else if (e.rot) delete e.rot;      // falsy-safe: rot 0 is never written
    });
    bump();                                                       // world draw + AK_COLLISION re-read the moved rect
    return { ok: true, moved: true, x: sx, y: sy, rot: nrot };
  }

  /* ====================================================================== *
   * (5) BUILD JOBS -- completion + gem-skip (parity-safe)
   * ====================================================================== */
  function jobForSlot(p, slot) {
    var builds = (p && p.builds) || [], now = Date.now();
    for (var i = 0; i < builds.length; i++) { var b = builds[i]; if (b.uc && b.uc.slot === slot && now < b.uc.t0 + b.uc.dur) return { idx: i, b: b }; }
    return null;
  }
  // onTick reconcile: any build whose timer elapsed -> goes live + frees its slot.
  function reconcileJobs() {
    var p = prof(); if (!p || !p.builds) return;
    var now = Date.now(), done = [];
    for (var i = 0; i < p.builds.length; i++) { var b = p.builds[i]; if (b.uc && now >= b.uc.t0 + b.uc.dur) done.push(b); }
    if (!done.length) return;
    BM.ctx.econ.mutateProfile(function (q) {
      if (!q.builds) return;
      for (var i = 0; i < q.builds.length; i++) {
        var b = q.builds[i];
        if (b.uc && now >= b.uc.t0 + b.uc.dur) { var slot = b.uc.slot; delete b.uc; if (q.crew && q.crew[slot]) { q.crew[slot].started = 0; q.crew[slot].dur = 0; } }
      }
    });
    bump();
    for (var k = 0; k < done.length; k++) { var d = STRUCT[done[k].type]; if (d) BM.ctx.showBanner(d.name.toUpperCase() + ' UP', 0.9); }
    refreshBar();
  }
  // Force a build job to complete (used by the free <=2min skip band + server gem-skip).
  function finishBuild(slot) {
    BM.ctx.econ.mutateProfile(function (p) {
      var builds = (p && p.builds) || [];
      for (var i = 0; i < builds.length; i++) { var b = builds[i]; if (b.uc && b.uc.slot === slot) { delete b.uc; if (p.crew && p.crew[slot]) { p.crew[slot].started = 0; p.crew[slot].dur = 0; } } }
    });
    bump(); refreshBar();
  }
  // Gem-skip a build job (parity HARD LAW: timer-skip ONLY, never fabricates gems).
  //   - <=2min remaining: FREE auto-finish band (sec 7.3) -> complete now.
  //   - longer: route through the server-only gem ledger (AK_ECON.gemSkip). With no
  //     server it returns SERVER_REQUIRED and does NOT complete (gems are server-only).
  function skipBuildJob(slot) {
    slot = slot | 0; var p0 = freshProfile(); var j = jobForSlot(p0, slot);
    if (!j) return { ok: false, error: 'NO_JOB' };
    var remainMs = j.b.uc.t0 + j.b.uc.dur - Date.now(), cost = gemSkipCost(remainMs / 1000);
    if (cost <= 0) { finishBuild(slot); if (BM.ctx) BM.ctx.showBanner('FINISHED', 0.8); return { ok: true, free: true }; }
    try {
      if (global.AK_ECON && typeof AK_ECON.gemSkip === 'function') {
        var r = AK_ECON.gemSkip({ kind: 'build', slot: slot, cost: cost, remainMs: remainMs });
        if (r && r.ok) { finishBuild(slot); return { ok: true, cost: cost }; }
      }
    } catch (_e) {}
    if (BM.ctx) BM.ctx.showBanner('GEMS ' + cost + ' TO SKIP -- SYNC TO SPEND', 1.3);
    return { ok: false, error: 'SERVER_REQUIRED', cost: cost };
  }

  /* ====================================================================== *
   * (6) GARDENS -- plant -> grow-timer -> harvest -> PRODUCE  (design sec 6)
   * ====================================================================== */
  // effGrow = the crop's base grow time scaled by the weather SNAPSHOTTED on the bed (b.wx).
  // Old beds (planted before AK-FARM) have no b.wx -> weatherMods() falls back to sun (1.0).
  function effGrow(b, crop) { crop = crop || (b && b.crop && CROPS[b.crop]); if (!crop) return 1; return Math.max(1000, (crop.grow || 0) * (weatherMods(b && b.wx).growMult || 1)); }
  function gardenStage(b) { var crop = b && b.crop && CROPS[b.crop]; if (!crop || !b.plantedAt) return -1; var f = (Date.now() - b.plantedAt) / effGrow(b, crop); return Math.max(0, Math.min(3, Math.floor(f * 4))); }
  function gardenRipe(b)  { var crop = b && b.crop && CROPS[b.crop]; if (!crop || !b.plantedAt) return false; return (Date.now() - b.plantedAt) >= effGrow(b, crop); }
  function gardenRemainMs(b) { var crop = b && b.crop && CROPS[b.crop]; if (!crop || !b.plantedAt) return 0; return Math.max(0, effGrow(b, crop) - (Date.now() - b.plantedAt)); }

  // PLANT a crop (Sunflower model): consumes one SEED ITEM from p.seeds[crop]; if you
  // hold none it AUTO-BUYS a single seed with gold (one-tap convenience -- the first
  // plant of a new crop costs gold, then harvest reseeds keep the bed self-sustaining).
  // Snapshots the day's WEATHER onto the bed (b.wx) so grow/yield are fixed for the cycle.
  function plantGarden(ctx, idx, cropKey, quiet) {
    var p0 = freshProfile(); var b = p0.builds && p0.builds[idx];
    if (!b || b.type !== 'GARDEN') { if (!quiet) ctx.showBanner('NOT A GARDEN', 0.9); return { ok: false, error: 'NOT_GARDEN' }; }
    if (b.crop) { if (!quiet) ctx.showBanner('ALREADY PLANTED', 0.9); return { ok: false, error: 'ALREADY_PLANTED' }; }
    var crop = CROPS[cropKey]; if (!crop) return { ok: false, error: 'BAD_CROP' };
    if (thOf(p0) < (crop.th || 1)) { if (!quiet) ctx.showBanner('NEED TOWN HALL ' + crop.th, 1.2); return { ok: false, error: 'TH_LOCKED', need: crop.th }; }
    var have = seedCountOf(p0, cropKey), buying = have < 1;
    if (buying && (p0.coins | 0) < crop.seed) { if (!quiet) ctx.showBanner('NEED A ' + crop.name.toUpperCase() + ' SEED OR ' + crop.seed + 'g', 1.3); return { ok: false, error: 'NO_SEED', need: crop.seed }; }
    var wx = curWeather(), now = Date.now(), em = econModNow();
    BM.ctx.econ.mutateProfile(function (p) {
      if (!p.seeds || typeof p.seeds !== 'object') p.seeds = {};
      if ((p.seeds[cropKey] | 0) >= 1) p.seeds[cropKey] = (p.seeds[cropKey] | 0) - 1;   // spend a held seed
      else p.coins = Math.max(0, (p.coins | 0) - crop.seed);                            // or auto-buy one
      // snapshot weather (grow time) + econMod crop multiplier (yield) so the cycle never flips
      var bb = p.builds[idx]; if (bb) { bb.crop = cropKey; bb.plantedAt = now; bb.wx = wx.key; bb.em = (em && isFinite(em.crop)) ? em.crop : 1; }
    });
    bump();
    if (!quiet) ctx.showBanner(crop.name.toUpperCase() + ' PLANTED ' + wx.glyph + ' -- ' + fmtTime(crop.grow * (wx.growMult || 1)), 1.3);
    return { ok: true, crop: cropKey, bought: buying, weather: wx.key };
  }
  // HARVEST: grants the CROP item (weather + faction scaled) to p.crops[crop] AND
  // BONUS SEEDS (crop.reseed -- the reproduce lever) back to p.seeds[crop]. No more
  // flat +produce; crops are now real items you SELL for gold or USE for produce.
  function harvestGarden(ctx, idx, builderCardName, quiet) {
    var p0 = freshProfile(); var b = p0.builds && p0.builds[idx];
    if (!b || b.type !== 'GARDEN' || !b.crop) { if (!quiet) ctx.showBanner('NOTHING TO HARVEST', 0.9); return { ok: false, error: 'EMPTY' }; }
    if (!gardenRipe(b)) { if (!quiet) ctx.showBanner('STILL GROWING -- ' + fmtTime(gardenRemainMs(b)) + ' LEFT', 0.9); return { ok: false, error: 'NOT_RIPE' }; }
    var crop = CROPS[b.crop], key = b.crop, mods = weatherMods(b.wx);
    var sig = signatureBonus(b.zone, key);     // +25% if this is the bed-district's signature crop (canon)
    // AK-ECONMOD (P8): yield uses the econMod CROP multiplier SNAPSHOTTED at plant (b.em --
    // chapter/season + weather + day/night). Old beds (no b.em) fall back to the weather-only
    // yieldMult (byte-identical to the pre-P8 harvest). Grow TIME still rides b.wx (weather).
    var yMod = (typeof b.em === 'number' && isFinite(b.em)) ? b.em : (mods.yieldMult || 1);
    var yieldN = Math.max(1, Math.round((crop.yield || 0) * yMod * (1 + factionBonus(builderCardName, 'tend') + sig)));
    var reseedN = Math.max(0, (crop.reseed || 0) | 0);
    BM.ctx.econ.mutateProfile(function (p) {
      if (!p.crops || typeof p.crops !== 'object') p.crops = {};
      p.crops[key] = (p.crops[key] | 0) + yieldN;                 // crop ITEM (falsy-default)
      if (reseedN > 0) { if (!p.seeds || typeof p.seeds !== 'object') p.seeds = {}; p.seeds[key] = (p.seeds[key] | 0) + reseedN; }   // reproduce: bonus seeds
      var bb = p.builds[idx]; if (bb) { delete bb.crop; delete bb.plantedAt; delete bb.wx; }
    });
    bump();
    if (!quiet) ctx.showBanner('+' + yieldN + ' ' + crop.name.toUpperCase() + (sig ? ' -- HOME CROP' : '') + (reseedN ? ('  +' + reseedN + ' SEED') : ''), 1.3);
    return { ok: true, key: key, crop: crop, amount: yieldN, seeds: reseedN, signature: sig > 0 };
  }
  // auto-tend pick: prefer a crop you ALREADY hold a seed for (cheapest grow first),
  // else the cheapest crop you can afford to BUY a seed for (keep a gold floor).
  function tendPick(p) {
    var th = thOf(p);
    for (var i = 0; i < CROP_ORDER.length; i++) { var k = CROP_ORDER[i], c = CROPS[k]; if ((c.th || 1) <= th && seedCountOf(p, k) >= 1) return k; }
    var coins = p.coins | 0;
    for (var j = 0; j < CROP_ORDER.length; j++) { var kk = CROP_ORDER[j], cc = CROPS[kk]; if ((cc.th || 1) <= th && coins >= (cc.seed + TEND_GOLD_FLOOR)) return kk; }
    return null;
  }
  // builder on task 'tend': one bed action per (TEND_PERIOD / builderSpeed) seconds --
  // harvest the first ripe bed, else plant (from seed stock, else buy) in an empty bed.
  function tendOneBed(ctx, slot) {
    var p = freshProfile(), builds = (p && p.builds) || [];
    for (var i = 0; i < builds.length; i++) { var b = builds[i]; if (b.type === 'GARDEN' && b.zone === ctx.zoneId && b.crop && gardenRipe(b)) { harvestGarden(ctx, i, slot.card, true); return true; } }
    for (var j = 0; j < builds.length; j++) { var e = builds[j]; if (e.type === 'GARDEN' && e.zone === ctx.zoneId && !e.crop) { var ck = tendPick(p); if (ck) { plantGarden(ctx, j, ck, true); return true; } break; } }
    return false;
  }
  function tendCycle(dt, ctx) {
    var p = prof(); if (!p || !p.crew) return;
    var th = thOf(p), cap = builderCap(th);
    for (var s = 0; s < cap; s++) {
      var c = p.crew[s]; if (!c || c.task !== 'tend') continue;
      if (c.target && c.target !== ctx.zoneId) continue;          // tends only its target zone (the one in view)
      var spd = builderSpeed(c.card ? cardLevelOf(p, c.card) : 1, th);
      BM.tendAcc[s] = (BM.tendAcc[s] || 0) + dt * spd;
      if (BM.tendAcc[s] < TEND_PERIOD) continue;
      BM.tendAcc[s] = 0;
      try { tendOneBed(ctx, c); } catch (_e) {}
    }
  }

  /* ====================================================================== *
   * (6b) GARDEN DEFENSE -- Plants-vs-Zombies mini-game STUB HOOK (NOT BUILT).
   * ====================================================================== *
   * FUTURE: a wave-defense skirmish where your ripe garden beds spawn "plant"
   * defenders that hold a lane vs raider waves -- win => bonus crops/seeds,
   * lose => a few beds get trampled (lose the in-progress crop, keep the bed).
   * It will live as an AK_SYSTEMS / systems/arcade.js mini-game (capped, soft-
   * currency only, parity-safe -- gems never buy power) and READ this module's
   * p.builds gardens + p.crops/p.seeds state. NO engine.js edit -- it layers on
   * the data/host like the rest of buildmode. Wire it later off AKStory / arcade. */
  function gardenDefenseStub() {
    return { ok: false, error: 'NOT_BUILT', note: 'PvZ-style garden-defense mini-game stub -- wire via systems/arcade.js; reads p.builds gardens + p.crops/p.seeds; capped soft-currency rewards; parity-safe.' };
  }

  /* ====================================================================== *
   * (7) INPUT -- capture-phase world taps across the WHOLE canvas. While build
   * mode is on the host's floating stick + tap-to-move yield (index.html gates
   * on AK_BUILDMODE.isOn()), so the left 45% is placement space too -- the old
   * left-zone skip made objects there unselectable ("my dpad gets in the way").
   * WASD/arrow movement still works in build mode; only the touch stick yields.
   * ====================================================================== */
  // AK-ISOEDIT 2026-07-18: the editor canvas + its chrome are MY ui too, so the in-world
  // capture handlers below never see a tap that belongs to the base editor.
  function inMyUI(t) { return !!(t && t.closest && (t.closest('#ak-bm-bar') || t.closest('#ak-bm-crew-panel') || t.closest('#ak-bm-crop-panel') || t.closest('#ak-bm-card-pick') || t.closest('#ak-bm-barn-panel') || t.closest('#ak-bm-fort-panel') || t.closest('#ak-bm-edit-top') || t.closest('#ak-bm-edit-pal') || t.closest('#ak-guard-ov') || (t.id === 'ak-bm-btn') || (t.id === 'ak-bm-edit-cv'))); }
  function toWorld(e) { var c = BM.ctx.cam; return { x: e.clientX + c.x, y: e.clientY + c.y }; }
  function gardenTapAt(ctx, x, y) {
    var idx = buildAt(ctx.zoneId, x, y);
    if (idx < 0) { ctx.showBanner('TAP A GARDEN BED', 0.9); return; }
    var p = freshProfile(), b = p.builds && p.builds[idx];
    if (!b || b.type !== 'GARDEN') { ctx.showBanner('NOT A GARDEN', 0.9); return; }
    if (isUnderConstruction(b)) { ctx.showBanner('STILL BUILDING THE BED', 0.9); return; }
    if (!b.crop) { showCropPicker(idx); return; }
    if (gardenRipe(b)) { harvestGarden(ctx, idx, null); refreshBar(); return; }
    ctx.showBanner((CROPS[b.crop] ? CROPS[b.crop].name.toUpperCase() : 'CROP') + ' -- ' + fmtTime(gardenRemainMs(b)) + ' LEFT', 1.1);
  }
  function onPointerDown(e) {
    if (!BM.active) return;
    if (editOn()) return;                    // AK-ISOEDIT: the editor owns its own canvas handlers
    if (inMyUI(e.target)) return;
    // AK-BM-DPAD 2026-07-09: no left-45% skip -- the host stick is suppressed in build mode
    var w = toWorld(e);
    if (BM.demolish) { demolishAt(BM.ctx, w.x, w.y); }
    else if (BM.tend) { gardenTapAt(BM.ctx, w.x, w.y); }
    else if (BM.sel) { BM.ghost = { x: snap(w.x), y: snap(w.y) }; place(BM.ctx, BM.sel, w.x, w.y); }
    else { BM.ctx.showBanner('PICK A STRUCTURE FIRST', 1.0); }
    e.preventDefault(); e.stopPropagation(); if (e.stopImmediatePropagation) e.stopImmediatePropagation();
  }
  function onPointerMove(e) {
    if (!BM.active || BM.demolish || BM.tend || !BM.sel) return;
    if (editOn()) return;                    // AK-ISOEDIT: no in-world ghost while the editor is up
    if (inMyUI(e.target)) return;
    var w = toWorld(e); BM.ghost = { x: snap(w.x), y: snap(w.y) };   // AK-BM-DPAD: ghost tracks the whole canvas now
  }
  // AK-ROTATE: cycle the pending placement rotation 0->1->2->3->0 (90deg per step). Bound
  // to the R key AND the on-screen ROTATE tap-target (mountButton's build bar) so it works
  // on mobile, the operator's primary device.
  function rotateSel() {
    BM.rot = ((BM.rot | 0) + 1) % 4;
    refreshBar();
    if (BM.ctx) BM.ctx.showBanner('ROTATE ' + (BM.rot * 90) + '°', 0.7);
  }
  function onKeyDown(e) {
    if (!BM.active) return;
    if (e && e.repeat) return;
    var k = e && e.key; if (!k) return;
    // AK-ISOEDIT 2026-07-18: desktop parity for the editor gestures. R turns the PIECE (same
    // verb as the in-world R), Q/E turn the VIEW 90deg, +/- zoom, Esc leaves.
    if (editOn()) {
      if (k === 'r' || k === 'R') { editTurnPiece(); return; }
      if (k === 'q' || k === 'Q') { editRotCam(-1); return; }
      if (k === 'e' || k === 'E') { editRotCam(1); return; }
      if (k === '+' || k === '=') { editZoom(1.25); return; }
      if (k === '-' || k === '_') { editZoom(1 / 1.25); return; }
      if (k === 'Escape') { exitEdit(); return; }
      return;
    }
    if (BM.demolish || BM.tend) return;
    if (k !== 'r' && k !== 'R') return;
    rotateSel();
  }
  function bindInput() {
    if (BM.listening || typeof global.addEventListener !== 'function') return;
    global.addEventListener('pointerdown', onPointerDown, true);
    global.addEventListener('pointermove', onPointerMove, true);
    global.addEventListener('keydown', onKeyDown, true);
    BM.listening = true;
  }

  /* ====================================================================== *
   * (8) DOM -- toggle button + bottom palette bar
   * ====================================================================== */
  function mountButton() {
    if (typeof document === 'undefined' || document.getElementById('ak-bm-btn')) { BM.btn = (typeof document !== 'undefined') ? document.getElementById('ak-bm-btn') : null; return; }
    var b = document.createElement('button');
    b.id = 'ak-bm-btn'; b.type = 'button'; b.title = 'Build Mode -- walls, gardens & crew';
    b.style.cssText = 'position:fixed;right:10px;top:234px;width:44px;height:44px;z-index:6;' +
      'border-radius:12px;border:1px solid rgba(201,168,76,.6);background:rgba(8,8,14,.82);' +
      'color:#e8c55a;font-size:11px;font-weight:900;line-height:1;box-shadow:0 3px 12px rgba(0,0,0,.5);' +
      'display:flex;align-items:center;justify-content:center;padding:0;cursor:pointer;-webkit-tap-highlight-color:transparent;';
    b.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); toggle(); });
    var bi = document.createElement('img'); bi.src = 'assets/icons/chip_tools.png'; bi.width = 26; bi.height = 26; bi.style.cssText = 'width:26px;height:26px;object-fit:contain;'; bi.onerror = function () { this.style.display = 'none'; b.textContent = 'BUILD'; };
    b.appendChild(bi);
    document.body.appendChild(b); BM.btn = b;
  }
  function btnCss(primary) {
    return primary
      ? 'background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;border-radius:9px;padding:7px 12px;font-weight:900;font-size:11px;letter-spacing:.04em;cursor:pointer;'
      : 'background:none;border:1px solid rgba(201,168,76,.5);color:#b9a76a;border-radius:9px;padding:7px 11px;font-weight:800;font-size:11px;cursor:pointer;';
  }
  function tileCss(selected, afford) {
    return 'flex:0 0 auto;min-width:74px;display:flex;flex-direction:column;align-items:center;justify-content:center;' +
      'padding:7px 8px;border-radius:11px;cursor:pointer;-webkit-tap-highlight-color:transparent;' +
      'background:' + (selected ? 'linear-gradient(180deg,rgba(232,197,90,.30),rgba(201,168,76,.16))' : 'rgba(20,18,26,.9)') + ';' +
      'border:1.5px solid ' + (selected ? '#e8c55a' : 'rgba(201,168,76,.35)') + ';' +
      'opacity:' + (afford ? '1' : '.45') + ';';
  }
  function ensureBar() {
    if (BM.bar || typeof document === 'undefined') return;
    var bar = document.createElement('div'); bar.id = 'ak-bm-bar';
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:11;display:none;flex-direction:column;gap:6px;' +
      'padding:8px 8px calc(8px + env(safe-area-inset-bottom));background:linear-gradient(0deg,rgba(8,8,12,.97),rgba(8,8,12,.86));' +
      'border-top:1px solid rgba(201,168,76,.45);font-family:Inter,system-ui,sans-serif;-webkit-tap-highlight-color:transparent;';
    var top = document.createElement('div');
    top.style.cssText = 'display:flex;align-items:center;gap:6px;color:#e8c55a;font-size:11px;font-weight:800;letter-spacing:.04em;';
    var title = document.createElement('span'); title.textContent = 'BUILD'; title.style.cssText = 'color:#e8c55a;';
    var mats = document.createElement('span'); mats.id = 'ak-bm-mats'; mats.style.cssText = 'flex:1;color:#E8E8E8;font-weight:700;letter-spacing:.02em;font-size:10px;';
    var crew = document.createElement('button'); crew.id = 'ak-bm-crew'; crew.type = 'button'; crew.textContent = 'CREW';
    crew.style.cssText = btnCss(false); crew.addEventListener('click', function (e) { e.stopPropagation(); toggleCrewPanel(); });
    var barn = document.createElement('button'); barn.id = 'ak-bm-barn'; barn.type = 'button'; barn.textContent = 'BARN';
    barn.style.cssText = btnCss(false); barn.addEventListener('click', function (e) { e.stopPropagation(); toggleBarnPanel(); });
    var tend = document.createElement('button'); tend.id = 'ak-bm-tend'; tend.type = 'button'; tend.textContent = 'TEND';
    tend.style.cssText = btnCss(false); tend.addEventListener('click', function (e) { e.stopPropagation(); BM.tend = !BM.tend; if (BM.tend) { BM.demolish = false; } refreshBar(); BM.ctx.showBanner(BM.tend ? 'TEND -- tap a bed to plant/harvest' : 'BUILD', 1.1); });
    var rotate = document.createElement('button'); rotate.id = 'ak-bm-rotate'; rotate.type = 'button'; rotate.textContent = 'ROTATE ⟳';
    rotate.style.cssText = btnCss(false); rotate.addEventListener('click', function (e) { e.stopPropagation(); rotateSel(); });
    var guard = document.createElement('button'); guard.id = 'ak-bm-guard'; guard.type = 'button'; guard.textContent = 'GUARD';
    guard.style.cssText = btnCss(false); guard.addEventListener('click', function (e) { e.stopPropagation(); openGuardOverlay(); });
    var fort = document.createElement('button'); fort.id = 'ak-bm-fort'; fort.type = 'button'; fort.textContent = 'FORT';
    fort.style.cssText = btnCss(false); fort.addEventListener('click', function (e) { e.stopPropagation(); toggleFortifyPanel(); });
    var demo = document.createElement('button'); demo.id = 'ak-bm-demo'; demo.type = 'button'; demo.textContent = 'SCRAP';
    demo.style.cssText = btnCss(false); demo.addEventListener('click', function (e) { e.stopPropagation(); BM.demolish = !BM.demolish; if (BM.demolish) { BM.sel = null; BM.tend = false; } refreshBar(); });
    // AK-ISOEDIT 2026-07-18: the way into the detached iso base editor.
    var edit = document.createElement('button'); edit.id = 'ak-bm-edit'; edit.type = 'button'; edit.textContent = 'EDIT';
    edit.style.cssText = btnCss(false); edit.addEventListener('click', function (e) { e.stopPropagation(); enterEdit(); });
    var done = document.createElement('button'); done.type = 'button'; done.textContent = 'DONE';
    done.style.cssText = btnCss(true); done.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    top.appendChild(title); top.appendChild(mats); top.appendChild(edit); top.appendChild(crew); top.appendChild(barn); top.appendChild(tend); top.appendChild(rotate); top.appendChild(guard); top.appendChild(fort); top.appendChild(demo); top.appendChild(done);
    var row = document.createElement('div'); row.id = 'ak-bm-row';
    row.style.cssText = 'display:flex;gap:6px;overflow-x:auto;padding-bottom:2px;';
    ORDER.forEach(function (key) {
      var def = STRUCT[key];
      var t = document.createElement('button'); t.type = 'button'; t.setAttribute('data-key', key);
      t.style.cssText = tileCss(false, true);
      var g = document.createElement('div'); g.style.cssText = 'width:22px;height:22px;line-height:1;display:flex;align-items:center;justify-content:center;';
      var gi = document.createElement('img'); gi.src = def.sprite; gi.width = 22; gi.height = 22; gi.style.cssText = 'width:22px;height:22px;object-fit:contain;'; gi.onerror = function () { this.style.display = 'none'; }; g.appendChild(gi);
      var n = document.createElement('div'); n.textContent = def.name; n.style.cssText = 'font-size:9px;font-weight:800;color:#e8c55a;margin-top:2px;white-space:nowrap;';
      var c = document.createElement('div'); c.className = 'ak-bm-cost'; c.textContent = costStr(def); c.style.cssText = 'font-size:8px;font-weight:700;color:#b9a76a;margin-top:1px;white-space:nowrap;';
      t.appendChild(g); t.appendChild(n); t.appendChild(c);
      t.addEventListener('click', function (e) { e.stopPropagation(); BM.demolish = false; BM.tend = false; BM.sel = (BM.sel === key ? null : key); refreshBar(); });
      row.appendChild(t);
    });
    bar.appendChild(top); bar.appendChild(row);
    document.body.appendChild(bar); BM.bar = bar;
  }
  // AK-NOEMOJI 2026-07-02: one materials/status chip. Custom chip icon art first (assets/icons),
  // else a clean uppercase gold label -- never an emoji. img.onerror degrades to the label, then nothing.
  function matChip(iconSrc, label, value) {
    var wrap = document.createElement('span');
    wrap.style.cssText = 'display:inline-flex;align-items:center;gap:3px;margin-right:9px;';
    if (iconSrc) {
      var im = document.createElement('img'); im.src = iconSrc; im.width = 14; im.height = 14;
      im.style.cssText = 'width:14px;height:14px;object-fit:contain;';
      im.onerror = function () { this.style.display = 'none'; if (label) { var t = document.createElement('span'); t.textContent = label; t.style.cssText = 'color:#e8c55a;font-weight:800;font-size:9px;letter-spacing:.03em;'; wrap.insertBefore(t, im.nextSibling); } };
      wrap.appendChild(im);
    } else if (label) {
      var lb = document.createElement('span'); lb.textContent = label; lb.style.cssText = 'color:#e8c55a;font-weight:800;font-size:9px;letter-spacing:.03em;'; wrap.appendChild(lb);
    }
    if (value !== '' && value != null) { var v = document.createElement('span'); v.textContent = value; v.style.cssText = 'color:#E8E8E8;font-weight:700;font-size:10px;'; wrap.appendChild(v); }
    return wrap;
  }
  function refreshBar() {
    if (!BM.bar) return;
    var p = freshProfile();
    var matsEl = document.getElementById('ak-bm-mats');
    if (matsEl) {
      var st = builderState(p), wx = curWeather(), totalCrops = 0;
      if (p && p.crops) for (var ck in p.crops) if (p.crops.hasOwnProperty(ck)) totalCrops += (p.crops[ck] | 0);
      var dd = districtDemand(BM.ctx && BM.ctx.zoneId);
      matsEl.innerHTML = '';
      MATS.forEach(function (k) { matsEl.appendChild(matChip(MAT_ICON[k], MAT_LABEL[k], (p && p[k] | 0))); });
      matsEl.appendChild(matChip(null, 'CROP', totalCrops));
      matsEl.appendChild(matChip('assets/icons/chip_produce.png', 'PROD', ((p && p.produce) | 0)));
      matsEl.appendChild(matChip(null, wx.glyph, ''));
      matsEl.appendChild(matChip('assets/icons/chip_builder.png', 'CREW', st.free + '/' + st.cap));
      matsEl.appendChild(matChip(null, 'FORT', fortifyLevel(p, BM.ctx && BM.ctx.zoneId)));
      matsEl.appendChild(matChip(null, 'ORD', (dd ? dd.openOrders : 0)));
    }
    var demo = document.getElementById('ak-bm-demo'); if (demo) demo.style.cssText = btnCss(BM.demolish);
    var tend = document.getElementById('ak-bm-tend'); if (tend) tend.style.cssText = btnCss(BM.tend);
    var rotate = document.getElementById('ak-bm-rotate');
    if (rotate) { rotate.textContent = 'ROTATE ' + ((BM.rot | 0) * 90) + '° ⟳'; rotate.style.cssText = btnCss((BM.rot | 0) !== 0); }
    var row = document.getElementById('ak-bm-row'); if (!row) return;
    var tiles = row.children;
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i], key = t.getAttribute('data-key'), def = STRUCT[key];
      t.style.cssText = tileCss(BM.sel === key && !BM.demolish && !BM.tend, canAfford(p, def));
    }
  }

  /* ---- CREW panel (lightweight Foreman in build mode; crew.js owns the full grid) ---- */
  function panelBase(id) {
    var d = document.createElement('div'); d.id = id;
    d.style.cssText = 'position:fixed;left:8px;right:8px;bottom:calc(150px + env(safe-area-inset-bottom));z-index:13;display:none;' +
      'max-height:46vh;overflow-y:auto;padding:10px;border-radius:14px;background:rgba(10,9,14,.97);' +
      'border:1px solid rgba(201,168,76,.5);font-family:Inter,system-ui,sans-serif;box-shadow:0 6px 22px rgba(0,0,0,.6);';
    document.body.appendChild(d); return d;
  }
  function ensureCrewPanel() { if (BM.crewPanel || typeof document === 'undefined') return; BM.crewPanel = panelBase('ak-bm-crew-panel'); }
  function toggleCrewPanel() { ensureCrewPanel(); if (!BM.crewPanel) return; var open = BM.crewPanel.style.display === 'none'; if (open) { hideCardPicker(); hideCropPicker(); if (BM.barnPanel) BM.barnPanel.style.display = 'none'; if (BM.fortPanel) BM.fortPanel.style.display = 'none'; renderCrewPanel(); BM.crewPanel.style.display = 'block'; } else BM.crewPanel.style.display = 'none'; }
  function refreshCrewPanel() { if (BM.crewPanel && BM.crewPanel.style.display !== 'none') renderCrewPanel(); }
  function renderCrewPanel() {
    if (!BM.crewPanel) return;
    var p = freshProfile(), list = buildersList(p);
    var html = '<div style="color:#e8c55a;font-weight:900;font-size:12px;letter-spacing:.05em;margin-bottom:6px;">THE CREW &middot; ' + list.length + ' BUILDER' + (list.length > 1 ? 'S' : '') + ' (TH' + thOf(p) + ')</div>';
    BM.crewPanel.innerHTML = html;
    list.forEach(function (s) {
      var row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:7px 4px;border-bottom:1px solid rgba(201,168,76,.18);';
      var name = document.createElement('button'); name.type = 'button';
      name.textContent = (s.card || '+ ASSIGN DOG') + (s.card ? '  Lv' + s.lvl : '');
      name.style.cssText = 'flex:1;text-align:left;background:none;border:none;color:' + (s.card ? '#E8E8E8' : '#b9a76a') + ';font-weight:800;font-size:12px;cursor:pointer;';
      name.addEventListener('click', function (e) { e.stopPropagation(); if (!s.building) showCardPicker(s.slot); });
      var spd = document.createElement('span'); spd.textContent = '×' + s.speed.toFixed(2);
      spd.style.cssText = 'color:#e8c55a;font-weight:900;font-size:11px;min-width:42px;text-align:right;';
      var taskBtn = document.createElement('button'); taskBtn.type = 'button';
      taskBtn.textContent = s.building ? ('BUILD ' + fmtTime(s.remainMs)) : s.task.toUpperCase();
      taskBtn.style.cssText = btnCss(false) + 'min-width:80px;';
      taskBtn.addEventListener('click', function (e) { e.stopPropagation(); if (s.building) { skipBuildJob(s.slot); renderCrewPanel(); return; } var order = ['build', 'gather', 'tend', 'train', 'guard'], nx = order[(order.indexOf(s.task) + 1) % order.length]; assignBuilder(s.slot, s.card, nx, BM.ctx.zoneId); });
      row.appendChild(name); row.appendChild(spd); row.appendChild(taskBtn);
      BM.crewPanel.appendChild(row);
    });
    var note = document.createElement('div'); note.style.cssText = 'color:#8a7f5e;font-size:9px;margin-top:6px;line-height:1.4;';
    note.textContent = 'A dog’s level × Town Hall sets build/gather/tend speed. More builders = unlock more Town Hall levels. Gems skip timers only.';
    BM.crewPanel.appendChild(note);
  }
  function ensureCardPicker() { if (BM.cardPicker || typeof document === 'undefined') return; BM.cardPicker = panelBase('ak-bm-card-pick'); }
  function hideCardPicker() { if (BM.cardPicker) BM.cardPicker.style.display = 'none'; }
  function showCardPicker(slot) {
    ensureCardPicker(); if (!BM.cardPicker) return; BM.pickSlot = slot;
    var p = freshProfile(), owned = (p && p.owned) || [], th = thOf(p);
    BM.cardPicker.innerHTML = '<div style="color:#e8c55a;font-weight:900;font-size:12px;margin-bottom:6px;">ASSIGN A DOG TO BUILDER #' + (slot + 1) + '</div>';
    if (!owned.length) { var e0 = document.createElement('div'); e0.style.cssText = 'color:#b9a76a;font-size:11px;'; e0.textContent = 'No cards owned yet -- win matches or open chests.'; BM.cardPicker.appendChild(e0); }
    owned.forEach(function (nm) {
      var lvl = cardLevelOf(p, nm), b = document.createElement('button'); b.type = 'button';
      b.textContent = nm + '  Lv' + lvl + '   ×' + builderSpeed(lvl, th).toFixed(2);
      b.style.cssText = 'display:block;width:100%;text-align:left;margin:3px 0;background:rgba(20,18,26,.9);border:1px solid rgba(201,168,76,.35);color:#E8E8E8;border-radius:9px;padding:9px 10px;font-weight:700;font-size:12px;cursor:pointer;';
      b.addEventListener('click', function (ev) { ev.stopPropagation(); assignBuilder(slot, nm, 'build', BM.ctx.zoneId); hideCardPicker(); renderCrewPanel(); });
      BM.cardPicker.appendChild(b);
    });
    var clr = document.createElement('button'); clr.type = 'button'; clr.textContent = 'CLEAR SLOT'; clr.style.cssText = btnCss(false) + 'margin-top:6px;';
    clr.addEventListener('click', function (ev) { ev.stopPropagation(); unassignBuilder(slot); hideCardPicker(); renderCrewPanel(); });
    BM.cardPicker.appendChild(clr);
    BM.cardPicker.style.display = 'block';
  }
  /* ---- CROP picker (plant) ---- */
  function ensureCropPanel() { if (BM.cropPanel || typeof document === 'undefined') return; BM.cropPanel = panelBase('ak-bm-crop-panel'); }
  function hideCropPicker() { if (BM.cropPanel) BM.cropPanel.style.display = 'none'; }
  function showCropPicker(idx) {
    ensureCropPanel(); if (!BM.cropPanel) return; BM.cropTarget = idx;
    var p = freshProfile(), th = thOf(p), coins = p.coins | 0, wx = curWeather(), em = econModNow();
    var zid = BM.ctx && BM.ctx.zoneId, sigKey = signatureCropFor(zid), sigCrop = sigKey && CROPS[sigKey];
    BM.cropPanel.innerHTML = '<div style="color:#e8c55a;font-weight:900;font-size:12px;margin-bottom:2px;">PLANT A CROP (Gold: ' + coins + ')</div>' +
      '<div style="color:#b9a76a;font-size:9px;margin-bottom:6px;">' + wx.glyph + ' ' + wx.label.toUpperCase() + (em.chapter ? (' &middot; ' + String(em.chapter).toUpperCase()) : '') + ' -- grow x' + (wx.growMult || 1).toFixed(2) + ', yield x' + (em.crop || 1).toFixed(2) +
      (sigCrop ? ('<br>' + districtName(zid) + ' grows ' + sigCrop.name + ' best (+' + Math.round(SIGNATURE_BONUS * 100) + '% yield)') : '') + '</div>';
    CROP_ORDER.forEach(function (key) {
      var c = CROPS[key], lock = th < (c.th || 1), have = seedCountOf(p, key), canBuy = coins >= c.seed;
      var sig = signatureBonus(zid, key);
      var b = document.createElement('button'); b.type = 'button';
      var growEff = (c.grow || 0) * (wx.growMult || 1), yEff = Math.max(1, Math.round((c.yield || 0) * (em.crop || 1) * (1 + sig)));
      var act = have >= 1 ? ('PLANT (seeds ' + have + ')') : ('BUY+PLANT ' + c.seed + 'g');
      b.textContent = (sig ? 'HOME ' : '') + c.name + '  •  ' + fmtTime(growEff) + '  •  +' + yEff + ' CROP / +' + (c.reseed || 0) + ' SEED  •  ' + (lock ? 'TH' + c.th : act);
      b.disabled = lock || (have < 1 && !canBuy);
      b.style.cssText = 'display:block;width:100%;text-align:left;margin:3px 0;border-radius:9px;padding:9px 10px;font-weight:700;font-size:11px;cursor:pointer;' +
        'background:' + (sig ? 'rgba(232,197,90,.16)' : 'rgba(20,18,26,.9)') + ';border:1px solid ' + (sig ? '#e8c55a' : 'rgba(201,168,76,.35)') + ';color:#E8E8E8;opacity:' + (b.disabled ? '.45' : '1') + ';';
      if (!b.disabled) b.addEventListener('click', function (ev) { ev.stopPropagation(); plantGarden(BM.ctx, idx, key); hideCropPicker(); refreshBar(); });
      BM.cropPanel.appendChild(b);
    });
    BM.cropPanel.style.display = 'block';
  }

  /* ---- BARN panel: realize crops (SELL -> gold / USE -> produce) + see seeds ---- */
  function ensureBarnPanel() { if (BM.barnPanel || typeof document === 'undefined') return; BM.barnPanel = panelBase('ak-bm-barn-panel'); }
  function toggleBarnPanel() { ensureBarnPanel(); if (!BM.barnPanel) return; var open = BM.barnPanel.style.display === 'none'; if (open) { hideCardPicker(); hideCropPicker(); if (BM.crewPanel) BM.crewPanel.style.display = 'none'; if (BM.fortPanel) BM.fortPanel.style.display = 'none'; renderBarnPanel(); BM.barnPanel.style.display = 'block'; } else BM.barnPanel.style.display = 'none'; }
  function refreshBarnPanel() { if (BM.barnPanel && BM.barnPanel.style.display !== 'none') renderBarnPanel(); }
  function akEcon() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function doSellCrop(key) { var e = akEcon(); if (e && e.sellCrop) { var r = e.sellCrop(key, cropCountOf(freshProfile(), key)); if (r && r.ok && BM.ctx) BM.ctx.showBanner('SOLD +' + r.gold + 'g', 1.0); } bump(); refreshBarnPanel(); refreshBar(); }
  function doUseCrop(key)  { var e = akEcon(); if (e && e.useCrop)  { var r = e.useCrop(key, cropCountOf(freshProfile(), key));  if (r && r.ok && BM.ctx) BM.ctx.showBanner('+' + r.produce + ' PRODUCE', 1.0); } bump(); refreshBarnPanel(); refreshBar(); }
  function renderBarnPanel() {
    if (!BM.barnPanel) return;
    var p = freshProfile(), wx = curWeather();
    BM.barnPanel.innerHTML = '<div style="color:#e8c55a;font-weight:900;font-size:12px;letter-spacing:.05em;margin-bottom:6px;">THE BARN &middot; ' + wx.glyph + ' ' + wx.label.toUpperCase() + '</div>';
    // P8: DISTRICT ORDERS -- the Fence buy-order board for THIS district (gives farming + mats a reason)
    var zid = BM.ctx && BM.ctx.zoneId, d = zid ? districtDemand(zid) : null;
    if (d) {
      var head = document.createElement('div');
      head.style.cssText = 'margin:-2px 0 8px;padding:7px 8px;border-radius:10px;background:rgba(232,197,90,.10);border:1px solid rgba(201,168,76,.4);';
      head.innerHTML = '<div style="color:#e8c55a;font-weight:900;font-size:11px;letter-spacing:.04em;">' + d.name.toUpperCase() + ' ORDERS' + (d.chapter ? (' &middot; ' + String(d.chapter).toUpperCase()) : '') + '</div>' +
        '<div style="color:#b9a76a;font-size:9px;margin-top:1px;">Fill the block&rsquo;s buy-orders for a premium (Fence &times;' + d.fenceMult.toFixed(2) + '). Resets daily.</div>';
      BM.barnPanel.appendChild(head);
      var mkOrder = function (slot, kind, iconSrc, label) {
        if (!slot || slot.want <= 0) return;
        var row = document.createElement('div'); row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:5px 2px;border-bottom:1px solid rgba(201,168,76,.14);';
        var lbl = document.createElement('span'); lbl.innerHTML = '<b style="color:#E8E8E8;">' + label + '</b> <span style="color:#b9a76a;">' + (slot.want - slot.open) + '/' + slot.want + '</span>';
        if (iconSrc) { var oi = document.createElement('img'); oi.src = iconSrc; oi.width = 14; oi.height = 14; oi.style.cssText = 'width:14px;height:14px;object-fit:contain;vertical-align:-2px;margin-right:3px;'; oi.onerror = function () { this.style.display = 'none'; }; lbl.insertBefore(oi, lbl.firstChild); }
        lbl.style.cssText = 'flex:1;font-size:11px;font-weight:700;color:#b9a76a;';
        var pay = document.createElement('span'); pay.textContent = slot.unit + 'g/ea'; pay.style.cssText = 'color:#7CFFB0;font-weight:800;font-size:10px;min-width:46px;text-align:right;';
        row.appendChild(lbl); row.appendChild(pay);
        var canFill = slot.fillable > 0, fill = document.createElement('button'); fill.type = 'button';
        fill.textContent = slot.open <= 0 ? 'FILLED' : (canFill ? ('FILL ' + slot.fillable + ' (+' + (slot.fillable * slot.unit) + 'g)') : ('HAVE ' + slot.have));
        fill.disabled = !canFill;
        fill.style.cssText = (canFill ? btnCss(true) : btnCss(false)) + 'font-size:10px;padding:6px 8px;opacity:' + (canFill ? '1' : '.5') + ';';
        if (canFill) fill.addEventListener('click', (function (k) { return function (e) { e.stopPropagation(); fillDemand(zid, k, null); }; })(kind));
        row.appendChild(fill); BM.barnPanel.appendChild(row);
      };
      if (d.crop) mkOrder(d.crop, 'crop', null, d.crop.name);
      mkOrder(d.mat, d.mat.key, MAT_ICON[d.mat.key], d.mat.label);
      var sub = document.createElement('div'); sub.style.cssText = 'color:#e8c55a;font-weight:900;font-size:11px;letter-spacing:.05em;margin:8px 0 4px;';
      sub.textContent = 'STOCK  (crop / seed)';
      BM.barnPanel.appendChild(sub);
    }
    var any = false;
    CROP_ORDER.forEach(function (key) {
      var c = CROPS[key], cropN = cropCountOf(p, key), seedN = seedCountOf(p, key);
      if (cropN <= 0 && seedN <= 0) return; any = true;
      var row = document.createElement('div'); row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:6px 2px;border-bottom:1px solid rgba(201,168,76,.18);';
      var lbl = document.createElement('span'); lbl.textContent = c.name; lbl.style.cssText = 'flex:1;color:#E8E8E8;font-weight:800;font-size:12px;';
      var cnt = document.createElement('span'); cnt.textContent = cropN + ' / ' + seedN; cnt.style.cssText = 'color:#b9a76a;font-size:10px;font-weight:700;min-width:48px;text-align:right;';
      row.appendChild(lbl); row.appendChild(cnt);
      if (cropN > 0) {
        var sell = document.createElement('button'); sell.type = 'button'; sell.textContent = 'SELL ' + (c.sell * cropN) + 'g';
        sell.style.cssText = btnCss(true) + 'font-size:10px;padding:6px 8px;'; sell.addEventListener('click', (function (k) { return function (e) { e.stopPropagation(); doSellCrop(k); }; })(key));
        var use = document.createElement('button'); use.type = 'button'; use.textContent = 'USE +' + (c.sell * cropN) + 'p';
        use.style.cssText = btnCss(false) + 'font-size:10px;padding:6px 8px;'; use.addEventListener('click', (function (k) { return function (e) { e.stopPropagation(); doUseCrop(k); }; })(key));
        row.appendChild(sell); row.appendChild(use);
      }
      BM.barnPanel.appendChild(row);
    });
    if (!any) { var em = document.createElement('div'); em.style.cssText = 'color:#b9a76a;font-size:11px;'; em.textContent = 'Empty barn -- plant a garden bed, let it ripen, then harvest.'; BM.barnPanel.appendChild(em); }
    var note = document.createElement('div'); note.style.cssText = 'color:#8a7f5e;font-size:9px;margin-top:6px;line-height:1.4;';
    note.textContent = 'Harvest yields crops + bonus seeds (reproduce). SELL crops for gold or USE them for produce. Weather is fixed per planting day.';
    BM.barnPanel.appendChild(note);
  }

  /* ---- FORTIFY panel: spend wood + stone to raise THIS district's raid defense ---- */
  function ensureFortifyPanel() { if (BM.fortPanel || typeof document === 'undefined') return; BM.fortPanel = panelBase('ak-bm-fort-panel'); }
  function toggleFortifyPanel() {
    ensureFortifyPanel(); if (!BM.fortPanel) return;
    var open = BM.fortPanel.style.display === 'none';
    if (open) { hideCardPicker(); hideCropPicker(); if (BM.crewPanel) BM.crewPanel.style.display = 'none'; if (BM.barnPanel) BM.barnPanel.style.display = 'none'; renderFortifyPanel(); BM.fortPanel.style.display = 'block'; }
    else BM.fortPanel.style.display = 'none';
  }
  function refreshFortifyPanel() { if (BM.fortPanel && BM.fortPanel.style.display !== 'none') renderFortifyPanel(); }
  function renderFortifyPanel() {
    if (!BM.fortPanel) return;
    var p = freshProfile(), zid = BM.ctx && BM.ctx.zoneId, cur = fortifyLevel(p, zid);
    var sigKey = signatureCropFor(zid), sigCrop = sigKey && CROPS[sigKey];
    var maxed = cur >= FORTIFY_MAX, cost = fortifyCost(cur + 1), afford = affordCost(p, cost);
    var html = '<div style="color:#e8c55a;font-weight:900;font-size:12px;letter-spacing:.05em;margin-bottom:4px;">FORTIFY &middot; ' + districtName(zid).toUpperCase() + '</div>';
    html += '<div style="color:#E8E8E8;font-size:11px;margin-bottom:3px;">Raid defense <b style="color:#e8c55a;">LV ' + cur + '/' + FORTIFY_MAX + '</b> &middot; walls hold <b style="color:#7CFFB0;">×' + fortifyDefense(cur).toFixed(2) + '</b> tougher</div>';
    var pips = ''; for (var i = 0; i < FORTIFY_MAX; i++) pips += '<span style="color:' + (i < cur ? '#e8c55a' : 'rgba(201,168,76,.25)') + ';">&#9646;</span>';
    html += '<div style="font-size:14px;letter-spacing:2px;margin-bottom:6px;">' + pips + '</div>';
    if (sigCrop) html += '<div style="color:#b9a76a;font-size:10px;margin-bottom:6px;">Signature crop: <b style="color:#E8E8E8;">' + sigCrop.name + '</b> grows here at <b style="color:#7CFFB0;">+' + Math.round(SIGNATURE_BONUS * 100) + '% yield</b>.</div>';
    BM.fortPanel.innerHTML = html;
    var btn = document.createElement('button'); btn.type = 'button';
    btn.textContent = maxed ? 'MAX FORTIFIED' : ('FORTIFY -> LV ' + (cur + 1) + '   (' + costLabel(cost) + ')');
    btn.disabled = maxed || !afford;
    btn.style.cssText = (btn.disabled ? btnCss(false) : btnCss(true)) + 'display:block;width:100%;margin-top:2px;padding:10px;font-size:12px;opacity:' + (btn.disabled ? '.5' : '1') + ';';
    if (!btn.disabled) btn.addEventListener('click', function (e) { e.stopPropagation(); fortifyDistrict(zid); });
    BM.fortPanel.appendChild(btn);
    var note = document.createElement('div'); note.style.cssText = 'color:#8a7f5e;font-size:9px;margin-top:6px;line-height:1.4;';
    note.textContent = 'Wood + stone raise the wall. A fortified district is harder for rival clans to raid -- your Town Hall + deck level survive the night. Gems never buy fortify.';
    BM.fortPanel.appendChild(note);
  }

  /* ====================================================================== *
   * (9) TOGGLE
   * ====================================================================== */
  function open() {
    if (!BM.ctx) return;
    ensureBar(); bindInput();
    try {
      var p = freshProfile();
      if (p && !p.builds_seeded) {
        BM.ctx.econ.mutateProfile(function (q) { for (var k in SEED) if (SEED.hasOwnProperty(k)) q[k] = ((q[k] | 0)) + SEED[k]; q.builds_seeded = 1; });
        bump();
        BM.ctx.showBanner('STARTER CACHE: ' + SEED.wood + ' wood / ' + SEED.stone + ' stone / ' + SEED.metal + ' metal', 2.0);
      }
    } catch (_e) {}
    BM.active = true; BM.demolish = false; BM.tend = false; if (!BM.sel) BM.sel = 'WALL';
    if (BM.bar) BM.bar.style.display = 'flex';
    if (BM.btn) { BM.btn.style.background = 'linear-gradient(180deg,#e8c55a,#c9a84c)'; BM.btn.style.color = '#15110a'; }
    refreshBar();
    BM.ctx.showBanner('BUILD MODE -- tap a piece, then tap the ground', 1.6);
  }
  function close() {
    if (editOn()) exitEdit();                    // AK-ISOEDIT: leaving build mode always tears the editor down
    BM.active = false; BM.ghost = null; BM.tend = false; BM.demolish = false;
    if (BM.bar) BM.bar.style.display = 'none';
    hideCropPicker(); hideCardPicker(); if (BM.crewPanel) BM.crewPanel.style.display = 'none'; if (BM.barnPanel) BM.barnPanel.style.display = 'none'; if (BM.fortPanel) BM.fortPanel.style.display = 'none';
    if (BM.btn) { BM.btn.style.background = 'rgba(8,8,14,.82)'; BM.btn.style.color = '#e8c55a'; }
  }
  function toggle() { if (BM.active) close(); else open(); }

  // GUARD -- hand off to the district-defense module (systems/guard.js owns the
  // p.guards layout + the akOpenGuard overlay). Lazily resolved at click time so
  // load order does not matter; degrades to a banner if the module is absent.
  function openGuardOverlay() {
    var zid = BM.ctx && BM.ctx.zoneId;
    if (typeof global.akOpenGuard === 'function') { try { global.akOpenGuard(zid); return; } catch (_e) {} }
    if (BM.ctx) BM.ctx.showBanner('GUARD POSTING UNLOCKS WITH THE DEFENSE MODULE', 1.4);
  }

  /* ====================================================================== *
   * (10) RENDER -- placed structures (always) + build overlay (build mode)
   * ====================================================================== */
  function dmgRatio(b) { return b.maxHp > 0 ? Math.max(0, Math.min(1, b.hp / b.maxHp)) : 1; }
  // AK-TIMERBAR 2026-06-22: ONE shared countdown bar (matches worldverbs harvest bar) so
  // construction + crops read the SAME visual language as mining. transform/fill only, 60fps-safe.
  function drawTimerBar(g, X, Y, frac, label) {
    var w = 48, h = 6;
    g.save();
    g.fillStyle = 'rgba(8,8,14,.85)'; g.fillRect(X - w / 2 - 2, Y - 2, w + 4, h + 4);
    g.fillStyle = 'rgba(232,197,90,.20)'; g.fillRect(X - w / 2, Y, w, h);
    g.fillStyle = 'rgba(232,197,90,.95)'; g.fillRect(X - w / 2, Y, w * Math.max(0, Math.min(1, frac)), h);
    g.fillStyle = '#e8e8e8'; g.font = '700 9px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    g.fillText(label, X, Y - 5);
    g.restore();
  }
  function drawBuildSite(g, X, Y, b, def) {
    var rot = b.rot || 0, w = effDW(def, rot), h = effDH(def, rot);
    g.save();
    g.fillStyle = 'rgba(30,26,18,.85)'; g.fillRect(X - w / 2, Y - h / 2, w, h);
    g.strokeStyle = GOLD; g.lineWidth = 1.5; g.setLineDash([4, 3]); g.strokeRect(X - w / 2, Y - h / 2, w, h); g.setLineDash([]);
    // AK-NOEMOJI 2026-07-02: gold gear vector marks the scaffold (was a wrench emoji, banned).
    g.strokeStyle = 'rgba(232,197,90,.9)'; g.fillStyle = 'rgba(232,197,90,.9)'; g.lineWidth = 1.6;
    var gcy = Y - 1, gr = 5;
    g.beginPath(); g.arc(X, gcy, gr, 0, 6.283); g.stroke();
    for (var gt = 0; gt < 6; gt++) { var ga = gt / 6 * 6.283, cs = Math.cos(ga), sn = Math.sin(ga); g.beginPath(); g.moveTo(X + cs * gr, gcy + sn * gr); g.lineTo(X + cs * (gr + 2.4), gcy + sn * (gr + 2.4)); g.stroke(); }
    g.beginPath(); g.arc(X, gcy, 1.5, 0, 6.283); g.fill();
    var rem = b.uc.t0 + b.uc.dur - Date.now(), frac = 1 - Math.max(0, Math.min(1, rem / (b.uc.dur || 1)));
    g.strokeStyle = 'rgba(201,168,76,.35)'; g.lineWidth = 3; g.beginPath(); g.arc(X, Y + h / 2 + 9, 8, 0, 6.283); g.stroke();
    g.strokeStyle = GREEN; g.lineWidth = 3; g.beginPath(); g.arc(X, Y + h / 2 + 9, 8, -Math.PI / 2, -Math.PI / 2 + frac * 6.283); g.stroke();
    g.restore();
    drawTimerBar(g, X, Y - h / 2 - 12, frac, fmtTime(Math.max(0, rem)));   // AK-TIMERBAR: build countdown over the scaffold
  }
  function drawStruct(g, X, Y, b) {
    var def = STRUCT[b.type]; if (!def) return;
    if (isUnderConstruction(b)) { drawBuildSite(g, X, Y, b, def); return; }     // scaffolding until the timer completes
    var rot = b.rot || 0, w = effDW(def, rot), h = effDH(def, rot), r = dmgRatio(b);
    g.save();
    var sim = spriteImg(def.sprite);
    var useSprite = spriteReady(sim) && !(def.family === 'garden' && b.crop);    // gardens with a crop use the procedural grow-stage draw
    if (useSprite) {
      // AK-ROT 2026-07-02: genuinely rotate the sprite (translate to center, rotate rot*90,
      // draw at NATURAL dw/dh) so a rotated wall segment turns instead of stretching. Left=left:
      // the piece pivots around its own unmoved center, no coordinate flip.
      if (rot) { g.translate(X, Y); g.rotate(rot * Math.PI / 2); g.drawImage(sim, -def.dw / 2, -def.dh / 2, def.dw, def.dh); }
      else { g.drawImage(sim, X - w / 2, Y - h / 2, w, h); }
    }
    else switch (def.family === 'wall' ? b.type : def.family) {
      case 'WALL': {
        g.fillStyle = '#5d3b1f'; g.fillRect(X - w / 2, Y - h / 2, w, h);
        g.strokeStyle = 'rgba(0,0,0,.35)'; g.lineWidth = 1;
        for (var py = -h / 2 + h / 3; py < h / 2; py += h / 3) { g.beginPath(); g.moveTo(X - w / 2, Y + py); g.lineTo(X + w / 2, Y + py); g.stroke(); }
        g.strokeStyle = GOLD_DK; g.lineWidth = 2; g.strokeRect(X - w / 2, Y - h / 2, w, h);
        break;
      }
      case 'STONE': {
        g.fillStyle = '#6c6f76'; g.fillRect(X - w / 2, Y - h / 2, w, h);
        g.strokeStyle = 'rgba(20,20,26,.6)'; g.lineWidth = 2;
        g.beginPath(); g.moveTo(X - w / 2, Y); g.lineTo(X + w / 2, Y);
        g.moveTo(X, Y - h / 2); g.lineTo(X, Y); g.moveTo(X - w / 4, Y); g.lineTo(X - w / 4, Y + h / 2); g.moveTo(X + w / 4, Y); g.lineTo(X + w / 4, Y + h / 2); g.stroke();
        g.strokeStyle = GOLD_DK; g.lineWidth = 1.5; g.strokeRect(X - w / 2, Y - h / 2, w, h);
        break;
      }
      case 'METAL': {
        g.fillStyle = '#39434e'; g.fillRect(X - w / 2, Y - h / 2, w, h);
        g.fillStyle = 'rgba(127,200,255,.18)'; g.fillRect(X - w / 2, Y - h / 2, w, 5);
        g.fillStyle = '#9aa7b3';
        var rv = [[-w / 2 + 7, -h / 2 + 7], [w / 2 - 7, -h / 2 + 7], [-w / 2 + 7, h / 2 - 7], [w / 2 - 7, h / 2 - 7]];
        for (var i = 0; i < rv.length; i++) { g.beginPath(); g.arc(X + rv[i][0], Y + rv[i][1], 2.2, 0, 7); g.fill(); }
        g.strokeStyle = GOLD; g.lineWidth = 2; g.strokeRect(X - w / 2, Y - h / 2, w, h);
        break;
      }
      case 'barricade': {
        g.fillStyle = '#1a1712'; g.fillRect(X - w / 2, Y - h / 2, w, h);
        g.save(); g.beginPath(); g.rect(X - w / 2, Y - h / 2, w, h); g.clip();
        g.strokeStyle = '#e8c55a'; g.lineWidth = 7;
        for (var sx = -w; sx < w; sx += 16) { g.beginPath(); g.moveTo(X + sx, Y - h / 2 - 4); g.lineTo(X + sx + h + 8, Y + h / 2 + 4); g.stroke(); }
        g.restore();
        g.strokeStyle = GOLD_DK; g.lineWidth = 2; g.strokeRect(X - w / 2, Y - h / 2, w, h);
        break;
      }
      case 'garden': {
        g.fillStyle = '#3a2716'; g.fillRect(X - w / 2, Y - h / 2, w, h);
        g.strokeStyle = GOLD_DK; g.lineWidth = 1.5; g.strokeRect(X - w / 2, Y - h / 2, w, h);
        g.strokeStyle = 'rgba(20,14,8,.5)'; g.lineWidth = 1;
        for (var ry = -h / 2 + 8; ry < h / 2 - 2; ry += 8) { g.beginPath(); g.moveTo(X - w / 2 + 3, Y + ry); g.lineTo(X + w / 2 - 3, Y + ry); g.stroke(); }
        if (b.crop && b.plantedAt) {
          var stg = gardenStage(b), ripeC = gardenRipe(b), grow = [0.22, 0.45, 0.72, 1.0][Math.max(0, Math.min(3, stg))];
          var spots = [[-w / 4, 4], [w / 5, -h / 8], [0, h / 6]];
          for (var f = 0; f < spots.length; f++) {
            var fx = X + spots[f][0], fy = Y + spots[f][1], stem = 10 * grow;
            g.fillStyle = '#2e7d32'; g.fillRect(fx - 1, fy - stem, 2, stem);
            if (stg >= 2) {
              var pr = 1.8 + 2.6 * grow; g.fillStyle = ripeC ? '#f4c430' : '#9ccc65';
              for (var a = 0; a < 6; a++) { var an = a / 6 * 6.283; g.beginPath(); g.arc(fx + Math.cos(an) * pr, fy - stem + Math.sin(an) * pr, 1.7, 0, 7); g.fill(); }
              if (ripeC) { g.fillStyle = '#6b4423'; g.beginPath(); g.arc(fx, fy - stem, 2, 0, 7); g.fill(); }
            }
          }
          if (ripeC) { var pa = BM.reduce ? 0.34 : (0.22 + 0.16 * (0.5 + 0.5 * Math.sin(BM.clock * 3))); g.strokeStyle = 'rgba(232,197,90,' + pa.toFixed(3) + ')'; g.lineWidth = 2; g.beginPath(); g.arc(X, Y - 3, Math.max(w, h) / 2 + 6, 0, 7); g.stroke(); }
          else { var grw = effGrow(b, CROPS[b.crop]), rmn = gardenRemainMs(b); drawTimerBar(g, X, Y - h / 2 - 12, 1 - rmn / grw, fmtTime(rmn)); }   // AK-TIMERBAR: crop grow countdown over the bed (weather-adjusted)
        }
        break;
      }
      case 'deco':
      default: {
        if (b.type === 'PATH') {
          g.fillStyle = 'rgba(40,40,52,.7)'; g.fillRect(X - w / 2, Y - h / 2, w, h);
          g.strokeStyle = 'rgba(201,168,76,.55)'; g.setLineDash([5, 4]); g.lineWidth = 1.5; g.strokeRect(X - w / 2 + 2, Y - h / 2 + 2, w - 4, h - 4); g.setLineDash([]);
        } else {
          g.fillStyle = '#2a2230'; g.beginPath(); g.arc(X, Y, w / 2 - 2, 0, 7); g.fill();
          g.strokeStyle = '#7fc8ff'; g.lineWidth = 2; g.beginPath(); g.arc(X, Y, w / 2 - 2, 0, 7); g.stroke();
          g.fillStyle = '#7CFFB0'; for (var pp = 0; pp < 3; pp++) { g.fillRect(X - 6 + pp * 5, Y - 10, 2, 9); }
        }
        break;
      }
    }
    if (def.hp > 0 && r < 1) {
      g.strokeStyle = 'rgba(10,8,6,.75)'; g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(X - w / 4, Y - h / 2); g.lineTo(X - w / 8, Y); g.lineTo(X - w / 5, Y + h / 2); g.stroke();
      if (r < 0.5) { g.beginPath(); g.moveTo(X + w / 5, Y - h / 2); g.lineTo(X + w / 10, Y - h / 8); g.lineTo(X + w / 4, Y + h / 3); g.stroke(); }
      if (r < 0.34 && !BM.reduce) { g.fillStyle = '#ffd36a'; for (var s = 0; s < 4; s++) { g.fillRect(X - w / 4 + Math.random() * w / 2, Y - h / 4 + Math.random() * h / 2, 1.5, 1.5); } }
    }
    g.restore();
  }

  /* ====================================================================== *
   * (10b) AK-ISOEDIT 2026-07-18 -- ISOMETRIC PROJECTION (edit mode only)
   * ====================================================================== *
   * drawStruct above stays TOP-DOWN and keeps owning the in-world path (host
   * cam, ctx.world.wx/wy). Edit mode swaps ONLY the projection: a DETACHED
   * camera {x,y,zoom,rot,w,h} maps world -> a 2:1 dimetric screen. The camera
   * is module-local -- the host cam is never touched, so walking away does not
   * move the editor and closing the editor does not move the dog.
   * PURE MATH: no DOM, no globals, node-requireable, so isoProject/isoUnproject
   * are round-trip testable head-less (see AK_BUILDMODE.iso).
   * Real-life logic law: the WORLD turns under a fixed camera on a rot snap, so
   * a piece keeps its own footprint -- left stays left, only the view turns.
   * ====================================================================== */
  var ISO_KX = 0.5, ISO_KY = 0.25, ISO_KH = 0.5;      // half-width / half-depth / height screen scales
  var ZOOM_MIN = 0.30, ZOOM_MAX = 2.40;
  var STRUCT_H = { wall: 46, barricade: 34, garden: 10, deco: 26 };   // world-unit extrusion per family
  function structH(def, type) { return type === 'PATH' ? 2 : ((def && STRUCT_H[def.family]) || 24); }
  function rotFwd(dx, dy, q) {
    switch ((q | 0) & 3) { case 1: return { x: -dy, y: dx }; case 2: return { x: -dx, y: -dy }; case 3: return { x: dy, y: -dx }; }
    return { x: dx, y: dy };
  }
  function rotBack(rx, ry, q) {
    switch ((q | 0) & 3) { case 1: return { x: ry, y: -rx }; case 2: return { x: -rx, y: -ry }; case 3: return { x: -ry, y: rx }; }
    return { x: rx, y: ry };
  }
  // world -> screen. hgt lifts a point off the ground plane (screen-y only, iso style).
  function isoProject(cam, wxp, wyp, hgt) {
    var z = cam.zoom || 1, r = rotFwd(wxp - cam.x, wyp - cam.y, cam.rot);
    return { x: (cam.w || 0) / 2 + (r.x - r.y) * ISO_KX * z,
             y: (cam.h || 0) / 2 + (r.x + r.y) * ISO_KY * z - (hgt || 0) * ISO_KH * z };
  }
  // screen -> world ON THE GROUND PLANE (hgt 0). Exact inverse of isoProject(cam,x,y,0).
  function isoUnproject(cam, sx, sy) {
    var z = cam.zoom || 1, ux = (sx - (cam.w || 0) / 2) / z, uy = (sy - (cam.h || 0) / 2) / z;
    var a = ux / ISO_KX, b = uy / ISO_KY;                 // a = rx-ry, b = rx+ry
    var w = rotBack((b + a) / 2, (b - a) / 2, cam.rot);
    return { x: cam.x + w.x, y: cam.y + w.y };
  }
  // the 4 screen corners of an axis-aligned world rect, lifted to hgt
  function isoQuad(cam, x, y, w, h, hgt) {
    var hw = w / 2, hh = h / 2;
    return [isoProject(cam, x - hw, y - hh, hgt), isoProject(cam, x + hw, y - hh, hgt),
            isoProject(cam, x + hw, y + hh, hgt), isoProject(cam, x - hw, y + hh, hgt)];
  }
  function quadPath(g, q) { g.beginPath(); g.moveTo(q[0].x, q[0].y); for (var i = 1; i < q.length; i++) g.lineTo(q[i].x, q[i].y); g.closePath(); }
  function quadMid(q) { var x = 0, y = 0; for (var i = 0; i < q.length; i++) { x += q[i].x; y += q[i].y; } return { x: x / q.length, y: y / q.length }; }
  var ISO_COL = {
    WALL:      { top: '#7a5228', side: '#40290f', line: '#c9a84c' },
    STONE:     { top: '#8a8d95', side: '#4e5158', line: '#c9a84c' },
    METAL:     { top: '#4d5966', side: '#252c34', line: '#e8c55a' },
    BARRICADE: { top: '#2c261c', side: '#15120c', line: '#e8c55a' },
    PATH:      { top: '#3a3a4a', side: '#24242c', line: 'rgba(201,168,76,.55)' },
    GARDEN:    { top: '#4a3320', side: '#281a0f', line: '#c9a84c' },
    PLANTER:   { top: '#3a3040', side: '#1e1824', line: '#7fc8ff' }
  };
  // ONE iso body: ground shadow -> 4 extruded side faces (painter-sorted) -> top face -> sprite.
  // tint 'ok'/'bad'/'sel' recolours the same geometry so the ghost, the dragged piece and a
  // settled piece all read as the SAME object.
  function drawIsoBody(g, cam, x, y, fwv, fhv, hgt, col, opts) {
    opts = opts || {};
    var ground = isoQuad(cam, x, y, fwv, fhv, 0), top = isoQuad(cam, x, y, fwv, fhv, hgt);
    var alpha = opts.alpha == null ? 1 : opts.alpha;
    g.save();
    g.globalAlpha = alpha;
    if (opts.shadow) { g.fillStyle = 'rgba(0,0,0,.34)'; quadPath(g, ground); g.fill(); }
    var order = [0, 1, 2, 3].sort(function (a, b) {
      return ((ground[a].y + ground[(a + 1) % 4].y) - (ground[b].y + ground[(b + 1) % 4].y));
    });
    for (var s = 0; s < order.length; s++) {
      var i = order[s], j = (i + 1) % 4;
      if (hgt <= 0) break;
      g.fillStyle = col.side;
      g.beginPath(); g.moveTo(ground[i].x, ground[i].y); g.lineTo(ground[j].x, ground[j].y);
      g.lineTo(top[j].x, top[j].y); g.lineTo(top[i].x, top[i].y); g.closePath(); g.fill();
      g.strokeStyle = 'rgba(0,0,0,.45)'; g.lineWidth = 1; g.stroke();
    }
    g.fillStyle = col.top; quadPath(g, top); g.fill();
    g.strokeStyle = col.line; g.lineWidth = opts.thick ? 2.5 : 1.4;
    if (opts.dash) { g.setLineDash([5, 4]); }
    quadPath(g, top); g.stroke(); g.setLineDash([]);
    g.restore();
    return { ground: ground, top: top, mid: quadMid(top) };
  }
  // a placed / dragged / ghosted structure in the iso view. Reads the SAME def + rot + footprint
  // the collision layer reads (fw/fh), so what you see in the editor is exactly what blocks.
  function drawIsoStruct(g, cam, b, x, y, opts) {
    var def = STRUCT[b.type]; if (!def) return;
    opts = opts || {};
    var rot = b.rot || 0, fwv = fw(def, rot), fhv = fh(def, rot), hgt = structH(def, b.type);
    var uc = isUnderConstruction(b);
    var col = ISO_COL[b.type] || ISO_COL.WALL;
    if (opts.tint === 'ok')  col = { top: 'rgba(124,255,176,.42)', side: 'rgba(60,170,110,.42)', line: GREEN };
    if (opts.tint === 'bad') col = { top: 'rgba(255,90,90,.40)',   side: 'rgba(150,40,40,.40)',  line: '#ff5a5a' };
    if (uc && !opts.tint)    col = { top: 'rgba(46,40,26,.9)',     side: 'rgba(24,20,12,.9)',    line: GOLD };
    var geo = drawIsoBody(g, cam, x, y, fwv, fhv, uc ? Math.max(6, hgt * 0.35) : hgt, col, {
      alpha: opts.alpha, shadow: opts.shadow !== false && !opts.tint, dash: uc, thick: !!opts.sel
    });
    var sim = spriteImg(def.sprite);
    if (spriteReady(sim) && !uc && !opts.tint) {
      var sw = Math.abs(geo.top[1].x - geo.top[3].x) * 0.72, sh = sw * (def.dh && def.dw ? (def.dh / def.dw) : 0.7);
      g.save(); g.globalAlpha = (opts.alpha == null ? 1 : opts.alpha) * 0.95;
      g.drawImage(sim, geo.mid.x - sw / 2, geo.mid.y - sh * 0.72, sw, sh);
      g.restore();
    }
    if (opts.sel) {                                    // gold selection ring on the ground cell
      g.save(); g.strokeStyle = GOLD; g.lineWidth = 2.5; g.setLineDash([7, 5]);
      quadPath(g, geo.ground); g.stroke(); g.setLineDash([]); g.restore();
    }
    if (b.crop && b.plantedAt && !uc && !opts.tint) {   // the SAME crop state the world path draws
      var ripe = gardenRipe(b);
      g.save(); g.fillStyle = ripe ? '#f4c430' : '#9ccc65';
      for (var c = 0; c < 3; c++) { g.beginPath(); g.arc(geo.mid.x - 8 + c * 8, geo.mid.y - 3, 2.6, 0, 7); g.fill(); }
      if (ripe) { g.strokeStyle = 'rgba(232,197,90,.75)'; g.lineWidth = 2; g.beginPath(); g.arc(geo.mid.x, geo.mid.y - 3, 15, 0, 7); g.stroke(); }
      g.restore();
    }
    if (uc) {
      var rem = b.uc.t0 + b.uc.dur - Date.now();
      g.save(); g.fillStyle = GOLD; g.font = '800 10px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(fmtTime(Math.max(0, rem)), geo.mid.x, geo.mid.y); g.restore();
    }
    return geo;
  }

  function drawOverlay(ctx, g) {
    var mx = ctx.world.wx(ctx.me.x), my = ctx.world.wy(ctx.me.y);
    g.save();
    g.strokeStyle = 'rgba(232,197,90,.30)'; g.lineWidth = 1.5; g.setLineDash([6, 6]);
    g.beginPath(); g.arc(mx, my, BUILD_RANGE, 0, 7); g.stroke(); g.setLineDash([]);
    g.fillStyle = 'rgba(201,168,76,.18)';
    var cx = snap(ctx.me.x), cy = snap(ctx.me.y), R = BUILD_RANGE;
    for (var x = cx - R; x <= cx + R; x += GRID) for (var y = cy - R; y <= cy + R; y += GRID) {
      var dxp = x - ctx.me.x, dyp = y - ctx.me.y; if (dxp * dxp + dyp * dyp > R * R) continue;
      g.fillRect(ctx.world.wx(x) - 1, ctx.world.wy(y) - 1, 2, 2);
    }
    if (BM.ghost && BM.sel && !BM.demolish && !BM.tend) {
      var def = STRUCT[BM.sel], gx = ctx.world.wx(BM.ghost.x), gy = ctx.world.wy(BM.ghost.y), grot = BM.rot | 0;
      var freeB = builderState(freshProfile()).free > 0;
      var ok = !placeReason(ctx, def, BM.ghost.x, BM.ghost.y, grot) && canAfford(freshProfile(), def) && freeB;
      var w = effDW(def, grot), h = effDH(def, grot);
      g.globalAlpha = 0.55;
      g.fillStyle = ok ? 'rgba(124,255,176,.35)' : 'rgba(255,90,90,.35)';
      g.strokeStyle = ok ? GREEN : '#ff5a5a'; g.lineWidth = 2;
      if (def.shape === 'circle') { g.beginPath(); g.arc(gx, gy, (def.cr || 24), 0, 7); g.fill(); g.stroke(); }
      else { g.fillRect(gx - w / 2, gy - h / 2, w, h); g.strokeRect(gx - w / 2, gy - h / 2, w, h); }
      // AK-NOEMOJI 2026-07-02: the ghost shows the real piece sprite (was the emoji glyph). Degrades
      // to a clean gold text label if the sprite is not ready -- never an emoji.
      g.globalAlpha = 1;
      var gsi = spriteImg(def.sprite);
      if (spriteReady(gsi)) { g.drawImage(gsi, gx - w / 2, gy - h / 2, w, h); }
      else { g.font = '700 10px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = GOLD; g.fillText(def.glyph, gx, gy); }
    }
    g.restore();
  }

  /* ====================================================================== *
   * (11) AK-ISOEDIT 2026-07-18 -- EDIT MODE: detached iso camera + drag editor
   * ====================================================================== *
   * The CoC-style base editor. Everything here is ADDITIVE: its own <canvas>
   * (#ak-bm-edit-cv), its own camera, its own pointer handlers bound to THAT
   * canvas only. The in-world tap-to-place path above is untouched.
   *
   * REFLECTION PAIR (the whole point): the editor writes through the SAME
   * place() / moveBuild() / demolishAt() -> ctx.econ.mutateProfile -> p.builds[]
   * path the world uses. There is no editor-only mirror array. Move a wall in
   * the editor and the hub world + the raid defense read it moved, because they
   * read the same p.builds[] entry (onDrawWorld -> drawStruct, buildRects ->
   * AK_COLLISION.obstaclesFor).
   *
   * WHY CANVAS2D: three_boot's budget() caps the whole app at ONE WebGLRenderer
   * shared by every mode, and the hub already spends up to 5 model-viewer
   * contexts on a phone. The editor therefore NEVER opens a GL context. AK_THREE
   * is PROBED (editTier) and used only to drop the soft-shadow pass when the GPU
   * is already loaded. The iso view is fully functional with three absent.
   *
   * Headless-safe: no DOM at load. BM.edit stays null until enterEdit().
   * ====================================================================== */
  var DRAG_SLOP = 6;                    // px before a press becomes a drag (tap stays a tap)
  function editState() {
    if (!BM.edit) BM.edit = {
      on: false, cv: null, g: null, top: null, pal: null, info: null, raf: 0, clock: 0, bound: false,
      cam: { x: 0, y: 0, zoom: 1, rot: 0, w: 1, h: 1 },
      ptr: {}, np: 0, pan: null, pinch: null, drag: null, ghost: null,
      multi: false,                // AK-ISOFIX 2026-07-18: latched while a gesture is multi-touch
      sel: null, rot: 0, pick: -1, pop: null, tier: 1
    };
    return BM.edit;
  }
  function editOn() { return !!(BM.edit && BM.edit.on); }
  // AK_THREE probe. NEVER a dependency -- see the WHY CANVAS2D note above.
  function editTier() {
    try {
      var T = global.AK_THREE; if (!T || typeof T.budget !== 'function') return 1;
      var b = T.budget() || {}, used = (b.modelViewer | 0) + (b.threeRenderers | 0);
      return used >= ((b.ceiling | 0) - 1) ? 0 : 1;      // GPU already loaded -> skip the shadow pass
    } catch (_) { return 1; }
  }

  /* ---- camera ---------------------------------------------------------- */
  function editZoom(mult, ax, ay) {
    var E = editState(), c = E.cam, z0 = c.zoom;
    var anchor = (ax == null) ? null : isoUnproject(c, ax, ay);
    c.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z0 * mult));
    if (anchor) { var after = isoUnproject(c, ax, ay); c.x += anchor.x - after.x; c.y += anchor.y - after.y; }
    refreshEditUI();
  }
  function editRotCam(dir) { var E = editState(); E.cam.rot = ((E.cam.rot | 0) + (dir | 0) + 4) & 3; refreshEditUI(); }
  function editCenter(E) {
    E = E || editState();
    var p = prof(), builds = (p && p.builds) || [], zid = BM.ctx && BM.ctx.zoneId, n = 0, sx = 0, sy = 0;
    for (var i = 0; i < builds.length; i++) { var b = builds[i]; if (b.zone !== zid) continue; sx += b.x; sy += b.y; n++; }
    if (n) { E.cam.x = sx / n; E.cam.y = sy / n; }
    else if (BM.ctx && BM.ctx.me) { E.cam.x = BM.ctx.me.x; E.cam.y = BM.ctx.me.y; }
    E.cam.zoom = 1; E.cam.rot = 0;
    refreshEditUI();
  }
  function editTurnPiece() {
    var E = editState();
    E.rot = ((E.rot | 0) + 1) & 3;
    if (E.pick >= 0 && !E.sel) {                       // a selected piece turns in place, on the spot
      var p = freshProfile(), b = p && p.builds && p.builds[E.pick];
      if (b) { var r = moveBuild(BM.ctx, E.pick, b.x, b.y, ((b.rot || 0) + 1) & 3); if (r.ok) editPop(E, b.x, b.y); }
    }
    refreshEditUI();
  }
  function editPop(E, x, y) { E.pop = { x: x, y: y, t: E.clock }; }
  function editHaptic(k) { try { if (global.AK_JUICE && AK_JUICE.haptic) AK_JUICE.haptic(k); } catch (_) {} }

  /* ---- hit test -------------------------------------------------------- */
  // Ground-plane test first; then ONE height-compensated retry so tapping the drawn BODY of a
  // tall wall (drawn lifted off its cell) still grabs that wall and not the cell behind it.
  function editHit(E, sx, sy) {
    var zid = BM.ctx && BM.ctx.zoneId;
    var w0 = isoUnproject(E.cam, sx, sy), i = buildAt(zid, w0.x, w0.y);
    if (i >= 0) return i;
    var w1 = isoUnproject(E.cam, sx, sy + (STRUCT_H.wall * ISO_KH * (E.cam.zoom || 1)));
    return buildAt(zid, w1.x, w1.y);
  }
  function editSnapWorld(E, sx, sy) { var w = isoUnproject(E.cam, sx, sy); return { x: snap(w.x), y: snap(w.y) }; }

  /* ---- pointer input (bound to the editor canvas ONLY) ------------------ */
  function ptrList(E) { var a = []; for (var k in E.ptr) if (E.ptr.hasOwnProperty(k)) a.push(E.ptr[k]); return a; }
  function onEditDown(e) {
    var E = editState(); if (!E.on) return;
    e.preventDefault(); e.stopPropagation();
    E.ptr[e.pointerId] = { x: e.clientX, y: e.clientY, id: e.pointerId };
    E.np = ptrList(E).length;
    try { if (E.cv.setPointerCapture) E.cv.setPointerCapture(e.pointerId); } catch (_) {}
    if (E.np >= 2) {                                   // second finger -> pinch, drop any 1-finger gesture
      var a = ptrList(E);
      E.pan = null; E.drag = null;
      // AK-ISOFIX 2026-07-18: a pinch is a CAMERA gesture, never a placement. Disarm the armed
      // ghost and LATCH multi, so lifting the last finger cannot fall through to editCommit and
      // drop a stale structure (which also charged materials + burned a builder slot).
      E.ghost = null; E.multi = true;
      E.pinch = { d0: Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y) || 1, z0: E.cam.zoom,
                  mx: (a[0].x + a[1].x) / 2, my: (a[0].y + a[1].y) / 2, cx: E.cam.x, cy: E.cam.y };
      return;
    }
    if (E.sel) { E.ghost = editSnapWorld(E, e.clientX, e.clientY); refreshEditUI(); return; }
    var idx = editHit(E, e.clientX, e.clientY);
    if (idx >= 0) {
      var p = freshProfile(), b = p && p.builds && p.builds[idx];
      var w = isoUnproject(E.cam, e.clientX, e.clientY);
      E.pick = idx;
      E.drag = { idx: idx, gx: w.x - (b ? b.x : w.x), gy: w.y - (b ? b.y : w.y),
                 sx: e.clientX, sy: e.clientY, wx: b ? b.x : w.x, wy: b ? b.y : w.y, moved: false };
      editHaptic('crew_ping');
      refreshEditUI();
      return;
    }
    E.pick = -1;
    E.pan = { sx: e.clientX, sy: e.clientY, cx: E.cam.x, cy: E.cam.y };
    refreshEditUI();
  }
  function onEditMove(e) {
    var E = editState(); if (!E.on) return;
    if (E.ptr[e.pointerId]) { E.ptr[e.pointerId].x = e.clientX; E.ptr[e.pointerId].y = e.clientY; }
    if (E.pinch) {
      var a = ptrList(E); if (a.length < 2) return;
      e.preventDefault();
      var d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y) || 1;
      E.cam.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, E.pinch.z0 * (d / E.pinch.d0)));
      var mx = (a[0].x + a[1].x) / 2, my = (a[0].y + a[1].y) / 2;
      var c0 = { x: E.pinch.cx, y: E.pinch.cy, zoom: E.cam.zoom, rot: E.cam.rot, w: E.cam.w, h: E.cam.h };
      var g0 = isoUnproject(c0, E.pinch.mx, E.pinch.my), g1 = isoUnproject(c0, mx, my);
      E.cam.x = E.pinch.cx + (g0.x - g1.x); E.cam.y = E.pinch.cy + (g0.y - g1.y);
      return;
    }
    if (E.drag) {
      e.preventDefault();
      if (!E.drag.moved && Math.hypot(e.clientX - E.drag.sx, e.clientY - E.drag.sy) < DRAG_SLOP) return;
      E.drag.moved = true;
      var w = isoUnproject(E.cam, e.clientX, e.clientY);
      E.drag.wx = snap(w.x - E.drag.gx); E.drag.wy = snap(w.y - E.drag.gy);
      return;
    }
    if (E.sel && !E.multi) { E.ghost = editSnapWorld(E, e.clientX, e.clientY); return; }   // AK-ISOFIX: no re-arm mid-pinch
    if (E.pan) {
      e.preventDefault();
      var cp = { x: E.pan.cx, y: E.pan.cy, zoom: E.cam.zoom, rot: E.cam.rot, w: E.cam.w, h: E.cam.h };
      var s0 = isoUnproject(cp, E.pan.sx, E.pan.sy), s1 = isoUnproject(cp, e.clientX, e.clientY);
      E.cam.x = E.pan.cx + (s0.x - s1.x); E.cam.y = E.pan.cy + (s0.y - s1.y);
    }
  }
  function onEditUp(e) {
    var E = editState(); if (!E.on) return;
    delete E.ptr[e.pointerId]; E.np = ptrList(E).length;
    try { if (E.cv.releasePointerCapture) E.cv.releasePointerCapture(e.pointerId); } catch (_) {}
    if (E.pinch) { if (E.np < 2) { E.pinch = null; refreshEditUI(); } return; }
    // AK-ISOFIX 2026-07-18: the TAIL of a multi-touch gesture is not a tap. Hold the latch until
    // every finger is off, so the second release lands here instead of in the commit below.
    if (E.multi) { if (E.np === 0) { E.multi = false; E.ghost = null; refreshEditUI(); } return; }
    if (E.drag) {
      var d = E.drag; E.drag = null;
      if (d.moved) {
        var r = moveBuild(BM.ctx, d.idx, d.wx, d.wy, null);
        if (r && r.ok && r.moved) { editPop(E, r.x, r.y); editHaptic('deploy'); if (BM.ctx) BM.ctx.showBanner('MOVED', 0.7); }
      } else if (BM.ctx) {
        var p = freshProfile(), b = p && p.builds && p.builds[d.idx], def = b && STRUCT[b.type];
        if (def) BM.ctx.showBanner(def.name.toUpperCase() + ' -- DRAG TO MOVE', 1.0);
      }
      refreshEditUI(); return;
    }
    if (E.sel && E.ghost) { editCommit(E); return; }
    E.pan = null;
  }
  function onEditCancel(e) {
    var E = editState(); if (!E.on) return;
    delete E.ptr[e.pointerId]; E.np = ptrList(E).length;
    E.pan = null; E.drag = null; if (E.np < 2) E.pinch = null;
    if (E.np === 0) { E.multi = false; E.ghost = null; }        // AK-ISOFIX 2026-07-18: cancel clears the latch too
  }
  // COMMIT: the drop. Goes through place() -- same cost, same builder job, same p.builds write.
  function editCommit(E) {
    if (!E.sel || !E.ghost || !BM.ctx) return false;
    var gx = E.ghost.x, gy = E.ghost.y;
    var ok = place(BM.ctx, E.sel, gx, gy, { rot: E.rot, ignoreRange: true });
    if (ok) { editPop(E, gx, gy); editHaptic('deploy'); }
    refreshEditUI();
    return ok;
  }
  function editScrapSel() {
    var E = editState(); if (E.pick < 0 || !BM.ctx) { if (BM.ctx) BM.ctx.showBanner('TAP A STRUCTURE FIRST', 1.0); return false; }
    var p = freshProfile(), b = p && p.builds && p.builds[E.pick];
    if (!b) { E.pick = -1; return false; }
    var done = demolishAt(BM.ctx, b.x, b.y);            // reuse the in-world scrap path (50% refund)
    if (done) { editPop(E, b.x, b.y); editHaptic('hit_2'); E.pick = -1; }   // real AK_JUICE key (see juice.js HAPTIC)
    refreshEditUI();
    return done;
  }

  /* ---- DOM: canvas + toolbar + palette --------------------------------- */
  function clearKids(el) { if (el) while (el.firstChild) el.removeChild(el.firstChild); }
  function editBtn(label, id, fn) {
    var b = document.createElement('button'); b.type = 'button'; b.textContent = label; if (id) b.id = id;
    b.style.cssText = btnCss(false) + 'flex:0 0 auto;';
    b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); fn(); });
    return b;
  }
  function ensureEditDom() {
    if (typeof document === 'undefined') return null;
    var E = editState();
    if (E.cv) return E;
    var cv = document.createElement('canvas'); cv.id = 'ak-bm-edit-cv';
    cv.style.cssText = 'position:fixed;left:0;top:0;width:100%;height:100%;z-index:9;display:none;' +
      'touch-action:none;-webkit-tap-highlight-color:transparent;background:radial-gradient(120% 90% at 50% 18%,#15162a 0%,#08080e 72%);';
    document.body.appendChild(cv);
    E.cv = cv; E.g = cv.getContext ? cv.getContext('2d') : null;

    var top = document.createElement('div'); top.id = 'ak-bm-edit-top';
    top.style.cssText = 'position:fixed;left:0;right:0;top:0;z-index:12;display:none;align-items:center;gap:6px;' +
      'padding:calc(6px + env(safe-area-inset-top)) 8px 6px;overflow-x:auto;' +
      'background:linear-gradient(180deg,rgba(8,8,12,.97),rgba(8,8,12,.72));border-bottom:1px solid rgba(201,168,76,.45);' +
      'font-family:Inter,system-ui,sans-serif;-webkit-tap-highlight-color:transparent;';
    var ttl = document.createElement('span'); ttl.textContent = 'BASE EDITOR';
    ttl.style.cssText = 'flex:0 0 auto;color:#e8c55a;font-weight:900;font-size:11px;letter-spacing:.06em;';
    var info = document.createElement('span'); info.id = 'ak-bm-edit-info';
    info.style.cssText = 'flex:1 1 auto;min-width:90px;color:#E8E8E8;font-weight:700;font-size:10px;letter-spacing:.02em;white-space:nowrap;';
    top.appendChild(ttl); top.appendChild(info);
    top.appendChild(editBtn('TURN', 'ak-bm-edit-turn', editTurnPiece));
    top.appendChild(editBtn('VIEW <', null, function () { editRotCam(-1); }));
    top.appendChild(editBtn('VIEW >', null, function () { editRotCam(1); }));
    top.appendChild(editBtn('-', null, function () { editZoom(1 / 1.25); }));
    top.appendChild(editBtn('+', null, function () { editZoom(1.25); }));
    top.appendChild(editBtn('CENTER', null, function () { editCenter(); }));
    top.appendChild(editBtn('SCRAP', 'ak-bm-edit-scrap', editScrapSel));
    var done = document.createElement('button'); done.type = 'button'; done.textContent = 'DONE';
    done.style.cssText = btnCss(true) + 'flex:0 0 auto;';
    done.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); exitEdit(); });
    top.appendChild(done);
    document.body.appendChild(top); E.top = top; E.info = info;

    var pal = document.createElement('div'); pal.id = 'ak-bm-edit-pal';
    pal.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:12;display:none;gap:6px;overflow-x:auto;' +
      'padding:8px 8px calc(8px + env(safe-area-inset-bottom));background:linear-gradient(0deg,rgba(8,8,12,.97),rgba(8,8,12,.80));' +
      'border-top:1px solid rgba(201,168,76,.45);font-family:Inter,system-ui,sans-serif;-webkit-tap-highlight-color:transparent;';
    pal.appendChild(editPalTile(null));                 // MOVE tool -- the drag-existing mode
    for (var i = 0; i < ORDER.length; i++) pal.appendChild(editPalTile(ORDER[i]));
    document.body.appendChild(pal); E.pal = pal;

    if (!E.bound) {
      cv.addEventListener('pointerdown', onEditDown);
      cv.addEventListener('pointermove', onEditMove);
      cv.addEventListener('pointerup', onEditUp);
      cv.addEventListener('pointercancel', onEditCancel);
      cv.addEventListener('wheel', function (e) { e.preventDefault(); editZoom(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY); }, { passive: false });
      E.bound = true;
    }
    return E;
  }
  // one palette tile. key===null builds the MOVE tool (clears the selection -> drag existing).
  function editPalTile(key) {
    var def = key ? STRUCT[key] : null;
    var t = document.createElement('button'); t.type = 'button'; t.setAttribute('data-ekey', key || '_move');
    t.style.cssText = tileCss(false, true);
    var ic = document.createElement('div');
    ic.style.cssText = 'width:22px;height:22px;display:flex;align-items:center;justify-content:center;';
    if (def) {
      var im = document.createElement('img'); im.src = def.sprite; im.width = 22; im.height = 22;
      im.style.cssText = 'width:22px;height:22px;object-fit:contain;';
      im.onerror = function () { this.style.display = 'none'; };
      ic.appendChild(im);
    } else {
      var mv = document.createElement('span'); mv.textContent = '<>';
      mv.style.cssText = 'color:#e8c55a;font-weight:900;font-size:13px;letter-spacing:-.05em;';
      ic.appendChild(mv);
    }
    var n = document.createElement('div'); n.textContent = def ? def.name : 'MOVE';
    n.style.cssText = 'font-size:9px;font-weight:800;color:#e8c55a;margin-top:2px;white-space:nowrap;';
    var c = document.createElement('div'); c.textContent = def ? costStr(def) : 'drag a piece';
    c.style.cssText = 'font-size:8px;font-weight:700;color:#b9a76a;margin-top:1px;white-space:nowrap;';
    t.appendChild(ic); t.appendChild(n); t.appendChild(c);
    t.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      var E = editState();
      E.sel = (key && E.sel !== key) ? key : null;
      E.ghost = null; E.pick = -1; E.drag = null;
      if (E.sel && BM.ctx) BM.ctx.showBanner('DRAG ONTO THE GRID', 1.0);
      refreshEditUI();
    });
    return t;
  }
  function refreshEditUI() {
    var E = BM.edit; if (!E || !E.on || typeof document === 'undefined') return;
    if (E.info) {
      var p = freshProfile(), st = builderState(p);
      var mode = E.sel ? ('PLACE ' + (STRUCT[E.sel] ? STRUCT[E.sel].name.toUpperCase() : E.sel))
                       : (E.pick >= 0 ? 'SELECTED -- DRAG TO MOVE' : 'DRAG A PIECE TO MOVE IT');
      var bits = [mode, 'W' + ((p && p.wood) | 0), 'S' + ((p && p.stone) | 0), 'M' + ((p && p.metal) | 0),
                  'CREW ' + st.free + '/' + st.cap, 'x' + E.cam.zoom.toFixed(2), 'VIEW ' + (E.cam.rot * 90) + 'deg'];
      E.info.textContent = bits.join('  |  ');
    }
    var turn = document.getElementById('ak-bm-edit-turn');
    if (turn) { turn.textContent = 'TURN ' + ((E.rot | 0) * 90) + 'deg'; turn.style.cssText = btnCss((E.rot | 0) !== 0) + 'flex:0 0 auto;'; }
    var scrap = document.getElementById('ak-bm-edit-scrap');
    if (scrap) scrap.style.cssText = btnCss(E.pick >= 0) + 'flex:0 0 auto;';
    if (E.pal) {
      var pr = freshProfile(), kids = E.pal.children;
      for (var i = 0; i < kids.length; i++) {
        var k = kids[i].getAttribute('data-ekey');
        if (k === '_move') kids[i].style.cssText = tileCss(!E.sel, true);
        else kids[i].style.cssText = tileCss(E.sel === k, canAfford(pr, STRUCT[k]));
      }
    }
  }
  // AK-ISOFIX 2026-07-18: #banner (index.html) is position:fixed with NO z-index, so it paints
  // UNDER our fixed z-index:9 editor canvas -- every editor message (MOVED / OUT OF BOUNDS /
  // SPOT TAKEN / ALL BUILDERS BUSY) was landing behind an opaque canvas. Lift it above the
  // editor chrome while editing, restore the original inline value on exit. No index.html edit.
  var _bannerZ = null;
  function liftBanner(on) {
    if (typeof document === 'undefined') return;
    var el = document.getElementById('banner'); if (!el || !el.style) return;
    if (on) { if (_bannerZ === null) _bannerZ = el.style.zIndex || ''; el.style.zIndex = '13'; }
    else if (_bannerZ !== null) { el.style.zIndex = _bannerZ; _bannerZ = null; }
  }
  function onEditResize() { var E = BM.edit; if (E && E.on) editResize(E); }
  function editResize(E) {
    if (!E || !E.cv) return;
    var w = (global.innerWidth | 0) || 360, h = (global.innerHeight | 0) || 640;
    var dpr = Math.min(2, global.devicePixelRatio || 1);
    E.cv.width = Math.round(w * dpr); E.cv.height = Math.round(h * dpr);
    E.cam.w = w; E.cam.h = h; E.dpr = dpr;
  }

  /* ---- render ---------------------------------------------------------- */
  function drawIsoGrid(g, cam, ctx) {
    var c = [isoUnproject(cam, 0, 0), isoUnproject(cam, cam.w, 0), isoUnproject(cam, cam.w, cam.h), isoUnproject(cam, 0, cam.h)];
    var minx = Math.min(c[0].x, c[1].x, c[2].x, c[3].x), maxx = Math.max(c[0].x, c[1].x, c[2].x, c[3].x);
    var miny = Math.min(c[0].y, c[1].y, c[2].y, c[3].y), maxy = Math.max(c[0].y, c[1].y, c[2].y, c[3].y);
    var WW = (ctx && ctx.world && ctx.world.WORLD_W) || 4000, WH = (ctx && ctx.world && ctx.world.WORLD_H) || 4000;
    minx = Math.max(0, minx); miny = Math.max(0, miny); maxx = Math.min(WW, maxx); maxy = Math.min(WH, maxy);
    if (maxx <= minx || maxy <= miny) return;
    var x0 = Math.floor(minx / GRID) * GRID, x1 = Math.ceil(maxx / GRID) * GRID;
    var y0 = Math.floor(miny / GRID) * GRID, y1 = Math.ceil(maxy / GRID) * GRID;
    var step = GRID * Math.max(1, Math.ceil(((x1 - x0) / GRID) / 160));      // thin out when zoomed way out
    g.save();
    g.strokeStyle = 'rgba(201,168,76,.16)'; g.lineWidth = 1;
    var a, b, x, y;
    for (x = x0; x <= x1; x += step) {
      a = isoProject(cam, x, y0, 0); b = isoProject(cam, x, y1, 0);
      g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
    }
    for (y = y0; y <= y1; y += step) {
      a = isoProject(cam, x0, y, 0); b = isoProject(cam, x1, y, 0);
      g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
    }
    var bounds = [isoProject(cam, 0, 0, 0), isoProject(cam, WW, 0, 0), isoProject(cam, WW, WH, 0), isoProject(cam, 0, WH, 0)];
    g.strokeStyle = 'rgba(232,197,90,.45)'; g.lineWidth = 2; quadPath(g, bounds); g.stroke();
    g.restore();
  }
  function drawIsoMe(g, cam, ctx) {
    if (!ctx || !ctx.me) return;
    var s = isoProject(cam, ctx.me.x, ctx.me.y, 0), z = cam.zoom || 1;
    g.save();
    g.strokeStyle = 'rgba(124,255,176,.85)'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(s.x, s.y - 7 * z); g.lineTo(s.x + 7 * z, s.y); g.lineTo(s.x, s.y + 7 * z); g.lineTo(s.x - 7 * z, s.y); g.closePath(); g.stroke();
    g.fillStyle = '#7CFFB0'; g.font = '800 9px Inter,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
    g.fillText('YOU', s.x, s.y - 11 * z);
    g.restore();
  }
  function drawEdit(E, ctx) {
    var g = E.g; if (!g || !ctx) return;
    var dpr = E.dpr || 1;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, E.cam.w, E.cam.h);
    drawIsoGrid(g, E.cam, ctx);

    var p = prof(), builds = (p && p.builds) || [], zid = ctx.zoneId, list = [], i, r;
    var zbs = (ctx.activeZone && ctx.activeZone.buildings) || [];
    for (i = 0; i < zbs.length; i++) {                 // the host's fixed buildings, so you can see what blocks
      var zb = zbs[i]; r = rotFwd(zb.x - E.cam.x, zb.y - E.cam.y, E.cam.rot);
      list.push({ kind: 'zb', zb: zb, d: r.x + r.y });
    }
    for (i = 0; i < builds.length; i++) {
      var b = builds[i]; if (b.zone !== zid) continue;
      var bx = b.x, by = b.y;
      if (E.drag && E.drag.idx === i && E.drag.moved) { bx = E.drag.wx; by = E.drag.wy; }
      r = rotFwd(bx - E.cam.x, by - E.cam.y, E.cam.rot);
      list.push({ kind: 'b', i: i, b: b, x: bx, y: by, d: r.x + r.y });
    }
    list.sort(function (a, c) { return a.d - c.d; });   // painter's order: far cells first

    var shadow = E.tier > 0;
    for (i = 0; i < list.length; i++) {
      var it = list[i];
      if (it.kind === 'zb') {
        drawIsoBody(g, E.cam, it.zb.x, it.zb.y, (it.zb.w || 60), (it.zb.h || 60) / 2, (it.zb.h || 60) * 0.55,
          { top: '#2a2b3a', side: '#171824', line: 'rgba(201,168,76,.30)' }, { alpha: 0.85, shadow: shadow });
        continue;
      }
      var dragging = !!(E.drag && E.drag.idx === it.i && E.drag.moved);
      var tint = null;
      if (dragging) {
        var def = STRUCT[it.b.type];
        tint = placeReason(ctx, def, it.x, it.y, it.b.rot || 0, { ignoreRange: true, exclude: it.i }) ? 'bad' : 'ok';
      }
      drawIsoStruct(g, E.cam, it.b, it.x, it.y, {
        sel: E.pick === it.i && !dragging, tint: tint, shadow: shadow, alpha: dragging ? 0.85 : 1
      });
    }
    if (E.sel && E.ghost) {                            // the drag-out ghost: green valid / red invalid
      var gdef = STRUCT[E.sel];
      var bad = placeReason(ctx, gdef, E.ghost.x, E.ghost.y, E.rot, { ignoreRange: true })
             || (canAfford(freshProfile(), gdef) ? null : 'NEED ' + costStr(gdef))
             || (builderState(freshProfile()).free > 0 ? null : 'ALL BUILDERS BUSY');
      drawIsoStruct(g, E.cam, { type: E.sel, rot: E.rot }, E.ghost.x, E.ghost.y,
        { tint: bad ? 'bad' : 'ok', alpha: 0.75, shadow: false });
      if (bad) {
        var gs = isoProject(E.cam, E.ghost.x, E.ghost.y, 0);
        g.save(); g.fillStyle = '#ff5a5a'; g.font = '800 10px Inter,sans-serif'; g.textAlign = 'center';
        g.fillText(bad, gs.x, gs.y + 22); g.restore();
      }
    }
    if (E.pop) {                                       // the commit pop: one expanding gold ring
      var age = E.clock - E.pop.t;
      if (age > 0.5) E.pop = null;
      else {
        var ps = isoProject(E.cam, E.pop.x, E.pop.y, 0), f = age / 0.5, z = E.cam.zoom || 1;
        g.save(); g.globalAlpha = 1 - f; g.strokeStyle = GREEN; g.lineWidth = 3;
        if (g.ellipse) { g.beginPath(); g.ellipse(ps.x, ps.y, (16 + 44 * f) * z, (8 + 22 * f) * z, 0, 0, 6.283); g.stroke(); }
        else { g.beginPath(); g.arc(ps.x, ps.y, (16 + 44 * f) * z, 0, 6.283); g.stroke(); }
        g.restore();
      }
    }
    drawIsoMe(g, E.cam, ctx);
  }
  function editFrame() {
    var E = BM.edit;
    if (!E || !E.on) { if (E) E.raf = 0; return; }
    E.clock += 1 / 60;
    try { reconcileJobs(); } catch (_e) {}             // build timers keep running while you edit
    try { drawEdit(E, BM.ctx); } catch (_e2) {}
    E.raf = (typeof requestAnimationFrame === 'function') ? requestAnimationFrame(editFrame) : 0;
  }
  function startEditLoop(E) {
    if (E.raf || typeof requestAnimationFrame !== 'function') return;
    E.raf = requestAnimationFrame(editFrame);
  }

  /* ---- enter / exit ---------------------------------------------------- */
  function enterEdit() {
    if (!BM.ctx || typeof document === 'undefined') return false;
    if (!BM.active) open();                            // edit implies build mode (starter cache + host stick yields)
    var E = ensureEditDom(); if (!E || !E.g) return false;
    E.on = true; E.sel = null; E.pick = -1; E.ghost = null;
    E.drag = null; E.pan = null; E.pinch = null; E.ptr = {}; E.np = 0; E.multi = false;
    E.rot = BM.rot | 0; E.tier = editTier();
    editResize(E); editCenter(E);
    E.cv.style.display = 'block'; E.top.style.display = 'flex'; E.pal.style.display = 'flex';
    liftBanner(true);                                  // AK-ISOFIX: keep editor messages visible
    if (BM.bar) BM.bar.style.display = 'none';         // the editor owns the screen while it is up
    hideCropPicker(); hideCardPicker();
    if (BM.crewPanel) BM.crewPanel.style.display = 'none';
    if (BM.barnPanel) BM.barnPanel.style.display = 'none';
    if (BM.fortPanel) BM.fortPanel.style.display = 'none';
    if (!E.rzBound && typeof global.addEventListener === 'function') { global.addEventListener('resize', onEditResize); E.rzBound = true; }
    startEditLoop(E);
    refreshEditUI();
    BM.ctx.showBanner('BASE EDITOR -- drag a piece to move it, pinch to zoom', 1.8);
    return true;
  }
  function exitEdit() {
    var E = BM.edit; if (!E) return false;
    E.on = false; E.drag = null; E.pan = null; E.pinch = null; E.ghost = null; E.ptr = {}; E.np = 0;
    if (E.raf && typeof cancelAnimationFrame === 'function') { try { cancelAnimationFrame(E.raf); } catch (_) {} }
    E.raf = 0;
    if (E.cv) E.cv.style.display = 'none';
    if (E.top) E.top.style.display = 'none';
    if (E.pal) E.pal.style.display = 'none';
    liftBanner(false);                                 // AK-ISOFIX: hand the banner back to the world
    if (BM.active && BM.bar) BM.bar.style.display = 'flex';
    bump(); refreshBar();
    return true;
  }
  function toggleEdit() { return editOn() ? exitEdit() : enterEdit(); }

  /* ====================================================================== *
   * REGISTER
   * ====================================================================== */
  global.AK_SYSTEMS.register({
    id: 'buildmode',
    init: function (ctx) {
      BM.ctx = ctx;
      try { BM.reduce = (typeof matchMedia !== 'undefined') && matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (_r) {}
      try { installCollisionWrap(); } catch (_e) {}
      try { mountButton(); } catch (_e2) {}
    },
    onTick: function (dt, ctx) {
      BM.clock += dt;
      try { reconcileJobs(); } catch (_e) {}      // finish elapsed build jobs -> free builders
      try { tendCycle(dt, ctx); } catch (_e2) {}   // builders on 'tend' auto-work the gardens
    },
    onDrawWorld: function (ctx) {
      var g = ctx.world.g, p = prof(); if (!g) return;
      var builds = (p && p.builds) || [], zid = ctx.zoneId, W = ctx.world.W, H = ctx.world.H;
      if (builds.length) {
        g.save();
        for (var i = 0; i < builds.length; i++) {
          var b = builds[i]; if (b.zone !== zid) continue;
          var X = ctx.world.wx(b.x), Y = ctx.world.wy(b.y);
          if (X < -60 || X > W + 60 || Y < -60 || Y > H + 60) continue;
          drawStruct(g, X, Y, b);
        }
        g.restore();
      }
      if (BM.active) { try { drawOverlay(ctx, g); } catch (_e) {} }
    }
  });

  // public API (host buttons, the Foreman/crew.js, + the verification harness)
  global.AK_BUILDMODE = {
    open: open, close: close, toggle: toggle,
    isActive: function () { return BM.active; },
    // AK-BM-DPAD 2026-07-09: canonical "am I on?" read for the HOST -- index.html's floating
    // stick + tap-to-move yield to build mode through this (the dpad was eating placement taps).
    isOn: function () { return !!BM.active; },
    STRUCT: STRUCT, CROPS: CROPS, mountButton: mountButton,
    // builders (design sec 5)
    builderCap: builderCap, builderSpeed: builderSpeed,
    builderState: function () { return builderState(freshProfile()); },
    builders: function () { return buildersList(freshProfile()); },
    assignBuilder: assignBuilder, unassignBuilder: unassignBuilder,
    // build jobs + gem-skip (sec 7.3)
    place: function (key, x, y) { return BM.ctx ? place(BM.ctx, key, x, y) : false; },
    gemSkipCost: gemSkipCost, skipBuildJob: skipBuildJob, baseBuildMs: baseBuildMs,
    // gardens (design sec 6) + AK-FARM (Sunflower model: seeds/crops items + weather)
    plantGarden: function (idx, crop) { return BM.ctx ? plantGarden(BM.ctx, idx, crop) : { ok: false }; },
    harvestGarden: function (idx, card) { return BM.ctx ? harvestGarden(BM.ctx, idx, card) : { ok: false }; },
    gardenStage: gardenStage, gardenRipe: gardenRipe, gardenRemainMs: gardenRemainMs, effGrow: effGrow,
    weather: function () { return curWeather(); },
    seedCount: function (key) { return seedCountOf(freshProfile(), key); },
    cropCount: function (key) { return cropCountOf(freshProfile(), key); },
    buySeed: function (key, n, pay) { var e = akEcon(); return (e && e.buySeed) ? e.buySeed(key, n, pay) : { ok: false, error: 'NO_ECON' }; },
    sellCrop: function (key, n) { var e = akEcon(); var r = (e && e.sellCrop) ? e.sellCrop(key, n) : { ok: false, error: 'NO_ECON' }; bump(); return r; },
    useCrop: function (key, n) { var e = akEcon(); var r = (e && e.useCrop) ? e.useCrop(key, n) : { ok: false, error: 'NO_ECON' }; bump(); return r; },
    sellSeed: function (key, n) { var e = akEcon(); return (e && e.sellSeed) ? e.sellSeed(key, n) : { ok: false, error: 'NO_ECON' }; },
    gardenDefense: gardenDefenseStub,   // PvZ garden-defense mini-game STUB (NOT_BUILT) -- see sec 6b note
    // district signature crops (canon: each of OUR 9 districts grows one crop best)
    DISTRICT_CROP: DISTRICT_CROP, DISTRICT_NAME: DISTRICT_NAME, signatureBonusPct: SIGNATURE_BONUS,
    districtName: districtName, signatureCropFor: signatureCropFor, signatureBonus: signatureBonus,
    // FORTIFY (district raid-defense sink) -- p.fortify[zoneId], READ BY THE RAID LAYER.
    // fortifyDefense(level) is the canonical level->multiplier the raid system applies.
    fortifyMax: FORTIFY_MAX, fortifyCost: fortifyCost, fortifyDefense: fortifyDefense,
    fortifyLevel: function (zid) { return fortifyLevel(freshProfile(), zid || (BM.ctx && BM.ctx.zoneId)); },
    fortify: function (zid) { return fortifyDistrict(zid); },
    // DISTRICT DEMAND (CAPTIVATION P8): the self-feeding Fence ORDER BOARD per district.
    // districtDemand(zid) is a PURE read (the live order board + premium prices folding
    // AK_ECON.econMod). fillDemand delivers crops/mats for premium gold. recordConsumption
    // is the hook production.js (or any consumer) calls to draw down stock + reopen demand.
    DISTRICT_MAT: DISTRICT_MAT, demandPremium: DEMAND_PREMIUM,
    econMod: econModNow,                                                  // (P8) the live crop/fence world-signal read (AK_ECON.econMod, weather fallback)
    districtDemand: function (zid) { return districtDemand(zid); },       // (zid?) -> { zone,name,fenceMult,crop:{...},mat:{...},openOrders } | null
    fillDemand: function (zid, kind, n) { return fillDemand(zid, kind, n); },   // (zid,kind"crop"|"wood"|"stone"|"metal",n?) -> deliver for premium gold
    recordConsumption: recordConsumption,                                 // (zid,mat,n) -> production/fortify draw-down -> reopens demand
    // AK-ISOEDIT 2026-07-18 -- EDIT MODE (detached iso base editor). Every editor write lands
    // in the SAME p.builds[] through the SAME ctx.econ.mutateProfile path the world reads, so
    // a piece moved here stands moved in the hub AND in raid defense (buildRects -> AK_COLLISION).
    enterEdit: enterEdit, exitEdit: exitEdit, toggleEdit: toggleEdit,
    isEditing: function () { return editOn(); },
    moveBuild: function (idx, x, y, rot) { return BM.ctx ? moveBuild(BM.ctx, idx, x, y, rot) : { ok: false, error: 'NO_CTX' }; },
    editCamera: function () { var E = editState(); return { x: E.cam.x, y: E.cam.y, zoom: E.cam.zoom, rot: E.cam.rot, w: E.cam.w, h: E.cam.h }; },
    editZoom: editZoom, editRotCam: editRotCam, editCenter: function () { return editCenter(); },
    // headless seam: drives the REAL editCommit -- the exact function onEditUp calls when you
    // let go of a dragged-out ghost. Lets the verification harness exercise the drop with no DOM.
    editCommitAt: function (key, x, y, rot) {
      var E = editState();
      E.sel = key; E.rot = (rot | 0) & 3; E.ghost = { x: snap(x), y: snap(y) };
      var r = editCommit(E);
      E.sel = null; E.ghost = null;
      return r;
    },
    // the isometric projection itself -- PURE, node-requireable, round-trip testable
    iso: { project: isoProject, unproject: isoUnproject, quad: isoQuad, structH: structH,
           KX: ISO_KX, KY: ISO_KY, KH: ISO_KH, zoomMin: ZOOM_MIN, zoomMax: ZOOM_MAX, tier: editTier },
    // let an external writer (crew.js) invalidate our ver-cache after touching p.crew
    refresh: function () { bump(); refreshBar(); refreshCrewPanel(); refreshBarnPanel(); refreshFortifyPanel(); }
  };

})(typeof window !== 'undefined' ? window : globalThis);
