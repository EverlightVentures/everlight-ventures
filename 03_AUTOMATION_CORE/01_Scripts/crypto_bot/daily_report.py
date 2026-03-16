#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any

from utils.coinbase_api import CoinbaseAPI

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
BASELINE_PATH = BASE_DIR / "data" / "daily_baseline.json"
HISTORY_PATH = BASE_DIR / "data" / "daily_baseline_history.jsonl"
TRADE_HISTORY = BASE_DIR / "logs" / "trade_history.csv"


def _fmt_money(val: float | None) -> str:
    if val is None:
        return "—"
    return f"${val:,.2f}"


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:.2f}%"


def _load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def _get_api() -> CoinbaseAPI:
    cfg = _load_config()
    exch = cfg.get("exchange", {})
    return CoinbaseAPI(
        exch.get("api_key", ""),
        exch.get("api_secret", ""),
        sandbox=exch.get("sandbox", False),
        use_perpetuals=exch.get("use_perpetuals", False),
    )


def _snapshot_portfolio(api: CoinbaseAPI) -> dict:
    accounts = api.get_accounts() or []
    cash = {"USD": 0.0, "USDC": 0.0}
    holdings: Dict[str, Dict[str, float]] = {}
    total = 0.0

    for acc in accounts:
        curr = acc.get("currency", "")
        bal = acc.get("available_balance", {})
        amount = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)
        if amount <= 0:
            continue

        if curr in cash:
            cash[curr] += amount
            total += amount
            continue

        price = api.get_current_price(f"{curr}-USD") or 0
        value = amount * price if price else 0.0
        if value <= 0:
            continue
        holdings[curr] = {
            "amount": amount,
            "price": price,
            "value": value,
        }
        total += value

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_usd": total,
        "cash": cash,
        "holdings": holdings,
    }


def _parse_time(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_filled_orders(api: CoinbaseAPI, since_dt: datetime, limit: int = 200) -> list[dict]:
    orders = api.get_historical_orders(order_status="FILLED", limit=limit) or []
    out = []
    for o in orders:
        created = o.get("created_time") or o.get("created_at")
        ts = _parse_time(created)
        if not ts or ts < since_dt:
            continue
        out.append(o)
    return out


def _summarize_execs(orders: list[dict]) -> dict:
    summary = {
        "count": 0,
        "gross_buy_usd": 0.0,
        "gross_sell_usd": 0.0,
        "fees_usd": 0.0,
        "net_flow_usd": 0.0,
        "by_pair": {},
        "recent": [],
    }
    for o in orders:
        side = str(o.get("side") or "").lower()
        pair = o.get("product_id") or o.get("product_id") or "UNKNOWN"
        filled_size = float(o.get("filled_size") or 0)
        avg_price = float(o.get("average_filled_price") or o.get("avg_price") or o.get("average_filled_price") or 0)
        filled_value = o.get("filled_value")
        try:
            filled_value = float(filled_value) if filled_value is not None else filled_size * avg_price
        except Exception:
            filled_value = filled_size * avg_price
        fees = o.get("total_fees") or o.get("fees") or 0
        try:
            fees = float(fees)
        except Exception:
            fees = 0.0

        summary["count"] += 1
        summary["fees_usd"] += fees
        if side == "buy":
            summary["gross_buy_usd"] += filled_value
            summary["net_flow_usd"] -= filled_value
        elif side == "sell":
            summary["gross_sell_usd"] += filled_value
            summary["net_flow_usd"] += filled_value

        pair_sum = summary["by_pair"].setdefault(pair, {"buy_usd": 0.0, "sell_usd": 0.0, "fees": 0.0})
        if side == "buy":
            pair_sum["buy_usd"] += filled_value
        elif side == "sell":
            pair_sum["sell_usd"] += filled_value
        pair_sum["fees"] += fees

        summary["recent"].append({
            "time": o.get("created_time") or o.get("created_at"),
            "pair": pair,
            "side": side,
            "size": filled_size,
            "price": avg_price,
            "value": filled_value,
            "fees": fees,
        })

    summary["net_flow_usd"] -= summary["fees_usd"]
    summary["recent"] = sorted(summary["recent"], key=lambda r: r.get("time") or "", reverse=True)[:10]
    return summary


def _load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text())
    except Exception:
        return None


