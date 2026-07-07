from fastapi.testclient import TestClient
from sld import api, store


def _seed(tmp_path):
    conn = store.connect(tmp_path, store.today_pt())
    store.upsert_event(
        conn,
        {"id": "chp:GGCC:1", "source": "chp", "type": "x", "title": "t",
         "lat": 38.2, "lon": -122.0, "geo_label": "L", "body": "b", "details": []},
        "2026-07-07T07:35:00-07:00",
    )
    conn.close()


def test_healthz():
    client = TestClient(api.app)
    assert client.get("/healthz").json() == {"ok": True}


def test_events_endpoint_returns_seeded(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    _seed(tmp_path)
    client = TestClient(api.app)
    body = client.get("/api/events").json()
    assert body["events"][0]["id"] == "chp:GGCC:1"


def test_events_missing_day_is_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    client = TestClient(api.app)
    body = client.get("/api/events?date=1999_01_01").json()
    assert body == {"date": "1999_01_01", "events": []}


def test_days_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("SLD_STORE", str(tmp_path))
    _seed(tmp_path)
    client = TestClient(api.app)
    assert store.today_pt() in client.get("/api/days").json()["days"]


def test_serves_index_html():
    client = TestClient(api.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "maplibre" in r.text.lower()
    assert 'id="map"' in r.text
