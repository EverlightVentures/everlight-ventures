"""Research edge -- the brain for the DEEP-liquidity markets (sports/elections/etc).

Crypto markets get a pure-math edge (crypto_edge.py). Event markets need real-world
research: Perplexity Sonar reads the live matchup/race/situation, Claude turns that
into a probability, and we compare to Kalshi's price. Direct HTTP (urllib) to both
APIs so it runs on e5 with zero installs.

estimate(title, yes_means) -> {"prob", "confidence", "reasoning", "research"}.
Keys load from 03_Credentials/.env via paths.read_env_key.
"""
import json
import re
import urllib.request

from kalshi_agent.paths import read_env_key

PPLX_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _perplexity(prompt, model="sonar", timeout=45):
    key = read_env_key("PERPLEXITY_API_KEY") or read_env_key("PPLX_API_KEY")
    if not key:
        return ""
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(PPLX_URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        return r["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[research unavailable: {e}]"


def _claude(prompt, model="claude-sonnet-4-6", max_tokens=350, timeout=50):
    key = read_env_key("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no ANTHROPIC_API_KEY")
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(ANTHROPIC_URL, data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return r["content"][0]["text"]


def estimate(title, yes_means, model="claude-sonnet-4-6"):
    """Research a market + return a probability the YES outcome happens."""
    research = _perplexity(
        "You are a research analyst for a prediction market. Give the most current, "
        "factual evidence (odds, polls, injuries, form, results, news) relevant to:\n"
        f"MARKET: {title}\nYES means: {yes_means}\n"
        "Be concise and specific with numbers/dates. Do not give a probability yourself.")
    prompt = (
        "You are a sharp, calibrated prediction-market trader. Using ONLY the market and the "
        "research below, estimate the TRUE probability the YES outcome resolves true. Be honest "
        "about uncertainty -- most real edges are small.\n\n"
        f"MARKET: {title}\nYES means: {yes_means}\n\nRESEARCH:\n{research}\n\n"
        'Respond with ONLY this JSON, nothing else: '
        '{"prob": <0.0-1.0>, "confidence": <0.0-1.0>, "reasoning": "<one short sentence>"}')
    txt = _claude(prompt, model=model)
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return {"prob": None, "confidence": 0.0, "reasoning": "parse failed", "research": research}
    d = json.loads(m.group(0))
    return {"prob": float(d["prob"]), "confidence": float(d.get("confidence", 0.5)),
            "reasoning": d.get("reasoning", ""), "research": research[:400]}


if __name__ == "__main__":
    import sys
    import urllib.parse
    K = "https://api.elections.kalshi.com/trade-api/v2"
    ticker = sys.argv[1] if len(sys.argv) > 1 else None
    m = json.loads(urllib.request.urlopen(K + f"/markets/{ticker}", timeout=15).read())["market"]
    title = m.get("title", "")
    yes_means = m.get("yes_sub_title") or m.get("subtitle") or "the YES outcome"
    print(f"MARKET: {title}\nYES means: {yes_means}")
    r = estimate(title, yes_means)
    print(f"\nClaude prob(YES): {r['prob']}  confidence: {r['confidence']}")
    print(f"reasoning: {r['reasoning']}")
    print(f"research snippet: {r['research'][:200]}")
