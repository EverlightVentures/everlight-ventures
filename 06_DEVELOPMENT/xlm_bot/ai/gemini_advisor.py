"""Gemini AI trade intelligence advisor.

Fire-and-forget background calls to Gemini CLI. Results cached to
data/ai_insight.json and read on the NEXT bot cycle.

Acts as a peer advisor to Claude, providing a second opinion, longer
context analysis, or specialized tasks.
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
_MODEL: str = "gemini-1.5-pro-latest"
_GEMINI_BIN: str = "/root/.local/bin/gemini"
_GMX_BIN: Path = Path(
    os.environ.get("GMX_DELEGATE_BIN")
    or "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py"
)
_CONFIG: dict = {}
_lock = threading.Lock()


def init(config: dict | None = None) -> None:
    """Initialize Gemini advisor from config."""
    global _ENABLED, _MODEL, _GEMINI_BIN, _CONFIG, _TRADES_PATH
    ai_cfg = (config or {}).get("ai") or {}
    gemini_cfg = ai_cfg.get("gemini") or {}
    
    # Default to enabled if gemini CLI is present, unless explicitly disabled
    if not gemini_cfg.get("enabled", True):
        _ENABLED = False
        return
        
    # Verify orchestrator wrapper and Gemini CLI are available.
    if not _GMX_BIN.exists():
        _ENABLED = False
        return
    if not shutil.which(_GEMINI_BIN):
        # Try finding it in path if absolute path fails.
        _GEMINI_BIN = shutil.which("gemini") or _GEMINI_BIN
        if not shutil.which(_GEMINI_BIN):
            _ENABLED = False
            return

    _MODEL = str(gemini_cfg.get("model", "gemini-1.5-pro-latest"))
    _CONFIG = gemini_cfg
    _ENABLED = True
    
    # Resolve trades path from config
    logging_cfg = (config or {}).get("logging") or {}
    _tc = logging_cfg.get("trades_csv", "logs/trades.csv")
    _base = Path(__file__).parent.parent
    _TRADES_PATH = _base / _tc if not Path(_tc).is_absolute() else Path(_tc)


def is_enabled() -> bool:
    return _ENABLED


def _read_cache() -> dict:
    """Read the full cache file. Returns {} on any error."""
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text())
    except Exception:
        pass
    return {}


def get_cached_insight(trigger: str) -> dict | None:
    """Read latest cached result for a trigger type."""
    cache = _read_cache()
    entry = cache.get(trigger)
    if not entry:
        return None
    expires = entry.get("expires_ts", 0)
    if expires > 0 and time.time() > expires:
        return None
    return entry.get("result")


def _fire_background_gemini(trigger: str, prompt: str, cache_ttl: int = 180) -> None:
    """Spawn detached subprocess to call Gemini CLI."""
    _log_path = Path(__file__).parent.parent / "logs" / "ai_debug.log"
    if not _ENABLED:
        return

    _base = Path(__file__).parent.parent
    prompt_file = _base / "data" / f".gemini_prompt_{trigger}.txt"
    # Write prompt to temp file
    prompt_file.write_text(prompt)

    # We use a worker script to run detached
    worker_script = f'''
import json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

log = Path("{_log_path}")
cache_path = Path("{_CACHE_PATH}")
prompt_file = Path("{prompt_file}")
trigger = "{trigger}"
ttl = {cache_ttl}
gmx_bin = {json.dumps(str(_GMX_BIN))}
model = "{_MODEL}"

def _log(msg):
    with open(log, "a") as f:
        f.write(f"[{{datetime.now(timezone.utc).isoformat()}}] {{msg}}
")

try:
    prompt = prompt_file.read_text()
    _log(f"FIRE_GEMINI {{trigger}} prompt_len={{len(prompt)}}")
    
    cmd = [
        sys.executable,
        gmx_bin,
        "--raw",
        "--mode",
        "execute",
        "--output-format",
        "text",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)

    t0 = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=90,
    )
    elapsed = time.time() - t0
    
    # stdout should be the raw response (hopefully JSON)
    # stderr might have "Loaded cached credentials"
    _log(f"CLI_GEMINI {{trigger}} rc={{result.returncode}} elapsed={{elapsed:.1f}}s")
    
    raw = result.stdout.strip()
    if raw:
        # Try to parse JSON from the output. It might be wrapped in markdown blocks.
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
            
            # Use 'gemini_' prefix for triggers in the shared cache file
            key = f"gemini_{{trigger}}" if not trigger.startswith("gemini_") else trigger
            
            cache[key] = {{
                "result": parsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expires_ts": time.time() + ttl,
            }}
            tmp = cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, indent=2))
            tmp.replace(cache_path)
            _log(f"DONE_GEMINI {{trigger}} keys={{list(parsed.keys())}}")
        else:
            _log(f"DONE_GEMINI {{trigger}} NO_JSON in {{raw[:100]!r}}")
    else:
        _log(f"DONE_GEMINI {{trigger}} EMPTY (stderr={{result.stderr[:100]!r}})")

except subprocess.TimeoutExpired:
    _log(f"TIMEOUT_GEMINI {{trigger}} after 90s")
except Exception as exc:
    _log(f"ERROR_GEMINI {{trigger}} {{exc}}")
finally:
    prompt_file.unlink(missing_ok=True)
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
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] LAUNCH_ERROR_GEMINI {trigger} {exc}\n")


# ── Public API ──────────────────────────────────────────────────────

def evaluate_entry(
    decision: dict,
    state: dict,
    df_15m: pd.DataFrame | None = None,
    df_1h: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion_state: dict | None = None,
) -> None:
    """Fire background entry evaluation."""
    if not _ENABLED or not _CONFIG.get("pre_entry_enabled", True):
        return
        
    # Re-use the prompt logic from ai.prompts (designed for Claude but works for Gemini)
    signal = {
        "direction": decision.get("direction"),
        "entry_type": decision.get("entry_signal"),
        "regime": decision.get("v4_regime"),
        "vol_phase": decision.get("vol_phase"),
        "score": decision.get("v4_selected_score"),
        "threshold": decision.get("v4_selected_threshold"),
        "lane": decision.get("lane_label"),
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
    ttl = int(_CONFIG.get("cache_ttl_entry", 180))
    _fire_background_gemini("entry_eval", prompt, cache_ttl=ttl)


def evaluate_exit(
    open_pos: dict,
    tick_data: dict,
    df_15m: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion_state: dict | None = None,
) -> None:
    """Fire background exit evaluation."""
    if not _ENABLED or not _CONFIG.get("exit_advisor_enabled", True):
        return

    position = {
        "direction": open_pos.get("direction"),
        "entry_type": open_pos.get("entry_type"),
        "entry_price": open_pos.get("entry_price"),
        "current_price": tick_data.get("price"),
        "pnl_usd_live": tick_data.get("pnl_usd_live"),
        "pnl_pct": tick_data.get("pnl_pct"),
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
    _fire_background_gemini("exit_eval", prompt, cache_ttl=ttl)


def evaluate_regime(
    regime_data: dict,
    df_1h: pd.DataFrame | None = None,
) -> None:
    """Fire background regime evaluation."""
    if not _ENABLED or not _CONFIG.get("regime_advisor_enabled", True):
        return
    prompt = regime_prompt(
        regime_data=regime_data,
        candles_1h=df_1h,
    )
    ttl = int(_CONFIG.get("cache_ttl_regime", 300))
    _fire_background_gemini("regime_eval", prompt, cache_ttl=ttl)


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
    """Fire background master directive request (Peer opinion)."""
    if not _ENABLED or not _CONFIG.get("executive_mode", True):
        return

    prompt = master_directive_prompt(
        status=status,
        candles_15m=df_15m,
        candles_1h=df_1h,
        regime_v4=regime_v4,
        expansion=expansion_state,
        trades_path=_TRADES_PATH,
        price=price,
        engine_recommendation=engine_recommendation,
        macro_news=macro_news,
        peer_intel=peer_intel,
        lane_perf_path=lane_perf_path,
    )
    # Post Gemini's assessment to agent_comms for inter-agent debate
    try:
        from ai import agent_comms as _ac
        if _ac.is_enabled():
            _ac.post_assessment("gemini", {
                "action": (engine_recommendation or {}).get("direction", "FLAT"),
                "confidence": 0.5,
                "reasoning": "Pre-directive Gemini risk assessment",
                "regime": (regime_v4 or {}).get("regime", "unknown"),
            })
    except Exception:
        pass
    ttl = int(_CONFIG.get("cache_ttl_directive", 60))
    _fire_background_gemini("directive", prompt, cache_ttl=ttl)


def get_directive() -> dict | None:
    """Read Gemini's most recent directive."""
    if not _ENABLED:
        return None
    return get_cached_insight("gemini_directive")


