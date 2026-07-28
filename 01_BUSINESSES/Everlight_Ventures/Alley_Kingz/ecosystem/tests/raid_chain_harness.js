// ==========================================================================
// ALLEY KINGZ -- WORLD-MAP MARCH -> RAID FULL-CHAIN HARNESS (playtest fix #10/#4/#2)
// ==========================================================================
// Proves, headless (mock Canvas2D, FAITHFUL *nested* overlay, no DOM/no deps),
// the END-TO-END live chain that the operator hit as broken ("the crew MARCH
// reaches the enemy but NO enemy map loads + nothing to raid"):
//
//   worldmap.openWorld -> startMarch -> [drive frames] -> march arrives ->
//   overlay.close({raidscene}) -> onClose -> launchRaidScene ->
//   *** the REAL window.AK_RAIDSCENE.launch *** (NOT a spy) opens the scout
//   scene as a NESTED overlay -> [drive scout frames WITHOUT THROWING] ->
//   tap START RAID -> beginRaid -> ctx.battle.launch(mode:'raid') + AK_RAID_TARGET
//   -> window.AK_MODES.raid.setup/checkEnd seed the base-as-battlefield from the
//   layout (walls take HP from the scouted materials -> wall combat #2).
//
// WHY THIS HARNESS EXISTS (the bug the old darkwar harness missed): it MOCKED
// AK_RAIDSCENE.launch as a spy, so it never ran the real scout scene. The real
// scene threw every frame on `target.crew.join(...)` (worldmap hands `crew` as a
// class STRING; raidscene assumed a roster ARRAY) -- swallowed by the overlay's
// onFrame try/catch -> the scene rendered nothing past the crew line -> no START
// RAID button (#10). It also drew the layout in the wrong coordinate space
// (worldmap 0..1700 world coords vs raidscene 0..100 plot coords) -> every
// structure off-screen (#4). This harness FAILS the build if either regresses:
// the faithful overlay RECORDS onFrame/onClose/onPointer throws instead of
// swallowing them, and asserts the scout layout is in 0..100 + START is hittable.
//
// Usage: node ecosystem/tests/raid_chain_harness.js
// ==========================================================================
'use strict';
var SYS = __dirname + '/../game/systems';
global.window = global;

var pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '  (' + extra + ')' : '')); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

// ---- mock Canvas2D context (every method no-op; gradients + measureText real-ish)
function mockG() {
  var grad = { addColorStop: function () {} };
  return new Proxy({}, {
    get: function (t, p) {
      if (p === 'measureText') return function () { return { width: 12 }; };
      if (p === 'createLinearGradient' || p === 'createRadialGradient') return function () { return grad; };
      if (p in t) return t[p];
      return function () {};
    },
    set: function (t, p, v) { t[p] = v; return true; }
  });
}

// ---- profile + AK_ECON (raid loot + worldmap layout reads write/read here) ----
var PROFILE = { coins: 5000, wood: 0, stone: 0, metal: 0, scrap: {}, raid: { shieldUntil: 0, revenge: [] }, baseLayout: {} };
global.AK_ECON = {
  loadProfile: function () { return PROFILE; },
  mutateProfile: function (fn) { try { fn(PROFILE); } catch (e) {} return PROFILE; },
  addScrap: function (r, n) { PROFILE.scrap[r] = (PROFILE.scrap[r] | 0) + (n | 0); return PROFILE; },
  townHallLevel: function () { return 4; },
  MAT_CAP: 2000, MAT_SELL: { wood: 2, stone: 3, metal: 5 }
};

// ---- real card index so genTarget's pickRoster resolves real defender names ----
function makeCards() {
  var names = ['Tank Pug', 'Copper Chow', 'Granite Saint', 'Grit Bulldog', 'Balboa', 'Iron Rottweiler',
    'Stonejaw', 'Cinderblock', 'Neon Whippet', 'Turbo Jack', 'Firewall', 'Laser Beagle', '$BCARDD'];
  var m = {}; names.forEach(function (n, i) { m[n] = { name: n, cardNumber: String(1000 + i), id: String(1000 + i) }; });
  return m;
}

