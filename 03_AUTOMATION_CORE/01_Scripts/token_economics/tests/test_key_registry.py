import os
import tempfile

from token_economics import key_registry as kr


def _mk(name, proj, cost, expires=None):
    return kr.KeyEntry(
        key_name=name, project=proj, sub_avenue="x", provider="p", owner="rich",
        created="2026-06-01", expires=expires, refresh_cadence="none",
        monthly_cost_usd=cost, status="live", value_location=f"vault:{name}", notes="",
    )


def test_roundtrip_load_save():
    e = _mk("CF_API_TOKEN", "infra", 0.0)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "reg.json")
        kr.save_registry([e], p)
        back = kr.load_registry(p)
    assert len(back) == 1
    assert back[0].key_name == "CF_API_TOKEN"
    assert back[0].value_location == "vault:CF_API_TOKEN"


def test_load_missing_returns_empty():
    assert kr.load_registry("/nonexistent/path/reg.json") == []


def test_rejects_embedded_secret():
    bad = kr.KeyEntry(
        key_name="OPENAI", project="llm", sub_avenue="content", provider="openai",
        owner="rich", created="2026-06-25", expires=None, refresh_cadence="none",
        monthly_cost_usd=0.0, status="live",
        value_location="sk-proj-ABC123definitelyasecretkey0000", notes="",
    )
    violations = kr.validate_registry([bad])
    assert violations, "a literal sk- secret must be flagged"


def test_accepts_pointer():
    ok = _mk("OPENAI_API_KEY", "llm", 0.0)
    assert kr.validate_registry([ok]) == []


def test_catches_supabase_token_with_underscores():
    # regression: sbp_v0_... tokens contain underscores; guard must still catch them
    fake = "sbp_v0_0000000000000000000000000000000000000000"
    assert kr.looks_like_secret(fake), "sbp_ token with underscores must be flagged"


def test_scan_catches_secret_in_list():
    # regression: a token passed as a bare CLI arg inside an array must be caught
    obj = {"mcpServers": {"supabase": {"args": ["--access-token", "sbp_v0_" + "0" * 40]}}}
    labels = kr.scan_object_for_secrets(obj)
    assert any("args" in lbl for lbl in labels), f"expected args[] flagged, got {labels}"


def test_scan_clean_object():
    obj = {"mcpServers": {"x": {"command": "node", "args": ["server.js"], "env": {"PORT": "3000"}}}}
    assert kr.scan_object_for_secrets(obj) == set()


def test_cost_rollup_and_expiry():
    es = [_mk("A", "alley_kingz", 5.0), _mk("B", "alley_kingz", 2.5), _mk("C", "bcardi", 1.0, "2026-07-01")]
    assert kr.monthly_cost_by_project(es)["alley_kingz"] == 7.5
    soon = kr.expiring_within(es, 30, today="2026-06-25")
    assert [e.key_name for e in soon] == ["C"]


def test_by_project_groups():
    es = [_mk("A", "alley_kingz", 1.0), _mk("B", "bcardi", 1.0)]
    grouped = kr.by_project(es)
    assert set(grouped.keys()) == {"alley_kingz", "bcardi"}
