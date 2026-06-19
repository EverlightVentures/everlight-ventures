# Alley Kingz -- HANDLER System Build Plan

Concrete, low-risk integration of the 6 Handlers (`game/handlers_data.js`) into
the live engine (`game/engine.js`) and renderer/HUD (`game/index.html`).

A Handler is the player's commander. It grants one always-on PASSIVE and one
tap-fired SPECIAL that spends a charge off a radial meter. Bones (a meta
currency) buy skill-tree nodes that patch the special's stats. One Handler is
equipped per match (chosen pre-match), exactly like a deck.

Design intent: REUSE existing engine primitives. Every special maps to a
mechanic the engine already runs (zone heal = `updateGoldenHour`, structures =
`new Unit` + `lifeT`, ally damage buff = `dmgBuffT`, shield = `shieldHp`, slow =
`slowTimer/slowMag`, AoE damage = the `castSpell('strike')` loop, energy =
`side.energy`). New per-unit fields are added only where no existing field fits
(`markT/markMul`, `stealthT`, `handlerDR`), each a single guarded read.

All file paths below are absolute where load-bearing; engine line numbers are
from the current `game/engine.js` (4101 lines) and `game/index.html` (8459).

---

## 0. Load order (index.html)

`handlers_data.js` is pure data and must load BEFORE `engine.js` so
`window.AK_HANDLERS` exists when `newMatch` resolves the equipped handler. Add
the script tag immediately before the existing `engine.js` include (alongside
`canon.js` / `cards_lore.js`):

```html
<script src="handlers_data.js"></script>   <!-- before engine.js -->
```

Node harness: `engine.js` guards on `typeof window` already; the resolver
(section 2) treats a missing `window.AK_HANDLERS` as "no handler" -> identity
no-op, so headless probes stay byte-true.

---

## 1. The special METER -- engine field + fill rule

### 1a. State (engine.js `newMatch`, in the `game = { ... }` literal ~line 1370)

Add one block next to `goldenHour`:

```js
// HANDLER: equipped commander + the radial special meter.
special: makeHandlerState(opts.handler),
handlerZones: [],   // active heal/armor/slow auras (Mender totem, Dealer blessing, Suppressor)
```

`makeHandlerState(handlerId)` (new helper, near `snapshotPerks`):

```js
function makeHandlerState(handlerId){
  var byId = (typeof window!=='undefined' && window.AK_HANDLERS_BY_ID) || null;
  var H = (byId && byId[handlerId]) || (byId && byId['handler_mender']) || null;
  if(!H) return null;                       // headless / no data -> meter disabled
  // unlocked Bones nodes for THIS handler come from the profile (section 7);
  // opts.handlerNodes is the resolved id-array index.html passes at startMatch.
  // Default = the FREE (bones===0) nodes only. The base special is inherent
  // (the resolver starts from H.special), so a handler whose tree is all
  // upgrades -- e.g. The Bruiser -- correctly starts with NO node applied.
  var freeNodes = H.skill_tree.filter(function(n){ return n.bones===0; }).map(function(n){ return n.id; });
  var unlocked = Array.isArray(opts.handlerNodes) ? opts.handlerNodes : freeNodes;
  var cfg = resolveHandlerCfg(H, unlocked);  // fold node mods onto base special
  return {
    id: H.id, handler: H, cfg: cfg, passive: H.passive,
    meter: 0,                                // 0..rechargeSec, fills on real dt
    rechargeSec: cfg.recharge_sec,
    charges: (cfg.charges>0 ? 1 : 0),        // start with 1 banked so the first fire is quick (Clash feel)
    maxCharges: cfg.charges,
    aiming: false,                           // true while player armed it, picking a target
    rigChoice: (cfg.rigChoices ? cfg.rigChoices[0] : null), // Rigger: selected turret
    reviveUsed: false,                       // Mender per-totem revive latch
    goldGainMul: cfg.goldGainMul || 1,       // Dealer: $BCARDD Blessing permanent mult
    elapsedGoldT: 0                          // Dealer: Small Blessing 30s accumulator
  };
}
```

### 1b. Resolver (engine.js, new pure helper -- mirrors data schema)

