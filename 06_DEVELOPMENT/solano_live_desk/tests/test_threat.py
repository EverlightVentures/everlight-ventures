from sld.threat import severity, proximity_ring, threat_level, classify


def test_severity_tiers():
    assert severity("Shots Fired at the mall") == "CRITICAL"
    assert severity("11-99 officer needs help") == "CRITICAL"
    assert severity("vehicle in active pursuit northbound") == "CRITICAL"
    assert severity("Injury collision two vehicles") == "HIGH"
    assert severity("FIRE-Report of Fire") == "MEDIUM"
    assert severity("Trfc Collision-No Inj") == "LOW"   # no-injury demotes
    assert severity("Traffic Hazard debris in lane") == "LOW"
    assert severity("WIND Advisory") == "LOW"


def test_proximity_rings():
    assert proximity_ring(0.3) == "IMMEDIATE"
    assert proximity_ring(1.0) == "NEAR"
    assert proximity_ring(3.0) == "AREA"
    assert proximity_ring(10.0) == "REGIONAL"
    assert proximity_ring(None) == "UNKNOWN"


def test_threat_matrix_corners():
    assert threat_level("CRITICAL", "IMMEDIATE") == "EXTREME"
    assert threat_level("CRITICAL", "REGIONAL") == "MEDIUM"
    assert threat_level("LOW", "REGIONAL") == "LOG"
    assert threat_level("HIGH", "NEAR") == "HIGH"


def test_heading_toward_bumps_one_level():
    assert threat_level("HIGH", "NEAR", heading_toward=True) == "EXTREME"
    assert threat_level("LOW", "REGIONAL", heading_toward=True) == "LOW"


def test_threat_level_unknown_distance_uses_severity_only():
    assert threat_level("CRITICAL", "UNKNOWN") == "HIGH"
    assert threat_level("LOW", "UNKNOWN") == "LOG"


def test_classify_shots_fired_near_user_is_extreme():
    ev = {"type": "Shots Fired", "title": "", "body": "", "lat": 38.251, "lon": -122.041}
    out = classify(ev, user_latlon=(38.25, -122.04))
    assert out["severity"] == "CRITICAL"
    assert out["ring"] == "IMMEDIATE"
    assert out["threat_level"] == "EXTREME"
    assert out["distance_mi"] < 0.5


def test_classify_without_user_location_is_severity_only():
    ev = {"type": "Traffic Hazard", "lat": 38.2, "lon": -122.0}
    out = classify(ev, user_latlon=None)
    assert out["distance_mi"] is None
    assert out["ring"] == "UNKNOWN"
    assert out["threat_level"] == "LOG"
