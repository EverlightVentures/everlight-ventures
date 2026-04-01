"""Hindsight Analyzer -- self-review of missed opportunities.

Every N minutes, looks back at recent price action and identifies
trades the bot SHOULD have taken but didn't. Logs missed opportunities
and adjusts future scoring to be more/less aggressive.

Also provides a forward-looking opportunity scan: where are the nearest
high-probability setups based on current structure?
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd


def analyze_missed_trades(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    decisions_path: str,
    lookback_hours: int = 6,
) -> dict:
    """Look back at recent price action and find missed opportunities.
    
    Scans the last N hours of 1H candles for big moves the bot sat out.
    A 'missed trade' is when price moved > 0.3% in one direction while
    the bot was flat (no position).
    
    Returns:
        missed_count: number of missed opportunities
        missed_usd: estimated total USD missed (per contract)
        biggest_miss: details of the largest missed move
        pattern: what the missed moves had in common
        lesson: what the bot should adjust
    """
    result = {
        "missed_count": 0,
        "missed_usd": 0.0,
        "biggest_miss": None,
        "pattern": "none",
        "lesson": "none",
        "lookback_hours": lookback_hours,
    }
    
    if df_1h is None or len(df_1h) < 4:
        return result
    
    # Look at recent 1H candles for big moves
    lookback_bars = min(lookback_hours, len(df_1h))
    recent = df_1h.iloc[-lookback_bars:]
    
    missed_moves = []
    for i in range(len(recent)):
        candle = recent.iloc[i]
        c_high = float(candle["high"])
        c_low = float(candle["low"])
        c_open = float(candle["open"])
        c_close = float(candle["close"])
        c_range = c_high - c_low
        
        if c_open <= 0:
            continue
        
        move_pct = abs(c_close - c_open) / c_open
        
        # A significant move is > 0.3% on 1H
        if move_pct >= 0.003:
            direction = "long" if c_close > c_open else "short"
            move_usd = abs(c_close - c_open) * 5000  # 5000 XLM per contract
            
            # Check for wick rejection setup
            body = abs(c_close - c_open)
            wick_pct = 1.0 - (body / c_range) if c_range > 0 else 0
            had_wick_setup = wick_pct >= 0.45
            
            missed_moves.append({
                "direction": direction,
                "move_pct": round(move_pct * 100, 3),
                "move_usd": round(move_usd, 2),
                "open": round(c_open, 6),
                "close": round(c_close, 6),
                "had_wick_setup": had_wick_setup,
                "wick_pct": round(wick_pct, 3),
                "bar_idx": i,
            })
    
    if not missed_moves:
        return result
    
    result["missed_count"] = len(missed_moves)
    result["missed_usd"] = round(sum(m["move_usd"] for m in missed_moves), 2)
    
    # Find biggest miss
    biggest = max(missed_moves, key=lambda m: m["move_usd"])
    result["biggest_miss"] = biggest
    
    # Pattern detection
    long_count = sum(1 for m in missed_moves if m["direction"] == "long")
    short_count = sum(1 for m in missed_moves if m["direction"] == "short")
    wick_count = sum(1 for m in missed_moves if m["had_wick_setup"])
    
    if long_count > short_count * 2:
        result["pattern"] = "missing_longs"
        result["lesson"] = "Bot is too bearish -- lower long entry threshold or disable short bias"
    elif short_count > long_count * 2:
        result["pattern"] = "missing_shorts"
        result["lesson"] = "Bot is too bullish -- consider reversal shorts at resistance"
    elif wick_count >= len(missed_moves) * 0.5:
        result["pattern"] = "missing_wick_reversals"
        result["lesson"] = "Wick reversals are the dominant pattern -- prioritize htf_swing entries"
    else:
        result["pattern"] = "mixed"
        result["lesson"] = "No clear pattern -- maintain current balance"
    
    return result


def scan_opportunities(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    fibs: dict,
    levels: dict,
    atr_15m: float,
) -> dict:
    """Forward-looking opportunity scan.
    
    Identifies the best upcoming setups based on current price structure:
    - Nearest Fib levels where wick reversals could trigger
    - Range edges where FVG retests could set up
    - Trend continuation points
    - Compression breakout zones
    
    Returns a ranked list of opportunities with estimated R:R.
    """
    opportunities = []
    
    if price <= 0 or atr_15m <= 0:
        return {"opportunities": [], "best_long": None, "best_short": None}
    
    # 1. Nearest Fib levels (potential reversal zones)
    if fibs:
        for name, level in fibs.items():
            if not isinstance(level, (int, float)) or level <= 0:
                continue
            dist = abs(price - level)
            dist_atr = dist / atr_15m if atr_15m > 0 else 999
            
            if dist_atr > 10:
                continue  # too far away
            
            direction = "long" if level < price else "short"
            # Estimated R:R based on distance to next Fib
            est_rr = max(2.0, min(5.0, dist_atr * 1.5))
            
            opportunities.append({
                "type": "fib_reversal",
                "level": round(level, 6),
                "level_name": f"fib_{name}",
                "direction": direction,
                "distance_atr": round(dist_atr, 2),
                "est_rr": round(est_rr, 1),
                "readiness": "ready" if dist_atr <= 1.0 else "approaching" if dist_atr <= 3.0 else "watching",
            })
    
    # 2. Structure levels (S/R zones)
    if levels:
        for name, level in levels.items():
            if not isinstance(level, (int, float)) or level <= 0:
                continue
            dist = abs(price - level)
            dist_atr = dist / atr_15m if atr_15m > 0 else 999
            
            if dist_atr > 8:
                continue
            
            direction = "long" if level < price else "short"
            
            opportunities.append({
                "type": "structure_sr",
                "level": round(level, 6),
                "level_name": name,
                "direction": direction,
                "distance_atr": round(dist_atr, 2),
                "est_rr": 3.0,
                "readiness": "ready" if dist_atr <= 1.0 else "approaching" if dist_atr <= 3.0 else "watching",
            })
    
    # 3. Bollinger Band edges (squeeze/expansion zones)
    if df_1h is not None and len(df_1h) >= 20:
        closes = df_1h["close"].values[-20:]
        sma = np.mean(closes)
        std = np.std(closes)
        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std
        bb_width = (bb_upper - bb_lower) / sma if sma > 0 else 0
        
        # Near lower band = long opportunity
        if price < sma:
            dist_lower = abs(price - bb_lower) / atr_15m
            if dist_lower <= 3.0:
                opportunities.append({
                    "type": "bb_bounce",
                    "level": round(bb_lower, 6),
                    "level_name": "bb_lower_1h",
                    "direction": "long",
                    "distance_atr": round(dist_lower, 2),
                    "est_rr": 3.0,
                    "readiness": "ready" if dist_lower <= 1.0 else "approaching",
                })
        # Near upper band = short opportunity
        if price > sma:
            dist_upper = abs(price - bb_upper) / atr_15m
            if dist_upper <= 3.0:
                opportunities.append({
                    "type": "bb_rejection",
                    "level": round(bb_upper, 6),
                    "level_name": "bb_upper_1h",
                    "direction": "short",
                    "distance_atr": round(dist_upper, 2),
                    "est_rr": 3.0,
                    "readiness": "ready" if dist_upper <= 1.0 else "approaching",
                })
        
        # Squeeze detection = imminent breakout
        if bb_width < 0.02:  # very tight bands
            opportunities.append({
                "type": "squeeze_breakout",
                "level": round(price, 6),
                "level_name": "bb_squeeze",
                "direction": "neutral",
                "distance_atr": 0,
                "est_rr": 4.0,
                "readiness": "imminent",
            })
    
    # Sort by readiness and distance
    readiness_order = {"imminent": 0, "ready": 1, "approaching": 2, "watching": 3}
    opportunities.sort(key=lambda o: (readiness_order.get(o["readiness"], 4), o["distance_atr"]))
    
    # Best long and short
    best_long = next((o for o in opportunities if o["direction"] == "long" and o["readiness"] in ("ready", "imminent")), None)
    best_short = next((o for o in opportunities if o["direction"] == "short" and o["readiness"] in ("ready", "imminent")), None)
    
    return {
        "opportunities": opportunities[:10],  # top 10
        "best_long": best_long,
        "best_short": best_short,
        "total_ready": sum(1 for o in opportunities if o["readiness"] in ("ready", "imminent")),
        "squeeze_detected": any(o["type"] == "squeeze_breakout" for o in opportunities),
    }
