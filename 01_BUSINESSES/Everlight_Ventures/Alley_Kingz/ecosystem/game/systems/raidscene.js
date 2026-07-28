/* game/systems/raidscene.js -- AK_SYSTEMS "raid" wave companion (WALK-TO-RAID).
 * ===========================================================================
 * THE #1 TRUST GAP CLOSED: a RAID used to be a menu button that dropped you
 * into the SAME convoy battler with no enemy base. This module makes it REAL:
 *
 *   (1) ENEMY BASES WITH REAL LAYOUTS -- genTarget()/genTargets() build
 *       DETERMINISTIC procedural bot bases from a crew name/seed using the
 *       buildmode STRUCTURE VOCABULARY (WALL=200 / STONE=500 / METAL=1200 /
 *       BARRICADE=120 HP, per AK_RAID_DEFENSE_SYSTEM), a ring of walls around
 *       a CORE (Town Hall, coreHp), 8-16 structures, themed per the 4 crews
 *       (Boneguard / Zoomie / Leashbreak / K9 -- crew, NEVER clan).
 *
 *   (2) SCOUT / WALK-ON VIEW -- AK_RAIDSCENE.launch(target) opens a fresh
 *       ctx.overlay.open Canvas2D scene that RENDERS the enemy base from
 *       target.layout (their walls / buildings / core drawn as themed sprites
 *       with HP bars, exactly the structures you build in build mode), shows
 *       the DEFENDER CREW (real cards BY NAME) + the LOOT preview, and lets you
 *       WALK a scout dog around their block (left-half joystick). A big
 *       START RAID button drops you into the battler.
 *
 *   (3) THE RAID = base-as-battlefield -- START writes the target to the
 *       handoff (window.AK_RAID_TARGET + localStorage 'ak_raid_target', since
 *       the frozen ctx.battle.launch only forwards mode/city/level/nemesis) and
 *       calls ctx.battle.launch({mode:'raid', ...}). game/systems/modes.js's
 *       window.AK_MODES.raid reads the handoff and seeds the battlefield FROM
 *       the layout (the scouted walls scale the enemy base towers' HP, the CORE
 *       = the win condition). See modes.js.
 *
 * SHARED INTERFACE (agreed with the march/raid agent):
 *   window.AK_RAIDSCENE.launch(target) where target = { name, crew, faction,
 *     layout:[{type,x,y,hp,maxHp}], coreHp, trophies, reward:{gold,scrap,wood,
 *     stone,metal} }.  Also exposes genTarget(opts) / genTargets(n) / enrich(base).
 *
 * HARD LAW honored: 2.5D Canvas2D only (overlay = a fresh layer; the battler is
 * NEVER forked). Soft-currency + MATERIALS loot ONLY (gold/scrap/wood/stone/
 * metal) -- NO gems / $BCARDD / ALK anywhere in raid loot. Reuse the 106 cards
 * BY NAME for defenders. "crew" never "clan". Gritty gold cyberpunk dog-gang
 * voice. Headless-safe: AK_RAIDSCENE is exposed UNCONDITIONALLY (raid.js +
 * worldmap.js + the node harness call it on pages without AK_SYSTEMS too), and
 * there is ZERO top-level DOM / localStorage at module load.
 * ========================================================================== */
