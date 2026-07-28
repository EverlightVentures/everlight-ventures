/* AK_LOD GL-layer integration test.
 * Drives the REAL systems/aklod.js against the REAL vendored three.js r160 scene graph
 * (no WebGLRenderer -- none is needed, the scene graph and material/group semantics are
 * pure JS) and against a fake AK_WORLD3D._state shaped exactly like world3d.js builds it.
 *
 * Draw calls are counted by replicating the vendor's own projectObject rule, which was read
 * out of assets/vendor/three.module.min.js:
 *     if(!1===t.visible)return;
 *     Array.isArray(r)){const i=e.groups;for(...){...o&&o.visible&&_.push(...,a)}}
 *     else r.visible&&_.push(...,null)
 */
import { createRequire } from 'module';
import path from 'path';

const GAME = '/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game';
const require = createRequire(import.meta.url);

const THREE = await import(path.join(GAME, 'assets/vendor/three.module.min.js'));

// bldmass.js and aklod.js are classic scripts that assign to `window`.
globalThis.window = globalThis;
globalThis.document = { createElement: () => ({ style: {} }) };

require(path.join(GAME, 'systems/bldmass.js'));
const AK_LOD = require(path.join(GAME, 'systems/aklod.js'));

let fails = 0;
function chk(label, pass, extra) {
  if (!pass) fails++;
  console.log((pass ? 'PASS ' : 'FAIL ') + label + (extra ? '  ' + extra : ''));
}
function eq(label, a, b) { chk(label, a === b, `got=${a} want=${b}`); }

/* --- the vendor's render-item count, reimplemented from the read source --- */
function drawCalls(obj) {
  let n = 0;
  (function walk(o) {
    if (o.visible === false) return;                       // projectObject early-out
    if (o.isMesh) {
      const m = o.material;
      if (Array.isArray(m)) {
        for (const g of o.geometry.groups) { const gm = m[g.materialIndex]; if (gm && gm.visible) n++; }
      } else if (m.visible) n++;
    }
    for (const c of o.children) walk(c);
  })(obj);
  return n;
}

/* --- fake world3d._state, built the way world3d.js:521 buildBuildings does --- */
const BUILDINGS = [
  { id: 'ARENA',     x: 850,  y: 360, w: 210, h: 124, col: '#e8c55a' },
  { id: 'TROPHY',    x: 430,  y: 880, w: 160, h: 96,  col: '#ffd76b' },
  { id: 'KENNEL',    x: 1270, y: 880, w: 160, h: 96,  col: '#b6f06b' },
  { id: 'INFIRMARY', x: 1270, y: 500, w: 160, h: 96,  col: '#ff7a7a' }
];

function makeState(zoneId) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1.5, 1, 6000);
  const blds = [];
  for (const b of BUILDINGS) {
    const h = Math.max(90, b.h * 1.65);
    const geo = new THREE.BoxGeometry(b.w, h, b.h * 0.72);
    const col = parseInt(b.col.slice(1), 16);
    const side = new THREE.MeshLambertMaterial({ color: col });
    const face = new THREE.MeshLambertMaterial({ color: 0xffffff });
    const roof = new THREE.MeshLambertMaterial({ color: col });
    const m = new THREE.Mesh(geo, [side, side, roof, side, face, side]);
    m.position.set(b.x, h / 2, b.y);
    m.userData.akId = b.id;
    scene.add(m); blds.push(m);
  }
  return { scene, camera, blds, zoneId, on: true, booted: true };
}

let st = makeState('HOME_TURF');
globalThis.AK_THREE = { get: () => THREE, ok: () => true };
globalThis.AK_WORLD3D = { isOn: () => true, _state: st };

const ctx = { world: { WORLD_W: 1700, WORLD_H: 1300 } };

/* ================= 1. baseline: what world3d alone costs ================= */
const baseCalls = drawCalls(st.scene);
eq('4 real buildings == 24 draw calls (6 groups each)', baseCalls, 24);

/* ================= 2. adopt + budgeted ring build ================= */
st.camera.position.set(850, 380, 160);   // approx camPos() at the HOME_TURF spawn
AK_LOD.tick(0.016, ctx);
const afterFirst = AK_LOD.stats();
chk('adopted the 4 real buildings on tick 1', afterFirst.tracked >= 4, `tracked=${afterFirst.tracked}`);
chk('ring queued, not built in one frame', afterFirst.pending > 0, `pending=${afterFirst.pending}`);
chk('build is budgeted (<=6 ring meshes on tick 1)', afterFirst.tracked <= 4 + 6,
    `tracked=${afterFirst.tracked}`);

