"""Trade timing intelligence — close ETAs and next-entry estimates."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd


# ── Helpers ──────────────────────────────────────────────────────────

def _fmt_dur(minutes: float) -> str:
    """Human-readable duration string."""
    if minutes < 1:
        return "< 1m"
    m = int(round(minutes))
    if m < 60:
        return f"{m}m"
    h, r = divmod(m, 60)
    return f"{h}h {r}m" if r else f"{h}h"


# Trade-state multipliers for expected hold time
_STATE_MULT = {
    "DECAY": 0.10,
    "UNDERWATER": 0.50,
    "SECURED": 0.70,
    "EARLY": 1.0,
    "BUILDING": 1.0,
    "EXPANSION": 1.5,
}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _parse_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _bias_matches(label: str | None, direction: str) -> bool:
    text = str(label or "").strip().lower()
    return bool(text and direction in text)


def _describe_regime(regime: str | None, adx: float | None) -> str:
    regime_txt = str(regime or "mixed").replace("_", " ").lower()
    if adx is None:
        return regime_txt
    if adx >= 25:
        return f"{regime_txt} with strong trend pressure"
    if adx >= 20:
        return f"{regime_txt} with building trend pressure"
    return f"{regime_txt} with weak trend pressure"


def _pick_ready_contracts(last_decision: dict[str, Any]) -> int:
    ladder = _parse_dict(last_decision.get("contract_ladder")) or {}
    playbook_cap = int(_safe_float(last_decision.get("margin_playbook_max_new_contracts"), 1) or 1)
    ready_sizes: list[int] = []
    for key, data in ladder.items():
        item = _parse_dict(data) if not isinstance(data, dict) else data
        if not item:
            continue
        try:
            target = int(item.get("target_size") or key)
        except Exception:
            continue
        if target <= max(playbook_cap, 1) and bool(item.get("ready")):
            ready_sizes.append(target)
    return max(ready_sizes) if ready_sizes else 1


def _build_forecast_candidate(
    *,
    direction: str,
    score: int,
    threshold: int,
    play: dict[str, Any] | None,
    last_decision: dict[str, Any],
) -> dict[str, Any]:
    readiness = (score / max(threshold, 1) * 100.0) if threshold > 0 else 0.0
    play_readiness = _safe_float((play or {}).get("readiness_pct"), readiness) or readiness
    trigger_price = _safe_float((play or {}).get("trigger_price"))
    distance_atr = _safe_float((play or {}).get("distance_atr"))
    level_name = str((play or {}).get("level_name") or "trigger zone")
    block_reason = str(last_decision.get(f"{direction}_block_reason") or "").strip()
    htf_readiness = str(last_decision.get("htf_readiness") or "")
    weekly_bias = str(last_decision.get("weekly_research_bias") or "")
    weekly_xlm_bias = str(last_decision.get("weekly_research_xlm_bias") or "")
    weekly_conf = _safe_float(last_decision.get("weekly_research_confidence"), 0.0) or 0.0
    adx = _safe_float(last_decision.get("v4_adx_15m"))
    market_regime = str(last_decision.get("market_regime") or last_decision.get("v4_regime") or "")
    lane_label = str(last_decision.get(f"lane_{direction}_label") or last_decision.get("lane_label") or "").strip()

    weighted = readiness * 0.55 + play_readiness * 0.20
    if _bias_matches(htf_readiness, direction):
        weighted += 18
    if _bias_matches(weekly_xlm_bias, direction):
        weighted += 14 * max(0.35, weekly_conf)
    if _bias_matches(weekly_bias, direction):
        weighted += 8 * max(0.35, weekly_conf)
    if adx is not None:
        if adx >= 25:
            weighted += 8
        elif adx < 18:
            weighted -= 6
    if "compression" in market_regime.lower():
        weighted -= 7
    if block_reason:
        weighted -= 12
    if lane_label:
        weighted += 4

    return {
        "direction": direction,
        "score": score,
        "threshold": threshold,
        "weighted": round(weighted, 2),
        "readiness_pct": round(max(readiness, play_readiness), 1),
        "trigger_price": trigger_price,
        "distance_atr": distance_atr,
        "level_name": level_name,
        "lane_label": lane_label,
        "block_reason": block_reason or None,
        "market_regime": market_regime,
        "adx": adx,
        "htf_readiness": htf_readiness,
        "weekly_bias": weekly_bias,
        "weekly_xlm_bias": weekly_xlm_bias,
        "weekly_confidence": weekly_conf,
    }


# ── Close ETA ────────────────────────────────────────────────────────

def estimate_close_eta(
    open_position: dict[str, Any],
    trades_df: pd.DataFrame,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Estimate when the current trade will close, based on historical data."""
    now = now or datetime.now(timezone.utc)
    result: dict[str, Any] = {}

    # Elapsed
    entry_time_str = open_position.get("entry_time") or ""
    try:
        entry_dt = datetime.fromisoformat(entry_time_str)
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
    except Exception:
        entry_dt = now
    elapsed_min = max(0.0, (now - entry_dt).total_seconds() / 60.0)
    result["elapsed_min"] = round(elapsed_min, 1)
    result["elapsed_display"] = _fmt_dur(elapsed_min)

    # Build group key
    et = str(open_position.get("entry_type") or "")
    tf = str(open_position.get("breakout_tf") or "")
    regime = str(open_position.get("strategy_regime") or "")

    # Filter historical trades (real trades only — exclude phantom/test)
    hist = _filter_real_trades(trades_df)
    confidence = "high"

    # Try exact match first
    matched = hist
    if et:
        m = hist[hist["entry_type"].astype(str) == et]
        if len(m) >= 5:
            matched = m
        else:
            confidence = "low"

    # Further narrow by tf + regime if enough data
    if len(matched) >= 10 and tf:
        m2 = matched[matched["breakout_tf"].astype(str) == tf]
        if len(m2) >= 5:
            matched = m2
            if confidence == "high" and regime:
                m3 = matched[matched["strategy_regime"].astype(str) == regime]
                if len(m3) >= 5:
                    matched = m3

    if confidence != "low" and len(matched) < 10:
        confidence = "medium"

    # Compute historical stats
    hold_times = matched["time_in_trade_min"].dropna()
    if hold_times.empty:
        result.update({
            "expected_hold_min": None, "expected_display": "no data",
            "remaining_min": None, "remaining_display": "—",
            "progress_pct": 0, "overdue": False,
            "historical_avg_min": None, "historical_range": "—",
            "historical_count": 0, "confidence": "low",
        })
        return result

    hist_avg = float(hold_times.median())
    hist_min_val = float(hold_times.min())
    hist_max_val = float(hold_times.max())
    hist_count = int(len(hold_times))

    # Adjust by trade state
    ew = open_position.get("exit_watch") or {}
    trade_state = str(ew.get("trade_state") or "EARLY")
    state_mult = _STATE_MULT.get(trade_state, 1.0)
    expected = hist_avg * state_mult

    # Adjust for TP proximity
    try:
        tp1 = float(ew.get("tp1") or 0)
        entry_price = float(open_position.get("entry_price") or 0)
        direction = str(open_position.get("direction") or "")
        mark = float(ew.get("dynamic_tp") or 0) or tp1
        if entry_price > 0 and tp1 > 0 and mark > 0:
            if direction == "long":
                total_move = tp1 - entry_price
                current_move = mark - entry_price if mark > entry_price else 0
            else:
                total_move = entry_price - tp1
                current_move = entry_price - mark if mark < entry_price else 0
            if total_move > 0:
                tp_progress = current_move / total_move
                if tp_progress > 0.80:
                    expected *= 0.60  # close to TP → speed up estimate
    except Exception:
        pass

    # Ensure minimum expected of 1 minute
    expected = max(expected, 1.0)
    remaining = expected - elapsed_min
    progress = (elapsed_min / expected * 100) if expected > 0 else 0

    if remaining > 0:
        remaining_display = f"~{_fmt_dur(remaining)} left"
    elif remaining > -1:
        remaining_display = "any moment"
    else:
        remaining_display = f"{_fmt_dur(abs(remaining))} overdue"

    result.update({
        "expected_hold_min": round(expected, 1),
        "expected_display": f"~{_fmt_dur(expected)}",
        "remaining_min": round(remaining, 1),
        "remaining_display": remaining_display,
        "progress_pct": round(progress, 1),
        "overdue": remaining < 0,
        "historical_avg_min": round(hist_avg, 1),
        "historical_range": f"{_fmt_dur(hist_min_val)}-{_fmt_dur(hist_max_val)}",
        "historical_count": hist_count,
        "confidence": confidence,
    })
    return result


