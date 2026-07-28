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
// AK-RIGTM 2026-07-18: real-world car marque retired to 'Sport' across canon.js + both
// cards.json copies. Glyph 'S' unchanged. Matches the 'sport' family in art/build_asset_prompts.py.
const RIG_GLYPH = { 'Muscle Car':'M', 'Sport':'S', 'Van':'V', 'Monster Truck':'T' };

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
// AK-FEEL B6: energy curve -- BOTH sides start at 0, regen ticks on REAL dt
// (not sim-speed dt) with a per-section multiplier so the late game accelerates
// deploys without the hidden 4x sim-speed regen hack.
const ENERGY_MAX = 10, ENERGY_RATE = 1/1.8, START_ENERGY = 0;
const ENERGY_SECTION_MULT = [1.0, 1.2, 1.4, 2.0];   // AK-FEEL B6: regen mult per convoy section
// AK-FEEL B2/B3/B4: combat-feel constants (COMBAT_FEEL_SPEC verbatim)
const ENGAGE_STOP = 0.95, ENGAGE_RESUME = 1.10;     // stop-at-range hysteresis bands
const SEP_ITERATIONS = 4, SEP_MAX_PUSH = 0.55;      // AK-SEP4 2026-06-15: 2->4 relax passes + 0.35->0.55 budget so DENSE funnels toward a tower fully clear -- marching troops never walk THROUGH each other (operator: "they should walk around or wait, never overlap")
// AK-SEP3 2026-06-15: units were separating by colR (0.35-0.75) but DRAWN at ~0.78 radius
// (baseR), so tokens overlapped/clumped (operator: "cards aren't accounting for card size +
// tile spacing... hard to see which is fighting which"). Floor unit-vs-unit separation to a
// VISUAL radius so the drawn tokens keep a real gap. Combat ranges (effRange) are unchanged.
const SEP_VIS_R = 0.92;   // AK-SEP3 bump 2026-06-15: drawn token radius ~0.85 -> 0.92 keeps a real GAP (no overlap, "always a little space" per operator)
const KB_TAU = 0.06;                                 // knockback velocity decay time constant (impulse plays out over ~0.12s)
const HIT_STOP = 0.06;                               // melee hit-stop freeze (both units) -- AK-JUICE 2026-06-18: 0.04->0.06 punchier impact (webgl decision Phase-0 #4)
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
  { idx:1, name:"MARKIN' TERRITORY",   district:'Neon Night', pace:1.0,  diff:3, garrison:'Zoomie Syndicate',affix:'zoomies',     gateLabel:'NEON RUNNER',   panDir:'up'     },
  { idx:2, name:"OFF THE LEASH",       district:'Industrial', pace:2.0,  diff:5, garrison:'Leashbreak Tactix',affix:'overclock',  gateLabel:'IRON HANDLER',  panDir:'right'  },
  { idx:3, name:"THAT'S MY SQUIRREL!", district:'Rain Docks', pace:4.0,  diff:7, garrison:'K9 Circuitry',    affix:'storm_surge', gateLabel:'DOCK SOVEREIGN',panDir:'upleft' }
];

