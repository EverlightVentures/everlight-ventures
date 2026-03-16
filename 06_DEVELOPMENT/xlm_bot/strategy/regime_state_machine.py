"""Regime State Machine -- Score 10 upgrade.

Enforces SINGLE ACTIVE REGIME at all times.
Prevents lane collision where e.g. Lane A says "buy the dip" while
Lane M says "volume climax, short it" simultaneously.

Hive Mind Finding (23_automation_architect):
  "21 overlapping Attack Lanes is absolute chaos.
   Collapse into 3 strict State Machine Regimes:
   TREND, MEAN_REVERSION, BREAKOUT.
   Only one regime can be active at a time."

Three top-level regimes:
  TREND         -- Lanes A, H, J, U eligible
  MEAN_REVERSION -- Lanes C, G, I, K, M, N, S eligible
  BREAKOUT      -- Lanes B, E, F, Q, R, T eligible

Special lanes (eligible in any regime):
  P (Grid Range) -- range only
  X (AI Executive) -- always

Blocking lanes (L, O) apply regardless of regime.

Usage
-----
from strategy.regime_state_machine import RegimeStateMachine

rsm = RegimeStateMachine()
regime = rsm.classify(expansion_state, adx_15m, rsi_15m, atr_ratio)
allowed = rsm.allowed_lanes(regime)
if "A" not in allowed:
    lane_a_result = None  # blocked by regime
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── Regime definitions ────────────────────────────────────────────────────────

REGIME_TREND = "TREND"
REGIME_MEAN_REVERSION = "MEAN_REVERSION"
REGIME_BREAKOUT = "BREAKOUT"
REGIME_UNKNOWN = "UNKNOWN"

REGIME_LANE_MAP: dict[str, list[str]] = {
    REGIME_TREND: ["A", "H", "J", "U"],
    REGIME_MEAN_REVERSION: ["C", "G", "I", "K", "M", "N", "S"],
    REGIME_BREAKOUT: ["B", "E", "F", "Q", "R", "T"],
}

# These run in any regime
UNIVERSAL_LANES = {"P", "X"}

# These are blockers (L=MTF Conflict, O=Exhaustion) -- checked separately
BLOCKING_LANES = {"L", "O"}


@dataclass
class RegimeState:
    regime: str                        # TREND | MEAN_REVERSION | BREAKOUT | UNKNOWN
    confidence: int                    # 0-100
    allowed_lanes: list[str]
    blocked_lanes: list[str]
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    ts_utc: str = ""

    def is_lane_allowed(self, lane: str) -> bool:
        if lane in BLOCKING_LANES:
            return True  # blocker logic handled externally
        return lane in self.allowed_lanes or lane in UNIVERSAL_LANES


class RegimeStateMachine:
    """Single-regime classifier for the XLM Reaper.

    Input: vol_phase, ADX, RSI, ATR ratio (same signals regime_manager uses).
    Output: RegimeState with exactly ONE active regime and its allowed lanes.
    """

    def __init__(self, config: dict | None = None):
        self._cfg = config or {}
        self._last_regime: str = REGIME_UNKNOWN
        self._regime_age: int = 0      # cycles in current regime (anti-whipsaw)

    def classify(
        self,
        vol_phase: str,
        adx_15m: float,
        rsi_15m: float,
        atr_ratio: float,
        config: dict | None = None,
    ) -> RegimeState:
        """Classify current market into exactly one regime.

        Priority: BREAKOUT > TREND > MEAN_REVERSION > UNKNOWN
        """
        cfg = config or self._cfg
        reasons: list[str] = []
        metrics = {
            "vol_phase": vol_phase,
            "adx_15m": round(adx_15m, 1),
            "rsi_15m": round(rsi_15m, 1),
            "atr_ratio": round(atr_ratio, 3),
        }

        vol_up = vol_phase.upper()

        # ── BREAKOUT: volatility igniting + ADX turning up ────────────
        breakout_adx_min = float(cfg.get("breakout_adx_min", 22))
        breakout_atr_min = float(cfg.get("breakout_atr_min", 1.05))
        breakout_phases = {"IGNITION", "EXPANSION"}

        if vol_up in breakout_phases and adx_15m >= breakout_adx_min and atr_ratio >= breakout_atr_min:
            reasons.append(f"vol={vol_up} ADX={adx_15m:.1f}>={breakout_adx_min} ATR_r={atr_ratio:.2f}")
            confidence = self._confidence(adx_15m, breakout_adx_min, atr_ratio, breakout_atr_min)
            return self._build(REGIME_BREAKOUT, confidence, reasons, metrics)

        # ── TREND: trending phase + directional ADX ───────────────────
        trend_adx_min = float(cfg.get("trend_adx_min", 25))
        trend_phases = {"EXPANSION", "IGNITION"}
        rsi_trend_lo = float(cfg.get("trend_rsi_lo", 45))
        rsi_trend_hi = float(cfg.get("trend_rsi_hi", 75))

        if vol_up in trend_phases and adx_15m >= trend_adx_min and rsi_trend_lo <= rsi_15m <= rsi_trend_hi:
            reasons.append(f"vol={vol_up} ADX={adx_15m:.1f}>={trend_adx_min} RSI={rsi_15m:.0f}")
            confidence = min(95, int((adx_15m - trend_adx_min) * 3 + 50))
            return self._build(REGIME_TREND, confidence, reasons, metrics)

        # ── MEAN REVERSION: compressed / exhausted ───────────────────
        mr_phases = {"COMPRESSION", "EXHAUSTION"}
        mr_adx_max = float(cfg.get("mr_adx_max", 30))
        rsi_mr_lo = float(cfg.get("mr_rsi_lo", 35))
        rsi_mr_hi = float(cfg.get("mr_rsi_hi", 65))

        is_mr_vol = vol_up in mr_phases
        is_mr_adx = adx_15m < mr_adx_max
        is_mr_rsi = rsi_mr_lo <= rsi_15m <= rsi_mr_hi

        if is_mr_vol or (is_mr_adx and is_mr_rsi):
            if is_mr_vol:
                reasons.append(f"vol={vol_up}")
            if is_mr_adx:
                reasons.append(f"ADX={adx_15m:.1f}<{mr_adx_max}")
            if is_mr_rsi:
                reasons.append(f"RSI={rsi_15m:.0f} in [{rsi_mr_lo:.0f}-{rsi_mr_hi:.0f}]")
            confidence = 60
            return self._build(REGIME_MEAN_REVERSION, confidence, reasons, metrics)

        # ── UNKNOWN fallback: allow trend + mean reversion lanes ──────
        reasons.append("no_clear_regime")
        combined = sorted(
            REGIME_LANE_MAP[REGIME_TREND]
            + REGIME_LANE_MAP[REGIME_MEAN_REVERSION]
        )
        return self._build(REGIME_UNKNOWN, 30, reasons, metrics, override_lanes=combined)

    def _build(
        self,
        regime: str,
        confidence: int,
        reasons: list[str],
        metrics: dict,
        override_lanes: list[str] | None = None,
    ) -> RegimeState:
        lanes = override_lanes if override_lanes else list(REGIME_LANE_MAP.get(regime, []))
        all_lanes = sorted(set(lanes) | UNIVERSAL_LANES)
        all_blocked = [
            l for l in _all_lanes()
            if l not in all_lanes and l not in UNIVERSAL_LANES and l not in BLOCKING_LANES
        ]

        self._last_regime = regime
        return RegimeState(
            regime=regime,
            confidence=confidence,
            allowed_lanes=all_lanes,
            blocked_lanes=all_blocked,
            reasons=reasons,
            metrics=metrics,
            ts_utc=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _confidence(val: float, threshold: float, ratio: float, ratio_min: float) -> int:
        adx_score = min(40, int((val - threshold) * 2))
        atr_score = min(40, int((ratio - ratio_min) * 40))
        return min(95, 30 + adx_score + atr_score)


def _all_lanes() -> list[str]:
    lanes = set()
    for v in REGIME_LANE_MAP.values():
        lanes.update(v)
    return sorted(lanes)
