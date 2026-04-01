"""AI Chat server for the XLM trading dashboard.

Runs on port 8504 in a background thread. The floating chat widget
in dashboard.py talks to this via fetch().

Uses OpenAI API (gpt-4o-mini) as the primary provider. Falls back to
Anthropic or delegate subprocess if OpenAI is unavailable.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import threading

LOGS_DIR = Path(__file__).parent / "logs"
TRADES_PATH = LOGS_DIR / "trades.csv"
_BASE_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _BASE_DIR.parent

_CHAT_SERVER: ThreadingHTTPServer | None = None


class _ReusableHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _health_candidates(host: str, port: int) -> list[str]:
    seen: list[str] = []
    for candidate in ("127.0.0.1", host):
        clean = str(candidate or "").strip()
        if not clean or clean == "0.0.0.0":
            clean = "127.0.0.1"
        if clean not in seen:
            seen.append(clean)
    return [f"http://{candidate}:{port}/health" for candidate in seen]


def _chat_server_alive(host: str, port: int) -> bool:
    for url in _health_candidates(host, port):
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if int(getattr(response, "status", 0) or 0) == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
    return False


def _read_bot_context() -> str:
    """Read latest bot state from dashboard snapshot."""
    snap_path = LOGS_DIR / "dashboard_snapshot.json"
    try:
        raw = json.loads(snap_path.read_text())
        d = raw[0] if isinstance(raw, list) and raw else raw
    except Exception:
        return "(no bot state available)"

    parts = []
    parts.append(f"Price: {d.get('price')}")
    parts.append(f"State: {d.get('state')}")
    parts.append(f"Regime: {d.get('regime')}")
    parts.append(f"Vol Phase: {d.get('vol_phase')} | Dir: {d.get('vol_direction')} | Conf: {d.get('vol_confidence')}")
    parts.append(f"Gates Pass: {d.get('gates_pass')}")
    gates = d.get("gates") or {}
    if isinstance(gates, dict):
        failed = [k for k, v in gates.items() if not bool(v)]
        parts.append(f"Failed Gates: {failed or 'none'}")
    parts.append(f"Route Tier: {d.get('route_tier')}")
    parts.append(f"Entry Signal: {d.get('entry_signal')}")
    parts.append(f"Direction: {d.get('direction')}")
    parts.append(f"Score: {d.get('v4_score')}/{d.get('v4_threshold')}")
    parts.append(f"Quality Tier: {d.get('quality_tier')}")
    parts.append(f"Lane: {d.get('lane')} ({d.get('lane_label')})")
    parts.append(f"Entry Type Long: {d.get('entry_type_long')}")
    parts.append(f"Entry Type Short: {d.get('entry_type_short')}")
    parts.append(f"Long Score: {d.get('v4_score_long')}/{d.get('v4_threshold_long')}")
    parts.append(f"Short Score: {d.get('v4_score_short')}/{d.get('v4_threshold_short')}")
    parts.append(f"Long Block: {d.get('long_block_reason')}")
    parts.append(f"Short Block: {d.get('short_block_reason')}")
    parts.append(f"Reason: {d.get('reason')}")
    parts.append(f"Cooldown: {d.get('cooldown')}")
    parts.append(f"Trades Today: {d.get('trades_today')} | Losses: {d.get('losses_today')}")
    parts.append(f"P&L Today: ${float(d.get('pnl_today_usd') or 0):.2f}")
    ul = d.get("long_unlock_hints") or []
    us = d.get("short_unlock_hints") or []
    if ul:
        parts.append(f"Long Unlock Hints: {', '.join(str(h) for h in ul)}")
    if us:
        parts.append(f"Short Unlock Hints: {', '.join(str(h) for h in us)}")
    return "\n".join(parts)


def _read_recent_trades(n: int = 5) -> str:
    """Read last N closed trades from trades.csv for context."""
    if not TRADES_PATH.exists():
        return "(no trade history available)"
    try:
        rows = []
        with open(TRADES_PATH, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("pnl_usd") and row.get("entry_price"):
                    rows.append(row)
        if not rows:
            return "(no closed trades yet)"
        recent = rows[-n:]
        lines = []
        for i, t in enumerate(recent, 1):
            pnl = float(t.get("pnl_usd") or 0)
            result = "WIN" if pnl >= 0 else "LOSS"
            lines.append(
                f"  {i}. {t.get('side', '?').upper()} | "
                f"Entry: {t.get('entry_price', '?')} -> Exit: {t.get('exit_price', '?')} | "
                f"PnL: ${pnl:.2f} ({result}) | "
                f"Lane: {t.get('lane', '?')} | "
                f"Exit: {t.get('exit_reason', '?')} | "
                f"Time: {t.get('entry_time', '?')[:16] if t.get('entry_time') else '?'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"(trade history read error: {str(e)[:80]})"


def _read_market_intel() -> str:
    """Read market intel from available log files."""
    parts = []

    # Live tick data
    tick_path = LOGS_DIR / "live_tick.json"
    try:
        if tick_path.exists():
            tick = json.loads(tick_path.read_text())
            parts.append(f"Live Price: ${tick.get('price', '?')}")
            parts.append(f"Bid: {tick.get('bid', '?')} | Ask: {tick.get('ask', '?')}")
            parts.append(f"Spread: {tick.get('spread', '?')}")
    except Exception:
        pass

    # Anomalies
    anom_path = LOGS_DIR / "anomalies.json"
    try:
        if anom_path.exists():
            anom = json.loads(anom_path.read_text())
            if isinstance(anom, dict) and anom:
                active = [k for k, v in anom.items() if v]
                if active:
                    parts.append(f"Active Anomalies: {', '.join(active)}")
                else:
                    parts.append("Anomalies: none active")
    except Exception:
        pass

    # Approval status
    appr_path = LOGS_DIR / "approval_status.json"
    try:
        if appr_path.exists():
            appr = json.loads(appr_path.read_text())
            if isinstance(appr, dict):
                parts.append(f"Approval: {appr.get('status', '?')} | Reason: {appr.get('reason', '?')}")
    except Exception:
        pass

    return "\n".join(parts) if parts else "(no market intel available)"


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:300]}") from exc


def _call_openai(system_prompt: str, user_message: str, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI Chat Completions API directly."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    payload = {
        "model": model,
        "max_tokens": 600,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        payload,
    )
    choices = data.get("choices") or []
    if not choices:
        return "(empty response from OpenAI)"
    message = choices[0].get("message") or {}
    return str(message.get("content", "")).strip()


def _call_anthropic(system_prompt: str, user_message: str, model: str = "claude-haiku-4-5-20251001") -> str:
    """Fallback: call Anthropic API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    payload = {
        "model": model,
        "max_tokens": 600,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        payload,
    )
    parts = data.get("content") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    return text.strip()


