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

  var SUPABASE_URL = "https://mfghdobptredxxhbjwyz.supabase.co";
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
  // AK-ART: custom faction crest art (the class indicator). Shop is at /shop/ -> ../ prefix.
  var FAC_CREST = { "Boneguard Crew": "Crest_Boneguard", "Zoomie Syndicate": "Crest_Zoomie", "Leashbreak Tactix": "Crest_Leashbreak", "K9 Circuitry": "Crest_K9" };
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

  // AK-SHOPFIX item 2: cfg must never go stale. Re-read identity from the SAME
  // places the account layer writes -- localStorage('ak_player_id') +
  // window.AK_SUPABASE_ANON_KEY -- so a signed-in player is NEVER told to log
  // in. Called on open AND at the top of every action. Upgrades cfg when the
  // identity is present; the ak-auth listener handles a clean sign-out drop.
  function recomputeCfg() {
    try {
      var pid = (typeof localStorage !== "undefined" && localStorage) ? localStorage.getItem("ak_player_id") : null;
      if (pid) cfg.playerId = pid;
      var ak = global.AK_SUPABASE_ANON_KEY || null;
      if (ak) cfg.anonKey = ak;
    } catch (_) {}
    cfg.online = !!(cfg.anonKey && cfg.playerId);
    return cfg.online;
  }
  // React to sign-in/out without a reload (account layer dispatches 'ak-auth').
  // Sign-in -> flip online + reload the shop under the new identity; sign-out
  // -> drop cleanly back to Local Mode. Either way the UI re-renders.
  function onAuthEvent(ev) {
    try {
      var u = ev && ev.detail && ev.detail.user;
      if (u && u.id) { cfg.playerId = u.id; cfg.anonKey = cfg.anonKey || global.AK_SUPABASE_ANON_KEY || null; }
      else { cfg.playerId = null; }   // signed out
    } catch (_) {}
    recomputeCfg();
    if (root && !root.hasAttribute("hidden")) { try { load(); } catch (_) { render(); } }
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

  // AK-SCRAP: shared economy module (game/economy.js). One source of truth for
  // chest tables, scrap dupes and keys, shared with index.html. Lazy-inject it
  // when the shop runs standalone (shop.html) so both surfaces stay in sync.
  function econ() { return global.AK_ECON || null; }
  function ensureEconomy() {
    if (econ() || !SHOP_DIR) return Promise.resolve();
    return new Promise(function (resolve) {
      var s = document.createElement("script");
      s.src = SHOP_DIR + "../economy.js?v=32";   // AK-GARAGE: bust stale pre-garage AK_ECON
      s.onload = function () { resolve(); };
      s.onerror = function () { resolve(); };
      document.head.appendChild(s);
    });
  }
  // Local profile view (offline wallet source of truth = ak_profile).
  function localProfile() {
    var e = econ();
    if (e) { try { return e.loadProfile(); } catch (_) {} }
    try {
      if (typeof localStorage === "undefined" || !localStorage) return null;
      var p = JSON.parse(localStorage.getItem("ak_profile") || "null");
      return (p && typeof p === "object") ? p : null;
    } catch (_) { return null; }
  }

  // resolve the real art file(s) for a card; falls back gracefully.
  function artCandidates(card) {
    if (typeof window !== "undefined" && window.akCardArtRel) { var _r = window.akCardArtRel(card); if (_r) return [ASSET_BASE + _r]; }   // AK-ARTRESOLVER: single source of truth (canon.js), shared with the game
    // AK-FIX 2026-06-17: canon cards carry name + cardNumber, NOT slug/num/id -> the old code produced an
    // EMPTY candidate list for every deck/shop card -> "art incoming" placeholder everywhere. Derive the
    // hyphen-slug from the name + use cardNumber, and try BOTH art dirs (units/ originals, cards/ variants)
    // so the onerror chain lands on whichever exists. The art is all on disk; this just builds the right path.
    var slug = card.slug || String(card.name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    var num = card.num || card.id || card.cardNumber || "";
    var out = [];
    if (slug) {
      if (card.type === "spell" || card.abilityType === "spell") {
        out.push(ASSET_BASE + "spells/" + slug + ".png");   // AK-SPELLART 2026-06-18: spell card art (glyph fallback until the Seedance art lands)
      } else {
        if (num) out.push(ASSET_BASE + "units/" + num + "_" + slug.replace(/-/g, "_") + ".png");  // originals 0001-0048
        out.push(ASSET_BASE + "cards/" + slug + ".png");                                           // variants 0049-0106 (hyphen filenames)
      }
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
      ok: true, test_mode: false, demo: true,   // AK-SHOPFIX item 1: never advertise test mode -- charges are REAL
      disclaimer: "Gems are purchased through Stripe secure checkout. All items are in-game value only.",
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
    recomputeCfg();   // AK-SHOPFIX item 2: identity may have arrived since open()
    // AK-SHOPFIX item 3: heal pass -- any owned card with NO copies entry gets
    // copies=1 so the Garage upgrade math always sees the cards the player holds.
    try { var eh = econ(); if (eh && eh.healCopies && eh.mutateProfile) eh.mutateProfile(function (p) { eh.healCopies(p); }); } catch (_) {}
    if (cfg.online) {
      return api("get-shop", {}).then(function (s) { state = s.ok ? s : demoState(); render(); })
        .catch(function () { state = demoState(); render(); });
    }
    state = demoState();
    render();
    return Promise.resolve();
  }
  // AK-SCRAP: balances are LOCAL-FIRST when signed out -- coins/scrap come from
  // the real ak_profile (earned in matches + chests), never from demo numbers.
  // Gems are SERVER-ONLY: signed out, you have zero gems by definition.
  function bal(name) {
    // AK-WALLET-MERGE: gems are SERVER money (signed out = 0); coins/scrap/keys
    // are LOCAL-FIRST everywhere -- matches and crates pay into ak_profile, so
    // the signed-in shop must read the same pocket the game pays into.
    if (name === "gems") {
      return cfg.online ? ((state && state.player && state.player.currencies.gems) || 0) : 0;
    }
    var p = localProfile();
    if (!p) return 0;
    if (name === "coins") return p.coins | 0;
    if (name.indexOf("scrap_") === 0) return ((p.scrap || {})[name.slice(6)]) | 0;
    if (name === "keys") return p.keys | 0;
    return 0;
  }
  // Unified wallet for the header: server currencies when online, ak_profile
  // when local. Always carries gems + coins + per-rarity scrap (+ keys).
  function walletView() {
    // AK-WALLET-MERGE: one wallet the player can trust -- server gems + local everything else.
    var p = localProfile() || {};
    var s = p.scrap || {};
    return {
      gems: bal("gems"), coins: p.coins | 0, keys: p.keys | 0,
      scrap_Common: s.Common | 0, scrap_Rare: s.Rare | 0, scrap_Epic: s.Epic | 0,
      scrap_Legendary: s.Legendary | 0, scrap_Mythic: s.Mythic | 0,
    };
  }

  function render() {
    if (!root || !state) return;   // AK-SCRAP: openLocalChest can fire before the shop UI loads
    var demo = state.demo || !cfg.online;
    var w = walletView();
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
    var scrapTip = "Scrap -- C " + fmt(w.scrap_Common || 0) + " / R " + fmt(w.scrap_Rare || 0) +
      " / E " + fmt(w.scrap_Epic || 0) + " / L " + fmt(w.scrap_Legendary || 0) + " / M " + fmt(w.scrap_Mythic || 0);
    var wallet = [coin("gems", w.gems || 0), coin("coins", w.coins || 0), coin("scrap", scrap, scrapTip)];
    if ((w.keys || 0) > 0) wallet.push(coin("keys", w.keys, "Chest keys -- open an owned crate free"));  // AK-KEYS
    return h("div", { class: "aks-top" }, [
      h("div", { class: "aks-mark" }, [
        h("div", { class: "aks-brand" }, ["ALLEY ", h("b", { text: "KINGZ" }), " // CHOP SHOP"]),
        h("div", { class: "aks-tag", text: "Back-alley black market" }),
      ]),
      h("div", { class: "aks-spacer" }),
      h("div", { class: "aks-wallet" }, wallet),
      h("button", { class: "aks-close", title: "Back to game", onclick: function () { try { location.href = "../"; } catch (_) { close(); } } }, ["×"]),
    ]);
  }
  function coin(cls, n, tip) {
    var ic = /gem/.test(cls) ? "cur_gems" : /gold/.test(cls) ? "cur_gold" : /scrap/.test(cls) ? "cur_scrap" : /key/.test(cls) ? "cur_keys" : /bone/.test(cls) ? "cur_bones" : null;  // AK-ART: wallet currency icons (existing art)
    var badge;
    if (ic) { badge = h("img", { class: "aks-curico", src: "../assets/ui/" + ic + ".jpg", alt: "" }); badge.onerror = function () { var d = h("span", { class: "dot" }); if (badge.parentNode) badge.parentNode.replaceChild(d, badge); }; }
    else badge = h("span", { class: "dot" });
    return h("div", { class: "aks-coin " + cls, title: tip || null }, [badge, fmt(n)]);
  }

  // AK-SHOPFIX item 1+2: NO test-mode strings anywhere -- charges are REAL.
  // Signed in -> a small green "Signed In" indicator + honest secure-checkout
  // line. Signed out -> a "Local Mode" pill (still no "no real charges" copy).
  function banner(demo) {
    if (demo) {
      return h("div", { class: "aks-banner" }, [
        h("span", { class: "pill bad", text: "Local Mode" }),
        h("span", { class: "muted", text: "Coins, Scrap + Crates are your real match earnings. Sign in for Gems." }),
      ]);
    }
    return h("div", { class: "aks-banner" }, [
      h("span", { class: "pill good", text: "● Signed In" }),
      h("span", { class: "muted", text: "Gems purchase via secure Stripe checkout -- real charges. All items are in-game value only." }),
    ]);
  }

  function tabsBar() {
    var t = [["deck", "Deck Lab"], ["gems", "Gems"], ["cards", "Card Shop"], ["draw", "Lucky Draw"], ["chests", "Crates"], ["upgrade", "Collection"], ["codex2", "Codex"], ["handlers", "Handlers"], ["drip2", "Drip"], ["crew2", "Crew"], ["pass2", "Alley Pass"], ["hit2", "Hit List"], ["street", "Street Code"]];
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
    var nodes = activeTab === "deck" ? deckView()
      : activeTab === "gems" ? gemsView()
      : activeTab === "cards" ? cardsView()
        : activeTab === "draw" ? drawView()
          : activeTab === "chests" ? chestsView()
            : activeTab === "handlers" ? handlersView()
              : activeTab === "codex2" ? codexView()
              : activeTab === "street" ? streetCodeView()
              : activeTab === "drip2" ? dripView()
              : activeTab === "crew2" ? crewView()
              : activeTab === "pass2" ? passView()
              : activeTab === "hit2" ? hitView()
              : upgradeView();
    nodes.forEach(function (n) { body.appendChild(n); });
  }

  // ---- AK-LORE: tagline/bio lookup -----------------------------------------
  // cards_lore.js exposes window.AK_LORE_GET (keyed by cardNumber). Guarded so
  // a missing/failed lore file never breaks the shop -- everything degrades to
  // the pre-lore layout.
  function loreOf(card) {
    try {
      if (!card || typeof global.AK_LORE_GET !== "function") return null;
      return global.AK_LORE_GET(card.num || card.id || card.cardNumber);
    } catch (_e) { return null; }
  }
  function oneLineTag(s) {
    s = String(s || "").replace(/\s+/g, " ").trim();
    return s.length > 64 ? (s.slice(0, 61) + "...") : s;
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
    if (card.faction) {
      var _cf = FAC_CREST[card.faction], _fb = h("div", { class: "aks-fac " + fi.cls, title: card.faction });
      if (_cf) { var _im = h("img", { class: "aks-fac-img", src: "../assets/ui/" + _cf + ".jpg", alt: "" }); _im.onerror = function () { _fb.textContent = fi.g; }; _fb.appendChild(_im); }
      else _fb.textContent = fi.g;
      box.appendChild(_fb);
    }
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
    var lr = loreOf(card);                                                  // AK-LORE: one-line tagline on every card frame
    if (lr && lr.tagline) meta.push(h("div", { class: "aks-tag", title: lr.tagline, text: "“" + oneLineTag(lr.tagline) + "”" }));
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
  // AK-GEMBUY: direct gems -> card copy. Server debits real gems (audited),
  // the copy lands in the local crew like every other earned card.
  var GEM_PER_COPY = { Common: 2, Rare: 10, Epic: 50, Legendary: 500, Mythic: 2000 };
  function gemBuyBtn(card) {
    if (!cfg.online) return null;
    var price = GEM_PER_COPY[card.rarity] || 0;
    if (!price) return null;
    var afford = bal("gems") >= price;
    return h("button", {
      class: "aks-btn gold gem-cost", text: fmt(price), disabled: afford ? null : "true",
      title: "Buy a copy with Gems",
      onclick: function () {
        recomputeCfg();   // AK-SHOPFIX item 2
        api("gem-buy-copy", { card_id: card.id }).then(function (r) {
          if (r.ok) {
            // AK-SHOPFIX item 3: ALWAYS bank a real copy (first buy used to grant
            // the name with 0 copies -- the Balboa case). addCopy = owned + copies++.
            grantCardCopy(card, 1);
            toast("Bought " + card.name + " for " + fmt(price) + " Gems.", "ok"); load();
          } else { toast(humanErr(r), "bad"); }
        }).catch(function () { toast("Network error.", "bad"); });
      },
    });
  }
  function buyCardBtn(card) {
    // AK-STACK 2026-06-13: an owned card is NOT disabled -- you can keep buying
    // copies to stack toward Garage upgrades (operator). The only gate is Scrap.
    // Owned cards show "Stack +1" so it's clear another copy is being added.
    var p = localProfile();
    var owned = !!(p && Array.isArray(p.owned) && p.owned.indexOf(card.name) >= 0);
    var afford = bal("scrap_" + card.rarity) >= card.scrap;
    return h("button", {
      class: "aks-btn", text: owned ? "Stack +1" : "Buy Copy", disabled: afford ? null : "true",
      title: owned ? "Buy another copy -- stacks toward the next upgrade" : "Buy a copy",
      onclick: function () { doAction("buy-card", { card_id: card.id }, (owned ? "Stacked a copy of " : "Bought a copy of ") + card.name); },
    });
  }

  // ---- GEMS view -----------------------------------------------------------
  function promoBanner() {
    var ps = (state.active_promos || []);
    if (!ps.length) return null;
    var top = ps.slice().sort(function (a, b) { return b.percent - a.percent; })[0];
    return h("div", { class: "aks-promobanner" }, [
      h("span", { class: "aks-promo-flame", text: "\uD83D\uDD25" }),
      h("span", { class: "aks-promo-txt", text: top.label + " -- up to " + top.percent + "% OFF. Limited time." }),
    ]);
  }
  function gemsView() {
    var packs = state.products.filter(function (p) { return p.kind === "gems"; });
    var head = secHead("Gem Packs", "Gems are the premium in-game currency. Secure checkout via Stripe. In-game value only -- never cashable.");
    var banner = promoBanner();
    if (banner) head = [banner].concat(head);
    return head.concat([grid(packs.map(gemTile))]);
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
      p.sale ? h("div", { class: "aks-saletag", text: p.sale.label + " -" + p.sale.percent_off + "%" }) : null,
      h("div", { class: "aks-row" }, p.sale ? [
        h("span", { class: "aks-price was", text: "$" + Number(p.sale.original_price_usd).toFixed(2) }),
        h("span", { class: "aks-price now", text: "$" + Number(p.sale.sale_price_usd).toFixed(2) }),
        h("button", { class: "aks-btn hot", text: "Buy", onclick: function () { buyGems(p.sku); } }),
      ] : [
        h("span", { class: "aks-price usd", text: "$" + Number(p.price_usd).toFixed(2) }),
        h("button", { class: "aks-btn", text: "Buy", onclick: function () { buyGems(p.sku); } }),
      ]),
    ];
    // Real gem-pack art (auto-routed to Leonardo via the art-factory queue); the
    // diamond glyph is the fallback shown until the cron paints assets/shop/<sku>.png.
    var gbox = h("div", { class: "aks-art" });
    var gimg = h("img", { alt: p.title, loading: "lazy" });
    gimg.onerror = function () { gimg.remove(); gbox.appendChild(h("div", { class: "gemglyph", text: "◆" })); };
    gimg.src = ASSET_BASE + "shop/" + p.sku + ".png";
    gbox.appendChild(gimg);
    return h("div", { class: "aks-card aks-gem" + (best ? " best" : "") }, [
      gbox,
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
      (function () { var g = h("div", { class: "gift" }); var im = h("img", { class: "gift-img", src: "../assets/ui/daily_drop.png", alt: "" }); im.onerror = function () { g.textContent = "◈"; }; g.appendChild(im); return g; })(),  // AK-ART: daily-deal hero art (existing daily_drop.png)
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
      return cardFrame(c, { priceNode: scrapPriceNode(c), btnNode: h("div", { class: "aks-btnrow" }, [buyCardBtn(c), gemBuyBtn(c)]) });
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
    recomputeCfg();   // AK-SHOPFIX item 2
    if (!cfg.online) {
      try {
        var d = state.draw || demoDraw();
        var results = localRoll(d, n);
        syncDrawResults(results);          // demo pulls land in ak_profile; dupes pay scrap (AK-SCRAP)
        showReveal(results);
        toast("Demo pull -- cards saved to your crew. Dupes paid out as Scrap.", "ok");
        render();                          // wallet may have new scrap
      } catch (err) { toast("Pull failed -- try again.", "bad"); try { render(); } catch (_) {} }
      return;
    }
    api("open-draw", { pulls: n }).then(function (r) {
      if (r.ok) { syncDrawResults(r.results || []); showReveal(r.results || []); load(); }
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
  function showReveal(results, opts) {
    var ov = h("div", { class: "aks-reveal" });
    var title = (opts && opts.title) || (results.length > 1 ? (results.length + "-Pull Haul") : "You Pulled");
    ov.appendChild(h("div", { class: "rv-title", text: title }));
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
      if (r.dupe) card.appendChild(h("div", { class: "rv-dupe", text: "DUPE +" + (r.scrap || 0) + "s" }));  // AK-SCRAP
      // AK-LORE: every reveal shows the tagline; a NEW card (not a dupe) also
      // unrolls its bio so the first pull of a dog tells its street story.
      var lr = loreOf(c);
      var capKids = [
        h("div", { class: "nm", text: r.name || c.name || r.card_id }),
        h("div", { class: "rr", text: r.rarity }),
      ];
      if (lr && lr.tagline) capKids.push(h("div", { class: "rv-tag", text: "“" + oneLineTag(lr.tagline) + "”" }));
      if (!r.dupe && lr && lr.bio) capKids.push(h("div", { class: "rv-bio", text: lr.bio }));
      card.appendChild(h("div", { class: "cap" }, capKids));
      g.appendChild(card);
    });
    ov.appendChild(g);
    if (opts && opts.chips && opts.chips.length) {           // AK-SCRAP: chest haul chips (coins/scrap/keys)
      ov.appendChild(h("div", { class: "rv-chips" }, opts.chips.map(function (ch) {
        return h("div", { class: "rv-chip " + (ch.cls || "") }, [h("span", { class: "dot" }), ch.text]);
      })));
    }
    ov.appendChild(h("div", { class: "rv-foot" }, [
      h("button", { class: "aks-btn wide", text: "Collect", onclick: function () { ov.classList.remove("show"); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 220); } }),
    ]));
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add("show"); });
  }

  // ---- CRATES view ---------------------------------------------------------
  // AK-KEYS: earned street crates (match rewards in ak_profile.chests) open
  // FREE right here. Keys open one chest of any OWNED tier without consuming
  // the chest. Gem-bought crates below stay 100% server-authoritative.
  var EARNED_TIER_META = {
    wood:    { title: "Wood Crate",    desc: "1 card + 15-30 coins + Common scrap." },
    bronze:  { title: "Bronze Crate",  desc: "2 cards + 50-90 coins + Common scrap." },
    silver:  { title: "Silver Crate",  desc: "3 cards + 110-170 coins + 4 Rare scrap. One drop floors at Rare." },
    gold:    { title: "Gold Crate",    desc: "4 cards + 200-300 coins + 2 Epic scrap. One drop floors at Epic." },
    diamond: { title: "Diamond Crate", desc: "5 cards + 350-500 coins + 4 Epic scrap. Epic floor x2, 5% Mythic shot, +1 Key back." },
  };
  function openLocalChest(tier, useKey) {
    // AK-SHOPFIX item 4: local spend, never awaits the server; full try/catch so
    // a thrown error can never freeze the crate UI mid-open. openChest is ONE
    // atomic profile write, and we render() after every outcome.
    try {
      var e = econ();
      if (!e) { toast("Economy still loading -- try again.", "bad"); return; }
      var pool = allCards().map(function (c) { return { id: c.id, name: c.name, rarity: c.rarity }; });
      var r = e.openChest(tier, { pool: pool, useKey: !!useKey, perks: (global.AK && global.AK.PERKS) || null });
      if (!r || !r.ok) { toast(humanErr(r || {}), "bad"); render(); return; }
      showChestReveal(r);
      render();
    } catch (err) { toast("Could not open crate -- try again.", "bad"); try { render(); } catch (_) {} }
  }
  function showChestReveal(r) {
    var meta = EARNED_TIER_META[r.tier] || { title: "Crate" };
    var chips = [];
    if (r.coins) chips.push({ cls: "coins", text: "+" + fmt(r.coins) + " Coins" });
    var e = econ();
    var rars = (e && e.RARITIES) || ["Common", "Rare", "Epic", "Legendary", "Mythic"];
    rars.forEach(function (rar) {
      if (r.scrap && r.scrap[rar]) chips.push({ cls: "scrap", text: "+" + fmt(r.scrap[rar]) + " " + rar + " Scrap" });
    });
    if (r.keys) chips.push({ cls: "keys", text: "+" + r.keys + " Key" });
    showReveal(r.cards || [], { title: meta.title.toUpperCase() + " CRACKED", chips: chips });
  }
  function earnedCrateTile(tier, p, keys) {
    var meta = EARNED_TIER_META[tier];
    var have = ((p.chests || {})[tier]) | 0;
    var btnRow = [
      h("span", { class: "aks-owned", text: have ? ("Owned x" + have) : "Win matches" }),
      h("button", {
        class: "aks-btn", text: have ? ("Open (" + have + ")") : "None", disabled: have ? null : "true",
        onclick: function () { openLocalChest(tier, false); },
      }),
    ];
    if (keys > 0 && have > 0) {
      btnRow.push(h("button", {
        class: "aks-btn ghost", text: "Use Key", title: "Open one " + meta.title + " free -- keeps the crate",
        onclick: function () { openLocalChest(tier, true); },
      }));
    }
    var cbox = h("div", { class: "aks-art" });
    var cimg = h("img", { alt: meta.title, loading: "lazy" });
    cimg.onerror = function () { cimg.remove(); cbox.appendChild(h("div", { class: "crate", text: "▣" })); };
    cimg.src = ASSET_BASE + "shop/earned_" + tier + ".png";
    cbox.appendChild(cimg);
    return h("div", { class: "aks-chest aks-card earned tier-" + tier }, [
      cbox,
      h("div", { class: "aks-meta" }, [
        h("div", { class: "aks-name", text: meta.title }),
        h("div", { class: "aks-desc", text: meta.desc }),
        h("div", { class: "aks-row wrap" }, btnRow),
      ]),
    ]);
  }
  function earnedChestsSection() {
    var e = econ();
    if (!e) return [];
    var p = null;
    try { p = e.loadProfile(); } catch (_) { return []; }
    var keys = p.keys | 0;
    var nodes = secHead("Street Crates",
      "Earned in matches -- open FREE right here. Bigger wins = bigger tiers (sweep under the clock for Diamond). Keys crack an owned crate without spending it.");
    if (keys > 0) nodes.push(h("div", { class: "aks-keysline" }, [
      h("span", { class: "dot" }), keys + (keys === 1 ? " Key" : " Keys") + " ready",
    ]));
    nodes.push(grid(((e.CHEST_TIERS) || []).map(function (t) { return earnedCrateTile(t, p, keys); })));
    return nodes;
  }
  function chestsView() {
    var chests = state.products.filter(function (p) { return p.kind === "chest"; });
    var owned = {}; ((state.player && state.player.chests) || []).forEach(function (x) { owned[x.chest_id] = x.qty; });
    var nodes = earnedChestsSection();   // AK-KEYS: earned crates first
    nodes = nodes.concat(secHead("Gem Crates", "Fixed-contents crates grant exactly what they say. Want odds-based rewards? Rip the Lucky Draw."));
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
  // AK-GARAGE: the Garage IS the collection (operator canon 2026-06-11 --
  // "my collection should be in my garage. They should be one and the same").
  // Every card in ak_profile.owned shows here with its level, copies toward
  // the next level, banked dupe surplus and the SAME local upgrade economics
  // the Deck Lab collection rides (AK_ECON.levelUpCard -> ak_profile
  // .cardLvls / .copies / .coins). Server inventory is no longer the card
  // source -- the local profile is the canon pocket the game pays into, so
  // the two surfaces can never disagree. Towers stay server-side (no local
  // tower economy exists).
  var GAR_TUNE_ATTRS = [                 // mirrors index.html AK-ATTRS verbatim (key, label, kind, per-attr max)
    { k: "hp", lab: "HP", kind: "boost", max: 5 }, { k: "dmg", lab: "DMG", kind: "boost", max: 5 },
    { k: "def", lab: "DEFENSE", kind: "guard", max: 4 }, { k: "spdef", lab: "SPEC DEF", kind: "guard", max: 4 },
    { k: "agi", lab: "AGILITY", kind: "boost", max: 5 }, { k: "aspd", lab: "ATK SPD", kind: "boost", max: 5 },
  ];
  var TUNE_CAP = 8;  // total tune points per card (mirrors index.html)
  // AK-CARDX: per-card skill tree (Garage Tuning) in the Skill tab -- spend p.sp on a card's
  // attrs, exactly like the Deck Lab. Writes p.skills.cards[name][attr] + p.sp via AK_ECON.
  function tuneState(name, p) {
    var ct = (p && p.skills && p.skills.cards && p.skills.cards[name]) || {};
    var total = 0; GAR_TUNE_ATTRS.forEach(function (a) { total += Math.max(0, ct[a.k] | 0); });
    return { ct: ct, total: total };
  }
  function shopBuyTune(name, stat) {
    var e = econ(), p = localProfile(); if (!e || !p) return false;
    var a = null; GAR_TUNE_ATTRS.forEach(function (x) { if (x.k === stat) a = x; }); if (!a) return false;
    if ((p.sp | 0) < 1) { toast("No skill points -- earn SP from level-ups + city clears.", "bad"); return false; }
    var st = tuneState(name, p);
    if (st.total >= TUNE_CAP) { toast(name + " is fully tuned (" + TUNE_CAP + " pts).", "bad"); return false; }
    if ((st.ct[stat] | 0) >= a.max) { toast(a.lab + " is maxed (" + a.max + ").", "bad"); return false; }
    e.mutateProfile(function (pr) {
      if (!pr.skills) pr.skills = {}; if (!pr.skills.cards) pr.skills.cards = {};
      var c = pr.skills.cards[name] || {}; c[stat] = (c[stat] | 0) + 1; pr.skills.cards[name] = c; pr.sp = (pr.sp | 0) - 1;
    });
    return true;
  }
  function shopRefundTune(name, stat) {
    var e = econ(), p = localProfile(); if (!e || !p) return false;
    var ct = (p.skills && p.skills.cards && p.skills.cards[name]) || null;
    if (!ct || (ct[stat] | 0) < 1) return false;
    e.mutateProfile(function (pr) {
      var c = pr.skills && pr.skills.cards && pr.skills.cards[name]; if (!c || (c[stat] | 0) < 1) return;
      c[stat] = (c[stat] | 0) - 1; pr.sp = (pr.sp | 0) + 1;
      var left = 0; GAR_TUNE_ATTRS.forEach(function (x) { left += (c[x.k] | 0); });
      if (left < 1) delete pr.skills.cards[name];
    });
    return true;
  }
  function tuneSummary(name, p) {
    var ct = (p && p.skills && p.skills.cards && p.skills.cards[name]) || null;
    if (!ct) return null;
    var parts = [], total = 0;
    GAR_TUNE_ATTRS.forEach(function (a) {
      var v = Math.max(0, ct[a.k] | 0);
      if (v > 0) { total += v; parts.push((a.kind === "guard" ? "-" : "+") + (v * 5) + "% " + a.lab); }
    });
    return total > 0 ? { total: total, text: parts.join(" / ") } : null;
  }
  function garageCards() {
    var p = localProfile();
    var owned = (p && Array.isArray(p.owned)) ? p.owned : [];
    var byName = {}; allCards().forEach(function (c) { byName[c.name] = c; });
    var out = [];
    owned.forEach(function (n) { if (byName[n]) out.push(byName[n]); });
    var ro = {}; RARITY_ORDER.forEach(function (r, i) { ro[r] = i; });
    out.sort(function (a, b) {
      return (ro[b.rarity] || 0) - (ro[a.rarity] || 0) || String(a.name).localeCompare(String(b.name));
    });
    return out;
  }
  function doGarageLevel(card, after) {
    // AK-SHOPFIX item 4: LOCAL spend -- never awaits the server. levelUpCard is
    // ONE atomic mutateProfile, and the whole path is wrapped so a thrown error
    // can never leave the Garage frozen mid-level-up.
    // AK-SHOPFIX item 5: render() re-renders the garage tile and `after`
    // re-opens the detail panel, so stats are never stale after a level-up.
    try {
      var e = econ();
      if (!e || !e.levelUpCard) { toast("Economy still loading -- try again.", "bad"); return; }
      var r = e.levelUpCard({ name: card.name, rarity: card.rarity });
      if (r && r.ok) {
        toast(card.name + " hits Lv" + r.level + ". +6% HP / +6% DMG per level.", "ok");
        render();              // re-render the garage tile immediately
        if (after) after();    // re-render/re-open the detail panel immediately
      } else { toast(humanErr(r || {}), "bad"); render(); }
    } catch (err) { toast("Could not level up -- try again.", "bad"); try { render(); } catch (_) {} }
  }
  function spareChip(nd) {
    if (!nd || nd.spare <= 0) return null;
    return h("div", { class: "aks-spare", title: "Duplicate copies beyond the next level -- they bank toward future levels" }, [
      h("span", { class: "dot" }), "+" + nd.spare + " spare " + (nd.spare === 1 ? "dupe" : "dupes") + " banked",
    ]);
  }
  function needLine(nd, coinsHave) {
    if (nd.atMax) return h("div", { class: "need", text: "Maxed out" });
    return h("div", { class: "need" }, [
      "Next: ",
      h("span", { class: nd.have >= nd.copies ? "ok" : "no", text: Math.min(nd.have, nd.copies) + "/" + nd.copies + " copies" }),
      " + " + fmt(nd.coins) + " coins",
      h("span", { class: coinsHave >= nd.coins ? "ok" : "no", text: " (" + fmt(coinsHave) + " held)" }),
    ]);
  }
  function garageTile(e, p, c) {
    var nd = e.upgradeNeed(c.name, c.rarity, p);
    var coinsHave = p.coins | 0;
    var canLevel = !nd.atMax && nd.have >= nd.copies && coinsHave >= nd.coins;
    var ts = tuneSummary(c.name, p);
    var metaExtra = [
      lvTrack(nd.lv),
      ts ? h("div", { class: "need" }, [h("span", { class: "ok", text: "Garage Tuning: " + ts.text + " (stacks on level)" })]) : null,
      nd.atMax ? null : copiesBar(nd.have, nd.copies, c.rarity),
      needLine(nd, coinsHave),
      spareChip(nd),
    ];
    var btn = nd.atMax
      ? h("button", { class: "aks-btn ghost", disabled: "true", text: "MAX" })
      : h("button", { class: "aks-btn", text: "Level Up", disabled: canLevel ? null : "true", onclick: function () { doGarageLevel(c); } });
    return cardFrame(c, {
      cls: "aks-up" + (nd.spare > 0 ? " has-spare" : ""),
      descNode: h("div", { class: "aks-desc", text: "Level " + nd.lv + " / " + (e.CARD_LV_CAP || 10) + "  -  " + nd.have + " copies banked" }),
      metaExtra: metaExtra,
      priceNode: h("button", { class: "aks-btn ghost", text: "Inspect", onclick: function () { garageDetail(c); } }),
      btnNode: btn,
    });
  }
  // The same detail/tuning read the Deck Lab collection shows on a card tap --
  // art, lore, level track, copies + spare, tuning summary, upgrade button.
  // (The shop is a standalone page, so this is the equivalent inline panel;
  // both read ak_profile, so the numbers always match the Deck Lab overlay.)
  // AK-CARDX 2026-06-15: canon combat stats (window.CANON_CARDS) for the Info tab.
  function canonStat(c) {
    try {
      var arr = global.CANON_CARDS || []; var num = String(c.num || c.id || "");
      var cc = null;
      for (var i = 0; i < arr.length; i++) { if (String(arr[i].cardNumber || "") === num || arr[i].name === c.name) { cc = arr[i]; break; } }
      if (!cc) return null;
      return { cost: cc.cost, hp: cc.hp, dmg: cc.damage, range: cc.range, atkspd: cc.attack_speed, ability: cc.ability || null };
    } catch (_) { return null; }
  }
  function deckGet() {
    try { var d = JSON.parse(localStorage.getItem("ak_decks") || "null"); var ai = parseInt(localStorage.getItem("ak_active") || "0", 10) || 0;
      return { decks: d, ai: ai, cards: (d && d[ai] && Array.isArray(d[ai].cards)) ? d[ai].cards.slice() : null }; } catch (_) { return { decks: null, ai: 0, cards: null }; }
  }
  function deckSwap(slotIdx, name) {
    try { var g = deckGet(); if (!g.cards || !g.decks) return false; g.decks[g.ai].cards[slotIdx] = name; localStorage.setItem("ak_decks", JSON.stringify(g.decks)); var e=econ(); if(e&&e.mutateProfile) e.mutateProfile(function(p){ if(Array.isArray(p.decks)&&p.decks[g.ai]&&Array.isArray(p.decks[g.ai].cards)) p.decks[g.ai].cards[slotIdx]=name; }); return true; } catch (_) { return false; }
  }

  // AK-ART: keyword icon (custom art) with glyph fallback. Shop is at /shop/ -> ../ prefix.
  function kwIco(k) {
    var img = h("img", { class: "gd-kwg-img", src: "../assets/ui/kw_" + k.id + ".jpg", alt: "" });
    img.onerror = function () { var s = document.createElement("span"); s.className = "gd-kwg"; s.textContent = k.glyph; if (img.parentNode) img.parentNode.replaceChild(s, img); };
    return img;
  }
  // AK-KEYWORDS: GU-style keyword chips for the card Info tab (legibility).
  function keywordChips(c) {
    var reg = global.AK_KEYWORDS_BY_ID, map = global.AK_CARD_KEYWORDS;
    if (!reg || !map) return null;
    var ids = map[c.num || c.id || ""] || map[c.name] || [];
    if (!ids.length) return null;
    return h("div", { class: "gd-kw" }, ids.map(function (id) {
      var k = reg[id]; if (!k) return null;
      return h("span", { class: "gd-kwchip", title: k.label + " -- " + k.desc, style: "--kw:" + k.color }, [
        kwIco(k), h("span", { class: "gd-kwl", text: k.label }) ]);
    }));
  }
  // AK-CARDX: the MULTI-TABBED card experience (operator: "card/deckbuilder/upgrade/skill tree
  // should be a multi-tabbed card experience"). Info + Deck + Upgrade + Skill, in the shop style.
  function codexTab2(c) {
    var n = [], lr = loreOf(c);
    var cc = (global.CANON_CARDS && global.CANON_CARDS[c.num || c.cardNumber || c.id]) || {};
    if (lr && lr.tagline) n.push(h("div", { class: "gd-tag", text: "\u201c" + lr.tagline + "\u201d" }));
    if (lr && lr.bio) n.push(h("div", { class: "gd-bio", text: lr.bio }));
    else if (c.desc) n.push(h("div", { class: "gd-bio", text: c.desc }));
    n.push(h("div", { class: "gd-stats" }, [
      h("div", { class: "gd-stat" }, [h("b", { text: String(cc["class"] || c.faction || "--") }), h("span", { text: "Crew" })]),
      h("div", { class: "gd-stat" }, [h("b", { text: String(cc.role || c.role || "--") }), h("span", { text: "Role" })]),
      h("div", { class: "gd-stat" }, [h("b", { text: String(cc.breed || c.breed || "--") }), h("span", { text: "Breed" })]),
      h("div", { class: "gd-stat" }, [h("b", { text: String(c.rarity || "--") }), h("span", { text: "Rarity" })]) ]));
    var reg = global.AK_KEYWORDS_BY_ID, map = global.AK_CARD_KEYWORDS;
    if (reg && map) { var ids = map[c.num || c.id || ""] || map[c.name] || [];
      ids.forEach(function (id) { var k = reg[id]; if (k) n.push(h("div", { class: "gd-ability" }, [h("b", { style: "color:" + k.color, text: k.glyph + " " + k.label }), h("span", { text: " -- " + k.desc })])); }); }
    var SYN = { "Boneguard Crew": "Bone Wall -- 3+ Boneguard alive share a regenerating shield.", "Zoomie Syndicate": "Pack Speed -- 3+ Zoomies move faster together.", "Leashbreak Tactix": "Targeting Net -- 3+ Leashbreak hit harder.", "K9 Circuitry": "Overclock -- 3+ K9 units cut spell cooldowns." };
    var sk = SYN[cc["class"] || c.factionName || ""];
    if (sk) n.push(h("div", { class: "gd-note", text: "CREW SYNERGY -- " + sk }));
    if (!n.length) n.push(h("div", { class: "gd-note", text: "No codex entry yet." }));
    return n;
  }
  function garageDetail(c) {
    var e = econ(), p = localProfile();
    if (!e || !p) { toast("Economy still loading -- try again.", "bad"); return; }
    var lr = loreOf(c), st = canonStat(c), tab = "info";
    var ov = h("div", { class: "aks-reveal aks-gd" });
    function closeOv() { ov.classList.remove("show"); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 220); }
    var bodyEl = h("div", { class: "gd-body" });
    var TABS = [["info", "Info"], ["codex", "Codex"], ["deck", "Deck"], ["upgrade", "Upgrade"], ["skill", "Skill"]];
    var tabbar = h("div", { class: "gd-tabs" }, TABS.map(function (t) {
      return h("div", { class: "gd-tab" + (t[0] === tab ? " on" : ""), "data-t": t[0], text: t[1], onclick: function () { tab = t[0]; refresh(); } });
    }));
    function statRow(lbl, v) { return h("div", { class: "gd-stat" }, [h("b", { text: String(v == null ? "--" : v) }), h("span", { text: lbl })]); }
    function infoTab() {
      var n = [];
      if (lr && lr.tagline) n.push(h("div", { class: "gd-tag", text: "“" + oneLineTag(lr.tagline) + "”" }));
      if (lr && lr.bio) n.push(h("div", { class: "gd-bio", text: lr.bio })); else if (c.desc) n.push(h("div", { class: "gd-bio", text: c.desc }));
      if (st) n.push(h("div", { class: "gd-stats" }, [statRow("Cost", st.cost), statRow("HP", st.hp), statRow("DMG", st.dmg), statRow("Range", st.range), statRow("Atk Spd", st.atkspd)]));
      if (st && st.ability && (st.ability.name || st.ability.description)) n.push(h("div", { class: "gd-ability" }, [h("b", { text: st.ability.name || "Ability" }), h("span", { text: " -- " + (st.ability.description || "") })]));
      else if (c.desc && !(lr && lr.bio)) {} // already shown
      var kw = keywordChips(c); if (kw) n.push(kw);
      return n;
    }
    function deckTab() {
      var g = deckGet();
      if (!g.cards) return [h("div", { class: "gd-note", text: "No active 11-card deck yet -- build one in the game's Deck Lab, then manage it here." })];
      var inDeck = g.cards.indexOf(c.name) >= 0;
      var n = [h("div", { class: "gd-sub", text: inDeck ? "In your active deck" : "Not in your active deck -- tap a slot below to swap " + c.name + " in" })];
      n.push(h("div", { class: "gd-decklist" }, g.cards.map(function (nm, i) {
        return h("button", { class: "gd-deckcard" + (nm === c.name ? " me" : ""), text: nm, onclick: function () { if (nm === c.name) return; if (deckSwap(i, c.name)) { toast(c.name + " swapped in for " + nm, "good"); refresh(); } else toast("Could not edit deck", "bad"); } });
      })));
      return n;
    }
    function upgradeTab() {
      var nd = e.upgradeNeed(c.name, c.rarity, p), coinsHave = p.coins | 0;
      var canLevel = !nd.atMax && nd.have >= nd.copies && coinsHave >= nd.coins;
      return [
        lvTrack(nd.lv),
        nd.atMax ? h("div", { class: "gd-sub", text: "Maxed out" }) : copiesBar(nd.have, nd.copies, c.rarity),
        needLine(nd, coinsHave), spareChip(nd),
        h("div", { class: "aks-row" }, [
          nd.atMax ? h("button", { class: "aks-btn ghost", disabled: "true", text: "MAX" })
            : h("button", { class: "aks-btn", text: "Level Up (" + fmt(nd.coins) + "c)", disabled: canLevel ? null : "true", onclick: function () { doGarageLevel(c, function () { p = localProfile(); refresh(); }); } }),
        ]),
      ];
    }
    function skillTab() {
      var pp = localProfile() || p;
      var st = tuneState(c.name, pp), spFree = pp ? (pp.sp | 0) : 0;
      var owned = !!(pp && pp.owned && pp.owned.indexOf(c.name) >= 0);
      var n = [h("div", { class: "gd-sub", text: "Skill Tree  -  " + st.total + "/" + TUNE_CAP + " pts spent  -  " + spFree + " SP free" })];
      if (!owned) { n.push(h("div", { class: "gd-note", text: "Own this dog to tune it -- win it in matches or the Card Shop." })); return n; }
      var rows = GAR_TUNE_ATTRS.map(function (a) {
        var cur = st.ct[a.k] | 0, canPlus = spFree > 0 && st.total < TUNE_CAP && cur < a.max, eff = cur > 0 ? ((a.kind === "guard" ? "-" : "+") + (cur * 5) + "%") : "";
        return h("div", { class: "gd-trow" }, [
          h("span", { class: "gd-tlab", text: a.lab }),
          h("span", { class: "gd-tval", text: cur + "/" + a.max + (eff ? ("  " + eff) : "") }),
          h("button", { class: "gd-tbtn" + (cur > 0 ? "" : " off"), text: "−", onclick: function () { if (shopRefundTune(c.name, a.k)) { p = localProfile(); refresh(); } } }),
          h("button", { class: "gd-tbtn" + (canPlus ? "" : " off"), text: "+", onclick: function () { if (shopBuyTune(c.name, a.k)) { p = localProfile(); refresh(); } } }),
        ]);
      });
      n.push(h("div", { class: "gd-tree" }, rows));
      n.push(h("div", { class: "gd-note", text: "1 SP = +5% per point (DEFENSE / SPEC DEF cut damage taken). Stacks on top of the card's level. Max " + TUNE_CAP + " pts per dog." }));
      return n;
    }
    function refresh() {
      Array.prototype.forEach.call(tabbar.children, function (el) { el.classList.toggle("on", el.getAttribute("data-t") === tab); });
      clear(bodyEl);
      var nodes = tab === "info" ? infoTab() : tab === "codex" ? codexTab2(c) : tab === "deck" ? deckTab() : tab === "upgrade" ? upgradeTab() : skillTab();
      nodes.forEach(function (n) { if (n) bodyEl.appendChild(n); });
    }
    ov.appendChild(h("div", { class: "gd-card " + rarClass(c.rarity) }, [
      artBox(c),
      h("div", { class: "gd-name", text: c.name }),
      h("div", { class: "gd-meta", text: [c.rarity, c.faction, c.role, c.breed].filter(Boolean).join(" // ") }),
      tabbar, bodyEl,
      h("button", { class: "aks-btn ghost", style: "margin-top:10px", text: "Close", onclick: closeOv }),
    ]));
    ov.onclick = function (ev) { if (ev.target === ov) closeOv(); };
    document.body.appendChild(ov);
    refresh();
    requestAnimationFrame(function () { ov.classList.add("show"); });
  }
  // ====================================================================
  // AK-HANDLER: the Commander hub -- a Chop-Shop tab. Pick your commander
  // (rides every match) + spend Bones on its skill tree. Reads/writes the
  // SAME ak_profile the game's loadProfile/startMatch use, so an equip or a
  // node unlock applies on the very next match. Roster = window.AK_HANDLERS.
  // ====================================================================
  function handlersData() { return global.AK_HANDLERS || []; }
  function handlersById() { return global.AK_HANDLERS_BY_ID || {}; }
  function handlerState() {
    var p = localProfile() || {};
    var hp = (p.handlers && typeof p.handlers === "object") ? p.handlers : {};
    if (typeof hp.selected !== "string") hp.selected = "handler_mender";
    if (typeof hp.bones !== "number") hp.bones = 0;
    if (!hp.unlocked || typeof hp.unlocked !== "object") hp.unlocked = {};
    handlersData().forEach(function (H) {
      if (!Array.isArray(hp.unlocked[H.id])) hp.unlocked[H.id] = [];
      H.skill_tree.forEach(function (n) { if (n.bones === 0 && hp.unlocked[H.id].indexOf(n.id) < 0) hp.unlocked[H.id].push(n.id); });
    });
    return hp;
  }
  // persist a mutation to ak_profile.handlers (AK_ECON if present, else direct LS)
  function writeHandlers(mut) {
    var e = econ();
    if (e && e.mutateProfile) {
      e.mutateProfile(function (p) { if (!p.handlers || typeof p.handlers !== "object") p.handlers = { selected: "handler_mender", bones: 0, unlocked: {} }; mut(p.handlers); });
      return true;
    }
    try {
      var p = JSON.parse(localStorage.getItem("ak_profile") || "null") || {};
      if (!p.handlers || typeof p.handlers !== "object") p.handlers = { selected: "handler_mender", bones: 0, unlocked: {} };
      mut(p.handlers);
      localStorage.setItem("ak_profile", JSON.stringify(p));
      return true;
    } catch (_) { return false; }
  }
  function handlerOwned(hid) { var hp = handlerState(); return (hp.unlocked && hp.unlocked[hid]) || []; }
  function handlerCanBuy(hid, node) {
    var hp = handlerState(), own = (hp.unlocked && hp.unlocked[hid]) || [];
    if (own.indexOf(node.id) >= 0) return false;
    if ((hp.bones | 0) < node.bones) return false;
    if (node.requires) {
      var reqs = String(node.requires).split(",").map(function (s) { return s.trim(); }).filter(Boolean);
      if (!reqs.every(function (r) { return own.indexOf(r) >= 0; })) return false;
    }
    return true;
  }
  // AK-HANDLERART: render the commander portrait (handler.art) with the emoji
  // glyph as the fallback if the image is missing/fails (e.g. Tracker not yet made).
  function handlerArtEl(H, big) {
    var glyph = (H && H.portrait) || "\u2605";
    if (H && H.art) {
      // shop is at /shop/ -> handler.art ("assets/...") needs ../ to reach /assets/ (game-root).
      var _src = (/^(https?:|\/)/.test(H.art) ? H.art : "../" + H.art);
      var img = h("img", { class: "aks-hart" + (big ? " big" : ""), src: _src, alt: H.name || "" });
      img.onerror = function () { var g = document.createElement("div"); g.className = "aks-hglyph" + (big ? " big" : ""); g.textContent = glyph; if (img.parentNode) img.parentNode.replaceChild(g, img); };
      return img;
    }
    return h("div", { class: "aks-hglyph" + (big ? " big" : "") }, [glyph]);
  }
  // AK-HANDLERART2: full-bleed portrait (the art IS the card). Glyph fallback fills.
  function handlerArtFull(H) {
    var glyph = (H && H.portrait) || "\u2605";
    if (H && H.art) {
      var _src = (/^(https?:|\/)/.test(H.art) ? H.art : "../" + H.art);
      var img = h("img", { class: "aks-hfull", src: _src, alt: H.name || "" });
      img.onerror = function () { var g = document.createElement("div"); g.className = "aks-hfull aks-hfg"; g.textContent = glyph; if (img.parentNode) img.parentNode.replaceChild(g, img); };
      return img;
    }
    return h("div", { class: "aks-hfull aks-hfg" }, [glyph]);
  }
  function handlersView() {
    var list = handlersData();
    if (!list.length) return secHead("Handlers", "Commander roster unavailable -- reload the shop.");
    var hp = handlerState(), eqH = handlersById()[hp.selected];
    var nodes = secHead("Handlers", "Your commander rides into every match -- a tap-fired SPECIAL + an always-on PASSIVE. Spend Bones (won in matches) on their skill tree. Tap a commander to open it.");
    nodes.push(h("div", { class: "aks-hbar" }, [
      h("span", { class: "aks-hbones", text: "🦴 " + (hp.bones | 0) + " Bones" }),
      h("span", { class: "aks-heqd", text: "Equipped: " + (eqH ? eqH.name : "--") }),
    ]));
    nodes.push(h("div", { class: "aks-hgrid" }, list.map(function (H) {
      var eq = hp.selected === H.id;
      return h("div", { class: "aks-hcard full r-Legendary" + (eq ? " eq" : ""), style: "--acc:" + (H.accent || "#D4AF37"), onclick: function () { handlerDetail(H); } }, [
        handlerArtFull(H),
        h("div", { class: "aks-hcap" }, [
          h("div", { class: "aks-hnm", text: H.name }),
          h("div", { class: "aks-hsp", text: H.special.name }),
        ]),
        eq ? h("div", { class: "aks-hbadge", text: "EQUIPPED" }) : null,
      ]);
    })));
    return nodes;
  }
  function handlerDetail(H) {
    var tab = "info";
    var ov = h("div", { class: "aks-reveal aks-gd" });
    function closeOv() { ov.classList.remove("show"); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 220); }
    var bodyEl = h("div", { class: "gd-body" });
    var TABS = [["info", "Info"], ["special", "Special"], ["passive", "Passive"], ["skill", "Skill Tree"]];
    var tabbar = h("div", { class: "gd-tabs" }, TABS.map(function (t) {
      return h("div", { class: "gd-tab" + (t[0] === tab ? " on" : ""), "data-t": t[0], text: t[1], onclick: function () { tab = t[0]; refresh(); } });
    }));
    function kv(lbl, v) { return h("div", { class: "gd-stat" }, [h("b", { text: String(v) }), h("span", { text: lbl })]); }
    function infoTab() {
      var hp = handlerState(), eq = hp.selected === H.id, sp = H.special, ps = H.passive;
      var n = [h("div", { class: "gd-bio", text: H.breed })];
      n.push(h("div", { class: "aks-row", style: "margin:10px 0" }, [
        eq ? h("button", { class: "aks-btn ghost", disabled: "true", text: "✓ EQUIPPED" })
          : h("button", { class: "aks-btn", text: "EQUIP " + H.name.toUpperCase(), onclick: function () { writeHandlers(function (hh) { hh.selected = H.id; }); toast(H.name + " equipped -- rides your next match", "good"); refresh(); render(); } }),
      ]));
      n.push(h("div", { class: "gd-ability" }, [h("b", { text: sp.name }), h("span", { text: " -- " + sp.desc })]));
      n.push(h("div", { class: "gd-ability" }, [h("b", { text: ps.name }), h("span", { text: " -- " + ps.desc })]));
      return n;
    }
    function specialTab() {
      var sp = H.special;
      return [
        h("div", { class: "gd-tag", text: "“" + sp.name + "”" }),
        h("div", { class: "gd-bio", text: sp.desc }),
        h("div", { class: "gd-stats" }, [kv("Recharge", sp.recharge_sec + "s"), kv("Charges", sp.charges), kv("Kind", String(sp.kind || "").replace(/-/g, " "))]),
      ];
    }
    function passiveTab() {
      var ps = H.passive;
      return [h("div", { class: "gd-tag", text: "“" + ps.name + "”" }), h("div", { class: "gd-bio", text: ps.desc })];
    }
    function skillTab() {
      var hp = handlerState(), own = (hp.unlocked && hp.unlocked[H.id]) || [];
      var n = [h("div", { class: "gd-sub", text: "Bones Skill Tree  -  🦴 " + (hp.bones | 0) + " available" })];
      var rows = H.skill_tree.map(function (node) {
        var owned = own.indexOf(node.id) >= 0 || node.bones === 0;
        var canBuy = handlerCanBuy(H.id, node);
        var locked = !owned && !canBuy && (hp.bones | 0) >= node.bones; // prereqs unmet
        var act;
        if (owned) act = h("span", { class: "aks-owned", text: "✓ OWNED" });
        else if (canBuy) act = h("button", { class: "gd-tbtn buy", text: "🦴 " + node.bones, onclick: function () {
          if (handlerCanBuy(H.id, node)) { writeHandlers(function (hh) { hh.bones -= node.bones; if (!hh.unlocked[H.id]) hh.unlocked[H.id] = []; hh.unlocked[H.id].push(node.id); }); toast(node.name + " unlocked", "good"); refresh(); }
          else toast("Not enough Bones", "bad");
        } });
        else act = h("span", { class: "aks-lock", text: locked ? "needs prereq" : ("🦴 " + node.bones) });
        return h("div", { class: "gd-trow" + (owned ? " on" : "") }, [
          h("span", { class: "gd-tlab" }, [h("b", { text: node.name }), h("span", { class: "gd-tnote", text: node.effect || "" })]),
          h("span", { class: "gd-tact" }, [act]),
        ]);
      });
      n.push(h("div", { class: "gd-tree" }, rows));
      n.push(h("div", { class: "gd-note", text: "Bones are earned every match (more for deeper runs). Each node's effect is absolute, so unlock order never matters." }));
      return n;
    }
    function refresh() {
      Array.prototype.forEach.call(tabbar.children, function (el) { el.classList.toggle("on", el.getAttribute("data-t") === tab); });
      clear(bodyEl);
      var nodes = tab === "info" ? infoTab() : tab === "special" ? specialTab() : tab === "passive" ? passiveTab() : skillTab();
      nodes.forEach(function (n) { if (n) bodyEl.appendChild(n); });
    }
    ov.appendChild(h("div", { class: "gd-card r-Legendary", style: "--acc:" + (H.accent || "#D4AF37") }, [
      h("div", { class: "gd-hbanner" }, [handlerArtFull(H)]),
      h("div", { class: "gd-name", text: H.name }),
      h("div", { class: "gd-meta", text: [H.breed, H.special.name].filter(Boolean).join(" // ") }),
      tabbar, bodyEl,
      h("button", { class: "aks-btn ghost", style: "margin-top:10px", text: "Close", onclick: closeOv }),
    ]));
    ov.onclick = function (ev) { if (ev.target === ov) closeOv(); };
    document.body.appendChild(ov);
    refresh();
    requestAnimationFrame(function () { ov.classList.add("show"); });
  }

// ====================================================================
// AK-DECK 2026-06-15: the Deck Lab, merged into the Chop Shop as a top-level
// tab (operator: kill the standalone deck builder; its full function lives
// here in the gold-glass style). Reads ak_profile.decks/.active via
// localProfile(); writes via econ().mutateProfile AND re-mirrors the flat
// ak_decks/ak_active store -- the SAME pair index.html's saveProfile() keeps
// in lockstep, which is what activeDeckNames()/startMatch() field. So a deck
// edited here is the deck fielded next match. Slot picker + 11-card deck reuse
// the handler-grid + cardFrame styling; a card tap reuses garageDetail() for
// the full inspect / swap / upgrade / skill sheet.
// ====================================================================
var DECK_SLOT_UNLOCK = [1, 3, 6, 9, 12, 15, 18, 21]; // mirrors index.html SLOT_UNLOCK (player level per slot)
function deckByName() { var m = {}; allCards().forEach(function (c) { m[c.name] = c; }); return m; }
function deckCardCost(c) { var s = canonStat(c); return (s && typeof s.cost === "number") ? s.cost : 0; }
function deckArchBand(avg) { return avg <= 3.8 ? "CYCLE" : (avg <= 5.2 ? "MIDRANGE" : "HEAVY"); }
// Mutate canon (ak_profile.decks/.active) THEN re-mirror the flat store the
// game reads -- identical contract to index.html saveProfile(). Returns ok.
function deckMutate(fn) {
  var e = econ();
  if (!e || !e.mutateProfile) { toast("Economy still loading -- try again.", "bad"); return false; }
  e.mutateProfile(function (p) {
    if (!Array.isArray(p.decks)) p.decks = [null, null, null, null, null, null, null, null];
    if (typeof p.active !== "number") p.active = 0;
    fn(p);
  });
  try {
    var p2 = localProfile() || {};
    if (Array.isArray(p2.decks)) localStorage.setItem("ak_decks", JSON.stringify(p2.decks.map(function (x) { return x ? { name: x.name, cards: x.cards } : null; })));
    if (typeof p2.active === "number") localStorage.setItem("ak_active", String(p2.active));
  } catch (_) {}
  return true;
}
  function deckView() {
    var p = localProfile() || {};
    var decks = Array.isArray(p.decks) ? p.decks : null;
    var nodes = secHead("Deck Lab", "Build your 11-card pack -- same cards, same inspect as the Card Shop. Tap a dog to read / upgrade / tune it; Add or Remove to shape the deck you field next match.");
    if (!decks) { var g0 = deckGet(); if (!g0.cards) { nodes.push(emptyCard("No deck yet -- buy cards in the Card Shop, then build here.")); return nodes; } decks = [{ name: "Active Deck", cards: g0.cards }]; p.active = 0; }
    var active = (typeof p.active === "number" && decks[p.active]) ? p.active : 0;
    var level = (p.level | 0) || 1, byName = deckByName();
    nodes.push(h("div", { class: "aks-deckslots" }, decks.map(function (d, i) {
      var unlocked = level >= (DECK_SLOT_UNLOCK[i] || 1);
      return h("button", { class: "aks-slotpill" + (i === active ? " on" : "") + (unlocked ? "" : " locked"),
        text: d ? (d.name || ("Deck " + (i + 1))) : (unlocked ? ("Deck " + (i + 1)) : ("Lv" + (DECK_SLOT_UNLOCK[i] || 1))),
        onclick: function () { if (!unlocked) { toast("Unlocks at level " + (DECK_SLOT_UNLOCK[i] || 1), "bad"); return; }
          deckMutate(function (pr) { if (!pr.decks[i]) pr.decks[i] = { name: "Deck " + (i + 1), cards: [], arch: null }; pr.active = i; }); render(); } });
    })));
    var deck = decks[active] || { name: "Deck " + (active + 1), cards: [] };
    var cards = Array.isArray(deck.cards) ? deck.cards : [];
    var sum = 0, cnt = 0; cards.forEach(function (nm) { var c = byName[nm]; if (c) { sum += deckCardCost(c); cnt++; } });
    nodes = nodes.concat(secHead("Active Deck -- " + cards.length + "/11", cnt ? ("Avg cost " + (Math.round(sum / cnt * 10) / 10) + " - " + deckArchBand(sum / cnt)) : "Add dogs from your crew below."));
    if (cards.length) nodes.push(grid(cards.map(function (nm) { var c = byName[nm] || { name: nm, rarity: "Common" };
      return cardFrame(c, { priceNode: h("span", { class: "aks-cost", text: "Cost " + deckCardCost(c) }),
        btnNode: h("div", { class: "aks-btnrow" }, [
          h("button", { class: "aks-btn ghost", text: "Inspect", onclick: function () { garageDetail(c); } }),
          h("button", { class: "aks-btn", text: "Remove", onclick: function () { deckMutate(function (pr) { var dk = pr.decks[active]; if (dk && Array.isArray(dk.cards)) { var ix = dk.cards.indexOf(nm); if (ix >= 0) dk.cards.splice(ix, 1); } }); render(); } }) ]) });
    })));
    else nodes.push(emptyCard("Empty deck -- add dogs from your crew below."));
    var owned = Array.isArray(p.owned) ? p.owned : [];
    var ro = {}; RARITY_ORDER.forEach(function (r, i) { ro[r] = i; });
    var pool = owned.filter(function (nm) { return cards.indexOf(nm) < 0 && byName[nm]; });
    pool.sort(function (a2, b2) { return (ro[byName[b2].rarity] || 0) - (ro[byName[a2].rarity] || 0) || String(a2).localeCompare(String(b2)); });
    nodes = nodes.concat(secHead("Your Crew", "Tap Add to slot a dog in. Inspect opens the full card."));
    if (pool.length) nodes.push(grid(pool.map(function (nm) { var c = byName[nm]; var full = cards.length >= 11;
      return cardFrame(c, { priceNode: h("span", { class: "aks-cost", text: "Cost " + deckCardCost(c) }),
        btnNode: h("div", { class: "aks-btnrow" }, [
          h("button", { class: "aks-btn ghost", text: "Inspect", onclick: function () { garageDetail(c); } }),
          h("button", { class: "aks-btn", text: full ? "Full" : "Add", disabled: full ? "true" : null, onclick: function () { deckMutate(function (pr) { var dk = pr.decks[active]; if (!dk) dk = pr.decks[active] = { name: "Deck " + (active + 1), cards: [], arch: null }; if (!Array.isArray(dk.cards)) dk.cards = []; if (dk.cards.length < 11 && dk.cards.indexOf(nm) < 0) dk.cards.push(nm); }); render(); } }) ]) });
    })));
    else nodes.push(emptyCard(owned.length ? "All your dogs are in this deck." : "No dogs yet -- buy in the Card Shop."));
    return nodes;
  }

  // AK-CODEX2: read-only card encyclopedia tab -- every dog, tap Read for the full card menu.
  function codexView() {
    var cards = (typeof allCards === "function") ? allCards() : (global.AK_CARDS || []);
    var nodes = secHead("Codex", "Every dog in the game. Tap Read for the full card -- lore, stats, crew synergy, keywords, skill tree.");
    if (!cards || !cards.length) { nodes.push(emptyCard("Card catalog still loading...")); return nodes; }
    var ro = {}; RARITY_ORDER.forEach(function (r, i) { ro[r] = i; });
    var list = cards.slice().sort(function (a, b) { return (ro[b.rarity] || 0) - (ro[a.rarity] || 0) || String(a.name || "").localeCompare(String(b.name || "")); });
    nodes.push(grid(list.map(function (c) {
      return cardFrame(c, { btnNode: h("button", { class: "aks-btn ghost", text: "Read", onclick: function () { garageDetail(c); } }) });
    })));
    return nodes;
  }
  // AK-STREET: the Street Code perk tree, ported into the Chop Shop. Writes
  // ak_profile.spec/.coins via econ().mutateProfile; the game's computePerks()
  // reads p.spec each match. Pick ONE path per branch at level SPEC_UNLOCK.
  var SPEC_UNLOCK = 10, SPEC_RESPEC_COST = 2000;
  var SPEC_PATHS = {
    muscle: [ { id: "enforcer", name: "The Enforcer", blurb: "Raw damage -- dogs hit like trucks." }, { id: "bulwark", name: "The Bulwark", blurb: "Den defense -- the block never falls." }, { id: "warlord", name: "The Warlord", blurb: "Tempo + energy -- flood the street." } ],
    hustle: [ { id: "kingpin", name: "The Kingpin", blurb: "Coins on coins -- run the whole block." }, { id: "fence", name: "The Fence", blurb: "Scrap empire -- nothing gets wasted." }, { id: "gambler", name: "The Gambler", blurb: "Loaded dice -- the chest always pays." } ],
    tech: [ { id: "hacker", name: "The Hacker", blurb: "Spells on a hair trigger." }, { id: "engineer", name: "The Engineer", blurb: "Energy reactor -- never runs dry." }, { id: "saboteur", name: "The Saboteur", blurb: "Cheap resumes + dirty utility." } ]
  };
  function specPathName(branch, id) { var a = SPEC_PATHS[branch] || []; for (var i = 0; i < a.length; i++) if (a[i].id === id) return a[i].name; return id || ""; }
  function pickSpec(branch, id) {
    var p = localProfile() || {}; var lvl = (p.level | 0) || 1;
    if (lvl < SPEC_UNLOCK) { toast("Street Code unlocks at level " + SPEC_UNLOCK + ".", "bad"); return; }
    var cur = (p.spec && p.spec[branch]) || null; if (cur === id) return;
    var e = econ(); if (!e || !e.mutateProfile) { toast("Economy still loading -- try again.", "bad"); return; }
    if (cur) { if ((p.coins | 0) < SPEC_RESPEC_COST) { toast("Switching a locked path costs " + SPEC_RESPEC_COST + " coins.", "bad"); return; }
      e.mutateProfile(function (pr) { if (!pr.spec || typeof pr.spec !== "object") pr.spec = {}; pr.spec[branch] = id; pr.coins = (pr.coins | 0) - SPEC_RESPEC_COST; });
      toast(specPathName(branch, id) + " locked (respec -" + SPEC_RESPEC_COST + "c).", "good");
    } else { e.mutateProfile(function (pr) { if (!pr.spec || typeof pr.spec !== "object") pr.spec = {}; pr.spec[branch] = id; });
      toast(specPathName(branch, id) + " locked in.", "good"); }
    render();
  }
  function streetCodeView() {
    var p = localProfile() || {}; var lvl = (p.level | 0) || 1; var spec = (p.spec && typeof p.spec === "object") ? p.spec : {};
    var nodes = secHead("Street Code", "Your crew's specialization -- it powers every match. At level " + SPEC_UNLOCK + ", lock ONE path per branch. Switching a locked path costs " + SPEC_RESPEC_COST + " coins.");
    if (lvl < SPEC_UNLOCK) nodes.push(h("div", { class: "aks-sec-sub", text: "Reach level " + SPEC_UNLOCK + " to unlock Street Code -- you're level " + lvl + "." }));
    ["muscle", "hustle", "tech"].forEach(function (branch) {
      nodes = nodes.concat(secHead(branch.charAt(0).toUpperCase() + branch.slice(1), spec[branch] ? ("Locked: " + specPathName(branch, spec[branch])) : "Choose one path."));
      nodes.push(h("div", { class: "aks-grid" }, (SPEC_PATHS[branch] || []).map(function (node) {
        var chosen = spec[branch] === node.id;
        return h("div", { class: "aks-card " + (chosen ? "r-Legendary aks-up" : "r-Rare") }, [
          h("div", { class: "aks-meta" }, [
            h("div", { class: "aks-name", text: node.name }),
            h("div", { class: "aks-desc", text: node.blurb }),
            h("div", { class: "aks-row" }, [ h("span"),
              chosen ? h("span", { class: "aks-owned", text: "✓ LOCKED" })
                : h("button", { class: "aks-btn", text: spec[branch] ? ("Switch -" + SPEC_RESPEC_COST + "c") : "Lock In", disabled: lvl < SPEC_UNLOCK ? "true" : null, onclick: function () { pickSpec(branch, node.id); } }) ])
          ])
        ]);
      })));
    });
    return nodes;
  }

// ============================================================================
// PASTE INTO shop/shop.js, inside the IIFE (e.g. right before `function upgradeView()`).
// AK-DRIP 2026-06-15: "The Drop" cosmetic shop + Locker, ported from the
// standalone drip.js overlay into the Chop Shop as a gd-native tab. Same server
// contract (ak-cosmetics edge fn via AKAccount.client()), same localStorage
// equip keys the engine's AKDrip.cardFilter/boardFilter/equippedEmotes read
// in-match -- so an equip made here rides the very next match. Gold = the local
// ak_profile.coins pocket (cosmetic spend; server only records ownership).
// drip.js's CATALOG is private, so it is replicated verbatim here.
// ============================================================================
var DRIP_CATALOG = {
  style_gilded:  { type: "style", name: "Gilded",    rarity: "Epic",   price: 800, sw: "linear-gradient(135deg,#f7e08a,#cf9b22)" },
  style_neon:    { type: "style", name: "Neon Noir", rarity: "Rare",   price: 600, sw: "linear-gradient(135deg,#5ee7ff,#8a5cff)" },
  style_toxic:   { type: "style", name: "Toxic",     rarity: "Rare",   price: 600, sw: "linear-gradient(135deg,#aaff66,#33aa33)" },
  style_shadow:  { type: "style", name: "Shadow",    rarity: "Rare",   price: 500, sw: "linear-gradient(135deg,#6b6b78,#15151c)" },
  style_frost:   { type: "style", name: "Frostbite", rarity: "Epic",   price: 700, sw: "linear-gradient(135deg,#bfefff,#4aa3df)" },
  style_inferno: { type: "style", name: "Inferno",   rarity: "Mythic", price: 900, sw: "linear-gradient(135deg,#ffb24a,#d4341a)" },
  board_noir:      { type: "board", name: "Noir Alley", rarity: "Rare", price: 400, sw: "linear-gradient(135deg,#cfcfd6,#2b2b30)" },
  board_vapor:     { type: "board", name: "Vaporwave",  rarity: "Epic", price: 500, sw: "linear-gradient(135deg,#ff8ad8,#7a5cff)" },
  board_bloodmoon: { type: "board", name: "Blood Moon", rarity: "Epic", price: 600, sw: "linear-gradient(135deg,#ff6a5e,#5a1414)" },
  emote_woof:  { type: "emote", name: "Woof",      rarity: "Common", price: 200, emoji: "🐕", text: "WOOF!" },
  emote_crown: { type: "emote", name: "All Hail",  rarity: "Rare",   price: 300, emoji: "👑", text: "ALL HAIL" },
  emote_gg:    { type: "emote", name: "Good Game", rarity: "Common", price: 200, emoji: "🤝", text: "GG" },
  emote_skull: { type: "emote", name: "Get Got",   rarity: "Rare",   price: 250, emoji: "💀", text: "GET GOT" },
};
var dripCache = { loaded: false, tried: false, rotation: [], prices: {}, resets: 0 };
var dripOwned = {};                                       // id -> 1 (server-synced, mirrored to ak_cos_owned)
var dripEquip = { styleAll: null, board: null, skins: {}, emotes: [] };
var dripSub = "shop";                                     // "shop" | "locker"
var dripLoading = false;

function dripMe() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
function dripLs(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }
function dripLsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }
function dripLsDel(k) { try { localStorage.removeItem(k); } catch (_) {} }
// mirror drip.js's call(): AKAccount.client().functions.invoke, JSON-decoding edge errors.
function dripCall(fn, body) {
  var sb = (global.AKAccount && global.AKAccount.client && global.AKAccount.client());
  if (!sb) return Promise.resolve({ ok: false, error: "offline" });
  return sb.functions.invoke(fn, { body: body }).then(function (r) {
    if (r.error) { var c = r.error.context; if (c && typeof c.json === "function") return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; }); return { ok: false, error: r.error.message || "error" }; }
    return r.data || { ok: false, error: "empty" };
  }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
}
function dripLoadEquip() {
  dripEquip.styleAll = dripLs("ak_style_all");
  dripEquip.board = dripLs("ak_board");
  try { dripOwned = JSON.parse(dripLs("ak_cos_owned") || "{}") || {}; } catch (_) { dripOwned = {}; }
  try { dripEquip.skins = JSON.parse(dripLs("ak_skins") || "{}") || {}; } catch (_) { dripEquip.skins = {}; }
  try { dripEquip.emotes = JSON.parse(dripLs("ak_emotes") || "[]") || []; } catch (_) { dripEquip.emotes = []; }
}
function dripGold() { var p = localProfile(); return (p && (p.coins | 0)) || 0; }
function dripMyCards() { var p = localProfile(); return ((p && p.owned) || []).slice().sort(); }
function dripOwnedOfType(t) { return Object.keys(dripOwned).filter(function (id) { return DRIP_CATALOG[id] && DRIP_CATALOG[id].type === t; }); }
function dripFmtCountdown(s) { var hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60); return "The Drop resets in " + hh + "h " + mm + "m"; }