// AK-STORY (contract L8.1): the 4 in-match district hook lines (STORYLINE_CANON
// section 11), engine SECTIONS order. The transition showpiece RIDE beat reads
// SECTION_HOOKS[next] into tr.show.rideFlavor -- the destination's one-line act
// flavor over the convoy handoff. Canon source of truth (exported via AK so the
// codex + index render the SAME strings, never a hand-copied blob). No em-dashes.
const SECTION_HOOKS = [
  "Born in this dirt. Don't you die in it.",                       // The Lot
  "Pretty lights. Ugly teeth behind them.",                        // Neon Night
  "They forge chains here. And the dogs that break them.",         // Industrial
  "Everything ships out of these docks. Slip, and so do you."      // Rain Docks
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
// AK-RESPAWN: enemy survivor respawn line entering the finale (mirror of 25.0).
const ENEMY_BACKLINE_Y = 5.0;   // AK-FEEL

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

// ---- AK-SYNERGY: NAMED SYNERGY TABLE v1 (Merge-Tactics layer) ----
// Activation = ALL listed members ALIVE on that side's field at the same time,
// recomputed every tick (computeNamedSynergy inside computeSynergy) so a buff
// drops the instant a member dies. SYMMETRIC: the AI side earns the exact same
// combos. Buffs ride the EXISTING multiplier stacks (getSpeed / doAttack /
// atkInterval / effRange / the synergy-shield pool) and stay under MOVE_CAP /
// DMG_CAP, so the whole layer lives inside the established power budget.
// Stacks BESIDE the faction-count crew synergy above, never replaces it.
// `req` + `effect` are display strings for the Deck Lab reference list.
const NAMED_SYNERGY = [
  { id:'alpha_pack',   label:'ALPHA PACK',     hint:'Alpha leads the pack.',      req:'$BCARDD + 2 other Boneguard',    effect:'Boneguard +10% damage' },
  { id:'shield_wall',  label:'SHIELD WALL',    hint:'Bone to bone.',              req:'2+ Vanguards',                   effect:'Vanguards +12% max-HP shield' },
  { id:'zoomie_train', label:'ZOOMIE TRAIN',   hint:"Can't catch the train.",     req:'3+ Very Fast units',             effect:'Those units +12% move' },
  { id:'turret_net',   label:'TURRET NET',     hint:'Overlapping fire.',          req:'2+ Structures',                  effect:'Structures +15% attack speed' },
  { id:'spotter',      label:'SPOTTER',        hint:'Target painted.',            req:'Hacker + Blaster',               effect:'Blasters +0.5 range' },
  { id:'street_medics',label:'STREET MEDICS',  hint:'Corner clinic is open.',     req:'2+ Supports',                    effect:'Allies within 3 tiles heal 1% max HP/s' },
  { id:'skewer_line',  label:'SKEWER LINE',    hint:'Hold the line of lances.',   req:'2+ Lancers',                     effect:'Lancers +10% damage' },
  { id:'chaos_crew',   label:'CHAOS CREW',     hint:'Whole block pulls up.',      req:'1+ alive from all 4 factions',   effect:'ALL units +5% damage, +5% move' },
  { id:'pup_swarm',    label:'PUP SWARM',      hint:'Strength in strays.',        req:'3+ units of cost 3 or less',     effect:'Those units +10% move' },
  { id:'big_dog',      label:'BIG DOG ENERGY', hint:'Heavyweights on the field.', req:'2+ Epic-or-better units',        effect:'Those units +8% damage' },
  // AK-CLASS: class-keyed combo expansion (TAXONOMY_DESIGN 3, wave 7 L2).
  // Same contract as the ten above: recomputed every tick, symmetric for the
  // AI, applied through the ns* layers under MOVE_CAP / DMG_CAP.
  { id:'bruiser_wall',     label:'KNUCKLE UP',       hint:'Frontline holds the block.',  req:'3+ Bruisers alive',                effect:'Bruisers +10% max-HP shield' },
  { id:'hit_squad',        label:'HIT SQUAD',        hint:'Contracts get finished.',     req:'2+ Assassins alive',               effect:'Assassins +10% move, +6% damage' },
  { id:'street_sorcery',   label:'STREET SORCERY',   hint:'The block runs on signal.',   req:'2+ Casters alive',                 effect:'Caster cooldowns refresh 15% faster' },
  { id:'firing_line',      label:'FIRING LINE',      hint:'Pick a window. Any window.',  req:'2+ Marksmen alive',                effect:'Marksmen +0.5 range' },
  { id:'puppy_mill',       label:'PUPPY MILL',       hint:'Numbers win wars.',           req:'2+ Summoners alive',               effect:'Friendly tokens +15% damage' },
  { id:'full_battery',     label:'FULL BATTERY',     hint:'The grid is humming.',        req:'Pylon + 2+ other Structures',      effect:'Structures +15% attack speed' },
  { id:'lock_and_key',     label:'LOCK AND KEY',     hint:'Hold them. Cut them.',        req:'Lockdown structure + 1+ Assassin', effect:'Assassins +15% damage vs locked targets' },
  { id:'dead_air',         label:'DEAD AIR',         hint:'Nobody calls for backup.',    req:'2+ Silence-subtype units',         effect:'Silence and jam durations +50%' },
  { id:'bodyguard_detail', label:'BODYGUARD DETAIL', hint:'Medics walk untouched.',      req:'1+ Bruiser + 2+ Supports',         effect:'Supports take 15% less damage' },
  { id:'wrecking_crew',    label:'WRECKING CREW',    hint:'Bring the walls down.',       req:'Structure + 1+ turret-breaker',    effect:'Those units +15% damage vs towers' },
  // AK-CLASS: the 11th is ACCOUNT-FLAVORED -- lights only when the L6 nemesis
  // (a named rival unit) is on the enemy field. Two accounts can never share it.
  { id:'grudge_match',     label:'GRUDGE MATCH',     hint:'This one is personal.',       req:'Your nemesis on the enemy field',  effect:'ALL your units +5% damage' }
];
const NAMED_SYNERGY_BY_ID = {};
NAMED_SYNERGY.forEach(s=>{ NAMED_SYNERGY_BY_ID[s.id]=s; });
const NS_HEAL_R = 3.0, NS_HEAL_PCT = 0.01;                 // Street Medics aura radius (tiles) + heal rate (maxHp/s)
const NS_BIG_RARITY = { Epic:1, Legendary:1, Mythic:1 };   // "Epic or better" for BIG DOG ENERGY
const NS_ALL_FACTIONS = ['boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry'];

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

// ==========================================================================
// AK-CLASS: THE CLASS LAYER (Wave 7 lane L2, TAXONOMY_DESIGN 1-2).
// CLASS is a NEW axis on top of ROLE: role keeps driving the AK-FEEL range
// band; class drives the class-keyed synergy combos, the structure-family
// archetype split, archetype detection and badge text. The canonical sidecar
// is game/classes.js (per-cardNumber map derived from the same family table);
// this interim CLASS_BY_FAMILY constant keeps the engine fully classified
// when the sidecar is absent (headless harness) until the canon merge lands
// combatClass in cards.json. A probe asserts sidecar === fallback.
// ==========================================================================
const CLASS_BY_FAMILY = {
  'Crownbreaker':'BRUISER','Armor Pulse':'BRUISER','Haymaker':'BRUISER',
  'Overclock Rage':'BRUISER','Bodywall':'BRUISER','Brawler':'BRUISER',
  'Shock Push':'BRUISER','Fortify':'SUPPORT','Grav Pull':'BRUISER',
  'Shield Bark':'SUPPORT','Bitechain':'BRUISER','Stonehide':'BRUISER',
  'Shadow Fang':'ASSASSIN','Pierce Rush':'MARKSMAN','Twin Strike':'ASSASSIN',
  'Dash Loop':'ASSASSIN','Blink Bite':'ASSASSIN','Sidecut':'ASSASSIN',
  'Spark Pups':'SUMMONER','Signal Scramble':'CASTER','Slipstream':'ASSASSIN',
  'Burst Bite':'ASSASSIN','Tag Boost':'SUPPORT','Tracer Round':'MARKSMAN',
  'Leashbreak':'CASTER','Hack Jam':'CASTER','Blackout':'CASTER',
  'Barrier Ring':'SUPPORT','Heal Beacon':'SUPPORT','Frost Bark':'CASTER',
  'Shatter':'CASTER','Tag Shot':'MARKSMAN','Phase':'ASSASSIN',
  'Echo Howl':'CASTER','Ping':'CASTER','Soothe':'SUPPORT',
  'Royal Hunt':'ASSASSIN','Drone Swarm':'SUMMONER','Overclock':'STRUCTURE',
  'Overheat':'STRUCTURE','Grid Lock':'STRUCTURE','Arc Shot':'CASTER',
  'Beacon':'SUPPORT','Tunnel Drones':'STRUCTURE','Battery':'STRUCTURE',
  'Rail Shot':'MARKSMAN','Mini Pup':'STRUCTURE'
};
// AK-CLASS: structure family -> one of the FIVE archetypes (TAXONOMY 1.3):
// ramper (per-target damage climb), turret (timed burst window), lockdown
// (snare-beam hold + 35% slow field), nest (planted repeating spawner, 4-token
// cap), pylon (planted +15% atkSpd aura for allied structures in 3.5 tiles).
const STRUCT_ARCH_BY_FAMILY = {
  'Overheat':'ramper','Overclock':'turret','Grid Lock':'lockdown',
  'Tunnel Drones':'nest','Mini Pup':'nest','Battery':'pylon'
};
// AK-CLASS: the reclass trio (0045 Neon Dachshund / 0046 Flux Pomeranian /
// 0048 Pixel Pug) becomes PLANTED STATIC. Stats stay canon-verbatim here --
// the +10% hp compensation ships with the operator-gated _build_canon.py
// regen (contract C1), never a hand edit.
const STATIC_OVERRIDE = { '0045':1, '0046':1, '0048':1 };
// AK-CLASS: CC subtypes (TAXONOMY 2) -- lock / slow / knock / silence ride
// existing engine timers (stun/snare/frozen, slow+slowMag, kbVx/kbVy,
// silenceT/disableTimer). blind/reveal = DENIAL: shown under Control on the
// card sheet but excluded from every CC-counting payoff.
const CC_SUBTYPE = {
  stun:'lock', root:'lock',
  slow:'slow',
  knockback:'knock',
  silence:'silence', disable_tower:'silence',
  blind:'denial', reveal:'denial'
};
// AK-CLASS: class + archetype lookup -- sidecar first (classes.js, keyed by
// cardNumber), interim family constant as the headless fallback.
function akCardClass(c){
  try{
    if(typeof global.AK_CLASS_GET==='function'){
      const k = global.AK_CLASS_GET(c.cardNumber);
      if(k && k.cls) return k.cls;
    }
  }catch(_e){}
  return CLASS_BY_FAMILY[c.ability && c.ability.name] || (c.role==='Structure' ? 'STRUCTURE' : null);
}
function akStructArch(c, cls){
  if(cls!=='STRUCTURE') return null;
  try{
    if(typeof global.AK_CLASS_GET==='function'){
      const k = global.AK_CLASS_GET(c.cardNumber);
      if(k && k.arch) return k.arch;
    }
  }catch(_e){}
  return STRUCT_ARCH_BY_FAMILY[c.ability && c.ability.name] || 'turret';
}

// AK-FEEL B1: role range BANDS (engine tiles). Canon range (1..5 abstract) maps
// into real engagement distances so front/mid/long lines actually form up.
// canon-split roles read the canon number; name overrides come last.
function rangeBand(role, canonRange, name){
  // AK-RULES: princess-tower range supremacy (Clash model, contract L1B).
  // Towers (princess 6, king 6.5) out-range nearly every card. Exactly TWO
  // sanctioned outrangers remain: Laser Beagle 6.5 (beam siege) and
  // Rail Terrier 6.25 (rail sniper). Byte Beagle pulled 6.0 -> 5.5; the
  // long Structure band trimmed 6.5 -> 5.75. Rosco stays 5.0.
  const OVERRIDE = { 'Rail Terrier':6.25, 'Byte Beagle':5.5, 'Laser Beagle':6.5, 'Rosco':5.0 };
  if(OVERRIDE[name] != null) return OVERRIDE[name];
  switch(role){
    case 'Assassin':   return 1.0;
    case 'Vanguard':   return 1.2;
    case 'Striker':    return 1.6;
    case 'Skirmisher': return canonRange <= 1 ? 1.2 : 3.5;
    case 'Spawner':    return 3.5;
    case 'Support':    return canonRange <= 2 ? 3.5 : 4.5;
    case 'Lancer':     return canonRange <= 2 ? 3.5 : 4.5;
    case 'Controller': return 4.5;
    case 'Hacker':     return 5.0;
    case 'Blaster':    return 5.5;
    case 'Structure':  return canonRange <= 4 ? 5.5 : 5.75;  // AK-RULES: was 6.5 -- towers out-range turrets now
    default:           return canonRange;
  }
}

// AK-RULES: one-shot range-band audit. Prints a band-per-card console table
// (longest first) and returns the rows so a headless probe can assert that
// NO third card reaches >= 6.0 (only the two sanctioned outrangers do).
function rangeBandAudit(){
  const rows = Object.values(CARDS)
    .map(c=>({ name:c.name, role:c.role, band:c.range, canonRange:c.canonRange }))
    .sort((a,b)=> b.band - a.band);
  try{
    if(typeof console!=='undefined' && console.table) console.table(rows.slice(0,16));
  }catch(e){}
  return rows;
}

function mapCanonToEngine(c){
  const cost = energyCost(c.cost);
  const range = c.range;
  const isRanged = range >= 2;
  // AK-CLASS: combat class + structure archetype + CC subtype (sidecar-first).
  const combatClass = akCardClass(c);
  const structArch  = akStructArch(c, combatClass);
  const ccSubtype   = CC_SUBTYPE[c.abilityType] || null;
  // AK-CLASS: the reclass trio plants as STATIC structures (speed handled below).
  const reclassStatic = !!STATIC_OVERRIDE[c.cardNumber];
  const isStructure = (c.move_speed === 0) || reclassStatic; // turrets in K9 Circuitry + reclassed statics
  // ---- Clash-style speed tiers (Spec: stagger the lane, slow the pace) ----
  // canon move_speed (0..1.5) -> a named tier + a TILES/SEC speed. The old
  // c.move_speed*1.35 huddled everyone at ~3 tiles/s; these are the real Clash
  // ratios (Very Slow/Slow/Medium/Fast/Very Fast ~ 1:1.5:2:3:4) scaled so a
  // ~13-tile lane crossing takes the Clash-feel 9-12s (Medium) / 5-6s (V.Fast).
  const ms = c.move_speed;
  const silSeed = hashStr(c.name); // reuse the silhouette seed for a tiny nudge
  let speedTier, speed;
  if(ms === 0){ speedTier='Static'; speed=0; }
  else {
    // AK-SPEED 2026-06-16: was a 4-bucket STEP that collapsed 68 of ~97 cards to an
    // identical 1.25 tiles/s -> "all cards travel the same speed" (worst at 4x phase).
    // Now a CONTINUOUS map: anchored on the Medium center (0.85 -> 1.25) so the bulk of
    // the roster keeps its balance, but slope 1.7 spreads the extremes by each card's
    // real canon move_speed -- a tank lumbers (~0.6), a zoomie rips (~2.4), and the
    // difference reads even when the phase multiplier scales everyone x4.
    speed = clamp(1.25 + (ms - 0.85) * 1.7, 0.55, 2.5);
    speedTier = ms <= 0.6 ? 'Slow' : ms <= 0.95 ? 'Medium' : ms <= 1.25 ? 'Fast' : 'Very Fast';
  }
  // per-card nudge so clones are not identical (kept within ~+/-6%)
  if(speed > 0) speed *= (0.94 + (silSeed % 13)/100);
  // AK-CLASS: reclassed nest/pylon cards lose their legs -- planted statics.
  if(reclassStatic){ speedTier='Static'; speed=0; }
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
    range: rangeBand(c.role, range, c.name),  // AK-FEEL B1: engine engagement band by role
    canonRange: range,     // AK-FEEL B1: original canon range (card UI / derivations)
    speed: speed,          // TILES/SEC at full ramp (Clash tier, NOT inflated)
    speedTier: speedTier,  // Static|Slow|Medium|Fast|Very Fast (shown on card)
    accel: 5.0,            // gentle ramp: ~90% of speed by ~0.5s (see getSpeed)
    isRanged: isRanged,
    isStructure: isStructure,
    abilityName: c.ability.name,
    abilityDesc: c.ability.description,
    abilityCD: c.ability.cooldown || 12,
    abilityKind: kind,
    // AK-CLASS: the class layer (TAXONOMY 1-2) -- UI chips, class-keyed
    // synergy combos, archetype behaviors and CC payoffs all read these.
    combatClass: combatClass,     // BRUISER|ASSASSIN|CASTER|MARKSMAN|SUPPORT|SUMMONER|STRUCTURE
    structArch: structArch,       // ramper|turret|lockdown|nest|pylon (STRUCTURE family only)
    ccSubtype: ccSubtype,         // lock|slow|knock|silence|denial|null
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

// ==========================================================================
// AK-STATS: per-match counter spine (Wave 7 lane L2, TAXONOMY_DESIGN 4.0).
// ONE set of counters on the game object -- built ONCE here, consumed by the
// downstream lanes (L4 loot kill-attribution, L5 quest checks, L6 nemesis
// top-damage fallback, L7 rap sheets). index.html reads AK.game.stats at
// grantMatchRewards time; nothing in here changes combat outcomes.
// Attacker plumbing: damage calls thread `att` = the attacking Unit OR a
// plain {owner, card} envelope (projectiles / spells / splash). Neutral
// damage (map hazards, gate zaps) stays unattributed by design -- hazard and
// AI-vs-AI kills must never feed player-attributed payoffs.
// ==========================================================================
function newMatchStats(){
  return {
    kills:0,                 // player-attributed enemy unit kills
    killsByCard:{},          // cardNumber -> kills (player units + spells)
    deploysByCard:{},        // cardNumber -> player deploys
    deathsByCard:{},         // AK-QUEST: player cardNumber -> real combat deaths (CLEANUP CREW + L7 rap-sheet d)
    tokensSpawned:0,         // player-side token spawns (RAT KING quest)
    spellsCast:0,            // player spell casts
    towersLost:0,            // player towers destroyed
    towerDamage:0,           // damage the player dealt to enemy towers
    towersByCard:{},         // AK-PERSONA: player cardNumber -> enemy towers destroyed (rap-sheet tw / WRECKER badge)
    abilitiesByCard:{},      // AK-PERSONA: player cardNumber -> abilities fired (rap-sheet ab / TRIGGER FINGER badge)
    kingDamageTaken:0,       // damage the player KING took
    lootPicked:0,            // L4 loot lane increments (reserved, wired here)
    ccApplied:{lock:0,slow:0,knock:0,silence:0},  // CC the player applied
    ccTaken:{lock:0,slow:0,knock:0,silence:0},    // CC the player's side ate
    hazardDamage:0,          // map-hazard damage dealt to the player's side
    enemyDmgByCard:{}        // enemy cardNumber -> damage dealt to the player (nemesis fallback)
  };
}
// normalize an attacker (Unit | {owner,card} | junk) -> {owner, num, card} | null
function attInfo(a){
  if(!a || typeof a!=='object') return null;
  const card = a.card || null;
  const owner = (typeof a.owner==='number') ? a.owner : null;
  if(owner===null) return null;
  return { owner: owner, card: card, num: card ? (card.cardNumber || card.id || null) : null };
}
function statKill(victim, att){           // victim = dead enemy Unit
  if(!game || !game.stats) return;
  const a = attInfo(att); if(!a) return;
  victim.lastHitBy = a;                   // kill attribution rides the corpse (L4 loot reads it)
  if(a.owner===0 && victim.owner===1 && !victim.isToken){
    game.stats.kills++;
    if(a.num) game.stats.killsByCard[a.num] = (game.stats.killsByCard[a.num]||0) + 1;
    // AK-HANDLER: Tracker keen_senses -- a player kill feeds the special meter.
    if(game.special && game.special.passive && game.special.passive.killMeterBonusSec){
      game.special.meter += game.special.passive.killMeterBonusSec;
    }
  }
}
function statDmg(att, victimOwner, amount){  // enemy damage tally (nemesis top-damage fallback)
  if(!game || !game.stats) return;
  const a = attInfo(att); if(!a) return;
  if(a.owner===1 && victimOwner===0 && a.num){
    game.stats.enemyDmgByCard[a.num] = (game.stats.enemyDmgByCard[a.num]||0) + (amount|0);
  }
}
function statCC(attOwner, victimOwner, sub){ // lock|slow|knock|silence (DENIAL never counts)
  if(!game || !game.stats) return;
  const s = game.stats;
  if(attOwner===0 && s.ccApplied[sub]!=null) s.ccApplied[sub]++;
  if(victimOwner===0 && s.ccTaken[sub]!=null) s.ccTaken[sub]++;
}

// ==========================================================================
// AK-LOOT: "THE SHAKEDOWN" phase 1 (LOOT_SYSTEM_DESIGN / WAVE7 contract L4).
// DMZ-style kill loot: player-attributed kills drop miniaturized real-art
// tokens (Coin Sparks + Scrap Shards), friendly units auto-magnet them into
// the UNBANKED stash, the district gate BANKS the stash onto the AK-SHOW
// ledger, and the banked total folds into the ONE grantMatchRewards grant.
// Phase-1 fence: Key Fragment + Card Tag slots REROLL as spark/shard (the
// roll weights are preserved so phase 2 is a flag flip, not a retune).
// Anti-farm: per-match drop budgets (consumed at DROP time), replay decay
// via opts.lootBudgetMult (the worldChestContext.decayMult rail), Quick Play
// at 75%, hazard/AI-vs-AI kills attribute nothing (statKill owner gate).
// Numbers live in economy.js (AK_ECON.LOOT_TABLE); the mirror below keeps
// the headless harness (which loads only canon+engine) byte-true.
//
// AK-LOOT2: phase 2 -- THE RARE LAYER + THE STAKE. The fragment + tag slots
// are now REAL (LOOT_PHASE flips to 2): Key Fragments drop (10 auto-forge a
// key on bank, AK_ECON.addFragments) + Card Tags drop (the killed card's real
// portrait, masked in a brass dog-tag, grants +1 copy via AK_ECON.addCopy).
// Both are JACKPOT class -- they sweep + survive a loss at 100% (no jackpot is
// ever lost to UX). Anti-farm: fragments cap 3/match (over-cap rerolls as a
// spark), tags cap 2/match (over-cap rerolls as a shard), tags are WORLD-MAP
// ONLY (Quick Play disables them -- targeted tag farming is a world activity).
// ==========================================================================
const LOOT_PHASE = 2;   // phase-2: fragment/tag slots resolve to real loot (was 1 = reroll)
const LOOT_DEFAULTS = {
  DROP_BASE:0.20, DROP_PER_COST:0.04, DROP_MAX:0.60,   // P(drop)=clamp(0.20+0.04*cost, .20, .60)
  SPARK_COINS:2,
  ROLL:[["spark",68],["shard",25],["fragment",5],["tag",2]],
  SHARD_VALUE:{ Common:1, Rare:1, Epic:1, Legendary:2, Mythic:5 },   // shards per kill, victim's rarity
  TOWER_DROP:{ sparks:3, commonShards:1, fragChance:0.10 },          // enemy princess down
  GATE_PINATA:{ sparks:5, fragChance:0.25, floors:["Common","Common","Rare","Epic"] },  // district gate clear
  MAGNET_UNIT:2.0, MAGNET_TOWER:1.5, PULL_SPEED:8.0, LIFETIME:12.0,
  SWEEP_COMMON:0.5, LOSS_KEEP_COMMON:0.5,
  CAP_COINS:40, CAP_SHARDS:10, CAP_SHARDS_BY_R:{ Epic:3, Legendary:2, Mythic:1 },
  QUICK_PLAY_MULT:0.75,
  FRAG_PER_KEY:10, CAP_FRAGMENTS:3, CAP_TAGS:2, TAG_PIN_BONUS:2   // AK-LOOT2 rare-layer budgets
};
function lootTable(){
  try{ const t = global.AK_ECON && global.AK_ECON.LOOT_TABLE; if(t && typeof t==='object') return t; }catch(_e){}
  return LOOT_DEFAULTS;
}
const LOOT_RARE = { Epic:1, Legendary:1, Mythic:1 };   // the jackpot class (100% survival rules)

// AK-LOOT: per-match loot state. budgetMult: replay decay (clamped 0.15..1,
// index passes the frontier decayMult) x Quick Play 75% (no city/level opts).
function newLootState(opts){
  const T = lootTable();
  let bm = 1;
  const dm = Number(opts && opts.lootBudgetMult);
  if(isFinite(dm) && dm > 0) bm = clamp(dm, 0.15, 1);
  const quick = !(opts && typeof opts.city==='number' && typeof opts.level==='number');
  if(quick) bm *= (T.QUICK_PLAY_MULT!=null ? T.QUICK_PLAY_MULT : 0.75);
  const capR = {};
  for(const r in T.CAP_SHARDS_BY_R) capR[r] = Math.round(T.CAP_SHARDS_BY_R[r]*bm);
  return {
    tokens: [],                       // field tokens (renderer draws, magnet pulls)
    // UNBANKED -- at risk until a gate banks it. fragments(count) + tags(name->count)
    // are AK-LOOT2 jackpot class (kept whole on sweep + loss).
    stash:  { coins:0, shards:{}, fragments:0, tags:{} },
    banked: { coins:0, shards:{}, fragments:0, tags:{} },   // safe forever; grantMatchRewards folds this
    spent:  { coins:0, shards:0, byR:{}, fragments:0, tags:0 },   // budget consumed at DROP time
    capCoins:  Math.max(2, Math.round(T.CAP_COINS*bm)),
    capShards: Math.max(1, Math.round(T.CAP_SHARDS*bm)),
    capByR: capR,
    // AK-LOOT2 rare-layer budgets. Fragments allowed in Quick Play; Card Tags
    // are WORLD-MAP ONLY (capTags forced to 0 + tagsAllowed false in Quick Play).
    capFrag:    Math.max(0, Math.round((T.CAP_FRAGMENTS!=null?T.CAP_FRAGMENTS:3)*bm)),
    capTags:    quick ? 0 : Math.max(0, Math.round((T.CAP_TAGS!=null?T.CAP_TAGS:2)*bm)),
    tagsAllowed: !quick,
    puffs: 0                          // post-cap Dust Puffs spawned (feel, zero value)
  };
}

// spawn a field token; tokens hard-cap at 60 entities (overflow credits the
// stash directly so value is never lost to the entity ceiling)
function lootSpawnToken(kind, rarity, value, x, y, meta){
  const L = game && game.loot; if(!L) return;
  if(kind!=='puff' && L.tokens.length >= 60){ lootCredit(kind, rarity, value, meta); return; }
  if(kind==='puff' && L.tokens.length >= 60) return;
  const a = Math.random()*Math.PI*2, d = 0.35 + Math.random()*0.55;
  const tx = clamp(x + Math.cos(a)*d, 0.6, ARENA_W-0.6);
  const ty = clamp(y + Math.sin(a)*d, 0.8, ARENA_H-1.2);
  L.tokens.push({ kind:kind, rarity:rarity||null, value:value|0,
                  // AK-LOOT2: tag tokens carry the killed card's name (-> +1 copy)
                  // and cardNumber (-> the renderer miniaturizes the REAL portrait).
                  name:(meta && meta.name)||null, num:(meta && meta.num)||null,
                  x:x, y:y, sx:x, sy:y, tx:tx, ty:ty, arcT:0, landed:false,
                  age:0, ghost:false, dead:false, pullT:0, mag:null,
                  seed:Math.random()*Math.PI*2 });
}
function lootCredit(kind, rarity, value, meta){
  const L = game && game.loot; if(!L || value<=0) return;
  if(kind==='spark') L.stash.coins += value|0;
  else if(kind==='shard'){ const r=rarity||'Common'; L.stash.shards[r]=(L.stash.shards[r]||0)+(value|0); }
  else if(kind==='fragment') L.stash.fragments += value|0;   // AK-LOOT2: loose key fragments
  else if(kind==='tag'){ const nm=meta&&meta.name; if(nm) L.stash.tags[nm]=(L.stash.tags[nm]||0)+(value|0); }
}
// budget-gated drops: after a cap empties, the slot pays a Dust Puff (the
// FEEL stays, the value is zero -- anti-farm soft ceiling, never punishment)
function lootDropSpark(x,y){
  const L = game && game.loot; if(!L) return;
  const T = lootTable(), v = T.SPARK_COINS!=null ? T.SPARK_COINS : 2;
  if(L.spent.coins + v > L.capCoins){ L.puffs++; lootSpawnToken('puff',null,0,x,y); return; }
  L.spent.coins += v;
  lootSpawnToken('spark', null, v, x, y);
}
function lootDropShard(rarity, value, x, y){
  const L = game && game.loot; if(!L) return;
  const r = rarity||'Common';
  const sub = L.capByR[r];
  const over = (L.spent.shards + 1 > L.capShards) || (sub!=null && ((L.spent.byR[r]||0) + 1 > sub));
  if(over){ L.puffs++; lootSpawnToken('puff',null,0,x,y); return; }
  L.spent.shards += 1; L.spent.byR[r] = (L.spent.byR[r]||0) + 1;
  lootSpawnToken('shard', r, Math.max(1, value|0), x, y);
}
// AK-LOOT2: Key Fragment drop. Budget cap 3/match; over the cap the slot
// REROLLS as a spark (the feel stays, the rare faucet closes -- design sec 7).
function lootDropFragment(x,y){
  const L = game && game.loot; if(!L) return;
  if(L.spent.fragments + 1 > L.capFrag){ lootDropSpark(x,y); return; }
  L.spent.fragments += 1;
  lootSpawnToken('fragment', null, 1, x, y);
}
// AK-LOOT2: Card Tag drop -- the killed card's portrait, +1 copy on bank.
// WORLD-MAP only (Quick Play tagsAllowed=false rerolls to a victim-rarity
// shard); over the 2/match cap also rerolls as a shard. card = victim.card.
function lootDropTag(card, x, y){
  const L = game && game.loot; if(!L) return;
  const T = lootTable();
  const rar = (card && card.rarity) || 'Common';
  const shardVal = (T.SHARD_VALUE && T.SHARD_VALUE[rar]) || 1;
  if(!L.tagsAllowed || !card || !card.name){ lootDropShard(rar, shardVal, x, y); return; }
  if(L.spent.tags + 1 > L.capTags){ lootDropShard(rar, shardVal, x, y); return; }
  L.spent.tags += 1;
  lootSpawnToken('tag', rar, 1, x, y, { name:card.name, num:card.cardNumber });
}

// kill drop -- fires from the unit death block. Player-attributed enemy
// kills ONLY (victim.lastHitBy set by statKill; hazards/AI-vs-AI never set
// an owner-0 attribution). Tokens (summon chaff) carry nothing.
function spawnKillLoot(victim){
  try{
    const L = game && game.loot; if(!L || game.phase!=='live') return;
    if(!victim || victim.owner!==1 || victim.isToken) return;
    const a = victim.lastHitBy;
    if(!a || a.owner!==0) return;
    const T = lootTable();
    const c = victim.card || {};
    const cost = (c.cost|0) || 3;
    const rar  = c.rarity || 'Common';
    const sure = (rar==='Legendary' || rar==='Mythic');   // boss loot never whiffs
    const p = clamp(T.DROP_BASE + T.DROP_PER_COST*cost, T.DROP_BASE, T.DROP_MAX);
    if(!sure && Math.random() >= p) return;
    let roll = Math.random()*100, slot = 'spark';
    for(const w of T.ROLL){ roll -= w[1]; if(roll < 0){ slot = w[0]; break; } }
    if(LOOT_PHASE < 2){               // phase-1 fence: weights preserved, slots reroll
      if(slot==='fragment') slot = 'spark';
      if(slot==='tag')      slot = 'shard';
    }
    if(slot==='spark'){
      const n = cost<=4 ? 1 : cost<=7 ? 2 : 3;   // expensive dogs carry more
      for(let i=0;i<n;i++) lootDropSpark(victim.x, victim.y);
    } else if(slot==='fragment'){
      lootDropFragment(victim.x, victim.y);       // AK-LOOT2: snapped key third
    } else if(slot==='tag'){
      lootDropTag(c, victim.x, victim.y);         // AK-LOOT2: dog-tag = +1 copy of the killed card
    } else {
      lootDropShard(rar, (T.SHARD_VALUE && T.SHARD_VALUE[rar]) || 1, victim.x, victim.y);
    }
  }catch(_e){}
}

// deterministic structure drops (no roll): enemy princess down = a small
// burst of field tokens; district gate clear = the LOOT PINATA, credited
// straight to the stash (advanceSection sweeps + banks immediately after,
// so pinata pay must never lose 50% to its own celebration).
function spawnTowerLoot(t){
  try{
    const L = game && game.loot; if(!L) return;
    const T = lootTable(), D = T.TOWER_DROP || {};
    for(let i=0;i<(D.sparks||3);i++) lootDropSpark(t.x, t.y);
    for(let i=0;i<(D.commonShards||1);i++) lootDropShard('Common', 1, t.x, t.y);
    if(Math.random() < (D.fragChance||0.10)) lootDropFragment(t.x, t.y);   // AK-LOOT2: real key fragment (was reroll)
  }catch(_e){}
}
function spawnGatePinata(t){
  try{
    const L = game && game.loot; if(!L) return;
    const T = lootTable(), P = T.GATE_PINATA || {};
    const v = T.SPARK_COINS!=null ? T.SPARK_COINS : 2;
    for(let i=0;i<(P.sparks||5);i++){
      if(L.spent.coins + v > L.capCoins){ L.puffs++; continue; }
      L.spent.coins += v; lootCredit('spark', null, v);
    }
    const floor = (P.floors && P.floors[game.section]) || 'Common';
    [floor, 'Common'].forEach(r=>{
      const sub = L.capByR[r];
      if(L.spent.shards + 1 > L.capShards || (sub!=null && (L.spent.byR[r]||0)+1 > sub)){ L.puffs++; return; }
      L.spent.shards += 1; L.spent.byR[r] = (L.spent.byR[r]||0)+1;
      lootCredit('shard', r, 1);
    });
    if(Math.random() < (P.fragChance||0.25)){   // AK-LOOT2: gate pinata frag = real fragment (credited, budget-gated)
      if(L.spent.fragments + 1 <= L.capFrag){ L.spent.fragments += 1; lootCredit('fragment', null, 1); }
    }
    addBurst(t.x, t.y, PAL.gold, 16);   // the celebration shower lands on the ledger beat
    effects.push(fx('txt', t.x, t.y-1.4, 'LOOT PINATA', PAL.gold, 1.3));
  }catch(_e){}
}

// auto-magnet collection (one-thumb law: 100% auto, no tap-to-collect ever).
// Magnet anchors to YOUR units (2.0 tiles) + your towers (1.5), pull 8 t/s
// with ease-in. 12s lifetime then ghost (sweeps at 50%). Ticks on SIM time.
function updateLoot(dt){
  const L = game && game.loot; if(!L || !L.tokens.length) return;
  const T = lootTable();
  const mU = T.MAGNET_UNIT!=null ? T.MAGNET_UNIT : 2.0;
  const mT = T.MAGNET_TOWER!=null ? T.MAGNET_TOWER : 1.5;
  const pull = T.PULL_SPEED!=null ? T.PULL_SPEED : 8.0;
  const life = T.LIFETIME!=null ? T.LIFETIME : 12.0;
  for(const tk of L.tokens){
    if(tk.dead) continue;
    tk.age += dt;
    if(!tk.landed){                      // 0.25s pop arc from the corpse
      tk.arcT += dt/0.25;
      if(tk.arcT >= 1){ tk.landed = true; tk.x = tk.tx; tk.y = tk.ty; }
      else { const e = tk.arcT; tk.x = tk.sx + (tk.tx-tk.sx)*e; tk.y = tk.sy + (tk.ty-tk.sy)*e; }
      continue;
    }
    if(tk.kind==='puff'){ if(tk.age >= 2.2) tk.dead = true; continue; }   // confetti only
    if(tk.ghost) continue;               // ghosts wait for the Sweep
    if(tk.age >= life){ tk.ghost = true; tk.mag = null; continue; }
    // (re)acquire a magnet anchor -- nearest live friendly unit / standing player tower in radius
    let m = tk.mag;
    if(m && ((m.alive===false) || m.destroyed)) m = tk.mag = null;
    if(!m){
      let bd = 1e9;
      for(const u of game.units){
        if(u.owner!==0 || !u.alive) continue;
        const d = Math.hypot(u.x-tk.x, u.y-tk.y);
        if(d <= mU && d < bd){ bd = d; m = u; }
      }
      for(const tw of game.player.towers){
        if(tw.destroyed) continue;
        const d = Math.hypot(tw.x-tk.x, tw.y-tk.y);
        if(d <= mT && d < bd){ bd = d; m = tw; }
      }
      tk.mag = m || null;
    }
    if(!m){ tk.pullT = 0; continue; }
    tk.pullT += dt;
    const sp = pull * Math.min(1, tk.pullT*1.8);   // ease-in (the Vampire-Survivors streak feel)
    const dx = m.x - tk.x, dy = m.y - tk.y, d = Math.hypot(dx,dy) || 0.001;
    const step = Math.min(d, sp*dt);
    tk.x += dx/d*step; tk.y += dy/d*step;
    if(d <= 0.38){                                  // SCOOP
      tk.dead = true;
      lootCredit(tk.kind, tk.rarity, tk.value, { name:tk.name });
      if(game.stats) game.stats.lootPicked++;
      // tier-pitched scoop: shard rides rarity index; AK-LOOT2 fragment/tag are
      // jackpot class -> the highest scoop pitches (frag 3, tag 4).
      const ri = tk.kind==='shard' ? Math.max(0, ['Common','Rare','Epic','Legendary','Mythic'].indexOf(tk.rarity||'Common'))
               : tk.kind==='fragment' ? 3 : tk.kind==='tag' ? 4 : 0;
      sfx('scoop'+ri);
      const burstCol = tk.kind==='shard' ? (RARITY_COL[tk.rarity]||PAL.gold)
                     : (tk.kind==='fragment' || tk.kind==='tag') ? PAL.gold : PAL.gold;
      addBurst(tk.x, tk.y, burstCol, tk.kind==='tag' ? 7 : 4);   // tag pop is a touch bigger
    }
  }
  if(L.tokens.length > 8) L.tokens = L.tokens.filter(t=>!t.dead);
  else { for(let i=L.tokens.length-1;i>=0;i--) if(L.tokens[i].dead) L.tokens.splice(i,1); }
}

// the Sweep: at a transition/match end every uncollected token (ghosts
// included) banks at 50% value -- EXCEPT Epic+ shards, which always sweep
// at 100% (no jackpot is ever lost to UX).
function lootSweep(){
  const L = game && game.loot; if(!L) return;
  const T = lootTable();
  const half = T.SWEEP_COMMON!=null ? T.SWEEP_COMMON : 0.5;
  for(const tk of L.tokens){
    if(tk.dead || tk.kind==='puff') continue;
    // jackpot class (Epic+ shards, Key Fragments, Card Tags) always sweeps at
    // 100% -- no rare is ever lost to UX; commons sweep at 50%.
    const jackpot = (tk.kind==='shard' && LOOT_RARE[tk.rarity]) || tk.kind==='fragment' || tk.kind==='tag';
    const v = jackpot ? tk.value : Math.floor(tk.value*half);
    if(v > 0) lootCredit(tk.kind, tk.rarity, v, { name:tk.name });
  }
  L.tokens.length = 0;
}
// stash -> banked (banked is safe forever); returns what moved for the ledger
function lootBank(){
  const L = game && game.loot; if(!L) return null;
  const c = L.stash.coins|0; let n = 0;
  L.banked.coins += c;
  for(const r in L.stash.shards){
    const k = L.stash.shards[r]|0;
    if(k > 0){ L.banked.shards[r] = (L.banked.shards[r]||0) + k; n += k; }
  }
  // AK-LOOT2: jackpot class banks too (fragments forge keys + tags grant copies
  // when grantMatchRewards folds the banked vault at match end).
  const f = L.stash.fragments|0;
  if(f > 0) L.banked.fragments = (L.banked.fragments||0) + f;
  let tg = 0;
  for(const nm in L.stash.tags){
    const k = L.stash.tags[nm]|0;
    if(k > 0){ L.banked.tags[nm] = (L.banked.tags[nm]||0) + k; tg += k; }
  }
  L.stash.coins = 0; L.stash.shards = {}; L.stash.fragments = 0; L.stash.tags = {};
  return { coins:c, shards:n, fragments:f, tags:tg };
}
// match end: win/timer/draw banks ALL; a loss keeps 50% of unbanked commons
// (rounded down, per loot type) and 100% of Epic+ shards (rage-quit guard).
// Banked loot is never touched. Nothing outside the match is ever at risk.
function lootFinalBank(lost){
  try{
    const L = game && game.loot; if(!L) return;
    lootSweep();
    if(lost){
      const T = lootTable();
      const keep = T.LOSS_KEEP_COMMON!=null ? T.LOSS_KEEP_COMMON : 0.5;
      L.stash.coins = Math.floor((L.stash.coins|0)*keep);
      for(const r in L.stash.shards){
        if(!LOOT_RARE[r]) L.stash.shards[r] = Math.floor((L.stash.shards[r]|0)*keep);
      }
    }
    lootBank();
  }catch(_e){}
}

// ---- TOWER ----
class Tower {
  constructor(x,y,type,owner){
    this.x=x; this.y=y; this.type=type; this.owner=owner;
    const s = TOWER_STATS[type];
    this.maxHp=s.hp; this.hp=s.hp; this.dmg=s.dmg; this.range=s.range; this.atkSpd=s.atkSpd;
    this.atkCD=0;
    this.active = (type!=='king'); // king dormant until a princess falls
    this.colR = 1.0;               // AK-FEEL B3: tower collision radius (immovable)
    this.destroyed=false; this.crownCounted=false;
    this.hitFlash=0; this.disableTimer=0;
    this.model=s.model;
  }
  takeDamage(d, att){
    if(this.destroyed) return;
    // AK-STATS: attacker attribution -- t.lastHitBy carries the card that
    // landed the LAST hit (killing blow = last setter before destroyed).
    // L6 nemesis promotion + the KINGMAKER quest read it. `att` may be a
    // Unit or an {owner,card} envelope; junk extras are safely ignored.
    const a = attInfo(att);
    if(a && a.owner!==this.owner && a.num) this.lastHitBy = a.num;
    // District Gate shield soaks first (reuses the unit-shield concept on a tower).
    if(this.gateShield>0){ const s=Math.min(this.gateShield,d); this.gateShield-=s; d-=s; if(d<=0){ this.hitFlash=0.18; return; } }
    const applied = Math.min(this.hp, d);
    // AK-STATS: tower-damage tallies (player perspective)
    if(game && game.stats){
      if(this.owner===1 && a && a.owner===0) game.stats.towerDamage += applied|0;
      if(this.owner===0 && this.type==='king') game.stats.kingDamageTaken += applied|0;
    }
    if(a) statDmg(a, this.owner, applied);
    this.hp=Math.max(0,this.hp-d); this.hitFlash=0.18;
    if(this.hp<=0){
      this.destroyed=true; this.hp=0;
      // AK-PERSONA: per-card tower-destruction tally (rap-sheet tw). Only the
      // player's killing-blow card on an ENEMY tower counts -- display only,
      // zero balance surface (rides the lastHitBy attribution already set).
      if(game && game.stats && this.owner===1 && a && a.owner===0 && a.num){
        game.stats.towersByCard[a.num]=(game.stats.towersByCard[a.num]||0)+1;
      }
    }
  }
}

// AK-FEEL B3: collision radius + mass from a unit's bulk (maxHp). Called at
// construction AND after any build-time stat mult (perks tune / AI curve) so
// the body always matches the final hp. Structures pin at 0.60 (immovable).
function computeBulk(u){
  const hp = u.maxHp || (u.card && u.card.hp) || 1;
  if(u.card && u.card.isStructure) u.colR = 0.60;
  else u.colR = hp < 700 ? 0.35 : hp <= 1500 ? 0.45 : hp <= 2400 ? 0.60 : 0.75;
  u.mass = Math.max(1, hp/1000);
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
    // AK-SYNERGY: named-synergy per-tick buffs (reset + reapplied every tick
    // in computeNamedSynergy; combat getters read them as one more layer).
    this.nsDmg=1;                // damage multiplier (Alpha Pack / Skewer Line / Chaos Crew / Big Dog)
    this.nsMove=1;               // move multiplier (Zoomie Train / Chaos Crew / Pup Swarm)
    this.nsAtkSpd=1;             // attack-speed multiplier (Turret Net)
    this.nsRangeAdd=0;           // flat range bonus in tiles (Spotter)
    this.nsShieldPct=0;          // extra synergy-shield cap as pct of maxHp (Shield Wall)
    // AK-CLASS: class-keyed combo layers (reset + reapplied every tick too)
    this.nsCd=1;                 // ability-cooldown refresh mult (Street Sorcery)
    this.nsLock=1;               // damage mult vs CC-locked targets (Lock and Key)
    this.nsWreck=1;              // damage mult vs towers (Wrecking Crew)
    this.nsDefTaken=1;           // damage-TAKEN mult (Bodyguard Detail; combined floor 0.80)
    // AK-CLASS: RAMPING DAMAGE archetype state -- per-target climb counter
    this._rampTgt=null; this._rampN=0;
    // ---- AK-FEEL B2/B3/B4: combat-feel state ----
    this.kwRegenPct=0;           // AK-KEYWORDS: 'regen' per-sec heal (0 = none)
    this.kbVx=0; this.kbVy=0;    // knockback velocity (integrated before the state machine, exp decay)
    this.hitStop=0;              // melee hit-stop freeze timer (state machine paused)
    this.rootT=0;                // beam firing root (no movement while >0)
    this.engaged=false;          // stop-at-range hysteresis latch
    this._engTgt=null;           // target the latch was set against
    computeBulk(this);           // colR + mass from maxHp (re-run after deploy stat mults)
  }
  getSpeed(){
    if(this.card.isStructure) return 0;
    if(this.frozenTimer>0 || this.snareTimer>0) return 0; // FREEZE stops, SNARE roots
    if(this.rootT>0) return 0; // AK-FEEL B5: beam units fire rooted
    let base = this.maxSpeed*(1-Math.exp(-this.accel*this.spawnTime));
    if(this.slowTimer>0) base*=(1 - (this.slowMag>0?this.slowMag:0.5)); // TAR SLOW (35%) or legacy ability-slow (50%)
    // Move multiplier stack: crew synergy (Pack Speed) x Storm Clock field buff
    // (Zoomies), clamped at MOVE_CAP per the Fairness Doctrine capped-stacking rule.
    let mult = 1;
    if(this.synergy && this.synergyMul) mult *= this.synergyMul.speed; // Pack Speed (Zoomie) move boost
    if(this.nsMove && this.nsMove!==1) mult *= this.nsMove;            // AK-SYNERGY: named-synergy move layer
    if(game && game.eventMods) mult *= game.eventMods.move;            // Storm Clock buff layer
    if(mult > MOVE_CAP) mult = MOVE_CAP;
    base *= mult;
    // AK-ATTRS: Garage Tuning AGILITY -- a permanent per-card stat (clamped
    // 1.25 in snapshotPerks), applied OUTSIDE the MOVE_CAP buff stack so it
    // composes with (never eats headroom from) Pack Speed / synergy / storm.
    if(this.tuneAgi) base *= this.tuneAgi;
    // AK-HANDLER: Shadow passive (swift_paw) + Slipstream timed move buff,
    // composed OUTSIDE the MOVE_CAP stack (like tuneAgi). Both undefined-falsy
    // with no handler -> identity.
    if(this.handlerMove>1) base *= this.handlerMove;
    if(this.spdBuffT>0) base *= (this.spdBuffMul||1);
    return base;
  }
  takeDamage(d,sx,sy,isAbility,att){
    if(!this.alive) return;
    if(this.invulnT>0) return;
    if(this.evadeT>0 && Math.random()<0.2){ effects.push(fx('txt',this.x,this.y-0.5,'DODGE',PAL.ivory,0.5)); return; }
    // AK-KW ward: the first enemy SPELL/ability that would hit is negated, then ward breaks.
    if(isAbility && this.ward){ this.ward=false; this.hitFlash=0.12; effects.push(fx('txt',this.x,this.y-0.5,'WARD','#6fb6ff',0.6)); return; }
    // AK-KW protected: the first instance of ANY damage is absorbed in full, then breaks.
    if(this.protect){ this.protect=false; this.hitFlash=0.12; effects.push(fx('txt',this.x,this.y-0.5,'BLOCKED',PAL.gold||'#D4AF37',0.6)); return; }
    let dmg=d;
    // AK-ATTRS: Garage Tuning DEFENSE / SPEC DEF -- clamped damage-taken
    // mults (0.80..1.0, snapshotPerks). isAbility=true on spell area damage,
    // unit-ability damage, trap fire and map hazards; everything else
    // (attacks, projectiles, splash) is physical. Applied BEFORE the shield
    // soak so shields also stretch further on a tuned dog.
    // AK-CLASS: BODYGUARD DETAIL rides the same damage-taken path -- the
    // COMBINED mult (tune x combo) respects the AK-ATTRS 0.80 floor.
    let tdm = (isAbility ? this.tuneSpecDef : this.tuneDef) || 1;
    if(this.nsDefTaken && this.nsDefTaken<1) tdm = Math.max(0.80, tdm * this.nsDefTaken);
    // AK-HANDLER: Bruiser squad_toughness (passive), totem self-DR (permanent),
    // armor-aura / Last-Stand timed DR -- all undefined-falsy with no handler.
    if(this.handlerDefTaken && this.handlerDefTaken<1) tdm = Math.max(0.80, tdm * this.handlerDefTaken);
    if(this.handlerDRperm>0) tdm = Math.max(0.50, tdm * (1 - this.handlerDRperm));
    if(this.handlerDR>0 && this.handlerDRt>0) tdm = Math.max(0.50, tdm * (1 - this.handlerDR));
    if(tdm && tdm < 1) dmg = dmg * tdm;
    // AK-HANDLER: Tracker mark -- marked enemies take extra damage.
    if(this.markT>0 && this.markMul>1) dmg *= this.markMul;
    // AK-STATS: enemy damage tally (nemesis top-damage fallback). Raw post-
    // mitigation-mult, pre-shield amount keeps the ranking honest + cheap.
    if(att) statDmg(att, this.owner, dmg);
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
    // AK-KW burn: a burn-attacker's hit ignites the target -> DoT ticks in updateUnits (att=null on ticks so no re-ignite).
    if(att && att.burn && this.alive && !(this.card && this.card.isStructure)){ if(!(this.burnT>0)) sfx('kw_burn'); this.burnT=BURN_DUR; this.burnDps=Math.max(2,Math.floor((att.dmg||10)*0.35)); }
    // AK-KW deadly: any damage this attacker lands is lethal (structures/towers immune so the king can't be one-bitten).
    if(att && att.deadly && !(this.card && this.card.isStructure)){ dmg = this.hp + 9999; sfx('kw_deadly'); effects.push(fx('txt',this.x,this.y-0.6,'DEADLY','#ff4d6d',0.6)); }
    this.hp=Math.max(0,this.hp-Math.floor(dmg)); this.hitFlash=0.14;
    if(this.hp>0 && !(this.card && this.card.isStructure)) sfx('hit_impact');   // AK-AUDIO: getting-hit thud (survivors only; voice-capped so a 150-unit brawl stays a din, not mud)
    if(this.hp<=0){
      // AK-HANDLER: Mender Revive Protocol may snatch an owner-0 unit from death
      // inside an active revive zone (no-op when no handler / no revive zone).
      if(tryHandlerRevive(this)){ this.hitFlash=0.14; return; }
      this.hp=0; this.alive=false; this.deathTimer=0;
      this.state=USTATE.DIE; this.stateTimer=0;
      // AK-KW afterlife: queue a weak spectral token (spawned post-substep in update(), never mid-iteration).
      if(this.afterlife && !this.isToken && !this.afterlifeTok && game){ (game._afterlifeQ || (game._afterlifeQ = [])).push({ card:this.card, owner:this.owner, x:this.x, y:this.y, hp:this.maxHp }); }
      if(att) statKill(this, att);   // AK-STATS: kill attribution (loot/quests/rap sheets)
      // AK-EVO: a UNIT that kills an enemy UNIT climbs its kill-streak + evolves (not for tokens, not on tower/structure kills).
      if(att instanceof Unit && !att.isToken && att.owner!==this.owner && !this.isToken && !(this.card && this.card.isStructure)){
        att.killStreak=(att.killStreak||0)+1; applyEvolution(att);
      }
      // AK-QUEST: player-unit death tally on the AK-STATS spine. Only REAL
      // combat deaths land here -- transition board wipes never touch this
      // path, so CLEANUP CREW reads true. Hazard deaths count too (no att
      // needed; a dead support is a dead support).
      if(this.owner===0 && !this.isToken && game && game.stats && this.card && this.card.cardNumber){
        game.stats.deathsByCard[this.card.cardNumber]=(game.stats.deathsByCard[this.card.cardNumber]||0)+1;
      }
      spawnKillLoot(this);           // AK-LOOT: the SHAKEDOWN -- attributed kills drop tokens
      sfxCard('death', this.card);   // AK-AUDIO: pitched-down per-card farewell vocal
      if(game) game.shake += 2; // unit death kick (Spec section 4)
      addBurst(this.x,this.y,this.card.color,10);
    }
  }
  dist(ox,oy){ return Math.hypot(this.x-ox,this.y-oy); }
}

// ==========================================================================
// MATCH SETUP
// ==========================================================================
// AK-PERKS: snapshot + clamp the perk object index.html sets on AK.PERKS right
// before newMatch. Snapshotted ONCE per match (never re-read mid-match). The
// clamps live HERE so a corrupt profile can never break balance. Missing
// object or key = identity defaults, so the headless harness (which never
// sets AK.PERKS) is a pure no-op.
// AK-SHEET: card-level stat math -- ONE source of truth for the engine apply
// (deploy) AND the card-detail attribute sheet (exported on AK.SHEET, so
// index.html renders the engine's numbers instead of re-deriving a formula).
// +6% HP / +6% DMG per level past 1 -- the exact promise the upgrade toast +
// Garage have always made -- capped at Lv10 (mirrors AK_ECON.CARD_LV_CAP).
const CARD_LV_FX = 0.06, CARD_LV_MAX = 10;
function akLevelMult(lv){
  lv = clamp(Math.floor((typeof lv==='number' && isFinite(lv)) ? lv : 1), 1, CARD_LV_MAX);
  return 1 + CARD_LV_FX*(lv-1);
}

function snapshotPerks(){
  let src = null;
  try{ src = (global.AK && global.AK.PERKS) || null; }catch(_e){ src = null; }
  if(!src || typeof src !== 'object') src = {};
  const num = (v,d)=> (typeof v==='number' && isFinite(v)) ? v : d;
  // AK-PERKS + AK-ATTRS: per-card tune overlay (Garage Tuning skill points).
  // Map of cardName -> attribute mults for PLAYER units only. Six tunable
  // attributes (wave-4 expansion from the old hp/dmg pair):
  //   hp/dmg/agi/aspd = boost mults, clamped 1.0..1.25 (+5%/pt, 5 useful pts)
  //   def/spdef       = damage-TAKEN mults, clamped 0.80..1.0 (-5%/pt, 4 pts)
  // def gates attack/projectile/splash damage; spdef gates spell + ability +
  // trap + map-hazard damage (the isAbility flag on Unit.takeDamage).
  // Clamps live HERE so a corrupt profile saturates instead of breaking the
  // card power budget. Stacks multiplicatively on top of card levels.
  const tune = {};
  try{
    const t = src.cardTune;
    if(t && typeof t==='object'){
      let n = 0;
      for(const k in t){
        if(n >= 64) break;
        const e = t[k]; if(!e || typeof e !== 'object') continue;
        const hp    = clamp(num(e.hp,1),    1.0, 1.25);
        const dmg   = clamp(num(e.dmg,1),   1.0, 1.25);
        const agi   = clamp(num(e.agi,1),   1.0, 1.25);   // AK-ATTRS: move speed
        const aspd  = clamp(num(e.aspd,1),  1.0, 1.25);   // AK-ATTRS: attack speed
        const def   = clamp(num(e.def,1),   0.80, 1.0);   // AK-ATTRS: physical taken
        const spdef = clamp(num(e.spdef,1), 0.80, 1.0);   // AK-ATTRS: spell/ability taken
        if(hp>1 || dmg>1 || agi>1 || aspd>1 || def<1 || spdef<1){
          tune[k] = { hp:hp, dmg:dmg, agi:agi, aspd:aspd, def:def, spdef:spdef }; n++;
        }
      }
    }
  }catch(_e){}
  // AK-SHEET: universal card LEVELS (the AK-VIS copies+coins economy) finally
  // reach the engine. index.html has ALWAYS sent perks.cardLevels = {name:lv};
  // until now the engine ignored it, so paid levels never landed on a unit.
  // lv clamps to 1..CARD_LV_MAX and becomes ONE build-time stat mult via
  // akLevelMult; the AK-ATTRS tune overlay stacks ON TOP (per its contract).
  const lvls = {};
  try{
    const L = src.cardLevels;
    if(L && typeof L==='object'){
      let n = 0;
      for(const k in L){
        if(n >= 64) break;
        const v = Math.floor(num(L[k],1));
        if(v > 1){ lvls[k] = clamp(v, 1, CARD_LV_MAX); n++; }
      }
    }
  }catch(_e){}
  return {
    // ENGINE-READ (clamped)
    startEnergy: clamp(Math.floor(num(src.startEnergy,0)), 0, 3),
    energyRegen: clamp(num(src.energyRegen,1), 1.0, 1.25),
    towerHp:     clamp(num(src.towerHp,1),     1.0, 1.30),
    spellCD:     clamp(num(src.spellCD,1),     0.85, 1.0),
    unitDmg:     clamp(num(src.unitDmg,1),     1.0, 1.10),
    cardTune:    tune,
    cardLevels:  lvls,   // AK-SHEET: clamped per-card level map (player only)
    // META-READ passthrough (index.html reward code reads these; engine ignores)
    coinMult: num(src.coinMult,1), scrapMult: num(src.scrapMult,1), xpMult: num(src.xpMult,1),
    dropLuck: num(src.dropLuck,0), chestLuck: num(src.chestLuck,0),
    checkpointDiscount: num(src.checkpointDiscount,0)
  };
}

// AK-NEMESIS (Wave 7 lane L6): named rival fielding. opts.nemesis =
// {card, name, title, tier 1..3, taunt, phase} built by the index.html
// nemesis module from w.nemesis (TAXONOMY_DESIGN 5). The rival's canon card
// rides the AI deck (initial build + every garrison reset) and every AI
// deploy of that card gets the tier mult (1.12/1.22/1.35) on the SAME seam
// as AK-AICURVE world scaling -- BEFORE computeBulk so colR/mass track the
// buffed hp. u.nemesisName feeds the renderer name tag + the GRUDGE MATCH
// synergy precheck. null = Quick Play / no rival -- byte-identical.
const NEMESIS_TIER_MULT = { 1:1.12, 2:1.22, 3:1.35 };
function cardByNumber(num){
  if(!num) return null;
  for(const k in CARDS){ const c=CARDS[k]; if(c && c.cardNumber===num) return c; }
  return null;
}
function nemesisFromOpts(o){
  if(!o || typeof o!=='object' || !o.card) return null;
  const rc = cardByNumber(String(o.card));
  if(!rc || rc.type==='spell') return null;   // a rival rides a deployable rig, never a spell
  const tier = Math.max(1, Math.min(3, Math.floor(o.tier)||1));
  return { card:String(o.card), name:String(o.name||'RIVAL'), title:String(o.title||''),
           tier:tier, mult:NEMESIS_TIER_MULT[tier], taunt:String(o.taunt||''),
           phase:(typeof o.phase==='number') ? Math.max(0,Math.min(3,o.phase|0)) : null };
}
// insert the rival's card into an AI deck if absent (one rig, no dupes)
function nemesisIntoDeck(deck, nx){
  if(!nx) return;
  const rc = cardByNumber(nx.card);
  if(rc && !deck.some(c=>c.cardNumber===nx.card)) deck.push(rc);
}

function newMatch(playerDeckNames, opts){
  opts = (opts && typeof opts==='object') ? opts : {};   // AK-WORLD: {startSection,diffOffset,city,level}
  _uid=0; effects=[]; projectiles=[]; particles=[];
  const mk = (arr)=>arr.map(n=>CARDS[n]).filter(Boolean);
  const pDeck = mk(playerDeckNames && playerDeckNames.length ? playerDeckNames : STARTER_DECK_NAMES);
  // AI uses the Zoomie Split Rush starter (a different faction for variety).
  const aiNames = (global.CANON_DECKS.find(d=>d.class==='Zoomie Syndicate')||{}).cards || STARTER_DECK_NAMES;
  const aDeck = mk(aiNames);
  // AK-NEMESIS: a fielded rival rides the AI deck from the first shuffle
  const nemesis = nemesisFromOpts(opts.nemesis);
  nemesisIntoDeck(aDeck, nemesis);

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
    mode:       (opts.mode || 'convoy'),                                   // AK-MODE: alternate win-conditions via AK_MODES
    convoyMode: (opts.mode == null || opts.mode === 'convoy'),             // the 4-section run is on (default)
    modeImpl:   (global.AK_MODES && opts.mode && global.AK_MODES[opts.mode]) || null,
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
    // AK-HANDLER: equipped commander + the radial special meter (null = none
    // equipped / headless -> the whole handler system is inert; see makeHandlerState).
    special: makeHandlerState(opts.handler, opts.handlerNodes),
    handlerZones: [],            // active heal/armor/slow auras (totem, blessing, suppressor)
    speedTierIdx: -1,
    gameSpeed: TIER_SPEED[0],
    // AK-PERKS: per-match snapshot of AK.PERKS (clamped; identity when unset)
    perks: snapshotPerks(),
    // AK-STATS: the per-match counter spine (TAXONOMY 4.0) -- kills, deploys,
    // CC, tower damage, loot. Quests/loot/nemesis/rap-sheet lanes read it.
    stats: newMatchStats(),
    // AK-LOOT: per-match SHAKEDOWN state -- field tokens, unbanked stash,
    // banked vault, drop budgets (replay decay + Quick Play 75% pre-applied).
    loot: newLootState(opts),
    // AK-WORLD: run config + the per-section clear-time record the world map reads.
    // startSection>0 = checkpoint restart (skipped districts never pay stars/gates).
    startSection: clamp(Math.floor(opts.startSection||0), 0, 3),
    diffOffset:   clamp(Math.floor(opts.diffOffset||0), 0, 6),
    worldCity:  (typeof opts.city==='number')  ? opts.city  : null,
    worldLevel: (typeof opts.level==='number') ? opts.level : null,
    // AK-NEMESIS: fielded rival {card,name,title,tier,mult,taunt,phase} | null
    nemesis: nemesis,
    // AK-AICURVE: world index base for the 1..400 difficulty curve. city 0-9,
    // level 1-10 -> base = city*40+(level-1)*4; +section+1 at compute time.
    // null = Quick Play -> legacy DIFFICULTY paths stay byte-identical.
    worldIdxBase: (typeof opts.city==='number' && typeof opts.level==='number')
                    ? (opts.city*40 + (opts.level-1)*4) : null,   // AK-FEEL
    aiCurve: null,                             // AK-AICURVE: set by computeAiCurve()
    sectionClearTimes: [null,null,null,null]   // elapsed seconds when each Gate fell
  };
  computeAiCurve();                            // AK-AICURVE (AK-FEEL)
  if(game.modeImpl && game.modeImpl.setup){ try{ game.modeImpl.setup(game); }catch(_e){} }  // AK-MODE: mode-specific board setup
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
  // AK-PERKS: player tower HP mult (PLAYER towers only; opponent untouched)
  if(game.perks.towerHp > 1){
    game.player.towers.forEach(t=>{ t.maxHp = Math.floor(t.maxHp*game.perks.towerHp); t.hp = t.maxHp; });
  }
  // deal hands (4 cards, rest in queue)
  dealHand(game.player);
  dealHand(game.opponent);
  // staircase difficulty + District Gate mini-boss for section 0
  DIFFICULTY = clamp(SECTIONS[0].diff + game.diffOffset, 0, 9);   // AK-WORLD: city/level staircase
  promoteGate(0);
  // AK-PERKS: flat bonus start energy (player only, capped at ENERGY_MAX)
  if(game.perks.startEnergy > 0){
    game.player.energy = Math.min(ENERGY_MAX, game.player.energy + game.perks.startEnergy);
  }
  // AK-WORLD: checkpoint restart -- jump straight to the saved district. The
  // garrison reset rebuilds enemy towers/deck/difficulty for that section; the
  // player's stars/gatesCleared stay 0 (skipped districts never pay). The clock
  // stays at MATCH_TIME: the timeTier > game.section guard in update() means the
  // 45/90/135 floors can never double-advance a late start.
  if(game.startSection > 0){
    game.section = game.startSection;
    game.speedTierIdx = game.startSection;
    resetEnemyGarrison(game.startSection);
  }
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
  // AK-RULES: staircase bulk applies ONLY where the king is (re)created fresh.
  // A CARRIED king (towers-only phase carry, conflict C3) keeps its current
  // hp/maxHp untouched -- no heal, no restat; only the Gate flavor re-skins.
  if(!king.akCarried){
    king.maxHp    = Math.floor(TOWER_STATS.king.hp * (1.35 + 0.12*section)); // staircase bulk
    king.hp       = king.maxHp;
  }
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
  // AK-SHOW: dress the transition window with the 5-beat showpiece payload.
  // Pure data -- the renderer (index.html ledger/ride/drop beats) consumes it.
  // Computed BEFORE the board resets so survivors + standing towers read true.
  // The choreography lives INSIDE the existing TRANSITION_DUR window (ledger
  // overlaps the ride), so it adds ZERO wall time and the 45/90/135 harness
  // contract is untouched.
  try{
    const elapsedNow = MATCH_TIME - game.time;
    const bounds = [45, 90, 135];                  // mirrors the section-clock floors
    const togo = viaGate ? Math.max(0, (bounds[next-1]||0) - elapsedNow) : 0;
    const towersUp = game.player.towers.filter(t=>!t.destroyed).length;
    // AK-SHOW: NEW district-clear bonus -- a small coin drip per tower standing
    // + time banked by an early clear; "CLEARED EARLY +X" rides on top for
    // earned (gate-cleared) pace. Makes every clear pay. Folded into the ONE
    // grantMatchRewards grant at match end (never a second faucet).
    let bonusCoins = 4*towersUp + Math.floor(togo/6);
    const earlyBonus = viaGate ? (8 + 4*(next-1)) : 0;
    bonusCoins += earlyBonus;
    const bonusScrap = viaGate ? towersUp : 0;     // Common scrap drip on earned clears
    if(!game.clearBonus) game.clearBonus = { coins:0, scrap:0 };
    game.clearBonus.coins += bonusCoins;
    game.clearBonus.scrap += bonusScrap;
    // AK-SHOW: one surviving player card gets the mic (AK-SPEAK, renderer-side)
    const alive = game.units.filter(u=>u.owner===0 && u.alive && u.card);
    const surv = alive.length ? alive[Math.floor(Math.random()*alive.length)].card : null;
    game.transition.show = {
      earned: !!viaGate,                           // earned = gold/major timbre; timer = red/minor
      stars: game.stars||0,
      coins: bonusCoins, scrap: bonusScrap,
      earlyBonus: earlyBonus,
      towers: towersUp, timeLeft: Math.ceil(togo),
      survivor: surv ? surv.name : null,
      lines: [],                                   // ledgerAddLine() target (L4 stamps SALVAGE here)
      rideFlavor: SECTION_HOOKS[next] || '',       // AK-STORY (L8.1): destination district hook line fills the RIDE slot
      // AK-NEMESIS: rematch intro on the ride banner -- the fielded rival
      // talks its talk over every district handoff (tauntSeed-stable voice)
      rideTaunt: (game.nemesis && game.nemesis.taunt) ? game.nemesis.taunt : ''
    };
  }catch(_e){}
  // AK-LOOT: every transition SWEEPS the pavement (uncollected tokens bank
  // into the stash at 50%, Epic+ shards at 100%), but only a CLEARED GATE
  // is the BANK -- a clock-forced move carries the stash UNBANKED into the
  // next district (the DMZ stake stays live until you earn the gate).
  try{
    lootSweep();
    const sh = game.transition.show;
    if(viaGate){
      const bk = lootBank();
      if(bk && (bk.coins>0 || bk.shards>0 || bk.fragments>0 || bk.tags>0) && sh && sh.lines){
        let val = '+'+bk.coins+'c';
        if(bk.shards>0)    val += ' +'+bk.shards+' shard'+(bk.shards>1?'s':'');
        if(bk.fragments>0) val += ' +'+bk.fragments+' frag'+(bk.fragments>1?'s':'');   // AK-LOOT2
        if(bk.tags>0)      val += ' +'+bk.tags+' tag'+(bk.tags>1?'s':'');               // AK-LOOT2
        sh.lines.push({ label:'SALVAGE BANKED', value:val });
      }
    } else if(game.loot && sh && sh.lines){
      const sc = game.loot.stash.coins|0;
      let ss = 0; for(const r in game.loot.stash.shards) ss += game.loot.stash.shards[r]|0;
      if(sc>0 || ss>0) sh.lines.push({ label:'STASH AT RISK', value:'+'+sc+'c -- clear the gate to bank it' });
    }
  }catch(_e){}
  // AK-RESPAWN (AK-FEEL) + AK-RULES: TOWERS-ONLY phase carry (contract L1A).
  // Entering sections 2 + 3 (next 1|2): ALL units leave on BOTH sides; the
  // ONLY things that persist are surviving towers, exactly as they are
  // (hp/maxHp untouched -- no heal, no restat). Player keeps current energy +
  // the +3 gate reward only (grantGateReward already fired on a clean clear).
  // EXCEPTION kept: entering the finale (next 3) = BOTH sides' survivors
  // respawn at their own back line (the AK-RESPAWN keepSurvivors seam).
  if(next <= 2){
    resetEnemyGarrison(next, { carryTowers:true });  // units wiped; surviving enemy towers carry as-is
    resetPlayerBoard();                     // AK-RESPAWN: drop ALL player units (alive included)
  } else {
    resetEnemyGarrison(next, { keepSurvivors:true, carryTowers:true });  // deck/difficulty/Gate rebuild, units kept
    repositionEnemyUnitsToBack();           // AK-RESPAWN: alive enemy survivors regroup at y=5.0
    repositionPlayerUnitsToBack();          // ALIVE player units regroup at the back + re-advance; DEAD are scrapped
  }
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
// AK-RESPAWN (AK-FEEL): survivor respawn -- used ONLY when entering the FINALE
// (section 3). Every ALIVE player unit relocates to the player spawn line and
// re-advances forward; DEAD player units are scrapped (gone). Sections 2 + 3
// entry instead does a FULL board reset on both sides (resetPlayerBoard +
// resetEnemyGarrison). The enemy mirror of this is repositionEnemyUnitsToBack.
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
    u.kbVx=0; u.kbVy=0; u.hitStop=0; u.rootT=0; u.engaged=false; u._engTgt=null;  // AK-FEEL
    effects.push(fx('ring', u.x, u.y, '', PAL.gold, 0.5));   // small regroup pop
  }
}

