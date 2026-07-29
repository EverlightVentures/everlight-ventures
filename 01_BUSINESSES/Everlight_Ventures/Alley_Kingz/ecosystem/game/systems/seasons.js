/* game/systems/seasons.js -- AK_SYSTEMS module: WAVE 5 "SEASONS".
   ------------------------------------------------------------------------
   Live-ops chapters (Monopoly-GO event cadence x Sunflower-Land chapters).
   Six 6-week dog-themed chapters rotate forever:

       JUNKYARD DYNASTY  ($BCARDD / Boneguard)   -- rust-gold, drifting embers
       NEON HOWL         (Jagged / Zoomie)       -- magenta neon, sparks
       DOG DAYS          (Rosco / Leashbreak)    -- summer gold, heat shimmer
       BLOOD MOON        (Crown Foxhound / K9)   -- crimson, red drizzle
       FROSTBITE         (the whole street)      -- ice blue, snow
       GOLDEN LEASH      ($BCARDD finale)         -- gold, sparks

   What this wave OWNS (Section 3.5 + 4 of the contract):
   - TROPHY ("TROPHY HALL", HOME_TURF) interior -> keeper Goldie opens the Season
     hub (track / stall / ranks) + a once-a-day Marks check-in.
   - A seasonMarks currency that RESETS at the end of every chapter. Marks are
     COSMETIC-ONLY (parity-safe -- they NEVER buy power), banked in the single
     falsy-default field `season:{id,marks,claimed}` (Lead added it once in
     economy.js ensureShape). A never-played profile stays byte-identical: nothing
     is written until the player first checks in or unlocks a cosmetic.
   - Per-chapter world RE-THEME: a screen-space season tint wash + ambient
     particles in onDrawWorld (re-grades every district to the active chapter --
     no shared-file edit, no districtBg swap needed).
   - The Seasonal Stall (cosmetics bought with Marks) + a seasonal leaderboard
     that REUSES crew score (live ak-crew crews, ranked).
   - A re-themed Alley Pass entry-point (reuses the LIVE ak-pass; the season name
     is surfaced and the pass opens via AKPass).
   - ONE FRONT DOOR (P1): doCheckIn() is exposed as a SINGLE idempotent DAILY
     faucet (anchored to LOCAL PT) so the lobby can pay Marks + advance the streak
     in ONE tap (window.AKSeasons.doCheckIn). A second tap the same PT day no-ops.
   - WEATHER as a WORLD SIGNAL (P7): getWeather() promotes weather to a public,
     legible, deterministic-by-PT-day signal (sun/rain/fog/storm) carrying
     READ-ONLY econ modifiers (farm/raid/encounter) the integration pass samples,
     and shows it in the season banner. Writes nothing -- zero-state safe.

   HARD-LAW COMPLIANCE:
   - Marks are a SOFT cosmetic currency -- never gems ($ctx.currency.grant('gems')
     is a no-op anyway), never $BCARDD / ALK. Cosmetics are parity-safe (visual only).
   - Reward track reuses ak-pass; leaderboard reuses ak-crew; the only NEW server
     surface (ak-season, for a dedicated crew board + true cross-player Marks
     ledger) is clearly marked // TODO-SERVER and degrades gracefully today.
   - Headless-safe: zero top-level DOM/localStorage, so the file is requireable in
     node; only the AK_SYSTEMS registration is gated (AK-SEASONLOAD 2026-07-18 --
     window.AKSeasons now always exports so the battler's hooks can reach it);
     every state touch rides AK_ECON (already try/catch wrapped).
   - Reuses the 106 cards + 4 Mythics + 6 handlers BY NAME (figureheads, stall
     item names, leaderboard rival crews). No invented characters, no generic art.
   - Theme voice: gritty gold cyberpunk dog-gang street culture. "Crew" never "clan."
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';
  // AK-SEASONLOAD 2026-07-18: this used to bail HERE when AK_SYSTEMS was absent,
  // which also skipped the window.AKSeasons export at the bottom. The battler
  // (game/game.html) calls AKSeasons.onMatchEnd + AKSeasons.doCheckIn, so a
  // top-of-file bail would have left both hooks dead even once the page includes
  // this file. Follow the systems/story.js precedent instead: the module body is
  // pure data + function declarations (zero DOM, zero storage at load, so it is
  // still requireable in node), the PUBLIC surface always exports, and only the
  // hub-loop registration is gated on AK_SYSTEMS down at the bottom.

  // ---- chapter cadence -----------------------------------------------------
  var PERIOD_MS = 42 * 24 * 3600 * 1000;     // a chapter runs 6 weeks (42 days)
  var EPOCH     = Date.UTC(2026, 0, 5);      // anchor: Mon 2026-01-05 00:00 UTC (chapter 0 start)
  var DAY_MS    = 86400000;
  var PT_OFFSET_MS = 8 * 3600 * 1000;        // LOCAL PT anchor (UTC-8 / PST) -- the DAILY clock + weather roll at PT midnight

  // ---- Marks faucet (cosmetic-only; daily check-in keeps it self-contained) -
  var MARKS_BASE   = 25;                      // base Marks per daily check-in
  var STREAK_BONUS = 5;                       // +5 per consecutive day...
  var STREAK_CAP   = 7;                        // ...capped at +30 (25..55/day)
  var WIN_MARKS    = 6;                        // optional match-win Marks (via window.AKSeasons.onMatchEnd)
  var WIN_MARKS_CAP= 60;                       // per-day cap on match-won Marks (anti-farm)

  // ---- the six chapters (figureheads + stall = real card / faction names) ---
  // wash = [r,g,b] grade color (low-alpha soft-light); accent = UI gold-substitute;
  // ambient = particle style; stall items are COSMETIC-ONLY (parity-safe).
  var CHAPTERS = [
    { key:'junkyard', name:'JUNKYARD DYNASTY', glyph:'🦴', icon:'assets/icons/season_junkyard.png', figure:'$BCARDD', faction:'Boneguard Crew',
      accent:'#c9a84c', wash:[58,42,18], ambient:'embers',
      flavor:"Boneguard runs the scrapyards this season -- haul rust into a crown.",
      stall:[
        { id:'jd_frame_stonejaw', kind:'frame',  name:'Stonejaw Scrap Crown', cost:150 },
        { id:'jd_banner_boneyard',kind:'banner', name:'Boneyard Banner',       cost:220 },
        { id:'jd_aura_rusthaze',  kind:'aura',   name:'Rust-Haze Aura',        cost:320 } ] },
    { key:'neonhowl', name:'NEON HOWL', glyph:'🌃', icon:'assets/icons/season_neon.png', figure:'Jagged', faction:'Zoomie Syndicate',
      accent:'#ff5cc8', wash:[40,12,48], ambient:'sparks',
      flavor:"Jagged lights the strip magenta -- the Zoomies run wild after dark.",
      stall:[
        { id:'nh_trail_pixel',  kind:'trail',  name:'Pixel Greyhound Trail', cost:180 },
        { id:'nh_banner_howl',  kind:'banner', name:'Neon Howl Banner',      cost:240 },
        { id:'nh_aura_circuit', kind:'aura',   name:'Circuit-Glow Aura',     cost:330 } ] },
    { key:'dogdays', name:'DOG DAYS', glyph:'☀️', icon:'assets/icons/season_sun.png', figure:'Rosco', faction:'Leashbreak Tactix',
      accent:'#ffd76b', wash:[70,52,12], ambient:'heat',
      flavor:"Rosco calls the heat -- Leashbreak owns the long summer streets.",
      stall:[
        { id:'dd_frame_sun',   kind:'frame', name:'Sunbleached Frame',  cost:160 },
        { id:'dd_trail_holo',  kind:'trail', name:'Holo Husky Trail',   cost:200 },
        { id:'dd_aura_heat',   kind:'aura',  name:'Heatwave Aura',      cost:300 } ] },
    { key:'bloodmoon', name:'BLOOD MOON', glyph:'🌑', icon:'assets/icons/season_moon.png', figure:'Crown Foxhound', faction:'K9 Circuitry',
      accent:'#ff4d4d', wash:[60,8,12], ambient:'rain',
      flavor:"A Blood Moon over NeonReach -- Crown Foxhound's circuits run red.",
      stall:[
        { id:'bm_frame_fang',   kind:'frame',  name:'Crimson Fang Frame', cost:180 },
        { id:'bm_banner_moon',  kind:'banner', name:'Blood Moon Banner',  cost:260 },
        { id:'bm_aura_howl',    kind:'aura',   name:'Howling Aura',       cost:360 } ] },
    { key:'frostbite', name:'FROSTBITE', glyph:'❄️', icon:'assets/icons/season_frost.png', figure:'Stonejaw', faction:'Boneguard Crew',
      accent:'#9fdcff', wash:[14,26,44], ambient:'snow',
      flavor:"Frostbite locks the docks -- Stonejaw's pack digs in to survive.",
      stall:[
        { id:'fb_frame_ice',   kind:'frame', name:'Frostbite Frame',  cost:160 },
        { id:'fb_trail_snow',  kind:'trail', name:'Snowfall Trail',    cost:200 },
        { id:'fb_aura_iced',   kind:'aura',  name:'Iced-Out Aura',     cost:320 } ] },
    { key:'goldenleash', name:'GOLDEN LEASH', glyph:'👑', icon:'assets/icons/season_crown.png', figure:'$BCARDD', faction:'Boneguard Crew',
      accent:'#e8c55a', wash:[56,46,14], ambient:'sparks',
      flavor:"The Golden Leash finale -- $BCARDD crowns the kings of the street.",
      stall:[
        { id:'gl_frame_leash',  kind:'frame',  name:'Golden Leash Frame', cost:200 },
        { id:'gl_banner_dyn',   kind:'banner', name:'Dynasty Banner',     cost:300 },
        { id:'gl_aura_crown',   kind:'aura',   name:'Crown Aura',         cost:380 } ] }
  ];

  // ---- pure cadence helpers -------------------------------------------------
  function periodNow(now) { return Math.floor(((now || Date.now()) - EPOCH) / PERIOD_MS); }
  function chapterAt(period) { var i = ((period % CHAPTERS.length) + CHAPTERS.length) % CHAPTERS.length; return CHAPTERS[i]; }
  function seasonIdAt(period) { return chapterAt(period).key + '.' + period; }
  function currentSeasonId(now) { return seasonIdAt(periodNow(now)); }
  function currentChapter(now) { return chapterAt(periodNow(now)); }
  function dayKey(now) { return new Date((now || Date.now()) - PT_OFFSET_MS).toISOString().slice(0, 10); }   // LOCAL PT calendar day (UTC-8 anchor), YYYY-MM-DD
  function ptDayIndex(now) { return Math.floor(((now || Date.now()) - PT_OFFSET_MS) / DAY_MS); }            // PT day bucket -- the weather seed (rolls at PT midnight)
  function weekOf(now) { now = now || Date.now(); var p = periodNow(now); var into = now - (EPOCH + p * PERIOD_MS); return Math.min(6, Math.floor(into / (7 * DAY_MS)) + 1); }
  function daysLeft(now) { now = now || Date.now(); var p = periodNow(now); var end = EPOCH + (p + 1) * PERIOD_MS; return Math.max(0, Math.ceil((end - now) / DAY_MS)); }

  function profile(ctx) { return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; }
  function seasonOf(p) { return (p && p.season && typeof p.season === 'object') ? p.season : { id:'', marks:0, claimed:[] }; }
  function marksOf(ctx) { var p = profile(ctx); return seasonOf(p).marks | 0; }

  // ---- WEATHER as a WORLD SIGNAL (P7) ---------------------------------------
  // Promotes the garden weather idea (AK_ECON.gardenWeather) to a CITY-WIDE,
  // legible signal the whole street feels: SUN / RAIN / FOG / STORM. Deterministic
  // by the LOCAL PT day (LCG hash on ptDayIndex -- mirrors the econ weather seed,
  // NO client RNG, byte-identical for everyone on the same PT day, never flips
  // mid-session). It WRITES NOTHING to the profile (zero-state safe) and carries
  // READ-ONLY econ modifiers the farming / raid / encounter systems sample via
  // window.AKSeasons.getWeather() / .weatherMod(domain). PARITY HARD-LAW: a global,
  // symmetric, no-gem world condition (like a Pokemon-GO boost ring) -- never
  // pay-to-win. Legible by design: glyph + label + one canon street blurb.
  var WX = {
    sun:   { key:'sun',   label:'Clear Skies', glyph:'☀️', icon:'assets/icons/wx_sun.png',
             blurb:'Dry blocks, clean sightlines over the 9 districts.',
             farmMult:1.00, raidMult:1.00, encounterMult:1.00 },
    rain:  { key:'rain',  label:'Rain',        glyph:'🌧️', icon:'assets/icons/wx_rain.png',
             blurb:'Crops drink deep, but the Watch runs thin in the wet.',
             farmMult:1.15, raidMult:0.90, encounterMult:1.10 },
    fog:   { key:'fog',   label:'Fog',         glyph:'🌫️', icon:'assets/icons/wx_fog.png',
             blurb:'Low cover off the docks -- more strays slip the Fence.',
             farmMult:1.00, raidMult:0.85, encounterMult:1.25 },
    storm: { key:'storm', label:'Storm',       glyph:'⛈️', icon:'assets/icons/wx_storm.png',
             blurb:'The streets bite back -- harvest suffers, raids turn vicious.',
             farmMult:0.85, raidMult:1.20, encounterMult:0.90 }
  };
  var WX_WHEEL = ['sun','sun','rain','fog','sun','rain','storm','sun'];   // ~50% sun / 25% rain / 12.5% fog / 12.5% storm
  function weatherKeyFor(day) { return WX_WHEEL[((day * 1103515245 + 12345) >>> 0) % WX_WHEEL.length]; }   // LCG hash -> deterministic wheel pick
  var _wxCache = null;                                                  // memo by PT day (cheap-Android: no per-call object churn)
  function getWeather(now) {
    var day = ptDayIndex(now);
    if (_wxCache && _wxCache.day === day) return _wxCache.wx;
    var w = WX[weatherKeyFor(day)] || WX.sun;
    var wx = { key:w.key, label:w.label, glyph:w.glyph, icon:w.icon, blurb:w.blurb,
               farmMult:w.farmMult, raidMult:w.raidMult, encounterMult:w.encounterMult, day:day };
    _wxCache = { day:day, wx:wx };
    return wx;
  }
  // single read for the integration pass: the multiplier (>=0, default 1) for
  // 'farm' | 'raid' | 'encounter'. Unknown/falsy domain -> 1 (no-op, parity-safe).
  function weatherMod(domain, now) {
    var wx = getWeather(now);
    if (domain === 'farm') return wx.farmMult;
    if (domain === 'raid') return wx.raidMult;
    if (domain === 'encounter') return wx.encounterMult;
    return 1;
  }

  // ---- season-boundary roll: RESET Marks + claims when a chapter ends -------
  // Lazy + byte-identical for fresh profiles: we only WRITE if the player has
  // already started a season (season.id set) AND it differs from the live one.
  function maybeRoll(ctx, now) {
    var p = profile(ctx); if (!p) return false;
    var s = seasonOf(p); var cur = currentSeasonId(now);
    if (!s.id) return false;                      // never started -> leave untouched (zero-state safe)
    if (s.id === cur) return false;               // same chapter -> nothing to do
    ctx.econ.mutateProfile(function (pp) {
      if (!pp.season || typeof pp.season !== 'object') pp.season = { id:'', marks:0, claimed:[] };
      pp.season.id = cur; pp.season.marks = 0; pp.season.claimed = []; pp.season.checkIn = null;
    });
    return true;
  }

  // ---- daily check-in (the Marks faucet) ------------------------------------
  function checkInStatus(ctx, now) {
    now = now || Date.now();
    var p = profile(ctx); var s = seasonOf(p);
    var ci = s.checkIn || {}; var today = dayKey(now);
    var available = ci.day !== today;
    var streak = (ci.day === today) ? (ci.streak | 0) : ((ci.day === dayKey(now - DAY_MS)) ? (ci.streak | 0) : 0);
    var nextStreak = available ? Math.min(STREAK_CAP, streak + 1) : streak;
    var reward = MARKS_BASE + (Math.max(0, nextStreak - 1) * STREAK_BONUS);
    return { available: available, streak: streak, nextStreak: nextStreak, reward: reward };
  }
  function doCheckIn(ctx, now) {
    now = now || Date.now();
    var today = dayKey(now), yday = dayKey(now - DAY_MS), cur = currentSeasonId(now);
    var res = { ok:false };
    ctx.econ.mutateProfile(function (p) {
      if (!p.season || typeof p.season !== 'object') p.season = { id:'', marks:0, claimed:[] };
      var s = p.season; if (s.id !== cur) { s.id = cur; s.marks = 0; s.claimed = []; s.checkIn = null; } // first stamp / silent roll
      var ci = s.checkIn || {};
      if (ci.day === today) { res = { ok:false, err:'DONE' }; return; }
      var streak = (ci.day === yday) ? Math.min(STREAK_CAP, (ci.streak | 0) + 1) : 1;
      var reward = MARKS_BASE + (Math.max(0, streak - 1) * STREAK_BONUS);
      s.marks = Math.max(0, (s.marks | 0) + reward);
      s.checkIn = { day: today, streak: streak };
      res = { ok:true, reward: reward, streak: streak, marks: s.marks };
    });
    return res;
  }

  // ---- optional match-win Marks (window.AKSeasons.onMatchEnd; daily-capped) --
  // Integration hook: game/game.html:8159 fires this once per match behind the
  // g._rewarded guard. Marks are COSMETIC currency only, so a win pays flex and
  // never power. NOTE: do NOT report pass XP from here. game.html:8146 already
  // fires AKPass.reportMatch on the same event; a second report would double-count
  // against the server's 300 XP/day cap.
  // AK-SEASONCTX 2026-07-18: resolve ctx the same way game.html:8875 does for
  // doCheckIn. Reading only global.AK_CTX meant that if AK_CTX had not been built
  // yet (it is set once, later, in the main script) a win silently paid nothing.
  function onMatchEnd(result, ctxIn) {
    try {
      var ctx = ctxIn || global.AK_CTX || (global.AK_ECON ? { econ: global.AK_ECON } : null);
      if (!ctx || !ctx.econ) return;
      var won = (result === 'win' || result === true || (result && result.result === 'win') || (result && result.won));
      if (!won) return;
      var now = Date.now(), today = dayKey(now), cur = currentSeasonId(now);
      ctx.econ.mutateProfile(function (p) {
        if (!p.season || typeof p.season !== 'object') p.season = { id:'', marks:0, claimed:[] };
        var s = p.season; if (s.id !== cur) { s.id = cur; s.marks = 0; s.claimed = []; s.checkIn = null; }
        var wm = s.winMarks || {}; var got = (wm.day === today) ? (wm.n | 0) : 0;
        if (got >= WIN_MARKS_CAP) return;
        var add = Math.min(WIN_MARKS, WIN_MARKS_CAP - got);
        /* AK-FIX-lane-C 2026-07-28: TROPHY building payoff. The Trophy Hall upgrade
           (AK_ECON.trophyRepMult, +5%/lvl) already boosts core Rep inside addRep(),
           but season Marks are granted directly here and were bypassing it -- so the
           upgrade did nothing for the season faucet. Guarded (global idiom, matches
           this file's AK_ECON refs) so an unwired multiplier just reads 1x and never
           crashes. The anti-farm WIN_MARKS_CAP stays tracked in BASE units below
           (winMarks.n = got + add), so the trophy boost pays more Marks without
           inflating the daily grant cap. */
        var tm = (global.AK_ECON && global.AK_ECON.trophyRepMult) ? global.AK_ECON.trophyRepMult(p) : 1;
        s.marks = Math.max(0, (s.marks | 0) + Math.round(add * tm));
        s.winMarks = { day: today, n: got + add };
      });
    } catch (_e) {}
  }

  // ---- the Seasonal Stall: unlock a cosmetic with Marks (parity-safe) -------
  function isOwned(ctx, itemId) { var s = seasonOf(profile(ctx)); return (s.claimed || []).indexOf(itemId) >= 0; }
  // AK-PARITY 2026-07-18: Marks buy FLEX, never power. The ladder already ranks on
  // card level + Town Hall, so a seasonal currency that bought scrap / chests /
  // cards / keys would sell raid strength on top of that spine. This allowlist is
  // the enforcement, not just the convention: a stall item whose kind is not a
  // pure cosmetic is refused here even if someone adds it to CHAPTERS later.
  var COSMETIC_KINDS = { frame:1, banner:1, aura:1, trail:1, skin:1 };
  function isCosmetic(item) { return !!(item && COSMETIC_KINDS[item.kind]); }
  function doUnlock(ctx, item, now) {
    if (!isCosmetic(item)) return { ok:false, err:'PARITY' };   // never power, at any price
    var cur = currentSeasonId(now || Date.now());
    var res = { ok:false };
    ctx.econ.mutateProfile(function (p) {
      if (!p.season || typeof p.season !== 'object') p.season = { id:'', marks:0, claimed:[] };
      var s = p.season; if (s.id !== cur) { s.id = cur; s.marks = 0; s.claimed = []; s.checkIn = null; }
      if (!Array.isArray(s.claimed)) s.claimed = [];
      if (s.claimed.indexOf(item.id) >= 0) { res = { ok:false, err:'OWNED' }; return; }
      if ((s.marks | 0) < item.cost) { res = { ok:false, err:'MARKS', need:item.cost, have:s.marks | 0 }; return; }
      s.marks = (s.marks | 0) - item.cost; s.claimed.push(item.id);
      res = { ok:true, marks: s.marks };
    });
    // TODO-SERVER: mirror the unlock to ak-cosmetics so the cosmetic equips on the
    // server profile (drip.js / ak-cosmetics own real cosmetic state). Parity-safe:
    // cosmetics are visual only -- the local record above is the source until then.
    if (res.ok) { try { trySyncCosmetic(item); } catch (_e) {} }
    return res;
  }
  function trySyncCosmetic(item) {
    // best-effort, fire-and-forget; degrades silently when ak-cosmetics is offline.
    var sb = sbc(); if (!sb || !me()) return;
    // TODO-SERVER: ak-cosmetics needs a {action:'season-unlock'} that validates the
    // Marks spend server-side (cross-device) and grants the cosmetic via ak_grants.
    try { sb.functions.invoke('ak-cosmetics', { body: { action: 'season-unlock', item_id: item.id, season: currentSeasonId() } }); } catch (_e) {}
  }

  // ---- server plumbing (reused rails; ak-season is // TODO-SERVER) ----------
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me()  { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function call(fn, body) {
    var sb = sbc();
    if (!sb) return Promise.resolve({ ok:false, error:'offline' });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var c = r.error && r.error.context;
        if (c && typeof c.json === 'function') return c.json().then(function (j) { return j || { ok:false, error:r.error.message }; }, function () { return { ok:false, error:r.error.message }; });
        return { ok:false, error:(r.error && r.error.message) || 'error' };
      }
      return r.data || { ok:false, error:'empty' };
    }, function (e) { return { ok:false, error:String((e && e.message) || e) }; });
  }
  // Seasonal leaderboard -- REUSE crew score. Prefer ak-season (// TODO-SERVER:
  // a dedicated, season-scoped crew board); fall back to LIVE ak-crew list ranked
  // by trophies so the board is real today, not a stub.
  function loadLeaderboard(cb) {
    call('ak-season', { action: 'leaderboard', season: currentSeasonId() }).then(function (r) {
      if (r && r.ok && Array.isArray(r.crews) && r.crews.length) { cb(r.crews, 'ak-season'); return; }
      // TODO-SERVER: the line above is the real home; until ak-season ships we reuse ak-crew.
      call('ak-crew', { action: 'list', q: '' }).then(function (rr) {
        var crews = (rr && rr.crews) || [];
        crews = crews.slice().sort(function (a, b) { return (b.trophies | 0) - (a.trophies | 0) || (b.member_count | 0) - (a.member_count | 0); }).slice(0, 25);
        cb(crews, crews.length ? 'ak-crew' : 'none');
      });
    });
  }

  // ==========================================================================
  // THE SEASON HUB OVERLAY (DOM panel on top of a frozen, themed backdrop).
  // Mirrors trading.js: ctx.overlay.open() freezes the hub + paints an animated
  // chapter backdrop; a #ak-season DOM section (z 47) holds the tabs.
  // ==========================================================================
  var HUB = { ov:null, root:null, bodyEl:null, headEl:null, tabsEl:null, toastEl:null, tab:'stall', ctx:null, ch:null };

  function injectCss() {
    if (document.getElementById('ak-season-css')) return;
    var st = document.createElement('style'); st.id = 'ak-season-css';
    st.textContent = [
      '#ak-season{position:fixed;inset:0;z-index:47;display:none;flex-direction:column;background:linear-gradient(180deg,rgba(11,10,16,.92),rgba(8,8,12,.97));color:#e9e9ee;font-family:Inter,system-ui,sans-serif}',
      '#ak-season.open{display:flex}',
      '.aksn-top{display:flex;align-items:center;gap:10px;padding:13px 14px;border-bottom:1px solid rgba(201,168,76,.2)}',
      '.aksn-glyph{font-size:26px;line-height:1}',
      '.aksn-ttl{flex:1}.aksn-ttl h2{margin:0;font-size:16px;letter-spacing:.06em;font-family:Cinzel,serif}',
      '.aksn-ttl .sub{font-size:11px;color:#9a9aa6;margin-top:2px}',
      '.aksn-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}',
      '.aksn-hd{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);display:flex;align-items:center;gap:10px}',
      '.aksn-marks{font-weight:900;font-size:15px}',
      '.aksn-wx{display:inline-flex;align-items:center;gap:6px;margin-left:10px;font-size:11px;font-weight:800;letter-spacing:.03em;color:#cfcfd6;padding:4px 9px;border-radius:9px;border:1px solid rgba(201,168,76,.28);background:rgba(255,255,255,.05)}',
      '.aksn-ci{margin-left:auto;border:0;border-radius:9px;padding:9px 13px;font-weight:800;font-size:12px;letter-spacing:.03em;cursor:pointer;color:#15110a}',
      '.aksn-ci[disabled]{opacity:.5;filter:grayscale(.5);cursor:default}',
      '.aksn-tabs{display:flex;gap:6px;padding:9px 12px}',
      '.aksn-tab{flex:1;padding:9px;border-radius:9px;border:1px solid rgba(201,168,76,.22);background:rgba(255,255,255,.03);color:#cfcfd6;font-weight:800;font-size:12px;letter-spacing:.04em;cursor:pointer}',
      '.aksn-tab.on{background:rgba(201,168,76,.16);border-color:rgba(201,168,76,.5)}',
      '.aksn-body{flex:1;overflow-y:auto;padding:10px 12px;-webkit-overflow-scrolling:touch}',
      '.aksn-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:12px;margin-bottom:10px}',
      '.aksn-item{display:flex;align-items:center;gap:10px;padding:10px;border:1px solid rgba(255,255,255,.08);border-radius:11px;margin-bottom:9px;background:rgba(255,255,255,.03)}',
      '.aksn-ico{width:40px;height:40px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:20px;border:1px solid rgba(201,168,76,.3)}',
      '.aksn-nm{font-weight:800;color:#fff;font-size:14px}.aksn-kd{font-size:11px;color:#9a9aa6;letter-spacing:.04em;text-transform:uppercase}',
      '.aksn-buy{border:0;border-radius:9px;padding:9px 13px;font-weight:800;font-size:12px;cursor:pointer;color:#15110a}',
      '.aksn-buy.owned{background:rgba(95,211,95,.16);color:#8fe08f;border:1px solid rgba(95,211,95,.4);cursor:default}',
      '.aksn-buy[disabled]{opacity:.5;cursor:default}',
      '.aksn-li{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid rgba(255,255,255,.06)}',
      '.aksn-rk{width:26px;text-align:center;font-weight:900;color:#c9a84c}',
      '.aksn-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px 8px;line-height:1.5}',
      '.aksn-btn{background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:0;border-radius:10px;padding:12px 0;width:100%;font-weight:900;font-size:14px;letter-spacing:.03em;cursor:pointer}',
      '.aksn-toast{position:fixed;left:50%;bottom:84px;transform:translateX(-50%);background:#1a1a22;color:#c9a84c;border:1px solid rgba(201,168,76,.4);padding:9px 16px;border-radius:20px;z-index:71;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}',
      '.aksn-toast.show{opacity:1}'
    ].join('');
    document.head.appendChild(st);
  }

  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
      if (k === 'class') e.className = v; else if (k === 'text') e.textContent = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') e[k] = v; else e.setAttribute(k, v);
    });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      e.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
    });
    return e;
  }
  function setKids(el, nodes) { if (el) el.replaceChildren.apply(el, [].concat(nodes).filter(function (n) { return n != null; })); }
  function toast(m) { var t = HUB.toastEl; if (!t) return; t.textContent = m; t.classList.add('show'); clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove('show'); }, 2200); }

  // AK-DEEMOJI: paint a PNG chapter icon into a glyph span, emoji as graceful fallback
  // (mirrors index.html setKeeperPortrait -- art preferred, glyph on 404/missing).
  // _glyphArtDead remembers paths that failed so we skip straight to the emoji next time.
  var _glyphArtDead = {};
  function setGlyphArt(el, art, glyph) {
    if (!el) return;
    glyph = glyph || '◆'; el.textContent = '';
    if (!art || _glyphArtDead[art]) { el.textContent = glyph; return; }
    var img = new Image(); img.alt = '';
    img.style.cssText = 'width:26px;height:26px;border-radius:6px;object-fit:contain;display:block;';
    img.onerror = function () { _glyphArtDead[art] = 1; if (el) el.textContent = glyph; };
    el.appendChild(img); img.src = art;   // appended first so the onerror swap targets a mounted node
  }

  var ICON = { frame:'🖼️', banner:'🚩', aura:'✨', trail:'💫' };

  function buildHubShell() {
    if (HUB.root) return;
    injectCss();
    var x = mk('button', { class:'aksn-x', type:'button', text:'×', onclick: closeHub });
    HUB.glyphEl = mk('span', { class:'aksn-glyph', text:'👑' });
    var ttl = mk('div', { class:'aksn-ttl' }, [ mk('h2', { id:'aksn-h2', text:'SEASON' }), mk('div', { class:'sub', id:'aksn-sub', text:'' }) ]);
    var top = mk('div', { class:'aksn-top' }, [ HUB.glyphEl, ttl, x ]);
    HUB.headEl = mk('div', { class:'aksn-hd' });
    var tStall = mk('button', { class:'aksn-tab on', type:'button', text:'STALL',   onclick:function(){ setTab('stall'); } });
    var tRanks = mk('button', { class:'aksn-tab',    type:'button', text:'RANKS',   onclick:function(){ setTab('ranks'); } });
    var tPass  = mk('button', { class:'aksn-tab',    type:'button', text:'PASS',    onclick:function(){ setTab('pass'); } });
    HUB._tabs = { stall:tStall, ranks:tRanks, pass:tPass };
    HUB.tabsEl = mk('div', { class:'aksn-tabs' }, [ tStall, tRanks, tPass ]);
    HUB.bodyEl = mk('div', { class:'aksn-body' });
    HUB.root = mk('section', { id:'ak-season' }, [ top, HUB.headEl, HUB.tabsEl, HUB.bodyEl ]);
    document.body.appendChild(HUB.root);
    HUB.toastEl = mk('div', { class:'aksn-toast' }); document.body.appendChild(HUB.toastEl);
  }

  function openHub(ctx) {
    HUB.ctx = ctx; HUB.ch = currentChapter();
    buildHubShell();
    // freeze the hub + paint an animated chapter backdrop behind the panel
    try {
      HUB.ov = ctx.overlay.open({ id:'season_hub',
        onFrame: function (g, dt, vp) { drawHubBackdrop(g, vp, dt); },
        onPointer: function () {},
        onClose: function () { teardownHub(); } });
    } catch (_e) { HUB.ov = null; }
    HUB.root.classList.add('open');
    setTab('stall');
  }
  function closeHub() { if (HUB.ov && HUB.ov.close) { try { HUB.ov.close(); return; } catch (_e) {} } teardownHub(); }
  function teardownHub() { if (HUB.root) HUB.root.classList.remove('open'); HUB.ov = null; }

  // animated, season-graded backdrop drawn into the overlay canvas (cheap)
  var _bd = [];
  function drawHubBackdrop(g, vp, dt) {
    var ch = HUB.ch || currentChapter(); var w = vp.w, h = vp.h;
    var gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, 'rgb(' + ch.wash[0] + ',' + ch.wash[1] + ',' + ch.wash[2] + ')');
    gr.addColorStop(1, '#08080c');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    if (!_bd.length) { for (var i = 0; i < 30; i++) _bd.push({ x:Math.random()*w, y:Math.random()*h, v:8+Math.random()*22, r:1+Math.random()*2.2, a:.15+Math.random()*.4, tw:Math.random()*6 }); }
    g.save(); g.fillStyle = ch.accent;
    for (var j = 0; j < _bd.length; j++) { var p = _bd[j];
      p.y -= p.v * dt; p.tw += dt * 2; if (p.y < -4) { p.y = h + 4; p.x = Math.random() * w; }
      g.globalAlpha = p.a * (.5 + .5 * Math.sin(p.tw));
      g.beginPath(); g.arc(p.x, p.y, p.r, 0, 7); g.fill();
    }
    g.restore();
  }

  function setTab(t) {
    HUB.tab = t;
    Object.keys(HUB._tabs).forEach(function (k) { HUB._tabs[k].classList.toggle('on', k === t); });
    renderHead();
    if (t === 'stall') renderStall(); else if (t === 'ranks') renderRanks(); else renderPass();
  }

  function renderHead() {
    var ctx = HUB.ctx, ch = HUB.ch || currentChapter();
    var wx = getWeather();                                          // P7: the legible world-signal weather
    if (HUB.glyphEl) setGlyphArt(HUB.glyphEl, ch.icon, ch.glyph);   // AK-DEEMOJI: PNG icon, emoji fallback
    var h2 = document.getElementById('aksn-h2'), sub = document.getElementById('aksn-sub');
    if (h2) h2.textContent = ch.name;
    if (sub) sub.textContent = 'Week ' + weekOf() + ' of 6 -- ' + daysLeft() + ' day' + (daysLeft() === 1 ? '' : 's') + ' left -- led by ' + ch.figure + ' -- ' + wx.glyph + ' ' + wx.label;
    var ci = checkInStatus(ctx);
    var btn = mk('button', { class:'aksn-ci', text: ci.available ? ('CHECK IN +' + ci.reward + ' MARKS') : ('CHECKED IN -- streak ' + ci.streak), style:'background:' + (ci.available ? 'linear-gradient(180deg,#e8c55a,#c9a84c)' : 'rgba(255,255,255,.08)') + (ci.available ? '' : ';color:#9a9aa6') });
    if (!ci.available) btn.disabled = true;
    else btn.onclick = function () {
      var r = doCheckIn(ctx);
      if (r.ok) toast('+' + r.reward + ' Marks  (streak ' + r.streak + ')');
      renderHead(); if (HUB.tab === 'stall') renderStall();
    };
    setKids(HUB.headEl, [
      mk('span', { class:'aksn-marks', style:'color:' + ch.accent, text:'◆ ' + marksOf(ctx) + ' MARKS' }),
      mk('span', { class:'aksn-wx', title: wx.blurb, text: wx.glyph + ' ' + wx.label }),   // P7: weather banner chip (boost-ring readout)
      btn
    ]);
  }

  function renderStall() {
    var ctx = HUB.ctx, ch = HUB.ch || currentChapter();
    var intro = mk('div', { class:'aksn-card' }, [
      mk('div', { class:'aksn-nm', text:'SEASONAL STALL' }),
      mk('div', { class:'aksn-kd', style:'margin-top:4px;text-transform:none;color:#cfcfd6', text: ch.flavor + ' Cosmetics only -- pure flex, never power.' })
    ]);
    var items = ch.stall.map(function (it) {
      var owned = isOwned(ctx, it.id);
      var have = marksOf(ctx);
      var btn;
      if (owned) btn = mk('button', { class:'aksn-buy owned', text:'OWNED' });
      else {
        btn = mk('button', { class:'aksn-buy', style:'background:linear-gradient(180deg,#e8c55a,#c9a84c)', text:'◆ ' + it.cost });
        if (have < it.cost) btn.disabled = true;
        else btn.onclick = function () {
          var r = doUnlock(ctx, it);
          if (r.ok) toast('Unlocked ' + it.name + '!');
          else if (r.err === 'MARKS') toast('Need ' + r.need + ' Marks (have ' + r.have + ')');
          renderHead(); renderStall();
        };
      }
      return mk('div', { class:'aksn-item' }, [
        mk('div', { class:'aksn-ico', style:'color:' + ch.accent, text: ICON[it.kind] || '✨' }),
        mk('div', { style:'flex:1' }, [ mk('div', { class:'aksn-nm', text: it.name }), mk('div', { class:'aksn-kd', text: it.kind }) ]),
        btn
      ]);
    });
    setKids(HUB.bodyEl, [intro].concat(items));
  }

  function renderRanks() {
    var ch = HUB.ch || currentChapter();
    var head = mk('div', { class:'aksn-card' }, [
      mk('div', { class:'aksn-nm', text:'SEASONAL LEADERBOARD' }),
      mk('div', { class:'aksn-kd', style:'margin-top:4px;text-transform:none;color:#cfcfd6', text:'Crews ranked by trophies this chapter. Stack wins -- carry your crew up the board.' })
    ]);
    var listBox = mk('div', {}, mk('div', { class:'aksn-note', text:'Loading the board...' }));
    setKids(HUB.bodyEl, [head, listBox]);
    loadLeaderboard(function (crews, source) {
      if (HUB.tab !== 'ranks') return;
      if (!crews || !crews.length) {
        setKids(listBox, mk('div', { class:'aksn-note', text:'No crews on the board yet. Start or join a crew in the Crew Yard -- your wins put your crew on the ' + ch.name + ' board.' }));
        return;
      }
      var rows = crews.map(function (c, i) {
        return mk('div', { class:'aksn-li' }, [
          mk('div', { class:'aksn-rk', text: '#' + (i + 1) }),
          mk('div', { style:'flex:1' }, [
            mk('div', { class:'aksn-nm', style:'font-size:13px', text: (c.name || 'Crew') + (c.tag ? ('  [' + c.tag + ']') : '') }),
            mk('div', { class:'aksn-kd', style:'text-transform:none', text: (c.faction_name || c.faction || '') + (c.member_count != null ? ('  -- ' + c.member_count + ' members') : '') })
          ]),
          mk('div', { style:'font-weight:900;color:' + ch.accent, text: (c.trophies | 0) + ' 🏆' })
        ]);
      });
      var foot = (source === 'ak-crew') ? [ mk('div', { class:'aksn-note', text:'Live crew standings. A dedicated season-scoped board lands with ak-season.' }) ] : [];
      setKids(listBox, rows.concat(foot));
    });
  }

  function renderPass() {
    var ch = HUB.ch || currentChapter();
    var card = mk('div', { class:'aksn-card' }, [
      mk('div', { class:'aksn-nm', text: ch.name + ' -- ALLEY PASS' }),
      mk('div', { class:'aksn-kd', style:'margin-top:6px;text-transform:none;color:#cfcfd6;line-height:1.5',
        text:'This chapter re-themes the Alley Pass around ' + ch.figure + ' and the ' + ch.faction + '. Free + Premium lanes, 30 tiers -- every match levels it up. Marks are the cosmetic flex on top; the Pass is where the loot lives.' })
    ]);
    // AK-SEASONCHAPTER 2026-07-18: read the LIVE pass state off game/pass.js. Both
    // files load together on index.html, so this is real on the hub; synced=false
    // (pass never opened this session, or signed out) falls back to the pitch line.
    var pp = null;
    try { if (global.AKPass && global.AKPass.progress) pp = global.AKPass.progress(); } catch (_e) {}
    if (pp && pp.synced) {
      card.appendChild(mk('div', { class:'aksn-kd', style:'margin-top:8px;text-transform:none;color:' + ch.accent,
        text:'Tier ' + pp.tier + ' / ' + pp.maxTier + (pp.tier >= pp.maxTier ? ' -- season maxed' : ' -- ' + pp.toNext + ' XP to tier ' + (pp.tier + 1)) + (pp.premium ? '  -  PREMIUM ACTIVE' : '') }));
      // AK-PASSPACE 2026-07-18: the chapter clock is the only thing that makes the
      // pass urgent, and this file owns that clock. pass.js owns the curve and the
      // server's 300 XP/day ceiling, so we hand it daysLeft() and print the answer.
      var pace = null;
      try { if (global.AKPass && global.AKPass.paceToFinish) pace = global.AKPass.paceToFinish(daysLeft()); } catch (_e) {}
      if (pace) card.appendChild(mk('div', { class:'aksn-kd', style:'margin-top:4px;text-transform:none;color:#9a9aa6',
        text: (pace.need === 0)
          ? 'Pass complete -- all ' + pp.maxTier + ' tiers banked before the chapter closed.'
          : (pace.onPace
              ? (pace.need + ' XP left. That is ' + pace.perDay + ' a day for ' + pace.days + ' day' + (pace.days === 1 ? '' : 's') + ' -- about ' + pace.matchesPerDay + ' match' + (pace.matchesPerDay === 1 ? '' : 'es') + ' a day.')
              : (pace.need + ' XP left with ' + pace.days + ' day' + (pace.days === 1 ? '' : 's') + ' of chapter to run. The 300/day ceiling needs ' + pace.minDays + ' -- push hard or ride it into next chapter.')) }));
    }
    var openBtn = mk('button', { class:'aksn-btn', text:'OPEN THE ALLEY PASS', onclick: function () {
      try { if (global.AKPass && global.AKPass.open) { closeHub(); setTimeout(function () { global.AKPass.open(); }, 60); return; } } catch (_e) {}
      toast('Alley Pass opens from the Pass House (THE YARDS).');
    } });
    setKids(HUB.bodyEl, [card, openBtn]);
    // TODO-SERVER: ak-pass SEASON is pinned to 1 server-side. A {action:'set-season'}
    // (or a season-derived TRACK) would let this chapter actually re-skin the reward
    // track. Until then the Pass is shared across chapters; the framing above is live.
  }

  // ==========================================================================
  // KEEPER (TROPHY HALL) -- the in-world entry point. Goldie greets you, shows the
  // chapter + Marks, lets you check in fast, and opens the Season hub.
  // ==========================================================================
  function renderKeeper(ctx, b) {
    var ch = currentChapter();
    var marks = marksOf(ctx);
    var ci = checkInStatus(ctx);
    var wx = getWeather();                                                // P7: world-signal weather in the banner line
    var line = ch.name + '  --  ' + wx.glyph + ' ' + wx.label + '. ' + wx.blurb + '  Week ' + weekOf() + '/6, ' + daysLeft() + 'd left.  ◆ ' + marks + ' Marks. ' + ch.flavor;
    var checkLabel = ci.available ? ('SEASON CHECK-IN  (+' + ci.reward + ' Marks)') : ('CHECKED IN -- streak ' + ci.streak);
    ctx.ui.keeperCard({
      place: b.label, glyph: '🏆', name: 'Goldie',
      line: line,
      interiorArt: 'assets/interiors/merchant.png',
      buttons: [
        { label: 'ENTER THE TROPHY HALL', primary: true, onClick: function (c) { openHub(c); } },
        { label: checkLabel, primary: false, disabled: !ci.available, onClick: function (c) {
            var r = doCheckIn(c);
            if (r.ok) c.showBanner('Season check-in: +' + r.reward + ' Marks (streak ' + r.streak + ')', 1.8);
            renderKeeper(c, b);
          } }
      ]
    });
  }

  // ---- world re-theme (season tint wash + ambient particles) ----------------
  var _amb = [];                          // screen-space ambient particles (recycled)
  var _chCache = null, _chAcc = 0;
  function seedAmbient(W, H) {
    _amb = []; for (var i = 0; i < 22; i++) _amb.push({ x:Math.random()*(W||360), y:Math.random()*(H||640), vx:(Math.random()-.5)*10, vy:0, r:.6+Math.random()*1.8, a:.12+Math.random()*.34, tw:Math.random()*6 });
  }

  // ---- the AK_SYSTEMS module ------------------------------------------------
  // AK-SEASONLOAD 2026-07-18: gated HERE, not at the top of the file. The hub
  // (index.html) owns the loop and gets init/onTick/onDrawWorld; the battler and
  // the node harness skip registration but still get window.AKSeasons below.
  if (global.AK_SYSTEMS) global.AK_SYSTEMS.register({
    id: 'seasons',

    init: function (ctx) {
      try { maybeRoll(ctx, Date.now()); } catch (_e) {}     // close out a chapter that ended while away
      _chCache = currentChapter();
      seedAmbient(ctx.world && ctx.world.W, ctx.world && ctx.world.H);
    },

    onEnterBuilding: function (b, ctx) {
      if (!b || b.id !== 'TROPHY') return false;            // claim ONLY Trophy Hall (Section 4)
      try { maybeRoll(ctx, Date.now()); } catch (_e) {}
      renderKeeper(ctx, b);
      return true;                                          // host shows the panel + suppresses the default keeper
    },

    onTick: function (dt, ctx) {
      _chAcc += dt;
      if (_chAcc >= 20) { _chAcc = 0; _chCache = currentChapter(); try { maybeRoll(ctx, Date.now()); } catch (_e) {} } // re-check the boundary every ~20s
    },

    // per-frame season GRADE + ambient: re-themes every district to the chapter.
    onDrawWorld: function (ctx) {
      var ch = _chCache || currentChapter(); if (!ch) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      if (!_amb.length || _amb._w !== W) { seedAmbient(W, H); _amb._w = W; }
      g.save();
      // (1) color grade -- low-alpha soft-light wash keeps the district art readable
      try { g.globalCompositeOperation = 'soft-light'; } catch (_e) {}
      g.globalAlpha = 0.55;
      g.fillStyle = 'rgb(' + ch.wash[0] + ',' + ch.wash[1] + ',' + ch.wash[2] + ')';
      g.fillRect(0, 0, W, H);
      g.globalCompositeOperation = 'source-over';
      // (2) ambient particles -- behaviour by chapter (no shadowBlur; perf-safe)
      var amb = ch.ambient;
      var fall = (amb === 'snow' || amb === 'rain');
      var col  = (amb === 'snow') ? '#dff2ff' : ch.accent;
      var spd  = (amb === 'rain') ? 150 : (amb === 'snow' ? 26 : 16);
      g.fillStyle = col;
      for (var i = 0; i < _amb.length; i++) {
        var p = _amb[i]; p.tw += 0.03;
        if (fall) { p.y += spd * 0.016; p.x += Math.sin(p.tw) * (amb === 'snow' ? 0.5 : 0.15); if (p.y > H + 4) { p.y = -4; p.x = Math.random() * W; } }
        else { p.y -= spd * 0.016; p.x += p.vx * 0.016; if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W; } if (p.x < -4) p.x = W + 4; if (p.x > W + 4) p.x = -4; }
        g.globalAlpha = p.a * (0.5 + 0.5 * Math.sin(p.tw));
        if (amb === 'rain') { g.fillRect(p.x, p.y, 1, 6); }
        else { g.beginPath(); g.arc(p.x, p.y, p.r, 0, 7); g.fill(); }
      }
      g.globalAlpha = 1;
      g.restore();
    }
  });

  // ---- public surface (optional integration hooks; safe no-ops if unused) ---
  global.AKSeasons = {
    open: function () { try { openHub(global.AK_CTX); } catch (_e) {} },
    close: closeHub,
    // ONE FRONT DOOR (P1): a SINGLE idempotent DAILY faucet the lobby fires in one
    // tap -- grants Marks + advances the streak; returns {ok:false,err:'DONE'} if
    // already claimed this PT day. ctx defaults to the live AK_CTX.
    doCheckIn: function (ctx) { try { return doCheckIn(ctx || global.AK_CTX); } catch (_e) { return { ok:false, err:'ERR' }; } },
    checkInStatus: function (ctx) { try { return checkInStatus(ctx || global.AK_CTX); } catch (_e) { return { available:false, streak:0, nextStreak:0, reward:0 }; } },
    // WEATHER as a WORLD SIGNAL (P7): the legible, deterministic-by-PT-day signal +
    // its READ-ONLY econ modifiers for the farming / raid / encounter integration.
    getWeather: function (now) { try { return getWeather(now); } catch (_e) { return null; } },
    weatherMod: function (domain, now) { try { return weatherMod(domain, now); } catch (_e) { return 1; } },
    onMatchEnd: onMatchEnd,                 // OPTIONAL: grantMatchRewards may call this on a win
    current: function () { return { id: currentSeasonId(), chapter: currentChapter().key, name: currentChapter().name, week: weekOf(), daysLeft: daysLeft() }; },
    currentName: function () { try { return currentChapter().name; } catch (_e) { return ''; } },   // population.js probes this for the season word
    marks: function () { try { return marksOf(global.AK_CTX); } catch (_e) { return 0; } }
  };
})(typeof window !== 'undefined' ? window : globalThis);
