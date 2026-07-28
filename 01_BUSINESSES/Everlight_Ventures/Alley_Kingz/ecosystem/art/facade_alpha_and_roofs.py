#!/usr/bin/env python3
"""AK 3D-quality fix #4: facade alpha cuts + procedural roof textures.

Two jobs, both feeding game/systems/world3d.js buildBuildings():

1. CUT  Convert baked-black background to real alpha on facade PNGs that are
        genuine cutouts. Uses a border-connected flood fill, NOT a global
        luminance threshold -- a global threshold eats windows, shadows and
        outlines, which is exactly how this kind of pass usually ruins the art.
        Only images that MEASURE as cutouts are cut (see is_cutout()); the rest
        are full-bleed painted scenes and are left alone on purpose.

2. ROOF Generate tileable roof textures. BoxGeometry's +y face (material index
        2) was flat colour, and at the hub's 38-52 degree camera pitch the roof
        is one of the most visible faces of every building. Palette is the
        game's gritty night-alley range: dark desaturated greys/browns.

Run:  python3 art/facade_alpha_and_roofs.py
Out:  game/assets/hub/<name>_cut.png      (alpha-cut facades, originals untouched)
      game/assets/hub/roofs/roof_<kind>.png (tileable roof textures)
"""

import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HUB = os.path.join(ROOT, "game", "assets", "hub")
ROOFDIR = os.path.join(HUB, "roofs")

# Mirrors the FACADE map in game/systems/world3d.js:387.
FACADES = [
    "town_hall", "trophy", "fixer", "garage", "drop", "kennel", "clan", "pass",
    "wardrobe", "archive", "street", "arcade", "gem_mine", "gold_mint",
    "card_forge", "research_lab", "power_gen", "infirmary",
]

# Flood-fill threshold. Measured on town_hall the background is a hard plateau:
# 48.20% of pixels at luminance<6 rising to only 49.82% at <30, i.e. the black
# background and the darkest legitimate art are cleanly separated. 18 sits in
# that plateau, catching compression ringing at the silhouette edge without
# reaching into the art.
CUT_THRESHOLD = 18

# A cutout must have a large border-connected black region AND that region must
# be stable across thresholds (the plateau test). Painted scenes fail both.
CUTOUT_MIN_BG = 25.0     # percent of frame
CUTOUT_MAX_DRIFT = 6.0   # percent growth from thr 6 -> thr 30


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114


