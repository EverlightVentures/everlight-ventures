# LUCREX OS Engine -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the registry-driven dashboard engine core: one `registry.yaml` brain that loads, validates fail-closed, feeds one linked theme and a buildless generator, and propagates to downstream surfaces through `sync.py` with dry-run safety.

**Architecture:** A small stdlib-first Python package at `09_DASHBOARD/lucrex_os/`. A YAML registry is parsed into dataclasses and validated before anything is written. A token module is the single color/font source; `lucrex.css` references only those tokens. The generator renders a registry entry + a data adapter into branded static HTML that links the shared theme and polls a `data.json`. `sync.py` injects generated blocks into existing files between markers, never writing unless the whole registry validates, with `--dry-run` showing a diff first.

**Tech Stack:** Python 3 (stdlib + PyYAML, already present -- `portal_server.py` imports it), pytest, plain HTML/CSS/JS. No node, no build step for the static path (runs on the phone).

**Plan split:** This is **Plan A (Engine Core)** -- working, testable software that renders a real dashboard and syncs one surface. **Plan B (Big-Bang Application)** is mapped at the end and gets its own expanded plan after Plan A lands.

**Spec:** `09_DASHBOARD/lucrex_os/docs/2026-06-15-lucrex-os-engine-design.md`

---

## File structure (Plan A)

```
09_DASHBOARD/lucrex_os/
  __init__.py
  registry.py            # dataclasses + load() + validate()  (Tasks 1-2)
  theme/
    tokens.py            # TOKENS dict + emit_css_vars()       (Task 3)
    lucrex.css           # tokens + components (authored)       (Task 4)
    lucrex.fx.css        # arcade FX, reduced-motion gated      (Task 4)
  builder/
    __init__.py
    adapters/__init__.py # load_source() dispatch              (Task 5)
    build.py             # render_dashboard() + LAYOUTS         (Task 6)
    badge.js             # stale-data honesty badge (authored)  (Task 6)
  sync.py                # marker injection + dry-run + gate     (Task 7)
  daemon.sh              # singleton self-heal loop              (Task 8)
  bootstrap.sh           # portable stand-up                     (Task 8)
  tests/
    __init__.py
    conftest.py
    fixtures/sample_registry.yaml
    test_registry.py test_validate.py test_tokens.py
    test_theme_lint.py test_adapters.py test_build.py test_sync.py
```

Each file has one responsibility. `registry.py` owns parsing+validation; `theme/tokens.py` owns the single color source; `builder/` owns rendering; `sync.py` owns propagation. They communicate through the `Registry` dataclass and plain dicts.

---

### Task 0: Scaffold the package + test harness

**Files:**
- Create: `09_DASHBOARD/lucrex_os/__init__.py`
- Create: `09_DASHBOARD/lucrex_os/builder/__init__.py`
- Create: `09_DASHBOARD/lucrex_os/builder/adapters/__init__.py`
- Create: `09_DASHBOARD/lucrex_os/tests/__init__.py`
- Create: `09_DASHBOARD/lucrex_os/tests/conftest.py`
- Create: `09_DASHBOARD/lucrex_os/tests/fixtures/sample_registry.yaml`
- Create: `09_DASHBOARD/lucrex_os/pytest.ini`

- [ ] **Step 1: Create the package directories and empty `__init__.py` files**

```bash
cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os
mkdir -p builder/adapters theme tests/fixtures
: > __init__.py
: > builder/__init__.py
: > builder/adapters/__init__.py
: > tests/__init__.py
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Create `tests/fixtures/sample_registry.yaml`** (the canonical test fixture every test reuses)

```yaml
tokens:
  gold: "#D4AF37"
  dark: "#0A0A0A"
  text: "#E8E8E8"
bands:
  - port: 2000
    name: hub
    range: "2000"
    default_vibe: boardroom
  - port: 2200
    name: reports
    range: "2200-2299"
    default_vibe: boardroom
