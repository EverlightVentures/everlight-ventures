/* ============================================================================
 * ALLEY KINGZ -- TYPE SYSTEM (Pokemon-style strengths/weaknesses)   2026-06-22
 * Each dog's ELEMENT is derived from its crew/faction (one source -- no new card
 * field to maintain). A 4-cycle of effectiveness, +/-20% clamped:
 *      Volt > Phantom > Bone > Zoom > Volt   (each beats the next)
 * HARD: engine.js is FROZEN. This is a DATA layer only -- read by the world-map
 * encounters/raid + the UI for a type-advantage multiplier. It NEVER edits the
 * combat loop; the tower battle's per-card matchups ride a future engine hook.
 * window.AK_TYPES = { typeOf, eff, advantage, label, icon, color, FROM_FACTION }.
 * ========================================================================== */
(function (global) {
  'use strict';
  var FROM_FACTION = {            // crewId (canon factionId) -> element
    k9_circuitry:    'Volt',      // The Crowned -- tech/electric
    boneguard_crew:  'Bone',      // The Rusted  -- grit/bone
    leashbreak_tactix:'Phantom',  // The Hologhosts -- ghost/tech-phantom
    zoomie_syndicate:'Zoom'       // The Unbound -- speed
  };
  var META = {
    Volt:    { icon: '⚡', color: '#00E0C0' },
    Bone:    { icon: '🦴', color: '#C9772E' },
    Phantom: { icon: '👻', color: '#7B5CFF' },
    Zoom:    { icon: '💨', color: '#FF2E88' },
    Stray:   { icon: '🐾', color: '#e8c55a' }   // neutral / unknown
  };
  var BEATS = { Volt: 'Phantom', Phantom: 'Bone', Bone: 'Zoom', Zoom: 'Volt' };   // attacker -> the type it beats
  function canonOf(key) {
    try { var L = global.CANON_CARDS || []; for (var i = 0; i < L.length; i++) { var c = L[i]; if (c && (c.name === key || c.id === key || String(c.cardNumber) === String(key))) return c; } } catch (_e) {}
    return null;
  }
  function typeOf(card) {
    var c = (typeof card === 'string') ? canonOf(card) : card; if (!c) return 'Stray';
    var f = c.factionId || c.faction || c.crewId; return FROM_FACTION[f] || 'Stray';
  }
  // multiplier for an attacker of type A hitting a defender of type D
  function eff(a, d) {
    if (!a || !d || a === 'Stray' || d === 'Stray') return 1.0;
    if (BEATS[a] === d) return 1.2;        // super-effective
    if (BEATS[d] === a) return 0.8;        // resisted
    return 1.0;
  }
  // human verdict for a matchup (for HUD hints): {mult, kind:'strong'|'weak'|'even', text}
  function advantage(a, d) {
    var m = eff(a, d);
    return { mult: m, kind: m > 1 ? 'strong' : (m < 1 ? 'weak' : 'even'),
             text: (m > 1 ? 'super effective +20%' : (m < 1 ? 'resisted -20%' : 'even')) };
  }
  function icon(t) { return (META[t] || META.Stray).icon; }
  function color(t) { return (META[t] || META.Stray).color; }
  function label(t) { return icon(t) + ' ' + (t || 'Stray'); }
  // the dominant element of a roster/deck (most common) -- used for deck-vs-deck pre-battle advantage
  function rosterType(names) {
    if (!names || !names.length) return 'Stray';
    var tally = {}; for (var i = 0; i < names.length; i++) { var t = typeOf(names[i]); tally[t] = (tally[t] || 0) + 1; }
    var best = 'Stray', n = -1; for (var k in tally) { if (tally[k] > n && k !== 'Stray') { n = tally[k]; best = k; } }
    return best;
  }
  global.AK_TYPES = { typeOf: typeOf, eff: eff, advantage: advantage, label: label, icon: icon, color: color, rosterType: rosterType, FROM_FACTION: FROM_FACTION, BEATS: BEATS, META: META };
})(typeof window !== 'undefined' ? window : globalThis);
