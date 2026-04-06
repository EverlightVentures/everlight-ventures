#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
BOT_DIR = WORKSPACE / "06_DEVELOPMENT" / "xlm_bot"

if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

from trading_watchtower_sync import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
