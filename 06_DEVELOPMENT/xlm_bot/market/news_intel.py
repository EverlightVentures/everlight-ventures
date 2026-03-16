"""Market intelligence collector for dashboard/news alerts.

Collects lightweight macro signals (crypto, equity, rates headlines, OI proxies)
with on-disk caching so bot cycles stay fast and resilient.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

_UA = {"User-Agent": "xlm-bot/market-intel"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_float(v: Any, default: float | None = None) -> float | None:
    try:
        return float(v)
    except Exception:
        return default


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            out = json.loads(path.read_text())
            return out if isinstance(out, dict) else {}
    except Exception:
        pass
    return {}


def _write_json(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
        tmp.replace(path)
    except Exception:
        pass


def _get_json(url: str, *, timeout: float, params: dict | None = None) -> dict | None:
    try:
        r = requests.get(url, params=params, headers=_UA, timeout=timeout)
        if r.status_code != 200:
            return None
        out = r.json()
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _get_text(url: str, *, timeout: float, params: dict | None = None) -> str | None:
    try:
        r = requests.get(url, params=params, headers=_UA, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def _fetch_crypto_prices(timeout: float) -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,stellar",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    payload = _get_json(url, timeout=timeout, params=params) or {}
    btc = payload.get("bitcoin") if isinstance(payload.get("bitcoin"), dict) else {}
    xlm = payload.get("stellar") if isinstance(payload.get("stellar"), dict) else {}
    return {
        "btc_usd": _to_float(btc.get("usd")),
        "btc_24h_pct": _to_float(btc.get("usd_24h_change")),
        "xlm_usd": _to_float(xlm.get("usd")),
        "xlm_24h_pct": _to_float(xlm.get("usd_24h_change")),
    }


def _fetch_stooq_quote(symbol: str, timeout: float) -> dict | None:
    text = _get_text(
        "https://stooq.com/q/l/",
        timeout=timeout,
        params={"s": symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
    )
    if not text:
        return None
    try:
        rows = list(csv.DictReader(text.splitlines()))
        if not rows:
            return None
        r = rows[0]
        close = _to_float(r.get("Close"))
        open_ = _to_float(r.get("Open"))
        if close is None:
            return None
        move_pct = None
        if open_ is not None and open_ > 0:
            move_pct = (close - open_) / open_ * 100.0
        return {"close": close, "move_pct": move_pct}
    except Exception:
        return None


def _fetch_macro_prices(timeout: float) -> dict:
    def _first(symbols: list[str]) -> dict | None:
        for s in symbols:
            q = _fetch_stooq_quote(s, timeout=timeout)
            if q:
                return q
        return None

    spx = _first(["^spx", "spx.us"])
    ndx = _first(["^ixic", "ndq.us", "^ndx"])
    gold = _first(["xauusd", "gold"])
    return {
        "spx": spx or {},
        "ndx": ndx or {},
        "gold": gold or {},
    }


def _fetch_okx_oi(timeout: float) -> float | None:
    payload = _get_json(
        "https://www.okx.com/api/v5/public/open-interest",
        timeout=timeout,
        params={"instType": "SWAP", "uly": "BTC-USDT", "instId": "BTC-USDT-SWAP"},
    )
    if not payload:
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    row = data[0] if isinstance(data[0], dict) else {}
    return _to_float(row.get("oiUsd") or row.get("oi"))


def _fetch_deribit_oi(timeout: float) -> float | None:
    payload = _get_json(
        "https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
        timeout=timeout,
        params={"currency": "BTC", "kind": "future"},
    )
    if not payload:
        return None
    rows = payload.get("result")
    if not isinstance(rows, list):
        return None
    total = 0.0
    count = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        oi = _to_float(r.get("open_interest"))
        if oi is None:
            continue
        total += oi
        count += 1
    if count <= 0:
        return None
    return total


def _rss_items(xml_text: str, topic: str, limit: int = 6) -> list[dict]:
    out: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out

    for item in root.findall(".//item"):
        if len(out) >= limit:
            break
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        source = ""
        if " - " in title:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                title, source = parts[0].strip(), parts[1].strip()
        pub_iso = ""
        if pub_raw:
            try:
                dt = parsedate_to_datetime(pub_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                pub_iso = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pub_iso = ""
        if not title:
            continue
        out.append(
            {
                "topic": topic,
                "title": title,
                "link": link,
                "source": source,
                "published_at": pub_iso,
            }
        )
    return out


def _fetch_news(timeout: float, max_items: int) -> list[dict]:
    queries = [
        ("btc crypto market liquidation fed", "crypto"),
        ("nasdaq s&p 500 federal reserve rates fintech", "macro"),
        ("gold market central bank policy", "gold"),
    ]
    headlines: list[dict] = []
    for q, topic in queries:
        xml = _get_text(
            "https://news.google.com/rss/search",
            timeout=timeout,
            params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )
        if not xml:
            continue
        headlines.extend(_rss_items(xml, topic=topic, limit=max(3, max_items // 4)))

    fed = _get_text("https://www.federalreserve.gov/feeds/press_monetary.xml", timeout=timeout)
    if fed:
        headlines.extend(_rss_items(fed, topic="fed", limit=4))

    dedup: list[dict] = []
    seen: set[str] = set()
    for h in headlines:
        key = str(h.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        dedup.append(h)
    dedup.sort(key=lambda x: str(x.get("published_at") or ""), reverse=True)
    return dedup[: max(1, max_items)]


def _pct_change(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / abs(prev) * 100.0


def _risk_flags(payload: dict) -> list[str]:
    out: list[str] = []
    p = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    btc_24h = _to_float(p.get("btc_24h_pct"))
    xlm_24h = _to_float(p.get("xlm_24h_pct"))
    if btc_24h is not None and abs(btc_24h) >= 3.0:
        out.append(f"BTC 24h move {btc_24h:+.1f}%")
    if xlm_24h is not None and abs(xlm_24h) >= 5.0:
        out.append(f"XLM 24h move {xlm_24h:+.1f}%")

    oi = payload.get("oi_proxy") if isinstance(payload.get("oi_proxy"), dict) else {}
    okx_chg = _to_float((oi.get("okx") or {}).get("change_pct"))
    deribit_chg = _to_float((oi.get("deribit") or {}).get("change_pct"))
    if okx_chg is not None and abs(okx_chg) >= 7.0:
        out.append(f"OKX OI shift {okx_chg:+.1f}%")
    if deribit_chg is not None and abs(deribit_chg) >= 7.0:
        out.append(f"Deribit OI shift {deribit_chg:+.1f}%")

    heads = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []
    joined = " | ".join(str(h.get("title") or "").lower() for h in heads[:12] if isinstance(h, dict))
    if "liquidation" in joined:
        out.append("Liquidation headlines active")
    if "federal reserve" in joined or "fed" in joined or "interest rate" in joined:
        out.append("Fed/rates headlines active")
    return out[:6]


def _summary(payload: dict) -> str:
    p = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    m = payload.get("macro") if isinstance(payload.get("macro"), dict) else {}
    oi = payload.get("oi_proxy") if isinstance(payload.get("oi_proxy"), dict) else {}

    bits: list[str] = []
    btc = _to_float(p.get("btc_usd"))
    btc_24 = _to_float(p.get("btc_24h_pct"))
    if btc is not None:
        b = f"BTC ${btc:,.0f}"
        if btc_24 is not None:
            b += f" ({btc_24:+.2f}% 24h)"
        bits.append(b)
    xlm = _to_float(p.get("xlm_usd"))
    xlm_24 = _to_float(p.get("xlm_24h_pct"))
    if xlm is not None:
        x = f"XLM ${xlm:.4f}"
        if xlm_24 is not None:
            x += f" ({xlm_24:+.2f}% 24h)"
        bits.append(x)

    spx = _to_float((m.get("spx") or {}).get("close"))
    ndx = _to_float((m.get("ndx") or {}).get("close"))
    gold = _to_float((m.get("gold") or {}).get("close"))
    macro_bits: list[str] = []
    if spx is not None:
        macro_bits.append(f"SPX {spx:,.1f}")
    if ndx is not None:
        macro_bits.append(f"NDX {ndx:,.1f}")
    if gold is not None:
        macro_bits.append(f"Gold {gold:,.1f}")
    if macro_bits:
        bits.append(", ".join(macro_bits))

    okx_oi = _to_float((oi.get("okx") or {}).get("value"))
    okx_chg = _to_float((oi.get("okx") or {}).get("change_pct"))
    if okx_oi is not None:
        o = f"OKX OI {okx_oi:,.0f}"
        if okx_chg is not None:
            o += f" ({okx_chg:+.1f}%)"
        bits.append(o)

    top = ""
    heads = payload.get("headlines") if isinstance(payload.get("headlines"), list) else []
    if heads and isinstance(heads[0], dict):
        top = str(heads[0].get("title") or "").strip()
    if top:
        bits.append(f"Top: {top[:140]}")

    return " | ".join(bits) if bits else "Market intel collected with partial data."


def get_market_intel(
    config: dict | None,
    data_dir: Path,
    *,
    now_utc: datetime | None = None,
) -> dict:
    """Return market intel payload with persistent cache fallback.

    Output keys:
      fetched_at, summary, prices, macro, oi_proxy, risk_flags, headlines,
      is_fresh, cache_age_sec
    """
    cfg = config or {}
    now = now_utc or _now_utc()
    refresh_seconds = int(cfg.get("refresh_seconds", 900) or 900)
    timeout = float(cfg.get("timeout_sec", 3.5) or 3.5)
    max_headlines = int(cfg.get("max_headlines", 24) or 24)
    cache_path = Path(data_dir) / "market_intel_cache.json"

    cache = _read_json(cache_path)
    cached_payload = cache.get("payload") if isinstance(cache.get("payload"), dict) else {}
    cached_ts_raw = str(cache.get("updated_at") or "")
    cached_ts = None
    if cached_ts_raw:
        try:
            cached_ts = datetime.fromisoformat(cached_ts_raw.replace("Z", "+00:00"))
            if cached_ts.tzinfo is None:
                cached_ts = cached_ts.replace(tzinfo=timezone.utc)
        except Exception:
            cached_ts = None

    if cached_payload and cached_ts:
        age = (now - cached_ts.astimezone(timezone.utc)).total_seconds()
        if age <= max(30, refresh_seconds):
            out = dict(cached_payload)
            out["is_fresh"] = False
            out["cache_age_sec"] = int(max(0, age))
            return out

    try:
        prices = _fetch_crypto_prices(timeout)
        macro = _fetch_macro_prices(timeout)
        okx_oi = _fetch_okx_oi(timeout)
        deribit_oi = _fetch_deribit_oi(timeout)
        prev_oi = cached_payload.get("oi_proxy") if isinstance(cached_payload.get("oi_proxy"), dict) else {}
        prev_okx = _to_float((prev_oi.get("okx") or {}).get("value"))
        prev_deribit = _to_float((prev_oi.get("deribit") or {}).get("value"))
        oi_proxy = {
            "okx": {
                "value": okx_oi,
                "change_pct": _pct_change(okx_oi, prev_okx),
            },
            "deribit": {
                "value": deribit_oi,
                "change_pct": _pct_change(deribit_oi, prev_deribit),
            },
        }
        headlines = _fetch_news(timeout, max_items=max_headlines)
        payload = {
            "fetched_at": now.astimezone(timezone.utc).isoformat(),
            "prices": prices,
            "macro": macro,
            "oi_proxy": oi_proxy,
            "headlines": headlines,
        }
        payload["risk_flags"] = _risk_flags(payload)
        payload["summary"] = _summary(payload)
        _write_json(cache_path, {"updated_at": payload["fetched_at"], "payload": payload})
        payload["is_fresh"] = True
        payload["cache_age_sec"] = 0
        return payload
    except Exception:
        if cached_payload:
            out = dict(cached_payload)
            out["is_fresh"] = False
            out["cache_age_sec"] = -1
            return out
        return {}