```js
function resolveHandlerCfg(H, unlockedIds){
  var c = Object.assign({}, H.special);     // shallow base
  c.outcomes = H.special.outcomes ? JSON.parse(JSON.stringify(H.special.outcomes)) : null;
  c.rigChoices = H.special.rigChoices ? H.special.rigChoices.slice() : null;
  for(var i=0;i<H.skill_tree.length;i++){
    var node = H.skill_tree[i];
    if(unlockedIds.indexOf(node.id) < 0) continue;
    var m = node.mods || {};
    for(var k in m){
      if(k==='addCharge'){ c.charges += m.addCharge; }
      else if(k==='addRigChoice'){ if(c.rigChoices && c.rigChoices.indexOf(m.addRigChoice)<0) c.rigChoices.push(m.addRigChoice); }
      else if(k==='addOutcome'){ for(var oid in m.addOutcome) c.outcomes[oid]=m.addOutcome[oid]; }
      else if(k==='weightDelta'){ for(var w in m.weightDelta){ if(c.outcomes[w]) c.outcomes[w].weight=Math.max(0,c.outcomes[w].weight+m.weightDelta[w]); } }
      else if(k==='ultimate'){ c.ultimate = m.ultimate; }
      else { c[k] = m[k]; }                  // scalar overrides: radius, healPct, recharge_sec, markDur, markMul, shieldPct, dmgBuffMul, stealthDur, rigHpMul...
    }
  }
  return c;
}
```

This is the ONLY place node math happens. The skill-tree authoring contract:
scalar nodes set the resolved value (e.g. `radius: 4.0`), additive/structural
nodes use the dedicated keys above. Order-independent (each node's effect is
absolute, not a delta on the previous node), so it is robust to any unlock order.

### 1c. Fill rule (engine.js `update(dt)`, right after the energy-regen block ~line 2189)

The meter fills on REAL `dt` (like energy), gated by `combatScale` so it pauses
during map transitions. It does NOT use the 4x sim `sdt` -- the special cadence
should feel wall-clock steady, matching the energy bar it sits beside.

```js
tickHandlerMeter(dt * combatScale);   // real-time, pauses mid-transition
```

```js
function tickHandlerMeter(dt){
  var sp = game.special; if(!sp || !dt) return;
  // Dealer Small Blessing: compound the gold mult every 30s elapsed.
  if(sp.passive && sp.passive.goldBonusPctPer30s){
    sp.elapsedGoldT += dt;
    while(sp.elapsedGoldT >= 30){ sp.elapsedGoldT -= 30; sp.goldGainMul *= (1 + sp.passive.goldBonusPctPer30s); }
  }
  if(sp.charges >= sp.maxCharges){ sp.meter = sp.rechargeSec; return; }  // full -> hold
  sp.meter += dt;
  if(sp.meter >= sp.rechargeSec){
    sp.meter -= sp.rechargeSec;
    sp.charges = Math.min(sp.maxCharges, sp.charges + 1);
    try{ sfx('ability'); }catch(_e){}   // soft "charge ready" cue
  }
}
```

Tracker `killMeterBonusSec`: in `spawnKillLoot`/`statKill` (the player-kill
attribution path, engine ~line 854), when `victim.owner===1` and the attacker is
owner 0, add `if(game.special && game.special.passive && game.special.passive.killMeterBonusSec) game.special.meter += game.special.passive.killMeterBonusSec;`
(clamped by the `charges>=max` guard above). One line, behind the existing
owner-0 attribution gate -> zero AI-side effect.

---

## 2. PASSIVES -- always-on auras

Passives apply every tick in a new `tickHandlerPassive(sdt)` called from
`update(dt)` right after `computeSynergy(sdt)` (so it composes with synergy, runs
on sim time like the Street Medics aura):

- **Mender `pack_scent`** (`regenPct`): loop `game.units`, owner 0, alive,
  non-structure -> `u.hp = Math.min(u.maxHp, u.hp + u.maxHp*regenPct*sdt)`. Same
  shape as the Street Medics loop (engine ~line 2375).
- **Shadow `swift_paw` / `passiveMove`**: set `u.handlerMove = mult` on owner-0
  units each tick; read in `getSpeed()` as one extra capped layer (see 4c).
