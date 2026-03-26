"""1-Minute Scalping Engine - 30 Strategies for XLP-20DEC30-CDE.

Activates during COMPRESSION when the swing system is idle.
Deactivates on IGNITION/EXPANSION to let swing trades run.
Separate risk bucket from sniper mode.

Each strategy: 1m candle signal + 5m trend filter + entry/SL/TP/direction/confidence.
Long and short are equal - no bias.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class ScalpSignal:
    """A scalp trade signal."""
    strategy_id: int
    strategy_name: str
    direction: str          # "long" or "short"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: int         # 0-100
    category: str           # "trend", "momentum", "microstructure"
    reason: str
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _bb(series: pd.Series, period: int = 20, std: float = 2.0):
    mid = series.rolling(period).mean()
    s = series.rolling(period).std()
    return mid, mid + std * s, mid - std * s

def _stoch(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def _vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol = (tp * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    return cum_tp_vol / cum_vol

def _keltner(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, mult: float = 1.5):
    mid = _ema(df["close"], ema_period)
    a = _atr(df, atr_period)
    return mid, mid + mult * a, mid - mult * a

def _trend_5m(df_5m: pd.DataFrame) -> str:
    """Determine 5m trend direction. Returns 'up', 'down', or 'flat'."""
    if df_5m is None or len(df_5m) < 10:
        return "flat"
    ema9 = _ema(df_5m["close"], 9)
    close = df_5m["close"]
    last_close = float(close.iloc[-1])
    last_ema = float(ema9.iloc[-1])
    prev_ema = float(ema9.iloc[-3])

    # Higher highs/lows check
    recent = df_5m.iloc[-5:]
    hh = float(recent["high"].iloc[-1]) > float(recent["high"].iloc[0])
    hl = float(recent["low"].iloc[-1]) > float(recent["low"].iloc[0])
    lh = float(recent["high"].iloc[-1]) < float(recent["high"].iloc[0])
    ll = float(recent["low"].iloc[-1]) < float(recent["low"].iloc[0])

    if last_close > last_ema and last_ema > prev_ema and (hh or hl):
        return "up"
    elif last_close < last_ema and last_ema < prev_ema and (lh or ll):
        return "down"
    return "flat"


# ---------------------------------------------------------------------------
# TREND SCALPS (1-10)
# ---------------------------------------------------------------------------

def _scalp_01_ema9_pullback(df_1m, df_5m, price, atr_val):
    """EMA9 pullback in 5m trend."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    ema9 = _ema(df_1m["close"], 9)
    last_ema = float(ema9.iloc[-1])
    prev_close = float(df_1m["close"].iloc[-2])
    curr_close = float(df_1m["close"].iloc[-1])
    vol_shrink = float(df_1m["volume"].iloc[-1]) < float(df_1m["volume"].iloc[-3:-1].mean())

    if trend == "up" and prev_close <= last_ema and curr_close > last_ema and vol_shrink:
        sl = float(df_1m["low"].iloc[-2])
        tp = price + (price - sl) * 1.5
        return ScalpSignal(1, "ema9_pullback", "long", price, sl, tp, 72, "trend",
            f"1m EMA9 pullback long in 5m uptrend at {price:.6f}")

    if trend == "down" and prev_close >= last_ema and curr_close < last_ema and vol_shrink:
        sl = float(df_1m["high"].iloc[-2])
        tp = price - (sl - price) * 1.5
        return ScalpSignal(1, "ema9_pullback", "short", price, sl, tp, 72, "trend",
            f"1m EMA9 pullback short in 5m downtrend at {price:.6f}")
    return None

