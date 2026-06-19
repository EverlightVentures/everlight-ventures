// AK-CLASS + AK-STATS probe (Wave 7 lane L2). Asserts:
//  1. census: per-class counts off the TAXONOMY 1.2 per-card table (the
//     authoritative roster -- the doc's census line sums to 115 over 106
//     cards, so the per-card table wins), sidecar === engine fallback.
//  2. the five structure archetypes roll-call + the static reclass trio
//     (planted, speed 0, canon hp byte-untouched).
//  3. behaviors: lockdown hold+field, pylon/turret-net/full-battery take-max,
//     nest 4-token cap with MOBILE tokens, ramper per-target climb, turret
//     burst window, the new class-keyed combos, grudge_match dormancy hook.
//  4. g.stats spine: deploys, kills + attribution, CC counters, tower damage,
//     king damage, towersLost, lastHitBy on towers.
// Headless: same scaffold as attrs_probe.js (engine only, no renderer).
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

let fails = 0;
function ok(cond, label){ if(cond){ console.log('  PASS '+label); } else { console.log('  FAIL '+label); fails++; } }

// ---- 1) census: engine FALLBACK first (no sidecar loaded yet) ----
run('canon.js'); run('engine.js');
const AK = win.AK;
AK.init();
const auditFallback = AK.classAudit();
// then the sidecar (classes.js) and a re-init -> sidecar path
run('classes.js');
AK.init();
const audit = AK.classAudit();
const EXPECT = { BRUISER:22, ASSASSIN:19, CASTER:21, MARKSMAN:8, SUPPORT:15, SUMMONER:9, STRUCTURE:12 };
console.log('census (sidecar):', JSON.stringify(audit.counts), 'total', audit.total);
ok(audit.total===106, 'census: 106 troops classified');
ok(Object.keys(EXPECT).every(k=>audit.counts[k]===EXPECT[k]) && !audit.counts.UNKNOWN, 'census: per-card table counts exact (B22/A19/C21/M8/SU15/SM9/ST12)');
ok(JSON.stringify(auditFallback)===JSON.stringify(audit), 'sidecar === engine fallback (classes.js and CLASS_BY_FAMILY agree on all 106)');
const sidecarCensus = win.AK_CLASSES.census();
ok(sidecarCensus.total===106 && Object.keys(EXPECT).every(k=>sidecarCensus[k]===EXPECT[k]), 'classes.js census() matches');

// ---- 2) archetype roll call + static reclass ----
const A = audit.arch;
ok(JSON.stringify(A.ramper)==='["0040","0093","0094"]',   'arch ramper = Overheat trio');
ok(JSON.stringify(A.turret)==='["0039","0105","0106"]',   'arch turret = Overclock trio');
ok(JSON.stringify(A.lockdown)==='["0042","0097","0098"]', 'arch lockdown = Grid Lock trio');
ok(JSON.stringify(A.nest)==='["0045","0048"]',            'arch nest = reclassed 0045/0048');
ok(JSON.stringify(A.pylon)==='["0046"]',                  'arch pylon = reclassed 0046');
const cards = AK.getCards();
const canonByNum = {}; (win.CANON_CARDS||[]).forEach(c=>{ canonByNum[c.cardNumber]=c; });
['Neon Dachshund','Flux Pomeranian','Pixel Pug'].forEach(n=>{
  const c=cards[n];
  ok(c && c.isStructure===true && c.speed===0 && c.speedTier==='Static', 'reclass static: '+n+' planted (isStructure, speed 0)');
  ok(c && c.hp===canonByNum[c.cardNumber].hp, 'reclass static: '+n+' canon hp byte-untouched (no rebalance)');
});

// ---- match scaffold ----
function fresh(){
  AK.newMatch(null, {});
  const g = AK.game;
  g.phase='live'; g.cd=0;
  g.opponent.hand=[]; g.opponent.energy=0;   // AI never deploys
  return g;
}
function put(g, side, name, x, y){
  const card = cards[name];
  side.hand=[card]; side.energy=99;
  AK.deploy(side, 0, x, y);
  side.hand=[]; side.energy=0;
  return g.units[g.units.length-1];
}
function tick(n, dt){ for(let i=0;i<n;i++) AK.update(dt||0.02); }

