/* game/systems/trading.js -- AK_SYSTEMS module (wave 6: TRADING).
   ==========================================================================
   ALLEY KINGZ // THE TRADING POST -- keeper "Switch the Broker"
   A Sunflower-Land-style player BARTER POST. Walk the broker down in THE YARDS
   -> a barter board opens. List a SPARE CARD (or cosmetic) for gold / scrap or
   trade card-for-card. Server-escrowed via the NEW ak-trading edge fn (mirrors
   ak-crew's server-authoritative grant pattern). SOFT items ONLY.

   HARD LAW honored here:
   - Soft-currency + card-copy + cosmetic barter ONLY. NO gems (server-only,
     grant('gems') is a no-op). NO $BCARDD / ALK in any leg of a trade -- that is
     the RMT / securities line and is hard-rejected client AND server side.
     ($BCARDD is also a Mythic card, and ALL Mythic cards are blocked from trade.)
   - Reuses the 106 cards BY NAME (ctx.cards() -> canon roster) as the only stock.
     Never invents a placeholder unit. Broker flavor name-drops the 6 handlers.
   - Additive: registers into window.AK_SYSTEMS, adds ONE roamer, opens its UI as a
     fresh overlay + DOM panel. Edits NO shared file. New player-state lives behind
     the falsy-default `trades` field (added once by the Lead in economy.js 6.B).
   - Headless-safe: no top-level DOM / localStorage; all storage via AK_ECON.

   Theme: gritty gold cyberpunk dog-gang street culture. "crew" never "clan".
   XSS-safe by construction (mk() builder -> textContent only, no innerHTML).
   No em-dashes (use --). No bundler. Plain browser JS (no TS).
   ========================================================================== */
