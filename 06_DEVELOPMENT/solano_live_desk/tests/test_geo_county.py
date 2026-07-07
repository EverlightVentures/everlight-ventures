import math
from sld.geo_county import distance_mi, bearing, parse_county, county_for


def test_distance_zero():
    assert distance_mi((38.0, -122.0), (38.0, -122.0)) == 0


def test_distance_one_degree_lat_is_about_69mi():
    d = distance_mi((38.0, -122.0), (39.0, -122.0))
    assert 68 < d < 70


def test_bearing_north_and_east():
    assert abs(bearing((38.0, -122.0), (39.0, -122.0)) - 0) < 1      # due north
    assert abs(bearing((38.0, -122.0), (38.0, -121.0)) - 90) < 1     # due east


def test_parse_county():
    payload = {
        "County": {"FIPS": "06095", "name": "Solano County"},
        "State": {"FIPS": "06", "code": "CA", "name": "California"},
    }
    assert parse_county(payload) == {
        "fips": "06095",
        "county": "Solano County",
        "state": "CA",
    }


def test_county_for_uses_injected_fetch():
    fake = lambda lat, lon: {"County": {"FIPS": "06095", "name": "Solano County"}, "State": {"code": "CA"}}
    assert county_for(38.25, -122.04, fetch_fn=fake)["county"] == "Solano County"