def _scalp_02_vwap_retest(df_1m, df_5m, price, atr_val):
    """VWAP retest in trend."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    vw = _vwap(df_1m)
    last_vwap = float(vw.iloc[-1])
    if pd.isna(last_vwap) or last_vwap <= 0:
        return None

    near_vwap = abs(price - last_vwap) < atr_val * 0.3
    curr = df_1m.iloc[-1]
    bullish_candle = float(curr["close"]) > float(curr["open"])
    bearish_candle = float(curr["close"]) < float(curr["open"])

    if trend == "up" and near_vwap and bullish_candle:
        sl = last_vwap - atr_val * 0.5
        tp = price + atr_val * 1.0
        return ScalpSignal(2, "vwap_retest", "long", price, sl, tp, 70, "trend",
            f"VWAP retest long at {price:.6f}, VWAP={last_vwap:.6f}")

    if trend == "down" and near_vwap and bearish_candle:
        sl = last_vwap + atr_val * 0.5
        tp = price - atr_val * 1.0
        return ScalpSignal(2, "vwap_retest", "short", price, sl, tp, 70, "trend",
            f"VWAP retest short at {price:.6f}, VWAP={last_vwap:.6f}")
    return None

def _scalp_03_hl_lh_resumption(df_1m, df_5m, price, atr_val):
    """Higher-low (long) / lower-high (short) resumption."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    lows = [float(df_1m["low"].iloc[i]) for i in range(-4, 0)]
    highs = [float(df_1m["high"].iloc[i]) for i in range(-4, 0)]

    if trend == "up" and lows[-1] > lows[-2] and lows[-2] > lows[-3]:
        sl = lows[-1] - atr_val * 0.3
        tp = price + atr_val * 1.0
        return ScalpSignal(3, "hl_resumption", "long", price, sl, tp, 68, "trend",
            "Higher-low formation in 5m uptrend")

    if trend == "down" and highs[-1] < highs[-2] and highs[-2] < highs[-3]:
        sl = highs[-1] + atr_val * 0.3
        tp = price - atr_val * 1.0
        return ScalpSignal(3, "lh_resumption", "short", price, sl, tp, 68, "trend",
            "Lower-high formation in 5m downtrend")
    return None

def _scalp_04_channel_pullback(df_1m, df_5m, price, atr_val):
    """Channel pullback on 1m."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    _, bb_upper, bb_lower = _bb(df_1m["close"], 20, 2.0)
    bu = float(bb_upper.iloc[-1])
    bl = float(bb_lower.iloc[-1])
    if pd.isna(bu) or pd.isna(bl):
        return None

    if trend == "up" and abs(price - bl) < atr_val * 0.4:
        sl = bl - atr_val * 0.3
        tp = price + atr_val * 1.2
        return ScalpSignal(4, "channel_pullback", "long", price, sl, tp, 66, "trend",
            f"Channel lower band pullback long at {price:.6f}")

    if trend == "down" and abs(price - bu) < atr_val * 0.4:
        sl = bu + atr_val * 0.3
        tp = price - atr_val * 1.2
        return ScalpSignal(4, "channel_pullback", "short", price, sl, tp, 66, "trend",
            f"Channel upper band pullback short at {price:.6f}")
    return None

def _scalp_05_flag_breakout(df_1m, df_5m, price, atr_val):
    """1m flag/consolidation breakout in 5m trend."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    recent = df_1m.iloc[-6:-1]
    r_high = float(recent["high"].max())
    r_low = float(recent["low"].min())
    r_range = r_high - r_low
    if r_range > atr_val * 1.5 or r_range <= 0:
        return None  # not a tight consolidation

    if trend == "up" and price > r_high:
        sl = r_low
        tp = price + r_range * 2
        return ScalpSignal(5, "flag_breakout", "long", price, sl, tp, 74, "trend",
            f"1m flag breakout long above {r_high:.6f}")

    if trend == "down" and price < r_low:
        sl = r_high
        tp = price - r_range * 2
        return ScalpSignal(5, "flag_breakout", "short", price, sl, tp, 74, "trend",
            f"1m flag breakout short below {r_low:.6f}")
    return None

def _scalp_06_ma_swing(df_1m, df_5m, price, atr_val):
    """MA swing - price crosses and holds above/below EMA9."""
    ema9 = _ema(df_1m["close"], 9)
    ema20 = _ema(df_1m["close"], 20)
    e9 = float(ema9.iloc[-1])
    e20 = float(ema20.iloc[-1])
    prev_close = float(df_1m["close"].iloc[-2])
    curr_close = float(df_1m["close"].iloc[-1])

    if e9 > e20 and prev_close < e9 and curr_close > e9:
        sl = e20 - atr_val * 0.2
        tp = price + atr_val * 1.0
        return ScalpSignal(6, "ma_swing", "long", price, sl, tp, 65, "trend",
            "MA swing long - reclaimed EMA9 above EMA20")

    if e9 < e20 and prev_close > e9 and curr_close < e9:
        sl = e20 + atr_val * 0.2
        tp = price - atr_val * 1.0
        return ScalpSignal(6, "ma_swing", "short", price, sl, tp, 65, "trend",
            "MA swing short - lost EMA9 below EMA20")
    return None

