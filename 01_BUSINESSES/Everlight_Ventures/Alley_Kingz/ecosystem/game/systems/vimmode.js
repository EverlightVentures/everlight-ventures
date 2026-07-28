/* ALLEY KINGZ -- systems/vimmode.js  (AK-VIM 2026-06-26, build steps 1-2: CORE + NAVIGATION)
   The hidden keyboard dev-layer. Per AK_VIM_MODE_DESIGN.md + AK_ROADMAP_V2_NAMED.md name canon.
   "The keyboard is your weapon. The modes are your stance. The commands are your combos."

   WHAT THIS FILE IS (and is NOT):
     - A HOST-SIDE keyboard interpreter. It NEVER edits engine.js, the combat loop, or index.html.
       It only DRIVES the same actions a tap/d-pad would: it reads AK_CTX.me and sets me.tx/me.ty
       (the EXACT tap-to-move target the right-zone tap + joystick already use -- index.html loop
       walks the player toward it), and calls the existing global enterZone() for district jumps.
     - DESKTOP / KEYBOARD ONLY + OPT-IN. The keydown listener stays DORMANT until Vim Mode is
       DISCOVERED, and it NEVER fights touch players or normal typing. When not discovered, when
       focus is in a text field, or when the hub is not walkable (overlay / interior / minigame),
       the handler is a clean PASS-THROUGH that consumes nothing.

   THIS BUILD = steps 1-2 ONLY: the core interpreter (mode state + pending count/operator/motion
   buffer + the `-- NORMAL --` mode indicator + discovery) and NAVIGATION. Combat operators,
   Visual mode, Command-line, and registers are LATER steps -- the mode scaffold is here so they
   plug in, but only NORMAL has live bindings now.

   INTERCEPTION: the listener is attached on window in the CAPTURE phase, so it runs BEFORE
   index.html's bubble-phase keydown (which maps held hjkl/WASD/arrows to the keys{} map). When
   vim consumes a key it calls stopImmediatePropagation() so index.html never ALSO sees it (no
   double movement, no stuck keys). Keys vim does NOT claim propagate normally -- so WASD + arrows
   keep working as continuous walk even after discovery; vim repurposes hjkl into discrete,
   count-aware motions on top.

   PERF: zero per-frame work. No onTick, no rAF. The only cost is a cheap keydown handler and a
   lazy DOM indicator created once on discovery. 60fps-safe on a $100 Android (where it never
   even arms -- touch players never trip discovery).
*/
(function () {
  "use strict";

  var hasDOM = (typeof window !== "undefined") && (typeof document !== "undefined");

  // ---- mode scaffold (NORMAL live this build; the rest are reserved for later steps) ----------
  var MODE = { NORMAL: "NORMAL", INSERT: "INSERT", VISUAL: "VISUAL", COMMAND: "COMMAND" };
  var mode = MODE.NORMAL;

  // ---- interpreter state ----------------------------------------------------------------------
  var discovered = false;          // armed only after discovery; persisted in the profile
  var booted = false;              // listeners attached once
  var pending = { count: "", op: null }; // op: 'g' | 'm' | '`' | 'z' (multi-key prefixes)
  var escTimes = [];               // timestamps for triple-Esc discovery
  var cmdBuf = "";                 // COMMAND-LINE buffer (the text typed after the leading ':')
  var lastSearch = "";             // last :/pattern (kept for a future repeat)
  var helpOpen = false;            // :help overlay visibility

  // tuning
  var STEP = 110;                  // px per hjkl motion (one confident stride; counts multiply it)
  var ESC_WINDOW = 1200;           // ms window for triple-Esc

  // ---- safe global readers (index.html exposes me/cam via AK_CTX; zone data are lexical globals)
  function ctx()      { try { return window.AK_CTX || null; } catch (_e) { return null; } }
  function getMe()    { var c = ctx(); if (c && c.me) return c.me; try { return (typeof me !== "undefined") ? me : null; } catch (_e) { return null; } }
  function getCam()   { var c = ctx(); if (c && c.world && c.world.cam) return c.world.cam; try { return (typeof cam !== "undefined") ? cam : null; } catch (_e) { return null; } }
  function vw()       { var c = ctx(); if (c && c.world && c.world.W)  return c.world.W;  try { return (typeof W !== "undefined") ? W : 0; } catch (_e) { return 0; } }
  function vh()       { var c = ctx(); if (c && c.world && c.world.H)  return c.world.H;  try { return (typeof H !== "undefined") ? H : 0; } catch (_e) { return 0; } }
  function worldW()   { var c = ctx(); if (c && c.world && c.world.WORLD_W) return c.world.WORLD_W; try { return (typeof WORLD_W !== "undefined") ? WORLD_W : 1700; } catch (_e) { return 1700; } }
  function worldH()   { var c = ctx(); if (c && c.world && c.world.WORLD_H) return c.world.WORLD_H; try { return (typeof WORLD_H !== "undefined") ? WORLD_H : 1300; } catch (_e) { return 1300; } }
  function getZone()  { try { return (typeof activeZone !== "undefined") ? activeZone : null; } catch (_e) { return null; } }
  function getZones() { try { return (typeof ZONES !== "undefined") ? ZONES : null; } catch (_e) { return null; } }
  function getZNav()  { try { return (typeof ZNAV !== "undefined") ? ZNAV : null; } catch (_e) { return null; } }
  function getEnterZone() {
    try { if (typeof window.enterZone === "function") return window.enterZone; } catch (_e) {}
    try { return (typeof enterZone === "function") ? enterZone : null; } catch (_e) { return null; }
  }
  function safeState()   { try { return (typeof state !== "undefined") ? state : null; } catch (_e) { return null; } }
  function safeInterior(){ try { return (typeof interiorOpen !== "undefined") ? !!interiorOpen : false; } catch (_e) { return false; } }

  // econ profile (discovery + waypoints persist here; falsy-default, zero-state safe)
  function econ() {
    var c = ctx(); if (c && c.econ) return c.econ;
    try { if (window.AK_ECON) return window.AK_ECON; } catch (_e) {}
    return null;
  }
  function loadProf() { var e = econ(); try { return (e && e.loadProfile) ? e.loadProfile() : null; } catch (_e) { return null; } }
  function mutate(fn) { var e = econ(); try { if (e && e.mutateProfile) { e.mutateProfile(fn); return true; } } catch (_e) {} return false; }

  // ---- "walkable hub" gate: vim only drives motion in IN_ZONE; everywhere else it is inert -----
  function isWalkable() {
    var st = safeState();
    if (st && st !== "IN_ZONE") return false;   // overlay / minigame / transition -> pass-through
    if (safeInterior()) return false;            // inside a building -> pass-through
    return true;
  }

  // ---- movement primitives: ALL set me.tx/me.ty (the existing tap-to-move intent) --------------
  function moveTo(x, y) {
    var m = getMe(); if (!m) return false;
    var pad = 20;
    m.tx = Math.max(pad, Math.min(worldW() - pad, x));
    m.ty = Math.max(pad, Math.min(worldH() - pad, y));
    return true;
  }
  function stepMove(dx, dy, n) {
    var m = getMe(); if (!m) return false;
    n = n || 1;
    return moveTo(m.x + dx * STEP * n, m.y + dy * STEP * n);
  }

  // interactables in the current district = its buildings (the doors you can enter)
  function interactables() {
    var z = getZone();
    var list = (z && z.buildings) ? z.buildings.slice() : [];
    if (!list.length) { try { if (typeof window.curBuildings === "function") list = window.curBuildings().slice(); } catch (_e) {} }
    // deterministic reading order: top-to-bottom, then left-to-right
    list.sort(function (a, b) { return (a.y - b.y) || (a.x - b.x); });
    return list;
  }
  function doorY(b) { return b.y + (b.h ? b.h / 2 : 0); }
  function nearestIdx(list) {
    var m = getMe(); if (!m || !list.length) return -1;
    var best = -1, bd = Infinity;
    for (var i = 0; i < list.length; i++) {
      var d = Math.hypot(m.x - list[i].x, m.y - doorY(list[i]));
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }
  function gotoBuilding(b) { if (!b) return false; return moveTo(b.x, doorY(b)); }

  // w/b = next/prev interactable (count-aware, wraps); e = snap onto nearest interactable's door
  function jumpInteractable(dir, n) {
    var list = interactables(); if (!list.length) return false;
    var cur = nearestIdx(list); if (cur < 0) cur = 0;
    var idx = ((cur + dir * (n || 1)) % list.length + list.length) % list.length;
    return gotoBuilding(list[idx]);
  }
  function jumpNearestDoor() {
    var list = interactables(); if (!list.length) return false;
    var i = nearestIdx(list); return (i >= 0) && gotoBuilding(list[i]);
  }

  // 0 = district entrance (zone center) ; ^ = first active node ; $ = boss node (Town Hall / arena)
  function gotoEntrance() { return moveTo(worldW() / 2, worldH() / 2); }
  function gotoFirstNode() { var list = interactables(); return list.length ? gotoBuilding(list[0]) : false; }
  function gotoBossNode() {
    var list = interactables(); if (!list.length) return false;
    var re = /(arena|town\s*hall|arcade|boss|throne|king)/i;
    for (var i = 0; i < list.length; i++) {
      var b = list[i];
      if (re.test(String(b.id || "")) || re.test(String(b.label || ""))) return gotoBuilding(b);
    }
    return gotoBuilding(list[list.length - 1]); // degrade: last node
  }

  // {/} = sector jumps: vertical thirds of the district (paragraph-style), count = number of bands
  function sectorJump(dir, n) {
    var m = getMe(); if (!m) return false;
    var H3 = worldH() / 3;
    var band = Math.max(0, Math.min(2, Math.floor(m.y / H3)));
    band = Math.max(0, Math.min(2, band + dir * (n || 1)));
    return moveTo(m.x, band * H3 + H3 / 2);
  }

  // Ctrl-u / Ctrl-d = half-screen scroll. Camera is player-locked, so we move the PLAYER half a
  // viewport (which scrolls the view exactly half a screen). count = number of half-screens.
  function halfScreen(dir, n) {
    var m = getMe(); if (!m) return false;
    var amt = (vh() || 600) / 2 * (n || 1);
    return moveTo(m.x, m.y + dir * amt);
  }

  // gg = HOME_TURF ; G = farthest reachable (unlocked) district -- "held" approximated, no
  // ownership API is exposed yet, so we degrade to farthest UNLOCKED by grid distance.
  function jumpHome() {
    var go = getEnterZone(), z = getZone();
    if (z && z.id === "HOME_TURF") return gotoEntrance();
    if (go) { try { go("HOME_TURF", { x: worldW() / 2, y: worldH() / 2 }); return true; } catch (_e) {} }
    return false; // degrade: no zone API
  }
  function jumpFarthestDistrict() {
    var go = getEnterZone(), zones = getZones(), nav = getZNav(), here = getZone();
    if (!go || !zones || !here) return false;
    var cx = here.gx, cy = here.gy, ids = nav || Object.keys(zones);
    var best = null, bd = -1;
    for (var i = 0; i < ids.length; i++) {
      var z = zones[ids[i]];
      if (!z || z.locked || z.id === here.id) continue;
      var d = Math.abs((z.gx || 0) - (cx || 0)) + Math.abs((z.gy || 0) - (cy || 0));
      if (d > bd) { bd = d; best = z; }
    }
    if (!best) return false;
    try { go(best.id, { x: worldW() / 2, y: worldH() / 2 }); return true; } catch (_e) { return false; }
  }

  // m{a-z} set waypoint ; `{a-z} jump waypoint. Persist in the profile (falsy-default vimMarks).
  function setMark(letter) {
    var m = getMe(), z = getZone(); if (!m) return false;
    return mutate(function (p) {
      if (!p.vimMarks || typeof p.vimMarks !== "object") p.vimMarks = {};
      p.vimMarks[letter] = { x: Math.round(m.x), y: Math.round(m.y), zone: z ? z.id : null };
    });
  }
  function jumpMark(letter) {
    var p = loadProf(); if (!p || !p.vimMarks) return false;
    var mk = p.vimMarks[letter]; if (!mk) return false;
    var z = getZone(), go = getEnterZone();
    if (z && mk.zone && mk.zone !== z.id) {
      if (go) { try { go(mk.zone, { x: mk.x, y: mk.y }); return true; } catch (_e) {} }
      return false; // degrade: cross-zone mark but no zone API
    }
    return moveTo(mk.x, mk.y);
  }

  // zz = center on player. The camera already locks to the player every frame, so this is a
  // confirmed NO-OP (kept for completeness + the indicator flash). Documented, intentional.
  function centerOnPlayer() { return true; }

  // ---- the pending-command state machine (count + operator + motion) ---------------------------
  function resetPending() { pending.count = ""; pending.op = null; }
  function count() { return pending.count ? parseInt(pending.count, 10) : 1; }

  // feed(key) -> true if vim consumed the key (caller then preventDefault + stopImmediatePropagation)
  function feed(key) {
    // resolve a pending multi-key prefix first
    if (pending.op) {
      var op = pending.op;
      if (op === "g") { pending.op = null; if (key === "g") { jumpHome(); resetPending(); render(); return true; } /* gu/gU later */ }
      else if (op === "z") { pending.op = null; if (key === "z") { centerOnPlayer(); resetPending(); render(); return true; } }
      else if (op === "m") { pending.op = null; if (/^[a-z]$/i.test(key)) { setMark(key.toLowerCase()); resetPending(); render(); return true; } resetPending(); render(); return true; }
      else if (op === "`") { pending.op = null; if (/^[a-z]$/i.test(key)) { jumpMark(key.toLowerCase()); resetPending(); render(); return true; } resetPending(); render(); return true; }
      // prefix did not complete -> fall through and treat key as a fresh command
    }

    // count digits (0 is a motion when no count is in progress, vim-style)
    if (/^[0-9]$/.test(key) && !(key === "0" && pending.count === "")) {
      pending.count += key; render(); return true;
    }

    var n = count(), did = true;
    switch (key) {
      case "h": stepMove(-1, 0, n); break;
      case "l": stepMove(1, 0, n); break;
      case "k": stepMove(0, -1, n); break;
      case "j": stepMove(0, 1, n); break;
      case "w": jumpInteractable(1, n); break;
      case "b": jumpInteractable(-1, n); break;
      case "e": jumpNearestDoor(); break;
      case "0": gotoEntrance(); break;
      case "^": gotoFirstNode(); break;
      case "$": gotoBossNode(); break;
      case "G": jumpFarthestDistrict(); break;
      case "{": sectorJump(-1, n); break;
      case "}": sectorJump(1, n); break;
      case "g": pending.op = "g"; render(); return true; // wait for second key (gg)
      case "z": pending.op = "z"; render(); return true; // wait for second key (zz)
      case "m": pending.op = "m"; render(); return true; // wait for a-z (set mark)
      case "`": pending.op = "`"; render(); return true; // wait for a-z (jump mark)
      default: did = false;
    }
    if (did) { resetPending(); render(); return true; }
    // not a vim key -> drop any half-typed count and let it pass through to the hub
    resetPending(); render();
    return false;
  }

  // ---- discovery -------------------------------------------------------------------------------
  function trackEsc(now) {
    escTimes.push(now);
    while (escTimes.length && now - escTimes[0] > ESC_WINDOW) escTimes.shift();
    if (escTimes.length >= 3) { escTimes = []; discover("triple-esc"); }
  }

  function discover(source) {
    if (discovered) return false;
    discovered = true;
    mutate(function (p) { p.vimDiscovered = true; });
    ensureIndicator();
    setMode(MODE.NORMAL);
    showIndicator(true);
    render();
    var c = ctx();
    try { if (c && c.showBanner) c.showBanner("VIM MODE unlocked -- hjkl to move, Esc to reset, : to command", 3); } catch (_e) {}
    try { console.log("[AK-VIM] discovered via", source || "unknown"); } catch (_e) {}
    return true;
  }

  function readDiscovered() { var p = loadProf(); if (p && p.vimDiscovered) { discovered = true; } }

  // ---- the mode indicator (lazy DOM, vim-styled corner badge) ----------------------------------
  var bar = null, barMode = null, barCmd = null;
  function ensureIndicator() {
    if (bar || !hasDOM || !document.body) return bar;
    bar = document.createElement("div");
    bar.id = "ak-vim-bar";
    bar.style.cssText =
      "position:fixed;right:10px;bottom:10px;z-index:30;display:none;pointer-events:none;" +
      "font:700 12px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.06em;" +
      "padding:5px 9px;border-radius:6px;background:rgba(8,8,10,.86);color:#e8c55a;" +
      "border:1px solid rgba(201,168,76,.5);border-left:3px solid #c9a84c;" +
      "box-shadow:0 2px 10px rgba(0,0,0,.5);text-shadow:0 1px 0 #000;user-select:none;";
    barMode = document.createElement("span");
    barCmd = document.createElement("span");
    barCmd.style.cssText = "margin-left:10px;color:#b9a76a;font-weight:900;";
    bar.appendChild(barMode);
    bar.appendChild(barCmd);
    document.body.appendChild(bar);
    return bar;
  }
  function showIndicator(on) { if (!bar) return; bar.style.display = on ? "block" : "none"; }
  function render() {
    if (!bar) return;
    barMode.textContent = "-- " + mode + " --";
    barCmd.textContent = (pending.count || "") + (pending.op || "");
  }

  function setMode(m) {
    if (!MODE[m] && m !== MODE.NORMAL && m !== MODE.INSERT && m !== MODE.VISUAL && m !== MODE.COMMAND) return;
    mode = m; render();
  }

  // ===========================================================================================
  // COMMAND-LINE MODE  (press ':' in NORMAL -> a bottom ':' prompt, vim-style)
  //   :w   persist the profile            :q / :q!  close the top open panel/menu
  //   :wq / :x  save + close              :<n>      jump to CROWN BLOODLINE chapter n
  //   :/text   search the district's interactables  :help [age|privacy|tos|stripe|vim]
  // HOST-SIDE ONLY: every command DRIVES an existing global (AK_ECON.mutateProfile,
  // AKStory.advance, window.exitInterior, AKWorldMap.close). It never edits engine.js. The
  // prompt only ever arms for a discovered keyboard player -- touch players never see it.
  // ===========================================================================================

  function flash(msg, secs) {
    var c = ctx();
    try { if (c && c.showBanner) { c.showBanner(msg, secs || 2.4); return true; } } catch (_e) {}
    try { console.log("[AK-VIM]", msg); } catch (_e) {}
    return false;
  }
  var ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  function roman(n) { return ROMAN[n | 0] || String(n | 0); }

  // ---- the ':' prompt (lazy DOM, vim-styled bottom bar; created once on first open) ------------
  var cmd = null, cmdTxt = null;
  function ensureCmdline() {
    if (cmd || !hasDOM || !document.body) return cmd;
    if (!document.getElementById("ak-vim-kf")) {
      var kf = document.createElement("style"); kf.id = "ak-vim-kf";
      kf.textContent = "@keyframes akVimCaret{0%,49%{opacity:1}50%,100%{opacity:0}}";
      (document.head || document.body).appendChild(kf);
    }
    cmd = document.createElement("div");
    cmd.id = "ak-vim-cmd";
    cmd.style.cssText =
      "position:fixed;left:0;right:0;bottom:0;z-index:31;display:none;pointer-events:none;" +
      "font:600 14px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.02em;" +
      "padding:7px 12px;background:rgba(6,6,9,.94);color:#e8c55a;" +
      "border-top:2px solid #c9a84c;box-shadow:0 -3px 14px rgba(0,0,0,.55);" +
      "text-shadow:0 1px 0 #000;user-select:none;white-space:pre;overflow:hidden;";
    cmdTxt = document.createElement("span");
    var caret = document.createElement("span");
    caret.textContent = "█";
    caret.style.cssText = "color:#e8c55a;animation:akVimCaret 1s steps(1) infinite;margin-left:1px;";
    cmd.appendChild(document.createTextNode(":"));
    cmd.appendChild(cmdTxt);
    cmd.appendChild(caret);
    document.body.appendChild(cmd);
    return cmd;
  }
  function renderCmdline() { if (cmdTxt) cmdTxt.textContent = cmdBuf; }
  function openCmdline() {
    ensureCmdline();
    cmdBuf = "";
    setMode(MODE.COMMAND);
    if (cmd) cmd.style.display = "block";
    renderCmdline(); render();
  }
  function closeCmdline() {
    cmdBuf = "";
    if (cmd) cmd.style.display = "none";
    setMode(MODE.NORMAL);
    resetPending(); render();
  }

  // keystrokes while the ':' prompt is open -- COMMAND mode owns the keyboard entirely
  function onCmdKey(e) {
    var key = e.key;
    if (key === "Escape")    { closeCmdline(); consume(e); return; }
    if (key === "Enter")     { var line = cmdBuf; closeCmdline(); execCmd(line); consume(e); return; }
    if (key === "Backspace") { if (!cmdBuf.length) closeCmdline(); else { cmdBuf = cmdBuf.slice(0, -1); renderCmdline(); } consume(e); return; }
    if (key && key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (cmdBuf.length < 64) { cmdBuf += key; renderCmdline(); }
      consume(e); return;
    }
    consume(e); // swallow arrows / tab / fn / lone modifiers so the hub never sees them
  }

  // ---- :command dispatch -----------------------------------------------------------------------
  function execCmd(raw) {
    var line = String(raw || "").trim();
    if (!line) return;                                                 // bare ':' -> no-op
    if (/^[0-9]+$/.test(line))  { jumpChapter(parseInt(line, 10)); return; }    // :<n>
    if (line.charAt(0) === "/") { searchInteractables(line.slice(1)); return; } // :/text
    var head = line.split(/\s+/)[0].toLowerCase();
    var rest = line.slice(head.length).trim();
    switch (head) {
      case "w":              cmdWrite(); break;
      case "q": case "q!":   cmdClose(); break;
      case "wq": case "x":   cmdWrite(); cmdClose(); break;
      case "help": case "h": helpCmd(rest.toLowerCase()); break;
      case "vim":            flash("You already walk with the terminal. :help vim for the manual."); break;
      default:               flash("E492: Not a street command: " + line);     // vim-flavored miss
    }
  }

  // :w -- persist the profile. A no-op mutate re-saves the CURRENT shape (no new fields written),
  // so a never-discovered profile stays byte-identical; only an explicit :w ever touches storage.
  function cmdWrite() { var ok = mutate(function (_p) {}); flash(ok ? "“the block” written" : "E212: nothing to write to"); }

  // :q -- close the top open panel / menu by driving the game's EXISTING closers (engine frozen).
  function cmdClose() { if (closeTopPanel()) return; flash("E444: nothing open to close"); }
  function closeTopPanel() {
    try { if (safeInterior() && typeof window.exitInterior === "function") { window.exitInterior(); return true; } } catch (_e) {}
    try { if (window.AKWorldMap && AKWorldMap.isOpen && AKWorldMap.isOpen()) { AKWorldMap.close(); return true; } } catch (_e) {}
    if (helpOpen) { closeHelp(); return true; }
    var ov = null;
    try { ov = document.querySelector("#toolspanel.show,#crewpanel.show,#tradepanel.show"); } catch (_e) {}
    if (ov) { try { ov.classList.remove("show"); return true; } catch (_e) {} }
    try { var soc = document.getElementById("ak-social"); if (soc && soc.classList.contains("open") && window.AKSocial && AKSocial.close) { AKSocial.close(); return true; } } catch (_e) {}
    var ids = ["transitpanel", "upgpanel", "dogpicker"];
    for (var i = 0; i < ids.length; i++) {
      var p = document.getElementById(ids[i]);
      if (p && p.style && p.style.display && p.style.display !== "none") { p.style.display = "none"; return true; }
    }
    return false;
  }

  // :<n> -- jump to CROWN BLOODLINE chapter n, GATED by rank/turf (drives AKStory.advance, which
  // honors the climb's gates). The existing chapter-card poll in index.html shows the card.
  function jumpChapter(n) {
    var S = null; try { S = window.AKStory; } catch (_e) {}
    if (!S || !S.stage) { flash("the streets have no story layer here"); return; }
    var st = S.stage(); var cur = st.idx | 0, g = st.gen | 0;
    var stages = (S.GENS && S.GENS[g] && S.GENS[g].stages) || S.STAGES || [];
    var max = stages.length || 7;
    if (n < 1) return;
    if (n > max) {                                                     // the rank-ceiling / collar reveal
      flash("There is no Chapter " + n + ". The climb itself was the Mongrel King's cage. -- the Old Pack", 4);
      return;
    }
    var target = n - 1;
    if (target <= cur) {                                              // re-read a chapter you have reached
      var c0 = stages[target] || {};
      flash("Chapter " + roman(n) + " -- " + (c0.title || "") + (c0.objective ? ": " + c0.objective : ""), 4);
      return;
    }
    try { if (S.check) S.check(); } catch (_e) {}                     // count any karma/turf earned since
    var now = S.stage().idx | 0, guard = 0;
    while (now < target && guard++ < 16) {
      var r = S.advance(false);                                       // GATED advance (respects rank/turf)
      var ni = (typeof r === "number") ? r : (S.stage().idx | 0);
      if (ni <= now) break;                                           // gate not met -> stalled
      now = ni;
    }
    if (now >= target) { flash("Chapter " + roman(n) + " -- the Crown Bloodline moves.", 3); }
    else {
      var nx = stages[now + 1] || stages[now] || {};
      flash("Chapter " + roman(n) + " is sealed. First: " + (nx.objective || "earn your rank and hold your turf"), 4);
    }
  }

  // :/text -- search the district's interactables (its buildings); jump to the next match (wraps)
  function searchInteractables(q) {
    q = String(q || "").trim().toLowerCase();
    if (!q) return false;
    var list = interactables();
    if (!list.length) { flash("nothing to search on this block"); return false; }
    var from = nearestIdx(list); if (from < 0) from = 0;
    for (var off = 1; off <= list.length; off++) {
      var b = list[(from + off) % list.length];
      var hay = (String(b.id || "") + " " + String(b.label || "")).toLowerCase();
      if (hay.indexOf(q) >= 0) { gotoBuilding(b); lastSearch = q; flash("/" + q + "  →  " + (b.label || b.id)); return true; }
    }
    flash("E486: no match -- /" + q);
    return false;
  }

  // ---- :help -- compliance topics + the SECRET MANUAL (lazy gold overlay, Esc/tap/close-btn) ----
  var help = null, helpTitle = null, helpBody = null;
  var HELP_TOPICS = {
    "": [
      "the terminal layer's manual.",
      "",
      ":help age      -- who can play, who can pay",
      ":help privacy  -- what we keep, your rights",
      ":help tos      -- the rules of the block",
      ":help stripe   -- how the money moves",
      ":help vim      -- the dev's edge (the manual)",
      "",
      "hjkl move.  : command.  Esc reset."
    ],
    "age": [
      "Alley Kingz is built for mature players.",
      "",
      "You must be 18 or older (or your region's age of",
      "majority) to make any real-money purchase. There is",
      "NO real-money gambling and NO cash-out -- gems and",
      "gold never convert back into money. Under age? Walk",
      "the block for free and keep your wallet closed."
    ],
    "privacy": [
      "What the block knows about you.",
      "",
      "We keep only what runs your account: your progress,",
      "your pack, your purchases. We do NOT sell or share",
      "your personal data. You can ask what we hold, ask us",
      "to delete it, and opt out of any sale or share",
      "(CCPA / CPRA). Your progress lives on your device and",
      "your linked account -- nowhere shady."
    ],
    "tos": [
      "The rules of the block.",
      "",
      "Play fair: no cheating the servers, no real-money",
      "trading of accounts, no harassing other packs. Gems,",
      "gold, and cards are a revocable license to in-game",
      "content -- you own the fun, not a financial asset. We",
      "can update the rules; big changes get announced",
      "in-game. Break the code and the King can pull your",
      "crown (suspend the account)."
    ],
    "stripe": [
      "How the money moves.",
      "",
      "Real-money purchases (gem packs) run through Stripe",
      "secure checkout. We never see or store your card",
      "number -- Stripe handles it. Everything you buy is",
      "in-game value only and is never cashable. Refunds",
      "follow the store's policy; reach out before you",
      "dispute so we can sort it clean."
    ]
  };
  // SECRET MANUAL -- verbatim from AK_VIM_MODE_DESIGN.md (shown on :help vim).
  var MANUAL =
    "VIM MODE -- The Dev's Edge. You found what the streets whisper about: " +
    "a deeper layer to this city, for those who speak the terminal. hjkl to move. " +
    "Esc to reset. : to command. The more fluent you get, the more the city opens. " +
    "Every command works in your editor too. This is not a game mechanic. " +
    "This is a lifestyle upgrade. :wq";

  function ensureHelp() {
    if (help || !hasDOM || !document.body) return help;
    help = document.createElement("div");
    help.id = "ak-vim-help";
    help.style.cssText =
      "position:fixed;inset:0;z-index:46;display:none;align-items:center;justify-content:center;" +
      "background:rgba(4,4,6,.84);padding:18px;";
    var card = document.createElement("div");
    card.style.cssText =
      "position:relative;width:min(92vw,560px);max-height:82vh;overflow:auto;" +
      "background:linear-gradient(180deg,#0c0b08,#070708);color:#e8c55a;" +
      "border:1px solid rgba(201,168,76,.55);border-left:4px solid #c9a84c;border-radius:10px;" +
      "box-shadow:0 12px 40px rgba(0,0,0,.6);padding:18px 20px 22px;" +
      "font:400 13.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;";
    helpTitle = document.createElement("div");
    helpTitle.style.cssText = "font-weight:800;font-size:13px;letter-spacing:.16em;color:#c9a84c;text-transform:uppercase;margin-bottom:12px;";
    helpBody = document.createElement("div");
    helpBody.style.cssText = "white-space:pre-wrap;color:#d9c9a4;";
    var x = document.createElement("button");
    x.textContent = "esc";
    x.style.cssText = "position:absolute;top:12px;right:14px;background:none;border:1px solid rgba(201,168,76,.4);color:#b9a76a;border-radius:6px;padding:3px 8px;font:700 11px ui-monospace,monospace;cursor:pointer;";
    x.onclick = function () { closeHelp(); };
    card.appendChild(x); card.appendChild(helpTitle); card.appendChild(helpBody);
    help.appendChild(card);
    help.addEventListener("click", function (ev) { if (ev.target === help) closeHelp(); });
    document.body.appendChild(help);
    return help;
  }
  function helpCmd(topic) {
    topic = String(topic || "").trim().toLowerCase();
    ensureHelp(); if (!help) { flash("help unavailable here"); return; }
    if (topic === "vim") {
      helpTitle.textContent = ":help vim -- The Dev's Edge";
      helpBody.textContent = MANUAL;
    } else if (Object.prototype.hasOwnProperty.call(HELP_TOPICS, topic)) {
      helpTitle.textContent = ":help" + (topic ? " " + topic : " -- Alley Kingz");
      helpBody.textContent = HELP_TOPICS[topic].join("\n");
    } else {
      helpTitle.textContent = ":help -- no topic “" + topic + "”";
      helpBody.textContent = HELP_TOPICS[""].join("\n");
    }
    help.style.display = "flex";
    helpOpen = true;
  }
  function closeHelp() { if (help) help.style.display = "none"; helpOpen = false; }

  // ---- the keydown interpreter (CAPTURE phase, so it precedes index.html's bubble handler) ------
  function consume(e) { try { e.preventDefault(); e.stopImmediatePropagation(); } catch (_e) {} }

  function inEditable() {
    var a = (hasDOM && document.activeElement) ? document.activeElement : null;
    if (!a) return false;
    var t = (a.tagName || "").toUpperCase();
    if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return true;
    if (a.isContentEditable) return true;
    return false;
  }

  function onKeyDown(e) {
    var key = e.key;
    if (key == null) return;

    // triple-Esc discovery is observed ALWAYS (even before discovery, even in a text field).
    if (key === "Escape") { trackEsc(Date.now()); }

    if (!discovered) return;          // DORMANT until discovered -> clean pass-through

    // COMMAND-LINE owns the entire keyboard while the ':' prompt is open.
    if (mode === MODE.COMMAND) { onCmdKey(e); return; }

    // the :help overlay is modal-ish: Esc closes it; every other key pauses motion (passes through).
    if (helpOpen) { if (key === "Escape") { closeHelp(); consume(e); return; } return; }

    if (inEditable()) return;         // never fight normal typing
    if (!isWalkable()) {              // overlay / interior / minigame -> never consume keys
      if (key === "Escape") { resetPending(); setMode(MODE.NORMAL); render(); }
      return;
    }

    // Esc = the panic button: reset to Normal + clear the pending buffer. Not consumed, so any
    // UI that also listens for Esc still gets it.
    if (key === "Escape") { resetPending(); setMode(MODE.NORMAL); render(); return; }

    // only NORMAL mode has live bindings this build (Insert/Visual/Command are later steps)
    if (mode !== MODE.NORMAL) return;

    // modifiers: claim ONLY Ctrl-u / Ctrl-d. Leave every other modified combo to the browser.
    if (e.ctrlKey || e.metaKey || e.altKey) {
      if (e.ctrlKey && !e.metaKey && !e.altKey) {
        var k = (key || "").toLowerCase();
        if (k === "u") { halfScreen(-1, count()); resetPending(); render(); consume(e); return; }
        if (k === "d") { halfScreen(1, count()); resetPending(); render(); consume(e); return; }
      }
      return; // pass-through other modified combos
    }

    // ':' opens the COMMAND-LINE prompt (Shift+; -> no ctrl/meta/alt, so it reaches here).
    if (key === ":") { openCmdline(); consume(e); return; }

    if (feed(key)) consume(e);
  }

  // discovery via typing :vim in any text field (input/textarea/contenteditable)
  function onInput(e) {
    if (discovered) return;
    var t = e && e.target; if (!t) return;
    var v = "";
    try { v = (t.value != null) ? String(t.value) : (t.isContentEditable ? String(t.textContent || "") : ""); } catch (_e) { return; }
    if (v.toLowerCase().indexOf(":vim") >= 0) {
      discover("command");
      // strip the token so it does not pollute the field / get submitted
      try { if (t.value != null) t.value = v.replace(/:vim/i, ""); } catch (_e) {}
    }
  }

  // ---- boot (idempotent) -----------------------------------------------------------------------
  function boot() {
    if (booted || !hasDOM) return;
    booted = true;
    readDiscovered();
    window.addEventListener("keydown", onKeyDown, true);   // CAPTURE: precede index.html
    document.addEventListener("input", onInput, true);
    if (discovered) { ensureIndicator(); showIndicator(true); render(); }
  }

  // ---- public API + registry. Export window.AK_VIM BEFORE the registry bail (headless-safe). ----
  var AK_VIM = {
    id: "vimmode",
    MODES: MODE,
    discover: function (src) { return discover(src || "api"); }, // future graffiti hook calls this
    isDiscovered: function () { return !!discovered; },
    getMode: function () { return mode; },
    setMode: setMode,
    reset: function () { closeCmdline(); closeHelp(); resetPending(); setMode(MODE.NORMAL); render(); },
    openCmd: function () { openCmdline(); },                      // open the ':' prompt programmatically
    exec: function (line) { execCmd(String(line == null ? "" : line)); }, // run a :command (no leading ':')
    help: function (topic) { helpCmd(topic || ""); },            // open :help [topic]
    MANUAL: MANUAL,                                              // the secret manual (verbatim)
    _feed: feed                                                  // internal / testing
  };

  if (typeof window !== "undefined") {
    window.AK_VIM = AK_VIM;
    try {
      if (window.AK_SYSTEMS && AK_SYSTEMS.register) {
        AK_SYSTEMS.register({ id: "vimmode", init: function () { boot(); } });
      }
    } catch (_e) {}
    // self-init fallback (AK_SYSTEMS absent, or initAll already ran)
    if (hasDOM) {
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
      else boot();
    }
  }
})();
