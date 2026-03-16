"""Market Pulse Service -- composite market health scoring.

Fuses: (1) Perplexity market brief, (2) live tick data,
(3) Fear & Greed sentiment into a single 0-100 health score.
Writes data/market_pulse.json with TTL.
Bot reads pulse once per cycle; AI prompt consumes it.

Regime classification:
    DANGER   (<25)  -- block most entries
    RISK_OFF (25-40) -- reduce size
    NEUTRAL  (40-60) -- normal trading
    RISK_ON  (60+)   -- conditions favorable
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE = Path(__file__).parent.parent
_PULSE_PATH = _BASE / "data" / "market_pulse.json"
_LIVE_TICK_PATH = _BASE / "logs" / "live_tick.json"
_SENTIMENT_PATH = _BASE / "data" / "sentiment_cache.json"
_BRIEF_PATH = _BASE / "data" / "market_brief.json"
_CACHE_TTL = 300  # 5 minutes default
_PREV_REGIME: str | None = None
_SLACK_FN: Any = None


def init(config: dict | None = None) -> None:
    """Configure from config.yaml market_pulse section."""
    global _CACHE_TTL, _SLACK_FN
    mp_cfg = (config or {}).get("market_pulse") or {}
    _CACHE_TTL = int(mp_cfg.get("cache_ttl_sec", 300))
    # Try to import slack for regime change alerts
    try:
        from alerts import slack as _sl
        _SLACK_FN = _sl
    except Exception:
        _SLACK_FN = None


def _read_json(path: Path) -> dict:
    """Safe JSON read, returns empty dict on failure."""
    try:
        if path.exists():
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _cache_age_seconds(data: dict) -> float:
    """Compute age of a cache file from its timestamp fields."""
    ts = data.get("expires_ts") or data.get("_ts")
    if ts:
        try:
            if data.get("expires_ts"):
                # expires_ts is future; compute age as TTL - remaining
                remaining = float(ts) - time.time()
                return max(0, _CACHE_TTL - remaining)
            return time.time() - float(ts)
        except (ValueError, TypeError):
            pass
    return 9999.0


def _tick_age_seconds(tick: dict) -> float:
    """Compute age of live_tick.json from written_at field."""
    wa = tick.get("written_at")
    if wa:
        try:
            wt = datetime.fromisoformat(str(wa))
            if wt.tzinfo is None:
                wt = wt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - wt).total_seconds()
        except (ValueError, TypeError):
            pass
    return 9999.0


def compute_pulse() -> dict:
    """Compute composite market pulse from available data sources.

    Returns:
        health_score: int 0-100 (0=danger, 50=neutral, 100=pristine)
        components: dict with per-source details
        regime: str (danger/risk_off/neutral/risk_on)
        reasons: list[str]
        timestamp: str ISO
    """
    score = 50.0  # neutral baseline
    reasons: list[str] = []
    components: dict[str, Any] = {}

    # Component 1: Sentiment (F&G index) -- weight 40%
    sentiment = _read_json(_SENTIMENT_PATH)
    fg_score = int(sentiment.get("score", 50))
    fg_stale = (time.time() - float(sentiment.get("_ts", 0))) > 3600 if sentiment.get("_ts") else True
    components["sentiment_score"] = fg_score
    components["sentiment_class"] = sentiment.get("classification", "Unknown")
    components["sentiment_stale"] = fg_stale
    # Map 0-100 F&G to -20..+20 contribution
    sentiment_contrib = (fg_score - 50) * 0.4
    score += sentiment_contrib
    if fg_score < 20:
        reasons.append(f"extreme fear F&G={fg_score}")
    elif fg_score > 75:
        reasons.append(f"greed F&G={fg_score}")
    if fg_stale:
        score -= 5
        reasons.append("sentiment data stale")

    # Component 2: News risk modifier -- weight 30%
    brief_file = _read_json(_BRIEF_PATH)
    brief_data = brief_file.get("brief") or {}
    news_risk = brief_data.get("risk_modifier", "neutral")
    news_conf = float(brief_data.get("confidence", 0.5))
    components["news_risk"] = news_risk
    components["news_confidence"] = round(news_conf, 2)
    components["news_headlines"] = (brief_data.get("headline_bullets") or [])[:3]
    if news_risk == "risk_off":
        score -= 15 * news_conf
        reasons.append(f"news risk_off (conf {news_conf:.0%})")
    elif news_risk == "risk_on":
        score += 15 * news_conf
        reasons.append(f"news risk_on (conf {news_conf:.0%})")

    # Component 3: Live tick health -- weight 15%
    tick = _read_json(_LIVE_TICK_PATH)
    tick_age = _tick_age_seconds(tick)
    components["tick_age_sec"] = round(tick_age, 1)
    tick_price = float(tick.get("price") or 0)
    components["tick_price"] = tick_price
    if tick_age < 10:
        components["tick_health"] = "live"
        score += 5
    elif tick_age < 60:
        components["tick_health"] = "recent"
    elif tick_age < 300:
        components["tick_health"] = "stale"
        score -= 5
        reasons.append(f"live tick stale ({tick_age:.0f}s)")
    else:
        components["tick_health"] = "dead"
        score -= 10
        reasons.append(f"live tick dead ({tick_age:.0f}s)")

    # Component 4: Staleness penalty -- weight 15%
    brief_age = _cache_age_seconds(brief_file)
    components["brief_age_min"] = round(brief_age / 60, 1)
    if brief_age > 3600:  # > 1 hour
        score -= 10
        reasons.append(f"news brief stale ({brief_age / 60:.0f}min)")
    elif brief_age > 1800:  # > 30 min
        score -= 5

    # Clamp 0-100
    score = max(0, min(100, int(score)))

    # Regime classification
    if score < 25:
        regime = "danger"
    elif score < 40:
        regime = "risk_off"
    elif score < 60:
        regime = "neutral"
    else:
        regime = "risk_on"

    # Regime change alert
    global _PREV_REGIME
    if _PREV_REGIME is not None and regime != _PREV_REGIME and _SLACK_FN:
        try:
            _SLACK_FN.send(
                f"Market Pulse: {_PREV_REGIME} -> {regime} "
                f"(score: {score}/100). {'; '.join(reasons[:3])}",
                level="warning" if regime in ("danger", "risk_off") else "info",
            )
        except Exception:
            pass
    _PREV_REGIME = regime

    return {
        "health_score": score,
        "components": components,
        "regime": regime,
        "reasons": reasons,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _read_pulse_cache() -> dict | None:
    """Read pulse cache if fresh."""
    try:
        if _PULSE_PATH.exists():
            data = json.loads(_PULSE_PATH.read_text())
            if time.time() < float(data.get("expires_ts", 0)):
                return data.get("pulse")
    except Exception:
        pass
    return None


def _write_pulse_cache(pulse: dict) -> None:
    """Atomic cache write."""
    try:
        wrapper = {
            "pulse": pulse,
            "expires_ts": time.time() + _CACHE_TTL,
        }
        tmp = _PULSE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(wrapper, indent=2))
        tmp.replace(_PULSE_PATH)
    except Exception:
        pass


def get_pulse() -> dict | None:
    """Cached read: return pulse if fresh, else recompute."""
    cached = _read_pulse_cache()
    if cached:
        return cached

    pulse = compute_pulse()
    _write_pulse_cache(pulse)
    return pulse


def evaluate_pulse_gate(pulse: dict, config: dict) -> dict:
    """Optional hard gate: block entries if pulse health is catastrophic.

    Args:
        pulse: output from get_pulse()
        config: the market_pulse config section

    Returns:
        allowed: bool
        reason: str
        size_mult: float
    """
    result: dict[str, Any] = {
        "allowed": True,
        "reason": "pulse_ok",
        "size_mult": 1.0,
    }

    if not config.get("enabled", False):
        result["reason"] = "pulse_gate_disabled"
        return result

    health = int((pulse or {}).get("health_score", 50))
    regime = str((pulse or {}).get("regime", "neutral"))

    danger_threshold = int(config.get("danger_threshold", 20))
    danger_block = bool(config.get("danger_block_entries", False))
    risk_off_mult = float(config.get("risk_off_size_mult", 0.7))

    if health < danger_threshold and danger_block:
        result["allowed"] = False
        result["reason"] = f"pulse_danger_{health}"
        result["size_mult"] = 0.0
        return result

    if regime == "risk_off":
        result["size_mult"] = risk_off_mult
        result["reason"] = f"pulse_risk_off_{health}"
        return result

    return result
