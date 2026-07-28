/* game/systems/shields.js -- AK_SYSTEMS module: SHIELDS / VILLAGE GUARD / PERSONAL BREAK.
 * AK-SHIELDS 2026-07-18
 * ---------------------------------------------------------------------------
 * THE ATTACKABILITY LAYER. This module answers exactly one question, and every
 * other base-layer system asks it: CAN THIS PLAYER BE ATTACKED RIGHT NOW?
 *
 * Without it the base layer is unplayable. A player who logs in and stays online
 * would be farmed continuously by every raider who can see their block, and a
 * player who logs off would come back to nothing. The three timers below are the
 * standard Clash-of-Clans answer, ported to Alley Kingz language:
 *
 *   1. SHIELD  -- granted automatically after you LOSE a defense, scaled by how
 *      badly your block got wrecked (12h at 30% destruction rising to 16h at
 *      90%+). Below 30% the raider barely scratched you, so no shield: that stops
 *      a friendly tap-in from buying you half a day of immunity.
 *
 *   2. BURN    -- a shield is NOT a free farming window. Raiding while shielded
 *      does not get blocked, it BURNS shield time, and the price escalates per
 *      attack (3h, then 4h, then 5h). Attack under a shield often enough and you
 *      have no shield left. Attacking under a shield ALSO forfeits the village
 *      guard below, so there is no way to farm from behind protection for free.
 *
 *   3. VILLAGE GUARD -- when a shield runs out you do not fall straight into the
 *      open. A shorter guard (1/8 of the shield that just ended, clamped 30m..3h)
 *      keeps you unattackable, and during guard you can raid FREELY with no burn.
 *      That is the window the game wants you to play in.
 *
 *   4. PERSONAL BREAK -- the anti-dodge timer. Staying online forever is itself a
 *      defense (raiders skip live bases), so after 3h of continuous UNPROTECTED
 *      online time the game forces a 30m break. Shielded and guarded time do not
 *      count toward it, which is the whole point: protection is the intended way
 *      to be safe, not permanent presence.
 *
 * ONE SHARED STATE, MANY WRITERS (the hard law of this repo).
 * There is already a shield field and there are already TWO writers on it:
 *     game/systems/raid.js  -- setShield()/buyShield(), the 5-tier gold+gem ladder
 *     game/shop/shop.js     -- AK-SHIELD "THE WATCH", coin tiers
 * Both write p.raid.shieldUntil, and economy.js zero-states p.raid as
 * { shieldUntil:0, lastRaid:0, revenge:[] }. This module EXTENDS that record, it
 * does not fork it. A shield bought in the shop is read here as a shield; a shield
 * granted here is read by raid.js shieldActive() as a shield. Two shield systems
 * disagreeing about whether a player is protected would be a vicious bug, so there
 * is exactly one field and everybody reads it.
 *
 * Fields added to p.raid (all falsy-default, written only when something actually
 * happens, so the zero-state profile stays byte-identical):
 *     guardUntil  -- village guard expiry (0 = none). Precomputed at grant time so
 *                    the guard resolves LAZILY with no ticking and no online client.
 *     burns       -- attacks made under the CURRENT shield (drives the burn ladder)
 *     shieldFrom  -- when the current shield was granted (UI only)
 *     lastRaided  -- when we last LOST a defense (distinct from raid.lastRaid,
 *                    which raid.js sets when YOU launch a raid)
 *     onlineSince -- start of the current unprotected online run (0 = not running)
 *     onlineLast  -- last heartbeat, so an idle gap ends the run instead of banking it
 *     breakUntil  -- forced-break expiry (0 = none)
 *     breaks      -- lifetime forced breaks served (telemetry)
 *
 * PURE FIRST. All four required entry points are pure time math over a plain
 * object, no DOM, no clock capture, no randomness: pass `now` and the answer is
 * deterministic. That is what lets the same file be require()d by a node harness
 * today and run on a server tick tomorrow when attackability has to be authoritative
 * (a client that decides its own shield is a client that never gets raided).
 *
 * PERSISTENCE follows the economy.js raidDamage() convention exactly:
 *     fn(p, ...)  -> mutates the profile you passed IN PLACE, does not save.
 *                    The caller persists (it is already inside a mutateProfile).
 *     fn(null,...)-> runs its own atomic load -> apply -> save through
 *                    AK_ECON.mutateProfile and returns the same result.
 * localStorage is never touched directly here. A parallel profile engine writing
 * storage behind AK_ECON's back is where a whole class of save-loss bugs in this
 * repo came from, so every write in this file goes through mutateProfile.
 * ========================================================================== */
