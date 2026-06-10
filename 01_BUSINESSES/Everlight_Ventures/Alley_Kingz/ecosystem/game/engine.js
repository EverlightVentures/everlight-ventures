// ==========================================================================
// ALLEY KINGZ -- PROTOTYPE ENGINE (Everlight Arcade)
// Self-contained 2D Canvas lane-combat demo. NO build step. NO npm. NO Unity.
// Runs via: python3 -m http.server  ->  open index.html
//
// HONEST SCOPE -- this is a SINGLE-PLAYER PLAYABLE PROTOTYPE, not the full
// server-authoritative multiplayer game. See ARCADE_MOUNT.md for the gap list.
//   DEMO-LEVEL  : single-player vs scripted AI, client-side state, 2D canvas,
//                 abilities simplified to a categorized effect set, no netcode,
//                 no progression/economy, no wallet/NFT, no 3D rig models.
//   FULL BUILD  : server-authoritative sim, matchmaking, the 2-ability rotation
//                 per dog from ability_params.json, Seedance 3D rigs, $BCARDD /
//                 NFT mint hooks, ladder + chests.
//
// REUSED from prototype/game_v8.html (proven, adapted to 2D):
//   - Unit physics: v(t) = v_max*(1 - e^(-accel*t)) acceleration curve
//   - Unit state machine: DEPLOY -> MOVE -> ACQUIRE -> WINDUP -> ATTACK -> RECOVER
//   - Lane/bridge pathing across the river (moveToward)
//   - Tower targeting + "king locked until a princess falls" rule (findTarget)
//   - Parabolic projectile arcs for ranged units/towers
//   - Energy(elixir) regen + AI deploy heuristic
// ADDED for the canon:
//   - Loads the real 48-card canon (canon.js) instead of v8's 41 invented cars
//   - Canon cost(2-11) -> energy mapped; canon hp/damage used verbatim
//   - Rig name + faction shown on each unit (Twisted-Metal layer)
//   - Rarity-colored frames (Mythic = crown gold)
// ==========================================================================

