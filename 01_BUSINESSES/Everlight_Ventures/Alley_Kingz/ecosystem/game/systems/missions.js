/* game/systems/missions.js -- AK_SYSTEMS module: "missions" (THE FIXER keeper).
   ------------------------------------------------------------------------
   Marrow the Fixer runs jobs out of THE FIXER (THE_YARDS). After the job-merge,
   the Fixer's local deliveries live in the UNIFIED board model (window.AKMissions,
   systems/mission_active.js) right alongside the faction recruiter jobs -- ONE
   Hit List, ONE board, ONE turn-in flow. This module is now just the keeper
   interior + the LIVE server Hit List bridge:

     (A) THE FIXER KEEPER -- offers the next delivery, TAKES it (AKMissions.
         acceptFromFixer), shows progress, and TURNS it in (AKMissions.turnIn,
         the same flow the board uses). "OPEN THE BOARD" jumps to the unified job
         board (window.akOpenMissions), which carries BOTH the Fixer runs and the
         recruiter jobs. The delivery POOL + its grants/sinks live in
         mission_active.js now -- this file no longer owns the job model.

     (B) THE LIVE HIT LIST -- the server daily/weekly quests (same surface as
         shop/shop.html#hit2). Read + claimed through the LIVE `ak-quests` edge fn
         and paid out through the `ak_grants` rail (via AKSocial.claimGrants). The
         keeper shows how many are ready and claims them in place (surface-the-next),
         or opens the full Hit List screen.

     (C) DAILY CLAN DUTIES (P2) -- a perishable, faction-scoped daily hit list:
         3 duties keyed to the player's CLAN (win a tower match / run a raid / stand
         a Watch shift), deterministic by LOCAL PT day (mirrors seasons.js), with a
         visible RESET countdown. Each completed duty feeds Alley Pass XP through the
         live ak-quests -> AKSocial.claimGrants rail (Marvel Snap's daily->pass pipe)
         plus a small BONES receipt (soft currency, parity-safe). Lives BEFORE the
         AK_SYSTEMS guard so window.AKDuties is exposed for the HUD + the integration
         pass regardless of the registry. exposes: window.AKDuties.today() (the duty
         data) + window.AKDuties.getResetMs() (the HUD countdown).

   HARD-LAW COMPLIANCE:
   - Soft currency + bones ONLY (the delivery pool + its grants now live in
     mission_active.js). No gems, no $BCARDD / ALK in any reward. Card / handler
     names are reused BY NAME as canon flavor only -- never re-stat, never placeholder.
   - The Fixer's offer rotation + milestone ledger live in `p.missions` (created
     lazily ON WRITE by AKMissions); the active run rides `p.activeMissions` with
     the recruiter jobs. A zero-state profile stays byte-identical: nothing happens
     until you walk in and TAKE a job.
   - Headless-safe: bails if AK_SYSTEMS is absent; zero top-level DOM/localStorage;
     every server call is guarded by AKAccount presence and degrades gracefully offline.
   - Owns ONLY the FIXER interior (Section 4). Returns false for everything else.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';

  // ==========================================================================
  // (C) DAILY CLAN DUTIES (P2) -- exposed as window.AKDuties BEFORE the registry
  // guard so the HUD + integration pass can read the duty data + reset countdown
  // on any page that loads this file. Pure + deterministic-by-LOCAL-PT-day (no
  // client RNG): the 3 duties + their targets are byte-identical for everyone on
  // the same PT day and never flip mid-session. Progress rides p.duties, created
  // lazily ON WRITE via AK_ECON.mutateProfile and keyed by the PT dayKey, so a new
  // PT day silently retires yesterday's progress (PERISHABLE). A zero-state profile
  // stays byte-identical: nothing is written until a REAL duty event lands.
  // PARITY HARD-LAW: payout is Alley Pass XP fed through the live ak-quests ->
  // AKSocial.claimGrants rail (server-authoritative, no client minting) + a small
  // BONES receipt (soft currency, earned, never gems, never pay-to-win).
  // ==========================================================================
  var DAY_MS = 86400000;
  var PT_OFFSET_MS = 8 * 3600 * 1000;        // LOCAL PT anchor (UTC-8 / PST) -- mirrors seasons.js exactly
  var WEEK_MS = 7 * DAY_MS;                   // a WEEKLY duty cycle = 7 days
  var WK_EPOCH = Date.UTC(2026, 0, 5);        // Mon 2026-01-05 00:00 UTC -- mirrors seasons.js EPOCH so the weekly reset lands on the SAME boundary the season week (seasons.weekOf) turns over

  // canon clans (NAME CANON -- never rename). stray = no colors (canon start state).
  var CLAN = {
    zoomie_syndicate:  { id: 'zoomie_syndicate',  name: 'Zoomie Syndicate',  color: '#FF2E88', epithet: 'the Unbound',    home: 'The Strip',    rival: 'Boneguard Crew' },
    leashbreak_tactix: { id: 'leashbreak_tactix', name: 'Leashbreak Tactix', color: '#7B5CFF', epithet: 'the Hologhosts', home: 'Neon Heights', rival: 'K9 Circuitry' },
    boneguard_crew:    { id: 'boneguard_crew',    name: 'Boneguard Crew',    color: '#C9772E', epithet: 'the Rusted',     home: 'Factory Row',  rival: 'Zoomie Syndicate' },
    k9_circuitry:      { id: 'k9_circuitry',      name: 'K9 Circuitry',      color: '#00E0C0', epithet: 'the Crowned',    home: 'The Docks',    rival: 'Leashbreak Tactix' },
    stray:             { id: 'stray',             name: 'Stray',             color: '#c9a84c', epithet: 'no colors',      home: 'The Yards',    rival: 'the Old Pack' }
  };

  // the THREE canon duty actions (fixed slots). FLAVOR + target rotate by PT day.
  var DUTY_KINDS = [
    { kind: 'tower', metric: 'duty_tower', glyph: '⚔️',  verb: 'Win',   noun: 'a tower match',  xp: 30, bones: 8, targets: [1, 1, 2] },
    { kind: 'raid',  metric: 'duty_raid',  glyph: '🐾',  verb: 'Run',   noun: 'a raid',         xp: 25, bones: 6, targets: [1, 1, 2] },
    { kind: 'watch', metric: 'duty_watch', glyph: '🛡️', verb: 'Stand', noun: 'a Watch shift',  xp: 20, bones: 5, targets: [1, 2, 2] }
  ];

  // the WEEKLY duty layer -- SAME three canon kinds (so the SAME report()/reportTowerWin/
  // reportRaidRun/reportWatchShift bumps advance BOTH the daily and the weekly ladders,
  // no new call sites), just BIGGER targets and a BIGGER capstone reward: more Alley Pass
  // XP (via the same live ak-quests rail), a fat BONES receipt, and a CRATE KEY. Reuses the
  // daily `metric` so no new server quest is needed. Deterministic-by-WEEK (mirrors seasons.
  // weekOf's shape, keyed by the global week bucket) -- byte-identical for a clan all week.
  var WEEK_KINDS = [
    { kind: 'tower', metric: 'duty_tower', glyph: '⚔️',  verb: 'Win',   noun: 'tower matches', target: 15, xp: 300, bones: 60, keys: 1 },
    { kind: 'raid',  metric: 'duty_raid',  glyph: '🐾',  verb: 'Run',   noun: 'raids',         target: 10, xp: 260, bones: 50, keys: 1 },
    { kind: 'watch', metric: 'duty_watch', glyph: '🛡️', verb: 'Stand', noun: 'Watch shifts',  target: 8,  xp: 220, bones: 45, keys: 1 }
  ];

  // faction-scoped flavor -- {C}=clan {E}=epithet {H}=home district {R}=rival.
  // Canon lore woven in (THE CROWN BLOODLINE / the Old Pack / the Fence / the Watch).
  var FLAVOR = {
    tower: { titles: ['Hold the Lane', 'Lane Law', 'Tower Tribute'], pitches: [
      'Take the tower lane for {C}. {E} hold the block by winning, not barking.',
      'The Crown Bloodline watches every lane -- drag a win home for {C}.',
      'Win the lane and make {R} read your colors before {H} sleeps.' ] },
    raid:  { titles: ['Run the Block', 'Stash Run', 'Hit the Turf'], pitches: [
      'Run a raid in {C} colors -- crack a rival stash before the Fence shuts.',
      'The Old Pack ran on raids. Pull one for {C} and bank the haul.',
      'Hit {R} turf and run it back to {H}. Bones for the pack.' ] },
    watch: { titles: ['Stand the Watch', 'Hold the Gate', 'Night Shift'], pitches: [
      'Stand a Watch shift for {C}. {E} guard their own -- no block flips on your watch.',
      'The Watch keeps the Crown Bloodline honest. Cover {H} for {C}.',
      'Pull a Watch shift before {R} tests the gate. Eyes up, mutt.' ] }
  };
  // a Stray (no colors) gets the same 3 actions, framed as earning into the Pack.
  var STRAY_PITCH = {
    tower: 'Win a tower match and earn your first colors -- the Crown Bloodline only signs winners.',
    raid:  'Run a raid as a Stray. Prove you can take a block before a clan takes you.',
    watch: 'Stand a Watch shift in The Yards. Earn trust, earn colors.'
  };

  // WEEKLY flavor -- bigger, season-scale framing. {T}=target {C}=clan {E}=epithet {H}=home {R}=rival.
  var WEEK_FLAVOR = {
    tower: { titles: ['Season of the Lane', 'Warlord of the Block', 'Tower Dynasty'], pitches: [
      'Win {T} tower matches this week for {C}. {E} build dynasties, not lucky streaks.',
      'The Crown Bloodline crowns the crew that owns the lane all week -- {T} wins for {C} before {H} sleeps.' ] },
    raid:  { titles: ['Week of Raids', 'The Long Haul', 'Stash Season'], pitches: [
      'Run {T} raids this week for {C}. The Old Pack was built on the long haul.',
      'Bleed {R} dry -- {T} raids banked back to {H} before the week turns.' ] },
    watch: { titles: ['The Long Watch', 'Season of the Gate', 'Nightwardens'], pitches: [
      'Stand {T} Watch shifts this week for {C}. No block flips on a long watch.',
      'Hold {H} all week -- {T} Watch shifts keep the Crown Bloodline honest against {R}.' ] }
  };
  var WEEK_STRAY_PITCH = {
    tower: 'Win {T} tower matches this week -- a Stray who wins all week earns colors, not scraps.',
    raid:  'Run {T} raids this week as a Stray. Prove the Pack should sign you.',
    watch: 'Stand {T} Watch shifts in The Yards this week. Earn trust, earn colors.'
  };

  function dnow() { return Date.now(); }
  function ptDayIndex(now) { return Math.floor(((now || dnow()) - PT_OFFSET_MS) / DAY_MS); }            // PT day bucket -- rolls at PT midnight
  function dutyDayKey(now) { return new Date((now || dnow()) - PT_OFFSET_MS).toISOString().slice(0, 10); } // LOCAL PT calendar day, YYYY-MM-DD
  function getResetMs(now) { now = now || dnow(); var next = (ptDayIndex(now) + 1) * DAY_MS + PT_OFFSET_MS; return Math.max(0, next - now); }
  function resetLabel(now) {
    var ms = getResetMs(now), m = Math.floor(ms / 60000), h = Math.floor(m / 60);
    if (h >= 1) return h + 'h ' + (m % 60) + 'm';
    if (m >= 1) return m + 'm';
    return '<1m';
  }
  // WEEKLY clock -- global monotonic week bucket anchored to seasons.js EPOCH (never
  // cycles 1-6, so it is a unique persistence key). It turns over on the SAME instant
  // seasons.weekOf does (42-day chapter = 6 whole weeks), so week-scoped progress resets
  // exactly on a new weekOf. weekOfNum() re-derives the 1..6 chapter week for display.
  function weekIndex(now) { return Math.floor(((now || dnow()) - WK_EPOCH) / WEEK_MS); }
  function weekKey(now) { return 'W' + weekIndex(now); }
  function weekOfNum(now) { return (((weekIndex(now) % 6) + 6) % 6) + 1; }
  function weeklyResetMs(now) { now = now || dnow(); var next = (weekIndex(now) + 1) * WEEK_MS + WK_EPOCH; return Math.max(0, next - now); }
  function weeklyResetLabel(now) {
    var ms = weeklyResetMs(now), h = Math.floor(ms / 3600000), d = Math.floor(h / 24);
    if (d >= 1) return d + 'd ' + (h % 24) + 'h';
    if (h >= 1) return h + 'h';
    var m = Math.floor(ms / 60000);
    return (m >= 1 ? m + 'm' : '<1m');
  }
  // deterministic 32-bit hash (mulberry32 mix) -- NO client RNG, byte-identical per (PT day, slot, clan)
  function hash32(x) { x = x | 0; x = (x + 0x6D2B79F5) | 0; var t = x; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return (t ^ (t >>> 14)) >>> 0; }
  function clanCode(id) { var s = 0; id = String(id || 'stray'); for (var i = 0; i < id.length; i++) s = (s + id.charCodeAt(i) * (i + 1)) | 0; return s; }

  function econD() { try { return global.AK_ECON || null; } catch (_e) { return null; } }
  function playerClanId() {
    try { if (global.localStorage) { var c = localStorage.getItem('ak_clan'); if (c && CLAN[c]) return c; } } catch (_e) {}
    try { var e = econD(), p = e && e.loadProfile && e.loadProfile(); var f = p && (p.clan || p.faction); if (f && CLAN[f]) return f; } catch (_e) {}
    return 'stray';                          // a Stray with no colors (canon-correct starting state)
  }
  function clanObj() { return CLAN[playerClanId()] || CLAN.stray; }
  function fill(s, cl) { return String(s).replace(/\{C\}/g, cl.name).replace(/\{E\}/g, cl.epithet).replace(/\{H\}/g, cl.home).replace(/\{R\}/g, cl.rival); }
  function fillW(s, cl, t) { return fill(s, cl).replace(/\{T\}/g, t); }   // weekly: also fill {T}=target

  // read p.duties for TODAY only (falsy-default; NO write). yesterday's progress is dead.
  function dutyStateRead() {
    try {
      var e = econD(), p = e && e.loadProfile && e.loadProfile(), d = p && p.duties;
      if (d && d.day === dutyDayKey()) return d;
    } catch (_e) {}
    return { day: dutyDayKey(), prog: {}, done: {} };
  }

  function buildDuty(def, slot, cl, st, now) {
    var h = hash32(ptDayIndex(now) * 131 + slot * 1009 + clanCode(cl.id));
    var bank = FLAVOR[def.kind];
    var title = bank.titles[h % bank.titles.length];
    var pitch = (cl.id === 'stray') ? STRAY_PITCH[def.kind] : fill(bank.pitches[(h >>> 8) % bank.pitches.length], cl);
    var target = def.targets[(h >>> 16) % def.targets.length];
    var prog = Math.min(target, (st.prog && st.prog[def.kind]) | 0);
    var done = !!(st.done && st.done[def.kind]) || prog >= target;
    return {
      kind: def.kind, metric: def.metric, glyph: def.glyph,
      title: title, desc: pitch, action: def.verb + ' ' + def.noun,
      clan: cl.id, clanName: cl.name, color: cl.color,
      target: target, prog: prog, done: done,
      xp: def.xp * target, bones: def.bones
    };
  }
  // today() -> the 3 live duties (reads the profile; never writes). ctx is ignored.
  function today() {
    var cl = clanObj(), st = dutyStateRead(), now = dnow();
    return DUTY_KINDS.map(function (def, i) { return buildDuty(def, i, cl, st, now); });
  }
  function summary() {
    var list = today(), done = 0;
    list.forEach(function (d) { if (d.done) done++; });
    return { total: list.length, done: done, allDone: done >= list.length, resetMs: getResetMs(), resetLabel: resetLabel(), clanName: list[0] ? list[0].clanName : 'Stray' };
  }

  // ---- WEEKLY ladder (same three kinds, week-scoped) ------------------------
  // Reads p.weekly for THIS week only (falsy-default; NO write). Last week's progress
  // is dead the instant the weekKey changes -- an untouched profile reads the empty
  // default, exactly like the daily p.duties pattern.
  function weekStateRead() {
    try {
      var e = econD(), p = e && e.loadProfile && e.loadProfile(), w = p && p.weekly;
      if (w && w.week === weekKey()) return w;
    } catch (_e) {}
    return { week: weekKey(), prog: {}, done: {} };
  }
  function buildWeekly(def, slot, cl, st, now) {
    var h = hash32(weekIndex(now) * 2609 + slot * 7793 + clanCode(cl.id));
    var bank = WEEK_FLAVOR[def.kind];
    var title = bank.titles[h % bank.titles.length];
    var pitch = (cl.id === 'stray') ? fillW(WEEK_STRAY_PITCH[def.kind], cl, def.target)
                                    : fillW(bank.pitches[(h >>> 8) % bank.pitches.length], cl, def.target);
    var target = def.target;
    var prog = Math.min(target, (st.prog && st.prog[def.kind]) | 0);
    var done = !!(st.done && st.done[def.kind]) || prog >= target;
    return {
      kind: def.kind, metric: def.metric, glyph: def.glyph,
      title: title, desc: pitch, action: def.verb + ' ' + def.target + ' ' + def.noun,
      clan: cl.id, clanName: cl.name, color: cl.color,
      target: target, prog: prog, done: done,
      xp: def.xp, bones: def.bones, keys: def.keys | 0
    };
  }
  // thisWeek() -> the 3 live weekly duties (reads the profile; never writes).
  function thisWeek() {
    var cl = clanObj(), st = weekStateRead(), now = dnow();
    return WEEK_KINDS.map(function (def, i) { return buildWeekly(def, i, cl, st, now); });
  }
  function weeklySummary() {
    var list = thisWeek(), done = 0;
    list.forEach(function (d) { if (d.done) done++; });
    return { total: list.length, done: done, allDone: done >= list.length, resetMs: weeklyResetMs(), resetLabel: weeklyResetLabel(), weekOf: weekOfNum(), clanName: list[0] ? list[0].clanName : 'Stray' };
  }

  // the documented daily->pass pipe: bump the live ak-quests counter, then pull any
  // queued pass/grant rewards through AKSocial.claimGrants. The server is the SOLE
  // authority for Alley Pass XP (no client minting -- parity-safe). Signed-out is a
  // graceful no-op (AKQuests/AKSocial self-gate on session), exactly like quests.js.
  function feedPassRail(metric) {
    try { if (global.AKQuests && global.AKQuests.reportEvent) global.AKQuests.reportEvent(metric, 1); } catch (_e) {}
    try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_e) {}
  }
  // record ONE real duty event (the integration pass calls this from the real tower-
  // win / raid / Watch triggers). n defaults to 1. Pays out exactly once per duty per
  // PT day (the done-guard). Returns the updated duty, or null when it cannot record.
  function report(kind, n) {
    var def = null, slot = -1, i;
    for (i = 0; i < DUTY_KINDS.length; i++) if (DUTY_KINDS[i].kind === kind) { def = DUTY_KINDS[i]; slot = i; break; }
    if (!def) return null;
    var e = econD(); if (!e || !e.mutateProfile) return null;
    n = (n | 0) || 1;
    var cl = clanObj(), now = dnow();
    var target = buildDuty(def, slot, cl, dutyStateRead(), now).target;

    // the WEEKLY twin of this kind (same event, bigger target). Looked up here so the
    // SAME bump advances daily AND weekly inside ONE mutateProfile -- no new call sites.
    var wdef = null, wslot = -1;
    for (i = 0; i < WEEK_KINDS.length; i++) if (WEEK_KINDS[i].kind === kind) { wdef = WEEK_KINDS[i]; wslot = i; break; }
    var wtarget = wdef ? buildWeekly(wdef, wslot, cl, weekStateRead(), now).target : 0;

    var justDone = false, paidXp = 0, paidBones = 0;
    var wJustDone = false, wPaidXp = 0, wPaidBones = 0, wPaidKeys = 0;
    e.mutateProfile(function (p) {
      var dk = dutyDayKey(now);
      if (!p.duties || typeof p.duties !== 'object' || p.duties.day !== dk) p.duties = { day: dk, prog: {}, done: {} };
      var d = p.duties;
      if (!d.prog || typeof d.prog !== 'object') d.prog = {};
      if (!d.done || typeof d.done !== 'object') d.done = {};
      var cur = (d.prog[kind] | 0) + n; if (cur > target) cur = target;
      d.prog[kind] = cur;
      if (cur >= target && !d.done[kind]) {                 // first crossing -> pay once
        d.done[kind] = 1; justDone = true;
        paidBones = def.bones; paidXp = def.xp * target;
        p.bones = Math.max(0, (p.bones | 0) + paidBones);   // soft-currency receipt (parity-safe)
      }
      // WEEKLY ladder -- week-scoped, resets on a new weekOf. Same lazy falsy-safe shape
      // as p.duties: nothing is written for an untouched profile until a real event lands.
      if (wdef) {
        var wk = weekKey(now);
        if (!p.weekly || typeof p.weekly !== 'object' || p.weekly.week !== wk) p.weekly = { week: wk, prog: {}, done: {} };
        var w = p.weekly;
        if (!w.prog || typeof w.prog !== 'object') w.prog = {};
        if (!w.done || typeof w.done !== 'object') w.done = {};
        var wcur = (w.prog[kind] | 0) + n; if (wcur > wtarget) wcur = wtarget;
        w.prog[kind] = wcur;
        if (wcur >= wtarget && !w.done[kind]) {             // first weekly crossing -> pay once
          w.done[kind] = 1; wJustDone = true;
          wPaidBones = wdef.bones; wPaidXp = wdef.xp; wPaidKeys = wdef.keys | 0;
          p.bones = Math.max(0, (p.bones | 0) + wPaidBones);            // bigger BONES receipt
          if (wPaidKeys > 0) p.keys = Math.max(0, (p.keys | 0) + wPaidKeys);   // + a CRATE KEY
        }
      }
    });
    if (justDone) {
      feedPassRail(def.metric);                             // Alley Pass XP via the live rail
      try {
        var ctx = global.AK_CTX, t = buildDuty(def, slot, cl, dutyStateRead(), now);
        if (ctx && ctx.showBanner) ctx.showBanner(def.glyph + ' Duty squared: ' + t.title + ' -- +' + paidXp + ' Pass XP, +' + paidBones + ' bones.', 2.4);
        if (global.akHud && global.akHud.tick) global.akHud.tick();   // refresh the bones chip
      } catch (_e) {}
    }
    if (wJustDone) {
      feedPassRail(wdef.metric);                            // weekly capstone -> same live Pass rail
      try {
        var wctx = global.AK_CTX, wt = buildWeekly(wdef, wslot, cl, weekStateRead(), now);
        var kmsg = wPaidKeys > 0 ? (', +' + wPaidKeys + ' crate key' + (wPaidKeys === 1 ? '' : 's')) : '';
        if (wctx && wctx.showBanner) wctx.showBanner(wdef.glyph + ' Weekly duty squared: ' + wt.title + ' -- +' + wPaidXp + ' Pass XP, +' + wPaidBones + ' bones' + kmsg + '.', 3.0);
        if (global.akHud && global.akHud.tick) global.akHud.tick();   // refresh the bones + keys chips
      } catch (_e) {}
    }
    if (justDone || wJustDone) {
      try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_e) {}
    }
    return buildDuty(def, slot, cl, dutyStateRead(), now);
  }

  // window.* surface for the HUD + the integration pass (clear, deterministic, read-only
  // except report*, which writes only on a real event).
  global.AKDuties = {
    today: today, list: today, summary: summary,
    getResetMs: getResetMs, resetLabel: resetLabel,
    // WEEKLY surface for the HUD (same report* call sites feed both ladders).
    thisWeek: thisWeek, weekly: thisWeek, weeklyList: thisWeek, weeklySummary: weeklySummary,
    weeklyResetMs: weeklyResetMs, weeklyResetLabel: weeklyResetLabel, weekOf: weekOfNum,
    // AK-DUTYWIRE 2026-07-18: the LIVE call sites (these three were orphaned -- exported
    // with ZERO callers, so 2 of 3 dailies, 2 of 3 weeklies and 2 crate keys a week could
    // never be claimed). Do not orphan them again; each fires exactly once per real run:
    //   reportTowerWin   <- game.html, on a won tower match
    //   reportRaidRun    <- raidscene.js creditRaidDuty(), from the WON branch of
    //                       target.onResult (the one funnel every raid path lands in);
    //                       also exported as AK_RAIDSCENE.creditRaidDuty for the two
    //                       raid paths that build their own onResult (raidmap/worldmap)
    //   reportWatchShift <- raid.js endDefense(true), the night-siege Watch shift, once
    //                       per night cycle (shares the loot's anti-farm window)
    report: report,
    reportTowerWin:  function (n) { return report('tower', n || 1); },
    reportRaidRun:   function (n) { return report('raid',  n || 1); },
    reportWatchShift:function (n) { return report('watch', n || 1); },
    clanId: playerClanId, clan: clanObj,
    KINDS: DUTY_KINDS.map(function (k) { return { kind: k.kind, action: k.verb + ' ' + k.noun, metric: k.metric }; }),
    WEEK_KINDS: WEEK_KINDS.map(function (k) { return { kind: k.kind, action: k.verb + ' ' + k.target + ' ' + k.noun, metric: k.metric, target: k.target }; })
  };

  if (!global.AK_SYSTEMS) return;            // hub-only; node harness / pages without the registry no-op

  var BID = 'FIXER';                          // the one building this wave owns (Section 4)
  var KEEPER = { name: 'Marrow the Fixer', glyph: '📋' }; // clipboard -- he runs the job board
  var PIP_COLOR = '#ff9d5c';                  // matches the FIXER building tint in index.html

  // ---- module-private state (NO profile state lives here) -------------------
  var S = { server: null, fetching: false, fetched: false, open: false,
            ready: false, _acc: 0, _now: 0 };

  // ---- the unified job model (mission_active.js) ----------------------------
  function akm() { return global.AKMissions || null; }

  // ---- LIVE HIT LIST server bridge (ak-quests edge fn + ak_grants rail) -----
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me()  { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function call(fn, body) {                            // mirrors quests.js / social.js call()
    var sb = sbc(); if (!sb) return Promise.resolve({ ok: false, error: 'offline' });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var c = r.error && r.error.context;
        if (c && typeof c.json === 'function') return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: (r.error && r.error.message) || 'error' };
      }
      return r.data || { ok: false, error: 'empty' };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }
  function fetchServer(ctx, cb) {                      // LIVE: ak-quests "get" -> summarize claimable/done
    if (S.fetching) { if (cb) cb(); return; }
    if (!me()) { S.server = null; S.fetched = true; if (cb) cb(); return; }
    S.fetching = true;
    call('ak-quests', { action: 'get' }).then(function (r) {
      S.fetching = false; S.fetched = true;
      if (r && r.ok && r.quests) {
        var claimable = 0, done = 0;
        r.quests.forEach(function (q) { if (q.claimable) claimable++; if (q.claimed) done++; });
        S.server = { quests: r.quests, claimable: claimable, done: done, total: r.quests.length };
      } else S.server = null;
      if (cb) cb();
    }, function () { S.fetching = false; S.fetched = true; S.server = null; if (cb) cb(); });
  }
  function openHitList(ctx) {
    // Prefer the in-page LIVE Hit List overlay (ak-quests + ak_grants) if it is loaded.
    try { if (global.AKQuests && global.AKQuests.open) { global.AKQuests.open(); return; } } catch (_e) {}
    // Fallback: navigate to the canonical Hit List shop surface, preserving the hub
    // zone + spot the exact way the host doEnter() does (return restores position).
    try {
      localStorage.setItem('ak_hub_zone', ctx.zoneId);
      localStorage.setItem('ak_hub_pos', JSON.stringify({ x: Math.round(ctx.me.x), y: Math.round(ctx.me.y) }));
      localStorage.setItem('ak_returning', '1');
    } catch (_e) {}
    if (ctx.showBanner) ctx.showBanner('Opening the Hit List…', 2);
    try { window.location.href = 'shop/shop.html#hit2'; } catch (_e) {}
  }
  // read out today's CLAN DUTIES at the keeper -- clan-scoped, with the reset clock.
  // (Reads the live AKDuties surface; the duties FEED the Hit List/Pass that the
  // HIT LIST button opens, so this stays a quick standup, not a second screen.)
  function openDuties(ctx) {
    try {
      var D = global.AKDuties; if (!D || !D.summary) { openHitList(ctx); return; }
      var dz = D.summary(), list = D.today();
      var msg = dz.clanName + ' duties -- resets in ' + dz.resetLabel + '.  ';
      msg += list.map(function (d) {
        return (d.done ? '✓ ' : '▢ ') + d.action + (d.done ? ' [squared]' : ' (' + d.prog + '/' + d.target + ', +' + d.xp + ' Pass XP)');
      }).join('   /   ');
      if (ctx && ctx.showBanner) ctx.showBanner(msg, 6);
    } catch (_e) { openHitList(ctx); }
  }
  function claimAllServer(ctx) {                       // claim every ready server quest in place, then pay grants
    var srv = S.server;
    if (!srv || !srv.quests) { openHitList(ctx); return; }
    var ready = srv.quests.filter(function (q) { return q.claimable; });
    if (!ready.length) { openHitList(ctx); return; }
    var i = 0;
    (function step() {
      if (i >= ready.length) {
        try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_e) {}
        if (ctx.showBanner) ctx.showBanner('Hit List paid out -- check your stash.', 1.8);
        fetchServer(ctx, function () { if (isOpen()) renderFixer(ctx); });
        return;
      }
      call('ak-quests', { action: 'claim', quest_id: ready[i++].id }).then(step, step);
    })();
  }

  // ---- open-state guard (async re-renders must NOT pop the panel back open) -
  // onTick fires ONLY while the interior is closed (host gate), so it clears
  // S.open; onEnterBuilding sets it true and onTick is frozen during the visit.
  function isOpen() {
    try { var el = document.getElementById('interior'); return S.open && !!el && el.style.display !== 'none'; } catch (_e) { return false; }
  }

  // ---- the keeper interior (re-rendered after every action) -----------------
  // The Fixer's delivery state comes from the unified model via AKMissions.fixerView;
  // TAKE / NEXT / TURN IN / DROP all delegate to AKMissions so there is ONE flow.
  function renderFixer(ctx) {
    var M = akm();
    var view = (M && M.fixerView) ? M.fixerView(ctx) : { hasJob: false, offer: false };
    var buttons = [], line;

    if (!view.hasJob) {
      // No run taken -- the Fixer is offering one.
      line = (view.offer ? (view.pitch + '  Pays ' + view.rewardPreview + '.') : "Quiet day. Check back, mutt.")
             + "  Bones feed your handlers' skill trees.";
      if (view.offer) buttons.push({ label: 'TAKE THE JOB', primary: true, onClick: function (c) { if (M && M.acceptFromFixer) M.acceptFromFixer(c); renderFixer(c); } });
      buttons.push({ label: 'NEXT JOB', primary: false, onClick: function (c) { if (M && M.fixerNext) M.fixerNext(c); renderFixer(c); } });
    } else if (view.ready) {
      line = "Job's done. Bring it in -- " + view.rewardPreview + " on the table.";
      buttons.push({ label: 'TURN IN  ▸  ' + view.rewardPreview, primary: true, onClick: function (c) {
        if (M && M.turnIn) { var r = M.turnIn(view.mid, c); if (r && r.ok && c.showBanner) c.showBanner('Squared up.', 1.6); }
        renderFixer(c);   // next offer surfaces immediately (Reward Flow)
      } });
      buttons.push({ label: 'DROP JOB', primary: false, onClick: function (c) { if (M && M.abandon) M.abandon(view.mid, c); renderFixer(c); } });
    } else {
      line = view.pitch + '   [' + Math.min(view.prog, view.target) + '/' + view.target + ' ' + view.res + ']';
      buttons.push({ label: Math.min(view.prog, view.target) + '/' + view.target + ' ' + (view.res || '').toUpperCase(), primary: true, disabled: true, onClick: function () {} });
      buttons.push({ label: 'DROP JOB', primary: false, onClick: function (c) { if (M && M.abandon) M.abandon(view.mid, c); renderFixer(c); } });
    }

    // P2 DAILY CLAN DUTIES -- perishable, faction-scoped, with the RESET clock. The
    // line is the at-a-glance checklist; the button reads them out in full. Duties
    // feed the Alley Pass via the live ak-quests -> AKSocial.claimGrants rail.
    try {
      var D = global.AKDuties;
      if (D && D.summary) {
        var dz = D.summary(), dlist = D.today(), checks = [];
        for (var qi = 0; qi < dlist.length; qi++) checks.push((dlist[qi].done ? '✓ ' : '▢ ') + dlist[qi].title + (dlist[qi].done ? '' : ' ' + dlist[qi].prog + '/' + dlist[qi].target));
        line += '   CLAN DUTIES (resets in ' + dz.resetLabel + '): ' + checks.join('  |  ') + '.';
        buttons.push({ label: 'CLAN DUTIES ' + dz.done + '/' + dz.total, primary: false, onClick: function (c) { openDuties(c); } });
      }
    } catch (_e) {}

    // Button: the UNIFIED board (Fixer runs + recruiter jobs in one list, one turn-in).
    buttons.push({ label: 'OPEN THE BOARD', primary: false, onClick: function (c) { try { if (global.akOpenMissions) global.akOpenMissions(); } catch (_e) {} } });

    // Button: the LIVE Hit List (server quests). Claim-in-place when ready, else open
    // the full screen. The count is a goal-gradient nudge.
    var srv = S.server, hitLabel, hitOnClick;
    if (!me()) {
      hitLabel = 'THE HIT LIST'; hitOnClick = function (c) { openHitList(c); };
    } else if (srv && srv.claimable > 0) {
      hitLabel = 'CLAIM HIT LIST (' + srv.claimable + ')'; hitOnClick = function (c) { claimAllServer(c); };
    } else if (srv) {
      hitLabel = 'HIT LIST  ' + srv.done + '/' + srv.total; hitOnClick = function (c) { openHitList(c); };
    } else {
      hitLabel = 'THE HIT LIST'; hitOnClick = function (c) { openHitList(c); };
    }
    buttons.push({ label: hitLabel, primary: false, onClick: hitOnClick });

    ctx.ui.keeperCard({ place: 'THE FIXER', glyph: KEEPER.glyph, name: KEEPER.name, line: line, buttons: buttons });
  }

  // a "job ready" pip over THE FIXER (THE_YARDS) when a delivery turn-in or a Hit
  // List claim is waiting. Readiness comes from the unified model (Fixer run ready)
  // or a claimable server quest.
  function fixerReady(ctx) {
    try { var M = akm(), fv = (M && M.fixerView) ? M.fixerView(ctx) : null; return !!(fv && fv.hasJob && fv.ready); } catch (_e) { return false; }
  }

  // ---- the AK_SYSTEMS module ------------------------------------------------
  global.AK_SYSTEMS.register({
    id: 'missions',

    init: function (ctx) {
      // No per-frame work. Pre-roll the readiness flag from the unified model so the
      // FIXER pip can light up on the first frame for a returning player.
      S.ready = fixerReady(ctx);
    },

    onEnterBuilding: function (b, ctx) {
      if (!b || b.id !== BID) return false;            // own ONLY the FIXER (Section 4)
      S.open = true;
      renderFixer(ctx);                                // synchronous: panel is ready before we return true
      fetchServer(ctx, function () { if (isOpen()) renderFixer(ctx); }); // live Hit List fills in async
      return true;                                     // host shows the panel + suppresses the default keeper
    },

    onTick: function (dt, ctx) {
      S.open = false;                                  // interior is closed whenever onTick runs (host gate)
      S._acc += dt;
      if (S._acc >= 1.0) {
        S._acc = 0;
        S._now = (global.performance && performance.now) ? performance.now() : Date.now();
        try {
          if (!S.fetched && !S.fetching && me()) fetchServer(ctx);   // one lazy fetch so the pip reflects server quests
          S.ready = fixerReady(ctx) || (!!(S.server && S.server.claimable > 0));
        } catch (_e) { S.ready = false; }
      }
    },

    // a "job ready" pip over THE FIXER (THE_YARDS) when a turn-in or a Hit List
    // claim is waiting -- the Monopoly-GO goal-gradient pull back to the keeper.
    onDrawWorld: function (ctx) {
      if (!S.ready) return;
      if (!ctx.activeZone || ctx.activeZone.id !== 'THE_YARDS') return;
      var bs = ctx.activeZone.buildings; if (!bs) return;
      var b = null, i;
      for (i = 0; i < bs.length; i++) { if (bs[i].id === BID) { b = bs[i]; break; } }
      if (!b) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var X = ctx.world.wx(b.x), Y = ctx.world.wy(b.y - (b.h ? b.h / 2 : 48) - 22);
      if (X < -40 || X > W + 40 || Y < -40 || Y > H + 40) return;
      var now = S._now || ((global.performance && performance.now) ? performance.now() : Date.now());
      var pulse = 0.55 + 0.45 * Math.sin(now / 300);
      g.save();
      g.globalAlpha = pulse; g.shadowColor = PIP_COLOR; g.shadowBlur = 14; g.fillStyle = PIP_COLOR;
      g.beginPath(); g.arc(X, Y, 9, 0, 7); g.fill();
      g.shadowBlur = 0; g.globalAlpha = 1;
      g.font = 'bold 13px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#15110a';
      g.fillText('!', X, Y + 0.5);
      g.restore();
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
