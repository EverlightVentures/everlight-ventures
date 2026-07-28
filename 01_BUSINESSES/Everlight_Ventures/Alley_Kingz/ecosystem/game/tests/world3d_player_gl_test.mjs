/* AK-PLR3D / AK-ENTRANCE integration test (operator bug 4).
 *
 * Drives the REAL systems/world3d.js against the REAL vendored three.js r160 scene graph. No
 * WebGLRenderer is constructed and none is needed -- the thing under test is whether player-built
 * structures from p.builds[] become geometry in the scene, and the scene graph is pure JS.
 *
 * WHY THIS FILE EXISTS AT ALL: the failure this repo keeps hitting is code nothing calls. The pure
 * selfTest() inside world3d.js proves the planner and the footprint maths, which is necessary and
 * not sufficient -- a planner can be perfect while the meshes are never added to anything. This
 * asserts on scene.children, i.e. on the only fact that puts a building on screen.
 *
 * Same harness idiom as tests/aklod_gl_test.mjs: real vendor module, classic scripts loaded through
 * createRequire against a globalThis window.
 *
 * Run: node tests/world3d_player_gl_test.mjs
 */
import { createRequire } from 'module';
import path from 'path';

const GAME = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';
const require = createRequire(import.meta.url);

const THREE = await import(path.join(GAME, 'assets/vendor/three.module.min.js'));

globalThis.window = globalThis;
/* three's ImageLoader reaches for createElementNS, not createElement. A stub missing it makes
 * TextureLoader.load THROW synchronously, which would look exactly like a broken build path. The
 * returned object swallows .src writes, so every texture simply never resolves -- which is also the
 * honest simulation of a 404 on the live edge, and the geometry must exist regardless. */
globalThis.document = {
  createElement: () => ({ style: {}, addEventListener() {}, removeEventListener() {} }),
  createElementNS: () => ({ style: {}, addEventListener() {}, removeEventListener() {} })
};

let fails = 0, checks = 0;
function chk(label, pass, extra) {
  checks++;
  if (!pass) fails++;
  console.log((pass ? 'PASS ' : 'FAIL ') + label + (extra !== undefined ? '  ' + extra : ''));
}
function eq(label, got, want) { chk(label, got === want, 'got=' + got + ' want=' + want); }

/* ---- fakes, shaped exactly like the real modules world3d reads through ---- */

// A profile with a small walled base in HOME_TURF plus one structure in another district, so the
// zone filter is exercised by the scene build and not only by the pure planner.
const PROFILE = {
  builds: [
    { type: 'WALL',      x: 640, y: 704, zone: 'HOME_TURF' },
    { type: 'WALL',      x: 704, y: 704, zone: 'HOME_TURF', rot: 1 },
    { type: 'STONE',     x: 768, y: 704, zone: 'HOME_TURF' },
    { type: 'PATH',      x: 640, y: 768, zone: 'HOME_TURF' },
    { type: 'PLANTER',   x: 576, y: 768, zone: 'HOME_TURF' },
    { type: 'GARDEN',    x: 512, y: 768, zone: 'HOME_TURF' },
    // No AK_BUILDMODE.STRUCT entry for this one. akinstance.js:824 `if (!def) continue` drops it
    // silently; world3d must fall through to the AK_GRID footprint and still raise a box.
    { type: 'STORAGE_GOLD', x: 448, y: 832, zone: 'HOME_TURF' },
    { type: 'METAL',     x: 900, y: 900, zone: 'DOWNTOWN' }
  ]
};
globalThis.AK_ECON = {
  loadProfile: () => JSON.parse(JSON.stringify(PROFILE)),
  mutateProfile: () => null
};

// Mirrors the real AK_BUILDMODE surface world3d reads: STRUCT + iso.structH.
const STRUCT_H = { wall: 46, barricade: 34, garden: 10, deco: 26 };
globalThis.AK_BUILDMODE = {
  STRUCT: {
    WALL:    { dw: 76, dh: 42, family: 'wall',   sprite: 'assets/sprites/struct_wall.png' },
    STONE:   { dw: 76, dh: 42, family: 'wall',   sprite: 'assets/sprites/struct_stone.png' },
    METAL:   { dw: 76, dh: 42, family: 'wall',   sprite: 'assets/sprites/struct_metal.png' },
    PATH:    { dw: 60, dh: 60, family: 'deco',   sprite: 'assets/sprites/struct_path.png' },
    GARDEN:  { dw: 58, dh: 46, family: 'garden', sprite: 'assets/sprites/struct_garden.png' },
    PLANTER: { dw: 42, dh: 42, family: 'deco', shape: 'circle', cr: 24, sprite: 'assets/sprites/struct_planter.png' }
  },
  iso: { structH: (def, type) => (type === 'PATH' ? 2 : ((def && STRUCT_H[def.family]) || 24)) }
};

