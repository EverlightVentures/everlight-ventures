import json
from pathlib import Path
import yaml
from everlense import paths

_DEFAULTS = Path(__file__).resolve().parent / "defaults" / "categories.yaml"

def _ensure_state_dir() -> Path:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d

def load_categories() -> dict:
    sd = _ensure_state_dir()
    f = sd / "categories.yaml"
    if not f.exists():
        f.write_text(_DEFAULTS.read_text())
    return yaml.safe_load(f.read_text()) or {}

def load_projects() -> dict:
    f = _ensure_state_dir() / "projects.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text())

def save_project(project: dict) -> None:
    projs = load_projects()
    projs[project["slug"]] = project
    (_ensure_state_dir() / "projects.json").write_text(json.dumps(projs, indent=2))

def load_state() -> dict:
    f = _ensure_state_dir() / "state.json"
    if not f.exists():
        return {"known_hashes": [], "last_scan": None}
    return json.loads(f.read_text())

def save_state(state: dict) -> None:
    (_ensure_state_dir() / "state.json").write_text(json.dumps(state, indent=2))