(function(global){
'use strict';

// ---- DESIGN TOKENS (match the $BCARDD coin site) ----
const PAL = {
  vanta:   '#050507',
  midnight:'#0D0D1A',
  gold:    '#D4AF37',
  goldLo:  '#c9a84c',
  goldHi:  '#f3d77a',
  ivory:   '#E8E8E8',
  steel:   '#4A4A55',
  blue:    '#4488FF',
  red:     '#FF4444',
  ok:      '#44FF88'
};
// Rarity frame colors (canon ladder: Mythic > Legendary > Epic > Rare > Common)
const RARITY_COL = {
  Mythic:    PAL.gold,
  Legendary: '#E6B800',
  Epic:      '#C1440E',
  Rare:      '#00BFFF',
  Common:    PAL.steel
};
const FACTION_COL = {
  boneguard_crew:  '#C9772E', // bruiser / amber
  zoomie_syndicate:'#FF2E88', // sprinter / hot pink
  leashbreak_tactix:'#7B5CFF',// tech-ops / violet
  k9_circuitry:    '#00E0C0'  // turret-util / teal
};
// Per-faction 3-tone palette {base,dark,light} -- the renderer draws the chassis
// body in base, shadow in dark, accents/edges in light. (Spec section 2.)
const FACTION_PAL = {
  boneguard_crew:   { base:'#C9772E', dark:'#6e2f12', light:'#ffb060' }, // amber/brick
  zoomie_syndicate: { base:'#FF2E88', dark:'#5e0e33', light:'#ff8ad0' }, // hot magenta/cyan
  leashbreak_tactix:{ base:'#7B5CFF', dark:'#2a1a55', light:'#b9a6ff' }, // violet
  k9_circuitry:     { base:'#00E0C0', dark:'#064b42', light:'#9affec' }  // teal/chrome
};
// Rig source-car -> short glyph used on the 2D chassis
const RIG_GLYPH = { 'Muscle Car':'M', 'GTR':'S', 'Van':'V', 'Monster Truck':'T' };

// Per-card silhouette body shape, keyed by canon role. (Spec section 2.)
const BODY_SHAPE = {
  Vanguard:'tank', Striker:'brawler', Lancer:'lance', Support:'rounded',
  Assassin:'blade', Skirmisher:'scout', Spawner:'carrier', Hacker:'dish',
  Blaster:'turret', Controller:'dish', Structure:'fixed'
};

// Deterministic string hash (FNV-1a-ish) -> unsigned 32-bit int.
function hashStr(s){
  let h = 2166136261 >>> 0;
  s = String(s||'');
  for(let i=0;i<s.length;i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h >>> 0;
}
// Per-card hue from the name -> HSL -> hex. Every card name yields a distinct
// accent so same-faction same-role cards still read differently. (Spec section 2.)
function hashHue(name){ return hashStr(name) % 360; }
function hslToHex(h,s,l){
  s/=100; l/=100;
  const c=(1-Math.abs(2*l-1))*s, x=c*(1-Math.abs((h/60)%2-1)), m=l-c/2;
  let r=0,g=0,b=0;
  if(h<60){ r=c;g=x; } else if(h<120){ r=x;g=c; } else if(h<180){ g=c;b=x; }
  else if(h<240){ g=x;b=c; } else if(h<300){ r=x;b=c; } else { r=c;b=x; }
  const to=v=>('0'+Math.round((v+m)*255).toString(16)).slice(-2);
  return '#'+to(r)+to(g)+to(b);
}
// weaponType: role + range + abilityType -> one of melee/bullet/cannon/lance/beam/spread.
// (Spec section 2/3 table.)
function deriveWeaponType(role, range, abilityType){
  if(role==='Spawner' || abilityType==='spawn' || abilityType==='chain') return 'spread';
  if(role==='Lancer' || abilityType==='pierce' || abilityType==='line') return 'lance';
  if(role==='Hacker' || role==='Controller' || range>=4) return 'beam';
  if((role==='Vanguard' || role==='Blaster') && range>=2) return 'cannon';
  if((role==='Striker' || role==='Skirmisher') && range>=2) return 'bullet';
  if(range>=2) return 'bullet'; // any other ranged card defaults to a fast bullet
  return 'melee';              // range 1 = melee slash/ram
}
// Projectile feel per weaponType. projColor needs the palette+accent so it is
// resolved in mapCanonToEngine; this table holds the static parts.
const WEAPON_FX = {
  melee:  { projSpeed:0, projSize:0,    projShape:'dot'   },
  bullet: { projSpeed:15, projSize:0.16, projShape:'dot'   },
  cannon: { projSpeed:5,  projSize:0.34, projShape:'shell' },
  lance:  { projSpeed:20, projSize:0.12, projShape:'lance' },
  beam:   { projSpeed:40, projSize:0.08, projShape:'beam'  },
  spread: { projSpeed:10, projSize:0.14, projShape:'pellet'}
};
// Impact particle counts per weaponType. (Spec section 3.)
const IMPACT_COUNT = { melee:4, bullet:5, cannon:14, lance:4, beam:6, spread:4 };
// crossLane: only special flankers may leave their lane. (Spec section 1.)
const CROSS_ROLES = { Assassin:true, Skirmisher:true };
const CROSS_ABILITY = { teleport:true, dash:true, lane_swap:true };

// ---- ARENA CONSTANTS (mirrors v8 grid) ----
const ARENA_W = 18, ARENA_H = 30;
const RIVER_Y = 15, RIVER_H = 1.4;
const BRIDGE_LX = 4, BRIDGE_RX = 14, BRIDGE_W = 3;
const ENERGY_MAX = 10, ENERGY_RATE = 1/1.4, START_ENERGY = 6; // faster regen than v8 to keep canon costs playable
const MATCH_TIME = 180;  // 3-minute match (4 stages x 45s real wall-clock) -- operator 2026-06-07
// ---- TIERED PACE RAMP (Spec: Rich 2026-06-03) ----
// The match clock runs a real 4:00. The SIMULATION speed ramps each minute so
// the game opens tense + slow and ends in a frantic sudden-death blitz:
//   min 1 (0-60s)  -> 0.75x   | min 2 (60-120s) -> 1.5x
//   min 3 (120-180)-> 2.0x    | min 4 (180-240) -> 4.0x  SUDDEN DEATH
const TIER_SPEED = [0.75, 1.5, 2.0, 4.0];
// Dog-pun pace callouts -- flashed on the board the moment each phase hits.
const PHASE_LABELS = [
  { name:"SNIFFIN' DIRT",       flavor:"nose down, scopin' the yard", sfx:'ability' },
  { name:"MARKIN' TERRITORY",   flavor:"this tree's mine now",        sfx:'ability' },
  { name:"OFF THE LEASH",       flavor:"teeth out, full chase",       sfx:'ability' },
  { name:"THAT'S MY SQUIRREL!", flavor:"SUDDEN DEATH • ZOOMIES",  sfx:'bark'    },
];
// Pace tier (0..3) for a given ELAPSED real-time (seconds). min1|min2|min3|min4.
function matchTier(elapsed){
  if(elapsed < 45)  return 0;
  if(elapsed < 90)  return 1;
  if(elapsed < 135) return 2;
  return 3;            // final minute: sudden death
}
function matchSpeed(elapsed){ return TIER_SPEED[matchTier(elapsed)]; }

// ==========================================================================
// MULTI-MAP CONVOY + STORM CLOCK (Master Strategy sec 2.2-2.4 / Track 1 G1-G4)
// The prototype shipped "4 of everything" (4 paces, 4 backdrops, 4 music loops,
// 4 tower skins, 4 difficulty rungs, 4 factions) -- multi-map is binding section
// index 0..3 to all of them at once. matchTier is the section clock; this block
// adds the Storm Clock (a SECOND, independent event scheduler that ticks on REAL
// wall-clock dt so an 8s warning stays readable during the 4x final-minute blitz).
// ==========================================================================

// ---- THE 4 CONVOY SECTIONS (Axis A, spec sec 2.2). Gameplay params only; the
// renderer maps each index to its backdrop / tower skins / music loop. ----
// panDir = the direction the camera pans when ENTERING this section. The road
// WINDS, so the angle varies per transition (operator spec): up -> right -> up-left.
// (idx 0 is the start, never panned into; its value is a harmless default.)
const SECTIONS = [
  { idx:0, name:"SNIFFIN' DIRT",       district:'The Lot',    pace:0.75, diff:0, garrison:'Boneguard Crew',  affix:null,          gateLabel:'LOT WARDEN',    panDir:'up'     },
  { idx:1, name:"MARKIN' TERRITORY",   district:'Neon Night', pace:1.5,  diff:3, garrison:'Zoomie Syndicate',affix:'zoomies',     gateLabel:'NEON RUNNER',   panDir:'up'     },
  { idx:2, name:"OFF THE LEASH",       district:'Industrial', pace:2.0,  diff:5, garrison:'Leashbreak Tactix',affix:'overclock',  gateLabel:'IRON HANDLER',  panDir:'right'  },
  { idx:3, name:"THAT'S MY SQUIRREL!", district:'Rain Docks', pace:4.0,  diff:7, garrison:'K9 Circuitry',    affix:'storm_surge', gateLabel:'DOCK SOVEREIGN',panDir:'upleft' }
];

// ---- STORM CLOCK windows (REAL seconds) + stacking caps (Fairness Doctrine) ----
const STORM_TELEGRAPH = 8.0;   // banner warning >= 8s (rule: telegraphed)
const STORM_ACTIVE    = 26.0;  // event live window
const STORM_BREATHER  = 14.0;  // calm between events (~48s full cycle)
const STRIKE_RETICLE  = 1.6;   // per-strike reticle >= 1.4s (rule: telegraphed)
const MOVE_CAP = 2.0;          // eventMods x synergy move multiplier ceiling
const DMG_CAP  = 1.8;          // eventMods x synergy damage multiplier ceiling

// ---- MAP TRANSITION (operator spec 2026-06-07): a CHOREOGRAPHED cool-down/warm-up
// beat on every section advance instead of a hard cut. Combat FREEZES under the
// camera pan (the "level passed" beat), then warms back up as the new district
// settles. Timed on REAL wall-clock dt so it stays readable even at the 4x final
// minute (same rule as the Storm Clock + camera pan). ----
const TRANSITION_DUR    = 5.0;   // total transition window (real seconds) -- the overworld "journey" beat plays here; SLOW + celebratory
const TRANSITION_FREEZE = 3.7;   // combat stays frozen while the journey overlay plays, then ramps 0->1 over the last ~1.3s as the new district re-engages
// Player spawn / back line: just IN FRONT of the player princess row (towers y=27).
// Alive player units regroup here on a map change so the spent energy is preserved.
const PLAYER_BACKLINE_Y = 25.0;

// ---- THE PUBLIC MENU OF 9 STORM EVENTS (spec sec 2.3). Fixed stats, surfaced on
// the studyable Storm Codex screen. 4 FIELD BUFFS (symmetric global multipliers) +
// 4 HAZARDS (hit CELLS not auto-locked units -> good spacing dodges them) + 1
// OBJECTIVE. Storm Surge is the section-3 entry affix (sec 2.2). ----
const STORM_CATALOG = {
  zoomies:    { type:'buff', name:'ZOOMIES',     flavor:'every paw floors it',   color:'#FF2E88', tierMin:1,
                mods:{ move:1.25, energy:1.25 },           codex:'+25% move speed, +25% energy regen. Symmetric.' },
  overclock:  { type:'buff', name:'OVERCLOCK',   flavor:'rigs redlining',        color:'#7B5CFF', tierMin:2,
                mods:{ energy:1.5, spellCD:0.7 },          codex:'+50% energy regen, -30% spell cooldown. Symmetric.' },
  smog:       { type:'buff', name:'ALLEY SMOG',  flavor:'nobody sees far',       color:'#9aa9b5', tierMin:1,
                mods:{ range:0.7 },                        codex:'Towers + ranged units -30% range. Zero damage -- pure tactics. Symmetric.' },
  glass_bones:{ type:'buff', name:'GLASS BONES', flavor:'everything bites harder',color:'#FF8800', tierMin:2,
                mods:{ dmg:1.3 },                          codex:'+30% ALL damage. The sudden-death amplifier. Symmetric.' },
  storm_surge:{ type:'buff', name:'STORM SURGE', flavor:'the empire shakes',     color:'#4488FF', tierMin:3,
                mods:{ splash:1.2 }, towerHpMult:0.75,     codex:'Tower HP -25% (one-time, both sides), splash +20%. Docks entry affix.' },
  lightning:  { type:'hazard', name:'JUNKYARD LIGHTNING', flavor:'bolts walk the lot', color:'#9fe8ff', tierMin:1,
                domain:'both', strikes:7, strikeDmg:140, radius:1.6, towerDmg:0,
                codex:'~7 telegraphed bolts. Hits ground + air cells. No tower damage. Spacing dodges it.' },
  flood:      { type:'hazard', name:'FLOOD SURGE', flavor:'the river jumps its banks', color:'#3aa6ff', tierMin:2,
                domain:'ground', band:true, strikeDmg:80, knockback:1.4, slow:2.2,
                codex:'Ground-only river band: knockback + slow. Air decks ride right over it.' },
  drone:      { type:'hazard', name:'DRONE SWEEP', flavor:'gunships overhead',  color:'#ff9a5a', tierMin:2,
                domain:'air', strafe:true, strikes:5, strikeDmg:120, radius:1.8, towerDmg:0,
                codex:'Air-only strafing run. Punishes flyer stacks. Ground units are untouched.' },
  scrap_rain: { type:'hazard', name:'SCRAP RAIN', flavor:'the sky comes apart', color:'#ffd07a', tierMin:3,
                domain:'both', strikes:9, strikeDmg:120, radius:1.7, towerDmg:0.5, rare:true,
                codex:'RARE late siege. 50% tower damage. The big swing -- heavily telegraphed.' },
  golden_hour:{ type:'objective', name:'GOLDEN HOUR', subtitle:"$BCARDD's Blessing", flavor:'hold the light', color:'#D4AF37', tierMin:1,
                zoneR:3.0, healPctPerSec:0.05, shieldPct:0.12,
                codex:'Contested center zone heals + shields units inside. The comeback flashpoint. Both sides.' }
};
// Tier-gated weighted pool for AUTONOMOUS rolls (section-entry affixes fire separately).
const STORM_POOL = {
  1:['zoomies','lightning','golden_hour','smog'],
  2:['overclock','glass_bones','flood','drone','lightning','golden_hour'],
  3:['glass_bones','scrap_rain','lightning','drone','golden_hour']
};

// ---- CREW SYNERGY (team-up buff) ----
// Fielding >= this many ALIVE units of the SAME faction on a side lights up a
// faction-flavored buff for ALL that side's units of that faction. Recomputed
// every tick (computeSynergy), so it falls off the instant the count drops.
// Multipliers are deliberately modest (~+15-25%) -- synergy rewards committing
// to a faction without making a mono-faction deck auto-win. Applies to BOTH
// the player AND the AI. (See getSpeed / doAttack / maybeFireAbility / regen.)
const SYNERGY_MIN = 3;
const SYNERGY = {
  boneguard_crew:   { speed:1.0,  damage:1.0,  cdRefresh:1.0,  shieldPct:0.20, label:'Bone Wall'    }, // tanks: regenerating +20% effective-HP shield
  zoomie_syndicate: { speed:1.20, damage:1.0,  cdRefresh:1.0,  shieldPct:0,    label:'Pack Speed'   }, // sprinters: +20% move + faster attack
  leashbreak_tactix:{ speed:1.0,  damage:1.0,  cdRefresh:1.25, shieldPct:0,    label:'Override'     }, // tech: ability cooldowns refresh ~25% faster
  k9_circuitry:     { speed:1.0,  damage:1.20, cdRefresh:1.0,  shieldPct:0,    label:'Targeting Net'} // turrets/range: +20% damage
};

// Cost in the engine = canon cost scaled into the energy band.
// Canon costs run 2..11. We compress so the king-card $BCARDD(10)/Jagged(11) feel
// like a heavy commit (~8-9 energy) without ever exceeding the bar.
function energyCost(canonCost){
  // linear map 2..11 -> 2..9, rounded, min 2
  const e = 2 + (canonCost - 2) * (7/9);
  return Math.max(2, Math.round(e));
}

// Tower stats (Pack Guard = princess, Alpha Den = king). Tuned for ~2-3 min matches.
const TOWER_STATS = {
  princess:{ model:'Pack Guard', hp:1400, dmg:60, range:6,  atkSpd:0.9 },
  king:    { model:'Alpha Den',  hp:2600, dmg:90, range:6.5, atkSpd:0.8 }
};

// ---- CANON -> ENGINE CARD MAP ----
// Preserves canon stats verbatim; only derives engine-side fields.
// Ability is collapsed into a small set of demo effect categories so the
// "abilities fire" requirement is met without re-implementing all 48 rotations.
const ABILITY_KIND = {
  // category -> how the demo fires it
  // (full 2-ability rotation lives in ability_params.json for the real build)
  shield:'shield', buff:'buff', aura:'dr', dr:'dr',
  stun:'stun', slow:'slow', heal:'heal', crit:'crit',
  teleport:'teleport', dash:'teleport', spawn:'spawn',
  disable_tower:'disable_tower', silence:'silence', knockback:'knockback',
  ramp:'ramp', line:'aoe', aoe:'aoe', double_hit:'double', queen_target:'queen',
  turret_break:'turret_break', pierce:'pierce', reveal:'reveal',
  evasion:'evasion', invuln:'invuln', blind:'blind', root:'root',
  chain:'chain', dot:'dot', burst:'crit', lane_swap:'teleport', pierce_:'pierce'
};

function mapCanonToEngine(c){
  const cost = energyCost(c.cost);
  const range = c.range;
  const isRanged = range >= 2;
  const isStructure = (c.move_speed === 0); // turrets in K9 Circuitry
  // ---- Clash-style speed tiers (Spec: stagger the lane, slow the pace) ----
  // canon move_speed (0..1.5) -> a named tier + a TILES/SEC speed. The old
  // c.move_speed*1.35 huddled everyone at ~3 tiles/s; these are the real Clash
  // ratios (Very Slow/Slow/Medium/Fast/Very Fast ~ 1:1.5:2:3:4) scaled so a
  // ~13-tile lane crossing takes the Clash-feel 9-12s (Medium) / 5-6s (V.Fast).
  const ms = c.move_speed;
  const silSeed = hashStr(c.name); // reuse the silhouette seed for a tiny nudge
  let speedTier, speed;
  if(ms === 0)          { speedTier='Static';    speed=0;    }
  else if(ms <= 0.6)    { speedTier='Slow';      speed=0.85; }
  else if(ms <= 0.95)   { speedTier='Medium';    speed=1.25; }
  else if(ms <= 1.25)   { speedTier='Fast';      speed=1.85; }
  else                  { speedTier='Very Fast'; speed=2.35; }
  // per-card nudge so clones are not identical (kept within ~+/-6%)
  if(speed > 0) speed *= (0.94 + (silSeed % 13)/100);
  const kind = ABILITY_KIND[c.abilityType] || 'buff';
  // ---- per-card visual identity (the renderer reads these off unit.card) ----
  const palette = FACTION_PAL[c.factionId] || { base:PAL.steel, dark:'#222', light:'#aaa' };
  // accent: hue from the name hash, with saturation/lightness also jittered from
  // higher hash bits so even a hue collision still yields a unique hex. (Spec section 2.)
  const _h = hashStr(c.name);
  const accent = hslToHex(_h % 360, 66 + (Math.floor(_h/360) % 24), 50 + (Math.floor(_h/9000) % 18));
  const bodyShape = BODY_SHAPE[c.role] || 'rounded';
  const weaponType = deriveWeaponType(c.role, range, c.abilityType);
  const wf = WEAPON_FX[weaponType];
  // projColor: bullet=accent, cannon=#FF6B2C, lance=palette.light, beam=palette.base, spread=accent
  const projColor = weaponType==='cannon' ? '#FF6B2C'
                  : weaponType==='lance'  ? palette.light
                  : weaponType==='beam'   ? palette.base
                  : accent; // bullet + spread
  const crossLane = !!(CROSS_ABILITY[c.abilityType] || CROSS_ROLES[c.role]);
  return {
    id: c.cardNumber,
    cardNumber: c.cardNumber,   // renderer keys unit icons by cardNumber (drawUnit + preloader)
    name: c.name,
    breed: c.breed,
    faction: c.factionId,
    factionName: c.class,
    rarity: c.rarity,
    isMythic: c.isMythic,
    cost: cost,            // ENGINE energy cost (derived)
    canonCost: c.cost,     // ORIGINAL canon cost (shown on card)
    role: c.role,
    hp: c.hp,              // CANON verbatim
    dmg: c.damage,         // CANON verbatim
    atkSpd: c.attack_speed,// CANON verbatim
    range: range,          // CANON verbatim
    speed: speed,          // TILES/SEC at full ramp (Clash tier, NOT inflated)
    speedTier: speedTier,  // Static|Slow|Medium|Fast|Very Fast (shown on card)
    accel: 5.0,            // gentle ramp: ~90% of speed by ~0.5s (see getSpeed)
    isRanged: isRanged,
    isStructure: isStructure,
    abilityName: c.ability.name,
    abilityDesc: c.ability.description,
    abilityCD: c.ability.cooldown || 12,
    abilityKind: kind,
    queenTarget: c.queen_target,
    rig: c.rig,
    color: FACTION_COL[c.factionId] || PAL.steel,
    glyph: RIG_GLYPH[c.rig.sourceCar] || 'M',
    // ---- NEW visual-identity contract fields (Spec section 2 + 5) ----
    palette: palette,                 // {base,dark,light} by faction
    accent: accent,                   // per-card hue (hex)
    bodyShape: bodyShape,             // silhouette family by role
    weaponType: weaponType,           // melee|bullet|cannon|lance|beam|spread
    projSpeed: wf.projSpeed,          // arena units/s (some fast, some slow)
    projColor: projColor,             // shell color by weaponType
    projSize: wf.projSize,            // render size of the projectile
    projShape: wf.projShape,          // dot|shell|lance|beam|pellet
    silhouetteSeed: hashStr(c.name),  // per-unit shape jitter seed
    crossLane: crossLane,             // true = may flank the other lane
    // ---- COMBAT CATEGORIES (Combat Spec sections 1-3) ----
    // Read verbatim from canon; defaults derived in canon.js annotateCombat().
    type: 'troop',
    domain: c.domain || 'ground',                 // 'ground' | 'air'
    targets: c.targets || (isRanged ? 'both' : 'ground'),  // 'ground' | 'air' | 'both'
    splash: !!c.splash,                           // AOE hit on impact
    splashRadius: c.splashRadius || 0             // radius (arena tiles)
  };
}

// ---- SPELL -> ENGINE CARD MAP (Combat Spec section 4) ----
// A spell is a hand card with type:'spell'. It is cast at a POINT, not deployed
// as a troop. Engine fields mirror a troop card enough that the hand UI + cost
// gate work unchanged (id/name/cost/rarity/glyph), plus the spell effect params.
function mapSpellToEngine(s){
  const palette = FACTION_PAL[s.factionId] || { base:PAL.gold, dark:'#222', light:'#aaa' };
  const _h = hashStr(s.name);
  const accent = hslToHex(_h % 360, 70, 56);
  return {
    id: s.spellNumber,
    cardNumber: s.spellNumber,      // hand UI keys art by cardNumber; spells have no PNG -> glyph fallback
    spellId: s.short || s.name,     // castSpell() key
    name: s.name,
    shortName: s.short || s.name,
    type: 'spell',
    faction: s.factionId,
    factionName: s.class,
    rarity: s.rarity || 'Epic',
    isMythic: false,
    cost: Math.max(2, s.cost|0),    // ENERGY cost (spells use canon cost directly)
    canonCost: s.cost,
    role: 'Spell',
    cooldown: s.cooldown || 10,     // seconds between casts (per-card, tracked on the side)
    effect: s.effect,               // freeze|slow|trap|zap|strike
    radius: s.radius || 2.4,        // AOE radius in arena tiles
    duration: s.duration || 0,      // status duration (s)
    damage: s.damage || 0,          // instant damage (zap/strike/trap)
    slowPct: s.slowPct || 0.35,     // tar slow magnitude
    fxKind: s.fx || s.effect,       // renderer FX selector
    glyph: s.glyph || '✦',
    abilityName: s.short || s.name,
    abilityDesc: s.description || '',
    color: FACTION_COL[s.factionId] || PAL.gold,
    palette: palette,
    accent: accent,
    // combat-category fields so any code that reads them on a hand card is safe
    domain:'spell', targets:'both', splash:true, splashRadius:s.radius||2.4,
    speedTier:'-', range:s.radius||2.4
  };
}

// Build the master card index from the inlined canon (troops + spells).
function buildCardIndex(){
  const idx = {};
  (global.CANON_CARDS || []).forEach(c => { idx[c.name] = mapCanonToEngine(c); });
  (global.CANON_SPELLS || []).forEach(s => { idx[s.name] = mapSpellToEngine(s); });
  return idx;
}

// Spell index by spellId (the short cast key) for castSpell lookups.
let SPELLS = {};
function buildSpellIndex(){
  SPELLS = {};
  (global.CANON_SPELLS || []).forEach(s => {
    const m = mapSpellToEngine(s); SPELLS[m.spellId] = m; SPELLS[m.name] = m;
  });
  return SPELLS;
}

// ---- THE STARTER DECK ----
// 8 cards: $BCARDD (Mythic king of the pack) + at least one per faction,
// spanning the cost curve so the demo has a real cycle.
// Boneguard: $BCARDD(M), Grit Bulldog. Zoomie: Pixel Greyhound, Turbo Jack.
// Leashbreak: Static Sheba Inu, Chill Samoyed. K9: Rail Terrier, Laser Beagle.
// Now 8 cards = 6 troops + 2 SPELLS so the spell layer is playable from boot.
// At least one troop per faction remains. STRIKE (neutral) + JOLT (Zoomie) give
// the player a burst-AOE and a swarm-clear/stun on the bar.
const STARTER_DECK_NAMES = [
  '$BCARDD',          // Boneguard Crew  -- Mythic, the king of the pack
  'Grit Bulldog',     // Boneguard Crew  -- cheap melee striker
  'Pixel Greyhound',  // Zoomie Syndicate-- fast cheap dasher (FLYER)
  'Strike',           // SPELL (neutral) -- the fireball, medium AOE burst
  'Chill Samoyed',    // Leashbreak Tactix- slow support
  'Jolt',             // SPELL (Zoomie)  -- instant AOE damage + 0.5s stun
  'Rail Terrier',     // K9 Circuitry    -- ranged anti-structure (anti-air)
  'Laser Beagle'      // K9 Circuitry    -- ranged turret (anti-air)
];

// ==========================================================================
// RUNTIME STATE
// ==========================================================================
let CARDS = {};                 // name -> engine card
let _uid = 0;
const USTATE = {DEPLOY:'deploy',MOVE:'move',ACQUIRE:'acquire',WINDUP:'windup',ATTACK:'attack',RECOVER:'recover',DIE:'die'};

let game = null;  // the live match object
let DIFFICULTY = 0;  // 0=easy (The Lot) ... 9=hardest (Empire State). AK.setDifficulty() sets it per arena/NOS-trophy tier so the AI gets tougher as you climb the ladder.
let effects = []; // floating text + rings
let projectiles = [];
let particles = [];

// ---- TOWER ----
class Tower {
  constructor(x,y,type,owner){
    this.x=x; this.y=y; this.type=type; this.owner=owner;
    const s = TOWER_STATS[type];
    this.maxHp=s.hp; this.hp=s.hp; this.dmg=s.dmg; this.range=s.range; this.atkSpd=s.atkSpd;
    this.atkCD=0;
    this.active = (type!=='king'); // king dormant until a princess falls
    this.destroyed=false; this.crownCounted=false;
    this.hitFlash=0; this.disableTimer=0;
    this.model=s.model;
  }
  takeDamage(d){
    if(this.destroyed) return;
    // District Gate shield soaks first (reuses the unit-shield concept on a tower).
    if(this.gateShield>0){ const s=Math.min(this.gateShield,d); this.gateShield-=s; d-=s; if(d<=0){ this.hitFlash=0.18; return; } }
    this.hp=Math.max(0,this.hp-d); this.hitFlash=0.18;
    if(this.hp<=0){ this.destroyed=true; this.hp=0; }
  }
}

// ---- UNIT (dog + rig) ----
class Unit {
  constructor(card,owner,x,y){
    this.id=_uid++; this.card=card; this.owner=owner; this.x=x; this.y=y;
    this.lane = (x < ARENA_W/2) ? 0 : 1; // overwritten by deploy(); default by spawn x
    this.maxHp=card.hp; this.hp=card.hp; this.dmg=card.dmg;
    this.maxSpeed=card.speed; this.accel=card.accel;
    this.range=card.range; this.atkSpd=card.atkSpd; this.atkCD=0;
    this.abilityCD=2; // first fire allowed shortly after deploy
    this.target=null; this.acquireTarget=null; this.alive=true;
    this.angle = owner===0 ? -Math.PI/2 : Math.PI/2;
    this.targetAngle=this.angle;
    this.spawnTime=0; this.hitFlash=0; this.deathTimer=-1;
    this.state=USTATE.DEPLOY; this.stateTimer=0; this.deployScale=0;
    this.bob=Math.random()*Math.PI*2;
    // status
    this.slowTimer=0; this.stunTimer=0; this.shieldHp=0; this.dmgBuffT=0;
    this.evadeT=0; this.invulnT=0; this.silenceT=0;
    this.muzzle=0;
    // ---- SPELL STATUS EFFECTS (Combat Spec section 4) ----
    // frozenTimer: total stop (no move, no attack, abilities paused). FREEZE.
    // snareTimer : rooted in place (no move) but may still attack. SNARE TRAP.
    // slowMag    : -fraction applied to move + attack speed while slowTimer>0.
    //              0 falls back to the legacy ability-slow (-50%); TAR SLOW sets 0.35.
    this.frozenTimer=0; this.snareTimer=0; this.slowMag=0;
    // crew synergy (set each tick by computeSynergy; renderer reads u.synergy)
    this.synergy=false;          // true while this unit's faction has >= SYNERGY_MIN alive on its side
    this.synergyMul=null;        // the active SYNERGY[faction] multiplier table (or null)
    this.synergyShieldHp=0;      // regenerating Bone Wall shield pool (separate from ability shieldHp)
  }
  getSpeed(){
    if(this.card.isStructure) return 0;
    if(this.frozenTimer>0 || this.snareTimer>0) return 0; // FREEZE stops, SNARE roots
    let base = this.maxSpeed*(1-Math.exp(-this.accel*this.spawnTime));
    if(this.slowTimer>0) base*=(1 - (this.slowMag>0?this.slowMag:0.5)); // TAR SLOW (35%) or legacy ability-slow (50%)
    // Move multiplier stack: crew synergy (Pack Speed) x Storm Clock field buff
    // (Zoomies), clamped at MOVE_CAP per the Fairness Doctrine capped-stacking rule.
    let mult = 1;
    if(this.synergy && this.synergyMul) mult *= this.synergyMul.speed; // Pack Speed (Zoomie) move boost
    if(game && game.eventMods) mult *= game.eventMods.move;            // Storm Clock buff layer
    if(mult > MOVE_CAP) mult = MOVE_CAP;
    base *= mult;
    return base;
  }
  takeDamage(d,sx,sy){
    if(!this.alive) return;
    if(this.invulnT>0) return;
    if(this.evadeT>0 && Math.random()<0.2){ effects.push(fx('txt',this.x,this.y-0.5,'DODGE',PAL.ivory,0.5)); return; }
    let dmg=d;
    // Bone Wall synergy shield soaks first (it regenerates while synergy holds).
    if(this.synergyShieldHp>0){
      const soaked=Math.min(this.synergyShieldHp,dmg);
      this.synergyShieldHp-=soaked; dmg-=soaked;
    }
    if(this.shieldHp>0){
      const absorbed=Math.min(this.shieldHp,dmg);
      this.shieldHp-=absorbed; dmg-=absorbed;
    }
    if(dmg<=0){ this.hitFlash=0.1; return; }
    this.hp=Math.max(0,this.hp-Math.floor(dmg)); this.hitFlash=0.14;
    if(this.hp<=0){
      this.hp=0; this.alive=false; this.deathTimer=0;
      this.state=USTATE.DIE; this.stateTimer=0;
      sfx('death');
      if(game) game.shake += 2; // unit death kick (Spec section 4)
      addBurst(this.x,this.y,this.card.color,10);
    }
  }
  dist(ox,oy){ return Math.hypot(this.x-ox,this.y-oy); }
}

// ==========================================================================
// MATCH SETUP
// ==========================================================================
function newMatch(playerDeckNames){
  _uid=0; effects=[]; projectiles=[]; particles=[];
  const mk = (arr)=>arr.map(n=>CARDS[n]).filter(Boolean);
  const pDeck = mk(playerDeckNames && playerDeckNames.length ? playerDeckNames : STARTER_DECK_NAMES);
  // AI uses the Zoomie Split Rush starter (a different faction for variety).
  const aiNames = (global.CANON_DECKS.find(d=>d.class==='Zoomie Syndicate')||{}).cards || STARTER_DECK_NAMES;
  const aDeck = mk(aiNames);

  game = {
    units: [],
    traps: [],  // SNARE TRAP: armed hidden traps {owner,x,y,radius,dmg,duration,armT,triggered}
    player:   { owner:0, energy:START_ENERGY, crowns:0, towers:[], deck:shuffle(pDeck), hand:[], next:0, spellCD:{} },
    opponent: { owner:1, energy:START_ENERGY, crowns:0, towers:[], deck:shuffle(aDeck), hand:[], next:0, aiCD:0, aiNext:2, spellCD:{} },
    time: MATCH_TIME,
    phase: 'countdown',  // countdown -> live -> ended
    cd: 3,
    result: '',
    selected: -1,
    shake: 0,  // screen shake magnitude (renderer reads + decays via AK.game)
    // ---- CONVOY RUN state (Axis A, spec sec 2.2) ----
    convoyMode: true,                // the 4-section run is on
    section: 0,                      // current district 0..3
    gatesCleared: 0,                 // District Gates beaten this run
    gateClearedThisSection: false,   // did we beat THIS district's gate?
    stars: 0,                        // 1 star per clean Gate clear
    cleanSweep: false,
    // ---- camera (G2.0): default IDENTITY so play is pixel-identical until a pan ----
    camera: { offX:0, offY:0, zoom:1 },
    pan: { active:false, t:1, dur:1.05, fromSection:0, toSection:0, dir:'up', fromX:0, fromY:0 },
    // ---- MAP TRANSITION beat (cool-down/warm-up that freezes combat under the pan) ----
    transition: { active:false, t:0, dur:TRANSITION_DUR },
    // ---- Storm Clock (G1): ticks on REAL wall-clock dt ----
    storm: { phase:'idle', eventKey:null, timer:0, clock:0, strikes:[], nextRollIn:9.0, lastWasObjective:false },
    eventMods: { move:1, dmg:1, energy:1, spellCD:1, range:1, splash:1, atkSpeed:1 },
    goldenHour: { active:false, x:ARENA_W/2, y:RIVER_Y, r:0, timer:0 },
    speedTierIdx: -1,
    gameSpeed: TIER_SPEED[0]
  };
  // towers (player bottom, opponent top)
  game.player.towers = [
    new Tower(BRIDGE_LX,27,'princess',0),
    new Tower(BRIDGE_RX,27,'princess',0),
    new Tower(9,29,'king',0)
  ];
  game.opponent.towers = [
    new Tower(BRIDGE_LX,3,'princess',1),
    new Tower(BRIDGE_RX,3,'princess',1),
    new Tower(9,1,'king',1)
  ];
  // deal hands (4 cards, rest in queue)
  dealHand(game.player);
  dealHand(game.opponent);
  // staircase difficulty + District Gate mini-boss for section 0
  DIFFICULTY = SECTIONS[0].diff;
  promoteGate(0);
  return game;
}

// ==========================================================================
// CONVOY SECTION MACHINE (G3 + G4)
// ==========================================================================
// Promote a district's enemy king tower into a "District Gate" mini-boss:
// faction-flavored, beefier, with a periodic mechanic that reuses the existing
// shield / zap / disable_tower paths. (spec sec 2.1 #1 + G4.0.)
function promoteGate(section){
  const king = game.opponent.towers.find(t=>t.type==='king');
  if(!king) return;
  const sec = SECTIONS[section] || SECTIONS[0];
  king.isGate     = true;
  king.gateFaction= sec.garrison;
  king.gateLabel  = sec.gateLabel;
  king.maxHp      = Math.floor(TOWER_STATS.king.hp * (1.35 + 0.12*section)); // staircase bulk
  king.hp         = king.maxHp;
  king.gateCD     = 6;  // seconds between gate mechanic pulses (ticks on sim time)
  // faction mechanic: Boneguard=shield, Zoomie=zap, Leashbreak=disable, K9=zap
  king.gateMech   = section===0?'shield' : section===2?'disable' : 'zap';
}

// Advance the convoy to the next district. viaGate=true when a Gate was cleared
// early (pulls the speed-up forward -- research_td "clear-speed = tempo currency");
// viaGate=false when the section CLOCK forced us forward (missed Gate -> Pursuers).
function advanceSection(viaGate){
  if(game.section >= 3){ if(viaGate) cleanSweepWin(); return; }
  const next = game.section + 1;
  game.section = next;
  game.gateClearedThisSection = false;
  startTransition();                        // cool-down/warm-up beat: freeze combat under the pan
  resetEnemyGarrison(next);                 // enemy garrison + towers RESET fresh
  repositionPlayerUnitsToBack();            // ALIVE player units regroup at the back + re-advance; DEAD are scrapped
  if(!viaGate){ spawnPursuers(); }          // missed-Gate chip pressure (never ends the run)
  // section-entry affix fires as a forced Storm Clock event (G3.3)
  const affix = SECTIONS[next].affix;
  if(affix){ triggerStormEvent(affix); }
  startPan(next);                           // camera slide-pan in this section's panDir + crossfade (renderer)
  // The overworld JOURNEY overlay (renderer drawConvoyJourney) owns the transition
  // text now -- "DISTRICT CLEARED -> GOOD JOB -> ENTERING X" + the curvy path with
  // checkmarks. No phaseAlert banner here (it would double up over the journey).
  game.speedTierIdx = next;
  sfx(next===3 ? 'bark' : 'ability');
}

// ---- MAP TRANSITION helpers (operator spec) ----
// Start the choreographed cool-down/warm-up window. Ticked on REAL dt in update().
function startTransition(){
  // game.section is already the DESTINATION here (advanceSection set it first), so
  // from = section-1, to = section. The renderer's journey overlay reads these.
  game.transition = { active:true, t:0, dur:TRANSITION_DUR, from:game.section-1, to:game.section };
}
// Combat-sim scale during a transition: 0 while frozen (under the camera pan),
// then a smooth warm-up ramp to 1 as the new district settles. 1 when idle.
function transitionCombatScale(){
  const tr = game.transition;
  if(!tr || !tr.active) return 1;
  if(tr.t <= TRANSITION_FREEZE) return 0;
  const span = Math.max(0.01, tr.dur - TRANSITION_FREEZE);
  return clamp((tr.t - TRANSITION_FREEZE)/span, 0, 1);
}
// Troop reset-to-the-back: on a map change, every ALIVE player unit relocates to
// the player spawn line at the BACK of the new section and re-advances forward,
// so the energy the player spent is NOT wasted. DEAD player units are scrapped
// (gone). Enemy garrison resets fresh per the existing rule (resetEnemyGarrison).
// The relocate snap is hidden under the camera pan (juice masks the swap).
function repositionPlayerUnitsToBack(){
  // 1) scrap dead player units -- carry-over only preserves the LIVE investment
  game.units = game.units.filter(u => !(u.owner===0 && !u.alive));
  // 2) clear ALL projectiles -- old shots were aimed at the previous district
  projectiles = [];
  // 3) lay the survivors out in a tidy back-line formation, per lane, then re-advance
  const laneCount = { 0:0, 1:0 };
  for(const u of game.units){
    if(u.owner!==0 || !u.alive) continue;
    const laneX = (u.lane===0) ? BRIDGE_LX : BRIDGE_RX;
    const rank  = laneCount[u.lane]++;
    const col = (rank % 3) - 1, row = Math.floor(rank/3);   // 3-wide columns, stacked back
    u.x = clamp(laneX + col*1.1, 1, ARENA_W-1);
    u.y = clamp(PLAYER_BACKLINE_Y + row*1.1, RIVER_Y+2, ARENA_H-1.5);
    // re-advance forward from the back: drop targets, reset to MOVE, re-ramp the accel curve
    u.target=null; u.acquireTarget=null;
    u.state=USTATE.MOVE; u.stateTimer=0; u.deployScale=1; u.spawnTime=0; u.atkCD=0;
    u.angle=-Math.PI/2; u.targetAngle=-Math.PI/2;   // face forward (player marches up)
    // clear movement-blocking statuses left over from the previous district
    u.frozenTimer=0; u.stunTimer=0; u.snareTimer=0; u.slowTimer=0; u.slowMag=0;
    effects.push(fx('ring', u.x, u.y, '', PAL.gold, 0.5));   // small regroup pop
  }
}

// Reset the enemy side for a fresh district: drop the old crew, deal the new
// faction's garrison deck, rebuild towers, re-promote the Gate, set difficulty.
// PLAYER units / towers / energy / crowns CARRY OVER (the "ride with the convoy").
function resetEnemyGarrison(section){
  const sec = SECTIONS[section];
  // mark old enemy units dead first so any stale player target ref invalidates,
  // then drop them from the board.
  game.units.forEach(u=>{ if(u.owner===1) u.alive=false; });
  game.units.forEach(u=>{ if(u.owner===0){ u.target=null; u.acquireTarget=null; } });
  game.units = game.units.filter(u=> u.owner!==1);
  projectiles = projectiles.filter(p=> p.owner===0);   // drop enemy shots at the old crew
  // fresh garrison deck for this district faction
  const deckDef = (global.CANON_DECKS||[]).find(d=>d.class===sec.garrison);
  const names = (deckDef && deckDef.cards) || STARTER_DECK_NAMES;
  const aDeck = names.map(n=>CARDS[n]).filter(Boolean);
  game.opponent.deck = shuffle(aDeck.length?aDeck:STARTER_DECK_NAMES.map(n=>CARDS[n]).filter(Boolean));
  game.opponent.hand = []; game.opponent.queueIdx = 0;
  dealHand(game.opponent);
  game.opponent.energy = START_ENERGY;
  game.opponent.aiCD = 0; game.opponent.aiNext = 2; game.opponent.aiLane = undefined;
  game.opponent.spellCD = {};
  game.opponent.towers = [
    new Tower(BRIDGE_LX,3,'princess',1),
    new Tower(BRIDGE_RX,3,'princess',1),
    new Tower(9,1,'king',1)
  ];
  DIFFICULTY = sec.diff;        // staircase difficulty rung
  promoteGate(section);
}

// Clean Gate clear reward (the comeback equalizer -- rewards the player's clear,
// never secretly buffs the AI). spec defaults: heal 25% units / repair 15% towers.
function grantGateReward(){
  game.units.forEach(u=>{ if(u.owner===0 && u.alive) u.hp=Math.min(u.maxHp, u.hp+Math.floor(u.maxHp*0.25)); });
  game.player.towers.forEach(t=>{ if(!t.destroyed) t.hp=Math.min(t.maxHp, t.hp+Math.floor(t.maxHp*0.15)); });
  game.player.energy = Math.min(ENERGY_MAX, game.player.energy + 3);
  effects.push(fx('crown', ARENA_W/2, RIVER_Y, 'GATE CLEARED +1', PAL.gold, 1.6));
}

// Missed-Gate penalty: 1-2 enemy "Pursuer" units chase in as chip pressure.
function spawnPursuers(){
  const deckDef = (global.CANON_DECKS||[]).find(d=>d.class===SECTIONS[game.section].garrison);
  const names = (deckDef && deckDef.cards) || STARTER_DECK_NAMES;
  const n = 1 + (Math.random()<0.5?1:0);
  let spawned=0;
  for(let i=0;i<n*2 && spawned<n;i++){
    const card = CARDS[names[Math.floor(Math.random()*names.length)]];
    if(!card || card.type==='spell') continue;
    const lane = Math.random()<0.5?0:1;
    const x = (lane===0?BRIDGE_LX:BRIDGE_RX) + (Math.random()-0.5);
    const u = new Unit(card, 1, x, 4); u.lane = lane;
    game.units.push(u); spawned++;
  }
  if(spawned) effects.push(fx('txt', ARENA_W/2, 6, 'PURSUERS!', PAL.red, 1.2));
}

function cleanSweepWin(){
  if(game.phase==='ended') return;
  game.player.crowns += 1; game.stars = (game.stars||0)+1;
  game.cleanSweep = true; game.phase='ended'; game.result='win';
  sfx('win');
}

// ---- camera slide-pan (G3.1): pan UP one board-height, ease back to identity.
// The new district slides in from the top; the carry-over snap is hidden at the
// pan mid-point. Ticks on REAL dt (updatePan). ----
// Per-direction START offsets for the camera (eased to 0 by updatePan). The new
// district's content begins shifted one board off-screen in the OPPOSITE direction
// to the pan, so it slides IN from that edge. Winding road => varies per section.
function panOffsets(dir){
  switch(dir){
    case 'right':   return { x:-ARENA_W,     y:0          };  // camera pans right -> content enters from the right
    case 'left':    return { x: ARENA_W,     y:0          };  // pans left  -> enters from the left
    case 'down':    return { x:0,            y:-ARENA_H   };  // pans down  -> enters from below
    case 'upright': return { x:-ARENA_W*0.7, y:ARENA_H*0.7};  // angled up-right
    case 'upleft':  return { x: ARENA_W*0.7, y:ARENA_H*0.7};  // angled up-left
    case 'up':
    default:        return { x:0,            y:ARENA_H    };  // pans up (north) -> enters from above (default)
  }
}
function startPan(toSection){
  const dir = (SECTIONS[toSection] && SECTIONS[toSection].panDir) || 'up';
  const o = panOffsets(dir);
  game.pan = { active:true, t:0, dur:2.4, fromSection: game.section-1, toSection: toSection,
               dir: dir, fromX: o.x, fromY: o.y };
  game.camera.offX = o.x;   // content sits one board off-screen along panDir; eases to 0
  game.camera.offY = o.y;
}
function updatePan(dt){
  const p = game.pan; if(!p || !p.active) return;
  p.t = Math.min(1, p.t + dt/p.dur);
  const e = 1 - Math.pow(1-p.t, 3);            // ease-out cubic
  game.camera.offX = (p.fromX!=null ? p.fromX : 0)       * (1 - e);
  game.camera.offY = (p.fromY!=null ? p.fromY : ARENA_H) * (1 - e);
  if(p.t>=1){ p.active=false; game.camera.offY=0; game.camera.offX=0; }
}

// ==========================================================================
// THE STORM CLOCK (G1) -- a data-driven event scheduler on REAL wall-clock dt.
// matchTier is the section clock; this is the SECOND, independent timeline:
// TELEGRAPH -> ACTIVE -> BREATHER windows (~48s). Real dt keeps the 8s warning
// readable even during the 4x final minute. Fires ONE global event at a time.
// ==========================================================================
function updateStorm(dt){
  const s = game.storm; if(!s) return;
  if(s.phase==='idle'){
    // Section 0 is the teaching district -- no autonomous storm. From section 1 on,
    // the clock rolls. (Section-entry affixes still fire via triggerStormEvent.)
    if(game.section >= 1){
      s.nextRollIn -= dt;
      if(s.nextRollIn <= 0) rollStormEvent();
    }
    return;
  }
  s.timer += dt;
  if(s.phase==='telegraph'){
    if(s.timer >= STORM_TELEGRAPH) enterStormActive();
  } else if(s.phase==='active'){
    s.clock += dt;
    const ev = STORM_CATALOG[s.eventKey];
    if(ev && ev.type==='hazard') tickHazardStrikes(ev);
    if(s.timer >= STORM_ACTIVE) enterStormBreather();
  } else if(s.phase==='breather'){
    if(s.timer >= STORM_BREATHER){
      s.phase='idle'; s.eventKey=null; s.timer=0; s.strikes=[];
      s.nextRollIn = 5 + Math.random()*7;
    }
  }
}
function rollStormEvent(){
  const tier = Math.min(3, Math.max(1, game.section));
  const pool = STORM_POOL[tier] || STORM_POOL[1];
  let key = pool[Math.floor(Math.random()*pool.length)];
  if(key==='golden_hour' && game.storm.lastWasObjective) key = pool[(pool.indexOf(key)+1)%pool.length];
  beginStorm(key);
}
function triggerStormEvent(key){ if(STORM_CATALOG[key]) beginStorm(key); }
function beginStorm(key){
  const ev = STORM_CATALOG[key]; if(!ev) return;
  const s = game.storm;
  s.phase='telegraph'; s.eventKey=key; s.timer=0; s.clock=0; s.strikes=[];
  s.lastWasObjective = (ev.type==='objective');
  game.stormAlert = { name:'INCOMING: '+ev.name, flavor:ev.flavor||'', color:ev.color||PAL.gold,
                      type:ev.type, ttl:STORM_TELEGRAPH, dur:STORM_TELEGRAPH };
  sfx('ability');
}
function enterStormActive(){
  const s = game.storm; const ev = STORM_CATALOG[s.eventKey];
  if(!ev){ s.phase='breather'; s.timer=0; return; }
  s.phase='active'; s.timer=0; s.clock=0;
  if(ev.type==='hazard')    scheduleHazard(ev);
  if(ev.type==='objective') openGoldenHour(ev);
  if(ev.type==='buff' && ev.towerHpMult) applyTowerHpMult(ev.towerHpMult);
  recomputeEventMods();
  game.stormAlert = { name:ev.name, flavor:ev.subtitle||ev.flavor||'', color:ev.color||PAL.gold,
                      type:ev.type, ttl:2.4, dur:2.4 };
  sfx(ev.type==='hazard' ? 'bark' : 'ability');
}
function enterStormBreather(){
  const s = game.storm; const ev = STORM_CATALOG[s.eventKey];
  s.phase='breather'; s.timer=0; s.strikes=[];
  if(ev && ev.type==='objective') closeGoldenHour();
  recomputeEventMods();   // clears buff mods
}

// Recompute the symmetric field-buff multipliers from the active storm event.
// (Both sides eat the identical event at the identical second -- Fairness rule.)
function recomputeEventMods(){
  const m = { move:1, dmg:1, energy:1, spellCD:1, range:1, splash:1, atkSpeed:1 };
  const s = game.storm;
  if(s && s.phase==='active' && s.eventKey){
    const ev = STORM_CATALOG[s.eventKey];
    if(ev && ev.type==='buff' && ev.mods){ for(const k in ev.mods) m[k] *= ev.mods[k]; }
  }
  game.eventMods = m;
}
function applyTowerHpMult(mult){   // Storm Surge one-time tower HP hit (both sides)
  [...game.player.towers, ...game.opponent.towers].forEach(t=>{
    if(t.destroyed) return;
    t.maxHp = Math.floor(t.maxHp*mult);
    t.hp = Math.min(t.hp, t.maxHp);
  });
}

// ---- HAZARDS (G1.3): hit CELLS, not auto-locked units -> spacing dodges them.
// Each strike telegraphs a reticle >= STRIKE_RETICLE before it lands. Hunter-mode
// targeting (operator default) aims the densest cluster at place-time. ----
function scheduleHazard(ev){
  const s = game.storm; s.strikes = [];
  if(ev.band){
    // FLOOD SURGE: a few timed pulses of the ground-only river band.
    const pulses = 4;
    for(let i=0;i<pulses;i++){
      s.strikes.push({ band:true, at: 1.2 + i*(STORM_ACTIVE-2.4)/pulses, fired:false,
                       dmg:ev.strikeDmg, knockback:ev.knockback, slow:ev.slow });
    }
    return;
  }
  const n = ev.strikes||0;
  const span = STORM_ACTIVE - 2.6;
  for(let i=0;i<n;i++){
    const at = 1.3 + (n>1 ? i*span/(n-1) : 0);
    s.strikes.push({ at, x:0, y:0, placed:false, fired:false, r:ev.radius||1.6,
                     dmg:ev.strikeDmg, domain:ev.domain||'both', towerDmg:ev.towerDmg||0, strafe:!!ev.strafe });
  }
}
function tickHazardStrikes(ev){
  const s = game.storm;
  for(const st of s.strikes){
    if(st.fired) continue;
    if(st.band){ if(s.clock>=st.at){ st.fired=true; fireFloodBand(st); } continue; }
    if(!st.placed && s.clock >= st.at - STRIKE_RETICLE){
      const cell = pickHazardCell(st.domain, st.strafe);
      st.x = cell.x; st.y = cell.y; st.placed = true;
    }
    if(st.placed && s.clock >= st.at){ st.fired=true; fireHazardStrike(st); }
  }
}
// Hunter mode: aim the densest cluster of units the hazard CAN affect (owner-blind
// rule applied to both sides -> symmetric). No units -> a random playfield cell.
function pickHazardCell(domain, strafe){
  const pts = game.units.filter(u=>u.alive && (!u.card||u.card.type!=='spell') &&
              (domain==='both' || (u.card.domain||'ground')===domain));
  if(strafe){
    if(pts.length){ const u=pts[Math.floor(Math.random()*pts.length)];
      return { x:clamp(u.x+(Math.random()-0.5),1,ARENA_W-1), y:clamp(u.y,2,ARENA_H-2) }; }
    return { x:2+Math.random()*(ARENA_W-4), y:RIVER_Y+(Math.random()-0.5)*6 };
  }
  if(!pts.length) return { x:2+Math.random()*(ARENA_W-4), y:4+Math.random()*(ARENA_H-8) };
  let best=pts[0], bestC=-1;
  for(const u of pts){
    let c=0; for(const o of pts){ if(Math.hypot(o.x-u.x,o.y-u.y)<=2.2) c++; }
    if(c>bestC){ bestC=c; best=u; }
  }
  return { x:clamp(best.x+(Math.random()-0.5)*0.8,1,ARENA_W-1), y:clamp(best.y+(Math.random()-0.5)*0.8,1,ARENA_H-1) };
}
function fireHazardStrike(st){
  applyMapDamage(st.x, st.y, st.r, st.dmg,
    { domain:st.domain, towerDmgPct:st.towerDmg, color: st.strafe?'#ff9a5a':'#9fe8ff' });
}
function fireFloodBand(st){
  const bandY = RIVER_Y, bandH = 4.0;
  for(const o of game.units){
    if(!o.alive || (o.card&&o.card.type==='spell')) continue;
    if((o.card.domain||'ground')!=='ground') continue;        // air rides over
    if(Math.abs(o.y-bandY) <= bandH/2){
      o.takeDamage(Math.floor(st.dmg), o.x, o.y);
      o.slowTimer = Math.max(o.slowTimer, st.slow||2.0); o.slowMag = Math.max(o.slowMag, 0.35);
      const dir = (o.owner===0)? 1 : -1;                       // shove back toward own side
      o.y = clamp(o.y + dir*(st.knockback||1.2), 1, ARENA_H-1);
      addBurst(o.x,o.y,'#3aa6ff',5);
    }
  }
  effects.push({ type:'flood_band', x:ARENA_W/2, y:bandY, color:'#3aa6ff', radius:bandH, dur:0.8, t:0 });
  if(game) game.shake += 4;
  sfx('tower_hit');
}

// applyMapDamage -- the neutral map-hazard helper (a castSpell mirror, but
// owner-AGNOSTIC: it damages BOTH sides' units in the cell, honoring domain so a
// ground-only flood can't tag flyers). Optional fractional tower damage. (G1.3.)
function applyMapDamage(cx, cy, radius, dmg, opts){
  opts = opts || {};
  const dom = opts.domain || 'both';
  const col = opts.color || '#9fe8ff';
  for(const o of game.units){
    if(!o.alive || (o.card && o.card.type==='spell')) continue;
    if(dom!=='both' && (o.card.domain||'ground')!==dom) continue;
    if(Math.hypot(o.x-cx, o.y-cy) <= radius){
      o.takeDamage(Math.floor(dmg), cx, cy);
      addBurst(o.x, o.y, col, 5);
    }
  }
  if(opts.towerDmgPct && opts.towerDmgPct>0){
    [...game.player.towers, ...game.opponent.towers].forEach(t=>{
      if(t.destroyed) return;
      if(Math.hypot(t.x-cx, t.y-cy) <= radius+0.6){
        t.takeDamage(Math.floor(dmg*opts.towerDmgPct));
        checkTowerDeathNeutral(t);
      }
    });
  }
  effects.push({ type:'hazard_strike', x:cx, y:cy, color:col, radius:radius, dur:0.45, t:0 });
  if(game) game.shake += 3;
  sfx('ability');
}

// ---- GOLDEN HOUR objective zone (G1.4) -- "$BCARDD's Blessing". A contested
// center heal/shield zone = the scheduled comeback flashpoint. Symmetric (both
// sides heal inside it -> contest the center, the only no-rubber-band comeback). ----
function openGoldenHour(ev){
  game.goldenHour = { active:true, x:ARENA_W/2, y:RIVER_Y, r:ev.zoneR||3.0,
                      healPctPerSec:ev.healPctPerSec||0.05, shieldPct:ev.shieldPct||0.12, timer:0 };
  effects.push({ type:'golden_open', x:ARENA_W/2, y:RIVER_Y, color:PAL.gold, radius:ev.zoneR||3, dur:0.6, t:0 });
}
function closeGoldenHour(){ if(game.goldenHour) game.goldenHour.active=false; }
function updateGoldenHour(dt){
  const z = game.goldenHour; if(!z || !z.active) return;
  z.timer += dt;
  for(const u of game.units){
    if(!u.alive || (u.card&&u.card.type==='spell')) continue;
    if(Math.hypot(u.x-z.x, u.y-z.y) <= z.r){
      u.hp = Math.min(u.maxHp, u.hp + u.maxHp*z.healPctPerSec*dt);
      const cap = Math.floor(u.maxHp*z.shieldPct);
      if(u.shieldHp < cap) u.shieldHp = Math.min(cap, u.shieldHp + cap*dt*0.5);
    }
  }
}
function shuffle(a){ a=[...a]; for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];} return a; }
function dealHand(side){ side.hand = side.deck.slice(0,4); side.queueIdx = 4; }
function cycleCard(side,handIdx){
  const played = side.hand[handIdx];
  side.hand[handIdx] = side.deck[side.queueIdx % side.deck.length];
  side.queueIdx++;
  // rotate played back into the deck tail
  side.deck.push(played);
}

// ==========================================================================
// DEPLOY
// ==========================================================================
function canDeploy(side,handIdx){
  const card = side.hand[handIdx];
  if(!card || side.energy < card.cost) return false;
  // spells have an extra per-spell cooldown gate on top of energy
  if(card.type==='spell' && (side.spellCD && side.spellCD[card.spellId]>0)) return false;
  return true;
}
function deploy(side,handIdx,gx,gy){
  const card = side.hand[handIdx];
  if(!card || side.energy < card.cost) return false;
  // SPELL: cast at the point, do NOT spawn a troop. Spells may target anywhere
  // (no own-half restriction -- you cast freeze/strike on the enemy push).
  if(card.type==='spell'){
    if(side.spellCD && side.spellCD[card.spellId]>0) return false; // still recharging
    gx=clamp(gx,1,ARENA_W-1); gy=clamp(gy,1,ARENA_H-1);
    side.energy -= card.cost;
    castSpell(card, side.owner, gx, gy);
    if(!side.spellCD) side.spellCD={};
    side.spellCD[card.spellId] = card.cooldown || 10;
    cycleCard(side,handIdx);
    return true;
  }
  // deploy zone rule: you can only deploy on your own half (+ the bridges)
  if(side.owner===0 && gy < RIVER_Y+RIVER_H/2 + 0.5) gy = RIVER_Y+RIVER_H/2+0.6;
  if(side.owner===1 && gy > RIVER_Y-RIVER_H/2 - 0.5) gy = RIVER_Y-RIVER_H/2-0.6;
  gx = clamp(gx,1,ARENA_W-1);
  side.energy -= card.cost;
  const u = new Unit(card, side.owner, gx, gy);
  u.lane = (gx < ARENA_W/2) ? 0 : 1; // left lane = 0, right lane = 1 (Spec section 1)
  game.units.push(u);
  effects.push(fx('ring',gx,gy,'',card.color,0.5));
  if(side.owner===0){ sfx('deploy'); if(card.isMythic) sfx('bark'); }  // heroes let out a war-cry
  cycleCard(side,handIdx);
  return true;
}

// ==========================================================================
// UPDATE LOOP
// ==========================================================================
function update(dt){
  if(!game) return;
  if(game.phase==='countdown'){ game.cd-=dt; if(game.cd<=0){ game.phase='live'; onMatchLive(); } return; }
  if(game.phase==='ended') return;

  game.time -= dt;                               // REAL countdown -> true 4:00 match
  game.shake = Math.max(0, game.shake - dt*30);  // real-time cosmetic shake decay

  // ---- SECTION CLOCK: the pace ramp is the floor (60/120/180s). Clearing a Gate
  // early pulls the convoy (and the speed-up) forward. section = max(timeTier, gates). ----
  const elapsed  = MATCH_TIME - game.time;
  const timeTier = matchTier(elapsed);
  if(game.convoyMode){
    // time forces the convoy forward if we have not already rolled past this tier
    // (never start a new advance while a pan or a transition beat is still running)
    if(game.phase==='live' && !game.pan.active && !(game.transition&&game.transition.active)
       && timeTier > game.section) advanceSection(false);
  } else {
    // classic single-board pace ramp (kept for non-convoy callers)
    if(timeTier !== game.speedTierIdx){
      game.speedTierIdx = timeTier;
      const L = PHASE_LABELS[timeTier];
      game.phaseAlert = { name:L.name, flavor:L.flavor, ttl:2.6, dur:2.6 };
      sfx(L.sfx); if(timeTier===3) sfx('bark');
    }
  }
  const sec = game.convoyMode ? game.section : timeTier;
  const sp  = TIER_SPEED[sec];
  game.gameSpeed   = sp;
  game.suddenDeath = (sec === 3);

  // PRE-TRANSITION TELEGRAPH: ~10s "NEW PHASE INCOMING" then a 5..1 countdown into each stage change
  if(game.convoyMode && game.section < 3 && !(game.transition && game.transition.active) && !game.pan.active){
    const STAGE_BOUNDS = [45, 90, 135];   // the time floors where stages advance
    const togo = STAGE_BOUNDS[game.section] - elapsed;
    game.phaseIncoming = (togo > 0 && togo <= 10)
      ? { secs: Math.ceil(togo), count: (togo <= 5 ? Math.ceil(togo) : 0) }
      : null;
  } else { game.phaseIncoming = null; }

  // banners decay on REAL dt (district + storm warnings stay readable at 4x)
  if(game.phaseAlert){ game.phaseAlert.ttl -= dt; if(game.phaseAlert.ttl <= 0) game.phaseAlert = null; }
  if(game.stormAlert){ game.stormAlert.ttl -= dt; if(game.stormAlert.ttl <= 0) game.stormAlert = null; }

  // ---- STORM CLOCK + camera pan tick on REAL dt (NOT sim-dt) ----
  updateStorm(dt);
  recomputeEventMods();
  updatePan(dt);

  // ---- MAP TRANSITION beat: tick on REAL dt so the pan + banner always finish.
  // combatScale freezes the whole combat sim (units/towers/storm-strikes/AI/energy)
  // while the camera pans, then warms it back up as the new district settles. ----
  if(game.transition && game.transition.active){
    game.transition.t += dt;
    if(game.transition.t >= game.transition.dur) game.transition.active = false;
  }
  const combatScale = transitionCombatScale();

  const sdt = dt * sp * combatScale;             // simulation time this frame (0 while frozen mid-transition)
  const eMod = game.eventMods ? game.eventMods.energy : 1;   // Zoomies/Overclock energy buff
  game.player.energy   = Math.min(ENERGY_MAX, game.player.energy   + ENERGY_RATE*sdt*eMod);
  game.opponent.energy = Math.min(ENERGY_MAX, game.opponent.energy + ENERGY_RATE*sdt*(0.78+DIFFICULTY*0.052)*eMod);

  computeSynergy(sdt);  // crew-synergy flags + shield regen, scaled to sim time
  tickSpellCooldowns(sdt);   // honors Overclock (-30% spell CD) inside
  // sub-step physics/combat so 4x speed doesn't tunnel units or projectiles
  let rem = sdt; const SUB = 0.05;
  while(rem > 1e-6){
    const s = Math.min(rem, SUB);
    updateUnits(s);
    updateTowers(s);
    updateProjectiles(s);
    updateTraps(s);     // snare traps arm + trigger inside the sub-step
    rem -= s;
  }
  updateAI(sdt);
  updateGoldenHour(sdt);   // objective-zone heal/shield (sim time)
  updateEffects(sdt);
  updateParticles(sdt);

  // tower disable timers + Gate mechanic pulse (sim time)
  [...game.player.towers,...game.opponent.towers].forEach(t=>{
    if(t.hitFlash>0) t.hitFlash-=sdt;
    if(t.disableTimer>0) t.disableTimer-=sdt;
  });

  // remove dead units after their death anim
  game.units = game.units.filter(u=> u.alive || u.deathTimer < 0.45);

  checkWin();
  if(game.time<=0 && game.phase==='live') endMatch();
}

// Fired the instant the countdown ends -> first district banner + opening pace.
function onMatchLive(){
  game.speedTierIdx = 0;
  const L = PHASE_LABELS[0];
  game.phaseAlert = { name:L.name, flavor:L.flavor, ttl:2.6, dur:2.6 };
  sfx(L.sfx);
}

// ---- CREW SYNERGY: count alive units per faction per side, light up the buff ----
// Runs once per tick. Recomputes from scratch so the buff turns ON the moment a
// side has >= SYNERGY_MIN alive same-faction units and turns OFF the moment the
// count drops below it. Sets per-unit flags the combat getters read, regenerates
// the Bone Wall shield, and publishes game.synergy for the HUD/renderer.
function computeSynergy(dt){
  if(!game) return;
  // 1) tally alive units by owner+faction
  const counts = { 0:{}, 1:{} };   // counts[owner][factionId] = aliveCount
  for(const u of game.units){
    if(!u.alive) continue;
    const f = u.card && u.card.faction;
    if(!f) continue;
    const c = counts[u.owner];
    c[f] = (c[f]||0) + 1;
  }
  // 2) flag each alive unit + regenerate its Bone Wall shield while synergy holds
  for(const u of game.units){
    const f = u.card && u.card.faction;
    const active = u.alive && f && (counts[u.owner][f]||0) >= SYNERGY_MIN;
    u.synergy = !!active;
    u.synergyMul = active ? (SYNERGY[f] || null) : null;
    if(active && u.synergyMul && u.synergyMul.shieldPct>0){
      // Bone Wall: top the shield up toward shieldPct of maxHp (regenerates ~1/3 of cap per second)
      const cap = Math.floor(u.maxHp * u.synergyMul.shieldPct);
      if(u.synergyShieldHp < cap){
        u.synergyShieldHp = Math.min(cap, u.synergyShieldHp + cap*(dt||0)/3);
      }
    } else {
      // synergy dropped -> shield bleeds off so the edge is not free forever
      u.synergyShieldHp = 0;
    }
  }
  // 3) publish for the renderer/HUD (only factions actually AT synergy threshold)
  const expose = (c)=>{ const o={}; for(const f in c){ if(c[f]>=SYNERGY_MIN) o[f]=c[f]; } return o; };
  game.synergy = { player: expose(counts[0]), opponent: expose(counts[1]) };
}

function updateUnits(dt){
  for(const u of game.units){
    if(!u.alive){ if(u.deathTimer>=0) u.deathTimer+=dt; continue; }
    u.spawnTime+=dt;
    if(u.abilityCD>0) u.abilityCD-=dt;
    if(u.hitFlash>0) u.hitFlash-=dt;
    if(u.slowTimer>0) u.slowTimer-=dt;
    if(u.dmgBuffT>0) u.dmgBuffT-=dt;
    if(u.evadeT>0) u.evadeT-=dt;
    if(u.invulnT>0) u.invulnT-=dt;
    if(u.silenceT>0) u.silenceT-=dt;
    if(u.muzzle>0) u.muzzle-=dt;
    if(u.snareTimer>0) u.snareTimer-=dt;   // SNARE roots movement (handled in getSpeed); attacks still allowed
    // FREEZE (and stun) = full stop: no move, no attack, no ability. Tick + skip.
    if(u.frozenTimer>0){ u.frozenTimer-=dt; continue; }
    if(u.stunTimer>0){ u.stunTimer-=dt; continue; }
    u.bob+=dt*3;
    // smooth turn
    const ad = ((u.targetAngle - u.angle + Math.PI*3) % (Math.PI*2)) - Math.PI;
    u.angle += ad*Math.min(1,dt*8);
    u.stateTimer+=dt;
    switch(u.state){
      case USTATE.DEPLOY:  stDeploy(u,dt); break;
      case USTATE.MOVE:    stMove(u,dt); break;
      case USTATE.ACQUIRE: stAcquire(u,dt); break;
      case USTATE.WINDUP:  stWindup(u,dt); break;
      case USTATE.ATTACK:  stAttack(u,dt); break;
      case USTATE.RECOVER: stRecover(u,dt); break;
    }
    // passive ability fires off cooldown while moving/fighting
    maybeFireAbility(u);
  }
}
function enter(u,s){ u.state=s; u.stateTimer=0; }
function targetValid(t){ if(!t) return false; if(t instanceof Tower) return !t.destroyed; return t.alive; }

function stDeploy(u,dt){
  const DUR=0.3; u.deployScale=Math.min(1,u.stateTimer/DUR);
  if(u.stateTimer>=DUR){ u.deployScale=1; enter(u,USTATE.MOVE); }
}
function stMove(u,dt){
  if(u.atkCD>0) u.atkCD-=dt;
  findTarget(u);
  if(u.target){
    const hitRange = effRange(u) + (u.target instanceof Tower ? 1.0 : 0.4);
    const d = u.dist(u.target.x,u.target.y);
    if(d<=hitRange){
      if(u.atkCD<=0){ u.acquireTarget=u.target; enter(u,USTATE.ACQUIRE); }
    } else if(!u.card.isStructure){
      moveToward(u,u.target.x,u.target.y,dt);
    }
  } else if(!u.card.isStructure){
    // No valid target: path down THIS unit's lane toward the same-side enemy
    // princess (lane-locked) or the enemy king (crossLane flankers). (Spec section 1.)
    const eTowers=(u.owner===0?game.opponent:game.player).towers;
    let goal=null;
    if(!u.card.crossLane){
      const sidePrinceX=(u.lane===0)?BRIDGE_LX:BRIDGE_RX;
      goal=eTowers.find(t=>t.type==='princess'&&!t.destroyed&&t.x===sidePrinceX)
         || eTowers.find(t=>t.type==='king');
    } else {
      goal=eTowers.find(t=>t.type==='king');
    }
    if(goal) moveToward(u,goal.x,goal.y,dt);
  }
}
function stAcquire(u,dt){
  if(!targetValid(u.acquireTarget)){ u.acquireTarget=null; enter(u,USTATE.MOVE); return; }
  u.targetAngle=Math.atan2(u.acquireTarget.y-u.y,u.acquireTarget.x-u.x);
  if(u.stateTimer>=0.1) enter(u,USTATE.WINDUP);
}
function stWindup(u,dt){
  if(!targetValid(u.acquireTarget)){ u.acquireTarget=null; enter(u,USTATE.MOVE); return; }
  if(u.stateTimer>=0.15) enter(u,USTATE.ATTACK);
}
function stAttack(u,dt){
  if(!targetValid(u.acquireTarget)){ u.acquireTarget=null; enter(u,USTATE.MOVE); return; }
  u.target=u.acquireTarget;
  doAttack(u);
  enter(u,USTATE.RECOVER);
}
function stRecover(u,dt){
  if(u.atkCD>0) u.atkCD-=dt;
  if(u.atkCD<=0){ u.acquireTarget=null; enter(u,USTATE.MOVE); }
}

// Lane band of an x coordinate: left = 0 (x<9), right = 1 (x>=9). (Spec section 1.)
function laneOf(x){ return x < ARENA_W/2 ? 0 : 1; }

// Lane-scoped targeting (Spec section 1):
//  - default units only see enemy units in the SAME lane band; crossLane units see all.
//  - tower targeting picks the SAME-SIDE princess (left unit -> BRIDGE_LX, right -> BRIDGE_RX).
//  - the king is targetable only after a princess falls (existing rule) OR queen_target,
//    and for a lane-locked unit only once ITS same-side princess is down.
// Can attacker hit a unit of this domain? (Combat Spec section 1.)
// A unit may attack a target ONLY if target.domain is in attacker.targets.
// 'both' hits ground + air; 'ground' cannot touch flyers; 'air' only flyers.
function canHitDomain(attackerCard, targetDomain){
  const t = attackerCard.targets || 'ground';
  if(t==='both') return true;
  return t===targetDomain;
}
function findTarget(u){
  u.target=null; let best=Infinity;
  const cross = u.card.crossLane;
  for(const o of game.units){
    if(o.owner===u.owner || !o.alive) continue;
    if(o.card && o.card.type==='spell') continue;          // spells are not board units
    if(!cross && laneOf(o.x)!==u.lane) continue;           // ignore the other lane's brawl
    if(!canHitDomain(u.card, o.card.domain||'ground')) continue; // air vs ground-only: skip
    const d=u.dist(o.x,o.y); if(d<best){ best=d; u.target=o; }
  }
  if(u.target) return;
  const eTowers=(u.owner===0?game.opponent:game.player).towers;
  const princAlive=eTowers.filter(t=>t.type==='princess'&&!t.destroyed).length;
  // the princess on this unit's side of the field
  const sidePrinceX = (u.lane===0) ? BRIDGE_LX : BRIDGE_RX;
  const sidePrince = eTowers.find(t=>t.type==='princess' && !t.destroyed && t.x===sidePrinceX);
  const sidePrinceDown = !sidePrince; // our lane's princess already gone
  for(const t of eTowers){
    if(t.destroyed) continue;
    if(t.type==='princess'){
      // lane-locked units only attack their same-side princess; crossLane units any princess
      if(!cross && t.x!==sidePrinceX) continue;
    } else { // king
      const kingOpen = cross ? (princAlive<2) : sidePrinceDown;
      if(!kingOpen && !u.card.queenTarget) continue;
    }
    const d=u.dist(t.x,t.y); if(d<best){ best=d; u.target=t; }
  }
}

function moveToward(u,tx,ty,dt){
  const onOwnSide = u.owner===0 ? u.y>RIVER_Y : u.y<RIVER_Y;
  const targetCrossSide = u.owner===0 ? ty<RIVER_Y : ty>RIVER_Y;
  const needBridge = onOwnSide && targetCrossSide;
  let mx=tx,my=ty;
  if(u.card.crossLane){
    // flankers may path freely (and pick the nearest bridge to cross).
    if(needBridge){
      const nl=Math.abs(u.x-BRIDGE_LX), nr=Math.abs(u.x-BRIDGE_RX);
      const atBridge = (nl<BRIDGE_W/2+0.5)||(nr<BRIDGE_W/2+0.5);
      if(!atBridge){ mx = nl<nr ? BRIDGE_LX : BRIDGE_RX; my = RIVER_Y + (u.owner===0?-0.3:0.3); }
    }
  } else {
    // lane-locked: hold THIS unit's lane bridge x as the corridor, no diagonal
    // drift to the other lane. Path down the lane, cross at the same-side bridge.
    const laneX = (u.lane===0) ? BRIDGE_LX : BRIDGE_RX;
    if(needBridge){
      const nearBridge = Math.abs(u.x-laneX) < BRIDGE_W/2+0.5;
      if(!nearBridge){ mx = laneX; my = RIVER_Y + (u.owner===0?-0.3:0.3); }
      else { mx = laneX; } // funnel straight across on the lane bridge
    } else {
      // hug the lane corridor: only commit horizontal travel toward the lane x,
      // never toward an x in the other lane.
      if(laneOf(tx)!==u.lane) mx = laneX;
    }
  }
  const dx=mx-u.x,dy=my-u.y,d=Math.hypot(dx,dy);
  if(d>0.05){
    // u.getSpeed() is already tiles/sec at full ramp -- no extra multiplier
    // (the old *2.5 inflation made everyone blitz the middle and huddle).
    const step=Math.min(u.getSpeed()*dt,d);
    u.x+=(dx/d)*step; u.y+=(dy/d)*step;
    u.targetAngle=Math.atan2(dy,dx);
  }
}

// Attack cooldown in seconds. Pack Speed (Zoomie synergy) also speeds up the
// trigger -- a synergy speed multiplier shortens the interval by the same ratio.
function atkInterval(u){
  let spd = u.atkSpd;
  if(u.synergy && u.synergyMul && u.synergyMul.speed>1.0) spd *= u.synergyMul.speed; // faster attack
  // Storm Clock attack-speed hook (no current buff sets it -> 1.0 no-op; kept ready
  // so a future event drops in as one more multiplier layer).
  if(game && game.eventMods && game.eventMods.atkSpeed!==1) spd *= game.eventMods.atkSpeed;
  // TAR SLOW also drags attack speed (-slowMag); legacy ability-slow leaves atk alone.
  if(u.slowTimer>0 && u.slowMag>0) spd *= (1 - u.slowMag);
  return 1/spd;
}

// Effective attack range -- Alley Smog (Storm Clock) shrinks ranged units' range
// (-30%); melee (range 1) is unaffected. (spec sec 2.3.)
function effRange(u){
  let r = u.range;
  if(game && game.eventMods && u.card && u.card.range>=2) r *= game.eventMods.range;
  return r;
}

// SPLASH (Combat Spec section 3): damage every enemy unit within `radius` of
// the impact point (cx,cy), EXCLUDING the primary target (already hit). Honors
// the attacker's domain targeting so a ground-only splasher can't splash flyers.
function applySplash(attackerCard, owner, cx, cy, dmg, radius, primary, color){
  if(!radius || radius<=0) return;
  if(game && game.eventMods && game.eventMods.splash!==1) radius *= game.eventMods.splash; // Storm Surge widens splash
  const enemyOwner = 1-owner;
  for(const o of game.units){
    if(o.owner!==enemyOwner || !o.alive || o===primary) continue;
    if(o.card && o.card.type==='spell') continue;
    if(!canHitDomain(attackerCard, o.card.domain||'ground')) continue;
    if(Math.hypot(o.x-cx, o.y-cy) <= radius){
      o.takeDamage(Math.floor(dmg), cx, cy);
      addBurst(o.x,o.y,color,4);
    }
  }
  effects.push({type:'aoering',x:cx,y:cy,color:color,radius:radius,dur:0.3,t:0});
}

// Branch the attack on the card's weaponType so each kind FEELS different.
// (Spec section 3.) melee = instant slash + impact, no projectile. Everything
// else launches a typed projectile (shape/size/color/speed/trail) that the
// renderer draws differently.
function doAttack(u){
  if(!u.target) return;
  // Damage multiplier stack: ability dmg-buff x crew synergy (Targeting Net) x
  // Storm Clock field buff (Glass Bones), clamped at DMG_CAP (capped-stacking rule).
  let dmgMult = 1;
  if(u.dmgBuffT>0) dmgMult *= 1.2;
  if(u.synergy && u.synergyMul && u.synergyMul.damage!==1.0) dmgMult *= u.synergyMul.damage; // Targeting Net (K9)
  if(game && game.eventMods) dmgMult *= game.eventMods.dmg;                                   // Glass Bones layer
  if(dmgMult > DMG_CAP) dmgMult = DMG_CAP;
  let d=Math.floor(u.dmg * dmgMult);
  const wt=u.card.weaponType;
  const pc=u.card.projColor;
  // muzzle flash on every shot (color = projColor, size by weaponType)
  u.muzzle=0.15;
  const muzzleSize = wt==='cannon'?0.5 : wt==='beam'?0.22 : wt==='lance'?0.3 : 0.32;
  effects.push({type:'muzzle',x:u.x,y:u.y,color:pc,size:muzzleSize,dur:0.12,t:0});
  sfx('atk_'+wt);   // per-weapon attack sound: bullet/cannon/beam/lance/spread/melee

  if(wt!=='melee'){
    // spread = 3 pellets in a small fan; others = single typed projectile
    if(wt==='spread'){
      const baseA=Math.atan2(u.target.y-u.y,u.target.x-u.x);
      const pellet=Math.max(1,Math.floor(d/3));
      for(let i=-1;i<=1;i++){
        const a=baseA+i*0.18, reach=u.range*0.95;
        const tx=u.x+Math.cos(a)*reach, ty=u.y+Math.sin(a)*reach;
        launchProjectile(u.x,u.y,tx,ty,u.card.projSpeed,pellet,u.owner,pc,u.card);
      }
    } else {
      launchProjectile(u.x,u.y,u.target.x,u.target.y,u.card.projSpeed,d,u.owner,pc,u.card);
    }
    u.atkCD=atkInterval(u);
    return;
  }

  // ---- melee: instant slash arc + impact at the target, no projectile ----
  const ang=Math.atan2(u.target.y-u.y,u.target.x-u.x);
  effects.push({type:'slash',x:u.x,y:u.y,angle:ang,color:u.card.accent,dur:0.18,t:0});
  if(u.target instanceof Tower){
    u.target.takeDamage(d);
    effects.push(fx('txt',u.target.x,u.target.y-0.4,'-'+d,PAL.red,0.5));
    sfx('towerhit');
    if(game) game.shake += 4; // tower hit kick (Spec section 4)
    addBurst(u.target.x,u.target.y,pc,IMPACT_COUNT.melee);
    checkTowerDeath(u.target,u.owner);
  } else {
    u.target.takeDamage(d,u.x,u.y);
    effects.push(fx('txt',u.target.x,u.target.y-0.4,'-'+d,PAL.red,0.45));
    addBurst(u.target.x,u.target.y,pc,IMPACT_COUNT.melee);
    // melee splashers ($BCARDD, Crown Foxhound) hit a small radius around the bite
    if(u.card.splash) applySplash(u.card,u.owner,u.target.x,u.target.y,Math.floor(d*0.6),u.card.splashRadius,u.target,pc);
  }
  u.atkCD=atkInterval(u);
}

// Demo abilities: the canon ability NAME shows on screen; the EFFECT is one of a
// categorized set (full per-dog rotation is documented in ability_params.json).
function maybeFireAbility(u){
  if(u.abilityCD>0 || u.silenceT>0 || !u.alive || u.isToken) return; // tokens never fire abilities -> no recursive drone spawning
  const k=u.card.abilityKind;
  const enemyOwner=1-u.owner;
  const announce=(col)=>effects.push(fx('ability',u.x,u.y-0.6,u.card.abilityName,col||PAL.gold,0.9));
  let fired=true;
  switch(k){
    case 'shield':
      u.shieldHp = Math.floor(u.maxHp*0.18); announce(PAL.gold); break;
    case 'buff':
      // $BCARDD's Regal Roar / pack buffs: dmg buff to nearby allies
      game.units.forEach(o=>{ if(o.owner===u.owner&&o.alive&&u.dist(o.x,o.y)<=2.6){ o.dmgBuffT=3; } });
      announce(PAL.gold); break;
    case 'dr': // damage-reduction aura proxy -> small shield to allies
      game.units.forEach(o=>{ if(o.owner===u.owner&&o.alive&&u.dist(o.x,o.y)<=2.2){ o.shieldHp=Math.max(o.shieldHp,Math.floor(o.maxHp*0.08)); } });
      announce('#7B5CFF'); break;
    case 'stun':
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2){ o.stunTimer=1.0; } });
      announce('#FFD200'); break;
    case 'slow':
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.5){ o.slowTimer=2.5; } });
      announce('#00BFFF'); break;
    case 'silence':
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.5){ o.silenceT=1.2; } });
      announce('#9aa'); break;
    case 'heal':
      game.units.forEach(o=>{ if(o.owner===u.owner&&o.alive&&u.dist(o.x,o.y)<=2.2){ o.hp=Math.min(o.maxHp,o.hp+Math.floor(o.maxHp*0.06)); } });
      announce(PAL.ok); break;
    case 'crit':
      u.dmgBuffT=3; announce('#FF8800'); break;
    case 'teleport':
      if(u.target){ const a=u.owner===0?-1:1; u.y+=a*2.0; } announce('#9aa'); break;
    case 'disable_tower': {
      const t=(u.owner===0?game.opponent:game.player).towers.find(t=>!t.destroyed);
      if(t){ t.disableTimer=1.5; } announce('#7B5CFF'); break;
    }
    case 'turret_break':
    case 'pierce':
      u.dmgBuffT=3; announce('#00E0C0'); break;
    case 'spawn':
      // simple drone: a weak fast melee ally
      spawnDrone(u); announce('#00E0C0'); break;
    case 'knockback':
      // shove the struck unit back toward its OWN side (sign was inverted -- it used to pull attackers in)
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=1.8){ const dir=(o.owner===0)?1:-1; o.y=clamp(o.y+dir*1.2,1,ARENA_H-1); } });
      announce('#C9772E'); break;
    case 'evasion': u.evadeT=2; announce('#9aa'); break;
    case 'invuln': u.invulnT=1.0; announce('#9aa'); break;
    case 'aoe':
    case 'chain':
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.0){ o.takeDamage(Math.floor(u.dmg*0.5),u.x,u.y); } });
      announce('#FF8800'); break;
    case 'double':
      if(u.target && targetValid(u.target)){
        if(u.target.takeDamage) u.target.takeDamage(Math.floor(u.dmg*0.5));
        // crown-count a tower killed by Twin Strike (was a silent match-stall: king died, match never ended)
        if(u.target instanceof Tower) checkTowerDeath(u.target,u.owner);
      } announce('#FF2E88'); break;
    default: fired=false;
  }
  if(fired){
    let cd=u.card.abilityCD;
    // Override (Leashbreak synergy): cooldowns refresh ~25% faster -> shorter recharge.
    if(u.synergy && u.synergyMul && u.synergyMul.cdRefresh>1.0) cd/=u.synergyMul.cdRefresh;
    u.abilityCD=cd;
  }
}
function spawnDrone(parent){
  // Hard board cap: a recursive spawn-storm (drones cloned from a Spawner card kept
  // spawning their own drones) ballooned to ~1000 units and froze the phone mid-match.
  // Never let the field grow past what a phone renders at 60fps.
  if(game.units.length >= 140) return;
  const base = CARDS['Pixel Pug'] || parent.card;
  const drone = new Unit(base, parent.owner, parent.x+(Math.random()-0.5), parent.y+(parent.owner===0?-0.6:0.6));
  drone.lane = parent.lane; // drone fights in its spawner's lane
  drone.maxHp=drone.hp=300; drone.dmg=40; // weak token
  drone.isToken=true; drone.abilityCD=Infinity; // a token can NEVER spawn (kills the recursion)
  game.units.push(drone);
}

