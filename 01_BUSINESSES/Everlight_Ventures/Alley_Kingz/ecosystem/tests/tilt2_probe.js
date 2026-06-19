// AK-TILT2 tap-accuracy probe (Wave 8 / A7, path B2).
// THE PASS/FAIL GATE: deploy taps must land EXACTLY where tapped across the WHOLE
// field, especially the top 20% (far towers) + the four corners.
//
// This loads the REAL game (canon.js + engine.js + the index.html inline) with the
// B2 in-canvas warp FORCED on (globalThis.__AK_TILT2__ = true), then proves the
// deploy-tap ROUND-TRIP through the actual shipped functions:
//
//   arena (gx,gy)  --toX/toY-->  linear backing px  --warpScreen-->  warped backing px
//   warped backing px  ==  the on-screen pixel the player taps (rect is 1:1 here)
//   canvasToArena(tap)  -->  recovered (gx,gy)   ASSERT ~= original
//
// If forward(warp) and inverse(canvasToArena B2 branch) are exact inverses, the
// recovered arena point equals the original to floating-point epsilon at every
// sampled point -- including the far/top rows where a naive ratio drifts. We test
// at IDENTITY camera AND a panned + zoomed camera (the warp is post-camera, so the
// inverse must compose with the camera step too).
//
// Run: node tests/tilt2_probe.js   (exit 0 + "TILT2 TAP PROBE: PASS" on success)

const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';

// FORCE B2 on for this probe (production never sets this global -> ships B1).
globalThis.__AK_TILT2__ = true;

// ---- minimal headless DOM (mirrors full_match_test.js). The canvas reports a
//      540x900 backing AND a 540x900 on-screen rect at origin, so a warped backing
//      pixel equals the client tap coordinate 1:1 -- exactly what a finger hits. ----
const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const els = {};
function makeEl(id){ const cls=new Set(); const handlers={}; const el={ id, style:{}, dataset:{}, children:[], width:540, height:900, _text:'', _html:'',
  classList:{ add:c=>cls.add(c), remove:c=>cls.delete(c), contains:c=>cls.has(c), toggle:(c,on)=>{ if(on===undefined){cls.has(c)?cls.delete(c):cls.add(c);} else {on?cls.add(c):cls.delete(c);} } }, _cls:cls,
  addEventListener:(tp,fn)=>{(handlers[tp]=handlers[tp]||[]).push(fn);}, _fire:(tp,ev)=>{(handlers[tp]||[]).forEach(fn=>fn(ev||{}));},
  appendChild:c=>{el.children.push(c);return c;}, removeChild:c=>{const i=el.children.indexOf(c); if(i>=0)el.children.splice(i,1); return c;}, remove(){}, getContext:()=>ctx,
  getBoundingClientRect:()=>({left:0,top:0,width:el.width||540,height:el.height||900}), clientWidth:540, clientHeight:900, querySelector:()=>null, querySelectorAll:()=>[],
  set innerHTML(v){el._html=v; if(v==='')el.children=[];}, get innerHTML(){return el._html;}, set textContent(v){el._text=v;}, get textContent(){return el._text;} };
  return el; }
function getEl(id){ return els[id] || (els[id]=makeEl(id)); }
const win = globalThis; win.window=win;
win.document={ getElementById:getEl, createElement:()=>makeEl(''), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:makeEl('body') };
win.addEventListener=()=>{}; win.alert=()=>{};
let _t=1000; win.performance={ now:()=>_t };
let rafCb=null; win.requestAnimationFrame=(cb)=>{ rafCb=cb; return 1; }; win.cancelAnimationFrame=()=>{ rafCb=null; };
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=(fn)=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }

const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/); const inline=m?m[1]:null;

run('canon.js'); run('engine.js');
vm.runInThisContext(inline,{filename:'index-inline.js'});
// boot a match so AK.game + camera exist (drives toX/toY through the real camera).
try{ getEl('playbtn')._fire('click',{}); }catch(_e){}
for(let i=0;i<3 && rafCb;i++){ const cb=rafCb; rafCb=null; _t+=16; try{ cb(_t); }catch(_e){} }

const AK = win.AK;
const T = AK && AK.__tilt2;
const ARENA_W = AK.ARENA_W, ARENA_H = AK.ARENA_H;

