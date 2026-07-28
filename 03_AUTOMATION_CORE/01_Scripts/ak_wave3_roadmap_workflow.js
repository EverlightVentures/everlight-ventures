export const meta = {
  name: 'ak-wave3-roadmap',
  description: 'Alley Kingz Wave 3: self-host Three.js, FPS renderer swap for the Gulag, Clash-style isometric base builder, 3D district world, marketplace, battle pass, replay/spectator, and the 2026 atmosphere pass',
  phases: [
    { title: 'Build', detail: 'eight lanes, file ownership disjoint from the two running workflows' },
    { title: 'Verify', detail: 'adversarial, integration-gated' },
  ],
}

const ECO = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem'

const RULES = `
REPO: ${ECO}

CRITICAL FILE-OWNERSHIP NOTICE
TWO other workflows may still be running. You must NEVER touch these files:
  game/index.html, game/systems/hub3d.js, game/systems/defense.js, game/systems/worldverbs.js,
  game/systems/arcade.js, game/economy.js, game/canon.js, game/systems/needs.js,
  game/systems/cameras/*, game/systems/garage.js, unity_migration/cards.json, art/rig_bible.json,
  art/build_card_roster.py, art/build_rig_prompts.py
If your work needs a change in one of those, put the exact one-line change in needs_from_others and
move on. Editing them WILL destroy another agent's work.

HARD RULES
- You OWN only the files in YOUR FILES.
- NO em-dash characters anywhere. A write guard rejects them.
- NO innerHTML. A security hook rejects it. Build and clear DOM nodes with explicit DOM calls.
- Match surrounding style (var not let/const in game-loop code, terse, same comment density). Tag new
  blocks with a dated marker like the existing AK-XXXX 2026-07-18 comments.
- Guard EVERYTHING. No DOM or global access at module load. A module must be requireable in node.
- Persist ONLY through AK_ECON.mutateProfile. Direct localStorage writes caused a whole class of
  save-loss bugs in this repo and are banned.
- INTEGRATION IS THE BAR, NOT PARSING. Previous runs shipped code that parsed and that NOTHING
  CALLED. Quote the exact real call site (file:line) in integration_proof. If your lane creates a NEW
  module whose owner file is locked by another workflow, say so plainly and give the exact one-line
  include or call the orchestrator must add.
- NEVER verify with mocks you invented. A previous lane "proved" itself against self-written mocks
  and shipped a broken gate. Extract the REAL function from the REAL file and run it, or trace and
  quote a real call path.
- Parse-check before finishing: node --check for .js. Report the real output.
- Do NOT run ship.sh or any deploy. Do NOT git commit.
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
    key: 'three-host',
    files: 'game/assets/vendor/ (Three.js drop, yours), game/systems/three_boot.js (NEW, yours)',
    task: `FOUNDATION LANE. Three.js is NOT in this repo. Verified: grep for THREE., three.min.js and
OrbitControls returns nothing outside game/assets/vendor/model-viewer.min.js, which bundles a private
copy and does NOT expose a THREE global. The 3D world, the FPS view and the isometric builder are all
blocked on this.

Do this:
  1. Self-host Three.js under game/assets/vendor/, exactly the way model-viewer is already served
     (that file is 913KB, self-hosted, loaded as type=module from index.html, and it replaced a CDN
     dependency after the CDN failing silently caused a fallback bug). Match that pattern: no CDN.
     Fetch a pinned version. If the sandbox has no network, say so plainly in not_done and instead
     deliver the loader plus exact install instructions and the expected file path and size.
  2. Write game/systems/three_boot.js: a tiny guarded bootstrapper exposing
     window.AK_THREE = { ready(): Promise, get(): THREE|null, ok(): bool }
     It must lazily load the vendor file ONCE, resolve for every caller, and NEVER throw if the file
     is missing. Every 3D consumer will call AK_THREE.ready() and degrade to its 2D path when ok() is
     false. This is what makes the 3D lanes safe to ship before the asset lands.
  3. Document the WebGL context budget. The device target is a phone, model-viewer already holds a
     live context for the hero, and hub3d pools more for allies. State the ceiling and how three_boot
     should share or coexist with model-viewer.
Prove it: require three_boot.js in node and show ok() returns false without throwing.`,
  },
  {
    key: 'fps-view',
    files: 'game/systems/modes.js ONLY',
    task: `FPS RENDERER SWAP for the Gulag. This is the single biggest felt change for the least work in
the whole roadmap, because THE GAME IS ALREADY BUILT.

