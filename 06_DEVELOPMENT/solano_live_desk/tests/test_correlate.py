from datetime import datetime, timedelta
from sld import correlate, store


def _now():
    return datetime.now(store.PT)


def _ev(id, type_, lat, lon, mins_ago=1, body=""):
    ts = (_now() - timedelta(minutes=mins_ago)).isoformat()
    return {"id": id, "source": id.split(":")[0], "type": type_, "title": type_,
            "body": body, "lat": lat, "lon": lon, "first_seen": ts, "last_seen": ts}


def test_lifecycle_live_vs_report():
    fresh = (_now() - timedelta(minutes=2)).isoformat()
    old = (_now() - timedelta(minutes=40)).isoformat()
    assert correlate.lifecycle_status(fresh) == "LIVE"
    assert correlate.lifecycle_status(old) == "REPORT"


def test_gunshot_inference_fuses_independent_sources():
    # scanner "shots fired" + a medical GSW run at the same spot + time -> one
    # CONFIRMED gunshot incident, no ShotSpotter.
    events = [
        _ev("scanner:1", "Scanner call: shots fired", 38.25, -122.04, body="shots fired at the plaza"),
        _ev("pulsepoint:1", "Medical", 38.251, -122.041, body="GSW, one victim"),
        _ev("chp:1", "Assist", 38.2505, -122.0405, body="units responding code 3"),
    ]
    inc = correlate.correlate(events)
    fused = [i for i in inc if i["inferred"]]
    assert len(fused) == 1
    g = fused[0]
    assert g["severity"] == "CRITICAL"
    assert g["tier"] == "CONFIRMED"       # 3 distinct sources
    assert g["confidence"] >= 0.85
    assert set(g["sources"]) == {"scanner", "pulsepoint", "chp"}


def test_unrelated_crash_stays_separate_and_denoised():
    events = [
        _ev("scanner:1", "Scanner call: shots fired", 38.25, -122.04, body="shots fired"),
        _ev("pulsepoint:1", "Medical", 38.251, -122.041, body="GSW victim"),
        _ev("chp:9", "Traffic Hazard", 38.60, -121.50, body="debris in lane"),  # far + low
    ]
    inc = correlate.correlate(events)
    # the LOW single-source crash 25mi away is de-noised out; only the gunshot fuses.
    assert all("corr:chp:9" != i["id"] for i in inc)
    assert any(i["inferred"] for i in inc)


def test_single_low_source_is_denoised():
    inc = correlate.correlate([_ev("chp:1", "Traffic Hazard", 38.25, -122.0, body="cones")])
    assert inc == []   # one low-severity source alone is not a command-center incident