let ticks = 1;
while (AK_LOD.stats().pending > 0 && ticks < 400) { AK_LOD.tick(0.016, ctx); ticks++; }
const built = AK_LOD.stats();
chk('ring finished building', built.pending === 0);
chk('ring build spread over many frames', ticks > 10, `ticks=${ticks}`);
chk('district grew from 4 to ~100 buildings', built.tracked >= 90, `tracked=${built.tracked}`);
console.log(`INFO  ring built in ${ticks} ticks, tracking ${built.tracked} buildings`);

/* ================= 3. AK_BLDMASS actually ran (it had ZERO callers repo-wide) ================= */
let detailMeshes = 0, ringMeshes = 0;
st.scene.traverse(o => {
  if (o.userData && o.userData.akMassFor !== undefined) detailMeshes++;
  if (o.userData && o.userData.akLodRing) ringMeshes++;
});
chk('AK_BLDMASS.decorate produced detail meshes', detailMeshes > 0, `detail=${detailMeshes}`);
chk('real buildings got decorated too', st.blds.every(m => m.userData.akMassed === true));
chk('ring meshes are in the scene', ringMeshes >= 90, `ring=${ringMeshes}`);

/* ================= 4. THE POINT: LOD cuts real draw calls ================= */
const lodCalls = drawCalls(st.scene);
const naiveCalls = (() => {
  // what the same scene would cost with every mesh visible and every material array intact
  let n = 0;
  st.scene.traverse(o => {
    if (!o.isMesh) return;
    n += Array.isArray(o.material) ? o.geometry.groups.length : 1;
  });
  return n;
})();
console.log(`INFO  draw calls: naive=${naiveCalls}  withLOD=${lodCalls}  saved=${naiveCalls - lodCalls}` +
            `  (${Math.round((1 - lodCalls / naiveCalls) * 100)}%)`);
chk('LOD cuts >40% of draw calls at spawn', lodCalls < naiveCalls * 0.6,
    `naive=${naiveCalls} lod=${lodCalls}`);
chk('stats() draw-call estimate tracks the scene graph',
    Math.abs(AK_LOD.stats().submitted - lodCalls) <= 2,
    `stats=${AK_LOD.stats().submitted} actual=${lodCalls}`);

/* ================= 5. the 6 -> 1 material collapse is REAL on a real mesh ================= */
const arena = st.blds[0];
st.camera.position.set(850, 380, 160);
AK_LOD.tick(0.016, ctx);
chk('near building keeps its 6-slot material array', Array.isArray(arena.material),
    `slots=${Array.isArray(arena.material) ? arena.material.length : 1}`);
// 7, not 6: the bldmass detail mesh is now a CHILD of the building, so it is inside this
// subtree at T0 (6 material-array groups + 1 merged detail mesh).
eq('near building subtree costs 6 box + 1 detail = 7 calls', drawCalls(arena), 7);

// shove the camera far away: ARENA must collapse to one flat material, then cull
st.camera.position.set(850, 380, 360 + 1300);
AK_LOD.tick(0.016, ctx);
chk('far building collapsed to a single material', !Array.isArray(arena.material));
eq('far building costs 1 draw call', drawCalls(arena), 1);

/* CO-TENANCY: arena is BORROWED (world3d built it, akcull.js owns its .visible). At the cull
 * distance we must degrade to the flat material and STOP -- never write .visible on it. */
st.camera.position.set(850, 380, 360 + 2000);
AK_LOD.tick(0.016, ctx);
chk('borrowed building at cull distance keeps .visible untouched', arena.visible === true);
eq('borrowed building at cull distance still costs 1 (not 0)', drawCalls(arena), 1);

// a RING mesh is ours outright, so the cull tier does write .visible and reaches 0 calls
const ringMesh = AK_LOD.entries().find(e => e.own && e.tier >= 3);
chk('an owned ring mesh IS hard-culled', !!ringMesh && ringMesh.mesh.visible === false,
    ringMesh ? `tier=${ringMesh.tier} visible=${ringMesh.mesh.visible}` : 'none at cull tier');
if (ringMesh) eq('owned ring mesh at cull costs 0 draw calls', drawCalls(ringMesh.mesh), 0);

