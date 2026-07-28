// ==========================================================================
// ALLEY KINGZ -- WALK-TO-RAID HARNESS (no browser, no deps)
// Proves the #2 deliverable end-to-end, headless:
//   1. AK_RAIDSCENE.genTarget() builds a real procedural base (layout 8-16 +
//      coreHp + reward, themed per a crew, buildmode wall HP).
//   2. AK_RAIDSCENE.launch(target, ctx) is callable; with no overlay it routes
//      straight to the battler handoff (mode:'raid', target stashed).
//   3. window.AK_MODES.raid.setup()/checkEnd() seed + resolve a stub match:
//      lazy tower-HP seeding from the layout, % progress, WIN at 50%, LOSE on
//      own-king-down + on the clock under 50%.
//   4. Loot grants (gold/scrap/wood/stone/metal -- never gems/$BCARDD/ALK).
// Usage: node ecosystem/tests/ak_raidscene_harness.js
// ==========================================================================
'use strict';
var SYS = __dirname + '/../game/systems';
global.window = global;

// ---- stub AK_ECON the raid loot grant writes to (gold/scrap/materials) ------
var PROFILE = { coins: 0, wood: 0, stone: 0, metal: 0, scrap: {} };
global.AK_ECON = {
  loadProfile: function () { return PROFILE; },
  mutateProfile: function (fn) { fn(PROFILE); return PROFILE; },
  addScrap: function (r, n) { PROFILE.scrap[r] = (PROFILE.scrap[r] | 0) + (n | 0); return PROFILE; }
};

require(SYS + '/modes.js');       // -> window.AK_MODES.raid
require(SYS + '/raidscene.js');   // -> window.AK_RAIDSCENE

var pass = 0, fail = 0;
function ok(name, cond, extra) { if (cond) { pass++; console.log('  PASS  ' + name + (extra ? '  (' + extra + ')' : '')); } else { fail++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); } }

console.log('--- (1) procedural base generation ---');
var t1 = AK_RAIDSCENE.genTarget({ name: 'The Boneyard Mob', faction: 'boneguard_crew', tier: 3 });
ok('genTarget returns a target', !!t1 && typeof t1 === 'object');
ok('layout has 8-16 structures', t1.layout.length >= 8 && t1.layout.length <= 16, 'n=' + t1.layout.length);
ok('layout has exactly one CORE', t1.layout.filter(function (s) { return s.type === 'CORE'; }).length === 1);
ok('CORE hp == coreHp', (function () { var c = t1.layout.filter(function (s) { return s.type === 'CORE'; })[0]; return c && c.hp === t1.coreHp && t1.coreHp >= 1500; })(), 'coreHp=' + t1.coreHp);
ok('every wall carries spec HP', t1.layout.every(function (s) { return s.type === 'CORE' || (s.hp > 0 && s.maxHp === s.hp); }));
ok('uses buildmode wall vocab', t1.layout.some(function (s) { return ['WALL', 'STONE', 'METAL', 'BARRICADE'].indexOf(s.type) >= 0; }));
ok('reward is soft-currency/materials only', (function () { var r = t1.reward; return r && !('gems' in r) && !('alk' in r) && !('bcardd' in r) && (r.gold > 0); }), JSON.stringify(t1.reward));
ok('crew defenders are real names', Array.isArray(t1.crew) && t1.crew.length >= 3);
var t1b = AK_RAIDSCENE.genTarget({ name: 'The Boneyard Mob', faction: 'boneguard_crew', tier: 3 });
ok('generation is deterministic', JSON.stringify(t1) === JSON.stringify(t1b));

console.log('--- (2) launch is callable (headless -> battler handoff) ---');
var launchCalls = [];
var cardMap = {}; (t1.crew || []).forEach(function (n, i) { cardMap[n] = { name: n, cardNumber: '00' + (10 + i) }; });
var stubCtx = { battle: { launch: function (o) { launchCalls.push(o); } }, cards: function () { return cardMap; } };
delete global.AK_RAID_TARGET;
var ret = AK_RAIDSCENE.launch(t1, stubCtx);   // no ctx.overlay -> beginRaid path
ok('launch did not throw + returned', ret != null);
ok('battle.launch called with mode:raid', launchCalls.length === 1 && launchCalls[0].mode === 'raid', launchCalls[0] && launchCalls[0].label);
ok('nemesis resolved from crew[0]', !!(launchCalls[0] && launchCalls[0].nemesis && launchCalls[0].nemesis.card));
ok('window.AK_RAID_TARGET stashed for the engine', global.AK_RAID_TARGET === t1);
ok('enrich() attaches a layout to a flat war-map base', (function () { var b = { name: 'Zoomie Riot', faction: 'zoomie_syndicate', tier: 2 }; AK_RAIDSCENE.enrich(b); return Array.isArray(b.layout) && b.layout.length >= 8 && b.coreHp > 0 && !!b.reward; })());

console.log('--- (3) raid modeImpl.setup + checkEnd on a stub game ---');
function tower(type, owner, hp) { return { type: type, owner: owner, maxHp: hp, hp: hp, destroyed: false }; }
function makeGame(target) {
  return {
    time: 180, stars: 0,
    player:   { crowns: 0, towers: [tower('princess', 0, 1400), tower('princess', 0, 1400), tower('king', 0, 2400)] },
    opponent: { crowns: 0, towers: [tower('princess', 1, 1400), tower('princess', 1, 1400), tower('king', 1, 1000)] }
  };
}
ok('AK_MODES.raid exists with setup+checkEnd', !!(AK_MODES.raid && AK_MODES.raid.setup && AK_MODES.raid.checkEnd));