// AK-RESPAWN (AK-FEEL): FULL board reset for the player side -- fired entering
// sections 2 + 3. ALL player units drop (alive included), all projectiles clear.
// Player energy is whatever is on the bar (the +3 gate reward came from
// grantGateReward before advanceSection; nothing extra is granted here).
function resetPlayerBoard(){
  // AK-ROLLOVER 2026-06-13: player STRUCTURES with lifetime left ROLL OVER to the
  // next phase (operator strategy: drop a tower/den before a phase ends and it is
  // already defending when the new district opens). Troops still all leave; only
  // live structures whose lifeT has not run out persist, exactly where they stand.
  game.units = game.units.filter(u => u.owner !== 0 || (u.card && u.card.isStructure && u.alive && (u.lifeT == null || u.lifeT > 0)));
  projectiles = [];   // clear in-flight shots; a carried structure just fires fresh next phase
}

// AK-RESPAWN (AK-FEEL): enemy mirror of repositionPlayerUnitsToBack -- fired
// entering the FINALE only. ALIVE enemy survivors regroup at ENEMY_BACKLINE_Y
// (5.0, mirror of the player's 25.0) in the same 3-wide lane columns, reset to
// MOVE with statuses cleared. A wiped side respawns nothing.
function repositionEnemyUnitsToBack(){
  // dead enemy units are scrapped; their shots already cleared by the garrison reset
  game.units = game.units.filter(u => !(u.owner===1 && !u.alive));
  const laneCount = { 0:0, 1:0 };
  for(const u of game.units){
    if(u.owner!==1 || !u.alive) continue;
    const laneX = (u.lane===0) ? BRIDGE_LX : BRIDGE_RX;
    const rank  = laneCount[u.lane]++;
    const col = (rank % 3) - 1, row = Math.floor(rank/3);   // 3-wide columns, stacked back (up)
    u.x = clamp(laneX + col*1.1, 1, ARENA_W-1);
    u.y = clamp(ENEMY_BACKLINE_Y - row*1.1, 1.5, RIVER_Y-2);
    u.target=null; u.acquireTarget=null;
    u.state=USTATE.MOVE; u.stateTimer=0; u.deployScale=1; u.spawnTime=0; u.atkCD=0;
    u.angle=Math.PI/2; u.targetAngle=Math.PI/2;   // face forward (enemy marches down)
    u.frozenTimer=0; u.stunTimer=0; u.snareTimer=0; u.slowTimer=0; u.slowMag=0;
    u.kbVx=0; u.kbVy=0; u.hitStop=0; u.rootT=0; u.engaged=false; u._engTgt=null;
    effects.push(fx('ring', u.x, u.y, '', PAL.red, 0.5));
  }
}

// Reset the enemy side for a fresh district: drop the old crew, deal the new
// faction's garrison deck, rebuild towers, re-promote the Gate, set difficulty.
// PLAYER units / towers / energy / crowns CARRY OVER (the "ride with the convoy").
function resetEnemyGarrison(section, opts){
  opts = opts || {};
  const sec = SECTIONS[section];
  // AK-RESPAWN: keepSurvivors (finale entry) skips the unit wipe -- alive enemy
  // units carry into section 3 (repositionEnemyUnitsToBack lays them out).
  if(!opts.keepSurvivors){
    // mark old enemy units dead first so any stale player target ref invalidates,
    // then drop them -- EXCEPT enemy structures with lifetime left, which ROLL
    // OVER like the player's (AK-ROLLOVER 2026-06-13: both sides' buildings persist
    // across the phase if their lifecycle allows, so pre-placed dens/turrets defend).
    const enemyCarry = u => (u.owner===1 && u.card && u.card.isStructure && u.alive && (u.lifeT==null || u.lifeT>0));
    game.units.forEach(u=>{ if(u.owner===1 && !enemyCarry(u)) u.alive=false; });
    game.units.forEach(u=>{ if(u.owner===0){ u.target=null; u.acquireTarget=null; } });
    game.units = game.units.filter(u=> u.owner!==1 || enemyCarry(u));
  }
  projectiles = projectiles.filter(p=> p.owner===0);   // drop enemy shots at the old crew
  game.traps = [];   // armed traps from the old district are stale debris -- clear them
  // fresh garrison deck for this district faction
  const deckDef = (global.CANON_DECKS||[]).find(d=>d.class===sec.garrison);
  const names = (deckDef && deckDef.cards) || STARTER_DECK_NAMES;
  const aDeck = names.map(n=>CARDS[n]).filter(Boolean);
  nemesisIntoDeck(aDeck, game.nemesis);   // AK-NEMESIS: the rival haunts every district garrison
  game.opponent.deck = shuffle(aDeck.length?aDeck:STARTER_DECK_NAMES.map(n=>CARDS[n]).filter(Boolean));
  game.opponent.hand = []; game.opponent.queueIdx = 0;
  dealHand(game.opponent);
  game.opponent.energy = START_ENERGY;
  game.opponent.aiCD = 0; game.opponent.aiNext = 2; game.opponent.aiLane = undefined;
  game.opponent.spellCD = {};
  // AK-RULES: TOWERS-ONLY phase carry (contract L1A + conflict C3). With
  // opts.carryTowers (live district transitions only -- checkpoint starts
  // rebuild fresh), a SURVIVING enemy tower persists exactly as it is:
  // hp/maxHp untouched, no heal, no restat. Destroyed slots are recreated
  // fresh, and ONLY fresh kings take the promoteGate staircase bulk.
  const prevTowers = (opts.carryTowers && game.opponent.towers) || [];
  const towerFor = (x,y,type)=>{
    const old = prevTowers.find(t=> t.type===type && t.x===x && t.y===y && !t.destroyed);
    if(old){
      // stale per-district combat state drops; hp/maxHp/active carry verbatim
      old.atkCD=0; old.hitFlash=0; old.disableTimer=0; old.gateShield=0;
      old.akCarried = true;   // promoteGate reads this: carried king keeps hp/maxHp
      return old;
    }
    return new Tower(x,y,type,1);
  };
  game.opponent.towers = [
    towerFor(BRIDGE_LX,3,'princess'),
    towerFor(BRIDGE_RX,3,'princess'),
    towerFor(9,1,'king')
  ];
  DIFFICULTY = clamp(sec.diff + ((game && game.diffOffset)||0), 0, 9);  // AK-WORLD: staircase rung + city/level offset
  promoteGate(section);
  computeAiCurve();   // AK-AICURVE (AK-FEEL): re-anchor the 1..400 curve to the new phase
}