def _scalp_07_liquidity_grab(df_1m, df_5m, price, atr_val):
    """Liquidity grab fade - spike through level then reverse."""
    recent_high = float(df_1m["high"].iloc[-10:-1].max())
    recent_low = float(df_1m["low"].iloc[-10:-1].min())
    curr = df_1m.iloc[-1]
    spiked_high = float(curr["high"]) > recent_high
    closed_below = float(curr["close"]) < recent_high
    spiked_low = float(curr["low"]) < recent_low
    closed_above = float(curr["close"]) > recent_low

    if spiked_high and closed_below:
        sl = float(curr["high"]) + atr_val * 0.2
        tp = price - atr_val * 1.0
        return ScalpSignal(7, "liq_grab_fade", "short", price, sl, tp, 76, "trend",
            f"Liquidity grab above {recent_high:.6f} - fading spike short")

    if spiked_low and closed_above:
        sl = float(curr["low"]) - atr_val * 0.2
        tp = price + atr_val * 1.0
        return ScalpSignal(7, "liq_grab_fade", "long", price, sl, tp, 76, "trend",
            f"Liquidity grab below {recent_low:.6f} - fading spike long")
    return None

def _scalp_08_volume_spike(df_1m, df_5m, price, atr_val):
    """Volume spike continuation in trend direction."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    vol_avg = float(df_1m["volume"].rolling(20).mean().iloc[-1])
    vol_now = float(df_1m["volume"].iloc[-1])
    if vol_avg <= 0 or vol_now < vol_avg * 1.8:
        return None
    curr = df_1m.iloc[-1]
    bullish = float(curr["close"]) > float(curr["open"])

    if trend == "up" and bullish:
        sl = float(curr["low"]) - atr_val * 0.2
        tp = price + atr_val * 1.0
        return ScalpSignal(8, "vol_spike", "long", price, sl, tp, 72, "trend",
            f"Volume spike {vol_now/vol_avg:.1f}x continuation long")

    if trend == "down" and not bullish:
        sl = float(curr["high"]) + atr_val * 0.2
        tp = price - atr_val * 1.0
        return ScalpSignal(8, "vol_spike", "short", price, sl, tp, 72, "trend",
            f"Volume spike {vol_now/vol_avg:.1f}x continuation short")
    return None

def _scalp_09_keltner_squeeze(df_1m, df_5m, price, atr_val):
    """Keltner channel squeeze breakout."""
    trend = _trend_5m(df_5m)
    _, ku, kl = _keltner(df_1m)
    ku_val = float(ku.iloc[-1])
    kl_val = float(kl.iloc[-1])
    if pd.isna(ku_val) or pd.isna(kl_val):
        return None

    if trend == "up" and price > ku_val:
        sl = kl_val
        tp = price + (ku_val - kl_val) * 0.5
        return ScalpSignal(9, "keltner_breakout", "long", price, sl, tp, 70, "trend",
            f"Keltner upper breakout long at {price:.6f}")

    if trend == "down" and price < kl_val:
        sl = ku_val
        tp = price - (ku_val - kl_val) * 0.5
        return ScalpSignal(9, "keltner_breakout", "short", price, sl, tp, 70, "trend",
            f"Keltner lower breakout short at {price:.6f}")
    return None

def _scalp_10_atr_breakout(df_1m, df_5m, price, atr_val):
    """ATR expansion breakout in 5m trend."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    atr_s = _atr(df_1m, 14)
    atr_now = float(atr_s.iloc[-1])
    atr_avg = float(atr_s.rolling(20).mean().iloc[-1])
    if pd.isna(atr_avg) or atr_avg <= 0 or atr_now < atr_avg * 1.5:
        return None
    curr = df_1m.iloc[-1]
    bullish = float(curr["close"]) > float(curr["open"])

    if trend == "up" and bullish:
        sl = price - atr_now * 1.0
        tp = price + atr_now * 1.5
        return ScalpSignal(10, "atr_breakout", "long", price, sl, tp, 74, "trend",
            f"ATR expansion {atr_now/atr_avg:.1f}x breakout long")

    if trend == "down" and not bullish:
        sl = price + atr_now * 1.0
        tp = price - atr_now * 1.5
        return ScalpSignal(10, "atr_breakout", "short", price, sl, tp, 74, "trend",
            f"ATR expansion {atr_now/atr_avg:.1f}x breakout short")
    return None


# ---------------------------------------------------------------------------
# MOMENTUM SCALPS (11-20)
# ---------------------------------------------------------------------------

