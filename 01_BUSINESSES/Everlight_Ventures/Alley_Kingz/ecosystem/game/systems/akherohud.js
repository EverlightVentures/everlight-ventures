/* ALLEY KINGZ -- AK_HEROHUD: see your hero + switch it from the HUD.  AK-HEROHUD 2026-07-28.
 *
 * OPERATOR: "i should see bacardi or balboa or whoever my hero is and i should be able to easily
 * change my hero from the HUD."
 *
 * WHAT THIS IS
 * A small HUD chip that shows WHICH hero you are and swaps it on tap. It drives the SAME hero system
 * everything else already reads -- hub3d.js resolves the live 3D hero from window.AK_HERO (then
 * heroCard()), so setting AK_HERO here changes the hero in the hub, the gulag opponent-pick, and the
 * per-clip action buttons all at once. No parallel state.
 *
 * WHY A CHIP, NOT A PORTRAIT
 * The roster art in assets/handlers/ is keyed by CLASS (mender/shadow/rigger...), not by the three
 * playable rigs (bcardd/balboa/jagged), so a portrait would mislabel. A name chip + per-hero accent
 * dot is unambiguous and needs no new art. "The Dealer" IS $BCARDD in canon, so it reads right.
 *
 * PERSISTENCE
 * The choice is stored in localStorage('ak_hero_sel') and re-applied to window.AK_HERO on load, so a
 * switch survives a reload / a trip into the gulag. Live swap uses __hero3d.setModel(url) when the
 * hub avatar is mounted, so the change is instant, not next-load.
 */
window.AK_HEROHUD = (function (root) {
  'use strict';

  // The switchable roster + how each reads. Mirrors hub3d.js HERO_MODELS; slug must match heroSlug().
  var ROSTER = [
    { slug: 'bcardd',     label: '$BCARDD',   url: 'assets/models/bcardd.glb',     dot: '#e8c55a' },
    { slug: 'balboa',     label: 'BALBOA',    url: 'assets/models/balboa.glb',     dot: '#ff7a4d' },
    { slug: 'jagged',     label: 'JAGGED',    url: 'assets/models/jagged.glb',     dot: '#7fc8ff' },
    // AK-3DALL 2026-07-28: three new breed heroes (Iron Rottweiler 0004, Grit Bulldog 0006, Blackout Malamute 0127).
    { slug: 'rottweiler', label: 'IRON ROTT', url: 'assets/models/rottweiler.glb', dot: '#c0563a' },
    { slug: 'bulldog',    label: 'GRIT BULL', url: 'assets/models/bulldog.glb',    dot: '#c9a24b' },
    { slug: 'malamute',   label: 'BLACKOUT',  url: 'assets/models/malamute.glb',   dot: '#8fa9c4' }
  ];
  var KEY = 'ak_hero_sel';
  var el = null, dotEl = null, nameEl = null, _lastVis = null;

  function idxOfCurrent() {
    var cur = String(root.AK_HERO || '').toLowerCase();
    for (var i = 0; i < ROSTER.length; i++) if (cur.indexOf(ROSTER[i].slug) !== -1) return i;
    return 0;
  }

  // Re-apply a saved choice on load, BEFORE hub3d resolves its model, so the right hero boots.
  (function restore() {
    try { var v = root.localStorage && localStorage.getItem(KEY); if (v && !root.AK_HERO) root.AK_HERO = v; } catch (_e) {}
  })();

  function render() {
    if (!el) return;
    var h = ROSTER[idxOfCurrent()];
    if (nameEl) nameEl.textContent = h.label;
    if (dotEl) dotEl.style.background = h.dot;
  }

  function apply(slug, url) {
    root.AK_HERO = slug;
    try { localStorage.setItem(KEY, slug); } catch (_e) {}
    // live swap of the hub avatar if it is mounted (hub3d owns the model-viewer)
    try { if (root.__hero3d && root.__hero3d.setModel) root.__hero3d.setModel(url); } catch (_e2) {}
    render();
    try { if (navigator.vibrate) navigator.vibrate(12); } catch (_e3) {}
  }

  function cycle() {
    var next = ROSTER[(idxOfCurrent() + 1) % ROSTER.length];
    apply(next.slug, next.url);
  }

  function mount() {
    if (el || typeof document === 'undefined') return;
    el = document.createElement('button');
    el.id = 'ak-herohud';
    el.type = 'button';
    el.style.cssText = 'position:fixed;left:16px;bottom:140px;z-index:6;display:none;align-items:center;gap:8px;' +
      'background:radial-gradient(circle at 30% 30%,rgba(30,26,18,.95),rgba(12,10,14,.96));' +
      'border:1.5px solid rgba(201,168,76,.5);border-radius:999px;padding:7px 13px 7px 9px;' +
      'font:800 12px Inter,system-ui;color:#e8c55a;letter-spacing:.04em;box-shadow:0 4px 12px rgba(0,0,0,.5);' +
      'touch-action:manipulation;cursor:pointer;';
    dotEl = document.createElement('span');
    dotEl.style.cssText = 'width:11px;height:11px;border-radius:50%;flex:0 0 auto;box-shadow:0 0 8px currentColor;';
    nameEl = document.createElement('span');
    var swap = document.createElement('span');
    swap.textContent = '⇄';   // ⇄ switch glyph
    swap.style.cssText = 'font-size:14px;color:#9a8f6a;margin-left:2px;';
    el.appendChild(dotEl); el.appendChild(nameEl); el.appendChild(swap);
    el.addEventListener('click', function (e) { e.preventDefault(); cycle(); });
    document.body.appendChild(el);
    render();
  }

  // Show only where choosing a hero makes sense: walking a district, in a raid, or in the gulag.
  function visibleNow(ctx) {
    try {
      var st = (ctx && ctx.state) || root.state;
      var gulag = !!(root.AK_MODES && root.AK_MODES.current && /gulag/i.test(root.AK_MODES.current() || '')) ||
                  /gulag/i.test((typeof document !== 'undefined' && document.body.innerText || '').slice(0, 200));
      var interior = !!root.interiorOpen;
      return (st === 'IN_ZONE' || st === 'RAID' || gulag) && !interior;
    } catch (_e) { return false; }
  }

  var api = {
    id: 'akherohud',
    onTick: function (dt, ctx) {
      if (!el) mount();
      if (!el) return;
      var v = visibleNow(ctx);
      if (v !== _lastVis) { el.style.display = v ? 'flex' : 'none'; _lastVis = v; }
      // keep the label in sync if the hero changed elsewhere (runner picker)
      if (v) render();
    }
  };
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);

  return { cycle: cycle, apply: apply, roster: ROSTER, current: function () { return ROSTER[idxOfCurrent()]; }, mount: mount };
})(window);