def audit_decision(
    decision: dict,
    state: dict,
    price: float = 0.0,
) -> None:
    """Audit a proposed decision for risk/math correctness. Fire-and-forget."""
    if not _ENABLED:
        return
        
    prompt = (
        "You are the Risk & Math Officer for an automated trading bot.\n"
        "Audit the following proposed trade decision against risk parameters.\n\n"
        "PROPOSAL:\n"
        f"{json.dumps(decision, indent=2)}\n\n"
        "ACCOUNT STATE:\n"
        f"Equity: {state.get('equity_usd', '?')}\n"
        f"PnL Today: {state.get('pnl_today_usd', '?')}\n"
        f"Trades Today: {state.get('trades_today', '?')}\n"
        f"Losses Today: {state.get('losses_today', '?')}\n"
        f"Current Price: {price}\n\n"
        "RULES:\n"
        "- Max daily loss: 10% of equity\n"
        "- Max trades/day: 8\n"
        "- Max losses/day: 5\n"
        "- Size limits: Max 5 contracts. Reduce size after 2 consecutive losses.\n"
        "- Cooldown: 10 mins mandatory after any loss.\n\n"
        "Respond ONLY with valid JSON (Risk Math Report):\n"
        "{\n"
        '  "account_equity": float,\n'
        '  "max_risk_per_trade": float (usd),\n'
        '  "current_exposure": float (usd),\n'
        '  "recommended_size": int (contracts),\n'
        '  "recovery_mode": "OFF" or "SEMI_AGGRESSIVE",\n'
        '  "recovery_cap_rules": "string summary",\n'
        '  "status": "OK" or "VIOLATION",\n'
        '  "reason": "explanation"\n'
        "}"
    )
    ttl = 60
    _fire_background_gemini("audit_decision", prompt, cache_ttl=ttl)


def get_audit_result() -> dict | None:
    """Read latest risk audit result."""
    if not _ENABLED:
        return None
    return get_cached_insight("gemini_audit_decision")
