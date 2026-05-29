"""Scanner (Cipher Wolfe). Filters Polymarket markets to tradeable candidates,
encoding the evidence-based strategy (STRATEGY.md): objective resolution only,
liquid enough to exit, right time window. The favorite-longshot edge itself is
realized downstream (predictor evaluates both sides + fades overpriced longshots)."""
from datetime import datetime, timezone, timedelta

# Categories with SUBJECTIVE resolution -- worst-calibrated, never forecast them
# (research: novelty/awards/pop-culture Brier ~0.23, barely better than random).
SUBJECTIVE_CATEGORIES = {
    "pop culture", "pop-culture", "culture", "awards", "entertainment",
    "celebrity", "novelty", "memes", "mention", "tweets",
}


class Scanner:
    def __init__(self, min_liquidity: float = 5000, min_volume_24h: float = 1000,
                 min_hours_to_resolution: float = 4, max_spread: float = 0.05,
                 skip_subjective: bool = True):
        self.min_liquidity = min_liquidity
        self.min_volume_24h = min_volume_24h
        self.min_hours_to_resolution = min_hours_to_resolution
        self.max_spread = max_spread
        self.skip_subjective = skip_subjective

    def _is_subjective(self, m) -> bool:
        cat = (getattr(m, "category", "") or "").strip().lower()
        if cat in SUBJECTIVE_CATEGORIES:
            return True
        # Heuristic: joke/novelty phrasing in the question is a subjective tell.
        q = (getattr(m, "question", "") or "").lower()
        return any(tell in q for tell in ("before gta", "before gta vi", "jesus", "alien"))

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
            if self.skip_subjective and self._is_subjective(m):
                continue  # objective-resolution only -- per STRATEGY.md
            try:
                end_dt = datetime.fromisoformat(m.end_date.replace("Z", "+00:00"))
            except ValueError:
                continue
            if end_dt < cutoff:
                continue
            out.append(m)
        return out
