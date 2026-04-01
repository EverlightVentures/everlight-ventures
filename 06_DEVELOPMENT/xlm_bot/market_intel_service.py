from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
import xml.etree.ElementTree as ET


def refresh_market_intel_state(
    *,
    config: dict | None,
    data_dir: Path,
    logs_dir: Path,
    market_intel: dict[str, Any] | None = None,
    market_brief: dict[str, Any] | None = None,
    weekly_research: dict[str, Any] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now = now_utc or datetime.now(timezone.utc)
    data_dir = Path(data_dir)
    logs_dir = Path(logs_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    market_intel = market_intel or _read_cached_payload(data_dir / "market_intel_cache.json", "payload")
    market_brief = market_brief or _read_cached_payload(data_dir / "market_brief.json", "brief")
    weekly_research = weekly_research or _read_cached_payload(data_dir / "weekly_market_research.json", "research")

    intraday = _build_intraday_state(market_intel, market_brief, now)
    weekly = _build_weekly_state(weekly_research, market_intel, now)
    event_calendar = _build_event_calendar(weekly_research, market_intel, now, data_dir=data_dir)
    source_scoreboard = _build_source_scoreboard(
        list(intraday.get("documents") or []) + list(weekly.get("documents") or []),
        now=now,
    )
    crowding_summary = _build_crowding_summary(market_intel, now=now)
    weekly_playbook = _build_weekly_playbook(
        intraday=intraday,
        weekly=weekly,
        event_calendar=event_calendar,
        source_scoreboard=source_scoreboard,
        crowding_summary=crowding_summary,
        now=now,
    )
    state = {
        "generated_at": now.isoformat(),
        "intraday": intraday,
        "weekly": weekly,
        "event_calendar": event_calendar,
        "source_scoreboard": source_scoreboard,
        "crowding_summary": crowding_summary,
        "weekly_playbook": weekly_playbook,
    }
    _write_json(data_dir / "market_intel_state.json", state)
    _write_json(data_dir / "market_event_calendar.json", event_calendar)
    _write_json(data_dir / "source_scoreboard.json", source_scoreboard)
    _write_json(data_dir / "crowding_summary.json", crowding_summary)
    _write_json(data_dir / "weekly_playbook.json", weekly_playbook)

    _emit_research_run(
        research_kind="intraday",
        state=intraday,
        logs_dir=logs_dir,
        data_dir=data_dir,
        generated_at=now,
    )
    _emit_research_run(
        research_kind="weekly",
        state=weekly,
        logs_dir=logs_dir,
        data_dir=data_dir,
        generated_at=now,
    )
    return state


def _build_intraday_state(
    market_intel: dict[str, Any] | None,
    market_brief: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    market_intel = market_intel if isinstance(market_intel, dict) else {}
    market_brief = market_brief if isinstance(market_brief, dict) else {}

    documents = _documents_from_market_intel(market_intel, research_kind="intraday", now=now)
    xlm_move = _flt(((market_intel.get("prices") or {}).get("xlm_24h_pct")))
    bias = "mixed"
    if xlm_move is not None:
        if xlm_move >= 1.0:
            bias = "bullish"
        elif xlm_move <= -1.0:
            bias = "bearish"

    macro_regime = str(market_brief.get("risk_modifier") or "neutral").lower()
    confidence = _review_confidence(
        base=float(market_brief.get("confidence") or 0.45),
        documents=documents,
        generated_at=market_intel.get("fetched_at"),
        now=now,
    )
    claims = _intraday_claims(market_intel, market_brief, confidence)
    review = _review_state(documents, claims, generated_at=market_intel.get("fetched_at"), now=now)

    return {
        "research_kind": "intraday",
        "generated_at": now.isoformat(),
        "source_mode": _source_mode(market_brief),
        "summary": str(market_intel.get("summary") or ""),
        "macro_regime": macro_regime,
        "directional_bias": bias,
        "xlm_bias": bias,
        "confidence": confidence,
        "review_score": review["score"],
        "review_notes": review["notes"],
        "risk_flags": list(market_intel.get("risk_flags") or []),
        "documents": documents,
        "claims": claims,
        "payload": {
            "market_brief": market_brief,
            "market_intel": market_intel,
        },
    }


def _build_weekly_state(
    weekly_research: dict[str, Any] | None,
    market_intel: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    weekly_research = weekly_research if isinstance(weekly_research, dict) else {}
    market_intel = market_intel if isinstance(market_intel, dict) else {}

    documents = _documents_from_weekly_research(weekly_research, now=now)
    documents.extend(_documents_from_market_intel(market_intel, research_kind="weekly_support", now=now)[:4])
    confidence = _review_confidence(
        base=float(weekly_research.get("confidence") or 0.4),
        documents=documents,
        generated_at=weekly_research.get("updated_at"),
        now=now,
    )
    claims = _weekly_claims(weekly_research, confidence)
    review = _review_state(documents, claims, generated_at=weekly_research.get("updated_at"), now=now)

    return {
        "research_kind": "weekly",
        "generated_at": now.isoformat(),
        "source_mode": str(weekly_research.get("generated_from") or "fallback"),
        "summary": " | ".join(str(x) for x in (weekly_research.get("key_themes") or [])[:3]),
        "macro_regime": str(weekly_research.get("macro_regime") or "neutral").lower(),
        "directional_bias": str(weekly_research.get("directional_bias") or "mixed").lower(),
        "xlm_bias": str(weekly_research.get("xlm_bias") or "mixed").lower(),
        "confidence": confidence,
        "review_score": review["score"],
        "review_notes": review["notes"],
        "window_label": str(weekly_research.get("window_label") or "OUTSIDE_WEEKLY_WINDOW"),
        "documents": documents,
        "claims": claims,
        "payload": {
            "weekly_research": weekly_research,
            "market_intel": market_intel,
        },
    }


def get_latest_market_intel_state(data_dir: Path | None = None) -> dict[str, Any]:
    base = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    return _read_json(base / "market_intel_state.json")


def get_latest_weekly_playbook(data_dir: Path | None = None) -> dict[str, Any]:
    base = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    return _read_json(base / "weekly_playbook.json")


def get_latest_event_calendar(data_dir: Path | None = None) -> dict[str, Any]:
    base = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    return _read_json(base / "market_event_calendar.json")


def get_latest_source_scoreboard(data_dir: Path | None = None) -> dict[str, Any]:
    base = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    return _read_json(base / "source_scoreboard.json")


def get_latest_crowding_summary(data_dir: Path | None = None) -> dict[str, Any]:
    base = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    return _read_json(base / "crowding_summary.json")


def _build_event_calendar(
    weekly_research: dict[str, Any],
    market_intel: dict[str, Any],
    now: datetime,
    *,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    weekly_research = weekly_research if isinstance(weekly_research, dict) else {}
    market_intel = market_intel if isinstance(market_intel, dict) else {}
    events: list[dict[str, Any]] = []

    for raw in (weekly_research.get("event_calendar") or [])[:12]:
        if isinstance(raw, dict):
            label = str(raw.get("label") or raw.get("title") or raw.get("name") or "").strip()
            if not label:
                continue
            ts = _event_timestamp(raw.get("timestamp") or raw.get("at") or raw.get("time"), now)
            importance = str(raw.get("importance") or raw.get("severity") or "medium").lower()
            bias = str(raw.get("bias") or raw.get("risk_bias") or "two_way").lower()
            events.append(
                _event_row(
                    label=label,
                    timestamp=ts,
                    category=str(raw.get("category") or "macro").lower(),
                    importance=importance,
                    bias=bias,
                    detail=str(raw.get("detail") or raw.get("notes") or ""),
                    source="weekly_research",
                    now=now,
                )
            )
        elif isinstance(raw, str) and raw.strip():
            events.append(
                _event_row(
                    label=raw.strip(),
                    timestamp=None,
                    category="watchlist",
                    importance="medium",
                    bias="two_way",
                    detail="Derived from weekly research event watchlist.",
                    source="weekly_research",
                    now=now,
                )
            )

    for raw in list(weekly_research.get("watch_items") or [])[:6]:
        label = str(raw).strip()
        if not label:
            continue
        _maybe_add_keyword_event(events, label, now, source="watch_items")

    for raw in list(weekly_research.get("risks") or [])[:6]:
        label = str(raw).strip()
        if not label:
            continue
        _maybe_add_keyword_event(events, label, now, source="risks")

    _append_scheduled_events(events, now)
    for direct_event in _fetch_direct_event_feed(now, data_dir=data_dir):
        events.append(direct_event)

    risk_flags = market_intel.get("risk_flags") if isinstance(market_intel.get("risk_flags"), list) else []
    for raw in risk_flags[:4]:
        label = str(raw).strip()
        if label:
            _maybe_add_keyword_event(events, label, now, source="market_intel")

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in sorted(events, key=lambda item: (_event_sort_key(item, now), item.get("label") or "")):
        key = str(event.get("event_id") or event.get("label") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(event)

    upcoming = [item for item in deduped if not item.get("expired")]
    next_event = upcoming[0] if upcoming else {}
    high_risk = [item for item in upcoming if item.get("importance") == "high"]
    return {
        "generated_at": now.isoformat(),
        "events": deduped[:12],
        "next_event": next_event,
        "high_risk_count": len(high_risk),
        "event_count": len(deduped[:12]),
    }


def _fetch_direct_event_feed(now: datetime, *, data_dir: Path | None = None) -> list[dict[str, Any]]:
    cache_path = (Path(data_dir) if data_dir else Path(__file__).parent / "data") / "market_event_feed.json"
    cached = _read_json(cache_path)
    cached_ts = _coerce_dt(cached.get("generated_at"))
    if cached_ts and (now - cached_ts).total_seconds() <= 6 * 3600:
        events = cached.get("events")
        return events if isinstance(events, list) else []

    events: list[dict[str, Any]] = []
    try:
        with urlopen("https://www.federalreserve.gov/feeds/press_monetary.xml", timeout=12) as resp:
            xml_text = resp.read()
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item")[:4]:
            title = (item.findtext("title") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if not title:
                continue
            ts = None
            try:
                from email.utils import parsedate_to_datetime

                ts = parsedate_to_datetime(pub_date).astimezone(timezone.utc) if pub_date else None
            except Exception:
                ts = None
            events.append(
                _event_row(
                    label=f"Fed RSS: {title}",
                    timestamp=ts,
                    category="macro",
                    importance="high",
                    bias="two_way",
                    detail="Direct Federal Reserve monetary-policy feed item.",
                    source="fed_rss",
                    now=now,
                )
            )
    except (URLError, TimeoutError, ET.ParseError, OSError):
        pass

    payload = {"generated_at": now.isoformat(), "events": events}
    try:
        _write_json(cache_path, payload)
    except Exception:
        pass
    return events


def _build_source_scoreboard(documents: list[dict[str, Any]], *, now: datetime) -> dict[str, Any]:
    board: dict[str, dict[str, Any]] = {}
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        name = str(doc.get("source_name") or "unknown").strip() or "unknown"
        row = board.setdefault(
            name,
            {
                "source_name": name,
                "documents": 0,
                "quality_sum": 0.0,
                "fresh_docs": 0,
                "topics": set(),
            },
        )
        row["documents"] += 1
        row["quality_sum"] += float(doc.get("source_quality") or 0.6)
        topic = str(doc.get("topic") or "").strip()
        if topic:
            row["topics"].add(topic)
        published_at = _coerce_dt(doc.get("published_at"))
        if published_at and (now - published_at).total_seconds() <= 48 * 3600:
            row["fresh_docs"] += 1

    sources: list[dict[str, Any]] = []
    for row in board.values():
        docs = max(1, int(row["documents"]))
        avg_quality = row["quality_sum"] / docs
        breadth = len(row["topics"])
        freshness = row["fresh_docs"] / docs
        weighted = round((avg_quality * 60.0) + min(20.0, docs * 4.0) + min(20.0, freshness * 20.0 + breadth * 2.0), 1)
        sources.append(
            {
                "source_name": row["source_name"],
                "documents": docs,
                "avg_quality": round(avg_quality, 3),
                "fresh_docs": int(row["fresh_docs"]),
                "topic_breadth": breadth,
                "weighted_score": weighted,
            }
        )
    sources.sort(key=lambda item: (-float(item.get("weighted_score") or 0.0), -int(item.get("documents") or 0)))
    leader = sources[0] if sources else {}
    return {
        "generated_at": now.isoformat(),
        "source_diversity": len(sources),
        "leader": leader,
        "top_sources": sources[:5],
        "avg_quality": round(sum(float(item.get("avg_quality") or 0.0) for item in sources) / max(1, len(sources)), 3),
    }


def _build_crowding_summary(market_intel: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    market_intel = market_intel if isinstance(market_intel, dict) else {}
    relativity = market_intel.get("futures_relativity") if isinstance(market_intel.get("futures_relativity"), dict) else {}
    composite = relativity.get("composite") if isinstance(relativity.get("composite"), dict) else {}
    bias = str(composite.get("bias") or "mixed").lower()
    funding_bias = str(composite.get("funding_bias") or "mixed").lower()
    oi_change = _flt(composite.get("oi_change_pct_avg")) or 0.0
    liq_bias = str((market_intel.get("liquidations") or {}).get("bias") or "mixed").lower() if isinstance(market_intel.get("liquidations"), dict) else "mixed"
    if bias == "bullish" and funding_bias == "shorts_paying_longs":
        regime = "squeeze_upside"
    elif bias == "bearish" and funding_bias == "longs_paying_shorts":
        regime = "flush_downside"
    elif abs(oi_change) < 0.15:
        regime = "balanced"
    else:
        regime = "crowded"
    return {
        "generated_at": now.isoformat(),
        "bias": bias,
        "funding_bias": funding_bias,
        "oi_change_pct": round(oi_change, 4),
        "liquidation_bias": liq_bias,
        "regime": regime,
    }


def _build_weekly_playbook(
    *,
    intraday: dict[str, Any],
    weekly: dict[str, Any],
    event_calendar: dict[str, Any],
    source_scoreboard: dict[str, Any],
    crowding_summary: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    next_event = event_calendar.get("next_event") if isinstance(event_calendar.get("next_event"), dict) else {}
    top_sources = source_scoreboard.get("top_sources") if isinstance(source_scoreboard.get("top_sources"), list) else []
    weekly_claims = weekly.get("claims") if isinstance(weekly.get("claims"), list) else []
    playbook_items = list((((weekly.get("payload") or {}).get("weekly_research") or {}).get("trade_playbook") or [])[:4])
    if not playbook_items:
        bias = str(weekly.get("xlm_bias") or "mixed").lower()
        if bias == "bullish":
            playbook_items = [
                "Prefer long continuations into unswept overhead liquidity during intraday attack windows.",
                "Treat downside sweeps into fib/EMA stretch as reversal-long candidates if reclaim confirms.",
            ]
        elif bias == "bearish":
            playbook_items = [
                "Prefer short continuations into unswept downside liquidity while crowding remains defensive.",
                "Fade failed upside sweeps only when rejection and order-book ask absorption agree.",
            ]
        else:
            playbook_items = [
                "Keep size conservative and let lane quality decide; do not force a weekly directional thesis.",
            ]
    invalidations = [str(item.get("invalidation") or "") for item in weekly_claims if isinstance(item, dict) and item.get("invalidation")]
    monday_ready = (
        int(weekly.get("review_score") or 0) >= 70
        and int(source_scoreboard.get("source_diversity") or 0) >= 3
        and str(weekly.get("source_mode") or "").lower() not in {"fallback", "market_intel_fallback", "unknown"}
    )
    return {
        "generated_at": now.isoformat(),
        "label": str(weekly.get("window_label") or "OUTSIDE_WEEKLY_WINDOW"),
        "macro_regime": weekly.get("macro_regime"),
        "directional_bias": weekly.get("directional_bias"),
        "xlm_bias": weekly.get("xlm_bias"),
        "confidence": weekly.get("confidence"),
        "review_score": weekly.get("review_score"),
        "monday_ready": monday_ready,
        "thesis": weekly.get("summary") or intraday.get("summary") or "No weekly thesis captured yet.",
        "top_setups": playbook_items[:4],
        "risk_map": [
            str(next_event.get("label") or "No major scheduled event queued"),
            f"Positioning pressure (crowding regime): {crowding_summary.get('regime')}",
            f"Macro backdrop (macro regime): {weekly.get('macro_regime')}",
        ],
        "invalidation_triggers": invalidations[:4] or ["Invalidate when intraday structure disagrees with the weekly bias."],
        "checklist": [
            "Respect the session plan before adding size.",
            "Do not hold weak edge into the Friday break or pre-cutoff defense window.",
            "For reversal trades, require clear resting buyers or sellers soaking up flow (book absorption) or a spoof unwind to agree.",
            "Prefer setups that line up with the strongest current research sources.",
        ],
        "top_sources": top_sources[:3],
        "next_event": next_event,
    }


def _event_row(
    *,
    label: str,
    timestamp: datetime | None,
    category: str,
    importance: str,
    bias: str,
    detail: str,
    source: str,
    now: datetime,
) -> dict[str, Any]:
    ts = timestamp.astimezone(timezone.utc) if timestamp else None
    hours = ((ts - now).total_seconds() / 3600.0) if ts else None
    return {
        "event_id": hashlib.sha1(f"{label}|{category}|{source}".encode("utf-8")).hexdigest()[:16],
        "label": label,
        "timestamp": ts.isoformat() if ts else "",
        "category": category,
        "importance": importance,
        "bias": bias,
        "detail": detail,
        "source": source,
        "hours_to_event": round(hours, 2) if hours is not None else None,
        "expired": bool(hours is not None and hours < -2.0),
    }


def _append_scheduled_events(events: list[dict[str, Any]], now: datetime) -> None:
    friday_break = _next_weekday_time(now, weekday=4, hour=21)
    monday_open = _next_weekday_time(now, weekday=0, hour=22)
    events.append(
        _event_row(
            label="Coinbase futures Friday break",
            timestamp=friday_break,
            category="exchange",
            importance="high",
            bias="two_way",
            detail="Derisk before the 5-6 PM ET futures maintenance break.",
            source="system_schedule",
            now=now,
        )
    )
    events.append(
        _event_row(
            label="Weekly research handoff / Monday open",
            timestamp=monday_open,
            category="playbook",
            importance="medium",
            bias="two_way",
            detail="Refresh weekly thesis, event map, and opening-bias checklist before the new trade week.",
            source="system_schedule",
            now=now,
        )
    )


def _maybe_add_keyword_event(events: list[dict[str, Any]], text: str, now: datetime, *, source: str) -> None:
    lower = text.lower()
    keywords = {
        "cpi": ("CPI / inflation release", "macro", "high", "two_way"),
        "fomc": ("FOMC / Fed communication", "macro", "high", "two_way"),
        "fed": ("Federal Reserve catalyst", "macro", "high", "two_way"),
        "jobs": ("US labor / jobs data", "macro", "high", "two_way"),
        "payroll": ("US labor / payrolls", "macro", "high", "two_way"),
        "inflation": ("Inflation narrative shift", "macro", "high", "two_way"),
        "sec": ("Regulatory headline risk", "regulation", "medium", "two_way"),
        "ripple": ("Cross-border payments sector headline", "crypto", "medium", "xlm_sensitive"),
        "stellar": ("Stellar ecosystem catalyst", "xlm", "medium", "xlm_sensitive"),
        "coinbase": ("Coinbase venue / futures operations", "exchange", "medium", "execution"),
    }
    for needle, meta in keywords.items():
        if needle in lower:
            label, category, importance, bias = meta
            events.append(
                _event_row(
                    label=label,
                    timestamp=None,
                    category=category,
                    importance=importance,
                    bias=bias,
                    detail=text,
                    source=source,
                    now=now,
                )
            )
            return


def _event_sort_key(event: dict[str, Any], now: datetime) -> tuple[float, int]:
    ts = _coerce_dt(event.get("timestamp"))
    if ts is None:
        return (999999.0, 1)
    return ((ts - now).total_seconds(), 0)


def _event_timestamp(value: Any, now: datetime) -> datetime | None:
    ts = _coerce_dt(value)
    if ts is not None:
        return ts
    return None


def _coerce_dt(value: Any) -> datetime | None:
    try:
        if not value:
            return None
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        return None


def _next_weekday_time(now: datetime, *, weekday: int, hour: int) -> datetime:
    days_ahead = (weekday - now.weekday()) % 7
    target = now + timedelta(days=days_ahead)
    target = target.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=7)
    return target.astimezone(timezone.utc)


def _intraday_claims(market_intel: dict[str, Any], market_brief: dict[str, Any], confidence: float) -> list[dict[str, Any]]:
    prices = market_intel.get("prices") if isinstance(market_intel.get("prices"), dict) else {}
    relativity = market_intel.get("futures_relativity") if isinstance(market_intel.get("futures_relativity"), dict) else {}
    composite = relativity.get("composite") if isinstance(relativity.get("composite"), dict) else {}
    claims: list[dict[str, Any]] = []
    risk_modifier = str(market_brief.get("risk_modifier") or "neutral")
    claims.append(_claim("macro_regime", "macro", risk_modifier, confidence, f"Intraday risk modifier is {risk_modifier}.", "Invalid if macro tape flips across equities and BTC."))
    xlm_move = _flt(prices.get("xlm_24h_pct"))
    if xlm_move is not None:
        bias = "bullish" if xlm_move > 0 else "bearish" if xlm_move < 0 else "mixed"
        claims.append(_claim("xlm_move_24h", "xlm", bias, confidence, f"XLM 24h move is {xlm_move:+.2f}%.", "Invalid if 24h move mean-reverts and futures context flips."))
    rel_bias = str(composite.get("bias") or "mixed").lower()
    claims.append(_claim("futures_relativity", "crypto", rel_bias, confidence, f"Cross-venue futures relativity bias is {rel_bias}.", "Invalid if funding and OI stop agreeing with price."))
    return claims


def _weekly_claims(weekly_research: dict[str, Any], confidence: float) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    claims.append(
        _claim(
            "weekly_macro_regime",
            "macro",
            str(weekly_research.get("macro_regime") or "neutral").lower(),
            confidence,
            "Weekly macro regime extracted from the latest strategic research.",
            "Invalid if rates, equities, and BTC diverge from the weekly thesis.",
        )
    )
    claims.append(
        _claim(
            "weekly_xlm_bias",
            "xlm",
            str(weekly_research.get("xlm_bias") or "mixed").lower(),
            confidence,
            "Weekly XLM directional bias extracted from strategic research.",
            "Invalid if XLM-specific catalysts or market structure break the weekly narrative.",
        )
    )
    for idx, item in enumerate((weekly_research.get("trade_playbook") or [])[:3], start=1):
        claims.append(
            _claim(
                f"weekly_playbook_{idx}",
                "playbook",
                str(weekly_research.get("xlm_bias") or "mixed").lower(),
                max(0.3, confidence - 0.05),
                str(item),
                "Invalid if intraday market structure and liquidation intelligence disagree.",
            )
        )
    return claims


def _claim(claim_type: str, asset_scope: str, bias: str, confidence: float, text: str, invalidation: str) -> dict[str, Any]:
    claim_id = hashlib.sha1(f"{claim_type}|{text}".encode("utf-8")).hexdigest()[:16]
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "asset_scope": asset_scope,
        "bias": bias,
        "horizon": "intraday" if "intraday" in claim_type or claim_type.startswith("xlm_") else "weekly",
        "confidence": round(confidence, 3),
        "claim_text": text,
        "invalidation": invalidation,
        "tradable": claim_type not in {"macro_regime", "weekly_macro_regime"},
    }


def _documents_from_market_intel(market_intel: dict[str, Any], *, research_kind: str, now: datetime) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for item in (market_intel.get("headlines") or [])[:10]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        published_at = str(item.get("published_at") or "")
        docs.append(
            {
                "document_id": hashlib.sha1(f"{research_kind}|{title}|{item.get('link')}".encode("utf-8")).hexdigest()[:16],
                "topic": str(item.get("topic") or "market"),
                "source_name": str(item.get("source") or "unknown"),
                "title": title,
                "url": str(item.get("link") or ""),
                "published_at": published_at,
                "collected_at": now.isoformat(),
                "snippet": title,
                "source_quality": _source_quality(str(item.get("source") or "")),
            }
        )
    return docs


def _documents_from_weekly_research(weekly_research: dict[str, Any], *, now: datetime) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for src in (weekly_research.get("sources") or [])[:10]:
        label = str(src).strip()
        if not label:
            continue
        docs.append(
            {
                "document_id": hashlib.sha1(f"weekly|{label}".encode("utf-8")).hexdigest()[:16],
                "topic": "weekly_research",
                "source_name": label,
                "title": label,
                "url": "",
                "published_at": str(weekly_research.get("updated_at") or ""),
                "collected_at": now.isoformat(),
                "snippet": label,
                "source_quality": _source_quality(label),
            }
        )
    return docs


def _review_confidence(*, base: float, documents: list[dict[str, Any]], generated_at: str | None, now: datetime) -> float:
    diversity_bonus = min(0.2, 0.04 * len({d.get("source_name") for d in documents if d.get("source_name")}))
    freshness_penalty = 0.0
    if generated_at:
        try:
            ts = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds() / 3600.0)
            freshness_penalty = min(0.25, age_hours / 48.0)
        except Exception:
            freshness_penalty = 0.1
    return round(max(0.2, min(0.95, base + diversity_bonus - freshness_penalty)), 3)


def _review_state(
    documents: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    *,
    generated_at: str | None,
    now: datetime,
) -> dict[str, Any]:
    notes: list[str] = []
    source_count = len({d.get("source_name") for d in documents if d.get("source_name")})
    evidence_count = len(documents)
    claim_count = len(claims)
    score = 45 + min(20, source_count * 3) + min(15, claim_count * 2) + min(10, evidence_count)
    if source_count < 3:
        notes.append("low_source_diversity")
        score -= 10
    if evidence_count < 4:
        notes.append("thin_evidence")
        score -= 10
    if generated_at:
        try:
            ts = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_hours = (now - ts.astimezone(timezone.utc)).total_seconds() / 3600.0
            if age_hours > 24:
                notes.append("stale_research")
                score -= 15
        except Exception:
            notes.append("invalid_timestamp")
            score -= 5
    return {"score": max(0, min(100, int(score))), "notes": notes or ["review_pass"]}


def _emit_research_run(
    *,
    research_kind: str,
    state: dict[str, Any],
    logs_dir: Path,
    data_dir: Path,
    generated_at: datetime,
) -> None:
    meta_path = data_dir / "market_intel_emit_state.json"
    meta = _read_json(meta_path)
    if not isinstance(meta, dict):
        meta = {}
    payload = state.get("payload") if isinstance(state.get("payload"), dict) else {}
    source_ts = (
        ((payload.get("market_intel") or {}).get("fetched_at"))
        or ((payload.get("weekly_research") or {}).get("updated_at"))
        or state.get("generated_at")
    )
    run_id = hashlib.sha1(f"{research_kind}|{source_ts}|{state.get('summary')}".encode("utf-8")).hexdigest()[:20]
    if str(meta.get(research_kind) or "") == run_id:
        return

    run = {
        "run_id": run_id,
        "research_kind": research_kind,
        "generated_at": generated_at.isoformat(),
        "source_timestamp": source_ts,
        "source_mode": state.get("source_mode"),
        "macro_regime": state.get("macro_regime"),
        "directional_bias": state.get("directional_bias"),
        "xlm_bias": state.get("xlm_bias"),
        "confidence": state.get("confidence"),
        "review_score": state.get("review_score"),
        "summary": state.get("summary"),
        "window_label": state.get("window_label"),
    }
    _append_jsonl(logs_dir / "market_intel_runs.jsonl", run)
    for doc in state.get("documents") or []:
        if isinstance(doc, dict):
            row = dict(doc)
            row["run_id"] = run_id
            row["research_kind"] = research_kind
            _append_jsonl(logs_dir / "market_intel_documents.jsonl", row)
    for claim in state.get("claims") or []:
        if isinstance(claim, dict):
            row = dict(claim)
            row["run_id"] = run_id
            row["research_kind"] = research_kind
            row["generated_at"] = generated_at.isoformat()
            row["review_score"] = state.get("review_score")
            _append_jsonl(logs_dir / "market_intel_claims.jsonl", row)
    meta[research_kind] = run_id
    _write_json(meta_path, meta)


def _read_cached_payload(path: Path, key: str) -> dict[str, Any]:
    data = _read_json(path)
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _source_mode(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    if payload.get("generated_from"):
        return str(payload.get("generated_from"))
    if payload.get("risk_modifier"):
        return "brief_cache"
    return "unknown"


def _source_quality(source_name: str) -> float:
    name = source_name.lower()
    if any(x in name for x in ("reuters", "bloomberg", "wsj", "ft")):
        return 0.95
    if any(x in name for x in ("coin desk", "coindesk", "cointelegraph", "yahoo finance", "cnbc")):
        return 0.8
    if any(x in name for x in ("google", "rss", "news")):
        return 0.7
    return 0.6


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    tmp.replace(path)


def _flt(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    state = refresh_market_intel_state(
        config={},
        data_dir=base_dir / "data",
        logs_dir=base_dir / "logs",
    )
    print(json.dumps(state, indent=2, default=str))
