#!/usr/bin/env python3
"""Daily audit/report for XLM trading bot -- reads synced Oracle data, writes markdown.

Usage:
    python3 daily_report.py              # today's report
    python3 daily_report.py 2026-02-27   # specific date

Importable:
    from daily_report import generate_report
"""

import json
import csv
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")

SYNC_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/sync/xlm_bot_oracle")
REPORT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports")

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _safe_float(val, default=0.0):
    """Parse a float from a string, returning default on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def load_json(path):
    """Load a JSON file, returning empty dict on any error."""
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def load_all_trades():
    """Load every row from trades.csv as a list of dicts."""
    p = SYNC_DIR / "trades.csv"
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def trades_for_day(all_trades, day_str):
    """Filter trades whose timestamp starts with YYYY-MM-DD (UTC or PT)."""
    results = []
    for t in all_trades:
        ts_raw = t.get("timestamp", "")
        # Try to parse and convert to PT for day matching
        try:
            dt = _parse_ts(ts_raw)
            if dt.astimezone(PT).strftime("%Y-%m-%d") == day_str:
                results.append(t)
                continue
        except Exception:
            pass
        # Fallback: simple string prefix match
        if ts_raw.startswith(day_str):
            results.append(t)
    return results


def _parse_ts(ts_str):
    """Parse an ISO timestamp string into a timezone-aware datetime."""
    ts = ts_str.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_service_status():
    """Read service_status.txt and return list of service lines."""
    p = SYNC_DIR / "service_status.txt"
    if not p.exists():
        return []
    try:
        return [line.strip() for line in p.read_text().splitlines() if line.strip()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Stat helpers
# ---------------------------------------------------------------------------

def _get_pnl(t):
    return _safe_float(t.get("pnl_usd", 0))


def _get_fees(t):
    """Handle both total_fees_usd (actual) and fees_usd (requested spec)."""
    val = t.get("total_fees_usd") or t.get("fees_usd") or "0"
    return _safe_float(val)


def _get_hold_min(t):
    """Handle both time_in_trade_min (actual) and hold_minutes (requested spec)."""
    val = t.get("time_in_trade_min") or t.get("hold_minutes") or "0"
    return _safe_float(val)


def _get_direction(t):
    return t.get("side") or t.get("direction") or "?"


def _get_result(t):
    """Derive win/loss from result column or pnl sign."""
    r = t.get("result", "").lower()
    if r in ("win", "loss"):
        return r
    pnl = _get_pnl(t)
    if pnl > 0:
        return "win"
    elif pnl < 0:
        return "loss"
    return "flat"


def _max_consecutive_losses(trades):
    """Longest streak of consecutive losses in trade list."""
    max_streak = 0
    current = 0
    for t in trades:
        if _get_result(t) == "loss":
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _max_drawdown_usd(trades):
    """Compute max drawdown in USD from cumulative PnL series."""
    if not trades:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cumulative += _get_pnl(t) - _get_fees(t)
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _best_worst_day(all_trades):
    """Find best and worst day by net PnL. Returns (best_day, best_pnl, worst_day, worst_pnl)."""
    daily = defaultdict(float)
    for t in all_trades:
        ts_raw = t.get("timestamp", "")
        try:
            dt = _parse_ts(ts_raw)
            day = dt.astimezone(PT).strftime("%Y-%m-%d")
        except Exception:
            day = ts_raw[:10]
        daily[day] += _get_pnl(t) - _get_fees(t)
    if not daily:
        return "N/A", 0.0, "N/A", 0.0
    best_day = max(daily, key=daily.get)
    worst_day = min(daily, key=daily.get)
    return best_day, daily[best_day], worst_day, daily[worst_day]


def _regime_time_summary(state, metrics):
    """Extract vol regime info. Returns dict of regime -> description."""
    # We only have a snapshot, not a time series. Report current regime.
    current = metrics.get("vol_state") or state.get("vol_state") or "N/A"
    return current


def _format_hold_time(minutes):
    """Format hold time from minutes into a readable string."""
    if minutes < 1:
        return "<1m"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m"


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_report(day_str=None):
    """Generate a full daily audit report as a markdown string.

    Args:
        day_str: Date in YYYY-MM-DD format. Defaults to today in PT.

    Returns:
        Markdown string of the report.
    """
    if day_str is None:
        day_str = datetime.now(PT).strftime("%Y-%m-%d")

    state = load_json(SYNC_DIR / "state.json")
    metrics = load_json(SYNC_DIR / "metrics.json")
    services = load_service_status()
    all_trades = load_all_trades()
    day_trades = trades_for_day(all_trades, day_str)

    now_pt = datetime.now(PT).strftime("%Y-%m-%d %I:%M %p PT")

    lines = []
    lines.append(f"# XLM Bot Daily Report -- {day_str}")
    lines.append(f"Generated: {now_pt}")
    lines.append("")

    # ------------------------------------------------------------------
    # 1. Bot Health
    # ------------------------------------------------------------------
    bot_alive = metrics.get("bot_alive", False)
    hb_age = metrics.get("heartbeat_age_s", "N/A")
    session_id = metrics.get("session_id") or state.get("session_id") or "N/A"
    safe_mode = metrics.get("safe_mode", state.get("_safe_mode", False))
    recovery = state.get("recovery_mode", "N/A")

    # Uptime -- approximate from generated_at vs session start
    generated_at = metrics.get("generated_at", "")
    try:
        gen_dt = _parse_ts(generated_at)
        uptime_s = (datetime.now(timezone.utc) - gen_dt).total_seconds()
        if uptime_s < 0:
            uptime_s = 0
        hb_age_display = f"{_safe_float(hb_age):.0f}s ago"
    except Exception:
        hb_age_display = "N/A"

    status_label = "ALIVE" if bot_alive else "DOWN"
    svc_str = ", ".join(services) if services else "N/A"

    lines.append("## 1. Bot Health")
    lines.append(f"- **Status:** {status_label}")
    lines.append(f"- **Heartbeat:** {hb_age_display}")
    lines.append(f"- **Session:** {session_id}")
    lines.append(f"- **Services:** {svc_str}")
    lines.append(f"- **Safe mode:** {'YES' if safe_mode else 'No'}")
    lines.append(f"- **Recovery mode:** {recovery}")
    lines.append(f"- **Overnight trading:** {metrics.get('overnight_ok', state.get('_overnight_trading_ok', 'N/A'))}")
    lines.append(f"- **Equity (start of day):** ${_safe_float(state.get('equity_start_usd', 0)):.2f}")

    spot_usdc = metrics.get("spot_usdc") or 0
    if not spot_usdc:
        cash_map = state.get("last_spot_cash_map", {})
        spot_usdc = _safe_float(cash_map.get("USDC", 0))
    lines.append(f"- **Spot USDC parked:** ${spot_usdc:.2f}")
    lines.append("")

    # ------------------------------------------------------------------
    # 2. Trading Summary
    # ------------------------------------------------------------------
    wins = sum(1 for t in day_trades if _get_result(t) == "win")
    losses = sum(1 for t in day_trades if _get_result(t) == "loss")
    total = len(day_trades)
    win_rate = f"{wins / total * 100:.0f}%" if total > 0 else "N/A"

    gross_pnl = sum(_get_pnl(t) for t in day_trades)
    total_fees = sum(_get_fees(t) for t in day_trades)
    net_pnl = gross_pnl - total_fees

    pnls = [_get_pnl(t) for t in day_trades]
    largest_win = max(pnls) if pnls and max(pnls) > 0 else 0.0
    largest_loss = min(pnls) if pnls and min(pnls) < 0 else 0.0

    lines.append("## 2. Trading Summary")
    lines.append(f"- **Total trades:** {total}")
    lines.append(f"- **Wins / Losses:** {wins} / {losses}")
    lines.append(f"- **Win rate:** {win_rate}")
    lines.append(f"- **Gross PnL:** ${gross_pnl:+.2f}")
    lines.append(f"- **Fees:** ${total_fees:.2f}")
    lines.append(f"- **Net PnL:** ${net_pnl:+.2f}")
    lines.append(f"- **Largest win:** ${largest_win:+.2f}" if largest_win else "- **Largest win:** N/A")
    lines.append(f"- **Largest loss:** ${largest_loss:+.2f}" if largest_loss else "- **Largest loss:** N/A")
    lines.append("")

    # ------------------------------------------------------------------
    # 3. Trade Table (last 10 of the day)
    # ------------------------------------------------------------------
    display_trades = day_trades[-10:]

    lines.append("## 3. Trade Log (last 10)")
    if display_trades:
        lines.append("| Time (PT) | Dir | Entry | Exit | PnL | Fees | Hold | Exit Reason |")
        lines.append("|-----------|-----|-------|------|-----|------|------|-------------|")
        for t in display_trades:
            # Time
            ts_raw = t.get("timestamp", "")
            try:
                dt = _parse_ts(ts_raw)
                ts_pt = dt.astimezone(PT).strftime("%I:%M %p")
            except Exception:
                ts_pt = ts_raw[:16]

            direction = _get_direction(t)
            entry_p = t.get("entry_price", "N/A")
            exit_p = t.get("exit_price", "N/A")
            pnl_val = _get_pnl(t)
            fees_val = _get_fees(t)
            hold_val = _get_hold_min(t)
            exit_reason = t.get("exit_reason", "N/A")

            lines.append(
                f"| {ts_pt} | {direction} | {entry_p} | {exit_p} "
                f"| ${pnl_val:+.2f} | ${fees_val:.2f} "
                f"| {_format_hold_time(hold_val)} | {exit_reason} |"
            )
    else:
        lines.append("No trades recorded for this day.")
    lines.append("")

    # ------------------------------------------------------------------
    # 4. Risk Metrics
    # ------------------------------------------------------------------
    day_consec_losses = _max_consecutive_losses(day_trades)
    day_drawdown = _max_drawdown_usd(day_trades)
    state_consec_losses = state.get("consecutive_losses", 0)

    # Margin ratio -- pull from state/metrics if available
    margin_ratio = metrics.get("margin_ratio_hwm") or state.get("margin_ratio_hwm") or "N/A"

    lines.append("## 4. Risk Metrics")
    lines.append(f"- **Max drawdown (today):** ${day_drawdown:.2f}")
    lines.append(f"- **Consecutive losses (today):** {day_consec_losses}")
    lines.append(f"- **Consecutive losses (current):** {state_consec_losses}")
    lines.append(f"- **Consecutive wins (current):** {state.get('consecutive_wins', 0)}")
    lines.append(f"- **Margin ratio HWM:** {margin_ratio}")
    lines.append(f"- **Loss debt:** ${_safe_float(state.get('loss_debt_usd', 0)):.2f}")
    lines.append("")

    # ------------------------------------------------------------------
    # 5. All-Time Stats
    # ------------------------------------------------------------------
    all_wins = sum(1 for t in all_trades if _get_result(t) == "win")
    all_losses = sum(1 for t in all_trades if _get_result(t) == "loss")
    all_total = len(all_trades)
    all_wr = f"{all_wins / all_total * 100:.0f}%" if all_total > 0 else "N/A"

    all_gross = sum(_get_pnl(t) for t in all_trades)
    all_fees = sum(_get_fees(t) for t in all_trades)
    all_net = all_gross - all_fees

    hold_times = [_get_hold_min(t) for t in all_trades if _get_hold_min(t) > 0]
    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0.0

    all_dd = _max_drawdown_usd(all_trades)
    all_consec = _max_consecutive_losses(all_trades)
    best_day, best_pnl, worst_day, worst_pnl = _best_worst_day(all_trades)

    lines.append("## 5. All-Time Stats")
    lines.append(f"- **Total trades:** {all_total}  (W: {all_wins}, L: {all_losses})")
    lines.append(f"- **Win rate:** {all_wr}")
    lines.append(f"- **Cumulative gross PnL:** ${all_gross:+.2f}")
    lines.append(f"- **Cumulative fees:** ${all_fees:.2f}")
    lines.append(f"- **Cumulative net PnL:** ${all_net:+.2f}")
    lines.append(f"- **Avg hold time:** {_format_hold_time(avg_hold)}")
    lines.append(f"- **Max drawdown (all-time):** ${all_dd:.2f}")
    lines.append(f"- **Max consecutive losses:** {all_consec}")
    lines.append(f"- **Best day:** {best_day} (${best_pnl:+.2f})")
    lines.append(f"- **Worst day:** {worst_day} (${worst_pnl:+.2f})")
    lines.append("")

    # ------------------------------------------------------------------
    # 6. Regime Summary
    # ------------------------------------------------------------------
    current_regime = _regime_time_summary(state, metrics)

    # Count trades per regime if vol_state column exists in CSV
    regime_counts = defaultdict(int)
    regime_pnl = defaultdict(float)
    for t in all_trades:
        regime = t.get("vol_state") or t.get("regime") or "unknown"
        regime_counts[regime] += 1
        regime_pnl[regime] += _get_pnl(t) - _get_fees(t)

    lines.append("## 6. Regime Summary")
    lines.append(f"- **Current regime:** {current_regime}")
    lines.append("")

    if regime_counts and not (len(regime_counts) == 1 and "unknown" in regime_counts):
        lines.append("| Regime | Trades | Net PnL |")
        lines.append("|--------|--------|---------|")
        for regime in sorted(regime_counts.keys()):
            lines.append(
                f"| {regime} | {regime_counts[regime]} | ${regime_pnl[regime]:+.2f} |"
            )
    else:
        lines.append("Regime breakdown not available (no per-trade regime data in CSV).")
    lines.append("")

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    lines.append("---")
    lines.append(f"Data source: `{SYNC_DIR}`")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(PT).strftime("%Y-%m-%d")
    report = generate_report(day)

    out = REPORT_DIR / f"daily_{day}.md"
    out.write_text(report)

    print(report)
    print(f"\nSaved to: {out}")


if __name__ == "__main__":
    main()