- **Bruiser `squad_toughness`** (`allyDamageTakenMul`): set `u.handlerDefTaken =
  0.92` on owner-0 units each tick; read in `takeDamage` (see 4d). `boneWallShieldAdd`
  folds into `computeSynergy`'s `totPct` for Boneguard-crew units (one `+=` next
  to the existing `nsShieldPct` merge at engine ~line 2261).
- **Tracker `keen_senses`**: `visionPreviewSec` is a renderer-only hint (HUD can
  ghost the next AI deploy 0.5s early -- optional, cosmetic). `killMeterBonusSec`
  handled in 1c.
- **Dealer `small_blessing`**: handled in `tickHandlerMeter` (1c). The
  `goldGainMul` multiplies any energy/gold the Dealer special grants.

Passive fields (`handlerMove`, `handlerDefTaken`) are written fresh each tick to
identity (1) for ALL units at the top of `tickHandlerPassive`, then overwritten
for owner-0 if a passive is active -- exactly the reset-then-apply pattern
`computeNamedSynergy` uses, so a buff can never outlive the equipped handler.

---

## 3. FIRE hooks -- which engine primitive each special calls

One dispatcher, `fireSpecial(gx, gy, choiceOpt)`, exported on `AK`. It checks a
charge is available, spends it, then routes by `cfg.kind`. Reuses existing
primitives -- no new combat code paths.

```js
function fireSpecial(gx, gy, choiceOpt){
  var sp = game.special; if(!sp || game.phase!=='live') return false;
  if(sp.charges <= 0) return false;
  var cfg = sp.cfg, owner = 0;
  // placement gate for own-side specials (reuse deploy()'s half clamp)
  if(cfg.ownSideOnly && gy < RIVER_Y + RIVER_H/2 + 0.5) gy = RIVER_Y + RIVER_H/2 + 0.6;
  gx = clamp(gx, 1, ARENA_W-1); gy = clamp(gy, 1, ARENA_H-1);
  var ok = false;
  switch(cfg.kind){
    case 'heal-totem':  ok = fireMenderTotem(cfg, gx, gy); break;
    case 'mark':        ok = fireTrackerMark(cfg, gx, gy); break;
    case 'slipstream':  ok = fireShadowSlip(cfg, gx, gy); break;
    case 'drop-rig':    ok = fireRiggerRig(cfg, gx, gy, choiceOpt || sp.rigChoice); break;
    case 'war-cry':     ok = fireBruiserCry(cfg, gx, gy); break;
    case 'house-edge':  ok = fireDealerEdge(cfg, gx, gy); break;
  }
  if(ok){ sp.charges--; sp.aiming=false; effects.push(fx('ring',gx,gy,'',sp.handler.accent,0.6)); }
  return ok;
}
```

### 3a. Mender -- `spawn-structure` (reuse `new Unit` + `lifeT` + a heal zone)

```js
function fireMenderTotem(cfg, gx, gy){
  var card = handlerStructCard('Field Kennel', cfg.handler && cfg.handler.accent, { totem:true });
  var u = new Unit(card, 0, gx, gy);
  u.maxHp = u.hp = cfg.totemHp; u.handlerDR = cfg.totemDR;   // 20% self DR (read in takeDamage)
  u.lifeT = cfg.lifeT; computeBulk(u); game.units.push(u);
  game.special.reviveUsed = false;
  game.handlerZones.push({ kind:'heal', owner:0, anchorId:u.id, x:gx, y:gy,
    r:cfg.radius, healPct:cfg.healPct, lifeT:cfg.lifeT,
    armorAura: cfg.armorAura || null, revive: cfg.revive || null });
  return true;
}
```

The totem is a real structure: it has HP, can be focused, expires on `lifeT`
exactly like every Clash building (the carry-between-districts filter at
engine ~line 1614 already keeps live structures). The heal/armor/revive logic
runs in `tickHandlerZones` (section 4a).

### 3b. Tracker -- `apply-buff-flag` (stamp mark on enemies in radius)