// ---- zones (the live 3x3 shape worldmap reads) --------------------------------
function B(id, label, col, x, y, w, h) { return { id: id, label: label, col: col, x: x, y: y, w: w, h: h }; }
function makeZones() {
  return {
    HOME_TURF: { id: 'HOME_TURF', name: 'THE LOT', gx: 1, gy: 1, locked: false,
      buildings: [B('ARENA', 'TOWN HALL', '#e8c55a', 850, 360, 210, 124)] },
    DOWNTOWN: { id: 'DOWNTOWN', name: 'DOWNTOWN', gx: 1, gy: 0, locked: false,
      buildings: [B('DROP', 'THE DROP', '#ff8fae', 560, 560, 170, 104)] }
  };
}

// ---- FAITHFUL nested overlay: supports open-from-within-onClose, RECORDS throws
// (unlike the live overlay which swallows them) so a regression FAILS the harness.
var overlays = [];            // live overlay stack
var errors = [];              // any onFrame/onClose/onPointer throw lands here
function openOverlay(spec) {
  var ov = { spec: spec, closed: false, g: mockG(), vp: { w: 390, h: 780, dpr: 1 } };
  ov.api = {
    g: ov.g, vp: ov.vp,
    close: function (res) {
      if (ov.closed) return; ov.closed = true;
      var i = overlays.indexOf(ov); if (i >= 0) overlays.splice(i, 1);
      try { spec.onClose && spec.onClose(res); }
      catch (e) { errors.push('onClose[' + spec.id + ']: ' + e.message); }
    }
  };
  overlays.push(ov);
  return ov.api;
}
function liveOverlay(id) { for (var i = overlays.length - 1; i >= 0; i--) if (overlays[i].spec.id === id) return overlays[i]; return null; }
function driveFrame(ov, dt) { if (!ov || ov.closed) return; try { ov.spec.onFrame && ov.spec.onFrame(ov.g, dt, ov.api.vp, ov.api); } catch (e) { errors.push('onFrame[' + ov.spec.id + ']: ' + e.message); } }
function sendPointer(ov, type, x, y) { if (!ov || ov.closed || !ov.spec.onPointer) return; try { ov.spec.onPointer({ type: type, clientX: x, clientY: y, pointerId: 1 }, ov.api); } catch (e) { errors.push('onPointer[' + ov.spec.id + ']: ' + e.message); } }

var battleIntents = [];
function makeCtx() {
  var cards = makeCards(), ZONES = makeZones();
  return {
    ZONES: ZONES, zoneId: 'HOME_TURF', activeZone: ZONES.HOME_TURF,
    me: { x: 850, y: 650, r: 22 }, cam: { x: 0, y: 0 },
    cards: function () { return cards; },
    showBanner: function () {},
    econ: global.AK_ECON,
    battle: { launch: function (o) { battleIntents.push(o); } },   // records (no real navigate)
    currency: { get: function () { return 0; }, grant: function () { return null; } },
    world: { WORLD_W: 1700, WORLD_H: 1300, W: 390, H: 780,
      wx: function (x) { return x; }, wy: function (y) { return y; }, distToMe: function () { return 9999; },
      addRoamer: function (s) { return s; }, removeRoamer: function () {}, roamers: function () { return []; } },
    overlay: { open: openOverlay }
  };
}

// ==========================================================================
// LOAD (real order: registry -> modes -> raidscene -> worldmap, as index.html)
// ==========================================================================
require(SYS + '/_registry.js');
require(SYS + '/modes.js');        // window.AK_MODES.raid (engine seam)
require(SYS + '/raidscene.js');    // window.AK_RAIDSCENE  (the REAL scout scene)
require(SYS + '/worldmap.js');     // window.AKWorldMap   (the war map + march)

ok('AK_RAIDSCENE.launch is the REAL fn (not a spy)', typeof AK_RAIDSCENE.launch === 'function' && AK_RAIDSCENE.launch.length >= 1);
ok('AKWorldMap + AK_MODES.raid present', !!(global.AKWorldMap && global.AK_MODES && global.AK_MODES.raid));

var ctx = makeCtx();
global.AK_CTX = ctx;                // launchRaidScene calls AK_RAIDSCENE.launch(target) (1 arg) -> ctx falls back to AK_CTX