dashboards:
  - id: kalshi
    title: "Kalshi Edge Engine"
    band: 2200
    sub_route: "/reports/kalshi.html"
    renderer: static
    source: { type: file, path: "tests/fixtures/kalshi_data.json" }
    layout: kpi
    vibe: boardroom
    access: tailnet
    hero_metric: all_time_pnl
    refresh_seconds: 90
    health_path: "/"
    icon: "K"
    description: "Sports edge engine"
```

- [ ] **Step 4: Create `tests/fixtures/kalshi_data.json`** (sample data the file adapter loads)

```json
{
  "generated_at": "2026-06-15T09:00:00-07:00",
  "kpis": [
    { "key": "all_time_pnl", "label": "All-Time P&L", "value": "+$85.96", "delta": "+$12.40", "baseline_label": "vs last week" },
    { "key": "record", "label": "Win / Loss", "value": "6-3" }
  ]
}
```

- [ ] **Step 5: Create `tests/conftest.py`** (shared fixtures)

```python
import os
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

@pytest.fixture
def fixture_path():
    return ROOT / "tests" / "fixtures" / "sample_registry.yaml"

@pytest.fixture(autouse=True)
def _chdir(monkeypatch):
    # tests reference fixture-relative paths from the package root
    monkeypatch.chdir(ROOT)
```

- [ ] **Step 6: Verify pytest collects (no tests yet, exit code 5 = no tests)**

Run: `cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os && python3 -m pytest`
Expected: "no tests ran" (exit 5). Confirms harness works.

- [ ] **Step 7: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os
git commit -m "chore(lucrex-os): scaffold engine package + test harness"
```

---

### Task 1: Registry model + YAML load

**Files:**
- Create: `09_DASHBOARD/lucrex_os/registry.py`
- Test: `09_DASHBOARD/lucrex_os/tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'registry'`

- [ ] **Step 3: Write minimal implementation**

```python
# registry.py
from __future__ import annotations
import dataclasses
import pathlib
import yaml

@dataclasses.dataclass
class Band:
    port: int
    name: str
    range: str
    default_vibe: str = "boardroom"

@dataclasses.dataclass
class Dashboard:
    id: str
    title: str
    band: int
    layout: str
    renderer: str = "static"
    source: dict = dataclasses.field(default_factory=dict)
    vibe: str = ""
    access: str = "tailnet"
    sub_route: str = ""
    hero_metric: str = ""
    refresh_seconds: int = 0
    health_path: str = "/"
    icon: str = ""
    description: str = ""
    mirror_source: str = ""

@dataclasses.dataclass
class Registry:
    tokens: dict
    bands: list[Band]
    dashboards: list[Dashboard]

def load_registry(path) -> Registry:
    raw = yaml.safe_load(pathlib.Path(path).read_text())
    bands = [Band(**b) for b in raw.get("bands", [])]
    band_default = {b.port: b.default_vibe for b in bands}
    dashboards = []
    for d in raw.get("dashboards", []):
        d = dict(d)
        if not d.get("vibe"):
            d["vibe"] = band_default.get(d.get("band"), "boardroom")
        dashboards.append(Dashboard(**d))
    return Registry(tokens=raw.get("tokens", {}), bands=bands, dashboards=dashboards)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/registry.py 09_DASHBOARD/lucrex_os/tests/test_registry.py
git commit -m "feat(lucrex-os): registry dataclasses + YAML loader"
```

---

### Task 2: Fail-closed validator

**Files:**
- Modify: `09_DASHBOARD/lucrex_os/registry.py` (add `validate`)
- Test: `09_DASHBOARD/lucrex_os/tests/test_validate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validate.py
import dataclasses
from registry import load_registry, validate

def test_valid_registry_has_no_errors(fixture_path):
    assert validate(load_registry(fixture_path)) == []

def test_bad_hex_token_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    reg.tokens["gold"] = "D4AF37"  # missing '#'
    errs = validate(reg)
    assert any("gold" in e and "hex" in e for e in errs)

def test_duplicate_dashboard_id_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    dup = dataclasses.replace(reg.dashboards[0])
    reg.dashboards.append(dup)
    errs = validate(reg)
    assert any("duplicate id" in e for e in errs)

def test_bad_enum_is_flagged(fixture_path):
    reg = load_registry(fixture_path)
    reg.dashboards[0].access = "world"  # not in enum
    errs = validate(reg)
    assert any("access" in e for e in errs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_validate.py -v`
