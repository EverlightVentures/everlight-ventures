/* ===========================================================================
 * AK RAID MAP -- window.akOpenRaidMap()
 * ---------------------------------------------------------------------------
 * "See the other blocks. Hit em for their stash." A self-mounting DOM overlay
 * (mirrors social.js / trading.js panel style -- no innerHTML, textContent only,
 * no bundler, no em-dashes) that lists OTHER bases to raid: the 29 seeded AI
 * dogs from AK_POPULATION (their clan, district, rank, trophies + an estimated
 * stash you take on a win).
 *
 * Tapping RAID launches an RPG-STYLE raid through the EXISTING raid path
 * (AK_RAIDSCENE.launch -> mode:'raid' on game.html, the SAME handoff raid.js +
 * worldmap.js use) -- NOT the lane/tower (FROZEN engine.js) battler. The win is
 * settled on game.html by AK_MODES.raid, which grants the target.reward
 * (gold / scrap / wood / stone -- soft + materials ONLY, never gems/$BCARDD)
 * straight through AK_ECON, star-scaled. The loot here is scaled to the
 * TARGET'S trophies so a King of the Block pays out far heavier than a Pup.
 *
 * Canon (AK_CORE_LOOP_CANON + AK_ROADMAP_V2 sec 0): clans Zoomie Syndicate /
 * Leashbreak Tactix / Boneguard Crew / K9 Circuitry / Stray; ranks Stray -> Pup
 * -> Runner -> Warrior -> Enforcer -> Right Paw -> King of the Block; OUR 9
 * districts; the Fence = market (raided produce launders into gold), the Watch =
 * guarding. All names come from AK_POPULATION rows -- nothing invented here.
 *
 * STATE: read-only. This module NEVER writes the profile (the raid win on
 * game.html owns the grant), so zero-state stays byte-identical. Perf: lazy DOM
 * (shell built once, rows rendered once per open), no timers, list capped --
 * 60fps-safe on a cheap Android.
 * ======================================================================== */
