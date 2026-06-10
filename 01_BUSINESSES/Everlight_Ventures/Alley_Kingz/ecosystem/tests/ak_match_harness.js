// ==========================================================================
// ALLEY KINGZ -- NODE MATCH HARNESS (no browser, no deps)
// Replaces the /tmp harnesses that got wiped with the session (2026-06-09).
// Runs a FULL simulated convoy match: engine + canon load headless, the AI
// plays itself, and a scripted "player" deploys a random affordable card
// every ~2.5s so abilities (knockback / double / aoe / spells) actually fire.
// PASS = the whole match runs without throwing and the sim clock advances.
// Usage: node ecosystem/tests/ak_match_harness.js
// ==========================================================================
'use strict';

const GAME_DIR = __dirname + '/../game';

// engine.js falls back to globalThis, but canon.js publishes CANON_* onto
// `window` -- give node a window alias so both load exactly like the browser.
global.window = global;

require(GAME_DIR + '/canon.js');
require(GAME_DIR + '/engine.js');

const AK = global.AK;
const info = AK.init();
console.log('cards loaded: ' + info.count + '  spells: ' + info.spells);

AK.newMatch(AK.STARTER_DECK_NAMES);
const g = AK.game;

const DT = 1 / 60;
const MAX_SIM_S = 260;            // MATCH_TIME(180) + transitions + overtime headroom
let frames = 0, deploys = 0, peakUnits = 0, lastErr = null;
let nextDeployAt = 1.5;

try {
  for (let t = 0; t < MAX_SIM_S; t += DT) {
    // scripted player: every ~2.5s drop a random affordable card on our half
    if (t >= nextDeployAt) {
      nextDeployAt = t + 2.5;
      const idx = (Math.random() * g.player.hand.length) | 0;
      const gx = 1 + Math.random() * (AK.ARENA_W - 2);
      const gy = AK.ARENA_H * (0.6 + Math.random() * 0.3);   // own (bottom) half
      if (AK.deploy(g.player, idx, gx, gy)) deploys++;
    }
    AK.update(DT);
    frames++;
    if (g.units.length > peakUnits) peakUnits = g.units.length;
    if (g.over || (g.phase && g.phase === 'ended')) break;   // match concluded
  }
} catch (e) {
  lastErr = e;
}

console.log('frames=' + frames + ' deploys=' + deploys + ' peakUnits=' + peakUnits
  + ' simTime=' + (g.time != null ? g.time.toFixed(1) : '?')
  + ' section=' + g.section + ' playerCrowns=' + g.player.crowns
  + ' aiCrowns=' + g.opponent.crowns);

if (lastErr) {
  console.log('=== VERDICT: MATCH THREW ===');
  console.log(lastErr.stack || String(lastErr));
  process.exit(1);
}
if (frames < 600) {               // <10s of sim = something silently stalled
  console.log('=== VERDICT: SIM STALLED EARLY ===');
  process.exit(1);
}
console.log('=== VERDICT: FULL MATCH RAN CLEAN (no throw) ===');
