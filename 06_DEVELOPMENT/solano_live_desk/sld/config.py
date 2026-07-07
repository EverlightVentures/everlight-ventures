from __future__ import annotations

import os
from pathlib import Path

_ENV = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: str | Path | None = None) -> None:
    """Load KEY=VALUE lines from a gitignored .env into os.environ (once).

    Existing environment variables win, so real exported secrets override the
    file. Blank lines and '#' comments are ignored. No external dependency.
    """
    p = Path(path) if path else _ENV
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())
