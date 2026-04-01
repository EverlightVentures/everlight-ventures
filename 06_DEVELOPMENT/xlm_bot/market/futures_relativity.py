"""Cross-venue futures relativity scoring.

Coinbase product book remains the primary guide. This module only adds a
bounded secondary modifier from external venue crowding and OI context.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FuturesRelativityResult:
    bonus: int = 0
    reasons: list[str] = field(default_factory=list)


def score_futures_relativity(
    direction: str,
    futures_ctx: dict,
    orderbook_ctx: dict | None = None,
    contract_ctx: dict | None = None,
    config: dict | None = None,
) -> FuturesRelativityResult:
    cfg = config or {}
    bonus_max = max(1, int(cfg.get("bonus_max", 4) or 4))
    min_conf = float(cfg.get("min_confidence", 0.45) or 0.45)

    out = FuturesRelativityResult()
    if not direction or not isinstance(futures_ctx, dict):
        return out

    side = direction.lower().strip()
    composite = futures_ctx.get("composite") if isinstance(futures_ctx.get("composite"), dict) else {}
    bias = str(composite.get("bias") or "NEUTRAL").upper()
    confidence = float(composite.get("confidence") or 0.0)
    oi_trend = str(composite.get("oi_trend") or "FLAT").upper()
    funding_bias = str(composite.get("funding_bias") or "NEUTRAL").upper()
    depth_bias = str((orderbook_ctx or {}).get("depth_bias") or "UNKNOWN").upper()

    if confidence < min_conf:
        return out

    if bias == "BULLISH_SQUEEZE_RISK":
        if side == "long":
            out.bonus += 2
            out.reasons.append(f"cross_venue_bullish_squeeze conf={confidence:.2f}")
        else:
            out.bonus -= 2
            out.reasons.append(f"cross_venue_bullish_squeeze_against_short conf={confidence:.2f}")
    elif bias == "BEARISH_LONG_CROWDING":
        if side == "short":
            out.bonus += 2
            out.reasons.append(f"cross_venue_bearish_long_crowding conf={confidence:.2f}")
        else:
            out.bonus -= 2
            out.reasons.append(f"cross_venue_bearish_long_crowding_against_long conf={confidence:.2f}")
    elif bias == "SHORTS_COVERING":
        if side == "long":
            out.bonus += 1
            out.reasons.append(f"shorts_covering_support conf={confidence:.2f}")
    elif bias == "LONGS_DELEVERAGING":
        if side == "short":
            out.bonus += 1
            out.reasons.append(f"longs_deleveraging_support conf={confidence:.2f}")

    if oi_trend == "RISING" and funding_bias == "LONGS_PAY" and side == "long":
        out.bonus -= 1
        out.reasons.append("cross_venue_longs_crowded")
    elif oi_trend == "RISING" and funding_bias == "SHORTS_PAY" and side == "short":
        out.bonus -= 1
        out.reasons.append("cross_venue_shorts_crowded")

    if depth_bias == "BID_HEAVY" and side == "long" and bias in {"BULLISH_SQUEEZE_RISK", "SHORTS_COVERING"}:
        out.bonus += 1
        out.reasons.append("coinbase_book_confirms_bullish_relativity")
    elif depth_bias == "ASK_HEAVY" and side == "short" and bias in {"BEARISH_LONG_CROWDING", "LONGS_DELEVERAGING"}:
        out.bonus += 1
        out.reasons.append("coinbase_book_confirms_bearish_relativity")

    out.bonus = max(-bonus_max, min(bonus_max, out.bonus))
    return out
