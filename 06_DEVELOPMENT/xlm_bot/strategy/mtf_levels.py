"""Multi-timeframe analysis engine.

Calculates per-timeframe: S/R zones, Fibonacci retracements, RSI, MACD,
volume profile.  Also fetches BTC and NASDAQ for cross-market correlation.

When S/R + fib + RSI align across 3+ timeframes = high-probability zone.
"""
from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from data.candles import fetch_coinbase_candles, resample_ohlcv


# Coinbase granularities: 60, 300, 900, 3600, 21600, 86400
_FETCH_MAP = {
    "1m":  {"gran": 60,    "days": 1},
    "5m":  {"gran": 300,   "days": 3},
    "15m": {"gran": 900,   "days": 10},
    "1h":  {"gran": 3600,  "days": 30},
    "1d":  {"gran": 86400, "days": 365},
}

_RESAMPLE_MAP = {
    "30m":  {"base": "15m", "rule": "30min"},
    "4h":   {"base": "1h",  "rule": "4h"},
    "1w":   {"base": "1d",  "rule": "W"},
    "1M":   {"base": "1d",  "rule": "ME"},
}

_FIB_LEVELS = [0.236, 0.382, 0.500, 0.618, 0.786]


# ── Indicator Calculations ────────────────────────────────────────────

def _rsi(closes: pd.Series, period: int = 14) -> float:
    """Calculate RSI for the last bar."""
    if len(closes) < period + 1:
        return 50.0  # neutral fallback
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if pd.notna(val) else 50.0


def _macd(closes: pd.Series) -> dict[str, float]:
    """Calculate MACD line, signal, histogram."""
    if len(closes) < 26:
        return {"macd": 0, "signal": 0, "hist": 0}
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    hist = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 7),
        "signal": round(float(signal_line.iloc[-1]), 7),
        "hist": round(float(hist.iloc[-1]), 7),
    }


def _volume_profile(df: pd.DataFrame) -> dict[str, Any]:
    """Calculate volume stats: current vs average, trend."""
    if df.empty or "volume" not in df.columns or len(df) < 5:
        return {"vol_ratio": 0, "vol_trend": "flat"}
    vol = df["volume"].astype(float)
    avg = vol.rolling(20, min_periods=5).mean().iloc[-1]
    current = vol.iloc[-1]
    ratio = round(current / avg, 2) if avg > 0 else 0
    recent_5 = vol.tail(5).mean()
    prior_5 = vol.tail(10).head(5).mean()
    trend = "rising" if recent_5 > prior_5 * 1.2 else ("falling" if recent_5 < prior_5 * 0.8 else "flat")
    return {"vol_ratio": ratio, "vol_trend": trend}


def _ema(closes: pd.Series, period: int) -> float:
    """Current EMA value."""
    if len(closes) < period:
        return float(closes.iloc[-1]) if len(closes) > 0 else 0
    return round(float(closes.ewm(span=period).mean().iloc[-1]), 6)


# ── S/R and Fib ───────────────────────────────────────────────────────

def _swing_high_low(df: pd.DataFrame, lookback: int | None = None) -> tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    d = df.tail(lookback) if lookback else df
    return float(d["high"].max()), float(d["low"].min())


def _fib_levels(high: float, low: float) -> dict[str, float]:
    if high <= low or high == 0:
        return {}
    diff = high - low
    return {
        f"fib_{int(lvl*1000)}": round(high - diff * lvl, 6)
        for lvl in _FIB_LEVELS
    }


def _find_sr_zones(df: pd.DataFrame, n_zones: int = 3) -> list[float]:
    if df.empty or len(df) < 5:
        return []
    pivots = []
    highs = df["high"].values
    lows = df["low"].values
    for i in range(2, len(df) - 2):
        if highs[i] >= max(highs[i-2], highs[i-1], highs[i+1], highs[i+2]):
            pivots.append(highs[i])
        if lows[i] <= min(lows[i-2], lows[i-1], lows[i+1], lows[i+2]):
            pivots.append(lows[i])
    if not pivots:
        return []
    pivots.sort()
    clusters: list[list[float]] = [[pivots[0]]]
    for p in pivots[1:]:
        if abs(p - clusters[-1][-1]) / max(clusters[-1][-1], 1e-9) < 0.005:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    clusters.sort(key=lambda c: len(c), reverse=True)
    return [round(sum(c) / len(c), 6) for c in clusters[:n_zones]]


