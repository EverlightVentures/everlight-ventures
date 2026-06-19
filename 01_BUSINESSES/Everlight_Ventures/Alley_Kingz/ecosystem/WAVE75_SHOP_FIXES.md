# WAVE 7.5 -- SHOP CHAIN + SENSORY FIXES (operator live-test, 2026-06-12 morning)
Run IMMEDIATELY after wave 7 deploys. Mostly shop.js/economy.js + small engine.

## DONE ALREADY (this morning, live)
- Sales = first-day welcome ONLY; market normal after (server, verified).
- Server disclaimer honest (live). Cache-stamp deploy wrapper on e5 (ship.sh)
  so players ALWAYS get fresh code -- root cause of "fixes not showing".

## P0 BUGS (the purchase chain)
1. TOP-OF-PAGE TEST-MODE BANNER: the Chop Shop page TOP still shows "TEST MODE
   no real charges" -- find banner()/topbar in shop.js + any hardcoded launcher
   text in shop.html; kill all remaining test-mode strings (charges are REAL).
2. "MUST LOG IN" WHILE LOGGED IN: cfg.online false on the shop page despite an
   active session. Make cfg resilient: recompute playerId/anonKey from
   localStorage(ak_player_id) + window.AK_SUPABASE_ANON_KEY at EVERY action
   (not just open), listen for the ak-auth event to re-config + re-render, and
   show a tiny signed-in indicator so the state is visible.
3. SERVER GRANTS MUST LAND LOCALLY (the Balboa case): Lucky Draw pulls, server
   chest opens and gem-buys grant card NAMES but not local COPIES, so upgrades
   show 0 copies. Fix the bridge: every server grant adds copies via
   AK_ECON.addCopy (draw results, confirm-gems grants, open-chest grants,
   gem-buy-copy) so the Garage upgrade math sees them. Also reconcile: owned
   names without a copies entry get copies=1 on load (heal pass).
4. UPGRADE FREEZE: buying/upgrading sometimes shows success but no currency
   deduction + no card added + panel freezes. Audit the Garage level-up and
   buy paths end to end: every mutation through ONE atomic mutateProfile,
   render() after every action, no awaiting a server response for local spends,
   try/catch so a thrown error can never leave the UI frozen mid-action.
5. STALE STATS AFTER UPGRADE/TUNE: re-render the detail panel + garage tile
   immediately on level-up and on tune (verify wave-7 lane 1c landed; if not,
   do it here).

## P1 SENSORY
6. VOICE VARIETY: only 2 system voices in use and the female voice dominates.
   Spread deterministically across ALL available en-* device voices (seed by
   cardNumber), keep breed pitch/rate variation on top, male/female assignment
   by card name/breed where inferable. Fallback chain when voices list is
   empty (load voices async via onvoiceschanged).

## NOTES (not bugs)
7. MAPS: only ~5/10 city art sets painted so far -- the Crown paints 60/day
   and districts fall back to legacy arenas until their art lands. ALSO queue
   the wiring task: use the painted L<NN>_<district>.png as the in-match
   BACKDROP per city/level once painted (currently only level tiles use them).
8. Card-level field application: FIXED in the micro-pass (engine applies
   +6%/lv at deploy) -- operator saw stale cache; the e5 ship.sh stamp fixes
   distribution going forward.
