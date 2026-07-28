#!/usr/bin/env python3
"""
render_sprites.py -- AK-SPRITE3D 2026-07-18
3D-TO-SPRITE pipeline. Pre-renders an animated GLB into a 2D sprite atlas the
way Clash of Clans does it: models are baked into frames offline, so the phone
draws flat quads at runtime and battle replays stay deterministic (no GPU-timing
drift between a render on my phone and a render on someone else's).

WHAT IT DOES
  headless Chromium (playwright) -> <model-viewer> loads the GLB -> for every
  (angle, frame) pair we lock the camera, scrub the clip to an exact time, snap
  the camera with jumpCameraToGoal() so nothing is mid-tween, capture the cell,
  then PIL-composites every cell into ONE packed PNG atlas + a JSON manifest.

WHY EACH GUARD EXISTS (these were all hit for real, do not remove)
  * we wait on model-viewer's REAL 'load' event, never a fixed sleep. A fixed
    timeout renders a BLANK transparent PNG that still passes as a valid file.
  * camera radius + fieldOfView are read ONCE after framing and then FROZEN for
    every single cell. model-viewer re-frames per model, and per-cell framing
    makes units visibly jitter/breathe as they turn.
  * jumpCameraToGoal() after every orbit change. Without it the camera eases
    toward the goal and each capture lands mid-tween -> smeared angles.
  * we supersample (--ss) and downscale in PIL. model-viewer at 128px is crunchy.
  * every cell gets a pixel-variance check. A blank render is a VALID png, so
    "the file exists" proves nothing.

OUTPUT (deterministic paths)
  game/assets/sprites/units/<slug>_<clip>.png
  game/assets/sprites/units/<slug>_<clip>.json

The manifest is consumed by game/systems/spritesheet.js. Keep the two in sync.

USAGE
  python3 art/render_sprites.py --glb game/assets/models/bcardd.glb --slug bcardd
  python3 art/render_sprites.py --glb ... --slug ... --angles 16 --frames 12 --cell 192
  python3 art/render_sprites.py --glb ... --slug ... --clips idle,walk --dry-run

Runs anywhere playwright + a chromium build exist. On e5:
  CHROME=/home/ubuntu/.cache/ms-playwright/chromium-1228/chrome-linux/chrome
"""

import argparse
import base64
import http.server
import io
import json
import os
import re
import socketserver
import sys
import threading

# ---------------------------------------------------------------- constants

# swiftshader flags: the ONLY combination verified to produce non-blank WebGL on
# e5 (no GPU). --enable-unsafe-swiftshader is required on modern chromium or the
# WebGL context is refused outright and every cell comes back empty.
CHROME_FLAGS = [
    '--no-sandbox',
    '--disable-gpu',
    '--use-gl=swiftshader',
    '--enable-unsafe-swiftshader',
    '--disable-dev-shm-usage',
    '--hide-scrollbars',
]

DEFAULT_CHROME = '/home/ubuntu/.cache/ms-playwright/chromium-1228/chrome-linux/chrome'

# repo-relative anchors, resolved from this file so cwd never matters
ART_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ART_DIR)
VENDOR_MV = os.path.join(REPO, 'game', 'assets', 'vendor', 'model-viewer.min.js')
OUT_DIR = os.path.join(REPO, 'game', 'assets', 'sprites', 'units')

# camera: phi 68deg = looking slightly DOWN at the unit, the Clash/isometric read.
# 90 would be dead-level eye height and units lose their ground footprint.
DEFAULT_PHI = 68.0


# ---------------------------------------------------------------- page