Verified: openGulag() at game/systems/modes.js:985 is a complete, playable twin-stick mode with cover
blocks, line-of-sight gating, bullets, strafing AI and touch input. ONLY the renderer is 2D: it draws
to a flat overlay and the fit line is around modes.js:1085 (sc = min(vp.w/AW, vp.h/AH)).

In game/systems/modes.js ONLY:
  - Add a first-person render path for the Gulag while leaving the ENTIRE game logic untouched. The
    logic layer keeps owning positions, hits, AI and win conditions; you are only changing how it is
    drawn and how look-input maps to a camera.
  - Camera at eye height with yaw from touch-drag or pointer movement, weapon model in view space,
    recoil kick and muzzle flash on fire. Movement stays on the existing virtual stick.
  - Gate the whole thing behind window.AK_THREE (from the three-boot lane): if AK_THREE.ok() is false,
    fall through to the EXISTING 2D renderer unchanged. It must be impossible for a missing Three.js
    to break a mode that works today.
  - Reuse what exists: the cover blocks, LOS and bullet state are already computed, so render them,
    do not recompute. systems/juice.js is on disk and loaded: use it for hit feedback rather than
    writing new effects.
Report exactly which lines you changed and confirm the 2D path still runs when AK_THREE is absent.`,
  },
  {
    key: 'builder-view',
    files: 'game/systems/buildmode.js ONLY',
    task: `CLASH-OF-CLANS STYLE BASE BUILDER. The data model is DONE; only the camera and editor view are
missing. Do not rebuild what exists.

Verified in game/systems/buildmode.js: p.builds[] persistence through ctx.econ.mutateProfile, a 7
structure vocabulary (WALL/STONE/METAL/BARRICADE/PATH/GARDEN/PLANTER) with real sprites in
assets/sprites/struct_*.png, GRID = 64 with snap(), rotation 0-3 that swaps w/h consistently, timed
builder jobs with a Town-Hall builder cap, an installCollisionWrap() that injects completed solids
into AK_COLLISION.obstaclesFor, and a self-mounting button. What it does NOT have: a dedicated editor
view. Today you place structures while walking as your dog inside a 360px radius at the normal hub
camera. There is no zoom-out, no drag-to-move-existing, no camera detach, and zero isometric.

In game/systems/buildmode.js ONLY, add an EDIT MODE:
  - A detached camera with pan and pinch zoom, and 90 degree rotation snaps, drawn isometric.
  - A building palette; drag out a ghost preview with green/red placement validity; snap to the
    existing GRID; drop with a satisfying commit.
  - DRAG EXISTING STRUCTURES to reposition them, which is the main thing players expect and the one
    thing the current in-world placement cannot do.
  - Everything writes to the SAME p.builds[] through the SAME mutateProfile path, so the hub world
    and the raid defense read the identical state. That is the reflection pair: move a wall in the
    editor, it stands in the world.
  - Isometric projection belongs next to the existing drawStruct (around buildmode.js:1192). Keep the
    existing top-down draw for the in-world path and switch projection only in edit mode.
  - If AK_THREE is available use it, but the isometric view MUST work in Canvas2D alone. Do not make
    the builder depend on Three.js.
Prove the round trip: place a structure in edit mode, read p.builds[] back, confirm the same entry
would render in the world path.`,
  },
  {
    key: 'world3d',
    files: 'game/systems/world3d.js (NEW file, yours alone)',
    task: `3D DISTRICT WORLD, the largest conversion. Build it as an ADDITIVE renderer, never a rewrite of
the hub.

Context you must respect: the hub is Canvas2D and its camera is two lines (cam.x = me.x - W/2). The
single highest-leverage seam is AK_CTX.world.wx/wy in index.html (around 2992-2998): every one of the
~15 plugin systems draws through it, so it is ALREADY a camera interface that happens to implement a
trivial translate. 10 painted district ground plates exist (game/assets/maps, 406MB) and 29 building
facade PNGs (game/assets/hub). Two hero GLBs exist and hub3d.js already pins a live model-viewer over
the 2D canvas, which proves WebGL composites fine on the target device.

