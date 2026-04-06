"""Candle Math -- calculates dollar profit per candle and retracement targets.

Every cycle this module tells the bot:
1. How much money is in the average candle (per timeframe)
2. Where the 50/61.8% retracement targets are after a big move
3. Whether the current market conditions favor aggressive or conservative entries

The bot uses this to adjust its confidence: if a typical 1H candle moves $7.50
and TP is $3.30, the setup is very achievable. If the avg candle is $1.50,
the bot needs to be pickier because the market isn't moving enough.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

_CS = 5000.0  # contract size


@dataclass
class CandleMathResult:
    # Per-timeframe average candle range in USD (per contract)
    avg_range_15m_usd: float = 0.0
    avg_range_1h_usd: float = 0.0
    avg_range_4h_usd: float = 0.0

    # Current candle stats
    current_range_usd: float = 0.0
    current_body_usd: float = 0.0

    # How many TP1s ($3.30) fit in an average candle?
    tp_coverage_15m: float = 0.0  # < 1 = hard to hit TP, > 1 = easy
    tp_coverage_1h: float = 0.0
    tp_coverage_4h: float = 0.0

    # Retracement targets after the most recent big candle
    retrace_50_price: float = 0.0
    retrace_618_price: float = 0.0
    retrace_direction: str = ""  # "long" if retracing a drop, "short" if retracing a pump
    retrace_pnl_50_usd: float = 0.0
    retrace_pnl_618_usd: float = 0.0
    big_candle_detected: bool = False

    # Score modifier: how aggressive should the bot be?
    # Positive = market is moving enough, be aggressive
    # Negative = market is dead, be selective
    aggression_modifier: int = 0
    aggression_reason: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def compute_candle_math(
    *,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame | None = None,
    price: float,
    tp_target_usd: float = 3.30,
    big_candle_atr_mult: float = 1.5,
) -> CandleMathResult:
    """Compute candle profitability and retracement targets."""
    result = CandleMathResult()

    # 1. Average candle range per timeframe
    for df, tf_name in [(df_15m, "15m"), (df_1h, "1h"), (df_4h, "4h")]:
        if df is None or df.empty or len(df) < 10:
            continue
        ranges = (df["high"] - df["low"]).tail(20)
        avg_range = float(ranges.mean())
        avg_usd = avg_range * _CS

        if tf_name == "15m":
            result.avg_range_15m_usd = round(avg_usd, 2)
            result.tp_coverage_15m = round(avg_usd / max(tp_target_usd, 0.01), 2)
        elif tf_name == "1h":
            result.avg_range_1h_usd = round(avg_usd, 2)
            result.tp_coverage_1h = round(avg_usd / max(tp_target_usd, 0.01), 2)
        elif tf_name == "4h":
            result.avg_range_4h_usd = round(avg_usd, 2)
            result.tp_coverage_4h = round(avg_usd / max(tp_target_usd, 0.01), 2)

    # Current candle stats
    if df_15m is not None and not df_15m.empty:
        last = df_15m.iloc[-1]
        result.current_range_usd = round((float(last["high"]) - float(last["low"])) * _CS, 2)
        result.current_body_usd = round(abs(float(last["close"]) - float(last["open"])) * _CS, 2)

    # 2. Retracement targets after big candle
    if df_1h is not None and not df_1h.empty and len(df_1h) >= 5:
        # Find the most recent "big" candle (range > 1.5x average)
        ranges_1h = df_1h["high"] - df_1h["low"]
        avg_1h_range = float(ranges_1h.tail(20).mean())

        for i in range(-1, max(-6, -len(df_1h)), -1):
            candle = df_1h.iloc[i]
            c_range = float(candle["high"]) - float(candle["low"])
            if c_range > avg_1h_range * big_candle_atr_mult:
                c_open = float(candle["open"])
                c_close = float(candle["close"])
                c_high = float(candle["high"])
                c_low = float(candle["low"])
                is_bearish = c_close < c_open

                if is_bearish:
                    # Big red candle -- expect a bounce (long retrace)
                    move = c_high - c_low
                    result.retrace_50_price = round(c_low + move * 0.50, 6)
                    result.retrace_618_price = round(c_low + move * 0.618, 6)
                    result.retrace_direction = "long"
                    result.retrace_pnl_50_usd = round((result.retrace_50_price - price) * _CS, 2) if price < result.retrace_50_price else 0
                    result.retrace_pnl_618_usd = round((result.retrace_618_price - price) * _CS, 2) if price < result.retrace_618_price else 0
                else:
                    # Big green candle -- expect a pullback (short retrace)
                    move = c_high - c_low
                    result.retrace_50_price = round(c_high - move * 0.50, 6)
                    result.retrace_618_price = round(c_high - move * 0.618, 6)
                    result.retrace_direction = "short"
                    result.retrace_pnl_50_usd = round((price - result.retrace_50_price) * _CS, 2) if price > result.retrace_50_price else 0
                    result.retrace_pnl_618_usd = round((price - result.retrace_618_price) * _CS, 2) if price > result.retrace_618_price else 0

                result.big_candle_detected = True
                break

    # 3. Aggression modifier for unified scorer
    # If the average 1H candle covers 2x the TP target, be aggressive (+8)
    # If it barely covers 1x, be neutral (0)
    # If it doesn't cover the TP at all, be conservative (-5)
    coverage = result.tp_coverage_1h
    if coverage >= 2.0:
        result.aggression_modifier = 8
        result.aggression_reason = "1H candles avg $%.1f -- TP is easy, be aggressive" % result.avg_range_1h_usd
    elif coverage >= 1.2:
        result.aggression_modifier = 5
        result.aggression_reason = "1H candles avg $%.1f -- TP achievable in one candle" % result.avg_range_1h_usd
    elif coverage >= 0.8:
        result.aggression_modifier = 2
        result.aggression_reason = "1H candles avg $%.1f -- TP tight but doable" % result.avg_range_1h_usd
    elif coverage >= 0.5:
        result.aggression_modifier = -3
        result.aggression_reason = "1H candles avg $%.1f -- market slow, be selective" % result.avg_range_1h_usd
    else:
        result.aggression_modifier = -5
        result.aggression_reason = "1H candles avg $%.1f -- dead market, only A+ setups" % result.avg_range_1h_usd

    # Bonus if big candle retrace is in play
    if result.big_candle_detected and result.retrace_pnl_50_usd > tp_target_usd:
        result.aggression_modifier += 3
        result.aggression_reason += " + big candle retrace in play ($%.1f to 50%%)" % result.retrace_pnl_50_usd

    return result
