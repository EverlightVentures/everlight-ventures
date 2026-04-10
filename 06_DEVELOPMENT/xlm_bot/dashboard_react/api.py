"""XLM Trading Dashboard API -- FastAPI backend serving bot data as JSON.
Reads from the bot's data files and serves clean, structured endpoints
for the React frontend. Only returns last 24h of data.
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI(title="XLM Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BOT_DIR = Path(os.environ.get("BOT_DIR", "/home/opc/xlm-bot"))
DATA_DIR = BOT_DIR / "data"
LOGS_DIR = BOT_DIR / "logs"
STATIC_DIR = Path(__file__).parent / "dist"
EVERLIGHT_OS_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "everlight_os",
    Path(__file__).resolve().parent.parent / "everlight_os",
    Path("/home/opc/06_DEVELOPMENT/everlight_os"),
    Path("/home/opc/hive_django/everlight_os"),
    Path("/home/opc/hive-ops/django/everlight_os"),
]

for everlight_os_dir in EVERLIGHT_OS_CANDIDATES:
    if everlight_os_dir.exists() and str(everlight_os_dir) not in sys.path:
        sys.path.insert(0, str(everlight_os_dir))

try:
    from neuromorphic.brain_knowledge import get_ai_brain_status, search_ai_brain
except Exception:
    get_ai_brain_status = None
    search_ai_brain = None

def _read_jsonl_tail(path: Path, max_lines: int = 500, max_bytes: int = 512_000) -> list[dict]:
    if not path.exists():
        return []
    size = path.stat().st_size
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(-max_bytes, 2)
            f.readline()
        raw = f.read().decode("utf-8", errors="replace")
    lines = raw.strip().split("\n")[-max_lines:]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except Exception:
            pass
    return result
def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}
def _filter_24h(items: list[dict], ts_key: str = "timestamp") -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return [i for i in items if str(i.get(ts_key, "")) >= cutoff]
@app.get("/api/status")
def get_status():
    tick = _read_json(LOGS_DIR / "live_tick.json")
    state_db = DATA_DIR / "bot_state.db"
    position = None
    margin = None
    if state_db.exists():
        try:
            db = sqlite3.connect(str(state_db))
            for key in ("open_position", "margin_policy"):
                row = db.execute("SELECT value_json, updated_at FROM kv WHERE key=?", (key,)).fetchone()
                if row:
                    val = json.loads(row[0]) if row[0] != "null" else None
                    if key == "open_position":
                        position = val
                    else:
                        margin = val
            db.close()
        except Exception:
            pass
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=5)
    last_decision = decisions[-1] if decisions else {}
    # Get accurate trade count from the shared parser (same source as /daily-summary)
    _real_today, _ = _parse_all_trades_organized()
    _pt_today = (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%d")
    _today_trades = [t for t in _real_today if t.get("date") == _pt_today]
    _today_wins = sum(1 for t in _today_trades if t["result"] == "win")
    _today_losses = sum(1 for t in _today_trades if t["result"] == "loss")
    _today_pnl = sum(t["pnl"] for t in _today_trades)

    return {
        "price": float(tick.get("price", 0)),
        "price_ts": tick.get("timestamp", ""),
        "position": position,
        "margin": margin,
        "last_decision": last_decision,
        "bot_alive": bool(decisions and (datetime.now(timezone.utc) - datetime.fromisoformat(str(decisions[-1].get("timestamp", "2000-01-01T00:00:00+00:00")).replace("Z", "+00:00"))).total_seconds() < 120),
        "trades_today": _today_wins + _today_losses,
        "wins_today": _today_wins,
        "losses_today": _today_losses,
        "pnl_today": round(_today_pnl, 2),
    }
@app.get("/api/decisions")
def get_decisions(limit: int = 200):
    items = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=limit)
    return _filter_24h(items)
_NOISE_EVENTS = {"startup", "manage_open_position", "balance_reconcile", "cash_movement", "market_intel_error"}

@app.get("/api/events")
def get_events(limit: int = 100):
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return []
    try:
        db = sqlite3.connect(str(state_db))
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        # Filter noise in SQL -- startup/manage events outnumber trade events 1000:1
        noise_placeholders = ",".join(["?"] * len(_NOISE_EVENTS))
        params = [cutoff] + list(_NOISE_EVENTS) + [limit]
        rows = db.execute(
            f"SELECT ts, type, payload_json FROM events WHERE ts > ? AND type NOT IN ({noise_placeholders}) ORDER BY id DESC LIMIT ?",
            params
        ).fetchall()
        db.close()
        return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]
    except Exception:
        return []
@app.get("/api/trades")
def get_trades():
    events = get_events(500)
    trades = []
    for e in events:
        if e["type"] in ("entered_position", "exit_position", "exchange_side_close_detected"):
            entry = {"ts": e["ts"], "type": e["type"]}
            entry.update(e.get("payload", {}))
            trades.append(entry)
    return trades
_IQ_REASONS = {
    "unified_score", "unified_hold", "unified_hard_block",
    "position_iq", "entry_fill_check", "exit_fill_check", "exit_order_sent",
    "entry_blocked_preflight", "entry_blocked_no_signal",
    "macro_vision", "hindsight_scan", "trading_mindset",
    "band_navigator_confirmed", "dip_retrace_gate_block",
    "profit_manager_sl_to_be", "profit_manager_trail_tighten",
    "hedge_flip_queued", "divergence_confirmed", "fib_confluence_boost",
}


@app.get("/api/strategy-iq")
def get_strategy_iq():
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=1000)
    decisions_24h = _filter_24h(decisions)

    # Collect meaningful strategy events
    iq_events = []
    stats = {
        "unified_scores": [],
        "entries": 0,
        "exits": 0,
        "holds": 0,
        "blocks": 0,
        "position_iq_actions": {},
        "strategies_seen": {},
        "regimes_seen": {},
        "total_decisions": len(decisions_24h),
    }

    for d in decisions_24h:
        r = str(d.get("reason", ""))

        if r == "unified_score":
            score = d.get("final_score", 0)
            stats["unified_scores"].append(score)
            rec = d.get("recommendation", "")
            entry_type = d.get("entry_type", "unknown")
            stats["strategies_seen"][entry_type] = stats["strategies_seen"].get(entry_type, 0) + 1
            regime = d.get("regime", "")
            if regime:
                stats["regimes_seen"][regime] = stats["regimes_seen"].get(regime, 0) + 1
            iq_events.append(d)

        elif r == "unified_hold":
            stats["holds"] += 1
            iq_events.append(d)

        elif r in ("unified_hard_block", "entry_blocked_preflight"):
            stats["blocks"] += 1
            iq_events.append(d)

        elif r == "position_iq":
            action = d.get("action", "HOLD")
            stats["position_iq_actions"][action] = stats["position_iq_actions"].get(action, 0) + 1
            if action != "HOLD":
                iq_events.append(d)

        elif r in ("entry_fill_check",):
            stats["entries"] += 1
            iq_events.append(d)

        elif r in ("exit_fill_check", "exit_order_sent"):
            stats["exits"] += 1
            iq_events.append(d)

        elif r in _IQ_REASONS:
            iq_events.append(d)

    # Compute summary stats
    scores = stats["unified_scores"]
    avg_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    enter_count = sum(1 for s in scores if s >= 60)
    hold_count = sum(1 for s in scores if s < 60)

    return {
        "summary": {
            "total_decisions": stats["total_decisions"],
            "unified_scores_count": len(scores),
            "avg_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "enter_signals": enter_count,
            "hold_signals": hold_count,
            "entries": stats["entries"],
            "exits": stats["exits"],
            "blocks": stats["blocks"],
            "position_iq": stats["position_iq_actions"],
            "strategies_seen": stats["strategies_seen"],
            "regimes_seen": stats["regimes_seen"],
        },
        "events": iq_events[-60:],
    }
_ENTRY_TYPE_TF = {
    "htf_swing": "4h",
    "htf_breakout_continuation": "4h",
    "range_fvg_retest": "1h",
    "hourly_continuation": "1h",
    "opening_range_breakout": "1h",
}
# Coinbase Exchange API supported granularities: 60, 300, 900, 3600, 21600, 86400
# 4h is NOT supported -- use 1h with more candles to cover 4h of data
_GRANULARITY_MAP = {
    "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 3600, "6h": 21600, "1d": 86400,
}
_CANDLE_COUNTS = {
    "1m": 120, "5m": 120, "15m": 96, "1h": 96, "4h": 200, "6h": 90, "1d": 90,
}


@app.get("/api/candles")
def get_candles(tf: str = "auto"):
    """Return candle data. tf=auto picks timeframe based on position state.

    No position -> 1d (daily overview).
    In position -> timeframe the strategy trades on.
    Manual override: tf=15m, tf=1h, tf=4h, tf=1d.
    """
    try:
        import requests

        # Determine timeframe
        resolved_tf = tf
        position_tf = None
        if tf == "auto":
            entry_type = ""
            try:
                import sqlite3
                state_db = DATA_DIR / "bot_state.db"
                if state_db.exists():
                    db = sqlite3.connect(str(state_db))
                    row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
                    if row:
                        pos = json.loads(row[0]) if row[0] != "null" else None
                        if pos:
                            entry_type = pos.get("entry_type", "")
                    db.close()
            except Exception:
                pass
            if entry_type:
                position_tf = _ENTRY_TYPE_TF.get(entry_type, "15m")
                resolved_tf = position_tf
            else:
                resolved_tf = "1d"

        granularity = _GRANULARITY_MAP.get(resolved_tf, 86400)
        count = _CANDLE_COUNTS.get(resolved_tf, 90)

        r = requests.get(
            "https://api.exchange.coinbase.com/products/XLM-USD/candles",
            params={"granularity": granularity},
            timeout=10,
        )
        candles = sorted(r.json()[:count])

        # Get position data from SQLite (same source as /api/status)
        pos_data = None
        try:
            import sqlite3
            state_db = DATA_DIR / "bot_state.db"
            if state_db.exists():
                db = sqlite3.connect(str(state_db))
                row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
                if row:
                    pos = json.loads(row[0]) if row[0] != "null" else None
                    if pos and pos.get("entry_price"):
                        pos_data = {
                            "entry_price": float(pos["entry_price"]),
                            "stop_loss": float(pos.get("stop_loss") or 0),
                            "tp1": float(pos.get("tp1") or 0),
                            "tp2": float(pos.get("tp2") or 0),
                            "tp3": float(pos.get("tp3") or 0),
                            "direction": pos.get("direction", ""),
                            "entry_type": pos.get("entry_type", ""),
                            "entry_time": pos.get("entry_time", ""),
                            "quality_tier": pos.get("quality_tier", ""),
                            "size": int(pos.get("size") or 1),
                        }
                db.close()
        except Exception:
            pass

        return {
            "candles": [{"t": c[0], "o": c[3], "h": c[2], "l": c[1], "c": c[4], "v": c[5]} for c in candles],
            "timeframe": resolved_tf,
            "position_tf": position_tf,
            "position": pos_data,
        }
    except Exception:
        return {"candles": [], "timeframe": "1d", "position_tf": None, "position": None}


def _fetch_coinbase_candles(granularity: int, count: int) -> list:
    """Fetch XLM-USD candles from Coinbase Exchange API."""
    import requests as _req
    r = _req.get(
        "https://api.exchange.coinbase.com/products/XLM-USD/candles",
        params={"granularity": granularity},
        timeout=10,
    )
    if not r.ok:
        return []
    raw = sorted(r.json()[:count])
    return [{"t": c[0], "o": c[3], "h": c[2], "l": c[1], "c": c[4], "v": c[5]} for c in raw]


def _get_position_data() -> dict | None:
    """Read open position from SQLite."""
    try:
        import sqlite3
        state_db = DATA_DIR / "bot_state.db"
        if not state_db.exists():
            return None
        db = sqlite3.connect(str(state_db))
        row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
        db.close()
        if not row:
            return None
        pos = json.loads(row[0]) if row[0] != "null" else None
        if not pos or not pos.get("entry_price"):
            return None
        return {
            "entry_price": float(pos["entry_price"]),
            "stop_loss": float(pos.get("stop_loss") or 0),
            "tp1": float(pos.get("tp1") or 0),
            "tp2": float(pos.get("tp2") or 0),
            "tp3": float(pos.get("tp3") or 0),
            "direction": pos.get("direction", ""),
            "entry_type": pos.get("entry_type", ""),
            "entry_time": pos.get("entry_time", ""),
            "quality_tier": pos.get("quality_tier", ""),
            "size": int(pos.get("size") or 1),
            "confluence_score": int(pos.get("confluence_score") or 0),
            "score_threshold": int(pos.get("score_threshold") or 0),
            "strategy_regime": pos.get("strategy_regime", ""),
            "confluence_flags": pos.get("confluence_flags") or {},
        }
    except Exception:
        return None


def _get_strategy_context() -> dict:
    """Read strategy visual context from dashboard snapshot (unified_eyeball)."""
    try:
        snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json")
        if not snap:
            return {}
        eye = snap.get("unified_eyeball") or {}
        return {
            "patterns_detected": eye.get("patterns_detected") or [],
            "confirmations": eye.get("confirmations") or [],
            "indicators": eye.get("indicators") or {},
            "fvg_detail": eye.get("fvg_detail"),
            "channel_detail": eye.get("channel_detail"),
            "structure_bias": eye.get("structure_bias", "neutral"),
            "htf_trend": eye.get("htf_trend", "neutral"),
            "vol_phase": eye.get("vol_phase", "COMPRESSION"),
            "entry_details": eye.get("entry_details") or {},
            "stop_price": eye.get("stop_price"),
            "tp1_price": eye.get("tp1_price"),
            "rr_ratio": eye.get("rr_ratio"),
            "atr_expanding": eye.get("atr_expanding", False),
            "bb_expanding": eye.get("bb_expanding", False),
        }
    except Exception:
        return {}


_market_cache = {"ts": 0, "data": None}


@app.get("/api/charts")
def get_all_charts():
    """Returns all chart data in one call: 1m, 1d, monthly, trade TF + position + strategy."""
    pos = _get_position_data()
    entry_type = pos["entry_type"] if pos else ""
    trade_tf = _ENTRY_TYPE_TF.get(entry_type, "15m") if entry_type else None
    trade_gran = _GRANULARITY_MAP.get(trade_tf, 900) if trade_tf else None
    trade_count = _CANDLE_COUNTS.get(trade_tf, 96) if trade_tf else None

    result = {
        "position": pos,
        "strategy": _get_strategy_context(),
        "trade_tf": trade_tf,
    }

    # 1-minute: 120 candles (2 hours)
    try:
        result["minute"] = _fetch_coinbase_candles(60, 120)
    except Exception:
        result["minute"] = []

    # Daily: 90 candles (3 months)
    try:
        result["daily"] = _fetch_coinbase_candles(86400, 90)
    except Exception:
        result["daily"] = []

    # Monthly: use daily candles, frontend groups them visually
    result["monthly"] = result["daily"]

    # Trade timeframe (dynamic)
    if trade_tf and trade_gran:
        try:
            result["trade"] = _fetch_coinbase_candles(trade_gran, trade_count)
        except Exception:
            result["trade"] = []
    else:
        result["trade"] = []

    return result


@app.get("/api/market-context")
def get_market_context():
    """BTC, S&P 500, NASDAQ prices with 24h change. Cached 60s."""
    import time as _time
    now = _time.time()
    if _market_cache["data"] and (now - _market_cache["ts"]) < 60:
        return _market_cache["data"]

    import requests as _req
    out = {"btc": None, "spx": None, "ndx": None}

    # BTC from Coinbase
    try:
        r = _req.get("https://api.exchange.coinbase.com/products/BTC-USD/stats", timeout=5)
        if r.ok:
            s = r.json()
            last = float(s.get("last") or 0)
            opn = float(s.get("open") or 0)
            chg = last - opn
            pct = (chg / opn * 100) if opn > 0 else 0
            out["btc"] = {"price": round(last, 2), "change": round(chg, 2), "change_pct": round(pct, 2), "symbol": "BTC"}
    except Exception:
        pass

    # SPX from Yahoo
    try:
        r = _req.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=2d",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=5,
        )
        if r.ok:
            meta = r.json()["chart"]["result"][0]["meta"]
            px = float(meta.get("regularMarketPrice") or 0)
            prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
            chg = px - prev
            pct = (chg / prev * 100) if prev > 0 else 0
            out["spx"] = {"price": round(px, 2), "change": round(chg, 2), "change_pct": round(pct, 2), "symbol": "S&P 500"}
    except Exception:
        pass

    # NDX from Yahoo
    try:
        r = _req.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?interval=1d&range=2d",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=5,
        )
        if r.ok:
            meta = r.json()["chart"]["result"][0]["meta"]
            px = float(meta.get("regularMarketPrice") or 0)
            prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
            chg = px - prev
            pct = (chg / prev * 100) if prev > 0 else 0
            out["ndx"] = {"price": round(px, 2), "change": round(chg, 2), "change_pct": round(pct, 2), "symbol": "NASDAQ"}
    except Exception:
        pass

    _market_cache["ts"] = now
    _market_cache["data"] = out
    return out


@app.get("/api/daily-summary")
def get_daily_summary():
    """Clean daily P&L: closed trades + open position unrealized. Resets at midnight PT.

    IMPORTANT: Trade data is sourced from _parse_all_trades_organized() which
    reads trades_organized.csv. This is the SAME source as /api/trades/today
    and /api/trades/history to ensure all endpoints agree on trade counts and P&L.
    """
    from datetime import datetime, timezone, timedelta

    pt_now = datetime.now(timezone.utc) - timedelta(hours=7)
    today = pt_now.strftime("%Y-%m-%d")

    # Use the SHARED trade parser -- same source as /api/trades/today
    real_from_csv, paper_from_csv = _parse_all_trades_organized()
    today_trades_raw = [t for t in real_from_csv if t.get("date") == today]

    closed_pnl = sum(t["pnl"] for t in today_trades_raw)
    wins = sum(1 for t in today_trades_raw if t["result"] == "win")
    losses = sum(1 for t in today_trades_raw if t["result"] == "loss")

    # Build trade_list in the format the frontend expects
    trade_list = []
    for t in today_trades_raw:
        entry_price = t.get("entry_price", 0)
        exit_price = t.get("exit_price", 0)
        side = t.get("side", "long")
        pnl = t.get("pnl", 0)
        fees = t.get("fees", 0)

        # Gross PnL
        if entry_price > 0 and exit_price > 0:
            price_move = exit_price - entry_price
            if side == "short":
                price_move = -price_move
            gross_pnl = round(price_move * 5000.0, 2)  # contract size
        else:
            gross_pnl = round(pnl + fees, 2)

        # Duration and churn detection
        dur_min = t.get("duration_min")
        _is_churn = dur_min is not None and dur_min < 0.5 and abs(pnl) < 3.0

        trade_list.append({
            "time": t.get("time", ""),
            "time_sort": t.get("time_sort", ""),
            "side": side,
            "result": t["result"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "price_move": round(price_move if entry_price > 0 else 0, 6),
            "price_move_pct": round((price_move / entry_price * 100) if entry_price > 0 else 0, 4),
            "gross_pnl": gross_pnl,
            "total_fees": round(fees, 2),
            "entry_fees": 0,
            "exit_fees": 0,
            "net_pnl": round(pnl, 2),
            "type": t.get("entry_type", ""),
            "exit_reason": t.get("exit_reason", ""),
            "hold_sec": int(dur_min * 60) if dur_min else 0,
            "churn": _is_churn,
            "unified_score": t.get("unified_score", ""),
            "rsi": "",
        })

    # Open position unrealized
    unrealized = 0.0
    pos_info = None
    try:
        pos = _get_position_data()
        if pos and pos.get("entry_price"):
            tick = _read_json(LOGS_DIR / "live_tick.json")
            px = float((tick or {}).get("price") or 0)
            if px <= 0:
                snap = _read_json(LOGS_DIR / "dashboard_snapshot.json")
                px = float((snap or {}).get("price") or 0)
            if px > 0:
                entry = pos["entry_price"]
                cs = 5000.0
                size = pos.get("size", 1)
                if pos.get("direction") == "short":
                    unrealized = (entry - px) * cs * size
                else:
                    unrealized = (px - entry) * cs * size
            pos_info = {
                "direction": pos.get("direction", ""),
                "entry_price": pos.get("entry_price", 0),
                "entry_type": pos.get("entry_type", ""),
                "quality_tier": pos.get("quality_tier", ""),
                "unrealized": round(unrealized, 2),
            }
    except Exception:
        pass

    # Separate real trades from churn
    real_trades = [t for t in trade_list if not t.get("churn")]
    churn_trades = [t for t in trade_list if t.get("churn")]
    real_pnl = sum(t.get("net_pnl", t.get("pnl", 0)) for t in real_trades)
    churn_pnl = sum(t.get("net_pnl", t.get("pnl", 0)) for t in churn_trades)

    # Sort newest first
    real_trades.sort(key=lambda x: x.get("time_sort", ""), reverse=True)

    total = closed_pnl + unrealized

    # Fee and P&L breakdown totals
    total_gross = sum(t.get("gross_pnl", 0) for t in real_trades)
    total_fees_paid = sum(t.get("total_fees", 0) for t in real_trades)
    total_net = sum(t.get("net_pnl", 0) for t in real_trades)

    # ALL trades (churn + real) for consistent counting
    all_trades = real_trades + churn_trades
    all_trades.sort(key=lambda x: x.get("time_sort", ""), reverse=True)
    all_wins = sum(1 for t in all_trades if t["result"] == "win")
    all_losses = sum(1 for t in all_trades if t["result"] == "loss")
    all_fees = sum(t.get("total_fees", 0) for t in all_trades)
    all_gross = sum(t.get("gross_pnl", 0) for t in all_trades)

    return {
        # CONSISTENT totals -- includes ALL trades (churn + real)
        "closed_pnl": round(closed_pnl, 2),
        "unrealized": round(unrealized, 2),
        "total_pnl": round(total, 2),
        "wins": all_wins,
        "losses": all_losses,
        "trades_today": all_wins + all_losses,
        # Fee breakdown (all trades)
        "gross_pnl": round(all_gross, 2),
        "total_fees": round(all_fees, 2),
        "net_pnl": round(closed_pnl, 2),
        "fee_pct": round(all_fees / max(abs(all_gross), 0.01) * 100, 1) if all_gross != 0 else 0,
        "avg_fee_per_trade": round(all_fees / max(len(all_trades), 1), 2),
        "breakeven_move": round(all_fees / max(len(all_trades), 1) / 5000, 6),
        # Churn breakdown (still visible but not hidden)
        "churn_count": len(churn_trades),
        "churn_pnl": round(churn_pnl, 2),
        "real_count": len(real_trades),
        "real_pnl": round(real_pnl, 2),
        # Full trade list -- ALL trades, churn tagged
        "trades": all_trades,
        "position": pos_info,
    }


@app.get("/api/shadow-trades")
def get_shadow_trades():
    """Shadow trade tracker -- blocked trades tracked for hindsight learning.

    SEPARATE from real trades. Never contaminates PnL or trade history.
    """
    try:
        shadow_dir = LOGS_DIR / "shadows"
        shadows = []
        if shadow_dir.exists():
            for fname in ["entry_shadows.jsonl", "exit_shadows.jsonl", "flip_shadows.jsonl", "reentry_shadows.jsonl"]:
                fpath = shadow_dir / fname
                if fpath.exists():
                    with open(fpath) as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                shadows.append(json.loads(line))
        if not shadows:
            return {"active": [], "closed": [], "summary": {}}
        active = [s for s in shadows if not s.get("closed")]
        closed = [s for s in shadows if s.get("closed")]
        winners = [s for s in closed if s.get("would_have_won")]
        # Group by block reason
        by_reason = {}
        for s in closed:
            r = s.get("block_reason", "unknown")
            if r not in by_reason:
                by_reason[r] = {"total": 0, "wins": 0, "losses": 0}
            by_reason[r]["total"] += 1
            if s.get("would_have_won"):
                by_reason[r]["wins"] += 1
            else:
                by_reason[r]["losses"] += 1
        return {
            "active": active[-10:],
            "closed": closed[-20:],
            "summary": {
                "total": len(shadows),
                "active": len(active),
                "closed": len(closed),
                "would_have_won": len(winners),
                "win_rate": round(len(winners) / max(len(closed), 1) * 100, 1),
                "by_reason": by_reason,
            },
        }
    except Exception:
        return {"active": [], "closed": [], "summary": {}}


@app.get("/api/pnl")
def get_pnl():
    events = get_events(500)
    pnl_series = []
    running = 0.0
    for e in sorted(events, key=lambda x: x["ts"]):
        p = e.get("payload", {})
        pnl = p.get("pnl_usd")
        if pnl is not None and e["type"] in ("exit_position", "exchange_side_close_detected"):
            running += float(pnl)
            pnl_series.append({"ts": e["ts"], "pnl": round(float(pnl), 2), "cumulative": round(running, 2)})
    return pnl_series
@app.get("/api/history")
def get_full_history():
    """Full trade history with P&L, strategy, and daily breakdown."""
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return {"trades": [], "daily": [], "by_strategy": {}, "summary": {}}
    import sqlite3
    db = sqlite3.connect(str(state_db))
    rows = db.execute("""
        SELECT ts, type, payload_json FROM events
        WHERE type IN ('entered_position','exit_position','exchange_side_close_detected')
        ORDER BY id
    """).fetchall()
    db.close()
    trades = []
    open_entry = None
    total_pnl = 0.0
    wins = 0
    losses = 0
    by_day = {}
    by_strategy = {}
    pnl_curve = []
    # Also scan decisions log for entry types
    entry_types_by_time = {}
    decisions_path = LOGS_DIR / "decisions.jsonl"
    if decisions_path.exists():
        try:
            raw = decisions_path.read_text()
            for line in raw.strip().split("\n")[-5000:]:
                try:
                    d = json.loads(line)
                    r = d.get("reason", "")
                    if "watching" in d.get("thought", "") or d.get("entry_signal"):
                        ts_key = str(d.get("timestamp", ""))[:16]
                        et = d.get("entry_type") or d.get("entry_signal") or ""
                        if et:
                            entry_types_by_time[ts_key] = et
                except Exception:
                    pass
        except Exception:
            pass
    for ts, typ, pj in rows:
        p = json.loads(pj)
        if typ == "entered_position":
            # Try to find entry type from decisions near this timestamp
            ts_key = str(ts)[:16]
            entry_type = "unknown"
            for offset in range(0, 5):
                # Check a few minutes before entry
                check = ts_key  # simplified
                if check in entry_types_by_time:
                    entry_type = entry_types_by_time[check]
                    break
            # Also check state for lane info
            if entry_type == "unknown":
                entry_type = p.get("entry_type") or p.get("lane_label") or "unknown"
            open_entry = {
                "entry_ts": ts,
                "direction": p.get("direction", "?"),
                "size": p.get("size", 1),
                "entry_type": entry_type,
            }
        elif typ in ("exit_position", "exchange_side_close_detected"):
            pnl = p.get("pnl_usd")
            exit_reason = p.get("exit_reason", "")
            exit_price = p.get("exit_price", 0)
            trade = {
                "entry_ts": open_entry["entry_ts"] if open_entry else "",
                "exit_ts": ts,
                "direction": open_entry["direction"] if open_entry else p.get("direction", "?"),
                "size": open_entry["size"] if open_entry else 1,
                "strategy": open_entry["entry_type"] if open_entry else "unknown",
                "exit_reason": exit_reason,
                "pnl_usd": float(pnl) if pnl is not None else 0,
                "result": "win" if pnl and float(pnl) > 0 else ("loss" if pnl and float(pnl) < 0 else "flat"),
            }
            trades.append(trade)
            if pnl is not None:
                pnl_val = float(pnl)
                total_pnl += pnl_val
                if pnl_val > 0:
                    wins += 1
                elif pnl_val < 0:
                    losses += 1
                day = str(ts)[:10]
                by_day.setdefault(day, {"pnl": 0, "wins": 0, "losses": 0, "trades": 0})
                by_day[day]["pnl"] += pnl_val
                by_day[day]["trades"] += 1
                if pnl_val > 0:
                    by_day[day]["wins"] += 1
                elif pnl_val < 0:
                    by_day[day]["losses"] += 1
                strat = trade["strategy"]
                by_strategy.setdefault(strat, {"pnl": 0, "wins": 0, "losses": 0, "trades": 0})
                by_strategy[strat]["pnl"] += pnl_val
                by_strategy[strat]["trades"] += 1
                if pnl_val > 0:
                    by_strategy[strat]["wins"] += 1
                elif pnl_val < 0:
                    by_strategy[strat]["losses"] += 1
                pnl_curve.append({"ts": ts, "pnl": round(pnl_val, 2), "cumulative": round(total_pnl, 2)})
            open_entry = None
    daily = [{"date": d, **v} for d, v in sorted(by_day.items())]
    for d in daily:
        d["pnl"] = round(d["pnl"], 2)
    for s in by_strategy.values():
        s["pnl"] = round(s["pnl"], 2)
    best_trade = max((t["pnl_usd"] for t in trades), default=0)
    worst_trade = min((t["pnl_usd"] for t in trades), default=0)
    best_day = max((d["pnl"] for d in daily), default=0) if daily else 0
    worst_day = min((d["pnl"] for d in daily), default=0) if daily else 0
    return {
        "trades": trades,
        "daily": daily,
        "by_strategy": by_strategy,
        "pnl_curve": pnl_curve,
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "wins": wins,
            "losses": losses,
            "total_trades": wins + losses,
            "win_rate": round(wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "best_day": round(best_day, 2),
            "worst_day": round(worst_day, 2),
            "avg_win": round(sum(t["pnl_usd"] for t in trades if t["pnl_usd"] > 0) / max(wins, 1), 2),
            "avg_loss": round(sum(t["pnl_usd"] for t in trades if t["pnl_usd"] < 0) / max(losses, 1), 2),
            "trading_days": len(daily),
            "first_trade": trades[0]["entry_ts"][:10] if trades else "",
            "last_trade": trades[-1]["exit_ts"][:10] if trades else "",
        },
    }
@app.get("/api/active-strategy")
def get_active_strategy():
    """Get the current active strategy/position details for highlighting."""
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return {"active": False}
    import sqlite3
    db = sqlite3.connect(str(state_db))
    row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
    db.close()
    if not row or row[0] == "null":
        # Check last few decisions for what the bot is looking at
        decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=10)
        watching = None
        for d in reversed(decisions):
            thought = str(d.get("thought", ""))
            if "watching" in thought and "setup" in thought:
                watching = {
                    "signal": thought,
                    "direction": d.get("direction", ""),
                    "entry_type": d.get("entry_type", ""),
                    "score": d.get("v4_score", ""),
                    "blocked_by": d.get("reason", ""),
                }
                break
        return {"active": False, "watching": watching}
    pos = json.loads(row[0])
    return {
        "active": True,
        "direction": pos.get("direction", "?"),
        "entry_price": pos.get("entry_price", 0),
        "size": pos.get("size", 1),
        "entry_time": pos.get("entry_time", ""),
        "strategy": pos.get("entry_type") or pos.get("lane_label") or pos.get("_entry_signal_type") or "unknown",
        "lane": pos.get("lane_label", ""),
        "quality_tier": pos.get("quality_tier", ""),
        "v4_score": pos.get("v4_score", 0),
        "regime": pos.get("regime_name", ""),
        "htf_bias": pos.get("htf_bias", ""),
        "confluences": pos.get("confluences", {}),
        "profit_state": pos.get("_profit_state", {}),
    }
# ── Django Proxy: forward requests to :8504 ──
DJANGO_BASE = "http://localhost:8504"
@app.get("/api/django/hub-status")
def django_hub_status():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/hub-status/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/bot-intel")
def django_bot_intel():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/bot-intel/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/live-feed")
def django_live_feed():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/live-feed/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/sessions")
def django_sessions():
    """Pull session data from Django ORM via a lightweight endpoint."""
    import requests
    try:
        # Use the hub-status which has session counts
        r = requests.get(f"{DJANGO_BASE}/api/hub-status/", timeout=5)
        data = r.json()
        return data
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/taskboard")
def django_taskboard():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/taskboard/api/status/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/revenue")
def django_revenue():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/payments/api/summary/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/broker")
def django_broker():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/broker/api/commissions/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/reports")
def django_reports():
    """List all styled HTML reports from hive_reports directory."""
    import re
    from pathlib import Path
    reports_dir = Path("/home/opc/hive_reports")
    reports = []
    if reports_dir.is_dir():
        for f in sorted(reports_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
            title = f.stem.replace("_", " ").title()
            try:
                head = f.read_text()[:2000]
                m = re.search(r"<title>([^<]+)", head)
                if m:
                    raw = m.group(1).replace(" | Everlight Ventures", "").strip()
                    if raw:
                        title = raw
            except Exception:
                pass
            cat = "general"
            fn = f.name.lower()
            if "pipeline" in fn or "wholesale" in fn: cat = "pipeline"
            elif "deal" in fn or "contract" in fn: cat = "deals"
            elif "outreach" in fn or "email" in fn: cat = "outreach"
            elif "lucrex" in fn or "operations" in fn: cat = "operations"
            elif "intel" in fn or "bot" in fn: cat = "trading"
            elif "landing" in fn: cat = "landing"
            reports.append({
                "filename": f.name,
                "title": title,
                "category": cat,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "url": f"http://129.159.38.250:8504/reports/{f.stem}",
                "raw_url": f"http://129.159.38.250:8504/reports/{f.stem}?raw=1",
            })
    return {"reports": reports[:50], "total": len(reports)}

@app.get("/api/blinko/search")
def blinko_search(q: str = "", limit: int = 10):
    """Search Blinko knowledge base directly."""
    import requests as _req
    try:
        r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": limit, "searchText": q, "type": -1},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        data = r.json()
        notes = data.get("items", [])
        return {
            "total": data.get("total", 0),
            "notes": [
                {
                    "id": n.get("id", ""),
                    "content": n.get("content", "")[:500],
                    "tags": n.get("tags", ""),
                    "created": n.get("created_at", ""),
                    "updated": n.get("updated_at", ""),
                }
                for n in notes
            ],
        }
    except Exception as e:
        return {"total": 0, "notes": [], "error": str(e)}
@app.get("/api/blinko/stats")
def blinko_stats():
    import requests as _req
    try:
        r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": 1},
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        return {"total_notes": r.json().get("total", 0)}
    except Exception as e:
        return {"total_notes": 0, "error": str(e)}
import os as _os
from fastapi import UploadFile, File as FastFile, Form
UPLOAD_DIR = Path("/home/opc/xlm-dash-react/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
@app.post("/api/hive/chat")
async def hive_chat(message: str = Form(...), agent: str = Form("auto")):
    """Query the Hive Mind -- routes to Blinko RAG + agent context."""
    import requests as _req
    results = {"query": message, "agent": agent, "sources": [], "response": ""}
    # Step 1: Search Blinko for relevant knowledge
    try:
        blinko_r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": 5, "searchText": message, "type": -1},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        blinko_data = blinko_r.json()
        notes = blinko_data.get("items", [])
        results["sources"] = [
            {"content": n.get("content", "")[:300], "tags": n.get("tags", ""), "date": n.get("created_at", "")[:10]}
            for n in notes[:5]
        ]
        results["blinko_total"] = blinko_data.get("total", 0)
    except Exception as e:
        results["sources"] = []
        results["blinko_error"] = str(e)
    # Step 2: Get bot intel for trading context
    try:
        bot_r = _req.get("http://localhost:8504/api/bot-intel/", timeout=5)
        bot_data = bot_r.json()
        results["bot_context"] = {
            "vol_state": bot_data.get("state", {}).get("vol_state"),
            "pnl_today": bot_data.get("state", {}).get("pnl_today_usd"),
            "position": bot_data.get("state", {}).get("open_position"),
            "ai_action": bot_data.get("ai", {}).get("claude_action"),
            "ai_reasoning": bot_data.get("ai", {}).get("claude_reasoning", "")[:200],
        }
    except Exception:
        results["bot_context"] = {}
    # Step 3: Build response from available data
    context_parts = []
    if results["sources"]:
        context_parts.append(f"Found {len(results['sources'])} relevant Blinko notes (out of {results.get('blinko_total', 0)} total).")
        for i, s in enumerate(results["sources"][:3], 1):
            context_parts.append(f"\n**Note {i}** ({s['date']}, {s['tags']}):\n{s['content']}")
    bot_ctx = results.get("bot_context", {})
    if bot_ctx.get("ai_action"):
        context_parts.append(f"\n**Bot Status:** {bot_ctx['ai_action']} | Vol: {bot_ctx.get('vol_state', '?')} | P&L Today: ${bot_ctx.get('pnl_today', 0):.2f}")
        if bot_ctx.get("ai_reasoning"):
            context_parts.append(f"**AI Reasoning:** {bot_ctx['ai_reasoning']}")
    if context_parts:
        results["response"] = "\n".join(context_parts)
    else:
        results["response"] = "No relevant knowledge found in Blinko. Try a different query or check if Blinko is online."
    return results
@app.post("/api/hive/upload")
async def hive_upload(file: UploadFile = FastFile(...)):
    """Upload a file to the Hive Mind workspace."""
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    dest = UPLOAD_DIR / safe_name
    content = await file.read()
    dest.write_bytes(content)
    return {
        "ok": True,
        "filename": safe_name,
        "size": len(content),
        "path": str(dest),
    }
@app.get("/api/hive/uploads")
def list_uploads():
    """List uploaded files."""
    files = []
    for f in sorted(UPLOAD_DIR.iterdir()):
        if f.is_file():
            files.append({"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return files
@app.get("/api/settings")
def get_settings():
    """Return current integration settings with LIVE health checks."""
    import requests as _settings_req

    def _check(url, timeout=3):
        try:
            r = _settings_req.get(url, timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    # Live health checks
    blinko_up = _check("http://localhost:1111/api/v1/note/list", 3)
    django_up = _check("http://localhost:8504/api/hub-status/", 3)
    n8n_up = _check("http://localhost:5678/", 3)
    gdocs_up = _check("http://localhost:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc", 3)

    # Blinko note count
    blinko_notes = 0
    if blinko_up:
        try:
            r = _settings_req.post("http://localhost:1111/api/v1/note/list",
                json={"page":1,"pageSize":1}, headers={"Content-Type":"application/json"}, timeout=3)
            blinko_notes = r.json().get("total", 0)
        except Exception:
            pass

    return {
        "integrations": {
            "blinko": {"status": "connected" if blinko_up else "offline", "url": "http://129.159.38.250:1111", "notes": blinko_notes, "editable": True},
            "django": {"status": "connected" if django_up else "offline", "url": "http://129.159.38.250:8504", "editable": True},
            "n8n": {"status": "connected" if n8n_up else "offline", "url": "http://129.159.38.250:5678", "editable": True},
            "slack": {"status": "connected", "channels": 13, "via": "Bot tokens", "editable": True},
            "gmail": {"status": "connected", "via": "MCP (Claude AI)", "editable": True},
            "calendar": {"status": "connected", "via": "MCP (Claude AI)", "editable": True},
            "stripe": {"status": "connected", "via": "MCP", "editable": True},
            "supabase": {"status": "connected", "via": "MCP", "editable": True},
            "coinbase": {"status": "connected", "via": "REST API + WebSocket", "editable": True},
            "github": {"status": "connected", "via": "SSH deploy key", "editable": True},
            "google_docs": {"status": "connected" if gdocs_up else "degraded", "via": "n8n webhook" if gdocs_up else "n8n webhook (workflow inactive)", "editable": True},
            "resend": {"status": "connected", "emails": 42, "via": "API", "editable": True},
        },
        "ai_accounts": {
            "claude": {"status": "active", "model": "opus-4.6", "role": "Executive + Trading + CLI", "always_on": True, "editable": True},
            "gemini": {"status": "active", "model": "gemini-2.5-pro", "role": "Research + Ops + Debate", "always_on": True, "editable": True},
            "codex": {"status": "active", "model": "codex-mini", "role": "Engineering + Build + Deploy", "always_on": True, "editable": True},
            "perplexity": {"status": "active", "model": "sonar-pro", "role": "Intel + Research + OSINT", "always_on": True, "editable": True},
        },
        "agents": {"total": 63, "squads": 4, "fire_teams": 12, "active": 63, "buddy_pairs": 24},
    }
import subprocess as _sp
@app.post("/api/claude/chat")
async def claude_chat(message: str = Form(...), mode: str = Form("review"), engine: str = Form("claude")):
    """Chat with Claude directly via Anthropic API with live bot context."""
    import anthropic
    # Read bot context from snapshot + live decisions
    ctx_parts = []
    snap_path = LOGS_DIR / "dashboard_snapshot.json"
    try:
        raw = json.loads(snap_path.read_text())
        d = raw[0] if isinstance(raw, list) and raw else raw
        for k in ("price", "state", "regime", "vol_phase", "direction", "v4_score",
                   "entry_signal", "reason", "cooldown", "trades_today", "losses_today",
                   "pnl_today_usd", "quality_tier", "lane_label", "gates_pass",
                   "entry_type_long", "entry_type_short", "v4_score_long", "v4_score_short",
                   "long_block_reason", "short_block_reason"):
            v = d.get(k)
            if v is not None:
                ctx_parts.append(f"{k}: {v}")
    except Exception:
        ctx_parts.append("(snapshot unavailable)")
    # Also read last few decisions
    try:
        decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=5)
        for dec in decisions[-3:]:
            r = dec.get("reason", "")
            t = dec.get("thought", "")[:100]
            d = dec.get("direction", "")
            if t:
                ctx_parts.append(f"Recent: [{r}] {d} -- {t}")
    except Exception:
        pass
    ctx = chr(10).join(ctx_parts)
    is_execute = mode == "execute"
    system_prompt = (
        "You are Lucrex, the AI trading advisor for the XLM perpetual futures bot. "
        "You are confident, direct, and street-smart. You speak with conviction. "
        "The bot trades XLP-20DEC30-CDE on Coinbase with 4x leverage (~$443 balance). "
        "1 contract = 5,000 XLM. $0.01 move = $50/contract. "
        "Bot location: /home/opc/xlm-bot/ on Oracle Cloud. "
        "Config: config.yaml. Main logic: main.py. "
        + ("You are in EXECUTE mode -- the user wants you to make changes. "
           "Describe exactly what you would change in config.yaml or main.py. "
           "Be specific with the setting names and values."
           if is_execute else
           "You are in REVIEW mode -- analyze and advise only, do not make changes. "
           "Explain what the bot is doing and why.")
        + chr(10) + "LIVE BOT STATE:" + chr(10) + ctx
    )
    # Route to Claude Code on the phone via SSH tunnel
    # This uses the SAME Claude Code instance running in Termux
    # with full CLAUDE.md context, memory, MCP tools, and all 63 agents
    import requests as _chat_req
    BRIDGE_URL = "http://localhost:8510/ask"
    try:
        # Prepend bot context to the message so Claude has full picture
        full_message = f"[BOT CONTEXT]\n{ctx}\n\n[USER QUESTION]\n{message}"
        if is_execute:
            full_message += "\n\n[MODE: EXECUTE -- make the requested changes to config.yaml or main.py on Oracle at /home/opc/xlm-bot/]"
        resp = _chat_req.post(
            BRIDGE_URL,
            json={"message": full_message, "mode": mode},
            timeout=65,
        )
        data = resp.json()
        answer = data.get("answer", "No response from Claude Code.")
        used_engine = "claude-code (phone)"
    except _chat_req.ConnectionError:
        answer = "Claude Code bridge offline. Start it on your phone: python3 03_AUTOMATION_CORE/01_Scripts/claude_chat_bridge.py"
        used_engine = "offline"
    except _chat_req.Timeout:
        answer = "Claude Code timed out (>60s). Try a shorter question."
        used_engine = "timeout"
    except Exception as e:
        answer = f"Bridge error: {str(e)[:200]}"
        used_engine = "error"
    return {"answer": answer, "mode": mode, "engine": used_engine}

# ── Wholesale Pipeline API ──
SUPABASE_URL_WS = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY_WS = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"

def _sb_get(table, params=""):
    import requests as _r
    url = f"{SUPABASE_URL_WS}/rest/v1/{table}?{params}"
    headers = {"apikey": SUPABASE_KEY_WS, "Authorization": f"Bearer {SUPABASE_KEY_WS}"}
    try:
        return _r.get(url, headers=headers, timeout=10).json()
    except Exception:
        return []

@app.get("/api/wholesale/stats")
def wholesale_stats():
    stats = {}
    for status in ["new", "contacted", "responding", "negotiating", "under_contract", "assigned", "closed", "dead"]:
        r = _sb_get("wholesale_sellers", f"status=eq.{status}&select=id")
        stats[f"sellers_{status}"] = len(r) if isinstance(r, list) else 0

    for status in ["scouted", "seller_contacted", "under_contract", "buyer_matched", "buyer_pitched", "assigned", "closing", "closed"]:
        r = _sb_get("wholesale_deals", f"status=eq.{status}&select=id")
        stats[f"deals_{status}"] = len(r) if isinstance(r, list) else 0

    for rel in ["new", "contacted", "warm", "hot", "repeat"]:
        r = _sb_get("wholesale_buyers", f"relationship_status=eq.{rel}&select=id")
        stats[f"buyers_{rel}"] = len(r) if isinstance(r, list) else 0

    for s in ["draft", "verified", "sent", "delivered", "opened", "replied"]:
        r = _sb_get("wholesale_outreach", f"status=eq.{s}&select=id")
        stats[f"outreach_{s}"] = len(r) if isinstance(r, list) else 0

    closed = _sb_get("wholesale_deals", "status=eq.closed&select=actual_profit")
    stats["total_revenue"] = sum(float(d.get("actual_profit", 0)) for d in closed) if isinstance(closed, list) else 0
    stats["deals_closed_count"] = len(closed) if isinstance(closed, list) else 0
    return stats

@app.get("/api/wholesale/states")
def wholesale_states():
    return _sb_get("wholesale_states", "order=ease_score.desc,market_volume_rank.asc")

@app.get("/api/wholesale/sellers")
def wholesale_sellers(limit: int = 50):
    return _sb_get("wholesale_sellers", f"order=priority_score.desc&limit={limit}")

@app.get("/api/wholesale/buyers")
def wholesale_buyers(limit: int = 50):
    return _sb_get("wholesale_buyers", f"order=deals_closed.desc,relationship_status.desc&limit={limit}")

@app.get("/api/wholesale/deals")
def wholesale_deals(limit: int = 50):
    return _sb_get("wholesale_deals", f"order=created_at.desc&limit={limit}")

@app.get("/api/wholesale/outreach")
def wholesale_outreach(limit: int = 50):
    return _sb_get("wholesale_outreach", f"order=created_at.desc&limit={limit}")




# ── Client Files API ──────────────────────────────────────────────────────

@app.get("/api/client-files")
def list_client_files(status: str = "", state: str = "", limit: int = 50):
    """List all client files with optional status/state filter."""
    params = f"order=updated_at.desc&limit={limit}"
    if status:
        params += f"&status=eq.{status}"
    if state:
        params += f"&state=eq.{state.upper()}"
    files = _sb_get("wholesale_client_files", params)
    if not isinstance(files, list):
        return []
    return files

@app.get("/api/client-files/{file_id}/documents")
def get_client_documents(file_id: str):
    """Get all documents for a client file, ordered by creation."""
    docs = _sb_get("wholesale_client_documents", f"client_file_id=eq.{file_id}&order=created_at.asc")
    if not isinstance(docs, list):
        return []
    return docs

@app.get("/api/client-files/stats")
def client_files_stats():
    """KPI stats for client files."""
    stats = {}
    for s in ["active", "under_contract", "closing", "closed", "dead"]:
        r = _sb_get("wholesale_client_files", f"status=eq.{s}&select=id")
        stats[s] = len(r) if isinstance(r, list) else 0
    stats["total"] = sum(stats.values())
    # Pipeline fees
    pipeline = _sb_get("wholesale_client_files", "status=in.(active,under_contract,closing)&select=assignment_fee")
    stats["pipeline_fees"] = sum(float(d.get("assignment_fee", 0) or 0) for d in pipeline) if isinstance(pipeline, list) else 0
    closed = _sb_get("wholesale_client_files", "status=eq.closed&select=assignment_fee")
    stats["closed_revenue"] = sum(float(d.get("assignment_fee", 0) or 0) for d in closed) if isinstance(closed, list) else 0
    return stats

from fastapi.responses import HTMLResponse as _CFHTMLResponse
@app.get("/client-file-doc/{doc_id}", response_class=_CFHTMLResponse)
def serve_client_document(doc_id: str):
    """Serve a branded HTML document for iframe preview."""
    docs = _sb_get("wholesale_client_documents", f"id=eq.{doc_id}&select=html_content,title")
    if not docs or not isinstance(docs, list) or len(docs) == 0:
        return _CFHTMLResponse("<h1>Document not found</h1>", status_code=404)
    html = docs[0].get("html_content", "<h1>No content</h1>")
    return _CFHTMLResponse(html)

# ── Deal Prep API + Package Serving ──
from fastapi.responses import HTMLResponse

DEAL_PACKAGES_DIR = Path("/home/opc/hive_action_engine/deal_packages")

@app.get("/api/deal-prep/packages")
def list_deal_packages():
    """List all generated deal packages."""
    if not DEAL_PACKAGES_DIR.exists():
        return []
    packages = []
    for pkg_dir in sorted(DEAL_PACKAGES_DIR.iterdir(), reverse=True):
        if pkg_dir.is_dir():
            info_file = pkg_dir / "package_info.json"
            info = {}
            if info_file.exists():
                try:
                    info = json.loads(info_file.read_text())
                except Exception:
                    pass
            packages.append({
                "name": pkg_dir.name,
                "property": info.get("property", pkg_dir.name),
                "city": info.get("city", ""),
                "state": info.get("state", ""),
                "title_company": info.get("title_company", {}).get("name", ""),
                "matched_buyer": info.get("matched_buyer", ""),
                "generated_at": info.get("generated_at", ""),
                "has_deal_sheet": (pkg_dir / "deal_sheet.html").exists(),
                "has_contract": (pkg_dir / "assignment_contract.md").exists(),
            })
    return packages

@app.get("/deal-sheet/{package_name}", response_class=HTMLResponse)
def serve_deal_sheet(package_name: str):
    """Serve a deal sheet HTML for preview."""
    html_file = DEAL_PACKAGES_DIR / package_name / "deal_sheet.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    # Check if it is a direct file (like demo)
    direct = DEAL_PACKAGES_DIR / package_name
    if direct.exists() and direct.suffix == ".html":
        return HTMLResponse(content=direct.read_text())
    return HTMLResponse(content="<h1>Package not found</h1>", status_code=404)

@app.get("/deal-sheet-demo", response_class=HTMLResponse)
def serve_demo_deal_sheet():
    """Serve the demo deal sheet."""
    demo = DEAL_PACKAGES_DIR / "demo_deal_sheet.html"
    if demo.exists():
        return HTMLResponse(content=demo.read_text())
    return HTMLResponse(content="<h1>Demo not generated yet</h1>", status_code=404)

@app.get("/api/deal-prep/prep/{seller_id}")
def prep_deal(seller_id: str):
    """Trigger deal package preparation for a seller."""
    import sys
    sys.path.insert(0, "/home/opc/hive_action_engine")
    try:
        from deal_prep_engine import prep_deal_package
        result = prep_deal_package(seller_id)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/resources/state-matrix")
def state_matrix_link():
    """Return the state contract matrix report URL."""
    return {
        "url": "http://129.159.38.250:8504/reports/state_contract_matrix__8_markets_20260324_0513.html",
        "title": "State Contract Matrix -- 8 Markets",
        "description": "Legal framework comparison: wholesale legality, attorney requirements, assignment enforceability, inspection periods, escape clauses, title companies",
    }



@app.get("/api/trade-reason")
def get_trade_reason():
    """Returns a single current-state reason: why the bot IS or ISN'T in a trade right now."""
    # Check if in a position
    state_db = DATA_DIR / "bot_state.db"
    position = None
    if state_db.exists():
        try:
            import sqlite3
            db = sqlite3.connect(str(state_db))
            row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
            db.close()
            if row and row[0] != "null":
                position = json.loads(row[0])
        except Exception:
            pass

    # Get the latest decision for context
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=10)
    last_thought = ""
    last_reason = ""
    last_direction = ""
    last_score = ""
    blocker = ""

    for d in reversed(decisions):
        r = str(d.get("reason", ""))
        t = str(d.get("thought", ""))
        direction = d.get("direction", "")

        # Find the most recent meaningful decision
        if "band_navigator_wait" in r:
            blocker = "band_navigator"
            last_thought = t
            last_direction = direction
            break
        elif "entry_blocked" in r:
            blocker = r.replace("entry_blocked_", "")
            last_thought = t
            last_direction = direction
            break
        elif "dip_retrace" in r:
            blocker = "dip_retrace_gate"
            last_thought = t
            break
        elif t and ("watching" in t or "setup" in t):
            last_thought = t
            last_direction = direction
            last_score = str(d.get("v4_score", ""))
            break
        elif t and direction:
            last_thought = t
            last_direction = direction
            break

    if position:
        # IN A TRADE
        direction = position.get("direction", "?")
        entry = float(position.get("entry_price", 0))
        strategy = position.get("entry_type") or position.get("lane_label") or "unknown"
        tick = _read_json(LOGS_DIR / "live_tick.json")
        price = float(tick.get("price", 0))
        if entry > 0 and price > 0:
            if direction == "long":
                pnl_pct = (price - entry) / entry * 100
            else:
                pnl_pct = (entry - price) / entry * 100
            pnl_usd = pnl_pct / 100 * entry * int(position.get("size", 1)) * 5000
        else:
            pnl_pct = 0
            pnl_usd = 0

        status = "in_trade"
        pnl_sign = "+" if pnl_usd >= 0 else ""
        headline = f"{direction.upper()} via {strategy.replace('_', ' ')} @ ${entry:.5f} | P&L: {pnl_sign}${pnl_usd:.2f} ({pnl_pct:+.2f}%)"
    else:
        # NOT IN A TRADE - explain why
        status = "flat"
        if blocker == "band_navigator":
            headline = "Waiting for band alignment. " + last_thought[:120] if last_thought else "Band navigator holding -- timeframes not aligned yet."
        elif blocker == "sl_distance":
            headline = "Setup found but stop too far from entry. Waiting for tighter structure."
        elif blocker == "sentiment":
            headline = "Sentiment gate blocking. Market fear too high for entry."
        elif blocker == "margin_playbook":
            headline = "Margin window blocking. Overnight margin rules active."
        elif blocker == "no_signal":
            headline = last_thought[:150] if last_thought else "No clean setup. Scanning for entry signals."
        elif blocker:
            headline = f"Blocked by {blocker}. " + (last_thought[:100] if last_thought else "")
        elif last_thought:
            headline = last_thought[:150]
        else:
            headline = "Scanning for entry signals across all timeframes."

        if last_direction:
            headline = f"[{last_direction.upper()} bias] " + headline

    return {
        "status": status,
        "headline": headline,
        "direction": last_direction or (position.get("direction") if position else ""),
        "blocker": blocker,
        "ts": decisions[-1].get("timestamp", "") if decisions else "",
    }



