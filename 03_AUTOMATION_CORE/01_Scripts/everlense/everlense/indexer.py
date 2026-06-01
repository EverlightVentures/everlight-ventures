import json
import sqlite3
from pathlib import Path
from everlense.models import PhotoRecord

def connect(db_path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS photos(
        sha256 TEXT PRIMARY KEY, dest_path TEXT, source TEXT, category TEXT,
        project TEXT, taken_at TEXT, gps_lat REAL, gps_lon REAL, address TEXT,
        ocr_text TEXT, tags TEXT, stamped INTEGER, filed_at TEXT)""")
    conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS photos_fts USING fts5(
        sha256 UNINDEXED, category, project, address, ocr_text, tags)""")
    conn.commit()
    return conn

def upsert(conn: sqlite3.Connection, r: PhotoRecord) -> None:
    conn.execute("""INSERT INTO photos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(sha256) DO UPDATE SET dest_path=excluded.dest_path, source=excluded.source,
        category=excluded.category, project=excluded.project, taken_at=excluded.taken_at,
        gps_lat=excluded.gps_lat, gps_lon=excluded.gps_lon, address=excluded.address,
        ocr_text=excluded.ocr_text, tags=excluded.tags, stamped=excluded.stamped, filed_at=excluded.filed_at""",
        (r.sha256, r.dest_path, r.source, r.category, r.project, r.taken_at, r.gps_lat, r.gps_lon,
         r.address, r.ocr_text, json.dumps(r.tags), int(r.stamped), r.filed_at))
    conn.execute("DELETE FROM photos_fts WHERE sha256=?", (r.sha256,))
    conn.execute("INSERT INTO photos_fts VALUES(?,?,?,?,?,?)",
        (r.sha256, r.category or "", r.project or "", r.address or "", r.ocr_text or "", " ".join(r.tags)))
    conn.commit()

def search(conn: sqlite3.Connection, query: str) -> list[dict]:
    hits = conn.execute("SELECT sha256 FROM photos_fts WHERE photos_fts MATCH ?", (query,)).fetchall()
    shas = [h["sha256"] for h in hits]
    if not shas:
        return []
    q = "SELECT * FROM photos WHERE sha256 IN (%s)" % ",".join("?" * len(shas))
    return [dict(row) for row in conn.execute(q, shas).fetchall()]
