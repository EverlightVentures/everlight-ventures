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
  //  Inventory is client-side localStorage today, so a LIST/ACCEPT deducts   //
  //  locally up front (the "deposit"); the server records the listing +      //
  //  matchmakes + delivers via ak_grants. A failed server call REFUNDS in    //
  //  full so nothing is ever lost. True server escrow lands when the economy //
  //  moves server-side. // TODO-SERVER: server-held inventory = real escrow.  //
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
  // atomically deposit a basket (check ALL first; then deduct). Returns {ok, error}.
  function depositAll(items) {
    for (var i = 0; i < items.length; i++) { if (forbidden(items[i])) return { ok: false, error: "FORBIDDEN_ITEM" }; if (!affordable(items[i])) return { ok: false, error: "CANT_AFFORD" }; }
    items.forEach(deduct);
    return { ok: true };
  }
  function refundAll(items) { items.forEach(refundItem); }

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
      ".akt-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:12px;margin-bottom:10px}",
      ".akt-li{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid rgba(255,255,255,.06)}",
      ".akt-give{color:#7CFFb0;font-weight:800}.akt-want{color:#e8c55a;font-weight:800}.akt-arrow{color:#9a9aa6}",
      ".akt-nm{font-weight:800;color:#fff;font-size:13px}.akt-sub{color:#9a9aa6;font-size:11px}",
      ".akt-btn{background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#1a1405;border:0;border-radius:9px;padding:10px 14px;font-weight:800;letter-spacing:.5px;cursor:pointer}",
      ".akt-btn.ghost{background:rgba(255,255,255,.05);color:#e9e9ee;border:1px solid rgba(255,255,255,.16)}",
      ".akt-btn.dng{background:rgba(220,80,80,.16);color:#f3a0a0;border:1px solid rgba(220,80,80,.3)}",
      ".akt-btn:active{transform:scale(.97)}.akt-btn[disabled]{opacity:.5;cursor:not-allowed}",
      ".akt-inp,.akt-sel{width:100%;box-sizing:border-box;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.14);color:#fff;border-radius:9px;padding:10px;margin:5px 0;font-size:14px}",
      ".akt-lbl{color:#9a8f6a;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-top:8px}",
      ".akt-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px 8px;line-height:1.5}",
      ".akt-fee{color:#e8c55a;font-size:12px;text-align:center;margin:6px 0}",
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
    if (me()) claimGrants();           // pull any pending payouts from prior trades
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
  function render() {
    if (!S.bodyEl) return;
    // gate 1: signed out
    if (!me()) {
      setKids(S.bodyEl, [ mk("div", { class: "akt-card" }, [
        mk("div", { class: "akt-note", text: "Sign in with Google to barter at the post. Switch only deals with known faces." }),
        mk("button", { class: "akt-btn", style: "display:block;margin:8px auto 0", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } })
      ]) ]);
      return;
    }
    // gate 2: Town Hall level
    var th = townHall();
    if (th < MIN_TH) {
      setKids(S.bodyEl, [ mk("div", { class: "akt-card" }, [
        mk("div", { class: "akt-note", text: "The post opens at Town Hall Lv " + MIN_TH + ". You're Lv " + th + ". Level the Town Hall, then come back and we'll talk." })
      ]) ]);
      return;
    }
    // tabs + meta
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
    setKids(S.bodyEl, [ tabs, meta, slot ]);
    if (S.tab === "board") renderBoard(slot);
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

  function renderBoard(slot) {
    setKids(slot, mk("div", { class: "akt-note", text: "Loading the board..." }));
    call(TRADE_FN, { action: "list", band: myBand(), q: "" }).then(function (r) {
      if (!S.root) return;
      if (!r || !r.ok) {
        setKids(slot, mk("div", { class: "akt-note", text: r && r.error === "offline" ? "Trading post is offline (sign-in / server not reachable). Your cards are safe." : ("Could not load offers" + (r && r.error ? ": " + r.error : "") + ".") }));
        return;
      }
      S.listings = (r.listings || []).filter(function (L) { return L && L.give && L.want; });
      if (!S.listings.length) { setKids(slot, mk("div", { class: "akt-note", text: "No open offers in your bracket. Tap POST to put a card on the board." })); return; }
      setKids(slot, S.listings.map(function (L) {
        var mine = L.seller_id === myId();
        var btn = mk("button", { class: "akt-btn" + (mine ? " ghost" : ""), text: mine ? "yours" : "Accept" });
        if (mine) btn.disabled = true; else btn.onclick = function () { acceptOffer(L, btn); };
        return mk("div", { class: "akt-li" }, [
          mk("div", { style: "flex:1" }, [
            mk("div", {}, [ mk("span", { class: "akt-give", text: fmtItem(L.give) }), mk("span", { class: "akt-arrow", text: "  →  " }), mk("span", { class: "akt-want", text: fmtItem(L.want) }) ]),
            mk("div", { class: "akt-sub", text: "from " + (L.seller_name || "Stray") })
          ]),
          btn
        ]);
      }));
    });
  }

  // ----- POST a new offer ------------------------------------------------- //
  function renderPost(slot) {
    var giveables = myGiveables();
    if (!giveables.length) {
      setKids(slot, mk("div", { class: "akt-card" }, [ mk("div", { class: "akt-note", text: "You have no spare cards to trade. Win matches, open chests, then come back. (Mythics are never tradeable.)" }) ]));
      return;
    }
    // GIVE: card picker (cosmetics flagged coming-soon -- needs server inventory)
    var giveCard = mk("select", { class: "akt-sel" }, giveables.map(function (n) { return mk("option", { value: n, text: n + "  (" + rarOf(n) + ", x" + cardCopies(n) + ")" }); }));
    var giveQtySel = mk("select", { class: "akt-sel" });
    function rebuildGiveQty() { var max = Math.min(3, cardCopies(giveCard.value) || 1); var opts = []; for (var q = 1; q <= max; q++) opts.push(mk("option", { value: String(q), text: q + " cop" + (q > 1 ? "ies" : "y") })); setKids(giveQtySel, opts); }
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
    giveCard.onchange = function () { rebuildGiveQty(); refreshFee(); };

    var feeEl = mk("div", { class: "akt-fee" });
    function refreshFee() { var fee = POST_FEE[rarOf(giveCard.value)] || 25; feeEl.textContent = "Listing fee: " + fee + " gold (Switch's cut) -- you have " + (cur() ? cur().get("gold") : 0); }
    refreshFee();

    var postBtn = mk("button", { class: "akt-btn", style: "flex:1", text: "POST OFFER" });
    function gateMsg() {
      if (capLeft() <= 0) return "Daily cap reached (" + DAILY_CAP + ").";
      var cd = cooldownLeft(); if (cd > 0) return "Broker's busy -- " + Math.ceil(cd / 1000) + "s.";
      var fee = POST_FEE[rarOf(giveCard.value)] || 25; if ((cur() ? cur().get("gold") : 0) < fee) return "Need " + fee + " gold for the listing fee.";
      return "";
    }
    postBtn.onclick = function () {
      var msg = gateMsg(); if (msg) { toast(msg); return; }
      var give = { kind: "card", card_id: giveCard.value, rarity: rarOf(giveCard.value), amount: parseInt(giveQtySel.value, 10) || 1 };
      var want; var wk = wantKind.value;
      if (wk === "gold") want = { kind: "gold", amount: parseInt(goldSel.value, 10) || 50 };
      else if (wk === "scrap") want = { kind: "scrap", rarity: scrapRar.value, amount: parseInt(scrapAmt.value, 10) || 4 };
      else want = { kind: "card", card_id: wantCard.value, rarity: rarOf(wantCard.value), amount: parseInt(wantCardQty.value, 10) || 1 };
      // hard parity guard (belt + suspenders -- selects already exclude Mythic/forbidden)
      if (forbidden(give) || forbidden(want)) { toast("That item can't be traded."); return; }
      var fee = POST_FEE[give.rarity] || 25;
      // deposit: the card we're offering + the gold listing fee
      var basket = [ give, { kind: "gold", amount: fee } ];
      var dep = depositAll(basket);
      if (!dep.ok) { toast(dep.error === "CANT_AFFORD" ? "Can't afford that (card + " + fee + " gold)." : "That item can't be traded."); return; }
      postBtn.disabled = true; postBtn.textContent = "Posting...";
      call(TRADE_FN, { action: "post", give: give, want: want, band: myBand(), name: myName() }).then(function (r) {
        if (r && r.ok) {
          logTrade("post", r.listing && r.listing.id);     // fee is a SINK on success (not refunded)
          toast("Posted to the board.");
          try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
          setTab("mine");
        } else {
          refundAll(basket);                                // server rejected -> give everything back
          toast(r && r.error === "offline" ? "Post is offline -- nothing was charged." : ((r && r.error) || "Could not post.") );
          postBtn.disabled = false; postBtn.textContent = "POST OFFER";
        }
      });
    };

    setKids(slot, mk("div", { class: "akt-card" }, [
      mk("div", { class: "akt-lbl", text: "You give" }), giveCard, giveQtySel,
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
    var dep = depositAll(basket);
    if (!dep.ok) { toast(dep.error === "CANT_AFFORD" ? ("Can't afford " + fmtItem(L.want) + " + " + ACCEPT_FEE + " gold.") : "That offer can't be traded."); return; }
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    call(TRADE_FN, { action: "accept", listing_id: L.id, band: myBand() }).then(function (r) {
      if (r && r.ok) {
        var got = applyGrants(r.grants || [{ kind: L.give.kind, card_id: L.give.card_id, rarity: L.give.rarity, amount: L.give.amount }]);
        logTrade("accept", L.id);
        toast("Trade done -- " + fmtItem(L.give) + " is yours.");
        try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
        render();
      } else {
        refundAll(basket);
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
      if (!list.length) { setKids(slot, mk("div", { class: "akt-note", text: "No open offers. Post one from the POST tab." })); return; }
      setKids(slot, list.map(function (L) {
        var btn = mk("button", { class: "akt-btn dng", text: "Cancel" });
        btn.onclick = function () { cancelOffer(L, btn); };
        return mk("div", { class: "akt-li" }, [
          mk("div", { style: "flex:1" }, [
            mk("div", {}, [ mk("span", { class: "akt-give", text: fmtItem(L.give) }), mk("span", { class: "akt-arrow", text: "  →  " }), mk("span", { class: "akt-want", text: fmtItem(L.want) }) ]),
            mk("div", { class: "akt-sub", text: (L.status || "open") + (L.expires_at ? "" : "") })
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
