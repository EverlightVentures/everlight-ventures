from sld.evac import summarize, parse_safe_points, fetch_active_zones, fetch_safe_points


def test_summarize_active_zones():
    gj = {"type": "FeatureCollection", "features": [
        {"properties": {"ZONE_ID": "SOL-E123", "ZONE_NAME": "Green Valley",
                        "STATUS": "Evacuation Order", "COUNTY": "Solano",
                        "EVENT_TYPE": "Fire", "CRITICAL_INFO": "Leave now"}},
    ]}
    s = summarize(gj)
    assert s[0]["zone_id"] == "SOL-E123"
    assert s[0]["status"] == "Evacuation Order"
    assert s[0]["event"] == "Fire"


def test_fetch_active_zones_blue_sky_is_empty():
    gj = fetch_active_zones(fetch_fn=lambda: {"features": []})
    assert gj["features"] == []
    # tolerate a non-feature error payload
    gj2 = fetch_active_zones(fetch_fn=lambda: {"error": "x"})
    assert gj2["features"] == []


def test_parse_safe_points_sorts_by_distance():
    overpass = {"elements": [
        {"tags": {"name": "NorthBay Medical", "amenity": "hospital"}, "lat": 38.27, "lon": -122.05},
        {"tags": {"amenity": "police"}, "lat": 38.251, "lon": -122.041},
    ]}
    pts = parse_safe_points(overpass, 38.25, -122.04)
    assert pts[0]["kind"] == "police"        # closest
    assert pts[0]["name"] == "Police"        # unnamed -> kind title
    assert pts[1]["name"] == "NorthBay Medical"


def test_fetch_safe_points_survives_failure():
    def boom(lat, lon, r):
        raise RuntimeError("overpass down")
    assert fetch_safe_points(38.25, -122.04, fetch_fn=boom) == []
