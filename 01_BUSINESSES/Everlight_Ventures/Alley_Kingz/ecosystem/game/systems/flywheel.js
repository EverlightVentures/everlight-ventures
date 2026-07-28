/* ==========================================================================
   ALLEY KINGZ // THE FLYWHEEL (AK-FLYWHEEL 2026-07-01)
   The single "what do I do next?" brain. PURE LOGIC -- zero UI, zero DOM,
   zero writes. It reads the live economy + story + duties and points the
   player at the single most rewarding next move, so the core loop always
   chains forward:

       raid -> loot -> upgrade -> stronger deck -> climb the ladder
             -> unlock the next Crown Bloodline chapter -> raid again

   Design contract (why this file exists):
   - DETERMINISTIC: same profile + same clock => same answer. No RNG.
   - GUARDED: every path is wrapped; the module NEVER throws. A missing
     dependency (AK_ECON / AKStory / AKDuties absent) degrades to a safe
     default, never an exception. Safe on a headless node harness.
   - READ-ONLY: it only calls PURE reads (loadProfile / buildingDamage /
     repairQuote(p) / buildingBenefit / townHallLevel(p) / stage() /
     AKDuties.today()). It writes NOTHING and adds NO persisted profile
     fields. A zero-state profile is byte-identical after any call.

   Include order: AFTER economy.js + story.js + missions.js (so AK_ECON /
   AKStory / AKDuties are present). It self-gates if they are not, so load
   order can never break it.
     <script src="systems/flywheel.js"></script>

   Public API on window.AK_FLYWHEEL:
     nextAction(p?)  -> { label, why, cta, target, screen }   (HUD beacon)
     dailyAgenda(p?) -> { list:[{label,done,goal,cta}], resetsInMs? }
     chainHint()     -> string   (one-line "where you are in the loop")
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- guarded dependency handles ----------------------------------------
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function story() { try { return global.AKStory || null; } catch (_) { return null; } }
  function duties() { try { return global.AKDuties || null; } catch (_) { return null; } }

  function num(v, d) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function now() { return Date.now(); }

  // ONE read of the profile. econ.loadProfile() is a pure read (localStorage ->
  // ensureShape); if econ is absent we hand back a minimal zero-state shape so
  // every downstream read is falsy-safe and never throws.
  function readProfile(p) {
    if (p && typeof p === "object") return p;
    var e = econ();
    if (e && typeof e.loadProfile === "function") {
      try { var lp = e.loadProfile(); if (lp && typeof lp === "object") return lp; } catch (_) {}
    }
    return { coins: 0, owned: [], prod: {}, baseDmg: {}, townHall: 1, trophies: 0 };
  }

  // ---- building id / name tables -----------------------------------------
  // ALL hub buildings (matches index.html const LV). The 5 PRODUCERS are the
  // income engine (GEM/MINT/FORGE/LAB/GEN). ARENA == the Town Hall meta-gate.
  var PRODUCER_IDS = ["GEM", "MINT", "FORGE", "LAB", "GEN"];
  var BUILDING_IDS = [
    "ARENA", "GEM", "MINT", "FORGE", "LAB", "GEN", "TROPHY", "FIXER", "GARAGE",
    "DROP", "KENNEL", "CLAN", "PASS", "WARD", "ARCH", "STREET", "ARCADE", "INFIRMARY"
  ];
  // MIRROR of index.html `const LV` / economy.js LV_BASE -- the default level the
  // hub SHOWS a building at when the profile has no p.prod entry yet. Kept here so
  // a producer-upgrade beacon quotes the SAME level the panel displays.
  var LV_BASE = {
    ARENA: 8, TROPHY: 4, FIXER: 3, GARAGE: 6, DROP: 5, KENNEL: 4, CLAN: 5, PASS: 2,
    WARD: 3, ARCH: 2, STREET: 3, ARCADE: 1, GEM: 5, MINT: 4, FORGE: 3, LAB: 3, GEN: 4, INFIRMARY: 1
  };
  // Friendly display names for the beacon copy (falls back to Title-cased id).
  var NAMES = {
    ARENA: "Town Hall", GEM: "Gem Mine", MINT: "Mint", FORGE: "Forge", LAB: "Lab",
    GEN: "Generator", TROPHY: "Trophy Room", FIXER: "Fixer", GARAGE: "Garage",
    DROP: "Drop Shop", KENNEL: "Kennel", CLAN: "Clan Hall", PASS: "Alley Pass",
    WARD: "Wardrobe", ARCH: "Codex", STREET: "Street", ARCADE: "Arcade", INFIRMARY: "Infirmary"
  };
  function bldName(id) {
    if (NAMES[id]) return NAMES[id];
    id = String(id || "");
    return id ? id.charAt(0) + id.slice(1).toLowerCase() : "building";
  }

  // MIRROR of production.js CFG.costBase + growth + MAX_LVL (that module registers
  // with AK_SYSTEMS and exposes NO global, so -- exactly like economy.js mirrors
  // its RATE_GROWTH/CAP_HOURS -- we carry the same constants and label them. If
  // production.js retunes these, retune here too.)
  var PROD_COST_BASE = { GEM: 180, MINT: 200, FORGE: 220, LAB: 260, GEN: 300 };
  var PROD_COST_GROWTH = 1.5;
  var PROD_MAX_LVL = 10;

  // Displayed level of a building: live p.prod entry wins, else the hub default.
  function bldLvl(p, id) {
    try {
      var e = p && p.prod && p.prod[id];
      var v = e && e.lvl;
      if (typeof v === "number" && isFinite(v) && v >= 1) return Math.floor(v);
    } catch (_) {}
    return LV_BASE[id] || 1;
  }
  // Gold cost to raise a producer one level (mirror of production.js upCost).
  // Infinity if already maxed (so it is never the "cheapest" pick).
  function producerUpCost(p, id) {
    var lvl = bldLvl(p, id);
    if (lvl >= PROD_MAX_LVL) return Infinity;
    var base = PROD_COST_BASE[id] || 200;
    return Math.round(base * Math.pow(PROD_COST_GROWTH, Math.max(0, lvl - 1)));
  }

  function spareGold(p) { return Math.max(0, (p && p.coins) | 0); }
  function hasDeck(p) {
    try { return !!(p && Array.isArray(p.owned) && p.owned.length > 0); } catch (_) { return false; }
  }

  // ---- pure economy reads (all take the profile; none mutate) -------------
  function dmgOf(p, id, t) {
    var e = econ();
    if (!e || typeof e.buildingDamage !== "function") return 0;
    try { return num(e.buildingDamage(p, id, t), 0); } catch (_) { return 0; }
  }
  function repairCost(p, id, t) {
    var e = econ();
    if (!e || typeof e.repairQuote !== "function") return 0;
    try { var q = e.repairQuote(p, id, t); return q && isFinite(q.cost) ? q.cost : 0; } catch (_) { return 0; }
  }
  function thLevel(p) {
    var e = econ();
    if (e && typeof e.townHallLevel === "function") { try { return num(e.townHallLevel(p), 1); } catch (_) {} }
    return Math.max(1, (p && p.townHall | 0) || 1);
  }
  function thCost(lv) {
    var e = econ();
    if (e && typeof e.townHallCost === "function") { try { return num(e.townHallCost(lv), Infinity); } catch (_) {} }
    return 500 * lv * lv;   // mirror of economy.js townHallCost
  }
  function benefitDelta(id, lv) {
    var e = econ();
    if (!e || typeof e.buildingBenefit !== "function") return "";
    try { var b = e.buildingBenefit(id, lv); return (b && b.deltaLabel) ? String(b.deltaLabel) : ""; } catch (_) { return ""; }
  }
  function division(p) {
    var e = econ();
    if (e && typeof e.rankDivision === "function") { try { return String(e.rankDivision((p && p.trophies) | 0)); } catch (_) {} }
    return "Stray";
  }
  function storyStage() {
    var s = story();
    if (!s || typeof s.stage !== "function") return null;
    try { var st = s.stage(); return (st && typeof st === "object") ? st : null; } catch (_) { return null; }
  }
  function storyBanner() {
    var s = story();
    if (!s || typeof s.banner !== "function") return "";
    try { return String(s.banner() || ""); } catch (_) { return ""; }
  }

  // ==========================================================================
  // 1) nextAction(p?) -> the single best next move.
  // Priority (highest applicable wins, every branch guarded):
  //   a. a building is damaged (>0.1)        -> REPAIR   (screen:"building")
  //   b. cheapest producer upgrade affordable -> UPGRADE (screen:"building")
  //   c. Town Hall can raise + affordable     -> UPGRADE (screen:"townhall")
  //   d. you have a deck / a hero             -> RAID     (screen:"raidmap")
  //   e. a story objective is pending         -> STORY    (screen:"story")
  //   f. default                              -> EXPLORE  (screen:"hub")
  // ==========================================================================
  function nextAction(p) {
    try {
      p = readProfile(p);
      var t = now();

      // (a) DAMAGE first -- a cracked base bleeds yield; patch it before farming.
      // Only p.baseDmg keys can carry damage, so iterate those (cheap + correct).
      var worstId = null, worstDmg = 0;
      try {
        var dm = p && p.baseDmg;
        if (dm && typeof dm === "object") {
          for (var id in dm) {
            if (!dm.hasOwnProperty(id)) continue;
            var d = dmgOf(p, id, t);
            if (d > worstDmg) { worstDmg = d; worstId = id; }
          }
        }
      } catch (_) {}
      if (worstId && worstDmg > 0.1) {
        var rc = repairCost(p, worstId, t);
        return {
          label: "Repair the " + bldName(worstId),
          why: "Raiders cracked your " + bldName(worstId) + " -- fix it" + (rc ? " for " + rc + "g" : "") + " before the yield bite eats your haul.",
          cta: "REPAIR", target: worstId, screen: "building"
        };
      }

      // (b) PRODUCER UPGRADE -- the income leg of the loop. Pick the cheapest
      // upgradeable producer; point at it only if the spare gold covers it.
      var gold = spareGold(p);
      var pickId = null, pickCost = Infinity;
      for (var i = 0; i < PRODUCER_IDS.length; i++) {
        var pid = PRODUCER_IDS[i];
        var c = producerUpCost(p, pid);
        if (isFinite(c) && c < pickCost) { pickCost = c; pickId = pid; }
      }
      if (pickId && isFinite(pickCost) && gold >= pickCost) {
        var lv = bldLvl(p, pickId);
        var delta = benefitDelta(pickId, lv);
        return {
          label: "Upgrade the " + bldName(pickId),
          why: (delta ? delta + "  " : "") + "(" + pickCost + "g) -- more haul every time you walk in and collect.",
          cta: "UPGRADE", target: pickId, screen: "building"
        };
      }

      // (c) RAISE THE TOWN HALL -- the meta-gate. Raising it lifts every card's
      // level cap, builders, crew, grid, tools. The master progression beat.
      var thLv = thLevel(p);
      if (thLv < PROD_MAX_LVL) {
        var thc = thCost(thLv);
        if (isFinite(thc) && gold >= thc) {
          var thDelta = benefitDelta("ARENA", thLv);
          return {
            label: "Raise the Town Hall",
            why: (thDelta ? thDelta + "  " : "") + "(" + thc + "g) -- lift the ceiling on your whole deck.",
            cta: "UPGRADE", target: "ARENA", screen: "townhall"
          };
        }
      }

      // (d) RUN A RAID -- the engine of the loop. If you hold a deck, raiding is
      // always the most rewarding actionable move: loot in, upgrade next.
      if (hasDeck(p)) {
        return {
          label: "Run a raid",
          why: "Your deck is loaded -- raid a rival stash for loot, then upgrade and climb.",
          cta: "RAID", target: null, screen: "raidmap"
        };
      }

      // (e) STORY -- a pending Crown Bloodline objective (no deck yet to raid with).
      var st = storyStage();
      if (st && st.objective) {
        return {
          label: String(st.title || "Your story"),
          why: String(st.objective),
          cta: "STORY", target: (st.id || null), screen: "story"
        };
      }

      // (f) DEFAULT -- hit the streets. Come up from Stray to King.
      return {
        label: "Run the streets",
        why: storyBanner() || "Come up from Stray to King",
        cta: "EXPLORE", target: null, screen: "hub"
      };
    } catch (_) {
      // Absolute backstop: never throw, always hand back a valid beacon.
      return { label: "Run the streets", why: "Come up from Stray to King", cta: "EXPLORE", target: null, screen: "hub" };
    }
  }

  // ==========================================================================
  // 2) dailyAgenda(p?) -> ~3 objectives + reset countdown.
  // Reuses the live AKDuties (PT-day duties) when present; else a stable default
  // set (run 2 raids / hold the Watch / advance your story). Each item is
  // { label, done, goal, cta }.
  // ==========================================================================
  var CTA_BY_KIND = { tower: "BATTLE", raid: "RAID", watch: "WATCH" };
  function dailyAgenda(p) {
    try {
      p = readProfile(p);
      var D = duties();
      if (D && typeof D.today === "function") {
        var raw = [];
        try { raw = D.today() || []; } catch (_) { raw = []; }
        if (Array.isArray(raw) && raw.length) {
          var list = raw.map(function (d) {
            d = d || {};
            var target = num(d.target, 1), prog = Math.min(target, num(d.prog, 0));
            return {
              label: String(d.action || d.title || "Daily duty"),
              done: !!d.done,
              goal: prog + "/" + target + (d.title ? " -- " + d.title : ""),
              cta: CTA_BY_KIND[d.kind] || "GO"
            };
          });
          var resetsInMs;
          try { if (typeof D.getResetMs === "function") resetsInMs = num(D.getResetMs(), undefined); } catch (_) {}
          var out = { list: list };
          if (typeof resetsInMs === "number") out.resetsInMs = resetsInMs;
          return out;
        }
      }
      // Default stable set (no AKDuties on this page).
      var st = storyStage();
      var storyGoal = (st && st.title) ? String(st.title) : "Advance the Crown Bloodline";
      return {
        list: [
          { label: "Run 2 raids", done: false, goal: "0/2", cta: "RAID" },
          { label: "Hold the Watch", done: false, goal: "0/1", cta: "WATCH" },
          { label: "Advance your story", done: false, goal: storyGoal, cta: "STORY" }
        ],
        resetsInMs: msToNextPtMidnight()
      };
    } catch (_) {
      return { list: [
        { label: "Run 2 raids", done: false, goal: "0/2", cta: "RAID" },
        { label: "Hold the Watch", done: false, goal: "0/1", cta: "WATCH" },
        { label: "Advance your story", done: false, goal: "Advance the Crown Bloodline", cta: "STORY" }
      ] };
    }
  }
  // Best-effort daily reset countdown when AKDuties is absent -- next LOCAL PT
  // midnight (mirrors the missions.js PT_OFFSET so the two never disagree).
  function msToNextPtMidnight() {
    try {
      var DAY_MS = 86400000, PT_OFFSET_MS = 8 * 3600 * 1000, t = now();
      var day = Math.floor((t - PT_OFFSET_MS) / DAY_MS);
      return Math.max(0, (day + 1) * DAY_MS + PT_OFFSET_MS - t);
    } catch (_) { return 0; }
  }

  // ==========================================================================
  // 3) chainHint() -> one-line "where you are in the loop" nudge. Best-effort,
  // always a coherent single line, never throws.
  // ==========================================================================
  function chainHint() {
    try {
      var p = readProfile(null);
      var div = division(p);
      var thLv = thLevel(p);
      return "Loop: raid -> loot -> upgrade your deck -> raise the Town Hall -> climb the ladder -> unlock the next Crown Bloodline chapter. You're " + div + ", Town Hall Lv " + thLv + ".";
    } catch (_) {
      return "Loop: raid -> loot -> upgrade -> climb -> unlock the next chapter.";
    }
  }

  // ---- export -------------------------------------------------------------
  global.AK_FLYWHEEL = {
    nextAction: nextAction,     // (p?) -> { label, why, cta, target, screen }
    dailyAgenda: dailyAgenda,   // (p?) -> { list:[{label,done,goal,cta}], resetsInMs? }
    chainHint: chainHint,       // () -> string
    // exposed for hosts/tests that want the raw lookups (all pure)
    PRODUCER_IDS: PRODUCER_IDS,
    BUILDING_IDS: BUILDING_IDS,
    bldName: bldName
  };
})(typeof window !== "undefined" ? window : globalThis);
