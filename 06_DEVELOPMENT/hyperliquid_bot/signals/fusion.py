"""
Hybrid signal fusion: confluence-gate -> regime-weights -> Kelly sizing.

Operator Rich Gee selected a 3-way hybrid (2026-05-19):
  Layer 1: Confluence gate -- 3-of-4 signals must agree on direction (entry binary)
  Layer 2: Regime-aware weights -- VIX regime selects which signal carries the load
  Layer 3: Kelly-style sizing -- position size scales with edge AND confidence

This module is the brain of the bot. Everything upstream (signal fetchers) produces
normalized SignalReadings. Everything downstream (the trade loop) consumes a single
TradeDecision. Fusion is the only file that knows how a signal becomes a trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


Side = Literal["long", "short"]
RegimeLabel = Literal["calm", "normal", "stressed"]
SignalSource = Literal[
    "polymarket_event_odds",
    "market_intel_macro",
    "spx_microstructure",
    "options_iv_skew",
]


@dataclass(frozen=True)
class SignalReading:
    """One signal source's view of the world. All sources normalize to this shape."""
    source: SignalSource
    direction: Side                  # which way this source thinks SPX goes
    confidence: float                # [0.0, 1.0] -- how sure the source is
    edge: float                      # [-1.0, +1.0] -- signed strength (sign = direction redundant w/ .direction; magnitude = conviction)
    age_seconds: float               # for staleness gate (90s in config)
    metadata: dict                   # source-specific: which Polymarket contract, which macro event, etc.


@dataclass(frozen=True)
class RegimeContext:
    """Current vol regime + the weight table the fusion should use."""
    label: RegimeLabel
    vix_spot: float
    weights: dict[SignalSource, float]   # loaded from config.regime_classifier.regimes[label]


@dataclass(frozen=True)
class TradeDecision:
    """The single output. None = stand down."""
    side: Side
    notional_usd: float              # what to send to Hyperliquid (capped by risk gate downstream)
    leverage: int                    # what to set on the order (1-50)
    stop_pct: float                  # adverse move % that triggers exit
    target_pct: float                # favorable move % for take-profit
    conviction: float                # [0.0, 1.0] -- aggregated, for audit log
    contributing_sources: list[SignalSource]
    reasoning: str                   # human-readable for Slack post + audit


# ---- Layer 1: Confluence gate ------------------------------------------------

CONFLUENCE_MIN = 3                   # from config.signal_confluence.min_required_for_entry
MONSTER_THRESHOLD = 4


def confluence_check(signals: list[SignalReading]) -> tuple[Side, list[SignalReading]] | None:
    """Return (consensus_side, agreeing_signals) if confluence met, else None.

    Confluence = at least CONFLUENCE_MIN signals agree on direction.
    Fresh signals only -- staleness is enforced upstream by the trade loop, but
    we also accept that any signal handed to us here passed the freshness gate.
    """
    longs = [s for s in signals if s.direction == "long"]
    shorts = [s for s in signals if s.direction == "short"]

    if len(longs) >= CONFLUENCE_MIN:
        return "long", longs
    if len(shorts) >= CONFLUENCE_MIN:
        return "short", shorts
    return None


# ---- Layer 2: Regime-aware aggregation --------------------------------------

def weighted_conviction(
    agreeing: list[SignalReading],
    regime: RegimeContext,
) -> float:
    """Combine agreeing signals into a single conviction score in [0.0, 1.0].

    Each signal contributes: weight[source] * confidence * |edge|
    Sum across sources, clamp to [0, 1].
    """
    score = 0.0
    for sig in agreeing:
        w = regime.weights.get(sig.source, 0.0)
        score += w * sig.confidence * abs(sig.edge)
    return max(0.0, min(1.0, score))


# ---- Layer 3: Kelly sizing (RICH'S CODE BLOCK) ------------------------------

# Constants you may reference. Pull from config in production; hardcoded here
# so you can run the function in isolation while writing it.
KELLY_FRACTION = 0.25                # quarter-Kelly (Thorp's safety adjustment)
MAX_LEVERAGE = 50                    # config.leverage.effective_cap
BASE_STOP_PCT = 0.6                  # 0.6% baseline stop -- tighter for higher conviction
WIN_LOSS_RATIO = 1.5                 # assume target = 1.5x stop distance


