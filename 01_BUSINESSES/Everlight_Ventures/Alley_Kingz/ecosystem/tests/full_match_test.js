// Full-match harness: reuse ak_domtest scaffolding but pump the ENTIRE 180s match,
// deploy cards periodically, and pinpoint the exact frame/time where the loop throws.
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';

const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const els = {};
function makeEl(id){ const cls=new Set(); const handlers={}; const el={ id, style:{}, dataset:{}, children:[], width:540, height:900, _text:'', _html:'',
  classList:{ add:c=>cls.add(c), remove:c=>cls.delete(c), contains:c=>cls.has(c), toggle:(c,on)=>{ if(on===undefined){cls.has(c)?cls.delete(c):cls.add(c);} else {on?cls.add(c):cls.delete(c);} } }, _cls:cls,
  addEventListener:(tp,fn)=>{(handlers[tp]=handlers[tp]||[]).push(fn);}, _fire:(tp,ev)=>{(handlers[tp]||[]).forEach(fn=>fn(ev||{}));},
  appendChild:c=>{el.children.push(c);return c;}, removeChild:c=>{const i=el.children.indexOf(c); if(i>=0)el.children.splice(i,1); return c;}, remove(){}, getContext:()=>ctx,
  getBoundingClientRect:()=>({left:0,top:0,width:el.width||540,height:el.height||900}), clientWidth:520, clientHeight:780, querySelector:()=>null, querySelectorAll:()=>[],
  set innerHTML(v){el._html=v; if(v==='')el.children=[];}, get innerHTML(){return el._html;}, set textContent(v){el._text=v;}, get textContent(){return el._text;} };
  return el; }
function getEl(id){ return els[id] || (els[id]=makeEl(id)); }
const win = globalThis; win.window=win;
win.document={ getElementById:getEl, createElement:()=>makeEl(''), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:makeEl('body') };
win.addEventListener=()=>{}; win.alert=(m)=>{};
let _t=1000; win.performance={ now:()=>_t };
let rafCb=null; win.requestAnimationFrame=(cb)=>{ rafCb=cb; return 1; }; win.cancelAnimationFrame=()=>{ rafCb=null; };
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=(fn)=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }

const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/); const inline=m?m[1]:null;

let threw=null, lastSection=-1, lastStorm=null, transitions=[];
try{
  run('canon.js'); run('engine.js');
  vm.runInThisContext(inline,{filename:'index-inline.js'});
  getEl('playbtn')._fire('click',{});
  const g0=win.AK.game; console.log('match started. phase=', g0&&g0.phase, 'MATCH_TIME hint time=', g0&&g0.time);
  let frame=0, deploys=0;
  for(let i=0;i<13000 && rafCb;i++){
    const cb=rafCb; rafCb=null; _t+=16;
    try { cb(_t); }
    catch(e){ threw={ frame:i, time:win.AK.game&&win.AK.game.time, elapsed:win.AK.game&&(win.AK.game.matchTime-win.AK.game.time), section:win.AK.game&&win.AK.game.section, err:e }; break; }
    frame++;
    const g=win.AK.game; if(!g) continue;
    // keep both sides' towers alive so the match runs the FULL 180s (test late-game spawns)
    [g.player,g.opponent].forEach(s=>{ (s&&s.towers||[]).forEach(t=>{ t.destroyed=false; if(t.maxHp){t.hp=t.maxHp;} }); });
    win._peak = Math.max(win._peak||0, g.units?g.units.length:0);
    // deploy a card every ~1.5s once live + energy available
    if(g.phase==='live' && i%90===0 && g.player && g.player.energy>=3){
      for(let s=0;s<(g.player.hand?g.player.hand.length:0);s++){ if(g.player.hand[s]){ g.selected=s; getEl('board')._fire('click',{clientX:270,clientY:760}); deploys++; break; } }
    }
    // log section transitions + storms as they fire
    if(g.section!==lastSection){ transitions.push({frame:i, elapsed:Math.round((g.matchTime||180)-g.time), section:g.section}); lastSection=g.section; }
    if(g.phase==='over'){ console.log('MATCH ENDED cleanly at frame',i,'time',Math.ceil(g.time)); break; }
  }
  console.log('frames pumped:', frame, '| deploys:', deploys, '| PEAK units:', win._peak);
  console.log('section transitions:', JSON.stringify(transitions));
  const g=win.AK.game;
  if(g) console.log('final phase=',g.phase,'time=',g&&Math.ceil(g.time),'section=',g.section,'units=',g.units&&g.units.length);
}catch(e){ threw={ setup:true, err:e }; }

if(threw){
  console.log('\n!!! FROZE/THREW');
  if(threw.time!=null) console.log('  at match time:', Math.floor(threw.time/60)+':'+String(Math.ceil(threw.time%60)).padStart(2,'0'), '(', Math.ceil(threw.time),'s left ) elapsed~', threw.elapsed,'s  section', threw.section, ' frame', threw.frame);
  console.log('  error:', threw.err.message);
  console.log(threw.err.stack.split('\n').slice(0,6).join('\n'));
  console.log('\n=== VERDICT: FREEZE REPRODUCED ===');
} else {
  console.log('\n=== VERDICT: FULL MATCH RAN CLEAN (no freeze) ===');
}