// Tick down per-side spell cooldowns (Combat Spec section 4).
function tickSpellCooldowns(dt){
  [game.player, game.opponent].forEach(side=>{
    if(!side.spellCD) return;
    for(const k in side.spellCD){ if(side.spellCD[k]>0){ side.spellCD[k]-=dt; if(side.spellCD[k]<0) side.spellCD[k]=0; } }
  });
}

// ==========================================================================
// SPELLS (Combat Spec section 4)
// castSpell applies an area effect at (x,y). card is the engine spell card
// (mapSpellToEngine). owner = caster side. Energy + cooldown handled in deploy.
// ==========================================================================
function castSpell(card, owner, x, y){
  const enemyOwner = 1-owner;
  const r = card.radius || 2.4;
  const dur = card.duration || 0;
  const dmg = card.damage || 0;
  // enemy units inside the area (honors air -- spells hit ground + air alike)
  const inArea = ()=> game.units.filter(o=> o.owner===enemyOwner && o.alive
                       && (!o.card || o.card.type!=='spell')
                       && Math.hypot(o.x-x,o.y-y) <= r );
  const eTowers = (owner===0?game.opponent:game.player).towers;

  switch(card.effect){
    case 'freeze': {
      // STOP: enemies (and towers) in the area freeze for `dur`. Classic reset.
      inArea().forEach(o=>{ o.frozenTimer = Math.max(o.frozenTimer,dur); });
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-x,t.y-y)<=r) t.disableTimer=Math.max(t.disableTimer,dur); });
      effects.push({type:'spell_freeze',x,y,color:'#9fe8ff',radius:r,dur:dur,t:0});
      sfx('ability');
      break;
    }
    case 'slow': {
      // TAR SLOW: -35% move + -35% atk speed for `dur`.
      inArea().forEach(o=>{ o.slowTimer=Math.max(o.slowTimer,dur); o.slowMag=card.slowPct||0.35; });
      effects.push({type:'spell_slow',x,y,color:'#3a2a14',radius:r,dur:dur,t:0});
      sfx('ability');
      break;
    }
    case 'trap': {
      // SNARE TRAP: plant a hidden, armed trap. Triggers on enemy cross -> root + dmg.
      game.traps.push({ owner:owner, x:x, y:y, radius:r, dmg:dmg, duration:dur,
                        armT:0.5, triggered:false, life:0 });
      effects.push({type:'spell_trap_set',x,y,color:'#00E0C0',radius:r,dur:0.6,t:0});
      sfx('ability');
      break;
    }
    case 'zap': {
      // JOLT: instant AOE damage + 0.5s stun. Kills swarms, resets attacks.
      inArea().forEach(o=>{ o.takeDamage(dmg,x,y); o.stunTimer=Math.max(o.stunTimer,dur||0.5); addBurst(o.x,o.y,'#7fefff',5); });
      effects.push({type:'spell_zap',x,y,color:'#9fe8ff',radius:r,dur:0.4,t:0});
      if(game) game.shake += 3;
      sfx('ability');
      break;
    }
    case 'strike': {
      // STRIKE: medium AOE burst damage (the fireball). Hits units AND towers.
      inArea().forEach(o=>{ o.takeDamage(dmg,x,y); addBurst(o.x,o.y,'#FF8800',7); });
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-x,t.y-y)<=r){ t.takeDamage(Math.floor(dmg*0.5)); checkTowerDeath(t,owner); } });
      effects.push({type:'spell_strike',x,y,color:'#ff7b2c',radius:r,dur:0.45,t:0});
      if(game) game.shake += 6;
      sfx('ability'); sfx('tower_hit');
      break;
    }
    default: break;
  }
}

