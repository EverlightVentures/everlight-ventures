#!/usr/bin/env python3
"""
Telemetry Logger - appends per-cycle telemetry to JSONL for live dashboards.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class TelemetryLogger:
    def __init__(self, log_dir: str = None, filename: str = "telemetry.jsonl"):
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.path = self.log_dir / filename

    def log_ping(self, data: Dict):
        record = dict(data)
        record.setdefault("timestamp", datetime.now().isoformat())
        with open(self.path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
