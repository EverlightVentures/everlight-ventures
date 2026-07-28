# Alley Kingz -- VIM MODE: the hidden dev layer (QUEUED -- build AFTER Waves 2-4)
*A keyboard-native control layer where vim motions map to game mechanics. A discovered easter-egg skill tree for DESKTOP/keyboard players; invisible to touch players. From Kimi's design bible, adapted to our canon + our engine constraints. Operator order: implement the V2 roadmap (Waves 2-4) FIRST, THEN build this via a workflow. 2026-06-25.*

## CORE (keep -- it is a strong, on-brand-for-devs concept)
"The keyboard is your weapon. The modes are your stance. The commands are your combos." Vim's verb+noun grammar (operator + motion + count) maps to game actions. Modal states map to game states: NORMAL = explore/combat-ready (block cursor), INSERT = build/customize (line cursor), VISUAL = target/area-select, COMMAND-LINE (:) = progression/macros. Esc = panic-reset to Normal. A `-- NORMAL --` style mode indicator shows in a corner.

## OUR-CONTEXT ADAPTATIONS (the important deltas from Kimi's draft)
1. **Desktop/keyboard only -- a LAYER, never a requirement.** alleykingz.online runs in-browser; phone/touch players never see it and are never disadvantaged. Vim Mode is a hidden parallel-depth for keyboard players (devs). This is the whole charm.
2. **Engine-frozen-safe.** Build as a HOST-SIDE keyboard interpreter (a new systems/vimmode.js) that listens for keydowns, tracks the mode/pending-command, and dispatches to EXISTING game actions (move me, target, enter building, open trade, advance chapter). It NEVER edits engine.js or the combat loop -- it just drives the same actions a tap would. A clean wrapper.
3. **NAME CANON (re-skin Kimi's generics -- per AK_ROADMAP_V2_NAMED.md section 0):** the crew-training drills are NOT "Enforcer/Lookout/Hacker/Wheelman" -- they map to OUR cabinets (BONE DIG, ALLEY DASH, WHACK-A-STRAY, GEM MINE, CARD FORGE) and OUR pack/handler classes. Ranks are NOT "Rank 1/5/10" -- they are Stray->Pup->Runner->Warrior->Enforcer->Right Paw->King of the Block (note: "Enforcer" IS one of our ranks -- fine). Districts are OUR 9 (`:e the_docks`, not `:e district5`). The narrative throne/collar/ledger use our Crown Bloodline + Old Pack + soulbound terms.
4. **Discovery** (on-brand): type `:vim` in any text field, OR triple-Esc, OR a graffiti tag in HOME_TURF reading "hjkl is the way" (our gritty style), OR the streets whisper of "a keyboard layer."

## THE MAPPINGS (kept, our-skinned)
- **District nav:** hjkl move; w/b/e jump interactables; 0/^/$ entrance/active-node/boss-node; gg=HOME_TURF, G=farthest held district; {/} sector jumps; ma + `a waypoints; Ctrl+u/d/zz camera.
- **Combat (operators+motions -- host-side, drives existing attack/target actions):** d=heavy hit, y=pull/disarm, c=swap weapon/terrain, >=knockback, <=grapple, ~=confuse/flip-facing, ==heal/buff, gu/gU=weaken/empower. Motions w/b/t/f/iw/ip/a"/i( select the target(s). Combos: dw, 3dw, yip, >} , gUiw. `.` repeats last combo.
- **The Watch (guarding) = Visual mode:** v/V/Ctrl-v select tile/street/grid; operate to place/clear/copy/paste defense layouts (Vjy yank layout, Vp paste, V> extend). Defenders are OUR pack cards.
- **Crew training = vim drills:** our cabinets prompt vim sequences (dd/yy/cc timing in WHACK-A-STRAY; /search + n + *  in a lookout-style cabinet; counted motions 10j/5w/3fa in ALLEY DASH). High scores sharpen the pack AND unlock vim hints.
- **The Fence (market) = registers:** "ay yank item to register a, "ap paste/sell, :reg = inventory, "_d = destroy, "+y/"+p = share/receive trade with allies.
- **Running with the crew (co-op) = multiplayer vim:** :split/:vsplit ally views, :bnext/:bprev switch ally, Ctrl-w hjkl navigate screens. Roles: Driver=Insert (nav), Muscle=Normal (combat), Inside-dog=Visual (stealth/lockpick).
- **Crown Bloodline gates = command-line:** :w save, :q menu, :wq save+exit, :<n> jump to Chapter n (gated by rank/turf), :/boss search encounter, :set nu rank numbers. ":11 -> There is no Rank 11" glitch = the rank-ceiling reveal (ties to THE COLLAR IS THE MONSTER).
- **Auteur steals via vim:** `:e throne` edit the throne room (:%s/dirt/gold/g renovate, gg=G organize); :registers = the scar/memory ledger ("ap = relive a scar flashback; q-a record a move macro); :set background=dark/light = world day/night; `~` flips a crew member's loyalty and OVERUSE tightens the collar (the system is the monster); macros (q) record move sequences.
- **In-world glyphs = vim glyphs:** ~ : / % $ ^ * @ " as the diegetic icon language (pairs with the de-emojify work -- only devs read them all).
- **Compliance via :help:** :help age / privacy / tos / stripe; :help vim unlocks the secret manual.

## SECRET MANUAL (shown on :help vim) -- keep verbatim, our voice
"VIM MODE -- The Dev's Edge. You found what the streets whisper about: a deeper layer to this city, for those who speak the terminal. hjkl to move. Esc to reset. : to command. The more fluent you get, the more the city opens. Every command works in your editor too. This is not a game mechanic. This is a lifestyle upgrade. :wq"

## BUILD ORDER (when we get here, after Waves 2-4 -- Kimi's priority, sound)
1. systems/vimmode.js core: keydown interpreter + mode state + the `-- NORMAL --` indicator + discovery triggers. 2. Navigation (hjkl + motions) -- affects everything. 3. Combat operators (host-side, drive existing actions). 4. Visual mode (guarding + co-op area select). 5. Command-line (Crown gates + cheats + :help). 6. Registers (the Fence). 7. Crew-training vim drills. 8. Multiplayer coordination. 9. Narrative vim integration (auteur). Build incrementally; each layer is optional + additive; touch players unaffected throughout.

## STATUS: QUEUED. Do NOT start until AK_ROADMAP_V2_NAMED.md Waves 2-4 are implemented + live. Then build via a dedicated workflow.
