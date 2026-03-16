"""Self-learning evolution engine for lane-based trading strategy.

Combines three techniques to adapt strategy parameters from real trade
outcomes without manual tuning:

  1. Thompson Sampling Bandit - probabilistically favors lanes that win more
  2. Weight Adjuster - tunes confluence flag weights per lane every 25 trades
  3. Threshold Optimizer - rolling window search for PnL-maximizing thresholds

All state is persisted to data/evolution_state.json so the engine survives
restarts. Writes are atomic (tmp + rename) to prevent corruption.
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VERSION: int = 1
_MAX_WINDOW: int = 100
_WEIGHT_ADJUST_INTERVAL: int = 25
_WEIGHT_CAP: int = 15
_DEFAULT_STATE_FILENAME: str = "evolution_state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_state() -> dict[str, Any]:
    return {
        "version": _VERSION,
        "updated_at": _now_iso(),
        "generation": 0,
        "total_trades": 0,
        "bandit": {},
        "weights": {},
        "thresholds": {},
    }


class EvolutionEngine:
    """Adaptive evolution engine for multi-lane trading strategy."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        if state_path is None:
            bot_root = Path(__file__).resolve().parent.parent
            state_path = bot_root / "data" / _DEFAULT_STATE_FILENAME
        self._path: Path = Path(state_path)
        self._state: dict[str, Any] = self._load()
        self._last_sampled: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        try:
            if self._path.exists():
                with open(self._path, "r") as fh:
                    data = json.load(fh)
                if isinstance(data, dict) and data.get("version") == _VERSION:
                    return data
                logger.warning("evolution: state version mismatch, resetting")
        except Exception as exc:
            logger.warning("evolution: failed to load state (%s), resetting", exc)
        return _empty_state()

    def _save(self) -> None:
        try:
            self._state["updated_at"] = _now_iso()
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent),
                prefix=".evo_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as fh:
                    json.dump(self._state, fh, indent=2)
                os.replace(tmp_path, str(self._path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as exc:
            logger.error("evolution: save failed: %s", exc)

    # ------------------------------------------------------------------
    # Component 1: Thompson Sampling Bandit
    # ------------------------------------------------------------------

    def _bandit(self) -> dict[str, dict[str, int]]:
        return self._state.setdefault("bandit", {})

    def sample_lane_priority(self, available_lanes: list[str]) -> list[str]:
        """Return available_lanes sorted by Thompson-sampled priority (best first).

        Each lane is treated as an arm in a multi-armed bandit.  Lanes with no
        history get a uniform Beta(1,1) prior so they are explored naturally.
        """
        try:
            bandit = self._bandit()
            scored: list[tuple[float, str]] = []
            for lane in available_lanes:
                stats = bandit.get(lane, {})
                alpha = stats.get("wins", 0) + 1
                beta = stats.get("losses", 0) + 1
                sample = random.betavariate(alpha, beta)
                scored.append((sample, lane))
                self._last_sampled[lane] = sample
            scored.sort(key=lambda t: t[0], reverse=True)
            return [lane for _, lane in scored]
        except Exception as exc:
            logger.error("evolution: sample_lane_priority failed: %s", exc)
            return list(available_lanes)

    def update_bandit(self, lane: str, won: bool) -> None:
        try:
            bandit = self._bandit()
            if lane not in bandit:
                bandit[lane] = {"wins": 0, "losses": 0}
            if won:
                bandit[lane]["wins"] += 1
            else:
                bandit[lane]["losses"] += 1
        except Exception as exc:
            logger.error("evolution: update_bandit failed: %s", exc)

    # ------------------------------------------------------------------
    # Component 2: Weight Adjuster
    # ------------------------------------------------------------------

    def _weights(self) -> dict[str, dict[str, Any]]:
        return self._state.setdefault("weights", {})

    def _ensure_weight_entry(self, lane: str) -> dict[str, Any]:
        weights = self._weights()
        if lane not in weights:
            weights[lane] = {
                "trade_count": 0,
                "pending": {},
                "adjustments": {},
                "last_adjusted_at": 0,
            }
        return weights[lane]

    def get_weight_adjustments(self, lane: str) -> dict[str, int]:
        """Return current weight deltas for lane. e.g. {"ADX_TREND": 5}."""
        try:
            entry = self._weights().get(lane)
            if entry is None:
                return {}
            return dict(entry.get("adjustments", {}))
        except Exception as exc:
            logger.error("evolution: get_weight_adjustments failed: %s", exc)
            return {}

    def update_weights(
        self,
        lane: str,
        flags_fired: dict[str, bool],
        won: bool,
    ) -> None:
        """Update flag win/loss counters and recalculate every 25 trades."""
        try:
            entry = self._ensure_weight_entry(lane)
            entry["trade_count"] += 1

            pending: dict[str, dict[str, int]] = entry.setdefault("pending", {})
            for flag, active in flags_fired.items():
                if not active:
                    continue
                if flag not in pending:
                    pending[flag] = {"w": 0, "l": 0}
                if won:
                    pending[flag]["w"] += 1
                else:
                    pending[flag]["l"] += 1

            trades_since = entry["trade_count"] - entry.get("last_adjusted_at", 0)
            if trades_since >= _WEIGHT_ADJUST_INTERVAL:
                adjustments: dict[str, int] = dict(entry.get("adjustments", {}))
                for flag, counts in pending.items():
                    w = counts.get("w", 0)
                    l = counts.get("l", 0)
                    total = w + l
                    if total < 5:
                        continue
                    flag_wr = w / total
                    if flag_wr > 0.55:
                        new_adj = min(adjustments.get(flag, 0) + 5, _WEIGHT_CAP)
                        adjustments[flag] = new_adj
                    elif flag_wr < 0.35:
                        new_adj = max(adjustments.get(flag, 0) - 5, -_WEIGHT_CAP)
                        adjustments[flag] = new_adj

                entry["adjustments"] = adjustments
                entry["last_adjusted_at"] = entry["trade_count"]
                entry["pending"] = {}
                self._state["generation"] = self._state.get("generation", 0) + 1
                self._save()
        except Exception as exc:
            logger.error("evolution: update_weights failed: %s", exc)

    # ------------------------------------------------------------------
    # Component 3: Threshold Optimizer
    # ------------------------------------------------------------------

    def _thresholds(self) -> dict[str, dict[str, Any]]:
        return self._state.setdefault("thresholds", {})

    def get_optimal_threshold(self, lane: str, base_threshold: int) -> int:
        """Search the rolling window for the PnL-maximizing threshold.

        Candidates: base-10 to base+20 in steps of 5.
        Falls back to base_threshold when data is insufficient.
        """
        try:
            entry = self._thresholds().get(lane)
            if entry is None:
                return base_threshold
            window: list[dict[str, Any]] = entry.get("window", [])
            if len(window) < 5:
                return base_threshold

            floor = base_threshold - 10
            ceiling = base_threshold + 25

            best_expected: float = -math.inf
            best_candidate: int = base_threshold

            for candidate in range(base_threshold - 10, base_threshold + 21, 5):
                passing = [t for t in window if t.get("score", 0) >= candidate]
                if len(passing) < 5:
                    continue
                wins = [t for t in passing if t.get("won", False)]
                losses = [t for t in passing if not t.get("won", False)]
                win_rate = len(wins) / len(passing)
                avg_win_pnl = (
                    sum(t.get("pnl", 0.0) for t in wins) / len(wins)
                    if wins
                    else 0.0
                )
                avg_loss_pnl = (
                    sum(t.get("pnl", 0.0) for t in losses) / len(losses)
                    if losses
                    else 0.0
                )
                expected = win_rate * avg_win_pnl - (1 - win_rate) * abs(avg_loss_pnl)
                if expected > best_expected:
                    best_expected = expected
                    best_candidate = candidate

            best_candidate = max(floor, min(ceiling, best_candidate))
            entry["optimal"] = best_candidate
            return best_candidate
        except Exception as exc:
            logger.error("evolution: get_optimal_threshold failed: %s", exc)
            return base_threshold

    def update_threshold_data(
        self,
        lane: str,
        score: int,
        threshold: int,
        pnl: float,
        won: bool,
    ) -> None:
        """Append a trade to the rolling window for lane (FIFO, max 100)."""
        try:
            thresholds = self._thresholds()
            if lane not in thresholds:
                thresholds[lane] = {"window": [], "optimal": threshold}
            window: list[dict[str, Any]] = thresholds[lane].setdefault("window", [])
            window.append({
                "score": score,
                "pnl": round(pnl, 4),
                "won": won,
            })
            if len(window) > _MAX_WINDOW:
                thresholds[lane]["window"] = window[-_MAX_WINDOW:]
        except Exception as exc:
            logger.error("evolution: update_threshold_data failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post_trade_update(
        self,
        lane: str,
        won: bool,
        pnl_usd: float,
        score: int,
        threshold: int,
        flags_fired: dict[str, bool],
    ) -> None:
        """Single entry point called after every closed trade."""
        try:
            self.update_bandit(lane, won)
            self.update_weights(lane, flags_fired, won)
            self.update_threshold_data(lane, score, threshold, pnl_usd, won)
            self._state["total_trades"] = self._state.get("total_trades", 0) + 1
            self._save()
        except Exception as exc:
            logger.error("evolution: post_trade_update failed: %s", exc)

    def get_lane_config(self, lane: str, base_threshold: int) -> dict[str, Any]:
        """Return evolved configuration for lane.

        Returns: {"threshold": int, "weight_adjustments": dict, "bandit_priority": float}
        """
        try:
            threshold = self.get_optimal_threshold(lane, base_threshold)
            weight_adj = self.get_weight_adjustments(lane)
            priority = self._last_sampled.get(lane, 0.5)
            return {
                "threshold": threshold,
                "weight_adjustments": weight_adj,
                "bandit_priority": round(priority, 4),
            }
        except Exception as exc:
            logger.error("evolution: get_lane_config failed: %s", exc)
            return {
                "threshold": base_threshold,
                "weight_adjustments": {},
                "bandit_priority": 0.5,
            }

    def get_dashboard_metrics(self) -> dict[str, Any]:
        """Return a snapshot of evolution state for the dashboard."""
        try:
            bandit_data: dict[str, dict[str, Any]] = {}
            for lane, stats in self._bandit().items():
                bandit_data[lane] = {
                    "wins": stats.get("wins", 0),
                    "losses": stats.get("losses", 0),
                    "priority": round(self._last_sampled.get(lane, 0.5), 4),
                }

            weight_changes: dict[str, dict[str, int]] = {}
            for lane, entry in self._weights().items():
                adj = entry.get("adjustments", {})
                if adj:
                    weight_changes[lane] = dict(adj)

            threshold_deltas: dict[str, int] = {}
            for lane, entry in self._thresholds().items():
                optimal = entry.get("optimal")
                if optimal is not None:
                    threshold_deltas[lane] = optimal

            return {
                "bandit": bandit_data,
                "weight_changes": weight_changes,
                "threshold_deltas": threshold_deltas,
                "generation": self._state.get("generation", 0),
                "total_trades": self._state.get("total_trades", 0),
            }
        except Exception as exc:
            logger.error("evolution: get_dashboard_metrics failed: %s", exc)
            return {
                "bandit": {},
                "weight_changes": {},
                "threshold_deltas": {},
                "generation": 0,
                "total_trades": 0,
            }
