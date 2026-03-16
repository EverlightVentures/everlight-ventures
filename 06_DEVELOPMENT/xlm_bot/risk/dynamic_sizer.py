"""Dynamic position sizer -- Score 10 upgrade.

Replaces static dollar caps with math-driven sizing:
  1. Kelly Criterion fraction from lane win-rate + edge
  2. ATR-volatility scalar (wider market = smaller size)
  3. NAV-percentage hard ceiling (never risk >X% of account)
  4. Drawdown brake (scale down under drawdown stress)

Usage
-----
from risk.dynamic_sizer import compute_dynamic_size

result = compute_dynamic_size(
    nav=500.0,
    lane_stats=lane_perf["lanes"]["A"],
    atr_14=0.0025,
    price=0.159,
    config=config["dynamic_sizer"],
)
# result.contracts, result.risk_usd, result.kelly_fraction, result.notes
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── Defaults (override via config["dynamic_sizer"]) ─────────────────────────

_DEFAULT_MAX_RISK_PCT = 0.02          # 2% NAV per trade
_DEFAULT_KELLY_CAP = 0.25            # Half-Kelly cap at 25%
_DEFAULT_MIN_KELLY = 0.05            # Never go below 5% (floor)
_DEFAULT_ATR_SCALAR_BASE = 0.015     # Baseline ATR/Price ratio for neutral sizing
_DEFAULT_DRAWDOWN_BRAKE_PCT = 0.10   # 10% drawdown triggers step-down
_DEFAULT_DRAWDOWN_SCALE = 0.6        # Size at 10% drawdown = 60%
_DEFAULT_HARD_MAX_CONTRACTS = 2      # Absolute hard cap


@dataclass
class SizerResult:
    contracts: int
    risk_usd: float
    kelly_fraction: float
    nav_risk_pct: float
    atr_scalar: float
    drawdown_brake: float
    notes: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)


def _kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    cap: float,
    floor: float,
) -> tuple[float, str]:
    """Half-Kelly fraction from lane stats.

    Full Kelly = (W*b - L) / b where b = avg_win/avg_loss odds.
    We use half-Kelly for robustness.
    """
    if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0:
        return floor, "kelly_fallback_to_floor"

    b = avg_win / avg_loss           # odds ratio
    p = win_rate
    q = 1.0 - p

    full_k = (p * b - q) / b
    half_k = full_k * 0.5           # Half-Kelly

    # Clamp
    result = max(floor, min(cap, half_k))
    label = f"kelly={full_k:.3f} half={half_k:.3f} clamped={result:.3f}"
    return result, label


def _atr_scalar(
    atr_14: float,
    price: float,
    baseline_ratio: float,
) -> float:
    """Scale size inversely with ATR/price ratio.

    If ATR is double the baseline, size halves. If ATR is half, size doubles.
    Clamped to [0.4, 1.5].
    """
    if price <= 0 or atr_14 <= 0:
        return 1.0
    current_ratio = atr_14 / price
    if current_ratio <= 0:
        return 1.0
    scalar = baseline_ratio / current_ratio
    return max(0.4, min(1.5, scalar))


def _drawdown_brake(
    current_drawdown_usd: float,
    nav: float,
    brake_pct: float,
    scale_factor: float,
) -> tuple[float, str]:
    """Return scale multiplier based on current drawdown vs NAV.

    Above brake threshold: linear scale-down to scale_factor.
    """
    if nav <= 0 or current_drawdown_usd <= 0:
        return 1.0, "no_drawdown"

    dd_pct = current_drawdown_usd / nav
    if dd_pct < brake_pct:
        return 1.0, f"dd_pct={dd_pct:.1%}_ok"

    # Linear decay: at brake_pct -> scale_factor, at 2*brake_pct -> scale_factor/2
    excess = (dd_pct - brake_pct) / brake_pct
    brake = max(0.25, scale_factor - excess * (scale_factor - 0.25))
    return brake, f"dd_brake={brake:.2f} dd={dd_pct:.1%}"


def compute_dynamic_size(
    *,
    nav: float,
    price: float,
    contract_size_xlm: float = 5000.0,
    lane_stats: dict | None = None,
    atr_14: float = 0.0,
    current_drawdown_usd: float = 0.0,
    config: dict | None = None,
) -> SizerResult:
    """Compute Kelly + NAV-scaled position size.

    Parameters
    ----------
    nav : float
        Total account NAV in USD.
    price : float
        Current XLM price.
    contract_size_xlm : float
        XLM per contract (default 5000).
    lane_stats : dict | None
        Stats from lane_performance_tracker for this lane.
        Expected keys: win_rate, avg_pnl_usd, avg_loss_usd (optional).
    atr_14 : float
        14-period ATR value in USD.
    current_drawdown_usd : float
        Today's realized drawdown so far.
    config : dict | None
        Config section (dynamic_sizer). Overrides defaults.
    """
    notes: list[str] = []
    cfg = config or {}

    max_risk_pct = float(cfg.get("max_risk_pct", _DEFAULT_MAX_RISK_PCT))
    kelly_cap = float(cfg.get("kelly_cap", _DEFAULT_KELLY_CAP))
    kelly_floor = float(cfg.get("kelly_floor", _DEFAULT_MIN_KELLY))
    atr_base = float(cfg.get("atr_scalar_base", _DEFAULT_ATR_SCALAR_BASE))
    dd_brake_pct = float(cfg.get("drawdown_brake_pct", _DEFAULT_DRAWDOWN_BRAKE_PCT))
    dd_scale = float(cfg.get("drawdown_scale", _DEFAULT_DRAWDOWN_SCALE))
    hard_max = int(cfg.get("hard_max_contracts", _DEFAULT_HARD_MAX_CONTRACTS))

    # ── 1. Kelly fraction ─────────────────────────────────────────────
    wr = 0.50          # neutral default
    avg_win = 3.0
    avg_loss = 2.0

    if lane_stats:
        wr = float(lane_stats.get("win_rate", 0.50))
        avg_win = float(lane_stats.get("avg_win_usd", lane_stats.get("avg_pnl_usd", 3.0)))
        avg_loss = abs(float(lane_stats.get("avg_loss_usd", 2.0)))
        if avg_win <= 0:
            avg_win = 3.0
        if avg_loss <= 0:
            avg_loss = 2.0

    kelly_f, kelly_note = _kelly_fraction(wr, avg_win, avg_loss, kelly_cap, kelly_floor)
    notes.append(kelly_note)

    # ── 2. ATR scalar ─────────────────────────────────────────────────
    atrs = _atr_scalar(atr_14, price, atr_base)
    notes.append(f"atr_scalar={atrs:.2f}")

    # ── 3. Drawdown brake ─────────────────────────────────────────────
    dd_brake, dd_note = _drawdown_brake(current_drawdown_usd, nav, dd_brake_pct, dd_scale)
    notes.append(dd_note)

    # ── 4. Combined risk budget ───────────────────────────────────────
    combined_f = kelly_f * atrs * dd_brake
    risk_usd = nav * max_risk_pct * combined_f

    # ── 5. Convert to contracts ───────────────────────────────────────
    if price <= 0 or contract_size_xlm <= 0:
        return SizerResult(
            contracts=0,
            risk_usd=0.0,
            kelly_fraction=kelly_f,
            nav_risk_pct=0.0,
            atr_scalar=atrs,
            drawdown_brake=dd_brake,
            notes=notes + ["zero_price_or_contract_size"],
        )

    notional_per_contract = price * contract_size_xlm
    raw_contracts = risk_usd / notional_per_contract if notional_per_contract > 0 else 0
    contracts = max(1, min(hard_max, math.floor(raw_contracts)))

    actual_risk = contracts * notional_per_contract
    nav_risk_pct = actual_risk / nav if nav > 0 else 0.0

    notes.append(
        f"contracts={contracts} risk_usd=${risk_usd:.2f} nav_risk={nav_risk_pct:.1%}"
    )

    return SizerResult(
        contracts=contracts,
        risk_usd=round(risk_usd, 2),
        kelly_fraction=round(kelly_f, 4),
        nav_risk_pct=round(nav_risk_pct, 4),
        atr_scalar=round(atrs, 3),
        drawdown_brake=round(dd_brake, 3),
        notes=notes,
        detail={
            "nav": nav,
            "price": price,
            "win_rate": wr,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "kelly_full": round((wr * (avg_win / avg_loss) - (1 - wr)) / (avg_win / avg_loss), 4) if avg_loss > 0 else 0,
            "kelly_half": round(kelly_f, 4),
            "atr_14": atr_14,
            "drawdown_usd": current_drawdown_usd,
        },
    )
