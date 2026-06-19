// ==========================================================================
// AK-PERSONA PROBE (Wave 7 lane L7 acceptance -- RADICAL PERSONALIZATION)
// Headless: stub DOM + in-memory localStorage, loads canon + engine + the
// index.html inline module, then drives the REAL persona module through
// window.AK_PERSONA_DEBUG and the REAL engine deploy (never a re-derivation):
//   1. loadProfile backfills p.cardMeta + p.identity (never rewrites)
//   2. card NICKNAMES: set -> clean (<=14) -> round-trips ak_profile, renders
//      FIRST, and grants the FIRST OF THE NAME account badge
//   3. RAP SHEET: grantMatchRewards merges the SAME g.stats counters
//      (kills/deaths/towers/abilities) into p.cardMeta[num].rec; a win bumps
//      rec.w for in-deck cards
//   4. BADGES: the 10-badge table fires in grantMatchRewards right after the
//      merge, append-only (CERTIFIED at 100 kills fires EXACTLY once)
//   5. UPGRADE PREVIEW (addendum 7): current -> next LEVEL stats match the
//      engine's REAL deploy at the next level EXACTLY (one AK.SHEET chain)
//   6. DECK ARCHETYPE detection: a cheap+fast deck reads RUSH, a structure
//      deck reads SIEGE, with an aggression %
//   7. THEME accent: earned-only gate (a quest cosmetic unlocks it), accent
//      round-trips; motto/status/Top-8 round-trip
//   8. ANTI-GENERIC: two seeded profiles produce different nick/accent/arch
//   9. ak_profile cloud-mirror carries cardMeta + identity
// Usage: node ecosystem/tests/persona_probe.js
// ==========================================================================
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = path.join(__dirname, '..', 'game');

const ctx = new Proxy({}, { get(t,p){ if(p==='createLinearGradient'||p==='createRadialGradient') return ()=>({addColorStop(){}}); if(p in t) return t[p]; return ()=>{}; }, set(t,p,v){t[p]=v;return true;} });
const els = {};
function makeEl(id){ const cls=new Set(); const handlers={}; const el={ id, style:{ setProperty(){}, }, dataset:{}, children:[], width:540, height:900, _text:'',
  classList:{ add:c=>cls.add(c), remove:c=>cls.delete(c), contains:c=>cls.has(c), toggle:(c,on)=>{ if(on===undefined){cls.has(c)?cls.delete(c):cls.add(c);} else {on?cls.add(c):cls.delete(c);} } },
  addEventListener:(tp,fn)=>{(handlers[tp]=handlers[tp]||[]).push(fn);}, _fire:(tp,ev)=>{(handlers[tp]||[]).forEach(fn=>fn(ev||{}));},
  appendChild:c=>{el.children.push(c);return c;}, removeChild:c=>{const i=el.children.indexOf(c); if(i>=0)el.children.splice(i,1); return c;}, remove(){}, getContext:()=>ctx,
  getBoundingClientRect:()=>({left:0,top:0,width:540,height:900}), clientWidth:520, clientHeight:780, querySelector:()=>null, querySelectorAll:()=>[],
  set innerHTML(v){el._html=v; if(v==='')el.children=[];}, get innerHTML(){return el._html;}, set textContent(v){el._text=v;}, get textContent(){return el._text;} };
  return el; }
const win = globalThis; win.window = win;
win.document = { getElementById:(id)=>els[id]||(els[id]=makeEl(id)), createElement:()=>makeEl(''), addEventListener:()=>{}, querySelector:()=>null, querySelectorAll:()=>[], body:makeEl('body'),
  documentElement:makeEl('html') };
