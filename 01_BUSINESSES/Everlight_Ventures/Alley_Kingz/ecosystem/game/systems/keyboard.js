/*
 * keyboard.js -- AK_KEYS (hybrid keyboard + hotkey layer)
 * Makes Alley Kingz fully playable on a keyboard, not just touch. Two surfaces
 * register their own actions; this module owns key listening, an on-screen HELP
 * card (press ?), and a QUICK-TRAVEL palette (press Tab in the hub). It never
 * knows page internals -- each page hands it closures, so the same module drives
 * the world hub (index.html) and the battler (game.html) with zero coupling.
 *
 *  HUB (index.html) -- movement (WASD/arrows) stays with the page's own loop;
 *  this layer adds:
 *    E / Enter / Space  interact: enter the building you are on, accept the
 *                       encounter in front of you, or talk to the NPC.
 *    1..9               fast-travel to district N (the Quick-Travel order).
 *    Tab                open the Quick-Travel palette (districts + every mode).
 *    R raid   T town hall   F fence   G the watch   C crew   B build
 *    M world map   I infirmary   Y story
 *    Esc                close the top panel / back to the district map.
 *
 *  BATTLE (game.html) -- the arena is touch-only today; this layer adds:
 *    1..4               select hand slot 1-4 (the four dogs you deploy).
 *    Arrows / WASD      move the deploy cursor inside your half.
 *    Space / Enter      deploy the selected dog at the cursor.
 *    Esc                cancel the selection (double-tap surrenders via cancel()).
 *
 * Global: ? toggles the HELP card. Typing in any input is always respected
 * (every hotkey is suppressed while a field/contenteditable is focused).
 *
 * Plain JS, window-guarded, node --check clean, NO em-dashes (use --), NO emoji.
 * No document = every method no-ops. Nothing renders until a key is pressed.
 * DOM is built with createElement + textContent only (no innerHTML, no XSS
 * surface -- every label is set as text, never parsed as markup).
 */