// ==========================================================================
// AK-AICURVE (AK-FEEL): AI difficulty curve 1..400.
// worldIdx = city0*40 + (level1-1)*4 + phase0 + 1 (city 0-9, level 1-10,
// phase = game.section 0-3). t = (idx-1)/399. Knobs apply to the AI side only.
// Quick Play (worldIdxBase null) -> aiCurve null -> legacy DIFFICULTY paths.
// Anchors: 1/1/1 clearable by a fresh account; 10/10/4 veteran boss.
// ==========================================================================
function computeAiCurve(){
  if(!game) return;
  if(game.worldIdxBase == null){ game.aiCurve = null; return; }
  const idx = clamp(game.worldIdxBase + game.section + 1, 1, 400);
  const t = (idx - 1) / 399;
  game.aiCurve = {
    idx: idx, t: t,
    aiEnergyMult: 0.70 + 0.65*t,                 // rookie 0.70 -> final boss 1.35
    aiNextBase:   Math.max(1.2, 5.0 - 3.4*t),    // decision interval base (+rand*1.2 at roll time)
    aiUnitMult:   1 + 0.60*t,                    // hp AND dmg mult applied at deploy (owner 1)
    sloppyChance: Math.max(0, 0.6 - 2.4*t)       // replaces the DIFFICULTY<=2 dumb-play branch
  };
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
  lootFinalBank(false);   // AK-LOOT: a win banks everything
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
  // FAIRNESS: hold strike countdowns + firing while a map transition freezes combat
  if(s.phase==='active' && game.transition && game.transition.active) return;
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
      if(o.owner===0 && game && game.stats) game.stats.hazardDamage += Math.floor(st.dmg);   // AK-STATS: IRON STOMACH quest fuel
      o.takeDamage(Math.floor(st.dmg), o.x, o.y, true);   // AK-ATTRS: flood hazard -> spdef
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
      if(o.owner===0 && game && game.stats) game.stats.hazardDamage += Math.floor(dmg);   // AK-STATS: hazard tally (kills stay unattributed)
      o.takeDamage(Math.floor(dmg), cx, cy, true);   // AK-ATTRS: map hazard -> spdef
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
// ==========================================================================
// AK-HANDLER: commander specials, passives, the radial meter + active zones.
// Contract: ../HANDLER_BUILD_PLAN.md. Design data: handlers_data.js.
// SAFETY: every per-unit field this stamps (markT, markMul, handlerMove,
// handlerDefTaken, handlerDR(+t), handlerDRperm, spdBuffT/Mul, stealthT,
// stealthLock, revealed, critNext) defaults UNDEFINED -> every read below is
// guarded -> with NO handler equipped (game.special===null) the whole system
// is inert and the sim is byte-identical (headless harness stays true).
// ==========================================================================
// AK-KEYWORDS: GU-style keyword flags at deploy. Default-falsy -> no-keyword = byte-identical.
var HIDDEN_SPAWN_SEC = 2.0;
var KW_REGEN_PCT = 0.015;
var BURN_DUR = 3.0;                 // AK-KW: burn DoT duration (seconds)
var FRONTLINE_TAUNT_R = 8.0;        // AK-KW: frontline taunt pull radius (a wall, not cross-map magnetism)
function applyCardKeywords(u, card){
  var map = (typeof window!=='undefined' && window.AK_CARD_KEYWORDS) || null;
  if(!map || !card) return;
  var ids = map[card.cardNumber] || map[card.name];
  if(!ids || !ids.length) return;
  if(ids.indexOf('hidden')>=0) u.stealthT = HIDDEN_SPAWN_SEC;
  if(ids.indexOf('regen')>=0)  u.kwRegenPct = KW_REGEN_PCT;
  if(ids.indexOf('blitz')>=0){ u.atkCD = 0; u.state = USTATE.MOVE; u.stateTimer = 0; u.deployScale = 1; }
  // AK-KW P2/P3: the 7 mechanics that were cosmetic-only are now WIRED. Every flag
  // defaults undefined-falsy -> a no-keyword unit (and the headless harness) stays byte-identical.
  if(ids.indexOf('frontline')>=0)   u.frontline  = true;   // taunt: enemies lock this first (findTarget)
  if(ids.indexOf('ward')>=0)        u.ward       = true;   // negate the first spell/ability (takeDamage)
  if(ids.indexOf('protected')>=0)   u.protect    = true;   // absorb the first damage instance (takeDamage)
  if(ids.indexOf('burn')>=0)        u.burn       = true;   // its hits ignite the target -> DoT (takeDamage)
  if(ids.indexOf('twin_strike')>=0) u.twinStrike = true;   // two hits -> double-damage swing (doAttack)
  if(ids.indexOf('deadly')>=0)      u.deadly     = true;   // any damage it deals is lethal (takeDamage)
  if(ids.indexOf('afterlife')>=0)   u.afterlife  = true;   // spawns a spectral token on death (update drain)
}
// ==========================================================================
// AK-EVO: KILL-STREAK CARD EVOLUTION. Per-UNIT, in-match only. A unit that racks
// up kills climbs tiers (every 2 kills) and gains stats; on death the streak is
// gone (the unit is gone) and next match every card redeploys at its shop level.
// Permanent power = the shop; this is a temporary in-match power spike (Brawl
// Stars Hypercharge / CoD reactive-camo model). All fields default-falsy so a
// 0-kill unit + the headless harness stay byte-identical. Spec: ../KILLSTREAK_EVOLUTION_SPEC.md
// ==========================================================================
var EVO_TIERS = [
  { kills:0, name:'',          dmg:1.00, hp:1.00, atk:1.00 },   // Basic
  { kills:2, name:'ADVANCED',  dmg:1.10, hp:1.10, atk:1.00 },
  { kills:4, name:'EXCELLENT', dmg:1.20, hp:1.20, atk:1.05 },
  { kills:6, name:'SUPREME',   dmg:1.30, hp:1.30, atk:1.10 },
  { kills:8, name:'DOG GOD',   dmg:1.40, hp:1.40, atk:1.15 }
];
function evoTierFor(kills){ var ti=0; for(var i=0;i<EVO_TIERS.length;i++){ if((kills||0)>=EVO_TIERS[i].kills) ti=i; } return ti; }
function applyEvolution(u){
  if(!u || u.isToken || !u.card || u.card.isStructure) return;            // tokens + structures never evolve
  if(u.baseDmg==null){ u.baseDmg=u.dmg; u.baseMaxHp=u.maxHp; u.baseAtkSpd=u.atkSpd; }   // capture deploy-time (post shop-level) stats ONCE
  var ti=evoTierFor(u.killStreak), T=EVO_TIERS[ti];
  u.dmg = Math.round(u.baseDmg * T.dmg);
  var newMax = Math.round(u.baseMaxHp * T.hp), add = newMax - u.maxHp;
  u.maxHp = newMax; if(add>0) u.hp = Math.min(u.maxHp, u.hp + add);       // grow current hp too -> visibly tougher
  u.atkSpd = u.baseAtkSpd * T.atk;
  if(ti > (u.evoTier||0)){                                                // TIER UP -> loud, telegraphed beat (enemy can see + focus-fire)
    u.evoTier = ti;
    var col = ti>=4 ? '#ffd24a' : ti>=3 ? '#ff8af0' : ti>=2 ? '#6fe0ff' : '#ffe7a0';
    effects.push(fx('crown', u.x, u.y-0.8, T.name, col, 1.1));
    effects.push({ type:'golden_open', x:u.x, y:u.y, color:col, radius:1.6, dur:0.5, t:0 });
    if(game) game.shake += (ti>=4 ? 5 : 2);
    try{ sfx('evo_up'); }catch(_e){}   // AK-AUDIO: dedicated tier-up fanfare
  }
}
function makeHandlerState(handlerId, handlerNodes){
  var byId = (typeof window!=='undefined' && window.AK_HANDLERS_BY_ID) || null;
  var H = byId && byId[handlerId];
  if(!H) return null;                          // headless / no data -> meter disabled
  // Default unlocks = the FREE (bones===0) nodes. The base special is inherent
  // (resolver starts from H.special), so an all-paid tree (Bruiser) starts bare.
  var freeNodes = H.skill_tree.filter(function(n){ return n.bones===0; }).map(function(n){ return n.id; });
  var unlocked = Array.isArray(handlerNodes) ? handlerNodes : freeNodes;
  var cfg = resolveHandlerCfg(H, unlocked);
  return {
    id: H.id, handler: H, cfg: cfg, passive: H.passive,
    meter: 0, rechargeSec: cfg.recharge_sec,
    charges: (cfg.charges>0 ? 1 : 0),          // 1 banked so the first fire is quick (Clash feel)
    maxCharges: cfg.charges,
    aiming: false,
    rigChoice: (cfg.rigChoices ? cfg.rigChoices[0] : null),
    reviveUsed: false,
    goldGainMul: cfg.goldGainMul || 1,
    elapsedGoldT: 0
  };
}
// Fold the unlocked skill-tree node mods onto a shallow copy of the base special.
// Order-independent: each node's effect is ABSOLUTE (a value, not a delta).
function resolveHandlerCfg(H, unlockedIds){
  var c = Object.assign({}, H.special);
  c.outcomes   = H.special.outcomes   ? JSON.parse(JSON.stringify(H.special.outcomes)) : null;
  c.rigChoices = H.special.rigChoices ? H.special.rigChoices.slice() : null;
  for(var i=0;i<H.skill_tree.length;i++){
    var node = H.skill_tree[i];
    if(unlockedIds.indexOf(node.id) < 0) continue;
    var m = node.mods || {};
    for(var k in m){
      if(k==='addCharge'){ c.charges += m.addCharge; }
      else if(k==='addRigChoice'){ if(c.rigChoices && c.rigChoices.indexOf(m.addRigChoice)<0) c.rigChoices.push(m.addRigChoice); }
      else if(k==='addOutcome'){ if(c.outcomes){ for(var oid in m.addOutcome) c.outcomes[oid]=m.addOutcome[oid]; } }
      else if(k==='weightDelta'){ if(c.outcomes){ for(var w in m.weightDelta){ if(c.outcomes[w]) c.outcomes[w].weight=Math.max(0,c.outcomes[w].weight+m.weightDelta[w]); } } }
      else if(k==='ultimate'){ c.ultimate = m.ultimate; }
      else { c[k] = m[k]; }                    // scalar overrides (radius/healPct/recharge_sec/markDur/...)
    }
  }
  return c;
}
// The radial meter -- fills on REAL dt (gated by combatScale), banks charges.
function tickHandlerMeter(dt){
  var sp = game.special; if(!sp || !dt) return;
  if(sp.passive && sp.passive.goldBonusPctPer30s){            // Dealer Small Blessing compounding
    sp.elapsedGoldT += dt;
    while(sp.elapsedGoldT >= 30){ sp.elapsedGoldT -= 30; sp.goldGainMul *= (1 + sp.passive.goldBonusPctPer30s); }
  }
  if(sp.charges >= sp.maxCharges){ sp.meter = sp.rechargeSec; return; }   // full -> hold
  sp.meter += dt;
  if(sp.meter >= sp.rechargeSec){
    sp.meter -= sp.rechargeSec;
    sp.charges = Math.min(sp.maxCharges, sp.charges + 1);
    try{ sfx('ability'); }catch(_e){}
  }
}
// Always-on passives. Reset-then-apply each tick so a buff never outlives the
// handler (mirrors computeNamedSynergy). Runs on sim time.
function tickHandlerPassive(sdt){
  var sp = game.special; if(!sp || !sdt) return;
  var ps = sp.passive || {};
  var moveMul = sp.cfg.passiveMove || ps.allMoveMul || 1;     // Shadow swift_paw (+Shadow Runner node)
  var defMul  = ps.allyDamageTakenMul || 0;                   // Bruiser squad_toughness (0 = none)
  for(var i=0;i<game.units.length;i++){
    var u = game.units[i];
    u.handlerMove = 1; u.handlerDefTaken = 1;                 // identity reset on ALL units
    if(u.owner!==0 || !u.alive) continue;
    var isStruct = u.card && u.card.isStructure;
    if(moveMul>1 && !isStruct) u.handlerMove = moveMul;
    if(defMul && defMul<1) u.handlerDefTaken = defMul;
    if(ps.regenPct && !isStruct){ u.hp = Math.min(u.maxHp, u.hp + u.maxHp*ps.regenPct*sdt); }  // Mender pack_scent
  }
}
// Active heal/armor/slow auras (Mender totem, Dealer blessing, Suppressor).
function tickHandlerZones(sdt){
  var sp = game.special; if(!sp || !sdt) return;
  var zones = game.handlerZones; if(!zones || !zones.length) return;
  for(var zi=zones.length-1; zi>=0; zi--){
    var z = zones[zi];
    z.lifeT -= sdt;
    if(z.anchorId!=null){                                     // zone dies with its totem/turret
      var anchor=null;
      for(var ai=0;ai<game.units.length;ai++){ if(game.units[ai].id===z.anchorId){ anchor=game.units[ai]; break; } }
      if(!anchor || !anchor.alive){ zones.splice(zi,1); continue; }
      z.x = anchor.x; z.y = anchor.y;
    }
    if(z.lifeT<=0){ zones.splice(zi,1); continue; }
    for(var ui=0; ui<game.units.length; ui++){
      var u = game.units[ui];
      if(!u.alive || (u.card && u.card.type==='spell')) continue;
      var d = Math.hypot(u.x-z.x, u.y-z.y);
      if(z.kind==='heal'){
        if(u.owner!==0 || d>z.r) continue;
        if(z.healPct) u.hp = Math.min(u.maxHp, u.hp + u.maxHp*z.healPct*sdt);
        if(z.shieldPct){ var cap=Math.floor(u.maxHp*z.shieldPct); if(u.shieldHp<cap) u.shieldHp=Math.min(cap, u.shieldHp+cap*sdt*0.5); }
        if(z.armorAura && d<=z.armorAura.radius){ u.handlerDR=Math.max(u.handlerDR||0, z.armorAura.drPct); u.handlerDRt=0.2; }
      } else if(z.kind==='slow'){
        if(u.owner!==1 || d>z.r) continue;
        u.slowTimer=Math.max(u.slowTimer,0.3); u.slowMag=Math.max(u.slowMag, z.slowPct);
      }
    }
  }
}
// Mender Revive Protocol -- intercepts an owner-0 unit death inside a revive zone.
function tryHandlerRevive(u){
  var sp = game.special;
  if(!sp || sp.reviveUsed || u.owner!==0 || u.isToken) return false;
  var zones = game.handlerZones; if(!zones) return false;
  for(var i=0;i<zones.length;i++){ var z=zones[i];
    if(z.kind!=='heal' || !z.revive) continue;
    if(Math.hypot(u.x-z.x, u.y-z.y) > z.r) continue;
    if(Math.random() < z.revive.chance){
      sp.reviveUsed = true;
      u.alive=true; u.hp=Math.floor(u.maxHp*z.revive.hpPct); u.shieldHp=0;
      u.state=USTATE.DEPLOY; u.stateTimer=0; u.deathTimer=-1; u.deployScale=0;
      effects.push(fx('crown', u.x, u.y-0.5, 'REVIVED', PAL.gold||'#D4AF37', 1.0));
      return true;
    }
    return false;                                            // zone present, roll failed -> stays dead
  }
  return false;
}
// Minimal engine card for a handler-summoned structure (no cardNumber -> invisible
// to loot/stats/level/tune maps; mirrors mapCanonToEngine's render contract).
function handlerStructCard(name, color, opts){
  opts = opts || {};
  var pal = (typeof FACTION_PAL!=='undefined' && FACTION_PAL[1]) || { base:(PAL&&PAL.steel)||'#8893a5', dark:'#222', light:'#aaa' };
  return {
    id:null, cardNumber:null, name:name, breed:'Handler Rig', faction:null, factionName:null,
    rarity:'Rare', isMythic:false, cost:0, canonCost:0, role:'Structure',
    hp: opts.hp||500, dmg: opts.dmg||0, atkSpd: opts.atkSpd||1.0,
    range: opts.range||0, canonRange: opts.range||0,
    speed:0, speedTier:'Static', accel:5.0, isRanged:(opts.range||0)>=2,
    isStructure:true, type:'unit',
    abilityName:null, abilityDesc:null, abilityCD:999, abilityKind:'buff',
    combatClass:'STRUCTURE', structArch: opts.structArch||'turret', specialArt: opts.specialArt||null, ccSubtype:null,
    queenTarget:false, rig:null,
    color: color||((PAL&&PAL.gold)||'#D4AF37'), glyph: opts.glyph||'M',
    palette: pal, accent: color||'#D4AF37', bodyShape:'blocky',
    weaponType: opts.weaponType||'bullet', targets: opts.targets||'both', domain: opts.domain||'ground',
    projSpeed:9, projColor: color||'#D4AF37', projSize:0.28, projShape:'shell',
    silhouetteSeed: (name.length*97)&1023, crossLane:true,
    splash: opts.splash||0, chain: opts.chain||0, isHandlerStruct:true
  };
}
function pickWeighted(outcomes){
  var keys=[], tot=0;
  for(var k in outcomes){ var w=Math.max(0,outcomes[k].weight||0); keys.push([k,w]); tot+=w; }
  if(tot<=0) return keys.length?keys[0][0]:null;
  var r=Math.random()*tot;
  for(var i=0;i<keys.length;i++){ r-=keys[i][1]; if(r<=0) return keys[i][0]; }
  return keys[keys.length-1][0];
}
// AK-HANDLER: a LOUD, unmistakable cast VFX so the player SEES the special land
// (operator: "I can't tell if it's working, I don't see any special effects").
// bright accent flash + shockwave + big floating SPECIAL NAME + screen kick +
// a white pop on every unit in the blast so the field reaction is obvious.
function handlerFireFx(sp, cfg, gx, gy){
  var acc = (sp.handler && sp.handler.accent) || '#D4AF37';
  var r = cfg.radius || 2.5;
  effects.push({ type:'hazard_strike', x:gx, y:gy, color:acc, radius:Math.max(2.4,r), dur:0.6, t:0 });
  effects.push({ type:'golden_open',  x:gx, y:gy, color:acc, radius:r, dur:0.7, t:0 });
  effects.push({ type:'special_sprite', kind:(cfg.kind||''), x:gx, y:gy, radius:Math.max(2.2,r), dur:1.1, t:0 });   // AK-SPECIALART 2026-06-18: custom cast sprite for all 6 specials
  var nm = String((cfg.name)||(sp.handler && sp.handler.special && sp.handler.special.name)||'SPECIAL').toUpperCase();
  effects.push(fx('crown', gx, gy-1.3, nm, acc, 1.5));
  if(game){
    game.shake += 7;
    for(var i=0;i<game.units.length;i++){ var u=game.units[i];
      if(u.alive && Math.hypot(u.x-gx,u.y-gy) <= r) u.hitFlash = Math.max(u.hitFlash||0, 0.22); }
  }
  try{ sfx('crown'); }catch(_e){}
}
// ---- fire dispatcher: one charge -> route by cfg.kind to an existing primitive ----
function fireSpecial(gx, gy, choiceOpt){
  var sp = game && game.special; if(!sp || game.phase!=='live') return false;
  if(sp.charges <= 0) return false;
  var cfg = sp.cfg;
  // AK-BALANCE 2026-06-17 (operator: the special was FREE/unlimited -- now it costs ENERGY too, not just the
  // recharge meter, so it's a real resource decision). Player-only; configurable via cfg.energyCost (default 4/10).
  var ecost = (cfg.energyCost!=null ? cfg.energyCost : 4);
  if(game.player && game.player.energy < ecost){ try{ effects.push(fx('txt', game.player.kingX||ARENA_W/2, ARENA_H-3, 'NEED '+ecost+' ENERGY', '#ff5a5a', 0.8)); }catch(_e){} return false; }
  if(cfg.ownSideOnly && gy < RIVER_Y + RIVER_H/2 + 0.5) gy = RIVER_Y + RIVER_H/2 + 0.6;
  gx = clamp(gx, 1, ARENA_W-1); gy = clamp(gy, 1, ARENA_H-1);
  var ok = false;
  switch(cfg.kind){
    case 'heal-totem': ok = fireMenderTotem(sp, cfg, gx, gy); break;
    case 'mark':       ok = fireTrackerMark(sp, cfg, gx, gy); break;
    case 'slipstream': ok = fireShadowSlip(sp, cfg, gx, gy); break;
    case 'drop-rig':   ok = fireRiggerRig(sp, cfg, gx, gy, choiceOpt || sp.rigChoice); break;
    case 'war-cry':    ok = fireBruiserCry(sp, cfg, gx, gy); break;
    case 'house-edge': ok = fireDealerEdge(sp, cfg, gx, gy); break;
  }
  if(ok){ sp.charges--; sp.aiming=false; if(game.player) game.player.energy = Math.max(0, game.player.energy - ecost); handlerFireFx(sp, cfg, gx, gy); }   // AK-BALANCE: special now spends energy on fire
  return ok;
}
function fireMenderTotem(sp, cfg, gx, gy){
  var card = handlerStructCard('Field Kennel', (sp.handler&&sp.handler.accent)||'#7FE3A0', { structArch:'nest', glyph:'+', specialArt:'heal-totem', hp:cfg.totemHp, range:0 });
  var u = new Unit(card, 0, gx, gy);
  u.maxHp = u.hp = cfg.totemHp; u.handlerDRperm = cfg.totemDR;   // permanent self DR (read in takeDamage)
  u.lifeT = cfg.lifeT; computeBulk(u); game.units.push(u);
  sp.reviveUsed = false;
  game.handlerZones.push({ kind:'heal', owner:0, anchorId:u.id, x:gx, y:gy,
    r:cfg.radius, healPct:cfg.healPct, lifeT:cfg.lifeT,
    armorAura: cfg.armorAura||null, revive: cfg.revive||null });
  effects.push({type:'golden_open', x:gx, y:gy, color:'#7FE3A0', radius:cfg.radius, dur:0.6, t:0});
  return true;
}
function fireTrackerMark(sp, cfg, gx, gy){
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==1 || !o.alive || (o.card && o.card.type==='spell')) continue;
    if(Math.hypot(o.x-gx,o.y-gy) > cfg.radius) continue;
    o.markT = cfg.markDur; o.markMul = cfg.markMul;
    if(cfg.reveal) o.revealed = cfg.markDur;
    if(cfg.noStealthForMarked) o.stealthLock = cfg.markDur;
  }
  effects.push({type:'golden_open', x:gx, y:gy, color:'#E2B23A', radius:cfg.radius, dur:0.5, t:0});
  return true;                                                   // fires on empty ground too (reveal sweep)
}
function fireShadowSlip(sp, cfg, gx, gy){
  var best=null, bd=cfg.pickRadius;
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==0 || !o.alive || (o.card && (o.card.isStructure || o.card.type==='spell'))) continue;
    if(o.stealthLock>0) continue;
    var d=Math.hypot(o.x-gx,o.y-gy); if(d<bd){ bd=d; best=o; }
  }
  if(!best) return false;                                        // no ally near tap -> don't spend the charge
  best.invulnT = Math.max(best.invulnT, cfg.stealthDur);
  best.stealthT = cfg.stealthDur;
  best.spdBuffT = cfg.stealthDur; best.spdBuffMul = cfg.speedMul;
  if(cfg.critNext>0) best.critNext = cfg.critNext;
  effects.push(fx('txt', best.x, best.y-0.6, 'SLIP', '#9B8CFF', 0.6));
  return true;
}
function fireRiggerRig(sp, cfg, gx, gy, choice){
  var rc = cfg.rigCards[choice] || cfg.rigCards[cfg.rigChoices[0]];
  if(!rc) return false;
  var card = handlerStructCard(rc.name, '#D45A2C', {
    structArch:'turret', glyph:'T', specialArt:'drop-rig', hp:rc.hp, dmg: Math.round(rc.dmg*(cfg.rigDmgMul||1)),
    range: rc.range, atkSpd: rc.atkSpd, weaponType: rc.weaponType, targets:'both',
    splash: rc.splash||0, chain: rc.chain||0
  });
  var u = new Unit(card, 0, gx, gy);
  u.maxHp = u.hp = Math.round(rc.hp * (cfg.rigHpMul||1));
  var structMul = (sp.passive && sp.passive.structLifeMul) || 1;
  u.lifeT = rc.lifeT * structMul * (cfg.rigLifeMul||1);
  if(rc.slowAura) game.handlerZones.push({ kind:'slow', owner:0, anchorId:u.id, x:gx, y:gy, r:rc.slowAura.radius, slowPct:rc.slowAura.slowPct, lifeT:u.lifeT });
  computeBulk(u); game.units.push(u);
  effects.push(fx('ring', gx, gy, '', card.accent, 0.5));
  return true;
}
function fireBruiserCry(sp, cfg, gx, gy){
  var hit=0;
  for(var i=0;i<game.units.length;i++){ var o=game.units[i];
    if(o.owner!==0 || !o.alive || (o.card && o.card.isStructure)) continue;
    if(Math.hypot(o.x-gx,o.y-gy) > cfg.radius) continue;
    o.dmgBuffT = Math.max(o.dmgBuffT, cfg.dmgBuffDur);
    o.dmgBuffMul = cfg.dmgBuffMul;                              // doAttack reads while dmgBuffT>0
    o.shieldHp = Math.max(o.shieldHp, Math.floor(o.maxHp*cfg.shieldPct));
    if(cfg.blockedHitDR>0){ o.handlerDR = Math.max(o.handlerDR||0, cfg.blockedHitDR); o.handlerDRt = cfg.blockedHitDur; }
    hit++;
  }
  effects.push({type:'golden_open', x:gx, y:gy, color:'#C0392B', radius:cfg.radius, dur:0.5, t:0});
  if(game) game.shake += 3;
  return hit>0;
}
// ---- Dealer mixed roll: each outcome maps to one existing primitive ----
function dealerCheapCard(maxCost){
  var pool = (game.player && game.player.deck) ? game.player.deck : [];
  var best=null;
  for(var i=0;i<pool.length;i++){ var c=pool[i];
    if(!c || c.type==='spell' || c.isStructure || c.cost>(maxCost||3)) continue;
    if(!best || c.cost<best.cost) best=c;
  }
  return best;
}
function dealerSpawnPup(maxCost, gx, gy){
  var c = dealerCheapCard(maxCost); if(!c) return;
  var u = new Unit(c, 0, clamp(gx+(Math.random()-0.5)*1.6,1,ARENA_W-1), clamp(gy+(Math.random()-0.5)*1.6,RIVER_Y+2,ARENA_H-1.6));
  u.isToken=true; computeBulk(u); game.units.push(u);
  effects.push(fx('ring', u.x, u.y, '', c.accent||'#D4AF37', 0.4));
}
function dealerUltimate(ult, gx, gy){
  try{ castSpell({ radius: ult.aoeRadius||2, damage: ult.aoeDmg||300, duration:0 }, 0, gx, gy); }catch(_e){}
  game.special.goldGainMul *= (ult.goldGainMul||1.20);
  if(game) game.shake += (ult.shakeDur ? 6 : 4);
  effects.push(fx('crown', gx, gy-0.5, '$BCARDD', PAL.gold||'#D4AF37', 1.2));
}
function fireDealerEdge(sp, cfg, gx, gy){
  var roll = pickWeighted(cfg.outcomes); if(!roll) return false;
  var o = cfg.outcomes[roll], side = game.player;
  var addEnergy = function(raw){ var e = raw * (cfg.goldToEnergy||(1/3)) * (sp.goldGainMul||1);
    side.energy = clamp(side.energy + e, 0, ENERGY_MAX); };
  switch(roll){
    case 'coin_rain':  addEnergy(o.goldRaw); effects.push(fx('crown', gx, gy-0.4, '+'+o.goldRaw, PAL.gold||'#D4AF37', 0.9)); break;
    case 'pup_swarm':  for(var n=0;n<(o.spawnPups||2);n++) dealerSpawnPup(o.pupCostMax||3, gx, gy); break;
    case 'blessing_aura':
      game.handlerZones.push({ kind:'heal', owner:0, x:gx, y:gy, r:o.zone.radius, healPct:o.zone.healPct, shieldPct:o.zone.shieldPct, lifeT:o.zone.lifeT });
      effects.push({type:'golden_open', x:gx, y:gy, color:PAL.gold||'#D4AF37', radius:o.zone.radius, dur:0.6, t:0}); break;
    case 'double_or_nothing':
      var win = Math.random() < (o.winChance||0.5); addEnergy(win ? o.winRaw : -o.gambleRaw);
      effects.push(fx('txt', gx, gy-0.4, win?'JACKPOT':'BUST', win?(PAL.gold||'#D4AF37'):PAL.red, 0.9)); break;
    case 'house_stake': dealerSpawnPup(4, gx, gy); addEnergy(o.goldRaw||8); break;
  }
  if(cfg.ultimate) dealerUltimate(cfg.ultimate, gx, gy);
  return true;
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
    if(side.owner===0 && game && game.stats) game.stats.spellsCast++;   // AK-STATS
    castSpell(card, side.owner, gx, gy);
    if(!side.spellCD) side.spellCD={};
    // AK-PERKS: player spell cooldown mult (0.85..1.0); opponent unchanged
    const cdMult = (side.owner===0 && game.perks) ? game.perks.spellCD : 1;
    side.spellCD[card.spellId] = (card.cooldown || 10) * cdMult;
    cycleCard(side,handIdx);
    return true;
  }
  // deploy zone rule: you can only deploy on your own half (+ the bridges)
  if(side.owner===0 && gy < RIVER_Y+RIVER_H/2 + 0.5) gy = RIVER_Y+RIVER_H/2+0.6;
  if(side.owner===1 && gy > RIVER_Y-RIVER_H/2 - 0.5) gy = RIVER_Y-RIVER_H/2-0.6;
  gx = clamp(gx,1,ARENA_W-1);
  side.energy -= card.cost;
  const u = new Unit(card, side.owner, gx, gy);
  applyCardKeywords(u, card);
  // AK-PERKS: player unit damage mult at build time (1.0..1.10); AI unchanged
  if(side.owner===0 && game.perks && game.perks.unitDmg > 1) u.dmg = u.dmg * game.perks.unitDmg;
  // AK-SHEET: universal card LEVEL mult (player only, build time) -- the level
  // the player PAID copies+coins for now lands on the unit: +6% HP / +6% DMG
  // per level past 1, capped Lv10 (akLevelMult, clamped in snapshotPerks).
  // Applied UNDER the tune overlay so tuning stacks on top; AI untouched;
  // missing map = identity, so the headless harness stays a byte-true no-op.
  if(side.owner===0 && game.perks && game.perks.cardLevels){
    const lv = game.perks.cardLevels[card.name];
    if(lv > 1){
      const lm = akLevelMult(lv);
      u.dmg = u.dmg * lm;
      u.maxHp = Math.round(u.maxHp * lm); u.hp = u.maxHp;
    }
  }
  // AK-PERKS + AK-ATTRS: per-card Garage Tuning overlay (player only, build
  // time). Mults were clamped in snapshotPerks (boosts 1.0..1.25, taken-mults
  // 0.80..1.0); they stack ON TOP of card levels.
  if(side.owner===0 && game.perks && game.perks.cardTune){
    const tn = game.perks.cardTune[card.name];
    if(tn){
      if(tn.dmg > 1) u.dmg = u.dmg * tn.dmg;
      if(tn.hp  > 1){ u.maxHp = Math.round(u.maxHp * tn.hp); u.hp = u.maxHp; }
      // AK-ATTRS: the 4 wave-4 attributes ride the unit as clamped mults and
      // get read at getSpeed / atkInterval / takeDamage (composing with the
      // AK-FEEL + AK-SYNERGY layers there, never replacing them). undefined =
      // identity, so AI units and untuned cards pay zero cost.
      if(tn.agi   > 1) u.tuneAgi     = tn.agi;    // move speed up
      if(tn.aspd  > 1) u.tuneAspd    = tn.aspd;   // attack interval down
      if(tn.def   < 1) u.tuneDef     = tn.def;    // physical damage-taken mult
      if(tn.spdef < 1) u.tuneSpecDef = tn.spdef;  // spell/ability damage-taken mult
    }
  }
  // AK-AICURVE (AK-FEEL): world-run AI units scale hp AND dmg at deploy time.
  // Quick Play (aiCurve null) deploys are byte-identical to wave-1.
  if(side.owner===1 && game.aiCurve && game.aiCurve.aiUnitMult > 1){
    u.dmg = u.dmg * game.aiCurve.aiUnitMult;
    u.maxHp = Math.round(u.maxHp * game.aiCurve.aiUnitMult); u.hp = u.maxHp;
  }
  // AK-NEMESIS: the named rival's rig deploys buffed -- hp/dmg x 1.12/1.22/
  // 1.35 by tier on the SAME seam as the AK-AICURVE world mult (before
  // computeBulk so colR/mass track the buffed hp). nemesisName feeds the
  // renderer name tag + the GRUDGE MATCH precheck in computeNamedSynergy.
  if(side.owner===1 && game.nemesis && card.cardNumber===game.nemesis.card){
    u.dmg = u.dmg * game.nemesis.mult;
    u.maxHp = Math.round(u.maxHp * game.nemesis.mult); u.hp = u.maxHp;
    u.nemesisName = game.nemesis.name;
  }
  computeBulk(u);   // AK-FEEL B3: colR/mass track the FINAL post-mult maxHp
  // AK-LIFETIME: every structure gets a Clash-Royale-style lifespan so it expires
  // instead of spawning/firing forever. Spawner nests ~30s (Goblin/Tombstone-hut
  // band), other buildings ~40s (Cannon/Tesla band). Non-structures: null = forever.
  if(u.card.isStructure){ u.lifeT = (u.card.structArch==='nest') ? 30 : 40; }
  // AK-HANDLER: Rigger structure_durability also lengthens CARD-summoned player
  // structures (rig turrets apply it in fireRiggerRig). Behind the owner-0 gate.
  if(side.owner===0 && u.card.isStructure && u.lifeT!=null && game.special && game.special.passive && game.special.passive.structLifeMul){
    u.lifeT *= game.special.passive.structLifeMul;
  }
  u.lane = (gx < ARENA_W/2) ? 0 : 1; // left lane = 0, right lane = 1 (Spec section 1)
  if(side.owner===0 && game.stats && card.cardNumber){   // AK-STATS: deploy tally
    game.stats.deploysByCard[card.cardNumber] = (game.stats.deploysByCard[card.cardNumber]||0) + 1;
  }
  game.units.push(u);
  effects.push(fx('ring',gx,gy,'',card.color,0.5));
  // AK-VOICE111 2026-06-13: ONE voice per deploy. The premium per-card tagline
  // (akSpeakTagline below) IS the deploy voice now -- the old synth deploy-vocal
  // (sfxCard 'deploy') + Mythic war-cry double-talked over it (operator: "two
  // voices at the same time -- one or the other"). Tagline wins; it is consistent
  // and per-card. Non-vocal combat SFX (hits/abilities) are untouched.
  if(side.owner===0) loreFlash(card, gx, gy);   // AK-LORE: tagline flash near the spawn (throttled; LOW_FX + headless skip)
  if(side.owner===0) akSpeakTagline(card);      // AK-SPEAK: the tagline is their VOICE -- audible even under LOW_FX (4s throttle + mute/ak_voice gates inside)
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
  // AK-FEEL B6: energy ticks on REAL dt (NOT sim-speed sdt) -- the section ramp
  // is the explicit ENERGY_SECTION_MULT curve, not a hidden 4x sim-regen hack.
  // combatScale still gates it to 0 while a map transition freezes combat.
  const eMod = game.eventMods ? game.eventMods.energy : 1;   // Zoomies/Overclock energy buff
  const pReg = (game.perks && game.perks.energyRegen) || 1;  // AK-PERKS: player-only regen mult
  const secMult = ENERGY_SECTION_MULT[game.section] || 1;    // AK-FEEL B6
  // AK-AICURVE: world runs use the 1..400 curve's energy knob INSTEAD of the
  // legacy DIFFICULTY formula (no double-ramp); Quick Play keeps legacy.
  const aiReg = game.aiCurve ? game.aiCurve.aiEnergyMult : (0.78+DIFFICULTY*0.052);
  game.player.energy   = Math.min(ENERGY_MAX, game.player.energy   + ENERGY_RATE*dt*secMult*combatScale*eMod*pReg);
  game.opponent.energy = Math.min(ENERGY_MAX, game.opponent.energy + ENERGY_RATE*dt*secMult*combatScale*eMod*aiReg);
  tickHandlerMeter(dt * combatScale);   // AK-HANDLER: radial meter fills on REAL dt, pauses mid-transition

  computeSynergy(sdt);  // crew-synergy flags + shield regen, scaled to sim time
  tickHandlerPassive(sdt);   // AK-HANDLER: always-on commander auras (composes after synergy, sim time)
  tickSpellCooldowns(sdt);   // honors Overclock (-30% spell CD) inside
  assignSurroundSlots();  // AK-SEP2: melee surround-ring slots (once per frame)
  // sub-step physics/combat so 4x speed doesn't tunnel units or projectiles
  let rem = sdt; const SUB = 0.05;
  while(rem > 1e-6){
    const s = Math.min(rem, SUB);
    updateUnits(s);
    separationPass(s);   // AK-FEEL B3: mass-weighted body separation (no stacking)
    updateTowers(s);
    updateProjectiles(s);
    updateTraps(s);     // snare traps arm + trigger inside the sub-step
    rem -= s;
  }
  // AK-KW afterlife: spawn the queued spectral tokens here (post-substep -> never mutates game.units mid-iteration).
  if(game._afterlifeQ && game._afterlifeQ.length){
    for(var _ai=0; _ai<game._afterlifeQ.length; _ai++){ var _q=game._afterlifeQ[_ai];
      try{ var _t=new Unit(_q.card, _q.owner, _q.x, _q.y); _t.isToken=true; _t.afterlifeTok=true;
        _t.maxHp=_t.hp=Math.max(1,Math.floor((_q.hp||40)*0.30)); _t.dmg=Math.floor((_t.dmg||10)*0.5);
        computeBulk(_t); game.units.push(_t); sfx('afterlife');
        effects.push(fx('txt', _q.x, _q.y-0.5, 'AFTERLIFE', '#b06bff', 0.7));
        effects.push({type:'golden_open', x:_q.x, y:_q.y, color:'#b06bff', radius:1.4, dur:0.5, t:0});
      }catch(_e){}
    }
    game._afterlifeQ.length=0;
  }
  updateAI(sdt);
  updateGoldenHour(sdt);   // objective-zone heal/shield (sim time)
  tickHandlerZones(sdt);   // AK-HANDLER: totem/blessing/suppressor auras (sim time)
  updateEffects(sdt);
  updateParticles(sdt);
  updateLoot(sdt);         // AK-LOOT: token pop arcs + auto-magnet scoop (sim time)

  // tower disable timers + Gate mechanic pulse (sim time)
  [...game.player.towers,...game.opponent.towers].forEach(t=>{
    if(t.hitFlash>0) t.hitFlash-=sdt;
    if(t.disableTimer>0) t.disableTimer-=sdt;
  });

  // remove dead units after their death anim
  game.units = game.units.filter(u=> u.alive || u.deathTimer < 0.45);

  checkWin();
  if(game.modeImpl && game.modeImpl.checkEnd && game.phase==='live'){   // AK-MODE: mode win-condition seam
    var _mr=game.modeImpl.checkEnd(game, dt);
    if(_mr){ if(_mr.result)game.result=_mr.result; if(typeof _mr.stars==='number')game.stars=_mr.stars; if(_mr.cleanSweep)game.cleanSweep=true; endMatch(); }
  }
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
  // 1.5) AK-SYNERGY: named-synergy pass FIRST so nsShieldPct is fresh when the
  // shield block below merges it with the crew Bone Wall pct.
  computeNamedSynergy(dt);
  tickLockdownStructures(dt);   // AK-CLASS: lockdown hold beam + slow field (sim time)
  // 2) flag each alive unit + regenerate its synergy shield while synergy holds
  for(const u of game.units){
    const f = u.card && u.card.faction;
    const active = u.alive && f && (counts[u.owner][f]||0) >= SYNERGY_MIN;
    u.synergy = !!active;
    u.synergyMul = active ? (SYNERGY[f] || null) : null;
    // shield cap = crew Bone Wall pct + named Shield Wall pct (AK-SYNERGY),
    // one shared pool so the soak order in takeDamage stays unchanged.
    const crewPct = (active && u.synergyMul) ? (u.synergyMul.shieldPct||0) : 0;
    const totPct = crewPct + (u.nsShieldPct||0);
    if(u.alive && totPct>0){
      // top the shield up toward totPct of maxHp (regenerates ~1/3 of cap per second)
      const cap = Math.floor(u.maxHp * totPct);
      if(u.synergyShieldHp < cap){
        u.synergyShieldHp = Math.min(cap, u.synergyShieldHp + cap*(dt||0)/3);
      } else if(u.synergyShieldHp > cap){
        u.synergyShieldHp = cap;   // a layer dropped -> clamp down to the new cap
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

// ==========================================================================
// AK-SYNERGY: NAMED SYNERGY v1 -- detect qualifying combos among each side's
// ALIVE field units every tick, apply the modest buffs while active, drop them
// the instant a member dies (everything is reset + recomputed from scratch).
// Symmetric: owner 0 and owner 1 run the identical rules. Buffs land on the
// per-unit ns* fields that the combat getters fold into their existing capped
// multiplier stacks (MOVE_CAP / DMG_CAP), so the power budget holds.
// Publishes game.namedSynergy = { player:[{id,label,hint}..], opponent:[..] }
// for the HUD chips + first-activation banner.
// ==========================================================================
function computeNamedSynergy(dt){
  if(!game) return;
  const sides = { 0:[], 1:[] };
  for(const u of game.units){
    if(u.card && u.card.type==='spell') continue;
    // hard reset every tick -> a buff can never outlive its members
    u.nsDmg=1; u.nsMove=1; u.nsAtkSpd=1; u.nsRangeAdd=0; u.nsShieldPct=0;
    u.nsCd=1; u.nsLock=1; u.nsWreck=1; u.nsDefTaken=1;   // AK-CLASS: combo layers reset too
    if(u.alive) sides[u.owner].push(u);
  }
  // AK-CLASS: GRUDGE MATCH precheck -- is a named nemesis rival (L6 sets
  // u.nemesisName at deploy) alive on the OTHER side? Dormant until L6 lands.
  const nemesisOn = { 0:false, 1:false };
  for(const owner of [0,1]){
    for(const e of sides[1-owner]){ if(e.nemesisName){ nemesisOn[owner]=true; break; } }
  }
  const deadAir = { 0:false, 1:false };   // AK-CLASS: DEAD AIR per-side flag
  const out = { player:[], opponent:[] };
  for(const owner of [0,1]){
    const list = sides[owner];
    const act = owner===0 ? out.player : out.opponent;
    if(!list.length) continue;
    // single tally pass over the side's alive units
    let hasBcardd=false, boneN=0, hackerN=0;
    const vang=[], vfast=[], structs=[], blasters=[], supports=[], lancers=[], cheap=[], bigs=[];
    // AK-CLASS: class-keyed tallies (TAXONOMY 3). Tokens never ENABLE a
    // combo (no drone-spam activation); they still RECEIVE token buffs.
    let summonerN=0, silencerN=0, lockdownN=0;
    const bruisers=[], assassins=[], casters=[], marksmen=[], clsSupports=[], pylons=[], wreckers=[];
    const facs={};
    for(const u of list){
      const c=u.card; if(!c) continue;
      if(c.name==='$BCARDD') hasBcardd=true;
      if(c.faction==='boneguard_crew') boneN++;
      if(c.faction) facs[c.faction]=1;
      if(c.role==='Vanguard') vang.push(u);
      if(c.speedTier==='Very Fast') vfast.push(u);
      if(c.isStructure) structs.push(u);
      if(c.role==='Hacker') hackerN++;
      if(c.role==='Blaster') blasters.push(u);
      if(c.role==='Support') supports.push(u);
      if(c.role==='Lancer') lancers.push(u);
      if(c.cost<=3) cheap.push(u);
      if(NS_BIG_RARITY[c.rarity]) bigs.push(u);
      if(!u.isToken){                                   // AK-CLASS tallies
        const kc=c.combatClass;
        if(kc==='BRUISER') bruisers.push(u);
        else if(kc==='ASSASSIN') assassins.push(u);
        else if(kc==='CASTER') casters.push(u);
        else if(kc==='MARKSMAN') marksmen.push(u);
        else if(kc==='SUPPORT') clsSupports.push(u);
        else if(kc==='SUMMONER') summonerN++;
        if(c.ccSubtype==='silence') silencerN++;
        if(c.structArch==='lockdown') lockdownN++;
        if(c.structArch==='pylon') pylons.push(u);
        if(c.abilityKind==='turret_break') wreckers.push(u);
      }
    }
    const on = (id)=>{ const s=NAMED_SYNERGY_BY_ID[id]; act.push({id:s.id,label:s.label,hint:s.hint}); };
    // 1 ALPHA PACK: $BCARDD + 2 other Boneguard -> Boneguard +10% dmg
    if(hasBcardd && boneN>=3){ on('alpha_pack'); for(const u of list){ if(u.card.faction==='boneguard_crew') u.nsDmg*=1.10; } }
    // 2 SHIELD WALL: 2+ Vanguards -> Vanguards +12% maxHp shield (rides the synergy-shield pool)
    if(vang.length>=2){ on('shield_wall'); for(const u of vang) u.nsShieldPct+=0.12; }
    // 3 ZOOMIE TRAIN: 3+ Very Fast units -> those +12% move
    if(vfast.length>=3){ on('zoomie_train'); for(const u of vfast) u.nsMove*=1.12; }
    // 4 TURRET NET / FULL BATTERY / pylon aura (AK-CLASS): ONE take-max
    // attack-speed layer for structures, never stacked. FULL BATTERY (pylon +
    // 2+ other structures) supersedes TURRET NET; outside both, the AURA
    // PYLON archetype still buffs allied structures within 3.5 tiles.
    {
      const structsNP = structs.filter(s=> s.card.structArch!=='pylon');
      const fullBattery = pylons.length>=1 && structsNP.length>=2;
      const turretNet   = !fullBattery && structs.length>=2;
      if(fullBattery) on('full_battery'); else if(turretNet) on('turret_net');
      for(const u of structs){
        let m = (fullBattery || turretNet) ? 1.15 : 1;
        if(m===1){
          for(const p of pylons){ if(p!==u && Math.hypot(u.x-p.x,u.y-p.y)<=3.5){ m=1.15; break; } }
        }
        if(m>1) u.nsAtkSpd*=m;
      }
    }
    // 5 SPOTTER: Hacker + Blaster alive -> Blasters +0.5 range
    if(hackerN>=1 && blasters.length>=1){ on('spotter'); for(const u of blasters) u.nsRangeAdd+=0.5; }
    // 6 STREET MEDICS: 2+ Supports -> allies within 3 tiles of a Support heal 1% maxHp/s
    if(supports.length>=2){
      on('street_medics');
      for(const u of list){
        if(u.hp>=u.maxHp) continue;
        for(const m of supports){
          if(Math.hypot(u.x-m.x, u.y-m.y) <= NS_HEAL_R){
            u.hp = Math.min(u.maxHp, u.hp + u.maxHp*NS_HEAL_PCT*(dt||0));
            break;
          }
        }
      }
    }
    // 7 SKEWER LINE: 2+ Lancers -> Lancers +10% dmg
    if(lancers.length>=2){ on('skewer_line'); for(const u of lancers) u.nsDmg*=1.10; }
    // 8 CHAOS CREW: 1+ alive from each of all 4 factions -> ALL units +5% dmg +5% move
    if(NS_ALL_FACTIONS.every(f=>facs[f])){ on('chaos_crew'); for(const u of list){ u.nsDmg*=1.05; u.nsMove*=1.05; } }
    // 9 PUP SWARM: 3+ units of cost<=3 alive -> those +10% move
    if(cheap.length>=3){ on('pup_swarm'); for(const u of cheap) u.nsMove*=1.10; }
    // 10 BIG DOG ENERGY: 2+ Epic-or-better alive -> those +8% dmg
    if(bigs.length>=2){ on('big_dog'); for(const u of bigs) u.nsDmg*=1.08; }
    // ---- AK-CLASS: class-keyed combo expansion (TAXONOMY 3) ----
    // 11 KNUCKLE UP: 3+ Bruisers -> Bruisers +10% maxHp shield (shared pool)
    if(bruisers.length>=3){ on('bruiser_wall'); for(const u of bruisers) u.nsShieldPct+=0.10; }
    // 12 HIT SQUAD: 2+ Assassins -> Assassins +10% move, +6% dmg
    if(assassins.length>=2){ on('hit_squad'); for(const u of assassins){ u.nsMove*=1.10; u.nsDmg*=1.06; } }
    // 13 STREET SORCERY: 2+ Casters -> ability cooldowns refresh 15% faster
    if(casters.length>=2){ on('street_sorcery'); for(const u of casters) u.nsCd*=1.15; }
    // 14 FIRING LINE: 2+ Marksmen -> Marksmen +0.5 range
    if(marksmen.length>=2){ on('firing_line'); for(const u of marksmen) u.nsRangeAdd+=0.5; }
    // 15 PUPPY MILL: 2+ Summoners -> all friendly TOKENS +15% dmg
    if(summonerN>=2){ on('puppy_mill'); for(const u of list){ if(u.isToken) u.nsDmg*=1.15; } }
    // 16 LOCK AND KEY: Lockdown structure + 1+ Assassin -> +15% dmg vs locked
    // targets (the conditional bite lands in doAttack, under DMG_CAP)
    if(lockdownN>=1 && assassins.length>=1){ on('lock_and_key'); for(const u of assassins) u.nsLock=1.15; }
    // 17 DEAD AIR: 2+ silence-subtype units -> silence/jam durations +50%
    // (read at the silence + disable_tower cases via game.nsDeadAir)
    if(silencerN>=2){ on('dead_air'); deadAir[owner]=true; }
    // 18 BODYGUARD DETAIL: 1+ Bruiser + 2+ Supports -> Supports take 15% less
    // damage (rides the AK-ATTRS damage-taken path, combined floor 0.80)
    if(bruisers.length>=1 && clsSupports.length>=2){ on('bodyguard_detail'); for(const u of clsSupports) u.nsDefTaken=0.85; }
    // 19 WRECKING CREW: Structure + 1+ turret-breaker -> those +15% vs towers
    if(structs.length>=1 && wreckers.length>=1){ on('wrecking_crew'); for(const u of wreckers) u.nsWreck=1.15; }
    // 20 GRUDGE MATCH (account-flavored): the L6 nemesis is on the enemy
    // field -> ALL this side's units +5% dmg. Dormant until L6 ships rivals.
    if(nemesisOn[owner]){ on('grudge_match'); for(const u of list) u.nsDmg*=1.05; }
  }
  game.nsDeadAir = deadAir;   // AK-CLASS: per-side DEAD AIR duration flag
  game.namedSynergy = out;
}

// ==========================================================================
// AK-CLASS: LOCKDOWN archetype per-tick pass (TAXONOMY 1.3). Each planted
// Grid Lock rig HOLDS the nearest non-structure enemy in range (snare beam,
// refreshed while it stays in range -- one held target per rig) and keeps the
// 35% slow FIELD on every other enemy in range. Rides the existing
// snareTimer/slowTimer+slowMag timers; symmetric for the AI; same per-tick
// pattern as the Street Medics aura loop.
// ==========================================================================
function tickLockdownStructures(dt){
  if(!game || !dt) return;
  for(const u of game.units){
    if(!u.alive || !u.card || u.card.structArch!=='lockdown') continue;
    const r = effRange(u) + 0.5;            // the field reaches slightly past the gun
    const enemyOwner = 1-u.owner;
    let hold=null, hd=Infinity;
    for(const o of game.units){
      if(o.owner!==enemyOwner || !o.alive) continue;
      if(o.card && (o.card.type==='spell' || o.card.isStructure)) continue;
      const d=u.dist(o.x,o.y); if(d<=r && d<hd){ hd=d; hold=o; }
    }
    if(!hold) continue;
    if(hold.snareTimer<=0) statCC(u.owner, hold.owner, 'lock');   // AK-STATS: fresh holds only
    hold.snareTimer = Math.max(hold.snareTimer, 0.35);            // hold persists while in range
    for(const o of game.units){
      if(o.owner!==enemyOwner || !o.alive || o===hold) continue;
      if(o.card && (o.card.type==='spell' || o.card.isStructure)) continue;
      if(u.dist(o.x,o.y)<=r){
        if(o.slowTimer<=0) statCC(u.owner, o.owner, 'slow');      // AK-STATS: fresh slows only
        o.slowTimer = Math.max(o.slowTimer, 0.6);
        o.slowMag   = Math.max(o.slowMag, 0.35);
      }
    }
    // readable hold pulse on the victim (throttled; skipped under LOW_FX)
    u._lockFxT = (u._lockFxT||0) - dt;
    if(!_akLowFx && u._lockFxT<=0){
      u._lockFxT = 0.5;
      effects.push(fx('ring', hold.x, hold.y, '', '#9fe8ff', 0.4));
    }
  }
}

// ==========================================================================
// AK-FEEL B3: SEPARATION PASS -- bodies never stack. Pairwise relax, 2
// iterations, pushes split by mass ratio along the center line, capped at
// SEP_MAX_PUSH per unit per tick. Ground separates vs ground (and immovable
// structures/towers); air separates vs air; air ignores ground entirely.
// Board is <= ~80 actors -> brute-force pairs, no grid needed.
// ==========================================================================
function sepPush(u, px, py){
  if(u.card.isStructure) return;                 // structures are immovable bodies
  const mag = Math.hypot(px, py);
  if(mag <= 1e-9) return;
  const allow = Math.min(mag, u._sepBudget || 0);
  if(allow <= 0) return;
  const k = allow / mag;
  u._sepBudget -= allow;
  u.x = clamp(u.x + px*k, 0.5, 17.5);
  u.y = clamp(u.y + py*k, 0.5, 29.5);
}
function separationPass(dt){
  if(!game) return;
  const units = [];
  for(const u of game.units){
    if(!u.alive || (u.card && u.card.type==='spell')) continue;
    u._sepBudget = SEP_MAX_PUSH;                 // per-unit per-tick displacement cap
    units.push(u);
  }
  if(!units.length) return;
  const towers = [];
  for(const t of [...game.player.towers, ...game.opponent.towers]){ if(!t.destroyed) towers.push(t); }
  for(let it=0; it<SEP_ITERATIONS; it++){
    for(let i=0; i<units.length; i++){
      const a = units[i];
      const aAir = (a.card.domain||'ground')==='air';
      for(let j=i+1; j<units.length; j++){
        const b = units[j];
        if(aAir !== ((b.card.domain||'ground')==='air')) continue;  // air ignores ground
        const rs = Math.max(a.colR, SEP_VIS_R) + Math.max(b.colR, SEP_VIS_R);  // AK-SEP3: separate by visual size
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.hypot(dx, dy);
        if(d >= rs) continue;
        let nx, ny, overlap;
        if(d < 0.001){ const ang = a.id*2.4; nx = Math.cos(ang); ny = Math.sin(ang); overlap = rs; }  // deterministic split
        else { nx = dx/d; ny = dy/d; overlap = rs - d; }
        const aImm = a.card.isStructure, bImm = b.card.isStructure;
        if(aImm && bImm) continue;
        let aShare, bShare;
        if(aImm){ aShare = 0; bShare = 1; }
        else if(bImm){ aShare = 1; bShare = 0; }
        else { const tm = a.mass + b.mass; aShare = b.mass/tm; bShare = a.mass/tm; }
        if(aShare) sepPush(a, -nx*overlap*aShare, -ny*overlap*aShare);
        if(bShare) sepPush(b,  nx*overlap*bShare,  ny*overlap*bShare);
      }
      // towers: immovable colR 1.0 bodies on the ground plane (air flies over)
      if(!aAir && !a.card.isStructure){
        for(const t of towers){
          const rs = a.colR + t.colR;
          const dx = a.x - t.x, dy = a.y - t.y;
          const d = Math.hypot(dx, dy);
          if(d >= rs) continue;
          let nx, ny, overlap;
          if(d < 0.001){ const ang = a.id*2.4; nx = Math.cos(ang); ny = Math.sin(ang); overlap = rs; }
          else { nx = dx/d; ny = dy/d; overlap = rs - d; }
          sepPush(a, nx*overlap, ny*overlap);
        }
      }
    }
  }
}

// ==========================================================================
// AK-SEP2: SURROUND RING SLOTS (separation v2). Separation already runs for
// units IN COMBAT (separationPass never filters by state, attackers keep their
// full colR) -- the stacking came from every melee attacker pursuing the SAME
// point (the target's center). Fix: melee attackers on a shared target claim
// Clash-style slots on a contact ring around the victim. N slots per ring
// scales with the target's body size; overflow attackers take a SECOND ring a
// half-tile back and hold there until a contact slot frees up. Slots are
// recomputed once per frame (before the physics sub-steps) and each attacker
// greedily grabs the free slot nearest its current bearing, so allies fan
// around the ring instead of cork-screwing across each other.
// ==========================================================================
const SEP2_RING_STEP = 0.5;   // spec: overflow ring holds a half-tile back
const SEP2_MAX_RINGS = 4;     // beyond this just walk at the target (degenerate pile)
function assignSurroundSlots(){
  if(!game) return;
  const groups = new Map();   // target -> melee attackers
  for(const u of game.units){
    if(!u.alive || (u.card && u.card.type==='spell')) continue;
    u._slotRing = -1; u._slotX = undefined; u._slotY = undefined;  // clear stale slots
    if(u.card.isStructure || u.card.weaponType !== 'melee') continue;
    const t = targetValid(u.acquireTarget) ? u.acquireTarget
            : targetValid(u.target)        ? u.target : null;
    if(!t) continue;
    let g = groups.get(t);
    if(!g){ g = []; groups.set(t, g); }
    g.push(u);
  }
  for(const [t, atks] of groups){
    if(atks.length < 2) continue;                // a lone attacker walks straight in
    // closest attackers claim the contact ring first (stable tiebreak by id)
    atks.sort((a,b)=> (a.dist(t.x,t.y) - b.dist(t.x,t.y)) || (a.id - b.id));
    const tR = (t instanceof Tower) ? 1.0 : (t.colR || 0.45);
    let avgR = 0; for(const a of atks) avgR += a.colR; avgR /= atks.length;
    // AK-SEP2 FIX 2026-06-13: a slot is only valid if a unit standing on it can
    // actually ATTACK the target. The group's melee reach (max effRange among the
    // attackers) + the target radius is the farthest a ring may sit. Rings beyond
    // that put units OUT of attack range -- where stMove parks them on the slot,
    // unable to engage (d>eng) and unwilling to advance -> the frozen, never-firing
    // back-pile blob the operator hit. Overflow attackers past the reachable rings
    // get NO slot (_slotRing stays -1) so they press the target CENTER and keep
    // attacking/overlapping (separation nudges them) instead of freezing out of range.
    let maxReach = 0; for(const a of atks){ const er = effRange(a); if(er > maxReach) maxReach = er; }
    const maxRingR = tR + maxReach;     // farthest ring that can still land a hit
    let ring = 0, qi = 0;
    while(qi < atks.length && ring < SEP2_MAX_RINGS){
      const ringR = tR + avgR + ring*(SEP2_RING_STEP + avgR);
      if(ring > 0 && ringR > maxRingR) break;   // no out-of-range holding rings -> overflow presses center
      // capacity: adjacent slot chord >= ~2 attacker radii (bodies fit whole)
      const half = Math.asin(Math.min(1, (avgR*1.05) / ringR));
      const N = Math.max(3, Math.min(14, Math.floor(Math.PI / Math.max(half, 1e-4))));
      const off = (ring % 2) * (Math.PI / N);    // stagger rings so files interlock
      const taken = new Array(N).fill(false);
      const fill = Math.min(N, atks.length - qi);
      for(let k=0; k<fill; k++, qi++){
        const u = atks[qi];
        const ua = Math.atan2(u.y - t.y, u.x - t.x);
        let best = -1, bd = Infinity;
        for(let i=0; i<N; i++){
          if(taken[i]) continue;
          const sa = off + i*2*Math.PI/N;
          let dA = Math.abs(sa - ua) % (2*Math.PI);
          if(dA > Math.PI) dA = 2*Math.PI - dA;
          if(dA < bd){ bd = dA; best = i; }
        }
        taken[best] = true;
        const sa = off + best*2*Math.PI/N;
        u._slotRing = ring;
        u._slotX = clamp(t.x + Math.cos(sa)*ringR, 0.5, ARENA_W - 0.5);
        u._slotY = clamp(t.y + Math.sin(sa)*ringR, 0.5, ARENA_H - 0.5);
      }
      ring++;
    }
  }
}

// ==========================================================================
// AK-FEEL B4: KNOCKBACK + HIT-STOP. Impulses live on u.kbVx/kbVy, integrated
// in updateUnits BEFORE the state machine and decayed with tau = KB_TAU so a
// shove plays out over ~0.12s. kbImpulse displaces ~`tiles` total distance.
// ==========================================================================
function kbImpulse(u, nx, ny, tiles){
  if(!u || !u.alive || (u.card && u.card.isStructure)) return;
  const v0 = tiles / KB_TAU;          // exp-decay integral: v0*tau = tiles total travel
  u.kbVx += nx * v0;
  u.kbVy += ny * v0;
}
// Melee hit: victim pushback scaled by mass ratio, attacker recoil, hit-stop.
function applyKnockback(att, def){
  const ang = Math.atan2(def.y - att.y, def.x - att.x);
  const nx = Math.cos(ang), ny = Math.sin(ang);
  // attacker recoil: 0.15 tiles straight back (towers do not recoil; units do)
  if(att instanceof Unit) kbImpulse(att, -nx, -ny, 0.15);
  if(def instanceof Tower || (def.card && def.card.isStructure)){
    if(att instanceof Unit){ att.hitStop = Math.max(att.hitStop, HIT_STOP); }
    return;                            // structures/towers take 0 pushback
  }
  let push = clamp(0.45 * att.mass / def.mass, 0.10, 0.90);
  if(def.mass >= 2.4) push *= 0.25;    // heavies shrug most of it off
  kbImpulse(def, nx, ny, push);
  if(push >= 0.45){ sfxThump(push); haptic('knock'); }   // AK-AUDIO + AK-HAPTIC: a real shove lands with a thump
  // a big shove (>= 0.5 tiles) resets the victim's windup -> back to MOVE
  if(push >= 0.5 && (def.state===USTATE.WINDUP || def.state===USTATE.ACQUIRE || def.state===USTATE.ATTACK)){
    def.acquireTarget = null; enter(def, USTATE.MOVE);
  }
  // HIT-STOP: freeze both units' state machines for a beat (impact weight)
  if(att instanceof Unit) att.hitStop = Math.max(att.hitStop, HIT_STOP);
  def.hitStop = Math.max(def.hitStop, HIT_STOP);
}

function updateUnits(dt){
  for(const u of game.units){
    if(!u.alive){ if(u.deathTimer>=0) u.deathTimer+=dt; continue; }
    u.spawnTime+=dt;
    // AK-LIFETIME 2026-06-13 (Clash-Royale building model): structures + spawners
    // are NOT permanent. They tick down a lifetime and then crumble -- so the Pug
    // den (and every building) stops spawning / firing after its window instead of
    // an unkillable forever-pile. CR refs: huts 30s, Barb Hut 60s, towers ~30-40s.
    if(u.card.isStructure && u.lifeT!=null){
      u.lifeT -= dt;
      if(u.lifeT <= 0 && u.alive){ u.hp=0; u.alive=false; u.deathTimer=0; effects.push(fx('ring',u.x,u.y,'',PAL.smoke||'#888',0.6)); continue; }
    }
    if(u.abilityCD>0) u.abilityCD-=dt;
    if(u.hitFlash>0) u.hitFlash-=dt;
    if(u.slowTimer>0) u.slowTimer-=dt;
    if(u.dmgBuffT>0) u.dmgBuffT-=dt;
    // AK-HANDLER: tick the commander-stamped status timers (all undefined-falsy
    // with no handler -> these are no-ops on an unbuffed unit).
    if(u.markT>0) u.markT-=dt;
    if(u.revealed>0) u.revealed-=dt;
    if(u.stealthLock>0) u.stealthLock-=dt;
    if(u.handlerDRt>0) u.handlerDRt-=dt;
    if(u.spdBuffT>0) u.spdBuffT-=dt;
    if(u.stealthT>0) u.stealthT-=dt;
    if(u.kwRegenPct && u.alive && !(u.card && u.card.isStructure)) u.hp=Math.min(u.maxHp, u.hp + u.maxHp*u.kwRegenPct*dt);
    // AK-KW burn DoT: accumulate fractional damage, apply integer ticks via takeDamage (att=null -> no re-ignite, real death path).
    if(u.burnT>0){ u.burnT-=dt; u._burnAcc=(u._burnAcc||0)+(u.burnDps||0)*dt; if(u._burnAcc>=1 && u.alive){ var _bc=Math.floor(u._burnAcc); u._burnAcc-=_bc; u.takeDamage(_bc,u.x,u.y,false,null); if(u.alive) effects.push(fx('txt',u.x,u.y-0.5,'-'+_bc,'#ff5a2c',0.35)); } }
    if(u.evadeT>0) u.evadeT-=dt;
    if(u.invulnT>0) u.invulnT-=dt;
    if(u.silenceT>0) u.silenceT-=dt;
    if(u.muzzle>0) u.muzzle-=dt;
    if(u.snareTimer>0) u.snareTimer-=dt;   // SNARE roots movement (handled in getSpeed); attacks still allowed
    if(u.rootT>0) u.rootT-=dt;             // AK-FEEL B5: beam firing root
    // AK-FEEL B4: knockback impulse integrates BEFORE the state machine, then
    // decays exponentially (tau=KB_TAU) so a shove plays out over ~0.12s.
    if(u.kbVx!==0 || u.kbVy!==0){
      u.x = clamp(u.x + u.kbVx*dt, 0.5, 17.5);
      u.y = clamp(u.y + u.kbVy*dt, 0.5, 29.5);
      const dk = Math.exp(-dt/KB_TAU);
      u.kbVx *= dk; u.kbVy *= dk;
      if(Math.abs(u.kbVx)<0.02 && Math.abs(u.kbVy)<0.02){ u.kbVx=0; u.kbVy=0; }
    }
    // AK-FEEL B4: hit-stop -- both melee parties freeze their state machine a beat
    if(u.hitStop>0){ u.hitStop-=dt; continue; }
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
// AK-FEEL B2: engagement distance = effective range + the target's body radius
// (towers count a full 1.0). Units STOP at 95% of it and only RESUME pursuit
// past 110% (hysteresis kills the stop/start jitter; separation slides still
// nudge a holding unit without breaking the latch).
function engageDist(u, t){
  return effRange(u) + (t instanceof Tower ? 1.0 : (t.colR || 0.45));
}
function stMove(u,dt){
  if(u.atkCD>0) u.atkCD-=dt;
  findTarget(u);
  if(u.target){
    // AK-FEEL B2: stop-at-range with hysteresis (latch resets on target swap)
    if(u._engTgt !== u.target){ u._engTgt = u.target; u.engaged = false; }
    const eng = engageDist(u, u.target);
    const d = u.dist(u.target.x,u.target.y);
    if(u.engaged){ if(d > eng*ENGAGE_RESUME) u.engaged = false; }
    else if(d <= eng*ENGAGE_STOP) u.engaged = true;
    if(d <= eng){
      if(u.atkCD<=0){ u.acquireTarget=u.target; enter(u,USTATE.ACQUIRE); }
      // inside engage range with the attack recharging: HOLD position
    } else if(!u.card.isStructure && (!u.engaged || u.atkCD<=0)){
      // resume only past the 110% band -- unless the attack is ready and the
      // target slipped out of reach (close the gap instead of stalling)
      // AK-SEP2: melee attackers pursue their SURROUND RING SLOT, not the
      // target's center -- contact-ring units fan around the victim, overflow
      // ring units hold their spot a half-tile back until a slot frees.
      let gx = u.target.x, gy = u.target.y;
      if(u._slotRing >= 0 && u._slotX !== undefined){ gx = u._slotX; gy = u._slotY; }
      moveToward(u,gx,gy,dt);
    }
  } else if(!u.card.isStructure){
    u.engaged = false; u._engTgt = null;   // AK-FEEL B2: no target -> latch off
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
  if(u.stateTimer>=0.1){
    enter(u,USTATE.WINDUP);
    // AK-FEEL B5: melee LUNGE -- a 0.30-tile hop into the bite during windup
    // (kbV micro-impulse; the recoil in applyKnockback springs it back)
    if(u.card.weaponType==='melee' && u.acquireTarget){
      const a=Math.atan2(u.acquireTarget.y-u.y,u.acquireTarget.x-u.x);
      kbImpulse(u, Math.cos(a), Math.sin(a), 0.30);
    }
  }
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
  // AK-COMMIT 2026-06-13 (Clash-Royale targeting): once a unit locks a VALID
  // target it FINISHES it -- no per-frame target flicker. Only agile harass
  // classes (Assassin, Skirmisher) opportunistically retarget; everyone else
  // commits until the target dies or stops being legally hittable (lane/domain).
  // Structures retarget freely (slow turrets pick the nearest valid each scan).
  const agile = (u.card.role==='Assassin' || u.card.role==='Skirmisher' || u.card.isStructure);
  if(!agile && u.target){
    const t=u.target;
    let stillLegal = targetValid(t);
    if(stillLegal && t.alive!==undefined){            // a unit target (not a tower)
      if(!u.card.crossLane && laneOf(t.x)!==u.lane) stillLegal=false;
      if(!canHitDomain(u.card, (t.card&&t.card.domain)||'ground')) stillLegal=false;
      if(t.stealthT>0) stillLegal=false;              // AK-HANDLER: Slipstream -> drop the lock
    }
    if(stillLegal) return;                             // COMMIT -- keep the current target
  }
  u.target=null; let best=Infinity, bestFront=Infinity, frontTgt=null;
  const cross = u.card.crossLane;
  for(const o of game.units){
    if(o.owner===u.owner || !o.alive) continue;
    if(o.card && o.card.type==='spell') continue;          // spells are not board units
    if(o.stealthT>0) continue;                             // AK-HANDLER: Slipstreamed = untargetable
    if(!cross && laneOf(o.x)!==u.lane) continue;           // ignore the other lane's brawl
    if(!canHitDomain(u.card, o.card.domain||'ground')) continue; // air vs ground-only: skip
    const d=u.dist(o.x,o.y);
    if(o.frontline && d<bestFront && d<FRONTLINE_TAUNT_R){ bestFront=d; frontTgt=o; }   // AK-KW frontline taunt: a wall in range pulls aggro
    if(d<best){ best=d; u.target=o; }
  }
  if(frontTgt) u.target=frontTgt;                          // AK-KW: lock the frontline wall first
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
  if(u.nsAtkSpd && u.nsAtkSpd!==1) spd *= u.nsAtkSpd; // AK-SYNERGY: Turret Net attack-speed layer
  // Storm Clock attack-speed hook (no current buff sets it -> 1.0 no-op; kept ready
  // so a future event drops in as one more multiplier layer).
  if(game && game.eventMods && game.eventMods.atkSpeed!==1) spd *= game.eventMods.atkSpeed;
  // TAR SLOW also drags attack speed (-slowMag); legacy ability-slow leaves atk alone.
  if(u.slowTimer>0 && u.slowMag>0) spd *= (1 - u.slowMag);
  // AK-ATTRS: Garage Tuning ATK SPD -- permanent per-card mult (clamped 1.25
  // in snapshotPerks); one more layer on the existing stack, never a replace.
  if(u.tuneAspd) spd *= u.tuneAspd;
  return 1/spd;
}

// Effective attack range -- Alley Smog (Storm Clock) shrinks ranged units' range
// (-30%); melee (range 1) is unaffected. (spec sec 2.3.)
function effRange(u){
  let r = u.range;
  if(game && game.eventMods && u.card && u.card.range>=2) r *= game.eventMods.range;
  if(u.nsRangeAdd) r += u.nsRangeAdd;   // AK-SYNERGY: Spotter flat range bonus (Blasters)
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
      o.takeDamage(Math.floor(dmg), cx, cy, false, {owner:owner, card:attackerCard});   // AK-STATS
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
  if(u.stealthT>0) u.stealthT=0;   // AK-KEYWORDS: first attack breaks Hidden
  // Damage multiplier stack: ability dmg-buff x crew synergy (Targeting Net) x
  // Storm Clock field buff (Glass Bones), clamped at DMG_CAP (capped-stacking rule).
  let dmgMult = 1;
  if(u.dmgBuffT>0) dmgMult *= (u.dmgBuffMul||1.2);   // AK-HANDLER: War Cry can push 1.20->1.25; existing card buffs keep 1.2
  if(u.synergy && u.synergyMul && u.synergyMul.damage!==1.0) dmgMult *= u.synergyMul.damage; // Targeting Net (K9)
  if(u.nsDmg && u.nsDmg!==1) dmgMult *= u.nsDmg;            // AK-SYNERGY: named-synergy damage layer
  // AK-CLASS: LOCK AND KEY -- assassins cut deeper into CC-locked targets
  // (stun/snare/frozen > 0). One branch, inside the DMG_CAP clamp.
  if(u.nsLock>1 && !(u.target instanceof Tower) &&
     (u.target.stunTimer>0 || u.target.snareTimer>0 || u.target.frozenTimer>0)) dmgMult *= u.nsLock;
  // AK-CLASS: WRECKING CREW -- structure + turret-breaker = +15% vs towers
  // (covers melee bites AND ranged shots launched at a tower).
  if(u.nsWreck>1 && (u.target instanceof Tower)) dmgMult *= u.nsWreck;
  // AK-CLASS: RAMPING DAMAGE archetype -- damage climbs per consecutive hit
  // on the SAME target (+8%/hit, cap +40%); the counter resets on retarget.
  if(u.card.structArch==='ramper'){
    if(u._rampTgt!==u.target){ u._rampTgt=u.target; u._rampN=0; }
    else if(u._rampN<5) u._rampN++;
    if(u._rampN>0) dmgMult *= (1 + 0.08*u._rampN);
  }
  if(game && game.eventMods) dmgMult *= game.eventMods.dmg;                                   // Glass Bones layer
  if(dmgMult > DMG_CAP) dmgMult = DMG_CAP;
  let d=Math.floor(u.dmg * dmgMult);
  // AK-HANDLER: Shadow Assassin's Edge -- the stealth-exit hit crits once.
  if(u.critNext>1){ d=Math.floor(d*u.critNext); u.critNext=0; }
  if(u.twinStrike) d=Math.floor(d*2);   // AK-KW twin_strike: two hits land as one double-punch (works melee + ranged)
  const wt=u.card.weaponType;
  const pc=u.card.projColor;
  // muzzle flash on every shot (color = projColor, size by weaponType)
  u.muzzle=0.15;
  const muzzleSize = wt==='cannon'?0.5 : wt==='beam'?0.22 : wt==='lance'?0.3 : 0.32;
  effects.push({type:'muzzle',x:u.x,y:u.y,color:pc,size:muzzleSize,dur:0.12,t:0});
  sfxCard('atk_'+wt, u.card);   // AK-AUDIO: weapon-family hit, fattened by cost + faction-tinted
  haptic(wt);                   // AK-HAPTIC: weapon-family micro-pattern rides the same beat

  if(wt!=='melee'){
    // AK-AIR: is the target a flyer? (towers have no card -> ground)
    const tgtAir = !!(u.target && u.target.card && u.target.card.domain==='air');
    // spread = 3 pellets in a small fan; others = single typed projectile
    if(wt==='spread'){
      const baseA=Math.atan2(u.target.y-u.y,u.target.x-u.x);
      const pellet=Math.max(1,Math.floor(d/3));
      for(let i=-1;i<=1;i++){
        const a=baseA+i*0.18, reach=u.range*0.95;
        const tx=u.x+Math.cos(a)*reach, ty=u.y+Math.sin(a)*reach;
        launchProjectile(u.x,u.y,tx,ty,u.card.projSpeed,pellet,u.owner,pc,u.card,tgtAir,u);
      }
    } else {
      launchProjectile(u.x,u.y,u.target.x,u.target.y,u.card.projSpeed,d,u.owner,pc,u.card,tgtAir,u);
    }
    // AK-FEEL B5: per-weapon firing feel (kbV micro-impulses, numbers verbatim:
    // bullet 0.10 recoil hop / lance 0.10 brace / spread 0.20 recoil /
    // beam rooted 0.25s + 0.05 tremble, no recoil / cannon: impact handles it)
    {
      const fa=Math.atan2(u.target.y-u.y,u.target.x-u.x);
      const bx=-Math.cos(fa), by=-Math.sin(fa);   // straight back from the shot
      if(wt==='bullet')      kbImpulse(u, bx, by, 0.10);
      else if(wt==='lance')  kbImpulse(u, bx, by, 0.10);
      else if(wt==='spread') kbImpulse(u, bx, by, 0.20);
      else if(wt==='beam'){
        u.rootT = Math.max(u.rootT, 0.25);        // rooted while the beam holds
        const ta=(u.id*2.4)+u.spawnTime*37;       // deterministic tremble dir
        kbImpulse(u, Math.cos(ta), Math.sin(ta), 0.05);
      }
    }
    u.atkCD=atkInterval(u);
    return;
  }

  // ---- melee: instant slash arc + impact at the target, no projectile ----
  const ang=Math.atan2(u.target.y-u.y,u.target.x-u.x);
  effects.push({type:'slash',x:u.x,y:u.y,angle:ang,color:u.card.accent,dur:0.18,t:0});
  if(u.target instanceof Tower){
    u.target.takeDamage(d, u);   // AK-STATS: attacker rides along (lastHitBy + tallies)
    effects.push(fx('txt',u.target.x,u.target.y-0.4,'-'+d,PAL.red,0.5));
    sfx('towerhit'); haptic('tower_hit');   // AK-HAPTIC: tower crack
    if(game) game.shake += 4; // tower hit kick (Spec section 4)
    addBurst(u.target.x,u.target.y,pc,IMPACT_COUNT.melee);
    applyKnockback(u, u.target);   // AK-FEEL B4: towers take 0 push; attacker still recoils
    checkTowerDeath(u.target,u.owner);
  } else {
    u.target.takeDamage(d,u.x,u.y,false,u);   // AK-STATS: attacker rides along
    effects.push(fx('txt',u.target.x,u.target.y-0.4,'-'+d,PAL.red,0.45));
    addBurst(u.target.x,u.target.y,pc,IMPACT_COUNT.melee);
    if(u.target.alive) applyKnockback(u, u.target);   // AK-FEEL B4: melee shove + recoil + hit-stop
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
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2){ o.stunTimer=1.0; statCC(u.owner,o.owner,'lock'); } });   // AK-STATS
      announce('#FFD200'); break;
    case 'slow':
      // AK-CLASS: LOCKDOWN structures run the per-tick hold beam + slow field
      // (tickLockdownStructures) INSTEAD of the pulsed slow -- no double dip.
      if(u.card.structArch==='lockdown'){ fired=false; break; }
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.5){ o.slowTimer=2.5; statCC(u.owner,o.owner,'slow'); } });   // AK-STATS
      announce('#00BFFF'); break;
    case 'silence': {
      // AK-CLASS: DEAD AIR -- 2+ silence-subtype units stretch silence +50%
      const sDur = 1.2 * ((game.nsDeadAir && game.nsDeadAir[u.owner]) ? 1.5 : 1);
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.5){ o.silenceT=sDur; statCC(u.owner,o.owner,'silence'); } });   // AK-STATS
      announce('#9aa'); break;
    }
    case 'heal':
      game.units.forEach(o=>{ if(o.owner===u.owner&&o.alive&&u.dist(o.x,o.y)<=2.2){ o.hp=Math.min(o.maxHp,o.hp+Math.floor(o.maxHp*0.06)); } });
      announce(PAL.ok); break;
    case 'crit':
      u.dmgBuffT=3; announce('#FF8800'); break;
    case 'teleport':
      if(u.target){ const a=u.owner===0?-1:1; u.y+=a*2.0; } announce('#9aa'); break;
    case 'disable_tower': {
      // AK-CLASS: DEAD AIR stretches the tower jam +50% too (same subtype)
      const jDur = 1.5 * ((game.nsDeadAir && game.nsDeadAir[u.owner]) ? 1.5 : 1);
      const t=(u.owner===0?game.opponent:game.player).towers.find(t=>!t.destroyed);
      if(t){ t.disableTimer=jDur; statCC(u.owner,t.owner,'silence'); } announce('#7B5CFF'); break;   // AK-STATS
    }
    case 'turret_break':
    case 'pierce':
      u.dmgBuffT=3; announce('#00E0C0'); break;
    case 'ramp':
      // AK-CLASS: STATIC TURRET archetype -- a timed burst-fire window every
      // cooldown (crit-style dmg buff), OFF the ramp code path. RAMPER
      // archetype stays passive here: its per-target climb lives in doAttack.
      if(u.card.structArch==='turret'){ u.dmgBuffT=2.5; announce('#FF8800'); }
      else fired=false;
      break;
    case 'spawn':
      // AK-CLASS: SPAWNER NEST archetype -- planted dens spawn on a repeating
      // cooldown, capped at 4 alive tokens per nest. A capped nest burns no
      // cooldown, so the next pup pops the moment a slot frees.
      if(u.card.structArch==='nest'){
        let mine=0;
        for(const o of game.units){ if(o.alive && o.isToken && o.spawnedBy===u.id) mine++; }
        if(mine>=4){ fired=false; break; }
      }
      // simple drone: a weak fast melee ally
      spawnDrone(u); announce('#00E0C0'); break;
    case 'knockback':
      // shove the struck unit back toward its OWN side (sign was inverted -- it used to pull attackers in)
      // AK-FEEL B4: still 1.2 tiles, but as a kbV impulse instead of a teleport snap
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=1.8){ const dir=(o.owner===0)?1:-1; kbImpulse(o, 0, dir, 1.2); statCC(u.owner,o.owner,'knock'); } });   // AK-STATS
      announce('#C9772E'); break;
    case 'evasion': u.evadeT=2; announce('#9aa'); break;
    case 'invuln': u.invulnT=1.0; announce('#9aa'); break;
    case 'aoe':
    case 'chain':
      game.units.forEach(o=>{ if(o.owner===enemyOwner&&o.alive&&u.dist(o.x,o.y)<=2.0){ o.takeDamage(Math.floor(u.dmg*0.5),u.x,u.y,true,u); } });   // AK-ATTRS: ability damage -> spdef; AK-STATS: attacker
      announce('#FF8800'); break;
    case 'double':
      if(u.target && targetValid(u.target)){
        if(u.target instanceof Tower) u.target.takeDamage(Math.floor(u.dmg*0.5), u);   // AK-STATS: tower path takes (d, att)
        else if(u.target.takeDamage) u.target.takeDamage(Math.floor(u.dmg*0.5), u.x, u.y, true, u);   // AK-ATTRS: ability damage -> spdef; AK-STATS: attacker
        // crown-count a tower killed by Twin Strike (was a silent match-stall: king died, match never ended)
        if(u.target instanceof Tower) checkTowerDeath(u.target,u.owner);
      } announce('#FF2E88'); break;
    default: fired=false;
  }
  if(fired){
    sfxCard('ability', u.card);   // AK-AUDIO: per-card ability trigger (was silent)
    // AK-PERSONA: per-card ability-fired tally (rap-sheet ab). Player units
    // only; tokens already returned at the top -- display only, no balance.
    if(u.owner===0 && game && game.stats && u.card && u.card.cardNumber){
      game.stats.abilitiesByCard[u.card.cardNumber]=(game.stats.abilitiesByCard[u.card.cardNumber]||0)+1;
    }
    let cd=u.card.abilityCD;
    // Override (Leashbreak synergy): cooldowns refresh ~25% faster -> shorter recharge.
    if(u.synergy && u.synergyMul && u.synergyMul.cdRefresh>1.0) cd/=u.synergyMul.cdRefresh;
    if(u.nsCd && u.nsCd>1) cd/=u.nsCd;   // AK-CLASS: STREET SORCERY refresh layer (same one-line pattern)
    u.abilityCD=cd;
  }
}
function spawnDrone(parent){
  // Hard board cap: a recursive spawn-storm (drones cloned from a Spawner card kept
  // spawning their own drones) ballooned to ~1000 units and froze the phone mid-match.
  // Never let the field grow past what a phone renders at 60fps.
  if(game.units.length >= 140) return;
  let base = CARDS['Pixel Pug'] || parent.card;
  // AK-CLASS: Pixel Pug is reclassed to a PLANTED STATIC (nest archetype) --
  // spawned TOKENS must keep their legs, so they ride a one-time mobile clone
  // of the card (isStructure off, Fast pace back on). CARDS never mutates.
  if(base.isStructure){
    if(!base._akTokenCard) base._akTokenCard = Object.assign({}, base, { isStructure:false, structArch:null, speed:1.85, speedTier:'Fast' });
    base = base._akTokenCard;
  }
  const drone = new Unit(base, parent.owner, parent.x+(Math.random()-0.5), parent.y+(parent.owner===0?-0.6:0.6));
  drone.lane = parent.lane; // drone fights in its spawner's lane
  drone.maxHp=drone.hp=300; drone.dmg=40; // weak token
  computeBulk(drone);   // AK-FEEL B3: token body matches its 300hp, not the parent card's
  drone.isToken=true; drone.abilityCD=Infinity; // a token can NEVER spawn (kills the recursion)
  drone.spawnedBy=parent.id;   // AK-CLASS: nest token-cap accounting
  if(parent.owner===0 && game.stats) game.stats.tokensSpawned++;   // AK-STATS: RAT KING quest fuel
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
      inArea().forEach(o=>{ o.frozenTimer = Math.max(o.frozenTimer,dur); statCC(owner,o.owner,'lock'); });   // AK-STATS: freeze = LOCK subtype
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-x,t.y-y)<=r) t.disableTimer=Math.max(t.disableTimer,dur); });
      effects.push({type:'spell_freeze',x,y,color:'#9fe8ff',radius:r,dur:dur,t:0});
      sfx('ability');
      break;
    }
    case 'slow': {
      // TAR SLOW: -35% move + -35% atk speed for `dur`.
      inArea().forEach(o=>{ o.slowTimer=Math.max(o.slowTimer,dur); o.slowMag=card.slowPct||0.35; statCC(owner,o.owner,'slow'); });   // AK-STATS
      effects.push({type:'spell_slow',x,y,color:'#3a2a14',radius:r,dur:dur,t:0});
      sfx('ability');
      break;
    }
    case 'trap': {
      // SNARE TRAP: plant a hidden, armed trap. Triggers on enemy cross -> root + dmg.
      // cap armed traps per side at 6 -- planting over cap retires the oldest
      const armed = game.traps.filter(t2=> t2.owner===owner && !t2.triggered);
      if(armed.length >= 6) game.traps.splice(game.traps.indexOf(armed[0]),1);
      game.traps.push({ owner:owner, x:x, y:y, radius:r, dmg:dmg, duration:dur,
                        armT:0.5, triggered:false, life:0 });
      effects.push({type:'spell_trap_set',x,y,color:'#00E0C0',radius:r,dur:0.6,t:0});
      sfx('ability');
      break;
    }
    case 'zap': {
      // JOLT: instant AOE damage + 0.5s stun. Kills swarms, resets attacks.
      inArea().forEach(o=>{ o.takeDamage(dmg,x,y,true,{owner:owner,card:card}); o.stunTimer=Math.max(o.stunTimer,dur||0.5); statCC(owner,o.owner,'lock'); addBurst(o.x,o.y,'#7fefff',5); });   // AK-ATTRS: spell damage -> spdef; AK-STATS: zap stun = LOCK
      effects.push({type:'spell_zap',x,y,color:'#9fe8ff',radius:r,dur:0.4,t:0});
      if(game) game.shake += 3;
      sfx('ability');
      break;
    }
    case 'strike': {
      // STRIKE: medium AOE burst damage (the fireball). Hits units AND towers.
      inArea().forEach(o=>{ o.takeDamage(dmg,x,y,true,{owner:owner,card:card}); addBurst(o.x,o.y,'#FF8800',7); });   // AK-ATTRS: spell damage -> spdef; AK-STATS: attacker
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-x,t.y-y)<=r){ t.takeDamage(Math.floor(dmg*0.5),{owner:owner,card:card}); checkTowerDeath(t,owner); } });   // AK-STATS
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
            statCC(tr.owner,o.owner,'lock');   // AK-STATS: snare = LOCK subtype
            o.takeDamage(tr.dmg||0,tr.x,tr.y,true,{owner:tr.owner,card:null});   // AK-ATTRS: trap fire -> spdef
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
      statCC(t.owner, tt.owner, 'silence');   // AK-STATS: gate jam = silence taken
      effects.push(fx('ability', t.x, t.y-1, 'GATE OVERRIDE', '#7B5CFF', 0.9)); }
  } else { // 'zap'
    let best=null,bd=8; game.units.forEach(u=>{ if(u.owner===0&&u.alive){ const d=Math.hypot(u.x-t.x,u.y-t.y); if(d<bd){bd=d;best=u;} } });
    if(best){ best.takeDamage(Math.floor(t.dmg*1.6), t.x, t.y, true); best.stunTimer=Math.max(best.stunTimer,0.4); statCC(t.owner, best.owner, 'lock');   // AK-ATTRS: gate zap = ability -> spdef; AK-STATS: stun taken
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
      launchProjectile(t.x,t.y,tgt.x,tgt.y,7,t.dmg,t.owner,t.owner===0?PAL.blue:PAL.red,
        null,(tgt.card&&tgt.card.domain==='air'));   // AK-AIR: towers angle UP at flyers
      t.atkCD=1/t.atkSpd;
    }
  }
}