function dripArt(c) {
  if (c.type === "emote") return h("div", { class: "aks-art", style: "min-height:96px;display:flex;align-items:center;justify-content:center;font-size:44px;background:rgba(0,0,0,0.35)" }, [c.emoji]);
  return h("div", { class: "aks-art", style: "min-height:96px;background:" + c.sw });
}
function dripTile(id, btn) {
  var c = DRIP_CATALOG[id]; if (!c) return null;
  return h("div", { class: "aks-card " + rarClass(c.rarity) }, [
    dripArt(c),
    h("div", { class: "aks-meta" }, [
      h("div", { class: "aks-name", text: c.name }),
      h("div", { class: "aks-sub", text: c.type.toUpperCase() + " // " + c.rarity }),
      h("div", { class: "aks-row" }, [h("span"), btn]),
    ]),
  ]);
}
function dripBuy(id, btn) {
  var c = DRIP_CATALOG[id]; if (!c) return;
  var price = (dripCache.prices && dripCache.prices[id]) || c.price || 0;
  if (dripGold() < price) { toast("Not enough gold (need " + fmt(price) + ")", "bad"); return; }
  if (btn) btn.disabled = true;
  dripCall("ak-cosmetics", { action: "buy", id: id }).then(function (r) {
    if (!r || !r.ok) { toast((r && r.error) ? r.error : "Could not buy", "bad"); if (btn) btn.disabled = false; return; }
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins || 0) - price); }); } catch (_) {}
    try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
    dripOwned[id] = 1; dripLsSet("ak_cos_owned", JSON.stringify(dripOwned));
    toast("Unlocked " + c.name + "!", "good");
    render();                                              // refresh wallet + re-render the Drip tab
  });
}
function dripEquipAll(id) { dripEquip.styleAll = id || null; if (id) dripLsSet("ak_style_all", id); else dripLsDel("ak_style_all"); toast(id ? "Squad skin equipped -- rides your next match" : "Squad skin removed", "good"); render(); }
function dripEquipBoard(id) { dripEquip.board = id || null; if (id) dripLsSet("ak_board", id); else dripLsDel("ak_board"); toast(id ? "Board equipped" : "Board removed", "good"); render(); }
function dripToggleEmote(id) {
  var i = dripEquip.emotes.indexOf(id);
  if (i >= 0) dripEquip.emotes.splice(i, 1);
  else { if (dripEquip.emotes.length >= 4) { toast("Emote slots full (4)", "bad"); return; } dripEquip.emotes.push(id); }
  dripLsSet("ak_emotes", JSON.stringify(dripEquip.emotes)); render();
}
function dripAssignSkin(cardName, styleId) {
  if (!cardName || !styleId || !DRIP_CATALOG[styleId]) return;
  dripEquip.skins[cardName] = styleId; dripLsSet("ak_skins", JSON.stringify(dripEquip.skins));
  toast(DRIP_CATALOG[styleId].name + " on " + cardName, "good"); render();
}
function dripClearSkin(cardName) { delete dripEquip.skins[cardName]; dripLsSet("ak_skins", JSON.stringify(dripEquip.skins)); render(); }

