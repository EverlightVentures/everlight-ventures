"""Session VWAP -- resets at major session opens.

Tracks VWAP for each trading session:
- Asia:    00:00 UTC (8 PM ET / 5 PM PT)
- London:  08:00 UTC (3 AM ET / 12 AM PT)
- New York: 13:30 UTC (9:30 AM ET / 6:30 AM PT)

Price above session VWAP = session is bullish. Below = bearish.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import time as dtime


# Session open times in UTC
SESSION_OPENS = {
    "asia":     dtime(0, 0),
    "london":   dtime(8, 0),
    "new_york": dtime(13, 30),
}


def _assign_session(utc_hour: int, utc_minute: int) -> str:
    """Assign a UTC time to its active session."""
    minutes = utc_hour * 60 + utc_minute
    if minutes < 480:       # 00:00 - 07:59 UTC
        return "asia"
    elif minutes < 810:     # 08:00 - 13:29 UTC
        return "london"
    else:                   # 13:30 - 23:59 UTC
        return "new_york"


def session_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Compute VWAP for each session, resetting at session boundaries.

    Returns DataFrame with columns: session_vwap, session_name.
    Expects df to have 'time', 'high', 'low', 'close', 'volume' columns.
    """
    if df is None or df.empty or len(df) < 2:
        return pd.DataFrame(
            {"session_vwap": pd.Series(dtype=float), "session_name": pd.Series(dtype=str)},
            index=df.index if df is not None else [],
        )

    times = pd.to_datetime(df["time"], utc=True)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, np.nan)

    # Assign sessions
    sessions = [_assign_session(t.hour, t.minute) for t in times]

    # Build session groups: new group when session changes
    groups = []
    current_session = sessions[0]
    group_id = 0
    for s in sessions:
        if s != current_session:
            group_id += 1
            current_session = s
        groups.append(group_id)

    group_series = pd.Series(groups, index=df.index)
    cum_tpv = (tp * vol).groupby(group_series).cumsum()
    cum_vol = vol.groupby(group_series).cumsum()

    svwap = cum_tpv / cum_vol.replace(0, np.nan)

    return pd.DataFrame({
        "session_vwap": svwap,
        "session_name": sessions,
    }, index=df.index)


def session_vwap_bias(df: pd.DataFrame) -> dict:
    """Get current session VWAP and price position relative to it.

    Returns:
        dict with session_name, session_vwap, price_above (bool), distance_pct
    """
    if df is None or df.empty or len(df) < 5:
        return {"session_name": "unknown", "session_vwap": None,
                "price_above": None, "distance_pct": 0.0}

    result = session_vwap(df)
    if result.empty:
        return {"session_name": "unknown", "session_vwap": None,
                "price_above": None, "distance_pct": 0.0}

    current_vwap = float(result["session_vwap"].iloc[-1]) if not pd.isna(result["session_vwap"].iloc[-1]) else None
    current_session = result["session_name"].iloc[-1]
    price = float(df["close"].iloc[-1])

    if current_vwap is None or current_vwap <= 0:
        return {"session_name": current_session, "session_vwap": None,
                "price_above": None, "distance_pct": 0.0}

    distance_pct = (price - current_vwap) / current_vwap * 100

    return {
        "session_name": current_session,
        "session_vwap": round(current_vwap, 8),
        "price_above": price > current_vwap,
        "distance_pct": round(distance_pct, 4),
    }
