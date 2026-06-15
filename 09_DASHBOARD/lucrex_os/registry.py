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