// SNARE TRAP update: arm after a short delay, then trigger when the FIRST enemy
// crosses the radius -> root (snareTimer) + small damage to everyone caught.
// A triggered trap lingers `duration` then expires. Untriggered traps persist.
function updateTraps(dt){
  if(!game || !game.traps || !game.traps.length) return;
  for(const tr of game.traps){
    if(tr.armT>0){ tr.armT-=dt; continue; }   // arming window
    if(!tr.triggered){
      const enemyOwner = 1-tr.owner;
      let crossed=false;
      for(const o of game.units){
        if(o.owner!==enemyOwner || !o.alive) continue;
        if(o.card && o.card.type==='spell') continue;
        if(Math.hypot(o.x-tr.x,o.y-tr.y) <= tr.radius){ crossed=true; break; }
      }
      if(crossed){
        tr.triggered=true; tr.life=0;
        // root + damage every enemy in the radius
        for(const o of game.units){
          if(o.owner!==enemyOwner || !o.alive) continue;
          if(o.card && o.card.type==='spell') continue;
          if(Math.hypot(o.x-tr.x,o.y-tr.y) <= tr.radius){
            o.snareTimer=Math.max(o.snareTimer,tr.duration||1.6);
            o.takeDamage(tr.dmg||0,tr.x,tr.y);
            addBurst(o.x,o.y,'#00E0C0',5);
          }
        }
        effects.push({type:'spell_trap_fire',x:tr.x,y:tr.y,color:'#00E0C0',radius:tr.radius,dur:0.5,t:0});
        if(game) game.shake += 2;
        sfx('ability');
      }
    } else {
      tr.life += dt;
    }
  }
  // drop triggered traps after they finish + a tiny grace; keep armed ones
  game.traps = game.traps.filter(tr=> !tr.triggered || tr.life < (tr.duration||1.6)+0.3 );
}

