#!/usr/bin/env python3
"""
AK facade alpha-cut + roof tile pipeline.

WHY BORDER-CONNECTED FLOOD FILL AND NOT A LUMINANCE THRESHOLD
-------------------------------------------------------------
The naive fix is `alpha = 0 where luminance < T`. On town_hall.png that deletes
106k+ pixels of legitimate dark ART -- window mullions, door recesses, the black
outlines the whole hub style is built on -- because those pixels are exactly as
dark as the background. Measured: a global T=24 threshold alphas 55.4% of the
frame; the border-connected flood fill alphas 48.6%. That 6.8-point gap IS the
interior art, and a threshold eats it.

So: seed from the image border, flood only through pixels that are BOTH dark and
reachable from the edge without crossing art. Interior black stays opaque.

WHICH FILES QUALIFY
-------------------
Measured 2026-07-19 across all 18 facades referenced by world3d.js FACADE:
  town_hall.png   1024x1024  border luminance 0.0, 100% of border < 24  -> CUTOUT
  other 17        1248x1824  border luminance 32-72, 0.2-45.6% dark     -> FULL-BLEED
The 17 are painted storefront scenes: the border pixels are sky, asphalt and
brick, i.e. artwork. Cutting them produces holes in the picture, not a silhouette.
This script REFUSES them via qualifies() rather than damaging them, so the 3D
path falls through facadeCutUrl() -> 404 -> facadeUrl() and renders the original.
That 404 is by design (world3d.js:406-416). Do not "fix" it.

Originals are NEVER overwritten. Output is always <name>_cut.png alongside.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
HUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'hub')

# Mirrors systems/world3d.js FACADE (and index.html:567 FAC). Keep all three in sync.
FACADE = ['town_hall','trophy','fixer','garage','drop','kennel','clan','pass','wardrobe',
          'archive','street','arcade','gem_mine','gold_mint','card_forge','research_lab',
          'power_gen','infirmary']

DARK = 24          # luminance below which a pixel may be background
BORDER_DARK_MIN = 0.90   # >=90% of the border must be dark to call it a cutout


def luminance(rgb):
    return 0.299*rgb[:,:,0] + 0.587*rgb[:,:,1] + 0.114*rgb[:,:,2]


def border_dark_frac(lum):
    b = np.concatenate([lum[0,:], lum[-1,:], lum[:,0], lum[:,-1]])
    return float((b < DARK).mean())


def qualifies(lum):
    """A file is a cutout only if its frame is essentially all background."""
    return border_dark_frac(lum) >= BORDER_DARK_MIN


def background_mask(lum):
    """Border-connected dark region. 4-connected so a 1px diagonal seam of art
    is enough to protect an interior pocket -- deliberately conservative."""
    dark = lum < DARK
    lab, n = ndimage.label(dark, structure=ndimage.generate_binary_structure(2, 1))
    if n == 0:
        return np.zeros_like(dark)
    edge = np.concatenate([lab[0,:], lab[-1,:], lab[:,0], lab[:,-1]])
    keep = set(int(v) for v in np.unique(edge) if v)
    if not keep:
        return np.zeros_like(dark)
    return np.isin(lab, list(keep))


def cut(stem, write=True):
    src = os.path.join(HUB, stem + '.png')
    if not os.path.exists(src):
        return dict(stem=stem, status='MISSING')
    im = Image.open(src).convert('RGB')
    a = np.asarray(im).astype(np.float32)
    lum = luminance(a)
    bd = border_dark_frac(lum)
    if not qualifies(lum):
        return dict(stem=stem, status='SKIP_FULLBLEED', border_dark=bd,
                    size=im.size, alphaed=0.0)
    bg = background_mask(lum)
    thresh_would = float((lum < DARK).mean())
    alphaed = float(bg.mean())
    # Pixels a naive threshold would have destroyed but the flood fill preserved.
    interior_dark_saved = int(((lum < DARK) & ~bg).sum())
    if write:
        alpha = np.where(bg, 0, 255).astype(np.uint8)
        out = np.dstack([np.asarray(im).astype(np.uint8), alpha])
        dst = os.path.join(HUB, stem + '_cut.png')
        assert os.path.abspath(dst) != os.path.abspath(src), 'refusing to overwrite original'
        Image.fromarray(out, 'RGBA').save(dst)
    return dict(stem=stem, status='CUT', border_dark=bd, size=im.size,
                alphaed=alphaed, threshold_would=thresh_would,
                interior_dark_saved=interior_dark_saved)


def main():
    write = '--dry-run' not in sys.argv
    print('%-14s %-16s %7s %8s %8s %10s' % ('file','status','bord<24','alphaed','naiveT','saved_px'))
    for stem in FACADE:
        r = cut(stem, write=write)
        print('%-14s %-16s %6.1f%% %7s %8s %10s' % (
            r['stem'], r['status'], r.get('border_dark',0)*100,
            ('%.1f%%' % (r['alphaed']*100)) if r['status']=='CUT' else '-',
            ('%.1f%%' % (r['threshold_would']*100)) if r['status']=='CUT' else '-',
            r.get('interior_dark_saved','-')))

if __name__ == '__main__':
    main()
