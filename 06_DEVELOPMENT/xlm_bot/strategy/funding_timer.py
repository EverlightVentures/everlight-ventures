"""
funding_timer.py -- Funding rate exploitation engine for Coinbase CDE perps.

Coinbase CDE perps have 8-hour funding intervals at 00:00, 08:00, 16:00 UTC.
Positions that are open at the snapshot pay/receive funding based on the rate.
This module times entries around funding to capture or avoid funding costs.
"""

from datetime import datetime, timezone, timedelta


FUNDING_SNAPSHOTS_UTC = [0, 8, 16]  # hours
XLM_PER_CONTRACT = 5000
XLM_PRICE_APPROX = 0.17
NOTIONAL_PER_CONTRACT = XLM_PER_CONTRACT * XLM_PRICE_APPROX  # ~$850

PRE_FUNDING_MINUTES = 60
POST_FUNDING_MINUTES = 30

EXTREME_POSITIVE_THRESHOLD = 0.03  # percent per 8hr
EXTREME_NEGATIVE_THRESHOLD = -0.03


def get_next_funding_snapshot(now_utc=None):
    """
    Determine the next funding snapshot time and current phase.

    Args:
        now_utc: datetime in UTC. If None, uses current time.

    Returns:
        dict with next_snapshot_utc, minutes_until, hours_until, phase
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    # Ensure timezone aware
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    current_hour = now_utc.hour
    current_date = now_utc.date()

    # Find next snapshot hour
    next_snapshot_hour = None
    next_date = current_date

    for h in FUNDING_SNAPSHOTS_UTC:
        candidate = datetime(
            current_date.year, current_date.month, current_date.day,
            h, 0, 0, tzinfo=timezone.utc
        )
        if candidate > now_utc:
            next_snapshot_hour = h
            break

    if next_snapshot_hour is None:
        # Next snapshot is 00:00 tomorrow
        next_date = current_date + timedelta(days=1)
        next_snapshot_hour = 0

    next_snapshot = datetime(
        next_date.year, next_date.month, next_date.day,
        next_snapshot_hour, 0, 0, tzinfo=timezone.utc
    )

    delta = next_snapshot - now_utc
    minutes_until = delta.total_seconds() / 60.0
    hours_until = minutes_until / 60.0

    # Determine phase
    if minutes_until <= PRE_FUNDING_MINUTES:
        phase = "pre_funding"
    else:
        # Check if we are within POST_FUNDING_MINUTES after the PREVIOUS snapshot
        prev_snapshot = _get_previous_snapshot(now_utc)
        if prev_snapshot is not None:
            minutes_since = (now_utc - prev_snapshot).total_seconds() / 60.0
            if minutes_since <= POST_FUNDING_MINUTES:
                phase = "post_funding"
            else:
                phase = "neutral"
        else:
            phase = "neutral"

    return {
        "next_snapshot_utc": next_snapshot,
        "minutes_until": int(minutes_until),
        "hours_until": round(hours_until, 2),
        "phase": phase,
    }


def _get_previous_snapshot(now_utc):
    """Get the most recent funding snapshot before now_utc."""
    current_date = now_utc.date()

    candidates = []
    for h in FUNDING_SNAPSHOTS_UTC:
        candidate = datetime(
            current_date.year, current_date.month, current_date.day,
            h, 0, 0, tzinfo=timezone.utc
        )
        candidates.append(candidate)

    # Also include last snapshot from yesterday (16:00)
    yesterday = current_date - timedelta(days=1)
    candidates.append(datetime(
        yesterday.year, yesterday.month, yesterday.day,
        FUNDING_SNAPSHOTS_UTC[-1], 0, 0, tzinfo=timezone.utc
    ))

    past = [c for c in candidates if c <= now_utc]
    if not past:
        return None
    return max(past)


def funding_direction_bias(funding_rate_pct, phase, direction):
    """
    Compute directional bias based on funding rate and timing phase.

    Before funding snapshots, positions that will pay funding tend to close,
    creating predictable price pressure. After the snapshot, they re-open.

    Args:
        funding_rate_pct: Current funding rate in percent (positive = longs pay).
        phase: "pre_funding", "post_funding", or "neutral".
        direction: "long" or "short" -- the direction being considered.

    Returns:
        dict with bias, score_adj, phase, reasoning
    """
    if funding_rate_pct is None or phase is None or direction is None:
        return {
            "bias": "neutral",
            "score_adj": 0,
            "phase": phase or "unknown",
            "reasoning": "Missing inputs -- no funding bias applied.",
        }

    direction = direction.lower()
    score_adj = 0
    bias = "neutral"
    reasoning = ""

    # Near-zero funding -- no meaningful pressure
    if abs(funding_rate_pct) < 0.005:
        return {
            "bias": "neutral",
            "score_adj": 0,
            "phase": phase,
            "reasoning": f"Funding rate {funding_rate_pct:.4f}% near zero -- no directional pressure.",
        }

    if phase == "pre_funding":
        if funding_rate_pct > 0:
            # Longs pay at snapshot -- longs close before -> price drops
            bias = "short"
            reasoning = (
                f"Pre-funding: longs pay {funding_rate_pct:.4f}%. "
                "Longs closing before snapshot -- short pressure expected."
            )
            if direction == "short":
                score_adj = 5
            elif direction == "long":
                score_adj = -5
        else:
            # Shorts pay at snapshot -- shorts close before -> price rises
            bias = "long"
            reasoning = (
                f"Pre-funding: shorts pay {abs(funding_rate_pct):.4f}%. "
                "Shorts closing before snapshot -- long pressure expected."
            )
            if direction == "long":
                score_adj = 5
            elif direction == "short":
                score_adj = -5

    elif phase == "post_funding":
        # After paying, positions re-open -- reverse of pre-funding flow
        if funding_rate_pct > 0:
            # Longs paid, now re-entering -> price recovers
            bias = "long"
            reasoning = (
                f"Post-funding: longs paid {funding_rate_pct:.4f}% and are re-entering. "
                "Expect recovery bounce."
            )
            if direction == "long":
                score_adj = 3
            elif direction == "short":
                score_adj = -3
        else:
            bias = "short"
            reasoning = (
                f"Post-funding: shorts paid {abs(funding_rate_pct):.4f}% and are re-entering. "
                "Expect downward pressure."
            )
            if direction == "short":
                score_adj = 3
            elif direction == "long":
                score_adj = -3

    else:
        reasoning = f"Neutral phase -- funding rate {funding_rate_pct:.4f}% noted but no timing edge."

    return {
        "bias": bias,
        "score_adj": score_adj,
        "phase": phase,
        "reasoning": reasoning,
    }


def funding_accumulation_value(funding_rate_pct, direction, hold_hours=8):
    """
    Compute how much funding a position earns or pays over a hold period.

    If you're on the earning side of funding, it's free money while you hold.
    If you're paying, it eats into profits.

    Args:
        funding_rate_pct: Funding rate in percent per 8hr period.
        direction: "long" or "short".
        hold_hours: Expected hold duration in hours.

    Returns:
        dict with earning_funding, funding_value_pct, funding_value_usd_per_contract, recommendation
    """
    if funding_rate_pct is None or direction is None:
        return {
            "earning_funding": False,
            "funding_value_pct": 0.0,
            "funding_value_usd_per_contract": 0.0,
            "recommendation": "neutral",
        }

    direction = direction.lower()
    if hold_hours is None or hold_hours <= 0:
        hold_hours = 8

    # Positive rate = longs pay shorts. Negative = shorts pay longs.
    if funding_rate_pct > 0:
        earning = direction == "short"
    elif funding_rate_pct < 0:
        earning = direction == "long"
    else:
        earning = False

    periods = hold_hours / 8.0
    raw_value = abs(funding_rate_pct) * periods

    if earning:
        funding_value_pct = raw_value
    else:
        funding_value_pct = -raw_value

    funding_value_usd = (funding_value_pct / 100.0) * NOTIONAL_PER_CONTRACT

    # Recommendation
    if abs(funding_rate_pct) < 0.005:
        recommendation = "neutral"
    elif earning:
        recommendation = "favorable"
    else:
        recommendation = "costly"

    return {
        "earning_funding": earning,
        "funding_value_pct": round(funding_value_pct, 6),
        "funding_value_usd_per_contract": round(funding_value_usd, 4),
        "recommendation": recommendation,
    }


def extreme_funding_signal(funding_rate_pct):
    """
    Detect extreme funding rates that signal crowded positioning.

    Extreme positive = too many longs, mean reversion short opportunity.
    Extreme negative = too many shorts, mean reversion long opportunity.

    Args:
        funding_rate_pct: Funding rate in percent per 8hr period.

    Returns:
        dict with extreme, direction_bias, score_adj, reasoning
    """
    if funding_rate_pct is None:
        return {
            "extreme": False,
            "direction_bias": "neutral",
            "score_adj": 0,
            "reasoning": "No funding rate provided.",
        }

    extreme = False
    direction_bias = "neutral"
    score_adj = 0
    reasoning = ""

    if funding_rate_pct > EXTREME_POSITIVE_THRESHOLD:
        extreme = True
        direction_bias = "short"
        # Scale score_adj from 0-8 based on how extreme
        # At 0.03% = +4, at 0.06%+ = +8
        intensity = min((funding_rate_pct - EXTREME_POSITIVE_THRESHOLD) / EXTREME_POSITIVE_THRESHOLD, 1.0)
        score_adj = 4 + int(intensity * 4)
        reasoning = (
            f"Extreme positive funding {funding_rate_pct:.4f}% -- "
            f"market is long-crowded. Mean reversion short bias (+{score_adj})."
        )

    elif funding_rate_pct < EXTREME_NEGATIVE_THRESHOLD:
        extreme = True
        direction_bias = "long"
        intensity = min((abs(funding_rate_pct) - abs(EXTREME_NEGATIVE_THRESHOLD)) / abs(EXTREME_NEGATIVE_THRESHOLD), 1.0)
        score_adj = 4 + int(intensity * 4)
        reasoning = (
            f"Extreme negative funding {funding_rate_pct:.4f}% -- "
            f"market is short-crowded. Mean reversion long bias (+{score_adj})."
        )

    else:
        reasoning = f"Funding rate {funding_rate_pct:.4f}% within normal range -- no extreme signal."

    return {
        "extreme": extreme,
        "direction_bias": direction_bias,
        "score_adj": score_adj,
        "reasoning": reasoning,
    }
