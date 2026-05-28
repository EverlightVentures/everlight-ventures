"""Telegram Bot API mirror-channel reader. Bot daemon writes ledger; this reads it."""
import json
import time
from pathlib import Path

from polymarket_agent.dataflows.interface import Signal


class TelegramBridge:
    def __init__(self, ledger_path: Path, now_ts: float | None = None):
        self.ledger_path = Path(ledger_path)
        self._now_ts = now_ts

    def _now(self) -> float:
        return self._now_ts if self._now_ts is not None else time.time()

    def get_recent_signals(self, last_minutes: int = 10) -> list:
        if not self.ledger_path.exists():
            return []
        cutoff = self._now() - last_minutes * 60
        signals = []
        for line in self.ledger_path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("ts", 0) < cutoff:
                continue
            signals.append(Signal(
                source="telegram",
                text=row.get("text", ""),
                author=row.get("channel", ""),
                timestamp=str(row.get("ts", "")),
                credibility=0.80,
            ))
        return signals
