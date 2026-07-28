export const meta = {
  name: 'ak-coc-economy-layer',
  description: 'Alley Kingz Clash-of-Clans layer: tile grid + inventory editing, collectors/storages with real distribution, loot math with TH caps and penalties, builder queue, shield/guard/break timers, and the 3D-to-sprite pipeline that makes the tower defense look 3D without a 3D engine',
  phases: [
    { title: 'Build', detail: 'six lanes, strict non-colliding ownership' },
    { title: 'Verify', detail: 'adversarial, integration-gated' },
  ],
}

const ECO = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem'

const RULES = `
REPO: ${ECO}

CRITICAL OWNERSHIP NOTICE. Another workflow (Wave 3) may be running and owns these files. Do NOT
touch them: game/systems/modes.js, game/systems/buildmode.js, game/systems/world3d.js,
game/systems/marketplace.js, game/systems/trading.js, game/systems/pass.js, game/systems/seasons.js,
game/systems/replay.js, game/systems/weather.js, game/assets/vendor/, game/systems/three_boot.js.
game/index.html is also OFF LIMITS: give exact insert lines in needs_from_others instead.

HARD RULES
- You OWN only the files in YOUR FILES.
- Match surrounding style. Tag new blocks with a dated marker like AK-XXXX 2026-07-18.
- NO em-dash characters. NO innerHTML. Both are rejected by guards.
- Persist ONLY through AK_ECON.mutateProfile. Never write localStorage directly: a whole class of
  save-loss bugs in this repo came from a parallel profile engine doing exactly that.
- INTEGRATION IS THE BAR. A lane is done when a real consumer reaches it, or when you state the exact
  one-line include/call the orchestrator must add and prove that line is correct. Previous runs
  shipped code nothing called; do not repeat it.
- NEVER verify with mocks you invented. Extract the REAL function from the REAL file and run it.
- node --check every .js you touch and report the real output.
- Headless-safe and pure where possible so the server can reuse the same math later.
- Do NOT deploy.

THE ARCHITECTURE THIS SERVES (read carefully, it explains why these lanes exist)
Alley Kingz nests worlds inside buildings. Walking the 3D district is the outer world. Entering the
BUILDER building drops you into a Clash-of-Clans base-editing world. Entering the GARDEN building
drops you into a Sunflower-Land farming world. The LAW: edits made inside a nested world MUST be
visible in the outer 3D district when you walk out. That works because there is ONE shared state and
MANY renderers, not two copies of the data. game/systems/buildmode.js already stores placements in
p.builds[] (zone,x,y,rot,hp) and already injects them into collision, so p.builds[] IS the shared
schema. Everything you build must read and write that same state rather than inventing a parallel one.
`

const SCHEMA = {
  type: 'object',
  properties: {
    lane: { type: 'string' },
    done: { type: 'array', items: { type: 'string' } },
    files_changed: { type: 'array', items: { type: 'string' } },
    integration_proof: { type: 'string' },
    parse_output: { type: 'string' },
    parse_verified: { type: 'boolean' },
    not_done: { type: 'array', items: { type: 'string' } },
    needs_from_others: { type: 'array', items: { type: 'string' } },
  },
  required: ['lane', 'done', 'files_changed', 'integration_proof', 'parse_verified', 'parse_output'],
}

