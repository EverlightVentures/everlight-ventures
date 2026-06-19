// AK-ATTRS probe: 6-attribute Garage Tuning overlay. A tuned player card must
// land with hp/dmg/agility boosts at deploy, a faster attack cadence
// (atkInterval), and defense / spec-defense damage-taken cuts that split by
// the isAbility flag. AI units of the same card stay stock, and corrupt tune
// values must saturate at the engine clamps (1.25 boost / 0.80 taken).
// Headless: same scaffold as full_match_test.js (engine only, no renderer).
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';

const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const win = globalThis; win.window = win;
win.document = { getElementById:()=>null, createElement:()=>({getContext:()=>ctx,style:{}}), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:{appendChild(){}} };
win.addEventListener=()=>{}; win.performance={ now:()=>Date.now() };
win.requestAnimationFrame=()=>0; win.cancelAnimationFrame=()=>{};
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=()=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }

run('canon.js'); run('engine.js');
const AK = win.AK;
AK.init();

// pick 5 distinct non-spell non-structure cards: B = boost trio (hp/dmg/agi),
// R = ranged (aspd cadence), C = def-only, D = spdef-only, E = corrupt clamp
const cards = AK.getCards();
const pool = [];
for(const n in cards){ const c=cards[n];
  if(c.type==='spell' || c.isStructure) continue;
  pool.push(c);
}
const cardB = pool[0];
const cardR = pool.find(c=>c.weaponType!=='melee' && c!==cardB);
const rest  = pool.filter(c=>c!==cardB && c!==cardR);
const cardC = rest[0], cardD = rest[1], cardE = rest[2];
if(!cardB||!cardR||!cardC||!cardD||!cardE){ console.log('ATTRS PROBE FAIL: not enough cards'); process.exit(1); }
console.log('cards: boost='+cardB.name+' aspd='+cardR.name+' (ranged) def='+cardC.name+' spdef='+cardD.name+' corrupt='+cardE.name);

// per-card tune overlay (what computePerks would hand over), set BEFORE newMatch
AK.PERKS = { cardTune: {} };
AK.PERKS.cardTune[cardB.name] = { hp:1.25, dmg:1.25, agi:1.25 };
AK.PERKS.cardTune[cardR.name] = { aspd:1.25 };
AK.PERKS.cardTune[cardC.name] = { def:0.80 };
AK.PERKS.cardTune[cardD.name] = { spdef:0.80 };
AK.PERKS.cardTune[cardE.name] = { hp:9.0, def:0.10 };   // corrupt save -> must clamp

AK.newMatch(null, {});
const g = AK.game;
g.phase = 'live'; g.cd = 0;
g.opponent.hand = []; g.opponent.energy = 0;

function put(side, card, x, y){
  side.hand=[card]; side.energy=99;
  AK.deploy(side, 0, x, y);
  side.hand=[]; side.energy=0;
  return g.units[g.units.length-1];
}

let fails = 0;
function check(label, ok, detail){
  console.log((ok?'  ok  ':'  FAIL')+' '+label+(detail?(' -- '+detail):''));
  if(!ok) fails++;
}

// ---- 1) boost trio at deploy: hp x1.25, dmg x1.25, agility x1.25 ----
const pB = put(g.player,   cardB, 5, 24);
const aB = put(g.opponent, cardB, 5, 5);
pB.spawnTime=10; aB.spawnTime=10;   // full accel ramp for getSpeed
const hpRatio  = pB.maxHp / aB.maxHp;
const dmgRatio = pB.dmg / aB.dmg;
const spdRatio = pB.getSpeed() / aB.getSpeed();
check('hp +25% at deploy',      Math.abs(hpRatio-1.25)<0.02,  'ratio '+hpRatio.toFixed(3));
check('dmg +25% at deploy',     Math.abs(dmgRatio-1.25)<0.001,'ratio '+dmgRatio.toFixed(3));
check('agility +25% getSpeed',  Math.abs(spdRatio-1.25)<0.01, 'ratio '+spdRatio.toFixed(3));
check('AI unit stays stock',    !aB.tuneAgi && !aB.tuneAspd && !aB.tuneDef && !aB.tuneSpecDef && aB.maxHp===cardB.hp);

