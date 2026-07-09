#!/usr/bin/env node
/* AK ASSET AUDIT -- bible Section 12.3: "never render blind, never re-render what exists".
   Loads canon.js + classes.js headlessly (window shim), walks all 106 cards, checks disk
   for every Section 12 visual phase, and writes ecosystem/AK_ASSET_GAP.md (the AUDIT
   MANIFEST every art batch starts from). Read-only on assets; regenerate any time.
   Run: node tools/asset_audit.js   (from ecosystem/ -- path-safe from anywhere)
   NO em-dashes anywhere in this file (hook law); use -- instead. */
'use strict';

var fs = require('fs');
var path = require('path');

// ---- headless shim: canon.js + classes.js are browser-first, window-guarded
global.window = global;
var GAME = path.join(__dirname, '..', 'game');
require(path.join(GAME, 'canon.js'));
require(path.join(GAME, 'classes.js'));

var CARDS = global.CANON_CARDS || [];
var CLS_GET = global.AK_CLASS_GET || function () { return null; };
if (!CARDS.length) { console.error('FATAL: canon.js loaded 0 cards'); process.exit(1); }

// ---- disk snapshot (one readdir per asset dir, then pure lookups)
function listDir(rel) {
  try { return fs.readdirSync(path.join(GAME, 'assets', rel)); } catch (_e) { return []; }
}
var CARDS_DIR = listDir('cards');
var PORTRAITS_DIR = listDir('portraits');
var CARDFX_DIR = listDir('cardfx');
var STORY_DIR = listDir('story');
var fxSet = {};
CARDFX_DIR.forEach(function (f) { fxSet[f] = 1; });
var portraitSet = {};
PORTRAITS_DIR.forEach(function (f) { portraitSet[f] = 1; });

// ---- per-phase checks (Section 12.1 path law + fallback chain law)
function hasCardArt(num) {
  // assets/cards/<NNNN>_*.webp|png (the stat card; resolver slug varies, prefix match)
  for (var i = 0; i < CARDS_DIR.length; i++) {
    var f = CARDS_DIR[i];
    if (f.indexOf(num + '_') === 0 && (/\.webp$/.test(f) || /\.png$/.test(f))) return true;
  }
  return false;
}
function storyPanels(num) {
  // assets/story/<NNNN>_*.jpg
  var n = 0;
  STORY_DIR.forEach(function (f) { if (f.indexOf(num + '_') === 0 && /\.jpg$/.test(f)) n++; });
  return n;
}
function clsSlug(num) {
  // resolve the dog's combat class the way classes.js maps it (AK_CLASS_GET)
  var rec = CLS_GET(num);
  return (rec && rec.cls) ? String(rec.cls).toLowerCase() : null;
}
// motion phase check: per-dog clip -> class fallback -> MISS (fallback chain law)
function motionPhase(num, cls, suffix) {
  if (fxSet[num + '_' + suffix + '.mp4']) return 'OK';
  if (cls && fxSet['class_' + cls + '_' + suffix + '.mp4']) return 'CLS';
  return 'MISS';
}

// ---- walk every card
var PHASES = ['CARD', 'PORTRAIT', 'WALK', 'IDLE', 'ACTION', 'HIT', 'VICTORY', 'STORY'];
var rows = [];
CARDS.forEach(function (c) {
  var num = c.cardNumber;
  var cls = clsSlug(num);
  var isStructure = (cls === 'structure');
  var engage = motionPhase(num, cls, 'engage');
  var vsStruct = motionPhase(num, cls, 'vs_structure');
  // ACTION = engage + vs_structure together: OK only if both per-dog, CLS if both covered
  var action = (engage === 'MISS' || vsStruct === 'MISS') ? 'MISS'
             : (engage === 'OK' && vsStruct === 'OK') ? 'OK' : 'CLS';
  var panels = storyPanels(num);
  rows.push({
    num: num, name: c.name, rarity: c.rarity, cls: cls,
    CARD: hasCardArt(num) ? 'OK' : 'MISS',
    PORTRAIT: portraitSet[num + '.jpg'] ? 'OK' : 'MISS',
    // structures are planted static (canon): district walk does not apply
    WALK: isStructure ? 'n/a' : motionPhase(num, cls, 'walk'),
    IDLE: motionPhase(num, cls, 'idle'),
    ACTION: action,
    HIT: (cls && fxSet['class_' + cls + '_hit.mp4']) ? 'CLS' : 'MISS',
    VICTORY: fxSet[num + '_victory.mp4'] ? 'OK' : 'MISS',   // none expected yet (phase 7 gap)
    STORY: panels > 0 ? 'OK' : 'MISS', storyCount: panels
  });
});

