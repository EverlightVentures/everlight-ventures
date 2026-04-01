"""Perplexity AI 'News & Catalyst Sentinel' advisor.

Provides situational awareness via rolling Market Briefs.
Never decides trades; only informs other agents.

Roles:
- Maintain rolling 'Market Brief' and 'XLM Catalyst Feed'
- Tag news by severity + timeframe
- Provide 'news risk modifier' (risk_on / risk_off / neutral)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Module state ────────────────────────────────────────────────────
_ENABLED: bool = True
_CACHE_PATH: Path = Path(__file__).parent.parent / "data" / "market_brief.json"
_WEEKLY_CACHE_PATH: Path = Path(__file__).parent.parent / "data" / "weekly_market_research.json"
_MARKET_INTEL_PATH: Path = Path(__file__).parent.parent / "data" / "market_intel_cache.json"
_ENV_FILE: Path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
_CLX_BIN: Path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py")
_API_KEY: str | None = None
_CACHE_TTL: int = 900  # 15 minutes
_WEEKLY_CACHE_TTL: int = 21600  # 6 hours

# Realtime signal cache paths (written by market intel modules)
_SENTIMENT_SHIFT_PATH: Path = Path(__file__).parent.parent / "data" / "sentiment_shift.json"
_ONCHAIN_ALERTS_PATH: Path = Path(__file__).parent.parent / "data" / "onchain_alerts.json"
_CORRELATION_DRIFT_PATH: Path = Path(__file__).parent.parent / "data" / "correlation_drift.json"

def init(config: dict | None = None) -> None:
    """Initialize Perplexity advisor."""
    global _API_KEY, _ENABLED
    ai_cfg = (config or {}).get("ai") or {}
    perp_cfg = ai_cfg.get("perplexity") or {}
    
    if not perp_cfg.get("enabled", True):
        _ENABLED = False
        return

    # Try to load API key from env file or environment
    if _ENV_FILE.exists():
        try:
            for line in _ENV_FILE.read_text().splitlines():
                if line.startswith("PERPLEXITY_API_KEY="):
                    _API_KEY = line.split("=", 1)[1].strip()
        except Exception:
            pass
    
    if not _API_KEY:
        _API_KEY = os.environ.get("PERPLEXITY_API_KEY")

    # Fallback: if no key, we can use Claude's WebSearch capability as a proxy "Perplexity"
    # so we don't disable the module, just the direct API mode.
    pass

def is_enabled() -> bool:
    return _ENABLED

def _read_cache() -> dict | None:
    try:
        if _CACHE_PATH.exists():
            data = json.loads(_CACHE_PATH.read_text())
            if time.time() < data.get("expires_ts", 0):
                return data.get("brief")
    except Exception:
        pass
    return None

def _write_cache(brief: dict) -> None:
    try:
        data = {
            "brief": brief,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_ts": time.time() + _CACHE_TTL
        }
        # Atomic write
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(_CACHE_PATH)
    except Exception:
        pass


def _read_weekly_cache() -> dict | None:
    try:
        if _WEEKLY_CACHE_PATH.exists():
            data = json.loads(_WEEKLY_CACHE_PATH.read_text())
            if time.time() < data.get("expires_ts", 0):
                return data.get("research")
    except Exception:
        pass
    return None


def _write_weekly_cache(research: dict, ttl_sec: int) -> None:
    try:
        data = {
            "research": research,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_ts": time.time() + max(900, int(ttl_sec or _WEEKLY_CACHE_TTL)),
        }
        tmp = _WEEKLY_CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(_WEEKLY_CACHE_PATH)
    except Exception:
        pass


def _read_market_intel_cache() -> dict[str, Any] | None:
    try:
        if _MARKET_INTEL_PATH.exists():
            data = json.loads(_MARKET_INTEL_PATH.read_text())
            payload = data.get("payload")
            return payload if isinstance(payload, dict) else None
    except Exception:
        pass
    return None


def _risk_modifier_from_market_intel(payload: dict[str, Any]) -> str:
    prices = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    macro = payload.get("macro") if isinstance(payload.get("macro"), dict) else {}
    xlm_move = float(prices.get("xlm_24h_pct") or 0.0)
    btc_move = float(prices.get("btc_24h_pct") or 0.0)
    spx_move = float(((macro.get("spx") or {}).get("move_pct")) or 0.0)
    ndx_move = float(((macro.get("ndx") or {}).get("move_pct")) or 0.0)
    if xlm_move <= -3 or btc_move <= -2 or (spx_move < -1 and ndx_move < -1):
        return "risk_off"
    if xlm_move >= 3 and btc_move >= 1 and (spx_move >= 0 or ndx_move >= 0):
        return "risk_on"
    return "neutral"


def _read_realtime_signals() -> dict[str, Any]:
    """Read all 3 realtime intel JSON caches and synthesize hot_signals.

    Gracefully returns empty signals if modules haven't run yet.
    """
    hot_signals: list[dict[str, Any]] = []
    sentiment: dict[str, Any] = {}
    onchain: dict[str, Any] = {}
    correlation: dict[str, Any] = {}

    # Read sentiment shift
    try:
        if _SENTIMENT_SHIFT_PATH.exists():
            sentiment = json.loads(_SENTIMENT_SHIFT_PATH.read_text()) or {}
            score = sentiment.get("score")
            direction = sentiment.get("direction")
            if isinstance(score, (int, float)) and direction:
                if score >= 70 or score <= 30:
                    hot_signals.append({
                        "source": "sentiment_monitor",
                        "signal": f"sentiment_{direction}_{score:.0f}",
                        "severity": "high" if (score >= 80 or score <= 20) else "medium",
                        "detail": f"Social sentiment {direction} ({score:.0f}/100)",
                    })
                topics = sentiment.get("hot_topics", [])
                if topics:
                    hot_signals.append({
                        "source": "sentiment_monitor",
                        "signal": "hot_topics",
                        "severity": "info",
                        "detail": "; ".join(str(t)[:80] for t in topics[:3]),
                    })
    except Exception:
        pass

    # Read on-chain alerts
    try:
        if _ONCHAIN_ALERTS_PATH.exists():
            onchain = json.loads(_ONCHAIN_ALERTS_PATH.read_text()) or {}
            whale_level = onchain.get("whale_alert_level", "none")
            if whale_level in ("warning", "critical"):
                hot_signals.append({
                    "source": "onchain_intelligence",
                    "signal": f"whale_alert_{whale_level}",
                    "severity": "high" if whale_level == "critical" else "medium",
                    "detail": f"Whale activity: {whale_level}",
                })
            if onchain.get("exchange_volume_spike"):
                hot_signals.append({
                    "source": "onchain_intelligence",
                    "signal": "exchange_volume_spike",
                    "severity": "medium",
                    "detail": "Exchange volume spike detected",
                })
            for sig in (onchain.get("signals") or [])[:3]:
                if isinstance(sig, dict) and sig.get("severity") in ("high", "medium"):
                    hot_signals.append({
                        "source": "onchain_intelligence",
                        "signal": str(sig.get("signal", "")),
                        "severity": str(sig.get("severity", "medium")),
                        "detail": str(sig.get("detail", "")),
                    })
    except Exception:
        pass

    # Read correlation drift
    try:
        if _CORRELATION_DRIFT_PATH.exists():
            correlation = json.loads(_CORRELATION_DRIFT_PATH.read_text()) or {}
            corr_trend = correlation.get("correlation_trend")
            divergence = correlation.get("divergence_flag")
            corr_val = correlation.get("btc_xlm_correlation_24h")
            if divergence:
                hot_signals.append({
                    "source": "correlation_drift",
                    "signal": "btc_xlm_divergence",
                    "severity": "high",
                    "detail": f"BTC/XLM divergence detected (corr={corr_val})",
                })
            elif corr_trend == "decoupling":
                hot_signals.append({
                    "source": "correlation_drift",
                    "signal": "btc_xlm_decoupling",
                    "severity": "medium",
                    "detail": f"BTC/XLM correlation declining (corr={corr_val})",
                })
            rel_strength = correlation.get("xlm_relative_strength")
            if rel_strength in ("leading", "lagging"):
                hot_signals.append({
                    "source": "correlation_drift",
                    "signal": f"xlm_{rel_strength}_btc",
                    "severity": "low",
                    "detail": f"XLM is {rel_strength} BTC (BTC {correlation.get('btc_24h_change', '?')}% vs XLM {correlation.get('xlm_24h_change', '?')}%)",
                })
    except Exception:
        pass

    # Deduplicate by signal name
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for s in hot_signals:
        key = str(s.get("signal", ""))
        if key and key not in seen:
            seen.add(key)
            deduped.append(s)

    return {
        "hot_signals": deduped[:10],
        "sentiment_snapshot": {
            "score": sentiment.get("score"),
            "direction": sentiment.get("direction"),
        } if sentiment.get("score") is not None else None,
        "onchain_snapshot": {
            "network_health": onchain.get("network_health"),
            "whale_alert_level": onchain.get("whale_alert_level"),
        } if onchain.get("network_health") else None,
        "correlation_snapshot": {
            "correlation_24h": correlation.get("btc_xlm_correlation_24h"),
            "trend": correlation.get("correlation_trend"),
            "divergence": correlation.get("divergence_flag"),
        } if correlation.get("btc_xlm_correlation_24h") is not None else None,
    }


def _normalize_brief_schema(brief: dict[str, Any]) -> dict[str, Any]:
    out = dict(brief or {})
    headline_bullets = out.get("headline_bullets")
    xlm_specific = out.get("xlm_specific")
    out["macro_bullets"] = list(out.get("macro_bullets") or headline_bullets or [])
    out["xlm_catalysts"] = list(out.get("xlm_catalysts") or xlm_specific or [])
    out["horizon"] = out.get("horizon") or out.get("time_horizon") or "24h"
    out["time_horizon"] = out.get("time_horizon") or out["horizon"]
    out["headline_bullets"] = list(headline_bullets or out["macro_bullets"])
    out["xlm_specific"] = list(xlm_specific or out["xlm_catalysts"])
    out["risk_modifier"] = out.get("risk_modifier") or "neutral"
    # Realtime signal fields (additive, never break existing consumers)
    if "hot_signals" not in out:
        out["hot_signals"] = []
    if "realtime_intel" not in out:
        out["realtime_intel"] = {}
    return out


def _normalize_weekly_schema(research: dict[str, Any]) -> dict[str, Any]:
    out = dict(research or {})
    out["week_of"] = str(out.get("week_of") or datetime.now(timezone.utc).date().isoformat())
    out["macro_regime"] = str(out.get("macro_regime") or out.get("risk_modifier") or "neutral")
    out["directional_bias"] = str(out.get("directional_bias") or "mixed")
    out["xlm_bias"] = str(out.get("xlm_bias") or out.get("directional_bias") or "mixed")
    out["confidence"] = float(out.get("confidence") or 0.45)
    out["key_themes"] = list(out.get("key_themes") or out.get("macro_bullets") or [])
    out["crypto_sentiment"] = list(out.get("crypto_sentiment") or [])
    out["xlm_catalysts"] = list(out.get("xlm_catalysts") or out.get("xlm_specific") or [])
    out["risks"] = list(out.get("risks") or [])
    out["trade_playbook"] = list(out.get("trade_playbook") or [])
    out["watch_items"] = list(out.get("watch_items") or [])
    out["sources"] = list(out.get("sources") or [])
    out["window_label"] = str(out.get("window_label") or "OUTSIDE_WEEKLY_WINDOW")
    out["generated_from"] = str(out.get("generated_from") or "unknown")
    out["updated_at"] = str(out.get("updated_at") or datetime.now(timezone.utc).isoformat())
    return out


def _synthesize_brief_from_market_intel(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    prices = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    macro = payload.get("macro") if isinstance(payload.get("macro"), dict) else {}
    relativity = payload.get("futures_relativity") if isinstance(payload.get("futures_relativity"), dict) else {}
    composite = relativity.get("composite") if isinstance(relativity.get("composite"), dict) else {}
    headlines = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []

    macro_bullets: list[str] = []
    xlm_catalysts: list[str] = []

    xlm_price = prices.get("xlm_usd")
    xlm_24h = prices.get("xlm_24h_pct")
    btc_price = prices.get("btc_usd")
    btc_24h = prices.get("btc_24h_pct")
    if xlm_price is not None and xlm_24h is not None:
        macro_bullets.append(f"Research snapshot had XLM around ${float(xlm_price):.6f}, {float(xlm_24h):+.2f}% over 24h.")
    if btc_price is not None and btc_24h is not None:
        macro_bullets.append(f"Research snapshot had BTC around ${float(btc_price):,.0f}, {float(btc_24h):+.2f}% over 24h.")
    spx_move = ((macro.get("spx") or {}).get("move_pct")) if isinstance(macro.get("spx"), dict) else None
    ndx_move = ((macro.get("ndx") or {}).get("move_pct")) if isinstance(macro.get("ndx"), dict) else None
    if spx_move is not None or ndx_move is not None:
        macro_bullets.append(
            f"Macro tape: S&P 500 {float(spx_move or 0.0):+.2f}%, Nasdaq {float(ndx_move or 0.0):+.2f}%."
        )

    bias = str(composite.get("bias") or "NEUTRAL").upper()
    confidence = float(composite.get("confidence") or 0.0)
    oi_change = composite.get("oi_change_pct_avg")
    xlm_catalysts.append(
        f"Cross-venue futures relativity is {bias.lower()} with confidence {confidence:.2f}"
        + (f"; average OI change {float(oi_change):+.3f}%." if oi_change is not None else ".")
    )
    for item in headlines[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        topic = str(item.get("topic") or "").strip()
        if title:
            target = xlm_catalysts if topic in {"xlm", "stellar"} else macro_bullets
            target.append(title)

    brief = {
        "headline_bullets": macro_bullets[:5],
        "xlm_specific": xlm_catalysts[:5],
        "risk_modifier": _risk_modifier_from_market_intel(payload),
        "time_horizon": "24h",
        "confidence": max(0.35, confidence if confidence > 0 else 0.45),
    }
    return _normalize_brief_schema(brief)


def _weekly_window_state(now_utc: datetime | None = None, config: dict | None = None) -> dict[str, Any]:
    now_utc = now_utc or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo

        now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        now_et = now_utc.astimezone(timezone(timedelta(hours=-5), name="ET"))

    market_cfg = (config or {}).get("market_intel") or {}
    weekly_cfg = (market_cfg.get("weekly_research") or {}) if isinstance(market_cfg, dict) else {}
    sunday_start = int(weekly_cfg.get("sunday_start_hour_et", 18) or 18)
    monday_end = int(weekly_cfg.get("monday_end_hour_et", 10) or 10)
    hourly_refresh = int(weekly_cfg.get("refresh_hours", 6) or 6)
    window_refresh = int(weekly_cfg.get("window_refresh_hours", 2) or 2)

    label = "OUTSIDE_WEEKLY_WINDOW"
    in_window = False
    if now_et.weekday() == 6 and now_et.hour >= sunday_start:
        label = "SUNDAY_RESEARCH"
        in_window = True
    elif now_et.weekday() == 0 and now_et.hour < monday_end:
        label = "MONDAY_OPENING_BIAS"
        in_window = True

    return {
        "label": label,
        "in_window": in_window,
        "refresh_hours": window_refresh if in_window else hourly_refresh,
        "now_et": now_et.isoformat(),
    }


def _synthesize_weekly_from_market_intel(payload: dict[str, Any], *, window_label: str = "OUTSIDE_WEEKLY_WINDOW") -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    brief = _synthesize_brief_from_market_intel(payload) or {}
    prices = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    relativity = payload.get("futures_relativity") if isinstance(payload.get("futures_relativity"), dict) else {}
    composite = relativity.get("composite") if isinstance(relativity.get("composite"), dict) else {}
    headlines = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []

    macro_regime = str(brief.get("risk_modifier") or "neutral")
    directional_bias = str(composite.get("bias") or "mixed").lower()
    if directional_bias not in {"bullish", "bearish", "mixed"}:
        directional_bias = "mixed"
    xlm_bias = "bullish" if float(prices.get("xlm_24h_pct") or 0.0) > 1.0 else "bearish" if float(prices.get("xlm_24h_pct") or 0.0) < -1.0 else directional_bias

    risks = []
    if macro_regime == "risk_off":
        risks.append("Macro backdrop is defensive (risk_off). Expect weaker upside follow-through and sharper forced-stop flushes (liquidation hunts).")
    if str(composite.get("funding_bias") or "").lower() == "shorts_paying_longs":
        risks.append("Too many traders are leaning short. Fast upside squeezes can overshoot.")
    if not risks:
        risks.append("No strong weekly warning from cached research. Let the live chart and structure lead, not the story.")

    trade_playbook = [
        "Use the bigger-picture lean (weekly bias) as background context, not as a reason to jump in by itself.",
        "Best entries are simple follow-through moves after a clean bounce or break (continuation setups), especially when the session plan agrees.",
        "If big buyers or sellers are clearly soaking up orders (order-book absorption) or price makes a forced-stop flush (liquidation sweep), trust that over the weekly story.",
    ]
    if macro_regime == "risk_off":
        trade_playbook.append("Take profits faster and keep long size smaller until that defensive pressure eases.")

    watch_items = []
    for item in headlines[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title:
            watch_items.append(title)

    research = {
        "week_of": datetime.now(timezone.utc).date().isoformat(),
        "macro_regime": macro_regime,
        "directional_bias": directional_bias,
        "xlm_bias": xlm_bias,
        "confidence": max(0.4, float(composite.get("confidence") or brief.get("confidence") or 0.45)),
        "key_themes": list(brief.get("headline_bullets") or [])[:5],
        "crypto_sentiment": [
            f"Cross-venue futures bias: {str(composite.get('bias') or 'mixed').lower()}",
            f"Funding bias: {str(composite.get('funding_bias') or 'neutral').lower()}",
        ],
        "xlm_catalysts": list(brief.get("xlm_specific") or [])[:5],
        "risks": risks[:4],
        "trade_playbook": trade_playbook[:4],
        "watch_items": watch_items[:6],
        "sources": ["market_intel_cache"],
        "window_label": window_label,
        "generated_from": "market_intel_fallback",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return _normalize_weekly_schema(research)


def _weekly_research_needs_retry(research: dict[str, Any] | None, *, window: dict[str, Any]) -> bool:
    if not isinstance(research, dict):
        return True
    generated_from = str(research.get("generated_from") or "unknown")
    confidence = float(research.get("confidence") or 0.0)
    source_count = len(list(research.get("sources") or []))
    if generated_from in {"market_intel_fallback", "unknown"}:
        return True
    if bool(window.get("in_window")) and (confidence < 0.6 or source_count < 3):
        return True
    return False


def _fetch_weekly_via_websearch(prompt: str) -> dict[str, Any] | None:
    try:
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CODE", None)
        cmd = [
            sys.executable,
            str(_CLX_BIN),
            "--raw",
            "--mode",
            "execute",
            "--output-format",
            "text",
            "--model",
            "haiku",
            "--allowed-tool",
            "WebSearch",
            prompt,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=50, env=env)
        if result.returncode == 0:
            parsed = _parse_json(result.stdout)
            if isinstance(parsed, dict):
                parsed["generated_from"] = "websearch_proxy"
            return parsed
    except Exception:
        return None
    return None

def fetch_market_brief(force: bool = False) -> dict | None:
    """Fetch structured Market Brief.
    
    Schema:
    - headline_bullets (list[str])
    - xlm_specific (list[str])
    - risk_modifier (risk_on | neutral | risk_off)
    - time_horizon (immediate | 24h | 7d)
    - confidence (float)
    """
    if not _ENABLED:
        return None
        
    cached = _read_cache()
    if cached and not force:
        return cached

    # Prompt designed for Perplexity (or Claude WebSearch proxy)
    prompt = (
        "Generate a structured 'Market Brief' for an XLM crypto trading bot.\\n"
        "Search for: Bitcoin price/sentiment, S&P 500/Nasdaq moves, Fed/Macro news today, "
        "and specific Stellar (XLM) news/catalysts.\\n\\n"
        "Respond ONLY with valid JSON:\\n"
        "{\\n"
        '  "headline_bullets": ["3-5 key macro/crypto points"],\\n'
        '  "xlm_specific": ["Specific XLM news or correlation notes"],\\n'
        '  "risk_modifier": "risk_on" or "neutral" or "risk_off",\\n'
        '  "time_horizon": "immediate" or "24h" or "7d" (dominant catalyst impact),\\n'
        '  "confidence": 0.0 to 1.0\\n'
        "}"
    )

    brief = None
    
    # Method A: Direct Perplexity API
    if _API_KEY:
        try:
            import requests
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "Market Intelligence Officer. JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                },
                timeout=20
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                brief = _parse_json(raw)
        except Exception:
            pass

    # Method B: Claude WebSearch Proxy (Fallback)
    if not brief:
        try:
            env = os.environ.copy()
            # Clean env for Claude CLI
            env.pop("CLAUDECODE", None)
            env.pop("CLAUDE_CODE", None)
            
            cmd = [
                sys.executable,
                str(_CLX_BIN),
                "--raw",
                "--mode",
                "execute",
                "--output-format",
                "text",
                "--model",
                "haiku",
                "--allowed-tool",
                "WebSearch",
                prompt,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=45, env=env
            )
            if result.returncode == 0:
                brief = _parse_json(result.stdout)
        except Exception:
            pass

    # Method C: local deterministic fallback from existing market intel cache
    if not brief:
        brief = _synthesize_brief_from_market_intel(_read_market_intel_cache() or {})

    if brief:
        normalized = _normalize_brief_schema(brief)
        # Enrich with realtime signals from market intel modules
        try:
            rt = _read_realtime_signals()
            if rt.get("hot_signals"):
                normalized["hot_signals"] = rt["hot_signals"]
            rt_intel = {}
            if rt.get("sentiment_snapshot"):
                rt_intel["sentiment"] = rt["sentiment_snapshot"]
            if rt.get("onchain_snapshot"):
                rt_intel["onchain"] = rt["onchain_snapshot"]
            if rt.get("correlation_snapshot"):
                rt_intel["correlation"] = rt["correlation_snapshot"]
            if rt_intel:
                normalized["realtime_intel"] = rt_intel
        except Exception:
            pass  # Never let realtime signal failure break the brief
        _write_cache(normalized)
        return normalized

    return brief


def fetch_weekly_market_research(force: bool = False, config: dict | None = None) -> dict | None:
    if not _ENABLED:
        return None

    window = _weekly_window_state(config=config)
    cached = _read_weekly_cache()
    if cached and not force:
        return _normalize_weekly_schema(cached)

    prompt = (
        "Generate a structured weekly market research brief for an XLM perpetual futures trading bot. "
        "Research macro markets, finance, crypto sentiment, XLM-specific catalysts, and crowd psychology for the coming week. "
        "Focus on what matters for next-session directional bias, liquidation behavior, and risk management. "
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "macro_regime": "risk_on" or "neutral" or "risk_off",\n'
        '  "directional_bias": "bullish" or "bearish" or "mixed",\n'
        '  "xlm_bias": "bullish" or "bearish" or "mixed",\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "key_themes": ["3-6 macro and crypto themes"],\n'
        '  "crypto_sentiment": ["market psychology and crowd positioning notes"],\n'
        '  "xlm_catalysts": ["XLM-specific catalysts or risks"],\n'
        '  "risks": ["key downside risks"],\n'
        '  "trade_playbook": ["how the bot should adapt this week"],\n'
        '  "watch_items": ["tickers, events, or topics to watch"],\n'
        '  "sources": ["public web or research sources used"]\n'
        "}"
    )

    research = None
    ttl_sec = int(window.get("refresh_hours", 6) or 6) * 3600

    if _API_KEY:
        try:
            import requests

            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "Weekly market strategist. JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=25,
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"]
                research = _parse_json(raw)
                if isinstance(research, dict):
                    research["generated_from"] = "perplexity_api"
        except Exception:
            pass

    if not research:
        research = _fetch_weekly_via_websearch(prompt)

    if not research:
        research = _synthesize_weekly_from_market_intel(
            _read_market_intel_cache() or {},
            window_label=str(window.get("label") or "OUTSIDE_WEEKLY_WINDOW"),
        )

    if _weekly_research_needs_retry(research, window=window):
        retried = _fetch_weekly_via_websearch(
            prompt
            + "\n\nRequire at least 3 named sources if possible, include the coming week's most relevant macro and XLM catalysts, "
              "and keep the response trade-oriented."
        )
        if retried:
            research = retried

    if research:
        research["window_label"] = str(window.get("label") or research.get("window_label") or "OUTSIDE_WEEKLY_WINDOW")
        research["updated_at"] = datetime.now(timezone.utc).isoformat()
        normalized = _normalize_weekly_schema(research)
        _write_weekly_cache(normalized, ttl_sec=ttl_sec)
        return normalized
    return None

def _parse_json(raw: str) -> dict | None:
    try:
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end+1])
    except Exception:
        pass
    return None

def get_latest_brief() -> dict | None:
    """Non-blocking read of latest brief."""
    brief = _read_cache()
    if brief:
        return _normalize_brief_schema(brief)
    fallback = _synthesize_brief_from_market_intel(_read_market_intel_cache() or {})
    if fallback:
        _write_cache(fallback)
    return fallback


def get_latest_weekly_market_research(config: dict | None = None) -> dict | None:
    research = _read_weekly_cache()
    if research:
        return _normalize_weekly_schema(research)
    fallback = _synthesize_weekly_from_market_intel(
        _read_market_intel_cache() or {},
        window_label=_weekly_window_state(config=config).get("label", "OUTSIDE_WEEKLY_WINDOW"),
    )
    if fallback:
        _write_weekly_cache(fallback, ttl_sec=int(_weekly_window_state(config=config).get("refresh_hours", 6) or 6) * 3600)
    return fallback
