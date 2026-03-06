"""
Trading Engine — Anomaly detector.
Flags unusual patterns from analyzed metrics.
"""

from typing import List, Dict


def detect_anomalies(analysis: dict) -> List[dict]:
    """
    Run anomaly detection on full analysis output.
    Returns list of anomaly dicts with severity, type, message, data.
    """
    anomalies = []

    # --- Decision anomalies ---
    decisions = analysis.get("decisions", {})
    if decisions.get("total_cycles", 0) > 0:
        # Very low gate pass rate
        gpr = decisions.get("gates_pass_rate", 0)
        if gpr < 0.05 and decisions["total_cycles"] > 50:
            anomalies.append({
                "severity": "warning",
                "type": "low_gate_pass_rate",
                "message": f"Gate pass rate is only {gpr*100:.1f}% over {decisions['total_cycles']} cycles. Bot may be stuck.",
                "value": gpr,
            })

        # Individual gate bottleneck
        for gate, info in decisions.get("gate_rates", {}).items():
            if info["pass_rate"] < 0.10 and info["total"] > 20:
                anomalies.append({
                    "severity": "info",
                    "type": "gate_bottleneck",
                    "message": f"Gate '{gate}' passing only {info['pass_rate']*100:.1f}% — may be blocking all entries.",
                    "gate": gate,
                    "pass_rate": info["pass_rate"],
                })

        # No signals at all
        if not decisions.get("entry_signals") and decisions["total_cycles"] > 100:
            anomalies.append({
                "severity": "warning",
                "type": "no_signals",
                "message": f"No entry signals detected in {decisions['total_cycles']} cycles.",
            })

        # Confluence score too low
        avg_score = decisions.get("avg_confluence_score", 0)
        if avg_score > 0 and avg_score < 2:
            anomalies.append({
                "severity": "info",
                "type": "low_confluence",
                "message": f"Average confluence score is {avg_score} — market may lack setup quality.",
                "value": avg_score,
            })

    # --- Trade anomalies ---
    trades = analysis.get("trades", {})
    if trades.get("total_trades", 0) > 0:
        # Consecutive losses
        if trades.get("max_loss_streak", 0) >= 3:
            anomalies.append({
                "severity": "danger",
                "type": "loss_streak",
                "message": f"Max loss streak of {trades['max_loss_streak']} trades detected.",
                "value": trades["max_loss_streak"],
            })

        # Win rate below 40%
        wr = trades.get("win_rate", 0)
        if wr < 0.40 and trades["total_trades"] >= 5:
            anomalies.append({
                "severity": "warning",
                "type": "low_win_rate",
                "message": f"Win rate is {wr*100:.1f}% over {trades['total_trades']} trades.",
                "value": wr,
            })

        # Large single loss
        worst = trades.get("worst_trade_usd", 0)
        equity = analysis.get("state", {}).get("equity_start_usd", 200)
        if worst < 0 and abs(worst) > equity * 0.05:
            anomalies.append({
                "severity": "warning",
                "type": "large_loss",
                "message": f"Worst trade lost ${abs(worst):.2f} ({abs(worst)/equity*100:.1f}% of equity).",
                "value": worst,
            })

    # --- Margin anomalies ---
    margin = analysis.get("margin", {})
    if margin.get("total_entries", 0) > 0:
        tier = margin.get("latest_tier")
        if tier == "WARNING":
            anomalies.append({
                "severity": "warning",
                "type": "margin_warning",
                "message": "Margin tier is WARNING — approaching danger zone.",
            })
        elif tier == "DANGER":
            anomalies.append({
                "severity": "danger",
                "type": "margin_danger",
                "message": "Margin tier is DANGER — liquidation risk is elevated.",
            })

        # UNKNOWN tier (missing data)
        tier_dist = margin.get("tier_distribution", {})
        if tier_dist.get("UNKNOWN", 0) > margin["total_entries"] * 0.8:
            anomalies.append({
                "severity": "info",
                "type": "margin_data_missing",
                "message": "Margin ratio data is mostly UNKNOWN — API may not be returning margin fields.",
            })

    # --- Incident anomalies ---
    incidents = analysis.get("incidents", {})
    if incidents.get("total_incidents", 0) > 0:
        anomalies.append({
            "severity": "warning",
            "type": "reconciliation_issues",
            "message": f"{incidents['total_incidents']} reconciliation incident(s) detected.",
            "types": incidents.get("types", {}),
        })

    # --- State anomalies ---
    state = analysis.get("state", {})
    if state:
        # Bot hasn't run in a while
        last_cycle = state.get("last_cycle_ts", "")
        if last_cycle:
            from datetime import datetime, timezone
            try:
                last = datetime.fromisoformat(last_cycle)
                age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
                if age_hours > 2:
                    anomalies.append({
                        "severity": "warning",
                        "type": "bot_stale",
                        "message": f"Bot last ran {age_hours:.1f} hours ago — may be stopped.",
                        "value": round(age_hours, 1),
                    })
            except (ValueError, TypeError):
                pass

        # Equity drop
        equity = state.get("equity_start_usd", 0)
        pnl = state.get("pnl_today_usd", 0)
        if equity > 0 and pnl < 0 and abs(pnl) > equity * 0.05:
            anomalies.append({
                "severity": "warning",
                "type": "daily_loss",
                "message": f"Down ${abs(pnl):.2f} today ({abs(pnl)/equity*100:.1f}% of starting equity).",
                "value": pnl,
            })

    return anomalies
