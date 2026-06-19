// AK-AIR probe: elevation language metadata. A ground ranged unit shooting a
// flyer must tag its projectiles tgtAir (renderer angles UP); a flyer shooting
// a ground unit must tag srcAir (renderer angles DOWN to the shadow point).
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
AK.newMatch(null, {});
const g = AK.game;
g.phase = 'live'; g.cd = 0;
g.opponent.hand = []; g.opponent.energy = 0;

// pick cards: a ranged GROUND unit that can target air, and a ranged AIR unit
const cards = AK.getCards();
let gShooter=null, flyer=null;
for(const n in cards){ const c=cards[n];
  if(c.type==='spell'||c.isStructure) continue;
  const dom=c.domain||'ground', tg=c.targets||'ground';
  if(!gShooter && dom==='ground' && c.weaponType!=='melee' && (tg==='both'||tg==='air')) gShooter=c;
  if(!flyer && dom==='air' && c.weaponType!=='melee') flyer=c;
}
if(!gShooter||!flyer){ console.log('AIR PROBE FAIL: missing ranged ground-vs-air or ranged flyer card'); process.exit(1); }
console.log('ground shooter:', gShooter.name, '(targets', gShooter.targets+')', '| flyer:', flyer.name, '(domain air)');

// enemy flyer parked near the player's half; player ground shooter below it
g.opponent.hand=[flyer]; g.opponent.energy=99;
AK.deploy(g.opponent, 0, 5, 5);
const fEnemy = g.units[g.units.length-1];
fEnemy.x=5; fEnemy.y=21; fEnemy.maxHp=9e9; fEnemy.hp=9e9; fEnemy.dmg=0;
g.opponent.hand=[]; g.opponent.energy=0;

g.player.hand=[gShooter]; g.player.energy=99;
AK.deploy(g.player, 0, 5, 24);
const gUnit = g.units[g.units.length-1];
gUnit.maxHp=9e9; gUnit.hp=9e9;

// player flyer that will shoot the enemy GROUND king tower side units? Use an
// enemy ground tank instead: spawn one for the flyer to shoot at.
let gTank=null;
for(const n in cards){ const c=cards[n];
  if(c.type==='spell'||c.isStructure) continue;
  if((c.domain||'ground')==='ground' && c.hp>1500){ gTank=c; break; }
}
g.opponent.hand=[gTank]; g.opponent.energy=99;
AK.deploy(g.opponent, 0, 13, 5);
const tEnemy = g.units[g.units.length-1];
tEnemy.x=13; tEnemy.y=21; tEnemy.maxHp=9e9; tEnemy.hp=9e9; tEnemy.dmg=0;
g.opponent.hand=[]; g.opponent.energy=0;

g.player.hand=[flyer]; g.player.energy=99;
AK.deploy(g.player, 0, 13, 24);
const fUnit = g.units[g.units.length-1];
fUnit.maxHp=9e9; fUnit.hp=9e9;
g.player.hand=[]; g.player.energy=0;

// pump 12s; collect projectile elevation tags by shooter card. Flat shots
// (ground-vs-ground, incl. tower fire at ground units) are LEGITIMATE; the
// bar is: every flyer-fired bolt carries srcAir, every bolt the ground
// shooter fires while locked on the flyer carries tgtAir.
let upShots=0, downShots=0, badFlyerShots=0, badGroundShots=0, total=0;
for(let t=0; t<12; t+=0.05){
  AK.update(0.05);
  g.player.energy=0; g.opponent.energy=0;
  for(const p of AK.projectiles){
    if(!p.alive || p._counted) continue;
    p._counted = true; total++;
    if(p.owner!==0) continue;
    if(p.card && p.card.name===flyer.name){           // fired BY the flyer
      if(p.srcAir) downShots++; else badFlyerShots++;
    } else if(p.card && p.card.name===gShooter.name){ // fired by the ground shooter
      // its only enemy in range is the parked flyer -> must angle UP
      if(p.tgtAir && !p.srcAir) upShots++; else badGroundShots++;
    }
  }
}
console.log('projectiles seen:', total, '| UP-shots (ground->air, tgtAir):', upShots,
            '| DOWN-shots (air->ground, srcAir):', downShots,
            '| mistagged flyer shots:', badFlyerShots, '| mistagged ground shots:', badGroundShots);
if(upShots>0 && downShots>0 && badFlyerShots===0 && badGroundShots===0)
  console.log('=== AIR PROBE PASS: flyer bolts angle DOWN (srcAir), ground-vs-air bolts angle UP (tgtAir) ===');
else { console.log('=== AIR PROBE FAIL ==='); process.exit(1); }
