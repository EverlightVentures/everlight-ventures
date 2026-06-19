// ==========================================================================
// AK-NEMESIS PROBE (Wave 7 lane L6 acceptance)
// Headless: stub DOM + in-memory localStorage, loads canon + engine + the
// index.html inline module, then drives the REAL nemesis module through
// window.AK_NEMESIS_DEBUG and the REAL engine deploy (never a re-derivation):
//   1. a scripted LOSS promotes the king-killer (t.lastHitBy) into a tier-1
//      rival with a generated breed x district x deed name+title; a second
//      loss on the same rig climbs the tier; a king-survived (timeout) loss
//      promotes the top-damage card via the g.stats fallback
//   2. fielding a rival deploys its rig buffed by the tier mult (1.35 @ tier 3)
//      on the SAME seam as AK-AICURVE -- hp/dmg both scale, name tag set
//   3. a WIN over a fielded rival DEMOTES it (tier 2 -> 1, stays); a WIN that
//      BREAKS it at tier 1 removes it, credits "Grudges Settled", and pays the
//      grudge bounty (chest +1 + 20 rival-rarity scrap) through grantMatchRewards
//      EXACTLY ONCE (a re-grant after removal pays nothing)
//   4. the opponent NAME LADDER renders a label EVERY phase (1..4), caps at the
//      named STORYLINE_CANON city boss at level 10, and a fielded rival replaces
//      the generated name for its haunted phase (one namespace); Quick Play too
//   5. w.nemesis round-trips the ak_world cloud-mirror JSON
// Usage: node ecosystem/tests/nemesis_probe.js
// ==========================================================================
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = path.join(__dirname, '..', 'game');

const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const els = {};
function makeEl(id){ const cls=new Set(); const handlers={}; const el={ id, style:{}, dataset:{}, children:[], width:540, height:900, _text:'',
  classList:{ add:c=>cls.add(c), remove:c=>cls.delete(c), contains:c=>cls.has(c), toggle:(c,on)=>{ if(on===undefined){cls.has(c)?cls.delete(c):cls.add(c);} else {on?cls.add(c):cls.delete(c);} } },
  addEventListener:(tp,fn)=>{(handlers[tp]=handlers[tp]||[]).push(fn);}, _fire:(tp,ev)=>{(handlers[tp]||[]).forEach(fn=>fn(ev||{}));},
  appendChild:c=>{el.children.push(c);return c;}, removeChild:c=>{const i=el.children.indexOf(c); if(i>=0)el.children.splice(i,1); return c;}, remove(){}, getContext:()=>ctx,
  getBoundingClientRect:()=>({left:0,top:0,width:540,height:900}), clientWidth:520, clientHeight:780, querySelector:()=>null, querySelectorAll:()=>[],
  set innerHTML(v){el._html=v; if(v==='')el.children=[];}, get innerHTML(){return el._html;}, set textContent(v){el._text=v;}, get textContent(){return el._text;} };
  return el; }
const win = globalThis; win.window = win;
win.document = { getElementById:(id)=>els[id]||(els[id]=makeEl(id)), createElement:()=>makeEl(''), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:makeEl('body') };
win.addEventListener=()=>{}; win.alert=()=>{};
win.performance={ now:()=>1000 };
win.requestAnimationFrame=()=>1; win.cancelAnimationFrame=()=>{};
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=()=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
win.localStorage={ _d:{}, getItem(k){ return (k in this._d)?this._d[k]:null; }, setItem(k,v){ this._d[k]=String(v); }, removeItem(k){ delete this._d[k]; } };

function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }
run('canon.js'); run('engine.js');
const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/);
vm.runInThisContext(m[1],{filename:'index-inline.js'});

const AK=win.AK, DBG=win.AK_NEMESIS_DEBUG;
let pass=0, fail=0;
function check(name, ok){ if(ok){ pass++; console.log('  PASS '+name); } else { fail++; console.log('  FAIL '+name); } }

let cards=AK.getCards();
if(!cards || !Object.keys(cards).length){ AK.init(); cards=AK.getCards(); }

check('AK_NEMESIS_DEBUG exposed', !!DBG);

// pick three distinct deployable (non-spell) rigs to ride as rivals
const troops=[];
for(const k in cards){ const c=cards[k]; if(c && c.type!=='spell' && c.cardNumber && troops.findIndex(x=>x.cardNumber===c.cardNumber)<0) troops.push(c); }
check('found deployable rigs', troops.length>=3);
const RIG_A=troops[0], RIG_B=troops[1], RIG_C=troops[2];

