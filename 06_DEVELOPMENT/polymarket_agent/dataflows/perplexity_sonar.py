"""Perplexity Sonar dataflow -- REAL live news/velocity signal for Polymarket.

Calls the live Perplexity Sonar API (api.perplexity.ai, model 'sonar') asking
for material developments in a market category, parses the structured response
into Signals, and TTL-caches to disk so we do not burn an API call every cycle.

This is the velocity layer that replaces a paid Twitter API: Sonar is itself a
real-time, source-cited search engine. Key is loaded from the shared Everlight
.env (PERPLEXITY_API_KEY). Degrades gracefully to [] (logged, never silent) if
the key is missing or the API fails -- a dead signal source must not crash the
trade cycle.
"""
import json
import logging
import re
import time
from pathlib import Path

from polymarket_agent.dataflows.interface import Signal

log = logging.getLogger("polymarket.sonar")

API_URL = "https://api.perplexity.ai/chat/completions"
ENV_PATH = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
DEFAULT_CACHE = Path(__file__).parent.parent / "data" / "sonar_cache.json"
_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def _load_key() -> str | None:
    import os
    # Operator-edited .env is authoritative; prefer it over ambient env.
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("PERPLEXITY_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    k = os.getenv("PERPLEXITY_API_KEY") or os.getenv("PPLX_API_KEY")
    return k.strip().strip('"').strip("'") if k else None


class Sonar:
    def __init__(self, api_key: str = None, cache_path=None, cache_ttl: int = 600,
                 model: str = "sonar"):
        self.api_key = api_key if api_key is not None else _load_key()
        self.cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE
        self.cache_ttl = cache_ttl
        self.model = model

    def _prompt(self, category: str, last_minutes: int) -> str:
        return (
            f"List up to 8 material, market-moving developments from roughly the "
            f"last {last_minutes} to {max(last_minutes, 180)} minutes relevant to "
            f"prediction markets in this category: {category}. "
            f"Return ONLY a compact JSON array. Each element: "
            f'{{"text": "<one factual sentence>", "url": "<source url>", '
            f'"sentiment": <number -1 to 1>}}. No prose, no markdown fences.'
        )

    def _call_sonar(self, prompt: str) -> str:
        """Real HTTP call to Perplexity Sonar. Returns the message content string."""
        import requests
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a real-time financial news "
                 "research assistant. Output only valid JSON when asked."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
        }
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _parse(self, content: str) -> list:
        if not content:
            return []
        m = _JSON_ARRAY.search(content)
        if not m:
            return []
        try:
            rows = json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            return []
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            try:
                sent = float(r.get("sentiment", 0.0))
            except (TypeError, ValueError):
                sent = 0.0
            out.append(Signal(
                source="perplexity_sonar",
                text=str(r.get("text", ""))[:500],
                url=str(r.get("url", "")),
                sentiment=max(-1.0, min(1.0, sent)),
                credibility=0.75,
            ))
        return out

    def _read_cache(self, category: str, now_ts: float):
        if not self.cache_path.exists():
            return None
        try:
            blob = json.loads(self.cache_path.read_text())
        except (json.JSONDecodeError, ValueError):
            return None
        entry = blob.get(category)
        if not entry:
            return None
        if now_ts - entry.get("ts", 0) > self.cache_ttl:
            return None
        return [Signal(**s) for s in entry.get("signals", [])]

    def _write_cache(self, category: str, signals: list, now_ts: float):
        import os
        blob = {}
        if self.cache_path.exists():
            try:
                blob = json.loads(self.cache_path.read_text())
            except (json.JSONDecodeError, ValueError):
                blob = {}
        blob[category] = {"ts": now_ts, "signals": [vars(s) for s in signals]}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(blob, indent=2))
        os.replace(tmp, self.cache_path)

    def get_news_velocity(self, category: str, last_minutes: int = 10,
                          now_ts: float = None) -> list:
        now = now_ts if now_ts is not None else time.time()
        cached = self._read_cache(category, now)
        if cached is not None:
            return cached
        if not self.api_key:
            log.warning("Sonar disabled: no PERPLEXITY_API_KEY found")
            return []
        try:
            content = self._call_sonar(self._prompt(category, last_minutes))
        except Exception as e:
            log.warning("Sonar live call failed: %s: %s", type(e).__name__, e)
            return []
        signals = self._parse(content)
        self._write_cache(category, signals, now)
        return signals
