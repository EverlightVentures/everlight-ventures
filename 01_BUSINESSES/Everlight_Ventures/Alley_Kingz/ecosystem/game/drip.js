/* ==========================================================================
   ALLEY KINGZ -- THE DROP + DRIP (cosmetics). Self-mounting (like pass.js).
   Cosmetic types:
     - style_*  CARD SKINS  -> CSS-filter recolor on card art in-match (drawUnit
                 AK-DRIP hook). Equip GLOBALLY (squad) or PER-CARD.
     - board_*  ARENA THEMES -> CSS-filter on the match backdrop (AK-BOARD hook).
     - emote_*  BATTLE EMOTES -> tap in-match to pop a bubble (DOM, no engine edit).
   Ownership server-side (ak-cosmetics); equipping is a local pref. Buying deducts
   Gold client-side (cosmetic, no pay-to-win). mk() builder, no innerHTML.
   Include AFTER quests.js. Exposes window.AKDrip {cardFilter, boardFilter, ...}.
   ========================================================================== */
(function (global) {
  "use strict";

  var CATALOG = {
    // ---- card skins (CSS filter on the art) ----
    style_gilded:  { type: "style", name: "Gilded",    rarity: "Epic",   price: 800, css: "sepia(0.7) saturate(2.2) hue-rotate(-12deg) brightness(1.08) contrast(1.05)", sw: "linear-gradient(135deg,#f7e08a,#cf9b22)" },
    style_neon:    { type: "style", name: "Neon Noir", rarity: "Rare",   price: 600, css: "contrast(1.25) saturate(1.7) hue-rotate(200deg) brightness(1.1)",            sw: "linear-gradient(135deg,#5ee7ff,#8a5cff)" },
    style_toxic:   { type: "style", name: "Toxic",     rarity: "Rare",   price: 600, css: "hue-rotate(75deg) saturate(2) brightness(1.05)",                              sw: "linear-gradient(135deg,#aaff66,#33aa33)" },
    style_shadow:  { type: "style", name: "Shadow",    rarity: "Rare",   price: 500, css: "grayscale(0.55) brightness(0.72) contrast(1.45)",                             sw: "linear-gradient(135deg,#6b6b78,#15151c)" },
    style_frost:   { type: "style", name: "Frostbite", rarity: "Epic",   price: 700, css: "hue-rotate(165deg) saturate(1.4) brightness(1.18)",                          sw: "linear-gradient(135deg,#bfefff,#4aa3df)" },
    style_inferno: { type: "style", name: "Inferno",   rarity: "Mythic", price: 900, css: "sepia(0.55) saturate(3) hue-rotate(-25deg) brightness(1.12)",                sw: "linear-gradient(135deg,#ffb24a,#d4341a)" },
    // ---- arena boards (CSS filter on the backdrop) ----
    board_noir:      { type: "board", name: "Noir Alley",  rarity: "Rare", price: 400, css: "grayscale(1) contrast(1.15)",                              sw: "linear-gradient(135deg,#cfcfd6,#2b2b30)" },
    board_vapor:     { type: "board", name: "Vaporwave",   rarity: "Epic", price: 500, css: "saturate(1.7) hue-rotate(-35deg) contrast(1.05)",          sw: "linear-gradient(135deg,#ff8ad8,#7a5cff)" },
    board_bloodmoon: { type: "board", name: "Blood Moon",  rarity: "Epic", price: 600, css: "sepia(0.45) saturate(2) hue-rotate(-18deg) brightness(0.88)", sw: "linear-gradient(135deg,#ff6a5e,#5a1414)" },
    // ---- battle emotes ----
    emote_woof:  { type: "emote", name: "Woof",      rarity: "Common", price: 200, emoji: "🐕", text: "WOOF!" },
    emote_crown: { type: "emote", name: "All Hail",  rarity: "Rare",   price: 300, emoji: "👑", text: "ALL HAIL" },
    emote_gg:    { type: "emote", name: "Good Game", rarity: "Common", price: 200, emoji: "🤝", text: "GG" },
    emote_skull: { type: "emote", name: "Get Got",   rarity: "Rare",   price: 250, emoji: "💀", text: "GET GOT" },
  };
  var RAR_COL = { Common: "#cfcfd6", Rare: "#5aa9ff", Epic: "#c06bff", Mythic: "#ff5e8a" };

  var D = { booted: false, owned: {}, rotation: [], prices: {}, resets: 0, tab: "shop",
            styleAll: null, board: null, skins: {}, emotes: [] };

  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function gold() { try { var p = econ() && econ().loadProfile(); return (p && p.coins) || 0; } catch (_) { return 0; } }
  function myCards() { try { var p = econ() && econ().loadProfile(); return ((p && p.owned) || []).slice().sort(); } catch (_) { return []; } }
  function lsGet(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (_) {} }

  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { var v = attrs[k]; if (v == null) return; if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.slice(0, 2) === "on" && typeof v === "function") e[k] = v; else e.setAttribute(k, v); });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) { if (c == null || c === false) return; e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c); });
    return e;
  }
  function setKids(el, nodes) { el.replaceChildren.apply(el, [].concat(nodes).filter(function (n) { return n != null; })); }
  function call(fn, body) {
    var sb = sbc(); if (!sb) return Promise.resolve({ ok: false, error: "offline" });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) { var c = r.error.context; if (c && typeof c.json === "function") return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; }); return { ok: false, error: r.error.message || "error" }; }
      return r.data || { ok: false, error: "empty" };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }

  // ---- equip state + engine-facing resolvers (fast, sync, no async) ---------
  function loadEquip() {
    D.styleAll = lsGet("ak_style_all");
    D.board = lsGet("ak_board");
    try { D.owned = JSON.parse(lsGet("ak_cos_owned") || "{}") || {}; } catch (_) { D.owned = {}; }
    try { D.skins = JSON.parse(lsGet("ak_skins") || "{}") || {}; } catch (_) { D.skins = {}; }
    try { D.emotes = JSON.parse(lsGet("ak_emotes") || "[]") || []; } catch (_) { D.emotes = []; }
  }
  function ownsId(id) { return !!D.owned[id]; }
  function cardFilter(card) {                       // engine drawUnit hook
    var nm = card && card.name;
    var per = nm && D.skins[nm];
    if (per && D.owned[per] && CATALOG[per]) return CATALOG[per].css;
    if (D.styleAll && D.owned[D.styleAll] && CATALOG[D.styleAll]) return CATALOG[D.styleAll].css;
    return null;
  }
  function boardFilter() {                          // engine backdrop hook
    if (D.board && D.owned[D.board] && CATALOG[D.board]) return CATALOG[D.board].css;
    return null;
  }
  function equippedEmotes() {
    return D.emotes.filter(function (id) { return D.owned[id] && CATALOG[id]; }).map(function (id) { return { id: id, emoji: CATALOG[id].emoji, text: CATALOG[id].text }; });
  }

  function injectCss() {
    if (document.getElementById("ak-drip-css")) return;
    var st = document.createElement("style"); st.id = "ak-drip-css";
    st.textContent = [
      "#ak-drip{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-drip.open{display:flex}",
      ".akd-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,0.18)}",
      ".akd-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#c9a84c;flex:1}",
      ".akd-gold{font-size:12px;color:#c9a84c;font-weight:800}",
      ".akd-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".akd-tabs{display:flex;gap:6px;padding:8px 12px}",
      ".akd-tab{flex:1;padding:9px;border-radius:9px;border:1px solid rgba(201,168,76,0.22);background:rgba(255,255,255,0.03);color:#cfcfd6;font-weight:700;font-size:12px;cursor:pointer}",
      ".akd-tab.on{background:rgba(201,168,76,0.16);color:#c9a84c;border-color:rgba(201,168,76,0.5)}",
      ".akd-count{font-size:11px;color:#9a9aa6;padding:0 14px 6px}",
      ".akd-body{flex:1;overflow-y:auto;padding:6px 12px}",
      ".akd-sec{font-size:11px;letter-spacing:1px;color:#8a8a96;margin:10px 2px 4px;font-weight:800}",
      ".akd-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}",
      ".akd-item{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:6px}",
      ".akd-sw{height:58px;border-radius:9px;border:1px solid rgba(255,255,255,0.12);display:flex;align-items:center;justify-content:center;font-size:30px}",
      ".akd-nm{font-weight:800;color:#fff;font-size:13px}.akd-rar{font-size:10px;letter-spacing:1px;font-weight:800}",
      ".akd-btn{background:linear-gradient(180deg,#c9a84c,#cf9b22);color:#1a1405;border:0;border-radius:8px;padding:8px;font-weight:800;font-size:12px;cursor:pointer}",
      ".akd-btn[disabled]{opacity:.45}.akd-btn.own{background:rgba(255,255,255,0.06);color:#9a9aa6;border:1px solid rgba(255,255,255,0.14)}",
      ".akd-btn.on{background:rgba(95,211,95,0.16);color:#5fd35f;border:1px solid rgba(95,211,95,0.45)}",
      ".akd-sel{width:100%;box-sizing:border-box;background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.14);color:#fff;border-radius:8px;padding:8px;margin:4px 0;font-size:13px}",
      ".akd-assign{display:flex;gap:6px;align-items:center;font-size:12px;color:#cfcfd6;padding:6px 2px;border-bottom:1px solid rgba(255,255,255,0.05)}",
      ".akd-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px}",
      ".akd-toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:#1a1a22;color:#c9a84c;border:1px solid rgba(201,168,76,0.4);padding:9px 16px;border-radius:20px;z-index:71;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".akd-toast.show{opacity:1}",
      // in-match emote button + bubble
      "#ak-emote-btn{position:fixed;right:12px;bottom:120px;z-index:55;width:46px;height:46px;border-radius:50%;border:1px solid rgba(201,168,76,0.5);background:rgba(20,20,28,0.85);color:#c9a84c;font-size:22px;display:none;cursor:pointer}",
      "#ak-emote-btn.show{display:block}",
      "#ak-emote-wheel{position:fixed;right:12px;bottom:172px;z-index:56;display:none;flex-direction:column;gap:6px}",
      "#ak-emote-wheel.show{display:flex}",
      ".ak-emo-opt{background:rgba(20,20,28,0.95);border:1px solid rgba(201,168,76,0.4);color:#fff;border-radius:18px;padding:6px 12px;font-size:14px;cursor:pointer;white-space:nowrap}",
      "#ak-emote-bubble{position:fixed;left:50%;bottom:200px;transform:translateX(-50%) scale(0.6);z-index:57;background:#fff;color:#15151c;font-weight:800;padding:10px 16px;border-radius:16px;font-size:18px;opacity:0;transition:opacity .15s,transform .15s;pointer-events:none}",
      "#ak-emote-bubble.show{opacity:1;transform:translateX(-50%) scale(1)}",
      ".akd-emoart{object-fit:cover}",
      ".ak-emo-opt{display:flex;align-items:center;gap:4px}",
      ".ak-emo-ico{width:24px;height:24px;border-radius:6px;object-fit:cover;flex:0 0 auto}",
    ].join("");
    document.head.appendChild(st);
  }

  var root, goldEl, tabsEl, countEl, bodyEl, toastEl;
  function buildShell() {
    if (root) return; injectCss();
    goldEl = mk("span", { class: "akd-gold", text: "" });
    var x = mk("button", { class: "akd-x", type: "button", text: "×", onclick: close });
    var top = mk("div", { class: "akd-top" }, [mk("h2", { text: "THE DROP" }), goldEl, x]);
    var tShop = mk("button", { class: "akd-tab on", text: "THE DROP", onclick: function () { setTab("shop"); } });
    var tLock = mk("button", { class: "akd-tab", text: "LOCKER", onclick: function () { setTab("locker"); } });
    tabsEl = mk("div", { class: "akd-tabs" }, [tShop, tLock]);
    countEl = mk("div", { class: "akd-count" });
    bodyEl = mk("div", { class: "akd-body" });
    root = mk("section", { id: "ak-drip" }, [top, tabsEl, countEl, bodyEl]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "akd-toast" }); document.body.appendChild(toastEl);
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }
  function setTab(t) { D.tab = t; Array.prototype.forEach.call(tabsEl.children, function (b, i) { b.classList.toggle("on", (t === "shop") === (i === 0)); }); if (t === "shop") renderShop(); else renderLocker(); }
  function open() { buildShell(); root.classList.add("open"); refreshGold(); setTab("shop"); load(); }
  function close() { if (root) root.classList.remove("open"); }
  function refreshGold() { if (goldEl) goldEl.textContent = "💰 " + gold(); }

  function load() {
    loadEquip();
    if (!me()) { setKids(bodyEl, [mk("div", { class: "akd-note", text: "Sign in to shop The Drop and equip skins, boards and emotes." }), mk("button", { class: "akd-btn", style: "display:block;margin:8px auto;max-width:240px", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } })]); countEl.textContent = ""; return; }
    call("ak-cosmetics", { action: "get" }).then(function (r) {
      if (r && r.ok) {
        D.owned = {}; (r.owned || []).forEach(function (id) { D.owned[id] = 1; });
        lsSet("ak_cos_owned", JSON.stringify(D.owned));
        D.rotation = r.rotation || []; D.prices = r.prices || {}; D.resets = r.resets_in || 0;
      }
      if (D.tab === "shop") renderShop(); else renderLocker();
    });
  }
  function fmtCountdown(s) { var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return "The Drop resets in " + h + "h " + m + "m"; }

  // AK-ART: custom emote art (assets/ui/emote_<id>.jpg) with emoji fallback
  function emoteArt(id, emoji, cls) {
    var img = mk("img", { class: (cls || "") + " akd-emoart", src: "assets/ui/" + id + ".jpg", alt: "" });
    img.onerror = function () { var d = mk("div", { class: cls || "", text: emoji }); if (img.parentNode) img.parentNode.replaceChild(d, img); };
    return img;
  }
  function itemChip(id, btn) {
    var c = CATALOG[id]; if (!c) return null;
    var sw = c.type === "emote"
      ? emoteArt(id, c.emoji, "akd-sw")
      : mk("div", { class: "akd-sw", style: "background:" + c.sw });
    return mk("div", { class: "akd-item" }, [sw, mk("div", { class: "akd-nm", text: c.name }), mk("div", { class: "akd-rar", style: "color:" + (RAR_COL[c.rarity] || "#ccc"), text: (c.type.toUpperCase() + " • " + c.rarity.toUpperCase()) }), btn]);
  }

  function renderShop() {
    if (!me()) return;
    countEl.textContent = D.resets ? fmtCountdown(D.resets) : "";
    if (!D.rotation.length) { setKids(bodyEl, mk("div", { class: "akd-note", text: "Loading the Drop..." })); return; }
    var items = D.rotation.map(function (id) {
      var c = CATALOG[id]; if (!c) return null;
      var btn;
      if (ownsId(id)) btn = mk("button", { class: "akd-btn own", disabled: "1", text: "Owned" });
      else { btn = mk("button", { class: "akd-btn", text: "💰 " + (D.prices[id] || c.price) }); btn.onclick = function () { buy(id, btn); }; }
      return itemChip(id, btn);
    }).filter(Boolean);
    setKids(bodyEl, mk("div", { class: "akd-grid" }, items));
  }
  function buy(id, btn) {
    var price = D.prices[id] || (CATALOG[id] && CATALOG[id].price) || 0;
    if (gold() < price) { toast("Not enough gold (need " + price + ")"); return; }
    btn.disabled = true;
    call("ak-cosmetics", { action: "buy", id: id }).then(function (r) {
      if (!r || !r.ok) { toast(r && r.error ? r.error : "could not buy"); btn.disabled = false; return; }
      try { econ().mutateProfile(function (p) { p.coins = Math.max(0, (p.coins || 0) - price); }); } catch (_) {}
      try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
      D.owned[id] = 1; lsSet("ak_cos_owned", JSON.stringify(D.owned));
      toast("Unlocked " + (CATALOG[id] ? CATALOG[id].name : id) + "!");
      refreshGold(); renderShop();
    });
  }

  // ---- LOCKER: skins (all + per-card), boards, emotes -----------------------
  function ownedOfType(t) { return Object.keys(D.owned).filter(function (id) { return CATALOG[id] && CATALOG[id].type === t; }); }
  function renderLocker() {
    if (!me()) return;
    countEl.textContent = "Equip your drip -- it shows on the battlefield.";
    var nodes = [];
    // SKINS
    nodes.push(mk("div", { class: "akd-sec", text: "CARD SKINS" }));
    var skins = ownedOfType("style");
    if (!skins.length) nodes.push(mk("div", { class: "akd-note", text: "No skins yet -- grab one from The Drop." }));
    else {
      nodes.push(mk("div", { class: "akd-grid" }, skins.map(function (id) {
        var active = D.styleAll === id;
        var btn = mk("button", { class: "akd-btn" + (active ? " on" : ""), text: active ? "✓ Squad" : "Wear (squad)" });
        btn.onclick = function () { equipAll(active ? null : id); };
        return itemChip(id, btn);
      })));
      // per-card assignment
      var cards = myCards();
      if (cards.length) {
        var cardSel = mk("select", { class: "akd-sel" }, cards.map(function (n) { return mk("option", { value: n, text: n }); }));
        var styleSel = mk("select", { class: "akd-sel" }, skins.map(function (id) { return mk("option", { value: id, text: CATALOG[id].name }); }));
        var go = mk("button", { class: "akd-btn", text: "Equip to this card", onclick: function () { var cn = cardSel.value, sid = styleSel.value; if (!cn || !sid) return; D.skins[cn] = sid; lsSet("ak_skins", JSON.stringify(D.skins)); toast(CATALOG[sid].name + " on " + cn); renderLocker(); } });
        nodes.push(mk("div", { class: "akd-sec", text: "PER-CARD (overrides squad)" }));
        nodes.push(cardSel); nodes.push(styleSel); nodes.push(go);
        var assigned = Object.keys(D.skins).filter(function (cn) { return D.skins[cn] && CATALOG[D.skins[cn]] && D.owned[D.skins[cn]]; });
        assigned.forEach(function (cn) {
          nodes.push(mk("div", { class: "akd-assign" }, [
            mk("span", { style: "flex:1", text: cn + " -> " + CATALOG[D.skins[cn]].name }),
            mk("button", { class: "akd-btn own", style: "padding:4px 10px", text: "clear", onclick: function () { delete D.skins[cn]; lsSet("ak_skins", JSON.stringify(D.skins)); renderLocker(); } }),
          ]));
        });
      }
    }
    // BOARDS
    nodes.push(mk("div", { class: "akd-sec", text: "ARENA BOARDS" }));
    var boards = ownedOfType("board");
    if (!boards.length) nodes.push(mk("div", { class: "akd-note", text: "No boards yet." }));
    else nodes.push(mk("div", { class: "akd-grid" }, boards.map(function (id) {
      var active = D.board === id;
      var btn = mk("button", { class: "akd-btn" + (active ? " on" : ""), text: active ? "✓ Active" : "Use" });
      btn.onclick = function () { equipBoard(active ? null : id); };
      return itemChip(id, btn);
    })));
    // EMOTES
    nodes.push(mk("div", { class: "akd-sec", text: "BATTLE EMOTES (tap to equip up to 4)" }));
    var emotes = ownedOfType("emote");
    if (!emotes.length) nodes.push(mk("div", { class: "akd-note", text: "No emotes yet." }));
    else nodes.push(mk("div", { class: "akd-grid" }, emotes.map(function (id) {
      var on = D.emotes.indexOf(id) >= 0;
      var btn = mk("button", { class: "akd-btn" + (on ? " on" : ""), text: on ? "✓ Equipped" : "Equip" });
      btn.onclick = function () { toggleEmote(id); };
      return itemChip(id, btn);
    })));
    setKids(bodyEl, nodes);
  }
  function equipAll(id) { D.styleAll = id || null; if (id) lsSet("ak_style_all", id); else lsDel("ak_style_all"); toast(id ? "Squad skin equipped" : "Squad skin removed"); renderLocker(); }
  function equipBoard(id) { D.board = id || null; if (id) lsSet("ak_board", id); else lsDel("ak_board"); toast(id ? "Board equipped" : "Board removed"); renderLocker(); }
  function toggleEmote(id) {
    var i = D.emotes.indexOf(id);
    if (i >= 0) D.emotes.splice(i, 1);
    else { if (D.emotes.length >= 4) { toast("Emote slots full (4)"); return; } D.emotes.push(id); }
    lsSet("ak_emotes", JSON.stringify(D.emotes)); renderLocker(); buildEmoteWheel();
  }

  // ---- in-match emote button + bubble (DOM; no engine edit) -----------------
  var emoBtn, emoWheel, emoBubble;
  function ensureEmoteUi() {
    if (emoBtn) return; injectCss();
    emoBtn = mk("button", { id: "ak-emote-btn", type: "button", text: "😀", onclick: function (e) { e.stopPropagation(); emoWheel.classList.toggle("show"); } });
    emoWheel = mk("div", { id: "ak-emote-wheel" });
    emoBubble = mk("div", { id: "ak-emote-bubble" });
    document.body.appendChild(emoBtn); document.body.appendChild(emoWheel); document.body.appendChild(emoBubble);
    document.addEventListener("click", function (e) { if (emoWheel && !emoWheel.contains(e.target) && e.target !== emoBtn) emoWheel.classList.remove("show"); });
  }
  function buildEmoteWheel() {
    if (!emoWheel) return;
    var list = equippedEmotes();
    setKids(emoWheel, list.map(function (e) { return mk("button", { class: "ak-emo-opt", onclick: function (ev) { ev.stopPropagation(); playEmote(e); emoWheel.classList.remove("show"); } }, [emoteArt(e.id, e.emoji, "ak-emo-ico"), mk("span", { text: " " + e.text })]); }));
  }
  function playEmote(e) { if (!emoBubble) return; emoBubble.textContent = e.emoji + " " + e.text; emoBubble.classList.add("show"); clearTimeout(playEmote._t); playEmote._t = setTimeout(function () { emoBubble.classList.remove("show"); }, 2500); }
  function inMatch() { try { return !!(global.AK && global.AK.game && global.AK.game.units); } catch (_) { return false; } }
  function emoteTick() {
    if (!me()) { if (emoBtn) emoBtn.classList.remove("show"); return; }
    var have = equippedEmotes().length > 0;
    if (have && inMatch()) { ensureEmoteUi(); if (!emoWheel.childNodes.length) buildEmoteWheel(); emoBtn.classList.add("show"); }
    else if (emoBtn) { emoBtn.classList.remove("show"); emoWheel && emoWheel.classList.remove("show"); }
  }

  function wire() {
    if (D.booted) return; D.booted = true;
    loadEquip();                       // so cardFilter/boardFilter work in-match before the panel opens
    var btn = document.getElementById("dripbtn");
    if (btn) btn.addEventListener("click", open);
    try { global.addEventListener("ak-auth", function (e) { if (e && e.detail && e.detail.user) load(); }); } catch (_) {}
    setInterval(emoteTick, 900);       // show the emote button only during a live match
    global.AKDrip = { open: open, close: close, cardFilter: cardFilter, boardFilter: boardFilter, equippedEmotes: equippedEmotes };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})(typeof window !== "undefined" ? window : this);