// ---- The Drop (rotating cosmetic store) ----
function dripShopSection() {
  var sub = dripCache.resets ? dripFmtCountdown(dripCache.resets) : "Rotating cosmetics -- card skins, arena boards + battle emotes. In-game value only, never pay-to-win.";
  var nodes = secHead("The Drop", sub);
  var rot = dripCache.rotation || [];
  if (!rot.length) { nodes.push(emptyCard("The Drop is restocking -- check back soon.")); return nodes; }
  var tiles = rot.map(function (id) {
    var c = DRIP_CATALOG[id]; if (!c) return null;
    var price = (dripCache.prices && dripCache.prices[id]) || c.price;
    var btn = dripOwned[id]
      ? h("button", { class: "aks-btn ghost", disabled: "true", text: "Owned" })
      : h("button", { class: "aks-btn", text: "💰 " + fmt(price), onclick: function () { dripBuy(id, this); } });
    return dripTile(id, btn);
  }).filter(Boolean);
  nodes.push(grid(tiles));
  return nodes;
}

// ---- Locker (equip skins / boards / emotes) ----
var DRIP_SEL_STYLE = "background:rgba(0,0,0,0.35);border:1px solid rgba(201,168,76,0.3);color:#e9e9ee;border-radius:8px;padding:9px;font-size:13px;flex:1;min-width:120px";
function dripLockerSection() {
  var nodes = secHead("Locker", "Equip your drip -- it shows on the battlefield and rides your very next match.");
  // SKINS
  nodes = nodes.concat(secHead("Card Skins", "Wear one across your whole squad, or assign it per-card below."));
  var skins = dripOwnedOfType("style");
  if (!skins.length) nodes.push(emptyCard("No skins yet -- grab one from The Drop."));
  else {
    nodes.push(grid(skins.map(function (id) {
      var active = dripEquip.styleAll === id;
      var btn = h("button", { class: "aks-btn" + (active ? "" : " ghost"), text: active ? "✓ Squad" : "Wear (squad)", onclick: function () { dripEquipAll(active ? null : id); } });
      return dripTile(id, btn);
    })));
    var cards = dripMyCards();
    if (cards.length) {
      nodes = nodes.concat(secHead("Per-Card", "Overrides the squad skin for one dog."));
      var cardSel = h("select", { style: DRIP_SEL_STYLE }, cards.map(function (n) { return h("option", { value: n, text: n }); }));
      var styleSel = h("select", { style: DRIP_SEL_STYLE }, skins.map(function (id) { return h("option", { value: id, text: DRIP_CATALOG[id].name }); }));
      var go = h("button", { class: "aks-btn", text: "Equip to this card", onclick: function () { dripAssignSkin(cardSel.value, styleSel.value); } });
      nodes.push(h("div", { class: "aks-row", style: "flex-wrap:wrap;gap:8px" }, [cardSel, styleSel, go]));
      var assigned = Object.keys(dripEquip.skins).filter(function (cn) { return dripEquip.skins[cn] && DRIP_CATALOG[dripEquip.skins[cn]] && dripOwned[dripEquip.skins[cn]]; });
      assigned.forEach(function (cn) {
        nodes.push(h("div", { class: "aks-row", style: "border-bottom:1px solid rgba(255,255,255,0.06);padding:6px 2px" }, [
          h("span", { style: "flex:1", text: cn + " → " + DRIP_CATALOG[dripEquip.skins[cn]].name }),
          h("button", { class: "aks-btn ghost", style: "padding:4px 10px", text: "clear", onclick: function () { dripClearSkin(cn); } }),
        ]));
      });
    }
  }
  // BOARDS
  nodes = nodes.concat(secHead("Arena Boards", "A board theme re-skins the match backdrop."));
  var boards = dripOwnedOfType("board");
  if (!boards.length) nodes.push(emptyCard("No boards yet -- grab one from The Drop."));
  else nodes.push(grid(boards.map(function (id) {
    var active = dripEquip.board === id;
    var btn = h("button", { class: "aks-btn" + (active ? "" : " ghost"), text: active ? "✓ Active" : "Use", onclick: function () { dripEquipBoard(active ? null : id); } });
    return dripTile(id, btn);
  })));
  // EMOTES
  nodes = nodes.concat(secHead("Battle Emotes", "Tap to equip up to 4 -- pop them in-match from the emote button."));
  var emotes = dripOwnedOfType("emote");
  if (!emotes.length) nodes.push(emptyCard("No emotes yet -- grab one from The Drop."));
  else nodes.push(grid(emotes.map(function (id) {
    var on = dripEquip.emotes.indexOf(id) >= 0;
    var btn = h("button", { class: "aks-btn" + (on ? "" : " ghost"), text: on ? "✓ Equipped" : "Equip", onclick: function () { dripToggleEmote(id); } });
    return dripTile(id, btn);
  })));
  return nodes;
}