// ==========================================================================
// (1) THE WAR MAP BUILDS -- targets delegated to raidscene -> 0..100 plot coords
// ==========================================================================
console.log('\n[1] war map builds + targets are scout-renderable (0..100 coords):');
var AK_WORLD = global.AKWorldMap;
AK_WORLD.openWorld(ctx);            // opens the world-tier overlay
var world = liveOverlay('worldmap');
ok('world-map overlay opened', !!world);
driveFrame(world, 0.05);            // first frame builds wterr if needed
var wterr = AK_WORLD._state.wterr;
ok('rival territories placed on the map', Array.isArray(wterr) && wterr.length >= 1, 'n=' + (wterr ? wterr.length : 0));
var terr = wterr[0];
var tgt = terr && terr.target;
ok('territory carries a target', !!tgt);
// the EXACT bug trigger: worldmap hands crew as a class STRING
ok('target.crew is a class STRING (the old .join crash trigger)', typeof tgt.crew === 'string', JSON.stringify(tgt.crew));
ok('target.layout is non-empty', Array.isArray(tgt.layout) && tgt.layout.length > 0, 'n=' + tgt.layout.length);
var coordsOK = tgt.layout.every(function (s) { return s.x >= 0 && s.x <= 100 && s.y >= 0 && s.y <= 100; });
ok('EVERY layout coord is in raidscene plot space 0..100 (renders on-screen, #4)', coordsOK,
  'sample x=' + tgt.layout[0].x + ' y=' + tgt.layout[0].y);
ok('layout has a CORE (Town Hall renders in the scout scene)', tgt.layout.some(function (s) { return s.type === 'CORE'; }));
ok('layout uses buildmode wall vocab (wood/stone/metal/barricade)', tgt.layout.some(function (s) { return ['WALL', 'STONE', 'METAL', 'BARRICADE'].indexOf(s.type) >= 0; }));
ok('reward is soft-currency/materials only -- no gems/$BCARDD/ALK', (function () {
  var r = tgt.reward || {}; return ['gems', 'gem', 'ALK', 'alk', 'bcardd', 'BCARDD', '$BCARDD'].every(function (k) { return !(k in r); }) && typeof r.gold === 'number';
})(), JSON.stringify(tgt.reward));

// ==========================================================================
// (2) THE MARCH ARRIVES -> the REAL scout scene OPENS as a nested overlay (#10)
// ==========================================================================
console.log('\n[2] crew march -> arrival -> REAL AK_RAIDSCENE.launch opens the scout scene:');
errors.length = 0;
AK_WORLD._startMarch(ctx, terr, world.api);
ok('march started', !!AK_WORLD._state.march);
var frames = 0;
while (frames < 100 && !world.closed) { driveFrame(world, 0.1); frames++; }
ok('world-map overlay closed on march arrival', world.closed === true, frames + ' frames');
ok('march state cleared', AK_WORLD._state.march === null);
var scout = liveOverlay('raidscene');
ok('a NEW scout-scene overlay is now open (enemy base loaded)', !!scout, scout ? 'id=' + scout.spec.id : 'NONE');
ok('no throw during march->handoff', errors.length === 0, errors.join(' | '));

// ==========================================================================
// (3) THE SCOUT SCENE RENDERS WITHOUT THROWING (the .join regression guard)
// ==========================================================================
console.log('\n[3] scout scene renders cleanly (would FAIL on the old crew.join bug):');
errors.length = 0;
for (var f = 0; f < 16; f++) driveFrame(scout, 0.05);
ok('scout scene survived 16 frames with ZERO throws', errors.length === 0, errors.join(' | '));

// ==========================================================================
// (4) TAP START RAID -> battler handoff (mode:'raid' + AK_RAID_TARGET stashed)
// ==========================================================================
console.log('\n[4] START RAID -> base-as-battlefield handoff:');
battleIntents.length = 0;
try { delete global.AK_RAID_TARGET; } catch (_) {}
// START RAID button: { x: W-14-168, y: H-58, w:168, h:42 } at vp 390x780 -> center (292,743)
sendPointer(scout, 'pointerdown', 292, 743);
ok('START RAID closed the scout scene', scout.closed === true);
ok('no throw on START tap', errors.length === 0, errors.join(' | '));
ok('battler launched with mode:"raid"', battleIntents.length === 1 && battleIntents[0].mode === 'raid', battleIntents[0] && battleIntents[0].label);
ok('full target stashed for the engine (AK_RAID_TARGET)', !!global.AK_RAID_TARGET && Array.isArray(global.AK_RAID_TARGET.layout), global.AK_RAID_TARGET && global.AK_RAID_TARGET.name);