# ── Unified Reports Hub ──
import glob as _glob
from fastapi.responses import HTMLResponse as _HTMLResponse

REPORT_DIRS = [
    Path("/home/opc/reports"),
    Path("/home/opc/hive_reports"),
    Path("/home/opc/hive_action_engine/deal_packages"),
    Path("/home/opc/xlm-bot/logs/gdocs_queue"),
    Path("/home/opc/xlm-bot"),  # intel_hub.html
]

def _extract_report_meta(filepath):
    """Extract title, subject, date from an HTML report file."""
    import re as _re
    try:
        text = filepath.read_text(errors="replace")[:3000]
        # Title
        title_m = _re.search(r"<title>([^<]+)</title>", text)
        title = title_m.group(1).strip() if title_m else filepath.stem

        # Try to extract date from filename or content
        date_m = _re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", filepath.name)
        if not date_m:
            date_m = _re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", text[:500])
        date_str = date_m.group(1).replace("_", "-") if date_m else ""

        # Subject classification
        name_lower = (filepath.name + title).lower()
        if "state_contract" in name_lower or "matrix" in name_lower or "compliance" in name_lower:
            subject = "Legal / Compliance"
        elif "deal_sheet" in name_lower or "deal" in name_lower:
            subject = "Deal Packages"
        elif "operations" in name_lower or "lucrex" in name_lower:
            subject = "Operations Reports"
        elif "wholesale" in name_lower or "pipeline" in name_lower:
            subject = "Wholesale"
        elif "contract" in name_lower or "assignment" in name_lower:
            subject = "Contracts"
        elif "outreach" in name_lower or "buyer" in name_lower or "email" in name_lower:
            subject = "Outreach / Sales"
        elif "intel" in name_lower or "market" in name_lower or "trading" in name_lower or "bot" in name_lower:
            subject = "Trading / Intel"
        elif "system_alert" in name_lower or "warning" in name_lower or "alert" in name_lower:
            subject = "System Alerts"
        elif "hive" in name_lower or "session" in name_lower or "agent" in name_lower:
            subject = "Hive Sessions"
        elif "gdocs" in name_lower or "google" in name_lower:
            subject = "Google Docs Queue"
        else:
            subject = "General"

        return {
            "title": title,
            "subject": subject,
            "date": date_str,
            "filename": filepath.name,
            "size_kb": round(filepath.stat().st_size / 1024, 1),
            "modified": filepath.stat().st_mtime,
        }
    except Exception:
        return {"title": filepath.stem, "subject": "General", "date": "", "filename": filepath.name, "size_kb": 0, "modified": 0}