let fail = 0;
function check(cond, msg){ if(!cond){ fail++; console.log('  FAIL:', msg); } }

console.log('ARENA', ARENA_W+'x'+ARENA_H, '| B2 active (TILT2_ON):', T && T.on());
check(!!T, 'AK.__tilt2 hook missing');
check(T && T.on()===true, 'TILT2_ON should be TRUE under __AK_TILT2__ (got '+(T&&T.on())+')');

// Round-trip a tap: arena -> draw pixel (toX/toY then warp) -> canvasToArena -> arena.
// The warped backing px IS the client tap coord (rect is 540x900 @ origin, 1:1).
const TOL = 1e-6;  // tiles; an exact inverse round-trips to float epsilon
function roundTrip(gx, gy){
  const X = T.toX(gx), Y = T.toY(gy);   // linear backing px (through the live camera)
  const w = T.warp(X, Y);               // warped backing px == on-screen tap pixel
  const got = T.c2a(w.x, w.y);          // the deploy point the game computes for that tap
  return { dx: Math.abs(got.gx - gx), dy: Math.abs(got.gy - gy), got, X, Y, w };
}

function sweep(label, setCam){
  setCam();
  const c = (AK.game && AK.game.camera) || {offX:0,offY:0,zoom:1};
  // sample grid: corners + top edge (far towers, the top 20%) + interior + near edge
  const xs = [0, ARENA_W*0.5, ARENA_W];
  const ys = [0, ARENA_H*0.05, ARENA_H*0.1, ARENA_H*0.2, ARENA_H*0.5, ARENA_H*0.8, ARENA_H];
  let maxErr = 0, top20Max = 0, n = 0;
  for(const gx of xs) for(const gy of ys){
    const r = roundTrip(gx, gy);
    const e = Math.max(r.dx, r.dy);
    maxErr = Math.max(maxErr, e); n++;
    if(gy <= ARENA_H*0.2) top20Max = Math.max(top20Max, e);
    check(e < TOL, label+' tap drift @ arena('+gx.toFixed(1)+','+gy.toFixed(1)+') = '+e.toExponential(2)+' tiles');
  }
  // explicit four-corners assertion (the brief calls these out)
  [[0,0],[ARENA_W,0],[0,ARENA_H],[ARENA_W,ARENA_H]].forEach(([gx,gy])=>{
    const r = roundTrip(gx,gy); check(Math.max(r.dx,r.dy) < TOL, label+' CORNER ('+gx+','+gy+') drift');
  });
  console.log('  '+label+' cam(offX='+c.offX+',offY='+c.offY+',zoom='+c.zoom+'): '+n+' pts, maxErr='+maxErr.toExponential(2)+' tiles, top20%Max='+top20Max.toExponential(2)+' tiles');
}

sweep('identity', ()=>{ if(AK.game) AK.game.camera = {offX:0,offY:0,zoom:1}; });
sweep('panned',   ()=>{ if(AK.game) AK.game.camera = {offX:0,offY:6.5,zoom:1}; });   // mid section-pan
sweep('zoomed',   ()=>{ if(AK.game) AK.game.camera = {offX:1.2,offY:3.0,zoom:1.15}; });

// Sanity: the warp must actually DO something (far end shrinks) and stay identity at
// the near/bottom edge -- otherwise a no-op warp would "pass" the round-trip trivially.
const near = T.warp(270, 900), far = T.warp(270, 60);
check(Math.abs(near.scale - 1) < 1e-9, 'warp must be identity at the bottom edge (scale '+near.scale+')');
check(far.scale < 0.95, 'warp must shrink the far/top row (scale '+far.scale.toFixed(3)+' should be <0.95)');
check(far.y > 60, 'far/top row must recede DOWN toward the vanishing line (y '+far.y.toFixed(1)+' should be >60)');
console.log('  warp profile: near.scale='+near.scale.toFixed(4)+' far.scale='+far.scale.toFixed(4)+' far.y='+far.y.toFixed(1));

if(fail===0){ console.log('\n=== TILT2 TAP PROBE: PASS (deploy taps land exactly across the whole field, incl. top 20% + corners) ==='); process.exit(0); }
else { console.log('\n=== TILT2 TAP PROBE: FAIL ('+fail+' assertion(s)) ==='); process.exit(1); }