// ==========================================================================
// (5) modes.raid SEEDS the base-as-battlefield -> WALL COMBAT (#2)
// ==========================================================================
console.log('\n[5] AK_MODES.raid seeds the base + wires wall HP into combat (#2):');
function twr(type, owner, hp) { return { type: type, owner: owner, maxHp: hp, hp: hp, destroyed: false }; }
function makeGame() {
  return { time: 180, stars: 0, phase: 'live',
    player:   { crowns: 0, towers: [twr('princess', 0, 1400), twr('princess', 0, 1400), twr('king', 0, 2400)] },
    opponent: { crowns: 0, towers: [twr('princess', 1, 1400), twr('princess', 1, 1400), twr('king', 1, 1000)] } };
}
var raidTarget = global.AK_RAID_TARGET;            // setup() consumes it
var g = makeGame();
AK_MODES.raid.setup(g);
ok('setup stored game.raid from the handed-off layout', !!(g.raid && g.raid.layout.length === raidTarget.layout.length));
ok('summed wall HP captured from the scouted materials (>0)', (g.raid.wallHp | 0) > 0, 'wallHp=' + g.raid.wallHp);
AK_MODES.raid.checkEnd(g);                          // first live frame -> lazy seed the enemy towers
var king = g.opponent.towers.filter(function (t) { return t.type === 'king'; })[0];
var walls = g.opponent.towers.filter(function (t) { return t.type !== 'king'; });
ok('CORE (king) HP seeded to coreHp', king.maxHp === g.raid.coreHp, 'core=' + king.maxHp);
ok('perimeter WALLS took HP from the scouted materials (gate the lane)', walls.every(function (w) { return (w.maxHp | 0) > 0; }), 'perWall=' + walls[0].maxHp);
var totalHp = g.raid.totalHp, coreShare = g.raid.coreHp / totalHp;
ok('coreShare > 0.5 (50% line stays core-authoritative)', coreShare > 0.5 && coreShare < 0.95, 'coreShare=' + coreShare.toFixed(2));
// break BOTH perimeter walls -> the path opens + the % climbs (wall combat lands)
var before = AK_MODES.raid.checkEnd(g) , pctBefore = g.raid.pct;
walls.forEach(function (w) { w.hp = 0; w.destroyed = true; });
AK_MODES.raid.checkEnd(g);
ok('breaking the walls advances base-destroyed % (path opens)', g.raid.pct > pctBefore, 'pct ' + (pctBefore * 100).toFixed(0) + '% -> ' + (g.raid.pct * 100).toFixed(0) + '%');
// now crack the core fully -> 3-star clean sweep WIN + loot to profile
PROFILE.coins = 0; PROFILE.wood = 0; PROFILE.metal = 0;
king.hp = 0; king.destroyed = true;
var winRes = AK_MODES.raid.checkEnd(g);
ok('core down -> WIN (3 stars + clean sweep)', !!(winRes && winRes.result === 'win' && winRes.stars === 3 && winRes.cleanSweep), JSON.stringify(winRes));
ok('raid loot banked to the profile (gold + materials, no gems)', PROFILE.coins > 0 && !('gems' in PROFILE), 'coins=' + PROFILE.coins + ' wood=' + PROFILE.wood);

// ==========================================================================
console.log('\n========================================================');
console.log('RESULT: ' + pass + ' passed, ' + fail + ' failed');
if (fail) { console.log('=== VERDICT: RAID CHAIN HARNESS FAILED ==='); process.exit(1); }
console.log('=== VERDICT: MARCH -> SCOUT SCENE -> START RAID -> BASE-AS-BATTLEFIELD -- FULL CHAIN CLEAN ===');