function mkStats(over){
  const s={ kills:0, killsByCard:{}, deploysByCard:{}, deathsByCard:{}, tokensSpawned:0,
    spellsCast:0, towersLost:0, towerDamage:0, kingDamageTaken:0, lootPicked:0,
    ccApplied:{lock:0,slow:0,knock:0,silence:0}, ccTaken:{lock:0,slow:0,knock:0,silence:0},
    hazardDamage:0, enemyDmgByCard:{} };
  if(over) for(const k in over) s[k]=over[k];
  return s;
}
// a synthetic finished world match (only the fields the real seams read)
function matchG(over){
  const g={ result:'lose', cleanSweep:false, convoyMode:true, section:2,
    worldCity:0, worldLevel:3, startSection:0, time:0, stars:0, gatesCleared:1,
    sectionClearTimes:[null,null,null,null],
    stats:mkStats(), player:{ towers:[], deck:troops.slice(0,11), hand:[] },
    opponent:{ towers:[] }, units:[], nemesis:null };
  if(over) for(const k in over) g[k]=over[k];
  return g;
}
function lossKingKill(city, level, killNum){
  return matchG({ result:'lose', worldCity:city, worldLevel:level,
    player:{ towers:[{type:'king', destroyed:true, lastHitBy:killNum}], deck:troops.slice(0,11), hand:[] } });
}
function rosterFor(city){
  const w=DBG.world();
  return (w.nemesis && w.nemesis.byCity && w.nemesis.byCity[city]) || [];
}

// ---- 1. PROMOTION: a loss promotes the king-killer ----------------------
DBG.record(lossKingKill(0,3,RIG_A.cardNumber));
let rA=rosterFor(0).find(r=>r.card===RIG_A.cardNumber);
check('loss promotes the king-killer into a rival', !!rA);
check('new rival starts at tier 1', rA && rA.tier===1);
check('king-kill deed recorded', rA && rA.deed==='king_kill');
check('rival has a generated street name', rA && typeof rA.name==='string' && rA.name.length>0);
check('title carries the deed + district noun (the Dirt)', rA && /of the Dirt$/.test(rA.title||''));

// climb: a second king-kill loss on the same rig bumps the tier
DBG.record(lossKingKill(0,3,RIG_A.cardNumber));
rA=rosterFor(0).find(r=>r.card===RIG_A.cardNumber);
check('repeat loss climbs the rival to tier 2', rA && rA.tier===2);

// top-damage fallback: king survives (timeout loss) -> top enemy-damage card
const tdG=matchG({ result:'lose', worldCity:1, worldLevel:2,
  player:{ towers:[{type:'king', destroyed:false, lastHitBy:null}], deck:troops.slice(0,11), hand:[] },
  stats:mkStats({ enemyDmgByCard:{ [RIG_B.cardNumber]: 999 } }) });
DBG.record(tdG);
const rB=rosterFor(1).find(r=>r.card===RIG_B.cardNumber);
check('timeout loss promotes the top-damage card', !!rB);
check('fallback deed is top_damage', rB && rB.deed==='top_damage');

// ---- 2. FIELDING: the rival rig deploys buffed (engine seam, real deploy) -
function deployRig(rig, nem){
  AK.newMatch(AK.STARTER_DECK_NAMES, nem ? {city:0, level:1, nemesis:nem} : {city:0, level:1});
  const g=AK.game;
  g.opponent.energy=99;
  g.opponent.hand=[rig];
  AK.deploy(g.opponent, 0, 9, 5);              // AI (owner 1) drop on the top half
  return g.units[g.units.length-1];
}
const uBase=deployRig(RIG_A, null);
const uBuff=deployRig(RIG_A, {card:RIG_A.cardNumber, name:'Scarjaw', tier:3});
check('plain AI deploy carries no nemesis name', uBase && !uBase.nemesisName);
check('fielded rival deploy wears its street name', uBuff && uBuff.nemesisName==='Scarjaw');
check('rival HP buffed by tier-3 mult (1.35) on the AICURVE seam',
  uBuff && uBase && uBuff.maxHp===Math.round(uBase.maxHp*1.35));
check('rival DMG buffed by tier-3 mult (1.35)',
  uBuff && uBase && Math.abs(uBuff.dmg - uBase.dmg*1.35) < 0.02);

