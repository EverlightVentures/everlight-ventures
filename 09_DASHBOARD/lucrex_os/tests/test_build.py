# tests/test_build.py
from registry import load_registry
from builder.build import render_dashboard

def test_render_kpi_dashboard(fixture_path):
    reg = load_registry(fixture_path)
    dash = next(d for d in reg.dashboards if d.id == "kalshi")
    html = render_dashboard(dash)
    assert '<link rel="stylesheet" href="/lucrex_os/theme/lucrex.css">' in html
    assert 'data-vibe="boardroom"' in html
    assert "All-Time P&amp;L" in html or "All-Time P&L" in html  # hero label
    assert 'lx-card lx-kpi hero' in html                          # hero_metric promoted, styled as card
    assert 'data-generated="2026-06-15T09:00:00-07:00"' in html   # honesty badge source
    assert "lucrex_os/builder/badge.js" in html