// ---- PROJECTILES (parabolic arc, v8 pattern) ----
// `card` (optional) supplies the visual contract: shape/size/projSpeed and
// whether the bolt leaves a trail. Towers pass shape:'dot'. (Spec section 3/5.)
// AK-AIR: optional `tgtAir` flags an airborne target so the renderer can angle
// the bolt UP to the flyer's elevated draw point; `srcAir` (from the firing
// card's domain) angles DOWN from a flyer to the ground shadow point. Pure
// visual metadata -- physics/impact logic is untouched.
function launchProjectile(fx0,fy0,tx,ty,speed,dmg,owner,color,card,tgtAir,src){
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
    card: card||null, src: src||null,   // AK-KW/AK-EVO: the firing UNIT -> ranged hits get burn/deadly + kill-streak credit
    splash: !!(card && card.splash), splashRadius: card?card.splashRadius:0,
    targets: card ? (card.targets||'both') : 'both',
    // AK-AIR: elevation language for the renderer (up-shots vs down-shots)
    srcAir: !!(card && card.domain==='air'), tgtAir: !!tgtAir
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
      if(best){
        best.takeDamage(p.dmg,p.sx,p.sy,false, p.src || {owner:p.owner,card:p.card}); effects.push(fx('txt',best.x,best.y-0.4,'-'+p.dmg,PAL.red,0.4));   // AK-STATS (p.src = firing unit -> ranged burn/deadly/evo)
        // AK-FEEL B4: cannon shells shove a flat 0.30 tiles along the shot line
        // (same mass resist as melee); bullet/lance/beam/spread shove 0.
        if(p.weaponType==='cannon' && best.alive && !(best.card && best.card.isStructure)){
          let push = 0.30;
          if(best.mass >= 2.4) push *= 0.25;
          const dd = Math.hypot(p.tx-p.sx, p.ty-p.sy) || 1;
          kbImpulse(best, (p.tx-p.sx)/dd, (p.ty-p.sy)/dd, push);
        }
      }
      // SPLASH: cannon/spread/identity-splash projectiles damage a radius on impact
      if(p.splash && p.card){ applySplash(p.card,p.owner,p.tx,p.ty,Math.floor(p.dmg*0.6),p.splashRadius,best,p.color); }
      const eTowers=(p.owner===0?game.opponent:game.player).towers;
      let hitTower=false;
      eTowers.forEach(t=>{ if(!t.destroyed && Math.hypot(t.x-p.tx,t.y-p.ty)<=1.3){ t.takeDamage(p.dmg,{owner:p.owner,card:p.card}); sfx('towerhit'); haptic('tower_hit'); hitTower=true; checkTowerDeath(t,p.owner); } });   // AK-STATS: attacker envelope
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
  ai.aiCD=0;
  if(game.aiCurve){
    // AK-AICURVE (AK-FEEL): world runs use the 1..400 curve's cadence + sloppy
    // knobs INSTEAD of the DIFFICULTY formulas (no double-ramp).
    ai.aiNext = game.aiCurve.aiNextBase + Math.random()*1.2;
    if(Math.random() < game.aiCurve.sloppyChance){ ai.aiNext += 1.2; }   // rookie hesitation
  } else {
    ai.aiNext=Math.max(1.0,(4.6-DIFFICULTY*0.36))+Math.random()*1.3;  // D0 ~5s (sluggish, easy) -> D9 ~2s (aggressive)
    // On easy tiers the AI also plays dumb: random card, not the best counter.
    if(DIFFICULTY<=2 && Math.random()<0.6){ ai.aiNext+=1.2; }
  }
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
      return;
    }
    // spell on cooldown / no target -- fall through to the best playable TROOP
    const troops = playable.filter(p=>p.c.type!=='spell');
    if(!troops.length) return;
    pick = troops.sort((a,b)=>(b.c.dmg||b.c.damage||0)-(a.c.dmg||a.c.damage||0))[0];
  }
  deploy(ai,pick.i,gx,gy);
}