```js
function fireTrackerMark(cfg, gx, gy){
  var hit=0;
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==1 || !o.alive || (o.card && o.card.type==='spell')) continue;
    if(Math.hypot(o.x-gx,o.y-gy) > cfg.radius) continue;
    o.markT = cfg.markDur; o.markMul = cfg.markMul;          // +damage-taken (read in takeDamage)
    o.revealed = cfg.reveal ? cfg.markDur : (o.revealed||0); // un-hide for the renderer
    if(cfg.noStealthForMarked) o.stealthLock = cfg.markDur;  // Tag capstone: blocks Slipstream-style stealth
    hit++;
  }
  effects.push({type:'spell_zap', x:gx, y:gy, color:'#E2B23A', radius:cfg.radius, dur:0.5, t:0});
  return true;   // fires even on empty ground (reveal sweep) -- design banks 2 charges
}
```

### 3c. Shadow -- `apply-buff-flag` (buff the friendly nearest the tap)

```js
function fireShadowSlip(cfg, gx, gy){
  var best=null, bd=cfg.pickRadius;
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==0 || !o.alive || o.card.isStructure || (o.card && o.card.type==='spell')) continue;
    var d=Math.hypot(o.x-gx,o.y-gy); if(d<bd){ bd=d; best=o; }
  }
  if(!best) return false;                       // no ally to buff -> don't spend the charge
  best.invulnT = Math.max(best.invulnT, cfg.stealthDur);   // untargetable: immune (existing field)
  best.stealthT = cfg.stealthDur;               // NEW flag: enemies skip it in findTarget (4e)
  best.spdBuffT = cfg.stealthDur;               // NEW: timed move buff (read in getSpeed)
  best.spdBuffMul = cfg.speedMul;
  if(cfg.critNext>0) best.critNext = cfg.critNext;   // Assassin's Edge: next-hit crit
  effects.push(fx('txt', best.x, best.y-0.6, 'SLIP', '#9B8CFF', 0.6));
  return true;
}
```

### 3d. Rigger -- `deploy-a-unit` (build a turret Unit from the rig table)

```js
function fireRiggerRig(cfg, gx, gy, choice){
  var rc = cfg.rigCards[choice] || cfg.rigCards[cfg.rigChoices[0]];
  var card = handlerStructCard(rc.name, '#D45A2C', {
    turret:true, dmg: Math.round(rc.dmg*cfg.rigDmgMul), range: rc.range, atkSpd: rc.atkSpd,
    domain: rc.domain, weaponType: rc.weaponType, splash: rc.splash||0, chain: rc.chain||0,
    structArch:'turret'
  });
  var u = new Unit(card, 0, gx, gy);
  u.maxHp = u.hp = Math.round(rc.hp * cfg.rigHpMul);
  // passive structure_durability (1.40) x node rigLifeMul (1.0/1.2): 30 -> 42 -> 50.4
  u.lifeT = rc.lifeT * (game.special.passive && game.special.passive.structLifeMul || 1) * (cfg.rigLifeMul||1);
  if(rc.slowAura) game.handlerZones.push({ kind:'slow', owner:0, anchorId:u.id, x:gx, y:gy,
    r:rc.slowAura.radius, slowPct:rc.slowAura.slowPct, lifeT:u.lifeT });
  computeBulk(u); game.units.push(u);
  return true;
}
```

The turret fights through the normal `updateUnits`/`doAttack` path because it has
`range/dmg/atkSpd/isStructure` -- the same path the K9 Circuitry turret cards
already use. `domain:'air'` (Flak) routes through the existing `canHitDomain`
gate. `splash`/`chain` reuse the projectile splash + beam-chain the renderer
already supports for those `weaponType`s.

The structure-durability PASSIVE also needs to touch CARD-summoned structures
(not just rig turrets). One line in `deploy()` at the `u.lifeT = ...` assignment
(engine ~line 2099):
`if(side.owner===0 && game.special && game.special.passive && game.special.passive.structLifeMul) u.lifeT *= game.special.passive.structLifeMul;`
Behind the owner-0 + handler gate, so AI + non-Rigger handlers are untouched.

### 3e. Bruiser -- `apply-buff-flag` (rally allies in radius; reuse `dmgBuffT` + `shieldHp`)