def _save_baseline(snapshot: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(snapshot, indent=2))


def _append_history(snapshot: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "snapshot": snapshot,
    }
    # Avoid duplicate date entries if already written today
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r") as f:
                lines = f.read().splitlines()
            if lines:
                last = json.loads(lines[-1])
                if last.get("date") == entry["date"]:
                    return
        except Exception:
            pass
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    out = []
    for line in HISTORY_PATH.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _collect_trade_stats(today: str, config: dict) -> dict:
    stats = {"closed": 0, "wins": 0, "losses": 0, "pnl_usd": 0.0, "open": 0, "fees_est_usd": 0.0}
    if not TRADE_HISTORY.exists():
        return stats
    try:
        with open(TRADE_HISTORY, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("status", "")
                if status == "OPEN":
                    stats["open"] += 1
                    continue
                exit_time = row.get("exit_time", "") or ""
                if not exit_time.startswith(today):
                    continue
                stats["closed"] += 1
                pnl = row.get("pnl_usd")
                try:
                    pnl_val = float(pnl) if pnl else 0.0
                except Exception:
                    pnl_val = 0.0
                stats["pnl_usd"] += pnl_val
                # Estimate fees based on size_usd
                try:
                    size_usd = float(row.get("size_usd") or 0.0)
                except Exception:
                    size_usd = 0.0
                fees_cfg = config.get("fees", {}) or {}
                taker = float(fees_cfg.get("taker_percent", 0.0) or 0.0)
                maker = float(fees_cfg.get("maker_percent", 0.0) or 0.0)
                assume_taker = bool(fees_cfg.get("assume_taker", True))
                fee_pct = taker if assume_taker else maker
                fees_est = size_usd * (fee_pct / 100.0) * 2
                stats["fees_est_usd"] += fees_est
                if pnl_val > 0:
                    stats["wins"] += 1
                elif pnl_val < 0:
                    stats["losses"] += 1
    except Exception:
        pass
    return stats


def _diff_holdings(curr: dict, base: dict) -> list[dict]:
    out = []
    curr_hold = curr.get("holdings", {})
    base_hold = base.get("holdings", {}) if base else {}
    symbols = set(curr_hold.keys()) | set(base_hold.keys())
    for sym in sorted(symbols):
        c = curr_hold.get(sym, {"amount": 0.0, "value": 0.0})
        b = base_hold.get(sym, {"amount": 0.0, "value": 0.0})
        out.append({
            "symbol": sym,
            "amount": c.get("amount", 0.0),
            "amount_delta": c.get("amount", 0.0) - b.get("amount", 0.0),
            "value": c.get("value", 0.0),
            "value_delta": c.get("value", 0.0) - b.get("value", 0.0),
        })
    return out


def _range_summary(history: list[dict], current: dict, days: int) -> dict | None:
    if not history:
        return None
    cutoff = datetime.now(timezone.utc).date().toordinal() - days
    candidates = []
    for entry in history:
        try:
            d = datetime.strptime(entry.get("date", ""), "%Y-%m-%d").date()
            if d.toordinal() >= cutoff:
                candidates.append(entry)
        except Exception:
            continue
    if not candidates:
        return None
    base_snap = candidates[0].get("snapshot", {})
    base_total = float(base_snap.get("total_usd", 0.0) or 0.0)
    curr_total = float(current.get("total_usd", 0.0) or 0.0)
    delta = curr_total - base_total
    delta_pct = (delta / base_total * 100) if base_total else 0.0
    return {
        "base_date": candidates[0].get("date"),
        "base_total": base_total,
        "current_total": curr_total,
        "delta": delta,
        "delta_pct": delta_pct,
    }


def _load_open_positions() -> list[dict]:
    # Prefer CSV if present
    if TRADE_HISTORY.exists():
        try:
            with open(TRADE_HISTORY, "r", newline="") as f:
                reader = csv.DictReader(f)
                return [r for r in reader if r.get("status") == "OPEN"]
        except Exception:
            pass
    json_path = BASE_DIR / "logs" / "trade_history.json"
    if json_path.exists():
        try:
            rows = json.loads(json_path.read_text())
            return [r for r in rows if r.get("status") == "OPEN"]
        except Exception:
            pass
    return []


def _open_positions_report(api: CoinbaseAPI, opens: list[dict]) -> dict:
    total_unreal = 0.0
    rows = []
    now = datetime.now(timezone.utc)
    for r in opens:
        pair = r.get("pair") or ""
        side = r.get("side") or ""
        entry_price = float(r.get("entry_price") or 0.0)
        size_usd = float(r.get("size_usd") or 0.0)
        entry_time = _parse_time(r.get("entry_time") or "")
        price = api.get_current_price(pair) or 0.0
        if entry_price <= 0 or price <= 0:
            continue
        pnl_pct = ((price - entry_price) / entry_price) * (1 if side == "buy" else -1)
        pnl_usd = size_usd * pnl_pct
        total_unreal += pnl_usd
        age = None
        if entry_time:
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            age = (now - entry_time).total_seconds() / 3600.0
        rows.append({
            "pair": pair,
            "side": side,
            "entry_price": entry_price,
            "current_price": price,
            "pnl_pct": pnl_pct * 100,
            "pnl_usd": pnl_usd,
            "age_hours": age,
        })
    return {"total_unrealized": total_unreal, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="reset baseline to current snapshot")
    parser.add_argument("--json", action="store_true", help="print JSON instead of formatted report")
    parser.add_argument("--weekly", action="store_true", help="include last 7 days summary")
    parser.add_argument("--monthly", action="store_true", help="include last 30 days summary")
    parser.add_argument("--executions", action="store_true", help="include executed order history summary")
    parser.add_argument("--days", type=int, default=1, help="execution lookback days (used with --executions)")
    args = parser.parse_args()

    config = _load_config()
    api = _get_api()
    snapshot = _snapshot_portfolio(api)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    baseline = _load_baseline()
    if args.reset or not baseline or baseline.get("date") != today:
        baseline = {
            "date": today,
            "snapshot": snapshot,
        }
        _save_baseline(baseline)
        _append_history(snapshot)

    base_snap = baseline.get("snapshot", {}) if baseline else {}
    base_total = float(base_snap.get("total_usd", 0.0) or 0.0)
    curr_total = float(snapshot.get("total_usd", 0.0) or 0.0)
    delta = curr_total - base_total
    delta_pct = (delta / base_total * 100) if base_total else 0.0

    holdings_diff = _diff_holdings(snapshot, base_snap)
    trade_stats = _collect_trade_stats(today, config)
    history = _load_history()
    exec_summary = None
    if args.executions:
        since = datetime.now(timezone.utc) - timedelta(days=max(1, args.days))
        orders = _fetch_filled_orders(api, since_dt=since, limit=200)
        exec_summary = _summarize_execs(orders)
    open_positions = _open_positions_report(api, _load_open_positions())

    if args.json:
        print(json.dumps({
            "date": today,
            "baseline": base_total,
            "current": curr_total,
            "delta_usd": delta,
            "delta_pct": delta_pct,
            "cash": snapshot.get("cash", {}),
            "holdings": holdings_diff,
            "trades": trade_stats,
            "weekly": _range_summary(history, snapshot, 7) if args.weekly else None,
            "monthly": _range_summary(history, snapshot, 30) if args.monthly else None,
            "executions": exec_summary if args.executions else None,
            "open_positions": open_positions,
        }, indent=2))
        return

    print("")
    print(f"DAILY TRADING REPORT — {today}")
    print("─────────────────────────────────────")
    print(f"Portfolio: {_fmt_money(curr_total)}  (Δ {_fmt_money(delta)} | {_fmt_pct(delta_pct)})")
    print(f"Cash: USD {_fmt_money(snapshot['cash'].get('USD', 0))} | USDC {_fmt_money(snapshot['cash'].get('USDC', 0))}")
    print("")
    print("Holdings (amount / Δ amount / value / Δ value)")
    for row in holdings_diff:
        amt = f"{row['amount']:.6f}"
        d_amt = f"{row['amount_delta']:+.6f}"
        val = _fmt_money(row["value"])
        d_val = _fmt_money(row["value_delta"])
        print(f" - {row['symbol']}: {amt} ({d_amt}) | {val} ({d_val})")
    print("")
    # Accumulation summary
    acc_up = [r for r in holdings_diff if r["amount_delta"] > 0]
    acc_down = [r for r in holdings_diff if r["amount_delta"] < 0]
    acc_value_up = sum(r["value_delta"] for r in acc_up)
    acc_value_down = sum(r["value_delta"] for r in acc_down)
    acc_score = (len(acc_up) - len(acc_down))
    print(f"Accumulation: {len(acc_up)} increased | {len(acc_down)} reduced")
    print(f"Accumulation score: {acc_score:+d} | Value Δ (adds): {_fmt_money(acc_value_up)} | Value Δ (trims): {_fmt_money(acc_value_down)}")
    if acc_up:
        top = sorted(acc_up, key=lambda r: r["amount_delta"], reverse=True)[:3]
        print("Top adds:")
        for r in top:
            print(f" - {r['symbol']}: +{r['amount_delta']:.6f} (value {r['value_delta']:+.2f})")
    if acc_down:
        top = sorted(acc_down, key=lambda r: r["amount_delta"])[:3]
        print("Top trims:")
        for r in top:
            print(f" - {r['symbol']}: {r['amount_delta']:.6f} (value {r['value_delta']:+.2f})")
    print("")
    fee_adj = trade_stats["pnl_usd"] - trade_stats.get("fees_est_usd", 0.0)
    print(f"Trades today: closed {trade_stats['closed']} (wins {trade_stats['wins']}, losses {trade_stats['losses']}) | "
          f"PNL {_fmt_money(trade_stats['pnl_usd'])} | Fees est {_fmt_money(trade_stats.get('fees_est_usd'))} | "
          f"Net {_fmt_money(fee_adj)} | Open {trade_stats['open']}")
    print("")

    if open_positions["rows"]:
        print(f"Open positions (unrealized total {_fmt_money(open_positions['total_unrealized'])}):")
        for row in open_positions["rows"]:
            age = f"{row['age_hours']:.1f}h" if row.get("age_hours") is not None else "—"
            print(f" - {row['pair']} {row['side']} | entry {row['entry_price']:.6f} -> {row['current_price']:.6f} | "
                  f"P/L {row['pnl_pct']:+.2f}% ({_fmt_money(row['pnl_usd'])}) | age {age}")
        print("")

    if exec_summary:
        print("Executed orders today (filled):")
        print(f" - Count: {exec_summary['count']}")
        print(f" - Gross buys: {_fmt_money(exec_summary['gross_buy_usd'])} | Gross sells: {_fmt_money(exec_summary['gross_sell_usd'])}")
        print(f" - Fees (actual): {_fmt_money(exec_summary['fees_usd'])}")
        print(f" - Net flow (sells - buys - fees): {_fmt_money(exec_summary['net_flow_usd'])}")
        print("")
        print("Recent fills:")
        for row in exec_summary["recent"]:
            print(f" - {row['time']} | {row['pair']} {row['side']} {row['size']:.6f} @ {row['price']:.4f} | {row['value']:.2f} | fees {row['fees']:.2f}")
        print("")

    if args.weekly:
        weekly = _range_summary(history, snapshot, 7)
        if weekly:
            print(f"Last 7d: {_fmt_money(weekly['current_total'])} (Δ {_fmt_money(weekly['delta'])} | {_fmt_pct(weekly['delta_pct'])})")
    if args.monthly:
        monthly = _range_summary(history, snapshot, 30)
        if monthly:
            print(f"Last 30d: {_fmt_money(monthly['current_total'])} (Δ {_fmt_money(monthly['delta'])} | {_fmt_pct(monthly['delta_pct'])})")
    print("")


if __name__ == "__main__":
    main()
