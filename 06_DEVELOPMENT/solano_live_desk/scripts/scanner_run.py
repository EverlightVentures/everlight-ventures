#!/usr/bin/env python3
"""Transcribe the latest Broadcastify archive blocks -> mapped scanner incidents.
Run on e5 (has faster-whisper). Scheduled every ~30 min by scanner.timer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sld import config, scanner_pipeline  # noqa: E402

config.load_env()
base = os.environ.get("SLD_STORE", os.path.join(os.path.dirname(__file__), "..", "store"))
n = scanner_pipeline.run(base)
print(f"scanner pipeline: stored {n} mapped scanner incidents")