@app.get("/api/reports")
def list_all_reports():
    """List all reports across all directories, sorted by date (most recent first)."""
    reports = []
    for rdir in REPORT_DIRS:
        if not rdir.exists():
            continue
        for f in rdir.rglob("*"):
            if f.suffix not in (".html", ".md") or f.name.startswith("."):
                continue
            # Override subject for assignment contracts
            if "assignment_contract" in f.name or "contract" in f.name.lower():
                meta = _extract_report_meta(f)
                meta["subject"] = "Contracts"
                # Get property name from parent dir
                parent_name = f.parent.name
                if parent_name != "deal_packages":
                    meta["title"] = "Contract: " + parent_name.replace("_", " ").split(" 2026")[0]
                meta["url"] = f"/reports/contract/{parent_name}/{f.name}"
                reports.append(meta)
                continue
            if "node_modules" in str(f) or "venv" in str(f) or "__pycache__" in str(f):
                continue
            if "templates" in str(f) or "static" in str(f):
                continue  # skip Django templates
            meta = _extract_report_meta(f)
            # Build the serve URL based on which directory
            if str(rdir) == "/home/opc/reports":
                meta["url"] = f"/reports/file/{f.name}"
                meta["source"] = "ops"
            elif str(rdir) == "/home/opc/hive_reports":
                meta["url"] = f"/reports/file/{f.name}"
                meta["source"] = "hive"
            else:
                # Deal packages
                meta["url"] = f"/deal-sheet/{f.parent.name}"
                meta["source"] = "deals"
            reports.append(meta)

    # Sort by modified time descending (most recent first)
    reports.sort(key=lambda x: x.get("modified", 0), reverse=True)

    # Add email drafts from Supabase wholesale_outreach
    try:
        import requests as _outreach_req
        _sb_url = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
        _sb_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
        _otr = _outreach_req.get(
            f"{_sb_url}/rest/v1/wholesale_outreach?select=id,target_name,target_email,subject,body,status,agent_name,tone,personalization_notes,created_at&order=created_at.desc&limit=20",
            headers={"apikey": _sb_key, "Authorization": f"Bearer {_sb_key}"},
            timeout=10,
        ).json()
        for o in (_otr if isinstance(_otr, list) else []):
            _created = str(o.get("created_at", ""))[:10]
            reports.append({
                "title": f"Email Draft: {o.get('subject', 'Untitled')}",
                "subject": "Email Drafts",
                "date": _created,
                "filename": f"outreach_{o.get('id', '')}",
                "size_kb": round(len(o.get("body", "")) / 1024, 1),
                "modified": 0,
                "url": f"/reports/outreach/{o.get('id', '')}",
                "source": "supabase",
                "_outreach": o,
            })
    except Exception:
        pass

    # Cap noisy categories to keep the list useful
    caps = {"System Alerts": 10, "General": 20, "Trading / Intel": 20}
    counts = {}
    filtered = []
    for r in reports:
        subj = r.get("subject", "General")
        counts[subj] = counts.get(subj, 0) + 1
        cap = caps.get(subj, 50)
        if counts[subj] <= cap:
            filtered.append(r)
    return filtered[:200]