function dripSubTabs() {
  return h("div", { class: "aks-deckslots" }, [
    h("button", { class: "aks-slotpill" + (dripSub === "shop" ? " on" : ""), text: "The Drop", onclick: function () { dripSub = "shop"; render(); } }),
    h("button", { class: "aks-slotpill" + (dripSub === "locker" ? " on" : ""), text: "Locker", onclick: function () { dripSub = "locker"; render(); } }),
  ]);
}

function dripView() {
  dripLoadEquip();                                          // cheap sync read so toggles always reflect localStorage
  if (!dripMe()) {                                          // signed out -> degrade like the other tabs
    var out = secHead("The Drop", "Cosmetic shop -- card skins, arena boards + battle emotes. In-game value only.");
    out.push(emptyCard("Sign in to shop The Drop and equip skins, boards and emotes."));
    out.push(h("div", { class: "aks-row", style: "justify-content:center;margin-top:8px" }, [
      h("button", { class: "aks-btn", text: "Sign in with Google", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } }),
    ]));
    return out;
  }
  // async load: fire ak-cosmetics get ONCE, render "loading", re-render on resolve (tried-flag = no refire loop on failure)
  if (!dripCache.loaded && !dripCache.tried && !dripLoading) {
    dripLoading = true;
    dripCall("ak-cosmetics", { action: "get" }).then(function (r) {
      dripLoading = false; dripCache.tried = true;
      if (r && r.ok) {
        dripCache.loaded = true;
        dripOwned = {}; (r.owned || []).forEach(function (id) { dripOwned[id] = 1; });
        dripLsSet("ak_cos_owned", JSON.stringify(dripOwned));
        dripCache.rotation = r.rotation || []; dripCache.prices = r.prices || {}; dripCache.resets = r.resets_in || 0;
      } else { toast((r && r.error) ? r.error : "Could not load The Drop", "bad"); }
      try { render(); } catch (_) {}
    });
  }
  var nodes = [dripSubTabs()];
  if (dripSub === "locker") return nodes.concat(dripLockerSection());   // Locker works from cached ak_cos_owned, no server needed
  if (!dripCache.loaded) {
    if (dripCache.tried) {
      nodes = nodes.concat(secHead("The Drop", "Could not reach The Drop."));
      nodes.push(emptyCard("The Drop is offline right now."));
      nodes.push(h("div", { class: "aks-row", style: "justify-content:center" }, [
        h("button", { class: "aks-btn", text: "Retry", onclick: function () { dripCache.tried = false; render(); } }),
      ]));
    } else {
      nodes = nodes.concat(secHead("The Drop", "Loading the Drop..."));
      nodes.push(emptyCard("Loading cosmetics..."));
    }
    return nodes;
  }
  return nodes.concat(dripShopSection());
}
/* ====================================================================
   AK-CREW 2026-06-15: Crew HQ (clans) + World/Crew chat + donations,
   ported from the standalone social.js overlay into the Chop Shop as a
   gd-native tab. Same server contract: ak-crew + ak-chat edge fns via the
   shared Supabase client (AKAccount.client().functions.invoke -- auto-attaches
   the signed-in JWT). Realtime chat uses sb.channel() exactly like the overlay;
   shop.html loads ak_account.js, which boots the SAME supabase-js client, so
   postgres_changes + presence work here too. Signed out, the tab degrades to a
   Google sign-in card like every other shop tab. social.js's own injected CSS
   (.aks-li/.aks-dot/.aks-crest/.aks-msg/.aks-inp) is NOT in shop.css, so roster
   rows / dots / chat bubbles / inputs are rebuilt with shop classes + inline
   gold-glass styles. Paste this whole block inside the IIFE, next to
   handlersView()/deckView() (e.g. right before function upgradeView()).
   ==================================================================== */
  var CREW_FACTIONS = [
    { id: "boneguard_crew", name: "Boneguard Crew" },
    { id: "zoomie_syndicate", name: "Zoomie Syndicate" },
    { id: "leashbreak_tactix", name: "Leashbreak Tactix" },
    { id: "k9_circuitry", name: "K9 Circuitry" },
  ];
  var CREW_FNAME = {}; CREW_FACTIONS.forEach(function (f) { CREW_FNAME[f.id] = f.name; });
  var crewS = {
    tab: "crew", scope: "world",
    crew: null, role: null, members: [],
    msgs: { world: [], crew: [] }, chans: {}, presence: { world: 0, crew: 0 },
    loaded: false, subscribed: false,
    donations: null, donLoaded: false, showDonForm: false,
    showCreate: false, listBox: null, mlist: null, worldLabel: null, crewLabel: null,
  };
  // shared Supabase client + identity (mirror social.js sbc()/me())
  function crewSb() { try { return (global.AKAccount && global.AKAccount.client && global.AKAccount.client()) || null; } catch (_) { return null; } }
  function crewMe() { try { return (global.AKAccount && global.AKAccount.user && global.AKAccount.user()) || null; } catch (_) { return null; } }
  function crewMyId() { var u = crewMe(); return (u && u.id) || null; }
  function crewMyName() { try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24); } catch (_) { return "Stray"; } }
  function crewMyOwned() { try { var p = localProfile(); return (p && p.owned) || []; } catch (_) { return []; } }
  function crewInpStyle() { return "width:100%;box-sizing:border-box;background:rgba(0,0,0,0.35);border:1px solid rgba(201,168,76,0.25);color:#fff;border-radius:9px;padding:10px;margin:5px 0;font-size:14px;outline:none"; }
  function crewReRender() { if (activeTab === "crew2") render(); }

  // server call -- exact mirror of social.js call() (JSON-context error unwrap)
  function crewCall(fn, body) {
    var sb = crewSb();
    if (!sb || !sb.functions) return Promise.resolve({ ok: false, error: "offline" });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var ctx = r.error && r.error.context;
        if (ctx && typeof ctx.json === "function") return ctx.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: (r.error && r.error.message) || "error" };
      }
      return r.data || { ok: false, error: "empty" };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }

  // ---- async loaders (populate cache, then re-render the crew tab) ----------
  function crewRefresh() {
    if (!crewMe()) { crewS.loaded = true; crewReRender(); return; }
    crewCall("ak-crew", { action: "mine" }).then(function (r) {
      if (r && r.ok) { crewS.crew = r.crew || null; crewS.role = r.role || null; crewS.members = r.members || []; }
      crewS.loaded = true; crewReRender();
      if (crewS.crew) crewSubscribeCrew();
    });
  }
  function crewLoadDonations() {
    crewS.donLoaded = true;
    crewCall("ak-crew", { action: "don-list" }).then(function (r) { crewS.donations = (r && r.requests) || []; crewReRender(); });
  }
  function crewLoadHistory(scope) {
    crewCall("ak-chat", { action: "history", scope: scope }).then(function (r) {
      if (r && r.ok) { crewS.msgs[scope] = r.messages || []; if (activeTab === "crew2" && crewS.tab === "chat" && crewS.scope === scope) crewPaintMsgs(); }
    });
  }

  // ---- Realtime (same channels/filters/presence as social.js) ---------------
  function crewPushMsg(scope, m) {
    var arr = crewS.msgs[scope] || (crewS.msgs[scope] = []);
    if (!m || arr.some(function (x) { return x.id === m.id; })) return;
    arr.push(m); if (arr.length > 120) arr.shift();
    if (activeTab === "crew2" && crewS.tab === "chat" && crewS.scope === scope) crewPaintMsgs();
  }
  function crewCountPresence(ch) { try { var st = ch.presenceState(); var ids = {}; Object.keys(st).forEach(function (k) { (st[k] || []).forEach(function (p) { if (p.uid) ids[p.uid] = 1; }); }); return Object.keys(ids).length; } catch (_) { return 0; } }
  function crewSyncHeadcount() {
    if (activeTab !== "crew2" || crewS.tab !== "chat") return;
    if (crewS.worldLabel && crewS.worldLabel.isConnected) crewS.worldLabel.textContent = "WORLD · " + crewS.presence.world + " on";
    if (crewS.crewLabel && crewS.crewLabel.isConnected && crewS.crew) crewS.crewLabel.textContent = "CREW · " + crewS.presence.crew + " on";
  }
  function crewSubscribeWorld() {
    var sb = crewSb(); if (!sb || !sb.channel || crewS.chans.world) return;
    var ch = sb.channel("ak-world-chat");
    ch.on("postgres_changes", { event: "INSERT", schema: "public", table: "ak_chat_messages", filter: "scope=eq.world" }, function (p) { crewPushMsg("world", p.new); });
    ch.on("presence", { event: "sync" }, function () { try { crewS.presence.world = crewCountPresence(ch); crewSyncHeadcount(); } catch (_) {} });
    ch.subscribe(function (st) { if (st === "SUBSCRIBED") { try { ch.track({ uid: crewMyId() || "anon", name: crewMyName() }); } catch (_) {} } });
    crewS.chans.world = ch;
  }
  function crewSubscribeCrew() {
    var sb = crewSb(); if (!sb || !sb.channel || !crewS.crew) return;
    crewUnsub("crew");
    var cid = crewS.crew.id;
    var ch = sb.channel("ak-crew-chat-" + cid);
    ch.on("postgres_changes", { event: "INSERT", schema: "public", table: "ak_chat_messages", filter: "crew_id=eq." + cid }, function (p) { if (p.new && p.new.scope === "crew") crewPushMsg("crew", p.new); });
    ch.on("presence", { event: "sync" }, function () {
      try {
        var st = ch.presenceState(); var ids = {};
        Object.keys(st).forEach(function (k) { (st[k] || []).forEach(function (pp) { if (pp.uid) ids[pp.uid] = 1; }); });
        crewS.presence.crew = Object.keys(ids).length;
        crewS.members.forEach(function (m) { m._on = !!ids[m.user_id]; });
        if (activeTab === "crew2") { if (crewS.tab === "chat") crewSyncHeadcount(); else crewReRender(); }
      } catch (_) {}
    });
    ch.subscribe(function (s) { if (s === "SUBSCRIBED") { try { ch.track({ uid: crewMyId() || "anon", name: crewMyName() }); } catch (_) {} } });
    crewS.chans.crew = ch;
  }
  function crewUnsub(which) { var sb = crewSb(); if (sb && crewS.chans[which]) { try { sb.removeChannel(crewS.chans[which]); } catch (_) {} crewS.chans[which] = null; } }

  // ---- chat send ------------------------------------------------------------
  function crewSendChat(inputEl) {
    if (!crewMe()) { toast("Sign in to chat.", "bad"); return; }
    var body = (inputEl.value || "").trim(); if (!body) return;
    inputEl.value = "";
    var faction = crewS.crew ? crewS.crew.faction : null;
    crewCall("ak-chat", { action: "send", scope: crewS.scope, body: body, name: crewMyName(), faction: faction }).then(function (r) {
      if (!r.ok) { toast(r.error || "Could not send.", "bad"); inputEl.value = body; }
      else if (r.message) { crewPushMsg(crewS.scope, r.message); try { if (global.AKQuests) global.AKQuests.reportEvent("chats", 1); } catch (_) {} }
    });
  }

  // ---- TOP-LEVEL VIEW -------------------------------------------------------
  function crewView() {
    // signed out -> sign-in card (matches every other shop tab's degrade)
    if (!crewMe()) {
      var out = secHead("Crew HQ", "Crews (clans), World + Crew chat, and card donations. Sign in with Google to start or join a crew.");
      out.push(h("div", { class: "aks-card" }, [
        h("div", { class: "aks-sub", text: "Sign in with Google to start or join a crew, chat with the world, and donate cards to your crewmates." }),
        h("div", { class: "aks-row", style: "margin-top:10px" }, [
          h("button", { class: "aks-btn", text: "SIGN IN WITH GOOGLE", onclick: function () { try { if (global.AKAccount && global.AKAccount.signIn) global.AKAccount.signIn(); else promptSignIn(); } catch (_) { promptSignIn(); } } }),
        ]),
      ]));
      return out;
    }
    if (!crewS.loaded) crewRefresh();
    if (!crewS.subscribed) { crewS.subscribed = true; crewSubscribeWorld(); try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_) {} }
    var nodes = secHead("Crew HQ", "Run with a crew -- clan roster, donations, and World + Crew chat. Your wins stack trophies for the whole crew.");
    nodes.push(h("div", { class: "gd-tabs" }, [
      h("div", { class: "gd-tab" + (crewS.tab === "crew" ? " on" : ""), text: "Crew HQ", onclick: function () { crewS.tab = "crew"; render(); } }),
      h("div", { class: "gd-tab" + (crewS.tab === "chat" ? " on" : ""), text: "Chat", onclick: function () { crewS.tab = "chat"; render(); } }),
    ]));
    if (crewS.tab === "chat") { crewChatNodes(nodes); return nodes; }
    if (!crewS.loaded) { nodes.push(emptyCard("Loading crew...")); return nodes; }
    if (crewS.crew) crewHomeNodes(nodes); else crewBrowseNodes(nodes);
    return nodes;
  }

  // ---- Crew HQ (home) -------------------------------------------------------
  function crewHomeNodes(nodes) {
    var c = crewS.crew;
    nodes.push(h("div", { class: "aks-card" }, [
      h("div", { class: "aks-row", style: "gap:10px" }, [
        h("div", { style: "width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;background:rgba(201,168,76,0.14);border:1px solid rgba(201,168,76,0.3)", text: "🐶" }),
        h("div", { style: "flex:1" }, [
          h("div", { class: "aks-name" }, [c.name + " ", h("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
          h("div", { class: "aks-sub", text: (CREW_FNAME[c.faction] || c.faction) + " · " + (c.member_count || crewS.members.length) + "/50 · " + (c.trophies || 0) + " trophies" }),
        ]),
      ]),
      c.description ? h("div", { class: "aks-sub", style: "margin-top:8px", text: c.description }) : null,
      h("div", { class: "aks-row", style: "gap:8px;margin-top:10px" }, [
        h("button", { class: "aks-btn", style: "flex:1", text: "💬 Crew Chat", onclick: function () { crewS.scope = "crew"; crewS.tab = "chat"; render(); } }),
        h("button", { class: "aks-btn ghost", text: "Leave", onclick: crewDoLeave }),
      ]),
    ]));
    crewDonationNodes(nodes);
    var rosterRows = crewS.members.map(function (m) {
      var nm = m.user_id === crewMyId() ? (crewMyName() + " (you)") : (m.name || ("Stray " + String(m.user_id).slice(0, 4)));
      return h("div", { class: "aks-row", style: "gap:10px;padding:8px 0;border-top:1px solid rgba(255,255,255,0.06)" }, [
        h("span", { style: "width:8px;height:8px;border-radius:50%;flex:0 0 auto;background:" + (m._on ? "#5fd35f" : "#3a3a44") + (m._on ? ";box-shadow:0 0 6px #5fd35f" : "") }),
        h("span", { class: "aks-name", style: "flex:1;font-size:13px", text: nm }),
        h("span", { class: "aks-sub", text: m.role || "member" }),
      ]);
    });
    nodes.push(h("div", { class: "aks-card" }, [h("div", { class: "aks-sub", style: "margin-bottom:6px", text: "CREW (" + crewS.members.length + " · " + crewS.presence.crew + " online)" })].concat(rosterRows)));
    nodes.push(h("div", { class: "aks-card" }, [
      h("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WARS" }),
      h("div", { class: "aks-sub", text: "Wars open with 2v2 (Phase 2). Stack trophies now -- your wins will tally for the crew." }),
    ]));
  }

  // ---- donations ------------------------------------------------------------
  function crewDonationNodes(nodes) {
    if (!crewS.donLoaded) crewLoadDonations();
    var kids = [h("div", { class: "aks-row", style: "margin-bottom:8px" }, [
      h("div", { class: "aks-sub", style: "flex:1", text: "DONATIONS -- carry your weight" }),
      h("button", { class: "aks-btn ghost", style: "padding:6px 10px", text: crewS.showDonForm ? "Close" : "Request", onclick: function () { crewS.showDonForm = !crewS.showDonForm; render(); } }),
    ])];
    if (crewS.showDonForm) kids.push(crewDonReqForm());
    if (!crewS.donLoaded || crewS.donations == null) kids.push(h("div", { class: "gd-note", text: "Loading..." }));
    else if (!crewS.donations.length) kids.push(h("div", { class: "gd-note", text: "No open requests. Tap Request to ask your crew for cards." }));
    else crewS.donations.forEach(function (rq) {
      var mine = rq.user_id === crewMyId();
      var btn = h("button", { class: "aks-btn" + (mine ? " ghost" : ""), style: "padding:6px 10px", text: mine ? "yours" : "Donate" });
      if (mine) btn.disabled = true;
      else btn.onclick = function () {
        btn.disabled = true;
        crewCall("ak-crew", { action: "don-fill", request_id: rq.id }).then(function (rr) {
          if (rr.ok) { toast("Donated " + rr.filled + "!", "good"); try { if (global.AKQuests) global.AKQuests.reportEvent("donates", rr.filled || 1); } catch (_) {} crewLoadDonations(); }
          else { toast(rr.error || "Could not donate.", "bad"); btn.disabled = false; }
        });
      };
      kids.push(h("div", { class: "aks-row", style: "gap:8px;padding:8px 0;border-top:1px solid rgba(255,255,255,0.06)" }, [
        h("div", { style: "flex:1" }, [
          h("div", { class: "aks-name", style: "font-size:13px", text: rq.requester_name || "Stray" }),
          h("div", { class: "aks-sub", text: "wants " + rq.qty_req + "x " + rq.card_id + "  (" + rq.qty_filled + "/" + rq.qty_req + ")" }),
        ]),
        btn,
      ]));
    });
    nodes.push(h("div", { class: "aks-card" }, kids));
  }
  function crewDonReqForm() {
    var owned = crewMyOwned();
    var picker = owned.length
      ? h("select", { style: crewInpStyle() }, owned.slice().sort().map(function (n) { return h("option", { value: n, text: n }); }))
      : h("input", { type: "text", placeholder: "Card name", style: crewInpStyle() });
    var qty = h("select", { style: crewInpStyle() }, [2, 4, 6, 8].map(function (q) { return h("option", { value: String(q), text: q + " copies" }); }));
    var go = h("button", { class: "aks-btn", text: "Post Request" });
    go.onclick = function () {
      var card = (picker.value || "").trim(); if (!card) { toast("Pick a card.", "bad"); return; }
      go.disabled = true;
      crewCall("ak-crew", { action: "don-request", card_id: card, qty_req: parseInt(qty.value, 10), name: crewMyName() }).then(function (r) {
        if (r.ok) { toast("Request posted.", "good"); crewS.showDonForm = false; crewLoadDonations(); }
        else { toast(r.error || "Could not post.", "bad"); go.disabled = false; }
      });
    };
    return h("div", { style: "margin-bottom:6px" }, [
      h("div", { class: "aks-sub", style: "margin-bottom:6px", text: "Crewmates donate copies -- free for them, a big help for you." }),
      picker, qty,
      h("div", { class: "aks-row", style: "gap:8px;margin-top:6px" }, [go]),
    ]);
  }
  function crewDoLeave() {
    if (!confirm("Leave " + (crewS.crew && crewS.crew.name) + "?")) return;
    crewCall("ak-crew", { action: "leave" }).then(function (r) {
      if (r.ok) { crewS.crew = null; crewS.members = []; crewUnsub("crew"); toast("Left the crew.", "ok"); crewS.loaded = false; crewRefresh(); }
      else toast(r.error || "Could not leave.", "bad");
    });
  }

  // ---- browse / create ------------------------------------------------------
  function crewBrowseNodes(nodes) {
    if (crewS.showCreate) { crewCreateNodes(nodes); return; }
    var search = h("input", { type: "text", placeholder: "Search crews", style: crewInpStyle() + ";margin:0" });
    var listBox = h("div", {}); crewS.listBox = listBox;
    var t; search.oninput = function () { clearTimeout(t); t = setTimeout(function () { crewLoadList(search.value, listBox); }, 350); };
    nodes.push(h("div", { class: "aks-card" }, [
      h("div", { class: "aks-row", style: "gap:8px;margin-bottom:10px" }, [search, h("button", { class: "aks-btn", text: "+ New", onclick: function () { crewS.showCreate = true; render(); } })]),
      listBox,
    ]));
    crewLoadList("", listBox);
  }
  function crewLoadList(q, box) {
    clear(box); box.appendChild(h("div", { class: "gd-note", text: "Loading crews..." }));
    crewCall("ak-crew", { action: "list", q: q || "" }).then(function (r) {
      if (!box.isConnected) return;
      var crews = (r && r.crews) || [];
      clear(box);
      if (!crews.length) { box.appendChild(h("div", { class: "gd-note", text: "No crews yet. Be the first -- start one." })); return; }
      crews.forEach(function (c) {
        var joinBtn = h("button", { class: "aks-btn", text: c.privacy === "request" ? "Ask" : "Join" });
        joinBtn.onclick = function () {
          joinBtn.disabled = true;
          crewCall("ak-crew", { action: "join", crew_id: c.id }).then(function (rr) {
            if (rr.ok && rr.requested) { toast("Request sent.", "good"); joinBtn.textContent = "Asked"; }
            else if (rr.ok) { toast("Joined!", "good"); crewS.loaded = false; crewRefresh(); }
            else { toast(rr.error || "Could not join.", "bad"); joinBtn.disabled = false; }
          });
        };
        box.appendChild(h("div", { class: "aks-row", style: "gap:10px;padding:9px 0;border-top:1px solid rgba(255,255,255,0.06)" }, [
          h("div", { style: "width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;background:rgba(201,168,76,0.14);border:1px solid rgba(201,168,76,0.3)", text: "🐶" }),
          h("div", { style: "flex:1" }, [
            h("div", { class: "aks-name" }, [c.name + " ", h("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
            h("div", { class: "aks-sub", text: (CREW_FNAME[c.faction] || c.faction) + " · " + (c.member_count || 0) + "/50 · " + (c.privacy || "open") }),
          ]),
          joinBtn,
        ]));
      });
    });
  }
  function crewCreateNodes(nodes) {
    var name = h("input", { maxlength: "24", type: "text", placeholder: "Crew name (3-24)", style: crewInpStyle() });
    var tag = h("input", { maxlength: "4", type: "text", placeholder: "Tag (2-4, e.g. BONE)", style: crewInpStyle() });
    var fac = h("select", { style: crewInpStyle() }, CREW_FACTIONS.map(function (f) { return h("option", { value: f.id, text: f.name }); }));
    var priv = h("select", { style: crewInpStyle() }, [
      h("option", { value: "open", text: "Open -- anyone joins" }),
      h("option", { value: "request", text: "Request -- approve members" }),
      h("option", { value: "closed", text: "Closed -- invite only" }),
    ]);
    var desc = h("input", { maxlength: "200", type: "text", placeholder: "Description (optional)", style: crewInpStyle() });
    var go = h("button", { class: "aks-btn", style: "flex:1", text: "Create Crew" });
    go.onclick = function () {
      go.disabled = true;
      crewCall("ak-crew", { action: "create", name: name.value.trim(), tag: tag.value.trim(), faction: fac.value, privacy: priv.value, description: desc.value.trim() }).then(function (r) {
        if (r.ok) { toast("Crew created -- you're the leader.", "good"); crewS.showCreate = false; crewS.loaded = false; crewRefresh(); }
        else { toast(r.error || "Could not create.", "bad"); go.disabled = false; }
      });
    };
    nodes.push(h("div", { class: "aks-card" }, [
      h("div", { class: "aks-name", style: "margin-bottom:6px", text: "Start a Crew" }),
      name, tag, fac, priv, desc,
      h("div", { class: "aks-row", style: "gap:8px;margin-top:6px" }, [go, h("button", { class: "aks-btn ghost", text: "Back", onclick: function () { crewS.showCreate = false; render(); } })]),
    ]));
  }

  // ---- chat sub-view --------------------------------------------------------
  function crewChatNodes(nodes) {
    var inCrew = !!crewS.crew;
    if (crewS.scope === "crew" && !inCrew) crewS.scope = "world";
    var wTab = h("div", { class: "gd-tab" + (crewS.scope === "world" ? " on" : ""), text: "WORLD · " + crewS.presence.world + " on", onclick: function () { crewS.scope = "world"; render(); } });
    var cTab = h("div", { class: "gd-tab" + (crewS.scope === "crew" ? " on" : ""), text: inCrew ? ("CREW · " + crewS.presence.crew + " on") : "CREW (none)", onclick: function () { if (!inCrew) { toast("Join a crew first.", "bad"); return; } crewS.scope = "crew"; render(); } });
    crewS.worldLabel = wTab; crewS.crewLabel = cTab;
    nodes.push(h("div", { class: "gd-tabs" }, [wTab, cTab]));
    var mlist = h("div", { style: "max-height:46vh;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin:8px 0;padding:2px" });
    crewS.mlist = mlist;
    nodes.push(mlist);
    crewPaintMsgs();
    var input = h("input", { maxlength: "200", type: "text", placeholder: crewS.scope === "crew" ? "Message your crew..." : "Message the world...", style: "flex:1;background:rgba(0,0,0,0.4);border:1px solid rgba(201,168,76,0.3);color:#fff;border-radius:20px;padding:10px 14px;font-size:14px;outline:none" });
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); crewSendChat(input); } });
    var send = h("button", { class: "aks-btn", text: "Send", onclick: function () { crewSendChat(input); } });
    nodes.push(h("div", { class: "aks-row", style: "gap:8px;margin-top:4px" }, [input, send]));
    crewLoadHistory(crewS.scope);
  }
  function crewPaintMsgs() {
    var mlist = crewS.mlist; if (!mlist) return;
    var arr = (crewS.msgs[crewS.scope] || []).slice(-80);
    clear(mlist);
    if (!arr.length) { mlist.appendChild(h("div", { class: "gd-note", text: "No messages yet. Start the conversation." })); return; }
    arr.forEach(function (m) {
      var nameKids = [h("b", { style: "color:#c9a84c", text: m.name || "Stray" })];
      if (m.faction && CREW_FNAME[m.faction]) nameKids.push(h("span", { style: "color:#8a8a96;font-size:10px;margin-left:6px", text: CREW_FNAME[m.faction] }));
      mlist.appendChild(h("div", { style: "background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:9px;padding:7px 9px;font-size:13px;line-height:1.35;word-break:break-word" }, [
        h("div", null, nameKids),
        h("div", { text: m.body || "" }),
      ]));
    });
    mlist.scrollTop = mlist.scrollHeight;
  }
  // ====================================================================
  // AK-PASS2 2026-06-15: the Alley Pass (battle pass) ported into the Chop
  // Shop as a gd-native tab (operator: kill the standalone overlay's lobby
  // entry; its full 30-tier track lives here in gold-glass). SAME server
  // contract as pass.js -- ak-pass get / claim-tier / unlock-premium via the
  // AKAccount Supabase client. Tier rewards queue to ak_grants server-side
  // (same rail as donations) and drain via AKSocial.claimGrants() WHEN PRESENT
  // (social.js is not loaded on shop.html -> the grant applies next time the
  // player opens the lobby Crew panel; the tier is already claimed server-side).
  // Match XP (report-match) is NOT fired here -- that stays in pass.js on the
  // game page (grantMatchRewards). The shop has no matches.
  // ====================================================================
  var passCache = null, passLoading = false;
  function passSbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function passMe() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  // mirrors pass.js call(): unwrap edge-fn errors, including the JSON body the
  // function returns on a non-2xx (needsGems / "not enough gems", etc.).
  function passCall(fn, body) {
    var sb = passSbc(); if (!sb) return Promise.resolve({ ok: false, error: "offline" });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var c = r.error.context;
        if (c && typeof c.json === "function") return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: r.error.message || "error" };
      }
      return r.data || { ok: false, error: "empty" };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }
  function passRewardEmoji(r) {
    if (!r) return "🎁";
    var art = ({ gold: "cur_gold", scrap: "cur_scrap", keys: "loot_key", chest: "chest_gold" })[r.kind];  // AK-ART: pass reward emblems use existing currency/loot/chest art
    if (art) {
      var im = h("img", { class: "pass-rw-img", src: "../assets/ui/" + art + ".jpg", alt: "" });
      im.onerror = function () { var s = document.createElement("span"); s.textContent = ({ gold: "💰", scrap: "🔩", chest: "📦", keys: "🔑" })[r.kind] || "🎁"; if (im.parentNode) im.parentNode.replaceChild(s, im); };
      return im;
    }
    return ({ card: "🃏", passxp: "⭐" })[r.kind] || "🎁";
  }
  function passRewardLabel(r) {
    if (!r) return "--";
    if (r.kind === "gold") return "💰 " + r.amount;
    if (r.kind === "scrap") return "🔩 " + r.amount + " " + (r.rarity || "");
    if (r.kind === "chest") return "📦 " + (r.card_id || "") + " chest";
    if (r.kind === "keys") return "🔑 " + r.amount + " key" + (r.amount > 1 ? "s" : "");
    if (r.kind === "card") return "🃏 " + (r.card_id || "card") + " x" + r.amount;
    return r.kind;
  }
  function passClaimTier(t, lane) {
    passCall("ak-pass", { action: "claim-tier", tier: t, lane: lane }).then(function (r) {
      if (!r || !r.ok) { toast(r && r.error ? r.error : "Could not claim.", "bad"); render(); return; }
      if (passCache) { (lane === "prem" ? (passCache.claimed_prem = passCache.claimed_prem || []) : (passCache.claimed_free = passCache.claimed_free || [])).push(t); }
      toast("Claimed " + passRewardLabel(r.reward), "ok");
      // drain the ak_grants inbox into the local economy if the social rail is
      // present (mirrors pass.js). On shop.html AKSocial is absent -> no-op; the
      // grant lands when the player next opens the lobby (social.js drains it).
      try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_) {}
      render();
    });
  }
  function passUnlockPremium() {
    if (global.confirm && !confirm("Unlock the Premium Alley Pass for 800 gems? Finish the season and you earn it back and then some.")) return;
    passCall("ak-pass", { action: "unlock-premium" }).then(function (r) {
      if (r && r.ok) { passCache = null; toast("Premium unlocked!", "ok"); render(); }       // refetch (mirrors pass.js load())
      else if (r && r.needsGems) { toast("Need " + (r.need || 800) + " gems -- grab a pack in the Gems tab.", "bad"); }
      else { toast(r && r.error ? r.error : "Could not unlock.", "bad"); }
    });
  }
  function passView() {
    // signed out -> gd-native sign-in CTA (like the shop's other gated tabs)
    if (!passMe()) {
      var out = secHead("Alley Pass -- Season 1", "Sign in to start your Alley Pass -- every match levels it up, then claim the tier rewards here.");
      out.push(h("div", { class: "aks-row", style: "justify-content:center;margin-top:12px" }, [
        h("button", { class: "aks-btn gold", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } }),
      ]));
      return out;
    }
    // async: fetch the pass once, cache it, then re-render through the shop's render()
    if (!passCache) {
      if (!passLoading) {
        passLoading = true;
        passCall("ak-pass", { action: "get" }).then(function (r) {
          passLoading = false;
          passCache = (r && r.ok) ? r : { _err: (r && r.error) || "Could not load your pass." };
          render();
        });
      }
      return secHead("Alley Pass -- Season 1", "Loading your pass...");
    }
    if (passCache._err) {
      var e0 = secHead("Alley Pass -- Season 1", "Season rewards -- climb tiers, claim the haul.");
      e0.push(emptyCard(passCache._err));
      return e0;
    }
    var P = passCache;
    var maxTier = P.max_tier || 30, xpPer = P.xp_per_tier || 100;
    var tier = P.tier | 0, xp = P.xp | 0, premium = !!P.premium;
    var cf = P.claimed_free || [], cp = P.claimed_prem || [], track = P.track || { free: [], prem: [] };
    var intoTier = xp - tier * xpPer;
    var pct = tier >= maxTier ? 100 : Math.max(0, Math.min(100, Math.round(intoTier / xpPer * 100)));

    var nodes = secHead("Alley Pass -- Season " + (P.season || 1),
      "Every match levels your pass. Free lane is yours -- Premium doubles the haul. Claim each tier you've reached.");

    // XP + premium header (gold-glass card; reuses the .copies bar for the XP fill)
    var premCta = premium
      ? h("span", { class: "aks-owned", text: "✓ PREMIUM ACTIVE" })
      : h("button", { class: "aks-btn gold gem-cost", text: "Unlock Premium - 800", onclick: passUnlockPremium });
    nodes.push(h("div", { class: "aks-card r-Legendary aks-up" }, [
      h("div", { class: "aks-meta" }, [
        h("div", { class: "aks-row" }, [
          h("div", { class: "aks-name", text: "Tier " + tier + " / " + maxTier }),
          h("div", { class: "aks-sub", text: tier >= maxTier ? "season maxed" : (intoTier + " / " + xpPer + " XP") }),
        ]),
        h("div", { class: "copies r-Legendary" }, [h("b", { style: "width:" + pct + "%" })]),
        h("div", { class: "aks-row", style: "margin-top:8px" }, [
          h("span", { class: "aks-desc", text: "Free lane is yours. Premium doubles the haul." }),
          premCta,
        ]),
      ]),
    ]));

    // 30-tier track -- one gd card per tier, free + prem lane rows
    if (!track.free || !track.free.length) { nodes.push(emptyCard("Track unavailable -- reload the shop.")); return nodes; }
    var tiles = [];
    for (var t = 1; t <= maxTier; t++) tiles.push(passTierTile(t, tier, premium, track, cf, cp));
    nodes.push(grid(tiles));
    return nodes;
  }
  function passTierTile(t, curTier, premium, track, cf, cp) {
    return h("div", { class: "aks-card" + (t === curTier + 1 ? " r-Legendary aks-up" : " r-Rare") }, [
      h("div", { class: "aks-meta" }, [
        h("div", { class: "aks-name", text: "Tier " + t + (t === curTier + 1 ? "  (next)" : (t <= curTier ? "  ✓" : "")) }),
        passLaneRow(t, "free", curTier, premium, track, cf, cp),
        passLaneRow(t, "prem", curTier, premium, track, cf, cp),
      ]),
    ]);
  }
  function passLaneRow(t, lane, curTier, premium, track, cf, cp) {
    var reward = (track[lane] || [])[t - 1];
    var reached = t <= curTier;
    var claimedArr = lane === "prem" ? cp : cf;
    var claimed = claimedArr.indexOf(t) >= 0;
    var btn;
    if (claimed) btn = h("span", { class: "aks-owned", text: "✓ claimed" });
    else if (!reached) btn = h("button", { class: "aks-btn ghost", disabled: "true", text: "🔒 Tier " + t });
    else if (lane === "prem" && !premium) btn = h("button", { class: "aks-btn ghost", text: "🔒 Premium", onclick: function () { toast("Unlock Premium up top to claim this lane.", "bad"); } });
    else { btn = h("button", { class: "aks-btn", text: "Claim", onclick: function () { btn.setAttribute("disabled", "true"); passClaimTier(t, lane); } }); }
    return h("div", { class: "aks-row pass-rwrow" }, [
      h("div", { class: "pass-rw" }, [
        h("span", { class: "pass-rw-em " + (lane === "prem" ? "prem" : "free") }, [passRewardEmoji(reward)]),
        h("span", { class: "aks-sub", text: (lane === "prem" ? "PREMIUM" : "FREE") + " · " + passRewardLabel(reward) }),
      ]),
      btn,
    ]);
  }
