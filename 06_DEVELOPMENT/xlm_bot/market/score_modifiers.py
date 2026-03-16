"""Score modifiers from contract context and liquidation cascade detection.

Provides bounded bonus/penalty points from OI, funding, and basis data.
Also classifies large price+OI events as liquidation cascades.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ScoreModResult:
    bonus: int = 0
    reasons: list[str] = field(default_factory=list)
    crowding_penalty: int = 0
    oi_signal: int = 0
    basis_signal: int = 0
    oi_price_rel: str = "UNKNOWN"


def score_contract_modifiers(
    direction: str,
    contract_ctx: dict,
    candle_ctx: dict,
    config: dict | None = None,
) -> ScoreModResult:
    """Compute bounded score modifiers from contract context.

    Args:
        direction: "long" or "short"
        contract_ctx: ContractSnapshot as dict
        candle_ctx: {price_delta_15m, regime, atr_expanding}
        config: contract_context config section
    Returns:
        ScoreModResult with total bonus clamped to [-total_mod_max, +total_mod_max]
    """
    cfg = config or {}
    crowding_max = int(cfg.get("crowding_penalty_max", 5) or 5)
    oi_max = int(cfg.get("oi_signal_max", 5) or 5)
    basis_max = int(cfg.get("basis_signal_max", 3) or 3)
    total_max = int(cfg.get("total_mod_max", 10) or 10)
    funding_mild = float(cfg.get("funding_mild_hr", 0.002) or 0.002)
    funding_extreme = float(cfg.get("funding_extreme_hr", 0.005) or 0.005)

    result = ScoreModResult()
    if not contract_ctx or not direction:
        return result

    d = direction.lower().strip()
    bias = str(contract_ctx.get("funding_bias") or "UNKNOWN")
    rate_hr = _flt(contract_ctx.get("funding_rate_hr"))
    oi_price = str(contract_ctx.get("oi_price_rel") or "UNKNOWN")
    basis_bps = _flt(contract_ctx.get("basis_bps"))

    result.oi_price_rel = oi_price

    # --- 1. Crowding penalty (0 to -crowding_max) ---
    if rate_hr is not None:
        rate_abs = abs(rate_hr)
        if bias == "LONGS_PAY" and d == "long":
            result.crowding_penalty = -crowding_max if rate_abs >= funding_extreme else (-3 if rate_abs >= funding_mild else 0)
            if result.crowding_penalty:
                result.reasons.append(f"crowded_longs (rate {rate_hr:.4f}%/hr)")
        elif bias == "SHORTS_PAY" and d == "short":
            result.crowding_penalty = -crowding_max if rate_abs >= funding_extreme else (-3 if rate_abs >= funding_mild else 0)
            if result.crowding_penalty:
                result.reasons.append(f"crowded_shorts (rate {rate_hr:.4f}%/hr)")

    # --- 2. OI + Price relationship (-oi_max to +oi_max) ---
    _oi_map = {
        # (oi_price_rel, direction) -> modifier
        ("UP+OI_UP", "long"): oi_max,
        ("UP+OI_UP", "short"): -3,
        ("UP+OI_DOWN", "long"): -2,
        ("UP+OI_DOWN", "short"): 2,
        ("DOWN+OI_UP", "long"): -3,
        ("DOWN+OI_UP", "short"): oi_max,
        ("DOWN+OI_DOWN", "long"): 2,
        ("DOWN+OI_DOWN", "short"): -2,
    }
    oi_mod = _oi_map.get((oi_price, d), 0)
    result.oi_signal = max(-oi_max, min(oi_max, oi_mod))
    if result.oi_signal:
        result.reasons.append(f"oi_price={oi_price} {'confirms' if result.oi_signal > 0 else 'contradicts'} {d}")

    # --- 3. Basis signal (-basis_max to +basis_max) ---
    if basis_bps is not None:
        if basis_bps > 10:
            # Premium — bullish
            result.basis_signal = 2 if d == "long" else -2
            result.reasons.append(f"basis_premium +{basis_bps:.1f}bps {'supports' if d == 'long' else 'against'} {d}")
        elif basis_bps < -10:
            # Discount — bearish
            result.basis_signal = 2 if d == "short" else -2
            result.reasons.append(f"basis_discount {basis_bps:.1f}bps {'supports' if d == 'short' else 'against'} {d}")
    result.basis_signal = max(-basis_max, min(basis_max, result.basis_signal))

    # --- Total ---
    result.bonus = max(-total_max, min(total_max, result.crowding_penalty + result.oi_signal + result.basis_signal))
    return result


# =====================================================================
# Liquidation cascade detection
# =====================================================================

@dataclass
class CascadeEvent:
    timestamp: str = ""
    cascade_type: str = ""
    price_delta_pct: float = 0.0
    oi_delta_pct: float = 0.0
    severity: str = "MINOR"


def detect_liquidation_cascade(
    contract_ctx: dict,
    candle_ctx: dict,
    config: dict | None = None,
) -> Optional[CascadeEvent]:
    """Detect large move + OI change as liquidation or build cascade."""
    cfg = config or {}
    price_thresh = float(cfg.get("cascade_price_threshold_pct", 0.015) or 0.015)
    oi_thresh = float(cfg.get("cascade_oi_threshold_pct", 0.02) or 0.02)

    price_delta = _flt(candle_ctx.get("price_delta_15m"))
    oi_delta = _flt(contract_ctx.get("oi_delta_15m"))

    if price_delta is None or oi_delta is None:
        return None

    abs_price = abs(price_delta)
    abs_oi = abs(oi_delta)

    if abs_price < price_thresh:
        return None  # not a large enough move

    cascade_type = None
    if price_delta < 0 and oi_delta < -oi_thresh:
        cascade_type = "LONG_LIQUIDATION_CASCADE"
    elif price_delta < 0 and oi_delta > oi_thresh:
        cascade_type = "SHORT_BUILD_CASCADE"
    elif price_delta > 0 and oi_delta < -oi_thresh:
        cascade_type = "SHORT_LIQUIDATION_CASCADE"
    elif price_delta > 0 and oi_delta > oi_thresh:
        cascade_type = "LONG_BUILD_CASCADE"

    if cascade_type is None:
        return None

    # Severity
    if abs_price > 0.04 or abs_oi > 0.10:
        severity = "MAJOR"
    elif abs_price > 0.02 or abs_oi > 0.05:
        severity = "MODERATE"
    else:
        severity = "MINOR"

    return CascadeEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        cascade_type=cascade_type,
        price_delta_pct=round(price_delta, 6),
        oi_delta_pct=round(oi_delta, 6),
        severity=severity,
    )


def log_cascade_event(event: CascadeEvent, log_path: Path) -> None:
    """Append cascade event to JSONL log."""
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")
    except Exception:
        pass


def score_zone_modifier(
    direction: str,
    zone_context: dict,
    config: dict | None = None,
) -> ScoreModResult:
    """Compute score modifier from macro zone proximity and micro precision flags.

    Args:
        direction: "long" or "short"
        zone_context: dict from compute_zone_context()
        config: optional overrides
    Returns:
        ScoreModResult with bonus clamped to [-5, +5]
    """
    cfg = config or {}
    max_bonus = int(cfg.get("zone_mod_max", 5) or 5)
    result = ScoreModResult()

    if not zone_context or not direction:
        return result

    d = direction.lower().strip()
    nearest = zone_context.get("nearest")
    if not nearest:
        return result

    inside = bool(nearest.get("inside", False))
    dist_atr = nearest.get("distance_norm_atr")
    zone_type = nearest.get("zone_type", "")
    types_merged = nearest.get("types_merged") or [zone_type]
    macro_bias = zone_context.get("macro_bias", "neutral")
    micro_flags = zone_context.get("micro_flags") or {}

    bonus = 0
    reasons = []

    # Near macro zone (within 1.5 ATR): +3 — zone confirms S/R
    near = inside or (dist_atr is not None and dist_atr <= 1.5)
    if near:
        bonus += 3
        reasons.append("near_macro_zone")

    # Inside wick zone with rejection flag: +5 (high-conviction reversal)
    if inside and "WICK_HIGH" in types_merged and micro_flags.get("rejection_up"):
        if d == "short":
            bonus += 2  # stacks with near_macro_zone
            reasons.append("wick_high_rejection_short")
    if inside and "WICK_LOW" in types_merged and micro_flags.get("rejection_down"):
        if d == "long":
            bonus += 2
            reasons.append("wick_low_rejection_long")

    # Inside body zone with compression: +2 (mean reversion from value)
    micro = zone_context.get("micro") or {}
    if inside and zone_type in ("BODY", "BODY_EDGE", "MIXED") and micro.get("compression"):
        bonus += 2
        reasons.append("body_zone_compression")

    # Trading against macro bias: -3 penalty
    if macro_bias == "short_bias" and d == "long":
        bonus -= 3
        reasons.append("against_macro_bias_long_in_wick_high")
    elif macro_bias == "long_bias" and d == "short":
        bonus -= 3
        reasons.append("against_macro_bias_short_in_wick_low")

    result.bonus = max(-max_bonus, min(max_bonus, bonus))
    result.reasons = reasons
    return result


def score_alignment_modifier(
    direction: str,
    df_15m,
    df_1h,
    df_4h,
    config: dict | None = None,
) -> ScoreModResult:
    """Multi-timeframe alignment bonus.

    Checks EMA21 slope + RSI direction on 15m/1h/4h.
    3 TFs aligned: +8, 2 aligned: +4, 1: 0, 0 (all against): -4.
    """
    cfg = config or {}
    max_bonus = int(cfg.get("alignment_max_bonus", 8) or 8)
    max_penalty = int(cfg.get("alignment_max_penalty", 5) or 5)
    result = ScoreModResult()

    if not direction:
        return result

    d = direction.lower().strip()
    aligned_count = 0
    tf_details = []

    for label, df in [("15m", df_15m), ("1h", df_1h), ("4h", df_4h)]:
        bias = _tf_directional_bias(df, d)
        if bias > 0:
            aligned_count += 1
        tf_details.append(f"{label}={'Y' if bias > 0 else 'N'}")

    bonus_map = {3: max_bonus, 2: 4, 1: 0, 0: -4}
    raw = bonus_map.get(aligned_count, 0)
    result.bonus = max(-max_penalty, min(max_bonus, raw))
    if result.bonus != 0:
        result.reasons.append(f"tf_align_{aligned_count}/3 ({','.join(tf_details)})")

    return result


def _tf_directional_bias(df, direction: str) -> int:
    """Return +1 if timeframe aligns with direction, -1 if against, 0 if neutral."""
    if df is None or not hasattr(df, "empty") or df.empty or len(df) < 25:
        return 0
    try:
        import pandas as pd
        from indicators.ema import ema
        from indicators.rsi import rsi
        e21 = ema(df["close"], 21)
        slope = float(e21.diff().tail(4).mean())
        r = rsi(df["close"], 14)
        rsi_val = float(r.iloc[-1]) if not pd.isna(r.iloc[-1]) else 50.0
    except Exception:
        return 0

    if direction == "long":
        if slope > 0 and rsi_val > 50:
            return 1
        elif slope < 0 and rsi_val < 50:
            return -1
    else:
        if slope < 0 and rsi_val < 50:
            return 1
        elif slope > 0 and rsi_val > 50:
            return -1
    return 0


def institutional_oi_gate(
    direction: str,
    contract_ctx: dict,
    config: dict | None = None,
) -> ScoreModResult:
    """Institutional accumulation / short-squeeze risk gate.

    Detects patterns where institutional players are likely accumulating longs:
      - OI rising while price falls (smart money buying dips)
      - Sustained 24h OI build
      - Extreme negative funding (shorts overloaded, squeeze risk)

    Penalizes shorts entering into these conditions.
    Rewards longs when accumulation is confirmed.

    Returns ScoreModResult clamped to [-10, +10].
    """
    cfg = config or {}
    result = ScoreModResult()

    if not contract_ctx or not direction:
        return result

    d = direction.lower().strip()
    oi_price = str(contract_ctx.get("oi_price_rel") or "UNKNOWN")
    funding_bias = str(contract_ctx.get("funding_bias") or "UNKNOWN")
    rate_hr = _flt(contract_ctx.get("funding_rate_hr"))
    oi_24h = _flt(contract_ctx.get("oi_24h_change_pct"))

    # Accumulation signal: OI builds as price dips = institutional buying
    if oi_price == "DOWN+OI_UP":
        if d == "short":
            result.bonus -= 8
            result.reasons.append("institutional_accumulation_block_short")
        elif d == "long":
            result.bonus += 5
            result.reasons.append("accumulation_supports_long")

    # Sustained 24h OI growth while shorting is dangerous
    if oi_24h is not None and oi_24h > 0.05 and d == "short":
        result.bonus -= 5
        result.reasons.append(f"oi_build_24h_{oi_24h:.1%}_caution_short")

    # Extreme negative funding = shorts being charged heavily, squeeze risk
    if rate_hr is not None and funding_bias == "SHORTS_PAY" and d == "short":
        rate_abs = abs(rate_hr)
        if rate_abs >= 0.008:
            result.bonus -= 5
            result.reasons.append(f"extreme_short_funding_{rate_hr:.4f}pct_hr_squeeze_risk")

    max_mod = int(cfg.get("institutional_max_mod", 10) or 10)
    result.bonus = max(-max_mod, min(max_mod, result.bonus))
    return result


def _flt(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
