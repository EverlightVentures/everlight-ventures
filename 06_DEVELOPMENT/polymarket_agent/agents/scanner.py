"""Scanner (Cipher Wolfe). Filters Polymarket markets to top candidates."""
from datetime import datetime, timezone, timedelta


class Scanner:
    def __init__(self, min_liquidity: float = 5000, min_volume_24h: float = 1000,
                 min_hours_to_resolution: float = 4, max_spread: float = 0.05):
        self.min_liquidity = min_liquidity
        self.min_volume_24h = min_volume_24h
        self.min_hours_to_resolution = min_hours_to_resolution
        self.max_spread = max_spread

    def filter(self, markets: list) -> list:
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=self.min_hours_to_resolution)
        out = []
        for m in markets:
            if m.liquidity < self.min_liquidity:
                continue
            if m.volume_24h < self.min_volume_24h:
                continue
            if m.spread > self.max_spread:
                continue
            try:
                end_dt = datetime.fromisoformat(m.end_date.replace("Z", "+00:00"))
            except ValueError:
                continue
            if end_dt < cutoff:
                continue
            out.append(m)
        return out