Create game/systems/world3d.js:
  - A Three.js scene per district: ground plane textured from the existing district plate, building
    meshes positioned from the EXISTING building data (start with box geometry, textured with the
    existing facade PNGs), and the hero GLB driven by the existing position and faceAngle values.
  - An orbit camera around the hero with drag to turn and pinch to zoom, clamped polar angle.
  - Expose a projection API shaped so that AK_CTX.world.wx/wy could delegate to it, which is the
    migration path that carries all 15 plugin systems onto the 3D camera at once. Document that
    exactly; do NOT edit index.html to do it, that file is locked.
  - Hard requirement: gate on window.AK_THREE.ok(). With Three.js absent the module must be a total
    no-op and the existing 2D hub must be untouched and unaware.
  - Keep a Canvas2D overlay path for HUD and the plugin systems, exactly as hub3d.js already proves in
    reverse.
Deliver the scene builder plus a pure, headless-testable projection core proven with real numbers.`,
  },
  {
    key: 'marketplace',
    files: 'game/systems/marketplace.js, game/systems/trading.js',
    task: `MARKETPLACE. This is wiring, not building: the ak-trading Supabase edge function is deployed
and both client files already exist.

In game/systems/marketplace.js and game/systems/trading.js ONLY:
  - Listing flow: list an item for sale with a price, cap active listings per player, expire after a
    duration, and take a percentage tax on sale.
  - Browse by category with sort and filter, matching the item taxonomy the backpack already uses
    (materials, currency, gear, cards). Read systems/backpack.js for that registry and reuse its
    categories rather than inventing a second taxonomy.
  - Price history: keep a rolling window per item and expose avg/min/max so a simple graph can be
    drawn later.
  - Barter offers (want-to-trade X for Y), since a pure gold market is thin at low population.
  - EVERY transaction must be server-verified through the existing ak-trading function. The client may
    never mint or destroy value on its own: read how drip.js does buy() (gold check, then server ack,
    THEN debit through mutateProfile) and follow that exact order.
  - Guard for signed-out players: degrade to a read-only browse rather than a hard sign-in wall. An
    auth wall in front of core content is a known problem in this codebase.
State honestly if ak-trading lacks an action you need, and name the exact action and payload required.`,
  },
  {
    key: 'battlepass',
    files: 'game/pass.js, game/systems/seasons.js',
    task: `BATTLE PASS and SEASONS. Also mostly wiring: pass.js plus the ak-pass edge function are live and
already call an atomic spend RPC correctly, and seasons.js has 6 week chapters with a PT day check-in.

In game/pass.js and game/systems/seasons.js ONLY:
  - A seasonal track with free and premium lanes, tier rewards, and XP progression fed by real play
    events. IMPORTANT: an audit found the duty rail feeds AKQuests.reportEvent with metrics the server
    rejects with a 400, so pass XP silently never lands. Read that path, use only metrics the server
    accepts, and report the exact allowlist change needed in needs_from_others if one is required.
  - Seasonal rewards must be cosmetic or currency, never power. This game already has a card-level and
    Town-Hall progression spine and selling power on top of it would break the raid fairness model.
  - Claim ledger stays server side. The client never grants its own tier.
  - AKSeasons is NOT loaded in game.html (verified: grep returns 0), so match-win Marks are never
    granted at all. Do not paper over that: state the exact include line game.html needs.
Prove the XP curve and tier unlock math with real numbers.`,
  },
  {
    key: 'replay',
    files: 'game/systems/replay.js (NEW file, yours alone)',
    task: `REPLAY AND SPECTATOR foundation. Be pragmatic: full live spectating needs concurrency this game
does not have yet, but REPLAY does not, and replay is the honest first step.

Create game/systems/replay.js:
  - Record a raid as a compact deterministic event log: wave spawns, player position samples, hits,
    loot pickups, extraction, outcome. Sample rates should keep a full raid small enough to store and
    share.
  - Deterministic playback that drives the SAME render path the live raid uses, so a replay looks
    identical rather than being a second renderer.
  - Free camera and timeline scrub (play, pause, speed) over the recorded log.
  - Export a highlight window (the last N seconds around a kill or the boss kill) shaped so
    systems/viral.js can turn it into its existing 9:16 clip with a ?ref= invite. viral.js already
    ships and is the only acquisition channel this project has, so make the handoff clean and say
    exactly what viral.js needs.
  - The raid difficulty core (systems/raidparams.js) is already pure and headless, which means a
    recorded raid can be re-simulated server side later. Keep your log format compatible with that.
  - Storage: keep replays local and capped, with explicit size limits. Do not add a backend.
Prove determinism: record a scripted sequence, play it back, and show the reconstructed state matches.`,
  },
  {
    key: 'atmosphere',
    files: 'game/systems/weather.js (NEW file, yours alone)',
    task: `2026 ATMOSPHERE PASS. Deliver the parts that work TODAY in Canvas2D and are ready to upgrade