(function (global) {
  'use strict';

  var MIN_MS = 60 * 1000;
  var HOUR_MS = 60 * MIN_MS;

  // ---- 1. shield grant curve -------------------------------------------------
  // 30% destruction -> 12h, 60% -> 14h, 90%+ -> 16h. Linear between the anchors.
  // Under 30% the raider did not really take the block, so nothing is granted.
  var SHIELD_MIN_PCT = 30, SHIELD_MAX_PCT = 90;
  var SHIELD_MIN_MS = 12 * HOUR_MS, SHIELD_MAX_MS = 16 * HOUR_MS;

  // ---- 2. burn ladder --------------------------------------------------------
  // Cost of raiding while shielded, escalating per attack under the SAME shield.
  // The last entry repeats forever, so attack 4 costs the same as attack 3.
  var BURN_LADDER = [3 * HOUR_MS, 4 * HOUR_MS, 5 * HOUR_MS];

  // ---- 3. village guard ------------------------------------------------------
  var GUARD_FRAC = 0.125;                     // 1/8 of the shield that just ended
  var GUARD_MIN_MS = 30 * MIN_MS, GUARD_MAX_MS = 3 * HOUR_MS;

  // ---- 4. personal break -----------------------------------------------------
  var ONLINE_LIMIT_MS = 3 * HOUR_MS;          // unprotected online time before a break is forced
  var BREAK_MS = 30 * MIN_MS;                 // how long the forced break lasts
  var IDLE_GAP_MS = 5 * MIN_MS;               // no heartbeat this long = you left, run resets

  // hub heartbeat cadence (seconds of ctx tick). 30s granularity against a 5m idle
  // gap and a 3h limit is plenty, and it keeps the profile write off the frame path.
  var BEAT_S = 30;

  // ---- module-local runtime (NEVER persisted) --------------------------------
  var M = { ctx: null, acc: 0, phase: null, onBreak: false, booted: false };

  // ==========================================================================
  // helpers
  // ==========================================================================
  function nowMs() { return Date.now(); }
  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  /* READ view of the raid record. Never creates anything, so a read can never
     dirty a zero-state profile. Mirrors raid.js raidOf(). */
  function raidOf(p) { return (p && p.raid && typeof p.raid === 'object') ? p.raid : null; }

  /* WRITE view. Creates the record in the SAME shape economy.js zero-states it
     with, so a profile touched here is indistinguishable from one touched by
     raid.js or shop.js. */
  function ensureRaid(p) {
    if (!p.raid || typeof p.raid !== 'object') p.raid = { shieldUntil: 0, lastRaid: 0, revenge: [] };
    return p.raid;
  }

  /* The persistence seam (economy.js raidDamage convention).
     p given  -> apply in place, caller saves.
     p absent -> atomic load/apply/save through AK_ECON.mutateProfile.
     No AK_ECON (node harness) -> applies to a throwaway so callers never crash. */
  function withProfile(p, fn) {
    if (p && typeof p === 'object') return fn(p);
    var econ = global.AK_ECON, out = null;
    if (!econ || !econ.mutateProfile) return fn({});
    econ.mutateProfile(function (pp) { out = fn(pp); });
    return out;
  }

  function fmtDur(ms) {
    if (!(ms > 0)) return '0m';
    var h = Math.floor(ms / HOUR_MS), m = Math.round((ms % HOUR_MS) / MIN_MS);
    if (m === 60) { h += 1; m = 0; }
    return (h ? h + 'h ' : '') + m + 'm';
  }

  // ==========================================================================
  // PURE: the four required entry points + their supporting math
  // ==========================================================================

  /* grantShieldFor(destructionPct) -> ms
     How much shield a successful raid on you is worth. PURE, no state at all.
     0..29% -> 0 (no shield), 30% -> 12h, 60% -> 14h, 90..100% -> 16h. */
  function grantShieldFor(destructionPct) {
    var pct = clamp(num(destructionPct, 0), 0, 100);
    if (pct < SHIELD_MIN_PCT) return 0;
    var t = (Math.min(pct, SHIELD_MAX_PCT) - SHIELD_MIN_PCT) / (SHIELD_MAX_PCT - SHIELD_MIN_PCT);
    return Math.round(SHIELD_MIN_MS + t * (SHIELD_MAX_MS - SHIELD_MIN_MS));
  }

  /* guardMsFor(shieldMs) -> ms. The village guard that follows a shield of this
     size. Short by design: it is a landing cushion, not a second shield. */
  function guardMsFor(shieldMs) {
    var ms = Math.max(0, num(shieldMs, 0));
    if (!ms) return 0;
    return Math.round(clamp(ms * GUARD_FRAC, GUARD_MIN_MS, GUARD_MAX_MS));
  }

  /* burnCostAt(index) -> ms. Escalating price of one attack under a shield. */
  function burnCostAt(index) {
    var i = Math.max(0, Math.floor(num(index, 0)));
    return BURN_LADDER[Math.min(i, BURN_LADDER.length - 1)];
  }

  /* shieldState(p, now) -> {shielded, guard, msLeft, canBeAttacked, ...}
     PURE. The single source of truth for attackability. Reads the SAME
     p.raid.shieldUntil that raid.js and shop/shop.js write, so a shield from any
     source is honored here and a shield granted here is honored there.
     Guard is only ever live AFTER the shield has run out, never during it. */
  function shieldState(p, now) {
    now = num(now, nowMs());
    var r = raidOf(p) || {};
    var sUntil = num(r.shieldUntil, 0), gUntil = num(r.guardUntil, 0);
    var shielded = now < sUntil;
    var guard = !shielded && gUntil > 0 && now < gUntil;
    var burns = Math.max(0, num(r.burns, 0));
    return {
      shielded: shielded,
      guard: guard,
      // the headline countdown: whichever protection is currently holding
      msLeft: shielded ? (sUntil - now) : guard ? (gUntil - now) : 0,
      canBeAttacked: !shielded && !guard,
      phase: shielded ? 'shield' : guard ? 'guard' : 'open',
      shieldMsLeft: shielded ? (sUntil - now) : 0,
      guardMsLeft: guard ? (gUntil - now) : 0,
      shieldUntil: sUntil,
      guardUntil: gUntil,
      burns: burns,
      // what raiding RIGHT NOW would cost. 0 under guard and in the open: that
      // asymmetry is the entire reason village guard exists.
      nextBurnMs: shielded ? burnCostAt(burns) : 0,
      label: shielded ? ('SHIELDED ' + fmtDur(sUntil - now))
           : guard ? ('VILLAGE GUARD ' + fmtDur(gUntil - now))
           : 'EXPOSED'
    };
  }

  /* previewBurn(p, now) -> what burnOnAttack would do, without doing it.
     PURE. Lets a confirm dialog say "this costs you 4h of shield" before the tap. */
  function previewBurn(p, now) {
    now = num(now, nowMs());
    var st = shieldState(p, now);
    if (!st.shielded) {
      return { ms: 0, index: st.burns, free: true, willBreak: false, msLeftAfter: st.msLeft,
               reason: st.guard ? 'GUARD_FREE' : 'NO_SHIELD' };
    }
    var cost = burnCostAt(st.burns);
    var consumed = Math.min(cost, st.shieldMsLeft);
    return {
      ms: consumed, index: st.burns, free: false,
      willBreak: consumed >= st.shieldMsLeft,
      msLeftAfter: st.shieldMsLeft - consumed,
      reason: 'BURN'
    };
  }

  /* breakTimer(p, now) -> does a forced break apply?
     PURE, no writes. `.active` is the answer to "is this player forced offline
     right now"; `.due` means the limit is reached and the next heartbeat will
     start the break. Protected time never accrues, so a shielded player can sit
     online all day and never owe a break. */
  function breakTimer(p, now) {
    now = num(now, nowMs());
    var r = raidOf(p) || {};
    var bUntil = num(r.breakUntil, 0);
    var active = now < bUntil;
    var since = num(r.onlineSince, 0);
    var exposed = shieldState(p, now).canBeAttacked;
    // only UNPROTECTED, non-break, actually-started time counts toward the limit
    var onlineMs = (!active && exposed && since > 0) ? Math.max(0, now - since) : 0;
    return {
      active: active,
      due: !active && onlineMs >= ONLINE_LIMIT_MS,
      msLeft: Math.max(0, bUntil - now),
      onlineMs: onlineMs,
      msUntilDue: Math.max(0, ONLINE_LIMIT_MS - onlineMs),
      until: bUntil,
      limitMs: ONLINE_LIMIT_MS,
      breakMs: BREAK_MS,
      breaks: Math.max(0, num(r.breaks, 0))
    };
  }

  /* status(p, now) -> the one-call merge every consumer actually wants.
     PURE. canAttack folds the break in: a player serving a forced break cannot
     raid, which is what makes the break a real cost and not a cosmetic banner. */
  function status(p, now) {
    now = num(now, nowMs());
    var st = shieldState(p, now), br = breakTimer(p, now);
    st.onBreak = br.active;
    st.breakMsLeft = br.msLeft;
    st.canAttack = !br.active;
    st.attackCostMs = br.active ? 0 : st.nextBurnMs;
    st.brk = br;
    return st;
  }

  // ==========================================================================
  // MUTATORS (in place when given a profile, self-persisting when not)
  // ==========================================================================

  /* grantShield(p, destructionPct, now) -- call when the player LOSES a defense.
     Never shortens an active shield (the law raid.js setShield() and shop.js both
     already follow), resets the burn ladder, and precomputes the village guard so
     the guard resolves with no ticking even if the player is offline for a week. */
  function grantShield(p, destructionPct, when) {
    var now = num(when, nowMs());
    var ms = grantShieldFor(destructionPct);
    return withProfile(p, function (pp) {
      var r = ensureRaid(pp);
      var cur = num(r.shieldUntil, 0);
      r.lastRaided = now;
      if (ms <= 0) {
        return { ok: false, reason: 'BELOW_THRESHOLD', granted: 0, pct: clamp(num(destructionPct, 0), 0, 100),
                 shieldUntil: cur, guardUntil: num(r.guardUntil, 0), extended: false };
      }
      var until = Math.max(cur, now + ms);        // never SHORTEN an active shield
      r.shieldUntil = until;
      r.shieldFrom = now;
      r.burns = 0;                                // fresh shield, fresh burn ladder
      r.guardUntil = until + guardMsFor(ms);      // lazy guard: no tick required
      r.onlineSince = 0;                          // protected time does not accrue toward a break
      return { ok: true, reason: 'GRANTED', granted: ms, pct: clamp(num(destructionPct, 0), 0, 100),
               shieldUntil: until, guardUntil: r.guardUntil, guardMs: guardMsFor(ms),
               extended: cur > now };
    });
  }

  /* burnOnAttack(p, now) -> shield time consumed, in ms.
     Call this when the player LAUNCHES a raid. Returns 0 when they are unshielded
     (nothing to burn) and 0 under village guard (guard attacks are free, on
     purpose). Burning ALSO forfeits the guard: choosing to raid from behind a
     shield gives up the cushion that would have followed it, so there is no route
     to a free farming window. */
  function burnOnAttack(p, when) {
    var now = num(when, nowMs());
    return withProfile(p, function (pp) {
      var r = ensureRaid(pp);
      var until = num(r.shieldUntil, 0);
      if (until <= now) return 0;                 // unshielded or under guard: free
      var idx = Math.max(0, num(r.burns, 0));
      var consumed = Math.min(burnCostAt(idx), until - now);
      r.shieldUntil = until - consumed;           // lands exactly on `now` when the shield breaks
      r.burns = idx + 1;
      // The guard RIDES the shield down instead of staying pinned to the original
      // expiry. Without this shift a burned-down shield would hand the attacker an
      // INSTANT guard (guardUntil was precomputed from an expiry that no longer
      // exists), which is exactly the free farming window the burn exists to stop.
      // Shifting keeps the gap constant: the guard still follows the shield, but it
      // costs 12h of protection to reach, which is a bad trade and therefore safe.
      var g = num(r.guardUntil, 0);
      if (g > 0) r.guardUntil = Math.max(r.shieldUntil, g - consumed);
      return consumed;
    });
  }

  /* heartbeat(p, now) -- the personal-break driver. Safe to call often; it is
     idempotent within a beat and only banks time the player actually spent
     unprotected and present. Returns the resulting breakTimer() state. */
  function heartbeat(p, when) {
    var now = num(when, nowMs());
    return withProfile(p, function (pp) {
      var r = ensureRaid(pp);
      if (now < num(r.breakUntil, 0)) {           // serving a break: nothing accrues
        r.onlineSince = 0; r.onlineLast = now;
        return breakTimer(pp, now);
      }
      if (!shieldState(pp, now).canBeAttacked) {  // shielded or guarded: nothing accrues
        r.onlineSince = 0; r.onlineLast = now;
        return breakTimer(pp, now);
      }
      var last = num(r.onlineLast, 0);
      // no start yet, or you were away long enough that the old run is stale
      if (!num(r.onlineSince, 0) || (last > 0 && (now - last) > IDLE_GAP_MS)) r.onlineSince = now;
      r.onlineLast = now;
      if ((now - num(r.onlineSince, 0)) >= ONLINE_LIMIT_MS) {
        r.breakUntil = now + BREAK_MS;
        r.onlineSince = 0;
        r.breaks = Math.max(0, num(r.breaks, 0)) + 1;
      }
      return breakTimer(pp, now);
    });
  }

  /* canBeAttacked(p, now) -> bool. The one-liner a raid target list wants. */
  function canBeAttacked(p, when) { return shieldState(p, num(when, nowMs())).canBeAttacked; }

  // ==========================================================================
  // public API
  // ==========================================================================
  global.AK_SHIELDS = {
    // pure math (node-requireable, server-reusable, deterministic given `now`)
    grantShieldFor: grantShieldFor,
    guardMsFor: guardMsFor,
    burnCostAt: burnCostAt,
    shieldState: shieldState,
    previewBurn: previewBurn,
    breakTimer: breakTimer,
    status: status,
    canBeAttacked: canBeAttacked,
    fmtDur: fmtDur,
    // persisted verbs (p given = in place; p omitted = atomic via AK_ECON.mutateProfile)
    grantShield: grantShield,
    burnOnAttack: burnOnAttack,
    heartbeat: heartbeat,
    // tuning, exposed so UI copy and a future server tick read the same numbers
    K: {
      SHIELD_MIN_PCT: SHIELD_MIN_PCT, SHIELD_MAX_PCT: SHIELD_MAX_PCT,
      SHIELD_MIN_MS: SHIELD_MIN_MS, SHIELD_MAX_MS: SHIELD_MAX_MS,
      BURN_LADDER: BURN_LADDER.slice(),
      GUARD_FRAC: GUARD_FRAC, GUARD_MIN_MS: GUARD_MIN_MS, GUARD_MAX_MS: GUARD_MAX_MS,
      ONLINE_LIMIT_MS: ONLINE_LIMIT_MS, BREAK_MS: BREAK_MS, IDLE_GAP_MS: IDLE_GAP_MS,
      HOUR_MS: HOUR_MS, MIN_MS: MIN_MS
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_SHIELDS;

  // ==========================================================================
  // hub lifecycle -- self-registering, so the ONLY host edit this module needs is
  // its script tag. AK_SYSTEMS.tickAll drives the personal-break timer with no
  // further wiring, and index.html only ticks systems while state==='IN_ZONE' and
  // no interior is open, which is exactly the "online and exposed in the world"
  // signal the break timer is supposed to measure.
  // ==========================================================================
  if (!global.AK_SYSTEMS) return;               // headless / game.html / node harness: pure API only
  global.AK_SYSTEMS.register({
    id: 'shields',
    init: function (ctx) {
      M.ctx = ctx;
      var p = null;
      try { p = ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { p = null; }
      var st = status(p, nowMs());
      M.phase = st.phase; M.onBreak = st.onBreak; M.booted = true;
      // a shield that ran out while the player was away has already rolled into
      // guard by pure math -- announce whatever is actually holding right now.
      if (st.shielded || st.guard) { try { ctx.showBanner(st.label, 2.0); } catch (_) {} }
    },
    onTick: function (dt, ctx) {
      M.ctx = ctx || M.ctx;
      M.acc += Math.max(0, num(dt, 0));
      if (M.acc < BEAT_S) return;               // one profile write per 30s, never per frame
      M.acc = 0;
      heartbeat();                              // atomic through AK_ECON.mutateProfile
      var p = null;
      try { p = ctx && ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { p = null; }
      var st = status(p, nowMs());
      if (M.booted && st.phase !== M.phase) {
        if (st.phase === 'guard') banner(ctx, 'SHIELD DOWN -- village guard holds ' + fmtDur(st.guardMsLeft) + '. Raid free.', 2.4);
        else if (st.phase === 'open') banner(ctx, 'GUARD DOWN -- your block is exposed.', 2.2);
        else if (st.phase === 'shield') banner(ctx, st.label, 2.0);
      }
      if (M.booted && st.onBreak && !M.onBreak) banner(ctx, 'FORCED BREAK -- crew needs rest. Back in ' + fmtDur(st.breakMsLeft) + '.', 2.6);
      M.phase = st.phase; M.onBreak = st.onBreak; M.booted = true;
    }
  });
  function banner(ctx, text, secs) { try { (ctx || M.ctx).showBanner(text, secs); } catch (_) {} }

})(typeof window !== 'undefined' ? window : globalThis);
