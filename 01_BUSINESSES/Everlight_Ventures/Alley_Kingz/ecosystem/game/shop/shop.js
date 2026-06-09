/* ==========================================================================
   ALLEY KINGZ // CHOP SHOP -- gritty TV-MA storefront (re-skin + deepen)
   Author: Kaelen Nguyen (Pixel Forge). Re-skin over Amara Osei's server-auth
   foundation. Vanilla JS, no bundler (phone-proot safe). XSS-safe by
   construction: built with a DOM hyperscript (h); every dynamic value is set
   via textContent / setAttribute. NO innerHTML anywhere.

   WHAT CHANGED vs the old build:
   - Real game card ART on every purchasable card (units/<num>_<slug>.png for
     originals, cards/<slug>.png for variants) with a clean rarity-framed
     fallback for the 42 variants not yet painted.
   - Gritty street component tree: rarity-framed cards, faction badges, HEAVY/
     STREET variant stamps, angular chrome panels. No emoji thumbnails.
   - Deeper marketplace: Gem packs, deterministic Card Shop (filters + daily
     deal), Chests, card+tower Upgrade screen with Gem top-off.
   - The Lucky Draw is UNLOCKED + advertised: featured-Mythic hero, x1/x10 pull,
     pity meter, a clean standard DROP RATES table, and a reveal animation.

   INTEGRATION HOOK (game lead -- in index.html; do NOT edit engine.js):
     <link rel="stylesheet" href="shop/shop.css">
     <script src="shop/cards_catalog.js"></script>   // window.AK_CARDS (106 cards)
     <script src="shop/shop.js"></script>
   Open the overlay from any game button:
     window.AKShop.open({ playerId: <id>, anonKey: <supabase anon key> });
   Close it (back to game):  window.AKShop.close();
   Standalone page:  shop/shop.html?player_id=<id>

   This module is a separate SURFACE. It never imports engine.js, never touches
   window.AK, never mutates game state. It posts INTENTS to the alley-kingz-shop
   edge function; the SERVER decides every grant + every draw outcome. With no
   anonKey/backend it renders embedded DEMO data, clearly labelled.
   LEGAL: Lane A only. Everything here is in-game value only -- never cashable,
   and the Lucky Draw never outputs a tradeable NFT. That is enforced server-side.
   ========================================================================== */
