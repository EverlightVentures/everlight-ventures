# builder/build.py
import html as _html
from builder.adapters import load_source

def _kpi(dash, data) -> str:
    cells = []
    for k in data.get("kpis", []):
        hero = " hero" if k.get("key") == dash.hero_metric else ""
        label = _html.escape(k.get("label", ""))
        value = _html.escape(str(k.get("value", "")))
        delta = ""
        if k.get("delta"):
            sign = "neg" if str(k["delta"]).startswith("-") else "pos"
            base = _html.escape(k.get("baseline_label", ""))
            delta = f'<div class="lx-delta {sign}">{_html.escape(str(k["delta"]))} {base}</div>'
        else:
            delta = '<div class="lx-delta">no baseline</div>'
        cells.append(
            f'<div class="lx-card lx-kpi{hero}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div>{delta}</div>'
        )
    return f'<div class="lx-grid">{"".join(cells)}</div>'

LAYOUTS = {"kpi": _kpi}

def render_dashboard(dash) -> str:
    data = load_source(dash.source)
    body = LAYOUTS[dash.layout](dash, data)
    generated = _html.escape(str(data.get("generated_at", "")))
    vibe = _html.escape(dash.vibe)
    refresh = dash.refresh_seconds or 0
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_html.escape(dash.title)} | LUCREX OS</title>
<link rel="stylesheet" href="/lucrex_os/theme/lucrex.css">
<link rel="stylesheet" href="/lucrex_os/theme/lucrex.fx.css">
</head>
<body data-vibe="{vibe}" data-generated="{generated}" data-refresh="{refresh}">
<div class="lx-header"><div class="lx-logo">Everlight Ventures</div>
<h1>{_html.escape(dash.title)}</h1>
<span class="lx-badge" id="lx-freshness"></span></div>
{body}
<script src="/lucrex_os/builder/badge.js"></script>
</body></html>"""
