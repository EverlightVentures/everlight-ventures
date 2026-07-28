/* Alley Kingz -- THE BACKPACK (window.AK_BACKPACK)
 * AK-BACKPACK 2026-07-18
 *
 * OPERATOR SPEC: "I like the backpack system where there's icons of what we have and inventory
 * slots and images for our inventory and different categories. There should be one for during the
 * raid so we can see what we have, and then when we go back to the district there should be a main
 * inventory bag where all of our inventory is. Pokemon did that well, Sunflower Land does that
 * well." Plus, on the district bag: "why not Zelda 3D preview as a hybrid."
 *
 * So this is ONE module with TWO faces, because the two moments want opposite things:
 *
 *   RAID BAG (Tarkov)   fast, tactical, weight-limited. What am I carrying, what is SECURED, how
 *                       close am I to overloaded, and what do I lose if I go down right now. You
 *                       are being shot at. It must read in half a second.
 *
 *   DISTRICT BAG (BOTW) tabbed categories with a live rotating 3D PREVIEW of the selected item.
 *                       This is where you linger and admire what you own. It is also the showroom
 *                       for the whole 3D art pipeline: every rig, weapon and attachment meshed in
 *                       Tripo gets somewhere to be SEEN, which is what makes meshing worth doing.
 *
 * The 3D preview reuses <model-viewer>, already self-hosted at assets/vendor/ and already proven on
 * device by hub3d.js, so the marginal cost is a container plus a registry lookup. Items with no
 * mesh yet fall back to their 2D icon automatically, so the bag is fully usable before any model
 * exists and upgrades itself as meshes land, with no code change.
 *
 * No innerHTML anywhere: nodes are built and cleared through explicit DOM calls only.
 * Headless-safe: no DOM touched at load, everything guarded, and the data layer (items, weight,
 * categories) is pure so it unit-tests and can be reused server-side.
 */