Expected: FAIL with `ImportError: cannot import name 'validate'`

- [ ] **Step 3: Write minimal implementation (append to `registry.py`)**

```python
import re

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_ACCESS = {"public", "tailnet", "gated"}
_RENDERER = {"static", "next"}
_LAYOUT = {"kpi", "grid", "list", "table", "detail", "feed", "today"}
_VIBE = {"boardroom", "arcade"}

def validate(reg: Registry) -> list[str]:
    errs: list[str] = []
    for name, val in reg.tokens.items():
        if not _HEX.match(str(val)):
            errs.append(f"token {name} is not a 6-digit hex: {val!r}")
    band_ports = [b.port for b in reg.bands]
    for p in band_ports:
        if not isinstance(p, int):
            errs.append(f"band port not an int: {p!r}")
    if len(band_ports) != len(set(band_ports)):
        errs.append("duplicate band port")
    seen_ids: set[str] = set()
    for d in reg.dashboards:
        if d.id in seen_ids:
            errs.append(f"duplicate id: {d.id}")
        seen_ids.add(d.id)
        if d.access not in _ACCESS:
            errs.append(f"dashboard {d.id}: bad access {d.access!r}")
        if d.renderer not in _RENDERER:
            errs.append(f"dashboard {d.id}: bad renderer {d.renderer!r}")
        if d.layout not in _LAYOUT:
            errs.append(f"dashboard {d.id}: bad layout {d.layout!r}")
        if d.vibe not in _VIBE:
            errs.append(f"dashboard {d.id}: bad vibe {d.vibe!r}")
        if d.band not in band_ports:
            errs.append(f"dashboard {d.id}: band {d.band} not declared")
    return errs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_validate.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/registry.py 09_DASHBOARD/lucrex_os/tests/test_validate.py
git commit -m "feat(lucrex-os): fail-closed registry validator"
```

---

### Task 3: Token module + CSS-var emitter (single color source)

**Files:**
- Create: `09_DASHBOARD/lucrex_os/theme/tokens.py`
- Create: `09_DASHBOARD/lucrex_os/theme/__init__.py` (empty)
- Test: `09_DASHBOARD/lucrex_os/tests/test_tokens.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tokens.py
from theme.tokens import TOKENS, emit_css_vars

def test_canonical_gold():
    assert TOKENS["gold"] == "#D4AF37"
    assert TOKENS["dark"] == "#0A0A0A"

def test_emit_css_vars_block():
    css = emit_css_vars()
    assert ":root" in css
    assert "--gold: #D4AF37;" in css
    assert "--canvas:" in css   # data-surface ramp token exists
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tokens.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'theme.tokens'`

- [ ] **Step 3: Write minimal implementation**

```python
# theme/__init__.py  (empty file)
```

```python
# theme/tokens.py
"""Single source of truth for LUCREX OS colors + fonts.
The gold value has never changed in git history, so this is a flat dict,
not a DTCG/Style-Dictionary pipeline (see design spec section 3.2)."""

TOKENS = {
    # chrome (brand)
    "gold": "#D4AF37",
    "dark": "#0A0A0A",
    "text": "#E8E8E8",
    "text_dim": "#A8A8A8",
    # data-surface elevation ramp (off pure black for readability)
    "canvas": "#141414",
    "card": "#1E1E1E",
    "gridline": "#2E2E2E",
    # status (desaturated, gold is NEVER a status color)
    "pos": "#5BA46A",
    "neg": "#C25B5B",
}

FONTS = {
    "display": "'Playfair Display', serif",
    "body": "'Inter', -apple-system, sans-serif",
    "mono": "'JetBrains Mono', monospace",
    "ui": "'DM Sans', sans-serif",
}

def emit_css_vars() -> str:
    lines = [":root {"]
    for k, v in TOKENS.items():
        lines.append(f"  --{k.replace('_','-')}: {v};")
    for k, v in FONTS.items():
        lines.append(f"  --font-{k}: {v};")
    lines.append("}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tokens.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/theme/
git add 09_DASHBOARD/lucrex_os/tests/test_tokens.py
git commit -m "feat(lucrex-os): token module + CSS-var emitter (one color source)"
```

