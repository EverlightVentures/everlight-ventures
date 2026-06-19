# TUTORIAL REWORK SPEC (operator, 2026-06-13) -- runs after wave-8 Track A deploys
The wave-7 AK-TUT tutorial is wrong on two counts:

## BUG 1: routes to Everlight Ventures
The tutorial (or a link/CTA inside it) sends the player to everlightventures.io. HARD LAW
[[feedback_domain_locked_logins]] + AUTH_SEPARATION_DOCTRINE: nothing on an Alley Kingz
surface links to or routes to Everlight. FIND the leaking link/redirect in the tutorial
flow (and sweep the whole game once more for any everlightventures.io href or redirect that
crept in during wave 7 -- Codex, story, profile, footer) and remove/repoint to an AK surface.

## BUG 2: it is a "manuscript", not a game
Today it dictates text at the player. REBUILD as an INTERACTIVE, hands-on tutorial:
- A scripted first match on a safe sandbox board where the game PAUSES and prompts the
  player to actually DO each thing: "drag this card to deploy it" (waits for the real drag),
  "now play your 2nd card on the left lane", "watch your troop take the tower", "you are low
  on energy -- wait for the bar", "you cleared the district -- tap to advance".
- Teach by doing: deploy via real drag-drop, energy economy, lane choice, tower objective,
  district advance, opening the first earned crate, the shop. Highlight/spotlight the real
  UI element for each step (dim the rest), advance only when the player performs the action
  (with a Skip option).
- Uses the REAL cards and REAL gameplay, not a slideshow. Ends granting a starter reward.
- First launch only (ak_tut_done); a "replay tutorial" entry in settings.
- Marker // AK-TUT2. Headless-safe. Keep the existing protected constants + all markers.