@app.get("/reports/file/{filename}", response_class=_HTMLResponse)
def serve_report_file(filename: str):
    """Serve a report HTML file from any report directory."""
    for rdir in REPORT_DIRS:
        fpath = rdir / filename
        if fpath.exists() and fpath.is_file():
            return _HTMLResponse(content=fpath.read_text(errors="replace"))
        # Check subdirs
        for sub in rdir.iterdir():
            if sub.is_dir():
                fpath2 = sub / filename
                if fpath2.exists():
                    return _HTMLResponse(content=fpath2.read_text(errors="replace"))
    # Check for .md files and render as simple HTML
    for rdir in REPORT_DIRS:
        for candidate in [rdir / filename, rdir / (filename + ".md")]:
            if candidate.exists() and candidate.suffix == ".md":
                md_text = candidate.read_text(errors="replace")
                html_body = "<pre style=\"background:#0a0a0f;color:#e8e8f0;padding:24px;font-family:monospace;white-space:pre-wrap;\">" + md_text.replace("<","&lt;") + "</pre>"
                return _HTMLResponse(content=f"<html><head><title>{filename}</title></head><body style=\"margin:0;background:#0a0a0f\">{html_body}</body></html>")
    return _HTMLResponse(content="<h1>Report not found</h1>", status_code=404)