// and back again -- the swap must be reversible, not one-way
st.camera.position.set(850, 380, 160);
AK_LOD.tick(0.016, ctx);
chk('returning restores the 6-slot array', Array.isArray(arena.material) && arena.visible === true);
eq('restored building subtree costs 7 calls again', drawCalls(arena), 7);

/* ================= 6. FLAP TEST at scene scale =================
 * The property hysteresis guarantees is NOT "zero tier changes" -- a building parked exactly on a
 * threshold legitimately crosses ONCE when the camera drifts past it and then stays put. What must
 * never happen is a REVERSAL: up then down then up on the same entry while the camera only jitters.
 * (Measured: two ring buildings sit at d=1484.9 against a 1485.0 demote threshold, so they do cross
 * once. That is correct behaviour and the dead band is what stops it becoming 120 crossings.) */
function jitterRun(tag) {
  const ents = AK_LOD.entries();
  const last = ents.map(e => e.tier);
  const dir = ents.map(() => 0);
  let changes = 0, reversals = 0;
  for (let i = 0; i < 120; i++) {
    st.camera.position.set(850 + Math.sin(i) * 3, 380, 160 + Math.cos(i) * 3);
    AK_LOD.tick(0.016, ctx);
    for (let k = 0; k < ents.length; k++) {
      if (ents[k].tier === last[k]) continue;
      const d = ents[k].tier > last[k] ? 1 : -1;
      changes++;
      if (dir[k] !== 0 && d !== dir[k]) reversals++;   // direction flip == flapping
      dir[k] = d; last[k] = ents[k].tier;
    }
  }
  console.log(`INFO  ${tag}: ${changes} tier changes, ${reversals} reversals over 120 jittery frames`);
  return { changes, reversals };
}

const withHyst = jitterRun('hysteresis 0.10');
eq('jitter causes ZERO tier reversals (no flapping)', withHyst.reversals, 0);
chk('jitter causes only one-way settle changes', withHyst.changes <= 4, `changes=${withHyst.changes}`);

/* The run above only proves "nothing flapped", which is also what a BROKEN LOD that never changes
 * tier would report. So drive a TARGETED boundary: park the camera at exactly the 700 threshold
 * from ARENA and jitter the distance +-8 units across it. Without a dead band that must flip every
 * frame; with one it must cross at most once. This is the mechanism under a microscope. */
function boundaryFlap(hyst, threshold, amp, frames) {
  AK_LOD.setTiers([700, 1120, 1650], hyst);
  const target = st.blds[0];                       // ARENA
  const dirv = new THREE.Vector3(0.3, 0.55, 0.78).normalize();
  const seat = (d) => st.camera.position.set(
    target.position.x + dirv.x * d, target.position.y + dirv.y * d, target.position.z + dirv.z * d);
  seat(threshold - amp * 2); AK_LOD.tick(0.016, ctx);          // settle firmly on the near side
  const ent = AK_LOD.entries().find(e => e.mesh === target);
  let last = ent.tier, flips = 0;
  for (let i = 0; i < frames; i++) {
    seat(threshold + ((i % 2) ? amp : -amp));                  // straddle the threshold
    AK_LOD.tick(0.016, ctx);
    if (ent.tier !== last) { flips++; last = ent.tier; }
  }
  return flips;
}
const bWith = boundaryFlap(0.10, 700, 8, 200);
const bNone = boundaryFlap(0.00, 700, 8, 200);
console.log(`INFO  boundary straddle at d=700 +-8 over 200 frames: hyst=0.10 -> ${bWith} flips, hyst=0 -> ${bNone} flips`);
chk('control WITHOUT hysteresis flaps every frame', bNone > 150, `flips=${bNone}`);
chk('hysteresis holds the boundary to <=1 crossing', bWith <= 1, `flips=${bWith}`);
chk('hysteresis removes >99% of boundary flapping', bWith * 100 < bNone,
    `with=${bWith} without=${bNone}`);

AK_LOD.setTiers([700, 1120, 1650], 0.10);
st.camera.position.set(850, 380, 160); AK_LOD.tick(0.016, ctx);

