"""Regime-based trading parameter overrides.

Classifies the current market into compression/expansion/transition
using indicators already computed by expansion.py and v4_engine.py,
then returns parameter overrides for position sizing, stops, TPs,
and time-based exits.

Pure function — no state, no side effects, no API calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegimeOverrides:
    """Parameter overrides for the current volatility regime."""
    regime_name: str                # "compression" | "expansion" | "transition"
    size_multiplier: float          # multiply position size (0.7 compression, 1.0 otherwise)
    max_sl_pct: float               # override config risk.max_sl_pct
    tp_atr_mult: float              # ATR multiplier for dynamic TP
    time_stop_bars: int             # override config exits.time_stop_bars
    early_save_bars: int            # override config exits.early_save_bars
    reasons: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def classify_trading_regime(
    vol_phase: str,
    vol_confidence: int,
    adx_15m: float,
    rsi_15m: float,
    atr_ratio: float,
    config: dict,
) -> RegimeOverrides:
    """Classify market regime and return parameter overrides.

    Args:
        vol_phase: from expansion_state["phase"] — COMPRESSION|IGNITION|EXPANSION|EXHAUSTION
        vol_confidence: from expansion_state["confidence"] — 0-100
        adx_15m: from regime_v4["adx_15m"]
        rsi_15m: from expansion_state["metrics"]["rsi"]
        atr_ratio: from expansion_state["metrics"]["tr_ratio"] (ATR recent / ATR avg)
        config: config["regime_manager"] section
    """
    metrics = {
        "vol_phase": vol_phase,
        "vol_confidence": vol_confidence,
        "adx_15m": round(adx_15m, 2),
        "rsi_15m": round(rsi_15m, 2),
        "atr_ratio": round(atr_ratio, 3),
    }

    comp_cfg = config.get("compression") or {}
    exp_cfg = config.get("expansion") or {}

    # --- Compression Mode: chop/range ---
    comp_adx = float(comp_cfg.get("adx_threshold", 25))
    comp_rsi_lo = float(comp_cfg.get("rsi_low", 40))
    comp_rsi_hi = float(comp_cfg.get("rsi_high", 60))

    is_compression_phase = vol_phase.upper() in ("COMPRESSION", "EXHAUSTION")
    is_low_adx = adx_15m < comp_adx
    is_mid_rsi = comp_rsi_lo <= rsi_15m <= comp_rsi_hi

    if is_compression_phase and is_low_adx and is_mid_rsi:
        reasons = []
        if is_compression_phase:
            reasons.append(f"vol_phase={vol_phase}")
        if is_low_adx:
            reasons.append(f"ADX={adx_15m:.1f}<{comp_adx}")
        if is_mid_rsi:
            reasons.append(f"RSI={rsi_15m:.1f} in [{comp_rsi_lo:.0f}-{comp_rsi_hi:.0f}]")
        return RegimeOverrides(
            regime_name="compression",
            size_multiplier=float(comp_cfg.get("size_multiplier", 0.7)),
            max_sl_pct=float(comp_cfg.get("max_sl_pct", 0.015)),
            tp_atr_mult=float(comp_cfg.get("tp_atr_mult", 1.0)),
            time_stop_bars=int(comp_cfg.get("time_stop_bars", 3)),
            early_save_bars=int(comp_cfg.get("early_save_bars", 3)),
            reasons=reasons,
            metrics=metrics,
        )

    # --- Expansion Mode: trending/breakout ---
    exp_adx = float(exp_cfg.get("adx_threshold", 25))
    exp_atr_ratio = float(exp_cfg.get("atr_ratio_threshold", 1.15))

    is_expansion_phase = vol_phase.upper() in ("IGNITION", "EXPANSION")
    is_high_adx = adx_15m >= exp_adx
    is_high_atr = atr_ratio > exp_atr_ratio

    if is_expansion_phase and (is_high_adx or is_high_atr):
        reasons = []
        if is_expansion_phase:
            reasons.append(f"vol_phase={vol_phase}")
        if is_high_adx:
            reasons.append(f"ADX={adx_15m:.1f}>={exp_adx}")
        if is_high_atr:
            reasons.append(f"ATR_ratio={atr_ratio:.2f}>{exp_atr_ratio}")
        return RegimeOverrides(
            regime_name="expansion",
            size_multiplier=float(exp_cfg.get("size_multiplier", 1.0)),
            max_sl_pct=float(exp_cfg.get("max_sl_pct", 0.03)),
            tp_atr_mult=float(exp_cfg.get("tp_atr_mult", 1.4)),
            time_stop_bars=int(exp_cfg.get("time_stop_bars", 8)),
            early_save_bars=int(exp_cfg.get("early_save_bars", 6)),
            reasons=reasons,
            metrics=metrics,
        )

    # --- Transition Mode: defaults ---
    # Fall through to base config values via defaults
    _default_sl = float(config.get("default_max_sl_pct", 0.03))
    _default_tp = float(config.get("default_tp_atr_mult", 1.0))
    _default_ts = int(config.get("default_time_stop_bars", 6))
    _default_es = int(config.get("default_early_save_bars", 6))
    trans_cfg = config.get("transition") or {}

    return RegimeOverrides(
        regime_name="transition",
        size_multiplier=float(trans_cfg.get("size_multiplier", 1.0)),
        max_sl_pct=_default_sl,
        tp_atr_mult=_default_tp,
        time_stop_bars=_default_ts,
        early_save_bars=_default_es,
        reasons=[f"vol_phase={vol_phase}", f"ADX={adx_15m:.1f}", "no regime match"],
        metrics=metrics,
    )


def classify_htf_trend_bias(df_1h: "pd.DataFrame") -> dict:
    """Detect higher-timeframe trend direction from 1h candles.

    Classification logic:
      bearish_crash    : RSI_1h < 30, price below EMA21, EMA21 below EMA55, slope negative
      bearish_trend    : RSI_1h < 45, price below EMA21, slope negative
      neutral          : neither strongly bullish nor bearish
      bullish_trend    : RSI_1h > 55, price above EMA21, slope positive
      bullish_expansion: RSI_1h > 70, price above EMA21, EMA21 above EMA55, slope positive

    Returns dict with:
      bias                    : str (one of the 5 states above)
      rsi_1h                  : float
      ema21_slope_pct         : float (slope as fraction of price over last 5 bars)
      price_vs_ema21          : "above" | "below"
      ema21_vs_ema55          : "above" | "below"
      size_mult_long          : float (< 1.0 in bearish, > 1.0 in bullish)
      size_mult_short         : float (> 1.0 in bearish, < 1.0 in bullish)
      long_require_capitulation  : bool (True in bearish_crash)
      short_require_capitulation : bool (True in bullish_expansion)
      reasons                 : list[str]
    """
    import pandas as pd
    from indicators.rsi import rsi as _rsi
    from indicators.ema import ema as _ema

    _default: dict = {
        "bias": "neutral",
        "rsi_1h": 50.0,
        "ema21_slope_pct": 0.0,
        "price_vs_ema21": "above",
        "ema21_vs_ema55": "above",
        "size_mult_long": 1.0,
        "size_mult_short": 1.0,
        "long_require_capitulation": False,
        "short_require_capitulation": False,
        "reasons": ["insufficient_data"],
    }
    try:
        if df_1h is None or df_1h.empty or len(df_1h) < 60:
            return _default

        rv = _rsi(df_1h["close"], 14)
        rsi_val = float(rv.iloc[-1]) if not pd.isna(rv.iloc[-1]) else 50.0

        e21 = _ema(df_1h["close"], 21)
        e55 = _ema(df_1h["close"], 55)
        e21_now = float(e21.iloc[-1])
        e55_now = float(e55.iloc[-1])
        price_1h = float(df_1h["close"].iloc[-1])

        # Slope: change over last 5 bars as fraction of current EMA21
        slope_5_raw = e21.diff(5).iloc[-1]
        slope_5 = float(slope_5_raw) if not pd.isna(slope_5_raw) else 0.0
        slope_pct = slope_5 / e21_now if e21_now > 0 else 0.0

        price_vs_ema21 = "above" if price_1h >= e21_now else "below"
        ema21_vs_ema55 = "above" if e21_now >= e55_now else "below"

        reasons = [
            f"rsi_1h={rsi_val:.1f}",
            f"price_{price_vs_ema21}_ema21",
            f"ema21_{ema21_vs_ema55}_ema55",
            f"slope_pct={slope_pct * 100:.2f}pct",
        ]

        if (rsi_val < 30
                and price_vs_ema21 == "below"
                and ema21_vs_ema55 == "below"
                and slope_pct < -0.0005):
            return {
                "bias": "bearish_crash",
                "rsi_1h": rsi_val,
                "ema21_slope_pct": slope_pct,
                "price_vs_ema21": price_vs_ema21,
                "ema21_vs_ema55": ema21_vs_ema55,
                "size_mult_long": 0.4,
                "size_mult_short": 1.2,
                "long_require_capitulation": True,
                "short_require_capitulation": False,
                "reasons": reasons,
            }

        if (rsi_val < 45
                and price_vs_ema21 == "below"
                and slope_pct < 0):
            return {
                "bias": "bearish_trend",
                "rsi_1h": rsi_val,
                "ema21_slope_pct": slope_pct,
                "price_vs_ema21": price_vs_ema21,
                "ema21_vs_ema55": ema21_vs_ema55,
                "size_mult_long": 0.7,
                "size_mult_short": 1.1,
                "long_require_capitulation": False,
                "short_require_capitulation": False,
                "reasons": reasons,
            }

        if (rsi_val > 70
                and price_vs_ema21 == "above"
                and ema21_vs_ema55 == "above"
                and slope_pct > 0.0005):
            return {
                "bias": "bullish_expansion",
                "rsi_1h": rsi_val,
                "ema21_slope_pct": slope_pct,
                "price_vs_ema21": price_vs_ema21,
                "ema21_vs_ema55": ema21_vs_ema55,
                "size_mult_long": 1.2,
                "size_mult_short": 0.4,
                "long_require_capitulation": False,
                "short_require_capitulation": True,
                "reasons": reasons,
            }

        if (rsi_val > 55
                and price_vs_ema21 == "above"
                and slope_pct > 0):
            return {
                "bias": "bullish_trend",
                "rsi_1h": rsi_val,
                "ema21_slope_pct": slope_pct,
                "price_vs_ema21": price_vs_ema21,
                "ema21_vs_ema55": ema21_vs_ema55,
                "size_mult_long": 1.1,
                "size_mult_short": 0.7,
                "long_require_capitulation": False,
                "short_require_capitulation": False,
                "reasons": reasons,
            }

        return {**_default, "rsi_1h": rsi_val, "ema21_slope_pct": slope_pct,
                "price_vs_ema21": price_vs_ema21, "ema21_vs_ema55": ema21_vs_ema55,
                "reasons": reasons}

    except Exception as exc:
        return {**_default, "reasons": [f"htf_bias_error:{exc}"]}