// ---- 3. DEMOTION + GRUDGE BOUNTY (exactly once) -------------------------
// build a tier-2 rival in city 6 (two king-kill losses on RIG_C)
DBG.record(lossKingKill(6,4,RIG_C.cardNumber));
DBG.record(lossKingKill(6,4,RIG_C.cardNumber));
let rC=rosterFor(6).find(r=>r.card===RIG_C.cardNumber);
check('tier-2 rival staged in city 6', rC && rC.tier===2);

// a win over the tier-2 rival demotes it to tier 1 (stays on the block)
function winVs(card, tier){
  return matchG({ result:'win', cleanSweep:false, worldCity:6, worldLevel:4,
    stars:2, time:50, gatesCleared:2,
    nemesis:{ card:card, name:rC?rC.name:'RIVAL', title:rC?rC.title:'', tier:tier, mult:({1:1.12,2:1.22,3:1.35})[tier] } });
}
const wTier2=winVs(RIG_C.cardNumber, 2);
check('no bounty while the rival is above tier 1', DBG.bounty(wTier2)===null);
DBG.record(wTier2);
rC=rosterFor(6).find(r=>r.card===RIG_C.cardNumber);
check('win demotes tier 2 -> tier 1 (rival stays)', rC && rC.tier===1);
check('demotion taunt line surfaces on the win screen', typeof DBG.line(wTier2)==='string' && DBG.line(matchG())===null);

// a win that BREAKS the rival at tier 1: bounty pays + rival removed + settled
const wTier1=winVs(RIG_C.cardNumber, 1);
const bnty=DBG.bounty(wTier1);
check('tier-1 win exposes the grudge bounty context', bnty && typeof bnty.rarity==='string');
const settledBefore=(DBG.world().nemesis.settled|0);
const rw=DBG.grant(wTier1);                                   // the REAL grantMatchRewards
check('grant pays 20 rival-rarity scrap (grudge bounty)', rw && rw.scrap && (rw.scrap[bnty.rarity]|0)>=20);
DBG.record(wTier1);
check('breaking win removes the rival from the block', !rosterFor(6).find(r=>r.card===RIG_C.cardNumber));
check('"Grudges Settled" credit increments', (DBG.world().nemesis.settled|0)===settledBefore+1);
check('settled taunt line surfaces', typeof DBG.line(wTier1)==='string');
// exactly once: with the rival gone the bounty context can never re-fire
check('grudge bounty cannot be claimed twice', DBG.bounty(winVs(RIG_C.cardNumber,1))===null);

// ---- 4. OPPONENT NAME LADDER: a label every phase -----------------------
function ladderG(sec, city, level, nem){
  return { convoyMode:true, phase:'live', section:sec, worldCity:city, worldLevel:level, nemesis:nem||null };
}
let everyPhase=true;
for(let s=0;s<4;s++){ const lbl=DBG.ladder(ladderG(s,2,5)); if(!(typeof lbl==='string' && lbl.indexOf(' -- ')>=0)) everyPhase=false; }
check('ladder names the dog in charge EVERY phase (1..4)', everyPhase);
const bossLbl=DBG.ladder(ladderG(3,2,10));                    // city 2 (Industrial), L10 finale
check('ladder caps at the named city boss at L10', bossLbl && bossLbl.indexOf('THE IRON HANDLER')>=0 && /CITY BOSS$/.test(bossLbl));
const fieldedLbl=DBG.ladder(ladderG(1,0,3,{name:'Scarjaw', title:'Warden of the Dirt', phase:1}));
check('a fielded rival replaces the generated name for its phase',
  fieldedLbl==='SCARJAW -- WARDEN OF THE DIRT');
let qpOk=true;
for(let s=0;s<4;s++){ const lbl=DBG.ladder(ladderG(s,null,null)); if(!(typeof lbl==='string' && lbl.length>0)) qpOk=false; }
check('Quick Play runs its own short chain of command', qpOk);

// ---- 5. cloud-mirror round-trip -----------------------------------------
const raw=win.localStorage.getItem('ak_world');
const rt=JSON.parse(raw);
check('ak_world JSON carries the nemesis block', rt && rt.nemesis && typeof rt.nemesis.byCity==='object' && typeof rt.nemesis.settled==='number');
check('round-trip keeps city-1 top-damage rival', Array.isArray(rt.nemesis.byCity['1']) && rt.nemesis.byCity['1'].some(r=>r.card===RIG_B.cardNumber));

console.log('');
console.log('nemesis probe: '+pass+' passed, '+fail+' failed');
if(fail){ console.log('=== VERDICT: NEMESIS PROBE FAILED ==='); process.exit(1); }
console.log('=== VERDICT: NEMESIS PROBE GREEN ===');
