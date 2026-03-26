"""Trend Reversal Engine - 30 Crypto-Tailored Reversal Strategies.

Detects trend exhaustion and reversal setups across multiple timeframes.
Designed for XLM perp (XLP-20DEC30-CDE) but works on any crypto pair.

These strategies identify WHEN a trend is ending and WHERE the reversal starts.
They feed into the existing lane scoring system as additional entry signals.
Long and short reversals are equal -- no directional bias.

Does NOT modify gates, thresholds, or risk management. Pure signal detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np


@dataclass
class ReversalSignal:
    """A trend reversal signal."""
    strategy_id: int
    strategy_name: str
    direction: str          # "long" or "short"
    confidence: int         # 0-100
    category: str           # "chart_pattern", "trendline", "indicator"
    timeframe: str          # primary TF this was detected on
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def _sma(s, p):
    return s.rolling(p).mean()

def _rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0.0).rolling(p).mean()
    l = (-d.where(d < 0, 0.0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l))

def _atr(df, p=14):
    tr = pd.concat([df["high"]-df["low"], (df["high"]-df["close"].shift(1)).abs(), (df["low"]-df["close"].shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def _macd(s, f=12, sl=26, sig=9):
    m = s.ewm(span=f).mean() - s.ewm(span=sl).mean()
    si = m.ewm(span=sig).mean()
    return m, si, m - si

def _bb(s, p=20, std=2.0):
    mid = s.rolling(p).mean()
    st = s.rolling(p).std()
    return mid, mid + std*st, mid - std*st

def _swing_highs(highs, order=3):
    pts = []
    for i in range(order, len(highs)-order):
        if all(highs[i] > highs[i-j] for j in range(1, order+1)) and all(highs[i] > highs[i+j] for j in range(1, order+1)):
            pts.append((i, float(highs[i])))
    return pts

def _swing_lows(lows, order=3):
    pts = []
    for i in range(order, len(lows)-order):
        if all(lows[i] < lows[i-j] for j in range(1, order+1)) and all(lows[i] < lows[i+j] for j in range(1, order+1)):
            pts.append((i, float(lows[i])))
    return pts

def _trend_dir(df, lookback=20):
    if len(df) < lookback:
        return "flat"
    c = df["close"].iloc[-lookback:]
    if float(c.iloc[-1]) > float(c.iloc[0]) * 1.01:
        return "up"
    elif float(c.iloc[-1]) < float(c.iloc[0]) * 0.99:
        return "down"
    return "flat"

def _vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    return (tp * df["volume"]).cumsum() / df["volume"].cumsum()


# ---------------------------------------------------------------------------
# CHART PATTERN REVERSALS (1-10)
# ---------------------------------------------------------------------------

def _rev_01_inverse_hs(df, price, atr_val):
    """Inverse head & shoulders - bullish reversal from downtrend."""
    if _trend_dir(df, 40) != "down" or len(df) < 30:
        return None
    lows = _swing_lows(df["low"].values, 3)
    if len(lows) < 3:
        return None
    l1, l2, l3 = lows[-3], lows[-2], lows[-1]
    if not (l2[1] < l1[1] and l2[1] < l3[1]):
        return None
    neckline = max(df["high"].iloc[l1[0]:l3[0]+1].max(), df["high"].iloc[l2[0]:l3[0]+1].max())
    if price > neckline:
        sl = l2[1] - atr_val * 0.5
        tp = price + (neckline - l2[1])
        return ReversalSignal(1, "inv_head_shoulders", "long", 82, "chart_pattern", "4h",
            price, sl, tp, f"Inverse H&S: neckline break ${neckline:.5f}")
    return None

def _rev_02_head_shoulders(df, price, atr_val):
    """Head & shoulders - bearish reversal from uptrend."""
    if _trend_dir(df, 40) != "up" or len(df) < 30:
        return None
    highs = _swing_highs(df["high"].values, 3)
    if len(highs) < 3:
        return None
    h1, h2, h3 = highs[-3], highs[-2], highs[-1]
    if not (h2[1] > h1[1] and h2[1] > h3[1]):
        return None
    neckline = min(df["low"].iloc[h1[0]:h3[0]+1].min(), df["low"].iloc[h2[0]:h3[0]+1].min())
    if price < neckline:
        sl = h2[1] + atr_val * 0.5
        tp = price - (h2[1] - neckline)
        return ReversalSignal(2, "head_shoulders", "short", 82, "chart_pattern", "4h",
            price, sl, tp, f"H&S: neckline break ${neckline:.5f}")
    return None

def _rev_03_double_top(df, price, atr_val):
    """Double top - bearish reversal."""
    highs = _swing_highs(df["high"].values, 3)
    if len(highs) < 2:
        return None
    h1, h2 = highs[-2], highs[-1]
    if abs(h1[1] - h2[1]) > atr_val * 1.5:
        return None
    neckline = df["low"].iloc[h1[0]:h2[0]+1].min()
    if price < neckline and h2[0] > len(df) - 10:
        sl = max(h1[1], h2[1]) + atr_val * 0.5
        tp = price - (max(h1[1], h2[1]) - neckline)
        return ReversalSignal(3, "double_top", "short", 78, "chart_pattern", "4h",
            price, sl, tp, f"Double top reversal: neckline ${neckline:.5f}")
    return None

def _rev_04_double_bottom(df, price, atr_val):
    """Double bottom - bullish reversal."""
    lows = _swing_lows(df["low"].values, 3)
    if len(lows) < 2:
        return None
    l1, l2 = lows[-2], lows[-1]
    if abs(l1[1] - l2[1]) > atr_val * 1.5:
        return None
    neckline = df["high"].iloc[l1[0]:l2[0]+1].max()
    if price > neckline and l2[0] > len(df) - 10:
        sl = min(l1[1], l2[1]) - atr_val * 0.5
        tp = price + (neckline - min(l1[1], l2[1]))
        return ReversalSignal(4, "double_bottom", "long", 78, "chart_pattern", "4h",
            price, sl, tp, f"Double bottom reversal: neckline ${neckline:.5f}")
    return None

def _rev_05_triple_top(df, price, atr_val):
    """Triple top - strong bearish reversal."""
    highs = _swing_highs(df["high"].values, 2)
    if len(highs) < 3:
        return None
    h1, h2, h3 = highs[-3], highs[-2], highs[-1]
    spread = max(h1[1], h2[1], h3[1]) - min(h1[1], h2[1], h3[1])
    if spread > atr_val * 2:
        return None
    support = df["low"].iloc[h1[0]:h3[0]+1].min()
    if price < support:
        sl = max(h1[1], h2[1], h3[1]) + atr_val * 0.5
        tp = price - (max(h1[1], h2[1], h3[1]) - support)
        return ReversalSignal(5, "triple_top", "short", 84, "chart_pattern", "4h",
            price, sl, tp, "Triple top: 3 failed resistance tests")
    return None

def _rev_06_triple_bottom(df, price, atr_val):
    """Triple bottom - strong bullish reversal."""
    lows = _swing_lows(df["low"].values, 2)
    if len(lows) < 3:
        return None
    l1, l2, l3 = lows[-3], lows[-2], lows[-1]
    spread = max(l1[1], l2[1], l3[1]) - min(l1[1], l2[1], l3[1])
    if spread > atr_val * 2:
        return None
    resistance = df["high"].iloc[l1[0]:l3[0]+1].max()
    if price > resistance:
        sl = min(l1[1], l2[1], l3[1]) - atr_val * 0.5
        tp = price + (resistance - min(l1[1], l2[1], l3[1]))
        return ReversalSignal(6, "triple_bottom", "long", 84, "chart_pattern", "4h",
            price, sl, tp, "Triple bottom: 3 held support tests")
    return None

def _rev_07_broadening_top(df, price, atr_val):
    """Broadening top - expanding swings at top."""
    if _trend_dir(df, 30) != "up" or len(df) < 20:
        return None
    recent = df.iloc[-20:]
    h_range = float(recent["high"].max()) - float(recent["high"].min())
    l_range = float(recent["low"].max()) - float(recent["low"].min())
    if h_range < atr_val * 3 or l_range < atr_val * 3:
        return None
    last_low = float(df["low"].iloc[-5:].min())
    prev_low = float(df["low"].iloc[-15:-5].min())
    if price < prev_low:
        sl = float(recent["high"].max()) + atr_val * 0.5
        tp = price - (float(recent["high"].max()) - prev_low) * 0.5
        return ReversalSignal(7, "broadening_top", "short", 72, "chart_pattern", "4h",
            price, sl, tp, "Broadening top: expanding swings breaking down")
    return None

def _rev_08_broadening_bottom(df, price, atr_val):
    """Broadening bottom - expanding swings at bottom."""
    if _trend_dir(df, 30) != "down" or len(df) < 20:
        return None
    recent = df.iloc[-20:]
    h_range = float(recent["high"].max()) - float(recent["high"].min())
    l_range = float(recent["low"].max()) - float(recent["low"].min())
    if h_range < atr_val * 3 or l_range < atr_val * 3:
        return None
    prev_high = float(df["high"].iloc[-15:-5].max())
    if price > prev_high:
        sl = float(recent["low"].min()) - atr_val * 0.5
        tp = price + (prev_high - float(recent["low"].min())) * 0.5
        return ReversalSignal(8, "broadening_bottom", "long", 72, "chart_pattern", "4h",
            price, sl, tp, "Broadening bottom: expanding swings breaking up")
    return None

def _rev_09_cup_handle(df, price, atr_val):
    """Cup & handle - rounded bottom accumulation."""
    if len(df) < 40:
        return None
    mid_low = float(df["low"].iloc[-30:-10].min())
    recent_high = float(df["high"].iloc[-10:].max())
    left_high = float(df["high"].iloc[-40:-30].max())
    if abs(left_high - recent_high) > atr_val * 3:
        return None
    handle_low = float(df["low"].iloc[-5:].min())
    if handle_low > mid_low and price > recent_high:
        sl = handle_low - atr_val * 0.5
        tp = price + (recent_high - mid_low)
        return ReversalSignal(9, "cup_handle", "long", 76, "chart_pattern", "1D",
            price, sl, tp, "Cup & handle breakout above handle")
    return None

def _rev_10_diamond_top(df, price, atr_val):
    """Diamond top - broadening then narrowing at top."""
    if _trend_dir(df, 30) != "up" or len(df) < 20:
        return None
    first_half = df.iloc[-20:-10]
    second_half = df.iloc[-10:]
    fh_range = float(first_half["high"].max()) - float(first_half["low"].min())
    sh_range = float(second_half["high"].max()) - float(second_half["low"].min())
    if sh_range >= fh_range or fh_range < atr_val * 3:
        return None
    support = float(second_half["low"].min())
    if price < support:
        sl = float(first_half["high"].max()) + atr_val * 0.5
        tp = price - fh_range * 0.5
        return ReversalSignal(10, "diamond_top", "short", 74, "chart_pattern", "4h",
            price, sl, tp, "Diamond top: contracting range breaks down")
    return None


# ---------------------------------------------------------------------------
# TRENDLINE / CHANNEL REVERSALS (11-20)
# ---------------------------------------------------------------------------

def _rev_11_downtrend_break_hl(df, price, atr_val):
    """Break of downtrend + higher low formation."""
    if _trend_dir(df, 30) != "down" or len(df) < 20:
        return None
    lows = _swing_lows(df["low"].values, 2)
    if len(lows) < 3:
        return None
    if lows[-1][1] > lows[-2][1]:
        ema21 = float(_ema(df["close"], 21).iloc[-1])
        if price > ema21:
            sl = lows[-1][1] - atr_val * 0.5
            tp = price + atr_val * 3
            return ReversalSignal(11, "downtrend_break_hl", "long", 76, "trendline", "4h",
                price, sl, tp, "Downtrend broken: higher low + above EMA21")
    return None

def _rev_12_uptrend_break_lh(df, price, atr_val):
    """Break of uptrend + lower high formation."""
    if _trend_dir(df, 30) != "up" or len(df) < 20:
        return None
    highs = _swing_highs(df["high"].values, 2)
    if len(highs) < 3:
        return None
    if highs[-1][1] < highs[-2][1]:
        ema21 = float(_ema(df["close"], 21).iloc[-1])
        if price < ema21:
            sl = highs[-1][1] + atr_val * 0.5
            tp = price - atr_val * 3
            return ReversalSignal(12, "uptrend_break_lh", "short", 76, "trendline", "4h",
                price, sl, tp, "Uptrend broken: lower high + below EMA21")
    return None

def _rev_13_channel_top_overshoot(df, price, atr_val):
    """Channel top overshoot then failure."""
    _, bb_up, _ = _bb(df["close"], 20, 2.0)
    bu = float(bb_up.iloc[-1])
    prev_high = float(df["high"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    if prev_high > bu and curr_close < bu:
        sl = prev_high + atr_val * 0.3
        tp = price - atr_val * 2
        return ReversalSignal(13, "channel_overshoot_top", "short", 70, "trendline", "4h",
            price, sl, tp, f"Overshoot above BB upper ${bu:.5f} then failed")
    return None

def _rev_14_channel_bottom_undershoot(df, price, atr_val):
    """Channel bottom undershoot then rejection."""
    _, _, bb_lo = _bb(df["close"], 20, 2.0)
    bl = float(bb_lo.iloc[-1])
    prev_low = float(df["low"].iloc[-2])
    curr_close = float(df["close"].iloc[-1])
    if prev_low < bl and curr_close > bl:
        sl = prev_low - atr_val * 0.3
        tp = price + atr_val * 2
        return ReversalSignal(14, "channel_undershoot_bottom", "long", 70, "trendline", "4h",
            price, sl, tp, f"Undershoot below BB lower ${bl:.5f} then reclaimed")
    return None

def _rev_15_false_breakout_up(df, price, atr_val):
    """False breakout above resistance then reversal."""
    recent_high = float(df["high"].iloc[-20:-2].max())
    spiked = float(df["high"].iloc[-1]) > recent_high
    closed_below = float(df["close"].iloc[-1]) < recent_high
    if spiked and closed_below:
        sl = float(df["high"].iloc[-1]) + atr_val * 0.3
        tp = price - atr_val * 2.5
        return ReversalSignal(15, "false_breakout_up", "short", 76, "trendline", "4h",
            price, sl, tp, f"False breakout above ${recent_high:.5f} - fading")
    return None

def _rev_16_false_breakout_down(df, price, atr_val):
    """False breakout below support then reversal."""
    recent_low = float(df["low"].iloc[-20:-2].min())
    spiked = float(df["low"].iloc[-1]) < recent_low
    closed_above = float(df["close"].iloc[-1]) > recent_low
    if spiked and closed_above:
        sl = float(df["low"].iloc[-1]) - atr_val * 0.3
        tp = price + atr_val * 2.5
        return ReversalSignal(16, "false_breakout_down", "long", 76, "trendline", "4h",
            price, sl, tp, f"False breakout below ${recent_low:.5f} - fading")
    return None

def _rev_17_channel_2nd_test(df, price, atr_val):
    """Second test of channel boundary - stronger signal."""
    highs = _swing_highs(df["high"].values, 2)
    if len(highs) < 2:
        return None
    h1, h2 = highs[-2], highs[-1]
    if abs(h1[1] - h2[1]) < atr_val * 0.5 and h2[0] > len(df) - 5:
        rsi = _rsi(df["close"])
        if float(rsi.iloc[-1]) > 65:
            sl = max(h1[1], h2[1]) + atr_val * 0.5
            tp = price - atr_val * 2.5
            return ReversalSignal(17, "channel_2nd_test_top", "short", 74, "trendline", "4h",
                price, sl, tp, "2nd test of resistance with RSI overbought")
    return None

def _rev_18_ema_rejection(df, price, atr_val):
    """Price rallies into declining EMA21 and gets rejected."""
    ema21 = _ema(df["close"], 21)
    e_now = float(ema21.iloc[-1])
    e_prev = float(ema21.iloc[-5])
    curr = df.iloc[-1]
    if e_now < e_prev and float(curr["high"]) >= e_now * 0.998 and float(curr["close"]) < e_now:
        sl = e_now + atr_val * 0.5
        tp = price - atr_val * 2.5
        return ReversalSignal(18, "ema_rejection_short", "short", 72, "trendline", "4h",
            price, sl, tp, f"Rejected at declining EMA21 ${e_now:.5f}")
    if e_now > e_prev and float(curr["low"]) <= e_now * 1.002 and float(curr["close"]) > e_now:
        sl = e_now - atr_val * 0.5
        tp = price + atr_val * 2.5
        return ReversalSignal(18, "ema_rejection_long", "long", 72, "trendline", "4h",
            price, sl, tp, f"Bounced off rising EMA21 ${e_now:.5f}")
    return None

def _rev_19_trendline_divergence(df, price, atr_val):
    """Price in trend but RSI shows divergence."""
    rsi = _rsi(df["close"])
    if len(rsi) < 10:
        return None
    highs = _swing_highs(df["high"].values, 2)
    if len(highs) >= 2:
        h1, h2 = highs[-2], highs[-1]
        if h2[1] > h1[1] and float(rsi.iloc[h2[0]]) < float(rsi.iloc[h1[0]]):
            sl = h2[1] + atr_val * 0.5
            tp = price - atr_val * 3
            return ReversalSignal(19, "bearish_divergence", "short", 74, "trendline", "4h",
                price, sl, tp, "Higher price + lower RSI = bearish divergence")
    lows = _swing_lows(df["low"].values, 2)
    if len(lows) >= 2:
        l1, l2 = lows[-2], lows[-1]
        if l2[1] < l1[1] and float(rsi.iloc[l2[0]]) > float(rsi.iloc[l1[0]]):
            sl = l2[1] - atr_val * 0.5
            tp = price + atr_val * 3
            return ReversalSignal(19, "bullish_divergence", "long", 74, "trendline", "4h",
                price, sl, tp, "Lower price + higher RSI = bullish divergence")
    return None

def _rev_20_volume_spike_reversal(df, price, atr_val):
    """Huge volume spike candle against the trend."""
    trend = _trend_dir(df, 20)
    vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
    vol_now = float(df["volume"].iloc[-1])
    if vol_avg <= 0 or vol_now < vol_avg * 2.5:
        return None
    curr = df.iloc[-1]
    bullish = float(curr["close"]) > float(curr["open"])
    if trend == "down" and bullish:
        sl = float(curr["low"]) - atr_val * 0.5
        tp = price + atr_val * 3
        return ReversalSignal(20, "vol_spike_reversal", "long", 78, "trendline", "4h",
            price, sl, tp, f"2.5x volume spike bullish in downtrend")
    if trend == "up" and not bullish:
        sl = float(curr["high"]) + atr_val * 0.5
        tp = price - atr_val * 3
        return ReversalSignal(20, "vol_spike_reversal", "short", 78, "trendline", "4h",
            price, sl, tp, f"2.5x volume spike bearish in uptrend")
    return None


# ---------------------------------------------------------------------------
# INDICATOR-BASED REVERSALS (21-30)
# ---------------------------------------------------------------------------

def _rev_21_rsi_divergence_extreme(df, price, atr_val):
    """RSI extreme divergence - strongest reversal signal."""
    rsi = _rsi(df["close"])
    r_now = float(rsi.iloc[-1])
    if r_now > 75:
        highs = _swing_highs(df["high"].values, 2)
        if len(highs) >= 2 and highs[-1][1] > highs[-2][1]:
            r_h1 = float(rsi.iloc[highs[-2][0]])
            r_h2 = float(rsi.iloc[highs[-1][0]])
            if r_h2 < r_h1:
                sl = highs[-1][1] + atr_val * 0.5
                tp = price - atr_val * 3
                return ReversalSignal(21, "rsi_extreme_div_bear", "short", 80, "indicator", "4h",
                    price, sl, tp, f"RSI {r_now:.0f} extreme + bearish divergence")
    if r_now < 25:
        lows = _swing_lows(df["low"].values, 2)
        if len(lows) >= 2 and lows[-1][1] < lows[-2][1]:
            r_l1 = float(rsi.iloc[lows[-2][0]])
            r_l2 = float(rsi.iloc[lows[-1][0]])
            if r_l2 > r_l1:
                sl = lows[-1][1] - atr_val * 0.5
                tp = price + atr_val * 3
                return ReversalSignal(21, "rsi_extreme_div_bull", "long", 80, "indicator", "4h",
                    price, sl, tp, f"RSI {r_now:.0f} extreme + bullish divergence")
    return None

def _rev_22_rsi_recovery(df, price, atr_val):
    """RSI recovers from deep in downtrend - momentum shift."""
    if _trend_dir(df, 20) != "down":
        return None
    rsi = _rsi(df["close"])
    r_now = float(rsi.iloc[-1])
    r_prev3 = float(rsi.iloc[-4])
    if r_prev3 < 30 and r_now > 45:
        sl = float(df["low"].iloc[-10:].min()) - atr_val * 0.5
        tp = price + atr_val * 2.5
        return ReversalSignal(22, "rsi_recovery", "long", 70, "indicator", "4h",
            price, sl, tp, f"RSI recovered from {r_prev3:.0f} to {r_now:.0f} in downtrend")
    return None

def _rev_23_macd_trendline_break(df, price, atr_val):
    """MACD histogram flips direction after extended run."""
    _, _, hist = _macd(df["close"])
    h = hist.iloc[-5:]
    if all(not pd.isna(x) for x in h):
        vals = [float(x) for x in h]
        if vals[-2] < 0 and vals[-1] > 0 and all(v < 0 for v in vals[:-1]):
            sl = float(df["low"].iloc[-5:].min()) - atr_val * 0.5
            tp = price + atr_val * 2.5
            return ReversalSignal(23, "macd_flip_bull", "long", 72, "indicator", "4h",
                price, sl, tp, "MACD histogram flipped positive after bearish run")
        if vals[-2] > 0 and vals[-1] < 0 and all(v > 0 for v in vals[:-1]):
            sl = float(df["high"].iloc[-5:].max()) + atr_val * 0.5
            tp = price - atr_val * 2.5
            return ReversalSignal(23, "macd_flip_bear", "short", 72, "indicator", "4h",
                price, sl, tp, "MACD histogram flipped negative after bullish run")
    return None

def _rev_24_macd_hist_spike(df, price, atr_val):
    """MACD histogram reversal spike near lows/highs."""
    _, _, hist = _macd(df["close"])
    h_now = float(hist.iloc[-1])
    h_prev = float(hist.iloc[-2])
    h_prev2 = float(hist.iloc[-3])
    if pd.isna(h_now):
        return None
    if h_prev2 < h_prev < 0 and h_now > 0:
        sl = float(df["low"].iloc[-5:].min()) - atr_val * 0.5
        tp = price + atr_val * 2
        return ReversalSignal(24, "macd_spike_bull", "long", 68, "indicator", "4h",
            price, sl, tp, "MACD histogram spike from negative to positive")
    if h_prev2 > h_prev > 0 and h_now < 0:
        sl = float(df["high"].iloc[-5:].max()) + atr_val * 0.5
        tp = price - atr_val * 2
        return ReversalSignal(24, "macd_spike_bear", "short", 68, "indicator", "4h",
            price, sl, tp, "MACD histogram spike from positive to negative")
    return None

def _rev_25_macd_crossover(df, price, atr_val):
    """MACD signal line crossover after prolonged trend."""
    macd_line, sig_line, _ = _macd(df["close"])
    m_now = float(macd_line.iloc[-1])
    s_now = float(sig_line.iloc[-1])
    m_prev = float(macd_line.iloc[-2])
    s_prev = float(sig_line.iloc[-2])
    if pd.isna(m_now) or pd.isna(s_now):
        return None
    if m_prev < s_prev and m_now > s_now and _trend_dir(df, 20) == "down":
        sl = float(df["low"].iloc[-10:].min()) - atr_val * 0.5
        tp = price + atr_val * 2.5
        return ReversalSignal(25, "macd_cross_bull", "long", 72, "indicator", "4h",
            price, sl, tp, "MACD bullish crossover in downtrend")
    if m_prev > s_prev and m_now < s_now and _trend_dir(df, 20) == "up":
        sl = float(df["high"].iloc[-10:].max()) + atr_val * 0.5
        tp = price - atr_val * 2.5
        return ReversalSignal(25, "macd_cross_bear", "short", 72, "indicator", "4h",
            price, sl, tp, "MACD bearish crossover in uptrend")
    return None

def _rev_26_bb_rsi_double(df, price, atr_val):
    """BB lower band + RSI oversold = double reversal signal."""
    _, _, bb_lo = _bb(df["close"])
    rsi = _rsi(df["close"])
    bl = float(bb_lo.iloc[-1])
    r = float(rsi.iloc[-1])
    if price <= bl * 1.002 and r < 30:
        sl = bl - atr_val * 1.0
        bm = float(_sma(df["close"], 20).iloc[-1])
        tp = bm
        return ReversalSignal(26, "bb_rsi_double_long", "long", 76, "indicator", "4h",
            price, sl, tp, f"BB lower + RSI {r:.0f} double confirmation long")
    _, bb_up, _ = _bb(df["close"])
    bu = float(bb_up.iloc[-1])
    if price >= bu * 0.998 and r > 70:
        sl = bu + atr_val * 1.0
        bm = float(_sma(df["close"], 20).iloc[-1])
        tp = bm
        return ReversalSignal(26, "bb_rsi_double_short", "short", 76, "indicator", "4h",
            price, sl, tp, f"BB upper + RSI {r:.0f} double confirmation short")
    return None

def _rev_27_bb_upper_rejection(df, price, atr_val):
    """BB upper band spike then rejection."""
    _, bb_up, _ = _bb(df["close"])
    bu = float(bb_up.iloc[-1])
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    if float(prev["high"]) > bu and float(curr["close"]) < bu:
        rsi = _rsi(df["close"])
        if float(rsi.iloc[-1]) > 60:
            sl = float(prev["high"]) + atr_val * 0.3
            bm = float(_sma(df["close"], 20).iloc[-1])
            tp = bm
            return ReversalSignal(27, "bb_rejection_short", "short", 72, "indicator", "4h",
                price, sl, tp, "BB upper rejection + RSI overbought")
    return None

def _rev_28_vwap_ema_pin(df, price, atr_val):
    """VWAP + EMA50 pin bar reversal."""
    vw = _vwap(df)
    ema50 = _ema(df["close"], 50)
    vw_val = float(vw.iloc[-1])
    e50 = float(ema50.iloc[-1])
    if pd.isna(vw_val) or pd.isna(e50):
        return None
    curr = df.iloc[-1]
    body = abs(float(curr["close"]) - float(curr["open"]))
    rng = float(curr["high"]) - float(curr["low"])
    if rng <= 0:
        return None
    lower_wick = min(float(curr["open"]), float(curr["close"])) - float(curr["low"])
    upper_wick = float(curr["high"]) - max(float(curr["open"]), float(curr["close"]))

    near_both = abs(price - vw_val) < atr_val * 1.0 and abs(price - e50) < atr_val * 1.0
    if near_both and lower_wick > body * 2 and _trend_dir(df, 20) == "down":
        sl = float(curr["low"]) - atr_val * 0.3
        tp = price + atr_val * 2.5
        return ReversalSignal(28, "vwap_ema_pin_long", "long", 74, "indicator", "4h",
            price, sl, tp, "Pin bar at VWAP+EMA50 confluence in downtrend")
    if near_both and upper_wick > body * 2 and _trend_dir(df, 20) == "up":
        sl = float(curr["high"]) + atr_val * 0.3
        tp = price - atr_val * 2.5
        return ReversalSignal(28, "vwap_ema_pin_short", "short", 74, "indicator", "4h",
            price, sl, tp, "Pin bar at VWAP+EMA50 confluence in uptrend")
    return None

def _rev_29_volume_trendline_break(df, price, atr_val):
    """Trendline break with volume confirmation."""
    trend = _trend_dir(df, 20)
    if trend == "flat":
        return None
    vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
    vol_now = float(df["volume"].iloc[-1])
    if vol_avg <= 0 or vol_now < vol_avg * 1.5:
        return None
    ema21 = _ema(df["close"], 21)
    e_now = float(ema21.iloc[-1])
    curr_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2])

    if trend == "down" and prev_close < e_now and curr_close > e_now:
        sl = float(df["low"].iloc[-5:].min()) - atr_val * 0.5
        tp = price + atr_val * 2.5
        return ReversalSignal(29, "vol_trendbreak_long", "long", 76, "indicator", "4h",
            price, sl, tp, f"EMA21 break with {vol_now/vol_avg:.1f}x volume in downtrend")
    if trend == "up" and prev_close > e_now and curr_close < e_now:
        sl = float(df["high"].iloc[-5:].max()) + atr_val * 0.5
        tp = price - atr_val * 2.5
        return ReversalSignal(29, "vol_trendbreak_short", "short", 76, "indicator", "4h",
            price, sl, tp, f"EMA21 break with {vol_now/vol_avg:.1f}x volume in uptrend")
    return None

def _rev_30_mtf_volume_spike(df_1h, df_4h, price, atr_val):
    """Multi-TF volume spike reversal - strongest indicator signal."""
    if df_1h is None or df_4h is None or len(df_1h) < 20 or len(df_4h) < 20:
        return None
    v1h_avg = float(df_1h["volume"].rolling(20).mean().iloc[-1])
    v1h_now = float(df_1h["volume"].iloc[-1])
    v4h_avg = float(df_4h["volume"].rolling(14).mean().iloc[-1])
    v4h_now = float(df_4h["volume"].iloc[-1])
    if v1h_avg <= 0 or v4h_avg <= 0:
        return None
    both_spike = v1h_now > v1h_avg * 2.0 and v4h_now > v4h_avg * 1.5

    if not both_spike:
        return None

    trend = _trend_dir(df_4h, 10)
    curr = df_1h.iloc[-1]
    bullish = float(curr["close"]) > float(curr["open"])

    if trend == "down" and bullish:
        sl = float(df_1h["low"].iloc[-3:].min()) - atr_val * 0.5
        tp = price + atr_val * 3
        return ReversalSignal(30, "mtf_vol_spike_long", "long", 82, "indicator", "1h+4h",
            price, sl, tp, f"Multi-TF vol spike (1h={v1h_now/v1h_avg:.1f}x, 4h={v4h_now/v4h_avg:.1f}x) bullish in downtrend")
    if trend == "up" and not bullish:
        sl = float(df_1h["high"].iloc[-3:].max()) + atr_val * 0.5
        tp = price - atr_val * 3
        return ReversalSignal(30, "mtf_vol_spike_short", "short", 82, "indicator", "1h+4h",
            price, sl, tp, f"Multi-TF vol spike (1h={v1h_now/v1h_avg:.1f}x, 4h={v4h_now/v4h_avg:.1f}x) bearish in uptrend")
    return None


# ---------------------------------------------------------------------------
# MASTER SCANNER
# ---------------------------------------------------------------------------

ALL_REVERSAL_STRATEGIES = [
    _rev_01_inverse_hs, _rev_02_head_shoulders, _rev_03_double_top,
    _rev_04_double_bottom, _rev_05_triple_top, _rev_06_triple_bottom,
    _rev_07_broadening_top, _rev_08_broadening_bottom, _rev_09_cup_handle,
    _rev_10_diamond_top,
    _rev_11_downtrend_break_hl, _rev_12_uptrend_break_lh,
    _rev_13_channel_top_overshoot, _rev_14_channel_bottom_undershoot,
    _rev_15_false_breakout_up, _rev_16_false_breakout_down,
    _rev_17_channel_2nd_test, _rev_18_ema_rejection,
    _rev_19_trendline_divergence, _rev_20_volume_spike_reversal,
    _rev_21_rsi_divergence_extreme, _rev_22_rsi_recovery,
    _rev_23_macd_trendline_break, _rev_24_macd_hist_spike,
    _rev_25_macd_crossover, _rev_26_bb_rsi_double,
    _rev_27_bb_upper_rejection, _rev_28_vwap_ema_pin,
    _rev_29_volume_trendline_break,
]

# Strategy 30 needs df_1h + df_4h, handled separately
_REV_30_MTF = _rev_30_mtf_volume_spike


def scan_reversal_signals(
    df_4h: pd.DataFrame,
    df_1h: pd.DataFrame = None,
    price: float = 0,
    config: dict = None,
) -> list[ReversalSignal]:
    """Scan all 30 reversal strategies on 4h data (primary TF for reversals).

    Returns list of ReversalSignal sorted by confidence.
    """
    if df_4h is None or len(df_4h) < 30:
        return []

    atr_s = _atr(df_4h, 14)
    atr_val = float(atr_s.iloc[-1]) if not pd.isna(atr_s.iloc[-1]) else 0.001
    if atr_val <= 0:
        atr_val = 0.001

    if price <= 0:
        price = float(df_4h["close"].iloc[-1])

    signals = []

    for fn in ALL_REVERSAL_STRATEGIES:
        try:
            sig = fn(df_4h, price, atr_val)
            if sig is not None:
                signals.append(sig)
        except Exception:
            continue

    # Strategy 30: MTF volume spike (needs both 1h and 4h)
    try:
        sig30 = _REV_30_MTF(df_1h, df_4h, price, atr_val)
        if sig30 is not None:
            signals.append(sig30)
    except Exception:
        pass

    signals.sort(key=lambda s: s.confidence, reverse=True)
    return signals


def reversal_score_modifier(signals: list[ReversalSignal], direction: str) -> int:
    """Compute score modifier from reversal signals for a given direction.

    Signals that agree with direction add their confidence/10.
    Signals that disagree subtract half that.
    """
    total = 0
    for sig in signals:
        bonus = sig.confidence // 10
        if sig.direction == direction:
            total += bonus
        else:
            total -= bonus // 2
    return max(-15, min(15, total))
