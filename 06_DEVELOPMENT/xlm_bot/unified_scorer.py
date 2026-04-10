"""Unified Scoring Engine -- replaces 18 independent gates with ONE weighted score.

The V4 confluence score becomes the BASE (normalized 0-100).
Each former gate becomes a modifier that adds or subtracts points.
Only hard risk gates (in risk_gate.py) can block a trade outright.

Score >= entry_threshold  =>  TRADE
Score < entry_threshold   =>  HOLD

Quality tiers derived from score distance above/below threshold:
  MONSTER: score >= threshold + 20
  FULL:    score >= threshold
  REDUCED: score >= threshold - 10
  SCALP:   score >= threshold - 20
  NO_TRADE: below all
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class UnifiedScore:
    """Result of the unified scoring engine."""
    final_score: int = 0
    base_score: int = 0                    # V4 confluence score (normalized 0-100)
    entry_threshold: int = 60              # Score needed to trade
    quality_tier: str = "NO_TRADE"         # MONSTER / FULL / REDUCED / SCALP / NO_TRADE
    recommendation: str = "HOLD"           # ENTER / HOLD
    direction: str = ""
    regime: str = "neutral"

    # Modifier breakdown (each is the points added/subtracted)
    modifiers: dict[str, int] = field(default_factory=dict)

    # Human-readable reasoning
    reasons: list[str] = field(default_factory=list)

    # Full breakdown for dashboard report card
    breakdown: dict[str, Any] = field(default_factory=dict)

    # Context fields for narrative (set by caller)
    entry_type: str = ""
    price: float = 0.0
    rsi_value: float = 0.0
    fib_level: str = ""
    structure_bias_str: str = ""

    # Alternative strategies considered (set by caller)
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    # Win probability from EV model
    p_win: float = 0.0
    # Expected profit from TP targets
    profit_anticipated_usd: float = 0.0
    # Risk:Reward ratio
    rr_ratio: float = 0.0

    # The play-call narrative
    narrative: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def build_narrative(self) -> str:
        """Build a human-readable play-call narrative from the score breakdown.

        Reads like a trader explaining the call, not a data dump.
        """
        parts: list[str] = []

        # Lead with the strategy and setup geometry
        entry_label = self.entry_type.replace("_", " ").title() if self.entry_type else "Setup"
        dir_label = self.direction or "neutral"

        if self.recommendation == "ENTER":
            parts.append(f"{entry_label} is the play.")
        else:
            parts.append(f"{entry_label} sees a {dir_label} setup forming")
            if not self.direction:
                parts[-1] = "No clear setup right now"

        # Structure and regime context
        if self.structure_bias_str and self.structure_bias_str != "neutral":
            parts.append(f"15m structure is {self.structure_bias_str}, we're {dir_label}-biased")

        if self.regime and self.regime != "neutral":
            regime_label = self.regime.replace("_", " ")
            parts.append(f"regime is {regime_label}")

        # Key indicator context
        if self.rsi_value > 0:
            parts.append(f"RSI at {self.rsi_value:.0f}")
        if self.fib_level:
            parts.append(f"sitting at the {self.fib_level} fib")

        # Top positive and negative modifiers (the meat of the explanation)
        pos_mods = sorted(
            [(k, v) for k, v in self.modifiers.items() if v > 0],
            key=lambda x: -x[1],
        )
        neg_mods = sorted(
            [(k, v) for k, v in self.modifiers.items() if v < 0],
            key=lambda x: x[1],
        )

        if pos_mods:
            confirms = [k.replace("_", " ") for k, _ in pos_mods[:3]]
            parts.append(f"confirmed by {', '.join(confirms)}")

        if neg_mods:
            headwinds = []
            for k, v in neg_mods[:2]:
                label = k.replace("_", " ")
                headwinds.append(label)
            if headwinds:
                parts.append(f"headwinds: {', '.join(headwinds)}")

        # Score and decision
        parts.append(f"Score: {self.final_score}")

        if self.recommendation == "ENTER":
            if self.quality_tier in ("REDUCED", "SCALP"):
                parts.append(
                    f"going in {self.quality_tier} size"
                )
            elif self.quality_tier == "MONSTER":
                parts.append("MONSTER quality -- full send")
            else:
                parts.append(f"entering {self.quality_tier}")
        else:
            # Explain what would need to change
            deficit = self.entry_threshold - self.final_score
            if neg_mods:
                worst = neg_mods[0][0].replace("_", " ")
                parts.append(
                    f"holding -- need {deficit} more points, biggest drag is {worst}"
                )
            else:
                parts.append(f"holding -- base score too low, need {deficit} more")

        # Stitch into flowing narrative
        narrative = ". ".join(parts) + "."

        # Clean up double periods and awkward joins
        narrative = narrative.replace("..", ".").replace(". .", ".")
        self.narrative = narrative
        return narrative


# --- Default weights (tunable from config) ---
DEFAULT_WEIGHTS = {
    # Regime alignment: do regime gates confirm?
    "regime_alignment":      {"max": 12, "min": -12},
    # EV filter: expected value positive/negative
    "ev_filter":             {"max": 8,  "min": -8},
    # AI executive opinion
    "ai_opinion":            {"max": 10, "min": -18},
    # Sentiment
    "sentiment":             {"max": 5,  "min": -10},
    # Rolling expectancy (bot running hot/cold)
    "expectancy":            {"max": 8,  "min": -10},
    # Structure alignment (countertrend penalty -- reduced from -15 to -8)
    "structure_alignment":   {"max": 5,  "min": -8},
    # Dip retrace (bounce detection for shorts)
    "dip_retrace":           {"max": 0,  "min": -10},
    # Support proximity (shorts near support)
    "support_proximity":     {"max": 0,  "min": -5},
    # Range chase (entered too far into range)
    "range_chase":           {"max": 0,  "min": -5},
    # Regime mode
    "regime_mode":           {"max": 0,  "min": -12},
    # Lane V cooldown
    "lane_cooldown":         {"max": 0,  "min": -8},
    # Daily profit target proximity
    "daily_target":          {"max": 0,  "min": -8},
    # Revenge pattern (3 losses same zone)
    "revenge_pattern":       {"max": 0,  "min": -5},
    # Macro vision alignment
    "macro_vision":          {"max": 8,  "min": -5},
    # Contract context (OI / funding / basis)
    "contract_context":      {"max": 6,  "min": -4},
    # BTC correlation
    "btc_correlation":       {"max": 5,  "min": -5},
    # Consensus bonus (multiple lanes agree)
    "lane_consensus":        {"max": 8,  "min": 0},
    # Trade memory (learns from recent wins/losses -- capped to prevent paralysis)
    "trade_memory":          {"max": 15, "min": -8},
    # Candle math (market is moving enough to hit TP?)
    "candle_aggression":     {"max": 10, "min": -5},
    # Foresight (does this trade match an anticipated scenario?)
    "foresight":             {"max": 10, "min": 0},
    # Trap detector (liquidation zones and squeeze setups)
    "trap_detector":         {"max": 10, "min": -12},
    # Session quality (prime trading hours = better moves)
    "session_quality":       {"max": 8, "min": -3},
    # Fee intelligence (cost awareness -- capped to prevent paralysis)
    "fee_intelligence":      {"max": 0, "min": -8},
    # Perplexity context (directional filter from macro watchlist)
    "perplexity_context":    {"max": 5, "min": -8},
}

# --- Threshold defaults ---
DEFAULT_ENTRY_THRESHOLD = 40
DEFAULT_SCALP_THRESHOLD = 25
DEFAULT_HTF_THRESHOLD = 40
TIER_GAPS = {"monster_above": 20, "full_at": 0, "reduced_gap": 10, "scalp_gap": 20}


def _normalize_v4_score(raw_score: int, raw_threshold: int) -> int:
    """Normalize V4 score to 0-100 scale.

    V4 scores range roughly 0-160 with thresholds 70-75.
    We map: raw_threshold -> 50 (midpoint), 0 -> 0, 2*threshold -> 100.
    This gives threshold-meeting setups a 50 base, leaving room for
    modifiers to push above or below the entry threshold (40).
    """
    if raw_threshold <= 0:
        raw_threshold = 75
    if raw_score <= 0:
        return 0
    normalized = int(round((raw_score / raw_threshold) * 50))
    return max(0, min(100, normalized))


def _compute_tier(score: int, threshold: int) -> str:
    gap = threshold - score
    if gap <= 0:
        if score >= threshold + TIER_GAPS["monster_above"]:
            return "MONSTER"
        return "FULL"
    if gap <= TIER_GAPS["reduced_gap"]:
        return "REDUCED"
    if gap <= TIER_GAPS["scalp_gap"]:
        return "SCALP"
    return "NO_TRADE"


def score_setup(
    *,
    # V4 base score
    v4_score: int = 0,
    v4_threshold: int = 75,
    v4_regime: str = "neutral",
    direction: str = "",

    # Regime gates result
    gates: dict[str, bool] | None = None,
    route_tier: str = "full",

    # EV snapshot
    ev_snapshot: dict[str, Any] | None = None,

    # AI signals
    ai_directive: dict[str, Any] | None = None,
    ai_insight: dict[str, Any] | None = None,

    # Sentiment
    sentiment_data: dict[str, Any] | None = None,
    sentiment_result: dict[str, Any] | None = None,

    # Rolling expectancy
    expectancy_data: dict[str, Any] | None = None,
    expectancy_result: dict[str, Any] | None = None,

    # Structure
    structure_bias: str = "neutral",

    # Dip retrace
    dip_retrace_blocked: bool = False,

    # Support proximity
    support_proximity_blocked: bool = False,

    # Range chase
    range_position: float = 0.5,

    # Regime mode
    regime_mode_block: dict[str, Any] | None = None,

    # Lane V cooldown
    lane_cooldown_active: bool = False,

    # Daily profit target
    pnl_today: float = 0.0,
    daily_profit_target: float = 0.0,

    # Revenge pattern
    zone_losses: int = 0,

    # Macro vision
    macro_vision: dict[str, Any] | None = None,

    # Contract/BTC/consensus modifiers (already computed as ints)
    contract_mod: int = 0,
    btc_mod: int = 0,
    consensus_bonus: int = 0,

    # Session quality (what hour of the day -- prime hours get a boost)
    hour_utc: int = 12,

    # Candle math aggression (is the market moving enough?)
    candle_aggression: int = 0,
    candle_aggression_reason: str = "",

    # Foresight (does trade match anticipated scenario?)
    foresight_boost: int = 0,
    foresight_reason: str = "",

    # Trap detector (liquidation zones)
    trap_modifier: int = 0,
    trap_reason: str = "",

    # Trade memory (from strategy.trade_memory)
    trade_memory_score: int = 0,
    trade_memory_min_override: int = 0,
    trade_memory_reasons: list[str] | None = None,

    # Fee intelligence (from strategy.fee_intelligence)
    fee_intel_score: int = 0,
    fee_intel_block: bool = False,
    fee_intel_reasons: list[str] | None = None,

    # Entry type (for scalp vs HTF threshold selection)
    entry_type: str = "",

    # Perplexity context (macro watchlist data)
    perplexity_context: dict[str, Any] | None = None,

    # Config overrides
    config: dict[str, Any] | None = None,
) -> UnifiedScore:
    """Compute the ONE unified score for a trade setup.

    Returns UnifiedScore with final_score, quality_tier, recommendation,
    and full breakdown.
    """
    cfg = (config or {}).get("unified_scorer", {}) or {}
    weights = dict(DEFAULT_WEIGHTS)
    cfg_weights = cfg.get("weights", {})
    if isinstance(cfg_weights, dict):
        for k, v in cfg_weights.items():
            if k in weights and isinstance(v, dict):
                weights[k] = {**weights[k], **v}

    # Scalp vs HTF threshold: scalps get a lower bar (faster, smaller targets)
    _scalp_types = {"micro_sweep", "breakout_retest", "pullback", "compression_range"}
    _htf_types = {"htf_swing", "range_fvg_retest", "htf_breakout_continuation"}
    if entry_type in _scalp_types:
        entry_threshold = int(cfg.get("scalp_threshold", DEFAULT_SCALP_THRESHOLD))
    elif entry_type in _htf_types:
        entry_threshold = int(cfg.get("htf_threshold", DEFAULT_HTF_THRESHOLD))
    else:
        entry_threshold = int(cfg.get("entry_threshold", DEFAULT_ENTRY_THRESHOLD))

    result = UnifiedScore(
        entry_threshold=entry_threshold,
        direction=direction,
        regime=v4_regime,
    )
    modifiers: dict[str, int] = {}
    reasons: list[str] = []

    # -- BASE SCORE: normalized V4 confluence --
    base = _normalize_v4_score(v4_score, v4_threshold)
    result.base_score = base
    result.breakdown["v4_raw"] = v4_score
    result.breakdown["v4_threshold"] = v4_threshold
    result.breakdown["v4_normalized"] = base

    running = base

    # -- MODIFIER 1: Regime alignment --
    w = weights["regime_alignment"]
    if gates:
        passing = sum(1 for v in gates.values() if v)
        total = len(gates) or 1
        ratio = passing / total
        if ratio >= 1.0:
            mod = w["max"]
            reasons.append(f"all {total} regime gates pass (+{mod})")
        elif ratio >= 0.75:
            mod = w["max"] // 2
            reasons.append(f"{passing}/{total} regime gates pass (+{mod})")
        elif ratio >= 0.5:
            mod = 0
        else:
            mod = w["min"]
            failed = [k for k, v in gates.items() if not v]
            reasons.append(f"regime gates failing: {', '.join(failed)} ({mod})")
    else:
        mod = 0
    modifiers["regime_alignment"] = mod
    running += mod

    # -- MODIFIER 2: EV filter --
    w = weights["ev_filter"]
    if ev_snapshot:
        ev_pass = bool(ev_snapshot.get("pass"))
        ev_usd = float(ev_snapshot.get("ev_usd", 0))
        if ev_pass and ev_usd > 0.5:
            mod = w["max"]
            reasons.append(f"EV positive ${ev_usd:.2f} (+{mod})")
        elif ev_pass:
            mod = w["max"] // 2
        elif ev_usd < -0.5:
            mod = w["min"]
            reasons.append(f"EV negative ${ev_usd:.2f} ({mod})")
        else:
            mod = w["min"] // 2
    else:
        mod = 0
    modifiers["ev_filter"] = mod
    running += mod

    # -- MODIFIER 3: AI opinion --
    w = weights["ai_opinion"]
    ai_mod = 0
    if ai_directive:
        action = str(ai_directive.get("action", "")).upper()
        confidence = float(ai_directive.get("confidence", 0))
        if action == "FLAT" and confidence >= 0.6:
            ai_mod = w["min"]
            reasons.append(f"AI executive says FLAT (conf {confidence:.0%}) ({ai_mod})")
        elif action in ("ENTER_LONG", "ENTER_SHORT"):
            ai_mod = int(w["max"] * confidence)
            reasons.append(f"AI executive says {action} (conf {confidence:.0%}) (+{ai_mod})")
    if ai_insight:
        verdict = str(ai_insight.get("verdict", ""))
        adj = int(ai_insight.get("score_adjustment", 0))
        if verdict == "skip" and float(ai_insight.get("confidence", 0)) >= 0.7:
            ai_mod = min(ai_mod, w["min"] + 3)
            reasons.append(f"AI insight says skip ({ai_mod})")
        elif adj != 0:
            adj = max(-10, min(10, adj))
            ai_mod += adj
    modifiers["ai_opinion"] = ai_mod
    running += ai_mod

    # -- MODIFIER 4: Sentiment --
    w = weights["sentiment"]
    if sentiment_result:
        allowed = sentiment_result.get("allowed", True)
        size_mult = float(sentiment_result.get("size_mult", 1.0))
        if not allowed:
            mod = w["min"]
            reasons.append(f"sentiment gate blocked ({mod})")
        elif size_mult < 0.8:
            mod = w["min"] // 2
        elif size_mult > 1.1:
            mod = w["max"]
        else:
            mod = 0
    else:
        mod = 0
    modifiers["sentiment"] = mod
    running += mod

    # -- MODIFIER 5: Rolling expectancy --
    w = weights["expectancy"]
    if expectancy_result:
        allowed = expectancy_result.get("allowed", True)
        if not allowed:
            mod = w["min"]
            reasons.append(f"expectancy kill-switch active ({mod})")
        else:
            size_mult = float(expectancy_result.get("size_mult", 1.0))
            if size_mult >= 1.2:
                mod = w["max"]
                reasons.append(f"bot running hot, expectancy bonus (+{mod})")
            elif size_mult >= 1.0:
                mod = w["max"] // 2
            else:
                mod = int(w["min"] * (1.0 - size_mult))
    else:
        mod = 0
    modifiers["expectancy"] = mod
    running += mod

    # -- MODIFIER 6: Structure alignment --
    w = weights["structure_alignment"]
    if structure_bias != "neutral" and direction:
        is_counter = (
            (structure_bias == "bearish" and direction == "long") or
            (structure_bias == "bullish" and direction == "short")
        )
        if is_counter:
            mod = w["min"]
            reasons.append(f"countertrend: {direction} vs {structure_bias} structure ({mod})")
        else:
            mod = w["max"]
            reasons.append(f"structure confirms {direction} (+{mod})")
    else:
        mod = 0
    modifiers["structure_alignment"] = mod
    running += mod

    # -- MODIFIER 7: Dip retrace --
    w = weights["dip_retrace"]
    if dip_retrace_blocked:
        mod = w["min"]
        reasons.append(f"bounce detected, short penalized ({mod})")
    else:
        mod = 0
    modifiers["dip_retrace"] = mod
    running += mod

    # -- MODIFIER 8: Support proximity --
    w = weights["support_proximity"]
    if support_proximity_blocked:
        mod = w["min"]
        reasons.append(f"price near support, short penalized ({mod})")
    else:
        mod = 0
    modifiers["support_proximity"] = mod
    running += mod

    # -- MODIFIER 9: Range chase --
    w = weights["range_chase"]
    if direction:
        chasing = (direction == "long" and range_position > 0.80) or \
                  (direction == "short" and range_position < 0.20)
        if chasing:
            mod = w["min"]
            reasons.append(f"chasing: {range_position*100:.0f}% into range ({mod})")
        else:
            mod = 0
    else:
        mod = 0
    modifiers["range_chase"] = mod
    running += mod

    # -- MODIFIER 10: Regime mode --
    w = weights["regime_mode"]
    if regime_mode_block:
        mod = w["min"]
        reasons.append(f"regime mode block active ({mod})")
    else:
        mod = 0
    modifiers["regime_mode"] = mod
    running += mod

    # -- MODIFIER 11: Lane cooldown --
    w = weights["lane_cooldown"]
    if lane_cooldown_active:
        mod = w["min"]
        reasons.append(f"lane V cooldown active ({mod})")
    else:
        mod = 0
    modifiers["lane_cooldown"] = mod
    running += mod

    # -- MODIFIER 12: Daily profit target --
    w = weights["daily_target"]
    if daily_profit_target > 0 and pnl_today >= daily_profit_target:
        mod = w["min"]
        reasons.append(f"daily target hit: ${pnl_today:.2f} >= ${daily_profit_target:.2f} ({mod})")
    elif daily_profit_target > 0 and pnl_today >= daily_profit_target * 0.8:
        mod = w["min"] // 2
        reasons.append(f"near daily target ({mod})")
    else:
        mod = 0
    modifiers["daily_target"] = mod
    running += mod

    # -- MODIFIER 13: Revenge pattern --
    # Triggers on zone losses (same price area) OR consecutive losses (any area)
    w = weights["revenge_pattern"]
    _consec_losses = int(trade_memory_min_override > 60)  # trade memory raises threshold when losing
    if zone_losses >= 3:
        mod = w["min"]
        reasons.append(f"{zone_losses} losses in same zone -- revenge blocked ({mod})")
    elif zone_losses >= 2:
        mod = w["min"] // 2
        reasons.append(f"{zone_losses} losses in zone -- caution ({mod})")
    elif pnl_today < -10:
        mod = -5
        reasons.append(f"down ${abs(pnl_today):.0f} today -- extra caution (-5)")
    else:
        mod = 0
    modifiers["revenge_pattern"] = mod
    running += mod

    # -- MODIFIER 14: Macro vision --
    w = weights["macro_vision"]
    if macro_vision:
        aligned = bool(macro_vision.get("aligned"))
        risk = str(macro_vision.get("risk", "")).lower()
        if aligned:
            mod = w["max"]
            reasons.append(f"macro vision aligned (+{mod})")
        elif risk == "high":
            mod = w["min"]
            reasons.append(f"macro vision high risk ({mod})")
        else:
            mod = 0
    else:
        mod = 0
    modifiers["macro_vision"] = mod
    running += mod

    # -- MODIFIER 15: Contract context --
    w = weights["contract_context"]
    mod = max(w["min"], min(w["max"], contract_mod))
    modifiers["contract_context"] = mod
    running += mod

    # -- MODIFIER 16: BTC correlation --
    w = weights["btc_correlation"]
    mod = max(w["min"], min(w["max"], btc_mod))
    modifiers["btc_correlation"] = mod
    running += mod

    # -- MODIFIER 17: Lane consensus --
    w = weights["lane_consensus"]
    mod = max(w["min"], min(w["max"], consensus_bonus))
    if mod > 0:
        reasons.append(f"lane consensus bonus (+{mod})")
    modifiers["lane_consensus"] = mod
    running += mod

    # -- MODIFIER 18: Session quality --
    # Crypto trades 24/7 but volume varies. Three major sessions overlap:
    # Asia (0-8 UTC / 4pm-midnight PT) -- solid volume, altcoin moves
    # London (7-15 UTC / 11pm-7am PT) -- overlap with Asia is strong
    # US (13-21 UTC / 5am-1pm PT) -- highest volume, biggest moves
    # Only truly dead: ~10-12 UTC (2-4am PT) gap between London close and US pre
    w = weights["session_quality"]
    mod = 0
    if 13 <= hour_utc <= 21:
        mod = w["max"]  # US session -- peak volume
        reasons.append(f"US session -- highest volume, cleanest setups (+{mod})")
    elif 7 <= hour_utc < 13:
        mod = w["max"] // 2 + 1  # London + Asia/London overlap
    elif 0 <= hour_utc < 7:
        mod = w["max"] // 2  # Asia session -- altcoins active
    elif 22 <= hour_utc <= 23:
        mod = w["max"] // 2  # US close / Asia pre-open
    modifiers["session_quality"] = mod
    running += mod

    # -- MODIFIER 19: Foresight --
    w = weights["foresight"]
    mod = max(w["min"], min(w["max"], foresight_boost))
    if mod > 0 and foresight_reason:
        reasons.append(foresight_reason)
    modifiers["foresight"] = mod
    running += mod

    # -- MODIFIER 20: Trap detector --
    w = weights["trap_detector"]
    mod = max(w["min"], min(w["max"], trap_modifier))
    if mod != 0 and trap_reason:
        reasons.append(trap_reason)
    modifiers["trap_detector"] = mod
    running += mod

    # -- MODIFIER 21: Candle aggression --
    w = weights["candle_aggression"]
    mod = max(w["min"], min(w["max"], candle_aggression))
    if mod != 0 and candle_aggression_reason:
        reasons.append(candle_aggression_reason)
    modifiers["candle_aggression"] = mod
    running += mod

    # -- MODIFIER 20: Trade memory --
    w = weights["trade_memory"]
    mod = max(w["min"], min(w["max"], trade_memory_score))
    if mod != 0:
        reasons.extend(trade_memory_reasons or [])
    modifiers["trade_memory"] = mod
    running += mod

    # -- MODIFIER 22: Fee intelligence --
    # Fee-aware expectancy, churn detection, lane fee health
    mod = max(-25, min(0, fee_intel_score))  # only penalties, max -25
    if mod != 0:
        reasons.extend(fee_intel_reasons or [])
    modifiers["fee_intelligence"] = mod
    running += mod
    # Hard block from fee intelligence
    if fee_intel_block:
        running = min(running, 20)  # crush score below any threshold
        reasons.append("FEE INTEL HARD BLOCK: lane disabled or fee+churn combo")

    # -- MODIFIER 23: Perplexity context (macro directional filter) --
    # Reads data/perplexity_context.json written by hourly poller.
    # Hybrid-C: directional filter with breakout proximity sub-gate.
    # Confirms direction = +5, counter-trend when bias strong = -8,
    # near range edge going counter = extra penalty (breakout proximity).
    w = weights.get("perplexity_context", {"max": 5, "min": -8})
    pctx = perplexity_context or {}
    pctx_mod = 0
    if pctx and not pctx.get("stale", True) and direction:
        bias = str(pctx.get("momentum_bias", "NEUTRAL")).upper()
        bp = pctx.get("breakout_proximity") or {}
        range_pos = float(bp.get("range_position", 0.5))

        # Directional alignment check
        bias_bullish = bias in ("LEAN_BULLISH", "BULLISH")
        bias_bearish = bias in ("LEAN_BEARISH", "BEARISH")
        confirms = (
            (direction == "long" and bias_bullish) or
            (direction == "short" and bias_bearish)
        )
        conflicts = (
            (direction == "long" and bias_bearish) or
            (direction == "short" and bias_bullish)
        )

        if confirms:
            pctx_mod = w["max"]
            reasons.append(f"perplexity bias {bias} confirms {direction} (+{pctx_mod})")
        elif conflicts:
            pctx_mod = w["min"]
            reasons.append(f"perplexity bias {bias} vs {direction} ({pctx_mod})")

        # Breakout proximity sub-gate: penalize counter-trend near range edges
        # Longing near 90d low with bearish bias = -6 extra
        # Shorting near 90d high with bullish bias = -6 extra
        near_low = range_pos < 0.15
        near_high = range_pos > 0.85
        if near_low and direction == "short" and not bias_bearish:
            pctx_mod = min(pctx_mod, pctx_mod - 6)
            reasons.append(f"breakout proximity: shorting near 90d low (range {range_pos:.0%}) (-6)")
        elif near_high and direction == "long" and not bias_bullish:
            pctx_mod = min(pctx_mod, pctx_mod - 6)
            reasons.append(f"breakout proximity: longing near 90d high (range {range_pos:.0%}) (-6)")

        # RSI extreme override: if RSI confirms the trade direction, soften penalty
        pctx_rsi = float(pctx.get("rsi_14", 50))
        if conflicts and pctx_rsi < 30 and direction == "long":
            # RSI oversold = mean reversion long is valid even if bias is bearish
            pctx_mod = max(pctx_mod, -3)
            reasons.append(f"perplexity RSI oversold ({pctx_rsi:.0f}) softens bearish penalty")
        elif conflicts and pctx_rsi > 70 and direction == "short":
            pctx_mod = max(pctx_mod, -3)
            reasons.append(f"perplexity RSI overbought ({pctx_rsi:.0f}) softens bullish penalty")

    modifiers["perplexity_context"] = pctx_mod
    running += pctx_mod

    # -- FINAL SCORE --
    # Variable negative cap: weak base scores get tighter caps
    # A MONSTER base (60+) can take headwinds; a marginal base (40) can't
    _total_negative = sum(v for v in modifiers.values() if v < 0)
    if running < 40:
        _neg_cap = -15  # weak setup: penalties bite hard
    elif running < 50:
        _neg_cap = -20  # marginal setup: moderate penalty tolerance
    elif running < 60:
        _neg_cap = -25  # decent setup: reasonable headwind room
    else:
        _neg_cap = -35  # strong setup: can absorb penalties

    if _total_negative < _neg_cap:
        _excess = _total_negative - _neg_cap
        running -= _excess
        reasons.append("penalty cap (%d): negatives capped, was %d" % (_neg_cap, _total_negative))

    # Trade memory can nudge threshold but never raise it more than 10 pts
    effective_threshold = entry_threshold
    if trade_memory_min_override > entry_threshold:
        effective_threshold = min(trade_memory_min_override, entry_threshold + 10)

    final = max(0, min(100, running))
    result.final_score = final
    result.modifiers = modifiers
    result.reasons = reasons
    result.quality_tier = _compute_tier(final, effective_threshold)

    # Dead zone: scores within dead_zone_width of threshold = HOLD for confirmation
    _dead_zone = int(cfg.get("dead_zone_width", 0))
    _min_tier = str(cfg.get("min_quality_tier", "SCALP")).upper()

    if _dead_zone > 0 and 0 < (final - effective_threshold) < _dead_zone:
        result.recommendation = "HOLD"
        reasons.append(
            "dead zone: score %d within %d pts of threshold %d -- hold for confirmation"
            % (final, _dead_zone, effective_threshold)
        )
    elif final >= effective_threshold:
        # Quality floor check: don't enter if tier is below minimum
        _tier_rank = {"NO_TRADE": 0, "SCALP": 1, "REDUCED": 2, "FULL": 3, "MONSTER": 4}
        if _tier_rank.get(result.quality_tier, 0) < _tier_rank.get(_min_tier, 0):
            result.recommendation = "HOLD"
            reasons.append(
                "quality floor: tier %s below minimum %s" % (result.quality_tier, _min_tier)
            )
        else:
            result.recommendation = "ENTER"
    else:
        result.recommendation = "HOLD"

    result.entry_threshold = effective_threshold

    # Summary breakdown for dashboard
    result.breakdown["modifiers_sum"] = sum(modifiers.values())
    result.breakdown["positive_mods"] = {k: v for k, v in modifiers.items() if v > 0}
    result.breakdown["negative_mods"] = {k: v for k, v in modifiers.items() if v < 0}
    result.breakdown["neutral_mods"] = {k: v for k, v in modifiers.items() if v == 0}

    return result


def build_alternatives(
    *,
    selected_entry_type: str,
    selected_direction: str,
    selected_score: int,
    long_v4: dict[str, Any] | None = None,
    short_v4: dict[str, Any] | None = None,
    lane_c_score: int = 0,
    lane_e_score: int = 0,
    lane_v_score: int = 0,
    ev_snapshot: dict[str, Any] | None = None,
    stop_price: float = 0.0,
    entry_price: float = 0.0,
    tp1_price: float = 0.0,
) -> list[dict[str, Any]]:
    """Build list of alternative strategies considered this cycle.

    Each entry: {name, direction, score, normalized, selected, p_win, rr, profit_est}
    """
    alts: list[dict[str, Any]] = []

    # Long and short V4 scores
    if long_v4:
        l_score = int(long_v4.get("score") or 0)
        l_thresh = int(long_v4.get("threshold") or 75)
        alts.append({
            "name": str(long_v4.get("entry_type", "long_setup")).replace("_", " ").title(),
            "direction": "long",
            "raw_score": l_score,
            "threshold": l_thresh,
            "normalized": _normalize_v4_score(l_score, l_thresh),
            "selected": selected_direction == "long",
        })
    if short_v4:
        s_score = int(short_v4.get("score") or 0)
        s_thresh = int(short_v4.get("threshold") or 75)
        alts.append({
            "name": str(short_v4.get("entry_type", "short_setup")).replace("_", " ").title(),
            "direction": "short",
            "raw_score": s_score,
            "threshold": s_thresh,
            "normalized": _normalize_v4_score(s_score, s_thresh),
            "selected": selected_direction == "short",
        })

    # Lane scores
    if lane_c_score > 0:
        alts.append({"name": "Lane C (Compression)", "direction": "-", "raw_score": lane_c_score, "normalized": lane_c_score, "selected": False})
    if lane_e_score > 0:
        alts.append({"name": "Lane E (Expansion)", "direction": "-", "raw_score": lane_e_score, "normalized": lane_e_score, "selected": False})
    if lane_v_score > 0:
        alts.append({"name": "Lane V (Liquidity Sweep)", "direction": "-", "raw_score": lane_v_score, "normalized": lane_v_score, "selected": False})

    # Add EV-derived stats to selected
    p_win = float((ev_snapshot or {}).get("p_win", 0))
    rr = 0.0
    profit_est = 0.0
    if stop_price > 0 and entry_price > 0 and tp1_price > 0:
        risk_dist = abs(entry_price - stop_price)
        reward_dist = abs(tp1_price - entry_price)
        if risk_dist > 0:
            rr = round(reward_dist / risk_dist, 2)
        # Rough profit estimate: reward * p_win - risk * (1 - p_win)
        if p_win > 0:
            profit_est = round(reward_dist * p_win - risk_dist * (1 - p_win), 4)

    for alt in alts:
        if alt.get("selected"):
            alt["p_win"] = round(p_win, 2)
            alt["rr_ratio"] = rr
            alt["profit_est"] = profit_est

    # Sort by normalized score descending
    alts.sort(key=lambda x: x.get("normalized", 0), reverse=True)

    return alts

    return result