when Three.js lands. Do not build anything that requires meshes that do not exist.

Create game/systems/weather.js:
  - A weather state machine per district: clear, rain, fog, storm, and district-flavoured variants
    (acid rain suits Factory Row, dust suits The Yards). Assets already exist:
    game/assets/icons/wx_rain.png, wx_fog.png, wx_storm.png, wx_sun.png. VERIFY each path on disk
    before referencing it.
  - Canvas2D rendering: layered rain streaks with parallax, drifting fog banks, lightning flash.
    Cheap enough for a phone: state your per-frame cost and cap particle counts.
  - Time of day: dawn, noon, dusk, night tint over the district, driven by real clock time in PT. Note
    that systems/raid.js already has a day/night cycle (CYCLE_MS, isNight()); READ it and drive from
    the same clock rather than inventing a competing one. Two disagreeing day cycles would be a bug.
  - GAMEPLAY HOOKS, so it is not only decoration: expose modifiers other systems can read, for example
    reduced visibility at night, slower movement in storms, faster crop growth in rain. Do not edit
    those consumers; export the modifiers and name the call sites in needs_from_others.
  - Volumetric fog and procedural animation are explicitly OUT OF SCOPE here because they need the 3D
    pipeline. Say so, and describe the upgrade path so the work is not lost.
Prove the cost: measure the particle budget and report actual numbers.`,
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
    degrades_safely: { type: 'boolean' },
    real_problems: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
  },
  required: ['lane', 'parse_ok', 'integration_real', 'real_problems', 'verdict'],
}

const verified = await parallel(ok.map(b => () =>
  agent(`Adversarially verify this Alley Kingz Wave 3 lane. REPO: ${ECO}. READ ONLY, do not edit.

LANE: ${b.lane}
CLAIMED DONE: ${JSON.stringify(b.done)}
FILES: ${JSON.stringify(b.files_changed)}
CLAIMED INTEGRATION: ${b.integration_proof}
CLAIMED PARSE: ${b.parse_verified} (${b.parse_output})

REFUTE, do not agree:
1. Re-run every parse check yourself and report the REAL output.
2. Re-test behaviour against the REAL extracted functions, never the author's mocks. If the author
   used invented mocks, redo it properly and say so.
3. DEGRADATION IS A BLOCKING CHECK for three-host, fps-view, builder-view and world3d: with
   window.AK_THREE absent or ok()===false, does the module no-op cleanly and leave the existing 2D
   path completely untouched? Actually require it in node with no THREE present and prove it does not
   throw. Set degrades_safely accordingly. A lane that breaks a working 2D mode is FIX_FIRST no
   matter how good the 3D path is.
4. Integration: does a real consumer reach this code? A NEW module with no caller is acceptable ONLY
   if the lane stated the exact one-line include/call needed AND that instruction is correct. Verify
   the instruction would actually work. Otherwise integration_real=false.
5. Confirm NO file owned by the other two running workflows was modified. Specifically check
   index.html, hub3d.js, defense.js, worldverbs.js, arcade.js, economy.js, canon.js, needs.js,
   cameras/*, garage.js. Any edit there is an automatic FIX_FIRST and must be called out loudly.
6. Hunt regressions: em-dashes, innerHTML, direct localStorage writes, unguarded DOM access at module
   load, asset paths that do not exist on disk, duplicated day/night or taxonomy systems, and any
   client path that mints or destroys value without a server ack.
Default to FIX_FIRST when uncertain. verdict is SHIP or FIX_FIRST.`,
    { label: `verify:${b.lane}`, phase: 'Verify', schema: VS })))

const v = verified.filter(Boolean)
return {
  lanes: ok.map(b => ({ lane: b.lane, files: b.files_changed, integration: b.integration_proof, not_done: b.not_done || [], needs: b.needs_from_others || [] })),
  verdicts: v.map(x => ({ lane: x.lane, verdict: x.verdict, integration_real: x.integration_real, degrades_safely: x.degrades_safely, problems: x.real_problems })),
  ship_ready: v.filter(x => x.verdict === 'SHIP' && x.integration_real).map(x => x.lane),
  needs_fix: v.filter(x => x.verdict !== 'SHIP' || !x.integration_real).map(x => ({ lane: x.lane, problems: x.real_problems })),
  blocked_on_three: v.filter(x => x.degrades_safely === false).map(x => x.lane),
}
