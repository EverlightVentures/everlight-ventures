#!/usr/bin/env python3
"""Metrics exporter -- runs on Oracle via cron every minute.
Reads state.json + trades.csv, writes metrics.json for remote monitoring."""

import json, os, csv, time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.environ.get("CRYPTO_BOT_DIR", os.path.dirname(os.path.abspath(__file__))))
DATA = BASE / "data"
LOGS = BASE / "logs"
OUT  = DATA / "metrics.json"

def load_state():
    p = DATA / "state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def load_trades_today(day_str):
    p = LOGS / "trades.csv"
    if not p.exists():
        return []
    trades = []
    try:
        with open(p) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("timestamp", "").startswith(day_str):
                    trades.append(row)
    except Exception:
        pass
    return trades

def heartbeat_age():
    # Primary: .heartbeat file. Fallback: state.json mtime.
    hb = BASE / ".heartbeat"
    if hb.exists():
        return time.time() - hb.stat().st_mtime
    sj = DATA / "state.json"
    if sj.exists():
        return time.time() - sj.stat().st_mtime
    return -1

def build_metrics():
    state = load_state()
    now = datetime.now(timezone.utc)
    day_str = state.get("day", now.strftime("%Y-%m-%d"))
    trades = load_trades_today(day_str)

    wins = sum(1 for t in trades if t.get("result") == "win")
    losses = sum(1 for t in trades if t.get("result") == "loss")
    total = wins + losses
    win_rate = round(wins / total * 100, 1) if total > 0 else 0.0

    total_pnl = sum(float(t.get("pnl_usd", 0)) for t in trades)
    total_fees = sum(float(t.get("total_fees_usd", 0)) for t in trades)

    hb_age = heartbeat_age()

    return {
        "generated_at": now.isoformat(),
        "heartbeat_age_s": round(hb_age, 1),
        "bot_alive": 0 < hb_age < 120,
        "session_id": state.get("session_id", "unknown"),
        "day": day_str,
        "equity_start_usd": state.get("equity_start_usd", 0),
        "exchange_equity_usd": state.get("exchange_equity_usd"),
        "pnl_today_usd": round(state.get("pnl_today_usd", 0), 4),
        "exchange_pnl_today_usd": round(state.get("exchange_pnl_today_usd", 0), 4),
        "trades_today": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "total_fees_usd": round(total_fees, 4),
        "vol_state": state.get("vol_state", "unknown"),
        "recovery_mode": state.get("recovery_mode", "NORMAL"),
        "open_position": bool(state.get("open_position")),
        "position_side": (state.get("open_position") or {}).get("side", None),
        "overnight_ok": state.get("_overnight_trading_ok", "unknown"),
        "safe_mode": state.get("_safe_mode", False),
        "consecutive_losses": state.get("consecutive_losses", 0),
        "consecutive_wins": state.get("consecutive_wins", 0),
        "spot_usdc": (state.get("last_spot_cash_map") or {}).get("USDC", 0),
        # Net profit auditor: track infra costs vs trading gains
        "infra_cost_daily_usd": 0.0,  # Oracle free tier = $0. Update if scaling.
        "net_pnl_today_usd": round(state.get("pnl_today_usd", 0) - 0.0, 4),
        "net_pnl_after_fees_usd": round(
            state.get("pnl_today_usd", 0) - total_fees - 0.0, 4
        ),
    }

if __name__ == "__main__":
    metrics = build_metrics()
    tmp = str(OUT) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    os.rename(tmp, str(OUT))
    print(json.dumps(metrics, indent=2, default=str))