// ---- summary counts per phase
function tally(phase) {
  var t = { OK: 0, CLS: 0, MISS: 0, na: 0 };
  rows.forEach(function (r) {
    var v = r[phase];
    if (v === 'n/a') t.na++; else t[v]++;
  });
  t.applicable = rows.length - t.na;
  t.covered = t.OK + t.CLS;
  t.pct = t.applicable ? Math.round(t.covered / t.applicable * 1000) / 10 : 0;
  t.pctOwn = t.applicable ? Math.round(t.OK / t.applicable * 1000) / 10 : 0;
  return t;
}
var summary = {};
PHASES.forEach(function (p) { summary[p] = tally(p); });

var flagships = rows.filter(function (r) { return r.rarity === 'Mythic' || r.rarity === 'Legendary'; });

// ---- class hit / idle / walk gaps at the class level (one clip covers many dogs)
var classes = {};
rows.forEach(function (r) { if (r.cls) classes[r.cls] = (classes[r.cls] || 0) + 1; });
var classList = Object.keys(classes).sort();

// ---- RENDER QUEUE (bible 12.3 priority: portraits -> per-winner victory ->
//      class hit -> walk/idle coverage -> per-dog actions, flagships then factions)
var q = [];
function push(section, items) { if (items.length) q.push({ section: section, items: items }); }

var flagNums = {};
flagships.forEach(function (r) { flagNums[r.num] = 1; });
var portFlag = flagships.filter(function (r) { return r.PORTRAIT === 'MISS'; })
  .map(function (r) { return 'assets/portraits/' + r.num + '.jpg   (' + r.name + ', ' + r.rarity + ')'; });
push('1. PORTRAITS -- flagship wave (Mythic/Legendary, highest impact: the picker)', portFlag);

// faction waves: group remaining missing portraits by faction, canon faction order
var factionOrder = (global.CANON_META && global.CANON_META.factions) || [];
var byCard = {};
CARDS.forEach(function (c) { byCard[c.cardNumber] = c; });
factionOrder.forEach(function (fac) {
  var wave = rows.filter(function (r) {
    return !flagNums[r.num] && r.PORTRAIT === 'MISS' && byCard[r.num]['class'] === fac;
  }).map(function (r) { return 'assets/portraits/' + r.num + '.jpg   (' + r.name + ')'; });
  push('2. PORTRAITS -- faction wave: ' + fac, wave);
});

push('3. VICTORY -- per-winner clips, flagships first (phase 7: win.mp4 is always $BCARDD today)',
  flagships.filter(function (r) { return r.VICTORY === 'MISS'; })
    .map(function (r) { return 'assets/cardfx/' + r.num + '_victory.mp4   (' + r.name + ')'; }));

push('4. CLASS HIT -- one clip covers every dog of the class (phase 6)',
  classList.filter(function (cls) { return !fxSet['class_' + cls + '_hit.mp4']; })
    .map(function (cls) { return 'assets/cardfx/class_' + cls + '_hit.mp4   (covers ' + classes[cls] + ' dogs)'; }));

var walkIdle = [];
classList.forEach(function (cls) {
  if (cls !== 'structure' && !fxSet['class_' + cls + '_walk.mp4'])
    walkIdle.push('assets/cardfx/class_' + cls + '_walk.mp4   (covers ' + classes[cls] + ' dogs)');
});
classList.forEach(function (cls) {
  if (!fxSet['class_' + cls + '_idle.mp4'])
    walkIdle.push('assets/cardfx/class_' + cls + '_idle.mp4   (covers ' + classes[cls] + ' dogs)');
});
push('5. WALK/IDLE coverage -- class-level clips (phases 3-4 fallback tier)', walkIdle);

// class-level action gaps (a missing class engage/vs_structure clip strands every dog of the class)
var actGaps = [];
classList.forEach(function (cls) {
  if (!fxSet['class_' + cls + '_engage.mp4'])
    actGaps.push('assets/cardfx/class_' + cls + '_engage.mp4   (covers ' + classes[cls] + ' dogs)');
  if (!fxSet['class_' + cls + '_vs_structure.mp4'])
    actGaps.push('assets/cardfx/class_' + cls + '_vs_structure.mp4   (covers ' + classes[cls] + ' dogs)');
});
push('5b. ACTION coverage -- class-level gaps (phase 5 fallback tier; these strand whole classes)', actGaps);

