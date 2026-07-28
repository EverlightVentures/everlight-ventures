/* ==========================================================================
   ALLEY KINGZ // SHARED ECONOMY -- chests, scrap, keys (AK-SCRAP / AK-KEYS)
   Single source of truth for the earn-path economy shared by the game
   (index.html grantMatchRewards / world map) and the Chop Shop (shop/shop.js).
   Include order: after canon.js, BEFORE shop.js (and before the index.html
   inline script if the game consumes it):
     <script src="economy.js"></script>
   Headless-safe: zero top-level DOM/localStorage access; every storage touch
   is wrapped in try/catch. With no localStorage every mutate is a no-op on a
   fresh in-memory profile, so the node harness never throws.
   GEMS ARE SERVER-ONLY: this module never reads, grants or spends gems.
   Spec: ecosystem/PROGRESSION_DESIGN.md + GAME_SHOP_MIRROR.md + the
   bj-finish build contract (chest tiers / scrap dupes / keys).
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- guarded storage (mirrors index.html lsGet/lsSet) -------------------
  function lsGet(k) { try { return (typeof localStorage !== "undefined" && localStorage) ? localStorage.getItem(k) : null; } catch (_) { return null; } }
  function lsSet(k, v) { try { if (typeof localStorage !== "undefined" && localStorage) localStorage.setItem(k, v); } catch (_) {} }

  var RARITIES = ["Common", "Rare", "Epic", "Legendary", "Mythic"];
  var CHEST_TIERS = ["wood", "bronze", "silver", "gold", "diamond"];

  // Dupe card -> scrap conversion (replaces the old flat +5c dupe rule)
  var SCRAP_DUPE = { Common: 5, Rare: 15, Epic: 40, Legendary: 100, Mythic: 250 };

  // Match-drop rarity weights -- mirrors index.html rollDrop DROP_W.
  // Legendary stays shop + draw only.
  var DROP_W = [["Common", 70], ["Rare", 22], ["Epic", 7], ["Mythic", 1]];

  // Chest contents per the build contract. floors[i] = rarity floor for card
  // slot i. Higher tiers stack the lower tiers' scrap lines.
  var CHEST_TABLE = {
    wood:    { cards: 1, coins: [15, 30],   scrap: { Common: [3, 6] },                                 floors: [],               mythicChance: 0,    keys: 0 },
    bronze:  { cards: 2, coins: [50, 90],   scrap: { Common: [6, 12] },                                floors: [],               mythicChance: 0,    keys: 0 },
    silver:  { cards: 3, coins: [110, 170], scrap: { Common: [6, 12], Rare: [4, 4] },                  floors: ["Rare"],         mythicChance: 0,    keys: 0 },
    gold:    { cards: 4, coins: [200, 300], scrap: { Common: [6, 12], Rare: [4, 4], Epic: [2, 2] },    floors: ["Epic"],         mythicChance: 0,    keys: 0 },
    diamond: { cards: 5, coins: [350, 500], scrap: { Common: [6, 12], Rare: [4, 4], Epic: [4, 4] },    floors: ["Epic", "Epic"], mythicChance: 0.05, keys: 1 }
  };

  // AK-LOOT: "THE SHAKEDOWN" phase-1 tables (LOOT_SYSTEM_DESIGN secs 4-7).
  // ONE source of truth -- the engine prefers this object over its local
  // mirror (the mirror exists only for the headless harness, which loads
  // canon+engine without economy.js). index/shop read the SAME numbers.
  // ROLL weights are the FULL 4-slot table; in phase 1 the engine rerolls
  // fragment->spark and tag->shard, so phase 2 is a flag flip, not a retune.
  var LOOT_TABLE = {
    DROP_BASE: 0.20, DROP_PER_COST: 0.04, DROP_MAX: 0.60,   // P(drop) = clamp(0.20 + 0.04*cost, .20, .60)
    SPARK_COINS: 2,                                          // 1 Coin Spark = 2 coins
    ROLL: [["spark", 68], ["shard", 25], ["fragment", 5], ["tag", 2]],
    SHARD_VALUE: { Common: 1, Rare: 1, Epic: 1, Legendary: 2, Mythic: 5 },  // shards per kill, victim's rarity
    TOWER_DROP: { sparks: 3, commonShards: 1, fragChance: 0.10 },           // enemy princess down (deterministic)
    GATE_PINATA: { sparks: 5, fragChance: 0.25, floors: ["Common", "Common", "Rare", "Epic"] },  // district gate clear
    MAGNET_UNIT: 2.0, MAGNET_TOWER: 1.5, PULL_SPEED: 8.0, LIFETIME: 12.0,   // auto-magnet (one-thumb law)
    SWEEP_COMMON: 0.5, LOSS_KEEP_COMMON: 0.5,                // sweep/loss keep rates; Epic+ shards always 100%
    CAP_COINS: 40, CAP_SHARDS: 10,                           // per-match anti-farm budgets (Dust Puffs after cap)
    CAP_SHARDS_BY_R: { Epic: 3, Legendary: 2, Mythic: 1 },
    QUICK_PLAY_MULT: 0.75,                                   // Quick Play budgets at 75%
    // AK-LOOT2 (phase-2 rare layer): Key Fragments forge keys (10 -> 1), Card
    // Tags grant a copy of the killed card. Both are jackpot class -- they
    // sweep + survive a loss at 100%, never reduced. Tags are WORLD-MAP only.
    FRAG_PER_KEY: 10, CAP_FRAGMENTS: 3, CAP_TAGS: 2,
    TAG_PIN_BONUS: 2                                          // pinned-card tag chance multiplier (phase-3 Shakedown List hook)
  };

  function num(v, d) { return (typeof v === "number" && isFinite(v)) ? v : d; }
  function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function randInt(lo, hi, rng) { return lo + Math.floor((rng || Math.random)() * (hi - lo + 1)); }

  // ---- profile shape (Section-1 schema; backfills, never rewrites) --------
  function ensureShape(p) {
    if (!p || typeof p !== "object") p = { level: 1, xp: 0, coins: 0, trophies: 0, owned: [] };
    if (typeof p.coins !== "number" || !isFinite(p.coins)) p.coins = 0;
    if (!Array.isArray(p.owned)) p.owned = [];
    if (!p.scrap || typeof p.scrap !== "object") p.scrap = {};
    RARITIES.forEach(function (r) { if (typeof p.scrap[r] !== "number" || !isFinite(p.scrap[r])) p.scrap[r] = 0; });
    if (!p.chests || typeof p.chests !== "object") p.chests = {};
    CHEST_TIERS.forEach(function (t) { if (typeof p.chests[t] !== "number" || !isFinite(p.chests[t])) p.chests[t] = 0; });
    if (typeof p.keys !== "number" || !isFinite(p.keys)) p.keys = 0;
    if (typeof p.trophies !== "number" || !isFinite(p.trophies)) p.trophies = 0;   // AK-RANK 2026-06-22: the ONE shared rank ladder (tower battle + world-map raids both move it)
    if (typeof p.fragments !== "number" || !isFinite(p.fragments)) p.fragments = 0;   // AK-LOOT2: loose key fragments (10 forge a key)
    if (typeof p.sp !== "number" || !isFinite(p.sp)) p.sp = 0;
    if (typeof p.spEarned !== "number" || !isFinite(p.spEarned)) p.spEarned = 0;
    if (!p.skills || typeof p.skills !== "object") p.skills = {};
    // AK-VIS: universal card levels + spare copies (dupes pay copies toward upgrades)
    if (!p.cardLvls || typeof p.cardLvls !== "object") p.cardLvls = {};
    if (!p.copies || typeof p.copies !== "object") p.copies = {};
    // AK-TOWNHALL 2026-06-20: the keystone meta-gate. On first migration, grandfather TH to your HIGHEST current card level so no existing card degrades; fresh profiles start at 1. (CARD_LV_CAP=10, literal here to avoid var-init order.)
    if (typeof p.townHall !== "number" || !isFinite(p.townHall)) { var _mx = 1; for (var _k in p.cardLvls) { var _v = Math.floor(p.cardLvls[_k] || 1); if (_v > _mx) _mx = _v; } p.townHall = Math.max(1, Math.min(10, _mx)); }
    p.townHall = Math.max(1, Math.min(10, Math.floor(p.townHall)));
    // === AK_SYSTEMS consolidated falsy-default fields (8 waves; zero-state stays byte-identical) ===
    if (typeof p.bones !== "number" || !isFinite(p.bones)) p.bones = 0;                 // shared soulbound skill currency
    if (!p.prod     || typeof p.prod     !== "object") p.prod = {};                     // production:  buildingId -> {lvl,lastCollect,stored}
    if (!p.missions || typeof p.missions !== "object") p.missions = {};                 // missions:    local cache (server = ak-quests)
    if (!p.captures || typeof p.captures !== "object") p.captures = {};                 // encounters:  cardName -> capture count
    if (typeof p.encSeed !== "number" || !isFinite(p.encSeed)) p.encSeed = 0;           // encounters:  deterministic spawn cursor
    if (!p.raid     || typeof p.raid     !== "object") p.raid = { shieldUntil:0, lastRaid:0, revenge:[] };
    if (!p.season   || typeof p.season   !== "object") p.season = { id:"", marks:0, claimed:[] }; // marks = cosmetic-only
    if (!p.trades   || typeof p.trades   !== "object") p.trades = { sent:[], cooldownUntil:0 };
    if (!p.arcade   || typeof p.arcade   !== "object") p.arcade = {};                   // arcade:      gameId -> {best,plays,lastReward}
    if (!p.modes    || typeof p.modes    !== "object") p.modes = {};                    // modes:       modeId -> {wins,losses,best}
    if (!p.baseLayout || typeof p.baseLayout !== "object") p.baseLayout = {};            // worldmap S2: base rearrange -> {buildingId:{x,y}}
    if (!p.karma    || typeof p.karma    !== "object") p.karma = {};                    // karma:       zoneId -> social-karma points (0% burn, prestige resets)
    // === worldverbs + buildmode shared material currencies + placed structures (falsy-default) ===
    if (typeof p.wood  !== "number" || !isFinite(p.wood))  p.wood  = 0;                 // harvest currency (trees / fences)
    if (typeof p.stone !== "number" || !isFinite(p.stone)) p.stone = 0;                 // harvest currency (rubble / rocks)
    if (typeof p.metal !== "number" || !isFinite(p.metal)) p.metal = 0;                 // harvest currency (rare nodes / scrap cars)
    if (typeof p.produce !== "number" || !isFinite(p.produce)) p.produce = 0;            // AK-ECON 2026-06-21 (sec 2): garden produce -- the tradable peasant resource (falsy-default 0, zero-state byte-identical)
    if (!p.seeds || typeof p.seeds !== "object") p.seeds = {};                           // AK-FARM (Sunflower model): seed ITEMS by crop key {catnip:n,...} -- buy/replant; falsy-default {} (zero-state byte-identical)
    if (!p.crops || typeof p.crops !== "object") p.crops = {};                           // AK-FARM: harvested crop ITEMS by crop key {catnip:n,...} -- sell for gold / USE for produce; falsy-default {}
    if (!Array.isArray(p.builds)) p.builds = [];                                         // buildmode: placed structures [{type,x,y,hp,maxHp,zone,t}]
    if (!p.nodes || typeof p.nodes !== "object") p.nodes = {};                           // worldverbs: per-zone harvest-node depletion state {zoneId:{key:{r,d}}} (empty = all ripe)
    if (!p.tools || typeof p.tools !== "object") p.tools = {};                           // AK-TOOLS: harvest tools {type:{tier,dur,owned[]}} (empty = Bare Paws, cannot work any node)
    return p;
  }
  function loadProfile() {
    var p = null;
    try { var raw = lsGet("ak_profile"); if (raw) p = JSON.parse(raw); } catch (_) { p = null; }
    return ensureShape(p);
  }
  function saveProfile(p) { try { lsSet("ak_profile", JSON.stringify(p)); } catch (_) {} }
  // Atomic read-modify-write: ONE load, ONE save per mutation.
  function mutateProfile(fn) {
    var p = loadProfile();
    try { fn(p); } catch (_) { return null; }
    saveProfile(p);
    return p;
  }
  function scrapTotal(p) {
    var t = 0; RARITIES.forEach(function (r) { t += (p && p.scrap && p.scrap[r]) | 0; });
    return t;
  }

  // ---- meta perks (clamped reading of AK.PERKS; engine clamps its own) ----
  function metaPerks(perks) {
    var src = perks || (global.AK && global.AK.PERKS) || {};
    return {
      coinMult: clampN(num(src.coinMult, 1), 1, 1.5),
      scrapMult: clampN(num(src.scrapMult, 1), 1, 1.75),
      xpMult: clampN(num(src.xpMult, 1), 1, 1.25),
      dropLuck: clampN(num(src.dropLuck, 0), 0, 8),
      chestLuck: clampN(num(src.chestLuck, 0), 0, 0.15),
      checkpointDiscount: clampN(num(src.checkpointDiscount, 0), 0, 0.5)
    };
  }

  // ---- chest tier from a finished match ------------------------------------
  // g = engine game object at result time (g.result, g.cleanSweep, g.stars,
  // g.time = clock remaining). chestLuck = chance to bump ONE tier, never past diamond.
  function rollChestTier(g, perks, rng) {
    rng = rng || Math.random;
    g = g || {};
    var won = !!g.cleanSweep || g.result === "win";
    var stars = g.stars | 0;
    var timeLeft = num(g.time, 0);
    var idx;
    if (!won) idx = 0;                                       // loss/draw -> wood
    else if (g.cleanSweep && timeLeft >= 60) idx = 4;        // fast sweep -> diamond
    else if (g.cleanSweep) idx = 3;                          // sweep -> gold
    else if (stars >= 3) idx = 2;                            // 3+ stars -> silver
    else idx = 1;                                            // win -> bronze
    var luck = metaPerks(perks).chestLuck;
    if (idx < 4 && luck > 0 && rng() < luck) idx++;
    return CHEST_TIERS[idx];
  }

  // ---- rarity roll (mirrors index.html rollDrop, + floor + dropLuck) -------
  function rollCardRarity(floorRarity, dropLuck, rng) {
    rng = rng || Math.random;
    var w = DROP_W.map(function (x) { return [x[0], x[1]]; });
    if (dropLuck) w[1][1] += clampN(num(dropLuck, 0), 0, 8);  // luck feeds the Rare weight
    var t = 0; w.forEach(function (x) { t += x[1]; });
    var x = rng() * t, rar = "Common";
    for (var i = 0; i < w.length; i++) { x -= w[i][1]; if (x < 0) { rar = w[i][0]; break; } }
    if (floorRarity && RARITIES.indexOf(rar) < RARITIES.indexOf(floorRarity)) rar = floorRarity;
    return rar;
  }

  // ---- grant helpers --------------------------------------------------------
  function grantChest(tier, n) {
    if (CHEST_TIERS.indexOf(tier) < 0) return null;
    return mutateProfile(function (p) { p.chests[tier] = (p.chests[tier] | 0) + (n == null ? 1 : (n | 0)); });
  }
  function addKeys(n) {
    return mutateProfile(function (p) { p.keys = Math.max(0, (p.keys | 0) + (n | 0)); });
  }
  // AK-RANK 2026-06-22: the ONE shared rank ladder. +trophies on a tower/encounter WIN, -trophies on a
  // raid LOSS -- so getting raided in your sleep sinks the SAME rank your tower battles climb. Floored at 0.
  function addTrophies(n) {
    var r = { trophies: 0 };
    mutateProfile(function (p) { p.trophies = Math.max(0, (p.trophies | 0) + (n | 0)); r.trophies = p.trophies; });
    return r;
  }
  function rankDivision(t) {                                   // trophies -> named division (shared by world + tower)
    t = t | 0;
    var TIERS = [[0,'Stray'],[200,'Bronze'],[500,'Silver'],[1000,'Gold'],[1800,'Crystal'],[3000,'Master'],[5000,'King of the Block']];
    var d = TIERS[0]; for (var i = 0; i < TIERS.length; i++) if (t >= TIERS[i][0]) d = TIERS[i]; return d[1];
  }
  // AK-LOOT2: bank loose Key Fragments and AUTO-FORGE whole keys at the
  // FRAG_PER_KEY threshold (10 -> 1). The remainder stays loose toward the
  // next key. ONE atomic write; clamps so a corrupt profile saturates, never
  // prints keys. Returns { fragments, forged } for the result ledger.
  function addFragments(n) {
    var per = (LOOT_TABLE.FRAG_PER_KEY | 0) || 10;
    var out = { fragments: 0, forged: 0 };
    mutateProfile(function (p) {
      p.fragments = Math.max(0, (p.fragments | 0) + (n | 0));
      var forged = Math.floor(p.fragments / per);
      if (forged > 0) {
        p.fragments -= forged * per;
        p.keys = Math.max(0, (p.keys | 0) + forged);
      }
      out.fragments = p.fragments; out.forged = forged;
    });
    return out;
  }
  function addScrap(rarity, n) {
    if (RARITIES.indexOf(rarity) < 0) return null;
    return mutateProfile(function (p) { p.scrap[rarity] = Math.max(0, (p.scrap[rarity] | 0) + (n | 0)); });
  }

  // ==========================================================================
  // AK-MAT (2026-06-20 economy-web glue): the wood/stone/metal SINK + anti-
  // runaway lever. worldverbs FAUCETS materials and buildmode SPENDS them, but
  // once a base is built materials had NO drain -> runaway inflation (the open
  // gap in AK_ECONOMY_WEB sec 5 #1: "sell excess -> Gold"). Two closures fix it:
  //   - bankMaterial: the centralized capped GRANT (every faucet routes here).
  //     Excess past MAT_CAP auto-"sells" to Gold at MAT_SELL -- no harvest is
  //     wasted, the material count can never runaway, the overflow feeds the
  //     Gold bottleneck (the doc's ~50% materials burn, realized as conversion).
  //   - convertMaterial: the explicit player "SELL EXCESS" verb (Chop Shop /
  //     Trading Post leg). Material -> Gold, atomic, gated by what you hold.
  // MAT_SELL is proportional to wall value/rarity (wood cheapest, metal rarest),
  // tuned BELOW match/producer income so selling never beats playing:
  //   wood 2g (wall=10 wood -> 20g) · stone 3g · metal 5g.
  // ==========================================================================
  var MATERIALS = ["wood", "stone", "metal"];
  var MAT_CAP = 2000;                                // per-material ceiling (~200 wood walls of headroom)
  var MAT_SELL = { wood: 2, stone: 3, metal: 5 };    // material -> gold sell/overflow rate
  function isMaterial(kind) { return MATERIALS.indexOf(kind) >= 0; }
  // GRANT n of a material, capped at MAT_CAP; the over-cap remainder auto-sells
  // to Gold at MAT_SELL. ONE atomic write. Returns {kind,added,overflow,gold}.
  function bankMaterial(kind, n) {
    if (!isMaterial(kind)) return null;
    n = Math.max(0, n | 0);
    var out = { kind: kind, added: 0, overflow: 0, gold: 0 };
    mutateProfile(function (p) {
      var cur = Math.max(0, p[kind] | 0), room = Math.max(0, MAT_CAP - cur);
      var add = Math.min(n, room), over = n - add;
      p[kind] = cur + add; out.added = add; out.overflow = over;
      if (over > 0) { var g = Math.round(over * (MAT_SELL[kind] || 1)); p.coins = Math.max(0, (p.coins | 0) + g); out.gold = g; }
    });
    return out;
  }
  // SELL n of a material for Gold (explicit player verb). Atomic; refuses if you
  // don't hold n. Returns {ok,kind,sold,gold} or {ok:false,error,...}.
  function convertMaterial(kind, n) {
    // AK-ECON 2026-06-21 (sec 7.4): produce sells to gold at the anchor (1.0).
    // Routed through the atomic trade() web; material path below stays identical.
    if (kind === "produce") { var t = trade("produce", "gold", n | 0); return t.ok ? { ok: true, kind: "produce", sold: t.spent, gold: t.got } : t; }
    if (!isMaterial(kind)) return { ok: false, error: "BAD_KIND" };
    n = n | 0; if (n <= 0) return { ok: false, error: "BAD_AMOUNT" };
    var r = { ok: false, error: "INSUFFICIENT" };
    mutateProfile(function (p) {
      var have = Math.max(0, p[kind] | 0);
      if (have < n) { r = { ok: false, error: "INSUFFICIENT", have: have, need: n }; return; }
      var g = Math.round(n * (MAT_SELL[kind] || 1));
      p[kind] = have - n; p.coins = Math.max(0, (p.coins | 0) + g);
      r = { ok: true, kind: kind, sold: n, gold: g };
    });
    return r;
  }

  // AK-SHOPFIX: server-grant -> local-copy bridge. Banks a real COPY (ownership
  // + copies++) in the same pocket the Garage upgrade math reads, so a card
  // granted by a draw / chest / gem-buy / confirm never shows 0 copies (the
  // Balboa case). n defaults to 1. ONE atomic profile write.
  function addCopy(name, n) {
    if (!name) return null;
    n = (n == null) ? 1 : (n | 0);
    if (n < 1) n = 1;
    return mutateProfile(function (p) {
      if (p.owned.indexOf(name) < 0) p.owned.push(name);
      p.copies[name] = (p.copies[name] | 0) + n;
    });
  }
  // AK-SHOPFIX: heal pass. Any owned card name with NO copies entry gets
  // copies=1 so legacy / granted-without-copies cards surface in upgrade math.
  // A legitimate 0 (every copy spent on a level) is left untouched -- only an
  // ABSENT entry is healed. Mutates the passed profile in place; returns changed.
  function healCopies(p) {
    if (!p || !Array.isArray(p.owned)) return false;
    if (!p.copies || typeof p.copies !== "object") p.copies = {};
    var changed = false;
    for (var i = 0; i < p.owned.length; i++) {
      var n = p.owned[i];
      if (n && p.copies[n] == null) { p.copies[n] = 1; changed = true; }
    }
    return changed;
  }

  // ---- deterministic Card Shop: buy the exact card with matching scrap -----
  // card = { name, rarity, scrap } (scrap = price in matching-rarity tokens).
  // AK-SHOPFIX: validates + deducts + grants (owned + a banked copy) through
  // ONE atomic mutateProfile -- a throw mid-write never persists a half state.
  function buyCardWithScrap(card) {
    if (!card || !card.name || RARITIES.indexOf(card.rarity) < 0) return { ok: false, error: "BAD_REQ" };
    var price = Math.max(0, card.scrap | 0);
    var result = { ok: false, error: "BAD_REQ" };
    var saved = mutateProfile(function (p) {
      // AK-STACK 2026-06-13: buying a card you ALREADY own is allowed -- it stacks
      // a copy toward the next Garage upgrade (operator: "no extra requirements,
      // click it and it buys + adds to collection"). The old ALREADY_OWNED refusal
      // (mislabeled "sign in to stack") blocked exactly that. Only gate = enough Scrap.
      if ((p.scrap[card.rarity] | 0) < price) {
        result = { ok: false, error: "INSUFFICIENT_SCRAP", have: p.scrap[card.rarity] | 0, need: price };
        return;
      }
      p.scrap[card.rarity] = (p.scrap[card.rarity] | 0) - price;
      if (p.owned.indexOf(card.name) < 0) p.owned.push(card.name);
      p.copies[card.name] = (p.copies[card.name] | 0) + 1;   // scrap-bought card banks/stacks a copy
      result = { ok: true, name: card.name, rarity: card.rarity, spent: price };
    });
    if (saved && result.ok) result.profile = saved;
    return result;
  }

  // ---- dupe -> scrap (for drops, draws, chest cards) ------------------------
  // Pure helper: returns the scrap value of a dupe of this rarity (perks applied).
  function dupeScrapValue(rarity, perks) {
    return Math.round((SCRAP_DUPE[rarity] || SCRAP_DUPE.Common) * metaPerks(perks).scrapMult);
  }

  // ==========================================================================
  // AK-GARAGE -- unified collection/garage upgrade economics. ONE source of
  // truth for card levels: the Deck Lab collection (index.html AK-VIS) and the
  // Chop Shop Garage tab both ride ak_profile.cardLvls + .copies + .coins with
  // THIS table, so the two surfaces can never disagree. Tables mirror the
  // index.html AK-VIS constants verbatim (Common 4/20c ... Mythic 1/1000c at
  // L1, scaled by current level, cap 10).
  // ==========================================================================
  var UP_COPIES = { Common: 4, Rare: 2, Epic: 1, Legendary: 1, Mythic: 1 };
  var UP_COINS = { Common: 20, Rare: 50, Epic: 400, Legendary: 600, Mythic: 1000 };
  var CARD_LV_CAP = 10;
  function cardLevel(p, name) {
    try {
      var v = p && p.cardLvls && p.cardLvls[name];
      var th = (p && typeof p.townHall === "number") ? p.townHall : CARD_LV_CAP; // AK-TOWNHALL: Main Tower caps every card
      return Math.max(1, Math.min(CARD_LV_CAP, th, Math.floor(v || 1)));
    } catch (_) { return 1; }
  }
  function cardCopies(p, name) {
    try { return Math.max(0, Math.floor((p && p.copies && p.copies[name]) || 0)); } catch (_) { return 0; }
  }
  // AK-TOWNHALL 2026-06-20: the keystone meta-gate. TH level (1..10) caps every card's level (CoC model). Upgrading TH is the master progression beat.
  function townHallLevel(p) { p = p || loadProfile(); return Math.max(1, Math.min(CARD_LV_CAP, (p.townHall | 0) || 1)); }
  function townHallCost(lv) { return 500 * lv * lv; } // ramping coin cost to raise TH (L1->2 = 500, L9->10 = 40500)
  // AK-THUX 2026-06-20 (#7): the caps each Town Hall level unlocks -- ONE source of truth so the
  // index.html panel can SHOW the player exactly what an upgrade buys (and future builder/crew/grid
  // systems read the SAME table). cardCap is ALREADY enforced (cardLevel() clamps to townHall).
  // AK-BLDWIRE 2026-07-18: crewSize was a dead invented curve (10 + lv*2 => 12 .. 30) that
  // contradicted the Kennel panel's "4 .. 8 crew slots" -- two promises, zero payouts. It now
  // reads crewSlotsAtTH (the Kennel ceiling this Hall permits) and dripSlots joins it for the
  // Wardrobe, so the Hall row and the building row can never disagree again. `grid` is a
  // DIFFERENT axis (the buildmode.js plot size) and stays TH-only; it is still ungated.
  function townHallPerks(lv) {
    lv = Math.max(1, Math.min(CARD_LV_CAP, (lv | 0) || 1));
    return {
      cardCap:  lv,                                   // every card can reach this level
      crewSize: crewSlotsAtTH(lv),                    // AK-BLDWIRE: == crewSlots() at the Kennel level this TH allows (5 .. 8)
      dripSlots: dripSlotsAtTH(lv),                   // AK-BLDWIRE: == dripSlots() at the Wardrobe level this TH allows (3 .. 6)
      builders: builderCap(lv),                       // AK-ECON 2026-06-21: sec 5.1 cap table (1 1 2 2 3 3 4 4 5 6) -- ONE source of truth; TH10 adds the "Top Dog" 6th slot
      grid:     (8 + lv) + 'x' + (8 + lv),            // base build grid: 9x9 .. 18x18
      maxToolTier: (function(){ var mt = 0; for (var i = 0; i < TOOL_TIERS.length; i++) { if (lv >= (TOOL_TIERS[i].unlockTH | 0)) mt = TOOL_TIERS[i].tier; } return mt; })()  // AK-THUX 2026-06-22: highest tool tier this TH unlocks (T1@1, T2@3, T3@5, T4@7) -- so the panel SHOWS the TH<->tools link the player was missing
    };
  }
  // Verified 2026-06-20 (#7): upgradeTownHall DOES deduct -- p.coins -= cost inside one atomic
  // mutateProfile (load->fn->save). The operator's "didn't deduct" was a feedback gap (no visible
  // change); index.html now flashes the gold chip -N via akHud.tick() the instant this returns ok.
  function upgradeTownHall() {
    var r = { ok: false };
    mutateProfile(function (p) {
      var lv = Math.max(1, Math.min(CARD_LV_CAP, (p.townHall | 0) || 1));
      if (lv >= CARD_LV_CAP) { r = { ok: false, error: "MAX", level: lv }; return; }
      var cost = townHallCost(lv);
      if ((p.coins | 0) < cost) { r = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: cost, level: lv }; return; }
      p.coins = (p.coins | 0) - cost; p.townHall = lv + 1;
      r = { ok: true, level: lv + 1, spent: cost };
    });
    return r;
  }
  // Next-level requirement for a card. p optional (defaults to a fresh load).
  // spare = copies BEYOND the next-level requirement (the dupe-surplus chip).
  function upgradeNeed(name, rarity, p) {
    p = p || loadProfile();
    var lv = cardLevel(p, name);
    var copies = (UP_COPIES[rarity] || 4) * lv;
    var coins = (UP_COINS[rarity] || 20) * lv;
    var have = cardCopies(p, name);
    return {
      lv: lv, atMax: lv >= CARD_LV_CAP, copies: copies, coins: coins,
      have: have, spare: Math.max(0, have - copies)
    };
  }
  // Spend copies + coins for one level. Same math as index.html upgradeCard()
  // (AK-VIS), local-first. AK-SHOPFIX: validate + spend through ONE atomic
  // mutateProfile -- a thrown error mid-write never persists a partial spend,
  // and the Garage UI never freezes on a half-applied level-up.
  function levelUpCard(card) {
    if (!card || !card.name || RARITIES.indexOf(card.rarity) < 0) return { ok: false, error: "BAD_REQ" };
    var result = { ok: false, error: "CARD_NOT_OWNED" };
    var saved = mutateProfile(function (p) {
      if (p.owned.indexOf(card.name) < 0) { result = { ok: false, error: "CARD_NOT_OWNED" }; return; }
      var nd = upgradeNeed(card.name, card.rarity, p);
      if (nd.atMax) { result = { ok: false, error: "MAX_LEVEL" }; return; }
      if (nd.have < nd.copies) { result = { ok: false, error: "INSUFFICIENT_COPIES", have: nd.have, need: nd.copies }; return; }
      if ((p.coins | 0) < nd.coins) { result = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: nd.coins }; return; }
      p.copies[card.name] = nd.have - nd.copies;
      p.coins = (p.coins | 0) - nd.coins;
      p.cardLvls[card.name] = nd.lv + 1;
      result = { ok: true, name: card.name, level: nd.lv + 1, spentCopies: nd.copies, spentCoins: nd.coins };
    });
    if (saved && result.ok) result.profile = saved;
    return result;
  }

  // ---- chest OPEN (local, earned chests + keys; gem chests stay server-side)
  // opts = { pool: [{id,name,rarity}], useKey: false, perks, rng }
  // useKey = spend 1 key to open a chest of an OWNED tier for free (the chest
  // itself is not consumed). Normal open consumes the chest. ONE profile write.
  function openChest(tier, opts) {
    opts = opts || {};
    var spec = CHEST_TABLE[tier];
    if (!spec) return { ok: false, error: "BAD_TIER" };
    var rng = opts.rng || Math.random;
    var perks = metaPerks(opts.perks);
    var pool = (Array.isArray(opts.pool) ? opts.pool : []).filter(function (c) { return c && c.name && c.rarity; });
    var p = loadProfile();
    if ((p.chests[tier] | 0) < 1) return { ok: false, error: "NO_CHEST_OWNED" };
    if (opts.useKey) {
      if ((p.keys | 0) < 1) return { ok: false, error: "NO_KEYS" };
      p.keys -= 1;                       // key open: chest count stays
    } else {
      p.chests[tier] -= 1;
    }
    // coins + scrap lines
    var coins = Math.round(randInt(spec.coins[0], spec.coins[1], rng) * perks.coinMult);
    var scrap = {};
    for (var r in spec.scrap) {
      var lo = spec.scrap[r][0], hi = spec.scrap[r][1];
      var n = Math.round(randInt(lo, hi, rng) * perks.scrapMult);
      if (n > 0) scrap[r] = (scrap[r] || 0) + n;
    }
    // card rolls (floors per slot; diamond gets a 5% forced-Mythic slot)
    var byR = {};
    pool.forEach(function (c) { (byR[c.rarity] || (byR[c.rarity] = [])).push(c); });
    var mythicSlot = (spec.mythicChance > 0 && rng() < spec.mythicChance) ? 0 : -1;
    var cards = [];
    for (var i = 0; i < spec.cards; i++) {
      var rar = (i === mythicSlot) ? "Mythic" : rollCardRarity(spec.floors[i] || null, perks.dropLuck, rng);
      var cp = byR[rar] || byR.Common || pool;
      if (!cp || !cp.length) continue;
      var card = cp[Math.floor(rng() * cp.length)];
      if (p.owned.indexOf(card.name) >= 0) {
        var s = dupeScrapValue(card.rarity, opts.perks);
        scrap[card.rarity] = (scrap[card.rarity] || 0) + s;
        p.copies[card.name] = (p.copies[card.name] | 0) + 1;   // AK-VIS: dupes also pay a copy
        cards.push({ id: card.id, name: card.name, rarity: card.rarity, dupe: true, scrap: s });
      } else {
        p.owned.push(card.name);
        p.copies[card.name] = (p.copies[card.name] | 0) + 1;   // AK-SHOPFIX: a NEW chest card banks its first copy
        cards.push({ id: card.id, name: card.name, rarity: card.rarity, dupe: false, scrap: 0 });
      }
    }
    var keys = spec.keys | 0;            // diamond pays a key back
    p.coins = (p.coins || 0) + coins;
    for (var r2 in scrap) p.scrap[r2] = (p.scrap[r2] | 0) + scrap[r2];
    if (keys) p.keys = (p.keys | 0) + keys;
    saveProfile(p);
    return { ok: true, tier: tier, cards: cards, coins: coins, scrap: scrap, keys: keys, usedKey: !!opts.useKey, profile: p };
  }

  // ==========================================================================
  // AK-ECON RATIO BACKBONE + PRODUCE + TRADING (AK_RESOURCE_ECONOMY_DESIGN
  // secs 2, 3.1, 5, 7). ONE anchor -> every conversion derived; nothing random.
  // The pure rate/cost lookups (toolCost / builderCap / builderPerks / tradeRate /
  // gemSkipCost / sellMaterial) are the CONTRACT the worldverbs / buildmode / crew /
  // UI agents call. The trade verbs (trade / tradeProduce) apply atomically via
  // mutateProfile. Headless-safe; no DOM; gems untouched (crypto gate, sec 9).
  // ==========================================================================

  // --- sec 7 ANCHOR: 1 base labor-minute of T1 active gathering ~= 12 gold. ---
  // Supply-gated by node respawn (the real regulator). Every rate below is
  // expressed relative to this anchor / to MAT_SELL, so retuning one number keeps
  // the web balanced -- no scattered magic constants.
  var ANCHOR_GOLD_PER_LABOR_MIN = 12;
  var PRODUCE_GOLD = 1.0;   // sec 7.1: produce base sell = 1.0 gold (crop tables apply the real premium)

  // --- sec 3 TOOLS: universal 5-tier ladder, applied per tool TYPE -----------
  // Cost/stats are per-tier (identical across axe/pickaxe/crowbar/drill); the
  // TYPE only selects the art skin + faction affinity. `scrap` = rarity-scrap
  // cost, `mats` = material cost, `produce` = the no-fight produce price
  // (null = no produce path, e.g. T4 is craft-only).
  var TOOL_TYPES = ["axe", "pickaxe", "crowbar", "drill"];
  var TOOL_TIERS = [
    { tier: 0, name: "Bare Paws", gold: null, produce: null, scrap: null,           mats: null,          durability: Infinity, gatherSpeed: 1.00, timeMult: 1.00, bonusLoot: 0.00, rareDrop: 0.00, unlockTH: 1 },
    { tier: 1, name: "Rusty",     gold: 60,   produce: 25,   scrap: null,           mats: null,          durability: 25,       gatherSpeed: 1.00, timeMult: 1.00, bonusLoot: 0.00, rareDrop: 0.00, unlockTH: 1 },
    { tier: 2, name: "Street",    gold: 220,  produce: 90,   scrap: { Common: 30 }, mats: null,          durability: 60,       gatherSpeed: 1.35, timeMult: 0.74, bonusLoot: 0.15, rareDrop: 0.05, unlockTH: 3 },
    { tier: 3, name: "Power",     gold: 600,  produce: 240,  scrap: { Rare: 40 },   mats: null,          durability: 120,      gatherSpeed: 1.80, timeMult: 0.56, bonusLoot: 0.30, rareDrop: 0.10, unlockTH: 5 },
    { tier: 4, name: "Chrome",    gold: 1500, produce: null, scrap: null,           mats: { metal: 60 }, durability: 240,      gatherSpeed: 2.50, timeMult: 0.40, bonusLoot: 0.50, rareDrop: 0.18, unlockTH: 7 }
  ];
  function tierIndex(tier) {
    if (typeof tier === "number") return clampN(Math.floor(tier), 0, 4);
    if (typeof tier === "string") { var m = /^[tT]?(\d)$/.exec(tier.trim()); if (m) return clampN(+m[1], 0, 4); }
    return 0;
  }
  // toolCost(type, tier) -> the full tier spec (cost + stats) + the resolved type.
  function toolCost(type, tier) {
    var src = TOOL_TIERS[tierIndex(tier)], out = {};
    for (var k in src) out[k] = src[k];
    out.type = (TOOL_TYPES.indexOf(type) >= 0) ? type : null;
    return out;
  }

  // --- sec 3 TOOL STATE (AK-TOOLS; worldverbs is the consumer) ---------------
  // The TABLES above are the law; these helpers PERSIST the player's owned tiers
  // + durability in p.tools (falsy-default {}). Absent entry => T0 Bare Paws
  // (tier 0, cannot work ANY node -- worldverbs.harvest gates on tier). All
  // writes atomic via mutateProfile. CRYPTO GATE: gems are never touched here
  // (buyTool/repairTool refuse payWith:"gems"; the server settles gem repairs).
  function isToolType(t) { return TOOL_TYPES.indexOf(t) >= 0; }
  // The equipped tool for a type -> {type,tier,dur,owned[],timeMult,bonusLoot,rareDrop,def}.
  function toolFor(p, type) {
    p = p || loadProfile();
    var t = (isToolType(type) && p.tools && p.tools[type]) ? p.tools[type] : null;
    var tier = t ? clampN(t.tier | 0, 0, 4) : 0;
    var def = TOOL_TIERS[tier];
    return {
      type: type, tier: tier,
      dur: t ? (t.dur === Infinity ? Infinity : (t.dur | 0)) : Infinity,
      owned: (t && Array.isArray(t.owned) && t.owned.length) ? t.owned.slice() : (tier ? [tier] : []),
      timeMult: def.timeMult, bonusLoot: def.bonusLoot, rareDrop: def.rareDrop, def: def
    };
  }
  // BUY a tier. payWith = "gold" (default; + the tier's extra scrap/metal) |
  // "produce" (the no-fight farmer path). TH-gated, atomic. Refills durability +
  // equips + records as owned. Returns {ok,type,tier,paid} | {ok:false,error,...}.
  function buyTool(type, tier, payWith) {
    tier = tierIndex(tier); payWith = payWith || "gold";
    if (!isToolType(type)) return { ok: false, error: "BAD_TYPE" };
    if (tier < 1 || tier > 4) return { ok: false, error: "BAD_TIER" };
    if (payWith === "gems") return { ok: false, error: "GEMS_SERVER_ONLY" };   // crypto gate: no client gem spend
    var def = TOOL_TIERS[tier];
    var r = { ok: false, error: "FAIL" };
    mutateProfile(function (p) {
      var th = townHallLevel(p);
      if (th < (def.unlockTH | 0)) { r = { ok: false, error: "TH_LOCKED", need: def.unlockTH, have: th }; return; }   // gems can NEVER bypass the TH gate
      if (!p.tools || typeof p.tools !== "object") p.tools = {};
      if (payWith === "produce") {
        if (def.produce == null) { r = { ok: false, error: "NO_PRODUCE_PATH" }; return; }
        if ((p.produce | 0) < def.produce) { r = { ok: false, error: "INSUFFICIENT_PRODUCE", have: p.produce | 0, need: def.produce }; return; }
        p.produce = (p.produce | 0) - def.produce;
        r = { ok: true, type: type, tier: tier, paid: { produce: def.produce } };
      } else {
        if (def.gold == null || (p.coins | 0) < def.gold) { r = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: def.gold | 0 }; return; }
        if (def.mats && def.mats.metal != null && (p.metal | 0) < def.mats.metal) { r = { ok: false, error: "INSUFFICIENT_METAL", have: p.metal | 0, need: def.mats.metal }; return; }
        if (def.scrap) { for (var rr in def.scrap) { if (((p.scrap && p.scrap[rr]) | 0) < def.scrap[rr]) { r = { ok: false, error: "INSUFFICIENT_SCRAP", rarity: rr, have: (p.scrap && p.scrap[rr]) | 0, need: def.scrap[rr] }; return; } } }
        var paid = { gold: def.gold }; p.coins = (p.coins | 0) - def.gold;
        if (def.mats && def.mats.metal != null) { p.metal = (p.metal | 0) - def.mats.metal; paid.metal = def.mats.metal; }
        if (def.scrap) { if (!p.scrap || typeof p.scrap !== "object") p.scrap = {}; for (var r2 in def.scrap) { p.scrap[r2] = (p.scrap[r2] | 0) - def.scrap[r2]; } paid.scrap = def.scrap; }
        r = { ok: true, type: type, tier: tier, paid: paid };
      }
      var cur = p.tools[type] || { owned: [] };
      var owned = Array.isArray(cur.owned) ? cur.owned.slice() : [];
      if (owned.indexOf(tier) < 0) owned.push(tier);
      owned.sort(function (a, b) { return a - b; });
      p.tools[type] = { tier: tier, dur: def.durability, owned: owned };   // refill + equip the bought tier
    });
    return r;
  }
  // EQUIP an already-owned tier (swap your active tool; resets dur to its max).
  function equipTool(type, tier) {
    tier = tierIndex(tier);
    if (!isToolType(type)) return { ok: false, error: "BAD_TYPE" };
    var r = { ok: false, error: "NOT_OWNED" };
    mutateProfile(function (p) {
      var t = p.tools && p.tools[type]; if (!t) { r = { ok: false, error: "NO_TOOL" }; return; }
      var owned = (Array.isArray(t.owned) && t.owned.length) ? t.owned : [t.tier];
      if (owned.indexOf(tier) < 0) { r = { ok: false, error: "NOT_OWNED" }; return; }
      t.tier = tier; t.dur = TOOL_TIERS[tier].durability;
      r = { ok: true, type: type, tier: tier, dur: t.dur };
    });
    return r;
  }
  // SPEND n durability uses on the equipped tier. At <=0 the tier BREAKS down to
  // the next-lower OWNED tier (refilled); the lowest owned tier refills in place
  // (never "unusable" -- you always keep your basic tool). Atomic.
  function spendDurability(type, n) {
    n = Math.max(0, n | 0);
    if (!isToolType(type)) return { ok: false, error: "BAD_TYPE" };
    var r = { ok: true, type: type, tier: 0, dur: Infinity, broke: false };
    mutateProfile(function (p) {
      var t = p.tools && p.tools[type]; if (!t) { r = { ok: true, type: type, tier: 0, dur: Infinity, broke: false }; return; }
      var def = TOOL_TIERS[clampN(t.tier | 0, 0, 4)];
      if (def.durability === Infinity || n === 0) { r = { ok: true, type: type, tier: t.tier, dur: t.dur, broke: false }; return; }
      t.dur = (t.dur | 0) - n;
      var broke = false;
      while (t.dur <= 0) {
        var owned = (Array.isArray(t.owned) && t.owned.length) ? t.owned.slice().sort(function (a, b) { return a - b; }) : [t.tier];
        var idx = owned.indexOf(t.tier);
        if (idx > 0) { t.tier = owned[idx - 1]; t.dur = TOOL_TIERS[t.tier].durability; broke = true; }
        else { t.dur = TOOL_TIERS[t.tier].durability; broke = true; break; }   // lowest owned tier: refill in place
      }
      r = { ok: true, type: type, tier: t.tier, dur: t.dur, broke: broke };
    });
    return r;
  }
  // REPAIR the equipped tier to full. payWith = "gold" (default) | "produce" (~half
  // the tier price). "gems" is server-only -> refused here. Parity-safe: only the
  // durability bar refills; never a tier, stat, cap or yield.
  function repairTool(type, payWith) {
    payWith = payWith || "gold";
    if (!isToolType(type)) return { ok: false, error: "BAD_TYPE" };
    if (payWith === "gems") return { ok: false, error: "GEMS_SERVER_ONLY", server: true };
    var r = { ok: false, error: "FAIL" };
    mutateProfile(function (p) {
      var t = p.tools && p.tools[type]; if (!t) { r = { ok: false, error: "NO_TOOL" }; return; }
      var def = TOOL_TIERS[clampN(t.tier | 0, 0, 4)];
      if (def.durability === Infinity) { r = { ok: true, type: type, tier: t.tier, dur: t.dur, paid: {} }; return; }
      if (payWith === "produce") {
        var pc = Math.ceil((def.produce == null ? def.gold : def.produce) * 0.5);
        if ((p.produce | 0) < pc) { r = { ok: false, error: "INSUFFICIENT_PRODUCE", have: p.produce | 0, need: pc }; return; }
        p.produce = (p.produce | 0) - pc; t.dur = def.durability; r = { ok: true, type: type, tier: t.tier, dur: t.dur, paid: { produce: pc } };
      } else {
        var gc = Math.ceil((def.gold || 0) * 0.5);
        if ((p.coins | 0) < gc) { r = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: gc }; return; }
        p.coins = (p.coins | 0) - gc; t.dur = def.durability; r = { ok: true, type: type, tier: t.tier, dur: t.dur, paid: { gold: gc } };
      }
    });
    return r;
  }

  // --- sec 7.3 GEM-SKIP: CoC diminishing-returns shape, AK-scaled (seconds) --
  // Buckets are the doc table verbatim; > 24 h continues the over-day slope
  // (24 + 76*((min-240)/1200)), continuous at the 24 h boundary (= 100).
  // Gems skip TIMERS ONLY; never a cap, a level, or loot quality (sec 9 HARD LAW).
  var GEM_SKIP = [
    [120,   0],    // <= 2 min  : free auto-finish
    [600,   2],    // <= 10 min
    [1800,  5],    // <= 30 min
    [3600,  9],    // <= 1 h
    [14400, 24],   // <= 4 h
    [43200, 60],   // <= 12 h
    [86400, 100]   // <= 24 h
  ];
  function gemSkipCost(seconds) {
    seconds = Math.max(0, Math.floor(num(seconds, 0)));
    for (var gi = 0; gi < GEM_SKIP.length; gi++) { if (seconds <= GEM_SKIP[gi][0]) return GEM_SKIP[gi][1]; }
    return Math.round(24 + 76 * ((seconds / 60 - 240) / 1200));   // > 24 h
  }

  // --- sec 5 BUILDERS = DOGS: caps, skill<->time speed, per-builder perks ----
  // sec 5.1 cap table -- TH 1..10 -> 1 1 2 2 3 3 4 4 5 6 (TH10 adds the "Top Dog"
  // foreman, our CoC B.O.B 6th slot). Closed form = ceil(TH/2) (+1 at TH10).
  function builderCap(th) {
    th = clampN(Math.floor(num(th, 1)), 1, CARD_LV_CAP);
    var c = Math.ceil(th / 2);
    if (th >= 10) c += 1;
    return clampN(c, 1, 6);
  }
  // AK-BONUSBLD 2026-06-30: the RUNTIME work-gate cap now = TH design cap + bought
  // builder slots (effectiveBuilderCap). townHallPerks.builders stays the TH-only
  // DESIGN ceiling (unchanged); THIS is the live cap the Foreman/upgrade gate honors,
  // so every existing caller of builderCapNow simply sees the extra hired slots.
  function builderCapNow(p) { return effectiveBuilderCap(p); }
  // AK-BUILDERCAP 2026-06-25: the ONE shared "builders in use" count -- the single
  // pool both surfaces draw from so they can never over-cap. Counts BOTH the
  // worldverbs harvest dispatch dogs (p.fieldJobs) AND the building upgrades in
  // flight (p.prod entries with upUntil>now). worldverbs.freeBuilders + index.html
  // activeUpgrades both read THIS, fixing the bug where each surface only saw its
  // own jobs and could blow past builderCap. PURE read -- pass a profile to stay
  // 60fps (no localStorage hit); falls back to a fresh load. fieldJobs is NOT
  // backfilled in ensureShape (worldverbs creates it lazily), so an absent entry
  // reads as 0 and zero-state stays byte-identical.
  function buildersBusy(p) {
    p = p || loadProfile();
    var now = Date.now(), n = 0;
    if (Array.isArray(p.fieldJobs)) n += p.fieldJobs.length;                                                   // worldverbs: dispatched harvest dogs
    if (p.prod && typeof p.prod === "object") { for (var k in p.prod) { var e = p.prod[k]; if (e && e.upUntil > now) n++; } }   // index.html: building upgrades in flight
    return n;
  }
  // sec 5.2 / 7.5: the ONE skill<->time multiplier (gather channel, build,
  // upgrade, bulk-gather, crop tend, train all divide by this).
  function builderSpeed(cardLvl, th) {
    cardLvl = clampN(Math.floor(num(cardLvl, 1)), 1, CARD_LV_CAP);
    th = clampN(Math.floor(num(th, 1)), 1, CARD_LV_CAP);
    return (1 + 0.08 * (cardLvl - 1)) * (1 + 0.05 * (th - 1));
  }
  // sec 5.4 store gating: best SKU a builder unlocks (TH gate AND builder level).
  function storeTier(th, builderLvl) {
    th = clampN(Math.floor(num(th, 1)), 1, CARD_LV_CAP);
    var bl = clampN(Math.floor(num(builderLvl, 1)), 1, CARD_LV_CAP);
    if (th >= 7 && bl >= 7) return 4;   // T4 needs TH7 + Lv7 builder
    if (th >= 5 && bl >= 5) return 3;   // T3 needs TH5 + Lv5 builder
    if (th >= 3) return 2;              // T1-T2 stocked at TH3
    return 1;
  }
  // sec 5.4 loot: rarity sets a bonus-loot FLOOR (derived; capped, never stacks
  // past T4's +50%); cardLvl>=7 unlocks the "high-gear" one-tier-better rare roll.
  var RARITY_LOOT_FLOOR = { Common: 0.00, Rare: 0.05, Epic: 0.10, Legendary: 0.15, Mythic: 0.20 };
  function cardRarityOf(name) {
    try {
      var list = (global.AK && typeof global.AK.getCards === "function" && global.AK.getCards())
              || global.CANON_CARDS || (global.AK && global.AK.CANON_CARDS) || null;
      if (list && list.length) for (var ci = 0; ci < list.length; ci++) { var c = list[ci]; if (c && (c.name === name || c.id === name)) return c.rarity; }
    } catch (_) {}
    return null;
  }
  // builderPerks(card, thLevel) -> { speed, lootFloor, lootBonus, highGear,
  // storeTier, cardLvl, th }. `card` may be a cardLvl number, a card NAME
  // (level resolved from profile, rarity from canon), or {name,lvl|level,rarity}.
  function builderPerks(card, th) {
    var lvl = 1, rarity = "Common", name = null;
    if (typeof card === "number") { lvl = card; }
    else if (typeof card === "string") { name = card; try { lvl = cardLevel(loadProfile(), card); } catch (_) {} rarity = cardRarityOf(card) || rarity; }
    else if (card && typeof card === "object") {
      name = card.name || null;
      lvl = Math.floor(num(card.lvl != null ? card.lvl : card.level, 1));
      rarity = card.rarity || (name ? (cardRarityOf(name) || rarity) : rarity);
    }
    lvl = clampN(lvl, 1, CARD_LV_CAP);
    if (RARITIES.indexOf(rarity) < 0) rarity = "Common";
    th = clampN(Math.floor(num(th, 1)), 1, CARD_LV_CAP);
    return {
      name: name, cardLvl: lvl, th: th,
      speed: builderSpeed(lvl, th),
      lootFloor: rarity,
      lootBonus: num(RARITY_LOOT_FLOOR[rarity], 0),
      highGear: lvl >= 7,
      storeTier: storeTier(th, lvl)
    };
  }
  // doc 10.1: what a TH level unlocks, for the #thpanel to SHOW (alias over
  // townHallPerks with the design's `cardLvlCap` naming + the sec 5.1 builders).
  function townHallUnlocks(lv) {
    var pk = townHallPerks(lv);
    return { cardLvlCap: pk.cardCap, builders: pk.builders, crewSize: pk.crewSize, dripSlots: pk.dripSlots, grid: pk.grid };
  }

  // ==========================================================================
  // AK-BONUSBLD 2026-06-30 -- "A WAY TO GET MORE BUILDERS" (the active gold lever)
  // The operator asked for it. p.bonusBuilders is a falsy-safe field: a fresh
  // profile NEVER carries it (zero-state byte-identical law), it is only WRITTEN
  // by buyBuilderSlot on a successful gold purchase, and every read is (p.x|0).
  // GEMS CAN NEVER BUY BUILDERS (parity law sec 9: gems are cosmetic/convenience,
  // never a cap or a level). buyBuilderSlot is GOLD-ONLY by construction.
  // ==========================================================================
  // The live cap = the TH design cap (sec 5.1 table) + permanently-hired bonus
  // slots. This is what builderCapNow delegates to, so the Foreman/upgrade gate
  // and worldverbs harvest-dispatch both honor hired builders.
  function effectiveBuilderCap(p) { p = p || loadProfile(); return builderCap(townHallLevel(p)) + (p.bonusBuilders | 0); }
  // HARD CAP: total effective builders may never exceed 8 (the design ceiling --
  // TH10 gives 6, two more can be hired). Escalating GOLD cost = 2000 * N^1.6
  // where N = the CURRENT effective cap, so the 2nd builder costs ~2000 and each
  // further hire climbs steeply (3rd ~6063, 4th ~11598, ...). TH2+ gate.
  function buyBuilderSlot() {
    var r = { ok: false };
    mutateProfile(function (p) {
      var th = townHallLevel(p);
      if (th < 2) { r = { ok: false, error: "TH_LOCKED", need: 2 }; return; }
      var totalNow = builderCap(th) + (p.bonusBuilders | 0);              // current effective cap
      if (totalNow >= 8) { r = { ok: false, error: "MAX", builders: totalNow }; return; }
      var cost = Math.round(2000 * Math.pow(totalNow, 1.6));
      if ((p.coins | 0) < cost) { r = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: cost }; return; }
      p.coins = (p.coins | 0) - cost;                                     // GOLD only -- gems untouched (crypto/parity gate)
      p.bonusBuilders = (p.bonusBuilders | 0) + 1;                        // first write of the field; fresh profiles stay clean
      r = { ok: true, cost: cost, builders: builderCap(th) + (p.bonusBuilders | 0) };
    });
    return r;
  }
  // Pure quote so the UI can render the button label + state without buying.
  function builderSlotQuote(p) {
    p = p || loadProfile();
    var th = townHallLevel(p);
    var totalNow = builderCap(th) + (p.bonusBuilders | 0);
    return {
      cost: Math.round(2000 * Math.pow(totalNow, 1.6)),
      locked: th < 2,
      maxed: totalNow >= 8,
      builders: totalNow
    };
  }

  // ==========================================================================
  // AK-BLDBENEFIT 2026-06-30 -- "UPGRADES MUST SHOW THEIR BENEFIT"
  // The operator: upgrades had no visible purpose. buildingBenefit(id, lv) returns
  // a deterministic { metric, curLabel, nextLabel, deltaLabel, blurb } so the
  // index.html upgrade panel can SHOW exactly what level lv+1 buys. Soft-currency
  // only (gold/produce/scrap/keys/fragments/caps/loot/XP/rep) -- never gems, never
  // power-for-pay. The 5 PRODUCERS (GEM/MINT/FORGE/LAB/GEN) mirror the REAL income
  // engine (production.js) so SHOWN == PAID; GARAGE/FIXER mirror their REAL applied
  // multipliers (garageLootMult/fixerPayMult). pct metrics scale per*lv %; slot
  // metrics step +1 every `step` levels; ARENA reads townHallPerks (the meta gate).
  // ==========================================================================
  // AK-PRODSYNC 2026-06-30: production.js is the ENGINE for the 5 producers and it
  // already pays per level -- KEEP THESE RATES IN SYNC with production.js (PRODUCERS
  // table + RATE_GROWTH=0.5, CAP_HOURS=8). baseRate(lvl) = rate*(1+0.5*(lvl-1));
  // cap = round(baseRate(lvl)*8). If production.js rates change, change them here too.
  var PROD_RATE_GROWTH = 0.5;   // mirror production.js RATE_GROWTH
  var PROD_CAP_HOURS   = 8;     // mirror production.js CAP_HOURS
  var PRODUCERS = {
    GEM:   { rate: 5,   res: "Rare scrap" },   // 5 Rare scrap/hr
    MINT:  { rate: 90,  res: "gold" },         // 90 gold/hr
    FORGE: { rate: 4,   res: "fragments" },    // 4 key-fragments/hr (10 frags auto-forge 1 key)
    LAB:   { rate: 2,   res: "Epic scrap" },   // 2 Epic scrap/hr
    GEN:   { rate: 0.5, res: "keys" }          // 0.5 keys/hr (+ row boost in the engine)
  };
  function prodBaseRate(rate, lvl) { lvl = Math.max(1, Math.floor(num(lvl, 1))); return rate * (1 + PROD_RATE_GROWTH * (lvl - 1)); }
  // AK-LVBASE 2026-06-30: mirror of index.html const LV (the default building levels
  // the hub shows) so an applied effect lands on the SAME level the panel displays.
  var LV_BASE = { ARENA: 8, TROPHY: 4, FIXER: 3, GARAGE: 6, DROP: 5, KENNEL: 4, CLAN: 5, PASS: 2, WARD: 3, ARCH: 2, STREET: 3, ARCADE: 1, GEM: 5, MINT: 4, FORGE: 3, LAB: 3, GEN: 4 };
  function bldLvl(p, id) { return (p && p.prod && p.prod[id] && p.prod[id].lvl) || LV_BASE[id] || 1; }
  // REAL applied multipliers (index.html raid loot + missions.js payouts call these).
  // +8% per building level, clamped [1, 2.5]. The benefit panel shows the SAME basis
  // (computed from the passed lv) so SHOWN == APPLIED.
  function garageLootMult(p) { p = p || loadProfile(); return clampN(1 + 0.08 * bldLvl(p, "GARAGE"), 1, 2.5); }
  function fixerPayMult(p)   { p = p || loadProfile(); return clampN(1 + 0.08 * bldLvl(p, "FIXER"),  1, 2.5); }
  function multPctFor(lv) { return clampN(1 + 0.08 * Math.max(1, Math.floor(num(lv, 1))), 1, 2.5); }   // pure level -> mult (same formula as the helpers)
  var BUILDING_BENEFIT = {
    TROPHY: { metric: "Season rep",    kind: "pct",    per: 5,                unit: "rep",          blurb: "Extra Block Rep per win -- climb the season ladder faster." },
    DROP:   { metric: "Shop edge",     kind: "pct",    per: 2,                unit: "off",          blurb: "Sharper shop prices + more daily deal slots." },
    CLAN:   { metric: "Crew share",    kind: "pct",    per: 3,                unit: "loot share",   blurb: "Crew-wide loot share + a longer crew-chat history." },
    PASS:   { metric: "Pass XP",       kind: "pct",    per: 8,                unit: "pass XP",      blurb: "Faster Alley Pass progress -- season tiers unlock sooner." },
    ARCH:   { metric: "Codex reward",  kind: "pct",    per: 4,                unit: "codex reward", blurb: "Bigger Codex completion rewards + deeper lore unlocks." },
    STREET: { metric: "Street loot",   kind: "pct",    per: 6,                unit: "street loot",  blurb: "Richer street-mode payouts." },
    ARCADE: { metric: "Arcade reward", kind: "pct",    per: 5,                unit: "arcade reward",blurb: "Better mini-game rewards + a higher token cap." },
    KENNEL: { metric: "Crew slots",    kind: "slot",   base: 4,    step: 2,   unit: " crew slots",  blurb: "Room for more handlers -- one extra crew slot every 2 levels." },
    WARD:   { metric: "Drip slots",    kind: "slot",   base: 2,    step: 2,   unit: " drip slots",  blurb: "More cosmetic loadout slots -- stunt on the block (pure cosmetic, no power)." }
  };
  function fmtNum(n) { return String(Math.round(num(n, 0))).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  // ARENA (Town Hall) is the meta gate -- surface the REAL townHallPerks numbers.
  function townHallBenefit(lv) {
    lv = clampN(Math.floor(num(lv, 1)), 1, CARD_LV_CAP);
    var cur = townHallPerks(lv);
    var curLabel = "Card Lv " + cur.cardCap + " | " + cur.builders + " builders | crew " + cur.crewSize + " | drip " + cur.dripSlots + " | grid " + cur.grid + " | tools T" + cur.maxToolTier;
    var blurb = "The keystone. Caps every card level, your builder count, crew size, build grid, and tool tier.";
    if (lv >= CARD_LV_CAP) {
      return { metric: "Town Hall (meta gate)", curLabel: curLabel, nextLabel: "MAX", deltaLabel: "MAX -- the crown is yours (Lv 10)", blurb: blurb };
    }
    var nxt = townHallPerks(lv + 1);
    var nextLabel = "Card Lv " + nxt.cardCap + " | " + nxt.builders + " builders | crew " + nxt.crewSize + " | drip " + nxt.dripSlots + " | grid " + nxt.grid + " | tools T" + nxt.maxToolTier;
    var parts = ["+1 card level"];
    if (nxt.builders > cur.builders)         parts.push("+" + (nxt.builders - cur.builders) + " builder");
    if (nxt.crewSize > cur.crewSize)         parts.push("+" + (nxt.crewSize - cur.crewSize) + " crew slot");
    if (nxt.dripSlots > cur.dripSlots)       parts.push("+" + (nxt.dripSlots - cur.dripSlots) + " drip slot");
    if (nxt.grid !== cur.grid)               parts.push("grid " + nxt.grid);
    if (nxt.maxToolTier > cur.maxToolTier)   parts.push("Tool T" + nxt.maxToolTier);
    return { metric: "Town Hall (meta gate)", curLabel: curLabel, nextLabel: nextLabel, deltaLabel: parts.join(" | "), blurb: blurb };
  }
  // The 5 producers read REAL numbers straight off the production.js engine model.
  function producerBenefit(id, lv) {
    var pr = PRODUCERS[id];
    var cur  = Math.round(prodBaseRate(pr.rate, lv));
    var next = Math.round(prodBaseRate(pr.rate, lv + 1));
    var cap  = Math.round(prodBaseRate(pr.rate, lv) * PROD_CAP_HOURS);
    return {
      metric: pr.res,
      curLabel: cur + " " + pr.res + "/hr",
      nextLabel: next + " " + pr.res + "/hr",
      deltaLabel: "+" + (next - cur) + "/hr (" + cur + " -> " + next + ")  ·  cap " + cap,
      blurb: "Walk in and COLLECT the haul -- faster rate + bigger cap each level."
    };
  }
  // GARAGE/FIXER show the SAME percent their applied multiplier delivers.
  function multBenefit(lv, metric, blurb) {
    var lower = metric.toLowerCase();
    var curPct  = Math.round((multPctFor(lv)     - 1) * 100);
    var nextPct = Math.round((multPctFor(lv + 1) - 1) * 100);
    var dPct = nextPct - curPct;
    return {
      metric: metric,
      curLabel: "+" + curPct + "% " + lower,
      nextLabel: "+" + nextPct + "% " + lower,
      deltaLabel: (dPct > 0 ? "+" + dPct + "% " + lower : "MAX (+" + curPct + "% capped)") + " (now +" + curPct + "%, next +" + nextPct + "%)",
      blurb: blurb
    };
  }
  function buildingBenefit(id, lv) {
    id = String(id || "").toUpperCase();
    lv = Math.max(1, Math.floor(num(lv, 1)));
    if (id === "ARENA") return townHallBenefit(lv);
    if (PRODUCERS[id]) return producerBenefit(id, lv);
    if (id === "GARAGE") return multBenefit(lv, "Raid loot", "Bigger haul out of every raid -- applied live to your loot, more per run each level.");
    if (id === "FIXER")  return multBenefit(lv, "Mission pay", "Fatter Hit List contracts -- applied live to mission payouts, more gold + scrap each level.");
    var s = BUILDING_BENEFIT[id];
    if (!s) return null;
    var cur, next, curLabel, nextLabel, deltaLabel;
    if (s.kind === "rate" || s.kind === "cap") {
      cur = s.base + s.per * lv; next = s.base + s.per * (lv + 1);
      curLabel = fmtNum(cur) + s.unit; nextLabel = fmtNum(next) + s.unit;
      deltaLabel = "+" + fmtNum(s.per) + s.unit + " (" + fmtNum(cur) + " -> " + fmtNum(next) + ")";
    } else if (s.kind === "pct") {
      // AK-BLDWIRE 2026-07-18: the SHOWN percent now comes from benefitPct, the SAME
      // pure function every applied multiplier below reads. One formula, no drift.
      cur = benefitPct(id, lv); next = benefitPct(id, lv + 1);
      curLabel = "+" + cur + "% " + s.unit; nextLabel = "+" + next + "% " + s.unit;
      deltaLabel = (next > cur) ? ("+" + (next - cur) + "% " + s.unit + " (" + cur + "% -> " + next + "%)")
                                : ("MAX (+" + cur + "% " + s.unit + " capped)");
    } else if (s.kind === "pctneg") {
      cur = Math.min(s.cap, s.per * lv); next = Math.min(s.cap, s.per * (lv + 1));
      curLabel = "-" + cur + "% " + s.unit; nextLabel = "-" + next + "% " + s.unit;
      var d = next - cur;
      deltaLabel = (d > 0) ? ("-" + d + "% " + s.unit + " (" + cur + "% -> " + next + "%)") : ("MAX -- " + s.unit + " floor reached (-" + cur + "%)");
    } else { // slot
      // AK-BLDWIRE 2026-07-18: SHOWN slots now come from benefitSlots, the SAME pure
      // function crewSlots()/dripSlots() apply. The panel can no longer promise a
      // number the game does not hand out.
      cur = benefitSlots(id, lv); next = benefitSlots(id, lv + 1);
      curLabel = cur + s.unit; nextLabel = next + s.unit;
      if (next > cur) { deltaLabel = "+1" + s.unit + " (" + cur + " -> " + next + ")"; }
      else { deltaLabel = "Next slot at Lv " + ((cur - s.base + 1) * s.step + 1); }
    }
    return { metric: s.metric, curLabel: curLabel, nextLabel: nextLabel, deltaLabel: deltaLabel, blurb: s.blurb };
  }

  // ==========================================================================
  // AK-BLDWIRE 2026-07-18 -- "THE NINE DEAD BUILDINGS PAY OUT NOW"
  // Operator complaint: an upgrade charged real gold + real materials and returned
  // literally nothing. BUILDING_BENEFIT had the design numbers for TROPHY / DROP /
  // CLAN / PASS / ARCH / STREET / ARCADE / KENNEL / WARD since 2026-06-30 and the
  // ONLY two consumers in the whole repo were LABELS (index.html panel row +
  // flywheel.js row). No multiplier lookup existed. GARAGE (garageLootMult) and
  // FIXER (fixerPayMult) were the only two buildings that actually did anything.
  // These accessors close the gap using the numbers ALREADY in the table -- per
  // for the pct buildings, base/step for the slot buildings. Nothing invented.
  // Pattern is a verbatim copy of garageLootMult/fixerPayMult: a pure function of
  // building level, clamped, exported on AK_ECON, headless-safe (loadProfile is
  // try/catch wrapped and an absent p.prod entry falls back to LV_BASE via bldLvl).
  // Soft-currency only. No gems, no power-for-pay (parity law sec 9).
  // buildingBenefit's pct + slot branches were rerouted through benefitPct/
  // benefitSlots above, so the panel and the payout are the SAME arithmetic.
  // ==========================================================================
  var BENEFIT_MULT_CAP = 2.5;    // the ceiling garageLootMult/fixerPayMult already use
  var SHOP_PRICE_FLOOR = 0.5;    // safety rail ONLY: a shop edge can never cut past 50% off
  // Pure level -> the percent the panel shows for this building (per * level).
  // Clamped to the building level cap so a corrupt p.prod entry cannot run away.
  function benefitPct(id, lv) {
    var s = BUILDING_BENEFIT[String(id || "").toUpperCase()];
    if (!s || s.kind !== "pct") return 0;
    return num(s.per, 0) * clampN(Math.floor(num(lv, 1)), 1, BLD_MAX_LVL);
  }
  // Pure level -> gain multiplier (1 + shown%), clamped exactly like the two live mults.
  function benefitMult(id, lv) { return clampN(1 + benefitPct(id, lv) / 100, 1, BENEFIT_MULT_CAP); }
  // Pure level -> slot count. base + one extra every `step` levels (the table's own rule).
  function benefitSlots(id, lv) {
    var s = BUILDING_BENEFIT[String(id || "").toUpperCase()];
    if (!s || s.kind !== "slot") return 0;
    var l = clampN(Math.floor(num(lv, 1)), 1, BLD_MAX_LVL);
    return s.base + Math.floor((l - 1) / Math.max(1, s.step | 0));
  }
  // The seven percent levers. Each mirrors garageLootMult's signature exactly:
  // pass a profile for a 60fps PURE read, or no arg to load one.
  function trophyRepMult(p)     { p = p || loadProfile(); return benefitMult("TROPHY", bldLvl(p, "TROPHY")); }   // Trophy Room -> season Rep gains
  function clanShareMult(p)     { p = p || loadProfile(); return benefitMult("CLAN",   bldLvl(p, "CLAN")); }     // Crew Hall   -> crew loot share
  function passXpMult(p)        { p = p || loadProfile(); return benefitMult("PASS",   bldLvl(p, "PASS")); }     // Pass Office -> Alley Pass XP
  function codexRewardMult(p)   { p = p || loadProfile(); return benefitMult("ARCH",   bldLvl(p, "ARCH")); }     // Archive     -> Codex completion rewards
  function streetPayMult(p)     { p = p || loadProfile(); return benefitMult("STREET", bldLvl(p, "STREET")); }   // Street Gym  -> street-mode payouts
  function arcadeRewardMult(p)  { p = p || loadProfile(); return benefitMult("ARCADE", bldLvl(p, "ARCADE")); }   // Arcade      -> mini-game rewards
  // DROP is the one NEGATIVE lever: the shown "+N% off" becomes a PRICE multiplier.
  function shopDiscount(p)  { p = p || loadProfile(); return clampN(benefitPct("DROP", bldLvl(p, "DROP")) / 100, 0, 1 - SHOP_PRICE_FLOOR); }
  function shopPriceMult(p) { return clampN(1 - shopDiscount(p), SHOP_PRICE_FLOOR, 1); }
  // The number a shop row should CHARGE and SHOW. Rounds to whole gold, never to 0
  // for a priced item (a free item stays free).
  function shopPrice(gold, p) {
    var g = Math.max(0, Math.round(num(gold, 0)));
    if (!g) return 0;
    return Math.max(1, Math.round(g * shopPriceMult(p)));
  }
  // The two slot levers. Same signature; integers, not multipliers.
  function crewSlots(p) { p = p || loadProfile(); return benefitSlots("KENNEL", bldLvl(p, "KENNEL")); }   // Kennel   -> handler roster slots
  function dripSlots(p) { p = p || loadProfile(); return benefitSlots("WARD",   bldLvl(p, "WARD")); }     // Wardrobe -> cosmetic loadout slots
  // AK-BLDWIRE 2026-07-18: the TWO-PROMISE BUG. townHallPerks said "crew 12 .. 30"
  // while the Kennel panel said "4 .. 8 crew slots", and NOTHING read either one, so
  // the player was quoted two different numbers for the same thing. ONE source now:
  // the Hall row shows the CEILING it permits (the Kennel/Wardrobe level this TH can
  // hold, floored at the shipped baseline exactly like buildingCapFor), and the
  // building itself hands out that same number via crewSlots()/dripSlots().
  // Pure th-level in, no profile read, so townHallPerks stays a pure function.
  function bldCapAtTH(th, id) {
    return clampN(Math.max(clampN(Math.floor(num(th, 1)), 1, BLD_MAX_LVL), buildingBaseline(id)), 1, BLD_MAX_LVL);
  }
  function crewSlotsAtTH(th) { return benefitSlots("KENNEL", bldCapAtTH(th, "KENNEL")); }
  function dripSlotsAtTH(th) { return benefitSlots("WARD",   bldCapAtTH(th, "WARD")); }

  // ==========================================================================
  // AK-THCAP 2026-07-18 -- TOWN HALL LEVEL CAP (the Clash of Clans rule).
  // Operator law: "Whatever the Town Hall number is, that's the cap." Raising the
  // Hall UPGRADES NOTHING. It only raises the ceiling every other building is
  // allowed to climb to. You still walk in and upgrade each building by hand.
  // Legal:   TH 8 + Lv 6 gem mine (you just haven't done the work yet).
  // Illegal: TH 6 + Lv 8 gem mine (the Hall was never big enough to hold it).
  // The gate lives HERE, inside the mutation, so no surface can route around it:
  // the 5 producers (GEM/MINT/FORGE/LAB/GEN) and every generic building call the
  // SAME upgradeBuilding() and eat the SAME cap. Timed builds are re-checked on
  // landing (finishBuildingUpgrades) so a Hall that got knocked down by a raid
  // mid-build never pays out a level it can no longer hold.
  // GRANDFATHER: a building's SHIPPED baseline (LV_BASE, e.g. GARAGE 6) is never
  // retroactively bricked -- the effective gate is max(TH, baseline). Nothing on
  // an existing base de-levels; it just stops climbing until the Hall catches up.
  // CURRENCY INTERLOCK (operator: "all the currencies play into each other"):
  // gold stays the base cost, but from Lv 3 up an upgrade ALSO eats MATERIALS on
  // a rising curve -- wood+stone at Lv3+, metal at Lv5+, Common scrap at Lv7+. So
  // the Hall gates the ceiling, gold gates the pace, and the harvest/raid economy
  // gates the top end. No new currencies; all four already live on the profile.
  // ==========================================================================
  var BLD_MAX_LVL   = CARD_LV_CAP;   // 10 -- mirrors production.js MAX_LVL
  var MAT_GATE_FROM = 3;             // below this level an upgrade is gold-only (early game stays frictionless)
  // The building's shipped default level (mirror of index.html LV / LV_BASE above).
  function buildingBaseline(id) { return Math.max(1, LV_BASE[String(id || "").toUpperCase()] | 0); }
  // THE canonical cap: the Town Hall level, full stop. This is the number the UI
  // shows the player ("Town Hall Lv 6 caps every building at Lv 6").
  function buildingCap(p) { return townHallLevel(p || loadProfile()); }
  // The EFFECTIVE per-building gate = the cap, floored at that building's shipped
  // baseline so a pre-existing base never goes backwards. ARENA is the Hall itself.
  function buildingCapFor(p, id) {
    id = String(id || "").toUpperCase();
    return clampN(Math.max(buildingCap(p), buildingBaseline(id)), 1, BLD_MAX_LVL);
  }
  // Gold curve, mirrored from the two live surfaces so SHOWN == CHARGED:
  // producers ride production.js upCost (costBase * 1.5^(lv-1)); the generic
  // buildings ride the index.html hub curve (80 + 70*lv).
  var PROD_COST_BASE = { GEM: 180, MINT: 200, FORGE: 220, LAB: 260, GEN: 300 };   // mirror production.js CFG.costBase
  function buildingGoldCost(id, curLvl) {
    id = String(id || "").toUpperCase();
    var lv = Math.max(1, Math.floor(num(curLvl, 1)));
    if (PROD_COST_BASE[id]) return Math.round(PROD_COST_BASE[id] * Math.pow(1.5, lv - 1));
    return 80 + 70 * lv;
  }
  // The material bill for the NEXT level. Rising curve, keyed off the level you
  // are upgrading FROM (same convention as upCost). Returns only the lines that
  // apply -- {} below MAT_GATE_FROM, so early upgrades stay pure gold.
  function buildingMatCost(id, curLvl) {
    var lv = Math.max(1, Math.floor(num(curLvl, 1)));
    var out = {};
    if (lv < MAT_GATE_FROM) return out;
    out.wood  = 30 + 25 * (lv - 2);
    out.stone = 20 + 18 * (lv - 2);
    if (lv >= 5) out.metal = 15 + 12 * (lv - 4);
    if (lv >= 7) out.scrap = { Common: 10 + 8 * (lv - 6) };
    return out;
  }
  function _matShort(p, mats) {                      // -> [] when the bill is covered
    var s = [];
    if (mats.wood  && (p.wood  | 0) < mats.wood)  s.push({ kind: "wood",  have: p.wood  | 0, need: mats.wood });
    if (mats.stone && (p.stone | 0) < mats.stone) s.push({ kind: "stone", have: p.stone | 0, need: mats.stone });
    if (mats.metal && (p.metal | 0) < mats.metal) s.push({ kind: "metal", have: p.metal | 0, need: mats.metal });
    if (mats.scrap) { for (var rr in mats.scrap) { var hv = (p.scrap && p.scrap[rr]) | 0; if (hv < mats.scrap[rr]) s.push({ kind: rr + " scrap", rarity: rr, have: hv, need: mats.scrap[rr] }); } }
    return s;
  }
  function _spendMats(p, mats) {
    if (mats.wood)  p.wood  = Math.max(0, (p.wood  | 0) - mats.wood);
    if (mats.stone) p.stone = Math.max(0, (p.stone | 0) - mats.stone);
    if (mats.metal) p.metal = Math.max(0, (p.metal | 0) - mats.metal);
    if (mats.scrap) { if (!p.scrap || typeof p.scrap !== "object") p.scrap = {}; for (var rr in mats.scrap) p.scrap[rr] = Math.max(0, (p.scrap[rr] | 0) - mats.scrap[rr]); }
  }
  // THE GUARD. (id, curLvl?, p?) -> { ok, reason, msg, lvl, next, cap, th }.
  // reason is 'TH_CAP' when the Hall is what's blocking you. curLvl null = resolve
  // from the profile. PURE -- pass a profile to stay 60fps.
  function canUpgradeBuilding(id, curLvl, p) {
    p = p || loadProfile();
    id = String(id || "").toUpperCase();
    var th = buildingCap(p), cap = buildingCapFor(p, id);
    var lv = (curLvl == null) ? Math.max(1, bldLvl(p, id) | 0) : Math.max(1, Math.floor(num(curLvl, 1)));
    var out = { ok: false, reason: "BLOCKED", msg: "", lvl: lv, next: lv + 1, cap: cap, th: th };
    if (id === "ARENA") { out.reason = "IS_TOWN_HALL"; out.msg = "The Hall raises itself. Run it through the Town Hall panel."; return out; }
    if (lv >= BLD_MAX_LVL) { out.reason = "MAX"; out.msg = "Lv " + BLD_MAX_LVL + ". Nothing left to build here."; return out; }
    if (lv >= cap) {
      out.reason = "TH_CAP";
      out.msg = "Town Hall Lv " + th + " caps this at Lv " + cap + ". Raise the Hall before you raise anything else on the block.";
      return out;
    }
    var e = p.prod && p.prod[id];
    if (e && e.upUntil > Date.now()) { out.reason = "BUSY"; out.msg = "Crew's already working this one."; return out; }
    out.ok = true; out.reason = null; out.msg = "";
    return out;
  }
  // The full quote the UI lane renders: gate + gold + the material bill + what
  // you're short. ok is true ONLY when the cap allows it AND the bill is covered.
  function buildingUpgradeQuote(id, curLvl, p) {
    p = p || loadProfile();
    id = String(id || "").toUpperCase();
    var g = canUpgradeBuilding(id, curLvl, p);
    var lv = g.lvl;
    var gold = buildingGoldCost(id, lv), mats = buildingMatCost(id, lv);
    var q = { ok: false, reason: g.reason, msg: g.msg, lvl: lv, next: g.next, cap: g.cap, th: g.th,
              gold: gold, mats: mats, haveGold: p.coins | 0, short: [] };
    if (!g.ok) return q;
    if ((p.coins | 0) < gold) q.short.push({ kind: "gold", have: p.coins | 0, need: gold });
    q.short = q.short.concat(_matShort(p, mats));
    if (q.short.length) {
      q.reason = (q.short[0].kind === "gold") ? "INSUFFICIENT_FUNDS" : "INSUFFICIENT_MATERIALS";
      q.msg = "Short " + q.short.map(function (s) { return (s.need - s.have) + " " + s.kind; }).join(" + ") + ". Go earn it.";
      return q;
    }
    q.ok = true; q.reason = null; q.msg = "";
    return q;
  }
  // THE MUTATION. Every upgrade path routes here, so the cap cannot be bypassed.
  // opts.timeMs > 0 = the TIMED build (generic hub buildings): ties up a builder,
  // stamps upUntil, and the level lands in finishBuildingUpgrades. opts.timeMs 0
  // or absent = the INSTANT bump (the producer keeper path). Gold + materials are
  // deducted and the level moves inside ONE atomic write.
  function upgradeBuilding(id, opts) {
    opts = opts || {};
    id = String(id || "").toUpperCase();
    var timeMs = Math.max(0, Math.floor(num(opts.timeMs, 0)));
    var r = { ok: false, error: "FAIL" };
    mutateProfile(function (p) {
      var q = buildingUpgradeQuote(id, opts.curLvl == null ? null : opts.curLvl, p);
      if (!q.ok) { r = { ok: false, error: q.reason || "BLOCKED", msg: q.msg, lvl: q.lvl, cap: q.cap, th: q.th, gold: q.gold, mats: q.mats, short: q.short }; return; }
      if (timeMs > 0) {
        var free = Math.max(0, effectiveBuilderCap(p) - buildersBusy(p));
        if (free <= 0) { r = { ok: false, error: "NO_BUILDERS", msg: "Every builder's already on a job." }; return; }
      }
      p.coins = Math.max(0, (p.coins | 0) - q.gold);
      _spendMats(p, q.mats);
      if (!p.prod || typeof p.prod !== "object") p.prod = {};
      var e = p.prod[id];
      if (!e || typeof e !== "object") { e = { lvl: q.lvl, lastCollect: Date.now(), stored: 0 }; p.prod[id] = e; }
      e.lvl = q.lvl;                                  // pin the resolved baseline so LV_BASE defaults persist
      if (timeMs > 0) { e.upUntil = Date.now() + timeMs; r = { ok: true, id: id, lvl: q.lvl, timed: true, doneAt: e.upUntil, cap: q.cap, th: q.th, spent: { gold: q.gold, mats: q.mats } }; }
      else { e.lvl = q.lvl + 1; e.upUntil = 0; r = { ok: true, id: id, lvl: e.lvl, timed: false, cap: q.cap, th: q.th, spent: { gold: q.gold, mats: q.mats } }; }
    });
    return r;
  }
  // PURE: how many timed builds have landed but not been applied yet (poll cheap,
  // write only when there's something to write -- no localStorage churn per tick).
  function pendingBuildingUpgrades(p, now) {
    p = p || loadProfile();
    now = num(now, Date.now());
    var n = 0;
    if (p.prod && typeof p.prod === "object") { for (var k in p.prod) { var e = p.prod[k]; if (e && e.upUntil && now >= e.upUntil) n++; } }
    return n;
  }
  // Land every finished timed build. RE-CHECKS the cap on landing: if the Hall got
  // knocked down while the crew was working, the build ends and the level does NOT
  // move (capped:true). Returns [{ id, lvl, capped }].
  function finishBuildingUpgrades(now) {
    now = num(now, Date.now());
    var done = [];
    if (pendingBuildingUpgrades(null, now) <= 0) return done;
    mutateProfile(function (p) {
      if (!p.prod || typeof p.prod !== "object") return;
      for (var k in p.prod) {
        var e = p.prod[k];
        if (!e || !e.upUntil || now < e.upUntil) continue;
        e.upUntil = 0;
        var cur = Math.max(1, e.lvl | 0), cap = buildingCapFor(p, k);
        if (cur >= cap || cur >= BLD_MAX_LVL) { done.push({ id: k, lvl: cur, capped: true }); continue; }   // Hall fell mid-build: no free level
        e.lvl = cur + 1;
        done.push({ id: k, lvl: e.lvl, capped: false });
      }
    });
    return done;
  }

  // --- sec 7.1 / 7.4 TRADE WEB: produce <-> resource <-> gold ----------------
  // produce buys material ABOVE gold-par (the farming subsidy); material sells at
  // MAT_SELL; produce sells at the anchor (1.0). gold does NOT buy raw material
  // (one-way sink, no buy-back arbitrage). Unlisted pairs return 0 (refused).
  var PRODUCE_TRADE = { wood: 0.8, stone: 0.55, metal: 0.30, gold: PRODUCE_GOLD };
  function tradeRate(from, to) {
    if (from === to) return 1;
    if (from === "produce") return num(PRODUCE_TRADE[to], 0);
    if (isMaterial(from) && to === "gold") return num(MAT_SELL[from], 0);
    return 0;
  }
  // sellMaterial(mat) -> gold-per-unit sell rate (sec 7.1). produce -> the anchor.
  function sellMaterial(mat) {
    if (mat === "produce") return PRODUCE_GOLD;
    return num(MAT_SELL[mat], 0);
  }
  function _balanceOf(p, kind) {
    if (kind === "gold") return Math.max(0, p.coins | 0);
    if (kind === "produce") return Math.max(0, p.produce | 0);
    if (isMaterial(kind)) return Math.max(0, p[kind] | 0);
    return -1;
  }
  // trade(from, to, n): atomic conversion at tradeRate. Lossy (floor) so trading
  // is convenience, not arbitrage. Trades INTO a material respect MAT_CAP
  // (overflow auto-sells to gold, mirroring bankMaterial -> no material runaway).
  // Returns { ok, from, to, spent, got, credited, overflowGold, rate } or { ok:false, error }.
  function trade(from, to, n) {
    n = n | 0;
    if (n <= 0) return { ok: false, error: "BAD_AMOUNT" };
    var rate = tradeRate(from, to);
    if (!(rate > 0)) return { ok: false, error: "BAD_PAIR", from: from, to: to };
    var got = Math.floor(n * rate);
    if (got <= 0) return { ok: false, error: "BELOW_MIN", from: from, to: to, n: n, rate: rate };
    var r = { ok: false, error: "INSUFFICIENT" };
    mutateProfile(function (p) {
      var have = _balanceOf(p, from);
      if (have < 0) { r = { ok: false, error: "BAD_PAIR" }; return; }
      if (have < n) { r = { ok: false, error: "INSUFFICIENT", have: have, need: n }; return; }
      if (from === "gold") p.coins = (p.coins | 0) - n;
      else if (from === "produce") p.produce = (p.produce | 0) - n;
      else p[from] = (p[from] | 0) - n;
      var credited = got, overflowGold = 0;
      if (to === "gold") p.coins = Math.max(0, (p.coins | 0) + got);
      else if (to === "produce") p.produce = Math.max(0, (p.produce | 0) + got);
      else {
        var cur = Math.max(0, p[to] | 0), room = Math.max(0, MAT_CAP - cur);
        var add = Math.min(got, room), over = got - add;
        p[to] = cur + add; credited = add;
        if (over > 0) { overflowGold = Math.round(over * (MAT_SELL[to] || 1)); p.coins = Math.max(0, (p.coins | 0) + overflowGold); }
      }
      r = { ok: true, from: from, to: to, spent: n, got: got, credited: credited, overflowGold: overflowGold, rate: rate };
    });
    return r;
  }
  function tradeProduce(toKind, n) { return trade("produce", toKind, n); }

  // ==========================================================================
  // AK-FARM (Sunflower Land study, 2026-06-25): SEEDS + CROPS as real soft items.
  // The flat "+gold per seed" garden is GONE. The loop now mirrors Sunflower Land:
  //   buy a SEED item -> plant -> grow-timer -> HARVEST yields the CROP item +
  //   BONUS SEEDS (reproduce, so a bed self-sustains) -> SELL crops for gold or
  //   USE them for produce (the tool/trade currency). Seeds + crops live in
  //   p.seeds{} / p.crops{} (per-crop-key item counts, falsy-default). ONE source
  //   of truth = CROPS here; buildmode.js reads AK_ECON.CROPS. Parity-safe: gold/
  //   produce/seeds/crops are 100% client soft currency, gems untouched (sec 9).
  //
  // CROPS fields: name, glyph (UI), seed (gold to buy 1 seed), grow (ms),
  //   yield (crops per harvest, pre-weather), reseed (bonus seeds per harvest --
  //   the "reproduce" lever), sell (gold per crop), th (Town Hall gate).
  // Per-cycle gold = yield*sell stays ~6-10 g/passive-min (below the active
  //   ANCHOR of 12 g/labor-min) -- longer timers bank more TOTAL (set & forget,
  //   CoC model), the grow timer + bed count + TH are the regulators.
  // ==========================================================================
  var CROPS = {
    catnip:   { name: "Catnip",          glyph: "🌿", seed: 5,   grow: 120000,   yield: 3,   reseed: 2, sell: 5,  th: 1 }, // 2m
    berry:    { name: "Block Berries",   glyph: "🫐", seed: 10,  grow: 300000,   yield: 5,   reseed: 2, sell: 7,  th: 1 }, // 5m
    corn:     { name: "Street Corn",     glyph: "🌽", seed: 20,  grow: 720000,   yield: 9,   reseed: 2, sell: 8,  th: 1 }, // 12m
    pumpkin:  { name: "Pumpkin",         glyph: "🎃", seed: 60,  grow: 1800000,  yield: 20,  reseed: 1, sell: 9,  th: 2 }, // 30m
    cabbage:  { name: "Concrete Cabbage",glyph: "🥬", seed: 100, grow: 3600000,  yield: 30,  reseed: 1, sell: 12, th: 2 }, // 1h
    beetroot: { name: "Beetroot",        glyph: "🥕", seed: 140, grow: 7200000,  yield: 46,  reseed: 1, sell: 16, th: 3 }, // 2h
    chili:    { name: "Firehouse Chili", glyph: "🌶️", seed: 220, grow: 12600000, yield: 70, reseed: 1, sell: 22, th: 4 }, // 3.5h
    kingweed: { name: "Kingweed",        glyph: "🍀", seed: 320, grow: 21600000, yield: 110, reseed: 1, sell: 30, th: 5 }, // 6h
    goldroot: { name: "Goldroot",        glyph: "🥔", seed: 700, grow: 57600000, yield: 230, reseed: 1, sell: 40, th: 7 }  // 16h
  };

  // --- WEATHER: a simple deterministic-by-day modifier (rain/sun/drought). ----
  // sun = neutral, rain = faster grow + more yield, drought = slower + less.
  // The day index (UTC midnight buckets) seeds a tiny LCG hash -> the wheel
  // (weighted toward sun) so the same day always reads the SAME weather, no RNG,
  // no per-frame work. buildmode SNAPSHOTS the weather key onto the bed at plant
  // time (b.wx) so a crop's grow/yield are fixed for its whole cycle (parity-safe,
  // never flips mid-grow). growMult scales grow time, yieldMult scales harvest.
  var CROP_WEATHER = {
    sun:     { label: "Clear Skies", glyph: "☀️",       grow: 1.00, yield: 1.00 },
    rain:    { label: "Rain",        glyph: "🌧️", grow: 0.80, yield: 1.15 },
    drought: { label: "Drought",     glyph: "🏜️", grow: 1.30, yield: 0.85 }
  };
  var WEATHER_WHEEL = ["sun", "rain", "sun", "drought", "sun", "rain"];   // ~50% sun / 33% rain / 17% drought
  function weatherDay(ms) { var t = (typeof ms === "number" && isFinite(ms)) ? ms : Date.now(); return Math.floor(t / 86400000); }
  function gardenWeather(day) {
    day = (day == null) ? weatherDay() : Math.floor(num(day, 0));
    var h = ((day * 1103515245 + 12345) >>> 0) % WEATHER_WHEEL.length;   // LCG hash -> deterministic wheel pick
    var key = WEATHER_WHEEL[h], w = CROP_WEATHER[key] || CROP_WEATHER.sun;
    return { key: key, label: w.label, glyph: w.glyph, growMult: w.grow, yieldMult: w.yield, day: day };
  }
  function weatherMods(key) { var w = CROP_WEATHER[key] || CROP_WEATHER.sun; return { growMult: w.grow, yieldMult: w.yield }; }
  // pure weather-applied grow/yield (the contract buildmode reads; single source).
  function cropGrowMs(key, weatherKey) { var c = CROPS[key]; if (!c) return 0; return Math.max(1000, Math.round((c.grow || 0) * weatherMods(weatherKey).growMult)); }
  function cropYield(key, weatherKey)  { var c = CROPS[key]; if (!c) return 0; return Math.max(1, Math.round((c.yield || 0) * weatherMods(weatherKey).yieldMult)); }

  // --- SEED + CROP item helpers (atomic, falsy-default, lazily create the maps) -
  function seedCount(p, key) { try { return Math.max(0, (p && p.seeds && p.seeds[key]) | 0); } catch (_) { return 0; } }
  function cropCount(p, key) { try { return Math.max(0, (p && p.crops && p.crops[key]) | 0); } catch (_) { return 0; } }
  function addSeed(key, n) { if (!CROPS[key]) return null; n = n | 0; return mutateProfile(function (p) { if (!p.seeds || typeof p.seeds !== "object") p.seeds = {}; p.seeds[key] = Math.max(0, (p.seeds[key] | 0) + n); }); }
  function addCrop(key, n) { if (!CROPS[key]) return null; n = n | 0; return mutateProfile(function (p) { if (!p.crops || typeof p.crops !== "object") p.crops = {}; p.crops[key] = Math.max(0, (p.crops[key] | 0) + n); }); }
  // BUY n seeds. payWith = "gold" (default, n*seed) | "produce" (n*seed at the 1.0
  // anchor). TH-gated, atomic. "gems" refused (crypto gate -- server settles gems).
  function buySeed(key, n, payWith) {
    var c = CROPS[key]; if (!c) return { ok: false, error: "BAD_CROP" };
    n = n | 0; if (n <= 0) n = 1; payWith = payWith || "gold";
    if (payWith === "gems") return { ok: false, error: "GEMS_SERVER_ONLY" };
    var r = { ok: false, error: "FAIL" };
    mutateProfile(function (p) {
      var th = townHallLevel(p);
      if (th < (c.th || 1)) { r = { ok: false, error: "TH_LOCKED", need: c.th, have: th }; return; }
      if (!p.seeds || typeof p.seeds !== "object") p.seeds = {};
      if (payWith === "produce") {
        var pc = Math.ceil((c.seed || 0) / (PRODUCE_GOLD || 1)) * n;
        if ((p.produce | 0) < pc) { r = { ok: false, error: "INSUFFICIENT_PRODUCE", have: p.produce | 0, need: pc }; return; }
        p.produce = (p.produce | 0) - pc; p.seeds[key] = (p.seeds[key] | 0) + n;
        r = { ok: true, key: key, n: n, paid: { produce: pc } };
      } else {
        var gc = (c.seed || 0) * n;
        if ((p.coins | 0) < gc) { r = { ok: false, error: "INSUFFICIENT_FUNDS", have: p.coins | 0, need: gc }; return; }
        p.coins = (p.coins | 0) - gc; p.seeds[key] = (p.seeds[key] | 0) + n;
        r = { ok: true, key: key, n: n, paid: { gold: gc } };
      }
    });
    return r;
  }
  // SELL n crops for gold at c.sell (the "sell" leg of harvest -> sell/use). Atomic.
  function sellCrop(key, n) {
    var c = CROPS[key]; if (!c) return { ok: false, error: "BAD_CROP" };
    n = n | 0; if (n <= 0) return { ok: false, error: "BAD_AMOUNT" };
    var r = { ok: false, error: "INSUFFICIENT" };
    mutateProfile(function (p) {
      var have = cropCount(p, key);
      if (have < n) { r = { ok: false, error: "INSUFFICIENT", have: have, need: n }; return; }
      var g = Math.round(n * (c.sell || 0));
      p.crops[key] = have - n; p.coins = Math.max(0, (p.coins | 0) + g);
      r = { ok: true, key: key, sold: n, gold: g };
    });
    return r;
  }
  // USE n crops -> produce (the tool/trade currency) at the crop's gold value
  // (sell/PRODUCE_GOLD), so SELL and USE are value-neutral -- gold vs produce.
  function useCrop(key, n) {
    var c = CROPS[key]; if (!c) return { ok: false, error: "BAD_CROP" };
    n = n | 0; if (n <= 0) return { ok: false, error: "BAD_AMOUNT" };
    var r = { ok: false, error: "INSUFFICIENT" };
    mutateProfile(function (p) {
      var have = cropCount(p, key);
      if (have < n) { r = { ok: false, error: "INSUFFICIENT", have: have, need: n }; return; }
      var g = Math.max(0, Math.round(n * (c.sell || 0) / (PRODUCE_GOLD || 1)));
      p.crops[key] = have - n; p.produce = (p.produce | 0) + g;
      r = { ok: true, key: key, used: n, produce: g };
    });
    return r;
  }
  // SELL n spare seeds for gold at ~50% of seed cost (the "or sell" on bonus seeds).
  function sellSeed(key, n) {
    var c = CROPS[key]; if (!c) return { ok: false, error: "BAD_CROP" };
    n = n | 0; if (n <= 0) return { ok: false, error: "BAD_AMOUNT" };
    var r = { ok: false, error: "INSUFFICIENT" };
    mutateProfile(function (p) {
      var have = seedCount(p, key);
      if (have < n) { r = { ok: false, error: "INSUFFICIENT", have: have, need: n }; return; }
      var g = Math.max(0, Math.floor(n * (c.seed || 0) * 0.5));
      p.seeds[key] = have - n; p.coins = Math.max(0, (p.coins | 0) + g);
      r = { ok: true, key: key, sold: n, gold: g };
    });
    return r;
  }

  // ==========================================================================
  // AK-STAKES (CORE LOOP CANON sec 1 + 3): the keystone STAKES SPINE. TOWN HALL
  // is the master -- it gates the DECK card-level MAX. Raid a player's district
  // and the Town Hall takes damage: TH drops -> deckMaxLevel drops -> every deck
  // card clamps DOWN (cardLevel() already reads p.townHall). The STORED card
  // levels in p.cardLvls are NOT erased -- rebuild the Town Hall on the Block and
  // the deck climbs right back to its real max. THAT is why guarding the turf
  // matters (canon: "Raids have a REAL, painful consequence"). No new profile
  // fields -- this rides p.townHall, so zero-state stays byte-identical.
  // ==========================================================================

  // deckMaxLevel(p): the HARD ceiling every deck card is clamped to, gated by the
  // Town Hall (higher TH -> higher max; equals townHallPerks(TH).cardCap). 60fps-
  // safe pure read -- pass a profile to skip the localStorage hit; falls back to a
  // fresh load. Drop the Town Hall and this drops with it (that is the stakes).
  function deckMaxLevel(p) {
    return townHallLevel(p);   // already clamped 1..CARD_LV_CAP; cardCap === TH level
  }

  // raidDamage(p, severity): the LOST-DEFENSE penalty -- you got raided in your
  // sleep, the Town Hall took the hit. Drops the Town Hall level so the deck is
  // NO LONGER max. severity = "minor"|"major"|"devastating"|"wipe" (1/2/3 TH
  // levels) OR a raw number of levels. TH floors at 1 -- you never lose the master
  // building itself. Stored card levels (p.cardLvls) are untouched, so rebuilding
  // TH restores the deck. If `p` is a real profile it is mutated IN PLACE and
  // {persisted:false} is returned -- persist it yourself (call inside
  // AK_ECON.mutateProfile, the doctrine path; mirrors healCopies). If `p` is
  // omitted, this runs its own atomic load->drop->save and returns {persisted:true}.
  var RAID_SEVERITY = { minor: 1, major: 2, devastating: 3, wipe: 3 };
  function raidDrop(severity) {
    if (typeof severity === "number" && isFinite(severity)) return Math.max(0, Math.floor(severity));
    var key = (typeof severity === "string") ? severity.toLowerCase().trim() : "";
    return (RAID_SEVERITY[key] != null) ? RAID_SEVERITY[key] : 1;   // default = minor (1 level)
  }
  function applyRaid(p, drop) {
    var from = Math.max(1, Math.min(CARD_LV_CAP, (p.townHall | 0) || 1));
    var to = Math.max(1, from - drop);   // clamp floor: TH never below 1
    p.townHall = to;
    return { ok: true, dropped: from - to, fromLevel: from, toLevel: to, deckMaxBefore: from, deckMaxAfter: to };
  }
  function raidDamage(p, severity) {
    var drop = raidDrop(severity), out;
    if (p && typeof p === "object") {
      out = applyRaid(p, drop); out.persisted = false;   // in place -- caller saves (via mutateProfile)
    } else {
      mutateProfile(function (pp) { out = applyRaid(pp, drop); });
      if (!out) out = { ok: false, error: "FAIL" };
      out.persisted = true;
    }
    out.severity = severity;
    return out;
  }

  // ==========================================================================
  // AK-LOOTMATH 2026-07-18: RAIDING IS AN ECONOMY, NOT A SLOT MACHINE.
  //
  // Loot is NOT one flat percentage of one number. It is FOUR POOLS, each with
  // its own rate, its own cap and its own unlock condition:
  //
  //   STORAGE    a falling share of the defender's liquid bank (gold/produce/mats)
  //   COLLECTOR  a much higher share (50%) of UNCOLLECTED producer yield
  //   TREASURY   a small slice (5%) of the scrap bag
  //   TOWN HALL  a flat vault, paid ONLY if the Town Hall actually dies
  //
  // THE INVERSE RELATIONSHIP (the whole point). The storage RATE falls as the
  // defender's Town Hall rises (50% at TH1 down to 10% at TH18) while the
  // absolute CAP rises (250 gold at TH1 up to 25000 at TH18). A new player can
  // never be stripped of a meaningful fraction of their bank, and a maxed player
  // is farmed for VOLUME rather than for percentage. Those two curves moving in
  // OPPOSITE directions is what makes the ladder survivable at the bottom and
  // still worth climbing at the top.
  //
  // THE COLLECTOR IS THE LESSON. Collectors leak at 50% because uncollected
  // yield is the one pool the defender chose to leave lying in the street.
  // Collect often and a raid barely scratches you. Log off full and you fund
  // the raider. That is a decision the player controls, which is exactly what
  // separates an economy from a slot machine.
  //
  // THE PENALTY. Attacking DOWN the ladder is taxed hard by Town Hall
  // difference, so a strong player cannot farm weak ones profitably. Same TH is
  // full value; attacking UP is never penalised.
  //
  // ---- RECONCILIATION WITH systems/raidparams.js (READ THIS BEFORE RETUNING) -
  // raidparams.js defines maxLootPercent per TH RISING 0.30 (TH1) -> 0.75 (TH10)
  // and lootCeiling() = storage * maxLootPercent * (1 + lootBonus). Its own header
  // calls that "the hard cap on how much of their storage you can ever extract",
  // so it is THE SAME QUANTITY as lootStorageRate() below and the two disagree in
  // DIRECTION. They cannot both stand. THIS FILE WINS. Why:
  //   1. NOTHING CALLS IT. raidparams.lootCeiling and raidparams.maxLootPercent
  //      have zero call sites repo-wide (verified 2026-07-18) -- they are
  //      unreferenced, so nothing regresses by making economy.js authoritative.
  //   2. A RISING storage percentage is backwards. It means a TH10 player who
  //      logs off loses 75% of their bank while a TH1 loses 30%, which punishes
  //      investment and inverts the protection the design wants.
  //   3. Gold lives here. economy.js owns the profile, the currencies and every
  //      grant path, so the number that actually MOVES currency has to live in
  //      the same file as the currency.
  // What raidparams KEEPS: lootBonus (the defender's rarity bonus, 0.00 Common ->
  // 0.50 Mythic) is a real lever with no collision, and lootPoolsFor() DOES apply
  // it -- see lootRarityBonus(). The fix on the raidparams side is a one-liner for
  // whoever owns that file: point lootCeiling at AK_ECON.lootPoolsFor(p).total and
  // drop the maxLoot column, or leave both as dead data. Do NOT multiply the two
  // rates together: that yields ~15% at TH1 and ~13% at TH10, a flat curve that
  // delivers neither the newbie protection nor the volume-at-the-top design.
  //
  // Every function here is PURE and headless-safe: no DOM, no writes, no RNG, no
  // localStorage, and it never mutates the profile it is handed. Award = transfer,
  // never minting -- every unit paid out traces to something the defender actually
  // holds, which is why the same math can run server-side unchanged.
  // ==========================================================================
  var LOOT_TH_MAX = 18;                 // the curve is defined to TH18 even though CARD_LV_CAP is 10 today

  // Storage rate FALLS with the defender's Town Hall (the protection curve).
  var LOOT_STORAGE_RATE = {
    1: 0.500, 2: 0.460, 3: 0.420, 4: 0.380, 5: 0.340, 6: 0.300,
    7: 0.270, 8: 0.240, 9: 0.210, 10: 0.180, 11: 0.165, 12: 0.150,
    13: 0.140, 14: 0.130, 15: 0.120, 16: 0.115, 17: 0.107, 18: 0.100
  };
  // Absolute cap RISES with the defender's Town Hall (the volume curve). Scaled to
  // THIS game's gold, not Clash's: townHallCost(9) = 40500 to reach TH10, and the
  // TH10 cap of 6500 means a maxed base funds roughly a sixth of that per clean raid.
  var LOOT_CAP = {
    1: 250, 2: 400, 3: 650, 4: 950, 5: 1400, 6: 2000,
    7: 2800, 8: 3800, 9: 5000, 10: 6500, 11: 8200, 12: 10000,
    13: 12000, 14: 14200, 15: 16600, 16: 19200, 17: 22000, 18: 25000
  };
  var LOOT_COLLECTOR_RATE     = 0.50;   // uncollected producer yield leaks HARD (the collect-often lesson)
  var LOOT_TREASURY_RATE      = 0.05;   // the scrap bag gives up only a token slice
  var LOOT_COLLECTOR_CAP_FRAC = 0.60;   // collector pool cap, as a fraction of LOOT_CAP
  var LOOT_TREASURY_CAP_FRAC  = 0.15;   // treasury pool cap, as a fraction of LOOT_CAP
  var LOOT_TH_VAULT_FRAC      = 0.20;   // Town Hall vault, flat fraction of LOOT_CAP, unlocked by killing the Hall
  // Penalty by (attackerTH - defenderTH). Index 0 = same TH. Attacking UP is index 0 too.
  var LOOT_PENALTY_LADDER     = [1.00, 0.80, 0.50, 0.25, 0.05];
  var LOOT_PENALTY_FLOOR      = 0.05;   // 4+ Town Halls down is a rounding error, never zero

  // Mirror of production.js accrual (that module bails without AK_SYSTEMS, so it can
  // not be imported headlessly; same mirror pattern as LOOT_TABLE above). Only the
  // three RAIDABLE producers are listed: FORGE (key fragments) and GEN (keys) are
  // deliberately EXCLUDED so the crate/key economy is never a PvP target.
  var LOOT_PROD = {
    GEM:  { rate: 5,  kind: "scrap", rarity: "Rare" },
    MINT: { rate: 90, kind: "gold",  rarity: null   },
    LAB:  { rate: 2,  kind: "scrap", rarity: "Epic" }
  };
  var LOOT_PROD_CAP_HOURS = 8;          // mirrors production.js CAP_HOURS
  var LOOT_PROD_GROWTH    = 0.5;        // mirrors production.js RATE_GROWTH
  var LOOT_GEN_BOOST      = 0.03;       // mirrors production.js GEN_BOOST_PER_LVL
  var LOOT_GEN_BOOST_MAX  = 0.30;       // mirrors production.js GEN_BOOST_MAX
  var LOOT_HR_MS          = 3600000;

  // A base with NO wealth data at all (the procedurally generated raid target: today
  // index.html builds _defProfile as { townHall, owned:[], cardLvls:{}, defense:{} }
  // because nothing in the repo publishes a real defender snapshot yet). Without this
  // such a target would pay ONLY the Town Hall vault and the whole pool model would be
  // dead weight against the most common opponent in the game. So a wealth-less base is
  // PRESUMED to be a full base for its Town Hall: each pool sits exactly at its own cap.
  // Deterministic, no RNG, and it self-disables the moment ANY real wealth field is
  // present, so a real player snapshot always uses real numbers.
  var LOOT_PRESUMED_BANK  = { gold: 0.55, produce: 0.10, wood: 0.20, stone: 0.10, metal: 0.05 };
  var LOOT_PRESUMED_COLL  = { gold: 0.60, Rare: 0.25, Epic: 0.15 };
  var LOOT_PRESUMED_SCRAP = { Common: 0.50, Rare: 0.35, Epic: 0.15 };

  // ---- systems/storages.js interop (AK-STORE, the SAME p.builds[] shared state) ----
  // storages.js derives WHICH BUCKET every resource sits in (collector / storage /
  // Town Hall) from the real structures in p.builds[]. That is genuinely its lane:
  // it reads the build placements, so a storage placed inside the nested build world
  // is visible to the loot math the moment you walk out, with no second copy of the
  // numbers. THIS file stays the authority on the RATES applied to those buckets.
  // Division of labour, stated once so it cannot drift:
  //     storages.js  ->  WHERE the resources are            (bucket partition)
  //     economy.js   ->  WHAT FRACTION a raider gets        (rates, caps, penalty)
  // Rate reconciliation: storages.js LOOT_RATE.collector is 0.50, which AGREES with
  // LOOT_COLLECTOR_RATE here. Its LOOT_RATE.storage is a FLAT 0.20; this file's
  // lootStorageRate() is the TH-indexed curve (0.50 @TH1 -> 0.10 @TH18) that the flat
  // 0.20 approximates (0.20 lands near the TH9 value). The CURVE wins, because a flat
  // rate cannot deliver the newbie protection the design is built on. Scrap is routed
  // to the TREASURY pool here and deliberately NOT counted in the storage pool, so the
  // two modules can never double-count the same scrap.
  // Absent / older / throwing AK_STORAGE degrades to this file's own derivation, which
  // is fully proven on its own, so this is an upgrade path and never a hard dependency.
  function lootMapBucket(bucket) {
    var out = { gold: 0, produce: 0, wood: 0, stone: 0, metal: 0, scrap: {} };
    if (!bucket || typeof bucket !== "object") return out;
    for (var k in bucket) {
      if (!bucket.hasOwnProperty(k)) continue;
      var n = Math.max(0, bucket[k] | 0);
      if (n <= 0) continue;
      if (k.indexOf("scrap:") === 0) { var r = k.slice(6); out.scrap[r] = (out.scrap[r] | 0) + n; }
      else if (k === "coins") out.gold += n;
      else if (k === "produce" || k === "wood" || k === "stone" || k === "metal") out[k] += n;
      // keys / fragments / bones are intentionally dropped: never lootable here.
    }
    return out;
  }
  function lootSourcesFrom(def, now) {
    try {
      var S = global.AK_STORAGE;
      if (!S || typeof S.lootableFrom !== "function") return null;
      // Ask for the FULL picture (townHallDestroyed:true) so the Hall bucket is filled;
      // this file gates whether that pool is actually PAID, in resolveLoot.
      var lf = S.lootableFrom(def, now, { townHallDestroyed: true });
      if (!lf || !lf.buckets) return null;
      var src = { bank: lootMapBucket(lf.buckets.storage),
                  coll: lootMapBucket(lf.buckets.collector),
                  hall: lootMapBucket(lf.buckets.townHall) };
      var any = 0, kk;
      for (kk in src) if (src.hasOwnProperty(kk)) {
        any += src[kk].gold + src[kk].produce + src[kk].wood + src[kk].stone + src[kk].metal
             + lootScrapValue(src[kk].scrap);
      }
      return any > 0 ? src : null;
    } catch (_) { return null; }
  }

  function lootTH(th) { return clampN(Math.floor(num(th, 1)) || 1, 1, LOOT_TH_MAX); }
  function lootStorageRate(th) { return num(LOOT_STORAGE_RATE[lootTH(th)], 0.10); }
  function lootCap(th) { return num(LOOT_CAP[lootTH(th)], 250); }

  // Gold-equivalent of a rarity-keyed scrap bag, valued off SCRAP_DUPE (the canon
  // scrap ladder in this file: Common 5 .. Mythic 250). No new value table invented.
  function lootScrapValue(bag) {
    var t = 0;
    for (var i = 0; i < RARITIES.length; i++) {
      var r = RARITIES[i];
      t += Math.max(0, (bag && bag[r]) | 0) * num(SCRAP_DUPE[r], 0);
    }
    return t;
  }

  // The defender's rarity loot bonus, read LIVE from raidparams (the one lever this
  // file keeps from that module). No raidparams / no canon list = 0, so the headless
  // harness and a bare page both stay deterministic.
  function lootRarityBonus(def) {
    try {
      var RP = global.AK_RAIDPARAMS;
      if (!RP || typeof RP.watcherRarity !== "function" || !RP.RARITY_MOD) return 0;
      var list = (global.AK && typeof global.AK.getCards === "function" && global.AK.getCards())
              || global.CANON_CARDS || (global.AK && global.AK.CANON_CARDS) || null;
      if (!list || !list.length) return 0;
      var byName = {};
      for (var i = 0; i < list.length; i++) if (list[i] && list[i].name) byName[list[i].name] = list[i];
      var mod = RP.RARITY_MOD[RP.watcherRarity(def, byName)];
      return mod ? num(mod.lootBonus, 0) : 0;
    } catch (_) { return 0; }
  }

  // UNCOLLECTED producer yield, deterministic from (lvl, lastCollect, now) exactly the
  // way production.js pendingUnits does it. e.stored is honoured if some future keeper
  // ever banks into it (today production.js always leaves it 0), clamped to the cap so
  // a corrupt entry can never print loot. PURE.
  function lootCollectorPending(p, now) {
    var out = { gold: 0, scrap: {}, value: 0 };
    var prod = (p && p.prod && typeof p.prod === "object") ? p.prod : null;
    if (!prod) return out;
    now = num(now, Date.now());
    var genLvl = (prod.GEN && (prod.GEN.lvl | 0)) || 0;
    var boost = 1 + Math.min(LOOT_GEN_BOOST_MAX, LOOT_GEN_BOOST * genLvl);
    for (var bid in LOOT_PROD) {
      if (!LOOT_PROD.hasOwnProperty(bid)) continue;
      var e = prod[bid];
      if (!e || typeof e !== "object") continue;
      var cfg = LOOT_PROD[bid];
      var lvl = Math.max(1, e.lvl | 0);
      var base = cfg.rate * (1 + LOOT_PROD_GROWTH * (lvl - 1));
      var cap = Math.max(1, Math.round(base * LOOT_PROD_CAP_HOURS));
      var rate = base * boost;
      if (rate <= 0) continue;
      var hr = Math.max(0, (now - num(e.lastCollect, now)) / LOOT_HR_MS);
      var acc = rate * hr;
      if (acc > cap) acc = cap;
      var units = Math.floor(acc) + Math.max(0, e.stored | 0);
      if (units > cap) units = cap;
      if (units <= 0) continue;
      if (cfg.kind === "gold") { out.gold += units; out.value += units; }
      else {
        out.scrap[cfg.rarity] = (out.scrap[cfg.rarity] | 0) + units;
        out.value += units * num(SCRAP_DUPE[cfg.rarity], 0);
      }
    }
    return out;
  }

  /* lootPoolsFor(defenderProfile, now?) -> { storage, collector, treasury, townHall,
   * total, ... }. Every pool is a GOLD-EQUIVALENT integer, already rate-applied,
   * already capped, already carrying the defender's rarity bonus. `total` is the
   * absolute maximum a 100% destruction + Town Hall kill + zero-penalty raid could
   * ever yield against this base. `detail` carries the source composition so
   * resolveLoot can pay the award out in the ACTUAL currencies the defender holds.
   * PURE: never mutates the profile it is handed. */
  function lootPoolsFor(def, now) {
    def = (def && typeof def === "object") ? def : {};
    now = num(now, Date.now());
    var th = lootTH(def.townHall);
    var cap = lootCap(th);
    var bonus = lootRarityBonus(def);
    var gain = 1 + bonus;

    // STORAGE: the liquid bank, each kind valued in gold at its canon sell rate.
    var bank = {
      gold:    Math.max(0, def.coins   | 0),
      produce: Math.max(0, def.produce | 0),
      wood:    Math.max(0, def.wood    | 0),
      stone:   Math.max(0, def.stone   | 0),
      metal:   Math.max(0, def.metal   | 0)
    };
    var unit = {
      gold: 1, produce: PRODUCE_GOLD,
      wood: num(MAT_SELL.wood, 0), stone: num(MAT_SELL.stone, 0), metal: num(MAT_SELL.metal, 0)
    };
    var bankValue = 0, k;
    var coll = lootCollectorPending(def, now);
    var effScrap = (def.scrap && typeof def.scrap === "object") ? def.scrap : {};
    var hallHold = null;

    // AK-STORE interop: if storages.js is live it owns the bucket partition (derived
    // from the shared p.builds[]), so take WHERE things sit from it and keep the rates
    // here. Scrap is pulled out of the storage/Hall buckets into the TREASURY pool so
    // the two modules can never double-count it. Absent/erroring -> own derivation.
    var src = lootSourcesFrom(def, now);
    if (src) {
      bank = { gold: src.bank.gold, produce: src.bank.produce, wood: src.bank.wood,
               stone: src.bank.stone, metal: src.bank.metal };
      coll = { gold: src.coll.gold, scrap: src.coll.scrap, value: 0 };
      coll.value = coll.gold + lootScrapValue(coll.scrap);
      effScrap = {};                                     // banked + Hall scrap -> treasury, counted once
      for (k in src.bank.scrap) if (src.bank.scrap.hasOwnProperty(k)) effScrap[k] = (effScrap[k] | 0) + src.bank.scrap[k];
      for (k in src.hall.scrap) if (src.hall.scrap.hasOwnProperty(k)) effScrap[k] = (effScrap[k] | 0) + src.hall.scrap[k];
      hallHold = src.hall;
    }
    for (k in bank) if (bank.hasOwnProperty(k)) bankValue += bank[k] * unit[k];
    var scrapValue = lootScrapValue(effScrap);

    // PRESUMED BASE: no bank, no collectors, no scrap anywhere -> a generated target.
    // Fill each pool to exactly its own cap (see LOOT_PRESUMED_* above).
    var rate = lootStorageRate(th);
    var presumed = (bankValue <= 0 && coll.value <= 0 && scrapValue <= 0);
    if (presumed) {
      var wantBank = cap / rate;                                    // so bankValue * rate == cap
      for (k in LOOT_PRESUMED_BANK) if (LOOT_PRESUMED_BANK.hasOwnProperty(k) && unit[k] > 0) {
        bank[k] = Math.floor(wantBank * LOOT_PRESUMED_BANK[k] / unit[k]);
        bankValue += bank[k] * unit[k];
      }
      var wantColl = (cap * LOOT_COLLECTOR_CAP_FRAC) / LOOT_COLLECTOR_RATE;
      coll = { gold: Math.floor(wantColl * LOOT_PRESUMED_COLL.gold), scrap: {}, value: 0 };
      coll.value = coll.gold;
      coll.scrap.Rare = Math.floor(wantColl * LOOT_PRESUMED_COLL.Rare / num(SCRAP_DUPE.Rare, 1));
      coll.scrap.Epic = Math.floor(wantColl * LOOT_PRESUMED_COLL.Epic / num(SCRAP_DUPE.Epic, 1));
      coll.value += lootScrapValue(coll.scrap);
      var wantScrap = (cap * LOOT_TREASURY_CAP_FRAC) / LOOT_TREASURY_RATE;
      var pScrap = {};
      for (k in LOOT_PRESUMED_SCRAP) if (LOOT_PRESUMED_SCRAP.hasOwnProperty(k)) {
        pScrap[k] = Math.floor(wantScrap * LOOT_PRESUMED_SCRAP[k] / num(SCRAP_DUPE[k], 1));
      }
      effScrap = pScrap;
      scrapValue = lootScrapValue(pScrap);
    }

    var storage = Math.min(bankValue * rate, cap) * gain;

    // COLLECTOR: uncollected producer yield, the pool the defender chose to leave out.
    var collector = Math.min(coll.value * LOOT_COLLECTOR_RATE, cap * LOOT_COLLECTOR_CAP_FRAC) * gain;

    // TREASURY: a token slice of the scrap bag.
    var treasury = Math.min(scrapValue * LOOT_TREASURY_RATE, cap * LOOT_TREASURY_CAP_FRAC) * gain;

    // TOWN HALL: the ONLY pool gated on actually killing the Hall. With storages.js
    // live this is the Hall's REAL non-scrap holdings (transfer, not minting), still
    // bounded by the TH cap curve. Without it, the flat vault.
    var hallValue = 0;
    if (hallHold) {
      hallValue = hallHold.gold * unit.gold + hallHold.produce * unit.produce
                + hallHold.wood * unit.wood + hallHold.stone * unit.stone + hallHold.metal * unit.metal;
    }
    var townHall = (hallValue > 0 ? Math.min(hallValue, cap * LOOT_TH_VAULT_FRAC) : cap * LOOT_TH_VAULT_FRAC) * gain;

    storage = Math.floor(storage); collector = Math.floor(collector);
    treasury = Math.floor(treasury); townHall = Math.floor(townHall);

    return {
      storage: storage, collector: collector, treasury: treasury, townHall: townHall,
      total: storage + collector + treasury + townHall,
      th: th, cap: cap, storageRate: rate, rarityBonus: bonus, presumed: presumed,
      viaStorages: !!src,
      detail: { bank: bank, unit: unit, bankValue: bankValue, collector: coll,
                scrap: effScrap, scrapValue: scrapValue, hall: hallHold }
    };
  }

  /* lootPenalty(attackerTH, defenderTH) -> multiplier. Attacking DOWN is taxed by
   * Town Hall difference so farming weak bases stops paying; attacking equal or UP
   * is always full value. PURE. */
  function lootPenalty(attackerTH, defenderTH) {
    var diff = lootTH(attackerTH) - lootTH(defenderTH);
    if (diff <= 0) return LOOT_PENALTY_LADDER[0];
    if (diff >= LOOT_PENALTY_LADDER.length) return LOOT_PENALTY_FLOOR;
    return LOOT_PENALTY_LADDER[diff];
  }

  // Split a gold-equivalent take across weighted sources, converting value back into
  // real UNITS at each source's own gold rate. Returns { key: units }.
  function lootSplit(take, parts) {
    var out = {}, totalW = 0, i;
    if (!(take > 0)) return out;
    for (i = 0; i < parts.length; i++) totalW += Math.max(0, parts[i].value);
    if (!(totalW > 0)) return out;
    for (i = 0; i < parts.length; i++) {
      var pt = parts[i];
      if (!(pt.value > 0) || !(pt.unit > 0)) continue;
      var share = take * (pt.value / totalW);
      var units = Math.floor(share / pt.unit);
      if (units > pt.have) units = pt.have;          // never pay out more than the defender holds
      if (units > 0) out[pt.key] = (out[pt.key] | 0) + units;
    }
    return out;
  }

  /* resolveLoot(defenderProfile, attackerTH, destructionPct, townHallDestroyed, opts?)
   * -> the FINAL award, paid in the real currencies the defender actually holds.
   *
   *   award = ( (storage + collector + treasury) * destruction + townHallPool )
   *           * lootPenalty(attackerTH, defenderTH)
   *
   * Destruction scales the three standing pools linearly (you carry out what you
   * wrecked); the Town Hall vault is all-or-nothing on killing the Hall, which is
   * what makes going for the Hall a real decision instead of an afterthought.
   * destructionPct accepts either 0..1 or 0..100. PURE: computes, never banks. The
   * caller banks via mutateProfile / addScrap / bankMaterial (see the wiring note in
   * the AK-LOOTMATH header). */
  function resolveLoot(def, attackerTH, destructionPct, townHallDestroyed, opts) {
    opts = opts || {};
    def = (def && typeof def === "object") ? def : {};
    var now = num(opts.now, Date.now());
    var defTH = lootTH(def.townHall);
    var atkTH = lootTH(attackerTH);
    var pools = lootPoolsFor(def, now);

    var d = num(destructionPct, 0);
    if (d > 1) d = d / 100;                          // accept 0..100 as well as 0..1
    d = clampN(d, 0, 1);
    var pen = lootPenalty(atkTH, defTH);
    var thPaid = townHallDestroyed ? pools.townHall : 0;

    var storageTake   = pools.storage   * d * pen;
    var collectorTake = pools.collector * d * pen;
    var treasuryTake  = pools.treasury  * d * pen;
    var vaultTake     = Math.floor(thPaid * pen);    // the vault pays in gold

    var dt = pools.detail;
    var award = { gold: 0, produce: 0, wood: 0, stone: 0, metal: 0, scrap: {} };
    var i, r, key;

    // STORAGE -> the liquid bank, proportional to each kind's share of bank value.
    var bankParts = [];
    for (key in dt.bank) if (dt.bank.hasOwnProperty(key)) {
      bankParts.push({ key: key, unit: dt.unit[key], have: dt.bank[key], value: dt.bank[key] * dt.unit[key] });
    }
    var got = lootSplit(storageTake, bankParts);
    for (key in got) if (got.hasOwnProperty(key)) award[key] += got[key];

    // COLLECTOR -> the producer kinds that were sitting uncollected.
    var collParts = [{ key: "gold", unit: 1, have: dt.collector.gold, value: dt.collector.gold }];
    for (r in dt.collector.scrap) if (dt.collector.scrap.hasOwnProperty(r)) {
      var cu = num(SCRAP_DUPE[r], 0), ch = dt.collector.scrap[r] | 0;
      collParts.push({ key: "scrap:" + r, unit: cu, have: ch, value: ch * cu });
    }
    got = lootSplit(collectorTake, collParts);
    for (key in got) if (got.hasOwnProperty(key)) {
      if (key.indexOf("scrap:") === 0) award.scrap[key.slice(6)] = (award.scrap[key.slice(6)] | 0) + got[key];
      else award[key] += got[key];
    }

    // TREASURY -> the scrap bag, proportional to each rarity's share of scrap value.
    var scrapParts = [];
    for (i = 0; i < RARITIES.length; i++) {
      r = RARITIES[i];
      var su = num(SCRAP_DUPE[r], 0), sh = Math.max(0, dt.scrap[r] | 0);   // dt.scrap = the EFFECTIVE bag (presumed for a generated base)
      if (sh > 0 && su > 0) scrapParts.push({ key: r, unit: su, have: sh, value: sh * su });
    }
    got = lootSplit(treasuryTake, scrapParts);
    for (key in got) if (got.hasOwnProperty(key)) award.scrap[key] = (award.scrap[key] | 0) + got[key];

    // TOWN HALL VAULT -> gold, only when the Hall actually came down.
    award.gold += vaultTake;

    var totalValue = award.gold * 1 + award.produce * dt.unit.produce
                   + award.wood * dt.unit.wood + award.stone * dt.unit.stone + award.metal * dt.unit.metal
                   + lootScrapValue(award.scrap);

    return {
      gold: award.gold, produce: award.produce,
      wood: award.wood, stone: award.stone, metal: award.metal, scrap: award.scrap,
      total: Math.round(totalValue),
      pools: { storage: pools.storage, collector: pools.collector, treasury: pools.treasury,
               townHall: pools.townHall, total: pools.total },
      penalty: pen, destruction: d, townHallDestroyed: !!townHallDestroyed,
      attackerTH: atkTH, defenderTH: defTH, cap: pools.cap, presumed: pools.presumed,
      storageRate: pools.storageRate, rarityBonus: pools.rarityBonus
    };
  }

  // cropValue(crop): the gold-per-unit sell value of a crop, so CROPS are tradeable
  // for currency at the Fence. `crop` may be a crop KEY ("catnip") or a CROPS entry
  // object. Unknown crop -> 0 (falsy-default). Pure read; sellCrop() banks this * n.
  function cropValue(crop) {
    var c = (crop && typeof crop === "object") ? crop : CROPS[crop];
    return c ? num(c.sell, 0) : 0;
  }

  // ==========================================================================
  // AK-AFTERMATH (2026-06-30): PERSISTENT BASE DAMAGE + LINEAR REBUILD. The
  // operator: "the opponents base would then need to get rebuilt from whatever
  // damage was taken in the raid. that applies for if our base gets attacked as
  // well ... visual aftermath from a raid ... that drives the economy."
  //
  // When the PLAYER's base is raided, each hit building records a damage fraction
  // (0..1) and a timestamp. From that moment the damage DECAYS LINEARLY back to 0
  // over REBUILD_HOURS -- the structure "rebuilds itself" and the visual aftermath
  // (cracks / rubble) fades as it repairs. The host (index.html) reads
  // buildingDamage() every frame to render the aftermath + a rebuild bar, baseIntact()
  // for the overall state, and damageYieldMult() so a damaged PRODUCER pays less while
  // it is broken (the economy bite that makes a raid HURT).
  //
  // State lives in the lazily-created field p.baseDmg = { <id>: { d, t } }. It is
  // NOT backfilled in ensureShape -- a fresh profile has NO baseDmg key (zero-state
  // stays byte-identical, mirrors p.stamina / p.downed). Nothing is written until the
  // first real hit. Every read is falsy-safe via (x|0) / num() and DETERMINISTIC from
  // (stored d, t, now) -- no RNG, no per-frame write (60fps-safe pure reads). The
  // OPPONENT base damage shown DURING a live raid is index.html's job (it owns the raid
  // sim); THIS module owns the player's PERSISTENT post-raid damage + the decay math.
  // ==========================================================================
  var REBUILD_HOURS = 6;                        // full (1.0) damage rebuilds to 0 in 6h
  var REBUILD_MS = REBUILD_HOURS * 3600000;     // ms form of the rebuild window
  var DMG_YIELD_BITE = 0.5;                     // a fully-damaged producer pays 50% less while broken

  // applyBaseDamage(idDamageMap): called when the PLAYER's base is RAIDED. For each
  // building id in the map, store the damage fraction (clamped 0..1) and stamp t=now,
  // in ONE atomic write. A 0 (or falsy) entry CLEARS any existing record for that id (a
  // fully-repaired building leaves no trace). p.baseDmg is lazily created only when a
  // real (>0) hit lands, so a raid that does no damage never writes the key. Returns
  // { ok, damaged:[ids], now } | { ok:false, error }.
  function applyBaseDamage(idDamageMap) {
    if (!idDamageMap || typeof idDamageMap !== "object") return { ok: false, error: "BAD_MAP" };
    var out = { ok: false, damaged: [], now: 0 };
    mutateProfile(function (p) {
      var t = Date.now();
      for (var id in idDamageMap) {
        if (!idDamageMap.hasOwnProperty(id)) continue;
        var raw = clampN(num(idDamageMap[id], 0), 0, 1);
        var d = raw > 0 ? raw * (1 - Math.min(0.75, buildingFortify(p, id) * 0.15)) : 0;   // AK-FORTIFY: fortified buildings absorb part of the hit (Lv1 -15% .. Lv5 -75%)
        if (raw <= 0) {
          if (p.baseDmg && p.baseDmg[id]) delete p.baseDmg[id];              // an explicit 0 repairs / clears the record
        } else if (d > 0.02) {
          if (!p.baseDmg || typeof p.baseDmg !== "object") p.baseDmg = {};   // lazy: created ONLY on real (post-fortify) damage
          p.baseDmg[id] = { d: d, t: t };
        }
      }
      out = { ok: true, damaged: (p.baseDmg ? Object.keys(p.baseDmg) : []), now: t };
    });
    return out;
  }

  // buildingDamage(p, id, now): CURRENT damage 0..1 for one building, DECAYING linearly
  // back to 0 over REBUILD_MS from the stored stamp. PURE read, deterministic from
  // (stored d, t, now); no record => 0. This is the crack / rubble intensity the host
  // renders; (1 - this) is the rebuild progress.
  function buildingDamage(p, id, now) {
    try {
      var e = p && p.baseDmg && p.baseDmg[id];
      if (!e) return 0;
      now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
      var d0 = clampN(num(e.d, 0), 0, 1);
      if (d0 <= 0) return 0;
      var elapsed = Math.max(0, now - num(e.t, 0));
      var cur = d0 * (1 - (elapsed / REBUILD_MS));    // linear decay: d0 at impact, 0 after the window
      return cur > 0 ? clampN(cur, 0, 1) : 0;
    } catch (_) { return 0; }
  }

  // baseIntact(p, now): overall 0..1 repair state across ALL recorded buildings
  // (1 = fully repaired / pristine, 0 = everything just leveled). Averages the LIVE
  // (decayed) damage of the recorded buildings; a base with no record reads 1. PURE.
  function baseIntact(p, now) {
    try {
      var m = p && p.baseDmg;
      if (!m || typeof m !== "object") return 1;
      now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
      var sum = 0, n = 0;
      for (var id in m) { if (!m.hasOwnProperty(id)) continue; n++; sum += buildingDamage(p, id, now); }
      if (n <= 0) return 1;
      return clampN(1 - (sum / n), 0, 1);
    } catch (_) { return 1; }
  }

  // AK-REPAIR 2026-07-01: pay GOLD to instantly fix a raided building (else it rebuilds itself over 6h).
  // Cost scales with LIVE damage. On pay, clears the baseDmg record (fully repaired).
  function repairQuote(p, id, now) {
    p = p || loadProfile(); now = (typeof now === "number") ? now : Date.now();
    var d = buildingDamage(p, id, now);
    return { damaged: d > 0.02, damage: d, cost: Math.round(60 + 340 * d) };
  }
  function repairBuilding(id) {
    var res = { ok: false };
    if (!repairQuote(loadProfile(), id).damaged) return { ok: false, error: "NOT_DAMAGED" };
    mutateProfile(function (p) {
      var cost = repairQuote(p, id).cost;
      if ((p.coins | 0) < cost) { res = { ok: false, error: "INSUFFICIENT_FUNDS", need: cost, have: p.coins | 0 }; return; }
      p.coins = (p.coins | 0) - cost;
      if (p.baseDmg && p.baseDmg[id]) delete p.baseDmg[id];
      res = { ok: true, cost: cost };
    });
    return res;
  }
  // AK-FORTIFY 2026-07-01: spend WOOD + STONE to raise a building's fortify level (raid-defense).
  // Canon: trees(wood) + stone -> FORTIFY districts vs raids. Falsy-safe p.fortify{ id:lvl }, cap 5.
  var FORTIFY_MAX = 5;
  function buildingFortify(p, id) { return (p && p.fortify && (p.fortify[id] | 0)) || 0; }
  function fortifyCost(lvl) { return { wood: 20 + 15 * lvl, stone: 15 + 12 * lvl }; }
  function fortifyQuote(p, id) {
    p = p || loadProfile(); var lvl = buildingFortify(p, id);
    if (lvl >= FORTIFY_MAX) return { level: lvl, maxed: true, cost: null };
    var c = fortifyCost(lvl);
    return { level: lvl, maxed: false, cost: c, canAfford: ((p.wood | 0) >= c.wood && (p.stone | 0) >= c.stone) };
  }
  function fortifyBuilding(id) {
    var res = { ok: false };
    mutateProfile(function (p) {
      var lvl = buildingFortify(p, id);
      if (lvl >= FORTIFY_MAX) { res = { ok: false, error: "MAX", level: lvl }; return; }
      var c = fortifyCost(lvl);
      if ((p.wood | 0) < c.wood || (p.stone | 0) < c.stone) { res = { ok: false, error: "INSUFFICIENT_MATERIALS", need: c, have: { wood: p.wood | 0, stone: p.stone | 0 } }; return; }
      p.wood = (p.wood | 0) - c.wood; p.stone = (p.stone | 0) - c.stone;
      if (!p.fortify || typeof p.fortify !== "object") p.fortify = {};
      p.fortify[id] = lvl + 1;
      res = { ok: true, level: lvl + 1, spent: c };
    });
    return res;
  }

  // damageYieldMult(p, id, now): the ECONOMY BITE. While a PRODUCER (GEM/MINT/FORGE/
  // LAB/GEN) is damaged, its yield is cut by up to DMG_YIELD_BITE (50% at full damage,
  // scaling linearly back to 1.0 as it rebuilds). production.js can multiply its hourly
  // rate by this. Non-producers (or undamaged) read 1.0 (no bite). PURE read.
  function damageYieldMult(p, id, now) {
    if (!PRODUCERS[String(id || "").toUpperCase()]) return 1;
    var dmg = buildingDamage(p, id, now);
    return clampN(1 - DMG_YIELD_BITE * dmg, 1 - DMG_YIELD_BITE, 1);
  }

  // ==========================================================================
  // AK-BONES 2026-07-18 (ONE WALLET): Bones shipped as TWO pockets wearing one
  // name and one icon. p.bones is the DUTY pocket (duties / population / viral /
  // the Fence first-buy) and is what the HUD reads; p.handlers.bones is the
  // HANDLER pocket (match rewards + tribute) and only ever bought skill-tree
  // nodes. Match bones never reached the HUD; duty bones never bought a node.
  // This is the canonical wallet: read the SUM, spend across BOTH pockets in a
  // defined order, so any bone can satisfy any sink. BOTH underlying fields stay
  // intact -- other files own every write site, so nothing here renames or moves
  // a field and an untouched profile still reads zero-state byte-identical.
  // Draw order: DUTY pocket first, then HANDLER, so the number the player is
  // already watching in the HUD moves before the hidden pocket does. Pass
  // prefer "handler" to flip it for handler-lane sinks (the skill tree).
  // ==========================================================================
  function bonesPockets(p) {
    p = p || loadProfile();
    var duty = Math.max(0, (p && p.bones) | 0);
    var hand = Math.max(0, (p && p.handlers && p.handlers.bones) | 0);
    return { duty: duty, handler: hand, total: duty + hand };
  }
  // The ONE bones number: p.bones + p.handlers.bones. PURE (pass a profile to
  // skip the localStorage hit; 60fps-safe). This is what the HUD should show.
  function bonesTotal(p) { return bonesPockets(p).total; }
  function canAffordBones(n, p) { return bonesPockets(p).total >= Math.max(0, n | 0); }
  // Apply a bones debit to an ALREADY-LOADED profile, in place. The module's own
  // sinks call this INSIDE their existing mutateProfile pass so no second
  // load/save is nested. Writes nothing when the wallet is short. Returns
  // { ok, spent, from:{duty,handler}, have, need } (have = the total AFTER a
  // successful draw, the total BEFORE on a refusal, mirroring the old shape).
  function drawBones(p, n, prefer) {
    n = Math.max(0, n | 0);
    var pk = bonesPockets(p), none = { duty: 0, handler: 0 };
    if (n <= 0) return { ok: true, spent: 0, from: none, have: pk.total, need: 0 };
    if (pk.total < n) return { ok: false, error: "INSUFFICIENT_BONES", spent: 0, from: none, have: pk.total, need: n };
    var handFirst = (prefer === "handler");
    var first = Math.min(n, handFirst ? pk.handler : pk.duty), rest = n - first;
    var dDuty = handFirst ? rest : first, dHand = handFirst ? first : rest;
    p.bones = pk.duty - dDuty;
    if (dHand > 0) {
      if (!p.handlers || typeof p.handlers !== "object") p.handlers = { selected: "handler_mender", bones: 0, unlocked: {} };
      p.handlers.bones = pk.handler - dHand;
    }
    return { ok: true, spent: n, from: { duty: dDuty, handler: dHand }, have: pk.total - n, need: n };
  }
  // Atomic public spend. ANY sink can charge the whole wallet through this, so a
  // stamina refill can be paid with match bones and a skill node with duty bones.
  function spendBones(n, opts) {
    opts = opts || {};
    var out = { ok: false, error: "FAIL" };
    mutateProfile(function (p) { out = drawBones(p, n, opts.prefer); });
    return out;
  }
  // ONE grant front door so new earn-paths stop picking a pocket by hand. Default
  // lands in the HUD-visible duty pocket; opts.into "handler" targets the
  // skill-tree pocket. A negative n routes back through the unified draw.
  function addBones(n, opts) {
    opts = opts || {};
    n = Math.round(num(n, 0));
    var into = (opts.into === "handler") ? "handler" : "duty";
    if (n < 0) return spendBones(-n, { prefer: into });
    var out = { ok: false, added: 0, total: 0, into: into };
    mutateProfile(function (p) {
      if (into === "handler") {
        if (!p.handlers || typeof p.handlers !== "object") p.handlers = { selected: "handler_mender", bones: 0, unlocked: {} };
        p.handlers.bones = Math.max(0, (p.handlers.bones | 0) + n);
      } else p.bones = Math.max(0, (p.bones | 0) + n);
      out = { ok: true, added: n, total: bonesPockets(p).total, into: into };
    });
    return out;
  }

  // ==========================================================================
  // AK-STAMINA (CAPTIVATION_PLAN P4): "BONES TO RUN" -- the deadline on the
  // reward-raid loop (Genshin resin, parity-safe). A time-regen pool that fills
  // from empty to full in ~8h (copies the production.js CAP_HOURS pattern), so it
  // is optimal to SPEND before it caps -- "achieve something on a clock." Refills
  // by TIME or by BONES (the soulbound soft currency) ONLY. NEVER gems, never
  // pay-to-win -- stamina only meters REWARD-raids; Story / free-roam / the Watch
  // stay unmetered so the open-world feel survives.
  //
  // State lives in the lazily-created field `p.stamina = { cur, last }`. It is NOT
  // backfilled in ensureShape -- an untouched profile has no p.stamina and reads
  // as FULL (zero-state stays byte-identical; nothing is written until the first
  // spend / refill, mirroring production.js's lazy p.prod[bid] entries). cur is a
  // float so sub-point regen is preserved across frequent spends; the player sees
  // Math.floor(cur). Deterministic from (now - last) elapsed time -- no RNG.
  // ==========================================================================
  var HR_MS            = 3600000;
  var STAM_MAX         = 12;     // max "Bones to Run" points (a handful of reward-raids per fill)
  var STAM_CAP_HOURS   = 8;      // empty -> full regen window (~8h, the production.js CAP_HOURS feel)
  var STAM_BONES_REFILL= 20;     // bones to instantly refill to full (the soft-currency, non-gem path)
  var STAM_RATE_MS     = STAM_MAX / (STAM_CAP_HOURS * HR_MS);   // points regenerated per ms

  // Live stamina from a profile at time `now`. PURE read (pass a profile to skip
  // the localStorage hit; 60fps-safe). Absent / falsy p.stamina => FULL.
  function staminaState(p, now) {
    p = p || loadProfile();
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var max = STAM_MAX, st = p && p.stamina, cur, last;
    if (!st || typeof st !== "object") { cur = max; last = now; }          // never touched -> full
    else {
      cur = clampN(num(st.cur, max), 0, max);
      last = num(st.last, now);
      if (last > now) last = now;                                          // clock-skew guard
    }
    var live = clampN(cur + (now - last) * STAM_RATE_MS, 0, max);
    var floorPts = Math.floor(live + 1e-9);
    var full = live >= max - 1e-9;
    // ms to the next whole point + to a full bar (deterministic countdowns for the HUD)
    var nextInMs = full ? 0 : Math.max(0, Math.ceil((Math.floor(floorPts + 1) - live) / STAM_RATE_MS));
    var fullInMs = full ? 0 : Math.max(0, Math.ceil((max - live) / STAM_RATE_MS));
    return { cur: floorPts, raw: live, max: max, full: full, regenMs: Math.round(1 / STAM_RATE_MS), nextInMs: nextInMs, fullInMs: fullInMs };
  }
  // Public live read of the raid-stamina pool (the HUD + raid gate call this).
  function raidStamina(p) { return staminaState(p, Date.now()); }
  function staminaFull(p) { return staminaState(p, Date.now()).full; }
  // SPEND n stamina to launch a reward-raid. Atomic; refuses if the floored live
  // pool is short. Persists the remaining float + a fresh `last` so regen resumes
  // cleanly. Returns { ok, spent, cur, max } | { ok:false, error, have, need, fullInMs }.
  function spendStamina(n) {
    n = Math.max(0, n | 0); if (n <= 0) n = 1;
    var r = { ok: false, error: "NO_STAMINA" };
    mutateProfile(function (p) {
      var now = Date.now(), s = staminaState(p, now);
      if (s.cur < n) { r = { ok: false, error: "NO_STAMINA", have: s.cur, need: n, fullInMs: s.fullInMs }; return; }
      p.stamina = { cur: clampN(s.raw - n, 0, STAM_MAX), last: now };
      r = { ok: true, spent: n, cur: Math.floor(p.stamina.cur + 1e-9), max: STAM_MAX };
    });
    return r;
  }
  // REFILL to full. payWith = "bones" (default) -- TIME or BONES only, NEVER gems
  // (the parity hard-law: stamina can never be bought with the premium currency).
  function refillStamina(payWith) {
    payWith = payWith || "bones";
    if (payWith === "gems") return { ok: false, error: "GEMS_NEVER", server: false };   // parity: stamina is never gem-refillable
    if (payWith !== "bones") return { ok: false, error: "BAD_PAY" };
    var r = { ok: false, error: "FAIL" };
    mutateProfile(function (p) {
      var now = Date.now(), s = staminaState(p, now);
      if (s.full) { r = { ok: false, error: "ALREADY_FULL", cur: s.cur, max: STAM_MAX }; return; }
      var cost = STAM_BONES_REFILL;
      // AK-BONES 2026-07-18: charge the WHOLE wallet (duty pocket then handler
      // pocket), so bones earned in a match can finally pay for a refill.
      var d = drawBones(p, cost, "duty");
      if (!d.ok) { r = { ok: false, error: "INSUFFICIENT_BONES", have: d.have, need: cost }; return; }
      p.stamina = { cur: STAM_MAX, last: now };
      r = { ok: true, paid: { bones: cost, from: d.from }, cur: STAM_MAX, max: STAM_MAX };
    });
    return r;
  }

  // ==========================================================================
  // AK-CRATES (timed-unlock SLOTS): the Clash-Royale chest-slot deadline layer.
  // Up to 3 slots hold a queued crate that unlocks on a per-class TIMER; a ready
  // slot is CLAIMED through the existing openChest() reveal, or a slot is SKIPPED
  // early by spending BONES (the soulbound soft currency -- gems are server-only,
  // so a gem skip stays a server TODO). PURE time-reads (crateSlots) + atomic
  // mutating verbs (enqueue/claim/skip) through mutateProfile, mirroring AK-STAMINA.
  //
  // State lives in the lazily-created field `p.crateSlots = [ {id,tier,rarity,
  // startAt,unlockAt} ]`. It is NOT backfilled in ensureShape -- an untouched
  // profile has no p.crateSlots and reads as EMPTY (zero-state stays byte-identical;
  // nothing is written until the first enqueue). Deterministic from (unlockAt - now)
  // -- no RNG in the timer. claimCrate returns openChest()'s EXACT result shape so
  // the existing AKLoops.revealCrate cinematic runs on it unchanged.
  // ==========================================================================
  var CRATE_MAX_SLOTS   = 3;                        // Clash-style: 3 chest slots
  // per-class unlock duration in SECONDS (DURATION[tier] -- the crate's rarity class)
  var CRATE_DURATION    = { Common: 900, Rare: 10800, Epic: 28800, Legendary: 43200, Mythic: 86400 };
  var CRATE_DEFAULT_SEC = CRATE_DURATION.Rare;      // safe fallback (3h) for an unknown class
  var CRATE_SKIP_MS_PER_BONE = 360000;              // bones-skip curve: 1 bone per 6 remaining minutes

  // unlock seconds for a crate. Faithful to DURATION[tier]; falls back to the
  // rarity class then a default so a mislabeled/absent class is a no-op, never a
  // NaN unlockAt. Pure.
  function crateDurationSec(tier, rarity) {
    var d = CRATE_DURATION[tier];
    if (d == null) d = CRATE_DURATION[rarity];
    if (d == null) d = CRATE_DEFAULT_SEC;
    return d | 0;
  }
  // bones to skip the remaining wait. Scales with remaining time (ceil), min 1
  // bone while any time is left, 0 once ready. Pure. NEVER touches gems.
  function crateSkipCost(remainMs) {
    remainMs = Math.max(0, num(remainMs, 0));
    if (remainMs <= 0) return 0;
    return Math.max(1, Math.ceil(remainMs / CRATE_SKIP_MS_PER_BONE));
  }

  // Live slot list at time `now`. PURE read (pass a profile to skip the localStorage
  // hit; 60fps-safe). Absent / falsy p.crateSlots => []. Never mutates.
  function crateSlots(p, now) {
    p = p || loadProfile();
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var raw = (p && Array.isArray(p.crateSlots)) ? p.crateSlots : [];
    var out = [];
    for (var i = 0; i < raw.length && out.length < CRATE_MAX_SLOTS; i++) {
      var s = raw[i]; if (!s || typeof s !== "object") continue;
      var unlockAt = num(s.unlockAt, now);
      var remainMs = Math.max(0, unlockAt - now);
      out.push({
        id: s.id, tier: s.tier, rarity: s.rarity,
        startAt: num(s.startAt, now), unlockAt: unlockAt,
        ready: remainMs <= 0, remainMs: remainMs
      });
    }
    return out;
  }
  // Queue a crate into the next free slot. unlockAt = now + DURATION[tier]. Returns
  // { ok, slotId } or { ok:false, reason:'full' } when all 3 slots are taken (the
  // caller then falls back to an instant open). Atomic.
  function enqueueCrate(tier, rarity) {
    var out = { ok: false, reason: "fail" };
    mutateProfile(function (p) {
      if (!Array.isArray(p.crateSlots)) p.crateSlots = [];
      if (p.crateSlots.length >= CRATE_MAX_SLOTS) { out = { ok: false, reason: "full" }; return; }
      var now = Date.now();
      var id = "cr_" + now.toString(36) + "_" + Math.floor(Math.random() * 1679616).toString(36);
      p.crateSlots.push({ id: id, tier: tier, rarity: rarity, startAt: now, unlockAt: now + crateDurationSec(tier, rarity) * 1000 });
      out = { ok: true, slotId: id };
    });
    return out;
  }
  // Claim a READY slot: provision the entitlement chest then crack it through
  // openChest(), returning its EXACT result shape (net-zero inventory: grant +1,
  // open -1), and consume the slot on a successful open. Returns null if the slot
  // is missing or not yet ready (never opens a locked crate). `opts` (optional) is
  // forwarded to openChest (pool / perks / rng).
  function claimCrate(id, now, opts) {
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var found = null, list = crateSlots(loadProfile(), now);
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { found = list[i]; break; } }
    if (!found || !found.ready) return null;
    try { grantChest(found.tier); } catch (_) {}
    var res = openChest(found.tier, opts || {});
    if (res && res.ok) {
      mutateProfile(function (p) {
        if (!Array.isArray(p.crateSlots)) return;
        for (var j = 0; j < p.crateSlots.length; j++) {
          if (p.crateSlots[j] && p.crateSlots[j].id === id) { p.crateSlots.splice(j, 1); break; }
        }
      });
    }
    return res;
  }
  // Spend BONES to finish a slot's timer now (set unlockAt = now). Cost scales with
  // remaining time (crateSkipCost). Returns { ok, cost } | { ok:false, reason:'bones' }
  // when short | { ok:false, reason:'notfound' }. Atomic. Gems untouched (server TODO).
  function skipCrate(id) {
    var out = { ok: false, reason: "notfound" };
    mutateProfile(function (p) {
      if (!Array.isArray(p.crateSlots)) { p.crateSlots = []; return; }
      var now = Date.now(), s = null;
      for (var i = 0; i < p.crateSlots.length; i++) { if (p.crateSlots[i] && p.crateSlots[i].id === id) { s = p.crateSlots[i]; break; } }
      if (!s) return;
      var remainMs = Math.max(0, num(s.unlockAt, now) - now);
      if (remainMs <= 0) { out = { ok: true, cost: 0 }; return; }   // already ready -> free
      var cost = crateSkipCost(remainMs);
      var d = drawBones(p, cost, "duty");   // AK-BONES 2026-07-18: whole-wallet draw, not just p.bones
      if (!d.ok) { out = { ok: false, reason: "bones", have: d.have, need: cost }; return; }
      s.unlockAt = now;
      out = { ok: true, cost: cost, from: d.from };
    });
    return out;
  }

  // ==========================================================================
  // AK-FENCE PRICE MODEL (CAPTIVATION_PLAN P6 + P8): the EVE/RuneScape "second
  // game." goldValue(resource) is the canonical FLOATING gold-per-unit price at
  // THE FENCE. It blends an ANCHOR (the resource's base worth) with a RECENT-FILL
  // MEDIAN (the supply/demand signal off real sales), wanders on a deterministic
  // daily clock, is held to a +/-5%/day move (RuneScape GE daily cap), and is
  // hard-banded by a floor/ceiling so a price can never crash to 0 or moon. No
  // client RNG (a day-seeded smooth wave) -> every client reads the SAME price on
  // the SAME day = parity-safe. marketplace.js (THE FENCE / the Bazaar) can anchor
  // its book to this so the two surfaces never disagree.
  //
  // PURE + load-free by default (60fps ticker-safe): with no fills source the
  // recent-fill median falls back to the anchor (neutral). Pass opts.fills (an
  // array of recent sale prices) or opts.p (a profile snapshot whose p.fence ledger
  // recordFenceFill() fills) for the supply-responsive price.
  // ==========================================================================
  var PT_OFFSET_MS      = 8 * 3600000;   // anchor every world clock to LOCAL PT (UTC-8 / PST per workspace doctrine); a FIXED offset keeps it parity-safe (device TZ never changes the result)
  var FENCE_ANCHOR_WEIGHT = 0.65;        // fair value = 65% anchor + 35% recent-fill median
  var FENCE_WANDER_AMP    = 0.18;        // +/-18% deterministic daily float band (the price discovery)
  var FENCE_DAILY_CLAMP   = 0.05;        // +/-5%/day max move vs yesterday (GE-style daily cap)
  var FENCE_FLOOR_MULT    = 0.55;        // hard floor: price never below 0.55x anchor
  var FENCE_CEIL_MULT     = 1.55;        // hard ceiling: price never above 1.55x anchor
  var FENCE_FILL_KEEP     = 12;          // recent-fill ring length per resource (the median window)
  var FENCE_WEATHER       = { sun: 1.00, rain: 0.97, drought: 1.06 };   // supply read: rain glut -> cheaper, drought scarcity -> dearer

  function ptDayIndex(now) { now = (typeof now === "number" && isFinite(now)) ? now : Date.now(); return Math.floor((now - PT_OFFSET_MS) / 86400000); }
  function ptHour(now) { now = (typeof now === "number" && isFinite(now)) ? now : Date.now(); return (((now - PT_OFFSET_MS) % 86400000) + 86400000) % 86400000 / HR_MS; }
  // LOCAL-PT day/night phase (the night-market / dawn-bonus clock). Deterministic.
  function ptPhase(now) {
    var h = ptHour(now);
    var key = (h < 5) ? "night" : (h < 8) ? "dawn" : (h < 18) ? "day" : (h < 21) ? "dusk" : "night";
    return { key: key, hour: h, frac: h / 24 };
  }
  function _strHash(s) { s = String(s == null ? "" : s); var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; }
  // deterministic smooth daily wander in [-1,1], phased per-resource so each
  // resource floats independently. Two slow sinusoids (periods ~26d + ~61d) keep
  // the day-over-day delta structurally under ~3.5% -- inside the +/-5%/day clamp.
  function fenceWave(key, day) {
    var ph = (_strHash(key) % 628) / 100;   // 0..6.28 rad phase offset
    var a = Math.sin((2 * Math.PI / 26) * day + ph);
    var b = Math.sin((2 * Math.PI / 61) * day + ph * 1.7);
    return clampN(0.6 * a + 0.4 * b, -1, 1);
  }
  function _resKey(resource) {
    if (resource == null) return "";
    if (typeof resource === "object") { if (resource.kind === "scrap") return "scrap:" + (resource.rarity || "Common"); return String(resource.kind || resource.key || resource.name || ""); }
    return String(resource);
  }
  // anchor (base gold-per-unit) for any tradeable soft resource. Mirrors the
  // marketplace.js fair-value anchors (MAT_SELL / PRODUCE_GOLD / SCRAP_DUPE) so
  // the Fence price floats AROUND the same worth both surfaces already use.
  function fenceAnchor(resource) {
    if (resource == null) return 0;
    var kind, rarity;
    if (typeof resource === "object") { kind = resource.kind || resource.key || resource.name; rarity = resource.rarity; }
    else { kind = String(resource); }
    if (kind === "gold" || kind === "coins") return 1;
    if (kind === "produce") return PRODUCE_GOLD;
    if (kind === "scrap") return num(SCRAP_DUPE[rarity || "Common"], 0);
    if (isMaterial(kind)) return num(MAT_SELL[kind], 0);
    if (CROPS[kind]) return num(CROPS[kind].sell, 0);
    if (RARITIES.indexOf(kind) >= 0) return num(SCRAP_DUPE[kind], 0);   // a bare rarity name reads as that scrap tier
    return 0;
  }
  function _median(arr) {
    if (!arr || !arr.length) return null;
    var a = []; for (var i = 0; i < arr.length; i++) { var v = num(arr[i], NaN); if (isFinite(v) && v > 0) a.push(v); }
    if (!a.length) return null;
    a.sort(function (x, y) { return x - y; });
    var m = a.length >> 1;
    return (a.length % 2) ? a[m] : (a[m - 1] + a[m]) / 2;
  }
  function fenceFills(src, key) { try { var f = src && src.fence && src.fence.fills && src.fence.fills[key]; return Array.isArray(f) ? f : null; } catch (_) { return null; } }
  // goldValue(resource, opts?) -> floating Fence gold-per-unit.
  //   opts.now   : timestamp (defaults Date.now())
  //   opts.day   : override the PT day index (testing / a future-dated ticker)
  //   opts.fills : array of recent sale prices (the supply signal); else opts.p's ledger; else neutral
  //   opts.p     : a profile snapshot to read the recent-fill ledger from (load-free)
  function goldValue(resource, opts) {
    opts = opts || {};
    var anchor = fenceAnchor(resource);
    if (!(anchor > 0)) return 0;
    var key = _resKey(resource);
    var now = (opts.now != null) ? opts.now : Date.now();
    var day = (opts.day != null) ? Math.floor(num(opts.day, 0)) : ptDayIndex(now);
    var fills = Array.isArray(opts.fills) ? opts.fills : fenceFills(opts.p, key);
    var med = _median(fills); if (med == null || !(med > 0)) med = anchor;   // no sales yet -> neutral (== anchor)
    var fair = anchor * FENCE_ANCHOR_WEIGHT + med * (1 - FENCE_ANCHOR_WEIGHT);
    var today = fair * (1 + FENCE_WANDER_AMP * fenceWave(key, day));
    var yest  = fair * (1 + FENCE_WANDER_AMP * fenceWave(key, day - 1));
    var price = clampN(today, yest * (1 - FENCE_DAILY_CLAMP), yest * (1 + FENCE_DAILY_CLAMP));   // +/-5%/day cap
    price = clampN(price, anchor * FENCE_FLOOR_MULT, anchor * FENCE_CEIL_MULT);                  // hard floor/ceiling band
    return (anchor >= 2) ? Math.max(1, Math.round(price)) : Math.round(price * 100) / 100;       // integer for big anchors, 2dp for sub-2g (produce)
  }
  // record a real SALE price into the recent-fill ring so the median (and thus the
  // Fence price) responds to actual supply. Lazily creates p.fence (NOT in
  // ensureShape -> zero-state stays byte-identical). Atomic; capped ring.
  function recordFenceFill(resource, price) {
    var key = _resKey(resource); if (!key) return null;
    var pr = num(price, 0); if (!(pr > 0)) return null;
    return mutateProfile(function (p) {
      if (!p.fence || typeof p.fence !== "object") p.fence = {};
      if (!p.fence.fills || typeof p.fence.fills !== "object") p.fence.fills = {};
      var ring = Array.isArray(p.fence.fills[key]) ? p.fence.fills[key] : [];
      ring.push(Math.round(pr * 100) / 100);
      while (ring.length > FENCE_FILL_KEEP) ring.shift();
      p.fence.fills[key] = ring;
    });
  }

  // ==========================================================================
  // AK-ECONMOD (CAPTIVATION_PLAN P7 + P8): the WORLD-SIGNAL multiplier layer.
  // econMod() folds the live world clocks into one read for CROP YIELDS + FENCE
  // PRICES: the active CHAPTER/SEASON (window.AKSeasons), the deterministic
  // WEATHER (this file's gardenWeather), and DAY/NIGHT (window.AKDayNight when the
  // P7 daynight module ships; 1.0 until then). All soft-economy only, deterministic
  // by the world clock, identical for every player -> parity-safe, never power.
  // The LOCAL-PT phase is always reported (anchored to PT) so a night-market / dawn
  // bonus can read it now, ahead of the dedicated daynight module.
  // ==========================================================================
  // per-chapter soft-economy flavor (keys match seasons.js CHAPTERS). DOG DAYS
  // bumper crops + a glut; FROSTBITE frozen ground + scarcity; etc. Bounded, small.
  var CHAPTER_ECON = {
    junkyard:    { crop: 1.00, fence: 1.05 },   // JUNKYARD DYNASTY -- Boneguard scrap runs, the Fence dear
    neonhowl:    { crop: 1.00, fence: 1.06 },   // NEON HOWL -- Zoomie night-trade buzz lifts prices
    dogdays:     { crop: 1.15, fence: 0.95 },   // DOG DAYS -- Leashbreak summer, bumper crops + a glut
    bloodmoon:   { crop: 0.92, fence: 1.08 },   // BLOOD MOON -- K9 Circuitry red nights, lean + dear
    frostbite:   { crop: 0.85, fence: 1.12 },   // FROSTBITE -- frozen ground, hard times, scarcity premium
    goldenleash: { crop: 1.10, fence: 1.04 }    // GOLDEN LEASH -- the $BCARDD finale boom
  };
  function econMod(opts) {
    opts = opts || {};
    var now = (opts.now != null) ? opts.now : Date.now();
    // --- chapter / season (AKSeasons if present, else neutral 1.0) ---
    var cKey = "", seasonId = "", week = 0, daysLeft = 0;
    try { var S = global.AKSeasons; if (S && typeof S.current === "function") { var cur = S.current() || {}; cKey = cur.chapter || ""; seasonId = cur.id || ""; week = cur.week | 0; daysLeft = cur.daysLeft | 0; } } catch (_) {}
    var ce = CHAPTER_ECON[cKey] || { crop: 1, fence: 1 };
    // --- weather (this file's deterministic-by-day model -- always available) ---
    var wKey = "sun", wCrop = 1, wFence = 1;
    try { var gw = gardenWeather(weatherDay(now)); wKey = gw.key; wCrop = num(gw.yieldMult, 1); wFence = num(FENCE_WEATHER[wKey], 1); } catch (_) {}
    // --- day/night (AKDayNight if present, else 1.0; PT phase always reported) ---
    var phase = ptPhase(now), dnCrop = 1, dnFence = 1;
    try {
      var D = global.AKDayNight;
      if (D) {
        var dc = (typeof D.current === "function") ? D.current() : D;
        if (dc) {
          if (typeof dc.cropMult === "number" && isFinite(dc.cropMult)) dnCrop = dc.cropMult;
          if (typeof dc.fenceMult === "number" && isFinite(dc.fenceMult)) dnFence = dc.fenceMult;
          if (dc.phase) phase = { key: String(dc.phase), hour: phase.hour, frac: num(dc.frac, phase.frac) };
        }
      }
    } catch (_) {}
    return {
      crop:  clampN(ce.crop  * wCrop  * dnCrop,  0.6, 1.6),   // multiply onto a base crop yield
      fence: clampN(ce.fence * wFence * dnFence, 0.6, 1.6),   // multiply onto a base Fence price (world-event overlay)
      chapter: cKey, season: seasonId, week: week, daysLeft: daysLeft,
      weather: wKey, phase: phase.key, phaseFrac: phase.frac
    };
  }

  // ==========================================================================
  // AK-REP (CAPTIVATION_PLAN P10): "BLOCK REP" -- the COMPETITIVE clock, kept
  // hard-apart from the permanent economy (the Brawl Stars / Merge Tactics split).
  // Block Rep is a PvP-ONLY ladder metric, SEPARATE from gold: it BUYS NOTHING at
  // the Fence -- it ONLY drives the canon rank ladder
  //   Stray -> Pup -> Runner -> Warrior -> Enforcer -> Right Paw -> King of the Block.
  // A tower-lane / world-map PvP WIN = +Rep, a loss = -Rep, with Apex-style
  // DEMOTION PROTECTION (a single loss can never knock you OUT of Stray / Pup /
  // Runner). A MONTHLY SOFT RESET on the 1st (LOCAL-PT month index) churns the
  // ladder + carries a small placement bonus, and a rotating seasonal EXCLUSIVE
  // high-rarity dog is the cosmetic carrot at the top (PARITY HARD-LAW: cosmetic /
  // free-track / bones-earned, NEVER raw power, NEVER gem-gated).
  //
  // OBSERVED WITHOUT TOUCHING game.html (frozen): Block Rep is folded from the
  // SHARED rank ladder p.trophies (AK-RANK) -- the SAME counter the PvP tower
  // battle + world-map raids already move on a match result. We bank a per-season
  // baseline (repSeason.troSeen) and award Rep off the trophy DELTA since that
  // baseline, so no match-result edit / window event is required. State is lazily
  // created and is NOT backfilled in ensureShape -> an untouched profile has no
  // p.blockRep / p.repSeason and reads as Stray @ 0 (zero-state stays byte-
  // identical, mirroring p.stamina / p.fence). All writes go through
  // AK_ECON.mutateProfile (or a write-gated commit); deterministic-by-time,
  // anchored to LOCAL PT (PT_OFFSET_MS). Headless-safe: no timers, no top-level
  // DOM/localStorage; pure reads accept a profile snapshot to stay 60fps.
  // ==========================================================================
  // canon rank ladder (Rep thresholds). PROTECTED = the first 3 rungs cannot be
  // lost on a single defeat (the Apex demotion shield).
  var REP_LADDER = [
    [0,    "Stray"],
    [120,  "Pup"],
    [300,  "Runner"],
    [600,  "Warrior"],
    [1050, "Enforcer"],
    [1700, "Right Paw"],
    [2600, "King of the Block"]
  ];
  var REP_PROTECT_MAX_IDX = 2;        // Stray / Pup / Runner: no single-loss demotion
  var REP_CAP             = 999999;   // soft ceiling (anti-overflow; never reached in play)
  var REP_WIN_PER_TRO     = 2.0;      // a WIN's trophy gain -> Rep (a ~+16 tro win ~= +32 Rep)
  var REP_LOSS_PER_TRO    = 3.6;      // a LOSS's trophy dip -> Rep (losses bite harder per trophy -- ranked tension)
  var REP_SOFT_KEEP       = 0.25;     // monthly soft reset keeps ~25% of last season's Rep...
  var REP_SOFT_DROP_RANKS = 2;        // ...floored no lower than (endRank -- 2 rungs): a King lands at Enforcer
  var REP_EXCLUSIVE_RANK  = 4;        // the seasonal exclusive unlocks at Enforcer (REP_LADDER[4])

  // rank index for a Rep value (0..6). Pure.
  function repRankIndex(rep) {
    rep = Math.max(0, Math.floor(num(rep, 0)));
    var idx = 0;
    for (var i = 0; i < REP_LADDER.length; i++) { if (rep >= REP_LADDER[i][0]) idx = i; }
    return idx;
  }
  // LOCAL-PT month bucket (year*12 + month). Deterministic, parity-safe (FIXED PT
  // offset -> device TZ never changes the result); rolls at PT midnight on the 1st.
  function repMonthIndex(now) {
    var d = new Date(((typeof now === "number" && isFinite(now)) ? now : Date.now()) - PT_OFFSET_MS);
    return d.getUTCFullYear() * 12 + d.getUTCMonth();
  }
  // ms until the next monthly SOFT RESET (1st of next PT month, PT midnight). For
  // the HUD countdown. Deterministic; Date.UTC normalizes the December rollover.
  function repSeasonResetMs(now) {
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var d = new Date(now - PT_OFFSET_MS);
    var next = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1, 0, 0, 0, 0) + PT_OFFSET_MS;
    return Math.max(0, next - now);
  }
  // the placement carry a soft reset grants from last season's ending Rep: keep
  // ~25%, floored at (endRank -- 2 rungs), never above what you ended with.
  function repPlacementCarry(prevRep) {
    prevRep = Math.max(0, Math.floor(num(prevRep, 0)));
    var placeIdx = Math.max(0, repRankIndex(prevRep) - REP_SOFT_DROP_RANKS);
    var carry = Math.max(REP_LADDER[placeIdx][0], Math.round(prevRep * REP_SOFT_KEEP));
    return Math.min(carry, prevRep);
  }
  // map a SHARED-ladder (p.trophies) delta to a Rep delta. A gain (win) scales
  // gently; a dip (loss) bites harder per trophy. Deterministic.
  function repFromTrophyDelta(troDelta) {
    troDelta = Math.round(num(troDelta, 0));
    if (troDelta === 0) return 0;
    return (troDelta > 0) ? Math.round(troDelta * REP_WIN_PER_TRO)
                          : Math.round(troDelta * REP_LOSS_PER_TRO);
  }
  // apply a Rep delta to `cur` with Apex demotion protection. Pure -> next Rep.
  function repApplyDelta(cur, n) {
    cur = Math.max(0, Math.floor(num(cur, 0)));
    n = Math.round(num(n, 0));
    var next = cur + n;
    if (n < 0) {
      var idx = repRankIndex(cur);
      if (idx <= REP_PROTECT_MAX_IDX) next = Math.max(REP_LADDER[idx][0], next);   // shield: no single-loss demotion out of Stray/Pup/Runner
    }
    return clampN(next, 0, REP_CAP);
  }
  // --- live-season reconcile (the deterministic heart; NO writes here) ---------
  // Given a profile + now, compute the CURRENT-season Rep, folding (a) the monthly
  // SOFT RESET if the stored month rolled over and (b) the pending trophy DELTA
  // since the season baseline. Returns { rep, month, troSeen, reset }. PURE: never
  // touches localStorage -> 60fps-safe when handed a profile snapshot. A first-ever
  // read seeds the baseline at the current trophies (no retroactive Rep windfall).
  function repLive(p, now) {
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var month = repMonthIndex(now);
    var tro = Math.max(0, (p && p.trophies) | 0);
    var rs = (p && p.repSeason && typeof p.repSeason === "object") ? p.repSeason : null;
    var rep = Math.max(0, (p && p.blockRep) | 0);
    var seenMonth = rs ? (rs.m | 0) : null;
    var troSeen = rs ? Math.max(0, num(rs.troSeen, tro)) : tro;
    var reset = false;
    if (seenMonth == null) {
      troSeen = tro;                                            // never initialized -> baseline = now, no retro award
    } else if (seenMonth !== month) {
      var endRep = repApplyDelta(rep, repFromTrophyDelta(tro - troSeen));   // close out last season at its live Rep...
      rep = repPlacementCarry(endRep);                          // ...soft reset to the placement carry...
      troSeen = tro; reset = true;                              // ...and rebase the trophy baseline (new season counts only NEW wins)
    } else {
      rep = repApplyDelta(rep, repFromTrophyDelta(tro - troSeen));          // same season -> fold the pending trophy delta
      troSeen = tro;
    }
    return { rep: rep, month: month, troSeen: troSeen, reset: reset };
  }
  // bake the live season state into a profile IN PLACE (lazily creating the
  // fields). Returns the live snapshot. Caller persists (inside mutateProfile).
  function repBake(p, now) {
    var live = repLive(p, now);
    p.blockRep = live.rep;
    if (!p.repSeason || typeof p.repSeason !== "object") p.repSeason = {};
    p.repSeason.m = live.month; p.repSeason.troSeen = live.troSeen;
    return live;
  }
  // write-gated COMMIT (used by the no-argument reads = the self-driving hook):
  // load -> reconcile -> save ONLY if the persisted season state actually changed
  // (month rollover or a non-zero trophy delta). A steady-state no-arg read after
  // the first commit is a pure no-op (no write). Returns the live snapshot.
  function repCommit(now) {
    var p = loadProfile();
    var live = repLive(p, now);
    var rs = (p.repSeason && typeof p.repSeason === "object") ? p.repSeason : null;
    var changed = ((p.blockRep | 0) !== live.rep) || !rs ||
                  ((rs.m | 0) !== live.month) || (Math.max(0, num(rs.troSeen, -1)) !== live.troSeen);
    if (changed) {
      p.blockRep = live.rep;
      if (!p.repSeason || typeof p.repSeason !== "object") p.repSeason = {};
      p.repSeason.m = live.month; p.repSeason.troSeen = live.troSeen;
      saveProfile(p);
    }
    return live;
  }
  // blockRep(p?): current-season Block Rep. PASS A PROFILE for a 60fps PURE read;
  // call with NO ARGUMENT at a match-end / lobby-refresh point to COMMIT the
  // trophy-delta fold + the monthly reset (write-gated -- a no-op when nothing
  // changed). Never call the no-arg form inside a per-frame render loop.
  function blockRep(p) {
    var now = Date.now();
    return (p != null) ? repLive(p, now).rep : repCommit(now).rep;
  }
  // repRank(p?): the full canon-ladder readout the HUD renders -- rank name, index,
  // progress to the next rung, demotion-shield flag, and the season clock. Same
  // pass-a-profile (pure) vs no-arg (commit) contract as blockRep().
  function repRank(p) {
    var now = Date.now();
    var live = (p != null) ? repLive(p, now) : repCommit(now);
    var rep = live.rep, idx = repRankIndex(rep), floor = REP_LADDER[idx][0];
    var atTop = idx >= REP_LADDER.length - 1;
    var nextAt = atTop ? null : REP_LADDER[idx + 1][0];
    var span = atTop ? 0 : (nextAt - floor);
    return {
      rep: rep, rank: REP_LADDER[idx][1], index: idx, floor: floor,
      next: atTop ? null : REP_LADDER[idx + 1][1], nextAt: nextAt,
      toNext: atTop ? 0 : Math.max(0, nextAt - rep),
      progress: atTop ? 1 : (span > 0 ? clampN((rep - floor) / span, 0, 1) : 0),
      protected: idx <= REP_PROTECT_MAX_IDX, atTop: atTop,
      month: live.month, reset: live.reset, resetInMs: repSeasonResetMs(now)
    };
  }
  // addRep(n): the PRIMITIVE win/loss award (n>0 win, n<0 loss). Atomic. Bakes any
  // pending season state first (monthly reset + trophy fold) so the manual nudge
  // lands on the reconciled live Rep, then applies n with Apex demotion protection.
  // Returns { ok, rep, delta, rank, index, promoted, demoted, demotionProtected }.
  function addRep(n) {
    n = Math.round(num(n, 0));
    var out = { ok: false };
    mutateProfile(function (p) {
      var now = Date.now();
      var live = repBake(p, now);
      var before = live.rep, bIdx = repRankIndex(before);
      // AK-BLDWIRE 2026-07-18: TROPHY IS LIVE. The Trophy Room multiplies Rep GAINS
      // only -- a bonus building must never deepen a loss, so n<0 passes through
      // untouched (and demotionProtected below still tests the raw n). p is the
      // in-flight profile, so this is one read, no extra load.
      var eff = (n > 0) ? Math.max(n, Math.round(n * trophyRepMult(p))) : n;
      var after = repApplyDelta(before, eff);
      p.blockRep = after;
      var aIdx = repRankIndex(after);
      out = {
        ok: true, rep: after, delta: after - before,
        rank: REP_LADDER[aIdx][1], index: aIdx,
        promoted: aIdx > bIdx, demoted: aIdx < bIdx,
        demotionProtected: (n < 0 && bIdx <= REP_PROTECT_MAX_IDX && (before + n) < REP_LADDER[bIdx][0]),
        reset: live.reset
      };
    });
    // AK-VIRAL level-up share hook: a genuine PROMOTION (rank INDEX climbed on the
    // reconciled ladder) offers a shareable clip. Fully guarded -- AK_VIRAL is
    // optional; never fires on a demotion or a same-rank change (out.promoted is
    // aIdx > bIdx). A no-op if the mutate failed (out.ok is falsy).
    try {
      if (out && out.ok && out.promoted && global.AK_VIRAL && typeof global.AK_VIRAL.shareMoment === "function") {
        global.AK_VIRAL.shareMoment("levelup", { title: "RANKED UP", sub: "Climbed to " + out.rank });
      }
    } catch (_) {}
    return out;
  }
  // syncRep(): the self-contained "match-result hook" -- folds the pending trophy
  // delta (since the season baseline) + the monthly reset into persisted Rep, with
  // no game.html edit. Safe to call anytime (a no-op when no delta + same month).
  // Returns { ok, rep, delta, rank, index, reset }.
  function syncRep() {
    var out = { ok: false };
    mutateProfile(function (p) {
      var pre = Math.max(0, (p.blockRep) | 0);
      var live = repBake(p, Date.now());
      var idx = repRankIndex(live.rep);
      out = { ok: true, rep: live.rep, delta: live.rep - pre, rank: REP_LADDER[idx][1], index: idx, reset: live.reset };
    });
    return out;
  }
  // seasonalExclusive(now?, p?): the month's COSMETIC carrot -- a rotating EXISTING
  // high-rarity canon dog BY NAME (no new card), gated by a Rep threshold (free-
  // track / cosmetic / bones-earned, NEVER raw power, NEVER gem-gated). Rotates once
  // per LOCAL-PT month. PURE read (never writes). Names + factions are byte-faithful
  // to canon.js CANON_META.mythics + legendary.
  var REP_EXCLUSIVES = [
    { name: "$BCARDD",        rarity: "Mythic",    faction: "Boneguard Crew",    cosmetic: "Crown Dynasty regalia" },
    { name: "Jagged",         rarity: "Mythic",    faction: "Zoomie Syndicate",  cosmetic: "Neon Howl regalia" },
    { name: "Rosco",          rarity: "Mythic",    faction: "Leashbreak Tactix", cosmetic: "Dog Days regalia" },
    { name: "Crown Foxhound", rarity: "Mythic",    faction: "K9 Circuitry",      cosmetic: "Blood Moon regalia" },
    { name: "Stonejaw",       rarity: "Legendary", faction: "Boneguard Crew",    cosmetic: "Frostbite regalia" }
  ];
  function seasonalExclusive(now, p) {
    now = (typeof now === "number" && isFinite(now)) ? now : Date.now();
    var month = repMonthIndex(now);
    var pick = REP_EXCLUSIVES[((month % REP_EXCLUSIVES.length) + REP_EXCLUSIVES.length) % REP_EXCLUSIVES.length];
    var gateRep = REP_LADDER[REP_EXCLUSIVE_RANK][0];
    var rep = repLive(p || loadProfile(), now).rep;
    return {
      name: pick.name, rarity: pick.rarity, faction: pick.faction,
      cosmetic: true, cosmeticLabel: pick.cosmetic, power: false, gemGated: false,
      repNeeded: gateRep, rankNeeded: REP_LADDER[REP_EXCLUSIVE_RANK][1],
      rep: rep, unlocked: rep >= gateRep,
      month: month, resetInMs: repSeasonResetMs(now)
    };
  }

  global.AK_ECON = {
    RARITIES: RARITIES,
    CHEST_TIERS: CHEST_TIERS,
    CHEST_TABLE: CHEST_TABLE,
    SCRAP_DUPE: SCRAP_DUPE,
    DROP_W: DROP_W,
    LOOT_TABLE: LOOT_TABLE,   // AK-LOOT: the SHAKEDOWN phase-1 numbers (engine + index + shop read this)
    ensureShape: ensureShape,
    loadProfile: loadProfile,
    saveProfile: saveProfile,
    mutateProfile: mutateProfile,
    scrapTotal: scrapTotal,
    metaPerks: metaPerks,
    rollChestTier: rollChestTier,
    rollCardRarity: rollCardRarity,
    dupeScrapValue: dupeScrapValue,
    // AK-GARAGE: unified collection/garage upgrade economics
    UP_COPIES: UP_COPIES,
    UP_COINS: UP_COINS,
    CARD_LV_CAP: CARD_LV_CAP,
    cardLevel: cardLevel,
    townHallLevel: townHallLevel,     // AK-TOWNHALL: the meta-gate (caps card level)
    townHallCost: townHallCost,
    townHallPerks: townHallPerks,     // AK-THUX (#7): caps each TH level unlocks (card cap / crew / builders / grid)
    upgradeTownHall: upgradeTownHall,
    deckMaxLevel: deckMaxLevel,       // AK-STAKES: the deck card-level MAX gated by Town Hall (== TH level)
    raidDamage: raidDamage,           // AK-STAKES: lost-defense penalty -- drop TH -> deck de-levels (floor 1)
    // AK-AFTERMATH: persistent base damage + linear rebuild (visual aftermath + economy bite)
    REBUILD_HOURS: REBUILD_HOURS,     // full damage rebuilds to 0 in this many hours (6)
    applyBaseDamage: applyBaseDamage, // (idDamageMap{ id:0..1 }) -> atomic stamp of raid damage on the PLAYER base (lazy p.baseDmg)
    buildingDamage: buildingDamage,   // (p,id,now) -> CURRENT damage 0..1, decaying linearly to 0 over REBUILD_HOURS (pure)
    repairQuote: repairQuote, repairBuilding: repairBuilding,   // AK-REPAIR: pay gold to instantly fix raid damage
    fortifyQuote: fortifyQuote, fortifyBuilding: fortifyBuilding, buildingFortify: buildingFortify,   // AK-FORTIFY: wood+stone -> raid defense
    baseIntact: baseIntact,           // (p,now) -> overall repair state 0..1 (1 = pristine) across recorded buildings (pure)
    damageYieldMult: damageYieldMult, // (p,id,now) -> producer yield multiplier 1 - 0.5*damage (production.js reads this)
    cardCopies: cardCopies,
    upgradeNeed: upgradeNeed,
    levelUpCard: levelUpCard,
    addCopy: addCopy,            // AK-SHOPFIX: server-grant -> local-copy bridge
    healCopies: healCopies,      // AK-SHOPFIX: owned-without-copies heal pass
    grantChest: grantChest,
    addKeys: addKeys,
    addTrophies: addTrophies,     // AK-RANK: shared rank ladder (tower win + / raid loss -)
    rankDivision: rankDivision,
    addFragments: addFragments,   // AK-LOOT2: bank fragments + auto-forge keys (10 -> 1)
    addScrap: addScrap,
    // AK-MAT: wood/stone/metal sink + anti-runaway (capped grant + sell-to-gold)
    MATERIALS: MATERIALS,
    MAT_CAP: MAT_CAP,
    MAT_SELL: MAT_SELL,
    bankMaterial: bankMaterial,
    convertMaterial: convertMaterial,
    // === AK-ECON RATIO BACKBONE + PRODUCE + TRADING (design secs 2, 3.1, 5, 7) ===
    ANCHOR_GOLD_PER_LABOR_MIN: ANCHOR_GOLD_PER_LABOR_MIN,
    PRODUCE_GOLD: PRODUCE_GOLD,
    TOOL_TYPES: TOOL_TYPES,
    TOOL_TIERS: TOOL_TIERS,
    toolCost: toolCost,                 // (type,tier) -> tier spec (gold/produce/scrap/mats/durability/speed/timeMult/bonusLoot/rareDrop/unlockTH)
    toolFor: toolFor,                   // AK-TOOLS state: (p,type) -> equipped {tier,dur,owned,timeMult,bonusLoot,rareDrop,def} (absent => T0 Bare Paws)
    buyTool: buyTool,                   // (type,tier,payWith"gold"|"produce") -> atomic buy, TH-gated, refills+equips (refuses gems)
    equipTool: equipTool,               // (type,tier) -> swap to an owned tier
    spendDurability: spendDurability,   // (type,n) -> decrement; break => fall back to next-lower owned tier (never unusable)
    repairTool: repairTool,             // (type,payWith) -> refill durability (gold/produce; gems server-only)
    GEM_SKIP: GEM_SKIP,
    gemSkipCost: gemSkipCost,           // (seconds) -> gems to skip the timer (sec 7.3 CoC curve)
    builderCap: builderCap,             // (thLevel) -> 1..6 (sec 5.1 table -- TH-only design ceiling)
    builderCapNow: builderCapNow,       // (p?) -> live work-gate cap = TH cap + hired bonus slots (== effectiveBuilderCap)
    effectiveBuilderCap: effectiveBuilderCap, // AK-BONUSBLD: (p?) -> builderCap(TH) + (p.bonusBuilders|0)
    buyBuilderSlot: buyBuilderSlot,     // AK-BONUSBLD: () -> hire one permanent builder for GOLD (TH2+, cap 8, escalating 2000*N^1.6); gems NEVER buy builders
    builderSlotQuote: builderSlotQuote, // AK-BONUSBLD: (p?) -> { cost, locked, maxed, builders } for the buy button (no purchase)
    buildingBenefit: buildingBenefit,   // AK-BLDBENEFIT: (id, lv) -> { metric, curLabel, nextLabel, deltaLabel, blurb } -- what an upgrade actually buys (producers mirror production.js; GARAGE/FIXER mirror the applied mults)
    // === AK-THCAP: the Town Hall level cap (CoC rule) + the currency interlock ===
    BLD_MAX_LVL: BLD_MAX_LVL,           // 10 -- mirrors production.js MAX_LVL
    MAT_GATE_FROM: MAT_GATE_FROM,       // upgrades below this level are gold-only
    buildingCap: buildingCap,           // (p?) -> THE cap: the current Town Hall level, full stop
    buildingCapFor: buildingCapFor,     // (p?,id) -> effective per-building gate = max(cap, shipped baseline); grandfathers an existing base
    buildingBaseline: buildingBaseline, // (id) -> shipped default level (mirror of index.html LV)
    buildingLevel: bldLvl,              // (p,id) -> current level (p.prod[id].lvl, falling back to the baseline)
    buildingGoldCost: buildingGoldCost, // (id,curLvl) -> gold for the next level (producer curve vs generic hub curve)
    buildingMatCost: buildingMatCost,   // (id,curLvl) -> MATERIAL bill { wood,stone,metal?,scrap:{Common} } ({} below MAT_GATE_FROM)
    canUpgradeBuilding: canUpgradeBuilding,     // (id,curLvl?,p?) -> { ok, reason:'TH_CAP'|'MAX'|'BUSY'|'IS_TOWN_HALL'|null, msg, lvl, next, cap, th } PURE
    buildingUpgradeQuote: buildingUpgradeQuote, // (id,curLvl?,p?) -> gate + { gold, mats, haveGold, short[] } for the panel PURE
    upgradeBuilding: upgradeBuilding,           // (id,{timeMs?,curLvl?}) -> ATOMIC cap-enforced upgrade; timeMs>0 = timed+builder-gated, else instant
    pendingBuildingUpgrades: pendingBuildingUpgrades, // (p?,now?) -> count of landed-but-unapplied timed builds PURE (poll before writing)
    finishBuildingUpgrades: finishBuildingUpgrades,   // (now?) -> [{id,lvl,capped}] land finished builds; re-checks the cap so a fallen Hall pays no level
    garageLootMult: garageLootMult,     // AK-BLDBENEFIT: (p?) -> raid-loot multiplier 1+0.08*GARAGE lvl, clamped [1,2.5] (index.html raid calls this)
    fixerPayMult: fixerPayMult,         // AK-BLDBENEFIT: (p?) -> mission-payout multiplier 1+0.08*FIXER lvl, clamped [1,2.5] (missions.js calls this)
    // === AK-BLDWIRE 2026-07-18: the NINE buildings that charged gold and paid nothing ===
    // Every one is a pure function of building level off the SAME BUILDING_BENEFIT
    // numbers the panel shows. Signature matches garageLootMult: (p?) -> value.
    benefitPct: benefitPct,             // (id,lv) -> the shown percent for a pct building (per * lv, level-clamped) PURE
    benefitMult: benefitMult,           // (id,lv) -> 1 + shown%, clamped [1,2.5] PURE
    benefitSlots: benefitSlots,         // (id,lv) -> slot count for a slot building (base + 1 per `step` levels) PURE
    trophyRepMult: trophyRepMult,       // (p?) -> season Rep multiplier, +5%/TROPHY lvl. LIVE: applied inside addRep() on gains
    shopDiscount: shopDiscount,         // (p?) -> DROP discount FRACTION, 2%/lvl, capped 0.5
    shopPriceMult: shopPriceMult,       // (p?) -> price multiplier (1 - shopDiscount), floored 0.5
    shopPrice: shopPrice,               // (gold,p?) -> the gold a shop row should CHARGE and SHOW (whole gold; free stays free)
    clanShareMult: clanShareMult,       // (p?) -> crew loot share multiplier, +3%/CLAN lvl
    passXpMult: passXpMult,             // (p?) -> Alley Pass XP multiplier, +8%/PASS lvl
    codexRewardMult: codexRewardMult,   // (p?) -> Codex completion reward multiplier, +4%/ARCH lvl
    streetPayMult: streetPayMult,       // (p?) -> street-mode payout multiplier, +6%/STREET lvl
    arcadeRewardMult: arcadeRewardMult, // (p?) -> arcade reward multiplier, +5%/ARCADE lvl
    crewSlots: crewSlots,               // (p?) -> handler roster slots, 4 + 1 per 2 KENNEL lvls (4..8)
    dripSlots: dripSlots,               // (p?) -> cosmetic loadout slots, 2 + 1 per 2 WARD lvls (2..6)
    crewSlotsAtTH: crewSlotsAtTH,       // (th) -> the crew-slot CEILING a Town Hall level permits PURE (townHallPerks.crewSize reads this)
    dripSlotsAtTH: dripSlotsAtTH,       // (th) -> the drip-slot CEILING a Town Hall level permits PURE (townHallPerks.dripSlots reads this)
    buildersBusy: buildersBusy,         // AK-BUILDERCAP: (p?) -> builders in use across harvest dispatch (p.fieldJobs) + building upgrades (p.prod upUntil>now); ONE shared pool
    builderSpeed: builderSpeed,         // (cardLvl,thLevel) -> the skill<->time multiplier (sec 5.2)
    builderPerks: builderPerks,         // (card,thLevel) -> {speed,lootFloor,lootBonus,highGear,storeTier,cardLvl,th}
    townHallUnlocks: townHallUnlocks,   // (lv) -> {cardLvlCap,builders,crewSize,grid} for the #thpanel
    RARITY_LOOT_FLOOR: RARITY_LOOT_FLOOR,
    PRODUCE_TRADE: PRODUCE_TRADE,
    tradeRate: tradeRate,               // (from,to) -> units of `to` per 1 `from` (sec 7.4)
    sellMaterial: sellMaterial,         // (mat) -> gold-per-unit sell rate (sec 7.1)
    trade: trade,                       // (from,to,n) -> atomic conversion via mutateProfile
    tradeProduce: tradeProduce,         // (toKind,n) -> trade("produce",toKind,n)
    // === AK-FARM (Sunflower model): seeds + crops as items + deterministic weather ===
    CROPS: CROPS,                       // ONE source of truth for the crop ladder (buildmode reads this)
    CROP_WEATHER: CROP_WEATHER,
    weatherDay: weatherDay,             // (ms?) -> UTC day index
    gardenWeather: gardenWeather,       // (day?) -> {key,label,glyph,growMult,yieldMult,day} (deterministic by day)
    weatherMods: weatherMods,           // (key) -> {growMult,yieldMult}
    cropGrowMs: cropGrowMs,             // (key,weatherKey) -> weather-applied grow ms
    cropYield: cropYield,               // (key,weatherKey) -> weather-applied harvest count
    seedCount: seedCount,               // (p,key) -> owned seeds (falsy-default 0)
    cropCount: cropCount,               // (p,key) -> owned harvested crops (falsy-default 0)
    addSeed: addSeed,                   // (key,n) -> bank seed items (atomic)
    addCrop: addCrop,                   // (key,n) -> bank crop items (atomic)
    buySeed: buySeed,                   // (key,n,payWith"gold"|"produce") -> TH-gated atomic buy (refuses gems)
    cropValue: cropValue,               // AK-STAKES/Fence: gold-per-unit sell value of a crop (key or CROPS entry) -- CROPS tradeable for currency
    // === AK-BONES 2026-07-18 ONE WALLET: p.bones + p.handlers.bones read + spent as ONE balance ===
    bonesPockets: bonesPockets,         // (p?) -> { duty, handler, total } PURE; both underlying fields stay intact
    bonesTotal: bonesTotal,             // (p?) -> the ONE bones number (HUD should read this, not p.bones)
    canAffordBones: canAffordBones,     // (n,p?) -> boolean against the SUM of both pockets
    spendBones: spendBones,             // (n,{prefer:'duty'|'handler'}) -> atomic cross-pocket spend { ok,spent,from:{duty,handler},have,need }
    addBones: addBones,                 // (n,{into:'duty'|'handler'}) -> ONE grant front door (default = HUD-visible duty pocket)
    // === AK-STAMINA "Bones to Run" (CAPTIVATION P4): the reward-raid deadline ===
    STAM_MAX: STAM_MAX,
    STAM_CAP_HOURS: STAM_CAP_HOURS,
    STAM_BONES_REFILL: STAM_BONES_REFILL,
    raidStamina: raidStamina,           // (p?) -> live { cur,raw,max,full,regenMs,nextInMs,fullInMs } (PURE; absent state => full)
    staminaFull: staminaFull,           // (p?) -> boolean
    spendStamina: spendStamina,         // (n) -> atomic spend to launch a reward-raid (refuses if short)
    refillStamina: refillStamina,       // (payWith"bones") -> full; TIME or BONES only, NEVER gems (parity)
    // === AK-CRATES timed-unlock SLOTS (Clash-Royale chest deadline; claim rides openChest) ===
    CRATE_MAX_SLOTS: CRATE_MAX_SLOTS,
    CRATE_DURATION: CRATE_DURATION,     // per-class unlock seconds { Common..Mythic }
    crateSlots: crateSlots,             // (p?,now?) -> [ {id,tier,rarity,startAt,unlockAt,ready,remainMs} ] PURE (absent => [])
    enqueueCrate: enqueueCrate,         // (tier,rarity) -> {ok,slotId} | {ok:false,reason:'full'} (3-slot cap)
    claimCrate: claimCrate,             // (id,now?,opts?) -> openChest() result shape | null (not ready/missing)
    skipCrate: skipCrate,               // (id) -> {ok,cost} spend BONES to finish now | {ok:false,reason:'bones'|'notfound'}
    // === AK-FENCE floating price model (CAPTIVATION P6): the EVE/RuneScape "second game" ===
    PT_OFFSET_MS: PT_OFFSET_MS,
    ptDayIndex: ptDayIndex,             // (now?) -> LOCAL-PT day bucket (parity-safe fixed offset)
    ptPhase: ptPhase,                   // (now?) -> { key,hour,frac } LOCAL-PT day/night phase (night-market / dawn-bonus clock)
    fenceAnchor: fenceAnchor,           // (resource) -> base gold-per-unit (mirrors marketplace anchors)
    goldValue: goldValue,               // (resource,opts?) -> FLOATING Fence gold-per-unit (anchor + recent-fill median, +/-5%/day, floor/ceiling)
    recordFenceFill: recordFenceFill,   // (resource,price) -> bank a real sale into the recent-fill ring (lazily creates p.fence)
    // === AK-ECONMOD (CAPTIVATION P7+P8): chapter/season + weather + day/night world-signal multipliers ===
    econMod: econMod,                   // (opts?) -> { crop,fence,chapter,season,week,daysLeft,weather,phase,phaseFrac }
    sellCrop: sellCrop,                 // (key,n) -> sell crops for gold (c.sell each)
    useCrop: useCrop,                   // (key,n) -> convert crops to produce (value-neutral vs sell)
    sellSeed: sellSeed,                 // (key,n) -> sell spare seeds for gold (~50% of seed cost)
    // === AK-REP "Block Rep" (CAPTIVATION P10): PvP-only canon ladder + monthly soft reset + seasonal exclusive ===
    REP_LADDER: REP_LADDER,             // [[rep,name]...] Stray -> ... -> King of the Block (canon ranks)
    repRankIndex: repRankIndex,         // (rep) -> ladder index 0..6
    repMonthIndex: repMonthIndex,       // (now?) -> LOCAL-PT month bucket (year*12+month; rolls at PT midnight on the 1st)
    repSeasonResetMs: repSeasonResetMs, // (now?) -> ms until the next monthly soft reset (HUD countdown)
    blockRep: blockRep,                 // (p?) -> current-season Block Rep; pass a profile for a 60fps PURE read, no-arg COMMITS the fold/reset
    repRank: repRank,                   // (p?) -> { rep,rank,index,floor,next,nextAt,toNext,progress,protected,atTop,month,resetInMs }
    addRep: addRep,                     // (n) -> atomic win(+)/loss(-) award with Apex demotion protection (Stray/Pup/Runner shielded)
    syncRep: syncRep,                   // () -> fold the PvP trophy-delta + monthly reset into persisted Rep (the no-game.html-edit hook)
    seasonalExclusive: seasonalExclusive, // (now?,p?) -> the month's rotating high-rarity COSMETIC unlock target (Rep-gated, never power, never gems)
    // === AK-LOOTMATH 2026-07-18: raid loot as FOUR POOLS, not one flat percentage ===
    // AUTHORITATIVE over raidparams.maxLootPercent / raidparams.lootCeiling (both
    // unreferenced repo-wide). See the AK-LOOTMATH header for the full reconciliation.
    LOOT_STORAGE_RATE: LOOT_STORAGE_RATE,   // defenderTH -> lootable share of the bank (0.50 @TH1 FALLING to 0.10 @TH18)
    LOOT_CAP: LOOT_CAP,                     // defenderTH -> absolute gold-equivalent ceiling (250 @TH1 RISING to 25000 @TH18)
    LOOT_PENALTY_LADDER: LOOT_PENALTY_LADDER,
    lootTH: lootTH,                         // (th) -> clamped 1..18 PURE
    lootStorageRate: lootStorageRate,       // (defenderTH) -> storage share PURE
    lootCap: lootCap,                       // (defenderTH) -> per-pool absolute cap PURE
    lootScrapValue: lootScrapValue,         // (rarityBag) -> gold-equivalent via SCRAP_DUPE PURE
    lootRarityBonus: lootRarityBonus,       // (defProfile) -> raidparams lootBonus 0.00..0.50 (0 headless) PURE
    lootCollectorPending: lootCollectorPending, // (defProfile,now?) -> {gold,scrap,value} uncollected producer yield PURE
    lootPoolsFor: lootPoolsFor,             // (defProfile,now?) -> {storage,collector,treasury,townHall,total,...} PURE
    lootPenalty: lootPenalty,               // (attackerTH,defenderTH) -> multiplier 1.00/0.80/0.50/0.25/0.05 PURE
    resolveLoot: resolveLoot,               // (defProfile,attackerTH,destructionPct,townHallDestroyed,opts?) -> final award PURE (computes, never banks)
    buyCardWithScrap: buyCardWithScrap,
    openChest: openChest
  };
})(typeof window !== "undefined" ? window : globalThis);