def size_kelly(
    conviction: float,               # output of weighted_conviction(), in [0,1]
    account_equity_usd: float,
    side: Side,
    contributing: list[SignalReading],
) -> TradeDecision:
    """
    ╔══════════════════════════════════════════════════════════════════════╗
    ║  YOUR 5-10 LINES, RICH                                               ║
    ║                                                                      ║
    ║  Inputs in scope:                                                    ║
    ║    - conviction: float in [0, 1]  (already regime-weighted)          ║
    ║    - account_equity_usd: float    (e.g. 250.0)                       ║
    ║    - side: "long" | "short"                                          ║
    ║    - contributing: list[SignalReading] (for metadata + reasoning)    ║
    ║                                                                      ║
    ║  Constants in scope (above):                                         ║
    ║    - KELLY_FRACTION  (0.25 = quarter-Kelly)                          ║
    ║    - MAX_LEVERAGE    (50, from your venue-max call)                  ║
    ║    - BASE_STOP_PCT   (0.6, tighten on higher conviction if you like) ║
    ║    - WIN_LOSS_RATIO  (1.5, target = 1.5x stop distance)              ║
    ║                                                                      ║
    ║  What you need to compute:                                           ║
    ║    1. kelly_fraction_of_equity = quarter-Kelly given conviction      ║
    ║       (classic Kelly: f* = p - (1-p)/b   where b = WIN_LOSS_RATIO    ║
    ║        and p = conviction interpreted as win-prob)                   ║
    ║    2. notional_usd = equity * leverage * kelly_fraction              ║
    ║       (downstream notional cap of 10x equity still applies)          ║
    ║    3. leverage: pick a value in [1, MAX_LEVERAGE] based on           ║
    ║       conviction (low conviction = low leverage; high conviction     ║
    ║       can scale up). This is YOUR call -- linear? stepped? capped?   ║
    ║    4. stop_pct: tighter when conviction high, wider when low.        ║
    ║       Suggestion: BASE_STOP_PCT * (1.5 - conviction) clamped >= 0.2  ║
    ║                                                                      ║
    ║  Trade-offs to weigh:                                                ║
    ║    - Kelly is mathematically optimal IF p is accurate. Our p comes   ║
    ║      from a weighted sum of 3+ noisy signals -- you may want to      ║
    ║      shrink p toward 0.5 to be conservative (e.g. p_shrunk =         ║
    ║      0.5 + 0.5 * (conviction - 0.5)).                                ║
    ║    - Pure Kelly recommends f* > 0 only when p > 1/(1+b) = 0.4 here.  ║
    ║      Below that, return TradeDecision with notional_usd=0 (or None   ║
    ║      and let the trade loop interpret as stand-down).                ║
    ║    - Leverage stepping: a simple rule like                           ║
    ║         lev = 1 + int(conviction * (MAX_LEVERAGE - 1))               ║
    ║      gives linear scaling. Aggressive but predictable.               ║
    ║                                                                      ║
    ║  Replace the TODO block below with your math.                        ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    # TODO(rich): compute kelly_fraction, leverage, notional, stop_pct here.
    kelly_fraction = 0.0       # <-- replace
    leverage = 1               # <-- replace
    notional_usd = 0.0         # <-- replace
    stop_pct = BASE_STOP_PCT   # <-- replace (or keep flat for v1)

    target_pct = stop_pct * WIN_LOSS_RATIO
    sources = [s.source for s in contributing]
    reasoning = (
        f"conviction={conviction:.2f} side={side} sources={sources} "
        f"kelly_f={kelly_fraction:.3f} lev={leverage}x notional=${notional_usd:.2f}"
    )

    return TradeDecision(
        side=side,
        notional_usd=notional_usd,
        leverage=leverage,
        stop_pct=stop_pct,
        target_pct=target_pct,
        conviction=conviction,
        contributing_sources=sources,
        reasoning=reasoning,
    )


# ---- Public entrypoint ------------------------------------------------------

def fuse(
    signals: list[SignalReading],
    regime: RegimeContext,
    account_equity_usd: float,
) -> TradeDecision | None:
    """Pipeline: confluence -> regime-weighted conviction -> Kelly sizing.

    Returns None if confluence not met (stand down). Otherwise returns a
    TradeDecision; the trade loop downstream applies the notional cap from
    the risk config and sends to Hyperliquid.
    """
    gate = confluence_check(signals)
    if gate is None:
        return None
    side, agreeing = gate

    conviction = weighted_conviction(agreeing, regime)
    decision = size_kelly(conviction, account_equity_usd, side, agreeing)

    if decision.notional_usd <= 0.0:
        return None      # Kelly said stand down
    return decision