push('6. PER-DOG ACTIONS -- flagships first (phase 5 signature moves; 0001 already has both)',
  flagships.reduce(function (acc, r) {
    if (!fxSet[r.num + '_engage.mp4']) acc.push('assets/cardfx/' + r.num + '_engage.mp4   (' + r.name + ')');
    if (!fxSet[r.num + '_vs_structure.mp4']) acc.push('assets/cardfx/' + r.num + '_vs_structure.mp4   (' + r.name + ')');
    return acc;
  }, []));

// ---- write AK_ASSET_GAP.md
var L = [];
L.push('# AK ASSET GAP -- the audit manifest (bible 12.3: never render blind)');
L.push('');
L.push('Generated by `tools/asset_audit.js` on ' + new Date().toISOString().slice(0, 10) +
  ' against ' + rows.length + ' canon cards. Regenerate before every art batch.');
L.push('Legend: OK = per-dog asset on disk. CLS = covered by the class fallback clip (fallback chain law).');
L.push('MISS = nothing on disk, engine falls to graceful static. n/a = phase does not apply (planted structures do not walk).');
L.push('');
L.push('## Summary -- per-phase coverage (' + rows.length + ' dogs)');
L.push('');
L.push('| Phase | Per-dog | Class fallback | Missing | n/a | Covered | Per-dog % |');
L.push('|---|---|---|---|---|---|---|');
PHASES.forEach(function (p) {
  var t = summary[p];
  L.push('| ' + p + ' | ' + t.OK + ' | ' + t.CLS + ' | ' + t.MISS + ' | ' + t.na +
    ' | ' + t.covered + '/' + t.applicable + ' (' + t.pct + '%) | ' + t.pctOwn + '% |');
});
L.push('');
L.push('## Flagship gap matrix -- the 14 Mythic/Legendary (full detail)');
L.push('');
L.push('| # | Name | Rarity | Class | CARD | PORTRAIT | WALK | IDLE | ACTION | HIT | VICTORY | STORY |');
L.push('|---|---|---|---|---|---|---|---|---|---|---|---|');
flagships.forEach(function (r) {
  L.push('| ' + r.num + ' | ' + r.name + ' | ' + r.rarity + ' | ' + (r.cls || '?') + ' | ' +
    r.CARD + ' | ' + r.PORTRAIT + ' | ' + r.WALK + ' | ' + r.IDLE + ' | ' + r.ACTION + ' | ' +
    r.HIT + ' | ' + r.VICTORY + ' | ' + (r.storyCount > 0 ? r.storyCount + ' panels' : 'MISS') + ' |');
});
L.push('');
L.push('## RENDER QUEUE -- next batches in bible 12.3 priority order');
L.push('');
q.forEach(function (sec) {
  L.push('### ' + sec.section + '  [' + sec.items.length + ' files]');
  L.push('');
  sec.items.forEach(function (it) { L.push('- `' + it + '`'); });
  L.push('');
});
L.push('---');
L.push('Chain of command for the renders (bible 12.4): CF flux free window = portrait/panel batches;');
L.push('Higgsfield = flagship pieces + motion clips. PIL verify + visual spot-check before ship.');
L.push('');

var OUT = path.join(__dirname, '..', 'AK_ASSET_GAP.md');
fs.writeFileSync(OUT, L.join('\n'));

// ---- console totals
console.log('AK ASSET AUDIT -- ' + rows.length + ' cards walked');
PHASES.forEach(function (p) {
  var t = summary[p];
  console.log('  ' + p.padEnd(9) + ' per-dog ' + String(t.OK).padStart(3) +
    '  class-fb ' + String(t.CLS).padStart(3) + '  missing ' + String(t.MISS).padStart(3) +
    (t.na ? '  n/a ' + t.na : '') + '  covered ' + t.pct + '%');
});
var queued = q.reduce(function (n, s) { return n + s.items.length; }, 0);
console.log('RENDER QUEUE: ' + queued + ' files across ' + q.length + ' batches');
console.log('Wrote ' + OUT);
