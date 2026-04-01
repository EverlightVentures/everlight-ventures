"""Pro Indicators Integration Module.

Collects all pro indicator signals and computes a combined score modifier
that plugs into the existing score_modifiers pipeline in main.py.

Usage in main.py (after contract_mod section, around line 7000):
    from market.pro_indicators import score_pro_indicators
    pro_mod = score_pro_indicators(direction, df_15m, contract_ctx, config)
    if pro_mod and pro_mod.bonus != 0 and selected_v4 is not None:
        selected_v4 = dict(selected_v4)
        adjusted = int(selected_v4.get("score") or 0) + pro_mod.bonus
        selected_v4["score"] = max(0, min(100, adjusted))
        selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
        score_gate_pass = bool(selected_v4["pass"])
        score_gate_pass_effective = bool(score_gate_pass)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger("pro_indicators")


@dataclass
class ProModResult:
    bonus: int = 0
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def score_pro_indicators(
    direction: str,
    df_15m: pd.DataFrame,
    contract_ctx: dict,
    config: dict,
    logs_dir: Path | None = None,
) -> ProModResult:
    """Compute combined score modifier from all pro indicators.

    Reads pro_indicators section from config. Each sub-indicator can be
    individually enabled/disabled.

    Returns ProModResult with total bonus clamped to [-15, +15].
    """
    result = ProModResult()

    if not direction or df_15m is None or df_15m.empty:
        return result

    pro_cfg = config.get("pro_indicators", {}) if isinstance(config, dict) else {}
    if not pro_cfg:
        return result

    d = direction.lower().strip()

    # Resolve logs_dir for history files
    if logs_dir is None:
        import os
        base = Path(os.environ.get("CRYPTO_BOT_DIR", Path(__file__).resolve().parent.parent))
        logs_dir = base / "logs"

    contract_history_path = logs_dir / "contract_context.jsonl"
    trade_log_path = logs_dir / "trade_labels.jsonl"

    # --- 1. BB Squeeze Percentile ---
    try:
        sq_cfg = pro_cfg.get("bb_squeeze_percentile", {})
        if sq_cfg.get("enabled", False):
            from indicators.squeeze import bb_width_percentile
            pctile = bb_width_percentile(df_15m)
            if not pctile.empty:
                current_pctile = float(pctile.iloc[-1])
                threshold = float(sq_cfg.get("threshold", 10))
                boost = int(sq_cfg.get("boost", 5))
                result.details["bb_squeeze_percentile"] = round(current_pctile, 1)
                if current_pctile < threshold:
                    # Extreme squeeze -- boost breakout setups
                    result.bonus += boost
                    result.reasons.append(f"bb_squeeze_{current_pctile:.0f}pct (<{threshold})")
    except Exception as e:
        logger.debug(f"BB squeeze error: {e}")

    # --- 2. TTM Squeeze Fire ---
    try:
        ttm_cfg = pro_cfg.get("ttm_squeeze", {})
        if ttm_cfg.get("enabled", False):
            from indicators.squeeze import squeeze_fire
            fired = squeeze_fire(df_15m)
            if not fired.empty:
                # Check if squeeze fired in last 3 bars
                recent_fire = bool(fired.iloc[-3:].any())
                boost = int(ttm_cfg.get("boost", 10))
                result.details["ttm_squeeze_fire"] = recent_fire
                if recent_fire:
                    result.bonus += boost
                    result.reasons.append("ttm_squeeze_FIRED")
    except Exception as e:
        logger.debug(f"TTM squeeze error: {e}")

    # --- 3. Funding Slope ---
    try:
        fund_cfg = pro_cfg.get("funding_slope", {})
        if fund_cfg.get("enabled", False):
            from indicators.funding import funding_slope, funding_slope_signal, extract_funding_history
            window = int(fund_cfg.get("window", 12))
            penalty = int(fund_cfg.get("penalty", 5))
            history = extract_funding_history(contract_history_path, max_entries=window * 2)
            slope = funding_slope(history, window)
            signal = funding_slope_signal(slope, d)
            result.details["funding_slope"] = round(slope, 6)
            result.details["funding_slope_signal"] = signal
            if signal == "against":
                result.bonus -= penalty
                result.reasons.append(f"funding_slope_against_{d} (slope={slope:.6f})")
            elif signal == "favorable":
                result.bonus += max(1, penalty // 2)
                result.reasons.append(f"funding_slope_favorable_{d}")
    except Exception as e:
        logger.debug(f"Funding slope error: {e}")

    # --- 4. Session VWAP ---
    try:
        sv_cfg = pro_cfg.get("session_vwap", {})
        if sv_cfg.get("enabled", False):
            from indicators.session_vwap import session_vwap_bias
            bias = session_vwap_bias(df_15m)
            boost = int(sv_cfg.get("boost", 3))
            result.details["session_vwap"] = bias
            if bias.get("price_above") is not None:
                aligned = (d == "long" and bias["price_above"]) or (d == "short" and not bias["price_above"])
                if aligned:
                    result.bonus += boost
                    result.reasons.append(f"session_vwap_aligned_{bias['session_name']}_{d}")
    except Exception as e:
        logger.debug(f"Session VWAP error: {e}")

    # --- 5. Kelly Sizing Confidence ---
    try:
        kelly_cfg = pro_cfg.get("kelly_sizing", {})
        if kelly_cfg.get("enabled", False):
            from strategy.position_sizing import kelly_from_trade_log
            kelly = kelly_from_trade_log(trade_log_path)
            result.details["kelly"] = kelly
            if kelly.get("sufficient_data") and kelly.get("kelly_pct", 0) > 15:
                result.bonus += 3
                result.reasons.append(f"kelly_confident_{kelly['kelly_pct']:.1f}%")
            elif kelly.get("sufficient_data") and kelly.get("kelly_pct", 0) <= 0:
                result.bonus -= 3
                result.reasons.append("kelly_negative_edge")
    except Exception as e:
        logger.debug(f"Kelly error: {e}")

    # --- 6. OI Rate of Change ---
    try:
        oi_cfg = pro_cfg.get("oi_roc", {})
        if oi_cfg.get("enabled", False):
            from indicators.oi_analysis import oi_roc, extract_oi_history
            window = int(oi_cfg.get("window", 12))
            boost = int(oi_cfg.get("boost", 5))
            oi_hist = extract_oi_history(contract_history_path)
            roc_val, roc_signal = oi_roc(oi_hist, window)
            result.details["oi_roc"] = roc_val
            result.details["oi_roc_signal"] = roc_signal
            # OI rising with trade direction = confirmation
            if roc_signal == "rising" and d == "long":
                result.bonus += boost
                result.reasons.append(f"oi_rising_confirms_long (roc={roc_val:.4f})")
            elif roc_signal == "falling" and d == "short":
                result.bonus += boost
                result.reasons.append(f"oi_falling_confirms_short (roc={roc_val:.4f})")
            elif roc_signal == "rising" and d == "short":
                result.bonus -= max(1, boost // 2)
                result.reasons.append(f"oi_rising_against_short")
            elif roc_signal == "falling" and d == "long":
                result.bonus -= max(1, boost // 2)
                result.reasons.append(f"oi_falling_against_long")
    except Exception as e:
        logger.debug(f"OI ROC error: {e}")

    # --- 7. Anchored VWAP bias (bonus context, small boost) ---
    try:
        avwap_cfg = pro_cfg.get("anchored_vwap", {})
        if avwap_cfg.get("enabled", True):  # enabled by default, lightweight
            from indicators.anchored_vwap import anchored_vwap_bias
            bias = anchored_vwap_bias(df_15m)
            result.details["anchored_vwap"] = bias
            # Long above swing-low AVWAP = move still valid
            if d == "long" and bias.get("above_low_avwap"):
                result.bonus += 2
                result.reasons.append("above_swing_low_avwap")
            elif d == "short" and bias.get("below_high_avwap"):
                result.bonus += 2
                result.reasons.append("below_swing_high_avwap")
    except Exception as e:
        logger.debug(f"Anchored VWAP error: {e}")

    # Clamp total
    max_bonus = int(pro_cfg.get("total_max", 15))
    result.bonus = max(-max_bonus, min(max_bonus, result.bonus))

    if result.reasons:
        logger.info(f"Pro indicators: bonus={result.bonus}, reasons={result.reasons}")

    return result