// District Gate mini-boss pulse (G4.0) -- a periodic faction mechanic that reuses
// the existing shield / zap / disable_tower effect paths. Only acts when engaged
// (a player unit has pushed into the enemy half) so the opening stays fair.
function tickGateMechanic(t, dt){
  if(t.gateCD>0){ t.gateCD-=dt; return; }
  const engaged = game.units.some(u=>u.owner===0 && u.alive && u.y < RIVER_Y+4);
  if(!engaged) return;
  t.gateCD = 7;
  if(t.gateMech==='shield'){
    t.gateShield = Math.floor(t.maxHp*0.10);
    effects.push(fx('ability', t.x, t.y-1, 'GATE SHIELD', PAL.gold, 0.9));
  } else if(t.gateMech==='disable'){
    const pts = game.player.towers.filter(x=>!x.destroyed);
    if(pts.length){ const tt=pts[Math.floor(Math.random()*pts.length)]; tt.disableTimer=Math.max(tt.disableTimer,2.0);
      effects.push(fx('ability', t.x, t.y-1, 'GATE OVERRIDE', '#7B5CFF', 0.9)); }
  } else { // 'zap'
    let best=null,bd=8; game.units.forEach(u=>{ if(u.owner===0&&u.alive){ const d=Math.hypot(u.x-t.x,u.y-t.y); if(d<bd){bd=d;best=u;} } });
    if(best){ best.takeDamage(Math.floor(t.dmg*1.6), t.x, t.y); best.stunTimer=Math.max(best.stunTimer,0.4);
      addBurst(best.x,best.y,'#9fe8ff',6); effects.push(fx('ability', t.x, t.y-1, 'GATE ZAP', '#9fe8ff', 0.9)); }
  }
}

