"""Contract-specific data layer for XLM Perpetual Futures.

Fetches and caches mark price, index price, open interest, basis,
and estimated funding rate from existing Coinbase API endpoints.
"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class ContractSnapshot:
    timestamp: str = ""
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    basis: Optional[float] = None
    basis_bps: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    oi_delta_1m: Optional[float] = None
    oi_delta_5m: Optional[float] = None
    oi_delta_15m: Optional[float] = None
    oi_trend: str = "UNKNOWN"
    funding_rate_hr: Optional[float] = None
    funding_bias: str = "UNKNOWN"
    contract_size: Optional[float] = None
    volume_24h: Optional[float] = None
    oi_price_rel: str = "UNKNOWN"


class ContractContext:
    """Fetches and caches contract-specific data for the perp."""

    def __init__(
        self,
        api,
        perp_product_id: str,
        spot_product_id: str,
        cache_dir: Path,
        logs_dir: Path,
        config: dict | None = None,
    ):
        self._api = api
        self._perp_id = perp_product_id
        self._spot_id = spot_product_id
        self._cache_dir = Path(cache_dir)
        self._logs_dir = Path(logs_dir)

        cfg = config or {}
        self._stale_seconds = float(cfg.get("stale_seconds", 25.0) or 25.0)
        self._max_history = int(cfg.get("max_history", 200) or 200)

        self._oi_ring: deque[tuple[float, float]] = deque(maxlen=self._max_history)
        self._last_snap: Optional[ContractSnapshot] = None
        self._last_fetch_ts: float = 0.0
        self._prev_price: Optional[float] = None

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._backfill_ring()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self) -> ContractSnapshot:
        """Fetch fresh data or return cached if still valid."""
        now = time.time()
        if self._last_snap and (now - self._last_fetch_ts) < self._stale_seconds:
            return self._last_snap

        ts_iso = datetime.now(timezone.utc).isoformat()

        mark, oi_raw, cs, vol24 = self._fetch_perp_details()
        index = self._fetch_index()

        basis = None
        basis_bps = None
        if mark is not None and index is not None and index > 0:
            basis = mark - index
            basis_bps = basis / index * 10000.0

        oi_usd = None
        if oi_raw is not None and cs is not None and mark is not None:
            oi_usd = oi_raw * cs * mark

        # OI deltas
        deltas = self._compute_oi_deltas(oi_raw, now)
        oi_trend = self._classify_oi_trend(deltas.get("d5m"), deltas.get("d15m"))

        # Funding estimate from basis
        funding_hr = None
        if basis_bps is not None:
            funding_hr = basis_bps / 24.0  # rough hourly estimate
        funding_bias = self._classify_funding_bias(basis_bps)

        # OI+Price relationship
        price_delta = None
        if mark is not None and self._prev_price is not None and self._prev_price > 0:
            price_delta = (mark - self._prev_price) / self._prev_price
        oi_price_rel = self._classify_oi_price(price_delta, deltas.get("d15m"))

        snap = ContractSnapshot(
            timestamp=ts_iso,
            mark_price=mark,
            index_price=index,
            basis=basis,
            basis_bps=_r(basis_bps, 2),
            open_interest=oi_raw,
            open_interest_usd=_r(oi_usd, 2),
            oi_delta_1m=_r(deltas.get("d1m"), 4),
            oi_delta_5m=_r(deltas.get("d5m"), 4),
            oi_delta_15m=_r(deltas.get("d15m"), 4),
            oi_trend=oi_trend,
            funding_rate_hr=_r(funding_hr, 6),
            funding_bias=funding_bias,
            contract_size=cs,
            volume_24h=vol24,
            oi_price_rel=oi_price_rel,
        )

        # Store OI reading
        if oi_raw is not None:
            self._oi_ring.append((now, oi_raw))
        self._prev_price = mark

        self._last_snap = snap
        self._last_fetch_ts = now
        self._persist(snap)
        return snap

    def get_latest(self) -> Optional[ContractSnapshot]:
        return self._last_snap

    def as_dict(self) -> dict:
        if self._last_snap:
            return asdict(self._last_snap)
        return {}

    # ------------------------------------------------------------------
    # Data fetching (all wrapped in try/except)
    # ------------------------------------------------------------------

    def _fetch_perp_details(self) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Returns (mark_price, open_interest, contract_size, volume_24h)."""
        try:
            d = self._api.get_product_details(self._perp_id)
            if not d:
                return None, None, None, None
            mark = _flt(d.get("price") or d.get("mid_market_price"))
            fd = d.get("future_product_details") or {}
            oi = _flt(fd.get("open_interest"))
            cs = _flt(fd.get("contract_size"))
            vol = _flt(d.get("volume_24h"))
            return mark, oi, cs, vol
        except Exception:
            return None, None, None, None

    def _fetch_index(self) -> Optional[float]:
        """Returns spot/index price for the underlying."""
        try:
            d = self._api.get_product_details(self._spot_id)
            if not d:
                return None
            return _flt(d.get("price") or d.get("mid_market_price"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # OI delta computation
    # ------------------------------------------------------------------

    def _compute_oi_deltas(self, current_oi: Optional[float], now: float) -> dict:
        out: dict[str, Optional[float]] = {"d1m": None, "d5m": None, "d15m": None}
        if current_oi is None or not self._oi_ring:
            return out
        for key, secs in [("d1m", 60), ("d5m", 300), ("d15m", 900)]:
            past_oi = self._find_nearest_oi(now - secs)
            if past_oi is not None and past_oi > 0:
                out[key] = (current_oi - past_oi) / past_oi
        return out

    def _find_nearest_oi(self, target_ts: float) -> Optional[float]:
        best = None
        best_gap = float("inf")
        for ts, oi in self._oi_ring:
            gap = abs(ts - target_ts)
            if gap < best_gap:
                best_gap = gap
                best = oi
        # Only use if within 2x the target window
        if best is not None and best_gap < 120:
            return best
        return None

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_oi_trend(d5m: Optional[float], d15m: Optional[float]) -> str:
        if d5m is None or d15m is None:
            return "UNKNOWN"
        if d5m > 0.005 and d15m > 0.005:
            return "RISING"
        if d5m < -0.005 and d15m < -0.005:
            return "FALLING"
        return "FLAT"

    @staticmethod
    def _classify_funding_bias(basis_bps: Optional[float]) -> str:
        if basis_bps is None:
            return "UNKNOWN"
        if basis_bps > 5.0:
            return "LONGS_PAY"
        if basis_bps < -5.0:
            return "SHORTS_PAY"
        return "NEUTRAL"

    @staticmethod
    def _classify_oi_price(price_delta: Optional[float], oi_delta: Optional[float]) -> str:
        if price_delta is None or oi_delta is None:
            return "UNKNOWN"
        price_up = price_delta > 0.001
        price_down = price_delta < -0.001
        oi_up = oi_delta > 0.002
        oi_down = oi_delta < -0.002
        if price_up and oi_up:
            return "UP+OI_UP"
        if price_up and oi_down:
            return "UP+OI_DOWN"
        if price_down and oi_up:
            return "DOWN+OI_UP"
        if price_down and oi_down:
            return "DOWN+OI_DOWN"
        return "NEUTRAL"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, snap: ContractSnapshot) -> None:
        d = asdict(snap)
        # Atomic write to cache file
        cache_file = self._cache_dir / "contract_context.json"
        tmp = cache_file.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(d, default=str))
            tmp.replace(cache_file)
        except Exception:
            pass
        # Append to history JSONL
        try:
            hist = self._logs_dir / "contract_context.jsonl"
            with open(hist, "a") as f:
                f.write(json.dumps(d, default=str) + "\n")
        except Exception:
            pass

    def _backfill_ring(self) -> None:
        """Load last N entries from history JSONL to populate OI ringbuffer."""
        hist = self._logs_dir / "contract_context.jsonl"
        if not hist.exists():
            return
        try:
            lines: list[str] = []
            with open(hist, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        lines.append(line)
            # Only keep last max_history lines
            for line in lines[-self._max_history:]:
                try:
                    d = json.loads(line)
                    ts_str = d.get("timestamp")
                    oi = _flt(d.get("open_interest"))
                    if ts_str and oi is not None:
                        ts = datetime.fromisoformat(str(ts_str)).timestamp()
                        self._oi_ring.append((ts, oi))
                    price = _flt(d.get("mark_price"))
                    if price is not None:
                        self._prev_price = price
                except Exception:
                    continue
        except Exception:
            pass


def _flt(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _r(v: Optional[float], digits: int) -> Optional[float]:
    if v is None:
        return None
    return round(v, digits)
