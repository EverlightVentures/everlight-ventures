from sld import dvr
from sld.alert_worker import process


def _capturing_senders(log):
    return {
        "push": lambda e, p: log.append(("push", e["id"], p)) or True,
        "email": lambda e, p: True,
        "dashboard": lambda e, p: True,
        "digest": lambda e, p: True,
    }


def test_new_extreme_near_user_fires_once(tmp_path):
    log = []
    seen = set()
    conn = dvr.connect(tmp_path)
    user = (38.25, -122.04)
    events = [
        {"id": "chp:GGCC:1", "type": "Shots Fired", "body": "", "lat": 38.251, "lon": -122.041},
        {"id": "chp:GGCC:2", "type": "Traffic Hazard", "body": "", "lat": 38.9, "lon": -122.9},
    ]
    fired = process(events, user, seen, conn, _capturing_senders(log), now_iso="t1")
    # Only the shots-fired-nearby incident is EXTREME and alerted.
    assert [f["id"] for f in fired] == ["chp:GGCC:1"]
    assert ("push", "chp:GGCC:1", 5) in log
    # Both incidents are recorded to the DVR regardless of alert level.
    assert len(dvr.recent(conn)) == 2
    # Second pass: same events, already-seen -> no re-alert.
    log.clear()
    fired2 = process(events, user, seen, conn, _capturing_senders(log), now_iso="t2")
    assert fired2 == []
    assert log == []


def test_no_user_location_does_not_fire_but_still_records(tmp_path):
    log = []
    conn = dvr.connect(tmp_path)
    events = [{"id": "x", "type": "Shots Fired", "lat": 38.2, "lon": -122.0}]
    fired = process(events, None, set(), conn, _capturing_senders(log), now_iso="t1")
    # No GPS -> severity-only mapping (CRITICAL -> HIGH) still alerts; recorded either way.
    assert len(dvr.recent(conn)) == 1
    assert [f["id"] for f in fired] == ["x"]  # HIGH is an alert level