// ---- 3a) new class-keyed combos light + apply ----
{
  const g = fresh();
  const j  = put(g, g.player, 'Jagged', 4, 24);          // ASSASSIN
  const gs = put(g, g.player, 'Ghost Spaniel', 5, 24);   // ASSASSIN
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('hit_squad')>=0 && j.nsMove>=1.10 && Math.abs(j.nsDmg/1.06-1)<0.2, 'HIT SQUAD lights on 2 assassins (+move/+dmg)');
}
{
  const g = fresh();
  const b1 = put(g, g.player, 'Balboa', 4, 24);
  const b2 = put(g, g.player, 'Grit Bulldog', 5, 24);
  const b3 = put(g, g.player, 'Stonejaw', 6, 24);
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('bruiser_wall')>=0 && b1.nsShieldPct>=0.10, 'KNUCKLE UP lights on 3 bruisers (+shield pct)');
}
{
  const g = fresh();
  const c1 = put(g, g.player, 'Glitch Basenji', 4, 24);    // CASTER + silence
  const c2 = put(g, g.player, 'Static Sheba Inu', 5, 24);  // CASTER + silence
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('street_sorcery')>=0 && c1.nsCd>1.14, 'STREET SORCERY lights on 2 casters (nsCd)');
  ok(ids.indexOf('dead_air')>=0 && g.nsDeadAir && g.nsDeadAir[0]===true, 'DEAD AIR flag set on 2 silence-subtype units');
}
{
  const g = fresh();
  const m1 = put(g, g.player, 'Razor Vizsla', 4, 24);
  const m2 = put(g, g.player, 'Byte Beagle', 5, 24);
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('firing_line')>=0 && m1.nsRangeAdd>=0.5, 'FIRING LINE lights on 2 marksmen (+0.5 range)');
}
{
  const g = fresh();
  put(g, g.player, 'Grit Bulldog', 4, 24);                  // BRUISER
  const s1 = put(g, g.player, 'Holo Husky', 5, 24);         // SUPPORT
  const s2 = put(g, g.player, 'Vibe Shih Tzu', 6, 24);      // SUPPORT
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('bodyguard_detail')>=0 && s1.nsDefTaken===0.85 && s2.nsDefTaken===0.85, 'BODYGUARD DETAIL lights (supports take less)');
}
{
  const g = fresh();
  put(g, g.player, 'Nova Shepherd', 4, 24);                 // STRUCTURE
  const fox = put(g, g.player, 'Crown Foxhound', 5, 24);    // turret_break
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('wrecking_crew')>=0 && fox.nsWreck===1.15, 'WRECKING CREW lights (turret-breaker +15% vs towers)');
}
{
  const g = fresh();
  const u1 = put(g, g.player, 'Grit Bulldog', 4, 24);
  const rival = put(g, g.opponent, 'Knuckles', 14, 6);
  rival.nemesisName = 'Scarjaw';                            // L6 will set this for real
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('grudge_match')>=0 && u1.nsDmg>=1.05, 'GRUDGE MATCH lights when a nemesis-tagged rival is fielded');
}

// ---- 3b) pylon / turret_net / full_battery take-max (never stack) ----
{
  const g = fresh();
  const py = put(g, g.player, 'Flux Pomeranian', 4, 24);
  const t1 = put(g, g.player, 'Laser Beagle', 5, 24);
  const t2 = put(g, g.player, 'Nova Shepherd', 6, 24);
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('full_battery')>=0 && ids.indexOf('turret_net')<0, 'FULL BATTERY supersedes TURRET NET');
  ok(Math.abs(t1.nsAtkSpd-1.15)<1e-9 && Math.abs(t2.nsAtkSpd-1.15)<1e-9 && Math.abs(py.nsAtkSpd-1.15)<1e-9, 'structure atkSpd layer is exactly 1.15 (take max, no 1.3225 stack)');
}
{
  const g = fresh();
  const py = put(g, g.player, 'Flux Pomeranian', 4, 24);
  const t1 = put(g, g.player, 'Laser Beagle', 5, 24);      // within 3.5 tiles
  tick(3);
  const ids = g.namedSynergy.player.map(s=>s.id);
  ok(ids.indexOf('full_battery')<0 && Math.abs(t1.nsAtkSpd-1.15)<1e-9, 'AURA PYLON archetype buffs a lone neighbor turret (no combo chip)');
}

// ---- 3c) lockdown hold + slow field + CC counters ----
{
  const g = fresh();
  const ld = put(g, g.player, 'Grid Schnauzer', 9, 17);     // lockdown rig
  const e1 = put(g, g.opponent, 'Stonejaw', 9, 13);         // nearest -> HELD
  const e2 = put(g, g.opponent, 'Knuckles', 11, 13);        // field -> SLOWED
  tick(10);
  ok(e1.snareTimer>0, 'LOCKDOWN holds the nearest enemy (snare beam)');
  ok(e2.slowTimer>0 && e2.slowMag>=0.35, 'LOCKDOWN keeps the 35% slow field on the rest');
  ok(g.stats.ccApplied.lock>=1 && g.stats.ccApplied.slow>=1, 'AK-STATS: ccApplied lock+slow counted');
}

