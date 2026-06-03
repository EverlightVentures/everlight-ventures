"""Crypto edge model -- the money math for Kalshi BTC/ETH range markets.

Kalshi lists markets like "BTC above $X at 5pm" / "BTC between $A-$B". We compute
the REAL probability of that outcome from the live spot price + realized vol +
time-to-close (a short-horizon lognormal, ~zero drift). Edge = our prob - the
market price. When |edge| is big enough to clear Kalshi's fee (peaks 1.75c/contract
at 50c, ~0.44c as a maker) AND leave profit, that side is a real bet.

No Claude needed -- this is a defensible quant edge that runs every cycle for free.
News/event markets (econ/weather) layer the Claude+Perplexity edge on top later.
"""
import math
import statistics
import time
import urllib.request
import json

COINBASE = "https://api.exchange.coinbase.com"
PRODUCT = {"BTC": "BTC-USD", "ETH": "ETH-USD"}


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def spot_and_vol(asset="BTC"):
    """Live spot + per-minute realized vol (stdev of 1m log returns, last ~60m)."""
    p = PRODUCT.get(asset.upper(), "BTC-USD")
    req = urllib.request.Request(f"{COINBASE}/products/{p}/candles?granularity=60",
                                 headers={"User-Agent": "ev-edge/1.0"})
    c = sorted(json.loads(urllib.request.urlopen(req, timeout=15).read()), key=lambda x: x[0])
    spot = c[-1][4]
    rets = [math.log(c[i][4] / c[i - 1][4]) for i in range(1, len(c)) if c[i - 1][4]]
    sig_1m = statistics.pstdev(rets[-60:]) if len(rets) > 10 else 0.0008
    return spot, sig_1m


def prob_above(spot, strike, sig_1m, minutes_left):
    """P(close > strike) under short-horizon lognormal, ~zero drift."""
    if minutes_left <= 0 or sig_1m <= 0 or spot <= 0 or strike <= 0:
        return 1.0 if spot > strike else 0.0
    sigma = sig_1m * math.sqrt(minutes_left)
    z = math.log(strike / spot) / sigma          # standardized log-distance to strike
    return 1.0 - _norm_cdf(z)                     # P(close above strike)


def prob_between(spot, lo, hi, sig_1m, minutes_left):
    """P(lo < close < hi)."""
    return max(0.0, prob_above(spot, lo, sig_1m, minutes_left)
               - prob_above(spot, hi, sig_1m, minutes_left))


def edge(model_prob, market_price):
    """Signed edge in probability terms (market_price in 0..1).
    >0 -> YES is underpriced (buy YES); <0 -> NO is underpriced (buy NO)."""
    return model_prob - market_price


def minutes_to_close(close_ts, now=None):
    return ((close_ts) - (now if now is not None else time.time())) / 60.0
