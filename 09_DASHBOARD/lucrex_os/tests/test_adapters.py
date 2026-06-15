# tests/test_adapters.py
from builder.adapters import load_source

def test_file_adapter_reads_json():
    data = load_source({"type": "file", "path": "tests/fixtures/kalshi_data.json"})
    assert data["kpis"][0]["key"] == "all_time_pnl"

def test_cmd_adapter_parses_json_stdout():
    data = load_source({"type": "cmd", "cmd": "printf '{\"ok\": true}'"})
    assert data["ok"] is True

def test_unknown_type_raises():
    import pytest
    with pytest.raises(ValueError):
        load_source({"type": "carrier-pigeon"})