def border_connected(dark: np.ndarray) -> np.ndarray:
    """Flood fill the dark mask inward from every border pixel."""
    h, w = dark.shape
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if dark[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if dark[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    return seen


def is_cutout(lum: np.ndarray):
    """True when the image is art on a black background rather than a full scene."""
    lo = border_connected(lum < 6).mean() * 100
    hi = border_connected(lum < 30).mean() * 100
    return (hi >= CUTOUT_MIN_BG and (hi - lo) <= CUTOUT_MAX_DRIFT), lo, hi


def cut_facade(name: str):
    src = os.path.join(HUB, name + ".png")
    if not os.path.exists(src):
        return {"name": name, "status": "missing"}

    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    lum = luminance(rgb)

    cutout, lo, hi = is_cutout(lum)
    if not cutout:
        return {"name": name, "status": "scene", "bg_lo": lo, "bg_hi": hi,
                "size": im.size}

    bg = border_connected(lum < CUT_THRESHOLD)

    # Soft edge: blur the hard binary mask so the silhouette gets an anti-aliased
    # alpha ramp instead of a stair-stepped cutout, then re-harden the interior so
    # the blur cannot make solid art semi-transparent.
    alpha = ((~bg).astype(np.float32)) * 255.0
    soft = Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    alpha = np.asarray(soft).astype(np.float32)
    alpha[~bg & (alpha > 140)] = 255.0     # solid art stays fully opaque
    alpha[bg & (alpha < 96)] = 0.0         # deep background stays fully clear

    # De-matte the rim: edge pixels were composited against black, so they carry a
    # dark fringe. Unmultiply by alpha to recover the true colour, which stops the
    # cut silhouette from reading as a grey halo once it is over a lit 3D scene.
    edge = (alpha > 8) & (alpha < 250)
    if edge.any():
        a = (alpha[edge] / 255.0)[:, None]
        rgb[edge] = np.clip(rgb[edge] / np.maximum(a, 0.25), 0, 255)

    out = np.dstack([rgb.astype(np.uint8), alpha.astype(np.uint8)])
    dst = os.path.join(HUB, name + "_cut.png")
    Image.fromarray(out, "RGBA").save(dst)

    return {
        "name": name, "status": "cut", "dst": dst, "size": im.size,
        "pct_alphaed": float((alpha < 8).mean() * 100),
        "pct_partial": float(edge.mean() * 100),
        "interior_dark_kept": float(((lum < CUT_THRESHOLD) & ~bg).mean() * 100),
    }


# ---------------------------------------------------------------------------
# Roof textures
# ---------------------------------------------------------------------------

def _noise(rng, size, octaves=4):
    """Cheap tileable fBm via summed wrapped low-res lattices."""
    acc = np.zeros((size, size), np.float32)
    amp = 1.0
    total = 0.0
    for o in range(octaves):
        n = max(2, 2 ** (o + 2))
        lat = rng.random((n, n)).astype(np.float32)
        lat = np.vstack([lat, lat[:1]])
        lat = np.hstack([lat, lat[:, :1]])          # wrap for tileability
        img = Image.fromarray((lat * 255).astype(np.uint8)).resize(
            (size + 1, size + 1), Image.BICUBIC)
        acc += np.asarray(img).astype(np.float32)[:size, :size] / 255.0 * amp
        total += amp
        amp *= 0.5
    return acc / total


def _tint(base_h, gray):
    """Blend a 0..1 grayscale field toward an RGB base colour."""
    g = gray[:, :, None]
    return np.clip(np.array(base_h, np.float32)[None, None, :] * (0.55 + 0.9 * g), 0, 255)


# AK-ROOF-CONTRAST 2026-07-19: the first pass used pure high-frequency grain and it
# MEASURED near-flat on screen -- source luminance std 8.1 collapsed to 3.6 once the
# GPU minified a 256px texture onto a roof a few dozen pixels tall. Mipmapping averages
# fine noise away, so grain alone cannot stop a roof reading as flat colour. Everything
# below adds LOW-frequency structure (seams, patches, stains, edge grime) which survives
# minification because it is large relative to the texel footprint.

def _seams(size, spacing, width=2, strength=0.30, axis="both"):
    """Dark structural joint lines. Spacing must divide size to stay tileable."""
    m = np.zeros((size, size), np.float32)
    idx = np.arange(size)
    line = ((idx % spacing) < width).astype(np.float32)
    if axis in ("both", "y"):
        m = np.maximum(m, np.tile(line[:, None], (1, size)))
    if axis in ("both", "x"):
        m = np.maximum(m, np.tile(line[None, :], (size, 1)))
    return m * strength


def _patches(size, rng, n, lo=0.72, hi=1.28):
    """Rectangular repair patches, wrapped so the tile still repeats seamlessly."""
    m = np.ones((size, size), np.float32)
    for _ in range(n):
        pw = int(rng.integers(size // 8, size // 3))
        ph = int(rng.integers(size // 8, size // 3))
        x0 = int(rng.integers(0, size))
        y0 = int(rng.integers(0, size))
        f = float(rng.uniform(lo, hi))
        xs = (np.arange(x0, x0 + pw) % size)
        ys = (np.arange(y0, y0 + ph) % size)
        m[np.ix_(ys, xs)] *= f
    return m


def _stains(size, rng, strength=0.22):
    """Broad pooled-water / weathering blotches: the lowest frequency layer."""
    lat = rng.random((4, 4)).astype(np.float32)
    lat = np.vstack([lat, lat[:1]])
    lat = np.hstack([lat, lat[:, :1]])
    img = Image.fromarray((lat * 255).astype(np.uint8)).resize(
        (size + 1, size + 1), Image.BICUBIC)
    f = np.asarray(img).astype(np.float32)[:size, :size] / 255.0
    return 1.0 - (np.clip(f - 0.45, 0, 1) * strength * 3.0)


def roof_tar(size, rng):
    """Tar-and-gravel: the default flat commercial roof. Big felt sheets + seams."""
    g = _noise(rng, size, 5)
    grit = rng.random((size, size)).astype(np.float32)
    g = np.clip(g * 0.60 + grit * 0.20 + _noise(rng, size, 2) * 0.20, 0, 1)
    img = _tint((50, 48, 52), g)
    img *= _patches(size, rng, 5, 0.68, 1.30)[:, :, None]      # tar-paper sheets
    img *= _stains(size, rng, 0.26)[:, :, None]
    img *= (1.0 - _seams(size, 64, 3, 0.34, "y"))[:, :, None]  # rolled-sheet joints
    spec = rng.random((size, size)) > 0.985
    img[spec] = np.clip(img[spec] * 1.8, 0, 255)
    return np.clip(img, 0, 255)


def roof_gravel(size, rng):
    """Coarser, browner ballast, drifted into uneven depths."""
    g = np.clip(_noise(rng, size, 6) * 0.45 + rng.random((size, size)) * 0.25
                + _noise(rng, size, 2) * 0.30, 0, 1)
    img = _tint((66, 57, 47), g)
    img *= _patches(size, rng, 7, 0.66, 1.34)[:, :, None]      # bare/thick ballast
    img *= _stains(size, rng, 0.30)[:, :, None]
    spec = rng.random((size, size)) > 0.975
    img[spec] = np.clip(img[spec] * 1.6, 0, 255)
    return np.clip(img, 0, 255)


def roof_corrugated(size, rng):
    """Corrugated metal: ribbed, rust bloom, panel joints."""
    x = np.arange(size, dtype=np.float32)
    ribs = 0.5 + 0.5 * np.sin(x / size * np.pi * 2 * 16)      # 16 whole ribs -> tiles
    field = np.tile(ribs[None, :], (size, 1))
    grime = _noise(rng, size, 4)
    g = np.clip(field * 0.50 + grime * 0.30 + _noise(rng, size, 2) * 0.20, 0, 1)
    img = _tint((70, 74, 80), g)
    rust = np.clip(_noise(rng, size, 3) - 0.48, 0, 1) * 2.6    # bigger rust blooms
    img[:, :, 0] = np.clip(img[:, :, 0] + rust * 95, 0, 255)
    img[:, :, 1] = np.clip(img[:, :, 1] + rust * 34, 0, 255)
    img[:, :, 2] = np.clip(img[:, :, 2] - rust * 16, 0, 255)
    img *= (1.0 - _seams(size, 128, 4, 0.40, "y"))[:, :, None]  # panel overlaps
    img *= _stains(size, rng, 0.20)[:, :, None]
    return np.clip(img, 0, 255)


def roof_asphalt(size, rng):
    """Asphalt shingle: darkest of the set, strong course banding."""
    g = np.clip(_noise(rng, size, 6) * 0.40 + rng.random((size, size)) * 0.30
                + _noise(rng, size, 2) * 0.30, 0, 1)
    img = _tint((44, 42, 46), g)
    # shingle courses: real bands, not hairlines, so they survive minification
    y = np.arange(size, dtype=np.float32)
    band = ((y % 32) < 16).astype(np.float32)
    img *= (1.0 - band * 0.16)[:, None, None]
    img *= (1.0 - _seams(size, 32, 3, 0.34, "y"))[:, :, None]   # course edges
    img *= _patches(size, rng, 4, 0.74, 1.24)[:, :, None]
    img *= _stains(size, rng, 0.24)[:, :, None]
    return np.clip(img, 0, 255)


ROOF_KINDS = {
    "tar": roof_tar,
    "gravel": roof_gravel,
    "corrugated": roof_corrugated,
    "asphalt": roof_asphalt,
}


def build_roofs(size=256):
    os.makedirs(ROOFDIR, exist_ok=True)
    made = []
    for i, (kind, fn) in enumerate(sorted(ROOF_KINDS.items())):
        rng = np.random.default_rng(9100 + i)      # deterministic across runs
        img = fn(size, rng).astype(np.uint8)
        dst = os.path.join(ROOFDIR, "roof_%s.png" % kind)
        Image.fromarray(img, "RGB").save(dst)
        made.append({"kind": kind, "dst": dst, "size": (size, size),
                     "mean": float(img.mean())})
    return made


def main():
    print("== facade alpha cuts ==")
    cuts = [cut_facade(n) for n in FACADES]
    for r in cuts:
        if r["status"] == "cut":
            print("  CUT   %-14s %s  alphaed %.2f%%  soft-edge %.2f%%  interior-dark-kept %.2f%%"
                  % (r["name"], r["size"], r["pct_alphaed"], r["pct_partial"],
                     r["interior_dark_kept"]))
        elif r["status"] == "scene":
            print("  scene %-14s %s  (full-bleed art, no black background -- left alone)"
                  % (r["name"], r["size"]))
        else:
            print("  MISS  %-14s" % r["name"])

    print("== roof textures ==")
    for m in build_roofs():
        print("  ROOF  %-12s %s  mean-lum %.1f  -> %s"
              % (m["kind"], m["size"], m["mean"], os.path.relpath(m["dst"], ROOT)))

    n_cut = sum(1 for r in cuts if r["status"] == "cut")
    print("\ncut %d / %d facades; %d left as painted scenes"
          % (n_cut, len(cuts), sum(1 for r in cuts if r["status"] == "scene")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
