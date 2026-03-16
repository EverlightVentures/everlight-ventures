"""Live cycle telemetry writer.

Writes data/lane_telemetry.json every bot cycle with real-time state.
Dashboard and external monitoring tools consume this for live display.

Uses atomic write (tmp -> rename) to prevent partial-read by dashboard.
Never raises -- any write failure is silently swallowed.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_TELEMETRY_FILE = Path(__file__).resolve().parent.parent / "data" / "lane_telemetry.json"


def write_cycle_telemetry(
    *,
    timestamp_iso: str,
    price: float,
    regime: str,
    vol_phase: str,
    active_lane: str | None,
    score: int | None,
    threshold: int | None,
    score_pass: bool,
    ev_usd: float | None,
    ev_pass: bool | None,
    direction: str | None,
    consensus: dict | None = None,
    kelly_mult: float | None = None,
    vol_atr_ratio: float | None = None,
    adaptive_threshold: int | None = None,
    vol_adaptive_threshold: int | None = None,
    p_win: float | None = None,
    profit_factor_used: float | None = None,
    btc_mod: int = 0,
    contract_mod: int = 0,
    alignment_mod: int = 0,
    inst_mod: int = 0,
    has_position: bool = False,
    position_pnl: float | None = None,
    extra: dict | None = None,
) -> None:
    """Atomic write of per-cycle telemetry snapshot to data/lane_telemetry.json."""
    payload: dict[str, Any] = {
        "ts": timestamp_iso,
        "ts_unix": time.time(),
        "price": round(price, 6) if price else None,
        "regime": regime,
        "vol_phase": vol_phase,
        "active_lane": active_lane,
        "score": score,
        "threshold": threshold,
        "adaptive_threshold": adaptive_threshold,
        "vol_adaptive_threshold": vol_adaptive_threshold,
        "score_pass": score_pass,
        "ev_usd": round(ev_usd, 4) if ev_usd is not None else None,
        "ev_pass": ev_pass,
        "p_win": round(p_win, 4) if p_win is not None else None,
        "profit_factor_used": round(profit_factor_used, 3) if profit_factor_used is not None else None,
        "direction": direction,
        "consensus": consensus,
        "kelly_mult": kelly_mult,
        "vol_atr_ratio": round(vol_atr_ratio, 3) if vol_atr_ratio is not None else None,
        "score_mods": {
            "btc": btc_mod,
            "contract": contract_mod,
            "alignment": alignment_mod,
            "institutional": inst_mod,
        },
        "has_position": has_position,
        "position_pnl": round(position_pnl, 4) if position_pnl is not None else None,
    }
    if extra:
        payload["extra"] = extra

    try:
        _TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _TELEMETRY_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":"), default=str))
        tmp.replace(_TELEMETRY_FILE)
    except Exception:
        pass