// ---- 2) defense / spec defense split by the isAbility flag ----
const pC = put(g.player, cardC, 8, 24);
const pD = put(g.player, cardD, 11, 24);
pC.maxHp=9e9; pC.hp=9e9; pD.maxHp=9e9; pD.hp=9e9;
let h=pC.hp; pC.takeDamage(400,0,0);      const cPhys = h-pC.hp;
h=pC.hp;     pC.takeDamage(400,0,0,true); const cSpell= h-pC.hp;
h=pD.hp;     pD.takeDamage(400,0,0);      const dPhys = h-pD.hp;
h=pD.hp;     pD.takeDamage(400,0,0,true); const dSpell= h-pD.hp;
check('def cuts physical -20%',      cPhys===320,  'took '+cPhys+'/400');
check('def ignores spell damage',    cSpell===400, 'took '+cSpell+'/400');
check('spdef ignores physical',      dPhys===400,  'took '+dPhys+'/400');
check('spdef cuts spell/ability -20%', dSpell===320, 'took '+dSpell+'/400');

// ---- 3) corrupt save saturates at the clamps ----
const pE = put(g.player, cardE, 14, 24);
const eHpRatio = pE.maxHp / cardE.hp;
pE.maxHp=9e9; pE.hp=9e9;
h=pE.hp; pE.takeDamage(400,0,0); const ePhys=h-pE.hp;
check('corrupt hp 9.0 clamps to 1.25', Math.abs(eHpRatio-1.25)<0.02, 'ratio '+eHpRatio.toFixed(3));
check('corrupt def 0.10 clamps to 0.80', ePhys===320, 'took '+ePhys+'/400');

// neutralize the stat units so the cadence lanes stay clean
[pB,aB,pC,pD,pE].forEach(u=>{ u.dmg=0; u.maxSpeed=0; u.maxHp=9e9; u.hp=9e9; });

// ---- 4) aspd: tuned R re-arms ~25% faster (max observed atkCD via atkInterval) ----
const eDum = put(g.opponent, cardB, 4, 5);  eDum.x=4;  eDum.y=20.5; eDum.maxHp=9e9; eDum.hp=9e9; eDum.dmg=0; eDum.maxSpeed=0;
const pR   = put(g.player,   cardR, 4, 24); pR.x=4;  pR.y=21.3;  pR.maxHp=9e9; pR.hp=9e9; pR.maxSpeed=0;
const pDum = put(g.player,   cardB, 15, 24); pDum.x=15; pDum.y=21.3; pDum.maxHp=9e9; pDum.hp=9e9; pDum.dmg=0; pDum.maxSpeed=0;
const aR   = put(g.opponent, cardR, 15, 5); aR.x=15; aR.y=20.5;  aR.maxHp=9e9; aR.hp=9e9; aR.maxSpeed=0;
let pMaxCD=0, aMaxCD=0;
for(let t=0; t<15; t+=0.05){
  AK.update(0.05);
  g.player.energy=0; g.opponent.energy=0;
  pR.x=4; pR.y=21.3; eDum.x=4; eDum.y=20.5;        // pin pairs (knockback/shove drift)
  aR.x=15; aR.y=20.5; pDum.x=15; pDum.y=21.3;
  if(pR.atkCD>pMaxCD) pMaxCD=pR.atkCD;
  if(aR.atkCD>aMaxCD) aMaxCD=aR.atkCD;
}
const cdRatio = (pMaxCD>0) ? (aMaxCD/pMaxCD) : 0;
check('both shooters attacked', pMaxCD>0 && aMaxCD>0, 'maxCD player '+pMaxCD.toFixed(3)+' / ai '+aMaxCD.toFixed(3));
check('aspd shortens the re-arm ~25%', cdRatio>1.15 && cdRatio<1.35, 'stock/tuned interval ratio '+cdRatio.toFixed(3));

if(fails===0) console.log('=== ATTRS PROBE PASS: 6-attribute tuning lands at deploy, speed, cadence and both damage-taken lanes ===');
else { console.log('=== ATTRS PROBE FAIL: '+fails+' check(s) ==='); process.exit(1); }