def _scalp_11_rsi_pullback(df_1m, df_5m, price, atr_val):
    """RSI pullback in trend."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    r = _rsi(df_1m["close"], 14)
    rsi_val = float(r.iloc[-1])

    if trend == "up" and 30 <= rsi_val <= 42:
        sl = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(11, "rsi_pullback", "long", price, sl, tp, 68, "momentum",
            f"RSI pullback to {rsi_val:.0f} in uptrend")

    if trend == "down" and 58 <= rsi_val <= 70:
        sl = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(11, "rsi_pullback", "short", price, sl, tp, 68, "momentum",
            f"RSI pullback to {rsi_val:.0f} in downtrend")
    return None

def _scalp_12_rsi_extreme(df_1m, df_5m, price, atr_val):
    """RSI extreme fade."""
    r = _rsi(df_1m["close"], 14)
    rsi_val = float(r.iloc[-1])

    if rsi_val <= 18:
        sl = price - atr_val * 1.0
        tp = price + atr_val * 0.8
        return ScalpSignal(12, "rsi_extreme", "long", price, sl, tp, 72, "momentum",
            f"RSI extreme oversold {rsi_val:.0f} - mean reversion long")

    if rsi_val >= 82:
        sl = price + atr_val * 1.0
        tp = price - atr_val * 0.8
        return ScalpSignal(12, "rsi_extreme", "short", price, sl, tp, 72, "momentum",
            f"RSI extreme overbought {rsi_val:.0f} - mean reversion short")
    return None

def _scalp_13_stoch_cross(df_1m, df_5m, price, atr_val):
    """Stochastic crossover in extreme zones."""
    k, d = _stoch(df_1m)
    k_val = float(k.iloc[-1])
    k_prev = float(k.iloc[-2])
    d_val = float(d.iloc[-1])
    d_prev = float(d.iloc[-2])
    if pd.isna(k_val) or pd.isna(d_val):
        return None

    if k_val < 25 and k_prev < d_prev and k_val > d_val:
        sl = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(13, "stoch_cross", "long", price, sl, tp, 66, "momentum",
            f"Stochastic bullish cross at {k_val:.0f}")

    if k_val > 75 and k_prev > d_prev and k_val < d_val:
        sl = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(13, "stoch_cross", "short", price, sl, tp, 66, "momentum",
            f"Stochastic bearish cross at {k_val:.0f}")
    return None

def _scalp_14_macd_signal_cross(df_1m, df_5m, price, atr_val):
    """MACD signal line crossover."""
    trend = _trend_5m(df_5m)
    ml, sl_line, hist = _macd(df_1m["close"])
    h_now = float(hist.iloc[-1])
    h_prev = float(hist.iloc[-2])
    if pd.isna(h_now) or pd.isna(h_prev):
        return None

    if trend == "up" and h_prev < 0 and h_now > 0:
        sl_p = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(14, "macd_cross", "long", price, sl_p, tp, 68, "momentum",
            "MACD histogram flipped positive in uptrend")

    if trend == "down" and h_prev > 0 and h_now < 0:
        sl_p = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(14, "macd_cross", "short", price, sl_p, tp, 68, "momentum",
            "MACD histogram flipped negative in downtrend")
    return None

def _scalp_15_macd_hist_accel(df_1m, df_5m, price, atr_val):
    """MACD histogram acceleration."""
    _, _, hist = _macd(df_1m["close"])
    h = [float(hist.iloc[i]) for i in range(-3, 0)] + [float(hist.iloc[-1])]
    if any(pd.isna(x) for x in h):
        return None

    if h[-1] > h[-2] > h[-3] and h[-1] > 0:
        sl = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(15, "macd_accel", "long", price, sl, tp, 66, "momentum",
            "MACD histogram accelerating positive")

    if h[-1] < h[-2] < h[-3] and h[-1] < 0:
        sl = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(15, "macd_accel", "short", price, sl, tp, 66, "momentum",
            "MACD histogram accelerating negative")
    return None

def _scalp_16_bb_mean_reversion(df_1m, df_5m, price, atr_val):
    """Bollinger Band mean reversion."""
    mid, upper, lower = _bb(df_1m["close"], 20, 2.0)
    bu = float(upper.iloc[-1])
    bl = float(lower.iloc[-1])
    bm = float(mid.iloc[-1])
    if pd.isna(bu) or pd.isna(bl):
        return None

    if price <= bl * 1.001:
        sl = bl - atr_val * 0.5
        tp = bm
        return ScalpSignal(16, "bb_mean_rev", "long", price, sl, tp, 68, "momentum",
            f"BB lower band touch - mean reversion long to {bm:.6f}")

    if price >= bu * 0.999:
        sl = bu + atr_val * 0.5
        tp = bm
        return ScalpSignal(16, "bb_mean_rev", "short", price, sl, tp, 68, "momentum",
            f"BB upper band touch - mean reversion short to {bm:.6f}")
    return None

def _scalp_17_bb_trend_continuation(df_1m, df_5m, price, atr_val):
    """BB trend continuation - riding the band."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    _, upper, lower = _bb(df_1m["close"], 20, 2.0)
    bu = float(upper.iloc[-1])
    bl = float(lower.iloc[-1])
    curr = df_1m.iloc[-1]
    strong_close = abs(float(curr["close"]) - float(curr["open"])) > atr_val * 0.5

    if trend == "up" and price > bu and strong_close:
        sl = price - atr_val * 1.0
        tp = price + atr_val * 1.5
        return ScalpSignal(17, "bb_trend_cont", "long", price, sl, tp, 70, "momentum",
            "BB upper band breakout continuation long")

    if trend == "down" and price < bl and strong_close:
        sl = price + atr_val * 1.0
        tp = price - atr_val * 1.5
        return ScalpSignal(17, "bb_trend_cont", "short", price, sl, tp, 70, "momentum",
            "BB lower band breakout continuation short")
    return None

