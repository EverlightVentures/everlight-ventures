/* ==========================================================================
   ALLEY KINGZ -- AGE GATE (compliance, in-world framed)  window.AK_AGEGATE
   --------------------------------------------------------------------------
   A first-run age gate, framed as the OLD PACK (the dead-legend ancestor
   narrator) sizing up a stranger before the block lets them run:
   "How long you been on these streets?"  The answer records an age BRACKET
   on the profile (p.ageBracket, falsy-default) and, for the under-16 class,
   raises a privacy-safe flag (p.noTargeting) the rest of the game can read --
   so ad / recommendation / LiveOps surfaces know to run DARK on a minor.
   Standard CCPA-style opt-out posture (we never sell info; under-16 gets no
   behavioral targeting). NOT privacy tokens -- legally murky, skipped per the
   roadmap compliance note (AK_ROADMAP_V2_NAMED sec 1).

   SKIPPABLE-ONCE-ANSWERED: the gate shows on first run only. Once a bracket is
   recorded, maybeShow() is a permanent no-op -- it never interrupts play again.

   CONTRACT (MODULE_CONTRACT-style):
   - NEW file. Edits NO shared file. engine.js stays FROZEN. The integration
     pass wires this in by calling window.AK_AGEGATE.maybeShow() once at boot
     (BEFORE the first playable frame). This file does NOT auto-show, so it can
     never double-fire or interrupt a frame the player already initiated.
   - ALL player state via window.AK_ECON behind falsy-default fields ONLY:
       p.ageBracket  ''     (absent until answered -- zero-state byte-identical)
       p.noTargeting (unset / true)   under-16 privacy flag (absent => targeting
                                       unrestricted; only ever SET true)
     Neither key is added to ensureShape, so a fresh profile is byte-identical
     until the player answers.
   - 60fps cheap-Android: LAZY DOM (nothing built until show()), no RAF loop, no
     timers, no top-level DOM / localStorage. One static modal, CSS fade only.
   - Gritty gangland voice. Everlight gold-cyberpunk palette. No em-dashes (--).
   ========================================================================== */