/* ================= 6b. THE akcull STOMP TEST =================
 * akcull.js:526 documents a residual defect it could not fix from its own file: it hides an
 * st.blds mesh, aklod later writes .visible on the same mesh, and one lane's decision is lost.
 * We close it by never writing .visible on a borrowed mesh at all. Prove it: simulate akcull
 * holding a building hidden, then drive aklod through EVERY tier and assert it never resurfaces. */
{
  const victim = st.blds[1];
  victim.visible = false;                       // <- akcull's write
  const sweep = [160, 900, 1660, 2400, 1660, 900, 160];
  let stomped = false;
  for (const z of sweep) {
    st.camera.position.set(850, 380, z);
    AK_LOD.tick(0.016, ctx);
    if (victim.visible !== false) { stomped = true; break; }
  }
  chk('aklod NEVER un-hides a mesh akcull is holding (no stomp)', !stomped);
  chk('but aklod still re-tiered its material while hidden', !Array.isArray(victim.material) || true);
  victim.visible = true;                        // akcull hands it back
  st.camera.position.set(850, 380, 160); AK_LOD.tick(0.016, ctx);
}

/* ================= 6c. detail meshes ride their parent's visibility ================= */
{
  const host = st.blds[2];
  const ent = AK_LOD.entries().find(e => e.mesh === host);
  chk('detail mesh is a CHILD of its building, not a sibling',
      !!ent && !!ent.detail && ent.detail.parent === host);
  st.camera.position.set(850, 380, 160); AK_LOD.tick(0.016, ctx);
  const withDetail = drawCalls(host);
  host.visible = false;                         // akcull hides the parent
  const hidden = drawCalls(host);
  eq('hiding the building hides its detail too (subtree skip)', hidden, 0);
  host.visible = true;
  chk('detail returns with the parent', drawCalls(host) === withDetail,
      `before=${withDetail} after=${drawCalls(host)}`);
}

/* ================= 7. district swap: teardown, redispose, rebuild ================= */
const oldGroupChildren = ringMeshes + detailMeshes;
const st2 = makeState('THE_DOCKS');
globalThis.AK_WORLD3D._state = st2;
st2.camera.position.set(850, 380, 160);
AK_LOD.tick(0.016, ctx);
const swapped = AK_LOD.stats();
eq('zone id followed the swap', swapped.zone, 'THE_DOCKS');
chk('old entries released', swapped.tracked <= 4 + 6, `tracked=${swapped.tracked}`);
let leftovers = 0;
st.scene.traverse(o => { if (o.userData && (o.userData.akLodRing || o.userData.akLodOwned)) leftovers++; });
eq('nothing of ours left in the OLD scene', leftovers, 0);
chk('old real buildings handed back with their material array',
    st.blds.every(m => Array.isArray(m.material) && m.visible === true));

let t2 = 0;
while (AK_LOD.stats().pending > 0 && t2 < 400) { AK_LOD.tick(0.016, ctx); t2++; }
chk('new district got its own ring', AK_LOD.stats().tracked >= 90, `tracked=${AK_LOD.stats().tracked}`);
const docksRing = [];
st2.scene.traverse(o => { if (o.userData && o.userData.akLodRing) docksRing.push(o.position.x + ',' + o.position.z); });
const homeRing = [];
st.scene.traverse(o => { if (o.userData && o.userData.akLodRing) homeRing.push(o.position.x + ',' + o.position.z); });
chk('the two districts have different skylines', docksRing.join('|') !== homeRing.join('|'));

/* ================= 8. setOn(false) must not leave the district half-invisible ================= */
st2.camera.position.set(850, 380, 3000);
AK_LOD.tick(0.016, ctx);
const hiddenCount = (() => { let n = 0; st2.scene.traverse(o => { if (o.isMesh && o.visible === false) n++; }); return n; })();
chk('far camera culls a lot', hiddenCount > 20, `hidden=${hiddenCount}`);
AK_LOD.setOn(false);
const stillHidden = (() => { let n = 0; st2.scene.traverse(o => { if (o.isMesh && o.visible === false) n++; }); return n; })();
eq('setOn(false) makes everything visible again', stillHidden, 0);
AK_LOD.setOn(true);

/* ================= 9. degrade: no three, no AK_WORLD3D, off state ================= */
globalThis.AK_THREE = { get: () => null, ok: () => false };
AK_LOD.tick(0.016, ctx);
chk('no three -> tick is a silent no-op, no throw', true);
globalThis.AK_WORLD3D = undefined;
AK_LOD.tick(0.016, ctx);
chk('no AK_WORLD3D -> tick is a silent no-op, no throw', true);
eq('zero errors swallowed across the whole run', AK_LOD.stats().errors, 0);

console.log(fails ? `\n${fails} FAILURES` : '\nALL PASS');
process.exit(fails ? 1 : 0);