function updateTowers(dt){
  for(const t of [...game.player.towers,...game.opponent.towers]){
    if(t.isGate && !t.destroyed) tickGateMechanic(t, dt);
    if(t.destroyed || !t.active || t.disableTimer>0) continue;
    t.atkCD-=dt; if(t.atkCD>0) continue;
    // Alley Smog (Storm Clock) trims tower range -30% while active.
    let tgt=null,bd=t.range*((game&&game.eventMods)?game.eventMods.range:1);
    for(const u of game.units){
      if(u.owner===t.owner || !u.alive) continue;
      const d=Math.hypot(u.x-t.x,u.y-t.y); if(d<bd){ bd=d; tgt=u; }
    }
    if(tgt){
      launchProjectile(t.x,t.y,tgt.x,tgt.y,7,t.dmg,t.owner,t.owner===0?PAL.blue:PAL.red);
      t.atkCD=1/t.atkSpd;
    }
  }
}

// ---- PROJECTILES (parabolic arc, v8 pattern) ----
// `card` (optional) supplies the visual contract: shape/size/projSpeed and
// whether the bolt leaves a trail. Towers pass shape:'dot'. (Spec section 3/5.)
function launchProjectile(fx0,fy0,tx,ty,speed,dmg,owner,color,card){
  const dx=tx-fx0,dy=ty-fy0,dist=Math.hypot(dx,dy);
  const wt = card ? card.weaponType : 'dot';
  // time-of-flight scales inversely with the weapon's projSpeed so cannons lob
  // slowly and beams/lances feel near-instant. Falls back to the old formula.
  const eff = (card && card.projSpeed) ? card.projSpeed : speed;
  const tof=Math.max(0.05,dist/(eff*2.2));
  // beams/lances fly flat; lobs (cannon/tower) arc. Trail on fast bolts.
  const flat = (wt==='beam'||wt==='lance');
  const arcH = flat ? 0 : Math.min(dist*0.35,3);
  const shape = card ? card.projShape : 'dot';
  const size  = card ? card.projSize  : 0.14;
  const trail = (wt==='bullet'||wt==='lance'||wt==='beam');
  projectiles.push({
    x:fx0,y:fy0,z:0,sx:fx0,sy:fy0,tx,ty,
    vx:dx/tof,vy:dy/tof,vz:arcH/tof*4,grav:arcH/tof/tof*8,
    t:0,tof,dmg,owner,color,alive:true,
    shape,size,trail,speed:eff,weaponType:wt,
    // carry the firing card so impact can honor splash + domain targeting
    card: card||null,
    splash: !!(card && card.splash), splashRadius: card?card.splashRadius:0,
    targets: card ? (card.targets||'both') : 'both'
  });
}
function updateProjectiles(dt){
  for(const p of projectiles){
    if(!p.alive) continue;
    p.t+=dt;
    p.x=p.sx+p.vx*p.t; p.y=p.sy+p.vy*p.t;
    p.z=p.vz*p.t-0.5*p.grav*p.t*p.t;
    if(p.t>=p.tof || p.z<-0.1){
      p.alive=false;
      // hit nearest enemy unit at impact, else towers in radius
      const enemyOwner=1-p.owner;
      const projTargets = p.targets || 'both';
      let best=null,bd=1.4;
      for(const u of game.units){
        if(u.owner!==enemyOwner||!u.alive) continue;
        if(u.card && u.card.type==='spell') continue;
        // honor the shooter's domain targeting (e.g. ground-only ranged can't tag air)
        if(projTargets!=='both' && projTargets!==(u.card.domain||'ground')) continue;
        const d=Math.hypot(u.x-p.tx,u.y-p.ty); if(d<bd){ bd=d; best=u; }
      }
      const cnt = IMPACT_COUNT[p.weaponType] || 5;
      if(best){ best.takeDamage(p.dmg,p.sx,p.sy); effects.push(fx('txt',best.x,best.y-0.4,'-'+p.dmg,PAL.red,0.4)); }
      // SPLASH: cannon/spread/identity-splash projectiles damage a radius on impact
      if(p.splash && p.card){ applySplash(p.card,p.owner,p.tx,p.ty,Math.floor(p.dmg*0.6),p.splashRadius,best,p.color); }
      const eTowers=(p.owner===0?game.opponent:game.player).towers;
      let hitTower=false;
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-p.tx,t.y-p.ty)<=1.3){ t.takeDamage(p.dmg); sfx('towerhit'); hitTower=true; checkTowerDeath(t,p.owner); } });
      if(hitTower && game) game.shake += 4;            // tower hit kick (Spec section 4)
      if(p.weaponType==='cannon' && game) game.shake += 3; // heavy cannon impact (Spec section 4)
      // impact particles colored by the projectile, count by weaponType
      addBurst(p.tx,p.ty,p.color,cnt);
    }
  }
  projectiles=projectiles.filter(p=>p.alive);
}

