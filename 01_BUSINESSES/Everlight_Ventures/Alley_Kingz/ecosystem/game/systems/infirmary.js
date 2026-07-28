/* game/systems/infirmary.js -- AK_SYSTEMS module: THE INFIRMARY (card death -> heal).
 * ---------------------------------------------------------------------------
 * CORE LOOP CANON line 5 ("DEATH -> INFIRMARY"): any card KILLED in a raid or
 * RPG-style combat must be PATCHED UP in the Infirmary before it can run with the
 * pack again. Cards are NOT disposable -- a death pulls the dog off your usable
 * deck until it heals. This is the consequence leg that makes the WATCH (guarding),
 * FORTIFY (wood/stone), and world-map raids actually bite.
 *
 * WHAT IT DOES (real, not a stub):
 *   - window.akOpenInfirmary() opens a lazy-DOM bottom-sheet overlay (built on open,
 *     hidden on close -- 60fps-safe, no per-frame work; a 1s ticker runs ONLY while
 *     the sheet is visible and is cleared on close). It lists every DOWNED dog with
 *     a heal countdown and two ways back to the deck:
 *       1) HEAL OVER TIME -- free, slow. The dog patches up on its own; bigger dogs
 *          (higher rarity) take longer. When the timer hits 0 it returns to the deck.
 *       2) HEAL NOW -- pay GOLD (soft currency) to put the dog back in the fight this
 *          second. Cost scales with the time left, so an almost-healed dog is cheap.
 *   - window.AK_INFIRMARY.downCard(name) is the contract the raid / encounter / RPG
 *     systems call the instant a card is killed. It marks the death; isDown(name)
 *     lets the deck / defense layers exclude a downed dog until it heals.
 *
 * STATE SHAPE (this module OWNS it; economy.js ensureShape is FROZEN so we never
 * touch it -- p.downed is lazily created on the first death, exactly like guard.js
 * does p.guards, so a fresh profile stays byte-identical / zero-state):
 *   p.downed = { cardName: { downAt: <ms>, healAt: <ms>, rarity: <str> }, ... }
 *   A dog is DOWN while an entry exists AND now < healAt. At/after healAt it is
 *   healed (auto-swept on the next open / tick). Falsy-default {} (absent = whole pack).
 *
 * HARD LAW honored (every line):
 *   - engine.js is FROZEN. This module layers via AK_CTX (overlay host / cards /
 *     showBanner) + AK_ECON only -- it edits NO shared host file.
 *   - ONE economy = AK_ECON. Every profile read/write goes through AK_ECON
 *     (loadProfile / mutateProfile), falsy-default on write, lazily-created p.downed.
 *   - Soft-currency only. HEAL NOW spends GOLD (p.coins). Gems are never read,
 *     granted, or spent here -- healing is never a paid-power gate.
 *   - Canon names only: the FENCE = market, the WATCH = guarding; this is THE
 *     INFIRMARY (Mama Bones patches the pack). No Kimi generics.
 *   - No em-dashes (use --). 60fps hub: lazy DOM, throttled 1s ticker, no per-frame work.
 *
 * Headless-safe: zero top-level DOM / localStorage; bails where AK_SYSTEMS is absent
 * (battler / node harness). XSS-safe (mk() -> textContent for every dynamic string).
 * Plain browser JS.
 */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;                 // hub-only module

  var ID = 'infirmary';
  var GOLD = '#e8c55a', DIM = '#b9a76a', GREEN = '#7CFFB0', RED = '#f3a0a0';

  // rarity -> accent (mirrors guard.js / modes.js so the overlay reads like the deck)
  var RAR_COLOR = { Common: '#9fb0c0', Rare: '#5ad0c0', Epic: '#c9a8ff', Legendary: '#ffd76b', Mythic: '#ff8fae' };

  // ---- heal config (the ONE source of truth) --------------------------------
  // FREE heal-over-time, in MINUTES, scaled by rarity -- a Mythic apex takes far
  // longer to drag back to its paws than a Common stray. Tuned so a fresh kill
  // costs a real beat (you feel the loss) without bricking the pack for a day.
  var HEAL_MIN = { Common: 10, Rare: 18, Epic: 30, Legendary: 45, Mythic: 70 };
  // PAY-TO-HEAL (gold). Cost is proportional to the time LEFT, so a near-healed
  // dog is cheap and a fresh corpse is dear. base + perMin*minutesLeft, capped.
  // This is the RUSH premium layered ON TOP of the infirmary fee below (skip the timer).
  var GOLD_BASE = 8, GOLD_PER_MIN = 6, GOLD_CAP = 600;
  // AK-AUTOWAKE (2026-06-30) -- the infirmary FEE: the flat GOLD cost to patch a dog
  // up, deducted automatically WHEN IT WAKES (or folded into HEAL NOW). Deterministic
  // from LEVEL + RARITY -- a high-level apex costs far more to drag back than a stray
  // pup (operator: "resources to cover the infirmary cost must be deducted"). base 50 +
  // 25*level, scaled by rarity. Stored on the downed entry at death so it is fixed
  // (deterministic) from that moment, never drifting with later level-ups.
  var FEE_BASE = 50, FEE_PER_LVL = 25;
  var FEE_RAR_MULT = { Common: 1.0, Rare: 1.25, Epic: 1.6, Legendary: 2.0, Mythic: 2.6 };
  var SHORT_FUNDS_MS = 5 * 60000;        // can't cover the fee at wake -> push the wake out 5 min, then retry (takes LONGER, never blocks)
  var AUTOWAKE_THROTTLE_MS = 5000;       // host onTick polls auto-wake at most every 5s (60fps-safe: a clock compare per frame, a write only when due)

  function now() { return Date.now(); }
  function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ---- module-local runtime (never persisted) -------------------------------
  var CTX = null;
  var S = { root: null, body: null, built: false, timer: 0 };

  /* ====================================================================== *
   * ECONOMY / CARD HELPERS (prefer AK_ECON / AK_CTX contracts; safe fallbacks)
   * ====================================================================== */
  function econ() { try { return (CTX && CTX.econ) ? CTX.econ : (global.AK_ECON || null); } catch (_) { return null; } }
  function freshProfile() { try { var e = econ(); return e ? e.loadProfile() : null; } catch (_) { return null; } }
  function thOf(p) { try { if (global.AK_ECON && AK_ECON.townHallLevel) return AK_ECON.townHallLevel(p); } catch (_) {} return Math.max(1, Math.min(10, (p && p.townHall | 0) || 1)); }
  function cardLevelOf(p, name) { try { if (global.AK_ECON && AK_ECON.cardLevel) return AK_ECON.cardLevel(p, name); } catch (_) {} var v = p && p.cardLvls && p.cardLvls[name]; return Math.max(1, Math.min(10, Math.floor(v || 1))); }
  function cardTable() { try { var c = CTX || global.AK_CTX; return (c && c.cards && c.cards()) || {}; } catch (_) { return {}; } }
  function cardInfo(name) { var t = cardTable(); return (name && t[name]) || null; }
  function rarityOf(name) { var c = cardInfo(name); return (c && c.rarity) || 'Common'; }
  function cardNumOf(name) { var c = cardInfo(name); return (c && (c.cardNumber || c.id)) || null; }
  function coinsOf(p) { return Math.max(0, (p && p.coins) | 0); }
  function banner(text, secs) { try { if (CTX && CTX.showBanner) CTX.showBanner(text, secs || 2); } catch (_) {} }

  /* ====================================================================== *
   * HEAL MATH (pure)
   * ====================================================================== */
  function healMsFor(rarity) { return (HEAL_MIN[rarity] || HEAL_MIN.Common) * 60000; }
  // remaining heal time for an entry, in ms (0 = already healed).
  function remainingMs(entry) { return entry ? Math.max(0, (entry.healAt || 0) - now()) : 0; }
  // gold to skip the remaining time. 0 once the timer has elapsed.
  function healCostGold(remMs) {
    if (remMs <= 0) return 0;
    var mins = remMs / 60000;
    return clampN(Math.ceil(GOLD_BASE + GOLD_PER_MIN * mins), 1, GOLD_CAP);
  }
  // the AUTO-WAKE infirmary fee (gold), deterministic from level + rarity. PURE.
  function infirmaryFee(level, rarity) {
    level = Math.max(1, Math.min(10, Math.floor(level || 1)));
    var mult = FEE_RAR_MULT[rarity] || 1;
    return Math.max(0, Math.round((FEE_BASE + FEE_PER_LVL * level) * mult));
  }

  /* ====================================================================== *
   * STATE READS (pure -- never write; 60fps-safe)
   * ====================================================================== */
  function downedMap(p) { return (p && p.downed && typeof p.downed === 'object') ? p.downed : null; }
  // is this dog currently OFF the deck (entry exists AND still healing)?
  function isDown(name) {
    if (!name) return false;
    var p = freshProfile(), m = downedMap(p);
    var e = m && m[name];
    return !!(e && now() < (e.healAt || 0));
  }
  // a quick {name:true} lookup of every currently-down dog -- the deck / WATCH
  // layers filter against this so a corpse can't be fielded. Pure (no write).
  function downedSet(p) {
    p = p || freshProfile(); var m = downedMap(p), out = {}, t = now();
    if (m) for (var k in m) { if (m.hasOwnProperty(k) && m[k] && t < (m[k].healAt || 0)) out[k] = true; }
    return out;
  }
  // the overlay/list view: every active entry, freshest-to-heal first.
  function list() {
    var p = freshProfile(), m = downedMap(p), th = thOf(p), out = [], t = now();
    if (m) for (var k in m) {
      if (!m.hasOwnProperty(k)) continue;
      var e = m[k]; if (!e) continue;
      var rem = Math.max(0, (e.healAt || 0) - t);
      if (rem <= 0) continue;                       // healed -> not listed (swept lazily on open/tick)
      var rar = e.rarity || rarityOf(k);
      var fee = Math.max(0, (e.cost | 0) || infirmaryFee(cardLevelOf(p, k), rar));   // auto-wake fee (stored at death)
      out.push({ name: k, rarity: rar, lvl: cardLevelOf(p, k), cardNumber: cardNumOf(k), downAt: e.downAt || 0, healAt: e.healAt || 0, remainingMs: rem, fee: fee, cost: fee + healCostGold(rem) });
    }
    out.sort(function (a, b) { return a.remainingMs - b.remainingMs; });
    return out;
  }
  function count() { return list().length; }

  /* ====================================================================== *
   * MUTATORS (atomic via AK_ECON.mutateProfile; falsy-default, lazy p.downed)
   * ====================================================================== */
  function ensureDowned(p) { if (!p.downed || typeof p.downed !== 'object') p.downed = {}; return p.downed; }

  // THE DEATH HOOK. raid / encounter / RPG-defense systems call this the moment a
  // card is killed. A re-death while already down EXTENDS the timer (max), never
  // shortens it. Returns { ok, name, healAt, rarity, healMs } or { ok:false,error }.
  function downCard(name) {
    if (!name) return { ok: false, error: 'NO_CARD' };
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    var rar = rarityOf(name), dur = healMsFor(rar), out = { ok: false, error: 'FAIL' };
    e.mutateProfile(function (p) {
      var m = ensureDowned(p), t = now(), nHeal = t + dur;
      var prev = m[name];
      var healAt = (prev && (prev.healAt || 0) > nHeal) ? (prev.healAt || 0) : nHeal;   // extend, never shorten
      var downAt = (prev && (prev.downAt || 0)) ? (prev.downAt || 0) : t;
      var fee = infirmaryFee(cardLevelOf(p, name), rar);                                // deterministic heal cost, fixed at death
      var cost = (prev && (prev.cost | 0)) ? Math.max(prev.cost | 0, fee) : fee;        // re-death keeps the larger fee
      m[name] = { downAt: downAt, healAt: healAt, rarity: rar, cost: cost };
      out = { ok: true, name: name, healAt: healAt, rarity: rar, healMs: dur, cost: cost };
    });
    if (out.ok) banner(name + ' is DOWN -- patch it up at the Infirmary', 2.4);
    refresh();
    return out;
  }

  // PAY GOLD to heal a downed dog right now. Atomic: validates funds, deducts,
  // removes the entry (dog back on the deck) in ONE write. A dog whose timer has
  // already elapsed heals for free (cost 0). Returns { ok, name, spent } | { ok:false,error }.
  function healNow(name) {
    if (!name) return { ok: false, error: 'NO_CARD' };
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    var out = { ok: false, error: 'NOT_DOWN' };
    e.mutateProfile(function (p) {
      var m = downedMap(p); var entry = m && m[name];
      if (!entry) { out = { ok: false, error: 'NOT_DOWN' }; return; }
      var rem = Math.max(0, (entry.healAt || 0) - now());
      var fee = Math.max(0, (entry.cost | 0) || infirmaryFee(cardLevelOf(p, name), entry.rarity || rarityOf(name)));
      var rush = healCostGold(rem);                  // time-skip premium (0 once the timer has elapsed)
      var cost = fee + rush;                          // resources to cover the infirmary cost are ALWAYS deducted
      if (cost > 0 && coinsOf(p) < cost) { out = { ok: false, error: 'INSUFFICIENT_FUNDS', have: coinsOf(p), need: cost }; return; }
      if (cost > 0) p.coins = coinsOf(p) - cost;
      delete m[name];
      out = { ok: true, name: name, spent: cost, fee: fee, rush: rush };
    });
    if (out.ok) banner(name + ' is back on the deck', 2);
    refresh();
    return out;
  }

  // HEAL ALL with gold (convenience). Heals what you can afford, cheapest-first,
  // in ONE atomic write. Returns { ok, healed:[names], spent }.
  function healAll() {
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    var out = { ok: true, healed: [], spent: 0 };
    e.mutateProfile(function (p) {
      var m = downedMap(p); if (!m) return;
      var t = now(), rows = [];
      for (var k in m) { if (!m.hasOwnProperty(k) || !m[k]) continue; var rem = Math.max(0, (m[k].healAt || 0) - t); var fee = Math.max(0, (m[k].cost | 0) || infirmaryFee(cardLevelOf(p, k), m[k].rarity || rarityOf(k))); rows.push({ name: k, rem: rem, cost: fee + healCostGold(rem) }); }
      rows.sort(function (a, b) { return a.cost - b.cost; });
      for (var i = 0; i < rows.length; i++) {
        var c = rows[i].cost;
        if (c > 0 && coinsOf(p) < c) continue;       // skip what you cannot afford
        if (c > 0) p.coins = coinsOf(p) - c;
        delete m[rows[i].name];
        out.healed.push(rows[i].name); out.spent += c;
      }
    });
    if (out.healed.length) banner(out.healed.length + ' dogs patched up', 2);
    refresh();
    return out;
  }

  // AUTO-WAKE -- the heart of the feature. Clear every downed dog whose heal timer
  // has elapsed, DEDUCTING its stored infirmary fee from GOLD as it returns to the
  // deck (no manual tap). If the player cannot cover the fee the wake is DELAYED
  // (healAt pushed out by SHORT_FUNDS_MS) instead of blocked -- the dog still comes
  // back, it just takes LONGER (operator law). ONE atomic write, ONLY when something
  // is actually due (idempotent + falsy-safe; zero downed => zero writes => zero-state
  // byte-identical). `t` defaults to now -- the harness passes a future stamp to prove
  // the timer without sleeping. Returns { woke:[names], spent, delayed:[names] }.
  function autoWake(t) {
    var e = econ(); if (!e) return { woke: [], spent: 0, delayed: [] };
    t = (typeof t === 'number' && isFinite(t)) ? t : now();
    var p0 = freshProfile(), m0 = downedMap(p0);
    if (!m0) return { woke: [], spent: 0, delayed: [] };
    var due = false;                                              // cheap pre-scan: only WRITE if a timer actually elapsed
    for (var k0 in m0) { if (m0.hasOwnProperty(k0) && m0[k0] && t >= (m0[k0].healAt || 0)) { due = true; break; } }
    if (!due) return { woke: [], spent: 0, delayed: [] };
    var out = { woke: [], spent: 0, delayed: [] };
    e.mutateProfile(function (p) {
      var m = p && p.downed; if (!m) return;
      for (var k in m) {
        if (!m.hasOwnProperty(k) || !m[k]) continue;
        var entry = m[k];
        if (t < (entry.healAt || 0)) continue;                    // not due yet
        var cost = Math.max(0, (entry.cost | 0) || infirmaryFee(cardLevelOf(p, k), entry.rarity || rarityOf(k)));
        if (cost > 0 && coinsOf(p) < cost) { entry.healAt = t + SHORT_FUNDS_MS; out.delayed.push(k); continue; }   // can't pay -> wake takes longer
        if (cost > 0) p.coins = coinsOf(p) - cost;
        delete m[k];
        out.woke.push(k); out.spent += cost;
      }
    });
    return out;
  }
  // sweep([t]) -- legacy alias. The over-time heal now runs through autoWake (fee
  // deducted), so a sweep is "auto-wake everything due". Returns the count revived
  // this pass (the overlay ticker reads it). Kept for back-compat callers.
  function sweep(t) { var r = autoWake(t); return (r && r.woke) ? r.woke.length : 0; }
  // pollAutoWake() -- the host onTick hook. Throttled to AUTOWAKE_THROTTLE_MS so the
  // 60fps loop only does a clock compare each frame and a real localStorage pass at
  // most every 5s (and a write only when a dog is actually due). Banners + refreshes
  // the overlay when a dog wakes (or gets delayed) on its own.
  var _lastPoll = 0;
  function pollAutoWake() {
    var t = now();
    if (t - _lastPoll < AUTOWAKE_THROTTLE_MS) return;
    _lastPoll = t;
    var r = autoWake(t);
    if (r.woke && r.woke.length) { banner(r.woke.length + ' dog' + (r.woke.length === 1 ? '' : 's') + ' patched up and back on the deck', 2); refresh(); }
    else if (r.delayed && r.delayed.length) { refresh(); }
  }
  // infirmaryState(p, now) -- the read the host renders the aftermath from: every
  // downed dog as { card, healsAt, cost, ready } (+ rarity / remainingMs for the UI).
  // `cost` is the auto-wake fee that will be deducted; `ready` = its timer elapsed
  // (auto-wake clears it on the next poll, funds permitting). PURE read (60fps-safe:
  // pass a profile to skip the load); absent p.downed => [] (zero-state).
  function infirmaryState(p, t) {
    p = p || freshProfile(); var m = downedMap(p), out = [];
    t = (typeof t === 'number' && isFinite(t)) ? t : now();
    if (m) for (var k in m) {
      if (!m.hasOwnProperty(k) || !m[k]) continue;
      var e = m[k], healsAt = e.healAt || 0, rar = e.rarity || rarityOf(k);
      var fee = Math.max(0, (e.cost | 0) || infirmaryFee(cardLevelOf(p, k), rar));
      out.push({ card: k, rarity: rar, healsAt: healsAt, cost: fee, ready: t >= healsAt, remainingMs: Math.max(0, healsAt - t) });
    }
    out.sort(function (a, b) { return a.healsAt - b.healsAt; });
    return out;
  }

  /* ====================================================================== *
   * OVERLAY (window.akOpenInfirmary) -- lazy DOM, built on open, hidden on close
   * ====================================================================== */
  function mk(tag, css, text) { var el = document.createElement(tag); if (css) el.style.cssText = css; if (text != null) el.textContent = text; return el; }
  function btnPrimary() { return 'background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;border-radius:9px;padding:8px 12px;font-weight:900;font-size:11px;letter-spacing:.03em;cursor:pointer;-webkit-tap-highlight-color:transparent;'; }
  function btnGhost() { return 'background:none;border:1px solid rgba(201,168,76,.5);color:#b9a76a;border-radius:9px;padding:8px 11px;font-weight:800;font-size:11px;cursor:pointer;-webkit-tap-highlight-color:transparent;'; }

  // mm:ss under an hour, else Hh Mm -- short, gritty, no clutter.
  function fmtTime(ms) {
    var s = Math.max(0, Math.ceil(ms / 1000));
    if (s >= 3600) { var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h + 'h ' + m + 'm'; }
    var mm = Math.floor(s / 60), ss = s % 60;
    return mm + ':' + (ss < 10 ? '0' : '') + ss;
  }

  /* ====================================================================== *
   * STORY FLAVOR (Block Chronicles) -- window.AK_STORIES is an OPTIONAL
   * sidecar; infirmary.js does not load it, only reads it off global at
   * render time (fully typeof-guarded). When a downed flagship dog has an
   * ambientBarks.infirmaryLines entry, the ward row gets a one-line flavor
   * quote. Picked DETERMINISTICALLY by the day-of-year (not Math.random) so
   * the row never flickers between re-renders / ticker refreshes the same day.
   * ====================================================================== */
  function storyDayIndex(mod) {
    if (!mod) return 0;
    try {
      var d = new Date();
      var doy = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 86400000);
      return ((doy % mod) + mod) % mod;
    } catch (_) { return 0; }
  }
  function storyFlavorFor(cardNumber) {
    try {
      var stories = global.AK_STORIES;
      if (!cardNumber || typeof stories !== 'object' || !stories) return null;
      var story = stories[cardNumber];
      var lines = story && story.ambientBarks && story.ambientBarks.infirmaryLines;
      if (!lines || !lines.length) return null;
      return lines[storyDayIndex(lines.length)];
    } catch (_) { return null; }
  }

  function ensureRoot() {
    if (S.built || typeof document === 'undefined') return;
    var ov = mk('div', 'position:fixed;inset:0;z-index:40;display:none;align-items:flex-end;justify-content:center;' +
      'background:rgba(6,6,10,.86);font-family:Inter,system-ui,sans-serif;-webkit-tap-highlight-color:transparent;');
    ov.id = 'ak-infirmary-ov';
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });   // tap the scrim to dismiss
    var card = mk('div', 'width:100%;max-width:560px;max-height:86dvh;overflow-y:auto;margin:0 8px;' +
      'padding:14px 14px calc(14px + env(safe-area-inset-bottom));border-radius:16px 16px 0 0;' +
      'background:rgba(10,9,14,.98);border:1px solid rgba(201,168,76,.5);border-bottom:none;box-shadow:0 -6px 30px rgba(0,0,0,.6);');
    card.id = 'ak-infirmary-card';
    card.addEventListener('click', function (e) { e.stopPropagation(); });
    ov.appendChild(card); document.body.appendChild(ov);
    S.root = ov; S.body = card; S.built = true;
  }

  function openInfirmary() {
    if (typeof document === 'undefined') return { ok: false, error: 'NO_DOM' };
    CTX = CTX || global.AK_CTX || null;
    ensureRoot(); if (!S.root) return { ok: false, error: 'NO_DOM' };
    autoWake();
    render(); S.root.style.display = 'flex';
    startTicker();
    return { ok: true };
  }
  function close() { stopTicker(); if (S.root) S.root.style.display = 'none'; }
  function refresh() { if (S.root && S.root.style.display !== 'none') render(); }

  // 1s ticker -- ONLY while the sheet is open. Updates the countdown text + heal
  // cost in place; re-renders only when a dog crosses the heal line (cheap).
  function startTicker() {
    stopTicker();
    if (typeof setInterval === 'undefined') return;
    S.timer = setInterval(function () {
      if (!S.root || S.root.style.display === 'none') { stopTicker(); return; }
      var aw = autoWake(now());
      if ((aw.woke && aw.woke.length) || (aw.delayed && aw.delayed.length)) { render(); return; }   // a dog healed (fee deducted) or got delayed (short on gold) -> rebuild
      var rows = S._rows || [];
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i], rem = Math.max(0, r.healAt - now());
        if (r.timeEl) r.timeEl.textContent = fmtTime(rem);
        if (r.costBtn) r.costBtn.textContent = 'HEAL NOW  ' + ((r.fee | 0) + healCostGold(rem)) + 'g';
      }
    }, 1000);
  }
  function stopTicker() { if (S.timer) { try { clearInterval(S.timer); } catch (_) {} S.timer = 0; } }

  function header() {
    var p = freshProfile(), n = count();
    var wrap = mk('div', 'margin-bottom:8px;');
    var top = mk('div', 'display:flex;align-items:center;gap:8px;');
    top.appendChild(mk('span', 'font-size:18px;line-height:1;', '🩹'));
    top.appendChild(mk('span', 'flex:1;color:#e8c55a;font-weight:900;font-size:13px;letter-spacing:.05em;', 'THE INFIRMARY'));
    var x = mk('button', btnGhost(), 'CLOSE'); x.type = 'button';
    x.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    top.appendChild(x);
    wrap.appendChild(top);
    var sub = mk('div', 'color:' + (n ? RED : DIM) + ';font-size:10px;font-weight:700;margin-top:4px;');
    sub.textContent = n
      ? (n + ' dog' + (n === 1 ? '' : 's') + ' down  ·  ' + coinsOf(p) + 'g on hand  ·  they auto-heal over time (a gold fee is deducted), or pay to run now')
      : ('Pack is whole  ·  ' + coinsOf(p) + 'g on hand');
    wrap.appendChild(sub);
    return wrap;
  }

  function render() {
    if (!S.body) return;
    S.body.replaceChildren();
    S._rows = [];
    S.body.appendChild(header());

    var rows = list();
    if (!rows.length) {
      var empty = mk('div', 'color:#b9a76a;font-size:12px;line-height:1.5;padding:16px 4px;');
      empty.textContent = 'No dogs in the Infirmary. Every fighter is on its paws and ready to run with the pack. Lose one in a raid and it lands here to heal.';
      S.body.appendChild(empty);
      return;
    }

    rows.forEach(function (it) {
      var row = mk('div', 'display:flex;align-items:center;gap:8px;padding:9px 4px;border-bottom:1px solid rgba(201,168,76,.18);');
      var pip = mk('span', 'width:8px;height:8px;border-radius:50%;flex:0 0 auto;background:' + (RAR_COLOR[it.rarity] || DIM) + ';');
      row.appendChild(pip);

      var info = mk('div', 'flex:1;min-width:0;');
      info.appendChild(mk('div', 'color:#E8E8E8;font-weight:800;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;', it.name + '  Lv' + it.lvl));
      var timeEl = mk('div', 'color:' + RED + ';font-weight:700;font-size:10px;margin-top:2px;');
      timeEl.textContent = fmtTime(it.remainingMs);
      var timeWrap = mk('div', 'display:flex;align-items:baseline;gap:5px;');
      timeWrap.appendChild(mk('span', 'color:#8a7f5e;font-size:9px;', 'HEALING'));
      timeWrap.appendChild(timeEl);
      info.appendChild(timeWrap);
      // AK-STORIES: flagship dog flavor quote row (guarded, deterministic-by-day)
      var flavor = storyFlavorFor(it.cardNumber);
      if (flavor) info.appendChild(mk('div', 'color:#9a8f6a;font-size:10px;font-style:italic;margin-top:3px;line-height:1.35;', flavor));
      row.appendChild(info);

      var costBtn = mk('button', btnPrimary() + 'min-width:104px;', 'HEAL NOW  ' + it.cost + 'g'); costBtn.type = 'button';
      costBtn.addEventListener('click', (function (nm) { return function (e) {
        e.stopPropagation();
        var r = healNow(nm);
        if (!r.ok && r.error === 'INSUFFICIENT_FUNDS') banner('Not enough gold -- need ' + r.need + 'g', 2);
      }; })(it.name));
      row.appendChild(costBtn);

      S.body.appendChild(row);
      S._rows.push({ name: it.name, healAt: it.healAt, fee: it.fee, timeEl: timeEl, costBtn: costBtn });
    });

    // footer -- HEAL ALL (gold) + DONE
    var foot = mk('div', 'display:flex;gap:8px;margin-top:12px;');
    var all = mk('button', btnGhost() + 'flex:1;', 'HEAL ALL'); all.type = 'button';
    all.addEventListener('click', function (e) { e.stopPropagation(); var r = healAll(); if (r.ok && !r.healed.length) banner('Not enough gold to heal any', 2); });
    var done = mk('button', btnPrimary() + 'flex:2;', 'DONE'); done.type = 'button';
    done.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    foot.appendChild(all); foot.appendChild(done);
    S.body.appendChild(foot);

    // AK-INFIRMARY-DOOR 2026-07-02: walk INTO the building itself (Patch + the living ward video) from the panel
    if (typeof global.akEnterInfirmaryBuilding === 'function') {
      var visit = mk('button', btnGhost() + 'width:100%;margin-top:8px;', '\u{1FA79} STEP INSIDE THE INFIRMARY');
      visit.type = 'button';
      visit.addEventListener('click', function (e) { e.stopPropagation(); close(); try { global.akEnterInfirmaryBuilding(); } catch (_e) {} });
      S.body.appendChild(visit);
    }

    var note = mk('div', 'color:#8a7f5e;font-size:9px;margin-top:8px;line-height:1.4;');
    note.textContent = 'A dog killed in a raid auto-heals over time -- a gold fee is deducted when it returns to the deck (bigger dogs cost more). Pay gold to put it back this second. Gems never buy a heal.';
    S.body.appendChild(note);
  }

  /* ====================================================================== *
   * MODULE REGISTRATION
   * ====================================================================== */
  global.AK_SYSTEMS.register({
    id: ID,
    init: function (ctx) { CTX = ctx || global.AK_CTX || CTX; },
    // claims an Infirmary building IF the world ever defines one (id/label match);
    // today no such building exists, so this never fires -- the HUD chip / overlay
    // entry is wired by the integration pass. Safe + future-proof.
    onEnterBuilding: function (b, ctx) {
      CTX = ctx || CTX;
      // AK-INFIRMARY 2026-07-01: do NOT claim the building here -- the host shows the proper keeper
      // interior (Patch the medic + the infirmary art), and its REST + RECOVER button opens openInfirmary().
      // Claiming it skipped straight to the bare overlay ("goes nowhere" when the pack is healthy).
      return false;
    },
    onTick: function (dt, ctx) { CTX = ctx || CTX; pollAutoWake(); },   // throttled auto-wake poll (60fps-safe: clock compare per frame, localStorage pass at most every 5s)
    onDrawWorld: function (ctx) {}                            // overlay + state only
  });

  // public API: the overlay entry + the death/heal contract the raid / encounter
  // / deck systems call.
  global.akOpenInfirmary = openInfirmary;
  global.AK_INFIRMARY = {
    open: openInfirmary, close: close,
    // death + heal contract
    downCard: downCard, isDown: isDown, healNow: healNow, healAll: healAll,
    // AUTO-WAKE: revive due dogs + deduct the heal fee (host onTick polls this; idempotent, falsy-safe)
    autoWake: autoWake, infirmaryState: infirmaryState, infirmaryFee: infirmaryFee,
    // reads for the deck / WATCH layers
    list: list, count: count, downedSet: downedSet, healMsFor: healMsFor, healCostGold: healCostGold
  };

})(typeof window !== 'undefined' ? window : globalThis);
