/* ==========================================================================
 * keywords_data.js -- Alley Kingz KEYWORD data layer (the Gods Unchained borrow).
 *
 * Pure DATA -- vanilla JS, no imports, browser + node-harness safe. Mirrors the
 * IIFE/window-export shape of handlers_data.js. NOTHING here touches combat;
 * this is the P1 "legibility" layer from GU_KEYWORD_SYSTEM_DESIGN.md -- cards
 * "read their role" from keyword chips, exactly like a real TCG.
 *
 * EXPORTS (read by shop.js card-inspect + index.html hand corner, later by the
 * engine in P2/P3):
 *   window.AK_KEYWORDS         -- registry array {id,label,glyph,color,desc,faction}
 *   window.AK_KEYWORDS_BY_ID   -- id -> keyword object
 *   window.AK_CARD_KEYWORDS    -- card (by cardNumber AND name) -> [keywordIds]
 *
 * PALETTE: Chop Shop gold/faction tokens (shop.css :root) --
 *   gold #D4AF37 | rust #c0612e (Boneguard) | cyan #2ee6ff (Zoomie)
 *   teal #1fd6c4 (Leashbreak) | hazard #ff8a1f (K9) | green #5fff8f
 *   shadow #9B8CFF (Shadow handler) | mythic-red #ff4d6d | epic #b06bff
 *   rare-blue #6fb6ff
 *
 * FACTION KITS (identity = mechanics, the second GU borrow):
 *   Boneguard  = frontline / protected      (the wall; St. Bernards regen)
 *   Zoomie     = blitz (+ hidden basenji)   (speed; Malinois twin_strike)
 *   Leashbreak = burn / twin_strike (+rare deadly)  (punishers; medics regen)
 *   K9         = ward                       (spell-proof tech; spawners afterlife)
 *   cross-faction = regen (medics) + afterlife (spawners)
 *
 * Each card carries 0-2 keywords (don't over-assign). The map is INLINED (not
 * derived from CANON_CARDS at load) so it resolves with zero load-order coupling
 * and the node harness can validate it standalone.
 * ======================================================================== */
