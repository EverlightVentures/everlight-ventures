/* game/systems/defense.js -- BLOCK WAR: the offline DEFENSE engine (incoming raids).
 * ---------------------------------------------------------------------------
 * The missing Clash-core half. raid.js is the SWORD (you hit THEIR block);
 * THIS module is the SHIELD WALL (rivals hit YOURS while you sleep). It owns:
 *   (1) DEFENSE POSTS -- up to 4 posted deck dogs standing HOME_TURF (fixed
 *       spots spread across The Lot; the HUB lane draws them, we own state).
 *       The wall MANS ITSELF: autoAssign(p) lazily fills every unmanned post
 *       from the player's ACTIVE 11-CARD DECK (localStorage 'ak_decks' +
 *       'ak_active', the flat mirror game.html saveProfile writes; strongest
 *       OWNED dogs as the fallback pool), picking the best by CLASS FIT
 *       (TUNE.CLASS_POST_FIT -- bruisers and standing steel post best) scaled
 *       by rarity + level, skipping Infirmary-downed dogs. Manual picks are
 *       LAW: assign()/clear() stamp assignedBy 'manual' and auto NEVER touches
 *       a manual slot (a manually cleared post stays empty on purpose).
 *   (2) defenseScore(p) -- ONE number for how hard your block is to crack:
 *       posted cards (rarity/level weighted) + wall/structure HP (p.builds,
 *       AK_BUILDMODE data) + fortify level + an active Watch bonus (AKGuard).
 *   (3) resolveIncoming(p, now) -- the OFFLINE RAID RESOLVER. On load it
 *       deterministically settles what hit the block since lastResolve
 *       (population.js resolveOvernight idiom: mulberry32 over the PT day, so
 *       the same absence always resolves the same). Shields block. A held
 *       defense pays pride (small rep/trophies). A breach costs CAPPED soft
 *       loot (max ~8% gold + a bite of wood/stone/produce -- NEVER gems /
 *       keys / bones), damages buildings via AK_ECON.applyBaseDamage (fortify
 *       mitigates -- already built), downs ONE posted defender to the
 *       Infirmary on a heavy breach, and arms a 24h revenge entry in the
 *       exact p.raid.revenge shape raid.js already consumes.
 *   (4) A capped defense LOG (p.defense.log, 12 entries) + lastReport(p) so
 *       the HUB can pop ONE "while you were gone" report card (p.defense.seenT).
 *
 * STATE SHAPE (this module OWNS it; economy.js ensureShape is FROZEN -- p.defense
 * is lazily created on the first real write, exactly like p.stamina / p.downed /
 * p.guards, so an untouched profile stays byte-identical / zero-state):
 *   p.defense = {
 *     posts: { "0".."3": cardName },       // posted defenders by slot
 *     postsBy: { "0".."3": 'auto'|'manual' }, // who manned the slot (manual survives auto passes;
 *                                          //  a manned slot with NO record reads as manual -- safe)
 *     log: [ { t, rival:{name,clan,color,dogId}, held, pct, lostGold, lostMats, shield } ],
 *     lastResolve: <ms>,                   // resolver stamp (idempotency gate)
 *     seenT: <ms>                          // last time the report card was shown
 *   }
 *
 * HARD LAW honored (every line):
 *   - engine.js / economy.js ensureShape are FROZEN. Every profile write goes
 *     through AK_ECON.mutateProfile, falsy-default, lazily-created p.defense.
 *   - Soft currency ONLY. Losses touch gold(p.coins)/wood/stone/produce.
 *     Gems / keys / bones are never read, granted or spent here.
 *   - Everything typeof-guarded + try/catch: missing AK_POPULATION / AK_ECON /
 *     AK_INFIRMARY / AKGuard degrade to no-op or skip that one effect.
 *   - First-ever run just stamps lastResolve and returns [] -- a brand-new
 *     player is NEVER punished for state that did not exist yet.
 *   - Canon names only (the Watch, The Lot, the four clans). No em-dashes (--).
 *
 * Headless-safe: zero top-level DOM / localStorage; pure logic (the HUB lane
 * draws the UI). Loadable on index.html with zero load-time injection AND in a
 * bare node harness. Plain browser JS.
 */
