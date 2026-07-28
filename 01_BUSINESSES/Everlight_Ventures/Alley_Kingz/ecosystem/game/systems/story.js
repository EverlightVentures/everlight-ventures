/* game/systems/story.js -- AK_SYSTEMS module: "story" (THE CROWN BLOODLINE).
   ============================================================================
   STORY MODE SPINE -- a client-deterministic, ENGINE-FREE state machine that
   reads the saga off the profile + the OTHER systems already in the build, and
   delivers objectives the way the dead do it: a dream from the OLD PACK (our
   StarClan of fallen legend dogs) is louder than any quest popup.

   DESIGN (AK_STORY_MODE_DESIGN.md "THE CROWN BLOODLINE", LOCKED section 7):
   - HYBRID generations. GEN I (lone stray -> KING, the full 7-stage CROWN CLIMB)
     is the complete, ships-on-its-own core. Passing the torch to a successor pup
     (GEN II/III bloodline) is an OPTIONAL path that UNLOCKS after you take the
     crown. Gen II/III ship here as extensible DATA stubs; the torch-pass UNLOCK
     + passTorch() + persistence are REAL.
   - GRITTY GANGLAND tone. Streets, turf, betrayal, hard edges -- GTA-of-dogs.
     The rescue-stray open still hooks the dog-lover, but loyalty is earned and
     the crown is taken, never given. Copy is street-tough.
   - HYBRID clan naming. Keep the built crew names (Zoomie Syndicate / Leashbreak
     Tactix / Boneguard Crew / K9 Circuitry) but call them "clans" in the prose.

   HOW EACH STAGE GATES OFF REAL STATE (GEN I, the CROWN CLIMB):
     0 STRAY AWAKENING   -> always (game started). Advance when the FIRST DELIVERY
                            lands: a turned-in job (p.missionLog), first trophies,
                            or a first capture.
     1 PICK YOUR CLAN    -> a clan is chosen + you start running its turf. We
                            auto-derive the clan from AKKarma district standings;
                            advance when that clan's karma hits New Face.
     2 PROVE YOURSELF    -> advance when your clan's karma tier reaches TRUSTED
                            (AKKarma, idx >= 3).
     3 CREW WARS         -> advance when a turf raid or a guard/defense lands
                            (p.raid.lastRaid / defenseNight / revenge).
     4 SEASONAL SUPREMACY-> advance on season engagement (p.season marks / claims /
                            check-in streak -- AKSeasons feeds these).
     5 CHALLENGE THE KING-> advance when you hit the throne rank (p.trophies at
                            King-of-the-Block) OR the orchestrator force-crowns you
                            on the season-final boss win (advance(true)).
     6 CROWNED           -> reign. UNLOCKS the optional torch-pass.

   NON-LINEAR (CROWN BLOODLINE loop gates, AK_ROADMAP_V2 sec.1): every rung ALSO
   clears from ANY avenue -- climbing the RANK ladder (trophies crossing a division:
   Stray -> Pup -> Runner -> Warrior -> Enforcer -> Right Paw -> King of the Block),
   holding TURF (districts controlled via AKKarma), or banking CLAN karma. CREW_WARS
   is HARD-gated behind holding >=3 districts and RE-LOCKS if turf drops below 3
   (until the crown is taken). packCap() exposes the pack size each rank unlocks
   (Stray=3, Pup=4, Runner=5, Warrior=7, Enforcer=9, Right Paw=12, King=15).

   CONTRACT COMPLIANCE (mirrors karma.js / seasons.js / mission_active.js):
   - Self-registers into window.AK_SYSTEMS; edits NO shared file. The orchestrator
     adds <script src="systems/story.js"> and wires the HUD beacon off the exported
     window.AKStory. engine.js is FROZEN and untouched.
   - ALL player state via window.AK_ECON.mutateProfile behind falsy-default fields
     this module lazy-creates ON WRITE (economy.js ensureShape is FROZEN, so a
     never-played profile stays byte-identical until the story first advances):
         p.storyStage (0..6)   p.storyGen (0 = Gen I)   p.storyClan (clan id)   p.storyFlags {}
   - NO server, NO engine edits. Reads are best-effort + try/catch wrapped; any
     absent sibling system (AKKarma / AKSeasons / raid) simply leaves a gate unmet
     (safe, never throws, headless byte-identical).
   - SOFT-CURRENCY ONLY: this spine pays NOTHING. It only narrates + gates. No gold,
     no gems, no $BCARDD / ALK -- the existing loops already pay out.
   - Public API on window.AKStory, EXPORTED BEFORE the registry bail so the file is
     harmless + headless-safe on pages without AK_SYSTEMS (node harness no-ops).
   - 60fps: onTick re-checks on a ~1.5s throttle, ONE mutateProfile max per check;
     zero per-frame work, no DOM, no roamers.
   - Voice: gritty gold cyberpunk dog-gang street culture; crews named, called clans.
   ============================================================================ */
