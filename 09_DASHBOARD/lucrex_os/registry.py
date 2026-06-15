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