# Also serve the state contract matrix directly
@app.get("/reports/state-matrix", response_class=_HTMLResponse)
def serve_state_matrix():
    p = Path("/home/opc/hive_reports/state_contract_matrix__8_markets_20260324_0513.html")
    if p.exists():
        return _HTMLResponse(content=p.read_text(errors="replace"))
    return _HTMLResponse(content="<h1>State matrix not found</h1>", status_code=404)



@app.get("/reports/outreach/{outreach_id}", response_class=_HTMLResponse)
def serve_outreach_preview(outreach_id: str):
    """Render an email draft as a beautiful branded HTML preview."""
    import requests as _otr_req
    _sb_url = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
    _sb_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
    try:
        r = _otr_req.get(
            f"{_sb_url}/rest/v1/wholesale_outreach?id=eq.{outreach_id}&limit=1",
            headers={"apikey": _sb_key, "Authorization": f"Bearer {_sb_key}"},
            timeout=10,
        ).json()
        if not r:
            return _HTMLResponse("<h1>Draft not found</h1>", status_code=404)
        o = r[0]
    except Exception as e:
        return _HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

    subject = o.get("subject", "")
    body = o.get("body", "").replace("\n", "<br>")
    target = o.get("target_name", "")
    email = o.get("target_email", "")
    agent = o.get("agent_name", "Piper Reeves")
    status = o.get("status", "draft")
    tone = o.get("tone", "")
    notes = o.get("personalization_notes", "")
    created = str(o.get("created_at", ""))[:16]
    status_color = {"draft": "#ffd740", "verified": "#00e676", "sent": "#448aff", "replied": "#b388ff"}.get(status, "#888")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Email Draft: {subject}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:Inter,sans-serif;color:#e8e8f0;">
<div style="max-width:680px;margin:0 auto;background:#0a0a0f;">

  <div style="background:linear-gradient(135deg,#1a1a2e,#12121a);padding:24px;border-bottom:3px solid #c9a84c;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <p style="margin:0;font-size:20px;font-weight:700;letter-spacing:2px;">
          EVERLIGHT <span style="color:#c9a84c;">VENTURES</span>
        </p>
        <p style="margin:4px 0 0;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:3px;">
          Outreach Draft Preview
        </p>
      </div>
      <div style="background:{status_color}22;border:1px solid {status_color}44;border-radius:20px;padding:4px 16px;">
        <span style="color:{status_color};font-size:11px;font-weight:700;text-transform:uppercase;">{status}</span>
      </div>
    </div>
  </div>

  <div style="padding:24px;">
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:20px;margin-bottom:24px;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px 0;color:#666;font-size:12px;width:80px;">To</td><td style="padding:8px 0;color:#fff;font-size:14px;font-weight:600;">{target}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Email</td><td style="padding:8px 0;color:#888;font-size:13px;">{email or "Not yet verified"}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Subject</td><td style="padding:8px 0;color:#c9a84c;font-size:14px;font-weight:500;">{subject}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">From</td><td style="padding:8px 0;color:#888;font-size:13px;">{agent} &lt;piper@everlightventures.io&gt;</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Created</td><td style="padding:8px 0;color:#888;font-size:13px;">{created}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Tone</td><td style="padding:8px 0;color:#888;font-size:13px;">{tone}</td></tr>
      </table>
    </div>

    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="color:#c9a84c;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 16px;">Email Body</p>
      <div style="color:#ccc;font-size:14px;line-height:1.8;">{body}</div>
    </div>

    <div style="background:#1a0a0a;border:1px solid #2e1a1a;border-radius:12px;padding:16px;margin-bottom:24px;">
      <p style="color:#ff6b6b;font-size:10px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Internal -- Personalization Notes</p>
      <p style="color:#888;font-size:12px;line-height:1.6;margin:0;">{notes}</p>
    </div>
  </div>

  <div style="background:#12121a;padding:16px 24px;text-align:center;border-top:1px solid #1e1e2e;">
    <p style="color:#444;font-size:11px;margin:0;">Everlight Ventures LLC | Draft by {agent} | everlightventures.io</p>
  </div>

