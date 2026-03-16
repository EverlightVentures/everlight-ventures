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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Module state ────────────────────────────────────────────────────
_ENABLED: bool = True
_CACHE_PATH: Path = Path(__file__).parent.parent / "data" / "market_brief.json"
_ENV_FILE: Path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
_CLX_BIN: Path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py")
_API_KEY: str | None = None
_CACHE_TTL: int = 900  # 15 minutes

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

    if brief:
        _write_cache(brief)
    
    return brief

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
    return _read_cache()
