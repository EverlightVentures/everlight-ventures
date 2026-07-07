from sld.nws import parse_alerts, fetch_alerts


SAMPLE = {
    "features": [
        {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-122.0, 38.0], [-122.0, 38.2], [-121.8, 38.2], [-121.8, 38.0]]],
            },
            "properties": {
                "id": "urn:oid:2.49.abc",
                "event": "Red Flag Warning",
                "headline": "Red Flag Warning until 8 PM",
                "areaDesc": "Solano County",
                "effective": "2026-07-07T12:00:00-07:00",
                "severity": "Severe",
                "description": "Critical fire weather.",
            },
        }
    ]
}


def test_parse_alerts_normalizes_and_centroids():
    events = parse_alerts(SAMPLE)
    assert len(events) == 1
    ev = events[0]
    assert ev["id"] == "nws:urn:oid:2.49.abc"
    assert ev["source"] == "nws"
    assert ev["type"] == "Red Flag Warning"
    assert ev["geo_label"] == "Solano County"
    # centroid of the polygon corners
    assert -122.0 <= ev["lon"] <= -121.8
    assert 38.0 <= ev["lat"] <= 38.2


def test_parse_alerts_handles_missing_geometry():
    payload = {"features": [{"geometry": None, "properties": {"event": "Heat Advisory"}}]}
    ev = parse_alerts(payload)[0]
    assert ev["lat"] is None and ev["lon"] is None
    assert ev["type"] == "Heat Advisory"


def test_fetch_alerts_uses_injected_fetch():
    events = fetch_alerts(38.25, -122.04, fetch_fn=lambda lat, lon: SAMPLE)
    assert events[0]["type"] == "Red Flag Warning"
