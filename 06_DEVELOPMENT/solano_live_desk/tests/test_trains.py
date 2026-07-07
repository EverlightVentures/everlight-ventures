from sld.trains import parse, near


PAYLOAD = {
    "6": [{"trainID": "6-7", "trainNum": 6, "routeName": "California Zephyr",
           "lat": 38.25, "lon": -121.95, "heading": "W", "velocity": 55, "trainState": "Active"}],
    "531": [{"trainID": "531-7", "trainNum": 531, "routeName": "Capitol Corridor",
             "lat": 39.5, "lon": -121.5, "heading": "N", "velocity": 60, "trainState": "Active"}],
}


def test_parse_flattens_national_feed():
    trains = parse(PAYLOAD)
    assert len(trains) == 2
    assert {t["route"] for t in trains} == {"California Zephyr", "Capitol Corridor"}


def test_near_filters_and_sorts_by_distance():
    trains = parse(PAYLOAD)
    close = near(trains, 38.25, -121.98, radius_mi=60)
    assert len(close) == 1                       # only the Zephyr is within 60mi
    assert close[0]["route"] == "California Zephyr"
    assert close[0]["distance_mi"] < 5
