"""
Everlight OS — Filesystem helpers.
Folder creation, slug generation, path conventions.
"""

import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


# --- Dynamic path resolution via path_map.json ---

_FALLBACK_BASE = Path("/mnt/sdcard/AA_MY_DRIVE")
_PATH_MAP_FILE = _FALLBACK_BASE / "everlight_os" / "_meta" / "path_map.json"
_path_map = {}


def _load_path_map():
    global _path_map
    if _PATH_MAP_FILE.exists():
        with open(_PATH_MAP_FILE) as f:
            _path_map = json.load(f)


_load_path_map()


def get_path(key: str) -> Path:
    """Get a path from path_map.json by key. Falls back to BASE if missing."""
    if key in _path_map:
        return Path(_path_map[key])
    return _FALLBACK_BASE


BASE = get_path("ROOT_TRUTH")


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")[:80]


def content_project_dir(slug: str) -> Path:
    """Create dated content project directory."""
    now = datetime.now(timezone.utc)
    path = BASE / "content_engine" / str(now.year) / f"{now.month:02d}" / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def trading_report_dir(date_str: str = None) -> Path:
    """Create dated trading report directory."""
    if not date_str:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y/%m/%d")
    parts = date_str.split("/")
    path = BASE / "trading" / "xlm_derivatives" / "reports" / "/".join(parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def books_project_dir(series: str, title: str) -> Path:
    """Create book project directory."""
    path = BASE / "books" / slugify(series) / slugify(title)
    path.mkdir(parents=True, exist_ok=True)
    return path


def saas_project_dir(slug: str) -> Path:
    """Create SaaS factory project directory for a given idea slug."""
    root = get_path("SAAS_FACTORY_ROOT")
    path = root / slug
    path.mkdir(parents=True, exist_ok=True)
    (path / "spec").mkdir(exist_ok=True)
    return path


def write_json(path: Path, data: dict):
    """Write JSON file with pretty formatting."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_json(path: Path) -> dict:
    """Read JSON file, return empty dict if missing."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def write_text(path: Path, text: str):
    """Write text file."""
    with open(path, "w") as f:
        f.write(text)


def read_text(path: Path) -> str:
    """Read text file, return empty string if missing."""
    if not path.exists():
        return ""
    with open(path) as f:
        return f.read()


def read_jsonl(path: Path, last_n: int = 0) -> list:
    """Read JSONL file. If last_n > 0, return only last N entries."""
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if last_n > 0:
        return entries[-last_n:]
    return entries