globalThis.AK_THREE = { ok: () => true, get: () => THREE };

require(path.join(GAME, 'systems/akgrid.js'));    // supplies the footprint fallback for STORAGE_GOLD
require(path.join(GAME, 'systems/bldmass.js'));   // the massing decorator the tall pieces use
const W3D = require(path.join(GAME, 'systems/world3d.js'));

/* ---- stand up a scene the way boot() would, minus the WebGLRenderer ----
 * sharedRenderer() cannot succeed in node (no WebGL context), so boot() would bail before ever
 * reaching the build calls. Injecting the Scene through the published _state seam is the same
 * thing boot() does on line one of its own body. */
const st = W3D._state;
st.scene = new THREE.Scene();
st.zoneId = 'HOME_TURF';
st.booted = true;
st.on = true;

console.log('--- AK-PLR3D: player structures reach the scene graph ---');

const synced = W3D.syncPlayer();
chk('syncPlayer() reports it did work', synced === true, 'got=' + synced);

const stats = W3D.playerStats();
eq('district under test', stats.zone, 'HOME_TURF');
eq('not deferring: AK_INSTANCE is absent', stats.deferredToInstanceLane, false);

// THE assertion. Seven HOME_TURF structures, and the DOWNTOWN one must not be among them.
eq('every HOME_TURF structure became a mesh', stats.structures, 7);

const meshes = st.scene.children.filter(o => o.isMesh && o.userData && o.userData.akPlayerBuilt);
eq('meshes are really parented to the scene', meshes.length, 7);
chk('every one carries real geometry', meshes.every(m => !!(m.geometry && m.geometry.attributes.position)));
chk('none landed at the DOWNTOWN structure position',
    !meshes.some(m => Math.round(m.position.x) === 900 && Math.round(m.position.z) === 900));

/* Placement is authoritative -- a renderer that quantises a player's wall MOVES his base.
 * akgrid.js:456 flags exactly this on the round-trip it does not control. */
const wallA = meshes.find(m => Math.round(m.position.x) === 640 && Math.round(m.position.z) === 704);
chk('the first wall is at its authored x/y, unquantised', !!wallA);
if (wallA) {
  const bb = new THREE.Box3().setFromObject(wallA);
  const size = bb.getSize(new THREE.Vector3());
  eq('wall footprint width == buildmode dw', Math.round(size.x), 76);
  eq('wall footprint depth == buildmode dh', Math.round(size.z), 42);
  eq('wall height == buildmode STRUCT_H.wall', Math.round(size.y), 46);
  chk('wall stands ON the ground, not sunk through it', Math.abs(bb.min.y) < 1e-6, 'min.y=' + bb.min.y);
}

// A rotated wall must turn, and its world-space bounds must swap with it.
const wallB = meshes.find(m => Math.round(m.position.x) === 704 && Math.round(m.position.z) === 704);
chk('the rotated wall exists', !!wallB);
if (wallB) {
  const size = new THREE.Box3().setFromObject(wallB).getSize(new THREE.Vector3());
  eq('rot1 swaps the footprint in WORLD space', Math.round(size.x), 42);
  eq('rot1 depth in world space', Math.round(size.z), 76);
}

// The regression that akinstance's `if (!def) continue` would have caused.
const storage = meshes.find(m => Math.round(m.position.x) === 448 && Math.round(m.position.z) === 832);
chk('a type buildmode does not define STILL renders', !!storage);
if (storage) {
  const size = new THREE.Box3().setFromObject(storage).getSize(new THREE.Vector3());
  chk('...at a real AK_GRID footprint, not zero', size.x > 0 && size.z > 0,
      'w=' + size.x + ' d=' + size.z);
}

// PATH is the documented flat special case: it must not extrude like the rest of the deco family.
const pathTile = meshes.find(m => Math.round(m.position.x) === 640 && Math.round(m.position.z) === 768);
chk('the path tile exists', !!pathTile);
if (pathTile) {
  const size = new THREE.Box3().setFromObject(pathTile).getSize(new THREE.Vector3());
  eq('PATH stays flat at 2 units, not 26', Math.round(size.y), 2);
}

console.log('--- idempotence + the throttle ---');

// An unchanged base must do NOTHING on the next UNFORCED sync -- that is the path frame() takes
// 60x a second. If the signature compare were broken this would re-allocate every geometry in the
// district several times a second. plrAt is zeroed first so the 700ms throttle is not what is
// under test here; the signature compare is.
const before = st.scene.children.length;
st.plrAt = 0;
const again = W3D.syncPlayer(false);
eq('an unchanged base is a no-op', again, false);
eq('scene child count did not move', st.scene.children.length, before);