def _scalp_18_vwap_rsi_combo(df_1m, df_5m, price, atr_val):
    """VWAP + RSI combo."""
    trend = _trend_5m(df_5m)
    if trend == "flat":
        return None
    vw = _vwap(df_1m)
    r = _rsi(df_1m["close"], 14)
    vw_val = float(vw.iloc[-1])
    rsi_val = float(r.iloc[-1])
    if pd.isna(vw_val) or pd.isna(rsi_val):
        return None
    near_vwap = abs(price - vw_val) < atr_val * 0.3

    if trend == "up" and near_vwap and 40 <= rsi_val <= 55:
        sl = vw_val - atr_val * 0.5
        tp = price + atr_val * 1.0
        return ScalpSignal(18, "vwap_rsi", "long", price, sl, tp, 70, "momentum",
            f"VWAP+RSI({rsi_val:.0f}) combo long")

    if trend == "down" and near_vwap and 45 <= rsi_val <= 60:
        sl = vw_val + atr_val * 0.5
        tp = price - atr_val * 1.0
        return ScalpSignal(18, "vwap_rsi", "short", price, sl, tp, 70, "momentum",
            f"VWAP+RSI({rsi_val:.0f}) combo short")
    return None

def _scalp_19_momentum_spike_fade(df_1m, df_5m, price, atr_val):
    """Fade overextended 1m momentum spike."""
    r = _rsi(df_1m["close"], 14)
    rsi_val = float(r.iloc[-1])
    curr = df_1m.iloc[-1]
    body = abs(float(curr["close"]) - float(curr["open"]))

    if rsi_val > 80 and body > atr_val * 2.0:
        sl = float(curr["high"]) + atr_val * 0.3
        tp = price - body * 0.5
        return ScalpSignal(19, "spike_fade", "short", price, sl, tp, 64, "momentum",
            f"Overextended spike fade short RSI={rsi_val:.0f}")

    if rsi_val < 20 and body > atr_val * 2.0:
        sl = float(curr["low"]) - atr_val * 0.3
        tp = price + body * 0.5
        return ScalpSignal(19, "spike_fade", "long", price, sl, tp, 64, "momentum",
            f"Overextended spike fade long RSI={rsi_val:.0f}")
    return None

def _scalp_20_alma_stoch(df_1m, df_5m, price, atr_val):
    """ALMA direction + stochastic squeeze."""
    # Use EMA as ALMA proxy
    alma = _ema(df_1m["close"], 9)
    alma_slope = float(alma.iloc[-1]) - float(alma.iloc[-3])
    k, d = _stoch(df_1m)
    k_val = float(k.iloc[-1])
    if pd.isna(k_val):
        return None

    if alma_slope > 0 and 20 < k_val < 40:
        sl = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(20, "alma_stoch", "long", price, sl, tp, 64, "momentum",
            f"ALMA rising + stoch squeeze({k_val:.0f}) long")

    if alma_slope < 0 and 60 < k_val < 80:
        sl = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(20, "alma_stoch", "short", price, sl, tp, 64, "momentum",
            f"ALMA falling + stoch squeeze({k_val:.0f}) short")
    return None


# ---------------------------------------------------------------------------
# MICROSTRUCTURE SCALPS (21-30)
# ---------------------------------------------------------------------------

def _scalp_21_wall_touch(df_1m, df_5m, price, atr_val):
    """Bid/ask wall proximity - use recent highs/lows as proxy for order clusters."""
    r_high = float(df_1m["high"].iloc[-20:].max())
    r_low = float(df_1m["low"].iloc[-20:].min())
    near_high = abs(price - r_high) < atr_val * 0.2
    near_low = abs(price - r_low) < atr_val * 0.2

    if near_low:
        sl = r_low - atr_val * 0.3
        tp = price + atr_val * 0.8
        return ScalpSignal(21, "wall_touch", "long", price, sl, tp, 62, "microstructure",
            f"Support wall touch near {r_low:.6f}")
    if near_high:
        sl = r_high + atr_val * 0.3
        tp = price - atr_val * 0.8
        return ScalpSignal(21, "wall_touch", "short", price, sl, tp, 62, "microstructure",
            f"Resistance wall touch near {r_high:.6f}")
    return None

