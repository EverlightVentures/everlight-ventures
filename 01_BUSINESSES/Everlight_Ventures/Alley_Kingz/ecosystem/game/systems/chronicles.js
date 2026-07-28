/*
 * chronicles.js -- AK_CHRONICLES (BLOCK CHRONICLES comic reader)
 * Full-screen gold-noir COMIC PAGE overlay for the per-dog story pages in
 * data/cards_stories.js (window.AK_STORIES, keyed by cardNumber "0001"..).
 * Plain JS, headless-safe (node --check clean), window-guarded, NO em-dashes
 * (hook law, use --). Zero invented proper nouns: every name on screen comes
 * from CANON_CARDS / AK_STORIES / AKStory / economy.js data.
 *
 * Public API (window.AK_CHRONICLES):
 *   open(ref, beatIdx?)          -> open the reader for a dog (cardNumber "0001",
 *                                   bare number, canon name, or id all accepted).
 *                                   Optional beatIdx = land ON that beat's page
 *                                   (the RESUME STORY chip's entry point).
 *                                   No AK_STORIES entry = the single classy
 *                                   "HIS STORY IS STILL BEING WRITTEN ON THE
 *                                   BLOCK" page (106 entries can land gradually).
 *   close(natural?)              -> dismiss + release any held cardfx clip.
 *                                   natural === true (the last-page GOT IT tap)
 *                                   ALSO clears the ak_chron_resume bookmark;
 *                                   any other close leaves it, so the page is
 *                                   never lost to an interrupt.
 *   isOpen()                     -> true while the reader overlay owns the
 *                                   screen (index.html's akStoryFocus gate).
 *   interrupt()                  -> the world MUST take the screen (a wild
 *                                   encounter fired): close gracefully with the
 *                                   one-line bridge banner "The block
 *                                   interrupts. The page waits." -- the resume
 *                                   bookmark stays for the RESUME STORY chip.
 *
 * RESUME CONTRACT (ak_chron_resume): every rendered page stamps
 *   { cardNumber, beatIdx, t } to localStorage. ONLY the natural completion
 *   (last page GOT IT) clears it. index.html shows a gold RESUME STORY chip
 *   whenever the bookmark exists and reopens via open(cardNumber, beatIdx).
 *   isUnlocked(ref, beatIdx)     -> true only if the beat EXISTS and its gate
 *                                   evaluates true against live signals.
 *   unlockLabel(ref, beatIdx)    -> the human "UNLOCKS: ..." label for a beat.
 *   setMoodPreview(m)            -> force a mood for testing ('hungry' etc,
 *                                   null/''/'live' returns to AK_NEEDS truth).
 *
 * MOOD RING (bible 10.2): every open page reads AK_NEEDS.mood() (typeof
 * guarded, 'neutral' fallback = today's exact chrome) and tints the page
 * CHROME, never the panel art assets:
 *   thriving   -> brighter gold border + inner glow, clean lines
 *   hungry     -> sepia + slight desaturation on the page
 *   lonely     -> blue tint + a subtle animated rain-streak veil
 *   weary      -> slow rotate jitter on the panel grid (border wobble)
 *   dishonored -> cracked chrome: dulled border + offset dashed inner line
 *                 + two ink crack strokes across the veil
 *
 * CHOICE PANELS (bible 10.3): a beat may carry
 *   choice: { prompt, options: [{ label, req?, fx?, tag? }] }
 * After the beat text completes, gold skewed comic buttons render in the
 * letterbox. req uses the SAME unlock grammar (evalUnlock) PLUS needs
 * comparators against AK_NEEDS.state(): 'hunger<=25', 'morale>=50',
 * 'energy<40', 'honor>=3' (honor compares the rep index). Unmet req = the
 * option shows dimmed/locked (players SEE what state earns them). Picking:
 *   - logs { cardNumber, beatKey, choice: tag||label, t } to localStorage
 *     ak_chron_choices (array, capped 100; an answered beat never re-asks)
 *   - fx {buff:'rage'|'tactical'|'easter'} is STORED to localStorage
 *     ak_next_battle_fx (the battler lane consumes it, never this file)
 *   - then the page turns.
 *
 * COMIC PAGE ANATOMY (each beat = one printed page):
 *   - paper-dark page frame with ink gutters; panels sit in a comic grid.
 *   - PANEL ART: assets/story/<cardNumber>_<beatKey>.jpg is the hero panel.
 *     If <cardNumber>_<beatKey>_p2.jpg / _p3.jpg exist (probed once with
 *     Image onerror, result cached), the page lays out a 2-3 panel action
 *     sequence: hero panel large + tilted sub-panels like a printed page.
 *     Missing images keep the faction-gradient + card-art fallback INSIDE
 *     the panel frame. Panels dropping in later = zero code change here.
 *   - COMIC GRAMMAR: the FIRST sentence of a beat renders as a gold CAPTION
 *     BOX (top-left, narrator box, slight skew); the REST types out inside a
 *     white SPEECH BUBBLE whose tail points at the narrator dog's portrait
 *     chip (bottom-left, in frame). Long bubble text auto-splits across 2
 *     bubbles revealed by tap.
 *   - PAGE-TURN: advancing plays a ~300ms CSS flip; footer counts pages
 *     like an issue ("PAGE 2 OF 5"). Tap completes the type, tap again turns.
 *   - COVER: page 0 of any story with beats is <cardNumber>_cover.jpg full
 *     bleed, with the codename as a drawn masthead + publicHook as the
 *     tagline (OUR typography over the art -- flux text is banned).
 *
 * UNLOCK CONTRACT (beat.unlock) -- evaluated against EXISTING signals ONLY:
 *   falsy | "free" | "always"          -> unlocked
 *   "owned"                            -> the dog is in p.owned (AK_ECON profile)
 *   "cardLevel:3" | {cardLevel:3}      -> AK_ECON.cardLevel(p, name) >= 3
 *   "repRank:2"   | {repRank:2}        -> AK_ECON.repRank(p).index  >= 2
 *   "chapter:2"   | {chapter:2}        -> AKStory.stage().idx       >= 2
 *   object = AND of its keys; array = AND of its entries.
 *   Aliases: own->owned, level->cardLevel, rep/rank->repRank,
 *            story/stage->chapter. ANY unknown key = LOCKED (fail closed),
 *   shown as a teaser page so players SEE what play earns them.
 */
