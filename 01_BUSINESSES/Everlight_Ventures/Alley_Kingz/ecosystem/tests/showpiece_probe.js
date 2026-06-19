// AK-SHOW + AK-XPBAR + AK-FRAME probe (Lane L3, wave 7).
// Reuses the full_match_test DOM-stub scaffolding. Exercises BOTH transition
// paths -- an EARNED gate clear (~20s, forced king kill) and a TIMER advance
// (90s clock bound) -- then forfeits and checks the result-screen XP bar.
//
// Asserts:
//  - TRANSITION_DUR contract: tr.dur === 5.0 (the showpiece adds ZERO wall time)
//  - tr.show payload: earned flag, district bonus coins, towers/timeLeft,
//    earlyBonus on earned clears only, empty rideFlavor/rideTaunt slots,
//    ledgerAddLine() rows (queued line drains in; live line lands direct)
//  - g.clearBonus accrues across transitions and folds into the ONE
//    grantMatchRewards grant (District chip on the reward panel)
//  - WARNING beat: clock 'warn' class through the telegraph window, big
//    pa-count digits at T-3, tick sfx
//  - BREAK beat: exactly one sting per transition (major on earned, minor on timer)
//  - LEDGER beat: surviving-card tagline spoken (when a survivor existed)
//  - DROP beat: energy bar 'refill' class through the warm-up tail
//  - AK-XPBAR: numbers match the stored xpToNext curve exactly
//  - AK-FRAME: breathing-border CSS present in index.html AND shop/shop.css
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

let pass=0, fail=0;
function ok(cond, label){ if(cond){ pass++; } else { fail++; console.log('FAIL: '+label); } }