```js
function fireBruiserCry(cfg, gx, gy){
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==0 || !o.alive || o.card.isStructure) continue;
    if(Math.hypot(o.x-gx,o.y-gy) > cfg.radius) continue;
    o.dmgBuffT = Math.max(o.dmgBuffT, cfg.dmgBuffDur);    // existing: doAttack reads dmgBuffT>0
    o.dmgBuffMul = cfg.dmgBuffMul;                        // NEW: lets Apex Roar push 1.20->1.25
    o.shieldHp = Math.max(o.shieldHp, Math.floor(o.maxHp*cfg.shieldPct));  // existing shield pool
    if(cfg.blockedHitDR>0){ o.handlerDR = Math.max(o.handlerDR||0, cfg.blockedHitDR); o.handlerDRt = cfg.blockedHitDur; }
  }
  effects.push({type:'spell_zap', x:gx, y:gy, color:'#C0392B', radius:cfg.radius, dur:0.5, t:0});
  game.shake += 3;
  return true;
}
```

`doAttack` (engine line 2930) currently hardcodes `if(u.dmgBuffT>0) dmgMult *= 1.2;`.
Change to `if(u.dmgBuffT>0) dmgMult *= (u.dmgBuffMul||1.2);` -- one line, keeps the
1.2 default for the existing card abilities (`dmgBuffT=3` at lines 3028/3052/3063)
that never set `dmgBuffMul`.

### 3f. Dealer -- `mixed` (weighted roll over 4-5 engine primitives)

```js
function fireDealerEdge(cfg, gx, gy){
  var roll = pickWeighted(cfg.outcomes);           // normalizes weights, returns key
  var o = cfg.outcomes[roll], side = game.player;
  var addEnergy = function(raw){ var e = raw * cfg.goldToEnergy * game.special.goldGainMul;
    side.energy = clamp(side.energy + e, 0, ENERGY_MAX); };
  switch(roll){
    case 'coin_rain':  addEnergy(o.goldRaw); coinFx(gx,gy); break;
    case 'pup_swarm':  for(var n=0;n<o.spawnPups;n++) dealerSpawnPup(o.pupCostMax, gx, gy); break;
    case 'blessing_aura': game.handlerZones.push({ kind:'heal', owner:0, x:gx, y:gy,
       r:o.zone.radius, healPct:o.zone.healPct, shieldPct:o.zone.shieldPct, lifeT:o.zone.lifeT }); break;
    case 'double_or_nothing': addEnergy(Math.random()<o.winChance ? o.winRaw : -o.gambleRaw); break;
    case 'house_stake': dealerSpawnSupport(gx,gy); addEnergy(o.goldRaw); break;
  }
  // $BCARDD Blessing ultimate rides ON TOP when unlocked (cfg.ultimate set):
  if(cfg.ultimate){ dealerUltimate(cfg.ultimate, gx, gy); }
  return true;
}
```

- **Coin Rain / Double or Nothing / House Stake gold** = `adjust-resource`:
  `side.energy` clamped to `ENERGY_MAX` (the "Gold->Energy" mapping, section 6).
- **Pup Swarm / House Stake unit** = `deploy-unit`: pick a cheap (`cost<=3`)
  owned card and `new Unit(...)` near the tap (clone of the `deploy()` tail; mark
  `isToken=true` so they don't drop loot or feed synergy activation, like
  `spawnDrone`).
- **Blessing Aura** = `spawn-zone-heal`: a `game.handlerZones` heal entry with a
  `shieldPct` (the only zone that also shields) -- byte-identical to
  `updateGoldenHour` math, localized + time-boxed.
- **$BCARDD Blessing ultimate** = the `castSpell('strike')` AoE loop (300 dmg in
  2 tiles) + permanent `game.special.goldGainMul *= 1.20` + `game.shake +=` for
  the screen kick. Recharge becomes 60s via the resolved `cfg.recharge_sec`.

`handlerStructCard(name, color, opts)` is a small factory (near `mapCanonToEngine`)
that returns a minimal engine card object: `{ name, color, accent:color, hp,
dmg, range, atkSpd, isStructure:true, structArch, weaponType, domain, splash,
chain, faction:null, cost:0, type:'unit', cardNumber:null }`. No canon entry, no
`cardNumber` -> it never touches the loot/stats/level/tune maps (all of which
gate on `card.cardNumber`), so it is invisible to progression and the headless
probes.