---

### Task 4: Author the theme CSS + a token-lint test

**Files:**
- Create: `09_DASHBOARD/lucrex_os/theme/lucrex.css`
- Create: `09_DASHBOARD/lucrex_os/theme/lucrex.fx.css`
- Test: `09_DASHBOARD/lucrex_os/tests/test_theme_lint.py`

- [ ] **Step 1: Write the failing test (lint: every var() used must be a defined token)**

```python
# tests/test_theme_lint.py
import re, pathlib
from theme.tokens import TOKENS, FONTS

CSS = pathlib.Path("theme/lucrex.css")
FX = pathlib.Path("theme/lucrex.fx.css")

def _defined():
    names = {f"--{k.replace('_','-')}" for k in TOKENS}
    names |= {f"--font-{k}" for k in FONTS}
    return names

def test_lucrex_css_only_uses_defined_tokens():
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", CSS.read_text()))
    undefined = used - _defined()
    assert not undefined, f"undefined tokens: {undefined}"

def test_fx_is_reduced_motion_gated():
    assert "prefers-reduced-motion: reduce" in FX.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_theme_lint.py -v`
Expected: FAIL (files do not exist yet -> FileNotFoundError)

- [ ] **Step 3: Author `theme/lucrex.css`** (tokens injected at sync time; this authored file references them)

```css
/* LUCREX OS theme -- the one linked stylesheet. The :root token block is
   injected by sync.py from theme/tokens.py between the markers below. */
/* LUCREX-OS:TOKENS:START */
/* LUCREX-OS:TOKENS:END */

* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--dark);
  color: var(--text);
  font-family: var(--font-body);
  line-height: 1.6;
}
.lx-header {
  background: linear-gradient(135deg, var(--dark) 0%, var(--canvas) 100%);
  border-bottom: 2px solid var(--gold);
  padding: 28px 24px;
}
.lx-logo {
  font-family: var(--font-display);
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--gold);
  font-size: 13px;
}
.lx-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  padding: 24px;
}
.lx-card {
  background: var(--card);
  border: 1px solid var(--gridline);
  border-radius: 10px;
  padding: 18px;
}
.lx-card:hover { border-color: var(--gold); }
.lx-kpi .label { color: var(--text-dim); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
.lx-kpi .value { font-family: var(--font-display); font-size: 30px; color: var(--text); }
.lx-kpi.hero { grid-column: span 2; grid-row: span 2; }
.lx-kpi.hero .value { color: var(--gold); font-size: 44px; }
.lx-delta.pos { color: var(--pos); }
.lx-delta.neg { color: var(--neg); }
.lx-badge { font-family: var(--font-mono); font-size: 12px; padding: 4px 10px; border-radius: 6px; }
.lx-badge.live { color: var(--pos); }
.lx-badge.stale { color: var(--neg); }
table { width: 100%; border-collapse: collapse; }
th { background: var(--canvas); color: var(--gold); text-align: left; padding: 10px; font-size: 12px; text-transform: uppercase; }
td { padding: 9px 10px; border-bottom: 1px solid var(--gridline); }
```

- [ ] **Step 4: Author `theme/lucrex.fx.css`** (arcade-only living layer, reduced-motion gated, NO infinite ambient loops)

```css
/* Arcade vibe FX. Applied only under [data-vibe="arcade"]. Static glass +
   gentle breathing only; the cursor-halo / drifting-grid / mote loops are
   intentionally NOT here (battery/thermal -- see spec 3.2). */
[data-vibe="arcade"] .lx-card {
  background: linear-gradient(135deg, rgba(30,30,30,0.85), rgba(20,20,20,0.6));
  backdrop-filter: blur(10px) saturate(130%);
  animation: lx-breath 6s ease-in-out infinite;
}
@keyframes lx-breath {
  0%,100% { box-shadow: 0 6px 24px rgba(0,0,0,0.45); }
  50%     { box-shadow: 0 0 22px -4px rgba(212,175,55,0.18), 0 6px 30px rgba(0,0,0,0.5); }
}
@media (prefers-reduced-motion: reduce) {
  [data-vibe="arcade"] .lx-card { animation: none; }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_theme_lint.py -v`
