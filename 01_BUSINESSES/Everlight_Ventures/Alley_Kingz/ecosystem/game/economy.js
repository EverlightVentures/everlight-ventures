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
    upgradeTownHall: upgradeTownHall,
    cardCopies: cardCopies,
    upgradeNeed: upgradeNeed,
    levelUpCard: levelUpCard,
    addCopy: addCopy,            // AK-SHOPFIX: server-grant -> local-copy bridge
    healCopies: healCopies,      // AK-SHOPFIX: owned-without-copies heal pass
    grantChest: grantChest,
    addKeys: addKeys,
    addFragments: addFragments,   // AK-LOOT2: bank fragments + auto-forge keys (10 -> 1)
    addScrap: addScrap,
    buyCardWithScrap: buyCardWithScrap,
    openChest: openChest
  };
})(typeof window !== "undefined" ? window : globalThis);
