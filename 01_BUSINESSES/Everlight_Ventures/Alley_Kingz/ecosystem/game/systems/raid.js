/* game/systems/raid.js -- AK_SYSTEMS "raid" wave (Wave 4).
 * ---------------------------------------------------------------------------
 * CLIENT side of RAID + BASE DEFENSE. Grounded in AK_MASTER_GAME_DESIGN_SYNTHESIS
 * (Clash of Clans raid + shield economy, Whiteout night-siege, Boom Beach
 * snapshot-as-bot async bases). Self-contained AK_SYSTEMS module: it edits NO
 * shared host file -- everything rides window.AK_CTX + window.AK_ECON.
 *
 * RESPONSIBILITY (all client, theme-consistent, real):
 *   - "rival crew scout" roamer drives through your zone (day). Walk into it ->
 *     the WAR MAP overlay opens (Boom Beach map-of-bases).
 *   - WAR MAP: snapshot-as-bot rival base PINS (real cards BY NAME), per-base
 *     surgical-building intel, RAID launches the battler with mode:"raid"
 *     (base layout = battlefield), the 5-tier SHIELD ladder, and a revenge list.
 *   - NIGHT DEFENSE: at night a siege beacon spawns on THE LOT; walk into it ->
 *     a flow-field horde of stray mutant cards rushes your core. Tap to fend
 *     them off; CALL CREW pulls reinforcements (ak-crew). PvE, capped rewards.
 *   - 5-tier shield UI (Street / Crew / Iron Curtain / Fortress Dome / Panic) --
 *     gold OR gems ONLY, never ALK/$BCARDD. Gold tiers settle client-side; gem
 *     tiers route to the server (gems are server-only).
 *
 * HARD LAW honored: 2.5D Canvas2D only (overlay = a fresh layer, the battler is
 * never forked); soft-currency + cosmetic loot only; gems server-only; reuse the
 * 106 cards + factions BY NAME; "crew" never "clan"; all new state is the single
 * falsy-default `raid:{}` field via AK_ECON. Headless-safe (bails with no
 * AK_SYSTEMS; every storage touch goes through AK_ECON's try/catch kernel).
 *
 * SERVER (LIVE -- edge fn `ak-raid` is deployed on project mfghdobptredxxhbjwyz):
 *   serves REAL players' published bases first + bot-base snapshots (`targets`),
 *   upserts the caller's own base (`publish-base`), settles + caps raid loot and
 *   pushes 24h revenge rows (`resolve`), drains the revenge inbox (`revenge`), sells
 *   gem shields (`buy-shield`), validates crew reinforcements (`reinforce`). Loot is
 *   delivered through the live `ak_grants` pattern (same as ak-crew donations ->
 *   AKSocial.claimGrants). Every server call degrades gracefully offline/signed-out.
 * ========================================================================== */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;            // hub-only; safe on game.html / node harness

  var ID = 'raid';
  var HOUR_MS = 3600 * 1000;
  var DAY_MS = 24 * HOUR_MS;
  // Accelerated day/night so a session sees both (Whiteout heartbeat, not wall-clock).
  var CYCLE_MS = 6 * 60 * 1000;              // full day+night = 6 real minutes
  var NIGHT_FRAC = 0.34;                      // last ~2 min of each cycle = night
  var GOLD = '#c9a84c', GOLD_HI = '#e8c55a';

  // ---- the 5-tier shield ladder (CoC choice-architecture). gold OR gems ONLY.
  // gems>0 tiers are SERVER-settled (gems are server-only); gold tiers settle here.
  var SHIELDS = [
    { id: 'street',   name: 'Street Cover',  hrs: 2,  gold: 300,  gems: 0,   glyph: 'X', icon: 'assets/icons/def_street.png',   line: 'Lookouts on the corner. 2 hours of quiet.' },
    { id: 'crew',     name: 'Crew Watch',    hrs: 8,  gold: 1200, gems: 0,   glyph: 'W', icon: 'assets/icons/def_crew.png',     line: 'The crew posts a watch. 8 hours safe.' },
    { id: 'iron',     name: 'Iron Curtain',  hrs: 12, gold: 2600, gems: 0,   glyph: 'I', icon: 'assets/icons/def_iron.png',     line: 'Roll the gates down. A full workday of peace.' },
    { id: 'fortress', name: 'Fortress Dome', hrs: 16, gold: 0,    gems: 80,  glyph: 'D', icon: 'assets/icons/def_fortress.png', line: 'Dome the whole block. 16 hours. Gems only.' },
    { id: 'panic',    name: 'Panic Button',  hrs: 24, gold: 0,    gems: 160, glyph: 'P', icon: 'assets/icons/def_panic.png',    line: 'Vacation lockout. 24 hours untouchable. Gems only.' }
  ];

  // ---- the 4 crews/factions (crew, NEVER clan) + real-card pools BY NAME -----
  // Fallback pools are real cards from data/cards.json; live resolution prefers
  // ctx.cards() filtered by class so a card rename can never desync.
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

  // the 5 producer buildings a base loses level on when raided (CoC surgical dmg)
  var BLD = [
    { id: 'GEM', name: 'Gem Mine' }, { id: 'MINT', name: 'Gold Mint' }, { id: 'FORGE', name: 'Card Forge' },
    { id: 'LAB', name: 'Research Lab' }, { id: 'GEN', name: 'Generator' }
  ];

  // ---- module-local runtime (never persisted) --------------------------------
  var M = { wasNight: false, scout: null, scoutTimer: 18, beacon: null, opening: false, booted: false, published: false, lastPublish: 0 };

  // ==========================================================================
  // helpers
  // ==========================================================================
  function now() { return Date.now(); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function profile(ctx) { try { return ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function raidOf(p) { return (p && p.raid) || { shieldUntil: 0, lastRaid: 0, revenge: [] }; }
  function shieldActive(p) { return raidOf(p).shieldUntil > now(); }

  // deterministic PRNG (mulberry32) so bot bases are stable within a window
  function rng32(seed) { var s = seed >>> 0; return function () { s |= 0; s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  function fmtDur(ms) {
    if (ms <= 0) return '0m';
    var h = Math.floor(ms / HOUR_MS), m = Math.floor((ms % HOUR_MS) / 60000);
    return (h ? h + 'h ' : '') + m + 'm';
  }
  // accelerated day/night phase (0..1); >= 1-NIGHT_FRAC = night
  function dayPhase() { return (now() % CYCLE_MS) / CYCLE_MS; }
  function isNight() { return dayPhase() >= (1 - NIGHT_FRAC); }

  // resolve a card name -> engine cardNumber (for nemesis fielding); null if unknown
  function cardNum(ctx, name) { try { var c = ctx.cards()[name]; return (c && (c.cardNumber || c.id)) || null; } catch (_) { return null; } }
  // a real, owned-or-canon name exists in the live card table?
  function liveName(ctx, name) { try { return !!ctx.cards()[name]; } catch (_) { return true; } }

  // pick a base roster (4 real names) weighted up by tier; prefers live cards
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

  // generate the bot-base snapshot list (local fallback for ak-raid: targets)
  function genTargets(ctx) {
    var windowId = Math.floor(now() / (CYCLE_MS * 2));    // rotate every ~12 min
    var r = rng32((windowId * 2654435761) >>> 0);
    var out = [];
    for (var i = 0; i < 3; i++) {
      var f = FACTIONS[Math.floor(r() * FACTIONS.length)];
      var tier = 1 + Math.floor(r() * 3);
      var gang = f.gangs[Math.floor(r() * f.gangs.length)];
      var roster = pickRoster(ctx, f, tier, r);
      var blds = BLD.map(function (b) { return { id: b.id, name: b.name, lvl: clamp(tier + Math.floor(r() * 3), 1, 10) }; });
      out.push({
        id: 'bot_' + windowId + '_' + i, name: gang, faction: f.id, cls: f.cls, accent: f.accent,
        tier: tier, trophies: 280 + tier * 210 + Math.floor(r() * 160),
        roster: roster, buildings: blds,
        loot: { gold: 110 * tier + Math.floor(r() * 90), scrap: tier >= 2 ? 2 * tier : 0, scrapR: tier >= 3 ? 'Epic' : 'Rare' },
        city: clamp(tier + 1, 0, 9), level: clamp(2 + tier * 2, 1, 10), diffOffset: tier - 1
      });
    }
    return out;
  }

  // a base's marquee defender -> a fielded nemesis blob (engine AK-NEMESIS) | null
  function nemesisFor(ctx, base) {
    var marquee = base.roster && base.roster[0];
    var num = marquee && cardNum(ctx, marquee);
    if (!num) return null;
    return { card: String(num), name: marquee, title: base.name, tier: base.tier, taunt: 'You picked the wrong block, mutt.' };
  }

  // ---- server caller (mirrors social.js call(); degrades to offline) ---------
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function callAkRaid(body) {
    var sb = sbc();
    if (!sb) return Promise.resolve({ ok: false, error: 'offline' });
    // edge fn `ak-raid` is LIVE/deployed (project mfghdobptredxxhbjwyz): targets /
    // publish-base / resolve / revenge / buy-shield / reinforce / claim-grants. When
    // signed-out or the network fails, sbc() is null (handled above) or the invoke
    // rejects -> every caller degrades to its offline/local fallback.
    return sb.functions.invoke('ak-raid', { body: body }).then(function (r) {
      if (r.error) return { ok: false, error: (r.error && r.error.message) || 'error' };
      return r.data || { ok: false, error: 'empty' };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }
  function signedIn() { try { return !!(global.AKAccount && global.AKAccount.user && global.AKAccount.user()); } catch (_) { return false; } }

  // PUBLISH the player's OWN base snapshot to ak-raid so REAL rivals can raid it.
  // Sends the cheap, non-PII fields the player has on hand: trophies + the 5
  // producer-building levels (from p.prod) + a derived tier + THE REAL DEFENSE the
  // owner actually posted -- roster = the 4 posted defenders (AK_DEFENSE.posts, canon
  // card names, no PII) and def_score = AK_DEFENSE.defenseScore. So a raided real base
  // fights back with the owner's OWN dogs, not a server-auto roster. The SERVER still
  // picks the canon crew name + caps soft-currency loot (a tampered client can't
  // inflate its bounty). AK_DEFENSE absent (bare page / not loaded) -> roster:[] +
  // def_score:0 and the server auto-staffs exactly as before. Throttled to once /
  // 10 min per session; signed-in only (a bot fallback covers signed-out players).
  function publishMyBase(ctx) {
    try {
      if (!sbc() || !signedIn()) return;
      var t = now(); if (M.lastPublish && (t - M.lastPublish) < 10 * 60 * 1000) return;
      var p = profile(ctx); if (!p) return;
      var prod = p.prod || {};
      var buildings = BLD.map(function (b) { var e = prod[b.id]; return { id: b.id, name: b.name, lvl: clamp((e && e.lvl) | 0 || 1, 1, 10) }; });
      var tr = (p.trophies | 0) || 0;
      var tier = tr >= 1200 ? 3 : tr >= 600 ? 2 : 1;
      // the REAL posted defenders + block defense number (guarded -- AK_DEFENSE may be absent)
      var roster = [], defScore = 0;
      try {
        if (global.AK_DEFENSE) {
          if (AK_DEFENSE.posts) roster = (AK_DEFENSE.posts(p) || []).map(function (q) { return q && q.cardName; }).filter(Boolean);
          if (AK_DEFENSE.defenseScore) defScore = AK_DEFENSE.defenseScore(p) | 0;
        }
      } catch (_d) { roster = []; defScore = 0; }
      M.lastPublish = t;
      callAkRaid({ action: 'publish-base', trophies: tr, tier: tier, buildings: buildings, roster: roster, def_score: defScore }).then(function (r) {
        if (r && r.ok && r.published) M.published = true;
        else M.lastPublish = 0;       // let a later attempt retry if the publish failed
      });
    } catch (_) {}
  }

  // ==========================================================================
  // shield economy
  // ==========================================================================
  function setShield(ctx, untilMs) {
    if (!ctx.econ) return;
    ctx.econ.mutateProfile(function (p) {
      if (!p.raid || typeof p.raid !== 'object') p.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] };
      // never SHORTEN an active shield (CoC: a longer shield replaces, a shorter is refused)
      p.raid.shieldUntil = Math.max(p.raid.shieldUntil | 0, untilMs);
    });
  }
  function buyShield(ctx, tier) {
    var p = profile(ctx); if (!p) return;
    var cur = raidOf(p).shieldUntil;
    var nextUntil = Math.max(cur, now()) + tier.hrs * HOUR_MS;
    if (tier.gold > 0) {
      var gold = ctx.currency.get('gold');
      if (gold < tier.gold) { ctx.showBanner('Need ' + tier.gold + ' gold (have ' + gold + ')', 1.8); return false; }
      ctx.currency.grant('gold', -tier.gold);          // soft-currency deduction (atomic, clamped >=0)
      setShield(ctx, nextUntil);
      ctx.showBanner(tier.name + ' up -- safe for ' + tier.hrs + 'h', 2.0);
      return true;
    }
    // gem tier: gems are SERVER-ONLY -> route to ak-raid (TODO-SERVER), degrade today.
    callAkRaid({ action: 'buy-shield', tier: tier.id }).then(function (r) {
      if (r && r.ok && r.shieldUntil) { setShield(ctx, r.shieldUntil); ctx.showBanner(tier.name + ' raised!', 1.8); }
      else ctx.showBanner('Gem shields unlock with the server -- coming soon.', 2.0);
    });
    return false;
  }

  // ==========================================================================
  // raid launch (NEVER forks the battler -- mode:"raid" rides AK.newMatch)
  // ==========================================================================
  function launchRaid(ctx, base, isRevenge) {
    if (ctx.econ) ctx.econ.mutateProfile(function (p) { if (!p.raid) p.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] }; p.raid.lastRaid = now(); });
    // WALK-TO-RAID: route through the SCOUT / walk-on scene when present so the
    // raider WALKS the enemy block (their walls/buildings/core, laid out) before
    // the hit. AK_RAIDSCENE.enrich attaches a real procedural layout/coreHp/reward
    // to the war-map bot, then launch() seeds the battler from target.layout
    // (mode:'raid'). The match still pays the live chest/loot path on top of reward.
    if (global.AK_RAIDSCENE && global.AK_RAIDSCENE.launch) {
      var target = global.AK_RAIDSCENE.enrich ? global.AK_RAIDSCENE.enrich(base, ctx) : base;
      // stamp the server base id + revenge flag so modes.js's raid win can settle
      // loot SERVER-AUTHORITATIVELY via ak-raid {action:'resolve'} (the client +50%
      // below is the OFFLINE fallback only; the server applies its own +50%).
      if (target) { if (base.id) target.id = base.id; target._revenge = !!isRevenge; }
      if (isRevenge && target && target.reward) {                 // revenge = +50% loot (24h revenge bonus)
        var rw = target.reward;
        ['gold', 'scrap', 'wood', 'stone', 'metal'].forEach(function (k) { if (rw[k]) rw[k] = Math.round(rw[k] * 1.5); });
      }
      global.AK_RAIDSCENE.launch(target, ctx);
      return;
    }
    // fallback (raidscene not loaded): straight into the battler (legacy path).
    // Seed the handoff ourselves so modes.js can still resolve loot server-side
    // (the frozen ctx.battle.launch only forwards mode/city/level/nemesis).
    try {
      base._revenge = !!isRevenge;
      global.AK_RAID_TARGET = base;
      if (typeof localStorage !== 'undefined') localStorage.setItem('ak_raid_target', JSON.stringify(base));
    } catch (_e) {}
    ctx.battle.launch({
      mode: 'raid', city: base.city, level: base.level, diffOffset: base.diffOffset,
      nemesis: nemesisFor(ctx, base),
      label: (isRevenge ? 'REVENGE -- ' : 'RAID -- ') + base.name
    });
  }

  // ==========================================================================
  // shared canvas-UI helpers (immediate-mode buttons for the overlays)
  // ==========================================================================
  function roundRect(g, x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function txt(g, s, x, y, font, color, align) { g.save(); g.font = font; g.fillStyle = color; g.textAlign = align || 'left'; g.textBaseline = 'alphabetic'; g.fillText(s, x, y); g.restore(); }
  function button(g, ui, x, y, w, h, label, cb, opts) {
    opts = opts || {}; var dis = !!opts.disabled, prim = opts.primary !== false;
    g.save(); roundRect(g, x, y, w, h, 10);
    if (dis) { g.fillStyle = 'rgba(255,255,255,0.05)'; g.fill(); }
    else if (prim) { var grd = g.createLinearGradient(0, y, 0, y + h); grd.addColorStop(0, GOLD_HI); grd.addColorStop(1, GOLD); g.fillStyle = grd; g.fill(); }
    else { g.fillStyle = 'rgba(201,168,76,0.10)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,0.5)'; g.lineWidth = 1.2; g.stroke(); }
    g.fillStyle = dis ? 'rgba(210,200,170,0.45)' : (prim ? '#15110a' : '#d8c98a');
    g.font = '800 ' + (opts.fs || 14) + 'px system-ui,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(label, x + w / 2, y + h / 2 + 1); g.restore();
    if (!dis && cb) ui.push({ x: x, y: y, w: w, h: h, cb: cb });
  }
  function hitUI(ui, px, py) { for (var i = ui.length - 1; i >= 0; i--) { var b = ui[i]; if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) return b.cb; } return null; }
  function stars(n) { var s = ''; for (var i = 0; i < 3; i++) s += i < n ? '*' : '.'; return '[' + s + ']'; }
  function panelBg(g, w, h) {
    g.fillStyle = '#08080c'; g.fillRect(0, 0, w, h);
    var grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, 'rgba(201,168,76,0.06)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd; g.fillRect(0, 0, w, h);
  }
  // AK-DEEMOJI: cached canvas icon loader -- draw the PNG when loaded, else the letter glyph.
  // Cached by path so onFrame never allocates a new Image (60fps-safe); a 404 marks the
  // path dead (null) so callers fall straight back to the bracketed letter.
  var _icoCache = {};
  function icoImg(path) {
    if (!path || typeof Image === 'undefined') return null;
    if (_icoCache.hasOwnProperty(path)) return _icoCache[path];
    var im = new Image(); _icoCache[path] = im;
    im.onerror = function () { _icoCache[path] = null; };
    im.src = path;
    return im;
  }

  // ==========================================================================
  // OVERLAY 1 -- THE WAR MAP (raid targets / shield / revenge)
  // ==========================================================================
  function openWarMap(ctx) {
    var view = 'raid';                     // 'raid' | 'shield' | 'revenge' | 'intel'
    var targets = genTargets(ctx);         // local procedural fallback; server refresh below
    var intelBase = null, ui = [];
    // make sure my base is published so others can hit it (cheap, throttled, signed-in only)
    try { publishMyBase(ctx); } catch (_e) {}
    // prefer the LIVE server snapshot: REAL players' bases lead, bots backfill.
    callAkRaid({ action: 'targets' }).then(function (r) { if (r && r.ok && Array.isArray(r.bases) && r.bases.length) targets = r.bases; });
    // pull any server-pushed 24h revenge entries into the local revenge list. Each is
    // stamped real:true so defense.js folds it into the "while you were gone" report
    // (a REAL rival hit your block, not a ghost). The ak-raid revenge action DRAINS the
    // inbox server-side, so this stores them locally once; defense.js reads the same
    // p.raid.revenge, race-safe (whoever pulls first stores, both fold from local).
    if (sbc() && signedIn()) callAkRaid({ action: 'revenge' }).then(function (r) {
      if (r && r.ok && Array.isArray(r.revenge) && r.revenge.length && ctx.econ) {
        ctx.econ.mutateProfile(function (p) {
          if (!p.raid || typeof p.raid !== 'object') p.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] };
          if (!Array.isArray(p.raid.revenge)) p.raid.revenge = [];
          var seen = {}; p.raid.revenge.forEach(function (e) { if (e && e.id) seen[e.id] = 1; });
          r.revenge.forEach(function (e) { if (e && (!e.id || !seen[e.id])) { e.real = true; p.raid.revenge.push(e); } });
        });
      }
    });

    ctx.overlay.open({
      id: 'raid_warmap',
      onPointer: function (evt, api) {
        if (evt.type !== 'pointerdown') return;
        var cb = hitUI(ui, evt.clientX, evt.clientY);
        if (cb) cb(api);
      },
      onClose: function (res) {
        if (res && res.then === 'raid' && res.base) launchRaid(ctx, res.base, !!res.revenge);
      },
      onFrame: function (g, dt, vp, api) {
        ui.length = 0; var W = vp.w, H = vp.h, pad = 16;
        panelBg(g, W, H);
        var p = profile(ctx);
        // header
        txt(g, 'WAR MAP', pad, 40, '900 22px system-ui', GOLD_HI);
        txt(g, 'pick a block to hit', pad, 60, '600 12px system-ui', '#8a8a96');
        // shield status strip
        var sa = shieldActive(p);
        txt(g, sa ? ('SHIELDED  ' + fmtDur(raidOf(p).shieldUntil - now())) : 'EXPOSED -- no shield up', W - pad, 40, '800 13px system-ui', sa ? '#7CFFB0' : '#f3a0a0', 'right');
        // tabs
        var tabW = (W - pad * 2 - 16) / 3, tabY = 76;
        button(g, ui, pad, tabY, tabW, 34, 'RAID', function () { view = 'raid'; }, { primary: view === 'raid', fs: 12 });
        button(g, ui, pad + tabW + 8, tabY, tabW, 34, 'SHIELD', function () { view = 'shield'; }, { primary: view === 'shield', fs: 12 });
        button(g, ui, pad + (tabW + 8) * 2, tabY, tabW, 34, 'REVENGE', function () { view = 'revenge'; }, { primary: view === 'revenge', fs: 12 });

        var y0 = 128;
        if (view === 'raid') drawRaidList(g, ui, W, H, pad, y0, p, sa, api);
        else if (view === 'shield') drawShieldList(g, ui, W, H, pad, y0, p);
        else if (view === 'revenge') drawRevengeList(g, ui, W, H, pad, y0, p, api);
        else if (view === 'intel') drawIntel(g, ui, W, H, pad, y0, intelBase, p, sa, api);

        // close
        button(g, ui, W - pad - 96, H - 50, 96, 38, 'LEAVE', function () { api.close(); }, { primary: false, fs: 13 });
      }
    });

    function drawRaidList(g, ui, W, H, pad, y, p, sa, api) {
      var rowH = 96;
      targets.forEach(function (b, i) {
        var ry = y + i * (rowH + 12), rx = pad, rw = W - pad * 2;
        g.save(); roundRect(g, rx, ry, rw, rowH, 14); g.fillStyle = 'rgba(255,255,255,0.04)'; g.fill();
        g.strokeStyle = b.accent + '66'; g.lineWidth = 1.2; g.stroke(); g.restore();
        txt(g, b.name, rx + 14, ry + 26, '800 16px system-ui', '#fff');
        txt(g, (FAC_BY_ID[b.faction] ? FAC_BY_ID[b.faction].cls : b.cls) + '  -  ' + b.trophies + ' tr', rx + 14, ry + 45, '600 11px system-ui', '#9a9aa6');
        txt(g, stars(b.tier), rx + 14, ry + 66, '700 14px system-ui', GOLD_HI);
        var lootStr = 'loot ' + b.loot.gold + (b.loot.scrap ? '  +' + b.loot.scrap + ' ' + b.loot.scrapR + ' scrap' : '');
        txt(g, lootStr, rx + 80, ry + 66, '700 12px system-ui', '#d8c98a');
        button(g, ui, rx + rw - 196, ry + 30, 88, 38, 'SCOUT', function () { intelBase = b; view = 'intel'; }, { primary: false, fs: 12 });
        button(g, ui, rx + rw - 100, ry + 30, 88, 38, 'RAID', function () { api.close({ then: 'raid', base: b }); }, { primary: true, fs: 13 });
      });
      txt(g, 'snapshot-as-bot -- every defender is a real card', pad, y + targets.length * (rowH + 12) + 18, '500 11px system-ui', '#6a6a76');
    }

    function drawIntel(g, ui, W, H, pad, y, b, p, sa, api) {
      if (!b) { view = 'raid'; return; }
      txt(g, b.name, pad, y, '800 18px system-ui', '#fff');
      txt(g, 'SCOUT REPORT -- surgical targets', pad, y + 20, '600 12px system-ui', '#9a9aa6');
      // roster (real cards BY NAME)
      txt(g, 'DEFENDERS', pad, y + 50, '800 12px system-ui', GOLD);
      txt(g, b.roster.join('  -  '), pad, y + 70, '600 12px system-ui', '#cfcfd6');
      // surgical building damage display (CoC: each building independent level)
      txt(g, 'BUILDINGS (a raid drops each a level)', pad, y + 102, '800 12px system-ui', GOLD);
      b.buildings.forEach(function (bl, i) {
        var by = y + 118 + i * 30, bw = W - pad * 2;
        txt(g, bl.name, pad, by + 16, '600 12px system-ui', '#cfcfd6');
        var barX = pad + 130, barW = bw - 200;
        g.save(); roundRect(g, barX, by + 4, barW, 14, 7); g.fillStyle = 'rgba(255,255,255,0.06)'; g.fill();
        roundRect(g, barX, by + 4, barW * (bl.lvl / 10), 14, 7); g.fillStyle = b.accent; g.fill(); g.restore();
        txt(g, 'Lv ' + bl.lvl + ' to ' + (bl.lvl - 1), pad + bw - 70, by + 16, '700 11px system-ui', '#d8c98a', 'left');
      });
      button(g, ui, pad, H - 50, 96, 38, 'BACK', function () { view = 'raid'; }, { primary: false, fs: 13 });
      button(g, ui, pad + 108, H - 50, 150, 38, 'RAID THIS BLOCK', function () { api.close({ then: 'raid', base: b }); }, { primary: true, fs: 12 });
    }

    function drawShieldList(g, ui, W, H, pad, y, p) {
      txt(g, 'BUY PEACE', pad, y, '800 16px system-ui', '#fff');
      txt(g, 'gold OR gems only -- a longer shield replaces a shorter one', pad, y + 18, '600 11px system-ui', '#9a9aa6');
      var rowH = 56;
      SHIELDS.forEach(function (s, i) {
        var ry = y + 36 + i * (rowH + 8), rx = pad, rw = W - pad * 2;
        g.save(); roundRect(g, rx, ry, rw, rowH, 12); g.fillStyle = 'rgba(255,255,255,0.04)'; g.fill(); g.restore();
        // AK-DEEMOJI: PNG icon when painted, else the bracketed letter glyph (graceful fallback)
        var im = icoImg(s.icon);
        if (im && im.complete && im.naturalWidth > 0) {
          var isz = 22; g.save(); try { g.drawImage(im, rx + 12, ry + 6, isz, isz); } catch (_e) {} g.restore();
          txt(g, s.name, rx + 12 + isz + 8, ry + 22, '800 14px system-ui', '#fff');
        } else {
          txt(g, '[' + s.glyph + ']  ' + s.name, rx + 12, ry + 22, '800 14px system-ui', '#fff');
        }
        txt(g, s.line, rx + 12, ry + 42, '500 10px system-ui', '#8a8a96');
        var cost = s.gold ? (s.gold + ' gold') : (s.gems + ' gems');
        button(g, ui, rx + rw - 122, ry + 11, 110, 34, cost, function (api) { buyShield(ctx, s); }, { primary: !!s.gold, fs: 12 });
      });
    }

    function drawRevengeList(g, ui, W, H, pad, y, p, api) {
      txt(g, 'REVENGE LIST', pad, y, '800 16px system-ui', '#fff');
      var rev = (raidOf(p).revenge || []).filter(function (e) { return (now() - (e.at || 0)) < DAY_MS; });
      if (!rev.length) {
        txt(g, 'Nobody has hit your block. Stay shielded and they never will.', pad, y + 30, '600 12px system-ui', '#9a9aa6');
        txt(g, '(server pushes a 24h revenge entry when you get raided offline)', pad, y + 50, '500 10px system-ui', '#6a6a76');
        return;
      }
      // LIVE: real attackers arrive two ways -- ak-raid {action:'revenge'} (a REAL
      // rival raided your published base; pulled above + folded by defense.js, real:true)
      // and defense.js resolveIncoming (the offline ghost sim arms {name,faction,tier,at}).
      var rowH = 64;
      rev.forEach(function (e, i) {
        var ry = y + 24 + i * (rowH + 8), rx = pad, rw = W - pad * 2;
        var f = FAC_BY_ID[e.faction] || FACTIONS[0];
        g.save(); roundRect(g, rx, ry, rw, rowH, 12); g.fillStyle = 'rgba(220,80,80,0.10)'; g.fill(); g.strokeStyle = 'rgba(220,80,80,0.35)'; g.lineWidth = 1; g.stroke(); g.restore();
        txt(g, e.name || 'Unknown crew', rx + 12, ry + 24, '800 14px system-ui', '#f3c0c0');
        txt(g, 'hit you ' + fmtDur(now() - (e.at || 0)) + ' ago  -  +50% loot', rx + 12, ry + 44, '600 11px system-ui', '#cfa0a0');
        button(g, ui, rx + rw - 110, ry + 14, 98, 36, 'REVENGE', function () {
          var base = { id: 'rev_' + i, name: e.name || 'Rival Crew', faction: e.faction, cls: f.cls, accent: f.accent, tier: e.tier || 2, trophies: 0, roster: pickRoster(ctx, f, e.tier || 2, rng32(i + 7)), buildings: BLD.map(function (b) { return { id: b.id, name: b.name, lvl: e.tier || 2 }; }), loot: { gold: 0 }, city: clamp((e.tier || 2) + 1, 0, 9), level: clamp(2 + (e.tier || 2) * 2, 1, 10), diffOffset: (e.tier || 2) - 1 };
          api.close({ then: 'raid', base: base, revenge: true });
        }, { primary: true, fs: 12 });
      });
    }
  }

  // ==========================================================================
  // OVERLAY 2 -- NIGHT DEFENSE (flow-field stray horde vs your core)
  // ==========================================================================
  function strayPool(ctx) {
    var bag = [];
    FACTIONS.forEach(function (f) { ['Common', 'Rare'].forEach(function (r) { (f.pool[r] || []).forEach(function (n) { if (liveName(ctx, n)) bag.push({ name: n, rare: r === 'Rare' }); }); }); });
    if (!bag.length) bag = [{ name: 'Tank Pug', rare: false }, { name: 'Neon Whippet', rare: false }];
    return bag;
  }
  function openNightDefense(ctx) {
    var pool = strayPool(ctx);
    var ui = [];
    var st = {
      core: { hp: 100, max: 100 }, wave: 0, waves: 3, spawnLeft: 0, spawnT: 0,
      strays: [], allies: [], fx: [], kills: 0, score: 0, over: false, win: false, reinforced: false, t: 0,
      rewardGold: 0, rewardBones: 0
    };
    function startWave() {
      st.wave++; st.spawnLeft = 4 + st.wave * 3; st.spawnT = 0;
      ctx.showBanner('WAVE ' + st.wave + ' / ' + st.waves, 1.4);
    }
    function spawnStray(W) {
      var pick = pool[Math.floor(Math.random() * pool.length)];
      var hp = (pick.rare ? 5 : 3) + st.wave;
      st.strays.push({ x: 30 + Math.random() * (W - 60), y: -20 - Math.random() * 60, r: pick.rare ? 15 : 12, hp: hp, max: hp, spd: 26 + st.wave * 5 + Math.random() * 16, name: pick.name, rare: pick.rare, dmg: pick.rare ? 9 : 6 });
    }
    function callCrew() {
      if (st.reinforced) { ctx.showBanner('Crew already rolled out.', 1.2); return; }
      st.reinforced = true;
      // TODO-SERVER: ak-crew needs a 'reinforce' action (server validates crew + cooldown,
      // returns how many defenders). For now degrade to local PvE auto-turrets (parity-safe: PvE).
      callAkRaid({ action: 'reinforce' });   // fire-and-forget hook for the future server resolve
      try { if (global.AKAccount && global.AKAccount.user && global.AKAccount.user()) ctx.showBanner('Crew rolls in -- reinforcements!', 1.6); else ctx.showBanner('Solo for now -- sign in + join a crew to call backup.', 1.8); } catch (_) {}
      var n = 2;
      for (var i = 0; i < n; i++) st.allies.push({ ang: (i / n) * Math.PI * 2, cd: 0, x: null, y: null });
    }
    function killStray(s) {
      var i = st.strays.indexOf(s); if (i < 0) return; st.strays.splice(i, 1);
      st.kills++; st.score += s.rare ? 3 : 1; st.fx.push({ x: s.x, y: s.y, t: 0, hit: true });
    }
    function endDefense(win) {
      if (st.over) return; st.over = true; st.win = win;
      if (win) {
        // anti-farm: full reward once per night cycle (capped). Replays still play for fun.
        var nightId = Math.floor(now() / CYCLE_MS);
        var p = profile(ctx); var claimed = p && p.raid && p.raid.defenseNight === nightId;
        st.rewardGold = claimed ? 0 : clamp(st.score * 8 + 40, 0, 300);
        st.rewardBones = claimed ? 0 : clamp(st.kills, 0, 30);
        if (st.rewardGold) ctx.currency.grant('gold', st.rewardGold);
        if (st.rewardBones) ctx.currency.grant('bones', st.rewardBones);
        if (!claimed && ctx.econ) ctx.econ.mutateProfile(function (pp) { if (!pp.raid) pp.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] }; pp.raid.defenseNight = nightId; pp.raid.lastDefenseAt = now(); });
        // AK-DUTYWIRE 2026-07-18: THE WATCH SHIFT. missions.js exposes AKDuties.
        // reportWatchShift (the daily "Stand a Watch shift" + the weekly "Stand 8 Watch
        // shifts" ladders) and it had ZERO call sites repo-wide, so those duties could
        // never be claimed. Holding the Lot through every wave IS the shift you stand --
        // guard.js is a persistent defense LAYOUT with no completion event, this is the
        // only thing in the game a player starts, stands, and finishes. Gated on
        // win === true so RETREAT (which routes through endDefense(false)) and a core
        // wipe never score, on st.over so it fires once per siege and never per frame,
        // and on !claimed so it reuses the SAME once-per-night-cycle anti-farm window
        // the loot already uses -- replaying a night pays nothing and credits nothing.
        // Guarded: a missing AKDuties is a silent no-op, never a throw in the frame.
        if (!claimed) { try { var D = global.AKDuties; if (D && typeof D.reportWatchShift === 'function') D.reportWatchShift(1); } catch (_e) {} }
      }
      // a loss leaves you exposed -- the WAR MAP nudges a shield buy next time.
    }

    ctx.overlay.open({
      id: 'raid_nightdef',
      onPointer: function (evt, api) {
        if (evt.type !== 'pointerdown') return;
        var cb = hitUI(ui, evt.clientX, evt.clientY); if (cb) { cb(api); return; }
        if (st.over) return;
        // a "whack" -- damage the nearest stray within radius of the tap
        var best = null, bd = 46 * 46;
        for (var i = 0; i < st.strays.length; i++) { var s = st.strays[i]; var dx = s.x - evt.clientX, dy = s.y - evt.clientY, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = s; } }
        st.fx.push({ x: evt.clientX, y: evt.clientY, t: 0, hit: !!best });
        if (best) { best.hp -= 3; if (best.hp <= 0) killStray(best); }
      },
      onFrame: function (g, dt, vp, api) {
        ui.length = 0; var W = vp.w, H = vp.h; st.t += dt;
        var coreX = W / 2, coreY = H - 96;
        // bg: night street
        g.fillStyle = '#05060a'; g.fillRect(0, 0, W, H);
        var grd = g.createRadialGradient(coreX, coreY, 20, coreX, coreY, H); grd.addColorStop(0, 'rgba(40,30,10,0.35)'); grd.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = grd; g.fillRect(0, 0, W, H);

        if (!st.over) {
          // wave director
          if (st.wave === 0) startWave();
          if (st.spawnLeft > 0) { st.spawnT -= dt; if (st.spawnT <= 0) { spawnStray(W); st.spawnLeft--; st.spawnT = 0.45 + Math.random() * 0.5; } }
          else if (!st.strays.length) { if (st.wave >= st.waves) endDefense(true); else startWave(); }

          // strays: flow-field toward core + light separation
          for (var i = st.strays.length - 1; i >= 0; i--) {
            var s = st.strays[i];
            var dx = coreX - s.x, dy = coreY - s.y, dist = Math.hypot(dx, dy) || 1;
            var vx = dx / dist, vy = dy / dist;
            for (var j = 0; j < st.strays.length; j++) { if (j === i) continue; var o = st.strays[j]; var sx = s.x - o.x, sy = s.y - o.y, sd = Math.hypot(sx, sy); if (sd > 0 && sd < 26) { vx += (sx / sd) * 0.5; vy += (sy / sd) * 0.5; } }
            var vm = Math.hypot(vx, vy) || 1; s.x += (vx / vm) * s.spd * dt; s.y += (vy / vm) * s.spd * dt;
            if (dist < 30) { st.core.hp -= s.dmg; st.strays.splice(i, 1); st.fx.push({ x: coreX, y: coreY, t: 0, hit: true, big: true }); if (st.core.hp <= 0) { st.core.hp = 0; endDefense(false); } continue; }
          }
          // allies (reinforcements) auto-fire at nearest stray
          st.allies.forEach(function (a) {
            a.cd -= dt; a.ang += dt * 0.6;
            a.x = coreX + Math.cos(a.ang) * 46; a.y = coreY + Math.sin(a.ang) * 46;
            if (a.cd <= 0 && st.strays.length) {
              var tgt = null, td = 1e9; st.strays.forEach(function (s2) { var d = Math.hypot(s2.x - a.x, s2.y - a.y); if (d < td) { td = d; tgt = s2; } });
              if (tgt && td < 260) { tgt.hp -= 2; st.fx.push({ x: tgt.x, y: tgt.y, t: 0, hit: true, ally: true }); if (tgt.hp <= 0) killStray(tgt); a.cd = 0.7; }
            }
          });
        }

        // ---- draw strays ----
        st.strays.forEach(function (s) {
          g.save();
          g.fillStyle = s.rare ? 'rgba(157,139,255,0.22)' : 'rgba(220,80,80,0.18)';
          g.beginPath(); g.arc(s.x, s.y, s.r + 4, 0, 7); g.fill();
          g.fillStyle = s.rare ? '#b6a8ff' : '#e88'; g.beginPath(); g.arc(s.x, s.y, s.r, 0, 7); g.fill();
          g.fillStyle = '#1a1015'; g.font = '700 ' + (s.r) + 'px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('d', s.x, s.y + 1);
          // hp pip
          g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(s.x - s.r, s.y - s.r - 7, s.r * 2, 4);
          g.fillStyle = '#7CFFB0'; g.fillRect(s.x - s.r, s.y - s.r - 7, s.r * 2 * (s.hp / s.max), 4);
          g.restore();
        });
        // ---- core ----
        g.save();
        g.fillStyle = 'rgba(201,168,76,0.16)'; g.beginPath(); g.arc(coreX, coreY, 34, 0, 7); g.fill();
        g.fillStyle = st.over && !st.win ? '#5a2a2a' : GOLD; g.beginPath(); g.arc(coreX, coreY, 26, 0, 7); g.fill();
        g.fillStyle = '#15110a'; g.font = '700 18px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('LOT', coreX, coreY + 1);
        g.restore();
        // allies
        st.allies.forEach(function (a) { if (a.x == null) return; g.save(); g.fillStyle = '#7CFFB0'; g.beginPath(); g.arc(a.x, a.y, 9, 0, 7); g.fill(); g.restore(); });
        // fx
        for (var k = st.fx.length - 1; k >= 0; k--) { var fx = st.fx[k]; fx.t += dt; var fa = 1 - fx.t / 0.3; if (fa <= 0) { st.fx.splice(k, 1); continue; } g.save(); g.globalAlpha = fa; g.strokeStyle = fx.ally ? '#7CFFB0' : (fx.hit ? GOLD_HI : '#888'); g.lineWidth = 3; g.beginPath(); g.arc(fx.x, fx.y, (fx.big ? 30 : 18) * (1 - fa + 0.3), 0, 7); g.stroke(); g.restore(); }

        // ---- HUD ----
        txt(g, 'NIGHT DEFENSE', 16, 34, '900 18px system-ui', GOLD_HI);
        txt(g, st.over ? '' : ('WAVE ' + st.wave + ' / ' + st.waves), 16, 54, '700 13px system-ui', '#cfcfd6');
        // core hp bar
        var bx = W - 16 - 150, bw = 150;
        txt(g, 'THE LOT', bx, 28, '700 11px system-ui', '#9a9aa6');
        g.save(); roundRect(g, bx, 34, bw, 14, 7); g.fillStyle = 'rgba(255,255,255,0.08)'; g.fill(); roundRect(g, bx, 34, bw * (st.core.hp / st.core.max), 14, 7); g.fillStyle = st.core.hp > 40 ? '#7CFFB0' : '#f3a0a0'; g.fill(); g.restore();
        txt(g, 'kills ' + st.kills, bx, 64, '700 11px system-ui', '#d8c98a');

        if (!st.over) {
          button(g, ui, 16, H - 52, 130, 40, st.reinforced ? 'CREW ROLLING' : 'CALL CREW', function () { callCrew(); }, { primary: !st.reinforced, disabled: st.reinforced, fs: 12 });
          button(g, ui, W - 16 - 110, H - 52, 110, 40, 'RETREAT', function (api) { endDefense(false); }, { primary: false, fs: 12 });
        } else {
          // result card
          g.save(); roundRect(g, W / 2 - 150, H / 2 - 80, 300, 160, 16); g.fillStyle = 'rgba(10,10,16,0.94)'; g.fill(); g.strokeStyle = GOLD + '88'; g.lineWidth = 1.4; g.stroke(); g.restore();
          txt(g, st.win ? 'BLOCK HELD' : 'THE LOT GOT HIT', W / 2, H / 2 - 36, '900 20px system-ui', st.win ? '#7CFFB0' : '#f3a0a0', 'center');
          txt(g, st.win ? ('+' + st.rewardGold + ' gold   +' + st.rewardBones + ' bones') : 'Buy a shield before the next raid.', W / 2, H / 2 - 6, '700 13px system-ui', '#d8c98a', 'center');
          txt(g, st.kills + ' strays put down', W / 2, H / 2 + 18, '600 12px system-ui', '#9a9aa6', 'center');
          button(g, ui, W / 2 - 80, H / 2 + 36, 160, 40, 'DONE', function (api) { api.close(); }, { primary: true, fs: 14 });
        }
      }
    });
  }

  // ==========================================================================
  // roamers (Boom Beach scout) + night siege beacon
  // ==========================================================================
  function spawnScout(ctx) {
    if (M.scout || M.opening) return;
    var W = ctx.world.WORLD_W, H = ctx.world.WORLD_H;
    var fromLeft = Math.random() < 0.5;
    var f = FACTIONS[Math.floor(Math.random() * FACTIONS.length)];
    var s = ctx.world.addRoamer({
      id: 'rival_scout_' + now(), zone: ctx.zoneId,
      x: fromLeft ? -30 : W + 30, y: 200 + Math.random() * (H - 400), r: 20,
      vx: (fromLeft ? 1 : -1) * (70 + Math.random() * 40), accent: f.accent, fac: f.cls, life: 34, detected: false,
      update: function (dt, self, c) {
        if (M.opening || c.zoneId !== self.zone) return;
        self.x += self.vx * dt;
        self.detected = c.world.distToMe(self.x, self.y) < 150;
        if (c.world.distToMe(self.x, self.y) < 64) {     // walk into the scout -> WAR MAP
          M.opening = true; c.world.removeRoamer(self); M.scout = null;
          c.showBanner('A rival crew scout flags a block.', 1.4);
          openWarMap(c);
          setTimeout(function () { M.opening = false; M.scoutTimer = 50 + Math.random() * 40; }, 600);
          return;
        }
        if (self.x < -60 || self.x > W + 60) { c.world.removeRoamer(self); M.scout = null; }
      },
      draw: function (g, self, c) {
        var X = c.world.wx(self.x), Y = c.world.wy(self.y);
        g.save();
        g.fillStyle = 'rgba(0,0,0,0.45)'; g.beginPath(); g.ellipse(X, Y + self.r * 0.8, self.r * 1.1, self.r * 0.4, 0, 0, 7); g.fill();
        g.fillStyle = self.accent; g.beginPath(); g.arc(X, Y, self.r, 0, 7); g.fill();
        g.fillStyle = '#10100a'; g.font = '900 14px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('RC', X, Y + 1);
        if (self.detected) { g.fillStyle = GOLD_HI; g.font = '900 18px system-ui'; g.fillText('!', X, Y - self.r - 12); }
        g.fillStyle = 'rgba(232,197,90,0.9)'; g.font = '700 10px system-ui'; g.fillText('SCOUT', X, Y - self.r - 2);
        g.restore();
      }
    });
    M.scout = s;
  }
  function armBeacon(ctx) {
    if (M.beacon) return;
    M.beacon = ctx.world.addRoamer({
      id: 'siege_beacon', zone: 'HOME_TURF', x: ctx.world.WORLD_W / 2, y: ctx.world.WORLD_H / 2 + 120, r: 26, pulse: 0,
      update: function (dt, self, c) {
        if (M.opening || c.zoneId !== 'HOME_TURF') return;
        self.pulse += dt;
        if (c.world.distToMe(self.x, self.y) < 80) {     // walk into the siege -> defend
          M.opening = true; c.showBanner('STRAYS BREACH THE LOT -- defend!', 1.6);
          openNightDefense(c);
          setTimeout(function () { M.opening = false; }, 700);
        }
      },
      draw: function (g, self, c) {
        var X = c.world.wx(self.x), Y = c.world.wy(self.y);
        var pr = 26 + Math.sin(self.pulse * 4) * 6;
        g.save();
        g.strokeStyle = 'rgba(220,70,70,0.8)'; g.lineWidth = 3; g.beginPath(); g.arc(X, Y, pr, 0, 7); g.stroke();
        g.fillStyle = 'rgba(220,70,70,0.18)'; g.beginPath(); g.arc(X, Y, pr, 0, 7); g.fill();
        g.fillStyle = '#f3a0a0'; g.font = '900 18px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('!', X, Y + 1);
        g.fillStyle = '#f3c0c0'; g.font = '800 11px system-ui'; g.fillText('NIGHT SIEGE', X, Y - pr - 6);
        g.restore();
      }
    });
  }
  function disarmBeacon(ctx) { if (M.beacon) { ctx.world.removeRoamer(M.beacon); M.beacon = null; } }

  // ==========================================================================
  // module registration
  // ==========================================================================
  global.AK_SYSTEMS.register({
    id: ID,
    init: function (ctx) {
      if (M.booted) return; M.booted = true;
      // prune stale revenge (>24h) once, on load -- no per-frame work
      if (ctx.econ) ctx.econ.mutateProfile(function (p) {
        if (!p.raid || typeof p.raid !== 'object') return;
        if (Array.isArray(p.raid.revenge)) p.raid.revenge = p.raid.revenge.filter(function (e) { return e && (now() - (e.at || 0)) < DAY_MS; });
      });
      M.wasNight = isNight();
      M.scoutTimer = 20 + Math.random() * 20;
      // PUBLISH my base so REAL rivals can raid it (signed-in only; throttled).
      try { publishMyBase(ctx); } catch (_e) {}
      // re-publish when the player signs in mid-session (base becomes raidable)
      try { global.addEventListener('ak-auth', function (e) { if (e && e.detail && e.detail.user) { M.lastPublish = 0; publishMyBase(ctx); } }); } catch (_e2) {}
      // re-publish on a DEFENSE CHANGE (assign / clear / fortify) -- defense.js fires
      // 'ak-defense-change' so a raided base reflects the defense the owner just set,
      // not only the roster from session start. Throttle is bypassed (lastPublish=0).
      try { global.addEventListener('ak-defense-change', function () { M.lastPublish = 0; publishMyBase(ctx); }); } catch (_e3) {}
      // expose a tiny bridge so a future hub button / debug can open the war room
      global.AKRaid = { warMap: function () { openWarMap(ctx); }, defend: function () { openNightDefense(ctx); }, isNight: isNight, publishBase: function () { M.lastPublish = 0; publishMyBase(ctx); } };
    },

    onEnterBuilding: function (b, ctx) { return false; },   // raid owns NO interior

    onTick: function (dt, ctx) {
      var night = isNight();
      if (night && !M.wasNight) { ctx.showBanner('NIGHT FALLS -- strays on the prowl. Defend the Lot.', 2.4); armBeacon(ctx); }
      else if (!night && M.wasNight) { ctx.showBanner('Dawn breaks. The strays scatter.', 1.4); disarmBeacon(ctx); }
      M.wasNight = night;

      if (!night) {                                          // day -> rival scouts roam
        M.scoutTimer -= dt;
        if (!M.scout && !M.opening && M.scoutTimer <= 0) { spawnScout(ctx); M.scoutTimer = 55 + Math.random() * 45; }
      }
    },

    onDrawWorld: function (ctx) {
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var night = isNight();
      // night tint vignette over the whole screen (screen-space, save/restore balanced)
      if (night) {
        g.save();
        var dark = 0.34 + 0.10 * Math.sin(now() / 600);
        g.fillStyle = 'rgba(8,10,28,' + clamp(dark, 0.25, 0.5) + ')'; g.fillRect(0, 0, W, H);
        g.fillStyle = '#f3a0a0'; g.font = '800 12px system-ui'; g.textAlign = 'center'; g.textBaseline = 'top';
        g.fillText('NIGHT -- SIEGE RISK', W / 2, 70);
        g.restore();
      }
      // shield indicator pip (top-left, below radar)
      var p = profile(ctx);
      if (shieldActive(p)) {
        g.save();
        g.fillStyle = 'rgba(124,255,176,0.9)'; g.font = '800 11px system-ui'; g.textAlign = 'left'; g.textBaseline = 'top';
        g.fillText('SHIELD ' + fmtDur(raidOf(p).shieldUntil - now()), 12, 92);
        g.restore();
      }
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
