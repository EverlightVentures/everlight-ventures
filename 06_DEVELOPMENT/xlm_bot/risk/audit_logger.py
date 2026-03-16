"""Structured audit logger -- Score 10 upgrade.

Writes immutable, structured records to:
  logs/audit/YYYY/MM/DD/daily_report.md
  logs/audit/YYYY/MM/DD/metrics.json
  logs/audit/YYYY/MM/DD/anomalies.json
  logs/audit/YYYY/MM/DD/state_snapshots.jsonl

Hive Mind Finding (everlight_packager):
  "You cannot backtest or audit an AI's decisions via Slack messages.
   The bot must write daily_report.md, anomalies.json, metrics.json,
   and state.json."

Usage
-----
from risk.audit_logger import AuditLogger

audit = AuditLogger(base_dir=LOGS_DIR / "audit")
audit.record_trade(trade_dict)
audit.record_anomaly("PHANTOM_POSITION", details)
audit.record_ai_decision(ai_insight, market_context)
audit.flush_daily()
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import math


@dataclass
class TradeAuditRecord:
    ts_utc: str
    trade_id: str
    lane: str
    entry_type: str
    direction: str
    contracts: int
    entry_price: float
    exit_price: float | None
    pnl_usd: float | None
    fees_usd: float | None
    confluence_score: int
    quality_tier: str
    sl_price: float
    tp1_price: float
    hold_bars: int | None
    exit_reason: str | None
    ai_action: str | None
    ai_confidence: float | None
    regime: str | None
    kelly_fraction: float | None
    notes: list[str] = field(default_factory=list)


@dataclass
class AnomalyRecord:
    ts_utc: str
    severity: str      # CRITICAL | WARNING | INFO
    anomaly_type: str
    details: dict


class AuditLogger:
    """Immutable structured audit trail for every bot action."""

    def __init__(self, base_dir: str | Path, tz_offset_hours: int = -8):
        self._base = Path(base_dir)
        self._tz = timezone(timedelta(hours=tz_offset_hours))
        self._trades: list[TradeAuditRecord] = []
        self._anomalies: list[AnomalyRecord] = []
        self._ai_decisions: list[dict] = []
        self._state_snapshots: list[dict] = []

    def _day_dir(self, ts: datetime | None = None) -> Path:
        now = (ts or datetime.now(timezone.utc)).astimezone(self._tz)
        d = self._base / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _atomic_write(self, path: Path, content: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            os.replace(tmp, str(path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _append_jsonl(self, path: Path, record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")

    # ── Public API ────────────────────────────────────────────────────

    def record_trade(self, trade: dict | TradeAuditRecord) -> None:
        """Log a completed trade."""
        if isinstance(trade, dict):
            rec = TradeAuditRecord(
                ts_utc=trade.get("ts_utc", datetime.now(timezone.utc).isoformat()),
                trade_id=str(trade.get("trade_id", trade.get("entry_order_id", "?"))),
                lane=str(trade.get("lane", trade.get("entry_type", "?"))),
                entry_type=str(trade.get("entry_type", "?")),
                direction=str(trade.get("direction", "?")),
                contracts=int(trade.get("contracts", 0)),
                entry_price=float(trade.get("entry_price", 0)),
                exit_price=_optional_float(trade.get("exit_price")),
                pnl_usd=_optional_float(trade.get("pnl_usd")),
                fees_usd=_optional_float(trade.get("total_fees_usd")),
                confluence_score=int(trade.get("confluence_score", 0)),
                quality_tier=str(trade.get("quality_tier", "UNKNOWN")),
                sl_price=float(trade.get("sl_price", 0)),
                tp1_price=float(trade.get("tp1_price", 0)),
                hold_bars=_optional_int(trade.get("hold_bars")),
                exit_reason=trade.get("exit_reason"),
                ai_action=trade.get("ai_action"),
                ai_confidence=_optional_float(trade.get("ai_confidence")),
                regime=trade.get("regime"),
                kelly_fraction=_optional_float(trade.get("kelly_fraction")),
                notes=list(trade.get("notes", [])),
            )
        else:
            rec = trade

        self._trades.append(rec)
        d = self._day_dir()
        self._append_jsonl(d / "trades.jsonl", asdict(rec))

    def record_anomaly(
        self,
        anomaly_type: str,
        details: dict,
        severity: str = "WARNING",
    ) -> None:
        """Log an anomaly (phantom position, API error, state mismatch, etc.)."""
        rec = AnomalyRecord(
            ts_utc=datetime.now(timezone.utc).isoformat(),
            severity=severity.upper(),
            anomaly_type=anomaly_type.upper(),
            details=details,
        )
        self._anomalies.append(rec)
        d = self._day_dir()
        existing = []
        anomaly_path = d / "anomalies.json"
        if anomaly_path.exists():
            try:
                existing = json.loads(anomaly_path.read_text())
            except Exception:
                existing = []
        existing.append(asdict(rec))
        self._atomic_write(anomaly_path, json.dumps(existing, indent=2, default=str))

    def record_ai_decision(self, ai_insight: dict, market_context: dict | None = None) -> None:
        """Log every AI executive decision with its reasoning."""
        record = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "action": ai_insight.get("action"),
            "confidence": ai_insight.get("confidence"),
            "reasoning": ai_insight.get("reasoning"),
            "market_context": market_context or {},
        }
        self._ai_decisions.append(record)
        d = self._day_dir()
        self._append_jsonl(d / "ai_decisions.jsonl", record)

    def record_state_snapshot(self, state: dict) -> None:
        """Append periodic state snapshot for timeline reconstruction."""
        snap = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            **state,
        }
        d = self._day_dir()
        self._append_jsonl(d / "state_snapshots.jsonl", snap)

    def flush_daily(self, nav: float | None = None) -> None:
        """Write metrics.json + daily_report.md for today."""
        self._flush_metrics(nav)
        self._flush_report(nav)

    def _flush_metrics(self, nav: float | None) -> None:
        """Compute and write metrics.json."""
        d = self._day_dir()
        trades = self._trades
        if not trades:
            metrics = {"trades": 0, "nav": nav}
        else:
            pnls = [t.pnl_usd for t in trades if t.pnl_usd is not None]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            total_pnl = sum(pnls)
            win_rate = len(wins) / len(pnls) if pnls else 0.0

            avg_win = sum(wins) / len(wins) if wins else 0.0
            avg_loss = sum(losses) / len(losses) if losses else 0.0
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else None

            sharpe = _daily_sharpe(pnls)
            max_dd = _max_drawdown(pnls)

            # Per-lane breakdown
            lane_pnl: dict[str, list[float]] = {}
            for t in trades:
                if t.pnl_usd is not None:
                    lane_pnl.setdefault(t.lane, []).append(t.pnl_usd)

            lane_metrics = {}
            for lane, lane_pnls in lane_pnl.items():
                lane_wins = [p for p in lane_pnls if p > 0]
                lane_metrics[lane] = {
                    "count": len(lane_pnls),
                    "win_rate": round(len(lane_wins) / len(lane_pnls), 3),
                    "total_pnl": round(sum(lane_pnls), 2),
                    "sharpe": _daily_sharpe(lane_pnls),
                    "max_dd": _max_drawdown(lane_pnls),
                }

            metrics = {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "nav": nav,
                "trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round(win_rate, 4),
                "total_pnl_usd": round(total_pnl, 2),
                "avg_win_usd": round(avg_win, 2),
                "avg_loss_usd": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 3) if profit_factor else None,
                "sharpe_daily": sharpe,
                "max_drawdown_usd": max_dd,
                "anomalies_count": len(self._anomalies),
                "ai_decisions_count": len(self._ai_decisions),
                "lanes": lane_metrics,
            }

        self._atomic_write(d / "metrics.json", json.dumps(metrics, indent=2, default=str))

    def _flush_report(self, nav: float | None) -> None:
        """Write human-readable daily_report.md."""
        d = self._day_dir()
        now_pt = datetime.now(timezone.utc).astimezone(self._tz)
        lines = [
            f"# XLM Reaper Daily Report -- {now_pt.strftime('%Y-%m-%d')} (PT)",
            "",
            f"**Generated:** {now_pt.strftime('%Y-%m-%d %H:%M PT')}",
            f"**NAV:** ${nav:.2f}" if nav else "**NAV:** unknown",
            "",
            "## Trade Summary",
        ]

        trades = self._trades
        if not trades:
            lines.append("No trades today.")
        else:
            pnls = [t.pnl_usd for t in trades if t.pnl_usd is not None]
            wins = [p for p in pnls if p > 0]
            lines += [
                f"- Trades: {len(trades)}",
                f"- Win Rate: {len(wins)/len(pnls):.0%}" if pnls else "- Win Rate: --",
                f"- Total PnL: ${sum(pnls):.2f}" if pnls else "",
                f"- Sharpe (daily): {_daily_sharpe(pnls)}",
                f"- Max Drawdown: ${_max_drawdown(pnls):.2f}" if pnls else "",
                "",
                "| Lane | Entry | Dir | Score | Tier | PnL | Exit Reason | AI |",
                "|------|-------|-----|-------|------|-----|-------------|-----|",
            ]
            for t in trades:
                pnl_str = f"${t.pnl_usd:+.2f}" if t.pnl_usd is not None else "--"
                ai_str = t.ai_action or "--"
                lines.append(
                    f"| {t.lane} | {t.entry_type[:12]} | {t.direction[:1]} | "
                    f"{t.confluence_score} | {t.quality_tier} | {pnl_str} | "
                    f"{t.exit_reason or '--'} | {ai_str} |"
                )

        if self._anomalies:
            lines += ["", "## Anomalies", ""]
            for a in self._anomalies:
                lines.append(f"- `[{a.severity}]` {a.anomaly_type}: {a.details}")

        if self._ai_decisions:
            lines += ["", "## AI Decisions", ""]
            for ai in self._ai_decisions[-5:]:  # last 5
                lines.append(
                    f"- `{ai.get('action')}` confidence={ai.get('confidence')} "
                    f"@ {ai.get('ts_utc', '')[:16]}"
                )

        self._atomic_write(d / "daily_report.md", "\n".join(lines) + "\n")


# ── Math helpers ──────────────────────────────────────────────────────────────

def _optional_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _optional_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _daily_sharpe(pnls: list[float]) -> float | None:
    """Compute Sharpe ratio from a list of per-trade PnLs (no risk-free rate)."""
    if len(pnls) < 2:
        return None
    mean = sum(pnls) / len(pnls)
    variance = sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None
    return round(mean / std, 3)


def _max_drawdown(pnls: list[float]) -> float:
    """Peak-to-trough drawdown in USD from a sequential list of PnLs."""
    if not pnls:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)
