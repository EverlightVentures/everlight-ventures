/*
 * manga_fx.js -- AK_MANGA (MANGA AS GAME STATE fx layer, bible Section 9)
 * The playable-comic grammar: impact frames in combat, the Battle Call
 * splash before a fight, the loot screen AS a manga page, and the anime
 * short exporter that rides the AK_VIRAL 9:16 recorder pattern.
 * Plain JS, headless-safe (node --check clean), window-guarded, NO
 * em-dashes (hook law, use --). Zero load-time DOM. Every consumer
 * typeof-guards; every dependency here (AK_STORIES, AK_CHRONICLES,
 * AK_VIRAL, MediaRecorder) is optional and degrades gracefully.
 * All dynamic markup goes through esc() (the chronicles.js/viral.js
 * escaping pattern) -- no unescaped string ever reaches innerHTML.
 *
 * Public API (window.AK_MANGA):
 *   impactFrame(opts)   -> 3-6 frame high-contrast gold-on-black ink flash
 *                          at {x,y} (or full-screen). Canvas-drawn burst +
 *                          hand-drawn speed lines, ~240ms, pointer-events
 *                          none, z-index 60, self-removing. Max 1 concurrent
 *                          (extras dropped). opts={x,y,color,full}.
 *   battleCall(opts)    -> the FIGHT splash: comic page frame, rival name /
 *                          crest large, faction accent wash, one hype line.
 *                          Auto-dismiss 1400ms or tap. Returns a Promise
 *                          that resolves on dismiss (chain into combat).
 *                          opts={name,accent,crest,line}.
 *   victoryPage(opts)   -> the loot screen AS a manga page: hero panel,
 *                          optional opts.heroLine speech bubble (the runner
 *                          speaks, win AND loss) docked to a circular
 *                          hero-art chip (opts.heroImg, chronicles recipe),
 *                          VICTORY/DEFEAT drawn as canvas art, loot rows
 *                          ink-stamped on 90ms apart, CONTINUE + optional
 *                          SHARE (AK_VIRAL.shareMoment). Returns the root.
 *                          opts={won,title,panelImg,accent,loot,onContinue,
 *                          shareKind}.
 *   exportShort(cardNumber) -> the ANIME SHORT: unlocked story pages as a
 *                          9:16 Ken Burns sequence with typed captions and
 *                          the gold lower-third, recorded offscreen at
 *                          720x1280 via captureStream + MediaRecorder
 *                          (the exact viral.js recordClip pattern), then
 *                          save/share. No pages or no recorder = a toast.
 *                          Returns Promise<{blob,ext}|null>.
 */
