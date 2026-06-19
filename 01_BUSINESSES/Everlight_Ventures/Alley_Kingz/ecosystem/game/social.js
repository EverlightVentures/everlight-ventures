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
      ".aks-crest{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;background:rgba(201,168,76,0.14);border:1px solid rgba(201,168,76,0.3)}",
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
        mk("div", { class: "aks-crest", text: "🐶" }),
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
    var war = mk("div", { class: "aks-card" }, [
      mk("div", { class: "aks-sub", style: "margin-bottom:4px", text: "CREW WARS" }),
      mk("div", { class: "aks-sub", style: "color:#cfcfd6", text: "Wars open with 2v2 (Phase 2). Stack trophies now -- your wins will tally for the crew." }),
    ]);
    setKids(bodyEl, [header, actions, renderDonations(), roster, war]);
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

  function renderCrewBrowse() {
    var search = mk("input", { class: "aks-inp", placeholder: "Search crews", style: "margin:0", type: "text" });
    var listBox = mk("div", {}, mk("div", { class: "aks-note", text: "Loading crews..." }));
    var t; search.oninput = function () { clearTimeout(t); t = setTimeout(function () { loadCrewList(search.value, listBox); }, 350); };
    var bar = mk("div", { class: "aks-row", style: "gap:6px;margin-bottom:10px" }, [search, mk("button", { class: "aks-btn", text: "+ New", onclick: renderCreateForm })]);
    setKids(bodyEl, [bar, listBox]);
    loadCrewList("", listBox);
  }
  function loadCrewList(q, box) {
    call("ak-crew", { action: "list", q: q || "" }).then(function (r) {
      if (!box.isConnected && bodyEl && !bodyEl.contains(box)) return;
      var crews = (r && r.crews) || [];
      if (!crews.length) { setKids(box, mk("div", { class: "aks-note", text: "No crews yet. Be the first -- start one." })); return; }
      setKids(box, crews.map(function (c) {
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
          mk("div", { class: "aks-crest", text: "🐶" }),
          mk("div", { style: "flex:1" }, [
            mk("div", { class: "aks-nm" }, [c.name + " ", mk("span", { class: "aks-tag", text: "[" + c.tag + "]" })]),
            mk("div", { class: "aks-sub", text: (FNAME[c.faction] || c.faction) + " • " + (c.member_count || 0) + "/50 • " + (c.privacy || "open") }),
          ]),
          joinBtn,
        ]);
      }));
    });
  }

  function renderCreateForm() {
    var name = mk("input", { class: "aks-inp", maxlength: "24", placeholder: "Crew name (3-24)", type: "text" });
    var tag = mk("input", { class: "aks-inp", maxlength: "4", placeholder: "Tag (2-4, e.g. BONE)", type: "text" });
    var fac = mk("select", { class: "aks-sel" }, FACTIONS.map(function (f) { return mk("option", { value: f.id, text: f.name }); }));
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
    mlist = mk("div", { class: "aks-mlist" });
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
    setKids(mlist, arr.map(function (m) {
      var kids = [mk("b", { text: m.name || "Stray" })];
      if (m.faction && FNAME[m.faction]) kids.push(mk("span", { class: "ft", text: FNAME[m.faction] }));
      kids.push(mk("br"));
      kids.push(document.createTextNode(m.body || ""));
      return mk("div", { class: "aks-msg" }, kids);
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

  // ---- wire-up ---------------------------------------------------------------
  function wire() {
    if (S.booted) return; S.booted = true;
    var btn = document.getElementById("crewbtn");
    if (btn) btn.addEventListener("click", open);
    try { global.addEventListener("ak-auth", function (e) { if (e && e.detail && e.detail.user) { claimGrants(); if (root && root.classList.contains("open")) refreshCrew(); } }); } catch (_) {}
    // also claim on first load if a session is already restored (returning player)
    setTimeout(claimGrants, 3500);
    global.AKSocial = { open: open, close: close, claimGrants: claimGrants };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})(typeof window !== "undefined" ? window : this);