# ── Per-Timeframe Analysis ────────────────────────────────────────────

def _analyze_tf(df: pd.DataFrame, label: str) -> dict[str, Any]:
    if df.empty or len(df) < 5:
        return {"tf": label, "bars": 0}
    swing_high, swing_low = _swing_high_low(df)
    fibs = _fib_levels(swing_high, swing_low)
    sr = _find_sr_zones(df)
    closes = df["close"].astype(float)
    current = float(closes.iloc[-1])
    rsi = _rsi(closes)
    macd = _macd(closes)
    vol = _volume_profile(df)
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    return {
        "tf": label,
        "bars": len(df),
        "high": round(swing_high, 6),
        "low": round(swing_low, 6),
        "current": round(current, 6),
        "range_pct": round((swing_high - swing_low) / swing_low * 100, 2) if swing_low > 0 else 0,
        "fibs": fibs,
        "sr_zones": sr,
        "rsi": rsi,
        "macd": macd,
        "vol": vol,
        "ema20": ema20,
        "ema50": ema50,
        "price_vs_ema": "above" if current > ema20 else "below",
        "ema_cross": "bullish" if ema20 > ema50 else "bearish",
    }


# ── Cross-Market Correlation ─────────────────────────────────────────

def _fetch_btc_context() -> dict[str, Any]:
    """Fetch BTC-USD for cross-market correlation."""
    try:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=3)
        df = fetch_coinbase_candles("BTC-USD", start, now, 3600)  # 1h candles
        if df.empty or len(df) < 10:
            return {}
        closes = df["close"].astype(float)
        current = float(closes.iloc[-1])
        h24_high = float(df.tail(24)["high"].max())
        h24_low = float(df.tail(24)["low"].min())
        rsi = _rsi(closes)
        macd = _macd(closes)
        pct_change_24h = round((current - float(closes.iloc[-24])) / float(closes.iloc[-24]) * 100, 2) if len(closes) >= 24 else 0
        return {
            "price": round(current, 2),
            "24h_range": f"${h24_low:,.0f}-${h24_high:,.0f}",
            "24h_change_pct": pct_change_24h,
            "rsi": rsi,
            "macd_hist": macd["hist"],
            "trend": "bullish" if current > _ema(closes, 20) else "bearish",
        }
    except Exception:
        return {}


def _fetch_nasdaq_context() -> dict[str, Any]:
    """Fetch ETH-USD as NASDAQ proxy (crypto markets correlate, no direct NASDAQ on Coinbase)."""
    try:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=3)
        # Use ETH as risk-on proxy (correlates with NASDAQ strongly)
        df = fetch_coinbase_candles("ETH-USD", start, now, 3600)
        if df.empty or len(df) < 10:
            return {}
        closes = df["close"].astype(float)
        current = float(closes.iloc[-1])
        rsi = _rsi(closes)
        pct_change_24h = round((current - float(closes.iloc[-24])) / float(closes.iloc[-24]) * 100, 2) if len(closes) >= 24 else 0
        return {
            "proxy": "ETH-USD",
            "price": round(current, 2),
            "24h_change_pct": pct_change_24h,
            "rsi": rsi,
            "trend": "bullish" if current > _ema(closes, 20) else "bearish",
        }
    except Exception:
        return {}


# ── Main Entry Points ─────────────────────────────────────────────────

def fetch_mtf_candles(product_id: str = "XLM-USD") -> dict[str, pd.DataFrame]:
    now = datetime.now(timezone.utc)
    frames: dict[str, pd.DataFrame] = {}
    for tf, cfg in _FETCH_MAP.items():
        try:
            start = now - timedelta(days=cfg["days"])
            df = fetch_coinbase_candles(product_id, start, now, cfg["gran"])
            if not df.empty:
                frames[tf] = df
        except Exception:
            pass
    for tf, cfg in _RESAMPLE_MAP.items():
        base_tf = cfg["base"]
        if base_tf in frames and not frames[base_tf].empty:
            try:
                resampled = resample_ohlcv(frames[base_tf], cfg["rule"])
                if not resampled.empty:
                    frames[tf] = resampled
            except Exception:
                pass
    return frames


