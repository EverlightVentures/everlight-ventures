from __future__ import annotations

from typing import Dict

import pandas as pd

from indicators.adx import adx
from indicators.atr import atr
from indicators.bollinger import bollinger_bands
from indicators.ema import ema
from indicators.macd import macd
from indicators.obv import obv_divergence
from indicators.pattern_engine import detect_patterns
from indicators.rsi import rsi
from indicators.rsi_gap import rsi_gap_signal
from indicators.vwap import vwap
from strategy.confluence import compute_confluences
from structure.levels import level_breakout


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _rvol(df_15m: pd.DataFrame) -> float:
    if df_15m.empty or len(df_15m) < 25:
        return 0.0
    base = df_15m["volume"].rolling(20).mean().iloc[-1]
    if base <= 0 or pd.isna(base):
        return 0.0
    return float(df_15m["volume"].iloc[-1] / base)


def classify_regime_v4(df_15m: pd.DataFrame, df_1h: pd.DataFrame, df_4h: pd.DataFrame | None = None, df_1d: pd.DataFrame | None = None) -> dict:
    out = {
        "regime": "neutral",
        "adx_15m": None,
        "adx_1h": None,
        "adx_4h": None,
        "adx_1d": None,
        "adx_rising": False,
        "atr_expanding": False,
        "bb_expanding": False,
        "atr_shock": False,
        "extreme_candle": False,
        "htf_trend": "neutral",
    }
    if df_15m.empty or len(df_15m) < 40 or df_1h.empty or len(df_1h) < 40:
        return out

    adx_15m = adx(df_15m, 14)
    adx_1h = adx(df_1h, 14)
    a15 = float(adx_15m.iloc[-1]) if not pd.isna(adx_15m.iloc[-1]) else 0.0
    a15_prev = float(adx_15m.iloc[-5]) if len(adx_15m) > 5 and not pd.isna(adx_15m.iloc[-5]) else a15
    a1h = float(adx_1h.iloc[-1]) if not pd.isna(adx_1h.iloc[-1]) else 0.0
    adx_rising = a15 > a15_prev

    # 4h and daily ADX for macro regime context
    a4h = 0.0
    a1d_val = 0.0
    if df_4h is not None and not df_4h.empty and len(df_4h) >= 30:
        try:
            _adx_4h = adx(df_4h, 14)
            a4h = float(_adx_4h.iloc[-1]) if not pd.isna(_adx_4h.iloc[-1]) else 0.0
        except Exception:
            pass
    if df_1d is not None and not df_1d.empty and len(df_1d) >= 20:
        try:
            _adx_1d = adx(df_1d, 14)
            a1d_val = float(_adx_1d.iloc[-1]) if not pd.isna(_adx_1d.iloc[-1]) else 0.0
        except Exception:
            pass

    atr15 = atr(df_15m, 14)
    atr_recent = float(atr15.iloc[-1]) if not pd.isna(atr15.iloc[-1]) else 0.0
    atr_mean20 = float(atr15.rolling(20).mean().iloc[-1]) if len(atr15) >= 20 and not pd.isna(atr15.rolling(20).mean().iloc[-1]) else atr_recent
    atr_expanding = atr_mean20 > 0 and atr_recent > (1.15 * atr_mean20)
    atr_shock = atr_mean20 > 0 and atr_recent > (2.2 * atr_mean20)

    bb = bollinger_bands(df_15m["close"], 20, 2.0)
    bb_w = bb["width"]
    bb_w_recent = float(bb_w.iloc[-1]) if not pd.isna(bb_w.iloc[-1]) else 0.0
    bb_w_mean20 = float(bb_w.rolling(20).mean().iloc[-1]) if len(bb_w) >= 20 and not pd.isna(bb_w.rolling(20).mean().iloc[-1]) else bb_w_recent
    bb_expanding = bb_w_mean20 > 0 and bb_w_recent > (1.10 * bb_w_mean20)

    c = df_15m.iloc[-1]
    candle_body = abs(float(c["close"]) - float(c["open"]))
    extreme_candle = atr_recent > 0 and (candle_body / atr_recent) > 2.5

    regime = "neutral"
    if a15 >= 25 and adx_rising and atr_expanding and bb_expanding:
        regime = "trend"
    elif a15 < 25 and not bb_expanding:
        regime = "mean_reversion"

    # HTF trend: if 4h or daily ADX is strong, classify macro direction
    htf_trend = "neutral"
    try:
        if a4h >= 25 or a1d_val >= 20:
            _htf_df = df_4h if df_4h is not None and not df_4h.empty and len(df_4h) >= 30 else df_1h
            _e21_htf = ema(_htf_df["close"], 21)
            _slope_htf = float(_e21_htf.diff().tail(3).mean())
            if _slope_htf > 0:
                htf_trend = "bullish"
            elif _slope_htf < 0:
                htf_trend = "bearish"
    except Exception:
        pass

    out.update(
        {
            "regime": regime,
            "adx_15m": a15,
            "adx_1h": a1h,
            "adx_4h": a4h,
            "adx_1d": a1d_val,
            "adx_rising": adx_rising,
            "atr_expanding": atr_expanding,
            "bb_expanding": bb_expanding,
            "atr_shock": atr_shock,
            "extreme_candle": extreme_candle,
            "htf_trend": htf_trend,
        }
    )
    return out


