# Alley Kingz Walkable Hub World -- Design + Build Plan (deep-dive 2026-06-18)

North-star: AK is judged by fun/feel/finish and its core is a TAP-FAST card battler. The hub is immersive
flavor WRAPPED around the battler -- it must NEVER gate a fight. Battle stays one tap away always.

## 1. TECH VERDICT
**Build it 2.5D ISOMETRIC in Phaser 3 -- NOT full Three.js.** Reuses AK's existing 2D sprite + art_factory
pipeline, fits a phone's GPU/battery (one heavy scene at a time, no 3D-model/draw-call blowup), nails the
Sunflower-Land/cyberpunk-dog look, matches AK's perf-budget doctrine. Full-3D Three.js loses on asset cost +
mobile perf + effort; 2D-tile-only loses the immersion. Iso is the middle that delivers depth without 3D cost.
**HARD CAVEAT: do NOT port the match into Phaser.** engine.js (253KB, canvas2D, juiced) stays as-is. The hub is
a NEW separate Phaser scene that WRAPS the existing screens.

## 2. THE WORLD -- "The Lot" hub
A small, DENSE cyberpunk alley block (small+dense beats big+empty), neon/rain, matching the `the_lot` painted map.
- Home plaza = spawn; your dog/rig idles there. Buildings line the street with glowing labeled doors.
- Corner tap-to-teleport MINI-MAP (jump to any building OR straight to Battle) = the tedium release valve.

**Buildings -> existing AK screen each opens (every one maps to a button that already exists in lobby.js):**
| Building | Opens | Mechanism |
|---|---|---|
| The Arena (center, biggest) | Battle/matchmaking (engine.js) | existing battle entry |
| The Garage | Deck builder + Handlers (deckbtn/handlerbtn) | reuse lobby handlers |
| The Drop | shop/shop.html (gems, Drip, The Drop) | location.href (already wired) |
| The Vault | Collection + Codex (akcodexbtn/cratesbtn) | existing handlers |
| The Arcade | $BCARDD blackjack | existing arcade mount |
| Trophy Hall | Trophy/profile + Alley Pass (profilebtn/pass.js) | walk-in OFF the victory screen |

**Avatar:** the player's chosen dog-pilot/rig (reuse an existing card/unit sprite -- zero new core art for MVP;
idle + 2-4 frame walk, or bob-and-slide). Drip skins swap it later.
**Movement:** TAP-TO-MOVE (RuneScape/Stardew-mobile), NOT a joystick (joysticks eat mobile screen + perform worse
when walking is secondary). Enter-building = Stardew-style fade-to-black scene swap (masks load; only ONE heavy
scene in memory at once -- hub OR shop OR match, never all three).

## 3. INTEGRATION -- the hub WRAPS, never rebuilds
- New `hub.js` + a Phaser scene mounted as a new lobby mode beside the current lobby; **the button-menu lobby
  STAYS as the fallback** (de-risks everything).
- Buildings dispatch the SAME handlers the buttons fire today (location.href / .click()). No screen reimplemented.
- Fade-to-black hides the canvas<->DOM swap; back = reverse fade, re-show hub at the door you exited.
- Trophy Hall off victory: the victory screen gets "Walk to the Trophy Hall ->" that loads the hub with the
  avatar auto-pathing into the Trophy Hall (= opens profile/pass) -- the dopamine lap after a win.
- Iso ground/backdrop tiles reuse the dedicated alley-kingz-maps host (deploy-isolation, ACAO:*). PII rule holds.
Net: a new NAVIGATION SKIN. Battle engine, shop, economy, pass, quests, codex, handlers reused byte-for-byte.

## 4. PHASED BUILD PLAN (deploy via sole-deployer e5 ~/ak_deploy -> ship.sh; verify in a real browser; never stale)
- **Phase 0 -- Feel Prototype (3-5 days):** one Phaser iso scene, placeholder buildings + door rects, avatar =
  an existing sprite, tap-to-move + fade-to-black that just console.logs "would open shop." No real art, no
  integration. Behind a `?hub=1` flag. DELIVERS: a yes/no on "does walking-to-a-fight feel good or annoying on
  Rich's actual phone?" GATES the whole project. Risk: low.
- **Phase 1 -- MVP Walkable Street (1.5-2 wks):** one polished block, 4 buildings wired to REAL screens (Arena/
  battle, Garage/deck, The Drop/shop, Vault/collection); real iso art (3-4 art_factory assets); corner teleport
  mini-map + a hard "FIGHT NOW" shortcut. Hub is OPT-IN; button-lobby stays default. Risk: medium (iso scene
  mobile perf + walk cycle) -> cap one scene in memory, pre-render glows to sprites (never strip effects).
- **Phase 2 -- The Payoff Lap (1-1.5 wks):** Trophy Hall walk-in off victory + the remaining buildings, polish.

## HONEST RISKS
Mobile perf of the iso scene; asset cost (iso tiles + avatar frames); scope creep. Do Phase 0 FIRST to prove the
feel cheaply before committing -- if walking feels like friction on a phone, stop and keep the tab bar.
