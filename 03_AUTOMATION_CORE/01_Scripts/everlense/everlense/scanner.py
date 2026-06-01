import hashlib
from pathlib import Path
from typing import Optional
import exifread
from PIL import Image
from everlense import paths
from everlense.models import MediaItem

_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
_SOCIAL = {"whatsapp", "instagram", "messenger", "threads", "twitter", "facebook"}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_source(p: Path) -> str:
    parent = p.parent.name.lower()
    if parent == "screenshots":
        return "screenshot"
    if parent in _SOCIAL:
        return "social"
    return "camera"

def _dms_to_deg(values, ref) -> Optional[float]:
    try:
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        deg = d + m / 60.0 + s / 3600.0
        if ref in ("S", "W"):
            deg = -deg
        return round(deg, 6)
    except Exception:
        return None

def read_exif(p: Path):
    taken_at = None
    gps = None
    try:
        with open(p, "rb") as fh:
            tags = exifread.process_file(fh, details=False)
        dt = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if dt:
            raw = str(dt).strip()           # "2026:05:31 14:30:12"
            d, t = raw.split(" ", 1)
            taken_at = d.replace(":", "-") + "T" + t
        lat = tags.get("GPS GPSLatitude"); lat_ref = tags.get("GPS GPSLatitudeRef")
        lon = tags.get("GPS GPSLongitude"); lon_ref = tags.get("GPS GPSLongitudeRef")
        if lat and lon:
            la = _dms_to_deg(lat.values, str(lat_ref)); lo = _dms_to_deg(lon.values, str(lon_ref))
            if la is not None and lo is not None:
                gps = {"lat": la, "lon": lo, "from": "exif"}
    except Exception:
        pass
    try:
        with Image.open(p) as im:
            w, h = im.size
    except Exception:
        w = h = 0
    return taken_at, gps, w, h

def scan(known_hashes: set, sources=None) -> list[MediaItem]:
    sources = sources or (paths.dcim_sources() + paths.social_sources())
    out = []
    for root in sources:
        if not Path(root).exists():
            continue
        for p in sorted(Path(root).rglob("*")):
            if p.suffix.lower() not in _IMG_EXT or not p.is_file():
                continue
            digest = sha256_file(p)
            if digest in known_hashes:
                continue
            taken_at, gps, w, h = read_exif(p)
            out.append(MediaItem(str(p), digest, detect_source(p), taken_at, gps, w, h))
    return out
