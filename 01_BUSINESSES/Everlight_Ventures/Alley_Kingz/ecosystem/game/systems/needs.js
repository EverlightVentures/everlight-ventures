/* ==========================================================================
   ALLEY KINGZ // THE RUNNER NEEDS (AK-NEEDS 2026-07-09)
   THE LIVING RUNNER engine -- the Sims layer, canon-mapped. Spec: THE BLOCK
   CHRONICLES bible (../AK_BLOCK_CHRONICLES_BIBLE.md) Section 10 -- "MANGA AS
   GAME STATE" / "THE LIVING MANGA": the runner is ALIVE, the manga mood ring
   reads his needs, and AK_FLYWHEEL's nextAction() is the ad system that points
   a hungry/lonely/weary runner at the fix.

   TRANSLATION LAW (bible 10.1, operator: "don't rename anything, merge"):
     HUNGER  -- NEW field, p.runnerNeeds.hunger.  Fed by PRODUCE/CROPS (the farm
                economy's daily WHY -- economy.js sec 2/7 p.produce, p.crops).
     ENERGY  -- delegates to the EXISTING AK_ECON stamina pool ("Bones to Run",
                economy.js ~1302). NEVER a second energy field.
     MORALE  -- NEW field, p.runnerNeeds.morale (social+fun merged). Fed by
                chat / arcade / crew wins / dog barks.
     HONOR   -- delegates to the EXISTING AK_ECON.repRank ("Block Rep",
                economy.js ~1697/1812). NEVER a second honor field.

   Design contract (mirrors systems/flywheel.js, the sibling "brain" module):
   - DETERMINISTIC: same profile + same clock => same answer. No RNG.
   - GUARDED: every path is wrapped; the module NEVER throws. Missing AK_ECON
     degrades to a safe neutral default (never an exception, never a crash).
   - HEADLESS-SAFE: zero load-time DOM, zero top-level localStorage access.
   - FALSY-SAFE LAZY FIELD (the AK-STAMINA idiom, economy.js ~1310): an
     untouched profile has no p.runnerNeeds and reads FULL -- a new or
     returning runner is never punished for time that passed off-screen.
     Decay only starts ticking once feed()/boostMorale() first stamps a
     timestamp; from then on state() computes it lazily from that stamp on
     every read -- no timers, no periodic writes.
   - Needs read/write ONLY through AK_ECON.mutateProfile lazy fields. This
     file duplicates NOTHING that AK_ECON already owns (stamina, repRank,
     produce, crops).

   Include order: AFTER economy.js (AK_ECON). AK_FLYWHEEL wiring (nextAction
   consulting adSuggestion) is a LATER lane -- this file only exposes the API.
     <script src="systems/needs.js"></script>

   Public API on window.AK_NEEDS:
     state(p?)        -> { hunger, energy, morale, honor:{index,name},
                            tier:{hunger,energy,morale,honor} }
     mood(p?)          -> 'thriving'|'hungry'|'lonely'|'weary'|'dishonored'|'neutral'
     combatMods(p?)    -> { dmgMult, missAdd }
     adSuggestion(p?)  -> { line, screen, target } | null
     feed(mealId|n?)   -> { ok, value, spent, meal, morale } | { ok:false, error, value }
     boostMorale(kind?, n?) -> { ok, value, amount, kind }
     productionMods(p?)-> { rateMult, capMult, morale, hunger, tier }   [AK-SIMLOOP]
     rest(kind?)       -> { ok, value, kind, paid, stamina? }           [AK-SIMLOOP]
     noteRaid(opts?)   -> { ok, hunger, morale, raids }                 [AK-SIMLOOP]

   AK-SIMLOOP 2026-07-18 -- THE CIRCLE CLOSES. Before this pass needs only COST
   (combatMods docked melee damage) and nothing on the board fed them back:
     morale low -> raid -> win -> hungry -> garden -> eat -> replant -> seeds
     -> shop -> gold -> upgrade cards/rigs -> raid again -> morale high
   Three new links: productionMods() makes morale COST YIELD (systems/production.js
   is the consumer); feed(mealId)/rest(kind) spend REAL profile resources
   (p.produce/p.crops, p.coins) to buy needs back; noteRaid() makes raiding
   actually MOVE the needs and starts the lazy time-decay clock. combatMods()
   rings noteRaid() itself (debounced), so the raid half needs no host edit.
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- guarded dependency handle -------------------------------------------
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }

  function num(v, d) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function now() { return Date.now(); }

  // ---- tunables (bible 10.1 table, "PT-day gentle") ------------------------
  var DAY_MS = 86400000;
  var NEEDS_MAX = 100;
  var NEEDS_FLOOR = 15;               // "floors at 15 (never zero-locked)"
  var HUNGER_DECAY_PER_DAY = 18;
  var MORALE_DECAY_PER_DAY = 12;
  var HUNGER_PER_UNIT = 12;           // 1 produce/crop unit fed = +12 hunger, cap 100
  var DANGER_AT = 25;                 // combatMods threshold; also the tier "danger" cutoff
  var TIER_LOW_AT = 50;
  var TIER_OK_AT = 75;
  // MORALE_BOOST: event -> flat morale gain (chat/arcade/crew-win/dog-bark hooks).
  // Keys are normalized (lowercased, non-alnum stripped) so "crew-win"/"crewWin"/
  // "crew_win" all resolve the same.
  var MORALE_BOOST = { chat: 6, arcade: 8, crewwin: 15, dogbark: 4, default: 5 };

  // ---- AK-SIMLOOP 2026-07-18 tunables (the PRODUCTION + ACTIVITY half) -----
  // Closing the operator circle: morale low -> raid -> win -> hungry -> garden
  // -> eat -> replant -> seeds -> shop -> gold -> upgrade -> raid -> morale high.
  // Needs already COST damage (combatMods). These make them COST YIELD, make the
  // farm PAY them back, and make raiding actually MOVE them.
  var PROD_DANGER_MULT   = 0.75;  // morale in the danger band: the row crawls
  var PROD_LOW_MULT      = 0.90;
  var PROD_OK_MULT       = 1.00;  // the neutral band == today's exact numbers
  var PROD_THRIVING_MULT = 1.15;  // high morale: the row hums
  var PROD_STARVE_MULT   = 0.90;  // starving drags on TOP of the morale band
  var PROD_STARVE_CAP    = 0.85;  // ...and a starving runner hauls a smaller load
  var PROD_CACHE_MS      = 1000;  // memo TTL: production.js hits this per building per frame

  // MEALS (bible 10.1, the farm's daily WHY): mealId -> REAL produce/crop units.
  // A bigger meal feeds the belly AND lifts the mood (eating together is social).
  var MEALS = {
    scraps: { units: 1, hunger: 12, morale: 0,  label: "Table Scraps" },
    bowl:   { units: 2, hunger: 30, morale: 3,  label: "Full Bowl" },
    feast:  { units: 5, hunger: 80, morale: 12, label: "Block Feast" }
  };
  var DEFAULT_MEAL = "scraps";

  // REST (bible 10.1, the KENNEL): kind -> REAL gold spent. 'nap' is the FREE
  // path (cooldown-gated) so a broke runner is never locked out of morale --
  // the never-punish law. ENERGY stays AK_ECON's pool: 'bunk' DELEGATES to
  // AK_ECON.refillStamina, it never writes p.stamina from this file.
  var REST = {
    nap:    { gold: 0,   morale: 8,  cooldownMs: 1800000, label: "Quick Nap" },
    kennel: { gold: 40,  morale: 25, cooldownMs: 0,       label: "Kennel Bunk" },
    bunk:   { gold: 120, morale: 50, cooldownMs: 0,       refill: true, label: "Deep Sleep" }
  };
  var DEFAULT_REST = "nap";

  // RAID drain: one run burns this much. The stamp it writes is the real prize --
  // a fresh profile has fedT/socialT = 0 (frozen full); the first raid STARTS the
  // time-decay clock, so needs stop sitting static the moment the player plays.
  // MORALE_COST is set against the existing crew-win payback (+15, MORALE_BOOST
  // above) so the BREAK-EVEN win rate lands near 50%: win more than half your
  // runs and morale climbs, lose more than half and it bleeds. Tuned up from a
  // first-pass 4 because the sim showed 4 pinned morale at 100 through a 3-loss
  // day, which made the whole morale lever inert.
  var RAID_HUNGER_COST  = 9;
  var RAID_MORALE_COST  = 8;
  var RAID_DRAIN_MIN_MS = 45000;  // debounce for the combatMods() auto-bell

  function normKind(kind) { return String(kind || "").toLowerCase().replace(/[^a-z0-9]/g, ""); }

  // ---- profile plumbing (mirrors flywheel.js readProfile) ------------------
  function readProfile(p) {
    if (p && typeof p === "object") return p;
    var e = econ();
    if (e && typeof e.loadProfile === "function") {
      try { var lp = e.loadProfile(); if (lp && typeof lp === "object") return lp; } catch (_) {}
    }
    return {};   // AK_ECON absent -> a bare shape; every read below is falsy-safe against it
  }

  // Lazily create the field (ONLY called from inside a mutateProfile closure --
  // feed()/boostMorale(). state() itself never creates this field; it is a
  // PURE read). Sentinel fedT/socialT = 0 means "never touched" -> full, no
  // decay (the falsy-safe law).
  function ensureNeedsShape(p) {
    if (!p.runnerNeeds || typeof p.runnerNeeds !== "object") {
      p.runnerNeeds = { hunger: NEEDS_MAX, morale: NEEDS_MAX, fedT: 0, socialT: 0 };
    }
    return p.runnerNeeds;
  }

  // Pure decay: a value stamped at `storedT` decays toward the floor at
  // `perDay`. storedT === 0 (sentinel, "never touched") => NO decay, return
  // the stored value as-is (untouched need == full, mirrors staminaState's
  // "absent state -> full" contract). PURE -- no writes, no timers.
  function decayFrom(storedVal, storedT, t, perDay) {
    var val = clampN(num(storedVal, NEEDS_MAX), NEEDS_FLOOR, NEEDS_MAX);
    var st = num(storedT, 0);
    if (!st) return val;                                    // never touched -> as-is
    if (st > t) st = t;                                      // clock-skew guard (mirrors staminaState)
    var elapsedDays = Math.max(0, t - st) / DAY_MS;
    return clampN(val - perDay * elapsedDays, NEEDS_FLOOR, NEEDS_MAX);
  }

  function liveHunger(p, t) {
    var rn = p && p.runnerNeeds;
    if (!rn || typeof rn !== "object") return NEEDS_MAX;      // untouched profile -> full
    return decayFrom(rn.hunger, rn.fedT, t, HUNGER_DECAY_PER_DAY);
  }
  function liveMorale(p, t) {
    var rn = p && p.runnerNeeds;
    if (!rn || typeof rn !== "object") return NEEDS_MAX;      // untouched profile -> full
    return decayFrom(rn.morale, rn.socialT, t, MORALE_DECAY_PER_DAY);
  }

  // ---- ENERGY: delegate to the EXISTING AK_ECON stamina pool ("Bones to Run").
  // NEVER a second energy field -- this reads AK_ECON's live stamina and maps
  // it 0..100. staminaState() is the pure read but is not currently exported
  // on AK_ECON, so raidStamina(p) (the exported public wrapper) is the primary
  // path; staminaState is tried first only in case a future export adds it.
  function liveEnergy(p) {
    var e = econ();
    if (e && typeof e.staminaState === "function") {
      try {
        var s = e.staminaState(p, now());
        var max = num(s.max, 0) || 1;
        return clampN((num(s.cur, 0) / max) * 100, 0, 100);
      } catch (_) {}
    }
    if (e && typeof e.raidStamina === "function") {
      try {
        var s2 = e.raidStamina(p);
        var max2 = num(s2.max, 0) || 1;
        return clampN((num(s2.cur, 0) / max2) * 100, 0, 100);
      } catch (_) {}
    }
    return NEEDS_MAX;   // AK_ECON absent -> inert module law: neutral/full, never punished
  }

  // ---- HONOR: delegate to the EXISTING AK_ECON.repRank ("Block Rep"). NEVER
  // a second honor field. pct is an INTERNAL severity scale (0..100, index
  // normalized across the 7-rung REP_LADDER) used only for tier/mood/ad
  // decisions -- it is never surfaced on the public state() object. Read
  // from repRank with a STARTER SHIELD: a fresh save genuinely IS a Stray, but
  // "dishonored" mood/cracked-border art on someone's first minute violates the
  // never-punish-a-new-player law (and mirrors repRank's own demotion shield for
  // the bottom rungs). Stray/Pup/Runner (idx 0-2) floor at the "ok" band; the
  // dishonored danger band is reachable only from Warrior+ by actually falling.
  function liveHonor(p) {
    var e = econ();
    if (e && typeof e.repRank === "function") {
      try {
        var r = e.repRank(p);
        var ladderLen = (e.REP_LADDER && e.REP_LADDER.length) || 7;
        var idx = num(r.index, 0);
        var pct = clampN((idx / Math.max(1, ladderLen - 1)) * 100, 0, 100);
        if (idx <= 2) pct = Math.max(pct, TIER_LOW_AT + 1);   // starter shield: never "danger"/dishonored at the entry rungs
        return { index: idx, name: String(r.rank || "Stray"), pct: pct };
      } catch (_) {}
    }
    // AK_ECON absent/broken -> inert module law: neutral (never falsely "dishonored"
    // just because the dependency didn't load).
    return { index: 0, name: "Stray", pct: NEEDS_MAX };
  }

  function tierOf(v) {
    if (v <= DANGER_AT) return "danger";
    if (v <= TIER_LOW_AT) return "low";
    if (v <= TIER_OK_AT) return "ok";
    return "thriving";
  }

  // Internal full readout (adds honor.pct for severity comparisons that state()
  // does not expose publicly). Every public read funnels through this ONE
  // pure computation so state()/mood()/combatMods()/adSuggestion() never drift.
  function compute(p) {
    p = readProfile(p);
    var t = now();
    var hunger = liveHunger(p, t);
    var morale = liveMorale(p, t);
    var energy = liveEnergy(p);
    var honor = liveHonor(p);
    return {
      hunger: hunger, energy: energy, morale: morale, honor: honor,
      tier: {
        hunger: tierOf(hunger),
        energy: tierOf(energy),
        morale: tierOf(morale),
        honor: tierOf(honor.pct)
      }
    };
  }

  // ==========================================================================
  // state(p?) -- the one read every surface (manga mood ring, HUD, raid loop)
  // calls. PURE: never mutates, never creates p.runnerNeeds. Absent AK_ECON /
  // untouched profile => neutral/full (inert-module law).
  // ==========================================================================
  function state(p) {
    try {
      var c = compute(p);
      return {
        hunger: c.hunger, energy: c.energy, morale: c.morale,
        honor: { index: c.honor.index, name: c.honor.name },
        tier: { hunger: c.tier.hunger, energy: c.tier.energy, morale: c.tier.morale, honor: c.tier.honor }
      };
    } catch (_) {
      return {
        hunger: NEEDS_MAX, energy: NEEDS_MAX, morale: NEEDS_MAX,
        honor: { index: 0, name: "Stray" },
        tier: { hunger: "thriving", energy: "thriving", morale: "thriving", honor: "thriving" }
      };
    }
  }

  // ==========================================================================
  // mood() -> ONE word for the manga mood ring (bible 10.2). Priority: the
  // WORST danger wins -- among needs currently in the "danger" tier, the one
  // with the lowest severity value (furthest below its floor) wins; ties break
  // in hunger > morale > energy > honor order (array scan order, strict `<`).
  // All four thriving -> 'thriving'. Anything else -> 'neutral'.
  // ==========================================================================
  function mood(p) {
    try {
      var c = compute(p);
      var candidates = [
        { word: "hungry", tier: c.tier.hunger, v: c.hunger },
        { word: "lonely", tier: c.tier.morale, v: c.morale },
        { word: "weary", tier: c.tier.energy, v: c.energy },
        { word: "dishonored", tier: c.tier.honor, v: c.honor.pct }
      ];
      var worst = null;
      for (var i = 0; i < candidates.length; i++) {
        var cand = candidates[i];
        if (cand.tier !== "danger") continue;
        if (!worst || cand.v < worst.v) worst = cand;
      }
      if (worst) return worst.word;
      var allThriving = c.tier.hunger === "thriving" && c.tier.energy === "thriving" &&
                         c.tier.morale === "thriving" && c.tier.honor === "thriving";
      return allThriving ? "thriving" : "neutral";
    } catch (_) { return "neutral"; }
  }

  // ==========================================================================
  // combatMods(p?) -> the raid loop's hook (bible 10.1 danger-state column).
  // ==========================================================================
  function combatMods(p) {
    try {
      var c = compute(p);
      var mods = {
        dmgMult: c.hunger <= DANGER_AT ? 0.75 : 1,
        missAdd: c.morale <= DANGER_AT ? 0.08 : 0
      };
      // AK-SIMLOOP 2026-07-18: this call IS the raid bell. index.html:1855 and
      // game.html:5757 each call combatMods() exactly once at raid/match start
      // to cache RAID.ndm / _akGaunt, so hanging the activity drain here closes
      // the loop with ZERO edits to those files. Order matters: mods are computed
      // BEFORE the drain, so the raid you are entering fights on the state you
      // entered it with. Debounced 45s, and SKIPPED when an explicit profile was
      // passed in (an explicit-profile read is a pure query, never the bell).
      if (!(p && typeof p === "object")) { try { autoRaidDrain(); } catch (_e) {} }
      return mods;
    } catch (_) { return { dmgMult: 1, missAdd: 0 }; }
  }

  // ==========================================================================
  // adSuggestion(p?) -> the thought-bubble line for AK_FLYWHEEL's ad engine
  // (bible 10.1: "a hungry runner's thought bubble points at the BARN/garden;
  // lonely points at Street Talk/arcade"). AK_FLYWHEEL wiring is a later lane;
  // this only exposes the API. null when nothing is in danger.
  // ==========================================================================
  function adSuggestion(p) {
    try {
      var c = compute(p);
      if (c.tier.hunger === "danger") {
        return { line: "Belly growling. Hit the garden or the BARN.", screen: "building", target: "BARN" };
      }
      if (c.tier.morale === "danger") {
        return { line: "Feeling cooped up. Catch some Street Talk or hit the Arcade.", screen: "building", target: "STREET" };
      }
      if (c.tier.energy === "danger") {
        return { line: "Running on empty. Let the Bones refill -- rest at the Kennel.", screen: "building", target: "KENNEL" };
      }
      return null;
    } catch (_) { return null; }
  }

  // ==========================================================================
  // feed(n?) -> consume produce (preferred) or crops (fallback) via
  // AK_ECON.mutateProfile. Each unit spent = +12 hunger, capped at 100. Gives
  // the farm economy its daily WHY (bible 10.1). n defaults to 1; non-positive
  // input normalizes to 1 (feed() with no args feeds one unit).
  // ==========================================================================
  // AK-SIMLOOP 2026-07-18: spend n units of REAL food (p.produce first, then
  // p.crops items) INSIDE a mutateProfile closure. Returns units actually taken
  // (0 = the pantry is bare). Extracted from the original feed() body so the
  // unit path and the meal path share ONE spend rule.
  function spendFood(p, n) {
    var avail = Math.max(0, p.produce | 0);
    var spend = Math.min(n, avail);
    var remain = n - spend;
    if (spend > 0) p.produce = avail - spend;
    if (remain > 0 && p.crops && typeof p.crops === "object") {
      var keys = Object.keys(p.crops);
      for (var i = 0; i < keys.length && remain > 0; i++) {
        var k = keys[i], have = Math.max(0, p.crops[k] | 0);
        var use = Math.min(have, remain);
        if (use > 0) { p.crops[k] = have - use; spend += use; remain -= use; }
      }
    }
    return spend;
  }

  // AK-SIMLOOP 2026-07-18: feed('bowl') is the MEAL path, feed(3) is the original
  // unit path (unchanged numbers -- 1 unit = +12 hunger). A partial pantry serves
  // a partial meal: gains scale by units actually eaten, never a silent full plate.
  function feed(meal) {
    var m = null, id = null, n;
    if (typeof meal === "string") {
      id = String(meal).toLowerCase();
      if (!MEALS[id]) id = DEFAULT_MEAL;
      m = MEALS[id]; n = m.units;
    } else {
      n = Math.floor(num(meal, 1));
      if (!(n > 0)) n = 1;
    }
    var e = econ();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECON", value: NEEDS_MAX };
    var out = { ok: false, error: "NO_FOOD", value: NEEDS_MAX };
    try {
      e.mutateProfile(function (p) {
        var t = now();
        ensureNeedsShape(p);
        var spend = spendFood(p, n);
        if (spend <= 0) { out = { ok: false, error: "NO_FOOD", value: liveHunger(p, t) }; return; }
        var share = m ? (spend / m.units) : 1;
        var next = clampN(liveHunger(p, t) + (m ? m.hunger * share : spend * HUNGER_PER_UNIT), NEEDS_FLOOR, NEEDS_MAX);
        p.runnerNeeds.hunger = next;
        p.runnerNeeds.fedT = t;
        var mor = null;
        if (m && m.morale > 0) {                    // a real meal lifts the mood too
          mor = clampN(liveMorale(p, t) + m.morale * share, NEEDS_FLOOR, NEEDS_MAX);
          p.runnerNeeds.morale = mor;
          p.runnerNeeds.socialT = t;
        }
        out = { ok: true, value: next, spent: spend, meal: id, morale: mor };
      });
    } catch (_) { return { ok: false, error: "FAIL", value: NEEDS_MAX }; }
    bumpCache();
    return out;
  }

  // ==========================================================================
  // AK-SIMLOOP 2026-07-18 -- rest(kind?) -> spend REAL gold (p.coins, the same
  // field production.js MINTs and charges for upgrades) to buy MORALE back.
  // kind: 'nap' (free, 30min cooldown) | 'kennel' (40g) | 'bunk' (120g, also
  // delegates a stamina refill to AK_ECON). ENERGY is never written here.
  // -> { ok, value, kind, paid:{gold}, stamina? } | { ok:false, error, ... }
  // ==========================================================================
  function rest(kind) {
    var id = String(kind == null ? DEFAULT_REST : kind).toLowerCase();
    if (!REST[id]) id = DEFAULT_REST;
    var r = REST[id];
    var e = econ();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECON", value: NEEDS_MAX };
    var out = { ok: false, error: "FAIL", value: NEEDS_MAX };
    try {
      e.mutateProfile(function (p) {
        var t = now();
        var rn = ensureNeedsShape(p);
        if (r.cooldownMs > 0) {
          var last = num(rn.restT, 0);
          if (last && (t - last) < r.cooldownMs && last <= t) {
            out = { ok: false, error: "COOLDOWN", waitMs: r.cooldownMs - (t - last), value: liveMorale(p, t) };
            return;
          }
        }
        var cost = r.gold | 0;
        if (cost > 0) {
          var have = Math.max(0, p.coins | 0);
          if (have < cost) { out = { ok: false, error: "NO_GOLD", have: have, need: cost, value: liveMorale(p, t) }; return; }
          p.coins = have - cost;
        }
        var next = clampN(liveMorale(p, t) + r.morale, NEEDS_FLOOR, NEEDS_MAX);
        rn.morale = next; rn.socialT = t; rn.restT = t;
        out = { ok: true, value: next, kind: id, paid: { gold: cost } };
      });
    } catch (_) { return { ok: false, error: "FAIL", value: NEEDS_MAX }; }
    // ENERGY stays AK_ECON's pool -- delegate, never duplicate p.stamina here.
    // Best-effort: a failed/short-on-bones refill never fails the rest itself.
    if (out.ok && r.refill && typeof e.refillStamina === "function") {
      try { out.stamina = e.refillStamina("bones"); } catch (_) {}
    }
    bumpCache();
    return out;
  }

  // ==========================================================================
  // AK-SIMLOOP 2026-07-18 -- noteRaid(opts?) -> ACTIVITY decay. A run burns the
  // belly and grinds the mood; the existing boostMorale('crew-win') hook
  // (index.html:2043) is what pays the mood back on a WIN, so a winning streak
  // nets positive morale and a losing grind nets negative. The stamp it writes
  // is what starts the lazy TIME decay on a previously untouched profile.
  // opts: { hunger?, morale? } override the per-raid cost.
  // -> { ok, hunger, morale, raids } | { ok:false, error }
  // ==========================================================================
  function noteRaid(opts) {
    opts = opts || {};
    var hCost = Math.max(0, num(opts.hunger, RAID_HUNGER_COST));
    var mCost = Math.max(0, num(opts.morale, RAID_MORALE_COST));
    var e = econ();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECON" };
    var out = { ok: false, error: "FAIL" };
    try {
      e.mutateProfile(function (p) {
        var t = now();
        var rn = ensureNeedsShape(p);
        var h = clampN(liveHunger(p, t) - hCost, NEEDS_FLOOR, NEEDS_MAX);
        var m = clampN(liveMorale(p, t) - mCost, NEEDS_FLOOR, NEEDS_MAX);
        rn.hunger = h; rn.fedT = t;      // stamping the clock is what STARTS time decay
        rn.morale = m; rn.socialT = t;
        rn.raids = (rn.raids | 0) + 1;
        out = { ok: true, hunger: h, morale: m, raids: rn.raids };
      });
    } catch (_) { return { ok: false, error: "FAIL" }; }
    _lastRaidT = now();
    bumpCache();
    return out;
  }

  // The debounced bell rung from combatMods(). Claims the window BEFORE the
  // write so a re-entrant / double call in the same tick can only drain once.
  var _lastRaidT = 0;
  function autoRaidDrain() {
    var t = now();
    if (_lastRaidT && (t - _lastRaidT) < RAID_DRAIN_MIN_MS) return false;
    _lastRaidT = t;
    noteRaid();
    return true;
  }

  // ==========================================================================
  // AK-SIMLOOP 2026-07-18 -- productionMods(p?) -> the PRODUCER hook, mirroring
  // combatMods() so consumers adopt it identically (guarded call, read a mult,
  // multiply). Low morale slows accrual, high morale speeds it; starving drags
  // the rate further and shrinks the haul cap.
  //   rateMult  -- multiply the per-hour accrual rate (morale band x starve drag)
  //   capMult   -- multiply the storage cap (hunger)
  //   engaged   -- false until the player first raids/feeds/rests (mods pinned to 1)
  // Absent AK_ECON / untouched profile => { rateMult:1, capMult:1 } == today's
  // exact numbers (the inert-module law: no AK_NEEDS changes nothing, and a
// broken dependency must never INFLATE yield -- see the engagement gate below).
  // 60fps-safe: the no-arg read is memoized for PROD_CACHE_MS and invalidated on
  // every mutation, because production.js calls this per building per frame.
  // Passing an explicit profile bypasses the cache and stays PURE.
  // ==========================================================================
  var _pmCache = null, _pmAt = 0, _pmVer = -1, _ver = 0;
  function bumpCache() { _ver++; _pmCache = null; }

  function prodBandMult(morale) {
    if (morale <= DANGER_AT) return PROD_DANGER_MULT;
    if (morale <= TIER_LOW_AT) return PROD_LOW_MULT;
    if (morale <= TIER_OK_AT) return PROD_OK_MULT;
    return PROD_THRIVING_MULT;
  }

  function computeProdMods(p) {
    p = readProfile(p);
    var c = compute(p);
    // ENGAGEMENT GATE. The falsy-safe law makes an UNTOUCHED profile read FULL,
    // and full morale would otherwise hand out the +15% thriving bonus forever
    // to a player who never engaged -- and, worse, would let a missing/broken
    // AK_ECON silently INFLATE producer yield. Absent state is therefore
    // NEUTRAL (1.0, today's exact numbers), not thriving. The lever arms itself
    // the moment the loop actually starts (noteRaid/feed/rest stamp the clock).
    var rn = p && p.runnerNeeds;
    var engaged = !!(rn && typeof rn === "object" && (num(rn.fedT, 0) || num(rn.socialT, 0)));
    if (!engaged) {
      return { rateMult: 1, capMult: 1, morale: c.morale, hunger: c.hunger, tier: c.tier.morale, engaged: false };
    }
    var rate = prodBandMult(c.morale);
    if (c.hunger <= DANGER_AT) rate *= PROD_STARVE_MULT;
    return {
      rateMult: Math.round(rate * 1000) / 1000,
      capMult: c.hunger <= DANGER_AT ? PROD_STARVE_CAP : 1,
      morale: c.morale,
      hunger: c.hunger,
      tier: c.tier.morale,
      engaged: true
    };
  }

  function productionMods(p) {
    try {
      if (p && typeof p === "object") return computeProdMods(p);          // explicit profile -> pure, uncached
      var t = now();
      if (_pmCache && _pmVer === _ver && (t - _pmAt) < PROD_CACHE_MS && t >= _pmAt) return _pmCache;
      _pmCache = computeProdMods(null); _pmAt = t; _pmVer = _ver;
      return _pmCache;
    } catch (_) {
      return { rateMult: 1, capMult: 1, morale: NEEDS_MAX, hunger: NEEDS_MAX, tier: "thriving" };
    }
  }

  // ==========================================================================
  // boostMorale(kind?, n?) -> event hook for chat / arcade / crew-win / dog-bark
  // beats. n overrides the table amount when passed a finite number.
  // ==========================================================================
  function boostMorale(kind, n) {
    var amt = (typeof n === "number" && isFinite(n)) ? n : (MORALE_BOOST[normKind(kind)] != null ? MORALE_BOOST[normKind(kind)] : MORALE_BOOST["default"]);
    amt = Math.max(0, amt);
    var e = econ();
    if (!e || typeof e.mutateProfile !== "function") return { ok: false, error: "NO_ECON", value: NEEDS_MAX };
    var out = { ok: false, error: "FAIL", value: NEEDS_MAX };
    try {
      e.mutateProfile(function (p) {
        var t = now();
        ensureNeedsShape(p);
        var cur = liveMorale(p, t);
        var next = clampN(cur + amt, NEEDS_FLOOR, NEEDS_MAX);
        p.runnerNeeds.morale = next;
        p.runnerNeeds.socialT = t;
        out = { ok: true, value: next, amount: amt, kind: kind || null };
      });
    } catch (_) { return { ok: false, error: "FAIL", value: NEEDS_MAX }; }
    bumpCache();   // AK-SIMLOOP 2026-07-18: morale moved -> productionMods() must re-read
    return out;
  }

  // ---- export ---------------------------------------------------------------
  global.AK_NEEDS = {
    state: state,               // (p?) -> {hunger,energy,morale,honor:{index,name},tier:{hunger,energy,morale,honor}}
    mood: mood,                 // (p?) -> 'thriving'|'hungry'|'lonely'|'weary'|'dishonored'|'neutral'
    combatMods: combatMods,     // (p?) -> {dmgMult,missAdd}
    adSuggestion: adSuggestion, // (p?) -> {line,screen,target} | null
    feed: feed,                 // (mealId|n?) -> {ok,value,spent,meal,morale} | {ok:false,error,value}
    boostMorale: boostMorale,   // (kind?,n?) -> {ok,value,amount,kind}
    // === AK-SIMLOOP 2026-07-18: the half that closes the circle ===
    productionMods: productionMods, // (p?) -> {rateMult,capMult,morale,hunger,tier} -- production.js hook
    rest: rest,                 // (kind?) -> {ok,value,kind,paid:{gold},stamina?} | {ok:false,error,...}
    noteRaid: noteRaid,         // (opts?) -> {ok,hunger,morale,raids} -- activity decay (auto-rung by combatMods)
    MEALS: MEALS,               // mealId -> {units,hunger,morale,label}
    REST: REST,                 // restId -> {gold,morale,cooldownMs,label}
    // exposed tunables for hosts/tests
    NEEDS_MAX: NEEDS_MAX,
    NEEDS_FLOOR: NEEDS_FLOOR,
    HUNGER_DECAY_PER_DAY: HUNGER_DECAY_PER_DAY,
    MORALE_DECAY_PER_DAY: MORALE_DECAY_PER_DAY,
    DANGER_AT: DANGER_AT,
    RAID_HUNGER_COST: RAID_HUNGER_COST,
    RAID_MORALE_COST: RAID_MORALE_COST,
    RAID_DRAIN_MIN_MS: RAID_DRAIN_MIN_MS
  };
})(typeof window !== "undefined" ? window : globalThis);
