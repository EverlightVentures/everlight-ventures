"""Load hive mind configuration from roster.yaml."""

from pathlib import Path

import yaml

ROSTER_PATH = Path(__file__).parent / "roster.yaml"
WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
AI_WORKERS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "ai_workers"
AGENT_DIR = WORKSPACE / ".claude" / "agents"


def load_roster() -> dict:
    with open(ROSTER_PATH) as f:
        return yaml.safe_load(f)


def get_wrapper_path(name: str) -> str:
    """Get the full path to an AI worker wrapper script."""
    paths = {
        "clx_delegate": str(AI_WORKERS / "clx_delegate.py"),
        "gmx_delegate": str(AI_WORKERS / "gemx_delegate.py"),
        "ppx_terminal": str(AI_WORKERS / "ppx_terminal.py"),
        "cx_terminal": str(AI_WORKERS / "cx_terminal.py"),
    }
    return paths.get(name, name)