// ============================================================================
// AK-HIT 2026-06-15: THE HIT LIST (daily/weekly quests) ported from the
// standalone quests.js overlay into the Chop Shop as a gd-native tab.
// Server calls go through the AUTHED Supabase client (AKAccount.client()
// .functions.invoke) -- SAME 'ak-quests' edge fn + SAME {action:"get"} /
// {action:"claim", quest_id} payloads as the overlay. Signed-out degrades to
// a sign-in prompt like the shop's other tabs. Async: module-level cache +
// render() after invoke resolves (same pattern as the shop's other views).
// PASTE this block alongside the other view functions (e.g. just above
// upgradeView() / streetCodeView()), INSIDE the IIFE.
// ============================================================================

// module-scope state -- declare near `var state`/`var filters` at top of the IIFE,
// OR leave it here (still inside the IIFE scope, hoisted by `var`):
var hit = { loaded: false, loading: false, error: null, quests: [] };

// authed client + signed-in user, mirrored from quests.js sbc()/me()
function hitSb() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
function hitUser() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }

// EXACT port of quests.js call() -- unwraps {data} / surfaces edge-fn JSON errors
function hitCall(fn, body) {
  var sb = hitSb(); if (!sb) return Promise.resolve({ ok: false, error: "offline" });
  return sb.functions.invoke(fn, { body: body }).then(function (r) {
    if (r.error) {
      var c = r.error.context;
      if (c && typeof c.json === "function") return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
      return { ok: false, error: r.error.message || "error" };
    }
    return r.data || { ok: false, error: "empty" };
  }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
}

// EXACT port of quests.js rewardLabel()
function hitRewardLabel(r) {
  if (!r) return "--";
  if (r.kind === "gold") return "💰 " + r.amount;
  if (r.kind === "passxp") return "⭐ " + r.amount + " Pass XP";
  if (r.kind === "scrap") return "🔩 " + r.amount + " " + (r.rarity || "");
  if (r.kind === "chest") return "📦 " + (r.card_id || "") + " chest";
  if (r.kind === "keys") return "🔑 " + r.amount;
  if (r.kind === "card") return "🃏 " + (r.card_id || "") + " x" + r.amount;
  return r.kind;
}

// fetch once, cache, re-render when it lands (guarded so render()->hitView()
// can't re-fire the call). force=true after a claim to refresh progress.
function hitLoad(force) {
  if (hit.loading) return;
  if (hit.loaded && !force) return;
  hit.loading = true; hit.error = null;
  hitCall("ak-quests", { action: "get" }).then(function (r) {
    hit.loading = false;
    if (!r || !r.ok) { hit.error = (r && r.error) ? r.error : "Could not load the Hit List."; hit.loaded = false; }
    else { hit.quests = r.quests || []; hit.loaded = true; }
    if (activeTab === "hit2") render();   // re-render only if still on this tab
  });
}

// claim -> SAME {action:"claim", quest_id} as the overlay; mirror its grants
// drain (non-passxp rewards ride the AKSocial grants rail) + refetch.
function hitClaim(q, btn) {
  if (btn) btn.disabled = true;
  hitCall("ak-quests", { action: "claim", quest_id: q.id }).then(function (r) {
    if (!r || !r.ok) { toast(r && r.error ? r.error : "Could not claim.", "bad"); if (btn) btn.disabled = false; return; }
    toast("Claimed " + hitRewardLabel(q.reward), "ok");
    if (q.reward && q.reward.kind !== "passxp") { try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_) {} }
    hit.loaded = false; hitLoad(true);   // refresh progress + claim state
  });
}

