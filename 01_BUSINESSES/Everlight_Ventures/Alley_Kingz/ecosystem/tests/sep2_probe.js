// AK-SEP2 probe: pump 8+ melee units onto ONE target and assert no two
// attacker centers ever settle closer than 80% of the sum of their radii.
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
g.phase = 'live'; g.cd = 0;   // skip countdown
g.opponent.hand = [];         // gag the AI deployer
g.opponent.energy = 0;

// pick cards: a melee attacker + a big tank target (colR 0.75 band, hp>2400)
const cards = AK.getCards();
let melee=null, tank=null;
for(const n in cards){ const c=cards[n];
  if(c.type==='spell'||c.isStructure) continue;
  if(!melee && c.weaponType==='melee' && (c.domain||'ground')==='ground' && c.hp<=1500) melee=c;
  if(!tank && c.hp>2400 && (c.domain||'ground')==='ground') tank=c;
}
if(!melee||!tank){ console.log('PROBE FAIL: no melee/tank card found'); process.exit(1); }
console.log('attacker card:', melee.name, 'hp', melee.hp, '| target card:', tank.name, 'hp', tank.hp);

// target: enemy tank parked in the LEFT lane on the player's half
g.opponent.hand = [tank]; g.opponent.energy = 99;
AK.deploy(g.opponent, 0, 5, 5);
const tgt = g.units[g.units.length-1];
tgt.x = 5; tgt.y = 21; tgt.maxHp = 9e9; tgt.hp = 9e9; tgt.dmg = 0;  // immortal, harmless
g.opponent.hand = []; g.opponent.energy = 0;

// 9 melee attackers scattered below it (same lane band, x<9)
const N_ATK = 9, atkIds = new Set();
for(let i=0;i<N_ATK;i++){
  g.player.hand = [melee]; g.player.energy = 99;
  AK.deploy(g.player, 0, 2.5 + (i%5)*1.2, 24 + Math.floor(i/5)*1.5);
  const u = g.units[g.units.length-1];
  u.maxHp = 9e9; u.hp = 9e9; u.dmg = 0;  // immortal so the ring holds steady
  atkIds.add(u.id);
}
g.player.hand = []; g.player.energy = 0;

// pump 15s at 50ms; measure pairwise spacing over the SETTLED window (t>=8s)
let minRatio = Infinity, minPair = null, minTgtRatio = Infinity, inCombat = 0;
for(let t=0; t<15; t+=0.05){
  AK.update(0.05);
  g.player.energy = 0; g.opponent.energy = 0;  // no drift deploys
  if(t < 8) continue;
  const atks = g.units.filter(u=>u.alive && atkIds.has(u.id));
  inCombat = atks.filter(u=>u.target===tgt||u.acquireTarget===tgt).length;
  for(let i=0;i<atks.length;i++) for(let j=i+1;j<atks.length;j++){
    const a=atks[i], b=atks[j];
    const r = Math.hypot(a.x-b.x, a.y-b.y) / (a.colR + b.colR);
    if(r < minRatio){ minRatio = r; minPair = [a.id, b.id, t.toFixed(2)]; }
  }
  for(const a of atks){
    const r = Math.hypot(a.x-tgt.x, a.y-tgt.y) / (a.colR + tgt.colR);
    if(r < minTgtRatio) minTgtRatio = r;
  }
}
const rings = {};
for(const u of g.units) if(atkIds.has(u.id) && u.alive) rings[u._slotRing] = (rings[u._slotRing]||0)+1;
console.log('attackers alive:', [...g.units.filter(u=>atkIds.has(u.id)&&u.alive)].length,
            '| engaging target:', inCombat, '| ring occupancy:', JSON.stringify(rings));
console.log('min attacker-pair spacing ratio (d / (rA+rB)) over t=8..15s:', minRatio.toFixed(3), 'pair', minPair);
console.log('min attacker-vs-target ratio (lunge dips expected):', minTgtRatio.toFixed(3));
if(minRatio >= 0.80) console.log('=== SEP2 PROBE PASS: no two attacker centers closer than 80% of summed radii ===');
else { console.log('=== SEP2 PROBE FAIL: attackers overlapped below the 80% bar ==='); process.exit(1); }
