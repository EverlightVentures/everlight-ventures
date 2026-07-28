/* ==========================================================================
   ALLEY KINGZ -- ALLEY PASS (battle pass) UI. Self-mounting (like social.js).
   - reportMatch(won,gates): fires ak-pass report-match (server awards capped XP).
     Called once per match from grantMatchRewards (AK-PASS hook in index.html).
   - Pass screen: XP bar + tier track (free + premium lanes), claim buttons.
     Tier rewards are queued to ak_grants by the server and applied via the shared
     AKSocial.claimGrants() (the grants rail built for donations).
   - AK-PASSXP 2026-07-18: reportEvent() is the allowlist-gated front door for
     NON-match play events, and the pass now wears the live season chapter.
   CLAIM LEDGER IS SERVER SIDE. The client never grants itself a tier: every
   claim round-trips ak-pass claim-tier, which re-checks tier reached, premium
   ownership and the claimed_free/claimed_prem arrays before it writes ak_grants.
   P.tier here is a DISPLAY cache of the server value and is never computed from
   local XP, so tampering with it buys nothing.
   XS-safe mk() builder (no innerHTML). Include AFTER social.js.
   ========================================================================== */
(function (global) {
  "use strict";

  var P = { season: 1, maxTier: 30, xpPer: 100, xp: 0, tier: 0, premium: false, cf: [], cp: [], track: null, booted: false, synced: false };

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

  // ---- AK-PASSXP 2026-07-18: ONE copy of the server XP curve ----------------
  // Mirrored from supabase/functions/ak-pass/index.ts (XP_PER_TIER 100, MAX_TIER
  // 30, tierFor = floor(xp / xpPer) clamped 0..MAX_TIER). Display + gating math
  // only; the server recomputes it on every claim, so these never grant anything.
  function tierFor(xp) { var t = Math.floor((xp | 0) / (P.xpPer || 100)); return Math.max(0, Math.min(P.maxTier || 30, t)); }
  function xpForTier(t) { return Math.max(0, Math.min(P.maxTier || 30, t | 0)) * (P.xpPer || 100); }
  function xpToNext(xp) { var t = tierFor(xp); return t >= (P.maxTier || 30) ? 0 : xpForTier(t + 1) - (xp | 0); }

  // ---- AK-PASSPACE 2026-07-18: "can I still finish this chapter?" ----------
  // Built from the REAL server faucet, not a guess: a match pays (won?30:10) + 5
  // per gate with gates clamped 0..4, so 50 XP is the per-match ceiling, and the
  // server stops paying at DAILY_CAP 300 XP/day (ak-pass/index.ts:15,83-88).
  // A full season is maxTier * xpPer = 3000 XP, so 10 capped days clears it and a
  // 42-day chapter (seasons.js PERIOD_MS) leaves 32 days of slack.
  // Pure math: no DOM, no network, no writes. systems/seasons.js renderPass()
  // calls this to put the pace line on the chapter card.
  var MATCH_XP_MAX = 50, DAILY_XP_CAP = 300;
  function paceToFinish(days, xp) {
    var total = (P.maxTier || 30) * (P.xpPer || 100);
    var have = (typeof xp === "number") ? xp : (P.xp | 0);
    var need = Math.max(0, total - have);
    days = Math.max(0, days | 0);
    if (!need) return { need: 0, days: days, perDay: 0, matchesPerDay: 0, minDays: 0, onPace: true };
    var minDays = Math.ceil(need / DAILY_XP_CAP);          // floor set by the daily cap
    var perDay = days ? Math.ceil(need / days) : need;     // 0 days left -> it all lands today or never
    return { need: need, days: days, perDay: perDay,
             matchesPerDay: Math.ceil(Math.min(perDay, DAILY_XP_CAP) / MATCH_XP_MAX),
             minDays: minDays, onPace: days >= minDays && perDay <= DAILY_XP_CAP };
  }

  // ---- AK-PASSXP 2026-07-18: the play-event -> XP rail, allowlist-gated -----
  // AUDIT (traced, real files): systems/missions.js:253 feedPassRail() fires
  // AKQuests.reportEvent(def.metric, 1) with duty_tower / duty_raid / duty_watch;
  // systems/encounters.js:373,950 fire captures / street_event; systems/karma.js:335,350
  // fire karma_recruit; social.js:600 fires raided. game/quests.js:121 posts ALL of
  // them straight through to ak-quests report-event, which allowlists donates|chats
  // ONLY (supabase/functions/ak-quests/index.ts:74) and answers everything else
  // 400 "bad metric". quests.js swallows the rejection, so those 7 metrics burned a
  // round trip each and landed ZERO pass XP, silently.
  // This gate mirrors the server allowlist exactly: an unsupported metric is
  // COUNTED locally and never fired. Widen EVENT_METRICS only in lockstep with
  // the ak-quests allowlist AND the ak_period_stats columns bump() writes (:60).
  var EVENT_METRICS = { donates: 1, chats: 1 };   // exact mirror of ak-quests report-event
  var droppedEvents = {};                         // metric -> refusals (read via AKPass.xpAudit)
  function reportEvent(metric, n) {
    metric = String(metric || "");
    n = Math.max(1, Math.min(20, (n | 0) || 1));  // same clamp the server applies
    if (!EVENT_METRICS[metric]) { droppedEvents[metric] = (droppedEvents[metric] | 0) + 1; return false; }
    if (!me()) return false;
    call("ak-quests", { action: "report-event", metric: metric, n: n });
    return true;
  }

  // ---- AK-PASSGUARD 2026-07-18: the gate applied to the LIVE rail ----------
  // The duty / encounter / karma callers above do NOT go through AKPass.reportEvent
  // -- they hold AKQuests.reportEvent directly. So the allowlist is wrapped ONTO
  // the live function instead of waiting for 6 call sites to be re-pointed.
  // Dropping is the honest behaviour: no accepted metric describes a duty, a
  // capture or a recruit, so re-pointing one would corrupt a real quest counter
  // (bump() at ak-quests:60 writes matches/wins/gates/donates/chats and nothing
  // else). Duty XP only starts landing when the SERVER allowlist widens -- see
  // needs_from_others. Until then the refusals are COUNTED, not silent: read them
  // with AKPass.xpAudit().dropped.
  // Ordering: pass.js loads BEFORE quests.js on both pages (index.html:3549/3550,
  // game.html:2449/2450), so global.AKQuests does not exist yet at wire() time.
  // Deferring one task lets every DOMContentLoaded handler run first.
  function installQuestGuard() {
    var Q = global.AKQuests;
    if (!Q || typeof Q.reportEvent !== "function" || Q.reportEvent._akGated) return false;
    var inner = Q.reportEvent;
    function gated(metric, n) {
      metric = String(metric || "");
      if (!EVENT_METRICS[metric]) { droppedEvents[metric] = (droppedEvents[metric] | 0) + 1; return false; }
      inner(metric, Math.max(1, Math.min(20, (n | 0) || 1)));
      return true;
    }
    gated._akGated = 1;
    Q.reportEvent = gated;
    return true;
  }

  // ---- AK-PARITY 2026-07-18: season rewards pay flex or currency, never power
  // The ladder already ranks on card level + Town Hall. Anything that upgrades or
  // hands over cards is POWER: scrap is upgrade material, chests and cards ARE
  // cards, keys open chests. gold is the soft currency. Cosmetics are pure flex.
  var POWER_KINDS = { scrap: 1, chest: 1, card: 1, keys: 1 };
  var COSMETIC_KINDS = { frame: 1, banner: 1, aura: 1, trail: 1, skin: 1 };
  function rewardClass(r) {
    if (!r || !r.kind) return "none";
    if (COSMETIC_KINDS[r.kind]) return "cosmetic";
    if (POWER_KINDS[r.kind]) return "power";
    return "currency";
  }
  // auditTrack(): count the parity break on the LIVE server track. Free-lane power
  // is symmetric (every player gets it) so it is fair; PREMIUM-lane power is SOLD
  // for 800 gems and is the part that breaks raid fairness. paidPower > 0 means
  // the track needs the server-side fix, not a client patch.
  function auditTrack(track) {
    track = track || P.track;
    var out = { free: [], prem: [], paidPower: 0 };
    if (!track) return out;
    ["free", "prem"].forEach(function (lane) {
      var arr = track[lane] || [];
      for (var i = 0; i < arr.length; i++) {
        if (rewardClass(arr[i]) !== "power") continue;
        out[lane].push(i + 1);
        if (lane === "prem") out.paidPower++;
      }
    });
    return out;
  }
  // AK-PARITY 2026-07-18: run the audit ONCE per session the moment the live
  // track lands (load()). The client cannot fix it -- claim-tier grants from the
  // server's own TRACK const -- so it reports instead of pretending. Console only,
  // never player-facing noise.
  var _parityWarned = false;
  function warnParityOnce() {
    if (_parityWarned || !P.track) return;
    _parityWarned = true;
    var a = auditTrack(P.track);
    if (a.paidPower > 0 && global.console && console.warn) {
      console.warn("[AKPass] parity: the PREMIUM lane sells power on " + a.paidPower +
        " of " + (P.maxTier | 0) + " tiers (" + a.prem.join(",") + "). ak-pass TRACK needs those swapped to cosmetic/gold.");
    }
  }

  // ---- AK-SEASONCHAPTER 2026-07-18: the pass wears the live chapter ---------
  // systems/seasons.js owns the 6-week chapter cadence. When it is on the page the
  // pass titles itself with the live chapter + week instead of a hardcoded label.
  // Absent (battler page, node harness) -> the plain season label, never a throw.
  function chapterInfo() {
    try { var S = global.AKSeasons; if (S && S.current) { var c = S.current(); if (c && c.name) return c; } } catch (_) {}
    return null;
  }
  function passTitle() { var c = chapterInfo(); return c ? ("ALLEY PASS -- " + c.name) : ("ALLEY PASS -- Season " + P.season); }
  function passSub() {
    var c = chapterInfo(); if (!c) return "";
    return "Week " + c.week + " of 6 -- " + c.daysLeft + " day" + (c.daysLeft === 1 ? "" : "s") + " left";
  }

  function injectCss() {
    if (document.getElementById("ak-pass-css")) return;
    var st = document.createElement("style"); st.id = "ak-pass-css";
    st.textContent = [
      "#ak-pass{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);color:#e9e9ee;font-family:inherit}",
      "#ak-pass.open{display:flex}",
      ".akp-top{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,0.18)}",
      ".akp-top h2{margin:0;font-size:16px;letter-spacing:1px;color:#c9a84c}",
      ".akp-ttl{flex:1}",
      ".akp-sub{font-size:10px;letter-spacing:.05em;color:#9a9aa6;margin-top:2px}",
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

  var root, hd, bodyEl, toastEl, titleEl, subEl;
  function buildShell() {
    if (root) return;
    injectCss();
    var x = mk("button", { class: "akp-x", type: "button", text: "×", onclick: close });
    // AK-SEASONCHAPTER 2026-07-18: title + week line are re-stamped by render()
    titleEl = mk("h2", { text: passTitle() });
    subEl = mk("div", { class: "akp-sub", text: passSub() });
    var top = mk("div", { class: "akp-top" }, [mk("div", { class: "akp-ttl" }, [titleEl, subEl]), x]);
    hd = mk("div", { class: "akp-hd" });
    bodyEl = mk("div", { class: "akp-body" });
    root = mk("section", { id: "ak-pass" }, [top, hd, bodyEl]);
    document.body.appendChild(root);
    toastEl = mk("div", { class: "akp-toast" }); document.body.appendChild(toastEl);
  }
  function toast(m) { if (!toastEl) return; toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2200); }
  // AK-PASSXP 2026-07-18: the pass shell is NOT mounted on the battler page (the
  // player never opened it), so a match-end tier-up had nowhere to show. Fall back
  // to the host banner when it exists, stay silent when neither is there.
  function notify(m, secs) {
    if (toastEl) { toast(m); return; }
    try { if (typeof global.showBanner === "function") global.showBanner(m, secs || 2); } catch (_) {}
  }

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
      P.synced = true;                              // AK-PASSXP: server truth is in hand
      warnParityOnce();                             // AK-PARITY: audit the LIVE track once
      render();
    });
  }
  function renderSignedOut() {
    setKids(hd, mk("div", { class: "akp-note", text: "Sign in to start your Alley Pass -- every match levels it up." }));
    setKids(bodyEl, mk("button", { class: "akp-btn", style: "display:block;margin:14px auto", text: "SIGN IN WITH GOOGLE", onclick: function () { try { global.AKAccount.signIn(); } catch (_) {} } }));
  }

  function render() {
    // AK-SEASONCHAPTER 2026-07-18: re-stamp the chapter each open (a chapter can
    // roll while the tab sits idle; seasons.js is the clock, this only reads it).
    if (titleEl) titleEl.textContent = passTitle();
    if (subEl) subEl.textContent = passSub();
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
  // THE live XP faucet: game/game.html:8146 fires this once per match behind the
  // g._rewarded guard. The server owns the award (won ? 30 : 10, +5 per gate, 300
  // XP/day cap) so the client posts the result and nothing else.
  function reportMatch(won, gates) {
    if (!me()) return;
    call("ak-pass", { action: "report-match", won: !!won, gates: gates || 0 }).then(function (r) {
      if (!r || !r.ok) return;
      // AK-PASSXP 2026-07-18: cache the SERVER tier (never tierFor(P.xp) locally)
      // and call the tier-up. First sync is silent: before is -1 until the client
      // has real server state, so an unopened pass cannot fake a tier-up banner.
      var before = P.synced ? (P.tier | 0) : -1;
      if (typeof r.xp === "number") P.xp = r.xp;
      if (typeof r.tier === "number") P.tier = r.tier;
      P.synced = true;
      if (r.awarded > 0) notify("Alley Pass +" + r.awarded + " XP");
      if (before >= 0 && (P.tier | 0) > before) notify("ALLEY PASS TIER " + P.tier + " -- reward ready", 2.6);
    });
  }

  // ---- AK-PASSXP 2026-07-18: read-only progress for systems/seasons.js ------
  // seasons.js renderPass() shows live tier/XP on the chapter card. Returns the
  // cached SERVER state; synced=false means nothing has been fetched yet.
  function progress() {
    return { season: P.season, tier: P.tier | 0, maxTier: P.maxTier | 0, xp: P.xp | 0,
             xpPer: P.xpPer | 0, toNext: xpToNext(P.xp), premium: !!P.premium, synced: !!P.synced };
  }
  // diagnostics: which metrics this client refused, and where the live server
  // track sells power on the paid lane. Both are read-only.
  function xpAudit() {
    var d = {}; Object.keys(droppedEvents).forEach(function (k) { d[k] = droppedEvents[k]; });
    return { allowed: Object.keys(EVENT_METRICS), dropped: d, track: auditTrack() };
  }

  function wire() {
    if (P.booted) return; P.booted = true;
    // AK-PASSXP 2026-07-18: DOM is optional here so the module exports headlessly
    // (node parse/proof harness) instead of throwing on getElementById.
    if (typeof document !== "undefined") {
      var btn = document.getElementById("passbtn");
      if (btn) btn.addEventListener("click", open);
    }
    global.AKPass = { open: open, close: close, reportMatch: reportMatch, reportEvent: reportEvent,
                      progress: progress, tierFor: tierFor, xpForTier: xpForTier, xpToNext: xpToNext,
                      paceToFinish: paceToFinish, installQuestGuard: installQuestGuard,
                      rewardClass: rewardClass, auditTrack: auditTrack, xpAudit: xpAudit };
    // AK-PASSGUARD 2026-07-18: quests.js wires on the SAME DOMContentLoaded and is
    // included after us, so AKQuests appears later in this same task. One deferred
    // tick puts the allowlist on the live rail. Re-tried once in case a page
    // injects quests.js late; installQuestGuard is idempotent (_akGated).
    if (typeof setTimeout === "function") { setTimeout(installQuestGuard, 0); setTimeout(installQuestGuard, 1500); }
  }
  // AK-PASSXP 2026-07-18: boot only where there is a document; headless still
  // exports AKPass so the curve/track math is testable outside a browser.
  if (typeof document === "undefined") wire();
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})(typeof window !== "undefined" ? window : globalThis);