def compute_mtf_levels(product_id: str = "XLM-USD") -> list[dict[str, Any]]:
    frames = fetch_mtf_candles(product_id)
    tf_order = ["1M", "1w", "1d", "4h", "1h", "30m", "15m", "5m", "1m"]
    results = []
    for tf in tf_order:
        if tf in frames:
            results.append(_analyze_tf(frames[tf], tf))
    return results


def compute_cross_market() -> dict[str, Any]:
    return {
        "btc": _fetch_btc_context(),
        "risk_proxy": _fetch_nasdaq_context(),
    }


def format_mtf_for_prompt(levels: list[dict], cross_market: dict | None = None) -> str:
    if not levels:
        return "(no multi-timeframe data)"
    lines = []

    for lv in levels:
        if lv.get("bars", 0) < 5:
            continue
        tf = lv["tf"]
        h = lv.get("high", 0)
        lo = lv.get("low", 0)
        rng = lv.get("range_pct", 0)
        fibs = lv.get("fibs", {})
        sr = lv.get("sr_zones", [])
        rsi = lv.get("rsi", 50)
        macd = lv.get("macd", {})
        vol = lv.get("vol", {})
        ema_cross = lv.get("ema_cross", "?")
        price_pos = lv.get("price_vs_ema", "?")

        # Line 1: Range + Fibs
        line = f"{tf:>3s}: ${lo:.5f}-${h:.5f} ({rng:.1f}%)"
        if fibs:
            fib50 = fibs.get("fib_500", 0)
            fib382 = fibs.get("fib_382", 0)
            fib618 = fibs.get("fib_618", 0)
            line += f" | Fib38={fib382:.5f} Fib50={fib50:.5f} Fib62={fib618:.5f}"
        lines.append(line)

        # Line 2: Indicators
        macd_hist = macd.get("hist", 0)
        macd_dir = "+" if macd_hist > 0 else "-" if macd_hist < 0 else "0"
        vol_ratio = vol.get("vol_ratio", 0)
        vol_trend = vol.get("vol_trend", "?")
        rsi_label = "OB" if rsi > 70 else ("OS" if rsi < 30 else "")

        ind_line = f"     RSI:{rsi:.0f}{rsi_label} MACD:{macd_dir}{abs(macd_hist):.6f} Vol:{vol_ratio:.1f}x({vol_trend}) EMA:{ema_cross} Price:{price_pos}"
        if sr:
            sr_str = ", ".join(f"{s:.5f}" for s in sr[:3])
            ind_line += f" S/R:[{sr_str}]"
        lines.append(ind_line)

    # Cross-market context
    if cross_market:
        lines.append("")
        lines.append("=== CROSS-MARKET CONTEXT ===")
        btc = cross_market.get("btc", {})
        if btc:
            lines.append(
                f"BTC: ${btc.get('price', 0):,.0f} ({btc.get('24h_change_pct', 0):+.1f}% 24h) "
                f"RSI:{btc.get('rsi', 0):.0f} MACD:{'+'if btc.get('macd_hist',0)>0 else '-'} "
                f"Trend:{btc.get('trend', '?')}"
            )
        risk = cross_market.get("risk_proxy", {})
        if risk:
            lines.append(
                f"ETH (risk proxy): ${risk.get('price', 0):,.0f} ({risk.get('24h_change_pct', 0):+.1f}% 24h) "
                f"RSI:{risk.get('rsi', 0):.0f} Trend:{risk.get('trend', '?')}"
            )
        # Correlation hint
        if btc and risk:
            btc_bull = btc.get("trend") == "bullish"
            risk_bull = risk.get("trend") == "bullish"
            if btc_bull and risk_bull:
                lines.append("SIGNAL: BTC + ETH both bullish → RISK-ON environment, favor LONGS on XLM")
            elif not btc_bull and not risk_bull:
                lines.append("SIGNAL: BTC + ETH both bearish → RISK-OFF environment, favor SHORTS on XLM")
            else:
                lines.append("SIGNAL: Mixed BTC/ETH signals → no clear cross-market bias")

    return "\n".join(lines)