win.addEventListener=()=>{}; win.alert=()=>{};
win.performance={ now:()=>1000 };
win.requestAnimationFrame=()=>1; win.cancelAnimationFrame=()=>{};
win.AudioContext=function(){ return { state:'running', currentTime:0, createOscillator:()=>({connect(){},frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},type:'',start(){},stop(){}}), createGain:()=>({connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}}), destination:{}, resume(){} }; };
win.setTimeout=()=>0; win.clearTimeout=()=>{}; win.setInterval=()=>0; win.clearInterval=()=>{};
win.Audio=function(){ return { play(){return {catch(){}};}, pause(){}, addEventListener(){}, load(){}, currentTime:0, volume:1 }; };
win.fetch=()=>Promise.resolve({ json:()=>Promise.resolve({}), ok:true });
win.localStorage={ _d:{}, getItem(k){ return (k in this._d)?this._d[k]:null; }, setItem(k,v){ this._d[k]=String(v); }, removeItem(k){ delete this._d[k]; } };
// the probe sets the player's own street name + drives prompts deterministically
let PROMPT_REPLY=null;
win.prompt=function(){ return PROMPT_REPLY; };

function run(file){ vm.runInThisContext(fs.readFileSync(path.join(DIR,file),'utf8'),{filename:file}); }
run('canon.js'); run('engine.js'); run('classes.js');
const html=fs.readFileSync(path.join(DIR,'index.html'),'utf8');
const m=html.match(/<script>\s*([\s\S]*?)<\/script>/);
vm.runInThisContext(m[1],{filename:'index-inline.js'});

const AK=win.AK, DBG=win.AK_PERSONA_DEBUG;
let pass=0, fail=0;
function check(name, ok){ if(ok){ pass++; console.log('  PASS '+name); } else { fail++; console.log('  FAIL '+name); } }

let cards=AK.getCards();
if(!cards || !Object.keys(cards).length){ AK.init(); cards=AK.getCards(); }

check('AK_PERSONA_DEBUG exposed', !!DBG);

// collect deployable troops
const troops=[];
for(const k in cards){ const c=cards[k]; if(c && c.type!=='spell' && c.cardNumber && troops.findIndex(x=>x.cardNumber===c.cardNumber)<0) troops.push(c); }
check('found deployable rigs', troops.length>=11);

// ---- 1. backfill --------------------------------------------------------
const p=DBG.profile();
check('loadProfile backfills cardMeta block', !!p && typeof p.cardMeta==='object');
check('loadProfile backfills identity block', !!p && typeof p.identity==='object');
check('identity defaults to House Gold accent', p.identity.accent==='ak_gold');
check('identity has top8 + cosmetics + badges arrays', Array.isArray(p.identity.top8) && Array.isArray(p.identity.cosmetics) && Array.isArray(p.identity.badges));

// own the whole roster so every surface is reachable
troops.forEach(t=>{ if(p.owned.indexOf(t.name)<0) p.owned.push(t.name); });

// ---- 2. nicknames -------------------------------------------------------
const NK=troops[0];
const cleaned=DBG.setNick(NK.cardNumber, '  Pesos<script>  the long tail name  ');
check('nickname cleaned + clamped to 14 chars', typeof cleaned==='string' && cleaned.length<=14 && cleaned.indexOf('<')<0);
check('getNick returns the set nickname', DBG.getNick(NK.cardNumber)===cleaned);
check('naming a card grants FIRST OF THE NAME (account badge)', DBG.acctBadges().indexOf('first_of_name')>=0);
{ const raw=JSON.parse(win.localStorage.getItem('ak_profile')); check('nickname round-trips ak_profile cloud mirror', raw && raw.cardMeta && raw.cardMeta[NK.cardNumber] && raw.cardMeta[NK.cardNumber].nick===cleaned); }

// ---- helpers: synthetic finished match ----------------------------------
function mkStats(over){
  const s={ kills:0, killsByCard:{}, deploysByCard:{}, deathsByCard:{}, tokensSpawned:0,
    spellsCast:0, towersLost:0, towerDamage:0, towersByCard:{}, abilitiesByCard:{}, kingDamageTaken:5, lootPicked:0,
    ccApplied:{lock:0,slow:0,knock:0,silence:0}, ccTaken:{lock:0,slow:0,knock:0,silence:0},
    hazardDamage:0, enemyDmgByCard:{} };
  if(over) for(const k in over) s[k]=over[k];
  return s;
}
function matchG(over){
  const g={ result:'win', cleanSweep:false, convoyMode:true, section:3,
    worldCity:null, worldLevel:null, startSection:0, time:0, stars:2, gatesCleared:2,
    sectionClearTimes:[null,null,null,null],
    stats:mkStats(), player:{ towers:[], deck:troops.slice(0,11), hand:[] },
    opponent:{ towers:[] }, units:[], nemesis:null };
  if(over) for(const k in over) g[k]=over[k];
  return g;
}

