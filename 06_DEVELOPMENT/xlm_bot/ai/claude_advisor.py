"""Claude AI trade intelligence advisor.

Fire-and-forget background calls to Claude CLI.  Results cached to
data/ai_insight.json and read on the NEXT bot cycle.  Bot never blocks
waiting for Claude — if no insight cached, normal logic proceeds.

Feeds Claude actual OHLCV candle data, indicator values, and trade
history so it can see the real chart before making recommendations.

Mirrors the fire-and-forget pattern in alerts/slack.py.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai.prompts import entry_prompt, exit_prompt, regime_prompt, master_directive_prompt

# ── Module state ────────────────────────────────────────────────────
_ENABLED: bool = False
_CACHE_PATH: Path = Path(__file__).parent.parent / "data" / "ai_insight.json"
_TRADES_PATH: Path = Path(__file__).parent.parent / "logs" / "trades.csv"
_MODEL: str = "opus"
_CONFIG: dict = {}
_ALLOWED_ACTIONS = ("ENTER_LONG", "ENTER_SHORT", "EXIT", "HOLD", "FLAT")
_CODEX_ENABLED: bool = False
_CODEX_CONFIG: dict = {}
_CODEX_MODEL: str = "gpt-5"
_CODEX_BIN: str = "codex"
_CLX_BIN: Path = Path(
    os.environ.get("CLX_DELEGATE_BIN")
    or "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py"
)
_lock = threading.Lock()


def init(config: dict | None = None) -> None:
    """Initialize AI advisor from config.  Call once at session start."""
    global _ENABLED, _MODEL, _CONFIG, _TRADES_PATH
    global _CODEX_ENABLED, _CODEX_CONFIG, _CODEX_MODEL, _CODEX_BIN
    ai_cfg = (config or {}).get("ai") or {}
    _CODEX_ENABLED = False
    _CODEX_CONFIG = {}
    _CODEX_MODEL = "gpt-5"
    _CODEX_BIN = "codex"
    if not ai_cfg.get("enabled", False):
        _ENABLED = False
        return
    # Verify claude orchestration wrapper and claude CLI are available
    if not _CLX_BIN.exists() or not shutil.which("claude"):
        _ENABLED = False
        return
    _MODEL = str(ai_cfg.get("model", "haiku"))
    _CONFIG = ai_cfg
    # Resolve trades path from config
    logging_cfg = (config or {}).get("logging") or {}
    _tc = logging_cfg.get("trades_csv", "logs/trades.csv")
    _base = Path(__file__).parent.parent
    _TRADES_PATH = _base / _tc if not Path(_tc).is_absolute() else Path(_tc)
    codex_cfg = ai_cfg.get("codex") or {}
    _CODEX_CONFIG = codex_cfg if isinstance(codex_cfg, dict) else {}
    _CODEX_MODEL = str(_CODEX_CONFIG.get("model", "gpt-5"))
    _CODEX_BIN = str(_CODEX_CONFIG.get("cli_bin", "codex"))
    if bool(_CODEX_CONFIG.get("enabled", False)) and shutil.which(_CODEX_BIN):
        _CODEX_ENABLED = True
    _ENABLED = True


def is_enabled() -> bool:
    return _ENABLED


def is_codex_enabled() -> bool:
    """True when Codex peer advisor is configured and CLI is available."""
    return _ENABLED and _CODEX_ENABLED


# ── Low-level CLI call ──────────────────────────────────────────────

def _call_claude(prompt: str, timeout: int = 45) -> str | None:
    """Call Claude via clx wrapper. Returns stdout or None on failure."""
    _log_path = Path(__file__).parent.parent / "logs" / "ai_debug.log"
    try:
        env = os.environ.copy()
        # Remove nesting-detection vars so Claude CLI runs cleanly
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CODE", None)
        env.pop("DISABLE_CLAUDE_CODE", None)
        _t0 = time.time()
        cmd = [
            sys.executable,
            str(_CLX_BIN),
            "--raw",
            "--mode",
            "execute",
            "--output-format",
            "text",
            "--model",
            _MODEL,
            prompt,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        _elapsed = time.time() - _t0
        with open(_log_path, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] model={_MODEL} rc={result.returncode} elapsed={_elapsed:.1f}s stdout={result.stdout[:200]!r} stderr={result.stderr[:200]!r}\n")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except subprocess.TimeoutExpired:
        with open(_log_path, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] TIMEOUT after {timeout}s\n")
    except Exception as exc:
        with open(_log_path, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {exc}\n")
    return None


def _parse_json(raw: str | None) -> dict:
    """Extract JSON object from Claude response.  Returns {} on failure."""
    if not raw:
        return {}
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        # Find first { ... } block
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def _to_float(value: Any, default: float = 0.0) -> float:
    """Best-effort float conversion for confidence/threshold fields."""
    try:
        return float(value)
    except Exception:
        return default


def _normalize_directive(raw: dict | None) -> dict | None:
    """Normalize and validate directive payload shape."""
    if not isinstance(raw, dict):
        return None
    action = str(raw.get("action", "")).upper().strip()
    if action not in _ALLOWED_ACTIONS:
        return None
    d = dict(raw)
    d["action"] = action
    return d


# ── Cache read/write ────────────────────────────────────────────────

def _read_cache() -> dict:
    """Read the full cache file.  Returns {} on any error."""
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text())
    except Exception:
        pass
    return {}


def _write_cache(trigger: str, result: dict, ttl: int) -> None:
    """Atomically merge a trigger result into the cache file."""
    with _lock:
        cache = _read_cache()
        cache[trigger] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_ts": time.time() + ttl,
        }
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, indent=2))
        tmp.replace(_CACHE_PATH)


def get_cached_insight(trigger: str) -> dict | None:
    """Read latest cached result for a trigger type.  Returns None if expired/missing."""
    cache = _read_cache()
    entry = cache.get(trigger)
    if not entry:
        return None
    # TTL 0 means "always valid until overwritten"
    expires = entry.get("expires_ts", 0)
    if expires > 0 and time.time() > expires:
        return None
    return entry.get("result")


# ── Background thread launcher ──────────────────────────────────────

def _fire_background(trigger: str, prompt: str, cache_ttl: int = 180) -> None:
    """Spawn a fully detached subprocess to call Claude and write cache.

    The bot process exits after each cycle (~3-5s), but Opus takes ~30-45s.
    Daemon threads die with the process, so we use a detached Python subprocess
    that survives independently and writes results to the cache file.
    """
    _log_path = Path(__file__).parent.parent / "logs" / "ai_debug.log"
    if not _ENABLED:
        return

    # Write prompt to a temp file (avoid shell escaping issues with long prompts)
    _base = Path(__file__).parent.parent
    prompt_file = _base / "data" / f".ai_prompt_{trigger}.txt"
    prompt_file.write_text(prompt)

    # Build a small Python script that runs detached
    worker_script = f'''
import json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

log = Path("{_log_path}")
cache_path = Path("{_CACHE_PATH}")
prompt_file = Path("{prompt_file}")
trigger = "{trigger}"
ttl = {cache_ttl}
model = "{_MODEL}"
clx_bin = {json.dumps(str(_CLX_BIN))}

def _log(msg):
    with open(log, "a") as f:
        f.write(f"[{{datetime.now(timezone.utc).isoformat()}}] {{msg}}\\n")

try:
    prompt = prompt_file.read_text()
    _log(f"FIRE {{trigger}} prompt_len={{len(prompt)}}")
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE", None)
    t0 = time.time()
    cmd = [
        sys.executable,
        clx_bin,
        "--raw",
        "--mode",
        "execute",
        "--output-format",
        "text",
        "--model",
        model,
        prompt,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
    elapsed = time.time() - t0
    _log(f"CLI {{trigger}} rc={{result.returncode}} elapsed={{elapsed:.1f}}s stdout={{result.stdout[:150]!r}}")
    raw = result.stdout.strip() if result.returncode == 0 else None
    if raw:
        cleaned = re.sub(r"```(?:json)?\\s*", "", raw).strip().rstrip("`")
        start = cleaned.find("{{")
        end = cleaned.rfind("}}")
        if start >= 0 and end > start:
            parsed = json.loads(cleaned[start:end+1])
            # Atomic write to cache
            import threading
            cache = {{}}
            if cache_path.exists():
                try: cache = json.loads(cache_path.read_text())
                except: pass
            cache[trigger] = {{
                "result": parsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expires_ts": time.time() + ttl,
            }}
            tmp = cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, indent=2))
            tmp.replace(cache_path)
            _log(f"DONE {{trigger}} keys={{list(parsed.keys())}}")
        else:
            _log(f"DONE {{trigger}} NO_JSON")
    else:
        _log(f"DONE {{trigger}} EMPTY (rc={{result.returncode}} stderr={{result.stderr[:100]!r}})")
except subprocess.TimeoutExpired:
    _log(f"TIMEOUT {{trigger}} after 90s")
except Exception as exc:
    _log(f"ERROR {{trigger}} {{exc}}")
finally:
    prompt_file.unlink(missing_ok=True)
'''

    # Launch as fully detached subprocess (survives bot exit)
    try:
        subprocess.Popen(
            [sys.executable, "-c", worker_script],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        with open(_log_path, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] LAUNCH_ERROR {trigger} {exc}\n")


def _fire_background_codex(trigger: str, prompt: str, cache_ttl: int = 180) -> None:
    """Spawn detached subprocess to call Codex CLI and cache JSON output.

    Codex is a peer advisor only. It never directly places orders. Output is
    stored under codex_* cache keys and consumed as metadata by get_directive().
    """
    _log_path = Path(__file__).parent.parent / "logs" / "ai_debug.log"
    if not _ENABLED or not _CODEX_ENABLED:
        return

    _base = Path(__file__).parent.parent
    prompt_file = _base / "data" / f".ai_prompt_{trigger}.txt"
    output_file = _base / "data" / f".ai_output_{trigger}.txt"
    prompt_file.write_text(prompt)
    output_file.unlink(missing_ok=True)

    _sandbox = str(_CODEX_CONFIG.get("sandbox_mode", "read-only")).strip() or "read-only"
    _timeout = int(_CODEX_CONFIG.get("timeout_sec", 60) or 60)
    _model = str(_CODEX_MODEL or "").strip()
    cmd = [
        _CODEX_BIN,
        "exec",
        "--sandbox",
        _sandbox,
        "--skip-git-repo-check",
        "--output-last-message",
        str(output_file),
    ]
    if _model:
        cmd.extend(["--model", _model])
    cmd.append("-")

    worker_script = f'''
import json, os, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

log = Path("{_log_path}")
cache_path = Path("{_CACHE_PATH}")
prompt_file = Path("{prompt_file}")
output_file = Path("{output_file}")
trigger = "{trigger}"
ttl = {cache_ttl}
timeout_sec = {_timeout}
cmd = {json.dumps(cmd)}

def _log(msg):
    with open(log, "a") as f:
        f.write(f"[{{datetime.now(timezone.utc).isoformat()}}] {{msg}}\\n")

try:
    prompt = prompt_file.read_text()
    _log(f"FIRE_CODEX {{trigger}} prompt_len={{len(prompt)}} cmd={{cmd[:4]}}")
    env = os.environ.copy()
    t0 = time.time()
    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
    )
    elapsed = time.time() - t0
    _log(
        f"CLI_CODEX {{trigger}} rc={{result.returncode}} elapsed={{elapsed:.1f}}s "
        f"stdout={{result.stdout[:120]!r}} stderr={{result.stderr[:120]!r}}"
    )
    raw = output_file.read_text().strip() if output_file.exists() else ""
    if not raw and result.stdout.strip():
        raw = result.stdout.strip()
    if raw:
        cleaned = re.sub(r"```(?:json)?\\s*", "", raw).strip().rstrip("`")
        start = cleaned.find("{{")
        end = cleaned.rfind("}}")
        if start >= 0 and end > start:
            parsed = json.loads(cleaned[start:end+1])
            cache = {{}}
            if cache_path.exists():
                try:
                    cache = json.loads(cache_path.read_text())
                except Exception:
                    cache = {{}}
            cache[trigger] = {{
                "result": parsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expires_ts": time.time() + ttl,
            }}
            tmp = cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, indent=2))
            tmp.replace(cache_path)
            _log(f"DONE_CODEX {{trigger}} keys={{list(parsed.keys())}}")
        else:
            _log(f"DONE_CODEX {{trigger}} NO_JSON")
    else:
        _log(f"DONE_CODEX {{trigger}} EMPTY")
except subprocess.TimeoutExpired:
    _log(f"TIMEOUT_CODEX {{trigger}} after {{timeout_sec}}s")
except Exception as exc:
    _log(f"ERROR_CODEX {{trigger}} {{exc}}")
finally:
    prompt_file.unlink(missing_ok=True)
    output_file.unlink(missing_ok=True)
'''

    try:
        subprocess.Popen(
            [sys.executable, "-c", worker_script],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        with open(_log_path, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] LAUNCH_ERROR_CODEX {trigger} {exc}\n")


# ── Public API ──────────────────────────────────────────────────────

def evaluate_entry(
    decision: dict,
    state: dict,
    df_15m: pd.DataFrame | None = None,
    df_1h: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion_state: dict | None = None,
) -> None:
    """Fire background entry evaluation with full chart context.  Non-blocking."""
    if not _ENABLED or not _CONFIG.get("pre_entry_enabled", True):
        return
    signal = {
        "direction": decision.get("direction"),
        "entry_type": decision.get("entry_signal"),
        "regime": decision.get("v4_regime"),
        "vol_phase": decision.get("vol_phase"),
        "score": decision.get("v4_selected_score"),
        "threshold": decision.get("v4_selected_threshold"),
        "quality_tier": decision.get("quality_tier"),
        "lane": decision.get("lane_label"),
        "regime_name": decision.get("regime_name"),
        "consecutive_losses": decision.get("consecutive_losses", 0),
        "consecutive_wins": decision.get("consecutive_wins", 0),
        "pnl_today_usd": decision.get("pnl_today_usd", 0),
        "trades_today": decision.get("trades_today", 0),
        "losses_today": decision.get("losses_today", 0),
        "recovery_mode": decision.get("recovery_mode", "NORMAL"),
        "htf_macro_bias": decision.get("htf_macro_bias"),
        "btc_trend": decision.get("btc_trend"),
    }
    price = float(decision.get("price") or 0)
    prompt = entry_prompt(
        signal=signal,
        candles_15m=df_15m,
        candles_1h=df_1h,
        regime_v4=regime_v4,
        expansion=expansion_state,
        trades_path=_TRADES_PATH,
        price=price,
    )
    ttl = int(_CONFIG.get("cache_ttl_entry", 0))
    _fire_background("entry_eval", prompt, cache_ttl=ttl)
    if _CODEX_ENABLED and bool(_CODEX_CONFIG.get("pre_entry_enabled", True)):
        _ttl_codex = int(_CODEX_CONFIG.get("cache_ttl_entry", ttl))
        _fire_background_codex("codex_entry_eval", prompt, cache_ttl=_ttl_codex)


def evaluate_exit(
    open_pos: dict,
    tick_data: dict,
    df_15m: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion_state: dict | None = None,
) -> None:
    """Fire background exit evaluation with live chart context.  Non-blocking."""
    if not _ENABLED or not _CONFIG.get("exit_advisor_enabled", True):
        return
    position = {
        "direction": open_pos.get("direction"),
        "entry_type": open_pos.get("entry_type"),
        "entry_price": open_pos.get("entry_price"),
        "strategy_regime": open_pos.get("strategy_regime"),
        "current_price": tick_data.get("price"),
        "pnl_usd_live": tick_data.get("pnl_usd_live"),
        "pnl_pct": tick_data.get("pnl_pct"),
        "max_unrealized_usd": tick_data.get("max_unrealized_usd"),
        "giveback_usd": tick_data.get("giveback_usd"),
        "bars_since_entry": tick_data.get("bars_since_entry"),
        "score_self": tick_data.get("score_self"),
        "score_opp": tick_data.get("score_opp"),
        "regime": tick_data.get("regime"),
    }
    price = float(tick_data.get("price") or 0)
    prompt = exit_prompt(
        position=position,
        candles_15m=df_15m,
        regime_v4=regime_v4,
        expansion=expansion_state,
        price=price,
    )
    ttl = int(_CONFIG.get("cache_ttl_exit", 120))
    _fire_background("exit_eval", prompt, cache_ttl=ttl)
    if _CODEX_ENABLED and bool(_CODEX_CONFIG.get("exit_advisor_enabled", True)):
        _ttl_codex = int(_CODEX_CONFIG.get("cache_ttl_exit", ttl))
        _fire_background_codex("codex_exit_eval", prompt, cache_ttl=_ttl_codex)


def evaluate_regime(
    regime_data: dict,
    df_1h: pd.DataFrame | None = None,
) -> None:
    """Fire background regime transition evaluation.  Non-blocking."""
    if not _ENABLED or not _CONFIG.get("regime_advisor_enabled", True):
        return
    prompt = regime_prompt(
        regime_data=regime_data,
        candles_1h=df_1h,
    )
    ttl = int(_CONFIG.get("cache_ttl_regime", 300))
    _fire_background("regime_eval", prompt, cache_ttl=ttl)
    if _CODEX_ENABLED and bool(_CODEX_CONFIG.get("regime_advisor_enabled", True)):
        _ttl_codex = int(_CODEX_CONFIG.get("cache_ttl_regime", ttl))
        _fire_background_codex("codex_regime_eval", prompt, cache_ttl=_ttl_codex)


# ── Macro News via Perplexity ──────────────────────────────────────

_NEWS_CACHE: dict = {"text": None, "expires": 0}
_NEWS_CACHE_TTL = 900  # 15 minutes — macro news doesn't change every 30s

def _fetch_macro_news() -> str | None:
    """Fetch macro market news via Claude CLI web search. Cached 15 min.

    Uses Haiku with WebSearch tool — free, fast, and always-authenticated
    via the user's existing Claude CLI session. Falls back to Perplexity API
    if available.
    """
    import time as _time
    if _NEWS_CACHE["text"] and _time.time() < _NEWS_CACHE["expires"]:
        return _NEWS_CACHE["text"]
    # Primary: Claude CLI with web search (always works, uses existing auth)
    try:
        _news_prompt = (
            "Give me a BRIEF market snapshot right now (max 150 words, bullet points only):\n"
            "1) Bitcoin price and % change today, crypto market sentiment\n"
            "2) XLM/Stellar price and any specific news\n"
            "3) S&P 500 and NASDAQ levels and % change today\n"
            "4) Any Fed announcements, CPI, jobs data, or major macro news today\n"
            "Just facts and numbers. No opinions."
        )
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
            _news_prompt,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Strip source links — Opus doesn't need URLs
            lines = []
            for line in result.stdout.strip().splitlines():
                if line.startswith("Sources:") or line.startswith("- ["):
                    continue
                lines.append(line)
            text = "\n".join(lines).strip()
            if len(text) > 30:
                _NEWS_CACHE["text"] = text
                _NEWS_CACHE["expires"] = _time.time() + _NEWS_CACHE_TTL
                return text
    except Exception:
        pass  # never let news failure block trading
    # Fallback: Perplexity API (if key is valid)
    try:
        import requests as _req
        _env_file = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        _api_key = None
        if _env_file.exists():
            for line in _env_file.read_text().splitlines():
                if line.startswith("PERPLEXITY_API_KEY="):
                    _api_key = line.split("=", 1)[1].strip()
        if not _api_key:
            _api_key = os.environ.get("PERPLEXITY_API_KEY")
        if _api_key:
            resp = _req.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "Concise market analyst. Factual bullets only. Max 150 words."},
                        {"role": "user", "content": "Latest: 1) BTC price+sentiment 2) XLM news 3) S&P/NASDAQ 4) Fed/macro. Numbers only."},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                _NEWS_CACHE["text"] = text
                _NEWS_CACHE["expires"] = _time.time() + _NEWS_CACHE_TTL
                return text
    except Exception:
        pass
    return _NEWS_CACHE.get("text")  # return stale if both fail


# ── Executive Mode: Master Directive ────────────────────────────────

def is_executive_mode() -> bool:
    """Check if Claude is in executive (decision-making) mode."""
    return _ENABLED and bool(_CONFIG.get("executive_mode", False))


def request_directive(
    status: dict,
    df_15m: pd.DataFrame | None = None,
    df_1h: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion_state: dict | None = None,
    engine_recommendation: dict | None = None,
    price: float = 0.0,
    macro_news: str | None = None,
    peer_intel: dict | None = None,
    lane_perf_path: str | None = None,
) -> None:
    """Fire background master directive request.  Non-blocking.

    This is the ONE call per cycle that asks Claude: what should we do?
    Result cached as 'directive' — read with get_directive().
    """
    if not _ENABLED or not _CONFIG.get("executive_mode", False):
        return
    feedback = get_feedback_summary(15)
    # Multi-timeframe S/R, fib, RSI, MACD, volume + cross-market (BTC, ETH)
    _mtf_text = None
    try:
        from strategy.mtf_levels import compute_mtf_levels, compute_cross_market, format_mtf_for_prompt
        _mtf_data = compute_mtf_levels("XLM-USD")
        _cross = compute_cross_market()
        _mtf_text = format_mtf_for_prompt(_mtf_data, _cross) if _mtf_data else None
    except Exception:
        pass  # never let MTF failure block directive
    # Use macro_news if provided, else fetch (which uses cache)
    if macro_news is None:
        macro_news = _fetch_macro_news()
        
    prompt = master_directive_prompt(
        status=status,
        candles_15m=df_15m,
        candles_1h=df_1h,
        regime_v4=regime_v4,
        expansion=expansion_state,
        trades_path=_TRADES_PATH,
        price=price,
        engine_recommendation=engine_recommendation,
        feedback=feedback,
        mtf_levels=_mtf_text,
        macro_news=macro_news,
        peer_intel=peer_intel,
        lane_perf_path=lane_perf_path,
    )
    # Post assessment to agent_comms board for inter-agent debate
    try:
        from ai import agent_comms as _ac
        if _ac.is_enabled():
            _ac.post_assessment("claude", {
                "action": engine_recommendation.get("direction") if engine_recommendation else "FLAT",
                "confidence": 0.5,
                "reasoning": "Pre-directive assessment based on engine recommendation",
                "regime": (regime_v4 or {}).get("regime", "unknown"),
            })
    except Exception:
        pass
    # Directive TTL: short because we fire every cycle
    ttl = int(_CONFIG.get("cache_ttl_directive", 60))
    _fire_background("directive", prompt, cache_ttl=ttl)
    if _CODEX_ENABLED and bool(_CODEX_CONFIG.get("executive_mode", True)):
        _ttl_codex = int(_CODEX_CONFIG.get("cache_ttl_directive", ttl))
        _fire_background_codex("codex_directive", prompt, cache_ttl=_ttl_codex)


def get_directive() -> dict | None:
    """Read Claude's most recent executive directive.

    Returns dict with keys:
        action: ENTER_LONG | ENTER_SHORT | EXIT | HOLD | FLAT
        confidence: 0.0-1.0
        stop_loss_price: float (for entries)
        take_profit_price: float (for entries, optional)
        reasoning: str
        market_read: str
    Returns None if no valid directive cached.
    """
    d = _normalize_directive(get_cached_insight("directive"))
    if not d:
        return None

    # Codex is advisory only: enrich Claude directive with peer signal metadata.
    # Claude remains the sole trading authority.
    codex_d = _normalize_directive(get_cached_insight("codex_directive")) if _CODEX_ENABLED else None
    if codex_d:
        d["peer_codex_action"] = codex_d.get("action")
        d["peer_codex_confidence"] = _to_float(codex_d.get("confidence"), 0.0)
        d["peer_codex_reasoning"] = str(codex_d.get("reasoning", ""))[:180]
        d["peer_agreement"] = bool(codex_d.get("action") == d.get("action"))
    return d


def get_codex_directive() -> dict | None:
    """Read Codex peer directive if available and valid."""
    if not _CODEX_ENABLED:
        return None
    return _normalize_directive(get_cached_insight("codex_directive"))


# ── Self-Learning Feedback Loop ──────────────────────────────────────

_FEEDBACK_PATH: Path = Path(__file__).parent.parent / "data" / "ai_feedback.jsonl"


def log_directive_outcome(
    directive: dict,
    trade_result: dict,
) -> None:
    """Log what Claude decided vs what actually happened.

    Called after each trade closes.  Builds up a feedback log that gets
    fed back into the prompt so Claude can learn from its own decisions.
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        # What Claude said
        "action": directive.get("action"),
        "confidence": directive.get("confidence"),
        "reasoning": directive.get("reasoning", "")[:200],
        "market_read": directive.get("market_read", "")[:150],
        "sl_price": directive.get("stop_loss_price"),
        "tp_price": directive.get("take_profit_price"),
        "ai_size": directive.get("size"),
        # What actually happened
        "direction": trade_result.get("direction"),
        "entry_price": trade_result.get("entry_price"),
        "exit_price": trade_result.get("exit_price"),
        "pnl_usd": trade_result.get("pnl_usd"),
        "duration_min": trade_result.get("duration_min"),
        "exit_reason": trade_result.get("exit_reason"),
        "max_unrealized": trade_result.get("max_unrealized"),
        # Verdict
        "won": bool(float(trade_result.get("pnl_usd") or 0) > 0),
    }
    try:
        with open(_FEEDBACK_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    # Ingest to Blinko knowledge base (fire-and-forget)
    try:
        _blinko_bridge = Path(__file__).parent.parent.parent.parent / (
            "03_AUTOMATION_CORE/01_Scripts/ai_workers/blinko_bridge.py"
        )
        if _blinko_bridge.exists():
            subprocess.Popen(
                [sys.executable, str(_blinko_bridge), "ingest-trade", json.dumps(entry)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except Exception:
        pass


def log_flat_outcome(
    directive: dict,
    price_at_flat: float,
    price_after: float,
    minutes_later: int = 30,
) -> None:
    """Log when Claude said FLAT — did it miss a move or correctly stay out?

    Called periodically when Claude's been saying FLAT to track whether
    staying out was the right call.
    """
    move_pct = ((price_after - price_at_flat) / price_at_flat * 100) if price_at_flat else 0
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": "FLAT",
        "confidence": directive.get("confidence"),
        "reasoning": directive.get("reasoning", "")[:200],
        "price_at_flat": price_at_flat,
        "price_after": price_after,
        "minutes_later": minutes_later,
        "move_pct": round(move_pct, 3),
        "missed_move": abs(move_pct) > 0.3,  # >0.3% move = missed opportunity
    }
    try:
        with open(_FEEDBACK_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_feedback_summary(n: int = 15) -> list[dict]:
    """Read last N feedback entries for prompt injection."""
    try:
        if not _FEEDBACK_PATH.exists():
            return []
        lines = _FEEDBACK_PATH.read_text().strip().split("\n")
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return entries
    except Exception:
        return []
