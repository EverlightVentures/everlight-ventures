/* ==========================================================================
   ALLEY KINGZ -- systems/ladder.js  (CAPTIVATION P10: THE COMPETITIVE LADDER)
   The "Block Ladder" overlay -- the Merge-Tactics "earn the exclusive before the
   reset" pull, rendered MOBA/Brawl-Stars style. READ-ONLY UI; this module never
   writes the profile, so zero-state stays byte-identical (no mutateProfile here).

   What it shows (one gold-cyberpunk overlay, mirrors social.js / trading.js):
     - HERO ........ the player's RANK + live BLOCK REP (AK_ECON.blockRep/repRank),
                     clan colors, current ladder place.
     - RESET ....... the MONTHLY soft-reset countdown (AK_ECON.repSeasonResetMs),
                     deterministic-by-time, anchored to LOCAL PT (1st of month 00:00).
     - EXCLUSIVE ... the SEASONAL EXCLUSIVE dog + Rep progress toward unlocking it
                     (AK_ECON.seasonalExclusive). PARITY HARD-LAW: cosmetic / free-
                     track / bones-earned -- NEVER raw power, NEVER gem-gated.
     - LADDER ...... the 7-rung CANON ladder (Stray -> Pup -> Runner -> Warrior ->
                     Enforcer -> Right Paw -> King of the Block) with the player marked.
     - BOARD ....... a populated leaderboard (AK_POPULATION.leaderboard()).

   Canon-only names. The Old Pack / the Mongrel King flavor. 9 districts via pop.
   engine.js (the tower lane) is FROZEN + untouched -- this is the meta layer only.
   XSS-safe by construction (mk() -> textContent; no innerHTML). No em-dashes (use --).
   Self-contained: graceful when AK_ECON / AK_POPULATION helpers are absent.
   Exposes: window.akOpenLadder() + window.AKLadder.
   Include AFTER economy.js + population.js (degrades fine in any order).
   ========================================================================== */