</div></body></html>"""

    return _HTMLResponse(content=html)



@app.get("/reports/contract/{package_name}/{filename}", response_class=_HTMLResponse)
def serve_contract_preview(package_name: str, filename: str):
    """Render a markdown contract as branded HTML."""
    PKGS = Path("/home/opc/hive_action_engine/deal_packages")
    md_path = PKGS / package_name / filename
    if not md_path.exists():
        md_path = PKGS / filename
    if not md_path.exists():
        return _HTMLResponse("<h1>Contract not found</h1>", status_code=404)

    md_text = md_path.read_text(errors="replace")

    # Convert markdown to styled HTML
    # Simple markdown rendering: headers, bold, lists, paragraphs
    import re as _cre
    body_html = md_text
    # Headers
    body_html = _cre.sub(r"^# (.+)$", r'<h1 style="color:#c9a84c;font-size:22px;margin:24px 0 12px;border-bottom:1px solid #1e1e2e;padding-bottom:8px;"></h1>', body_html, flags=_cre.MULTILINE)
    body_html = _cre.sub(r"^## (.+)$", r'<h2 style="color:#fff;font-size:17px;margin:20px 0 8px;"></h2>', body_html, flags=_cre.MULTILINE)
    body_html = _cre.sub(r"^### (.+)$", r'<h3 style="color:#ccc;font-size:15px;margin:16px 0 6px;"></h3>', body_html, flags=_cre.MULTILINE)
    # Bold
    body_html = _cre.sub(r"\*\*(.+?)\*\*", r"<strong style='color:#fff;'></strong>", body_html)
    # Horizontal rules
    body_html = body_html.replace("---", '<hr style="border:none;border-top:1px solid #1e1e2e;margin:16px 0;">')
    # Line breaks
    body_html = body_html.replace("\n", "<br>")
    # Bullet lists
    body_html = _cre.sub(r"^- (.+)$", r'<div style="padding:3px 0 3px 16px;color:#ccc;">&#8226; </div>', body_html, flags=_cre.MULTILINE)

    # Get property name for title
    prop_name = package_name.replace("_", " ").split(" 2026")[0] if "2026" in package_name else package_name

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Contract: {prop_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:Inter,sans-serif;color:#e8e8f0;">
<div style="max-width:680px;margin:0 auto;background:#0a0a0f;">

  <div style="background:linear-gradient(135deg,#1a1a2e,#12121a);padding:24px;border-bottom:3px solid #c9a84c;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <p style="margin:0;font-size:20px;font-weight:700;letter-spacing:2px;">
          EVERLIGHT <span style="color:#c9a84c;">VENTURES</span>
        </p>
        <p style="margin:4px 0 0;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:3px;">
          Assignment Contract
        </p>
      </div>
      <div style="background:#ff174422;border:1px solid #ff174444;border-radius:20px;padding:4px 16px;">
        <span style="color:#ff6b6b;font-size:11px;font-weight:700;text-transform:uppercase;">DRAFT -- REQUIRES LEGAL REVIEW</span>
      </div>
    </div>
  </div>

  <div style="padding:24px;">
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;line-height:1.8;font-size:14px;">
      {body_html}
    </div>

    <div style="background:#1a0a0a;border:1px solid #2e1a1a;border-radius:12px;padding:16px;margin-top:24px;">
      <p style="color:#ff6b6b;font-size:10px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Legal Disclaimer</p>
      <p style="color:#888;font-size:11px;line-height:1.6;margin:0;">This is a draft template for internal review only. A licensed attorney in the applicable state MUST review and approve before execution. Everlight Ventures is NOT a law firm.</p>
    </div>
  </div>

  <div style="background:#12121a;padding:16px 24px;text-align:center;border-top:1px solid #1e1e2e;">
    <p style="color:#444;font-size:11px;margin:0;">Everlight Ventures LLC | Assignment Contract Draft | everlightventures.io</p>
  </div>

</div></body></html>"""

    return _HTMLResponse(content=html)



# ── NEW: Macro Vision + Intelligence endpoints ──────────────────────

@app.get("/api/macro-vision")
def get_macro_vision():
    """Cycle-aware market intelligence -- macro + median + micro."""
    import sys
    sys.path.insert(0, str(BOT_DIR))
    try:
        from strategy.macro_vision import get_vision_summary
        snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json")
        price = float(snap.get("price") or 0)
        btc_price = float(snap.get("btc_price") or 0)
        btc_mom = float(snap.get("btc_momentum_pct") or 0) * 100
        if price <= 0:
            return {"error": "no price data"}
        vision = get_vision_summary(price, btc_price=btc_price, btc_change_24h_pct=btc_mom)
        return vision
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/hindsight")
def get_hindsight():
    """Missed trade analysis + opportunity scanner."""
    decisions = _read_jsonl_tail(BOT_DIR / "logs" / "decisions.jsonl", max_lines=200)
    # Find latest hindsight_scan entry
    hindsight = {}
    for d in reversed(decisions):
        if d.get("reason") == "hindsight_scan":
            hindsight = d
            break
    # Find latest macro_vision entry
    macro = {}
    for d in reversed(decisions):
        if d.get("reason") == "macro_vision":
            macro = d
            break
    return {"hindsight": hindsight, "macro": macro}


@app.get("/api/opportunities")
def get_opportunities():
    """Forward-looking opportunity scan from decision log."""
    decisions = _read_jsonl_tail(BOT_DIR / "logs" / "decisions.jsonl", max_lines=100)
    snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json")
    
    # Get latest next_play data
    next_long = snap.get("next_play_long")
    next_short = snap.get("next_play_short")
    
    # Get latest opportunities from hindsight scan
    opps = {}
    for d in reversed(decisions):
        if d.get("reason") == "hindsight_scan":
            opps = {
                "best_long": d.get("best_long"),
                "best_short": d.get("best_short"),
                "opp_ready": d.get("opp_ready", 0),
                "squeeze": d.get("squeeze", False),
            }
            break
    
    return {
        "next_play_long": next_long,
        "next_play_short": next_short,
        "opportunities": opps,
        "score_long": snap.get("v4_score_long"),
        "score_short": snap.get("v4_score_short"),
        "threshold": snap.get("adaptive_threshold"),
        "entry_type_long": snap.get("entry_type_long"),
        "entry_type_short": snap.get("entry_type_short"),
        "long_block": snap.get("long_block_reason"),
        "short_block": snap.get("short_block_reason"),
        "htf_trend": snap.get("htf_trend"),
        "vol_phase": snap.get("vol_phase"),
        "market_health": snap.get("market_health_score"),
        "market_regime": snap.get("market_regime"),
    }


@app.get("/api/cycle-history")
def get_cycle_history():
    """XLM historical cycle data for overlay charts."""
    return {
        "cycles": [
            {"cycle": 1, "low": 0.002, "low_date": "2017-01", "high": 0.938, "high_date": "2018-01", "retrace": 0.040, "retrace_date": "2018-12", "retrace_pct": 95.7},
            {"cycle": 2, "low": 0.026, "low_date": "2020-03", "high": 0.799, "high_date": "2021-05", "retrace": 0.071, "retrace_date": "2022-12", "retrace_pct": 91.1},
            {"cycle": 3, "low": 0.076, "low_date": "2024-07", "high": 0.634, "high_date": "2024-11", "retrace": None, "retrace_date": None, "retrace_pct": None},
        ],
        "ath": {"price": 0.938, "date": "2018-01-04"},
        "halvings": [
            {"date": "2016-07-09", "label": "BTC Halving 2"},
            {"date": "2020-05-11", "label": "BTC Halving 3"},
            {"date": "2024-04-20", "label": "BTC Halving 4"},
        ],
        "current_price": float((_read_json(BOT_DIR / "logs" / "dashboard_snapshot.json") or {}).get("price") or 0),
    }


@app.get("/api/trade-analytics")
def get_trade_analytics():
    """Deep trade analytics -- strategy breakdown, R:R, streaks."""
    trades = _read_jsonl_tail(BOT_DIR / "logs" / "trades.csv", max_lines=200)
    
    # Parse CSV trades
    import csv, io
    csv_path = BOT_DIR / "logs" / "trades.csv"
    if not csv_path.exists():
        return {"error": "no trades file"}
    
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    if not rows:
        return {"trades": 0}
    
    # Analytics
    total = len(rows)
    wins = [r for r in rows if r.get("result") == "win"]
    losses = [r for r in rows if r.get("result") == "loss"]
    
    win_pnls = [float(r.get("pnl_usd", 0) or 0) for r in wins]
    loss_pnls = [float(r.get("pnl_usd", 0) or 0) for r in losses]
    
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    total_pnl = sum(float(r.get("pnl_usd", 0) or 0) for r in rows)
    
    # By strategy
    by_strategy = {}
    for r in rows:
        et = r.get("entry_type", "unknown")
        if et not in by_strategy:
            by_strategy[et] = {"wins": 0, "losses": 0, "pnl": 0}
        if r.get("result") == "win":
            by_strategy[et]["wins"] += 1
        else:
            by_strategy[et]["losses"] += 1
        by_strategy[et]["pnl"] += float(r.get("pnl_usd", 0) or 0)
    
    # By direction
    longs = [r for r in rows if r.get("direction") == "long"]
    shorts = [r for r in rows if r.get("direction") == "short"]
    long_pnl = sum(float(r.get("pnl_usd", 0) or 0) for r in longs)
    short_pnl = sum(float(r.get("pnl_usd", 0) or 0) for r in shorts)
    
    # Streaks
    current_streak = 0
    streak_type = ""
    for r in reversed(rows):
        if r.get("result") == "win":
            if streak_type == "win" or streak_type == "":
                current_streak += 1
                streak_type = "win"
            else:
                break
        elif r.get("result") == "loss":
            if streak_type == "loss" or streak_type == "":
                current_streak += 1
                streak_type = "loss"
            else:
                break
    
    # Best/worst trade
    all_pnls = [(float(r.get("pnl_usd", 0) or 0), r.get("entry_type", "?"), r.get("direction", "?")) for r in rows]
    best = max(all_pnls, key=lambda x: x[0]) if all_pnls else (0, "?", "?")
    worst = min(all_pnls, key=lambda x: x[0]) if all_pnls else (0, "?", "?")
    
    # Daily P&L
    daily = {}
    for r in rows:
        ts = r.get("exit_time", r.get("timestamp", ""))[:10]
        if ts:
            if ts not in daily:
                daily[ts] = {"pnl": 0, "trades": 0, "wins": 0, "losses": 0}
            daily[ts]["pnl"] += float(r.get("pnl_usd", 0) or 0)
            daily[ts]["trades"] += 1
            if r.get("result") == "win":
                daily[ts]["wins"] += 1
            else:
                daily[ts]["losses"] += 1
    
    daily_list = [{"date": k, **v} for k, v in sorted(daily.items())]
    
    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "total_pnl": round(total_pnl, 2),
        "best_trade": {"pnl": best[0], "strategy": best[1], "direction": best[2]},
        "worst_trade": {"pnl": worst[0], "strategy": worst[1], "direction": worst[2]},
        "current_streak": current_streak,
        "streak_type": streak_type,
        "by_strategy": by_strategy,
        "long_pnl": round(long_pnl, 2),
        "short_pnl": round(short_pnl, 2),
        "long_count": len(longs),
        "short_count": len(shorts),
        "daily_pnl": daily_list[-30:],
    }


@app.get("/api/moonshot-status")
def get_moonshot_status():
    """Current moonshot mode status."""
    snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json")
    pos = snap.get("position") or snap.get("open_position") or {}
    ms = pos.get("moonshot_state") or {}
    return {
        "active": ms.get("active", False),
        "activation_reason": ms.get("activation_reason"),
        "peak_price": ms.get("peak_price"),
        "trailing_stop": ms.get("trailing_stop_price"),
        "bars_active": ms.get("bars_active", 0),
        "stale_bars": ms.get("stale_bars", 0),
        "in_position": bool(pos.get("direction")),
        "direction": pos.get("direction"),
        "entry_price": pos.get("entry_price"),
        "size": pos.get("size"),
    }



@app.get("/api/goals")
def get_goals():
    """Dynamic P&L goal tracking with loss recovery."""
    import sys, csv
    sys.path.insert(0, str(BOT_DIR))
    try:
        from strategy.goal_tracker import compute_goals
        # Load today's trades from trades.csv
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")
        trades_today = []
        csv_path = BOT_DIR / "logs" / "trades.csv"
        if csv_path.exists():
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = row.get("exit_time", row.get("timestamp", ""))[:10]
                    if ts == today:
                        trades_today.append(row)
        return compute_goals(trades_today=trades_today)
    except Exception as e:
        return {"error": str(e)}



@app.get("/api/mindset")
def get_mindset():
    """Bot's current trading mindset and work ethic."""
    decisions = _read_jsonl_tail(BOT_DIR / "logs" / "decisions.jsonl", max_lines=50)
    mindset = {}
    for d in reversed(decisions):
        if d.get("reason") == "trading_mindset":
            mindset = d
            break
    goals = {}
    try:
        import sys, csv
        sys.path.insert(0, str(BOT_DIR))
        from strategy.goal_tracker import compute_goals
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")
        trades_today = []
        csv_path = BOT_DIR / "logs" / "trades.csv"
        if csv_path.exists():
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get("exit_time", row.get("timestamp", ""))[:10]) == today:
                        trades_today.append(row)
        goals = compute_goals(trades_today=trades_today)
    except Exception:
        pass
    return {"mindset": mindset, "goals": goals}


@app.get("/api/brain/status")
@app.get("/brain/status")
def get_brain_status():
    """Expose neuromorphic knowledge state for the React dashboard."""
    if get_ai_brain_status is None:
        return {"available": False, "error": "brain_knowledge_unavailable"}
    try:
        status = get_ai_brain_status()
        return status if isinstance(status, dict) else {"available": False}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/brain/search")
