"""
Position service -- normalise exchange position data for dashboard display.

Display-only; never places orders or modifies bot state.
"""
from __future__ import annotations

from .formatters import safe_float, safe_str


# ---------------------------------------------------------------------------
# Position normalisation
# ---------------------------------------------------------------------------

def normalize_cfm_position(pos_dict: dict) -> dict:
    """Normalise a Coinbase CFM position payload into a dashboard-friendly shape.

    Returns dict with: product_id, direction, contracts, entry_price,
    current_price, unrealized_pnl, raw.
    """
    if not isinstance(pos_dict, dict):
        return {
            "product_id": "?",
            "direction": "?",
            "contracts": None,
            "entry_price": None,
            "current_price": None,
            "unrealized_pnl": None,
            "raw": {},
        }

    p = pos_dict
    pid = safe_str(p.get("product_id")) or "?"
    side = safe_str(p.get("side")).upper()
    direction = "short" if "SHORT" in side else "long" if "LONG" in side else "?"

    contracts = (
        safe_float(p.get("number_of_contracts"), default=None)
        or safe_float(p.get("contracts"), default=None)
        or safe_float(p.get("size"), default=None)
    )
    entry = (
        safe_float(p.get("avg_entry_price"), default=None)
        or safe_float(p.get("average_entry_price"), default=None)
        or safe_float(p.get("entry_price"), default=None)
    )
    cur = (
        safe_float(p.get("current_price"), default=None)
        or safe_float(p.get("mark_price"), default=None)
        or safe_float(p.get("price"), default=None)
    )
    upnl = safe_float(p.get("unrealized_pnl"), default=None)

    return {
        "product_id": pid,
        "direction": direction,
        "contracts": int(contracts) if contracts is not None else None,
        "entry_price": entry,
        "current_price": cur,
        "unrealized_pnl": upnl,
        "raw": p,
    }


# ---------------------------------------------------------------------------
# Order protection summary
# ---------------------------------------------------------------------------

def order_protection_summary(order_dict: dict) -> dict:
    """Extract bracket/trigger status from a Coinbase order payload.

    Returns dict with: status, order_type, trigger_status,
    stop_trigger, take_profit, health.
    """
    if not isinstance(order_dict, dict):
        return {
            "status": "?",
            "order_type": "?",
            "trigger_status": "",
            "stop_trigger": None,
            "take_profit": None,
            "health": "ok",
        }

    o = order_dict
    trig_status = safe_str(o.get("trigger_status"))
    order_type = safe_str(o.get("order_type")) or safe_str(o.get("type")) or "?"
    status = safe_str(o.get("status")) or "?"

    stop = None
    tp = None
    try:
        oc = o.get("order_configuration") or {}
        for key in ("trigger_bracket_gtc", "trigger_bracket_ioc", "trigger_bracket_fok"):
            if key in oc and isinstance(oc.get(key), dict):
                cfg = oc.get(key) or {}
                stop = safe_float(cfg.get("stop_trigger_price") or cfg.get("stop_price"), default=None)
                tp = safe_float(
                    cfg.get("take_profit_price") or cfg.get("limit_price") or cfg.get("tp_price"),
                    default=None,
                )
                break
    except Exception:
        pass

    if stop is None or tp is None:
        try:
            aoc = o.get("attached_order_configuration") or {}
            if isinstance(aoc, dict):
                cfg = aoc.get("trigger_bracket_gtc") or {}
                if isinstance(cfg, dict):
                    if stop is None:
                        stop = safe_float(cfg.get("stop_trigger_price"), default=None)
                    if tp is None:
                        tp = safe_float(cfg.get("limit_price"), default=None)
        except Exception:
            pass

    health = "ok"
    if trig_status and trig_status.upper() != "TRIGGER_STATUS_UNSPECIFIED":
        if "INVALID" in trig_status.upper() or "REJECT" in trig_status.upper():
            health = "bad"
        else:
            health = "warn"

    return {
        "status": status,
        "order_type": order_type,
        "trigger_status": trig_status,
        "stop_trigger": stop,
        "take_profit": tp,
        "health": health,
    }


# ---------------------------------------------------------------------------
# Strategy TP levels
# ---------------------------------------------------------------------------

def strategy_tp_levels(
    entry_px: float,
    direction: str,
    leverage: float,
    config: dict,
) -> dict:
    """Compute TP1/TP2/TP3 prices from entry + config.

    Returns dict with keys tp1, tp2, tp3 (float or None).
    """
    try:
        lev = float(leverage or 1.0)
        if lev <= 0:
            lev = 1.0
    except (TypeError, ValueError):
        lev = 1.0

    exits = config.get("exits", {}) if isinstance(config, dict) else {}
    tp1_move = float(exits.get("tp1_move", 0.20) or 0.20)
    tp2_move = float(exits.get("tp2_move", 0.40) or 0.40)
    tp3_move = float(exits.get("tp3_move", 0.60) or 0.60)

    try:
        px = float(entry_px or 0.0)
        if px <= 0:
            return {"tp1": None, "tp2": None, "tp3": None}
    except (TypeError, ValueError):
        return {"tp1": None, "tp2": None, "tp3": None}

    d = (direction or "").lower()

    def _lvl(move: float) -> float:
        m = float(move) / lev
        if "short" in d:
            return px * (1.0 - m)
        return px * (1.0 + m)

    return {"tp1": _lvl(tp1_move), "tp2": _lvl(tp2_move), "tp3": _lvl(tp3_move)}
