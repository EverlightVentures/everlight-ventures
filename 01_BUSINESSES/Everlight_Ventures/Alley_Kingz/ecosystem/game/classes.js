/* AK-CLASS: Alley Kingz class layer sidecar (Wave 7 lane L2, TAXONOMY_DESIGN 1-2).
   CLASS is a NEW axis on top of ROLE: the fantasy + buff hook that drives the
   class-keyed synergy combos, badge text, archetype detection and the
   structure family split. Sidecar map keyed by cardNumber -- canon.js is
   GENERATED and stays untouched (no stat edits here, classification only).
   Pattern mirrors cards_lore.js: plain JS, headless-safe, window-guarded.
   NO em-dashes anywhere in this file (hook law); use -- instead. */
(function (global) {

  // ---- ability FAMILY -> combat class (TAXONOMY_DESIGN 1.2, verbatim).
  // Clones share their base card's kit, so class is assigned per ability
  // family and inherited by every variant.
  var CLASS_BY_FAMILY = {
    // BONEGUARD CREW
    'Crownbreaker':'BRUISER', 'Armor Pulse':'BRUISER', 'Haymaker':'BRUISER',
    'Overclock Rage':'BRUISER', 'Bodywall':'BRUISER', 'Brawler':'BRUISER',
    'Shock Push':'BRUISER', 'Fortify':'SUPPORT', 'Grav Pull':'BRUISER',
    'Shield Bark':'SUPPORT', 'Bitechain':'BRUISER', 'Stonehide':'BRUISER',
    // ZOOMIE SYNDICATE
    'Shadow Fang':'ASSASSIN', 'Pierce Rush':'MARKSMAN', 'Twin Strike':'ASSASSIN',
    'Dash Loop':'ASSASSIN', 'Blink Bite':'ASSASSIN', 'Sidecut':'ASSASSIN',
    'Spark Pups':'SUMMONER', 'Signal Scramble':'CASTER', 'Slipstream':'ASSASSIN',
    'Burst Bite':'ASSASSIN', 'Tag Boost':'SUPPORT', 'Tracer Round':'MARKSMAN',
    // LEASHBREAK TACTIX
    'Leashbreak':'CASTER', 'Hack Jam':'CASTER', 'Blackout':'CASTER',
    'Barrier Ring':'SUPPORT', 'Heal Beacon':'SUPPORT', 'Frost Bark':'CASTER',
    'Shatter':'CASTER', 'Tag Shot':'MARKSMAN', 'Phase':'ASSASSIN',
    'Echo Howl':'CASTER', 'Ping':'CASTER', 'Soothe':'SUPPORT',
    // K9 CIRCUITRY
    'Royal Hunt':'ASSASSIN', 'Drone Swarm':'SUMMONER', 'Overclock':'STRUCTURE',
    'Overheat':'STRUCTURE', 'Grid Lock':'STRUCTURE', 'Arc Shot':'CASTER',
    'Beacon':'SUPPORT', 'Tunnel Drones':'STRUCTURE', 'Battery':'STRUCTURE',
    'Rail Shot':'MARKSMAN', 'Mini Pup':'STRUCTURE'
  };

  // ---- structure family -> one of the FIVE archetypes (TAXONOMY_DESIGN 1.3).
  // ramper   = damage climbs per consecutive hit on the SAME target, resets on retarget
  // turret   = flat dps + a timed burst-fire window (off the ramp code path)
  // lockdown = snare-beam HOLD on one unit + the 35% slow field on the rest
  // nest     = planted den, repeating token spawn, 4 alive tokens per nest
  // pylon    = planted battery, +15% attack speed to allied structures in 3.5 tiles
  var ARCH_BY_FAMILY = {
    'Overheat':'ramper', 'Overclock':'turret', 'Grid Lock':'lockdown',
    'Tunnel Drones':'nest', 'Mini Pup':'nest', 'Battery':'pylon'
  };
  // The reclass trio becomes PLANTED STATIC (move_speed 0 in the engine map).
  // Their +10% hp compensation lives in data/_build_canon.py and ships with
  // the operator-gated canon regen (contract C1) -- never hand-tuned here.
  var STATIC_RECLASS = { '0045':1, '0046':1, '0048':1 };

  // ---- CC attack subtypes (TAXONOMY_DESIGN 2) keyed by canon abilityType.
  // lock/slow/knock/silence ride existing engine timers; blind/reveal are
  // DENIAL (listed under Control on the sheet, excluded from CC payoffs).
  var CC_BY_ABILITY_TYPE = {
    stun:'lock', root:'lock',
    slow:'slow',
    knockback:'knock',
    silence:'silence', disable_tower:'silence',
    blind:'denial', reveal:'denial'
  };

  // ---- build the per-cardNumber map from the inlined canon (single derivation,
  // never hand-copied stats). Guarded: no canon loaded = empty map, callers
  // fall back to the engine's interim CLASS_BY_FAMILY constant.
  var BY_CARD = {};
  try {
    var cards = (global && global.CANON_CARDS) || (typeof CANON_CARDS !== 'undefined' ? CANON_CARDS : null);
    if (cards && cards.forEach) {
      cards.forEach(function (c) {
        if (!c || !c.cardNumber) return;
        var fam = (c.ability && c.ability.name) || '';
        var cls = CLASS_BY_FAMILY[fam] || (c.role === 'Structure' ? 'STRUCTURE' : null);
        BY_CARD[c.cardNumber] = {
          cls: cls,
          arch: (cls === 'STRUCTURE') ? (ARCH_BY_FAMILY[fam] || 'turret') : null,
          reclassStatic: !!STATIC_RECLASS[c.cardNumber],
          cc: CC_BY_ABILITY_TYPE[c.abilityType] || null,
          family: fam
        };
      });
    }
  } catch (_e) { BY_CARD = {}; }

  var API = {
    byCard: BY_CARD,
    CLASS_BY_FAMILY: CLASS_BY_FAMILY,
    ARCH_BY_FAMILY: ARCH_BY_FAMILY,
    CC_BY_ABILITY_TYPE: CC_BY_ABILITY_TYPE,
    STATIC_RECLASS: STATIC_RECLASS,
    // census over the derived map (probe + Deck Lab read this)
    census: function () {
      var out = { total: 0 };
      for (var k in BY_CARD) { var c = BY_CARD[k].cls || 'UNKNOWN'; out[c] = (out[c] || 0) + 1; out.total++; }
      return out;
    }
  };

  if (global) {
    global.AK_CLASSES = API;
    global.AK_CLASS_GET = function (num) { return BY_CARD[num] || null; };
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
