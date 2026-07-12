"""Dispersed Egress scoring + ranking. Pure logic, all fetches injected."""
from sld import escape


# A short straight route (lon,lat pairs, OSRM geojson order) up Main St.
MAIN = {"type": "LineString", "coordinates": [[-122.05, 38.25], [-122.05, 38.26], [-122.05, 38.27]]}
# A parallel back road one block east.
BACK = {"type": "LineString", "coordinates": [[-122.04, 38.25], [-122.04, 38.26], [-122.04, 38.27]]}


def test_line_latlon_flips_order():
    assert escape._line_latlon(MAIN)[0] == (38.25, -122.05)


def test_near_line_hits_and_misses():
    line = escape._line_latlon(MAIN)
    assert escape._near_line((38.26, -122.05), line, 0.02) is True
    assert escape._near_line((38.26, -122.00), line, 0.02) is False


def test_angle_wraps():
    assert escape._angle(350, 10) == 20
    assert escape._angle(10, 350) == 20
    assert escape._angle(0, 180) == 180


def test_score_counts_controls_on_route_only():
    # two lights on Main, none near Back
    controls = [
        (38.26, -122.05, "traffic_signals"),
        (38.27, -122.05, "traffic_signals"),
        (38.26, -122.04, "stop"),
    ]
    s_main = escape.score_route(MAIN, 300, controls, [])
    s_back = escape.score_route(BACK, 300, controls, [])
    assert s_main["signals"] == 2 and s_main["stops"] == 0
    assert s_back["signals"] == 0 and s_back["stops"] == 1
    # Main's two lights cost more than Back's one stop
    assert s_main["adj_s"] > s_back["adj_s"]


def test_blocked_route_is_penalized_and_flagged():
    blockers = [(38.26, -122.05, "structure fire")]
    s = escape.score_route(MAIN, 300, [], blockers)
    assert s["blocked"] is True
    assert "structure fire" in s["avoids"]
    assert s["adj_s"] >= escape.BLOCK_PENALTY_S


def test_pick_dest_avoids_fleeing_toward_hazard():
    user = (38.25, -122.05)
    # north point (toward a hazard due north) vs a farther south point (away)
    pts = [
        {"name": "North Clinic", "lat": 38.30, "lon": -122.05, "distance_mi": 3.0},
        {"name": "South Shelter", "lat": 38.20, "lon": -122.05, "distance_mi": 3.5},
    ]
    hazard = {"lat": 38.35, "lon": -122.05}  # due north
    dest = escape._pick_dest(pts, user, hazard)
    assert dest["name"] == "South Shelter"  # do not flee into the fire
    # no hazard -> nearest
    assert escape._pick_dest(pts, user, None)["name"] == "North Clinic"


def test_plan_escape_recommends_the_clearer_route():
    def fake_safe(la, lo):
        return [{"name": "Kaiser", "lat": 38.27, "lon": -122.05, "distance_mi": 1.4}]

    def fake_osrm(la, lo, dla, dlo):
        return {"routes": [
            {"geometry": MAIN, "distance": 2200, "duration": 300},  # fastest raw, but light-heavy
            {"geometry": BACK, "distance": 2400, "duration": 330},  # slightly longer, clear
        ]}

    controls = [
        (38.26, -122.05, "traffic_signals"),
        (38.27, -122.05, "traffic_signals"),
        (38.255, -122.05, "traffic_signals"),
    ]
    out = escape.plan_escape(
        38.25, -122.05, base="store",
        osrm_fn=fake_osrm, controls_fn=lambda bbox: controls, blockers=[],
        safe_fn=fake_safe,
    )
    assert "error" not in out
    assert out["routes"][0]["recommended"] is True
    # the clear back road wins despite being longer raw
    assert out["routes"][0]["signals"] == 0
    assert "clearest way out" in out["routes"][0]["reason"]
    assert out["dest"]["name"] == "Kaiser"


def test_plan_escape_ranks_blocked_route_last():
    def fake_safe(la, lo):
        return [{"name": "Kaiser", "lat": 38.27, "lon": -122.05, "distance_mi": 1.4}]

    def fake_osrm(la, lo, dla, dlo):
        return {"routes": [
            {"geometry": MAIN, "distance": 2200, "duration": 300},
            {"geometry": BACK, "distance": 2600, "duration": 360},
        ]}

    # a crash sits on Main St -> Back should win even though it is slower raw
    blockers = [(38.26, -122.05, "collision")]
    out = escape.plan_escape(
        38.25, -122.05, base="store",
        osrm_fn=fake_osrm, controls_fn=lambda bbox: [], blockers=blockers,
        safe_fn=fake_safe,
    )
    assert out["routes"][0]["geometry"] == BACK
    assert out["routes"][0]["recommended"] is True
    assert out["routes"][-1]["blocked"] is True


def test_plan_escape_no_safe_point():
    out = escape.plan_escape(38.25, -122.05, base="store", safe_fn=lambda la, lo: [])
    assert out["error"]