(function (global) {
  'use strict';
  if (global.AK_KEYS) return;
  var HEADLESS = (typeof document === 'undefined');

  var GOLD = '#e8c55a', INK = '#0b0b12';
  var hubApi = null;      // { dispatch(action, arg), districts() }
  var battleApi = null;   // { select(i), move(dx,dy), deploy(), cancel(), help() }
  var helpEl = null, paletteEl = null, bound = false;

  /* ---- keymap tables (single source for dispatch + help + palette) ------- */
  // Hub mode hotkeys: bare letters that never collide with movement
  // (movement owns w,a,s,d,h,j,k,l + arrows -- these are all clear of it).
  var HUB_MODES = [
    { key: 'r', action: 'raid',      label: 'Raid a block' },
    { key: 't', action: 'town',      label: 'Town Hall (battle)' },
    { key: 'f', action: 'fence',     label: 'The Fence (trade)' },
    { key: 'g', action: 'guard',     label: 'The Watch (defend)' },
    { key: 'c', action: 'crew',      label: 'Crew / social' },
    { key: 'b', action: 'build',     label: 'Build mode' },
    { key: 'm', action: 'map',       label: 'World map' },
    { key: 'i', action: 'infirmary', label: 'Infirmary' },
    { key: 'y', action: 'story',     label: 'Story / chapter' }
  ];
  var HUB_INTERACT = { keys: ['e', 'enter', ' '], action: 'interact', label: 'Interact (enter / accept / talk)' };

  function isTyping() {
    try {
      var a = document.activeElement; if (!a) return false;
      var t = (a.tagName || '').toUpperCase();
      return t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT' || a.isContentEditable === true;
    } catch (_e) { return false; }
  }

  /* ---- tiny DOM builder (text-only, no markup parsing) ------------------- */
  function mk(tag, css, text) {
    var el = document.createElement(tag);
    if (css) el.style.cssText = css;
    if (text != null) el.textContent = text;
    return el;
  }

  /* ---- HELP card (press ?) ---------------------------------------------- */
  function helpRows() {
    if (battleApi) {
      return [
        ['1 - 4', 'Pick the dog to deploy'],
        ['Arrows / WASD', 'Move the deploy cursor'],
        ['Space / Enter', 'Deploy the selected dog'],
        ['Esc', 'Cancel (again to surrender)'],
        ['?', 'Show / hide this card']
      ];
    }
    var rows = [
      ['WASD / Arrows', 'Walk the block'],
      ['E / Enter / Space', 'Interact -- enter, accept, talk'],
      ['1 - 9', 'Fast-travel to a district'],
      ['Tab', 'Quick-Travel menu']
    ];
    for (var i = 0; i < HUB_MODES.length; i++) rows.push([HUB_MODES[i].key.toUpperCase(), HUB_MODES[i].label]);
    rows.push(['Esc', 'Close / back to the map']);
    rows.push(['?', 'Show / hide this card']);
    return rows;
  }
  function buildHelp() {
    if (HEADLESS || helpEl) return;
    helpEl = mk('div', 'position:fixed;z-index:99998;right:14px;bottom:14px;max-width:280px;'
      + 'background:linear-gradient(180deg,rgba(14,14,22,.97),rgba(8,8,13,.97));'
      + 'border:1.5px solid ' + GOLD + ';border-radius:14px;padding:12px 14px;'
      + 'box-shadow:0 10px 34px rgba(0,0,0,.6);font-family:Inter,system-ui,sans-serif;'
      + 'color:#e8e8ea;display:none;');
    helpEl.id = 'ak-kbhelp';
    document.body.appendChild(helpEl);
  }
  function renderHelp() {
    buildHelp(); if (!helpEl) return;
    while (helpEl.firstChild) helpEl.removeChild(helpEl.firstChild);
    helpEl.appendChild(mk('div', 'font:800 12px Inter,sans-serif;letter-spacing:.14em;color:' + GOLD + ';margin-bottom:8px;', 'KEYBOARD'));
    var rows = helpRows();
    for (var i = 0; i < rows.length; i++) {
      var row = mk('div', 'display:flex;justify-content:space-between;gap:12px;padding:3px 0;font-size:12px;');
      row.appendChild(mk('b', 'color:#fff;white-space:nowrap;', rows[i][0]));
      row.appendChild(mk('span', 'color:#aab0b8;text-align:right;', rows[i][1]));
      helpEl.appendChild(row);
    }
  }
  function toggleHelp() {
    buildHelp(); if (!helpEl) return;
    if (helpEl.style.display !== 'none') { helpEl.style.display = 'none'; return; }
    renderHelp(); helpEl.style.display = 'block';
  }

  /* ---- Quick-Travel palette (hub, Tab) ---------------------------------- */
  function closePalette() { if (paletteEl) { try { paletteEl.remove(); } catch (_e) {} paletteEl = null; } }
  function paletteRow(badgeText, badgeCss, label, action, arg) {
    var row = mk('div', 'display:flex;align-items:center;gap:10px;padding:7px 8px;border-radius:9px;cursor:pointer;');
    row.className = 'ak-kbrow';
    row.setAttribute('data-act', action);
    if (arg != null) row.setAttribute('data-arg', String(arg));
    row.appendChild(mk('b', 'min-width:20px;height:20px;line-height:20px;text-align:center;border-radius:5px;font-size:12px;' + badgeCss, badgeText));
    row.appendChild(mk('span', 'color:#e8e8ea;font-size:13px;', label));
    return row;
  }
  function openPalette() {
    if (HEADLESS || !hubApi) return;
    closePalette();
    var districts = [];
    try { districts = (hubApi.districts && hubApi.districts()) || []; } catch (_e) { districts = []; }
    paletteEl = mk('div', 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;'
      + 'justify-content:center;background:rgba(4,4,8,.72);backdrop-filter:blur(3px);font-family:Inter,system-ui,sans-serif;');
    paletteEl.id = 'ak-kbpalette';
    var card = mk('div', 'width:min(92vw,440px);max-height:82vh;overflow:auto;background:' + INK + ';'
      + 'border:1.5px solid ' + GOLD + ';border-radius:16px;padding:16px 18px;box-shadow:0 20px 60px rgba(0,0,0,.7);');
    card.appendChild(mk('div', 'font:900 15px Cinzel,serif;color:' + GOLD + ';letter-spacing:.08em;margin-bottom:2px;', 'QUICK TRAVEL'));
    card.appendChild(mk('div', 'font-size:11px;color:#8a909a;margin-bottom:12px;', 'Press a number for a district, a letter for a mode. Esc closes.'));
    if (districts.length) {
      card.appendChild(mk('div', 'font:700 10px Inter;letter-spacing:.16em;color:#7fc8ff;margin:6px 0 4px;', 'DISTRICTS'));
      for (var d = 0; d < districts.length && d < 9; d++) {
        card.appendChild(paletteRow(String(d + 1), 'background:' + GOLD + ';color:#000;', String(districts[d]), 'travel', d + 1));
      }
    }
    card.appendChild(mk('div', 'font:700 10px Inter;letter-spacing:.16em;color:#ff9d5c;margin:12px 0 4px;', 'MODES'));
    for (var m = 0; m < HUB_MODES.length; m++) {
      card.appendChild(paletteRow(HUB_MODES[m].key.toUpperCase(), 'background:#2a2a34;color:' + GOLD + ';', HUB_MODES[m].label, HUB_MODES[m].action, null));
    }
    paletteEl.appendChild(card);
    paletteEl.addEventListener('click', function (ev) {
      var row = ev.target && ev.target.closest ? ev.target.closest('.ak-kbrow') : null;
      if (row) { fire(row.getAttribute('data-act'), row.getAttribute('data-arg')); closePalette(); return; }
      if (ev.target === paletteEl) closePalette();
    });
    document.body.appendChild(paletteEl);
  }

  function fire(action, arg) {
    if (!hubApi || !hubApi.dispatch) return;
    try { hubApi.dispatch(action, arg); } catch (_e) {}
  }

  /* ---- the one key listener --------------------------------------------- */
  function onKey(e) {
    if (isTyping()) return;
    var k = (e.key || '').toLowerCase();

    // HELP toggle works on either surface.
    if (k === '?' || (k === '/' && e.shiftKey)) { e.preventDefault(); toggleHelp(); return; }

    // ---- palette is modal: only Esc / its own clicks matter while open ----
    if (paletteEl) { if (k === 'escape') { e.preventDefault(); closePalette(); } return; }

    if (battleApi) {
      if (k >= '1' && k <= '4') { e.preventDefault(); try { battleApi.select(parseInt(k, 10) - 1); } catch (_e) {} return; }
      if (k === 'arrowleft' || k === 'a') { e.preventDefault(); try { battleApi.move(-1, 0); } catch (_e) {} return; }
      if (k === 'arrowright' || k === 'd') { e.preventDefault(); try { battleApi.move(1, 0); } catch (_e) {} return; }
      if (k === 'arrowup' || k === 'w') { e.preventDefault(); try { battleApi.move(0, -1); } catch (_e) {} return; }
      if (k === 'arrowdown' || k === 's') { e.preventDefault(); try { battleApi.move(0, 1); } catch (_e) {} return; }
      if (k === ' ' || k === 'enter') { e.preventDefault(); try { battleApi.deploy(); } catch (_e) {} return; }
      if (k === 'escape') { e.preventDefault(); try { battleApi.cancel(); } catch (_e) {} return; }
      return;
    }

    if (hubApi) {
      if (k === 'tab') { e.preventDefault(); openPalette(); return; }
      if (k === 'escape') { e.preventDefault(); fire('back'); return; }
      if (HUB_INTERACT.keys.indexOf(k) >= 0) { e.preventDefault(); fire('interact'); return; }
      if (k >= '1' && k <= '9') { e.preventDefault(); fire('travel', parseInt(k, 10)); return; }
      for (var i = 0; i < HUB_MODES.length; i++) {
        if (k === HUB_MODES[i].key) { e.preventDefault(); fire(HUB_MODES[i].action); return; }
      }
    }
  }

  function ensureBound() {
    if (bound || HEADLESS) return;
    try { document.addEventListener('keydown', onKey, false); bound = true; } catch (_e) {}
  }

  /* ---- public API -------------------------------------------------------- */
  global.AK_KEYS = {
    // index.html: dispatch(action[, arg]) routes every hub hotkey; districts()
    // returns an ordered name list for the palette + fast-travel numbers.
    mountHub: function (api) { hubApi = api || null; battleApi = null; ensureBound(); },
    // game.html: the four battle closures (cursor + deploy live in the page).
    mountBattle: function (api) { battleApi = api || null; hubApi = null; ensureBound(); },
    unmount: function () { hubApi = null; battleApi = null; closePalette(); if (helpEl) helpEl.style.display = 'none'; },
    toggleHelp: toggleHelp,
    isTyping: isTyping
  };
})(typeof window !== 'undefined' ? window : this);
