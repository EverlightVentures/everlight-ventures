// AK CARD-ART CONSOLIDATOR -- one folder, one naming, art follows the card.
// Canonical scheme: assets/cards/<NNNN>_<name-slug>.png  (number = stable unique key, slug = matches the card NAME).
// For each card, find its existing valid art (units/ original OR cards/ variant, any current naming) and COPY it to the
// canonical name -- the custom art stays mapped to its card; only the filename changes. Spells/specials/ui untouched here.
// DRY-RUN by default (reports the plan). Pass --apply to perform the copies. Pass --prune to also remove the OLD files after.
global.window = global;
const fs = require('fs'), path = require('path');
const GAME = path.resolve(__dirname, '..', 'game');
require(path.join(GAME, 'canon.js'));
const C = global.CANON_CARDS;
const slug = n => String(n || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
const valid = f => { try { return fs.statSync(f).size > 20000; } catch (_) { return false; } };

function canonicalRel(c) { return 'assets/cards/' + String(c.cardNumber).padStart(4, '0') + '_' + slug(c.name) + '.png'; }
function findSource(c) {
  const num = String(c.cardNumber).padStart(4, '0'), s = slug(c.name), h = s.replace(/_/g, '-');
  // every historical naming we've ever used, newest-canonical first
  const cands = [`assets/cards/${num}_${s}.png`, `assets/units/${num}_${s}.png`, `assets/cards/${h}.png`,
                 `assets/cards/${s}.png`, `assets/units/${num}_${h}.png`];
  for (const cd of cands) if (valid(path.join(GAME, cd))) return cd;
  return null;
}

const APPLY = process.argv.includes('--apply'), PRUNE = process.argv.includes('--prune');
const arr = Array.isArray(C) ? C : Object.values(C || {});
const seenCanon = {}; let mapped = 0, copied = 0, already = 0; const missing = [], collisions = [], moves = [];
arr.forEach(c => {
  if (!c || c.type === 'spell') return;
  const canon = canonicalRel(c), src = findSource(c);
  if (seenCanon[canon]) collisions.push(canon + ' <- ' + c.cardNumber + ' ' + c.name); seenCanon[canon] = true;
  if (!src) { missing.push(c.cardNumber + ' ' + c.name + ' (slug ' + slug(c.name) + ')'); return; }
  mapped++;
  if (src === canon) { already++; return; }
  moves.push([src, canon]);
  if (APPLY) {
    fs.copyFileSync(path.join(GAME, src), path.join(GAME, canon));
    if (PRUNE && src !== canon) try { fs.unlinkSync(path.join(GAME, src)); } catch (_) {}
    copied++;
  }
});
console.log((APPLY ? 'APPLIED' : 'DRY-RUN') + ': cards=' + arr.filter(c => c && c.type !== 'spell').length +
  ' mapped=' + mapped + ' already-canonical=' + already + ' to-copy=' + moves.length +
  ' copied=' + copied + ' MISSING=' + missing.length + ' collisions=' + collisions.length);
if (missing.length) console.log('MISSING (no valid source art):\n  ' + missing.join('\n  '));
if (collisions.length) console.log('COLLISIONS (two cards -> same canonical):\n  ' + collisions.join('\n  '));
console.log('sample moves:'); moves.slice(0, 12).forEach(m => console.log('  ' + m[0] + '  ->  ' + m[1]));