---

## 4. Engine read-sites (the new per-unit fields)

All new fields default falsy and every read is guarded, so unequipped/headless =
identity.

- **4a. `tickHandlerZones(sdt)`** (called from `update` after `updateGoldenHour`,
  ~line 2206): for each zone, decrement `lifeT` by `sdt`; drop zones whose
  `lifeT<=0` OR whose `anchorId` unit is dead/gone (totem destroyed -> zone dies).
  Then apply by `kind`:
  - `heal`: friendly units in `r` -> `hp += maxHp*healPct*sdt`; if `shieldPct`,
    top `shieldHp` toward `maxHp*shieldPct` (copy of `updateGoldenHour` lines
    1996-1999).
  - `armorAura` (on the heal zone): set `u.handlerDR = max(u.handlerDR, drPct)` +
    `u.handlerDRt = 0.2` (short refresh) on friendlies in range.
  - `slow` (Suppressor): enemies in `r` -> `slowTimer=max(.,0.3); slowMag=slowPct`
    (same as `tickLockdownStructures`, engine line 2433).
  - `revive` (Mender): in the unit-death path (`takeDamage`, line 1196), if the
    dead unit is owner 0, non-token, within a heal zone whose `revive` is set and
    `!game.special.reviveUsed`, roll `chance` -> set `alive=true; hp=maxHp*hpPct;
    state=DEPLOY; deathTimer=-1; game.special.reviveUsed=true`. One guarded block.

- **4b. Mark (`markT/markMul`)** -- `takeDamage` (line 1167). After the existing
  `tdm` damage-taken mult, add:
  `if(this.markT>0 && this.markMul>1) dmg *= this.markMul;`
  Tick `markT` down in `updateUnits`' status-timer block (line 2660, beside
  `dmgBuffT`/`evadeT`): `if(u.markT>0) u.markT-=dt;` likewise `revealed`,
  `stealthLock`, `handlerDRt`, `spdBuffT`, `stealthT`.

- **4c. Move buff (`spdBuffT/spdBuffMul`, passive `handlerMove`)** -- `getSpeed()`
  (line 1147), after the `tuneAgi` line, OUTSIDE the MOVE_CAP stack (like
  tuneAgi, so it composes rather than eats headroom):
  `if(this.handlerMove>1) base*=this.handlerMove; if(this.spdBuffT>0) base*=this.spdBuffMul;`

- **4d. Damage-reduction (`handlerDR`, passive `handlerDefTaken`)** -- `takeDamage`,
  fold into the existing `tdm` chain (line 1180) so it respects the same soak
  order:
  `if(this.handlerDefTaken && this.handlerDefTaken<1) tdm = Math.max(0.80, tdm*this.handlerDefTaken);`
  `if(this.handlerDR>0 && this.handlerDRt>0) tdm = Math.max(0.50, tdm*(1-this.handlerDR));`

- **4e. Stealth untargetable (`stealthT`)** -- `findTarget` (line 2813), add to the
  enemy scan: `if(o.stealthT>0) continue;`. Combined with `invulnT` (already
  blocks damage) this makes a Slipstreamed unit truly untargetable for the
  window. `stealthLock` (Tracker Tag) is read where Slipstream would apply
  stealth -> skip if `target.stealthLock>0`.

- **4f. Crit-on-exit (`critNext`)** -- `doAttack` (line 2949), where `d` is
  computed: `if(u.critNext>1){ d=Math.floor(d*u.critNext); u.critNext=0; }`. Fires
  once, then clears.

These are the complete set of engine edits: ~10 single-line guarded reads + 4
new tick functions + the `fireSpecial` family. No existing behavior changes when
no handler is equipped (every field is undefined -> falsy).

---

## 5. In-match HUD -- handler portrait + radial meter (index.html)

### 5a. Markup -- in `#dock`, beside `#hand` (index.html ~line 1824)