// ---- WIN / CROWNS ----
// AK-WORLD: stamp the elapsed clear time for the CURRENT section the moment its
// Gate falls (called BEFORE advanceSection moves the cursor). World map reads
// game.sectionClearTimes for time-tier scoring; never affects engine timing.
function recordSectionClear(){
  if(!game || !game.sectionClearTimes) return;
  const elapsed = Math.max(0, MATCH_TIME - game.time);
  game.sectionClearTimes[game.section] = Math.round(elapsed*10)/10;
}
function checkTowerDeath(t,attackerOwner){
  if(!t.destroyed || t.crownCounted) return;
  t.crownCounted=true;
  if(t.owner===0 && game && game.stats) game.stats.towersLost++;   // AK-STATS
  if(game) game.shake += 12; // tower destroyed = big kick (Spec section 4)
  haptic(t.type==='king'?'gate_down':'tower_down', true);   // AK-HAPTIC: tower-destroyed rumble (bypasses the tick throttle)
  // ---- CONVOY: enemy king = the District Gate; player king down = defeat ----
  if(game.convoyMode){
    if(t.type==='king' && t.owner===1 && attackerOwner===0){
      game.player.crowns += 1; game.stars=(game.stars||0)+1;     // Gate cleared +1 + a star
      game.gateClearedThisSection = true;
      game.gatesCleared = Math.max(game.gatesCleared, game.section+1);
      recordSectionClear();   // AK-WORLD
      addBurst(t.x,t.y,PAL.gold,18);
      effects.push(fx('crown',t.x,t.y-1,'GATE DOWN',PAL.gold,1.5));
      grantGateReward();
      spawnGatePinata(t);                      // AK-LOOT: gate clear = LOOT PINATA (straight to stash)
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
    if(t.owner===1 && attackerOwner===0) spawnTowerLoot(t);   // AK-LOOT: deterministic princess drop
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
  if(t.owner===1 && attackerOwner===0 && t.type!=='king') spawnTowerLoot(t);   // AK-LOOT
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
  if(t.owner===0 && game && game.stats) game.stats.towersLost++;   // AK-STATS
  if(game) game.shake += 10;
  haptic(t.type==='king'?'gate_down':'tower_down', true);   // AK-HAPTIC: hazard tower-down rumble too
  if(game.convoyMode && t.type==='king'){
    if(t.owner===0){ game.opponent.crowns=Math.max(game.opponent.crowns,3); endMatch(); return; }
    game.player.crowns += 1; game.stars=(game.stars||0)+1;
    game.gateClearedThisSection=true; game.gatesCleared=Math.max(game.gatesCleared,game.section+1);
    recordSectionClear();   // AK-WORLD
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
  if(!game.result){   // AK-MODE: a mode (C3) may preset the result; only recompute from crowns when it didn't
  if(game.player.crowns>game.opponent.crowns) game.result='win';
  else if(game.opponent.crowns>game.player.crowns) game.result='lose';
  else {
    // tiebreak on PERCENT HP of the CURRENT section's towers (enemy towers rebuild
    // fresh each district -- raw HP would hand the AI every clock-out)
    const pct = ts=>{ let hp=0,mx=0; ts.forEach(t=>{ mx+=t.maxHp; if(!t.destroyed) hp+=t.hp; }); return mx? hp/mx : 0; };
    const ph=pct(game.player.towers), oh=pct(game.opponent.towers);
    game.result = ph>oh?'win':oh>ph?'lose':'draw';
  }
  }
  // AK-LOOT: win/timer/draw banks ALL unbanked loot; a LOSS keeps 50% of the
  // unbanked commons (rounded down per type) and 100% of Epic+ shards.
  lootFinalBank(game.result==='lose');
  sfx(game.result==='win'?'win':'lose');
}

// ---- EFFECTS + PARTICLES ----
function fx(type,x,y,text,color,dur){ return {type,x,y,text,color,dur:dur||1,t:0}; }

// AK-LORE: deploy tagline flash -- floats the card's lore tagline near the
// spawn on the PLAYER's first deploy of that card each match. Throttled to
// one flash per 2.5s so spam/cycle decks never flood the board; LOW_FX skips
// entirely; headless harness (no cards_lore.js loaded) no-ops via the guard.
function loreFlash(card, x, y){
  try{
    if(_akLowFx || !game || !card) return;
    if(typeof window==='undefined' || typeof window.AK_LORE_GET!=='function') return;
    if(!game._loreSeen) game._loreSeen={};
    if(game._loreSeen[card.name]) return;                      // once per card per match
    if(game._loreLastT!=null && (game._loreLastT - game.time) < 2.5) return;   // game.time counts DOWN
    const L=window.AK_LORE_GET(card.cardNumber);
    if(!L || !L.tagline) return;
    game._loreSeen[card.name]=true; game._loreLastT=game.time;
    effects.push(fx('txt', x, y-0.9, '"'+L.tagline+'"', PAL.gold, 1.5));
  }catch(_e){}
}
function updateEffects(dt){ effects.forEach(e=>{e.t+=dt; if(e.type==='txt'||e.type==='ability'||e.type==='crown') e.y-=dt*0.6;}); effects=effects.filter(e=>e.t<e.dur); }
function addBurst(x,y,color,n){ for(let i=0;i<n;i++){ const a=Math.random()*Math.PI*2,s=1+Math.random()*3; particles.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,t:0,dur:0.4+Math.random()*0.3,color,sz:0.06+Math.random()*0.05}); } }
function updateParticles(dt){ particles.forEach(p=>{p.t+=dt;p.x+=p.vx*dt*1.5;p.y+=p.vy*dt*1.5;}); particles=particles.filter(p=>p.t<p.dur); if(particles.length>240) particles=particles.slice(-240); }

// ---- AUDIO (WebAudio, no assets) ----
let AC=null;
function getAC(){ if(!AC){ try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){} } return AC; }

