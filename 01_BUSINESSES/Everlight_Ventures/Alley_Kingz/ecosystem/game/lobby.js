/* ==========================================================================
   ALLEY KINGZ -- LOBBY REDESIGN (Clash/CoD bottom-tab + hero). Self-mounting.
   Restructures #startscreen into: top bar (brand+auth+currency) / hero carousel +
   Alley Pass strip / stage (big PLAY pillar) / persistent bottom TAB BAR, plus a
   compact icon row for secondary surfaces. Red-dot badges drive traffic.
   SAFE: it RE-PARENTS the existing buttons (keeps every id + listener) -- zero
   logic changes, pure layout/CSS. Fancy 3D CSS buttons now; Seedance art later.
   Include LAST (after drip.js). Spec: ecosystem/MENU_REDESIGN_SPEC.md
   ========================================================================== */
(function (global) {
  "use strict";
  var done = false;

  function $(id) { return document.getElementById(id); }
  function me() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function sbInvoke(fn, body) {
    try { var sb = global.AKAccount && global.AKAccount.client && global.AKAccount.client(); if (!sb) return Promise.resolve(null);
      return sb.functions.invoke(fn, { body: body }).then(function (r) { return r && r.data ? r.data : null; }, function () { return null; }); }
    catch (_) { return Promise.resolve(null); }
  }
  function gold() { try { var p = global.AK_ECON && global.AK_ECON.loadProfile(); return (p && p.coins) || 0; } catch (_) { return 0; } }
  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { var v = attrs[k]; if (v == null) return; if (k === "class") e.className = v; else if (k === "text") e.textContent = v; else if (k.slice(0, 2) === "on" && typeof v === "function") e[k] = v; else e.setAttribute(k, v); });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) { if (c == null || c === false) return; e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c); });
    return e;
  }

  function injectCss() {
    if ($("ak-lobby-css")) return;
    var st = document.createElement("style"); st.id = "ak-lobby-css";
    st.textContent = [
      // AK-PREMIUM: match everlightventures.io brand system -- Cinzel/Playfair luxury
      // serifs + Inter body, gold gradient #c9a84c->#e8c55a, glass-morphism, gold glow.
      "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');",
      // base props only -- NO display here, so the game's hide (.hidden / inline none) still works
      // AK-DOGHERO: the dog photo is the BIG full-bleed backdrop; everything sits in front.
      // Scrim keeps the top bar + tab bar + text legible while the dog shows through the middle.
      // AK-DOGHERO: Clash/CoD style -- the photo COVERS the whole screen to the bottom, UI floats on top.
      // Light scrim only at the very top (topbar) + bottom (tab bar) for legibility; clear in the middle so the dog shows.
      "#startscreen.ak-relayout{flex-direction:column;align-items:stretch;justify-content:flex-start;padding:0;margin:0;overflow:hidden;position:absolute;inset:0;width:100%;height:100%;font-family:'Inter',-apple-system,sans-serif;background:linear-gradient(180deg,rgba(8,8,12,.62) 0%,rgba(8,8,12,.10) 24%,rgba(8,8,12,.14) 60%,rgba(8,8,12,.86) 100%),#0a0a0e}",
      // show as flex ONLY when not hidden; when the match starts and .hidden is added, this stops applying -> lobby hides
      "#startscreen.ak-relayout:not(.hidden){display:flex}",
      "#startscreen.ak-relayout.hidden{display:none !important}",
      "#startscreen.ak-relayout .mode-grid{display:none !important}",
      "#startscreen.ak-relayout > #ak-topbar,#startscreen.ak-relayout > #ak-content{width:100%;box-sizing:border-box;flex-shrink:0}",
      "#startscreen.ak-relayout > #ak-content{flex:1 1 auto;min-height:0;position:relative;z-index:1}",
      // AK-VIDBG: the Seedance menu video as the wallpaper (poster = dog photo while it loads)
      "#ak-bgvid{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;background:#0a0a0e}",
      "#ak-bgscrim{position:absolute;inset:0;z-index:0;pointer-events:none;background:linear-gradient(180deg,rgba(8,8,12,.55) 0%,rgba(8,8,12,.10) 24%,rgba(8,8,12,.14) 60%,rgba(8,8,12,.86) 100%)}",
      // top bar (glass)
      "#ak-topbar{display:flex;align-items:center;gap:8px;padding:11px 13px;background:rgba(10,10,16,.55);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid rgba(201,168,76,.22);z-index:5}",
      "#ak-topbar .ak-brand{font-family:'Cinzel',serif;font-weight:900;letter-spacing:3px;font-size:15px;flex:0 0 auto;background:linear-gradient(135deg,#c9a84c,#e8c55a 50%,#c9a84c);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}",
      "#ak-topbar .ak-spacer{flex:1}",
      ".ak-cur{display:inline-flex;align-items:center;gap:4px;background:rgba(21,21,32,.7);backdrop-filter:blur(8px);border:1px solid rgba(201,168,76,.32);border-radius:9999px;padding:5px 11px;font-size:12px;font-weight:700;color:#E8E8E8;cursor:pointer}",
      // scroll content
      "#ak-content{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:8px 12px 96px;display:flex;flex-direction:column;gap:12px}",
      // AK-DOGHERO: gold title over the dog photo (Cinzel, gradient, drop-shadow for legibility)
      "#ak-title{text-align:center;padding:14px 12px 2px;flex-shrink:0}",
      "#ak-title .ak-h1{margin:0;font-family:'Cinzel',serif;font-size:34px;font-weight:900;letter-spacing:3px;line-height:1;background:linear-gradient(135deg,#e8c55a,#c9a84c 50%,#e8c55a);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 2px 10px rgba(0,0,0,.9))}",
      "#ak-title .ak-tag{margin:6px 0 0;font-family:'Playfair Display',serif;font-size:13px;font-style:italic;color:#E8E8E8;text-shadow:0 2px 8px rgba(0,0,0,.95)}",
      // AK-BRANDSWEEP: the Chop Shop premium vibe across EVERY panel -- Inter body + gold-gradient
      // Cinzel titles (fonts already @import'd above). Panels: social/pass/quests/drip + the shop.
      // AK-BRANDSWEEP2 2026-06-15: copy the Chop Shop's premium SHELL onto every panel --
      // layered rust/cyan glow bg + scanlines, a film-grain overlay, and a glass top bar.
      "#ak-social,#ak-pass,#ak-quests,#ak-drip{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:radial-gradient(1100px 540px at 18% -8%,rgba(192,97,46,.16),transparent 60%),radial-gradient(1000px 600px at 92% 0%,rgba(46,230,255,.06),transparent 55%),repeating-linear-gradient(0deg,rgba(255,255,255,.014) 0 1px,transparent 1px 3px),linear-gradient(180deg,#0c0d12 0%,#070708 70%)}",
      "#ak-social::before,#ak-pass::before,#ak-quests::before,#ak-drip::before{content:'';position:absolute;inset:0;pointer-events:none;z-index:0;opacity:.06;mix-blend-mode:overlay;background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")}",
      "#ak-social>*,#ak-pass>*,#ak-quests>*,#ak-drip>*{position:relative;z-index:1}",
      ".aks-top,.akp-top,.akq-top,.akd-top{background:linear-gradient(180deg,rgba(20,21,27,.92),rgba(10,11,14,.92));backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);box-shadow:0 1px 0 rgba(255,255,255,.04) inset,0 10px 30px rgba(0,0,0,.5)}",
      ".aks-top h2,.akp-top h2,.akq-top h2,.akd-top h2{font-family:'Cinzel',serif;letter-spacing:2px;background:linear-gradient(135deg,#D4AF37,#f3d77a 50%,#D4AF37);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}",
      ".aks-tab.on,.akd-tab.on{background:rgba(212,175,55,.16);border-color:rgba(212,175,55,.5)}",
      // hero carousel
      "#ak-hero{position:relative;border-radius:24px;overflow:hidden;min-height:128px;border:1px solid rgba(201,168,76,.3);box-shadow:0 0 30px rgba(201,168,76,.12),0 10px 26px rgba(0,0,0,.5)}",
      ".ak-slide{position:absolute;inset:0;display:none;flex-direction:column;justify-content:flex-end;padding:16px;color:#fff}",
      ".ak-slide.on{display:flex;animation:akfade .45s}",
      "@keyframes akfade{from{opacity:.15}to{opacity:1}}",
      ".ak-slide .tag{font-size:10px;letter-spacing:2px;color:#0a0a10;background:linear-gradient(135deg,#c9a84c,#e8c55a);align-self:flex-start;padding:3px 9px;border-radius:8px;font-weight:900}",
      ".ak-slide h3{margin:7px 0 2px;font-family:'Playfair Display',serif;font-size:20px;font-weight:700;text-shadow:0 2px 10px rgba(0,0,0,.8)}",
      ".ak-slide p{margin:0;font-size:12px;color:#dcdce4;text-shadow:0 1px 4px rgba(0,0,0,.8)}",
      "#ak-dots{position:absolute;top:8px;right:10px;display:flex;gap:5px}",
      "#ak-dots i{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.35)}#ak-dots i.on{background:#f0c14b}",
      // pass strip
      "#ak-passstrip{display:flex;align-items:center;gap:8px;background:rgba(21,21,32,.6);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border:1px solid rgba(201,168,76,.18);border-radius:14px;padding:9px 13px;cursor:pointer}",
      "#ak-passstrip .lab{font-size:11px;color:#c9a84c;font-weight:800;white-space:nowrap;letter-spacing:.5px}",
      "#ak-passstrip .bar{flex:1;height:8px;border-radius:5px;background:rgba(255,255,255,.1);overflow:hidden}",
      "#ak-passstrip .fill{height:100%;background:linear-gradient(90deg,#c9a84c,#e8c55a)}",
      "#ak-passstrip .nx{font-size:10px;color:#9a9aa6;white-space:nowrap}",
      // stage + PLAY pillar
      "#ak-stage{display:flex;align-items:center;justify-content:center;padding:14px 0}",
      "#ak-stage{display:flex;align-items:center;justify-content:center;padding:14px 0;width:100%;box-sizing:border-box}",
      "#startscreen.ak-relayout #playbtn{flex:0 0 auto;max-width:86%;font-family:'Cinzel',serif;font-size:22px;font-weight:900;letter-spacing:2px;color:#0a0a0e;border:0;border-radius:18px;padding:17px 40px;cursor:pointer;background:linear-gradient(135deg,#c9a84c,#e8c55a 50%,#c9a84c);box-shadow:0 0 20px rgba(201,168,76,.25),0 10px 26px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.6);animation:akpulse 2.6s ease-in-out infinite}",
      "#startscreen.ak-relayout #playbtn:active{transform:translateY(3px);box-shadow:0 0 14px rgba(201,168,76,.3),0 4px 10px rgba(0,0,0,.5)}",
      "@keyframes akpulse{0%,100%{box-shadow:0 0 20px rgba(201,168,76,.18),0 10px 26px rgba(0,0,0,.55)}50%{box-shadow:0 0 42px rgba(201,168,76,.4),0 10px 26px rgba(0,0,0,.55)}}",
      // icon row (secondary)
      "#ak-iconrow{display:flex;gap:10px;overflow-x:auto;padding:2px 0 4px;-webkit-overflow-scrolling:touch}",
      "#startscreen.ak-relayout #ak-iconrow .mode-tile{flex:0 0 auto;width:62px;min-height:0;height:auto;padding:8px 4px;border-radius:12px;background:rgba(20,20,28,.7);border:1px solid rgba(240,193,75,.2);display:flex;flex-direction:column;align-items:center;gap:3px;font-size:9px;color:#cfcfd6}",
      "#startscreen.ak-relayout #ak-iconrow .mt-sub{display:none}",
      "#startscreen.ak-relayout #ak-iconrow .mt-ico{font-size:20px}",
      // bottom tab bar
      "#ak-tabbar{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:flex-end;justify-content:space-around;background:rgba(8,8,12,.72);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-top:1px solid rgba(201,168,76,.26);padding:6px 6px 10px;z-index:6}",
      "#startscreen.ak-relayout #ak-tabbar .mode-tile{position:relative;flex:1;min-height:0;height:auto;background:none;border:0;border-radius:10px;padding:6px 2px;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:9.5px;letter-spacing:.3px;color:#b8b8c2}",
      "#startscreen.ak-relayout #ak-tabbar .mt-sub{display:none}",
      "#startscreen.ak-relayout #ak-tabbar .mt-ico{font-size:21px}",
      "#ak-tabbar .ak-playtab{flex:0 0 auto;width:76px;height:64px;margin:-22px 4px 0;border-radius:50%;border:3px solid #0a0a0e;background:url('assets/ui/play_btn.jpg') center/cover,linear-gradient(135deg,#c9a84c,#e8c55a 50%,#c9a84c);color:#0a0a0e;text-shadow:0 1px 2px rgba(255,255,255,.45);font-family:'Cinzel',serif;font-weight:900;font-size:11px;letter-spacing:1px;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 6px 16px rgba(0,0,0,.5),0 0 22px rgba(201,168,76,.45)}",
      "#ak-tabbar .ak-playtab span{font-size:22px;line-height:1}",
      ".ak-curico{width:17px;height:17px;border-radius:4px;object-fit:cover;margin-right:3px;vertical-align:middle;box-shadow:0 0 0 1px rgba(201,168,76,.4)}",
      ".ak-dot{position:absolute;top:0;right:8px;min-width:16px;height:16px;border-radius:9px;background:#e0413f;color:#fff;font-size:9px;font-weight:900;display:flex;align-items:center;justify-content:center;padding:0 4px;box-shadow:0 0 0 2px #0a0a10}",
    ].join("");
    document.head.appendChild(st);
  }

  function slide(tag, title, sub, bg, onTap) {
    var s = mk("div", { class: "ak-slide", style: "background:" + bg, onclick: onTap }, [
      mk("span", { class: "tag", text: tag }), mk("h3", { text: title }), mk("p", { text: sub }),
    ]);
    return s;
  }
  function tapBtn(id) { var b = $(id); if (b) b.click(); }

  function restructure() {
    if (done) return; var scr = $("startscreen"); if (!scr) return;
    done = true; injectCss(); scr.classList.add("ak-relayout");

    // top bar: brand + auth chip (moved) + currency
    var auth = $("ak-auth");
    var gems = mk("span", { class: "ak-cur", id: "ak-gems", onclick: function () { location.href = "shop/shop.html"; } }, [mk("img", { class: "ak-curico", src: "assets/ui/cur_gems.jpg", alt: "" }), mk("b", { id: "ak-gems-n", text: "--" })]);
    var goldc = mk("span", { class: "ak-cur", id: "ak-gold", onclick: function () { tapBtn("shopbtn"); } }, [mk("img", { class: "ak-curico", src: "assets/ui/cur_gold.jpg", alt: "" }), mk("b", { id: "ak-gold-n", text: String(gold()) })]);
    var topbar = mk("div", { id: "ak-topbar" }, [mk("span", { class: "ak-brand", text: "ALLEY KINGZ" }), mk("span", { class: "ak-spacer" }), auth || null, gems, goldc]);

    // AK-DOGHERO: the dog photo IS the hero (full-bleed backdrop) -> a light gold title
    // overlay sits on it instead of a carousel box, so the photo stays big + dominant.
    var hero = mk("div", { id: "ak-title" }, [
      mk("h1", { class: "ak-h1", text: "ALLEY KINGZ" }),
      mk("p", { class: "ak-tag", text: "Run the pack. Rule the streets." }),
    ]);

    // pass strip
    var passFill = mk("div", { class: "fill", style: "width:0%" });
    var passNx = mk("span", { class: "nx", text: "" });
    var passStrip = mk("div", { id: "ak-passstrip", onclick: function () { tapBtn("passbtn"); } }, [mk("span", { class: "lab", id: "ak-pass-lab", text: "ALLEY PASS" }), mk("div", { class: "bar" }, passFill), passNx]);

    // icon row: secondary surfaces (keep ids + listeners)
    var iconRow = mk("div", { id: "ak-iconrow" });
    ["deckbtn", "shopbtn", "mapbtn", "cratesbtn", "profilebtn", "akcodexbtn", "skillsbtn", "handlerbtn", "dc-claim"].forEach(function (id) { var b = $(id); if (b) { if (!b.classList.contains("mode-tile")) b.classList.add("mode-tile"); iconRow.appendChild(b); } });

    // stage: the big PLAY pillar (the real #playbtn, re-parented)
    var stage = mk("div", { id: "ak-stage" }); var playBtn = $("playbtn"); if (playBtn) stage.appendChild(playBtn);

    // content scroll region (everything between the bars)
    // AK-DOGHERO: title up top, then the dog photo breathes, then PLAY + controls sit lower
    // over the photo (Clash/CoD: art fills the screen, the big PLAY + nav float near the bottom).
    var spacer = mk("div", { style: "flex:1 1 auto;min-height:12px" });
    var content = mk("div", { id: "ak-content" }, [hero, spacer, stage, passStrip, iconRow]);
    try { var _nt = $("newsticker"); if (_nt) content.insertBefore(_nt, spacer); } catch (_e) {}   // AK-WIRE: re-parent the news ticker INTO content so the relayout hide-loop stops killing it

    // bottom tab bar: 4 surface tabs + raised center PLAY proxy
    var tabbar = mk("div", { id: "ak-tabbar" });
    var leftWrap = mk("div", { style: "display:flex;flex:1;justify-content:space-around" });
    var rightWrap = mk("div", { style: "display:flex;flex:1;justify-content:space-around" });
    ["dripbtn", "crewbtn"].forEach(function (id) { var b = $(id); if (b) leftWrap.appendChild(b); });
    ["passbtn", "questsbtn"].forEach(function (id) { var b = $(id); if (b) rightWrap.appendChild(b); });
    var playTab = mk("button", { class: "ak-playtab", type: "button", "aria-label": "Play", onclick: function () { try { window.AK && AK.sfx && AK.sfx("tap"); } catch (_e) {} tapBtn("playbtn"); } }, []);
    if (playBtn) playBtn.style.display = "none";   // AK-ART: hide the long generic "Play Now" bar. Reuse the ref captured at L147 -- it was re-parented OUT of the live DOM into `stage`, so $("playbtn") returns null here and the hide silently no-ops. Small custom badge proxies the click.
    tabbar.appendChild(leftWrap); tabbar.appendChild(playTab); tabbar.appendChild(rightWrap);

    // assemble: topbar, content, tabbar at the front of #startscreen (rest stays in flow, hidden grid)
    scr.insertBefore(topbar, scr.firstChild);
    scr.insertBefore(content, topbar.nextSibling);
    scr.appendChild(tabbar);
    // AK-MENUART: swap tile emoji for custom icon art (assets/ui/<file>.jpg) when it loads; emoji stays as fallback.
    try {
      var MENU_ICONS = { deckbtn:"Deck", shopbtn:"Shop", mapbtn:"Map", cratesbtn:"Crates", passbtn:"Pass", profilebtn:"Profile", akcodexbtn:"Codex", skillsbtn:"Street", handlerbtn:"Handlers", dripbtn:"Drip", crewbtn:"Crew", questsbtn:"HitList" };
      Object.keys(MENU_ICONS).forEach(function (mid) {
        var b = $(mid); if (!b) return; var ico = b.querySelector(".mt-ico,.sb-ico"); if (!ico) return;
        var src = "assets/ui/" + MENU_ICONS[mid] + ".jpg", pre = new Image();
        pre.onload = function () { ico.style.backgroundImage = "url('" + src + "')"; ico.classList.add("ak-tileart"); };
        pre.src = src;
      });
    } catch (_e) {}

    // AK-RELAYOUT: hide leftover ORIGINAL lobby sections (replaced by the new layout)
    // so only [topbar, content, tabbar] show. Leave modals/overlays + already-hidden alone.
    Array.prototype.slice.call(scr.children).forEach(function (c) {
      if (c.id === "ak-topbar" || c.id === "ak-content" || c.id === "ak-tabbar") return;
      if (/drawer|overlay|modal|screen/i.test(c.id || "")) return;
      if (c.classList && c.classList.contains("hidden")) return;
      c.style.display = "none";
    });

    // AK-VIDBG 2026-06-15: the Seedance menu video as the wallpaper, layered BEHIND the UI.
    // muted + loop + playsinline = mobile autoplay; poster = the dog photo while it buffers.
    var bgvid = mk("video", { id: "ak-bgvid", autoplay: "", loop: "", playsinline: "", "webkit-playsinline": "", preload: "auto", poster: "assets/ui/lobby_hero.png" }, mk("source", { src: "assets/ui/menu_bg.mp4", type: "video/mp4" }));   // AK-FIX: poster = instant hero so the lobby never shows a black void while the video decodes (the gate already preloads lobby_hero.png)
    bgvid.muted = true; bgvid.defaultMuted = true;
    scr.appendChild(bgvid);
    scr.appendChild(mk("div", { id: "ak-bgscrim" }));
    try { var _pr = bgvid.play(); if (_pr && _pr.catch) _pr.catch(function () {}); } catch (_) {}

    // first paint of currency + badges, and refresh on auth
    refresh();
    try { global.addEventListener("ak-auth", refresh); } catch (_) {}
    setInterval(function () { var g = $("ak-gold-n"); if (g) g.textContent = String(gold()); }, 4000);
    global.AKLobby = { refresh: refresh };
    try{ global.AKPreload && global.AKPreload.bootReady(); }catch(_e){}   // AK-PRELOAD: lobby assembled -> let the gate reveal
  }

  function badge(id, n) {
    var b = $(id); if (!b) return;
    var old = b.querySelector(".ak-dot"); if (old) old.remove();
    if (n > 0) b.appendChild(mk("span", { class: "ak-dot", text: n > 9 ? "9+" : String(n) }));
  }

  function refresh() {
    var g = $("ak-gold-n"); if (g) g.textContent = String(gold());
    if (!me()) { var gm = $("ak-gems-n"); if (gm) gm.textContent = "0"; var pl = $("ak-pass-lab"); if (pl) pl.textContent = "ALLEY PASS -- sign in"; return; }
    // currency (gems) + drip dot
    sbInvoke("ak-cosmetics", { action: "get" }).then(function (d) { var gm = $("ak-gems-n"); if (gm && d) gm.textContent = String(d.gems != null ? d.gems : 0); });
    // pass strip + pass dot
    sbInvoke("ak-pass", { action: "get" }).then(function (d) {
      if (!d) return;
      var into = (d.xp || 0) - (d.tier || 0) * (d.xp_per_tier || 100);
      var pct = d.tier >= d.max_tier ? 100 : Math.max(0, Math.min(100, Math.round(into / (d.xp_per_tier || 100) * 100)));
      var fill = document.querySelector("#ak-passstrip .fill"); if (fill) fill.style.width = pct + "%";
      var lab = $("ak-pass-lab"); if (lab) lab.textContent = "PASS  T" + (d.tier || 0);
      var nx = document.querySelector("#ak-passstrip .nx"); if (nx) nx.textContent = d.tier >= d.max_tier ? "MAX" : (into + "/" + (d.xp_per_tier || 100));
      var claimable = 0; var cf = d.claimed_free || []; for (var t = 1; t <= (d.tier || 0); t++) if (cf.indexOf(t) < 0) claimable++;
      badge("passbtn", claimable);
    });
    // hit list dot
    sbInvoke("ak-quests", { action: "get" }).then(function (d) { if (!d || !d.quests) return; badge("questsbtn", d.quests.filter(function (q) { return q.claimable; }).length); });
    // crew dot: fillable donation requests (not mine)
    sbInvoke("ak-crew", { action: "don-list" }).then(function (d) { if (!d || !d.requests) return; var uid = me() && me().id; badge("crewbtn", d.requests.filter(function (r) { return r.user_id !== uid; }).length); });
  }

  function boot() { try { restructure(); } catch (e) { try { console.warn("[lobby] relayout failed:", e && e.message); } catch (_) {} } }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})(typeof window !== "undefined" ? window : this);
