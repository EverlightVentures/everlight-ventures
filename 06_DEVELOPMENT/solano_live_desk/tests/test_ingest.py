from pathlib import Path
from sld import ingest, store

FIX = Path(__file__).parent / "fixtures" / "sa_sample.xml"


def test_run_once_stores_solano_events(tmp_path):
    xml = FIX.read_text()
    n = ingest.run_once(
        lambda: xml, tmp_path, day="2026_07_07",
        now_iso="2026-07-07T07:35:00-07:00",
    )
    assert n == 1
    conn = store.connect(tmp_path, "2026_07_07")
    rows = store.get_events(conn)
    assert len(rows) == 1
    assert rows[0]["id"] == "chp:GGCC:0042"


def test_run_once_is_idempotent(tmp_path):
    xml = FIX.read_text()
    ingest.run_once(lambda: xml, tmp_path, day="2026_07_07", now_iso="t1")
    ingest.run_once(lambda: xml, tmp_path, day="2026_07_07", now_iso="t2")
    conn = store.connect(tmp_path, "2026_07_07")
    assert len(store.get_events(conn)) == 1  # same log id, no duplicate row
