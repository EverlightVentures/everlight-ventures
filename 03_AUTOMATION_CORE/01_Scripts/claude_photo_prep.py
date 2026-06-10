#!/usr/bin/env python3
"""
Prep a photo (or folder of photos) for Claude to Read without OOM-crashing.

Default: resize to <=1600px long edge, JPEG q85, strip EXIF (after rotating).
--full: copy the original to /tmp/claude_photos/ unchanged.

Prints machine-readable output paths on stdout, one per line, prefixed `PATH: `,
followed by a human summary. Designed to be called by the /photo slash command.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

OUT_DIR = Path("/tmp/claude_photos")
DEFAULT_MAX_EDGE = 1600
DEFAULT_QUALITY = 85
DEFAULT_BATCH = 5
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def _short_hash(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:10]


def _resize_one(src: Path, max_edge: int, quality: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{src.stem}_{_short_hash(src)}.jpg"
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(out, "JPEG", quality=quality, optimize=True)
    return out


def _passthrough(src: Path) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{src.stem}_{_short_hash(src)}{src.suffix.lower()}"
    shutil.copy2(src, out)
    return out


def _collect(target: Path, batch: int) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise FileNotFoundError(target)
    photos = [p for p in target.iterdir() if p.suffix.lower() in PHOTO_EXTS]
    photos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return photos[:batch]


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024  # type: ignore
    return f"{n:.0f} TB"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="Photo file or directory of photos")
    ap.add_argument("--full", action="store_true", help="Pass through original (no resize)")
    ap.add_argument("--max-edge", type=int, default=DEFAULT_MAX_EDGE)
    ap.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                    help=f"Max photos to process from a directory (default {DEFAULT_BATCH})")
    args = ap.parse_args()

    target = Path(args.target).expanduser()
    if not target.exists():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    try:
        sources = _collect(target, args.batch)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not sources:
        print(f"ERROR: no photo files in {target}", file=sys.stderr)
        return 2

    results: list[tuple[Path, Path, int, int]] = []
    errors: list[tuple[Path, str]] = []

    for src in sources:
        try:
            src_size = src.stat().st_size
            if args.full:
                out = _passthrough(src)
            else:
                out = _resize_one(src, args.max_edge, args.quality)
            out_size = out.stat().st_size
            results.append((src, out, src_size, out_size))
        except (UnidentifiedImageError, OSError) as e:
            errors.append((src, str(e)))

    for _, out, _, _ in results:
        print(f"PATH: {out}")

    print("", file=sys.stderr)
    print(f"Mode: {'PASSTHROUGH (full quality)' if args.full else f'RESIZED (<= {args.max_edge}px, q{args.quality})'}",
          file=sys.stderr)
    print(f"Processed: {len(results)}/{len(sources)} from {target}", file=sys.stderr)
    for src, out, src_size, out_size in results:
        ratio = (out_size / src_size * 100) if src_size else 0
        print(f"  {src.name}  {_fmt_size(src_size)}  ->  {out.name}  {_fmt_size(out_size)}  ({ratio:.0f}%)",
              file=sys.stderr)
    for src, err in errors:
        print(f"  SKIP {src.name}: {err}", file=sys.stderr)

    if not results:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