(function (global) {
  "use strict";

  var SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";
  var FN = SUPABASE_URL + "/functions/v1/alley-kingz-shop";

  // ---- asset base (resolved from this script's absolute URL) --------------
  // shop.js always lives at .../game/shop/shop.js, so assets are at
  // .../game/assets/. Computing from the script URL makes art paths correct
  // whether the shop is opened standalone OR embedded as an overlay in index.html.
  var THIS_SCRIPT = (document.currentScript && document.currentScript.src) || (function () {
    var s = document.querySelector('script[src$="shop/shop.js"]') ||
            document.querySelector('script[src$="shop.js"]');
    return s ? s.src : "";
  })();
  var SHOP_DIR = THIS_SCRIPT ? THIS_SCRIPT.replace(/[^/]*\.js(\?.*)?$/, "") : "";
  var ASSET_BASE = THIS_SCRIPT ? THIS_SCRIPT.replace(/[^/]*\.js(\?.*)?$/, "../assets/") : "../assets/";

  var FAC = {
    "Boneguard Crew": { cls: "fac-bone", g: "B", key: "Bone" },
    "Zoomie Syndicate": { cls: "fac-zoom", g: "Z", key: "Zoom" },
    "Leashbreak Tactix": { cls: "fac-leash", g: "L", key: "Leash" },
    "K9 Circuitry": { cls: "fac-k9", g: "K", key: "K9" },
  };
  var RARITY_ORDER = ["Common", "Rare", "Epic", "Legendary", "Mythic"];

  var cfg = { playerId: null, anonKey: null, online: false };
  var state = null;     // last get-shop payload
  var root = null;      // overlay element
  var activeTab = "gems";
  var filters = { rarity: "All", faction: "All", variant: "All" };

  // ---- safe DOM hyperscript (no innerHTML) --------------------------------
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      var v = attrs[k];
      if (v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") el[k] = v;
      else el.setAttribute(k, v);
    }
    (children || []).forEach(function (c) {
      if (c == null || c === false) return;
      el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return el;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }

  // ---- backend call (server-authoritative) --------------------------------
  function api(action, extra) {
    var bodyObj = Object.assign({ action: action, player_id: cfg.playerId }, extra || {});
    return fetch(FN, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": cfg.anonKey || "",
        "Authorization": "Bearer " + (cfg.anonKey || ""),
      },
      body: JSON.stringify(bodyObj),
    }).then(function (r) { return r.json(); });
  }

  // ---- card catalog (real art source) -------------------------------------
  function allCards() { return (global.AK_CARDS && global.AK_CARDS.length) ? global.AK_CARDS : []; }
  var _byId = null;
  function cardById(id) {
    if (!_byId) { _byId = {}; allCards().forEach(function (c) { _byId[c.id] = c; }); }
    return id == null ? _byId : _byId[id];
  }
  // If embedded without cards_catalog.js, inject it (best-effort) then continue.
  function ensureCatalog() {
    if (allCards().length || !SHOP_DIR) return Promise.resolve();
    return new Promise(function (resolve) {
      var s = document.createElement("script");
      s.src = SHOP_DIR + "cards_catalog.js";
      s.onload = function () { _byId = null; resolve(); };
      s.onerror = function () { resolve(); };
      document.head.appendChild(s);
    });
  }

  // resolve the real art file(s) for a card; falls back gracefully.
  function artCandidates(card) {
    var slug = card.slug || "";
    var num = card.num || card.id || "";
    var out = [];
    if (card.is_new) {                                   // VARIANT -> cards/<slug>.png
      if (slug) out.push(ASSET_BASE + "cards/" + slug + ".png");
    } else {                                             // ORIGINAL -> units/<num>_<slug>.png
      if (num && slug) out.push(ASSET_BASE + "units/" + num + "_" + slug.replace(/-/g, "_") + ".png");
      if (slug) out.push(ASSET_BASE + "cards/" + slug + ".png"); // future unified location
    }
    return out;
  }
  function facInfo(f) { return FAC[f] || { cls: "", g: "?", key: "?" }; }
  function rarClass(r) { return "r-" + (r || "Common"); }

  // ---- DEMO data (offline review only) ------------------------------------
  function demoDraw() {
    return {
      live: true, cost_gems: 100, cost_gems_10: 900, featured_card: "0001",
      odds: { Mythic: 0.01, Legendary: 0.04, Epic: 0.15, Rare: 0.35, Common: 0.45 },
      soft_pity_start: 30, hard_pity_mythic: 40, legendary_floor: 10,
      prize_type: "in-game-card", cashable: false, nft: false,
    };
  }
  function demoState() {
    function gemsForSku(s) { return ({ "ak-gems-rookie": 500, "ak-gems-player": 1100, "ak-gems-baller": 2500, "ak-gems-highroller": 6500, "ak-gems-kingpin": 14000 })[s] || 0; }
    function p(sku, title, desc, usd) { return { sku: sku, kind: "gems", title: title, description: desc, price_usd: usd, grants: { gems: gemsForSku(sku) } }; }
    function c(sku, title, desc, gems, rnd) { return { sku: sku, kind: "chest", title: title, description: desc, price_gems: gems, is_random: rnd, grants: {} }; }
    return {
      ok: true, test_mode: true, demo: true,
      disclaimer: "TEST MODE -- no real charges. Gems and all items are in-game value only.",
      products: [
        p("ak-gems-rookie", "Rookie Stash", "500 Gems", 4.99),
        p("ak-gems-player", "Player Pack", "1,100 Gems (+10%)", 9.99),
        p("ak-gems-baller", "Baller Bag", "2,500 Gems (+25%)", 19.99),
        p("ak-gems-highroller", "High Roller Crate", "6,500 Gems (+30%)", 49.99),
        p("ak-gems-kingpin", "Kingpin Vault", "14,000 Gems (+40%)", 99.99),
        c("chest_scrap_crate", "Scrap Crate", "200 Coins + 5 Common Scrap (fixed contents).", 40, false),
        c("chest_crew", "Crew Chest", "500 Coins + 10 Common + 3 Rare Scrap (fixed).", 150, false),
        c("chest_chop_shop", "Chop-Shop Crate", "Odds-based haul.", 400, true),
        c("chest_kingpin", "Kingpin Crate", "Odds-based haul.", 900, true),
      ],
      catalog: [],            // demo uses window.AK_CARDS directly for the Card Shop
      draw: demoDraw(),
      gem_per_copy: { Common: 2, Rare: 10, Epic: 50, Legendary: 500, Mythic: 2000 },
      level_costs: [
        { entity_type: "card", rarity: "Common", from_level: 2, copies_required: 4, coins_required: 20 },
        { entity_type: "card", rarity: "Rare", from_level: 1, copies_required: 1, coins_required: 50 },
        { entity_type: "card", rarity: "Epic", from_level: 1, copies_required: 1, coins_required: 400 },
        { entity_type: "tower", rarity: null, from_level: 1, copies_required: 1, coins_required: 200 },
      ],
      player: {
        currencies: {
          gems: 1200, coins: 4200,
          scrap_Common: 40, scrap_Rare: 12, scrap_Epic: 3, scrap_Legendary: 0, scrap_Mythic: 0,
          draw_pity_m: 18, draw_pity_l: 4, draw_total: 18,
        },
        inventory: [
          { card_id: "0010", copies: 6, level: 2 },
          { card_id: "0006", copies: 1, level: 1 },
          { card_id: "0003", copies: 0, level: 1 },
        ],
        towers: [{ tower_id: "crown", copies: 1, level: 3 }],
        chests: [{ chest_id: "chest_scrap_crate", qty: 2 }],
      },
      legal: { lane: "A", cashable: false, gacha_live: true, draw_prize: "in-game-card-only" },
    };
  }

  // ---- load + render -------------------------------------------------------
  function load() {
    if (cfg.online) {
      return api("get-shop", {}).then(function (s) { state = s.ok ? s : demoState(); render(); })
        .catch(function () { state = demoState(); render(); });
    }
    state = demoState();
    render();
    return Promise.resolve();
  }
  function bal(name) { return (state && state.player && state.player.currencies[name]) || 0; }

  function render() {
    if (!root) return;
    var demo = state.demo || !cfg.online;
    var w = (state.player && state.player.currencies) || {};
    clear(root);
    root.appendChild(topbar(w));
    root.appendChild(banner(demo));
    root.appendChild(tabsBar());
    var body = h("div", { class: "aks-body", id: "aks-body" });
    root.appendChild(body);
    root.appendChild(foot());
    renderBody(body);
  }

  function topbar(w) {
    var scrap = (w.scrap_Common || 0) + (w.scrap_Rare || 0) + (w.scrap_Epic || 0) + (w.scrap_Legendary || 0) + (w.scrap_Mythic || 0);
    return h("div", { class: "aks-top" }, [
      h("div", { class: "aks-mark" }, [
        h("div", { class: "aks-brand" }, ["ALLEY ", h("b", { text: "KINGZ" }), " // CHOP SHOP"]),
        h("div", { class: "aks-tag", text: "Back-alley black market" }),
      ]),
      h("div", { class: "aks-spacer" }),
      h("div", { class: "aks-wallet" }, [coin("gems", w.gems || 0), coin("coins", w.coins || 0), coin("scrap", scrap)]),
      h("button", { class: "aks-close", title: "Back to game", onclick: close }, ["×"]),
    ]);
  }
  function coin(cls, n) { return h("div", { class: "aks-coin " + cls }, [h("span", { class: "dot" }), fmt(n)]); }

  function banner(demo) {
    var kids = [h("span", { class: "pill", text: "Test Mode" }), h("span", { class: "muted", text: "No real charges yet" })];
    if (demo) kids.push(h("span", { class: "pill bad", text: "Demo Data" }));
    return h("div", { class: "aks-banner" }, kids);
  }

  function tabsBar() {
    var t = [["gems", "Gems"], ["cards", "Card Shop"], ["draw", "Lucky Draw"], ["chests", "Crates"], ["upgrade", "Garage"]];
    return h("div", { class: "aks-tabs" }, t.map(function (x) {
      return h("div", {
        class: "aks-tab", role: "tab", "data-tab": x[0],
        "aria-selected": String(x[0] === activeTab), text: x[1],
        onclick: function () { activeTab = x[0]; render(); },
      });
    }));
  }

  function renderBody(body) {
    clear(body);
    var nodes = activeTab === "gems" ? gemsView()
      : activeTab === "cards" ? cardsView()
        : activeTab === "draw" ? drawView()
          : activeTab === "chests" ? chestsView()
            : upgradeView();
    nodes.forEach(function (n) { body.appendChild(n); });
  }

  // ---- shared card frame (real art) ---------------------------------------
  function artBox(card, extraNodes) {
    var box = h("div", { class: "aks-art" });
    var srcs = artCandidates(card);
    var idx = 0;
    var img = h("img", { alt: card.name || "", loading: "lazy" });
    img.onerror = function () { if (idx < srcs.length) img.src = srcs[idx++]; else box.classList.add("fb-on"); };
    if (srcs.length) img.src = srcs[idx++]; else box.classList.add("fb-on");
    box.appendChild(img);
    box.appendChild(h("div", { class: "scrim" }));
    var fi = facInfo(card.faction);
    box.appendChild(h("div", { class: "fb" }, [
      h("div", { class: "g " + fi.cls, text: fi.g }),
      h("div", { class: "b", text: card.name || "" }),
      h("div", { class: "t", text: (card.rarity || "") + " // art incoming" }),
    ]));
    if (card.faction) box.appendChild(h("div", { class: "aks-fac " + fi.cls, title: card.faction, text: fi.g }));
    if (card.rarity) box.appendChild(h("div", { class: "aks-rib", text: card.rarity }));
    if (card.variant === "HEAVY") box.appendChild(h("div", { class: "aks-vstamp heavy", text: "Heavy" }));
    else if (card.variant === "STREET") box.appendChild(h("div", { class: "aks-vstamp street", text: "Street" }));
    (extraNodes || []).forEach(function (n) { box.appendChild(n); });
    return box;
  }
  function cardFrame(card, opts) {
    opts = opts || {};
    var meta = [
      h("div", { class: "aks-name", text: card.name || "" }),
      h("div", { class: "aks-sub", text: subLine(card) }),
    ];
    if (opts.descNode) meta.push(opts.descNode);
    else meta.push(h("div", { class: "aks-desc", text: card.desc || "" }));
    (opts.metaExtra || []).forEach(function (n) { meta.push(n); });
    meta.push(h("div", { class: "aks-row" }, [opts.priceNode || h("span"), opts.btnNode || h("span")]));
    return h("div", { class: "aks-card " + rarClass(card.rarity) + (opts.cls ? (" " + opts.cls) : "") }, [
      artBox(card, opts.topStamp ? [opts.topStamp] : []),
      h("div", { class: "aks-meta" }, meta),
    ]);
  }
  function subLine(card) {
    var bits = [];
    if (card.role) bits.push(card.role);
    if (card.breed) bits.push(card.breed);
    return bits.join(" // ");
  }
  function scrapPriceNode(card) {
    return h("div", { class: "aks-price scrap" }, [
      h("span", { class: "dot" }), String(card.scrap),
      h("small", { text: card.rarity + " scrap" }),
    ]);
  }
  function buyCardBtn(card) {
    var afford = !cfg.online || bal("scrap_" + card.rarity) >= card.scrap;
    return h("button", {
      class: "aks-btn", text: "Buy Copy", disabled: afford ? null : "true",
      onclick: function () { doAction("buy-card", { card_id: card.id }, "Bought a copy of " + card.name); },
    });
  }

  // ---- GEMS view -----------------------------------------------------------
  function gemsView() {
    var packs = state.products.filter(function (p) { return p.kind === "gems"; });
    return secHead("Gem Packs", "Gems are the premium in-game currency. Bought via Stripe (TEST mode). In-game value only -- never cashable.")
      .concat([grid(packs.map(gemTile))]);
  }
  function gemTile(p) {
    var gems = (p.grants && p.grants.gems) || 0;
    var bonus = (p.description || "").match(/\+\s*\d+%/);
    var best = p.sku && p.sku.indexOf("highroller") >= 0;
    var meta = [
      best ? h("div", { class: "aks-best", text: "Best Value" }) : null,
      h("div", { class: "aks-name", text: p.title }),
      h("div", { class: "aks-sub", text: fmt(gems) + " Gems" }),
      bonus ? h("div", { class: "aks-bonus", text: "Bonus " + bonus[0].replace(/\s/g, "") })
        : h("div", { class: "aks-desc", text: "Premium currency" }),
      h("div", { class: "aks-row" }, [
        h("span", { class: "aks-price usd", text: "$" + Number(p.price_usd).toFixed(2) }),
        h("button", { class: "aks-btn", text: "Buy", onclick: function () { buyGems(p.sku); } }),
      ]),
    ];
    return h("div", { class: "aks-card aks-gem" + (best ? " best" : "") }, [
      h("div", { class: "aks-art" }, [h("div", { class: "gemglyph", text: "◆" })]),
      h("div", { class: "aks-meta" }, meta),
    ]);
  }

  // ---- CARD SHOP view (deterministic, real art, filters, daily deal) ------
  function facKey(f) { return facInfo(f).key; }
  function shopCards() {
    // Online + backend marks an active catalog -> intersect with AK_CARDS art.
    if (cfg.online && state.catalog && state.catalog.length) {
      return state.catalog.map(function (row) {
        var m = cardById(row.card_id) || {};
        return Object.assign({}, m, {
          id: row.card_id, name: row.name || m.name, rarity: row.rarity || m.rarity,
          scrap: row.card_shop_price != null ? row.card_shop_price : m.scrap,
          desc: row.description || m.desc,
        });
      });
    }
    return allCards();
  }
  function applyFilters(cards) {
    return cards.filter(function (c) {
      if (filters.rarity !== "All" && c.rarity !== filters.rarity) return false;
      if (filters.faction !== "All" && facKey(c.faction) !== filters.faction) return false;
      if (filters.variant !== "All" && (c.variant || "ORIGINAL") !== filters.variant) return false;
      return true;
    });
  }
  function chip(label, group, value) {
    return h("span", {
      class: "aks-chip", role: "button", "aria-pressed": String(filters[group] === value),
      text: label, onclick: function () { filters[group] = value; render(); },
    });
  }
  function filterBar(count) {
    var rar = [["All", "All"], ["Common", "Common"], ["Rare", "Rare"], ["Epic", "Epic"], ["Legendary", "Legend"], ["Mythic", "Mythic"]];
    var fac = [["All", "All"], ["Bone", "Boneguard"], ["Zoom", "Zoomie"], ["Leash", "Leashbreak"], ["K9", "K9"]];
    var var_ = [["All", "All"], ["ORIGINAL", "Original"], ["HEAVY", "Heavy"], ["STREET", "Street"]];
    return h("div", { class: "aks-filters" }, [
      h("span", { class: "aks-flabel", text: "Rarity" })].concat(
        rar.map(function (x) { return chip(x[1], "rarity", x[0]); }),
        [h("span", { class: "aks-flabel", text: "Crew" })],
        fac.map(function (x) { return chip(x[1], "faction", x[0]); }),
        [h("span", { class: "aks-flabel", text: "Build" })],
        var_.map(function (x) { return chip(x[1], "variant", x[0]); }),
        [h("span", { class: "aks-count", text: count + " cards" })],
      ));
  }
  function dailyCard() {
    var cards = allCards();
    if (!cards.length) return null;
    var pool = cards.filter(function (c) { return c.rarity === "Epic" || c.rarity === "Rare"; });
    if (!pool.length) pool = cards;
    var d = new Date();
    var key = d.getUTCFullYear() * 1000 + d.getUTCMonth() * 40 + d.getUTCDate();
    return pool[key % pool.length];
  }
  function dailyHero() {
    var card = dailyCard();
    if (!card) return null;
    return h("div", { class: "aks-daily-hero" }, [
      h("div", { class: "gift", text: "◈" }),
      h("div", { class: "copy" }, [
        h("h4", { text: "Daily Deal" }),
        h("p", null, ["Today's rotating drop: ", h("b", { text: card.name }),
          " (" + card.rarity + "). Grab the copy with Scrap before the lot resets."]),
      ]),
      scrapPriceNode(card),
      buyCardBtn(card),
      h("div", { class: "aks-reset", text: "Resets 00:00 UTC" }),
    ]);
  }
  function cardsView() {
    var cards = shopCards();
    var filtered = applyFilters(cards);
    var nodes = secHead("Card Shop", "Deterministic. Spend matching-rarity Scrap Tokens for the EXACT card you want -- real art, no random draws. Duplicates feed the Garage upgrade.");
    var hero = dailyHero();
    if (hero) nodes.push(hero);
    nodes.push(filterBar(filtered.length));
    if (!filtered.length) { nodes.push(emptyCard("No cards match the filter.")); return nodes; }
    nodes.push(grid(filtered.map(function (c) {
      return cardFrame(c, { priceNode: scrapPriceNode(c), btnNode: buyCardBtn(c) });
    })));
    return nodes;
  }

  // ---- LUCKY DRAW view (unlocked advertisement) ---------------------------
  function drawView() {
    var d = state.draw || demoDraw();
    var w = (state.player && state.player.currencies) || {};
    var gems = w.gems || 0;
    var feat = cardById(d.featured_card) || cardById("0001") || allCards()[0] || { name: "$BCARDD", rarity: "Mythic" };

    // featured-Mythic art
    var srcs = artCandidates(feat); var i = 0;
    var featImg = h("img", { alt: feat.name });
    var artWrap = h("div", { class: "aks-pull-art" });
    featImg.onerror = function () { if (i < srcs.length) featImg.src = srcs[i++]; else featImg.remove(); };
    if (srcs.length) featImg.src = srcs[i++];
    artWrap.appendChild(featImg);
    artWrap.appendChild(h("div", { class: "glow" }));
    artWrap.appendChild(h("div", { class: "tag", text: "Featured Mythic" }));

    function pullBtn(n, cost, cls) {
      var disabled = cfg.online && gems < cost;
      return h("button", {
        class: "aks-pull-btn" + (cls ? (" " + cls) : ""), disabled: disabled ? "true" : null,
        onclick: function () { doDraw(n, cost); },
      }, [h("span", { text: "Pull x" + n }), h("span", { class: "cost", text: fmt(cost) + " Gems" })]);
    }
    var hero = h("div", { class: "aks-banner-hero" }, [
      artWrap,
      h("div", { class: "aks-hero-copy" }, [
        h("div", { class: "aks-hero-kicker", text: "The Crown Banner" }),
        h("div", { class: "aks-hero-title" }, ["PULL FOR ", h("b", { text: feat.name })]),
        h("p", { class: "aks-hero-sub" }, ["Rip the chop-shop crate for a shot at ", h("b", { text: "Mythic" }),
          " dogs. Every pull lands a card -- and a ", h("b", { text: "guaranteed Mythic by pull " + d.hard_pity_mythic }),
          ". Prizes are in-game cards for your crew."]),
        h("div", { class: "aks-pull-cta" }, [pullBtn(1, d.cost_gems), pullBtn(10, d.cost_gems_10, "ten")]),
      ]),
    ]);

    var pity = pityMeter(d, w);
    var rates = dropRates(d);
    return [h("div", { class: "aks-draw" }, [hero]), pity, rates];
  }
  function pityMeter(d, w) {
    var pm = w.draw_pity_m || 0, pl = w.draw_pity_l || 0;
    function bar(cls, lab, lead, cur, max) {
      var pct = Math.max(0, Math.min(100, (cur / max) * 100));
      return h("div", { class: "row" }, [
        h("div", { class: "lab" + (cls === "leg" ? " leg" : "") }, [lab + " ", h("b", { text: lead })]),
        h("div", { class: "bar" + (cls === "leg" ? " leg" : "") }, [h("i", { style: "width:" + pct + "%" })]),
        h("div", { class: "ct", text: cur + " / " + max }),
      ]);
    }
    return h("div", { class: "aks-pity" }, [
      bar("m", "Mythic guaranteed within", String(d.hard_pity_mythic), pm, d.hard_pity_mythic),
      bar("leg", "Legendary or better within", String(d.legendary_floor), pl, d.legendary_floor),
    ]);
  }
  function dropRates(d) {
    var order = ["Mythic", "Legendary", "Epic", "Rare", "Common"];
    var rows = order.map(function (r) {
      var pctNum = (d.odds[r] || 0) * 100;
      var pct = (pctNum % 1 === 0 ? pctNum.toFixed(0) : pctNum.toFixed(1));
      return h("div", { class: "rrow rr-" + r }, [
        h("span", { class: "dot" }),
        h("span", { class: "k", text: r }),
        h("span", { class: "track" }, [h("b", { style: "width:" + Math.max(4, pctNum) + "%" })]),
        h("span", { class: "v", text: pct + "%" }),
      ]);
    });
    return h("div", { class: "aks-rates" }, [
      h("div", { class: "rh" }, [h("span", { class: "t", text: "Drop Rates" }), h("span", { class: "n", text: "per pull" })]),
    ].concat(rows, [
      h("div", { class: "rfoot", text: "Mythic odds climb after pull " + d.soft_pity_start + " and are guaranteed by pull " + d.hard_pity_mythic + ". A Legendary or better lands at least every " + d.legendary_floor + " pulls. Prizes are in-game cards." }),
    ]));
  }
  function doDraw(n, cost) {
    if (!cfg.online) {
      var d = state.draw || demoDraw();
      var results = localRoll(d, n);
      showReveal(results);
      toast("Demo pull -- connect a backend for real grants.", "ok");
      return;
    }
    api("open-draw", { pulls: n }).then(function (r) {
      if (r.ok) { showReveal(r.results || []); load(); }
      else { toast(humanErr(r), "bad"); }
    }).catch(function () { toast("Draw unavailable.", "bad"); });
  }
  // client-only mock roll for offline DEMO review (server is authoritative live)
  function localRoll(d, n) {
    var cards = allCards();
    var byR = {}; cards.forEach(function (c) { (byR[c.rarity] || (byR[c.rarity] = [])).push(c); });
    var out = [];
    for (var i = 0; i < n; i++) {
      var x = Math.random(), acc = 0, rar = "Common";
      var tiers = [["Mythic", d.odds.Mythic], ["Legendary", d.odds.Legendary], ["Epic", d.odds.Epic], ["Rare", d.odds.Rare], ["Common", d.odds.Common]];
      for (var t = 0; t < tiers.length; t++) { acc += tiers[t][1]; if (x < acc) { rar = tiers[t][0]; break; } }
      var pool = byR[rar] || byR["Common"] || cards;
      var card = pool[Math.floor(Math.random() * pool.length)] || { name: "Card", rarity: rar };
      out.push({ card_id: card.id, name: card.name, rarity: rar });
    }
    return out;
  }
  function showReveal(results) {
    var ov = h("div", { class: "aks-reveal" });
    ov.appendChild(h("div", { class: "rv-title", text: results.length > 1 ? (results.length + "-Pull Haul") : "You Pulled" }));
    var g = h("div", { class: "rv-grid" });
    results.forEach(function (r) {
      var c = cardById(r.card_id) || { name: r.name, rarity: r.rarity };
      var card = h("div", { class: "rv-card " + rarClass(r.rarity) });
      var srcs = artCandidates(c); var i = 0;
      var img = h("img", { alt: r.name || "" });
      img.onerror = function () {
        if (i < srcs.length) img.src = srcs[i++];
        else { img.remove(); if (!card.querySelector(".fb")) card.insertBefore(h("div", { class: "fb", text: (r.rarity || "?").charAt(0) }), card.firstChild); }
      };
      if (srcs.length) img.src = srcs[i++]; else card.appendChild(h("div", { class: "fb", text: (r.rarity || "?").charAt(0) }));
      card.appendChild(img);
      card.appendChild(h("div", { class: "cap" }, [
        h("div", { class: "nm", text: r.name || c.name || r.card_id }),
        h("div", { class: "rr", text: r.rarity }),
      ]));
      g.appendChild(card);
    });
    ov.appendChild(g);
    ov.appendChild(h("div", { class: "rv-foot" }, [
      h("button", { class: "aks-btn wide", text: "Collect", onclick: function () { ov.classList.remove("show"); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 220); } }),
    ]));
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add("show"); });
  }

  // ---- CRATES view ---------------------------------------------------------
  function chestsView() {
    var chests = state.products.filter(function (p) { return p.kind === "chest"; });
    var owned = {}; ((state.player && state.player.chests) || []).forEach(function (x) { owned[x.chest_id] = x.qty; });
    var nodes = secHead("Crates", "Fixed-contents crates grant exactly what they say. Want odds-based rewards? Rip the Lucky Draw.");
    nodes.push(grid(chests.map(function (p) {
      var have = owned[p.sku] || 0, soon = p.is_random;
      var meta = [
        soon ? h("span", { class: "aks-soon", text: "Soon" }) : null,
        h("div", { class: "aks-name", text: p.title }),
        h("div", { class: "aks-desc", text: p.description }),
        h("div", { class: "aks-row" }, [
          soon ? h("span", { class: "aks-owned", text: "Use Lucky Draw" })
            : h("span", { class: "aks-owned", text: have ? ("Owned x" + have) : "earn or buy" }),
          soon ? h("button", { class: "aks-btn ghost", text: "To Draw", onclick: function () { activeTab = "draw"; render(); } })
            : (have > 0
              ? h("button", { class: "aks-btn", text: "Open (" + have + ")", onclick: function () { doAction("open-chest", { chest_id: p.sku }, "Opened " + p.title); } })
              : h("button", { class: "aks-btn ghost", disabled: "true", text: "None owned" })),
        ]),
      ];
      // Real crate art (auto-routed to Leonardo via the art-factory queue); the
      // unicode glyph is the fallback shown until the cron paints assets/shop/<sku>.png.
      var cbox = h("div", { class: "aks-art" });
      var cimg = h("img", { alt: p.title, loading: "lazy" });
      cimg.onerror = function () { cimg.remove(); cbox.appendChild(h("div", { class: "crate", text: soon ? "▤" : "▣" })); };
      cimg.src = ASSET_BASE + "shop/" + p.sku + ".png";
      cbox.appendChild(cimg);
      return h("div", { class: "aks-chest aks-card" + (soon ? " gated" : "") }, [
        cbox,
        h("div", { class: "aks-meta" }, meta),
      ]);
    })));
    return nodes;
  }

  // ---- GARAGE / UPGRADE view ----------------------------------------------
  function upgradeView() {
    var inv = (state.player && state.player.inventory) || [];
    var gpc = state.gem_per_copy || { Common: 2, Rare: 10, Epic: 50, Legendary: 500, Mythic: 2000 };
    var cardTiles = inv.map(function (it) {
      var c = cardById(it.card_id) || { id: it.card_id, name: it.card_id, rarity: "Common" };
      var cost = costFor("card", c.rarity, it.level);
      var atMax = it.level >= 10;
      var need = cost ? cost.copies_required : 0;
      var missing = Math.max(0, need - it.copies);
      var coinsOk = !cost || bal("coins") >= cost.coins_required;
      var copyOk = !cost || it.copies + bal("scrap_" + c.rarity) >= need;
      var canLevel = !atMax && cost && coinsOk && copyOk;
      var gemCost = missing * (gpc[c.rarity] || 50);

      var metaExtra = [
        lvTrack(it.level),
        cost ? copiesBar(it.copies, need, c.rarity) : null,
        cost ? h("div", { class: "need" }, [
          "Next: ",
          h("span", { class: it.copies >= need ? "ok" : "no", text: it.copies + "/" + need + " copies" }),
          " + " + fmt(cost.coins_required) + " coins",
        ]) : h("div", { class: "need", text: atMax ? "Maxed out" : "" }),
        (!atMax && missing > 0) ? h("div", { class: "aks-topoff" }, [
          h("span", { class: "g", text: "◆" }),
          "Top-off " + missing + " " + (missing === 1 ? "copy" : "copies") + " for " + fmt(gemCost) + " gems",
        ]) : null,
      ];
      var btn = atMax
        ? h("button", { class: "aks-btn ghost", disabled: "true", text: "MAX" })
        : h("button", { class: "aks-btn", text: "Level Up", disabled: canLevel ? null : "true", onclick: function () { doAction("level-up-card", { card_id: it.card_id }, c.name + " leveled up"); } });
      var topBtn = (!atMax && missing > 0)
        ? h("button", { class: "aks-btn ghost", text: "Top-off", onclick: function () { doAction("top-off-card", { card_id: it.card_id }, "Topped off " + c.name); } })
        : null;
      return cardFrame(Object.assign({}, c), {
        cls: "aks-up",
        descNode: h("div", { class: "aks-desc", text: "Level " + it.level + " / 10  -  " + it.copies + " copies owned" }),
        metaExtra: metaExtra,
        priceNode: topBtn || h("span"),
        btnNode: btn,
      });
    });

    var towerTiles = ((state.player && state.player.towers) || []).map(function (t) {
      var cost = costFor("tower", null, t.level), atMax = t.level >= 10;
      var canLevel = !atMax && cost && bal("coins") >= cost.coins_required && t.copies >= cost.copies_required;
      var synthetic = { id: t.tower_id, name: towerName(t.tower_id), rarity: "Legendary", role: "Tower", breed: "" };
      return cardFrame(synthetic, {
        cls: "aks-up",
        descNode: h("div", { class: "aks-desc", text: "Level " + t.level + " / 10  -  " + t.copies + " tower copies" }),
        metaExtra: [
          lvTrack(t.level),
          cost ? h("div", { class: "need" }, ["Next: ",
            h("span", { class: t.copies >= cost.copies_required ? "ok" : "no", text: t.copies + "/" + cost.copies_required + " copies" }),
            " + " + fmt(cost.coins_required) + " coins"]) : h("div", { class: "need", text: atMax ? "Maxed out" : "" }),
        ],
        btnNode: atMax ? h("button", { class: "aks-btn ghost", disabled: "true", text: "MAX" })
          : h("button", { class: "aks-btn", text: "Level Up", disabled: canLevel ? null : "true", onclick: function () { doAction("level-up-tower", { tower_id: t.tower_id }, towerName(t.tower_id) + " leveled up"); } }),
      });
    });

    var all = cardTiles.concat(towerTiles);
    var nodes = secHead("Garage", "Level cards + towers 1 to 10 with duplicate copies + coins. Short on copies? Top-off the exact missing copies with Gems. The curve is HP/DMG only -- a maxed Common never beats a base Mythic. No pay-to-win.");
    nodes.push(all.length ? grid(all) : emptyCard("No crew yet. Win matches or buy copies in the Card Shop."));
    return nodes;
  }
  function lvTrack(level) {
    var seg = [];
    for (var i = 1; i <= 10; i++) seg.push(h("i", { class: i <= level ? "on" : "" }));
    return h("div", { class: "lvtrack" }, seg);
  }
  function copiesBar(copies, need, rarity) {
    var pct = Math.max(0, Math.min(100, (copies / Math.max(1, need)) * 100));
    return h("div", { class: "copies " + rarClass(rarity) }, [h("b", { style: "width:" + pct + "%" })]);
  }

  // ---- helpers -------------------------------------------------------------
  function grid(nodes) { return h("div", { class: "aks-grid" }, nodes); }
  function secHead(t, s) {
    return [
      h("div", { class: "aks-sec" }, [h("div", { class: "aks-sec-title", text: t })]),
      h("div", { class: "aks-sec-sub", text: s }),
    ];
  }
  function emptyCard(t) { return h("div", { class: "aks-empty", text: t }); }
  function costFor(type, rarity, level) {
    return (state.level_costs || []).find(function (c) {
      return c.entity_type === type && (c.rarity || null) === (rarity || null) && c.from_level === level;
    });
  }
  function towerName(id) { return ({ crown: "Crown Tower", left_garrison: "Left Garrison", right_garrison: "Right Garrison" })[id] || id; }
  function fmt(n) { return Number(n || 0).toLocaleString("en-US"); }
  function foot() {
    return h("div", { class: "aks-foot" }, [
      h("b", { text: "Alley Kingz items are in-game value only and have no cash value." }),
      " Gems are purchased through Stripe (currently ",
      h("b", { text: "TEST MODE" }),
      " -- no real charges). Cards, Coins and Scrap are earned through play. An Everlight Ventures arcade.",
    ]);
  }

  // ---- intent dispatch (server decides) -----------------------------------
  function doAction(action, extra, okMsg) {
    if (!cfg.online) { toast("Demo mode -- connect a backend to spend.", "bad"); return; }
    api(action, extra).then(function (r) {
      if (r.ok) { toast(okMsg, "ok"); load(); }
      else if (r.gated) { toast(r.message || "Coming soon.", "bad"); }
      else { toast(humanErr(r), "bad"); }
    }).catch(function () { toast("Network error.", "bad"); });
  }
  function buyGems(sku) {
    if (!cfg.online) { toast("Demo mode -- gem checkout needs the backend + TEST Stripe.", "bad"); return; }
    api("buy-gems", {
      sku: sku,
      success_url: location.href.split("#")[0] + "#gems-ok={CHECKOUT_SESSION_ID}",
      cancel_url: location.href.split("#")[0],
    }).then(function (r) {
      if (r.ok && r.url) { toast("TEST checkout -- no real charge.", "ok"); location.href = r.url; }
      else { toast(r.detail || humanErr(r), "bad"); }
    }).catch(function () { toast("Checkout unavailable.", "bad"); });
  }
  function humanErr(r) {
    var m = {
      INSUFFICIENT_SCRAP: "Not enough Scrap Tokens.", INSUFFICIENT_FUNDS: "Not enough copies/coins.",
      INSUFFICIENT_GEMS: "Not enough Gems.", MAX_LEVEL: "Already max level.",
      NO_CHEST_OWNED: "You do not own that crate.", CARD_NOT_OWNED: "You do not own that card yet.",
      NO_TOPOFF_NEEDED: "You already have the copies for this level.", EMPTY_CATALOG: "Catalog unavailable.",
    };
    return m[r.error] || r.message || r.error || "Could not complete.";
  }

  // ---- toast ---------------------------------------------------------------
  var toastEl = null, toastT = null;
  function toast(msg, kind) {
    if (!toastEl) { toastEl = h("div", { class: "aks-toast" }); document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.className = "aks-toast show " + (kind || "");
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl.className = "aks-toast " + (kind || ""); }, 2600);
  }

  // ---- public API (the integration hook) ----------------------------------
  function ensureRoot() {
    if (root) return;
    root = h("div", { class: "akshop", role: "dialog", "aria-label": "Alley Kingz Shop" });
    root.setAttribute("hidden", "");
    document.body.appendChild(root);
  }
  function qs(k) { return new URLSearchParams(location.search).get(k); }
  function open(opts) {
    opts = opts || {};
    cfg.playerId = opts.playerId || cfg.playerId || qs("player_id") || localStorage.getItem("ak_player_id");
    cfg.anonKey = opts.anonKey || cfg.anonKey || global.AK_SUPABASE_ANON_KEY || null;
    cfg.online = !!(cfg.anonKey && cfg.playerId);
    if (cfg.playerId) try { localStorage.setItem("ak_player_id", cfg.playerId); } catch (e) {}
    ensureRoot();
    root.removeAttribute("hidden");
    ensureCatalog().then(load);
  }
  function close() { if (root) root.setAttribute("hidden", ""); }

  global.AKShop = {
    open: open, close: close,
    config: function (o) { Object.assign(cfg, o || {}); cfg.online = !!(cfg.anonKey && cfg.playerId); },
    _state: function () { return state; },
  };

  if (document.body && document.body.dataset && document.body.dataset.akshopStandalone === "1") {
    document.addEventListener("DOMContentLoaded", function () { open({}); });
  }
})(typeof window !== "undefined" ? window : this);