// ---- AI (v8 deploy heuristic, adapted) ----
function updateAI(dt){
  const ai=game.opponent;
  ai.aiCD+=dt;
  if(ai.aiCD < ai.aiNext) return;
  // deploy cadence scales with difficulty: easy = slow (~3.5s avg), hardest = fast (~1.4s avg)
  ai.aiCD=0; ai.aiNext=Math.max(1.0,(4.6-DIFFICULTY*0.36))+Math.random()*1.3;  // D0 ~5s (sluggish, easy) -> D9 ~2s (aggressive)
  // On easy tiers the AI also plays dumb: random card, not the best counter.
  if(DIFFICULTY<=2 && Math.random()<0.6){ ai.aiNext+=1.2; }
  const playable=[];
  ai.hand.forEach((c,i)=>{ if(c && ai.energy>=c.cost) playable.push({i,c}); });
  if(!playable.length) return;
  // The AI commits to ONE lane and stacks it (like a human pushing a side),
  // re-rolling occasionally. (Spec section 1: AI picks a lane and sticks to it.)
  if(ai.aiLane===undefined || Math.random()<0.15) ai.aiLane = Math.random()<0.5?0:1;
  const laneBridge = ai.aiLane===0 ? BRIDGE_LX : BRIDGE_RX;
  // react to player threats, but ONLY ones in the lane the AI is defending
  const threats=game.units.filter(u=>u.owner===0 && u.y<RIVER_Y+3 && laneOf(u.x)===ai.aiLane);
  let pick,gx,gy;
  if(threats.length){
    pick=playable.sort((a,b)=>(b.c.dmg||b.c.damage||0)-(a.c.dmg||a.c.damage||0))[0];
    const t=threats[0];
    // jitter stays inside the lane band so the deploy keeps the chosen lane
    gx=clamp(laneBridge+(Math.random()-0.5)*2,1,ARENA_W-1); gy=clamp(t.y-2.5,2,RIVER_Y-2);
  } else {
    pick=playable[Math.floor(Math.random()*playable.length)];
    gx=clamp(laneBridge+(Math.random()-0.5)*2,1,ARENA_W-1); gy=4+Math.random()*4;
  }
  // If the AI happens to hold a SPELL, cast it on the player's densest cluster
  // (on the AI's side of the river) rather than "deploying" it as a troop.
  if(pick.c.type==='spell'){
    if(canDeploy(ai,pick.i) && threats.length){
      const t=threats[0]; deploy(ai,pick.i,t.x,t.y);
    }
    return; // skip if on cooldown or no good target this beat
  }
  deploy(ai,pick.i,gx,gy);
}