def _scalp_22_micro_breakout(df_1m, df_5m, price, atr_val):
    """Micro range breakout on 1m."""
    r5 = df_1m.iloc[-6:-1]
    r_high = float(r5["high"].max())
    r_low = float(r5["low"].min())
    r_range = r_high - r_low
    if r_range > atr_val * 2.0 or r_range <= 0:
        return None

    if price > r_high + atr_val * 0.1:
        sl = r_low
        tp = price + r_range
        return ScalpSignal(22, "micro_breakout", "long", price, sl, tp, 70, "microstructure",
            f"Micro breakout above {r_high:.6f}")
    if price < r_low - atr_val * 0.1:
        sl = r_high
        tp = price - r_range
        return ScalpSignal(22, "micro_breakout", "short", price, sl, tp, 70, "microstructure",
            f"Micro breakout below {r_low:.6f}")
    return None

def _scalp_23_one_tick_grab(df_1m, df_5m, price, atr_val):
    """One-tick liquidity grab and reverse."""
    curr = df_1m.iloc[-1]
    prev = df_1m.iloc[-2]
    prev_high = float(prev["high"])
    prev_low = float(prev["low"])
    curr_high = float(curr["high"])
    curr_low = float(curr["low"])
    curr_close = float(curr["close"])

    poked_high = curr_high > prev_high and curr_close < prev_high
    poked_low = curr_low < prev_low and curr_close > prev_low

    if poked_high:
        sl = curr_high + atr_val * 0.2
        tp = price - atr_val * 0.8
        return ScalpSignal(23, "one_tick_grab", "short", price, sl, tp, 74, "microstructure",
            f"Poked above {prev_high:.6f} and reversed - fade short")
    if poked_low:
        sl = curr_low - atr_val * 0.2
        tp = price + atr_val * 0.8
        return ScalpSignal(23, "one_tick_grab", "long", price, sl, tp, 74, "microstructure",
            f"Poked below {prev_low:.6f} and reversed - fade long")
    return None

def _scalp_24_tight_spread(df_1m, df_5m, price, atr_val):
    """Tight range micro-reversal when volatility is dead."""
    recent = df_1m.iloc[-5:]
    ranges = (recent["high"] - recent["low"]).values
    avg_range = float(np.mean(ranges))
    if avg_range > atr_val * 0.5:
        return None  # not tight enough

    r_high = float(recent["high"].max())
    r_low = float(recent["low"].min())
    if price - r_low < (r_high - r_low) * 0.25:
        sl = r_low - atr_val * 0.2
        tp = r_high
        return ScalpSignal(24, "tight_spread", "long", price, sl, tp, 60, "microstructure",
            "Tight spread micro-reversal long at range bottom")
    if r_high - price < (r_high - r_low) * 0.25:
        sl = r_high + atr_val * 0.2
        tp = r_low
        return ScalpSignal(24, "tight_spread", "short", price, sl, tp, 60, "microstructure",
            "Tight spread micro-reversal short at range top")
    return None

def _scalp_25_tick_vol_trend(df_1m, df_5m, price, atr_val):
    """Tick volume micro-trend."""
    vols = df_1m["volume"].iloc[-5:]
    closes = df_1m["close"].iloc[-5:]
    vol_rising = all(float(vols.iloc[i]) > float(vols.iloc[i-1]) for i in range(1, len(vols)))
    price_rising = all(float(closes.iloc[i]) > float(closes.iloc[i-1]) for i in range(1, len(closes)))
    price_falling = all(float(closes.iloc[i]) < float(closes.iloc[i-1]) for i in range(1, len(closes)))

    if vol_rising and price_rising:
        sl = price - atr_val * 0.8
        tp = price + atr_val * 1.0
        return ScalpSignal(25, "tick_vol_trend", "long", price, sl, tp, 68, "microstructure",
            "Rising tick volume + rising price - momentum long")
    if vol_rising and price_falling:
        sl = price + atr_val * 0.8
        tp = price - atr_val * 1.0
        return ScalpSignal(25, "tick_vol_trend", "short", price, sl, tp, 68, "microstructure",
            "Rising tick volume + falling price - momentum short")
    return None

