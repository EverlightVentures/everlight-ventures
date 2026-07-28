# ALLEY KINGZ UNIFICATION PLAN

## Context

Alley Kingz must feel like several different games sharing one economy: a WoW style 3D RPG overworld,
a Clash Royale battle, a Clash of Clans base builder, MP4 interiors, and a CoD style Gulag FPS. Today
every mode renders through one Canvas2D top down view, so nothing feels distinct, and several systems
that look real are facades.

### This is NOT a rendering rebuild

Exploration found far more already built than the external audit assumed:

| Target mode | Already exists | Actually missing |
|---|---|---|
| Gulag FPS | **The entire game.** `openGulag()` (`systems/modes.js:985`) has cover, line of sight AI, bullets, strafing, twin stick input | Only the renderer (`modes.js:1085`) |
| Clash Royale battle | `AK.game.camera{offX,offY,zoom}` (`engine.js:1406`), `toX/toY`, inverse `canvasToArena` (`game.html:5184`), **18 degree tilt already shipping** (`game.html:2858`), billboard warp built and kill switched (`:2880`) | Flip `TILT2_ENABLED`, drive the camera |
| CoC base builder | `p.builds[]` schema and persistence, 7 structures with sprites, grid snap 64, rotation, timed builders, collision feed, mounted UI button (`buildmode.js`) | Camera and editor view only |
| RPG 3D overworld | `hub3d.js` (per hero GLB registry, yaw, anim FSM), `hero3d.html` working orbit camera, 2 GLBs, self hosted model viewer, 10 painted district plates (406 MB) | Three.js (absent) plus scene assembly |
| Mode router | `AK_CTX.overlay.open()` (`index.html:3009`), push/pop with state save restore, already used by 5 systems | Generalize to accept a WebGL surface |

`RENDER_MODE_CANON.md` is the canonical design doc for this exact migration. This plan is its execution arm.

**Highest leverage seam:** `AK_CTX.world.wx/wy` (`index.html:2992-2998`). Every plugin system draws
through it, so replacing that translate with a projective transform moves all 15 systems to a new
camera for free.

### Why the economy leads

Two save destroyers make every other feature pointless, and they share one root cause.

**P0a, the boot time total wipe.** `game.html:6389` validates a save by `!Array.isArray(p.decks)`, but
`economy.js` never creates `p.decks` (zero matches). So the hub creates a profile with no `decks` key,
the player harvests and upgrades, taps a battle, and `game.html` rebuilds the profile from
`defaultProfile()` carrying only 11 fields, then calls `saveProfile()` unconditionally at boot
(`:6990-6991`). Destroyed on page load with no match required: `townHall, wood, stone, metal, produce,
seeds, crops, builds, nodes, tools, karma, prod, bones, cardLvls, copies, captures, raid, season,
trades, arcade, modes, baseLayout, blockRep, duties, weekly, missions, fragments, handlers, cardMeta`.

**P0b, the stale blob clobber.** `grantMatchRewards` (`game.html:8019`) writes rep, Marks and duty
progress through `mutateProfile`, then `saveProfile()` (`:8235`) serializes the boot time `DBPROFILE`
over them. The authors knew: they guarded the crate slot, bounty and tribute writes (`:8236, :8269,
:8756`) and never applied it to these.

**One fix collapses both.** `game.html` runs a parallel profile engine (`defaultProfile`, `loadProfile`,
`saveProfile`, plus the `DBPROFILE` cache). Delete those three and route its 31 write sites through
`AK_ECON.mutateProfile`. `index.html` already proves the pattern (41 modules, 17 mutate sites, zero
`DBPROFILE`). This also removes races R1 (mid session mutate), R3 (cross tab) and R5 (shop shim).

---

## PHASE 0: make the state trustworthy

1. **Kill the parallel profile engine in `game.html`** (above). Single highest value change in the repo.
2. **Load the missing rails.** `quests.js` and `pass.js` are absent from `index.html`, so every
   `AKQuests.reportEvent` from `encounters.js`, `karma.js`, `missions.js` is a silent no op on the hub.
   `seasons.js` and `population.js` are absent from `game.html`, so match win Marks are never granted
   (`WIN_MARKS = 6` unreachable) and one existing guard protects dead code.
3. **Charge for cosmetics server side.** `ak-cosmetics/index.ts:62-69` checks `PRICES[id]` only for
   existence and never verifies balance. Its own header admits gold is deducted client side. A direct
   POST grants a 900 gold skin free. Add the balance check and debit server side.
