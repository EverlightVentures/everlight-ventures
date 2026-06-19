// ==========================================================================
// AK-QUEST PROBE (Wave 7 lane L5 acceptance)
// Headless: stub DOM + in-memory localStorage, loads canon + engine + the
// index.html inline module, then drives the REAL quest evaluation through
// window.AK_QUEST_DEBUG (never a re-derivation):
//   1. a scripted Lot win (cost<=4 deck, zero spells) completes STRAY'S OATH
//      and NO HELP COMING and pays through the existing verbs
//   2. rewards land exactly once (done-flag idempotency on a second win)
//   3. the daily roll is deterministic per date (same items on re-roll AND
//      on a fresh account same-day)
//   4. w.quests round-trips the ak_world cloud-mirror JSON
// Usage: node ecosystem/tests/quest_probe.js
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
// in-memory localStorage: persistence + cloud-mirror shape checks need it
win.localStorage={ _d:{}, getItem(k){ return (k in this._d)?this._d[k]:null; }, setItem(k,v){ this._d[k]=String(v); }, removeItem(k){ delete this._d[k]; } };

function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }
run('canon.js'); run('engine.js');
const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/);
vm.runInThisContext(m[1],{filename:'index-inline.js'});

const AK=win.AK, DBG=win.AK_QUEST_DEBUG;
let pass=0, fail=0;
function check(name, ok){ if(ok){ pass++; console.log('  PASS '+name); } else { fail++; console.log('  FAIL '+name); } }

check('AK_QUEST_DEBUG exposed', !!DBG);
check('30 sidequests cataloged', DBG && DBG.questCount===30);

// ---- build a synthetic finished Lot match: cost<=4 troops, zero spells ----
const cards=AK.getCards();
const cheap=[];
for(const k in cards){ const c=cards[k]; if(c && c.type!=='spell' && typeof c.canonCost==='number' && c.canonCost<=4 && cheap.findIndex(x=>x.cardNumber===c.cardNumber)<0) cheap.push(c); if(cheap.length>=11) break; }
check('found 11 cost<=4 troops', cheap.length>=11);

function lotWin(){
  return {
    result:'win', cleanSweep:false, worldCity:0, worldLevel:1, startSection:0,
    time:60, stars:2, gatesCleared:2,
    stats:{ kills:0, killsByCard:{}, deploysByCard:{}, deathsByCard:{}, tokensSpawned:0,
            spellsCast:0, towersLost:1, towerDamage:0, kingDamageTaken:40, hazardDamage:0,
            ccApplied:{lock:0,slow:0,knock:0,silence:0}, ccTaken:{lock:0,slow:0,knock:0,silence:0},
            enemyDmgByCard:{} },
    player:{ deck:cheap.slice(0,11), hand:[] },
    opponent:{ towers:[] },
    units:[]
  };
}

// 1. scripted run completes STRAY'S OATH + NO HELP COMING
const sg={};
const out1=DBG.evalMatch(lotWin(), sg);
const w1=DBG.world();
check("STRAY'S OATH done", !!(w1.quests.done.strays_oath));
check('NO HELP COMING done', !!(w1.quests.done.no_help_coming));
const names1=(out1 && out1.lines||[]).map(l=>l.name);
check('completion lines name both quests', names1.indexOf("STRAY'S OATH")>=0 && names1.indexOf('NO HELP COMING')>=0);
check('coins paid through the grant (150 flat)', out1 && out1.coins>=150);

// 2. idempotency: a second identical win pays those quests ZERO again
const out2=DBG.evalMatch(lotWin(), {});
const names2=(out2 && out2.lines||[]).map(l=>l.name);
check('no double pay on re-clear', names2.indexOf("STRAY'S OATH")<0 && names2.indexOf('NO HELP COMING')<0);

// 3. daily roll deterministic per date
const d1=DBG.rollDaily(), d2=DBG.rollDaily();
check('daily holds 2 bounties', d1 && d1.items && d1.items.length===2);
check('same-day re-roll is stable', JSON.stringify(d1.items.map(i=>[i.tid,i.p]))===JSON.stringify(d2.items.map(i=>[i.tid,i.p])));
const savedWorld=win.localStorage.getItem('ak_world');
win.localStorage.removeItem('ak_world');            // fresh account, same date
const d3=DBG.rollDaily();
check('fresh account rolls identical bounties', JSON.stringify(d1.items.map(i=>[i.tid,i.p]))===JSON.stringify(d3.items.map(i=>[i.tid,i.p])));
win.localStorage.setItem('ak_world', savedWorld);   // restore the veteran world

// 4. cloud mirror round-trip: w.quests survives the ak_world JSON
const raw=win.localStorage.getItem('ak_world');
const rt=JSON.parse(raw);
check('ak_world JSON carries quests block', rt && rt.quests && typeof rt.quests.done==='object' && rt.quests.daily && typeof rt.quests.counters==='object');
check('round-trip keeps done flags', !!rt.quests.done.strays_oath && !!rt.quests.done.no_help_coming);

// 5. counters: Docks per-day wins + Strip streak behave
const dock=lotWin(); dock.worldCity=3; DBG.evalMatch(dock,{});
const dock2=lotWin(); dock2.worldCity=3; DBG.evalMatch(dock2,{});
const dock3=lotWin(); dock3.worldCity=3; DBG.evalMatch(dock3,{});
const w2=DBG.world();
check('CRATE CRACKER fires on 3 same-day Docks wins', !!w2.quests.done.crate_cracker);
const strip1=lotWin(); strip1.worldCity=7; DBG.evalMatch(strip1,{});
const stripL=lotWin(); stripL.worldCity=7; stripL.result='lose'; DBG.evalMatch(stripL,{});
const w3=DBG.world();
check('Strip streak resets on a loss', (w3.quests.counters.stripStreak|0)===0 && !w3.quests.done.double_or_nothing);
const strip2=lotWin(); strip2.worldCity=7; DBG.evalMatch(strip2,{});
const strip3=lotWin(); strip3.worldCity=7; DBG.evalMatch(strip3,{});
const w4=DBG.world();
check('DOUBLE OR NOTHING fires on back-to-back wins', !!w4.quests.done.double_or_nothing);

console.log('');
console.log('quest probe: '+pass+' passed, '+fail+' failed');
if(fail){ console.log('=== VERDICT: QUEST PROBE FAILED ==='); process.exit(1); }
console.log('=== VERDICT: QUEST PROBE GREEN ===');
