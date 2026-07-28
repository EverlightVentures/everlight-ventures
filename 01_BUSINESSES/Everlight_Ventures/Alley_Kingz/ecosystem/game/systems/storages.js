/* game/systems/storages.js -- AK_SYSTEMS module: "COLLECTORS & STORAGES" (AK-STORE 2026-07-18)
   ------------------------------------------------------------------------
   The engine of the base economy: what your base can HOLD, how a deposit
   SPREADS across the storages you actually built, and what a raider can TAKE.

   THREE BUCKETS, THREE LOOT RATES (the loot lane reads lootableFrom):
     COLLECTOR-HELD -- yield sitting UNCOLLECTED in a producer (GEM/MINT/FORGE/
                       LAB/GEN). Juiciest target: it is not banked yet.
     STORAGE-HELD   -- banked in the storage structures you placed in build mode.
     TOWNHALL-HELD  -- the Town Hall's own slice. Lootable ONLY if the Town Hall
                       is destroyed, which is what makes the Hall worth defending.

   THE ONE-STATE LAW (why this file persists almost nothing):
     A storage's contents are NOT stored. They are DERIVED, every read, from
       (a) the real balance already on the profile (p.coins / p.wood / p.scrap[R] ...)
       (b) the real structures in p.builds[] (the buildmode schema, shared)
       (c) the real Town Hall level (p.townHall)
     splitOf(total, caps) is a pure function, so the walk-out promise holds for
     free: place a storage inside the nested build world, walk out, and the outer
     district instantly sees a bigger cap and a re-levelled split. There is no
     second copy of the numbers to drift, and no new save-loss surface.

   ACCRUAL IS NOT DUPLICATED:
     production.js owns producer accrual. This file only ASKS what is pending.
     It prefers global.AK_PROD.pendingUnits (see the one-line export noted in the
     wave handoff); until that lands it uses PROD_MIRROR below, whose constants
     are a verbatim mirror of production.js. Parity is proven by driving the REAL
     production.js COLLECT button and comparing the granted units, all five
     producers, in the wave handoff harness (storages_proof.js).

   HARD-LAW COMPLIANCE:
     - Every write goes through AK_ECON.mutateProfile. Zero direct localStorage.
     - Soft currency only. Gems are server-only and are never read or written.
     - Bones are soulbound: uncapped and NEVER lootable.
     - Headless-safe and pure: no top-level DOM, no timers. The math half runs
       under node so the server can reuse it verbatim.
     - Zero new profile fields. Nothing here changes a zero-state profile.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';

  var HR_MS        = 3600000;
  var BLD_MAX_LVL  = 10;     // mirrors AK_ECON.BLD_MAX_LVL / production.js MAX_LVL
  var TH_MAX       = 10;

  var RARITIES = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic'];
  try { if (global.AK_ECON && AK_ECON.RARITIES && AK_ECON.RARITIES.length) RARITIES = AK_ECON.RARITIES.slice(); } catch (_e) {}

  /* ---------------------------------------------------------------------- *
   * RESOURCE REGISTRY -- real profile fields ONLY (see economy.js ensureShape)
   * ---------------------------------------------------------------------- *
   * store    : which storage TYPE banks it (null = Town Hall slice only)
   * lootable : can a raider take it at all
   * uncapped : no ceiling (bones -- soulbound skill currency)                */
  var RES = {
    coins:     { label: 'Gold',          store: 'SAFE',      lootable: true,  thBase: 1500 },
    wood:      { label: 'Wood',          store: 'LOCKER',    lootable: true,  thBase: 500  },
    stone:     { label: 'Stone',         store: 'LOCKER',    lootable: true,  thBase: 500  },
    metal:     { label: 'Metal',         store: 'SCRAPYARD', lootable: true,  thBase: 300  },
    produce:   { label: 'Produce',       store: 'PANTRY',    lootable: true,  thBase: 250  },
    keys:      { label: 'Keys',          store: null,        lootable: true,  thBase: 20   },  // Hall prize: takeable only if the Hall falls
    fragments: { label: 'Key Fragments', store: null,        lootable: false, thBase: 50   },  // jackpot class (LOOT_TABLE sec 7): never reduced
    bones:     { label: 'Bones',         store: null,        lootable: false, uncapped: true } // soulbound skill currency
  };
  // Scrap tiers are real fields too: p.scrap[rarity]. Keyed 'scrap:Rare' etc.
  var SCRAP_TH_BASE = { Common: 150, Rare: 100, Epic: 60, Legendary: 30, Mythic: 15 };
  for (var _ri = 0; _ri < RARITIES.length; _ri++) {
    var _r = RARITIES[_ri];
    RES['scrap:' + _r] = { label: _r + ' Scrap', store: 'SCRAPYARD', lootable: true, scrap: _r, thBase: SCRAP_TH_BASE[_r] || 30 };
  }
  var RES_KEYS = Object.keys(RES);

  /* ---------------------------------------------------------------------- *
   * STORAGE STRUCTURES -- the canonical spec (buildmode STRUCT mirrors this)
   * ---------------------------------------------------------------------- *
   * They live in p.builds[] like every other placement: {type,x,y,zone,hp,lvl}.
   * `lvl` is an optional field on the shared entry (same pattern as crop /
   * plantedAt / rot / uc), defaulting to 1, and is clamped by the Town Hall.   */
  var STORAGE_TYPES = {
    SAFE:      { name: 'Street Safe',   base: 2000, holds: 'gold',    blurb: 'Banks gold off the block.' },
    LOCKER:    { name: 'Supply Locker', base: 600,  holds: 'lumber',  blurb: 'Wood and stone, stacked deep.' },
    SCRAPYARD: { name: 'Scrap Yard',    base: 400,  holds: 'scrap',   blurb: 'Metal and every scrap tier.' },
    PANTRY:    { name: 'Cold Pantry',   base: 300,  holds: 'produce', blurb: 'Keeps the harvest from spoiling.' }
  };
  var STORE_GROWTH = 0.6;   // each storage level adds +60% of its base capacity
  var TH_GROWTH    = 0.5;   // each Town Hall level adds +50% of the Hall's base slice

  // Loot rates by bucket. The loot lane multiplies these itself (garageLootMult etc).
  var LOOT_RATE = {
    collector: 0.50,   // uncollected yield is the fat target
    storage:   0.20,   // banked resources bleed slowly
    townHall:  1.00    // the Hall's slice, and ONLY once the Hall is down
  };

  /* ---------------------------------------------------------------------- *
   * PROD_MIRROR -- verbatim mirror of production.js accrual constants.
   * ---------------------------------------------------------------------- *
   * Used ONLY while production.js keeps its math module-private. pending()
   * prefers global.AK_PROD.pendingUnits when that export lands. Parity with the
   * REAL production.js collect path is proven in test/storages_proof.js.        */
  var PROD_MIRROR = {
    CAP_HOURS: 8, RATE_GROWTH: 0.5, GEN_BOOST_PER_LVL: 0.03, GEN_BOOST_MAX: 0.30,
    RATE: { GEM: 5, MINT: 90, FORGE: 4, LAB: 2, GEN: 0.5 },
    // which resource key each producer's haul lands in (mirrors CFG grantKind + rarity)
    RES:  { GEM: 'scrap:Rare', MINT: 'coins', FORGE: 'fragments', LAB: 'scrap:Epic', GEN: 'keys' }
  };
  var PRODUCERS = ['GEM', 'MINT', 'FORGE', 'LAB', 'GEN'];

  function num(v, d) { return (typeof v === 'number' && isFinite(v)) ? v : d; }
  function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function townHallLevel(p) {
    try { if (global.AK_ECON && AK_ECON.townHallLevel) return AK_ECON.townHallLevel(p); } catch (_e) {}
    return clampN(Math.floor(num(p && p.townHall, 1)), 1, TH_MAX);
  }

  // ---- balance access: the REAL fields, never a shadow copy -----------------
  function readBal(p, key) {
    if (!p) return 0;
    var def = RES[key]; if (!def) return 0;
    if (def.scrap) return Math.max(0, (p.scrap && p.scrap[def.scrap]) | 0);
    if (key === 'bones') {                                   // ONE WALLET: duty + handler pockets
      try { if (global.AK_ECON && AK_ECON.bonesTotal) return Math.max(0, AK_ECON.bonesTotal(p) | 0); } catch (_e) {}
      return Math.max(0, p.bones | 0);
    }
    return Math.max(0, p[key] | 0);
  }
  function writeBal(p, key, v) {
    var def = RES[key]; if (!def || !p) return;
    v = Math.max(0, Math.round(v));
    if (def.scrap) { if (!p.scrap || typeof p.scrap !== 'object') p.scrap = {}; p.scrap[def.scrap] = v; return; }
    p[key] = v;
  }

  /* ---------------------------------------------------------------------- *
   * STORAGE UNITS -- read straight out of the SHARED p.builds[] schema
   * ---------------------------------------------------------------------- */
  function unitCap(type, lvl) {
    var d = STORAGE_TYPES[type]; if (!d) return 0;
    lvl = clampN(Math.floor(num(lvl, 1)), 1, BLD_MAX_LVL);
    return Math.max(1, Math.round(d.base * (1 + STORE_GROWTH * (lvl - 1))));
  }
  function thCapFor(key, th) {
    var def = RES[key]; if (!def || def.uncapped) return 0;
    th = clampN(Math.floor(num(th, 1)), 1, TH_MAX);
    return Math.max(0, Math.round((def.thBase || 0) * (1 + TH_GROWTH * (th - 1))));
  }

  // Every built storage, with its EFFECTIVE level (Town Hall caps it, CoC rule).
  // Under-construction placements (b.uc still running) do not count yet.
  function storageUnits(p, now) {
    now = num(now, Date.now());
    var th = townHallLevel(p), out = [], builds = (p && p.builds) || [];
    for (var i = 0; i < builds.length; i++) {
      var b = builds[i]; if (!b || !STORAGE_TYPES[b.type]) continue;
      if (b.uc && now < (num(b.uc.t0, 0) + num(b.uc.dur, 0))) continue;      // still going up
      var lvl = clampN(Math.floor(num(b.lvl, 1)), 1, Math.min(BLD_MAX_LVL, th));
      out.push({ idx: i, type: b.type, name: STORAGE_TYPES[b.type].name, zone: b.zone || null, lvl: lvl, cap: unitCap(b.type, lvl) });
    }
    return out;
  }

  // The participants that hold ONE resource: its storages plus the Town Hall.
  function holdersFor(p, key, now) {
    var def = RES[key]; if (!def || def.uncapped) return [];
    var out = [], th = townHallLevel(p);
    if (def.store) {
      var units = storageUnits(p, now);
      for (var i = 0; i < units.length; i++) if (units[i].type === def.store) {
        out.push({ kind: 'storage', key: units[i].type + '#' + units[i].idx, idx: units[i].idx, type: units[i].type, name: units[i].name, zone: units[i].zone, lvl: units[i].lvl, cap: units[i].cap });
      }
    }
    var tc = thCapFor(key, th);
    if (tc > 0) out.push({ kind: 'townHall', key: 'TOWNHALL', idx: -1, type: 'TOWNHALL', name: 'Town Hall', zone: null, lvl: th, cap: tc });
    return out;
  }

  /* ---------------------------------------------------------------------- *
   * THE EVEN-FILL ALGORITHM (pure, integer-exact)
   * ---------------------------------------------------------------------- *
   * splitOf(total, caps) -> per-holder contents.
   *
   * Water-filling on ABSOLUTE contents: walk the holders from SMALLEST capacity
   * to largest, and hand each one an even share of what is left over the holders
   * still unserved. A low-level storage therefore FILLS FIRST, up to its own
   * reduced capacity, and the share it could not take rolls forward to the bigger
   * holders instead of being stranded. When every holder is roomy the result is
   * dead even (within 1 unit of rounding dust).
   *
   * Deterministic: contents are a pure function of (total, caps). Two clients
   * with the same base and the same balance compute the identical split, which
   * is why nothing has to be persisted and why the server can replay it.        */
  function splitOf(total, caps) {
    var n = caps.length, out = new Array(n), i;
    for (i = 0; i < n; i++) out[i] = 0;
    var rem = Math.max(0, Math.floor(num(total, 0)));
    if (n === 0) return { contents: out, stored: 0, overflow: rem };

    var order = [];
    for (i = 0; i < n; i++) order.push(i);
    order.sort(function (a, b) { return (caps[a] - caps[b]) || (a - b); });    // smallest capacity first

    for (var k = 0; k < n; k++) {
      var idx = order[k], slots = n - k;                    // holders still unserved, this one included
      var share = Math.floor(rem / slots);
      var give = Math.min(Math.max(0, Math.floor(num(caps[idx], 0))), share);
      out[idx] = give; rem -= give;
    }
    // Rounding dust (and only dust): hand it out smallest-capacity first.
    for (var pass = 0; pass < n && rem > 0; pass++) {
      var moved = false;
      for (var j = 0; j < n && rem > 0; j++) {
        var t = order[j];
        if (out[t] < caps[t]) { out[t]++; rem--; moved = true; }
      }
      if (!moved) break;
    }
    var stored = 0; for (i = 0; i < n; i++) stored += out[i];
    return { contents: out, stored: stored, overflow: rem };
  }

  /* ---------------------------------------------------------------------- *
   * PUBLIC READS
   * ---------------------------------------------------------------------- */
  // capacityFor(p) -> { resourceKey: capacity }, or capacityFor(p,key) -> number.
  // Built from REAL building levels: every storage of the right type plus the
  // Town Hall slice. `null` means uncapped (bones).
  function capacityFor(p, key, now) {
    if (key != null) {
      var def = RES[key]; if (!def) return 0;
      if (def.uncapped) return null;
      var hs = holdersFor(p, key, now), t = 0;
      for (var i = 0; i < hs.length; i++) t += hs[i].cap;
      return t;
    }
    var map = {};
    for (var k = 0; k < RES_KEYS.length; k++) map[RES_KEYS[k]] = capacityFor(p, RES_KEYS[k], now);
    return map;
  }

  // distribute(p, resource, amount) -> the per-storage split, before and after.
  // PURE: reports what WOULD happen. bank() is the write path.
  // Overflow is reported as `waste` so the UI can prompt a storage upgrade.
  function distribute(p, key, amount, now) {
    var def = RES[key];
    if (!def) return { ok: false, error: 'UNKNOWN_RESOURCE', resource: key };
    var held = readBal(p, key);
    amount = Math.max(0, Math.floor(num(amount, 0)));

    if (def.uncapped) {
      return { ok: true, resource: key, label: def.label, uncapped: true, held: held,
               amount: amount, placed: amount, waste: 0, capacity: null, after: held + amount,
               storages: [], townHall: null, full: false, pctFull: 0 };
    }

    var holders = holdersFor(p, key, now);
    var caps = holders.map(function (h) { return h.cap; });
    var capacity = caps.reduce(function (a, b) { return a + b; }, 0);

    var room   = Math.max(0, capacity - held);
    var placed = Math.min(amount, room);
    var waste  = amount - placed;

    var before = splitOf(held, caps);
    var after  = splitOf(held + placed, caps);

    var rows = [], thRow = null;
    for (var i = 0; i < holders.length; i++) {
      var h = holders[i];
      var row = { key: h.key, kind: h.kind, idx: h.idx, type: h.type, name: h.name, zone: h.zone,
                  lvl: h.lvl, cap: h.cap, before: before.contents[i], after: after.contents[i],
                  added: after.contents[i] - before.contents[i],
                  full: after.contents[i] >= h.cap };
      if (h.kind === 'townHall') thRow = row; else rows.push(row);
    }
    return {
      ok: true, resource: key, label: def.label,
      held: held, amount: amount, placed: placed, waste: waste,
      capacity: capacity, after: held + placed, room: room,
      storages: rows, townHall: thRow,
      full: (held + placed) >= capacity,
      pctFull: capacity > 0 ? Math.min(1, (held + placed) / capacity) : 1,
      needsUpgrade: waste > 0
    };
  }

  /* ---------------------------------------------------------------------- *
   * COLLECTORS -- ASK production.js, never re-derive its accrual
   * ---------------------------------------------------------------------- */
  function prodApi() {
    var a = global.AK_PROD;
    return (a && typeof a.pendingUnits === 'function') ? a : null;
  }
  function mirrorPending(p, bid, now) {                    // fallback only; parity-tested
    var prod = (p && p.prod) || {}, e = prod[bid];
    if (!e) return 0;
    var lvl = Math.max(1, e.lvl | 0);
    var base = PROD_MIRROR.RATE[bid] * (1 + PROD_MIRROR.RATE_GROWTH * (lvl - 1));
    var boost = 1;
    if (bid !== 'GEN') {
      var g = prod.GEN ? (prod.GEN.lvl | 0) : 0;
      boost = 1 + Math.min(PROD_MIRROR.GEN_BOOST_MAX, PROD_MIRROR.GEN_BOOST_PER_LVL * g);
    }
    var rate = base * boost, cap = Math.max(1, Math.round(base * PROD_MIRROR.CAP_HOURS));
    if (rate <= 0) return 0;
    var hr = Math.max(0, (now - num(e.lastCollect, 0)) / HR_MS);
    var acc = rate * hr; if (acc > cap) acc = cap;
    var u = Math.floor(acc);
    return u < 0 ? 0 : u;
  }
  function pendingUnits(p, bid, now) {
    now = num(now, Date.now());
    var api = prodApi();
    if (api) { try { return Math.max(0, api.pendingUnits((p && p.prod) || {}, bid, now) | 0); } catch (_e) {} }
    return mirrorPending(p, bid, now);
  }

  // collectorHeld(p) -> { resourceKey: uncollected units }. Only producers the
  // player has actually claimed (p.prod entry exists) contribute.
  function collectorHeld(p, now) {
    now = num(now, Date.now());
    var out = {};
    for (var i = 0; i < PRODUCERS.length; i++) {
      var bid = PRODUCERS[i], key = PROD_MIRROR.RES[bid];
      var u = pendingUnits(p, bid, now); if (u <= 0) continue;
      out[key] = (out[key] | 0) + u;
    }
    return out;
  }

  /* ---------------------------------------------------------------------- *
   * lootableFrom(p) -- the three buckets the loot lane consumes
   * ---------------------------------------------------------------------- *
   * opts.townHallDestroyed flips the Hall slice from PROTECTED to takeable.
   * Every bucket carries its own rate because they are looted differently.      */
  function lootableFrom(p, now, opts) {
    now = num(now, Date.now());
    opts = opts || {};
    var thDown = !!opts.townHallDestroyed;
    var coll = collectorHeld(p, now);
    var buckets = { storage: {}, collector: {}, townHall: {} };
    var stealable = {}, rows = [], totals = { storage: 0, collector: 0, townHall: 0, stealable: 0 };

    for (var i = 0; i < RES_KEYS.length; i++) {
      var key = RES_KEYS[i], def = RES[key];
      var held = readBal(p, key);
      var inColl = coll[key] | 0;
      var inStore = 0, inTH = 0;

      if (!def.uncapped) {
        var holders = holdersFor(p, key, now);
        var caps = holders.map(function (h) { return h.cap; });
        var sp = splitOf(held, caps);
        for (var j = 0; j < holders.length; j++) {
          if (holders[j].kind === 'townHall') inTH += sp.contents[j]; else inStore += sp.contents[j];
        }
        // Anything already banked past capacity (legacy stock, or a demolished
        // storage) is unhoused: treat it as storage-held so it is never invisible.
        inStore += Math.max(0, held - sp.stored);
      } else {
        inStore = held;   // uncapped, unhoused by definition (bones: not lootable anyway)
      }

      var takeStore = def.lootable ? Math.floor(inStore * LOOT_RATE.storage) : 0;
      var takeColl  = def.lootable ? Math.floor(inColl  * LOOT_RATE.collector) : 0;
      var takeTH    = (def.lootable && thDown) ? Math.floor(inTH * LOOT_RATE.townHall) : 0;
      var take      = takeStore + takeColl + takeTH;

      if (inStore) buckets.storage[key] = inStore;
      if (inColl)  buckets.collector[key] = inColl;
      if (inTH)    buckets.townHall[key] = inTH;
      if (take)    stealable[key] = take;

      totals.storage += inStore; totals.collector += inColl; totals.townHall += inTH; totals.stealable += take;

      if (inStore || inColl || inTH) {
        rows.push({ resource: key, label: def.label, lootable: !!def.lootable,
                    storage: inStore, collector: inColl, townHall: inTH,
                    held: held + inColl, stealable: take,
                    takeStorage: takeStore, takeCollector: takeColl, takeTownHall: takeTH,
                    protectedByHall: (def.lootable && !thDown) ? inTH : 0 });
      }
    }
    return { now: now, townHall: townHallLevel(p), townHallDestroyed: thDown,
             rates: { collector: LOOT_RATE.collector, storage: LOOT_RATE.storage, townHall: LOOT_RATE.townHall },
             buckets: buckets, stealable: stealable, detail: rows, totals: totals };
  }

  /* ---------------------------------------------------------------------- *
   * WRITE PATH -- the ONLY one, and it rides AK_ECON.mutateProfile
   * ---------------------------------------------------------------------- *
   * bank(resource, n) caps the deposit at capacity and RETURNS the waste so the
   * caller can prompt a storage upgrade. Never silently eats a haul without
   * saying so, and never lowers a balance that is already over cap.             */
  function bank(key, n, opts) {
    opts = opts || {};
    var econ = global.AK_ECON;
    if (!econ || !econ.mutateProfile) return { ok: false, error: 'NO_ECON', placed: 0, waste: 0 };
    var p0 = opts.profile || econ.loadProfile();
    var plan = distribute(p0, key, n, opts.now);
    if (!plan.ok) return { ok: false, error: plan.error, placed: 0, waste: 0 };
    if (plan.placed <= 0) return { ok: true, resource: key, placed: 0, waste: plan.waste, full: plan.full, plan: plan };
    econ.mutateProfile(function (p) { writeBal(p, key, readBal(p, key) + plan.placed); });
    return { ok: true, resource: key, placed: plan.placed, waste: plan.waste, full: plan.full,
             capacity: plan.capacity, after: plan.after, plan: plan };
  }

  // Human-readable one-liner for a HUD row. Returns a plain string: the caller
  // assigns it with textContent, so no markup ever crosses this boundary.
  function capacityLine(p, key, now) {
    var d = distribute(p, key, 0, now);
    if (!d.ok) return '';
    if (d.uncapped) return d.label + ': ' + d.held;
    return d.label + ': ' + d.held + ' / ' + d.capacity + (d.full ? '  FULL' : '');
  }

  /* ---------------------------------------------------------------------- *
   * EXPORTS -- always published (headless + server reuse the same math)
   * ---------------------------------------------------------------------- */
  global.AK_STORAGE = {
    RES: RES, RES_KEYS: RES_KEYS, STORAGE_TYPES: STORAGE_TYPES, LOOT_RATE: LOOT_RATE,
    PRODUCERS: PRODUCERS, PROD_MIRROR: PROD_MIRROR,
    unitCap: unitCap, thCapFor: thCapFor, storageUnits: storageUnits, holdersFor: holdersFor,
    splitOf: splitOf,                 // the pure even-fill algorithm
    capacityFor: capacityFor,         // total capacity per resource, from real building levels
    distribute: distribute,           // per-storage split + overflow report
    collectorHeld: collectorHeld,     // uncollected producer yield (asks production.js)
    pendingUnits: pendingUnits,
    lootableFrom: lootableFrom,       // storage vs collector vs town-hall buckets
    bank: bank,                       // the ONLY write path
    capacityLine: capacityLine,
    readBalance: readBal
  };

  // Register as a well-behaved AK_SYSTEMS module when the hub registry is present.
  if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) {
    global.AK_SYSTEMS.register({
      id: 'storages',
      init: function (ctx) { try { global.AK_STORAGE.ctx = ctx || null; } catch (_e) {} }
    });
  }
})(typeof window !== 'undefined' ? window : globalThis);
