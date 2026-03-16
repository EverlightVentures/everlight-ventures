from __future__ import annotations

from datetime import datetime, timezone


def _clean(value: object) -> str:
    return str(value or "").strip()


def _slug(value: object) -> str:
    return _clean(value).lower()


def human_label(value: object) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    return raw.replace("_", " ").replace("-", " ").strip().title()


def age_label_minutes(minutes: object) -> str:
    try:
        value = float(minutes)
    except Exception:
        return "Update time unavailable"
    if value < 1:
        return "Updated just now"
    if value < 60:
        return f"Updated {int(round(value))} min ago"
    return f"Updated {value / 60.0:.1f}h ago"


def ts_age_label(ts_value: object) -> str:
    raw = _clean(ts_value)
    if not raw:
        return "Timestamp unavailable"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_sec = max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))
        if age_sec < 60:
            return f"{age_sec}s ago"
        return f"{int(round(age_sec / 60.0))} min ago"
    except Exception:
        return "Timestamp unavailable"


def public_system_state(bot_state: object) -> str:
    mapping = {
        "idle": "Waiting for a valid setup (idle)",
        "flat": "Flat and waiting (no position)",
        "open_position": "Managing an open trade (in position)",
        "open": "Managing an open trade (in position)",
        "in_position": "Managing an open trade (in position)",
        "live": "System is running live",
    }
    raw = _slug(bot_state)
    return mapping.get(raw, human_label(bot_state) or "Unknown")


def public_setup_state(entry_signal: object, gates_pass: object | None = None) -> str:
    raw = _slug(entry_signal)
    if not raw:
        if gates_pass is False:
            return "Setup blocked by safeguards"
        return "No clean trade setup yet"
    mapping = {
        "htf_breakout_continuation": "Breakout follow-through setup",
        "breakout_probe_reclaim": "Bounce holding near breakout",
        "early_reversal_attempt": "Early bounce / reversal attempt",
        "bullish_confirmation": "Bullish follow-through confirmed",
        "breakout_test": "Breakout test in progress",
        "rejection_risk": "Breakout may fail here",
        "ai_executive": "AI review escalation",
    }
    return mapping.get(raw, human_label(entry_signal))


def public_decision_label(reason: object) -> str:
    mapping = {
        "entry_blocked_no_signal": "Price moved, but no clean setup fired",
        "entry_blocked_guardrails": "Safeguards blocked the trade",
        "entry_blocked": "Trade idea was blocked by safeguards",
        "manage_open_position": "Open trade is being managed",
        "monitor_only": "Watching only, no trade action",
        "hold_position": "Holding the current position",
        "flat_wait": "Waiting for better structure",
    }
    raw = _slug(reason)
    return mapping.get(raw, human_label(reason) or "No recent decision note")


def public_market_climate(pulse_regime: object, pulse_health: object | None = None) -> str:
    mapping = {
        "danger": "Risk is elevated (danger regime)",
        "balanced": "Conditions look balanced",
        "neutral": "Conditions look neutral",
        "risk_on": "Momentum is supportive (risk-on)",
        "risk_off": "Momentum is defensive (risk-off)",
    }
    raw = _slug(pulse_regime)
    label = mapping.get(raw, human_label(pulse_regime) or "Unknown")
    if pulse_health in (None, ""):
        return label
    return f"{label} | Health {pulse_health}"


def public_tick_status(tick_health: object, tick_age_sec: object | None = None) -> str:
    mapping = {
        "healthy": "Price feed is current",
        "live": "Price feed is current",
        "stale": "Price feed is lagging (stale tick)",
        "dead": "Price feed is down (dead tick)",
    }
    raw = _slug(tick_health)
    label = mapping.get(raw, human_label(tick_health) or "Feed status unknown")
    try:
        age = float(tick_age_sec)
    except Exception:
        age = None
    if age is None:
        return label
    if age < 1:
        return f"{label} | 0s old"
    if age < 120:
        return f"{label} | {int(round(age))}s old"
    return f"{label} | {int(round(age / 60.0))} min old"


def public_data_status(data_quality_status: object) -> str:
    mapping = {
        "healthy": "Healthy live feed",
        "degraded": "Feed needs caution",
        "unknown": "Feed status unknown",
    }
    raw = _slug(data_quality_status)
    return mapping.get(raw, human_label(data_quality_status) or "Feed status unknown")


def public_pressure_note(
    liquidation_bias: object,
    orderbook_depth_bias: object,
    funding_bias: object,
) -> str:
    liq = _slug(liquidation_bias)
    depth = _slug(orderbook_depth_bias)
    funding = _slug(funding_bias)

    if "short" in liq:
        return "Sellers are getting forced out (short liquidations / squeeze pressure)."
    if "long" in liq:
        return "Late buyers are getting forced out (long liquidations)."
    if "bid" in depth or "buy" in depth:
        return "Buyers are leaning on the order book (bid-side support)."
    if "ask" in depth or "sell" in depth:
        return "Sellers are leaning on the order book (ask-side pressure)."
    if "negative" in funding or "short" in funding:
        return "A lot of traders are still leaning short (negative funding)."
    if "positive" in funding or "long" in funding:
        return "A lot of traders are still leaning long (positive funding)."
    return "Positioning looks mixed right now."


def public_status_blurb(payload: dict) -> str:
    quality = _slug(payload.get("data_quality_status"))
    if quality == "healthy":
        return "Live feed looks healthy and current."

    reasons: list[str] = []
    if _slug(payload.get("pulse_regime")) == "danger":
        reasons.append("risk is elevated")
    tick = _slug(payload.get("tick_health"))
    if tick == "stale":
        reasons.append("the price feed is lagging")
    elif tick == "dead":
        reasons.append("the price feed is down")

    try:
        snapshot_age = float(payload.get("snapshot_age_min") or 0)
    except Exception:
        snapshot_age = 0
    if snapshot_age >= 60:
        reasons.append("the core snapshot is old")

    try:
        brief_age = float(payload.get("brief_age_min") or 0)
    except Exception:
        brief_age = 0
    if brief_age >= 45:
        reasons.append("the research snapshot is old")

    if not reasons:
        return "Some telemetry is stale or degraded. Treat this page as informational until the feed recovers."
    if len(reasons) == 1:
        return f"Some telemetry needs caution because {reasons[0]}."
    return f"Some telemetry needs caution because {', '.join(reasons[:-1])}, and {reasons[-1]}."


def build_public_watchtower_fields(payload: dict) -> dict:
    return {
        "public_system_state": public_system_state(payload.get("bot_state")),
        "public_setup_state": public_setup_state(payload.get("entry_signal"), payload.get("gates_pass")),
        "public_market_climate": public_market_climate(
            payload.get("pulse_regime"),
            payload.get("pulse_health"),
        ),
        "public_tick_status": public_tick_status(
            payload.get("tick_health"),
            payload.get("tick_age_sec"),
        ),
        "public_data_status": public_data_status(payload.get("data_quality_status")),
        "public_decision_label": public_decision_label(payload.get("decision_reason")),
        "public_pressure_note": public_pressure_note(
            payload.get("liquidation_bias"),
            payload.get("orderbook_depth_bias"),
            payload.get("cross_venue_funding_bias"),
        ),
        "public_status_blurb": public_status_blurb(payload),
        "public_decision_age_label": age_label_minutes(payload.get("decision_age_min")),
        "public_brief_age_label": age_label_minutes(payload.get("brief_age_min")),
        "public_price_age_label": ts_age_label(payload.get("price_ts") or payload.get("generated_at")),
    }
