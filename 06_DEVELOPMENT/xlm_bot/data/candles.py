from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests


@dataclass
class CandleStore:
    data_dir: Path

    def _path(self, symbol: str, timeframe: str) -> Path:
        return self.data_dir / f"{symbol.replace('/', '-')}_{timeframe}.csv"

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        path = self._path(symbol, timeframe)
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    def save(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        path = self._path(symbol, timeframe)
        df.to_csv(path, index=False)


def fetch_coinbase_candles(product_id: str, start: datetime, end: datetime, granularity: int) -> pd.DataFrame:
    """Fetch candles with pagination (Coinbase returns max 300 per request)."""
    import time as _time

    url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
    max_candles = 300
    chunk_seconds = max_candles * granularity
    all_data = []
    started = _time.time()
    req_timeout_s = float(os.environ.get("XLM_FETCH_TIMEOUT_S", "6"))
    max_runtime_s = float(os.environ.get("XLM_FETCH_MAX_RUNTIME_S", "30"))
    fail_streak = 0
    max_fail_streak = int(os.environ.get("XLM_FETCH_MAX_FAIL_STREAK", "3"))

    current_start = start
    while current_start < end:
        if (_time.time() - started) > max_runtime_s:
            break
        current_end = min(current_start + timedelta(seconds=chunk_seconds), end)
        params = {
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            "granularity": granularity,
        }
        try:
            resp = requests.get(url, params=params, timeout=req_timeout_s)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    all_data.extend(data)
                fail_streak = 0
            else:
                fail_streak += 1
        except requests.RequestException:
            fail_streak += 1
        if fail_streak >= max_fail_streak:
            break
        current_start = current_end
        _time.sleep(min(0.3 * (2 ** fail_streak), 5.0))  # Exponential backoff on errors; 0.3s base

    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=["timestamp", "low", "high", "open", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.set_index("timestamp")
    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule).agg(ohlc).dropna()
    out = out.reset_index()
    return out


def ensure_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "15m":
        return resample_ohlcv(df, "15min")
    if timeframe == "1h":
        return resample_ohlcv(df, "1h")
    if timeframe == "4h":
        return resample_ohlcv(df, "4h")
    return df


def _is_stale(df: pd.DataFrame, max_age_minutes: int = 30) -> bool:
    """Check if the most recent candle is older than max_age_minutes."""
    if df.empty:
        return True
    last_ts = pd.to_datetime(df["timestamp"].iloc[-1], utc=True)
    age = datetime.now(timezone.utc) - last_ts
    return age > timedelta(minutes=max_age_minutes)


def load_or_fetch(store: CandleStore, product_id: str, symbol: str, timeframe: str, days: int = 30) -> pd.DataFrame:
    df = store.load(symbol, timeframe)
    if not df.empty and not _is_stale(df):
        return df

    # Always fetch fresh 15m base data and rebuild higher timeframes
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    base = fetch_coinbase_candles(product_id, start, end, granularity=900)
    if base.empty:
        # Fall back to cached data if fetch fails
        return df if not df.empty else base

    # Guard: never overwrite good cached data with a partial/truncated fetch.
    # A partial fetch happens when the API times out mid-pagination — the
    # result covers Jan 5→Jan 30 instead of Jan 5→now, so iloc[-1] would
    # return a price from weeks ago, causing phantom trades.
    if not df.empty and len(base) < len(df) * 0.8:
        # Fetch got fewer rows than cache — likely truncated.  Merge instead
        # of overwriting: keep the cache and append any newer rows from fetch.
        cached_last_ts = pd.to_datetime(df["timestamp"].iloc[-1], utc=True)
        new_rows = base[base["timestamp"] > cached_last_ts]
        if not new_rows.empty:
            base = pd.concat([df, new_rows]).drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        else:
            # Fetch is strictly older/shorter — keep cache as-is
            base = df

    # Extra guard: reject fetch if latest candle is more than 60 min old
    # (means we got stale data that would feed wrong prices to the bot)
    if not base.empty:
        _fetch_last_ts = pd.to_datetime(base["timestamp"].iloc[-1], utc=True)
        _fetch_age = datetime.now(timezone.utc) - _fetch_last_ts
        if _fetch_age > timedelta(minutes=60) and not df.empty:
            _cache_last_ts = pd.to_datetime(df["timestamp"].iloc[-1], utc=True)
            if _cache_last_ts > _fetch_last_ts:
                base = df  # cache is more recent — keep it

    # Save fresh 15m data
    store.save(symbol, "15m", base)

    # Build requested timeframe
    fresh = ensure_timeframe(base, timeframe)
    if not fresh.empty:
        store.save(symbol, timeframe, fresh)
    return fresh
