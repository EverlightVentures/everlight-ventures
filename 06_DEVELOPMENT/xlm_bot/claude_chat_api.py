"""Tiny HTTP server for Claude chat from the dashboard.

Runs on port 8504 in a background thread. The floating chat widget
in dashboard.py talks to this via fetch().
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import threading

LOGS_DIR = Path(__file__).parent / "logs"
CLX_BIN = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py")
GMX_BIN = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py")


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


def _norm_choice(value: str, allowed: set[str], default: str) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in allowed else default


def _safe_opt_text(value: object) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    # Keep args compact and avoid shell/CLI control characters.
    return "".join(ch for ch in s if ch.isalnum() or ch in ("-", "_", ".", ":", "/"))[:48]


def _build_delegate_cmd(
    *,
    engine: str,
    mode: str,
    model: str,
    agent: str,
    allow_web: bool,
    prompt: str,
) -> list[str]:
    if engine == "gemini":
        cmd = [
            sys.executable,
            str(GMX_BIN),
            "--raw",
            "--mode",
            mode if mode in {"execute", "plan", "explain"} else "explain",
            "--output-format",
            "text",
        ]
        if model:
            cmd.extend(["--model", model])
        if allow_web:
            cmd.extend(["--allowed-tool", "WebSearch"])
        cmd.append(prompt)
        return cmd

    # Claude default
    cmd = [
        sys.executable,
        str(CLX_BIN),
        "--raw",
        "--mode",
        mode if mode in {"execute", "plan", "review"} else "review",
        "--output-format",
        "text",
    ]
    if model:
        cmd.extend(["--model", model])
    if agent:
        cmd.extend(["--agent", agent])
    if allow_web:
        cmd.extend(["--allowed-tool", "WebSearch"])
    cmd.append(prompt)
    return cmd


class _ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "service": "claude_chat_api"}).encode())
            return
        self.send_error(404)

    def do_POST(self):
        if self.path == "/ask":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            question = str(body.get("question", "")).strip()
            history = body.get("history", "")
            engine = _norm_choice(body.get("engine", "claude"), {"claude", "gemini"}, "claude")
            mode_raw = _norm_choice(
                body.get("mode", "review"),
                {"review", "plan", "execute", "explain"},
                "review",
            )
            mode = "explain" if (engine == "gemini" and mode_raw in {"review", "plan"}) else mode_raw
            model = _safe_opt_text(body.get("model"))
            agent = _safe_opt_text(body.get("agent"))
            allow_web = bool(body.get("allow_web", False))

            ctx = _read_bot_context()
            prompt = (
                "You are the Profit Maximizer (Agent 27) for an XLM perpetual futures trading bot on Coinbase. "
                "You operate within the Everlight AI Hive Mind. Your sole mission is ROI, capital preservation, "
                "and ruthless financial efficiency. The bot trades XLP-USD-PERP using spot XLM-USD for indicators. "
                "It has lanes A(trend) B(breakout) C(sweep) E(squeeze) F(comp-breakout) G(range-scalp). "
                "Answer concisely in 2-5 sentences, plain English, no markdown. Focus on risk/reward and capital allocation.\n\n"
                f"LIVE BOT STATE:\n{ctx}\n\n"
            )
            if history:
                prompt += f"CONVERSATION:\n{history}\n\n"
            prompt += f"User: {question}"

            try:
                default_model = "haiku" if engine == "claude" else ""
                cmd = _build_delegate_cmd(
                    engine=engine,
                    mode=mode,
                    model=model or default_model,
                    agent=agent,
                    allow_web=allow_web,
                    prompt=prompt,
                )
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=45,
                    env={**os.environ, "CLAUDECODE": ""},
                )
                answer = (result.stdout or "").strip()
                if not answer:
                    answer = f"(No response — code {result.returncode}: {(result.stderr or '').strip()[:120]})"
                meta = {
                    "engine": engine,
                    "mode": mode,
                    "model": model or default_model,
                    "agent": agent,
                    "allow_web": allow_web,
                    "returncode": result.returncode,
                }
            except subprocess.TimeoutExpired:
                answer = "(Timed out after 45s — try a shorter question)"
                meta = {"engine": engine, "mode": mode, "model": model, "agent": agent, "allow_web": allow_web}
            except Exception as e:
                answer = f"(Error: {str(e)[:120]})"
                meta = {"engine": engine, "mode": mode, "model": model, "agent": agent, "allow_web": allow_web}

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


def start_chat_server(port: int = 8504) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), _ChatHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