(function (global) {
  'use strict';

  /* ---- the 4 clans (crew names kept; called clans in prose -- LOCKED #3) --- */
  // Mirrors AKKarma.FACTIONS keys so the auto-derived clan lines up with the
  // district-karma layer. Carries a static crew/clan/soul so display works even
  // when AKKarma is not loaded (headless / battler page).
  var CLANS = {
    unbound:    { key: 'unbound',    crew: 'Zoomie Syndicate',  clan: 'Zoomie',     soul: 'excitable, ride-or-die speed' },
    crowned:    { key: 'crowned',    crew: 'K9 Circuitry',      clan: 'K9',         soul: 'reactive, dominant tech-hounds' },
    rusted:     { key: 'rusted',     crew: 'Boneguard Crew',    clan: 'Boneguard',  soul: 'calm, immovable grit' },
    hologhosts: { key: 'hologhosts', crew: 'Leashbreak Tactix', clan: 'Leashbreak', soul: 'aloof, ghost ambushers' }
  };

  /* ======================================================================== *
   * THE GENERATIONS. Gen I is the canonical CROWN CLIMB (7 stages). Gen II/III
   * are extensible DATA STUBS (torch-pass unlock is real; their beats are
   * placeholder narrative the bloodline path grows into). Each stage:
   *   id        -- stable key
   *   title     -- gritty street-tough header
   *   objective -- the next move (the HUD beacon line)
   *   vision    -- a dream from the OLD PACK (dead legends) that DELIVERS the
   *                objective with menace + mentorship (this is HOW we hand quests)
   * ======================================================================== */
  var GEN_I = [
    { id: 'STRAY_AWAKENING',
      title: 'STRAY AWAKENING',
      objective: "Take the Fixer's first job. Run the delivery and put your name on the block.",
      vision: "The Old Pack circles you in the dark, eyes like dead streetlights. \"You came up alone, pup. No collar, no crew, no name. The Fixer's got work on the wire -- run it. Every king on these streets started as a stray nobody fed. Now MOVE.\"" },
    { id: 'PICK_CLAN',
      title: 'PICK YOUR CLAN',
      objective: "Run a clan's turf until they claim you. Zoomie, Boneguard, Leashbreak, or K9 -- pick a side and bleed for it.",
      vision: "A fallen king drags a chain across the concrete, link by link. \"A lone dog dies in winter, pup. Find your pack. One of those clans is already your blood -- you just ain't earned the colors yet. Go work their turf til they call you family.\"" },
    { id: 'PROVE_YOURSELF',
      title: 'PROVE YOURSELF',
      objective: "Climb your clan's karma to Trusted. Make the block say your name without flinching.",
      vision: "The Old Pack bares teeth in the fog. \"Colors don't make you, pup. Work does. Climb til they Trust you, til the old heads nod when you pass. Respect ain't handed out on this block. You take it, bite by bite.\"" },
    { id: 'CREW_WARS',
      title: 'CREW WARS',
      objective: "Hit a rival's turf or guard your own. Win a crew war and hold the ground.",
      vision: "Scarred ghosts of dead warriors pace the rooftops. \"Peace is for pets, pup. Word came down the wire -- the Dog That Eats Names is already licking his chops at your blocks. Raid. Guard. Win the war. Bury the ones who come for yours before he swallows your name whole.\"" },
    { id: 'SEASONAL_SUPREMACY',
      title: 'SEASONAL SUPREMACY',
      objective: "Run the whole season. Push your clan's districts to the top of the board.",
      vision: "The fallen king's eyes burn gold through the smoke. \"One war don't crown nobody. Rule the SEASON. Stack the marks, hold the districts -- but hear me: the Mongrel King has eaten every season but his own. Make the whole city flinch when your name drops, and make HIM remember it. An era belongs to whoever survives it.\"" },
    { id: 'CHALLENGE_THE_KING',
      title: 'CHALLENGE THE KING',
      objective: "The season's almost up. Face the reigning King in the tower final and rip the crown off his head.",
      vision: "Every dead legend lines the alley, dead silent. The old king steps forward, half his muzzle gone. \"This is where I fell, pup -- the Mongrel King, the Dog That Eats Names, took my crown and my name in the same breath. He's up that tower now and he won't kneel. Climb. Beat him in the final. Take back what he stole from all of us. The Old Pack made room for one more crown -- make it yours.\"" },
    { id: 'CROWNED',
      title: 'CROWNED -- KING OF THE BLOCK',
      objective: "Reign. Hold the block, feed your clan, and when you're ready, pick an heir and pass the torch.",
      vision: "The Old Pack bows low for the first time. \"You did it. You put the Dog That Eats Names in the dirt and pulled the crown off his skull. You're the King now -- the one the strays will dream about. But crowns get heavy and these streets got long memories. Hold it. And when your time comes, choose an heir and let the bloodline ride.\"" }
  ];

  // --- GEN II stub: "THE BLOODLINE" (extensible; advance() drives it for now) --
  var GEN_II = [
    { id: 'HEIR_RISING',
      title: 'HEIR RISING',
      objective: "Your heir takes the streets. Prove the bloodline didn't go soft.",
      vision: "The Old Pack -- and your own ghost among them now -- watch the pup you chose. \"Blood means nothing til it bleeds, heir. Show the block the crown was no fluke.\"" },
    { id: 'DEFEND_THE_THRONE',
      title: 'DEFEND THE THRONE',
      objective: "The rivals you spared are circling. Defend the throne your blood built.",
      vision: "Old enemies stir in the dark with new teeth. \"Mercy made you debts, heir. They're calling them in. Hold what your sire took.\"" },
    { id: 'BLOODLINE_CROWNED',
      title: 'BLOODLINE CROWNED',
      objective: "Hold the dynasty. The streets remember two kings now.",
      vision: "Two crowns hang in the smoke. \"A king is a story. A bloodline is a legend. Keep it burning, heir.\"" }
  ];

  // --- GEN III stub: "THE LEGEND WARS" (extensible) --------------------------
  var GEN_III = [
    { id: 'EMBERS_OF_WAR',
      title: 'EMBERS OF WAR',
      objective: "The clans your bloodline shaped collide. Pick where the city burns.",
      vision: "The whole Old Pack rises at once. \"Every choice your line ever made comes due tonight. The city's a powder keg. Light it on your terms.\"" },
    { id: 'CITY_AFLAME',
      title: 'CITY AFLAME',
      objective: "Win the era-defining city war. Who stands with you was decided generations ago.",
      vision: "Fallen kings march beside you. \"This is the war they'll carve in the concrete. March, and don't look at who falls.\"" },
    { id: 'LEGEND_ETERNAL',
      title: 'LEGEND ETERNAL',
      objective: "Outlast the fire. Become the legend the next strays dream about.",
      vision: "The Old Pack opens its circle for you. \"You don't rule the streets anymore, pup. You ARE the streets. Take your place.\"" }
  ];

  var GENS = [
    { gen: 0, name: "THE STRAY'S RISE", stages: GEN_I },
    { gen: 1, name: 'THE BLOODLINE',    stages: GEN_II },
    { gen: 2, name: 'THE LEGEND WARS',  stages: GEN_III }
  ];

  /* ======================================================================== *
   * CINEMA LAYER (Tarantino, AK_AUTEUR_AUDIT.md sec.1): cold-open flash-forward
   * + full-screen titled chapter cards. PURE DATA -- index.html owns the render.
   *  - Narrator portrait = THE OLD PACK (our StarClan); shown on every card + the
   *    dream-vision. Index does a graceful onerror fallback to a glyph circle.
   *  - Nemesis portrait = THE MONGREL KING, "the Dog That Eats Names" (King's
   *    named-antagonist steal): woven through the mid/late visions + epigraphs and
   *    FLAGGED onto the CHALLENGE_THE_KING card so the throne fight is personal.
   *  - Backdrops are REUSED existing hub/district art (assets/hub/*.png). We
   *    GENERATE NOTHING -- each card just re-lights a place the player already
   *    knows, dimmed, so the title lands like a film chapter title.
   * ======================================================================== */
  var STORY_ART = {
    narrator: 'assets/story/narrator_oldpack.png',   // the Old Pack (EXISTS)
    nemesis:  'assets/story/nemesis_mongrel.png'     // the Dog That Eats Names (EXISTS)
  };
  var ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];
  function roman(i) { return ROMAN[i | 0] || String((i | 0) + 1); }

  // Per-stage card metadata, keyed by STAGE ID so it survives across generations.
  // backdrop -> an EXISTING reused background; epigraph -> one Old Pack line
  // (the dream-vision distilled to a chapter-card kicker); nemesis -> show the
  // Mongrel King portrait on this card. Falls back to the stage objective if a
  // stage has no entry (Gen II/III stubs all carry one anyway).
  var CARD_META = {
    // --- GEN I (THE CROWN CLIMB) ---
    STRAY_AWAKENING:    { backdrop: 'assets/hub/street.png',          epigraph: "Every king on these streets started as a stray nobody fed." },
    PICK_CLAN:          { backdrop: 'assets/hub/clan.png',            epigraph: "A lone dog dies in winter. Find your pack or feed the cold." },
    PROVE_YOURSELF:     { backdrop: 'assets/hub/downtown_bg.png',     epigraph: "Respect ain't handed out on this block. You take it, bite by bite." },
    CREW_WARS:          { backdrop: 'assets/hub/the_docks_bg.png',    epigraph: "Peace is for pets -- and the Dog That Eats Names is already counting yours." },
    SEASONAL_SUPREMACY: { backdrop: 'assets/hub/neon_heights_bg.png', epigraph: "The Mongrel King has buried every season but his own. Make him remember yours." },
    CHALLENGE_THE_KING: { backdrop: 'assets/hub/town_hall.png',       epigraph: "He eats names for a living. Climb the tower and make him choke on yours.", nemesis: true, collar: true },
    CROWNED:            { backdrop: 'assets/hub/trophy.png',          epigraph: "You're the King now -- the one the strays will dream about.", collar: true },
    // --- GEN II (THE BLOODLINE) ---
    HEIR_RISING:        { backdrop: 'assets/hub/clan.png',            epigraph: "Blood means nothing til it bleeds, heir." },
    DEFEND_THE_THRONE:  { backdrop: 'assets/hub/town_hall.png',       epigraph: "Mercy made you debts. Tonight they come to collect." },
    BLOODLINE_CROWNED:  { backdrop: 'assets/hub/trophy.png',          epigraph: "A king is a story. A bloodline is a legend." },
    // --- GEN III (THE LEGEND WARS) ---
    EMBERS_OF_WAR:      { backdrop: 'assets/hub/downtown_bg.png',     epigraph: "Every choice your line ever made comes due tonight." },
    CITY_AFLAME:        { backdrop: 'assets/hub/neon_heights_bg.png', epigraph: "This is the war they'll carve into the concrete." },
    LEGEND_ETERNAL:     { backdrop: 'assets/hub/trophy.png',          epigraph: "You don't rule the streets anymore. You ARE the streets." }
  };

  /* the rank threshold that crowns you (reuses economy.js rankDivision ladder:
     5000 trophies == "King of the Block"). The orchestrator may also force-crown
     on the season-final boss win via advance(true). */
  var THRONE_TROPHIES = 5000;

  /* ======================================================================== *
   * THE COLLAR IS THE MONSTER (del Toro steal, AK_ROADMAP_V2 sec.1). The apex
   * antagonist was NEVER the Mongrel King -- it is the HUMAN SYSTEM: the pound,
   * the catchers, the collar, the wagon that drags strays off the block at dawn.
   * The Mongrel King "the Dog That Eats Names" only ever SERVED the collar -- he
   * did its biting on a chain he called a crown. Revealed NEAR THE RANK CEILING
   * (Right Paw, or once you reach CHALLENGE_THE_KING) by the OLD PACK: the seven-
   * rung climb was the catchers' own ladder all along and the crown was the bait.
   * PURE narrative data + reads -- surfaces via stage().collar + collarReveal();
   * never gates the climb, never pays out, writes nothing on its own. */
  var COLLAR = {
    id: 'THE_COLLAR',
    name: 'THE COLLAR',
    // the Old Pack's last lesson, delivered near the throne (gritty gangland).
    reveal: "The Old Pack stops circling. For the first time their dead eyes drift PAST you -- up to the floodlights burning over the pound fence. \"Listen close, cause no stray lives long enough to hear this part. The Dog That Eats Names? He was never king of nothing. He wore a collar too -- the catchers' collar. The POUND runs this whole city. The leash, the wire, the wagon that hauls strays off the block at first light -- THAT is the thing that ate every king before you. The Mongrel King just did its biting, fat and proud on a chain he called a crown. Seven rungs you climbed, pup, and men built every one of 'em. The crown was the bait. The block was the cage. Now you finally see the real teeth. So choose: rip the collar off this whole city, or wear it pretty like he did and call it a throne.\""
  };
  var COLLAR_REVEAL_RANK = 5;     // Right Paw -- the rung before the throne
  var CHALLENGE_KING_IDX = 5;     // GEN_I idx of CHALLENGE_THE_KING (the ceiling lead-in)

  /* ---- SCAR / MEMORY LEDGER (auteur steal: dogs carry scars + a record of HOW
   * you won). A capped, append-only log on p.storyFlags.ledger that raid.js +
   * encounters.js feed via window.AKStory.logDeed(text) on a WIN. The Old Pack
   * recites the freshest scars back into the dream-visions (stage().scars). Falsy
   * -default + lazy-created ON WRITE, so a never-played profile stays byte-
   * identical (no ledger key until the first deed is logged). */
  var LEDGER_CAP   = 24;          // keep the last N deeds (cheap-Android memory cap)
  var SCAR_SURFACE = 3;           // how many recent scars the vision recounts

  /* ---- module state (ctx cached at init so window.AKStory works ctx-less) -- */
  var S = { ctx: null, _acc: 0 };

  /* ---- small utils -------------------------------------------------------- */
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function ctxOf() { return S.ctx || (global && global.AK_CTX) || null; }
  function profile(ctx) { try { return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function akKarma() { try { return global.AKKarma || null; } catch (_) { return null; } }
  function raidOf(p) { return (p && p.raid && typeof p.raid === 'object') ? p.raid : {}; }
  function seasonOf(p) { return (p && p.season && typeof p.season === 'object') ? p.season : {}; }
  function flagsOf(p) { return (p && p.storyFlags && typeof p.storyFlags === 'object') ? p.storyFlags : {}; }

  /* ---- CLAN derivation off the district-karma layer (AKKarma) ------------- *
   * Your clan is whichever clan's turf you've earned the most karma in -- you
   * earn into it by playing, no extra UI needed. Returns {key, points} | null.
   * ======================================================================== */
  function dominantClan(p) {
    var K = akKarma();
    if (!K || !K.DISTRICTS) return null;
    var karmaMap = (p && p.karma && typeof p.karma === 'object') ? p.karma : {};
    var byFac = {};                                  // facKey -> MAX district karma for that clan
    for (var zid in K.DISTRICTS) {
      if (!K.DISTRICTS.hasOwnProperty(zid)) continue;
      var fac = K.DISTRICTS[zid];
      if (!fac || fac === 'neutral' || !CLANS[fac]) continue;
      var pts = karmaMap[zid] | 0;
      if (!(fac in byFac) || pts > byFac[fac]) byFac[fac] = pts;
    }
    var best = null, bestPts = -1;
    for (var f in byFac) { if (byFac.hasOwnProperty(f) && byFac[f] > bestPts) { bestPts = byFac[f]; best = f; } }
    if (best == null || bestPts <= 0) return null;
    return { key: best, points: bestPts };
  }
  // Tier idx (0..6) of the player's clan, via AKKarma.tierByPoints. -1 if unknown.
  function clanTierIdx(p) {
    var K = akKarma(), dc = dominantClan(p);
    if (!K || !dc || !K.tierByPoints) return -1;
    try { var t = K.tierByPoints(dc.points); return t ? (t.idx | 0) : -1; } catch (_) { return -1; }
  }

  /* ======================================================================== *
   * NON-LINEAR AVENUES -- the CROWN BLOODLINE advances from ANY direction.
   * Beyond the per-stage objective gate, each rung ALSO clears when the player
   * climbs the RANK ladder (trophies crossing a division), holds enough TURF
   * (districts controlled via AKKarma karma), or banks enough CLAN karma. PURE
   * reads of EXISTING fields (p.trophies, p.karma) -- no new profile fields,
   * falsy-default, zero-state byte-identical (this module still writes nothing
   * until the climb actually advances).
   * ======================================================================== */

  /* RANK ladder -- OUR canon clan ranks; thresholds MIRROR economy.js
     rankDivision() [0,200,500,1000,1800,3000,5000]. cap = the pack size this rank
     unlocks (Stray=3 ... King of the Block=15). */
  var RANKS = [
    { idx: 0, name: 'Stray',             min: 0,    cap: 3  },
    { idx: 1, name: 'Pup',               min: 200,  cap: 4  },
    { idx: 2, name: 'Runner',            min: 500,  cap: 5  },
    { idx: 3, name: 'Warrior',           min: 1000, cap: 7  },
    { idx: 4, name: 'Enforcer',          min: 1800, cap: 9  },
    { idx: 5, name: 'Right Paw',         min: 3000, cap: 12 },
    { idx: 6, name: 'King of the Block', min: 5000, cap: 15 }
  ];
  // rank division idx (0..6) off trophies. null profile -> Stray (0).
  function rankIdx(p) {
    var t = p ? (p.trophies | 0) : 0, r = 0;
    for (var i = 0; i < RANKS.length; i++) { if (t >= RANKS[i].min) r = i; }
    return r;
  }

  /* TURF control -- how many districts the player HOLDS. A district is held once
     your AKKarma standing there reaches "Trusted" (the block backs you). Reads the
     same p.karma map dominantClan() uses; only counts REAL districts when the canon
     (AKKarma.DISTRICTS) is loaded. Falsy-default -> 0 (zero-state holds nothing). */
  var CONTROL_TIER_IDX = 3;     // AKKarma "Trusted" idx
  var CONTROL_MIN_PTS  = 175;   // fallback when AKKarma absent: mirrors karma.js TIERS Trusted.min
  function districtHeld(pts) {
    var K = akKarma();
    if (K && K.tierByPoints) { try { var t = K.tierByPoints(pts | 0); return !!t && (t.idx | 0) >= CONTROL_TIER_IDX; } catch (_) {} }
    return (pts | 0) >= CONTROL_MIN_PTS;
  }
  function turfHeld(p) {
    if (!p || !p.karma || typeof p.karma !== 'object') return 0;
    var K = akKarma(), n = 0;
    for (var zid in p.karma) {
      if (!p.karma.hasOwnProperty(zid)) continue;
      if (K && K.DISTRICTS && !K.DISTRICTS.hasOwnProperty(zid)) continue;   // canon districts only when loaded
      if (districtHeld(p.karma[zid])) n++;
    }
    return n;
  }

  /* THE CREW_WARS TURF GATE -- the CREW_WARS chapter (stage idx 3) is HARD-gated
     behind holding >=3 districts and RE-LOCKS if turf drops below 3 (until the crown
     is taken). GATES[2] is the rung that enters CREW_WARS. */
  var CREW_WARS_IDX = 3;
  var CREW_WARS_GATE = 2;
  var TURF_FOR_CREW_WARS = 3;

  /* per-gate non-linear avenues: GATES[i] (the rung INTO stage i+1) ALSO clears if
     rankIdx >= rank, turfHeld >= turf, or clanTierIdx >= clan. -1 = avenue n/a.
     GATES[2] (into CREW_WARS) leaves turf to the HARD gate above, not an OR. */
  var AVENUES = [
    { rank: 1, turf: 1,  clan: 1 },   // -> PICK_CLAN
    { rank: 2, turf: 2,  clan: 2 },   // -> PROVE_YOURSELF
    { rank: 3, turf: -1, clan: 3 },   // -> CREW_WARS (turf is the hard gate, below)
    { rank: 4, turf: 4,  clan: 4 },   // -> SEASONAL_SUPREMACY
    { rank: 5, turf: 5,  clan: 5 },   // -> CHALLENGE_THE_KING
    { rank: 6, turf: 6,  clan: 6 }    // -> CROWNED
  ];

  /* the max pack size your RANK unlocks (Stray=3 ... King of the Block=15). */
  function packCap() {
    var ctx = ctxOf(), p = profile(ctx);
    return RANKS[rankIdx(p)].cap;
  }

  /* ======================================================================== *
   * THE GEN I GATES -- each returns true when the matching stage's objective is
   * DONE (advancing the climb). computeIdx() counts the CONTIGUOUS run of met
   * gates from the bottom, so you can never reach CROWNED without each rung.
   * ======================================================================== */
  function gFirstDelivery(p) {
    if (Array.isArray(p.missionLog) && p.missionLog.length >= 1) return true;   // a turned-in faction job == a delivery
    if ((p.trophies | 0) > 0) return true;                                       // first ranked result counts
    if (p.captures && typeof p.captures === 'object') { for (var k in p.captures) { if (p.captures.hasOwnProperty(k)) return true; } }
    if (flagsOf(p).delivered) return true;                                       // orchestrator override hook
    return false;
  }
  function gClanEarned(p) { return dominantClan(p) != null && clanTierIdx(p) >= 1; }   // chosen + New Face on its turf
  function gTrusted(p)    { return clanTierIdx(p) >= 3; }                              // AKKarma Trusted tier
  function gWarDone(p) {
    var r = raidOf(p);
    if ((r.lastRaid | 0) > 0) return true;                                       // launched a turf raid
    if (r.defenseNight || (r.lastDefenseAt | 0) > 0) return true;                // claimed a guard / defense night
    if (Array.isArray(r.revenge) && r.revenge.length > 0) return true;           // got hit + has a revenge marker
    if (flagsOf(p).warDone) return true;                                         // orchestrator override hook
    return false;
  }
  function gSeasonProg(p) {
    var s = seasonOf(p);
    if ((s.marks | 0) >= 120) return true;                                       // stacked a season's marks
    if (Array.isArray(s.claimed) && s.claimed.length >= 1) return true;          // unlocked a seasonal cosmetic
    if (s.checkIn && (s.checkIn.streak | 0) >= 3) return true;                   // ran the season daily
    if (flagsOf(p).seasonDone) return true;                                      // orchestrator override hook
    return false;
  }
  function gThrone(p) {
    if ((p.trophies | 0) >= THRONE_TROPHIES) return true;                        // King of the Block on the rank ladder
    if (flagsOf(p).crowned) return true;                                         // season-final boss win force-crown
    return false;
  }
  var GATES = [gFirstDelivery, gClanEarned, gTrusted, gWarDone, gSeasonProg, gThrone];

  // one gate's verdict: the stage objective OR any non-linear avenue (RANK / TURF /
  // CLAN karma). The CREW_WARS rung carries a HARD turf requirement that no avenue
  // can bypass (and that makes it re-lock when turf is lost).
  function gateMet(i, p) {
    var ok = false; try { ok = !!GATES[i](p); } catch (_) { ok = false; }
    if (!ok) {
      var av = AVENUES[i];
      if (av) {
        if (av.rank >= 0 && rankIdx(p) >= av.rank) ok = true;
        else if (av.turf >= 0 && turfHeld(p) >= av.turf) ok = true;
        else if (av.clan >= 0 && clanTierIdx(p) >= av.clan) ok = true;
      }
    }
    if (i === CREW_WARS_GATE && turfHeld(p) < TURF_FOR_CREW_WARS) ok = false;   // hard CREW_WARS turf gate
    return ok;
  }

  // contiguous count of satisfied gates from the bottom (Gen I only) -> idx 0..6
  function computeIdx(p) {
    var idx = 0;
    for (var i = 0; i < GATES.length; i++) {
      if (gateMet(i, p)) idx = i + 1; else break;
    }
    return clamp(idx, 0, GEN_I.length - 1);
  }

  // EFFECTIVE stage after the CREW_WARS turf re-lock: slip below 3 districts before
  // the crown is taken and CREW_WARS (plus any rung above it) re-locks back to the
  // PROVE_YOURSELF rung until you reclaim turf. The persisted high-water (storyStage)
  // is NEVER regressed -- this is a reversible PRESENTATION clamp, so reclaiming turf
  // restores progress instantly -- and a taken crown is permanent (no turf dip ever
  // un-thrones a King of the Block).
  function effectiveIdx(p, rawIdx, g) {
    if ((g | 0) !== 0) return rawIdx;                                   // Gen I climb only
    if (rawIdx >= GEN_I.length - 1) return rawIdx;                      // CROWNED is terminal -- never re-locked
    if (flagsOf(p).crowned) return rawIdx;                              // crown taken (force-crown) -- permanent
    if (rawIdx >= CREW_WARS_IDX && turfHeld(p) < TURF_FOR_CREW_WARS) return CREW_WARS_IDX - 1;
    return rawIdx;
  }

  /* ======================================================================== *
   * CORE API
   * ======================================================================== */
  // Re-evaluate the climb from profile + sibling systems, PERSIST any forward
  // movement (never regress), and return the current idx. ONE mutateProfile max.
  // Gen II/III are DATA STUBS: they do not auto-advance off the (inherited)
  // profile state -- they move only via advance(). Zero-state stays byte-identical
  // (no write at idx 0 with no clan to lock).
  function check() {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return curIdx();
    var p = profile(ctx); if (!p) return 0;
    var gen = p.storyGen | 0, persisted = p.storyStage | 0;
    if (gen !== 0) return clamp(persisted, 0, ((GENS[gen] && GENS[gen].stages.length) || 1) - 1);

    var computed = computeIdx(p);
    var nextIdx = Math.max(persisted, computed);
    var dc = dominantClan(p);
    var needClan = (nextIdx >= 1 && !p.storyClan && dc);
    var needCrown = (nextIdx >= 6 && !flagsOf(p).crowned);
    if (nextIdx === persisted && !needClan && !needCrown) return effectiveIdx(p, persisted, gen);   // nothing to write

    ctx.econ.mutateProfile(function (pp) {
      if ((pp.storyStage | 0) < nextIdx) pp.storyStage = nextIdx;               // lazy-create ON WRITE, monotonic
      if (nextIdx >= 1 && !pp.storyClan && dc) pp.storyClan = dc.key;           // lock the clan you earned into
      if (nextIdx >= 6) {                                                       // reaching CROWNED unlocks the torch
        if (!pp.storyFlags || typeof pp.storyFlags !== 'object') pp.storyFlags = {};
        pp.storyFlags.crowned = true;
      }
    });
    return effectiveIdx(p, nextIdx, gen);                                       // turf re-lock is presentational
  }

  // cheap, ctx-less current idx read (no write) -- safe on headless.
  function curIdx() { var ctx = ctxOf(); var p = profile(ctx); return p ? (p.storyStage | 0) : 0; }

  // the current stage object, enriched with idx + gen (does NOT mutate).
  function stage() {
    var ctx = ctxOf(), p = profile(ctx);
    var gen = p ? (p.storyGen | 0) : 0;
    var stages = (GENS[gen] && GENS[gen].stages) || GEN_I;
    var idx = clamp(p ? (p.storyStage | 0) : 0, 0, stages.length - 1);
    idx = effectiveIdx(p, idx, gen);                                            // apply the CREW_WARS turf re-lock
    var st = stages[idx] || stages[0];
    var meta = CARD_META[st.id] || {};
    // narrator (the Old Pack) rides every vision so the dream has a face; nemesis
    // portrait is non-null on the stages where the Mongrel King is present. collar
    // = the Old Pack's apex reveal once you brush the rank ceiling (additive --
    // null until then); scars = the freshest deeds the dream recites (the ledger
    // of HOW you won, surfaced right inside the vision).
    return { idx: idx, id: st.id, title: st.title, objective: st.objective, vision: st.vision, gen: gen,
             narrator: STORY_ART.narrator, nemesis: meta.nemesis ? STORY_ART.nemesis : null,
             collar: collarRevealed(p) ? COLLAR.reveal : null,
             scars: recentDeedsFrom(p, SCAR_SURFACE) };
  }

  function gen() { var ctx = ctxOf(), p = profile(ctx); return p ? (p.storyGen | 0) : 0; }

  // Advance one stage. force=true skips the gate (orchestrator force-crown on the
  // season-final boss win). Without force, Gen I only advances if the next gate is
  // actually met; Gen II/III stubs advance freely (no auto-gates yet).
  function advance(force) {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return curIdx();
    var res = 0;
    ctx.econ.mutateProfile(function (p) {
      var g = p.storyGen | 0;
      var stages = (GENS[g] && GENS[g].stages) || GEN_I;
      var idx = p.storyStage | 0;
      if (idx >= stages.length - 1) { res = idx; return; }                      // already terminal
      if (!force && g === 0 && computeIdx(p) <= idx) { res = idx; return; }      // gate not met yet
      p.storyStage = idx + 1; res = p.storyStage;
      if (p.storyStage >= stages.length - 1) {                                   // reached this gen's CROWNED
        if (!p.storyFlags || typeof p.storyFlags !== 'object') p.storyFlags = {};
        p.storyFlags.crowned = true;
      }
    });
    return res;
  }

  function banner() { return stage().objective; }     // HUD beacon: the next move
  function vision() { return stage().vision; }         // the dream from the Old Pack

  // chosen clan info (display-safe even without AKKarma) | null.
  function clan() {
    var ctx = ctxOf(), p = profile(ctx);
    var key = p && p.storyClan;
    return (key && CLANS[key]) ? CLANS[key] : null;
  }

  /* ======================================================================== *
   * THE OPTIONAL TORCH-PASS (unlocks post-CROWNED) -- begins the next gen.
   * Picks a successor dog from the OWNED roster (the bloodline), bumps storyGen,
   * RESETS the climb for the heir while KEEPING territory (karma) + bloodline
   * (owned) + clan. Real + persisted; Gen II/III beats are the data stubs above.
   * ======================================================================== */
  function torchUnlocked() {
    var ctx = ctxOf(), p = profile(ctx); if (!p) return false;
    var g = p.storyGen | 0;
    var stages = (GENS[g] && GENS[g].stages) || GEN_I;
    return ((p.storyStage | 0) >= stages.length - 1) || !!flagsOf(p).crowned;
  }
  // pick the highest-rarity owned dog as the heir (bloodline pride), else the first.
  function pickHeir(ctx, owned) {
    if (!owned || !owned.length) return null;
    var cards = {}; try { cards = (ctx && ctx.cards && ctx.cards()) || {}; } catch (_) {}
    var order = { Mythic: 5, Legendary: 4, Epic: 3, Rare: 2, Common: 1 };
    var best = null, bestR = -1;
    for (var i = 0; i < owned.length; i++) {
      var nm = owned[i], c = cards[nm], r = c ? (order[c.rarity] || 0) : 0;
      if (r > bestR) { bestR = r; best = nm; }
    }
    return best || owned[0];
  }
  function passTorch(successorName) {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return { ok: false, error: 'NO_CTX' };
    if (!torchUnlocked()) return { ok: false, error: 'NOT_CROWNED' };
    var p = profile(ctx);
    var owned = (p && Array.isArray(p.owned)) ? p.owned : [];
    var heir = (successorName && owned.indexOf(successorName) >= 0) ? successorName : pickHeir(ctx, owned);
    if (!heir) return { ok: false, error: 'NO_HEIR' };                          // need at least one dog to crown
    var out = { ok: false };
    ctx.econ.mutateProfile(function (pp) {
      if (!pp.storyFlags || typeof pp.storyFlags !== 'object') pp.storyFlags = {};
      var prevGen = pp.storyGen | 0;
      if (!Array.isArray(pp.storyFlags.bloodline)) pp.storyFlags.bloodline = [];
      pp.storyFlags.bloodline.push({ gen: prevGen, heir: heir, clan: pp.storyClan || null, trophies: pp.trophies | 0, at: Date.now() });
      pp.storyGen = prevGen + 1;                                                // begin the next generation
      pp.storyStage = 0;                                                        // reset the climb for the heir
      pp.storyFlags.heir = heir;                                               // you now play AS the heir
      pp.storyFlags.crowned = false;                                           // the new gen must earn its own crown
      pp.storyFlags.genStart = { trophies: pp.trophies | 0, at: Date.now() };   // baseline for future delta-gating
      // territory (p.karma), bloodline (p.owned), and clan (p.storyClan) are KEPT.
      out = { ok: true, gen: pp.storyGen, heir: heir, clan: pp.storyClan || null };
    });
    return out;
  }

  /* HUD / orchestrator helper: explicitly lock a clan (e.g. a player pick UI).
     Falls back to auto-derivation in check() if never called. */
  function setClan(clanId) {
    var ctx = ctxOf(); if (!ctx || !ctx.econ || !CLANS[clanId]) return { ok: false, error: 'BAD_CLAN' };
    ctx.econ.mutateProfile(function (p) { p.storyClan = clanId; });
    return { ok: true, clan: CLANS[clanId] };
  }

  /* ======================================================================== *
   * CINEMA LAYER API (pure data for index.html's full-screen render). No DOM,
   * no engine, no per-frame work. Reused art only -- generates nothing.
   * ======================================================================== */
  // The full-screen chapter card for a stage idx in (optional) gen. Resolves the
  // CURRENT gen by default so it works through the torch-pass. Returns:
  //   { num, title, epigraph, backdrop, narrator, nemesis, gen, idx, id }
  // narrator is ALWAYS the Old Pack; nemesis is the Mongrel King path | null.
  function chapterCard(idx, genArg) {
    var ctx = ctxOf(), p = profile(ctx);
    var g = (genArg == null) ? (p ? (p.storyGen | 0) : 0) : (genArg | 0);
    var stages = (GENS[g] && GENS[g].stages) || GEN_I;
    var i = clamp(idx | 0, 0, stages.length - 1);
    var st = stages[i] || stages[0];
    var meta = CARD_META[st.id] || {};
    return {
      num: roman(i),
      title: st.title,
      epigraph: meta.epigraph || st.objective,
      backdrop: meta.backdrop || 'assets/hub/street.png',
      narrator: STORY_ART.narrator,
      nemesis: meta.nemesis ? STORY_ART.nemesis : null,
      collar: !!meta.collar,        // ceiling cards carry the collar motif (the real monster)
      gen: g, idx: i, id: st.id
    };
  }

  // The cold-open flash-forward (Tarantino): open on CHAPTER VII -- CROWNED, the
  // player crowned + bleeding, ~3.5s, then SMASH-CUT back to CHAPTER I -- STRAY
  // AWAKENING. Pure sequence data; index.html plays it ONCE on first load and
  // calls markColdOpenSeen(). The Mongrel King looms on the crowned frame -- the
  // throne you bleed for was HIS.
  function coldOpen() {
    var crowned = chapterCard(GEN_I.length - 1, 0);   // VII
    var stray   = chapterCard(0, 0);                  // I
    return {
      smashCut: true,
      frames: [
        { num: crowned.num, title: 'CROWNED', bleeding: true, hold: 3500, flash: true,
          epigraph: "This is how it ends -- crowned, bleeding, the Dog That Eats Names dead at your paws. Now watch how a stray got here.",
          backdrop: crowned.backdrop, narrator: STORY_ART.narrator, nemesis: STORY_ART.nemesis },
        { num: stray.num, title: stray.title, bleeding: false, hold: 3500, flash: false,
          epigraph: stray.epigraph, backdrop: stray.backdrop, narrator: STORY_ART.narrator, nemesis: null }
      ]
    };
  }

  // has the player already seen the cold-open? (falsy-default, zero-state safe)
  function coldOpenSeen() {
    var ctx = ctxOf(), p = profile(ctx);
    return !!(p && flagsOf(p).coldOpenSeen);
  }
  // mark it seen (one mutateProfile, lazy-creates storyFlags on write).
  function markColdOpenSeen() {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return false;
    ctx.econ.mutateProfile(function (p) {
      if (!p.storyFlags || typeof p.storyFlags !== 'object') p.storyFlags = {};
      p.storyFlags.coldOpenSeen = true;
    });
    return true;
  }

  /* ======================================================================== *
   * THE COLLAR IS THE MONSTER -- reveal layer (additive; never gates the climb).
   * Surfaces near the rank ceiling: Right Paw on the ladder, OR once the climb
   * reaches CHALLENGE_THE_KING. Sticky once played (orchestrator calls
   * markCollarSeen()). Pure reads -- writes nothing unless markCollarSeen runs.
   * ======================================================================== */
  function collarRevealed(p) {
    if (!p) return false;
    if (flagsOf(p).collarSeen) return true;                  // already played -> stays revealed
    if ((p.storyStage | 0) >= CHALLENGE_KING_IDX) return true;
    return rankIdx(p) >= COLLAR_REVEAL_RANK;                  // Right Paw, brushing the ceiling
  }
  // the Old Pack's collar reveal (apex = the human system) | null until the ceiling.
  function collarReveal() {
    var ctx = ctxOf(), p = profile(ctx);
    if (!collarRevealed(p)) return null;
    return { id: COLLAR.id, title: COLLAR.name, vision: COLLAR.reveal,
             narrator: STORY_ART.narrator, nemesis: STORY_ART.nemesis };
  }
  // persist that the reveal has played (one mutateProfile, lazy-creates storyFlags).
  function markCollarSeen() {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return false;
    ctx.econ.mutateProfile(function (p) {
      if (!p.storyFlags || typeof p.storyFlags !== 'object') p.storyFlags = {};
      p.storyFlags.collarSeen = true;
    });
    return true;
  }

  /* ======================================================================== *
   * SCAR / MEMORY LEDGER -- how you won. logDeed(text) is the hook raid.js +
   * encounters.js call on a WIN; ledger()/recentDeeds()/scars() read it back; the
   * dream-visions recite the freshest scars (stage().scars). Append-only + capped.
   * ======================================================================== */
  function ledgerArr(p) {
    return (p && p.storyFlags && Array.isArray(p.storyFlags.ledger)) ? p.storyFlags.ledger : [];
  }
  // record one deed (how a fight was won). Coerces + trims + caps; falsy text no-ops.
  function logDeed(text) {
    var ctx = ctxOf(); if (!ctx || !ctx.econ) return false;
    var t = String(text == null ? '' : text).replace(/\s+/g, ' ').trim().slice(0, 160);
    if (!t) return false;                                    // nothing to record (zero-state safe)
    ctx.econ.mutateProfile(function (p) {
      if (!p.storyFlags || typeof p.storyFlags !== 'object') p.storyFlags = {};
      var L = Array.isArray(p.storyFlags.ledger) ? p.storyFlags.ledger : (p.storyFlags.ledger = []);
      L.push({ text: t, at: Date.now(), stage: p.storyStage | 0, gen: p.storyGen | 0 });
      if (L.length > LEDGER_CAP) L.splice(0, L.length - LEDGER_CAP);   // keep the last N (cap)
    });
    return true;
  }
  // a COPY of the full ledger (newest last) -- never hands out the live array.
  function ledger() { var ctx = ctxOf(), p = profile(ctx); return ledgerArr(p).slice(); }
  // last n deed TEXTS off a known profile (no extra profile load).
  function recentDeedsFrom(p, n) {
    var L = ledgerArr(p); n = n | 0; if (n <= 0) n = SCAR_SURFACE;
    var out = [], start = (L.length - n) > 0 ? (L.length - n) : 0;
    for (var i = start; i < L.length; i++) out.push(L[i].text);
    return out;
  }
  function recentDeeds(n) { var ctx = ctxOf(), p = profile(ctx); return recentDeedsFrom(p, n); }
  // the scars the current vision recounts (last SCAR_SURFACE deeds).
  function scars() { var ctx = ctxOf(), p = profile(ctx); return recentDeedsFrom(p, SCAR_SURFACE); }

  /* ======================================================================== *
   * STORY BEAT -- the host-facing payoff toast/card (NARRATIVE CONTINUITY SPEC
   * sec.2). The mission loop (and any other system) calls AKStory.storyBeat(beat)
   * on a WIN. If the host registered a richer renderer at ctx.ui.storyBeat it is
   * used; otherwise we degrade to the existing banner (ctx.showBanner, else
   * global.showBanner). The optional ctx arg lets a caller hand in its own LIVE
   * ctx (the mission loop does), falling back to the cached ctx for HUD callers.
   * Pure pass-through: shows + returns whether anything rendered. Writes nothing,
   * never throws. Beat shape: { title, line, next, scar?, advancesChapter? }.
   * The chapter/ledger wiring stays on logDeed + check (already public, below).
   * ======================================================================== */
  function storyBeat(beat, ctx) {
    if (!beat) return false;
    try {
      var c = ctx || ctxOf();
      if (c && c.ui && typeof c.ui.storyBeat === 'function') { c.ui.storyBeat(beat); return true; }
      var txt = String(beat.line == null ? '' : beat.line);
      if (beat.next) txt += '  ' + String(beat.next);
      if (!txt) return false;
      var sb = (c && typeof c.showBanner === 'function') ? c.showBanner
             : (typeof global.showBanner === 'function' ? global.showBanner : null);
      if (sb) { sb(txt, 4.2); return true; }
    } catch (_) {}
    return false;
  }

  /* ======================================================================== *
   * PUBLIC API (window.AKStory) -- EXPORTED BEFORE the registry bail so it is
   * harmless + headless-safe on pages without AK_SYSTEMS.
   * ======================================================================== */
  global.AKStory = {
    STAGES: GEN_I,                 // the CROWN CLIMB data (Gen I)
    GENS: GENS,                    // all generations (Gen I climb + Gen II/III stubs)
    CLANS: CLANS,
    stage: stage,                  // current {idx,id,title,objective,vision,gen}
    gen: gen,                      // current generation idx (0 = Gen I)
    check: check,                  // re-evaluate from profile+systems, persist, return idx
    advance: advance,              // advance(force?) one stage
    banner: banner,                // current objective text (HUD beacon)
    vision: vision,                // current dream text (the Old Pack)
    storyBeat: storyBeat,          // show a mission/story payoff beat (host renderer, else banner)
    packCap: packCap,              // max pack size gated by RANK (Stray 3 .. King of the Block 15)
    clan: clan,                    // chosen clan info | null
    setClan: setClan,              // optional explicit clan pick
    torchUnlocked: torchUnlocked,  // is the optional torch-pass available?
    passTorch: passTorch,          // begin the next generation with a chosen heir
    // --- CINEMA LAYER (full-screen chapter cards + cold-open) ---
    ART: STORY_ART,                // {narrator, nemesis} portrait paths (reused art)
    chapterCard: chapterCard,      // chapterCard(idx, gen?) -> full-screen card data
    coldOpen: coldOpen,            // the first-load flash-forward sequence
    coldOpenSeen: coldOpenSeen,    // has the cold-open already played?
    markColdOpenSeen: markColdOpenSeen, // persist that it played (mutateProfile)
    // --- THE COLLAR IS THE MONSTER (apex antagonist = the human system) ---
    collarReveal: collarReveal,    // Old Pack reveal near the rank ceiling | null
    markCollarSeen: markCollarSeen, // persist that the collar reveal has played
    // --- SCAR / MEMORY LEDGER (how you won) ---
    logDeed: logDeed,              // raid.js/encounters.js call this on a WIN
    ledger: ledger,                // full ledger copy (newest last)
    recentDeeds: recentDeeds,      // recentDeeds(n) -> last n deed texts
    scars: scars                   // the deeds the current vision recounts (last 3)
  };

  /* hub-only lifecycle: cache ctx + re-check the climb on a ~1.5s throttle. */
  if (!global.AK_SYSTEMS) return;
  global.AK_SYSTEMS.register({
    id: 'story',
    init: function (ctx) { S.ctx = ctx; try { check(); } catch (_) {} },
    onTick: function (dt, ctx) {
      S.ctx = ctx;
      S._acc += dt;
      if (S._acc < 1.5) return;          // throttle: no per-frame work
      S._acc = 0;
      try { check(); } catch (_) {}      // ONE mutateProfile max inside
    }
  });

})(typeof window !== 'undefined' ? window : globalThis);