// ==========================================================================
// AK-AUDIO: per-card sound identity (procedural, zero new assets).
// Every card derives a DETERMINISTIC voice from its canon data:
//   - breed size class -> bark pitch + length (bigger dog = deeper, slower)
//   - weaponType       -> attack sound family (melee thud / bullet snap /
//                         cannon boom / beam whine / lance / spread)
//   - cost             -> fattens the hit (deeper + longer tail)
//   - rarity           -> subtle shimmer layer (Mythic the most)
//   - faction          -> timbre tint (detune cents + lowpass + osc flavor)
// Discipline: ONE shared AudioContext, master gain ~0.5 into a compressor
// (no clipping), hard cap of AK_VOICE_CAP concurrent voices, LOW_FX drops the
// shimmer layer, mute persisted to localStorage 'ak_muted', and every call is
// try/catch'd so the headless node harness no-ops cleanly.
// ==========================================================================
const AK_VOICE_CAP = 8;          // AK-AUDIO: hard concurrency cap
let _akVoices = 0;
let _akMaster = null;
let _akLowFx  = false;           // fed by index.html FPS sampler via AK.setAudioLow
let _akMuted  = false;
try{ _akMuted = (typeof localStorage!=='undefined' && localStorage.getItem('ak_muted')==='1'); }catch(e){}

function akMaster(){             // AK-AUDIO: master gain ~0.5 -> compressor -> out
  const ac=getAC(); if(!ac) return null;
  if(!_akMaster){
    try{
      const m = ac.createGain();
      m.gain.value = _akMuted ? 0 : 0.5;
      let out = ac.destination;
      try{ const comp = ac.createDynamicsCompressor(); comp.connect(ac.destination); out = comp; }catch(e){}
      m.connect(out);
      _akMaster = m;
    }catch(e){ _akMaster=null; }
  }
  return _akMaster;
}
function akSetMuted(m){
  _akMuted=!!m;
  try{ if(_akMaster) _akMaster.gain.value = _akMuted?0:0.5; }catch(e){}
  // AK-SPEAK: muting also silences any in-flight spoken tagline immediately
  try{ if(_akMuted && akSpeechAvail()) window.speechSynthesis.cancel(); }catch(e){}
  try{ if(_akMuted) akStopClip(); }catch(e){}
}

// AK-VIBES: AnalyserNode tap off the master chain. PURE tap -- the master keeps
// its existing route to the compressor/destination; the analyser has NO output,
// it only listens. index.html also feeds the BGM media-element decks into it so
// the arena edge glow hears the music, not just the SFX. Lazy, cached, and
// fully guarded so the headless harness (stub AC without createAnalyser) no-ops.
let _akAnalyser = null;
function akAnalyser(){
  const ac=getAC(); if(!ac) return null;
  if(!_akAnalyser){
    try{
      if(!ac.createAnalyser) return null;
      const an = ac.createAnalyser();
      an.fftSize = 256;                 // 128 bins -- cheap to read at 30Hz
      an.smoothingTimeConstant = 0.55;  // pre-smooth so the JS envelope stays simple
      const m = akMaster(); if(m) m.connect(an);
      _akAnalyser = an;
    }catch(e){ _akAnalyser=null; }
  }
  return _akAnalyser;
}
function akVoiceFree(){ return _akVoices < AK_VOICE_CAP; }
function akVoiceTake(node, dur){ // count a voice; release on ended OR timer (belt+braces)
  _akVoices++;
  let done=false; const rel=()=>{ if(!done){ done=true; _akVoices=Math.max(0,_akVoices-1); } };
  try{ node.onended = rel; }catch(e){}
  try{ if(typeof setTimeout!=='undefined') setTimeout(rel, ((dur||0.5)*1000)+250); }catch(e){}
}

// AK-AUDIO: breed -> size class 0..4 (tiny..giant). Bigger = deeper + slower bark.
const BREED_SIZE = {
  'Pomeranian':0,'Shih Tzu':0,'Pug':0,'Jack Russell':0,'Dachshund':0,
  'Corgi':1,'Beagle':1,'Sheltie':1,'Basenji':1,'Terrier':1,'Schnauzer':1,'Shiba Inu':1,'Whippet':1,
  'Border Collie':2,'Spaniel':2,'Poodle':2,'Basset':2,'Australian Cattle Dog':2,'Samoyed':2,
  'Vizsla':2,'Pointer':2,'Setter':2,'Foxhound':2,'Dalmatian':2,
  'Boxer':3,'Husky':3,'Retriever':3,'German Shepherd':3,'Malinois':3,'Doberman':3,'Airedale':3,
  'Greyhound':3,'Saluki':3,'Chow':3,'Bulldog':3,'Akita':3,'Dogo Argentino':3,
  'Rottweiler':4,'Cane Corso':4,'Bullmastiff':4,'Mastiff':4,'St. Bernard':4,'Newfoundland':4
};
// AK-AUDIO: faction timbre tint -- detune (cents), lowpass cutoff (Hz), osc flavor
const FACTION_TIMBRE = {
  boneguard_crew:    { detune:-30, filter:1500, osc:'square'   },  // heavy + dark
  k9_circuitry:      { detune: 35, filter:5500, osc:'sawtooth' },  // electric + bright
  leashbreak_tactix: { detune: 10, filter:2800, osc:'sawtooth' },  // raw street grit
  zoomie_syndicate:  { detune: 60, filter:4200, osc:'triangle' }   // zippy + light
};
const FACTION_TIMBRE_DEF = { detune:0, filter:3000, osc:'sawtooth' };
const RARITY_SHIMMER = { Common:0, Rare:0.05, Epic:0.08, Legendary:0.12, Mythic:0.17 };

// AK-AUDIO: deterministic per-card voice, cached on the card object
function cardVoice(card){
  if(!card) return null;
  if(card._akVoice) return card._akVoice;
  const size = (BREED_SIZE[card.breed]!=null) ? BREED_SIZE[card.breed] : 2;
  const h = (card.silhouetteSeed || hashStr(card.name||'?'))>>>0;
  const jit = ((h % 97)/97 - 0.5)*0.14;                 // +-7% per-card pitch fingerprint
  card._akVoice = {
    size: size,
    pitch: Math.max(70,(330 - size*52)*(1+jit)),        // tiny ~330Hz .. giant ~120Hz
    vdur:  0.09 + size*0.04,                            // giants roll the bark out slower
    fat:   clamp((card.cost||3)/7, 0.35, 1),            // cost fattens the hit
    tint:  FACTION_TIMBRE[card.faction] || FACTION_TIMBRE_DEF,
    shimmer: RARITY_SHIMMER[card.rarity]||0
  };
  return card._akVoice;
}