Expected: PASS (2 tests). If `undefined tokens` lists names, add them to `TOKENS` or fix the CSS reference.

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/theme/lucrex.css 09_DASHBOARD/lucrex_os/theme/lucrex.fx.css 09_DASHBOARD/lucrex_os/tests/test_theme_lint.py
git commit -m "feat(lucrex-os): author linked theme + token lint"
```

---

### Task 5: Data adapter (file + cmd)

**Files:**
- Create: `09_DASHBOARD/lucrex_os/builder/adapters/__init__.py` (replace the empty stub)
- Test: `09_DASHBOARD/lucrex_os/tests/test_adapters.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_adapters.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_source'`

- [ ] **Step 3: Write minimal implementation**

```python
# builder/adapters/__init__.py
import json, pathlib, subprocess

def _file(src):
    return json.loads(pathlib.Path(src["path"]).read_text())

def _cmd(src):
    out = subprocess.run(src["cmd"], shell=True, capture_output=True, text=True, timeout=20)
    return json.loads(out.stdout)

_ADAPTERS = {"file": _file, "cmd": _cmd}

def load_source(src: dict) -> dict:
    t = src.get("type")
    if t not in _ADAPTERS:
        raise ValueError(f"unknown source type: {t!r}")
    return _ADAPTERS[t](src)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_adapters.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/builder/adapters/__init__.py 09_DASHBOARD/lucrex_os/tests/test_adapters.py
git commit -m "feat(lucrex-os): file + cmd data adapters with dispatch"
```

---

### Task 6: Generator core + kpi layout + honesty badge

**Files:**
- Create: `09_DASHBOARD/lucrex_os/builder/build.py`
- Create: `09_DASHBOARD/lucrex_os/builder/badge.js`
- Test: `09_DASHBOARD/lucrex_os/tests/test_build.py`

- [ ] **Step 1: Write the failing test**

```python
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
    assert 'class="lx-kpi hero"' in html                          # hero_metric promoted
    assert 'data-generated="2026-06-15T09:00:00-07:00"' in html   # honesty badge source
    assert "lucrex_os/builder/badge.js" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'builder.build'`

- [ ] **Step 3: Write minimal implementation**

```python
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
    refresh = dash.refresh_seconds or 0
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_html.escape(dash.title)} | LUCREX OS</title>
<link rel="stylesheet" href="/lucrex_os/theme/lucrex.css">
<link rel="stylesheet" href="/lucrex_os/theme/lucrex.fx.css">
</head>
<body data-vibe="{dash.vibe}" data-generated="{generated}" data-refresh="{refresh}">
<div class="lx-header"><div class="lx-logo">Everlight Ventures</div>
<h1>{_html.escape(dash.title)}</h1>
<span class="lx-badge" id="lx-freshness"></span></div>
{body}
<script src="/lucrex_os/builder/badge.js"></script>
</body></html>"""
```

- [ ] **Step 4: Author `builder/badge.js`** (the stale-data honesty badge)

```javascript
// Flips the freshness badge based on data-generated vs now + data-refresh.
(function () {
  var body = document.body;
  var el = document.getElementById("lx-freshness");
  if (!el) return;
  var iso = body.getAttribute("data-generated");
  var refresh = parseInt(body.getAttribute("data-refresh") || "0", 10);
  function fmtPT(d) {
    return d.toLocaleTimeString("en-US", { timeZone: "America/Los_Angeles", hour: "2-digit", minute: "2-digit" });
  }
  function paint() {
    if (!iso) { el.textContent = "no timestamp"; el.className = "lx-badge stale"; return; }
    var gen = new Date(iso), now = new Date();
    var ageSec = (now - gen) / 1000;
    var window = refresh > 0 ? refresh * 2 : 3600;
    if (ageSec <= window) { el.textContent = "live " + fmtPT(gen) + " PT"; el.className = "lx-badge live"; }
    else { el.textContent = "STALE as of " + fmtPT(gen) + " PT"; el.className = "lx-badge stale"; }
  }
  paint();
  document.addEventListener("visibilitychange", function () { if (!document.hidden) paint(); });
})();
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/builder/build.py 09_DASHBOARD/lucrex_os/builder/badge.js 09_DASHBOARD/lucrex_os/tests/test_build.py
git commit -m "feat(lucrex-os): generator core + kpi layout + honesty badge"
```