def _scalp_26_washout_trap(df_1m, df_5m, price, atr_val):
    """Washout/trap level detection."""
    curr = df_1m.iloc[-1]
    wick_down = min(float(curr["open"]), float(curr["close"])) - float(curr["low"])
    wick_up = float(curr["high"]) - max(float(curr["open"]), float(curr["close"]))
    body = abs(float(curr["close"]) - float(curr["open"]))
    rng = float(curr["high"]) - float(curr["low"])
    if rng <= 0:
        return None

    if wick_down > body * 2.5 and wick_down > rng * 0.6:
        sl = float(curr["low"]) - atr_val * 0.2
        tp = price + atr_val * 0.8
        return ScalpSignal(26, "washout_trap", "long", price, sl, tp, 72, "microstructure",
            "Bear trap / washout with long lower wick")
    if wick_up > body * 2.5 and wick_up > rng * 0.6:
        sl = float(curr["high"]) + atr_val * 0.2
        tp = price - atr_val * 0.8
        return ScalpSignal(26, "washout_trap", "short", price, sl, tp, 72, "microstructure",
            "Bull trap / washout with long upper wick")
    return None

def _scalp_27_averaging_micro(df_1m, df_5m, price, atr_val):
    """Average into micro-move toward VWAP/EMA."""
    ema9 = _ema(df_1m["close"], 9)
    e9 = float(ema9.iloc[-1])
    vw = _vwap(df_1m)
    vw_val = float(vw.iloc[-1]) if not pd.isna(vw.iloc[-1]) else e9

    if price < e9 and price < vw_val and abs(price - e9) < atr_val * 0.5:
        sl = price - atr_val * 0.5
        tp = e9
        return ScalpSignal(27, "avg_micro", "long", price, sl, tp, 62, "microstructure",
            f"Averaging toward EMA9 {e9:.6f} from below")
    if price > e9 and price > vw_val and abs(price - e9) < atr_val * 0.5:
        sl = price + atr_val * 0.5
        tp = e9
        return ScalpSignal(27, "avg_micro", "short", price, sl, tp, 62, "microstructure",
            f"Averaging toward EMA9 {e9:.6f} from above")
    return None

def _scalp_28_time_window(df_1m, df_5m, price, atr_val):
    """Time-window scalp - early candle momentum."""
    if len(df_1m) < 3:
        return None
    curr = df_1m.iloc[-1]
    prev = df_1m.iloc[-2]
    curr_open = float(curr["open"])
    curr_close = float(curr["close"])
    prev_close = float(prev["close"])
    momentum = curr_close - curr_open
    vol_now = float(curr["volume"])
    vol_avg = float(df_1m["volume"].iloc[-10:].mean())

    if momentum > atr_val * 0.3 and vol_now > vol_avg * 1.3:
        sl = curr_open - atr_val * 0.3
        tp = price + atr_val * 0.8
        return ScalpSignal(28, "time_window", "long", price, sl, tp, 64, "microstructure",
            "Early candle strong bullish momentum")
    if momentum < -atr_val * 0.3 and vol_now > vol_avg * 1.3:
        sl = curr_open + atr_val * 0.3
        tp = price - atr_val * 0.8
        return ScalpSignal(28, "time_window", "short", price, sl, tp, 64, "microstructure",
            "Early candle strong bearish momentum")
    return None

def _scalp_29_news_micro(df_1m, df_5m, price, atr_val):
    """News micro-move - detect sudden ATR expansion on 1m."""
    atr_s = _atr(df_1m, 5)
    atr_now = float(atr_s.iloc[-1])
    atr_prev = float(atr_s.iloc[-3])
    if pd.isna(atr_now) or pd.isna(atr_prev) or atr_prev <= 0:
        return None
    if atr_now < atr_prev * 2.5:
        return None  # not a spike

    trend = _trend_5m(df_5m)
    curr = df_1m.iloc[-1]
    bullish = float(curr["close"]) > float(curr["open"])

    if trend != "down" and bullish:
        sl = price - atr_now * 1.0
        tp = price + atr_now * 1.0
        return ScalpSignal(29, "news_micro", "long", price, sl, tp, 66, "microstructure",
            f"ATR spike {atr_now/atr_prev:.1f}x - news/event micro long")
    if trend != "up" and not bullish:
        sl = price + atr_now * 1.0
        tp = price - atr_now * 1.0
        return ScalpSignal(29, "news_micro", "short", price, sl, tp, 66, "microstructure",
            f"ATR spike {atr_now/atr_prev:.1f}x - news/event micro short")
    return None