@app.get("/brain/search")
def get_brain_search(q: str, limit: int = 5):
    """Search the local AI brain knowledge corpus."""
    if search_ai_brain is None:
        return {"results": [], "error": "brain_knowledge_unavailable"}
    try:
        results = search_ai_brain(q, top_k=max(1, min(limit, 10)))
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.get("/api/report-card")
def get_report_card():
    """Unified scoring engine report card -- the play-call breakdown."""
    snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json")
    if not snap:
        return {"active": False}

    # Pull unified_* fields from snapshot
    score = snap.get("unified_score")
    if score is None:
        return {"active": False}

    return {
        "active": True,
        "score": int(score or 0),
        "base_score": int(snap.get("unified_base") or 0),
        "threshold": int(snap.get("unified_threshold") or 60),
        "tier": snap.get("unified_tier", "NO_TRADE"),
        "recommendation": snap.get("unified_recommendation", "HOLD"),
        "direction": snap.get("unified_direction", ""),
        "entry_type": snap.get("unified_entry_type", ""),
        "regime": snap.get("unified_regime", "neutral"),
        "modifiers": snap.get("unified_modifiers") or {},
        "narrative": snap.get("unified_narrative", ""),
        "reasons": snap.get("unified_reasons") or [],
        "alternatives": snap.get("unified_alternatives") or [],
        "p_win": float(snap.get("unified_p_win") or 0),
        "rr_ratio": float(snap.get("unified_rr_ratio") or 0),
        "profit_est": float(snap.get("unified_profit_est") or 0),
        "eyeball": snap.get("unified_eyeball") or {},
        "foresight": snap.get("foresight") or {},
        "candle_math": snap.get("candle_math") or {},
        "ai_advisor": _get_ai_advisor_state(),
        "trap_analysis": snap.get("trap_analysis") or {},
        "combo": {
            "macro": snap.get("macro_regime") or (snap.get("foresight") or {}).get("bias", "").upper() or "NEUTRAL",
            "mini": snap.get("mini_structure") or "RANGING",
            "entry_tf": snap.get("entry_timeframe") or snap.get("unified_entry_type", ""),
        },
        "ts": snap.get("unified_ts", ""),
    }


def _get_ai_advisor_state() -> dict:
    """Get AI advisor's current thinking from decisions log."""
    try:
        decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=200)
        ai_state = {
            "last_insight": None,
            "last_directive": None,
            "score_adjustment": 0,
            "thought_process": [],
            "modifiers_active": {},
        }
        # Get the latest unified_score with modifiers
        snap = _read_json(BOT_DIR / "logs" / "dashboard_snapshot.json") or {}
        mods = snap.get("unified_modifiers") or {}
        ai_state["modifiers_active"] = {k: v for k, v in mods.items() if v != 0}

        # Get recent AI-relevant decisions
        for d in reversed(decisions):
            r = d.get("reason", "")
            if r == "unified_score":
                ai_state["last_insight"] = {
                    "score": d.get("final_score"),
                    "threshold": d.get("threshold"),
                    "direction": d.get("direction"),
                    "entry_type": d.get("entry_type"),
                    "recommendation": d.get("recommendation"),
                    "narrative": d.get("narrative", ""),
                    "quality_tier": d.get("quality_tier"),
                }
                break

        # Get foresight
        fs = snap.get("foresight") or {}
        if fs:
            ai_state["foresight_bias"] = fs.get("bias")
            ai_state["foresight_rsi"] = fs.get("rsi_state")
            ai_state["scenarios"] = fs.get("scenarios", [])
            ai_state["projected_profit"] = "$%s-%s" % (
                round(fs.get("projected_profit_conservative", 0)),
                round(fs.get("projected_profit_best", 0)))

        # Get recent thoughts (macro vision, mindset, hindsight)
        thoughts = []
        seen = set()
        for d in reversed(decisions[-50:]):
            r = d.get("reason", "")
            t = d.get("thought", "")
            if r in ("trading_mindset", "macro_vision", "hindsight_scan", "unified_score", "unified_hold") and t and r not in seen:
                thoughts.append({"type": r, "thought": t[:200], "ts": d.get("timestamp", "")[11:19]})
                seen.add(r)
                if len(thoughts) >= 5:
                    break
        ai_state["thought_process"] = thoughts

        # Current position awareness
        pos = snap.get("position") or snap.get("open_position")
        if isinstance(pos, dict) and pos.get("entry_price"):
            ai_state["position_awareness"] = {
                "direction": pos.get("direction"),
                "entry_type": pos.get("entry_type"),
                "quality_tier": pos.get("quality_tier"),
            }

        return ai_state
    except Exception:
        return {}


# ============================================================
# BROKER OS / WHOLESALE PIPELINE ENDPOINTS
# ============================================================

SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww")

def _sb_fetch(table, params=""):
    """Fetch from Supabase REST API."""
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except Exception:
        return []

@app.get("/api/broker/stats")
def broker_stats():
    """Pipeline KPIs."""
    stats = {}
    for status in ["new", "contacted", "negotiating", "under_contract", "marketing", "closed", "cold"]:
        r = _sb_fetch("wholesale_sellers", f"status=eq.{status}&select=id")
        stats[f"sellers_{status}"] = len(r) if isinstance(r, list) else 0

    stats["sellers_total"] = sum(v for k, v in stats.items() if k.startswith("sellers_"))

    buyers = _sb_fetch("wholesale_buyers", "select=id")
    stats["buyers_total"] = len(buyers) if isinstance(buyers, list) else 0

    deals = _sb_fetch("wholesale_deals", "select=id,status,assignment_fee,actual_profit")
    stats["deals_total"] = len(deals) if isinstance(deals, list) else 0
    stats["deals_active"] = sum(1 for d in deals if d.get("status") not in ("closed", "dead")) if isinstance(deals, list) else 0
    stats["deals_closed"] = sum(1 for d in deals if d.get("status") == "closed") if isinstance(deals, list) else 0
    stats["revenue_total"] = sum(float(d.get("actual_profit") or 0) for d in deals) if isinstance(deals, list) else 0
    stats["pipeline_value"] = sum(float(d.get("assignment_fee") or 10000) for d in deals if d.get("status") not in ("closed", "dead")) if isinstance(deals, list) else 0

    outreach = _sb_fetch("wholesale_outreach", "select=id,status")
    if isinstance(outreach, list):
        stats["outreach_sent"] = sum(1 for o in outreach if o.get("status") == "sent")
        stats["outreach_replied"] = sum(1 for o in outreach if o.get("status") == "replied")
        stats["outreach_bounced"] = sum(1 for o in outreach if o.get("status") == "bounced")
        stats["outreach_pending"] = sum(1 for o in outreach if o.get("status") in ("draft", "pending"))

    return stats

@app.get("/api/broker/sellers")
def broker_sellers(status: str = None, state: str = None, limit: int = 100):
    """List wholesale sellers with optional filters."""
    params = f"order=priority_score.desc&limit={limit}"
    if status:
        params += f"&status=eq.{status}"
    if state:
        params += f"&state=eq.{state}"
    return _sb_fetch("wholesale_sellers", params)

@app.get("/api/broker/buyers")
def broker_buyers(state: str = None, limit: int = 100):
    """List wholesale buyers."""
    params = f"order=created_at.desc&limit={limit}"
    if state:
        params += f"&state=eq.{state}"
    return _sb_fetch("wholesale_buyers", params)

@app.get("/api/broker/deals")
def broker_deals(status: str = None, limit: int = 50):
    """List wholesale deals."""
    params = f"order=created_at.desc&limit={limit}"
    if status:
        params += f"&status=eq.{status}"
    return _sb_fetch("wholesale_deals", params)

@app.get("/api/broker/outreach")
def broker_outreach(limit: int = 50):
    """Recent outreach activity."""
    return _sb_fetch("wholesale_outreach", f"order=created_at.desc&limit={limit}")

@app.get("/api/broker/states")
def broker_states():
    """State priority list."""
    return _sb_fetch("wholesale_states", "order=ease_score.desc")


def _register_clean_dashboard_aliases():
    """Support the React app's clean paths alongside /api/* endpoints."""
    aliases = [
        ("/status", get_status),
        ("/decisions", get_decisions),
        ("/events", get_events),
        ("/candles", get_candles),
        ("/charts", get_all_charts),
        ("/market-context", get_market_context),
        ("/daily-summary", get_daily_summary),
        ("/active-strategy", get_active_strategy),
        ("/macro-vision", get_macro_vision),
        ("/hindsight", get_hindsight),
        ("/opportunities", get_opportunities),
        ("/cycle-history", get_cycle_history),
        ("/trade-analytics", get_trade_analytics),
        ("/moonshot-status", get_moonshot_status),
        ("/goals", get_goals),
        ("/mindset", get_mindset),
        ("/report-card", get_report_card),
    ]
    for path, endpoint in aliases:
        app.add_api_route(path, endpoint, methods=["GET"], include_in_schema=False)


_register_clean_dashboard_aliases()


# ── Onboarding endpoint ──
@app.get("/api/onboard")
def onboard_page():
    """Client onboarding form (gold/black branded)."""
    from fastapi.responses import HTMLResponse
    html = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Deploy Your AI Team</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Inter,-apple-system,sans-serif;background:#0a0a0a;color:#f0f0f0;min-height:100vh}.c{max-width:700px;margin:0 auto;padding:30px 20px}.gb{height:3px;background:linear-gradient(90deg,#d4a017,#f5d060,#d4a017);margin-bottom:30px}h1{font-size:2rem;font-weight:800;background:linear-gradient(135deg,#d4a017,#f5d060);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}.sub{color:#888;font-size:.9rem;margin-bottom:30px}.s{background:#111;border:1px solid #222;border-radius:12px;padding:24px;margin-bottom:16px}.s:hover{border-color:#d4a017}.sh{display:flex;align-items:center;gap:12px;margin-bottom:12px}.sn{width:32px;height:32px;background:linear-gradient(135deg,#d4a017,#b8860b);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;color:#0a0a0a}.st{font-size:1rem;font-weight:700}label{display:block;font-size:.8rem;color:#aaa;margin:10px 0 4px}input,textarea{width:100%;padding:10px 14px;background:#1a1a1a;border:1px solid #333;border-radius:8px;color:#f0f0f0;font-size:.9rem}input:focus,textarea:focus{outline:none;border-color:#d4a017}.ag{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}.ac{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:10px;cursor:pointer}.ac:hover{border-color:#d4a017}.ac.sel{border-color:#d4a017;background:#1a1500}.an{font-weight:700;font-size:.85rem}.ar{font-size:.7rem;color:#888}.btn{display:block;width:100%;padding:14px;background:linear-gradient(135deg,#d4a017,#b8860b);border:none;border-radius:10px;color:#0a0a0a;font-size:1rem;font-weight:800;cursor:pointer;margin-top:24px}.btn:hover{box-shadow:0 8px 24px rgba(212,160,23,.3)}.ok{background:#1a2a1a;border:1px solid #2a7d2a;border-radius:12px;padding:24px;text-align:center;display:none}.ok h2{color:#4ade80;margin-bottom:8px}</style></head><body><div class="gb"></div><div class="c"><h1>Deploy Your AI Team</h1><p class="sub">Connect your tools. Pick your agents. Go live in minutes.</p><form id="f"><div class="s"><div class="sh"><div class="sn">1</div><div class="st">Your Company</div></div><label>Company Name</label><input name="company_name" required placeholder="Acme Corp"><label>Your Name</label><input name="contact_name" required placeholder="Jane Smith"><label>Email</label><input type="email" name="email" required placeholder="jane@acme.com"><label>Business Description</label><textarea name="desc" rows="2" placeholder="We sell B2B SaaS..."></textarea></div><div class="s"><div class="sh"><div class="sn">2</div><div class="st">Connect Slack</div></div><label>Slack Workspace URL</label><input name="slack" placeholder="https://your-team.slack.com"></div><div class="s"><div class="sh"><div class="sn">3</div><div class="st">Pick Your Team</div></div><div class="ag"><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Marcus Cole</div><div class="ar">Chief Operator - dispatches team, daily briefs</div></div><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Piper Reeves</div><div class="ar">Outreach - email campaigns, follow-ups</div></div><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Penny Vance</div><div class="ar">Profit - revenue tracking, deal analysis</div></div><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Cipher Wolfe</div><div class="ar">Intel - market research, trends</div></div><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Vera Lux</div><div class="ar">Content - social, blog, brand voice</div></div><div class="ac" onclick="this.classList.toggle(\'sel\')"><div class="an">Franklin Steele</div><div class="ar">Engineer - tools, dashboards, code</div></div></div></div><button type="submit" class="btn">Deploy Your AI Team</button></form><div id="ok" class="ok"><h2>Team Deployed!</h2><p style="color:#aaa">We\'ll reach out within 24h to connect your Slack and activate your agents.</p></div></div><script>document.getElementById("f").onsubmit=function(e){e.preventDefault();var a=[];document.querySelectorAll(".ac.sel").forEach(function(c){a.push(c.querySelector(".an").textContent)});var d=new FormData(this);fetch("/api/onboard-submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({company:d.get("company_name"),contact:d.get("contact_name"),email:d.get("email"),desc:d.get("desc"),slack:d.get("slack"),agents:a})}).then(function(){document.getElementById("f").style.display="none";document.getElementById("ok").style.display="block"}).catch(function(){document.getElementById("f").style.display="none";document.getElementById("ok").style.display="block"})}</script></body></html>'
    return HTMLResponse(content=html)


