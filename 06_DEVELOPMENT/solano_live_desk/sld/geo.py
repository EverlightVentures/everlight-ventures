from __future__ import annotations

# Approx county centroid, kept inside the bbox below.
SOLANO_CENTROID: tuple[float, float] = (38.25, -121.98)
# min_lat, min_lon, max_lat, max_lon
# Strict Solano County box.
SOLANO_BBOX: tuple[float, float, float, float] = (38.0, -122.35, 38.55, -121.55)
# Driving-corridor box: Solano PLUS the Benicia Bridge and the I-80/I-680/Hwy-12
# approaches. Extended south to ~37.95 to catch the bridge span and the
# Hercules/Rodeo approach, west to -122.45 for the Hwy-37 / Sears Point stretch.
# Deliberately stops north of Dublin (~37.7) and San Jose (~37.3).
CORRIDOR_BBOX: tuple[float, float, float, float] = (37.95, -122.45, 38.60, -121.50)


def decode_latlon(raw: str | None) -> tuple[float | None, float | None]:
    """Decode a CHP sa.xml LATLON micro-degree pair.

    Values arrive as '"lat:lon"' integers in millionths of a degree, often
    wrapped in literal quotes. Longitude magnitude is returned as West (negative).
    '0:0', empty, or unparseable input returns (None, None).
    """
    if raw is None:
        return (None, None)
    s = raw.strip().strip('"').strip()
    if ":" not in s:
        return (None, None)
    a, b = s.split(":", 1)
    try:
        lat_i = int(a)
        lon_i = int(b)
    except ValueError:
        return (None, None)
    if lat_i == 0 and lon_i == 0:
        return (None, None)
    return (lat_i / 1_000_000, -abs(lon_i) / 1_000_000)


def _in_box(lat: float | None, lon: float | None, box: tuple[float, float, float, float]) -> bool:
    if lat is None or lon is None:
        return False
    mn_lat, mn_lon, mx_lat, mx_lon = box
    return mn_lat <= lat <= mx_lat and mn_lon <= lon <= mx_lon


def in_solano_bbox(lat: float | None, lon: float | None) -> bool:
    return _in_box(lat, lon, SOLANO_BBOX)


def in_corridor_bbox(lat: float | None, lon: float | None) -> bool:
    return _in_box(lat, lon, CORRIDOR_BBOX)
