/* game/systems/builders.js -- AK-BLDQUEUE 2026-07-18: THE BUILDER QUEUE.
   ------------------------------------------------------------------------
   The pacing mechanism of the base game (Clash's builder huts). A small pool
   of builders (2 early, ~5-6 late, 8 hard ceiling); EACH timed upgrade ties up
   ONE builder for its whole duration. Scarcity of builders -- not gold -- is
   the real pacing lever, so the ONLY thing that matters here is that the busy
   count is HONEST across every surface that can start a job.

   WHY THIS FILE EXISTS (it is a wrapper, not a new engine):
   economy.js already owns the cap (effectiveBuilderCap), the busy count
   (buildersBusy), the atomic cap-enforced spend (upgradeBuilding) and the
   cap-re-checking landing (finishBuildingUpgrades). This module does NOT fork
   any of that. It adds the one thing missing: THREE surfaces can start a job
   but AK_ECON.buildersBusy only counts TWO of them.

       p.fieldJobs[]        worldverbs harvest dispatch   -> counted by economy
       p.prod[id].upUntil   building upgrades in flight   -> counted by economy
       p.builds[i].uc       buildmode base construction   -> NOT counted  <<<<

   The AK-BUILDERCAP note in economy.js says it fixed the bug where "each
   surface only saw its own jobs and could blow past builderCap". It fixed two
   of the three. buildmode.js stores its jobs on the placed structure as
   b.uc = { slot, t0, dur } (see buildmode.js jobForSlot / busySlots), and
   nothing in economy.js reads p.builds. So today: fill every builder inside
   BUILD MODE, walk out, and the district upgrade panel still believes the
   builders are free. busyBuilders() here closes that hole by counting all
   three pools off the ONE shared profile.

   SHARED-STATE LAW: p.builds[] is the shared schema between the nested
   builder world and the outer 3D district. We READ it for the busy count and
   we only ever WRITE it through AK_ECON.mutateProfile (boost re-timing). We
   never touch localStorage -- a parallel profile engine writing storage
   directly is where this repo's save-loss bugs came from.

   ZERO-STATE LAW: the only field this module introduces is p.builderBoost,
   which is falsy-default and is written ONLY by applyBoost() on a real boost.
   A fresh profile never carries it; every read is guarded. Nothing here is
   backfilled in ensureShape, so zero-state stays byte-identical.

   HEADLESS-SAFE + PURE: zero DOM, zero top-level storage. Every read takes an
   optional profile so a 60fps caller stays allocation-cheap, and every number
   below is derivable from (profile, now) alone -- the server can reuse this
   same math to re-verify a client's queue without a renderer.

   GEMS ARE SERVER-ONLY (parity hard law sec 9): skipCost() PRICES a skip, it
   never grants, spends or reads gems. The caller settles the gems server-side
   and then calls finishNow(). Boosts here move TIMERS only, never a cap, a
   level or loot quality.

   Include order: after economy.js and after buildmode.js.
   ======================================================================== */
