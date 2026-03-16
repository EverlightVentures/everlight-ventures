"""
Trading Engine — Report generator.
Produces daily reports with AI commentary from analyzed metrics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from ...core.ai_worker import call_openai
from ...core.filesystem import trading_report_dir, write_json, write_text


REPORT_SYSTEM = """You are a trading analyst for an XLM derivatives bot running on Coinbase.
Write a clear, concise daily report in markdown. Use plain English, not overly technical.
The audience is the bot operator who wants to know: what happened, is anything wrong, what to do next.
Keep it under 500 words. Use bullet points. Include specific numbers.
Do NOT give financial advice — just report facts and observations."""


def generate_daily_report(analysis: dict, anomalies: list) -> dict:
    """
    Generate a full daily report from analysis + anomalies.
    Returns dict with file paths of all generated artifacts.
    """
    now = datetime.now(timezone.utc)
    report_dir = trading_report_dir()

    # Save raw metrics
    write_json(report_dir / "metrics.json", analysis)

    # Save anomalies
    write_json(report_dir / "anomalies.json", anomalies)

    # Build AI prompt
    prompt = _build_report_prompt(analysis, anomalies)

    # Generate report via OpenAI
    report_md = call_openai(prompt, system=REPORT_SYSTEM, temperature=0.4, max_tokens=2000)

    # Check for API errors
    if report_md.startswith("[ERROR"):
        report_md = _fallback_report(analysis, anomalies)

    write_text(report_dir / "daily_report.md", report_md)

    # Generate recommended changes if anomalies warrant it
    changes_md = ""
    danger_anomalies = [a for a in anomalies if a.get("severity") in ("danger", "warning")]
    if danger_anomalies:
        changes_md = _generate_recommendations(analysis, danger_anomalies)
        write_text(report_dir / "recommended_changes.md", changes_md)

    return {
        "report_dir": str(report_dir),
        "daily_report": str(report_dir / "daily_report.md"),
        "metrics": str(report_dir / "metrics.json"),
        "anomalies": str(report_dir / "anomalies.json"),
        "recommended_changes": str(report_dir / "recommended_changes.md") if changes_md else None,
        "anomaly_count": len(anomalies),
        "danger_count": len(danger_anomalies),
    }


def _build_report_prompt(analysis: dict, anomalies: list) -> str:
    """Build the prompt for the AI report generator."""
    state = analysis.get("state", {})
    snapshot = analysis.get("snapshot", {})
    decisions = analysis.get("decisions", {})
    trades = analysis.get("trades", {})
    margin = analysis.get("margin", {})

    sections = []

    # Current state
    sections.append(f"""## Current Bot State
- Day: {state.get('day', '?')}
- Equity: ${state.get('equity_start_usd', 0):.2f}
- PnL today: ${state.get('pnl_today_usd', 0):.2f}
- Trades today: {state.get('trades', 0)}, Losses: {state.get('losses', 0)}
- Position: {'OPEN — ' + str(state.get('open_position', {})) if state.get('open_position') else 'FLAT'}
- Vol state: {state.get('vol_state', '?')}
- Last cycle: {state.get('last_cycle_ts', '?')}""")

    # Snapshot highlights
    if snapshot:
        sections.append(f"""## Latest Snapshot
- Regime: {snapshot.get('regime', '?')} / Vol phase: {snapshot.get('vol_phase', '?')}
- Confluence score: {snapshot.get('confluence_score', '?')}
- State: {snapshot.get('state', '?')}
- Thought: {snapshot.get('thought', '?')}
- HTF bias: {snapshot.get('htf_macro_bias', '?')}""")

    # Decision metrics
    if decisions.get("total_cycles", 0) > 0:
        sections.append(f"""## Decision Metrics ({decisions.get('lookback_hours', 24)}h lookback)
- Total cycles: {decisions['total_cycles']}
- Gate pass rate: {decisions.get('gates_pass_rate', 0)*100:.1f}%
- Gate breakdown: {json.dumps(decisions.get('gate_rates', {}), indent=2)}
- Entry signals seen: {json.dumps(decisions.get('entry_signals', {}))}
- Top block reasons: {json.dumps(decisions.get('block_reasons', {}))}
- Avg confluence score: {decisions.get('avg_confluence_score', 0)}""")

    # Trade stats
    if trades.get("total_trades", 0) > 0:
        sections.append(f"""## Trade Stats (all time)
- Total trades: {trades['total_trades']}
- Win rate: {trades.get('win_rate', 0)*100:.1f}%
- Total PnL: ${trades.get('total_pnl_usd', 0):.2f}
- Best: ${trades.get('best_trade_usd', 0):.2f}, Worst: ${trades.get('worst_trade_usd', 0):.2f}
- Max win streak: {trades.get('max_win_streak', 0)}, Max loss streak: {trades.get('max_loss_streak', 0)}""")

    # Margin
    if margin.get("total_entries", 0) > 0:
        sections.append(f"""## Margin Health
