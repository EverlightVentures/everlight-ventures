"""HTF Macro Zone engine (Monthly + Weekly).

Builds macro support/resistance zones from monthly + weekly OHLC (July 2024 →
present), clusters them, and provides proximity context + micro-precision
readiness labels for the bot and dashboard.

This is context-only — it does NOT alter entry/exit logic or risk sizing.
"""
from __future__ import annotations

import json
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from indicators.atr import atr as calc_atr
from indicators.rsi import rsi as calc_rsi
from indicators.ema import ema as calc_ema


# ---------------------------------------------------------------------------
# A) Monthly data: fetch daily from Coinbase, resample to monthly
# ---------------------------------------------------------------------------

_MONTHLY_CACHE_FILE = "monthly_ohlc.json"
_CACHE_MAX_AGE_HOURS = 12  # re-fetch at most twice a day
_MONTHLY_START = datetime(2024, 7, 1, tzinfo=timezone.utc)


def _fetch_daily_coinbase(product_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Fetch daily candles from Coinbase exchange API (86400s granularity)."""
    import requests

    url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
    granularity = 86400  # 1 day
    max_candles = 300
    chunk_seconds = max_candles * granularity
    all_data: list = []
    current_start = start
    started = _time.time()

    while current_start < end:
        if (_time.time() - started) > 25:
            break
        current_end = min(current_start + timedelta(seconds=chunk_seconds), end)
        params = {
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            "granularity": granularity,
        }
        try:
            resp = requests.get(url, params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    all_data.extend(data)
        except Exception:
            pass
        current_start = current_end
        _time.sleep(0.3)

    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=["timestamp", "low", "high", "open", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def _resample_to_monthly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to monthly bars."""
    if daily_df.empty:
        return daily_df
    df = daily_df.set_index("timestamp")
    monthly = df.resample("MS").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna().reset_index()
    return monthly


def load_monthly_ohlc(
    product_id: str = "XLM-USD",
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Load monthly OHLC, using cache if fresh enough."""
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / _MONTHLY_CACHE_FILE

    # Check cache freshness
    if cache_path.exists():
        try:
            age_hours = (datetime.now(timezone.utc).timestamp() - cache_path.stat().st_mtime) / 3600
            if age_hours < _CACHE_MAX_AGE_HOURS:
                cached = pd.read_json(cache_path, orient="records")
                if not cached.empty and "timestamp" in cached.columns:
                    cached["timestamp"] = pd.to_datetime(cached["timestamp"], utc=True)
                    return cached
        except Exception:
            pass

    # Fetch fresh
    end = datetime.now(timezone.utc)
    daily = _fetch_daily_coinbase(product_id, _MONTHLY_START, end)
    if daily.empty:
        # Fallback to cache even if stale
        if cache_path.exists():
            try:
                cached = pd.read_json(cache_path, orient="records")
                if not cached.empty:
                    cached["timestamp"] = pd.to_datetime(cached["timestamp"], utc=True)
                    return cached
            except Exception:
                pass
        return pd.DataFrame()

    monthly = _resample_to_monthly(daily)
    if not monthly.empty:
        try:
            monthly.to_json(cache_path, orient="records", date_format="iso")
        except Exception:
            pass
    return monthly


# ---------------------------------------------------------------------------
# A2) Weekly data: fetch daily from Coinbase, resample to weekly
# ---------------------------------------------------------------------------

_WEEKLY_CACHE_FILE = "weekly_ohlc.json"


def _resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly bars (ending Sunday)."""
    if daily_df.empty:
        return daily_df
    df = daily_df.set_index("timestamp")
    weekly = df.resample("W").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna().reset_index()
    return weekly


def load_weekly_ohlc(
    product_id: str = "XLM-USD",
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Load weekly OHLC, using cache if fresh enough."""
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / _WEEKLY_CACHE_FILE

    if cache_path.exists():
        try:
            age_hours = (datetime.now(timezone.utc).timestamp() - cache_path.stat().st_mtime) / 3600
            if age_hours < _CACHE_MAX_AGE_HOURS:
                cached = pd.read_json(cache_path, orient="records")
                if not cached.empty and "timestamp" in cached.columns:
                    cached["timestamp"] = pd.to_datetime(cached["timestamp"], utc=True)
                    return cached
        except Exception:
            pass

    end = datetime.now(timezone.utc)
    daily = _fetch_daily_coinbase(product_id, _MONTHLY_START, end)
    if daily.empty:
        if cache_path.exists():
            try:
                cached = pd.read_json(cache_path, orient="records")
                if not cached.empty:
                    cached["timestamp"] = pd.to_datetime(cached["timestamp"], utc=True)
                    return cached
            except Exception:
                pass
        return pd.DataFrame()

    weekly = _resample_to_weekly(daily)
    if not weekly.empty:
        try:
            weekly.to_json(cache_path, orient="records", date_format="iso")
        except Exception:
            pass
    return weekly


# ---------------------------------------------------------------------------
# B) Define monthly zones (wick + body)
# ---------------------------------------------------------------------------

def _monthly_atr(monthly_df: pd.DataFrame) -> float:
    """Average true range of the monthly series."""
    if monthly_df.empty or len(monthly_df) < 2:
        return 0.01  # fallback
    tr_series = pd.concat([
        (monthly_df["high"] - monthly_df["low"]),
        (monthly_df["high"] - monthly_df["close"].shift(1)).abs(),
        (monthly_df["low"] - monthly_df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return float(tr_series.mean())


def define_monthly_zones(monthly_df: pd.DataFrame) -> list[dict]:
    """Create zone primitives from each monthly candle.

    For large-body months (body > 2x ATR), we only use the open/close edges
    as thin zones instead of the full body — a giant body zone spanning
    the entire range provides no useful S/R context.
    """
    if monthly_df.empty:
        return []

    m_atr = _monthly_atr(monthly_df)
    # Zone thickness for wicks and edge zones: ~2% of current price range
    last_close = float(monthly_df["close"].iloc[-1])
    thickness = max(last_close * 0.02, m_atr * 0.02, 0.001)

    zones: list[dict] = []
    for _, row in monthly_df.iterrows():
        o = float(row["open"])
        c = float(row["close"])
        h = float(row["high"])
        l = float(row["low"])
        month_label = str(row["timestamp"])[:7]

        body_low = min(o, c)
        body_high = max(o, c)
        body_size = body_high - body_low

        if body_size <= m_atr * 1.5:
            zones.append({
                "type": "BODY",
                "timeframe": "M",
                "low": body_low,
                "high": body_high,
                "center": (body_low + body_high) / 2,
                "month": month_label,
            })
        else:
            zones.append({
                "type": "BODY_EDGE",
                "timeframe": "M",
                "low": body_low - thickness * 0.5,
                "high": body_low + thickness * 0.5,
                "center": body_low,
                "month": month_label,
            })
            zones.append({
                "type": "BODY_EDGE",
                "timeframe": "M",
                "low": body_high - thickness * 0.5,
                "high": body_high + thickness * 0.5,
                "center": body_high,
                "month": month_label,
            })

        if h > body_high + thickness:
            zones.append({
                "type": "WICK_HIGH",
                "timeframe": "M",
                "low": h - thickness,
                "high": h + thickness,
                "center": h,
                "month": month_label,
            })
        if l < body_low - thickness:
            zones.append({
                "type": "WICK_LOW",
                "timeframe": "M",
                "low": l - thickness,
                "high": l + thickness,
                "center": l,
                "month": month_label,
            })

    return zones


def define_weekly_zones(weekly_df: pd.DataFrame) -> list[dict]:
    """Create zone primitives from each weekly candle.

    Same logic as monthly zones but labeled with timeframe="W" and
    uses weekly period labels.  Large-body weeks get edge zones only.
    """
    if weekly_df.empty:
        return []

    # Weekly ATR for zone sizing
    if len(weekly_df) >= 2:
        tr = pd.concat([
            (weekly_df["high"] - weekly_df["low"]),
            (weekly_df["high"] - weekly_df["close"].shift(1)).abs(),
            (weekly_df["low"] - weekly_df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        w_atr = float(tr.mean())
    else:
        w_atr = 0.01

    last_close = float(weekly_df["close"].iloc[-1])
    thickness = max(last_close * 0.012, w_atr * 0.02, 0.0005)

    zones: list[dict] = []
    for _, row in weekly_df.iterrows():
        o = float(row["open"])
        c = float(row["close"])
        h = float(row["high"])
        l = float(row["low"])
        week_label = str(row["timestamp"])[:10]

        body_low = min(o, c)
        body_high = max(o, c)
        body_size = body_high - body_low

        if body_size <= w_atr * 1.5:
            zones.append({
                "type": "BODY",
                "timeframe": "W",
                "low": body_low,
                "high": body_high,
                "center": (body_low + body_high) / 2,
                "month": week_label,
            })
        else:
            zones.append({
                "type": "BODY_EDGE",
                "timeframe": "W",
                "low": body_low - thickness * 0.5,
                "high": body_low + thickness * 0.5,
                "center": body_low,
                "month": week_label,
            })
            zones.append({
                "type": "BODY_EDGE",
                "timeframe": "W",
                "low": body_high - thickness * 0.5,
                "high": body_high + thickness * 0.5,
                "center": body_high,
                "month": week_label,
            })

        if h > body_high + thickness:
            zones.append({
                "type": "WICK_HIGH",
                "timeframe": "W",
                "low": h - thickness,
                "high": h + thickness,
                "center": h,
                "month": week_label,
            })
        if l < body_low - thickness:
            zones.append({
                "type": "WICK_LOW",
                "timeframe": "W",
                "low": l - thickness,
                "high": l + thickness,
                "center": l,
                "month": week_label,
            })

    return zones


# ---------------------------------------------------------------------------
# C) Cluster / merge zones
# ---------------------------------------------------------------------------

def cluster_zones(
    raw_zones: list[dict],
    merge_threshold: float | None = None,
    monthly_atr: float | None = None,
) -> list[dict]:
    """Merge overlapping or nearby zones.

    merge_threshold defaults to 15% of monthly ATR — zones closer than this
    get merged.  Target: 5-12 final zones.
    """
    if not raw_zones:
        return []

    if merge_threshold is None:
        atr_val = monthly_atr or 0.01
        # 4% of monthly ATR — tight enough to keep distinct levels separate
        merge_threshold = atr_val * 0.04

    # Sort by center price
    sorted_zones = sorted(raw_zones, key=lambda z: z["center"])

    clusters: list[dict] = []
    current = {
        "low": sorted_zones[0]["low"],
        "high": sorted_zones[0]["high"],
        "center": sorted_zones[0]["center"],
        "types": {sorted_zones[0]["type"]},
        "months": {sorted_zones[0]["month"]},
        "timeframes": {sorted_zones[0].get("timeframe", "M")},
    }

    for z in sorted_zones[1:]:
        if z["low"] <= current["high"] + merge_threshold:
            current["low"] = min(current["low"], z["low"])
            current["high"] = max(current["high"], z["high"])
            current["center"] = (current["low"] + current["high"]) / 2
            current["types"].add(z["type"])
            current["months"].add(z["month"])
            current["timeframes"].add(z.get("timeframe", "M"))
        else:
            clusters.append(current)
            current = {
                "low": z["low"],
                "high": z["high"],
                "center": z["center"],
                "types": {z["type"]},
                "months": {z["month"]},
                "timeframes": {z.get("timeframe", "M")},
            }
    clusters.append(current)

    result: list[dict] = []
    for i, c in enumerate(clusters):
        types = c["types"]
        if len(types) > 1:
            zone_type = "MIXED"
        else:
            zone_type = next(iter(types))
        # Priority: M > W (monthly zones rank higher)
        tfs = c.get("timeframes", {"M"})
        top_tf = "M" if "M" in tfs else "W"
        result.append({
            "zone_id": i,
            "zone_type": zone_type,
            "low": round(c["low"], 8),
            "high": round(c["high"], 8),
            "center": round(c["center"], 8),
            "width": round(c["high"] - c["low"], 8),
            "strength": len(c["months"]),
            "months_included": sorted(c["months"]),
            "types_merged": sorted(c["types"]),
            "timeframe": top_tf,
            "timeframes": sorted(tfs),
        })

    return result


# ---------------------------------------------------------------------------
# D) Price → zone context
# ---------------------------------------------------------------------------

def zone_proximity(
    price: float,
    zones: list[dict],
    bot_atr: float | None = None,
) -> dict:
    """Compute proximity of current price to the nearest zones.

    Returns zone_context dict with nearest zone, distance, inside flag,
    and top 3 closest zones.
    """
    if not zones or price <= 0:
        return {
            "nearest": None,
            "inside_any_zone": False,
            "zones_top3": [],
        }

    scored: list[dict] = []
    for z in zones:
        inside = z["low"] <= price <= z["high"]
        if inside:
            dist_abs = 0.0
            position = "INSIDE"
            zone_side = "UPPER" if (price - z["low"]) > (z["high"] - price) else "LOWER"
        elif price > z["high"]:
            dist_abs = price - z["high"]
            position = "ABOVE"
            zone_side = None
        else:
            dist_abs = z["low"] - price
            position = "BELOW"
            zone_side = None

        dist_pct = (dist_abs / price * 100) if price > 0 else 0.0
        dist_norm = (dist_abs / bot_atr) if bot_atr and bot_atr > 0 else None

        scored.append({
            **z,
            "inside": inside,
            "distance_abs": round(dist_abs, 8),
            "distance_pct": round(dist_pct, 4),
            "distance_norm_atr": round(dist_norm, 3) if dist_norm is not None else None,
            "position": position,
            "zone_side": zone_side,
        })

    scored.sort(key=lambda s: s["distance_abs"])
    nearest = scored[0] if scored else None
    inside_any = any(s["inside"] for s in scored)

    # Macro bias from nearest zone interaction
    macro_bias = "neutral"
    if nearest and nearest.get("inside"):
        zt = nearest.get("zone_type", "")
        types_merged = nearest.get("types_merged") or [zt]
        if "WICK_HIGH" in types_merged:
            macro_bias = "short_bias"  # liquidity rail above
        elif "WICK_LOW" in types_merged:
            macro_bias = "long_bias"   # liquidity rail below
        # Body zones = neutral (mean-revert territory)

    return {
        "nearest": nearest,
        "inside_any_zone": inside_any,
        "zones_top3": scored[:3],
        "macro_bias": macro_bias,
    }


# ---------------------------------------------------------------------------
# E) 7-day microstructure alignment → readiness labels
# ---------------------------------------------------------------------------

def microstructure_readiness(
    price: float,
    zone_context: dict,
    df_15m: pd.DataFrame,
    expansion_state: dict | None = None,
) -> dict:
    """Combine zone proximity with 7-day microstructure for readiness labels.

    Returns dict with readiness label, micro tags, and reasoning.
    """
    result: dict[str, Any] = {
        "label": None,
        "micro": {},
        "reasons": [],
    }

    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return result

    # 7-day window (~672 15m candles)
    bars_7d = min(672, len(df_15m))
    recent = df_15m.tail(bars_7d)

    # Microstructure tags
    recent_high = float(recent["high"].max())
    recent_low = float(recent["low"].min())

    rsi_series = calc_rsi(recent["close"], 14)
    rsi_now = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

    ema_21 = calc_ema(recent["close"], 21)
    ema_slope = float(ema_21.diff().tail(4).mean()) if len(ema_21) > 4 else 0.0

    # Use existing vol state if available
    vol_phase = "UNKNOWN"
    if expansion_state and isinstance(expansion_state, dict):
        vol_phase = expansion_state.get("phase", "UNKNOWN")

    compression = vol_phase == "COMPRESSION"
    expanding = vol_phase in ("IGNITION", "EXPANSION")

    momentum_tag = "BULLISH" if rsi_now > 55 else ("BEARISH" if rsi_now < 45 else "NEUTRAL")
    trend_tag = "UP" if ema_slope > 0 else ("DOWN" if ema_slope < 0 else "FLAT")

    micro = {
        "recent_range_high": round(recent_high, 8),
        "recent_range_low": round(recent_low, 8),
        "rsi": round(rsi_now, 2),
        "ema_slope": round(ema_slope, 8),
        "momentum": momentum_tag,
        "trend": trend_tag,
        "vol_phase": vol_phase,
        "compression": compression,
        "expanding": expanding,
    }
    result["micro"] = micro

    # Readiness logic — combine zone proximity with micro signals
    nearest = zone_context.get("nearest")
    if not nearest:
        return result

    zone_type = nearest.get("zone_type", "")
    position = nearest.get("position", "")
    dist_norm = nearest.get("distance_norm_atr")
    inside = nearest.get("inside", False)

    # "Near" = within 2 ATR of zone edge
    near_zone = inside or (dist_norm is not None and dist_norm <= 2.0)
    reasons: list[str] = []

    if near_zone and zone_type in ("WICK_HIGH", "MIXED") and position in ("INSIDE", "BELOW"):
        # Near a wick-high zone — bearish reversal watch
        if momentum_tag == "BEARISH" or (rsi_now > 65 and ema_slope < 0):
            result["label"] = "SHORT_BIAS_WATCH"
            reasons.append("near_wick_high_zone")
            if momentum_tag == "BEARISH":
                reasons.append("bearish_momentum")
            if rsi_now > 65:
                reasons.append("rsi_overbought_fading")

    if near_zone and zone_type in ("WICK_LOW", "MIXED") and position in ("INSIDE", "ABOVE"):
        # Near a wick-low zone — bullish reversal watch
        if momentum_tag == "BULLISH" or (rsi_now < 35 and ema_slope > 0):
            result["label"] = "LONG_BIAS_WATCH"
            reasons.append("near_wick_low_zone")
            if momentum_tag == "BULLISH":
                reasons.append("bullish_momentum")
            if rsi_now < 35:
                reasons.append("rsi_oversold_bouncing")

    if inside and zone_type in ("BODY", "BODY_EDGE", "MIXED") and expanding:
        # Inside a body zone with expansion — rotation or continuation
        result["label"] = "ROTATION_OR_CONTINUATION_WATCH"
        reasons.append("inside_body_zone")
        reasons.append("vol_expanding")
        if trend_tag == "UP":
            reasons.append("uptrend_bias")
        elif trend_tag == "DOWN":
            reasons.append("downtrend_bias")

    # Zone approach watch — price heading toward a zone
    if not inside and near_zone and not result["label"]:
        if position == "BELOW" and trend_tag == "UP":
            result["label"] = "APPROACHING_ZONE_FROM_BELOW"
            reasons.append(f"heading_toward_{zone_type.lower()}")
        elif position == "ABOVE" and trend_tag == "DOWN":
            result["label"] = "APPROACHING_ZONE_FROM_ABOVE"
            reasons.append(f"heading_toward_{zone_type.lower()}")

    # --- 20-candle micro precision: zone interaction flags ---
    micro_flags: dict[str, bool] = {}
    if nearest and len(df_15m) >= 20:
        z_lo = float(nearest.get("low", 0))
        z_hi = float(nearest.get("high", 0))
        last_20 = df_15m.tail(20)

        rej_up = False    # high enters zone from below, close stays below
        rej_down = False  # low enters zone from above, close stays above
        sweep_past = False  # wick beyond zone edge, close back inside
        bo_above = False  # strong body close above zone
        bo_below = False  # strong body close below zone

        for _i in range(len(last_20)):
            _c = last_20.iloc[_i]
            ch = float(_c["high"])
            cl = float(_c["low"])
            cc = float(_c["close"])
            co = float(_c["open"])
            _body = abs(cc - co)
            _rng = ch - cl
            _br = _body / _rng if _rng > 0 else 0

            # Rejection up: wick pokes into zone from below, close rejected
            if ch >= z_lo and cc < z_lo:
                rej_up = True
            # Rejection down: wick pokes into zone from above, close rejected
            if cl <= z_hi and cc > z_hi:
                rej_down = True
            # Sweep past: wick beyond zone edge, close settles back inside zone
            if (ch > z_hi and z_lo <= cc <= z_hi) or (cl < z_lo and z_lo <= cc <= z_hi):
                sweep_past = True
            # Breakout: close beyond zone with strong body ratio
            if cc > z_hi and _br > 0.6:
                bo_above = True
            if cc < z_lo and _br > 0.6:
                bo_below = True

        # Retest: previously broke out, now price returned near zone edge
        cur = float(df_15m["close"].iloc[-1])
        retest = False
        if bo_above and cur > 0 and abs(cur - z_hi) / cur < 0.005:
            retest = True
        if bo_below and cur > 0 and abs(cur - z_lo) / cur < 0.005:
            retest = True

        micro_flags = {
            "rejection_up": rej_up,
            "rejection_down": rej_down,
            "sweep_past": sweep_past,
            "retest": retest,
            "breakout_above": bo_above,
            "breakout_below": bo_below,
        }

        # Upgrade readiness labels from precision flags
        if rej_up and zone_type in ("WICK_HIGH", "MIXED"):
            result["label"] = "SHORT_TRIGGER_READY"
            reasons.append("rejection_at_wick_high")
        elif rej_down and zone_type in ("WICK_LOW", "MIXED"):
            result["label"] = "LONG_TRIGGER_READY"
            reasons.append("rejection_at_wick_low")
        elif sweep_past and not bo_above and not bo_below:
            if not result["label"] or result["label"].endswith("_WATCH"):
                result["label"] = "SWEEP_REVERSAL_WATCH"
                reasons.append("sweep_past_zone_reclaimed")

    result["micro_flags"] = micro_flags
    result["reasons"] = reasons
    return result


# ---------------------------------------------------------------------------
# Public API: full zone context for bot + dashboard
# ---------------------------------------------------------------------------

def compute_zone_context(
    price: float,
    df_15m: pd.DataFrame,
    *,
    product_id: str = "XLM-USD",
    cache_dir: Path | None = None,
    bot_atr: float | None = None,
    expansion_state: dict | None = None,
) -> dict:
    """One-call entry point: loads monthly + weekly data, builds zones, computes
    proximity and readiness.

    Returns a dict safe for JSON serialization in the decision payload.
    """
    result: dict[str, Any] = {
        "asof": datetime.now(timezone.utc).isoformat(),
        "price": price,
        "nearest": None,
        "inside_any_zone": False,
        "zones_top3": [],
        "macro_bias": "neutral",
        "readiness_label": None,
        "readiness_reasons": [],
        "micro": {},
        "micro_flags": {},
        "total_zones": 0,
    }

    try:
        monthly = load_monthly_ohlc(product_id, cache_dir=cache_dir)
        if monthly.empty:
            return result

        m_atr = _monthly_atr(monthly)

        # Build monthly + weekly zones, merge together
        raw_zones = define_monthly_zones(monthly)
        try:
            weekly = load_weekly_ohlc(product_id, cache_dir=cache_dir)
            if not weekly.empty:
                raw_zones.extend(define_weekly_zones(weekly))
        except Exception:
            pass

        zones = cluster_zones(raw_zones, monthly_atr=m_atr)
        result["total_zones"] = len(zones)

        proximity = zone_proximity(price, zones, bot_atr=bot_atr)
        result["nearest"] = proximity.get("nearest")
        result["inside_any_zone"] = proximity.get("inside_any_zone", False)
        result["zones_top3"] = proximity.get("zones_top3", [])
        result["macro_bias"] = proximity.get("macro_bias", "neutral")

        readiness = microstructure_readiness(price, proximity, df_15m, expansion_state)
        result["readiness_label"] = readiness.get("label")
        result["readiness_reasons"] = readiness.get("reasons", [])
        result["micro"] = readiness.get("micro", {})
        result["micro_flags"] = readiness.get("micro_flags", {})

    except Exception:
        pass

    return result