// ...and the throttle itself must hold the line between polls, so a changed profile still costs
// nothing until the next window opens.
st.plrAt = Date.now();
eq('the throttle short-circuits between polls', W3D.syncPlayer(false), false);

// A placement must actually appear.
PROFILE.builds.push({ type: 'WALL', x: 832, y: 704, zone: 'HOME_TURF' });
W3D.syncPlayer();
eq('placing a structure adds exactly one mesh', W3D.playerStats().structures, 8);

// ...and a demolish must actually remove it, with no orphan left behind in the graph.
PROFILE.builds.pop();
W3D.syncPlayer();
eq('demolishing removes it again', W3D.playerStats().structures, 7);
eq('no orphaned player meshes left in the scene',
   st.scene.children.filter(o => o.userData && o.userData.akPlayerBuilt).length, 7);

console.log('--- the stand-down handshake with akinstance.js ---');

// akinstance renders this same content better. Exactly one lane may draw it.
globalThis.AK_INSTANCE = { ok: () => true, builds: { sync() {}, stats() { return {}; } } };
W3D.syncPlayer();
eq('world3d stands down when the instanced lane is live', W3D.playerStats().structures, 0);
eq('...and says so', W3D.playerStats().deferredToInstanceLane, true);
eq('no player meshes left in the scene after standing down',
   st.scene.children.filter(o => o.userData && o.userData.akPlayerBuilt).length, 0);

delete globalThis.AK_INSTANCE;
W3D.syncPlayer();
eq('and takes over again if that lane goes away', W3D.playerStats().structures, 7);

console.log('--- AK-ENTRANCE: functional buildings are marked, background is not ---');

const zone = {
  id: 'HOME_TURF',
  buildings: [
    { id: 'ARENA',   label: 'TOWN HALL', col: '#e8c55a', x: 850,  y: 360, w: 210, h: 124, url: 'x', act: 'a' },
    { id: 'KENNEL',  label: 'KENNEL',    col: '#7fc8ff', x: 430,  y: 500, w: 160, h: 96,  url: 'y', act: 'b' },
    { id: 'TROPHY',  label: 'TROPHY',    col: '#ffd76b', x: 430,  y: 880, w: 160, h: 96,  url: 'soon' }
  ]
};
st.zoneId = '';                       // force setZone to accept the swap
W3D.setZone({ activeZone: zone, world: { WORLD_W: 1700, WORLD_H: 1300 } });

const authored = st.scene.children.filter(o => o.isMesh && o.userData && o.userData.akFunctional);
eq('every authored building is marked functional', authored.length, 3);
chk('hasBox() answers for a building that has one', W3D.hasBox('ARENA') === true);
chk('hasBox() is false for a building that does not exist', W3D.hasBox('NOPE') === false);

const doors = st.scene.children.filter(o => o.userData && o.userData.akDoor);
eq('door markers cost 2 draw calls for the whole district', doors.length, 2);
chk('door markers are instanced, not one mesh per building', doors.every(d => d.isInstancedMesh));
// TROPHY is 'soon' -- signposted but shut. Lighting its door would promise something that is not there.
eq('only the ENTERABLE buildings are lit', doors[0].count, 2);

// The three populations must be separable by a machine, which is the precondition for them being
// separable by eye: authored+enterable, player-built, and akworldgen backdrop.
const plr = st.scene.children.filter(o => o.userData && o.userData.akPlayerBuilt);
chk('a player structure is never marked functional',
    plr.every(m => !m.userData.akFunctional));
chk('an authored building is never marked player-built',
    authored.every(m => !m.userData.akPlayerBuilt));

console.log('--- district teardown leaks nothing ---');

const zone2 = { id: 'DOWNTOWN', buildings: [
  { id: 'DROP', label: 'THE DROP', col: '#ff8fae', x: 560, y: 560, w: 170, h: 104, url: 'z', act: 'c' }
] };
W3D.setZone({ activeZone: zone2, world: { WORLD_W: 1700, WORLD_H: 1300 } });
eq('the old district\'s door markers are gone',
   st.scene.children.filter(o => o.userData && o.userData.akDoor).length, 2);
eq('hasBox() forgets the previous district', W3D.hasBox('ARENA'), false);
eq('hasBox() knows the new one', W3D.hasBox('DROP'), true);
// DOWNTOWN owns exactly one structure in the fixture profile.
eq('the new district rebuilt ITS structures, not the old ones', W3D.playerStats().structures, 1);
const dm = st.scene.children.filter(o => o.userData && o.userData.akPlayerBuilt);
chk('and it is the DOWNTOWN one', dm.length === 1 &&
    Math.round(dm[0].position.x) === 900 && Math.round(dm[0].position.z) === 900);

console.log('\n' + (fails === 0 ? 'ALL PASS' : fails + ' FAILURE(S)') + '  (' + checks + ' checks)');
process.exit(fails === 0 ? 0 : 1);
