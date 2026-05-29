"""Crypto 5-minute candle markets -- the high-activity momentum lane.

Polymarket's busiest markets (where the smart money + volume live) are the
5-minute 'Bitcoin Up or Down' candle markets (slug btc-updown-5m-{window_ts}),
resolving every 5 minutes. The edge here is NOT news/Claude -- it is short-term
PRICE MOMENTUM (transcript strategy: enter LATE in the window after the candle
has formed direction, ride strong momentum, SKIP indecisive 'doji' candles).

Honest: a 5-min BTC candle is near a coin flip; momentum gives a thin edge at
best, and crypto fees are the highest on Polymarket. This lane runs on BOUNDED
small stakes -- it's a fast, cheap experiment whose 5-min resolution tells us
within ~a day whether any real edge exists.

Free price feed: Coinbase 1m candles (no key, US-reachable).
"""
import json
import time
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"
COINBASE = "https://api.exchange.coinbase.com"
ASSET_SLUGS = {"BTC": "btc", "ETH": "eth", "SOL": "sol", "XRP": "xrp"}
ASSET_PRODUCTS = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ev-candle/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())


def current_window_ts(now_ts: float = None) -> int:
    """Unix ts of the current 5-minute window start."""
    now = int(now_ts if now_ts is not None else time.time())
    return (now // 300) * 300


def find_candle_market(asset: str = "BTC", now_ts: float = None) -> dict | None:
    """The live 5m up/down market for this window. Returns a dict with token ids
    + prices, or None. Tries the current window then the next (markets are keyed
    by window-start; allow +/- one window for clock skew)."""
    slug_base = ASSET_SLUGS.get(asset.upper())
    if not slug_base:
        return None
    base = current_window_ts(now_ts)
    for ts in (base, base + 300, base - 300):
        slug = f"{slug_base}-updown-5m-{ts}"
        try:
            data = _get(f"{GAMMA}/markets?slug={slug}")
        except Exception:
            continue
        m = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) and data.get("id") else None)
        if not m or m.get("closed"):
            continue
        outcomes = m.get("outcomes"); prices = m.get("outcomePrices"); toks = m.get("clobTokenIds")
        outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
        prices = json.loads(prices) if isinstance(prices, str) else prices
        toks = json.loads(toks) if isinstance(toks, str) else toks
        if not (outcomes and prices and toks):
            continue
        return {
            "slug": slug, "window_ts": ts, "asset": asset.upper(),
            "question": m.get("question", ""),
            "outcomes": outcomes,                      # ["Up","Down"]
            "prices": {o: float(p) for o, p in zip(outcomes, prices)},
            "token_ids": {o: str(t) for o, t in zip(outcomes, toks)},
            "end_date": m.get("endDate", ""),
            "liquidity": float(m.get("liquidity", 0) or 0),
        }
    return None


def momentum(asset: str = "BTC", window_ts: int = None, now_ts: float = None) -> dict:
    """Read 1m candles and gauge the current 5m window's direction + strength.

    Returns {direction 'Up'/'Down', strength 0..1, minutes_in, is_doji}.
    strength = |net move this window| / recent 1m volatility (ATR-like), capped.
    """
    product = ASSET_PRODUCTS.get(asset.upper(), "BTC-USD")
    win = window_ts if window_ts is not None else current_window_ts(now_ts)
    now = now_ts if now_ts is not None else time.time()
    candles = _get(f"{COINBASE}/products/{product}/candles?granularity=60")  # [t,low,high,open,close,vol]
    candles = sorted(candles, key=lambda c: c[0])
    in_win = [c for c in candles if win <= c[0] < win + 300]
    recent = candles[-30:] if len(candles) >= 30 else candles
    if not in_win or not recent:
        mins = ((now_ts if now_ts is not None else time.time()) - win) / 60.0
        return {"direction": None, "strength": 0.0, "minutes_in": round(mins, 2),
                "is_doji": True, "net": 0.0}
    open_px = in_win[0][3]
    last_px = in_win[-1][4]
    net = last_px - open_px
    # recent 1m volatility (mean true range proxy)
    vol = sum(abs(c[2] - c[1]) for c in recent) / len(recent) or 1e-9
    strength = min(1.0, abs(net) / (vol * 2))   # net move vs ~2 ATR -> 0..1
    minutes_in = (now - win) / 60.0
    is_doji = strength < 0.25                     # weak body relative to range = indecision
    return {
        "direction": "Up" if net > 0 else "Down",
        "strength": round(strength, 3),
        "minutes_in": round(minutes_in, 2),
        "is_doji": is_doji,
        "net": round(net, 2),
    }


def window_outcome(asset: str, window_ts: int) -> str | None:
    """Resolve a finished 5m candle from the price feed: 'Up' if close>open over
    the window, 'Down' if <, None if the window has not fully closed yet. This
    settles candle bets deterministically without waiting on Polymarket's oracle."""
    if time.time() < window_ts + 300:
        return None  # window not finished
    product = ASSET_PRODUCTS.get(asset.upper(), "BTC-USD")
    try:
        candles = sorted(_get(f"{COINBASE}/products/{product}/candles?granularity=60"),
                         key=lambda c: c[0])
    except Exception:
        return None
    in_win = [c for c in candles if window_ts <= c[0] < window_ts + 300]
    if not in_win:
        return None
    open_px, close_px = in_win[0][3], in_win[-1][4]
    return "Up" if close_px >= open_px else "Down"


def candle_decision(asset: str = "BTC", min_edge: float = 0.05,
                    enter_after_min: float = 3.0, now_ts: float = None) -> dict | None:
    """Combine the live market + momentum into a trade decision, or None.

    Strategy (transcript-derived): only act LATE in the window (>= enter_after_min,
    i.e. last ~2 min of the 5-min candle) once direction has formed, SKIP dojis,
    and only bet when our momentum-implied probability beats the market price by
    >= min_edge. predicted_prob = 0.5 + 0.4*strength (capped)."""
    mkt = find_candle_market(asset, now_ts=now_ts)
    if not mkt:
        return None
    mo = momentum(asset, window_ts=mkt["window_ts"], now_ts=now_ts)
    if mo["direction"] is None or mo["is_doji"]:
        return {"skip": "doji/indecisive", "market": mkt, "momentum": mo}
    if mo["minutes_in"] < enter_after_min:
        return {"skip": "too early in window", "market": mkt, "momentum": mo}
    direction = mo["direction"]
    price = mkt["prices"].get(direction, 0.5)
    pred = min(0.95, 0.5 + 0.4 * mo["strength"])
    edge = pred - price
    if edge < min_edge:
        return {"skip": f"edge {edge:.3f} < {min_edge}", "market": mkt, "momentum": mo}
    return {
        "asset": asset.upper(), "market_id": mkt["token_ids"][direction],
        "outcome": direction, "market_price": price, "predicted_prob": pred,
        "edge": round(edge, 4), "strength": mo["strength"],
        "slug": mkt["slug"], "question": mkt["question"],
    }
