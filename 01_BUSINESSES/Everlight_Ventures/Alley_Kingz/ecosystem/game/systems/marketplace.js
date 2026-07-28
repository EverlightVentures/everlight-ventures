/* game/systems/marketplace.js -- AK_SYSTEMS module (CROWN CLIMB phase 7: Sunflower MARKETPLACE).
   ==========================================================================
   ALLEY KINGZ // THE BAZAAR -- keeper "Quill the Quartermaster" in THE DOCKS
   A Sunflower-Land-style player RESOURCE EXCHANGE, SEPARATE from the story shop
   and SEPARATE from the card barter post (systems/trading.js / "Switch"). Here
   you LIST / BUY / SELL the SOFT raw economy -- wood / stone / metal / scrap /
   produce / gold -- against other players. Server-authoritative via the SAME
   ak-trading edge fn + ak_trade_listings table (invoked exactly like social.js /
   trading.js), with a CLEAN local market book + NPC liquidity fallback so the
   bazaar is fully playable offline / signed out.

   HARD LAW honored here (every line):
   - SOFT resources ONLY (wood/stone/metal/scrap/produce/gold). NO gems (server-
     only, cosmetic/skip/pay -- NEVER power/loot), NO cards (that is the barter
     post), NO $BCARDD / ALK. Gems + cards are hard-rejected on BOTH legs.
   - engine.js is FROZEN. This module never touches it -- it layers via AK_CTX
     (overlay/world/currency) + AK_ECON only.
   - ONE economy = AK_ECON. Every player-side balance read/write goes through
     AK_ECON.mutateProfile / addScrap / bankMaterial (falsy-default on write).
     We add NO new ak_profile field -- the local market book lives in a SEPARATE
     localStorage key ("ak_market"), so the profile zero-state stays byte-identical.
   - Server-authoritative trades when reachable; clean local fallback otherwise.
     Resource legs forward-compat the ak-trading server (which is card-only today):
     a resource post that the server rejects degrades to a local book entry, and
     the board self-fills fair asks via a lightweight market maker.
   - 60fps hub: lazy DOM (built on open, removed on close), no per-frame heavy
     work (the market maker runs only on open / board render / a gentle interval
     while the panel is open, cleared on close).

   Theme: gritty gold cyberpunk dog-gang street culture. XSS-safe by construction
   (mk() builder -> textContent only, no innerHTML). No em-dashes (use --). No
   bundler. Plain browser JS (no TS).
   ========================================================================== */
