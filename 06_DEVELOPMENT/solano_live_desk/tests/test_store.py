from sld import store


def test_upsert_creates_then_updates(tmp_path):
    conn = store.connect(tmp_path, "2026_07_07")
    ev = {
        "id": "chp:GGCC:1", "source": "chp", "type": "x", "title": "t",
        "lat": 38.2, "lon": -122.0, "geo_label": "L", "body": "line1",
        "details": ["line1"],
    }
    store.upsert_event(conn, ev, "2026-07-07T07:35:00-07:00")
    ev["body"] = "line1\nline2"
    store.upsert_event(conn, ev, "2026-07-07T07:36:00-07:00")
    rows = store.get_events(conn)
    assert len(rows) == 1
    assert rows[0]["body"] == "line1\nline2"
    assert rows[0]["first_seen"] == "2026-07-07T07:35:00-07:00"
    assert rows[0]["last_seen"] == "2026-07-07T07:36:00-07:00"


def test_upsert_preserves_coords_when_later_none(tmp_path):
    conn = store.connect(tmp_path, "2026_07_07")
    base = {"id": "chp:GGCC:2", "source": "chp", "type": "x", "title": "t",
            "geo_label": "L", "body": "b", "details": []}
    store.upsert_event(conn, {**base, "lat": 38.2, "lon": -122.0}, "t1")
    store.upsert_event(conn, {**base, "lat": None, "lon": None}, "t2")
    rows = store.get_events(conn)
    assert rows[0]["lat"] == 38.2  # COALESCE keeps the known fix


def test_list_days(tmp_path):
    store.connect(tmp_path, "2026_07_06").close()
    store.connect(tmp_path, "2026_07_07").close()
    assert store.list_days(tmp_path) == ["2026_07_06", "2026_07_07"]