phase('Build')
const LANES = [
  {
    key: 'base-grid',
    files: 'game/systems/basegrid.js (NEW, yours alone)',
    task: `Build the TILE GRID and the INVENTORY-BASED EDITING MODEL that makes Clash-of-Clans base
editing feel effortless.

Reference behaviour to match:
  - A square tile grid, roughly 40x40, with footprints per building type: 1x1 traps/decor, 2x2 huts,
    3x3 storages and most defenses, 4x4 Town Hall and big army buildings.
  - THE KEY IDEA, and the reason CoC editing feels good: you do not shuffle buildings around the map
    one at a time. You REMOVE them into an inventory tray (grouped by type and level), which lets you
    clear the whole base and rebuild from scratch without losing anything, then drag them back.
  - Valid/invalid placement highlighting, generous but precise snapping, no overlap.
  - Move-all (shift the whole layout one tile any direction, rotate 90 degrees about the center).
  - Multiple saved layout slots, and a scout view that hides traps to show what an attacker sees.

In game/systems/basegrid.js implement the DATA + RULES layer (not the renderer):
  - FOOTPRINTS registry per building type, tile size, world<->tile conversion helpers.
  - occupancy(): fast lookup of taken tiles, built from the EXISTING p.builds[] schema used by
    buildmode.js. Read buildmode.js first and match its entry shape exactly; do NOT invent a second
    placement schema, because the nested-world reflection depends on one shared state.
  - canPlace(type, tileX, tileY, rot) -> {ok, reason} covering overlap, bounds, adjacency.
  - toInventory(entryId) / fromInventory(itemId, tileX, tileY, rot): the remove-into-tray flow.
  - moveAll(dx,dy) and rotateAll(): whole-layout transforms with a validity pre-check so a move that
    would push anything out of bounds is rejected atomically rather than half-applied.
  - layout slots: save/load/list named layouts, all through AK_ECON.mutateProfile.
Prove it: build a real occupancy map from a real p.builds fixture, place and reject overlaps, run
moveAll into a wall and show atomic rejection, print the tile map.`,
  },
  {
    key: 'storages',
    files: 'game/systems/storages.js (NEW, yours alone)',
    task: `Build COLLECTORS and STORAGES, the engine of the base economy.

Reference behaviour:
  - Collectors generate passively and must be COLLECTED manually. Alley Kingz already has producers
    GEM/MINT/FORGE/LAB/GEN in game/systems/production.js: read it and wrap or extend it, do NOT
    duplicate its accrual.
  - Storages hold banked resources and define the cap. The DISTRIBUTION ALGORITHM matters: resources
    spread EVENLY across all storages, and a lower-level storage fills first up to its reduced
    capacity. Implement that even distribution, because it is what makes storage upgrades feel
    meaningful and partial looting sensible.
  - The Town Hall itself stores a slice, lootable ONLY if the Town Hall is destroyed.
  - Capacity scales with Town Hall level and with storage building count/level.

In game/systems/storages.js:
  - capacityFor(p): total capacity per resource from real building levels.
  - distribute(p, resource, amount): the even-fill algorithm returning per-storage contents.
  - lootableFrom(p): split into storage-held vs collector-held vs town-hall-held, since those are
    looted at different rates (the loot lane consumes this).
  - overflow handling: cap deposits and report the waste so the UI can prompt a storage upgrade.
Use resources that actually exist: coins/gold, wood, stone, metal, produce, scrap tiers, bones, keys.
Do NOT invent currencies. Read game/economy.js for real field names.
Prove the distribution with a worked example and print the per-storage split.`,
  },
  {
    key: 'loot-math',
    files: 'game/economy.js ONLY',
    task: `Implement the LOOT MATH that makes raiding an economy rather than a slot machine.

Reference behaviour:
  - Loot is NOT a flat percentage. It is several pools each with its own rate and cap: a percentage of
    STORAGE contents, a much higher share (about 50%) of COLLECTOR contents, a small treasury slice,
    and a TOWN HALL pool obtained only if the Town Hall is destroyed.
  - The storage percentage FALLS as Town Hall rises (about 50% at TH1 down to about 10% at TH18) while
    the absolute CAP rises. That inverse relationship protects new players and keeps high-level
    raiding about volume rather than percentage.
  - A LOOT PENALTY applies when attacking a lower Town Hall, which stops strong players farming weak
    ones. Implement it as a multiplier by TH difference.

In game/economy.js implement and export on AK_ECON:
  - lootPoolsFor(defenderProfile) -> {storage, collector, townHall, total}
  - lootPenalty(attackerTH, defenderTH) -> multiplier
  - resolveLoot(defenderProfile, attackerTH, destructionPct, townHallDestroyed) -> final award
NOTE: game/systems/raidparams.js already defines maxLootPercent per TH (0.30 at TH1 to 0.75 at TH10)
used by the raid layer. Read it and RECONCILE rather than contradict: state which number wins and why,
because two different loot ceilings in one game is exactly the drift that has bitten this repo.
Prove with a table across TH1/5/10 showing pools, caps, penalty and final award.`,
  },
  {
    key: 'builders',
    files: 'game/systems/builders.js (NEW, yours alone)',
    task: `Build the BUILDER QUEUE, the pacing mechanism of the base game.

Reference behaviour:
  - A small number of builders (start 2, expandable to about 5). EACH upgrade occupies ONE builder for
    its whole duration. That scarcity is the real pacing lever, more than cost is.
  - Upgrade times range from seconds early to many days late.
  - Any timer can be skipped for premium currency on a NON-LINEAR curve: short remaining times cost
    disproportionately more per second, so skipping the last minutes is cheap absolutely but expensive
    per second.
  - Boost items exist (a potion multiplying builder speed for an hour, books that finish instantly).

In game/systems/builders.js:
  - builderCount(p) / freeBuilders(p) reading REAL values. economy.js already has effectiveBuilderCap
    and townHallPerks(lv).builders: read and wrap them, do not fork.
  - enqueue(buildingId, targetLevel): validate a free builder, validate the Town Hall cap (economy.js
    exposes buildingCap/canUpgradeBuilding from the AK-THCAP block: reuse it), charge cost, start timer.
  - jobs(p) / finishDue(now): the tick that lands upgrades. Landing must be IDEMPOTENT and must
    re-check the TH cap at landing time, so a Town Hall knocked down mid-build cannot land an over-cap
    building.
  - skipCost(remainingMs): the non-linear curve. Document the shape chosen and why.
  - applyBoost(mult, durationMs).
Prove: fill every builder, show the queue rejects the next job, land one, show the slot frees. Print
skip costs for 10 minutes / 6 hours / 3 days to show the curve is non-linear per second.`,
  },
  {
    key: 'shields',
    files: 'game/systems/shields.js (NEW, yours alone)',
    task: `Build SHIELDS, VILLAGE GUARD and the PERSONAL BREAK TIMER: the systems deciding when a player
can be attacked. Without these the base layer is unplayable, because an online player would be farmed
continuously.

Reference behaviour:
  - Shields granted automatically after being successfully raided, scaled by destruction (roughly 12h
    at 30 percent up to 16h at 90 percent).
  - Attacking while shielded BURNS shield time rather than being blocked, escalating per attack. That
    is what stops shields being a free farming window.
  - When a shield expires a shorter VILLAGE GUARD starts, during which you can attack freely without
    losing protection.
  - A PERSONAL BREAK TIMER forces a short offline window after a long unshielded online session, so
    players cannot stay online forever to dodge attacks.

In game/systems/shields.js implement all three as pure testable time math plus small persisted state
through AK_ECON.mutateProfile:
  - grantShieldFor(destructionPct) -> ms
  - shieldState(p, now) -> {shielded, guard, msLeft, canBeAttacked}
  - burnOnAttack(p) -> shield time consumed
  - breakTimer(p, now) -> whether a forced break applies
NOTE: game/systems/raid.js already has shieldUntil in p.raid and a shieldActive(p) helper, and
shop/shop.js sells raid shields. Read them and EXTEND that state rather than creating a second shield
system: two shield sources disagreeing would be a nasty bug.
Prove with a simulated timeline: raided at 65 percent, shield granted, attack twice showing the burn,
expire into guard, then trigger a forced break.`,
  },
  {
    key: 'garage-world',
    files: 'game/systems/garage.js ONLY (it already exists and is already loaded by index.html)',
    task: `Make the GARAGE an actual nested world, and make its edits REFLECT outward. This is the third
nested world alongside the base editor and the farm, and it is currently broken in a very visible way.

THE BUG: game/index.html:670 declares
  B('GARAGE','THE GARAGE','#7fc8ff',1140,560,170,104,'shop/shop.html#deck','deck builder')
so walking into THE GARAGE navigates to the SHOP DECK BUILDER. The operator's garage, the place his
rigs live, currently opens a card screen. Its only other mechanical existence is garageLootMult in
economy.js, a raid-loot multiplier.

YOU MAY NOT EDIT index.html. You do not need to. Use the pattern production.js already uses: it claims
the five producer buildings by returning true from onEnterBuilding in the AK_SYSTEMS registry, which
intercepts the walk-in BEFORE index.html's generic interior/url handling runs. Read
game/systems/production.js and copy that contract exactly.

BUILD, all inside game/systems/garage.js:
  1. ENTRY. Register onEnterBuilding and claim b.id === 'GARAGE' by returning true, then open the
     garage world. Confirm by reading index.html that claiming actually pre-empts the shop navigation,
     and quote the line that proves it. If it does NOT pre-empt, say so plainly and give the exact
     one-line index.html change instead: do not guess.
  2. THE WORLD. A garage view: the player's current rig centred on a lift, slowly rotating, with the
     8 part slots around it. Reuse what already exists rather than rebuilding:
       - game/systems/cameras/GarageCamera.js (already written and already loaded) for the turntable
       - model-viewer, self-hosted at assets/vendor/, for the 3D rig once a mesh exists
       - the rig's 2D art as the fallback when no mesh exists, so the garage works TODAY
     Drag a part onto a slot -> live stat preview showing the delta -> confirm to equip.
  3. THE REFLECTION, the part that matters most. Equipping a part must change the rig OUTSIDE the
     garage: on the world map and in raids. Expose a single resolver, e.g.
     AK_GARAGE.rigVisual(cardName) -> {model, decals, tint, mountPoints}
     and AK_GARAGE.rigStats(cardName) -> the final stat block, both derived from the SAME persisted
     state the garage edits. Everything outside reads through that resolver, so there is exactly one
     source of truth and the world cannot disagree with the garage. State in needs_from_others the
     exact call sites that should adopt it (the raid draw and the hub avatar draw in index.html).
  4. TEST DRIVE. A button that spawns the rig in a small test arena so the player can feel the tuning.
     If a full arena is out of scope, implement it as a stat readout plus a short scripted drive-by
     rather than a dead button, and say which you did.

Prove the entry claim by quoting the real index.html dispatch line, and prove rigStats/rigVisual by
equipping a real part and printing the before/after stat block from the REAL functions.`,
  },
  {
    key: 'sprite-pipeline',
    files: 'art/render_sprites.py (NEW), game/systems/spritesheet.js (NEW)',
    task: `Build the 3D-TO-SPRITE pipeline. This is how the tower defense stops using flat card photos and
starts looking 3D WITHOUT a 3D engine, exactly how Clash of Clans does it: models are pre-rendered
into 2D sprites, because mobile cannot run hundreds of real-time 3D units and because pre-rendered
frames keep battle replays deterministic.

WHAT EXISTS TO BUILD ON (verify each before using):
  - Two real animated GLBs: game/assets/models/bcardd.glb and jagged.glb, with idle/walk/run clips.
  - model-viewer self-hosted at game/assets/vendor/model-viewer.min.js, renders reliably.
  - e5 has headless Chromium at
    /home/ubuntu/.cache/ms-playwright/chromium-1228/chrome-linux/chrome
    and ffmpeg at ~/.cache/ms-playwright/ffmpeg-1011. Working flags: --no-sandbox --disable-gpu
    --use-gl=swiftshader --enable-unsafe-swiftshader. WebGL content needs waiting on model-viewer's
    real 'load' event; a fixed timeout renders BLANK (this was hit before, do not repeat it).

PART A, art/render_sprites.py: drive headless Chromium on e5 to render a GLB into a sprite atlas.
  - N camera angles around the model (8 or 16, parameterised) x M animation frames per clip.
  - Transparent background, consistent framing and scale across every cell so units do not jitter.
  - Emit a packed PNG atlas plus a JSON manifest (cell size, angle count, frame count, clip names,
    per-cell rect) so the runtime indexes it without guessing.
  - Deterministic paths: game/assets/sprites/units/<slug>_<clip>.png and .json.
  - Run it for real on bcardd.glb and report actual output: atlas dimensions, cell count, file size,
    and confirm the render is NOT blank by checking pixel variance, because a blank render still
    produces a valid PNG.

PART B, game/systems/spritesheet.js: the runtime that draws from those atlases.
  - load(slug): guarded async fetch of manifest plus image.
  - draw(g, slug, clip, angleRad, t, x, y, scale): nearest angle cell for the heading, right frame for
    the time, then blit. Falls back silently to existing card art when no atlas exists, so the battler
    is never broken by a missing sheet.
  - This is a texture-source change, NOT an architecture change: the battler keeps its 2D draw path.
Report honestly whether the e5 render actually worked, with numbers.`,
  },
]

