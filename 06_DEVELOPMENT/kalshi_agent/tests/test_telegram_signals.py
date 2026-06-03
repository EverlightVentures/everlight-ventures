import json
from pathlib import Path
from kalshi_agent.dataflows.telegram_signals import TelegramBridge


def test_reads_jsonl_ledger_filters_by_age(tmp_path: Path):
    ledger = tmp_path / "telegram_signals.jsonl"
    ledger.write_text(
        json.dumps({"text": "fresh", "ts": 1764345600, "channel": "x"}) + "\n" +
        json.dumps({"text": "stale", "ts": 1764000000, "channel": "y"}) + "\n"
    )
    bridge = TelegramBridge(ledger_path=ledger, now_ts=1764345700)
    signals = bridge.get_recent_signals(last_minutes=10)
    assert len(signals) == 1
    assert signals[0].text == "fresh"
    assert signals[0].source == "telegram"