// gd-native quest card: secHead/.aks-card/.aks-row/.aks-name/.aks-desc/.gd-sub
// + reused copiesBar() for the progress bar (gold-glass, existing shop.css).
function hitQuestCard(q) {
  var target = Math.max(1, q.target | 0);
  var done = q.claimable || q.claimed;
  var btn;
  if (q.claimed) btn = h("button", { class: "aks-btn ghost", disabled: "true", text: "✓ Done" });
  else if (q.claimable) { btn = h("button", { class: "aks-btn", text: "Claim" }); btn.onclick = function () { hitClaim(q, btn); }; }
  else btn = h("button", { class: "aks-btn ghost", disabled: "true", text: q.progress + "/" + q.target });
  return h("div", { class: "aks-card " + rarClass(done ? "Legendary" : "Epic") }, [
    h("div", { class: "aks-meta" }, [
      h("div", { class: "aks-row" }, [
        h("div", { style: "flex:1" }, [
          h("div", { class: "aks-name", text: q.title }),
          h("div", { class: "aks-desc", text: q.desc }),
          h("div", { class: "gd-sub", text: hitRewardLabel(q.reward) }),
        ]),
        btn,
      ]),
      copiesBar(q.progress | 0, target, done ? "Legendary" : "Epic"),
      h("div", { class: "gd-note", text: q.progress + " / " + q.target }),
    ]),
  ]);
}