(function (global) {
  'use strict';

  var GOLD = '#e8c55a', GOLD_D = '#c9a84c', RED = '#C0392B', INK = '#06060a',
      TXT = '#E8E8E8', DIM = '#9a8f6a';

  // ---- wall HP from the buildmode / AK_RAID_DEFENSE_SYSTEM spec --------------
  var WALL_HP = { WALL: 200, STONE: 500, METAL: 1200, BARRICADE: 120 };
  // producer-building HP (defensible mid values; buildings sit inside the ring)
  var BLD_HP  = { GEM: 700, MINT: 700, FORGE: 850, LAB: 750, GEN: 900 };
  var BLD_GLYPH = { GEM: 'G', MINT: '$', FORGE: 'F', LAB: 'L', GEN: 'E' };
  var BLD_NAME  = { GEM: 'Gem Mine', MINT: 'Gold Mint', FORGE: 'Card Forge', LAB: 'Research Lab', GEN: 'Generator' };

  // ---- AK-STRUCTART: scout-scene structures use the SAME placed-structure PNGs
  // the build mode paints (struct_wall/stone/metal/barricade), so the enemy base
  // reads as a real base, not a procedural mock (#4). Producer buildings reuse the
  // hub facade art (assets/hub/<facade>.png). Headless-safe: no Image() in node ->
  // spriteImg() returns null -> drawStruct falls back to the procedural Canvas2D draw.
  var STRUCT_SPRITE = {
    WALL:  'assets/sprites/struct_wall.png',  STONE: 'assets/sprites/struct_stone.png',
    METAL: 'assets/sprites/struct_metal.png', BARRICADE: 'assets/sprites/struct_barricade.png'
  };
  var BLD_FACADE = { GEM: 'gem_mine', MINT: 'gold_mint', FORGE: 'card_forge', LAB: 'research_lab', GEN: 'power_gen' };
  var _img = {};
  function spriteImg(path) {
    if (!path || typeof Image === 'undefined') return null;
    var im = _img[path];
    if (im === undefined) { im = new Image(); im.onerror = function () { _img[path] = null; }; im.src = path; _img[path] = im; }
    return im;   // null (known-dead) | a loading/loaded Image
  }
  function spriteReady(im) { return !!(im && im.complete && im.naturalWidth > 0); }

  // ---- the 4 crews/factions (crew, NEVER clan) -- mirrors raid.js FACTIONS so a
  // target generated here is consistent with the war map's pins + intel. -------
  var FACTIONS = [
    { id: 'boneguard_crew',   cls: 'Boneguard Crew',   accent: '#e8c55a',
      gangs: ['The Boneyard Mob', 'Crypt Kings', 'Marrow Syndicate'],
      pool: { Common: ['Tank Pug', 'Copper Chow', 'Brick Bullmastiff', 'Hatchet'], Rare: ['Granite Saint', 'Grit Bulldog', 'Alloy Akita', 'Warden Newfie'], Epic: ['Balboa', 'Iron Rottweiler', 'Anvil', 'Bonecrusher'], Legendary: ['Stonejaw', 'Cinderblock', 'Tombstone'], Mythic: ['$BCARDD'] } },
    { id: 'zoomie_syndicate', cls: 'Zoomie Syndicate', accent: '#7CFFB0',
      gangs: ['Zoomie Riot', 'Nitro Pack', 'The Burnouts'],
      pool: { Common: ['Neon Whippet', 'Turbo Jack', 'Drift Sheltie', 'Byte Beagle'], Rare: ['Pixel Greyhound', 'Circuit Shiba', 'Flash Saluki', 'Bolt Corgi'], Epic: ['Razor Vizsla', 'Aero Malinois', 'Roadblock', 'Bullbar'], Legendary: ['Rollcage', 'Deadweight'], Mythic: ['Jagged'] } },
    { id: 'leashbreak_tactix', cls: 'Leashbreak Tactix', accent: '#9d8bff',
      gangs: ['Leashless Cartel', 'Ghost Wire Tactix', 'The Static Saints'],
      pool: { Common: ['Echo Dalmatian', 'Static Sheba Inu', 'Vibe Shih Tzu', 'Hexer'], Rare: ['Holo Husky', 'Chill Samoyed', 'Prism Poodle', 'Signal Pointer'], Epic: ['Synth Collie', 'Noir Setter', 'Pulse Border Collie', 'Deadbolt'], Legendary: ['Firewall', 'Sandbag', 'Bulwark'], Mythic: ['Rosco'] } },
    { id: 'k9_circuitry',     cls: 'K9 Circuitry',     accent: '#7fc8ff',
      gangs: ['Circuit Hounds', 'The Grid Pack', 'Voltage Kennel'],
      pool: { Common: ['Neon Dachshund', 'Flux Pomeranian', 'Rail Terrier', 'Buckshot'], Rare: ['Laser Beagle', 'Volt Corgi', 'Grid Schnauzer', 'Beacon Basset'], Epic: ['Circuit Retriever', 'Nova Shepherd', 'Bunker', 'Howitzer'], Legendary: ['Casemate', 'Emplacement'], Mythic: ['Crown Foxhound'] } }
  ];
  var FAC_BY_ID = {}; FACTIONS.forEach(function (f) { FAC_BY_ID[f.id] = f; });

  /* ---------------------------------------------------------------- helpers */
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  // FNV-1a -> a stable 32-bit seed from a crew name (deterministic bases)
  function seedFromName(s) { s = String(s == null ? 'rival' : s); var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  // mulberry32 PRNG
  function rng32(seed) { var s = seed >>> 0; return function () { s |= 0; s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  function resolveFaction(idOrCls) {
    if (!idOrCls) return null;
    if (FAC_BY_ID[idOrCls]) return FAC_BY_ID[idOrCls];
    for (var i = 0; i < FACTIONS.length; i++) if (FACTIONS[i].cls === idOrCls) return FACTIONS[i];
    return null;
  }
  // a card name exists in the live table? (so a rename can never desync)
  function liveName(ctx, name) { try { return !!(ctx && ctx.cards && ctx.cards()[name]); } catch (_) { return true; } }
  function pickRoster(ctx, f, tier, r) {
    var tiers = tier >= 3 ? ['Legendary', 'Epic', 'Epic', 'Rare'] : tier === 2 ? ['Epic', 'Rare', 'Rare', 'Common'] : ['Rare', 'Common', 'Common', 'Common'];
    var out = [];
    tiers.forEach(function (rar) {
      var bag = (f.pool[rar] || f.pool.Common).filter(function (n) { return liveName(ctx, n); });
      if (!bag.length) bag = f.pool[rar] || f.pool.Common;
      var n = bag[Math.floor(r() * bag.length)];
      if (out.indexOf(n) < 0) out.push(n); else out.push(bag[(bag.indexOf(n) + 1) % bag.length]);
    });
    return out;
  }
  // marquee defender -> a fielded nemesis blob (engine AK-NEMESIS) | null
  function nemesisFor(ctx, target) {
    try {
      // crew may arrive as a roster ARRAY (raidscene-native) OR a class STRING
      // (worldmap targets) -- resolve the marquee defender safely from either.
      var arr = (target && Array.isArray(target.roster) && target.roster.length) ? target.roster
              : (target && Array.isArray(target.crew) ? target.crew : []);
      var nm = arr[0];
      if (!nm || !ctx || !ctx.cards) return null;
      var c = ctx.cards()[nm]; var n = c && (c.cardNumber || c.id);
      if (!n) return null;
      return { card: String(n), name: nm, title: target.name, tier: target.tier || 1, taunt: 'You picked the wrong block, mutt.' };
    } catch (_) { return null; }
  }

  /* ===================================================================== *
   * (1) PROCEDURAL BASE GENERATION (deterministic from a crew name/seed)
   * ===================================================================== */
  // layout coords live in a normalized 0..100 x 0..100 "base plot". The SCOUT
  // scene maps that to the viewport; modes.js maps it into the enemy arena half.
  // GOAL 11a 2026-07-03: DISTINCT bases. genLayout picks 1 of 4 TEMPLATES by seed (ring / grid / cluster /
  // fortress), each with its own wall placement, density and producer mix, so different rivals yield visibly
  // different blocks -- not the same 5 buildings. GOAL 10 (retuned AK-LOOTALL 2026-07-10): it also seeds 6-10
  // GATHERABLE harvest nodes (tag node:true so akRaidZoneFrom skips them and akRaidBuildZones instantiates them into RAID.nodes).
  function genLayout(r, tier) {
    var out = [];
    var cx = 50, cy = 36, radX = 30, radY = 22;
    // --- the CORE (Town Hall) -- hp filled by the caller from coreHp ---
    out.push({ type: 'CORE', x: cx, y: cy, hp: 0, maxHp: 0, name: 'TOWN HALL' });
    var heavy = tier >= 3 ? 'METAL' : tier >= 2 ? 'STONE' : 'WALL';
    var light = tier >= 3 ? 'STONE' : 'WALL';
    var tpl = Math.floor(r() * 4);   // 0 ring | 1 grid | 2 cluster | 3 fortress
    if (tpl === 0) {
      // RING -- walls circle the core (count + material scale with tier)
      var ringN = 6 + Math.floor(r() * (tier >= 3 ? 6 : tier >= 2 ? 4 : 3));   // 6..11
      for (var i = 0; i < ringN; i++) {
        var a = -Math.PI / 2 + (i / ringN) * Math.PI * 2;
        var wt = (r() < 0.3) ? light : heavy;                 // mixed perimeter
        var x = cx + Math.cos(a) * radX * (0.85 + r() * 0.3);
        var y = cy + Math.sin(a) * radY * (0.85 + r() * 0.3);
        out.push({ type: wt, x: clamp(x, 7, 93), y: clamp(y, 8, 64), hp: WALL_HP[wt], maxHp: WALL_HP[wt] });
      }
    } else if (tpl === 1) {
      // GRID -- a lattice of walls in rows (a fortified compound), gaps punched by seed
      var cols = 3 + Math.floor(r() * 2), rows = 2 + Math.floor(r() * 2);
      for (var gr = 0; gr < rows; gr++) for (var gc = 0; gc < cols; gc++) {
        if (r() < 0.22) continue;                             // gaps you can slip through
        var gwt = (r() < 0.4) ? light : heavy;
        out.push({ type: gwt, x: clamp(20 + gc * (56 / (cols - 1 || 1)) + (r() * 6 - 3), 7, 93), y: clamp(13 + gr * 14 + (r() * 4 - 2), 8, 64), hp: WALL_HP[gwt], maxHp: WALL_HP[gwt] });
      }
    } else if (tpl === 2) {
      // CLUSTER -- loose knots of cover, low wall density (a scrappy, open block)
      var knots = 4 + Math.floor(r() * 4);
      for (var c2 = 0; c2 < knots; c2++) {
        var cwt = (r() < 0.6) ? light : heavy;
        out.push({ type: cwt, x: clamp(12 + r() * 76, 7, 93), y: clamp(12 + r() * 50, 8, 64), hp: WALL_HP[cwt], maxHp: WALL_HP[cwt] });
      }
    } else {
      // FORTRESS -- a DOUBLE ring, heavy material, high density (a hard target)
      var fN = 8 + Math.floor(r() * 5);
      for (var f = 0; f < fN; f++) {
        var fa = -Math.PI / 2 + (f / fN) * Math.PI * 2, inner = (f % 2 === 0);
        var frx = inner ? 18 : 32, fry = inner ? 13 : 24;
        var fwt = inner ? heavy : (r() < 0.5 ? heavy : light);
        out.push({ type: fwt, x: clamp(cx + Math.cos(fa) * frx * (0.9 + r() * 0.2), 7, 93), y: clamp(cy + Math.sin(fa) * fry * (0.9 + r() * 0.2), 8, 64), hp: WALL_HP[fwt], maxHp: WALL_HP[fwt] });
      }
    }
    // --- a barricade or two guarding the front gate (common to all templates) ---
    var gates = 1 + Math.floor(r() * 2);
    for (var b = 0; b < gates; b++) {
      out.push({ type: 'BARRICADE', x: clamp(cx + (b ? 14 : -14) + (r() * 8 - 4), 8, 92), y: clamp(cy + radY + 8, 10, 70), hp: WALL_HP.BARRICADE, maxHp: WALL_HP.BARRICADE });
    }
    // --- producer buildings inside the block (fortress packs more; mix varies by seed) ---
    var bldKeys = ['GEM', 'MINT', 'FORGE', 'LAB', 'GEN'];
    var bn = (tpl === 3 ? 3 : 2) + Math.floor(r() * (tier >= 2 ? 3 : 2));     // 2..5
    for (var k = 0; k < bn; k++) {
      var key = bldKeys[Math.floor(r() * bldKeys.length)];
      var ba = r() * Math.PI * 2, bd = r() * 14;
      out.push({ type: key, x: clamp(cx + Math.cos(ba) * bd, 14, 86), y: clamp(cy + Math.sin(ba) * (bd * 0.7), 12, 60), hp: BLD_HP[key], maxHp: BLD_HP[key], name: BLD_NAME[key] });
    }
    // --- GOAL 10 + AK-LOOTALL 2026-07-10 ("take everything -- their trees, their stone, their resources"):
    // 6-10 GATHERABLE harvest nodes per base (was 2-4), count scaled by base size, kinds mixed. Per-node yields
    // trimmed (wood 10->5, scrap 4->2, produce 8->4) so total raid loot stays ~1.5x the old economy even with
    // minable props + producer bursts on top (index.html AK-LOOTALL). node:true so akRaidZoneFrom skips them
    // (never a "structure" for the win-count); akRaidBuildZones banks them as RAID.nodes.
    var nodeKinds = [{ type: 'tree', kind: 'wood', amt: 5 }, { type: 'scrap', kind: 'scrap', amt: 2 }, { type: 'garden', kind: 'produce', amt: 4 }];
    var structN = out.length;   // core + walls + gates + buildings placed so far = the base's size
    var nn = Math.min(10, 6 + Math.floor(r() * 3) + (structN >= 16 ? 2 : structN >= 12 ? 1 : 0));   // 6..10, bigger base = more to strip
    for (var q = 0; q < nn; q++) {
      var nk = nodeKinds[Math.floor(r() * nodeKinds.length)];
      var nhp = 90 + Math.floor(r() * 70) + tier * 20;   // ~110..200 -- a few hits, not a chore
      out.push({ node: true, type: nk.type, x: clamp(10 + r() * 80, 8, 92), y: clamp(cy + radY + 4 + r() * 24, 12, 78), hp: nhp, maxHp: nhp, loot: { kind: nk.kind, amount: nk.amt + Math.floor(r() * nk.amt) } });
    }
    return out;   // 1 core + template walls + 1..2 barricades + 2..5 buildings + 6..10 harvest nodes (capped by clamps)
  }

  // build a full raid TARGET (the shared-interface shape). opts may be a flat
  // war-map base ({name,faction,tier,roster,...}) -> it gets enriched, not replaced.
  function genTarget(opts, ctx) {
    opts = opts || {}; ctx = ctx || global.AK_CTX || null;
    var fac = resolveFaction(opts.faction || opts.cls);
    var name = opts.name;
    var seed = (typeof opts.seed === 'number') ? (opts.seed >>> 0) : seedFromName(name || (fac && fac.id) || 'rival');
    var r = rng32(seed);
    if (!fac) fac = FACTIONS[Math.floor(r() * FACTIONS.length)];
    if (!name) name = fac.gangs[Math.floor(r() * fac.gangs.length)];
    var tier = clamp(opts.tier || (1 + Math.floor(r() * 3)), 1, 3);
    var coreHp = 3600 + tier * 950 + Math.floor(r() * 500);   // ~4550..6650 (big enough to be multi-frame, never one-shot)
    var layout = genLayout(r, tier);
    for (var i = 0; i < layout.length; i++) if (layout[i].type === 'CORE') { layout[i].hp = coreHp; layout[i].maxHp = coreHp; }
    var crew = opts.crew || opts.roster || pickRoster(ctx, fac, tier, r);
    var reward = opts.reward || {
      gold:  110 * tier + Math.floor(r() * 90),
      scrap: tier >= 2 ? 2 * tier : 1,
      scrapR: tier >= 3 ? 'Epic' : 'Rare',
      wood:  20 * tier + Math.floor(r() * 20),
      stone: tier >= 2 ? 10 * tier : 0,
      metal: tier >= 3 ? 6 * tier : 0,
      produce: 12 * tier + Math.floor(r() * 12)            // AK-RAIDLOOT: their farmed produce (the tradable peasant resource)
    };
    return {
      id: opts.id || ('rs_' + seed.toString(36)),
      name: name, faction: fac.id, cls: fac.cls, accent: fac.accent,
      crew: crew, roster: crew, tier: tier,
      trophies: opts.trophies || (280 + tier * 210 + Math.floor(r() * 160)),
      layout: layout, coreHp: coreHp, reward: reward,
      city:       (opts.city != null) ? opts.city : clamp(tier + 1, 0, 9),
      level:      (opts.level != null) ? opts.level : clamp(2 + tier * 2, 1, 10),
      diffOffset: (opts.diffOffset != null) ? opts.diffOffset : (tier - 1)
    };
  }

  // attach layout/coreHp/reward/crew to an EXISTING war-map base in place
  // (idempotent -- raid.js + worldmap.js call this so every bot carries a real layout).
  // BASE-ID INVARIANT (the #1 reason ak_raid_log stayed 0): enrich MUST NOT re-stamp
  // the id. A real Supabase base id (a bot-row uuid, or a live player's user_id) rides
  // in on base.id and MUST survive so modes.js isServerBaseId() returns true and the
  // server {action:'resolve'} actually fires. enrich mutates in place and only ever
  // assigns id when the incoming base has NONE -- and then only the local, prefixed
  // genTarget id (rs_...), which correctly routes to the offline fallback. A truthy
  // server uuid is therefore never touched; a local bot_/wm_loc_/wc_ id is preserved
  // exactly (they keep the local fallback). Verified by the raid harness.
  function enrich(base, ctx) {
    if (!base || typeof base !== 'object') return base;
    if (Array.isArray(base.layout) && base.layout.length && base.coreHp && base.reward) return base;
    var t = genTarget(base, ctx);
    if (!base.id && t.id) base.id = t.id;   // ONLY fill a missing id (local rs_...); a real uuid is left untouched
    base.layout = t.layout; base.coreHp = t.coreHp; base.reward = base.reward || t.reward;
    base.crew = base.crew || base.roster || t.crew; base.roster = base.roster || base.crew;
    if (base.city == null) base.city = t.city;
    if (base.level == null) base.level = t.level;
    if (base.diffOffset == null) base.diffOffset = t.diffOffset;
    if (!base.accent) base.accent = t.accent;
    if (!base.cls) base.cls = t.cls;
    return base;
  }

  // a rotating list of N targets (mirrors raid.js's ~12-min window rotation)
  function genTargets(n, ctx) {
    n = n || 3;
    var windowId = Math.floor(Date.now() / (12 * 60 * 1000));
    var out = [];
    for (var i = 0; i < n; i++) {
      var seed = (windowId * 2654435761 + i * 40503) >>> 0;
      out.push(genTarget({ seed: seed }, ctx));
    }
    return out;
  }

  /* ===================================================================== *
   * HANDOFF -> the battler (mode:'raid'). The frozen ctx.battle.launch only
   * forwards mode/city/level/diffOffset/nemesis, so the full target rides a
   * SEPARATE channel that modes.js's AK_MODES.raid.setup reads.
   * ===================================================================== */
  /* ===================================================================== *
   * SERVER-AUTHORITATIVE RAID SETTLEMENT (ak-raid {action:'resolve'})
   * The async real-player loop's LAST MILE. Every raid battler funnels its result
   * through target.onResult (below): the in-hub akEnterRaid calls it, modes.js's
   * openWorldMoba forwards it, the tower fallback carries it. On a WIN against a
   * REAL server base id, the SERVER caps + banks the loot on ak_grants (drained
   * exactly once via AKSocial.claimGrants), ledgers ak_raid_log ONCE per window,
   * and pushes a 24h revenge row to a real victim -- the client only drains grants.
   * A LOCAL id (bot_/rs_/wm_loc_/wc_), signed-out, or a network error degrades to
   * grantRaidReward -- today's exact single-player loot. OFFLINE-DEGRADING.
   * (This is the ak-raid edge fn -- LIVE/deployed on project mfghdobptredxxhbjwyz.)
   * ===================================================================== */
  // a server base id is a real uuid (a bot row id, or a victim's user_id). Local
  // procedural ids are all prefixed -> never resolvable server-side. Mirrors
  // modes.js isServerBaseId() EXACTLY (the two MUST agree).
  function isServerBaseId(id) { return typeof id === 'string' && id.length >= 8 && !/^(bot_|rs_|wm_loc_|wc_)/.test(id); }
  function akRaidClient() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_e) { return null; } }
  function akSignedIn() { try { return !!(global.AKAccount && global.AKAccount.user && global.AKAccount.user()); } catch (_e) { return false; } }
  function starMult(stars) { var s = stars | 0; return s >= 3 ? 2.5 : s >= 2 ? 1.5 : 1.0; }
  // LOCAL loot grant (offline / signed-out / a local id / a server error). This is
  // the EXACT payout the raid paid before the server loop existed -- byte-identical
  // to the old inline onResult body (star-scaled soft currency + materials only).
  function grantRaidReward(target, stars) {
    try {
      var E = global.AK_ECON; if (!E || !E.mutateProfile) return;
      var r = target && target.reward; if (!r) return;
      var mult = starMult(stars);
      var gm = (E.garageLootMult) ? E.garageLootMult() : 1; mult = mult * gm;
      if (r.scrap && E.addScrap) E.addScrap(r.scrapR || 'Rare', Math.round((r.scrap | 0) * mult));
      if (r.wood  && E.bankMaterial) E.bankMaterial('wood',  Math.round((r.wood  | 0) * mult));
      if (r.stone && E.bankMaterial) E.bankMaterial('stone', Math.round((r.stone | 0) * mult));
      if (r.metal && E.bankMaterial) E.bankMaterial('metal', Math.round((r.metal | 0) * mult));
      E.mutateProfile(function (p) {
        if (r.gold)    p.coins   = (p.coins   | 0) + Math.round((r.gold    | 0) * mult);
        if (r.produce) p.produce = (p.produce | 0) + Math.round((r.produce | 0) * mult);
      });
    } catch (_e) {}
  }
  // AK-DUTYWIRE 2026-07-18: the CLAN DUTY credit for a raid. missions.js exposes
  // AKDuties.reportRaidRun (the daily "Run a raid" + the weekly "Run 10 raids"
  // ladders) and it had ZERO call sites repo-wide, so 1 of 3 dailies, 1 of 3
  // weeklies and 1 crate key a week could NEVER be claimed. Fired ONLY from the WON
  // branch of target.onResult -- the one result funnel every raid path lands in
  // (in-hub akExitRaid, modes.openWorldMoba onClose, the ctx.battle.launch fallback).
  // WIN-gated on purpose: a bail-out routes through index.html's LEAVE -> akRaidEnd(
  // pct >= 0.5), so an abandoned run arrives as {win:false} and is indistinguishable
  // from a real loss -- gating on the win is the only way an abandon can never score.
  // Idempotent per target via _dutyRaid (mirrors the _raidSettled loot guard) so a
  // double-fired onResult can never double-count. Fully guarded: a missing AKDuties
  // (bare page / node harness) is a silent no-op, never a throw inside the game loop.
  function creditRaidDuty(target) {
    try {
      if (!target || target._dutyRaid) return;
      target._dutyRaid = true;                                // flag FIRST -- reentrancy-proof
      var D = global.AKDuties;
      if (D && typeof D.reportRaidRun === 'function') D.reportRaidRun(1);
    } catch (_e) {}
  }

  // settleRaidServer(target, stars) -> true when the SERVER will settle this win's
  // loot (the caller then SUPPRESSES its local grant); false = degrade to local.
  // Idempotent per target (one settle per raid). Fully guarded: no client /
  // signed-out / a local id all return false so the caller pays local loot --
  // signed-out is EXACTLY today's single-player game.
  function settleRaidServer(target, stars) {
    if (!target) return false;
    if (target._raidSettled) return !!target._raidServer;   // idempotent -- never settle a raid twice
    var id = target.id, sb = akRaidClient();
    if (!(id && isServerBaseId(id) && sb && akSignedIn())) return false;   // -> local fallback (offline-degrade)
    target._raidSettled = true; target._raidServer = true;
    var st = clamp(stars | 0, 1, 3);
    try {
      sb.functions.invoke('ak-raid', { body: { action: 'resolve', base_id: id, revenge: !!target._revenge, won: true, stars: st, name: (target.name || 'Rival Crew') } })
        .then(function (r) {
          var d = r && r.data;
          if (d && d.ok && d.looted) {                        // server paid -> drain the queued grants ONCE
            try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_e) {}
          } else if (!(d && d.ok)) {                          // hard error -> local fallback (full amount)
            grantRaidReward(target, st);
          }
          // d.ok && !looted == already looted this window -> replays are free (intended)
        }, function () { grantRaidReward(target, st); });     // network error -> local fallback
    } catch (_e2) { grantRaidReward(target, st); }
    return true;
  }

  function beginRaid(ctx, target) {
    global.AK_RAID_TARGET = target;                          // in-memory (same-page + node harness)
    try { if (typeof localStorage !== 'undefined') localStorage.setItem('ak_raid_target', JSON.stringify(target)); } catch (_e) {}
    // AK-RAID-RPG 2026-06-26: world-map raids are RPG-STYLE (modes' own openWorldMoba unit-fight),
    // NOT the frozen lane/tower engine. The tower (ctx.battle.launch) stays the ARENA door only.
    var _M = global.AK_MODES;
    // AK-RAIDLOOT 2026-06-29: the target's farmed stash, star-scaled (1*=1.0 / 2*=1.5 / 3*=2.5x,
    // mirrors modes.js raid tranches). scrap is an OBJECT keyed by rarity -- route through addScrap
    // (the old p.scrap = (p.scrap|0)+n corrupted the bag); mats go through the capped bankMaterial.
    target.onResult = function (res) {
      try {
        var won = !!(res && res.win), E = global.AK_ECON;
        if (!E || !E.mutateProfile) return;
        if (won && target.reward) {
          var stars = (res && res.stars) | 0;
          // SERVER-AUTHORITATIVE settle: a REAL server base (a bot uuid or a live
          // player's user_id) + a signed-in raider routes loot through ak-raid
          // {action:'resolve'} -- the server CAPS + banks it on ak_grants (drained
          // exactly once via AKSocial.claimGrants), ledgers ak_raid_log, and arms a
          // 24h revenge row for a real victim. settleRaidServer() suppresses the
          // local grant so loot lands ONCE. Signed-out / a local (bot_/rs_/wm_loc_)
          // id / a network error all fall through to grantRaidReward -- signed-out
          // is EXACTLY today's single-player loot.
          if (!settleRaidServer(target, stars)) grantRaidReward(target, stars);
          creditRaidDuty(target);   // AK-DUTYWIRE 2026-07-18: the raid daily + weekly duty ladders
          var _bn = (typeof window !== 'undefined' && window.showBanner) ? window.showBanner : (ctx && ctx.showBanner);
          if (_bn) _bn('RAID WON -- you took their stash', 1.8);
        } else if (!won && typeof E.raidDamage === 'function') {
          try { E.raidDamage(E.loadProfile ? E.loadProfile() : null, 1); } catch (_d) {}
          var _bn2 = (typeof window !== 'undefined' && window.showBanner) ? window.showBanner : (ctx && ctx.showBanner);
          if (_bn2) _bn2('RAID LOST -- you took damage', 1.8);
        }
      } catch (_e2) {}
    };
    // AK-HUBRAID 2026-06-30: route the raid INTO the hub renderer -- you walk the opponent's REAL
    // district (their buildings/layout in the SAME draw() as your own base), not the standalone arena.
    // Falls back to the modes openWorldMoba arena only if the in-hub raid is unavailable.
    if (typeof global.akEnterRaid === 'function') { try { global.akEnterRaid(target); return target; } catch (_e3) {} }
    if (_M && typeof _M.openWorldMoba === 'function') {
      _M.openWorldMoba(ctx, { enemyHero: nemesisFor(ctx, target), raidTarget: target, label: 'RAID -- ' + (target.name || 'Rival Crew'), onResult: target.onResult });
      return target;
    }
    if (ctx && ctx.battle && ctx.battle.launch) {   // fallback only if modes not loaded
      ctx.battle.launch({
        mode: 'raid',
        city: target.city, level: target.level, diffOffset: target.diffOffset,
        nemesis: nemesisFor(ctx, target),
        label: 'RAID -- ' + (target.name || 'Rival Crew')
      });
    }
    return target;
  }

  /* ===================================================================== *
   * (2) THE SCOUT / WALK-ON SCENE  (ctx.overlay.open Canvas2D layer)
   * ===================================================================== */
  function roundRect(g, x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function txt(g, s, x, y, font, color, align) { g.save(); g.font = font; g.fillStyle = color; g.textAlign = align || 'left'; g.textBaseline = 'alphabetic'; g.fillText(s, x, y); g.restore(); }
  function hpBar(g, x, y, w, frac, col) { g.save(); roundRect(g, x, y, w, 4, 2); g.fillStyle = 'rgba(0,0,0,.55)'; g.fill(); roundRect(g, x, y, w * clamp(frac, 0, 1), 4, 2); g.fillStyle = col; g.fill(); g.restore(); }

  // draw one structure as a themed sprite (matches the build-mode look)
  function drawStruct(g, s, X, Y, sz, accent) {
    var w = sz, h = sz, x = X - w / 2, y = Y - h / 2;
    // 2.5D contact shadow -- cheap (offset dark ellipse, NO per-frame shadowBlur)
    // so the structure reads as sitting ON the block. 60fps-safe.
    g.save(); g.fillStyle = 'rgba(0,0,0,.40)'; g.beginPath();
    g.ellipse(X, Y + h * 0.46, w * 0.50, h * 0.20, 0, 0, 7); g.fill(); g.restore();
    // PNG sprite for the wall family (the SAME art the build mode places) -----
    var sp = STRUCT_SPRITE[s.type] ? spriteImg(STRUCT_SPRITE[s.type]) : null;
    if (spriteReady(sp)) { g.save(); g.drawImage(sp, x, y - h * 0.16, w, h * 1.16); g.restore(); return; }   // slight lift = extrusion
    // AK-BASEASSAULT 2026-06-29: the TOWN HALL renders with the SAME facade the player sees
    // in their own hub (assets/hub/town_hall.png, then the build-mode th_exterior fallback), so
    // raiding it reads as hitting a real district -- not an abstract crown box.
    if (s.type === 'CORE') {
      var th = spriteImg('assets/hub/town_hall.png'); if (!spriteReady(th)) th = spriteImg('assets/sprites/th_exterior.png');
      if (spriteReady(th)) {
        g.save(); g.drawImage(th, x, y - h * 0.22, w, h * 1.22); g.restore();
        g.save(); g.strokeStyle = GOLD; g.lineWidth = 2; g.globalAlpha = 0.85; roundRect(g, x, y - h * 0.22, w, h * 1.22, 5); g.stroke(); g.restore();
        return;
      }
    }
    // producer buildings reuse the hub facade art when present ----------------
    if (BLD_FACADE[s.type]) {
      var fa = spriteImg('assets/hub/' + BLD_FACADE[s.type] + '.png');
      if (spriteReady(fa)) { g.save(); roundRect(g, x, y - h * 0.10, w, h * 1.10, 5); g.clip(); g.drawImage(fa, x, y - h * 0.10, w, h * 1.10);
        g.restore(); g.save(); roundRect(g, x, y - h * 0.10, w, h * 1.10, 5); g.lineWidth = 1.6; g.strokeStyle = accent || GOLD_D; g.stroke(); g.restore(); return; }
    }
    g.save();
    if (s.type === 'CORE') {
      g.fillStyle = '#15110a'; roundRect(g, x, y, w, h, 5); g.fill();
      g.strokeStyle = GOLD; g.lineWidth = 2.5; g.shadowColor = GOLD; g.shadowBlur = 10; g.stroke();
      g.shadowBlur = 0; g.fillStyle = GOLD; g.font = '900 ' + Math.round(sz * 0.7) + 'px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('♛', X, Y + 1);  // crown glyph
    } else if (s.type === 'WALL') {
      g.fillStyle = '#5d3b1f'; g.fillRect(x, y, w, h); g.strokeStyle = GOLD_D; g.lineWidth = 1.5; g.strokeRect(x, y, w, h);
    } else if (s.type === 'STONE') {
      g.fillStyle = '#6c6f76'; g.fillRect(x, y, w, h); g.strokeStyle = 'rgba(20,20,26,.6)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, Y); g.lineTo(x + w, Y); g.moveTo(X, y); g.lineTo(X, y + h); g.stroke(); g.strokeStyle = GOLD_D; g.strokeRect(x, y, w, h);
    } else if (s.type === 'METAL') {
      g.fillStyle = '#39434e'; g.fillRect(x, y, w, h); g.fillStyle = 'rgba(127,200,255,.18)'; g.fillRect(x, y, w, 3); g.strokeStyle = GOLD; g.lineWidth = 2; g.strokeRect(x, y, w, h);
    } else if (s.type === 'BARRICADE') {
      g.fillStyle = '#1a1712'; g.fillRect(x, y, w, h); g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.strokeStyle = GOLD; g.lineWidth = 4; for (var sx = -w; sx < w; sx += 9) { g.beginPath(); g.moveTo(X + sx, y - 3); g.lineTo(X + sx + h + 4, y + h + 3); g.stroke(); } g.restore(); g.strokeStyle = GOLD_D; g.lineWidth = 1.5; g.strokeRect(x, y, w, h);
    } else { // producer building
      g.fillStyle = '#1a1925'; roundRect(g, x, y, w, h, 4); g.fill(); g.strokeStyle = accent || GOLD_D; g.lineWidth = 1.8; g.stroke();
      g.fillStyle = accent || GOLD; g.font = '900 ' + Math.round(sz * 0.55) + 'px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(BLD_GLYPH[s.type] || 'B', X, Y + 1);
    }
    g.restore();
  }

  function launch(target, ctx) {
    ctx = ctx || global.AK_CTX || null;
    // accept a flat war-map base, a partial, or nothing -> always end up with a full target
    target = (target && Array.isArray(target.layout) && target.layout.length && target.coreHp)
      ? target : genTarget(target || {}, ctx);

    // AK-NOSCOUT 2026-07-01: the pre-raid scout / walk-on "this is the base" screen is retired
    // (operator: "that second screen is pointless"). A launched raid now goes STRAIGHT into the
    // fight. beginRaid seeds the handoff + the onResult loot, then routes to global.akEnterRaid
    // (the in-hub raid), falling back to modes.openWorldMoba / ctx.battle.launch exactly as before.
    return beginRaid(ctx, target);
  }

  /* ===================================================================== *
   * PUBLIC API (exposed UNCONDITIONALLY -- headless-safe, no DOM at load)
   * ===================================================================== */
  global.AK_RAIDSCENE = {
    launch: launch,
    genTarget: genTarget,
    genTargets: genTargets,
    enrich: enrich,
    nemesisFor: nemesisFor,
    // AK-DUTYWIRE 2026-07-18: the two raid paths that build their OWN onResult and skip
    // beginRaid (raidmap.js's rival-row raid, worldmap.js raidFrom) call this one line
    // from their WIN branch so their raids feed the duty ladders too. Idempotent per
    // target, so calling it on a target that already went through beginRaid is a no-op.
    creditRaidDuty: creditRaidDuty,
    // AK-BASEASSAULT 2026-06-29: modes.js reuses this exact build-mode structure art so the
    // raid battlefield reads as a real district (one shared structure renderer, no fork).
    drawStruct: drawStruct,
    WALL_HP: WALL_HP,
    BLD_HP: BLD_HP,
    FACTIONS: FACTIONS
  };

})(typeof window !== 'undefined' ? window : globalThis);
