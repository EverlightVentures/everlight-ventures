"""Tests for dehashed_client.py -- mocked HTTP, no live key/credits needed."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dehashed_client as dc


_SAMPLE_PAYLOAD = {
    "balance": 999,
    "total": 2,
    "entries": [
        {"email": "rita.townsend@realmail.com", "name": "Rita Townsend",
         "phone": "9015551212", "address": "123 Real St, Memphis TN",
         "database_name": "SomeBreach2019"},
        {"email": "RITA.T@work.org", "name": "Rita M Townsend", "phone": ""},
        {"email": "junk@faisalman.com", "name": "Rita Townsend"},   # junk -> dropped
        {"email": "not-an-email", "name": "x"},                      # invalid -> dropped
        {"username": "ritarocks", "name": "Rita"},                  # no email -> skipped
    ],
}


def _set_key(monkeypatch, v2=False):
    monkeypatch.setenv("DEHASHED_API_KEY", "test_key_123")
    if v2:
        monkeypatch.setenv("DEHASHED_API_VERSION", "v2")
    else:
        monkeypatch.setenv("DEHASHED_EMAIL", "pi@example.com")
        monkeypatch.setenv("DEHASHED_API_VERSION", "v1")


class TestConfig:
    def test_not_configured_without_key(self, monkeypatch):
        monkeypatch.delenv("DEHASHED_API_KEY", raising=False)
        assert dc.is_configured() is False
        r = dc.search(name="Jane Doe")
        assert r["configured"] is False
        assert r["emails"] == []
        assert "not set" in r["error"]

    def test_configured_with_key(self, monkeypatch):
        _set_key(monkeypatch)
        assert dc.is_configured() is True


class TestQueryBuild:
    def test_name_and_location(self):
        q = dc._build_query(name="Jane Doe", city="Memphis", state="TN")
        assert 'name:"Jane Doe"' in q
        assert "Memphis" in q and "TN" in q

    def test_phone_digits_only(self):
        q = dc._build_query(phone="(901) 555-1212")
        assert "phone:9015551212" in q

    def test_address(self):
        q = dc._build_query(address="123 Real St")
        assert 'address:"123 Real St"' in q

    def test_empty(self):
        assert dc._build_query() == ""


class TestExtract:
    def test_extracts_distinct_real_emails(self):
        emails = dc._extract_emails(_SAMPLE_PAYLOAD)
        addrs = {e["email"] for e in emails}
        assert "rita.townsend@realmail.com" in addrs
        assert "rita.t@work.org" in addrs            # lowercased
        assert "junk@faisalman.com" not in addrs     # junk domain dropped
        assert "not-an-email" not in addrs           # invalid dropped
        assert all(e["source"] == "dehashed" for e in emails)

    def test_carries_corroborating_fields(self):
        emails = dc._extract_emails(_SAMPLE_PAYLOAD)
        rec = next(e for e in emails if e["email"] == "rita.townsend@realmail.com")
        assert rec["phone"] == "9015551212"
        assert "Memphis" in rec["address"]
        assert rec["database"] == "SomeBreach2019"


class TestSearchMocked:
    def test_v1_search_returns_real_emails(self, monkeypatch):
        _set_key(monkeypatch)
        captured = {}

        def fake_http(url, *, headers, data=None):
            captured["url"] = url
            captured["headers"] = headers
            return _SAMPLE_PAYLOAD

        monkeypatch.setattr(dc, "_http_json", fake_http)
        r = dc.search(name="Rita Townsend", city="Memphis", state="TN")
        assert r["configured"] is True
        assert r["error"] == ""
        assert len(r["emails"]) == 2
        assert r["balance"] == 999
        assert captured["url"].startswith(dc.V1_URL)
        assert "Authorization" in captured["headers"]

    def test_v2_uses_header_auth_and_post(self, monkeypatch):
        _set_key(monkeypatch, v2=True)
        captured = {}

        def fake_http(url, *, headers, data=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            return _SAMPLE_PAYLOAD

        monkeypatch.setattr(dc, "_http_json", fake_http)
        r = dc.search(name="Rita Townsend")
        assert captured["url"] == dc.V2_URL
        assert captured["headers"].get("Dehashed-Api-Key") == "test_key_123"
        assert captured["data"] is not None          # POST body
        assert len(r["emails"]) == 2

    def test_http_error_degrades_gracefully(self, monkeypatch):
        _set_key(monkeypatch)
        import urllib.error

        def boom(url, *, headers, data=None):
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

        monkeypatch.setattr(dc, "_http_json", boom)
        r = dc.search(name="Rita Townsend")
        assert r["emails"] == []
        assert r["error"] == "http_401"

    def test_network_error_never_raises(self, monkeypatch):
        _set_key(monkeypatch)

        def boom(url, *, headers, data=None):
            raise OSError("network down")

        monkeypatch.setattr(dc, "_http_json", boom)
        r = dc.search(name="Rita Townsend")     # must not raise
        assert r["emails"] == []
        assert "OSError" in r["error"]
