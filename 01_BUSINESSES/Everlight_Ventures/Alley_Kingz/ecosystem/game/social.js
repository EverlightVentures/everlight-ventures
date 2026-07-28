/* ==========================================================================
   ALLEY KINGZ -- SOCIAL LAYER (Phase 1): CREWS + WORLD/CREW CHAT
   Self-mounting vanilla-JS module (mirrors ak_account.js's self-mount style).
   - Crews (clans): browse / create / join / leave / roster, all via the
     server-authoritative `ak-crew` edge function (the client never writes the DB).
   - Chat: world + crew. SEND goes through `ak-chat` (rate-limit + profanity +
     ban-check server-side); RECEIVE is Supabase Realtime postgres_changes on
     ak_chat_messages (RLS scopes crew rows to members), seeded with last-50 history.
   - Uses the ONE shared Supabase client from AKAccount.client(); functions.invoke
     auto-attaches the signed-in user's JWT. Degrades gracefully when signed out.
   XSS-safe by construction: the mk() builder puts every dynamic value through
   textContent -- there is no innerHTML anywhere. No em-dashes (use --). No bundler.
   Include AFTER ak_account.js.
   ========================================================================== */
(function (global) {
  "use strict";

  var FACTIONS = [
    { id: "boneguard_crew", name: "Boneguard Crew" },
    { id: "zoomie_syndicate", name: "Zoomie Syndicate" },
    { id: "leashbreak_tactix", name: "Leashbreak Tactix" },
    { id: "k9_circuitry", name: "K9 Circuitry" },
  ];
  var FNAME = {}; FACTIONS.forEach(function (f) { FNAME[f.id] = f.name; });
  // AK-CHAT-RESKIN: per-crew accent colour drives each bubble's --crew var.
  function facColor(fac) { return ({ boneguard_crew: "#e8d8a0", zoomie_syndicate: "#5fd3ff", leashbreak_tactix: "#ff8a5f", k9_circuitry: "#9d8bff" })[fac] || "#c9a84c"; }
  // AK-CREST 2026-06-30: the real faction CREST as art (assets/ui/Crest_*.jpg) instead of a
  // generic emoji -- raises the clan menu to the chop-shop bar. Same dir for index.html + game.html.
  function facCrest(fac) { return ({ boneguard_crew: "assets/ui/Crest_Boneguard.jpg", zoomie_syndicate: "assets/ui/Crest_Zoomie.jpg", leashbreak_tactix: "assets/ui/Crest_Leashbreak.jpg", k9_circuitry: "assets/ui/Crest_K9.jpg" })[fac] || ""; }
  // a crest tile painted with the faction art (paw-glyph fallback if the image is missing),
  // ringed + glowing in the faction colour. Built via mk() -- no innerHTML.
  function crestEl(fac) {
    var col = facColor(fac);
    var d = mk("div", { class: "aks-crest", style: "border-color:" + col + "99;box-shadow:0 0 9px " + col + "44" });
    var src = facCrest(fac);
    if (src) {
      var img = mk("img", { src: src, alt: "", style: "width:100%;height:100%;border-radius:8px;object-fit:cover;object-position:center", onerror: function () { try { d.removeChild(img); d.textContent = "🐾"; } catch (_) {} } });
      d.appendChild(img);
    } else { d.textContent = "🐾"; }
    return d;
  }

  var S = { crew: null, role: null, members: [], scope: "world",
            msgs: { world: [], crew: [] }, chans: {}, presence: { world: 0, crew: 0 }, booted: false, tab: "crew" };

  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function myId() { var u = me(); return (u && u.id) || null; }
  function myName() { try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24); } catch (_) { return "Stray"; } }
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function myOwned() { try { var e = econ(); var p = e && e.loadProfile(); return (p && p.owned) || []; } catch (_) { return []; } }

  // ---- grants inbox: apply server-queued grants to the local economy ---------
  function applyGrant(g) {
    var e = econ(); if (!e) return false;
    try {
      if (g.kind === "card" && g.card_id) e.addCopy(g.card_id, g.amount || 1);
      else if (g.kind === "gold") e.mutateProfile(function (p) { p.coins = (p.coins || 0) + (g.amount || 0); });
      else if (g.kind === "scrap" && g.rarity) e.addScrap(g.rarity, g.amount || 0);
      else if (g.kind === "chest") e.grantChest(g.card_id || "wood", g.amount || 1);
      else if (g.kind === "keys") e.addKeys(g.amount || 0);
      else return false;
      return true;
    } catch (_) { return false; }
  }
  function claimGrants() {
    if (!me() || !econ()) return;
    call("ak-crew", { action: "claim-grants" }).then(function (r) {
      if (!r || !r.ok || !r.grants || !r.grants.length) return;
      var cards = 0, gold = 0, n = 0;
      r.grants.forEach(function (g) { if (applyGrant(g)) { n++; if (g.kind === "card") cards += g.amount || 0; if (g.kind === "gold") gold += g.amount || 0; } });
      if (!n) return;
      try { if (global.AKAccount && global.AKAccount.pushNow) global.AKAccount.pushNow(); } catch (_) {}
      var bits = []; if (cards) bits.push(cards + " card" + (cards > 1 ? "s" : "")); if (gold) bits.push(gold + " gold");
      toast("Claimed " + (bits.join(" + ") || (n + " reward" + (n > 1 ? "s" : ""))));
    });
  }

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

  // ---- server call helper (edge fn via supabase functions.invoke) ------------
  function call(fn, body) {
    var sb = sbc();
    if (!sb) return Promise.resolve({ ok: false, error: "offline" });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var ctx = r.error && r.error.context;
        if (ctx && typeof ctx.json === "function") return ctx.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: (r.error && r.error.message) || "error" };
      }
      return r.data || { ok: false, error: "empty" };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }

  // ---- CSS -------------------------------------------------------------------
  function injectCss() {
    if (document.getElementById("ak-social-css")) return;
    var st = document.createElement("style"); st.id = "ak-social-css";
    st.textContent = [
      "#ak-social{position:fixed;inset:0;z-index:60;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-social.open{display:flex}",
      ".aks-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,0.18)}",
      ".aks-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#c9a84c;flex:1}",
      ".aks-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".aks-tabs{display:flex;gap:6px;padding:8px 12px}",
      ".aks-tab{flex:1;padding:9px;border-radius:9px;border:1px solid rgba(201,168,76,0.22);background:rgba(255,255,255,0.03);color:#cfcfd6;font-weight:700;font-size:12px;letter-spacing:.5px;cursor:pointer}",
      ".aks-tab.on{background:rgba(201,168,76,0.16);color:#c9a84c;border-color:rgba(201,168,76,0.5)}",
      ".aks-tab[disabled]{opacity:.45}",
      ".aks-body{flex:1;overflow-y:auto;padding:10px 12px;-webkit-overflow-scrolling:touch}",
      ".aks-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px;margin-bottom:10px}",
      ".aks-row{display:flex;align-items:center;gap:8px}",
      ".aks-crest{flex:0 0 auto;width:42px;height:42px;border-radius:9px;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:20px;background:rgba(201,168,76,0.14);border:1px solid rgba(201,168,76,0.3)}",
      ".aks-nm{font-weight:800;color:#fff}.aks-tag{color:#c9a84c;font-weight:800}.aks-sub{color:#9a9aa6;font-size:11px}",
      ".aks-btn{background:linear-gradient(180deg,#c9a84c,#cf9b22);color:#1a1405;border:0;border-radius:9px;padding:10px 14px;font-weight:800;letter-spacing:.5px;cursor:pointer}",
      ".aks-btn.ghost{background:rgba(255,255,255,0.05);color:#e9e9ee;border:1px solid rgba(255,255,255,0.16)}",
      ".aks-btn.dng{background:rgba(220,80,80,0.16);color:#f3a0a0;border:1px solid rgba(220,80,80,0.3)}",
      ".aks-btn:active{transform:scale(0.97)}.aks-btn[disabled]{opacity:.5}",
      ".aks-inp,.aks-sel{width:100%;box-sizing:border-box;background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.14);color:#fff;border-radius:9px;padding:10px;margin:5px 0;font-size:14px}",
      ".aks-dot{width:8px;height:8px;border-radius:50%;background:#3a3a44;display:inline-block;margin-right:6px;flex:0 0 auto}.aks-dot.on{background:#5fd35f;box-shadow:0 0 6px #5fd35f}",
      ".aks-mlist{display:flex;flex-direction:column;gap:6px}",
      ".aks-msg{background:rgba(255,255,255,0.04);border-radius:9px;padding:7px 9px;font-size:13px;line-height:1.35;word-break:break-word}",
      ".aks-msg b{color:#c9a84c;font-weight:700}.aks-msg .ft{color:#8a8a96;font-size:10px;margin-left:4px}",
      ".aks-chatbar{display:flex;gap:6px;padding:8px 12px;border-top:1px solid rgba(201,168,76,0.18)}",
      ".aks-chatbar input{flex:1;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.14);color:#fff;border-radius:20px;padding:10px 14px;font-size:14px}",
      ".aks-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px 8px}",
      ".aks-toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:#1a1a22;color:#c9a84c;border:1px solid rgba(201,168,76,0.4);padding:9px 16px;border-radius:20px;z-index:70;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".aks-toast.show{opacity:1}",
      ".aks-li{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid rgba(255,255,255,0.06)}",
      // AK-CHAT-RESKIN: custom gold-cyberpunk speech bubbles (self-contained so
      // the overlay themes correctly even on a page that doesn't load shop.css).
      ".akc-list{display:flex;flex-direction:column;gap:9px}",
      ".akc-row{display:flex;align-items:flex-end;gap:8px;max-width:88%;align-self:flex-start}",
      ".akc-row.mine{flex-direction:row-reverse;align-self:flex-end}",
      ".akc-av{flex:0 0 auto;width:27px;height:27px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;line-height:1;background:radial-gradient(circle at 50% 32%,rgba(201,168,76,.24),rgba(10,10,16,.92));border:1.5px solid var(--crew,#c9a84c);box-shadow:0 0 7px rgba(201,168,76,.28);color:#f3e6c0}",
      ".akc-bub{position:relative;min-width:0;background:linear-gradient(180deg,rgba(20,20,28,.92),rgba(10,10,16,.92));border:1px solid rgba(201,168,76,.26);border-left:2px solid var(--crew,#c9a84c);border-radius:14px 14px 14px 4px;padding:6px 11px 7px;box-shadow:0 2px 9px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.045);overflow:hidden}",
      ".akc-row.mine .akc-bub{background:linear-gradient(180deg,rgba(201,168,76,.22),rgba(143,110,30,.17));border:1px solid rgba(232,197,90,.5);border-left:1px solid rgba(232,197,90,.5);border-right:2px solid #e8c55a;border-radius:14px 14px 4px 14px}",
      ".akc-hd{display:flex;align-items:baseline;gap:7px;margin-bottom:1px}",
      ".akc-nm{font-family:'Cinzel',Georgia,serif;font-weight:700;font-size:11.5px;letter-spacing:.3px;background:linear-gradient(90deg,#c9a84c,#e8c55a);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:#e8c55a}",
      ".akc-row.mine .akc-nm{background:linear-gradient(90deg,#fff1cc,#e8c55a);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}",
      ".akc-ft{font-size:9px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:var(--crew,#8a8a96);opacity:.85}",
      ".akc-bd{font-family:'Inter',system-ui,sans-serif;color:#ece7da;font-size:13.5px;line-height:1.4;word-break:break-word}",
      ".akc-row.mine .akc-bd{color:#fff7e6}",
      ".akc-row.fresh{animation:akcPop .26s cubic-bezier(.2,.8,.2,1) both}",
      ".akc-row.fresh .akc-bub::after{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(115deg,transparent 32%,rgba(232,197,90,.34) 50%,transparent 68%);transform:translateX(-130%);animation:akcShimmer .9s ease-out .08s 1;pointer-events:none}",
      "@keyframes akcPop{from{opacity:0;transform:translateY(7px) scale(.97)}to{opacity:1;transform:none}}",
      "@keyframes akcShimmer{to{transform:translateX(130%)}}",
      "@media (prefers-reduced-motion:reduce){.akc-row.fresh{animation:none}.akc-row.fresh .akc-bub::after{display:none}}",
    ].join("");
    document.head.appendChild(st);
  }

  // ---- DOM shell -------------------------------------------------------------
  var root, bodyEl, chatBar, chatInput, sendBtn, toastEl, tabCrew, tabChat;
  function buildShell() {
    if (root) return;
    injectCss();
    var xBtn = mk("button", { class: "aks-x", type: "button", "aria-label": "close", onclick: close, text: "×" });
    var top = mk("div", { class: "aks-top" }, [mk("h2", { text: "CREW HQ" }), xBtn]);
    tabCrew = mk("button", { class: "aks-tab on", type: "button", text: "CREW", onclick: function () { setTab("crew"); } });
    tabChat = mk("button", { class: "aks-tab", type: "button", text: "CHAT", onclick: function () { setTab("chat"); } });
    var tabs = mk("div", { class: "aks-tabs" }, [tabCrew, tabChat]);
    bodyEl = mk("div", { class: "aks-body" });
    chatInput = mk("input", { maxlength: "200", placeholder: "Say something...", type: "text" });
    chatInput.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); sendChat(); } });
    sendBtn = mk("button", { class: "aks-btn", type: "button", text: "Send", onclick: sendChat });
    chatBar = mk("div", { class: "aks-chatbar" }, [chatInput, sendBtn]);
    chatBar.style.display = "none";
    root = mk("section", { id: "ak-social" }, [top, tabs, bodyEl, chatBar]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "aks-toast" }); document.body.appendChild(toastEl);
  }

  function setTab(t) {
    S.tab = t;
    tabCrew.classList.toggle("on", t === "crew");
    tabChat.classList.toggle("on", t === "chat");
    chatBar.style.display = t === "chat" ? "flex" : "none";
    if (t === "crew") renderCrew(); else renderChat();
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }

  function open() { buildShell(); root.classList.add("open"); setTab("crew"); refreshCrew(); subscribeWorld(); claimGrants(); }
  function close() { if (root) root.classList.remove("open"); }

  // ---- CREW ------------------------------------------------------------------
  function refreshCrew() {
    if (!me()) { renderCrew(); return; }
    call("ak-crew", { action: "mine" }).then(function (r) {
      if (r && r.ok) { S.crew = r.crew || null; S.role = r.role || null; S.members = r.members || []; }
      renderCrew();
      if (S.crew) subscribeCrew();
    });
  }
  function renderCrew() {
    if (S.tab !== "crew" || !bodyEl) return;
    if (!me()) {
      setKids(bodyEl, [
        mk("div", { class: "aks-note", text: "Sign in with Google to start or join a crew, chat, and donate cards." }),
        mk("button", { class: "aks-btn", style: "display:block;margin:0 auto", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } }),
      ]);
      return;
    }
    if (S.crew) renderCrewHome(); else renderCrewBrowse();
  }

  function renderCrewHome() {
    var c = S.crew;
    var header = mk("div", { class: "aks-card" }, [
      mk("div", { class: "aks-row" }, [
        crestEl(c.faction),
        mk("div", { style: "flex:1" }, [
          mk("div", { class: "aks-nm" }, [c.name + " ", mk("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
          mk("div", { class: "aks-sub", text: (FNAME[c.faction] || c.faction) + " • " + (c.member_count || S.members.length) + "/50 • " + (c.trophies || 0) + " trophies" }),
        ]),
      ]),
      c.description ? mk("div", { class: "aks-sub", style: "margin-top:8px", text: c.description }) : null,
    ]);
    var actions = mk("div", { class: "aks-row", style: "gap:8px;margin-bottom:10px" }, [
      mk("button", { class: "aks-btn", style: "flex:1", text: "💬 Crew Chat", onclick: function () { S.scope = "crew"; setTab("chat"); } }),
      mk("button", { class: "aks-btn dng", text: "Leave", onclick: doLeave }),
    ]);
    var rosterRows = S.members.map(function (m) {
      var nm = m.user_id === myId() ? myName() + " (you)" : (m.name || ("Stray " + String(m.user_id).slice(0, 4)));
      return mk("div", { class: "aks-li" }, [
        mk("span", { class: "aks-dot" + (m._on ? " on" : "") }),
        mk("span", { class: "aks-nm", style: "flex:1", text: nm }),
        mk("span", { class: "aks-sub", text: m.role || "member" }),
      ]);
    });
    var roster = mk("div", { class: "aks-card" }, [mk("div", { class: "aks-sub", style: "margin-bottom:6px", text: "CREW (" + S.members.length + " • " + S.presence.crew + " online)" })].concat(rosterRows));
    setKids(bodyEl, [header, actions, renderDonations(), roster, renderCrewWars()]);
  }

  // ---- DONATIONS board (the carry-your-weight loop) --------------------------
  function renderDonations() {
    var head = mk("div", { class: "aks-row", style: "margin-bottom:8px" }, [
      mk("div", { class: "aks-sub", style: "flex:1", text: "DONATIONS -- carry your weight" }),
      mk("button", { class: "aks-btn", style: "padding:6px 10px", text: "Request", onclick: donRequestForm }),
    ]);
    var box = mk("div", { class: "aks-card" }, [head, mk("div", { class: "aks-note", text: "Loading..." })]);
    call("ak-crew", { action: "don-list" }).then(function (r) {
      var list = (r && r.requests) || [];
      var rows;
      if (!list.length) rows = [mk("div", { class: "aks-note", text: "No open requests. Tap Request to ask your crew for cards." })];
      else rows = list.map(function (rq) {
        var mine = rq.user_id === myId();
        var btn = mk("button", { class: "aks-btn" + (mine ? " ghost" : ""), style: "padding:6px 10px", text: mine ? "yours" : "Donate" });
        if (mine) btn.disabled = true;
        else btn.onclick = function () { btn.disabled = true; call("ak-crew", { action: "don-fill", request_id: rq.id }).then(function (rr) { if (rr.ok) { toast("Donated " + rr.filled + "!"); try { if (global.AKQuests) global.AKQuests.reportEvent("donates", rr.filled || 1); } catch (_) {} renderCrew(); } else { toast(rr.error || "error"); btn.disabled = false; } }); };
        return mk("div", { class: "aks-li" }, [
          mk("div", { style: "flex:1" }, [
            mk("div", { class: "aks-nm", style: "font-size:13px", text: rq.requester_name || "Stray" }),
            mk("div", { class: "aks-sub", text: "wants " + rq.qty_req + "x " + rq.card_id + "  (" + rq.qty_filled + "/" + rq.qty_req + ")" }),
          ]),
          btn,
        ]);
      });
      setKids(box, [head].concat(rows));
    });
    return box;
  }
  function donRequestForm() {
    var owned = myOwned();
    var picker = owned.length
      ? mk("select", { class: "aks-sel" }, owned.slice().sort().map(function (n) { return mk("option", { value: n, text: n }); }))
      : mk("input", { class: "aks-inp", placeholder: "Card name", type: "text" });
    var qty = mk("select", { class: "aks-sel" }, [2, 4, 6, 8].map(function (q) { return mk("option", { value: String(q), text: q + " copies" }); }));
    var go = mk("button", { class: "aks-btn", style: "flex:1", text: "Post Request" });
    go.onclick = function () {
      var card = (picker.value || "").trim(); if (!card) { toast("pick a card"); return; }
      go.disabled = true;
      call("ak-crew", { action: "don-request", card_id: card, qty_req: parseInt(qty.value, 10), name: myName() })
        .then(function (r) { if (r.ok) { toast("Request posted"); renderCrew(); } else { toast(r.error || "error"); go.disabled = false; } });
    };
    setKids(bodyEl, mk("div", { class: "aks-card" }, [
      mk("div", { class: "aks-nm", style: "margin-bottom:6px", text: "Request cards from your crew" }),
      mk("div", { class: "aks-sub", style: "margin-bottom:6px", text: "Crewmates donate copies -- free for them, a big help for you." }),
      picker, qty,
      mk("div", { class: "aks-row", style: "gap:8px;margin-top:6px" }, [go, mk("button", { class: "aks-btn ghost", text: "Back", onclick: renderCrew })]),
    ]));
  }
  function doLeave() {
    if (!confirm("Leave " + S.crew.name + "?")) return;
    call("ak-crew", { action: "leave" }).then(function (r) {
      if (r.ok) { S.crew = null; S.members = []; unsub("crew"); toast("Left the crew"); refreshCrew(); }
      else toast(r.error || "error");
    });
  }

  // ---- CREW WARS board (Phase 2: async crew-vs-crew trophy tally) ------------
  // AK-CREWWARS 2026-07-12: wire the client entry point for the DEPLOYED-but-idle
  // ak_crew_wars / ak_war_battles rail. The ak-crew edge function does NOT expose a
  // war action yet -- see the handoff note for Lucrex (needs: war-status [read the
  // caller crew's active/recent war + battle log from ak_crew_wars + ak_war_battles],
  // war-start [leader: matchmake an opponent crew + open an ak_crew_wars row],
  // war-battle [record an ak_war_battles row + tally, likely auto-fed off raid
  // resolve]). Until those ship, call() returns {ok:false,error:'unknown action'}
  // (online) or {ok:false,error:'offline'} (signed out / no network) and this card
  // degrades to the honest "wars open soon" state -- never a crash, never blank. When
  // war-status ships returning {ok,war,battles} the SAME card lights up with the live
  // us-vs-them tally, no client shape change needed.
  function warStartBtn() {
    var start = mk("button", { class: "aks-btn", style: "margin-top:8px;padding:6px 10px", text: "Find a War" });
    start.onclick = function () {
      start.disabled = true;
      call("ak-crew", { action: "war-start" }).then(function (rr) {
        if (rr && rr.ok) { toast("War matchmaking started"); renderCrew(); }
        else { toast((rr && rr.error === "unknown action") ? "Crew Wars go live soon" : ((rr && rr.error) || "not yet")); start.disabled = false; }
      });
    };
    return start;
  }
  function warIdle(r) {
    var kids = [
      mk("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WARS" }),
      mk("div", { class: "aks-sub", style: "color:#cfcfd6", text: "Wars open with async crew-vs-crew (Phase 2). Stack trophies now -- your raid wins tally for the crew the moment wars go live." }),
    ];
    // leader-only Start, and only when the rail actually answered (deployed but idle),
    // not when we are simply signed out / offline -- keeps the button honest.
    if (S.role === "leader" && r && r.error && r.error !== "offline") kids.push(warStartBtn());
    return kids;
  }
  function warLive(r) {
    var w = r.war || null;
    if (!w) {
      var none = [
        mk("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WARS" }),
        mk("div", { class: "aks-note", text: "No active war. Matchmake an opponent crew to start a trophy war." }),
      ];
      if (S.role === "leader") none.push(warStartBtn());
      return none;
    }
    var us = (w.our_score | 0), them = (w.their_score | 0);
    var myTag = (S.crew && S.crew.tag) ? ("[" + S.crew.tag + "]") : "US";
    var head = mk("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WAR -- " + (w.state || "active") });
    var score = mk("div", { class: "aks-row", style: "gap:10px;align-items:center;margin:6px 0" }, [
      mk("div", { style: "flex:1;text-align:center" }, [
        mk("div", { class: "aks-nm", text: String(us) }),
        mk("div", { class: "aks-sub", text: myTag }),
      ]),
      mk("div", { class: "aks-sub", text: "vs" }),
      mk("div", { style: "flex:1;text-align:center" }, [
        mk("div", { class: "aks-nm", text: String(them) }),
        mk("div", { class: "aks-sub", text: w.opponent_tag ? ("[" + w.opponent_tag + "]") : (w.opponent_name || "THEM") }),
      ]),
    ]);
    var battles = Array.isArray(r.battles) ? r.battles.slice(0, 12) : [];
    var log = battles.length
      ? battles.map(function (b) {
          return mk("div", { class: "aks-li" }, [
            mk("span", { class: "aks-sub", style: "flex:1", text: (b.attacker_name || "Crewmate") + (b.stars != null ? (" -- " + b.stars + "star") : "") }),
            mk("span", { class: "aks-sub", text: b.for_us ? myTag : "THEM" }),
          ]);
        })
      : [mk("div", { class: "aks-note", text: "No battles logged yet. Raid to score for the crew." })];
    return [head, score].concat(log);
  }
  function renderCrewWars() {
    var card = mk("div", { class: "aks-card" }, [
      mk("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WARS" }),
      mk("div", { class: "aks-note", text: "Loading war board..." }),
    ]);
    call("ak-crew", { action: "war-status" }).then(function (r) {
      if (!card.isConnected && bodyEl && !bodyEl.contains(card)) return;
      if (r && r.ok) setKids(card, warLive(r));
      else setKids(card, warIdle(r));
    }, function () { setKids(card, warIdle(null)); });
    return card;
  }

  function renderCrewBrowse() {
    var search = mk("input", { class: "aks-inp", placeholder: "Search crews", style: "margin:0", type: "text" });
    var listBox = mk("div", {}, mk("div", { class: "aks-note", text: "Loading crews..." }));
    var t; search.oninput = function () { clearTimeout(t); t = setTimeout(function () { loadCrewList(search.value, listBox); }, 350); };
    var bar = mk("div", { class: "aks-row", style: "gap:6px;margin-bottom:10px" }, [search, mk("button", { class: "aks-btn", text: "+ New", onclick: renderCreateForm })]);
    setKids(bodyEl, [bar, listBox]);
    loadCrewList("", listBox);
  }
  // AK-GHOSTCLANS 2026-07-03: a fresh player's crew list comes back EMPTY -- the
  // cold-start "empty room". Backfill with the 4 canon NPC clans from population.js
  // (same crest + colour the raid map + Fence already use) as pre-seeded,
  // JOINABLE-looking crews so the browser never feels dead. A tap explains they're
  // canon and routes to Create with that faction pre-picked (you become the first
  // real member). Guard: if AK_POPULATION is absent we return null and the list is
  // left as-is -- never a crash.
  function ghostCrews() {
    var pop = null;
    try { pop = global.AK_POPULATION; } catch (_) { pop = null; }
    if (!pop || typeof pop.clans !== "function") return null;
    var clans;
    try { clans = pop.clans() || []; } catch (_) { return null; }
    if (!clans.length) return null;
    return clans.map(function (cl) {
      return { id: null, _ghost: true, faction: cl.id, name: cl.name, tag: cl.tag, color: cl.color, member_count: 0, privacy: "open" };
    });
  }
  // one crew row for the browse list. Real crews get the Join/Ask flow; ghost
  // (canon) clans get a Claim tap that routes to Create with the faction pre-picked.
  function crewRowEl(c) {
    if (c._ghost) {
      var claimBtn = mk("button", { class: "aks-btn", text: "Claim" });
      claimBtn.onclick = function () { toast("Canon crew -- be the first real member"); renderCreateForm(c.faction); };
      return mk("div", { class: "aks-li" }, [
        crestEl(c.faction),
        mk("div", { style: "flex:1" }, [
          mk("div", { class: "aks-nm" }, [c.name + " ", mk("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
          mk("div", { class: "aks-sub", text: (FNAME[c.faction] || c.faction) + " • canon crew -- be the first real member" }),
        ]),
        claimBtn,
      ]);
    }
    var joinBtn = mk("button", { class: "aks-btn", text: c.privacy === "request" ? "Ask" : "Join" });
    joinBtn.onclick = function () {
      joinBtn.disabled = true;
      call("ak-crew", { action: "join", crew_id: c.id }).then(function (rr) {
        if (rr.ok && rr.requested) { toast("Request sent"); joinBtn.textContent = "Asked"; }
        else if (rr.ok) { toast("Joined!"); refreshCrew(); }
        else { toast(rr.error || "error"); joinBtn.disabled = false; }
      });
    };
    return mk("div", { class: "aks-li" }, [
      crestEl(c.faction),
      mk("div", { style: "flex:1" }, [
        mk("div", { class: "aks-nm" }, [c.name + " ", mk("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
        mk("div", { class: "aks-sub", text: (FNAME[c.faction] || c.faction) + " • " + (c.member_count || 0) + "/50 • " + (c.privacy || "open") }),
      ]),
      joinBtn,
    ]);
  }
  function loadCrewList(q, box) {
    call("ak-crew", { action: "list", q: q || "" }).then(function (r) {
      if (!box.isConnected && bodyEl && !bodyEl.contains(box)) return;
      var crews = (r && r.crews) || [];
      if (!crews.length) {
        // ghost-seed only the unfiltered cold-start browse -- a search that finds
        // nothing should honestly say so rather than surface the canon clans.
        var ghosts = (q && String(q).trim()) ? null : ghostCrews();
        if (!ghosts || !ghosts.length) { setKids(box, mk("div", { class: "aks-note", text: "No crews yet. Be the first -- start one." })); return; }
        crews = ghosts;
      }
      setKids(box, crews.map(crewRowEl));
    });
  }

  function renderCreateForm(prefFac) {
    var name = mk("input", { class: "aks-inp", maxlength: "24", placeholder: "Crew name (3-24)", type: "text" });
    var tag = mk("input", { class: "aks-inp", maxlength: "4", placeholder: "Tag (2-4, e.g. BONE)", type: "text" });
    var fac = mk("select", { class: "aks-sel" }, FACTIONS.map(function (f) { return mk("option", { value: f.id, text: f.name }); }));
    // a ghost-clan tap routes here with its faction pre-picked (string-guarded so the
    // "+ New" button, which passes a click Event, never mis-sets the select).
    if (typeof prefFac === "string" && prefFac) { try { fac.value = prefFac; } catch (_) {} }
    var priv = mk("select", { class: "aks-sel" }, [
      mk("option", { value: "open", text: "Open -- anyone joins" }),
      mk("option", { value: "request", text: "Request -- approve members" }),
      mk("option", { value: "closed", text: "Closed -- invite only" }),
    ]);
    var desc = mk("input", { class: "aks-inp", maxlength: "200", placeholder: "Description (optional)", type: "text" });
    var createBtn = mk("button", { class: "aks-btn", style: "flex:1", text: "Create Crew" });
    createBtn.onclick = function () {
      createBtn.disabled = true;
      call("ak-crew", { action: "create", name: name.value.trim(), tag: tag.value.trim(), faction: fac.value, privacy: priv.value, description: desc.value.trim() })
        .then(function (r) { if (r.ok) { toast("Crew created -- you're the leader"); refreshCrew(); } else { toast(r.error || "error"); createBtn.disabled = false; } });
    };
    var actions = mk("div", { class: "aks-row", style: "gap:8px;margin-top:6px" }, [createBtn, mk("button", { class: "aks-btn ghost", text: "Back", onclick: renderCrewBrowse })]);
    setKids(bodyEl, mk("div", { class: "aks-card" }, [mk("div", { class: "aks-nm", style: "margin-bottom:6px", text: "Start a Crew" }), name, tag, fac, priv, desc, actions]));
  }

  // ---- CHAT ------------------------------------------------------------------
  var mlist;
  function renderChat() {
    if (S.tab !== "chat" || !bodyEl) return;
    var inCrew = !!S.crew;
    if (S.scope === "crew" && !inCrew) S.scope = "world";
    var wTab = mk("button", { class: "aks-tab" + (S.scope === "world" ? " on" : ""), text: "WORLD • " + S.presence.world + " on", onclick: function () { S.scope = "world"; renderChat(); } });
    var cAttrs = { class: "aks-tab" + (S.scope === "crew" ? " on" : ""), text: inCrew ? "CREW" : "CREW (none)", onclick: function () { if (!inCrew) { toast("Join a crew first"); return; } S.scope = "crew"; renderChat(); } };
    if (!inCrew) cAttrs.disabled = "disabled";
    var cTab = mk("button", cAttrs);
    var scopeTabs = mk("div", { class: "aks-tabs", style: "padding:0 0 8px" }, [wTab, cTab]);
    mlist = mk("div", { class: "aks-mlist akc-list" });
    setKids(bodyEl, [scopeTabs, mlist]);
    paintMsgs();
    var signedIn = !!me();
    sendBtn.disabled = !signedIn;
    chatInput.disabled = !signedIn;
    chatInput.placeholder = !signedIn ? "Sign in to chat" : (S.scope === "crew" ? "Message your crew..." : "Message the world...");
    loadHistory(S.scope);
  }
  function paintMsgs() {
    if (!mlist) return;
    var arr = (S.msgs[S.scope] || []).slice(-80);
    if (!arr.length) { setKids(mlist, mk("div", { class: "aks-note", text: "No messages yet. Start the conversation." })); return; }
    // gold shimmer only on the genuinely-new last message (not on every repaint)
    var lastId = arr.length ? arr[arr.length - 1].id : null;
    var freshId = (lastId != null && lastId !== S._lastSeenId) ? lastId : null;
    S._lastSeenId = lastId;
    var uid = myId(), nm = myName();
    setKids(mlist, arr.map(function (m) {
      var mine = (m.user_id && uid && m.user_id === uid) || (!m.user_id && (m.name || "Stray") === nm);
      var hd = [mk("span", { class: "akc-nm", text: m.name || "Stray" })];
      if (m.faction && FNAME[m.faction]) hd.push(mk("span", { class: "akc-ft", text: FNAME[m.faction] }));
      var bub = mk("div", { class: "akc-bub" }, [
        mk("div", { class: "akc-hd" }, hd),
        mk("div", { class: "akc-bd", text: m.body || "" }),
      ]);
      var av = mk("span", { class: "akc-av", text: "🐾" }); // paw -- dog-gang flavour
      var cls = "akc-row" + (mine ? " mine" : "") + (m.id != null && m.id === freshId ? " fresh" : "");
      return mk("div", { class: cls, style: "--crew:" + facColor(m.faction) }, [av, bub]);
    }));
    mlist.scrollTop = mlist.scrollHeight;
  }
  function loadHistory(scope) {
    call("ak-chat", { action: "history", scope: scope }).then(function (r) {
      if (r && r.ok) { S.msgs[scope] = r.messages || []; if (S.tab === "chat" && S.scope === scope) paintMsgs(); }
    });
  }
  function pushMsg(scope, m) {
    var arr = S.msgs[scope] || (S.msgs[scope] = []);
    if (arr.some(function (x) { return x.id === m.id; })) return;
    arr.push(m); if (arr.length > 120) arr.shift();
    if (S.tab === "chat" && S.scope === scope) paintMsgs();
  }
  function sendChat() {
    if (!me()) { toast("Sign in to chat"); return; }
    var body = (chatInput.value || "").trim(); if (!body) return;
    chatInput.value = "";
    var faction = S.crew ? S.crew.faction : null;
    call("ak-chat", { action: "send", scope: S.scope, body: body, name: myName(), faction: faction }).then(function (r) {
      if (!r.ok) { toast(r.error || "could not send"); chatInput.value = body; }
      else if (r.message) { pushMsg(S.scope, r.message); try { if (global.AKQuests) global.AKQuests.reportEvent("chats", 1); } catch (_) {} }
    });
  }

  // ---- Realtime --------------------------------------------------------------
  function subscribeWorld() {
    var sb = sbc(); if (!sb || S.chans.world) return;
    var ch = sb.channel("ak-world-chat");
    ch.on("postgres_changes", { event: "INSERT", schema: "public", table: "ak_chat_messages", filter: "scope=eq.world" }, function (p) { pushMsg("world", p.new); });
    ch.on("presence", { event: "sync" }, function () { try { S.presence.world = countPresence(ch); if (S.tab === "chat") syncWorldHeadcount(); } catch (_) {} });
    ch.subscribe(function (st) { if (st === "SUBSCRIBED") { try { ch.track({ uid: myId() || "anon", name: myName() }); } catch (_) {} } });
    S.chans.world = ch;
  }
  function subscribeCrew() {
    var sb = sbc(); if (!sb || !S.crew) return;
    unsub("crew");
    var cid = S.crew.id;
    var ch = sb.channel("ak-crew-chat-" + cid);
    ch.on("postgres_changes", { event: "INSERT", schema: "public", table: "ak_chat_messages", filter: "crew_id=eq." + cid }, function (p) { if (p.new && p.new.scope === "crew") pushMsg("crew", p.new); });
    ch.on("presence", { event: "sync" }, function () {
      try {
        var st = ch.presenceState(); var ids = {};
        Object.keys(st).forEach(function (k) { (st[k] || []).forEach(function (p) { if (p.uid) ids[p.uid] = 1; }); });
        S.presence.crew = Object.keys(ids).length;
        S.members.forEach(function (m) { m._on = !!ids[m.user_id]; });
        if (S.tab === "crew") renderCrew();
      } catch (_) {}
    });
    ch.subscribe(function (s) { if (s === "SUBSCRIBED") { try { ch.track({ uid: myId() || "anon", name: myName() }); } catch (_) {} } });
    S.chans.crew = ch;
  }
  function countPresence(ch) { try { var st = ch.presenceState(); var ids = {}; Object.keys(st).forEach(function (k) { (st[k] || []).forEach(function (p) { if (p.uid) ids[p.uid] = 1; }); }); return Object.keys(ids).length; } catch (_) { return 0; } }
  function unsub(which) { var sb = sbc(); if (sb && S.chans[which]) { try { sb.removeChannel(S.chans[which]); } catch (_) {} S.chans[which] = null; } }
  function syncWorldHeadcount() { if (S.tab === "chat" && bodyEl) { var t = bodyEl.querySelector(".aks-tabs .aks-tab"); if (t) t.textContent = "WORLD • " + S.presence.world + " on"; } }

  // ---- AK-RAIDPING 2026-06-22: live "you were raided" feed -------------------
  // The server ALREADY inserts ak_raid_revenge on every real-player raid resolve
  // (ak-raid edge fn). We just subscribe (victim_id = me) + toast it so the world
  // feels alive with other players acting on you. North star: play WITH each other.
  // Standalone toast so it fires even when the social panel is closed.
  function raidPing(msg) {
    injectCss();
    var el = toastEl;
    if (!el) { el = document.createElement("div"); el.className = "aks-toast"; document.body.appendChild(el); }
    el.textContent = msg; el.classList.add("show");
    clearTimeout(raidPing._t); raidPing._t = setTimeout(function () { el.classList.remove("show"); }, 4200);
  }
  function subscribeRevenge() {
    var sb = sbc(), id = myId(); if (!sb || !id || S.chans.revenge) return;
    var ch = sb.channel("ak-revenge-" + id);
    ch.on("postgres_changes", { event: "INSERT", schema: "public", table: "ak_raid_revenge", filter: "victim_id=eq." + id }, function (p) {
      var r = p && p.new; if (!r) return;
      var who = r.attacker_name || "A rival crew", tier = r.tier ? (" T" + r.tier) : "";
      raidPing("🐾 " + who + tier + " raided your turf! Hit back from the War Map.");
      try { if (global.AKQuests) global.AKQuests.reportEvent("raided", 1); } catch (_) {}
    });
    ch.subscribe();
    S.chans.revenge = ch;
  }

  // ---- AK-SOCIALAPI 2026-07-03: read-only social data for other lanes --------
  // window.AKSocial owns these; every consumer typeof-guards the call. Both are
  // fully guarded -- a missing population system or a signed-out player is a no-op
  // (crewLeaderboard -> [], reportReferral -> resolves falsy), never a throw.

  // crew members ranked by trophies. Reuses AK_POPULATION.leaderboard() for the
  // player's real count + a plausible canon spread for crewmates the server roster
  // carries no trophy count for. Returns [] when signed out or not in a crew.
  function crewLeaderboard() {
    try {
      if (!me() || !S.crew) return [];
      var members = S.members || [];
      if (!members.length) return [];
      var uid = myId();
      var lb = [];
      try { var pop = global.AK_POPULATION; if (pop && typeof pop.leaderboard === "function") lb = pop.leaderboard() || []; } catch (_) { lb = []; }
      var youRow = null;
      for (var i = 0; i < lb.length; i++) { if (lb[i] && lb[i].isYou) { youRow = lb[i]; break; } }
      var myTr = youRow ? (youRow.trophies | 0) : 0;
      var myRank = (youRow && youRow.rank) || null;
      // pool of {t,rank} from the canon roster -> fills crewmates with no server count
      var pool = lb.filter(function (r) { return r && !r.isYou; })
                   .map(function (r) { return { t: r.trophies | 0, rank: r.rank || null }; })
                   .sort(function (a, b) { return b.t - a.t; });
      var rows = members.map(function (m, idx) {
        var isYou = !!(m.user_id && uid && m.user_id === uid);
        var nm = isYou ? myName() : (m.name || ("Stray " + String(m.user_id || "").slice(0, 4)));
        var pr = pool.length ? pool[idx % pool.length] : { t: 0, rank: null };
        var tr = (m.trophies != null) ? (m.trophies | 0) : (isYou ? myTr : pr.t);
        if (isYou && myTr) tr = myTr;
        var rank = m.rank || (isYou ? myRank : pr.rank) || null;
        return { name: nm, trophies: tr, isYou: isYou, rank: rank };
      });
      rows.sort(function (a, b) { return b.trophies - a.trophies; });
      rows.forEach(function (r, i) { r.place = i + 1; });
      return rows;
    } catch (_) { return []; }
  }

  // AK-REALBOARD 2026-07-12 (Phase 2 social): a REAL, server-derived leaderboard of
  // live crews ranked by trophies, read from the DEPLOYED ak-crew {action:'list'} (the
  // server sorts by trophies desc). The ladder lane (systems/ladder.js) consumes this
  // for its LIVE board tab. Server-derived rank only -- trophies come off the server
  // crew row, never the local save. Fully guarded + offline-degrading: resolves [] when
  // signed out, offline, the social/account client is absent, or the server returns
  // nothing, so the ghost roster board stays the populated fallback (never blank).
  // NOTE for Lucrex: this is a real CREW board. A true real-PLAYER-by-trophies board
  // still needs a NEW edge action (ak-crew or ak-raid {action:'leaderboard'} reading
  // ak_player_bases / the deferred ak_players projection server-side) -- ak_player_bases
  // is RLS own-row-locked and ak-crew {action:'mine'} carries no per-member trophies,
  // so real per-player ranks cannot be read from the client today.
  function serverLeaderboard() {
    try {
      if (!sbc() || !me()) return Promise.resolve([]);
      return call("ak-crew", { action: "list", q: "" }).then(function (r) {
        var crews = (r && r.ok && Array.isArray(r.crews)) ? r.crews : [];
        if (!crews.length) return [];
        var myCrewId = (S.crew && S.crew.id) || null;
        return crews.slice()
          .sort(function (a, b) { return ((b.trophies | 0) - (a.trophies | 0)) || ((b.member_count | 0) - (a.member_count | 0)); })
          .slice(0, 50)
          .map(function (c, i) {
            return {
              name: (c.name || "Crew") + (c.tag ? (" [" + c.tag + "]") : ""),
              clan: c.faction || "stray",
              color: facColor(c.faction),
              rank: FNAME[c.faction] || "",
              trophies: c.trophies | 0,
              place: i + 1,
              isCrew: true,
              isYou: !!(myCrewId && c.id === myCrewId),
            };
          });
      }, function () { return []; });
    } catch (_) { return Promise.resolve([]); }
  }

  // best-effort: tell the server an inbound referral code arrived so the INVITER
  // can be credited later. The invitee's own welcome bonus is granted client-side
  // by the viral lane, not here. Resolves falsy (never throws) if the server has no
  // such action, we're offline, or the player is signed out.
  function reportReferral(code) {
    try {
      var c = (code == null) ? "" : String(code).trim();
      if (!c || !sbc() || !me()) return Promise.resolve(false);
      return call("ak-crew", { action: "referral", code: c, name: myName() }).then(
        function (r) { return !!(r && r.ok); },
        function () { return false; }
      );
    } catch (_) { return Promise.resolve(false); }
  }

  // ---- wire-up ---------------------------------------------------------------
  function wire() {
    if (S.booted) return; S.booted = true;
    var btn = document.getElementById("crewbtn");
    if (btn) btn.addEventListener("click", open);
    try { global.addEventListener("ak-auth", function (e) { if (e && e.detail && e.detail.user) { claimGrants(); subscribeRevenge(); if (root && root.classList.contains("open")) refreshCrew(); } }); } catch (_) {}
    // also claim + start the raid-ping feed on first load if a session is already restored
    setTimeout(function () { claimGrants(); subscribeRevenge(); }, 3500);
    global.AKSocial = { open: open, close: close, claimGrants: claimGrants, subscribeRevenge: subscribeRevenge, crewLeaderboard: crewLeaderboard, serverLeaderboard: serverLeaderboard, reportReferral: reportReferral };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})(typeof window !== "undefined" ? window : this);
