from kalshi_agent.dataflows.orderbook_sentinel import OrderbookSentinel


def test_sentinel_fires_on_3x_volume_spike():
    s = OrderbookSentinel(spike_multiplier=3.0, baseline_window_min=5)
    s.record("mkt_1", volume_24h=1000.0, liquidity=5000.0, timestamp=0)
    s.record("mkt_1", volume_24h=1100.0, liquidity=5100.0, timestamp=60)
    s.record("mkt_1", volume_24h=1200.0, liquidity=5200.0, timestamp=120)
    alerts = s.check_spikes()
    assert alerts == []

    s.record("mkt_1", volume_24h=4500.0, liquidity=5300.0, timestamp=180)
    alerts = s.check_spikes()
    assert len(alerts) == 1
    assert alerts[0]["market_id"] == "mkt_1"
    assert alerts[0]["reason"] == "volume_spike"


def test_sentinel_fires_on_liquidity_spike():
    s = OrderbookSentinel(spike_multiplier=3.0, baseline_window_min=5)
    for i in range(4):
        s.record(f"mkt_2", volume_24h=1000.0, liquidity=1000.0, timestamp=i * 60)
    s.record("mkt_2", volume_24h=1000.0, liquidity=4000.0, timestamp=240)
    alerts = s.check_spikes()
    assert any(a["reason"] == "liquidity_spike" for a in alerts)
