"""
inventory_intel.py -- Position and inventory intelligence.

Think like a market maker about your book. How hot is the position?
How is the session going? What does the basis tell us?
"""

from datetime import datetime, timezone


def position_heat(state, config=None):
    """
    Classify how 'hot' the current position is based on age and movement.

    Args:
        state: dict with entry_time (datetime or ISO str), direction, pnl_usd_live,
               bars_since_entry, max_unrealized_usd, atr (current ATR value),
               entry_price, mark_price.
        config: optional dict overrides.

    Returns:
        dict with heat, age_minutes, move_atr, recommendation, exit_urgency
    """
    if not state or not isinstance(state, dict):
        return {
            "heat": "cold",
            "age_minutes": 0.0,
            "move_atr": 0.0,
            "recommendation": "No position data -- treat as new.",
            "exit_urgency": 0.0,
        }

    now = datetime.now(timezone.utc)

    # Parse entry time
    entry_time = state.get("entry_time")
    if entry_time is None:
        age_minutes = 0.0
    elif isinstance(entry_time, str):
        try:
            et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            if et.tzinfo is None:
                et = et.replace(tzinfo=timezone.utc)
            age_minutes = (now - et).total_seconds() / 60.0
        except (ValueError, TypeError):
            age_minutes = 0.0
    elif isinstance(entry_time, datetime):
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
        age_minutes = (now - entry_time).total_seconds() / 60.0
    else:
        age_minutes = 0.0

    # Clamp negative ages (clock skew)
    age_minutes = max(age_minutes, 0.0)

    # Compute move in ATR units
    atr = state.get("atr") or 0.0
    entry_price = state.get("entry_price") or 0.0
    mark_price = state.get("mark_price") or entry_price
    price_move = abs(mark_price - entry_price) if entry_price > 0 else 0.0

    if atr > 0:
        move_atr = price_move / atr
    else:
        move_atr = 0.0

    # Classify heat
    if age_minutes > 240 and move_atr < 1.0:
        heat = "overcooked"
        recommendation = (
            f"Position is {age_minutes:.0f} min old with only {move_atr:.1f} ATR move. "
            "Thesis may be wrong -- consider closing to free up capital."
        )
        exit_urgency = 0.8

    elif age_minutes > 60 or move_atr > 2.0:
        heat = "hot"
        if move_atr > 2.0:
            recommendation = (
                f"Big move ({move_atr:.1f} ATR). Tighten trailing stop. "
                "Lock in gains before reversion."
            )
            exit_urgency = 0.6
        else:
            recommendation = (
                f"Position aging ({age_minutes:.0f} min). Active management -- "
                "tighten stops and watch for momentum fade."
            )
            exit_urgency = 0.5

    elif age_minutes >= 15:
        heat = "warm"
        recommendation = (
            f"Position developing ({age_minutes:.0f} min, {move_atr:.1f} ATR). "
            "Normal management -- let thesis play out."
        )
        exit_urgency = 0.2

    else:
        heat = "cold"
        recommendation = (
            f"Fresh position ({age_minutes:.0f} min). Still developing -- "
            "give it room unless invalidated."
        )
        exit_urgency = 0.1

    return {
        "heat": heat,
        "age_minutes": round(age_minutes, 1),
        "move_atr": round(move_atr, 2),
        "recommendation": recommendation,
        "exit_urgency": round(exit_urgency, 2),
    }


def session_pnl_aggression(state, config=None):
    """
    Grade the session's performance and adjust position sizing aggression.

    When winning big, press the edge. When bleeding, go defensive.

    Args:
        state: dict with pnl_today_usd, equity_start_usd, trades_today,
               wins_today, losses_today.
        config: optional overrides.

    Returns:
        dict with grade, pnl_today, pnl_pct, size_mult, trades, win_rate
    """
    if not state or not isinstance(state, dict):
        return {
            "grade": "flat",
            "pnl_today": 0.0,
            "pnl_pct": 0.0,
            "size_mult": 0.85,
            "trades": 0,
            "win_rate": 0.0,
        }

    pnl_today = float(state.get("pnl_today_usd") or 0.0)
    equity_start = float(state.get("equity_start_usd") or 0.0)
    trades = int(state.get("trades_today") or 0)
    wins = int(state.get("wins_today") or 0)
    losses = int(state.get("losses_today") or 0)

    # Compute PnL percentage
    if equity_start > 0:
        pnl_pct = (pnl_today / equity_start) * 100.0
    else:
        pnl_pct = 0.0

    # Win rate
    if trades > 0:
        win_rate = (wins / trades) * 100.0
    else:
        win_rate = 0.0

    # Grade the session
    if pnl_pct < -3.0:
        grade = "crisis"
        size_mult = 0.40
    elif pnl_pct < -1.0:
        grade = "bleeding"
        size_mult = 0.65
    elif pnl_pct < 1.0:
        grade = "flat"
        size_mult = 0.85
    elif pnl_pct < 3.0:
        grade = "solid"
        size_mult = 1.0
    else:
        grade = "crushing_it"
        size_mult = 1.25

    return {
        "grade": grade,
        "pnl_today": round(pnl_today, 2),
        "pnl_pct": round(pnl_pct, 2),
        "size_mult": size_mult,
        "trades": trades,
        "win_rate": round(win_rate, 1),
    }


def basis_monitor(spot_price, perp_price, expiry_days_remaining=None):
    """
    Monitor the basis (premium/discount) between spot and perp.

    A large positive basis means the perp is expensive relative to spot --
    bias short. A large negative basis means cheap perp -- bias long.

    Args:
        spot_price: Current spot price.
        perp_price: Current perpetual/futures mark price.
        expiry_days_remaining: Days until contract expiry (optional, for annualizing).

    Returns:
        dict with basis_pct, annualized_pct, bias, score_adj, reasoning
    """
    if spot_price is None or perp_price is None:
        return {
            "basis_pct": 0.0,
            "annualized_pct": 0.0,
            "bias": "neutral",
            "score_adj": 0,
            "reasoning": "Missing price data -- cannot compute basis.",
        }

    spot_price = float(spot_price)
    perp_price = float(perp_price)

    if spot_price <= 0:
        return {
            "basis_pct": 0.0,
            "annualized_pct": 0.0,
            "bias": "neutral",
            "score_adj": 0,
            "reasoning": "Spot price is zero or negative -- invalid.",
        }

    # Basis = (perp - spot) / spot * 100
    basis_pct = ((perp_price - spot_price) / spot_price) * 100.0

    # Annualize if expiry is known
    annualized_pct = 0.0
    if expiry_days_remaining is not None and expiry_days_remaining > 0:
        annualized_pct = basis_pct * (365.0 / expiry_days_remaining)

    # Determine bias and score adjustment
    if basis_pct > 0.5:
        bias = "short"
        score_adj = 5
        reasoning = (
            f"Perp trading at +{basis_pct:.3f}% premium to spot. "
            "Expensive perp -- short bias."
        )
    elif basis_pct < -0.5:
        bias = "long"
        score_adj = 5
        reasoning = (
            f"Perp trading at {basis_pct:.3f}% discount to spot. "
            "Cheap perp -- long bias."
        )
    else:
        bias = "neutral"
        score_adj = 0
        reasoning = (
            f"Basis at {basis_pct:.3f}% -- within normal range, no edge."
        )

    if annualized_pct != 0.0:
        reasoning += f" Annualized: {annualized_pct:.1f}%."

    return {
        "basis_pct": round(basis_pct, 4),
        "annualized_pct": round(annualized_pct, 2),
        "bias": bias,
        "score_adj": score_adj,
        "reasoning": reasoning,
    }