const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const shopCss=fs.readFileSync(path.join(DIR,'shop','shop.css'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/); const inline=m?m[1]:null;

// ---- AK-FRAME: static CSS contract (one breathing-border component everywhere)
ok(html.indexOf('.screen::after')>=0, 'AK-FRAME: .screen::after frame in index.html');
ok(html.indexOf('akFrameBreathe')>=0, 'AK-FRAME: breathe keyframes in index.html');
ok(shopCss.indexOf('body::after')>=0, 'AK-FRAME: body::after frame in shop.css');
ok(shopCss.indexOf('akFrameBreathe')>=0, 'AK-FRAME: breathe keyframes in shop.css');
ok((html.match(/AK-SHOW/g)||[]).length>=10, 'AK-SHOW markers present in index.html');
ok((html.match(/AK-XPBAR/g)||[]).length>=4, 'AK-XPBAR markers present in index.html');

run('canon.js'); run('cards_lore.js'); run('classes.js'); run('engine.js');
vm.runInThisContext(inline,{filename:'index-inline.js'});

// spies: sting/tick sfx + spoken taglines
const stings=[]; const realPlay=win.AK.playSfx;
win.AK.playSfx=function(n){ stings.push(n); return realPlay.call(win.AK,n); };
let spoke=0; const realSpeak=win.AK.speakTagline;
win.AK.speakTagline=function(c){ spoke++; return realSpeak.call(win.AK,c); };
ok((html.match(/AK-SHOW/g)||[]).length>0 && typeof realPlay==='function', 'AK-SHOW: AK.playSfx exported');

getEl('playbtn')._fire('click',{});
const g0=win.AK.game;
ok(g0 && g0.phase==='countdown', 'match boots');

// stamp a ledger line BEFORE any transition -- must queue, then drain into transition 1
win.ledgerAddLine('SALVAGE BANKED', '+12c +2 shards');

let deploys=0, killedKing=false, frame=0;
let earnedShow=null, timerShow=null, liveLineLanded=false;
let warnSeen=false, bigCountSeen=false, refillSeen=false, durOk=true, transitionsSeen=0;
let lastTr=null;

for(let i=0;i<9000 && rafCb;i++){
  const cb=rafCb; rafCb=null; _t+=16;
  try{ cb(_t); }catch(e){ console.log('THREW at frame',i,e.message,(e.stack||'').split('\n').slice(0,4).join('\n')); fail++; break; }
  frame++;
  const g=win.AK.game; if(!g) continue;
  const elapsed=(180-(g.time||0));
  // keep towers alive (except the gate king flagged for the forced clear)
  [g.player,g.opponent].forEach(s=>{ (s&&s.towers||[]).forEach(t=>{
    if(t._probeSkip) return;
    t.destroyed=false; if(t.maxHp){t.hp=t.maxHp;}
  }); });
  // deploy a card every ~1.5s so a survivor exists at the first transition
  if(g.phase==='live' && i%90===0 && g.player && g.player.energy>=3){
    for(let s=0;s<(g.player.hand?g.player.hand.length:0);s++){ if(g.player.hand[s]){ g.selected=s; getEl('board')._fire('click',{clientX:270,clientY:760}); deploys++; break; } }
  }
  // EARNED path: at ~20s force the enemy king (the Gate) down with a spell
  if(!killedKing && g.phase==='live' && elapsed>=20 && g.section===0 && !(g.transition&&g.transition.active)){
    killedKing=true;
    const king=g.opponent.towers.find(t=>t.type==='king');
    if(king){ king._probeSkip=true; king.hp=1;
      king.gateShield=0;   // QA-GATE: the Boneguard shield pulse can soak the forced kill (flake) -- the probe tests the SHOW payload, not the gate mechanic
      // cast every spell at the gate until one's tower-damage path lands the
      // kill (castSpellAt -> checkTowerDeath -> advanceSection(true) = EARNED)
      const SP=win.AK.getSpells();
      for(const k in SP){ if(king.destroyed) break; try{ win.AK.castSpellAt(k,0,king.x,king.y); }catch(_e){} }
      if(!king.destroyed) console.log('WARN: forced gate kill did not land');
    }
  }
  const tr=g.transition;
  if(tr && tr.active){
    if(tr!==lastTr){ lastTr=tr; transitionsSeen++;
      if(tr.dur!==5.0) durOk=false;
      if(tr.show && tr.show.earned && !earnedShow) earnedShow=tr.show;
      if(tr.show && tr.show.earned===false && !timerShow) timerShow=tr.show;
      // live stamp lands directly on the open ledger (after showpieceTick has run once)
    }
    if(tr.show && tr.t>1.0 && tr.show.earned===false && !liveLineLanded){
      win.ledgerAddLine('LIVE STAMP', '+1');
      liveLineLanded = tr.show.lines.some(r=>r.label==='LIVE STAMP');
    }
    if(tr.t > (tr.dur-1.3) && els['energyfill'] && els['energyfill'].classList.contains('refill')) refillSeen=true;
  }
  if(g.phaseIncoming){
    if(els['timer'] && els['timer'].classList.contains('warn')) warnSeen=true;
    if(g.phaseIncoming.count>0 && g.phaseIncoming.count<=3 && String(els['phasealert']._html).indexOf('pa-count')>=0) bigCountSeen=true;
  }
  // after the timer transition (90s bound) completes, forfeit to hit the result screen
  if(elapsed>97 && g.phase==='live' && transitionsSeen>=2 && !(tr&&tr.active)){
    g.phase='ended'; g.result='lose';
  }
}
// pump any AK-XPBAR animation frames left on the rAF chain
for(let i=0;i<300 && rafCb;i++){ const cb=rafCb; rafCb=null; _t+=16; try{ cb(_t); }catch(e){ fail++; console.log('XP anim threw:',e.message); break; } }

const g=win.AK.game;

// ---- transition contract
ok(durOk && transitionsSeen>=2, 'TRANSITION_DUR stays 5.0 across '+transitionsSeen+' transitions (zero added wall time)');
ok(!!earnedShow, 'earned (gate-clear) transition carried a show payload');
ok(!!timerShow, 'timer (clock-bound) transition carried a show payload');
if(earnedShow){
  ok(earnedShow.earned===true, 'earned payload flagged earned');
  ok(earnedShow.earlyBonus>0, 'earned clear pays CLEARED EARLY +X ('+earnedShow.earlyBonus+')');
  ok(earnedShow.timeLeft>0, 'earned clear banks time remaining ('+earnedShow.timeLeft+'s)');
  ok(earnedShow.scrap>0, 'earned clear drips scrap per standing tower');
  ok(earnedShow.coins>=4*earnedShow.towers, 'district bonus pays per tower standing');
  ok(typeof earnedShow.rideFlavor==='string' && earnedShow.rideFlavor.length>0, 'AK-STORY (L8): RIDE flavor slot filled with the district hook line ('+JSON.stringify(earnedShow.rideFlavor)+')');
  ok(earnedShow.rideTaunt==='', 'RIDE taunt slot still empty (no nemesis fielded; L6 fills it when one is)');
  ok(Array.isArray(earnedShow.lines) && earnedShow.lines.some(r=>r.label==='SALVAGE BANKED'), 'queued ledgerAddLine drained into the first ledger');
  ok(typeof earnedShow.survivor==='string', 'a surviving card got the mic ('+earnedShow.survivor+')');
}
if(timerShow){
  ok(timerShow.earned===false, 'timer payload flagged NOT earned');
  ok(timerShow.earlyBonus===0 && timerShow.scrap===0, 'timer move pays no early bonus / scrap');
  ok(timerShow.coins===4*timerShow.towers, 'timer bonus = towers only (no time banked)');
}
ok(liveLineLanded, 'ledgerAddLine lands DIRECT on a live transition ledger');

// ---- beats observed
ok(stings.filter(s=>s==='sting_major').length>=1, 'BREAK: major sting on the earned transition');
ok(stings.filter(s=>s==='sting_minor').length>=1, 'BREAK: minor sting on the timer transition');
ok(stings.filter(s=>s==='tick').length>=1, 'WARNING: 3-2-1 countdown ticks fired');
ok(warnSeen, 'WARNING: clock wears the warn flash through the telegraph');
ok(bigCountSeen, 'WARNING: big pa-count digits at T-3');
ok(refillSeen, 'DROP: energy bar refill flare through the warm-up tail');
ok(!earnedShow || !earnedShow.survivor || spoke>=1, 'LEDGER: surviving card tagline spoken (AK-SPEAK)');

// ---- clear bonus folds into the ONE grant
ok(g && g._rewarded===true, 'grantMatchRewards ran once');
ok(g && g.clearBonus && g.clearBonus.coins===(earnedShow?earnedShow.coins:0)+(timerShow?timerShow.coins:0),
   'clearBonus accrued exactly the two ledgers ('+(g&&g.clearBonus&&g.clearBonus.coins)+'c)');
// District chip on the reward panel names the fold
const rows=(els['rewardpanel'].children||[]).find(c=>c&&c.children&&c.children.some(r=>r.children&&r.children[0]&&r.children[0]._text==='District'));
const distRow=rows&&rows.children.find(r=>r.children&&r.children[0]&&r.children[0]._text==='District');
ok(!!distRow && distRow._text==='+'+(g&&g.clearBonus&&g.clearBonus.coins), 'reward panel District chip = +'+(g&&g.clearBonus&&g.clearBonus.coins));

// ---- AK-XPBAR: numbers match the stored curve exactly (lose: 15 + 10/gate)
const expXp = 15 + 10*(g?g.gatesCleared||0:0);
function need(lv){ return 80+40*(lv-1); }
let lv=1, xp=expXp; while(xp>=need(lv)){ xp-=need(lv); lv++; }
ok(els['xp-num']._text===(xp+' / '+need(lv)+' XP'), 'XP bar numbers match the curve ('+els['xp-num']._text+' vs '+xp+' / '+need(lv)+' XP)');
ok(els['xp-lv']._text==='LV '+lv, 'XP bar level readout ('+els['xp-lv']._text+')');
ok(String(els['xp-fill'].style.width||'')===Math.round((xp/need(lv))*100)+'%', 'XP fill width matches ('+els['xp-fill'].style.width+')');
ok(!els['xpbar'].classList.contains('hidden'), 'XP bar visible on the result screen');

console.log('\nSHOWPIECE PROBE: '+pass+' pass / '+fail+' fail');
process.exit(fail?1:0);
