"""Parsers for the key-gated sources (FIRMS, Windy, 511). Fetching is verified
live; these lock the normalization logic without needing network or keys."""
from sld.firms import parse_csv
from sld.webcams import parse as parse_webcams
from sld.transit import near as transit_near


def test_firms_parse_csv():
    csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,confidence,frp\n"
        "38.121,-121.375,320.5,0.4,0.4,2026-07-07,1012,n,0.42\n"
        "bad,row,,,,,,,\n"  # unparseable -> skipped
    )
    fires = parse_csv(csv)
    assert len(fires) == 1
    f = fires[0]
    assert f["source"] == "firms" and f["type"] == "Wildfire hotspot"
    assert f["lat"] == 38.121 and f["lon"] == -121.375
    assert f["severity"] == "MEDIUM"
    assert "0.42" in f["geo_label"]


def test_firms_empty_input():
    assert parse_csv("") == []
    assert parse_csv("no,header,here") == []


def test_webcams_parse():
    payload = {"webcams": [
        {"webcamId": 42, "title": "Downtown Fairfield", "status": "active",
         "location": {"latitude": 38.25, "longitude": -122.04},
         "images": {"current": {"preview": "https://x/p.jpg", "thumbnail": "https://x/t.jpg"}}},
        {"webcamId": 43, "title": "no-coords", "location": {}},  # dropped
    ]}
    cams = parse_webcams(payload)
    assert len(cams) == 1
    assert cams[0]["name"] == "Downtown Fairfield"
    assert cams[0]["image"] == "https://x/p.jpg"


def test_transit_near_filters_and_sorts():
    vehicles = [
        {"id": "b1", "route": "30", "lat": 38.251, "lon": -122.041},
        {"id": "b2", "route": "80", "lat": 39.5, "lon": -121.0},  # far
    ]
    close = transit_near(vehicles, 38.25, -122.04, radius_mi=30)
    assert [v["id"] for v in close] == ["b1"]
    assert close[0]["distance_mi"] < 1
