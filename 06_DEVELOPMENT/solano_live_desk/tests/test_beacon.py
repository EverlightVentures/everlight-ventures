"""EPIRB-style distress beacon: activate, repeat-due, cancel."""
from sld import beacon


def test_activate_and_get(tmp_path):
    b = beacon.activate(str(tmp_path), "driverA", 38.25, -122.04, "taking on water", now=1000)
    assert b["active"] is True and b["lat"] == 38.25 and b["note"] == "taking on water"
    got = beacon.get(str(tmp_path), "driverA", now=1060)
    assert got["active"] is True and got["elapsed_s"] == 60


def test_refresh_keeps_original_start(tmp_path):
    beacon.activate(str(tmp_path), "driverA", 38.25, -122.04, now=1000)
    beacon.activate(str(tmp_path), "driverA", 38.30, -122.10, now=1200)  # moved, refreshed
    got = beacon.get(str(tmp_path), "driverA", now=1200)
    assert got["lat"] == 38.30 and got["elapsed_s"] == 200  # start time preserved


def test_cancel(tmp_path):
    beacon.activate(str(tmp_path), "driverA", 38.25, -122.04, now=0)
    beacon.cancel(str(tmp_path), "driverA")
    assert beacon.get(str(tmp_path), "driverA")["active"] is False
    assert beacon.get(str(tmp_path)) == []


def test_repeat_due_and_mark(tmp_path):
    T = 1_000_000.0  # epoch-like: elapsed since last_bcast=0 already exceeds REPEAT_S
    beacon.activate(str(tmp_path), "driverA", 38.25, -122.04, now=T)
    assert beacon.due_for_broadcast(str(tmp_path), now=T)             # never broadcast -> due now
    beacon.mark_broadcast(str(tmp_path), "driverA", now=T)            # first pulse sent
    assert beacon.due_for_broadcast(str(tmp_path), now=T + 100) == []           # not due yet
    assert beacon.due_for_broadcast(str(tmp_path), now=T + beacon.REPEAT_S)     # due again after interval


def test_multiple_active_beacons_listed(tmp_path):
    beacon.activate(str(tmp_path), "a", 38.2, -122.0, now=0)
    beacon.activate(str(tmp_path), "b", 38.3, -122.1, now=0)
    assert len(beacon.get(str(tmp_path))) == 2