(function (global) {
  "use strict";
  if (!global.AK_SYSTEMS) return;                 // hub-only module; bail where the registry is absent

  // ----------------------------------------------------------------------- //
  //  CONSTANTS (gates + economy knobs)                                       //
  // ----------------------------------------------------------------------- //
  var MARKET_FN  = "ak-trading";                  // SAME edge fn + ak_trade_listings table as trading.js
  var HOME_ZONE  = "THE_DOCKS";                   // the quartermaster works the trade docks (resource bazaar)
  var MIN_TH     = 2;                             // Town Hall gate (anti-fresh-account abuse; lower than the card post)
  var DAILY_CAP  = 8;                             // posts + accepts per local day (anti-spam; server enforces its own 24h cap)
  var BAND_SIZE  = 400;                           // trophy-band width -- you trade with your own bracket
  var COOLDOWN_MS = 4000;                         // anti-spam cooldown between bazaar actions
  var TRIGGER_R  = 72;                            // walk this close to Quill -> the bazaar opens
  var KEEPER_SPD = 56;                            // patrol px/s
  var NPC_SPREAD = 0.18;                          // the market maker's buy/sell spread around fair value (the natural sink)
  var MAKER_FILL_RATIO = 1.05;                    // a resting SELL fills if you ask <= 105% of what you give is worth
  var MARKET_TAX_PCT = 0.05;                      // gold-equivalent skim on a FILLED sale's proceeds (a pure sink)
  var SEED_TTL_MS = 90000;                        // NPC liquidity rotates every ~90s
  // AK-MKT 2026-07-18: listing lifecycle. DAILY_CAP throttles the RATE of actions; these two
  // bound the STANDING board -- how many offers one dog may rest at once, and how long a
  // resting offer sits before the docks hand the goods back.
  var ACTIVE_CAP    = 5;                          // max simultaneously-open local offers
  var LISTING_TTL_MS = 24 * 3600000;              // a resting offer expires after 24h (deposit refunded)

  // --- THE FENCE LAUNDER (raided / stolen goods don't spend until washed) --- //
  var LAUNDER_CUT_PCT = 0.20;                     // the Fence's cut to wash hot goods clean (a sink + the gritty tax)
  var RUSH_CUT_PCT    = 0.40;                     // skip the wait -- a fatter cut to move it right now
  var LAUNDER_BASE_MS = 120000;                   // base wash time (the delay before hot goods spend clean)
  var LAUNDER_STEP_MS = 30000;                    // +30s per 100g of value (big hauls move slow + quiet)
  var LAUNDER_MAX_MS  = 900000;                   // cap the wash at 15 min
  var HOT_CAP         = 40;                        // max distinct hot piles (anti-bloat)

  var RES_KINDS = ["gold", "produce", "wood", "stone", "metal", "scrap"]; // the tradable soft economy
  var SCRAP_RARITIES = ["Common", "Rare", "Epic", "Legendary"];           // Mythic scrap is NEVER tradeable
  var MATERIAL_KINDS = ["wood", "stone", "metal"];

  // glyphs MIRROR index.html TRADE_ICO so the bazaar reads like the rest of the HUD.
  var ICO = {
    gold: "\u{1FA99}", produce: "\u{1F33F}", wood: "\u{1FAB5}", stone: "\u{1FAA8}",
    metal: "\u{1F529}", scrap: "⚙️"
  };
  // bounded amount presets per kind (no abusive numbers; the server also clamps).
  var AMT_OPTS = {
    gold:    [50, 100, 250, 500, 1000],
    produce: [10, 25, 50, 100, 200],
    wood:    [10, 25, 50, 100, 200],
    stone:   [10, 25, 50, 100, 200],
    metal:   [5, 10, 25, 50, 100],
    scrap:   [5, 10, 25, 50]
  };
  // flavor for the NPC liquidity (street vendors working the docks).
  var VENDOR_NAMES = ["Scrapyard Sal", "Dockside Reo", "Old Marrow", "Tin Whistle", "Greasepaw Min", "Hauler Bex", "Coil the Fence", "Pitbull Pawn"];
  var KEEPER_LINES = [
    "Quill the Quartermaster. Raw goods only -- wood, stone, metal, scrap, produce, coin. No crypto, no cards.",
    "Sell your overflow before it rots. The docks always need stone.",
    "Fair price or it sits. The board don't lie, mutt.",
    "Buy low off the haulers, sell high to the builders. That's the dock game.",
    "No gems at my table. Soft goods keep the bazaar free.",
    "Got spare metal? The riggers pay a premium this week.",
    "Something hot off a raid? Bring it to the WASH bench -- my cut, then it spends clean.",
    "Boneyard got hit again -- they're paying over market for wood. Check the ORDERS board.",
    "Prices float, mutt. What's dear today is cheap next week. Read the tape."
  ];

  // ----------------------------------------------------------------------- //
  //  P6 FLOATING FENCE TICKER + P8 RAID-FED BUY-ORDER SINK (CAPTIVATION_PLAN)//
  //  P6: every price floats via AK_ECON.goldValue (recent-fill median + daily //
  //  wander, +/-5%/day cap, floor/ceiling) -- the EVE/RuneScape "second game"//
  //  stock ticker. P8: a raided / damaged DISTRICT screams for the fortify    //
  //  mats it lost (wood/stone/scrap). That demand SPIKES those prices (the    //
  //  tape turns green + 🔥) AND posts BUY-ORDERS the harvester sells into at  //
  //  a premium. Each filled order records a high fill, so the float stays     //
  //  dear for days = the self-feeding loop (raids destroy -> demand -> price  //
  //  up -> harvesters profit). Deterministic by LOCAL-PT day; no client RNG.  //
  // ----------------------------------------------------------------------- //
  var TICKER_KINDS = [
    { kind: "produce" }, { kind: "wood" }, { kind: "stone" }, { kind: "metal" },
    { kind: "scrap", rarity: "Common" }, { kind: "scrap", rarity: "Rare" }
  ];
  var DEMAND_MAT_KINDS = ["wood", "stone", "scrap"];   // the fortify mats a gutted block needs back (CORE_LOOP_CANON: trees/stone fortify; scrap rebuilds)
  var DEMAND_REF       = 240;     // outstanding units that map to the full demand bump
  var DEMAND_GAIN      = 0.30;    // +30% price at DEMAND_REF outstanding units...
  var DEMAND_MAX_MULT  = 1.30;    // ...capped at +30% over fair (a LOCAL spike on top of the parity quote)
  var BO_PREM_MIN      = 0.10;    // a buy-order always pays at least +10% over fair (the harvester's cut)
  var BO_PREM_MAX      = 0.45;    // a freshly-gutted block pays up to +45% over fair
  var BUYORDER_TTL_MS  = 6 * 3600000;   // a raid-fed order stands ~6h then the block gives up
  var BUYORDER_CAP     = 24;      // max live raid-fed orders (anti-bloat)
  var DISTRICTS_HIT_PER_DAY = 3;  // how many of the 9 blocks post distress demand each PT-day (the offline AI-chaos / Crown Bloodline turf churn)
  // the 9 canon districts (ids + names mirror index.html ZONES; CTX.ZONES wins at runtime).
  var DISTRICTS = [
    { id: "THE_OVERLOOK",  name: "THE OVERLOOK" },
    { id: "DOWNTOWN",      name: "DOWNTOWN" },
    { id: "NEON_HEIGHTS",  name: "NEON HEIGHTS" },
    { id: "THE_YARDS",     name: "THE YARDS" },
    { id: "HOME_TURF",     name: "THE LOT" },
    { id: "FACTORY_ROW",   name: "FACTORY ROW" },
    { id: "THE_UNDERCITY", name: "THE UNDERCITY" },
    { id: "THE_STRIP",     name: "THE STRIP" },
    { id: "THE_DOCKS",     name: "THE DOCKS" }
  ];

  // ----------------------------------------------------------------------- //
  //  STATE                                                                   //
  // ----------------------------------------------------------------------- //
  var CTX = null;
  var S = {
    seeded: false, uiOpen: false, entryLock: false,
    ovApi: null, root: null, bodyEl: null, toastEl: null,
    tab: "board", makerTimer: 0,
    cat: "all", sort: "deal", sweepT: 0,     // AK-MKT 2026-07-18: board browse state (category tab + sort order) + hub-tick expiry sweep accumulator
    npc: [], npcAt: 0,
    dist: [], distDay: -1, tickerEl: null,   // P6/P8: seeded district demand cache + the live ticker tape element
    keeper: null, wp: 0,
    waypoints: [ { x: 360, y: 360 }, { x: 1320, y: 360 }, { x: 1320, y: 940 }, { x: 360, y: 940 } ]
  };
  // session-only tracker: bot listing IDs the player already bought this session.
  // IDs encode the hourBucket ("bot_{idx}_{bucket}") so they auto-differ next hour.
  var _boughtBotIds = {};

  // ----------------------------------------------------------------------- //
  //  HELPERS -- identity + server (mirrors trading.js / social.js)           //
  // ----------------------------------------------------------------------- //
  function econ() { try { return global.AK_ECON || (CTX && CTX.econ) || null; } catch (_) { return null; } }
  function prof() { var e = econ(); return e ? e.loadProfile() : null; }
  function sbc()  { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me()   { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function myId() { var u = me(); return (u && u.id) || null; }
  function myName(){ try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24); } catch (_) { return "Stray"; } }
  function online() { return !!(me() && sbc()); }

  // edge-fn call (functions.invoke; auto-attaches JWT). Degrades to {ok:false} offline. (identical to trading.js)
  function call(fn, body) {
    var sb = sbc();
    if (!sb) return Promise.resolve({ ok: false, error: "offline" });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var c = r.error && r.error.context;
        if (c && typeof c.json === "function") return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: (r.error && r.error.message) || "error" };
      }
      return r.data || { ok: false, error: "empty" };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }

  // ----------------------------------------------------------------------- //
  //  ECONOMY (player side) -- soft resources via AK_ECON only                //
  //  balanceOf / affordable / deduct / credit mirror trading.js's escrow     //
  //  but for the resource economy. credit() routes materials through the     //
  //  AK_ECON capped grant (bankMaterial) so a refund/payout can never bust   //
  //  the anti-runaway material cap.                                          //
  // ----------------------------------------------------------------------- //
  function K(o, d) { return o == null ? d : o; }
  function isMaterial(k) { return MATERIAL_KINDS.indexOf(k) >= 0; }
  function ecScrapDupe() { var e = econ(); return (e && e.SCRAP_DUPE) || { Common: 5, Rare: 15, Epic: 40, Legendary: 100, Mythic: 250 }; }
  function ecMatSell() { var e = econ(); return (e && e.MAT_SELL) || { wood: 2, stone: 3, metal: 5 }; }
  function ecProduceGold() { var e = econ(); return (e && typeof e.PRODUCE_GOLD === "number") ? e.PRODUCE_GOLD : 1.0; }

  function balanceOf(item) {
    var p = prof(); if (!p || !item) return 0;
    if (item.kind === "gold") return Math.max(0, p.coins | 0);
    if (item.kind === "produce") return Math.max(0, p.produce | 0);
    if (isMaterial(item.kind)) return Math.max(0, p[item.kind] | 0);
    if (item.kind === "scrap") return Math.max(0, (p.scrap && p.scrap[item.rarity]) | 0);
    return 0;
  }
  function affordable(item) { return balanceOf(item) >= (item.amount | 0); }
  function deduct(item) {
    var e = econ(); if (!e) return; var a = item.amount | 0;
    if (item.kind === "gold") e.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins | 0) - a); });
    else if (item.kind === "produce") e.mutateProfile(function (p) { p.produce = Math.max(0, (p.produce | 0) - a); });
    else if (isMaterial(item.kind)) e.mutateProfile(function (p) { p[item.kind] = Math.max(0, (p[item.kind] | 0) - a); });
    else if (item.kind === "scrap") e.addScrap(item.rarity, -a);
  }
  function credit(item) {
    var e = econ(); if (!e) return; var a = item.amount | 0;
    if (item.kind === "gold") e.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins | 0) + a); });
    else if (item.kind === "produce") e.mutateProfile(function (p) { p.produce = Math.max(0, (p.produce | 0) + a); });
    else if (isMaterial(item.kind)) { if (e.bankMaterial) e.bankMaterial(item.kind, a); else e.mutateProfile(function (p) { p[item.kind] = Math.max(0, (p[item.kind] | 0) + a); }); }
    else if (item.kind === "scrap") e.addScrap(item.rarity, a);
  }
  // apply a single server grant to the LOCAL economy (resource-aware mirror of trading.js applyGrant).
  function applyGrant(g) {
    var e = econ(); if (!e || !g) return false;
    try {
      if (g.kind === "gold" || g.kind === "coins") e.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins || 0) + (g.amount || 0)); });
      else if (g.kind === "produce") e.mutateProfile(function (p) { p.produce = Math.max(0, (p.produce || 0) + (g.amount || 0)); });
      else if (isMaterial(g.kind)) { if (e.bankMaterial) e.bankMaterial(g.kind, g.amount || 0); else e.mutateProfile(function (p) { p[g.kind] = Math.max(0, (p[g.kind] || 0) + (g.amount || 0)); }); }
      else if (g.kind === "scrap" && g.rarity) e.addScrap(g.rarity, g.amount || 0);
      else if (g.kind === "card" && g.card_id) e.addCopy(g.card_id, g.amount || 1);  // forward-compat (the bazaar never grants cards)
      else if (g.kind === "keys") e.addKeys(g.amount || 0);
      else return false;
      return true;
    } catch (_) { return false; }
  }
  function applyGrants(arr) { var n = 0; (arr || []).forEach(function (g) { if (applyGrant(g)) n++; }); if (n) pushNow(); return n; }
  function pushNow() { try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {} }
  // pull any queued payouts (a sold offer's proceeds land here next session).
  function claimGrants() {
    if (!online()) return Promise.resolve(0);
    return call(MARKET_FN, { action: "claim-grants" }).then(function (r) {
      if (!r || !r.ok || !r.grants || !r.grants.length) return 0;
      // only apply RESOURCE grants here (cards belong to the barter post; this avoids double-claiming a card inbox).
      var res = r.grants.filter(function (g) { return g && RES_KINDS.indexOf(g.kind) >= 0; });
      var n = applyGrants(res);
      if (n) toast("Claimed market payouts.");
      return n;
    });
  }

  // ======================================================================= //
  //  P6 PRICING -- FLOATING FENCE QUOTE (AK_ECON.goldValue, degrade -> flat) //
  //  Every bazaar price flows through unitPrice(): the parity-safe floating   //
  //  base from AK_ECON.goldValue (recent-fill median + daily wander), times   //
  //  the world-signal overlay (econMod.fence: chapter/weather/day-night,      //
  //  P7+P8), times the LOCAL raid-demand spike (P8). Gold is the numeraire -- //
  //  always exactly 1. Older economy.js (no goldValue) degrades to the flat   //
  //  anchors this module always used. No client RNG -> parity-safe.           //
  // ======================================================================= //
  // a profile snapshot for the recent-fill ledger (load-light: refreshed >=1s; a fill clears it).
  var _pf = null, _pfAt = 0;
  function pSnap() { var n = Date.now(); if (!_pf || (n - _pfAt) > 1000) { _pf = prof(); _pfAt = n; } return _pf; }
  // parity-safe FLOATING base gold-per-unit via AK_ECON (degrades to flat anchors).
  function baseUnit(kind, rarity, dayOpt) {
    if (kind === "gold") return 1;
    var e = econ();
    if (e && typeof e.goldValue === "function") {
      try {
        var res = (kind === "scrap") ? { kind: "scrap", rarity: rarity || "Common" } : { kind: kind };
        var o = { p: pSnap() }; if (dayOpt != null) o.day = dayOpt;
        var u = e.goldValue(res, o);
        if (u > 0) return u;
      } catch (_) {}
    }
    if (kind === "produce") return ecProduceGold();           // flat fallback (older economy.js)
    if (isMaterial(kind)) return (ecMatSell()[kind] || 1);
    if (kind === "scrap") return (ecScrapDupe()[rarity] || 5);
    return 0;
  }
  // the world-event price overlay (chapter/season + weather + day/night). P7+P8.
  function econFenceMult() { var e = econ(); try { if (e && typeof e.econMod === "function") { var m = e.econMod(); if (m && isFinite(m.fence)) return m.fence; } } catch (_) {} return 1; }
  // LOCAL raid-demand spike: outstanding buy-order volume for a fortify mat lifts
  // its price (bounded). This is the visible "raids -> demand -> prices rise" cue.
  function demandMult(kind, rarity) {
    if (DEMAND_MAT_KINDS.indexOf(kind) < 0) return 1;
    var rem = outstandingDemand(kind, rarity);
    if (rem <= 0) return 1;
    return Math.min(DEMAND_MAX_MULT, 1 + DEMAND_GAIN * (rem / DEMAND_REF));
  }
  // the live per-unit Fence quote everywhere (board, valuations, fills, ticker).
  function unitPrice(kind, rarity) {
    if (kind === "gold") return 1;
    return baseUnit(kind, rarity) * econFenceMult() * demandMult(kind, rarity);
  }
  // fair GOLD value of any resource item -- the common denominator for pricing.
  function goldValue(it) {
    if (!it) return 0;
    var a = Math.max(0, it.amount | 0);
    if (it.kind === "gold") return a;
    return a * unitPrice(it.kind, it.rarity);
  }
  // record a real transacted unit price so the floating median responds to sales
  // (the self-feeding signal). Degrades to a no-op if AK_ECON lacks the ring.
  function recordFill(kind, rarity, unit) {
    var e = econ(); if (!e || typeof e.recordFenceFill !== "function") return;
    if (kind === "gold" || !(unit > 0)) return;
    try { e.recordFenceFill((kind === "scrap") ? { kind: "scrap", rarity: rarity || "Common" } : { kind: kind }, unit); _pf = null; } catch (_) {}
  }

  // ----------------------------------------------------------------------- //
  //  AK-MKT 2026-07-18: PRICE HISTORY (read-only view of the fill ring)      //
  //  economy.js ALREADY banks every transacted unit price in a rolling ring  //
  //  at p.fence.fills[key] (recordFenceFill, capped at 12 -- the median      //
  //  window that floats goldValue). Nothing exposed avg/min/max off it, so   //
  //  no surface could draw a tape. This reads that SAME ring -- it never     //
  //  writes and never keeps a second copy, so there is exactly one history.  //
  //  _resKey mirrors economy.js's private key derivation ("scrap:<rarity>"   //
  //  or "<kind>"); keep the two in step if that ever changes.                //
  // ----------------------------------------------------------------------- //
  function fillKey(kind, rarity) { return (kind === "scrap") ? ("scrap:" + (rarity || "Common")) : String(kind || ""); }
  function fillRing(kind, rarity) {
    try {
      // prof() not pSnap(): pSnap is the 60fps ticker cache and is only invalidated by OUR
      // recordFill, so a fill banked by any other system (or economy.js directly) reads stale
      // for up to a second. History is a panel-open / graph-draw path, so it reads live.
      var p = prof(); if (!p || !p.fence || !p.fence.fills) return [];
      var r = p.fence.fills[fillKey(kind, rarity)];
      return Array.isArray(r) ? r.filter(function (v) { return isFinite(v) && v > 0; }) : [];
    } catch (_) { return []; }
  }
  // priceHistory(kind, rarity?) -> the rolling window plus the stats a graph needs.
  // `series` is oldest-first (ring push order), so it plots left-to-right as-is.
  // n===0 means "no sales banked yet" -- callers should show `now` (the live quote) alone
  // rather than a flat line at zero.
  function priceHistory(kind, rarity) {
    var s = fillRing(kind, rarity), now = unitPrice(kind, rarity);
    if (!s.length) return { kind: kind, rarity: rarity, n: 0, series: [], avg: now, min: now, max: now, last: now, now: now, cap: 12 };
    var sum = 0, mn = s[0], mx = s[0];
    for (var i = 0; i < s.length; i++) { sum += s[i]; if (s[i] < mn) mn = s[i]; if (s[i] > mx) mx = s[i]; }
    function r2(v) { return Math.round(v * 100) / 100; }
    return { kind: kind, rarity: rarity, n: s.length, series: s.slice(),
             avg: r2(sum / s.length), min: r2(mn), max: r2(mx), last: r2(s[s.length - 1]), now: now, cap: 12 };
  }

  // ----------------------------------------------------------------------- //
  //  AK-MKT 2026-07-18: CATEGORY TAXONOMY -- borrowed from the BACKPACK      //
  //  backpack.js owns the item registry the player already reads (ITEMS[].cat//
  //  over MATERIALS / CURRENCY / GEAR / CARDS). The bazaar used to sort its   //
  //  goods into nothing at all; inventing a second taxonomy here would mean   //
  //  the same wood sitting under two different headings in two screens. So    //
  //  this DEFERS to AK_BACKPACK at CALL time (backpack.js loads AFTER this    //
  //  file in index.html, so a load-time read would be undefined) and falls    //
  //  back to a mirror of its cats when the bag module is absent (headless).   //
  // ----------------------------------------------------------------------- //
  var CAT_FALLBACK = { gold: "currency", produce: "materials", wood: "materials",
                       stone: "materials", metal: "materials", scrap: "materials" };
  function bp() { try { return global.AK_BACKPACK || null; } catch (_) { return null; } }
  // kind -> backpack category id. Resource kinds map 1:1 onto the bag's own ids.
  function catOf(kind) {
    var b = bp();
    try { if (b && typeof b.def === "function") { var d = b.def(kind); if (d && d.cat) return d.cat; } } catch (_) {}
    return CAT_FALLBACK[kind] || "materials";
  }
  // the category tabs the board offers: ALL + only those the bazaar actually trades,
  // in the bag's own declared order so the two screens read identically.
  function marketCats() {
    var b = bp(), live = {}, out = [ { id: "all", label: "ALL" } ];
    RES_KINDS.forEach(function (k) { live[catOf(k)] = 1; });
    var src = (b && Array.isArray(b.CATS) && b.CATS.length) ? b.CATS
            : [ { id: "materials", label: "MATERIALS" }, { id: "currency", label: "CURRENCY" } ];
    src.forEach(function (c) { if (c && live[c.id]) out.push({ id: c.id, label: c.label }); });
    return out;
  }
  // a listing belongs to a category if EITHER leg does (you browse by what is on offer
  // as much as by what is being asked for).
  function listingInCat(L, cat) {
    if (!cat || cat === "all") return true;
    if (!L || !L.give || !L.want) return false;
    return catOf(L.give.kind) === cat || catOf(L.want.kind) === cat;
  }

  // ----------------------------------------------------------------------- //
  //  AK-MKT 2026-07-18: BOARD SORTS -- every comparator is pure + total      //
  //  "value" ranks by what the GIVE leg is worth; "deal" ranks by how much   //
  //  give-value you get per unit of want-value (the actual bargain metric).  //
  // ----------------------------------------------------------------------- //
  var SORTS = [
    { id: "deal",   label: "BEST DEAL" },
    { id: "value",  label: "BIGGEST" },
    { id: "cheap",  label: "CHEAPEST" },
    { id: "kind",   label: "BY GOOD" }
  ];
  function dealScore(L) { var w = goldValue(L.want); return w > 0 ? (goldValue(L.give) / w) : 0; }
  function sortListings(rows, id) {
    var a = (rows || []).slice();
    if (id === "value") a.sort(function (x, y) { return goldValue(y.give) - goldValue(x.give); });
    else if (id === "cheap") a.sort(function (x, y) { return goldValue(x.want) - goldValue(y.want); });
    else if (id === "kind") a.sort(function (x, y) { return String(x.give && x.give.kind).localeCompare(String(y.give && y.give.kind)); });
    else a.sort(function (x, y) { return dealScore(y) - dealScore(x); });
    return a;
  }

  // ======================================================================= //
  //  P8 BUY-ORDER BOOK -- raid-fed demand sink                                //
  //  REAL raid-fed orders persist in the SAME ak_market book (b.buyOrders --  //
  //  a SEPARATE LS key; profile zero-state stays byte-identical). SEEDED      //
  //  district-distress orders are deterministic by LOCAL-PT day (the offline  //
  //  turf churn) and live in memory only. Raid/world systems feed real demand //
  //  via window.AKFence.postRaidDemand(district, needs?, severity?).          //
  // ======================================================================= //
  function ptDay() { var e = econ(); try { if (e && typeof e.ptDayIndex === "function") return e.ptDayIndex(); } catch (_) {} return Math.floor((Date.now() - 8 * 3600000) / 86400000); }
  function hash32(s) { s = String(s == null ? "" : s); var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; }
  function dNameById(id) {
    try { var z = CTX && CTX.ZONES && CTX.ZONES[id]; if (z && (z.name || z.label)) return z.name || z.label; } catch (_) {}
    for (var i = 0; i < DISTRICTS.length; i++) if (DISTRICTS[i].id === id) return DISTRICTS[i].name;
    return id || "a rival block";
  }
  function newBoId() { return "bo_" + Date.now().toString(36) + "_" + Math.floor(Math.random() * 1296).toString(36); }
  function boRemaining(o) { return Math.max(0, (o.qty | 0) - (o.filled | 0)); }
  // build one buy-order. unit = floating fair (incl world overlay, EXCL demand --
  // the order's own premium IS its demand) times a distress premium by severity.
  function makeBuyOrder(id, distId, kind, rarity, qty, severity, src) {
    var prem = BO_PREM_MIN + (BO_PREM_MAX - BO_PREM_MIN) * Math.max(0, Math.min(1, severity || 0));
    var unit = Math.max(1, Math.ceil(baseUnit(kind, rarity) * econFenceMult() * (1 + prem)));
    return { id: id, district: distId, districtName: dNameById(distId), kind: kind, rarity: (kind === "scrap") ? (rarity || "Common") : undefined, qty: Math.max(1, qty | 0), filled: 0, unit: unit, prem: prem, src: src || "raid", t: Date.now(), expiresAt: Date.now() + BUYORDER_TTL_MS };
  }
  // deterministic per-PT-day district distress (the offline turf-churn signal so
  // the ORDERS board + ticker are alive even before a real raid lands).
  function seededDistrictOrders() {
    var day = ptDay();
    if (S.dist.length && S.distDay === day) return S.dist;
    var out = [];
    for (var i = 0; i < DISTRICTS.length; i++) {
      var d = DISTRICTS[i], hv = hash32(d.id + "|" + day);
      if ((hv % 9) >= DISTRICTS_HIT_PER_DAY) continue;            // ~DISTRICTS_HIT_PER_DAY of 9 are raided today
      var kind = DEMAND_MAT_KINDS[(hv >>> 4) % DEMAND_MAT_KINDS.length];   // >>> (unsigned) -- a signed >> goes negative for high-bit hashes
      var rarity = (kind === "scrap") ? pick(["Common", "Rare"], hv >>> 8) : undefined;
      var sev = 0.35 + ((hv >>> 12) % 50) / 100;                  // 0.35..0.84 deterministic severity
      var qty = (kind === "scrap") ? (10 + (hv >>> 16) % 30) : (40 + (hv >>> 16) % 120);
      var o = makeBuyOrder("seed_" + d.id + "_" + day, d.id, kind, rarity, qty, sev, "district");
      o.expiresAt = 0;                                            // seeded validity tracked by the day cache, not a TTL
      o._src = "seed";
      out.push(o);
    }
    S.dist = out; S.distDay = day;
    return S.dist;
  }
  function pruneBuyOrders(b) { var now = Date.now(); b.buyOrders = (b.buyOrders || []).filter(function (o) { return o && boRemaining(o) > 0 && (!o.expiresAt || o.expiresAt > now); }); }
  // ALL open buy-orders: seeded (in-memory, stable refs) + real raid-fed (LS).
  function openBuyOrders() {
    var now = Date.now();
    var real = (loadBook().buyOrders || []).filter(function (o) { return o && boRemaining(o) > 0 && (!o.expiresAt || o.expiresAt > now); });
    real.forEach(function (o) { o._src = "loc"; });
    return seededDistrictOrders().concat(real);
  }
  function outstandingDemand(kind, rarity) {
    var rem = 0;
    openBuyOrders().forEach(function (o) {
      if (o.kind !== kind) return;
      if (kind === "scrap" && (o.rarity || "Common") !== (rarity || "Common")) return;
      rem += boRemaining(o);
    });
    return rem;
  }
  function findOrder(id) { var a = openBuyOrders(); for (var i = 0; i < a.length; i++) if (a[i].id === id) return a[i]; return null; }

  // PUBLIC (raid-fed): a raided/damaged district posts demand for its lost mats.
  //   district : a zone id string, or { id, name }
  //   needs    : a {kind,rarity?,qty} | array of them; OR a number = severity (auto-derive wood+stone[+scrap])
  //   severity : 0..1 (how hard it got hit -> the premium it'll pay). Default 0.6.
  function postRaidDemand(district, needs, severity) {
    var distId = (district && typeof district === "object") ? (district.id || district.zone || "") : String(district || "");
    var sev, list;
    if (typeof needs === "number") { sev = needs; list = null; }
    else { sev = (typeof severity === "number") ? severity : 0.6; list = needs; }
    sev = Math.max(0, Math.min(1, sev));
    if (!list) {                                               // auto-derive the fortify shopping list from severity
      list = [{ kind: "wood", qty: Math.round(40 + 80 * sev) }, { kind: "stone", qty: Math.round(30 + 70 * sev) }];
      if (sev >= 0.6) list.push({ kind: "scrap", rarity: "Common", qty: Math.round(8 + 16 * sev) });
    }
    var arr = Array.isArray(list) ? list : [list], added = 0;
    mutateBook(function (b) {
      pruneBuyOrders(b);
      arr.forEach(function (n) {
        if (!n) return;
        var kind = n.kind, rarity = (kind === "scrap") ? (n.rarity || "Common") : undefined;
        if (DEMAND_MAT_KINDS.indexOf(kind) < 0) return;        // only the fortify mats (wood/stone/scrap)
        var qty = Math.max(1, (n.qty | 0) || (kind === "scrap" ? 12 : 60));
        var o = makeBuyOrder(newBoId(), distId, kind, rarity, qty, sev, "raid"); o._src = "loc";
        var merged = false;                                    // coalesce a same district+kind+rarity open order
        for (var i = 0; i < b.buyOrders.length; i++) {
          var e = b.buyOrders[i];
          if (e && e.district === distId && e.kind === kind && (e.rarity || null) === (rarity || null) && boRemaining(e) > 0) {
            e.qty = (e.qty | 0) + qty; e.expiresAt = Math.max(e.expiresAt || 0, o.expiresAt); e.unit = Math.max(e.unit | 0, o.unit); merged = true; break;
          }
        }
        if (!merged) { if (b.buyOrders.length >= BUYORDER_CAP) b.buyOrders.shift(); b.buyOrders.push(o); }
        added++;
      });
    });
    if (added && S.uiOpen && (S.tab === "orders" || S.tab === "board")) render();
    return { ok: added > 0, added: added };
  }

  // sell what you HOLD into a district's buy-order: premium gold now, the mat is
  // consumed (the sink), the fill records a high price (the float ticks up).
  function fillBuyOrder(id, btn) {
    var cd = cooldownLeft(); if (cd > 0) { toast("Quill's counting coin -- " + Math.ceil(cd / 1000) + "s."); return; }
    if (capLeft() <= 0) { toast("Daily cap reached (" + DAILY_CAP + ")."); return; }
    var order = findOrder(id); if (!order) { toast("That order's gone."); render(); return; }
    var rem = boRemaining(order);
    var have = balanceOf({ kind: order.kind, rarity: order.rarity });
    var amt = Math.min(rem, have);
    if (amt <= 0) { toast("You hold no " + (order.rarity ? order.rarity + " " : "") + order.kind + " to sell."); return; }
    if (btn) btn.disabled = true;
    deduct({ kind: order.kind, rarity: order.rarity, amount: amt });
    var gold = Math.round(amt * order.unit);
    credit({ kind: "gold", amount: gold });
    recordFill(order.kind, order.rarity, order.unit);          // a fill at the premium price -> the float ticks up
    if (order._src === "seed") { order.filled = (order.filled | 0) + amt; }   // in-memory day-cache ref
    else { mutateBook(function (b) { for (var i = 0; i < b.buyOrders.length; i++) { if (b.buyOrders[i] && b.buyOrders[i].id === id) { b.buyOrders[i].filled = (b.buyOrders[i].filled | 0) + amt; break; } } pruneBuyOrders(b); }); }
    logAction("sell"); pushNow();
    toast("Sold " + fmtN(amt) + " " + (order.rarity ? order.rarity + " " : "") + order.kind + " to " + (order.districtName || "the block") + " for " + fmtN(gold) + "g.");
    render();
  }

  // ----------------------------------------------------------------------- //
  //  PARITY GUARD (belt + suspenders -- the selects already exclude these)   //
  // ----------------------------------------------------------------------- //
  function forbidden(item) {
    if (!item || typeof item !== "object") return true;
    if (RES_KINDS.indexOf(item.kind) < 0) return true;          // blocks gems, cards, cosmetics, $BCARDD
    if (item.kind === "scrap" && SCRAP_RARITIES.indexOf(item.rarity) < 0) return true;  // Mythic scrap blocked
    if ((item.amount | 0) <= 0) return true;
    return false;
  }
  function isResListing(L) { return L && L.give && L.want && !forbidden(L.give) && !forbidden(L.want); }

  // ----------------------------------------------------------------------- //
  //  LOCAL MARKET BOOK -- a SEPARATE localStorage key (NOT ak_profile).      //
  //  Holds the player's resting offers + a light anti-spam log. Profile      //
  //  zero-state stays byte-identical (we never add a profile field).         //
  // ----------------------------------------------------------------------- //
  function lsGet(k) { try { return (typeof localStorage !== "undefined" && localStorage) ? localStorage.getItem(k) : null; } catch (_) { return null; } }
  function lsSet(k, v) { try { if (typeof localStorage !== "undefined" && localStorage) localStorage.setItem(k, v); } catch (_) {} }
  function loadBook() {
    var b = null; try { var raw = lsGet("ak_market"); if (raw) b = JSON.parse(raw); } catch (_) { b = null; }
    if (!b || typeof b !== "object") b = {};
    if (!Array.isArray(b.mine)) b.mine = [];
    if (!Array.isArray(b.log)) b.log = [];
    if (!Array.isArray(b.hot)) b.hot = [];   // the Fence's hot stash (raided goods awaiting laundering)
    if (!Array.isArray(b.buyOrders)) b.buyOrders = [];   // P8: real raid-fed buy-orders (district demand)
    if (typeof b.cooldownUntil !== "number") b.cooldownUntil = 0;
    return b;
  }
  function saveBook(b) { try { lsSet("ak_market", JSON.stringify(b)); } catch (_) {} }
  function mutateBook(fn) { var b = loadBook(); try { fn(b); } catch (_) { return null; } saveBook(b); return b; }

  function todayKey() { var d = new Date(); return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }
  function actionsToday() {
    var b = loadBook(), day = todayKey();
    return b.log.filter(function (x) { return x && x.day === day; }).length;
  }
  function capLeft() { return Math.max(0, DAILY_CAP - actionsToday()); }
  // AK-MKT 2026-07-18: how many offers this dog is currently resting on the local book.
  // Counted AFTER the expiry sweep so a lapsed offer never holds a slot hostage.
  function activeCount() { return loadBook().mine.filter(function (L) { return L && L.status === "open"; }).length; }
  function cooldownLeft() { var b = loadBook(); return Math.max(0, (Number(b.cooldownUntil) || 0) - Date.now()); }   // NOTE: no `| 0` -- a ms timestamp overflows 32-bit truncation
  function logAction(type) {
    mutateBook(function (b) {
      b.log.push({ t: Date.now(), day: todayKey(), type: type });
      var cut = Date.now() - 48 * 3600 * 1000;
      b.log = b.log.filter(function (x) { return x && x.t > cut; }).slice(-80);
      b.cooldownUntil = Date.now() + COOLDOWN_MS;
    });
  }

  // ----------------------------------------------------------------------- //
  //  NPC LIQUIDITY (local fallback) -- a rotating market book so the bazaar  //
  //  is alive offline / signed out. Prices anchor to goldValue() with a      //
  //  spread (vendors sell above fair, buy below fair -- that spread is the   //
  //  sink). Self-disables the moment real server liquidity exists.           //
  // ----------------------------------------------------------------------- //
  function pick(arr, i) { return arr[((i % arr.length) + arr.length) % arr.length]; }
  function npcOffers() {
    if (S.npc.length && (Date.now() - S.npcAt) < SEED_TTL_MS) return S.npc;
    var out = [], i = 0, seed = Math.floor(Date.now() / SEED_TTL_MS);
    function vendor() { return pick(VENDOR_NAMES, seed + (i++)); }
    function scrapItem(amt) { return { kind: "scrap", rarity: pick(SCRAP_RARITIES, seed), amount: amt }; }
    // 1) vendors SELLING raw goods for gold (you BUY, paying a small premium)
    [ { kind: "wood", amount: 50 }, { kind: "stone", amount: 50 }, { kind: "metal", amount: 25 } ].forEach(function (give) {
      out.push({ id: "npc_s" + (i), _src: "npc", seller_name: vendor(), give: give, want: { kind: "gold", amount: Math.ceil(goldValue(give) * (1 + NPC_SPREAD)) } });
    });
    // 2) vendors BUYING raw goods with gold (you SELL, taking a small discount)
    [ { kind: "produce", amount: 50 }, { kind: "wood", amount: 100 }, { kind: "metal", amount: 25 } ].forEach(function (want) {
      out.push({ id: "npc_b" + (i), _src: "npc", seller_name: vendor(), give: { kind: "gold", amount: Math.max(1, Math.floor(goldValue(want) * (1 - NPC_SPREAD))) }, want: want });
    });
    // 3) pure barter (resource for resource), priced at par + a touch
    out.push({ id: "npc_x1", _src: "npc", seller_name: vendor(), give: { kind: "stone", amount: 40 }, want: { kind: "wood", amount: Math.ceil(goldValue({ kind: "stone", amount: 40 }) / (ecMatSell().wood || 2)) } });
    out.push({ id: "npc_x2", _src: "npc", seller_name: vendor(), give: scrapItem(10), want: { kind: "produce", amount: Math.ceil(goldValue(scrapItem(10)) / ecProduceGold()) } });
    S.npc = out.filter(isResListing); S.npcAt = Date.now();
    return S.npc;
  }
  function dropNpc(id) { S.npc = S.npc.filter(function (o) { return o.id !== id; }); }
  // pull the current-hour bot population listings (deterministic, always offline-safe).
  // Filters out IDs the player already bought this session so each clears once.
  function botListings() {
    try {
      var pop = global.AK_POPULATION;
      if (!pop || typeof pop.marketListings !== "function") return [];
      return pop.marketListings(Date.now()).filter(function (L) {
        return !_boughtBotIds[L.id] && isResListing(L);
      });
    } catch (_) { return []; }
  }

  // ----------------------------------------------------------------------- //
  //  MARKET MAKER -- fills a fair resting SELL offer (you ask <= what you     //
  //  give is worth + a small spread). Greedy asks rest until you cancel.     //
  //  Runs ONLY on open / board render / a gentle interval while open.        //
  // ----------------------------------------------------------------------- //
  // AK-MKT 2026-07-18: EXPIRY. A resting offer that never found a taker is not abandoned --
  // after LISTING_TTL_MS the docks hand the deposit back, so goods can never be stranded on
  // the board forever (which is what made an active-listing cap unfair to hold anyone to).
  // Runs off fillRestingOffers, so every existing sweep site gets it with no new call.
  // Entries posted before this shipped have no expiresAt -- they are dated from `t` on read.
  function expireListings() {
    var b = loadBook(); if (!b.mine.length) return 0;
    var now = Date.now(), back = [];
    b.mine.forEach(function (L) {
      if (!L || L.status !== "open" || L._src !== "loc") return;
      var due = Number(L.expiresAt) || ((Number(L.t) || now) + LISTING_TTL_MS);
      if (due > now) return;
      L.status = "expired";
      if (L.give) { credit(L.give); back.push(L.give); }   // refund the deposited give
    });
    if (!back.length) return 0;
    b.mine = b.mine.filter(function (L) { return L && L.status === "open"; });
    saveBook(b); pushNow();
    toast(back.length + " offer" + (back.length > 1 ? "s" : "") + " expired -- your goods are back.");
    return back.length;
  }

  function fillRestingOffers() {
    expireListings();                 // sweep dead listings first, so a stale ask never fills
    var b = loadBook(); if (!b.mine.length) return 0;
    var filled = [], changed = false;
    b.mine.forEach(function (L) {
      if (!L || L.status !== "open" || L._src !== "loc") return;
      var giveV = goldValue(L.give), wantV = goldValue(L.want);
      if (giveV <= 0 || wantV <= 0) return;
      if (wantV <= giveV * MAKER_FILL_RATIO) {        // a fair (buyer-friendly) ask -> the market finds a taker
        L.status = "filled"; changed = true;
        // pay out the WANT minus the market tax (a pure gold-equivalent sink baked into the unit count)
        var taxUnits = Math.floor((L.want.amount | 0) * MARKET_TAX_PCT);
        var payout = { kind: L.want.kind, rarity: L.want.rarity, amount: Math.max(0, (L.want.amount | 0) - taxUnits) };
        if (payout.amount > 0) credit(payout);
        recordFill(L.give.kind, L.give.rarity, goldValue(L.want) / Math.max(1, L.give.amount | 0));   // P6: the price the give-good fetched feeds the float
        filled.push(payout);
      }
    });
    if (changed) {
      b.mine = b.mine.filter(function (L) { return L && L.status === "open"; });   // prune cleared rows
      saveBook(b);
      pushNow();
      if (filled.length) toast("Sold " + filled.length + " offer" + (filled.length > 1 ? "s" : "") + " -- proceeds banked.");
    }
    return filled.length;
  }

  // ----------------------------------------------------------------------- //
  //  THE FENCE -- LAUNDER (raided / stolen goods wash clean here)            //
  //  Hot goods off a raid can't spend until laundered: the Fence takes a CUT //
  //  and a wash DELAY (rush it for a bigger cut). Stored in the SAME         //
  //  ak_market book under b.hot -- a SEPARATE LS key, so the AK_ECON profile //
  //  zero-state stays byte-identical (we add no profile field). Other        //
  //  systems feed loot in via window.AKFence.deposit(items, src).            //
  // ----------------------------------------------------------------------- //
  function hotList()  { return loadBook().hot.filter(function (h) { return h && (h.amount | 0) > 0; }); }
  function hotGold()  { return hotList().reduce(function (s, h) { return s + goldValue(h); }, 0); }
  function dirtyOnly(){ return hotList().filter(function (h) { return h.status !== "washing"; }); }
  function washing()  { return hotList().filter(function (h) { return h.status === "washing"; }); }
  function newHotId() { return "hot_" + Date.now().toString(36) + "_" + Math.floor(Math.random() * 1296).toString(36); }

  // normalize + validate one loot item to the soft economy (same parity rules as a trade)
  function normLoot(it) {
    if (!it || typeof it !== "object") return null;
    var kind = it.kind, amt = Math.max(0, Math.floor(it.amount || 0));
    if (RES_KINDS.indexOf(kind) < 0 || amt <= 0) return null;          // blocks gems / cards / $BCARDD / cosmetics
    var rar = (kind === "scrap") ? it.rarity : undefined;
    if (kind === "scrap" && SCRAP_RARITIES.indexOf(rar) < 0) return null;  // Mythic / bad scrap never washes
    return { kind: kind, rarity: rar, amount: amt };
  }
  // a pile's wash time scales with its value -- big hauls move slower (and quieter).
  function washMsFor(it) { return Math.min(LAUNDER_MAX_MS, LAUNDER_BASE_MS + Math.floor(goldValue(it) / 100) * LAUNDER_STEP_MS); }
  // clean payout after a cut (the cut units vanish -- a pure sink).
  function afterCut(it, pct) { return { kind: it.kind, rarity: it.rarity, amount: Math.max(0, Math.floor((it.amount | 0) * (1 - pct))) }; }
  function findHot(b, id) { for (var i = 0; i < b.hot.length; i++) if (b.hot[i] && b.hot[i].id === id) return b.hot[i]; return null; }

  // PUBLIC: register raided / stolen goods as HOT (works panel-open or closed -- pure LS).
  function depositLoot(items, src) {
    var arr = Array.isArray(items) ? items : [items], added = 0;
    mutateBook(function (b) {
      arr.forEach(function (raw) {
        var it = normLoot(raw); if (!it) return;
        // coalesce a same kind+rarity DIRTY pile to keep the stash tidy + under cap
        var merged = false;
        for (var i = 0; i < b.hot.length; i++) {
          var h = b.hot[i];
          if (h && h.status !== "washing" && h.kind === it.kind && (h.rarity || null) === (it.rarity || null)) { h.amount = (h.amount | 0) + it.amount; merged = true; break; }
        }
        if (!merged) {
          if (b.hot.length >= HOT_CAP) return;             // stash full -- drop (anti-bloat)
          b.hot.push({ id: newHotId(), kind: it.kind, rarity: it.rarity, amount: it.amount, src: (src || "raid"), status: "dirty", t: Date.now(), readyAt: 0, clean: 0 });
        }
        added++;
      });
    });
    if (added && S.uiOpen && S.tab === "launder") render();
    return { ok: added > 0, added: added };
  }

  // start a timed wash on one hot pile (smaller cut, a delay before it spends clean).
  function startWash(id) {
    var res = null;
    mutateBook(function (b) {
      var h = findHot(b, id); if (!h || h.status === "washing") return;
      h.clean = afterCut(h, LAUNDER_CUT_PCT).amount;
      h.status = "washing"; h.readyAt = Date.now() + washMsFor(h);
      res = { kind: h.kind, rarity: h.rarity, amount: h.amount };
    });
    if (res) toast("Washing " + fmtItem(res) + " -- back clean soon, minus the Fence's cut.");
    if (S.uiOpen) render();
    return { ok: !!res };
  }
  // RUSH a hot pile clean right now -- a fatter cut, no wait.
  function rushWash(id) {
    var paid = null;
    mutateBook(function (b) {
      var h = findHot(b, id); if (!h) return;
      paid = afterCut(h, RUSH_CUT_PCT);
      for (var i = 0; i < b.hot.length; i++) if (b.hot[i] === h) { b.hot.splice(i, 1); break; }
    });
    if (paid && paid.amount > 0) { credit(paid); pushNow(); toast("Rushed -- " + fmtItem(paid) + " clean in your pocket."); }
    else if (paid) toast("Too little to bother washing.");
    if (S.uiOpen) render();
    return { ok: !!paid };
  }
  // claim a finished wash -> clean goods land in the wallet.
  function claimWash(id) {
    var payout = null;
    mutateBook(function (b) {
      var h = findHot(b, id); if (!h || h.status !== "washing" || Date.now() < (h.readyAt || 0)) return;
      payout = { kind: h.kind, rarity: h.rarity, amount: Math.max(0, h.clean | 0) };
      for (var i = 0; i < b.hot.length; i++) if (b.hot[i] === h) { b.hot.splice(i, 1); break; }
    });
    if (payout && payout.amount > 0) { credit(payout); pushNow(); toast("Clean -- " + fmtItem(payout) + " banked."); }
    if (S.uiOpen) render();
    return { ok: !!payout };
  }

  // ----------------------------------------------------------------------- //
  //  DOM (XSS-safe builder; mirrors trading.js mk/setKids)                   //
  // ----------------------------------------------------------------------- //
  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") e[k] = v;
      else e.setAttribute(k, v);
    });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return e;
  }
  function setKids(el, nodes) { if (el) el.replaceChildren.apply(el, [].concat(nodes).filter(function (n) { return n != null; })); }
  function fmtN(n) { n = Math.round(n || 0); if (n >= 1e6) return (n / 1e6).toFixed(1) + "M"; if (n >= 1e4) return (n / 1e3).toFixed(1) + "k"; return "" + n; }
  function fmtTime(ms) { ms = Math.max(0, ms | 0); var s = Math.ceil(ms / 1000); if (s < 60) return s + "s"; var m = Math.floor(s / 60); return m + "m " + (s % 60) + "s"; }

  function injectCss() {
    if (document.getElementById("ak-market-css")) return;
    var st = document.createElement("style"); st.id = "ak-market-css";
    st.textContent = [
      // THE FENCE -- black-market kitsch on matte steel. SVG grain (--grain ~.06) + worn-metal
      // header; everything flat by default. The hand-chalked LIVE FENCE board is the ONE focal
      // that earns a glow. No pills, no glossy gradient buttons, no gradient-text on numbers.
      "#ak-market{position:fixed;inset:0;z-index:47;display:none;flex-direction:column;color:#e9e6db;font-family:Inter,system-ui,sans-serif;--grain:url(\"data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='140'%20height='140'%3E%3Cfilter%20id='g'%3E%3CfeTurbulence%20type='fractalNoise'%20baseFrequency='0.9'%20numOctaves='2'%20stitchTiles='stitch'/%3E%3C/filter%3E%3Crect%20width='100%25'%20height='100%25'%20filter='url(%23g)'%20opacity='0.06'/%3E%3C/svg%3E\");background:var(--grain) repeat,linear-gradient(165deg,#15131c,#0A0A0A)}",
      "#ak-market.open{display:flex}",
      // header -- worn steel slab, gold left rule, Cinzel skewed stamp title
      ".akm-top{display:flex;align-items:flex-start;gap:11px;padding:13px 15px 12px;border-bottom:1px solid #2a2620;background:var(--grain) repeat,linear-gradient(180deg,#1b1822,#100e15);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),inset 0 -12px 20px rgba(0,0,0,.42)}",
      ".akm-glyph{font-size:23px;line-height:1.2;filter:grayscale(.3) drop-shadow(0 1px 0 #000)}",
      ".akm-ttl{flex:1;min-width:0;padding-left:11px;border-left:3px solid #c9a84c}",
      ".akm-ttl h2{margin:0;font-family:Cinzel,Georgia,serif;font-weight:900;font-size:19px;letter-spacing:.03em;text-transform:uppercase;color:#e8c55a;transform:skewX(-5deg);text-shadow:0 1px 0 #000,0 2px 0 rgba(0,0,0,.55),0 3px 6px rgba(0,0,0,.65)}",
      ".akm-ttl .sub{color:#8f8463;font-size:10.5px;letter-spacing:.03em;margin-top:3px}",
      ".akm-x{background:none;border:0;color:#9a8f6a;font-size:26px;line-height:1;cursor:pointer;padding:0 2px}",
      ".akm-x:active{transform:scale(.9)}",
      // keeper barker line -- chalk scrawl across the slab
      ".akm-line{padding:9px 15px;color:#b9ad84;font-size:12px;font-style:italic;letter-spacing:.01em;border-bottom:1px solid #221f1a;background:rgba(0,0,0,.22)}",
      // tabs -- printed labels; selected = gold text + stamped underline (no pills, no boxes)
      ".akm-tabs{display:flex;gap:16px;padding:10px 15px 5px;border-bottom:1px solid #221f1a}",
      ".akm-tab{flex:0 1 auto;min-width:0;padding:3px 1px 7px;border:0;background:none;color:#7d7459;font-weight:700;font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-bottom:2px solid transparent}",
      ".akm-tab.on{color:#e8c55a;border-bottom-color:#c9a84c}",
      ".akm-meta{display:flex;gap:16px;padding:9px 15px 5px;font-size:11px;color:#8f8a7a;flex-wrap:wrap}",
      ".akm-meta b{color:#e8c55a;font-variant-numeric:tabular-nums}",
      // wallet -- flat squared steel chips
      ".akm-wallet{display:flex;gap:7px;flex-wrap:wrap;padding:0 15px 8px;font-size:11px;color:#c2b896}",
      ".akm-wallet span{display:inline-flex;align-items:center;gap:4px;background:linear-gradient(180deg,#1a1722,#100e15);border:1px solid #2a2620;border-radius:2px;padding:4px 9px;box-shadow:inset 0 1px 0 rgba(255,255,255,.04);font-variant-numeric:tabular-nums}",
      ".akm-body{flex:1;overflow-y:auto;padding:12px 15px 20px;-webkit-overflow-scrolling:touch}",
      // matte steel goods crate -- flat: faint warm top rim + bottom ambient occlusion, no glow
      ".akm-card{background:var(--grain) repeat,linear-gradient(165deg,#15131c,#0A0A0A);border:1px solid #2a2620;border-radius:3px;padding:12px 13px;margin-bottom:11px;box-shadow:inset 0 1px 0 rgba(255,255,255,.045),inset 0 -16px 22px rgba(0,0,0,.34)}",
      ".akm-li{display:flex;align-items:center;gap:11px;padding:10px 2px;border-bottom:1px solid #211e19}",
      ".akm-give{color:#74e0a0;font-weight:800;font-variant-numeric:tabular-nums}.akm-want{color:#e8c55a;font-weight:800;font-variant-numeric:tabular-nums}.akm-arrow{color:#6f6a5a}",
      ".akm-nm{font-weight:800;color:#efeadb;font-size:13px}.akm-sub{color:#8a8576;font-size:11px}",
      // AK-ART 2026-07-01: seller CREST avatar + real resource-chip legs (the chop-shop bar)
      ".akm-offer{align-items:center;gap:12px}",
      ".akm-av{flex:0 0 auto;width:44px;height:44px;border-radius:9px;overflow:hidden;border:1.5px solid #c9a84c88;background:var(--grain) repeat,radial-gradient(circle at 50% 34%,rgba(201,168,76,.18),rgba(10,10,14,.94));display:flex;align-items:center;justify-content:center;font-size:20px;line-height:1}",
      ".akm-av img{width:100%;height:100%;object-fit:cover;object-position:center}",
      ".akm-offmid{flex:1;min-width:0}",
      ".akm-trade{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
      ".akm-need{display:flex;align-items:center;flex-wrap:wrap}",
      ".akm-chip{display:inline-flex;align-items:center;gap:3px;font-variant-numeric:tabular-nums}",
      ".akm-ri{object-fit:contain;vertical-align:middle;filter:drop-shadow(0 1px 1px rgba(0,0,0,.55))}",
      ".akm-ri-g{font-size:15px;line-height:1}",
      ".akm-amt{font-weight:800}",
      ".akm-rar{font-size:10px;color:#b9ad84;font-weight:700;letter-spacing:.04em;text-transform:uppercase}",
      ".akm-seller{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:5px}",
      ".akm-sellnm{color:#c2b896;font-weight:700;font-size:12px}",
      ".akm-clan{font-size:10px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}",
      // CTA -- flat gold stamp, hard street-cut corner, no gloss, no pill
      ".akm-btn{background:#c9a84c;color:#16110a;border:1px solid #8a712b;border-radius:0;clip-path:polygon(7px 0,100% 0,100% 100%,0 100%,0 7px);padding:11px 16px;font-family:Inter,sans-serif;font-weight:800;letter-spacing:.06em;text-transform:uppercase;font-size:12px;cursor:pointer}",
      ".akm-btn.ghost{background:linear-gradient(180deg,#1b1822,#100e15);color:#d9d3c2;border:1px solid #2a2620}",
      ".akm-btn.dng{background:#3a1414;color:#f1a5a5;border:1px solid #5e2222}",
      ".akm-btn:active{transform:translateY(1px) scale(.99)}.akm-btn[disabled]{opacity:.45;cursor:not-allowed}",
      ".akm-inp,.akm-sel{width:100%;box-sizing:border-box;background:#0c0a10;border:1px solid #2a2620;color:#efeadb;border-radius:2px;padding:11px;margin:5px 0;font-size:14px}",
      ".akm-inp:focus,.akm-sel:focus{outline:0;border-color:#c9a84c}",
      ".akm-lbl{color:#8f8463;font-size:10.5px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin-top:9px}",
      ".akm-note{color:#8a8576;font-size:12.5px;text-align:center;padding:22px 10px;line-height:1.55}",
      ".akm-val{color:#e8c55a;font-size:12px;margin:7px 0;font-variant-numeric:tabular-nums}",
      // taped / stamped price marks -- hand-applied, slightly crooked, hard edges
      ".akm-tag{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:1px;margin-left:7px;transform:rotate(-1.6deg)}",
      ".akm-tag.live{background:rgba(116,224,160,.1);color:#74e0a0;border:1px solid rgba(116,224,160,.5);box-shadow:inset 0 0 0 1px rgba(116,224,160,.12)}",
      ".akm-tag.loc{background:rgba(201,168,76,.1);color:#e8c55a;border:1px solid rgba(201,168,76,.5);box-shadow:inset 0 0 0 1px rgba(201,168,76,.12);transform:rotate(1.4deg)}",
      ".akm-toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:linear-gradient(180deg,#1b1822,#100e15);color:#e8c55a;border:1px solid #2a2620;border-left:3px solid #c9a84c;padding:9px 16px;border-radius:2px;z-index:71;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none;box-shadow:0 6px 18px rgba(0,0,0,.5)}",
      ".akm-toast.show{opacity:1}",
      // THE FOCAL -- the hand-chalked LIVE FENCE board. The one element that earns a glow.
      ".akm-ticker{margin-bottom:13px;border:1px solid #2a2620;border-radius:3px;background:var(--grain) repeat,linear-gradient(180deg,#13130f,#0c0c09);overflow:hidden;box-shadow:0 0 0 1px rgba(201,168,76,.18),0 6px 22px rgba(201,168,76,.1),inset 0 0 34px rgba(0,0,0,.55)}",
      ".akm-tk-cap{display:flex;align-items:center;gap:8px;padding:6px 11px 4px;font-size:10px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;color:#e8c55a;border-bottom:1px solid rgba(201,168,76,.16);text-shadow:0 0 1px rgba(255,241,204,.25)}",
      ".akm-tk-cap .akm-tk-sub{color:#8f8463;font-weight:600;letter-spacing:.02em;text-transform:none;text-shadow:none}",
      ".akm-tk-tape{overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}",
      ".akm-tk-row{display:flex;gap:22px;white-space:nowrap;width:max-content;padding:8px 11px;will-change:transform;animation:akm-tape 26s linear infinite}",
      ".akm-tk-tape:active .akm-tk-row{animation-play-state:paused}",
      "@keyframes akm-tape{from{transform:translateX(0)}to{transform:translateX(-50%)}}",
      ".akm-tk-i{display:inline-flex;align-items:center;gap:5px;font-size:12px}",
      ".akm-tk-g{font-size:13px;line-height:1}",
      ".akm-tk-l{color:#8f8463;text-transform:uppercase;letter-spacing:.06em;font-size:10px;font-weight:700}",
      ".akm-tk-p{color:#e8c55a;font-weight:800;font-variant-numeric:tabular-nums;text-shadow:0 0 1px rgba(255,241,204,.2)}",
      ".akm-tk-a{font-weight:900;font-size:11px;font-variant-numeric:tabular-nums}",
      ".akm-tk-a.up{color:#74e0a0}.akm-tk-a.down{color:#ff7a7a}.akm-tk-a.flat{color:#8f8a7a}",
      ".akm-tk-hot{font-size:11px;filter:drop-shadow(0 0 4px rgba(255,140,60,.7))}",
      "@media (prefers-reduced-motion:reduce){.akm-tk-row{animation:none}}"
    ].join("");
    document.head.appendChild(st);
  }

  function toast(m) { if (!S.toastEl) return; S.toastEl.textContent = m; S.toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { S.toastEl.classList.remove("show"); }, 2200); }

  // ----------------------------------------------------------------------- //
  //  PANEL: open / close (overlay freeze + DOM controls on top)              //
  // ----------------------------------------------------------------------- //
  function buildPanel() {
    if (S.root) return;
    injectCss();
    var glyph = mk("span", { class: "akm-glyph", text: "⚖️" }); // balance scales
    var ttl = mk("div", { class: "akm-ttl" }, [ mk("h2", { text: "THE BAZAAR" }), mk("div", { class: "sub", text: "Quill the Quartermaster -- resource exchange" }) ]);
    var x = mk("button", { class: "akm-x", type: "button", "aria-label": "close", text: "×", onclick: closeMarket });
    var top = mk("div", { class: "akm-top" }, [ glyph, ttl, x ]);
    var line = mk("div", { class: "akm-line", text: pick(KEEPER_LINES, Math.floor(Math.random() * KEEPER_LINES.length)) });
    S.bodyEl = mk("div", { class: "akm-body" });
    S.root = mk("section", { id: "ak-market" }, [ top, line, S.bodyEl ]);
    document.body.appendChild(S.root);
    if (!S.toastEl) { S.toastEl = mk("div", { class: "akm-toast" }); document.body.appendChild(S.toastEl); }
    S.root.classList.add("open");
  }

  function drawBackdrop(g, dt, vp) {
    // gritty dim wash + drifting gold embers behind the DOM panel
    g.save();
    g.fillStyle = "rgba(6,5,3,.86)"; g.fillRect(0, 0, vp.w, vp.h);
    var t = (drawBackdrop._t = (drawBackdrop._t || 0) + dt);
    g.globalAlpha = .5; g.fillStyle = "#e8c55a";
    for (var i = 0; i < 14; i++) {
      var x = (i * 71 + (t * 11 + i * 37)) % (vp.w + 40) - 20;
      var y = (vp.h - ((t * 17 + i * 84) % (vp.h + 40)));
      g.beginPath(); g.arc(x, y, 1.2 + (i % 3) * 0.5, 0, 7); g.fill();
    }
    g.globalAlpha = 1; g.restore();
  }

  var VALID_TABS = { board: 1, post: 1, orders: 1, mine: 1, launder: 1 };
  function openMarket(tab) {
    if (S.uiOpen) { if (tab && VALID_TABS[tab]) setTab(tab); return; }
    S.uiOpen = true; S.entryLock = true;
    // freeze the hub via the contract overlay (drawn backdrop). DOM panel rides on top (z 47 > overlay 40).
    if (CTX && CTX.overlay && CTX.overlay.open) {
      try { S.ovApi = CTX.overlay.open({ id: "marketplace", onFrame: drawBackdrop, onPointer: function () {}, onClose: teardownUI }); }
      catch (_e) { S.ovApi = null; }
    }
    buildPanel();
    if (online()) claimGrants();      // pull any pending sale proceeds first
    fillRestingOffers();              // clear any fair asks the market took while you were away
    setTab(tab && VALID_TABS[tab] ? tab : "board");
    // gentle heartbeat while the panel is open (cleared on close -> no background work).
    // re-renders MINE on a fill, and LAUNDER every beat so wash countdowns tick + claim unlocks.
    clearInterval(S.makerTimer);
    S.makerTimer = setInterval(function () {
      if (!S.uiOpen) { clearInterval(S.makerTimer); return; }
      var f = fillRestingOffers();
      refreshTicker();                                  // P6: the tape re-reads the float every beat (and after any fill)
      if ((f && S.tab === "mine") || S.tab === "launder" || S.tab === "orders") render();
    }, 6000);
  }
  function closeMarket() {
    if (S.ovApi) { try { S.ovApi.close(); } catch (_e) { teardownUI(); } }   // onClose -> teardownUI
    else teardownUI();
  }
  function teardownUI() {
    S.uiOpen = false; S.ovApi = null;
    clearInterval(S.makerTimer); S.makerTimer = 0;
    if (S.root) { try { S.root.remove(); } catch (_e) {} S.root = null; S.bodyEl = null; }
  }
  function setTab(t) { S.tab = t; render(); }

  // ----------------------------------------------------------------------- //
  //  GATES                                                                   //
  // ----------------------------------------------------------------------- //
  function townHall() { var e = econ(); try { return e && e.townHallLevel ? e.townHallLevel() : 1; } catch (_) { return 1; } }
  function myTrophies() { var p = prof(); return (p && p.trophies | 0) || 0; }
  function myBand() { return Math.floor(myTrophies() / BAND_SIZE); }
  function bandLabel(b) { return (b * BAND_SIZE) + "-" + (b * BAND_SIZE + BAND_SIZE - 1) + " trophies"; }

  // ----------------------------------------------------------------------- //
  //  RENDER                                                                  //
  // ----------------------------------------------------------------------- //
  function fmtItem(it) {
    if (!it) return "?";
    var ic = ICO[it.kind] || "";
    if (it.kind === "scrap") return ic + " " + fmtN(it.amount) + " " + it.rarity + " scrap";
    return ic + " " + fmtN(it.amount) + " " + it.kind;
  }

  // ----------------------------------------------------------------------- //
  //  ART (AK-ART 2026-07-01) -- REAL crest + resource-chip art for the rows  //
  //  Reuses the shop-wide resolvers, NO new art path: the faction CREST      //
  //  mirrors social.js facCrest (assets/ui/Crest_*.jpg); resource chips are  //
  //  the transparent-cleaned assets/icons/chip_*.png set. The ICO glyph is   //
  //  the fallback ONLY where art is genuinely absent (stray / vendor seller, //
  //  a missing file). Raises the Fence rows to the chop-shop card-art bar.   //
  // ----------------------------------------------------------------------- //
  var FAC_CREST = {
    boneguard_crew:    "assets/ui/Crest_Boneguard.jpg",
    zoomie_syndicate:  "assets/ui/Crest_Zoomie.jpg",
    leashbreak_tactix: "assets/ui/Crest_Leashbreak.jpg",
    k9_circuitry:      "assets/ui/Crest_K9.jpg"
  };
  function facCrest(fac) { return FAC_CREST[fac] || ""; }
  var RES_CHIP = {
    gold:    "assets/icons/chip_gold.png",
    produce: "assets/icons/chip_produce.png",
    wood:    "assets/icons/chip_wood.png",
    stone:   "assets/icons/chip_stone.png",
    metal:   "assets/icons/chip_metal.png",
    scrap:   "assets/icons/chip_scrap.png"
  };
  // a resource as REAL chip art (transparent PNG); degrades to the ICO glyph if missing.
  function resIcon(kind, px) {
    px = px || 18;
    var src = RES_CHIP[kind];
    if (!src) return mk("span", { class: "akm-ri-g", text: ICO[kind] || "" });
    var img = mk("img", { class: "akm-ri", src: src, alt: "", loading: "lazy", style: "width:" + px + "px;height:" + px + "px" });
    img.onerror = function () { try { if (img.parentNode) img.parentNode.replaceChild(mk("span", { class: "akm-ri-g", text: ICO[kind] || "" }), img); } catch (_) {} };
    return img;
  }
  // an OFFER/WANT leg as chip art + tabular amount (+ rarity for scrap). cls tints the amount.
  function itemChip(it, cls) {
    if (!it) return mk("span", { class: cls || "", text: "?" });
    var kids = [ resIcon(it.kind, 18), mk("span", { class: "akm-amt", text: fmtN(it.amount) }) ];
    if (it.kind === "scrap") kids.push(mk("span", { class: "akm-rar", text: it.rarity }));
    return mk("span", { class: "akm-chip " + (cls || ""), title: fmtItem(it) }, kids);
  }
  // the SELLER as a real avatar: the clan CREST art (bot listings), ringed in the clan
  // colour; a neutral Fence token for vendors / local / stray sellers (no clan art to show).
  function sellerAvatar(L) {
    var col = (L && L.color) || "#c9a84c";
    var wrap = mk("div", { class: "akm-av", style: "border-color:" + col + "88;box-shadow:0 0 8px " + col + "44" });
    var src = facCrest(L && L.seller_clan);
    if (src) {
      var img = mk("img", { src: src, alt: "", loading: "lazy" });
      img.onerror = function () { try { wrap.removeChild(img); wrap.textContent = "\u{1F43E}"; } catch (_) {} };
      wrap.appendChild(img);
    } else {
      wrap.textContent = (L && L._src === "npc") ? "\u{1F6D2}" : "\u{1F43E}";
    }
    return wrap;
  }

  function wallet() {
    var p = prof() || {};
    var scrapTot = p.scrap ? (p.scrap.Common | 0) + (p.scrap.Rare | 0) + (p.scrap.Epic | 0) + (p.scrap.Legendary | 0) : 0;
    function wc(kind, amt) { return mk("span", {}, [ resIcon(kind, 15), mk("span", { text: fmtN(amt) }) ]); }
    return mk("div", { class: "akm-wallet" }, [
      wc("gold", p.coins | 0), wc("produce", p.produce | 0), wc("wood", p.wood | 0),
      wc("stone", p.stone | 0), wc("metal", p.metal | 0), wc("scrap", scrapTot)
    ]);
  }

  function render() {
    if (!S.bodyEl) return;
    // Town Hall gate (applies online + offline -- anti-fresh-account)
    var th = townHall();
    if (th < MIN_TH) {
      setKids(S.bodyEl, [ mk("div", { class: "akm-card" }, [
        mk("div", { class: "akm-note", text: "The bazaar opens at Town Hall Lv " + MIN_TH + ". You're Lv " + th + ". Level the Town Hall, then come haul." })
      ]) ]);
      return;
    }
    var hotN = hotList().length, orderN = openBuyOrders().length;
    var tabs = mk("div", { class: "akm-tabs" }, [
      mk("button", { class: "akm-tab" + (S.tab === "board" ? " on" : ""), text: "MARKET", onclick: function () { setTab("board"); } }),
      mk("button", { class: "akm-tab" + (S.tab === "post" ? " on" : ""), text: "SELL", onclick: function () { setTab("post"); } }),
      mk("button", { class: "akm-tab" + (S.tab === "orders" ? " on" : ""), text: "ORDERS" + (orderN ? " (" + orderN + ")" : ""), onclick: function () { setTab("orders"); } }),
      mk("button", { class: "akm-tab" + (S.tab === "mine" ? " on" : ""), text: "MINE", onclick: function () { setTab("mine"); } }),
      mk("button", { class: "akm-tab" + (S.tab === "launder" ? " on" : ""), text: "WASH" + (hotN ? " (" + hotN + ")" : ""), onclick: function () { setTab("launder"); } })
    ]);
    var meta = mk("div", { class: "akm-meta" }, [
      mk("span", {}, [ "Band: ", mk("b", { text: bandLabel(myBand()) }) ]),
      mk("span", {}, [ "Today: ", mk("b", { text: actionsToday() + "/" + DAILY_CAP }) ]),
      mk("span", {}, [ online() ? "Live market" : "Local market" ])
    ]);
    var slot = mk("div", {});
    var nodes = [ tabs, meta, wallet() ];
    if (!me()) nodes.push(mk("div", { class: "akm-note", style: "padding:6px 2px", text: "Signed out -- you are trading the local market. Sign in to deal with other players." }));
    // P6: the live FENCE ticker tape rides above the board + the orders board.
    if (S.tab === "board" || S.tab === "orders") nodes.push(renderTicker());
    else S.tickerEl = null;
    nodes.push(slot);
    setKids(S.bodyEl, nodes);
    if (S.tab === "board") renderBoard(slot);
    else if (S.tab === "post") renderPost(slot);
    else if (S.tab === "orders") renderOrders(slot);
    else if (S.tab === "launder") renderLaunder(slot);
    else renderMine(slot);
  }

  // ----- P6 LIVE TICKER TAPE: floating Fence prices scroll like a stock crawl - //
  function fmtPrice(v) { v = +v || 0; return (v >= 2) ? fmtN(Math.round(v)) : (Math.round(v * 100) / 100); }
  function priceArrow(kind, rarity) {
    var cur = unitPrice(kind, rarity), e = econ(), day = null;
    try { if (e && typeof e.ptDayIndex === "function") day = e.ptDayIndex(); } catch (_) {}
    var ref = baseUnit(kind, rarity, (day != null) ? day - 1 : null) * econFenceMult();   // yesterday's float, no demand
    var dir = 0;
    if (ref > 0) { if (cur > ref * 1.004) dir = 1; else if (cur < ref * 0.996) dir = -1; }
    return { cur: cur, dir: dir };
  }
  function tickerItems() {
    function build() {
      return TICKER_KINDS.map(function (t) {
        var a = priceArrow(t.kind, t.rarity), dm = demandMult(t.kind, t.rarity);
        var dir = a.dir > 0 ? "up" : a.dir < 0 ? "down" : "flat";
        var arrow = a.dir > 0 ? "▲" : a.dir < 0 ? "▼" : "▬";   // up / down / flat
        var lbl = (t.kind === "scrap") ? ((t.rarity || "Common").charAt(0) + " scr") : t.kind;
        var kids = [
          mk("span", { class: "akm-tk-g" }, [ resIcon(t.kind, 15) ]),
          mk("span", { class: "akm-tk-l", text: lbl }),
          mk("span", { class: "akm-tk-p", text: fmtPrice(a.cur) + "g" }),
          mk("span", { class: "akm-tk-a " + dir, text: arrow })
        ];
        if (dm > 1.001) kids.push(mk("span", { class: "akm-tk-hot", title: "district demand -- price up", text: "🔥" }));
        return mk("span", { class: "akm-tk-i" }, kids);
      });
    }
    return build().concat(build());   // duplicate once for a seamless -50% scroll loop
  }
  function renderTicker() {
    var row = mk("div", { class: "akm-tk-row" }, tickerItems());
    S.tickerEl = row;
    return mk("div", { class: "akm-ticker" }, [
      mk("div", { class: "akm-tk-cap" }, [ mk("span", { text: "⚡ LIVE FENCE" }), mk("span", { class: "akm-tk-sub", text: "prices float on recent fills" }) ]),
      mk("div", { class: "akm-tk-tape" }, [ row ])
    ]);
  }
  function refreshTicker() { try { if (S.tickerEl && S.uiOpen) setKids(S.tickerEl, tickerItems()); } catch (_) {} }

  // ----- ORDERS: raid-fed district buy-orders (the P8 demand sink) ---------- //
  function renderOrders(slot) {
    var orders = openBuyOrders().slice().sort(function (a, b) { return (b.prem || 0) - (a.prem || 0); });
    var nodes = [ mk("div", { class: "akm-note", style: "padding:6px 2px;text-align:left", text: "Raided blocks are short on fortify mats. Sell them wood, stone or scrap -- they pay over market, and every sale you make nudges the Fence price up." }) ];
    if (!orders.length) { nodes.push(mk("div", { class: "akm-note", text: "No blocks are crying for mats right now. Hit a rival's stash -- a gutted block always needs to rebuild." })); setKids(slot, nodes); return; }
    orders.forEach(function (o) {
      var rem = boRemaining(o), have = balanceOf({ kind: o.kind, rarity: o.rarity }), prem = Math.round((o.prem || 0) * 100);
      var sell = Math.min(rem, have);
      var btn = mk("button", { class: "akm-btn" + (have > 0 ? "" : " ghost"), text: have > 0 ? ("SELL " + fmtN(sell)) : "NONE HELD" });
      if (have > 0) btn.onclick = function () { fillBuyOrder(o.id, btn); }; else btn.disabled = true;
      var srcTag = (o.src === "raid") ? mk("span", { class: "akm-tag live", text: "raid" }) : mk("span", { class: "akm-tag loc", text: "distress" });
      nodes.push(mk("div", { class: "akm-li" }, [
        mk("div", { style: "flex:1" }, [
          mk("div", { class: "akm-need" }, [ mk("span", { class: "akm-want", text: (o.districtName || "a block") }), mk("span", { class: "akm-sub", text: " needs " + fmtN(rem) + " " }), resIcon(o.kind, 15), mk("span", { class: "akm-sub", text: " " + (o.rarity ? o.rarity + " " : "") + o.kind }) ]),
          mk("div", { class: "akm-sub" }, [ mk("span", { class: "akm-give", text: o.unit + "g/ea" }), " (+" + prem + "% over market)  ", srcTag ])
        ]),
        btn
      ]));
    });
    setKids(slot, nodes);
  }

  // ----- WASH: launder raided / stolen goods clean (the Fence's cut + delay) ----- //
  function renderLaunder(slot) {
    var dirty = dirtyOnly(), wash = washing(), nodes = [];
    nodes.push(mk("div", { class: "akm-note", style: "padding:6px 2px;text-align:left", text: "Hot goods off a raid don't spend clean. Quill washes them -- a " + Math.round(LAUNDER_CUT_PCT * 100) + "% cut and a wait, or rush it for " + Math.round(RUSH_CUT_PCT * 100) + "%." }));
    if (!dirty.length && !wash.length) {
      nodes.push(mk("div", { class: "akm-note", text: "No hot goods to move. Raid a rival's stash, then bring the haul back here to launder it clean." }));
      setKids(slot, nodes); return;
    }
    if (wash.length) {
      nodes.push(mk("div", { class: "akm-lbl", text: "Washing" }));
      wash.forEach(function (h) {
        var left = (h.readyAt || 0) - Date.now(), ready = left <= 0;
        var btn = mk("button", { class: "akm-btn" + (ready ? "" : " ghost"), text: ready ? "CLAIM" : fmtTime(left) });
        if (ready) btn.onclick = function () { claimWash(h.id); }; else btn.disabled = true;
        nodes.push(mk("div", { class: "akm-li" }, [
          mk("div", { style: "flex:1" }, [
            mk("div", { class: "akm-trade" }, [ itemChip(h, "akm-give"), mk("span", { class: "akm-arrow", text: "→" }), itemChip({ kind: h.kind, rarity: h.rarity, amount: h.clean }, "akm-want"), mk("span", { class: "akm-sub", text: "clean" }) ]),
            mk("div", { class: "akm-sub", text: ready ? "washed -- ready to claim" : "washing... " + fmtTime(left) })
          ]), btn
        ]));
      });
    }
    if (dirty.length) {
      nodes.push(mk("div", { class: "akm-lbl", text: "Hot stash" }));
      dirty.forEach(function (h) {
        var clean = afterCut(h, LAUNDER_CUT_PCT).amount, rush = afterCut(h, RUSH_CUT_PCT).amount;
        var washBtn = mk("button", { class: "akm-btn", text: "LAUNDER", onclick: function () { startWash(h.id); } });
        var rushBtn = mk("button", { class: "akm-btn ghost", text: "RUSH", onclick: function () { rushWash(h.id); } });
        nodes.push(mk("div", { class: "akm-li" }, [
          mk("div", { style: "flex:1" }, [
            mk("div", { class: "akm-trade" }, [ itemChip(h, "akm-give"), mk("span", { class: "akm-sub", text: "from " + (h.src || "raid") }) ]),
            mk("div", { class: "akm-sub", text: "wash -> " + fmtN(clean) + " clean (" + fmtTime(washMsFor(h)) + ")  ·  rush -> " + fmtN(rush) + " now" })
          ]),
          mk("div", { style: "display:flex;gap:6px" }, [ washBtn, rushBtn ])
        ]));
      });
    }
    setKids(slot, nodes);
  }

  function offerRow(L, action) {
    // provenance tag: bot rows now carry the crest avatar + clan name, so the tag reads "world"
    var srcTag = L._src === "npc" ? mk("span", { class: "akm-tag loc", text: "vendor" })
               : L._src === "bot" ? mk("span", { class: "akm-tag live", text: "world" })
               : L._src === "loc" ? mk("span", { class: "akm-tag loc", text: "local" })
               : mk("span", { class: "akm-tag live", text: "live" });
    var btn = mk("button", { class: "akm-btn" + (action.ghost ? " ghost" : (action.danger ? " dng" : "")), text: action.label });
    if (action.disabled) btn.disabled = true; else btn.onclick = function () { action.fn(L, btn); };
    var trade = mk("div", { class: "akm-trade" }, [
      itemChip(L.give, "akm-give"),
      mk("span", { class: "akm-arrow", text: "→" }),
      itemChip(L.want, "akm-want")
    ]);
    var seller = mk("div", { class: "akm-seller" }, [
      mk("span", { class: "akm-sellnm", text: (L.seller_name || "Stray") }),
      L.seller_clanName ? mk("span", { class: "akm-clan", style: "color:" + ((L.color) || "#8f8463"), text: L.seller_clanName }) : null,
      srcTag
    ]);
    return mk("div", { class: "akm-li akm-offer" }, [
      sellerAvatar(L),
      mk("div", { class: "akm-offmid" }, [ trade, seller ]),
      btn
    ]);
  }

  // ----- BOARD: server listings + bot population + NPC vendor liquidity ---- //
  function renderBoard(slot) {
    fillRestingOffers();
    var bots = botListings(); // deterministic per hour -- always available offline
    function paint(serverRows, isLive) {
      if (!S.root) return;
      var live = (serverRows || []).filter(isResListing);
      // NPC vendor fallback only when there are no live server listings (same policy as before)
      var vendors = live.length ? [] : npcOffers();
      // bot population listings always appear -- they represent AI dogs living in the world
      var all = live.concat(bots).concat(vendors);
      if (!all.length) { setKids(slot, mk("div", { class: "akm-note", text: "No open offers right now. Tap SELL to put goods on the board, or check back -- the docks move fast." })); return; }

      // AK-MKT 2026-07-18: browse controls. Category tabs come from the BACKPACK registry so
      // "MATERIALS" means the same thing in the bag and on the board; the sort select ranks
      // what survives the filter. Both are pure view state -- nothing is refetched on change.
      var rowsHost = mk("div", {});
      var cats = marketCats();
      var tabRow = mk("div", { class: "akm-cats", style: "display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px" });
      var sortSel = mk("select", { class: "akm-sel", style: "margin-bottom:6px" },
        SORTS.map(function (s) { return mk("option", { value: s.id, text: s.label }); }));
      sortSel.value = S.sort;

      function paintRows() {
        var shown = sortListings(all.filter(function (L) { return listingInCat(L, S.cat); }), S.sort);
        if (!shown.length) {
          setKids(rowsHost, mk("div", { class: "akm-note", text: "Nothing on the board in that category. Try ALL." }));
          return;
        }
        setKids(rowsHost, shown.map(function (L) {
          var mine = isLive && L.seller_id === myId();
          var isBot = (L._src === "bot");
          return offerRow(L, mine
            ? { label: "yours", ghost: true, disabled: true, fn: function () {} }
            : isBot
              ? { label: "Trade", fn: acceptBotListing }
              : { label: "Trade", fn: acceptOffer });
        }));
      }
      function paintTabs() {
        setKids(tabRow, cats.map(function (c) {
          var on = (c.id === S.cat);
          return mk("button", {
            class: "akm-btn" + (on ? "" : " ghost"),
            style: "padding:5px 11px;font-size:11px",
            text: c.label,
            onclick: function () { S.cat = c.id; paintTabs(); paintRows(); }
          });
        }));
      }
      sortSel.onchange = function () { S.sort = sortSel.value; paintRows(); };
      paintTabs(); paintRows();
      setKids(slot, [ tabRow, sortSel, rowsHost ]);
    }
    if (online()) {
      setKids(slot, mk("div", { class: "akm-note", text: "Loading the board..." }));
      call(MARKET_FN, { action: "list", band: myBand(), q: "" }).then(function (r) {
        if (!S.root) return;
        var rows = (r && r.ok) ? (r.listings || []).filter(isResListing) : [];
        paint(rows, !!(r && r.ok));
      });
    } else {
      paint([], false);
    }
  }

  // ----- SELL: post a new offer (give resource -> want resource) ----------- //
  function renderPost(slot) {
    // GIVE
    var giveKind = mk("select", { class: "akm-sel" }, RES_KINDS.map(function (k) { return mk("option", { value: k, text: ICO[k] + " " + k }); }));
    var giveScrapRar = mk("select", { class: "akm-sel" }, SCRAP_RARITIES.map(function (rr) { return mk("option", { value: rr, text: rr + " scrap" }); }));
    var giveAmt = mk("select", { class: "akm-sel" });
    var giveScrapWrap = mk("div", { style: "display:none" }, giveScrapRar);
    // WANT
    var wantKind = mk("select", { class: "akm-sel" }, RES_KINDS.map(function (k) { return mk("option", { value: k, text: ICO[k] + " " + k }); }));
    var wantScrapRar = mk("select", { class: "akm-sel" }, SCRAP_RARITIES.map(function (rr) { return mk("option", { value: rr, text: rr + " scrap" }); }));
    var wantAmt = mk("select", { class: "akm-sel" });
    var wantScrapWrap = mk("div", { style: "display:none" }, wantScrapRar);
    giveKind.value = "wood"; wantKind.value = "gold";

    function fillAmt(sel, kind) { setKids(sel, (AMT_OPTS[kind] || [10]).map(function (v) { return mk("option", { value: String(v), text: fmtN(v) }); })); }
    function curGive() { return { kind: giveKind.value, rarity: giveKind.value === "scrap" ? giveScrapRar.value : undefined, amount: parseInt(giveAmt.value, 10) || 0 }; }
    function curWant() { return { kind: wantKind.value, rarity: wantKind.value === "scrap" ? wantScrapRar.value : undefined, amount: parseInt(wantAmt.value, 10) || 0 }; }

    var valEl = mk("div", { class: "akm-val" });
    function refresh() {
      giveScrapWrap.style.display = giveKind.value === "scrap" ? "block" : "none";
      wantScrapWrap.style.display = wantKind.value === "scrap" ? "block" : "none";
      var g = curGive(), w = curWant();
      var gv = goldValue(g), wv = goldValue(w);
      var verdict = (wv <= gv * MAKER_FILL_RATIO) ? "fair -- the market should take it fast" : "above market -- it may rest until a buyer bites";
      valEl.textContent = "You give ~" + fmtN(gv) + "g of value, you want ~" + fmtN(wv) + "g (" + verdict + ").";
    }
    fillAmt(giveAmt, giveKind.value); fillAmt(wantAmt, wantKind.value);
    giveKind.onchange = function () { fillAmt(giveAmt, giveKind.value); refresh(); };
    wantKind.onchange = function () { fillAmt(wantAmt, wantKind.value); refresh(); };
    [giveScrapRar, giveAmt, wantScrapRar, wantAmt].forEach(function (el) { el.onchange = refresh; });
    refresh();

    var postBtn = mk("button", { class: "akm-btn", style: "flex:1", text: "LIST OFFER" });
    postBtn.onclick = function () {
      var g = curGive(), w = curWant();
      if (g.kind === w.kind && (g.kind !== "scrap" || g.rarity === w.rarity)) { toast("Pick two different goods to trade."); return; }
      var gate = gateMsg(g); if (gate) { toast(gate); return; }
      postOffer(g, w, postBtn);
    };
    function gateMsg(g) {
      if (capLeft() <= 0) return "Daily cap reached (" + DAILY_CAP + ").";
      // AK-MKT 2026-07-18: standing-board cap (expired offers already released their slot).
      expireListings();
      if (activeCount() >= ACTIVE_CAP) return "You've got " + ACTIVE_CAP + " offers resting. Cancel one first.";
      var cd = cooldownLeft(); if (cd > 0) return "Quill's counting coin -- " + Math.ceil(cd / 1000) + "s.";
      if (!affordable(g)) return "You don't hold " + fmtItem(g) + ".";
      return "";
    }

    setKids(slot, mk("div", { class: "akm-card" }, [
      mk("div", { class: "akm-lbl", text: "You give" }), giveKind, giveScrapWrap, giveAmt,
      mk("div", { class: "akm-lbl", text: "You want" }), wantKind, wantScrapWrap, wantAmt,
      valEl,
      mk("div", { class: "akm-note", style: "padding:6px 2px", text: "Soft goods only -- wood, stone, metal, scrap, produce, gold. No gems, no cards, no $BCARDD. A " + Math.round(MARKET_TAX_PCT * 100) + "% market tax skims a filled sale." }),
      mk("div", { style: "display:flex;gap:8px;margin-top:6px" }, [ postBtn, mk("button", { class: "akm-btn ghost", text: "Back", onclick: function () { setTab("board"); } }) ])
    ]));
  }

  // ----- MINE: my open offers (server + local book) + cancel --------------- //
  function renderMine(slot) {
    fillRestingOffers();
    function paint(rows) {
      if (!S.root) return;
      var local = loadBook().mine.filter(function (L) { return L && L.status === "open"; }).map(function (L) { return { id: L.id, _src: "loc", seller_name: "you", give: L.give, want: L.want }; });
      var all = (rows || []).filter(isResListing).concat(local);
      if (!all.length) { setKids(slot, mk("div", { class: "akm-note", text: "No open offers. Post one from the SELL tab." })); return; }
      setKids(slot, all.map(function (L) { return offerRow(L, { label: "Cancel", danger: true, fn: cancelOffer }); }));
    }
    if (online()) {
      setKids(slot, mk("div", { class: "akm-note", text: "Loading your offers..." }));
      call(MARKET_FN, { action: "mine" }).then(function (r) { paint((r && r.ok) ? r.listings : []); });
    } else {
      paint([]);
    }
  }

  // ----------------------------------------------------------------------- //
  //  ACTIONS                                                                 //
  // ----------------------------------------------------------------------- //
  function postOffer(give, want, btn) {
    if (forbidden(give) || forbidden(want)) { toast("Those goods can't be traded here."); return; }
    if (!affordable(give)) { toast("You don't hold " + fmtItem(give) + "."); return; }
    expireListings();
    if (activeCount() >= ACTIVE_CAP) { toast("You've got " + ACTIVE_CAP + " offers resting. Cancel one first."); return; }
    if (btn) { btn.disabled = true; btn.textContent = "Listing..."; }
    // AK-MKT 2026-07-18: drip.js buy() order -- affordability CHECK above, then the ack, then
    // the debit. The give used to be deducted before the call, so a dropped response ate the
    // goods with no listing anywhere. Now each terminal branch debits exactly once, at the
    // moment the listing actually becomes real (server row, or committed local book entry).
    function restLocal(reason) {
      if (!affordable(give)) { toast("You don't hold " + fmtItem(give) + "."); if (btn) { btn.disabled = false; btn.textContent = "LIST OFFER"; } return; }
      deduct(give);                                // deposit / escrow the give as the row is written
      var id = "loc_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
      var t = Date.now();
      mutateBook(function (b) { b.mine.push({ id: id, _src: "loc", give: give, want: want, status: "open", t: t, expiresAt: t + LISTING_TTL_MS }); });
      logAction("post");
      fillRestingOffers();                         // a fair ask may clear immediately
      toast(reason || "Listed on the docks.");
      pushNow(); setTab("mine");
    }
    if (online()) {
      call(MARKET_FN, { action: "post", give: give, want: want, band: myBand(), name: myName() }).then(function (r) {
        if (r && r.ok) { deduct(give); logAction("post"); toast("Listed on the live market."); pushNow(); setTab("mine"); }
        else { restLocal(r && r.error === "offline" ? "Offline -- listed on your local book." : "Listed on your local book."); }   // server card-only today -> graceful local rest
      });
    } else {
      restLocal("Listed on your local book.");
    }
  }

  function acceptOffer(L, btn) {
    var cd = cooldownLeft(); if (cd > 0) { toast("Quill's counting coin -- " + Math.ceil(cd / 1000) + "s."); return; }
    if (capLeft() <= 0) { toast("Daily cap reached (" + DAILY_CAP + ")."); return; }
    if (!isResListing(L)) { toast("That offer can't be traded."); return; }
    if (!affordable(L.want)) { toast("You can't afford " + fmtItem(L.want) + "."); return; }
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    // NPC / local vendor liquidity -> instant atomic exchange (pay want, receive give).
    if (L._src === "npc") {
      deduct(L.want); credit(L.give);
      recordFill(L.give.kind, L.give.rarity, goldValue(L.want) / Math.max(1, L.give.amount | 0));   // P6: feed the float
      dropNpc(L.id); logAction("accept");
      try { if (!window._akStingT) window._akStingT = {}; var _ts = Date.now(); if ((window._akStingT.trade_done || 0) + 60000 < _ts) { window._akStingT.trade_done = _ts; if (window.akPlayCinematic) akPlayCinematic('trade_done'); } } catch (_e) {}  // STINGER (60s throttle -- high-frequency action)
      toast("Traded -- " + fmtItem(L.give) + " banked.");
      pushNow(); render();
      return;
    }
    // live server listing -> server-authoritative claim. AK-MKT 2026-07-18: pay AFTER the ack,
    // per drip.js buy(). The server's compare-and-swap is the only authority on who actually
    // wins a contested offer, so paying first meant every loser of that race ("offer was just
    // taken") had to be refunded -- and a dropped response refunded nobody. Now a rejected
    // claim costs nothing, so there is no refund path to get wrong.
    call(MARKET_FN, { action: "accept", listing_id: L.id, band: myBand() }).then(function (r) {
      if (r && r.ok) {
        deduct(L.want);
        applyGrants(r.grants && r.grants.length ? r.grants : [{ kind: L.give.kind, rarity: L.give.rarity, amount: L.give.amount }]);
        recordFill(L.give.kind, L.give.rarity, goldValue(L.want) / Math.max(1, L.give.amount | 0));   // P6: feed the float
        logAction("accept");
        try { if (!window._akStingT) window._akStingT = {}; var _ts = Date.now(); if ((window._akStingT.trade_done || 0) + 60000 < _ts) { window._akStingT.trade_done = _ts; if (window.akPlayCinematic) akPlayCinematic('trade_done'); } } catch (_e) {}  // STINGER (60s throttle -- high-frequency action)
        toast("Trade done -- " + fmtItem(L.give) + " is yours.");
        pushNow(); render();
      } else {
        toast(r && r.error === "offline" ? "Trade is offline -- nothing was charged." : ((r && r.error) || "Trade failed."));
        if (btn) { btn.disabled = false; btn.textContent = "Trade"; }
      }
    });
  }

  // accept a BOT population listing: instant atomic exchange identical to the NPC
  // vendor path. The listing is marked session-bought so it disappears from the
  // board -- the same bot's listing returns next hour under a new ID.
  function acceptBotListing(L, btn) {
    var cd = cooldownLeft(); if (cd > 0) { toast("Quill's counting coin -- " + Math.ceil(cd / 1000) + "s."); return; }
    if (capLeft() <= 0) { toast("Daily cap reached (" + DAILY_CAP + ")."); return; }
    if (!isResListing(L)) { toast("That offer can't be traded."); return; }
    if (!affordable(L.want)) { toast("You can't afford " + fmtItem(L.want) + "."); return; }
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    deduct(L.want);
    credit(L.give);
    recordFill(L.give.kind, L.give.rarity, goldValue(L.want) / Math.max(1, L.give.amount | 0));
    _boughtBotIds[L.id] = true;
    logAction("accept");
    try { if (!window._akStingT) window._akStingT = {}; var _ts = Date.now(); if ((window._akStingT.trade_done || 0) + 60000 < _ts) { window._akStingT.trade_done = _ts; if (window.akPlayCinematic) akPlayCinematic('trade_done'); } } catch (_e) {}  // STINGER (60s throttle -- high-frequency action)
    toast("Traded -- " + fmtItem(L.give) + " from " + (L.seller_name || "a dog") + " [" + (L.seller_clanName || "Stray") + "].");
    pushNow(); render();
  }

  function cancelOffer(L, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    if (L._src === "loc") {                         // local book entry -> pull + refund the deposited give
      var found = null;
      mutateBook(function (b) {
        for (var i = 0; i < b.mine.length; i++) { if (b.mine[i].id === L.id && b.mine[i].status === "open") { found = b.mine[i]; b.mine.splice(i, 1); break; } }
      });
      if (found) { credit(found.give); toast("Offer pulled -- your " + fmtItem(found.give) + " is back."); }
      pushNow(); render();
      return;
    }
    call(MARKET_FN, { action: "cancel", listing_id: L.id }).then(function (r) {
      if (r && r.ok) {
        applyGrants(r.grants && r.grants.length ? r.grants : [{ kind: L.give.kind, rarity: L.give.rarity, amount: L.give.amount }]);
        toast("Offer pulled -- your " + fmtItem(L.give) + " is back.");
        pushNow(); render();
      } else {
        toast(r && r.error === "offline" ? "Offline -- could not cancel." : ((r && r.error) || "Could not cancel."));
        if (btn) { btn.disabled = false; btn.textContent = "Cancel"; }
      }
    });
  }

  // ----------------------------------------------------------------------- //
  //  ROAMER: "Quill the Quartermaster" (mirrors trading.js's Switch broker)  //
  // ----------------------------------------------------------------------- //
  function seedKeeper(ctx) {
    if (S.keeper || !ctx || !ctx.world || !ctx.world.addRoamer) return;
    var wp0 = S.waypoints[0];
    S.keeper = ctx.world.addRoamer({
      id: "quill_quartermaster", zone: HOME_ZONE, x: wp0.x, y: wp0.y, r: 20,
      update: function (dt, self, c) {
        var w = S.waypoints[S.wp % S.waypoints.length];
        var dx = w.x - self.x, dy = w.y - self.y, d = Math.hypot(dx, dy) || 1;
        if (d < 18) { S.wp = (S.wp + 1) % S.waypoints.length; }
        else { self.x += (dx / d) * KEEPER_SPD * dt; self.y += (dy / d) * KEEPER_SPD * dt; }
        self._face = dx < 0 ? -1 : 1;
        if (S.uiOpen) return;
        var pd = c.world.distToMe(self.x, self.y);
        self._near = pd < TRIGGER_R * 1.5;
        if (S.entryLock) { if (pd > TRIGGER_R + 40) S.entryLock = false; return; }
        if (pd < TRIGGER_R) { try { ctxBanner(c, "Quill the Quartermaster -- the bazaar"); } catch (_) {} openMarket(); }
      },
      draw: function (g, self, c) {
        var X = c.world.wx(self.x), Y = c.world.wy(self.y), r = self.r;
        g.save();
        g.fillStyle = "rgba(0,0,0,.34)"; g.beginPath(); g.ellipse(X, Y + r + 2, r * .8, 4.5, 0, 0, 7); g.fill();
        g.beginPath(); g.arc(X, Y, r, 0, 7);
        g.fillStyle = "#15130f"; g.fill();
        g.lineWidth = 2.4; g.strokeStyle = "#e8c55a"; g.shadowColor = "#c9a84c"; g.shadowBlur = 10; g.stroke(); g.shadowBlur = 0;
        g.fillStyle = "#e8c55a"; g.font = "700 16px Inter,sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText("⚖️", X, Y + 1);
        g.fillStyle = "#e8c55a"; g.font = "700 10px Inter,sans-serif"; g.textBaseline = "alphabetic";
        g.fillText("QUILL", X, Y - r - 6);
        if (self._near) {
          var bob = Math.sin((performance.now() / 220)) * 2;
          g.fillStyle = "rgba(12,12,18,.9)"; roundRect(g, X - 34, Y - r - 34 + bob, 68, 16, 5); g.fill();
          g.strokeStyle = "rgba(201,168,76,.6)"; g.lineWidth = 1; g.stroke();
          g.fillStyle = "#7CFFb0"; g.font = "700 9px Inter,sans-serif"; g.textAlign = "center";
          g.fillText("⚖️ BAZAAR", X, Y - r - 23 + bob);
        }
        g.restore();
      }
    });
  }
  function roundRect(g, x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
  function ctxBanner(c, t) { if (c && c.showBanner) c.showBanner(t, 0.6); }

  // ----------------------------------------------------------------------- //
  //  MODULE REGISTRATION                                                     //
  // ----------------------------------------------------------------------- //
  global.AK_SYSTEMS.register({
    id: "marketplace",
    init: function (ctx) {
      CTX = ctx || global.AK_CTX || CTX;
      if (S.seeded) return; S.seeded = true;
      try { seedKeeper(CTX); } catch (_e) {}
    },
    onEnterBuilding: function (b, ctx) { return false; },   // the bazaar owns NO building (roamer + overlay only)
    // AK-MKT 2026-07-18: a resting offer ages on a wall clock, so expiry cannot wait for the
    // player to walk back to the docks -- goods would sit stranded past their TTL. Sweep on
    // the hub tick, throttled to once a minute so the 60fps budget never sees it. Guarded and
    // panel-independent: with no offers on the book both calls are a loadBook + early return.
    onTick: function (dt, ctx) {
      CTX = ctx || CTX;                                     // patrol + proximity live on the roamer (host-driven)
      S.sweepT = (S.sweepT || 0) + (dt || 0);
      if (S.sweepT < 60) return;
      S.sweepT = 0;
      try { expireListings(); fillRestingOffers(); } catch (_e) {}
    },
    onDrawWorld: function (ctx) {}                           // the keeper draws itself via the roamer
  });

  // entry points: the orchestrator wires window.akOpenMarket onto a HUD chip / keeper.
  // ENHANCED akOpenMarket(tab) accepts an optional tab ("board"|"post"|"orders"|"mine"|"launder");
  // the new "orders" tab is the P8 raid-fed buy-order board, and the "board" tab now
  // rides the P6 floating-price ticker tape.
  global.akOpenMarket = openMarket;
  // P6 floating-price reads for the integration pass (HUD chips, raid-result screens).
  global.AKMarket = {
    open: openMarket, close: closeMarket,
    price: function (kind, rarity) { return unitPrice(kind, rarity); },   // live floating gold-per-unit
    value: goldValue,                                                     // ({kind,rarity,amount}) -> floating gold value
    ticker: function () { return TICKER_KINDS.map(function (t) { return { kind: t.kind, rarity: t.rarity, price: unitPrice(t.kind, t.rarity), demand: outstandingDemand(t.kind, t.rarity) }; }); },
    // AK-MKT 2026-07-18: rolling price history off economy.js's own fill ring.
    // history(kind, rarity?) -> {n, series[], avg, min, max, last, now, cap} -- everything a
    // sparkline needs. tape() is the same over every ticker good, for a whole-board graph.
    history: priceHistory,
    tape: function () { return TICKER_KINDS.map(function (t) { return priceHistory(t.kind, t.rarity); }); },
    // the BACKPACK-derived taxonomy the board browses by (one taxonomy, two screens).
    cats: marketCats,
    catOf: catOf,
    // browse(rows, {cat, sort}) -> the same filter+sort the board tab runs, for any other
    // surface that wants a slice of the book (a HUD "best wood deals" chip, a raid-result
    // upsell) without reimplementing the comparators.
    browse: function (rows, o) { o = o || {}; return sortListings((rows || []).filter(function (L) { return listingInCat(L, o.cat || "all"); }), o.sort || "deal"); },
    sorts: function () { return SORTS.slice(); },
    // my resting local offers + the standing-board cap, for a HUD badge.
    mine: function () { return loadBook().mine.filter(function (L) { return L && L.status === "open"; }); },
    activeCap: function () { return { open: activeCount(), cap: ACTIVE_CAP, ttlMs: LISTING_TTL_MS }; },
    // sweep expiries + fair-ask fills WITHOUT opening the panel. Offers age on a wall clock
    // while the bazaar is closed, so a daily-reset / hub-tick caller needs this to hand goods
    // back on time instead of stranding them until the player next walks to the docks.
    sweep: function () { return { expired: expireListings(), filled: fillRestingOffers() }; }
  };
  // THE FENCE contract -- raid / steal / world systems plug in here.
  //  (a) HOT loot: push raided goods as HOT; they must be laundered (cut + delay)
  //      before they spend clean. deposit() works panel-open or closed.
  //  (b) P8 BUY-ORDER SINK: a raided / damaged DISTRICT posts demand for the
  //      fortify mats it lost (wood/stone/scrap) via postRaidDemand(district, needs?,
  //      severity?). That spikes those Fence prices AND lets harvesters sell in at a
  //      premium -- raids destroy -> demand -> price up -> harvesters profit.
  global.AKFence = {
    deposit: depositLoot,
    list: hotList,
    total: function () { return { piles: hotList().length, gold: Math.round(hotGold()) }; },
    // launder mutators (also driven by the WASH tab buttons) -- a raid-result screen
    // can offer "launder now" / "rush" directly. claim() only pays out once washed.
    launder: startWash, rush: rushWash, claim: claimWash,
    open: function () { openMarket("launder"); },
    // --- P8 raid-fed buy-order sink ---
    postRaidDemand: postRaidDemand,   // (district, needs?|severity, severity?) -> post a gutted block's mat demand
    orders: openBuyOrders,            // () -> all open buy-orders (seeded + raid-fed)
    demand: outstandingDemand,        // (kind, rarity?) -> outstanding units demanded (drives the price spike)
    sellTo: fillBuyOrder,             // (id) -> sell what you hold into an order for premium gold
    openOrders: function () { openMarket("orders"); }
  };

})(typeof window !== "undefined" ? window : globalThis);
