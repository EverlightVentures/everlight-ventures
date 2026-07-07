from __future__ import annotations

# Approx county centroid, kept inside the bbox below.
SOLANO_CENTROID: tuple[float, float] = (38.25, -121.98)
# min_lat, min_lon, max_lat, max_lon
SOLANO_BBOX: tuple[float, float, float, float] = (38.0, -122.35, 38.55, -121.55)


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


def in_solano_bbox(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    mn_lat, mn_lon, mx_lat, mx_lon = SOLANO_BBOX
    return mn_lat <= lat <= mx_lat and mn_lon <= lon <= mx_lon
