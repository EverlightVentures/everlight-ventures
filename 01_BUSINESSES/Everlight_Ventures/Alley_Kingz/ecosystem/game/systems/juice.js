/* Alley Kingz -- JUICE LAYER (window.AK_JUICE)
 *
 * The meta-layer feedback the 2026-07-16 audit found missing. The economy has
 * five tiers of escalation; the juice had one. This is the door on the vault.
 *
 *   - HAPTICS            zero existed anywhere in the build
 *   - 5-TIER IMPACT      damage magnitude decides how hard a hit lands
 *   - RARITY LADDER      Supercell doctrine: rarity is a hard-gated audio ladder
 *                        with a dedicated top rung, repeated across subsystems
 *   - BONUS ESCALATION   the bonus_1..4 rung ladder
 *   - CHEST SEQUENCE     staged beats (fly, land, loop, unlock, open) with
 *                        per-tier identity, replacing one MP4 shared by 5 tiers
 *
 * ARCHITECTURE NOTE, stolen from Supercell's own .sc format: their timeline
 * carries NO sound. The animation and the audio cue list are separate systems
 * joined at runtime by game code. That separation is why they can retune a cue
 * nine times without touching art. So this module owns the CUE LIST and the
 * timing; AK.sfx owns playback. Do not bake sound into the animation here.
 *
 * Additive and typeof-guarded throughout. Nothing in this file can break an
 * existing path: every call site degrades to a no-op if the host lacks the API.
 */
