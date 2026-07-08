from __future__ import annotations

import glob
import json
import os
import time

from . import cameras
from .geo_county import distance_mi

# Rolling snapshot DVR: record the cameras nearest the operator every minute into
# a short ring buffer, so an incident can replay the ~5-min-before/after window.
# Stills only (Caltrans refreshes ~1-5 min); kept small + rotated hard.


def _framedir(base: str, cam_id: str) -> str:
    return os.path.join(base, "camframes", cam_id.replace("/", "_"))


def snapshot_once(base: str, lat: float, lon: float, n: int = 8) -> int:
    """Save the current image from the N nearest cameras. Returns frames saved."""
    import httpx

    saved = 0
    ts = int(time.time())
    for c in cameras.nearest(cameras.fetch_cameras(), lat, lon, n):
        url = c.get("image_url")
        if not url:
            continue
        d = _framedir(base, c["id"])
        os.makedirs(d, exist_ok=True)
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            if r.status_code == 200 and r.content:
                with open(os.path.join(d, f"{ts}.jpg"), "wb") as f:
                    f.write(r.content)
                meta = os.path.join(d, "meta.json")
                if not os.path.exists(meta):
                    json.dump({"id": c["id"], "name": c.get("name"), "lat": c["lat"], "lon": c["lon"]},
                              open(meta, "w"))
                saved += 1
        except Exception:  # noqa: BLE001
            pass
    return saved


def rotate(base: str, keep_sec: int = 1500) -> None:
    """Delete frames older than keep_sec (~25 min) so the buffer stays tiny."""
    now = time.time()
    for f in glob.glob(os.path.join(base, "camframes", "*", "*.jpg")):
        try:
            if now - int(os.path.basename(f)[:-4]) > keep_sec:
                os.remove(f)
        except Exception:  # noqa: BLE001
            pass


def window(base: str, lat: float, lon: float, center_ts: int,
           before: int = 300, after: int = 300) -> dict:
    """Frames from the recorded camera nearest (lat,lon) within [t-before, t+after]."""
    best = None
    best_d = 9e9
    for meta_p in glob.glob(os.path.join(base, "camframes", "*", "meta.json")):
        try:
            m = json.load(open(meta_p))
        except Exception:  # noqa: BLE001
            continue
        d = distance_mi((lat, lon), (m["lat"], m["lon"]))
        if d >= best_d:
            continue
        camdir = os.path.dirname(meta_p)
        frames = []
        for f in glob.glob(os.path.join(camdir, "*.jpg")):
            try:
                t = int(os.path.basename(f)[:-4])
                if center_ts - before <= t <= center_ts + after:
                    frames.append(t)
            except Exception:  # noqa: BLE001
                pass
        if frames:
            best_d = d
            best = (m, os.path.basename(camdir), sorted(frames))
    if not best:
        return {"camera": None, "frames": []}
    m, safe_id, frames = best
    return {
        "camera": {"id": m["id"], "name": m.get("name"), "distance_mi": round(best_d, 1)},
        "frames": [{"ts": t, "url": f"/api/camframe/{safe_id}/{t}"} for t in frames],
    }


def frame_path(base: str, safe_id: str, ts: str) -> str:
    return os.path.join(base, "camframes", safe_id, f"{ts}.jpg")