def _ema_alignment_and_slope(df_1h: pd.DataFrame, direction: str) -> bool:
    if df_1h.empty or len(df_1h) < 60:
        return False
    e21 = ema(df_1h["close"], 21)
    e55 = ema(df_1h["close"], 55)
    e21_now = float(e21.iloc[-1])
    e55_now = float(e55.iloc[-1])
    slope = float(e21.diff().tail(4).mean())
    if direction == "long":
        return e21_now > e55_now and slope > 0
    return e21_now < e55_now and slope < 0


def _macd_divergence_like(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or len(df_15m) < 8:
        return False
    m = macd(df_15m["close"])
    hist = m["hist"]
    if hist.isna().tail(6).any():
        return False
    px_delta = float(df_15m["close"].iloc[-1] - df_15m["close"].iloc[-5])
    hist_delta = float(hist.iloc[-1] - hist.iloc[-5])
    if direction == "long":
        return px_delta < 0 and hist_delta > 0
    return px_delta > 0 and hist_delta < 0


def _rsi_divergence(df_15m: pd.DataFrame, direction: str, lookback: int = 14) -> bool:
    """RSI divergence: price lower low + RSI higher low (bullish), or vice versa."""
    if df_15m.empty or len(df_15m) < lookback + 5:
        return False
    rv = rsi(df_15m["close"], 14)
    if rv.isna().tail(lookback).sum() > lookback // 2:
        return False
    window = df_15m.tail(lookback)
    rsi_window = rv.tail(lookback)
    half = lookback // 2
    if direction == "long":
        recent_price_low = float(window["low"].iloc[-3:].min())
        earlier_price_low = float(window["low"].iloc[:half].min())
        recent_rsi_low = float(rsi_window.iloc[-3:].min())
        earlier_rsi_low = float(rsi_window.iloc[:half].min())
        return recent_price_low < earlier_price_low and recent_rsi_low > earlier_rsi_low
    else:
        recent_price_high = float(window["high"].iloc[-3:].max())
        earlier_price_high = float(window["high"].iloc[:half].max())
        recent_rsi_high = float(rsi_window.iloc[-3:].max())
        earlier_rsi_high = float(rsi_window.iloc[:half].max())
        return recent_price_high > earlier_price_high and recent_rsi_high < earlier_rsi_high


def _macd_momentum(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or len(df_15m) < 5:
        return False
    h = macd(df_15m["close"])["hist"]
    if h.isna().tail(4).any():
        return False
    if direction == "long":
        return h.iloc[-1] > h.iloc[-2] > h.iloc[-3]
    return h.iloc[-1] < h.iloc[-2] < h.iloc[-3]


def _rsi_extreme(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty:
        return False
    rv = rsi(df_15m["close"], 14)
    if rv.isna().iloc[-1]:
        return False
    last = float(rv.iloc[-1])
    if direction == "long":
        return last <= 35
    return last >= 65


def _bollinger_rejection(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or len(df_15m) < 25:
        return False
    bb = bollinger_bands(df_15m["close"], 20, 2.0)
    row = df_15m.iloc[-1]
    upper = float(bb["upper"].iloc[-1]) if not pd.isna(bb["upper"].iloc[-1]) else 0.0
    lower = float(bb["lower"].iloc[-1]) if not pd.isna(bb["lower"].iloc[-1]) else 0.0
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    if direction == "long":
        return lower > 0 and low <= lower and close > lower
    return upper > 0 and high >= upper and close < upper


def _bandwalk(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or len(df_15m) < 25:
        return False
    bb = bollinger_bands(df_15m["close"], 20, 2.0)
    close = float(df_15m["close"].iloc[-1])
    upper = float(bb["upper"].iloc[-1]) if not pd.isna(bb["upper"].iloc[-1]) else 0.0
    lower = float(bb["lower"].iloc[-1]) if not pd.isna(bb["lower"].iloc[-1]) else 0.0
    if direction == "long":
        return upper > 0 and close >= (0.995 * upper)
    return lower > 0 and close <= (1.005 * lower)


def confluence_score_v4(
    *,
    regime: str,
    direction: str,
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    breakout_type: str,
    entry_type: str | None,
    lane: str | None = None,
    lane_weights: dict | None = None,
) -> dict:
    conf = compute_confluences(price, df_1h, df_4h, df_15m, levels, fibs, direction)
    rv = _rvol(df_15m)
    adx_series = adx(df_15m, 14)
    adx_now = float(adx_series.iloc[-1]) if len(adx_series) and not pd.isna(adx_series.iloc[-1]) else 0.0
    atr15 = atr(df_15m, 14)
    atr_recent = float(atr15.iloc[-1]) if len(atr15) and not pd.isna(atr15.iloc[-1]) else 0.0
    atr_mean20 = float(atr15.rolling(20).mean().iloc[-1]) if len(atr15) >= 20 and not pd.isna(atr15.rolling(20).mean().iloc[-1]) else atr_recent
    atr_expanding = atr_mean20 > 0 and atr_recent > (1.15 * atr_mean20)
    bb = bollinger_bands(df_15m["close"], 20, 2.0)
    bbw = bb["width"]
    bbw_recent = float(bbw.iloc[-1]) if len(bbw) and not pd.isna(bbw.iloc[-1]) else 0.0
    bbw_mean20 = float(bbw.rolling(20).mean().iloc[-1]) if len(bbw) >= 20 and not pd.isna(bbw.rolling(20).mean().iloc[-1]) else bbw_recent
    bb_expanding = bbw_mean20 > 0 and bbw_recent > (1.10 * bbw_mean20)

    trend_break = level_breakout(price, levels, direction)
    ema_align = _ema_alignment_and_slope(df_1h, direction)
    macd_momo = _macd_momentum(df_15m, direction)
    macd_div_like = _macd_divergence_like(df_15m, direction)
    rsi_extreme = _rsi_extreme(df_15m, direction)
    bb_reject = _bollinger_rejection(df_15m, direction)
    bb_walk = _bandwalk(df_15m, direction)
    vol_spike = rv >= 1.2
    rsi_div = _rsi_divergence(df_15m, direction)
    obv_div = obv_divergence(df_15m, direction)
    rsi_gap_sig = rsi_gap_signal(df_15m, direction)

    # Chart pattern detection (flag, cup & handle, double bottom/top, + v4 patterns)
    pattern_result = detect_patterns(df_15m, direction)
    flag_detected = pattern_result["flag"]["detected"]
    cup_handle_detected = pattern_result["cup_handle"]["detected"]
    double_pattern_detected = pattern_result["double_pattern"]["detected"]

    # New v4 pattern detectors -- each returns {detected, direction, confidence}
    # Only score when pattern direction confirms the proposed trade direction,
    # or when the pattern is directionally neutral (symmetrical triangle, rectangle).
    def _pattern_confirms(pat: dict, dir_: str) -> bool:
        if not pat.get("detected"):
            return False
        pd_ = pat.get("direction", "neutral")
        if pd_ == "neutral":
            return True  # neutral patterns give small bonus either way
        return (dir_ == "long" and pd_ == "bullish") or (dir_ == "short" and pd_ == "bearish")

    _hs = pattern_result.get("head_shoulders", {})
    _triple = pattern_result.get("triple_pattern", {})
    _wedge = pattern_result.get("wedge", {})
    _triangle = pattern_result.get("triangle", {})
    _rectangle = pattern_result.get("rectangle", {})
    _rounded = pattern_result.get("rounded_reversal", {})

    head_shoulders_detected = _pattern_confirms(_hs, direction)
    triple_pattern_detected = _pattern_confirms(_triple, direction)
    wedge_detected = _pattern_confirms(_wedge, direction)
    triangle_detected = _pattern_confirms(_triangle, direction)
    rectangle_detected = _pattern_confirms(_rectangle, direction)
    rounded_reversal_detected = _pattern_confirms(_rounded, direction)

    # VWAP confluence: price above VWAP for longs, below for shorts
    vwap_confirm = False
    vwap_val = 0.0
    vwap_side = ""
    try:
        if "time" in df_1h.columns and len(df_1h) >= 5:
            vwap_series = vwap(df_1h)
            vwap_val = float(vwap_series.iloc[-1]) if not vwap_series.empty and not pd.isna(vwap_series.iloc[-1]) else 0.0
            if vwap_val > 0:
                vwap_side = "above" if price >= vwap_val else "below"
                if direction == "long":
                    vwap_confirm = price >= vwap_val
                else:
                    vwap_confirm = price <= vwap_val
    except Exception:
        vwap_confirm = False

    # FVG confluence (imported lazily to avoid circular imports)
    fvg_support = False
    fvg_detail = None  # {type, high, low, age}
    try:
        from strategy.fvg import detect_fvg, nearest_fvg
        fvgs = detect_fvg(df_1h)
        nfvg = nearest_fvg(price, fvgs, direction)
        fvg_support = nfvg is not None
        if nfvg:
            fvg_detail = {
                "type": nfvg.get("type", ""),
                "high": round(float(nfvg.get("high", 0)), 6),
                "low": round(float(nfvg.get("low", 0)), 6),
                "age": int(nfvg.get("age", 0)),
            }
    except Exception:
        fvg_support = False

    # Channel confluence (imported lazily)
    channel_support = False
    channel_breakout = False
    channel_detail = None  # {type, position, upper, lower, width_atr}
    try:
        from strategy.channels import detect_channel, channel_confluence
        chan = detect_channel(df_1h)
        if chan:
            chan_conf = channel_confluence(chan, direction, price)
            channel_support = bool(chan_conf.get("CHANNEL_SUPPORT") or chan_conf.get("CHANNEL_RESISTANCE"))
            channel_breakout = bool(chan_conf.get("CHANNEL_BREAKOUT"))
            channel_detail = {
                "type": chan.get("type", ""),
                "position": chan.get("position", ""),
                "upper": round(float(chan.get("upper_at_now", 0)), 6),
                "lower": round(float(chan.get("lower_at_now", 0)), 6),
                "width_atr": round(float(chan.get("width_atr", 0)), 2),
            }
    except Exception:
        channel_support = False
        channel_breakout = False

    mr_flags = {
        "HTF_LEVEL": bool(conf.get("STRUCTURE_ZONE")),
        "FIB_ZONE": bool(conf.get("FIB_ZONE")),
        "RSI_EXTREME": rsi_extreme,
        "MACD_DIVERGENCE": macd_div_like,
        "RSI_DIVERGENCE": rsi_div,
        "OBV_DIVERGENCE": obv_div,
        "RSI_GAP_CLOSING": rsi_gap_sig,
        "BB_REJECTION": bb_reject,
        "VOLUME_SPIKE": vol_spike,
        "ADX_LOW": adx_now < 25,
        "ATR_NOT_EXPANDING": not atr_expanding,
        "VWAP_CONFIRM": vwap_confirm,
        "FVG_SUPPORT": fvg_support,
        "CHANNEL_SUPPORT": channel_support,
        "CUP_HANDLE": cup_handle_detected,
        "DOUBLE_PATTERN": double_pattern_detected,
        "HEAD_SHOULDERS": head_shoulders_detected,
        "TRIPLE_PATTERN": triple_pattern_detected,
        "WEDGE": wedge_detected,
        "RECTANGLE": rectangle_detected,
        "ROUNDED_REVERSAL": rounded_reversal_detected,
    }
    trend_flags = {
        "HTF_BREAK": trend_break,
        "EMA_ALIGN_SLOPE": ema_align,
        "ADX_TREND": adx_now >= 25,
        "ATR_EXPANDING": atr_expanding,
        "VOLUME_SPIKE": vol_spike,
        "BB_EXPAND_OR_WALK": bb_expanding or bb_walk,
        "MACD_MOMENTUM": macd_momo,
        "RSI_DIVERGENCE": rsi_div,
        "OBV_DIVERGENCE": obv_div,
        "VWAP_CONFIRM": vwap_confirm,
        "CHANNEL_BREAKOUT": channel_breakout,
        "FLAG_CONTINUATION": flag_detected,
        "TRIANGLE_BREAKOUT": triangle_detected,
    }

    mr_weights = {
        "HTF_LEVEL": 25,
        "FIB_ZONE": 20,
        "RSI_EXTREME": 12,
        "MACD_DIVERGENCE": 12,
        "RSI_DIVERGENCE": 10,
        "OBV_DIVERGENCE": 8,
        "RSI_GAP_CLOSING": 12,
        "BB_REJECTION": 10,
        "VOLUME_SPIKE": 10,
        "ADX_LOW": 10,
        "ATR_NOT_EXPANDING": 5,
        "VWAP_CONFIRM": 10,
        "FVG_SUPPORT": 10,
        "CHANNEL_SUPPORT": 10,
        "CUP_HANDLE": 12,
        "DOUBLE_PATTERN": 15,
        "HEAD_SHOULDERS": 18,
        "TRIPLE_PATTERN": 15,
        "WEDGE": 12,
        "RECTANGLE": 10,
        "ROUNDED_REVERSAL": 8,
    }
    trend_weights = {
        "HTF_BREAK": 20,
        "EMA_ALIGN_SLOPE": 20,
        "ADX_TREND": 15,
        "ATR_EXPANDING": 15,
        "VOLUME_SPIKE": 15,
        "BB_EXPAND_OR_WALK": 10,
        "MACD_MOMENTUM": 5,
        "RSI_DIVERGENCE": 5,
        "OBV_DIVERGENCE": 5,
        "VWAP_CONFIRM": 5,
        "CHANNEL_BREAKOUT": 15,
        "FLAG_CONTINUATION": 12,
        "TRIANGLE_BREAKOUT": 12,
    }

    mr_score = int(sum(w for k, w in mr_weights.items() if mr_flags.get(k)))
    trend_score = int(sum(w for k, w in trend_weights.items() if trend_flags.get(k)))
    active_regime = regime if regime in ("mean_reversion", "trend") else ("trend" if breakout_type in ("trend", "exponential") else "mean_reversion")
    active_score = trend_score if active_regime == "trend" else mr_score
    threshold = 75 if active_regime == "trend" else 70
    pass_score = active_score >= threshold

    # --- Per-lane weight override ---
    # If a lane is specified with custom weights, merge all flags and score
    # using lane-specific weights. Flags not in the lane dict get weight 0.
    lane_weights_used = None
    if lane and lane_weights:
        lw = lane_weights.get(lane) or lane_weights.get(lane.upper())
        if lw and isinstance(lw, dict) and lw:
            all_flags = {**mr_flags, **trend_flags}
            active_score = int(sum(
                int(lw.get(k, 0))
                for k, v in all_flags.items() if v
            ))
            lane_weights_used = lane

    # Entry-type hygiene: discourage breakout entries in MR and weak pullbacks in trend.
    if not lane_weights_used:
        if active_regime == "mean_reversion" and entry_type == "breakout_retest":
            pass_score = False
        if active_regime == "trend" and entry_type == "pullback" and not ema_align:
            pass_score = False

    # Reversal impulse: bypasses EMA slope requirement, uses its own scoring.
    # Reversals trade against the trend so EMA alignment doesn't apply.
    if entry_type == "reversal_impulse" and not lane_weights_used:
        ri_flags = {
            "HTF_LEVEL": bool(conf.get("STRUCTURE_ZONE")),
            "FIB_ZONE": bool(conf.get("FIB_ZONE")),
            "RSI_EXTREME": rsi_extreme,
            "BB_REJECTION": bb_reject,
            "VOLUME_SPIKE": vol_spike,
            "MACD_DIVERGENCE": macd_div_like,
            "RSI_DIVERGENCE": rsi_div,
            "OBV_DIVERGENCE": obv_div,
            "RSI_GAP_CLOSING": rsi_gap_sig,
            "ATR_EXPANDING": atr_expanding,
            "CUP_HANDLE": cup_handle_detected,
            "DOUBLE_PATTERN": double_pattern_detected,
            "HEAD_SHOULDERS": head_shoulders_detected,
            "TRIPLE_PATTERN": triple_pattern_detected,
            "WEDGE": wedge_detected,
            "ROUNDED_REVERSAL": rounded_reversal_detected,
        }
        ri_weights = {
            "HTF_LEVEL": 20,
            "FIB_ZONE": 15,
            "RSI_EXTREME": 15,
            "BB_REJECTION": 15,
            "VOLUME_SPIKE": 15,
            "MACD_DIVERGENCE": 10,
            "RSI_DIVERGENCE": 10,
            "OBV_DIVERGENCE": 8,
            "RSI_GAP_CLOSING": 12,
            "ATR_EXPANDING": 10,
            "CUP_HANDLE": 10,
            "DOUBLE_PATTERN": 12,
            "HEAD_SHOULDERS": 18,
            "TRIPLE_PATTERN": 15,
            "WEDGE": 12,
            "ROUNDED_REVERSAL": 8,
        }
        ri_score = int(sum(w for k, w in ri_weights.items() if ri_flags.get(k)))
        ri_threshold = 60  # Lower than trend (75) since reversal signals are inherently strong
        active_score = ri_score
        threshold = ri_threshold
        pass_score = ri_score >= ri_threshold
        # Override the trend hygiene blocks for reversals
        mr_flags.update(ri_flags)
        trend_flags.update(ri_flags)

    # Recompute pass_score if lane weights were used (threshold set by caller)
    if lane_weights_used:
        pass_score = active_score >= threshold

    return {
        "regime": active_regime,
        "score": active_score,
        "threshold": threshold,
        "pass": pass_score,
        "mr_score": mr_score,
        "trend_score": trend_score,
        "mr_flags": mr_flags,
        "trend_flags": trend_flags,
        "adx_15m": adx_now,
        "atr_15m": atr_recent,
        "rvol": rv,
        "lane_weights_used": lane_weights_used,
        "vwap_price": vwap_val,
        "vwap_side": vwap_side,
        "fvg_detail": fvg_detail,
        "channel_detail": channel_detail,
        "rsi_divergence": rsi_div,
        "obv_divergence": obv_div,
        "rsi_gap_closing": rsi_gap_sig,
        "flag_detected": flag_detected,
        "cup_handle_detected": cup_handle_detected,
        "double_pattern_detected": double_pattern_detected,
        "head_shoulders_detected": head_shoulders_detected,
        "triple_pattern_detected": triple_pattern_detected,
        "wedge_detected": wedge_detected,
        "triangle_detected": triangle_detected,
        "rectangle_detected": rectangle_detected,
        "rounded_reversal_detected": rounded_reversal_detected,
        "pattern_detail": pattern_result,
    }


def expected_value_v4(
    *,
    score: float,
    regime: str,
    atr_value: float,
    price: float,
    contract_size: float,
    size: int,
    maker_fee_rate: float = 0.00085,
    taker_fee_rate: float = 0.00090,
    slippage_pct: float = 0.0002,
    funding_pct: float = 0.0,
    min_ev_usd: float = 0.0,
    profit_factor: float = 0.0,
    tp1_price: float = 0.0,
    stop_price: float = 0.0,
    direction: str = "",
) -> dict:
    # Base win probability from score (expanded range vs old 0.40-0.65)
    p_win_base = _clamp(0.30 + 0.004 * float(score), 0.35, 0.70)

    # Adjust win probability by live profit factor (evidence from real trades).
    # PF >= 2.0 → +6%; PF >= 1.5 → +4%; PF >= 1.2 → +2%
    # PF <  0.8 → -4%; PF <  1.0 → -2%
    # Capped at ±6% to prevent over-fitting to small samples.
    pf = float(profit_factor)
    if 0.0 < pf < 999.0:
        if pf >= 2.0:
            pf_adj = 0.06
        elif pf >= 1.5:
            pf_adj = 0.04
        elif pf >= 1.2:
            pf_adj = 0.02
        elif pf < 0.8:
            pf_adj = -0.04
        elif pf < 1.0:
            pf_adj = -0.02
        else:
            pf_adj = 0.0
        p_win = _clamp(p_win_base + pf_adj, 0.30, 0.75)
    else:
        p_win = p_win_base
    if regime == "trend":
        ewin_mult = 1.8
        eloss_mult = 1.0
    else:
        ewin_mult = 1.15
        eloss_mult = 1.5

    notional = float(price) * float(contract_size) * int(size)

    # Use actual TP1/SL distances when available (real pips, not ATR estimates)
    _cs = float(contract_size) * int(size)
    _tp1 = float(tp1_price or 0)
    _sl = float(stop_price or 0)
    _p = float(price)
    _dir = str(direction).lower()
    if _tp1 > 0 and _p > 0:
        if _dir == "long":
            ewin_usd = max(0.0, (_tp1 - _p) * _cs)
        elif _dir == "short":
            ewin_usd = max(0.0, (_p - _tp1) * _cs)
        else:
            ewin_usd = float(atr_value) * ewin_mult * _cs
    else:
        ewin_usd = float(atr_value) * ewin_mult * _cs

    if _sl > 0 and _p > 0:
        if _dir == "long":
            eloss_usd = max(0.0, (_p - _sl) * _cs)
        elif _dir == "short":
            eloss_usd = max(0.0, (_sl - _p) * _cs)
        else:
            eloss_usd = float(atr_value) * eloss_mult * _cs
    else:
        eloss_usd = float(atr_value) * eloss_mult * _cs

    # Entry/exit are generally maker for planned flow; keep taker component for safety premium.
    fees = notional * ((maker_fee_rate * 2.0) + (0.2 * taker_fee_rate))
    slip = notional * slippage_pct
    funding = notional * funding_pct
    total_costs = fees + slip + funding
    ev = (p_win * ewin_usd) - ((1.0 - p_win) * eloss_usd) - total_costs
    # Simple pip profit check: will TP1 cover fees even without probability?
    net_tp1_profit = ewin_usd - total_costs
    covers_fees = net_tp1_profit > 0
    return {
        "p_win": p_win,
        "p_win_base": p_win_base,
        "profit_factor_used": pf if 0.0 < pf < 999.0 else None,
        "ewin_usd": ewin_usd,
        "eloss_usd": eloss_usd,
        "fees_usd": fees,
        "slippage_usd": slip,
        "funding_usd": funding,
        "total_costs_usd": total_costs,
        "ev_usd": ev,
        "net_tp1_profit_usd": net_tp1_profit,
        "covers_fees": covers_fees,
        "pass": ev > float(min_ev_usd) and covers_fees,
        "notional_usd": notional,
    }
