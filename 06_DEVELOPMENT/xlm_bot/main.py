from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import signal as _signal
import traceback
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yaml

from data.candles import CandleStore, load_or_fetch, ensure_timeframe, fetch_5m_candles, fetch_1m_candles
from execution.coinbase_advanced import CoinbaseAdvanced
from execution.order_manager import OrderManager, OrderRequest
from indicators.ema import ema
from indicators.atr import atr
from structure.levels import compute_structure_levels
from structure.fib import find_swing, fib_levels
from strategy.regime import run_regime_gates, compute_route_tier
from strategy.entries import pullback_continuation, breakout_retest, reversal_impulse, compression_breakout, early_impulse, compression_range, trend_continuation, detect_15m_structure_bias, fib_retrace, _detect_swing_points, slow_bleed_hunter, wick_rejection, volume_climax_reversal, vwap_reversion, grid_range, funding_arb_bias, regime_low_vol, stat_arb_proxy, orderflow_imbalance, macro_ma_cross, mtf_conflict_block, exhaustion_warning_block, liquidity_sweep, htf_breakout_continuation, assess_htf_breakout_continuation, opening_range_breakout, hourly_continuation
from strategy.risk import stop_loss_price, sl_distance_ok
from strategy.exits import tp_prices
from strategy.confluence import compute_confluences, confluence_passes, confluence_count
from strategy.breakout import dominant_timeframe, classify_breakout
from strategy.v4_engine import classify_regime_v4, confluence_score_v4, expected_value_v4
from strategy.adaptive import compute_adaptive_threshold, compute_vol_adaptive_threshold
from strategy.expansion import compute_expansion, derive_vol_state
from timing.trade_eta import estimate_close_eta, estimate_next_entry
from strategy.regime_manager import classify_trading_regime, RegimeOverrides, classify_htf_trend_bias
from strategy.monthly_zones import compute_zone_context
from market.contract_context import ContractContext
from market.futures_relativity import score_futures_relativity
from market.liquidation_feed import read_liquidation_snapshot, score_liquidation_modifier
from market.liquidation_clusters import build_intelligence as build_liquidation_intelligence, format_for_prompt as format_liquidation_prompt, to_dict as liquidation_intel_to_dict
from market.orderbook_context import OrderBookContext, score_orderbook_modifier
from market.score_modifiers import score_contract_modifiers, score_zone_modifier, score_alignment_modifier, detect_liquidation_cascade, log_cascade_event, institutional_oi_gate
from market.moonshot import evaluate_moonshot, moonshot_overrides_exit, moonshot_trail_hit, moonshot_as_dict, MoonshotState
from market.news_intel import get_market_intel
from market.sentiment_gate import get_sentiment, evaluate_sentiment_gate
from market.rolling_expectancy import get_rolling_expectancy, evaluate_expectancy_gate, kelly_size_multiplier
from ai import market_pulse
from strategy.lane_scoring import detect_sweep, detect_reclaim_impulse, select_lane, lane_allowed_by_regime
from strategy.micro_sweep import detect_micro_sweep, MicroSweepResult
from strategy.wick_zones import build_wick_zones, zones_to_levels, zone_proximity_score, WickZone
from strategy.pattern_memory import detect_patterns, pattern_score_modifier, PatternSignal
from strategy.lane_consensus import evaluate_lane_consensus
from strategy.telemetry import write_cycle_telemetry
from risk.balance_reconciler import reconcile_balances as _reconcile_balances, ReconcileResult
from alerts import slack as slack_alert
from alerts import slack_reports as _slack_reports
from alerts import slack_intel
from ai import claude_advisor as ai_advisor
from ai import gemini_advisor
from ai import perplexity_advisor
from ai import codex_advisor
from state_store import StateStore
from risk.margin_policy import evaluate_margin_policy
from risk.plrl3 import evaluate_plrl3, compute_initial_contracts_plrl3
from risk.reconcile import reconcile_exchange_truth
from strategy.lane_performance_tracker import update_lane_performance, get_lane_overrides
from strategy.evolution import EvolutionEngine
from risk.audit_logger import AuditLogger
from ai.decision_linker import link_decisions
from ai import agent_comms
import feature_store
import trade_reviewer
import market_intel_service
from indicators.wick_score import analyze_wick, detect_reclaim_reject, score_for_lane_v


BASE_DIR = Path(__file__).parent
_DEFAULT_COINBASE_CONFIGS = [
    os.environ.get("COINBASE_CONFIG_PATH"),
    str(BASE_DIR / "secrets" / "config.json"),
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/config.json",
]
CRYPTO_BOT_CONFIG = next((str(Path(p).expanduser()) for p in _DEFAULT_COINBASE_CONFIGS if p and Path(p).expanduser().exists()), _DEFAULT_COINBASE_CONFIGS[-1])
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DASHBOARD_SNAPSHOT_PATH = LOGS_DIR / "dashboard_snapshot.json"
DASHBOARD_SNAPSHOT_LAST_GOOD_PATH = LOGS_DIR / "dashboard_snapshot.last_good.json"
DASHBOARD_TIMESERIES_PATH = LOGS_DIR / "dashboard_timeseries.jsonl"
CASH_MOVEMENTS_PATH = LOGS_DIR / "cash_movements.jsonl"
MARKET_NEWS_PATH = LOGS_DIR / "market_news.jsonl"

# Structured audit trail (war room: everlight_packager recommendation)
_audit_logger = AuditLogger(base_dir=LOGS_DIR / "audit")


def _resolve_runtime_dir(value: str | None, default_dir: Path) -> Path:
    if not value:
        return default_dir
    p = Path(str(value)).expanduser()
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


def _deep_merge_dict(base: dict, override: dict) -> dict:
    out = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_dict(out.get(k) or {}, v)
        else:
            out[k] = v
    return out


def _apply_runtime_paths(config: dict) -> None:
    global DATA_DIR, LOGS_DIR, DASHBOARD_SNAPSHOT_PATH, DASHBOARD_SNAPSHOT_LAST_GOOD_PATH, DASHBOARD_TIMESERIES_PATH, CASH_MOVEMENTS_PATH, MARKET_NEWS_PATH
    paths_cfg = (config.get("paths") or {}) if isinstance(config.get("paths"), dict) else {}
    DATA_DIR = _resolve_runtime_dir(paths_cfg.get("data_dir"), BASE_DIR / "data")
    LOGS_DIR = _resolve_runtime_dir(paths_cfg.get("logs_dir"), BASE_DIR / "logs")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_SNAPSHOT_PATH = LOGS_DIR / "dashboard_snapshot.json"
    DASHBOARD_SNAPSHOT_LAST_GOOD_PATH = LOGS_DIR / "dashboard_snapshot.last_good.json"
    DASHBOARD_TIMESERIES_PATH = LOGS_DIR / "dashboard_timeseries.jsonl"
    CASH_MOVEMENTS_PATH = LOGS_DIR / "cash_movements.jsonl"
    MARKET_NEWS_PATH = LOGS_DIR / "market_news.jsonl"
    feature_store.configure(base_dir=BASE_DIR, data_dir=DATA_DIR, logs_dir=LOGS_DIR)


def _session_vwap(df: pd.DataFrame) -> float | None:
    if df is None or df.empty or "close" not in df.columns:
        return None
    try:
        vol = pd.to_numeric(df.get("volume"), errors="coerce").fillna(0.0)
        if float(vol.sum()) <= 0:
            return None
        typical = (
            pd.to_numeric(df.get("high"), errors="coerce").fillna(0.0)
            + pd.to_numeric(df.get("low"), errors="coerce").fillna(0.0)
            + pd.to_numeric(df.get("close"), errors="coerce").fillna(0.0)
        ) / 3.0
        return float((typical * vol).sum() / vol.sum())
    except Exception:
        return None


def _build_lane_v_directional_intel(
    *,
    direction: str,
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    levels: dict[str, float],
    fibs: dict[str, float],
    liquidation_ctx: dict[str, Any],
    contract_ctx: dict[str, Any],
    lane_cfg: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if df_15m is None or df_15m.empty:
        return out
    try:
        atr_val = float(atr(df_15m, 14).iloc[-1])
    except Exception:
        atr_val = 0.0
    if atr_val <= 0:
        return out

    d = direction.lower().strip()
    try:
        conf = compute_confluences(price, df_1h, df_1h, df_15m, levels, fibs, d)
    except Exception:
        conf = {}
    fib_hit = bool(conf.get("FIB_ZONE"))
    try:
        ema21_val = float(ema(df_15m["close"], 21).iloc[-1])
        ema50_val = float(ema(df_15m["close"], 50).iloc[-1])
    except Exception:
        ema21_val = 0.0
        ema50_val = 0.0
    vwap_val = _session_vwap(df_15m)
    ema21_distance_atr = abs(price - ema21_val) / atr_val if atr_val > 0 and ema21_val > 0 else 0.0
    ema50_distance_atr = abs(price - ema50_val) / atr_val if atr_val > 0 and ema50_val > 0 else 0.0
    vwap_distance_atr = abs(price - vwap_val) / atr_val if atr_val > 0 and vwap_val else 0.0
    ema_stretch = ema21_distance_atr >= 1.0 or ema50_distance_atr >= 1.2
    vwap_stretch = vwap_distance_atr >= 1.0

    wick_cfg = {
        "wick_min_ratio": lane_cfg.get("lane_v_wick_min_ratio", 0.35),
        "wick_strong_ratio": lane_cfg.get("lane_v_wick_strong_ratio", 0.50),
        "wick_inspect_bars": 4,
        "wick_confirm_bars": 3,
    }
    wick = analyze_wick(
        df_15m,
        atr_val,
        d,
        wick_cfg,
        fib_hit=fib_hit,
        ema_stretch=ema_stretch,
        vwap_stretch=vwap_stretch,
    )
    funding_rate = float(contract_ctx.get("funding_rate_hr") or 0.0)
    price_velocity = float(pd.to_numeric(df_15m["close"], errors="coerce").diff().tail(3).mean() or 0.0)
    candle = df_15m.iloc[-1]

    liq_cluster_cfg = (lane_cfg.get("liquidation_clusters") or lane_cfg) if isinstance(lane_cfg, dict) else {}
    liq_cluster_cfg = dict(liq_cluster_cfg) if isinstance(liq_cluster_cfg, dict) else {}
    if lane_cfg.get("lane_v_cluster_zone_atr") is not None:
        liq_cluster_cfg["sweep_zone_atr"] = float(
            lane_cfg.get("lane_v_cluster_zone_atr") or liq_cluster_cfg.get("sweep_zone_atr", 0.25)
        )

    base_intel = build_liquidation_intelligence(
        liquidation_ctx or {},
        current_price=price,
        atr_value=atr_val,
        candle_low=float(candle["low"]),
        candle_high=float(candle["high"]),
        candle_close=float(candle["close"]),
        price_velocity=price_velocity,
        funding_rate=funding_rate,
        wick_score=float(wick.score),
        config=liq_cluster_cfg,
        prev_sweep_state=((liquidation_ctx.get("prev_sweep_state") or {}) if isinstance(liquidation_ctx, dict) else {}),
    )
    base_dict = liquidation_intel_to_dict(base_intel)
    sweep_level = float(base_dict.get("sweep_level") or base_intel.sweep.cluster_center or 0.0)
    rr = detect_reclaim_reject(
        df_15m,
        sweep_level=sweep_level,
        direction=d,
        atr_value=atr_val,
        config={"confirm_bars": 3, "fail_buffer_atr": 0.10},
    )

    if rr.reclaim_confirmed:
        base_dict["reclaim_confirmed"] = True
    if rr.rejection_confirmed:
        base_dict["rejection_confirmed"] = True
    base_dict["followthrough_confirmed"] = bool(rr.followthrough_confirmed or wick.followthrough_confirmed)
    base_dict["failed_reclaim"] = bool(rr.failed_reclaim)
    base_dict["failed_rejection"] = bool(rr.failed_rejection)
    base_dict["confirm_bars"] = int(rr.confirm_bars or 0)
    base_dict["wick_score"] = float(wick.score)
    base_dict["wick_ratio"] = float(wick.wick_ratio)
    base_dict["body_failure"] = bool(wick.body_failure)
    base_dict["fib_hit"] = fib_hit
    base_dict["ema_stretch"] = bool(ema_stretch)
    base_dict["ema21_distance_atr"] = round(ema21_distance_atr, 3)
    base_dict["ema50_distance_atr"] = round(ema50_distance_atr, 3)
    base_dict["vwap_stretch"] = bool(vwap_stretch)
    base_dict["vwap_distance_atr"] = round(vwap_distance_atr, 3)
    base_dict["volume_spike"] = bool(wick.volume_above_avg)
    base_dict["funding_rate_hr"] = funding_rate
    base_dict["funding_confirms"] = bool(
        (d == "long" and base_dict.get("funding_lean") == "long")
        or (d == "short" and base_dict.get("funding_lean") == "short")
    )

    strongest_above = (base_intel.clusters_above[0] if base_intel.clusters_above else None)
    strongest_below = (base_intel.clusters_below[0] if base_intel.clusters_below else None)
    relevant_cont = strongest_above if d == "long" else strongest_below
    relevant_rev = strongest_below if d == "long" else strongest_above
    target_cluster = relevant_cont.center_price if relevant_cont else 0.0
    reversal_cluster = relevant_rev.center_price if relevant_rev else 0.0

    balanced_penalty = float(liq_cluster_cfg.get("balanced_penalty", 10) or 10)
    continuation_bonus = float(liq_cluster_cfg.get("continuation_bonus", 2) or 2)
    reversal_bonus = float(liq_cluster_cfg.get("reversal_bonus", 4) or 4)
    lane_score = score_for_lane_v(
        wick,
        rr,
        float((relevant_rev.strength if relevant_rev and base_intel.sweep.status in {"completed", "in_progress"} else (relevant_cont.strength if relevant_cont else 0.0)) or 0.0),
        fib_hit,
        bool(ema_stretch or vwap_stretch),
        bool(base_dict["funding_confirms"]),
        bool(base_dict["volume_spike"]),
        config={
            "min_signals": int(lane_cfg.get("lane_v_min_signals", 4) or 4),
            "threshold": int(lane_cfg.get("lane_v_threshold", 55) or 55),
            "wick_min_ratio": float(lane_cfg.get("lane_v_wick_min_ratio", 0.35) or 0.35),
        },
    )
    if str(base_dict.get("cluster_side") or "") == "balanced":
        lane_score["score"] = max(0, int(lane_score["score"]) - int(balanced_penalty))
        lane_score["pass"] = False

    continuation_ok = bool(
        lane_cfg.get("lane_v_continuation_enabled", True)
        and relevant_cont
        and base_intel.sweep.status == "none"
        and str(base_dict.get("cluster_side") or "") != "balanced"
        and float(base_dict.get("magnet_score") or 0.0) >= float(lane_cfg.get("lane_v_threshold", 55) or 55) - 5
        and float(relevant_cont.strength) >= float(lane_cfg.get("lane_v_min_cluster_strength", 30) or 30)
        and float(relevant_cont.distance_atr) > float(lane_cfg.get("lane_v_continuation_tp_buffer_atr", 0.15) or 0.15)
        and not base_dict["failed_reclaim"]
        and not base_dict["failed_rejection"]
    )
    reversal_ok = bool(
        lane_cfg.get("lane_v_reversal_enabled", True)
        and base_intel.sweep.status in {"completed", "in_progress"}
        and ((d == "long" and base_intel.sweep.sweep_side == "long") or (d == "short" and base_intel.sweep.sweep_side == "short"))
        and float(base_dict.get("wick_ratio") or 0.0) >= float(lane_cfg.get("lane_v_wick_min_ratio", 0.35) or 0.35)
        and float(base_dict.get("wick_score") or 0.0) >= float(lane_cfg.get("lane_v_wick_score_min", 55) or 55)
        and (base_dict.get("reclaim_confirmed") or base_dict.get("rejection_confirmed"))
        and not base_dict["failed_reclaim"]
        and not base_dict["failed_rejection"]
        and (not bool(lane_cfg.get("lane_v_require_volume_spike_for_reversal", False)) or base_dict["volume_spike"])
        and (not bool(lane_cfg.get("lane_v_require_fib_or_ema_stretch", False)) or fib_hit or ema_stretch or vwap_stretch)
        and (float(base_dict.get("distance_to_cluster_atr") or 0.0) <= float(lane_cfg.get("lane_v_max_reversal_chase_atr", 1.2) or 1.2))
    )
    if continuation_ok:
        lane_score["score"] = min(100, int(lane_score.get("score") or 0) + int(continuation_bonus))
    if reversal_ok:
        lane_score["score"] = min(100, int(lane_score.get("score") or 0) + int(reversal_bonus))
    lane_score["pass"] = bool(int(lane_score.get("score") or 0) >= int(lane_cfg.get("lane_v_threshold", 55) or 55))

    no_trade_reason = ""
    if bool(lane_cfg.get("lane_v_skip_balanced_clusters", True)) and str(base_dict.get("cluster_side") or "") == "balanced":
        no_trade_reason = "balanced_clusters_chop"
    elif base_intel.sweep.status in {"completed", "in_progress"} and not reversal_ok:
        if base_dict["failed_reclaim"] or base_dict["failed_rejection"]:
            no_trade_reason = "sweep_failed_reclaim_reject"
        elif float(base_dict.get("wick_score") or 0.0) < float(lane_cfg.get("lane_v_wick_score_min", 55) or 55):
            no_trade_reason = "wick_quality_too_weak"
        elif float(base_dict.get("distance_to_cluster_atr") or 0.0) > float(lane_cfg.get("lane_v_max_reversal_chase_atr", 1.2) or 1.2):
            no_trade_reason = "reversal_chase_too_far"
    elif base_intel.sweep.status == "none" and not continuation_ok:
        if not relevant_cont:
            no_trade_reason = "no_unswept_cluster_ahead"
        elif float(relevant_cont.distance_atr) <= float(lane_cfg.get("lane_v_continuation_tp_buffer_atr", 0.15) or 0.15):
            no_trade_reason = "already_at_target_cluster"
        else:
            no_trade_reason = "continuation_momentum_or_magnet_missing"

    base_dict["target_cluster_price"] = round(target_cluster, 6) if target_cluster > 0 else 0.0
    base_dict["reversal_cluster_price"] = round(reversal_cluster, 6) if reversal_cluster > 0 else 0.0
    base_dict["continuation_ok"] = continuation_ok
    base_dict["reversal_ok"] = reversal_ok
    base_dict["no_trade_reason"] = no_trade_reason
    base_dict["lane_v_mode"] = "reversal" if reversal_ok else ("continuation" if continuation_ok else "none")
    base_dict["lane_v_score"] = int(lane_score.get("score") or 0)
    base_dict["lane_v_score_pass"] = bool(lane_score.get("pass"))
    base_dict["lane_v_core_signals"] = int(lane_score.get("core_count") or 0)
    base_dict["lane_v_signal_flags"] = lane_score.get("signals") or {}
    base_dict["liquidation_prompt"] = format_liquidation_prompt(base_intel)
    return base_dict


def load_config(config_path: str | Path | None = None) -> dict:
    base_cfg_path = BASE_DIR / "config.yaml"
    cfg_path = Path(config_path) if config_path else base_cfg_path
    if not cfg_path.is_absolute():
        cfg_path = BASE_DIR / cfg_path
    with open(base_cfg_path, "r") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        cfg = {}
    if cfg_path != base_cfg_path:
        with open(cfg_path, "r") as f:
            override = yaml.safe_load(f)
        if not isinstance(override, dict):
            override = {}
        cfg = _deep_merge_dict(cfg, override)
    if not isinstance(cfg, dict):
        cfg = {}
    _apply_runtime_paths(cfg)
    cfg["_config_path"] = str(cfg_path)
    return cfg


def _state_path() -> Path:
    return DATA_DIR / "state.json"


def load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    state["last_cycle_ts"] = datetime.now(timezone.utc).isoformat()
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write to avoid a torn state.json on crash/power loss.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_json_safe(state), indent=2, default=str))
    tmp.replace(path)
    # Heartbeat for external watchdog (Termux boot script checks freshness)
    try:
        path.parent.joinpath(".heartbeat").write_text(str(datetime.now(timezone.utc).timestamp()))
    except Exception:
        pass


def _json_safe(obj):
    try:
        import numpy as np
        import pandas as pd
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            # NaN/Inf are not valid JSON -- convert to None
            if v != v or v == float("inf") or v == float("-inf"):
                return None
            return v
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, pd.Series):
            return obj.tolist()
    except ImportError:
        pass
    except Exception:
        pass
    # Handle native float NaN/Inf
    if isinstance(obj, float):
        if obj != obj or obj == float("inf") or obj == float("-inf"):
            return None
    if isinstance(obj, set):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_live_tick() -> dict:
    """Read live_tick.json written by WS feed. Returns dict or empty dict.
    Keys: product_id, price, timestamp, src, written_at, age_seconds (computed).
    """
    try:
        _tick_path = LOGS_DIR / "live_tick.json"
        if not _tick_path.exists():
            return {}
        data = json.loads(_tick_path.read_text())
        if not data or not data.get("price"):
            return {}
        written_at = data.get("written_at")
        if written_at:
            _wt = datetime.fromisoformat(str(written_at))
            if _wt.tzinfo is None:
                _wt = _wt.replace(tzinfo=timezone.utc)
            data["age_seconds"] = (datetime.now(timezone.utc) - _wt).total_seconds()
        else:
            data["age_seconds"] = -1
        return data
    except Exception:
        return {}


def _resolve_output_path(raw_path: str | Path | None, default_dir: Path) -> Path:
    p = Path(str(raw_path or "")).expanduser() if raw_path else Path("")
    if p and p.is_absolute():
        return p
    if not p:
        return default_dir
    # Backward compatibility: explicit logs/data-relative config keeps old behavior.
    if p.parts and p.parts[0] in ("logs", "data"):
        return BASE_DIR / p
    return default_dir / p


def _action_from_reason(reason: str, payload: dict) -> str:
    r = str(reason or "").lower().strip()
    if r in ("plrl3_rescue", "rescue_margin"):
        return "RESCUE"
    if r in ("trend_scale_in",):
        return "SCALE"
    if r in ("trend_flip",):
        return "FLIP"
    if r in ("exit_order_sent", "exchange_side_close", "emergency_exit_mr", "plrl3_exit", "profit_lock"):
        return "EXIT"
    if r in ("entry_order_failed", "duplicate_entry_suppressed"):
        return "ENTRY_FAILED"
    if r in ("halt_trading_mr", "margin_policy_block_entry", "v4_score_block_entry", "ev_block_entry"):
        return "BLOCKED"
    if r in ("quality_tier_entry",):
        return "SETUP"
    if r in ("profit_transfer", "funding_transfer", "funding_transfer_skip", "funding_shortfall", "spot_balance_delta"):
        return "FUNDS"
    if str(payload.get("entry_signal") or "").strip():
        return "SETUP"
    return "HOLD"


def _parse_ts_utc(raw: Any) -> datetime | None:
    try:
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _minutes_between(start: Any, end: Any) -> float | None:
    a = _parse_ts_utc(start)
    b = _parse_ts_utc(end)
    if not a or not b:
        return None
    return max(0.0, (b - a).total_seconds() / 60.0)


def _bool_cfg(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return bool(default)
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return bool(default)


def _direction_allowed(required: Any, actual: Any) -> bool:
    req_raw = str(required or "").strip().lower()
    act = str(actual or "").strip().lower()
    if not act:
        return False
    if not req_raw:
        return True
    if req_raw in ("both", "any", "either", "all"):
        return act in ("long", "short")
    req_parts = [p.strip() for p in req_raw.replace("|", ",").replace("/", ",").split(",") if p.strip()]
    if not req_parts:
        return True
    return act in req_parts


def _format_money_short(v: Any) -> str:
    fv = _to_float(v, None)
    if fv is None:
        return "n/a"
    return f"${fv:.2f}"


def _zone_nearest_summary(zone_ctx: dict) -> dict | None:
    """Compact summary of nearest zone for decision payload."""
    nearest = zone_ctx.get("nearest")
    if not nearest or not isinstance(nearest, dict):
        return None
    return {
        "zone_type": nearest.get("zone_type"),
        "low": nearest.get("low"),
        "high": nearest.get("high"),
        "position": nearest.get("position"),
        "distance_pct": nearest.get("distance_pct"),
        "distance_norm_atr": nearest.get("distance_norm_atr"),
        "strength": nearest.get("strength"),
    }


def _decision_thought(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "quiet cycle: holding."

    reason = str(payload.get("reason") or "").strip().lower()
    product = str(payload.get("product_id") or payload.get("product_selected") or "xlm contract").strip()
    direction = str(payload.get("direction") or "").strip().lower()
    signal = str(payload.get("entry_signal") or "").strip().lower()
    score = _to_float(payload.get("v4_selected_score"), None)
    threshold = _to_float(payload.get("v4_selected_threshold"), None)
    ev = payload.get("ev") if isinstance(payload.get("ev"), dict) else {}
    ev_usd = _to_float((ev or {}).get("ev_usd"), None)
    active_mr = _to_float(payload.get("active_mr"), None)
    pnl = _to_float(payload.get("pnl_usd"), _to_float(payload.get("pnl_today_usd"), None))

    if reason == "exit_order_sent":
        exit_reason = str(payload.get("exit_reason") or "signal").strip().lower()
        return f"closing {product} on {exit_reason}. risk first, recheck next cycle."
    if reason == "exchange_side_close":
        return f"exchange closed {product}; reconciled pnl { _format_money_short(payload.get('pnl_usd')) }."
    if reason == "entry_order_failed":
        return f"setup was there for {product} {direction}, but order failed: {str(payload.get('message') or '').strip()[:90]}"
    if reason == "entry_blocked_preflight":
        blocks = payload.get("block_reasons") if isinstance(payload.get("block_reasons"), list) else []
        failed_gates = payload.get("failed_gates") if isinstance(payload.get("failed_gates"), list) else []
        if failed_gates:
            return f"standing down: preflight blocked by {', '.join([str(x) for x in failed_gates[:3]])}."
        return f"standing down: preflight blocked ({', '.join([str(x) for x in blocks[:3]]) or 'risk check'})."
    if reason == "entry_blocked_no_signal":
        return "no clean edge yet; waiting for better structure + confirmation."
    if reason == "ai_executive_entry_initiated":
        _ai_r = payload.get("ai_directive") or {}
        return f"AI EXECUTIVE: initiating {payload.get('direction', '?')} entry — {str(_ai_r.get('reasoning', ''))[:120]}"
    if reason == "ai_executive_flat_override":
        _ai_r = payload.get("ai_directive") or {}
        return f"AI EXECUTIVE: staying FLAT — {str(_ai_r.get('reasoning', ''))[:120]}"
    if reason == "ai_skip_entry":
        _ai_r = payload.get("ai_insight") or {}
        return f"AI advisor blocked entry — {str(_ai_r.get('reasoning', ''))[:120]}"
    if reason == "v4_score_block_entry":
        failed_flags = payload.get("failed_flags") if isinstance(payload.get("failed_flags"), list) else []
        if failed_flags:
            return f"signal seen, but quality filter blocked ({', '.join([str(x) for x in failed_flags[:3]])})."
        if score is not None and threshold is not None:
            return f"signal seen, but quality too low ({score:.0f}/{threshold:.0f}). skipping."
        return "signal seen, but quality score not high enough. skipping."
    if reason == "ev_block_entry":
        return f"edge is negative after fees/slippage (ev { _format_money_short(ev_usd) }). not worth taking."
    if reason == "margin_policy_block_entry":
        tier = str(payload.get("tier") or "risk").upper()
        return f"margin guard says no new risk ({tier}). holding flat."
    if reason == "plrl3_rescue":
        step = int(_to_float(payload.get("step"), 0) or 0)
        add = int(_to_float(payload.get("add_contracts"), 0) or 0)
        return f"rescue step {step}: adding {add} contract(s) with MR guardrails."
    if reason == "emergency_exit_mr":
        return f"mr danger on {product} (active {active_mr:.3f}): flattening now." if active_mr is not None else f"mr danger on {product}: flattening now."
    if reason == "profit_transfer":
        return f"locking gains: transferred { _format_money_short(payload.get('amount')) } to spot reserve."
    if reason == "funding_transfer":
        return (
            f"moved { _format_money_short(payload.get('amount_usd')) } "
            f"{str(payload.get('currency') or '').upper()} to futures so margin stays healthy."
        )
    if reason == "funding_transfer_skip":
        shortfall = _to_float(payload.get("shortfall_usd"), 0.0) or 0.0
        if shortfall <= 0:
            return "funding check passed; no transfer needed."
        return f"funding check ran, but no transfer executed; shortfall still { _format_money_short(shortfall) }."
    if reason == "funding_shortfall":
        return f"cannot fund safely right now; shortfall { _format_money_short(payload.get('shortfall_usd')) } after constraints."
    if reason == "spot_balance_delta":
        return "account balances changed (USD/USDC); logged as a cash movement event."
    if reason == "distance_gate_override_applied":
        return "trend-short quality is strong; allowing entry despite distance-from-value gate."
    if reason == "atr_gate_override_applied":
        return "trend-short quality is strong; allowing entry despite ATR regime gate."
    if reason == "v4_score_override_applied":
        return "score override applied: strong trend-short setup passed despite EMA alignment miss."

    # Decision snapshots without a reason key.
    if signal and direction:
        base = f"watching {product}: {signal} {direction} setup"
        if score is not None and threshold is not None:
            base += f" ({score:.0f}/{threshold:.0f})"
        if ev_usd is not None:
            base += f", ev { _format_money_short(ev_usd) }"
        return base + "."

    if payload.get("gates_pass") is False:
        gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
        fails = [k for k, v in gates.items() if not bool(v)]
        return f"market not ready: blocked by {', '.join(fails[:3]) or 'regime gates'}."

    if pnl is not None and payload.get("trades_today") is not None:
        return f"holding flat. day pnl { _format_money_short(pnl) }, waiting for next clean edge."

    return "quiet cycle: no high-quality setup yet, staying patient."


def _with_lifecycle_fields(
    row: dict,
    *,
    entry_time: Any = None,
    exit_time: Any = None,
    wait_since_last_exit_min: float | None = None,
) -> dict:
    out = dict(row or {})
    if entry_time is not None:
        out["entry_time"] = entry_time
    if exit_time is not None:
        out["exit_time"] = exit_time
    dur_min = _minutes_between(entry_time, exit_time)
    if dur_min is not None:
        out["time_in_trade_min"] = round(float(dur_min), 2)
    if wait_since_last_exit_min is not None:
        out["wait_since_last_exit_min"] = round(float(wait_since_last_exit_min), 2)
    return out


def _derive_state(prev_state: str, reason: str, payload: dict) -> str:
    r = str(reason or "").lower().strip()
    if r in ("no_data",):
        return "WAITING_DATA"
    if r in ("open_position_tick",):
        return "IN_TRADE"
    if r in ("exit_order_sent", "exchange_side_close", "emergency_exit_mr", "plrl3_exit"):
        return "IN_TRADE_EXITING"
    if r in ("halt_trading_mr", "margin_policy_block_entry", "v4_score_block_entry", "ev_block_entry"):
        return "IDLE_BLOCKED"
    if r in ("quality_tier_entry",):
        return "IDLE_SIGNAL_READY"
    if str(payload.get("entry_signal") or "").strip() and bool(payload.get("gates_pass")):
        return "IDLE_SIGNAL_READY"
    if prev_state:
        return prev_state
    return "IDLE"


def _gate_reasons(payload: dict) -> list[str]:
    gates = payload.get("gates")
    if not isinstance(gates, dict):
        return []
    out = []
    for k, v in gates.items():
        if not bool(v):
            out.append(str(k))
    return out


def _build_block_reason(
    entry_dict: dict | None,
    v4_dict: dict | None,
    gates_pass: bool,
    cooldown: bool,
    product_available: bool,
    gates_effective: dict,
) -> str | None:
    """Short pipe-delimited string explaining why a direction was blocked, or None if it passed."""
    reasons: list[str] = []
    if not entry_dict:
        reasons.append("no_structure")
    if entry_dict and not v4_dict:
        reasons.append("no_score")
    if v4_dict and not bool(v4_dict.get("pass")):
        score = int(v4_dict.get("score") or 0)
        thresh = int(v4_dict.get("threshold") or 75)
        reasons.append(f"score_{score}_below_{thresh}")
    if not gates_pass:
        failed = [k for k, v in gates_effective.items() if not bool(v)]
        if failed:
            reasons.append("gates:" + ",".join(failed))
    if cooldown:
        reasons.append("cooldown")
    if not product_available:
        reasons.append("no_product")
    return "|".join(reasons) if reasons else None


_TIER_RANK = {"NO_TRADE": -1, "SCALP": 0, "REDUCED": 1, "FULL": 2, "MONSTER": 3}


def _compute_quality_tier(score: int, threshold: int, qt_cfg: dict) -> str:
    """Compute quality tier from score vs threshold.

    Returns "MONSTER", "FULL", "REDUCED", "SCALP", or "NO_TRADE".
    """
    if not qt_cfg.get("enabled", False):
        return "FULL" if score >= threshold else "NO_TRADE"
    gap = threshold - score
    if gap <= 0:
        monster_above = int(qt_cfg.get("monster_above", 15) or 15)
        if score >= threshold + monster_above:
            return "MONSTER"
        return "FULL"
    reduced_gap = int(qt_cfg.get("reduced_gap", 10) or 10)
    scalp_gap = int(qt_cfg.get("scalp_gap", 20) or 20)
    if gap <= reduced_gap:
        return "REDUCED"
    if gap <= scalp_gap:
        return "SCALP"
    return "NO_TRADE"


def _resolve_profit_lock_params(
    profit_lock_cfg: dict,
    quality_tier: str,
    regime_name: str,
) -> dict:
    """Resolve tier+regime-aware profit lock parameters.

    Lookup order:
    1. "{TIER}_{regime}" combo key (e.g., FULL_expansion)
    2. "{TIER}" key (e.g., FULL, SCALP)
    3. Flat top-level defaults (backwards compat)
    """
    tiers_cfg = profit_lock_cfg.get("tiers") or {}
    tier_upper = str(quality_tier or "FULL").upper()
    regime_lower = str(regime_name or "transition").lower()
    combo_key = f"{tier_upper}_{regime_lower}"
    override = tiers_cfg.get(combo_key) or tiers_cfg.get(tier_upper) or {}
    return {
        "activate_usd": float(override.get("activate_usd") or profit_lock_cfg.get("activate_usd", 2.0) or 2.0),
        "keep_ratio": float(override.get("keep_ratio") or profit_lock_cfg.get("keep_ratio", 0.45) or 0.45),
        "max_giveback_usd": float(override.get("max_giveback_usd") or profit_lock_cfg.get("max_giveback_usd", 1.25) or 1.25),
    }


def _resolve_entry_profile(pp_cfg: dict, entry_type: str, strategy_regime: str) -> dict:
    """Resolve strategy-specific profit profile for an entry.

    Lookup order:
    1. "{entry_type}_{regime}" combo key (e.g., pullback_trend)
    2. "{entry_type}" key (e.g., pullback, compression_range)
    3. Global defaults
    """
    profiles = pp_cfg.get("entry_profiles") or {}
    et = str(entry_type or "pullback").lower()
    sr = str(strategy_regime or "mean_reversion").lower()
    combo = profiles.get(f"{et}_{sr}") or {}
    base = profiles.get(et) or {}
    return {
        "tp_mult": float(combo.get("tp_mult") or base.get("tp_mult") or 1.0),
        "min_profit_usd": float(combo.get("min_profit_usd") or base.get("min_profit_usd") or 3.0),
        "decay_pct": float(combo.get("decay_pct") or base.get("decay_pct") or 0.45),
    }


def _compute_position_size(
    equity: float,
    price: float,
    stop_price: float,
    contract_size_val: float,
    lane: str,
    quality_tier: str,
    consecutive_wins: int,
    consecutive_losses: int,
    ps_cfg: dict,
) -> tuple[int, dict]:
    """Dynamic position sizing with compound growth.

    Returns (num_contracts, sizing_metadata).
    Uses % of equity risk model: position size scales with account growth.
    Lane budgets, quality tiers, streak, and account tiers all adjust size.
    """
    meta = {}
    if not ps_cfg.get("enabled", False) or equity <= 0 or contract_size_val <= 0:
        return 1, {"mode": "default", "reason": "sizing_disabled"}

    base_risk_pct = float(ps_cfg.get("base_risk_pct", 0.03) or 0.03)
    max_risk_pct = float(ps_cfg.get("max_risk_pct", 0.06) or 0.06)
    min_contracts = int(ps_cfg.get("min_contracts", 1) or 1)
    growth_stage = _select_growth_ladder_stage(ps_cfg, equity)
    # Dynamic max contracts: grows with equity ($500 per contract ceiling)
    _mc_raw = ps_cfg.get("max_contracts", 10)
    _hard_cap = int(ps_cfg.get("max_contracts_hard_cap", 10) or 10)
    if str(_mc_raw).strip().lower() == "auto":
        _eq_per = float(ps_cfg.get("equity_per_contract", 500) or 500)
        max_contracts = max(min_contracts, min(_hard_cap, int(equity / _eq_per))) if _eq_per > 0 else min_contracts
    else:
        max_contracts = int(_mc_raw or 10)
    if growth_stage:
        _stage_base = float(growth_stage.get("base_risk_pct", 0.0) or 0.0)
        _stage_max = float(growth_stage.get("max_risk_pct", 0.0) or 0.0)
        _stage_contracts = int(growth_stage.get("max_contracts", 0) or 0)
        if _stage_base > 0:
            base_risk_pct = min(base_risk_pct, _stage_base)
        if _stage_max > 0:
            max_risk_pct = min(max_risk_pct, _stage_max)
        if _stage_contracts > 0:
            max_contracts = max(min_contracts, min(max_contracts, _stage_contracts))

    # 1. Lane budget multiplier
    lane_budgets = ps_cfg.get("lane_budgets") or {}
    lane_mult = float(lane_budgets.get(lane, 1.0) or 1.0)

    # 2. Quality tier multiplier
    tier_mults = ps_cfg.get("tier_multipliers") or {}
    tier_mult = float(tier_mults.get(quality_tier, 1.0) or 1.0)

    # 3. Streak adjustment (anti-martingale)
    streak_cfg = ps_cfg.get("streak") or {}
    streak_mult = 1.0
    if streak_cfg.get("enabled", False):
        if consecutive_wins > 0:
            bonus_per = float(streak_cfg.get("win_streak_bonus", 0.10) or 0.10)
            cap = int(streak_cfg.get("win_streak_max", 3) or 3)
            streak_mult = 1.0 + bonus_per * min(consecutive_wins, cap)
        elif consecutive_losses > 0:
            cut_per = float(streak_cfg.get("loss_streak_cut", 0.25) or 0.25)
            cap = int(streak_cfg.get("loss_streak_max", 2) or 2)
            streak_mult = max(0.25, 1.0 - cut_per * min(consecutive_losses, cap))

    # 4. Account tier multiplier
    acct_mult = 1.0
    acct_tiers = ps_cfg.get("account_tiers") or []
    for tier in acct_tiers:
        if equity <= float(tier.get("max_equity", 99999)):
            acct_mult = float(tier.get("risk_mult", 1.0) or 1.0)
            break

    # Combine: effective risk % = base * lane * tier * streak * account
    eff_risk_pct = base_risk_pct * lane_mult * tier_mult * streak_mult * acct_mult
    eff_risk_pct = min(eff_risk_pct, max_risk_pct)

    # Calculate $ at risk and contracts
    risk_usd = equity * eff_risk_pct
    sl_distance = abs(price - stop_price)
    if sl_distance <= 0:
        return min_contracts, {"mode": "equity_pct", "reason": "zero_sl_distance"}

    risk_per_contract = sl_distance * contract_size_val
    if risk_per_contract <= 0:
        return min_contracts, {"mode": "equity_pct", "reason": "zero_risk_per_contract"}

    raw_contracts = risk_usd / risk_per_contract
    contracts = max(min_contracts, min(max_contracts, int(raw_contracts)))

    meta = {
        "mode": "equity_pct",
        "equity": round(equity, 2),
        "base_risk_pct": base_risk_pct,
        "eff_risk_pct": round(eff_risk_pct, 4),
        "risk_usd": round(risk_usd, 2),
        "sl_distance": round(sl_distance, 6),
        "risk_per_contract": round(risk_per_contract, 4),
        "raw_contracts": round(raw_contracts, 2),
        "contracts": contracts,
        "max_contracts_ceiling": max_contracts,
        "lane_mult": lane_mult,
        "tier_mult": tier_mult,
        "streak_mult": round(streak_mult, 2),
        "acct_mult": acct_mult,
        "lane": lane,
        "quality_tier": quality_tier,
        "consecutive_wins": consecutive_wins,
        "consecutive_losses": consecutive_losses,
    }
    if growth_stage:
        meta.update({
            "growth_stage_label": growth_stage.get("label"),
            "growth_stage_max_equity": growth_stage.get("max_equity"),
            "growth_stage_max_contracts": growth_stage.get("max_contracts"),
            "growth_daily_target_usd": growth_stage.get("daily_target_usd"),
            "growth_daily_stop_usd": growth_stage.get("daily_stop_usd"),
            "growth_per_trade_risk_usd": growth_stage.get("per_trade_risk_usd"),
            "growth_withdrawal_mode": growth_stage.get("withdrawal_mode"),
        })
    return contracts, meta


def _select_growth_ladder_stage(ps_cfg: dict, equity: float) -> dict:
    ladder_cfg = (ps_cfg.get("growth_ladder") or {}) if isinstance(ps_cfg.get("growth_ladder"), dict) else {}
    if not ladder_cfg.get("enabled", False) or equity <= 0:
        return {}
    stages = ladder_cfg.get("stages") or []
    if not isinstance(stages, list):
        return {}
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        max_equity = float(stage.get("max_equity", 0) or 0)
        if max_equity <= 0:
            continue
        if equity <= max_equity:
            out = dict(stage)
            out["index"] = idx
            return out
    if stages and isinstance(stages[-1], dict):
        out = dict(stages[-1])
        out["index"] = len(stages) - 1
        return out
    return {}


def _compute_contract_readiness(
    api: CoinbaseAdvanced,
    *,
    product_id: str,
    direction: str,
    config: dict,
    state: dict,
    transfers_today: float,
    target_size: int,
    stage_equity: float,
) -> dict:
    if not product_id or target_size <= 0:
        return {"ready": False, "reason": "missing_product"}
    funding_cfg = (config.get("futures_funding") or {}) if isinstance(config.get("futures_funding"), dict) else {}
    funding_prefs = _funding_preferences(funding_cfg)
    margin_info = api.estimate_required_margin(product_id, size=target_size, direction=direction)
    _, bp_info = api.ensure_futures_margin(
        product_id=product_id,
        size=target_size,
        direction=direction,
        buffer_pct=float(funding_cfg.get("buffer_pct", 0.10)),
        reserve_usd=float(funding_cfg.get("reserve_usd", 0.0)),
        auto_transfer=False,
        currency=str(funding_cfg.get("currency", "USDC")),
        preferred_currencies=funding_prefs,
        conversion_cost_bps=float(funding_cfg.get("conversion_cost_bps", 0.0) or 0.0),
        spot_reserve_floor_usd=float(funding_cfg.get("spot_reserve_floor_usd", 0.0)),
        max_transfer_usd=float(funding_cfg.get("max_transfer_per_day_usd", 0.0) or 0.0),
        transfer_used_usd=float(transfers_today or 0.0),
    )
    bp = _to_float((bp_info or {}).get("futures_buying_power"), 0.0) or 0.0
    required_margin = _to_float((margin_info or {}).get("required_margin"), 0.0) or 0.0
    ps_cfg = (config.get("position_sizing") or {}) if isinstance(config.get("position_sizing"), dict) else {}
    readiness_cfg = (ps_cfg.get("readiness") or {}) if isinstance(ps_cfg.get("readiness"), dict) else {}
    buffer_pct = float(
        readiness_cfg.get("contract_buffer_pct", readiness_cfg.get("two_contract_buffer_pct", 0.10)) or 0.10
    )
    required_with_buffer = required_margin * (1 + buffer_pct)
    headroom = bp - required_with_buffer
    stage = _select_growth_ladder_stage(ps_cfg, stage_equity)
    stage_max = int(stage.get("max_contracts", 0) or 0) if stage else 0
    ready = bool(required_margin > 0 and bp > 0 and headroom >= 0 and stage_max >= target_size)
    reason = "ready"
    if stage_max and stage_max < target_size:
        reason = f"growth_stage_caps_at_{stage_max}"
    elif required_margin <= 0:
        reason = "missing_margin_estimate"
    elif bp <= 0:
        reason = "missing_buying_power"
    elif headroom < 0:
        reason = "insufficient_buffered_margin"
    return {
        "ready": ready,
        "reason": reason,
        "target_size": int(target_size),
        "required_margin": round(required_margin, 4) if required_margin > 0 else None,
        "required_with_buffer": round(required_with_buffer, 4) if required_with_buffer > 0 else None,
        "buying_power": round(bp, 4) if bp > 0 else None,
        "headroom": round(headroom, 4),
        "buffer_pct": buffer_pct,
        "growth_stage_label": stage.get("label") if stage else None,
        "growth_stage_max_contracts": stage_max or None,
        "margin_rate": (margin_info or {}).get("margin_rate"),
        "notional": (margin_info or {}).get("notional"),
    }


def _compute_contract_ladder(
    api: CoinbaseAdvanced,
    *,
    product_id: str,
    direction: str,
    config: dict,
    state: dict,
    transfers_today: float,
    stage_equity: float,
    targets: tuple[int, ...] = (1, 2, 3, 5),
) -> dict:
    ladder: dict[str, dict] = {}
    for target in targets:
        try:
            ladder[str(int(target))] = _compute_contract_readiness(
                api,
                product_id=product_id,
                direction=direction,
                config=config,
                state=state,
                transfers_today=transfers_today,
                target_size=int(target),
                stage_equity=stage_equity,
            )
        except Exception as exc:
            ladder[str(int(target))] = {
                "ready": False,
                "reason": f"readiness_error:{type(exc).__name__}",
                "target_size": int(target),
            }
    return ladder


def _apply_expectancy_size_multiplier(size: int, size_mult: float, cfg: dict | None = None) -> tuple[int, dict]:
    out = {
        "expectancy_size_mult": round(float(size_mult or 1.0), 3),
    }
    if size <= 0:
        return size, out

    cfg = cfg or {}
    promotion_min = float(cfg.get("promotion_min_size_mult", 1.15) or 1.15)
    promotion_cap = float(cfg.get("promotion_cap", 1.5) or 1.5)
    reduction_floor = float(cfg.get("reduction_floor", 0.25) or 0.25)
    effective_mult = max(reduction_floor, min(float(size_mult or 1.0), promotion_cap))
    if effective_mult < 1.0:
        out["expectancy_mode"] = "reduce"
        return max(1, int(size * effective_mult)), out
    if effective_mult >= promotion_min:
        out["expectancy_mode"] = "promote"
        return max(size, int(math.ceil(size * effective_mult))), out
    out["expectancy_mode"] = "hold"
    return size, out


def _read_lane_stats(logs_dir: Path) -> dict[str, Any]:
    try:
        payload = _read_json_file(logs_dir / "lane_performance.json")
        if isinstance(payload, dict):
            lanes = payload.get("lanes")
            if isinstance(lanes, dict):
                return lanes
    except Exception:
        pass
    return {}


def _lane_specific_expectancy_multiplier(
    lane_letter: str | None,
    lane_stats: dict[str, Any] | None,
    cfg: dict | None = None,
) -> tuple[float, dict[str, Any]]:
    lane = str(lane_letter or "").upper().strip()
    stats = lane_stats or {}
    lane_cfg = cfg or {}
    if not lane or lane != "W":
        return 1.0, {"lane_expectancy_mode": "skip"}
    item = stats.get(lane)
    if not isinstance(item, dict):
        return 1.0, {"lane_expectancy_mode": "no_data", "lane_expectancy_lane": lane}

    count = int(item.get("count") or 0)
    win_rate = float(item.get("win_rate") or 0.0)
    avg_pnl = float(item.get("avg_pnl_usd") or 0.0)
    sharpe = float(item.get("sharpe") or 0.0)
    min_trades = int(lane_cfg.get("lane_w_expectancy_min_trades", 5) or 5)
    promote_wr = float(lane_cfg.get("lane_w_expectancy_promote_win_rate", 0.55) or 0.55)
    reduce_wr = float(lane_cfg.get("lane_w_expectancy_reduce_win_rate", 0.40) or 0.40)
    max_promote = float(lane_cfg.get("lane_w_expectancy_promote_mult", 1.15) or 1.15)
    max_reduce = float(lane_cfg.get("lane_w_expectancy_reduce_mult", 0.75) or 0.75)

    meta = {
        "lane_expectancy_lane": lane,
        "lane_expectancy_trades": count,
        "lane_expectancy_win_rate": round(win_rate, 3),
        "lane_expectancy_avg_pnl_usd": round(avg_pnl, 3),
        "lane_expectancy_sharpe": round(sharpe, 3),
    }
    if count < min_trades:
        meta["lane_expectancy_mode"] = "observe"
        return 1.0, meta
    if win_rate >= promote_wr and avg_pnl > 0 and sharpe >= 0:
        meta["lane_expectancy_mode"] = "promote"
        return max_promote, meta
    if win_rate <= reduce_wr or avg_pnl < 0:
        meta["lane_expectancy_mode"] = "reduce"
        return max_reduce, meta
    meta["lane_expectancy_mode"] = "hold"
    return 1.0, meta


def _nontrade_slack_allowed(config: dict, state: dict | None = None) -> bool:
    alert_cfg = (config.get("slack_alerts") or {}) if isinstance(config.get("slack_alerts"), dict) else {}
    trade_only = bool(alert_cfg.get("trade_only_mode", True))
    if not trade_only:
        return True
    if isinstance(state, dict):
        return bool(state.get("open_position"))
    return False


def _score_weekly_research_modifier(
    direction: str,
    research: dict[str, Any] | None,
    config: dict | None = None,
) -> tuple[int, list[str]]:
    if not direction or not isinstance(research, dict):
        return 0, []

    market_cfg = (config.get("market_intel") or {}) if isinstance(config, dict) else {}
    weekly_cfg = (market_cfg.get("weekly_research") or {}) if isinstance(market_cfg, dict) else {}
    if not bool(weekly_cfg.get("enabled", True)):
        return 0, []

    max_bonus = max(1, int(weekly_cfg.get("score_bonus_max", 3) or 3))
    min_conf = float(weekly_cfg.get("min_confidence", 0.45) or 0.45)
    confidence = float(research.get("confidence") or 0.0)
    if confidence < min_conf:
        return 0, ["weekly_research_low_confidence"]

    bias = str(research.get("directional_bias") or "mixed").lower()
    xlm_bias = str(research.get("xlm_bias") or "mixed").lower()
    macro_regime = str(research.get("macro_regime") or "neutral").lower()
    side = direction.lower().strip()

    bonus = 0
    reasons: list[str] = []
    if side == "long":
        if bias == "bullish":
            bonus += 1
            reasons.append("weekly_macro_bias_bullish")
        elif bias == "bearish":
            bonus -= 1
            reasons.append("weekly_macro_bias_bearish")
        if xlm_bias == "bullish":
            bonus += 2
            reasons.append("weekly_xlm_bias_bullish")
        elif xlm_bias == "bearish":
            bonus -= 2
            reasons.append("weekly_xlm_bias_bearish")
        if macro_regime == "risk_off":
            bonus -= 1
            reasons.append("weekly_macro_regime_risk_off")
    elif side == "short":
        if bias == "bearish":
            bonus += 1
            reasons.append("weekly_macro_bias_bearish")
        elif bias == "bullish":
            bonus -= 1
            reasons.append("weekly_macro_bias_bullish")
        if xlm_bias == "bearish":
            bonus += 2
            reasons.append("weekly_xlm_bias_bearish")
        elif xlm_bias == "bullish":
            bonus -= 2
            reasons.append("weekly_xlm_bias_bullish")
        if macro_regime == "risk_on":
            bonus -= 1
            reasons.append("weekly_macro_regime_risk_on")

    if str(research.get("window_label") or "").upper() in {"SUNDAY_RESEARCH", "MONDAY_OPENING_BIAS"}:
        reasons.append("weekly_refresh_window_active")
        if bonus > 0:
            bonus += 1

    return max(-max_bonus, min(max_bonus, bonus)), reasons


def _compute_friday_break_risk(
    *,
    config: dict,
    now_utc: datetime | None = None,
) -> dict:
    mp_cfg = (config.get("margin_policy") or {}) if isinstance(config.get("margin_policy"), dict) else {}
    fb_cfg = (mp_cfg.get("friday_break") or {}) if isinstance(mp_cfg.get("friday_break"), dict) else {}
    if not bool(fb_cfg.get("enabled", True)):
        return {
            "enabled": False,
            "active": False,
            "pre_break_lock": False,
            "force_flat_now": False,
            "reopen_cooldown_active": False,
            "label": "DISABLED",
            "notes": ["friday_break_disabled"],
        }
    try:
        from zoneinfo import ZoneInfo
        now_utc = now_utc or datetime.now(timezone.utc)
        now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        now_et = (now_utc or datetime.now(timezone.utc))

    break_weekday = int(fb_cfg.get("break_weekday", 4) or 4)
    start_h = int(fb_cfg.get("break_start_hour_et", 17) or 17)
    start_m = int(fb_cfg.get("break_start_minute_et", 0) or 0)
    end_h = int(fb_cfg.get("break_end_hour_et", 18) or 18)
    end_m = int(fb_cfg.get("break_end_minute_et", 0) or 0)
    pre_lock_min = int(fb_cfg.get("pre_break_new_entry_lock_minutes", 60) or 60)
    force_flat_min = int(fb_cfg.get("force_flat_minutes_before_break", 20) or 20)
    reopen_cooldown_min = int(fb_cfg.get("reopen_cooldown_minutes", 10) or 10)

    current_minutes = now_et.hour * 60 + now_et.minute
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    is_friday = int(now_et.weekday()) == break_weekday
    is_break_active = bool(is_friday and start_minutes <= current_minutes < end_minutes)
    in_pre_break_lock = bool(is_friday and (start_minutes - pre_lock_min) <= current_minutes < start_minutes)
    force_flat_now = bool(is_friday and (start_minutes - force_flat_min) <= current_minutes < start_minutes)
    reopen_cooldown_active = bool(is_friday and end_minutes <= current_minutes < (end_minutes + reopen_cooldown_min))

    minutes_to_break = None
    if is_friday and current_minutes < start_minutes:
        minutes_to_break = start_minutes - current_minutes
    minutes_to_reopen = None
    if is_friday and current_minutes < end_minutes:
        minutes_to_reopen = end_minutes - current_minutes

    label = "NORMAL"
    notes: list[str] = []
    if is_break_active:
        label = "FRIDAY_BREAK_ACTIVE"
        notes.append("exchange_break_window")
    elif force_flat_now:
        label = "FRIDAY_BREAK_FORCE_FLAT"
        notes.append("flatten_before_exchange_break")
    elif in_pre_break_lock:
        label = "FRIDAY_BREAK_PRELOCK"
        notes.append("block_new_entries_before_break")
    elif reopen_cooldown_active:
        label = "FRIDAY_BREAK_REOPEN_COOLDOWN"
        notes.append("let_reopen_orderflow_settle")
    else:
        notes.append("friday_break_clear")

    return {
        "enabled": True,
        "active": is_break_active,
        "pre_break_lock": in_pre_break_lock,
        "force_flat_now": force_flat_now,
        "reopen_cooldown_active": reopen_cooldown_active,
        "minutes_to_break": minutes_to_break,
        "minutes_to_reopen": minutes_to_reopen,
        "label": label,
        "notes": notes,
    }


def _resolve_margin_window_playbook(
    *,
    config: dict,
    mp_decision,
    overnight_trading_ok: bool,
    quality_tier: str,
    two_contract_ready: dict,
    friday_break: dict | None = None,
    now_utc: datetime | None = None,
) -> dict:
    mp_cfg = (config.get("margin_policy") or {}) if isinstance(config.get("margin_policy"), dict) else {}
    pb_cfg = (mp_cfg.get("playbook") or {}) if isinstance(mp_cfg.get("playbook"), dict) else {}
    metrics = (mp_decision.metrics or {}) if mp_decision and isinstance(getattr(mp_decision, "metrics", None), dict) else {}
    margin_window = str(metrics.get("margin_window") or "unknown")
    if margin_window == "unknown":
        try:
            from zoneinfo import ZoneInfo
            now_utc = now_utc or datetime.now(timezone.utc)
            now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
            t_et = now_et.timetz().replace(tzinfo=None)
            cutoff_h = int(mp_cfg.get("cutoff_hour_et", 16) or 16)
            cutoff_m = int(mp_cfg.get("cutoff_minute_et", 0) or 0)
            intra_h = int(mp_cfg.get("intraday_start_hour_et", 8) or 8)
            intra_m = int(mp_cfg.get("intraday_start_minute_et", 0) or 0)
            pre_cut = int(mp_cfg.get("pre_cutoff_minutes", 15) or 15)
            cutoff_minutes = cutoff_h * 60 + cutoff_m
            start_minutes = intra_h * 60 + intra_m
            now_minutes = t_et.hour * 60 + t_et.minute
            if now_minutes < start_minutes or now_minutes >= cutoff_minutes:
                margin_window = "overnight"
            elif now_minutes >= (cutoff_minutes - pre_cut):
                margin_window = "pre_cutoff"
            else:
                margin_window = "intraday"
        except Exception:
            margin_window = "overnight"
    mins_to_cutoff = int(metrics.get("mins_to_cutoff") or 9999)
    quality_tier = str(quality_tier or "NO_TRADE").upper()

    def _tier_rank(label: str) -> int:
        return int(_TIER_RANK.get(str(label or "NO_TRADE").upper(), 0))

    if not bool(pb_cfg.get("enabled", True)):
        return {
            "enabled": False,
            "label": "DISABLED",
            "margin_window": margin_window,
            "objective": "playbook_disabled",
            "block_new_entries": False,
            "allow_multi_contract": False,
            "max_new_contracts": None,
            "force_exit_before_cutoff": False,
            "force_flat_now": False,
            "mins_to_cutoff": mins_to_cutoff,
            "notes": ["playbook_disabled"],
        }

    notes: list[str] = []
    if margin_window == "intraday":
        profile = (pb_cfg.get("intraday") or {}) if isinstance(pb_cfg.get("intraday"), dict) else {}
        label = str(profile.get("label") or "INTRADAY_ATTACK")
        objective = str(profile.get("objective") or "press_best_setups_and_close_before_cutoff")
        block_new_entries = False
        allow_multi_contract = bool(profile.get("allow_multi_contract", True))
        max_new_contracts = int(profile.get("max_new_contracts", 2) or 2)
        min_quality = str(profile.get("min_quality_for_multi_contract", "FULL") or "FULL").upper()
        force_exit_before_cutoff = bool(profile.get("force_exit_before_cutoff", True))
        notes.append("lower_margin_window")
        if allow_multi_contract and _tier_rank(quality_tier) < _tier_rank(min_quality):
            allow_multi_contract = False
            notes.append(f"needs_{min_quality}_for_multi_contract")
        if allow_multi_contract and not bool(two_contract_ready.get("ready")):
            allow_multi_contract = False
            notes.append(str(two_contract_ready.get("reason") or "two_contract_not_ready"))
    elif margin_window == "pre_cutoff":
        profile = (pb_cfg.get("pre_cutoff") or {}) if isinstance(pb_cfg.get("pre_cutoff"), dict) else {}
        label = str(profile.get("label") or "PRE_CUTOFF_DEFENSE")
        objective = str(profile.get("objective") or "no_new_risk_manage_existing_position_and_be_flat_before_overnight")
        block_new_entries = bool(profile.get("block_new_entries", True))
        allow_multi_contract = False
        max_new_contracts = int(profile.get("max_new_contracts", 1) or 1)
        force_exit_before_cutoff = bool(profile.get("force_exit_before_cutoff", True))
        notes.extend(["cutoff_approaching", "prefer_flat_before_overnight"])
    else:
        profile = (pb_cfg.get("overnight") or {}) if isinstance(pb_cfg.get("overnight"), dict) else {}
        label = str(profile.get("label") or "OVERNIGHT_DEFENSE")
        objective = str(profile.get("objective") or "preserve_capital_trade_small_only_if_overnight_margin_is_safe")
        if overnight_trading_ok:
            block_new_entries = bool(profile.get("block_new_entries_when_safe", False))
            allow_multi_contract = bool(profile.get("allow_multi_contract_when_safe", False))
            max_new_contracts = int(profile.get("max_new_contracts_when_safe", 1) or 1)
            notes.append("overnight_trading_safe")
        else:
            block_new_entries = bool(profile.get("block_new_entries_if_not_safe", True))
            allow_multi_contract = False
            max_new_contracts = int(profile.get("max_new_contracts_when_unsafe", 1) or 1)
            notes.extend(["overnight_margin_defense", "avoid_fresh_risk_without_overnight_cushion"])
        force_exit_before_cutoff = False

    notes.append("multi_contract_window_open" if allow_multi_contract else "single_contract_bias")
    if force_exit_before_cutoff:
        notes.append("close_before_cutoff")

    friday_break = friday_break or {}
    force_flat_now = False
    if bool(friday_break.get("enabled", True)):
        if bool(friday_break.get("active")):
            label = "FRIDAY_BREAK_ACTIVE"
            objective = "exchange_break_active_do_not_trade"
            block_new_entries = True
            allow_multi_contract = False
            max_new_contracts = 0
            force_flat_now = False
            notes.extend(list(friday_break.get("notes") or []))
        elif bool(friday_break.get("force_flat_now")):
            label = "FRIDAY_BREAK_FORCE_FLAT"
            objective = "flatten_and_avoid_new_risk_before_exchange_break"
            block_new_entries = True
            allow_multi_contract = False
            max_new_contracts = 0
            force_flat_now = True
            notes.extend(list(friday_break.get("notes") or []))
        elif bool(friday_break.get("pre_break_lock")):
            label = "FRIDAY_BREAK_PRELOCK"
            objective = "no_new_entries_into_exchange_break"
            block_new_entries = True
            allow_multi_contract = False
            max_new_contracts = 0
            notes.extend(list(friday_break.get("notes") or []))
        elif bool(friday_break.get("reopen_cooldown_active")):
            label = "FRIDAY_BREAK_REOPEN_COOLDOWN"
            objective = "let_post_break_orderflow_settle_before_reentry"
            block_new_entries = True
            allow_multi_contract = False
            max_new_contracts = 0
            notes.extend(list(friday_break.get("notes") or []))

    return {
        "enabled": True,
        "label": label,
        "margin_window": margin_window,
        "objective": objective,
        "block_new_entries": bool(block_new_entries),
        "allow_multi_contract": bool(allow_multi_contract),
        "max_new_contracts": int(max_new_contracts) if max_new_contracts > 0 else None,
        "force_exit_before_cutoff": bool(force_exit_before_cutoff),
        "force_flat_now": bool(force_flat_now),
        "mins_to_cutoff": mins_to_cutoff,
        "notes": notes,
    }


def _evaluate_recovery_mode(state: dict, config: dict, now: datetime) -> dict:
    """
    Evaluate Recovery Mode state machine.

    States: NORMAL → RECOVERY → SAFE_MODE
    Returns dict with mode info and trade adjustments.
    """
    v4_cfg = config.get("v4", {}) if isinstance(config.get("v4"), dict) else {}
    rm_cfg = v4_cfg.get("recovery_mode", {}) if isinstance(v4_cfg.get("recovery_mode"), dict) else {}
    if not rm_cfg.get("enabled", False):
        return {"mode": "NORMAL", "active": False}

    loss_trigger = float(rm_cfg.get("loss_trigger_usd", 4.0) or 4.0)
    goal_mult = float(rm_cfg.get("goal_multiplier", 2.0) or 2.0)
    max_trades = int(rm_cfg.get("max_recovery_trades", 2) or 2)
    max_dd = float(rm_cfg.get("max_daily_drawdown_usd", 15.0) or 15.0)
    size_mult = float(rm_cfg.get("size_multiplier", 1.25) or 1.25)
    max_size_mult = float(rm_cfg.get("max_size_multiplier", 1.35) or 1.35)
    min_score = int(rm_cfg.get("min_score", 50) or 50)
    tp_tight = float(rm_cfg.get("tp_tightness", 0.65) or 0.65)
    max_hold = float(rm_cfg.get("max_hold_minutes", 30) or 30)
    cool_after_loss = float(rm_cfg.get("cooldown_after_loss_minutes", 10) or 10)

    # Read state
    pnl_today = float(state.get("pnl_today_usd") or 0)
    exchange_pnl = float(state.get("exchange_pnl_today_usd") or 0)
    # Prefer exchange PnL (Coinbase-verified)
    realized_pnl = exchange_pnl if exchange_pnl != 0 else pnl_today

    current_mode = str(state.get("recovery_mode", "NORMAL"))
    recovery_attempts = int(state.get("recovery_attempts") or 0)
    recovery_start_pnl = float(state.get("recovery_start_pnl") or 0)
    last_loss_side = str(state.get("last_loss_side") or "")

    result = {
        "mode": current_mode,
        "active": False,
        "preferred_side": "",
        "size_multiplier": 1.0,
        "min_score": min_score,
        "tp_tightness": 1.0,
        "max_hold_minutes": 0,
        "recovery_debt": 0,
        "recovery_goal": 0,
        "recovery_attempts": recovery_attempts,
        "max_recovery_trades": max_trades,
    }

    # DISABLED: SAFE_MODE: too much drawdown — no trades
    # DISABLED:     if max_dd > 0 and realized_pnl <= -max_dd:
    # DISABLED:         state["recovery_mode"] = "SAFE_MODE"
    # DISABLED:         result["mode"] = "SAFE_MODE"
    # DISABLED:         return result

    # Check if we should EXIT recovery (goal met)
    if current_mode == "RECOVERY":
        net_since = realized_pnl - recovery_start_pnl
        debt = abs(recovery_start_pnl) if recovery_start_pnl < 0 else 0
        goal = debt * goal_mult
        result["recovery_debt"] = round(debt, 2)
        result["recovery_goal"] = round(goal, 2)

        if net_since >= goal:
            # Goal met — back to normal
            state["recovery_mode"] = "NORMAL"
            state["recovery_attempts"] = 0
            state["recovery_start_pnl"] = 0
            result["mode"] = "NORMAL"
            return result

        if recovery_attempts >= max_trades:
            # Used all attempts — back to normal, cool down
            state["recovery_mode"] = "NORMAL"
            state["recovery_attempts"] = 0
            state["recovery_start_pnl"] = 0
            result["mode"] = "NORMAL"
            return result
        # DISABLED: 
        # DISABLED:         if max_dd > 0 and realized_pnl <= -max_dd:
        # DISABLED:             state["recovery_mode"] = "SAFE_MODE"
        # DISABLED:             result["mode"] = "SAFE_MODE"
        # DISABLED:             return result

        # Still in recovery — return semi-aggressive settings
        preferred = "long" if last_loss_side == "short" else ("short" if last_loss_side == "long" else "")
        result["active"] = True
        result["preferred_side"] = preferred
        result["size_multiplier"] = min(size_mult, max_size_mult)
        result["min_score"] = min_score
        result["tp_tightness"] = tp_tight
        result["max_hold_minutes"] = max_hold
        return result

    # NORMAL mode — check if we should ENTER recovery
    if current_mode == "NORMAL" and realized_pnl <= -loss_trigger:
        # Check cooldown from last recovery loss
        _rc_cool = state.get("recovery_cooldown_until")
        if _rc_cool:
            try:
                if now <= datetime.fromisoformat(_rc_cool):
                    return result  # Still cooling down
            except Exception:
                pass

        state["recovery_mode"] = "RECOVERY"
        state["recovery_start_pnl"] = realized_pnl
        state["recovery_attempts"] = 0
        preferred = "long" if last_loss_side == "short" else ("short" if last_loss_side == "long" else "")
        debt = abs(realized_pnl)
        goal = debt * goal_mult

        result["mode"] = "RECOVERY"
        result["active"] = True
        result["preferred_side"] = preferred
        result["size_multiplier"] = min(size_mult, max_size_mult)
        result["min_score"] = min_score
        result["tp_tightness"] = tp_tight
        result["max_hold_minutes"] = max_hold
        result["recovery_debt"] = round(debt, 2)
        result["recovery_goal"] = round(goal, 2)
        return result

    return result


def _evaluate_post_tp_bias(state: dict, config: dict, now: datetime) -> str:
    """
    After any TP exit, bias next trade toward the opposite direction.
    Returns "long", "short", or "" (no bias).
    """
    v4_cfg = config.get("v4", {}) if isinstance(config.get("v4"), dict) else {}
    rm_cfg = v4_cfg.get("recovery_mode", {}) if isinstance(v4_cfg.get("recovery_mode"), dict) else {}
    bias_cfg = rm_cfg.get("post_tp_bias", {}) if isinstance(rm_cfg.get("post_tp_bias"), dict) else {}
    if not bias_cfg.get("enabled", False):
        return ""

    bias_side = str(state.get("post_tp_bias_side") or "")
    if not bias_side:
        return ""

    # Check expiry by time
    expire_min = float(bias_cfg.get("expire_minutes", 30) or 30)
    bias_set_at = state.get("post_tp_bias_set_at")
    if bias_set_at:
        try:
            if now > datetime.fromisoformat(bias_set_at) + timedelta(minutes=expire_min):
                state["post_tp_bias_side"] = ""
                return ""
        except Exception:
            pass

    # Check expiry by trade count
    expire_trades = int(bias_cfg.get("expire_after_trades", 1) or 1)
    trades_since = int(state.get("post_tp_bias_trades_since") or 0)
    if trades_since >= expire_trades:
        state["post_tp_bias_side"] = ""
        return ""

    return bias_side


def _compute_unlock_hints(v4_result: dict | None, n: int = 3) -> list[str]:
    """Top-N FALSE flags by weight that would boost score most."""
    if not v4_result:
        return []
    regime = str(v4_result.get("regime") or "trend")
    if regime == "trend":
        flags = v4_result.get("trend_flags") or {}
        weights = {
            "HTF_BREAK": 20, "EMA_ALIGN_SLOPE": 20, "ADX_TREND": 15,
            "ATR_EXPANDING": 15, "VOLUME_SPIKE": 15, "BB_EXPAND_OR_WALK": 10,
            "MACD_MOMENTUM": 5, "VWAP_CONFIRM": 5, "CHANNEL_BREAKOUT": 15,
        }
    else:
        flags = v4_result.get("mr_flags") or {}
        weights = {
            "HTF_LEVEL": 20, "FIB_ZONE": 15, "RSI_EXTREME": 15,
            "MACD_DIVERGENCE": 15, "BB_REJECTION": 10, "VOLUME_SPIKE": 10,
            "ADX_LOW": 10, "ATR_NOT_EXPANDING": 5, "VWAP_CONFIRM": 10,
            "FVG_SUPPORT": 10, "CHANNEL_SUPPORT": 10,
        }
    missing = [(k, weights.get(k, 0)) for k, v in flags.items() if not bool(v)]
    missing.sort(key=lambda x: -x[1])
    return [f"{name}(+{w})" for name, w in missing[:n]]


def _compute_next_play(
    price: float,
    direction: str,
    levels: dict,
    fibs: dict,
    channel_detail: dict | None,
    vwap_price: float,
    atr_15m: float,
    v4_score: int,
    v4_threshold: int,
) -> dict | None:
    """Find nearest support (long) or resistance (short) trigger level."""
    if price <= 0 or atr_15m <= 0:
        return None

    candidates: list[tuple[str, float]] = []

    for name, lvl in levels.items():
        if not isinstance(lvl, (int, float)) or lvl <= 0:
            continue
        if direction == "long" and lvl < price:
            candidates.append((name.replace("_", " "), float(lvl)))
        elif direction == "short" and lvl > price:
            candidates.append((name.replace("_", " "), float(lvl)))

    for name, lvl in fibs.items():
        if not isinstance(lvl, (int, float)) or lvl <= 0:
            continue
        if direction == "long" and lvl < price:
            candidates.append((f"fib {name}", float(lvl)))
        elif direction == "short" and lvl > price:
            candidates.append((f"fib {name}", float(lvl)))

    if vwap_price and vwap_price > 0:
        if direction == "long" and vwap_price < price:
            candidates.append(("vwap", float(vwap_price)))
        elif direction == "short" and vwap_price > price:
            candidates.append(("vwap", float(vwap_price)))

    if channel_detail and isinstance(channel_detail, dict):
        lower = float(channel_detail.get("lower") or 0)
        upper = float(channel_detail.get("upper") or 0)
        if direction == "long" and 0 < lower < price:
            candidates.append(("channel lower", lower))
        if direction == "short" and upper > price:
            candidates.append(("channel upper", upper))

    if not candidates:
        return None

    candidates.sort(key=lambda x: abs(price - x[1]))
    best_name, best_price = candidates[0]
    distance = abs(price - best_price)
    distance_atr = distance / atr_15m if atr_15m > 0 else 0
    readiness_pct = min(100, int((v4_score / max(v4_threshold, 1)) * 100))

    return {
        "trigger_price": round(best_price, 6),
        "level_name": best_name,
        "distance_atr": round(distance_atr, 2),
        "readiness_pct": readiness_pct,
        "score": v4_score,
        "threshold": v4_threshold,
    }


def _update_dashboard_feed(update: dict, *, append_timeseries: bool = False) -> None:
    DASHBOARD_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev = _read_json_file(DASHBOARD_SNAPSHOT_PATH)
    snap = dict(prev) if isinstance(prev, dict) else {}
    for k, v in (_json_safe(update) or {}).items():
        if v is not None:
            snap[str(k)] = v

    snap["ts"] = snap.get("ts") or datetime.now(timezone.utc).isoformat()

    # Atomic snapshot write + last-good backup for dashboard corruption fallback.
    tmp = DASHBOARD_SNAPSHOT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_json_safe(snap), separators=(",", ":"), ensure_ascii=False))
    tmp.replace(DASHBOARD_SNAPSHOT_PATH)
    try:
        DASHBOARD_SNAPSHOT_LAST_GOOD_PATH.write_text(json.dumps(_json_safe(snap), separators=(",", ":"), ensure_ascii=False))
    except Exception:
        pass

    if append_timeseries:
        line = {
            "ts": snap.get("ts"),
            "product": snap.get("product"),
            "price": snap.get("price"),
            "state": snap.get("state"),
            "regime": snap.get("regime"),
            "gates_pass": snap.get("gates_pass"),
            "entry_signal": snap.get("entry_signal"),
            "direction": snap.get("direction"),
            "trades_today": snap.get("trades_today"),
            "losses_today": snap.get("losses_today"),
            "pnl_today_usd": snap.get("pnl_today_usd"),
            "active_mr": snap.get("active_mr"),
            "mr_intraday": snap.get("mr_intraday"),
            "mr_overnight": snap.get("mr_overnight"),
            "dist_to_liq": snap.get("dist_to_liq"),
            "rescue_count": snap.get("rescue_count"),
            "scale_count": snap.get("scale_count"),
            "confluence_score": snap.get("confluence_score"),
            "ev_usd": (snap.get("ev_estimate") or {}).get("ev_usd") if isinstance(snap.get("ev_estimate"), dict) else snap.get("ev_estimate"),
            "last_action": snap.get("last_action"),
            "time_in_trade_min": snap.get("time_in_trade_min"),
            "wait_since_last_exit_min": snap.get("wait_since_last_exit_min"),
            "transfers_today_usd": snap.get("transfers_today_usd"),
            "conversion_cost_today_usd": snap.get("conversion_cost_today_usd"),
        }
        with open(DASHBOARD_TIMESERIES_PATH, "a") as f:
            f.write(json.dumps(_json_safe(line)) + "\n")


def _dashboard_update_from_decision(payload: dict) -> tuple[dict, bool]:
    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    reason = str(payload.get("reason") or "")
    product = payload.get("product_selected") or payload.get("product_id") or payload.get("product")
    price = payload.get("price")
    if price is None:
        price = payload.get("mark_price")
    if price is None:
        price = payload.get("exit_price")
    prev = _read_json_file(DASHBOARD_SNAPSHOT_PATH)
    prev_state = str(prev.get("state") or "")
    regime = (
        payload.get("v4_selected_regime")
        or payload.get("v4_regime")
        or payload.get("regime")
        or prev.get("regime")
    )
    confluence_score = (
        payload.get("v4_selected_score")
        if payload.get("v4_selected_score") is not None
        else payload.get("confluence_score")
    )
    if confluence_score is None:
        confluence_score = payload.get("confluence_count")
    ev_estimate = payload.get("ev")
    if ev_estimate is None and payload.get("ev_usd") is not None:
        ev_estimate = {"ev_usd": payload.get("ev_usd")}

    out = {
        "ts": ts,
        "product": product,
        "price": _to_float(price, None),
        "state": _derive_state(prev_state, reason, payload),
        "regime": regime,
        "gates_pass": payload.get("gates_pass"),
        "gate_reasons": _gate_reasons(payload),
        "entry_signal": payload.get("entry_signal"),
        "direction": payload.get("direction"),
        "gates": payload.get("gates"),
        "confluences": payload.get("confluences"),
        "confluence_count": payload.get("confluence_count"),
        "breakout_type": payload.get("breakout_type"),
        "trades_today": payload.get("trades_today"),
        "losses_today": payload.get("losses_today"),
        "pnl_today_usd": payload.get("pnl_today_usd"),
        "transfers_today_usd": payload.get("transfers_today_usd"),
        "conversion_cost_today_usd": payload.get("conversion_cost_today_usd"),
        "active_mr": payload.get("active_mr"),
        "mr_intraday": payload.get("mr_intraday"),
        "mr_overnight": payload.get("mr_overnight"),
        "maintenance_margin_requirement": payload.get("maintenance_margin_requirement"),
        "total_funds_for_margin": payload.get("total_funds_for_margin"),
        "liquidation_price": payload.get("liquidation_price"),
        "dist_to_liq": payload.get("dist_to_liq"),
        "rescue_count": payload.get("rescue_count"),
        "scale_count": payload.get("scale_count"),
        "confluence_score": confluence_score,
        "ev_estimate": ev_estimate,
        "last_action": _action_from_reason(reason, payload),
        "last_cash_movement": payload.get("last_cash_movement"),
        "thought": payload.get("thought"),
        "entry_time": payload.get("entry_time"),
        "exit_time": payload.get("exit_time"),
        "time_in_trade_min": payload.get("time_in_trade_min"),
        "wait_since_last_exit_min": payload.get("wait_since_last_exit_min"),
        "wait_since_last_entry_min": payload.get("wait_since_last_entry_min"),
        "max_trades_per_day": payload.get("max_trades_per_day"),
        # Existing fields needed by dashboard but previously missing from snapshot
        "v4_score_long": payload.get("v4_score_long"),
        "v4_score_short": payload.get("v4_score_short"),
        "v4_selected_threshold": payload.get("v4_selected_threshold"),
        "v4_regime": payload.get("v4_selected_regime") or payload.get("v4_regime"),
        "lane": payload.get("lane"),
        "lane_label": payload.get("lane_label"),
        "lane_reason": payload.get("lane_reason"),
        "lane_atr_bypassed": payload.get("lane_atr_bypassed"),
        "lane_distance_bypassed": payload.get("lane_distance_bypassed"),
        "sweep_detected": payload.get("sweep_detected"),
        "squeeze_detected": payload.get("squeeze_detected"),
        "compression_range_target": payload.get("compression_range_target"),
        "cooldown": payload.get("cooldown"),
        "overnight_trading_ok": payload.get("overnight_trading_ok"),
        "margin_window": payload.get("margin_window"),
        "vol_phase": payload.get("vol_phase"),
        "vol_direction": payload.get("vol_direction"),
        "htf_readiness": payload.get("htf_readiness"),
        "htf_macro_bias": payload.get("htf_macro_bias"),
        "htf_micro_flags": payload.get("htf_micro_flags"),
        "zone_bonus": payload.get("zone_bonus"),
        "zone_bonus_reasons": payload.get("zone_bonus_reasons"),
        "alignment_bonus": payload.get("alignment_bonus"),
        "alignment_reasons": payload.get("alignment_reasons"),
        "lane_weights_used": payload.get("lane_weights_used"),
        "v4_adx_15m": payload.get("v4_adx_15m"),
        # Per-direction diagnostic state
        "entry_type_long": payload.get("entry_type_long"),
        "entry_type_short": payload.get("entry_type_short"),
        "v4_threshold_long": payload.get("v4_threshold_long"),
        "v4_threshold_short": payload.get("v4_threshold_short"),
        "v4_pass_long": payload.get("v4_pass_long"),
        "v4_pass_short": payload.get("v4_pass_short"),
        "lane_long": payload.get("lane_long"),
        "lane_long_label": payload.get("lane_long_label"),
        "lane_long_reason": payload.get("lane_long_reason"),
        "lane_short": payload.get("lane_short"),
        "lane_short_label": payload.get("lane_short_label"),
        "lane_short_reason": payload.get("lane_short_reason"),
        "candidate_long_pass": payload.get("candidate_long_pass"),
        "candidate_short_pass": payload.get("candidate_short_pass"),
        "long_block_reason": payload.get("long_block_reason"),
        "short_block_reason": payload.get("short_block_reason"),
        "quality_tier": payload.get("quality_tier"),
        "v4_long_missing_pts": payload.get("v4_long_missing_pts"),
        "v4_short_missing_pts": payload.get("v4_short_missing_pts"),
        "long_unlock_hints": payload.get("long_unlock_hints"),
        "short_unlock_hints": payload.get("short_unlock_hints"),
        "next_play_long": payload.get("next_play_long"),
        "next_play_short": payload.get("next_play_short"),
        "route_tier": payload.get("route_tier"),
        "vwap_price": payload.get("vwap_price"),
        "vwap_side": payload.get("vwap_side"),
        "fvg_detail": payload.get("fvg_detail"),
        "channel_detail": payload.get("channel_detail"),
        "vol_confidence": payload.get("vol_confidence"),
        "vol_reasons": payload.get("vol_reasons"),
        # Position fields (from open_position_tick)
        "entry_price": payload.get("entry_price"),
        "pnl_pct": payload.get("pnl_pct"),
        "pnl_usd_live": payload.get("pnl_usd_live"),
        "size": payload.get("size"),
        "leverage": payload.get("leverage"),
        "max_unrealized_usd": payload.get("max_unrealized_usd"),
        "giveback_usd": payload.get("giveback_usd"),
        "contract_size": payload.get("contract_size"),
        "mark_price": payload.get("mark_price"),
        "spot_price": payload.get("spot_price"),
        "equity_start_usd": payload.get("equity_start_usd"),
        "last_spot_cash_map": payload.get("last_spot_cash_map"),
        "reconcile_status": payload.get("reconcile_status"),
        "safe_mode": payload.get("safe_mode"),
        "spot_usdc": payload.get("spot_usdc"),
        "spot_usd": payload.get("spot_usd"),
        "derivatives_usdc": payload.get("derivatives_usdc"),
        "drift_count_today": payload.get("drift_count_today"),
    }
    append_series = _to_float(price, None) is not None
    return out, append_series


def log_decision(config: dict, payload: dict) -> None:
    logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
    path = _resolve_output_path(logging_cfg.get("decisions_jsonl", "decisions.jsonl"), LOGS_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    base_payload = dict(payload or {}) if isinstance(payload, dict) else {"message": str(payload)}
    if not str(base_payload.get("thought") or "").strip():
        base_payload["thought"] = _decision_thought(base_payload)
    safe_payload = _json_safe(base_payload)
    with open(path, "a") as f:
        f.write(json.dumps(safe_payload) + "\n")
    try:
        upd, append_series = _dashboard_update_from_decision(safe_payload if isinstance(safe_payload, dict) else {})
        _update_dashboard_feed(upd, append_timeseries=append_series)
    except Exception:
        pass
    try:
        feature_store.record_snapshot(safe_payload if isinstance(safe_payload, dict) else {}, event_type="decision")
    except Exception:
        pass
    # Slack live feed reports (dashboard replacement)
    try:
        _state_for_reports = load_state()
        _ctx = safe_payload if isinstance(safe_payload, dict) else {}
        _slack_reports.maybe_send_reports(_state_for_reports, config, _ctx)
    except Exception:
        pass  # Never let reporting crash the bot


def log_margin_policy(payload: dict) -> None:
    """High-cadence log (separate from decisions.jsonl to avoid drowning signal history)."""
    path = LOGS_DIR / "margin_policy.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _json_safe(payload)
    with open(path, "a") as f:
        f.write(json.dumps(safe_payload) + "\n")
    try:
        if isinstance(safe_payload, dict):
            _update_dashboard_feed(
                {
                    "ts": safe_payload.get("timestamp"),
                    "margin_tier": safe_payload.get("tier"),
                    "active_mr": safe_payload.get("active_mr"),
                    "mr_intraday": safe_payload.get("mr_intraday"),
                    "mr_overnight": safe_payload.get("mr_overnight"),
                    "maintenance_margin_requirement": safe_payload.get("maintenance_margin_requirement"),
                    "total_funds_for_margin": safe_payload.get("total_funds_for_margin"),
                },
                append_timeseries=False,
            )
    except Exception:
        pass


def log_plrl3(payload: dict) -> None:
    path = LOGS_DIR / "plrl3.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(_json_safe(payload)) + "\n")


def log_incident(payload: dict) -> None:
    path = LOGS_DIR / "incidents.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _json_safe(payload)
    with open(path, "a") as f:
        f.write(json.dumps(safe_payload) + "\n")
    try:
        if isinstance(safe_payload, dict):
            incident_id = f"{safe_payload.get('timestamp') or datetime.now(timezone.utc).isoformat()}::{safe_payload.get('type') or 'INCIDENT'}"
            _update_dashboard_feed(
                {
                    "ts": safe_payload.get("timestamp"),
                    "last_incident": safe_payload,
                    "incident_ref": incident_id,
                },
                append_timeseries=False,
            )
    except Exception:
        pass


def log_fill(payload: dict) -> None:
    path = LOGS_DIR / "fills.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(_json_safe(payload)) + "\n")


def log_signal(payload: dict) -> None:
    """Log intent/simulation entries that were NOT confirmed as exchange fills."""
    path = LOGS_DIR / "signals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = _json_safe(payload if isinstance(payload, dict) else {"message": str(payload)})
    if isinstance(safe, dict) and not safe.get("timestamp"):
        safe["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(path, "a") as f:
        f.write(json.dumps(safe) + "\n")


def log_market_news(payload: dict) -> None:
    path = MARKET_NEWS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _json_safe(payload if isinstance(payload, dict) else {"message": str(payload)})
    if isinstance(safe_payload, dict) and not safe_payload.get("timestamp"):
        safe_payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(path, "a") as f:
        f.write(json.dumps(safe_payload) + "\n")
    try:
        if isinstance(safe_payload, dict):
            _update_dashboard_feed(
                {
                    "ts": safe_payload.get("fetched_at") or safe_payload.get("timestamp"),
                    "market_news": safe_payload,
                    "market_news_ts": safe_payload.get("fetched_at") or safe_payload.get("timestamp"),
                    "market_news_summary": safe_payload.get("summary"),
                    "market_news_risk_flags": safe_payload.get("risk_flags"),
                },
                append_timeseries=False,
            )
    except Exception:
        pass


def _market_news_digest_bullets(intel: dict, max_items: int = 5) -> list[str]:
    out: list[str] = []
    if not isinstance(intel, dict):
        return out
    prices = intel.get("prices") if isinstance(intel.get("prices"), dict) else {}
    macro = intel.get("macro") if isinstance(intel.get("macro"), dict) else {}
    oi_proxy = intel.get("oi_proxy") if isinstance(intel.get("oi_proxy"), dict) else {}

    btc = _to_float(prices.get("btc_usd"), None)
    btc_24 = _to_float(prices.get("btc_24h_pct"), None)
    xlm = _to_float(prices.get("xlm_usd"), None)
    xlm_24 = _to_float(prices.get("xlm_24h_pct"), None)
    if btc is not None and xlm is not None:
        _line = f"BTC ${btc:,.0f}"
        if btc_24 is not None:
            _line += f" ({btc_24:+.2f}% 24h)"
        _line += f" | XLM ${xlm:.4f}"
        if xlm_24 is not None:
            _line += f" ({xlm_24:+.2f}% 24h)"
        out.append(_line)

    spx = _to_float((macro.get("spx") or {}).get("close"), None)
    ndx = _to_float((macro.get("ndx") or {}).get("close"), None)
    gold = _to_float((macro.get("gold") or {}).get("close"), None)
    if spx is not None or ndx is not None or gold is not None:
        parts: list[str] = []
        if spx is not None:
            parts.append(f"SPX {spx:,.1f}")
        if ndx is not None:
            parts.append(f"NDX {ndx:,.1f}")
        if gold is not None:
            parts.append(f"Gold {gold:,.1f}")
        out.append(" | ".join(parts))

    okx_oi = _to_float((oi_proxy.get("okx") or {}).get("value"), None)
    okx_chg = _to_float((oi_proxy.get("okx") or {}).get("change_pct"), None)
    if okx_oi is not None:
        oi_line = f"OKX OI {okx_oi:,.0f}"
        if okx_chg is not None:
            oi_line += f" ({okx_chg:+.1f}%)"
        out.append(oi_line)

    headlines = intel.get("headlines") if isinstance(intel.get("headlines"), list) else []
    for h in headlines[: max(0, int(max_items))]:
        if not isinstance(h, dict):
            continue
        title = str(h.get("title") or "").strip()
        if not title:
            continue
        source = str(h.get("source") or "").strip()
        out.append(f"{title[:130]}{(' - ' + source) if source else ''}")
        if len(out) >= max_items:
            break
    return out[: max(0, int(max_items))]


EQUITY_SERIES_PATH = LOGS_DIR / "equity_series.jsonl"


def _log_equity_tick(equity_usd: float, mark_price: float, state: dict,
                     portfolio_usd: float = 0.0) -> None:
    """Append equity + price snapshot to equity_series.jsonl every cycle."""
    try:
        _st = "IN_TRADE" if state.get("open_position") else "IDLE"
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "equity": round(equity_usd, 2),
            "portfolio": round(portfolio_usd, 2) if portfolio_usd > 0 else round(equity_usd, 2),
            "mark_price": round(mark_price, 6) if mark_price else 0,
            "pnl_today": round(float(state.get("pnl_today_usd") or 0), 2),
            "state": _st,
        }
        EQUITY_SERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EQUITY_SERIES_PATH, "a") as f:
            f.write(json.dumps(_json_safe(row), default=str) + "\n")
    except Exception:
        pass


def verify_fill(api, order_id: str) -> dict | None:
    """
    Check if order_id actually filled on Coinbase.
    Returns dict with fill details or None if not filled / error.
    """
    if not order_id:
        return None
    try:
        resp = api.get_order(order_id)
        if not resp:
            return None
        order = resp.get("order", resp)
        status = str(order.get("status") or "").upper()
        if status != "FILLED":
            return {"status": status, "filled": False, "order_id": order_id}
        filled_size = float(order.get("filled_size") or order.get("filled_value") or 0)
        avg_price = float(order.get("average_filled_price") or 0)
        total_fees = float(order.get("total_fees") or 0)
        completion = order.get("completion_percentage")
        return {
            "filled": True,
            "order_id": order_id,
            "status": status,
            "filled_size": filled_size,
            "average_filled_price": avg_price,
            "total_fees": total_fees,
            "completion_percentage": completion,
        }
    except Exception:
        return None


def _build_entry_preflight_snapshot(
    config: dict,
    api,
    *,
    product_id: str,
    direction: str,
    size: int,
    entry_price: float,
    stop_loss: float | None,
    take_profit: float | None,
    attach_exchange_tp: bool,
) -> dict:
    stop_loss = float(stop_loss or 0.0)
    take_profit = float(take_profit or 0.0) if take_profit is not None else None
    entry_price = float(entry_price or 0.0)
    bracket_valid = bool(
        entry_price > 0
        and (
            (direction == "long" and stop_loss > 0 and stop_loss < entry_price and (take_profit is None or take_profit > entry_price))
            or (direction == "short" and stop_loss > entry_price and (take_profit is None or take_profit < entry_price))
        )
    )
    spread_pct = None
    margin = {}
    margin_window = None
    try:
        spread_pct = api.get_spread_pct(product_id)
    except Exception:
        spread_pct = None
    try:
        margin = api.estimate_required_margin(product_id, size=max(int(size), 1), direction=direction, price=entry_price) or {}
        margin_window = margin.get("margin_window")
    except Exception:
        margin = {}
        margin_window = None
    spread_limit = None
    try:
        spread_limit = float(((config.get("regime_gates") or {}).get("spread_max_pct")) or 0.0)
    except Exception:
        spread_limit = None
    spread_ok = True if spread_pct is None or not spread_limit or spread_limit <= 0 else float(spread_pct) <= float(spread_limit)
    reason = "ok"
    if int(size or 0) <= 0:
        reason = "invalid_size"
    elif entry_price <= 0:
        reason = "invalid_entry_price"
    elif not bracket_valid:
        reason = "invalid_bracket_geometry"
    elif not spread_ok:
        reason = "spread_too_wide"
    return {
        "ok": reason == "ok",
        "reason": reason,
        "direction": direction,
        "size": int(size or 0),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "attach_exchange_tp": bool(attach_exchange_tp),
        "bracket_valid": bracket_valid,
        "spread_pct": spread_pct,
        "spread_limit_pct": spread_limit,
        "spread_ok": spread_ok,
        "required_margin": margin.get("required_margin"),
        "margin_rate": margin.get("margin_rate"),
        "margin_window": margin_window,
        "notional": margin.get("notional"),
    }


def _inspect_entry_protection(api, *, product_id: str, order_id: str | None, attach_exchange_tp: bool, order_message: str = "") -> dict:
    mode = "software_managed"
    reason = "software_tp_only"
    exchange_tp_armed = False
    degraded = False
    attached = None
    if attach_exchange_tp:
        mode = "exchange_bracket_requested"
        reason = "exchange_bracket_requested"
        if "plain_fallback_no_bracket" in str(order_message or ""):
            mode = "software_fallback"
            reason = "bracket_rejected_plain_fallback"
            degraded = True
        elif order_id:
            try:
                payload = api.get_order(order_id) or {}
                order = payload.get("order", payload)
                attached = order.get("attached_order_configuration") or {}
                if attached:
                    exchange_tp_armed = True
                    mode = "exchange_bracket"
                    reason = "attached_order_configuration_present"
                else:
                    mode = "exchange_bracket_unverified"
                    reason = "attached_order_configuration_missing"
                    degraded = True
            except Exception:
                mode = "exchange_bracket_unverified"
                reason = "protection_inspection_failed"
                degraded = True
    return {
        "mode": mode,
        "reason": reason,
        "exchange_tp_requested": bool(attach_exchange_tp),
        "exchange_tp_armed": bool(exchange_tp_armed),
        "software_protection_active": not bool(exchange_tp_armed),
        "degraded": bool(degraded),
        "attached_order_configuration": attached if isinstance(attached, dict) and attached else None,
    }


def _materialize_pending_fill_position(pending_meta: dict, *, fill_price: float, fees_usd: float) -> dict | None:
    if not isinstance(pending_meta, dict):
        return None
    seed = pending_meta.get("open_position_seed")
    if not isinstance(seed, dict):
        return None
    restored = dict(seed)
    if float(fill_price or 0.0) > 0:
        restored["entry_price"] = float(fill_price)
    restored["entry_fees_usd"] = float(fees_usd or 0.0)
    restored["entry_fill_verified"] = True
    restored["pending_fill_recovered"] = True
    restored["pending_fill_recovered_at"] = datetime.now(timezone.utc).isoformat()
    return restored


def _verify_position_closed(api, product_id: str, max_retries: int = 3, delay: float = 1.0) -> bool:
    """Verify the position is actually closed on the exchange.

    Calls get_position() up to max_retries times with delay between.
    Returns True only if position size is confirmed 0 or position doesn't exist.
    """
    import time as _time
    for attempt in range(max_retries):
        if attempt > 0:
            _time.sleep(delay)
        try:
            pos = api.get_position(product_id)
            if pos is None:
                return True  # Position not found = closed
            pos_size = abs(float(pos.get("number_of_contracts") or pos.get("size") or 0))
            if pos_size == 0:
                return True
        except Exception:
            continue  # API error — retry
    return False  # Still open after all retries


def _force_flatten_position(api, product_id: str, max_rounds: int = 3) -> dict:
    """Slippage-resilient exit ladder until exchange confirms position=0.

    Strategy per round:
      1. Get exchange position size + order book best bid/ask
      2. Place LIMIT order at best price (aggressive side)
      3. Wait, check fill. If not filled, walk price 3 ticks toward market.
      4. If still not filled after limit ladder, fall back to MARKET close.
      5. Verify position=0. Repeat if not flat.

    Returns dict with:
      - flat: True if position confirmed closed
      - attempts: number of rounds
      - close_info: info from market fallback (if used)
      - order_id: order_id from the successful close
      - method: "limit", "limit_walked", or "market"
    """
    import time as _time
    result = {"flat": False, "attempts": 0, "close_info": None, "order_id": None, "method": None}

    def _extract_oid(res):
        """Extract order_id from API response."""
        if not res:
            return None
        # Direct success_response path
        oid = (res.get("success_response") or {}).get("order_id")
        if oid:
            return str(oid)
        # order_id at top level
        oid = res.get("order_id")
        if oid:
            return str(oid)
        return None

    def _get_exchange_position():
        """Get current position size and side from exchange."""
        try:
            pos = api.get_position(product_id)
            if pos is None:
                return 0, ""
            size = abs(float(pos.get("number_of_contracts") or pos.get("size") or 0))
            side_raw = str(pos.get("side") or "").lower()
            return size, side_raw
        except Exception:
            return -1, ""  # -1 = API error

    def _get_best_prices():
        """Get best bid and ask from order book."""
        try:
            book = api.api.get_orderbook(product_id) or {}
            # Handle both wrapped and unwrapped formats
            pricebook = book.get("pricebook") or book
            bids = pricebook.get("bids") or []
            asks = pricebook.get("asks") or []
            best_bid = float(bids[0]["price"]) if bids else None
            best_ask = float(asks[0]["price"]) if asks else None
            return best_bid, best_ask
        except Exception:
            return None, None

    for round_num in range(max_rounds):
        result["attempts"] = round_num + 1

        # Check if already flat
        size, side_raw = _get_exchange_position()
        if size == 0:
            result["flat"] = True
            return result
        if size < 0:
            # API error — brief wait and retry
            _time.sleep(0.5)
            continue

        # Determine close side (opposite of position)
        is_short = "short" in side_raw or "sell" in side_raw
        close_side = "BUY" if is_short else "SELL"

        # Cancel any hanging orders first
        try:
            api.cancel_open_orders(product_id=product_id)
        except Exception:
            pass
        _time.sleep(0.2)

        # ── STEP 1: Limit order at best price ──
        best_bid, best_ask = _get_best_prices()
        limit_filled = False
        last_oid = None

        if best_bid and best_ask:
            # Aggressive limit: if buying to close, start at best_ask (taker)
            # If selling to close, start at best_bid (taker)
            base_price = best_ask if close_side == "BUY" else best_bid
            # Tick size: ~0.02% of price per step
            tick = base_price * 0.0002

            for step in range(4):  # Initial + 3 walks
                # Cancel previous attempt
                if last_oid:
                    try:
                        api.api.cancel_order(last_oid)
                    except Exception:
                        pass
                    _time.sleep(0.2)

                # Walk price toward market on each step
                if close_side == "BUY":
                    limit_price = base_price + (tick * step)  # Pay more to close short
                else:
                    limit_price = base_price - (tick * step)  # Accept less to close long

                try:
                    res = api.api.place_cfm_order(
                        product_id=product_id,
                        side=close_side,
                        base_size=size,
                        price=limit_price,
                        reduce_only=False,  # CDE doesn't support reduce_only
                    )
                    last_oid = _extract_oid(res)
                    if last_oid:
                        result["order_id"] = last_oid
                except Exception:
                    last_oid = None

                # Wait for fill
                _wait = 1.5 if step == 0 else 1.0
                _time.sleep(_wait)

                # Check fill
                if last_oid:
                    try:
                        fill = api.verify_order_fill(last_oid)
                        if fill and fill.get("filled"):
                            limit_filled = True
                            result["method"] = "limit" if step == 0 else "limit_walked"
                            break
                    except Exception:
                        pass

            # Cancel last limit if not filled
            if not limit_filled and last_oid:
                try:
                    api.api.cancel_order(last_oid)
                except Exception:
                    pass
                _time.sleep(0.2)

        # Check if limit worked
        if limit_filled:
            if _verify_position_closed(api, product_id, max_retries=2, delay=0.3):
                result["flat"] = True
                return result
            # Partial fill — continue to next round
            continue

        # ── STEP 2: Market fallback ──
        try:
            close_info = api.close_cfm_position(product_id, paper=False)
            result["close_info"] = close_info
            try:
                oid = ((close_info or {}).get("result") or {}).get("order_id")
                if oid:
                    result["order_id"] = oid
                    result["method"] = "market"
            except Exception:
                pass
        except Exception:
            result["close_info"] = {"ok": False, "error": "market_fallback_exception"}

        _time.sleep(1.5)

        if _verify_position_closed(api, product_id, max_retries=2, delay=0.5):
            result["flat"] = True
            return result

    return result  # Still not flat after all rounds


def log_cash_movement(payload: dict) -> None:
    path = CASH_MOVEMENTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _json_safe(payload if isinstance(payload, dict) else {"message": str(payload)})
    if isinstance(safe_payload, dict) and not safe_payload.get("timestamp"):
        safe_payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(path, "a") as f:
        f.write(json.dumps(safe_payload) + "\n")
    try:
        if isinstance(safe_payload, dict):
            _update_dashboard_feed(
                {
                    "ts": safe_payload.get("timestamp"),
                    "last_cash_movement": safe_payload,
                    "transfers_today_usd": safe_payload.get("transfers_today_usd"),
                    "conversion_cost_today_usd": safe_payload.get("conversion_cost_today_usd"),
                },
                append_timeseries=False,
            )
    except Exception:
        pass


def _funding_preferences(funding_cfg: dict) -> list[str]:
    requested = str((funding_cfg or {}).get("currency", "USDC") or "USDC").strip().upper()
    prefs: list[str] = []
    for c in [requested] + list((funding_cfg or {}).get("preferred_currencies") or []) + ["USD", "USDC"]:
        cc = str(c or "").strip().upper()
        if cc and cc not in prefs:
            prefs.append(cc)
    return prefs


def _record_funding_outcome(
    *,
    config: dict,
    state: dict,
    durable: StateStore | None,
    now: datetime,
    context: str,
    margin_ok: bool,
    margin_info: dict | None,
) -> None:
    info = margin_info if isinstance(margin_info, dict) else {}
    reason = str(info.get("reason") or "")
    attempted = bool(info.get("transfer_attempted"))
    success = bool(info.get("transfer_result"))
    amount = float(info.get("transferable") or 0.0)
    conversion_est = float(info.get("estimated_conversion_cost_usd") or 0.0)
    needed_total = _to_float(info.get("needed_total"), 0.0) or 0.0
    bp_post = _to_float(info.get("futures_buying_power_post_transfer"), None)
    if bp_post is None:
        bp_post = _to_float(info.get("futures_buying_power"), 0.0) or 0.0
    shortfall = max(0.0, float(needed_total) - float(bp_post))

    if attempted and success and amount > 0:
        state["transfers_today_usd"] = float(state.get("transfers_today_usd") or 0.0) + amount
    if conversion_est > 0:
        state["conversion_cost_today_usd"] = float(state.get("conversion_cost_today_usd") or 0.0) + conversion_est

    if attempted and success:
        ev_type = "SPOT_TO_FUTURES_TRANSFER"
    elif attempted and not success:
        ev_type = "SPOT_TO_FUTURES_TRANSFER_FAILED"
    elif reason == "sufficient_buying_power":
        ev_type = "FUNDING_NO_TRANSFER_NEEDED"
    elif not margin_ok:
        ev_type = "FUNDING_SHORTFALL"
    else:
        ev_type = "FUNDING_CHECK"

    movement = {
        "timestamp": now.isoformat(),
        "type": ev_type,
        "context": str(context or "entry"),
        "ok": bool(margin_ok),
        "reason": reason,
        "amount_usd": amount,
        "currency": info.get("chosen_currency") or info.get("requested_currency") or info.get("currency"),
        "transfer_direction": info.get("transfer_direction") or "spot_to_futures",
        "needed_total": needed_total,
        "futures_buying_power": info.get("futures_buying_power"),
        "futures_buying_power_post_transfer": bp_post,
        "shortfall_usd": shortfall,
        "spot_cash_by_currency": info.get("spot_cash_by_currency"),
        "transfer_candidates": info.get("transfer_candidates"),
        "transfer_response": info.get("transfer_response"),
        "estimated_conversion_cost_usd": conversion_est,
        "conversion_cost_bps": info.get("conversion_cost_bps"),
        "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
        "conversion_cost_today_usd": float(state.get("conversion_cost_today_usd") or 0.0),
    }
    log_cash_movement(movement)
    try:
        if durable is not None:
            durable.log_event("cash_movement", movement)
    except Exception:
        pass

    decision_reason = None
    if ev_type == "SPOT_TO_FUTURES_TRANSFER":
        decision_reason = "funding_transfer"
    elif ev_type in ("SPOT_TO_FUTURES_TRANSFER_FAILED", "FUNDING_SHORTFALL"):
        decision_reason = "funding_shortfall"
    if decision_reason:
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": decision_reason,
                "context": context,
                "ok": bool(margin_ok),
                "margin_info": info,
                "amount_usd": amount,
                "currency": movement.get("currency"),
                "shortfall_usd": shortfall,
                "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
                "conversion_cost_today_usd": float(state.get("conversion_cost_today_usd") or 0.0),
                "last_cash_movement": movement,
            },
        )


def _observe_spot_balance_changes(
    *,
    config: dict,
    state: dict,
    api: CoinbaseAdvanced,
    durable: StateStore | None,
    now: datetime,
) -> None:
    funding_cfg = (config.get("futures_funding") or {}) if isinstance(config.get("futures_funding"), dict) else {}
    monitor = funding_cfg.get("monitor_currencies")
    if not isinstance(monitor, list) or not monitor:
        monitor = ["USD", "USDC"]
    currencies: list[str] = []
    for c in monitor:
        cc = str(c or "").strip().upper()
        if cc and cc not in currencies:
            currencies.append(cc)
    if not currencies:
        return
    delta_min = float(funding_cfg.get("balance_delta_alert_usd", 0.50) or 0.50)
    try:
        current = api.get_spot_cash_map(currencies)
    except Exception:
        return
    previous = state.get("last_spot_cash_map") if isinstance(state.get("last_spot_cash_map"), dict) else {}
    if not previous:
        state["last_spot_cash_map"] = current
        return

    deltas: dict[str, float] = {}
    for cc in currencies:
        d = float(current.get(cc, 0.0) or 0.0) - float(previous.get(cc, 0.0) or 0.0)
        if abs(d) >= max(0.0, delta_min):
            deltas[cc] = round(d, 8)
    state["last_spot_cash_map"] = current
    if not deltas:
        return

    positives = [v for v in deltas.values() if v > 0]
    negatives = [v for v in deltas.values() if v < 0]
    ev_type = "SPOT_CONVERSION_DETECTED" if positives and negatives else "SPOT_BALANCE_DELTA"
    event = {
        "timestamp": now.isoformat(),
        "type": ev_type,
        "context": "account_observer",
        "reason": "spot_balance_change",
        "deltas": deltas,
        "spot_cash_before": previous,
        "spot_cash_after": current,
        "threshold": delta_min,
        "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
        "conversion_cost_today_usd": float(state.get("conversion_cost_today_usd") or 0.0),
    }
    log_cash_movement(event)
    try:
        if durable is not None:
            durable.log_event("cash_movement", event)
    except Exception:
        pass
    log_decision(
        config,
        {
            "timestamp": now.isoformat(),
            "reason": "spot_balance_delta",
            "deltas": deltas,
            "last_cash_movement": event,
        },
    )


def _run_balance_reconcile(
    *,
    config: dict,
    state: dict,
    api: "CoinbaseAdvanced",
    durable: "StateStore | None",
    now: datetime,
    mode: str = "IDLE",
    required_margin: float = 0.0,
) -> ReconcileResult | None:
    """Run balance reconciliation cycle with logging."""
    recon_cfg = config.get("balance_reconciliation", {}) or {}
    if not recon_cfg.get("enabled", False):
        return None

    # Sweep cooldown: if the last sweep failed, don't retry for 5 min.
    # Prevents wasting 6+ API calls/min on transfers the exchange keeps rejecting.
    _sweep_fail_ts = state.get("_last_sweep_fail_ts")
    if _sweep_fail_ts and mode == "IDLE":
        try:
            from datetime import timezone as _tz
            _fail_dt = datetime.fromisoformat(str(_sweep_fail_ts))
            if (now - _fail_dt).total_seconds() < 300:  # 5 min cooldown
                return None
        except Exception:
            pass

    try:
        result = _reconcile_balances(
            api, config=config, state=state, mode=mode, now=now,
            required_margin=required_margin,
        )
        # Belt-and-suspenders: if SAFE_MODE was triggered by sweep failures
        # (should no longer happen after reconciler fix), suppress it anyway.
        if result.safe_mode and result.safe_mode_reason and "transfer_failed" in result.safe_mode_reason:
            if mode in ("POST_EXIT", "IDLE"):
                result.safe_mode = False
                result.safe_mode_reason = None
                result.status = "SWEEP_DEFERRED"
                state["_safe_mode"] = False
                state.pop("_safe_mode_reason", None)

        # Track sweep failures for cooldown — avoid retrying every 30s
        _sweep_failed = any(
            a.get("action") == "SWEEP_TO_SPOT" and not a.get("ok")
            for a in result.actions_taken
        )
        # Also cooldown on "sweep_already_pending" (returns ok=True but sweep
        # is not complete yet -- without this the reconciler loops every cycle).
        _sweep_pending = any(
            a.get("action") == "SWEEP_TO_SPOT" and a.get("ok")
            and a.get("response") in ("sweep_already_pending", "sweep_check_failed_assume_pending")
            for a in result.actions_taken
        )
        if _sweep_failed or _sweep_pending:
            state["_last_sweep_fail_ts"] = now.isoformat()
        elif any(a.get("action") == "SWEEP_TO_SPOT" and a.get("ok") for a in result.actions_taken):
            state.pop("_last_sweep_fail_ts", None)  # clear on true success only

        # Log if drift detected or verbose mode
        _drift_list = (result.drift.drifts if result.drift else []) or []
        has_drift = bool(_drift_list)
        log_every = bool(recon_cfg.get("log_every_cycle", False))
        if has_drift or log_every or result.safe_mode:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "balance_reconcile",
                "reconcile_mode": mode,
                "reconcile_status": result.status,
                "safe_mode": result.safe_mode,
                "safe_mode_reason": result.safe_mode_reason,
                "drifts": list(_drift_list),
                "actions_taken": result.actions_taken,
                "spot_usdc": result.snapshot.spot_usdc,
                "spot_usd": result.snapshot.spot_usd,
                "derivatives_usdc": result.snapshot.derivatives_usdc,
                "thought": _reconcile_thought(result),
            })
        if durable and has_drift:
            durable.log_event("balance_reconcile", {
                "mode": mode,
                "status": result.status,
                "drifts": len(_drift_list),
                "actions": len(result.actions_taken),
                "safe_mode": result.safe_mode,
            })
        return result
    except Exception:
        return None


def _reconcile_thought(result: ReconcileResult) -> str:
    if result.safe_mode:
        return f"SAFE MODE: {result.safe_mode_reason}"
    _drift_items = (result.drift.drifts if result.drift else []) or []
    if not _drift_items:
        return f"balances OK ({result.mode})"
    types = [d.get("type", "?") for d in _drift_items]
    actions = [a.get("action", "?") for a in result.actions_taken if a.get("ok")]
    parts = f"drift: {', '.join(types)}"
    if actions:
        parts += f", fixed: {', '.join(actions)}"
    return parts


def _sweep_derivatives_to_spot(
    *,
    config: dict,
    state: dict,
    api: "CoinbaseAdvanced",
    durable: "StateStore | None",
    now: datetime,
    context: str = "idle_sweep",
) -> bool:
    """Sweep derivatives balance back to spot USDC so idle funds earn yield."""
    # Respect sweep cooldown from reconciler — don't double-hammer the API
    _sweep_fail_ts = state.get("_last_sweep_fail_ts")
    if _sweep_fail_ts and context != "post_exit_sweep":
        try:
            _fail_dt = datetime.fromisoformat(str(_sweep_fail_ts))
            if (now - _fail_dt).total_seconds() < 300:
                return False
        except Exception:
            pass

    funding_cfg = config.get("futures_funding", {}) or {}
    sweep_cfg = funding_cfg.get("idle_sweep", {}) or {}
    if not sweep_cfg.get("enabled", False):
        return False
    min_sweep = float(sweep_cfg.get("min_sweep_usd", 5) or 5)
    currency = str(funding_cfg.get("currency", "USDC") or "USDC").strip().upper()
    try:
        # Use actual derivatives wallet balance (cfm_usd_balance), NOT buying power.
        # Buying power includes cross-margin from spot and overstates what's sweepable.
        _inner = getattr(api, "api", api)
        _bs = api.get_futures_balance_summary() or {}
        _root = _bs.get("balance_summary", {}) if isinstance(_bs, dict) else {}
        _cfm = _root.get("cfm_usd_balance") if isinstance(_root, dict) else None
        if _cfm is not None:
            bp = float(_cfm.get("value", 0) if isinstance(_cfm, dict) else _cfm)
        else:
            bp = float(_inner.get_cfm_buying_power() or 0)
    except Exception:
        return False
    if bp < min_sweep:
        return False
    # Keep a small buffer in derivatives for any pending settlement
    sweep_amt = round(bp - 2.0, 2)
    if sweep_amt < min_sweep:
        return False
    try:
        tx = api.transfer_futures_profit(sweep_amt, currency=currency)
        ok = bool((tx or {}).get("ok"))
        move = {
            "timestamp": now.isoformat(),
            "type": "IDLE_SWEEP_TO_SPOT" if ok else "IDLE_SWEEP_FAILED",
            "context": context,
            "ok": ok,
            "reason": (tx or {}).get("reason"),
            "amount_usd": float(sweep_amt),
            "currency": currency,
            "transfer_direction": "futures_to_spot",
            "derivatives_balance_before": bp,
            "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
        }
        log_cash_movement(move)
        if durable:
            durable.log_event("cash_movement", move)
        if ok:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "idle_sweep_to_spot",
                "amount": sweep_amt,
                "currency": currency,
                "derivatives_balance_before": bp,
                "ok": True,
                "last_cash_movement": move,
                "thought": f"swept ${sweep_amt:.2f} from derivatives → spot USDC (yield parking)",
            })
        return ok
    except Exception:
        return False


def log_trade(config: dict, row: dict) -> None:
    logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
    path = _resolve_output_path(logging_cfg.get("trades_csv", "trades.csv"), LOGS_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = _json_safe(row)
    # Feed structured audit logger (war room: everlight_packager)
    try:
        _audit_logger.record_trade(row)
    except Exception:
        pass
    # CSV writer crashes if any key is None/non-string; normalize defensively.
    row = {str(k): v for k, v in row.items() if k not in (None, "")}
    if path.exists():
        # Normalize header if it changed
        with open(path, "r", newline="") as f:
            reader = csv.reader(f)
            raw_header = next(reader, [])
            header = [str(h) for h in raw_header if h not in (None, "")]
            existing_rows = list(csv.DictReader(f, fieldnames=header)) if header else []
        new_fields = list(dict.fromkeys([h for h in header if h] + list(row.keys())))
        if new_fields != header:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=new_fields, extrasaction="ignore")
                writer.writeheader()
                for r in existing_rows:
                    clean_r = {str(k): v for k, v in (r or {}).items() if k not in (None, "")}
                    writer.writerow(clean_r)
                writer.writerow(row)
            try:
                feature_store.record_snapshot(row, event_type="trade")
                feature_store.record_trade_label(row)
            except Exception:
                pass
            return
    with open(path, "a", newline="") as f:
        if path.stat().st_size == 0:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()), extrasaction="ignore")
            writer.writeheader()
            writer.writerow(row)
        else:
            # Re-read the header to ensure columns align (don't use row.keys()
            # which may have different order/subset than the file header).
            f.seek(0)
            with open(path, "r", newline="") as rf:
                existing_header = next(csv.reader(rf), [])
            existing_header = [str(h) for h in existing_header if h not in (None, "")]
            fieldnames = existing_header if existing_header else list(row.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writerow(row)
    try:
        feature_store.record_snapshot(row, event_type="trade")
        feature_store.record_trade_label(row)
    except Exception:
        pass
    # Trade learning: start shadow tracking on completed trades
    try:
        if row.get("exit_price") and row.get("entry_price"):
            trade_reviewer.on_trade_exit(row)
    except Exception:
        pass

    # AI feedback loop: log trade outcome for self-learning
    try:
        if row.get("exit_price") and ai_advisor.is_executive_mode():
            _last_dir = ai_advisor.get_cached_insight("directive") or {}
            if _last_dir:
                duration_min = None
                try:
                    _et = pd.to_datetime(row.get("entry_time"))
                    _xt = pd.to_datetime(row.get("exit_time"))
                    if pd.notna(_et) and pd.notna(_xt):
                        duration_min = int((_xt - _et).total_seconds() / 60)
                except Exception:
                    pass
                ai_advisor.log_directive_outcome(
                    directive=_last_dir,
                    trade_result={
                        "direction": row.get("side"),
                        "entry_price": row.get("entry_price"),
                        "exit_price": row.get("exit_price"),
                        "pnl_usd": row.get("pnl_usd"),
                        "duration_min": duration_min,
                        "exit_reason": row.get("exit_reason"),
                        "max_unrealized": row.get("max_unrealized_usd"),
                    },
                )
    except Exception:
        pass

    # Self-learning hooks: update lane tracker, decision linker, evolution engine
    try:
        if row.get("exit_price") and row.get("entry_type"):
            logging_cfg_sl = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
            _trades_csv = _resolve_output_path(logging_cfg_sl.get("trades_csv", "trades.csv"), LOGS_DIR)
            _lane_perf_path = LOGS_DIR / "lane_performance.json"
            update_lane_performance(str(_trades_csv), str(_lane_perf_path))
            # Decision linker: connect decisions to outcomes
            _decisions_path = _resolve_output_path(
                logging_cfg_sl.get("decisions_jsonl", "decisions.jsonl"), LOGS_DIR
            )
            _outcomes_path = LOGS_DIR / "decision_outcomes.jsonl"
            link_decisions(_decisions_path, _trades_csv, _outcomes_path)
            # Evolution engine: update bandit, weights, thresholds
            _pnl = float(row.get("pnl_usd") or 0)
            _won = _pnl > 0
            _score = int(row.get("confluence_score") or 0)
            _threshold = int(row.get("score_threshold") or row.get("threshold") or 50)
            _entry_type = str(row.get("entry_type") or "")
            _flags = {}  # confluence flags from v4 scoring (if available)
            try:
                _flags_raw = row.get("confluence_flags") or row.get("flags") or "{}"
                if isinstance(_flags_raw, str):
                    import ast
                    _flags = ast.literal_eval(_flags_raw) if _flags_raw.startswith("{") else {}
                elif isinstance(_flags_raw, dict):
                    _flags = _flags_raw
            except Exception:
                pass
            _evo = EvolutionEngine()
            _evo.post_trade_update(
                lane=_entry_type,
                won=_won,
                pnl_usd=_pnl,
                score=_score,
                threshold=_threshold,
                flags_fired=_flags,
            )
    except Exception:
        pass


def _today_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _reset_daily(state: dict, now: datetime) -> tuple[dict, dict | None]:
    key = _today_key(now)
    reset_info = None
    if state.get("day") != key:
        reset_info = {
            "old_day": state.get("day"),
            "new_day": key,
            "prev_pnl": float(state.get("pnl_today_usd") or 0.0),
            "prev_exchange_pnl": float(state.get("exchange_pnl_today_usd") or 0.0),
            "prev_trades": int(state.get("trades") or 0),
            "prev_losses": int(state.get("losses") or 0),
        }
        state["day"] = key
        state["trades"] = 0
        state["losses"] = 0
        state["cooldown_until"] = None
        state["pnl_today_usd"] = 0.0
        state["exchange_pnl_today_usd"] = 0.0
        state["equity_start_usd"] = None
        state["exchange_equity_usd"] = None
        state["transfers_today_usd"] = 0.0
        state["conversion_cost_today_usd"] = 0.0
        state["_reconcile_drift_count_today"] = 0
        state["_shift_summaries_sent"] = {}  # Clear old shift tracking
        state["recovery_mode"] = "NORMAL"
        state["recovery_attempts"] = 0
        state["recovery_start_pnl"] = 0
        state["recovery_cooldown_until"] = None
        # Clear carryover safety flags so each UTC day starts clean.
        state["_safe_mode"] = False
        state.pop("_safe_mode_reason", None)
        state["safe_mode"] = False
        state.pop("safe_mode_reason", None)
        state["post_tp_bias_side"] = ""
        state["post_tp_bias_set_at"] = None
        state["post_tp_bias_trades_since"] = 0
        state.pop("_last_exit_counted_entry", None)  # prevents cross-day double-count guard collision
    return state, reset_info


def _write_daily_brief(config: dict, state: dict, now: datetime) -> None:
    """Write data/daily_brief.json with last 3 days of performance for AI context."""
    try:
        logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
        trades_path = _resolve_output_path(logging_cfg.get("trades_csv", "trades.csv"), LOGS_DIR)
        days: dict = {}
        if trades_path.exists():
            import csv as _csv
            with open(trades_path, newline="") as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    ts = (row.get("timestamp") or "")[:10]
                    if not ts:
                        continue
                    d = days.setdefault(ts, {"wins": 0, "losses": 0, "pnl": 0.0, "max_loss": 0.0, "max_hold_min": 0.0})
                    result = row.get("result", "")
                    pnl = float(row.get("pnl_usd") or 0)
                    hold = float(row.get("hold_minutes") or 0)
                    if result == "win":
                        d["wins"] += 1
                    elif result == "loss":
                        d["losses"] += 1
                        d["max_loss"] = min(d["max_loss"], pnl)
                    d["pnl"] += pnl
                    d["max_hold_min"] = max(d["max_hold_min"], hold)
        sorted_days = sorted(days.items(), reverse=True)[:3]
        last_3 = [
            {
                "date": k,
                "trades": v["wins"] + v["losses"],
                "pnl_usd": round(v["pnl"], 2),
                "max_single_loss_usd": round(v["max_loss"], 2),
                "max_hold_minutes": round(v["max_hold_min"], 0),
                "win_rate_pct": round(v["wins"] / max(1, v["wins"] + v["losses"]) * 100, 1),
            }
            for k, v in sorted_days
        ]
        total_pnl = sum(d["pnl_usd"] for d in last_3)
        posture = "conservative" if total_pnl < -20 else ("normal" if total_pnl < 10 else "aggressive")
        brief = {
            "generated_at": now.isoformat(),
            "last_3_days": last_3,
            "total_3day_pnl_usd": round(total_pnl, 2),
            "equity_trend": "declining" if total_pnl < -10 else ("stable" if total_pnl < 5 else "growing"),
            "suggested_posture": posture,
        }
        out = DATA_DIR / "daily_brief.json"
        tmp = str(out) + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(brief, fh, indent=2)
        Path(tmp).rename(out)
    except Exception:
        pass


def _trades_in_window(config: dict, start_utc: datetime, end_utc: datetime) -> dict:
    """Read trades.csv and compute stats for trades within a UTC time window."""
    logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
    path = _resolve_output_path(logging_cfg.get("trades_csv", "trades.csv"), LOGS_DIR)
    result = {"trades": 0, "wins": 0, "losses": 0, "pnl_usd": 0.0, "best": None, "worst": None}
    if not path.exists():
        return result
    try:
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_raw = row.get("exit_time") or row.get("timestamp") or ""
                if not ts_raw:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_raw)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                # Only count exit rows (have exit_price and pnl_usd)
                if not row.get("exit_price") or not row.get("pnl_usd"):
                    continue
                if ts < start_utc or ts >= end_utc:
                    continue
                pnl = float(row.get("pnl_usd") or 0)
                result["trades"] += 1
                result["pnl_usd"] += pnl
                if pnl > 0:
                    result["wins"] += 1
                elif pnl < 0:
                    result["losses"] += 1
                if result["best"] is None or pnl > result["best"]:
                    result["best"] = pnl
                if result["worst"] is None or pnl < result["worst"]:
                    result["worst"] = pnl
    except Exception:
        pass
    return result


def _check_shift_summaries(config: dict, state: dict, now: datetime) -> dict:
    """Send Slack shift summaries at scheduled times. Returns updated state."""
    try:
        from zoneinfo import ZoneInfo
        PT = ZoneInfo("America/Los_Angeles")
    except ImportError:
        return state

    now_pt = now.astimezone(PT)
    today_str = now_pt.strftime("%Y-%m-%d")
    sent = state.get("_shift_summaries_sent") or {}

    # Shift schedule: (name, trigger_hour, trigger_minute)
    shifts = [
        ("intraday", 13, 0),   # 1:00 PM PT — covers 5 AM → 1 PM
        ("overnight", 5, 0),   # 5:00 AM PT — covers yesterday 1 PM → today 5 AM
        ("daily", 20, 0),      # 8:00 PM PT — covers full 24h
    ]

    for name, trigger_h, trigger_m in shifts:
        key = f"{name}_{today_str}"
        if sent.get(key):
            continue
        current_minutes = now_pt.hour * 60 + now_pt.minute
        trigger_minutes = trigger_h * 60 + trigger_m
        if current_minutes < trigger_minutes:
            continue

        # Compute UTC time window for this shift
        if name == "intraday":
            # 5 AM PT → 1 PM PT today
            start_pt = now_pt.replace(hour=5, minute=0, second=0, microsecond=0)
            end_pt = now_pt.replace(hour=13, minute=0, second=0, microsecond=0)
            window_str = f"{today_str}  5:00 AM → 1:00 PM PT"
            label = "Intraday"
        elif name == "overnight":
            # Yesterday 1 PM PT → today 5 AM PT
            yesterday_pt = now_pt - timedelta(days=1)
            start_pt = yesterday_pt.replace(hour=13, minute=0, second=0, microsecond=0)
            end_pt = now_pt.replace(hour=5, minute=0, second=0, microsecond=0)
            window_str = f"{yesterday_pt.strftime('%m/%d')} 1:00 PM → {now_pt.strftime('%m/%d')} 5:00 AM PT"
            label = "Overnight"
        else:  # daily
            start_pt = now_pt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_pt = now_pt
            window_str = f"{today_str}  Full Day"
            label = "24h Total"

        start_utc = start_pt.astimezone(timezone.utc)
        end_utc = end_pt.astimezone(timezone.utc)
        stats = _trades_in_window(config, start_utc, end_utc)

        # Get exchange equity and cumulative PnL for context
        equity = float(state.get("exchange_equity_usd") or 0) or None
        cum_pnl = float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd") or 0)

        if _nontrade_slack_allowed(config, state):
            slack_alert.shift_summary(
                shift_name=name,
                shift_label=label,
                window_str=window_str,
                trades=stats["trades"],
                wins=stats["wins"],
                losses=stats["losses"],
                pnl_usd=round(stats["pnl_usd"], 2),
                best_trade_usd=round(stats["best"], 2) if stats["best"] is not None else None,
                worst_trade_usd=round(stats["worst"], 2) if stats["worst"] is not None else None,
                equity=equity,
                cumulative_pnl_usd=round(cum_pnl, 2) if name != "daily" else None,
            )

        sent[key] = now.isoformat()
        state["_shift_summaries_sent"] = sent

    return state


def _cooldown_active(state: dict, now: datetime) -> bool:
    ts = state.get("cooldown_until")
    if not ts:
        return False
    return now <= datetime.fromisoformat(ts)


def _update_cooldown(state: dict, now: datetime, minutes: int) -> None:
    state["cooldown_until"] = (now + timedelta(minutes=minutes)).isoformat()


def _extract_total_funds_for_margin(balance_summary: dict | None) -> float | None:
    try:
        if not isinstance(balance_summary, dict):
            return None
        root = balance_summary.get("balance_summary") or {}
        if not isinstance(root, dict):
            return None
        val = root.get("total_usd_balance") or root.get("total_funds_for_margin")
        if isinstance(val, dict):
            val = val.get("value")
        v = float(val)
        return v if v > 0 else None
    except Exception:
        return None


def _to_float(v: Any, default: float | None = None) -> float | None:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _position_liquidation_price(open_pos: dict, api: CoinbaseAdvanced, product_id: str) -> float | None:
    liq = _to_float((open_pos or {}).get("liquidation_price"))
    if liq and liq > 0:
        return liq
    if product_id:
        liq = _to_float(api.get_liquidation_price(product_id))
        if liq and liq > 0:
            return liq
    return None


def _liquidation_distance(mark: float, liq: float | None, direction: str) -> float | None:
    if liq is None or liq <= 0 or mark <= 0:
        return None
    d = str(direction or "long").lower()
    if d == "long":
        # LONG: dist=(mark-liq)/mark
        return (mark - liq) / mark
    # SHORT: dist=(liq-mark)/liq
    return (liq - mark) / liq


def _trend_alignment_15m_1h(df_15m: pd.DataFrame, df_1h: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or df_1h.empty or len(df_15m) < 30 or len(df_1h) < 30:
        return False
    d = str(direction or "long").lower()
    e21_15 = ema(df_15m["close"], 21)
    e55_15 = ema(df_15m["close"], 55)
    e21_1h = ema(df_1h["close"], 21)
    e55_1h = ema(df_1h["close"], 55)
    s15 = float(e21_15.diff().tail(4).mean())
    s1h = float(e21_1h.diff().tail(4).mean())
    if d == "long":
        return bool(e21_15.iloc[-1] > e55_15.iloc[-1] and e21_1h.iloc[-1] > e55_1h.iloc[-1] and s15 > 0 and s1h > 0)
    return bool(e21_15.iloc[-1] < e55_15.iloc[-1] and e21_1h.iloc[-1] < e55_1h.iloc[-1] and s15 < 0 and s1h < 0)


def _retest_hold(df_15m: pd.DataFrame, direction: str) -> bool:
    if df_15m.empty or len(df_15m) < 25:
        return False
    row = df_15m.iloc[-1]
    close = float(row["close"])
    high = float(row["high"])
    low = float(row["low"])
    e21 = float(ema(df_15m["close"], 21).iloc[-1])
    d = str(direction or "long").lower()
    if d == "long":
        return low <= (e21 * 1.003) and close >= e21 and close <= high
    return high >= (e21 * 0.997) and close <= e21 and close >= low


def _is_duplicate_order(state: dict, fingerprint: str, now: datetime, window_sec: int = 90) -> bool:
    last_f = str(state.get("last_order_fingerprint") or "")
    last_ts = str(state.get("last_order_ts") or "")
    if not last_f or not last_ts:
        return False
    if last_f != fingerprint:
        return False
    try:
        dt = datetime.fromisoformat(last_ts)
    except Exception:
        return False
    return (now - dt).total_seconds() <= int(window_sec)


def _sanitize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=[c for c in ("open", "high", "low", "close") if c in out.columns])
    return out.reset_index(drop=True)


def _recent_reason_count(path: Path, reason: str, since_utc: datetime, max_lines: int = 4000) -> int:
    if not path.exists():
        return 0
    target = str(reason or "").strip().lower()
    if not target:
        return 0
    try:
        lines = path.read_text().splitlines()
    except Exception:
        return 0
    count = 0
    for line in lines[-int(max_lines):]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if str(row.get("reason") or "").strip().lower() != target:
            continue
        try:
            ts = datetime.fromisoformat(str(row.get("timestamp") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        if ts >= since_utc:
            count += 1
    return count


def _lane_v_cooldown_blocks_entry(
    state: dict[str, Any],
    entry: dict[str, Any] | None,
    *,
    atr_value: float,
    lane_cfg: dict[str, Any],
    now: datetime,
) -> bool:
    if not entry or str(entry.get("type") or "") != "liquidity_sweep":
        return False
    cooldown_bars = int(lane_cfg.get("lane_v_sweep_cooldown_bars", 3) or 3)
    if cooldown_bars <= 0:
        return False
    last_entry_type = str(state.get("last_entry_type") or "")
    last_entry_time = str(state.get("last_entry_time") or "")
    if last_entry_type != "liquidity_sweep" or not last_entry_time:
        return False
    try:
        last_dt = datetime.fromisoformat(last_entry_time)
    except Exception:
        return False
    elapsed_min = max(0.0, (now - last_dt).total_seconds() / 60.0)
    if elapsed_min > (cooldown_bars * 15):
        return False
    current_anchor = float(entry.get("sweep_level") or entry.get("target_cluster_price") or 0.0)
    last_anchor = float(state.get("last_liquidity_sweep_anchor") or 0.0)
    if current_anchor <= 0 or last_anchor <= 0 or atr_value <= 0:
        return True
    zone_atr = float(lane_cfg.get("lane_v_cluster_zone_atr", 0.25) or 0.25)
    return abs(current_anchor - last_anchor) / atr_value <= zone_atr


def _evaluate_hard_risk_gates(
    config: dict,
    state: dict,
    pnl_today: float,
    equity_start: float,
    recovery_info: dict,
    now: datetime,
    *,
    pulse: dict | None = None,
    live_tick_age_sec: float | None = None,
) -> str | None:
    """
    Evaluates hard risk gates that cannot be bypassed even by AI executive mode.
    Returns the reason string if blocked, else None.
    """
    max_daily_loss_pct = float(config.get("risk", {}).get("max_daily_loss_pct", 0.0) or 0.0)
    
    # HARD risk gate: daily loss cap is never bypassable
    _pnl_for_daily_loss = float(state.get("exchange_pnl_today_usd") or 0.0)
    if _pnl_for_daily_loss == 0.0:
        _pnl_for_daily_loss = float(pnl_today or 0.0)
        
    max_loss_hit = bool(
        max_daily_loss_pct > 0
        and equity_start > 0
        and _pnl_for_daily_loss <= -(equity_start * max_daily_loss_pct)
    )
    if max_loss_hit:
        return "entry_blocked_max_daily_loss"

    # SAFE_MODE gate disabled -- stay in the market, learn from losses
    # if recovery_info.get("mode") == "SAFE_MODE":
    #     return "entry_blocked_recovery_safe_mode"

    # Force clear SAFE_MODE -- never want full shutdown
    state.pop("_safe_mode", None)
    state.pop("safe_mode", None)

    freshness_cfg = (config.get("freshness_gates") or {}) if isinstance(config.get("freshness_gates"), dict) else {}
    if bool(freshness_cfg.get("enabled", True)):
        pulse = pulse or {}
        pulse_components = pulse.get("components") if isinstance(pulse.get("components"), dict) else {}
        pulse_regime = str(pulse.get("regime") or "unknown")
        tick_health = str(pulse_components.get("tick_health") or "unknown")
        brief_age_min = float(pulse_components.get("brief_age_min") or 0.0) if pulse_components.get("brief_age_min") is not None else None
        sentiment_stale = bool(pulse_components.get("sentiment_stale"))
        max_live_tick_age_sec = float(freshness_cfg.get("max_live_tick_age_sec", 60) or 60)
        max_market_brief_age_min = float(freshness_cfg.get("max_market_brief_age_min", 45) or 45)

        if bool(freshness_cfg.get("block_on_dead_tick", True)):
            if tick_health == "dead":
                return "entry_blocked_live_tick_dead"
            if live_tick_age_sec is not None and live_tick_age_sec >= max_live_tick_age_sec:
                return "entry_blocked_live_tick_stale"

        if bool(freshness_cfg.get("block_on_stale_market_brief", True)) and brief_age_min is not None and brief_age_min >= max_market_brief_age_min:
            return "entry_blocked_market_brief_stale"

        if bool(freshness_cfg.get("block_on_sentiment_stale_in_danger", True)) and sentiment_stale and pulse_regime == "danger":
            return "entry_blocked_sentiment_stale"

        if bool(freshness_cfg.get("block_on_pulse_danger", True)) and pulse_regime == "danger":
            return "entry_blocked_market_pulse_danger"
        
    return None


def _dip_retrace_gate(
    direction: str,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    price: float,
    config: dict,
    quality_tier: str = "",
    entry_type: str = "",
) -> tuple[bool, dict]:
    """
    Dip-retrace no-short gate: blocks shorts when price is bouncing.
    Returns (blocked, metadata).

    Logic: If price is recovering (RSI rising + higher closes + near/above VWAP),
    shorting is likely to get squeezed. Block it.
    """
    v4_cfg = (config.get("v4") or {}) if isinstance(config.get("v4"), dict) else {}
    drg_cfg = (v4_cfg.get("dip_retrace_gate") or {}) if isinstance(v4_cfg.get("dip_retrace_gate"), dict) else {}

    if not drg_cfg.get("enabled", False):
        return False, {"gate": "dip_retrace", "enabled": False}

    block_dir = str(drg_cfg.get("block_direction", "short")).lower()
    if direction.lower() != block_dir:
        return False, {"gate": "dip_retrace", "skip": "direction_mismatch"}

    # Exempt tiers
    exempt_tiers = list(drg_cfg.get("exempt_tiers") or [])
    if quality_tier in exempt_tiers:
        return False, {"gate": "dip_retrace", "skip": "exempt_tier", "tier": quality_tier}

    # Exempt entry types
    exempt_types = list(drg_cfg.get("exempt_entry_types") or [])
    if entry_type in exempt_types:
        return False, {"gate": "dip_retrace", "skip": "exempt_entry_type", "type": entry_type}

    meta = {"gate": "dip_retrace", "checks": {}}
    blocked_count = 0

    # Check 1: RSI rising for N bars
    rsi_bars = int(drg_cfg.get("rsi_rising_bars", 3) or 3)
    try:
        from indicators.ema import ema as _ema_fn
        rsi_col = None
        if "rsi" in df_15m.columns:
            rsi_col = df_15m["rsi"]
        else:
            # Compute RSI inline
            delta = df_15m["close"].diff()
            gain = delta.where(delta > 0, 0.0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
            rs = gain / loss.replace(0, float("nan"))
            rsi_col = 100 - (100 / (1 + rs))

        if rsi_col is not None and len(rsi_col) >= rsi_bars + 1:
            rsi_vals = rsi_col.iloc[-(rsi_bars + 1):].values
            rsi_rising = all(rsi_vals[i + 1] > rsi_vals[i] for i in range(len(rsi_vals) - 1))
            meta["checks"]["rsi_rising"] = bool(rsi_rising)
            meta["checks"]["rsi_current"] = float(rsi_vals[-1]) if len(rsi_vals) > 0 else 0
            if rsi_rising:
                blocked_count += 1
    except Exception:
        meta["checks"]["rsi_rising"] = None

    # Check 2: Higher closes (consecutive candles closing higher)
    min_higher = int(drg_cfg.get("min_higher_closes", 2) or 2)
    try:
        closes = df_15m["close"].iloc[-(min_higher + 1):].values
        higher_closes = all(closes[i + 1] > closes[i] for i in range(len(closes) - 1))
        meta["checks"]["higher_closes"] = bool(higher_closes)
        if higher_closes:
            blocked_count += 1
    except Exception:
        meta["checks"]["higher_closes"] = None

    # Check 3: Price near or above VWAP (1h)
    vwap_pct = float(drg_cfg.get("vwap_reclaim_pct", 0.002) or 0.002)
    try:
        if len(df_1h) >= 5:
            tp = (df_1h["high"] + df_1h["low"] + df_1h["close"]) / 3
            vol = df_1h["volume"] if "volume" in df_1h.columns else pd.Series([1.0] * len(df_1h))
            vwap = (tp * vol).cumsum() / vol.cumsum()
            vwap_val = float(vwap.iloc[-1])
            if vwap_val > 0:
                dist = (price - vwap_val) / vwap_val
                above_vwap = dist >= -vwap_pct  # within tolerance or above
                meta["checks"]["vwap_val"] = round(vwap_val, 6)
                meta["checks"]["vwap_dist_pct"] = round(dist * 100, 3)
                meta["checks"]["above_vwap"] = bool(above_vwap)
                if above_vwap:
                    blocked_count += 1
    except Exception:
        meta["checks"]["above_vwap"] = None

    # Need at least 2 of 3 checks to confirm bounce and block the short
    blocked = blocked_count >= 2
    meta["blocked"] = blocked
    meta["checks_passed"] = blocked_count
    return blocked, meta


def decide_and_trade(config: dict, paper: bool = True) -> None:
    symbol = "XLM"
    data_product_id = config.get("data_product_id", "XLM-USD")
    execution_product_id = str(config.get("product_id") or "").strip()
    signal_product_id = str(config.get("signal_product_id") or execution_product_id or data_product_id).strip()
    store = CandleStore(data_dir=DATA_DIR)
    api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
    durable = StateStore(DATA_DIR / "bot_state.db")
    durable.log_event("startup", {"paper": bool(paper)})

    # Initialize inter-agent communication board
    try:
        agent_comms.init(config)
    except Exception:
        pass

    # --- Contract context (OI / funding / basis) ---
    cc_cfg = (config.get("contract_context") or {}) if isinstance(config.get("contract_context"), dict) else {}
    cc_enabled = bool(cc_cfg.get("enabled", True))
    cc_mgr: ContractContext | None = None
    if cc_enabled:
        try:
            cc_mgr = ContractContext(
                api=api,
                perp_product_id=execution_product_id or config.get("product_id", "XLP-USD-PERP"),
                spot_product_id=data_product_id,
                cache_dir=DATA_DIR,
                logs_dir=LOGS_DIR,
                config=cc_cfg,
            )
        except Exception:
            cc_mgr = None
    ms_cfg = (config.get("market_structure") or {}) if isinstance(config.get("market_structure"), dict) else {}
    ms_enabled = bool(ms_cfg.get("enabled", True))
    ob_mgr: OrderBookContext | None = None
    if ms_enabled:
        try:
            ob_mgr = OrderBookContext(
                api=api,
                product_id=execution_product_id or signal_product_id,
                cache_dir=DATA_DIR,
                config=ms_cfg,
            )
        except Exception:
            ob_mgr = None

    # --- Session detection ---
    now_boot = datetime.now(timezone.utc)
    _st = load_state()
    last_ts_raw = _st.get("last_cycle_ts")
    gap_seconds = 9999
    if last_ts_raw:
        try:
            last_ts_dt = datetime.fromisoformat(str(last_ts_raw))
            if last_ts_dt.tzinfo is None:
                last_ts_dt = last_ts_dt.replace(tzinfo=timezone.utc)
            gap_seconds = (now_boot - last_ts_dt).total_seconds()
        except Exception:
            pass
    # Initialize Slack alerts from config or env var
    slack_alert.init(config)
    ai_advisor.init(config)
    gemini_advisor.init(config)
    perplexity_advisor.init(config)
    # Set a default for cycles without an open position so peer_intel payload
    # never references an uninitialized variable.
    integrity_report = None
    ev_snapshot = None
    _re_size_mult = 1.0
    _re_result: dict[str, Any] = {}
    _re_data: dict[str, Any] = {}
    _kelly_mult = 1.0
    _kelly_reason = "disabled"
    weekly_research: dict[str, Any] | None = None
    weekly_research_bonus = 0
    weekly_research_reasons: list[str] = []

    if gap_seconds > 60 or "session_id" not in _st:
        session_id = uuid.uuid4().hex[:8]
        _st["session_id"] = session_id
        cfg_hash = hashlib.md5(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:8]
        log_decision(config, {
            "timestamp": now_boot.isoformat(),
            "reason": "bot_session_start",
            "session_id": session_id,
            "paper": bool(paper),
            "config_hash": cfg_hash,
            "gap_seconds": round(gap_seconds, 1),
        })
        save_state(_st)
        # Slack bot_started disabled — too noisy on every cycle restart.
        # User only wants alerts for live trades.
        # slack_alert.bot_started(
        #     session_id=session_id,
        #     equity=float(_st.get("equity_start_usd") or 0),
        #     pnl_today=float(_st.get("pnl_today_usd") or 0),
        # )
    else:
        session_id = _st["session_id"]

    # --- Guardian restart marker ---
    guardian_marker = DATA_DIR / ".guardian_restart"
    if guardian_marker.exists():
        try:
            restart_ts = guardian_marker.read_text().strip()
            log_decision(config, {
                "timestamp": now_boot.isoformat(),
                "reason": "guardian_restart",
                "restart_ts": restart_ts,
                "session_id": session_id,
            })
        except Exception:
            pass
        try:
            guardian_marker.unlink()
        except Exception:
            pass

    # ── Startup integrity check ──────────────────────────────────────
    # When a new session starts (gap > 60s), recalculate pnl/trades from
    # trades.csv to prevent phantom PnL from persisting across restarts.
    if gap_seconds > 60:
        try:
            import csv as _csv
            _today_str = now_boot.strftime("%Y-%m-%d")
            _st = load_state()
            _csv_pnl = 0.0
            _csv_trades = 0
            _csv_losses = 0
            _trades_path = LOGS_DIR / "trades.csv"
            if _trades_path.exists():
                with open(_trades_path, "r") as _f:
                    for _row in _csv.DictReader(_f):
                        _et = _row.get("entry_time", "")
                        if _today_str not in _et:
                            continue
                        _result = _row.get("result", "")
                        if _result in ("ok",):
                            continue
                        _csv_trades += 1
                        _csv_pnl += float(_row.get("pnl_usd") or 0)
                        if _result == "loss":
                            _csv_losses += 1
            _old_pnl = float(_st.get("pnl_today_usd") or 0)
            if abs(_old_pnl - _csv_pnl) > 1.0:
                log_decision(config, {
                    "timestamp": now_boot.isoformat(),
                    "reason": "startup_pnl_correction",
                    "old_pnl": round(_old_pnl, 2),
                    "csv_pnl": round(_csv_pnl, 2),
                    "old_trades": _st.get("trades"),
                    "csv_trades": _csv_trades,
                    "thought": f"state PnL ${_old_pnl:.2f} doesn't match trades.csv ${_csv_pnl:.2f} — correcting.",
                })
                _st["pnl_today_usd"] = round(_csv_pnl, 2)
                _st["trades"] = _csv_trades
                _st["losses"] = _csv_losses
                save_state(_st)
        except Exception:
            pass

    history_days = int((config.get("data") or {}).get("history_days_15m", 45) or 45) if isinstance(config.get("data"), dict) else 45
    # Single base fetch per cycle to avoid long blocking on three separate network pulls.
    # FIX: use data_product_id (spot XLM-USD) for candle fetches. The perp
    # product (XLP-20DEC30-CDE) returns NotFound on the Exchange candle API.
    df_15m = load_or_fetch(store, data_product_id, symbol, "15m", days=history_days)
    df_15m = _sanitize_ohlcv(df_15m)
    df_1h = _sanitize_ohlcv(ensure_timeframe(df_15m, "1h"))
    df_4h = _sanitize_ohlcv(ensure_timeframe(df_15m, "4h"))

    # Recovery fallback: if resampled windows are insufficient, load cached higher-TF files.
    if df_1h.empty or len(df_1h) < 120:
        df_1h = _sanitize_ohlcv(load_or_fetch(store, data_product_id, symbol, "1h", days=max(60, history_days)))
    if df_4h.empty or len(df_4h) < 120:
        df_4h = _sanitize_ohlcv(load_or_fetch(store, data_product_id, symbol, "4h", days=max(90, history_days)))

    # Higher timeframes: 1D, 1W, 1M resampled from 1h data for macro context.
    # These feed structure levels, wick zones, regime classification, and alignment.
    df_1d = pd.DataFrame()
    df_1w = pd.DataFrame()
    df_1mo = pd.DataFrame()
    try:
        # Use 1h as base for daily+ resampling (more data than 15m, less noise)
        _htf_base = df_1h if not df_1h.empty and len(df_1h) >= 120 else df_15m
        if not _htf_base.empty and len(_htf_base) >= 24:
            df_1d = _sanitize_ohlcv(ensure_timeframe(_htf_base, "1d"))
        if not _htf_base.empty and len(_htf_base) >= 168:
            df_1w = _sanitize_ohlcv(ensure_timeframe(_htf_base, "1w"))
        if not _htf_base.empty and len(_htf_base) >= 720:
            df_1mo = _sanitize_ohlcv(ensure_timeframe(_htf_base, "1M"))
    except Exception:
        pass

    # Fetch 5m and 1m candles for micro-sweep and wick zone detection
    df_5m = pd.DataFrame()
    df_1m = pd.DataFrame()
    _pre_lane_cfg = ((config.get("v4") or {}).get("lane_scoring") or {}) if isinstance((config.get("v4") or {}).get("lane_scoring"), dict) else {}
    if bool(_pre_lane_cfg.get("micro_sweep_enabled", False)):
        try:
            df_5m = _sanitize_ohlcv(fetch_5m_candles(store, data_product_id, symbol, days=2))
        except Exception:
            pass
    # 1m candles: ultra-lightweight (4 hours, cached 3 min)
    _wz_pre = (_pre_lane_cfg.get("wick_zones") or {}) if isinstance(_pre_lane_cfg.get("wick_zones"), dict) else {}
    if bool(_wz_pre.get("enabled", True)) and bool(_wz_pre.get("enable_1m", True)):
        try:
            df_1m = _sanitize_ohlcv(fetch_1m_candles(store, data_product_id, symbol, hours=4))
        except Exception:
            pass

    if df_15m.empty or df_1h.empty or df_4h.empty:
        now = datetime.now(timezone.utc)
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "no_data",
            "data_product_id": data_product_id,
            "signal_product_id": signal_product_id,
        })
        return

    price = float(df_15m["close"].iloc[-1])
    _candle_price = price  # preserve candle price for sanity checks

    # Live tick integration: use WS price if fresher than candle
    _live_tick = _read_live_tick()
    _live_price = float(_live_tick.get("price") or 0)
    _live_age = float(_live_tick.get("age_seconds") or 999)
    if _live_price > 0 and _live_age < 60:  # only trust ticks < 60s old
        price = _live_price
        _price_source = "live_ws"
    else:
        _price_source = "candle_close"

    e21_1h = float(ema(df_1h["close"], 21).iloc[-1])
    spread_estimate = api.get_spread_pct(signal_product_id) or 0.0

    now = datetime.now(timezone.utc)

    # Trade learning: update shadow tracking with current price
    try:
        trade_reviewer.tick_shadows(price, now)
    except Exception:
        pass

    gates = run_regime_gates(df_1h, price, e21_1h, spread_estimate, config, now)
    gates_pass = all(gates.values())
    route_tier = compute_route_tier(gates, config)

    # --- Contract context (deferred until after product selection) ---
    contract_ctx: dict = {}

    # Build candle context for score modifiers / cascade detection
    def _price_delta_pct(df: pd.DataFrame, bars: int = 1) -> float | None:
        if df is None or len(df) < bars + 1 or "close" not in df.columns:
            return None
        try:
            cur = float(df["close"].iloc[-1])
            prev = float(df["close"].iloc[-(bars + 1)])
            return (cur - prev) / prev if prev > 0 else None
        except Exception:
            return None

    candle_ctx: dict = {
        "price_delta_15m": _price_delta_pct(df_15m, 1),
        "price_delta_1h": _price_delta_pct(df_1h, 1),
    }

    # --- Expansion detection & volatility state machine ---
    _prev_vol_state = str(load_state().get("vol_state") or "COMPRESSION")
    try:
        expansion_state = derive_vol_state(df_15m, df_1h, prev_state=_prev_vol_state)
    except Exception:
        expansion_state = {"phase": "COMPRESSION", "direction": "NEUTRAL", "confidence": 0,
                           "reasons": ["ERROR"], "metrics": {}, "range": {"high": None, "low": None}}

    # AI advisor: fire regime evaluation on vol state transitions
    _curr_vol_phase = expansion_state.get("phase", "COMPRESSION")
    if _prev_vol_state != _curr_vol_phase:
        _regime_payload = {
            "old_phase": _prev_vol_state,
            "new_phase": _curr_vol_phase,
            "vol_direction": expansion_state.get("direction"),
            "vol_confidence": expansion_state.get("confidence", 0),
            "vol_reasons": expansion_state.get("reasons", []),
            "pnl_today_usd": float(_st.get("pnl_today_usd") or 0),
            "consecutive_losses": int(_st.get("consecutive_losses") or 0),
        }
        ai_advisor.evaluate_regime(_regime_payload, df_1h=df_1h)
        gemini_advisor.evaluate_regime(_regime_payload, df_1h=df_1h)

    # Fire Perplexity research refreshes through cache-aware paths.
    perplexity_advisor.fetch_market_brief()
    perplexity_advisor.fetch_weekly_market_research(config=config)

    # Market Pulse: composite health score (fuses sentiment + news + live tick)
    _pulse: dict | None = None
    try:
        market_pulse.init(config)
        _pulse = market_pulse.get_pulse()
    except Exception:
        pass

    # --- ATR regime audit logging (append-only JSONL) ---
    try:
        _exp_m = expansion_state.get("metrics") or {}
        _audit = {
            "timestamp": now.isoformat(),
            "price": price,
            "atr_regime_pass": gates.get("atr_regime", False),
            "gates_pass": gates_pass,
            "atr": _exp_m.get("atr"),
            "atr_prev": _exp_m.get("atr_prev"),
            "atr_slope": _exp_m.get("atr_slope"),
            "tr": _exp_m.get("tr"),
            "avg_tr": _exp_m.get("avg_tr"),
            "tr_ratio": _exp_m.get("tr_ratio"),
            "vol_ratio": _exp_m.get("vol_ratio"),
            "rsi": _exp_m.get("rsi"),
            "range_high": _exp_m.get("range_high"),
            "range_low": _exp_m.get("range_low"),
            "close": _exp_m.get("close"),
            "vol_phase": expansion_state.get("phase"),
            "vol_direction": expansion_state.get("direction"),
            "vol_confidence": expansion_state.get("confidence"),
            "expansion_but_gate_false": (
                expansion_state.get("phase") in ("IGNITION", "EXPANSION")
                and not gates.get("atr_regime", False)
            ),
        }
        _audit_path = LOGS_DIR / "atr_regime_audit.jsonl"
        _audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_audit_path, "a") as _af:
            _af.write(json.dumps(_audit, default=str) + "\n")
    except Exception:
        pass

    # --- HTF Monthly Zone context ---
    try:
        _atr15 = atr(df_15m, 14)
        _bot_atr = float(_atr15.iloc[-1]) if not _atr15.empty and not pd.isna(_atr15.iloc[-1]) else None
        zone_context = compute_zone_context(
            price, df_15m,
            product_id=signal_product_id,
            cache_dir=DATA_DIR,
            bot_atr=_bot_atr,
            expansion_state=expansion_state,
        )
    except Exception:
        zone_context = {"nearest": None, "inside_any_zone": False, "zones_top3": [],
                        "readiness_label": None, "readiness_reasons": [], "total_zones": 0}

    # Use daily data for structure levels when available (more accurate macro S/R)
    _levels_base = df_1d if not df_1d.empty and len(df_1d) >= 7 else df_4h
    levels = compute_structure_levels(_levels_base)
    swing_high, swing_low = find_swing(df_4h, 60)
    fibs = fib_levels(swing_high, swing_low)
    v4_cfg = (config.get("v4") or {}) if isinstance(config.get("v4"), dict) else {}
    lane_cfg = (v4_cfg.get("lane_scoring") or {}) if isinstance(v4_cfg.get("lane_scoring"), dict) else {}
    lane_cfg = _deep_merge_dict(lane_cfg, {"liquidation_clusters": (config.get("liquidation_clusters") or {})})

    # Multi-TF wick rejection/bounce zones (support + resistance from wick clusters)
    _wick_zones: list[WickZone] = []
    _wick_zone_levels: dict[str, float] = {}
    _wz_cfg = (lane_cfg.get("wick_zones") or {}) if isinstance(lane_cfg.get("wick_zones"), dict) else {}
    if bool(_wz_cfg.get("enabled", True)):
        try:
            _wick_zones = build_wick_zones(
                df_5m=df_5m if not df_5m.empty else None,
                df_15m=df_15m if not df_15m.empty else None,
                df_1h=df_1h if not df_1h.empty else None,
                df_4h=df_4h if not df_4h.empty else None,
                config=_wz_cfg,
                df_1m=df_1m if not df_1m.empty else None,
                df_1d=df_1d if not df_1d.empty else None,
                df_1w=df_1w if not df_1w.empty else None,
            )
            _wick_zone_levels = zones_to_levels(_wick_zones, price)
            # Merge wick zones into structure levels so every entry lane benefits
            levels.update(_wick_zone_levels)
        except Exception:
            pass

    # Pattern detection: double tops/bottoms, channels, breakouts, fakeouts
    _active_patterns: list[PatternSignal] = []
    try:
        if _wick_zones:
            _atr_for_patterns = float(atr(df_15m, 14).iloc[-1]) if not df_15m.empty and len(df_15m) >= 15 else 0.0
            if _atr_for_patterns > 0:
                _active_patterns = detect_patterns(
                    price, df_15m, _wick_zones, _atr_for_patterns,
                    state=_st, config=_wz_cfg,
                )
    except Exception:
        pass

    long_liquidation_intel: dict[str, Any] = {}
    short_liquidation_intel: dict[str, Any] = {}
    liquidation_prompt = ""
    try:
        long_liquidation_intel = _build_lane_v_directional_intel(
            direction="long",
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            levels=levels,
            fibs=fibs,
            liquidation_ctx=liquidation_ctx,
            contract_ctx=contract_ctx,
            lane_cfg=lane_cfg,
        )
        short_liquidation_intel = _build_lane_v_directional_intel(
            direction="short",
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            levels=levels,
            fibs=fibs,
            liquidation_ctx=liquidation_ctx,
            contract_ctx=contract_ctx,
            lane_cfg=lane_cfg,
        )
        liquidation_prompt = str(long_liquidation_intel.get("liquidation_prompt") or short_liquidation_intel.get("liquidation_prompt") or "")
    except Exception:
        long_liquidation_intel = {}
        short_liquidation_intel = {}
        liquidation_prompt = ""
    try:
        lane_v_atr_value = float(atr(df_15m, 14).iloc[-1])
    except Exception:
        lane_v_atr_value = 0.0

    breakout_tf = dominant_timeframe(df_4h, df_1h, df_15m)
    tf_df = df_15m if breakout_tf == "15m" else df_1h if breakout_tf == "1h" else df_4h
    breakout_type_long = classify_breakout(tf_df, "long")
    breakout_type_short = classify_breakout(tf_df, "short")
    try:
        _lane_w_playbook = market_intel_service.get_latest_weekly_playbook(DATA_DIR)
    except Exception:
        _lane_w_playbook = {}
    try:
        _lane_w_calendar = market_intel_service.get_latest_event_calendar(DATA_DIR)
    except Exception:
        _lane_w_calendar = {}
    lane_w_cfg = (config.get("score_lanes") or {}) if isinstance(config.get("score_lanes"), dict) else {}
    long_htf_breakout_watch = assess_htf_breakout_continuation(
        price,
        df_4h,
        df_1h,
        df_15m,
        levels,
        fibs,
        "long",
        weekly_playbook=_lane_w_playbook,
        event_calendar=_lane_w_calendar,
        config=lane_w_cfg,
    )
    short_htf_breakout_watch = assess_htf_breakout_continuation(
        price,
        df_4h,
        df_1h,
        df_15m,
        levels,
        fibs,
        "short",
        weekly_playbook=_lane_w_playbook,
        event_calendar=_lane_w_calendar,
        config=lane_w_cfg,
    )

    long_entry = htf_breakout_continuation(price, df_4h, df_1h, df_15m, levels, fibs, "long", weekly_playbook=_lane_w_playbook, event_calendar=_lane_w_calendar, config=lane_w_cfg)
    long_entry = long_entry or trend_continuation(price, df_15m, df_1h, "long", state=_st)
    long_entry = long_entry or fib_retrace(price, df_1h, df_15m, "long", config=config)
    long_entry = long_entry or pullback_continuation(price, df_1h, df_4h, df_15m, levels, fibs, "long")
    long_entry = long_entry or breakout_retest(price, df_15m, levels, fibs, "long")
    long_entry = long_entry or reversal_impulse(price, df_1h, df_15m, levels, fibs, "long")
    long_entry = long_entry or compression_breakout(price, df_15m, df_1h, expansion_state, levels, fibs, "long")
    long_entry = long_entry or early_impulse(price, df_15m, expansion_state, "long")
    long_entry = long_entry or compression_range(price, df_15m, expansion_state, "long")
    long_entry = long_entry or slow_bleed_hunter(price, df_15m, "long", config=config)
    long_entry = long_entry or liquidity_sweep(price, df_15m, df_1h, "long", levels, fibs, liquidation_intel=long_liquidation_intel, config=lane_cfg)
    long_entry = long_entry or wick_rejection(price, df_15m, df_1h, levels, "long")
    long_entry = long_entry or volume_climax_reversal(price, df_15m, "long")
    long_entry = long_entry or vwap_reversion(price, df_15m, df_1h, "long")
    long_entry = long_entry or grid_range(price, df_15m, df_1h, "long", levels, fibs, expansion_state)
    long_entry = long_entry or regime_low_vol(price, df_15m, df_1h, "long", expansion_state, levels)
    long_entry = long_entry or stat_arb_proxy(price, df_15m, df_1h, "long")
    long_entry = long_entry or orderflow_imbalance(price, df_15m, "long")
    long_entry = long_entry or macro_ma_cross(price, df_1h, df_4h, "long")
    long_entry = long_entry or opening_range_breakout(price, df_15m, df_1h, "long", levels, config=config)
    long_entry = long_entry or hourly_continuation(price, df_15m, df_1h, "long", levels, config=config)
    short_entry = htf_breakout_continuation(price, df_4h, df_1h, df_15m, levels, fibs, "short", weekly_playbook=_lane_w_playbook, event_calendar=_lane_w_calendar, config=lane_w_cfg)
    short_entry = short_entry or trend_continuation(price, df_15m, df_1h, "short", state=_st)
    short_entry = short_entry or fib_retrace(price, df_1h, df_15m, "short", config=config)
    short_entry = short_entry or pullback_continuation(price, df_1h, df_4h, df_15m, levels, fibs, "short")
    short_entry = short_entry or breakout_retest(price, df_15m, levels, fibs, "short")
    short_entry = short_entry or reversal_impulse(price, df_1h, df_15m, levels, fibs, "short")
    short_entry = short_entry or compression_breakout(price, df_15m, df_1h, expansion_state, levels, fibs, "short")
    short_entry = short_entry or early_impulse(price, df_15m, expansion_state, "short")
    short_entry = short_entry or compression_range(price, df_15m, expansion_state, "short")
    short_entry = short_entry or slow_bleed_hunter(price, df_15m, "short", config=config)
    short_entry = short_entry or liquidity_sweep(price, df_15m, df_1h, "short", levels, fibs, liquidation_intel=short_liquidation_intel, config=lane_cfg)
    short_entry = short_entry or wick_rejection(price, df_15m, df_1h, levels, "short")
    short_entry = short_entry or volume_climax_reversal(price, df_15m, "short")
    short_entry = short_entry or vwap_reversion(price, df_15m, df_1h, "short")
    short_entry = short_entry or grid_range(price, df_15m, df_1h, "short", levels, fibs, expansion_state)
    short_entry = short_entry or regime_low_vol(price, df_15m, df_1h, "short", expansion_state, levels)
    short_entry = short_entry or stat_arb_proxy(price, df_15m, df_1h, "short")
    short_entry = short_entry or orderflow_imbalance(price, df_15m, "short")
    short_entry = short_entry or macro_ma_cross(price, df_1h, df_4h, "short")
    short_entry = short_entry or opening_range_breakout(price, df_15m, df_1h, "short", levels, config=config)
    short_entry = short_entry or hourly_continuation(price, df_15m, df_1h, "short", levels, config=config)
    _micro_sweep_promoted = False
    _micro_sweep_source = None

    if _lane_v_cooldown_blocks_entry(_st, long_entry, atr_value=lane_v_atr_value, lane_cfg=lane_cfg, now=now):
        long_entry = None
    if _lane_v_cooldown_blocks_entry(_st, short_entry, atr_value=lane_v_atr_value, lane_cfg=lane_cfg, now=now):
        short_entry = None

    # Blocking lanes: MTF conflict (Lane L) and exhaustion warning (Lane O)
    _mtf_blocked = False
    _exhaustion_blocked = False
    try:
        if long_entry:
            _mtf_blocked = mtf_conflict_block(df_15m, df_1h, df_4h, "long")
            _exhaustion_blocked = exhaustion_warning_block(df_15m, "long", expansion_state)
            if _mtf_blocked or _exhaustion_blocked:
                long_entry = None
        if short_entry:
            _mtf_blocked = mtf_conflict_block(df_15m, df_1h, df_4h, "short")
            _exhaustion_blocked = exhaustion_warning_block(df_15m, "short", expansion_state)
            if _mtf_blocked or _exhaustion_blocked:
                short_entry = None
    except Exception:
        pass

    # Compute structure bias for countertrend blocking (used in gate chain)
    try:
        _structure_bias = detect_15m_structure_bias(df_15m)
    except Exception:
        _structure_bias = "neutral"

    contract_ctx = {}
    orderbook_ctx = {}
    try:
        _ctx_product_id = execution_product_id or signal_product_id
        if cc_mgr and _ctx_product_id:
            cc_mgr._perp_id = _ctx_product_id
            _cc_snap = cc_mgr.fetch()
            contract_ctx = cc_mgr.as_dict() if _cc_snap else {}
        if ob_mgr and _ctx_product_id:
            ob_mgr._product_id = _ctx_product_id
            _ob_snap = ob_mgr.fetch()
            orderbook_ctx = ob_mgr.as_dict() if _ob_snap else {}
    except Exception:
        pass

    # Late-bind Lane Q: funding_arb_bias needs contract_ctx (populated above)
    _q_cfg = ((config.get("v4") or {}).get("lane_scoring") or {}) if isinstance(config.get("v4"), dict) else {}
    if contract_ctx and not long_entry:
        long_entry = funding_arb_bias(price, df_15m, "long", contract_ctx, config=_q_cfg)
    if contract_ctx and not short_entry:
        short_entry = funding_arb_bias(price, df_15m, "short", contract_ctx, config=_q_cfg)

    sweep_long = None
    sweep_short = None
    squeeze_long = None
    squeeze_short = None
    micro_sweep_long = None
    micro_sweep_short = None
    try:
        if lane_cfg.get("enabled", False):
            sweep_long = detect_sweep(df_15m, df_1h, "long", lane_cfg)
            sweep_short = detect_sweep(df_15m, df_1h, "short", lane_cfg)
            squeeze_long = detect_reclaim_impulse(df_15m, df_1h, "long", expansion_state, lane_cfg)
            squeeze_short = detect_reclaim_impulse(df_15m, df_1h, "short", expansion_state, lane_cfg)
            # --- Micro-Sweep Detection (5m + 1m) ---
            if bool(lane_cfg.get("micro_sweep_enabled", False)):
                _ms_cfg = {
                    "min_wick_ratio": float(lane_cfg.get("micro_sweep_min_wick_ratio", 0.40) or 0.40),
                    "min_wick_atr": float(lane_cfg.get("micro_sweep_min_wick_atr", 0.50) or 0.50),
                    "max_reclaim_bars": int(lane_cfg.get("micro_sweep_max_reclaim_bars", 3) or 3),
                    "min_volume_mult": float(lane_cfg.get("micro_sweep_min_volume_mult", 0.8) or 0.8),
                    "lookback_bars": int(lane_cfg.get("micro_sweep_lookback_bars", 6) or 6),
                    "min_score": int(lane_cfg.get("micro_sweep_min_score", 50) or 50),
                    "max_chase_atr": float(lane_cfg.get("micro_sweep_max_chase_atr", 1.5) or 1.5),
                }
                # Run on 5m
                if not df_5m.empty and len(df_5m) >= 6:
                    micro_sweep_long = detect_micro_sweep(df_5m, df_15m, df_1h, "long", _ms_cfg)
                    micro_sweep_short = detect_micro_sweep(df_5m, df_15m, df_1h, "short", _ms_cfg)
                # Also run on 1m for faster detection - take the better score
                if not df_1m.empty and len(df_1m) >= 12:
                    _ms_cfg_1m = dict(_ms_cfg)
                    _ms_cfg_1m["lookback_bars"] = 12  # scan last 12 one-minute candles
                    _ms_cfg_1m["max_reclaim_bars"] = 5  # allow up to 5 bars (5 min) for reclaim on 1m
                    _ms_1m_long = detect_micro_sweep(df_1m, df_15m, df_1h, "long", _ms_cfg_1m)
                    _ms_1m_short = detect_micro_sweep(df_1m, df_15m, df_1h, "short", _ms_cfg_1m)
                    # Keep whichever scored higher (5m or 1m)
                    if _ms_1m_long.detected and (not micro_sweep_long or not micro_sweep_long.detected or _ms_1m_long.score > micro_sweep_long.score):
                        micro_sweep_long = _ms_1m_long
                    if _ms_1m_short.detected and (not micro_sweep_short or not micro_sweep_short.detected or _ms_1m_short.score > micro_sweep_short.score):
                        micro_sweep_short = _ms_1m_short
    except Exception:
        pass

    # --- 5m/1m Micro-Sweep Entry Promotion (after detection) ---
    if not long_entry and micro_sweep_long and getattr(micro_sweep_long, "detected", False) and not getattr(micro_sweep_long, "htf_hostile", True):
        long_entry = {
            "type": "micro_sweep", "mode": "reversal", "entry_profile_key": "liquidity_sweep_reversal",
            "micro_sweep": True, "micro_sweep_score": micro_sweep_long.score,
            "swept_level": micro_sweep_long.swept_level, "reclaim_price": micro_sweep_long.reclaim_price,
            "wick_ratio": micro_sweep_long.wick_ratio, "wick_vs_atr": micro_sweep_long.wick_vs_atr,
            "reclaim_bars": micro_sweep_long.reclaim_bars,
            "fail_fast_bars": int(lane_cfg.get("micro_sweep_max_reclaim_bars", 3) or 3),
            "lane_v_mode": "reversal",
            "confluence": {"MICRO_SWEEP_5M": True, "WICK_RECLAIM": True,
                           "VOLUME_OK": micro_sweep_long.volume_ok, "HTF_ALIGNED": not micro_sweep_long.htf_hostile},
        }
        _micro_sweep_promoted = True
        _micro_sweep_source = micro_sweep_long
    if not short_entry and micro_sweep_short and getattr(micro_sweep_short, "detected", False) and not getattr(micro_sweep_short, "htf_hostile", True):
        short_entry = {
            "type": "micro_sweep", "mode": "reversal", "entry_profile_key": "liquidity_sweep_reversal",
            "micro_sweep": True, "micro_sweep_score": micro_sweep_short.score,
            "swept_level": micro_sweep_short.swept_level, "reclaim_price": micro_sweep_short.reclaim_price,
            "wick_ratio": micro_sweep_short.wick_ratio, "wick_vs_atr": micro_sweep_short.wick_vs_atr,
            "reclaim_bars": micro_sweep_short.reclaim_bars,
            "fail_fast_bars": int(lane_cfg.get("micro_sweep_max_reclaim_bars", 3) or 3),
            "lane_v_mode": "reversal",
            "confluence": {"MICRO_SWEEP_5M": True, "WICK_RECLAIM": True,
                           "VOLUME_OK": micro_sweep_short.volume_ok, "HTF_ALIGNED": not micro_sweep_short.htf_hostile},
        }
        _micro_sweep_promoted = True
        _micro_sweep_source = micro_sweep_short

    reverse_cfg = (v4_cfg.get("reverse_on_exit") or {}) if isinstance(v4_cfg.get("reverse_on_exit"), dict) else {}
    regime_v4 = classify_regime_v4(df_15m, df_1h, df_4h=df_4h, df_1d=df_1d)
    high_vol_pause = bool(regime_v4.get("atr_shock") or regime_v4.get("extreme_candle"))

    # --- Regime Manager: adapt params to market conditions ---
    _rm_cfg = (config.get("regime_manager") or {}) if isinstance(config.get("regime_manager"), dict) else {}
    if _rm_cfg.get("enabled", False):
        _exp_m = expansion_state.get("metrics") or {}
        regime_overrides = classify_trading_regime(
            vol_phase=str(expansion_state.get("phase", "COMPRESSION")),
            vol_confidence=int(expansion_state.get("confidence", 0)),
            adx_15m=float(regime_v4.get("adx_15m") or 0),
            rsi_15m=float(_exp_m.get("rsi", 50)),
            atr_ratio=float(_exp_m.get("tr_ratio", 1.0)),
            config=_rm_cfg,
        )
    else:
        regime_overrides = RegimeOverrides(
            regime_name="transition", size_multiplier=1.0,
            max_sl_pct=float(config["risk"]["max_sl_pct"]),
            tp_atr_mult=1.0,
            time_stop_bars=int(config["exits"]["time_stop_bars"]),
            early_save_bars=int(config["exits"]["early_save_bars"]),
            reasons=["disabled"], metrics={},
        )

    # --- HTF Trend Bias: block longs in crash, shorts in squeeze ---
    _htf_bias: dict = {}
    try:
        _htf_bias = classify_htf_trend_bias(df_1h)
        _htf_filter_cfg = (config.get("htf_direction_filter") or {}) if isinstance(config.get("htf_direction_filter"), dict) else {}
        if _htf_filter_cfg.get("enabled", True) and _htf_bias:
            _htf_state = str(_htf_bias.get("bias", "neutral"))
            _cap_types = set(_htf_filter_cfg.get("capitulation_entry_types") or [
                "reversal_impulse", "wick_rejection", "volume_climax_reversal", "fib_retrace", "liquidity_sweep",
            ])
            _long_type = str((long_entry or {}).get("type") or "")
            _short_type = str((short_entry or {}).get("type") or "")

            if _htf_state == "bearish_crash" and long_entry and _long_type not in _cap_types:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "htf_long_blocked_bearish_crash",
                    "htf_bias": _htf_bias.get("bias"),
                    "rsi_1h": _htf_bias.get("rsi_1h"),
                    "entry_type": _long_type,
                    "thought": f"HTF bearish crash (RSI={_htf_bias.get('rsi_1h'):.1f}): blocking non-capitulation long ({_long_type}). Only reversals allowed.",
                })
                long_entry = None
                long_v4 = None

            if _htf_state == "bullish_expansion" and short_entry and _short_type not in _cap_types:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "htf_short_blocked_bullish_expansion",
                    "htf_bias": _htf_bias.get("bias"),
                    "rsi_1h": _htf_bias.get("rsi_1h"),
                    "entry_type": _short_type,
                    "thought": f"HTF bullish expansion (RSI={_htf_bias.get('rsi_1h'):.1f}): blocking non-exhaustion short ({_short_type}). Only reversals allowed.",
                })
                short_entry = None
                short_v4 = None
    except Exception:
        _htf_bias = {}

    long_v4 = None
    short_v4 = None
    if long_entry:
        long_v4 = confluence_score_v4(
            regime=str(regime_v4.get("regime") or "neutral"),
            direction="long",
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            df_4h=df_4h,
            levels=levels,
            fibs=fibs,
            breakout_type=breakout_type_long,
            entry_type=long_entry.get("type"),
        )
    if short_entry:
        short_v4 = confluence_score_v4(
            regime=str(regime_v4.get("regime") or "neutral"),
            direction="short",
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            df_4h=df_4h,
            levels=levels,
            fibs=fibs,
            breakout_type=breakout_type_short,
            entry_type=short_entry.get("type"),
        )

    # --- Lane scoring: re-evaluate thresholds and optionally re-score ---
    lane_result_long = None
    lane_result_short = None
    try:
        if lane_cfg.get("enabled", False):
            if long_entry and long_v4:
                lane_result_long = select_lane(
                    entry_type=(long_entry or {}).get("type"),
                    regime=str(regime_v4.get("regime") or "neutral"),
                    expansion_phase=expansion_state.get("phase", "COMPRESSION"),
                    sweep=sweep_long,
                    squeeze=squeeze_long,
                    contract_ctx=contract_ctx,
                    config=lane_cfg,
                )
                if lane_result_long:
                    lw_cfg = lane_cfg.get("lane_weights") or {}
                    _rescore_entry = lane_result_long.rescore_as or (long_entry or {}).get("type")
                    if lw_cfg.get(lane_result_long.lane):
                        # Re-score with lane-specific weight profile
                        long_v4 = dict(confluence_score_v4(
                            regime=str(regime_v4.get("regime") or "neutral"),
                            direction="long", price=price, df_15m=df_15m,
                            df_1h=df_1h, df_4h=df_4h, levels=levels, fibs=fibs,
                            breakout_type=breakout_type_long,
                            entry_type=_rescore_entry,
                            lane=lane_result_long.lane,
                            lane_weights=lw_cfg,
                        ))
                    elif lane_result_long.rescore_as == "reversal_impulse":
                        long_v4 = dict(confluence_score_v4(
                            regime=str(regime_v4.get("regime") or "neutral"),
                            direction="long", price=price, df_15m=df_15m,
                            df_1h=df_1h, df_4h=df_4h, levels=levels, fibs=fibs,
                            breakout_type=breakout_type_long,
                            entry_type="reversal_impulse",
                        ))
                    else:
                        long_v4 = dict(long_v4)
                    long_v4["threshold"] = lane_result_long.threshold
                    long_v4["pass"] = bool(int(long_v4.get("score", 0)) >= lane_result_long.threshold)
            if short_entry and short_v4:
                lane_result_short = select_lane(
                    entry_type=(short_entry or {}).get("type"),
                    regime=str(regime_v4.get("regime") or "neutral"),
                    expansion_phase=expansion_state.get("phase", "COMPRESSION"),
                    sweep=sweep_short,
                    squeeze=squeeze_short,
                    contract_ctx=contract_ctx,
                    config=lane_cfg,
                )
                if lane_result_short:
                    lw_cfg_s = lane_cfg.get("lane_weights") or {}
                    _rescore_entry_s = lane_result_short.rescore_as or (short_entry or {}).get("type")
                    if lw_cfg_s.get(lane_result_short.lane):
                        short_v4 = dict(confluence_score_v4(
                            regime=str(regime_v4.get("regime") or "neutral"),
                            direction="short", price=price, df_15m=df_15m,
                            df_1h=df_1h, df_4h=df_4h, levels=levels, fibs=fibs,
                            breakout_type=breakout_type_short,
                            entry_type=_rescore_entry_s,
                            lane=lane_result_short.lane,
                            lane_weights=lw_cfg_s,
                        ))
                    elif lane_result_short.rescore_as == "reversal_impulse":
                        short_v4 = dict(confluence_score_v4(
                            regime=str(regime_v4.get("regime") or "neutral"),
                            direction="short", price=price, df_15m=df_15m,
                            df_1h=df_1h, df_4h=df_4h, levels=levels, fibs=fibs,
                            breakout_type=breakout_type_short,
                            entry_type="reversal_impulse",
                        ))
                    else:
                        short_v4 = dict(short_v4)
                    short_v4["threshold"] = lane_result_short.threshold
                    short_v4["pass"] = bool(int(short_v4.get("score", 0)) >= lane_result_short.threshold)
    except Exception:
        pass

    # Evolution engine: apply learned thresholds and lane performance overrides
    try:
        _evo_engine = EvolutionEngine()
        _lane_perf_overrides = get_lane_overrides(str(LOGS_DIR / "lane_performance.json"))
        for _dir_label, _v4_dict, _lr in [
            ("long", long_v4, lane_result_long),
            ("short", short_v4, lane_result_short),
        ]:
            if not _v4_dict or not isinstance(_v4_dict, dict):
                continue
            _etype = (_lr.lane if _lr else _v4_dict.get("entry_type", ""))
            if not _etype:
                continue
            # Check lane performance override (auto-disable losing lanes)
            _lp_ovr = _lane_perf_overrides.get(_etype, {})
            if _lp_ovr.get("action") == "disable":
                _v4_dict["pass"] = False
                _v4_dict["_blocked_by"] = "lane_performance_disabled"
                continue
            if _lp_ovr.get("action") == "raise_threshold":
                _v4_dict["threshold"] = int(_v4_dict.get("threshold", 50)) + 10
                _v4_dict["pass"] = bool(int(_v4_dict.get("score", 0)) >= _v4_dict["threshold"])
            # Evolution engine threshold optimization
            _base_thr = int(_v4_dict.get("threshold", 50))
            _evo_cfg = _evo_engine.get_lane_config(_etype, _base_thr)
            if _evo_cfg.get("threshold") != _base_thr:
                _v4_dict["threshold"] = _evo_cfg["threshold"]
                _v4_dict["pass"] = bool(int(_v4_dict.get("score", 0)) >= _v4_dict["threshold"])
                _v4_dict["_evo_threshold"] = _evo_cfg["threshold"]
    except Exception:
        pass

    entry = None
    direction = None
    selected_v4 = None
    breakout_type = "neutral"
    lane_result = None
    v4_candidates = []
    if long_entry and long_v4 and bool(long_v4.get("pass")):
        v4_candidates.append(("long", long_entry, long_v4, breakout_type_long, lane_result_long))
    if short_entry and short_v4 and bool(short_v4.get("pass")):
        v4_candidates.append(("short", short_entry, short_v4, breakout_type_short, lane_result_short))
    if v4_candidates:
        v4_candidates.sort(key=lambda it: (int((it[2] or {}).get("score") or 0), int(confluence_count((it[1] or {}).get("confluence") or {}))), reverse=True)
        # Recovery Mode / Post-TP bias: prefer specific direction if both sides qualify
        # (Use _st from load_state() at top of function — 'state' isn't defined until later)
        _bias_side = ""
        _rm_state = str(_st.get("recovery_mode") or "NORMAL")
        _last_loss = str(_st.get("last_loss_side") or "")
        if _rm_state == "RECOVERY" and _last_loss:
            _bias_side = "long" if _last_loss == "short" else ("short" if _last_loss == "long" else "")
        elif str(_st.get("post_tp_bias_side") or ""):
            _bias_side = str(_st.get("post_tp_bias_side"))
        if _bias_side and len(v4_candidates) > 1:
            # If both sides pass, prefer the biased side (as long as score is within 15 pts)
            _top_score = int((v4_candidates[0][2] or {}).get("score") or 0)
            for _ci, _cand in enumerate(v4_candidates):
                if _cand[0] == _bias_side:
                    _cand_score = int((_cand[2] or {}).get("score") or 0)
                    if _top_score - _cand_score <= 15:
                        v4_candidates.insert(0, v4_candidates.pop(_ci))
                    break
        direction, entry, selected_v4, breakout_type, lane_result = v4_candidates[0]
    else:
        # Backward-compatible fallback if neither side passes v4 threshold.
        if long_entry and short_entry:
            long_count = confluence_count(long_entry["confluence"])
            short_count = confluence_count(short_entry["confluence"])
            if long_count > short_count:
                entry = long_entry
                direction = "long"
                selected_v4 = long_v4
                breakout_type = breakout_type_long
            elif short_count > long_count:
                entry = short_entry
                direction = "short"
                selected_v4 = short_v4
                breakout_type = breakout_type_short
        elif long_entry:
            entry = long_entry
            direction = "long"
            selected_v4 = long_v4
            breakout_type = breakout_type_long
        elif short_entry:
            entry = short_entry
            direction = "short"
            selected_v4 = short_v4
            breakout_type = breakout_type_short

    regime_mode = str(v4_cfg.get("regime_mode", "dual") or "dual").lower().strip()
    selected_regime = str((selected_v4 or {}).get("regime") or regime_v4.get("regime") or "neutral").lower().strip()
    regime_mode_block: dict[str, Any] | None = None
    trend_modes = {"trend", "trend_only", "trend-only"}
    mr_modes = {"mr", "mr_only", "mr-only", "mean_reversion", "mean_reversion_only", "mean-reversion", "mean-reversion-only"}
    if entry and regime_mode in trend_modes and selected_regime != "trend":
        regime_mode_block = {"mode": "trend_only", "selected_regime": selected_regime}
        entry = None
        direction = None
        selected_v4 = None
        breakout_type = "neutral"
    if entry and regime_mode in mr_modes and selected_regime != "mean_reversion":
        regime_mode_block = {"mode": "mr_only", "selected_regime": selected_regime}
        entry = None
        direction = None
        selected_v4 = None
        breakout_type = "neutral"

    # -- Auto-regime mutex: prevent lane collision ----------------------------
    # When regime_mode == "auto", use the market regime from classify_regime_v4()
    # to block lanes that conflict with current conditions.  This prevents
    # Lane A ("buy the dip") and Lane M ("volume climax, short") from firing
    # in the same cycle.  Breakout lanes always pass.
    if entry and regime_mode == "auto" and lane_result:
        _market_regime = str(regime_v4.get("regime") or "neutral").lower().strip()
        if not lane_allowed_by_regime(lane_result, _market_regime):
            regime_mode_block = {
                "mode": "auto_regime_mutex",
                "market_regime": _market_regime,
                "blocked_lane": lane_result.lane,
                "lane_regime": lane_result.label,
            }
            entry = None
            direction = None
            selected_v4 = None
            breakout_type = "neutral"

    # Preserve this cycle's entry intent so an opposite exit can optionally re-enter same cycle.
    entry_candidate = entry
    direction_candidate = direction
    selected_v4_candidate = selected_v4
    breakout_type_candidate = breakout_type

    # Use pinned product_id from config; fall back to dynamic selection only if not set.
    _pinned = str(config.get("product_id") or "").strip()
    if _pinned:
        product_id = _pinned
        selection = {"product_id": _pinned, "reason": "config_pinned"}
    else:
        selection = api.select_xlm_product(config.get("selector", {}), direction=direction or "long")
        product_id = selection["product_id"] if selection else None

    # --- Contract context fetch (uses dynamically selected product) ---
    try:
        _cc_perp = product_id
        if not _cc_perp:
            _cc_perp = (load_state().get("open_position") or {}).get("product_id")
        if cc_mgr and _cc_perp:
            cc_mgr._perp_id = _cc_perp
            _cc_snap = cc_mgr.fetch()
            contract_ctx = cc_mgr.as_dict() if _cc_snap else {}
    except Exception:
        contract_ctx = {}
    try:
        _ob_product = product_id or signal_product_id
        if ob_mgr and _ob_product:
            ob_mgr._product_id = _ob_product
            _ob_snap = ob_mgr.fetch()
            orderbook_ctx = ob_mgr.as_dict() if _ob_snap else {}
    except Exception:
        orderbook_ctx = {}

    # ── Price sanity check ─────────────────────────────────────────────
    # If the candle-derived price diverges >10% from the contract mark
    # price, the candle data is stale/truncated (e.g. API timed out mid-
    # pagination and we got January data instead of today).  Abort cycle
    # to prevent phantom trades at wrong prices.
    _mark = float(contract_ctx.get("mark_price") or 0)
    if _mark > 0 and price > 0:
        _price_divergence = abs(price - _mark) / _mark
        if _price_divergence > 0.04:  # 4% threshold; 10% was too wide for $0.16 XLM at 4x leverage
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "price_sanity_fail",
                "candle_price": price,
                "mark_price": _mark,
                "divergence_pct": round(_price_divergence * 100, 1),
                "thought": f"candle price ${price:.4f} diverges {_price_divergence*100:.0f}% from mark ${_mark:.4f} — stale data, skipping cycle.",
            })
            return

    # Candle timestamp staleness guard: block new entries if feed is old.
    _stale_cfg = (config.get("data") or {}) if isinstance(config.get("data"), dict) else {}
    _max_candle_age_min = float(_stale_cfg.get("max_candle_age_min", 45) or 45)
    try:
        if not df_15m.empty and "time" in df_15m.columns and entry:
            import pandas as _pd_ts
            _last_candle_ts = df_15m["time"].iloc[-1]
            _last_candle_ts = _pd_ts.Timestamp(_last_candle_ts, tz="UTC") if getattr(_last_candle_ts, "tzinfo", None) is None else _last_candle_ts
            _candle_age_min = (now - _last_candle_ts).total_seconds() / 60.0
            if _candle_age_min > _max_candle_age_min:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "candle_stale_block",
                    "candle_age_min": round(_candle_age_min, 1),
                    "max_candle_age_min": _max_candle_age_min,
                    "thought": f"Candle data is {_candle_age_min:.0f}min old (limit {_max_candle_age_min:.0f}min). Blocking entry to prevent stale-data trade.",
                })
                entry = None
                direction = None
    except Exception:
        pass

    # Pending fill recovery: if a previous cycle sent an entry order but couldn't verify the fill,
    # retry verification now.  Complete the entry log or expire if >60s old.
    _pending_oid = (load_state() or {}).get("_pending_fill_order_id")
    if _pending_oid and not paper:
        _pending_meta = (load_state() or {}).get("_pending_fill_meta") or {}
        _pending_ts = _pending_meta.get("ts", "")
        _pending_expiry_sec = int(((config.get("exits") or {}).get("pending_fill_expiry_sec", 90)) or 90)
        _pending_age_s = 999
        try:
            _pending_age_s = (now - datetime.fromisoformat(_pending_ts)).total_seconds()
        except Exception:
            pass
        _pf = verify_fill(api, _pending_oid)
        _pf_ok = bool(_pf and _pf.get("filled"))
        if _pf_ok:
            _pf_price = float(_pf.get("average_filled_price") or 0)
            _pf_fees = float(_pf.get("total_fees") or 0)
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "pending_fill_verified",
                "order_id": _pending_oid,
                "fill_price": _pf_price,
                "fees_usd": _pf_fees,
                "age_s": round(_pending_age_s, 1),
            })
            # Update or reconstruct open position with verified fill price.
            _st = load_state()
            _op = _st.get("open_position")
            if isinstance(_op, dict):
                if _pf_price > 0:
                    _op["entry_price"] = _pf_price
                _op["entry_fees_usd"] = _pf_fees
                _op["entry_fill_verified"] = True
                _st["open_position"] = _op
            else:
                _restored = _materialize_pending_fill_position(_pending_meta, fill_price=_pf_price, fees_usd=_pf_fees)
                if isinstance(_restored, dict):
                    _st["open_position"] = _restored
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "pending_fill_position_restored",
                        "order_id": _pending_oid,
                        "entry_type": _restored.get("entry_type"),
                        "direction": _restored.get("direction"),
                        "size": _restored.get("size"),
                    })
            _st.pop("_pending_fill_order_id", None)
            _st.pop("_pending_fill_meta", None)
            save_state(_st)
        elif _pending_age_s > _pending_expiry_sec:
            # Before expiring, check if a position actually opened on the exchange.
            # If it did, the reconciler will handle it; clearing state is still safe.
            _exchange_pos = None
            _order_status = None
            try:
                if not paper and product_id:
                    _exchange_pos = api.get_position(product_id)
            except Exception:
                pass
            try:
                _pending_order = api.get_order(_pending_oid) or {}
                _pending_order = _pending_order.get("order", _pending_order)
                _order_status = _pending_order.get("status")
            except Exception:
                _order_status = None
            _st = load_state()
            _has_exchange_pos = float((_exchange_pos or {}).get("net_size") or 0) != 0
            log_signal({
                "timestamp": now.isoformat(),
                "type": "entry_expired_with_pos" if _has_exchange_pos else "entry_expired",
                "order_id": _pending_oid,
                "age_s": round(_pending_age_s, 1),
                "expiry_s": int(_pending_expiry_sec),
                "order_status": _order_status,
                "meta": _pending_meta,
                "exchange_pos": _exchange_pos,
                "thought": "fill unconfirmed after 60s; exchange pos found, reconciler will handle" if _has_exchange_pos else "fill unconfirmed after 60s, no exchange position found",
            })
            if _has_exchange_pos:
                slack_alert.send(
                    "WARNING: pending fill expired but exchange shows open position. Reconciler will handle.",
                    level="warning",
                )
            _st.pop("_pending_fill_order_id", None)
            _st.pop("_pending_fill_meta", None)
            save_state(_st)

    state, reset_info = _reset_daily(load_state(), now)
    if reset_info is not None:
        log_decision(config, {"timestamp": now.isoformat(), "reason": "daily_reset", **reset_info})
        # Send daily summary for the previous day before reset
        if _nontrade_slack_allowed(config, state):
            slack_alert.daily_summary(
                trades=int(reset_info.get("prev_trades") or 0),
                wins=0,  # not tracked separately in reset_info
                losses=int(reset_info.get("prev_losses") or 0),
                pnl_usd=float(reset_info.get("prev_pnl") or 0),
                exchange_pnl_usd=float(reset_info.get("prev_exchange_pnl") or 0) or None,
                equity=float(state.get("exchange_equity_usd") or 0) or None,
            )
        # Flush structured audit trail (metrics.json + daily_report.md)
        try:
            _nav = float(state.get("exchange_equity_usd") or 0) or None
            _audit_logger.flush_daily(nav=_nav)
        except Exception:
            pass
        # Write daily brief for AI context (last 3 days perf summary)
        try:
            _write_daily_brief(config, state, now)
        except Exception:
            pass
    # Check shift summary schedule (intraday 1 PM, overnight 5 AM, daily 8 PM)
    try:
        state = _check_shift_summaries(config, state, now)
    except Exception:
        pass
    state["loss_debt_usd"] = float(state.get("loss_debt_usd") or 0.0)
    state["consecutive_losses"] = int(state.get("consecutive_losses") or 0)
    state["conversion_cost_today_usd"] = float(state.get("conversion_cost_today_usd") or 0.0)
    state["vol_state"] = expansion_state.get("phase", "COMPRESSION")
    market_cfg = (config.get("market_intel") or {}) if isinstance(config.get("market_intel"), dict) else {}
    market_intel: dict[str, Any] = {}
    liquidation_cfg = (
        (market_cfg.get("liquidation_feed") or {})
        if isinstance(market_cfg.get("liquidation_feed"), dict)
        else {}
    )
    liquidation_ctx: dict[str, Any] = {}
    if bool(market_cfg.get("enabled", True)):
        try:
            market_intel = get_market_intel(market_cfg, DATA_DIR, now_utc=now)
            if isinstance(market_intel, dict) and market_intel:
                _update_dashboard_feed(
                    {
                        "ts": market_intel.get("fetched_at") or now.isoformat(),
                        "market_news": market_intel,
                        "market_news_ts": market_intel.get("fetched_at") or now.isoformat(),
                        "market_news_summary": market_intel.get("summary"),
                        "market_news_risk_flags": market_intel.get("risk_flags"),
                    },
                    append_timeseries=False,
                )
                if bool(market_intel.get("is_fresh")) or (not MARKET_NEWS_PATH.exists()):
                    log_market_news(market_intel)
                digest_every_min = int(market_cfg.get("slack_interval_minutes", 60) or 60)
                digest_max_items = int(market_cfg.get("slack_max_items", 5) or 5)
                digest_enabled = bool(market_cfg.get("slack_digest_enabled", True))
                digest_key = {
                    "summary": market_intel.get("summary"),
                    "headlines": [
                        str((h or {}).get("title") or "")
                        for h in (market_intel.get("headlines") or [])[:10]
                        if isinstance(h, dict)
                    ],
                }
                digest_hash = hashlib.md5(json.dumps(digest_key, sort_keys=True).encode()).hexdigest()[:12]
                last_digest_ts = _parse_ts_utc(state.get("market_news_last_slack_ts"))
                due = (
                    last_digest_ts is None
                    or (now - last_digest_ts).total_seconds() >= max(5, digest_every_min) * 60
                )
                changed = str(state.get("market_news_last_hash") or "") != digest_hash
                if (
                    digest_enabled
                    and bool(market_intel.get("is_fresh"))
                    and due
                    and changed
                    and slack_alert.is_enabled()
                    and _nontrade_slack_allowed(config, state)
                ):
                    slack_alert.market_news_update(
                        summary=str(market_intel.get("summary") or ""),
                        bullets=_market_news_digest_bullets(market_intel, max_items=digest_max_items),
                        risk_flags=list(market_intel.get("risk_flags") or []),
                    )
                    state["market_news_last_slack_ts"] = now.isoformat()
                    state["market_news_last_hash"] = digest_hash
                state["market_news_last_seen_ts"] = now.isoformat()
        except Exception as e:
            try:
                durable.log_event("market_intel_error", {"error": str(e)})
            except Exception:
                pass
    market_intel_state: dict[str, Any] = {}
    try:
        market_intel_state = market_intel_service.refresh_market_intel_state(
            config=config,
            data_dir=DATA_DIR,
            logs_dir=LOGS_DIR,
            market_intel=market_intel,
            market_brief=perplexity_advisor.get_latest_brief(),
            weekly_research=perplexity_advisor.get_latest_weekly_market_research(config=config),
            now_utc=now,
        )
    except Exception:
        try:
            market_intel_state = market_intel_service.get_latest_market_intel_state(DATA_DIR)
        except Exception:
            market_intel_state = {}
    try:
        _market_intel_disk = market_intel_service.get_latest_market_intel_state(DATA_DIR)
        if isinstance(_market_intel_disk, dict) and _market_intel_disk:
            market_intel_state = _market_intel_disk
    except Exception:
        pass
    try:
        liquidation_ctx = read_liquidation_snapshot(DATA_DIR, config=liquidation_cfg)
    except Exception:
        liquidation_ctx = {}
    if not paper:
        _observe_spot_balance_changes(
            config=config,
            state=state,
            api=api,
            durable=durable,
            now=now,
        )
    rec_incidents_count = 0
    # Exchange-truth reconciliation on every run to survive restart churn and forced exchange closes.
    try:
        # Prefer contract mark price (from exchange) over candle price for reconciliation —
        # candle price can be stale if the API fetch was truncated.
        _reconcile_mark = float(contract_ctx.get("mark_price") or 0) or price
        rec = reconcile_exchange_truth(api, config, state, durable, now=now, mark_price=_reconcile_mark)
        state = rec.state
        rec_incidents_count = len(rec.incidents or [])
        for incident in rec.incidents:
            log_incident(incident)
            durable.log_event("incident", incident)
            # Alert on unauthorized positions on the account
            if str(incident.get("type")) == "UNAUTHORIZED_POSITION_DETECTED":
                try:
                    slack_alert.unauthorized_position(
                        product_id=str(incident.get("product_id", "?")),
                        direction=str(incident.get("direction", "?")),
                        size=str(incident.get("size", "?")),
                    )
                except Exception:
                    pass
        if rec.closed_trade:
            rec_trade = _with_lifecycle_fields(
                dict(rec.closed_trade),
                entry_time=rec.closed_trade.get("entry_time"),
                exit_time=rec.closed_trade.get("exit_time") or now.isoformat(),
            )
            # Reconciler exits are inherently exchange-verified — position was
            # confirmed closed on exchange before we got here.
            rec_trade["fill_verified"] = True
            log_trade(config, rec_trade)
            slack_alert.reconciler_exit(
                direction=str(rec_trade.get("side") or ""),
                pnl_usd=_to_float(rec_trade.get("pnl_usd")),
                exit_reason=str(rec_trade.get("exit_reason") or "exchange_side_close"),
            )
            rec_pnl = _to_float(rec_trade.get("pnl_usd"))
            rec_result = str(rec_trade.get("result") or "")
            state["last_exit_time"] = str(rec_trade.get("exit_time") or now.isoformat())
            # exchange_side_close is NOT a strategy failure — don't count toward
            # consecutive_losses or trigger cooldown.  PnL and debt still tracked.
            if rec_pnl is not None:
                if rec_result == "loss":
                    state["loss_debt_usd"] = float(state.get("loss_debt_usd") or 0.0) + abs(float(rec_pnl))
                elif rec_result == "win" and rec_pnl > 0:
                    state["loss_debt_usd"] = max(0.0, float(state.get("loss_debt_usd") or 0.0) - float(rec_pnl))
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "exchange_side_close",
                    "product_id": rec_trade.get("product_id"),
                    "side": rec_trade.get("side"),
                    "size": rec_trade.get("size"),
                    "entry_time": rec_trade.get("entry_time"),
                    "exit_time": rec_trade.get("exit_time"),
                    "time_in_trade_min": rec_trade.get("time_in_trade_min"),
                    "exit_price": rec_trade.get("exit_price"),
                    "pnl_usd": rec_trade.get("pnl_usd"),
                    "result": rec_trade.get("result"),
                    "loss_debt_usd": state.get("loss_debt_usd"),
                },
            )
        save_state(state)
    except Exception as e:
        err = {"timestamp": now.isoformat(), "type": "RECONCILE_ERROR", "error": str(e)}
        log_incident(err)
        durable.log_event("recovery_error", {"error": str(e)})

    eq = float(state.get("equity_start_usd") or 0.0)
    if eq <= 0:
        eq = float(api.get_futures_equity() or 0.0)
    if eq <= 0:
        eq = float(_extract_total_funds_for_margin(api.get_futures_balance_summary() or {}) or 0.0)
    if eq <= 0:
        # Fallback: sum spot + derivatives balances directly.
        # This handles CDE accounts where equity API returns 0 but
        # the actual capital is sitting in the derivatives wallet.
        try:
            from risk.balance_reconciler import get_balance_snapshot as _get_snap
            _snap = _get_snap(api, currencies=["USD", "USDC"])
            if _snap.fetch_ok:
                eq = _snap.total_equity or (_snap.spot_usdc + _snap.spot_usd + _snap.derivatives_usdc)
        except Exception:
            pass
    if eq > 0:
        state["equity_start_usd"] = eq
        save_state(state)

    equity_start = float(state.get("equity_start_usd") or 0.0)
    pnl_today = float(state.get("pnl_today_usd") or 0.0)
    transfers_today = float(state.get("transfers_today_usd") or 0.0)
    conversion_cost_today = float(state.get("conversion_cost_today_usd") or 0.0)
    cooldown = _cooldown_active(state, now)

    # Coinbase-style margin ratio guard (read-only unless enforcement is enabled).
    mp_cfg = (config.get("margin_policy") or {}) if isinstance(config.get("margin_policy"), dict) else {}
    mp_enabled = bool(mp_cfg.get("enabled", False))
    mp_enforcement = str(mp_cfg.get("enforcement", "block_entries")).lower().strip()  # log_only/block_entries/reduce_only/exit_all
    mp_decision = None
    balance_summary = None
    if (not paper) and mp_enabled:
        try:
            bs = api.get_futures_balance_summary() or {}
            balance_summary = bs
            from datetime import time as _time_cls
            _cutoff_h = int(mp_cfg.get("cutoff_hour_et", 16) or 16)
            _cutoff_m = int(mp_cfg.get("cutoff_minute_et", 0) or 0)
            _intra_h = int(mp_cfg.get("intraday_start_hour_et", 8) or 8)
            _intra_m = int(mp_cfg.get("intraday_start_minute_et", 0) or 0)
            mp_decision = evaluate_margin_policy(
                bs,
                now_utc=now,
                cutoff_et=_time_cls(_cutoff_h, _cutoff_m),
                intraday_start_et=_time_cls(_intra_h, _intra_m),
                pre_cutoff_minutes=int(mp_cfg.get("pre_cutoff_minutes", 20) or 20),
                safe_lt=float(mp_cfg.get("safe_lt", 0.80) or 0.80),
                warning_lt=float(mp_cfg.get("warning_lt", 0.90) or 0.90),
                danger_lt=float(mp_cfg.get("danger_lt", 0.95) or 0.95),
                liquidation_gte=float(mp_cfg.get("liquidation_gte", 1.00) or 1.00),
            )
            log_margin_policy({
                "timestamp": now.isoformat(),
                "tier": mp_decision.tier,
                "actions": mp_decision.actions,
                "reasons": mp_decision.reasons,
                **(mp_decision.metrics or {}),
            })
            durable.set_kv("margin_policy", {
                "timestamp": now.isoformat(),
                "tier": mp_decision.tier,
                "actions": mp_decision.actions,
                "reasons": mp_decision.reasons,
                "metrics": mp_decision.metrics,
            })
        except Exception as e:
            durable.log_event("margin_policy_error", {"error": str(e)})

    # Update exchange equity snapshot every cycle (for dashboard)
    if balance_summary and isinstance(balance_summary, dict):
        try:
            _bs_root = balance_summary.get("balance_summary") or {}
            _eq_val = _bs_root.get("equity", {})
            _current_eq = float(_eq_val.get("value") or 0) if isinstance(_eq_val, dict) else float(_eq_val or 0)
            if _current_eq > 0:
                state["exchange_equity_usd"] = _current_eq
                _eq_start = float(state.get("equity_start_usd") or 0)
                _transfers = float(state.get("transfers_today_usd") or 0)
                if _eq_start > 0:
                    state["exchange_pnl_today_usd"] = _current_eq - _eq_start + _transfers
        except Exception:
            pass

    # Log equity tick for dashboard chart (includes full portfolio value)
    _eq_for_tick = float(state.get("exchange_equity_usd") or 0)
    if _eq_for_tick <= 0:
        _eq_for_tick = float(state.get("equity_start_usd") or 0) + float(state.get("pnl_today_usd") or 0)
    _mark_for_tick = float(contract_ctx.get("mark_price") or 0) if contract_ctx else 0
    _cash_map = state.get("last_spot_cash_map") or {}
    # Portfolio total: use Coinbase total_usd_balance (cfm + cbi USD, no double-count) + USDC
    # Old formula (_eq_for_tick + _spot_total) double-counted because CFM equity includes cross-margin from spot
    _portfolio_for_tick = _eq_for_tick  # default fallback
    if balance_summary and isinstance(balance_summary, dict):
        _bs_r = balance_summary.get("balance_summary") or {}
        _tub = _bs_r.get("total_usd_balance", {})
        _total_usd = float(_tub.get("value") or 0) if isinstance(_tub, dict) else float(_tub or 0)
        if _total_usd > 0:
            _usdc_val = float((_cash_map or {}).get("USDC") or 0)
            _portfolio_for_tick = _total_usd + _usdc_val
    if _eq_for_tick > 0:
        _log_equity_tick(_eq_for_tick, _mark_for_tick, state, portfolio_usd=_portfolio_for_tick)

    # Overnight trading auto-detection: check if equity can cover overnight margin for 1 contract.
    # This uses PROJECTED margin (would equity cover 1 contract at overnight rates?) not just current MR.
    overnight_cfg = mp_cfg.get("overnight_trading") or {}
    overnight_mode = str(overnight_cfg.get("mode", "auto")).lower()
    overnight_trading_ok = False
    if overnight_mode == "always":
        overnight_trading_ok = True
    elif overnight_mode == "never":
        overnight_trading_ok = False
    elif overnight_mode == "auto" and mp_decision and isinstance(mp_decision.metrics, dict):
        total_funds = _to_float(mp_decision.metrics.get("total_funds_for_margin"))
        mr_overnight = _to_float(mp_decision.metrics.get("mr_overnight"))
        overnight_safe_mr = float(overnight_cfg.get("overnight_safe_mr", 0.85) or 0.85)
        min_equity_ratio = float(overnight_cfg.get("min_equity_ratio", 1.20) or 1.20)

        # Use futures_buying_power if available — it includes USDC cross-margin collateral
        # that total_usd_balance misses. This is what Coinbase actually uses for margin.
        _buying_power = None
        try:
            _inner = getattr(api, "api", api)
            _buying_power = float(_inner.get_cfm_buying_power() or 0)
        except Exception:
            pass
        if _buying_power and _buying_power > (total_funds or 0):
            total_funds = _buying_power

        # Method 1: If there's an open position, check actual overnight MR
        has_position = bool(state.get("open_position"))
        if has_position and mr_overnight is not None:
            overnight_trading_ok = mr_overnight < overnight_safe_mr

        # Method 2: If no position, check if equity could COVER 1 contract overnight.
        # Overnight margin per contract ≈ notional × 0.52 (for 4x leverage products).
        if not has_position and total_funds is not None:
            contract_notional = float(price) * float(config.get("contract_size", 5000) or 5000)
            overnight_margin_1c = contract_notional * 0.52  # ~$432 at $0.166
            projected_mr = overnight_margin_1c / total_funds if total_funds > 0 else 99.0
            overnight_trading_ok = projected_mr < overnight_safe_mr and total_funds >= overnight_margin_1c * min_equity_ratio

    # Detect transition: log when overnight trading unlocks/locks
    _prev_overnight = str(state.get("_overnight_trading_ok") or "")
    _curr_overnight = "yes" if overnight_trading_ok else "no"
    if _prev_overnight != _curr_overnight:
        state["_overnight_trading_ok"] = _curr_overnight
        event_type = "OVERNIGHT_TRADING_UNLOCKED" if overnight_trading_ok else "OVERNIGHT_TRADING_LOCKED"
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "overnight_trading_change",
            "overnight_trading": overnight_trading_ok,
            "event": event_type,
            "mr_overnight": (mp_decision.metrics or {}).get("mr_overnight") if mp_decision else None,
            "total_funds": (mp_decision.metrics or {}).get("total_funds_for_margin") if mp_decision else None,
            "margin_window": (mp_decision.metrics or {}).get("margin_window") if mp_decision else None,
        })
        durable.log_event(event_type.lower(), {
            "overnight_trading": overnight_trading_ok,
            "mr_overnight": (mp_decision.metrics or {}).get("mr_overnight") if mp_decision else None,
        })

    # ── Recovery Mode evaluation ──────────────────────────────────────────
    _prev_recovery_mode = str(state.get("recovery_mode") or "NORMAL")
    recovery_info = _evaluate_recovery_mode(state, config, now)
    post_tp_bias = _evaluate_post_tp_bias(state, config, now)
    _new_recovery_mode = recovery_info.get("mode", "NORMAL")
    if _new_recovery_mode != _prev_recovery_mode:
        try:
            pnl_today_rm = float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd") or 0)
            slack_alert.recovery_mode_change(
                new_mode=_new_recovery_mode,
                pnl_today=pnl_today_rm,
                debt=recovery_info.get("recovery_debt", 0),
                goal=recovery_info.get("recovery_goal", 0),
                preferred_side=recovery_info.get("preferred_side", ""),
            )
        except Exception:
            pass

    # PLRL-3 high-cadence status log (even when we are flat) so the dashboard stays live.
    plrl_cfg = (config.get("plrl3") or {}) if isinstance(config.get("plrl3"), dict) else {}
    if (not paper) and bool(plrl_cfg.get("enabled", False)):
        try:
            if balance_summary is None:
                balance_summary = api.get_futures_balance_summary() or {}
            # Reuse the margin policy evaluation as the canonical MR source.
            if mp_decision is None:
                mp_decision = evaluate_margin_policy(balance_summary, now_utc=now)
            log_plrl3({
                "timestamp": now.isoformat(),
                "strategy": "PLRL-3",
                "action": "IDLE" if not state.get("open_position") else "TICK",
                "rescue_step": int((state.get("open_position") or {}).get("plrl3_rescue_step") or 0),
                "max_rescues": int(plrl_cfg.get("max_rescues", 3) or 3),
                "mr_intraday": (mp_decision.metrics or {}).get("mr_intraday"),
                "mr_overnight": (mp_decision.metrics or {}).get("mr_overnight"),
                "active_mr": (mp_decision.metrics or {}).get("active_mr"),
                "active_window": (mp_decision.metrics or {}).get("active_mr_source"),
                "next_rescue_at": None,
                "fail_at": float(plrl_cfg.get("fail_mr", 0.95) or 0.95),
                "enforcement": str(plrl_cfg.get("enforcement", "log_only")).lower().strip(),
            })
        except Exception as e:
            durable.log_event("plrl3_log_error", {"error": str(e)})

    open_pos = state.get("open_position")
    if (not paper) and mp_decision:
        metrics = (mp_decision.metrics or {}) if isinstance(mp_decision.metrics, dict) else {}
        active_mr = float(metrics.get("active_mr") or 0.0)
        danger_mr = float(mp_cfg.get("danger_lt", 0.95) or 0.95)
        liq_mr = float(mp_cfg.get("liquidation_gte", 1.00) or 1.00)

        if active_mr >= danger_mr:
            slack_alert.margin_warning(tier=mp_decision.tier, margin_ratio=active_mr)

        if active_mr >= liq_mr:
            liq_incident = {
                "timestamp": now.isoformat(),
                "type": "LIQUIDATION_TIER_OBSERVED",
                "active_mr": active_mr,
                "tier": mp_decision.tier,
                "actions": mp_decision.actions,
                "metrics": metrics,
            }
            log_incident(liq_incident)
            durable.log_event("liquidation_tier_observed", {"active_mr": active_mr, "tier": mp_decision.tier})

        if open_pos and active_mr >= danger_mr:
            # MIRROR STRATEGY: Don't panic sell. Add margin from spot instead.
            _spot_usdc = float((state.get("last_spot_cash_map") or {}).get("USDC") or 0)
            _add_amount = min(_spot_usdc * 0.5, 50.0)  # add up to half of spot or $50
            if _add_amount >= 5.0:
                try:
                    _topup = api.transfer_funds("spot_to_futures", _add_amount)
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "margin_rescue_topup",
                        "active_mr": active_mr,
                        "amount_usd": _add_amount,
                        "spot_available": _spot_usdc,
                        "topup_result": str(_topup)[:200],
                        "thought": f"Near liquidation (MR={active_mr:.3f}). Adding ${_add_amount:.2f} margin instead of panic selling.",
                    })
                except Exception as _te:
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "margin_rescue_failed",
                        "active_mr": active_mr,
                        "error": str(_te)[:200],
                    })
                save_state(state)
                return  # skip the panic sell, margin added
            # Only panic sell if we have NO spot funds to add
            pos_product_id = str(open_pos.get("product_id") or product_id or "")
            direction = str(open_pos.get("direction") or "long")
            entry_price = float(open_pos.get("entry_price") or 0.0)
            size = int(open_pos.get("size") or 0)
            # Guard: verify position actually exists on exchange before emergency exit.
            # Prevents phantom exits when state has ghost position from unverified fill.
            try:
                _mr_exch_pos = api.get_position(pos_product_id) if pos_product_id else None
                _mr_exch_size = abs(float((_mr_exch_pos or {}).get("number_of_contracts") or (_mr_exch_pos or {}).get("size") or 0))
            except Exception:
                _mr_exch_size = -1  # API failed, proceed with caution
            if _mr_exch_size == 0:
                # No position on exchange. Clear ghost state and skip exit.
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "GHOST_EMERGENCY_EXIT_PREVENTED",
                    "product_id": pos_product_id,
                    "active_mr": active_mr,
                    "thought": "State had open_position but exchange has none. Clearing ghost.",
                })
                state["open_position"] = None
                save_state(state)
                durable.set_kv("open_position", None)
                # Ghost position cleared. Do not proceed with emergency exit.
                return
            entry_time_raw = open_pos.get("entry_time")
            exit_time_iso = now.isoformat()
            cancel_info = api.cancel_open_orders(product_id=pos_product_id) if pos_product_id else {"attempted": 0, "cancelled": 0, "errors": 0}
            close_info = api.close_cfm_position(pos_product_id, paper=False) if pos_product_id else {"ok": False, "note": "missing_product_id"}

            contract_size = float(open_pos.get("contract_size") or 0.0)
            if contract_size <= 0 and pos_product_id:
                cs_info = api.estimate_required_margin(pos_product_id, 1, direction, price=price)
                contract_size = float(cs_info.get("contract_size") or 0.0)
            pnl_pct = 0.0
            if entry_price > 0:
                pnl_pct = (price - entry_price) / entry_price
                if direction == "short":
                    pnl_pct = -pnl_pct
            pnl_usd = None
            if contract_size > 0 and size > 0:
                raw = (price - entry_price) * contract_size * size
                pnl_usd = -raw if direction == "short" else raw
            result = "win" if pnl_pct > 0 else "loss" if pnl_pct < 0 else "flat"

            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "emergency_exit_mr",
                    "product_id": pos_product_id,
                    "entry_time": entry_time_raw,
                    "exit_time": exit_time_iso,
                    "time_in_trade_min": _minutes_between(entry_time_raw, exit_time_iso),
                    "active_mr": active_mr,
                    "cancel_info": cancel_info,
                    "close_info": close_info,
                },
            )
            log_fill(
                {
                    "timestamp": now.isoformat(),
                    "reason": "emergency_exit_mr",
                    "product_id": pos_product_id,
                    "cancel_info": cancel_info,
                    "close_info": close_info,
                }
            )
            # Verify emergency exit fill
            _emr_oid = None
            try:
                _emr_oid = ((close_info or {}).get("result") or {}).get("order_id")
            except Exception:
                pass
            _emr_fill = verify_fill(api, _emr_oid) if _emr_oid else None
            _emr_verified = bool(_emr_fill and _emr_fill.get("filled"))
            _emr_fill_price = float(_emr_fill.get("average_filled_price") or 0) if _emr_fill else 0
            _emr_fees = float(_emr_fill.get("total_fees") or 0) if _emr_fill else 0
            _emr_exit_price = _emr_fill_price if _emr_fill_price > 0 else price
            # Force-flatten with retries — emergency exits are critical
            _emr_flatten = _force_flatten_position(api, pos_product_id, max_rounds=3)
            if _emr_flatten.get("order_id") and not _emr_oid:
                _emr_oid = _emr_flatten["order_id"]
                _emr_fill = verify_fill(api, _emr_oid) if _emr_oid else None
                _emr_verified = bool(_emr_fill and _emr_fill.get("filled"))
                _emr_fill_price = float(_emr_fill.get("average_filled_price") or 0) if _emr_fill else 0
                _emr_fees = float(_emr_fill.get("total_fees") or 0) if _emr_fill else 0
                _emr_exit_price = _emr_fill_price if _emr_fill_price > 0 else price
            if not _emr_flatten["flat"]:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "GHOST_EXIT_PREVENTED",
                    "exit_reason": "emergency_exit_mr",
                    "product_id": pos_product_id,
                    "flatten_attempts": _emr_flatten["attempts"],
                    "thought": f"Emergency: {_emr_flatten['attempts']} close attempts, position still open.",
                })
                slack_alert.send(
                    f"EMERGENCY GHOST EXIT — {_emr_flatten['attempts']} close attempts failed. Position still open!",
                    level="error",
                )
                save_state(state)
                return
            # Recalculate PnL from verified fill price (same as normal exit)
            if _emr_fill_price > 0 and entry_price > 0:
                if direction == "long":
                    pnl_pct = (_emr_fill_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - _emr_fill_price) / entry_price
                pnl_usd = pnl_pct * entry_price * size * contract_size if (contract_size > 0 and size > 0) else None
            # Subtract fees from PnL
            _entry_fees = float(open_pos.get("entry_fees_usd") or 0)
            _total_fees = _entry_fees + _emr_fees
            # Fallback: use estimated fees if actual fees are 0 (fill verification failed)
            if _total_fees <= 0:
                _total_fees = float(open_pos.get("estimated_round_trip_fees") or 0)
            if pnl_usd is not None and _total_fees > 0:
                pnl_usd -= _total_fees
            result = "win" if pnl_pct > 0 else "loss" if pnl_pct < 0 else "flat"
            log_trade(
                config,
                _with_lifecycle_fields(
                    {
                        "timestamp": now.isoformat(),
                        "product_id": pos_product_id,
                        "side": direction,
                        "size": size,
                        "entry_price": entry_price if entry_price > 0 else None,
                        "exit_price": _emr_exit_price,
                        "pnl_pct": pnl_pct,
                        "pnl_usd": pnl_usd,
                        "result": result,
                        "exit_reason": "emergency_exit_mr",
                        "exit_order_id": _emr_oid,
                        "fill_verified": _emr_verified,
                        "entry_fees_usd": _entry_fees,
                        "exit_fees_usd": _emr_fees,
                        "total_fees_usd": _total_fees,
                    },
                    entry_time=entry_time_raw,
                    exit_time=exit_time_iso,
                ),
            )
            log_incident(
                {
                    "timestamp": now.isoformat(),
                    "type": "EMERGENCY_EXIT_TRIGGERED",
                    "product_id": pos_product_id,
                    "active_mr": active_mr,
                    "pnl_usd": pnl_usd,
                    "result": result,
                }
            )
            durable.log_event(
                "emergency_exit_mr",
                {"product_id": pos_product_id, "active_mr": active_mr, "result": result},
            )
            # Guard against double-counting (same as main exit chain)
            _last_counted_entry = str(state.get("_last_exit_counted_entry") or "")
            _this_entry = str(entry_time_raw or "")
            _already_counted = bool(_last_counted_entry and _this_entry and _last_counted_entry == _this_entry)
            if not _already_counted:
                state["_last_exit_counted_entry"] = _this_entry
                if result == "loss":
                    state["losses"] = int(state.get("losses") or 0) + 1
                    state["consecutive_losses"] = int(state.get("consecutive_losses") or 0) + 1
                    state["consecutive_wins"] = 0
                    if pnl_usd is not None:
                        state["loss_debt_usd"] = float(state.get("loss_debt_usd") or 0.0) + abs(float(pnl_usd))
                elif result == "win":
                    state["consecutive_losses"] = 0
                    state["consecutive_wins"] = int(state.get("consecutive_wins") or 0) + 1
                    if pnl_usd is not None and pnl_usd > 0:
                        state["loss_debt_usd"] = max(0.0, float(state.get("loss_debt_usd") or 0.0) - float(pnl_usd))
                if pnl_usd is not None:
                    state["pnl_today_usd"] = float(state.get("pnl_today_usd") or 0.0) + float(pnl_usd)
                # Fetch exchange equity for reality check
                try:
                    _post_exit_eq = float(api.get_futures_equity() or 0)
                    if _post_exit_eq > 0:
                        state["exchange_equity_usd"] = _post_exit_eq
                        _eq_start = float(state.get("equity_start_usd") or 0)
                        _transfers = float(state.get("transfers_today_usd") or 0)
                        if _eq_start > 0:
                            state["exchange_pnl_today_usd"] = _post_exit_eq - _eq_start + _transfers
                except Exception:
                    pass
            _emr_held = (now - datetime.fromisoformat(str(open_pos.get("entry_time") or now.isoformat()))).total_seconds() / 60.0 if open_pos.get("entry_time") else 0
            _emr_exp = ((open_pos.get("exit_watch") or {}).get("close_eta") or {}).get("expected_hold_min")
            slack_alert.trade_exit(
                direction=direction, exit_reason="emergency_exit_mr",
                entry_price=entry_price, exit_price=_emr_exit_price,
                pnl_usd=pnl_usd, pnl_pct=pnl_pct, fill_verified=_emr_verified,
                held_min=_emr_held, expected_hold_min=_emr_exp,
                size=int(open_pos.get("size") or 1),
            )
            try:
                slack_intel.post_cycle_intel({"price": _emr_exit_price, "direction": direction, "pnl_usd": pnl_usd, "exit_reason": "emergency_exit_mr"}, event="trade_close")
            except Exception:
                pass
            state["last_exit_time"] = exit_time_iso
            state["open_position"] = None
            save_state(state)
            durable.set_kv("open_position", None)
            return

        if (not open_pos) and active_mr >= liq_mr:
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "halt_trading_mr",
                    "tier": mp_decision.tier,
                    "active_mr": active_mr,
                    "actions": mp_decision.actions,
                },
            )
            save_state(state)
            return

    # Manage open position exits
    if open_pos:
        continue_after_exit = False
        durable.log_event("manage_open_position", {"paper": bool(paper)})
        pos_product_id = str(open_pos.get("product_id") or product_id or "")
        if pos_product_id and not open_pos.get("product_id"):
            open_pos["product_id"] = pos_product_id
        entry_price = float(open_pos.get("entry_price") or 0.0)
        if entry_price <= 0:
            entry_price = float(price)
            open_pos["entry_price"] = entry_price
            durable.log_event("recovered_entry_price_fallback", {"entry_price": entry_price})

        direction = str(open_pos.get("direction") or "long")
        leverage = int(open_pos.get("leverage") or config.get("leverage") or 1)
        contract_size = _to_float(open_pos.get("contract_size"), 0.0) or 0.0
        if contract_size <= 0 and pos_product_id:
            cs_info = api.estimate_required_margin(pos_product_id, 1, direction, price=price)
            contract_size = float(cs_info.get("contract_size") or 0.0)
            if contract_size > 0:
                open_pos["contract_size"] = contract_size
        try:
            entry_time = datetime.fromisoformat(str(open_pos.get("entry_time") or ""))
        except Exception:
            entry_time = now
            open_pos["entry_time"] = now.isoformat()

        bars_since = int((now - entry_time).total_seconds() // (15 * 60))
        _hold_secs = (now - entry_time).total_seconds() if entry_time else 9999
        # Hard max_hold_hours wall: force exit regardless of PnL to prevent overnight drift
        _cb_cfg_pos = (v4_cfg.get("circuit_breaker") or {}) if isinstance(v4_cfg.get("circuit_breaker"), dict) else {}
        _max_hold_h = float(_cb_cfg_pos.get("max_hold_hours", 0) or 0)
        _max_hold_triggered = False
        if _max_hold_h > 0:
            _hold_hours = (now - entry_time).total_seconds() / 3600
            if _hold_hours >= _max_hold_h:
                _max_hold_triggered = True
                durable.log_event("max_hold_hours_triggered", {"hold_hours": round(_hold_hours, 2), "max": _max_hold_h})
        # Use perp mark price for PnL (matches Coinbase settlement), fall back to spot
        _mark_price = _to_float(contract_ctx.get("mark_price"), None)
        _pnl_price = _mark_price if _mark_price and _mark_price > 0 else price
        pnl_pct = (_pnl_price - entry_price) / entry_price if entry_price > 0 else 0.0
        if direction == "short":
            pnl_pct = -pnl_pct
        pnl_usd_live = None
        if contract_size > 0 and int(open_pos.get("size") or 0) > 0:
            raw_live = (_pnl_price - entry_price) * float(contract_size) * float(open_pos.get("size") or 0)
            pnl_usd_live = -raw_live if direction == "short" else raw_live
        adverse = int(open_pos.get("adverse_bars") or 0)

        regime_live = classify_regime_v4(df_15m, df_1h, df_4h=df_4h, df_1d=df_1d)
        current_breakout_type = str(open_pos.get("breakout_type") or ("trend" if (regime_live.get("regime") == "trend") else "neutral"))

        # --- Trend health override: suppress premature exits when trend is objectively healthy ---
        _tr_cfg = (v4_cfg.get("trend_ride") or {}) if isinstance(v4_cfg.get("trend_ride"), dict) else {}
        trend_ride_enabled = bool(_tr_cfg.get("enabled", False))
        trend_healthy = False
        if trend_ride_enabled and str(open_pos.get("strategy_regime") or "") == "trend":
            trend_healthy = _trend_alignment_15m_1h(df_15m, df_1h, direction)
        self_score = confluence_score_v4(
            regime=str(regime_live.get("regime") or "neutral"),
            direction=direction,
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            df_4h=df_4h,
            levels=levels,
            fibs=fibs,
            breakout_type=current_breakout_type,
            entry_type=str(open_pos.get("entry_type") or "pullback"),
        )
        opp_dir = "short" if direction == "long" else "long"
        opp_breakout_type = classify_breakout(tf_df, opp_dir)
        opp_score = confluence_score_v4(
            regime=str(regime_live.get("regime") or "neutral"),
            direction=opp_dir,
            price=price,
            df_15m=df_15m,
            df_1h=df_1h,
            df_4h=df_4h,
            levels=levels,
            fibs=fibs,
            breakout_type=opp_breakout_type,
            entry_type="breakout_retest",
        )

        # Track peak unrealized profit so we can protect winners from full giveback.
        prev_peak = _to_float(open_pos.get("max_unrealized_usd"), 0.0) or 0.0
        curr_upnl = _to_float(pnl_usd_live, 0.0) or 0.0
        max_unrealized_usd = max(prev_peak, curr_upnl)
        giveback_usd = max(0.0, max_unrealized_usd - curr_upnl)
        open_pos["max_unrealized_usd"] = max_unrealized_usd
        # Track max pnl_pct for break-even stop
        prev_pnl_peak = float(open_pos.get("max_pnl_pct") or 0.0)
        open_pos["max_pnl_pct"] = max(prev_pnl_peak, pnl_pct)

        liq_price = _position_liquidation_price(open_pos, api, pos_product_id)
        liq_dist = _liquidation_distance(price, liq_price, direction)
        if liq_price is not None:
            open_pos["liquidation_price"] = liq_price
        if liq_dist is not None:
            open_pos["dist_to_liq"] = liq_dist

        # High cadence "holding" telemetry for dashboard and audit.
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "open_position_tick",
                "product_id": pos_product_id,
                "state": "open_position",
                "direction": direction,
                "entry_price": entry_price,
                "size": int(open_pos.get("size") or 0),
                "leverage": int(open_pos.get("leverage") or config.get("leverage", 4)),
                "contract_size": float(open_pos.get("contract_size") or config.get("contract_size", 5000)),
                "price": _pnl_price,
                "spot_price": price,
                "mark_price": _mark_price,
                "pnl_pct": pnl_pct,
                "pnl_usd_live": pnl_usd_live,
                "max_unrealized_usd": max_unrealized_usd,
                "giveback_usd": giveback_usd,
                "entry_time": open_pos.get("entry_time"),
                "time_in_trade_min": _minutes_between(open_pos.get("entry_time"), now.isoformat()),
                "bars_since_entry": bars_since,
                "regime": regime_live.get("regime"),
                "adx_15m": regime_live.get("adx_15m"),
                "atr_expanding": regime_live.get("atr_expanding"),
                "bb_expanding": regime_live.get("bb_expanding"),
                "atr_shock": regime_live.get("atr_shock"),
                "extreme_candle": regime_live.get("extreme_candle"),
                "score_self": self_score.get("score"),
                "score_opp": opp_score.get("score"),
                "liquidation_price": liq_price,
                "dist_to_liq": liq_dist,
                "active_mr": ((mp_decision.metrics or {}) if mp_decision else {}).get("active_mr"),
                "mr_intraday": ((mp_decision.metrics or {}) if mp_decision else {}).get("mr_intraday"),
                "mr_overnight": ((mp_decision.metrics or {}) if mp_decision else {}).get("mr_overnight"),
                "maintenance_margin_requirement": ((mp_decision.metrics or {}) if mp_decision else {}).get("maintenance_margin_requirement"),
                "total_funds_for_margin": ((mp_decision.metrics or {}) if mp_decision else {}).get("total_funds_for_margin"),
                "rescue_count": int(open_pos.get("plrl3_rescue_step") or 0),
                "scale_count": int(open_pos.get("scale_count") or 0),
                "strategy_regime": open_pos.get("strategy_regime"),
                "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
                "conversion_cost_today_usd": float(state.get("conversion_cost_today_usd") or 0.0),
                "contract_basis_bps": contract_ctx.get("basis_bps"),
                "contract_oi_trend": contract_ctx.get("oi_trend"),
                "contract_funding_bias": contract_ctx.get("funding_bias"),
                "contract_oi_price_rel": contract_ctx.get("oi_price_rel"),
                # Balance fields for dashboard during trades
                "spot_usdc": float((state.get("last_spot_cash_map") or {}).get("USDC") or 0),
                "spot_usd": float((state.get("last_spot_cash_map") or {}).get("USD") or 0),
                "derivatives_usdc": float(((mp_decision.metrics or {}) if mp_decision else {}).get("cfm_usd_balance") or 0),
                "cfm_usd_balance": float(((mp_decision.metrics or {}) if mp_decision else {}).get("cfm_usd_balance") or 0),
                "last_spot_cash_map": state.get("last_spot_cash_map") or {},
                "reconcile_status": state.get("_last_reconcile_status"),
                "safe_mode": bool(state.get("_safe_mode")),
                "equity_start_usd": float(state.get("equity_start_usd") or 0),
                "exchange_equity_usd": float(state.get("exchange_equity_usd") or 0),
                "exchange_pnl_today_usd": float(state.get("exchange_pnl_today_usd") or 0),
                "pnl_today_usd": float(state.get("pnl_today_usd") or 0),
            },
        )

        # AI advisor: fire exit evaluation (background, cached 2 min)
        _exit_payload = {
            "price": _pnl_price,
            "pnl_usd_live": pnl_usd_live,
            "pnl_pct": pnl_pct,
            "max_unrealized_usd": max_unrealized_usd,
            "giveback_usd": giveback_usd,
            "bars_since_entry": bars_since,
            "regime": regime_live.get("regime"),
            "score_self": self_score.get("score"),
            "score_opp": opp_score.get("score"),
        }
        ai_advisor.evaluate_exit(open_pos, _exit_payload, df_15m=df_15m, regime_v4=regime_live, expansion_state=expansion_state)
        gemini_advisor.evaluate_exit(open_pos, _exit_payload, df_15m=df_15m, regime_v4=regime_live, expansion_state=expansion_state)

        # Flip logic: if an MR trade faces opposite-direction trend confirmation on 15m+1h, exit.
        is_mr_trade = str(open_pos.get("strategy_regime") or "mean_reversion") == "mean_reversion"
        trend_flip = bool(
            is_mr_trade
            and str(regime_live.get("regime")) == "trend"
            and str(opp_score.get("regime")) == "trend"
            and bool(opp_score.get("pass"))
            and _trend_alignment_15m_1h(df_15m, df_1h, opp_dir)
        )

        # Generate Data Integrity Report (Codex)
        integrity_report = None
        reconcile_result = locals().get("rec")
        if reconcile_result:
             integrity_report = codex_advisor.generate_integrity_report(reconcile_result)
             if integrity_report.get("status") == "BLOCK_TRADING":
                 log_decision(config, {
                     "timestamp": now.isoformat(),
                     "reason": "integrity_block_trading",
                     "report": integrity_report
                 })
                 # Can optionally return here or just let gates catch it, but blocking is safer
                 # For now we log it and let it inform peer_intel

        # Near-cutoff de-risk if overnight MR is already unsafe.
        # SKIP entirely if overnight_trading_ok — account can safely hold overnight.
        cutoff_derisk = False
        friday_break_risk = _compute_friday_break_risk(config=config, now_utc=now)
        friday_break_derisk = bool(friday_break_risk.get("force_flat_now"))
        if not overnight_trading_ok and mp_decision and isinstance(mp_decision.metrics, dict):
            mins_to_cutoff = int(mp_decision.metrics.get("mins_to_cutoff") or 9999)
            mr_overnight = _to_float(mp_decision.metrics.get("mr_overnight"))
            guard = float((v4_cfg.get("kill_switches") or {}).get("overnight_derisk_mr", 0.90) or 0.90)
            pre_cut = int(mp_cfg.get("pre_cutoff_minutes", 15) or 15)
            margin_window = str(mp_decision.metrics.get("margin_window", ""))
            cutoff_derisk = bool(
                mr_overnight is not None
                and mins_to_cutoff <= pre_cut
                and mr_overnight >= guard
                and margin_window != "overnight"
            )

        # --- AGGRESSIVE MARGIN RESCUE SWEEP ---
        # When margin ratio is critical (>=0.75), sweep ALL available spot USDC
        # to derivatives wallet to prevent liquidation. This is safer than adding
        # position size - it just adds collateral.
        _aggressive_sweep_done = False
        if not paper and active_mr is not None and active_mr >= 0.75:
            _agg_sweep_key = "_last_aggressive_sweep_ts"
            _agg_sweep_cooldown = 120  # 2 min cooldown between aggressive sweeps
            _last_agg = float(state.get(_agg_sweep_key) or 0)
            _now_ts = now.timestamp()
            if (_now_ts - _last_agg) >= _agg_sweep_cooldown:
                try:
                    _spot_cash = api.get_spot_cash_map(["USDC", "USD"])
                    _avail_usdc = float(_spot_cash.get("USDC") or 0) + float(_spot_cash.get("USD") or 0)
                    _reserve = 2.0  # keep $2 in spot for settlement
                    _sweep_amt = _avail_usdc - _reserve
                    if _sweep_amt >= 5.0:  # only sweep if meaningful amount
                        funding_cfg = config.get("futures_funding", {})
                        funding_prefs = _funding_preferences(funding_cfg)
                        ok, info = api.ensure_futures_margin(
                            product_id=pos_product_id,
                            size=int(open_pos.get("size") or 0),
                            direction=direction,
                            buffer_pct=0.50,  # large buffer to pull max funds
                            reserve_usd=_sweep_amt,
                            auto_transfer=True,
                            currency="USDC",
                            preferred_currencies=funding_prefs,
                            conversion_cost_bps=0.0,
                            spot_reserve_floor_usd=_reserve,
                            max_transfer_usd=_sweep_amt,
                            transfer_used_usd=transfers_today,
                        )
                        state[_agg_sweep_key] = _now_ts
                        _aggressive_sweep_done = True
                        durable.log_event("aggressive_margin_sweep", {
                            "active_mr": round(active_mr, 4),
                            "sweep_amount": round(_sweep_amt, 2),
                            "available_spot": round(_avail_usdc, 2),
                            "ok": ok,
                        })
                        if ok:
                            slack_alert.send(
                                f":shield: MARGIN RESCUE: Swept ${_sweep_amt:.2f} spot to derivatives (MR={active_mr:.2%})",
                                level="warning",
                            )
                except Exception as _agg_err:
                    durable.log_event("aggressive_sweep_error", {"error": str(_agg_err)})

        # Legacy funding-rescue top-up, but only under mean-reversion + liquidation-distance condition.
        rescue_cfg = (config.get("futures_funding", {}) or {}).get("rescue", {}) or {}
        if not paper and rescue_cfg.get("enabled", True) and (str(regime_live.get("regime")) == "mean_reversion"):
            trigger = float(rescue_cfg.get("trigger_pct", 0.05) or 0.05)
            if liq_dist is not None and liq_dist <= trigger and not open_pos.get("rescue_done"):
                margin_info = api.estimate_required_margin(pos_product_id, int(open_pos.get("size") or 0), direction, price=price)
                req = float(margin_info.get("required_margin") or 0.0)
                reserve = req * float(rescue_cfg.get("reserve_multiple", 1.0))
                funding_cfg = config.get("futures_funding", {})
                funding_prefs = _funding_preferences(funding_cfg)
                ok, info = api.ensure_futures_margin(
                    product_id=pos_product_id,
                    size=int(open_pos.get("size") or 0),
                    direction=direction,
                    buffer_pct=float(funding_cfg.get("buffer_pct", 0.10)),
                    reserve_usd=reserve,
                    auto_transfer=bool(funding_cfg.get("auto_transfer", False)),
                    currency=str(funding_cfg.get("currency", "USDC")),
                    preferred_currencies=funding_prefs,
                    conversion_cost_bps=float(funding_cfg.get("conversion_cost_bps", 0.0) or 0.0),
                    spot_reserve_floor_usd=float(funding_cfg.get("spot_reserve_floor_usd", 0.0)),
                    max_transfer_usd=float(funding_cfg.get("max_transfer_per_day_usd", 0.0) or 0.0),
                    transfer_used_usd=transfers_today,
                )
                _record_funding_outcome(
                    config=config,
                    state=state,
                    durable=durable,
                    now=now,
                    context="rescue",
                    margin_ok=ok,
                    margin_info=info,
                )
                log_decision(
                    config,
                    {
                        "timestamp": now.isoformat(),
                        "reason": "rescue_margin",
                        "price": price,
                        "liquidation_price": liq_price,
                        "liq_dist_pct": liq_dist,
                        "reserve_usd": reserve,
                        "ok": ok,
                        "info": info,
                    },
                )
                open_pos["rescue_done"] = True

        # PLRL-3: only permit rescues in MR regime, under liq-distance trigger, and with volatility guard.
        plrl_cfg = (config.get("plrl3") or {}) if isinstance(config.get("plrl3"), dict) else {}
        if (not paper) and bool(plrl_cfg.get("enabled", False)) and pos_product_id:
            manual_override = (DATA_DIR / "MANUAL_OVERRIDE").exists()
            enforcement = str(plrl_cfg.get("enforcement", "log_only")).lower().strip()
            execute_live = (enforcement == "live") and (not manual_override)
            rescue_step = int(open_pos.get("plrl3_rescue_step") or 0)
            initial_contracts = int(open_pos.get("plrl3_initial_contracts") or open_pos.get("size") or 0)
            liq_trigger = float(plrl_cfg.get("liq_trigger_pct", 0.05) or 0.05)
            liq_guard_ok = bool(liq_dist is not None and liq_dist <= liq_trigger)
            regime_guard_ok = str(regime_live.get("regime")) == "mean_reversion"
            volatility_guard_ok = not bool(regime_live.get("atr_shock") or regime_live.get("extreme_candle"))
            consider_rescues = (not manual_override) and regime_guard_ok and liq_guard_ok and volatility_guard_ok

            bs = balance_summary if isinstance(balance_summary, dict) else (api.get_futures_balance_summary() or {})
            details = api.get_product_details(pos_product_id) or {}
            dec = evaluate_plrl3(
                balance_summary=bs,
                product_details=details,
                direction=direction,
                price=float(price),
                initial_contracts=initial_contracts,
                rescue_step=rescue_step,
                max_rescues=int(plrl_cfg.get("max_rescues", 3) or 3),
                mr_triggers=list(plrl_cfg.get("mr_triggers", [0.60, 0.75, 0.88]) or []),
                add_multipliers=list(plrl_cfg.get("add_multipliers", [2, 4, 8]) or []),
                fail_mr=float(plrl_cfg.get("fail_mr", 0.95) or 0.95),
                max_projected_mr=float(plrl_cfg.get("max_projected_mr", 0.95) or 0.95),
                overnight_guard_mr=float(plrl_cfg.get("overnight_guard_mr", 0.90) or 0.90),
                now_utc=now,
                disable_rescues_pre_cutoff_min=int(plrl_cfg.get("disable_rescues_pre_cutoff_min", 30) or 30),
                allow_rescues=consider_rescues,
            )
            log_plrl3(
                {
                    "timestamp": now.isoformat(),
                    "strategy": dec.strategy,
                    "product_id": pos_product_id,
                    "direction": direction,
                    "position_contracts": int(open_pos.get("size") or 0),
                    "avg_entry": entry_price,
                    "price": float(price),
                    "rescue_step": dec.rescue_step,
                    "max_rescues": dec.max_rescues,
                    "mr_intraday": dec.mr_intraday,
                    "mr_overnight": dec.mr_overnight,
                    "active_mr": dec.active_mr,
                    "active_window": dec.active_window,
                    "next_rescue_at": dec.next_rescue_at,
                    "fail_at": dec.fail_at,
                    "projected_mr_intraday": dec.projected_mr_intraday,
                    "projected_mr_overnight": dec.projected_mr_overnight,
                    "action": dec.action,
                    "add_contracts": dec.add_contracts,
                    "notes": dec.notes,
                    "manual_override": manual_override,
                    "enforcement": enforcement,
                    "liq_dist": liq_dist,
                    "liq_trigger_pct": liq_trigger,
                    "regime": regime_live.get("regime"),
                    "vol_guard_ok": volatility_guard_ok,
                }
            )

            if execute_live:
                if dec.action == "EXIT":
                    durable.log_event("plrl3_exit", {"product_id": pos_product_id, "mr": dec.active_mr, "notes": dec.notes})
                    entry_time_raw = open_pos.get("entry_time")
                    exit_time_iso = now.isoformat()
                    cancel_info = api.cancel_open_orders(product_id=pos_product_id)
                    close_info = api.close_cfm_position(pos_product_id, paper=False)
                    log_fill(
                        {
                            "timestamp": now.isoformat(),
                            "reason": "plrl3_exit",
                            "product_id": pos_product_id,
                            "cancel_info": cancel_info,
                            "close_info": close_info,
                        }
                    )
                    # Verify fill and recalculate PnL from exchange data
                    _plrl_oid = None
                    try:
                        _plrl_oid = ((close_info or {}).get("result") or {}).get("order_id")
                    except Exception:
                        pass
                    _plrl_fill = verify_fill(api, _plrl_oid) if _plrl_oid else None
                    _plrl_verified = bool(_plrl_fill and _plrl_fill.get("filled"))
                    _plrl_fill_price = float(_plrl_fill.get("average_filled_price") or 0) if _plrl_fill else 0
                    _plrl_fees = float(_plrl_fill.get("total_fees") or 0) if _plrl_fill else 0
                    _plrl_exit_price = _plrl_fill_price if _plrl_fill_price > 0 else price
                    # Force-flatten with retries
                    _plrl_flatten = _force_flatten_position(api, pos_product_id, max_rounds=3)
                    if _plrl_flatten.get("order_id") and not _plrl_oid:
                        _plrl_oid = _plrl_flatten["order_id"]
                        _plrl_fill = verify_fill(api, _plrl_oid) if _plrl_oid else None
                        _plrl_verified = bool(_plrl_fill and _plrl_fill.get("filled"))
                        _plrl_fill_price = float(_plrl_fill.get("average_filled_price") or 0) if _plrl_fill else 0
                        _plrl_fees = float(_plrl_fill.get("total_fees") or 0) if _plrl_fill else 0
                        _plrl_exit_price = _plrl_fill_price if _plrl_fill_price > 0 else price
                    if not _plrl_flatten["flat"]:
                        log_decision(config, {
                            "timestamp": now.isoformat(),
                            "reason": "GHOST_EXIT_PREVENTED",
                            "exit_reason": "plrl3_exit",
                            "product_id": pos_product_id,
                            "flatten_attempts": _plrl_flatten["attempts"],
                            "thought": f"PLRL3: {_plrl_flatten['attempts']} close attempts, still open.",
                        })
                        slack_alert.send(
                            f"PLRL3 GHOST EXIT — {_plrl_flatten['attempts']} close attempts failed.",
                            level="error",
                        )
                        save_state(state)
                        return
                    _plrl_size = int(open_pos.get("size") or 0)
                    # Recalculate from verified fill
                    if _plrl_fill_price > 0 and entry_price > 0:
                        if direction == "long":
                            pnl_pct = (_plrl_fill_price - entry_price) / entry_price
                        else:
                            pnl_pct = (entry_price - _plrl_fill_price) / entry_price
                        if contract_size > 0 and _plrl_size > 0:
                            pnl_usd_live = pnl_pct * entry_price * _plrl_size * contract_size
                    # Subtract fees
                    _entry_fees = float(open_pos.get("entry_fees_usd") or 0)
                    _total_plrl_fees = _entry_fees + _plrl_fees
                    if _total_plrl_fees <= 0:
                        _total_plrl_fees = float(open_pos.get("estimated_round_trip_fees") or 0)
                    if pnl_usd_live is not None and _total_plrl_fees > 0:
                        pnl_usd_live -= _total_plrl_fees
                    result = "win" if pnl_pct > 0 else "loss" if pnl_pct < 0 else "flat"
                    # Guard against double-counting
                    _last_counted_entry = str(state.get("_last_exit_counted_entry") or "")
                    _this_entry = str(entry_time_raw or "")
                    _already_counted = bool(_last_counted_entry and _this_entry and _last_counted_entry == _this_entry)
                    if not _already_counted:
                        state["_last_exit_counted_entry"] = _this_entry
                        if result == "loss":
                            state["losses"] = int(state.get("losses") or 0) + 1
                            state["consecutive_losses"] = int(state.get("consecutive_losses") or 0) + 1
                            state["consecutive_wins"] = 0
                            if pnl_usd_live is not None:
                                state["loss_debt_usd"] = float(state.get("loss_debt_usd") or 0.0) + abs(float(pnl_usd_live))
                        elif result == "win":
                            state["consecutive_losses"] = 0
                            state["consecutive_wins"] = int(state.get("consecutive_wins") or 0) + 1
                            if pnl_usd_live is not None and pnl_usd_live > 0:
                                state["loss_debt_usd"] = max(0.0, float(state.get("loss_debt_usd") or 0.0) - float(pnl_usd_live))
                        if pnl_usd_live is not None:
                            state["pnl_today_usd"] = float(state.get("pnl_today_usd") or 0.0) + float(pnl_usd_live)
                        # Exchange equity snapshot
                        try:
                            _post_exit_eq = float(api.get_futures_equity() or 0)
                            if _post_exit_eq > 0:
                                state["exchange_equity_usd"] = _post_exit_eq
                                _eq_start = float(state.get("equity_start_usd") or 0)
                                _transfers = float(state.get("transfers_today_usd") or 0)
                                if _eq_start > 0:
                                    state["exchange_pnl_today_usd"] = _post_exit_eq - _eq_start + _transfers
                        except Exception:
                            pass
                    log_trade(
                        config,
                        _with_lifecycle_fields(
                            {
                                "timestamp": now.isoformat(),
                                "product_id": pos_product_id,
                                "side": direction,
                                "size": _plrl_size,
                                "entry_price": entry_price,
                                "exit_price": _plrl_exit_price,
                                "pnl_pct": pnl_pct,
                                "pnl_usd": pnl_usd_live,
                                "result": result,
                                "exit_reason": "plrl3_exit",
                                "exit_order_id": _plrl_oid,
                                "fill_verified": _plrl_verified,
                                "entry_fees_usd": _entry_fees,
                                "exit_fees_usd": _plrl_fees,
                                "total_fees_usd": _total_plrl_fees,
                            },
                            entry_time=entry_time_raw,
                            exit_time=exit_time_iso,
                        ),
                    )
                    _plrl_held = (now - datetime.fromisoformat(str(open_pos.get("entry_time") or now.isoformat()))).total_seconds() / 60.0 if open_pos.get("entry_time") else 0
                    _plrl_exp = ((open_pos.get("exit_watch") or {}).get("close_eta") or {}).get("expected_hold_min")
                    slack_alert.trade_exit(
                        direction=direction, exit_reason="plrl3_exit",
                        entry_price=entry_price, exit_price=_plrl_exit_price,
                        pnl_usd=pnl_usd_live, pnl_pct=pnl_pct, fill_verified=_plrl_verified,
                        held_min=_plrl_held, expected_hold_min=_plrl_exp,
                        size=int(open_pos.get("size") or 1),
                    )
                    state["last_exit_time"] = exit_time_iso
                    state["open_position"] = None
                    save_state(state)
                    durable.set_kv("open_position", None)
                    return
                if dec.action == "RESCUE" and dec.add_contracts > 0:
                    stop_px = open_pos.get("stop_loss")
                    side = "BUY" if direction == "long" else "SELL"
                    om = OrderManager(api, paper=False)
                    res = om.place_entry(OrderRequest(product_id=pos_product_id, side=side, size=int(dec.add_contracts), leverage=leverage, stop_loss=stop_px))
                    log_fill(
                        {
                            "timestamp": now.isoformat(),
                            "reason": "plrl3_rescue",
                            "product_id": pos_product_id,
                            "step": rescue_step,
                            "add_contracts": int(dec.add_contracts),
                            "order_id": res.order_id,
                            "ok": bool(res.success),
                        }
                    )
                    durable.log_event(
                        "plrl3_rescue",
                        {"product_id": pos_product_id, "step": rescue_step, "add": int(dec.add_contracts), "order_id": res.order_id, "ok": bool(res.success)},
                    )
                    log_decision(
                        config,
                        {
                            "timestamp": now.isoformat(),
                            "reason": "plrl3_rescue",
                            "product_id": pos_product_id,
                            "step": rescue_step,
                            "add_contracts": int(dec.add_contracts),
                            "mr_intraday": dec.mr_intraday,
                            "mr_overnight": dec.mr_overnight,
                            "active_mr": dec.active_mr,
                            "notes": dec.notes,
                            "order_id": res.order_id,
                            "ok": bool(res.success),
                        },
                    )
                    if res.success:
                        # Verify fill before updating size to prevent phantom contract inflation
                        _rescue_fill = verify_fill(api, res.order_id) if res.order_id else None
                        _rescue_fill_ok = bool(_rescue_fill and _rescue_fill.get("filled"))
                        if _rescue_fill_ok:
                            open_pos["size"] = int(open_pos.get("size") or 0) + int(dec.add_contracts)
                            open_pos["plrl3_rescue_step"] = rescue_step + 1
                            open_pos["plrl3_initial_contracts"] = initial_contracts
                            state["open_position"] = open_pos
                            save_state(state)
                            durable.set_kv("open_position", open_pos)
                        else:
                            log_decision(config, {
                                "timestamp": now.isoformat(),
                                "reason": "plrl3_rescue_fill_unverified",
                                "order_id": res.order_id,
                                "thought": "rescue order sent but fill unverified; size NOT updated",
                            })
                        return

        # Safe scaling into winners (trend-only, profitable, retest hold, MR guard).
        scale_cfg = (v4_cfg.get("scaling") or {}) if isinstance(v4_cfg.get("scaling"), dict) else {}
        if (not paper) and bool(scale_cfg.get("enabled", True)):
            if str(open_pos.get("strategy_regime") or "mean_reversion") == "trend" and str(regime_live.get("regime")) == "trend":
                atr_now = _to_float(self_score.get("atr_15m"), 0.0) or 0.0
                profit_atr = abs(pnl_pct * entry_price) / atr_now if atr_now > 0 else 0.0
                scale_count = int(open_pos.get("scale_count") or 0)
                max_adds = int(scale_cfg.get("max_adds", 2) or 2)
                last_scale_ts = str(open_pos.get("last_scale_ts") or "")
                min_gap = int(scale_cfg.get("min_minutes_between_adds", 30) or 30)
                gap_ok = True
                if last_scale_ts:
                    try:
                        gap_ok = (now - datetime.fromisoformat(last_scale_ts)).total_seconds() >= (min_gap * 60)
                    except Exception:
                        gap_ok = True

                if scale_count < max_adds and gap_ok and profit_atr >= float(scale_cfg.get("profit_trigger_atr", 0.75) or 0.75) and _retest_hold(df_15m, direction):
                    base_size = int(open_pos.get("base_size") or open_pos.get("plrl3_initial_contracts") or open_pos.get("size") or 1)
                    add_pct = float(scale_cfg.get("add_size_pct", 0.25) or 0.25)
                    add_size = max(1, int(round(base_size * add_pct)))
                    active_mr = float(((mp_decision.metrics or {}) if mp_decision else {}).get("active_mr") or 0.0)
                    total_funds = _to_float(((mp_decision.metrics or {}) if mp_decision else {}).get("total_funds_for_margin"), 0.0) or 0.0
                    add_margin = api.estimate_required_margin(pos_product_id, add_size, direction, price=price) if pos_product_id else {}
                    add_req = float((add_margin or {}).get("required_margin") or 0.0)
                    projected_mr_upper = active_mr + ((add_req / total_funds) if total_funds > 0 and add_req > 0 else 0.0)
                    prefer_mr = float(scale_cfg.get("projected_mr_prefer_lt", 0.90) or 0.90)
                    hard_mr = float(scale_cfg.get("projected_mr_hard_lt", 0.95) or 0.95)
                    if projected_mr_upper < hard_mr:
                        side = "BUY" if direction == "long" else "SELL"
                        om = OrderManager(api, paper=False)
                        res = om.place_entry(
                            OrderRequest(
                                product_id=pos_product_id,
                                side=side,
                                size=int(add_size),
                                leverage=leverage,
                                stop_loss=open_pos.get("stop_loss"),
                            )
                        )
                        log_fill(
                            {
                                "timestamp": now.isoformat(),
                                "reason": "trend_scale_in",
                                "product_id": pos_product_id,
                                "order_id": res.order_id,
                                "add_size": int(add_size),
                                "projected_mr_upper": projected_mr_upper,
                                "prefer_mr": prefer_mr,
                                "hard_mr": hard_mr,
                                "ok": bool(res.success),
                            }
                        )
                        log_decision(
                            config,
                            {
                                "timestamp": now.isoformat(),
                                "reason": "trend_scale_in",
                                "product_id": pos_product_id,
                                "add_size": int(add_size),
                                "projected_mr_upper": projected_mr_upper,
                                "prefer_mr": prefer_mr,
                                "order_id": res.order_id,
                                "ok": bool(res.success),
                            },
                        )
                        if res.success:
                            # Verify fill before updating size to prevent phantom contract inflation
                            _scale_fill = verify_fill(api, res.order_id) if res.order_id else None
                            _scale_fill_ok = bool(_scale_fill and _scale_fill.get("filled"))
                            if _scale_fill_ok:
                                open_pos["size"] = int(open_pos.get("size") or 0) + int(add_size)
                                open_pos["scale_count"] = scale_count + 1
                                open_pos["last_scale_ts"] = now.isoformat()
                                state["open_position"] = open_pos
                                save_state(state)
                                durable.set_kv("open_position", open_pos)
                            else:
                                log_decision(config, {
                                    "timestamp": now.isoformat(),
                                    "reason": "scale_in_fill_unverified",
                                    "order_id": res.order_id,
                                    "thought": "scale-in order sent but fill unverified; size NOT updated",
                                })
                            return

        if pnl_pct <= -config["exits"]["early_save_adverse_pct"]:
            adverse += 1
        elif pnl_pct > -0.005:
            adverse = 0

        exit_cfg = (v4_cfg.get("exit") or {}) if isinstance(v4_cfg.get("exit"), dict) else {}
        profit_lock_cfg = (v4_cfg.get("profit_lock") or {}) if isinstance(v4_cfg.get("profit_lock"), dict) else {}

        # Quality-tier exit overrides (early init for time stop)
        pos_quality_tier = str(open_pos.get("quality_tier") or "FULL").upper()
        qt_exit_overrides: dict = {}
        if pos_quality_tier in ("REDUCED", "SCALP"):
            _qt_cfg_for_exit = (v4_cfg.get("quality_tiers") or {}) if isinstance(v4_cfg.get("quality_tiers"), dict) else {}
            qt_exit_overrides = (_qt_cfg_for_exit.get(pos_quality_tier.lower()) or {}) if isinstance(_qt_cfg_for_exit.get(pos_quality_tier.lower()), dict) else {}

        # Regime-aware time stop: use regime overrides stored at entry, quality tier overrides still win
        _regime_ts_bars = int(open_pos.get("regime_time_stop_bars") or config["exits"]["time_stop_bars"])
        _ts_bars = int(qt_exit_overrides.get("time_stop_bars") or _regime_ts_bars)
        if trend_healthy:
            _ts_bars = int(_tr_cfg.get("time_stop_bars_trend", 12) or 12)
        _ts_min_move = float(qt_exit_overrides.get("time_stop_min_move_pct") or config["exits"]["time_stop_min_move_pct"])

        # Entry-type-specific time_stop override (Mar 21 fix)
        # Reversal entries need more time to develop -- don't time-stop them early
        _pos_entry_type = str(open_pos.get("entry_type") or "")
        _et_ts_cfg = (config.get("exits") or {}).get("entry_type_time_stop") or {}
        _et_override = _et_ts_cfg.get(_pos_entry_type) or {}
        if _et_override:
            _et_ts_bars = int(_et_override.get("time_stop_bars") or _ts_bars)
            _et_ts_min = float(_et_override.get("time_stop_min_move_pct") or _ts_min_move)
            # Entry-type override wins over default, but quality tier still wins over entry-type
            if not qt_exit_overrides.get("time_stop_bars"):
                _ts_bars = max(_ts_bars, _et_ts_bars)  # always use the MORE patient value
            if not qt_exit_overrides.get("time_stop_min_move_pct"):
                _ts_min_move = min(_ts_min_move, _et_ts_min)  # always use the LOOSER threshold

        time_stop = bars_since >= _ts_bars and pnl_pct < _ts_min_move
        tp_plan = tp_prices(
            entry_price,
            leverage,
            direction,
            config["exits"]["tp1_move"],
            config["exits"]["tp2_move"],
            config["exits"]["tp3_move"],
            full_close_at_tp1=config["exits"]["tp_full_close_if_single_contract"],
        )
        tp_hit = price >= tp_plan.tp1 if direction == "long" else price <= tp_plan.tp1
        dynamic_tp_price = None
        if bool(exit_cfg.get("dynamic_tp_enabled", True)):
            atr_now = _to_float(self_score.get("atr_15m"), 0.0) or 0.0
            if atr_now > 0:
                # Regime-aware TP: use regime override stored at entry if set
                _regime_tp = float(open_pos.get("regime_tp_atr_mult") or 0)
                if _regime_tp > 0:
                    tp_mult = _regime_tp
                else:
                    tp_mult = float(
                        exit_cfg.get(
                            "trend_tp_atr",
                            1.4 if str(open_pos.get("strategy_regime") or "mean_reversion") == "trend" else 1.0,
                        )
                        if str(open_pos.get("strategy_regime") or "mean_reversion") == "trend"
                        else exit_cfg.get("mr_tp_atr", 1.0)
                    )
                dynamic_tp_price = (entry_price + tp_mult * atr_now) if direction == "long" else (entry_price - tp_mult * atr_now)
                # Compression range: target mid-range instead of ATR
                cr_target = _to_float(open_pos.get("compression_range_target"), 0.0)
                if str(open_pos.get("entry_type") or "") == "compression_range" and cr_target > 0:
                    dynamic_tp_price = cr_target
                # Fib retrace: target the fib level instead of ATR
                elif str(open_pos.get("entry_type") or "") == "fib_retrace":
                    _fib_tp = _to_float(open_pos.get("fib_tp_price"), 0.0)
                    if _fib_tp > 0:
                        dynamic_tp_price = _fib_tp
                # SCALP tier: force min_tp_pct as TP target
                elif pos_quality_tier == "SCALP" and bool(qt_exit_overrides.get("use_min_tp", False)):
                    scalp_tp_dist = price * float(exit_cfg.get("min_tp_pct", 0.003) or 0.003)
                    dynamic_tp_price = entry_price + scalp_tp_dist if direction == "long" else entry_price - scalp_tp_dist
                # Enforce minimum TP distance floor
                min_tp_pct = float(exit_cfg.get("min_tp_pct", 0.003) or 0.003)
                min_tp_dist = price * min_tp_pct
                if abs(dynamic_tp_price - entry_price) < min_tp_dist:
                    dynamic_tp_price = entry_price + min_tp_dist if direction == "long" else entry_price - min_tp_dist
                if direction == "long":
                    tp_hit = bool(tp_hit or price >= dynamic_tp_price)
                else:
                    tp_hit = bool(tp_hit or price <= dynamic_tp_price)
        breakout_type = str(open_pos.get("breakout_type", "neutral"))
        reversal = False
        opp_conf = {}
        # Always compute reversal (needed for runner mode even with single-contract)
        try:
            opp_conf = compute_confluences(price, df_1h, df_4h, df_15m, levels, fibs, opp_dir)
            reversal = confluence_passes(opp_conf)
            rev_min_bars = int(exit_cfg.get("reversal_min_bars", 2) or 2)
            rev_requires_nonpos = bool(exit_cfg.get("reversal_requires_nonpositive_pnl", True))
            rev_min_hold_min = float(exit_cfg.get("reversal_min_hold_minutes", 0) or 0)
            if bars_since < rev_min_bars:
                reversal = False
            if rev_requires_nonpos and pnl_pct > 0:
                reversal = False
            # Hold-time guard: don't exit on reversal signal if trade hasn't been held long enough
            if rev_min_hold_min > 0 and _hold_secs < rev_min_hold_min * 60:
                reversal = False
        except Exception:
            reversal = False

        # Profit-lock: tier+regime-aware — SCALP locks fast, MONSTER lets winners run.
        profit_lock_hit = False
        lock_floor_usd = None
        lock_armed = False
        _pl_tier = str(open_pos.get("quality_tier") or "FULL").upper()
        _pl_regime = str(open_pos.get("regime_name") or "transition").lower()
        if bool(profit_lock_cfg.get("enabled", True)):
            _pl = _resolve_profit_lock_params(profit_lock_cfg, _pl_tier, _pl_regime)
            activate_usd = _pl["activate_usd"]
            keep_ratio = _pl["keep_ratio"]
            max_giveback = _pl["max_giveback_usd"]
            min_bars_lock = int(profit_lock_cfg.get("min_bars_since_entry", 1) or 1)
            lock_min_usd = float(profit_lock_cfg.get("lock_min_usd", 0.25) or 0.25)
            lock_armed = bool(max_unrealized_usd >= activate_usd and bars_since >= min_bars_lock)
            if lock_armed:
                lock_floor_usd = max(lock_min_usd, max_unrealized_usd * keep_ratio)
                if curr_upnl <= lock_floor_usd:
                    profit_lock_hit = True
                if giveback_usd >= max_giveback:
                    profit_lock_hit = True

        recovery_target = float(open_pos.get("recovery_target_usd") or 0.0)
        recovery_hit = bool(recovery_target > 0 and pnl_usd_live is not None and pnl_usd_live >= recovery_target)

        # --- Profit Protection Lanes ---
        _pp_cfg = (v4_cfg.get("profit_protection") or {}) if isinstance(v4_cfg.get("profit_protection"), dict) else {}

        # Entry profile overrides (frozen at entry time, stored in open_position)
        _ep_min_profit = float(open_pos.get("entry_profile_min_profit_usd") or 0)
        _ep_decay_pct = float(open_pos.get("entry_profile_decay_pct") or 0)

        # Lane 1: Hard minimum profit floor — once up $X, NEVER give it all back.
        # Uses entry profile min if available, otherwise global config.
        # In COMPRESSION: lower floor for rapid scalp profits.
        _min_floor_hit = False
        _min_floor_cfg = (_pp_cfg.get("min_floor") or {}) if isinstance(_pp_cfg.get("min_floor"), dict) else {}
        if bool(_min_floor_cfg.get("enabled", True)):
            _mf_usd = _ep_min_profit if _ep_min_profit > 0 else float(_min_floor_cfg.get("floor_usd", 3.0) or 3.0)
            _mf_bars = int(_min_floor_cfg.get("min_bars", 2) or 2)
            # Compression scalp: lower floor + faster arm for quick profit capture
            # (exempt trend entries — they need wider leash from entry_profiles)
            _vol_phase = state.get("vol_state", "COMPRESSION")
            if _vol_phase == "COMPRESSION":
                _cs_cfg = (_pp_cfg.get("compression_scalp") or {}) if isinstance(_pp_cfg.get("compression_scalp"), dict) else {}
                _cs_exempt = list(_cs_cfg.get("exempt_regimes") or [])
                _entry_regime = str(open_pos.get("strategy_regime") or "")
                if _entry_regime not in _cs_exempt:
                    _cs_floor = float(_cs_cfg.get("min_floor_usd", 1.0) or 1.0)
                    _mf_usd = min(_mf_usd, _cs_floor)
                    _mf_bars = min(_mf_bars, int(_cs_cfg.get("min_bars", 1) or 1))
            _mf_trail_pct = float(_min_floor_cfg.get("trail_pct", 0.40) or 0.40)
            _mf_armed = bool(max_unrealized_usd >= _mf_usd and bars_since >= _mf_bars)
            if _mf_armed:
                # Trailing floor: keep trail_pct of peak unrealized, not a hard dollar line
                _mf_trail_floor = max_unrealized_usd * _mf_trail_pct
                if curr_upnl < _mf_trail_floor:
                    _min_floor_hit = True

        # Lane 2: Momentum-confirmed decay exit — profit retraced significantly AND momentum dying.
        # Uses entry profile decay_pct if available, otherwise strategy override or global config.
        _decay_exit_hit = False
        _decay_cfg = (_pp_cfg.get("decay_exit") or {}) if isinstance(_pp_cfg.get("decay_exit"), dict) else {}
        if bool(_decay_cfg.get("enabled", True)):
            _de_arm = float(_decay_cfg.get("arm_usd", 5.0) or 5.0)
            # Compression scalp: lower arm threshold so decay works on small moves
            # (exempt trend entries — they need wider leash)
            if state.get("vol_state") == "COMPRESSION":
                _cs_cfg2 = (_pp_cfg.get("compression_scalp") or {}) if isinstance(_pp_cfg.get("compression_scalp"), dict) else {}
                _cs_exempt2 = list(_cs_cfg2.get("exempt_regimes") or [])
                if str(open_pos.get("strategy_regime") or "") not in _cs_exempt2:
                    _de_arm = min(_de_arm, float(_cs_cfg2.get("decay_arm_usd", 1.50) or 1.50))
            _strat_regime = str(open_pos.get("strategy_regime") or "mean_reversion")
            _so = (_decay_cfg.get("strategy_overrides") or {}).get(_strat_regime) or {}
            # Priority: entry profile > strategy override > global config
            _de_pct = _ep_decay_pct if _ep_decay_pct > 0 else float(_so.get("decay_pct") or _decay_cfg.get("decay_pct", 0.45) or 0.45)
            _de_require_momentum = bool(_decay_cfg.get("require_momentum", True))
            if max_unrealized_usd >= _de_arm and max_unrealized_usd > 0 and curr_upnl > 0:
                _retrace_pct = giveback_usd / max_unrealized_usd
                if _retrace_pct >= _de_pct:
                    # Check momentum weakness (optional)
                    _momentum_weak = True  # default if check disabled
                    if _de_require_momentum:
                        _momentum_weak = False
                        try:
                            from indicators.rsi import rsi as _rsi_fn
                            from indicators.macd import macd as _macd_fn
                            _rsi_vals = _rsi_fn(df_15m["close"], 14)
                            _macd_data = _macd_fn(df_15m["close"])
                            _macd_h = _macd_data["hist"]
                            if len(_rsi_vals) >= 3 and len(_macd_h) >= 3:
                                _rsi_now = float(_rsi_vals.iloc[-1])
                                _rsi_prev = float(_rsi_vals.iloc[-3])
                                _macd_h_now = float(_macd_h.iloc[-1])
                                _macd_h_prev = float(_macd_h.iloc[-3])
                                if direction == "long":
                                    # Weakness for long: RSI falling OR MACD hist declining
                                    _momentum_weak = (_rsi_now < _rsi_prev - 3) or (_macd_h_now < _macd_h_prev)
                                else:
                                    # Weakness for short: RSI rising OR MACD hist rising
                                    _momentum_weak = (_rsi_now > _rsi_prev + 3) or (_macd_h_now > _macd_h_prev)
                        except Exception:
                            _momentum_weak = True  # fail-safe: exit if can't compute
                    if _momentum_weak:
                        _decay_exit_hit = True

        # AI advisor: tighten decay when AI says exit_now
        _ai_exit = ai_advisor.get_cached_insight("exit_eval")
        if _ai_exit and _ai_exit.get("urgency") == "exit_now" and bool((config.get("ai") or {}).get("exit_tighten_on_exit_now", True)):
            if max_unrealized_usd > 0 and curr_upnl > 0 and not _decay_exit_hit:
                _retrace_pct_ai = giveback_usd / max_unrealized_usd if max_unrealized_usd > 0 else 0
                # Lower decay threshold by 30% when AI says exit_now
                try:
                    _de_pct_tight = _de_pct * 0.7
                except NameError:
                    _de_pct_tight = 0.30
                if _retrace_pct_ai >= _de_pct_tight:
                    _decay_exit_hit = True

        # Trade state label for dashboard visibility
        moonshot_state = None  # initialized here; evaluated after trade state labels
        if bars_since <= 1 and curr_upnl < 1.0:
            _trade_state = "EARLY"
        elif curr_upnl > 0 and not (lock_armed or _mf_armed if bool(_min_floor_cfg.get("enabled", True)) else lock_armed):
            _trade_state = "BUILDING"
        elif lock_armed or (_mf_armed if bool(_min_floor_cfg.get("enabled", True)) else False):
            if moonshot_state and moonshot_state.active:
                _trade_state = "EXPANSION"
            elif giveback_usd > 0 and max_unrealized_usd > 0 and (giveback_usd / max_unrealized_usd) > 0.15:
                _trade_state = "DECAY"
            else:
                _trade_state = "SECURED"
        elif curr_upnl < 0:
            _trade_state = "UNDERWATER"
        else:
            _trade_state = "BUILDING"

        # --- Moonshot evaluation ---
        moonshot_state = None
        ms_cfg = (v4_cfg.get("moonshot") or {}) if isinstance(v4_cfg.get("moonshot"), dict) else {}
        try:
            atr_exit = _to_float(self_score.get("atr_15m"), 0.0) or 0.0
            prev_ms = None
            if open_pos.get("moonshot_state"):
                try:
                    prev_ms = MoonshotState(**open_pos["moonshot_state"])
                except Exception:
                    prev_ms = None
            moonshot_state = evaluate_moonshot(
                direction=direction,
                price=price,
                entry_price=entry_price,
                pnl_pct=pnl_pct,
                contract_ctx=contract_ctx,
                atr_value=atr_exit,
                regime=str(open_pos.get("strategy_regime") or "mean_reversion"),
                bars_since_entry=bars_since,
                current_moonshot=prev_ms,
                config=ms_cfg,
                df_15m=df_15m,
                df_1h=df_1h,
            )
            open_pos["moonshot_state"] = moonshot_as_dict(moonshot_state)
        except Exception:
            moonshot_state = None

        # --- Runner mode: trailing stop for trend rides past TP1 ---
        _runner_cfg = (v4_cfg.get("runner_mode") or {}) if isinstance(v4_cfg.get("runner_mode"), dict) else {}
        _runner_active = False
        _runner_state = open_pos.get("runner_state") or {}
        if _runner_state.get("active") and bool(_runner_cfg.get("enabled", False)):
            _runner_active = True
            # Update peak price
            if direction == "short":
                _runner_state["peak_price"] = min(price, float(_runner_state.get("peak_price") or price))
            else:
                _runner_state["peak_price"] = max(price, float(_runner_state.get("peak_price") or price))
            # Trail distance (fib-aware tightening)
            _r_trail_mult = float(_runner_cfg.get("trail_atr_mult", 1.5) or 1.5)
            if _runner_state.get("fib_tightened"):
                _r_trail_mult *= float(_runner_cfg.get("fib_tighten_mult", 0.6) or 0.6)
            _r_trail_dist = (atr_exit if atr_exit > 0 else 0.001) * _r_trail_mult
            # Update trail price
            _r_peak = float(_runner_state["peak_price"])
            if direction == "short":
                _runner_state["trail_price"] = _r_peak + _r_trail_dist
            else:
                _runner_state["trail_price"] = _r_peak - _r_trail_dist
            # Check fib 786 crossing
            _fib_786 = float(_runner_state.get("fib_786") or 0)
            if _fib_786 > 0 and not _runner_state.get("fib_tightened"):
                if (direction == "short" and price <= _fib_786) or (direction == "long" and price >= _fib_786):
                    _runner_state["fib_tightened"] = True
            # Check 2-bar reversal (consecutive closes against direction)
            _rev_bars_needed = int(_runner_cfg.get("reversal_bars", 2) or 2)
            try:
                if df_15m is not None and len(df_15m) >= 3:
                    _c1 = float(df_15m["close"].iloc[-1])
                    _c2 = float(df_15m["close"].iloc[-2])
                    _c3 = float(df_15m["close"].iloc[-3])
                    if direction == "short" and _c1 > _c2 and _c2 > _c3:
                        _runner_state["consec_against"] = int(_runner_state.get("consec_against") or 0) + 1
                    elif direction == "long" and _c1 < _c2 and _c2 < _c3:
                        _runner_state["consec_against"] = int(_runner_state.get("consec_against") or 0) + 1
                    else:
                        _runner_state["consec_against"] = 0
            except Exception:
                pass
            _runner_state["bars_active"] = int(_runner_state.get("bars_active") or 0) + 1
            open_pos["runner_state"] = _runner_state

        # (qt_exit_overrides already initialized above for time stop)

        # Break-even check: compute before exit chain
        # Use mark price (_pnl_price) to avoid false triggers from spot/mark basis divergence.
        break_even_hit = False
        be_price = None
        _be_check_price = _pnl_price if _pnl_price and _pnl_price > 0 else price
        if atr_exit > 0 and _be_check_price > 0 and entry_price > 0:
            be_cfg = config.get("exits", {})
            be_atr_trigger = float(qt_exit_overrides.get("breakeven_atr_trigger") or be_cfg.get("breakeven_atr_trigger", 1.0) or 1.0)
            be_buffer_pct = float(be_cfg.get("breakeven_buffer_pct", 0.001) or 0.001)
            # Has price ever moved far enough to arm the break-even?
            if pnl_pct >= (atr_exit / _be_check_price) * be_atr_trigger:
                pass  # Currently in favorable territory — don't exit yet
            # Check if max unrealized profit was >= trigger but price has now reversed to entry
            be_threshold_pct = (atr_exit / _be_check_price) * be_atr_trigger
            max_pnl_pct = float(open_pos.get("max_pnl_pct") or pnl_pct)
            if max_pnl_pct >= be_threshold_pct:
                be_price = entry_price * (1 + be_buffer_pct) if direction == "long" else entry_price * (1 - be_buffer_pct)
                if (direction == "long" and _be_check_price < be_price) or (direction == "short" and _be_check_price > be_price):
                    break_even_hit = True

        exit_reason = None

        # === MIRROR DRAWDOWN STRATEGY ===
        # NO hard loss stop. Hold through drawdown, wait for the flip.
        # Only exit on profit (mirror target) or margin/cutoff emergencies.
        _mirror_pnl = float(pnl_usd_live) if pnl_usd_live is not None else 0.0

        # Track max drawdown during this trade for mirror target
        _max_dd_key = "_mirror_max_drawdown"
        _prev_max_dd = float(open_pos.get(_max_dd_key) or 0.0)
        if _mirror_pnl < 0 and abs(_mirror_pnl) > _prev_max_dd:
            open_pos[_max_dd_key] = abs(_mirror_pnl)
            _prev_max_dd = abs(_mirror_pnl)

        # Mirror profit target: if we were down $X, exit when up $X
        # BUT ONLY IF the chart says the move is exhausting.
        # If trend/momentum still supports, HOLD and let it run.
        _mirror_target_hit = _prev_max_dd > 0.50 and _mirror_pnl >= _prev_max_dd
        _chart_says_hold = False
        if _mirror_target_hit:
            # Check if chart structure supports staying in
            _exit_trend_healthy = bool(trend_healthy)
            _exit_momentum_ok = False
            try:
                _exit_rsi = float(df_15m["close"].pct_change().rolling(14).apply(
                    lambda x: 100 - 100 / (1 + x[x > 0].sum() / max(abs(x[x < 0].sum()), 1e-9))
                ).iloc[-1])
                if direction == "long":
                    _exit_momentum_ok = _exit_rsi > 45  # RSI above 45 = momentum still up
                else:
                    _exit_momentum_ok = _exit_rsi < 55  # RSI below 55 = momentum still down
            except Exception:
                _exit_momentum_ok = False
            # Check if price is above/below key EMA (trend still intact)
            try:
                _ema21 = float(df_15m["close"].ewm(span=21).mean().iloc[-1])
                if direction == "long":
                    _chart_says_hold = price > _ema21 and _exit_momentum_ok
                else:
                    _chart_says_hold = price < _ema21 and _exit_momentum_ok
            except Exception:
                pass
            # Also hold if trend is healthy regardless
            if _exit_trend_healthy:
                _chart_says_hold = True

        if not exit_reason and _mirror_target_hit and not _chart_says_hold:
            exit_reason = "mirror_profit_target"
            durable.log_event("mirror_profit_target", {
                "pnl_usd": round(_mirror_pnl, 4),
                "max_drawdown_usd": round(_prev_max_dd, 4),
                "chart_hold_override": False,
            })
        elif _mirror_target_hit and _chart_says_hold:
            # Mirror target hit but chart says keep riding -- log it and hold
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "mirror_target_hold_override",
                "pnl_usd": round(_mirror_pnl, 4),
                "max_drawdown_usd": round(_prev_max_dd, 4),
                "trend_healthy": _exit_trend_healthy,
                "thought": f"Mirror target ${_prev_max_dd:.2f} hit with ${_mirror_pnl:.2f} profit, but chart says hold. Riding the trend.",
            })

        # Hard wall: max_hold_hours exceeded
        if not exit_reason and _max_hold_triggered:
            exit_reason = "max_hold_time"
        # SMART STRUCTURAL EXIT -- exits based on chart conditions, not arbitrary percentages.
        # A dip to support that bounces is NOT an exit. A dip THROUGH support with volume IS.
        _sl_price = 0
        try:
            from strategy.smart_exit import should_exit as smart_should_exit
            _smart_exit = smart_should_exit(
                price=price,
                direction=direction,
                entry_price=entry_price,
                df_15m=df_15m,
                df_1h=df_1h,
                pnl_usd=pnl_usd,
                max_loss_usd=10.0,  # $10 absolute emergency floor to prevent exchange force-close
            )
            if _smart_exit["exit"] and not exit_reason:
                exit_reason = _smart_exit["exit_type"]
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "smart_exit",
                    "exit_type": _smart_exit["exit_type"],
                    "detail": _smart_exit["reason"],
                    "confidence": _smart_exit["confidence"],
                    "price": price,
                    "entry_price": entry_price,
                    "pnl_usd": pnl_usd,
                    "support": _smart_exit.get("support", 0),
                    "resistance": _smart_exit.get("resistance", 0),
                })
        except Exception:
            pass  # if smart_exit fails, fall through to other exit logic
        # AI Executive: forced exit — Claude says EXIT or FLAT while in a trade
        _ai_d = ai_advisor.get_directive()
        _ai_min_conf = float((config.get("ai") or {}).get("executive_min_confidence", 0.6))
        _ai_exec_exit = bool(
            _ai_d
            and _ai_d.get("action") in ("EXIT", "FLAT")
            and float(_ai_d.get("confidence", 0)) >= _ai_min_conf
            and ai_advisor.is_executive_mode()
        )
        # AI exit_eval: exit_now with low hold confidence = force close
        _ai_exit_eval = ai_advisor.get_cached_insight("exit_eval")
        _ai_exit_eval_force = bool(
            _ai_exit_eval
            and _ai_exit_eval.get("urgency") == "exit_now"
            and float(_ai_exit_eval.get("hold_confidence", 1.0)) <= 0.20
            and ai_advisor.is_executive_mode()
        )
        # Minimum hold timer: suppress soft exits for first 60 seconds to avoid noise
        _hold_secs = (now - entry_time).total_seconds() if entry_time else 9999
        _min_hold_met = _hold_secs >= 60

        # === HYBRID EXIT LOGIC: Chart-aware + Mechanical safety net ===
        # Chart signals get priority, but mechanical exits protect capital.
        # Re-enabled 2026-03-18: mirror-only strategy was bleeding money.
        if _ai_exec_exit:
            exit_reason = "ai_executive_exit"
        elif _ai_exit_eval_force:
            exit_reason = "ai_exit_eval_force"
        elif friday_break_derisk:
            exit_reason = "friday_break_derisk"
        elif cutoff_derisk:
            exit_reason = "cutoff_derisk"
        elif trend_flip:
            exit_reason = "trend_flip"
        elif reversal:
            exit_reason = "reversal_signal"
        # --- PROFIT-SIDE MECHANICAL EXITS (lock wins, never cut losers) ---
        elif _min_hold_met and tp_hit:
            exit_reason = "tp1"
        elif _min_hold_met and profit_lock_hit:
            exit_reason = "profit_lock"
        elif _min_hold_met and _min_floor_hit:
            exit_reason = "min_profit_floor"
        elif _min_hold_met and _decay_exit_hit:
            exit_reason = "profit_decay"
        elif _min_hold_met and recovery_hit:
            exit_reason = "recovery_take_profit"
        elif _min_hold_met and break_even_hit:
            exit_reason = "break_even"

        # --- Moonshot exit override ---
        if moonshot_state and moonshot_state.active:
            if exit_reason:
                suppress, replacement = moonshot_overrides_exit(moonshot_state, exit_reason, price, direction)
                if suppress:
                    exit_reason = None
                elif replacement:
                    exit_reason = replacement
            elif moonshot_trail_hit(moonshot_state, price, direction):
                exit_reason = "moonshot_trail_stop"

        # --- Runner exit override ---
        if _runner_active:
            _rs = open_pos.get("runner_state") or {}
            _RUNNER_SUPPRESS = {"tp1", "time_stop", "early_save", "profit_lock", "min_profit_floor", "profit_decay"}
            if not exit_reason:
                # Check runner-specific exit conditions
                _r_trail = float(_rs.get("trail_price") or 0)
                if direction == "short" and _r_trail > 0 and price >= _r_trail:
                    exit_reason = "runner_trail_stop"
                elif direction == "long" and _r_trail > 0 and price <= _r_trail:
                    exit_reason = "runner_trail_stop"
                elif int(_rs.get("consec_against") or 0) >= int(_runner_cfg.get("reversal_bars", 2) or 2):
                    exit_reason = "runner_reversal"
                elif curr_upnl < float(_rs.get("floor_usd") or 0):
                    exit_reason = "runner_floor_hit"
            elif exit_reason in _RUNNER_SUPPRESS:
                exit_reason = None  # suppress — let the runner ride

        if exit_reason:
            durable.log_event("exit_position", {"exit_reason": exit_reason, "direction": direction, "paper": bool(paper)})
            entry_time_raw = open_pos.get("entry_time")
            exit_time_iso = now.isoformat()
            if (not paper) and pos_product_id:
                # --- FORCE FLATTEN: Cancel + close + verify in a loop until flat ---
                # Step 1: Initial cancel + close attempt
                cancel_info = api.cancel_open_orders(product_id=pos_product_id)
                close_info = api.close_cfm_position(pos_product_id, paper=False)
                log_decision(
                    config,
                    {
                        "timestamp": now.isoformat(),
                        "reason": "exit_order_sent",
                        "exit_reason": exit_reason,
                        "product_id": pos_product_id,
                        "entry_time": entry_time_raw,
                        "exit_time": exit_time_iso,
                        "time_in_trade_min": _minutes_between(entry_time_raw, exit_time_iso),
                        "cancel_info": cancel_info,
                        "close_info": close_info,
                    },
                )

                # Step 2: Force-flatten — keeps trying until exchange confirms position=0
                # 5 attempts × (cancel + market close + 1.5s wait + verify) = ~12s max
                _flatten = _force_flatten_position(api, pos_product_id, max_rounds=3)

                # Step 3: Get fill data from the best available order
                _exit_order_id = None
                try:
                    _exit_order_id = (
                        _flatten.get("order_id")
                        or ((close_info or {}).get("result") or {}).get("order_id")
                        or (((close_info or {}).get("result") or {}).get("success_response") or {}).get("order_id")
                    )
                except Exception:
                    pass
                _exit_fill = verify_fill(api, _exit_order_id) if _exit_order_id else None
                _exit_fill_verified = bool(_exit_fill and _exit_fill.get("filled"))
                _exit_fill_price = float(_exit_fill.get("average_filled_price") or 0) if _exit_fill else 0
                _exit_fees = float(_exit_fill.get("total_fees") or 0) if _exit_fill else 0

                # Step 4: If STILL not flat after 5 attempts, keep position and retry next cycle
                if not _flatten["flat"]:
                    log_incident({
                        "timestamp": now.isoformat(),
                        "type": "FORCE_CLOSE_FAILED",
                        "exit_reason": exit_reason,
                        "product_id": pos_product_id,
                        "flatten_attempts": _flatten["attempts"],
                    })
                    slack_alert.send(
                        f"FORCE CLOSE FAILED — {_flatten['attempts']} attempts for {exit_reason}. "
                        f"Position still open. Retrying in 5s.",
                        level="error",
                    )
                    # Don't log exit, don't clear position — bot will retry in 5s
                    save_state(state)
                    return

                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "exit_fill_check",
                    "exit_reason": exit_reason,
                    "exit_order_id": _exit_order_id,
                    "fill_verified": _exit_fill_verified,
                    "fill_price": _exit_fill_price,
                    "fees_usd": _exit_fees,
                    "mark_price": _pnl_price,
                    "position_confirmed_closed": True,
                    "flatten_method": _flatten.get("method") or "initial_close",
                    "flatten_rounds": _flatten.get("attempts", 0),
                })

            else:
                # Paper trade or no product_id — no exchange verification possible
                _exit_order_id = None
                _exit_fill_verified = False
                _exit_fill_price = 0
                _exit_fees = 0

            # Use exchange fill price for exit when available, else mark price, else candle
            _verified_exit_price = _exit_fill_price if _exit_fill_price > 0 else (_pnl_price if _pnl_price and _pnl_price > 0 else price)

            # Recalculate PnL from verified prices when we have exchange fill data
            if _exit_fill_price > 0 and entry_price > 0:
                if direction == "long":
                    pnl_pct = (_exit_fill_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - _exit_fill_price) / entry_price
                _size = int(open_pos.get("size") or 0)
                pnl_usd_live = pnl_pct * entry_price * _size * contract_size

            # Subtract exchange fees from PnL (entry + exit)
            _entry_fees = float(open_pos.get("entry_fees_usd") or 0)
            _total_fees = _entry_fees + _exit_fees
            if _total_fees <= 0:
                _total_fees = float(open_pos.get("estimated_round_trip_fees") or 0)
            if pnl_usd_live is not None and _total_fees > 0:
                pnl_usd_live -= _total_fees

            result = "win" if pnl_pct > 0 else "loss" if pnl_pct < 0 else "flat"
            pnl_usd = pnl_usd_live
            # Guard: only count win/loss ONCE per unique entry_time to prevent
            # double-counting when close_cfm_position reports success but exchange
            # still holds the position (reconcile re-opens → exit fires again).
            _last_counted_entry = str(state.get("_last_exit_counted_entry") or "")
            _this_entry = str(entry_time_raw or "")
            _already_counted = bool(_last_counted_entry and _this_entry and _last_counted_entry == _this_entry)
            if not _already_counted:
                state["_last_exit_counted_entry"] = _this_entry
                if result == "loss":
                    state["losses"] = int(state.get("losses") or 0) + 1
                    state["consecutive_losses"] = int(state.get("consecutive_losses") or 0) + 1
                    state["consecutive_wins"] = 0
                    if pnl_usd is not None:
                        state["loss_debt_usd"] = float(state.get("loss_debt_usd") or 0.0) + abs(float(pnl_usd))
                elif result == "win":
                    state["consecutive_losses"] = 0
                    state["consecutive_wins"] = int(state.get("consecutive_wins") or 0) + 1
                    if pnl_usd is not None and pnl_usd > 0:
                        state["loss_debt_usd"] = max(0.0, float(state.get("loss_debt_usd") or 0.0) - float(pnl_usd))
                if pnl_usd is not None:
                    state["pnl_today_usd"] = float(state.get("pnl_today_usd") or 0.0) + pnl_usd

                # Recovery Mode: track loss direction and recovery cooldown
                if result == "loss":
                    state["last_loss_side"] = direction
                    if bool(open_pos.get("is_recovery_trade")):
                        v4_cfg_rm = config.get("v4", {}) if isinstance(config.get("v4"), dict) else {}
                        rm_cfg_exit = v4_cfg_rm.get("recovery_mode", {}) if isinstance(v4_cfg_rm.get("recovery_mode"), dict) else {}
                        _cool_min = float(rm_cfg_exit.get("cooldown_after_loss_minutes", 10) or 10)
                        state["recovery_cooldown_until"] = (now + timedelta(minutes=_cool_min)).isoformat()

                # Post-TP bias: after any TP exit, bias next trade opposite
                if exit_reason and "tp" in str(exit_reason).lower():
                    _opp = "short" if direction == "long" else "long"
                    state["post_tp_bias_side"] = _opp
                    state["post_tp_bias_set_at"] = now.isoformat()
                    state["post_tp_bias_trades_since"] = 0

                # Fetch exchange equity for reality check
                try:
                    _post_exit_eq = float(api.get_futures_equity() or 0)
                    if _post_exit_eq > 0:
                        state["exchange_equity_usd"] = _post_exit_eq
                        _eq_start = float(state.get("equity_start_usd") or 0)
                        _transfers = float(state.get("transfers_today_usd") or 0)
                        if _eq_start > 0:
                            state["exchange_pnl_today_usd"] = _post_exit_eq - _eq_start + _transfers
                except Exception:
                    pass
                if pnl_usd > 0:
                    funding_cfg = config.get("futures_funding", {})
                    if funding_cfg.get("auto_transfer", False):
                        split = float(funding_cfg.get("profit_split_pct", 0.5) or 0.5)
                        min_transfer = float(funding_cfg.get("min_transfer_usd", 0.0) or 0.0)
                        transfer_amt = pnl_usd * split
                        if transfer_amt >= min_transfer:
                            tx = api.transfer_futures_profit(transfer_amt, currency=str(funding_cfg.get("currency", "USDC")))
                            ok = bool((tx or {}).get("ok"))
                            move = {
                                "timestamp": now.isoformat(),
                                "type": "FUTURES_TO_SPOT_TRANSFER" if ok else "FUTURES_TO_SPOT_TRANSFER_FAILED",
                                "context": "profit_lock",
                                "ok": ok,
                                "reason": (tx or {}).get("reason"),
                                "amount_usd": float(transfer_amt),
                                "currency": str(funding_cfg.get("currency", "USDC")),
                                "transfer_direction": "futures_to_spot",
                                "transfer_response": (tx or {}).get("transfer_response"),
                                "source_portfolio_uuid": (tx or {}).get("source_portfolio_uuid"),
                                "target_portfolio_uuid": (tx or {}).get("target_portfolio_uuid"),
                                "transfers_today_usd": float(state.get("transfers_today_usd") or 0.0),
                                "conversion_cost_today_usd": float(state.get("conversion_cost_today_usd") or 0.0),
                            }
                            log_cash_movement(move)
                            durable.log_event("cash_movement", move)
                            log_decision(
                                config,
                                {
                                    "timestamp": now.isoformat(),
                                    "reason": "profit_transfer",
                                    "amount": transfer_amt,
                                    "currency": funding_cfg.get("currency", "USDC"),
                                    "ok": ok,
                                    "transfer_info": tx,
                                    "last_cash_movement": move,
                                },
                            )
            log_trade(
                config,
                _with_lifecycle_fields(
                    {
                        "timestamp": now.isoformat(),
                        "product_id": pos_product_id or product_id,
                        "side": direction,
                        "size": int(open_pos.get("size") or 0),
                        "entry_price": entry_price,
                        "exit_price": _verified_exit_price,
                        "pnl_pct": pnl_pct,
                        "pnl_usd": pnl_usd,
                        "result": result,
                        "exit_reason": exit_reason,
                        "exit_order_id": _exit_order_id,
                        "fill_verified": _exit_fill_verified,
                        "entry_fees_usd": _entry_fees,
                        "exit_fees_usd": _exit_fees,
                        "total_fees_usd": _total_fees,
                    },
                    entry_time=entry_time_raw,
                    exit_time=exit_time_iso,
                ),
            )
            _norm_held = (now - datetime.fromisoformat(str(open_pos.get("entry_time") or now.isoformat()))).total_seconds() / 60.0 if open_pos.get("entry_time") else 0
            _norm_exp = ((open_pos.get("exit_watch") or {}).get("close_eta") or {}).get("expected_hold_min")
            _rn_kw = {}
            if str(exit_reason).startswith("runner_"):
                _rn_kw["runner_bars"] = int((open_pos.get("runner_state") or {}).get("bars_active") or 0)
            _exit_ai_eval = ((ai_advisor.get_cached_insight("exit_eval")) or {}) if ai_advisor else {}
            slack_alert.trade_exit(
                direction=direction, exit_reason=exit_reason,
                entry_price=entry_price, exit_price=_verified_exit_price,
                pnl_usd=pnl_usd, pnl_pct=pnl_pct, fill_verified=_exit_fill_verified,
                held_min=_norm_held, expected_hold_min=_norm_exp,
                size=int(open_pos.get("size") or 1),
                ai_size=int(open_pos.get("size") or 1),
                ai_exit_urgency=_exit_ai_eval.get("urgency", ""),
                ai_hold_confidence=_exit_ai_eval.get("hold_confidence"),
                ai_exit_reasoning=_exit_ai_eval.get("reasoning", ""),
                **_rn_kw,
            )
            # War room: broadcast exit with agent views
            try:
                _wr_exit_views = agent_comms.get_all_assessments() if agent_comms.is_enabled() else {}
                slack_alert.war_room_trade_close(
                    direction=direction, pnl_usd=pnl_usd, exit_reason=exit_reason,
                    hold_minutes=int(_norm_held) if _norm_held else None,
                    agent_views=_wr_exit_views,
                )
            except Exception:
                pass
            state["last_exit_time"] = exit_time_iso
            state["open_position"] = None

            # Post-loss debrief: fire AI deep dive during cooldown
            if result == "loss" and ai_advisor and pnl_usd is not None:
                try:
                    _lost_trade_info = {
                        "direction": direction,
                        "entry_price": entry_price,
                        "exit_price": _verified_exit_price,
                        "pnl_usd": pnl_usd,
                        "pnl_pct": pnl_pct,
                        "exit_reason": exit_reason,
                        "entry_type": str(open_pos.get("entry_type") or ""),
                        "strategy_regime": str(open_pos.get("strategy_regime") or ""),
                        "lane": str(open_pos.get("lane_label") or ""),
                        "confluence_score": open_pos.get("confluence_score"),
                        "held_minutes": round(_norm_held, 1) if _norm_held else 0,
                        "size": int(open_pos.get("size") or 1),
                    }
                    ai_advisor.debrief_loss(
                        lost_trade=_lost_trade_info,
                        state=state,
                        df_15m=df_15m if "df_15m" in dir() else None,
                        df_1h=df_1h if "df_1h" in dir() else None,
                        regime_v4=regime_v4 if "regime_v4" in dir() else None,
                        expansion_state=expansion_state if "expansion_state" in dir() else None,
                    )
                except Exception as _debrief_exc:
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "loss_debrief_error",
                        "error": str(_debrief_exc),
                    })

            if bool(reverse_cfg.get("enabled", False)):
                allowed_reasons = set(reverse_cfg.get("allowed_exit_reasons", ["reversal_signal", "trend_flip"]) or [])
                require_opposite = bool(reverse_cfg.get("require_opposite_direction", True))
                require_profitable = bool(reverse_cfg.get("require_profitable_exit", True))
                candidate_entry = entry_candidate
                candidate_dir = str(direction_candidate or "")
                candidate_v4 = selected_v4_candidate
                candidate_breakout = breakout_type_candidate
                dynamic_candidate = False

                # Skip flip if exit was a loss and require_profitable_exit is on
                _exit_was_profitable = (result == "win") or (pnl_usd is not None and pnl_usd > 0)
                _profit_gate_ok = _exit_was_profitable or (not require_profitable)

                # If no preselected candidate exists, synthesize one from opposite-side v4 score.
                if (not candidate_entry or not candidate_dir) and exit_reason in allowed_reasons and _profit_gate_ok:
                    if bool((opp_score or {}).get("pass")):
                        candidate_entry = {
                            "type": "reverse_after_exit",
                            "confluence": dict(opp_conf) if isinstance(opp_conf, dict) else {},
                        }
                        candidate_dir = opp_dir
                        candidate_v4 = dict(opp_score) if isinstance(opp_score, dict) else None
                        candidate_breakout = opp_breakout_type
                        dynamic_candidate = True

                candidate_ok = bool(candidate_entry) and bool(candidate_dir)
                opposite_ok = (candidate_dir == opp_dir)
                if (
                    exit_reason in allowed_reasons
                    and candidate_ok
                    and _profit_gate_ok
                    and (opposite_ok or (not require_opposite))
                ):
                    entry_candidate = candidate_entry
                    direction_candidate = candidate_dir
                    selected_v4_candidate = candidate_v4
                    breakout_type_candidate = candidate_breakout
                    continue_after_exit = True
                    log_decision(
                        config,
                        {
                            "timestamp": now.isoformat(),
                            "reason": "reverse_reentry_armed",
                            "exit_reason": exit_reason,
                            "exit_pnl_usd": pnl_usd,
                            "candidate_direction": candidate_dir,
                            "candidate_type": (candidate_entry or {}).get("type"),
                            "candidate_score": (candidate_v4 or {}).get("score"),
                            "candidate_threshold": (candidate_v4 or {}).get("threshold"),
                            "dynamic_candidate": dynamic_candidate,
                            "require_opposite_direction": require_opposite,
                            "opposite_ok": opposite_ok,
                        },
                    )
                    slack_alert.send(
                        f"FLIP ENTRY ARMED — exited {direction.upper()} with {'+' if (pnl_usd or 0) >= 0 else ''}${pnl_usd:.2f} "
                        f"via {exit_reason}. Scoring {candidate_dir.upper()} entry...",
                        level="info",
                    )
                else:
                    log_decision(
                        config,
                        {
                            "timestamp": now.isoformat(),
                            "reason": "reverse_reentry_skipped",
                            "exit_reason": exit_reason,
                            "exit_pnl_usd": pnl_usd,
                            "exit_was_profitable": _exit_was_profitable,
                            "profit_gate_ok": _profit_gate_ok,
                            "candidate_direction": candidate_dir or None,
                            "candidate_exists": candidate_ok,
                            "dynamic_candidate": dynamic_candidate,
                            "require_opposite_direction": require_opposite,
                            "opposite_ok": opposite_ok,
                            "allowed_reasons": sorted(list(allowed_reasons)),
                        },
                    )
        else:
            open_pos["adverse_bars"] = adverse
            try:
                open_pos["exit_watch"] = {
                    "bars_since": int(bars_since),
                    "pnl_pct": float(pnl_pct),
                    "adverse_bars": int(adverse),
                    "breakout_type": breakout_type,
                    "tp1": float(tp_plan.tp1) if tp_plan.tp1 is not None else None,
                    "tp2": float(tp_plan.tp2) if tp_plan.tp2 is not None else None,
                    "tp3": float(tp_plan.tp3) if tp_plan.tp3 is not None else None,
                    "dynamic_tp": float(dynamic_tp_price) if dynamic_tp_price is not None else None,
                    "tp_hit": bool(tp_hit),
                    "time_stop": bool(time_stop),
                    "reversal": bool(reversal),
                    "max_unrealized_usd": float(max_unrealized_usd),
                    "giveback_usd": float(giveback_usd),
                    "profit_lock_armed": bool(lock_armed),
                    "profit_lock_floor_usd": float(lock_floor_usd) if lock_floor_usd is not None else None,
                    "profit_lock_hit": bool(profit_lock_hit),
                    "profit_lock_tier": _pl_tier,
                    "profit_lock_activate": float(activate_usd) if bool(profit_lock_cfg.get("enabled", True)) else None,
                    "profit_lock_max_giveback": float(max_giveback) if bool(profit_lock_cfg.get("enabled", True)) else None,
                    "trend_flip": bool(trend_flip),
                    "cutoff_derisk": bool(cutoff_derisk),
                    "friday_break_derisk": bool(friday_break_derisk),
                    "recovery_target_usd": recovery_target,
                    "next_exit_reason": None,
                    "moonshot_active": bool(moonshot_state and moonshot_state.active) if moonshot_state else False,
                    "moonshot_trail_stop": float(moonshot_state.trailing_stop_price) if moonshot_state and moonshot_state.trailing_stop_price else None,
                    "moonshot_peak": float(moonshot_state.peak_price) if moonshot_state and moonshot_state.peak_price else None,
                    "trend_healthy": bool(trend_healthy),
                    # Runner mode
                    "runner_active": bool(_runner_active),
                    "runner_trail_price": float(_runner_state.get("trail_price") or 0) if _runner_active else None,
                    "runner_peak": float(_runner_state.get("peak_price") or 0) if _runner_active else None,
                    "runner_fib_786": float(_runner_state.get("fib_786") or 0) if _runner_active else None,
                    "runner_fib_tightened": bool(_runner_state.get("fib_tightened")) if _runner_active else False,
                    "runner_bars": int(_runner_state.get("bars_active") or 0) if _runner_active else 0,
                    "runner_floor_usd": float(_runner_state.get("floor_usd") or 0) if _runner_active else None,
                    # Profit protection lanes
                    "trade_state": _trade_state,
                    "min_floor_armed": bool(_mf_armed if bool(_min_floor_cfg.get("enabled", True)) else False),
                    "min_floor_usd": float(_mf_usd) if bool(_min_floor_cfg.get("enabled", True)) else None,
                    "decay_retrace_pct": round(giveback_usd / max_unrealized_usd, 3) if max_unrealized_usd > 0 else 0.0,
                    "decay_threshold_pct": round(_de_pct, 3) if bool(_decay_cfg.get("enabled", True)) else None,
                    "decay_armed": bool(max_unrealized_usd >= _de_arm) if bool(_decay_cfg.get("enabled", True)) else False,
                }
            except Exception:
                pass
            # Compute close ETA and embed in exit_watch
            try:
                _trades_path = os.path.join(os.path.dirname(__file__), "logs", "trades.csv")
                _trades_for_eta = pd.read_csv(_trades_path) if os.path.exists(_trades_path) else pd.DataFrame()
                _close_eta = estimate_close_eta(open_pos, _trades_for_eta, now)
                open_pos.setdefault("exit_watch", {})["close_eta"] = _close_eta
            except Exception:
                pass
            state["open_position"] = open_pos
        _cd_thresh = int(config.get("risk", {}).get("cooldown_loss_threshold", 3) or 3)
        if int(state.get("consecutive_losses") or 0) >= _cd_thresh:
            _update_cooldown(state, now, int(config["risk"]["cooldown_minutes"]))
        # Post-exit: reconcile balances (sweeps derivatives → spot USDC for yield)
        if not state.get("open_position") and not paper:
            try:
                _run_balance_reconcile(
                    config=config, state=state, api=api,
                    durable=durable, now=now, mode="POST_EXIT",
                )
            except Exception:
                pass
            # Fallback direct sweep if reconciler disabled
            try:
                _sweep_derivatives_to_spot(
                    config=config, state=state, api=api,
                    durable=durable, now=now, context="post_exit_sweep",
                )
            except Exception:
                pass
        # Save trend_continuation re-entry state for next cycle
        _exit_pnl = locals().get("pnl_usd")
        if str(open_pos.get("entry_type") or "") == "trend_continuation" and _exit_pnl is not None and _exit_pnl > 0:
            try:
                _reentry_bias = detect_15m_structure_bias(df_15m)
                _structure_intact = (
                    (direction == "short" and _reentry_bias == "bearish") or
                    (direction == "long" and _reentry_bias == "bullish")
                )
                state["_last_trend_exit_structure_intact"] = _structure_intact
                state["_last_trend_exit_direction"] = direction
                state["_last_trend_exit_price"] = float(_verified_exit_price or 0)
                state["_last_trend_entry_price"] = float(entry_price or 0)
            except Exception:
                state["_last_trend_exit_structure_intact"] = False
        else:
            state["_last_trend_exit_structure_intact"] = False
        # Save swing context for fib_retrace awareness on next cycle
        try:
            _sw_1h = _detect_swing_points(df_1h.tail(48), left=3, right=3)
            _sw_highs = _sw_1h.get("swing_highs", [])
            _sw_lows = _sw_1h.get("swing_lows", [])
            if _sw_highs and _sw_lows:
                state["_fib_swing_context"] = {
                    "last_swing_high": _sw_highs[0][1],
                    "last_swing_low": _sw_lows[0][1],
                    "exit_price": float(_verified_exit_price or price),
                    "exit_direction": direction,
                    "exit_time": now.isoformat(),
                }
        except Exception:
            pass
        save_state(state)
        durable.set_kv("open_position", state.get("open_position"))
        if not continue_after_exit:
            return
        entry = entry_candidate
        direction = direction_candidate
        selected_v4 = selected_v4_candidate
        breakout_type = breakout_type_candidate
        if bool(reverse_cfg.get("ignore_cooldown", True)):
            cooldown = False

    # Balance reconciliation: sweep derivatives → spot USDC, detect drift, self-heal
    _recon_result = None
    if not state.get("open_position") and not paper:
        try:
            _recon_result = _run_balance_reconcile(
                config=config, state=state, api=api,
                durable=durable, now=now, mode="IDLE",
            )
        except Exception:
            pass
        # Fallback direct sweep if reconciler disabled
        try:
            _sweep_derivatives_to_spot(
                config=config, state=state, api=api,
                durable=durable, now=now, context="idle_sweep",
            )
        except Exception:
            pass

    # Block entries if balance reconciler is in SAFE_MODE
    if _recon_result and _recon_result.safe_mode:
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "safe_mode_block",
            "reconcile_status": _recon_result.status,
            "safe_mode_reason": _recon_result.safe_mode_reason,
            "thought": f"SAFE MODE active: {_recon_result.safe_mode_reason} — no new entries",
        })
        save_state(state)
        return

    # --- Hard dollar drawdown cap (AI executive CANNOT override this) ---
    _rm_cfg_dd = (v4_cfg.get("recovery_mode") or {}) if isinstance(v4_cfg.get("recovery_mode"), dict) else {}
    _hard_dd_cap = float(_rm_cfg_dd.get("max_daily_drawdown_usd", 9999.0) or 9999.0)
    _hard_dd_cap_pct = float(_rm_cfg_dd.get("max_daily_drawdown_pct", 0) or 0)
    if _hard_dd_cap_pct > 0 and equity_start > 0:
        _hard_dd_cap = min(_hard_dd_cap if _hard_dd_cap < 9000 else 9999, equity_start * _hard_dd_cap_pct)
    if _hard_dd_cap < 9000 and not open_pos:
        _dd_today_hard = abs(min(0.0, float(state.get("pnl_today_usd", 0) or 0)))
        if _dd_today_hard >= _hard_dd_cap:
            _hard_dd_reason = f"hard_drawdown_cap: -${_dd_today_hard:.2f} today >= cap ${_hard_dd_cap:.2f}"
            state["_safe_mode"] = True
            state["safe_mode"] = True
            state["safe_mode_reason"] = _hard_dd_reason
            log_decision(config, {"timestamp": now.isoformat(), "reason": "hard_drawdown_cap", "detail": _hard_dd_reason})
            slack_alert.send(
                f":stop_sign: HARD DRAWDOWN CAP: -${_dd_today_hard:.2f} today (limit ${_hard_dd_cap:.2f}). No new entries until tomorrow.",
                level="critical",
            )
            save_state(state)
            return

    # --- Combined circuit breaker: streak + drawdown ---
    cb_cfg = (v4_cfg.get("circuit_breaker") or {}) if isinstance(v4_cfg.get("circuit_breaker"), dict) else {}
    if bool(cb_cfg.get("enabled", False)) and not open_pos:
        _cb_losses = int(state.get("losses", 0) or 0)
        _cb_dd = abs(min(0.0, float(state.get("pnl_today_usd", 0) or 0)))
        _cb_combo_losses = int(cb_cfg.get("combo_loss_count", 3) or 3)
        _cb_combo_dd = float(cb_cfg.get("combo_drawdown_usd", 20.0) or 20.0)
        _cb_combo_dd_pct = float(cb_cfg.get("combo_drawdown_pct", 0) or 0)
        if _cb_combo_dd_pct > 0 and equity_start > 0:
            _cb_combo_dd = max(_cb_combo_dd, equity_start * _cb_combo_dd_pct)
        if _cb_losses >= _cb_combo_losses and _cb_dd >= _cb_combo_dd:
            _cb_reason = f"circuit_breaker: {_cb_losses} losses + ${_cb_dd:.2f} drawdown today"
            _cb_htf_str = ""
            if _htf_bias:
                _cb_htf_str = (
                    f" | HTF: {_htf_bias.get('bias','?')} "
                    f"RSI={_htf_bias.get('rsi_1h', 0):.0f} "
                    f"slope={_htf_bias.get('ema21_slope_pct', 0)*100:.2f}%"
                )
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "circuit_breaker_trip",
                "detail": _cb_reason,
                "htf_bias": _htf_bias,
                "thought": f"Circuit breaker tripped: {_cb_reason}{_cb_htf_str}. No new entries today.",
            })
            if cb_cfg.get("notify_slack", True):
                slack_alert.send(
                    f":no_entry: CIRCUIT BREAKER: {_cb_losses} losses, -${_cb_dd:.2f} today{_cb_htf_str}. No new entries until next session.",
                    level="critical",
                )
            save_state(state)
            return

    product_available = api.is_product_available(product_id) if product_id else False
    ks_cfg = (v4_cfg.get("kill_switches") or {}) if isinstance(v4_cfg.get("kill_switches"), dict) else {}
    spread_limit = float(ks_cfg.get("max_spread_pct", 0.0035) or 0.0035)
    spread_fail = bool(spread_estimate and spread_estimate > spread_limit)
    fail_safe = bool(spread_fail or high_vol_pause)
    # --- Adaptive score threshold ---
    adaptive_threshold = None
    adaptive_reason = None
    try:
        logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
        trades_csv = _resolve_output_path(logging_cfg.get("trades_csv", "trades.csv"), LOGS_DIR)
        orig_threshold = int((selected_v4 or {}).get("threshold") or 0)
        adaptive_threshold, adaptive_reason = compute_adaptive_threshold(trades_csv, config, orig_threshold)
        if adaptive_threshold > orig_threshold and selected_v4 is not None:
            selected_v4 = dict(selected_v4)
            selected_v4["threshold"] = adaptive_threshold
            selected_v4["pass"] = bool(int(selected_v4.get("score") or 0) >= adaptive_threshold)
    except Exception:
        adaptive_reason = "adaptive_error"

    # --- Volatility-adaptive threshold (raises threshold in high-vol regimes) ---
    vol_adaptive_threshold = None
    vol_adaptive_reason = None
    try:
        _atr_s = atr(df_15m, 14)
        _atr_now_v = float(_atr_s.iloc[-1]) if len(_atr_s) and not pd.isna(_atr_s.iloc[-1]) else 0.0
        _atr_m20 = float(_atr_s.rolling(20).mean().iloc[-1]) if len(_atr_s) >= 20 and not pd.isna(_atr_s.rolling(20).mean().iloc[-1]) else _atr_now_v
        _vol_adapt_cfg = (v4_cfg.get("vol_adaptive_threshold") or {}) if isinstance(v4_cfg.get("vol_adaptive_threshold"), dict) else {}
        if bool(_vol_adapt_cfg.get("enabled", True)) and _atr_now_v > 0 and selected_v4 is not None:
            _cur_thr = int((selected_v4 or {}).get("threshold") or 0)
            vol_adaptive_threshold, vol_adaptive_reason = compute_vol_adaptive_threshold(
                _cur_thr, _atr_now_v, _atr_m20
            )
            if vol_adaptive_threshold > _cur_thr:
                selected_v4 = dict(selected_v4)
                selected_v4["threshold"] = vol_adaptive_threshold
                selected_v4["pass"] = bool(int(selected_v4.get("score") or 0) >= vol_adaptive_threshold)
    except Exception:
        vol_adaptive_reason = "vol_adapt_error"

    # --- Trade learning: consult past lessons before entry ---
    _lesson_advice = {}
    try:
        if selected_v4 and selected_direction:
            _lesson_advice = trade_reviewer.consult_lessons(
                direction=selected_direction,
                entry_signal=str(selected_entry_signal or ""),
                price=price,
                market_conditions={
                    "vol_phase": expansion_state.get("phase"),
                    "pulse_regime": str(_pulse_regime),
                },
            )
            _lesson_mod = int(_lesson_advice.get("lesson_score_modifier") or 0)
            if _lesson_mod != 0 and selected_v4 is not None:
                selected_v4 = dict(selected_v4)
                old_score = int(selected_v4.get("score") or 0)
                selected_v4["score"] = max(0, old_score + _lesson_mod)
                selected_v4["pass"] = bool(selected_v4["score"] >= int(selected_v4.get("threshold") or 0))
    except Exception:
        pass

    score_gate_pass = bool((selected_v4 or {}).get("pass"))
    score_gate_strict = bool(v4_cfg.get("strict_score_gate", True))
    score_gate_pass_effective = bool(score_gate_pass)

    # --- Contract score modifiers ---
    contract_mod = None
    cascade_event = None
    try:
        if contract_ctx and direction:
            cc_cfg = (config.get("contract_context") or {}) if isinstance(config.get("contract_context"), dict) else {}
            contract_mod = score_contract_modifiers(direction, contract_ctx, candle_ctx, cc_cfg)
            if contract_mod and contract_mod.bonus != 0 and selected_v4 is not None:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + contract_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
            cascade_event = detect_liquidation_cascade(contract_ctx, candle_ctx, cc_cfg)
            if cascade_event:
                log_cascade_event(cascade_event, Path(LOGS_DIR) / "liquidation_events.jsonl")
    except Exception:
        pass

    orderbook_mod = None
    try:
        if orderbook_ctx and direction and selected_v4 is not None:
            orderbook_mod = score_orderbook_modifier(direction, orderbook_ctx, ms_cfg)
            if orderbook_mod and orderbook_mod.bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + orderbook_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    futures_relativity = (
        market_intel.get("futures_relativity")
        if isinstance(market_intel, dict) and isinstance(market_intel.get("futures_relativity"), dict)
        else {}
    )
    futures_relativity_mod = None
    weekly_research = perplexity_advisor.get_latest_weekly_market_research(config=config)
    market_intel_state = market_intel_state if isinstance(market_intel_state, dict) else {}
    _weekly_playbook = market_intel_state.get("weekly_playbook") if isinstance(market_intel_state.get("weekly_playbook"), dict) else {}
    _event_calendar = market_intel_state.get("event_calendar") if isinstance(market_intel_state.get("event_calendar"), dict) else {}
    _source_scoreboard = market_intel_state.get("source_scoreboard") if isinstance(market_intel_state.get("source_scoreboard"), dict) else {}
    _crowding_summary = market_intel_state.get("crowding_summary") if isinstance(market_intel_state.get("crowding_summary"), dict) else {}
    if not _weekly_playbook:
        try:
            _weekly_playbook = market_intel_service.get_latest_weekly_playbook(DATA_DIR)
        except Exception:
            _weekly_playbook = {}
    if not _event_calendar:
        try:
            _event_calendar = market_intel_service.get_latest_event_calendar(DATA_DIR)
        except Exception:
            _event_calendar = {}
    if not _source_scoreboard:
        try:
            _source_scoreboard = market_intel_service.get_latest_source_scoreboard(DATA_DIR)
        except Exception:
            _source_scoreboard = {}
    if not _crowding_summary:
        try:
            _crowding_summary = market_intel_service.get_latest_crowding_summary(DATA_DIR)
        except Exception:
            _crowding_summary = {}
    _next_event = _event_calendar.get("next_event") if isinstance(_event_calendar.get("next_event"), dict) else {}
    weekly_research_bonus = 0
    weekly_research_reasons: list[str] = []
    try:
        _fr_cfg = (market_cfg.get("futures_relativity") or {}) if isinstance(market_cfg, dict) else {}
        if futures_relativity and direction and selected_v4 is not None:
            futures_relativity_mod = score_futures_relativity(
                direction,
                futures_relativity,
                orderbook_ctx=orderbook_ctx,
                contract_ctx=contract_ctx,
                config=_fr_cfg,
            )
            if futures_relativity_mod and futures_relativity_mod.bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + futures_relativity_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    try:
        if weekly_research and direction and selected_v4 is not None:
            weekly_research_bonus, weekly_research_reasons = _score_weekly_research_modifier(
                direction,
                weekly_research,
                config=config,
            )
            if weekly_research_bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + weekly_research_bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        weekly_research_bonus = 0
        weekly_research_reasons = []

    liquidation_mod = None
    try:
        if direction and selected_v4 is not None:
            liquidation_mod = score_liquidation_modifier(direction, liquidation_ctx, liquidation_cfg)
            if liquidation_mod and liquidation_mod.bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + liquidation_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Zone score modifier ---
    zone_mod = None
    try:
        if direction and zone_context:
            zone_mod = score_zone_modifier(direction, zone_context)
            if zone_mod and zone_mod.bonus != 0 and selected_v4 is not None:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + zone_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Wick zone proximity modifier ---
    _wz_prox = {"near_zone": False}
    try:
        if direction and _wick_zones and selected_v4 is not None:
            _atr_for_wz = float(atr(df_15m, 14).iloc[-1]) if not df_15m.empty else 0.0
            _wz_prox = zone_proximity_score(price, _wick_zones, direction, _atr_for_wz)
            if _wz_prox.get("near_zone") and _wz_prox.get("confidence", 0) >= 0.3:
                _wz_bonus = int(min(8, _wz_prox["confidence"] * 12))
                if _wz_bonus > 0:
                    selected_v4 = dict(selected_v4)
                    adjusted = int(selected_v4.get("score") or 0) + _wz_bonus
                    selected_v4["score"] = max(0, min(100, adjusted))
                    selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                    score_gate_pass = bool(selected_v4["pass"])
                    score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Pattern memory modifier (double tops, channels, breakouts, fakeouts) ---
    _pattern_mod = 0
    try:
        if direction and _active_patterns and selected_v4 is not None:
            _pattern_mod = pattern_score_modifier(_active_patterns, direction)
            if _pattern_mod != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + _pattern_mod
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Multi-TF alignment modifier ---
    alignment_mod = None
    try:
        align_cfg = (v4_cfg.get("alignment") or {}) if isinstance(v4_cfg.get("alignment"), dict) else {}
        if bool(align_cfg.get("enabled", False)) and direction and selected_v4 is not None:
            alignment_mod = score_alignment_modifier(direction, df_15m, df_1h, df_4h, align_cfg, df_1d=df_1d, df_1w=df_1w)
            if alignment_mod and alignment_mod.bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + alignment_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Institutional OI gate (penalizes shorts during accumulation) ---
    inst_mod = None
    try:
        if contract_ctx and direction and selected_v4 is not None:
            _inst_cfg = (v4_cfg.get("institutional_gate") or {}) if isinstance(v4_cfg.get("institutional_gate"), dict) else {}
            inst_mod = institutional_oi_gate(direction, contract_ctx, _inst_cfg)
            if inst_mod and inst_mod.bonus != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + inst_mod.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Multi-lane consensus bonus (multiple signals = higher conviction) ---
    consensus_result = None
    try:
        if direction and selected_v4 is not None and lane_result is not None:
            _sweep_dir = sweep_long if direction == "long" else sweep_short
            _squeeze_dir = squeeze_long if direction == "long" else squeeze_short
            consensus_result = evaluate_lane_consensus(
                primary_lane=lane_result.lane,
                direction=direction,
                regime=str(regime_v4.get("regime", "neutral")),
                expansion_phase=str((expansion_state or {}).get("phase", "COMPRESSION")),
                sweep=_sweep_dir,
                squeeze=_squeeze_dir,
                contract_ctx=contract_ctx,
                df_15m=df_15m,
                df_1h=df_1h,
                df_4h=df_4h,
                config=config,
            )
            if consensus_result and consensus_result.bonus > 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + consensus_result.bonus
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- BTC correlation modifier ---
    btc_signal = None
    try:
        btc_cfg = (config.get("btc_correlation") or {}) if isinstance(config.get("btc_correlation"), dict) else {}
        if bool(btc_cfg.get("enabled", False)) and direction and selected_v4 is not None:
            from market.btc_correlation import compute_btc_signal
            btc_signal = compute_btc_signal(direction, btc_cfg)
            if btc_signal and btc_signal.score_modifier != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + btc_signal.score_modifier
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Candlestick pattern modifier ---
    candle_pattern = None
    try:
        cp_cfg = (config.get("candle_patterns") or {}) if isinstance(config.get("candle_patterns"), dict) else {}
        if bool(cp_cfg.get("enabled", False)) and direction and selected_v4 is not None:
            from indicators.candle_patterns import detect_candle_patterns
            _v4_mr_flags = (selected_v4 or {}).get("mr_flags") or {}
            candle_pattern = detect_candle_patterns(
                df_15m, direction, cp_cfg,
                at_structure_level=bool(_v4_mr_flags.get("HTF_LEVEL")),
                at_fib_zone=bool(_v4_mr_flags.get("FIB_ZONE")),
            )
            if candle_pattern and candle_pattern.score_modifier != 0:
                selected_v4 = dict(selected_v4)
                adjusted = int(selected_v4.get("score") or 0) + candle_pattern.score_modifier
                selected_v4["score"] = max(0, min(100, adjusted))
                selected_v4["pass"] = bool(adjusted >= int(selected_v4.get("threshold") or 75))
                score_gate_pass = bool(selected_v4["pass"])
                score_gate_pass_effective = bool(score_gate_pass)
    except Exception:
        pass

    # --- Quality tier computation ---
    qt_cfg = (v4_cfg.get("quality_tiers") or {}) if isinstance(v4_cfg.get("quality_tiers"), dict) else {}
    quality_tier = _compute_quality_tier(
        int((selected_v4 or {}).get("score") or 0),
        int((selected_v4 or {}).get("threshold") or 75),
        qt_cfg,
    )

    consecutive_losses = int(state.get("consecutive_losses") or 0)
    sizing_meta = {}
    wait_since_last_exit_min = _minutes_between(state.get("last_exit_time"), now.isoformat())
    wait_since_last_entry_min = _minutes_between(state.get("last_entry_time"), now.isoformat())
    gates_effective = dict(gates or {})
    gates_pass_effective = bool(gates_pass)

    # --- Lane C ATR gate bypass ---
    lane_atr_bypassed = False
    if lane_result and lane_result.atr_gate_bypass and not gates_effective.get("atr_regime"):
        gates_effective["atr_regime"] = True
        gates_pass_effective = all(bool(v) for v in gates_effective.values())
        lane_atr_bypassed = True

    # --- Lane E distance gate bypass ---
    lane_distance_bypassed = False
    if lane_result and lane_result.distance_gate_bypass and not gates_effective.get("distance_from_value"):
        gates_effective["distance_from_value"] = True
        gates_pass_effective = all(bool(v) for v in gates_effective.values())
        lane_distance_bypassed = True

    # --- FULL/MONSTER quality bypass: distance gate ---
    # High-conviction signals shouldn't be killed by distance_from_value.
    # If the scoring engine says GO (FULL+), the signal quality is enough.
    if not gates_effective.get("distance_from_value"):
        if _TIER_RANK.get(quality_tier, 0) >= _TIER_RANK.get("FULL", 2):
            gates_effective["distance_from_value"] = True
            gates_pass_effective = all(bool(v) for v in gates_effective.values())
            lane_distance_bypassed = True

    selected_score_now = float((selected_v4 or {}).get("score") or 0.0)
    selected_regime_now = str((selected_v4 or {}).get("regime") or "").strip().lower()
    selected_direction_now = str(direction or "").strip().lower()
    selected_entry_type = str((entry or {}).get("type") or "").strip().lower()

    ev_cfg_probe = (v4_cfg.get("ev") or {}) if isinstance(v4_cfg.get("ev"), dict) else {}
    fee_model_probe = str(ev_cfg_probe.get("fee_model", "balanced") or "balanced").lower().strip()
    maker_probe = float(ev_cfg_probe.get("maker_fee_rate", 0.00085) or 0.00085)
    taker_probe = float(ev_cfg_probe.get("taker_fee_rate", 0.00090) or 0.00090)
    slip_probe = float(ev_cfg_probe.get("slippage_pct", 0.0002) or 0.0002)
    if fee_model_probe in ("conservative", "taker"):
        maker_probe = taker_probe
        slip_probe = max(slip_probe, 0.0005)
    elif fee_model_probe in ("maker_bias", "maker"):
        slip_probe = min(slip_probe, 0.0002)
    atr_now_probe = atr(df_15m, 14)
    atr_value_probe = _to_float(atr_now_probe.iloc[-1] if len(atr_now_probe) else None, 0.0) or 0.0
    margin_probe = api.estimate_required_margin(product_id, 1, direction, price=price) if product_id else {}
    contract_probe = _to_float((margin_probe or {}).get("contract_size"), 0.0) or 0.0

    def _ev_probe_for_override(*, min_ev: float, score_val: float, regime_val: str) -> tuple[dict[str, Any] | None, bool]:
        ev_probe_local: dict[str, Any] | None = None
        ev_ok_local = False
        if contract_probe > 0 and atr_value_probe > 0:
            ev_probe_local = expected_value_v4(
                score=score_val,
                regime=regime_val or "trend",
                atr_value=float(atr_value_probe),
                price=float(price),
                contract_size=float(contract_probe),
                size=1,
                maker_fee_rate=maker_probe,
                taker_fee_rate=taker_probe,
                slippage_pct=slip_probe,
                funding_pct=float(ev_cfg_probe.get("funding_pct", 0.0) or 0.0),
                min_ev_usd=min_ev,
            )
            ev_ok_local = bool(ev_probe_local.get("pass")) and float(ev_probe_local.get("ev_usd") or 0.0) >= min_ev
        return ev_probe_local, ev_ok_local

    short_bias_cfg = (
        (v4_cfg.get("short_bias_distance_override") or {})
        if isinstance(v4_cfg.get("short_bias_distance_override"), dict)
        else {}
    )
    short_bias_atr_cfg = (
        (v4_cfg.get("short_bias_atr_override") or {})
        if isinstance(v4_cfg.get("short_bias_atr_override"), dict)
        else {}
    )
    distance_override_applied = False
    distance_override_meta: dict[str, Any] | None = None
    atr_override_applied = False
    atr_override_meta: dict[str, Any] | None = None
    score_override_applied = False
    score_override_meta: dict[str, Any] | None = None
    if _bool_cfg(short_bias_cfg.get("enabled"), False) and entry and direction and selected_v4 and product_id:
        failed_gates = [k for k, v in gates_effective.items() if not bool(v)]
        only_distance_fail = set(failed_gates) == {"distance_from_value"}
        if only_distance_fail:
            required_dir = str(short_bias_cfg.get("require_direction", "short") or "short").strip().lower()
            min_score = float(short_bias_cfg.get("min_score", 90) or 90)
            regime_req = str(short_bias_cfg.get("require_regime", "trend") or "trend").strip().lower()
            atr_expanding_ok = bool(regime_v4.get("atr_expanding"))
            min_ev_usd = float(short_bias_cfg.get("min_ev_usd", ev_cfg_probe.get("min_ev_usd", 0.0)) or 0.0)
            ev_probe, ev_ok = _ev_probe_for_override(
                min_ev=min_ev_usd,
                score_val=selected_score_now,
                regime_val=selected_regime_now,
            )

            distance_override_applied = bool(
                _direction_allowed(required_dir, selected_direction_now)
                and bool(gates_effective.get("atr_regime"))
                and selected_regime_now == regime_req
                and selected_score_now >= min_score
                and atr_expanding_ok
                and ev_ok
            )
            distance_override_meta = {
                "enabled": True,
                "required_direction": required_dir,
                "direction": direction,
                "required_regime": regime_req,
                "regime": selected_regime_now,
                "score": selected_score_now,
                "min_score": min_score,
                "atr_expanding": atr_expanding_ok,
                "failed_gates": failed_gates,
                "ev_probe": ev_probe,
                "min_ev_usd": min_ev_usd,
                "applied": distance_override_applied,
            }
            if distance_override_applied:
                gates_effective["distance_from_value"] = True
                gates_pass_effective = all(bool(v) for v in gates_effective.values())
                log_decision(
                    config,
                    {
                        "timestamp": now.isoformat(),
                        "reason": "distance_gate_override_applied",
                        "product_id": product_id,
                        "direction": direction,
                        "override": distance_override_meta,
                    },
                )
    if _bool_cfg(short_bias_atr_cfg.get("enabled"), False) and entry and direction and selected_v4 and product_id:
        failed_gates = [k for k, v in gates_effective.items() if not bool(v)]
        only_atr_fail = set(failed_gates) == {"atr_regime"}
        required_dir = str(short_bias_atr_cfg.get("require_direction", "short") or "short").strip().lower()
        regime_req = str(short_bias_atr_cfg.get("require_regime", "trend") or "trend").strip().lower()
        min_score = float(short_bias_atr_cfg.get("min_score", 80) or 80)
        min_adx = float(short_bias_atr_cfg.get("min_adx_15m", 30.0) or 30.0)
        adx_now = float(_to_float(regime_v4.get("adx_15m"), 0.0) or 0.0)
        require_atr_exp = _bool_cfg(short_bias_atr_cfg.get("require_atr_expanding"), True)
        require_bb_exp = _bool_cfg(short_bias_atr_cfg.get("require_bb_expanding"), True)
        atr_expanding_ok = bool(regime_v4.get("atr_expanding")) if require_atr_exp else True
        bb_expanding_ok = bool(regime_v4.get("bb_expanding")) if require_bb_exp else True
        required_entry_type = str(short_bias_atr_cfg.get("require_entry_type", "pullback") or "pullback").strip().lower()
        entry_type_ok = (not required_entry_type) or (selected_entry_type == required_entry_type)
        min_ev_usd = float(short_bias_atr_cfg.get("min_ev_usd", ev_cfg_probe.get("min_ev_usd", 0.0)) or 0.0)
        ev_probe, ev_ok = _ev_probe_for_override(
            min_ev=min_ev_usd,
            score_val=selected_score_now,
            regime_val=selected_regime_now,
        )
        atr_override_applied = bool(
            only_atr_fail
            and _direction_allowed(required_dir, selected_direction_now)
            and selected_regime_now == regime_req
            and selected_score_now >= min_score
            and adx_now >= min_adx
            and atr_expanding_ok
            and bb_expanding_ok
            and entry_type_ok
            and ev_ok
        )
        atr_override_meta = {
            "enabled": True,
            "failed_gates": failed_gates,
            "required_direction": required_dir,
            "direction": selected_direction_now,
            "required_regime": regime_req,
            "regime": selected_regime_now,
            "score": selected_score_now,
            "min_score": min_score,
            "adx_15m": adx_now,
            "min_adx_15m": min_adx,
            "atr_expanding_ok": atr_expanding_ok,
            "bb_expanding_ok": bb_expanding_ok,
            "entry_type": selected_entry_type,
            "required_entry_type": required_entry_type,
            "ev_probe": ev_probe,
            "min_ev_usd": min_ev_usd,
            "applied": atr_override_applied,
        }
        if atr_override_applied:
            gates_effective["atr_regime"] = True
            gates_pass_effective = all(bool(v) for v in gates_effective.values())
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "atr_gate_override_applied",
                    "product_id": product_id,
                    "direction": direction,
                    "override": atr_override_meta,
                },
            )
            if score_gate_strict and not score_gate_pass_effective and _bool_cfg(short_bias_atr_cfg.get("allow_score_override"), True):
                trend_flags = (selected_v4.get("trend_flags") or {}) if isinstance(selected_v4, dict) else {}
                failed_flags = [k for k, v in trend_flags.items() if not bool(v)]
                only_ema_fail = set(failed_flags) == {"EMA_ALIGN_SLOPE"}
                allow_only_ema_fail = _bool_cfg(short_bias_atr_cfg.get("score_override_only_ema_bias_fail"), True)
                min_score_for_score_override = float(short_bias_atr_cfg.get("score_override_min_score", min_score) or min_score)
                score_override_applied = bool(
                    selected_score_now >= min_score_for_score_override
                    and ((only_ema_fail and allow_only_ema_fail) or (not allow_only_ema_fail))
                )
                score_override_meta = {
                    "enabled": True,
                    "failed_flags": failed_flags,
                    "only_ema_fail": only_ema_fail,
                    "allow_only_ema_bias_fail": allow_only_ema_fail,
                    "score": selected_score_now,
                    "min_score": min_score_for_score_override,
                    "applied": score_override_applied,
                }
                if score_override_applied:
                    score_gate_pass_effective = True
                    log_decision(
                        config,
                        {
                            "timestamp": now.isoformat(),
                            "reason": "v4_score_override_applied",
                            "product_id": product_id,
                            "direction": direction,
                            "override": score_override_meta,
                        },
                    )
    # --- Next Play predictions ---
    _next_long = None
    _next_short = None
    try:
        _np_atr = atr_value_probe if atr_value_probe > 0 else 0
        _np_vwap = float((selected_v4 or {}).get("vwap_price") or 0)
        _np_chan = (selected_v4 or {}).get("channel_detail")
        if _np_atr > 0:
            _next_long = _compute_next_play(
                price=price, direction="long", levels=levels, fibs=fibs,
                channel_detail=_np_chan, vwap_price=_np_vwap, atr_15m=_np_atr,
                v4_score=int((long_v4 or {}).get("score") or 0),
                v4_threshold=int((long_v4 or {}).get("threshold") or 75),
            )
            _next_short = _compute_next_play(
                price=price, direction="short", levels=levels, fibs=fibs,
                channel_detail=_np_chan, vwap_price=_np_vwap, atr_15m=_np_atr,
                v4_score=int((short_v4 or {}).get("score") or 0),
                v4_threshold=int((short_v4 or {}).get("threshold") or 75),
            )
    except Exception:
        pass
    _htf_watch_selected = long_htf_breakout_watch if direction == "long" else short_htf_breakout_watch if direction == "short" else (
        long_htf_breakout_watch if float(long_htf_breakout_watch.get("pressure_score") or 0) >= float(short_htf_breakout_watch.get("pressure_score") or 0) else short_htf_breakout_watch
    )

    _stage_equity_basis = max(
        float(equity_start or 0.0),
        float((_recon_result.snapshot.spot_usdc) if _recon_result else float((state.get("last_spot_cash_map") or {}).get("USDC") or 0.0)),
        float((_recon_result.snapshot.derivatives_usdc) if _recon_result else float(((mp_decision.metrics or {}) if mp_decision else {}).get("cfm_usd_balance") or 0.0)),
    )
    _two_contract_ready = _compute_contract_readiness(
        api,
        product_id=str(product_id or ""),
        direction=str(direction or "long"),
        config=config,
        state=state,
        transfers_today=transfers_today,
        target_size=2,
        stage_equity=_stage_equity_basis,
    )
    _contract_ladder = _compute_contract_ladder(
        api,
        product_id=str(product_id or ""),
        direction=str(direction or "long"),
        config=config,
        state=state,
        transfers_today=transfers_today,
        stage_equity=_stage_equity_basis,
    )
    _friday_break_risk = _compute_friday_break_risk(config=config, now_utc=now)
    _margin_window_playbook = _resolve_margin_window_playbook(
        config=config,
        mp_decision=mp_decision,
        overnight_trading_ok=overnight_trading_ok,
        quality_tier=quality_tier,
        two_contract_ready=_two_contract_ready,
        friday_break=_friday_break_risk,
        now_utc=now,
    )

    decision = {
        "timestamp": now.isoformat(),
        "session_id": session_id,
        "price": price,
        "gates": gates_effective,
        "gates_pass": gates_pass_effective,
        "route_tier": route_tier,
        "signal_product_id": signal_product_id,
        "spot_reference_product_id": data_product_id,
        "signal_uses_contract": bool(signal_product_id == (product_id or execution_product_id)),
        "distance_gate_override_applied": distance_override_applied,
        "distance_gate_override": distance_override_meta,
        "atr_gate_override_applied": atr_override_applied,
        "atr_gate_override": atr_override_meta,
        "product_available": product_available,
        "product_selected": product_id,
        "product_select_reason": selection.get("reason") if selection else None,
        "breakout_tf": breakout_tf,
        "breakout_type": breakout_type,
        "spread_pct": spread_estimate,
        "spread_limit_pct": spread_limit,
        "high_vol_pause": high_vol_pause,
        "fail_safe": fail_safe,
        "entry_signal": entry["type"] if entry else None,
        "direction": direction,
        "confluence_count": confluence_count(entry["confluence"]) if entry else 0,
        "confluences": entry["confluence"] if entry else None,
        "v4_regime": regime_v4.get("regime"),
        "v4_adx_15m": regime_v4.get("adx_15m"),
        "v4_atr_expanding": regime_v4.get("atr_expanding"),
        "v4_bb_expanding": regime_v4.get("bb_expanding"),
        "bb_expanding_1h": regime_v4.get("bb_expanding_1h"),
        "bb_expanding_4h": regime_v4.get("bb_expanding_4h"),
        "bb_tf_count": regime_v4.get("bb_tf_count"),
        "rvol_15m": regime_v4.get("rvol_15m"),
        "rvol_1h": regime_v4.get("rvol_1h"),
        "rvol_4h": regime_v4.get("rvol_4h"),
        "v4_atr_shock": regime_v4.get("atr_shock"),
        "v4_extreme_candle": regime_v4.get("extreme_candle"),
        "v4_score_long": (long_v4 or {}).get("score"),
        "v4_score_short": (short_v4 or {}).get("score"),
        "v4_selected_score": (selected_v4 or {}).get("score"),
        "v4_selected_threshold": (selected_v4 or {}).get("threshold"),
        "v4_selected_regime": (selected_v4 or {}).get("regime"),
        "v4_selected_mr_flags": (selected_v4 or {}).get("mr_flags"),
        "v4_selected_trend_flags": (selected_v4 or {}).get("trend_flags"),
        "v4_long_mr_flags": (long_v4 or {}).get("mr_flags"),
        "v4_long_trend_flags": (long_v4 or {}).get("trend_flags"),
        "v4_short_mr_flags": (short_v4 or {}).get("mr_flags"),
        "v4_short_trend_flags": (short_v4 or {}).get("trend_flags"),
        "vwap_price": (selected_v4 or {}).get("vwap_price"),
        "vwap_side": (selected_v4 or {}).get("vwap_side"),
        "fvg_detail": (selected_v4 or {}).get("fvg_detail"),
        "channel_detail": (selected_v4 or {}).get("channel_detail"),
        "v4_score_pass": score_gate_pass,
        "v4_score_pass_effective": score_gate_pass_effective,
        "v4_score_override_applied": score_override_applied,
        "v4_score_override": score_override_meta,
        "quality_tier": quality_tier,
        "adaptive_threshold": adaptive_threshold,
        "adaptive_reason": adaptive_reason,
        "vol_phase": expansion_state.get("phase"),
        "vol_direction": expansion_state.get("direction"),
        "vol_confidence": expansion_state.get("confidence"),
        "vol_reasons": expansion_state.get("reasons"),
        "vol_metrics": expansion_state.get("metrics"),
        "regime_name": regime_overrides.regime_name,
        "regime_size_mult": regime_overrides.size_multiplier,
        "regime_max_sl_pct": regime_overrides.max_sl_pct,
        "regime_tp_atr_mult": regime_overrides.tp_atr_mult,
        "regime_reasons": regime_overrides.reasons,
        "tier_min_rr": (lambda rrc: float(rrc.get(quality_tier, rrc.get("default", 1.5)) or 1.5) if isinstance(rrc, dict) else float(rrc or 1.5))(config.get("risk", {}).get("min_rr_ratio", 1.5)),
        "htf_zone_nearest": _zone_nearest_summary(zone_context),
        "htf_zone_inside": zone_context.get("inside_any_zone", False),
        "htf_readiness": zone_context.get("readiness_label"),
        "htf_readiness_reasons": zone_context.get("readiness_reasons"),
        "htf_macro_bias": zone_context.get("macro_bias", "neutral"),
        "htf_micro_flags": zone_context.get("micro_flags", {}),
        "htf_trend_bias": _htf_bias.get("bias", "neutral") if _htf_bias else "neutral",
        "htf_trend_rsi_1h": _htf_bias.get("rsi_1h") if _htf_bias else None,
        "htf_trend_slope_pct": _htf_bias.get("ema21_slope_pct") if _htf_bias else None,
        "zone_bonus": zone_mod.bonus if zone_mod else 0,
        "zone_bonus_reasons": zone_mod.reasons if zone_mod else [],
        "wick_zone_near": _wz_prox.get("near_zone", False),
        "wick_zone_confidence": _wz_prox.get("confidence", 0),
        "wick_zone_bias": _wz_prox.get("bounce_bias", "none"),
        "wick_zone_strongest_tf": _wz_prox.get("zone_strongest_tf"),
        "pattern_mod": _pattern_mod,
        "patterns_active": [{"pattern": p.pattern, "bias": p.direction_bias, "confidence": p.confidence, "level": p.zone_level, "desc": p.description} for p in _active_patterns[:3]] if _active_patterns else None,
        "alignment_bonus": alignment_mod.bonus if alignment_mod else 0,
        "alignment_reasons": alignment_mod.reasons if alignment_mod else [],
        "cooldown": cooldown,
        "overnight_trading_ok": overnight_trading_ok,
        "margin_window": (mp_decision.metrics or {}).get("margin_window") if mp_decision else None,
        "reconcile_status": state.get("_last_reconcile_status"),
        "safe_mode": bool(state.get("_safe_mode")),
        "spot_usdc": float((_recon_result.snapshot.spot_usdc) if _recon_result else float((state.get("last_spot_cash_map") or {}).get("USDC") or 0)),
        "spot_usd": float((_recon_result.snapshot.spot_usd) if _recon_result else float((state.get("last_spot_cash_map") or {}).get("USD") or 0)),
        "derivatives_usdc": float((_recon_result.snapshot.derivatives_usdc) if _recon_result else float(((mp_decision.metrics or {}) if mp_decision else {}).get("cfm_usd_balance") or 0)),
        "cfm_usd_balance": float(((mp_decision.metrics or {}) if mp_decision else {}).get("cfm_usd_balance") or 0),
        "drift_count_today": int(state.get("_reconcile_drift_count_today") or 0),
        "consecutive_losses": consecutive_losses,
        "wait_since_last_exit_min": wait_since_last_exit_min,
        "wait_since_last_entry_min": wait_since_last_entry_min,
        "last_entry_time": state.get("last_entry_time"),
        "last_exit_time": state.get("last_exit_time"),
        "trades_today": state.get("trades", 0),
        "max_trades_per_day": int(config["risk"]["max_trades_per_day"]),
        "losses_today": state.get("losses", 0),
        "max_losses_per_day": int(config["risk"]["max_losses_per_day"]),
        "pnl_today_usd": pnl_today,
        "exchange_pnl_today_usd": float(state.get("exchange_pnl_today_usd") or 0),
        "exchange_equity_usd": float(state.get("exchange_equity_usd") or 0),
        "transfers_today_usd": transfers_today,
        "conversion_cost_today_usd": conversion_cost_today,
        "equity_start_usd": equity_start,
        "last_spot_cash_map": state.get("last_spot_cash_map") or {},
        "loss_debt_usd": float(state.get("loss_debt_usd") or 0.0),
        "recovery_mode": recovery_info.get("mode", "NORMAL"),
        "recovery_active": recovery_info.get("active", False),
        "recovery_debt": recovery_info.get("recovery_debt", 0),
        "recovery_goal": recovery_info.get("recovery_goal", 0),
        "recovery_attempts": recovery_info.get("recovery_attempts", 0),
        "recovery_preferred_side": recovery_info.get("preferred_side", ""),
        "post_tp_bias": post_tp_bias,
        "reconcile_incidents": rec_incidents_count,
        "mr_intraday": ((mp_decision.metrics or {}) if mp_decision else {}).get("mr_intraday"),
        "mr_overnight": ((mp_decision.metrics or {}) if mp_decision else {}).get("mr_overnight"),
        "active_mr": ((mp_decision.metrics or {}) if mp_decision else {}).get("active_mr"),
        "maintenance_margin_requirement": ((mp_decision.metrics or {}) if mp_decision else {}).get("maintenance_margin_requirement"),
        "total_funds_for_margin": ((mp_decision.metrics or {}) if mp_decision else {}).get("total_funds_for_margin"),
        "two_contract_ready": _two_contract_ready.get("ready"),
        "two_contract_ready_reason": _two_contract_ready.get("reason"),
        "two_contract_required_margin": _two_contract_ready.get("required_margin"),
        "two_contract_required_with_buffer": _two_contract_ready.get("required_with_buffer"),
        "two_contract_buying_power": _two_contract_ready.get("buying_power"),
        "two_contract_headroom": _two_contract_ready.get("headroom"),
        "two_contract_buffer_pct": _two_contract_ready.get("buffer_pct"),
        "two_contract_stage_label": _two_contract_ready.get("growth_stage_label"),
        "two_contract_stage_max_contracts": _two_contract_ready.get("growth_stage_max_contracts"),
        "contract_ladder": _contract_ladder,
        "margin_playbook_label": _margin_window_playbook.get("label"),
        "margin_playbook_objective": _margin_window_playbook.get("objective"),
        "margin_playbook_block_new_entries": _margin_window_playbook.get("block_new_entries"),
        "margin_playbook_allow_multi_contract": _margin_window_playbook.get("allow_multi_contract"),
        "margin_playbook_max_new_contracts": _margin_window_playbook.get("max_new_contracts"),
        "margin_playbook_force_exit_before_cutoff": _margin_window_playbook.get("force_exit_before_cutoff"),
        "margin_playbook_force_flat_now": _margin_window_playbook.get("force_flat_now"),
        "margin_playbook_mins_to_cutoff": _margin_window_playbook.get("mins_to_cutoff"),
        "margin_playbook_notes": _margin_window_playbook.get("notes"),
        "friday_break_label": _friday_break_risk.get("label"),
        "friday_break_active": _friday_break_risk.get("active"),
        "friday_break_pre_break_lock": _friday_break_risk.get("pre_break_lock"),
        "friday_break_force_flat_now": _friday_break_risk.get("force_flat_now"),
        "friday_break_reopen_cooldown_active": _friday_break_risk.get("reopen_cooldown_active"),
        "friday_break_minutes_to_break": _friday_break_risk.get("minutes_to_break"),
        "friday_break_minutes_to_reopen": _friday_break_risk.get("minutes_to_reopen"),
        "friday_break_notes": _friday_break_risk.get("notes"),
        "contract_basis_bps": contract_ctx.get("basis_bps"),
        "contract_oi_trend": contract_ctx.get("oi_trend"),
        "contract_funding_bias": contract_ctx.get("funding_bias"),
        "contract_oi_price_rel": contract_ctx.get("oi_price_rel"),
        "contract_oi_delta_15m": contract_ctx.get("oi_delta_15m"),
        "contract_mark_price": contract_ctx.get("mark_price"),
        "contract_index_price": contract_ctx.get("index_price"),
        "contract_price_change_24h_pct": contract_ctx.get("price_change_24h_pct"),
        "contract_high_24h": contract_ctx.get("high_24h"),
        "contract_low_24h": contract_ctx.get("low_24h"),
        "contract_mod_bonus": contract_mod.bonus if contract_mod else 0,
        "contract_mod_reasons": contract_mod.reasons if contract_mod else [],
        "orderbook_depth_bias": orderbook_ctx.get("depth_bias"),
        "orderbook_imbalance": orderbook_ctx.get("imbalance_ratio"),
        "orderbook_spread_bps": orderbook_ctx.get("spread_bps"),
        "orderbook_mid_price": orderbook_ctx.get("mid_price"),
        "orderbook_mid_move_bps": orderbook_ctx.get("mid_move_bps"),
        "orderbook_bid_replenishment": orderbook_ctx.get("bid_replenishment_ratio"),
        "orderbook_ask_replenishment": orderbook_ctx.get("ask_replenishment_ratio"),
        "orderbook_absorption_bias": orderbook_ctx.get("absorption_bias"),
        "orderbook_spoof_risk": orderbook_ctx.get("spoof_risk"),
        "orderbook_spoof_side": orderbook_ctx.get("spoof_side"),
        "orderbook_depth_flip": orderbook_ctx.get("depth_flip"),
        "orderbook_levels_sampled": orderbook_ctx.get("levels_sampled"),
        "orderbook_history_samples": orderbook_ctx.get("history_samples"),
        "orderbook_history_bias": orderbook_ctx.get("history_bias"),
        "orderbook_history_avg_imbalance": orderbook_ctx.get("history_avg_imbalance"),
        "orderbook_history_absorption_rate": orderbook_ctx.get("history_absorption_rate"),
        "orderbook_history_spoof_rate": orderbook_ctx.get("history_spoof_rate"),
        "orderbook_history_depth_flips": orderbook_ctx.get("history_depth_flips"),
        "orderbook_history_mid_move_bps_avg": orderbook_ctx.get("history_mid_move_bps_avg"),
        "orderbook_mod_bonus": orderbook_mod.bonus if orderbook_mod else 0,
        "orderbook_mod_reasons": orderbook_mod.reasons if orderbook_mod else [],
        "liquidation_signal_source": "binance_force_orders" if liquidation_ctx.get("feed_live") else "exchange_inference_price_oi",
        "liquidation_feed_live": bool(liquidation_ctx.get("feed_live")),
        "liquidation_bias": liquidation_ctx.get("bias"),
        "liquidation_events_5m": ((liquidation_ctx.get("window_5m") or {}).get("events")),
        "liquidation_notional_5m_usd": ((liquidation_ctx.get("window_5m") or {}).get("notional_usd")),
        "liquidation_intelligence": liquidation_prompt,
        "lane_v_mode": (entry or {}).get("mode"),
        "lane_v_cluster_side": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("cluster_side"),
        "lane_v_cluster_strength": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("cluster_strength"),
        "lane_v_distance_to_cluster_atr": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("distance_to_cluster_atr"),
        "lane_v_magnet_score": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("magnet_score"),
        "lane_v_sweep_status": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("sweep_status"),
        "lane_v_sweep_side": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("sweep_side"),
        "lane_v_wick_score": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("wick_score"),
        "lane_v_wick_ratio": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("wick_ratio"),
        "lane_v_reclaim_confirmed": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("reclaim_confirmed"),
        "lane_v_rejection_confirmed": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("rejection_confirmed"),
        "lane_v_followthrough_confirmed": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("followthrough_confirmed"),
        "lane_v_fib_hit": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("fib_hit"),
        "lane_v_ema_stretch": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("ema_stretch"),
        "lane_v_vwap_stretch": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("vwap_stretch"),
        "lane_v_continuation_ok": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("continuation_ok"),
        "lane_v_reversal_ok": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("reversal_ok"),
        "lane_v_no_trade_reason": ((long_liquidation_intel if direction == "long" else short_liquidation_intel) or {}).get("no_trade_reason"),
        "liquidation_mod_bonus": liquidation_mod.bonus if liquidation_mod else 0,
        "liquidation_mod_reasons": liquidation_mod.reasons if liquidation_mod else [],
        "ev_estimated_fees_usd": (ev_snapshot or {}).get("fees_usd") if isinstance(ev_snapshot, dict) else None,
        "ev_estimated_slippage_usd": (ev_snapshot or {}).get("slippage_usd") if isinstance(ev_snapshot, dict) else None,
        "ev_estimated_funding_usd": (ev_snapshot or {}).get("funding_usd") if isinstance(ev_snapshot, dict) else None,
        "ev_estimated_net_usd": (ev_snapshot or {}).get("ev_usd") if isinstance(ev_snapshot, dict) else None,
        "ev_notional_usd": (ev_snapshot or {}).get("notional_usd") if isinstance(ev_snapshot, dict) else None,
        "expectancy_size_mult": round(float(_re_size_mult or 1.0), 3),
        "expectancy_gate_reason": _re_result.get("reason"),
        "expectancy_gate_action": _re_result.get("action"),
        "expectancy_allowed": _re_result.get("allowed"),
        "expectancy_avg_pnl_usd": _re_data.get("avg_pnl_usd"),
        "expectancy_profit_factor": _re_data.get("profit_factor"),
        "expectancy_win_rate": _re_data.get("win_rate"),
        "kelly_size_mult": round(float(_kelly_mult or 1.0), 3),
        "kelly_reason": _kelly_reason,
        "futures_relativity_bias": (((futures_relativity or {}).get("composite") or {}).get("bias")),
        "futures_relativity_confidence": (((futures_relativity or {}).get("composite") or {}).get("confidence")),
        "cross_venue_oi_change_pct": (((futures_relativity or {}).get("composite") or {}).get("oi_change_pct_avg")),
        "cross_venue_funding_bias": (((futures_relativity or {}).get("composite") or {}).get("funding_bias")),
        "futures_relativity_mod_bonus": futures_relativity_mod.bonus if futures_relativity_mod else 0,
        "futures_relativity_mod_reasons": futures_relativity_mod.reasons if futures_relativity_mod else [],
        "weekly_research_window": (weekly_research or {}).get("window_label") if isinstance(weekly_research, dict) else None,
        "weekly_research_macro_regime": (weekly_research or {}).get("macro_regime") if isinstance(weekly_research, dict) else None,
        "weekly_research_bias": (weekly_research or {}).get("directional_bias") if isinstance(weekly_research, dict) else None,
        "weekly_research_xlm_bias": (weekly_research or {}).get("xlm_bias") if isinstance(weekly_research, dict) else None,
        "weekly_research_confidence": (weekly_research or {}).get("confidence") if isinstance(weekly_research, dict) else None,
        "weekly_research_generated_from": (weekly_research or {}).get("generated_from") if isinstance(weekly_research, dict) else None,
        "weekly_research_updated_at": (weekly_research or {}).get("updated_at") if isinstance(weekly_research, dict) else None,
        "weekly_research_mod_bonus": weekly_research_bonus,
        "weekly_research_mod_reasons": weekly_research_reasons,
        "research_intraday_review_score": (market_intel_state.get("intraday") or {}).get("review_score") if isinstance(market_intel_state.get("intraday"), dict) else None,
        "research_weekly_review_score": (market_intel_state.get("weekly") or {}).get("review_score") if isinstance(market_intel_state.get("weekly"), dict) else None,
        "research_source_diversity": _source_scoreboard.get("source_diversity"),
        "research_source_avg_quality": _source_scoreboard.get("avg_quality"),
        "research_source_leader": (_source_scoreboard.get("leader") or {}).get("source_name") if isinstance(_source_scoreboard.get("leader"), dict) else None,
        "research_source_leader_score": (_source_scoreboard.get("leader") or {}).get("weighted_score") if isinstance(_source_scoreboard.get("leader"), dict) else None,
        "research_next_event_label": _next_event.get("label"),
        "research_next_event_category": _next_event.get("category"),
        "research_next_event_importance": _next_event.get("importance"),
        "research_next_event_hours": _next_event.get("hours_to_event"),
        "research_high_risk_event_count": _event_calendar.get("high_risk_count"),
        "research_event_count": _event_calendar.get("event_count"),
        "weekly_playbook_label": _weekly_playbook.get("label"),
        "weekly_playbook_monday_ready": _weekly_playbook.get("monday_ready"),
        "weekly_playbook_thesis": _weekly_playbook.get("thesis"),
        "weekly_playbook_top_setups": _weekly_playbook.get("top_setups"),
        "weekly_playbook_risk_map": _weekly_playbook.get("risk_map"),
        "htf_breakout_long_ready": long_htf_breakout_watch.get("ready"),
        "htf_breakout_short_ready": short_htf_breakout_watch.get("ready"),
        "htf_breakout_long_reason": long_htf_breakout_watch.get("reason"),
        "htf_breakout_short_reason": short_htf_breakout_watch.get("reason"),
        "htf_breakout_long_pressure_score": long_htf_breakout_watch.get("pressure_score"),
        "htf_breakout_short_pressure_score": short_htf_breakout_watch.get("pressure_score"),
        "htf_breakout_long_followthrough_score": long_htf_breakout_watch.get("followthrough_score"),
        "htf_breakout_short_followthrough_score": short_htf_breakout_watch.get("followthrough_score"),
        "htf_breakout_long_confidence": long_htf_breakout_watch.get("confidence"),
        "htf_breakout_short_confidence": short_htf_breakout_watch.get("confidence"),
        "htf_breakout_long_hold_score": long_htf_breakout_watch.get("hold_score"),
        "htf_breakout_short_hold_score": short_htf_breakout_watch.get("hold_score"),
        "htf_breakout_long_false_break_risk": long_htf_breakout_watch.get("false_break_risk"),
        "htf_breakout_short_false_break_risk": short_htf_breakout_watch.get("false_break_risk"),
        "htf_breakout_long_management_bias": long_htf_breakout_watch.get("management_bias"),
        "htf_breakout_short_management_bias": short_htf_breakout_watch.get("management_bias"),
        "htf_breakout_long_breakout_level": long_htf_breakout_watch.get("breakout_level"),
        "htf_breakout_short_breakout_level": short_htf_breakout_watch.get("breakout_level"),
        "htf_breakout_long_invalidation": long_htf_breakout_watch.get("invalidation_price"),
        "htf_breakout_short_invalidation": short_htf_breakout_watch.get("invalidation_price"),
        "htf_breakout_long_chase_atr": long_htf_breakout_watch.get("chase_atr"),
        "htf_breakout_short_chase_atr": short_htf_breakout_watch.get("chase_atr"),
        "htf_breakout_long_weekly_alignment": long_htf_breakout_watch.get("weekly_alignment"),
        "htf_breakout_short_weekly_alignment": short_htf_breakout_watch.get("weekly_alignment"),
        "htf_breakout_long_event_blocked": long_htf_breakout_watch.get("event_risk_blocked"),
        "htf_breakout_short_event_blocked": short_htf_breakout_watch.get("event_risk_blocked"),
        "htf_breakout_long_event_label": long_htf_breakout_watch.get("event_risk_label"),
        "htf_breakout_short_event_label": short_htf_breakout_watch.get("event_risk_label"),
        "htf_breakout_long_event_hours": long_htf_breakout_watch.get("event_risk_hours"),
        "htf_breakout_short_event_hours": short_htf_breakout_watch.get("event_risk_hours"),
        "htf_breakout_selected_direction": _htf_watch_selected.get("direction"),
        "htf_breakout_selected_ready": _htf_watch_selected.get("ready"),
        "htf_breakout_selected_reason": _htf_watch_selected.get("reason"),
        "htf_breakout_selected_pressure_score": _htf_watch_selected.get("pressure_score"),
        "htf_breakout_selected_followthrough_score": _htf_watch_selected.get("followthrough_score"),
        "htf_breakout_selected_confidence": _htf_watch_selected.get("confidence"),
        "htf_breakout_selected_hold_score": _htf_watch_selected.get("hold_score"),
        "htf_breakout_selected_false_break_risk": _htf_watch_selected.get("false_break_risk"),
        "htf_breakout_selected_management_bias": _htf_watch_selected.get("management_bias"),
        "htf_breakout_selected_breakout_level": _htf_watch_selected.get("breakout_level"),
        "htf_breakout_selected_invalidation": _htf_watch_selected.get("invalidation_price"),
        "htf_breakout_selected_chase_atr": _htf_watch_selected.get("chase_atr"),
        "htf_breakout_selected_event_blocked": _htf_watch_selected.get("event_risk_blocked"),
        "htf_breakout_selected_event_label": _htf_watch_selected.get("event_risk_label"),
        "htf_breakout_selected_event_hours": _htf_watch_selected.get("event_risk_hours"),
        "htf_breakout_selected_reasons": _htf_watch_selected.get("reasons"),
        "lane_specific_expectancy_mode": sizing_meta.get("lane_expectancy_mode") if isinstance(sizing_meta, dict) else None,
        "lane_specific_expectancy_win_rate": sizing_meta.get("lane_expectancy_win_rate") if isinstance(sizing_meta, dict) else None,
        "lane_specific_expectancy_avg_pnl_usd": sizing_meta.get("lane_expectancy_avg_pnl_usd") if isinstance(sizing_meta, dict) else None,
        "lane_specific_expectancy_sharpe": sizing_meta.get("lane_expectancy_sharpe") if isinstance(sizing_meta, dict) else None,
        "crowding_regime": _crowding_summary.get("regime"),
        "crowding_bias": _crowding_summary.get("bias"),
        "crowding_funding_bias": _crowding_summary.get("funding_bias"),
        "crowding_oi_change_pct": _crowding_summary.get("oi_change_pct"),
        "crowding_liquidation_bias": _crowding_summary.get("liquidation_bias"),
        "btc_trend": btc_signal.btc_trend if btc_signal else None,
        "btc_momentum_pct": btc_signal.btc_momentum_pct if btc_signal else None,
        "btc_score_mod": btc_signal.score_modifier if btc_signal else 0,
        "btc_reasons": btc_signal.reasons if btc_signal else [],
        "candle_pattern": candle_pattern.reasons if candle_pattern and candle_pattern.has_pattern else [],
        "candle_pattern_bias": candle_pattern.direction_bias if candle_pattern else None,
        "candle_pattern_mod": candle_pattern.score_modifier if candle_pattern else 0,
        "cascade_event": asdict(cascade_event) if cascade_event else None,
        "lane": lane_result.lane if lane_result else None,
        "lane_label": lane_result.label if lane_result else None,
        "lane_threshold": lane_result.threshold if lane_result else None,
        "lane_reason": lane_result.reason if lane_result else None,
        "lane_atr_bypassed": lane_atr_bypassed,
        "lane_distance_bypassed": lane_distance_bypassed,
        "sweep_detected": bool(sweep_long or sweep_short),
        "sweep_long": sweep_long,
        "sweep_short": sweep_short,
        "micro_sweep_promoted": _micro_sweep_promoted,
        "micro_sweep_long": {"detected": micro_sweep_long.detected, "score": micro_sweep_long.score, "wick_ratio": micro_sweep_long.wick_ratio} if micro_sweep_long and micro_sweep_long.detected else None,
        "micro_sweep_short": {"detected": micro_sweep_short.detected, "score": micro_sweep_short.score, "wick_ratio": micro_sweep_short.wick_ratio} if micro_sweep_short and micro_sweep_short.detected else None,
        "wick_zones_count": len(_wick_zones),
        "wick_zones_top3": [{"level": z.level, "side": z.side, "strength": z.strength, "touches": z.touch_count, "strongest_tf": z.strongest_tf} for z in _wick_zones[:3]] if _wick_zones else None,
        "htf_trend": regime_v4.get("htf_trend", "neutral"),
        "adx_4h": regime_v4.get("adx_4h"),
        "adx_1d": regime_v4.get("adx_1d"),
        "htf_data_available": {"1d": not df_1d.empty if hasattr(df_1d, 'empty') else False, "1w": not df_1w.empty if hasattr(df_1w, 'empty') else False, "1mo": not df_1mo.empty if hasattr(df_1mo, 'empty') else False},
        "compression_range_target": (entry or {}).get("mid_range"),
        "sizing_meta": sizing_meta if sizing_meta else None,
        "consecutive_wins": int(state.get("consecutive_wins") or 0),
        "squeeze_detected": bool(squeeze_long or squeeze_short),
        "squeeze_long": squeeze_long,
        "squeeze_short": squeeze_short,
        "price_source": _price_source,
        "live_tick_age_sec": round(_live_age, 1) if _live_age >= 0 else None,
        "market_health_score": (_pulse or {}).get("health_score"),
        "market_regime": (_pulse or {}).get("regime"),
        "market_tick_health": (((_pulse or {}).get("components") or {}) if isinstance((_pulse or {}).get("components"), dict) else {}).get("tick_health"),
        "market_brief_age_min": (((_pulse or {}).get("components") or {}) if isinstance((_pulse or {}).get("components"), dict) else {}).get("brief_age_min"),
        "sentiment_stale": (((_pulse or {}).get("components") or {}) if isinstance((_pulse or {}).get("components"), dict) else {}).get("sentiment_stale"),
        # ── Per-direction diagnostic state ──
        "entry_type_long": (long_entry or {}).get("type"),
        "entry_type_short": (short_entry or {}).get("type"),
        "v4_threshold_long": (long_v4 or {}).get("threshold"),
        "v4_threshold_short": (short_v4 or {}).get("threshold"),
        "v4_pass_long": bool((long_v4 or {}).get("pass")) if long_v4 else False,
        "v4_pass_short": bool((short_v4 or {}).get("pass")) if short_v4 else False,
        "lane_long": lane_result_long.lane if lane_result_long else None,
        "lane_long_label": lane_result_long.label if lane_result_long else None,
        "lane_long_reason": lane_result_long.reason if lane_result_long else None,
        "lane_short": lane_result_short.lane if lane_result_short else None,
        "lane_short_label": lane_result_short.label if lane_result_short else None,
        "lane_short_reason": lane_result_short.reason if lane_result_short else None,
        "lane_weights_used": (selected_v4 or {}).get("lane_weights_used"),
        "candidate_long_pass": bool(long_entry and long_v4 and bool(long_v4.get("pass"))),
        "candidate_short_pass": bool(short_entry and short_v4 and bool(short_v4.get("pass"))),
        "long_block_reason": _build_block_reason(long_entry, long_v4, gates_pass_effective, cooldown, product_available, gates_effective),
        "short_block_reason": _build_block_reason(short_entry, short_v4, gates_pass_effective, cooldown, product_available, gates_effective),
        "v4_long_missing_pts": max(0, int((long_v4 or {}).get("threshold") or 75) - int((long_v4 or {}).get("score") or 0)) if long_v4 else None,
        "v4_short_missing_pts": max(0, int((short_v4 or {}).get("threshold") or 75) - int((short_v4 or {}).get("score") or 0)) if short_v4 else None,
        "long_unlock_hints": _compute_unlock_hints(long_v4),
        "short_unlock_hints": _compute_unlock_hints(short_v4),
        "next_play_long": _next_long,
        "next_play_short": _next_short,
        # AI advisor insights (from previous cycle's background call)
        "ai_insight": ai_advisor.get_cached_insight("entry_eval"),
        "ai_exit_advice": ai_advisor.get_cached_insight("exit_eval"),
        "ai_regime": ai_advisor.get_cached_insight("regime_eval"),
        "ai_loss_debrief": ai_advisor.get_loss_debrief(),
        # Codex peer advisor (advisory-only metadata; Opus remains authority)
        "codex_insight": ai_advisor.get_cached_insight("codex_entry_eval"),
        "codex_exit_advice": ai_advisor.get_cached_insight("codex_exit_eval"),
        "codex_regime": ai_advisor.get_cached_insight("codex_regime_eval"),
        # Gemini peer advisor (team member)
        "gemini_insight": gemini_advisor.get_cached_insight("gemini_entry_eval"),
        "gemini_exit_advice": gemini_advisor.get_cached_insight("gemini_exit_eval"),
        "gemini_regime": gemini_advisor.get_cached_insight("gemini_regime_eval"),
    }

    # AI executive directive: add to decision payload
    _ai_directive = ai_advisor.get_directive()
    decision["ai_directive"] = _ai_directive
    decision["codex_directive"] = ai_advisor.get_codex_directive()
    decision["gemini_directive"] = gemini_advisor.get_directive()

    log_decision(config, decision)

    # ── AI Executive Mode: fire master directive request ──────────────
    # Sends Claude the full picture (candles, indicators, position, trade history,
    # plus what the strategy engine recommends).  Result available NEXT cycle.
    if ai_advisor.is_executive_mode():
        _engine_rec = {
            "has_signal": bool(entry),
            "direction": direction,
            "entry_type": (entry or {}).get("type"),
            "score": (selected_v4 or {}).get("score"),
            "threshold": (selected_v4 or {}).get("threshold"),
            "regime": (selected_v4 or {}).get("regime"),
            "quality_tier": quality_tier,
            "lane": (lane_result.lane if lane_result else None),
        }
        _ai_status = {
            "has_open_position": bool(open_pos),
            "position_direction": (open_pos or {}).get("direction"),
            "position_entry_price": (open_pos or {}).get("entry_price"),
            "position_pnl_usd": float(state.get("_live_pnl_usd") or 0),
            "pnl_today_usd": pnl_today,
            "equity_usd": equity_start,
            "consecutive_losses": consecutive_losses,
            "consecutive_wins": int(state.get("consecutive_wins") or 0),
            "trades_today": state.get("trades", 0),
            "losses_today": state.get("losses", 0),
            "vol_phase": expansion_state.get("phase"),
            "recovery_mode": recovery_info.get("mode", "NORMAL"),
            "contract_context": contract_ctx,
            "market_structure": orderbook_ctx,
            "futures_relativity": futures_relativity,
            "liquidation_intelligence": liquidation_prompt,
            "live_price": _live_price if _live_price > 0 else None,
            "live_tick_age_sec": round(_live_age, 1) if _live_age >= 0 else None,
            "price_source": _price_source,
            "market_health_score": (_pulse or {}).get("health_score"),
            "market_regime": (_pulse or {}).get("regime"),
        }
        _market_brief = perplexity_advisor.get_latest_brief()
        _weekly_research = weekly_research or perplexity_advisor.get_latest_weekly_market_research(config=config)
        _peer_intel = {
            "gemini_entry_insight": gemini_advisor.get_cached_insight("gemini_entry_eval"),
            "gemini_regime_insight": gemini_advisor.get_cached_insight("gemini_regime_eval"),
            "codex_directive": ai_advisor.get_codex_directive(),
            "data_integrity_report": integrity_report,
        }
        _ai_directive_payload = {
            "status": _ai_status,
            "df_15m": df_15m,
            "df_1h": df_1h,
            "regime_v4": regime_v4,
            "expansion_state": expansion_state,
            "engine_recommendation": _engine_rec,
            "price": price,
            "macro_news": json.dumps(_market_brief) if _market_brief else None,
            "weekly_market_research": json.dumps(_weekly_research) if _weekly_research else None,
            "peer_intel": _peer_intel,
            "lane_perf_path": str(LOGS_DIR / "lane_performance.json"),
        }
        ai_advisor.request_directive(**_ai_directive_payload)
        gemini_advisor.request_directive(**_ai_directive_payload)

        # Gemini Risk Audit: If Claude has a directive, ask Gemini to audit it
        if _ai_directive:
            gemini_advisor.audit_decision(_ai_directive, _ai_status, price=price)

    # Apply Claude's lane adjustments (self-learning feedback)
    try:
        if _ai_directive and isinstance(_ai_directive.get("lane_adjustments"), dict):
            _lane_adj = _ai_directive["lane_adjustments"]
            _lane_perf_path = LOGS_DIR / "lane_performance.json"
            if _lane_perf_path.exists():
                import json as _json_mod
                _lp_data = _json_mod.loads(_lane_perf_path.read_text())
                _lp_lanes = _lp_data.setdefault("lanes", {})
                for _adj_lane, _adj_info in _lane_adj.items():
                    if not isinstance(_adj_info, dict):
                        continue
                    _action = _adj_info.get("action", "")
                    if _action == "disable":
                        _lp_lanes.setdefault(_adj_lane, {})["override"] = "ai_disabled"
                    elif _action == "raise_threshold":
                        _lp_lanes.setdefault(_adj_lane, {})["override"] = "ai_raise_threshold"
                    elif _action == "lower_threshold":
                        _lp_lanes.setdefault(_adj_lane, {})["override"] = "ai_lower_threshold"
                _lp_data["lanes"] = _lp_lanes
                _lane_perf_path.write_text(_json_mod.dumps(_lp_data, indent=2))
    except Exception:
        pass

    # ── AI Executive: advisory by default, override only when explicitly enabled ──
    _ai_exec_override = False
    _gemini_audit = gemini_advisor.get_audit_result()
    _ai_cfg = (config.get("ai") or {}) if isinstance(config.get("ai"), dict) else {}
    _ai_soft_override_enabled = bool(_ai_cfg.get("executive_full_control", False)) and bool(_ai_cfg.get("executive_allow_soft_risk_override", False))
    _ai_allow_gemini_takeover = bool(_ai_cfg.get("executive_allow_gemini_takeover", False))
    _ai_allow_no_signal_entries = bool(_ai_cfg.get("executive_allow_no_signal_entries", False))
    _ai_allow_size_override = bool(_ai_cfg.get("executive_allow_size_override", False))

    if (
        ai_advisor.is_executive_mode()
        and _ai_soft_override_enabled
        and _ai_directive
        and _ai_directive.get("action", "").startswith("ENTER")
        and float(_ai_directive.get("confidence", 0)) >= float(_ai_cfg.get("executive_min_confidence", 0.6))
    ):
        # Gemini Risk Check:
        if _gemini_audit and _gemini_audit.get("approved") is False:
             log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "gemini_risk_veto",
                    "claude_proposal": _ai_directive,
                    "gemini_audit": _gemini_audit,
                },
            )
             save_state(state)
             return
        
        _ai_exec_override = True

    # Gemini Failover: If Claude is unavailable (no directive), but Gemini has a strong opinion
    # AND integrity is OK
    if not _ai_exec_override and _ai_allow_gemini_takeover and ai_advisor.is_executive_mode() and not _ai_directive:
        _integrity_ok = not (integrity_report and integrity_report.get("status") == "BLOCK_TRADING")
        _gem_directive = gemini_advisor.get_directive()
        if (
            _gem_directive
            and _gem_directive.get("action", "").startswith("ENTER")
            and float(_gem_directive.get("confidence", 0)) >= 0.75
            and _integrity_ok
        ):
             log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "claude_unavailable_gemini_takeover",
                    "gemini_proposal": _gem_directive,
                },
            )
             # Use Gemini as the directive
             _ai_directive = _gem_directive
             _ai_exec_override = True

    # PRE-TRADE STATE SYNC: verify local state matches exchange (war room rec #3)
    # Prevents phantom positions where bot thinks it's flat but exchange has a position
    if entry and direction and not paper:
        try:
            _sync_positions = api.get_cfm_positions() or []
            _sync_has_exchange_pos = any(
                abs(float(p.get("number_of_contracts") or 0)) > 0
                for p in _sync_positions
                if str(p.get("product_id", "")).upper() == str(config.get("product_id", "")).upper()
            )
            _sync_has_local_pos = bool(state.get("open_position"))
            if _sync_has_exchange_pos and not _sync_has_local_pos:
                # Exchange has position but bot thinks it's flat = DANGEROUS
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "state_sync_mismatch_exchange_has_position",
                    "detail": "Exchange has open position but local state is flat. Blocking entry.",
                })
                _audit_logger.record_anomaly("STATE_SYNC_MISMATCH", {
                    "type": "exchange_has_position_local_flat",
                    "action": "blocked_entry",
                }, severity="CRITICAL")
                entry = None
                direction = None
            elif not _sync_has_exchange_pos and _sync_has_local_pos:
                # Bot thinks it has a position but exchange doesn't = stale state
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "state_sync_mismatch_local_stale",
                    "detail": "Local state has position but exchange is flat. Allowing entry.",
                })
                _audit_logger.record_anomaly("STATE_SYNC_MISMATCH", {
                    "type": "local_has_position_exchange_flat",
                    "action": "allowed_entry",
                }, severity="WARNING")
        except Exception:
            pass  # API failure shouldn't block entries

    # HARD risk gate check (not bypassable by AI executive)
    _pulse_components = (_pulse or {}).get("components") if isinstance((_pulse or {}).get("components"), dict) else {}
    _hard_block_reason = _evaluate_hard_risk_gates(
        config,
        state,
        pnl_today,
        equity_start,
        recovery_info,
        now,
        pulse=_pulse,
        live_tick_age_sec=(_live_age if _live_age >= 0 else _to_float(_pulse_components.get("tick_age_sec"), None)),
    )
    if _hard_block_reason:
        _pnl_for_daily_loss = float(state.get("exchange_pnl_today_usd") or 0.0)
        if _pnl_for_daily_loss == 0.0:
            _pnl_for_daily_loss = float(pnl_today or 0.0)
            
        log_payload = {
            "timestamp": now.isoformat(),
            "reason": _hard_block_reason,
            "pnl_today_usd": _pnl_for_daily_loss,
            "equity_start_usd": equity_start,
        }
        if _hard_block_reason == "entry_blocked_recovery_safe_mode":
            log_payload["recovery_mode"] = recovery_info.get("mode")
        else:
            log_payload.update({
                "pnl_today_state_usd": float(pnl_today or 0.0),
                "pnl_today_exchange_usd": float(state.get("exchange_pnl_today_usd") or 0.0),
                "max_daily_loss_pct": float(config.get("risk", {}).get("max_daily_loss_pct", 0.0) or 0.0),
            })
        if _pulse:
            log_payload.update(
                {
                    "pulse_regime": (_pulse or {}).get("regime"),
                    "pulse_health": (_pulse or {}).get("health_score"),
                    "tick_health": _pulse_components.get("tick_health"),
                    "tick_age_sec": _pulse_components.get("tick_age_sec"),
                    "brief_age_min": _pulse_components.get("brief_age_min"),
                    "sentiment_stale": _pulse_components.get("sentiment_stale"),
                }
            )
            
        log_decision(config, log_payload)
        save_state(state)
        # Post cycle intel to Slack (throttled, max 1 per 5 min)
        try:
            slack_intel.post_cycle_intel(log_payload, event="cycle")
        except Exception:
            pass
        return

    cooldown_loss_threshold = int(config.get("risk", {}).get("cooldown_loss_threshold", 3) or 3)
    if consecutive_losses >= cooldown_loss_threshold:
        _update_cooldown(state, now, int(config["risk"]["cooldown_minutes"]))
        cooldown = True

    runtime_guard_cfg = (v4_cfg.get("runtime_guard") or {}) if isinstance(v4_cfg.get("runtime_guard"), dict) else {}
    runtime_unstable = False
    recent_bot_errors = 0
    if bool(runtime_guard_cfg.get("enabled", True)):
        window_minutes = int(runtime_guard_cfg.get("window_minutes", 20) or 20)
        max_bot_errors = int(runtime_guard_cfg.get("max_bot_errors", 2) or 2)
        logging_cfg = (config.get("logging") or {}) if isinstance(config.get("logging"), dict) else {}
        decisions_path = _resolve_output_path(logging_cfg.get("decisions_jsonl", "decisions.jsonl"), LOGS_DIR)
        recent_bot_errors = _recent_reason_count(
            decisions_path,
            "bot_error",
            now - timedelta(minutes=max(1, window_minutes)),
            max_lines=int(runtime_guard_cfg.get("scan_lines", 4000) or 4000),
        )
        runtime_unstable = recent_bot_errors >= max(1, max_bot_errors)

    # Recompute route_tier with effective gates (after overrides)
    route_tier_effective = compute_route_tier(gates_effective, config)

    # In "reduced" tier, only allow C/E/F/reversal_impulse/compression entries
    reduced_entry_blocked = False
    if route_tier_effective == "reduced" and entry:
        allowed_reduced = {"reversal_impulse", "compression_breakout", "compression_range", "trend_continuation", "fib_retrace", "slow_bleed_hunter", "liquidity_sweep", "micro_sweep"}
        lane_name = (lane_result.lane if lane_result else "").upper() if lane_result else ""
        if lane_name in ("C", "E", "F", "G", "H", "I", "J", "V"):
            pass  # allowed
        elif selected_entry_type in allowed_reduced:
            pass  # allowed
        else:
            reduced_entry_blocked = True

    # MONSTER bypass: exceptional setups skip cooldown — these are too
    # good to miss (the overnight ghost-trade disaster taught us this).
    if cooldown and _TIER_RANK.get(quality_tier, 0) >= _TIER_RANK.get("FULL", 2):
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "cooldown_bypassed",
            "quality_tier": quality_tier,
            "consecutive_losses": int(state.get("consecutive_losses") or 0),
        })
        cooldown = False

    # --- Dip-retrace no-short gate ---
    # Blocks shorts when price is bouncing (RSI rising + higher closes + VWAP reclaim)
    _drg_blocked = False
    _drg_meta = {}
    if entry and direction:
        try:
            _drg_blocked, _drg_meta = _dip_retrace_gate(
                direction=direction,
                df_15m=df_15m,
                df_1h=df_1h,
                price=price,
                config=config,
                quality_tier=quality_tier,
                entry_type=selected_entry_type,
            )
            if _drg_blocked:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "dip_retrace_gate_block",
                    "direction": direction,
                    "entry_type": selected_entry_type,
                    "quality_tier": quality_tier,
                    "gate_meta": _drg_meta,
                    "thought": "Bounce detected: RSI rising + higher closes + near VWAP. Blocking short.",
                })
                # Do not enter - bounce in progress
                entry = None
                direction = None
        except Exception:
            pass

    # --- Support Proximity Gate (Mar 21 fix) ---
    # Block shorts when price is within X% of recent support (48h low on 1h)
    # Reversal shorts at 0.165 lost because they shorted INTO support instead of after a break
    if entry and direction and direction.lower() == "short":
        try:
            _spg_cfg = (v4_cfg.get("support_proximity_gate") or {}) if isinstance(v4_cfg.get("support_proximity_gate"), dict) else {}
            if _spg_cfg.get("enabled", False):
                _spg_lookback = int(_spg_cfg.get("lookback_bars_1h", 48))
                _spg_proximity = float(_spg_cfg.get("proximity_pct", 0.005))
                _spg_exempt_tiers = list(_spg_cfg.get("exempt_tiers") or [])
                _spg_exempt_types = list(_spg_cfg.get("exempt_entry_types") or [])
                _spg_blocked = False

                if quality_tier not in _spg_exempt_tiers and selected_entry_type not in _spg_exempt_types:
                    if df_1h is not None and len(df_1h) >= _spg_lookback:
                        _recent_low = float(df_1h["low"].iloc[-_spg_lookback:].min())
                        _dist_to_support = (price - _recent_low) / _recent_low if _recent_low > 0 else 999
                        if _dist_to_support < _spg_proximity:
                            _spg_blocked = True
                            log_decision(config, {
                                "timestamp": now.isoformat(),
                                "reason": "support_proximity_gate_block",
                                "direction": direction,
                                "entry_type": selected_entry_type,
                                "price": price,
                                "support_level": _recent_low,
                                "distance_pct": round(_dist_to_support, 6),
                                "threshold_pct": _spg_proximity,
                                "thought": f"Short blocked: price ${price:.5f} is only {_dist_to_support*100:.2f}% above 48h support ${_recent_low:.5f}. Wait for confirmed break below.",
                            })
                            entry = None
                            direction = None
        except Exception:
            pass

    _ai_initiated = False  # Set to True if Claude initiates an entry (no strategy engine signal)
    gate_blocked = (route_tier_effective == "blocked") or reduced_entry_blocked
    if (gate_blocked or cooldown or not product_available or fail_safe or runtime_unstable) and not _ai_exec_override:
        block_reasons = []
        failed_gates = [k for k, v in gates_effective.items() if not bool(v)]
        if gate_blocked:
            block_reasons.append("gates_fail")
        if cooldown:
            block_reasons.append("cooldown")
        if not product_available:
            block_reasons.append("product_unavailable")
        if fail_safe:
            block_reasons.append("kill_switch")
        if runtime_unstable:
            block_reasons.append("runtime_unstable")
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_preflight",
                "block_reasons": block_reasons,
                "failed_gates": failed_gates,
                "gates": gates_effective,
                "gates_pass": gates_pass_effective,
                "route_tier": route_tier_effective,
                "reduced_entry_blocked": reduced_entry_blocked,
                "distance_gate_override_applied": distance_override_applied,
                "distance_gate_override": distance_override_meta,
                "atr_gate_override_applied": atr_override_applied,
                "atr_gate_override": atr_override_meta,
                "v4_score_override_applied": score_override_applied,
                "v4_score_override": score_override_meta,
                "cooldown": cooldown,
                "product_available": product_available,
                "fail_safe": fail_safe,
                "recent_bot_errors": recent_bot_errors,
                "runtime_guard": runtime_guard_cfg,
            },
        )
        save_state(state)
        return

    if state["trades"] >= config["risk"]["max_trades_per_day"] and not _ai_exec_override:
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_max_trades",
                "trades_today": state.get("trades", 0),
                "max_trades_per_day": config["risk"]["max_trades_per_day"],
            },
        )
        save_state(state)
        return
    if state["losses"] >= config["risk"]["max_losses_per_day"] and not _ai_exec_override:
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_max_losses",
                "losses_today": state.get("losses", 0),
                "max_losses_per_day": config["risk"]["max_losses_per_day"],
            },
        )
        save_state(state)
        return

    # ── Daily profit target — lock in green days (AI can override if it sees edge) ──
    _daily_target = float(config.get("risk", {}).get("daily_profit_target_usd", 0))
    _pnl_today = float(state.get("pnl_today_usd") or 0.0)
    if _daily_target > 0 and _pnl_today >= _daily_target and not _ai_exec_override:
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_daily_profit_target",
                "pnl_today_usd": _pnl_today,
                "daily_profit_target_usd": _daily_target,
            },
        )
        print(f"Daily profit target hit: ${_pnl_today:.2f} >= ${_daily_target:.2f} — done for the day")
        # state["_safe_mode"] = True  # disabled -- never want full shutdown
        save_state(state)
        return

    # ── Revenge trade blocker — default cooldown, AI can override with conviction ──
    _revenge_cooldown_min = float(config.get("risk", {}).get("revenge_cooldown_minutes", 0))
    if _revenge_cooldown_min > 0 and int(state.get("consecutive_losses", 0)) >= 1 and not _ai_exec_override:
        _last_exit_str = state.get("last_exit_time")
        if _last_exit_str:
            try:
                _last_exit_dt = datetime.fromisoformat(str(_last_exit_str))
                _minutes_since_exit = (now - _last_exit_dt).total_seconds() / 60
                if _minutes_since_exit < _revenge_cooldown_min:
                    log_decision(
                        config,
                        {
                            "timestamp": now.isoformat(),
                            "reason": "revenge_blocked",
                            "minutes_since_last_loss": round(_minutes_since_exit, 1),
                            "revenge_cooldown_minutes": _revenge_cooldown_min,
                            "consecutive_losses": state.get("consecutive_losses", 0),
                        },
                    )
                    print(
                        f"Revenge blocked: {_minutes_since_exit:.1f}min since last loss "
                        f"(need {_revenge_cooldown_min}min cooldown)"
                    )
                    save_state(state)
                    return
            except (ValueError, TypeError):
                pass

    # -- Rolling expectancy gate: kill switch when bot is running cold --
    _re_cfg = config.get("rolling_expectancy", {}) or {}
    _re_blocked = False
    _re_size_mult = 1.0
    _re_result: dict[str, Any] = {}
    _re_data: dict[str, Any] = {}
    _kelly_mult = 1.0
    _kelly_reason = "disabled"
    if _re_cfg.get("enabled", False) and entry:
        try:
            _re_data = get_rolling_expectancy(
                LOGS_DIR / "trades.csv",
                lookback=int(_re_cfg.get("lookback", 20)),
            )
            _re_result = evaluate_expectancy_gate(_re_data, _re_cfg)
            _re_size_mult = float(_re_result.get("size_mult", 1.0))
            # Kelly Criterion: further scale size by edge quality (not just gate pass/fail)
            try:
                _kelly_mult, _kelly_reason = kelly_size_multiplier(
                    _re_data,
                    min_trades=int(_re_cfg.get("kelly_min_trades", 10) or 10),
                    kelly_fraction=float(_re_cfg.get("kelly_fraction", 0.4) or 0.4),
                )
                # Blend: kelly mult only applies when gate allows and mult > 1
                # (never oversize when expectancy gate already reduced size)
                if _kelly_mult > 1.0 and _re_size_mult >= 1.0:
                    _re_size_mult = min(_re_size_mult * _kelly_mult, 1.5)
                elif _kelly_mult < 1.0:
                    _re_size_mult = _re_size_mult * _kelly_mult
            except Exception:
                _kelly_reason = "kelly_error"
            if not _re_result.get("allowed", True) and not _ai_exec_override:
                _re_blocked = True
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "entry_blocked_rolling_expectancy",
                    "rolling_expectancy": _re_result.get("expectancy_data"),
                    "gate_reason": _re_result.get("reason"),
                    "action": _re_result.get("action"),
                })
                try:
                    slack_alert.send(
                        f"EXPECTANCY KILL-SWITCH: {_re_result.get('reason')}. "
                        f"WR={_re_data.get('win_rate', 0):.0%}, "
                        f"EV=${_re_data.get('avg_pnl_usd', 0):.2f}, "
                        f"PF={_re_data.get('profit_factor', 0):.2f}",
                        level="warning",
                    )
                except Exception:
                    pass
                save_state(state)
                return
        except Exception:
            pass  # never block on computation error

    if regime_mode_block and not _ai_exec_override:
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_regime_mode",
                "regime_mode": (regime_mode_block or {}).get("mode"),
                "selected_regime": (regime_mode_block or {}).get("selected_regime"),
            },
        )
        save_state(state)
        return

    # -- Sentiment gate: block toxic trades during extreme fear/panic --
    _sentiment_cfg = config.get("sentiment_gate", {}) or {}
    _sentiment_blocked = False
    _sentiment_size_mult = 1.0
    _sentiment_data: dict = {}
    if _sentiment_cfg.get("enabled", True) and entry:
        try:
            _sentiment_data = get_sentiment()
            _sg_result = evaluate_sentiment_gate(
                _sentiment_data, direction, _sentiment_cfg,
            )
            _sentiment_size_mult = float(_sg_result.get("size_mult", 1.0))
            if not _sg_result.get("allowed", True) and not _ai_exec_override:
                _sentiment_blocked = True
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "entry_blocked_sentiment",
                    "sentiment_score": _sg_result.get("score"),
                    "sentiment_class": _sg_result.get("classification"),
                    "direction": direction,
                    "gate_reason": _sg_result.get("reason"),
                    "entry_type": selected_entry_type,
                })
                save_state(state)
                return
        except Exception:
            pass  # API failure = neutral, never block trades on fetch error

    if not entry:
        # AI Executive: Claude can initiate entries the strategy engine missed
        _ai_d_entry = ai_advisor.get_directive()
        _ai_initiated = False
        if (
            _ai_d_entry
            and _ai_d_entry.get("action") in ("ENTER_LONG", "ENTER_SHORT")
            and float(_ai_d_entry.get("confidence", 0)) >= float((config.get("ai") or {}).get("executive_min_confidence", 0.6))
            and ai_advisor.is_executive_mode()
            and _ai_allow_no_signal_entries
            and float(_ai_d_entry.get("stop_loss_price", 0) or 0) > 0
        ):
            direction = "long" if _ai_d_entry["action"] == "ENTER_LONG" else "short"
            # Validate AI entry price sanity (prevent corrupt JSON)
            _ai_entry_price = float(_ai_d_entry.get("entry_price") or 0)
            if _ai_entry_price > 0 and not (price * 0.90 <= _ai_entry_price <= price * 1.10):
                log_decision(config, {"timestamp": now.isoformat(), "reason": "ai_entry_price_sanity_fail", "ai_price": _ai_entry_price, "market_price": price})
                save_state(state)
                return
            entry = {"type": "ai_executive", "confluence": {"ai_confidence": float(_ai_d_entry.get("confidence", 0.7))}}
            # AI-initiated entries still pass through hard gates — score reflects AI confidence, not a free pass
            _ai_synth_score = max(int(float(_ai_d_entry.get("confidence", 0.7)) * 100), 50)
            selected_v4 = {"score": _ai_synth_score, "threshold": 40, "pass": True, "regime": regime_v4.get("regime", "neutral")}
            # Compute real quality tier from market score, not hardcoded FULL
            # AI confidence does not override market quality
            _ai_market_score = int(selected_v4.get("score") or 0)
            _ai_market_thresh = int(selected_v4.get("threshold") or 75)
            qt_cfg_ai = (v4_cfg.get("quality_tiers") or {}) if isinstance(v4_cfg.get("quality_tiers"), dict) else {}
            quality_tier = _compute_quality_tier(_ai_market_score, _ai_market_thresh, qt_cfg_ai)
            if quality_tier == "NO_TRADE":
                log_decision(config, {"timestamp": now.isoformat(), "reason": "ai_blocked_no_trade_quality", "score": _ai_market_score, "threshold": _ai_market_thresh})
                save_state(state)
                return
            lane_result = None
            breakout_type = "neutral"
            _ai_initiated = True
            state.pop("_ai_flat_price", None)  # clear FLAT tracking on entry
            state.pop("_ai_flat_ts", None)
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "ai_executive_entry_initiated",
                "direction": direction,
                "ai_directive": _ai_d_entry,
            })
        else:
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "entry_blocked_no_signal",
                },
            )
            save_state(state)
            return

    # AI Executive: FLAT override — Claude says stay out even if engine has a signal
    _ai_d_flat = ai_advisor.get_directive()
    if (
        _ai_d_flat
        and _ai_d_flat.get("action") == "FLAT"
        and float(_ai_d_flat.get("confidence", 0)) >= float((config.get("ai") or {}).get("executive_min_confidence", 0.6))
        and ai_advisor.is_executive_mode()
        and not _ai_initiated
    ):
        # Track FLAT for self-learning feedback
        _prev_flat_price = float(state.get("_ai_flat_price") or 0)
        _prev_flat_ts = state.get("_ai_flat_ts")
        if _prev_flat_price > 0 and _prev_flat_ts:
            try:
                _flat_age_min = (now - _parse_ts_utc(_prev_flat_ts)).total_seconds() / 60
                if _flat_age_min >= 10:  # only log after 10+ min
                    ai_advisor.log_flat_outcome(
                        directive=_ai_d_flat,
                        price_at_flat=_prev_flat_price,
                        price_after=price,
                        minutes_later=int(_flat_age_min),
                    )
                    state.pop("_ai_flat_price", None)
                    state.pop("_ai_flat_ts", None)
            except Exception:
                pass
        if not state.get("_ai_flat_price"):
            state["_ai_flat_price"] = price
            state["_ai_flat_ts"] = now.isoformat()
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "ai_executive_flat_override",
            "ai_directive": _ai_d_flat,
            "engine_had_signal": bool(entry),
            "engine_direction": direction,
        })
        save_state(state)
        return

    # --- Countertrend Structure Block ---
    # Block entries that fight 15m swing structure, unless MONSTER quality
    if entry and direction and _structure_bias != "neutral":
        _is_countertrend = (
            (_structure_bias == "bearish" and direction == "long") or
            (_structure_bias == "bullish" and direction == "short")
        )
        _is_fib_retrace = (selected_entry_type == "fib_retrace")
        _is_bleed = (selected_entry_type == "slow_bleed_hunter")
        if _is_countertrend and not _is_fib_retrace and not _is_bleed and _TIER_RANK.get(quality_tier, 0) < _TIER_RANK.get("MONSTER", 3) and not _ai_exec_override:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_countertrend_structure",
                "direction": direction,
                "structure_bias": _structure_bias,
                "quality_tier": quality_tier,
                "entry_type": selected_entry_type,
                "thought": f"blocking {direction} entry — 15m structure is {_structure_bias}. Need MONSTER quality to override.",
            })
            save_state(state)
            return

    # ── HARD GATES — NOTHING overrides these, not even AI executive ─────
    _hard_min = int((config.get("ai") or {}).get("hard_min_score", 40))
    _cur_score = int((selected_v4 or {}).get("score") or 0)

    # Gate A: Absolute minimum score floor
    if _cur_score < _hard_min and not _ai_initiated:
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "hard_min_score_block",
            "score": _cur_score,
            "hard_min": _hard_min,
            "quality_tier": quality_tier,
            "direction": direction,
            "thought": f"score {_cur_score} below absolute floor {_hard_min} — NO override allowed",
        })
        save_state(state)
        return

    # Gate B: NO_TRADE quality tier is an unconditional hard block
    if quality_tier == "NO_TRADE":
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "no_trade_hard_block",
            "score": _cur_score,
            "quality_tier": quality_tier,
            "direction": direction,
            "thought": "NO_TRADE tier is an absolute block — nothing overrides this",
        })
        save_state(state)
        return

    # Gate C: Revenge trade detection — block if last 3 trades lost in same price zone
    try:
        _revenge_zone_pct = 0.005  # 0.5% price band = "same zone"
        _revenge_lookback = 3
        if trades is not None and not trades.empty and price > 0:
            _recent_trades = trades.tail(_revenge_lookback)
            _zone_losses = 0
            for _, _rt in _recent_trades.iterrows():
                _rt_entry = float(_rt.get("entry_price") or 0)
                _rt_result = str(_rt.get("result") or "")
                if _rt_entry > 0 and _rt_result == "loss" and abs(_rt_entry - price) / price < _revenge_zone_pct:
                    _zone_losses += 1
            if _zone_losses >= _revenge_lookback:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "revenge_trade_blocked",
                    "price": price,
                    "zone_losses": _zone_losses,
                    "direction": direction,
                    "thought": f"last {_zone_losses} trades all lost within 0.5% of current price — revenge pattern blocked",
                })
                save_state(state)
                return
    except Exception:
        pass  # never let revenge check crash the bot

    if score_gate_strict and not score_gate_pass_effective and not _ai_exec_override:
        qt_enabled = bool(qt_cfg.get("enabled", False))
        if qt_enabled and quality_tier in ("NO_TRADE",):
            trend_flags = (selected_v4.get("trend_flags") or {}) if isinstance(selected_v4, dict) else {}
            failed_flags = [k for k, v in trend_flags.items() if not bool(v)]
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "v4_score_block_entry",
                    "direction": direction,
                    "score": (selected_v4 or {}).get("score"),
                    "threshold": (selected_v4 or {}).get("threshold"),
                    "regime": (selected_v4 or {}).get("regime"),
                    "failed_flags": failed_flags,
                    "quality_tier": quality_tier,
                    "v4_score_pass": score_gate_pass,
                    "v4_score_pass_effective": score_gate_pass_effective,
                    "v4_score_override_applied": score_override_applied,
                    "v4_score_override": score_override_meta,
                },
            )
            save_state(state)
            return
        # REDUCED or SCALP tier: allow entry with tighter management
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "quality_tier_entry",
                "direction": direction,
                "quality_tier": quality_tier,
                "score": (selected_v4 or {}).get("score"),
                "threshold": (selected_v4 or {}).get("threshold"),
            },
        )

    # Enforce margin policy for NEW entries only (existing positions are managed above).
    if mp_decision and mp_enforcement != "log_only" and not _ai_exec_override:
        if "BLOCK_ENTRY" in (mp_decision.actions or []) and mp_decision.tier in ("WARNING", "DANGER", "LIQUIDATION"):
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "margin_policy_block_entry",
                "tier": mp_decision.tier,
                "actions": mp_decision.actions,
                "metrics": mp_decision.metrics,
            })
            save_state(state)
            return

    # --- Range Position Gate: block chasing entries ---
    # If price has already consumed >80% of recent range in our direction, we're chasing.
    # Uses last 48 bars (12h on 15m) to define the session range.
    # FULL/MONSTER quality bypasses this gate (structure-led entries are intentional).
    _rp_lookback = 48
    _rp_chase_pct = 0.80  # block if >80% consumed
    if len(df_15m) >= _rp_lookback:
        _rp_window = df_15m.tail(_rp_lookback)
        _rp_high = float(_rp_window["high"].max())
        _rp_low = float(_rp_window["low"].min())
        _rp_range = _rp_high - _rp_low
        if _rp_range > 0:
            _rp_position = (price - _rp_low) / _rp_range  # 0=bottom, 1=top
            _rp_chasing = (direction == "long" and _rp_position > _rp_chase_pct) or \
                          (direction == "short" and _rp_position < (1.0 - _rp_chase_pct))
            if _rp_chasing and _TIER_RANK.get(quality_tier, 0) < _TIER_RANK.get("REDUCED", 1) and not _ai_exec_override:
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "entry_blocked_range_chase",
                    "direction": direction,
                    "range_position": round(_rp_position, 3),
                    "range_high": round(_rp_high, 6),
                    "range_low": round(_rp_low, 6),
                    "quality_tier": quality_tier,
                    "thought": f"chasing: price at {_rp_position*100:.0f}% of 12h range ({direction}). Waiting for pullback.",
                })
                save_state(state)
                return

    sl_buffer_mult = float(config.get("risk", {}).get("sl_atr_buffer_mult", 0.5) or 0.5)
    # AI Executive: use Claude's stop loss if this is an AI-initiated entry
    _ai_sl = float((ai_advisor.get_directive() or {}).get("stop_loss_price", 0) or 0)
    if _ai_initiated and _ai_sl > 0:
        stop_price = _ai_sl
    else:
        stop_price = stop_loss_price(price, df_1h, direction, df_15m=df_15m, buffer_atr_mult=sl_buffer_mult)
    # Structure-based stop override: use the most recent swing high/low
    # instead of the 20-bar absolute high/low when structure is confirmed.
    # Applies to ALL entry types — not just trend_continuation.
    _struct_stop_used = False
    if entry and direction and df_15m is not None and len(df_15m) >= 40:
        try:
            from strategy.entries import _detect_swing_points
            from strategy.risk import structure_stop_loss_price
            _sw = _detect_swing_points(df_15m.tail(60), left=2, right=2)
            _shs = _sw.get("swing_highs", [])
            _sls = _sw.get("swing_lows", [])
            _struct_entry = {}
            if direction == "short" and _shs:
                _struct_entry["structure_stop"] = _shs[0][1]  # most recent swing high
            elif direction == "long" and _sls:
                _struct_entry["structure_stop"] = _sls[0][1]  # most recent swing low
            if _struct_entry.get("structure_stop"):
                _ss = structure_stop_loss_price(price, _struct_entry, direction, df_15m)
                if _ss > 0:
                    # Use structure stop if it's TIGHTER (closer to price)
                    if direction == "long" and _ss > stop_price:
                        stop_price = _ss
                        _struct_stop_used = True
                    elif direction == "short" and _ss < stop_price:
                        stop_price = _ss
                        _struct_stop_used = True
        except Exception:
            pass
    # Fib retrace: override stop with swing extreme from entry result
    if str((entry or {}).get("type") or "") == "fib_retrace":
        _fib_stop = float((entry or {}).get("structure_stop") or 0)
        if _fib_stop > 0:
            stop_price = _fib_stop
            _struct_stop_used = True
    _effective_max_sl = regime_overrides.max_sl_pct  # regime-aware SL cap
    # FULL/MONSTER quality gets 20% wider SL allowance — exceptional setups
    # shouldn't be killed by a 0.01% rounding edge case
    if _TIER_RANK.get(quality_tier, 0) >= _TIER_RANK.get("FULL", 2):
        _effective_max_sl *= 1.20
    # ATR fallback stop: when structure stop exceeds SL cap but lane has
    # atr_gate_bypass (Lane H, C, G, I), fall back to ATR-based stop.
    # Better to enter with a tighter stop than to miss a massive move.
    if not sl_distance_ok(price, stop_price, _effective_max_sl):
        _atr_fb_applied = False
        if lane_result and lane_result.atr_gate_bypass:
            _exp_m_fb = (expansion_state.get("metrics") or {})
            _atr_fb = float(_exp_m_fb.get("atr", 0) or 0)
            _fb_mult = float(config.get("risk", {}).get("sl_atr_fallback_mult", 4.0) or 4.0)
            if _atr_fb > 0:
                if direction == "short":
                    _fb_stop = price + _atr_fb * _fb_mult
                else:
                    _fb_stop = price - _atr_fb * _fb_mult
                if _fb_stop > 0 and sl_distance_ok(price, _fb_stop, _effective_max_sl):
                    _orig_sl_dist = abs(price - stop_price) / price if price > 0 else 0
                    _new_sl_dist = abs(price - _fb_stop) / price if price > 0 else 0
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "sl_atr_fallback",
                        "direction": direction,
                        "original_stop": round(float(stop_price), 6),
                        "fallback_stop": round(float(_fb_stop), 6),
                        "original_sl_pct": round(_orig_sl_dist * 100, 2),
                        "fallback_sl_pct": round(_new_sl_dist * 100, 2),
                        "atr": round(_atr_fb, 8),
                        "mult": _fb_mult,
                        "lane": lane_result.lane,
                        "thought": f"structure stop too far ({_orig_sl_dist*100:.1f}%), ATR fallback ({_new_sl_dist*100:.1f}%) via {_fb_mult:.0f}×ATR",
                    })
                    stop_price = _fb_stop
                    _struct_stop_used = False
                    _atr_fb_applied = True
    if not sl_distance_ok(price, stop_price, _effective_max_sl) and not _ai_exec_override:
        _sl_dist = abs(price - stop_price) / price if price > 0 and stop_price > 0 else 0.0
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "entry_blocked_sl_distance",
            "direction": direction,
            "price": float(price),
            "stop_price": float(stop_price),
            "sl_distance_pct": round(_sl_dist * 100, 2),
            "max_sl_pct": _effective_max_sl * 100,
            "regime": regime_overrides.regime_name,
            "thought": f"stop too far: {_sl_dist*100:.1f}% vs {_effective_max_sl*100:.0f}% max ({regime_overrides.regime_name}) — waiting for tighter setup.",
        })
        save_state(state)
        return

    # --- R:R Gate: tier-based — weaker signals need better R:R ---
    # MONSTER tier bypasses entirely — signal quality IS the edge
    # Fee-adjusted: subtract estimated round-trip fees from TP distance
    _rr_cfg = config.get("risk", {}).get("min_rr_ratio", {})
    if isinstance(_rr_cfg, dict):
        _min_rr = float(_rr_cfg.get(quality_tier, _rr_cfg.get("default", 0.0)) or 0.0)
    else:
        _min_rr = float(_rr_cfg or 0.0)  # legacy: flat number
    _rr_bypass = _TIER_RANK.get(quality_tier, 0) >= _TIER_RANK.get("MONSTER", 3)
    if _min_rr > 0 and stop_price > 0 and price > 0 and not _rr_bypass:
        _sl_dist_rr = abs(price - stop_price)
        _exp_m_rr = (expansion_state.get("metrics") or {})
        _atr_for_rr = float(_exp_m_rr.get("atr", 0) or 0)
        _tp_dist_rr = regime_overrides.tp_atr_mult * _atr_for_rr if _atr_for_rr > 0 else _sl_dist_rr
        # Subtract fee cost from TP distance (fees eat into profit)
        _rr_ev_cfg = config.get("ev") or {}
        _rr_fee_rate = float(_rr_ev_cfg.get("taker_fee_rate", 0.0009) or 0.0009)
        _rr_fee_dist = price * _rr_fee_rate * 2  # round-trip fees as price distance
        _tp_dist_rr_net = max(_tp_dist_rr - _rr_fee_dist, 0)
        _rr_ratio = _tp_dist_rr_net / _sl_dist_rr if _sl_dist_rr > 0 else 0.0
        if _rr_ratio < _min_rr and not _ai_exec_override:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "entry_blocked_rr_ratio",
                "direction": direction,
                "quality_tier": quality_tier,
                "rr_ratio": round(_rr_ratio, 2),
                "min_rr_ratio": _min_rr,
                "sl_distance": round(_sl_dist_rr, 8),
                "tp_distance": round(_tp_dist_rr, 8),
                "tp_distance_net": round(_tp_dist_rr_net, 8),
                "est_fees_dist": round(_rr_fee_dist, 8),
                "regime": regime_overrides.regime_name,
                "thought": f"R:R {_rr_ratio:.1f} (net of fees) < {_min_rr:.1f} min for {quality_tier} tier — skipping entry.",
            })
            save_state(state)
            return

    # Micro-sweep overnight override:
    # Allow 1-contract micro-sweep entries during overnight IF margin is safe.
    _micro_sweep_overnight_bypass = False
    if (
        _micro_sweep_promoted
        and entry
        and bool(entry.get("micro_sweep"))
        and overnight_trading_ok
        and bool(lane_cfg.get("micro_sweep_overnight_override", False))
    ):
        _micro_sweep_overnight_bypass = True
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "micro_sweep_overnight_bypass",
            "direction": direction,
            "micro_sweep_score": entry.get("micro_sweep_score"),
            "swept_level": entry.get("swept_level"),
            "reclaim_price": entry.get("reclaim_price"),
            "thought": "5m micro-sweep detected during overnight. Margin is safe, allowing 1-contract entry.",
        })

    if (
        _margin_window_playbook.get("enabled")
        and _margin_window_playbook.get("block_new_entries")
        and not state.get("open_position")
        and not _ai_exec_override
        and not _micro_sweep_overnight_bypass
    ):
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "entry_blocked_margin_playbook",
            "direction": direction,
            "quality_tier": quality_tier,
            "margin_window": _margin_window_playbook.get("margin_window"),
            "playbook_label": _margin_window_playbook.get("label"),
            "objective": _margin_window_playbook.get("objective"),
            "mins_to_cutoff": _margin_window_playbook.get("mins_to_cutoff"),
            "notes": _margin_window_playbook.get("notes"),
            "thought": "Margin-window playbook blocks fresh entries in this time window.",
        })
        save_state(state)
        return

    leverage = min(int(config["leverage"]), 4)
    size = 1
    sizing_meta = {}

    # --- Dynamic position sizing (compound growth engine) ---
    ps_cfg = (config.get("position_sizing") or {}) if isinstance(config.get("position_sizing"), dict) else {}
    if ps_cfg.get("enabled", False) and equity_start and equity_start > 0:
        # Margin-window-aware equity_per_contract override
        _mws = ps_cfg.get("margin_window_sizing") or {}
        if _mws.get("enabled", False) and mp_decision and isinstance(mp_decision.metrics, dict):
            _mw = (mp_decision.metrics or {}).get("margin_window", "")
            if _mw == "intraday":
                _mw_epc = float(_mws.get("intraday_equity_per_contract", 0) or 0)
            elif _mw == "pre_cutoff":
                _mw_epc = float(_mws.get("pre_cutoff_equity_per_contract", 0) or 0)
            else:  # overnight or unknown
                _mw_epc = float(_mws.get("overnight_equity_per_contract", 0) or 0)
            if _mw_epc > 0:
                ps_cfg = dict(ps_cfg)  # shallow copy to avoid mutating config
                ps_cfg["equity_per_contract"] = _mw_epc
                sizing_meta["margin_window"] = _mw
                sizing_meta["margin_window_epc"] = _mw_epc
        # Get contract size for risk calculation
        _cs_probe = api.get_product_details(product_id) if product_id else {}
        _cs_val = _to_float((_cs_probe or {}).get("contract_size"), 0.0) or 0.0
        consecutive_wins = int(state.get("consecutive_wins") or 0)
        _lane_letter = (lane_result.lane if lane_result else "A").upper()
        # Use TOTAL balance (derivatives + transferable spot) for sizing, not just derivatives
        _sizing_equity = equity_start or 0
        try:
            _spot_cash = state.get("last_spot_cash_map") or {}
            _spot_avail = sum(float(v) for v in _spot_cash.values() if v)
            _spot_reserve = float((config.get("futures_funding") or {}).get("spot_reserve_floor_usd", 5) or 5)
            _spot_xfer = max(0, _spot_avail - _spot_reserve)
            if _spot_xfer > 10:
                _sizing_equity += _spot_xfer
                sizing_meta["equity_includes_spot"] = round(_spot_xfer, 2)
        except Exception:
            pass
        size, sizing_meta = _compute_position_size(
            equity=_sizing_equity,
            price=float(price),
            stop_price=float(stop_price),
            contract_size_val=_cs_val,
            lane=_lane_letter,
            quality_tier=quality_tier,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            ps_cfg=ps_cfg,
        )
        # Regime size multiplier (compression = 0.7x, expansion/transition = 1.0x)
        if regime_overrides.size_multiplier != 1.0:
            _pre_regime_size = size
            size = max(1, int(size * regime_overrides.size_multiplier))
            sizing_meta["regime_size_mult"] = regime_overrides.size_multiplier
            sizing_meta["pre_regime_size"] = _pre_regime_size
        # HTF direction bias: asymmetric sizing (smaller longs in downtrend, bigger shorts)
        _htf_size_mult = 1.0
        if _htf_bias:
            _htf_dir_cfg = (config.get("htf_direction_filter") or {}) if isinstance(config.get("htf_direction_filter"), dict) else {}
            if _htf_dir_cfg.get("enabled", True):
                _htf_bias_state = str(_htf_bias.get("bias", "neutral"))
                if direction == "long":
                    _htf_size_mult = float(_htf_bias.get("size_mult_long", 1.0))
                elif direction == "short":
                    _htf_size_mult = float(_htf_bias.get("size_mult_short", 1.0))
                if _htf_size_mult != 1.0:
                    _pre_htf_size = size
                    size = max(1, int(size * _htf_size_mult))
                    sizing_meta["htf_bias"] = _htf_bias_state
                    sizing_meta["htf_size_mult"] = _htf_size_mult
                    sizing_meta["pre_htf_size"] = _pre_htf_size
        # Sentiment gate: reduce size in fear conditions
        if _sentiment_size_mult < 1.0:
            _pre_sentiment_size = size
            size = max(1, int(size * _sentiment_size_mult))
            sizing_meta["sentiment_size_mult"] = _sentiment_size_mult
            sizing_meta["sentiment_score"] = _sentiment_data.get("score")
            sizing_meta["pre_sentiment_size"] = _pre_sentiment_size
        # Rolling expectancy gate: reduce or promote size based on realized edge quality.
        if _re_size_mult != 1.0:
            _pre_re_size = size
            size, _re_size_meta = _apply_expectancy_size_multiplier(size, _re_size_mult, _re_cfg)
            sizing_meta.update(_re_size_meta)
            sizing_meta["pre_expectancy_size"] = _pre_re_size
            sizing_meta["expectancy_gate_reason"] = _re_result.get("reason")
            sizing_meta["expectancy_allowed"] = bool(_re_result.get("allowed", True))
            sizing_meta["expectancy_avg_pnl_usd"] = _re_data.get("avg_pnl_usd")
            sizing_meta["expectancy_win_rate"] = _re_data.get("win_rate")
            sizing_meta["kelly_size_mult"] = round(float(_kelly_mult or 1.0), 3)
            sizing_meta["kelly_reason"] = _kelly_reason
        # Lane-specific expectancy: only promote/reduce Lane W when its own stats justify it.
        _lane_specific_mult = 1.0
        _lane_specific_meta: dict[str, Any] = {}
        if lane_result is not None:
            _lane_specific_mult, _lane_specific_meta = _lane_specific_expectancy_multiplier(
                lane_result.lane,
                _read_lane_stats(LOGS_DIR),
                lane_cfg,
            )
            if _lane_specific_mult != 1.0:
                _pre_lane_expectancy_size = size
                size, _lane_specific_size_meta = _apply_expectancy_size_multiplier(
                    size,
                    _lane_specific_mult,
                    {
                        "promotion_min_size_mult": 1.05,
                        "promotion_cap": max(1.0, _lane_specific_mult),
                        "reduction_floor": min(1.0, _lane_specific_mult),
                    },
                )
                sizing_meta["pre_lane_expectancy_size"] = _pre_lane_expectancy_size
                sizing_meta.update(_lane_specific_meta)
                sizing_meta.update(_lane_specific_size_meta)
            elif _lane_specific_meta:
                sizing_meta.update(_lane_specific_meta)
        # Market pulse gate: reduce size in risk_off conditions
        if _pulse:
            _pulse_cfg = config.get("market_pulse", {}) or {}
            if _pulse_cfg.get("enabled", False):
                _pg = market_pulse.evaluate_pulse_gate(_pulse, _pulse_cfg)
                if _pg.get("size_mult", 1.0) < 1.0:
                    _pre_pulse_size = size
                    size = max(1, int(size * _pg["size_mult"]))
                    sizing_meta["pulse_size_mult"] = _pg["size_mult"]
                    sizing_meta["pulse_health"] = _pulse.get("health_score")
                    sizing_meta["pre_pulse_size"] = _pre_pulse_size
        # Recovery Mode: apply size multiplier
        if recovery_info.get("active") and recovery_info.get("size_multiplier", 1.0) > 1.0:
            _rm_mult = recovery_info["size_multiplier"]
            _rm_size = max(1, int(size * _rm_mult))
            sizing_meta["recovery_size_mult"] = _rm_mult
            sizing_meta["pre_recovery_size"] = size
            size = _rm_size

        # Micro-sweep size cap: conservative 1-contract only for this entry class.
        if entry and bool(entry.get("micro_sweep")):
            _ms_max = int(lane_cfg.get("micro_sweep_max_contracts", 1) or 1)
            if size > _ms_max:
                sizing_meta["micro_sweep_size_cap"] = _ms_max
                sizing_meta["pre_micro_sweep_size"] = size
                size = _ms_max

        # --- Equity % Risk Cap (10% of equity per trade) ---
        _max_risk_pct = float(config.get("risk", {}).get("max_risk_pct_per_trade", 0.10) or 0.10)
        _max_loss_usd = equity_start * _max_risk_pct if equity_start > 0 else 0.0
        if _max_loss_usd > 0 and stop_price > 0 and _cs_val > 0:
            _loss_per_contract = abs(price - stop_price) * _cs_val
            _total_loss = _loss_per_contract * size
            if _total_loss > _max_loss_usd:
                _max_contracts = int(_max_loss_usd / _loss_per_contract) if _loss_per_contract > 0 else 0
                if _max_contracts >= 1:
                    sizing_meta["equity_risk_cap_original"] = size
                    sizing_meta["equity_risk_cap_reduced"] = _max_contracts
                    sizing_meta["loss_per_contract"] = round(_loss_per_contract, 4)
                    sizing_meta["max_risk_usd"] = round(_max_loss_usd, 2)
                    sizing_meta["max_risk_pct"] = _max_risk_pct
                    size = _max_contracts
                elif not _ai_exec_override:
                    log_decision(config, {
                        "timestamp": now.isoformat(),
                        "reason": "entry_blocked_equity_risk_cap",
                        "direction": direction,
                        "size": int(size),
                        "loss_per_contract": round(_loss_per_contract, 4),
                        "max_risk_usd": round(_max_loss_usd, 2),
                        "max_risk_pct": _max_risk_pct,
                        "equity": round(equity_start, 2),
                        "regime": regime_overrides.regime_name,
                        "thought": f"Even 1 contract risks ${_loss_per_contract:.2f} > ${_max_loss_usd:.2f} ({_max_risk_pct*100:.0f}% of ${equity_start:.0f} equity) — blocking entry.",
                    })
                    save_state(state)
                    return

        # --- Multi-contract unlock: FULL quality + expansion → can go to 2 ---
        _mc_cfg = (ps_cfg.get("multi_contract") or {}) if isinstance(ps_cfg.get("multi_contract"), dict) else {}
        if _mc_cfg.get("enabled", False) and size == 1 and _cs_val > 0:
            _mc_min_tier = str(_mc_cfg.get("min_quality", "FULL")).upper()
            _mc_require_exp = bool(_mc_cfg.get("require_expansion", True))
            _mc_max = int(_mc_cfg.get("max_contracts_unlock", 2) or 2)
            _mc_buffer = float(_mc_cfg.get("margin_buffer_pct", 0.20) or 0.20)
            _tier_ok = _TIER_RANK.get(quality_tier, 0) >= _TIER_RANK.get(_mc_min_tier, 2)
            _regime_ok = (not _mc_require_exp) or regime_overrides.regime_name == "expansion"
            if _tier_ok and _regime_ok:
                # Estimate margin needed: notional / leverage per contract
                _est_margin_1 = (price * _cs_val / max(leverage, 1)) if price > 0 else 0
                _est_margin_n = _est_margin_1 * _mc_max
                _required_with_buffer = _est_margin_n * (1 + _mc_buffer)
                # Also check: total risk for N contracts must stay under equity risk cap
                _risk_n = _loss_per_contract * _mc_max if _loss_per_contract > 0 else 0
                if equity_start >= _required_with_buffer and _risk_n <= _max_loss_usd:
                    sizing_meta["multi_contract_unlock"] = True
                    sizing_meta["multi_contract_from"] = size
                    sizing_meta["multi_contract_to"] = _mc_max
                    sizing_meta["est_margin_total"] = round(_est_margin_n, 2)
                    sizing_meta["equity_headroom"] = round(equity_start - _required_with_buffer, 2)
                    size = _mc_max

        # --- AI Executive Size Override ---
        # If Claude specifies a 'size' in its directive, use it (capped by allocation/margin limits).
        if _ai_exec_override and _ai_allow_size_override and _ai_directive:
            _ai_size = int(_ai_directive.get("size") or 0)
            if 1 <= _ai_size <= 10:
                sizing_meta["ai_requested_size"] = _ai_size
                sizing_meta["pre_ai_size"] = size
                size = _ai_size

        _growth_stage_max = int(sizing_meta.get("growth_stage_max_contracts") or 0)
        if _growth_stage_max > 0 and size > _growth_stage_max:
            sizing_meta["growth_stage_cap_original"] = size
            sizing_meta["growth_stage_cap_reduced"] = _growth_stage_max
            size = _growth_stage_max

        _pb_max = int(_margin_window_playbook.get("max_new_contracts") or 0)
        if _pb_max > 0 and size > _pb_max:
            sizing_meta["margin_playbook_cap_original"] = size
            sizing_meta["margin_playbook_cap_reduced"] = _pb_max
            sizing_meta["margin_playbook_label"] = _margin_window_playbook.get("label")
            size = _pb_max
        if size > 1 and not bool(_margin_window_playbook.get("allow_multi_contract")):
            sizing_meta["margin_playbook_multi_contract_blocked"] = True
            sizing_meta["margin_playbook_label"] = _margin_window_playbook.get("label")
            sizing_meta["margin_playbook_notes"] = _margin_window_playbook.get("notes")
            size = 1

        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "dynamic_sizing",
            "recovery_mode": recovery_info.get("mode", "NORMAL"),
            "regime": regime_overrides.regime_name,
            "quality_tier": quality_tier,
            **sizing_meta,
        })

    # PLRL-3 initial sizing (always logged; only enforced when plrl3.enforcement=live).
    plrl_cfg = (config.get("plrl3") or {}) if isinstance(config.get("plrl3"), dict) else {}
    if (not paper) and bool(plrl_cfg.get("enabled", False)):
        enforcement = str(plrl_cfg.get("enforcement", "log_only")).lower().strip()
        strict = bool(plrl_cfg.get("strict_initial_sizing", True))
        try:
            add_muls = list(plrl_cfg.get("add_multipliers", [2, 4, 8]) or [])
            total_mult = 1 + sum(int(x) for x in add_muls[: int(plrl_cfg.get("max_rescues", 3) or 3)] if int(x) > 0)
        except Exception:
            total_mult = 15
        bs = balance_summary if isinstance(balance_summary, dict) else (api.get_futures_balance_summary() or {})
        details = api.get_product_details(product_id) or {}
        init_n, info = compute_initial_contracts_plrl3(
            balance_summary=bs,
            product_details=details,
            direction=direction,
            price=float(price),
            mr_max_allowed=float(plrl_cfg.get("mr_max_allowed", 0.95) or 0.95),
            total_multiplier=int(plrl_cfg.get("total_multiplier", total_mult) or total_mult),
        )
        log_plrl3({
            "timestamp": now.isoformat(),
            "strategy": "PLRL-3",
            "action": "SIZING",
            "product_id": product_id,
            "direction": direction,
            "price": float(price),
            "recommended_initial_contracts": int(init_n),
            "strict": strict,
            "enforcement": enforcement,
            "info": info,
        })
        if enforcement == "live" and strict and int(init_n) <= 0 and not _ai_exec_override:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "plrl3_block_entry_sizing",
                "product_id": product_id,
                "price": float(price),
                "info": info,
            })
            save_state(state)
            return
        if enforcement == "live" and int(init_n) > 0:
            size = int(init_n)

    # Per-bot capital allocation cap (supports running trend + MR bots at 12.5% each).
    # For small/growth accounts, skip if equity < 2x margin per contract (let exchange decide).
    risk_cfg = (config.get("risk") or {}) if isinstance(config.get("risk"), dict) else {}
    alloc_pct = float(risk_cfg.get("capital_allocation_pct", 0.0) or 0.0)
    if (not paper) and alloc_pct > 0 and product_id and direction:
        total_funds_for_margin = _to_float(((mp_decision.metrics or {}) if mp_decision else {}).get("total_funds_for_margin"), 0.0) or 0.0
        if total_funds_for_margin <= 0:
            bs_alloc = balance_summary if isinstance(balance_summary, dict) else (api.get_futures_balance_summary() or {})
            total_funds_for_margin = float(_extract_total_funds_for_margin(bs_alloc) or 0.0)
        # Include spot balances (USDC/USD) that auto-transfer will move to derivatives
        # Without this, sizing only sees derivatives wallet and caps at 1 contract
        try:
            _spot_cash = state.get("last_spot_cash_map") or {}
            _spot_total = sum(float(v) for v in _spot_cash.values() if v)
            _reserve = float((config.get("futures_funding") or {}).get("spot_reserve_floor_usd", 5) or 5)
            _transferable = max(0, _spot_total - _reserve)
            if _transferable > 10:  # only if meaningful amount in spot
                total_funds_for_margin += _transferable
        except Exception:
            pass
        one_margin = api.estimate_required_margin(product_id, 1, direction, price=price) if product_id else {}
        req_1 = _to_float((one_margin or {}).get("required_margin"), 0.0) or 0.0
        alloc_budget = total_funds_for_margin * alloc_pct if total_funds_for_margin > 0 else 0.0
        max_alloc_contracts = int(alloc_budget // req_1) if req_1 > 0 else 0
        # Growth mode: if account can't even afford 1 contract via pre-check,
        # skip the allocation gate and let the exchange margin check decide.
        if max_alloc_contracts <= 0 and total_funds_for_margin > 0 and req_1 > 0:
            ratio = total_funds_for_margin / req_1
            if ratio >= 0.85:
                # Close enough — let the exchange decide, force 1 contract
                max_alloc_contracts = 1
                size = 1
                log_decision(config, {
                    "timestamp": now.isoformat(),
                    "reason": "growth_mode_override_allocation",
                    "total_funds": total_funds_for_margin,
                    "required_per_contract": req_1,
                    "ratio": round(ratio, 3),
                })
        if max_alloc_contracts <= 0 and not _ai_exec_override:
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "entry_blocked_allocation",
                    "capital_allocation_pct": alloc_pct,
                    "total_funds_for_margin": total_funds_for_margin,
                    "required_margin_per_contract": req_1,
                    "allocation_budget": alloc_budget,
                },
            )
            save_state(state)
            return
        if size > max_alloc_contracts:
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "entry_size_capped_allocation",
                    "requested_size": int(size),
                    "capped_size": int(max_alloc_contracts),
                    "capital_allocation_pct": alloc_pct,
                    "allocation_budget": alloc_budget,
                    "required_margin_per_contract": req_1,
                },
            )
            size = int(max_alloc_contracts)

    api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
    # Futures margin / funding separation
    funding_cfg = config.get("futures_funding", {})
    funding_prefs = _funding_preferences(funding_cfg)
    enforce_funding = bool(funding_cfg.get("enforce", False))
    margin_ok, margin_info = api.ensure_futures_margin(
        product_id=product_id,
        size=size,
        direction=direction,
        buffer_pct=float(funding_cfg.get("buffer_pct", 0.10)),
        reserve_usd=float(funding_cfg.get("reserve_usd", 0.0)),
        auto_transfer=bool(funding_cfg.get("auto_transfer", False)),
        currency=str(funding_cfg.get("currency", "USDC")),
        preferred_currencies=funding_prefs,
        conversion_cost_bps=float(funding_cfg.get("conversion_cost_bps", 0.0) or 0.0),
        spot_reserve_floor_usd=float(funding_cfg.get("spot_reserve_floor_usd", 0.0)),
        max_transfer_usd=float(funding_cfg.get("max_transfer_per_day_usd", 0.0) or 0.0),
        transfer_used_usd=transfers_today,
    )
    _record_funding_outcome(
        config=config,
        state=state,
        durable=durable,
        now=now,
        context="entry",
        margin_ok=margin_ok,
        margin_info=margin_info,
    )
    if enforce_funding and not margin_ok and not _ai_exec_override:
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "insufficient_futures_margin",
            "product_id": product_id,
            "price": price,
            "margin_info": margin_info,
        })
        save_state(state)
        return

    # Risk/target budget checks
    contract_size = margin_info.get("contract_size") if margin_info else None
    risk_cfg = config.get("risk_profile", {})
    risk_pct = float(risk_cfg.get("risk_pct", 0.0) or 0.0)
    target_pct = float(risk_cfg.get("target_pct", 0.0) or 0.0)
    if equity_start and contract_size:
        risk_budget = equity_start * risk_pct
        risk_usd = abs(price - stop_price) * float(contract_size) * size
        if risk_budget and risk_usd > risk_budget and not _ai_exec_override:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "risk_budget_exceeded",
                "risk_usd": risk_usd,
                "risk_budget": risk_budget,
                "product_id": product_id,
            })
            save_state(state)
            return

        tp_plan = tp_prices(
            price,
            leverage,
            direction,
            config["exits"]["tp1_move"],
            config["exits"]["tp2_move"],
            config["exits"]["tp3_move"],
            full_close_at_tp1=config["exits"]["tp_full_close_if_single_contract"],
        )
        tp_prices_list = [tp_plan.tp1, tp_plan.tp2, tp_plan.tp3]
        pnls = []
        for tp in tp_prices_list:
            if tp is None:
                continue
            raw = (tp - price) * float(contract_size) * size
            pnl = -raw if direction == "short" else raw
            pnls.append(pnl)
        max_tp_pnl = max(pnls) if pnls else 0.0
        target_budget = equity_start * target_pct
        if target_budget and max_tp_pnl < target_budget and not _ai_exec_override:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "target_unreachable",
                "max_tp_pnl": max_tp_pnl,
                "target_budget": target_budget,
                "product_id": product_id,
            })
            save_state(state)
            return

    # Expected value filter (fees/slippage/funding aware).
    ev_cfg = (v4_cfg.get("ev") or {}) if isinstance(v4_cfg.get("ev"), dict) else {}
    fee_model = str(ev_cfg.get("fee_model", "balanced") or "balanced").lower().strip()
    maker_fee = float(ev_cfg.get("maker_fee_rate", 0.00085) or 0.00085)
    taker_fee = float(ev_cfg.get("taker_fee_rate", 0.00090) or 0.00090)
    slippage = float(ev_cfg.get("slippage_pct", 0.0002) or 0.0002)
    if fee_model in ("conservative", "taker"):
        maker_fee = taker_fee
        slippage = max(slippage, 0.0005)
    elif fee_model in ("maker_bias", "maker"):
        slippage = min(slippage, 0.0002)
    atr_now = atr(df_15m, 14)
    atr_value = _to_float(atr_now.iloc[-1] if len(atr_now) else None, 0.0) or 0.0
    ev_snapshot = None
    # Fetch live profit_factor (cached, no disk read if <30s stale) for EV model
    _ev_pf = 0.0
    try:
        _ev_re = get_rolling_expectancy(LOGS_DIR / "trades.csv", lookback=20)
        _ev_pf = float(_ev_re.get("profit_factor", 0.0) or 0.0)
        if _ev_pf >= 999.0:
            _ev_pf = 0.0
    except Exception:
        pass
    if contract_size and atr_value > 0 and selected_v4:
        ev_snapshot = expected_value_v4(
            score=float((selected_v4 or {}).get("score") or 0.0),
            regime=str((selected_v4 or {}).get("regime") or "mean_reversion"),
            atr_value=float(atr_value),
            price=float(price),
            contract_size=float(contract_size),
            size=int(size),
            maker_fee_rate=maker_fee,
            taker_fee_rate=taker_fee,
            slippage_pct=slippage,
            funding_pct=float(ev_cfg.get("funding_pct", 0.0) or 0.0),
            min_ev_usd=float(ev_cfg.get("min_ev_usd", 0.0) or 0.0),
            profit_factor=_ev_pf,
            tp1_price=float(tp_plan.tp1) if tp_plan else 0.0,
            stop_price=float(stop_price) if stop_price else 0.0,
            direction=str(direction or ""),
        )
        ev_snapshot["fee_model"] = fee_model
        if not bool(ev_snapshot.get("pass")) and not _ai_exec_override:
            log_decision(
                config,
                {
                    "timestamp": now.isoformat(),
                    "reason": "ev_block_entry",
                    "product_id": product_id,
                    "direction": direction,
                    "ev": ev_snapshot,
                },
            )
            save_state(state)
            return

    # --- Live telemetry snapshot (consumed by dashboard / monitoring) ---
    try:
        _atr_ratio_telem = None
        try:
            _atr_s2 = atr(df_15m, 14)
            _atr_v2 = float(_atr_s2.iloc[-1]) if len(_atr_s2) and not pd.isna(_atr_s2.iloc[-1]) else 0.0
            _atr_m2 = float(_atr_s2.rolling(20).mean().iloc[-1]) if len(_atr_s2) >= 20 and not pd.isna(_atr_s2.rolling(20).mean().iloc[-1]) else _atr_v2
            _atr_ratio_telem = round(_atr_v2 / _atr_m2, 3) if _atr_m2 > 0 else None
        except Exception:
            pass
        _kelly_mult_telem = None
        try:
            _re_telem = get_rolling_expectancy(LOGS_DIR / "trades.csv", lookback=20)
            _kelly_mult_telem, _ = kelly_size_multiplier(_re_telem)
        except Exception:
            pass
        write_cycle_telemetry(
            timestamp_iso=now.isoformat(),
            price=float(price),
            regime=str((regime_v4 or {}).get("regime", "neutral")),
            vol_phase=str((expansion_state or {}).get("phase", "COMPRESSION")),
            active_lane=lane_result.lane if lane_result else None,
            score=int((selected_v4 or {}).get("score") or 0) if selected_v4 else None,
            threshold=int((selected_v4 or {}).get("threshold") or 0) if selected_v4 else None,
            score_pass=bool(score_gate_pass),
            ev_usd=float(ev_snapshot.get("ev_usd") or 0.0) if ev_snapshot else None,
            ev_pass=bool(ev_snapshot.get("pass")) if ev_snapshot else None,
            direction=direction,
            consensus={
                "count": consensus_result.consensus_count if consensus_result else 0,
                "bonus": consensus_result.bonus if consensus_result else 0,
                "lanes": consensus_result.confirming_lanes if consensus_result else [],
                "reason": consensus_result.reason if consensus_result else "",
            },
            kelly_mult=_kelly_mult_telem,
            vol_atr_ratio=_atr_ratio_telem,
            adaptive_threshold=adaptive_threshold,
            vol_adaptive_threshold=vol_adaptive_threshold,
            p_win=float(ev_snapshot.get("p_win") or 0.0) if ev_snapshot else None,
            profit_factor_used=float(ev_snapshot.get("profit_factor_used") or 0.0) if ev_snapshot and ev_snapshot.get("profit_factor_used") else None,
            btc_mod=btc_signal.score_modifier if btc_signal else 0,
            contract_mod=contract_mod.bonus if contract_mod else 0,
            alignment_mod=alignment_mod.bonus if alignment_mod else 0,
            inst_mod=inst_mod.bonus if inst_mod else 0,
            has_position=False,
        )
    except Exception:
        pass

    # ── AI Advisor: pre-entry evaluation ─────────────────────────────
    # Fire background AI call (result available NEXT cycle).
    # Check PREVIOUS cycle's cached insight — skip if AI says so.
    ai_advisor.evaluate_entry(decision, state, df_15m=df_15m, df_1h=df_1h, regime_v4=regime_v4, expansion_state=expansion_state)
    gemini_advisor.evaluate_entry(decision, state, df_15m=df_15m, df_1h=df_1h, regime_v4=regime_v4, expansion_state=expansion_state)
    _ai_cfg = config.get("ai") or {}
    _ai = ai_advisor.get_cached_insight("entry_eval")
    if _ai and _ai.get("verdict") == "skip" and float(_ai.get("confidence", 0)) >= float(_ai_cfg.get("skip_confidence_threshold", 0.7)):
        log_decision(config, {
            "timestamp": now.isoformat(),
            "reason": "ai_skip_entry",
            "ai_insight": _ai,
            "direction": direction,
            "entry_type": entry.get("type") if entry else None,
            "score": int((selected_v4 or {}).get("score") or 0),
        })
        save_state(state)
        return
    # AI score adjustment (nudge score, recheck threshold)
    _ai_adj = int((_ai or {}).get("score_adjustment", 0))
    _max_adj = int(_ai_cfg.get("max_score_adjustment", 10))
    _ai_adj = max(-_max_adj, min(_max_adj, _ai_adj))
    if _ai_adj != 0 and selected_v4:
        _orig_score = int(selected_v4.get("score") or 0)
        selected_v4["score"] = _orig_score + _ai_adj
        selected_v4["ai_score_adjustment"] = _ai_adj
        _thresh = int(selected_v4.get("threshold") or 75)
        if selected_v4["score"] < _thresh:
            log_decision(config, {
                "timestamp": now.isoformat(),
                "reason": "ai_score_adjusted_below_threshold",
                "original_score": _orig_score,
                "adjusted_score": selected_v4["score"],
                "ai_adjustment": _ai_adj,
                "threshold": _thresh,
            })
            save_state(state)
            return

    # Idempotency: suppress repeated entry intents in a short window.
    fingerprint = f"{product_id}|{direction}|{size}|{round(float(price), 6)}|{entry.get('type')}|{int((selected_v4 or {}).get('score') or 0)}"
    if _is_duplicate_order(state, fingerprint, now, window_sec=int(v4_cfg.get("entry_idempotency_sec", 90) or 90)):
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "duplicate_entry_suppressed",
                "fingerprint": fingerprint,
            },
        )
        save_state(state)
        return
    om = OrderManager(api, paper=paper)
    side = "BUY" if direction == "long" else "SELL"
    # Attach exchange-native stop/TP triggers so the position is protected if bot cycle is interrupted.
    tp_attach = None
    try:
        exits_cfg = config.get("exits", {}) if isinstance(config.get("exits"), dict) else {}
        if bool(exits_cfg.get("attach_exchange_tp", True)):
            tp_seed = tp_prices(
                price,
                leverage,
                direction,
                exits_cfg.get("tp1_move"),
                exits_cfg.get("tp2_move"),
                exits_cfg.get("tp3_move"),
                full_close_at_tp1=bool(exits_cfg.get("tp_full_close_if_single_contract", False)),
            )
            tp_attach = tp_seed.tp1
    except Exception:
        tp_attach = None
    # AI Executive: override TP with Claude's take_profit_price if set
    _ai_tp = float((ai_advisor.get_directive() or {}).get("take_profit_price", 0) or 0)
    if _ai_initiated and _ai_tp > 0:
        tp_attach = _ai_tp
    _entry_preflight = _build_entry_preflight_snapshot(
        config,
        api,
        product_id=product_id,
        direction=direction,
        size=int(size),
        entry_price=float(price),
        stop_loss=stop_price,
        take_profit=tp_attach,
        attach_exchange_tp=bool(exits_cfg.get("attach_exchange_tp", True)),
    )
    if not bool(_entry_preflight.get("ok")):
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_preflight_block",
                "product_id": product_id,
                "direction": direction,
                "entry_type": entry.get("type") if isinstance(entry, dict) else None,
                "preflight": _entry_preflight,
            },
        )
        save_state(state)
        return
    # Generate strategy-tagged clientOrderId for order fingerprinting
    _entry_type_tag = str((entry or {}).get("type") or "unknown")[:12]
    _lane_tag = str((lane_result.lane if lane_result else "X"))[:2]
    _ts_tag = int(now.timestamp() * 1000)
    _client_oid = f"EL_{direction[:1].upper()}_{_lane_tag}_{_entry_type_tag}_{_ts_tag}"
    res = om.place_entry(
        OrderRequest(
            product_id=product_id,
            side=side,
            size=size,
            leverage=leverage,
            stop_loss=stop_price,
            take_profit=tp_attach,
            client_order_id=_client_oid,
        )
    )
    log_fill(
        {
            "timestamp": now.isoformat(),
            "reason": "entry",
            "product_id": product_id,
            "direction": direction,
            "size": int(size),
            "order_id": res.order_id,
            "client_order_id": _client_oid,
            "ok": bool(res.success),
            "message": res.message,
            "exchange_tp": tp_attach,
            "entry_preflight": _entry_preflight,
            "ev": ev_snapshot,
        }
    )
    if not bool(res.success):
        log_decision(
            config,
            {
                "timestamp": now.isoformat(),
                "reason": "entry_order_failed",
                "product_id": product_id,
                "direction": direction,
                "size": int(size),
                "order_id": res.order_id,
                "message": res.message,
            },
        )
        log_signal({
            "timestamp": now.isoformat(),
            "type": "entry_order_failed",
            "product_id": product_id,
            "direction": direction,
            "size": int(size),
            "order_id": res.order_id,
            "message": res.message,
        })
        save_state(state)
        return

    # --- Fill verification: confirm the entry order actually filled on Coinbase ---
    _entry_fill = verify_fill(api, res.order_id) if res.order_id else None
    _entry_fill_verified = bool(_entry_fill and _entry_fill.get("filled"))
    _entry_fill_price = float(_entry_fill.get("average_filled_price") or 0) if _entry_fill else 0
    _entry_fees = float(_entry_fill.get("total_fees") or 0) if _entry_fill else 0
    # Use exchange fill price when available; fall back to candle/mark price
    _verified_entry_price = _entry_fill_price if _entry_fill_price > 0 else price
    _protection_state = _inspect_entry_protection(
        api,
        product_id=product_id,
        order_id=res.order_id,
        attach_exchange_tp=bool(exits_cfg.get("attach_exchange_tp", True)),
        order_message=res.message,
    )

    if not _entry_fill_verified and res.order_id:
        # Order sent but not yet confirmed as filled — save for next-cycle retry
        _pending_position_seed = {
            "product_id": product_id,
            "entry_time": now.isoformat(),
            "entry_price": float(price),
            "direction": direction,
            "size": size,
            "base_size": size,
            "leverage": leverage,
            "stop_loss": stop_price,
            "contract_size": contract_size,
            "rescue_done": False,
            "breakout_type": breakout_type,
            "breakout_tf": breakout_tf,
            "entry_type": entry.get("type"),
            "strategy_regime": str((selected_v4 or {}).get("regime") or ("trend" if breakout_type == "trend" else "mean_reversion")),
            "confluence_score": int((selected_v4 or {}).get("score") or 0),
            "ev_snapshot": ev_snapshot,
            "scale_count": 0,
            "max_unrealized_usd": 0.0,
            "recovery_target_usd": 0.0,
            "is_recovery_trade": bool(recovery_info.get("active", False)),
            "recovery_max_hold_minutes": float(recovery_info.get("max_hold_minutes") or 0) if bool(recovery_info.get("active", False)) else 0,
            "wait_since_last_exit_min": wait_since_last_exit_min,
            "quality_tier": quality_tier,
            "entry_fees_usd": 0.0,
            "entry_order_id": res.order_id,
            "regime_name": regime_overrides.regime_name,
            "regime_time_stop_bars": regime_overrides.time_stop_bars,
            "regime_early_save_bars": regime_overrides.early_save_bars,
            "regime_tp_atr_mult": regime_overrides.tp_atr_mult,
            "lane_v_mode": entry.get("mode"),
            "entry_profile_key": entry.get("entry_profile_key") or entry.get("type"),
            "lane_v_reversal_tp_mode": entry.get("lane_v_reversal_tp_mode") or lane_cfg.get("lane_v_reversal_tp_mode"),
            "estimated_round_trip_fees": 0.0,
            "entry_preflight": _entry_preflight,
            "protection_state": _protection_state,
            "protection_mode": _protection_state.get("mode"),
            "exchange_tp_requested": _protection_state.get("exchange_tp_requested"),
            "exchange_tp_armed": _protection_state.get("exchange_tp_armed"),
            "software_protection_active": _protection_state.get("software_protection_active"),
        }
        log_signal({
            "timestamp": now.isoformat(),
            "type": "entry_fill_unverified",
            "product_id": product_id,
            "direction": direction,
            "size": int(size),
            "order_id": res.order_id,
            "candle_price": price,
            "thought": "entry order sent but fill not confirmed yet — will retry verification next cycle",
        })
        state["_pending_fill_order_id"] = res.order_id
        state["_pending_fill_meta"] = {
            "product_id": product_id, "direction": direction, "size": int(size),
            "stop_price": stop_price, "candle_price": price, "ts": now.isoformat(),
            "entry_type": entry.get("type"), "breakout_type": breakout_type,
            "breakout_tf": breakout_tf, "fingerprint": fingerprint,
            "confluence": {k: v for k, v in entry.get("confluence", {}).items() if v},
            "selected_v4": dict(selected_v4) if isinstance(selected_v4, dict) else None,
            "ev_snapshot": ev_snapshot,
            "entry_preflight": _entry_preflight,
            "protection_state": _protection_state,
            "open_position_seed": _pending_position_seed,
        }
        # FIX: Do not set open_position or send Slack alerts for unverified fills.
        # Prevents phantom trades where reconciler emergency-exits a ghost position.
        save_state(state)
        return

    log_decision(config, {
        "timestamp": now.isoformat(),
        "reason": "entry_fill_check",
        "order_id": res.order_id,
        "fill_verified": _entry_fill_verified,
        "fill_price": _entry_fill_price,
                "fees_usd": _entry_fees,
                "candle_price": price,
                "protection_state": _protection_state,
            })

    wait_since_last_exit_min = _minutes_between(state.get("last_exit_time"), now.isoformat())
    wait_since_last_entry_min = _minutes_between(state.get("last_entry_time"), now.isoformat())
    state["trades"] = int(state.get("trades") or 0) + 1
    state["last_entry_time"] = now.isoformat()
    state["last_entry_type"] = entry.get("type")
    if entry.get("type") == "liquidity_sweep":
        state["last_liquidity_sweep_anchor"] = float(entry.get("sweep_level") or entry.get("target_cluster_price") or 0.0)
    _update_cooldown(state, now, config["risk"]["cooldown_minutes"])
    state["last_order_fingerprint"] = fingerprint
    state["last_order_ts"] = now.isoformat()
    save_state(state)
    durable.log_event("entered_position", {"product_id": product_id, "direction": direction, "size": size, "paper": bool(paper), "order_id": res.order_id})

    # Recovery Mode: tighter TP distances for quicker profits
    _tp1_move = config["exits"]["tp1_move"]
    _tp2_move = config["exits"]["tp2_move"]
    _tp3_move = config["exits"]["tp3_move"]
    _is_recovery_trade = recovery_info.get("active", False)
    if _is_recovery_trade:
        _tp_tight = recovery_info.get("tp_tightness", 0.65)
        _tp1_move = _tp1_move * _tp_tight
        _tp2_move = _tp2_move * _tp_tight
        _tp3_move = _tp3_move * _tp_tight

    # Regime-aware TP scaling: compression → tighter, expansion → wider
    _vol_regime = str(regime_overrides.regime_name or "transition").lower()
    if _vol_regime == "compression":
        _vol_tp_mult = 0.60   # take what you can in chop
    elif _vol_regime == "expansion":
        _vol_tp_mult = 1.35   # let winners run in trend
    else:
        _vol_tp_mult = 1.0
    _tp1_move *= _vol_tp_mult
    _tp2_move *= _vol_tp_mult
    _tp3_move *= _vol_tp_mult

    # Strategy-specific TP profile: each entry type has its own expected move range.
    _entry_profile = _resolve_entry_profile(
        (v4_cfg.get("profit_protection") or {}),
        entry.get("entry_profile_key") or entry.get("type"),
        str((selected_v4 or {}).get("regime") or ("trend" if breakout_type == "trend" else "mean_reversion")),
    )
    _ep_tp_mult = _entry_profile["tp_mult"]
    _tp1_move *= _ep_tp_mult
    _tp2_move *= _ep_tp_mult
    _tp3_move *= _ep_tp_mult

    tp_plan = tp_prices(
        _verified_entry_price,
        leverage,
        direction,
        _tp1_move,
        _tp2_move,
        _tp3_move,
        full_close_at_tp1=config["exits"]["tp_full_close_if_single_contract"],
    )
    log_trade(
        config,
        _with_lifecycle_fields(
            {
                "timestamp": now.isoformat(),
                "product_id": product_id,
                "side": direction,
                "size": size,
                "entry_price": _verified_entry_price,
                "stop_loss": stop_price,
                "tp1": tp_plan.tp1,
                "tp2": tp_plan.tp2,
                "tp3": tp_plan.tp3,
                "paper": paper,
                "result": res.message,
                "order_id": res.order_id,
                "fill_verified": _entry_fill_verified,
                "fees_usd": _entry_fees,
                "confluence": ";".join([k for k, v in entry["confluence"].items() if v]),
                "entry_type": entry["type"],
                "breakout_type": breakout_type,
                "breakout_tf": breakout_tf,
                "strategy_regime": str((selected_v4 or {}).get("regime") or "unknown"),
                "confluence_score": int((selected_v4 or {}).get("score") or 0),
                "score_threshold": (selected_v4 or {}).get("threshold"),
                "ev_usd": (ev_snapshot or {}).get("ev_usd") if isinstance(ev_snapshot, dict) else None,
                "wait_since_last_exit_min": wait_since_last_exit_min,
                "wait_since_last_entry_min": wait_since_last_entry_min,
            },
            entry_time=now.isoformat(),
            wait_since_last_exit_min=wait_since_last_exit_min,
        ),
    )
    # Compute expected hold for Slack timing info
    _entry_exp_hold = None
    _entry_timing_label = ""
    try:
        _trades_path_e = os.path.join(os.path.dirname(__file__), "logs", "trades.csv")
        _trades_for_entry = pd.read_csv(_trades_path_e) if os.path.exists(_trades_path_e) else pd.DataFrame()
        _fake_pos = {"entry_type": entry.get("type", ""), "breakout_tf": breakout_tf, "strategy_regime": str((selected_v4 or {}).get("regime") or ""), "entry_time": now.isoformat()}
        _entry_eta = estimate_close_eta(_fake_pos, _trades_for_entry, now)
        _entry_exp_hold = _entry_eta.get("historical_avg_min")
        _entry_timing_label = f"{breakout_tf} {entry.get('type', '')} {str((selected_v4 or {}).get('regime') or '')}"
    except Exception:
        pass
    slack_alert.trade_entry(
        direction=direction, product_id=product_id, size=size,
        entry_price=_verified_entry_price, stop_loss=stop_price,
        entry_type=entry.get("type", ""), score=int((selected_v4 or {}).get("score") or 0),
        fill_verified=_entry_fill_verified,
        expected_hold_min=_entry_exp_hold,
        timing_label=_entry_timing_label,
        ai_action=(_ai_directive or {}).get("action", ""),
        ai_confidence=(_ai_directive or {}).get("confidence"),
        ai_size=(_ai_directive or {}).get("size"),
        ai_reasoning=(_ai_directive or {}).get("reasoning", ""),
        margin_reason=(margin_info or {}).get("reason", ""),
    )
    # War room: broadcast entry with agent views
    try:
        _wr_views = agent_comms.get_all_assessments() if agent_comms.is_enabled() else {}
        slack_alert.war_room_trade_open(
            direction=direction, entry_price=_verified_entry_price, size=size,
            agent_views=_wr_views,
        )
    except Exception:
        pass
    recovery_cfg = (v4_cfg.get("recovery") or {}) if isinstance(v4_cfg.get("recovery"), dict) else {}
    debt = float(state.get("loss_debt_usd") or 0.0)
    high_quality_score = int(recovery_cfg.get("high_quality_score", 85) or 85)
    recovery_cap = float(recovery_cfg.get("recovery_cap_per_trade", 6.0) or 6.0)
    recovery_target = 0.0
    if debt > 0 and bool(recovery_cfg.get("enabled", True)) and int((selected_v4 or {}).get("score") or 0) >= high_quality_score:
        recovery_target = float(min(debt, recovery_cap))

    # Estimate round-trip fees so profit targets account for real costs
    _ev_cfg = config.get("ev") or {}
    _fee_rate = float(_ev_cfg.get("taker_fee_rate", 0.0009) or 0.0009)
    _contract_notional = float(price) * float(config.get("contract_size", 5000) or 5000) * int(size)
    _est_rt_fees = _contract_notional * _fee_rate * 2  # entry + exit

    state["open_position"] = {
        "product_id": product_id,
        "entry_time": now.isoformat(),
        "entry_price": _verified_entry_price,
        "direction": direction,
        "size": size,
        "base_size": size,
        "leverage": leverage,
        "stop_loss": stop_price,
        "tp1": tp_plan.tp1,
        "tp2": tp_plan.tp2,
        "tp3": tp_plan.tp3,
        "adverse_bars": 0,
        "contract_size": contract_size,
        "rescue_done": False,
        "breakout_type": breakout_type,
        "breakout_tf": breakout_tf,
        "entry_type": entry.get("type"),
        "strategy_regime": str((selected_v4 or {}).get("regime") or ("trend" if breakout_type == "trend" else "mean_reversion")),
        "confluence_score": int((selected_v4 or {}).get("score") or 0),
        "ev_snapshot": ev_snapshot,
        "scale_count": 0,
        "max_unrealized_usd": 0.0,
        "recovery_target_usd": recovery_target,
        "is_recovery_trade": _is_recovery_trade,
        "recovery_max_hold_minutes": float(recovery_info.get("max_hold_minutes") or 0) if _is_recovery_trade else 0,
        "wait_since_last_exit_min": wait_since_last_exit_min,
        "quality_tier": quality_tier,
        "entry_fees_usd": _entry_fees,
        "entry_order_id": res.order_id,
        "entry_fill_verified": _entry_fill_verified,
        "entry_preflight": _entry_preflight,
        "protection_state": _protection_state,
        "protection_mode": _protection_state.get("mode"),
        "exchange_tp_requested": _protection_state.get("exchange_tp_requested"),
        "exchange_tp_armed": _protection_state.get("exchange_tp_armed"),
        "software_protection_active": _protection_state.get("software_protection_active"),
        # Regime overrides (frozen at entry for consistent exit management)
        "regime_name": regime_overrides.regime_name,
        "regime_time_stop_bars": regime_overrides.time_stop_bars,
        "regime_early_save_bars": regime_overrides.early_save_bars,
        "regime_tp_atr_mult": regime_overrides.tp_atr_mult,
        "lane_v_mode": entry.get("mode"),
        "entry_profile_key": entry.get("entry_profile_key") or entry.get("type"),
        "lane_v_reversal_tp_mode": entry.get("lane_v_reversal_tp_mode") or lane_cfg.get("lane_v_reversal_tp_mode"),
        # Entry profit profile (frozen at entry for consistent exit management)
        # Add estimated round-trip fees to min_profit so we never exit "profitable"
        # but actually lose money after Coinbase fees.
        "entry_profile_min_profit_usd": _entry_profile["min_profit_usd"] + _est_rt_fees,
        "entry_profile_decay_pct": _entry_profile["decay_pct"],
        "entry_profile_tp_mult": _entry_profile["tp_mult"],
        "estimated_round_trip_fees": _est_rt_fees,
    }
    # Compression range: store mid-range target for TP override
    if entry.get("type") == "compression_range" and entry.get("mid_range"):
        state["open_position"]["compression_range_target"] = float(entry["mid_range"])
    # Slow Bleed Hunter: store bleed context for micro-trailing exit
    if entry.get("type") == "slow_bleed_hunter":
        state["open_position"]["bleed_bars"] = int(entry.get("bleed_bars") or 0)
        state["open_position"]["avg_bar_size"] = float(entry.get("avg_bar_size") or 0)
    # Fib retrace: store fib TP and swing data for exit management
    if entry.get("type") == "fib_retrace":
        if entry.get("fib_tp_price"):
            state["open_position"]["fib_tp_price"] = float(entry["fib_tp_price"])
        if entry.get("fib_target_name"):
            state["open_position"]["fib_target_name"] = str(entry["fib_target_name"])
        if entry.get("swing_high"):
            state["open_position"]["swing_high"] = float(entry["swing_high"])
        if entry.get("swing_low"):
            state["open_position"]["swing_low"] = float(entry["swing_low"])
    if entry.get("type") == "liquidity_sweep":
        if entry.get("fail_fast_bars"):
            state["open_position"]["regime_time_stop_bars"] = min(
                int(state["open_position"].get("regime_time_stop_bars") or regime_overrides.time_stop_bars),
                int(entry.get("fail_fast_bars") or regime_overrides.time_stop_bars),
            )
        if entry.get("target_cluster_price"):
            state["open_position"]["target_cluster_price"] = float(entry["target_cluster_price"])
        if entry.get("sweep_level"):
            state["open_position"]["sweep_level"] = float(entry["sweep_level"])
    try:
        plrl_cfg = (config.get("plrl3") or {}) if isinstance(config.get("plrl3"), dict) else {}
        if (not paper) and bool(plrl_cfg.get("enabled", False)):
            state["open_position"]["plrl3_initial_contracts"] = int(size)
            state["open_position"]["plrl3_rescue_step"] = 0
    except Exception:
        pass
    # Use actual exchange fill price instead of spot price for accurate PnL
    if not paper:
        try:
            import time as _t
            _t.sleep(0.5)  # brief delay for exchange settlement
            _exch_pos = api.get_position(product_id)
            if _exch_pos:
                _fill_price = float(_exch_pos.get("avg_entry_price") or 0)
                if _fill_price > 0:
                    state["open_position"]["entry_price"] = _fill_price
        except Exception:
            pass
    # Recovery Mode: count this attempt and track post-TP bias trades
    if _is_recovery_trade:
        state["recovery_attempts"] = int(state.get("recovery_attempts") or 0) + 1
    if state.get("post_tp_bias_side"):
        state["post_tp_bias_trades_since"] = int(state.get("post_tp_bias_trades_since") or 0) + 1

    save_state(state)
    durable.set_kv("open_position", state["open_position"])

    # Post trade open to Slack with agent analysis
    try:
        slack_intel.post_cycle_intel(log_payload, event="trade_open")
    except Exception:
        pass


_shutdown_logged = False


def _handle_shutdown(signum, frame):
    global _shutdown_logged
    if not _shutdown_logged:
        _shutdown_logged = True
        try:
            cfg = load_config()
            log_decision(cfg, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "clean_shutdown",
                "signal": _signal.Signals(signum).name if signum else "unknown",
            })
        except Exception:
            pass
    raise SystemExit(0)


def main() -> None:
    _signal.signal(_signal.SIGTERM, _handle_shutdown)
    _signal.signal(_signal.SIGINT, _handle_shutdown)

def _build_smoke_check_preview(config: dict, api: CoinbaseAdvanced, direction: str = "long", size: int = 1) -> dict:
    selection = api.select_xlm_product(config.get("selector", {}), direction=direction)
    product_id = selection["product_id"] if selection else None
    if not product_id:
        return {"ok": False, "reason": "smoke_check_no_product", "direction": direction}

    info = api.get_product_details(product_id) or {}
    _pricebook = info.get("pricebook") if isinstance(info.get("pricebook"), dict) else {}
    entry_price = _to_float(
        info.get("mid_market_price")
        or info.get("price")
        or info.get("mark_price")
        or _pricebook.get("mid_price"),
        0.0,
    )
    if entry_price <= 0:
        margin_probe = api.estimate_required_margin(product_id, size=max(int(size), 1), direction=direction)
        notional = _to_float(margin_probe.get("notional"), 0.0)
        contract_size = _to_float(info.get("contract_size"), 0.0)
        if contract_size > 0 and notional > 0:
            entry_price = notional / (contract_size * max(int(size), 1))
    if entry_price <= 0:
        return {"ok": False, "reason": "smoke_check_no_price", "product_id": product_id, "direction": direction}

    leverage = min(int(config.get("leverage", 1) or 1), 4)
    exits_cfg = config.get("exits", {}) if isinstance(config.get("exits"), dict) else {}
    risk_cfg = config.get("risk", {}) if isinstance(config.get("risk"), dict) else {}
    stop_pct = float(risk_cfg.get("smoke_check_stop_pct", 0.0025) or 0.0025)
    stop_loss = entry_price * (1 - stop_pct) if direction == "long" else entry_price * (1 + stop_pct)
    tp_seed = tp_prices(
        entry_price,
        leverage,
        direction,
        exits_cfg.get("tp1_move"),
        exits_cfg.get("tp2_move"),
        exits_cfg.get("tp3_move"),
        full_close_at_tp1=bool(exits_cfg.get("tp_full_close_if_single_contract", False)),
    )
    attach_exchange_tp = bool(exits_cfg.get("attach_exchange_tp", True))
    take_profit = tp_seed.tp1 if attach_exchange_tp else None
    bracket_valid = bool(
        (direction == "long" and stop_loss < entry_price and (take_profit is None or take_profit > entry_price))
        or (direction == "short" and stop_loss > entry_price and (take_profit is None or take_profit < entry_price))
    )
    client_order_id = f"SMOKE_{direction[:1].upper()}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    req = OrderRequest(
        product_id=product_id,
        side="BUY" if direction == "long" else "SELL",
        size=max(int(size), 1),
        leverage=leverage,
        stop_loss=stop_loss,
        take_profit=take_profit,
        client_order_id=client_order_id,
    )
    res = OrderManager(api, paper=True).place_entry(req)
    margin = api.estimate_required_margin(product_id, size=max(int(size), 1), direction=direction, price=entry_price)
    protection = _inspect_entry_protection(
        api,
        product_id=product_id,
        order_id=res.order_id,
        attach_exchange_tp=bool(attach_exchange_tp),
        order_message=res.message,
    )
    preflight = _build_entry_preflight_snapshot(
        config,
        api,
        product_id=product_id,
        direction=direction,
        size=max(int(size), 1),
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        attach_exchange_tp=bool(attach_exchange_tp),
    )
    return {
        "ok": bool(res.success) and bool(preflight.get("ok")),
        "direction": direction,
        "product_id": product_id,
        "product_available": api.is_product_available(product_id),
        "entry_price": round(entry_price, 6),
        "stop_loss": round(stop_loss, 6),
        "take_profit": round(take_profit, 6) if take_profit is not None else None,
        "bracket_valid": bracket_valid,
        "attach_exchange_tp": attach_exchange_tp,
        "client_order_id": client_order_id,
        "paper_result": res.message,
        "paper_order_id": res.order_id,
        "preflight": preflight,
        "protection": protection,
        "required_margin": margin.get("required_margin"),
        "margin_rate": margin.get("margin_rate"),
        "margin_window": margin.get("margin_window"),
        "notional": margin.get("notional"),
        "spread_pct": api.get_spread_pct(config.get("data_product_id", "XLM-USD")),
    }


def _cli_entrypoint() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml", help="config file path (relative to xlm_bot/ or absolute)")
    parser.add_argument("--paper", action="store_true")
    parser.add_argument("--test-fire", action="store_true", help="paper-only: force a single test order")
    parser.add_argument("--live-check", action="store_true", help="validate API connectivity without trading")
    parser.add_argument("--live-test-fire", action="store_true", help="live: force a single order to test error path")
    parser.add_argument("--funding-check", action="store_true", help="log futures margin shortfall without trading")
    parser.add_argument("--smoke-check", action="store_true", help="validate paper entry plus bracket payload without trading")
    parser.add_argument("--i-understand-live", action="store_true", help="required for live orders")
    parser.add_argument("--live", action="store_true", help="override config paper mode for live tests")
    parser.add_argument("--check-last-order", action="store_true", help="check status of last live_test_fire order")
    args = parser.parse_args()
    config = load_config(args.config)
    paper = False if args.live else (args.paper or config.get("paper", True))

    if args.live_check:
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        selection = api.select_xlm_product(config.get("selector", {}), direction="long")
        product_id = selection["product_id"] if selection else None
        spread = api.get_spread_pct(config.get("data_product_id", "XLM-USD"))
        ok = bool(selection) and api.is_product_available(product_id) if product_id else False
        log_decision(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "live_check",
            "product_selected": product_id,
            "product_available": ok,
            "spread_pct": spread,
        })
        return

    if args.funding_check:
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        selection = api.select_xlm_product(config.get("selector", {}), direction="long")
        product_id = selection["product_id"] if selection else None
        if not product_id:
            log_decision(config, {"timestamp": datetime.now(timezone.utc).isoformat(), "reason": "funding_check_no_product"})
            return
        info = api.estimate_required_margin(product_id, size=1, direction="long")
        funding_cfg = config.get("futures_funding", {})
        funding_prefs = _funding_preferences(funding_cfg)
        state = load_state()
        ok, margin_info = api.ensure_futures_margin(
            product_id=product_id,
            size=1,
            direction="long",
            buffer_pct=float(funding_cfg.get("buffer_pct", 0.10)),
            reserve_usd=float(funding_cfg.get("reserve_usd", 0.0)),
            auto_transfer=False,
            currency=str(funding_cfg.get("currency", "USDC")),
            preferred_currencies=funding_prefs,
            conversion_cost_bps=float(funding_cfg.get("conversion_cost_bps", 0.0) or 0.0),
            spot_reserve_floor_usd=float(funding_cfg.get("spot_reserve_floor_usd", 0.0)),
            max_transfer_usd=float(funding_cfg.get("max_transfer_per_day_usd", 0.0) or 0.0),
            transfer_used_usd=float(state.get("transfers_today_usd") or 0.0),
        )
        _record_funding_outcome(
            config=config,
            state=state,
            durable=None,
            now=datetime.now(timezone.utc),
            context="funding_check",
            margin_ok=ok,
            margin_info=margin_info,
        )
        log_decision(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "funding_check",
            "product_id": product_id,
            "ok": ok,
            "required_margin": info.get("required_margin"),
            "notional": info.get("notional"),
            "margin_rate": info.get("margin_rate"),
            "futures_buying_power": margin_info.get("futures_buying_power") if margin_info else None,
            "shortfall": (margin_info.get("needed_total") - margin_info.get("futures_buying_power")) if margin_info else None,
        })
        return

    if args.smoke_check:
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        preview = _build_smoke_check_preview(config, api, direction="long", size=1)
        log_decision(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "smoke_check",
            **preview,
        })
        return

    if args.check_last_order:
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        trades_path = BASE_DIR / config["logging"]["trades_csv"]
        if trades_path.exists():
            with open(trades_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                rows = [r for r in reader if r.get("entry_type") == "live_test_fire"]
            if rows:
                order_id = rows[-1].get("order_id")
                if order_id:
                    status = api.api.get_order(order_id)
                    log_decision(config, {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reason": "check_last_order",
                        "order_id": order_id,
                        "order_status": status,
                    })
        return

    if args.test_fire:
        if not paper:
            log_decision(config, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "test_fire_blocked_not_paper",
            })
            return
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        selection = api.select_xlm_product(config.get("selector", {}), direction="long")
        product_id = selection["product_id"] if selection else None
        if not product_id:
            return
        om = OrderManager(api, paper=True)
        res = om.place_entry(OrderRequest(product_id=product_id, side="BUY", size=1, leverage=min(int(config["leverage"]), 4)))
        log_trade(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "product_id": product_id,
            "side": "long",
            "size": 1,
            "entry_price": "TEST",
            "paper": True,
            "result": res.message,
            "order_id": res.order_id,
            "entry_type": "test_fire",
        })
        return

    if args.live_test_fire:
        if paper or not args.i_understand_live:
            log_decision(config, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "live_test_fire_blocked",
            })
            return
        api = CoinbaseAdvanced(config_path=CRYPTO_BOT_CONFIG)
        selection = api.select_xlm_product(config.get("selector", {}), direction="long")
        product_id = selection["product_id"] if selection else None
        if not product_id:
            log_decision(config, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "live_test_fire_no_product",
            })
            return
        om = OrderManager(api, paper=False)
        res = om.place_entry(OrderRequest(product_id=product_id, side="BUY", size=1, leverage=min(int(config["leverage"]), 4)))
        log_trade(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "product_id": product_id,
            "side": "long",
            "size": 1,
            "entry_price": "LIVE_TEST",
            "paper": False,
            "result": res.message,
            "order_id": res.order_id,
            "entry_type": "live_test_fire",
        })
        return

    if not paper and not args.i_understand_live:
        log_decision(config, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": "live_blocked_missing_flag",
        })
        return

    try:
        decide_and_trade(config, paper=paper)
    except Exception as e:
        # Always emit a decision line so the dashboard shows failures immediately.
        try:
            log_decision(config, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "bot_error",
                "error": str(e),
                "traceback": traceback.format_exc(limit=8),
            })
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
    _cli_entrypoint()
