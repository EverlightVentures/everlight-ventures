# tests/test_registry.py
from registry import load_registry, Band, Dashboard

def test_load_parses_bands_and_dashboards(fixture_path):
    reg = load_registry(fixture_path)
    assert reg.tokens["gold"] == "#D4AF37"
    assert any(isinstance(b, Band) and b.port == 2200 for b in reg.bands)
    kalshi = next(d for d in reg.dashboards if d.id == "kalshi")
    assert isinstance(kalshi, Dashboard)
    assert kalshi.band == 2200
    assert kalshi.layout == "kpi"
    # vibe defaults to the band default when omitted; here it is explicit
    assert kalshi.vibe == "boardroom"
    assert kalshi.source["type"] == "file"
