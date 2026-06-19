// AK-TUT2 probe: prove the INTERACTIVE tutorial drives the REAL engine -- welcome
// card shows, Start launches a sandbox match, the AI is silenced (aiNext=Infinity),
// energy is primed, and the guided steps auto-advance on real actions (deploy x2,
// tower damage, energy refill), then "Advance" ends the match, grants a starter
// crate, and walks into the lobby steps. Mirrors full_match_test.js scaffolding
// but adds a localStorage stub + hand children so the tutorial actually runs.
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';

const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const els = {};
function makeEl(id){ const cls=new Set(); const handlers={}; const el={ id, style:{}, dataset:{}, children:[], width:540, height:900, _text:'', _html:'',
  classList:{ add:c=>cls.add(c), remove:c=>cls.delete(c), contains:c=>cls.has(c), toggle:(c,on)=>{ if(on===undefined){cls.has(c)?cls.delete(c):cls.add(c);} else {on?cls.add(c):cls.delete(c);} } }, _cls:cls,
  addEventListener:(tp,fn)=>{(handlers[tp]=handlers[tp]||[]).push(fn);}, _fire:(tp,ev)=>{(handlers[tp]||[]).forEach(fn=>fn(ev||{}));},
  appendChild:c=>{el.children.push(c);return c;}, removeChild:c=>{const i=el.children.indexOf(c); if(i>=0)el.children.splice(i,1); return c;}, remove(){}, getContext:()=>ctx,
  getBoundingClientRect:()=>({left:10,top:(id==='boardwrap'?60:600),width:120,height:80}), clientWidth:520, clientHeight:780, querySelector:()=>null, querySelectorAll:()=>[],
  setAttribute(){}, removeAttribute(){}, setPointerCapture(){}, releasePointerCapture(){},
  set innerHTML(v){el._html=v; if(v==='')el.children=[];}, get innerHTML(){return el._html;}, set textContent(v){el._text=v;}, get textContent(){return el._text;} };
  return el; }
function getEl(id){ return els[id] || (els[id]=makeEl(id)); }
const win = globalThis; win.window=win;
win.document={ getElementById:getEl, createElement:()=>makeEl(''), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:makeEl('body'), head:makeEl('head') };
win.addEventListener=()=>{}; win.alert=(m)=>{}; win.innerWidth=400; win.innerHeight=720;
let _t=1000; win.performance={ now:()=>_t };
let rafCb=null; win.requestAnimationFrame=(cb)=>{ rafCb=cb; return 1; }; win.cancelAnimationFrame=()=>{ rafCb=null; };
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=(fn)=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
win.PointerEvent=function(){};
// localStorage stub -> this is what flips the tutorial ON (the harness has none)
const _ls={}; win.localStorage={ getItem:k=>(k in _ls?_ls[k]:null), setItem:(k,v)=>{_ls[k]=String(v);}, removeItem:k=>{delete _ls[k];} };
function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }

const FAIL=[]; function ok(c,m){ if(!c){ FAIL.push(m); console.log('  FAIL:',m);} else console.log('  ok  :',m); }

run('canon.js'); run('engine.js');
const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/); const inline=m[1];
vm.runInThisContext(inline,{filename:'index-inline.js'});

// boot fires maybeShowTutorial(); the welcome overlay should be visible (no ak_tut_done)
console.log('-- welcome card --');
const ov=getEl('tutoverlay');
ok(!ov._cls.has('hidden'), 'welcome overlay shown on fresh launch');
ok(getEl('tut-step').textContent==='WELCOME TO THE LOT', 'welcome step title set');

// press "Start my first match" -> startTutorialMatch
console.log('-- start guided match --');
getEl('tut-next')._fire('click',{});
ok(ov._cls.has('hidden'), 'welcome overlay hidden after Start');
ok(getEl('tutcoach') && !getEl('tutcoach')._cls.has('hidden'), 'coachmark shown');
ok(getEl('tc-step').textContent.indexOf('STEP 1')>=0, 'on STEP 1 (deploy)');
ok(win.AK.game && win.AK.game.phase, 'a real match is running, phase='+(win.AK.game&&win.AK.game.phase));