(function (global) {
  'use strict';

  var HEADLESS = (typeof document === 'undefined');

  var GOLD = '#e8c55a';
  // Faction accent tints -- mirrors akfx.js FAC_COL / engine.js FACTION_COL
  // (the ONE canon palette; never a new faction color here).
  var FAC_COL = {
    boneguard_crew:    '#C9772E',
    zoomie_syndicate:  '#FF2E88',
    leashbreak_tactix: '#7B5CFF',
    k9_circuitry:      '#00E0C0',
    neutral:           '#c9a84c'
  };
  // Rep rank NAMES -- label mirror of economy.js REP_LADDER (the CHECK itself
  // always goes through AK_ECON.repRank, never this list).
  var REP_NAMES = ['Stray', 'Pup', 'Runner', 'Warrior', 'Enforcer', 'Right Paw', 'King of the Block'];

  var TYPE_MS = 28;          // typewriter cadence per char
  var Z = 70;                // above every existing hub overlay (max seen: 60)
  var TURN_MS = 150;         // half a page turn (out 150 + in 150 = ~300ms flip)
  var BUBBLE_MAX = 235;      // chars before the speech bubble splits in two

  // Comic lettering stacks -- graceful fallback to bold system faces.
  var COMIC_FONT = "'Comic Neue','Comic Sans MS','Chalkboard SE','Segoe Print',system-ui,sans-serif";
  var DISPLAY_FONT = "'Bangers','Luckiest Guy','Comic Neue','Arial Black',Inter,system-ui,sans-serif";
  var INK = '#05050a';       // panel borders + gutters ink

  /* ======================== canon + profile lookups ======================== */

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pad4(v) {
    var d = String(v == null ? '' : v).replace(/[^0-9]/g, '');
    return d ? ('0000' + d).slice(-4) : '';
  }
  // accepts cardNumber ("0001" | 1), canon name, or id
  function canonAny(ref) {
    try {
      var L = global.CANON_CARDS || [], num = pad4(ref), i, c;
      for (i = 0; i < L.length; i++) {
        c = L[i]; if (!c) continue;
        if (c.name === ref || c.id === ref) return c;
        if (c.cardNumber && (String(c.cardNumber) === String(ref) || (num && pad4(c.cardNumber) === num))) return c;
      }
    } catch (_e) {}
    return null;
  }
  function numOf(ref) {
    var c = canonAny(ref);
    if (c && c.cardNumber) return pad4(c.cardNumber);
    return pad4(ref);
  }
  function storyOf(num) {
    try {
      if (typeof global.AK_STORIES === 'object' && global.AK_STORIES && num) return global.AK_STORIES[num] || null;
    } catch (_e) {}
    return null;
  }
  function prof() {
    try { return (global.AK_ECON && global.AK_ECON.loadProfile) ? global.AK_ECON.loadProfile() : null; } catch (_e) { return null; }
  }
  function accentOf(card) {
    var id = card && (card.factionId || '').toLowerCase();
    return FAC_COL[id] || GOLD;
  }
  function artOf(card) {
    try { if (card && typeof global.akCardArtRel === 'function') { var rel = global.akCardArtRel(card); if (rel) return 'assets/' + rel; } } catch (_e) {}
    return '';
  }
  function ownedHas(card) {
    if (!card) return false;
    var p = prof(), o = (p && Array.isArray(p.owned)) ? p.owned : [];
    for (var i = 0; i < o.length; i++) {
      var nm = o[i]; if (!nm) continue;
      if (nm === card.name || nm === card.id || (card.cardNumber && pad4(nm) && pad4(nm) === pad4(card.cardNumber))) return true;
    }
    return false;
  }

  /* ========================= UNLOCK EVALUATOR ============================= */

  var ALIAS = {
    owned: 'owned', own: 'owned', pulled: 'owned',
    cardlevel: 'cardLevel', level: 'cardLevel', lv: 'cardLevel',
    reprank: 'repRank', rep: 'repRank', rank: 'repRank',
    chapter: 'chapter', story: 'chapter', stage: 'chapter', storystage: 'chapter', storychapter: 'chapter'
  };
  function chapterTitle(idx) {
    try {
      var S = (global.AKStory && global.AKStory.STAGES) || null;
      if (S && S[idx] && S[idx].title) return String(S[idx].title);
    } catch (_e) {}
    return '';
  }
  // one recognized signal -> { ok, label }; unknown -> fail closed
  function evalOne(key, val, card) {
    var k = ALIAS[String(key || '').toLowerCase()] || null;
    var name = (card && card.name) ? String(card.name).toUpperCase() : 'THIS DOG';
    if (k === 'owned') {
      return { ok: ownedHas(card), label: 'PULL ' + name + ' FROM A CHEST' };
    }
    if (k === 'cardLevel') {
      var lv = Math.max(1, val | 0), got = 0;
      try { if (global.AK_ECON && global.AK_ECON.cardLevel && card) got = global.AK_ECON.cardLevel(prof(), card.name) | 0; } catch (_e1) {}
      return { ok: got >= lv, label: 'RAISE ' + name + ' TO LEVEL ' + lv };
    }
    if (k === 'repRank') {
      var ri = Math.max(0, val | 0), cur = -1;
      try { if (global.AK_ECON && global.AK_ECON.repRank) { var r = global.AK_ECON.repRank(prof()); cur = (r && (r.index | 0)) || 0; } } catch (_e2) {}
      var rn = String(REP_NAMES[ri] || ('REP RANK ' + ri)).toUpperCase();
      return { ok: cur >= ri, label: 'REACH ' + rn + (rn.indexOf('BLOCK') >= 0 ? ' REP' : ' REP ON THE BLOCK') };
    }
    if (k === 'chapter') {
      var ch = Math.max(0, val | 0), at = -1;
      try { if (global.AKStory && global.AKStory.stage) { var st = global.AKStory.stage(); at = (st && (st.idx | 0)) || 0; } } catch (_e3) {}
      var t = chapterTitle(ch);
      return { ok: at >= ch, label: 'REACH CHAPTER ' + (ch + 1) + (t ? (' -- ' + t.toUpperCase()) : ' OF THE CROWN CLIMB') };
    }
    // unknown signal: LOCKED, with the raw key surfaced so the tease still reads
    return { ok: false, label: String(key || 'PLAY').replace(/[_:.-]+/g, ' ').toUpperCase() };
  }
  // whole beat.unlock -> { ok, label } (label = joined outstanding requirements)
  function evalUnlock(unlock, card) {
    if (unlock == null || unlock === '' || unlock === false) return { ok: true, label: '' };
    var s = (typeof unlock === 'string') ? unlock.toLowerCase().replace(/\s+/g, '') : null;
    if (s === 'free' || s === 'always' || s === 'open') return { ok: true, label: '' };
    var parts = [], i;
    if (typeof unlock === 'string') {
      // accept BOTH contract spellings: the bible 4.2 comparator form ("cardLevel>=3",
      // "repRank>=2", "storyChapter>=5") AND the colon form ("cardlevel:3"). A bare
      // key ("owned") evaluates truthy.
      var cmp = unlock.match(/^\s*([A-Za-z_]+)\s*>=?\s*(\d+)\s*$/);
      if (cmp) { parts.push(evalOne(cmp[1], parseInt(cmp[2], 10) || 0, card)); }
      else {
        var kv = unlock.split(':');
        parts.push(evalOne(kv[0], kv.length > 1 ? parseInt(kv[1], 10) || 0 : true, card));
      }
    } else if (Object.prototype.toString.call(unlock) === '[object Array]') {
      for (i = 0; i < unlock.length; i++) { var sub = evalUnlock(unlock[i], card); if (!sub.ok || sub.label) parts.push(sub); }
      if (!parts.length) return { ok: true, label: '' };
    } else if (typeof unlock === 'object') {
      for (var key in unlock) {
        if (!Object.prototype.hasOwnProperty.call(unlock, key)) continue;
        parts.push(evalOne(key, unlock[key], card));
      }
      if (!parts.length) return { ok: true, label: '' };
    } else {
      return { ok: false, label: 'KEEP PLAYING' };
    }
    var ok = true, labels = [];
    for (i = 0; i < parts.length; i++) {
      if (!parts[i].ok) { ok = false; if (parts[i].label) labels.push(parts[i].label); }
    }
    return { ok: ok, label: labels.join(' + ') };
  }

  /* ---- choice req: unlock grammar PLUS needs comparators (bible 10.3) ---- */

  function needsState() {
    try {
      if (global.AK_NEEDS && typeof global.AK_NEEDS.state === 'function') {
        var st = global.AK_NEEDS.state();
        if (st && typeof st === 'object') return st;
      }
    } catch (_e) {}
    return null;
  }
  // req -> { ok, label }. 'hunger<=25' / 'morale>=50' / 'energy<40' /
  // 'honor>=3' read AK_NEEDS.state() (honor compares the rep index). Missing
  // AK_NEEDS reads FULL (100 / index 0) so state-locked desperate options stay
  // locked = today's exact behavior. Anything else = the unlock grammar.
  function evalReq(req, card) {
    if (req == null || req === '' || req === false) return { ok: true, label: '' };
    if (typeof req === 'string') {
      var m = req.replace(/\s+/g, '').match(/^(hunger|morale|energy|honor)(<=|>=|<|>)(\d+)$/i);
      if (m) {
        var k = m[1].toLowerCase(), op = m[2], n = parseInt(m[3], 10) || 0;
        var st = needsState(), v;
        if (k === 'honor') v = (st && st.honor && (st.honor.index | 0)) || 0;
        else v = (st && typeof st[k] === 'number' && isFinite(st[k])) ? st[k] : 100;
        var ok = (op === '<=') ? v <= n : (op === '>=') ? v >= n : (op === '<') ? v < n : v > n;
        var word = (op === '<=' || op === '<') ? 'BELOW' : 'ABOVE';
        return { ok: ok, label: k.toUpperCase() + ' ' + word + ' ' + n };
      }
    }
    return evalUnlock(req, card);
  }

  /* ---- choice log: localStorage ak_chron_choices + ak_next_battle_fx ---- */

  function ls() { try { return global.localStorage || null; } catch (_e) { return null; } }
  function readChoices() {
    try {
      var S = ls(); if (!S) return [];
      var a = JSON.parse(S.getItem('ak_chron_choices') || '[]');
      return Array.isArray(a) ? a : [];
    } catch (_e) { return []; }
  }
  function choiceMade(num, beatKey) {
    var a = readChoices();
    for (var i = 0; i < a.length; i++) {
      var e = a[i];
      if (e && e.cardNumber === num && e.beatKey === beatKey) return e;
    }
    return null;
  }
  // the pick: log the choice (capped 100), store fx for the battler lane
  // (STORE only, the battler consumes), return the entry.
  function recordChoice(num, beatKey, opt) {
    var entry = {
      cardNumber: String(num || ''),
      beatKey: String(beatKey || ''),
      choice: String((opt && (opt.tag || opt.label)) || ''),
      t: Date.now()
    };
    try {
      var S = ls();
      if (S) {
        var a = readChoices();
        a.push(entry);
        if (a.length > 100) a = a.slice(a.length - 100);
        S.setItem('ak_chron_choices', JSON.stringify(a));
      }
    } catch (_e) {}
    try {
      var fx = opt && opt.fx;
      if (fx && fx.buff) {
        var S2 = ls();
        if (S2) S2.setItem('ak_next_battle_fx', JSON.stringify({
          buff: String(fx.buff), source: 'chronicles',
          cardNumber: entry.cardNumber, beatKey: entry.beatKey, t: entry.t
        }));
      }
    } catch (_e2) {}
    return entry;
  }

  function isUnlocked(ref, beatIdx) {
    try {
      var num = numOf(ref), story = storyOf(num);
      if (!story || !Array.isArray(story.beats)) return false;
      var b = story.beats[beatIdx | 0];
      if (!b) return false;
      return evalUnlock(b.unlock, canonAny(ref)).ok;
    } catch (_e) { return false; }
  }
  function unlockLabel(ref, beatIdx) {
    try {
      var num = numOf(ref), story = storyOf(num);
      var b = story && Array.isArray(story.beats) ? story.beats[beatIdx | 0] : null;
      if (!b) return '';
      return evalUnlock(b.unlock, canonAny(ref)).label;
    } catch (_e) { return ''; }
  }

  /* ============================== READER UI =============================== */

  var UI = null;             // { root, page, panels, caption, btext, chip, ... }
  var pages = [];            // [{kind:'cover'|'beat'|'locked'|'unwritten', beat?, label?, text?}]
  var pageAt = 0;
  var curCard = null, curNum = '', curCodename = '';
  var typeTimer = null, typeFull = '', typeAt = 0, typing = false;
  var heldClipPath = null;
  var bubbleParts = [], bubbleAt = 0;   // split speech text, revealed by tap
  var turning = false;                  // mid page-flip: taps ignored
  var renderSeq = 0;                    // guards async panel-probe callbacks
  var PANEL_COUNT = {};                 // "<num>_<beatKey>" -> 1|2|3 (probe cache)
  var choicePending = false;            // a choice panel is up: taps never turn the page
  var moodPreview = null;               // setMoodPreview override (testing)
  var openFlag = false;                 // the reader owns the screen (isOpen truth)

  /* ====================== MOOD RING (bible 10.2) ========================== */

  // the page frame's stock chrome -- the reset EVERY mood starts from, so a
  // missing AK_NEEDS ('neutral') = today's exact look.
  var PAGE_BORDER = '1px solid #2b2433';
  var PAGE_SHADOW = '0 18px 44px rgba(0,0,0,.8),inset 0 0 0 1px rgba(232,197,90,.06)';

  function moodNow() {
    if (moodPreview) return moodPreview;
    try {
      if (global.AK_NEEDS && typeof global.AK_NEEDS.mood === 'function') {
        var m = global.AK_NEEDS.mood();
        if (m) return String(m);
      }
    } catch (_e) {}
    return 'neutral';
  }
  function ensureMoodCSS() {
    if (HEADLESS) return;
    try {
      if (document.getElementById('chron-mood-css')) return;
      var st = document.createElement('style');
      st.id = 'chron-mood-css';
      st.textContent =
        '@keyframes chronWobble{0%,100%{transform:rotate(-.35deg)}50%{transform:rotate(.35deg)}}' +
        '@keyframes chronRain{from{background-position:0 0,0 0}to{background-position:-46px 240px,0 0}}';
      document.head.appendChild(st);
    } catch (_e) {}
  }
  // the mood cocktail lands on the page CHROME only (frame, veil, panel grid
  // jitter, kicker) -- NEVER repaints panel art assets. Small and tasteful.
  function applyMood(m) {
    if (HEADLESS || !UI) return;
    try {
      var pg = UI.page, pn = UI.panels, veil = UI.moodveil;
      // reset to stock chrome first (neutral == today's exact behavior)
      pg.style.filter = '';
      pg.style.border = PAGE_BORDER;
      pg.style.boxShadow = PAGE_SHADOW;
      pg.style.outline = '';
      pg.style.outlineOffset = '';
      pn.style.animation = '';
      veil.style.display = 'none';
      veil.style.background = '';
      veil.style.animation = '';
      UI.kicker.style.color = GOLD;
      if (m === 'thriving') {          // brighter gold accents + clean borders
        pg.style.border = '1px solid rgba(232,197,90,.6)';
        pg.style.boxShadow = '0 18px 44px rgba(0,0,0,.8),inset 0 0 0 1px rgba(232,197,90,.22),0 0 26px rgba(232,197,90,.14)';
        UI.kicker.style.color = '#f6dc80';
      } else if (m === 'hungry') {     // sepia drain + slight desaturation
        pg.style.filter = 'sepia(.38) saturate(.78)';
      } else if (m === 'lonely') {     // blue tint + subtle rain streaks
        pg.style.filter = 'saturate(.86)';
        veil.style.background =
          'repeating-linear-gradient(168deg,rgba(160,190,255,.10) 0px,rgba(160,190,255,.10) 1px,transparent 1px,transparent 26px),' +
          'linear-gradient(180deg,rgba(70,110,200,.16),rgba(40,60,130,.10))';
        veil.style.animation = 'chronRain 1.6s linear infinite';
        veil.style.display = 'block';
      } else if (m === 'weary') {      // slight rotate jitter on the panels
        pn.style.animation = 'chronWobble 2.4s ease-in-out infinite';
      } else if (m === 'dishonored') { // cracked chrome: double border + ink cracks
        pg.style.border = '1px solid #4a3f52';
        pg.style.outline = '1px dashed rgba(201,168,76,.4)';
        pg.style.outlineOffset = '-7px';
        veil.style.background =
          'linear-gradient(104deg,transparent 31%,rgba(5,5,10,.5) 31.4%,transparent 31.9%),' +
          'linear-gradient(76deg,transparent 68%,rgba(5,5,10,.45) 68.4%,transparent 68.8%)';
        veil.style.display = 'block';
      }
      // 'neutral' (or anything unknown) keeps the stock chrome from the reset
    } catch (_e) {}
  }
  function setMoodPreview(m) {
    moodPreview = (m == null || m === '' || m === 'live') ? null : String(m);
    applyMood(moodNow());
    return moodNow();
  }

  function releaseClip() {
    try {
      var CF = global.AK_CARDFX;
      if (heldClipPath && CF && CF.release) CF.release(heldClipPath);
    } catch (_e) {}
    heldClipPath = null;
  }
  function stopType() { if (typeTimer) { clearInterval(typeTimer); typeTimer = null; } typing = false; }

  /* ---- multi-panel probe: does _p2 / _p3 exist for this beat? cached ---- */
  function probePanels(num, key, cb) {
    var ck = num + '_' + key;
    if (PANEL_COUNT[ck] != null) { cb(PANEL_COUNT[ck]); return; }
    if (HEADLESS || typeof Image === 'undefined') { cb(1); return; }
    var got = { p2: null, p3: null };
    function settle() {
      if (got.p2 == null || got.p3 == null) return;
      var n = 1 + (got.p2 ? 1 : 0) + ((got.p2 && got.p3) ? 1 : 0);
      PANEL_COUNT[ck] = n;
      cb(n);
    }
    function probe(which) {
      try {
        var im = new Image();
        im.onload = function () { got[which] = true; settle(); };
        im.onerror = function () { got[which] = false; settle(); };
        im.src = 'assets/story/' + num + '_' + key + '_' + which + '.jpg';
      } catch (_e) { got[which] = false; settle(); }
    }
    probe('p2'); probe('p3');
  }

  function ensureUI() {
    var root = document.getElementById('chronpanel');
    if (root && root._chronUI) { UI = root._chronUI; return UI; }
    if (!root) {
      root = document.createElement('div');
      root.id = 'chronpanel';
      root.style.cssText = 'position:fixed;inset:0;z-index:' + Z + ';display:none;flex-direction:column;background:#04040a;font-family:Inter,system-ui,sans-serif;';
      document.body.appendChild(root);
    }
    root.innerHTML =
      // ---- top rail: series kicker + close ----
      '<div style="flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px 6px;">'
      +   '<div id="chron-kicker" style="font:800 10px Inter,system-ui;letter-spacing:.22em;color:' + GOLD + ';text-transform:uppercase;text-shadow:0 1px 6px #000;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">BLOCK CHRONICLES</div>'
      +   '<button id="chron-close" style="flex:0 0 auto;width:32px;height:32px;border-radius:50%;border:1px solid rgba(232,197,90,.55);background:rgba(6,6,12,.72);color:' + GOLD + ';font:800 14px Inter,system-ui;cursor:pointer;">&#10005;</button>'
      + '</div>'
      // ---- the reading desk (perspective host for the page-turn flip) ----
      + '<div style="flex:1;display:flex;align-items:stretch;justify-content:center;padding:2px 10px 6px;perspective:1400px;overflow:hidden;min-height:0;">'
      +   '<div id="chron-page" style="position:relative;flex:1;max-width:560px;min-height:0;display:flex;flex-direction:column;padding:10px;cursor:pointer;backface-visibility:hidden;border-radius:5px;border:1px solid #2b2433;background:linear-gradient(165deg,#1a1620 0%,#141118 42%,#0e0c13 100%);box-shadow:0 18px 44px rgba(0,0,0,.8),inset 0 0 0 1px rgba(232,197,90,.06);">'
      // panel grid -- the 8px gaps ARE the ink gutters on the paper-dark stock
      +     '<div id="chron-panels" style="position:relative;flex:1;min-height:0;display:flex;flex-direction:column;gap:8px;"></div>'
      // halftone print texture across the whole page
      +     '<div style="position:absolute;inset:0;pointer-events:none;border-radius:5px;background-image:radial-gradient(rgba(255,255,255,.05) 1px,transparent 1.5px);background-size:6px 6px;mix-blend-mode:overlay;"></div>'
      // mood veil (bible 10.2): rain streaks / crack strokes land here
      +     '<div id="chron-moodveil" style="position:absolute;inset:0;z-index:3;display:none;pointer-events:none;border-radius:5px;"></div>'
      // lock overlay (over the panels, under the comic grammar)
      +     '<div id="chron-lock" style="position:absolute;inset:10px;z-index:4;display:none;align-items:center;justify-content:center;flex-direction:column;text-align:center;padding:0 7vw;border-radius:3px;background:radial-gradient(ellipse at 50% 42%,#141020cc 0%,#04040acc 74%);"></div>'
      // narrator CAPTION BOX -- classic gold box, top-left, slight skew
      +     '<div id="chron-caption" style="position:absolute;top:18px;left:16px;max-width:74%;z-index:5;display:none;background:linear-gradient(180deg,#f6dc80,#e8c55a);color:#181203;border:2px solid ' + INK + ';padding:6px 10px;transform:rotate(-1.5deg) skewX(-2deg);box-shadow:3px 3px 0 rgba(0,0,0,.55);font:700 12.5px/1.35 ' + COMIC_FONT + ';"></div>'
      // SPEECH BUBBLE -- white, ink border, tail pointing at the narrator chip
      +     '<div id="chron-bubblewrap" style="position:absolute;left:86px;right:14px;bottom:16px;z-index:6;display:none;">'
      +       '<div style="position:relative;background:#fdfbf2;color:#16131c;border:2.5px solid ' + INK + ';border-radius:15px;padding:9px 12px 11px;box-shadow:0 8px 20px rgba(0,0,0,.55);">'
      +         '<div id="chron-btext" style="font:700 14px/1.42 ' + COMIC_FONT + ';min-height:20px;"></div>'
      +         '<div id="chron-more" style="position:absolute;right:9px;bottom:3px;display:none;font:900 9px ' + COMIC_FONT + ';color:#8a7430;letter-spacing:.08em;">TAP &#9658;</div>'
      +         '<div style="position:absolute;left:-14px;bottom:9px;width:0;height:0;border-top:4px solid transparent;border-bottom:13px solid transparent;border-right:15px solid ' + INK + ';"></div>'
      +         '<div style="position:absolute;left:-9px;bottom:12px;width:0;height:0;border-top:3px solid transparent;border-bottom:9px solid transparent;border-right:11px solid #fdfbf2;"></div>'
      +       '</div>'
      +     '</div>'
      // narrator dog IN frame, bottom-left, like a character on the page
      +     '<div id="chron-chipbox" style="position:absolute;left:12px;bottom:14px;z-index:7;width:64px;text-align:center;">'
      +       '<div id="chron-chip" style="width:56px;height:56px;margin:0 auto;border-radius:50%;overflow:hidden;border:2px solid ' + GOLD + ';box-shadow:0 0 14px rgba(232,197,90,.4),0 4px 10px rgba(0,0,0,.6);background:#15111c;"></div>'
      +       '<div id="chron-codename" style="font:900 8.5px ' + COMIC_FONT + ';letter-spacing:.04em;color:' + GOLD + ';margin-top:4px;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-shadow:0 1px 4px #000;"></div>'
      +     '</div>'
      // issue-cover masthead (page 0 only): OUR typography over the art
      +     '<div id="chron-mast" style="position:absolute;inset:10px;z-index:8;display:none;pointer-events:none;border-radius:3px;overflow:hidden;"></div>'
      // CHOICE letterbox (bible 10.3): gold skewed comic buttons over the page
      +     '<div id="chron-choice" style="position:absolute;left:14px;right:14px;bottom:16px;z-index:9;display:none;flex-direction:column;gap:8px;"></div>'
      +   '</div>'
      + '</div>'
      // ---- issue footer: BACK | PAGE n OF m | NEXT ----
      + '<div style="flex:0 0 auto;display:flex;gap:8px;align-items:center;padding:8px 14px calc(12px + env(safe-area-inset-bottom,0px));">'
      +   '<button id="chron-back" style="flex:0 0 92px;background:none;border:1px solid rgba(232,197,90,.4);color:#cbb87a;border-radius:9px;padding:9px 0;font:800 11px Inter,system-ui;letter-spacing:.1em;cursor:pointer;">BACK</button>'
      +   '<div id="chron-count" style="flex:1;text-align:center;font:800 10px Inter,system-ui;letter-spacing:.24em;color:#cbb87a;text-transform:uppercase;"></div>'
      +   '<button id="chron-next" style="flex:0 0 124px;background:linear-gradient(180deg,#e8c55a,#b8922e);border:none;color:#141005;border-radius:9px;padding:9px 0;font:900 11px Inter,system-ui;letter-spacing:.12em;cursor:pointer;box-shadow:0 4px 14px rgba(232,197,90,.3);">NEXT</button>'
      + '</div>';
    UI = {
      root: root,
      page: root.querySelector('#chron-page'),
      panels: root.querySelector('#chron-panels'),
      lock: root.querySelector('#chron-lock'),
      caption: root.querySelector('#chron-caption'),
      bubblewrap: root.querySelector('#chron-bubblewrap'),
      btext: root.querySelector('#chron-btext'),
      more: root.querySelector('#chron-more'),
      moodveil: root.querySelector('#chron-moodveil'),
      choice: root.querySelector('#chron-choice'),
      chipbox: root.querySelector('#chron-chipbox'),
      chip: root.querySelector('#chron-chip'),
      codename: root.querySelector('#chron-codename'),
      mast: root.querySelector('#chron-mast'),
      kicker: root.querySelector('#chron-kicker'),
      count: root.querySelector('#chron-count'),
      back: root.querySelector('#chron-back'),
      next: root.querySelector('#chron-next'),
      closeBtn: root.querySelector('#chron-close')
    };
    root._chronUI = UI;
    UI.closeBtn.onclick = function (e) { try { e.stopPropagation(); } catch (_e) {} close(); };
    UI.back.onclick = function () { if (!turning && pageAt > 0) turnTo(pageAt - 1, true); };
    UI.next.onclick = function () { tap(); };
    // tap the page: finish the typewriter, then next bubble, then page-turn
    UI.page.onclick = function () { tap(); };
    ensureMoodCSS();
    return UI;
  }

  function tap() {
    if (turning) return;
    if (typing) { finishType(); return; }
    if (bubbleAt < bubbleParts.length - 1) { bubbleAt += 1; showBubblePart(); return; }
    // the beat text is done: an unanswered choice takes the page over --
    // only picking an option turns it (bible 10.3)
    if (maybeShowChoice()) return;
    // the LAST page's tap is the natural GOT IT -- the one close that clears the bookmark
    if (pageAt < pages.length - 1) turnTo(pageAt + 1, false); else close(true);
  }

  /* ================== CHOICE PANELS (bible 10.3) ========================== */

  function hideChoice() {
    choicePending = false;
    if (UI && UI.choice) { UI.choice.style.display = 'none'; UI.choice.innerHTML = ''; }
  }
  // current page carries an unanswered choice -> render it, hold the page.
  // choicePending true = already up (taps keep waiting on the buttons).
  function maybeShowChoice() {
    if (choicePending) return true;
    var pg = pages[pageAt];
    if (!pg || pg.kind !== 'beat' || !pg.beat || !pg.beat.choice) return false;
    var ch = pg.beat.choice;
    if (!ch || !Array.isArray(ch.options) || !ch.options.length) return false;
    var key = String(pg.beat.key || '');
    if (choiceMade(curNum, key)) return false;   // answered on a past read: canon holds
    renderChoice(pg.beat, key);
    return true;
  }
  function renderChoice(beat, key) {
    var box = UI.choice;
    box.innerHTML = '';
    // prompt strip -- same gold caption-box grammar as the narrator box
    var pr = document.createElement('div');
    pr.style.cssText = 'align-self:flex-start;max-width:88%;background:linear-gradient(180deg,#f6dc80,#e8c55a);color:#181203;border:2px solid ' + INK + ';padding:5px 10px;transform:rotate(-1deg) skewX(-3deg);box-shadow:3px 3px 0 rgba(0,0,0,.55);font:800 12px/1.3 ' + COMIC_FONT + ';';
    pr.textContent = String(beat.choice.prompt || 'CHOOSE.');
    box.appendChild(pr);
    var opts = beat.choice.options;
    for (var i = 0; i < opts.length; i++) {
      var opt = opts[i]; if (!opt || !opt.label) continue;
      var ev = evalReq(opt.req, curCard);
      var b = document.createElement('button');
      if (ev.ok) {
        b.style.cssText = 'display:block;width:100%;text-align:left;background:linear-gradient(180deg,#e8c55a,#b8922e);color:#141005;border:2px solid ' + INK + ';border-radius:3px;padding:9px 12px;transform:skewX(-6deg);font:900 13px/1.3 ' + COMIC_FONT + ';letter-spacing:.03em;cursor:pointer;box-shadow:3px 3px 0 rgba(0,0,0,.6),0 4px 14px rgba(232,197,90,.25);';
        b.textContent = String(opt.label);
      } else {
        // state-locked tease: players SEE what the state earns them
        b.style.cssText = 'display:block;width:100%;text-align:left;background:rgba(10,9,15,.88);color:#9a8f6a;border:2px dashed rgba(154,143,106,.5);border-radius:3px;padding:9px 12px;transform:skewX(-6deg);font:900 13px/1.3 ' + COMIC_FONT + ';letter-spacing:.03em;cursor:default;';
        b.textContent = String(opt.label);
        var lk = document.createElement('span');
        lk.style.cssText = 'display:block;font:800 9px Inter,system-ui;letter-spacing:.14em;color:#6f6650;margin-top:3px;text-transform:uppercase;';
        lk.textContent = 'LOCKED: ' + (ev.label || 'KEEP PLAYING');
        b.appendChild(lk);
      }
      b.onclick = (function (o, ok) {
        return function (e) {
          try { e.stopPropagation(); } catch (_e) {}
          if (!ok || turning || !choicePending) return;
          recordChoice(curNum, key, o);
          hideChoice();
          if (pageAt < pages.length - 1) turnTo(pageAt + 1, false); else close(true);
        };
      })(opt, ev.ok);
      box.appendChild(b);
    }
    box.style.display = 'flex';
    choicePending = true;
  }

  /* ---- page-turn flip: ~300ms total (150 out around the spine, 150 in) ---- */
  function turnTo(i, back) {
    if (turning || !UI) return;
    turning = true;
    stopType();
    var pg = UI.page;
    try {
      pg.style.transition = 'transform ' + TURN_MS + 'ms ease-in, opacity ' + TURN_MS + 'ms ease-in';
      pg.style.transformOrigin = back ? '100% 50%' : '0% 50%';
      pg.style.transform = 'rotateY(' + (back ? '' : '-') + '62deg)';
      pg.style.opacity = '0.25';
    } catch (_e) {}
    setTimeout(function () {
      renderPage(i);
      try {
        pg.style.transition = 'none';
        pg.style.transformOrigin = back ? '0% 50%' : '100% 50%';
        pg.style.transform = 'rotateY(' + (back ? '-' : '') + '46deg)';
        void pg.offsetWidth;   // reflow so the incoming half animates
        pg.style.transition = 'transform ' + TURN_MS + 'ms ease-out, opacity ' + TURN_MS + 'ms ease-out';
        pg.style.transform = 'rotateY(0deg)';
        pg.style.opacity = '1';
      } catch (_e2) {}
      setTimeout(function () {
        turning = false;
        try { pg.style.transition = 'none'; } catch (_e3) {}
      }, TURN_MS + 30);
    }, TURN_MS + 10);
  }

  /* ---- typewriter (into the speech bubble) ---- */
  function typeText(s) {
    stopType();
    typeFull = String(s || '');
    typeAt = 0;
    UI.btext.textContent = '';
    if (!typeFull) { updateMore(); return; }
    typing = true;
    typeTimer = setInterval(function () {
      typeAt += 1;
      UI.btext.textContent = typeFull.slice(0, typeAt);
      if (typeAt >= typeFull.length) { stopType(); updateMore(); }
    }, TYPE_MS);
  }
  function finishType() { stopType(); UI.btext.textContent = typeFull; updateMore(); }
  function updateMore() {
    try { UI.more.style.display = (!typing && bubbleAt < bubbleParts.length - 1) ? 'block' : 'none'; } catch (_e) {}
  }

  /* ---- comic grammar split: first sentence = caption, rest = bubble(s) ---- */
  function splitBeatText(t) {
    t = String(t || '').replace(/^\s+|\s+$/g, '');
    if (!t) return { cap: '', parts: [] };
    var m = t.match(/^([\s\S]*?[.!?]+["')\]]*)\s+([\s\S]+)$/);
    var cap = m ? m[1] : t;
    var rest = m ? m[2] : '';
    var parts = [];
    if (rest) {
      if (rest.length > BUBBLE_MAX) {
        // auto-split into 2 bubbles at the sentence end nearest the midpoint
        var cut = -1, mid = rest.length / 2, re = /[.!?]+["')\]]*\s+/g, mm;
        while ((mm = re.exec(rest))) {
          var pos = mm.index + mm[0].length;
          if (pos > 0 && pos < rest.length && (cut < 0 || Math.abs(pos - mid) < Math.abs(cut - mid))) cut = pos;
        }
        if (cut <= 0 || cut >= rest.length) {
          cut = rest.lastIndexOf(' ', mid | 0);
          if (cut <= 0) cut = mid | 0;
        }
        parts.push(rest.slice(0, cut).replace(/\s+$/, ''));
        parts.push(rest.slice(cut).replace(/^\s+/, ''));
      } else {
        parts.push(rest);
      }
    }
    return { cap: cap, parts: parts };
  }
  function setSpeech(t) {
    var sp = splitBeatText(t);
    if (sp.cap) {
      UI.caption.textContent = sp.cap;
      UI.caption.style.display = 'block';
    }
    bubbleParts = sp.parts;
    bubbleAt = 0;
    if (bubbleParts.length) showBubblePart();
  }
  function showBubblePart() {
    var part = String(bubbleParts[bubbleAt] || '');
    UI.bubblewrap.style.display = 'block';
    // lettering sized to fit the bubble
    UI.btext.style.fontSize = (part.length > 175 ? 12.5 : (part.length > 115 ? 13.5 : 14.5)) + 'px';
    UI.more.style.display = 'none';
    typeText(part);
  }

  /* ---- fallback scene INSIDE a panel frame: faction gradient + card art ---- */
  function paintFallbackInto(el, dimmed) {
    var ac = accentOf(curCard);
    el.style.background =
      'radial-gradient(ellipse at 50% 30%,' + ac + '44 0%,transparent 58%),' +
      'linear-gradient(168deg,' + ac + '2e 0%,#0a0812 46%,#04040a 100%)';
    var art = artOf(curCard);
    var inner = '';
    if (art) {
      inner = '<img src="' + esc(art) + '" alt="" '
        + 'onerror="if(!(window.akImgErr&&akImgErr(this)))this.style.display=\'none\';" '
        + 'style="max-width:82%;max-height:78%;object-fit:contain;border-radius:14px;'
        + 'filter:drop-shadow(0 0 34px ' + ac + '88) drop-shadow(0 14px 30px rgba(0,0,0,.8))'
        + (dimmed ? ' grayscale(.85) brightness(.4)' : '') + ';'
        + (dimmed ? 'opacity:.28;' : '') + '">';
    } else {
      inner = '<div style="width:46vmin;height:46vmin;border-radius:50%;background:radial-gradient(circle,' + ac + '55,transparent 70%);"></div>';
    }
    el.innerHTML = inner;
    el.style.display = 'flex';
  }

  /* ---- panel factory: ink frame, real art swaps in over the fallback ---- */
  function panelShell(extra) {
    return 'position:relative;overflow:hidden;background:#0a0912;border:2px solid ' + INK + ';border-radius:3px;box-shadow:0 2px 10px rgba(0,0,0,.6),inset 0 0 0 1px rgba(232,197,90,.08);' + (extra || '');
  }
  function mkPanel(src, sizing, rot) {
    var d = document.createElement('div');
    d.style.cssText = panelShell(sizing + (rot ? 'transform:rotate(' + rot + 'deg) translateY(' + (rot < 0 ? 2 : -2) + 'px);' : ''));
    var fb = document.createElement('div');
    fb.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;';
    d.appendChild(fb);
    paintFallbackInto(fb, false);
    if (src) {
      var im = document.createElement('img');
      im.alt = '';
      im.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;';
      im.onload = function () { im.style.display = 'block'; fb.style.display = 'none'; };
      im.onerror = function () { im.style.display = 'none'; fb.style.display = 'flex'; };
      im.src = src;
      d.appendChild(im);
    }
    return d;
  }
  function buildSinglePanel(dimmed) {
    var P = UI.panels;
    P.innerHTML = '';
    var d = document.createElement('div');
    d.style.cssText = panelShell('flex:1;min-height:0;');
    var fb = document.createElement('div');
    fb.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;';
    d.appendChild(fb);
    paintFallbackInto(fb, dimmed);
    P.appendChild(d);
  }
  // hero panel large + tilted sub-panels below, like a printed action page
  function buildBeatPanels(pg, count) {
    var P = UI.panels;
    P.innerHTML = '';
    var key = String((pg.beat && pg.beat.key) || '');
    var base = key ? 'assets/story/' + curNum + '_' + key : '';
    var n = Math.max(1, Math.min(3, count | 0));
    P.appendChild(mkPanel(base ? base + '.jpg' : '', n === 1 ? 'flex:1;min-height:0;' : 'flex:1 1 62%;min-height:0;', 0));
    if (n >= 2 && base) {
      var row = document.createElement('div');
      row.style.cssText = 'flex:0 0 32%;display:flex;gap:8px;min-height:0;padding:0 2px;';
      row.appendChild(mkPanel(base + '_p2.jpg', 'flex:1;', -1.4));
      if (n >= 3) row.appendChild(mkPanel(base + '_p3.jpg', 'flex:1;', 1.6));
      P.appendChild(row);
    }
  }
  /* ---- ISSUE COVER: full-bleed cover art + drawn masthead + tagline ---- */
  function buildCover() {
    var P = UI.panels;
    P.innerHTML = '';
    P.appendChild(mkPanel(curNum ? 'assets/story/' + curNum + '_cover.jpg' : '', 'flex:1;min-height:0;', 0));
    var story = storyOf(curNum);
    var hook = (story && story.publicHook) ? String(story.publicHook) : teaserLine(story);
    UI.mast.innerHTML =
      '<div style="position:absolute;top:0;left:0;right:0;padding:12px 12px 34px;background:linear-gradient(180deg,rgba(4,4,10,.9) 0%,rgba(4,4,10,.55) 55%,transparent 100%);">'
      + '<div style="font:800 9px Inter,system-ui;letter-spacing:.3em;color:#cbb87a;text-transform:uppercase;">AK BLOCK CHRONICLES &bull; ISSUE No. ' + esc(curNum || '----') + '</div>'
      + '<div style="font:900 clamp(30px,10vw,58px)/1 ' + DISPLAY_FONT + ';color:' + GOLD + ';text-transform:uppercase;letter-spacing:.02em;margin-top:4px;text-shadow:3px 3px 0 ' + INK + ',-2px -2px 0 ' + INK + ',2px -2px 0 ' + INK + ',-2px 2px 0 ' + INK + ',0 12px 30px rgba(0,0,0,.85);">' + esc(curCodename || 'THE BLOCK') + '</div>'
      + '</div>'
      + '<div style="position:absolute;left:12px;right:12px;bottom:14px;">'
      + '<div style="display:inline-block;max-width:100%;background:rgba(10,9,15,.92);border:2px solid ' + GOLD + ';padding:7px 11px;transform:rotate(-1deg);font:700 13px/1.35 ' + COMIC_FONT + ';color:#f2e8c8;box-shadow:3px 3px 0 rgba(0,0,0,.6);">' + esc(hook) + '</div>'
      + '</div>';
    UI.mast.style.display = 'block';
  }

  /* ---- one page ---- */
  function renderPage(i) {
    pageAt = Math.max(0, Math.min(pages.length - 1, i | 0));
    renderSeq += 1;
    var seq = renderSeq;
    var pg = pages[pageAt];
    var ac = accentOf(curCard);
    stopType();
    hideChoice();
    bubbleParts = []; bubbleAt = 0;
    UI.lock.style.display = 'none';
    UI.mast.style.display = 'none';
    UI.caption.style.display = 'none';
    UI.bubblewrap.style.display = 'none';
    UI.more.style.display = 'none';
    UI.chipbox.style.display = (pg.kind === 'cover') ? 'none' : 'block';
    // issue footer counter (the cover is page 0, story pages count from 1)
    var hasCover = pages.length > 0 && pages[0].kind === 'cover';
    if (pg.kind === 'cover') UI.count.textContent = 'COVER';
    else if (hasCover) UI.count.textContent = 'PAGE ' + pageAt + ' OF ' + (pages.length - 1);
    else UI.count.textContent = 'PAGE ' + (pageAt + 1) + ' OF ' + pages.length;
    UI.back.style.visibility = pageAt > 0 ? 'visible' : 'hidden';
    UI.next.textContent = (pageAt < pages.length - 1) ? (pg.kind === 'cover' ? 'OPEN' : 'NEXT') : 'GOT IT';
    // RESUME CONTRACT: every page turn stamps where the reader stands. Only the
    // natural GOT IT close clears it -- an interrupted close keeps the bookmark
    // so index.html's RESUME STORY chip can reopen the book AT this beat.
    try {
      var S = ls();
      if (S && curNum && pages.length && pages[0].kind !== 'unwritten') {
        var hc = pages[0].kind === 'cover';
        S.setItem('ak_chron_resume', JSON.stringify({
          cardNumber: curNum, beatIdx: Math.max(0, pageAt - (hc ? 1 : 0)), t: Date.now()
        }));
      }
    } catch (_eR) {}

    if (pg.kind === 'cover') {
      buildCover();
      return;
    }
    if (pg.kind === 'beat') {
      // fallback panel FIRST (beautiful by default), real art swaps in on load;
      // the multi-panel probe upgrades the layout only if _p2/_p3 exist.
      var key = String((pg.beat && pg.beat.key) || '');
      var cached = key ? PANEL_COUNT[curNum + '_' + key] : 1;
      buildBeatPanels(pg, cached || 1);
      if (key && cached == null) {
        probePanels(curNum, key, function (n) {
          if (seq === renderSeq && n > 1) buildBeatPanels(pg, n);
        });
      }
      setSpeech(pg.text);
    } else if (pg.kind === 'locked') {
      buildSinglePanel(true);
      UI.lock.innerHTML =
        '<div style="font:800 10px Inter,system-ui;letter-spacing:.3em;color:#9a8f6a;text-transform:uppercase;margin-bottom:10px;">UNLOCKS:</div>'
        + '<div style="font:900 clamp(20px,5.4vw,34px)/1.25 \'Playfair Display\',serif;color:' + GOLD + ';text-shadow:0 0 22px rgba(232,197,90,.35),0 2px 8px #000;">' + esc(pg.label || 'KEEP PLAYING') + '</div>'
        + '<div style="width:54px;height:2px;background:' + ac + ';margin:16px auto 0;box-shadow:0 0 10px ' + ac + ';"></div>';
      UI.lock.style.background = 'radial-gradient(ellipse at 50% 42%,#141020cc 0%,#04040acc 74%)';
      UI.lock.style.display = 'flex';
      setSpeech(pg.text);
    } else { // 'unwritten'
      buildSinglePanel(false);
      UI.lock.innerHTML =
        '<div style="font:900 clamp(19px,5vw,32px)/1.3 \'Playfair Display\',serif;color:' + GOLD + ';text-shadow:0 0 22px rgba(232,197,90,.35),0 2px 8px #000;">HIS STORY IS STILL<br>BEING WRITTEN ON THE BLOCK</div>'
        + '<div style="width:54px;height:2px;background:' + ac + ';margin:16px auto 0;box-shadow:0 0 10px ' + ac + ';"></div>';
      UI.lock.style.background = 'transparent';   // let the faction gradient + art carry the page
      UI.lock.style.display = 'flex';
      setSpeech(pg.text);
    }
  }

  /* ---- narrator chip: cardfx idle/walk clip when one resolves, else art ---- */
  function mountChip() {
    releaseClip();
    UI.chip.innerHTML = '';
    var media = null;
    try {
      var CF = global.AK_CARDFX;
      if (CF && typeof CF.resolve === 'function' && typeof CF.acquire === 'function' && curCard) {
        var pth = CF.resolve(curCard, 'idle') || CF.resolve(curCard, 'walk');
        if (pth) {
          var v = CF.acquire(pth);
          if (v) { heldClipPath = pth; media = v; }
        }
      }
    } catch (_e) {}
    if (media) {
      media.style.width = '100%'; media.style.height = '100%'; media.style.objectFit = 'cover';
      UI.chip.appendChild(media);
      return;
    }
    var art = artOf(curCard);
    if (art) {
      UI.chip.innerHTML = '<img src="' + esc(art) + '" alt="" '
        + 'onerror="if(!(window.akImgErr&&akImgErr(this)))this.style.display=\'none\';" '
        + 'style="width:100%;height:100%;object-fit:cover;">';
    }
  }

  /* ---- bubble line for non-beat pages: existing data only, no invention ---- */
  function teaserLine(story) {
    if (story && story.publicHook) return String(story.publicHook);
    try {
      if (typeof global.AK_LORE_GET === 'function' && curNum) {
        var L = global.AK_LORE_GET(curNum);
        if (L && L.tagline) return String(L.tagline);
      }
    } catch (_e) {}
    return 'The block keeps its stories close. Keep playing.';
  }

  /* ============================== open/close ============================== */

  function open(ref, beatIdx) {
    if (HEADLESS) return;
    try {
      curCard = canonAny(ref);
      curNum = numOf(ref);
      var story = storyOf(curNum);
      curCodename = (story && story.codename) || (curCard && curCard.name) || '';
      pages = [];
      if (story && Array.isArray(story.beats) && story.beats.length) {
        for (var i = 0; i < story.beats.length; i++) {
          var b = story.beats[i]; if (!b) continue;
          var ev = evalUnlock(b.unlock, curCard);
          if (ev.ok) pages.push({ kind: 'beat', beat: b, text: String(b.text || '') });
          else pages.push({ kind: 'locked', beat: b, label: ev.label, text: teaserLine(story) });
        }
      }
      // the issue cover fronts any book that has pages behind it
      if (pages.length) pages.unshift({ kind: 'cover' });
      if (!pages.length) pages = [{ kind: 'unwritten', text: teaserLine(story) }];

      ensureUI();
      turning = false;
      UI.codename.textContent = curCodename;
      UI.kicker.textContent = 'BLOCK CHRONICLES' + (curCodename ? (' -- ' + curCodename.toUpperCase()) : '');
      mountChip();
      try {
        UI.page.style.transition = 'none';
        UI.page.style.transform = 'none';
        UI.page.style.opacity = '1';
      } catch (_e0) {}
      applyMood(moodNow());   // the mood ring tints the chrome for this read
      UI.root.style.display = 'flex';
      openFlag = true;
      // RESUME entry point: an explicit beatIdx lands the reader ON that beat's
      // page (the cover fronts the book, so beat 0 = page 1 when a cover exists).
      var startAt = 0;
      if (beatIdx != null && isFinite(beatIdx)) {
        var hasCover = pages.length > 0 && pages[0].kind === 'cover';
        startAt = Math.max(0, Math.min(pages.length - 1, (beatIdx | 0) + (hasCover ? 1 : 0)));
      }
      renderPage(startAt);
    } catch (_e) {}
  }

  // natural === true ONLY on the last-page GOT IT tap -- that one close clears
  // the ak_chron_resume bookmark. Every other close (X button, interrupt(),
  // an external caller) leaves it, so an interrupted read is never lost.
  function close(natural) {
    try {
      stopType();
      releaseClip();
      hideChoice();
      turning = false;
      openFlag = false;
      if (UI && UI.root) UI.root.style.display = 'none';
      if (natural === true) {
        try { var S = ls(); if (S) S.removeItem('ak_chron_resume'); } catch (_e1) {}
      }
    } catch (_e) {}
  }

  // true while the reader overlay owns the screen -- index.html's akStoryFocus
  // gate reads this every frame, so keep it allocation-free and throw-proof.
  function isOpen() {
    if (HEADLESS) return false;
    try { return !!(openFlag && UI && UI.root && UI.root.style.display !== 'none'); } catch (_e) { return false; }
  }

  // The world MUST take the screen (a wild encounter fired mid-read): bow out
  // gracefully -- close WITHOUT clearing the bookmark, then float the one-line
  // bridge banner so the player knows the page waits for them.
  function interrupt() {
    if (HEADLESS) return;
    try {
      if (!isOpen()) return;
      close(false);
      var d = document.createElement('div');
      d.style.cssText = 'position:fixed;left:50%;top:18%;transform:translateX(-50%) rotate(-1.5deg) skewX(-2deg);z-index:' + (Z + 2) + ';background:linear-gradient(180deg,#f6dc80,#e8c55a);color:#181203;border:2px solid ' + INK + ';padding:8px 14px;box-shadow:4px 4px 0 rgba(0,0,0,.6);font:800 13px/1.35 ' + COMIC_FONT + ';pointer-events:none;max-width:84vw;text-align:center;';
      d.textContent = 'The block interrupts. The page waits.';
      document.body.appendChild(d);
      setTimeout(function () { try { d.remove(); } catch (_e1) {} }, 1900);
    } catch (_e) {}
  }

  /* =============================== export ================================= */

  global.AK_CHRONICLES = {
    open: open,
    close: close,
    isOpen: isOpen,            // the reader owns the screen (akStoryFocus gate)
    interrupt: interrupt,      // graceful bow-out: bridge banner, bookmark kept
    isUnlocked: isUnlocked,
    unlockLabel: unlockLabel,
    setMoodPreview: setMoodPreview,   // force a mood on the chrome (testing)
    _eval: evalUnlock,         // exposed for tests / future surfaces
    _mood: moodNow,            // exposed for tests: live mood word
    _evalReq: evalReq,         // exposed for tests: choice req gating
    _recordChoice: recordChoice,      // exposed for tests: log + fx store
    _choiceMade: choiceMade    // exposed for tests: answered-beat lookup
  };

})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