@app.post("/api/onboard-submit")
def onboard_submit(data: dict):
    """Process onboarding -> Blinko + Slack #ai-consulting."""
    import urllib.request as ur
    company = data.get("company", "")
    contact = data.get("contact", "")
    email = data.get("email", "")
    agents = data.get("agents", [])

    # Log to Blinko
    try:
        note = f"# New Customer: {company}\n#hive/onboard #hive/customer\n\nContact: {contact} ({email})\nAgents: {', '.join(agents)}"
        payload = json.dumps({"content": note, "type": 1}).encode()
        req = ur.Request("http://129.159.38.250:1111/api/v1/note/upsert", data=payload, method="POST", headers={"Content-Type": "application/json"})
        ur.urlopen(req, timeout=10)
    except Exception:
        pass

    # Slack alert
    try:
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        if token:
            msg = f":tada: *New Hive Mind Customer*\nCompany: {company}\nContact: {contact} ({email})\nAgents: {', '.join(agents)}"
            payload = json.dumps({"channel": "C0AN8SGAS22", "text": msg}).encode()
            req = ur.Request("https://slack.com/api/chat.postMessage", data=payload, method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
            ur.urlopen(req, timeout=10)
    except Exception:
        pass

    return {"ok": True, "company": company}


# ===================================================================
# CHANGELOG -- what was updated, when, organized by day
# ===================================================================

@app.get("/api/changelog")
def get_changelog(date: str = "", week: str = "", month: str = ""):
    """What we updated and when. Midnight-to-midnight PT days.

    Query params:
        date: YYYY-MM-DD -- single day
        week: YYYY-WNN (e.g. 2026-W15) -- single week
        month: YYYY-MM -- single month
        (none) -- last 7 days
    """
    changelog_path = LOGS_DIR / "changelog.jsonl"
    if not changelog_path.exists():
        return {"days": [], "filter": {"date": date, "week": week, "month": month}}

    entries = _read_jsonl_tail(changelog_path, max_lines=500)

    # Filter
    if date:
        entries = [e for e in entries if e.get("date") == date]
    elif week:
        # Parse YYYY-WNN
        entries = [e for e in entries if _entry_in_week(e, week)]
    elif month:
        entries = [e for e in entries if e.get("date", "").startswith(month)]
    else:
        # Default: last 7 days
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=7) - timedelta(days=7)).strftime("%Y-%m-%d")
        entries = [e for e in entries if e.get("date", "") >= cutoff]

    # Group by day
    from collections import OrderedDict
    days = OrderedDict()
    for e in sorted(entries, key=lambda x: x.get("timestamp", "")):
        d = e.get("date", "unknown")
        if d not in days:
            days[d] = {"date": d, "updates": []}
        days[d]["updates"].append({
            "time": e.get("time", ""),
            "category": e.get("category", ""),
            "summary": e.get("summary", ""),
            "details": e.get("details", ""),
            "files": e.get("files_changed", []),
        })

    return {
        "days": list(days.values()),
        "total_updates": len(entries),
        "filter": {"date": date, "week": week, "month": month},
    }


@app.get("/api/changelog/today")
def get_changelog_today():
    """What was updated today."""
    pt_now = datetime.now(timezone.utc) - timedelta(hours=7)
    return get_changelog(date=pt_now.strftime("%Y-%m-%d"))


def _entry_in_week(entry, week_str):
    """Check if a changelog entry falls in a given ISO week (YYYY-WNN)."""
    try:
        d = entry.get("date", "")
        if not d:
            return False
        from datetime import datetime as _dt
        dt = _dt.strptime(d, "%Y-%m-%d")
        iso = dt.isocalendar()
        return week_str == f"{iso[0]}-W{iso[1]:02d}"
    except Exception:
        return False


@app.post("/api/changelog/add")
def add_changelog_entry(entry: dict):
    """Add a changelog entry. Called by deploy scripts or manually."""
    from datetime import datetime, timezone, timedelta
    pt_now = datetime.now(timezone.utc) - timedelta(hours=7)
    h = pt_now.hour
    m = pt_now.minute
    ampm = "am" if h < 12 else "pm"
    h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)

    record = {
        "timestamp": pt_now.isoformat(),
        "date": pt_now.strftime("%Y-%m-%d"),
        "time": f"{h12}:{m:02d} {ampm}",
        "category": entry.get("category", "update"),
        "summary": entry.get("summary", ""),
        "details": entry.get("details", ""),
        "files_changed": entry.get("files_changed", []),
    }

    changelog_path = LOGS_DIR / "changelog.jsonl"
    with open(changelog_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    return {"ok": True, "entry": record}


# ===================================================================
# ORGANIZED TRADE HISTORY -- midnight-to-midnight PT, by day/week/month
# Paper/ghost trades in separate section. Real trades only in main view.
# ===================================================================

def _parse_all_trades_organized():
    """Read trades_organized.csv (or trades.csv) and return structured data.
    Separates real vs paper/ghost. Groups by day (midnight PT boundaries)."""
    import csv as _csv
    trades_path = LOGS_DIR / "trades_organized.csv"
    if not trades_path.exists():
        trades_path = LOGS_DIR / "trades.csv"
    if not trades_path.exists():
        return [], []

    real = []
    paper = []
    with open(trades_path) as f:
        for row in _csv.DictReader(f):
            if not row.get("exit_price") or not row.get("pnl_usd"):
                continue  # Skip entries without exits

            pnl = float(row.get("pnl_usd") or 0)
            fees = float(row.get("total_fees_usd") or 0)
            result = row.get("result", "")
            side = row.get("side", "")
            entry_p = float(row.get("entry_price") or 0)
            exit_p = float(row.get("exit_price") or 0)

            # Use organized columns if available, otherwise parse
            date_pt = row.get("date_pt", "")
            time_pt = row.get("time_pt", "")
            exit_date_pt = row.get("exit_date_pt", "")
            exit_time_pt = row.get("exit_time_pt", "")
            dur = row.get("duration_min", "")
            session = row.get("session", "")

            if not date_pt:
                # Fallback: parse from timestamp
                ts = row.get("entry_time") or row.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    pt_dt = dt - timedelta(hours=7)
                    date_pt = pt_dt.strftime("%Y-%m-%d")
                    time_pt = pt_dt.strftime("%H:%M:%S")
                except Exception:
                    continue

            # 12hr format
            def to_12hr(t24):
                if not t24 or len(t24) < 5:
                    return ""
                h = int(t24[:2])
                m = t24[3:5]
                ampm = "am" if h < 12 else "pm"
                h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
                return f"{h12}:{m} {ampm}"

            trade = {
                "date": date_pt,
                "time": to_12hr(time_pt),
                "exit_date": exit_date_pt,
                "exit_time": to_12hr(exit_time_pt),
                "side": side,
                "entry_price": entry_p,
                "exit_price": exit_p,
                "result": result,
                "pnl": round(pnl, 2),
                "fees": round(fees, 2),
                "duration_min": float(dur) if dur else None,
                "session": session,
                "exit_reason": row.get("exit_reason", ""),
                "entry_type": row.get("entry_type", ""),
                "unified_score": row.get("unified_score", ""),
                "order_id": row.get("order_id", ""),
                "time_sort": time_pt,
            }

            # Separate paper/ghost from real
            # Paper = explicitly marked paper OR has "paper" in order_id
            # Real = everything else (including exchange_side_close with no order_id)
            _paper_flag = str(row.get("paper", "")).strip().lower()
            _order_id = row.get("order_id", "") or ""
            is_paper = (_paper_flag == "true"
                        or "paper" in _order_id.lower())
            if is_paper:
                trade["label"] = "paper"
                paper.append(trade)
            else:
                trade["label"] = "real"
                real.append(trade)

    return real, paper


@app.get("/api/trades/history")
def get_trade_history(month: str = "", date: str = ""):
    """Organized trade history grouped by day.
    Each day: 12:00 am - 11:59 pm PT. Blank row between days.

    Query params:
        month: YYYY-MM (e.g. 2026-04) -- filter to month
        date: YYYY-MM-DD -- filter to specific day

    Returns real trades grouped by day + paper trades in separate section.
    """
    real, paper = _parse_all_trades_organized()

    # Filter
    if date:
        real = [t for t in real if t["date"] == date]
        paper = [t for t in paper if t["date"] == date]
    elif month:
        real = [t for t in real if t["date"].startswith(month)]
        paper = [t for t in paper if t["date"].startswith(month)]

    # Group by day
    from collections import OrderedDict
    days = OrderedDict()
    for t in sorted(real, key=lambda x: x["date"] + " " + (x.get("time_sort") or "")):
        d = t["date"]
        if d not in days:
            days[d] = {"date": d, "trades": [], "wins": 0, "losses": 0, "pnl": 0.0, "fees": 0.0}
        days[d]["trades"].append(t)
        days[d]["pnl"] += t["pnl"]
        days[d]["fees"] += t["fees"]
        if t["result"] == "win":
            days[d]["wins"] += 1
        elif t["result"] == "loss":
            days[d]["losses"] += 1

    # Round day totals
    for d in days.values():
        total = d["wins"] + d["losses"]
        d["pnl"] = round(d["pnl"], 2)
        d["fees"] = round(d["fees"], 2)
        d["trade_count"] = total
        d["win_rate"] = round(d["wins"] / total * 100) if total > 0 else 0

    # Paper trades grouped same way
    paper_days = OrderedDict()
    for t in sorted(paper, key=lambda x: x["date"] + " " + (x.get("time_sort") or "")):
        d = t["date"]
        if d not in paper_days:
            paper_days[d] = {"date": d, "trades": [], "count": 0}
        paper_days[d]["trades"].append(t)
        paper_days[d]["count"] += 1

    # Available months for navigation
    all_months = sorted(set(t["date"][:7] for t in real)) if real else []

    # Grand totals
    total_pnl = sum(d["pnl"] for d in days.values())
    total_wins = sum(d["wins"] for d in days.values())
    total_losses = sum(d["losses"] for d in days.values())
    total_trades = total_wins + total_losses
    total_fees = sum(d["fees"] for d in days.values())

    return {
        "days": list(days.values()),
        "paper_trades": list(paper_days.values()),
        "summary": {
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": round(total_wins / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "total_fees": round(total_fees, 2),
        },
        "months": all_months,
        "filter": {"month": month, "date": date},
    }


@app.get("/api/trades/today")
def get_trades_today():
    """Today's trades only. 12:00 am - 11:59 pm PT. Real trades only."""
    pt_now = datetime.now(timezone.utc) - timedelta(hours=7)
    today = pt_now.strftime("%Y-%m-%d")
    return get_trade_history(date=today)


# ===================================================================
# POSITION AGGREGATOR -- Coinbase-style flat-to-flat P&L + fee intel
# ===================================================================

@app.get("/api/positions")
def get_positions(date: str = ""):
    """Aggregate partial fills into Coinbase-style positions.

    Groups fills into flat-to-flat round trips. Shows:
    - Avg entry/exit price per position
    - Number of partial fills
    - Total fees vs gross P&L
    - Loss attribution (fees vs signal vs slippage)

    This matches what Coinbase shows in the portfolio view.
    """
    try:
        import sys as _sys
        _strategy_dir = str(BOT_DIR / "strategy")
        if _strategy_dir not in _sys.path:
            _sys.path.insert(0, _strategy_dir)
        from fee_intelligence import aggregate_positions_from_csv
    except ImportError:
        return {"error": "fee_intelligence module not found", "positions": []}

    csv_path = LOGS_DIR / "trades_organized.csv"
    if not csv_path.exists():
        csv_path = LOGS_DIR / "trades.csv"

    positions = aggregate_positions_from_csv(str(csv_path))

    # Filter by date
    if date:
        positions = [p for p in positions if p.get("date") == date]

    # Summary
    closed = [p for p in positions if p.get("result") != "open"]
    wins = sum(1 for p in closed if p.get("result") == "win")
    losses = sum(1 for p in closed if p.get("result") == "loss")
    total_pnl = sum(p.get("net_pnl", 0) for p in closed)
    total_fees = sum(p.get("total_fees", 0) for p in closed)
    total_gross = sum(p.get("gross_pnl", 0) for p in closed)

    # Fee attribution breakdown
    fee_caused = sum(1 for p in closed if p.get("loss_cause") == "fees")
    signal_caused = sum(1 for p in closed if p.get("loss_cause") == "signal")

    return {
        "positions": positions[-50:],  # last 50
        "summary": {
            "total_positions": len(closed),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / max(wins + losses, 1) * 100),
            "net_pnl": round(total_pnl, 2),
            "gross_pnl": round(total_gross, 2),
            "total_fees": round(total_fees, 2),
            "fee_pct_of_gross": round(total_fees / max(abs(total_gross), 0.01) * 100, 1),
            "losses_from_fees": fee_caused,
            "losses_from_signal": signal_caused,
        },
        "filter": {"date": date},
    }


@app.get("/api/positions/today")
def get_positions_today():
    pt_now = datetime.now(timezone.utc) - timedelta(hours=7)
    return get_positions(date=pt_now.strftime("%Y-%m-%d"))


@app.get("/api/fee-intel")
def get_fee_intel():
    """Fee intelligence dashboard -- churn detection, lane health, fee attribution."""
    try:
        import sys as _sys
        _strategy_dir = str(BOT_DIR / "strategy")
        if _strategy_dir not in _sys.path:
            _sys.path.insert(0, _strategy_dir)
        from fee_intelligence import get_fee_intelligence_summary
    except ImportError:
        return {"error": "fee_intelligence module not found"}

    # Load bot state to get fee intel data
    state_path = LOGS_DIR / "dashboard_snapshot.json"
    state = _read_json(state_path)
    return get_fee_intelligence_summary(state)


# Serve React static files
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    @app.get("/{path:path}")
    def serve_spa(path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
