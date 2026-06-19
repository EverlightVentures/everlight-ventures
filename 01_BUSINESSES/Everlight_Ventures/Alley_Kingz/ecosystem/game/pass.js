/* ==========================================================================
   ALLEY KINGZ -- ALLEY PASS (battle pass) UI. Self-mounting (like social.js).
   - reportMatch(won,gates): fires ak-pass report-match (server awards capped XP).
     Called once per match from grantMatchRewards (AK-PASS hook in index.html).
   - Pass screen: XP bar + tier track (free + premium lanes), claim buttons.
     Tier rewards are queued to ak_grants by the server and applied via the shared
     AKSocial.claimGrants() (the grants rail built for donations).
   XS-safe mk() builder (no innerHTML). Include AFTER social.js.
   ========================================================================== */
(function (global) {
  "use strict";

  var P = { season: 1, maxTier: 30, xpPer: 100, xp: 0, tier: 0, premium: false, cf: [], cp: [], track: null, booted: false };

  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me() { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }

  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") e[k] = v; else e.setAttribute(k, v);
    });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
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
    if (r.kind === "scrap") return "🔩 " + r.amount + " " + (r.rarity || "");
    if (r.kind === "chest") return "📦 " + (r.card_id || "") + " chest";
    if (r.kind === "keys") return "🔑 " + r.amount + " key" + (r.amount > 1 ? "s" : "");
    if (r.kind === "card") return "🃏 " + (r.card_id || "card") + " x" + r.amount;
    return r.kind;
  }

  function injectCss() {
    if (document.getElementById("ak-pass-css")) return;
    var st = document.createElement("style"); st.id = "ak-pass-css";
    st.textContent = [
      "#ak-pass{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-pass.open{display:flex}",
      ".akp-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,0.18)}",
      ".akp-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#c9a84c;flex:1}",
      ".akp-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}",
      ".akp-hd{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.06)}",
      ".akp-bar{height:10px;border-radius:6px;background:rgba(255,255,255,0.1);overflow:hidden;margin:6px 0}",
      ".akp-fill{height:100%;background:linear-gradient(90deg,#c9a84c,#cf9b22)}",
      ".akp-prem{margin-top:8px;display:flex;gap:8px;align-items:center}",
      ".akp-prem .pill{flex:1;font-size:11px;color:#9a9aa6}",
      ".akp-btn{background:linear-gradient(180deg,#c9a84c,#cf9b22);color:#1a1405;border:0;border-radius:8px;padding:8px 12px;font-weight:800;font-size:12px;cursor:pointer}",
      ".akp-btn[disabled]{opacity:.45}.akp-btn.lock{background:rgba(255,255,255,0.06);color:#9a9aa6;border:1px solid rgba(255,255,255,0.12)}",
      ".akp-body{flex:1;overflow-y:auto;padding:8px 10px}",
      ".akp-tier{display:grid;grid-template-columns:38px 1fr 1fr;gap:8px;align-items:center;padding:7px 4px;border-bottom:1px solid rgba(255,255,255,0.05)}",
      ".akp-tier.cur{background:rgba(201,168,76,0.07);border-radius:8px}",
      ".akp-tn{font-weight:800;color:#c9a84c;text-align:center}",
      ".akp-cell{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:6px 8px;font-size:12px;display:flex;flex-direction:column;gap:4px}",
      ".akp-cell.locked{opacity:.4}.akp-cell.claimed{border-color:rgba(95,211,95,0.4)}",
      ".akp-lane{font-size:9px;letter-spacing:1px;color:#8a8a96}",
      ".akp-done{color:#5fd35f;font-size:11px;font-weight:700}",
      ".akp-note{color:#9a9aa6;font-size:12px;text-align:center;padding:18px}",
      ".akp-toast{position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:#1a1a22;color:#c9a84c;border:1px solid rgba(201,168,76,0.4);padding:9px 16px;border-radius:20px;z-index:71;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none}",
      ".akp-toast.show{opacity:1}",
    ].join("");
    document.head.appendChild(st);
  }

  var root, hd, bodyEl, toastEl;
  function buildShell() {
    if (root) return;
    injectCss();
    var x = mk("button", { class: "akp-x", type: "button", text: "×", onclick: close });
    var top = mk("div", { class: "akp-top" }, [mk("h2", { text: "ALLEY PASS -- Season 1" }), x]);
    hd = mk("div", { class: "akp-hd" });
    bodyEl = mk("div", { class: "akp-body" });
    root = mk("section", { id: "ak-pass" }, [top, hd, bodyEl]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "akp-toast" }); document.body.appendChild(toastEl);
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }

  function open() { buildShell(); root.classList.add("open"); load(); }
  function close() { if (root) root.classList.remove("open"); }

  function load() {
    if (!me()) { renderSignedOut(); return; }
    setKids(bodyEl, mk("div", { class: "akp-note", text: "Loading your pass..." }));
    call("ak-pass", { action: "get" }).then(function (r) {
      if (!r || !r.ok) { setKids(bodyEl, mk("div", { class: "akp-note", text: r && r.error ? r.error : "Could not load" })); return; }
      P.season = r.season; P.maxTier = r.max_tier; P.xpPer = r.xp_per_tier;
      P.xp = r.xp; P.tier = r.tier; P.premium = r.premium;
      P.cf = r.claimed_free || []; P.cp = r.claimed_prem || []; P.track = r.track;
      render();
    });
  }
  function renderSignedOut() {
    setKids(hd, mk("div", { class: "akp-note", text: "Sign in to start your Alley Pass -- every match levels it up." }));
    setKids(bodyEl, mk("button", { class: "akp-btn", style: "display:block;margin:14px auto", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } }));
  }

  function render() {
    var intoTier = P.xp - P.tier * P.xpPer;
    var pct = P.tier >= P.maxTier ? 100 : Math.max(0, Math.min(100, Math.round(intoTier / P.xpPer * 100)));
    var premCta = P.premium
      ? mk("span", { class: "akp-done", text: "PREMIUM ACTIVE" })
      : mk("button", { class: "akp-btn", text: "Unlock Premium (800 💎)", onclick: function () {
          if (global.confirm && !confirm("Unlock the Premium Alley Pass for 800 gems? Finish the season and you earn it back and then some.")) return;
          call("ak-pass", { action: "unlock-premium" }).then(function (r) {
            if (r && r.ok) { P.premium = true; toast("Premium unlocked!"); load(); }
            else if (r && r.needsGems) { toast("Need " + (r.need || 800) + " gems -- grab a pack in the Shop."); }
            else { toast(r && r.error ? r.error : "could not unlock"); }
          });
        } });
    setKids(hd, [
      mk("div", { class: "akp-prem" }, [
        mk("div", { style: "font-weight:800;color:#fff", text: "Tier " + P.tier + " / " + P.maxTier }),
        mk("div", { class: "pill", style: "text-align:right", text: P.tier >= P.maxTier ? "season maxed" : (intoTier + " / " + P.xpPer + " XP") }),
      ]),
      mk("div", { class: "akp-bar" }, mk("div", { class: "akp-fill", style: "width:" + pct + "%" })),
      mk("div", { class: "akp-prem" }, [mk("span", { class: "pill", text: "Free lane is yours. Premium doubles the haul." }), premCta]),
    ]);
    if (!P.track) { setKids(bodyEl, mk("div", { class: "akp-note", text: "No track" })); return; }
    var rows = [];
    for (var t = 1; t <= P.maxTier; t++) rows.push(tierRow(t));
    setKids(bodyEl, rows);
    // scroll current tier into view
    var cur = bodyEl.querySelector(".akp-tier.cur"); if (cur) try { cur.scrollIntoView({ block: "center" }); } catch (_) {}
  }

  function tierRow(t) {
    return mk("div", { class: "akp-tier" + (t === P.tier + 1 ? " cur" : "") }, [
      mk("div", { class: "akp-tn", text: String(t) }),
      laneCell(t, "free"),
      laneCell(t, "prem"),
    ]);
  }
  function laneCell(t, lane) {
    var reward = P.track[lane][t - 1];
    var reached = t <= P.tier;
    var claimedArr = lane === "prem" ? P.cp : P.cf;
    var claimed = claimedArr.indexOf(t) >= 0;
    var kids = [mk("div", { class: "akp-lane", text: lane === "prem" ? "PREMIUM" : "FREE" }), mk("div", { text: rewardLabel(reward) })];
    if (claimed) kids.push(mk("div", { class: "akp-done", text: "✓ claimed" }));
    else if (!reached) kids.push(mk("button", { class: "akp-btn lock", disabled: "1", text: "🔒 tier " + t }));
    else if (lane === "prem" && !P.premium) kids.push(mk("button", { class: "akp-btn lock", text: "🔒 premium", onclick: function () { toast("Unlock premium up top"); } }));
    else {
      var b = mk("button", { class: "akp-btn", text: "Claim" });
      b.onclick = function () { b.disabled = true; claimTier(t, lane, b); };
      kids.push(b);
    }
    return mk("div", { class: "akp-cell" + (claimed ? " claimed" : (reached ? "" : " locked")) }, kids);
  }
  function claimTier(t, lane, btn) {
    call("ak-pass", { action: "claim-tier", tier: t, lane: lane }).then(function (r) {
      if (!r || !r.ok) { toast(r && r.error ? r.error : "could not claim"); if (btn) btn.disabled = false; return; }
      (lane === "prem" ? P.cp : P.cf).push(t);
      toast("Claimed " + rewardLabel(r.reward));
      try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_) {}
      render();
    });
  }

  // ---- match XP hook (called from grantMatchRewards) ------------------------
  function reportMatch(won, gates) {
    if (!me()) return;
    call("ak-pass", { action: "report-match", won: !!won, gates: gates || 0 }).then(function (r) {
      if (r && r.ok && r.awarded > 0) { try { toast("Alley Pass +" + r.awarded + " XP"); } catch (_) {} }
    });
  }

  function wire() {
    if (P.booted) return; P.booted = true;
    var btn = document.getElementById("passbtn");
    if (btn) btn.addEventListener("click", open);
    global.AKPass = { open: open, close: close, reportMatch: reportMatch };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})(typeof window !== "undefined" ? window : this);