(function (global) {
  "use strict";

  // ---- CANON 7-rung ladder (floors MIRROR economy.js rankDivision + population RANK_FLOOR) ----
  var RANKS = [
    { name: "Stray",             min: 0,    glyph: "○" }, // open ring -- no colors
    { name: "Pup",               min: 200,  glyph: "◉" },
    { name: "Runner",            min: 500,  glyph: "◈" },
    { name: "Warrior",           min: 1000, glyph: "✦" },
    { name: "Enforcer",          min: 1800, glyph: "✧" },
    { name: "Right Paw",         min: 3000, glyph: "✪" },
    { name: "King of the Block", min: 5000, glyph: "♛" }  // the crown
  ];
  // Fallback clan colors (canon) when the population row carries none.
  var CLAN_COLOR = {
    zoomie_syndicate: "#FF2E88", leashbreak_tactix: "#7B5CFF",
    boneguard_crew: "#C9772E", k9_circuitry: "#00E0C0", stray: "#c9a84c"
  };
  // Cosmetic seasonal-exclusive dog names -- rotate by PT month so a NEW skin is up
  // each monthly reset. SKINS, not stats (parity). Canon clan/rank flavor.
  var EXCLUSIVE_POOL = [
    "Dawnbreak King", "Chrome Stray", "Goldfang Runner", "Circuit Hound",
    "Ember Boneguard", "Voltaic Zoomie", "Phantom Leashbreaker", "Crowned Cur",
    "Static Pup", "Aurum Enforcer", "Ghostlight Warrior", "Neon Mongrel"
  ];
  var MONTHS = ["JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"];
  var EXCLUSIVE_DEFAULT_REP = 1800;   // default "earn before reset" target = Enforcer rung (reachable in a month)

  // ---- safe accessors --------------------------------------------------------
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function pop()  { try { return global.AK_POPULATION || null; } catch (_) { return null; } }
  function num(v, d) { v = +v; return isFinite(v) ? v : (d || 0); }
  function myName() { try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24) || "Stray"; } catch (_) { return "Stray"; } }
  // Read a helper that may be a function OR a plain value OR a profile field.
  function readEcon(key, profKey, dflt) {
    var e = econ();
    try {
      if (e && typeof e[key] === "function") { var v = e[key](); if (v != null) return v; }
      else if (e && e[key] != null && typeof e[key] !== "function") return e[key];
    } catch (_) {}
    if (profKey) { try { var p = e && e.loadProfile && e.loadProfile(); if (p && p[profKey] != null) return p[profKey]; } catch (_) {} }
    return dflt;
  }

  // BLOCK REP: dedicated helper -> profile.blockRep -> p.trophies (the shipped shared
  // ladder doubles as Block Rep until the P10 econ helper lands). Always a number.
  function blockRep() {
    var v = readEcon("blockRep", "blockRep", null);
    if (v != null) return Math.max(0, num(v, 0) | 0);
    try { var p = econ() && econ().loadProfile && econ().loadProfile(); if (p) return Math.max(0, (p.trophies | 0)); } catch (_) {}
    return 0;
  }
  function rankIdxFor(rep) { var r = 0; for (var i = 0; i < RANKS.length; i++) if (rep >= RANKS[i].min) r = i; return r; }
  function repRankName(rep) {
    var v = readEcon("repRank", "repRank", null);
    if (typeof v === "string" && v) return v;
    return RANKS[rankIdxFor(rep)].name;
  }

  // ---- LOCAL PT clock (deterministic; mirrors daynight.js ptParts) -----------
  // The monthly reset fires on the 1st at 00:00 PT for ALL players (parity-safe).
  function ptNowParts(now) {
    now = (now == null) ? Date.now() : now;
    try {
      var f = ptNowParts._f || (ptNowParts._f = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/Los_Angeles", hour12: false,
        year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit"
      }));
      var o = {}, parts = f.formatToParts(new Date(now));
      for (var i = 0; i < parts.length; i++) { if (parts[i].type !== "literal") o[parts[i].type] = parseInt(parts[i].value, 10); }
      if (o.hour === 24) o.hour = 0;                  // Intl edge: 24:00 -> 00:00
      return o;
    } catch (_) {
      var d = new Date(now - 8 * 3600000);            // PST (UTC-8) fallback
      return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1, day: d.getUTCDate(), hour: d.getUTCHours(), minute: d.getUTCMinutes(), second: d.getUTCSeconds() };
    }
  }
  // ms until the next PT 1st-of-month midnight. Diff is computed in wall-clock
  // space so the device offset cancels -- a pure function of the PT calendar clock.
  function msToMonthResetPT(now) {
    var o = ptNowParts(now);
    var wallNow = Date.UTC(o.year, o.month - 1, o.day, o.hour, o.minute, o.second);
    var nextStart = Date.UTC(o.year, o.month, 1, 0, 0, 0);   // o.month (1-based) == next month 0-based; Date.UTC rolls Dec->Jan
    return Math.max(0, nextStart - wallNow);
  }
  function seasonResetMs() {
    var v = readEcon("repSeasonResetMs", "repSeasonResetMs", null);
    if (v != null && isFinite(+v)) return Math.max(0, +v | 0);
    return msToMonthResetPT();
  }
  function seasonLabel() { var o = ptNowParts(); return (MONTHS[(o.month - 1) % 12] || "SEASON") + " SEASON"; }

  // ---- SEASONAL EXCLUSIVE (cosmetic; parity hard-law) ------------------------
  function seasonalExclusive() {
    var v = readEcon("seasonalExclusive", "seasonalExclusive", null);
    var o = ptNowParts();
    var fallbackName = EXCLUSIVE_POOL[(o.month - 1) % EXCLUSIVE_POOL.length];
    var ex;
    if (v && typeof v === "object") {
      ex = {
        name: String(v.name || v.card || fallbackName),
        repNeeded: Math.max(1, num(v.repNeeded != null ? v.repNeeded : (v.rep != null ? v.rep : EXCLUSIVE_DEFAULT_REP), EXCLUSIVE_DEFAULT_REP) | 0),
        rarity: v.rarity || "Seasonal",
        glyph: v.glyph || "✨",
        desc: v.desc || null,
        unlocked: v.unlocked === true || null
      };
    } else if (typeof v === "string" && v) {
      ex = { name: v, repNeeded: EXCLUSIVE_DEFAULT_REP, rarity: "Seasonal", glyph: "✨", desc: null, unlocked: null };
    } else {
      ex = { name: fallbackName, repNeeded: EXCLUSIVE_DEFAULT_REP, rarity: "Seasonal", glyph: "✨", desc: null, unlocked: null };
    }
    var rep = blockRep();
    if (ex.unlocked == null) ex.unlocked = rep >= ex.repNeeded;
    ex.rep = rep;
    ex.pct = ex.repNeeded > 0 ? Math.max(0, Math.min(1, rep / ex.repNeeded)) : 1;
    ex.toGo = Math.max(0, ex.repNeeded - rep);
    return ex;
  }

  // ---- player snapshot (rep/rank from econ; place from the live board) -------
  function leaderboardRows() {
    var p = pop();
    try { if (p && typeof p.leaderboard === "function") { var r = p.leaderboard(); if (Array.isArray(r)) return r; } } catch (_) {}
    return [];
  }
  function playerSnapshot(rows) {
    var rep = blockRep(), rank = repRankName(rep);
    var snap = { name: myName(), rep: rep, rank: rank, place: null, clan: "stray", clanName: "Stray", color: CLAN_COLOR.stray };
    var you = null;
    for (var i = 0; i < rows.length; i++) { if (rows[i] && rows[i].isYou) { you = rows[i]; break; } }
    if (you) {
      snap.place = you.place || null;
      snap.clan = you.clan || "stray";
      snap.clanName = you.clanName || "Stray";
      snap.color = you.color || CLAN_COLOR[snap.clan] || CLAN_COLOR.stray;
      if (!rep && (you.trophies | 0)) { snap.rep = you.trophies | 0; snap.rank = repRankName(snap.rep); }
    }
    return snap;
  }

  // ---- countdown formatting --------------------------------------------------
  function splitMs(ms) {
    if (ms == null || ms < 0) ms = 0;
    var s = Math.floor(ms / 1000);
    var d = Math.floor(s / 86400); s -= d * 86400;
    var h = Math.floor(s / 3600);  s -= h * 3600;
    var m = Math.floor(s / 60);    s -= m * 60;
    return { d: d, h: h, m: m, s: s };
  }
  function pad2(n) { n = n | 0; return n < 10 ? "0" + n : "" + n; }

  // ---- safe DOM builder (no innerHTML -- dynamic text via textContent) --------
  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
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
  function setKids(el, nodes) { if (el) el.replaceChildren.apply(el, [].concat(nodes).filter(function (n) { return n != null; })); }

  // ---- CSS (gold-cyberpunk; self-contained so it themes without shop.css) ----
  function injectCss() {
    if (document.getElementById("ak-ladder-css")) return;
    var st = document.createElement("style"); st.id = "ak-ladder-css";
    st.textContent = [
      // THE LADDER -- engraved trophy plate on matte steel. SVG grain (--grain ~.06) + brushed
      // metal. ONE focal: the player's rank badge + name (oversized, the only glow). Countdown
      // reads like a stamped deadline; the seasonal dog is framed like a prize. No gradient-text
      // on numbers, no circle clan dots, no glossy pills.
      "#ak-ladder{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;color:#ece7da;font-family:'Inter',system-ui,sans-serif;--grain:url(\"data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='140'%20height='140'%3E%3Cfilter%20id='g'%3E%3CfeTurbulence%20type='fractalNoise'%20baseFrequency='0.9'%20numOctaves='2'%20stitchTiles='stitch'/%3E%3C/filter%3E%3Crect%20width='100%25'%20height='100%25'%20filter='url(%23g)'%20opacity='0.06'/%3E%3C/svg%3E\");background:var(--grain) repeat,linear-gradient(165deg,#15131c,#0A0A0A)}",
      "#ak-ladder.open{display:flex}",
      "#ak-ladder::before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.3;background:repeating-linear-gradient(0deg,rgba(201,168,76,.04) 0,rgba(201,168,76,.04) 1px,transparent 1px,transparent 3px)}",
      // header -- worn steel slab, gold left rule, Cinzel skewed engraved stamp (no gradient-text)
      ".akl-top{position:relative;z-index:1;display:flex;align-items:flex-start;gap:11px;padding:14px 15px 13px;border-bottom:1px solid #2a2620;background:var(--grain) repeat,linear-gradient(180deg,#1b1822,#100e15);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),inset 0 -12px 20px rgba(0,0,0,.42)}",
      ".akl-top h2{margin:0;flex:1;min-width:0;padding-left:11px;border-left:3px solid #c9a84c;font-family:'Cinzel',Georgia,serif;font-weight:900;font-size:18px;letter-spacing:.04em;text-transform:uppercase;color:#e8c55a;transform:skewX(-5deg);text-shadow:0 1px 0 #000,0 2px 0 rgba(0,0,0,.55),0 3px 6px rgba(0,0,0,.65)}",
      ".akl-top small{display:block;font-family:'Inter',sans-serif;font-weight:700;font-size:8.5px;letter-spacing:.18em;color:#8f8463;transform:skewX(-5deg);margin-top:3px}",
      ".akl-x{background:none;border:0;color:#9a8f6a;font-size:27px;line-height:1;cursor:pointer;padding:0 2px;align-self:flex-start}",
      ".akl-x:active{transform:scale(.9)}",
      ".akl-body{position:relative;z-index:1;flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:14px 13px 30px}",
      // brushed-metal plate -- flat: faint top rim + bottom ambient occlusion, no glow
      ".akl-card{position:relative;background:var(--grain) repeat,linear-gradient(165deg,#15131c,#0A0A0A);border:1px solid #2a2620;border-radius:3px;padding:13px;margin-bottom:13px;box-shadow:inset 0 1px 0 rgba(255,255,255,.045),inset 0 -16px 22px rgba(0,0,0,.34)}",
      ".akl-cap{font-family:'Cinzel',serif;font-weight:800;font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:#c9a84c;margin-bottom:10px;display:flex;align-items:center;gap:8px}",
      ".akl-cap::before{content:'';width:16px;height:2px;background:#c9a84c}",
      // HERO -- THE FOCAL. Oversized rank badge + name; the one element that earns a glow.
      ".akl-hero{display:flex;align-items:center;gap:14px}",
      ".akl-badge{flex:0 0 auto;width:80px;height:80px;border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(155deg,#23202c,#0c0b11);border:1.5px solid var(--clan,#c9a84c);box-shadow:0 0 22px rgba(201,168,76,.34),inset 0 1px 0 rgba(255,255,255,.06),inset 0 -10px 16px rgba(0,0,0,.55)}",
      ".akl-badge .g{font-size:34px;line-height:1;color:#f7ecca;text-shadow:0 0 12px var(--clan,#c9a84c),0 2px 2px rgba(0,0,0,.6)}",
      ".akl-hero-main{flex:1;min-width:0}",
      ".akl-hero-rank{font-family:'Cinzel',serif;font-weight:900;font-size:27px;letter-spacing:.02em;color:#fff7e6;line-height:1.05;transform:skewX(-4deg);text-shadow:0 1px 0 #000,0 2px 4px rgba(0,0,0,.6)}",
      ".akl-hero-sub{font-size:11px;color:#8f8a7a;margin-top:5px}",
      ".akl-hero-sub b{color:var(--clan,#c9a84c)}",
      ".akl-rep{flex:0 0 auto;text-align:right}",
      ".akl-rep .n{font-family:'Cinzel',serif;font-weight:900;font-size:24px;color:#e8c55a;line-height:1;font-variant-numeric:tabular-nums;text-shadow:0 1px 0 #000,0 2px 4px rgba(0,0,0,.55)}",
      ".akl-rep .l{font-size:8px;font-weight:800;letter-spacing:.2em;color:#8a7a45;text-transform:uppercase;margin-top:3px}",
      // RESET countdown -- stamped steel deadline plates (flat, engraved digits, no glow)
      ".akl-clock{display:flex;gap:7px}",
      ".akl-seg{flex:1;max-width:78px;text-align:center;padding:9px 4px;border-radius:2px;background:linear-gradient(180deg,#1a1722,#0d0b12);border:1px solid #2a2620;box-shadow:inset 0 1px 0 rgba(255,255,255,.04),inset 0 -6px 10px rgba(0,0,0,.4)}",
      ".akl-seg .v{font-family:'Cinzel',serif;font-weight:900;font-size:22px;color:#efe6c8;text-shadow:0 1px 0 #000,0 2px 3px rgba(0,0,0,.5);font-variant-numeric:tabular-nums}",
      ".akl-seg .k{font-size:8px;font-weight:800;letter-spacing:.16em;color:#8a7a45;text-transform:uppercase;margin-top:3px}",
      ".akl-reset-note{font-size:11px;color:#8f8a7a;margin-top:10px;line-height:1.45}",
      // EXCLUSIVE -- the seasonal dog framed like a prize (gold double-frame, no soft glow)
      ".akl-ex{display:flex;align-items:center;gap:13px}",
      ".akl-ex-art{flex:0 0 auto;width:58px;height:58px;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:28px;background:linear-gradient(155deg,#23202c,#0c0b11);border:1px solid #e8c55a;box-shadow:0 0 0 3px #0a0a0a,0 0 0 4px rgba(201,168,76,.45),inset 0 -8px 12px rgba(0,0,0,.5)}",
      ".akl-ex-art.locked{filter:grayscale(.55) brightness(.8);border-color:#5a5340;box-shadow:0 0 0 3px #0a0a0a,0 0 0 4px rgba(90,83,64,.5)}",
      ".akl-ex-main{flex:1;min-width:0}",
      ".akl-ex-name{font-family:'Cinzel',serif;font-weight:800;font-size:15px;color:#fff7e6;text-shadow:0 1px 0 #000}",
      ".akl-ex-tag{font-size:9px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#5fd3ff;margin-top:2px}",
      ".akl-bar{height:9px;border-radius:1px;background:#0d0b12;border:1px solid #2a2620;overflow:hidden;margin-top:9px}",
      ".akl-bar i{display:block;height:100%;background:linear-gradient(90deg,#c9a84c,#e8c55a);background-image:repeating-linear-gradient(90deg,rgba(0,0,0,.28) 0,rgba(0,0,0,.28) 1px,transparent 1px,transparent 7px),linear-gradient(90deg,#c9a84c,#e8c55a);transition:width .5s cubic-bezier(.2,.8,.2,1)}",
      ".akl-ex-prog{font-size:11px;color:#bdb79f;margin-top:7px;font-variant-numeric:tabular-nums}",
      ".akl-ex-prog b{color:#e8c55a}",
      ".akl-ex-prog.done{color:#7be08a}",
      ".akl-parity{font-size:9.5px;color:#7d7766;margin-top:8px;font-style:italic;line-height:1.45}",
      // LADDER rungs -- engraved roll, flat steel, the YOU row gets a gold edge (no heavy glow)
      ".akl-rungs{display:flex;flex-direction:column-reverse;gap:5px}",
      ".akl-rung{display:flex;align-items:center;gap:11px;padding:9px 11px;border-radius:2px;border:1px solid #211e19;background:rgba(255,255,255,.02)}",
      ".akl-rung.done{border-color:rgba(201,168,76,.22)}",
      ".akl-rung.future{opacity:.45}",
      ".akl-rung.you{border:1px solid #c9a84c;border-left:3px solid #c9a84c;background:linear-gradient(90deg,rgba(201,168,76,.16),rgba(201,168,76,.03))}",
      ".akl-rung .rg{flex:0 0 auto;width:24px;text-align:center;font-size:15px;color:#c9a84c}",
      ".akl-rung.you .rg{color:#fff1cc;text-shadow:0 0 9px #e8c55a}",
      ".akl-rung .rn{flex:1;font-family:'Cinzel',serif;font-weight:700;font-size:13px;color:#ddd6c6}",
      ".akl-rung.you .rn{color:#fff7e6}",
      ".akl-rung .rf{font-size:10px;font-weight:700;color:#8a7a45;font-variant-numeric:tabular-nums}",
      // YOU mark -- flat stamped gold tag (hard street-cut corner, no pill)
      ".akl-you-pill{font-family:'Inter',sans-serif;font-size:8px;font-weight:900;letter-spacing:.12em;color:#16110a;background:#c9a84c;border-radius:0;clip-path:polygon(4px 0,100% 0,100% 100%,0 100%,0 4px);padding:2px 7px;margin-left:7px}",
      // LEADERBOARD
      ".akl-board{display:flex;flex-direction:column;gap:3px}",
      ".akl-lrow{display:flex;align-items:center;gap:10px;padding:8px;border-radius:2px;border-bottom:1px solid #211e19}",
      ".akl-lrow.you{background:linear-gradient(90deg,rgba(201,168,76,.16),rgba(201,168,76,.03));border:1px solid #c9a84c;border-left:3px solid #c9a84c}",
      ".akl-pl{flex:0 0 auto;width:26px;text-align:center;font-family:'Cinzel',serif;font-weight:900;font-size:13px;color:#8a7a45;font-variant-numeric:tabular-nums}",
      ".akl-lrow.top .akl-pl{color:#e8c55a}",
      // clan chip -- small notched steel tab, not a circle avatar
      ".akl-dot{flex:0 0 auto;width:9px;height:9px;border-radius:1px;background:var(--c,#c9a84c);border:1px solid rgba(0,0,0,.4);box-shadow:inset 0 1px 0 rgba(255,255,255,.18)}",
      ".akl-lnm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:700;font-size:13px;color:#ddd6c6}",
      ".akl-lrow.you .akl-lnm{color:#fff7e6}",
      ".akl-lrk{flex:0 0 auto;font-size:9px;font-weight:700;letter-spacing:.05em;color:#7d7766;text-transform:uppercase}",
      ".akl-ltr{flex:0 0 auto;font-family:'Cinzel',serif;font-weight:800;font-size:13px;color:#c9a84c;font-variant-numeric:tabular-nums;min-width:42px;text-align:right}",
      ".akl-note{color:#8a8576;font-size:12px;text-align:center;padding:18px 8px;line-height:1.5}",
      // BOARD tabs -- stamped steel segmented control (The Block / Crew). Active = gold plate.
      ".akl-tabs{display:flex;gap:6px;margin-bottom:11px}",
      ".akl-tab{flex:0 0 auto;font-family:'Cinzel',serif;font-weight:800;font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#8a7a45;background:rgba(255,255,255,.02);border:1px solid #211e19;border-radius:2px;padding:6px 13px;cursor:pointer}",
      ".akl-tab.on{color:#16110a;background:#c9a84c;border-color:#c9a84c;box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}",
      ".akl-tab:active{transform:scale(.96)}",
      // PASSED-YOU toast -- mirrors trading.js/social.js pill (above the overlay)
      ".akl-toast{position:fixed;left:50%;bottom:92px;transform:translateX(-50%);background:#1a1a22;color:#e8c55a;border:1px solid rgba(201,168,76,.4);padding:9px 16px;border-radius:20px;z-index:70;font-size:13px;opacity:0;transition:opacity .2s;pointer-events:none;max-width:88vw;text-align:center}",
      ".akl-toast.show{opacity:1}",
      "@media (prefers-reduced-motion:reduce){.akl-bar i{transition:none}}"
    ].join("");
    document.head.appendChild(st);
  }

  // ---- DOM shell + section refs ----------------------------------------------
  var S = { booted: false, open: false, ticker: 0, boardTab: "global", globalRows: [], serverRows: [], myPlace: null };
  var root, bodyEl, segD, segH, segM, segS, resetNote, exBarFill, exProg, boardWrap, toastEl;
  var LAST_PLACE_KEY = "ak_ladder_last_place";   // "passed you" snapshot -- best place we last showed the player

  function buildShell() {
    if (root || typeof document === "undefined") return;
    injectCss();
    var xBtn = mk("button", { class: "akl-x", type: "button", "aria-label": "close", onclick: close, text: "×" });
    var top = mk("div", { class: "akl-top" }, [
      mk("h2", {}, ["BLOCK LADDER", mk("small", { text: "Climb the blocks -- earn the crown" })]),
      xBtn
    ]);
    bodyEl = mk("div", { class: "akl-body" });
    root = mk("section", { id: "ak-ladder", role: "dialog", "aria-label": "Block Ladder" }, [top, bodyEl]);
    document.body.appendChild(root);
  }

  // ---- section renderers -----------------------------------------------------
  function renderHero(snap) {
    var rIdx = rankIdxFor(snap.rep);
    var placeTxt = snap.place ? ("#" + snap.place + " on the block") : "unranked -- run a tower match";
    return mk("div", { class: "akl-card" }, [
      mk("div", { class: "akl-hero", style: "--clan:" + snap.color }, [
        mk("div", { class: "akl-badge" }, [mk("span", { class: "g", text: RANKS[rIdx].glyph })]),
        mk("div", { class: "akl-hero-main" }, [
          mk("div", { class: "akl-hero-rank", text: snap.rank }),
          mk("div", { class: "akl-hero-sub" }, [snap.name + "  --  ", mk("b", { text: snap.clanName }), "  --  " + placeTxt])
        ]),
        mk("div", { class: "akl-rep" }, [
          mk("div", { class: "n", text: String(snap.rep) }),
          mk("div", { class: "l", text: "Block Rep" })
        ])
      ])
    ]);
  }

  function renderReset() {
    var t = splitMs(seasonResetMs());
    segD = mk("span", { class: "v", text: String(t.d) });
    segH = mk("span", { class: "v", text: pad2(t.h) });
    segM = mk("span", { class: "v", text: pad2(t.m) });
    segS = mk("span", { class: "v", text: pad2(t.s) });
    function seg(node, label) { return mk("div", { class: "akl-seg" }, [node, mk("div", { class: "k", text: label })]); }
    resetNote = mk("div", { class: "akl-reset-note", text: seasonLabel() + " resets the ladder -- ranks soft-reset, your wealth + cards are untouched (the Fence never wipes)." });
    return mk("div", { class: "akl-card" }, [
      mk("div", { class: "akl-cap", text: "Season resets in" }),
      mk("div", { class: "akl-clock" }, [seg(segD, "Days"), seg(segH, "Hrs"), seg(segM, "Min"), seg(segS, "Sec")]),
      resetNote
    ]);
  }

  function renderExclusive() {
    var ex = seasonalExclusive();
    exBarFill = mk("i", { style: "width:" + Math.round(ex.pct * 100) + "%" });
    var prog;
    if (ex.unlocked) prog = mk("div", { class: "akl-ex-prog done" }, ["UNLOCKED -- it is yours when the season turns over."]);
    else prog = mk("div", { class: "akl-ex-prog" }, [mk("b", { text: String(ex.rep) }), " / " + ex.repNeeded + " Rep  --  ", mk("b", { text: String(ex.toGo) }), " to go before the reset"]);
    exProg = prog;
    return mk("div", { class: "akl-card" }, [
      mk("div", { class: "akl-cap", text: "Seasonal exclusive" }),
      mk("div", { class: "akl-ex" }, [
        mk("div", { class: "akl-ex-art" + (ex.unlocked ? "" : " locked") }, [mk("span", { text: ex.glyph })]),
        mk("div", { class: "akl-ex-main" }, [
          mk("div", { class: "akl-ex-name", text: ex.name }),
          mk("div", { class: "akl-ex-tag", text: "Cosmetic -- this season only" }),
          mk("div", { class: "akl-bar" }, [exBarFill]),
          prog
        ])
      ]),
      mk("div", { class: "akl-parity", text: ex.desc || "Earned by Block Rep on the free track -- a cosmetic skin, never raw power, never gem-gated. Miss the reset and it walks off the block." })
    ]);
  }

  function renderLadder(snap) {
    var youIdx = rankIdxFor(snap.rep);
    var rungs = RANKS.map(function (r, i) {
      var cls = "akl-rung" + (i === youIdx ? " you" : (i < youIdx ? " done" : " future"));
      var kids = [
        mk("span", { class: "rg", text: r.glyph }),
        mk("span", { class: "rn" }, [r.name, i === youIdx ? mk("span", { class: "akl-you-pill", text: "YOU" }) : null]),
        mk("span", { class: "rf", text: (i === youIdx ? (snap.rep + " rep") : (r.min + "+")) })
      ];
      return mk("div", { class: cls }, kids);
    });
    return mk("div", { class: "akl-card" }, [
      mk("div", { class: "akl-cap", text: "The 7 rungs" }),
      mk("div", { class: "akl-rungs" }, rungs)   // column-reverse -> King on top, Stray at the bottom
    ]);
  }

  // one leaderboard row -- shared by the GLOBAL board and the CREW (friends) board so
  // both stay byte-identical in layout. Crew rows carry no clan color -> stray fallback.
  function boardRow(r) {
    var place = (r && r.place) || 0;
    var cls = "akl-lrow" + (r && r.isYou ? " you" : "") + (place > 0 && place <= 3 ? " top" : "");
    var nm = ((r && r.name) || "Stray") + (r && r.isYou ? " (you)" : "");
    return mk("div", { class: cls }, [
      mk("span", { class: "akl-pl", text: place ? ("#" + place) : "--" }),
      mk("span", { class: "akl-dot", style: "--c:" + ((r && r.color) || CLAN_COLOR[r && r.clan] || CLAN_COLOR.stray) }),
      mk("span", { class: "akl-lnm", text: nm }),
      mk("span", { class: "akl-lrk", text: (r && r.rank) || "" }),
      mk("span", { class: "akl-ltr", text: String((r && r.trophies) | 0) })
    ]);
  }

  // CREW (friends) board rows -- consume the social lane. social.js owns crewLeaderboard()
  // on window.AKSocial; we NEVER throw if it is absent/offline/no-crew (returns []).
  function crewRows() {
    var s; try { s = global.AKSocial; } catch (_) { s = null; }
    try {
      if (s && typeof s.crewLeaderboard === "function") {
        var r = s.crewLeaderboard();
        if (Array.isArray(r)) return r;
      }
    } catch (_) {}
    return [];
  }

  // AK-REALBOARD 2026-07-12 (Phase 2 social): pull the LIVE server board -- REAL crews
  // ranked by trophies -- from the social lane (window.AKSocial.serverLeaderboard, which
  // reads the deployed ak-crew {action:'list'}). Fully guarded + offline-degrading: if the
  // social lane is absent, signed out, or offline the promise resolves [] and the LIVE tab
  // shows a note; the ghost "Block" board is never touched, so the leaderboard is never
  // blank. Server-derived trophies only (do not trust the local save for a competitive rank).
  function loadServerBoard() {
    var s; try { s = global.AKSocial; } catch (_) { s = null; }
    if (!s || typeof s.serverLeaderboard !== "function") { S.serverRows = []; return; }
    try {
      var p = s.serverLeaderboard();
      if (!p || typeof p.then !== "function") { S.serverRows = []; return; }
      p.then(function (rows) {
        S.serverRows = Array.isArray(rows) ? rows : [];
        if (S.open && S.boardTab === "live") paintBoard();
      }, function () { S.serverRows = []; });
    } catch (_) { S.serverRows = []; }
  }

  // paint the active board tab into boardWrap (global rows cached from render; crew +
  // live fetched live -- both degrade to a note, never blank).
  function paintBoard() {
    if (!boardWrap) return;
    if (S.boardTab === "crew") {
      var crows = crewRows();
      if (!crows.length) {
        setKids(boardWrap, mk("div", { class: "akl-note", text: "Join a crew to see your friends board -- then race them for the top rung." }));
        return;
      }
      setKids(boardWrap, mk("div", { class: "akl-board" }, crows.slice(0, 50).map(boardRow)));
      return;
    }
    if (S.boardTab === "live") {
      var lrows = S.serverRows || [];
      if (!lrows.length) {
        setKids(boardWrap, mk("div", { class: "akl-note", text: "Live crew rankings load once you sign in and real crews take the field. The Block board always shows the streets." }));
        return;
      }
      setKids(boardWrap, mk("div", { class: "akl-board" }, lrows.slice(0, 50).map(boardRow)));
      return;
    }
    var rows = S.globalRows || [];
    if (!rows.length) {
      setKids(boardWrap, mk("div", { class: "akl-note", text: "The streets are loading. Run a match to put your name on the board." }));
      return;
    }
    setKids(boardWrap, mk("div", { class: "akl-board" }, rows.slice(0, 40).map(boardRow)));
  }

  // segmented control -- The Block (global ghost) / Live (real server crews) / Crew
  // (your friends). Toggling repaints only the list.
  function buildTabs() {
    var defs = [
      { id: "global", label: "The Block" },
      { id: "live", label: "Live" },
      { id: "crew", label: "Crew" },
    ];
    var btns = {};
    function set(tab) {
      S.boardTab = tab;
      defs.forEach(function (d) { if (btns[d.id]) btns[d.id].className = "akl-tab" + (tab === d.id ? " on" : ""); });
      paintBoard();
    }
    var els = defs.map(function (d) {
      var b = mk("button", { class: "akl-tab" + (S.boardTab === d.id ? " on" : ""), type: "button", text: d.label, onclick: function () { set(d.id); } });
      btns[d.id] = b; return b;
    });
    return mk("div", { class: "akl-tabs" }, els);
  }

  function renderBoard() {
    boardWrap = mk("div", {});
    var card = mk("div", { class: "akl-card" }, [
      mk("div", { class: "akl-cap", text: "Leaderboard" }),
      buildTabs(),
      boardWrap
    ]);
    paintBoard();
    return card;
  }

  // ---- render + live ticker --------------------------------------------------
  function render() {
    if (!bodyEl) return;
    var rows = leaderboardRows();
    var snap = playerSnapshot(rows);
    S.globalRows = rows;          // cached so the Crew<->Block tab toggle repaints without re-querying pop.
    S.myPlace = snap.place;       // stashed for the "passed you" check in open()
    loadServerBoard();            // async real crews (server) -> repaints the LIVE tab when it lands
    setKids(bodyEl, [
      renderHero(snap),
      renderReset(),
      renderExclusive(),
      renderLadder(snap),
      renderBoard()
    ]);
  }
  // Cheap tick: ONE setInterval, touches only the countdown text nodes (no relayout
  // of the heavy lists). Paused while the overlay is closed or the tab is hidden.
  function tick() {
    if (!S.open) return;
    if (typeof document !== "undefined" && document.hidden) return;
    var t = splitMs(seasonResetMs());
    if (segD) segD.textContent = String(t.d);
    if (segH) segH.textContent = pad2(t.h);
    if (segM) segM.textContent = pad2(t.m);
    if (segS) segS.textContent = pad2(t.s);
  }
  function startTicker() { stopTicker(); S.ticker = setInterval(tick, 1000); }
  function stopTicker() { if (S.ticker) { clearInterval(S.ticker); S.ticker = 0; } }

  // ---- toast + "passed you" nudge --------------------------------------------
  // Lazy pill, mirrors trading.js/social.js. Fully guarded -- never throws if no DOM.
  function toast(m) {
    try {
      if (typeof document === "undefined") return;
      if (!toastEl) { toastEl = mk("div", { class: "akl-toast" }); document.body.appendChild(toastEl); }
      toastEl.textContent = m;
      toastEl.classList.add("show");
      clearTimeout(toast._t);
      toast._t = setTimeout(function () { if (toastEl) toastEl.classList.remove("show"); }, 2600);
    } catch (_) {}
  }
  // Retention hook: a crewmate/rival passed you -> your place NUMBER climbed (worse). Compare the
  // current place to the last one we showed; nudge if you slipped, then re-stamp. All localStorage
  // access guarded so a missing/blocked store is a silent no-op (never a crash).
  function checkPassed(place) {
    place = +place;
    if (!isFinite(place) || place <= 0) return;   // unranked -- nothing to compare against
    var prev = null;
    try { var raw = localStorage.getItem(LAST_PLACE_KEY); if (raw != null && raw !== "") prev = parseInt(raw, 10); } catch (_) {}
    try { localStorage.setItem(LAST_PLACE_KEY, String(place | 0)); } catch (_) {}
    if (prev != null && isFinite(prev) && prev > 0 && place > prev) toast("Someone passed you -- reclaim your spot");
  }

  // ---- open / close / refresh ------------------------------------------------
  function open() {
    buildShell(); if (!root) return;
    S.open = true;
    render();
    checkPassed(S.myPlace);   // fire the nudge AFTER render (uses the place we just stashed)
    root.classList.add("open");
    startTicker();
  }
  function close() { S.open = false; stopTicker(); if (root) root.classList.remove("open"); }
  function toggle() { if (S.open) close(); else open(); }
  function refresh() { if (S.open) render(); }

  // ---- wire-up + export ------------------------------------------------------
  function wire() {
    if (S.booted) return; S.booted = true;
    try {
      var btn = document.getElementById("ladderbtn");   // optional launcher (mirrors social.js crewbtn)
      if (btn) btn.addEventListener("click", open);
    } catch (_) {}
    // re-render on auth flips while open (name/clan/board can change)
    try { global.addEventListener("ak-auth", function () { refresh(); }); } catch (_) {}
    // pause/resume the cheap ticker with tab visibility
    try { if (typeof document !== "undefined") document.addEventListener("visibilitychange", function () { if (S.open && !document.hidden) tick(); }); } catch (_) {}
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
  }

  // PUBLIC SURFACE
  global.AKLadder = {
    open: open, close: close, toggle: toggle, refresh: refresh,
    blockRep: blockRep, repRank: function () { return repRankName(blockRep()); },
    seasonResetMs: seasonResetMs, seasonalExclusive: seasonalExclusive,
    RANKS: RANKS.slice()
  };
  global.akOpenLadder = open;
})(typeof window !== "undefined" ? window : this);
