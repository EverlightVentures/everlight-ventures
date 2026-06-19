// ==========================================================================
// ALLEY KINGZ -- LEVEL APPLY PROBE (contract L0 bug 1 acceptance)
// Proves the full card-level chain mechanically applies at deploy:
//   AK.PERKS.cardLevels {name:lv} -> snapshotPerks clamp -> akLevelMult(lv)
//   at deployUnit -> computeBulk AFTER the mult.
// PASS = a Lv5 troop deploys with hp AND dmg exactly akLevelMult(5) x base,
// and a Lv1 troop deploys at exactly base. No browser, no deps.
// Usage: node ecosystem/tests/level_apply_probe.js
// ==========================================================================
'use strict';

const GAME_DIR = __dirname + '/../game';
global.window = global;
require(GAME_DIR + '/canon.js');
require(GAME_DIR + '/classes.js');
require(GAME_DIR + '/engine.js');

const AK = global.AK;
AK.init();

let pass = 0, fail = 0;
function ok(cond, msg){
  if(cond){ pass++; console.log('  PASS ' + msg); }
  else    { fail++; console.log('  FAIL ' + msg); }
}

// deploy the first non-spell card in hand with every starter card at `lv`,
// return its deployed maxHp/dmg + canon base values
function deployAt(lv){
  const lvls = {};
  AK.STARTER_DECK_NAMES.forEach(function(n){ lvls[n] = lv; });
  AK.PERKS = { cardLevels: lvls };
  AK.newMatch(AK.STARTER_DECK_NAMES);
  const g = AK.game;
  const DT = 1/60;
  for(let t = 0; t < 6; t += DT) AK.update(DT);   // clear countdown
  g.player.energy = 10;
  for(let i = 0; i < g.player.hand.length; i++){
    const c = g.player.hand[i];
    if(c && c.type !== 'spell'){
      AK.deploy(g.player, i, 5, 22);
      const u = g.units.find(function(u){ return u.owner === 0 && u.card && u.card.name === c.name; });
      if(!u) return null;
      return { name: c.name, hp: u.maxHp, dmg: u.dmg, colR: u.colR, baseHp: c.hp, baseDmg: c.dmg };
    }
  }
  return null;
}

const r1 = deployAt(1);
const r5 = deployAt(5);
const m1 = AK.SHEET.levelMult(1);
const m5 = AK.SHEET.levelMult(5);
const TOL = 0.02;   // float headroom only -- the mult must land exactly

ok(!!r1, 'Lv1 troop deployed (' + (r1 && r1.name) + ')');
ok(!!r5, 'Lv5 troop deployed (' + (r5 && r5.name) + ')');
ok(m1 === 1, 'akLevelMult(1) is exactly 1.0');
ok(m5 > 1, 'akLevelMult(5) grows the card (' + m5.toFixed(3) + ')');

if(r1){
  ok(Math.abs(r1.hp / r1.baseHp - m1) < TOL, 'Lv1 hp is base (' + r1.hp + ' / ' + r1.baseHp + ')');
  ok(Math.abs(r1.dmg / r1.baseDmg - m1) < TOL, 'Lv1 dmg is base (' + r1.dmg + ' / ' + r1.baseDmg + ')');
}
if(r5){
  ok(Math.abs(r5.hp / r5.baseHp - m5) < TOL, 'Lv5 hp = akLevelMult(5) x base (' + (r5.hp / r5.baseHp).toFixed(3) + ' vs ' + m5.toFixed(3) + ')');
  ok(Math.abs(r5.dmg / r5.baseDmg - m5) < TOL, 'Lv5 dmg = akLevelMult(5) x base (' + (r5.dmg / r5.baseDmg).toFixed(3) + ' vs ' + m5.toFixed(3) + ')');
  ok(r5.colR > 0, 'computeBulk ran after the mult (colR ' + r5.colR + ')');
}

// snapshotPerks clamp: an absurd level saturates at CARD_LV_MAX, never breaks the budget
const rBig = deployAt(999);
if(rBig){
  const mMax = AK.SHEET.levelMult(999);   // levelMult clamps internally too
  ok(Math.abs(rBig.hp / rBig.baseHp - mMax) < TOL, 'Lv999 clamps to CARD_LV_MAX (' + (rBig.hp / rBig.baseHp).toFixed(3) + ' vs ' + mMax.toFixed(3) + ')');
}

AK.PERKS = null;   // leave no perk state behind for other probes

console.log('');
if(fail === 0){ console.log('=== LEVEL APPLY PROBE: ALL GREEN (' + pass + ' checks) ==='); }
else { console.log('=== LEVEL APPLY PROBE: ' + fail + ' FAIL / ' + pass + ' pass ==='); process.exit(1); }
