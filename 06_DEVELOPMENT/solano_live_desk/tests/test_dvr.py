from sld import dvr


def _ev(**kw):
    base = {"id": "chp:GGCC:9", "source": "chp", "type": "x", "severity": "LOW",
            "threat_level": "LOW", "lat": 38.2, "lon": -122.0}
    base.update(kw)
    return base


def test_record_new_then_update(tmp_path):
    conn = dvr.connect(tmp_path)
    assert dvr.record(conn, _ev(threat_level="LOW"), "t1") is True   # new
    assert dvr.record(conn, _ev(threat_level="EXTREME"), "t2") is False  # update
    rows = dvr.recent(conn)
    assert len(rows) == 1
    assert rows[0]["threat_level"] == "EXTREME"
    assert rows[0]["last_seen"] == "t2"


def test_recent_hides_cleared(tmp_path):
    conn = dvr.connect(tmp_path)
    dvr.record(conn, _ev(id="a"), "t1")
    dvr.record(conn, _ev(id="b"), "t1")
    conn.execute("UPDATE incidents SET cleared=1 WHERE id='a'")
    conn.commit()
    ids = {r["id"] for r in dvr.recent(conn)}
    assert ids == {"b"}