4. **Audit the shop function.** `shop.js:39` targets `alley-kingz-shop`, whose source is NOT in this
   repo, and authenticates with the anon key while passing `player_id` in the body (`:89-99`). If it
   trusts that field, anyone can act as any player. Locate the source and verify before launch.
5. **Merge the two bones pockets.** `p.bones` (duties, HUD, stamina, build speedup) and
   `p.handlers.bones` (match rewards, skill tree) are separate wallets with one name and one icon.
   Match earned bones never appear in the HUD.
6. **Resolve "Stand a Watch shift":** a duty for a verb that exists nowhere. Build the activity or
   remove the duty and its weekly capstone.
7. **Fix the metric allowlist.** `ak-quests` rejects everything but `donates` and `chats` with a 400,
   killing duty XP, captures, street events and karma recruits.
8. **Wire the save rescue UI.** `AKSave` export/import/rescue now exists in `ak_account.js` and is
   already hardened (rescue slots, progress scoring, choice modal) but has zero consumers. Also make
   `progressScore` count materials and producer levels, which it currently ignores.

**Gate:** play a match, reload, assert through `AK_ECON.loadProfile()` that rep, Marks, duties, coins
and materials all survive. State reads only.

---

## PHASE 1: delete the facades

- **9 of 11 building upgrades are no ops.** `BUILDING_BENEFIT` (`economy.js:826-836`) defines TROPHY,
  DROP, CLAN, PASS, ARCH, STREET, ARCADE, KENNEL, WARD. The only consumers repo wide are two display
  sites (`index.html:966`, `flywheel.js:136`). They charge gold and materials and return nothing.
  Either implement the multiplier lookups or remove the upgrades. Note TROPHY's "+5% Block Rep" sits on
  top of `addRep`, which is itself clobbered: the same currency broken twice, independently.
- **Cosmetic parts are a facade.** `COS_PRICE` (`drip.js:46-52`) defines a ladder up to 200 gems, but
  `AKDrip` exports no buy function (`:410-411`) and `shop.js:2345-2357` renders the price as inert text
  beside an Equip button. Part ids are not in the server `PRICES` table, and rendering is ownership
  gated (`drip.js:145`), so a "equipped" part can never render. Add the purchase path.
- **Gems have no faucet.** `index.html:3006` explicitly refuses to grant them; `economy.js:11` says
  server only; the only writer is the missing shop function. Every gem price is unreachable today.
- **Town Hall `crewSize` and `grid`** are surfaced but gate nothing (`economy.js:361-363` admits it).

---

## PHASE 2: finish the four half built lanes

Written and parsing, but not wired. All four came back FIX_FIRST under adversarial verify.

- **TH cap** (`economy.js` AK-THCAP): enforce in the producer path (`production.js`) and the generic
  building path, not only in `upgradeBuilding`. Give `finishBuildingUpgrades()` a caller. Fix the
  `index.html` probe: wrong signature, and it reads `buildingCap` where it needs `buildingCapFor`.
- **Harvest** (`worldmap.js` AK-HARVEST): enforce the respawn cooldown inside `harvest()` (loopable
  today for infinite materials), reuse the `worldverbs.js:638` tool tier gate, drop the parallel
  `FENCE_TIERS` list in favour of buildmode STRUCT costs, then add a tap handler and draw pass so it
  has a consumer at all.
- **Ground loot labels**: keep the worldverbs node labels, drop the duplicated `WV_TAG` table.

---

## PHASE 3: mode and camera architecture