const built = await parallel(LANES.map(L => () =>
  agent(`${RULES}
YOUR FILES (relative to ${ECO}): ${L.files}

TASK:
${L.task}`, { label: `build:${L.key}`, phase: 'Build', schema: SCHEMA })))

const ok = built.filter(Boolean)
log(`build: ${ok.length}/${LANES.length} lanes returned, ${ok.filter(b => b.parse_verified).length} parse-verified`)

phase('Verify')
const VS = {
  type: 'object',
  properties: {
    lane: { type: 'string' },
    parse_ok: { type: 'boolean' },
    integration_real: { type: 'boolean' },
    real_problems: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
  },
  required: ['lane', 'parse_ok', 'integration_real', 'real_problems', 'verdict'],
}

const verified = await parallel(ok.map(b => () =>
  agent(`Adversarially verify this Alley Kingz lane. REPO: ${ECO}. READ ONLY.

LANE: ${b.lane}
CLAIMED DONE: ${JSON.stringify(b.done)}
FILES: ${JSON.stringify(b.files_changed)}
CLAIMED INTEGRATION: ${b.integration_proof}
CLAIMED PARSE: ${b.parse_verified} (${b.parse_output})

REFUTE, do not agree:
1. Re-run every parse check yourself; report the REAL output.
2. Re-test behaviour against the REAL extracted functions, never the author's mocks.
3. Integration: a NEW module with no caller is acceptable ONLY if the lane gave the exact one-line
   include and that line is verifiably correct (right path, right load order relative to economy.js
   and _registry.js). Otherwise integration_real=false.
4. SHARED-STATE CHECK, the most important one: this layer exists so edits inside a nested world
   reflect in the outer 3D district. Confirm every lane reads and writes the EXISTING p.builds[] /
   profile schema used by buildmode.js and economy.js, and did NOT invent a parallel placement or
   currency store. A second source of truth here is a blocking defect.
5. Lane-specific traps:
   - loot-math: does it reconcile with raidparams.js maxLootPercent, or silently contradict it?
   - builders: is landing idempotent, and does it re-check the Town Hall cap at landing time?
   - shields: does it extend p.raid.shieldUntil / shieldActive rather than forking a second shield?
   - storages: does it wrap production.js accrual rather than duplicating it?
   - sprite-pipeline: did the e5 render ACTUALLY produce a non-blank atlas? Check pixel variance
     yourself; a blank render still writes a valid PNG and would silently ship empty sprites.
6. Hunt regressions: em-dashes, innerHTML, direct localStorage writes, invented currencies.
Default to FIX_FIRST when uncertain. verdict is SHIP or FIX_FIRST.`,
    { label: `verify:${b.lane}`, phase: 'Verify', schema: VS })))

const v = verified.filter(Boolean)
return {
  lanes: ok.map(b => ({ lane: b.lane, files: b.files_changed, integration: b.integration_proof, not_done: b.not_done || [], needs: b.needs_from_others || [] })),
  verdicts: v.map(x => ({ lane: x.lane, verdict: x.verdict, integration_real: x.integration_real, problems: x.real_problems })),
  ship_ready: v.filter(x => x.verdict === 'SHIP' && x.integration_real).map(x => x.lane),
  needs_fix: v.filter(x => x.verdict !== 'SHIP' || !x.integration_real).map(x => ({ lane: x.lane, problems: x.real_problems })),
}