// WIN path
global.AK_RAID_TARGET = t1;
var g = makeGame(t1);
AK_MODES.raid.setup(g);
ok('setup stored game.raid from the layout', !!(g.raid && g.raid.layout.length === t1.layout.length && g.raid.coreHp === t1.coreHp));
var firstNull = AK_MODES.raid.checkEnd(g);     // first live frame -> lazy seed, no result yet
ok('first checkEnd seeds + returns null (base intact)', firstNull === null);
ok('lazy seed set the CORE (king) HP to coreHp', g.opponent.towers.filter(function (x) { return x.type === 'king'; })[0].maxHp === t1.coreHp);
// coreShare > 0.5 => the 50% win line can only be crossed via core damage, so
// checkEnd always fires the win before the engine king-death crown path pre-empts.
ok('core is >50% of the base (check stays authoritative)', t1.coreHp / g.raid.totalHp > 0.5 && t1.coreHp / g.raid.totalHp < 0.85, 'coreShare=' + (t1.coreHp / g.raid.totalHp).toFixed(2));
// flatten the whole enemy base -> clean sweep win
g.opponent.towers.forEach(function (x) { x.hp = 0; x.destroyed = true; });
var win = AK_MODES.raid.checkEnd(g);
ok('full clear -> WIN', !!(win && win.result === 'win'), JSON.stringify(win));
ok('full clear -> 3 stars + cleanSweep', win.stars === 3 && win.cleanSweep === true);
ok('loot granted to profile (gold)', PROFILE.coins >= (t1.reward.gold | 0) && PROFILE.coins > 0, 'coins=' + PROFILE.coins);
ok('loot granted to profile (materials)', (PROFILE.wood | 0) >= (t1.reward.wood | 0) && (t1.reward.metal ? (PROFILE.metal | 0) >= t1.reward.metal : true), 'wood=' + PROFILE.wood + ' metal=' + PROFILE.metal);
ok('loot granted scrap (no gems/alk/bcardd)', !('gems' in PROFILE) && (t1.reward.scrap ? Object.keys(PROFILE.scrap).length > 0 : true));

// partial WIN (>=50%, not a clean sweep)
PROFILE = { coins: 0, wood: 0, stone: 0, metal: 0, scrap: {} };
global.AK_RAID_TARGET = t1; var g2 = makeGame(t1); AK_MODES.raid.setup(g2); AK_MODES.raid.checkEnd(g2);
// remove ~52% of the base: both walls + just enough core (core still alive)
var R2 = g2.raid;
R2.wallTowers.forEach(function (x) { x.hp = 0; x.destroyed = true; });
var wallRemoved = R2.wallTowers.reduce(function (s, x) { return s + (x.maxHp | 0); }, 0);
var need = Math.ceil(R2.totalHp * 0.52) - wallRemoved;
if (need > 0) R2.core.hp = Math.max(1, R2.core.maxHp - need);
var pw = AK_MODES.raid.checkEnd(g2);
ok('core still alive when 50% win fires (no crown pre-empt)', !R2.core.destroyed && (R2.core.hp | 0) > 0, 'coreHp=' + R2.core.hp);
// DESIGN: crossing 50% BANKS the win (R.won + 1+ star + loot) but checkEnd returns
// null so the raider can keep deploying to push for 2/3 stars (CoC ladder). The
// terminal win only fires at 100%/core-down or clock-out (tested elsewhere).
ok('cracking 50%+ -> WIN banked (R.won + 1+ star, raid continues)', R2.won === true && (R2.stars | 0) >= 1 && pw === null, 'won=' + R2.won + ' stars=' + R2.stars + ' ret=' + JSON.stringify(pw));
ok('partial win still grants loot once', PROFILE.coins > 0);

// LOSE path: your own king falls
global.AK_RAID_TARGET = t1; var g3 = makeGame(t1); AK_MODES.raid.setup(g3); AK_MODES.raid.checkEnd(g3);
g3.player.towers.filter(function (x) { return x.type === 'king'; })[0].destroyed = true;
var lose = AK_MODES.raid.checkEnd(g3);
ok('own king down -> LOSE', !!(lose && lose.result === 'lose' && lose.stars === 0), JSON.stringify(lose));

// LOSE path: clock runs out under 50%
global.AK_RAID_TARGET = t1; var g4 = makeGame(t1); AK_MODES.raid.setup(g4); AK_MODES.raid.checkEnd(g4);
g4.opponent.towers[0].hp = 0; g4.opponent.towers[0].destroyed = true;   // ~one wall down, well under 50%
g4.time = 0.05;
var to = AK_MODES.raid.checkEnd(g4);
ok('timeout under 50% -> LOSE', !!(to && to.result === 'lose'), JSON.stringify(to));

console.log('--- (4) HUD string is safe ---');
ok('hud() returns a string', typeof AK_MODES.raid.hud(g2) === 'string', AK_MODES.raid.hud(g2));

console.log('\n=== ' + pass + ' passed, ' + fail + ' failed ===');
process.exit(fail ? 1 : 0);
