"""Order flow intelligence -- market maker-level signals from book + trade data.

Goes deeper than orderbook_context.py by detecting weighted imbalances,
liquidity vacuums, aggressive taker flow, and spoofing patterns.
All functions are pure, stateless, and safe on empty/None inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Function 1: Deep book imbalance (weighted by proximity to top of book)
# ---------------------------------------------------------------------------

def deep_book_imbalance(
    bids: Optional[List[Tuple[float, float]]],
    asks: Optional[List[Tuple[float, float]]],
) -> Dict[str, Any]:
    """Compute weighted bid/ask volume ratio across all levels.

    Near levels are weighted more heavily (level 1 = 10, level 10 = 1).
    Returns imbalance 0-1, directional bias, and score adjustments.
    """
    empty: Dict[str, Any] = {
        "imbalance": 0.5,
        "bias": "neutral",
        "bid_vol": 0.0,
        "ask_vol": 0.0,
        "score_adj_long": 0,
        "score_adj_short": 0,
        "strength": "none",
    }

    if not bids and not asks:
        return empty

    safe_bids: List[Tuple[float, float]] = bids if bids else []
    safe_asks: List[Tuple[float, float]] = asks if asks else []

    weighted_bid_vol = _weighted_volume(safe_bids)
    weighted_ask_vol = _weighted_volume(safe_asks)

    total = weighted_bid_vol + weighted_ask_vol
    if total <= 0.0:
        return empty

    imbalance = weighted_bid_vol / total

    # Classify bias and score adjustments
    if imbalance > 0.75:
        bias = "bullish"
        strength = "strong"
        adj_long = 8
        adj_short = -5
    elif imbalance > 0.65:
        bias = "bullish"
        strength = "moderate"
        adj_long = 5
        adj_short = -3
    elif imbalance < 0.25:
        bias = "bearish"
        strength = "strong"
        adj_long = -5
        adj_short = 8
    elif imbalance < 0.35:
        bias = "bearish"
        strength = "moderate"
        adj_long = -3
        adj_short = 5
    else:
        bias = "neutral"
        strength = "none"
        adj_long = 0
        adj_short = 0

    return {
        "imbalance": round(imbalance, 4),
        "bias": bias,
        "bid_vol": round(weighted_bid_vol, 4),
        "ask_vol": round(weighted_ask_vol, 4),
        "score_adj_long": adj_long,
        "score_adj_short": adj_short,
        "strength": strength,
    }


def _weighted_volume(levels: List[Tuple[float, float]]) -> float:
    """Sum size * weight for up to 10 levels. Level 1 = weight 10, level 10 = weight 1."""
    total = 0.0
    for i, level in enumerate(levels[:10]):
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue
        price, size = level[0], level[1]
        if price is None or size is None:
            continue
        try:
            s = float(size)
        except (TypeError, ValueError):
            continue
        if s <= 0.0:
            continue
        weight = 10 - i  # level 0 -> weight 10, level 9 -> weight 1
        total += s * weight
    return total


# ---------------------------------------------------------------------------
# Function 2: Liquidity vacuum detector
# ---------------------------------------------------------------------------

def liquidity_vacuum_detector(
    current_depth: Optional[float],
    historical_depths: Optional[List[float]],
    threshold_pct: float = 0.50,
) -> Dict[str, Any]:
    """Detect when market makers pull liquidity (danger signal).

    Compares current total book depth against the rolling average of
    recent depth readings. A sharp drop means MMs have stepped away.
    """
    empty: Dict[str, Any] = {
        "vacuum": False,
        "current_depth": 0.0,
        "avg_depth": 0.0,
        "depth_ratio": 1.0,
        "action": "clear",
        "size_mult": 1.0,
    }

    if current_depth is None or current_depth < 0:
        return empty

    safe_history = [d for d in (historical_depths or []) if d is not None and d > 0]
    if not safe_history:
        return {
            "vacuum": False,
            "current_depth": round(current_depth, 4),
            "avg_depth": 0.0,
            "depth_ratio": 1.0,
            "action": "clear",
            "size_mult": 1.0,
        }

    avg_depth = sum(safe_history) / len(safe_history)
    if avg_depth <= 0.0:
        return empty

    depth_ratio = current_depth / avg_depth
    vacuum = depth_ratio < threshold_pct

    # Classify severity
    if depth_ratio < 0.30:
        action = "block"
        size_mult = 0.0
    elif depth_ratio < 0.50:
        action = "caution"
        size_mult = 0.5
    else:
        action = "clear"
        size_mult = 1.0

    return {
        "vacuum": vacuum,
        "current_depth": round(current_depth, 4),
        "avg_depth": round(avg_depth, 4),
        "depth_ratio": round(depth_ratio, 4),
        "action": action,
        "size_mult": size_mult,
    }


# ---------------------------------------------------------------------------
# Function 3: Aggressive flow detector (taker bursts)
# ---------------------------------------------------------------------------

def aggressive_flow_detector(
    recent_trades: Optional[List[Dict[str, Any]]],
    window_sec: int = 60,
) -> Dict[str, Any]:
    """Detect bursts of aggressive taker orders that signal directional intent.

    Filters trades to the last window_sec seconds, then checks if buy or
    sell volume dominates by 3x or more.
    """
    empty: Dict[str, Any] = {
        "signal": "none",
        "buy_vol": 0.0,
        "sell_vol": 0.0,
        "ratio": 0.0,
        "score_adj_long": 0,
        "score_adj_short": 0,
    }

    if not recent_trades:
        return empty

    now = datetime.now(timezone.utc)
    buy_vol = 0.0
    sell_vol = 0.0

    for trade in recent_trades:
        if not isinstance(trade, dict):
            continue

        # Parse timestamp and filter by window
        trade_time = _parse_time(trade.get("time"))
        if trade_time is not None:
            age_sec = (now - trade_time).total_seconds()
            if age_sec < 0 or age_sec > window_sec:
                continue

        size = _safe_float(trade.get("size"))
        if size is None or size <= 0:
            continue

        side = str(trade.get("side", "")).lower().strip()
        if side == "buy":
            buy_vol += size
        elif side == "sell":
            sell_vol += size

    # Compute ratio (avoid division by zero)
    if buy_vol <= 0 and sell_vol <= 0:
        return empty

    if sell_vol > 0 and buy_vol > 0:
        ratio = max(buy_vol, sell_vol) / min(buy_vol, sell_vol)
    elif buy_vol > 0:
        ratio = float("inf")
    else:
        ratio = float("inf")

    # Classify
    signal = "none"
    adj_long = 0
    adj_short = 0

    if buy_vol > 3.0 * sell_vol and buy_vol > 0:
        signal = "aggressive_buy"
        adj_long = 5
        adj_short = -3
    elif sell_vol > 3.0 * buy_vol and sell_vol > 0:
        signal = "aggressive_sell"
        adj_long = -3
        adj_short = 5

    # Cap ratio for JSON serialization
    display_ratio = min(ratio, 999.0)

    return {
        "signal": signal,
        "buy_vol": round(buy_vol, 4),
        "sell_vol": round(sell_vol, 4),
        "ratio": round(display_ratio, 2),
        "score_adj_long": adj_long,
        "score_adj_short": adj_short,
    }


# ---------------------------------------------------------------------------
# Function 4: Spoof detector (vanishing large orders)
# ---------------------------------------------------------------------------

def spoof_detector(
    book_snapshots: Optional[List[Dict[str, Any]]],
    min_snapshots: int = 3,
) -> Dict[str, Any]:
    """Detect spoofing -- large orders that appear then vanish.

    Compares consecutive snapshots to find orders > 2x average level size
    that were present in snapshot N but gone in snapshot N+1.
    """
    empty: Dict[str, Any] = {
        "detected": False,
        "side": "none",
        "implied_direction": "none",
        "score_adj": 0,
    }

    if not book_snapshots or len(book_snapshots) < min_snapshots:
        return empty

    bid_spoofs = 0
    ask_spoofs = 0

    # Compare consecutive pairs
    for i in range(len(book_snapshots) - 1):
        snap_a = book_snapshots[i]
        snap_b = book_snapshots[i + 1]
        if not isinstance(snap_a, dict) or not isinstance(snap_b, dict):
            continue

        # Check bid side
        bid_spoof = _check_side_spoof(
            levels_a=snap_a.get("bids"),
            levels_b=snap_b.get("bids"),
        )
        if bid_spoof:
            bid_spoofs += 1

        # Check ask side
        ask_spoof = _check_side_spoof(
            levels_a=snap_a.get("asks"),
            levels_b=snap_b.get("asks"),
        )
        if ask_spoof:
            ask_spoofs += 1

    if bid_spoofs == 0 and ask_spoofs == 0:
        return empty

    # Dominant spoof side wins
    if bid_spoofs >= ask_spoofs:
        # Fake buy wall pulled -- real intent is bearish
        return {
            "detected": True,
            "side": "bid",
            "implied_direction": "bearish",
            "score_adj": -3,
        }
    else:
        # Fake sell wall pulled -- real intent is bullish
        return {
            "detected": True,
            "side": "ask",
            "implied_direction": "bullish",
            "score_adj": 3,
        }


def _check_side_spoof(
    levels_a: Any,
    levels_b: Any,
) -> bool:
    """Check if a large order in levels_a vanished in levels_b.

    A large order is defined as > 2x the average level size in levels_a.
    It counts as vanished if no level in levels_b has matching price.
    """
    parsed_a = _parse_levels(levels_a)
    parsed_b = _parse_levels(levels_b)

    if len(parsed_a) < 2:
        return False

    sizes = [s for _, s in parsed_a]
    avg_size = sum(sizes) / len(sizes) if sizes else 0.0
    if avg_size <= 0.0:
        return False

    threshold = avg_size * 2.0
    prices_b = {p for p, _ in parsed_b}

    for price, size in parsed_a:
        if size > threshold and price not in prices_b:
            return True

    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_levels(raw: Any) -> List[Tuple[float, float]]:
    """Parse order book levels from list of (price, size) or [price, size]."""
    out: List[Tuple[float, float]] = []
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            p = _safe_float(entry[0])
            s = _safe_float(entry[1])
            if p is not None and s is not None and p > 0 and s > 0:
                out.append((p, s))
        elif isinstance(entry, dict):
            p = _safe_float(entry.get("price") or entry.get("px"))
            s = _safe_float(entry.get("size") or entry.get("qty"))
            if p is not None and s is not None and p > 0 and s > 0:
                out.append((p, s))
    return out


def _parse_time(value: Any) -> Optional[datetime]:
    """Best-effort ISO timestamp parse."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str):
        return None
    try:
        # Handle common ISO formats
        cleaned = value.strip().rstrip("Z") + "+00:00" if "Z" in str(value) else value.strip()
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    """Convert value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