function pump(frames){ for(let i=0;i<frames && rafCb;i++){ const cb=rafCb; rafCb=null; _t+=16; cb(_t); } }
function sumDeploys(){ const s=win.AK.game.stats.deploysByCard; let n=0; for(const k in s) n+=s[k]|0; return n; }
function deployOne(){
  const g=win.AK.game; for(let s=0;s<(g.player.hand?g.player.hand.length:0);s++){ const c=g.player.hand[s]; if(c && g.player.energy>=c.cost){ return win.AK.deploy(g.player,s, c.type==='spell'?9:9, 24); } }
  return false;
}

// pump into 'live' and confirm the safe-board + energy prime
pump(400);
ok(win.AK.game.opponent.aiNext===Infinity, 'AI silenced (opponent.aiNext=Infinity)');
ok(win.AK.game.player.energy>=6, 'player energy primed for the first drag ('+win.AK.game.player.energy.toFixed(1)+')');

// STEP 1 -> deploy once, pump past minDwell, expect advance to STEP 2
console.log('-- step advances on real deploys --');
ok(deployOne(), 'deployed card #1');
pump(60);
ok(getEl('tc-step').textContent.indexOf('STEP 2')>=0, 'auto-advanced to STEP 2 after 1 deploy ('+getEl('tc-step').textContent+')');

// STEP 2 -> deploy a second, expect advance to STEP 3 (tower)
let tries=0; while(!deployOne() && tries++<400){ pump(20); }
pump(60);
ok(getEl('tc-step').textContent.indexOf('STEP 3')>=0, 'auto-advanced to STEP 3 after 2 deploys ('+getEl('tc-step').textContent+')');

// STEP 3 -> force tower damage (units have to reach it; just inject a stat bump like the harness does for towers)
console.log('-- tower-damage + energy beats --');
win.AK.game.stats.towerDamage += 50;     // simulate a troop biting the enemy Pack Guard
pump(60);
ok(getEl('tc-step').textContent.indexOf('STEP 4')>=0, 'auto-advanced to STEP 4 (energy) after tower damage ('+getEl('tc-step').textContent+')');

// STEP 4 -> energy bar refills to >=9
win.AK.game.player.energy = 9.5;
pump(120);
ok(getEl('tc-step').textContent.indexOf('STEP 5')>=0, 'auto-advanced to STEP 5 (clear district) after energy refill ('+getEl('tc-step').textContent+')');

// STEP 5 is a TAP step -> Advance ends the match, grants a crate, jumps to lobby crate step
console.log('-- advance ends match -> lobby steps + starter reward --');
ok(getEl('tc-go') && !getEl('tc-go')._cls.has('hidden'), 'Advance button visible on the tap step');
getEl('tc-go')._fire('click',{});
ok(getEl('stage')._cls.has('hidden'), 'match stage hidden (returned to lobby)');
ok(!getEl('startscreen')._cls.has('hidden'), 'lobby (startscreen) shown');
ok(getEl('tc-step').textContent.indexOf('STEP 6')>=0, 'on STEP 6 (first crate) in the lobby ('+getEl('tc-step').textContent+')');
const prof=JSON.parse(_ls['ak_profile']||'{}');
ok(prof.chests && (prof.chests.wood|0)>=1, 'starter wood crate granted ('+(prof.chests&&prof.chests.wood)+')');
ok((prof.coins|0)>=50, 'starter coins granted ('+prof.coins+')');

// STEP 6 -> Got it -> STEP shop, then Finish sets ak_tut_done
getEl('tc-go')._fire('click',{});
ok(getEl('tc-step').textContent.indexOf('SHOP')>=0, 'advanced to the shop step ('+getEl('tc-step').textContent+')');
getEl('tc-go')._fire('click',{});
ok(getEl('tutcoach')._cls.has('hidden'), 'coachmark hidden after Finish');
ok(_ls['ak_tut_done']==='1', 'ak_tut_done set -> never auto-shows again');

console.log('\n=== VERDICT:', FAIL.length? ('TUT2 PROBE FAILED ('+FAIL.length+')') : 'TUT2 PROBE PASSED', '===');
process.exit(FAIL.length?1:0);