- Latest tier: {margin.get('latest_tier', '?')}
- Tier distribution: {json.dumps(margin.get('tier_distribution', {}))}""")

    # Anomalies
    if anomalies:
        anom_text = "\n".join(f"- [{a['severity'].upper()}] {a['message']}" for a in anomalies)
        sections.append(f"""## Anomalies Detected
{anom_text}""")
    else:
        sections.append("## Anomalies\nNone detected.")

    prompt = """Write a daily trading report based on these metrics.
Include sections: Summary, Key Metrics, Anomalies & Concerns, Outlook.
Be direct and factual.

""" + "\n\n".join(sections)

    return prompt


def _fallback_report(analysis: dict, anomalies: list) -> str:
    """Generate a simple report without AI if API fails."""
    state = analysis.get("state", {})
    trades = analysis.get("trades", {})

    lines = [
        f"# XLM Bot Daily Report — {state.get('day', 'Unknown')}",
        "",
        "## Summary",
        f"- Equity: ${state.get('equity_start_usd', 0):.2f}",
        f"- PnL today: ${state.get('pnl_today_usd', 0):.2f}",
        f"- Trades today: {state.get('trades', 0)}",
        f"- Position: {'OPEN' if state.get('open_position') else 'FLAT'}",
        f"- Vol state: {state.get('vol_state', '?')}",
        "",
        "## Trade History",
        f"- Total trades: {trades.get('total_trades', 0)}",
        f"- Win rate: {trades.get('win_rate', 0)*100:.1f}%",
        f"- Total PnL: ${trades.get('total_pnl_usd', 0):.2f}",
        "",
        "## Anomalies",
    ]

    if anomalies:
        for a in anomalies:
            lines.append(f"- [{a['severity'].upper()}] {a['message']}")
    else:
        lines.append("- None detected")

    lines.append("")
    lines.append("*Report generated without AI (API unavailable)*")
    return "\n".join(lines)


def _generate_recommendations(analysis: dict, anomalies: list) -> str:
    """Generate recommended config changes based on anomalies."""
    prompt = f"""Based on these trading bot anomalies, suggest specific config changes.
The bot config is YAML with keys like: max_trades_per_day, max_losses_per_day, max_sl_pct,
cooldown_minutes, capital_allocation_pct, leverage, etc.

Anomalies:
{json.dumps(anomalies, indent=2)}

Current state:
{json.dumps(analysis.get('state', {}), indent=2)}

For each recommendation:
1. What to change (specific config key)
2. Current behavior
3. Proposed value
4. Why

Be conservative — safety first. Do NOT recommend increasing leverage or position sizes.
Keep it under 300 words."""

    system = "You are a risk-focused trading systems advisor. Be conservative and specific."
    result = call_openai(prompt, system=system, temperature=0.3, max_tokens=1500)

    if result.startswith("[ERROR"):
        lines = ["# Recommended Changes", ""]
        for a in anomalies:
            lines.append(f"- [{a['severity'].upper()}] {a['message']}")
        lines.append("")
        lines.append("*Manual review recommended — AI recommendations unavailable*")
        return "\n".join(lines)

    return f"# Recommended Changes\n\n{result}"


def format_slack_summary(analysis: dict, anomalies: list, report_dir: str) -> str:
    """Format a Slack-friendly summary of the report."""
    state = analysis.get("state", {})
    trades = analysis.get("trades", {})
    snapshot = analysis.get("snapshot", {})

    danger = [a for a in anomalies if a["severity"] == "danger"]
    warnings = [a for a in anomalies if a["severity"] == "warning"]

    status_emoji = ":red_circle:" if danger else ":large_yellow_circle:" if warnings else ":large_green_circle:"

    lines = [
        f"{status_emoji} *XLM Bot Daily Report — {state.get('day', '?')}*",
        "",
        f"*Equity:* ${state.get('equity_start_usd', 0):.2f} | *PnL:* ${state.get('pnl_today_usd', 0):.2f}",
        f"*Position:* {'OPEN' if state.get('open_position') else 'FLAT'} | *Regime:* {snapshot.get('regime', '?')} | *Vol:* {snapshot.get('vol_phase', '?')}",
        f"*Trades (all-time):* {trades.get('total_trades', 0)} | *Win rate:* {trades.get('win_rate', 0)*100:.0f}%",
    ]

    if anomalies:
        lines.append("")
        lines.append(f"*Anomalies ({len(anomalies)}):*")
        for a in anomalies[:5]:
            sev = {"danger": ":rotating_light:", "warning": ":warning:", "info": ":information_source:"}.get(a["severity"], "")
            lines.append(f"{sev} {a['message']}")

    lines.append(f"\n_Full report: `{report_dir}`_")
    return "\n".join(lines)