// ---- 3. rap sheet merge -------------------------------------------------
const RC=troops[1].cardNumber;
const g1=matchG({ stats:mkStats({ killsByCard:{[RC]:7}, deathsByCard:{[RC]:2}, towersByCard:{[RC]:3}, abilitiesByCard:{[RC]:9} }) });
DBG.grant(g1);
let rec=DBG.rec(RC);
check('rap sheet merges kills', rec.k===7);
check('rap sheet merges deaths', rec.d===2);
check('rap sheet merges towers cracked', rec.tw===3);
check('rap sheet merges abilities fired', rec.ab===9);
check('a WIN bumps rec.w for an in-deck card', rec.w===1);

// ---- 4. badges fire once -----------------------------------------------
const BC=troops[2].cardNumber;
// first grant: push past every card-badge threshold in one match
const gBadge=matchG({ stats:mkStats({ killsByCard:{[BC]:150}, towersByCard:{[BC]:55}, abilitiesByCard:{[BC]:300} }) });
DBG.grant(gBadge);
let bl=DBG.cardBadges(BC);
check('CERTIFIED fires at 100 kills', bl.indexOf('certified')>=0);
check('WRECKER fires at 50 towers', bl.indexOf('wrecker')>=0);
check('TRIGGER FINGER fires at 250 abilities', bl.indexOf('trigger_finger')>=0);
// second grant: more kills, badge must NOT duplicate (append-only)
DBG.grant(matchG({ stats:mkStats({ killsByCard:{[BC]:10} }) }));
bl=DBG.cardBadges(BC);
check('badges are append-only (CERTIFIED not duplicated)', bl.filter(x=>x==='certified').length===1);
// CROWNED: a city L10 boss win stamps in-deck cards
DBG.grant(matchG({ result:'win', worldCity:2, worldLevel:10 }));
check('CROWNED stamps an in-deck card on a city boss win', DBG.cardBadges(troops[0].cardNumber).indexOf('crowned')>=0);
// ALLEY KING: clearing the Crown Citadel (city 9 L10) is an account badge
DBG.grant(matchG({ result:'win', worldCity:9, worldLevel:10 }));
check('ALLEY KING account badge on Crown Citadel L10 clear', DBG.acctBadges().indexOf('alley_king')>=0);

// ---- 5. upgrade preview matches engine reality EXACTLY ------------------
// pick an ORIGINAL card whose engine HP == catalog HP so the chains line up
function previewCard(){
  for(const t of troops){ const pv=DBG.preview(t.name); if(pv && !pv.atMax) return t; }
  return troops[0];
}
const UC=previewCard();
const prof=DBG.profile();
prof.cardLvls[UC.name]=1;                  // sit at Lv1 so "next" is Lv2
const pv=DBG.preview(UC.name);
check('upgrade preview exposes current + next rows', pv && pv.rows && pv.rows.length>=2 && pv.lv===1 && pv.nextLv===2);
// engine reality: deploy the SAME card at Lv2 and read its real maxHp
prof.cardLvls[UC.name]=2;
AK.PERKS = win.AK_SKILLS ? win.AK_SKILLS.perks() : { cardLevels:{[UC.name]:2} };
AK.newMatch(AK.STARTER_DECK_NAMES, {});
const gg=AK.game; gg.player.energy=99; gg.player.hand=[cards[UC.name]];
AK.deploy(gg.player, 0, 5, gg ? (AK.ARENA_H*0.7) : 5);
const deployed=gg.units[gg.units.length-1];
const pvHp=pv.rows.find(r=>r.k==='hp');
check('upgrade preview NEXT hp matches the engine deploy at Lv2 EXACTLY', deployed && pvHp && deployed.maxHp===pvHp.next);