(function (global) {
  "use strict";

  function E() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
  function clampN(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function prof(p) { if (p && typeof p === "object") return p; var e = E(); return e ? e.loadProfile() : {}; }

  var MIN_JOB_MS = 1000;          // never stamp a sub-second job (mirrors buildmode's floor)
  var BOOST_MAX  = 100;           // sanity ceiling on a speed potion; a "book" uses finishNow()

  /* ======================================================================
     1. THE POOL -- how many builders exist, how many are working.
     ====================================================================== */

  /* builderCount(p) -> the LIVE cap. Wraps AK_ECON.effectiveBuilderCap, which
     is builderCap(townHall) + (p.bonusBuilders|0), i.e. the sec 5.1 TH table
     1,1,2,2,3,3,4,4,5,6 plus gold-hired slots, hard-ceilinged at 8 by
     buyBuilderSlot. We do NOT re-derive the table: economy owns it and
     townHallPerks(lv).builders is the same number for the design ceiling. */
  function builderCount(p) {
    var e = E(); p = prof(p);
    if (e && typeof e.effectiveBuilderCap === "function") return Math.max(1, e.effectiveBuilderCap(p) | 0);
    if (e && typeof e.builderCapNow === "function") return Math.max(1, e.builderCapNow(p) | 0);
    return 1;                                   // economy absent: assume the single starter builder, never zero
  }

  /* The DESIGN ceiling the Town Hall alone permits, for UI that wants to show
     "TH 6 gives 3 builders, you hired 1 more". Reads townHallPerks(lv).builders
     exactly as specified, no fork. */
  function designBuilders(p) {
    var e = E(); p = prof(p);
    if (!e) return 1;
    try {
      var th = (typeof e.townHallLevel === "function") ? e.townHallLevel(p) : 1;
      if (typeof e.townHallPerks === "function") { var pk = e.townHallPerks(th); if (pk && pk.builders) return pk.builders | 0; }
      if (typeof e.builderCap === "function") return e.builderCap(th) | 0;
    } catch (_) {}
    return 1;
  }

  /* THE THIRD POOL. buildmode.js base-construction jobs ride the placed
     structure: b.uc = { slot, t0, dur }, live while now < t0 + dur. Counted by
     DISTINCT builder slot (buildmode assigns one slot per job and busySlots()
     keys on uc.slot), so two structures that somehow share a slot cost one
     builder, matching what buildmode itself believes. */
  function baseBuildJobs(p, now) {
    p = prof(p); now = num(now, Date.now());
    var out = [], seen = {}, b = Array.isArray(p.builds) ? p.builds : [];
    for (var i = 0; i < b.length; i++) {
      var s = b[i];
      if (!s || !s.uc) continue;
      var end = num(s.uc.t0, 0) + num(s.uc.dur, 0);
      if (now >= end) continue;                                   // landed; buildmode's own tick clears it
      var slot = String(s.uc.slot == null ? ("idx" + i) : s.uc.slot);
      if (seen[slot]) continue;
      seen[slot] = 1;
      out.push({ pool: "base", id: (s.type || s.id || "STRUCT"), slot: slot, idx: i,
                 zone: s.zone, endAt: end, remainMs: Math.max(0, end - now) });
    }
    return out;
  }

  /* busyBuilders(p) -> the HONEST count across all three pools.
     economy's buildersBusy covers p.fieldJobs + p.prod; we add p.builds[].uc.
     Strictly >= economy's number, never less, so wiring this in can only make
     the gate tighter -- it can never let a caller over-cap that could not
     already over-cap today. */
  function busyBuilders(p, now) {
    var e = E(); p = prof(p); now = num(now, Date.now());
    var n = 0;
    if (e && typeof e.buildersBusy === "function") { try { n = e.buildersBusy(p) | 0; } catch (_) { n = 0; } }
    else {
      if (Array.isArray(p.fieldJobs)) n += p.fieldJobs.length;
      if (p.prod && typeof p.prod === "object") { for (var k in p.prod) { var en = p.prod[k]; if (en && en.upUntil > now) n++; } }
    }
    return n + baseBuildJobs(p, now).length;
  }

  /* freeBuilders(p) -> slots available RIGHT NOW. Clamped to [0, count] so a
     stale over-count (e.g. a fieldJob leaked by a crashed tab) can never read
     negative and can never read more free than exist. */
  function freeBuilders(p, now) {
    p = prof(p);
    var cap = builderCount(p);
    return clampN(cap - busyBuilders(p, now), 0, cap);
  }

  /* ======================================================================
     2. THE QUEUE -- every job in flight, one shape, one sort.
     ====================================================================== */

  /* jobs(p, now) -> [{ pool, id, endAt, remainMs, ... }] soonest first.
     Unifies all three pools so a HUD can render "3 of 4 builders busy" and
     list them without knowing which subsystem owns which. PURE. */
  function jobs(p, now) {
    p = prof(p); now = num(now, Date.now());
    var out = [], k;
    if (p.prod && typeof p.prod === "object") {
      for (k in p.prod) {
        var e = p.prod[k];
        if (!e || !e.upUntil || now >= e.upUntil) continue;
        out.push({ pool: "upgrade", id: k, lvl: Math.max(1, e.lvl | 0), next: Math.max(1, e.lvl | 0) + 1,
                   endAt: e.upUntil, remainMs: Math.max(0, e.upUntil - now) });
      }
    }
    if (Array.isArray(p.fieldJobs)) {
      for (var i = 0; i < p.fieldJobs.length; i++) {
        var f = p.fieldJobs[i]; if (!f) continue;
        var fe = num(f.doneAt, num(f.endAt, num(f.until, 0)));
        out.push({ pool: "field", id: String(f.id || f.zone || "FIELD"), endAt: fe, remainMs: Math.max(0, fe - now) });
      }
    }
    out = out.concat(baseBuildJobs(p, now));
    out.sort(function (a, b) { return a.endAt - b.endAt; });
    return out;
  }

  /* The build duration for the NEXT level of a building, BEFORE boost.
     Mirrors index.html upTimeMs(lv) = (30 + 25*lv) seconds so the queue quotes
     exactly what the live district panel quotes (SHOWN == CHARGED). If that
     curve ever moves, it moves in one place and this mirror follows. */
  function baseUpgradeMs(curLvl) { return (30 + 25 * Math.max(1, Math.floor(num(curLvl, 1)))) * 1000; }

  /* ======================================================================
     3. ENQUEUE -- the only way a builder gets taken.
     ====================================================================== */

  /* enqueue(buildingId, targetLevel, opts) -> { ok, ... } | { ok:false, error }

     Validation order is deliberate: cheapest + most explanatory first, spend
     last. Every gate is a REAL read.
       1. economy present
       2. Town Hall gate      -> AK_ECON.canUpgradeBuilding (the AK-THCAP block)
       3. one level per job   -> targetLevel must be exactly curLvl + 1
       4. a FREE BUILDER      -> our three-pool count, not economy's two-pool one
       5. charge + stamp      -> AK_ECON.upgradeBuilding({timeMs}), ATOMIC

     Step 5 is what actually deducts gold + materials and writes upUntil, all
     inside one mutateProfile. We never deduct anything ourselves. Because our
     step 4 is strictly tighter than the identical check inside upgradeBuilding,
     the two can never disagree in the unsafe direction.

     opts.now GATES, IT DOES NOT STAMP. AK_ECON.upgradeBuilding computes
     upUntil = Date.now() + timeMs internally, so a caller-supplied clock steers
     the busy/free evaluation here but the stamped end time always rides the real
     clock. That is deliberate: the persisted timestamp must never be forgeable
     from a caller argument. A test or a server replay reads back the real stamp. */
  function enqueue(buildingId, targetLevel, opts) {
    opts = opts || {};
    var e = E();
    if (!e || typeof e.upgradeBuilding !== "function") return { ok: false, error: "NO_ECONOMY", msg: "economy.js is not loaded." };
    var id = String(buildingId || "").toUpperCase();
    if (!id) return { ok: false, error: "BAD_ID", msg: "No building named." };

    var p = e.loadProfile(), now = num(opts.now, Date.now());
    var g = e.canUpgradeBuilding(id, null, p);          // reason: TH_CAP | MAX | BUSY | IS_TOWN_HALL | null

    var want = (targetLevel == null) ? g.next : Math.floor(num(targetLevel, 0));
    if (want !== g.next) {
      return { ok: false, error: "BAD_TARGET", msg: "One level per job. This building is Lv " + g.lvl + ", so the only legal target is Lv " + g.next + ".",
               lvl: g.lvl, next: g.next, asked: want };
    }
    if (!g.ok) return { ok: false, error: g.reason || "BLOCKED", msg: g.msg, lvl: g.lvl, next: g.next, cap: g.cap, th: g.th };

    var cap = builderCount(p), busy = busyBuilders(p, now);
    if (cap - busy <= 0) {
      return { ok: false, error: "NO_BUILDERS", msg: "Every builder's already on a job.",
               builders: cap, busy: busy, free: 0, nextFreeMs: nextFreeMs(p, now) };
    }

    var ms = Math.max(MIN_JOB_MS, Math.round(boostedMs(baseUpgradeMs(g.lvl), p, now)));
    var r = e.upgradeBuilding(id, { timeMs: ms, curLvl: g.lvl });
    if (!r || !r.ok) return r || { ok: false, error: "FAIL" };

    r.queuedMs = ms;
    r.baseMs = baseUpgradeMs(g.lvl);
    r.boosted = ms < r.baseMs;
    r.free = clampN(cap - (busy + 1), 0, cap);
    r.builders = cap;
    return r;
  }

  /* When does the next builder come free? Infinity if none are working. */
  function nextFreeMs(p, now) {
    var j = jobs(p, now);
    return j.length ? j[0].remainMs : 0;
  }

  /* ======================================================================
     4. LANDING -- idempotent, and the cap is re-checked at landing time.
     ====================================================================== */

  /* finishDue(now) -> [{ id, lvl, capped }]

     Delegates to AK_ECON.finishBuildingUpgrades, which is already the correct
     landing: it clears upUntil FIRST, then re-reads buildingCapFor(p, id) and
     refuses the level if the Town Hall no longer holds it (capped:true). That
     is the "a Hall knocked down mid-build cannot land an over-cap building"
     rule, and it lives inside the mutation so no surface can route around it.

     IDEMPOTENT twice over: economy polls pendingBuildingUpgrades() and returns
     [] without writing when nothing is due, and a landed job has upUntil = 0
     so a second call in the same tick matches nothing. Safe to call every
     frame -- it only writes on the frame something actually lands.

     Base-construction jobs (p.builds[].uc) are NOT landed here on purpose:
     buildmode.js owns that transition (it clears b.uc and frees the crew slot
     in its own tick). We count those jobs, we do not land them. One owner per
     transition is exactly why the shared state stays coherent. */
  function finishDue(now) {
    var e = E();
    if (!e || typeof e.finishBuildingUpgrades !== "function") return [];
    if (typeof e.pendingBuildingUpgrades === "function") {
      try { if (e.pendingBuildingUpgrades(null, num(now, Date.now())) <= 0) return []; } catch (_) {}
    }
    return e.finishBuildingUpgrades(num(now, Date.now())) || [];
  }

  /* PURE poll for a 60fps caller: is there anything worth calling finishDue for? */
  function dueCount(p, now) {
    var e = E();
    if (e && typeof e.pendingBuildingUpgrades === "function") { try { return e.pendingBuildingUpgrades(prof(p), num(now, Date.now())) | 0; } catch (_) {} }
    p = prof(p); now = num(now, Date.now());
    var n = 0;
    if (p.prod && typeof p.prod === "object") { for (var k in p.prod) { var en = p.prod[k]; if (en && en.upUntil && now >= en.upUntil) n++; } }
    return n;
  }

  /* ======================================================================
     5. SKIP -- the non-linear curve.
     ====================================================================== */

  /* skipCost(remainingMs) -> gems to finish a timer NOW.

     SHAPE: a bucketed diminishing-returns ladder keyed on SECONDS remaining,
     then a linear over-day tail. It is AK_ECON.gemSkipCost, delegated, not
     re-derived:

         <= 2 min    0 gems      (free auto-finish band)
         <= 10 min   2
         <= 30 min   5
         <= 1 h      9
         <= 4 h     24
         <= 12 h    60
         <= 24 h   100
          > 24 h    24 + 76 * ((minutes - 240) / 1200)   (continuous at 24 h = 100)

     WHY THIS SHAPE. Total price rises with time but SUBLINEARLY, so the price
     PER SECOND falls hard as the timer grows. That is the whole point:
       10 min -> 2 gems     = 0.003333 gems/sec
        6 h   -> 60 gems    = 0.002778 gems/sec   (0.83x the 10-minute rate)
        3 d   -> 282 gems   = 0.001088 gems/sec   (0.33x the 10-minute rate)
     So the last minutes of a long build are cheap in absolute gems but the
     most expensive seconds you can buy, while a multi-day build is enormous in
     absolute gems yet a bargain per second. Short skips feel like impulse buys
     (2 gems, why not); long skips feel like a real decision. Linear pricing
     would invert that and make impulse skipping the dominant strategy, which
     collapses the builder scarcity this whole file exists to protect.

     WHY DELEGATE INSTEAD OF DEFINING A SMOOTHER CURVE. gemSkipCost is already
     the LIVE price on two shipped surfaces (game/index.html line 3033 and
     game/systems/buildmode.js gemSkipCost). A prettier continuous curve here
     would quote a different number for the same timer, which is precisely the
     two-promises bug the AK-BLDWIRE block in economy.js was written to kill.
     ONE price, everywhere. The step-function's flat regions are surfaced as a
     FEATURE by skipQuote() below rather than smoothed away.

     NOTE the bucket edges are inclusive upper bounds on seconds, so we floor
     ms -> s the same way the shipped callers do (they pass remainMs/1000). */
  function skipCost(remainingMs) {
    var secs = Math.max(0, num(remainingMs, 0) / 1000);
    var e = E();
    if (e && typeof e.gemSkipCost === "function") { try { return e.gemSkipCost(secs) | 0; } catch (_) {} }
    // Headless mirror of the SAME table (economy absent). Mirrors buildmode.js's
    // identical fallback; if these three ever drift, economy.js is the law.
    if (secs <= 120)   return 0;
    if (secs <= 600)   return 2;
    if (secs <= 1800)  return 5;
    if (secs <= 3600)  return 9;
    if (secs <= 14400) return 24;
    if (secs <= 43200) return 60;
    if (secs <= 86400) return 100;
    return Math.round(24 + 76 * ((secs / 60 - 240) / 1200));
  }

  /* skipQuote(remainingMs) -> { gems, perSec, free, nextBreakMs, nextGems, saveGems }
     Turns the step function into information instead of a surprise: it tells
     the player how long until the price DROPS to the next bucket and by how
     much. Same numbers as skipCost, just explained. PURE. */
  var SKIP_EDGES = [120, 600, 1800, 3600, 14400, 43200, 86400];
  function skipQuote(remainingMs) {
    var ms = Math.max(0, num(remainingMs, 0));
    var secs = ms / 1000, gems = skipCost(ms);
    var q = { remainMs: ms, gems: gems, free: gems <= 0,
              perSec: secs > 0 ? gems / secs : 0,
              nextBreakMs: 0, nextGems: gems, saveGems: 0 };
    for (var i = SKIP_EDGES.length - 1; i >= 0; i--) {
      if (secs > SKIP_EDGES[i]) {                       // the next cheaper bucket is at this edge
        q.nextBreakMs = Math.max(0, ms - SKIP_EDGES[i] * 1000);
        q.nextGems = skipCost(SKIP_EDGES[i] * 1000);
        q.saveGems = Math.max(0, gems - q.nextGems);
        return q;
      }
    }
    return q;                                            // already in the free band
  }

  /* ======================================================================
     6. BOOSTS -- the potion (speed x mult for a window) and the book (instant).
     ====================================================================== */

  /* p.builderBoost = { mult, until } -- falsy-default, written ONLY here.

     THE MATH (pure, exported as boostedRemain for the server to re-verify).
     A job with R ms of work left, under a boost of speed `mult` that has W ms
     of wall-clock window left:
        work done during the window = mult * W
        if mult*W >= R  -> the job finishes inside the window at R / mult
        else            -> W of boosted wall time, then (R - mult*W) at 1x
     That is exact, monotonic in every argument, and needs nothing but numbers,
     so the same function re-times a job on the client and audits it server-side. */
  function boostedRemain(remainMs, mult, windowMs) {
    var R = Math.max(0, num(remainMs, 0));
    var m = num(mult, 1), W = Math.max(0, num(windowMs, 0));
    if (!(m > 1) || W <= 0 || R <= 0) return R;
    var work = m * W;
    if (work >= R) return R / m;
    return W + (R - work);
  }

  /* The live boost, or null. PURE. Expired boosts read as null and are never
     written back (no storage churn just to clear a stale field). */
  function activeBoost(p, now) {
    p = prof(p); now = num(now, Date.now());
    var b = p.builderBoost;
    if (!b || !(num(b.mult, 1) > 1) || num(b.until, 0) <= now) return null;
    return { mult: num(b.mult, 1), until: num(b.until, 0), remainMs: num(b.until, 0) - now };
  }

  /* Apply the live boost to a duration a job is ABOUT to be stamped with, so a
     job started during a potion is stamped short rather than needing a rewrite. */
  function boostedMs(ms, p, now) {
    var b = activeBoost(p, now);
    return b ? boostedRemain(ms, b.mult, b.remainMs) : Math.max(0, num(ms, 0));
  }

  /* applyBoost(mult, durationMs) -> { ok, mult, until, retimed }

     The speed potion. Does TWO things in ONE mutateProfile:
       1. records p.builderBoost so jobs enqueued during the window are stamped
          short at creation (boostedMs above), and
       2. RE-TIMES every job already in flight, because jobs are stored as
          absolute end timestamps -- a speed multiplier that did not rewrite
          them would do nothing to the work already started, which is the
          opposite of what a builder potion means.
     Re-times both pools it is allowed to move: p.prod[].upUntil (upgrades) and
     p.builds[].uc (base construction, by extending uc.dur's origin so
     buildmode's own `rem = t0 + dur - now` and its progress fraction both stay
     correct). p.fieldJobs is left alone: worldverbs owns that shape and this
     is a BUILDER potion, not a harvest potion.

     Stacking: a stronger boost replaces a weaker one and a same-or-stronger
     boost extends the window. It never multiplies, so no potion stack can
     collapse a multi-day build to nothing. */
  function applyBoost(mult, durationMs, opts) {
    opts = opts || {};
    var e = E();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECONOMY" };
    var m = clampN(num(mult, 0), 0, BOOST_MAX);
    var dur = Math.max(0, Math.floor(num(durationMs, 0)));
    if (!(m > 1)) return { ok: false, error: "BAD_MULT", msg: "A boost must be faster than 1x." };
    if (dur <= 0) return { ok: false, error: "BAD_DURATION", msg: "A boost needs a window." };

    var now = num(opts.now, Date.now()), out = { ok: false, error: "FAIL" };
    e.mutateProfile(function (p) {
      var cur = activeBoost(p, now);
      var until = now + dur, retimed = 0;

      // Re-time work already in flight, at the NEW multiplier, over the NEW window.
      if (p.prod && typeof p.prod === "object") {
        for (var k in p.prod) {
          var en = p.prod[k];
          if (!en || !en.upUntil || en.upUntil <= now) continue;
          en.upUntil = now + Math.max(MIN_JOB_MS, Math.round(boostedRemain(en.upUntil - now, m, dur)));
          retimed++;
        }
      }
      if (Array.isArray(p.builds)) {
        for (var i = 0; i < p.builds.length; i++) {
          var s = p.builds[i];
          if (!s || !s.uc) continue;
          var t0 = num(s.uc.t0, 0), end = t0 + num(s.uc.dur, 0);
          if (end <= now) continue;
          var nr = Math.max(MIN_JOB_MS, Math.round(boostedRemain(end - now, m, dur)));
          s.uc.dur = (now + nr) - t0;                     // keep t0 so buildmode's progress fraction stays anchored
          retimed++;
        }
      }

      // Stronger wins; equal-or-stronger extends. Never multiplies.
      if (cur && cur.mult > m) { until = Math.max(cur.until, until); m = cur.mult; }
      else if (cur && cur.until > until && cur.mult === m) { until = cur.until; }
      p.builderBoost = { mult: m, until: until };
      out = { ok: true, mult: m, until: until, durationMs: until - now, retimed: retimed };
    });
    return out;
  }

  /* finishNow(buildingId) -> the BOOK (instant-finish), and the settlement hook
     for a paid skip. Collapses one job's remaining time to zero and lands it
     through the SAME cap-re-checking path as a natural finish, so an instant
     finish can no more exceed the Town Hall cap than waiting it out could.
     Gems are NOT touched here (server-only): price with skipCost(), settle the
     currency server-side, then call this. */
  function finishNow(buildingId, opts) {
    opts = opts || {};
    var e = E();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECONOMY" };
    var id = String(buildingId || "").toUpperCase();
    var now = num(opts.now, Date.now()), found = false;
    e.mutateProfile(function (p) {
      var en = p.prod && p.prod[id];
      if (!en || !en.upUntil || en.upUntil <= now) return;
      en.upUntil = now;                                   // due exactly now -> finishDue lands it, cap re-checked
      found = true;
    });
    if (!found) return { ok: false, error: "NO_JOB", msg: "Nothing in flight on " + id + "." };
    var landed = finishDue(now);
    for (var i = 0; i < landed.length; i++) {
      if (landed[i].id === id) return { ok: true, id: id, lvl: landed[i].lvl, capped: !!landed[i].capped };
    }
    return { ok: true, id: id, landed: false };
  }

  /* ======================================================================
     7. STATUS -- one object a HUD can render without asking anything else.
     ====================================================================== */
  function status(p, now) {
    p = prof(p); now = num(now, Date.now());
    var cap = builderCount(p), busy = busyBuilders(p, now);
    return {
      builders: cap,
      design: designBuilders(p),
      hired: Math.max(0, cap - designBuilders(p)),
      busy: busy,
      free: clampN(cap - busy, 0, cap),
      jobs: jobs(p, now),
      due: dueCount(p, now),
      nextFreeMs: nextFreeMs(p, now),
      boost: activeBoost(p, now)
    };
  }

  global.AK_BUILDERS = {
    // pool
    builderCount: builderCount,     // (p?) -> live cap (wraps AK_ECON.effectiveBuilderCap)
    designBuilders: designBuilders,  // (p?) -> TH-only design ceiling (wraps townHallPerks(lv).builders)
    busyBuilders: busyBuilders,      // (p?,now?) -> HONEST busy across p.fieldJobs + p.prod + p.builds[].uc
    freeBuilders: freeBuilders,      // (p?,now?) -> free slots, clamped to [0,cap]
    baseBuildJobs: baseBuildJobs,    // (p?,now?) -> the buildmode pool economy.js does not see
    // queue
    jobs: jobs,                      // (p?,now?) -> every job in flight, soonest first PURE
    status: status,                  // (p?,now?) -> the whole HUD payload in one read PURE
    enqueue: enqueue,                // (id,targetLevel?,opts?) -> validate + charge + stamp (ATOMIC via AK_ECON)
    baseUpgradeMs: baseUpgradeMs,    // (curLvl) -> pre-boost duration (mirrors index.html upTimeMs)
    nextFreeMs: nextFreeMs,          // (p?,now?) -> ms until a builder frees up
    // landing
    finishDue: finishDue,            // (now?) -> land due upgrades; IDEMPOTENT, re-checks the TH cap
    dueCount: dueCount,              // (p?,now?) -> cheap poll before writing PURE
    // skip
    skipCost: skipCost,              // (remainingMs) -> gems (delegates to AK_ECON.gemSkipCost)
    skipQuote: skipQuote,            // (remainingMs) -> { gems, perSec, nextBreakMs, saveGems } PURE
    // boosts
    applyBoost: applyBoost,          // (mult,durationMs,opts?) -> potion: records + re-times in-flight work
    boostedRemain: boostedRemain,    // (remainMs,mult,windowMs) -> exact boosted remainder PURE
    boostedMs: boostedMs,            // (ms,p?,now?) -> duration to stamp under the live boost PURE
    activeBoost: activeBoost,        // (p?,now?) -> { mult, until, remainMs } | null PURE
    finishNow: finishNow             // (id,opts?) -> book / paid-skip settlement; lands via the cap-checked path
  };
})(typeof window !== "undefined" ? window : globalThis);