(function (global) {
  'use strict';

  if (global.AK_MANGA) return;
  var HEADLESS = (typeof document === 'undefined');

  /* ---- style constants copied from chronicles.js (ONE book, one look) ---- */
  var GOLD = '#e8c55a';
  var INK = '#05050a';                 // panel borders + gutters ink
  var PAGE_BG = 'linear-gradient(165deg,#1a1620 0%,#141118 42%,#0e0c13 100%)';
  var PAGE_EDGE = 'border-radius:5px;border:1px solid #2b2433;box-shadow:0 18px 44px rgba(0,0,0,.8),inset 0 0 0 1px rgba(232,197,90,.06);';
  var HALFTONE = 'position:absolute;inset:0;pointer-events:none;border-radius:5px;background-image:radial-gradient(rgba(255,255,255,.05) 1px,transparent 1.5px);background-size:6px 6px;mix-blend-mode:overlay;';
  var COMIC_FONT = "'Comic Neue','Comic Sans MS','Chalkboard SE','Segoe Print',system-ui,sans-serif";
  var DISPLAY_FONT = "'Bangers','Luckiest Guy','Comic Neue','Arial Black',Inter,system-ui,sans-serif";
  // Faction accent tints -- mirrors chronicles.js FAC_COL (the ONE canon palette).
  var FAC_COL = {
    boneguard_crew:    '#C9772E',
    zoomie_syndicate:  '#FF2E88',
    leashbreak_tactix: '#7B5CFF',
    k9_circuitry:      '#00E0C0',
    neutral:           '#c9a84c'
  };
  var STEEL = '#9aa4b2';               // defeat drains to cold steel-grey (bible 8.3)
  /* ---- lower-third recipe mirrored from viral.js paintOverlay ---- */
  var V_GOLD = '#e8b84b', V_GOLD_DEEP = '#c8922e', V_INK = '#0a0a0c', V_PAPER = '#f3ead2';
  var SITE = 'alleykingz.online';

  var Z_IMPACT = 60;                   // contract: impact flash sits at 60
  var Z_PAGE = 80;                     // splash/victory pages above chronicles (70)

  /* ============================== helpers ================================ */

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pad4(v) {
    var d = String(v == null ? '' : v).replace(/[^0-9]/g, '');
    return d ? ('0000' + d).slice(-4) : '';
  }
  function accentOr(ac) {
    if (!ac) return GOLD;
    var k = String(ac).toLowerCase();
    return FAC_COL[k] || String(ac);
  }
  // toast recipe mirrored from viral.js
  function toast(msg) {
    try {
      var t = document.createElement('div');
      t.textContent = msg;
      t.style.cssText = 'position:fixed;left:50%;bottom:16%;transform:translateX(-50%);z-index:100002;'
        + 'background:#12100a;color:' + GOLD + ';border:1px solid ' + V_GOLD_DEEP + ';padding:11px 18px;border-radius:10px;'
        + 'font:600 14px system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.6);max-width:82vw;text-align:center;';
      document.body.appendChild(t);
      setTimeout(function () { t.style.transition = 'opacity .4s'; t.style.opacity = '0'; setTimeout(function () { try { t.remove(); } catch (_e) {} }, 420); }, 2200);
    } catch (_e) {}
  }
  function wrapLines(ctx, text, maxW) {
    var words = String(text || '').split(' '), lines = [], cur = '';
    for (var i = 0; i < words.length; i++) {
      var t = cur ? cur + ' ' + words[i] : words[i];
      if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = words[i]; }
      else cur = t;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function isImgPath(s) {
    return /\.(png|jpe?g|webp|gif|svg)(\?|$)/i.test(String(s || ''));
  }

  /* ---- hand-drawn radial speed lines (canvas strokes, never a font) ---- */
  function drawSpeedLines(ctx, cx, cy, rIn, rOut, count, color, alpha) {
    ctx.save();
    ctx.lineCap = 'round';
    for (var i = 0; i < count; i++) {
      var a = Math.random() * Math.PI * 2;
      var r0 = rIn * (0.55 + Math.random() * 0.75);
      var r1 = r0 + (rOut - rIn) * (0.4 + Math.random() * 0.6);
      var wob = (Math.random() - 0.5) * 0.09;             // hand wobble off the ray
      var x0 = cx + Math.cos(a) * r0, y0 = cy + Math.sin(a) * r0;
      var x1 = cx + Math.cos(a + wob) * r1, y1 = cy + Math.sin(a + wob) * r1;
      var mx = (x0 + x1) / 2 + Math.cos(a + Math.PI / 2) * (Math.random() - 0.5) * 8;
      var my = (y0 + y1) / 2 + Math.sin(a + Math.PI / 2) * (Math.random() - 0.5) * 8;
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha * (0.4 + Math.random() * 0.6);
      ctx.lineWidth = 0.6 + Math.random() * 3;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.quadraticCurveTo(mx, my, x1, y1);
      ctx.stroke();
    }
    ctx.restore();
  }
  /* ---- rough ink burst star: jittered spike polygon, gold on black ---- */
  function drawBurstStar(ctx, cx, cy, rIn, rOut, color) {
    var spikes = 12 + ((Math.random() * 5) | 0);
    ctx.save();
    ctx.beginPath();
    for (var i = 0; i < spikes * 2; i++) {
      var a = (Math.PI * i) / spikes + (Math.random() - 0.5) * 0.12;
      var r = (i % 2 === 0 ? rOut : rIn) * (0.82 + Math.random() * 0.36);
      var x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = INK;
    ctx.stroke();
    ctx.restore();
  }

  /* ============================ impactFrame ============================== */
  // 3-6 hand-inked frames redrawn ~240ms total: the Demon Slayer STRIKE beat
  // (bible 8.3 "high-contrast impact frame, single explosive moment").

  var impactLive = false;
  function impactFrame(opts) {
    if (HEADLESS) return;
    if (impactLive) return;                       // max 1 concurrent -- drop extras
    try {
      opts = opts || {};
      impactLive = true;
      var W = Math.max(1, global.innerWidth | 0), H = Math.max(1, global.innerHeight | 0);
      var full = !!opts.full || (opts.x == null && opts.y == null);
      var cx = (opts.x == null) ? W / 2 : +opts.x;
      var cy = (opts.y == null) ? H / 2 : +opts.y;
      var col = accentOr(opts.color);
      var dpr = Math.min(2, (global.devicePixelRatio || 1));
      var cv = document.createElement('canvas');
      cv.width = (W * dpr) | 0; cv.height = (H * dpr) | 0;
      cv.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:' + Z_IMPACT + ';';
      document.body.appendChild(cv);
      var ctx = cv.getContext('2d');
      ctx.scale(dpr, dpr);
      var frames = 3 + ((Math.random() * 4) | 0);   // 3-6 ink frames
      var frameMs = Math.round(240 / frames);       // total ~240ms flash
      var burstR = full ? Math.max(W, H) * 0.62 : Math.min(W, H) * 0.34;
      var at = 0;

      function paintFrame(f) {
        ctx.clearRect(0, 0, W, H);
        // near-monochrome ground: black takes the screen (full) or a local void
        if (full) {
          ctx.fillStyle = 'rgba(3,3,6,.93)';
          ctx.fillRect(0, 0, W, H);
        } else {
          var g = ctx.createRadialGradient(cx, cy, burstR * 0.1, cx, cy, burstR * 1.5);
          g.addColorStop(0, 'rgba(3,3,6,.92)');
          g.addColorStop(1, 'rgba(3,3,6,0)');
          ctx.fillStyle = g;
          ctx.fillRect(0, 0, W, H);
        }
        // the STRIKE frame (2nd) gets the white-hot core; the rest stay gold
        var strike = (f === 1);
        var core = ctx.createRadialGradient(cx, cy, 0, cx, cy, burstR * 0.5);
        core.addColorStop(0, strike ? 'rgba(255,247,224,.95)' : (col + 'e6'));
        core.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = core;
        ctx.fillRect(cx - burstR, cy - burstR, burstR * 2, burstR * 2);
        drawBurstStar(ctx, cx, cy, burstR * 0.16, burstR * (0.3 + f * 0.05), strike ? '#fff7e0' : col);
        // hand-drawn speed lines, redrawn every frame = the flicker IS the ink
        drawSpeedLines(ctx, cx, cy, burstR * 0.4, burstR * (full ? 2.1 : 1.5), full ? 72 : 46, col, 0.95);
        drawSpeedLines(ctx, cx, cy, burstR * 0.5, burstR * (full ? 1.9 : 1.3), 16, '#fff7e0', strike ? 0.9 : 0.45);
      }
      function step() {
        if (at >= frames) {
          try { cv.remove(); } catch (_e) {}
          impactLive = false;
          return;
        }
        try { paintFrame(at); } catch (_e2) {}
        at += 1;
        setTimeout(step, frameMs);
      }
      step();
    } catch (_e) {
      impactLive = false;
    }
  }

  /* ============================= battleCall ============================== */
  // The FIGHT splash: a comic page announcing the rival (bible 9.1 Battle Call).

  var callClose = null;
  function battleCall(opts) {
    if (HEADLESS) return Promise.resolve();
    return new Promise(function (resolve) {
      try {
        if (callClose) { try { callClose(); } catch (_e0) {} }
        opts = opts || {};
        var ac = accentOr(opts.accent);
        var name = String(opts.name || 'THE RIVAL');
        var line = String(opts.line || 'No leash holds this one. Hold the block.');
        var crest = (opts.crest && isImgPath(opts.crest)) ? String(opts.crest) : '';

        var root = document.createElement('div');
        root.style.cssText = 'position:fixed;inset:0;z-index:' + Z_PAGE + ';display:flex;align-items:center;justify-content:center;'
          + 'background:rgba(4,4,10,.9);padding:18px;box-sizing:border-box;cursor:pointer;font-family:Inter,system-ui,sans-serif;';
        var page = document.createElement('div');
        page.style.cssText = 'position:relative;width:min(94vw,540px);height:min(72vh,600px);overflow:hidden;padding:14px;box-sizing:border-box;'
          + 'display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;'
          + 'background:' + PAGE_BG + ';' + PAGE_EDGE
          + 'transform:scale(1.4) rotate(-3deg);opacity:0;transition:transform 150ms cubic-bezier(.2,1.5,.4,1),opacity 130ms;';
        // faction accent color wash over the paper-dark stock
        var wash = document.createElement('div');
        wash.style.cssText = 'position:absolute;inset:0;pointer-events:none;background:'
          + 'radial-gradient(ellipse at 50% 34%,' + ac + '55 0%,transparent 60%),'
          + 'linear-gradient(168deg,' + ac + '26 0%,transparent 52%);';
        page.appendChild(wash);
        // converging speed lines drawn behind the name (canvas strokes)
        var cv = document.createElement('canvas');
        cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;';
        page.appendChild(cv);
        // the call itself -- every dynamic string below passes through esc()
        var body = document.createElement('div');
        body.style.cssText = 'position:relative;z-index:2;max-width:100%;';
        body.innerHTML =
          '<div style="font:800 10px Inter,system-ui;letter-spacing:.3em;color:#cbb87a;text-transform:uppercase;">BLOCK CHRONICLES &bull; BATTLE CALL</div>'
          + (crest ? '<img src="' + esc(crest) + '" alt="" onerror="this.style.display=\'none\';" style="width:min(34vw,150px);height:min(34vw,150px);object-fit:contain;margin:12px auto 2px;display:block;filter:drop-shadow(0 0 26px ' + ac + '88) drop-shadow(0 10px 24px rgba(0,0,0,.8));">' : '')
          + '<div style="font:900 clamp(34px,11vw,64px)/1 ' + DISPLAY_FONT + ';color:' + GOLD + ';text-transform:uppercase;letter-spacing:.02em;margin-top:10px;'
          +   'text-shadow:3px 3px 0 ' + INK + ',-2px -2px 0 ' + INK + ',2px -2px 0 ' + INK + ',-2px 2px 0 ' + INK + ',0 12px 30px rgba(0,0,0,.85);">' + esc(name) + '</div>'
          + '<div style="width:64px;height:3px;background:' + ac + ';margin:14px auto 0;box-shadow:0 0 12px ' + ac + ';"></div>'
          + '<div style="display:inline-block;max-width:92%;margin-top:16px;background:linear-gradient(180deg,#f6dc80,#e8c55a);color:#181203;border:2px solid ' + INK + ';'
          +   'padding:7px 12px;transform:rotate(-1.5deg) skewX(-2deg);box-shadow:3px 3px 0 rgba(0,0,0,.55);font:700 13.5px/1.35 ' + COMIC_FONT + ';">' + esc(line) + '</div>'
          + '<div style="font:800 9px Inter,system-ui;letter-spacing:.28em;color:#9a8f6a;text-transform:uppercase;margin-top:18px;">TAP TO FIGHT</div>';
        page.appendChild(body);
        // halftone print texture across the whole page (chronicles recipe)
        var ht = document.createElement('div');
        ht.style.cssText = HALFTONE;
        page.appendChild(ht);
        root.appendChild(page);
        document.body.appendChild(root);

        // draw the converging lines once the page has a size
        setTimeout(function () {
          try {
            var w = page.clientWidth || 300, h = page.clientHeight || 400;
            var dpr = Math.min(2, (global.devicePixelRatio || 1));
            cv.width = (w * dpr) | 0; cv.height = (h * dpr) | 0;
            var c2 = cv.getContext('2d');
            c2.scale(dpr, dpr);
            drawSpeedLines(c2, w / 2, h * 0.42, Math.min(w, h) * 0.26, Math.max(w, h) * 0.85, 64, ac, 0.5);
            drawSpeedLines(c2, w / 2, h * 0.42, Math.min(w, h) * 0.3, Math.max(w, h) * 0.8, 20, GOLD, 0.35);
          } catch (_e1) {}
        }, 0);
        // punch-in
        try { void page.offsetWidth; page.style.transform = 'scale(1) rotate(0deg)'; page.style.opacity = '1'; } catch (_e2) {}

        var done = false, timer = null;
        function dismiss() {
          if (done) return;
          done = true;
          if (timer) { clearTimeout(timer); timer = null; }
          if (callClose === dismiss) callClose = null;
          try { root.remove(); } catch (_e3) {}
          resolve();
        }
        callClose = dismiss;
        root.addEventListener('click', dismiss);
        timer = setTimeout(dismiss, 1400);          // auto-dismiss or tap
      } catch (_e) { resolve(); }
    });
  }

  /* ============================ victoryPage ============================== */
  // THE loot screen IS a manga page (bible 9.1 Victory): rewards land on the
  // page like printed ink, the big word is DRAWN, never a plain UI font.

  function drawWordArt(cv, word, gold) {
    try {
      var w = Math.max(1, cv.clientWidth || 300), h = 104;
      var dpr = Math.min(2, (global.devicePixelRatio || 1));
      cv.width = (w * dpr) | 0; cv.height = (h * dpr) | 0;
      var ctx = cv.getContext('2d');
      ctx.scale(dpr, dpr);
      // horizontal dash ticks behind the word (motion, hand-ruled)
      ctx.save();
      ctx.strokeStyle = gold ? GOLD : STEEL;
      for (var i = 0; i < 26; i++) {
        var ty = 8 + Math.random() * (h - 16), tx = Math.random() * w;
        ctx.globalAlpha = 0.12 + Math.random() * 0.25;
        ctx.lineWidth = 0.8 + Math.random() * 2;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(tx + 26 + Math.random() * 70, ty + (Math.random() - 0.5) * 3);
        ctx.stroke();
      }
      ctx.restore();
      // skewed, risen lettering: strokes first (double-hit print), then the fill
      ctx.save();
      ctx.translate(w / 2, h * 0.62);
      ctx.transform(1, -0.045, -0.24, 1, 0, 0);     // skew like a shouted SFX
      var size = Math.min(84, Math.max(40, (w - 40) / (word.length * 0.62)));
      ctx.font = '900 ' + (size | 0) + 'px ' + DISPLAY_FONT;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = INK;
      ctx.lineWidth = 11;
      ctx.strokeText(word, 3, 4);                    // dropped ink hit
      ctx.strokeText(word, 0, 0);
      var fg = ctx.createLinearGradient(0, -size / 2, 0, size / 2);
      if (gold) { fg.addColorStop(0, '#f6dc80'); fg.addColorStop(1, '#b8922e'); }
      else { fg.addColorStop(0, '#c8d2dc'); fg.addColorStop(1, '#6b7683'); }
      ctx.fillStyle = fg;
      ctx.fillText(word, 0, 0);
      // rough re-ink passes: jittered thin strokes = hand-lettered edge
      ctx.strokeStyle = 'rgba(5,5,10,.55)';
      ctx.lineWidth = 1.4;
      for (var p = 0; p < 2; p++) {
        ctx.strokeText(word, (Math.random() - 0.5) * 2.4, (Math.random() - 0.5) * 2.4);
      }
      ctx.restore();
    } catch (_e) {}
  }

  function victoryPage(opts) {
    if (HEADLESS) return null;
    try {
      opts = opts || {};
      var won = (opts.won !== false);
      var ac = accentOr(opts.accent);
      var title = String(opts.title || (won ? 'THE BLOCK REMEMBERS' : 'THE BLOCK COLLECTS'));
      var loot = Array.isArray(opts.loot) ? opts.loot : [];
      var word = won ? 'VICTORY' : 'DEFEAT';
      if (!won) ac = STEEL;                          // defeat drains to steel-grey

      var root = document.createElement('div');
      root.style.cssText = 'position:fixed;inset:0;z-index:' + Z_PAGE + ';display:flex;flex-direction:column;align-items:center;justify-content:center;'
        + 'background:rgba(4,4,10,.94);padding:16px;box-sizing:border-box;font-family:Inter,system-ui,sans-serif;';
      var page = document.createElement('div');
      page.style.cssText = 'position:relative;width:min(94vw,540px);max-height:82vh;overflow:hidden;padding:12px;box-sizing:border-box;'
        + 'display:flex;flex-direction:column;background:' + PAGE_BG + ';' + PAGE_EDGE;

      // top rail: issue kicker
      var kick = document.createElement('div');
      kick.style.cssText = 'position:relative;z-index:2;font:800 9px Inter,system-ui;letter-spacing:.3em;color:#cbb87a;text-transform:uppercase;text-align:center;padding:2px 0 8px;';
      kick.textContent = 'BLOCK CHRONICLES • ' + title.toUpperCase();
      page.appendChild(kick);

      // hero panel: ink frame, real art or faction-gradient fallback inside
      var hero = document.createElement('div');
      hero.style.cssText = 'position:relative;z-index:2;flex:0 0 auto;height:min(34vh,240px);overflow:hidden;'
        + 'background:radial-gradient(ellipse at 50% 30%,' + ac + '44 0%,transparent 58%),linear-gradient(168deg,' + ac + '2e 0%,#0a0812 46%,#04040a 100%);'
        + 'border:2px solid ' + INK + ';border-radius:3px;box-shadow:0 2px 10px rgba(0,0,0,.6),inset 0 0 0 1px rgba(232,197,90,.08);';
      if (opts.panelImg) {
        var him = document.createElement('img');
        him.alt = '';
        him.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;'
          + (won ? '' : 'filter:grayscale(.7) brightness(.6);');
        him.onload = function () { him.style.display = 'block'; };
        him.onerror = function () { him.style.display = 'none'; };
        him.src = String(opts.panelImg);
        hero.appendChild(him);
      }
      page.appendChild(hero);

      // the big word, DRAWN as art, slammed across the hero panel seam
      var wordCv = document.createElement('canvas');
      wordCv.style.cssText = 'position:relative;z-index:3;width:100%;height:104px;margin:-46px 0 0;transform:rotate(-2deg);pointer-events:none;'
        + 'filter:drop-shadow(0 10px 22px rgba(0,0,0,.85));';
      page.appendChild(wordCv);

      // hero side-dialogue (opts.heroLine): the RUNNER speaks on the page --
      // a white speech bubble docked to a circular hero-art chip. Chip + bubble
      // + tail values reused from the chronicles narrator-chip recipe (56px
      // gold-ring circle over #15111c; #fdfbf2 bubble, 2.5px ink border,
      // left-pointing double-triangle tail). The dog speaks in DEFEAT too
      // (won:false grays the chip like the hero panel). No heroLine = today's
      // exact page, byte for byte.
      var heroLine = String(opts.heroLine || '');
      if (heroLine) {
        var say = document.createElement('div');
        say.style.cssText = 'position:relative;z-index:3;flex:0 0 auto;display:flex;align-items:flex-end;gap:10px;margin:-4px 0 8px;padding:0 6px;';
        var chip = document.createElement('div');
        chip.style.cssText = 'flex:0 0 auto;width:56px;height:56px;border-radius:50%;overflow:hidden;'
          + 'border:2px solid ' + GOLD + ';box-shadow:0 0 14px rgba(232,197,90,.4),0 4px 10px rgba(0,0,0,.6);background:#15111c;';
        var chipArt = String(opts.heroImg || opts.panelImg || '');
        if (chipArt && isImgPath(chipArt)) {
          var ci = document.createElement('img');
          ci.alt = '';
          ci.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;'
            + (won ? '' : 'filter:grayscale(.7) brightness(.7);');
          ci.onerror = function () { ci.style.display = 'none'; };
          ci.src = chipArt;
          chip.appendChild(ci);
        }
        say.appendChild(chip);
        var bub = document.createElement('div');
        bub.style.cssText = 'position:relative;flex:1;min-width:0;background:#fdfbf2;color:#16131c;border:2.5px solid ' + INK + ';'
          + 'border-radius:15px;padding:9px 12px 11px;box-shadow:0 8px 20px rgba(0,0,0,.55);font:700 13.5px/1.42 ' + COMIC_FONT + ';';
        var tailInk = document.createElement('div');
        tailInk.style.cssText = 'position:absolute;left:-14px;bottom:9px;width:0;height:0;border-top:4px solid transparent;border-bottom:13px solid transparent;border-right:15px solid ' + INK + ';';
        var tailFill = document.createElement('div');
        tailFill.style.cssText = 'position:absolute;left:-9px;bottom:12px;width:0;height:0;border-top:3px solid transparent;border-bottom:9px solid transparent;border-right:11px solid #fdfbf2;';
        bub.appendChild(tailInk);
        bub.appendChild(tailFill);
        var bt = document.createElement('div');
        bt.textContent = heroLine;
        bub.appendChild(bt);
        say.appendChild(bub);
        page.appendChild(say);
      }

      // loot rows land here, stamped one by one
      var lootBox = document.createElement('div');
      lootBox.style.cssText = 'position:relative;z-index:2;flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:7px;padding:2px 6px 6px;';
      page.appendChild(lootBox);

      // footer: CONTINUE + optional SHARE (chron-next button recipe)
      var foot = document.createElement('div');
      foot.style.cssText = 'position:relative;z-index:2;flex:0 0 auto;display:flex;gap:8px;padding-top:8px;';
      var canShare = false;
      try { canShare = !!(global.AK_VIRAL && typeof global.AK_VIRAL.shareMoment === 'function'); } catch (_e0) {}
      if (canShare) {
        var bShare = document.createElement('button');
        bShare.textContent = 'SHARE';
        bShare.style.cssText = 'flex:0 0 100px;background:none;border:1px solid rgba(232,197,90,.4);color:#cbb87a;border-radius:9px;padding:10px 0;font:800 11px Inter,system-ui;letter-spacing:.1em;cursor:pointer;';
        bShare.onclick = function () {
          try { global.AK_VIRAL.shareMoment(String(opts.shareKind || (won ? 'win' : 'levelup')), { title: title }); } catch (_e1) {}
        };
        foot.appendChild(bShare);
      }
      var bGo = document.createElement('button');
      bGo.textContent = 'CONTINUE';
      bGo.style.cssText = 'flex:1;background:linear-gradient(180deg,#e8c55a,#b8922e);border:none;color:#141005;border-radius:9px;padding:10px 0;font:900 11px Inter,system-ui;letter-spacing:.12em;cursor:pointer;box-shadow:0 4px 14px rgba(232,197,90,.3);';
      bGo.onclick = function () {
        try { root.remove(); } catch (_e2) {}
        try { if (typeof opts.onContinue === 'function') opts.onContinue(); } catch (_e3) {}
      };
      foot.appendChild(bGo);
      page.appendChild(foot);

      // halftone print texture across the whole page (chronicles recipe)
      var ht = document.createElement('div');
      ht.style.cssText = HALFTONE;
      page.appendChild(ht);
      root.appendChild(page);
      document.body.appendChild(root);

      setTimeout(function () { drawWordArt(wordCv, word, won); }, 0);

      // loot rows STAMPED onto the page one by one, 90ms apart
      function stampRow(item, i) {
        setTimeout(function () {
          try {
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:10px;background:#fdfbf2;color:#16131c;'
              + 'border:2px solid ' + INK + ';padding:7px 11px;box-shadow:3px 3px 0 rgba(0,0,0,.55);'
              + 'font:700 13.5px/1.3 ' + COMIC_FONT + ';'
              + 'transform:scale(1.8) rotate(' + (i % 2 ? 1.2 : -1.3) + 'deg);opacity:0;';
            var icon = String((item && item.icon) || '');
            if (icon && isImgPath(icon)) {
              var ic = document.createElement('img');
              ic.alt = '';
              ic.src = icon;
              ic.onerror = function () { ic.style.display = 'none'; };
              ic.style.cssText = 'width:24px;height:24px;object-fit:contain;flex:0 0 auto;';
              row.appendChild(ic);
            } else if (icon) {
              var it = document.createElement('span');
              it.style.cssText = 'flex:0 0 auto;font:900 14px ' + COMIC_FONT + ';';
              it.textContent = icon;
              row.appendChild(it);
            }
            var lbl = document.createElement('span');
            lbl.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
            lbl.textContent = String((item && item.label) || 'LOOT');
            row.appendChild(lbl);
            if (item && item.qty != null) {
              var q = document.createElement('span');
              q.style.cssText = 'flex:0 0 auto;font:900 14px ' + COMIC_FONT + ';color:#8a6a12;';
              q.textContent = 'x' + item.qty;
              row.appendChild(q);
            }
            lootBox.appendChild(row);
            void row.offsetWidth;                    // reflow, then the stamp slams
            row.style.transition = 'transform 130ms cubic-bezier(.2,1.7,.4,1),opacity 90ms';
            row.style.transform = 'scale(1) rotate(' + (i % 2 ? 1.2 : -1.3) + 'deg)';
            row.style.opacity = '1';
          } catch (_e4) {}
        }, 240 + i * 90);
      }
      for (var i = 0; i < loot.length; i++) stampRow(loot[i], i);

      return root;
    } catch (_e) { return null; }
  }

  /* ============================ exportShort ============================== */
  // The ANIME SHORT (bible 9.4 format 2): the dog's UNLOCKED story pages as a
  // 9:16 Ken Burns sequence, typed captions, gold lower-third, recorded on an
  // offscreen 720x1280 canvas via the exact viral.js recordClip pattern.

  // pickMime + canRecord mirrored from viral.js
  function pickMime() {
    var t = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return '';
    for (var i = 0; i < t.length; i++) { try { if (MediaRecorder.isTypeSupported(t[i])) return t[i]; } catch (_e) {} }
    return '';
  }
  function canRecord() {
    try { return typeof MediaRecorder !== 'undefined' && !!document.createElement('canvas').captureStream; }
    catch (_e) { return false; }
  }
  function firstSentence(t) {
    t = String(t || '').replace(/^\s+|\s+$/g, '');
    var m = t.match(/^([\s\S]*?[.!?]+["')\]]*)\s/);
    return m ? m[1] : t;
  }
  function loadImg(src) {
    return new Promise(function (resolve) {
      try {
        var im = new Image();
        im.onload = function () { resolve(im); };
        im.onerror = function () { resolve(null); };
        im.src = src;
      } catch (_e) { resolve(null); }
    });
  }
  // which beats does THIS player get in the cut? chronicles is the unlock
  // authority; without it only ungated beats ship (fail closed, bible 4.2).
  function unlockedBeat(num, beat, idx) {
    try {
      var CH = global.AK_CHRONICLES;
      if (CH && typeof CH.isUnlocked === 'function') return !!CH.isUnlocked(num, idx);
    } catch (_e) {}
    var u = beat && beat.unlock;
    if (u == null || u === '' || u === false) return true;
    return /^(free|always|open)$/i.test(String(u).replace(/\s+/g, ''));
  }

  var exporting = false;
  function exportShort(cardNumber) {
    if (HEADLESS) return Promise.resolve(null);
    if (exporting) return Promise.resolve(null);
    var num = pad4(cardNumber);
    var story = null;
    try { if (global.AK_STORIES && num) story = global.AK_STORIES[num] || null; } catch (_e) {}
    if (!story || !Array.isArray(story.beats) || !story.beats.length) {
      toast('His story is still being written on the block');
      return Promise.resolve(null);
    }
    var mime = canRecord() ? pickMime() : '';
    if (!mime) {
      toast('Clip capture not supported here. Read the pages in CHRONICLES');
      return Promise.resolve(null);
    }
    exporting = true;
    var codename = String(story.codename || '');

    // page list: the cover fronts the cut, then every UNLOCKED beat panel
    var wants = [{ src: 'assets/story/' + num + '_cover.jpg', cap: String(story.publicHook || '') }];
    for (var i = 0; i < story.beats.length; i++) {
      var b = story.beats[i];
      if (!b || !b.key) continue;
      if (!unlockedBeat(num, b, i)) continue;
      wants.push({ src: 'assets/story/' + num + '_' + b.key + '.jpg', cap: firstSentence(b.text) });
    }

    return Promise.all(wants.map(function (w) { return loadImg(w.src); })).then(function (imgs) {
      var pages = [];
      for (var j = 0; j < wants.length; j++) { if (imgs[j]) pages.push({ img: imgs[j], cap: wants[j].cap }); }
      if (!pages.length) {
        exporting = false;
        toast('No pages inked yet for this dog');
        return null;
      }

      var PAGE_MS = 4000, TYPE_MS = 34;
      var W = 720, H = 1280;
      var cv = document.createElement('canvas');
      cv.width = W; cv.height = H;
      var ctx = cv.getContext('2d');

      // preview card while the short renders (viral.js share-card recipe)
      var back = document.createElement('div');
      back.style.cssText = 'position:fixed;inset:0;z-index:100000;background:rgba(4,4,7,.9);'
        + 'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;'
        + 'backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);padding:14px;box-sizing:border-box;';
      cv.style.cssText = 'height:min(70vh,560px);aspect-ratio:9/16;max-width:94vw;border-radius:16px;'
        + 'border:2px solid ' + V_GOLD_DEEP + ';box-shadow:0 20px 70px rgba(0,0,0,.7);background:' + V_INK + ';';
      back.appendChild(cv);
      var status = document.createElement('div');
      status.style.cssText = 'font:600 12px system-ui,sans-serif;color:' + V_GOLD + ';opacity:.85;min-height:16px;letter-spacing:.04em;';
      status.textContent = 'INKING THE SHORT...';
      back.appendChild(status);
      var row = document.createElement('div');
      row.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;justify-content:center;max-width:94vw;';
      back.appendChild(row);
      document.body.appendChild(back);

      function btn(label, primary) {
        var b = document.createElement('button'); b.textContent = label;
        b.style.cssText = 'font:700 13px system-ui,sans-serif;padding:12px 16px;border-radius:11px;cursor:pointer;'
          + 'border:1px solid ' + V_GOLD_DEEP + ';'
          + (primary ? ('background:linear-gradient(180deg,' + V_GOLD + ',' + V_GOLD_DEEP + ');color:#141005;')
                     : ('background:#14120c;color:' + V_GOLD + ';'));
        return b;
      }
      function cleanup() { exporting = false; try { back.remove(); } catch (_e) {} }

      // Ken Burns: slow pan/zoom across the panel, direction alternating by page
      function drawPage(pg, idx, tl) {
        var img = pg.img;
        var prog = Math.min(1, tl / PAGE_MS);
        var z = 1.06 + 0.16 * prog;
        var iw = img.naturalWidth || 1, ih = img.naturalHeight || 1;
        var s = Math.max(W / iw, H / ih) * z;
        var dw = iw * s, dh = ih * s;
        var drift = (idx % 2 ? 1 : -1) * (prog - 0.5) * W * 0.06;
        var rise = (idx % 3 === 0 ? 1 : -1) * (prog - 0.5) * H * 0.04;
        ctx.drawImage(img, (W - dw) / 2 + drift, (H - dh) / 2 + rise, dw, dh);
        // manga cut: each page rises out of black
        if (tl < 350) { ctx.fillStyle = 'rgba(3,3,6,' + (1 - tl / 350) + ')'; ctx.fillRect(0, 0, W, H); }
        // typed caption in the gold narrator box (chronicles caption recipe)
        var cap = String(pg.cap || '');
        if (cap) {
          var chars = Math.min(cap.length, Math.floor(tl / TYPE_MS));
          var shown = cap.slice(0, chars);
          if (shown) {
            ctx.save();
            ctx.translate(46, 150);
            ctx.transform(1, -0.02, -0.03, 1, 0, 0);   // the slight caption skew
            ctx.font = '700 30px ' + COMIC_FONT;
            var lines = wrapLines(ctx, shown, W - 170);
            var bh = lines.length * 38 + 24;
            ctx.fillStyle = 'rgba(0,0,0,.55)';
            ctx.fillRect(5, 5, W - 130, bh);           // dropped ink shadow
            var gg = ctx.createLinearGradient(0, 0, 0, bh);
            gg.addColorStop(0, '#f6dc80'); gg.addColorStop(1, '#e8c55a');
            ctx.fillStyle = gg;
            ctx.fillRect(0, 0, W - 130, bh);
            ctx.strokeStyle = INK; ctx.lineWidth = 4;
            ctx.strokeRect(0, 0, W - 130, bh);
            ctx.fillStyle = '#181203';
            for (var li = 0; li < lines.length; li++) ctx.fillText(lines[li], 16, 34 + li * 38);
            ctx.restore();
          }
        }
      }
      // gold lower-third: the viral.js paintOverlay brand block, mirrored
      function drawLowerThird(t) {
        var g = ctx.createLinearGradient(0, H * 0.72, 0, H);
        g.addColorStop(0, 'rgba(8,8,12,0)'); g.addColorStop(0.55, 'rgba(8,8,12,.55)'); g.addColorStop(1, 'rgba(8,8,12,.94)');
        ctx.fillStyle = g; ctx.fillRect(0, H * 0.72, W, H * 0.28);
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = V_GOLD; ctx.font = '700 40px Georgia, serif';
        ctx.fillText('♛ ALLEY KINGZ', 46, H - 128);
        ctx.fillStyle = V_GOLD_DEEP; ctx.fillRect(46, H - 110, 270, 3);
        if (codename) {
          ctx.fillStyle = V_PAPER; ctx.font = '800 34px Georgia, serif';
          ctx.fillText(codename.toUpperCase(), 46, H - 74);
        }
        var beat = 0.5 + 0.5 * Math.sin(t * 3.2);
        ctx.globalAlpha = 0.72 + 0.28 * beat;
        ctx.fillStyle = V_GOLD; ctx.font = '700 30px Georgia, serif';
        ctx.fillText('▶ PLAY FREE · ' + SITE, 46, H - 30);
        ctx.globalAlpha = 1;
      }

      // the recordClip pattern: captureStream + MediaRecorder + rAF composer
      return new Promise(function (resolve) {
        var stream, rec, chunks = [], t0 = performance.now(), raf, stopped = false;
        var durMs = pages.length * PAGE_MS;
        try { stream = cv.captureStream(30); } catch (_e) { cleanup(); toast('Clip capture not supported here'); resolve(null); return; }
        function frame() {
          if (stopped) return;
          var el = performance.now() - t0;
          var idx = Math.min(pages.length - 1, Math.floor(el / PAGE_MS));
          ctx.fillStyle = V_INK; ctx.fillRect(0, 0, W, H);
          try { drawPage(pages[idx], idx, el - idx * PAGE_MS); } catch (_e1) {}
          try { drawLowerThird(el / 1000); } catch (_e2) {}
          try { status.textContent = 'INKING THE SHORT... PAGE ' + (idx + 1) + ' OF ' + pages.length; } catch (_e3) {}
          raf = requestAnimationFrame(frame);
        }
        frame();
        try {
          rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 6000000 });
        } catch (_e4) { stopped = true; if (raf) cancelAnimationFrame(raf); cleanup(); toast('Clip capture not supported here'); resolve(null); return; }
        rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = function () {
          stopped = true; if (raf) cancelAnimationFrame(raf);
          try { stream.getTracks().forEach(function (tr) { tr.stop(); }); } catch (_e5) {}
          var ext = mime.indexOf('mp4') >= 0 ? 'mp4' : 'webm';
          var blob = chunks.length ? new Blob(chunks, { type: mime.split(';')[0] }) : null;
          var out = blob ? { blob: blob, ext: ext } : null;
          offer(out);
          resolve(out);
        };
        try { rec.start(); } catch (_e6) { stopped = true; if (raf) cancelAnimationFrame(raf); cleanup(); toast('Clip capture not supported here'); resolve(null); return; }
        setTimeout(function () { try { if (rec.state !== 'inactive') rec.stop(); } catch (_e7) { cleanup(); resolve(null); } }, durMs);

        // once the short is cut: SAVE / SHARE / CLOSE, the AK_VIRAL grammar
        function offer(out) {
          try {
            if (!out) { status.textContent = 'Could not cut the short here'; }
            else { status.textContent = 'SHORT READY'; }
            var name = 'alleykingz_short_' + num + '_' + Date.now();
            if (out) {
              var bSave = btn('SAVE SHORT', true);
              bSave.onclick = function () {
                try {
                  var u = URL.createObjectURL(out.blob);
                  var a = document.createElement('a'); a.href = u; a.download = name + '.' + out.ext;
                  document.body.appendChild(a); a.click(); a.remove();
                  setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
                  toast('Short saved. Post it and tag the block');
                } catch (_e8) { toast('Could not save the short'); }
              };
              row.appendChild(bSave);
              var bShare = btn('SHARE', false);
              bShare.onclick = function () {
                var text = (codename ? codename + ' -- ' : '') + 'THE BLOCK CHRONICLES. ' + SITE;
                try {
                  if (navigator.canShare) {
                    var f = new File([out.blob], name + '.' + out.ext, { type: out.blob.type });
                    if (navigator.canShare({ files: [f] })) {
                      navigator.share({ files: [f], text: text }).then(function () {}).catch(function () {});
                      return;
                    }
                  }
                } catch (_e9) {}
                try { if (navigator.share) { navigator.share({ title: 'Alley Kingz', text: text }).catch(function () {}); return; } } catch (_ea) {}
                toast('Save the short and post it anywhere');
              };
              row.appendChild(bShare);
            }
            var bClose = btn('CLOSE', false);
            bClose.onclick = cleanup;
            row.appendChild(bClose);
          } catch (_eb) { cleanup(); }
        }
      });
    }).catch(function () { exporting = false; return null; });
  }

  /* =============================== export ================================= */

  global.AK_MANGA = {
    impactFrame: impactFrame,
    battleCall: battleCall,
    victoryPage: victoryPage,
    exportShort: exportShort
  };

})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
