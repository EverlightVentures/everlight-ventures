"""
path_resolver.py - Auto-detect environment and return correct root paths.

Usage:
    from everlight_os._meta.path_resolver import PATHS, ROOT
    print(PATHS["XLM_BOT"])
"""

import os
import json
from pathlib import Path


def detect_root() -> Path:
    """Return the repo root, no matter which device we are on."""

    # 1. Explicit override via env var (set this in .bashrc on laptop)
    env_root = os.environ.get("EVERLIGHT_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root)

    # 2. Android / Termux path
    android_root = Path("/mnt/sdcard/AA_MY_DRIVE")
    if android_root.exists():
        return android_root

    # 3. Linux laptop: repo cloned to ~/AA_MY_DRIVE or ~/everlight
    for candidate in [
        Path.home() / "AA_MY_DRIVE",
        Path.home() / "everlight",
        Path.home() / "hive_mind",
    ]:
        if candidate.exists():
            return candidate

    # 4. Fallback: walk up from this file's location
    # This file lives at ROOT/everlight_os/_meta/path_resolver.py
    return Path(__file__).resolve().parent.parent.parent


ROOT = detect_root()


def _build_paths(root: Path) -> dict:
    r = str(root)
    return {
        "ROOT_TRUTH":          r,
        "EVERLIGHT_OS":        f"{r}/everlight_os",
        "CONTENT_ENGINE_ROOT": f"{r}/content_engine",
        "BOOKS_ROOT":          f"{r}/books",
        "TRADING_ROOT":        f"{r}/trading/xlm_derivatives",
        "TRADING_REPORTS":     f"{r}/trading/xlm_derivatives/reports",
        "XLM_BOT":             f"{r}/xlm_bot",
        "XLM_BOT_LOGS":        f"{r}/xlm_bot/logs",
        "XLM_BOT_DATA":        f"{r}/xlm_bot/data",
        "BUSINESSES":          f"{r}/01_BUSINESSES",
        "CONTENT_FACTORY":     f"{r}/02_CONTENT_FACTORY",
        "AUTOMATION_CORE":     f"{r}/03_AUTOMATION_CORE",
        "CREDENTIALS":         f"{r}/03_AUTOMATION_CORE/03_Credentials",
        "PUBLISHING":          f"{r}/01_BUSINESSES/Publishing",
        "SAM_BOOKS":           f"{r}/01_BUSINESSES/Publishing/Ebook_Sells/ADVENTURES_WITH_SAM",
        "DASHBOARDS":          f"{r}/09_DASHBOARD",
        "LOGS":                f"{r}/everlight_os/_logs",
        "KNOWLEDGE":           f"{r}/everlight_os/knowledge",
        "CONFIGS":             f"{r}/everlight_os/configs",
        "META":                f"{r}/everlight_os/_meta",
        "SAAS_FACTORY_ROOT":   f"{r}/saas_factory",
    }


PATHS = _build_paths(ROOT)


def get(key: str) -> str:
    """Get a resolved path by key."""
    return PATHS[key]


if __name__ == "__main__":
    print(f"Detected root: {ROOT}")
    print(json.dumps(PATHS, indent=2))