(function (global) {
  'use strict';

  var ZONE = 'HOME_TURF';                          // the defended district (The Lot)
  var DAY_MS = 24 * 3600000;                        // a real 24h -- revenge windows (mirrors raid.js DAY_MS)

  /* ====================================================================== *
   * TUNABLES -- the ONE table (balance lives here, nowhere else)
   * ====================================================================== */
  var TUNE = {
    POSTS: 4,                                       // defense posts on HOME_TURF
    BASE_SCORE: 100,                                // every block starts with walls of pride
    CARD_SCORE: { Common: 40, Rare: 70, Epic: 110, Legendary: 160, Mythic: 220 },
    CARD_LVL_BONUS: 0.06,                           // +6% of the rarity score per level above 1
    // CLASS FIT -- how well each canon combat role HOLDS A POST (autoAssign
    // multiplier on the rarity/level worth). Bruisers + standing steel anchor
    // the wall; glass roles and healers would rather run than stand.
    CLASS_POST_FIT: {
      Vanguard: 1.5, Structure: 1.5,                // the wall itself
      Striker: 1.25, Lancer: 1.15,                  // hits hard enough to hold
      Controller: 1.0, Skirmisher: 0.9, Blaster: 0.9,
      Spawner: 0.8, Hacker: 0.7, Assassin: 0.7,     // built to raid, not to stand
      Support: 0.6                                  // medics guard nothing
    },
    WALL_HP_DIV: 40,                                // + sum(builds hp) / 40
    FORTIFY_PER_LVL: 60,                            // + fortifyLevel * 60
    WATCH_BONUS: 80,                                // + flat if AKGuard has an active watch
    ATTACK_BASE: 120,                               // attackPower = 120 + trophies*0.35, +-20%
    ATTACK_TROPHY_MULT: 0.35,
    ATTACK_VAR: 0.20,
    DEF_VAR_LO: 0.85, DEF_VAR_HI: 1.15,             // defense factor at resolve time
    MIN_GAP_MS: 8 * 3600000,                        // min 8h between incoming raids
    MAX_PENDING: 2,                                 // cap even after a long absence
    RAID_CHANCE_BASE: 0.55,                         // per-slot fire chance ...
    RAID_CHANCE_TROPHY_DIV: 3000,                   // ... + trophies/3000 (high rank = hotter block)
    RAID_CHANCE_MAX: 0.95,
    LOSS_GOLD_PCT: 0.08,                            // max ~8% of gold on a full (pct=1) breach
    LOSS_MAT_PCT: 0.05,                             // max ~5% of wood/stone/produce
    BREACH_PCT_FLOOR: 0.15,                         // even a close breach stings a little
    HEAVY_BREACH: 0.6,                              // pct >= this downs one posted defender
    BLD_DMG_BASE: 0.25, BLD_DMG_SCALE: 0.5,         // applyBaseDamage per hit building
    HELD_TROPHIES_LO: 2, HELD_TROPHIES_HI: 5,       // pride pay on a held defense
    HELD_REP: 3,
    LOG_CAP: 12
  };

  // fixed post positions spread across HOME_TURF (ZW=1700 x ZH=1300 district)
  var POST_XY = [
    { x: 430,  y: 400 },
    { x: 1270, y: 400 },
    { x: 430,  y: 920 },
    { x: 1270, y: 920 }
  ];

  var SEED = 0xB10CBA55;                            // "block bass" -- stable module seed

  /* ====================================================================== *
   * DETERMINISTIC RNG + PT DAY (population.js idiom, byte-for-byte)
   * ====================================================================== */
  function mulberry32(a) {
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function ptCal(ms) {
    try {
      var f = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit',
        day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      }), o = {};
      f.formatToParts(new Date(ms || Date.now())).forEach(function (p) { if (p.type !== 'literal') o[p.type] = p.value; });
      var h = +o.hour; if (h === 24) h = 0;
      return { y: +o.year, m: +o.month, d: +o.day, h: h };
    } catch (_) {
      var n = new Date(ms || Date.now());
      return { y: n.getFullYear(), m: n.getMonth() + 1, d: n.getDate(), h: n.getHours() };
    }
  }
  function ptDayIndex(ms) { var c = ptCal(ms); return Math.floor(Date.UTC(c.y, c.m - 1, c.d) / 86400000); }
  // per-(PT day, raid slot) deterministic stream -- the SAME absence resolves the SAME
  function raidRng(dayIdx, salt) {
    var s = (SEED ^ Math.imul(dayIdx | 0, 2654435761) ^ Math.imul((salt | 0) + 1, 40503)) >>> 0;
    return mulberry32(s);
  }

  /* ====================================================================== *
   * GUARDED NEIGHBOR READS (every miss degrades, never throws)
   * ====================================================================== */
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function freshProfile() { try { var e = econ(); return (e && e.loadProfile) ? e.loadProfile() : null; } catch (_) { return null; } }
  function clampN(v, lo, hi) { v = +v; if (!isFinite(v)) v = lo; return Math.max(lo, Math.min(hi, v)); }

  // ---- guarded ak-raid caller (mirrors raid.js; offline / signed-out degrade) ----
  // Used ONLY to consume the server revenge inbox so a REAL rival who raided your
  // published base shows up in the "while you were gone" report instead of a ghost.
  // No client / no session -> Promise.resolve({ok:false}); the ghost sim stands alone.
  function sbClient() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function signedInDef() { try { return !!(global.AKAccount && global.AKAccount.user && global.AKAccount.user()); } catch (_) { return false; } }
  function callAkRaidFn(body) {
    var sb = sbClient();
    if (!sb || !sb.functions || !sb.functions.invoke) return Promise.resolve({ ok: false, error: 'offline' });
    try {
      return sb.functions.invoke('ak-raid', { body: body }).then(function (r) {
        if (r && r.error) return { ok: false, error: 'error' };
        return (r && r.data) || { ok: false, error: 'empty' };
      }, function () { return { ok: false, error: 'neterr' }; });
    } catch (_) { return Promise.resolve({ ok: false, error: 'throw' }); }
  }
  // fire 'ak-defense-change' so raid.js re-publishes the base with the owner's real
  // posted defenders the moment they assign / clear a post. Fully guarded (no DOM = no-op).
  function emitDefenseChange() {
    try { if (typeof global.dispatchEvent === 'function' && typeof CustomEvent === 'function') global.dispatchEvent(new CustomEvent('ak-defense-change')); } catch (_) {}
  }

  var _rarMap = null, _roleMap = null;
  function buildCanonMaps() {
    _rarMap = {}; _roleMap = {};
    var L = global.CANON_CARDS || [];
    for (var i = 0; i < L.length; i++) if (L[i] && L[i].name) {
      _rarMap[L[i].name] = L[i].rarity || 'Common';
      _roleMap[L[i].name] = L[i].role || '';
    }
  }
  function rarityOf(name) {
    if (!name) return 'Common';
    try { var ctx = global.AK_CTX, c = ctx && ctx.cards && ctx.cards()[name]; if (c && c.rarity) return c.rarity; } catch (_) {}
    try {
      if (!_rarMap) buildCanonMaps();
      return _rarMap[name] || 'Common';
    } catch (_) { return 'Common'; }
  }
  // canon combat role (Vanguard / Structure / Striker / ...) -- feeds CLASS_POST_FIT
  function roleOf(name) {
    if (!name) return '';
    try { var ctx = global.AK_CTX, c = ctx && ctx.cards && ctx.cards()[name]; if (c && c.role) return c.role; } catch (_) {}
    try {
      if (!_roleMap) buildCanonMaps();
      return _roleMap[name] || '';
    } catch (_) { return ''; }
  }
  function cardLevelOf(p, name) {
    try { var e = econ(); if (e && e.cardLevel) return e.cardLevel(p, name) | 0; } catch (_) {}
    var v = p && p.cardLvls && p.cardLvls[name];
    return Math.max(1, Math.min(10, Math.floor(v || 1)));
  }
  function ownedNames(p) { return (p && Array.isArray(p.owned)) ? p.owned : []; }
  function isOwned(p, name) { return ownedNames(p).indexOf(name) >= 0; }
  function fortifyLevelOf(p) {
    try { if (global.AK_BUILDMODE && global.AK_BUILDMODE.fortifyLevel) return global.AK_BUILDMODE.fortifyLevel(ZONE) | 0; } catch (_) {}
    try { var e = econ(); if (e && e.buildingFortify) return e.buildingFortify(p, ZONE) | 0; } catch (_) {}
    return (p && p.fortify && (p.fortify[ZONE] | 0)) || 0;
  }
  function watchActive() {
    try {
      var g = global.AKGuard;
      if (g && g.defendersFor) { var d = g.defendersFor(ZONE); return Array.isArray(d) && d.length > 0; }
    } catch (_) {}
    return false;
  }
  // the ACTIVE 11-card deck (game.html saveProfile mirrors DBPROFILE.decks flat
  // to localStorage 'ak_decks' + 'ak_active' -- same source activeDeckNames()
  // reads). Guarded: no localStorage (bare harness) => null => owned fallback.
  function deckNames() {
    try {
      var ls = (typeof localStorage !== 'undefined') ? localStorage : null;
      if (!ls) return null;
      var raw = ls.getItem('ak_decks'); if (!raw) return null;
      var decks = JSON.parse(raw);
      var ai = parseInt(ls.getItem('ak_active') || '0', 10) || 0;
      var d = decks && decks[ai];
      if (d && Array.isArray(d.cards) && d.cards.length) return d.cards.slice();
    } catch (_) {}
    return null;
  }
  // {name:true} of every dog still healing (a corpse never mans a post).
  // AK_INFIRMARY.downedSet(p) when loaded; falls back to a raw p.downed read.
  function downedSetOf(p) {
    try {
      var inf = global.AK_INFIRMARY;
      if (inf && inf.downedSet) { var s = inf.downedSet(p); if (s && typeof s === 'object') return s; }
    } catch (_) {}
    var out = {};
    try {
      var m = p && p.downed, t = Date.now();
      if (m && typeof m === 'object') for (var k in m) { if (m.hasOwnProperty(k) && m[k] && t < (m[k].healAt || 0)) out[k] = true; }
    } catch (_) {}
    return out;
  }

  /* ====================================================================== *
   * DEFENSE POSTS (p.defense.posts = { "0".."3": cardName }; lazy)
   * ====================================================================== */
  function postsOf(p) { var d = p && p.defense; return (d && d.posts && typeof d.posts === 'object') ? d.posts : {}; }
  function ensureDefense(p) {
    if (!p.defense || typeof p.defense !== 'object') p.defense = {};
    if (!p.defense.posts || typeof p.defense.posts !== 'object') p.defense.posts = {};
    if (!Array.isArray(p.defense.log)) p.defense.log = [];
    return p.defense;
  }
  function postsByOf(p) { var d = p && p.defense; return (d && d.postsBy && typeof d.postsBy === 'object') ? d.postsBy : {}; }
  // how well a dog holds a post: CLASS FIT x rarity score x level bonus
  function postFitOf(name) {
    var f = TUNE.CLASS_POST_FIT[roleOf(name)];
    return (typeof f === 'number' && isFinite(f)) ? f : 1;
  }
  function postWorth(p, name) {
    var base = TUNE.CARD_SCORE[rarityOf(name)] || TUNE.CARD_SCORE.Common;
    return postFitOf(name) * base * (1 + TUNE.CARD_LVL_BONUS * (cardLevelOf(p, name) - 1));
  }
  // computeFills(p) -> [{slot,cardName}] the auto pass WOULD write. PURE. Rules:
  //   - a slot is OPEN when it is effectively unmanned: never touched, its dog
  //     was traded away (unowned), or an AUTO-posted dog is down in the Infirmary
  //   - a manned MANUAL slot is never touched, even when its dog is down
  //   - a manual CLEAR (record 'manual', NO stored name) stays empty -- the
  //     operator's strategic call; a dead manual pick (name stored but unowned)
  //     reopens, because that assignment cannot stand anyway
  //   - candidates: active 11-deck FIRST (best fit x worth), strongest owned as
  //     the tail pool; downed dogs and dogs already on a post are skipped
  function computeFills(p) {
    var map = postsOf(p), by = postsByOf(p), down = downedSetOf(p);
    var open = [], manning = {}, s, raw, nm, who;
    for (s = 0; s < TUNE.POSTS; s++) {
      raw = map[s] || map[String(s)] || null;
      nm = raw;
      if (nm && !isOwned(p, nm)) nm = null;                     // a traded-away dog left the post
      who = by[String(s)] || by[s] || (raw ? 'manual' : null);  // manned + no record = manual (legacy-safe)
      if (nm && who === 'auto' && down[nm]) nm = null;          // a downed AUTO dog frees its post
      if (nm) manning[nm] = true;
      else if (!(who === 'manual' && !raw)) open.push(s);       // only a hand-cleared post stays empty
    }
    if (!open.length) return [];
    var deckPool = [], ownPool = [], seen = {};
    function take(pool) {
      return function (n) {
        if (!n || seen[n] || manning[n] || down[n] || !isOwned(p, n)) return;
        seen[n] = true; pool.push(n);
      };
    }
    (deckNames() || []).forEach(take(deckPool));                // the built 11-deck leads
    ownedNames(p).forEach(take(ownPool));                       // strongest owned backs it up
    var byWorth = function (a, b) { return postWorth(p, b) - postWorth(p, a); };
    deckPool.sort(byWorth); ownPool.sort(byWorth);
    var pool = deckPool.concat(ownPool), fills = [];
    for (var i = 0; i < open.length && i < pool.length; i++) fills.push({ slot: open[i], cardName: pool[i] });
    return fills;
  }
  // autoAssign(p?) -> { ok, filled:[{slot,cardName}], profile? }. Mans every open
  // post from the deck (best CLASS FIT first). NEVER overwrites a manual slot.
  // Zero writes when nothing to fill -- safe to call lazily on every posts() read.
  function autoAssign(p) {
    p = p || freshProfile();
    if (!p) return { ok: false, error: 'NO_PROFILE', filled: [] };
    if (!computeFills(p).length) return { ok: true, filled: [] };   // fully manned (or no dogs) -- no write
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON', filled: [] };
    var filled = [], fresh = null;
    try {
      fresh = e.mutateProfile(function (q) {
        var fills = computeFills(q);                            // recompute on the atomic read
        if (!fills.length) return;
        var d = ensureDefense(q);
        if (!d.postsBy || typeof d.postsBy !== 'object') d.postsBy = {};
        fills.forEach(function (f) {
          delete d.posts[f.slot];                               // clear any numeric-key ghost
          d.posts[String(f.slot)] = f.cardName;
          d.postsBy[String(f.slot)] = 'auto';
          filled.push({ slot: f.slot, cardName: f.cardName });
        });
      });
    } catch (_) { return { ok: false, error: 'FAIL', filled: [] }; }
    return { ok: true, filled: filled, profile: fresh || null };
  }
  // posts(p) -> the 4 HOME_TURF defense posts (cardName null when unmanned).
  // LAZY SELF-MANNING: any open post pulls the best-fit deck dog the moment
  // anything reads the wall (first run, and after a downed dog frees a slot).
  function posts(p) {
    p = p || freshProfile();
    try {
      var aa = autoAssign(p);
      if (aa && aa.ok && aa.filled.length && aa.profile) p = aa.profile;
    } catch (_) {}
    var map = postsOf(p), out = [];
    for (var s = 0; s < TUNE.POSTS; s++) {
      var nm = map[s] || map[String(s)] || null;
      if (nm && !isOwned(p, nm)) nm = null;          // an unowned name never mans a post
      out.push({ slot: s, cardName: nm, x: POST_XY[s].x, y: POST_XY[s].y });
    }
    return out;
  }
  // assign(slot, cardName): OWNED cards only; a card holds ONE post (moves, never dupes)
  function assign(slot, cardName) {
    slot = slot | 0;
    if (slot < 0 || slot >= TUNE.POSTS) return { ok: false, error: 'BAD_SLOT' };
    if (!cardName) return { ok: false, error: 'NO_CARD' };
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    var out = { ok: false, error: 'FAIL' };
    try {
      e.mutateProfile(function (p) {
        if (!isOwned(p, cardName)) { out = { ok: false, error: 'NOT_OWNED' }; return; }
        var d = ensureDefense(p);
        if (!d.postsBy || typeof d.postsBy !== 'object') d.postsBy = {};
        for (var s = 0; s < TUNE.POSTS; s++)          // one dog, one post
          if (d.posts[s] === cardName || d.posts[String(s)] === cardName) {
            delete d.posts[s]; delete d.posts[String(s)];
            delete d.postsBy[s]; delete d.postsBy[String(s)];
          }
        d.posts[String(slot)] = cardName;
        d.postsBy[String(slot)] = 'manual';           // the operator's pick -- auto never touches it
        out = { ok: true, slot: slot, cardName: cardName };
      });
    } catch (_) {}
    if (out && out.ok) emitDefenseChange();            // re-publish the base with the new defender
    return out;
  }
  function clear(slot) {
    slot = slot | 0;
    if (slot < 0 || slot >= TUNE.POSTS) return { ok: false, error: 'BAD_SLOT' };
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    var out = { ok: false, error: 'FAIL' };
    try {
      e.mutateProfile(function (p) {
        var d = ensureDefense(p);
        delete d.posts[slot]; delete d.posts[String(slot)];
        if (!d.postsBy || typeof d.postsBy !== 'object') d.postsBy = {};
        d.postsBy[String(slot)] = 'manual';           // cleared BY HAND stays empty (strategy call)
        out = { ok: true, slot: slot };
      });
    } catch (_) {}
    if (out && out.ok) emitDefenseChange();            // re-publish the base with the post cleared
    return out;
  }

  /* ====================================================================== *
   * DEFENSE SCORE (pure read -- 60fps-safe when a profile is passed)
   * ====================================================================== */
  function defenseScore(p) {
    p = p || freshProfile();
    var score = TUNE.BASE_SCORE;
    try {
      // posted dogs: rarity weight scaled by level (a Lv10 Mythic anchors the block)
      var ps = posts(p);
      for (var i = 0; i < ps.length; i++) {
        var nm = ps[i].cardName; if (!nm) continue;
        var base = TUNE.CARD_SCORE[rarityOf(nm)] || TUNE.CARD_SCORE.Common;
        score += base * (1 + TUNE.CARD_LVL_BONUS * (cardLevelOf(p, nm) - 1));
      }
    } catch (_) {}
    try {
      // standing walls/structures (buildmode) -- hp is the defense that counts
      var builds = (p && Array.isArray(p.builds)) ? p.builds : [], hpSum = 0;
      for (var b = 0; b < builds.length; b++) {
        var bd = builds[b]; if (!bd) continue;
        if (bd.zone && bd.zone !== ZONE) continue;    // only what stands on the home block
        hpSum += Math.max(0, bd.hp | 0);
      }
      score += hpSum / TUNE.WALL_HP_DIV;
    } catch (_) {}
    try { score += fortifyLevelOf(p) * TUNE.FORTIFY_PER_LVL; } catch (_) {}
    try { if (watchActive()) score += TUNE.WATCH_BONUS; } catch (_) {}
    return Math.round(score);
  }

  /* ====================================================================== *
   * THE OFFLINE RAID RESOLVER
   * ====================================================================== */
  function rivalPool() {
    try {
      var pop = global.AK_POPULATION;
      var r = pop && pop.roster && pop.roster();
      if (Array.isArray(r) && r.length) return r;
    } catch (_) {}
    // no population module: ONE colorless fallback so the block still lives
    return [{ id: 'stray_0', name: 'A Stray', clan: 'stray', clanName: 'Stray', color: '#c9a84c', trophies: 220 }];
  }
  function pickRival(rng, myTrophies) {
    var pool = rivalPool().slice();
    pool.sort(function (a, b) {                       // trophy proximity -- rivals in your weight class
      return Math.abs((a.trophies | 0) - myTrophies) - Math.abs((b.trophies | 0) - myTrophies);
    });
    var near = pool.slice(0, Math.min(6, pool.length));
    return near[(rng() * near.length) | 0] || pool[0];
  }
  function tierFor(trophies) { trophies = trophies | 0; return trophies >= 1800 ? 3 : trophies >= 500 ? 2 : 1; }

  /* ====================================================================== *
   * REAL ATTACKERS IN THE REPORT (fold ak_raid_revenge -> the "LAST NIGHT" log)
   * defense.js was 100% offline: every "while you were gone" hit was a ghost. The
   * seam is ak_raid_revenge -- when a REAL player raids your PUBLISHED base, the
   * server arms a 24h revenge row (attacker_name / faction / tier). foldRealRevenge
   * turns any real:true revenge already in p.raid.revenge into a defense-log entry
   * the report card surfaces (held:false, real:true); foldServerRevenge pulls FRESH
   * ones off ak-raid {action:'revenge'} first. Both are guarded + idempotent (dedup
   * by the revenge id). Signed-out / empty inbox -> the ghost sim stands alone.
   * ====================================================================== */
  // SYNC: fold real:true p.raid.revenge entries into p.defense.log (dedup by srev).
  // Race-safe with raid.js's war-map pull -- whoever drained the server stored them
  // locally; this surfaces them in the report regardless of who pulled first.
  function foldRealRevenge(now) {
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    var e = econ(); if (!e || !e.mutateProfile) return [];
    var added = [];
    try {
      e.mutateProfile(function (q) {
        var rev = (q.raid && Array.isArray(q.raid.revenge)) ? q.raid.revenge : [];
        var reals = [];
        for (var i = 0; i < rev.length; i++) { var x = rev[i]; if (x && x.real && (now - (x.at || 0)) < DAY_MS) reals.push(x); }
        if (!reals.length) return;
        var d = ensureDefense(q);
        var seen = {};
        for (var j = 0; j < d.log.length; j++) { var en0 = d.log[j]; if (en0 && en0.srev != null) seen[String(en0.srev)] = 1; }
        reals.forEach(function (rv) {
          var key = (rv.id != null) ? String(rv.id) : ('srv_' + (rv.at || 0));
          if (seen[key]) return; seen[key] = 1;
          var en = { t: rv.at || now, srev: key, real: true, held: false, pct: 0, lostGold: 0, lostMats: null, shield: false,
            rival: { name: rv.name || 'A Rival Crew', clan: rv.faction || 'stray', color: '#e46a6a', dogId: null } };
          d.log.push(en); added.push(en);
        });
        while (d.log.length > TUNE.LOG_CAP) d.log.shift();
      });
    } catch (_) {}
    return added;
  }
  // ASYNC: pull the FRESH server revenge inbox, store into p.raid.revenge (real:true,
  // dedup), then fold into the report. Guarded: signed-out / no client -> [] (ghost sim only).
  function foldServerRevenge(now) {
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    if (!signedInDef() || !sbClient()) return Promise.resolve([]);   // signed-out == today's ghost-only report
    var e = econ(); if (!e || !e.mutateProfile) return Promise.resolve([]);
    return callAkRaidFn({ action: 'revenge' }).then(function (r) {
      if (!(r && r.ok && Array.isArray(r.revenge) && r.revenge.length)) return [];
      try {
        e.mutateProfile(function (q) {
          if (!q.raid || typeof q.raid !== 'object') q.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] };
          if (!Array.isArray(q.raid.revenge)) q.raid.revenge = [];
          var seen = {};
          for (var i = 0; i < q.raid.revenge.length; i++) { var x = q.raid.revenge[i]; if (x && x.id != null) seen[String(x.id)] = 1; }
          r.revenge.forEach(function (rv) {
            if (!rv) return;
            var rid = (rv.id != null) ? String(rv.id) : ('srv_' + (rv.at || 0));
            if (seen[rid]) return; seen[rid] = 1;
            q.raid.revenge.push({ id: rid, name: rv.name || 'Rival Crew', faction: rv.faction || 'boneguard_crew', tier: rv.tier || 2, at: rv.at || now, real: true });
          });
        });
      } catch (_) {}
      return foldRealRevenge(now);   // surface the freshly-stored real attackers in the report
    }, function () { return []; });
  }

  // resolveIncoming(p?, now?) -> new log entries (may be []). Idempotent: stamps
  // p.defense.lastResolve; re-running inside the 8h window adds NOTHING. First-ever
  // run just stamps and returns [] (a brand-new player is never punished).
  function resolveIncoming(p, now) {
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    var e = econ(); if (!e || !e.mutateProfile) return [];
    p = p || freshProfile(); if (!p) return [];

    // REAL attackers first: fold any real revenge already stored (sync, cheap, dedup)
    // and kick a FRESH server pull (async, fire-and-forget, guarded). These land in
    // p.defense.log so lastReport() surfaces a REAL rival raid alongside the ghost sim.
    // Both no-op when signed-out / empty -- the ghost resolver below is untouched.
    try { foldRealRevenge(now); } catch (_) {}
    try { foldServerRevenge(now); } catch (_) {}

    var last = (p.defense && +p.defense.lastResolve) || 0;
    if (!last) {                                      // FIRST-EVER: stamp, never punish
      try { e.mutateProfile(function (q) { ensureDefense(q).lastResolve = now; }); } catch (_) {}
      return [];
    }
    var elapsed = now - last;
    if (elapsed < TUNE.MIN_GAP_MS) return [];         // idempotency gate (< 8h = quiet)

    var pending = Math.min(TUNE.MAX_PENDING, Math.floor(elapsed / TUNE.MIN_GAP_MS));
    var myTrophies = (p.trophies | 0);
    var chance = clampN(TUNE.RAID_CHANCE_BASE + myTrophies / TUNE.RAID_CHANCE_TROPHY_DIV, TUNE.RAID_CHANCE_BASE, TUNE.RAID_CHANCE_MAX);
    var defScore = defenseScore(p);
    var shieldUntil = (p.raid && +p.raid.shieldUntil) || 0;
    var dayIdx = ptDayIndex(now);

    // ---- pre-compute every hit OUTSIDE the mutate (mutate = pure state stamp) ----
    var hits = [], sideFx = [];                       // sideFx = post-mutate guarded calls
    for (var i = 0; i < pending; i++) {
      var rng = raidRng(dayIdx, i);
      if (rng() >= chance) continue;                  // a quiet slot -- nobody tried the block
      var raidTime = Math.min(now, last + (i + 1) * TUNE.MIN_GAP_MS);
      var rival = pickRival(rng, myTrophies);
      var entry = {
        t: raidTime,
        rival: { name: rival.name || 'A Stray', clan: rival.clan || 'stray', color: rival.color || '#c9a84c', dogId: rival.id || null },
        held: true, pct: 0, lostGold: 0, lostMats: null, shield: false
      };
      if (shieldUntil > raidTime) {                   // SHIELD CHECK first -- attack blocked
        entry.shield = true;
        hits.push({ entry: entry });
        continue;
      }
      var atk = (TUNE.ATTACK_BASE + (rival.trophies | 0) * TUNE.ATTACK_TROPHY_MULT) *
                (1 - TUNE.ATTACK_VAR + rng() * TUNE.ATTACK_VAR * 2);
      var defEff = defScore * (TUNE.DEF_VAR_LO + rng() * (TUNE.DEF_VAR_HI - TUNE.DEF_VAR_LO));
      if (defEff >= atk) {                            // DEFENSE HELD -- pay pride
        var gain = TUNE.HELD_TROPHIES_LO + Math.floor(rng() * (TUNE.HELD_TROPHIES_HI - TUNE.HELD_TROPHIES_LO + 1));
        hits.push({ entry: entry, trophyGain: gain, rep: TUNE.HELD_REP });
      } else {                                        // BREACHED -- capped soft losses
        var ratio = (atk - defEff) / Math.max(1, atk);
        var pct = clampN(TUNE.BREACH_PCT_FLOOR + ratio * 1.2, TUNE.BREACH_PCT_FLOOR, 1);
        entry.held = false; entry.pct = Math.round(pct * 100) / 100;
        var hit = { entry: entry, pct: pct, raidTime: raidTime, rival: rival };
        // 1-2 producer buildings take fortify-mitigated damage (economy owns the math)
        var bldIds = ['MINT', 'FORGE', 'LAB', 'GEN'];
        var nB = 1 + ((rng() < pct) ? 1 : 0), dmgMap = {}, start = (rng() * bldIds.length) | 0;
        for (var b = 0; b < nB; b++) dmgMap[bldIds[(start + b) % bldIds.length]] = clampN(TUNE.BLD_DMG_BASE + pct * TUNE.BLD_DMG_SCALE, 0, 1);
        hit.dmgMap = dmgMap;
        // heavy breach: ONE posted defender goes down to the Infirmary
        if (pct >= TUNE.HEAVY_BREACH) {
          var manned = posts(p).filter(function (q) { return !!q.cardName; });
          if (manned.length) hit.downName = manned[(rng() * manned.length) | 0].cardName;
        }
        hits.push(hit);
      }
    }

    // ---- ONE atomic profile write: stamp + losses + log + revenge -------------
    var report = [];
    try {
      e.mutateProfile(function (q) {
        var d = ensureDefense(q);
        d.lastResolve = now;
        hits.forEach(function (h) {
          var en = h.entry;
          if (!en.held) {
            // capped soft-currency losses -- NEVER gems / keys / bones
            var lostGold = Math.floor(Math.max(0, q.coins | 0) * TUNE.LOSS_GOLD_PCT * h.pct);
            var mats = {}, kinds = ['wood', 'stone', 'produce'];
            for (var k = 0; k < kinds.length; k++) {
              var kn = kinds[k], lose = Math.floor(Math.max(0, q[kn] | 0) * TUNE.LOSS_MAT_PCT * h.pct);
              if (lose > 0) { q[kn] = (q[kn] | 0) - lose; mats[kn] = lose; }
            }
            if (lostGold > 0) q.coins = (q.coins | 0) - lostGold;
            en.lostGold = lostGold; en.lostMats = mats;
            // arm revenge -- the exact shape raid.js drawRevengeList consumes
            if (!q.raid || typeof q.raid !== 'object') q.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] };
            if (!Array.isArray(q.raid.revenge)) q.raid.revenge = [];
            q.raid.revenge.push({ id: 'def_' + en.t, name: (h.rival && h.rival.name ? h.rival.name + "'s crew" : 'Rival Crew'), faction: en.rival.clan, tier: tierFor(h.rival && h.rival.trophies), at: en.t });
          } else if (!en.shield && h.trophyGain) {
            q.trophies = (q.trophies | 0) + h.trophyGain;   // pride pay for a held block
          }
          d.log.push(en);
          report.push(en);
        });
        while (d.log.length > TUNE.LOG_CAP) d.log.shift();
      });
    } catch (_) { return []; }

    // ---- guarded side effects (each owns its own atomic write) ----------------
    hits.forEach(function (h) {
      if (h.dmgMap) { try { if (e.applyBaseDamage) e.applyBaseDamage(h.dmgMap); } catch (_) {} }
      if (h.downName) { try { if (global.AK_INFIRMARY && global.AK_INFIRMARY.downCard) global.AK_INFIRMARY.downCard(h.downName); } catch (_) {} }
      if (h.rep) { try { if (e.addRep) e.addRep(h.rep); } catch (_) {} }
    });
    return report;
  }

  /* ====================================================================== *
   * LOG READS + the report card gate
   * ====================================================================== */
  function log(p) {
    p = p || freshProfile();
    var L = (p && p.defense && Array.isArray(p.defense.log)) ? p.defense.log : [];
    return L.slice().reverse();                       // newest-first
  }
  function lastReport(p) {
    p = p || freshProfile();
    var seen = (p && p.defense && +p.defense.seenT) || 0;
    return log(p).filter(function (en) { return en && (+en.t || 0) > seen; });
  }
  // the HUB calls this the moment the report card is shown (stamps p.defense.seenT)
  function markSeen(now) {
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    try { e.mutateProfile(function (q) { ensureDefense(q).seenT = now; }); return { ok: true, seenT: now }; } catch (_) { return { ok: false, error: 'FAIL' }; }
  }

  /* ====================================================================== *
   * AK-BASESTATS 2026-07-18: PER-BUILDING STATS (the meters nobody could see)
   * The operator stood in his own Lot and saw no health bar and no attack
   * number. The numbers were not missing, they were never EXPOSED: every one
   * already existed behind a call the hub never made. Provenance, honestly:
   *   hp  -> AK_ECON.buildingDamage(p,id,now): the live 0..1 raid damage that
   *          decays to 0 over REBUILD_HOURS. Zone facades carry NO absolute hp
   *          pool anywhere in this tree (index.html B(id,label,col,x,y,w,h,
   *          url,act) has no hp field), so a facade meter is a PERCENT of that
   *          real fraction (hpUnit 'pct', hpReal false). PLACED structures
   *          (p.builds from buildmode, {type,x,y,hp,maxHp,zone,t}) do carry a
   *          real pool, so those report hpUnit 'hp', hpReal true.
   *   atk -> buildings have NO attack data in this codebase (the only turrets
   *          are card lore). Per-building atk is 0 with atkReal false rather
   *          than a back-filled guess. The block's REAL attack is the posted
   *          roster's dmg from AK_RAIDPARAMS.defenders(p, cardsByName, params),
   *          the SAME call the attacker's wave planner makes (raidwaves.js),
   *          reading the SAME p.defense.posts this module owns.
   *   def -> the points that building actually adds to defenseScore. Facades
   *          add ZERO: defenseScore folds only p.builds hp + p.fortify[ZONE].
   *          Per-building fortify (p.fortify[id], what applyBaseDamage reads)
   *          never reaches defenseScore, so it is reported as mitigation.
   * ZERO new balance constants: every figure reads an existing export. Poll it
   * on the HUD chip cadence; posts() self-mans, so never call this per frame.
   * ====================================================================== */
  var _cbnMap = null;
  function cardsByName() {
    if (_cbnMap) return _cbnMap;
    var m = {};
    try { var L = global.CANON_CARDS || []; for (var i = 0; i < L.length; i++) if (L[i] && L[i].name) m[L[i].name] = L[i]; } catch (_) {}
    _cbnMap = m; return m;
  }
  // the REAL facade list for the home block (index.html owns ZONES; AK_CTX exposes it)
  function zoneBuildings() {
    try { var ctx = global.AK_CTX, Z = ctx && ctx.ZONES && ctx.ZONES[ZONE];
      if (Z && Array.isArray(Z.buildings)) return Z.buildings; } catch (_) {}
    return [];
  }
  // placed structures standing on the home block (walls / barricades carry real hp)
  function structuresOf(p) {
    var out = [];
    try {
      var b = (p && Array.isArray(p.builds)) ? p.builds : [];
      for (var i = 0; i < b.length; i++) { var s = b[i]; if (!s) continue; if (s.zone && s.zone !== ZONE) continue; out.push(s); }
    } catch (_) {}
    return out;
  }
  // the DEFENDING ROSTER: watcher + lieutenants with REAL hp/dmg, from raidparams
  function rosterOf(p) {
    try {
      var rp = global.AK_RAIDPARAMS; if (!rp || !rp.defenders) return [];
      var cbn = cardsByName(), params = rp.calculate ? rp.calculate(p, cbn) : null;
      var r = rp.defenders(p, cbn, params);
      return Array.isArray(r) ? r : [];
    } catch (_) { return []; }
  }
  function bldLevelOf(p, id) {
    try { var e = econ(); if (e && e.buildingLevel) return e.buildingLevel(p, id) | 0; } catch (_) {}
    try { var lv = global.AK_CTX && global.AK_CTX.buildingLevels; if (lv && lv[id]) return lv[id] | 0; } catch (_) {}
    return 1;
  }
  function bldDamageOf(p, id, now) {
    try { var e = econ(); if (e && e.buildingDamage) return clampN(e.buildingDamage(p, id, now), 0, 1); } catch (_) {}
    return 0;
  }
  function bldFortifyOf(p, id) {
    try { var e = econ(); if (e && e.buildingFortify) return e.buildingFortify(p, id) | 0; } catch (_) {}
    return (p && p.fortify && (p.fortify[id] | 0)) || 0;
  }
  // buildingStats(id, p?, now?) -> one building's real numbers, or ok:false when
  // the id stands on no zone facade and matches no placed structure type.
  //   { ok, id, label, zone, kind, lvl, hp, maxHp, hpUnit, hpReal, dmg, integrity,
  //     atk, atkReal, atkNote, def, defReal, fortify, mitigation, count,
  //     watcher, lieutenants, rosterScope, repairGold }
  function buildingStats(id, p, now) {
    id = String(id == null ? '' : id);
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    p = p || freshProfile();
    var out = { ok: false, id: id, label: id, zone: ZONE, kind: null, lvl: 1,
      hp: 0, maxHp: 0, hpUnit: 'pct', hpReal: false, dmg: 0, integrity: 1,
      atk: 0, atkReal: false, atkNote: 'NO_BUILDING_ATTACK_DATA',
      def: 0, defReal: true, fortify: 0, mitigation: 0, count: 0,
      watcher: null, lieutenants: [], rosterScope: 'base', repairGold: 0, repairable: false };
    if (!p || !id) return out;
    // the whole block answers any wave, so every building reports the base roster
    try {
      var ros = rosterOf(p);
      for (var r = 0; r < ros.length; r++) {
        if (ros[r] && ros[r].role === 'watcher') out.watcher = ros[r];
        else if (ros[r]) out.lieutenants.push(ros[r]);
      }
    } catch (_) {}
    // 1) a placed STRUCTURE type (WALL / STONE / METAL / BARRICADE): REAL hp pool
    var st = structuresOf(p), hpSum = 0, maxSum = 0, n = 0;
    for (var i = 0; i < st.length; i++) {
      if (String(st[i].type) !== id) continue;
      n++; hpSum += Math.max(0, st[i].hp | 0); maxSum += Math.max(0, st[i].maxHp | 0);
    }
    if (n > 0) {
      out.ok = true; out.kind = 'structure'; out.count = n;
      out.hp = hpSum; out.maxHp = maxSum; out.hpUnit = 'hp'; out.hpReal = true;
      out.integrity = maxSum > 0 ? clampN(hpSum / maxSum, 0, 1) : 1;
      out.dmg = Math.round((1 - out.integrity) * 100) / 100;
      out.def = Math.round((hpSum / TUNE.WALL_HP_DIV) * 10) / 10;   // exactly how defenseScore folds it
      return out;
    }
    // 2) a zone FACADE (ARENA / TROPHY / KENNEL / INFIRMARY / MINT / ...): no hp
    //    pool exists, so the meter is a percent of the REAL decayed damage.
    var list = zoneBuildings(), hit = null;
    for (var b = 0; b < list.length; b++) if (list[b] && String(list[b].id) === id) { hit = list[b]; break; }
    if (!hit && !(p.prod && p.prod[id]) && !(p.baseDmg && p.baseDmg[id])) return out;
    out.ok = true; out.kind = 'facade'; out.count = 1;
    out.label = (hit && hit.label) || id;
    out.lvl = bldLevelOf(p, id);
    out.dmg = bldDamageOf(p, id, now);
    out.integrity = clampN(1 - out.dmg, 0, 1);
    out.hp = Math.round(out.integrity * 100); out.maxHp = 100;   // PERCENT view, not an hp pool
    out.fortify = bldFortifyOf(p, id);
    out.mitigation = Math.min(0.75, out.fortify * 0.15);         // applyBaseDamage's real absorb
    out.def = 0; // a facade adds nothing to defenseScore -- stated, not invented
    // repairQuote returns { damaged, damage, cost } -- gold to fix it NOW (else 6h rebuild)
    try { var e = econ(); if (e && e.repairQuote) { var q = e.repairQuote(p, id, now);
      if (q) { out.repairGold = q.cost | 0; out.repairable = !!q.damaged; } } } catch (_) {}
    return out;
  }
  // baseSummary(p?, now?) -> the whole block in one read, for a HUD panel.
  //   { defenseScore, wallHp, wallMaxHp, defenderHp, totalHp, atk, atkReal,
  //     posted, postsMax, fortify, watch, integrity, watcher, lieutenants,
  //     buildings:[buildingStats], weakest }
  function baseSummary(p, now) {
    now = (typeof now === 'number' && isFinite(now)) ? now : Date.now();
    p = p || freshProfile();
    var out = { defenseScore: 0, wallHp: 0, wallMaxHp: 0, defenderHp: 0, totalHp: 0,
      atk: 0, atkReal: false, posted: 0, postsMax: TUNE.POSTS, fortify: 0, watch: false,
      integrity: 1, watcher: null, lieutenants: [], buildings: [], weakest: null };
    if (!p) return out;
    try { out.defenseScore = defenseScore(p); } catch (_) {}
    try { var ps = posts(p); for (var i = 0; i < ps.length; i++) if (ps[i] && ps[i].cardName) out.posted++; } catch (_) {}
    try { out.fortify = fortifyLevelOf(p); } catch (_) {}
    try { out.watch = watchActive(); } catch (_) {}
    // REAL wall pool (the same p.builds hp defenseScore divides by WALL_HP_DIV)
    var st = structuresOf(p), types = {};
    for (var s = 0; s < st.length; s++) {
      out.wallHp += Math.max(0, st[s].hp | 0); out.wallMaxHp += Math.max(0, st[s].maxHp | 0);
      types[String(st[s].type)] = 1;
    }
    // REAL roster hp + dmg (raidparams, the attacker's own numbers)
    try {
      var ros = rosterOf(p);
      for (var r = 0; r < ros.length; r++) {
        var u = ros[r]; if (!u) continue;
        out.defenderHp += (u.hp | 0); out.atk += (u.dmg | 0);
        if (u.role === 'watcher') out.watcher = u; else out.lieutenants.push(u);
      }
      if (ros.length) out.atkReal = true;
    } catch (_) {}
    out.totalHp = out.wallHp + out.defenderHp;
    try { var e = econ(); if (e && e.baseIntact) out.integrity = clampN(e.baseIntact(p, now), 0, 1); } catch (_) {}
    // every facade on the block, then every placed structure type
    var list = zoneBuildings(), k;
    for (k = 0; k < list.length; k++) {
      if (!list[k] || !list[k].id) continue;
      var bs = buildingStats(list[k].id, p, now); if (bs.ok) out.buildings.push(bs);
    }
    for (k in types) { if (!types.hasOwnProperty(k)) continue;
      var ss = buildingStats(k, p, now); if (ss.ok) out.buildings.push(ss); }
    for (k = 0; k < out.buildings.length; k++) {
      var c = out.buildings[k];
      if (!out.weakest || c.integrity < out.weakest.integrity) out.weakest = c;
    }
    return out;
  }

  /* ====================================================================== *
   * PUBLIC API -- the BLOCK-WAR CONTRACT (index.html consumes, typeof-guarded)
   * ====================================================================== */
  try {
    global.AK_DEFENSE = {
      TUNE: TUNE,                       // the balance table (read-only by convention)
      posts: posts,                     // (p?) -> [{slot,cardName|null,x,y}] x4 on HOME_TURF (lazily self-mans open posts)
      assign: assign,                   // (slot, cardName) -> post an OWNED dog by hand (one post per dog; auto never touches it)
      clear: clear,                     // (slot) -> pull the dog off the post BY HAND (stays empty until reassigned)
      autoAssign: autoAssign,           // (p?) -> man every open post from the 11-deck by CLASS FIT (manual slots untouched)
      defenseScore: defenseScore,       // (p?) -> the block's ONE defense number (pure read)
      buildingStats: buildingStats,     // AK-BASESTATS (id,p?,now?) -> {ok,kind,hp,maxHp,hpUnit,hpReal,dmg,integrity,atk,atkReal,def,fortify,mitigation,watcher,lieutenants}
      baseSummary: baseSummary,         // AK-BASESTATS (p?,now?) -> {defenseScore,wallHp,defenderHp,totalHp,atk,posted,watcher,lieutenants,buildings,weakest}
      resolveIncoming: resolveIncoming, // (p?, now?) -> settle offline raids (idempotent) + fold real attackers
      foldServerRevenge: foldServerRevenge, // (now?) -> pull ak-raid revenge inbox, fold REAL attackers into the report
      foldRealRevenge: foldRealRevenge, // (now?) -> fold real:true p.raid.revenge into the report (sync, dedup)
      log: log,                         // (p?) -> defense log, newest-first (cap 12)
      lastReport: lastReport,           // (p?) -> entries since the report card was last shown
      markSeen: markSeen                // (now?) -> stamp p.defense.seenT after showing the card
    };
  } catch (_) {}

})(typeof window !== 'undefined' ? window : globalThis);
