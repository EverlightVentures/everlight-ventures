from sld.quakes import parse, fetch_quakes, _severity_for

SAMPLE = {"features": [
    {"id": "nc123", "properties": {"mag": 4.2, "place": "5km NE of Napa, CA",
     "title": "M 4.2 - 5km NE of Napa", "time": 1751900000000},
     "geometry": {"coordinates": [-122.2, 38.3, 5.0]}},
]}


def test_parse_earthquake():
    q = parse(SAMPLE)[0]
    assert q["id"] == "usgs:nc123"
    assert q["source"] == "usgs"
    assert q["lat"] == 38.3 and q["lon"] == -122.2
    assert q["type"] == "Earthquake M4.2"
    assert q["severity"] == "HIGH"        # magnitude 4.2
    assert "Napa" in q["geo_label"]


def test_severity_thresholds():
    assert _severity_for(5.1) == "CRITICAL"
    assert _severity_for(4.0) == "HIGH"
    assert _severity_for(3.0) == "MEDIUM"
    assert _severity_for(1.0) == "LOW"
    assert _severity_for(None) == "LOW"


def test_fetch_uses_injected_fetch():
    q = fetch_quakes(38.25, -122.0, fetch_fn=lambda lat, lon: SAMPLE)
    assert len(q) == 1 and q[0]["severity"] == "HIGH"