# ── Next Entry ETA ───────────────────────────────────────────────────

def estimate_next_entry(
    state: dict[str, Any],
    last_decision: dict[str, Any],
    trades_df: pd.DataFrame,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Estimate when the next trade entry might happen."""
    now = now or datetime.now(timezone.utc)
    result: dict[str, Any] = {}

    # Best candidate from latest decision
    score_l = int(last_decision.get("v4_score_long") or 0)
    score_s = int(last_decision.get("v4_score_short") or 0)
    thresh_l = int(last_decision.get("v4_threshold_long") or 55)
    thresh_s = int(last_decision.get("v4_threshold_short") or 55)
    thought = str(last_decision.get("thought") or "")
    price_now = _safe_float(last_decision.get("price"), 0.0) or 0.0
    contract_size = _safe_float(last_decision.get("contract_size"), 5000.0) or 5000.0
    next_long = _parse_dict(last_decision.get("next_play_long"))
    next_short = _parse_dict(last_decision.get("next_play_short"))

    if score_s >= score_l:
        best_score, best_thresh, best_dir = score_s, thresh_s, "short"
    else:
        best_score, best_thresh, best_dir = score_l, thresh_l, "long"

    # Extract entry type from thought
    entry_type = ""
    for et_name in ("pullback", "breakout_retest", "compression_range", "early_impulse",
                     "compression_breakout", "fib_retrace", "slow_bleed_hunter", "trend_continuation"):
        if et_name.replace("_", " ") in thought.lower() or et_name in thought.lower():
            entry_type = et_name
            break

    if best_score > 0:
        result["watching_setup"] = f"{entry_type or 'signal'} {best_dir} ({best_score}/{best_thresh})"
        result["readiness_pct"] = round(best_score / max(best_thresh, 1) * 100, 0)
    else:
        result["watching_setup"] = "No setup visible"
        result["readiness_pct"] = 0

    # Blocking reasons
    blocking = None
    safe_mode = bool(state.get("_safe_mode"))
    cooldown = state.get("cooldown_until")
    if safe_mode:
        blocking = "safe mode"
    elif cooldown:
        try:
            cd_dt = datetime.fromisoformat(str(cooldown))
            if cd_dt.tzinfo is None:
                cd_dt = cd_dt.replace(tzinfo=timezone.utc)
            if cd_dt > now:
                remaining = (cd_dt - now).total_seconds() / 60.0
                blocking = f"cooldown ({_fmt_dur(remaining)})"
        except Exception:
            pass
    elif state.get("open_position"):
        blocking = "in trade"
    elif best_score > 0 and best_score < best_thresh:
        blocking = "score below threshold"
    elif "r:r" in thought.lower() or "rr" in thought.lower():
        blocking = "R:R too low"
    result["blocking_reason"] = blocking

    # Time since last exit
    last_exit_str = str(state.get("last_exit_time") or "")
    if last_exit_str:
        try:
            last_exit_dt = datetime.fromisoformat(last_exit_str)
            if last_exit_dt.tzinfo is None:
                last_exit_dt = last_exit_dt.replace(tzinfo=timezone.utc)
            result["time_since_exit_min"] = round((now - last_exit_dt).total_seconds() / 60.0, 1)
        except Exception:
            result["time_since_exit_min"] = None
    else:
        result["time_since_exit_min"] = None

    # Average gap between trades from history
    hist = _filter_real_trades(trades_df)
    if len(hist) >= 3 and "entry_time" in hist.columns:
        try:
            entry_times = pd.to_datetime(hist["entry_time"], utc=True, errors="coerce").dropna().sort_values()
            if len(entry_times) >= 3:
                gaps = entry_times.diff().dropna().dt.total_seconds() / 60.0
                # Filter out sub-2-min gaps (phantom re-entries)
                gaps = gaps[gaps >= 2.0]
                if not gaps.empty:
                    avg_gap = float(gaps.median())
                    # Adjust by vol state
                    vol = str(state.get("vol_state") or "")
                    if vol == "COMPRESSION":
                        avg_gap *= 1.5
                    elif vol == "EXPANSION":
                        avg_gap *= 0.6
                    result["avg_gap_min"] = round(avg_gap, 1)
                else:
                    result["avg_gap_min"] = None
            else:
                result["avg_gap_min"] = None
        except Exception:
            result["avg_gap_min"] = None
    else:
        result["avg_gap_min"] = None

    # Build richer forecast
    long_candidate = _build_forecast_candidate(
        direction="long",
        score=score_l,
        threshold=thresh_l,
        play=next_long,
        last_decision=last_decision,
    )
    short_candidate = _build_forecast_candidate(
        direction="short",
        score=score_s,
        threshold=thresh_s,
        play=next_short,
        last_decision=last_decision,
    )
    forecast = long_candidate if long_candidate["weighted"] >= short_candidate["weighted"] else short_candidate
    planned_contracts = _pick_ready_contracts(last_decision)
    result["forecast_direction"] = forecast["direction"]
    result["forecast_contracts"] = planned_contracts
    result["forecast_lane"] = forecast.get("lane_label")
    result["forecast_trigger_price"] = forecast.get("trigger_price")
    result["forecast_trigger_label"] = forecast.get("level_name")
    result["forecast_readiness_pct"] = forecast.get("readiness_pct")
    result["forecast_weighted_score"] = forecast.get("weighted")
    result["forecast_block_reason"] = forecast.get("block_reason")

    distance_atr = _safe_float(forecast.get("distance_atr"))
    trigger_price = _safe_float(forecast.get("trigger_price"))
    atr_est = None
    if price_now > 0 and trigger_price and distance_atr and distance_atr > 0:
        atr_est = abs(price_now - trigger_price) / distance_atr
    elif price_now > 0:
        atr_est = price_now * 0.004

    adx = _safe_float(forecast.get("adx"))
    regime = str(forecast.get("market_regime") or state.get("vol_state") or "mixed")
    expected_atr_mult = 0.8
    if "expansion" in regime.lower():
        expected_atr_mult = 1.2
    elif "compression" in regime.lower():
        expected_atr_mult = 0.6
    if _bias_matches(str(forecast.get("htf_readiness") or ""), forecast["direction"]):
        expected_atr_mult += 0.2
    if _bias_matches(str(forecast.get("weekly_xlm_bias") or ""), forecast["direction"]):
        expected_atr_mult += 0.15
    if adx is not None and adx >= 25:
        expected_atr_mult += 0.15
    expected_atr_mult = min(1.8, max(0.45, expected_atr_mult))

    if atr_est and atr_est > 0 and trigger_price and trigger_price > 0:
        move_points = atr_est * expected_atr_mult
        stop_points = max(atr_est * 0.55, trigger_price * 0.0015)
        target_price = trigger_price + move_points if forecast["direction"] == "long" else trigger_price - move_points
        profit_per_contract = move_points * contract_size
        result["forecast_target_price"] = round(target_price, 6)
        result["forecast_move_points"] = round(move_points, 6)
        result["forecast_move_bps"] = round((move_points / trigger_price) * 10000, 1)
        result["forecast_profit_per_contract_usd"] = round(profit_per_contract, 2)
        result["forecast_profit_total_usd"] = round(profit_per_contract * planned_contracts, 2)
        result["forecast_rr"] = round(move_points / max(stop_points, 1e-9), 2)
    else:
        result["forecast_target_price"] = None
        result["forecast_move_points"] = None
        result["forecast_move_bps"] = None
        result["forecast_profit_per_contract_usd"] = None
        result["forecast_profit_total_usd"] = None
        result["forecast_rr"] = None

    eta_low = None
    eta_high = None
    if blocking:
        if result.get("avg_gap_min"):
            eta_low = float(result["avg_gap_min"])
            eta_high = eta_low * 1.35
    else:
        readiness = float(forecast.get("readiness_pct") or 0.0)
        if readiness >= 95 and (distance_atr is not None and distance_atr <= 0.25):
            eta_low, eta_high = 3.0, 12.0
        elif readiness >= 85 and (distance_atr is not None and distance_atr <= 0.45):
            eta_low, eta_high = 10.0, 30.0
        elif readiness >= 70:
            eta_low, eta_high = 20.0, 75.0
        elif result.get("avg_gap_min"):
            avg_gap = float(result["avg_gap_min"])
            eta_low, eta_high = avg_gap * 0.7, avg_gap * 1.3
        else:
            eta_low, eta_high = 45.0, 180.0
        if "compression" in regime.lower():
            eta_low *= 1.2
            eta_high *= 1.35
        elif "expansion" in regime.lower():
            eta_low *= 0.75
            eta_high *= 0.85

    result["estimated_min"] = round(eta_low, 1) if eta_low is not None else None
    result["estimated_window_max_min"] = round(eta_high, 1) if eta_high is not None else None
    if eta_low is not None and eta_high is not None:
        if eta_high - eta_low < 5:
            result["eta_window_display"] = f"~{_fmt_dur(eta_low)}"
        else:
            result["eta_window_display"] = f"{_fmt_dur(eta_low)}-{_fmt_dur(eta_high)}"
    else:
        result["eta_window_display"] = "Watching..."

    bias_parts: list[str] = []
    weekly_xlm_bias = str(forecast.get("weekly_xlm_bias") or "").strip().lower()
    weekly_bias = str(forecast.get("weekly_bias") or "").strip().lower()
    htf_readiness = str(forecast.get("htf_readiness") or "").strip()
    if weekly_xlm_bias and weekly_xlm_bias != "mixed":
        bias_parts.append(f"weekly XLM bias {weekly_xlm_bias}")
    if weekly_bias and weekly_bias != "mixed":
        bias_parts.append(f"macro bias {weekly_bias}")
    if htf_readiness:
        bias_parts.append(f"HTF {htf_readiness.replace('_', ' ').lower()}")
    bias_parts.append(_describe_regime(regime, adx))
    result["htf_bias_summary"] = " | ".join(part for part in bias_parts if part)

    if forecast["direction"] == "long":
        result["timeframe_logic"] = (
            f"Higher timeframes lean up, but the bot still wants a cleaner long trigger near "
            f"{forecast.get('level_name') or 'support'} before paying up."
        )
    else:
        result["timeframe_logic"] = (
            f"Higher timeframes are not strong enough to force a breakout long, so the bot is still "
            f"watching for a short fade or failed push near {forecast.get('level_name') or 'resistance'}."
        )
    if blocking:
        result["timeframe_logic"] += f" Current blocker: {blocking}."
    elif forecast.get("block_reason"):
        result["timeframe_logic"] += f" Directional blocker: {forecast['block_reason']}."

    result["price_logic"] = (
        f"Current price ${price_now:.5f} vs trigger "
        f"{('$' + format(trigger_price, '.5f')) if trigger_price else '—'}; "
        f"stalking a {forecast['direction']} if readiness and structure stay aligned."
    )

    # Build display string
    if blocking:
        result["estimated_display"] = f"Blocked: {blocking}"
    elif best_score >= best_thresh and best_score > 0:
        result["estimated_display"] = "Setup ready"
    elif result.get("eta_window_display") and result["eta_window_display"] != "Watching...":
        result["estimated_display"] = f"~{result['eta_window_display']}"
    elif result.get("avg_gap_min"):
        result["estimated_display"] = f"~{_fmt_dur(result['avg_gap_min'])}"
    else:
        result["estimated_display"] = "Watching..."

    return result


# ── Internal ─────────────────────────────────────────────────────────

def _filter_real_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Build merged trade records from entry + exit row pairs in trades.csv.

    In this CSV, entry rows have entry_type/breakout_tf/strategy_regime but no
    time_in_trade_min, while exit rows have time_in_trade_min but no entry_type.
    We pair them by matching entry_time fields.
    """
    if trades_df is None or trades_df.empty:
        return pd.DataFrame()
    df = trades_df.copy()

    # Identify exit rows (have time_in_trade) and entry rows (have entry_type)
    if "time_in_trade_min" in df.columns:
        df["time_in_trade_min"] = pd.to_numeric(df["time_in_trade_min"], errors="coerce")
    if "entry_type" not in df.columns or "time_in_trade_min" not in df.columns:
        return pd.DataFrame()

    # Entry rows: have a non-empty entry_type
    entry_rows = df[df["entry_type"].astype(str).str.strip().ne("") & ~df["entry_type"].isna()].copy()
    entry_rows = entry_rows[~entry_rows["entry_type"].astype(str).isin(["test_fire", "live_test_fire"])]

    # Exit rows: have a numeric time_in_trade >= 1 min and a result
    exit_rows = df[df["time_in_trade_min"].notna() & (df["time_in_trade_min"] >= 3.0)].copy()
    if "result" in exit_rows.columns:
        exit_rows = exit_rows[exit_rows["result"].astype(str).isin(["win", "loss", "flat"])]

    if exit_rows.empty:
        return pd.DataFrame()

    # Build lookup: entry_time → entry metadata from entry rows
    if "entry_time" not in df.columns:
        return exit_rows  # fallback: no pairing possible

    entry_lookup = {}
    for _, row in entry_rows.iterrows():
        et_str = str(row.get("entry_time") or row.get("timestamp") or "")
        if et_str:
            entry_lookup[et_str] = {
                "entry_type": str(row.get("entry_type") or ""),
                "breakout_tf": str(row.get("breakout_tf") or ""),
                "strategy_regime": str(row.get("strategy_regime") or ""),
                "breakout_type": str(row.get("breakout_type") or ""),
            }

    # Merge entry metadata into exit rows
    def _merge_entry(row):
        et_str = str(row.get("entry_time") or "")
        meta = entry_lookup.get(et_str, {})
        for k, v in meta.items():
            cur = row.get(k)
            if cur is None or (isinstance(cur, float) and pd.isna(cur)) or str(cur).strip() in ("", "nan"):
                row[k] = v
        return row

    merged = exit_rows.apply(_merge_entry, axis=1)
    return merged