// ---- 3d) nest cap = 4 alive tokens, tokens stay MOBILE ----
{
  const g = fresh();
  const nest = put(g, g.player, 'Pixel Pug', 4, 24);
  let maxAlive=0, everAt4=false, badToken=false;
  for(let i=0;i<400;i++){
    nest.abilityCD = 0;                                     // force spawn pressure every tick
    AK.update(0.02);
    let mine=0;
    for(const o of g.units){ if(o.alive && o.isToken && o.spawnedBy===nest.id){ mine++;
      if(o.card.isStructure || !(o.maxSpeed>0)) badToken=true; } }
    maxAlive=Math.max(maxAlive,mine); if(mine===4) everAt4=true;
  }
  ok(everAt4 && maxAlive<=4, 'SPAWNER NEST caps at exactly 4 alive tokens (peak '+maxAlive+')');
  ok(!badToken, 'nest tokens are MOBILE units (clone card: no isStructure, speed > 0)');
  ok(g.stats.tokensSpawned>=4, 'AK-STATS: tokensSpawned counted ('+g.stats.tokensSpawned+')');
  ok(nest.card.isStructure && nest.maxSpeed===0, 'the nest itself stays planted');
}

// ---- 3e) ramper climbs per target, turret bursts ----
{
  const g = fresh();
  const rb = put(g, g.player, 'Laser Beagle', 9, 17);
  const tank = put(g, g.opponent, 'Stonejaw', 9, 14);       // in beam range
  tick(300, 0.02);                                          // ~6s of fire
  ok(rb._rampTgt===tank && rb._rampN>=2, 'RAMPER climbs on a held target (_rampN='+rb._rampN+')');
}
{
  const g = fresh();
  const tu = put(g, g.player, 'Nova Shepherd', 9, 17);
  put(g, g.opponent, 'Stonejaw', 9, 14);
  let burst=false;
  for(let i=0;i<300;i++){ AK.update(0.02); if(tu.dmgBuffT>0) burst=true; }
  ok(burst && tu._rampN===0, 'TURRET fires the timed burst window (no ramp path)');
}

// ---- 4) g.stats spine: deploys, kills, attribution, tower damage ----
{
  const g = fresh();
  const killer = put(g, g.player, 'Rail Terrier', 4, 17);   // ranged: projectile-path attribution
  const victim = put(g, g.opponent, 'Glitch Basenji', 4, 14);
  victim.hp = victim.maxHp = 40;                             // rig: one shot drops it (deterministic credit)
  ok(g.stats.deploysByCard['0047']===1, 'AK-STATS: deploysByCard counts the player deploy');
  tick(300, 0.02);
  ok(g.stats.kills>=1 && (g.stats.killsByCard['0047']||0)>=1, 'AK-STATS: player kill attributed to the killing card');
  ok(victim.lastHitBy && victim.lastHitBy.owner===0, 'AK-STATS: corpse carries lastHitBy (loot lane reads it)');
  // tower damage + lastHitBy on a tower
  const g2 = fresh();
  const sieger = put(g2, g2.player, 'Rail Terrier', 4, 17); // outranges, hits towers
  tick(600, 0.02);
  ok(g2.stats.towerDamage>0, 'AK-STATS: towerDamage tallies player hits on enemy towers');
  const hitT = g2.opponent.towers.find(t=>t.lastHitBy);
  ok(!!hitT && hitT.lastHitBy==='0047', 'AK-STATS: Tower.lastHitBy = attacking cardNumber');
  // king damage taken (raider teleported deep -- the deploy clamp keeps real
  // deploys on their own half, this is a rig)
  const g3 = fresh();
  const raider = put(g3, g3.opponent, 'Knuckles', 9, 14);
  g3.player.towers.forEach(t=>{ if(t.type!=='king') { t.destroyed=true; t.crownCounted=true; } });
  g3.player.towers.find(t=>t.type==='king').active=true;
  raider.x=9; raider.y=26.5;                                 // drop it at the king's porch
  tick(800, 0.02);
  ok(g3.stats.kingDamageTaken>0, 'AK-STATS: kingDamageTaken tallies hits on the player king');
  ok(g3.stats.towersLost===0, 'AK-STATS: towersLost ignores probe-rigged tower flags (crownCounted)');
}

console.log(fails===0 ? '\n=== CLASS LAYER PROBE: ALL GREEN ===' : '\n=== CLASS LAYER PROBE: '+fails+' FAIL(S) ===');
process.exit(fails===0?0:1);
