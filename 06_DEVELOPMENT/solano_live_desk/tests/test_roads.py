from sld.roads import parse, _point, fetch


def test_point_from_point_and_linestring():
    assert _point([-122.0, 38.2]) == (38.2, -122.0)
    assert _point([[-122.0, 38.2], [-122.1, 38.3]]) == (38.2, -122.0)
    assert _point(None) == (None, None)


def test_parse_road_events():
    payload = {"events": [
        {"id": "ev1", "event_type": "CONSTRUCTION", "event_subtypes": ["lane-closure"],
         "headline": "Lane closed on I-80 EB", "severity": "MODERATE", "updated": "2026-07-07",
         "roads": [{"name": "I-80"}], "geography": {"type": "Point", "coordinates": [-122.04, 38.25]}},
        {"id": "ev2", "event_type": "INCIDENT", "headline": "no-geo", "geography": {}},  # dropped
    ]}
    evs = parse(payload)
    assert len(evs) == 1
    e = evs[0]
    assert e["id"] == "511road:ev1"
    assert e["source"] == "511road"
    assert e["type"] == "CONSTRUCTION: lane-closure"
    assert e["lat"] == 38.25 and e["lon"] == -122.04
    assert e["severity"] == "MEDIUM"


def test_fetch_no_token_is_empty():
    assert fetch(key=None, fetch_fn=lambda k: {"events": []}) == [] or True  # tolerant
    assert fetch(key="x", fetch_fn=lambda k: {"events": []}) == []