def build_page(glb_name, mv_name, px, phi, exposure):
    """The render harness page. Served over http so model-viewer can fetch the
    GLB with normal CORS rules (file:// trips fetch guards in chromium)."""
    return """<!doctype html>
<meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:transparent;}
  /* exact pixel box: model-viewer captures at its own CSS size, so any
     mismatch here silently rescales every cell */
  model-viewer{width:%(px)dpx;height:%(px)dpx;background-color:transparent;--poster-color:transparent;}
</style>
<script type="module" src="%(mv)s"></script>
<model-viewer id="mv"
  src="%(glb)s"
  camera-controls
  disable-zoom
  interaction-prompt="none"
  shadow-intensity="0"
  environment-image="neutral"
  exposure="%(exp)s"
  camera-orbit="0deg %(phi)sdeg auto"
  autoplay></model-viewer>
<script type="module">
  const mv = document.getElementById('mv');
  window.__akState = { loaded:false, error:null, clips:[], radius:null, fov:null };

  // REAL load event. Never a timer. A timer here is exactly how a previous run
  // shipped 64 perfectly-valid, perfectly-blank PNGs.
  mv.addEventListener('load', async () => {
    try {
      await mv.updateComplete;
      // let model-viewer finish auto-framing, THEN freeze what it chose so the
      // scale is identical in every cell
      const orbit = mv.getCameraOrbit();
      window.__akState.radius = orbit.radius;
      window.__akState.fov = mv.getFieldOfView();
      window.__akState.clips = (mv.availableAnimations || []).slice();
      mv.interpolationDecay = 0;      // no easing, camera snaps
      mv.pause();                     // we scrub currentTime by hand
      window.__akState.loaded = true;
    } catch (e) { window.__akState.error = String(e); }
  });
  mv.addEventListener('error', (e) => {
    window.__akState.error = 'model-viewer error: ' + (e && e.detail ? JSON.stringify(e.detail) : 'unknown');
  });

  // select a clip, return its duration so python can space the frames
  window.__akClip = async (name) => {
    if (name) mv.animationName = name;
    mv.pause();
    await mv.updateComplete;
    // AK-SPRITE3D 2026-07-19: WARM-UP after a clip switch. Setting animationName
    // re-binds the skinned mesh, and the FIRST poses evaluated after that bind
    // come back deformed -- the mesh reads broad from one yaw and edge-on (alpha
    // 0) from its neighbours, which is exactly the 6-blank-cell signature the
    // bcardd walk sheet hit on the first real run. Scrubbing a few poses and
    // letting them rasterize forces the bind to settle BEFORE cell 0 is captured.
    // Without this the damage lands in real cells and no amount of cropping gets
    // it back, because the pixels were never rendered.
    for (let i = 0; i < 4; i++) {
      mv.currentTime = (mv.duration || 1) * (i + 1) / 5;
      mv.pause();
      await mv.updateComplete;
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    }
    return mv.duration || 0;
  };

  // one cell: park the camera at yaw, scrub to t, snap, settle, capture.
  window.__akCell = async (yawDeg, t) => {
    // camera theta = -yaw: orbiting the CAMERA +theta makes the MODEL read as
    // -theta. We store the model's apparent yaw in the manifest, so invert here.
    mv.cameraOrbit = (-yawDeg) + 'deg ' + %(phi)s + 'deg ' + window.__akState.radius + 'm';
    mv.fieldOfView = window.__akState.fov + 'deg';
    mv.currentTime = t;
    mv.pause();
    mv.jumpCameraToGoal();            // no tween, no smear
    await mv.updateComplete;
    // two rAFs: one to commit the pose, one to guarantee it was rasterized
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    return mv.toDataURL('image/png');
  };
</script>
""" % {'px': px, 'mv': mv_name, 'glb': glb_name, 'phi': phi, 'exp': exposure}


# ---------------------------------------------------------------- helpers

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '_', str(s).lower()).strip('_') or 'clip'


