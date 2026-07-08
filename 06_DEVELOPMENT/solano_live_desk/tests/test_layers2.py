from sld.spacewx import parse_kp, status_for, fetch as swx_fetch
from sld.fema import parse as fema_parse, fetch as fema_fetch


def test_kp_parse_and_status():
    payload = [["time_tag", "Kp", "a", "b", "c"], ["2026-07-07 12:00:00", "6.33", "", "", ""]]
    assert parse_kp(payload) == 6.33
    s = status_for(6.33)
    assert s["alert"] is True and "GPS" in s["gps"]
    assert status_for(1.0)["level"] == "quiet"
    assert status_for(None)["level"] == "unknown"


def test_swx_fetch_degrades():
    assert swx_fetch(fetch_fn=lambda: [["h"], ["t", "8.0"]])["alert"] is True


def test_fema_parse_dedups():
    payload = {"DisasterDeclarationsSummaries": [
        {"disasterNumber": 4700, "declarationTitle": "WILDFIRE", "incidentType": "Fire",
         "state": "CA", "designatedArea": "Solano (County)", "incidentBeginDate": "2026-06-01T00:00:00.000Z"},
        {"disasterNumber": 4700, "declarationTitle": "WILDFIRE", "incidentType": "Fire",
         "state": "CA", "designatedArea": "Solano (County)", "incidentBeginDate": "2026-06-01T00:00:00.000Z"},
    ]}
    d = fema_parse(payload)
    assert len(d) == 1 and d[0]["type"] == "Fire"


def test_fema_fetch_survives_error():
    def boom(state, since):
        raise RuntimeError("fema down")
    assert fema_fetch(fetch_fn=boom) == []
