/* ==========================================================================
   ALLEY KINGZ -- THE HIT LIST (daily/weekly quests). Self-mounting (like pass.js).
   - reportMatch(won,gates) + reportEvent(metric,n): bump server counters (called
     from grantMatchRewards + social.js donate/chat).
   - Hit List screen: daily + weekly quests, progress bars, claim buttons.
     Rewards apply via AKSocial.claimGrants() (grants rail) or feed the pass (passxp).
   mk() builder, no innerHTML. Include AFTER pass.js.
   ========================================================================== */
(function (global) {
  "use strict";
  var Q = { booted: false, quests: [] };
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
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
  function rewardLabel(r) {
    if (!r) return "--";
    if (r.kind === "gold") return "💰 " + r.amount;
    if (r.kind === "passxp") return "⭐ " + r.amount + " Pass XP";
    if (r.kind === "scrap") return "🔩 " + r.amount + " " + (r.rarity || "");
    if (r.kind === "chest") return "📦 " + (r.card_id || "") + " chest";
    if (r.kind === "keys") return "🔑 " + r.amount;
    if (r.kind === "card") return "🃏 " + (r.card_id || "") + " x" + r.amount;
    return r.kind;
  }
  function injectCss() {
    if (document.getElementById("ak-quests-css")) return;
    var st = document.createElement("style"); st.id = "ak-quests-css";
    st.textContent = [
      "#ak-quests{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-quests.open{display:flex}",
      ".akq-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,0.18)}",
      ".akq-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#c9a84c;flex:1}",
      ".akq-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".akq-body{flex:1;overflow-y:auto;padding:10px 12px}",
      ".akq-sec{font-size:11px;letter-spacing:1px;color:#8a8a96;margin:8px 2px 4px}",
      ".akq-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:11px;margin-bottom:9px}",
      ".akq-row{display:flex;align-items:center;gap:10px}",
      ".akq-nm{font-weight:800;color:#fff;font-size:14px}.akq-desc{color:#9a9aa6;font-size:11px}",
      ".akq-rw{color:#c9a84c;font-size:11px;font-weight:700;margin-top:2px}",
      ".akq-bar{height:8px;border-radius:5px;background:rgba(255,255,255,0.1);overflow:hidden;margin:7px 0 4px}",
      ".akq-fill{height:100%;background:linear-gradient(90deg,#5fd35f,#33a833)}",
      ".akq-fill.done{background:linear-gradient(90deg,#c9a84c,#cf9b22)}",
      ".akq-btn{background:linear-gradient(180deg,#c9a84c,#cf9b22);color:#1a1405;border:0;border-radius:8px;padding:9px 14px;font-weight:800;font-size:12px;cursor:pointer;white-space:nowrap}",
      ".akq-btn[disabled]{opacity:.4}.akq-btn.done{background:rgba(95,211,95,0.14);color:#5fd35f;border:1px solid rgba(95,211,95,0.4)}",
      ".akq-prog{font-size:11px;color:#cfcfd6}",
      ".akq-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px}",
      ".akq-toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:#1a1a22;color:#c9a84c;border:1px solid rgba(201,168,76,0.4);padding:9px 16px;border-radius:20px;z-index:71;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".akq-toast.show{opacity:1}",
    ].join("");
    document.head.appendChild(st);
  }
  var root, bodyEl, toastEl;
  function buildShell() {
    if (root) return; injectCss();
    var x = mk("button", { class: "akq-x", type: "button", text: "×", onclick: close });
    var top = mk("div", { class: "akq-top" }, [mk("h2", { text: "THE HIT LIST" }), x]);
    bodyEl = mk("div", { class: "akq-body" });
    root = mk("section", { id: "ak-quests" }, [top, bodyEl]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "akq-toast" }); document.body.appendChild(toastEl);
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }
  function open() { buildShell(); root.classList.add("open"); load(); }
  function close() { if (root) root.classList.remove("open"); }
  function load() {
    if (!me()) { setKids(bodyEl, [mk("div", { class: "akq-note", text: "Sign in to take on daily + weekly missions for gold, scrap and Pass XP." }), mk("button", { class: "akq-btn", style: "display:block;margin:8px auto", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } })]); return; }
    setKids(bodyEl, mk("div", { class: "akq-note", text: "Loading the Hit List..." }));
    call("ak-quests", { action: "get" }).then(function (r) {
      if (!r || !r.ok) { setKids(bodyEl, mk("div", { class: "akq-note", text: r && r.error ? r.error : "Could not load" })); return; }
      Q.quests = r.quests || []; render();
    });
  }
  function render() {
    var daily = Q.quests.filter(function (q) { return q.scope === "daily"; });
    var weekly = Q.quests.filter(function (q) { return q.scope === "weekly"; });
    var nodes = [];
    nodes.push(mk("div", { class: "akq-sec", text: "DAILY -- resets every morning" }));
    daily.forEach(function (q) { nodes.push(questCard(q)); });
    nodes.push(mk("div", { class: "akq-sec", text: "WEEKLY -- resets Monday" }));
    weekly.forEach(function (q) { nodes.push(questCard(q)); });
    setKids(bodyEl, nodes);
  }
  function questCard(q) {
    var pct = Math.max(0, Math.min(100, Math.round(q.progress / q.target * 100)));
    var btn;
    if (q.claimed) btn = mk("button", { class: "akq-btn done", disabled: "1", text: "✓ done" });
    else if (q.claimable) { btn = mk("button", { class: "akq-btn", text: "Claim" }); btn.onclick = function () { btn.disabled = true; claim(q, btn); }; }
    else btn = mk("button", { class: "akq-btn", disabled: "1", text: q.progress + "/" + q.target });
    return mk("div", { class: "akq-card" }, [
      mk("div", { class: "akq-row" }, [
        mk("div", { style: "flex:1" }, [mk("div", { class: "akq-nm", text: q.title }), mk("div", { class: "akq-desc", text: q.desc }), mk("div", { class: "akq-rw", text: rewardLabel(q.reward) })]),
        btn,
      ]),
      mk("div", { class: "akq-bar" }, mk("div", { class: "akq-fill" + (q.claimable || q.claimed ? " done" : ""), style: "width:" + pct + "%" })),
      mk("div", { class: "akq-prog", text: q.progress + " / " + q.target }),
    ]);
  }
  function claim(q, btn) {
    call("ak-quests", { action: "claim", quest_id: q.id }).then(function (r) {
      if (!r || !r.ok) { toast(r && r.error ? r.error : "could not claim"); if (btn) btn.disabled = false; return; }
      toast("Claimed " + rewardLabel(q.reward));
      if (q.reward && q.reward.kind !== "passxp") { try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_) {} }
      load();
    });
  }
  // ---- reporting (called from match end + social actions) -------------------
  function reportMatch(won, gates) { if (!me()) return; call("ak-quests", { action: "report-match", won: !!won, gates: gates || 0 }); }
  function reportEvent(metric, n) { if (!me()) return; call("ak-quests", { action: "report-event", metric: metric, n: n || 1 }); }
  function wire() {
    if (Q.booted) return; Q.booted = true;
    var btn = document.getElementById("questsbtn");
    if (btn) btn.addEventListener("click", open);
    global.AKQuests = { open: open, close: close, reportMatch: reportMatch, reportEvent: reportEvent };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})(typeof window !== "undefined" ? window : this);