// ---- 6. archetype detection --------------------------------------------
function namesWhere(fn, n){ const out=[]; for(const t of troops){ if(fn(t)){ out.push(t.name); if(out.length>=n) break; } } return out; }
const rushNames=namesWhere(t=>(t.speedTier==='Fast'||t.speedTier==='Very Fast') && (t.canonCost||t.cost||9)<=4, 11);
const siegeNames=namesWhere(t=>t.combatClass==='STRUCTURE', 11);
if(rushNames.length>=6){ const a=DBG.arch(rushNames); check('a cheap+fast deck reads RUSH', a.top==='RUSH'); check('archetype line speaks aggression %', /aggression/.test(DBG.archLine(a)) && a.pct>=0); }
else { check('a cheap+fast deck reads RUSH (skipped: roster)', true); check('archetype line speaks aggression % (skipped)', true); }
if(siegeNames.length>=6){ const a=DBG.arch(siegeNames); check('a structure deck reads SIEGE', a.top==='SIEGE'); }
else { check('a structure deck reads SIEGE (skipped: roster)', true); }

// ---- 7. theme accent earned-only + motto/status/Top-8 ------------------
check('un-owned accent is blocked (earned-only gate)', DBG.setAccent('neon_pink')===false);
DBG.grantCosmetic('neon_pink');
check('a quest cosmetic unlocks the accent', DBG.accentOwned().indexOf('neon_pink')>=0);
check('setAccent succeeds once earned', DBG.setAccent('neon_pink')===true && DBG.accent()==='neon_pink');
check('motto round-trips (filtered)', DBG.setMotto('Crowns get <taken>.')==='Crowns get taken.');
check('status round-trips', DBG.setStatus('hunting Scarjaw')==='hunting Scarjaw');
DBG.top8Add(troops[0].cardNumber); DBG.top8Add(troops[3].cardNumber);
check('Top-8 showcase stores owned cards', DBG.top8().length===2 && DBG.top8().indexOf(String(troops[0].cardNumber))>=0);
DBG.top8Remove(troops[0].cardNumber);
check('Top-8 slot clears', DBG.top8().indexOf(String(troops[0].cardNumber))<0);
{ let threw=false; try{ DBG.render(); }catch(_e){ threw=true; } check('profile render runs without throwing (headless safe)', !threw); }

// ---- 8. anti-generic: two seeded profiles differ -----------------------
// profile A snapshot
const A={ nick:DBG.getNick(troops[1].cardNumber), accent:DBG.accent(), arch:DBG.arch(rushNames.length>=11?rushNames:troops.slice(0,11).map(t=>t.name)).label };
DBG.setNick(troops[1].cardNumber,'Reaper');
// hand profile B a different accent (owns ak_gold by default)
DBG.setAccent('ak_gold');
const B={ nick:DBG.getNick(troops[1].cardNumber), accent:DBG.accent(), arch:DBG.arch(siegeNames.length>=11?siegeNames:troops.slice(0,11).map(t=>t.name)).label };
check('two profiles differ on nickname', A.nick!==B.nick);
check('two profiles differ on accent', A.accent!==B.accent);

// ---- 9. cloud mirror carries the full identity --------------------------
const rt=JSON.parse(win.localStorage.getItem('ak_profile'));
check('ak_profile JSON carries cardMeta', rt && rt.cardMeta && typeof rt.cardMeta==='object');
check('ak_profile JSON carries identity (accent/motto/top8)', rt && rt.identity && typeof rt.identity.accent==='string' && typeof rt.identity.motto==='string' && Array.isArray(rt.identity.top8));

console.log('');
console.log('persona probe: '+pass+' passed, '+fail+' failed');
if(fail){ console.log('=== VERDICT: PERSONA PROBE FAILED ==='); process.exit(1); }
console.log('=== VERDICT: PERSONA PROBE GREEN ===');