// the tab body
function hitView() {
  // signed-out -> sign-in prompt (matches the overlay's load() degrade)
  if (!hitUser()) {
    var nodes0 = secHead("Hit List", "Daily + weekly missions for gold, scrap and Pass XP.");
    nodes0.push(emptyCard("Sign in to take on daily + weekly missions."));
    nodes0.push(h("div", { class: "aks-row", style: "justify-content:center;margin-top:10px" }, [
      h("button", { class: "aks-btn", text: "Sign in with Google", onclick: function () { try { if (global.AKAccount && global.AKAccount.signIn) global.AKAccount.signIn(); } catch (_) {} } }),
    ]));
    return nodes0;
  }
  if (!hit.loaded && !hit.error) hitLoad(false);   // kick the async fetch on first view
  var nodes = secHead("Hit List", "Take on daily + weekly missions -- climb the bar, then claim gold, scrap and Pass XP. Resets every morning (daily) and Monday (weekly).");
  if (hit.loading && !hit.loaded) { nodes.push(emptyCard("Loading the Hit List...")); return nodes; }
  if (hit.error && !hit.loaded) {
    nodes.push(emptyCard(hit.error));
    nodes.push(h("div", { class: "aks-row", style: "justify-content:center;margin-top:10px" }, [
      h("button", { class: "aks-btn ghost", text: "Retry", onclick: function () { hitLoad(true); } }),
    ]));
    return nodes;
  }
  var daily = hit.quests.filter(function (q) { return q.scope === "daily"; });
  var weekly = hit.quests.filter(function (q) { return q.scope === "weekly"; });
  if (!daily.length && !weekly.length) { nodes.push(emptyCard("No active missions right now -- check back after your next match.")); return nodes; }
  nodes = nodes.concat(secHead("Daily -- resets every morning", daily.length + " active"));
  nodes.push(daily.length ? grid(daily.map(hitQuestCard)) : emptyCard("No daily missions."));
  nodes = nodes.concat(secHead("Weekly -- resets Monday", weekly.length + " active"));
  nodes.push(weekly.length ? grid(weekly.map(hitQuestCard)) : emptyCard("No weekly missions."));
  return nodes;
}

  function upgradeView() {
    var e = econ(), p = localProfile();
    var cardTiles = [];
    if (e && p && e.upgradeNeed) {
      cardTiles = garageCards().map(function (c) { return garageTile(e, p, c); });
    }

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
    // AK-GARAGE: header makes the unification explicit -- this IS the collection.
    var nodes = secHead("Collection", "Your FULL collection -- every card you own, its level, its banked dupes -- all in one place. Level cards 1 to 10 with duplicate copies + coins. Spare dupes beyond the next level bank for future levels. The curve is HP/DMG only -- a maxed Common never beats a base Mythic. No pay-to-win.");
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
      " Gems are purchased through Stripe secure checkout. Cards, Coins and Scrap are earned through play.",
    ]);
  }

  // ---- deck-lab profile sync shim ------------------------------------------
  // The deck lab (index.html) reads localStorage ak_profile.owned by card NAME,
  // while the server keys inventory by player_id. Every grant that resolves in
  // this surface -- demo pulls included -- is ALSO merged into ak_profile so the
  // deck lab sees it immediately. Names merge unique (shop dupes feed the Garage,
  // not the +coins rule -- that one is match-drops only). If no profile exists
  // yet we write a deckless stub; index.html loadProfile() merges it over the
  // starter set on next game boot. Spec: ecosystem/PROGRESSION_DESIGN.md
  // AK-SCRAP: extended shim -- scrap = {rarity:+n} delta, chests = {tier:+n}
  // delta. The stub now carries the full Section-1 field set (scrap/chests/
  // keys/sp/spEarned/skills) so a shop-first profile never loses fields when
  // index.html loadProfile() merges it over the starter set.
  function profileSync(names, coins, scrap, chests) {
    try {
      if (typeof localStorage === "undefined" || !localStorage) return;
      var p = null;
      try { p = JSON.parse(localStorage.getItem("ak_profile") || "null"); } catch (e) { p = null; }
      if (!p || typeof p !== "object") p = { level: 1, xp: 0, coins: 0, trophies: 0, owned: [] };
      if (!Array.isArray(p.owned)) p.owned = [];
      if (!p.scrap || typeof p.scrap !== "object") p.scrap = { Common: 0, Rare: 0, Epic: 0, Legendary: 0, Mythic: 0 };
      if (!p.chests || typeof p.chests !== "object") p.chests = { wood: 0, bronze: 0, silver: 0, gold: 0, diamond: 0 };
      if (typeof p.keys !== "number") p.keys = 0;
      if (typeof p.sp !== "number") p.sp = 0;
      if (typeof p.spEarned !== "number") p.spEarned = 0;
      if (!p.skills || typeof p.skills !== "object") p.skills = {};
      (names || []).forEach(function (n) { if (n && p.owned.indexOf(n) < 0) p.owned.push(n); });
      if (coins) p.coins = (p.coins || 0) + coins;
      if (scrap) for (var r in scrap) { if (p.scrap[r] != null) p.scrap[r] = (p.scrap[r] | 0) + (scrap[r] | 0); }
      if (chests) for (var t in chests) { if (p.chests[t] != null) p.chests[t] = (p.chests[t] | 0) + (chests[t] | 0); }
      localStorage.setItem("ak_profile", JSON.stringify(p));
    } catch (e) {}
  }
  // AK-SHOPFIX item 3: the server-grant -> local-copy bridge. EVERY card a
  // server action grants is banked as a real local copy (owned + copies++) via
  // AK_ECON.addCopy, so the Garage upgrade math sees it. Degrades to a name-only
  // merge if the economy module has not loaded yet.
  function cardNameOf(x) {
    if (!x) return null;
    if (typeof x === "string") return x;
    return x.name || (cardById(x.card_id) || {}).name || null;
  }
  function grantCardCopy(cardLike, n) {
    var name = cardNameOf(cardLike);
    if (!name) return;
    var e = econ();
    if (e && e.addCopy) e.addCopy(name, n || 1);
    else profileSync([name], 0);
  }
  function grantServerCards(cards) {
    (cards || []).forEach(function (c) { grantCardCopy(c, 1); });
  }

  function syncDrawResults(results) {
    results = results || [];
    var e = econ();
    if (!cfg.online && e) {
      // AK-SCRAP: local pulls -- dupes convert to scrap (no more silent merge).
      // Marks r.dupe / r.scrap so the reveal shows the payout.
      try {
        e.mutateProfile(function (p) {
          results.forEach(function (r) {
            var c = cardById(r.card_id) || {};
            var name = c.name || r.name;
            var rar = c.rarity || r.rarity || "Common";
            if (!name) return;
            if (!p.copies || typeof p.copies !== "object") p.copies = {};
            if (p.owned.indexOf(name) >= 0) {
              var s = e.SCRAP_DUPE[rar] || 5;
              if (p.scrap[rar] != null) p.scrap[rar] = (p.scrap[rar] | 0) + s;
              p.copies[name] = (p.copies[name] | 0) + 1;       // AK-VIS: dupes also pay a copy
              r.dupe = true; r.scrap = s;
            } else {
              p.owned.push(name);
              p.copies[name] = (p.copies[name] | 0) + 1;       // AK-SHOPFIX item 3: a NEW pull banks its first copy
            }
          });
        });
        return;
      } catch (_) {}
    }
    // AK-SHOPFIX item 3: online (or no econ) -- bank every granted card as a
    // local copy so the Garage upgrade math sees it (was a name-only merge).
    grantServerCards(results);
  }
  function syncBoughtCard(cardId) {
    var c = cardById(cardId);
    if (c && c.name) profileSync([c.name], 0);
  }

  // ---- intent dispatch (server decides) -----------------------------------
  function doAction(action, extra, okMsg) {
    recomputeCfg();   // AK-SHOPFIX item 2: never tell a signed-in player to log in
    // AK-WALLET-MERGE: card purchases with Scrap are LOCAL in both modes --
    // the scrap pocket lives in ak_profile (matches/crates pay there).
    // AK-SHOPFIX item 4: full try/catch -- a thrown error can never freeze the
    // UI mid-action; we always re-render so the screen stays interactive.
    if (action === "buy-card" && extra && extra.card_id) {
      try {
        var cardL = cardById(extra.card_id);
        if (!cardL) { toast("Card unavailable.", "bad"); return; }
        var eL = econ();
        if (!eL) { syncBoughtCard(extra.card_id); toast(okMsg + " (saved to your crew).", "ok"); return; }
        var rL = eL.buyCardWithScrap({ name: cardL.name, rarity: cardL.rarity, scrap: cardL.scrap });
        if (rL && rL.ok) { toast(okMsg + " (-" + fmt(rL.spent) + " " + cardL.rarity + " Scrap).", "ok"); render(); }
        else { toast(humanErr(rL || {}), "bad"); }
      } catch (err) { toast("Could not complete -- try again.", "bad"); try { render(); } catch (_) {} }
      return;
    }
    if (!cfg.online) {
      if (action === "buy-card" && extra && extra.card_id) {
        // AK-SCRAP: local buys are REAL now -- matching-rarity scrap is checked
        // and deducted from ak_profile atomically before the card is granted.
        var card = cardById(extra.card_id);
        if (!card) { toast("Card unavailable.", "bad"); return; }
        var e = econ();
        if (!e) { syncBoughtCard(extra.card_id); toast(okMsg + " (saved to your crew).", "ok"); return; }
        var r0 = e.buyCardWithScrap({ name: card.name, rarity: card.rarity, scrap: card.scrap });
        if (r0 && r0.ok) { toast(okMsg + " (-" + fmt(r0.spent) + " " + card.rarity + " Scrap).", "ok"); render(); }
        else { toast(humanErr(r0 || {}), "bad"); }
        return;
      }
      promptSignIn(); return;
    }
    api(action, extra).then(function (r) {
      if (r.ok) {
        if (action === "buy-card" && extra && extra.card_id) syncBoughtCard(extra.card_id);
        if (action === "open-chest" && r.grants) {
          // AK-SHOPFIX item 3: currencies via profileSync, cards via the copy
          // bridge so server-chest grants land as real local copies for upgrades.
          profileSync([], r.grants.coins || 0, r.grants.scrap || null, r.grants.chests || null);
          grantServerCards(r.grants.cards || []);
        }
        toast(okMsg, "ok"); load();
      }
      else if (r.gated) { toast(r.message || "Coming soon.", "bad"); }
      else { toast(humanErr(r), "bad"); }
    }).catch(function () { toast("Network error.", "bad"); });
  }
  function promptSignIn() {
    var acct = (typeof window !== "undefined") && window.AKAccount;
    if (acct && acct.signIn) { toast("Sign in with Google to buy -- your gems save to your account.", "ok"); acct.signIn(); }
    else { toast("Sign in (lobby) to unlock purchases.", "bad"); }
  }
  function buyGems(sku) {
    recomputeCfg();   // AK-SHOPFIX item 2: a signed-in player must reach checkout, never the log-in nag
    if (!cfg.online) { promptSignIn(); return; }
    api("buy-gems", {
      sku: sku,
      success_url: location.href.split("#")[0] + "#gems-ok={CHECKOUT_SESSION_ID}",
      cancel_url: location.href.split("#")[0],
    }).then(function (r) {
      if (r.ok && r.url) { toast("Opening secure checkout...", "ok"); location.href = r.url; }
      else { toast(r.detail || humanErr(r), "bad"); }
    }).catch(function () { toast("Checkout unavailable.", "bad"); });
  }
  function humanErr(r) {
    var m = {
      INSUFFICIENT_SCRAP: "Not enough Scrap Tokens -- win matches and crack crates.", INSUFFICIENT_FUNDS: "Not enough coins -- win matches and crack crates.",
      INSUFFICIENT_COPIES: "Not enough copies -- dupes from crates, draws and the Card Shop all count.",  // AK-GARAGE
      INSUFFICIENT_GEMS: "Not enough Gems.", MAX_LEVEL: "Already max level.",
      NO_CHEST_OWNED: "You do not own that crate.", CARD_NOT_OWNED: "You do not own that card yet.",
      NO_TOPOFF_NEEDED: "You already have the copies for this level.", EMPTY_CATALOG: "Catalog unavailable.",
      NO_KEYS: "No Keys left -- Diamond crates and city sweeps pay them.",  // AK-KEYS
      ALREADY_OWNED: "Already in your crew -- sign in to stack copies for the Garage.",
      BAD_TIER: "Unknown crate tier.", BAD_REQ: "Could not complete.",
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
    recomputeCfg();   // AK-SHOPFIX item 2: resolve identity from live storage/globals too
    if (cfg.playerId) try { localStorage.setItem("ak_player_id", cfg.playerId); } catch (e) {}
    ensureRoot();
    // deep-link: shop.html#handlers / #draw / #cards ... opens straight to that tab
    try { var hh = (location.hash || "").replace(/^#/, "").split("&")[0];
      if (["deck", "gems", "cards", "draw", "chests", "upgrade", "codex2", "handlers", "street", "drip2", "crew2", "pass2", "hit2"].indexOf(hh) >= 0) activeTab = hh; } catch (_) {}
    root.removeAttribute("hidden");
    ensureCatalog().then(ensureEconomy).then(load);   // AK-SCRAP: shared economy first
    confirmPendingGems();
  }
  // Stripe success redirect lands back here with #gems-ok=<session_id>.
  // confirm-gems is idempotent server-side (ak_transactions unique lock), so
  // re-running on refresh is safe; the hash is cleared after one attempt.
  function confirmPendingGems() {
    var m = /[#&]gems-ok=([^&]+)/.exec(location.hash || "");
    recomputeCfg();   // AK-SHOPFIX item 2: identity may have just restored on this redirect
    if (!m || !cfg.online) return;
    var sid = decodeURIComponent(m[1]);
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
    api("confirm-gems", { session_id: sid }).then(function (r) {
      if (r.ok || r.error === "already_credited") {
        // AK-SHOPFIX item 3: a gem-pack that also grants cards banks them locally.
        if (r.grants && r.grants.cards) grantServerCards(r.grants.cards);
        toast(r.ok ? "Gems delivered. Spend wisely, champ." : "Already credited.", "ok"); load();
      }
      else { toast(humanErr(r), "bad"); }
    }).catch(function () { toast("Could not confirm purchase -- it will retry next visit.", "bad"); });
  }
  function close() { if (root) root.setAttribute("hidden", ""); }

  global.AKShop = {
    open: open, close: close,
    openLocalChest: openLocalChest,      // AK-KEYS: earned-chest opener (local, free)
    config: function (o) { Object.assign(cfg, o || {}); cfg.online = !!(cfg.anonKey && cfg.playerId); },
    _state: function () { return state; },
  };

  // AK-SHOPFIX item 2: re-config + re-render the moment auth state changes, so
  // a player who signs in mid-session never gets the "log in" nag.
  try { if (global.addEventListener) global.addEventListener("ak-auth", onAuthEvent); } catch (_) {}

  if (document.body && document.body.dataset && document.body.dataset.akshopStandalone === "1") {
    document.addEventListener("DOMContentLoaded", function () { open({}); });
  }
})(typeof window !== "undefined" ? window : this);
