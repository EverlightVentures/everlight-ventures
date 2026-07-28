/* game/systems/guard.js -- AK_SYSTEMS module: DISTRICT GUARDING / BASE DEFENSE.
 * ---------------------------------------------------------------------------
 * CROWN CLIMB phase 8 ("district GUARDING") + the STAKES-LOOP base-defense leg
 * (AK_MASTER_BUILD_PLAN: Crew Wars / guard turf). This is the DEFENSE-LAYOUT layer:
 * the player PLACES their own deck cards as DEFENDERS of a district they control,
 * and the raid / night-defense reads that layout to staff the block.
 *
 * WHAT IT DOES (real, not a stub):
 *   - window.akOpenGuard(zoneId) opens a lazy-DOM overlay (built on open, removed
 *     on close -- 60fps-safe, no per-frame work). It shows the district, its
 *     control status, and GUARD SLOTS. Each slot is filled from your DECK (then
 *     the rest of your owned cards) -- the dogs ARE the people defending the block.
 *   - The layout persists as p.guards = { zoneId: [cardName, ...] } in AK_ECON
 *     (falsy-default, lazily created on the first post -- zero-state byte-identical;
 *     economy.js ensureShape is FROZEN so we never touch it, exactly like p.crew).
 *   - Guard slot CAP scales with Town Hall (guardCap(th)) and is gated by DISTRICT
 *     CONTROL: you can only post defenders to a district you HOLD (ctx.ZONES, not
 *     locked). Locked / un-held districts show a "raid and hold it first" message.
 *   - DEFENSE STATE the raid / base-defense reads (the contract that systems/raid.js
 *     consumes): AKGuard.defenseFor(zid) -> { controlled, count, cap, power, patrol,
 *     total, coreBonus, cards }. Defense POWER is derived ONLY from earned card
 *     levels x Town Hall (parity-safe -- never gems, never a paid stat). It also
 *     folds in any buildmode crew dog stationed on task 'guard' for that zone as a
 *     PATROL defender (buildmode sets c.task='guard', c.target=zoneId). alliesFor(zid)
 *     hands the night-defense a ready turret list (hp/dmg per defender).
 *
 * HARD LAW honored (every line):
 *   - engine.js is FROZEN. This module layers via AK_CTX (overlay host / ZONES /
 *     cards) + AK_ECON only -- it edits NO shared host file.
 *   - ONE economy = AK_ECON. Every profile read/write goes through AK_ECON
 *     (loadProfile / mutateProfile), falsy-default on write, lazily-created p.guards.
 *   - Gems are cosmetic/skip/pay-ONLY, never power/loot. Posting a guard is FREE
 *     (a layout, like CoC defense placement); this module never reads/grants/spends
 *     gems and defense power is 100% earned.
 *   - Soft-currency only. No $BCARDD / ALK anywhere. Cards are reused BY NAME from
 *     the live 106-card roster (ctx.cards()).
 *   - No em-dashes (use --). 60fps hub: lazy DOM, no per-frame heavy work.
 *
 * Headless-safe: zero top-level DOM / localStorage; bails where AK_SYSTEMS is
 * absent (battler / node harness). XSS-safe by construction (mk() -> textContent
 * for every dynamic string; no innerHTML for card names). Plain browser JS.
 */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;                 // hub-only module

  var ID = 'guard';
  var GOLD = '#e8c55a', GOLD_DK = '#c9a84c', DIM = '#b9a76a', GREEN = '#7CFFB0', RED = '#f3a0a0';

  // rarity -> accent (mirrors modes.js rarityColor so the overlay reads like the deck)
  var RAR_COLOR = { Common: '#9fb0c0', Rare: '#5ad0c0', Epic: '#c9a8ff', Legendary: '#ffd76b', Mythic: '#ff8fae' };
  // rarity -> defense base (the unit's standing-guard worth before level + TH scale).
  // EARNED only -- bigger rarity is a bigger card you already own, never a paid stat.
  var RAR_BASE = { Common: 6, Rare: 10, Epic: 16, Legendary: 24, Mythic: 36 };

  // ---- module-local runtime (never persisted) -------------------------------
  var CTX = null;
  var S = { root: null, body: null, zid: null, pickSlot: -1, built: false };

  /* ====================================================================== *
   * ECONOMY / CARD HELPERS (prefer AK_ECON contracts; design-exact fallbacks)
   * ====================================================================== */
  function econ() { try { return CTX && CTX.econ ? CTX.econ : (global.AK_ECON || null); } catch (_) { return null; } }
  function freshProfile() { try { var e = econ(); return e ? e.loadProfile() : null; } catch (_) { return null; } }
  function thOf(p) { try { if (global.AK_ECON && AK_ECON.townHallLevel) return AK_ECON.townHallLevel(p); } catch (_) {} return Math.max(1, Math.min(10, (p && p.townHall | 0) || 1)); }
  function cardLevelOf(p, name) { try { if (global.AK_ECON && AK_ECON.cardLevel) return AK_ECON.cardLevel(p, name); } catch (_) {} var v = p && p.cardLvls && p.cardLvls[name]; return Math.max(1, Math.min(10, Math.floor(v || 1))); }
  function builderSpeed(cardLvl, th) { try { if (global.AK_ECON && AK_ECON.builderSpeed) return AK_ECON.builderSpeed(cardLvl, th); } catch (_) {} cardLvl = Math.max(1, cardLvl | 0); th = Math.max(1, th | 0); return (1 + 0.08 * (cardLvl - 1)) * (1 + 0.05 * (th - 1)); }

  function cardTable() { try { return (CTX && CTX.cards && CTX.cards()) || {}; } catch (_) { return {}; } }
  function cardInfo(name) { var t = cardTable(); return (name && t[name]) || null; }
  function rarityOf(name) { var c = cardInfo(name); return (c && c.rarity) || 'Common'; }
  function cardNumOf(name) { var c = cardInfo(name); return (c && (c.cardNumber || c.id)) || null; }

  // PORTRAIT resolver -- reuses the hub's canonical akCardArtRel + CANON_CARDS path
  // (the exact one index.html openPicker / dogArt use). No new art path is introduced.
  function artFor(name) {
    try {
      var L = global.CANON_CARDS || [];
      for (var i = 0; i < L.length; i++) {
        var c = L[i];
        if (c && (c.name === name || c.id === name || String(c.cardNumber) === String(name))) {
          if (global.akCardArtRel) { var rel = akCardArtRel(c); if (rel) return 'assets/' + rel; }
          break;
        }
      }
    } catch (_) {}
    return '';
  }

  // ---- TYPE layer (AK_TYPES Volt/Bone/Phantom/Zoom) -- defense COMPOSITION ---
  // A defender's element is faction-derived (one source of truth -- systems/types.js).
  // typeEff(def, atk) is the DEFENSE multiplier of a defender of type `def` standing
  // against a raid of type `atk`: 1.2 when our dog counters the raider, 0.8 when the
  // raider counters our dog, 1.0 otherwise (the same 4-cycle, read from the defender's
  // stance). All defensive -- never reads/grants/spends gems; pure earned card data.
  function typesApi() { try { return global.AK_TYPES || null; } catch (_) { return null; } }
  function typeOfCard(name) { var T = typesApi(); if (T && T.typeOf) { try { return T.typeOf(name) || 'Stray'; } catch (_) {} } return 'Stray'; }
  function typeEff(def, atk) { var T = typesApi(); if (T && T.eff) { try { return T.eff(def, atk); } catch (_) {} } return 1.0; }
  function typeIcon(t) { var T = typesApi(); if (T && T.icon) { try { return T.icon(t); } catch (_) {} } return ''; }
  function typeColor(t) { var T = typesApi(); if (T && T.color) { try { return T.color(t); } catch (_) {} } return DIM; }
  // the raid element a defender of type `t` HARD-COUNTERS (BEATS[t]) -- used for hints.
  function countersOf(t) { var T = typesApi(); try { return (T && T.BEATS && T.BEATS[t]) || null; } catch (_) { return null; } }

  function ownedNames(p) { return (p && Array.isArray(p.owned)) ? p.owned.slice() : []; }
  // the active deck (the dogs you field) -- mirrors modes.js playerHeroName fallback chain
  function deckNames(p) { var d = p && (p.deck || p.activeDeck || p.deckNames); return Array.isArray(d) ? d.filter(Boolean) : []; }

  /* ====================================================================== *
   * DISTRICT CONTROL + GUARD CAP
   * ====================================================================== */
  function zoneName(zid) { try { var z = CTX && CTX.ZONES && CTX.ZONES[zid]; return (z && (z.name || z.label)) || zid || 'THIS BLOCK'; } catch (_) { return zid || 'THIS BLOCK'; } }
  // you can only post guards on a district you HOLD (exists in ZONES + not locked).
  function controlled(zid) { try { var z = CTX && CTX.ZONES && CTX.ZONES[zid]; return !!(z && !z.locked); } catch (_) { return false; } }
  // guard slots per district scale with Town Hall (prefer an AK_ECON contract if it
  // ever lands; else the local table). Capped at 8 (below a full deck) so a district
  // is staffed, not stacked. TH1 = 2 .. TH10 = 7.
  function guardCap(th) {
    try { if (global.AK_ECON && AK_ECON.guardCap) return AK_ECON.guardCap(th); } catch (_) {}
    th = Math.max(1, Math.min(10, th | 0));
    return Math.max(2, Math.min(8, 2 + Math.floor(th / 2)));
  }
  function capFor(zid) { var p = freshProfile(); return guardCap(thOf(p)); }

  /* ====================================================================== *
   * GUARD LAYOUT STATE  (p.guards = { zoneId: [cardName,...] }; falsy-default)
   * ====================================================================== */
  function layoutOf(p, zid) { var g = p && p.guards && p.guards[zid]; return Array.isArray(g) ? g.filter(Boolean) : []; }
  // owned-only, de-duped, clamped to the cap -- the canonical posted-defender list.
  function postedFor(p, zid) {
    p = p || freshProfile();
    var raw = layoutOf(p, zid), owned = ownedNames(p), seen = {}, out = [], cap = guardCap(thOf(p));
    for (var i = 0; i < raw.length && out.length < cap; i++) {
      var nm = raw[i]; if (!nm || seen[nm]) continue;
      if (owned.length && owned.indexOf(nm) < 0) continue;   // a card you no longer hold cannot defend
      seen[nm] = 1; out.push(nm);
    }
    return out;
  }
  // slot view for the overlay: cap entries, each {slot, card|null, lvl, rarity, power}
  function slotList(zid) {
    var p = freshProfile(), th = thOf(p), cap = guardCap(th), posted = postedFor(p, zid), out = [];
    for (var s = 0; s < cap; s++) {
      var nm = posted[s] || null, lvl = nm ? cardLevelOf(p, nm) : 1;
      out.push({ slot: s, card: nm, lvl: lvl, rarity: nm ? rarityOf(nm) : null, type: nm ? typeOfCard(nm) : null, power: nm ? cardPower(nm, lvl, th) : 0 });
    }
    return out;
  }

  // a single defender's standing-guard power (EARNED: rarity x level x Town Hall).
  function cardPower(name, lvl, th) {
    var base = RAR_BASE[rarityOf(name)] || RAR_BASE.Common;
    return Math.max(1, Math.round(base * (1 + 0.12 * (Math.max(1, lvl | 0) - 1)) * (1 + 0.05 * (Math.max(1, th | 0) - 1))));
  }

  // buildmode crew dogs stationed on task 'guard' for this zone = PATROL defenders.
  // Reads p.crew (buildmode's slot state) defensively; each adds a modest patrol
  // power (scaled by the SAME builderSpeed skill<->TH curve), capped so patrol never
  // dwarfs the posted deck layout.
  function patrolFor(p, zid) {
    p = p || freshProfile(); var crew = (p && p.crew) || {}, th = thOf(p), out = [];
    for (var k in crew) {
      if (!crew.hasOwnProperty(k)) continue;
      var c = crew[k]; if (!c || c.task !== 'guard') continue;
      if (c.target && c.target !== zid) continue;          // patrols only its posted zone
      var lvl = c.card ? cardLevelOf(p, c.card) : 1;
      out.push({ slot: k | 0, card: c.card || null, lvl: lvl, power: Math.max(1, Math.round(8 * builderSpeed(lvl, th))) });
    }
    return out;
  }

  /* ====================================================================== *
   * DEFENSE STATE -- the contract systems/raid.js + night-defense read
   * ====================================================================== */
  // The marquee defender list (posted deck cards) with computed power + card number.
  function defendersFor(zid) {
    zid = zid || (CTX && CTX.zoneId);
    var p = freshProfile(), th = thOf(p), posted = postedFor(p, zid), out = [];
    for (var i = 0; i < posted.length; i++) {
      var nm = posted[i], lvl = cardLevelOf(p, nm), rar = rarityOf(nm);
      out.push({ name: nm, cardNumber: cardNumOf(nm), rarity: rar, type: typeOfCard(nm), lvl: lvl, power: cardPower(nm, lvl, th) });
    }
    return out;
  }

  /* ====================================================================== *
   * DEFENSE COMPOSITION  -- why WHICH dogs you post matters, not just how many.
   * A district staffed with one element gets shredded by the raid that counters
   * it; a balanced spread closes every angle. composition() reads the posted
   * defenders' TYPES (AK_TYPES) and yields: the per-element spread, distinct-type
   * count, an effective-defense RATIO vs each of the 4 raid elements (1.0 = flat,
   * >1 strong, <1 soft), the weakest/strongest matchup, and a modest EARNED
   * coverage multiplier for a diverse block. Parity-safe -- never touches gems.
   * ====================================================================== */
  var RAID_ELEMENTS = ['Volt', 'Bone', 'Phantom', 'Zoom'];
  function composition(zid) {
    zid = zid || (CTX && CTX.zoneId);
    var defs = defendersFor(zid), spread = {}, order = [], totalPow = 0, distinct = 0, i;
    for (i = 0; i < defs.length; i++) {
      var t = defs[i].type || 'Stray', pw = defs[i].power;
      if (spread[t] == null) { spread[t] = 0; order.push(t); if (t !== 'Stray') distinct++; }
      spread[t] += pw; totalPow += pw;
    }
    // effective-defense ratio vs each raid element (power-weighted type matchup)
    var vs = {}, weakType = null, weakR = 99, strongType = null, strongR = -1;
    for (var a = 0; a < RAID_ELEMENTS.length; a++) {
      var atk = RAID_ELEMENTS[a], eff = 0;
      for (i = 0; i < defs.length; i++) eff += defs[i].power * typeEff(defs[i].type, atk);
      var ratio = totalPow > 0 ? (eff / totalPow) : 1.0;
      vs[atk] = ratio;
      if (ratio < weakR) { weakR = ratio; weakType = atk; }
      if (ratio > strongR) { strongR = ratio; strongType = atk; }
    }
    // a balanced spread earns a small, capped coverage edge; a one-flavor block earns
    // nothing (and stays exposed via the vs<1 weakness above). 2 types +6%..4 types +18%.
    var compMult = distinct <= 1 ? 1.0 : (1 + Math.min(3, distinct - 1) * 0.06);
    return {
      spread: spread, order: order, distinct: distinct, totalPower: totalPow, vs: vs,
      weakType: totalPow > 0 ? weakType : null, weakRatio: weakR,
      strongType: totalPow > 0 ? strongType : null, strongRatio: strongR,
      compMult: compMult
    };
  }

  // the ONE base-defense read. coreBonus = extra core HP the night-defense can add on
  // top of its base (a strong, real defense makes The Lot tougher); capped + parity-safe.
  // comp = bonus power earned by a diverse type spread (composition matters).
  function defenseFor(zid) {
    zid = zid || (CTX && CTX.zoneId);
    var p = freshProfile(), th = thOf(p), held = controlled(zid);
    var defs = held ? defendersFor(zid) : [], patrol = held ? patrolFor(p, zid) : [];
    var power = 0, names = [], i;
    for (i = 0; i < defs.length; i++) { power += defs[i].power; names.push(defs[i].name); }
    var pat = 0; for (i = 0; i < patrol.length; i++) pat += patrol[i].power;
    var comp = held ? composition(zid) : null;
    var compMult = comp ? comp.compMult : 1.0;
    var compBonus = Math.max(0, Math.round(power * (compMult - 1)));
    var total = power + pat + compBonus;
    return {
      zoneId: zid, controlled: held, cap: guardCap(th), count: defs.length,
      power: power, patrol: pat, comp: compBonus, compMult: compMult, total: total,
      types: comp ? comp.spread : {}, distinct: comp ? comp.distinct : 0,
      weakType: comp ? comp.weakType : null, strongType: comp ? comp.strongType : null,
      coverage: comp ? comp.vs : {},
      coreBonus: Math.max(0, Math.min(400, Math.round(total * 0.6))),
      cards: names, defenders: defs, patrols: patrol
    };
  }
  // the TYPE-AWARE base-defense read the raid uses when the incoming raid has a known
  // element: scales each posted defender by its matchup vs the attacker, so a raider
  // who brings the counter-type is rewarded and a balanced block holds. Patrol +
  // composition bonus ride along unscaled (they are not single-element). Returns the
  // full defenseFor object with effectivePower / effectiveTotal / typeMult added.
  function defenseVsType(zid, attackerType) {
    var base = defenseFor(zid), defs = base.defenders || [];
    if (!attackerType || !defs.length) {
      base.attackerType = attackerType || null; base.effectivePower = base.power;
      base.effectiveTotal = base.total; base.typeMult = 1.0; return base;
    }
    var eff = 0; for (var i = 0; i < defs.length; i++) eff += defs[i].power * typeEff(defs[i].type, attackerType);
    eff = Math.round(eff);
    base.attackerType = attackerType; base.effectivePower = eff;
    base.effectiveTotal = eff + base.patrol + (base.comp || 0);
    base.typeMult = base.power > 0 ? (eff / base.power) : 1.0;
    return base;
  }
  // a night-defense-ready turret/ally list (real cards) sized to the posted layout.
  // hp/dmg derived from the same EARNED power -- a future raid.js night-defense edit
  // drops these in as st.allies (parity-safe PvE).
  function alliesFor(zid) {
    var defs = defendersFor(zid), out = [];
    for (var i = 0; i < defs.length; i++) {
      var d = defs[i], rare = (d.rarity === 'Epic' || d.rarity === 'Legendary' || d.rarity === 'Mythic');
      out.push({ name: d.name, cardNumber: d.cardNumber, type: d.type, rare: rare, hp: Math.max(6, Math.round(d.power * 0.5)), dmg: Math.max(1, Math.round(d.power * 0.12)) });
    }
    return out;
  }

  /* ====================================================================== *
   * MUTATORS -- assign / unassign / clear (atomic, falsy-default, lazy p.guards)
   * ====================================================================== */
  function ensureLayout(p, zid) {
    if (!p.guards || typeof p.guards !== 'object') p.guards = {};
    if (!Array.isArray(p.guards[zid])) p.guards[zid] = [];
    return p.guards[zid];
  }
  function assign(zid, slot, cardName) {
    zid = zid || (CTX && CTX.zoneId); slot = slot | 0;
    if (!controlled(zid)) return { ok: false, error: 'NOT_HELD' };
    var p0 = freshProfile(); var cap = guardCap(thOf(p0));
    if (slot < 0 || slot >= cap) return { ok: false, error: 'OVER_CAP', cap: cap };
    if (!cardName) return { ok: false, error: 'NO_CARD' };
    if (Array.isArray(p0.owned) && p0.owned.indexOf(cardName) < 0) return { ok: false, error: 'CARD_NOT_OWNED' };
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    e.mutateProfile(function (p) {
      var arr = ensureLayout(p, zid);
      // a dog defends ONE post per district -- pull it from any other slot first.
      for (var j = 0; j < arr.length; j++) { if (arr[j] === cardName) arr[j] = null; }
      while (arr.length <= slot) arr.push(null);
      arr[slot] = cardName;
      while (arr.length > cap) arr.pop();
    });
    refresh();
    try { if (!window._akStingT) window._akStingT = {}; var _ts = Date.now(); if ((window._akStingT.watch_posted || 0) + 60000 < _ts) { window._akStingT.watch_posted = _ts; if (window.akPlayCinematic) akPlayCinematic('watch_posted'); } } catch (_e) {}  // STINGER (60s throttle -- high-frequency action)
    return { ok: true, zoneId: zid, slot: slot, card: cardName };
  }
  function unassign(zid, slot) {
    zid = zid || (CTX && CTX.zoneId); slot = slot | 0;
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    e.mutateProfile(function (p) { var arr = p.guards && p.guards[zid]; if (Array.isArray(arr) && slot >= 0 && slot < arr.length) arr[slot] = null; });
    refresh();
    return { ok: true, zoneId: zid, slot: slot };
  }
  function clear(zid) {
    zid = zid || (CTX && CTX.zoneId);
    var e = econ(); if (!e) return { ok: false, error: 'NO_ECON' };
    e.mutateProfile(function (p) { if (p.guards && p.guards[zid]) p.guards[zid] = []; });
    refresh();
    return { ok: true, zoneId: zid };
  }

  /* ====================================================================== *
   * OVERLAY  (window.akOpenGuard) -- lazy DOM, built on open, hidden on close
   * ====================================================================== */
  function mk(tag, css, text) { var e = document.createElement(tag); if (css) e.style.cssText = css; if (text != null) e.textContent = text; return e; }
  function btnPrimary() { return 'background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;border-radius:9px;padding:8px 12px;font-weight:900;font-size:11px;letter-spacing:.03em;cursor:pointer;-webkit-tap-highlight-color:transparent;'; }
  function btnGhost() { return 'background:none;border:1px solid rgba(201,168,76,.5);color:#b9a76a;border-radius:9px;padding:8px 11px;font-weight:800;font-size:11px;cursor:pointer;-webkit-tap-highlight-color:transparent;'; }

  // the accent of the district you HOLD (gold fallback) -- mirrors index.html openPicker's
  // AK_DISTRICTS.info(...).accent so THE WATCH reads in the same colour as the block you own.
  function heldAccent() {
    try { var di = global.AK_DISTRICTS && AK_DISTRICTS.info ? AK_DISTRICTS.info(S.zid) : null; return (di && di.accent) || GOLD; } catch (_) { return GOLD; }
  }
  // circular card-art portrait (the chop-shop tile look) -- img with webp->png->dog-glyph
  // fallback (reuses global.akImgErr). Built with createElement, no innerHTML (XSS-safe).
  function dogAvatar(name, px, ringColor) {
    var wrap = mk('span', 'position:relative;flex:0 0 auto;width:' + px + 'px;height:' + px + 'px;border-radius:50%;overflow:hidden;' +
      'border:2px solid ' + ringColor + ';background:radial-gradient(circle at 50% 38%,rgba(201,168,76,.22),rgba(10,10,16,.9));' +
      'display:flex;align-items:center;justify-content:center;font-size:' + Math.round(px * 0.46) + 'px;');
    var art = artFor(name);
    if (art) {
      var img = document.createElement('img'); img.alt = ''; img.src = art;
      img.style.cssText = 'width:100%;height:100%;object-fit:cover;object-position:center top;';
      img.onerror = function () { if (!(global.akImgErr && akImgErr(img))) { try { wrap.removeChild(img); wrap.textContent = '\u{1F415}'; } catch (_) {} } };
      wrap.appendChild(img);
    } else { wrap.textContent = '\u{1F415}'; }
    return wrap;
  }

  function ensureRoot() {
    if (S.built || typeof document === 'undefined') return;
    var ov = mk('div', 'position:fixed;inset:0;z-index:40;display:none;align-items:flex-end;justify-content:center;' +
      'background:rgba(6,6,10,.86);font-family:Inter,system-ui,sans-serif;-webkit-tap-highlight-color:transparent;');
    ov.id = 'ak-guard-ov';
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });   // tap the scrim to dismiss
    var card = mk('div', 'width:100%;max-width:560px;max-height:86dvh;overflow-y:auto;margin:0 8px;' +
      'padding:14px 14px calc(14px + env(safe-area-inset-bottom));border-radius:16px 16px 0 0;' +
      'background:rgba(10,9,14,.98);border:1px solid rgba(201,168,76,.5);border-bottom:none;box-shadow:0 -6px 30px rgba(0,0,0,.6);');
    card.id = 'ak-guard-card';
    card.addEventListener('click', function (e) { e.stopPropagation(); });
    ov.appendChild(card); document.body.appendChild(ov);
    S.root = ov; S.body = card; S.built = true;
  }
  function openGuard(zoneId) {
    if (typeof document === 'undefined') return { ok: false, error: 'NO_DOM' };
    CTX = CTX || global.AK_CTX || null;
    S.zid = zoneId || (CTX && CTX.zoneId) || null;
    S.pickSlot = -1;
    ensureRoot(); if (!S.root) return { ok: false, error: 'NO_DOM' };
    render(); S.root.style.display = 'flex';
    return { ok: true, zoneId: S.zid };
  }
  function close() { if (S.root) S.root.style.display = 'none'; S.pickSlot = -1; }
  function refresh() { if (S.root && S.root.style.display !== 'none') render(); }

  function header() {
    var def = defenseFor(S.zid);
    var wrap = mk('div', 'margin-bottom:8px;');
    var top = mk('div', 'display:flex;align-items:center;gap:8px;');
    top.appendChild(mk('span', 'font-size:18px;line-height:1;', '🛡️'));
    top.appendChild(mk('span', 'flex:1;color:#e8c55a;font-weight:900;font-size:13px;letter-spacing:.05em;', 'DISTRICT DEFENSE -- ' + zoneName(S.zid)));
    var x = mk('button', btnGhost(), 'CLOSE'); x.type = 'button'; x.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    top.appendChild(x);
    wrap.appendChild(top);
    var sub = mk('div', 'color:' + (def.controlled ? DIM : RED) + ';font-size:10px;font-weight:700;margin-top:4px;');
    sub.textContent = def.controlled
      ? ('HELD -- ' + def.count + '/' + def.cap + ' posted  ·  DEF POWER ' + def.total + (def.patrol ? (' (+' + def.patrol + ' patrol)') : '') + '  ·  core +' + def.coreBonus)
      : 'NOT HELD -- raid and hold this block before you can post defenders.';
    wrap.appendChild(sub);
    return wrap;
  }

  function render() {
    if (!S.body) return;
    S.body.replaceChildren();
    S.body.appendChild(header());
    if (!controlled(S.zid)) {
      var lock = mk('div', 'color:#b9a76a;font-size:12px;line-height:1.5;padding:14px 4px;');
      lock.textContent = 'This district is not under your control. Win it on the WAR MAP, then come back to post your deck as its defenders.';
      S.body.appendChild(lock);
      return;
    }
    if (S.pickSlot >= 0) { renderPicker(); return; }
    renderSlots();
  }

  function renderSlots() {
    var slots = slotList(S.zid), accent = heldAccent();
    slots.forEach(function (s) {
      var row = mk('div', 'display:flex;align-items:center;gap:9px;padding:8px 4px;border-bottom:1px solid rgba(201,168,76,.18);');
      // the dog's FACE stands the post (chop-shop card-art look), not a color dot
      if (s.card) { row.appendChild(dogAvatar(s.card, 40, (RAR_COLOR[s.rarity] || GOLD) + 'cc')); }
      else { row.appendChild(mk('span', 'position:relative;flex:0 0 auto;width:40px;height:40px;border-radius:50%;border:1.5px dashed ' + accent + '66;background:rgba(10,10,16,.5);display:flex;align-items:center;justify-content:center;color:' + DIM + ';font-size:20px;font-weight:400;', '+')); }
      var name = mk('button', 'flex:1;text-align:left;background:none;border:none;color:' + (s.card ? '#E8E8E8' : DIM) + ';font-weight:800;font-size:12px;cursor:pointer;-webkit-tap-highlight-color:transparent;');
      name.type = 'button';
      var tg = (s.card && s.type && s.type !== 'Stray') ? (typeIcon(s.type) + ' ') : '';
      name.textContent = s.card ? (tg + s.card + '  Lv' + s.lvl) : ('+ POST DEFENDER #' + (s.slot + 1));
      name.addEventListener('click', (function (slot) { return function (e) { e.stopPropagation(); S.pickSlot = slot; render(); }; })(s.slot));
      row.appendChild(name);
      if (s.card) {
        var pwr = mk('span', 'color:#e8c55a;font-weight:900;font-size:11px;min-width:46px;text-align:right;', 'DEF ' + s.power);
        row.appendChild(pwr);
        var rm = mk('button', btnGhost() + 'min-width:64px;', 'REMOVE'); rm.type = 'button';
        rm.addEventListener('click', (function (slot) { return function (e) { e.stopPropagation(); unassign(S.zid, slot); }; })(s.slot));
        row.appendChild(rm);
      } else {
        var add = mk('button', btnPrimary() + 'min-width:64px;', 'ASSIGN'); add.type = 'button';
        add.addEventListener('click', (function (slot) { return function (e) { e.stopPropagation(); S.pickSlot = slot; render(); }; })(s.slot));
        row.appendChild(add);
      }
      S.body.appendChild(row);
    });
    var comp = compositionPanel();
    if (comp) S.body.appendChild(comp);
    var foot = mk('div', 'display:flex;gap:8px;margin-top:10px;');
    var clr = mk('button', btnGhost() + 'flex:1;', 'CLEAR ALL'); clr.type = 'button';
    clr.addEventListener('click', function (e) { e.stopPropagation(); clear(S.zid); });
    var done = mk('button', btnPrimary() + 'flex:2;', 'DONE'); done.type = 'button';
    done.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    foot.appendChild(clr); foot.appendChild(done);
    S.body.appendChild(foot);
    var note = mk('div', 'color:#8a7f5e;font-size:9px;margin-top:8px;line-height:1.4;');
    note.textContent = 'Your posted dogs defend this block when rivals raid -- their level x Town Hall sets the defense power, and a mixed-element block (Volt / Bone / Phantom / Zoom) closes every raid angle. Posting is free. Gems never buy defense.';
    S.body.appendChild(note);
  }

  // PACK COMPOSITION -- a cheap, render-time panel that makes WHICH types you post
  // legible: the element spread, a coverage edge, and the raid you are soft against.
  function compositionPanel() {
    var def = defenseFor(S.zid);
    if (!def.count) return null;
    var wrap = mk('div', 'margin-top:11px;padding:9px 10px;border-radius:10px;background:rgba(20,18,26,.6);border:1px solid rgba(201,168,76,.22);');
    var ttl = mk('div', 'color:#e8c55a;font-weight:900;font-size:10px;letter-spacing:.06em;margin-bottom:7px;',
      'PACK COMPOSITION' + (def.distinct >= 2 ? ('  ·  +' + Math.round((def.compMult - 1) * 100) + '% coverage') : ''));
    wrap.appendChild(ttl);
    var chips = mk('div', 'display:flex;flex-wrap:wrap;gap:6px;');
    var sp = def.types || {}, any = false;
    for (var t in sp) {
      if (!sp.hasOwnProperty(t) || t === 'Stray') continue; any = true;
      var col = typeColor(t);
      var c = mk('span', 'display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:800;padding:2px 8px;border-radius:20px;background:rgba(0,0,0,.3);border:1px solid ' + col + '66;color:' + col + ';', typeIcon(t) + ' ' + t);
      chips.appendChild(c);
    }
    if (sp.Stray) chips.appendChild(mk('span', 'font-size:11px;font-weight:800;padding:2px 8px;border-radius:20px;background:rgba(0,0,0,.3);border:1px solid rgba(201,168,76,.35);color:' + DIM + ';', '🐾 Stray'));
    wrap.appendChild(chips);
    // weakest / strongest raid matchup (only when the spread actually tilts it)
    var cov = def.coverage || {}, wk = def.weakType, st = def.strongType;
    if (any && wk && cov[wk] < 0.995) {
      var cnt = null, T = typesApi(); if (T && T.BEATS) { for (var k in T.BEATS) { if (T.BEATS[k] === wk) { cnt = k; break; } } }
      var w = mk('div', 'margin-top:7px;font-size:10px;font-weight:700;line-height:1.5;color:' + RED + ';',
        'SOFT vs ' + typeIcon(wk) + ' ' + wk + ' raids (x' + cov[wk].toFixed(2) + ')' + (cnt ? (' -- post a ' + typeIcon(cnt) + ' ' + cnt + ' dog to plug it.') : '.'));
      wrap.appendChild(w);
    }
    if (any && st && cov[st] > 1.005) {
      var s2 = mk('div', 'margin-top:4px;font-size:10px;font-weight:700;line-height:1.5;color:' + GREEN + ';',
        'HARD vs ' + typeIcon(st) + ' ' + st + ' raids (x' + cov[st].toFixed(2) + ').');
      wrap.appendChild(s2);
    }
    return wrap;
  }

  function renderPicker() {
    var p = freshProfile(), th = thOf(p), slot = S.pickSlot, accent = heldAccent();
    var posted = postedFor(p, S.zid), postedSet = {}; posted.forEach(function (n) { postedSet[n] = 1; });
    var slotCard = posted[slot] || null;   // the dog STANDING this post right now (stationed highlight)
    var hdr = mk('div', 'color:#e8c55a;font-weight:900;font-size:12px;margin:6px 0 3px;', 'PICK A DEFENDER FOR POST #' + (slot + 1));
    S.body.appendChild(hdr);
    S.body.appendChild(mk('div', 'color:' + DIM + ';font-size:10px;margin:0 0 11px;', 'Tap a dog to post it. Your deck leads -- a green ring means already on patrol.'));
    // deck cards lead (the dogs you field), then the rest of your owned roster.
    var deck = deckNames(p), owned = ownedNames(p), seen = {}, ordered = [];
    deck.forEach(function (n) { if (n && !seen[n] && owned.indexOf(n) >= 0) { seen[n] = 1; ordered.push({ name: n, deck: true }); } });
    owned.forEach(function (n) { if (n && !seen[n]) { seen[n] = 1; ordered.push({ name: n, deck: false }); } });
    if (!ordered.length) {
      S.body.appendChild(mk('div', 'color:#b9a76a;font-size:11px;padding:8px 4px;', 'No cards owned yet -- win matches or open chests to recruit defenders.'));
    } else {
      // 3-column card-art grid (mirrors index.html openPicker): the dog's real portrait,
      // its name, a level/DEF meta line, and the held-district accent ring.
      var grid = mk('div', 'display:grid;grid-template-columns:repeat(3,1fr);gap:9px;');
      ordered.forEach(function (it) {
        var nm = it.name, lvl = cardLevelOf(p, nm), rar = rarityOf(nm), typ = typeOfCard(nm);
        var here = !!postedSet[nm], stationedHere = (nm === slotCard);
        var rarCol = RAR_COLOR[rar] || DIM;
        var ringCol = stationedHere ? accent : (here ? GREEN : rarCol);
        var tile = mk('button', 'position:relative;display:flex;flex-direction:column;align-items:center;gap:5px;padding:8px 5px;border-radius:12px;cursor:pointer;-webkit-tap-highlight-color:transparent;transition:transform .1s ease;' +
          'border:1.5px solid ' + (stationedHere ? accent : (here ? 'rgba(124,255,176,.55)' : 'rgba(201,168,76,.28)')) + ';' +
          'background:' + (stationedHere ? (accent + '1f') : 'rgba(20,18,26,.85)') + ';');
        tile.type = 'button';
        tile.appendChild(dogAvatar(nm, 54, ringCol + 'cc'));
        tile.appendChild(mk('span', 'font-size:10px;font-weight:800;color:' + (stationedHere ? '#fff' : '#d9c688') + ';line-height:1.15;text-align:center;max-width:82px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', nm));
        var tIcon = (typ && typ !== 'Stray') ? (typeIcon(typ) + ' ') : '';
        tile.appendChild(mk('span', 'font-size:9px;font-weight:800;color:#e8c55a;', tIcon + 'Lv' + lvl + '  DEF ' + cardPower(nm, lvl, th)));
        tile.appendChild(mk('span', 'position:absolute;top:5px;left:6px;width:8px;height:8px;border-radius:50%;background:' + rarCol + ';'));
        if (it.deck) tile.appendChild(mk('span', 'position:absolute;top:4px;right:6px;font-size:7px;font-weight:900;color:' + accent + ';letter-spacing:.05em;', 'DECK'));
        if (stationedHere) tile.appendChild(mk('span', 'position:absolute;bottom:3px;right:5px;font-size:11px;line-height:1;', '\u{1F6E1}\u{FE0F}'));      // stationed at THIS post
        else if (here) tile.appendChild(mk('span', 'position:absolute;bottom:3px;right:5px;font-size:10px;line-height:1;', '\u{2705}'));                  // posted elsewhere on this block
        tile.addEventListener('click', (function (name) { return function (e) { e.stopPropagation(); assign(S.zid, slot, name); S.pickSlot = -1; render(); }; })(nm));
        grid.appendChild(tile);
      });
      S.body.appendChild(grid);
    }
    var back = mk('button', btnGhost() + 'width:100%;margin-top:11px;', 'BACK'); back.type = 'button';
    back.addEventListener('click', function (e) { e.stopPropagation(); S.pickSlot = -1; render(); });
    S.body.appendChild(back);
  }

  /* ====================================================================== *
   * MODULE REGISTRATION
   * ====================================================================== */
  global.AK_SYSTEMS.register({
    id: ID,
    init: function (ctx) { CTX = ctx || global.AK_CTX || CTX; },
    onEnterBuilding: function (b, ctx) { return false; },   // guard owns NO interior
    onTick: function (dt, ctx) { CTX = ctx || CTX; },        // no per-frame work (60fps)
    onDrawWorld: function (ctx) {}                            // overlay + state only; raid.js draws defense pips
  });

  // public API: the akOpenGuard overlay entry (wired onto the buildmode GUARD button
  // + future HUD chip) + the DEFENSE-STATE contract systems/raid.js reads.
  global.akOpenGuard = openGuard;
  global.AKGuard = {
    open: openGuard, close: close,
    // defense-state reads (the raid / base-defense contract)
    defenseFor: defenseFor, defendersFor: defendersFor, alliesFor: alliesFor,
    // TYPE-aware reads -- composition + a raid-element-scaled defense the raid consumes
    composition: composition, defenseVsType: defenseVsType,
    controlled: controlled, cap: capFor, guardCap: guardCap,
    // layout mutators + slot view
    list: slotList, assign: assign, unassign: unassign, clear: clear
  };

})(typeof window !== 'undefined' ? window : globalThis);