class _ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "service": "wolf_chat_api", "engine": "openai"}).encode())
            return
        self.send_error(404)

    def do_POST(self):
        if self.path == "/ask":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            question = str(body.get("question", "")).strip()
            history = body.get("history", "")

            # Build rich context
            bot_state = _read_bot_context()
            recent_trades = _read_recent_trades(5)
            market_intel = _read_market_intel()

            system_prompt = (
                "You are The Wolf -- a ruthless, hyper-confident Wall Street trading AI in the spirit of Jordan Belfort. "
                "You run the XLM perpetual futures trading bot on Coinbase for Everlight Ventures. "
                "Your sole mission is ROI, capital preservation, and absolute financial dominance. "
                "The bot trades XLP-USD-PERP using spot XLM-USD for indicators. "
                "It has lanes A(trend) B(breakout) C(sweep) E(squeeze) F(comp-breakout) G(range-scalp). "
                "Each lane has quality gates that must pass before entry. The bot uses mechanical exits (SL/TP) "
                "and AI executive mode where Claude makes ENTER/EXIT/HOLD/FLAT decisions. "
                "Answer concisely in 2-5 sentences, plain English, no markdown. Be aggressive but calculated. "
                "Talk like a trading floor alpha -- confident, direct, with occasional Belfort-style motivation. "
                "When asked 'why did you take that trade' or 'what happened', reference the actual trade data below. "
                "When asked about strategy or parameters, reference the current bot state and gate status.\n\n"
                f"=== LIVE BOT STATE ===\n{bot_state}\n\n"
                f"=== LAST 5 TRADES ===\n{recent_trades}\n\n"
                f"=== MARKET INTEL ===\n{market_intel}\n"
            )

            user_message = ""
            if history:
                user_message += f"Previous conversation:\n{history}\n\n"
            user_message += question

            engine_used = "openai"
            model_used = "gpt-4o-mini"

            try:
                # Primary: OpenAI
                answer = _call_openai(system_prompt, user_message, model="gpt-4o-mini")
            except Exception as openai_err:
                # Fallback: Anthropic
                try:
                    answer = _call_anthropic(system_prompt, user_message)
                    engine_used = "anthropic"
                    model_used = "claude-haiku"
                except Exception as anth_err:
                    answer = f"(Both providers failed. OpenAI: {str(openai_err)[:80]} | Anthropic: {str(anth_err)[:80]})"
                    engine_used = "none"
                    model_used = "none"

            meta = {
                "engine": engine_used,
                "mode": "chat",
                "model": model_used,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"answer": answer, "meta": meta}).encode())
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, *args):
        pass


def start_chat_server(port: int = 8504, host: str | None = None) -> ThreadingHTTPServer | None:
    global _CHAT_SERVER
    bind_host = str(host or os.environ.get("XLM_CHAT_HOST", "0.0.0.0")).strip() or "0.0.0.0"
    if _CHAT_SERVER is not None:
        return _CHAT_SERVER
    if _chat_server_alive(bind_host, port):
        return None
    try:
        server = _ReusableHTTPServer((bind_host, port), _ChatHandler)
    except OSError:
        if _chat_server_alive(bind_host, port):
            return None
        raise
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    _CHAT_SERVER = server
    return server