(function (global) {
  'use strict';

  var ICON = 'assets/icons/';
  var MODELS = 'assets/models/';

  // ---- ITEM REGISTRY ------------------------------------------------------
  // cat: which tab it lives under. w: carry weight per unit (raid bag only, currency is weightless).
  // model: optional GLB for the 3D preview -- absent means "icon only, for now".
  var ITEMS = {
    // MATERIALS -- what you harvest and raid for
    wood:      { name: 'Wood',      cat: 'materials', icon: 'chip_wood.png',    w: 1.0, stack: 999, tint: '#b98b4e' },
    stone:     { name: 'Stone',     cat: 'materials', icon: 'chip_stone.png',   w: 1.6, stack: 999, tint: '#9aa3ad' },
    metal:     { name: 'Iron',      cat: 'materials', icon: 'chip_metal.png',   w: 2.2, stack: 999, tint: '#c2ccd6' },
    scrap:     { name: 'Scrap',     cat: 'materials', icon: 'chip_scrap.png',   w: 0.8, stack: 999, tint: '#d08b5b' },
    produce:   { name: 'Produce',   cat: 'materials', icon: 'chip_produce.png', w: 0.5, stack: 999, tint: '#7ee787' },
    // CURRENCY -- weightless, and gold never slows you down
    gold:      { name: 'Gold',      cat: 'currency',  icon: 'chip_gold.png',    w: 0,   stack: 1e9, tint: '#e8c55a' },
    bones:     { name: 'Bones',     cat: 'currency',  icon: 'chip_bones.png',   w: 0,   stack: 1e9, tint: '#e6e0d0' },
    keys:      { name: 'Keys',      cat: 'currency',  icon: 'chip_keys.png',    w: 0,   stack: 999, tint: '#f0c674' },
    fragments: { name: 'Fragments', cat: 'currency',  icon: 'chip_keys.png',    w: 0,   stack: 999, tint: '#b48ead' },
    gems:      { name: 'Gems',      cat: 'currency',  icon: 'chip_gem.png',     w: 0,   stack: 1e9, tint: '#7fd7ff' },
    // GEAR -- tools now; rigs, weapons and attachments land here and THESE get meshes
    tools:     { name: 'Tools',     cat: 'gear',      icon: 'chip_tools.png',   w: 3.0, stack: 99,  tint: '#cbb994' },
    card:      { name: 'Card',      cat: 'cards',     icon: 'chip_paw.png',     w: 0,   stack: 999, tint: '#e8c55a' }
  };

  var CATS = [
    { id: 'materials', label: 'MATERIALS' },
    { id: 'currency',  label: 'CURRENCY'  },
    { id: 'gear',      label: 'GEAR'      },
    { id: 'cards',     label: 'CARDS'     }
  ];

  function def(id) {
    var d = ITEMS[id];
    if (!d) return { name: String(id).toUpperCase(), cat: 'materials', icon: 'chip_paw.png', w: 1, stack: 999, tint: '#cfcfcf' };
    return d;
  }
  function weightOf(id, n) { return def(id).w * (n | 0); }

  // Per-instance icon. A tool slot should show ITS tool, not a generic wrench: the art already
  // exists (tool_axe / tool_pickaxe / tool_crowbar / tool_drill) and was going unused.
  var SUB_ICON = { axe: 'tool_axe.png', pick: 'tool_pickaxe.png', pickaxe: 'tool_pickaxe.png',
                   crowbar: 'tool_crowbar.png', drill: 'tool_drill.png' };
  function iconFor(slot) {
    if (slot && slot.sub && SUB_ICON[String(slot.sub).toLowerCase()]) return SUB_ICON[String(slot.sub).toLowerCase()];
    return def(slot && slot.id).icon;
  }

  // ---- CARRY CAPACITY -----------------------------------------------------
  // The raid bag is weight-limited on purpose: greed costs you speed, and then it costs you the
  // haul. Capacity grows with Town Hall so progression is felt in the bag itself.
  function capacityFor(p) {
    var th = (p && p.townHall) | 0 || 1;
    return 60 + th * 20;                       // TH1 = 80, TH10 = 260
  }
  function bagWeight(bag) {
    var t = 0; try { for (var k in bag) t += weightOf(k, bag[k]); } catch (_e) {}
    return Math.round(t * 10) / 10;
  }
  function overloaded(bag, p) { return bagWeight(bag) > capacityFor(p); }

  // ---- READ THE PLAYER'S STUFF -------------------------------------------
  // Flatten the profile into displayable slots. Scrap is a tiered object, so it fans out per tier.
  function districtSlots(p) {
    var out = [];
    try {
      if (!p) return out;
      var simple = ['wood', 'stone', 'metal', 'produce', 'bones', 'keys', 'fragments'];
      for (var i = 0; i < simple.length; i++) {
        var v = p[simple[i]] | 0; if (v > 0) out.push({ id: simple[i], n: v });
      }
      if ((p.coins | 0) > 0) out.push({ id: 'gold', n: p.coins | 0 });
      if (p.scrap && typeof p.scrap === 'object') {
        for (var t in p.scrap) { var sv = p.scrap[t] | 0; if (sv > 0) out.push({ id: 'scrap', n: sv, sub: t }); }
      }
      if (p.tools && typeof p.tools === 'object') {
        for (var tk in p.tools) out.push({ id: 'tools', n: 1, sub: tk });
      }
      if (p.copies && typeof p.copies === 'object') {
        for (var ck in p.copies) { var cv = p.copies[ck] | 0; if (cv > 0) out.push({ id: 'card', n: cv, sub: ck }); }
      }
    } catch (_e) {}
    return out;
  }
  function slotsByCat(slots, cat) {
    return slots.filter(function (s) { return (s.cat || def(s.id).cat) === cat; });
  }

  // ---- 3D PREVIEW ---------------------------------------------------------
  // Zelda-style: the selected item rotates in 3D. Falls back to the 2D icon when no mesh exists yet,
  // so the bag is useful today and simply gets better as meshes land.
  function previewFor(slot) {
    var d = def(slot && slot.id);
    if (d.model) return { kind: '3d', src: MODELS + d.model };
    return { kind: '2d', src: ICON + d.icon, tint: d.tint };
  }

  // ---- UI -----------------------------------------------------------------
  var el = null, mode = 'district', sel = null;

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  function css() {
    return '#ak-bp{position:fixed;inset:0;z-index:60;background:rgba(6,6,10,.93);display:flex;'
      + 'flex-direction:column;font-family:Inter,system-ui,sans-serif;color:#e8e8e8;}'
      + '#ak-bp .bp-h{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid rgba(232,197,90,.25);}'
      + '#ak-bp .bp-t{font-weight:900;letter-spacing:1px;color:#e8c55a;font-size:15px;}'
      + '#ak-bp .bp-x{margin-left:auto;background:none;border:1px solid rgba(232,197,90,.4);color:#e8c55a;'
      + 'border-radius:8px;padding:6px 12px;font-weight:800;}'
      + '#ak-bp .bp-w{font-size:12px;color:#9aa3ad;}'
      + '#ak-bp .bp-w.over{color:#ff6b6b;font-weight:800;}'
      + '#ak-bp .bp-tabs{display:flex;gap:6px;padding:10px 16px;flex-wrap:wrap;}'
      + '#ak-bp .bp-tab{padding:7px 14px;border-radius:8px;border:1px solid rgba(255,255,255,.12);'
      + 'background:rgba(255,255,255,.04);color:#9aa3ad;font-size:11px;font-weight:800;letter-spacing:.5px;}'
      + '#ak-bp .bp-tab.on{background:#e8c55a;color:#111;border-color:#e8c55a;}'
      + '#ak-bp .bp-body{flex:1;display:flex;gap:14px;padding:0 16px 16px;overflow:hidden;}'
      + '#ak-bp .bp-grid{flex:1;display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));'
      + 'gap:8px;align-content:start;overflow:auto;}'
      + '#ak-bp .bp-slot{aspect-ratio:1;border-radius:10px;border:1px solid rgba(255,255,255,.10);'
      + 'background:rgba(255,255,255,.03);display:flex;flex-direction:column;align-items:center;'
      + 'justify-content:center;gap:3px;position:relative;cursor:pointer;}'
      + '#ak-bp .bp-slot.on{border-color:#e8c55a;background:rgba(232,197,90,.12);}'
      + '#ak-bp .bp-slot.sec{border-color:rgba(126,231,135,.55);}'
      + '#ak-bp .bp-slot img{width:34px;height:34px;object-fit:contain;}'
      + '#ak-bp .bp-n{position:absolute;right:5px;bottom:4px;font-size:10px;font-weight:800;color:#e8e8e8;'
      + 'text-shadow:0 1px 3px #000;}'
      + '#ak-bp .bp-lab{font-size:9px;color:#9aa3ad;text-align:center;line-height:1.1;}'
      + '#ak-bp .bp-prev{width:240px;border-radius:12px;border:1px solid rgba(232,197,90,.22);'
      + 'background:rgba(255,255,255,.03);display:flex;flex-direction:column;align-items:center;'
      + 'justify-content:center;padding:14px;gap:10px;}'
      + '#ak-bp .bp-prev img{width:120px;height:120px;object-fit:contain;}'
      + '#ak-bp .bp-prev model-viewer{width:200px;height:200px;background:transparent;}'
      + '#ak-bp .bp-pn{font-weight:900;color:#e8c55a;font-size:14px;text-align:center;}'
      + '#ak-bp .bp-pd{font-size:11px;color:#9aa3ad;text-align:center;line-height:1.5;}'
      + '@media(max-width:640px){#ak-bp .bp-prev{display:none;}}';
  }

  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'on') { for (var e in attrs[k]) n.addEventListener(e, attrs[k][e]); }
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function renderPreview(box, slot) {
    clear(box);
    if (!slot) { box.appendChild(h('div', { class: 'bp-pd', text: 'Select an item' })); return; }
    var d = def(slot.id), pv = previewFor(slot);
    if (pv.kind === '3d' && global.customElements && customElements.get('model-viewer')) {
      var mv = document.createElement('model-viewer');
      mv.setAttribute('src', pv.src); mv.setAttribute('camera-controls', '');
      mv.setAttribute('auto-rotate', ''); mv.setAttribute('interaction-prompt', 'none');
      mv.setAttribute('shadow-intensity', '0'); mv.setAttribute('exposure', '1.1');
      box.appendChild(mv);
    } else {
      box.appendChild(h('img', { src: ICON + iconFor(slot), alt: d.name }));
    }
    box.appendChild(h('div', { class: 'bp-pn', text: (slot.sub ? slot.sub + ' ' : '') + d.name }));
    box.appendChild(h('div', { class: 'bp-pd',
      text: 'x' + (slot.n | 0) + (d.w ? '   ' + (d.w * (slot.n | 0)).toFixed(1) + ' wt' : '   weightless')
        + (slot.secured ? '   SECURED' : '') }));
  }

  function open(opts) {
    try {
      opts = opts || {};
      mode = opts.mode || (global.RAID ? 'raid' : 'district');
      close();
      var p = null; try { p = (global.AK_ECON && AK_ECON.loadProfile) ? AK_ECON.loadProfile() : null; } catch (_e) {}

      var slots = [], title = 'YOUR STASH', wtxt = '', over = false;
      if (mode === 'raid' && global.RAID) {
        var r = global.RAID, k;
        for (k in (r.bag || {})) { if ((r.bag[k] | 0) > 0) slots.push({ id: k, n: r.bag[k] | 0 }); }
        for (k in (r.secured || {})) { if ((r.secured[k] | 0) > 0) slots.push({ id: k, n: r.secured[k] | 0, secured: true }); }
        var wt = bagWeight(r.bag || {}), cap = capacityFor(p);
        over = wt > cap;
        title = 'RAID BAG';
        wtxt = wt.toFixed(1) + ' / ' + cap + ' wt' + (over ? '   OVERLOADED' : '');
      } else {
        slots = districtSlots(p);
      }

      var grid = h('div', { class: 'bp-grid' });
      var prev = h('div', { class: 'bp-prev' });
      var cat = opts.cat || 'materials';
      var tabs = h('div', { class: 'bp-tabs' });

      function paint() {
        clear(grid);
        var list = (mode === 'raid') ? slots : slotsByCat(slots, cat);
        if (!list.length) { grid.appendChild(h('div', { class: 'bp-pd', text: 'Nothing here yet.' })); return; }
        list.forEach(function (s) {
          var d = def(s.id);
          grid.appendChild(h('div', {
            class: 'bp-slot' + (sel === s ? ' on' : '') + (s.secured ? ' sec' : ''),
            on: { click: function () { sel = s; paint(); renderPreview(prev, s); } }
          }, [
            h('img', { src: ICON + iconFor(s), alt: d.name }),
            h('div', { class: 'bp-lab', text: (s.sub ? s.sub : d.name) }),
            h('div', { class: 'bp-n', text: 'x' + (s.n | 0) })
          ]));
        });
      }

      if (mode !== 'raid') {
        CATS.forEach(function (c) {
          tabs.appendChild(h('button', {
            class: 'bp-tab' + (c.id === cat ? ' on' : ''), text: c.label,
            on: { click: function () {
              cat = c.id; sel = null; renderPreview(prev, null);
              Array.prototype.forEach.call(tabs.children, function (b) {
                b.className = 'bp-tab' + (b.textContent === c.label ? ' on' : '');
              });
              paint();
            } }
          }));
        });
      }

      el = h('div', { id: 'ak-bp' }, [
        h('style', { text: css() }),
        h('div', { class: 'bp-h' }, [
          h('div', { class: 'bp-t', text: title }),
          h('div', { class: 'bp-w' + (over ? ' over' : ''), text: wtxt }),
          h('button', { class: 'bp-x', text: 'CLOSE', on: { click: close } })
        ]),
        tabs,
        h('div', { class: 'bp-body' }, [grid, prev])
      ]);
      paint(); renderPreview(prev, null);
      document.body.appendChild(el);
    } catch (_e) {}
  }

  function close() { try { if (el && el.parentNode) el.parentNode.removeChild(el); } catch (_e) {} el = null; sel = null; }

  // ---- self-mounting touch button ----------------------------------------
  // The operator plays on a phone, so a keyboard-only bag is no bag at all. Mounts itself the same
  // way buildmode.js does, so index.html needs no layout change. Badge turns red when the raid bag
  // is overloaded, which is the one state you must notice without opening anything.
  var btn = null;
  function mountButton() {
    try {
      if (btn || typeof document === 'undefined' || !document.body) return;
      btn = document.createElement('button');
      btn.id = 'ak-bp-btn';
      var bi = document.createElement('img');
      bi.src = ICON + 'loot_bag.png'; bi.alt = 'BAG';
      bi.style.cssText = 'width:26px;height:26px;object-fit:contain;pointer-events:none;';
      btn.appendChild(bi);
      btn.style.cssText = 'position:fixed;right:10px;top:288px;width:44px;height:44px;z-index:22;'
        + 'border-radius:12px;border:1px solid rgba(232,197,90,.45);background:rgba(12,12,18,.82);'
        + 'color:#e8c55a;font:800 10px Inter,system-ui;letter-spacing:.5px;';
      btn.addEventListener('click', function () {
        open({ mode: (global.RAID && !global.RAID.over) ? 'raid' : 'district' });
      });
      document.body.appendChild(btn);
    } catch (_e) {}
  }
  function refreshButton() {
    try {
      if (!btn) return;
      var r = global.RAID;
      if (r && !r.over) {
        var p = null; try { p = (global.AK_ECON && AK_ECON.loadProfile) ? AK_ECON.loadProfile() : null; } catch (_e2) {}
        var ov = overloaded(r.bag || {}, p);
        btn.style.borderColor = ov ? 'rgba(255,107,107,.85)' : 'rgba(232,197,90,.45)';
        btn.style.color = ov ? '#ff6b6b' : '#e8c55a';
        btn.style.background = ov ? 'rgba(60,12,12,.88)' : 'rgba(12,12,18,.82)';
      } else {
        btn.style.borderColor = 'rgba(232,197,90,.45)'; btn.style.background = 'rgba(12,12,18,.82)';
      }
    } catch (_e) {}
  }

  var _rt = 0;
  var api = {
    id: 'backpack',
    init: function () { mountButton(); },
    onTick: function (dt) { _rt += (dt || 0); if (_rt > 0.5) { _rt = 0; refreshButton(); } },
    onDrawWorld: function () {}
  };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_BACKPACK = {
    open: open, close: close,
    ITEMS: ITEMS, CATS: CATS, def: def,
    weightOf: weightOf, bagWeight: bagWeight, capacityFor: capacityFor, overloaded: overloaded,
    districtSlots: districtSlots, slotsByCat: slotsByCat, previewFor: previewFor
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_BACKPACK;
})(typeof window !== 'undefined' ? window : this);