// ---- WIN / CROWNS ----
function checkTowerDeath(t,attackerOwner){
  if(!t.destroyed || t.crownCounted) return;
  t.crownCounted=true;
  if(game) game.shake += 12; // tower destroyed = big kick (Spec section 4)
  // ---- CONVOY: enemy king = the District Gate; player king down = defeat ----
  if(game.convoyMode){
    if(t.type==='king' && t.owner===1 && attackerOwner===0){
      game.player.crowns += 1; game.stars=(game.stars||0)+1;     // Gate cleared +1 + a star
      game.gateClearedThisSection = true;
      game.gatesCleared = Math.max(game.gatesCleared, game.section+1);
      addBurst(t.x,t.y,PAL.gold,18);
      effects.push(fx('crown',t.x,t.y-1,'GATE DOWN',PAL.gold,1.5));
      grantGateReward();
      if(game.section >= 3) cleanSweepWin();   // all 4 Gates cleared -> CLEAN SWEEP
      else advanceSection(true);               // roll on early (pulls the speed-up forward)
      return;
    }
    if(t.type==='king' && t.owner===0){        // player king down = run over
      game.opponent.crowns = Math.max(game.opponent.crowns,3);
      endMatch(); return;
    }
    // princess (either side): +1 crown, activate that side's king, but NEVER end on
    // 3 crowns (only a Gate/king/clock decides a convoy run).
    const atk = attackerOwner===0 ? game.player : game.opponent;
    atk.crowns++;
    addBurst(t.x,t.y,attackerOwner===0?PAL.blue:PAL.red,16);
    effects.push(fx('crown',t.x,t.y-1,attackerOwner===0?'CROWN!':'TOWER DOWN',PAL.gold,1.4));
    const def = attackerOwner===0 ? game.opponent : game.player;
    const king=def.towers.find(tt=>tt.type==='king');
    if(king && !king.active) king.active=true;
    return;
  }
  // ---- CLASSIC single-board crown logic ----
  const atk = attackerOwner===0 ? game.player : game.opponent;
  if(t.type==='king'){ atk.crowns=3; }
  else { atk.crowns++; }
  addBurst(t.x,t.y,attackerOwner===0?PAL.blue:PAL.red,16);
  effects.push(fx('crown',t.x,t.y-1,attackerOwner===0?'CROWN!':'TOWER DOWN',PAL.gold,1.4));
  // activate defender king when a princess falls
  const def = attackerOwner===0 ? game.opponent : game.player;
  const king=def.towers.find(tt=>tt.type==='king');
  if(king && !king.active) king.active=true;
  if(atk.crowns>=3) endMatch();
}
// Neutral tower death (map hazard) -- no crown awarded to anyone.
function checkTowerDeathNeutral(t){
  if(!t.destroyed || t.crownCounted) return;
  t.crownCounted=true;
  if(game) game.shake += 10;
  if(game.convoyMode && t.type==='king'){
    if(t.owner===0){ game.opponent.crowns=Math.max(game.opponent.crowns,3); endMatch(); return; }
    game.player.crowns += 1; game.stars=(game.stars||0)+1;
    game.gateClearedThisSection=true; game.gatesCleared=Math.max(game.gatesCleared,game.section+1);
    grantGateReward();
    if(game.section>=3) cleanSweepWin(); else advanceSection(true);
    return;
  }
  const ownerSide = t.owner===0?game.player:game.opponent;
  const king = ownerSide.towers.find(k=>k.type==='king');
  if(king && !king.active) king.active=true;
}
function checkWin(){
  if(game.convoyMode) return;   // convoy end-conditions handled in checkTowerDeath + clock
  const pk=game.player.towers.find(t=>t.type==='king');
  const ok=game.opponent.towers.find(t=>t.type==='king');
  if(pk && pk.destroyed && !pk.crownCounted){ pk.crownCounted=true; game.opponent.crowns=3; endMatch(); }
  if(ok && ok.destroyed && !ok.crownCounted){ ok.crownCounted=true; game.player.crowns=3; endMatch(); }
}
function endMatch(){
  if(game.phase==='ended') return;
  game.phase='ended';
  if(game.player.crowns>game.opponent.crowns) game.result='win';
  else if(game.opponent.crowns>game.player.crowns) game.result='lose';
  else {
    // tiebreak on remaining tower HP
    const ph=game.player.towers.reduce((s,t)=>s+(t.destroyed?0:t.hp),0);
    const oh=game.opponent.towers.reduce((s,t)=>s+(t.destroyed?0:t.hp),0);
    game.result = ph>oh?'win':oh>ph?'lose':'draw';
  }
  sfx(game.result==='win'?'win':'lose');
}

// ---- EFFECTS + PARTICLES ----
function fx(type,x,y,text,color,dur){ return {type,x,y,text,color,dur:dur||1,t:0}; }
function updateEffects(dt){ effects.forEach(e=>{e.t+=dt; if(e.type==='txt'||e.type==='ability'||e.type==='crown') e.y-=dt*0.6;}); effects=effects.filter(e=>e.t<e.dur); }
function addBurst(x,y,color,n){ for(let i=0;i<n;i++){ const a=Math.random()*Math.PI*2,s=1+Math.random()*3; particles.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,t:0,dur:0.4+Math.random()*0.3,color,sz:0.06+Math.random()*0.05}); } }
function updateParticles(dt){ particles.forEach(p=>{p.t+=dt;p.x+=p.vx*dt*1.5;p.y+=p.vy*dt*1.5;}); particles=particles.filter(p=>p.t<p.dur); if(particles.length>240) particles=particles.slice(-240); }

// ---- AUDIO (WebAudio, no assets) ----
let AC=null;
function getAC(){ if(!AC){ try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){} } return AC; }
function tone(f,type,dur,vol,fEnd){ const ac=getAC(); if(!ac) return; try{ const o=ac.createOscillator(),g=ac.createGain(); o.connect(g);g.connect(ac.destination); o.type=type||'sine'; o.frequency.setValueAtTime(f,ac.currentTime); if(fEnd)o.frequency.exponentialRampToValueAtTime(Math.max(20,fEnd),ac.currentTime+dur); g.gain.setValueAtTime(vol||0.18,ac.currentTime); g.gain.exponentialRampToValueAtTime(0.001,ac.currentTime+dur); o.start(); o.stop(ac.currentTime+dur+0.03);}catch(e){} }
// ---- sample SFX (ElevenLabs mp3s in assets/sfx/), with synth-tone fallback ----
const SFX_BUF = {};   // name -> decoded AudioBuffer
const SFX_NAMES = ['deploy','atk_bullet','atk_cannon','atk_beam','atk_lance','atk_spread','atk_melee','death','tower_hit','tower_down','ability','win','lose','bark'];
let _sfxLoaded = false;
function loadAllSfx(){
  if(_sfxLoaded) return; _sfxLoaded = true;
  const ac = getAC(); if(!ac || typeof fetch === 'undefined') return;  // node stub / no audio -> skip
  SFX_NAMES.forEach(n=>{
    fetch('assets/sfx/'+n+'.mp3').then(r=> r.ok ? r.arrayBuffer() : Promise.reject(0))
      .then(buf=> ac.decodeAudioData(buf)).then(b=>{ SFX_BUF[n]=b; }).catch(()=>{});
  });
}
function playSample(name){
  const ac=getAC(), b=SFX_BUF[name];
  if(!ac || !b) return false;
  try{ const s=ac.createBufferSource(); s.buffer=b; const g=ac.createGain();
    g.gain.value=0.55; s.connect(g); g.connect(ac.destination); s.start(); return true; }catch(e){ return false; }
}
// engine event name -> sample file, then play the sample or fall back to the synth tone
function sfx(name){
  const file = name==='shoot' ? 'atk_bullet' : name==='towerhit' ? 'tower_hit' : name;
  if(playSample(file)) return;                     // real sample if loaded
  if(name==='deploy') tone(280,'sawtooth',0.14,0.18,120);
  else if(name==='shoot' || name.indexOf('atk_')===0) tone(520,'sawtooth',0.1,0.12,200);
  else if(name==='towerhit' || name==='tower_hit') tone(60,'sine',0.16,0.3,32);
  else if(name==='tower_down') tone(48,'sine',0.4,0.34,24);
  else if(name==='death') tone(120,'sawtooth',0.22,0.18,30);
  else if(name==='ability') tone(700,'triangle',0.18,0.16,1100);
  else if(name==='bark') tone(180,'sawtooth',0.18,0.22,90);
  else if(name==='win') [392,523,659,784].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.4,0.22,f*1.01),i*130));
  else if(name==='lose') [392,329,261,196].forEach((f,i)=>setTimeout(()=>tone(f,'sine',0.4,0.18,f*0.95),i*170));
}

function clamp(v,lo,hi){ return Math.max(lo,Math.min(hi,v)); }

// ==========================================================================
// PUBLIC API (consumed by index.html renderer)
// ==========================================================================
global.AK = {
  PAL, RARITY_COL, FACTION_COL,
  ARENA_W, ARENA_H, RIVER_Y, RIVER_H, BRIDGE_LX, BRIDGE_RX, BRIDGE_W,
  ENERGY_MAX, MATCH_TIME, USTATE, TOWER_STATS,
  SYNERGY, SYNERGY_MIN,   // crew-synergy table + threshold (renderer reads labels/multipliers for the HUD glow)
  STARTER_DECK_NAMES,
  // ---- convoy + storm (renderer reads these for assets, codex, HUD) ----
  SECTIONS, STORM_CATALOG, PHASE_LABELS, TIER_SPEED,
  getStorm(){ return game ? game.storm : null; },
  getCamera(){ return game ? game.camera : {offX:0,offY:0,zoom:1}; },
  triggerStorm(key){ if(game) triggerStormEvent(key); },     // debug/affix hook
  init(){ CARDS = buildCardIndex(); buildSpellIndex(); return { cards:CARDS, count:Object.keys(CARDS).length, spells:Object.keys(SPELLS).length }; },
  getCards(){ return CARDS; },
  getSpells(){ return SPELLS; },                 // spellId/name -> engine spell card
  getStarterDeck(){ return STARTER_DECK_NAMES.map(n=>CARDS[n]).filter(Boolean); },
  // castSpellAt(spellIdOrName, owner, x, y): direct cast (used by the renderer's
  // spell reticle path AFTER deploy() has charged energy + set cooldown; this is
  // the low-level apply). Most casts go through deploy() which routes spells here.
  castSpellAt(spellKey, owner, x, y){ const s=SPELLS[spellKey]; if(s) castSpell(s, owner|0, x, y); },
  newMatch, deploy, canDeploy, update,
  get game(){ return game; },
  get effects(){ return effects; },
  get projectiles(){ return projectiles; },
  get particles(){ return particles; },
  resumeAudio(){ const ac=getAC(); if(ac && ac.state==='suspended') ac.resume(); loadAllSfx(); },
  setDifficulty(n){ DIFFICULTY = Math.max(0, Math.min(9, n|0)); return DIFFICULTY; }
};

})(typeof window!=='undefined'?window:globalThis);