(function (root) {
  'use strict';

  /* ---- KEYWORD REGISTRY ------------------------------------------------- */
  // engineFlag names the P2/P3 Unit field the chip wires to (see the build
  // plan); it is documentation here -- this file stays pure data.
  var KEYWORDS = [
    { id: 'frontline',   label: 'Frontline',   glyph: '🧱', color: '#c0612e', faction: 'boneguard',
      engineFlag: 'frontline',
      desc: 'Enemies in the lane must lock onto this dog first -- the wall.' },
    { id: 'hidden',      label: 'Hidden',      glyph: '🫥', color: '#9B8CFF', faction: 'zoomie',
      engineFlag: 'stealthT',
      desc: 'Spawns stealthed -- untargetable until its first attack reveals it.' },
    { id: 'blitz',       label: 'Blitz',       glyph: '⚡', color: '#2ee6ff', faction: 'zoomie',
      engineFlag: 'atkCD',
      desc: 'No deploy wind-up -- swings the instant it hits the field.' },
    { id: 'ward',        label: 'Ward',        glyph: '🔮', color: '#6fb6ff', faction: 'k9',
      engineFlag: 'ward',
      desc: 'Negates the first enemy spell that would hit it, then breaks.' },
    { id: 'protected',   label: 'Protected',   glyph: '🛡', color: '#D4AF37', faction: 'boneguard',
      engineFlag: 'protect',
      desc: 'Absorbs the first instance of damage in full, then breaks.' },
    { id: 'regen',       label: 'Regen',       glyph: '💚', color: '#5fff8f', faction: 'cross',
      engineFlag: 'regenPct',
      desc: 'Heals a slice of its max HP every second -- medic dogs.' },
    { id: 'burn',        label: 'Burn',        glyph: '🔥', color: '#ff5a2c', faction: 'leashbreak',
      engineFlag: 'burnT',
      desc: 'Its hits set the target ablaze -- damage over time.' },
    { id: 'twin_strike', label: 'Twin Strike', glyph: '⚔', color: '#1fd6c4', faction: 'leashbreak',
      engineFlag: 'twinStrike',
      desc: 'Lands two hits on every swing -- double the punish.' },
    { id: 'deadly',      label: 'Deadly',      glyph: '☠', color: '#ff4d6d', faction: 'leashbreak',
      engineFlag: 'deadly',
      desc: 'Any damage it deals is lethal -- one bite ends it.' },
    { id: 'afterlife',   label: 'Afterlife',   glyph: '👻', color: '#b06bff', faction: 'cross',
      engineFlag: 'afterlife',
      desc: 'Leaves a token or effect behind the moment it dies.' }
  ];

  var BY_ID = {};
  for (var i = 0; i < KEYWORDS.length; i++) BY_ID[KEYWORDS[i].id] = KEYWORDS[i];

  /* ---- CARD -> KEYWORD ASSIGNMENTS -------------------------------------
   * RAW rows: [cardNumber, name, [keywordIds]]. Assigned by FACTION + role +
   * breed/ability off the canon roster (106 dogs). Boneguard strikers are
   * intentionally bare -- their kits (stun/buff/ramp) sit outside this set,
   * and 0-keyword cards are valid (don't over-assign).
   * ---------------------------------------------------------------------- */
  var RAW = [
    // BONEGUARD CREW -- the wall (frontline/protected; St. Bernards regen)
    ['0001', '$BCARDD', ['frontline', 'protected']],
    ['0002', 'Stonejaw', ['frontline', 'protected']],
    ['0004', 'Iron Rottweiler', ['frontline']],
    ['0005', 'Granite Saint', ['frontline', 'regen']],
    ['0007', 'Alloy Akita', ['frontline']],
    ['0008', 'Warden Newfie', ['protected']],
    ['0009', 'Rust Cane Corso', ['frontline']],
    ['0010', 'Tank Pug', ['protected']],
    ['0012', 'Brick Bullmastiff', ['frontline', 'protected']],
    ['0051', 'Tombstone', ['frontline']],
    ['0052', 'Razorgums', ['frontline']],
    ['0053', 'Anvil', ['frontline', 'regen']],
    ['0054', 'Hatchet', ['frontline', 'regen']],
    ['0057', 'Warhorse', ['frontline']],
    ['0058', 'Lugnut', ['frontline']],
    ['0059', 'Ironhide', ['protected']],
    ['0060', 'Snaggle', ['protected']],
    ['0061', 'Slab', ['frontline']],
    ['0062', 'Brassknuck', ['frontline']],

    // ZOOMIE SYNDICATE -- speed (blitz; basenji/evasion hidden; Malinois twin_strike)
    ['0013', 'Jagged', ['hidden', 'deadly']],
    ['0014', 'Razor Vizsla', ['blitz']],
    ['0015', 'Aero Malinois', ['twin_strike', 'blitz']],
    ['0016', 'Pixel Greyhound', ['blitz']],
    ['0017', 'Circuit Shiba', ['blitz']],
    ['0018', 'Flash Saluki', ['blitz']],
    ['0019', 'Bolt Corgi', ['afterlife']],
    ['0020', 'Glitch Basenji', ['hidden']],
    ['0021', 'Neon Whippet', ['blitz', 'hidden']],
    ['0022', 'Turbo Jack', ['blitz']],
    ['0023', 'Drift Sheltie', ['blitz']],
    ['0024', 'Byte Beagle', ['blitz']],
    ['0063', 'Roadblock', ['blitz']],
    ['0064', 'Nitro', ['blitz']],
    ['0065', 'Bullbar', ['blitz']],
    ['0066', 'Switchblade', ['blitz']],
    ['0067', 'Rollcage', ['blitz']],
    ['0068', 'Ricochet', ['blitz']],
    ['0069', 'Crashcage', ['blitz']],
    ['0070', 'Hotwire', ['blitz']],
    ['0071', 'Bumper', ['afterlife']],
    ['0072', 'Backfire', ['afterlife']],
    ['0073', 'Gridiron', ['hidden']],
    ['0074', 'Skidmark', ['hidden']],
    ['0075', 'Deadweight', ['twin_strike']],
    ['0076', 'Flatline', ['twin_strike', 'blitz']],

    // LEASHBREAK TACTIX -- punishers (burn; pointers twin_strike; medics regen; ghosts hidden)
    ['0025', 'Rosco', ['burn', 'deadly']],
    ['0026', 'Synth Collie', ['burn']],
    ['0027', 'Noir Setter', ['burn']],
    ['0028', 'Pulse Border Collie', ['burn']],
    ['0029', 'Holo Husky', ['regen']],
    ['0030', 'Chill Samoyed', ['burn']],
    ['0031', 'Prism Poodle', ['burn']],
    ['0032', 'Signal Pointer', ['twin_strike']],
    ['0033', 'Ghost Spaniel', ['hidden']],
    ['0034', 'Echo Dalmatian', ['burn']],
    ['0035', 'Static Sheba Inu', ['burn']],
    ['0036', 'Vibe Shih Tzu', ['regen']],
    ['0077', 'Firewall', ['burn']],
    ['0078', 'Glitchfork', ['burn']],
    ['0079', 'Deadbolt', ['regen']],
    ['0080', 'Static', ['regen']],
    ['0081', 'Bunkerlink', ['burn']],
    ['0082', 'Shortcircuit', ['burn']],
    ['0083', 'Faraday', ['burn']],
    ['0084', 'Hexer', ['burn']],
    ['0085', 'Sandbag', ['burn']],
    ['0086', 'Whitenoise', ['burn']],
    ['0087', 'Blacksite', ['twin_strike']],
    ['0088', 'Carrier', ['twin_strike']],
    ['0089', 'Hardline', ['hidden']],
    ['0090', 'Spike', ['hidden']],
    ['0091', 'Bulwark', ['burn']],
    ['0092', 'Brownout', ['burn']],

    // K9 CIRCUITRY -- spell-proof tech (ward; spawners afterlife; foxhound hidden)
    ['0037', 'Crown Foxhound', ['ward', 'hidden']],
    ['0038', 'Circuit Retriever', ['ward', 'afterlife']],
    ['0039', 'Nova Shepherd', ['ward']],
    ['0040', 'Laser Beagle', ['ward']],
    ['0041', 'Volt Corgi', ['ward', 'afterlife']],
    ['0042', 'Grid Schnauzer', ['ward']],
    ['0043', 'Chrome Airedale', ['ward']],
    ['0044', 'Beacon Basset', ['ward']],
    ['0045', 'Neon Dachshund', ['ward', 'afterlife']],
    ['0046', 'Flux Pomeranian', ['ward']],
    ['0047', 'Rail Terrier', ['ward']],
    ['0048', 'Pixel Pug', ['ward', 'afterlife']],
    ['0093', 'Bunker', ['ward']],
    ['0094', 'Buckshot', ['ward']],
    ['0095', 'Howitzer', ['ward', 'afterlife']],
    ['0096', 'Tripwire', ['ward', 'afterlife']],
    ['0097', 'Flakwall', ['ward']],
    ['0098', 'Deadeye', ['ward']],
    ['0099', 'Casemate', ['ward', 'afterlife']],
    ['0100', 'Shrapnel', ['ward', 'afterlife']],
    ['0101', 'Pillbox', ['ward']],
    ['0102', 'Hairtrigger', ['ward']],
    ['0103', 'Stronghold', ['ward']],
    ['0104', 'Snubnose', ['ward']],
    ['0105', 'Emplacement', ['ward']],
    ['0106', 'Salvo', ['ward']]
  ];

  // Build the lookup keyed by BOTH cardNumber and name so callers can resolve
  // however they hold a card (shop.js inspects by c.num/c.id OR c.name; the
  // engine holds card.cardNumber). Arrays are shared by reference -- read-only.
  var CARD_KEYWORDS = {};
  for (var j = 0; j < RAW.length; j++) {
    var num = RAW[j][0], name = RAW[j][1], ids = RAW[j][2];
    CARD_KEYWORDS[num] = ids;
    CARD_KEYWORDS[name] = ids;
  }

  root.AK_KEYWORDS = KEYWORDS;
  root.AK_KEYWORDS_BY_ID = BY_ID;
  root.AK_CARD_KEYWORDS = CARD_KEYWORDS;

  // Node/CommonJS convenience (harness + tests); harmless in the browser.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AK_KEYWORDS: KEYWORDS, AK_KEYWORDS_BY_ID: BY_ID, AK_CARD_KEYWORDS: CARD_KEYWORDS };
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