---

### Task 7: `sync.py` -- marker injection, dry-run, fail-closed gate

**Files:**
- Create: `09_DASHBOARD/lucrex_os/sync.py`
- Test: `09_DASHBOARD/lucrex_os/tests/test_sync.py`

This task delivers propagation for the FIRST surface (the shell-banner DASHBOARDS block) plus the token injection into `lucrex.css`, proving the marker mechanism. Remaining surfaces are Plan B.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sync.py
import pathlib
from registry import load_registry
import sync

MARK = ("# LX:START", "# LX:END")

def test_inject_block_is_idempotent(tmp_path):
    f = tmp_path / "x.sh"
    f.write_text("a\n# LX:START\nOLD\n# LX:END\nb\n")
    sync.inject_block(f, MARK, "NEW")
    sync.inject_block(f, MARK, "NEW")  # twice -> same result
    out = f.read_text()
    assert out.count("# LX:START") == 1
    assert "NEW" in out and "OLD" not in out
    assert out.startswith("a\n") and out.rstrip().endswith("b")

def test_run_sync_dry_run_writes_nothing(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    target = tmp_path / "banner.sh"
    target.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    monkeypatch.setattr(sync, "SHELL_BANNER", target)
    changed = sync.run_sync(reg, dry_run=True)
    assert "banner.sh" in "".join(changed)            # reports it WOULD change
    assert target.read_text() == "# LX:DASH:START\n# LX:DASH:END\n"  # unchanged

def test_run_sync_fails_closed_on_invalid_registry(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    reg.dashboards[0].access = "world"                # invalid
    target = tmp_path / "banner.sh"
    target.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    monkeypatch.setattr(sync, "SHELL_BANNER", target)
    import pytest
    with pytest.raises(SystemExit):
        sync.run_sync(reg, dry_run=False)
    assert target.read_text() == "# LX:DASH:START\n# LX:DASH:END\n"  # zero writes

def test_token_injection_writes_root_block(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    css = tmp_path / "lucrex.css"
    css.write_text("/* LUCREX-OS:TOKENS:START */\n/* LUCREX-OS:TOKENS:END */\nbody{}\n")
    banner = tmp_path / "banner.sh"
    banner.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    monkeypatch.setattr(sync, "LUCREX_CSS", css)
    monkeypatch.setattr(sync, "SHELL_BANNER", banner)
    sync.run_sync(reg, dry_run=False)
    assert "--gold: #D4AF37;" in css.read_text()       # tokens injected -> dashboard is styled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sync'`

- [ ] **Step 3: Write minimal implementation**

```python
# sync.py
import os, sys, pathlib, difflib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # run from any cwd (bootstrap)
from registry import load_registry, validate
from theme.tokens import emit_css_vars

ROOT = pathlib.Path(os.environ.get("LUCREX_OS_ROOT", pathlib.Path(__file__).resolve().parents[2]))
OS_DIR = ROOT / "09_DASHBOARD/lucrex_os"
SHELL_BANNER = ROOT / "03_AUTOMATION_CORE/01_Scripts/everlight_shell.zsh"
LUCREX_CSS = OS_DIR / "theme/lucrex.css"
BANNER_MARK = ("# LX:DASH:START", "# LX:DASH:END")
TOKENS_MARK = ("/* LUCREX-OS:TOKENS:START */", "/* LUCREX-OS:TOKENS:END */")
BANNER_DESC = "/* GENERATED FROM registry.yaml by lucrex_os/sync.py -- DO NOT EDIT */"

def inject_block(path, mark, content):
    start, end = mark
    text = pathlib.Path(path).read_text()
    block = f"{start}\n{content}\n{end}"
    if start in text and end in text:
        pre = text.split(start)[0]
        post = text.split(end, 1)[1]
        new = pre + block + post
    else:
        new = text.rstrip() + "\n" + block + "\n"
    pathlib.Path(path).write_text(new)

def generate_shell_banner(reg) -> str:
    lines = [BANNER_DESC]
    for b in reg.bands:
        ds = [d for d in reg.dashboards if d.band == b.port]
        lines.append(f'_ev_row "{b.name}  {b.port}"')
        for d in ds:
            lines.append(f'_ev_row "  {d.id}  http://127.0.0.1:{d.band}{d.sub_route}  {d.description}"')
    return "\n".join(lines)

def generate_tokens_css(reg) -> str:
    # tokens.py is the canonical CSS color source; reg.tokens is validated-only.
    return emit_css_vars()

# (path_fn, marker, generator) -- add Plan B surfaces here
SURFACES = [
    (lambda: SHELL_BANNER, BANNER_MARK, generate_shell_banner),
    (lambda: LUCREX_CSS, TOKENS_MARK, generate_tokens_css),
]

def run_sync(reg, dry_run=False) -> list[str]:
    errs = validate(reg)
    if errs:
        sys.stderr.write("REGISTRY INVALID -- zero files written:\n" + "\n".join(errs) + "\n")
        raise SystemExit(1)
    changed = []
    for path_fn, mark, gen in SURFACES:
        path = path_fn()
        content = gen(reg)
        current = pathlib.Path(path).read_text() if pathlib.Path(path).exists() else ""
        block = f"{mark[0]}\n{content}\n{mark[1]}"
        if block not in current:
            changed.append(str(path))
            if dry_run:
                sys.stdout.write("\n".join(difflib.unified_diff(
                    current.splitlines(), block.splitlines(),
                    fromfile=str(path), tofile=str(path)+" (new)", lineterm="")) + "\n")
            else:
                inject_block(path, mark, content)
    return changed

if __name__ == "__main__":
    reg = load_registry(OS_DIR / "registry.yaml")
    dry = "--check" in sys.argv or "--dry-run" in sys.argv
    print("would change:" if dry else "synced:", run_sync(reg, dry_run=dry))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_sync.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full suite**

Run: `cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os && python3 -m pytest -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/sync.py 09_DASHBOARD/lucrex_os/tests/test_sync.py
git commit -m "feat(lucrex-os): sync.py marker injection + dry-run + fail-closed gate"
```

---

### Task 8: Portability -- `bootstrap.sh` + `daemon.sh`

**Files:**
- Create: `09_DASHBOARD/lucrex_os/bootstrap.sh`
- Create: `09_DASHBOARD/lucrex_os/daemon.sh`
- Test: `09_DASHBOARD/lucrex_os/tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test (bootstrap honors LUCREX_OS_ROOT, daemon has a singleton guard)**

```python
# tests/test_bootstrap.py
import pathlib, subprocess, os

BOOT = pathlib.Path("bootstrap.sh")
DAEMON = pathlib.Path("daemon.sh")

def test_bootstrap_dry_run_uses_root_env(tmp_path):
    env = dict(os.environ, LUCREX_OS_ROOT=str(tmp_path), LX_DRY_RUN="1")
    out = subprocess.run(["bash", str(BOOT)], capture_output=True, text=True, env=env)
    assert out.returncode == 0
    assert str(tmp_path) in out.stdout

def test_daemon_has_singleton_guard():
    txt = DAEMON.read_text()
    assert "LUCREX_OS_ROOT" in txt
    assert "pidfile" in txt.lower() or "flock" in txt.lower()
    assert "crontab" not in txt   # must NOT be a cron entry (phone crond is dead)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_bootstrap.py -v`
Expected: FAIL (files do not exist)

- [ ] **Step 3: Author `bootstrap.sh`**

```bash
#!/usr/bin/env bash
# Stand up LUCREX OS on any machine. Portable: keys off LUCREX_OS_ROOT.
set -euo pipefail
ROOT="${LUCREX_OS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
OS_DIR="$ROOT/09_DASHBOARD/lucrex_os"
echo "LUCREX OS root: $ROOT"
echo "engine dir: $OS_DIR"
if [[ "${LX_DRY_RUN:-0}" == "1" ]]; then
  echo "[dry-run] would: validate registry, sync surfaces, start daemon"
  exit 0
fi
python3 "$OS_DIR/sync.py"
nohup bash "$OS_DIR/daemon.sh" >/dev/null 2>&1 &
echo "daemon started."
```

- [ ] **Step 4: Author `daemon.sh`** (singleton while-loop, NOT cron)

```bash
#!/usr/bin/env bash
# Self-heal loop for LUCREX OS. Singleton-guarded. NOT a crontab entry
# (the phone has no crond; cron entries silently never run).
set -uo pipefail
ROOT="${LUCREX_OS_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
OS_DIR="$ROOT/09_DASHBOARD/lucrex_os"
pidfile="/tmp/lucrex_os_daemon.pid"
if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  echo "daemon already running"; exit 0
fi
echo $$ > "$pidfile"
trap 'rm -f "$pidfile"' EXIT
while true; do
  python3 "$OS_DIR/sync.py" --check >/dev/null 2>&1 || true
  sleep 60
done
```

- [ ] **Step 5: Make scripts executable and run the test**

```bash
chmod +x /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os/bootstrap.sh /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os/daemon.sh
cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/lucrex_os && python3 -m pytest tests/test_bootstrap.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git add 09_DASHBOARD/lucrex_os/bootstrap.sh 09_DASHBOARD/lucrex_os/daemon.sh 09_DASHBOARD/lucrex_os/tests/test_bootstrap.py
git commit -m "feat(lucrex-os): portable bootstrap + singleton self-heal daemon"
```

---

## Plan A complete = working engine

At this point: a registry loads + validates fail-closed, one token source feeds the linked theme (sync injects the `:root` block, so a rendered KPI dashboard is fully *styled*, not just structured), the generator renders a real KPI dashboard with the honesty badge, `sync.py` propagates the shell-banner + token surfaces with dry-run safety, and the whole thing stands up portably from `LUCREX_OS_ROOT` with a cron-free self-heal daemon. Full suite green.

---

## Plan B (Big-Bang Application) -- to be expanded into its own plan

Sequenced follow-on tasks (each becomes a full TDD task in the Plan B doc):

1. **Remaining adapters:** `sqlite`, `supabase` (read-only, publishable key), `blinko`.
2. **Remaining layouts:** `grid`, `list`, `table` (read-only), `detail`, `feed`; `today` as a composed page.
3. **Remaining sync surfaces:** `dashboards_watchdog.sh` SERVICES array, `.zshrc` band functions/aliases, master-hub `index.html` tiles, command-palette index feeding existing `ev_nav.js`.
4. **Theme reconciliation + cleanup:** (token injection into `lucrex.css` already ships in Plan A Task 7.) Reconcile the two token echoes -- make `tokens.py` load from / assert-equal `registry.yaml`'s `tokens:` block so there is one literal source; then the ~1-hour inline-hex cleanup pointing existing dashboards at the tokens.
5. **QR + PWA:** QR PNG per dashboard (`qrcode`+Pillow), real `manifest.json` (name/icons/theme), minimal network-first versioned `sw.js`.
6. **Next codegen:** generate `lib/external-tools.ts` + `lib/hub-data.ts` from the registry; retire `portal_server.py` + the `:8800` surface (salvage its 15-category taxonomy as registry data).
7. **Inventory + big-bang regen:** classify all ~173 dashboards (keep/merge/retire), populate the registry, `sync.py --dry-run` review, one regeneration pass; mirror-awareness for e5-mirrored pages (e.g. `kalshi.html`).
8. **Stale-badge rollout** to the live decision boards (Kalshi, XLM) + regenerate the `WORKSPACE_MANIFEST.md` port map from the registry (kill the stale 8502/8503).

Phase 2 (auth/profiles/channels, write-back, Today interactivity, Cloudflare Access) and Phase 3 (Mattermost) are separate programs per the spec.
