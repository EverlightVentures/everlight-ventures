"""Tests for the shared-services bridge. Slack + Blinko are mocked/offline;
the contract under test is graceful degradation -- a dead service never raises."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from kalshi_agent.notify import Notifier


class _Bet:
    id = "ORDER_1"
    market_id = "TOKEN_YES"
    outcome = "Yes"
    amount_usdc = "10"
    limit_price = "0.5"
    edge = 0.12


def test_order_placed_calls_branded_slack(tmp_path):
    n = Notifier(channel_trades="C_TRADES", channel_alerts="C_ALERTS")
    fake = MagicMock()
    with patch.object(n, "_slack", return_value=fake):
        ok = n.order_placed(_Bet())
    assert ok is True
    assert fake.post_branded_slack.call_count == 1
    _, kw = fake.post_branded_slack.call_args
    assert kw["channel"] == "C_TRADES"
    assert kw["category"] == "deal"


def test_halt_calls_branded_alert(tmp_path):
    n = Notifier(channel_trades="C_TRADES", channel_alerts="C_ALERTS")
    fake = MagicMock()
    with patch.object(n, "_slack", return_value=fake):
        ok = n.halted("reconcile_drift", "drift 10.00")
    assert ok is True
    _, kw = fake.post_branded_alert.call_args
    assert kw["channel"] == "C_ALERTS"
    assert kw["severity"] == "critical"


def test_slack_failure_degrades_not_raises(tmp_path):
    n = Notifier(channel_trades="C", channel_alerts="C")
    with patch.object(n, "_slack", side_effect=ImportError("no content_tools")):
        assert n.order_placed(_Bet()) is False
        assert n.halted("x", "y") is False


def test_disabled_notifier_is_noop(tmp_path):
    n = Notifier(channel_trades="C", channel_alerts="C", enabled=False)
    assert n.order_placed(_Bet()) is False
    assert n.halted("x", "y") is False


def test_brain_log_writes_local_even_when_remote_down(tmp_path):
    log_path = tmp_path / "brain.jsonl"
    n = Notifier(channel_trades="C", channel_alerts="C", brain_log_path=log_path)
    # Force all remote endpoints to fail
    with patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
        n.brain_log("test title", "test body")
    assert log_path.exists()
    row = json.loads(log_path.read_text().strip())
    assert row["title"] == "test title"


def test_cycle_summary_logs_to_brain(tmp_path):
    log_path = tmp_path / "brain.jsonl"
    n = Notifier(channel_trades="C", channel_alerts="C", brain_log_path=log_path)
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        n.cycle_summary({"placed": 2, "markets": 30, "halt": False})
    body = log_path.read_text()
    assert "2 placed" in body
