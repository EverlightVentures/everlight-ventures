"""Multi-lane consensus scoring.

When multiple independent attack lanes confirm the same entry direction,
conviction increases. This module scores secondary alignment and returns
a consensus bonus added to the primary score.

Bonus table:
  1 confirming lane  -> +5 pts
  2 confirming lanes -> +10 pts
  3+ confirming lanes -> +18 pts  (synergistic burst: can lift FULL -> MONSTER)

The bonus is modest -- it supplements signal strength, not replaces it.
A setup with 3 confirming lanes is genuinely special.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class LaneConsensusResult:
    primary_lane: str = ""
    confirming_lanes: list = field(default_factory=list)
    consensus_count: int = 0
    bonus: int = 0
    reason: str = ""


def evaluate_lane_consensus(
    *,
    primary_lane: str,
    direction: str,
    regime: str,
    expansion_phase: str,
    sweep: dict | None,
    squeeze: dict | None,
    contract_ctx: dict | None,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame | None = None,
    config: dict,
) -> LaneConsensusResult:
    """Score how many secondary lanes also support the current entry.

    Only lanes different from the primary contribute. Each applies a
    lightweight check (not full v4 scoring) to confirm alignment.
    Results are additive: the caller adds consensus.bonus to v4 score.
    """
    primary = str(primary_lane).upper().strip()
    d = direction.lower().strip() if direction else "long"
    confirming: list[str] = []

    # Lane Q: Funding rate aligned (shorts pay when going long, etc.)
    if primary != "Q" and contract_ctx:
        funding_bias = str(contract_ctx.get("funding_bias") or "")
        if d == "long" and funding_bias == "SHORTS_PAY":
            confirming.append("Q")
        elif d == "short" and funding_bias == "LONGS_PAY":
            confirming.append("Q")

    # Lane T: Orderflow / OI-price relationship confirms direction
    if primary != "T" and contract_ctx:
        oi_price = str(contract_ctx.get("oi_price_rel") or "")
        if d == "long" and oi_price in ("UP+OI_UP", "DOWN+OI_DOWN"):
            confirming.append("T")
        elif d == "short" and oi_price in ("DOWN+OI_UP", "UP+OI_DOWN"):
            confirming.append("T")

    # Lane C: Sweep confirmation (secondary signal)
    if primary != "C" and sweep and sweep.get("detected"):
        confirming.append("C")

    # Lane E: Squeeze impulse confirmation
    if primary != "E" and squeeze and squeeze.get("detected"):
        phase = str(expansion_phase or "").upper()
        if phase in ("IGNITION", "EXPANSION"):
            confirming.append("E")

    # Lane A: Trend alignment (EMA21 slope on 1h)
    if primary != "A" and regime == "trend":
        try:
            if not df_1h.empty and len(df_1h) >= 25:
                from indicators.ema import ema as _ema
                e21 = _ema(df_1h["close"], 21)
                slope = float(e21.diff().tail(4).mean())
                if d == "long" and slope > 0:
                    confirming.append("A")
                elif d == "short" and slope < 0:
                    confirming.append("A")
        except Exception:
            pass

    # Lane U: Price vs 200 MA on 1h (macro regime alignment)
    if primary != "U" and not df_1h.empty and len(df_1h) >= 200:
        try:
            from indicators.ema import ema as _ema
            e200 = _ema(df_1h["close"], 200)
            ma200_val = float(e200.iloc[-1]) if not pd.isna(e200.iloc[-1]) else 0.0
            cur_price = float(df_1h["close"].iloc[-1])
            if ma200_val > 0:
                if d == "long" and cur_price > ma200_val:
                    confirming.append("U")
                elif d == "short" and cur_price < ma200_val:
                    confirming.append("U")
        except Exception:
            pass

    # Lane N: VWAP alignment
    if primary != "N":
        try:
            if not df_1h.empty and "time" in df_1h.columns and len(df_1h) >= 5:
                from indicators.vwap import vwap as _vwap
                vwap_series = _vwap(df_1h)
                if not vwap_series.empty:
                    vwap_val = float(vwap_series.iloc[-1])
                    cur_price = float(df_15m["close"].iloc[-1]) if not df_15m.empty else 0.0
                    if vwap_val > 0 and cur_price > 0:
                        if d == "long" and cur_price >= vwap_val:
                            confirming.append("N")
                        elif d == "short" and cur_price <= vwap_val:
                            confirming.append("N")
        except Exception:
            pass

    # Lane M: Volume climax (2.5x spike at any key level = capitulation confirm)
    if primary != "M" and not df_15m.empty and len(df_15m) >= 21:
        try:
            vol_now = float(df_15m["volume"].iloc[-1])
            vol_avg = float(df_15m["volume"].rolling(20).mean().iloc[-1])
            if vol_avg > 0 and vol_now >= vol_avg * 2.5:
                confirming.append("M")
        except Exception:
            pass

    # Bonus table
    n = len(confirming)
    if n >= 3:
        bonus = 18
    elif n == 2:
        bonus = 10
    elif n == 1:
        bonus = 5
    else:
        bonus = 0

    lanes_str = ",".join(confirming) if confirming else "none"
    reason = f"consensus_{n}x[{lanes_str}]+{bonus}pts"

    return LaneConsensusResult(
        primary_lane=primary,
        confirming_lanes=confirming,
        consensus_count=n,
        bonus=bonus,
        reason=reason,
    )