(function (global) {
  "use strict";

  // ---- light reads (never throw into the host) ------------------------------
  function pop() { try { return global.AK_POPULATION || null; } catch (_) { return null; } }
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function ctx() { try { return global.AK_CTX || null; } catch (_) { return null; } }
  function myTrophies() { try { var e = econ(), p = e && e.loadProfile && e.loadProfile(); return (p && p.trophies | 0) || 0; } catch (_) { return 0; } }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

  // ---- safe DOM builder (no innerHTML; dynamic text via textContent) ---------
  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null) return;
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
  function setKids(el, nodes) { el.replaceChildren.apply(el, [].concat(nodes).filter(function (n) { return n != null; })); }

  // ---- loot scaling (matches AK_MODES.raid grant: gold/scrap/wood/stone) ------
  // Tier mirrors raid.js publishMyBase: <600 = 1, <1200 = 2, else 3. The estimate
  // shown is EXACTLY what modes.js banks on a 1-star win (then star-scaled there).
  function tierFor(tr) { tr = tr | 0; return tr >= 1200 ? 3 : tr >= 600 ? 2 : 1; }
  // stable 0..1 jitter from an id so a target's stash never flickers between opens
  function seedJ(id) { var h = 2166136261 >>> 0, s = String(id || ""); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 1000) / 1000; }
  // a handful of OUR districts grow signature crops (canon) -- their stash carries
  // produce, which a raid laundres into gold through the Fence (gritty-gangland).
  var GARDEN = { THE_YARDS: 1, FACTORY_ROW: 1, THE_OVERLOOK: 1, HOME_TURF: 1 };
  function lootFor(row) {
    var tr = row.trophies | 0, tier = tierFor(tr), j = seedJ(row.id);
    var gold = Math.round(90 + tr * 0.16 + j * 80);
    var produce = GARDEN[row.district] ? Math.round(20 + tr * 0.05 + j * 30) : 0;
    var fenced = produce;                                  // produce launders 1:1 -> gold at the Fence
    return {
      tier: tier,
      gold: gold + fenced,
      goldRaw: gold,
      produce: produce,
      scrap: tier >= 2 ? tier * 2 : 1,
      scrapR: tier >= 3 ? "Epic" : "Rare",
      wood: Math.round(14 + tr * 0.02 + j * 16),
      stone: tier >= 2 ? Math.round(tr * 0.012 + j * 10) : 0
    };
  }
  // ---- REAL art resolvers (AK-ART 2026-07-01) --------------------------------
  // Reuse the SAME crest map the Fence (marketplace.js) + social.js clan menu use
  // and the transparent-cleaned chip-icon set -- NO new art path invented. The clan
  // CREST (assets/ui/Crest_*.jpg, keyed by faction id = row.clan) is the target's
  // identity token; each stash amount rides a resource chip (assets/icons/chip_*.png).
  // Both degrade to a unicode glyph if the file is missing (headless / stray seller).
  var FAC_CREST = {
    boneguard_crew:    "assets/ui/Crest_Boneguard.jpg",
    zoomie_syndicate:  "assets/ui/Crest_Zoomie.jpg",
    leashbreak_tactix: "assets/ui/Crest_Leashbreak.jpg",
    k9_circuitry:      "assets/ui/Crest_K9.jpg"
  };
  function facCrest(fac) { return FAC_CREST[fac] || ""; }
  var RES_CHIP = {
    gold:  "assets/icons/chip_gold.png",  produce: "assets/icons/chip_produce.png",
    wood:  "assets/icons/chip_wood.png",  stone:   "assets/icons/chip_stone.png",
    metal: "assets/icons/chip_metal.png", scrap:   "assets/icons/chip_scrap.png"
  };
  var ICO = { gold: "\u{1FA99}", produce: "\u{1F33F}", wood: "\u{1FAB5}", stone: "\u{1FAA8}", metal: "\u{1F529}", scrap: "⚙️" };
  // a resource amount as REAL chip art (transparent PNG); degrades to the ICO glyph if missing.
  function resIcon(kind, px) {
    px = px || 16;
    var src = RES_CHIP[kind];
    if (!src) return mk("span", { class: "akrm-rig", text: ICO[kind] || "" });
    var img = mk("img", { class: "akrm-ri", src: src, alt: "", loading: "lazy", style: "width:" + px + "px;height:" + px + "px" });
    img.onerror = function () { try { if (img.parentNode) img.parentNode.replaceChild(mk("span", { class: "akrm-rig", text: ICO[kind] || "" }), img); } catch (_) {} };
    return img;
  }
  // one stash leg = chip art + amount (+ rarity tag for scrap).
  function stashChip(kind, amount, rarity) {
    var kids = [resIcon(kind, 15), mk("span", { class: "akrm-amt", text: String(amount) })];
    if (kind === "scrap" && rarity) kids.push(mk("span", { class: "akrm-rar", text: rarity }));
    return mk("span", { class: "akrm-chip" }, kids);
  }

  // ---- CSS (self-contained gold-cyberpunk; themes even sans shop.css) ---------
  function injectCss() {
    if (document.getElementById("ak-raidmap-css")) return;
    var st = document.createElement("style"); st.id = "ak-raidmap-css";
    st.textContent = [
      "#ak-raidmap{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#120a0c,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-raidmap.open{display:flex}",
      ".akrm-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(232,90,90,0.22)}",
      ".akrm-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#ff6b6b;flex:1}",
      ".akrm-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".akrm-sub{color:#9a9aa6;font-size:11px}",
      ".akrm-bar{padding:6px 14px 2px;color:#cf9b6b;font-size:11px;letter-spacing:.4px}",
      ".akrm-body{flex:1;overflow-y:auto;padding:8px 12px 18px;-webkit-overflow-scrolling:touch}",
      ".akrm-card{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-left:3px solid var(--cl,#c9a84c);border-radius:12px;padding:10px;margin-bottom:9px}",
      ".akrm-crest{flex:0 0 auto;width:48px;height:48px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px;overflow:hidden;color:#15110a;background:var(--cl,#c9a84c);border:1px solid rgba(0,0,0,0.3)}",
      ".akrm-crest img{width:100%;height:100%;object-fit:cover;object-position:center top}",
      ".akrm-mid{flex:1;min-width:0}",
      ".akrm-nm{font-weight:800;color:#fff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
      ".akrm-cl{font-weight:800;color:var(--cl,#c9a84c)}",
      ".akrm-stash{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-top:6px}",
      ".akrm-stash-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#cf9b6b;margin-right:1px}",
      ".akrm-chip{display:inline-flex;align-items:center;gap:3px;background:rgba(0,0,0,0.34);border:1px solid rgba(201,168,76,0.30);border-radius:7px;padding:2px 6px;font-size:11px;font-weight:800;line-height:1}",
      ".akrm-ri{display:inline-block;object-fit:contain;vertical-align:middle}",
      ".akrm-rig{font-size:12px}",
      ".akrm-amt{color:#fff}",
      ".akrm-rar{color:#cf9b6b;font-size:9px;font-weight:700;text-transform:uppercase}",
      ".akrm-fence{display:flex;align-items:center;gap:3px;color:#7CFFb0;font-size:10px;margin-top:4px}",
      ".akrm-raid{flex:0 0 auto;background:linear-gradient(180deg,#ff7b5f,#cf3b22);color:#1a0805;border:0;border-radius:9px;padding:11px 14px;font-weight:800;letter-spacing:.5px;cursor:pointer}",
      ".akrm-raid:active{transform:scale(0.96)}",
      ".akrm-note{color:#9a9aa6;font-size:12px;text-align:center;padding:22px 10px;line-height:1.5}",
      ".akrm-toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:#1a1a22;color:#ff9d6b;border:1px solid rgba(232,90,90,0.4);padding:9px 16px;border-radius:20px;z-index:72;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".akrm-toast.show{opacity:1}"
    ].join("");
    document.head.appendChild(st);
  }

  // ---- DOM shell (built once, lazily) ----------------------------------------
  var root, bodyEl, barEl, toastEl;
  function buildShell() {
    if (root) return;
    injectCss();
    var xBtn = mk("button", { class: "akrm-x", type: "button", "aria-label": "close", onclick: close, text: "×" });
    var top = mk("div", { class: "akrm-top" }, [
      mk("div", { style: "flex:1" }, [
        mk("h2", { text: "RAID MAP" }),
        mk("div", { class: "akrm-sub", text: "scout the other blocks -- hit em for their stash" })
      ]),
      xBtn
    ]);
    barEl = mk("div", { class: "akrm-bar" });
    bodyEl = mk("div", { class: "akrm-body" });
    root = mk("section", { id: "ak-raidmap" }, [top, barEl, bodyEl]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "akrm-toast" }); document.body.appendChild(toastEl);
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }

  // ---- target list -----------------------------------------------------------
  var MAX_ROWS = 24;
  function targets() {
    var P = pop(); if (!P) return [];
    var rows = [];
    try { rows = (P.leaderboard && P.leaderboard()) || (P.roster && P.roster()) || []; } catch (_) { rows = []; }
    // drop yourself (can't raid your own block) + cap for cheap-Android render
    rows = rows.filter(function (r) { return r && !r.isYou; });
    return rows.slice(0, MAX_ROWS);
  }

  function crestFor(row) {
    var col = row.color || "#c9a84c";
    var crest = mk("div", { class: "akrm-crest", style: "--cl:" + col + ";border-color:" + col + "88;box-shadow:0 0 9px " + col + "55" });
    var letter = (row.name || "?").charAt(0).toUpperCase();
    function toLetter() { try { crest.textContent = letter; } catch (_) {} }
    // fallback rung 2: the target's own card PORTRAIT (row.avatar = akCardArtRel result,
    // relative to assets/); webp->png via the canonical akImgErr, then the letter glyph.
    function toCardArt() {
      var av = row.avatar ? ("assets/" + row.avatar) : "";
      if (!av) { toLetter(); return; }
      var pi = mk("img", { alt: "", src: av });
      pi.onerror = function () { try { if (global.akImgErr && global.akImgErr(pi)) return; } catch (_) {} toLetter(); };
      try { crest.textContent = ""; crest.appendChild(pi); } catch (_) { toLetter(); }
    }
    // PRIMARY: the target's clan CREST (assets/ui/Crest_*.jpg via the shared faction map,
    // keyed by faction id = row.clan) -- the SAME art the Fence sellerAvatar + social clan menu use.
    var src = facCrest(row.clan);
    if (src) {
      var img = mk("img", { alt: "", src: src, loading: "lazy" });
      img.onerror = toCardArt;
      crest.appendChild(img);
    } else { toCardArt(); }
    return crest;
  }

  function rowCard(row) {
    var l = lootFor(row);
    var cl = row.color || "#c9a84c";
    var meta = (row.clanName || "Stray") + " · " + (row.districtName || row.district || "the streets") + " · " + (row.rank || "Stray");
    // STASH chips mirror the exact legs modes.js banks on a win (gold/scrap/wood/stone);
    // gold already folds the laundered produce, so produce rides the fence note below.
    var chips = [mk("span", { class: "akrm-stash-lbl", text: "STASH" }), stashChip("gold", l.gold)];
    if (l.scrap) chips.push(stashChip("scrap", l.scrap, l.scrapR));
    if (l.wood) chips.push(stashChip("wood", l.wood));
    if (l.stone) chips.push(stashChip("stone", l.stone));
    var mid = mk("div", { class: "akrm-mid" }, [
      mk("div", { class: "akrm-nm" }, [row.name + "  ", mk("span", { class: "akrm-cl", style: "--cl:" + cl, text: (row.trophies | 0) + " tr" })]),
      mk("div", { class: "akrm-sub", text: meta }),
      mk("div", { class: "akrm-stash" }, chips),
      l.produce ? mk("div", { class: "akrm-fence" }, [resIcon("produce", 12), mk("span", { text: "+" + l.produce + " produce -- fenced into the gold" })]) : null
    ]);
    var btn = mk("button", { class: "akrm-raid", type: "button", text: "RAID", onclick: function () { raid(row, l); } });
    return mk("div", { class: "akrm-card", style: "--cl:" + cl }, [crestFor(row), mid, btn]);
  }

  function render() {
    if (!bodyEl) return;
    var list = targets();
    barEl.textContent = list.length
      ? (list.length + " blocks on the grid  ·  you sit at " + myTrophies() + " tr")
      : "";
    if (!list.length) {
      setKids(bodyEl, [mk("div", { class: "akrm-note", text: "The streets are quiet -- no rival blocks on the grid yet. Climb the ranks and rivals will show." })]);
      return;
    }
    setKids(bodyEl, list.map(rowCard));
  }

  // ---- launch the raid (EXISTING path -- AKRaid/modes raid, NOT the lane) -----
  function raid(row, l) {
    l = l || lootFor(row);
    close();                                               // drop our overlay before the scout scene / page-nav
    var c = ctx();
    // gold here already folds the laundered produce; reward fields are exactly what
    // AK_MODES.raid.grantRaidLoot banks via AK_ECON on a win (materials/soft ONLY).
    var reward = { gold: l.gold, scrap: l.scrap, scrapR: l.scrapR, wood: l.wood, stone: l.stone };
    var opts = {
      id: "wm_loc_" + row.id,                              // local-prefix => client-side grant (not a server base)
      faction: row.clan, name: (row.name || "Rival") + "'s Block",
      tier: l.tier, trophies: row.trophies | 0, reward: reward
    };

    // PREFERRED: walk-on scout scene -> mode:'raid' battler (raidscene grabs AK_CTX)
    var RS = global.AK_RAIDSCENE;
    if (RS && typeof RS.launch === "function") {
      var target = (typeof RS.genTarget === "function") ? RS.genTarget(opts, c) : opts;
      try { if (target) target.id = opts.id; } catch (_) {}
      try { RS.launch(target, c); } catch (_e) { toast("Couldn't reach that block -- try the world map"); }
      return;
    }

    // FALLBACK (raidscene not loaded): seed the handoff + straight into the battler
    // (mirrors worldmap.raidFrom / raid.js launchRaid's legacy path).
    if (c && c.battle && typeof c.battle.launch === "function") {
      var tier = l.tier;
      var t2 = {
        id: opts.id, name: opts.name, faction: row.clan, cls: row.clanName || "Rival Crew",
        tier: tier, trophies: row.trophies | 0, reward: reward,
        roster: row.avatarCard ? [row.avatarCard] : [],
        city: clamp(tier + 1, 0, 9), level: clamp(2 + tier * 2, 1, 10), diffOffset: tier - 1
      };
      try {
        global.AK_RAID_TARGET = t2;
        if (typeof localStorage !== "undefined") localStorage.setItem("ak_raid_target", JSON.stringify(t2));
      } catch (_e2) {}
      // AK-RAIDLOOT 2026-06-30: scrap is a rarity-keyed OBJECT -- route through addScrap (the old
      // p.scrap = (p.scrap|0)+n corrupted the bag); mats through capped bankMaterial; star-scaled.
      t2.onResult = function (res) { try { var E = global.AK_ECON; if (!E) return;
        if (res && res.win && t2.reward) { var r = t2.reward, stars = (res && res.stars) | 0, mult = stars >= 3 ? 2.5 : stars >= 2 ? 1.5 : 1.0;
          var gm = (global.AK_ECON && AK_ECON.garageLootMult) ? AK_ECON.garageLootMult() : 1; mult = mult * gm;
          if (r.scrap && E.addScrap) E.addScrap(r.scrapR || 'Rare', Math.round((r.scrap | 0) * mult));
          if (r.wood && E.bankMaterial) E.bankMaterial('wood', Math.round((r.wood | 0) * mult));
          if (r.stone && E.bankMaterial) E.bankMaterial('stone', Math.round((r.stone | 0) * mult));
          if (r.metal && E.bankMaterial) E.bankMaterial('metal', Math.round((r.metal | 0) * mult));
          if (E.mutateProfile) E.mutateProfile(function (p) { if (r.gold) p.coins = (p.coins | 0) + Math.round((r.gold | 0) * mult); if (r.produce) p.produce = (p.produce | 0) + Math.round((r.produce | 0) * mult); });
        } else if (res && !res.win && typeof E.raidDamage === "function") { try { E.raidDamage(E.loadProfile ? E.loadProfile() : null, 1); } catch (_d) {} }
      } catch (_r) {} };
      try {
        // AK-HUBRAID 2026-06-30: raid INSIDE the hub renderer (walk their real district); arena is the fallback.
        if (typeof global.akEnterRaid === "function") { global.akEnterRaid(t2); return; }
        if (global.AK_MODES && typeof global.AK_MODES.openWorldMoba === "function") {
          global.AK_MODES.openWorldMoba(c, { enemyHero: (row.avatarCard || opts.name), raidTarget: t2, label: "RAID -- " + opts.name, onResult: t2.onResult });
        } else {
          c.battle.launch({ mode: "raid", city: t2.city, level: t2.level, diffOffset: t2.diffOffset, label: "RAID -- " + opts.name });
        }
      } catch (_e3) { toast("Raid path unavailable right now"); }
      return;
    }
    toast("Raid path unavailable -- open the world map to hit a block");
  }

  // ---- open / close ----------------------------------------------------------
  function open() {
    buildShell();
    render();
    root.classList.add("open");
  }
  function close() { if (root) root.classList.remove("open"); }

  // ---- EXPORT ----------------------------------------------------------------
  // exposes: window.akOpenRaidMap (the integration pass wires a HUD entry to this)
  try { global.akOpenRaidMap = open; } catch (_) {}
  try { global.AKRaidMap = { open: open, close: close }; } catch (_) {}

})(typeof window !== "undefined" ? window : globalThis);