(function (global) {
  "use strict";
  if (!global.AK_SYSTEMS) return;                 // hub-only module; bail where the registry is absent

  // ----------------------------------------------------------------------- //
  //  CONSTANTS (gates + economy knobs -- the server re-enforces these)       //
  // ----------------------------------------------------------------------- //
  var TRADE_FN   = "ak-trading";                  // NEW edge fn (spec at the bottom; NOT deployed yet). Contract manifest alias: ak-trade.
  var HOME_ZONE  = "THE_YARDS";                   // the broker roams the gritty yards (barter district)
  var MIN_TH     = 3;                             // min Town Hall level to use the post (anti-fresh-account abuse)
  var DAILY_CAP  = 5;                             // posts + accepts per local day
  // AK-MKT 2026-07-18: cap CONCURRENT open offers (DAILY_CAP throttles rate, not board spam).
  // The server has no active-offer cap, so this is client-side board hygiene only.
  var ACTIVE_CAP = 3;                             // max simultaneously-open offers per player
  var BAND_SIZE  = 400;                           // trophy-band width -- you only trade with your own bracket
  var COOLDOWN_MS = 8000;                         // anti-spam cooldown between broker actions
  var TRIGGER_R  = 72;                            // walk this close to Switch -> the post opens
  var BROKER_SPD = 62;                            // patrol px/s
  // gold "tax" gates -- a pure sink (never refunded on success), keeps the economy honest.
  var POST_FEE   = { Common: 10, Rare: 25, Epic: 60, Legendary: 150 };  // listing fee by GIVE-card rarity (gold)
  var ACCEPT_FEE = 12;                            // broker's cut to accept an offer (gold)
  var GOLD_WANT_OPTS = [50, 100, 200, 400, 800];  // bounded gold asking-price presets (no abusive numbers)
  var SCRAP_WANT_OPTS = [4, 8, 16, 32];           // bounded scrap asking-amount presets
  var TRADE_RARITIES = ["Common", "Rare", "Epic", "Legendary"]; // Mythic is NEVER tradeable (prestige + parity + $BCARDD guard)

  // Minimal REAL-roster fallback (canon names + rarities) used ONLY if ctx.cards()
  // is empty (the hub does not load engine.js) and the canon fetch has not landed.
  // These are real Alley Kingz cards -- never generic placeholders.
  var EMBEDDED_ROSTER = {
    "$BCARDD": "Mythic", "Jagged": "Mythic", "Rosco": "Mythic", "Crown Foxhound": "Mythic",
    "Stonejaw": "Legendary",
    "Balboa": "Epic", "Iron Rottweiler": "Epic", "Razor Vizsla": "Epic",
    "Granite Saint": "Rare", "Grit Bulldog": "Rare", "Alloy Akita": "Rare", "Warden Newfie": "Rare",
    "Rust Cane Corso": "Rare", "Pixel Greyhound": "Rare", "Circuit Shiba": "Rare", "Bolt Corgi": "Rare",
    "Flash Saluki": "Rare",
    "Tank Pug": "Common", "Copper Chow": "Common", "Brick Bullmastiff": "Common",
    "Neon Whippet": "Common", "Turbo Jack": "Common"
  };
  // The 6 commanders -- name-dropped in broker flavor so the world feels lived-in.
  var HANDLER_NAMES = ["The Mender", "The Tracker", "The Shadow", "The Rigger", "The Bruiser", "The Dealer"];
  var BROKER_LINES = [
    "Switch the Broker. Everything's got a price, mutt -- card for card, coin for coin.",
    "The Mender's been sniffin' around for a Granite Saint. You holdin'?",
    "Trade smart. The Rigger paid double for a spare Bolt Corgi last week.",
    "No crypto at my table. Soft goods only -- that's how Switch stays free.",
    "The Tracker says your bracket's hot right now. Post somethin' before it cools.",
    "Cards, scrap, gold. No $BCARDD, no funny money. Keep it clean and we both eat."
  ];

  // ----------------------------------------------------------------------- //
  //  STATE                                                                   //
  // ----------------------------------------------------------------------- //
  var CTX = null;
  var S = {
    seeded: false, uiOpen: false, entryLock: false,
    ovApi: null, root: null, bodyEl: null, toastEl: null,
    tab: "board", cardIdx: null, idxLoading: false,
    listings: [], mine: [], lastBand: 0,
    // AK-MKT 2026-07-18: board browse state (category filter + sort order) and the cached
    // read-only preview board a signed-out dog reads instead of hitting a sign-in wall.
    browseCat: "all", browseSort: "new", preview: [], previewAt: -1,
    broker: null, wp: 0,
    waypoints: [ { x: 320, y: 320 }, { x: 1380, y: 320 }, { x: 1380, y: 980 }, { x: 320, y: 980 } ]
  };

  // ----------------------------------------------------------------------- //
  //  HELPERS -- identity + economy + server (mirrors social.js)              //
  // ----------------------------------------------------------------------- //
  function econ() { try { return global.AK_ECON || (CTX && CTX.econ) || null; } catch (_) { return null; } }
  function prof() { var e = econ(); return e ? e.loadProfile() : null; }
  function sbc()  { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me()   { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function myId() { var u = me(); return (u && u.id) || null; }
  function myName(){ try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24); } catch (_) { return "Stray"; } }

  // edge-fn call (functions.invoke; auto-attaches JWT). Degrades to {ok:false} offline.
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

  // apply a single server grant to the LOCAL economy (mirror of social.js applyGrant).
  function applyGrant(g) {
    var e = econ(); if (!e || !g) return false;
    try {
      if (g.kind === "card" && g.card_id) e.addCopy(g.card_id, g.amount || 1);
      else if (g.kind === "gold" || g.kind === "coins") e.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins || 0) + (g.amount || 0)); });
      else if (g.kind === "scrap" && g.rarity) e.addScrap(g.rarity, g.amount || 0);
      else if (g.kind === "keys") e.addKeys(g.amount || 0);
      else if (g.kind === "chest") e.grantChest(g.card_id || "wood", g.amount || 1);
      else return false;
      return true;
    } catch (_) { return false; }
  }
  function applyGrants(arr) { var n = 0; (arr || []).forEach(function (g) { if (applyGrant(g)) n++; }); if (n) { try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {} } return n; }
  // pull any queued grants (poster's payment lands here next session). // TODO-SERVER: ak-trading claim-grants
  function claimGrants() {
    if (!me() || !econ()) return Promise.resolve(0);
    return call(TRADE_FN, { action: "claim-grants" }).then(function (r) {
      if (!r || !r.ok || !r.grants || !r.grants.length) return 0;
      return applyGrants(r.grants);
    });
  }

  // ----------------------------------------------------------------------- //
  //  CARD INDEX -- ctx.cards() first, canon fetch second, embedded last      //
  // ----------------------------------------------------------------------- //
  function buildIdxFrom(cards) {
    var m = {};
    for (var k in cards) { var c = cards[k]; if (c && (c.name || k)) m[c.name || k] = { rarity: c.rarity || "Common", faction: c.class || c.faction || "", cost: c.cost || 0 }; }
    return m;
  }
  function ensureCardIdx() {
    if (S.cardIdx) return;
    // 1) the contract resolver
    try { var c = CTX && CTX.cards && CTX.cards(); if (c && Object.keys(c).length) { S.cardIdx = buildIdxFrom(c); return; } } catch (_) {}
    // 3) seed with the embedded real roster so the UI is never empty
    if (!S.cardIdx) { S.cardIdx = {}; for (var n in EMBEDDED_ROSTER) S.cardIdx[n] = { rarity: EMBEDDED_ROSTER[n], faction: "", cost: 0 }; }
    // 2) async upgrade to the full canon (the hub does not load engine.js)
    if (S.idxLoading || typeof fetch !== "function") return;
    S.idxLoading = true;
    var tries = ["../data/cards.json", "data/cards.json", "./data/cards.json"];
    (function next(i) {
      if (i >= tries.length) { S.idxLoading = false; return; }
      fetch(tries[i]).then(function (r) { return r.ok ? r.json() : Promise.reject(0); }).then(function (j) {
        var arr = (j && j.cards) || []; var m = {};
        arr.forEach(function (c) { if (c && c.name) m[c.name] = { rarity: c.rarity || "Common", faction: c.class || "", cost: c.cost || 0 }; });
        if (Object.keys(m).length) S.cardIdx = m;
        S.idxLoading = false;
      }, function () { next(i + 1); });
    })(0);
  }
  function rarOf(name) { var r = S.cardIdx && S.cardIdx[name] && S.cardIdx[name].rarity; return r || EMBEDDED_ROSTER[name] || "Rare"; }
  function isTradeableCard(name) { return name && rarOf(name) !== "Mythic" && !/\$|bcardd|alk/i.test(name); }
  // every name in the canon (excluding Mythics + forbidden) -- the want-a-card universe
  function allTradeNames() {
    var src = (S.cardIdx && Object.keys(S.cardIdx).length) ? Object.keys(S.cardIdx) : Object.keys(EMBEDDED_ROSTER);
    return src.filter(isTradeableCard).sort();
  }
  // cards I OWN with a spare copy to give (real owned names, non-Mythic)
  function myGiveables() {
    var p = prof(); if (!p) return [];
    return (p.owned || []).filter(function (n) { return isTradeableCard(n) && cardCopies(n) >= 1; }).sort();
  }
  function cardCopies(name) { var e = econ(), p = prof(); try { return e && e.cardCopies ? e.cardCopies(p, name) : Math.max(0, (p && p.copies && p.copies[name]) | 0); } catch (_) { return 0; } }

  // ----------------------------------------------------------------------- //
  //  GATES                                                                   //
  // ----------------------------------------------------------------------- //
  function townHall() { var e = econ(); try { return e && e.townHallLevel ? e.townHallLevel() : 1; } catch (_) { return 1; } }
  function myTrophies() { var p = prof(); return (p && p.trophies | 0) || 0; }
  function myBand() { return Math.floor(myTrophies() / BAND_SIZE); }
  function bandLabel(b) { return (b * BAND_SIZE) + "-" + (b * BAND_SIZE + BAND_SIZE - 1) + " trophies"; }
  function todayKey() { var d = new Date(); return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }
  function tradesToday() {
    var p = prof(); if (!p || !p.trades || !Array.isArray(p.trades.sent)) return 0;
    var day = todayKey();
    return p.trades.sent.filter(function (s) { return s && s.day === day && (s.type === "post" || s.type === "accept"); }).length;
  }
  function capLeft() { return Math.max(0, DAILY_CAP - tradesToday()); }
  function cooldownLeft() { var p = prof(); var u = (p && p.trades && p.trades.cooldownUntil) | 0; return Math.max(0, u - Date.now()); }
  function logTrade(type, id) {
    var e = econ(); if (!e) return;
    e.mutateProfile(function (p) {
      if (!p.trades || typeof p.trades !== "object") p.trades = { sent: [], cooldownUntil: 0 };
      if (!Array.isArray(p.trades.sent)) p.trades.sent = [];
      p.trades.sent.push({ t: Date.now(), day: todayKey(), type: type, id: id || null });
      // prune: keep last 60 / last 48h
      var cut = Date.now() - 48 * 3600 * 1000;
      p.trades.sent = p.trades.sent.filter(function (s) { return s && s.t > cut; }).slice(-60);
      p.trades.cooldownUntil = Date.now() + COOLDOWN_MS;
    });
  }

  // ----------------------------------------------------------------------- //
  //  ESCROW (client side of the deposit) -- soft items only                  //
  //  Inventory is client-side localStorage today, so a LIST/ACCEPT deposits  //
  //  locally; the server records the listing + matchmakes + delivers via     //
  //  ak_grants. AK-MKT 2026-07-18: the deposit now happens AFTER the server  //
  //  ack (canDepositAll -> call -> depositAll), matching drip.js buy(). That //
  //  retires the old refund-on-failure path: a rejected or dropped call now  //
  //  charges NOTHING, instead of charging and then trying to put it back.    //
  //  refundItem / refundAll are kept for the local-escrow path that lands    //
  //  with server-held inventory. // TODO-SERVER: real escrow moves this.     //
  // ----------------------------------------------------------------------- //
  function cur() { return CTX && CTX.currency; }
  function forbidden(item) { // hard parity / RMT guard
    if (!item) return true;
    if (item.kind === "gems") return true;
    if (item.kind === "card") return !isTradeableCard(item.card_id);
    if (item.kind === "scrap") return item.rarity === "Mythic"; // block the Mythic scrap leg; Common..Legendary ok
    return false;
  }
  function affordable(item) {
    var c = cur(); if (!c) return false;
    if (item.kind === "gold") return c.get("gold") >= (item.amount | 0);
    if (item.kind === "scrap") return c.get("scrap", item.rarity) >= (item.amount | 0);
    if (item.kind === "card") return cardCopies(item.card_id) >= (item.amount | 0);
    return false;
  }
  function deduct(item) {
    var c = cur(), e = econ();
    if (item.kind === "gold") c.grant("gold", -(item.amount | 0));
    else if (item.kind === "scrap") e.addScrap(item.rarity, -(item.amount | 0));
    else if (item.kind === "card") e.mutateProfile(function (p) { p.copies[item.card_id] = Math.max(0, (p.copies[item.card_id] | 0) - (item.amount | 0)); });
  }
  function refundItem(item) {
    var c = cur(), e = econ();
    if (item.kind === "gold") c.grant("gold", item.amount | 0);
    else if (item.kind === "scrap") e.addScrap(item.rarity, item.amount | 0);
    else if (item.kind === "card") e.addCopy(item.card_id, item.amount | 0);
  }
  // AK-MKT 2026-07-18: check-only half of depositAll, so a caller can gate BEFORE the
  // server call and debit only after the ack (the drip.js buy() order: check -> ack -> debit).
  function canDepositAll(items) {
    for (var i = 0; i < items.length; i++) { if (forbidden(items[i])) return { ok: false, error: "FORBIDDEN_ITEM" }; if (!affordable(items[i])) return { ok: false, error: "CANT_AFFORD" }; }
    return { ok: true };
  }
  // atomically deposit a basket (check ALL first; then deduct). Returns {ok, error}.
  function depositAll(items) {
    var chk = canDepositAll(items); if (!chk.ok) return chk;
    items.forEach(deduct);
    return { ok: true };
  }
  function refundAll(items) { items.forEach(refundItem); }

  // ----------------------------------------------------------------------- //
  //  AK-MKT 2026-07-18: BROWSE -- category taxonomy + sorts                  //
  //  backpack.js already owns the categories the player reads (ITEMS[].cat   //
  //  over MATERIALS / CURRENCY / GEAR / CARDS). The post used to dump every  //
  //  offer into one flat list, and inventing a second taxonomy here would    //
  //  file the same scrap under two different headings in two screens. So     //
  //  this DEFERS to AK_BACKPACK at CALL time (it loads AFTER this file in    //
  //  index.html, so a load-time read is undefined) and mirrors its cats when //
  //  the bag is absent (headless). Every offer GIVES a card, so a row is     //
  //  filed by what it ASKS for -- the axis a browser actually picks along.   //
  // ----------------------------------------------------------------------- //
  var CAT_FALLBACK = { gold: "currency", scrap: "materials", card: "cards" };
  var WANT_KINDS_UI = ["gold", "scrap", "card"];   // the legs the post accepts as payment
  function bp() { try { return global.AK_BACKPACK || null; } catch (_) { return null; } }
  // kind -> bag category id. Only trust the bag for kinds it genuinely registers: its own
  // def() answers "materials" for anything unknown, which would mis-file a cosmetic leg.
  function catOf(kind) {
    if (kind === "cosmetic") return "gear";        // the bag has no cosmetic row yet
    var b = bp();
    try { if (b && b.ITEMS && b.ITEMS[kind] && b.ITEMS[kind].cat) return b.ITEMS[kind].cat; } catch (_) {}
    return CAT_FALLBACK[kind] || "cards";
  }
  // the tabs the board offers: ALL + only the categories the post actually deals in,
  // in the bag's own declared order so the two screens read identically.
  function tradeCats() {
    var b = bp(), live = {}, out = [ { id: "all", label: "ALL" } ];
    WANT_KINDS_UI.forEach(function (k) { live[catOf(k)] = 1; });
    var src = (b && Array.isArray(b.CATS) && b.CATS.length) ? b.CATS
            : [ { id: "materials", label: "MATERIALS" }, { id: "currency", label: "CURRENCY" }, { id: "cards", label: "CARDS" } ];
    src.forEach(function (c) { if (c && live[c.id]) out.push({ id: c.id, label: c.label }); });
    return out;
  }
  function listingInCat(L, cat) {
    if (!cat || cat === "all") return true;
    if (!L || !L.want) return false;
    return catOf(L.want.kind) === cat;
  }

  // Sort-only value. This orders ROWS and NEVER prices a trade: no payout, fee, tax or
  // grant reads it. Gold/scrap defer to the live bazaar quote (AKMarket.value) so both
  // boards rank the same goods identically; a card is ranked off the listing-fee rarity
  // ladder (POST_FEE), the only rarity->gold curve this module already owns.
  var CARD_SORT_MULT = 6;
  function sortValue(it) {
    if (!it) return 0;
    if (it.kind === "card") return (POST_FEE[it.rarity] || POST_FEE.Rare) * CARD_SORT_MULT * Math.max(1, it.amount | 0);
    try {
      if (global.AKMarket && typeof global.AKMarket.value === "function") {
        var v = global.AKMarket.value(it); if (isFinite(v) && v > 0) return v;
      }
    } catch (_) {}
    if (it.kind === "gold") return it.amount | 0;
    return (it.amount | 0) * 5;
  }
  var SORTS = [
    { id: "new",   label: "NEWEST" },
    { id: "cheap", label: "CHEAPEST" },
    { id: "rich",  label: "BIGGEST" },
    { id: "rar",   label: "BY RARITY" }
  ];
  var RAR_ORDER = { Legendary: 0, Epic: 1, Rare: 2, Common: 3 };
  function rarRank(it) { var r = RAR_ORDER[it && it.rarity]; return r == null ? 9 : r; }
  function sortListings(rows, id) {
    var a = (rows || []).slice();
    if (id === "cheap") a.sort(function (x, y) { return sortValue(x.want) - sortValue(y.want); });
    else if (id === "rich") a.sort(function (x, y) { return sortValue(y.give) - sortValue(x.give); });
    else if (id === "rar") a.sort(function (x, y) { return rarRank(x.give) - rarRank(y.give); });
    else a.sort(function (x, y) { return String(y.created_at || "").localeCompare(String(x.created_at || "")); });
    return a;
  }

  // ----------------------------------------------------------------------- //
  //  AK-MKT 2026-07-18: READ-ONLY PREVIEW BOARD (signed-out)                 //
  //  ak-trading verifies a JWT on EVERY action, "list" included, so a signed //
  //  -out dog cannot read the real board at all. The old behaviour was a     //
  //  hard sign-in wall over the WHOLE post, which hides the one screen that  //
  //  explains why signing in is worth anything. So we show the SHAPE of the  //
  //  market instead: deterministic sample offers off the same bot roster     //
  //  Street Talk uses, hour-bucketed exactly like population.js's own        //
  //  marketListings, badged "sample board", and never acceptable -- a        //
  //  preview row has no accept path at all, so no client-side mint exists.   //
  //  // TODO-SERVER: a REAL signed-out board needs a public read on the edge //
  //  // fn -- action "list-public", payload {band}, skipping the JWT check   //
  //  // and returning the same rowToListing shape minus seller_id.           //
  // ----------------------------------------------------------------------- //
  function hourBucket() { return Math.floor(Date.now() / 3600000); }
  // tiny deterministic hash: no Math.random, so the preview is stable within the hour and
  // identical on every device (parity-safe, and nothing about it is ever persisted).
  function pvHash(a, b) {
    var h = (Math.imul((a | 0) + 1, 0x9E3779B9) ^ Math.imul((b | 0) + 1, 0x6C62272E)) >>> 0;
    h ^= h >>> 15; return Math.imul(h, 0x2545F491) >>> 0;
  }
  function previewListings() {
    var bucket = hourBucket();
    if (S.preview.length && S.previewAt === bucket) return S.preview;
    var names = allTradeNames();
    if (!names.length) return [];
    var roster = [];
    try { var pop = global.AK_POPULATION; if (pop && typeof pop.roster === "function") roster = pop.roster() || []; } catch (_) {}
    var out = [];
    for (var i = 0; i < 6; i++) {
      var h = pvHash(i, bucket);
      var give = names[h % names.length], want;
      var roll = (h >>> 8) % 3;
      if (roll === 0) want = { kind: "gold", amount: GOLD_WANT_OPTS[(h >>> 12) % GOLD_WANT_OPTS.length] };
      else if (roll === 1) want = { kind: "scrap", rarity: TRADE_RARITIES[(h >>> 12) % TRADE_RARITIES.length], amount: SCRAP_WANT_OPTS[(h >>> 16) % SCRAP_WANT_OPTS.length] };
      else {
        var wn = names[(h >>> 12) % names.length];
        if (wn === give) continue;                 // never show a card-for-itself sample
        want = { kind: "card", card_id: wn, rarity: rarOf(wn), amount: 1 };
      }
      var dog = roster.length ? roster[(h >>> 20) % roster.length] : null;
      out.push({
        id: "pv_" + i + "_" + bucket, _src: "preview", seller_id: null,
        seller_name: (dog && dog.name) || "Stray",
        give: { kind: "card", card_id: give, rarity: rarOf(give), amount: 1 },
        want: want, band: myBand(), status: "open", created_at: ""
      });
    }
    S.preview = out; S.previewAt = bucket;
    return out;
  }

  // ----------------------------------------------------------------------- //
  //  DOM (XSS-safe builder; mirrors social.js mk/setKids)                    //
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

  function injectCss() {
    if (document.getElementById("ak-trade-css")) return;
    var st = document.createElement("style"); st.id = "ak-trade-css";
    st.textContent = [
      "#ak-trade{position:fixed;inset:0;z-index:46;display:none;flex-direction:column;background:linear-gradient(180deg,#0c0b08,#08080c);color:#e9e9ee;font-family:Inter,system-ui,sans-serif}",
      "#ak-trade.open{display:flex}",
      ".akt-top{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,.22)}",
      ".akt-glyph{font-size:26px;line-height:1}",
      ".akt-ttl{flex:1}.akt-ttl h2{margin:0;font-size:16px;letter-spacing:1px;color:#e8c55a;font-family:Cinzel,serif}",
      ".akt-ttl .sub{color:#9a8f6a;font-size:11px}",
      ".akt-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".akt-line{padding:8px 14px;color:#cfc7a8;font-size:12px;font-style:italic;border-bottom:1px solid rgba(201,168,76,.1)}",
      ".akt-tabs{display:flex;gap:6px;padding:8px 12px}",
      ".akt-tab{flex:1;padding:9px;border-radius:9px;border:1px solid rgba(201,168,76,.22);background:rgba(255,255,255,.03);color:#cfcfd6;font-weight:700;font-size:12px;letter-spacing:.5px;cursor:pointer}",
      ".akt-tab.on{background:rgba(201,168,76,.16);color:#e8c55a;border-color:rgba(201,168,76,.5)}",
      ".akt-meta{display:flex;gap:8px;padding:0 12px 8px;font-size:11px;color:#9a9aa6}",
      ".akt-meta b{color:#e8c55a}",
      ".akt-body{flex:1;overflow-y:auto;padding:8px 12px;-webkit-overflow-scrolling:touch}",
      ".akt-card{background:linear-gradient(165deg,#15131c,#0b0b10);border:1px solid #2a2620;border-radius:10px;padding:12px;margin-bottom:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.045),inset 0 -14px 20px rgba(0,0,0,.32)}",
      ".akt-li{display:flex;align-items:center;gap:10px;padding:10px 4px;border-bottom:1px solid #211e19}",
      ".akt-give{color:#7CFFb0;font-weight:800}.akt-want{color:#e8c55a;font-weight:800}.akt-arrow{color:#6f6a5a;font-weight:900}",
      ".akt-nm{font-weight:800;color:#fff;font-size:13px}.akt-sub{color:#9a9aa6;font-size:11px}",
      // AK-ART 2026-07-01: real card portraits + resource-chip legs + card-art give-picker
      ".akt-offer{align-items:center;gap:11px}",
      ".akt-offmid{flex:1;min-width:0}",
      ".akt-trade{display:flex;align-items:center;gap:10px;flex-wrap:wrap}",
      ".akt-leg{display:inline-flex;align-items:center;gap:7px;min-width:0}",
      ".akt-av{flex:0 0 auto;border-radius:9px;overflow:hidden;border:1.5px solid #c9a84ccc;background:radial-gradient(circle at 50% 34%,rgba(201,168,76,.2),rgba(10,10,16,.92));display:flex;align-items:center;justify-content:center;line-height:1}",
      ".akt-av img{width:100%;height:100%;object-fit:cover;object-position:center top}",
      ".akt-legtx{display:flex;flex-direction:column;min-width:0}",
      ".akt-legnm{font-weight:800;color:#f0ead9;font-size:12px;max-width:118px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".akt-legsub{font-size:10px;color:#9a8f6a;font-weight:700;letter-spacing:.03em;text-transform:uppercase}",
      ".akt-chip{display:inline-flex;align-items:center;gap:3px;font-variant-numeric:tabular-nums}",
      ".akt-ri{object-fit:contain;vertical-align:middle;filter:drop-shadow(0 1px 1px rgba(0,0,0,.55))}",
      ".akt-ri-g{font-size:16px;line-height:1}",
      ".akt-amt{font-weight:800}",
      ".akt-rar{font-size:10px;color:#b9ad84;font-weight:700;letter-spacing:.04em;text-transform:uppercase}",
      ".akt-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:6px 0}",
      ".akt-tile{position:relative;display:flex;flex-direction:column;align-items:center;gap:5px;padding:8px 5px;border-radius:12px;cursor:pointer;-webkit-tap-highlight-color:transparent;border:1.5px solid rgba(201,168,76,.28);background:rgba(20,18,26,.85);transition:transform .1s ease}",
      ".akt-tile.on{background:rgba(201,168,76,.15)}",
      ".akt-tile:active{transform:scale(.97)}",
      ".akt-tilenm{font-size:10px;font-weight:800;color:#d9c688;line-height:1.15;text-align:center;max-width:82px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".akt-tilesub{font-size:9px;font-weight:800}",
      ".akt-btn{background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#1a1405;border:0;border-radius:9px;padding:10px 14px;font-weight:800;letter-spacing:.5px;cursor:pointer}",
      ".akt-btn.ghost{background:rgba(255,255,255,.05);color:#e9e9ee;border:1px solid rgba(255,255,255,.16)}",
      ".akt-btn.dng{background:rgba(220,80,80,.16);color:#f3a0a0;border:1px solid rgba(220,80,80,.3)}",
      ".akt-btn:active{transform:scale(.97)}.akt-btn[disabled]{opacity:.5;cursor:not-allowed}",
      ".akt-inp,.akt-sel{width:100%;box-sizing:border-box;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.14);color:#fff;border-radius:9px;padding:10px;margin:5px 0;font-size:14px}",
      ".akt-lbl{color:#9a8f6a;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-top:8px}",
      ".akt-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px 8px;line-height:1.5}",
      ".akt-fee{color:#e8c55a;font-size:12px;text-align:center;margin:6px 0}",
      // AK-MKT 2026-07-18: browse controls + the read-only gate banner (a strip above the
      // content, never a wall in front of it).
      ".akt-browse{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:0 0 8px}",
      ".akt-chipbtn{padding:6px 11px;border-radius:8px;border:1px solid rgba(201,168,76,.22);background:rgba(255,255,255,.03);color:#9a9aa6;font-weight:800;font-size:10px;letter-spacing:.5px;cursor:pointer}",
      ".akt-chipbtn.on{background:rgba(201,168,76,.16);color:#e8c55a;border-color:rgba(201,168,76,.5)}",
      ".akt-sortsel{width:auto;margin:0 0 0 auto;padding:6px 9px;font-size:11px}",
      ".akt-gate{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 12px 8px;padding:8px 10px;border-radius:9px;border:1px solid rgba(201,168,76,.28);background:rgba(201,168,76,.07)}",
      ".akt-gatetx{flex:1;min-width:150px;color:#cfc7a8;font-size:11px;line-height:1.45}",
      ".akt-btn.sm{padding:7px 12px;font-size:11px}",
      ".akt-toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#1a1a22;color:#e8c55a;border:1px solid rgba(201,168,76,.4);padding:9px 16px;border-radius:20px;z-index:70;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".akt-toast.show{opacity:1}"
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
    ensureCardIdx();
    var glyph = mk("span", { class: "akt-glyph", text: "💼" }); // briefcase
    var ttl = mk("div", { class: "akt-ttl" }, [ mk("h2", { text: "THE TRADING POST" }), mk("div", { class: "sub", text: "Switch the Broker -- barter, no crypto" }) ]);
    var x = mk("button", { class: "akt-x", type: "button", "aria-label": "close", text: "×", onclick: closeTradePost });
    var top = mk("div", { class: "akt-top" }, [ glyph, ttl, x ]);
    var line = mk("div", { class: "akt-line", text: BROKER_LINES[Math.floor(Math.random() * BROKER_LINES.length)] });
    S.bodyEl = mk("div", { class: "akt-body" });
    S.root = mk("section", { id: "ak-trade" }, [ top, line, S.bodyEl ]);
    document.body.appendChild(S.root);
    if (!S.toastEl) { S.toastEl = mk("div", { class: "akt-toast" }); document.body.appendChild(S.toastEl); }
    S.root.classList.add("open");
  }

  function drawBackdrop(g, dt, vp) {
    // gritty dim wash + a few drifting gold embers behind the DOM panel
    g.save();
    g.fillStyle = "rgba(6,5,3,.86)"; g.fillRect(0, 0, vp.w, vp.h);
    var t = (drawBackdrop._t = (drawBackdrop._t || 0) + dt);
    g.globalAlpha = .5; g.fillStyle = "#e8c55a";
    for (var i = 0; i < 14; i++) {
      var x = (i * 67 + (t * 12 + i * 40)) % (vp.w + 40) - 20;
      var y = (vp.h - ((t * 18 + i * 90) % (vp.h + 40)));
      g.beginPath(); g.arc(x, y, 1.2 + (i % 3) * 0.5, 0, 7); g.fill();
    }
    g.globalAlpha = 1; g.restore();
  }

  function openTradePost() {
    if (S.uiOpen) return;
    S.uiOpen = true; S.entryLock = true;
    // freeze the hub via the contract overlay (drawn backdrop). DOM panel rides on top (z 46 > overlay 40).
    if (CTX && CTX.overlay && CTX.overlay.open) {
      try { S.ovApi = CTX.overlay.open({ id: "trade_post", onFrame: drawBackdrop, onPointer: function () {}, onClose: teardownUI }); }
      catch (_e) { S.ovApi = null; }
    }
    buildPanel();
    setTab("board");
    if (me()) { claimGrants(); refreshMine(); }   // pending payouts + seed the ACTIVE_CAP gate
  }
  // AK-MKT 2026-07-18: S.mine was only ever filled by a visit to the MINE tab, so the
  // concurrent-offer cap did nothing on a fresh session -- the first POST always slipped
  // past it. Seed the snapshot on open so the gate is honest from the first offer.
  function refreshMine() {
    if (!me()) return;
    call(TRADE_FN, { action: "mine" }).then(function (r) {
      if (r && r.ok) S.mine = (r.listings || []).filter(function (L) { return L && L.give && L.want; });
    });
  }
  function closeTradePost() {
    if (S.ovApi) { try { S.ovApi.close(); } catch (_e) { teardownUI(); } } // onClose -> teardownUI
    else teardownUI();
  }
  function teardownUI() {
    S.uiOpen = false; S.ovApi = null;
    if (S.root) { try { S.root.remove(); } catch (_e) {} S.root = null; S.bodyEl = null; }
  }

  function setTab(t) { S.tab = t; render(); }

  // ----------------------------------------------------------------------- //
  //  RENDER                                                                  //
  // ----------------------------------------------------------------------- //
  // AK-MKT 2026-07-18: what blocks TRADING, which is not the same as what blocks BROWSING.
  // "" = this dog can deal; otherwise the reason. The board stays readable either way.
  function blockedReason() {
    if (!me()) return "signin";
    if (townHall() < MIN_TH) return "th";
    return "";
  }
  function gateText(reason) {
    return reason === "signin"
      ? "Browsing read-only. Sign in to post or accept."
      : "Browsing read-only. The post opens at Town Hall Lv " + MIN_TH + " -- you're Lv " + townHall() + ".";
  }
  function signInBtn(cls, label) {
    return mk("button", { class: cls, text: label, onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } });
  }
  // the ask rides ABOVE the content as a strip, so it never replaces the board.
  function gateBanner(reason) {
    var kids = [ mk("span", { class: "akt-gatetx", text: gateText(reason) }) ];
    if (reason === "signin") kids.push(signInBtn("akt-btn sm", "SIGN IN"));
    return mk("div", { class: "akt-gate" }, kids);
  }
  // full card for the tabs that genuinely need an account (POST / MINE move goods).
  function gateCard(reason) {
    var kids = [ mk("div", { class: "akt-note", text: reason === "signin"
      ? "Sign in with Google to barter at the post. Switch only deals with known faces. The BOARD tab is open to everyone."
      : "The post opens at Town Hall Lv " + MIN_TH + ". You're Lv " + townHall() + ". Level the Town Hall, then come back and we'll talk." }) ];
    if (reason === "signin") kids.push(signInBtn("akt-btn", "SIGN IN WITH GOOGLE"));
    return mk("div", { class: "akt-card" }, kids);
  }

  function render() {
    if (!S.bodyEl) return;
    // AK-MKT 2026-07-18: NO auth wall. A signed-out or under-levelled dog still browses the
    // board read-only -- an auth wall in front of core content is a known problem here, and
    // this was the last one in the post. Only the tabs that actually move goods stay gated.
    var blocked = blockedReason();
    var tabs = mk("div", { class: "akt-tabs" }, [
      mk("button", { class: "akt-tab" + (S.tab === "board" ? " on" : ""), text: "BOARD", onclick: function () { setTab("board"); } }),
      mk("button", { class: "akt-tab" + (S.tab === "post" ? " on" : ""), text: "POST", onclick: function () { setTab("post"); } }),
      mk("button", { class: "akt-tab" + (S.tab === "mine" ? " on" : ""), text: "MINE", onclick: function () { setTab("mine"); } })
    ]);
    var meta = mk("div", { class: "akt-meta" }, [
      mk("span", {}, [ "Band: ", mk("b", { text: bandLabel(myBand()) }) ]),
      mk("span", {}, [ "Today: ", mk("b", { text: tradesToday() + "/" + DAILY_CAP }) ])
    ]);
    var slot = mk("div", {});
    var kids = [ tabs, meta, slot ];
    if (blocked) kids.splice(2, 0, gateBanner(blocked));
    setKids(S.bodyEl, kids);
    if (S.tab === "board") renderBoard(slot, blocked);
    else if (blocked) setKids(slot, gateCard(blocked));
    else if (S.tab === "post") renderPost(slot);
    else renderMine(slot);
  }

  function fmtItem(it) {
    if (!it) return "?";
    if (it.kind === "gold") return (it.amount | 0) + " gold";
    if (it.kind === "scrap") return (it.amount | 0) + " " + it.rarity + " scrap";
    if (it.kind === "card") return (it.amount | 0) + "x " + it.card_id;
    if (it.kind === "cosmetic") return "cosmetic: " + it.card_id;
    return "?";
  }

  // ----------------------------------------------------------------------- //
  //  ART (AK-ART 2026-07-01) -- REAL card portraits + resource-chip art      //
  //  Reuses the hub's canonical akCardArtRel + CANON_CARDS (the exact path   //
  //  index.html openPicker / THE WATCH use) and the transparent-cleaned      //
  //  assets/icons/chip_*.png set. NO new art path. Glyph fallback only where //
  //  art is genuinely absent (missing canon entry / file). Card legs + the   //
  //  give-card picker render as chop-shop card-art tiles to match the world. //
  // ----------------------------------------------------------------------- //
  var RES_CHIP = { gold: "assets/icons/chip_gold.png", scrap: "assets/icons/chip_scrap.png" };
  var GLYPH    = { gold: "\u{1FA99}", scrap: "⚙️", card: "\u{1F0CF}", cosmetic: "✨" };
  var RAR_COLOR = { Common: "#9fb0c0", Rare: "#5fd3ff", Epic: "#b57bff", Legendary: "#ffb648", Mythic: "#ff5f7a" };
  // resolve a card's REAL portrait via the shared resolver (assets/cards/NNNN_slug.webp).
  function cardArtFor(name) {
    try {
      var L = global.CANON_CARDS || [];
      for (var i = 0; i < L.length; i++) {
        var c = L[i];
        if (c && (c.name === name || c.id === name || String(c.cardNumber) === String(name))) {
          if (global.akCardArtRel) { var rel = akCardArtRel(c); if (rel) return "assets/" + rel; }
          break;
        }
      }
    } catch (_) {}
    return "";
  }
  // a resource (gold / scrap) as REAL chip art; degrades to the glyph if missing.
  function resIcon(kind, px) {
    px = px || 18;
    var src = RES_CHIP[kind];
    if (!src) return mk("span", { class: "akt-ri-g", text: GLYPH[kind] || "" });
    var img = mk("img", { class: "akt-ri", src: src, alt: "", loading: "lazy", style: "width:" + px + "px;height:" + px + "px" });
    img.onerror = function () { try { if (img.parentNode) img.parentNode.replaceChild(mk("span", { class: "akt-ri-g", text: GLYPH[kind] || "" }), img); } catch (_) {} };
    return img;
  }
  // a circular card-art portrait tile (webp -> png via akImgErr -> dog glyph), ringed by rarity.
  function cardAvatar(name, px, ringColor) {
    px = px || 40;
    var wrap = mk("div", { class: "akt-av", style: "width:" + px + "px;height:" + px + "px;border-color:" + (ringColor || "#c9a84c") + ";font-size:" + Math.round(px * 0.46) + "px" });
    var art = cardArtFor(name);
    if (art) {
      var img = mk("img", { src: art, alt: "", loading: "lazy" });
      img.onerror = function () { if (!(global.akImgErr && akImgErr(img))) { try { wrap.removeChild(img); wrap.textContent = "\u{1F415}"; } catch (_) {} } };
      wrap.appendChild(img);
    } else { wrap.textContent = "\u{1F415}"; }
    return wrap;
  }
  // a trade leg as art: card -> portrait tile + name/rarity; gold/scrap -> chip + amount;
  // cosmetic -> sparkle token. cls ("akt-give"/"akt-want") tints the numeric legs.
  function legNode(it, cls) {
    if (!it) return mk("span", { class: cls || "", text: "?" });
    if (it.kind === "card") {
      var rar = it.rarity || rarOf(it.card_id);
      return mk("span", { class: "akt-leg " + (cls || ""), title: fmtItem(it) }, [
        cardAvatar(it.card_id, 34, (RAR_COLOR[rar] || "#c9a84c") + "cc"),
        mk("span", { class: "akt-legtx" }, [
          mk("span", { class: "akt-legnm", text: it.card_id }),
          mk("span", { class: "akt-legsub", text: ((it.amount | 0) > 1 ? ("x" + (it.amount | 0) + "  ") : "") + rar })
        ])
      ]);
    }
    if (it.kind === "cosmetic") {
      return mk("span", { class: "akt-leg " + (cls || ""), title: fmtItem(it) }, [
        mk("span", { class: "akt-ri-g", text: GLYPH.cosmetic }),
        mk("span", { class: "akt-legtx" }, [ mk("span", { class: "akt-legnm", text: it.card_id }), mk("span", { class: "akt-legsub", text: "cosmetic" }) ])
      ]);
    }
    var kids = [ resIcon(it.kind, 20), mk("span", { class: "akt-amt", text: String(it.amount | 0) }) ];
    if (it.kind === "scrap") kids.push(mk("span", { class: "akt-rar", text: it.rarity }));
    return mk("span", { class: "akt-chip " + (cls || ""), title: fmtItem(it) }, kids);
  }

  // AK-MKT 2026-07-18: category tabs + a sort select. Buttons restyle in place rather than
  // rebuilding the strip, so the select keeps focus while you flip categories.
  function browseControls(onChange) {
    var row = mk("div", { class: "akt-browse" }), btns = [];
    tradeCats().forEach(function (c) {
      var b = mk("button", { class: "akt-chipbtn" + (S.browseCat === c.id ? " on" : ""), text: c.label });
      b.onclick = function () {
        S.browseCat = c.id;
        btns.forEach(function (x) { x.el.className = "akt-chipbtn" + (x.id === c.id ? " on" : ""); });
        onChange();
      };
      btns.push({ id: c.id, el: b }); row.appendChild(b);
    });
    var sel = mk("select", { class: "akt-sel akt-sortsel" });
    SORTS.forEach(function (s) {
      var o = mk("option", { value: s.id, text: s.label });
      if (S.browseSort === s.id) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = function () { S.browseSort = sel.value; onChange(); };
    row.appendChild(sel);
    return row;
  }
  // the server stamps expires_at (48h default) and hides lapsed rows from "list"; surface the
  // clock so a resting offer reads as perishable instead of permanent.
  function expiryTx(L) {
    if (!L || !L.expires_at) return "";
    var ms = new Date(L.expires_at).getTime() - Date.now();
    if (!isFinite(ms) || ms <= 0) return "";
    var h = Math.floor(ms / 3600000);
    return h >= 1 ? ("  ends in " + h + "h") : ("  ends in " + Math.max(1, Math.round(ms / 60000)) + "m");
  }
  // one board row. `blocked` decides whether the action is a real accept or a read-only nudge:
  // a preview row has NO accept path at all, so nothing can be minted from a sample board.
  function offerRow(L, blocked) {
    var mine = L.seller_id && L.seller_id === myId(), btn;
    if (L._src === "preview" || blocked === "signin") btn = signInBtn("akt-btn ghost", "Sign in");
    else if (mine) { btn = mk("button", { class: "akt-btn ghost", text: "yours" }); btn.disabled = true; }
    else if (blocked) { btn = mk("button", { class: "akt-btn ghost", text: "Lv " + MIN_TH }); btn.disabled = true; }
    else { btn = mk("button", { class: "akt-btn", text: "Accept" }); btn.onclick = function () { acceptOffer(L, btn); }; }
    var sub = "from " + (L.seller_name || "Stray") + (L._src === "preview" ? "  (sample board)" : expiryTx(L));
    return mk("div", { class: "akt-li akt-offer" }, [
      mk("div", { class: "akt-offmid" }, [
        mk("div", { class: "akt-trade" }, [ legNode(L.give, "akt-give"), mk("span", { class: "akt-arrow", text: "→" }), legNode(L.want, "akt-want") ]),
        mk("div", { class: "akt-sub", text: sub })
      ]),
      btn
    ]);
  }

  function renderBoard(slot, blocked) {
    var listEl = mk("div", {});
    setKids(slot, [ browseControls(paint), listEl ]);
    function paint() {
      if (!S.root) return;
      var rows = sortListings(S.listings.filter(function (L) { return listingInCat(L, S.browseCat); }), S.browseSort);
      if (!rows.length) {
        setKids(listEl, mk("div", { class: "akt-note", text: S.listings.length
          ? "Nothing asking for that. Tap ALL to see the whole board."
          : "No open offers in your bracket. Tap POST to put a card on the board." }));
        return;
      }
      setKids(listEl, rows.map(function (L) { return offerRow(L, blocked); }));
    }
    // signed out -> the deterministic sample board. The edge fn rejects an unauthenticated
    // "list" outright (401), so there is no real board to fetch until they sign in.
    if (blocked === "signin") { S.listings = previewListings(); paint(); return; }
    setKids(listEl, mk("div", { class: "akt-note", text: "Loading the board..." }));
    call(TRADE_FN, { action: "list", band: myBand(), q: "" }).then(function (r) {
      if (!S.root) return;
      if (!r || !r.ok) {
        S.listings = [];
        setKids(listEl, mk("div", { class: "akt-note", text: r && r.error === "offline" ? "Trading post is offline (sign-in / server not reachable). Your cards are safe." : ("Could not load offers" + (r && r.error ? ": " + r.error : "") + ".") }));
        return;
      }
      S.listings = (r.listings || []).filter(function (L) { return L && L.give && L.want; });
      paint();
    });
  }

  // ----- POST a new offer ------------------------------------------------- //
  function renderPost(slot) {
    var giveables = myGiveables();
    if (!giveables.length) {
      setKids(slot, mk("div", { class: "akt-card" }, [ mk("div", { class: "akt-note", text: "You have no spare cards to trade. Win matches, open chests, then come back. (Mythics are never tradeable.)" }) ]));
      return;
    }
    // GIVE: card-art tile grid (owned tradeable cards) -- tap a real portrait to select it.
    // Mirrors THE WATCH picker (systems/guard.js): rarity-ringed portrait, name, rarity + copies.
    var selGive = giveables[0];
    var giveGrid = mk("div", { class: "akt-grid" });
    var giveQtySel = mk("select", { class: "akt-sel" });
    function rebuildGiveQty() { var max = Math.min(3, cardCopies(selGive) || 1); var opts = []; for (var q = 1; q <= max; q++) opts.push(mk("option", { value: String(q), text: q + " cop" + (q > 1 ? "ies" : "y") })); setKids(giveQtySel, opts); }
    function paintGiveGrid() {
      setKids(giveGrid, giveables.map(function (n) {
        var rar = rarOf(n), on = (n === selGive), ring = (RAR_COLOR[rar] || "#c9a84c");
        var tile = mk("button", { type: "button", class: "akt-tile" + (on ? " on" : ""), style: "border-color:" + (on ? "#e8c55a" : "rgba(201,168,76,.28)") }, [
          cardAvatar(n, 54, ring + "cc"),
          mk("span", { class: "akt-tilenm", text: n }),
          mk("span", { class: "akt-tilesub", style: "color:" + ring, text: rar + " x" + cardCopies(n) })
        ]);
        tile.onclick = function () { selGive = n; paintGiveGrid(); rebuildGiveQty(); refreshFee(); };
        return tile;
      }));
    }
    paintGiveGrid();
    rebuildGiveQty();

    // WANT: kind + dynamic fields
    var wantKind = mk("select", { class: "akt-sel" }, [
      mk("option", { value: "gold", text: "Gold" }),
      mk("option", { value: "scrap", text: "Scrap" }),
      mk("option", { value: "card", text: "A card (card-for-card)" })
    ]);
    var wantWrap = mk("div", {});
    var goldSel = mk("select", { class: "akt-sel" }, GOLD_WANT_OPTS.map(function (v) { return mk("option", { value: String(v), text: v + " gold" }); }));
    var scrapRar = mk("select", { class: "akt-sel" }, TRADE_RARITIES.map(function (r) { return mk("option", { value: r, text: r }); }));
    var scrapAmt = mk("select", { class: "akt-sel" }, SCRAP_WANT_OPTS.map(function (v) { return mk("option", { value: String(v), text: v + " scrap" }); }));
    var wantCard = mk("select", { class: "akt-sel" }, allTradeNames().map(function (n) { return mk("option", { value: n, text: n + "  (" + rarOf(n) + ")" }); }));
    var wantCardQty = mk("select", { class: "akt-sel" }, [1, 2, 3, 4].map(function (q) { return mk("option", { value: String(q), text: q + "x" }); }));
    function rebuildWant() {
      var k = wantKind.value;
      if (k === "gold") setKids(wantWrap, goldSel);
      else if (k === "scrap") setKids(wantWrap, [scrapRar, scrapAmt]);
      else setKids(wantWrap, [wantCard, wantCardQty]);
    }
    rebuildWant();
    wantKind.onchange = rebuildWant;

    var feeEl = mk("div", { class: "akt-fee" });
    function refreshFee() { var fee = POST_FEE[rarOf(selGive)] || 25; feeEl.textContent = "Listing fee: " + fee + " gold (Switch's cut) -- you have " + (cur() ? cur().get("gold") : 0); }
    refreshFee();

    var postBtn = mk("button", { class: "akt-btn", style: "flex:1", text: "POST OFFER" });
    function gateMsg() {
      if (capLeft() <= 0) return "Daily cap reached (" + DAILY_CAP + ").";
      // AK-MKT 2026-07-18: concurrent-offer cap. S.mine is the last server "mine" snapshot,
      // so this only bites once the MINE tab has loaded -- the daily cap still backstops it.
      if (S.mine.length >= ACTIVE_CAP) return "You already have " + ACTIVE_CAP + " offers up. Cancel one first.";
      var cd = cooldownLeft(); if (cd > 0) return "Broker's busy -- " + Math.ceil(cd / 1000) + "s.";
      var fee = POST_FEE[rarOf(selGive)] || 25; if ((cur() ? cur().get("gold") : 0) < fee) return "Need " + fee + " gold for the listing fee.";
      return "";
    }
    postBtn.onclick = function () {
      var msg = gateMsg(); if (msg) { toast(msg); return; }
      var give = { kind: "card", card_id: selGive, rarity: rarOf(selGive), amount: parseInt(giveQtySel.value, 10) || 1 };
      var want; var wk = wantKind.value;
      if (wk === "gold") want = { kind: "gold", amount: parseInt(goldSel.value, 10) || 50 };
      else if (wk === "scrap") want = { kind: "scrap", rarity: scrapRar.value, amount: parseInt(scrapAmt.value, 10) || 4 };
      else want = { kind: "card", card_id: wantCard.value, rarity: rarOf(wantCard.value), amount: parseInt(wantCardQty.value, 10) || 1 };
      // hard parity guard (belt + suspenders -- selects already exclude Mythic/forbidden)
      if (forbidden(give) || forbidden(want)) { toast("That item can't be traded."); return; }
      var fee = POST_FEE[give.rarity] || 25;
      // deposit: the card we're offering + the gold listing fee
      var basket = [ give, { kind: "gold", amount: fee } ];
      // AK-MKT 2026-07-18: drip.js buy() order -- CHECK the basket, get the server ack, and
      // only THEN debit. Debiting first meant a dropped response / closed tab between the
      // deduct and the reply ate the card + fee with no listing to show for it. Nothing is
      // charged until the server has actually recorded the offer, so there is no refund path.
      var chk = canDepositAll(basket);
      if (!chk.ok) { toast(chk.error === "CANT_AFFORD" ? "Can't afford that (card + " + fee + " gold)." : "That item can't be traded."); return; }
      postBtn.disabled = true; postBtn.textContent = "Posting...";
      call(TRADE_FN, { action: "post", give: give, want: want, band: myBand(), name: myName() }).then(function (r) {
        if (r && r.ok) {
          depositAll(basket);                               // server ack'd -> NOW debit (fee is a SINK, never refunded)
          logTrade("post", r.listing && r.listing.id);
          toast("Posted to the board.");
          try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
          setTab("mine");
        } else {
          toast(r && r.error === "offline" ? "Post is offline -- nothing was charged." : ((r && r.error) || "Could not post.") );
          postBtn.disabled = false; postBtn.textContent = "POST OFFER";
        }
      });
    };

    setKids(slot, mk("div", { class: "akt-card" }, [
      mk("div", { class: "akt-lbl", text: "You give" }), giveGrid, giveQtySel,
      mk("div", { class: "akt-lbl", text: "You want" }), wantKind, wantWrap,
      feeEl,
      mk("div", { class: "akt-note", style: "padding:6px 2px", text: "Soft goods only -- cards, scrap, gold. No gems, no $BCARDD. Cosmetic trades land with the next update." }),
      mk("div", { style: "display:flex;gap:8px;margin-top:6px" }, [ postBtn, mk("button", { class: "akt-btn ghost", text: "Back", onclick: function () { setTab("board"); } }) ])
    ]));
  }

  // ----- ACCEPT an offer -------------------------------------------------- //
  function acceptOffer(L, btn) {
    var cd = cooldownLeft(); if (cd > 0) { toast("Broker's busy -- " + Math.ceil(cd / 1000) + "s."); return; }
    if (capLeft() <= 0) { toast("Daily cap reached (" + DAILY_CAP + ")."); return; }
    if (forbidden(L.want) || forbidden(L.give)) { toast("That offer can't be traded."); return; }
    // I pay the WANT + the broker's accept cut; I receive the GIVE via server grant.
    var basket = [ L.want, { kind: "gold", amount: ACCEPT_FEE } ];
    // AK-MKT 2026-07-18: same drip.js ordering as the post path -- check, ack, THEN debit.
    // The server CAS ("offer was just taken") is the only authority on whether this fill is
    // real, so paying before asking was a guaranteed refund-race on every contested offer.
    var chk = canDepositAll(basket);
    if (!chk.ok) { toast(chk.error === "CANT_AFFORD" ? ("Can't afford " + fmtItem(L.want) + " + " + ACCEPT_FEE + " gold.") : "That offer can't be traded."); return; }
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    call(TRADE_FN, { action: "accept", listing_id: L.id, band: myBand() }).then(function (r) {
      if (r && r.ok) {
        depositAll(basket);                                 // server ack'd the claim -> NOW pay
        var got = applyGrants(r.grants || [{ kind: L.give.kind, card_id: L.give.card_id, rarity: L.give.rarity, amount: L.give.amount }]);
        logTrade("accept", L.id);
        toast("Trade done -- " + fmtItem(L.give) + " is yours.");
        try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
        render();
      } else {
        toast(r && r.error === "offline" ? "Trade is offline -- nothing was charged." : ((r && r.error) || "Trade failed."));
        if (btn) { btn.disabled = false; btn.textContent = "Accept"; }
      }
    });
  }

  // ----- MINE: my open offers + cancel ------------------------------------ //
  function renderMine(slot) {
    setKids(slot, mk("div", { class: "akt-note", text: "Loading your offers..." }));
    call(TRADE_FN, { action: "mine" }).then(function (r) {
      if (!S.root) return;
      if (!r || !r.ok) { setKids(slot, mk("div", { class: "akt-note", text: r && r.error === "offline" ? "Offline -- your offers will show when the post is reachable." : "Could not load your offers." })); return; }
      var list = (r.listings || []).filter(function (L) { return L && L.give && L.want; });
      S.mine = list;                                  // AK-MKT 2026-07-18: feeds the ACTIVE_CAP gate on the POST tab
      if (!list.length) { setKids(slot, mk("div", { class: "akt-note", text: "No open offers. Post one from the POST tab." })); return; }
      setKids(slot, list.map(function (L) {
        var btn = mk("button", { class: "akt-btn dng", text: "Cancel" });
        btn.onclick = function () { cancelOffer(L, btn); };
        return mk("div", { class: "akt-li akt-offer" }, [
          mk("div", { class: "akt-offmid" }, [
            mk("div", { class: "akt-trade" }, [ legNode(L.give, "akt-give"), mk("span", { class: "akt-arrow", text: "→" }), legNode(L.want, "akt-want") ]),
            mk("div", { class: "akt-sub", text: (L.status || "open") })
          ]),
          btn
        ]);
      }));
    });
  }
  function cancelOffer(L, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    call(TRADE_FN, { action: "cancel", listing_id: L.id }).then(function (r) {
      if (r && r.ok) {
        // server returns a refund grant for the deposited GIVE; apply it locally.
        applyGrants(r.grants || [{ kind: L.give.kind, card_id: L.give.card_id, rarity: L.give.rarity, amount: L.give.amount }]);
        toast("Offer pulled -- your " + fmtItem(L.give) + " is back.");
        try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
        render();
      } else {
        toast(r && r.error === "offline" ? "Offline -- could not cancel." : ((r && r.error) || "Could not cancel."));
        if (btn) { btn.disabled = false; btn.textContent = "Cancel"; }
      }
    });
  }

  // ----------------------------------------------------------------------- //
  //  ROAMER: "Switch the Broker" (OL'SCRAPS NPC pattern, walks THE_YARDS)     //
  // ----------------------------------------------------------------------- //
  function seedBroker(ctx) {
    if (S.broker || !ctx || !ctx.world || !ctx.world.addRoamer) return;
    var wp0 = S.waypoints[0];
    S.broker = ctx.world.addRoamer({
      id: "switch_the_broker", zone: HOME_ZONE, x: wp0.x, y: wp0.y, r: 20,
      update: function (dt, self, c) {
        // patrol toward the current waypoint
        var w = S.waypoints[S.wp % S.waypoints.length];
        var dx = w.x - self.x, dy = w.y - self.y, d = Math.hypot(dx, dy) || 1;
        if (d < 18) { S.wp = (S.wp + 1) % S.waypoints.length; }
        else { self.x += (dx / d) * BROKER_SPD * dt; self.y += (dy / d) * BROKER_SPD * dt; }
        self._face = dx < 0 ? -1 : 1;
        // proximity trigger (avoidable; opens the post on contact)
        if (S.uiOpen) return;
        var pd = c.world.distToMe(self.x, self.y);
        self._near = pd < TRIGGER_R * 1.5;
        if (S.entryLock) { if (pd > TRIGGER_R + 40) S.entryLock = false; return; }
        if (pd < TRIGGER_R) { try { ctxBanner(c, "Switch the Broker -- trading post"); } catch (_) {} openTradePost(); }
      },
      draw: function (g, self, c) {
        var X = c.world.wx(self.x), Y = c.world.wy(self.y), r = self.r;
        g.save();
        // ground shadow
        g.fillStyle = "rgba(0,0,0,.34)"; g.beginPath(); g.ellipse(X, Y + r + 2, r * .8, 4.5, 0, 0, 7); g.fill();
        // body -- dark coat, gold ring (merchant vibe)
        g.beginPath(); g.arc(X, Y, r, 0, 7);
        g.fillStyle = "#1b1712"; g.fill();
        g.lineWidth = 2.4; g.strokeStyle = "#e8c55a"; g.shadowColor = "#c9a84c"; g.shadowBlur = 10; g.stroke(); g.shadowBlur = 0;
        // briefcase glyph
        g.fillStyle = "#e8c55a"; g.font = "700 16px Inter,sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText("💼", X, Y + 1);
        // name tag
        g.fillStyle = "#e8c55a"; g.font = "700 10px Inter,sans-serif"; g.textBaseline = "alphabetic";
        g.fillText("SWITCH", X, Y - r - 6);
        // "tap to trade" cue when the player is close
        if (self._near) {
          var bob = Math.sin((performance.now() / 220)) * 2;
          g.fillStyle = "rgba(12,12,18,.9)"; roundRect(g, X - 30, Y - r - 34 + bob, 60, 16, 5); g.fill();
          g.strokeStyle = "rgba(201,168,76,.6)"; g.lineWidth = 1; g.stroke();
          g.fillStyle = "#7CFFb0"; g.font = "700 9px Inter,sans-serif"; g.textAlign = "center";
          g.fillText("$ TRADE", X, Y - r - 23 + bob);
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
    id: "trading",
    init: function (ctx) {
      CTX = ctx || global.AK_CTX || CTX;
      if (S.seeded) return; S.seeded = true;
      ensureCardIdx();
      try { seedBroker(CTX); } catch (_e) {}
    },
    onEnterBuilding: function (b, ctx) { return false; },   // trading owns NO building (roamer + overlay only)
    onTick: function (dt, ctx) { CTX = ctx || CTX; /* patrol + proximity live on the roamer (host-driven); offer cooldown read on demand */ },
    onDrawWorld: function (ctx) { /* the broker draws itself via the roamer; no extra world overlay */ }
  });

  // expose a tiny handle for debugging / external open (parity with AKSocial)
  global.AKTrading = { open: openTradePost, close: closeTradePost };

})(typeof window !== "undefined" ? window : globalThis);

/* ==========================================================================
   ===== ak-trading EDGE FN -- SERVER SPEC (DO NOT DEPLOY; mirrors ak-crew) =====
   Lead/integrator applies this. Deno fn, service-role single-writer, RLS blocks
   all direct client writes (this fn is the only path). Auth = caller JWT (same
   verify block as ak-crew). Delivery rides the EXISTING `ak_grants` table +
   pattern (social.js applyGrant claims them). All amounts soft only.

   ----- NEW MIGRATION: supabase/migrations/<ts>_trading.sql --------------------
   create table if not exists ak_trade_listings (
     id           uuid primary key default gen_random_uuid(),
     seller_id    uuid not null references auth.users(id),
     seller_name  text not null default 'Stray',
     give_kind    text not null,        -- 'card' | 'cosmetic'  (never gems/$BCARDD)
     give_card_id text,                 -- card name or cosmetic id
     give_rarity  text,
     give_amount  int  not null default 1,
     want_kind    text not null,        -- 'gold' | 'scrap' | 'card'
     want_card_id text,
     want_rarity  text,
     want_amount  int  not null default 0,
     band         int  not null default 0,           -- floor(trophies/400)
     status       text not null default 'open',       -- open|filled|cancelled|expired
     filled_by    uuid,
     created_at   timestamptz not null default now(),
     expires_at   timestamptz not null default (now() + interval '48 hours')
   );
   create index on ak_trade_listings (status, band, created_at desc);
   create index on ak_trade_listings (seller_id, status);
   alter table ak_trade_listings enable row level security;  -- NO client policies => service-role only
   -- ak_grants already exists (ak-crew). Reused for delivery.

   ----- ACTIONS ---------------------------------------------------------------
   Shared guards (server-authoritative -- re-enforce every client gate):
     FORBID  = give/want kind 'gems'  OR  rarity 'Mythic'  OR  card_id ~* '\\$|bcardd|alk'
     DAILY   = count(ak_trade_listings where seller_id=uid and created_at> now()-24h
                     + filled rows where filled_by=uid and filled_at> now()-24h)  <= 5
     BAND    = listing.band must equal caller's band on list/accept
     (NOTE: Town Hall + the gold tax are CLIENT-side today because coins/cards live
      in localStorage. The server records + matchmakes + delivers; it cannot yet
      deduct client gold. // TODO-SERVER: when the economy moves server-side, the
      deposit becomes a real server-held escrow and the tax a server debit, which
      also makes the trade fully DUPE-PROOF.)

   list   {band,q}            -> open listings where status='open' and band=band and seller_id<>uid
                                 (ilike give_card_id/want_card_id on q), limit 50, newest first.
                                 reply {ok, listings:[{id,seller_id,seller_name,give:{...},want:{...},band}]}
   post   {give,want,band,name}-> FORBID/DAILY/shape validate; insert row status='open'.
                                 reply {ok, listing:{id,...}}.   (client already deducted give+fee.)
   accept {listing_id,band}   -> load open listing; reject if mine / filled / expired / band<>.
                                 mark status='filled', filled_by=uid, filled_at=now().
                                 queue ak_grants: (uid <- give item)  AND  (seller_id <- want item).
                                 reply {ok, grants:[<the GIVE item for the acceptor>]}  (acceptor applies
                                 immediately; the seller claims their WANT via claim-grants next session).
   cancel {listing_id}        -> only seller; status='open'->'cancelled'.
                                 queue ak_grants: (uid <- the deposited give item)  [refund].
                                 reply {ok, grants:[<refund give item>]}.
   mine   {}                  -> caller's status='open' listings. reply {ok, listings:[...]}.
   claim-grants {}            -> IDENTICAL to ak-crew: pull ak_grants where user_id=uid, claimed=false,
                                 mark claimed=true, reply {ok, grants:[...]}.

   Anti-dupe today: client deducts on deposit (post/accept) and the server only ever
   GRANTS (never trusts a client to mint). A failed call is refunded client-side, so the
   net is conservative. Gems are impossible here (server-only + no-op client). $BCARDD/ALK
   and all Mythics are double-blocked (client selects exclude them; server FORBID rejects).
   ========================================================================== */