(function (global) {
  'use strict';

  var J = {};

  /* ---------------------------------------------------------------- HAPTICS
   * navigator.vibrate takes a duration or a pattern array. It is absent on iOS
   * Safari and on desktop, which is why every call is wrapped and returns a
   * boolean rather than throwing. Patterns are [buzz, pause, buzz, ...].
   */
  var HAPTIC = {
    card_draw:       12,
    hit_1:            8,
    hit_2:           18,
    hit_3:          [22, 30, 22],
    hit_4:          [30, 40, 60],
    hit_5:          [40, 30, 40, 30, 90],
    ability:        [10, 20, 40],
    deploy:          14,
    chest_land:     [30, 20, 50],
    chest_shake:    [6, 70, 6, 70, 6, 70],
    chest_common:    20,
    chest_rare:     [20, 40, 30],
    chest_epic:     [30, 40, 50, 40, 70],
    chest_legendary:[40, 30, 40, 30, 40, 30, 120],
    chest_mythic:   [60, 40, 60, 40, 60, 40, 200],
    victory:        [40, 60, 120],
    defeat:         [120],
    crew_ping:        8
  };

  var hapticsOn = true;
  try { hapticsOn = localStorage.getItem('ak_haptics') !== '0'; } catch (_) {}

  J.haptic = function (key) {
    if (!hapticsOn) return false;
    var p = HAPTIC[key];
    if (p === undefined) return false;
    try { return !!(global.navigator && navigator.vibrate && navigator.vibrate(p)); }
    catch (_) { return false; }
  };
  J.setHaptics = function (on) {
    hapticsOn = !!on;
    try { localStorage.setItem('ak_haptics', hapticsOn ? '1' : '0'); } catch (_) {}
    return hapticsOn;
  };
  J.hapticsOn = function () { return hapticsOn; };
  J.hapticKeys = function () { return Object.keys(HAPTIC); };

  /* ----------------------------------------------------- THE 5-TIER IMPACT
   * A 200-damage crit and an 8-damage chip should not feel the same. Returns
   * the tier so the caller can also drive shake and flash from one decision.
   * The shake values are pixel amplitudes matching game.html's existing shake.
   */
  var IMPACT = [
    { max: 20,       tier: 1, shake: 0,  slowmo: 0,   haptic: 'hit_1' },
    { max: 50,       tier: 2, shake: 2,  slowmo: 0,   haptic: 'hit_2' },
    { max: 100,      tier: 3, shake: 4,  slowmo: 0,   haptic: 'hit_3' },
    { max: 200,      tier: 4, shake: 7,  slowmo: 0,   haptic: 'hit_4' },
    { max: Infinity, tier: 5, shake: 12, slowmo: 120, haptic: 'hit_5' }
  ];

  J.impact = function (damage) {
    var d = Math.abs(+damage || 0);
    var row = IMPACT[IMPACT.length - 1];
    for (var i = 0; i < IMPACT.length; i++) {
      if (d <= IMPACT[i].max) { row = IMPACT[i]; break; }
    }
    J.haptic(row.haptic);
    return row;
  };

  /* -------------------------------------------------- THE RARITY LADDER
   * Fires through AK.sfx, which already dispatches sample-then-synth. The
   * engine owns playback; this owns which rung fires and when.
   */
  var RUNGS = ['Common', 'Rare', 'Epic', 'Legendary', 'Mythic'];

  function play(name) {
    try { if (global.AK && global.AK.sfx) { global.AK.sfx(name); return true; } } catch (_) {}
    return false;
  }

  J.raritySting = function (rarity) {
    var r = String(rarity || 'Common');
    if (RUNGS.indexOf(r) < 0) r = 'Common';
    play('chest_' + r.toLowerCase());
    J.haptic('chest_' + r.toLowerCase());
    return r;
  };

  /* The bonus_1..4 escalation ladder. Each extra reward beat lands one rung
   * higher than the last, so a five-card diamond crate audibly climbs.
   */
  J.bonus = function (step) {
    var n = Math.max(1, Math.min(4, (step | 0) || 1));
    play('bonus_' + n);
    return n;
  };

  /* ----------------------------------------------------- CHEST SEQUENCE
   * The staged beats Supercell's own asset names expose:
   *   chest_fly -> chest_land -> chest_loop -> unlock_chest_start -> chest_open
   * chest_loop existing AS A LOOP is the proof the anticipation hold is a
   * designed first-class state, not a transition. So it gets real dwell time,
   * and it scales with tier: a diamond crate makes you wait for it.
   *
   * opts: { tier, rarity, el, onOpen }
   *   tier   'wood'|'bronze'|'silver'|'gold'|'diamond'
   *   rarity the TRUE top rarity in the payload, drives the sting
   *   el     optional element to shake during the hold
   *   onOpen callback fired at the open beat
   * Returns a cancel function.
   */
  var TIER_HOLD = { wood: 380, bronze: 520, silver: 700, gold: 950, diamond: 1400 };
  var TIER_ART = {
    wood: 'assets/ui/chest_wood.jpg', bronze: 'assets/ui/chest_bronze.jpg',
    silver: 'assets/ui/chest_silver.jpg', gold: 'assets/ui/chest_gold.jpg',
    diamond: 'assets/ui/chest_diamond.jpg'
  };

  J.chestArt = function (tier) { return TIER_ART[tier] || TIER_ART.wood; };
  J.chestHold = function (tier) { return TIER_HOLD[tier] || TIER_HOLD.wood; };

  J.chestSequence = function (opts) {
    opts = opts || {};
    var tier = String(opts.tier || 'wood');
    var hold = J.chestHold(tier);
    var el = opts.el || null;
    var timers = [];
    var dead = false;

    function at(ms, fn) { timers.push(setTimeout(function () { if (!dead) fn(); }, ms)); }

    // land
    play('chest_land'); J.haptic('chest_land');

    // the hold: a real dwell, ticking faster as it goes. This is the beat the
    // MP4 could never have, because a video cannot know what is inside.
    var ticks = Math.round(hold / 110);
    for (var i = 0; i < ticks; i++) {
      (function (i) {
        at(Math.round(hold * (i / ticks)), function () {
          play('chest_tick');
          if (el && el.style) {
            var amp = 1 + (i / ticks) * 3;
            el.style.transform = 'translate(' + ((i % 2 ? -amp : amp)).toFixed(1) + 'px,0)';
          }
        });
      })(i);
    }
    at(hold - 60, function () { J.haptic('chest_shake'); });

    // open
    at(hold, function () {
      if (el && el.style) el.style.transform = '';
      play('chest_unlock');
      J.raritySting(opts.rarity || 'Common');
      if (typeof opts.onOpen === 'function') { try { opts.onOpen(); } catch (_) {} }
    });

    return function cancel() {
      dead = true;
      for (var t = 0; t < timers.length; t++) clearTimeout(timers[t]);
      if (el && el.style) el.style.transform = '';
    };
  };

  /* ------------------------------------------------------------- EXPORT */
  J.version = 1;
  global.AK_JUICE = J;

})(typeof window !== 'undefined' ? window : globalThis);
