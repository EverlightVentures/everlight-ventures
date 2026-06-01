from everlense import indexer
from everlense.models import PhotoRecord

def _rec(**kw):
    base = dict(sha256="h1", dest_path="/x/a.jpg", source="screenshot",
               category="Screenshots/Linux", project=None, taken_at="2026-05-31T10:00:00",
               gps_lat=None, gps_lon=None, address=None, ocr_text="sudo apt update",
               tags=[], stamped=False, filed_at="2026-05-31T10:01:00")
    base.update(kw); return PhotoRecord(**base)

def test_upsert_and_search(tmp_path):
    db = tmp_path / "idx.db"
    conn = indexer.connect(db)
    indexer.upsert(conn, _rec())
    indexer.upsert(conn, _rec(sha256="h2", category="Screenshots/AI", ocr_text="claude prompt"))
    rows = indexer.search(conn, "sudo")
    assert len(rows) == 1 and rows[0]["category"] == "Screenshots/Linux"
    rows = indexer.search(conn, "AI")            # category match
    assert any(r["sha256"] == "h2" for r in rows)

def test_upsert_is_idempotent(tmp_path):
    conn = indexer.connect(tmp_path / "idx.db")
    indexer.upsert(conn, _rec()); indexer.upsert(conn, _rec(category="Screenshots/Tech_Dev"))
    rows = indexer.search(conn, "Linux OR Tech_Dev")
    assert len([r for r in rows if r["sha256"] == "h1"]) == 1   # one row, updated
