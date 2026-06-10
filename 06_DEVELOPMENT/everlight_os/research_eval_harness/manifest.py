"""manifest.py -- reproducibility manifest emitter.

One manifest.json per run. Hashes everything needed to re-run and get the
same numbers within sampling noise. See SPEC.md §6.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__ as HARNESS_VERSION


@dataclass
class Manifest:
    """Per-run reproducibility manifest. Written to runs/.../manifest.json."""

    paper: int
    condition: str
    seed: int
    git_sha: str
    harness_version: str = HARNESS_VERSION
    python_version: str = field(default_factory=lambda: platform.python_version())
    platform: str = field(default_factory=lambda: platform.platform())
    package_versions: dict[str, str] = field(default_factory=dict)
    model_versions: dict[str, str] = field(default_factory=dict)
    dataset_hash: str = ""
    prompt_template_hashes: dict[str, str] = field(default_factory=dict)
    seeds: list[int] = field(default_factory=list)
    start_time_utc: str = ""
    end_time_utc: str = ""
    duration_seconds: float = 0.0
    hive_session_id: str = ""
    cost_estimate_usd: float = 0.0
    cost_actual_usd: float = 0.0
    n_probes: int = 0
    notes: str = ""


def git_sha(workspace: Path | None = None) -> str:
    """Return git HEAD SHA of the workspace, or 'unknown' if unavailable."""
    raise NotImplementedError("TODO: subprocess.run(['git','rev-parse','HEAD'], cwd=workspace)")


def hash_text(text: str) -> str:
    """SHA-256 hex digest of a string. Used for prompts + datasets."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_jsonl(path: Path) -> str:
    """SHA-256 of a JSONL file content (canonical, index-order preserved)."""
    raise NotImplementedError("TODO: stream file, sha256 line by line")


def collect_package_versions(packages: list[str]) -> dict[str, str]:
    """Return {pkg_name: version} for each importable package."""
    raise NotImplementedError("TODO: importlib.metadata.version for each package")


def write(manifest: Manifest, out_dir: Path) -> Path:
    """Write manifest.json to out_dir/manifest.json. Returns the path."""
    raise NotImplementedError("TODO: out_dir.mkdir + json.dump(asdict(manifest))")


def verify(manifest_path: Path) -> dict[str, Any]:
    """Reload a manifest and report which fields still resolve (git SHA reachable,
    package versions installed, dataset hash matches). Returns a diff report."""
    raise NotImplementedError("TODO: reload + cross-check + diff report")