Generalize `AK_CTX.overlay.open()` into a `ModeManager` and unify the three existing 2D cameras (hub
translate only, battler `{offX,offY,zoom}` plus tilt, worldmap `{cam,scale}` pinch pan) behind one
interface. Add Three.js (absent today, do not scavenge model viewer's bundled copy).

Create `game/systems/modes/`, one module per mode, each owning camera, controls and surface, all
reading the SAME state. Reuse `akPlayTransition()` and `transition_wipe.mp4` for blends (authored
assets, not bugs). Precedent in repo: `arcade.js` runs 5 distinct games off one surface, differing only
by their `onFrame` callback.

---

## PHASE 4: build the modes, cheapest first

1. **Gulag FPS.** Swap the renderer at `modes.js:1085` for a first person camera. Game logic untouched.
   Largest felt change for the least work.
2. **Battle.** Flip `TILT2_ENABLED` (`game.html:2880`) and drive the existing camera, then deepen with
   3D lanes and card to board spawn animation.
3. **Base builder.** New isometric camera and editor view (drag existing buildings, ghost preview,
   green/red validity, 90 degree rotation snaps). Keep `place()/remove()/reconcileJobs()` and
   `p.builds[]` untouched; add iso projection to `drawStruct` (`buildmode.js:1192`). Delivers the
   reflection pair: edit in 2D, see it standing in the 3D world.
4. **RPG 3D overworld.** Largest conversion, deliberately last. Swap `AK_CTX.world.wx/wy` for a
   projective transform so all 15 plugin systems follow, and keep a Canvas2D layer as HUD compositor
   (`hub3d.js` already proves the inverse composite works).

Every mode ships playable with placeholder geometry. Models load from a registry so swapping in a
finished GLB is a one line data change.

---

## PHASE 5: rig and weapon content pipeline

Operator confirmed: **Higgsfield generates reference images, operator meshes by hand in Tripo Studio.**
Automated meshing stays off (the Tripo API wallet is separate from the 25k Studio credits, and empty).

Extend `art/build_card_roster.py` and `art/rig_bible.json` to emit, per rig and per weapon:

1. **A `MESH` prompt:** one subject, plain background, flat even lighting, full vehicle uncropped, 3/4
   front view. No cinematic styling, because heavy shadow and film grain bake into the texture and
   corrupt geometry (proven on the dog pipeline).
2. **A `CARD` prompt:** the cinematic hero shot, card face only.
3. **Trademark discipline.** Research real trucks and supercars for silhouette accuracy and record it
   in the internal only `dna` field (the bible already does this correctly). Player facing names stay
   original. **Blocking: "GTR" is a live Nissan trademark sitting in shipped card data. Rename before
   generating any art.**
4. **Deterministic filenames** for drag and drop into Tripo: `rig_<family>_<slug>_MESH.png` and
   `_CARD.png`, weapons `wep_<class>_<slug>_MESH.png`.

**Every card gets a rig.** Today roughly 44 cards carry an empty `"{Breed} Rig"`, 58 are copy paste
templates, and the 20 named bible rigs are orphaned with zero overlap. Execute
`AK_WAR_RIG_MERGE_PLAN.md` (written, never run) so no dog rides an unnamed car.

Also outstanding: the 21 new cards (0107 to 0127) have complete data and zero art.

---

## PHASE 6: the compounding loadout economy

```
RIG rarity    -> HARDPOINTS   (Common 1 ... Mythic 4-5)
WEAPON rarity -> ATTACH SLOTS (Common 1 ... Mythic 3)
loadout depth  = hardpoints x slots per weapon
```

- Enforce capacity in the Phase 0 ledger work. Capacity is purchasable adjacent and must not be client
  trusted.
- **The art must agree with the stats.** Mount count becomes a hard variable in the prompt generator, so
  a Mythic rig visibly carries more hardpoints than a Common. Meshes get sockets at the hardpoints,
  reusing the `drip.js` `COS_SLOTS` socket pattern so rig skins and attachments share one system.
- Rig skins are material swaps on a bought once mesh: cheapest revenue in the project.

---

## Integration discipline

Learned from four dead lanes in the previous run:

1. A lane is done when **a real consumer calls it**, not when it parses.
2. **No self written mocks as proof.** One lane verified itself against invented mocks and shipped a
   broken gate. Proof is a state read from a real session.
3. Parallel lanes get file ownership **plus a named integration owner**.
4. Keep adversarial verify. It caught all four failures.

---

## Verification

- **Economy:** run the Playwright harness on e5 (`e5:~/ak_qa/`), play a match, reload, assert
  `AK_ECON.loadProfile()` retains rep, Marks, duties, coins, materials and keys. State assertions only:
  an earlier QA pass produced 9 false PASSes from pixel diffs because a tutorial overlay
  (`ak-tut-root`, z 9000) sat on top. Dismiss it with the clean `AK_TUTORIAL.skip()` API.
- **The wipe specifically:** build up hub state, cross into `game.html`, return, and assert every field
  in the P0a loss list survived.
- **Modes:** enter and exit each mode, confirm camera, controls and art direction are visibly distinct
  and that no two modes render at once.
- **Reflection pair:** move a building in builder mode, exit, confirm it moved in the world.
- **Content:** every card resolves a named rig, zero trademarked strings in player visible data, MESH
  images import cleanly into Tripo Studio.
- **Deploy:** `nohup bash ship.sh` detached on e5, then verify the LIVE edge by **content type**, not
  status code (CF Pages serves an HTML shell with 200 for missing assets).