```html
<div id="dock">
  <div id="energywrap">...</div>
  <div id="cardinfo"></div>
  <div id="handrow">
    <button id="specialbtn" class="special-dock" aria-label="Handler special">
      <svg class="sp-ring" viewBox="0 0 44 44">
        <circle class="sp-track" cx="22" cy="22" r="19"></circle>
        <circle class="sp-fill"  cx="22" cy="22" r="19"></circle>  <!-- stroke-dashoffset = meter -->
      </svg>
      <img class="sp-portrait" alt="" />        <!-- handler.art, glyph fallback -->
      <span class="sp-charges">0</span>          <!-- banked charges -->
    </button>
    <div id="hand"></div>
  </div>
  <div id="hint">...</div>
</div>
```

`#handrow` is a flex row so the radial button docks to the LEFT of the 4-card
hand (thumb-reachable). The ring uses an SVG `stroke-dasharray`/`-dashoffset`
radial fill (conic-gradient fallback for non-SVG). `.special-dock` styling reuses
the existing `.card` gold-glow tokens (`--ak-gold #D4AF37`).

### 5b. Wiring (index.html, in `syncHUD` ~line 3962 and a new init block)

In `syncHUD`, each frame:

```js
var sp = g.special;
if(sp && specialBtn){
  var pct = sp.charges>0 ? 1 : Math.min(1, sp.meter/sp.rechargeSec);
  var circ = 2*Math.PI*19;                       // ring circumference
  spFill.style.strokeDashoffset = String(circ*(1-pct));
  spChargesEl.textContent = sp.charges;
  specialBtn.classList.toggle('ready', sp.charges>0);
  specialBtn.classList.toggle('armed', !!sp.aiming);
  if(spPortrait.src===''){ spPortrait.src = sp.handler.art; spPortrait.onerror=function(){ this.replaceWith(glyphSpan(sp.handler.portrait)); }; }
}
```

Tap handling (init once):

```js
specialBtn.addEventListener('click', function(){
  var g=AK.game; if(!g||!g.special||g.special.charges<=0) return;
  // War Cry / House Edge / Slipstream-on-self can fire instantly at a default
  // point; placement specials ARM and wait for a board tap.
  g.selected=-1;                                  // clear any armed card
  g.special.aiming = true;                        // next board tap = target
  // Rigger: cycle the rig picker on repeat taps of the button.
  if(g.special.cfg.kind==='drop-rig'){ cycleRigChoice(g.special); }
});
```

### 5c. Board-tap routing (index.html `handleCanvasTap` ~line 4366)

Add ONE branch at the top of the function, before the card-place branch:

```js
if(g.special && g.special.aiming){
  AK.fireSpecial(gx, gy, g.special.rigChoice);
  g.special.aiming=false; return;
}
```

So the gesture is: tap the radial -> it arms (and for the Rigger shows the rig
picker) -> tap the board -> `fireSpecial`. War Cry/House Edge can also fire on
the button press at the handler's home position if `aiming` round-trips feel
heavy; the design keeps tap-to-place for parity with card deploys.

Add `fireSpecial` to the `AK` export object (engine.js ~line 4041, beside
`deploy, canDeploy, update`): `newMatch, deploy, canDeploy, update, fireSpecial,`.

---

## 6. Resource mapping note (The Dealer)

The in-match economy is ENERGY (`AK.ENERGY_MAX = 10`, regen `1/1.8`/s); there is
no separate mid-match "Gold" pool (Gold/coins are a META reward computed in
`grantMatchRewards` post-match). The Dealer designs reference "Gold", so:
`handlers_data.js` carries the raw design numbers as `goldRaw`/`winRaw`/`gambleRaw`,
and `fireDealerEdge` converts via `GOLD_TO_ENERGY = 1/3`, clamped to
`ENERGY_MAX`: +18 gold -> +6 energy, +40 -> full bar, -12 -> -4 energy. The
`goldGainMul` (Small Blessing compounding + $BCARDD Blessing +20%) multiplies the
converted energy. This keeps the Dealer's "luck = tempo" fantasy inside the
existing energy economy with no new resource bar to render. (If a true in-match
coin pool is added later, swap `addEnergy` for a `side.gold` adjust -- the data
layer needs no change.)

---

## 7. Handler-SELECT + Bones skill-tree storage (ak_profile)

### 7a. Profile shape (index.html `loadProfile` ~line 5040, never-rewrites backfill)