(function (global) {
  "use strict";

  /* ---- palette (Everlight gold cyberpunk -- mirrors social/karma) -------- */
  var GOLD = "#c9a84c", GOLD_HI = "#e8c55a", INK = "#06060a", TXT = "#ece7da", DIM = "#9a8f6a";

  /* ======================================================================== *
   * THE BRACKETS -- CCPA age tiers, framed in-world.
   *   minor:true  == under 16  -> the privacy-protected class (no targeting).
   *   coppa:true  == under 13  -> COPPA territory (parental-consent class).
   * `street` is the gritty label the pup taps; `age` is the unambiguous range
   * the compliance answer actually records.
   * ======================================================================== */
  var BRACKETS = [
    { id: "u13",   street: "Fresh off the leash",     age: "Under 13",  minor: true,  coppa: true  },
    { id: "13_15", street: "Still cutting my teeth",  age: "13 to 15",  minor: true,  coppa: false },
    { id: "16_17", street: "Run these blocks a while",age: "16 or 17",  minor: false, coppa: false },
    { id: "18up",  street: "Grown dog, seen it all",  age: "18 and up", minor: false, coppa: false }
  ];
  function bracketDef(id) { for (var i = 0; i < BRACKETS.length; i++) if (BRACKETS[i].id === id) return BRACKETS[i]; return null; }

  /* ---- economy bridge (falsy-safe; headless-safe) ------------------------ */
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function profile() { try { var e = econ(); return e && e.loadProfile ? e.loadProfile() : null; } catch (_) { return null; } }

  /* current recorded bracket id ('' = unanswered). falsy-default read. */
  function bracket() { var p = profile(); return (p && p.ageBracket) || ""; }
  function answered() { return !!bracket(); }
  /* under-16 privacy class: derive from the recorded bracket, honor the stored
     flag too. Other systems may read p.noTargeting directly (cheaper). */
  function noTargeting() {
    var p = profile();
    if (p && p.noTargeting) return true;
    var d = bracketDef((p && p.ageBracket) || "");
    return !!(d && d.minor);
  }
  function isMinor() { return noTargeting(); }

  /* persist the answer in ONE atomic mutateProfile (doctrine path). Sets the
     under-16 privacy flag ONLY when minor (stays falsy-default otherwise so an
     adult's profile never carries the key -- zero-state discipline). */
  function record(id) {
    var d = bracketDef(id); if (!d) return false;
    var e = econ(); if (!e || !e.mutateProfile) return false;
    e.mutateProfile(function (p) {
      p.ageBracket = d.id;                 // falsy-default '' until set
      if (d.minor) p.noTargeting = true;   // under-16 -> run dark (CCPA, no behavioral targeting)
    });
    return true;
  }

  /* ======================================================================== *
   * LAZY DOM -- nothing below runs until show() is called.
   * ======================================================================== */
  var ID = "ak-agegate", CSS_ID = "ak-agegate-css", openRoot = null, pending = null;

  function mk(tag, attrs, kids) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
      var v = attrs[k]; if (v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;          // dynamic text via textContent (XSS-safe)
      else if (k.slice(0, 2) === "on" && typeof v === "function") el[k] = v;
      else el.setAttribute(k, v);
    }
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return el;
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var st = document.createElement("style"); st.id = CSS_ID;
    st.textContent = [
      "#" + ID + "{position:fixed;inset:0;z-index:2147483646;display:flex;align-items:center;justify-content:center;",
        "background:radial-gradient(circle at 50% 38%,rgba(20,18,12,.97),rgba(6,6,10,.99));",
        "font-family:'Inter',system-ui,sans-serif;color:" + TXT + ";padding:22px;box-sizing:border-box;",
        "opacity:0;transition:opacity .22s ease}",
      "#" + ID + ".on{opacity:1}",
      "#" + ID + " .akag-card{width:100%;max-width:430px;background:linear-gradient(180deg,rgba(18,18,26,.96),rgba(8,8,12,.98));",
        "border:1px solid rgba(201,168,76,.32);border-radius:16px;padding:22px 20px 18px;",
        "box-shadow:0 16px 48px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.05)}",
      "#" + ID + " .akag-eye{font:700 10px/1 'Inter',system-ui;letter-spacing:2px;text-transform:uppercase;color:" + DIM + ";text-align:center}",
      "#" + ID + " .akag-h{margin:8px 0 4px;font-family:'Cinzel','Playfair Display',serif;font-weight:800;",
        "font-size:21px;line-height:1.18;text-align:center;",
        "background:linear-gradient(90deg," + GOLD + "," + GOLD_HI + ");-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:" + GOLD_HI + "}",
      "#" + ID + " .akag-sub{margin:0 0 16px;font-size:12.5px;line-height:1.5;text-align:center;color:#cdbf95}",
      "#" + ID + " .akag-opts{display:flex;flex-direction:column;gap:9px}",
      "#" + ID + " .akag-opt{display:flex;align-items:center;justify-content:space-between;gap:10px;width:100%;box-sizing:border-box;",
        "background:rgba(255,255,255,.04);border:1px solid rgba(201,168,76,.26);border-left:3px solid " + GOLD + ";",
        "border-radius:11px;padding:12px 14px;color:" + TXT + ";font:inherit;text-align:left;cursor:pointer;",
        "transition:background .14s,border-color .14s,transform .08s}",
      "#" + ID + " .akag-opt:active{transform:scale(.985)}",
      "#" + ID + " .akag-opt:hover{background:rgba(201,168,76,.12);border-color:rgba(232,197,90,.55)}",
      "#" + ID + " .akag-st{font-weight:800;font-size:14px;color:#fff}",
      "#" + ID + " .akag-age{flex:0 0 auto;font-weight:800;font-size:12px;letter-spacing:.4px;color:" + GOLD_HI + ";",
        "background:rgba(201,168,76,.14);border:1px solid rgba(201,168,76,.34);border-radius:999px;padding:3px 10px}",
      "#" + ID + " .akag-foot{margin:16px 2px 0;font-size:10.5px;line-height:1.5;color:" + DIM + ";text-align:center}",
      "@media (prefers-reduced-motion:reduce){#" + ID + "{transition:none}#" + ID + " .akag-opt{transition:none}}"
    ].join("");
    document.head.appendChild(st);
  }

  /* settle the pending promise + fire a host hook + DOM event, then tear down. */
  function finish(id) {
    record(id);
    var d = bracketDef(id);
    teardown();
    var detail = d ? { bracket: d.id, age: d.age, minor: d.minor, coppa: d.coppa, noTargeting: !!d.minor } : { bracket: "", minor: false, noTargeting: false };
    try { if (typeof global.AK_AGEGATE_ONDONE === "function") global.AK_AGEGATE_ONDONE(detail); } catch (_) {}
    try { if (typeof document !== "undefined" && document.dispatchEvent) document.dispatchEvent(new CustomEvent("ak:agegate", { detail: detail })); } catch (_) {}
    if (pending) { var res = pending.resolve; pending = null; try { res(detail); } catch (_) {} }
  }

  function teardown() {
    if (openRoot && openRoot.parentNode) openRoot.parentNode.removeChild(openRoot);
    openRoot = null;
  }

  /* build + mount the modal (lazy). No animation loop -- a single CSS fade. */
  function build() {
    injectCss();
    var opts = mk("div", { class: "akag-opts" }, BRACKETS.map(function (b) {
      return mk("button", { class: "akag-opt", type: "button", "aria-label": b.street + ", " + b.age,
        onclick: function () { finish(b.id); } },
        [ mk("span", { class: "akag-st", text: b.street }), mk("span", { class: "akag-age", text: b.age }) ]);
    }));
    var card = mk("div", { class: "akag-card", role: "dialog", "aria-modal": "true", "aria-label": "Age check" }, [
      mk("div", { class: "akag-eye", text: "THE OLD PACK SIZES YOU UP" }),
      mk("h2",  { class: "akag-h",   text: "HOW LONG YOU BEEN ON THESE STREETS?" }),
      mk("p",   { class: "akag-sub", text: "The block don't let strangers run, pup. Speak true -- how many winters you got?" }),
      opts,
      mk("p", { class: "akag-foot", text: "Straight talk: we never sell your info. Run under 16 and the block keeps it dark -- no behavioral targeting. (CCPA)" })
    ]);
    var root = mk("div", { id: ID }, card);
    document.body.appendChild(root);
    openRoot = root;
    // next frame -> add .on so the CSS fade actually transitions (cheap, one rAF)
    try { (global.requestAnimationFrame || function (f) { f(); })(function () { if (openRoot) openRoot.classList.add("on"); }); }
    catch (_) { root.classList.add("on"); }
    return root;
  }

  /* ======================================================================== *
   * PUBLIC API -- the integration pass wires AK_AGEGATE.maybeShow() at boot.
   * ======================================================================== */

  // Force the gate open (ignores the answered check). Returns a Promise that
  // resolves with the chosen bracket detail. Idempotent while open.
  function show() {
    if (typeof document === "undefined" || !document.body) return Promise.resolve({ bracket: bracket(), minor: isMinor(), noTargeting: noTargeting() });
    if (openRoot) { return pending ? pending.promise : Promise.resolve(null); }
    var p = {}; p.promise = new Promise(function (res) { p.resolve = res; }); pending = p;
    build();
    return p.promise;
  }

  // First-run entry: show ONLY if not yet answered. Once answered it is a
  // permanent no-op (skippable-once-answered) and resolves immediately with the
  // already-recorded bracket -- so the boot flow can always await it safely.
  function maybeShow() {
    if (answered()) return Promise.resolve({ bracket: bracket(), minor: isMinor(), noTargeting: noTargeting(), already: true });
    return show();
  }

  global.AK_AGEGATE = {
    BRACKETS: BRACKETS,
    bracketDef: bracketDef,
    maybeShow: maybeShow,     // <-- the boot seam: call once before first playable frame
    show: show,               // force-open (e.g. a future Settings "re-check age")
    answered: answered,
    bracket: bracket,         // '' until answered (falsy-default)
    isMinor: isMinor,         // under-16 privacy class
    noTargeting: noTargeting, // CCPA flag the rest of the game reads (mirrors p.noTargeting)
    record: record           // headless / Settings: persist a bracket without the modal
  };

})(typeof window !== "undefined" ? window : globalThis);
