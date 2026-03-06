"""
compress_upload.py - Shrink images in _uploads/ before hive processing.

Usage: python3 compress_upload.py [path_to_image]
       python3 compress_upload.py        (processes all images in _uploads/)

Prevents Errno 7 (arg list too long) and glibc malloc crashes caused
by passing large image data into subprocesses.
"""
import os
import sys
from pathlib import Path
from PIL import Image

UPLOADS_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_uploads")
MAX_BYTES = 800_000   # 800 KB target
MAX_DIM   = 1280      # max width or height


def compress(img_path: Path) -> Path:
    size_before = img_path.stat().st_size
    if size_before <= MAX_BYTES:
        print(f"  {img_path.name}: {size_before // 1024}KB -- already small, skipping")
        return img_path

    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    out_path = img_path.with_suffix(".compressed.jpg")
    quality = 80
    while quality >= 30:
        img.save(out_path, "JPEG", quality=quality, optimize=True)
        if out_path.stat().st_size <= MAX_BYTES:
            break
        quality -= 10

    size_after = out_path.stat().st_size
    print(f"  {img_path.name}: {size_before // 1024}KB -> {size_after // 1024}KB (q={quality})")
    return out_path


def main():
    targets = []
    if len(sys.argv) > 1:
        targets = [Path(sys.argv[1])]
    else:
        targets = list(UPLOADS_DIR.glob("*.jpg")) + list(UPLOADS_DIR.glob("*.png"))

    if not targets:
        print("No images found.")
        return

    for p in targets:
        if ".compressed." in p.name:
            continue
        try:
            compress(p)
        except Exception as e:
            print(f"  ERROR on {p.name}: {e}")


if __name__ == "__main__":
    main()