Add beside the existing `p.skills` / `p.spec` backfills:

```js
// HANDLERS: equipped commander + per-handler Bones skill-tree unlocks.
if(!p.handlers || typeof p.handlers!=='object') p.handlers = {};
var hp = p.handlers;
if(typeof hp.selected!=='string') hp.selected = 'handler_mender';   // starter
if(typeof hp.bones!=='number') hp.bones = 0;                        // Bones currency
if(!hp.unlocked || typeof hp.unlocked!=='object') hp.unlocked = {}; // { handlerId: [nodeId,...] }
// grant every handler its FREE (bones===0) nodes -- the base special is
// inherent in the resolver, so handlers whose tree is all paid upgrades
// (The Bruiser) get nothing free here.
(window.AK_HANDLERS||[]).forEach(function(H){
  if(!Array.isArray(hp.unlocked[H.id])) hp.unlocked[H.id] = [];
  H.skill_tree.forEach(function(n){
    if(n.bones===0 && hp.unlocked[H.id].indexOf(n.id)<0) hp.unlocked[H.id].unshift(n.id);
  });
});
```

`saveProfile` already serializes the whole `DBPROFILE` -> no change needed. Bones
are earned post-match in `grantMatchRewards` (add `DBPROFILE.handlers.bones += bonesAwarded;`
alongside the coins/XP grant) -- award scales with run depth like coins.

### 7b. Spend / unlock (index.html, mirror the existing skill-tree UI)

A node is purchasable iff: not already in `hp.unlocked[hid]`, its `requires` (if
any -- comma-separated ids) are all unlocked, and `hp.bones >= node.bones`. On
buy: `hp.bones -= node.bones; hp.unlocked[hid].push(node.id); saveProfile();`.
Reuse the `#skilltree` panel chrome (index.html ~line 8025, the `ak_profile.skills`
UI) with a handler tab; render each handler's `skill_tree` as cost-pips reading
`node.bones`, gated/owned styling exactly like the card skill grid.

### 7c. Equip + pass into the match (index.html)

- A "HANDLERS" row in the deck/loadout screen lists `window.AK_HANDLERS` as
  selectable portraits; tapping sets `DBPROFILE.handlers.selected = id; saveProfile()`.
- At `startMatch()` (index.html ~line 4677), extend the `AK.newMatch(...)` opts:

```js
var hsel = (DBPROFILE && DBPROFILE.handlers) ? DBPROFILE.handlers : null;
AK.newMatch(activeDeckNames() || AK.STARTER_DECK_NAMES, {
  startSection: opts.startSection||0, diffOffset: diffOffset, city: opts.city, level: opts.level,
  nemesis: opts.nemesis||null,
  handler: hsel ? hsel.selected : 'handler_mender',
  handlerNodes: (hsel && hsel.unlocked && hsel.unlocked[hsel.selected]) || null   // resolved unlock id-list
});
```

`newMatch` reads `opts.handler` + `opts.handlerNodes` in `makeHandlerState`
(section 1a). Headless harness passes neither -> `makeHandlerState` returns null
-> meter disabled, every read identity, probes byte-true.

---

## 8. Implementation order (lowest risk first)

1. Load `handlers_data.js` before `engine.js` (section 0); add `makeHandlerState`
   + `resolveHandlerCfg` + `game.special`/`game.handlerZones` state (1a/1b). No
   behavior change yet (nothing reads them).
2. Add `tickHandlerMeter` + `tickHandlerZones` + `tickHandlerPassive` calls in
   `update` (1c, 2, 4a). Still inert until a special fires.
3. Add the new per-unit field reads (4b-4f) -- guarded, default-falsy.
4. Add the `fireSpecial` family + `handlerStructCard` (section 3) and export
   `AK.fireSpecial`.
5. Profile backfill + equip + `startMatch` opts (section 7).
6. HUD radial + tap routing (section 5). Verify in a real browser (Playwright on
   e5-mother per the AK SOLE DEPLOYER rule), not just the node harness.
7. Skill-tree spend UI + Bones award (7b + grantMatchRewards).

Each step is independently shippable and reversible; steps 1-3 are pure
no-ops on the live game until step 4 wires the trigger.