// ==========================================================================
// AK-SPEAK: spoken taglines via window.speechSynthesis (zero new assets).
// Operator canon 2026-06-12: "it needs to be audible, not just observable --
// the text is their voice." When a card deploys (and when its detail overlay
// opens) the lore tagline is SPOKEN. Voice character derives from the SAME
// breed-size system as the barks: giants = pitch ~0.6-0.8 + rate ~0.85,
// tiny dogs = pitch ~1.3-1.6 + rate ~1.2; faction detune nudges pitch a hair.
// Volume sits modestly UNDER the SFX bed. Respects ak_muted AND its own
// ak_voice toggle (index.html VOICE chip, default ON). Throttle: max one
// spoken line per ~4s, and cancel() before every speak so lines never
// overlap. Deliberately KEPT under LOW_FX (speech is cheap -- no canvas work,
// no WebAudio voices burned). Fully guarded: headless node / browsers without
// speechSynthesis no-op cleanly.
// ==========================================================================
let _akVoiceOn = true;          // AK-SPEAK: VOICE chip state, persisted by index.html to ak_voice
try{ _akVoiceOn = !(typeof localStorage!=='undefined' && localStorage.getItem('ak_voice')==='0'); }catch(e){}
let _akSpeakLast = -1e9;        // AK-SPEAK: global ~4s throttle clock (ms)
function akSpeechAvail(){       // AK-SPEAK: feature gate (headless node = false)
  try{ return typeof window!=='undefined' && !!window.speechSynthesis && typeof window.SpeechSynthesisUtterance==='function'; }catch(_e){ return false; }
}
// ==========================================================================
// AK-VOICEVAR: spread spoken taglines across EVERY available en-* device voice
// instead of letting one (usually female) default voice dominate. Each card is
// assigned a voice DETERMINISTICALLY seeded by its cardNumber, so a given card
// always sounds the same while the roster fans out across the whole installed
// voice set. The breed-size pitch/rate fingerprint (akSpeechCharacter) still
// layers ON TOP. Where a card name/breed leans male or female we PREFER a
// matching-gender voice; otherwise the full en-* pool is used (max spread).
// getVoices() is frequently empty on first call -- we listen for
// 'voiceschanged' and rebuild the table (bumping a generation counter so cached
// per-card picks invalidate) when the list finally arrives. If the list never
// populates we return null and akSpeak falls back to pitch/rate-only variation.
// Fully guarded: headless node (no speechSynthesis) no-ops cleanly.
// ==========================================================================
let _akSpkVoices  = [];        // AK-VOICEVAR: sorted en-* voice list (deterministic order)
let _akSpkVoicesF = [];        // AK-VOICEVAR: female-leaning subset
let _akSpkVoicesM = [];        // AK-VOICEVAR: male-leaning subset
let _akSpkVoiceGen = 0;        // AK-VOICEVAR: bumped on every rebuild -> invalidates per-card cache
let _akSpkVoicesBound = false; // AK-VOICEVAR: voiceschanged listener attached once
// label hints that classify a DEVICE voice as female / male
const _AK_VOICE_F = ['female','woman','girl','samantha','victoria','karen','moira','tessa','fiona','veena','kanya','susan','zira','hazel','catherine','allison','ava','serena','kate','joana','amelie','anna','caroline','vicki','ellen','nora','paulina','sara','yuna','kyoko','luciana','monica','paola','alice','aria','jenny','michelle','nadia','sonia','clara','emma','olivia','sophia'];
const _AK_VOICE_M = ['daniel','alex','fred','aaron','arthur','oliver','thomas','rishi','gordon','jorge','juan','diego','carlos','david','mark','george','james','ralph','albert','bruce','reed','liam','ryan','christopher','eric','brian','tony','xander','rocko'];
function _akVoiceGender(v){          // AK-VOICEVAR: 'f' | 'm' | '?' from a voice label
  try{
    const n=String((v&&(v.name||v.voiceURI))||'').toLowerCase();
    if(/\b(female|woman|girl)\b/.test(n)) return 'f';   // checked BEFORE 'male' (female contains 'male')
    if(/\b(male|man|boy)\b/.test(n))      return 'm';
    for(let i=0;i<_AK_VOICE_F.length;i++){ if(n.indexOf(_AK_VOICE_F[i])>=0) return 'f'; }
    for(let i=0;i<_AK_VOICE_M.length;i++){ if(n.indexOf(_AK_VOICE_M[i])>=0) return 'm'; }
  }catch(_e){}
  return '?';
}
// card-name / breed hints that lean a CARD male or female (soft, where possible)
const _AK_CARD_F = ['saint','lady','queen','princess','duchess','diva','belle','bella','luna','daisy','rosa','rosie','stella','roxy','misty','pearl','ruby','aurora','willow','ivy','sasha','zoey','coco','dame','empress','maiden','siren','vixen'];
const _AK_CARD_M = ['bcardd','bacardi','dealer','king','duke','brutus','bruno','rocky','balboa','rosco','baron','lord','butch','spike','hunter','ranger','chief','tyson','zeus','thor','hercules','gunner','bullet','diesel','warhorse','bonecrusher','capo','boss','don','gambler','ace','jack','duke','rex','max','tank','rambo','bandit','sarge','colonel','general'];
function _akCardGender(card){        // AK-VOICEVAR: infer card gender lean ('f'|'m'|'?')
  try{
    const hay=(String((card&&card.name)||'')+' '+String((card&&card.breed)||'')).toLowerCase();
    for(let i=0;i<_AK_CARD_F.length;i++){ if(hay.indexOf(_AK_CARD_F[i])>=0) return 'f'; }
    for(let i=0;i<_AK_CARD_M.length;i++){ if(hay.indexOf(_AK_CARD_M[i])>=0) return 'm'; }
  }catch(_e){}
  return '?';
}
function _akRebuildVoices(){         // AK-VOICEVAR: (re)build the en-* voice table + gender pools
  try{
    if(typeof window==='undefined' || !window.speechSynthesis || typeof window.speechSynthesis.getVoices!=='function') return;
    let list=[];
    try{ list=window.speechSynthesis.getVoices()||[]; }catch(_e){ list=[]; }
    const en=[];
    for(let i=0;i<list.length;i++){
      const v=list[i];
      if(String((v&&v.lang)||'').toLowerCase().indexOf('en')===0) en.push(v);
    }
    // deterministic, stable order so cardNumber-seeded picks never shuffle between calls
    en.sort(function(a,b){ const ka=String((a&&(a.voiceURI||a.name))||''), kb=String((b&&(b.voiceURI||b.name))||''); return ka<kb?-1:(ka>kb?1:0); });
    _akSpkVoices=en;
    _akSpkVoicesF=en.filter(function(v){ return _akVoiceGender(v)==='f'; });
    _akSpkVoicesM=en.filter(function(v){ return _akVoiceGender(v)==='m'; });
    _akSpkVoiceGen++;                // invalidate every cached per-card pick
  }catch(_e){}
}
function _akEnsureVoices(){          // AK-VOICEVAR: lazy bind voiceschanged + best-effort sync fill
  try{
    if(!akSpeechAvail()) return;
    if(!_akSpkVoicesBound){
      _akSpkVoicesBound=true;
      try{
        if(window.speechSynthesis.addEventListener){ window.speechSynthesis.addEventListener('voiceschanged', _akRebuildVoices); }
        else if('onvoiceschanged' in window.speechSynthesis){ window.speechSynthesis.onvoiceschanged=_akRebuildVoices; }
      }catch(_e){}
    }
    if(_akSpkVoices.length===0) _akRebuildVoices();   // often already populated by the time a card deploys
  }catch(_e){}
}
function akCardVoice(card){          // AK-VOICEVAR: deterministic per-card device voice (or null)
  try{
    if(!card || !akSpeechAvail()) return null;
    _akEnsureVoices();
    if(_akSpkVoices.length===0) return null;                     // fallback -> pitch/rate-only variation
    if(card._akVoiceObj && card._akVoiceGen===_akSpkVoiceGen) return card._akVoiceObj;  // stable cache
    const idstr=String(card.cardNumber!=null?card.cardNumber:(card.num!=null?card.num:(card.name||'?')));
    const seed=((parseInt(idstr.replace(/\D/g,''),10)||0) || hashStr(idstr)) >>> 0;  // cardNumber-seeded
    const g=_akCardGender(card);
    let pool=_akSpkVoices;
    if(g==='f' && _akSpkVoicesF.length) pool=_akSpkVoicesF;
    else if(g==='m' && _akSpkVoicesM.length) pool=_akSpkVoicesM;
    // $BCARDD: hard-force a stable, deep MALE device voice (his signature). Prefer
    // a known-deep label; else the first male voice. Never a female voice on him.
    if(akIsBcardd(card)){
      const mp=_akSpkVoicesM.length?_akSpkVoicesM:_akSpkVoices;
      const PREF=['daniel','google uk english male','microsoft david','alex','rishi','arthur','fred'];
      let deep=null;
      for(let pi=0; pi<PREF.length && !deep; pi++){ for(let vi=0; vi<mp.length; vi++){ if(String((mp[vi].name||'')).toLowerCase().indexOf(PREF[pi])>=0){ deep=mp[vi]; break; } } }
      const pickB = deep || mp[0] || null;
      if(pickB){ card._akVoiceObj=pickB; card._akVoiceGen=_akSpkVoiceGen; return pickB; }
    }
    const pick=pool[seed % pool.length] || _akSpkVoices[seed % _akSpkVoices.length] || null;
    card._akVoiceObj=pick; card._akVoiceGen=_akSpkVoiceGen;
    return pick;
  }catch(_e){ return null; }
}
// AK-SPEAK: is this the $BCARDD mascot (card #0001, the Dealer)? Gets a unique
// PREMIUM signature voice -- deep, measured, confident "house dealer" cadence --
// and is hard-forced MALE so a female device voice never lands on him.
function akIsBcardd(card){
  try{ if(!card) return false;
    if(card.cardNumber===1 || card.cardNumber==='0001' || card.num===1) return true;
    return /b[\s-]?cardd|bacardi/i.test(String(card.name||''));
  }catch(_e){ return false; }
}
function akSpeechCharacter(card){   // AK-SPEAK: pitch/rate from breed size + faction tint
  // $BCARDD signature: a deep, slow, swaggering boy voice -- the brand's voice.
  if(akIsBcardd(card)) return { pitch: 0.74, rate: 0.82, sig: true };
  const size=(card && BREED_SIZE[card.breed]!=null)?BREED_SIZE[card.breed]:2;
  const h=((card && (card.silhouetteSeed || hashStr(card.name||'?')))||0)>>>0;
  const jit=((h%89)/89-0.5)*0.12;                        // +-6% per-card voice fingerprint
  const tint=(card && FACTION_TIMBRE[card.faction])||FACTION_TIMBRE_DEF;
  return {
    pitch: clamp(1.45 - size*0.19 + tint.detune/1000 + jit, 0.6, 1.6),  // tiny ~1.45 .. giant ~0.69
    rate:  clamp(1.20 - size*0.0875 + jit*0.3, 0.8, 1.25)               // tiny ~1.2  .. giant ~0.85
  };
}
// AK-VOICE111: premium pre-rendered ElevenLabs clip, preferred over the free
// speechSynthesis. assets/voices/<cardNumber>.mp3; a missing/failed clip is
// remembered so it falls back cleanly to TTS. Browser-only (Audio); headless no-op.
var _akClipEl=null, _akClipMiss={};
function akVoiceClipURL(card){
  try{ if(!card) return null; var n=(card.cardNumber!=null?card.cardNumber:card.num); if(n==null) return null;
    return 'assets/voices/'+String(n)+'.mp3'; }catch(_e){ return null; }
}
function akPlayVoiceClip(card){
  try{
    if(typeof Audio==='undefined') return false;
    var url=akVoiceClipURL(card); if(!url || _akClipMiss[url]) return false;
    if(!_akClipEl) _akClipEl=new Audio();
    _akClipEl.onerror=function(){ _akClipMiss[url]=true; };   // mark missing -> TTS next time
    _akClipEl.src=url; _akClipEl.volume=0.9;
    var pr=_akClipEl.play();
    if(pr && pr.catch) pr.catch(function(){ _akClipMiss[url]=true; });
    return true;
  }catch(_e){ return false; }
}
function akStopClip(){               // AK-SPEAK: hard-stop the premium mp3 channel
  try{ if(_akClipEl){ _akClipEl.pause(); _akClipEl.currentTime=0; } }catch(_e){}
}
function akSpeak(text, card){       // AK-SPEAK: speak one line in the card's voice
  try{
    if(_akMuted || !_akVoiceOn || !text) return false;
    const now=(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
    if(now-_akSpeakLast<4000) return false;              // max 1 spoken line per ~4s
    _akSpeakLast=now;
    // never overlap: kill BOTH channels (TTS + the premium mp3) before a new line
    try{ if(akSpeechAvail()) window.speechSynthesis.cancel(); }catch(_e){}
    akStopClip();
    if(akPlayVoiceClip(card)) return true;               // AK-VOICE111: premium mp3 wins
    if(!akSpeechAvail()) return false;                   // no clip + no TTS -> silent
    const u=new window.SpeechSynthesisUtterance(String(text));
    const v=akSpeechCharacter(card);
    u.pitch=v.pitch; u.rate=v.rate;
    u.volume=0.55;                                       // modest -- sits under the SFX bed
    // AK-VOICEVAR: deterministic per-card device voice (gender-leaned where inferable);
    // breed-size pitch/rate above still layers on top. Null -> system default voice.
    try{ const vv=akCardVoice(card); if(vv){ u.voice=vv; if(vv.lang) u.lang=vv.lang; } }catch(_e){}
    window.speechSynthesis.speak(u);
    return true;
  }catch(_e){ return false; }
}
function akSpeakTagline(card){      // AK-SPEAK: lore tagline lookup -> speak
  try{
    if(!card) return false;
    if(typeof window==='undefined' || typeof window.AK_LORE_GET!=='function') return false;
    const L=window.AK_LORE_GET(card.cardNumber!=null?card.cardNumber:card.num);
    if(!L || !L.tagline) return false;
    const spoke=akSpeak(L.tagline, card);
    // AK-DOGVOICE 2026-06-15: a short bark UNDER the spoken line so it reads as a
    // DOG talking, not a person. $BCARDD gets a deeper, fatter signature bark.
    if(spoke){ try{ const v=cardVoice(card); if(v) cardBark(v, akIsBcardd(card)?0.8:1.0, akIsBcardd(card)?1.15:0.85); }catch(_e){} }
    return spoke;
  }catch(_e){ return false; }
}
function akSetVoiceOn(v){           // AK-SPEAK: VOICE chip toggle; turning OFF silences now
  _akVoiceOn=!!v;
  if(!_akVoiceOn && akSpeechAvail()){ try{ window.speechSynthesis.cancel(); }catch(_e){} }
}

// AK-AUDIO: tinted oscillator voice (detune + lowpass per faction), capped + mastered
function cardTone(f, dur, vol, fEnd, tint, oscType){
  const ac=getAC(); if(!ac || _akMuted || !akVoiceFree()) return;
  try{
    const o=ac.createOscillator(), g=ac.createGain();
    o.connect(g);
    let tail=g;
    try{
      if(tint && tint.filter && ac.createBiquadFilter){
        const fl=ac.createBiquadFilter(); fl.type='lowpass';
        fl.frequency.setValueAtTime(tint.filter, ac.currentTime);
        g.connect(fl); tail=fl;
      }
    }catch(e){ tail=g; }
    tail.connect(akMaster()||ac.destination);
    o.type = oscType || (tint&&tint.osc) || 'sawtooth';
    try{ if(tint && tint.detune && o.detune && o.detune.setValueAtTime) o.detune.setValueAtTime(tint.detune, ac.currentTime); }catch(e){}
    o.frequency.setValueAtTime(Math.max(20,f), ac.currentTime);
    if(fEnd) o.frequency.exponentialRampToValueAtTime(Math.max(20,fEnd), ac.currentTime+dur);
    g.gain.setValueAtTime(Math.min(0.5,(vol||0.18)*1.7), ac.currentTime);  // x1.7 pre-master keeps shipped loudness behind the 0.5 master
    g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime+dur);
    o.start(); o.stop(ac.currentTime+dur+0.03);
    akVoiceTake(o, dur);
  }catch(e){}
}

// AK-AUDIO: bark/vocal -- small dogs double-yip, giants get a chest layer
function cardBark(v, pitchMul, volMul){
  if(!v) return;
  const p=v.pitch*(pitchMul||1), d=v.vdur, vol=0.16*(volMul||1)*(0.85+v.fat*0.3);
  cardTone(p*1.35, d, vol, p*0.65, v.tint);
  if(v.size<=1){
    try{ if(typeof setTimeout!=='undefined') setTimeout(()=>cardTone(p*1.5, d*0.8, vol*0.8, p*0.75, v.tint), d*900); }catch(e){}
  } else if(v.size>=4){
    cardTone(p*0.5, d*1.5, vol*0.7, p*0.3, null, 'sine');
  }
}
// AK-AUDIO: rarity shimmer -- soft high sparkle, dropped under LOW_FX
function cardShimmer(v){
  if(!v || !v.shimmer || _akLowFx) return;
  cardTone(v.pitch*6, 0.22, v.shimmer, v.pitch*9,  null, 'triangle');
  cardTone(v.pitch*8, 0.30, v.shimmer*0.7, v.pitch*12, null, 'sine');
}
// AK-AUDIO: attack-hit family by weaponType, fattened by cost, tinted by faction
function cardWeapon(wt, v){
  const fm = 1.12 - v.fat*0.3;       // heavier card = deeper hit
  const dm = 0.85 + v.fat*0.45;      // ...and a longer tail
  const t  = v.tint;
  if(wt==='melee'){                                      // bite + impact thud
    cardTone(160*fm, 0.06*dm, 0.14, 60, t);
    cardTone( 70*fm, 0.12*dm, 0.20*(0.8+v.fat*0.5), 34, null, 'sine');
  } else if(wt==='bullet'){ cardTone(880*fm, 0.05*dm, 0.10, 240, t); }       // snap
  else if(wt==='spread'){                                // double snap fan
    cardTone(760*fm, 0.05*dm, 0.09, 220, t);
    try{ if(typeof setTimeout!=='undefined') setTimeout(()=>cardTone(700*fm,0.05*dm,0.08,200,t),35); }catch(e){}
  } else if(wt==='cannon'){                              // boom
    cardTone( 90*fm, 0.30*dm, 0.30, 28, null, 'sine');
    cardTone(300*fm, 0.08, 0.10, 80, t);
  } else if(wt==='beam'){  cardTone(520*fm, 0.16*dm, 0.10, 1400*fm, t); }    // synth whine
  else if(wt==='lance'){   cardTone(680*fm, 0.09*dm, 0.11, 220, t); }
  else { cardTone(520*fm, 0.10*dm, 0.10, 200, t); }
}
// AK-AUDIO: entry point for card-aware SFX. Global events (win/lose/crown/
// phase) stay on the plain sfx(). Falls back to sfx() with no card context.
function sfxCard(name, card){
  try{
    if(_akMuted) return;
    const v = cardVoice(card);
    if(!v){ sfx(name); return; }
    if(name==='deploy'){
      if(!playSample('deploy', 1.25 - v.size*0.12)) cardBark(v, 1, 1);   // card vocal
      cardShimmer(v);
    } else if(name==='death'){
      if(!playSample('death', 1.18 - v.size*0.10)) cardBark(v, 0.6, 0.8); // pitched-down farewell
    } else if(name.indexOf('atk_')===0){
      if(!playSample(name, (1.1 - v.fat*0.25)*(1.06 - v.size*0.04))) cardWeapon(name.slice(4), v);
    } else if(name==='ability'){
      if(!playSample('ability', 1.15 - v.size*0.08)) cardTone(v.pitch*2.2, 0.16, 0.13, v.pitch*3.6, v.tint, 'triangle');
      cardShimmer(v);
    } else sfx(name);
  }catch(e){}
}
// AK-AUDIO: knockback thump -- a big shove lands with weight
function sfxThump(push){
  try{ if(_akMuted) return; cardTone(64, 0.14, Math.min(0.3, 0.12+push*0.25), 30, null, 'sine'); }catch(e){}
}

// AK-HAPTIC: micro-vibration per hit, riding the existing AK-AUDIO call sites
// (sfxCard atk_* / sfxThump / towerhit / tower death) -- never new timing.
// Patterns by weaponType: melee thud, cannon boom, beam buzz, bullet tick,
// plus knockback thump and tower-destroyed rumble. Small and tasteful: a
// 70ms throttle keeps battle ticks from turning into a constant buzz; big
// moments (tower down) bypass it. Fully guarded: no navigator.vibrate
// (headless harness / desktop) = silent no-op. index.html owns the
// ak_haptics settings chip and mirrors it onto global.AK_HAPTICS (default ON).
const HAPTIC_PAT = {
  melee:[14],            // thud
  cannon:[34],           // boom
  beam:[8,26,8],         // buzz
  bullet:[5],            // tick
  lance:[9],             // jab
  spread:[6,16,6],       // double snap
  knock:[22],            // knockback thump
  tower_hit:[12],        // tower crack
  tower_down:[45,40,85], // tower-destroyed rumble
  gate_down:[60,45,110]  // king/Gate down -- the big one
};
let _hapLast = 0;
function haptic(kind, force){
  try{
    if(typeof navigator === 'undefined' || !navigator.vibrate) return;
    if(global.AK_HAPTICS === false) return;   // settings chip (default ON when unset)
    const pat = HAPTIC_PAT[kind];
    if(!pat) return;
    const now = Date.now();
    if(!force && now - _hapLast < 70) return;
    _hapLast = now;
    navigator.vibrate(pat);
  }catch(e){}
}

// AK-AUDIO: legacy tone() now routes through the master chain + voice cap
function tone(f,type,dur,vol,fEnd){ const ac=getAC(); if(!ac) return; try{ if(!akVoiceFree()) return; const o=ac.createOscillator(),g=ac.createGain(); o.connect(g);g.connect(akMaster()||ac.destination); o.type=type||'sine'; o.frequency.setValueAtTime(f,ac.currentTime); if(fEnd)o.frequency.exponentialRampToValueAtTime(Math.max(20,fEnd),ac.currentTime+dur); g.gain.setValueAtTime(Math.min(0.5,(vol||0.18)*1.7),ac.currentTime); g.gain.exponentialRampToValueAtTime(0.001,ac.currentTime+dur); o.start(); o.stop(ac.currentTime+dur+0.03); akVoiceTake(o,dur);}catch(e){} }
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
// AK-AUDIO: rate = per-card playbackRate (size/cost pitch identity on samples)
function playSample(name, rate){
  const ac=getAC(), b=SFX_BUF[name];
  if(!ac || !b || !akVoiceFree()) return false;
  try{ const s=ac.createBufferSource(); s.buffer=b;
    try{
      const r = clamp(rate||1, 0.5, 2);
      if(s.playbackRate && s.playbackRate.setValueAtTime) s.playbackRate.setValueAtTime(r, ac.currentTime);
      else if(s.playbackRate) s.playbackRate.value = r;
    }catch(e){}
    const g=ac.createGain();
    g.gain.value=1.1;   // x1.1 pre-master ~= the shipped 0.55 behind the 0.5 master
    s.connect(g); g.connect(akMaster()||ac.destination); s.start();
    akVoiceTake(s, (b.duration||0.5)/(rate||1));
    return true; }catch(e){ return false; }
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
  // AK-SHOW: transition stings + warning tick. Earned (3-crown) clears land the
  // MAJOR gold sting; clock-forced moves land the MINOR urgent one. Both open
  // with the bass drop (the BREAK beat). 'tick' is the 3-2-1 countdown click.
  else if(name==='sting_major'){ tone(70,'sine',0.5,0.30,36); [523,659,784].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.30,0.20,f*1.02),i*90)); }
  else if(name==='sting_minor'){ tone(70,'sine',0.5,0.30,30); [466,554,622].forEach((f,i)=>setTimeout(()=>tone(f,'sawtooth',0.26,0.14,f*0.97),i*90)); }
  else if(name==='tick') tone(940,'square',0.06,0.16,620);
  // AK-LOOT: tier-pitched magnet scoop -- scoop0 (Common/spark) .. scoop4
  // (Mythic). Short bright tick, pitch climbs with the tier so a rare scoop
  // READS over combat without ever competing with the stings.
  else if(name && String(name).slice(0,5)==='scoop'){
    const ti = Math.max(0, Math.min(4, parseInt(String(name).slice(5),10)||0));
    tone(760+ti*150,'triangle',0.07,0.10,1400+ti*220);
  }
  // AK-AUDIO: custom UI sound bites -- procedural (ZzFX-style), no asset, ships free + zero license.
  else if(name==='chest_open'){ tone(90,'square',0.12,0.24,46); [659,880,1175].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.22,0.17,f*1.02),i*70)); }   // wood crack -> gold burst
  // AK-JUICE 2026-07-17: the tiered chest ladder systems/juice.js drives. Rarity is AUDIBLE now,
  // a diamond crate no longer sounds like a wood one. Dedicated Mythic rung + bonus_1..4 climb.
  else if(name==='chest_land'){ tone(64,'sine',0.20,0.32,44); }
  else if(name==='chest_tick'){ tone(900,'square',0.03,0.05,900); }
  else if(name==='chest_unlock'){ tone(150,'sawtooth',0.16,0.20,90); setTimeout(()=>tone(320,'square',0.06,0.10,260),60); }
  else if(name==='chest_common'){ tone(300,'sine',0.30,0.13,210); }
  else if(name==='chest_rare'){ [523,659].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.24,0.17,f),i*90)); }
  else if(name==='chest_epic'){ [523,659,784].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.32,0.19,f),i*80)); }
  else if(name==='chest_legendary'){ tone(65,'sine',0.6,0.30,58); [523,659,784,1046].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.40,0.21,f),i*95)); }
  else if(name==='chest_mythic'){ tone(55,'sine',0.95,0.34,50); [659,784,988,1318,1568].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.5,0.23,f),i*115)); }
  else if(name && String(name).slice(0,6)==='bonus_'){ const bn=Math.max(1,Math.min(4,parseInt(String(name).slice(6),10)||1)); tone(392+bn*98,'triangle',0.18,0.18,392+bn*98); }
  else if(name==='reward'){ [784,1047,1319].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.18,0.14,f*1.03),i*60)); }                                          // ascending shimmer
  else if(name==='tap'){ tone(420,'square',0.04,0.10,300); }                                                                                                       // crisp UI click
  // AK-AUDIO: combat + mechanic identifiers (synth placeholders; drop assets/sfx/<name>.mp3 to upgrade to bespoke).
  else if(name==='hit_impact'){ tone(150,'sine',0.06,0.08,68); }                                                                                                   // a unit takes a hit -- short low thud, voice-capped (combat texture)
  else if(name==='kw_burn'){ tone(380,'sawtooth',0.18,0.10,180); }                                                                                                 // ignite -- a hissing crackle
  else if(name==='kw_deadly'){ tone(220,'square',0.10,0.16,40); setTimeout(()=>tone(900,'triangle',0.08,0.10,1300),40); }                                          // lethal bite -- dark hit + sting
  else if(name==='afterlife'){ [523,415,330].forEach((f,i)=>setTimeout(()=>tone(f,'sine',0.22,0.12,f*0.96),i*70)); }                                               // spectral descend
  else if(name==='evo_up'){ [523,659,784,1047].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.22,0.16,f*1.02),i*80)); }                                         // tier-up fanfare (ascending)
  else if(name==='boot_reveal'){ tone(70,'sine',0.5,0.22,40); [659,988].forEach((f,i)=>setTimeout(()=>tone(f,'triangle',0.4,0.16,f*1.02),i*120)); }               // loading gate -> lobby whoosh+chime
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
  NAMED_SYNERGY,          // AK-SYNERGY: named combo table (Deck Lab reference list + HUD chips read labels/hints)
  STARTER_DECK_NAMES,
  // ---- convoy + storm (renderer reads these for assets, codex, HUD) ----
  SECTIONS, SECTION_HOOKS, STORM_CATALOG, PHASE_LABELS, TIER_SPEED,   // AK-STORY: district hook lines (L8.1)
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
  // AK-HANDLER: tap-fire the equipped commander's special (HUD + board-tap route here)
  fireSpecial, makeHandlerState,
  get HANDLERS(){ return (typeof window!=='undefined' && window.AK_HANDLERS) || []; },
  get game(){ return game; },
  // AK-LOOT: the SHAKEDOWN surface -- renderer draws game.loot.tokens, the
  // stash chip reads game.loot.stash, grantMatchRewards folds game.loot.banked.
  get loot(){ return game ? game.loot : null; },
  lootTable,
  get effects(){ return effects; },
  get projectiles(){ return projectiles; },
  get particles(){ return particles; },
  resumeAudio(){ const ac=getAC(); if(ac && ac.state==='suspended') ac.resume(); loadAllSfx(); },
  sfx,   // AK-AUDIO: expose the synth/sample dispatcher so the lobby + shop can fire UI sound bites (chest_open/reward/tap)
  // AK-AUDIO: mute (persisted by index.html to ak_muted) + LOW_FX shimmer gate
  setMuted(m){ akSetMuted(m); },
  isMuted(){ return _akMuted; },
  setAudioLow(b){ _akLowFx = !!b; },
  // AK-SHEET: attribute-sheet math -- the card detail renders REAL numbers
  // with the engine's OWN math (level mult + the snapshotPerks tune clamps),
  // never a second formula. index.html falls back to local mirrors headless.
  SHEET: {
    LV_FX: CARD_LV_FX, LV_MAX: CARD_LV_MAX,
    levelMult(lv){ return akLevelMult(lv); },
    clampBoost(m){ return clamp((typeof m==='number'&&isFinite(m))?m:1, 1.0, 1.25); },   // hp/dmg/agi/aspd tune mult
    clampGuard(m){ return clamp((typeof m==='number'&&isFinite(m))?m:1, 0.80, 1.0); }    // def/spdef damage-TAKEN mult
  },
  // AK-SHOW: named-SFX entry for the renderer's showpiece beats (stings, ticks)
  // and the AK-XPBAR level-up moment. Rides the existing sfx() synth/sample
  // layer -- mute + voice-cap gates apply inside, headless = clean no-op.
  playSfx(name){ try{ sfx(name); }catch(_e){} },
  // AK-SPEAK: spoken-tagline channel (VOICE chip persisted by index.html to ak_voice)
  setVoiceOn(v){ akSetVoiceOn(v); },
  isVoiceOn(){ return _akVoiceOn; },
  speakTagline(c){ return akSpeakTagline(c); },
  // AK-VOICEVAR: warm + bind the device voice list early (index.html boot calls this
  // so 'voiceschanged' is hooked before the first card deploys). Returns the en-* voice
  // count (0 headless / before load). Safe to call repeatedly; no-op without speechSynthesis.
  warmVoices(){ try{ _akEnsureVoices(); }catch(_e){} return _akSpkVoices.length; },
  voiceCount(){ return _akSpkVoices.length; },
  // AK-RULES: range-supremacy audit hook (L1B) -- one-shot band-per-card table;
  // probes assert exactly TWO cards reach >= 6.0 (Laser Beagle, Rail Terrier).
  rangeBandAudit,
  // AK-CLASS: class-layer census audit -- counts per combat class over the
  // troop index + the structure-archetype roll call. Probes assert these
  // against the TAXONOMY 1.2 per-card table (the authoritative roster).
  classAudit(){
    const counts={}, arch={}; let total=0;
    for(const k in CARDS){
      const c=CARDS[k]; if(!c || c.type==='spell') continue;
      total++;
      const cls=c.combatClass||'UNKNOWN';
      counts[cls]=(counts[cls]||0)+1;
      if(c.structArch){ (arch[c.structArch]=arch[c.structArch]||[]).push(c.cardNumber); }
    }
    for(const a in arch) arch[a].sort();
    return { total:total, counts:counts, arch:arch };
  },
  // AK-VIBES: analyser tap + raw context for the arena edge glow (index.html)
  getAnalyser(){ return akAnalyser(); },
  getAudioCtx(){ return getAC(); },
  setDifficulty(n){ DIFFICULTY = Math.max(0, Math.min(9, n|0)); return DIFFICULTY; }
};

})(typeof window!=='undefined'?window:globalThis);
