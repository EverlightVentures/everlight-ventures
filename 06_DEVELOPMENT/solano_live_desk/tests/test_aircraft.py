from sld.aircraft import parse, classify


def test_classify():
    assert classify({"dbFlags": 1, "flight": "RCH123"}) == "military"       # mil flag
    assert classify({"flight": "REACH51"}) == "military"                    # mil callsign
    assert classify({"flight": "UAL245", "r": "N12345"}) == "commercial"    # airline callsign
    assert classify({"flight": "N707TE", "r": "N707TE"}) == "ga"            # N-number private
    assert classify({"flight": "", "r": "N4427R"}) == "ga"                  # no callsign


def test_parse_fields_and_emergency():
    payload = {"ac": [
        {"hex": "a1", "flight": "UAL245 ", "lat": 38.2, "lon": -122.0, "alt_baro": 30000,
         "gs": 420, "track": 95, "t": "B738", "r": "N1", "squawk": "1200", "dbFlags": 0},
        {"hex": "b2", "flight": "N911XX", "lat": 38.3, "lon": -122.1, "track": None,
         "true_heading": 180, "squawk": "7700", "dbFlags": 0},   # emergency
        {"hex": "c3", "lat": None, "lon": None},                 # no position -> dropped
    ]}
    acs = parse(payload)
    assert len(acs) == 2
    a = acs[0]
    assert a["flight"] == "UAL245" and a["kind"] == "commercial" and a["emergency"] is False
    assert a["track"] == 95
    b = acs[1]
    assert b["emergency"] is True     # 7700 squawk
    assert b["track"] == 180          # falls back to true_heading when track is None