def _scalp_30_one_candle_reversion(df_1m, df_5m, price, atr_val):
    """One-candle reversion toward VWAP/EMA."""
    vw = _vwap(df_1m)
    vw_val = float(vw.iloc[-1]) if not pd.isna(vw.iloc[-1]) else 0
    ema9 = float(_ema(df_1m["close"], 9).iloc[-1])
    target = vw_val if vw_val > 0 else ema9
    if target <= 0:
        return None

    deviation = price - target
    if abs(deviation) < atr_val * 0.8:
        return None  # not far enough

    if deviation < 0:  # below target
        sl = price - atr_val * 0.5
        tp = target
        return ScalpSignal(30, "one_candle_rev", "long", price, sl, tp, 64, "microstructure",
            f"One-candle reversion long toward {target:.6f}")
    else:  # above target
        sl = price + atr_val * 0.5
        tp = target
        return ScalpSignal(30, "one_candle_rev", "short", price, sl, tp, 64, "microstructure",
            f"One-candle reversion short toward {target:.6f}")


# ---------------------------------------------------------------------------
# MASTER SCANNER
# ---------------------------------------------------------------------------

ALL_SCALP_STRATEGIES = [
    _scalp_01_ema9_pullback, _scalp_02_vwap_retest, _scalp_03_hl_lh_resumption,
    _scalp_04_channel_pullback, _scalp_05_flag_breakout, _scalp_06_ma_swing,
    _scalp_07_liquidity_grab, _scalp_08_volume_spike, _scalp_09_keltner_squeeze,
    _scalp_10_atr_breakout,
    _scalp_11_rsi_pullback, _scalp_12_rsi_extreme, _scalp_13_stoch_cross,
    _scalp_14_macd_signal_cross, _scalp_15_macd_hist_accel, _scalp_16_bb_mean_reversion,
    _scalp_17_bb_trend_continuation, _scalp_18_vwap_rsi_combo, _scalp_19_momentum_spike_fade,
    _scalp_20_alma_stoch,
    _scalp_21_wall_touch, _scalp_22_micro_breakout, _scalp_23_one_tick_grab,
    _scalp_24_tight_spread, _scalp_25_tick_vol_trend, _scalp_26_washout_trap,
    _scalp_27_averaging_micro, _scalp_28_time_window, _scalp_29_news_micro,
    _scalp_30_one_candle_reversion,
]


def scan_scalp_signals(
    df_1m: pd.DataFrame,
    df_5m: pd.DataFrame,
    price: float,
    config: dict = None,
) -> list[ScalpSignal]:
    """Scan all 30 scalp strategies and return matching signals.

    Args:
        df_1m: 1-minute OHLCV DataFrame (needs 25+ rows)
        df_5m: 5-minute OHLCV DataFrame (for trend filter)
        price: current live price
        config: scalping_mode config dict

    Returns:
        List of ScalpSignal sorted by confidence (highest first).
    """
    if df_1m is None or len(df_1m) < 25:
        return []

    cfg = config or {}
    atr_s = _atr(df_1m, 14)
    atr_val = float(atr_s.iloc[-1]) if not pd.isna(atr_s.iloc[-1]) else 0.0001
    if atr_val <= 0:
        atr_val = 0.0001

    min_profit = float(cfg.get("min_profit_usd", 1.50) or 1.50)
    contract_size = float(cfg.get("contract_size", 5000) or 5000)

    signals = []
    for fn in ALL_SCALP_STRATEGIES:
        try:
            sig = fn(df_1m, df_5m, price, atr_val)
            if sig is not None:
                # Validate minimum profit potential
                move = abs(sig.take_profit - sig.entry_price)
                potential_usd = move * contract_size
                if potential_usd >= min_profit:
                    sig.meta["potential_usd"] = round(potential_usd, 2)
                    sig.meta["risk_usd"] = round(abs(sig.stop_loss - sig.entry_price) * contract_size, 2)
                    signals.append(sig)
        except Exception:
            continue

    signals.sort(key=lambda s: s.confidence, reverse=True)
    return signals


def pick_best_scalp(signals: list[ScalpSignal], config: dict = None) -> Optional[ScalpSignal]:
    """Pick the single best scalp signal from the list.

    Prefers: highest confidence, then best R:R ratio.
    """
    if not signals:
        return None

    cfg = config or {}
    min_confidence = int(cfg.get("min_confidence", 65) or 65)
    min_rr = float(cfg.get("min_rr", 1.0) or 1.0)

    for sig in signals:
        risk = abs(sig.stop_loss - sig.entry_price)
        reward = abs(sig.take_profit - sig.entry_price)
        rr = reward / risk if risk > 0 else 0

        if sig.confidence >= min_confidence and rr >= min_rr:
            sig.meta["rr_ratio"] = round(rr, 2)
            return sig

    return None
