"""Internal volume/liquidity spike detector. Zero external cost."""
from collections import defaultdict, deque


class OrderbookSentinel:
    def __init__(self, spike_multiplier: float = 3.0, baseline_window_min: int = 5):
        self.spike_multiplier = spike_multiplier
        self.window_sec = baseline_window_min * 60
        self.history = defaultdict(deque)

    def record(self, market_id: str, volume_24h: float, liquidity: float, timestamp: float):
        d = self.history[market_id]
        d.append((timestamp, volume_24h, liquidity))
        cutoff = timestamp - self.window_sec
        while d and d[0][0] < cutoff:
            d.popleft()

    def check_spikes(self) -> list:
        alerts = []
        for market_id, hist in self.history.items():
            if len(hist) < 2:
                continue
            baseline_vol = sum(h[1] for h in list(hist)[:-1]) / (len(hist) - 1)
            baseline_liq = sum(h[2] for h in list(hist)[:-1]) / (len(hist) - 1)
            latest_vol = hist[-1][1]
            latest_liq = hist[-1][2]
            if baseline_vol > 0 and latest_vol / baseline_vol >= self.spike_multiplier:
                alerts.append({"market_id": market_id, "reason": "volume_spike",
                               "baseline": baseline_vol, "latest": latest_vol})
            if baseline_liq > 0 and latest_liq / baseline_liq >= self.spike_multiplier:
                alerts.append({"market_id": market_id, "reason": "liquidity_spike",
                               "baseline": baseline_liq, "latest": latest_liq})
        return alerts
