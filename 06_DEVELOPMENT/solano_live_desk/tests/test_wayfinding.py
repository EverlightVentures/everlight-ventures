from sld.wayfinding import describe, parse_landmarks, where


def test_parse_landmarks_distance_and_direction():
    overpass = {
        "elements": [
            {"tags": {"name": "Wells Fargo", "amenity": "bank"}, "lat": 38.2503, "lon": -122.040},
            {"tags": {"amenity": "bank"}, "lat": 38.25, "lon": -122.04},  # no name -> skipped
        ]
    }
    lms = parse_landmarks(overpass, 38.2494, -122.0400)
    assert len(lms) == 1
    assert lms[0]["name"] == "Wells Fargo"
    assert lms[0]["dir"] == "N"          # landmark is due north of the point
    assert lms[0]["dist_m"] > 0


def test_describe_builds_readable_string():
    rev = {"address": {"road": "Texas St", "city": "Fairfield"}}
    lms = [{"name": "Wells Fargo", "dist_m": 120, "dir": "NE", "kind": "bank"}]
    assert describe(rev, lms) == "near Wells Fargo (~120m NE), on Texas St, Fairfield"


def test_describe_degrades_gracefully():
    assert describe({}, []) == "location unavailable"


def test_where_survives_fetch_failure():
    def boom(lat, lon):
        raise RuntimeError("overpass down")

    out = where(38.25, -122.04, reverse_fn=lambda a, b: {"address": {"road": "Main St"}}, landmarks_fn=boom)
    assert out["text"] == "on Main St"
    assert out["landmarks"] == []