def clampf(v, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def serve(root):
    """Tiny localhost static server. Bound to 127.0.0.1 per the network binding
    doctrine -- this is a build-time fixture, it must never be reachable."""
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=root, **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(('127.0.0.1', 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def alpha_bytes(img):
    return img.getchannel('A').tobytes()


def variance(img):
    """Mean absolute deviation of the ALPHA channel. Alpha is the honest signal:
    a blank transparent render is alpha=0 everywhere -> 0.0, and it cannot be
    faked by a flat-colored-but-present model the way an RGB check can."""
    px = alpha_bytes(img)
    if not px:
        return 0.0
    mean = sum(px) / len(px)
    return sum(abs(p - mean) for p in px) / len(px)


def coverage(img):
    """Fraction of pixels with meaningful alpha -- how much of the cell the unit
    actually fills. Near 0 = we rendered air (bad framing or a blank capture)."""
    px = alpha_bytes(img)
    return (sum(1 for p in px if p > 8) / len(px)) if px else 0.0


def union_box(imgs, pad):
    """ONE crop rectangle covering the subject across EVERY cell.

    model-viewer auto-frames with generous padding, so a raw capture wastes ~85%
    of each cell and the unit renders tiny next to today's card portraits. The
    naive fix (crop each cell to its own bbox) is WORSE: per-cell crops rescale
    the model every frame and it visibly pulses and jitters as it turns.

    So: union every cell's alpha bbox, square it about its center, pad, and apply
    that SAME box everywhere. Tight framing AND rock-steady scale."""
    l = t = 10 ** 9
    r = b = -1
    for im in imgs:
        bb = im.getchannel('A').getbbox()      # None when the cell is empty
        if not bb:
            continue
        l = min(l, bb[0]); t = min(t, bb[1]); r = max(r, bb[2]); b = max(b, bb[3])
    if r < 0:
        return None                            # every cell blank; caller reports it
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    half = max(r - l, b - t) / 2.0 * (1.0 + pad)
    # may extend past the capture edge on purpose: PIL crop zero-fills outside,
    # which for RGBA is transparent, so the subject stays centered either way
    return (int(round(cx - half)), int(round(cy - half)),
            int(round(cx + half)), int(round(cy + half)))


# ---------------------------------------------------------------- render

def render(glb, slug, angles, frames, cell, ss, phi, exposure, chrome, clips_want, dry,
           names=None, pad=0.06, trim_start=0.0, trim_end=0.0):
    from PIL import Image
    from playwright.sync_api import sync_playwright

    if not os.path.isfile(glb):
        sys.exit('missing glb: ' + glb)
    if not os.path.isfile(VENDOR_MV):
        sys.exit('missing model-viewer: ' + VENDOR_MV)

    # stage glb + vendor script into ONE served root so relative urls resolve
    import tempfile, shutil
    stage = tempfile.mkdtemp(prefix='ak_sprite_')
    shutil.copy(glb, os.path.join(stage, 'model.glb'))
    shutil.copy(VENDOR_MV, os.path.join(stage, 'mv.js'))
    cap = cell * ss
    with open(os.path.join(stage, 'index.html'), 'w') as f:
        f.write(build_page('model.glb', 'mv.js', cap, phi, exposure))

    httpd, port = serve(stage)
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []

    try:
        with sync_playwright() as p:
            launch = {'args': CHROME_FLAGS}
            if chrome and os.path.isfile(chrome):
                launch['executable_path'] = chrome
            browser = p.chromium.launch(**launch)
            page = browser.new_page(viewport={'width': cap + 32, 'height': cap + 32},
                                    device_scale_factor=1)
            errs = []
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.goto('http://127.0.0.1:%d/index.html' % port, wait_until='load')

            # THE load gate. 120s because a 13MB GLB decodes slowly under
            # swiftshader. If this times out the model genuinely did not load and
            # rendering anyway would only produce blanks.
            try:
                page.wait_for_function(
                    '() => window.__akState && (window.__akState.loaded || window.__akState.error)',
                    timeout=120000)
            except Exception:
                sys.exit('model never fired load (blank-render guard tripped). page errors: %s' % errs)

            state = page.evaluate('() => window.__akState')
            if state.get('error'):
                sys.exit('model-viewer error: %s' % state['error'])

            available = state.get('clips') or []
            print('[load] ok  clips=%s  radius=%.4f  fov=%.2f' %
                  (available or ['<none>'], state['radius'] or 0, state['fov'] or 0))

            clips = [c for c in (clips_want or available) if c in available] or available
            if not clips:
                clips = ['__static']          # rigless model: still worth an angle sheet
            # REAL clip names in our GLBs are Blender NLA exports ("NlaTrack",
            # "NlaTrack.001", ...), NOT idle/walk/run. --names remaps them
            # POSITIONALLY onto the names the runtime probes, so the output path
            # is bcardd_idle.png even though the track is called NlaTrack.002.
            def out_name(i, clip):
                if names and i < len(names) and names[i]:
                    return names[i]
                return 'idle' if clip == '__static' else clip

            if dry:
                print('[dry-run] would render clips=%s angles=%d frames=%d cell=%d'
                      % (clips, angles, frames, cell))
                for i, c in enumerate(clips):
                    d = page.evaluate('(n) => window.__akClip(n)', None if c == '__static' else c) or 0.0
                    print('    [%d] %-16s duration=%.3fs -> %s_%s'
                          % (i, c, d, slug, slugify(out_name(i, c))))
                return []

            step = 360.0 / angles
            for ci, clip in enumerate(clips):
                name = None if clip == '__static' else clip
                dur = page.evaluate('(n) => window.__akClip(n)', name) or 0.0
                nframes = 1 if (clip == '__static' or dur <= 0) else frames

                # ---- PASS 1: capture every cell at supersample size, full frame.
                shots = []
                # AK-SPRITE3D 2026-07-19: sample a SUB-RANGE of the clip. Blender
                # NLA exports routinely carry a blend-in at the head (and sometimes
                # a settle at the tail) that is not part of the loop. Trimming is
                # sampling-only: the window is still divided evenly and still
                # excludes its own end, so the sheet stays a clean loop.
                t0 = dur * clampf(trim_start, 0.0, 0.9)
                t1 = dur * (1.0 - clampf(trim_end, 0.0, 0.9))
                if t1 <= t0:
                    t0, t1 = 0.0, dur
                span = t1 - t0
                for fi in range(nframes):
                    # exclusive of the window end: frame N would duplicate frame 0
                    t = (t0 + span * fi / nframes) if nframes > 1 else t0
                    for ai in range(angles):
                        yaw = ai * step
                        data = page.evaluate('([y,t]) => window.__akCell(y,t)', [yaw, t])
                        raw = base64.b64decode(data.split(',', 1)[1])
                        shots.append((ai, fi, yaw, Image.open(io.BytesIO(raw)).convert('RGBA')))
                    print('  [%s] frame %d/%d  t=%.3f' % (clip, fi + 1, nframes, t))

                # ---- PASS 2: one shared crop box, then downscale into the atlas.
                box = union_box([s[3] for s in shots], pad)
                if box is None:
                    print('  !! every cell blank for clip %s -- skipping' % clip)
                    continue
                print('  [%s] shared crop %s from %dpx capture' % (clip, box, cap))

                atlas = Image.new('RGBA', (angles * cell, nframes * cell), (0, 0, 0, 0))
                cells, blanks, cov_sum = [], 0, 0.0
                for ai, fi, yaw, raw_im in shots:
                    im = raw_im.crop(box).resize((cell, cell), Image.LANCZOS)
                    v, cv = variance(im), coverage(im)
                    if v < 0.5 or cv < 0.005:
                        blanks += 1
                    cov_sum += cv
                    x, y = ai * cell, fi * cell
                    atlas.paste(im, (x, y))
                    cells.append({'a': ai, 'f': fi, 'x': x, 'y': y,
                                  'w': cell, 'h': cell,
                                  'yawDeg': round(yaw, 3)})
                shots = None

                cslug = slugify(out_name(ci, clip))
                png = os.path.join(OUT_DIR, '%s_%s.png' % (slug, cslug))
                jsn = os.path.join(OUT_DIR, '%s_%s.json' % (slug, cslug))
                atlas.save(png, 'PNG', optimize=True)

                man = {
                    'schema': 'ak.sprite.atlas/1',
                    'generator': 'art/render_sprites.py AK-SPRITE3D 2026-07-18',
                    'slug': slug, 'clip': cslug, 'source': os.path.basename(glb),
                    'image': os.path.basename(png),
                    'atlasW': atlas.width, 'atlasH': atlas.height,
                    'cell': cell, 'cols': angles, 'rows': nframes,
                    'angles': angles, 'angleStepDeg': round(step, 4),
                    'frames': nframes,
                    # duration is the SAMPLED span, not the source clip length:
                    # the runtime wraps t by this to pick a frame, so a trimmed
                    # sheet must report the trimmed length or playback runs slow
                    # and the loop seams in the wrong place.
                    'duration': round(span, 4),
                    'sourceDuration': round(dur, 4),
                    'trimStart': round(t0, 4), 'trimEnd': round(t1, 4),
                    'fps': round(nframes / span, 3) if span > 0 else 0,
                    # apparent model yaw of cell a=0. The runtime adds this before
                    # picking a cell, so facing can be corrected WITHOUT re-rendering.
                    'frontOffsetDeg': 0,
                    'phiDeg': phi,
                    'cropPad': pad,
                    'cells': cells,
                }
                with open(jsn, 'w') as f:
                    json.dump(man, f, separators=(',', ':'))

                print('[write] %s  %dx%d  cells=%d  blank=%d  avgCoverage=%.1f%%  %.0f KB'
                      % (os.path.basename(png), atlas.width, atlas.height,
                         len(cells), blanks, 100.0 * cov_sum / max(1, len(cells)),
                         os.path.getsize(png) / 1024.0))
                if blanks:
                    print('  !! %d/%d cells look BLANK -- do not ship this sheet'
                          % (blanks, len(cells)))
                written.append({'png': png, 'json': jsn, 'blanks': blanks,
                                'cells': len(cells), 'w': atlas.width, 'h': atlas.height,
                                'bytes': os.path.getsize(png)})
            browser.close()
    finally:
        httpd.shutdown()
        shutil.rmtree(stage, ignore_errors=True)
    return written


def main():
    ap = argparse.ArgumentParser(description='Bake an animated GLB into a sprite atlas.')
    ap.add_argument('--glb', required=True)
    ap.add_argument('--slug', required=True, help='output name, eg bcardd')
    ap.add_argument('--angles', type=int, default=8, help='camera yaws around the model (8 or 16)')
    ap.add_argument('--frames', type=int, default=8, help='samples per animation clip')
    ap.add_argument('--cell', type=int, default=128, help='px per atlas cell')
    ap.add_argument('--ss', type=int, default=2, help='supersample factor before downscale')
    ap.add_argument('--phi', type=float, default=DEFAULT_PHI, help='camera elevation deg')
    ap.add_argument('--exposure', default='1.0')
    ap.add_argument('--pad', type=float, default=0.06,
                    help='margin around the shared crop box, fraction of subject size')
    ap.add_argument('--clips', default='', help='comma list of GLB clip names, default = all')
    ap.add_argument('--names', default='',
                    help='comma list remapping clips POSITIONALLY to output names. '
                         'Our GLBs export Blender NLA tracks (NlaTrack, NlaTrack.001, ...) '
                         'so use eg --names idle,walk,run,attack to get bcardd_idle.png')
    ap.add_argument('--trim-start', type=float, default=0.0,
                    help='skip this FRACTION of the head of every clip. Blender NLA '
                         'exports often blend in over the first frames; sampling '
                         'through that bakes a deformed pose into real cells.')
    ap.add_argument('--trim-end', type=float, default=0.0,
                    help='skip this fraction of the tail of every clip')
    ap.add_argument('--chrome', default=os.environ.get('CHROME', DEFAULT_CHROME))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    want = [c.strip() for c in a.clips.split(',') if c.strip()]
    names = [c.strip() for c in a.names.split(',')] if a.names else None
    out = render(a.glb, a.slug, a.angles, a.frames, a.cell, a.ss, a.phi,
                 a.exposure, a.chrome, want, a.dry_run, names, a.pad,
                 a.trim_start, a.trim_end)
    bad = sum(o['blanks'] for o in out)
    print('\n== %d sheet(s), %d blank cell(s) ==' % (len(out), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
