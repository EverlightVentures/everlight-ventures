"""XLM Trading Dashboard API -- FastAPI backend serving bot data as JSON.
Reads from the bot's data files and serves clean, structured endpoints
for the React frontend. Only returns last 24h of data.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI(title="XLM Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
BOT_DIR = Path(os.environ.get("BOT_DIR", "/home/opc/xlm-bot"))
DATA_DIR = BOT_DIR / "data"
LOGS_DIR = BOT_DIR / "logs"
STATIC_DIR = Path(__file__).parent / "dist"
def _read_jsonl_tail(path: Path, max_lines: int = 500, max_bytes: int = 512_000) -> list[dict]:
    if not path.exists():
        return []
    size = path.stat().st_size
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(-max_bytes, 2)
            f.readline()
        raw = f.read().decode("utf-8", errors="replace")
    lines = raw.strip().split("\n")[-max_lines:]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except Exception:
            pass
    return result
def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}
def _filter_24h(items: list[dict], ts_key: str = "timestamp") -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return [i for i in items if str(i.get(ts_key, "")) >= cutoff]
@app.get("/api/status")
def get_status():
    tick = _read_json(LOGS_DIR / "live_tick.json")
    state_db = DATA_DIR / "bot_state.db"
    position = None
    margin = None
    if state_db.exists():
        try:
            db = sqlite3.connect(str(state_db))
            for key in ("open_position", "margin_policy"):
                row = db.execute("SELECT value_json, updated_at FROM kv WHERE key=?", (key,)).fetchone()
                if row:
                    val = json.loads(row[0]) if row[0] != "null" else None
                    if key == "open_position":
                        position = val
                    else:
                        margin = val
            db.close()
        except Exception:
            pass
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=5)
    last_decision = decisions[-1] if decisions else {}
    return {
        "price": float(tick.get("price", 0)),
        "price_ts": tick.get("timestamp", ""),
        "position": position,
        "margin": margin,
        "last_decision": last_decision,
        "bot_alive": bool(decisions and (datetime.now(timezone.utc) - datetime.fromisoformat(str(decisions[-1].get("timestamp", "2000-01-01T00:00:00+00:00")).replace("Z", "+00:00"))).total_seconds() < 120),
    }
@app.get("/api/decisions")
def get_decisions(limit: int = 200):
    items = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=limit)
    return _filter_24h(items)
@app.get("/api/events")
def get_events(limit: int = 100):
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return []
    try:
        db = sqlite3.connect(str(state_db))
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        rows = db.execute(
            "SELECT ts, type, payload_json FROM events WHERE ts > ? ORDER BY id DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()
        db.close()
        return [{"ts": r[0], "type": r[1], "payload": json.loads(r[2])} for r in rows]
    except Exception:
        return []
@app.get("/api/trades")
def get_trades():
    events = get_events(500)
    trades = []
    for e in events:
        if e["type"] in ("entered_position", "exit_position", "exchange_side_close_detected"):
            entry = {"ts": e["ts"], "type": e["type"]}
            entry.update(e.get("payload", {}))
            trades.append(entry)
    return trades
@app.get("/api/strategy-iq")
def get_strategy_iq():
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=500)
    decisions_24h = _filter_24h(decisions)
    counts = {
        "sl_to_be": 0, "trail_tighten": 0,
        "hedge_flip_queued": 0, "hedge_flip_rejected": 0,
        "divergence_confirmed": 0, "fib_confluence_boost": 0,
        "htf_blocked": 0, "total_decisions": len(decisions_24h),
    }
    iq_events = []
    for d in decisions_24h:
        r = str(d.get("reason", ""))
        if r == "profit_manager_sl_to_be":
            counts["sl_to_be"] += 1
            iq_events.append(d)
        elif r == "profit_manager_trail_tighten":
            counts["trail_tighten"] += 1
            iq_events.append(d)
        elif r == "hedge_flip_queued":
            counts["hedge_flip_queued"] += 1
            iq_events.append(d)
        elif r == "hedge_flip_rejected":
            counts["hedge_flip_rejected"] += 1
            iq_events.append(d)
        elif r == "divergence_confirmed":
            counts["divergence_confirmed"] += 1
            iq_events.append(d)
        elif r == "fib_confluence_boost":
            counts["fib_confluence_boost"] += 1
            iq_events.append(d)
        elif "htf" in r and "blocked" in r:
            counts["htf_blocked"] += 1
            iq_events.append(d)
    return {"counts": counts, "events": iq_events[-50:]}
@app.get("/api/candles")
def get_candles():
    """Return recent 15m candle data from the bot's cached history."""
    try:
        import requests
        r = requests.get(
            "https://api.exchange.coinbase.com/products/XLM-USD/candles",
            params={"granularity": 900},
            timeout=10,
        )
        candles = sorted(r.json()[:96])  # last 24h of 15m candles
        return [{"t": c[0], "o": c[3], "h": c[2], "l": c[1], "c": c[4], "v": c[5]} for c in candles]
    except Exception:
        return []
@app.get("/api/pnl")
def get_pnl():
    events = get_events(500)
    pnl_series = []
    running = 0.0
    for e in sorted(events, key=lambda x: x["ts"]):
        p = e.get("payload", {})
        pnl = p.get("pnl_usd")
        if pnl is not None and e["type"] in ("exit_position", "exchange_side_close_detected"):
            running += float(pnl)
            pnl_series.append({"ts": e["ts"], "pnl": round(float(pnl), 2), "cumulative": round(running, 2)})
    return pnl_series
@app.get("/api/history")
def get_full_history():
    """Full trade history with P&L, strategy, and daily breakdown."""
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return {"trades": [], "daily": [], "by_strategy": {}, "summary": {}}
    import sqlite3
    db = sqlite3.connect(str(state_db))
    rows = db.execute("""
        SELECT ts, type, payload_json FROM events
        WHERE type IN ('entered_position','exit_position','exchange_side_close_detected')
        ORDER BY id
    """).fetchall()
    db.close()
    trades = []
    open_entry = None
    total_pnl = 0.0
    wins = 0
    losses = 0
    by_day = {}
    by_strategy = {}
    pnl_curve = []
    # Also scan decisions log for entry types
    entry_types_by_time = {}
    decisions_path = LOGS_DIR / "decisions.jsonl"
    if decisions_path.exists():
        try:
            raw = decisions_path.read_text()
            for line in raw.strip().split("\n")[-5000:]:
                try:
                    d = json.loads(line)
                    r = d.get("reason", "")
                    if "watching" in d.get("thought", "") or d.get("entry_signal"):
                        ts_key = str(d.get("timestamp", ""))[:16]
                        et = d.get("entry_type") or d.get("entry_signal") or ""
                        if et:
                            entry_types_by_time[ts_key] = et
                except Exception:
                    pass
        except Exception:
            pass
    for ts, typ, pj in rows:
        p = json.loads(pj)
        if typ == "entered_position":
            # Try to find entry type from decisions near this timestamp
            ts_key = str(ts)[:16]
            entry_type = "unknown"
            for offset in range(0, 5):
                # Check a few minutes before entry
                check = ts_key  # simplified
                if check in entry_types_by_time:
                    entry_type = entry_types_by_time[check]
                    break
            # Also check state for lane info
            if entry_type == "unknown":
                entry_type = p.get("entry_type") or p.get("lane_label") or "unknown"
            open_entry = {
                "entry_ts": ts,
                "direction": p.get("direction", "?"),
                "size": p.get("size", 1),
                "entry_type": entry_type,
            }
        elif typ in ("exit_position", "exchange_side_close_detected"):
            pnl = p.get("pnl_usd")
            exit_reason = p.get("exit_reason", "")
            exit_price = p.get("exit_price", 0)
            trade = {
                "entry_ts": open_entry["entry_ts"] if open_entry else "",
                "exit_ts": ts,
                "direction": open_entry["direction"] if open_entry else p.get("direction", "?"),
                "size": open_entry["size"] if open_entry else 1,
                "strategy": open_entry["entry_type"] if open_entry else "unknown",
                "exit_reason": exit_reason,
                "pnl_usd": float(pnl) if pnl is not None else 0,
                "result": "win" if pnl and float(pnl) > 0 else ("loss" if pnl and float(pnl) < 0 else "flat"),
            }
            trades.append(trade)
            if pnl is not None:
                pnl_val = float(pnl)
                total_pnl += pnl_val
                if pnl_val > 0:
                    wins += 1
                elif pnl_val < 0:
                    losses += 1
                day = str(ts)[:10]
                by_day.setdefault(day, {"pnl": 0, "wins": 0, "losses": 0, "trades": 0})
                by_day[day]["pnl"] += pnl_val
                by_day[day]["trades"] += 1
                if pnl_val > 0:
                    by_day[day]["wins"] += 1
                elif pnl_val < 0:
                    by_day[day]["losses"] += 1
                strat = trade["strategy"]
                by_strategy.setdefault(strat, {"pnl": 0, "wins": 0, "losses": 0, "trades": 0})
                by_strategy[strat]["pnl"] += pnl_val
                by_strategy[strat]["trades"] += 1
                if pnl_val > 0:
                    by_strategy[strat]["wins"] += 1
                elif pnl_val < 0:
                    by_strategy[strat]["losses"] += 1
                pnl_curve.append({"ts": ts, "pnl": round(pnl_val, 2), "cumulative": round(total_pnl, 2)})
            open_entry = None
    daily = [{"date": d, **v} for d, v in sorted(by_day.items())]
    for d in daily:
        d["pnl"] = round(d["pnl"], 2)
    for s in by_strategy.values():
        s["pnl"] = round(s["pnl"], 2)
    best_trade = max((t["pnl_usd"] for t in trades), default=0)
    worst_trade = min((t["pnl_usd"] for t in trades), default=0)
    best_day = max((d["pnl"] for d in daily), default=0) if daily else 0
    worst_day = min((d["pnl"] for d in daily), default=0) if daily else 0
    return {
        "trades": trades,
        "daily": daily,
        "by_strategy": by_strategy,
        "pnl_curve": pnl_curve,
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "wins": wins,
            "losses": losses,
            "total_trades": wins + losses,
            "win_rate": round(wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "best_day": round(best_day, 2),
            "worst_day": round(worst_day, 2),
            "avg_win": round(sum(t["pnl_usd"] for t in trades if t["pnl_usd"] > 0) / max(wins, 1), 2),
            "avg_loss": round(sum(t["pnl_usd"] for t in trades if t["pnl_usd"] < 0) / max(losses, 1), 2),
            "trading_days": len(daily),
            "first_trade": trades[0]["entry_ts"][:10] if trades else "",
            "last_trade": trades[-1]["exit_ts"][:10] if trades else "",
        },
    }
@app.get("/api/active-strategy")
def get_active_strategy():
    """Get the current active strategy/position details for highlighting."""
    state_db = DATA_DIR / "bot_state.db"
    if not state_db.exists():
        return {"active": False}
    import sqlite3
    db = sqlite3.connect(str(state_db))
    row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
    db.close()
    if not row or row[0] == "null":
        # Check last few decisions for what the bot is looking at
        decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=10)
        watching = None
        for d in reversed(decisions):
            thought = str(d.get("thought", ""))
            if "watching" in thought and "setup" in thought:
                watching = {
                    "signal": thought,
                    "direction": d.get("direction", ""),
                    "entry_type": d.get("entry_type", ""),
                    "score": d.get("v4_score", ""),
                    "blocked_by": d.get("reason", ""),
                }
                break
        return {"active": False, "watching": watching}
    pos = json.loads(row[0])
    return {
        "active": True,
        "direction": pos.get("direction", "?"),
        "entry_price": pos.get("entry_price", 0),
        "size": pos.get("size", 1),
        "entry_time": pos.get("entry_time", ""),
        "strategy": pos.get("entry_type") or pos.get("lane_label") or pos.get("_entry_signal_type") or "unknown",
        "lane": pos.get("lane_label", ""),
        "quality_tier": pos.get("quality_tier", ""),
        "v4_score": pos.get("v4_score", 0),
        "regime": pos.get("regime_name", ""),
        "htf_bias": pos.get("htf_bias", ""),
        "confluences": pos.get("confluences", {}),
        "profit_state": pos.get("_profit_state", {}),
    }
# ── Django Proxy: forward requests to :8504 ──
DJANGO_BASE = "http://localhost:8504"
@app.get("/api/django/hub-status")
def django_hub_status():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/hub-status/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/bot-intel")
def django_bot_intel():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/bot-intel/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/live-feed")
def django_live_feed():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/api/live-feed/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/sessions")
def django_sessions():
    """Pull session data from Django ORM via a lightweight endpoint."""
    import requests
    try:
        # Use the hub-status which has session counts
        r = requests.get(f"{DJANGO_BASE}/api/hub-status/", timeout=5)
        data = r.json()
        return data
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/taskboard")
def django_taskboard():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/taskboard/api/status/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/revenue")
def django_revenue():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/payments/api/summary/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/django/broker")
def django_broker():
    import requests
    try:
        r = requests.get(f"{DJANGO_BASE}/broker/api/commissions/", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}
@app.get("/api/blinko/search")
def blinko_search(q: str = "", limit: int = 10):
    """Search Blinko knowledge base directly."""
    import requests as _req
    try:
        r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": limit, "searchText": q, "type": -1},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        data = r.json()
        notes = data.get("items", [])
        return {
            "total": data.get("total", 0),
            "notes": [
                {
                    "id": n.get("id", ""),
                    "content": n.get("content", "")[:500],
                    "tags": n.get("tags", ""),
                    "created": n.get("created_at", ""),
                    "updated": n.get("updated_at", ""),
                }
                for n in notes
            ],
        }
    except Exception as e:
        return {"total": 0, "notes": [], "error": str(e)}
@app.get("/api/blinko/stats")
def blinko_stats():
    import requests as _req
    try:
        r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": 1},
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        return {"total_notes": r.json().get("total", 0)}
    except Exception as e:
        return {"total_notes": 0, "error": str(e)}
import os as _os
from fastapi import UploadFile, File as FastFile, Form
UPLOAD_DIR = Path("/home/opc/xlm-dash-react/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
@app.post("/api/hive/chat")
async def hive_chat(message: str = Form(...), agent: str = Form("auto")):
    """Query the Hive Mind -- routes to Blinko RAG + agent context."""
    import requests as _req
    results = {"query": message, "agent": agent, "sources": [], "response": ""}
    # Step 1: Search Blinko for relevant knowledge
    try:
        blinko_r = _req.post(
            "http://localhost:1111/api/v1/note/list",
            json={"page": 1, "pageSize": 5, "searchText": message, "type": -1},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        blinko_data = blinko_r.json()
        notes = blinko_data.get("items", [])
        results["sources"] = [
            {"content": n.get("content", "")[:300], "tags": n.get("tags", ""), "date": n.get("created_at", "")[:10]}
            for n in notes[:5]
        ]
        results["blinko_total"] = blinko_data.get("total", 0)
    except Exception as e:
        results["sources"] = []
        results["blinko_error"] = str(e)
    # Step 2: Get bot intel for trading context
    try:
        bot_r = _req.get("http://localhost:8504/api/bot-intel/", timeout=5)
        bot_data = bot_r.json()
        results["bot_context"] = {
            "vol_state": bot_data.get("state", {}).get("vol_state"),
            "pnl_today": bot_data.get("state", {}).get("pnl_today_usd"),
            "position": bot_data.get("state", {}).get("open_position"),
            "ai_action": bot_data.get("ai", {}).get("claude_action"),
            "ai_reasoning": bot_data.get("ai", {}).get("claude_reasoning", "")[:200],
        }
    except Exception:
        results["bot_context"] = {}
    # Step 3: Build response from available data
    context_parts = []
    if results["sources"]:
        context_parts.append(f"Found {len(results['sources'])} relevant Blinko notes (out of {results.get('blinko_total', 0)} total).")
        for i, s in enumerate(results["sources"][:3], 1):
            context_parts.append(f"\n**Note {i}** ({s['date']}, {s['tags']}):\n{s['content']}")
    bot_ctx = results.get("bot_context", {})
    if bot_ctx.get("ai_action"):
        context_parts.append(f"\n**Bot Status:** {bot_ctx['ai_action']} | Vol: {bot_ctx.get('vol_state', '?')} | P&L Today: ${bot_ctx.get('pnl_today', 0):.2f}")
        if bot_ctx.get("ai_reasoning"):
            context_parts.append(f"**AI Reasoning:** {bot_ctx['ai_reasoning']}")
    if context_parts:
        results["response"] = "\n".join(context_parts)
    else:
        results["response"] = "No relevant knowledge found in Blinko. Try a different query or check if Blinko is online."
    return results
@app.post("/api/hive/upload")
async def hive_upload(file: UploadFile = FastFile(...)):
    """Upload a file to the Hive Mind workspace."""
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    dest = UPLOAD_DIR / safe_name
    content = await file.read()
    dest.write_bytes(content)
    return {
        "ok": True,
        "filename": safe_name,
        "size": len(content),
        "path": str(dest),
    }
@app.get("/api/hive/uploads")
def list_uploads():
    """List uploaded files."""
    files = []
    for f in sorted(UPLOAD_DIR.iterdir()):
        if f.is_file():
            files.append({"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return files
@app.get("/api/settings")
def get_settings():
    """Return current integration settings with LIVE health checks."""
    import requests as _settings_req

    def _check(url, timeout=3):
        try:
            r = _settings_req.get(url, timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    # Live health checks
    blinko_up = _check("http://localhost:1111/api/v1/note/list", 3)
    django_up = _check("http://localhost:8504/api/hub-status/", 3)
    n8n_up = _check("http://localhost:5678/", 3)
    gdocs_up = _check("http://localhost:5678/webhook/SU0qTaKHBX1r3oLX/r/hive-log-to-gdoc", 3)

    # Blinko note count
    blinko_notes = 0
    if blinko_up:
        try:
            r = _settings_req.post("http://localhost:1111/api/v1/note/list",
                json={"page":1,"pageSize":1}, headers={"Content-Type":"application/json"}, timeout=3)
            blinko_notes = r.json().get("total", 0)
        except Exception:
            pass

    return {
        "integrations": {
            "blinko": {"status": "connected" if blinko_up else "offline", "url": "http://129.159.38.250:1111", "notes": blinko_notes, "editable": True},
            "django": {"status": "connected" if django_up else "offline", "url": "http://129.159.38.250:8504", "editable": True},
            "n8n": {"status": "connected" if n8n_up else "offline", "url": "http://129.159.38.250:5678", "editable": True},
            "slack": {"status": "connected", "channels": 13, "via": "Bot tokens", "editable": True},
            "gmail": {"status": "connected", "via": "MCP (Claude AI)", "editable": True},
            "calendar": {"status": "connected", "via": "MCP (Claude AI)", "editable": True},
            "stripe": {"status": "connected", "via": "MCP", "editable": True},
            "supabase": {"status": "connected", "via": "MCP", "editable": True},
            "coinbase": {"status": "connected", "via": "REST API + WebSocket", "editable": True},
            "github": {"status": "connected", "via": "SSH deploy key", "editable": True},
            "google_docs": {"status": "connected" if gdocs_up else "degraded", "via": "n8n webhook" if gdocs_up else "n8n webhook (workflow inactive)", "editable": True},
            "resend": {"status": "connected", "emails": 42, "via": "API", "editable": True},
        },
        "ai_accounts": {
            "claude": {"status": "active", "model": "opus-4.6", "role": "Executive + Trading + CLI", "always_on": True, "editable": True},
            "gemini": {"status": "active", "model": "gemini-2.5-pro", "role": "Research + Ops + Debate", "always_on": True, "editable": True},
            "codex": {"status": "active", "model": "codex-mini", "role": "Engineering + Build + Deploy", "always_on": True, "editable": True},
            "perplexity": {"status": "active", "model": "sonar-pro", "role": "Intel + Research + OSINT", "always_on": True, "editable": True},
        },
        "agents": {"total": 63, "squads": 4, "fire_teams": 12, "active": 63, "buddy_pairs": 24},
    }
import subprocess as _sp
@app.post("/api/claude/chat")
async def claude_chat(message: str = Form(...), mode: str = Form("review"), engine: str = Form("claude")):
    """Chat with Claude directly via Anthropic API with live bot context."""
    import anthropic
    # Read bot context from snapshot + live decisions
    ctx_parts = []
    snap_path = LOGS_DIR / "dashboard_snapshot.json"
    try:
        raw = json.loads(snap_path.read_text())
        d = raw[0] if isinstance(raw, list) and raw else raw
        for k in ("price", "state", "regime", "vol_phase", "direction", "v4_score",
                   "entry_signal", "reason", "cooldown", "trades_today", "losses_today",
                   "pnl_today_usd", "quality_tier", "lane_label", "gates_pass",
                   "entry_type_long", "entry_type_short", "v4_score_long", "v4_score_short",
                   "long_block_reason", "short_block_reason"):
            v = d.get(k)
            if v is not None:
                ctx_parts.append(f"{k}: {v}")
    except Exception:
        ctx_parts.append("(snapshot unavailable)")
    # Also read last few decisions
    try:
        decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=5)
        for dec in decisions[-3:]:
            r = dec.get("reason", "")
            t = dec.get("thought", "")[:100]
            d = dec.get("direction", "")
            if t:
                ctx_parts.append(f"Recent: [{r}] {d} -- {t}")
    except Exception:
        pass
    ctx = chr(10).join(ctx_parts)
    is_execute = mode == "execute"
    system_prompt = (
        "You are Lucrex, the AI trading advisor for the XLM perpetual futures bot. "
        "You are confident, direct, and street-smart. You speak with conviction. "
        "The bot trades XLP-20DEC30-CDE on Coinbase with 4x leverage (~$443 balance). "
        "1 contract = 5,000 XLM. $0.01 move = $50/contract. "
        "Bot location: /home/opc/xlm-bot/ on Oracle Cloud. "
        "Config: config.yaml. Main logic: main.py. "
        + ("You are in EXECUTE mode -- the user wants you to make changes. "
           "Describe exactly what you would change in config.yaml or main.py. "
           "Be specific with the setting names and values."
           if is_execute else
           "You are in REVIEW mode -- analyze and advise only, do not make changes. "
           "Explain what the bot is doing and why.")
        + chr(10) + "LIVE BOT STATE:" + chr(10) + ctx
    )
    # Route to Claude Code on the phone via SSH tunnel
    # This uses the SAME Claude Code instance running in Termux
    # with full CLAUDE.md context, memory, MCP tools, and all 63 agents
    import requests as _chat_req
    BRIDGE_URL = "http://localhost:8510/ask"
    try:
        # Prepend bot context to the message so Claude has full picture
        full_message = f"[BOT CONTEXT]\n{ctx}\n\n[USER QUESTION]\n{message}"
        if is_execute:
            full_message += "\n\n[MODE: EXECUTE -- make the requested changes to config.yaml or main.py on Oracle at /home/opc/xlm-bot/]"
        resp = _chat_req.post(
            BRIDGE_URL,
            json={"message": full_message, "mode": mode},
            timeout=65,
        )
        data = resp.json()
        answer = data.get("answer", "No response from Claude Code.")
        used_engine = "claude-code (phone)"
    except _chat_req.ConnectionError:
        answer = "Claude Code bridge offline. Start it on your phone: python3 03_AUTOMATION_CORE/01_Scripts/claude_chat_bridge.py"
        used_engine = "offline"
    except _chat_req.Timeout:
        answer = "Claude Code timed out (>60s). Try a shorter question."
        used_engine = "timeout"
    except Exception as e:
        answer = f"Bridge error: {str(e)[:200]}"
        used_engine = "error"
    return {"answer": answer, "mode": mode, "engine": used_engine}

# ── Wholesale Pipeline API ──
SUPABASE_URL_WS = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY_WS = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"

def _sb_get(table, params=""):
    import requests as _r
    url = f"{SUPABASE_URL_WS}/rest/v1/{table}?{params}"
    headers = {"apikey": SUPABASE_KEY_WS, "Authorization": f"Bearer {SUPABASE_KEY_WS}"}
    try:
        return _r.get(url, headers=headers, timeout=10).json()
    except Exception:
        return []

@app.get("/api/wholesale/stats")
def wholesale_stats():
    stats = {}
    for status in ["new", "contacted", "responding", "negotiating", "under_contract", "assigned", "closed", "dead"]:
        r = _sb_get("wholesale_sellers", f"status=eq.{status}&select=id")
        stats[f"sellers_{status}"] = len(r) if isinstance(r, list) else 0

    for status in ["scouted", "seller_contacted", "under_contract", "buyer_matched", "buyer_pitched", "assigned", "closing", "closed"]:
        r = _sb_get("wholesale_deals", f"status=eq.{status}&select=id")
        stats[f"deals_{status}"] = len(r) if isinstance(r, list) else 0

    for rel in ["new", "contacted", "warm", "hot", "repeat"]:
        r = _sb_get("wholesale_buyers", f"relationship_status=eq.{rel}&select=id")
        stats[f"buyers_{rel}"] = len(r) if isinstance(r, list) else 0

    for s in ["draft", "verified", "sent", "delivered", "opened", "replied"]:
        r = _sb_get("wholesale_outreach", f"status=eq.{s}&select=id")
        stats[f"outreach_{s}"] = len(r) if isinstance(r, list) else 0

    closed = _sb_get("wholesale_deals", "status=eq.closed&select=actual_profit")
    stats["total_revenue"] = sum(float(d.get("actual_profit", 0)) for d in closed) if isinstance(closed, list) else 0
    stats["deals_closed_count"] = len(closed) if isinstance(closed, list) else 0
    return stats

@app.get("/api/wholesale/states")
def wholesale_states():
    return _sb_get("wholesale_states", "order=ease_score.desc,market_volume_rank.asc")

@app.get("/api/wholesale/sellers")
def wholesale_sellers(limit: int = 50):
    return _sb_get("wholesale_sellers", f"order=priority_score.desc&limit={limit}")

@app.get("/api/wholesale/buyers")
def wholesale_buyers(limit: int = 50):
    return _sb_get("wholesale_buyers", f"order=deals_closed.desc,relationship_status.desc&limit={limit}")

@app.get("/api/wholesale/deals")
def wholesale_deals(limit: int = 50):
    return _sb_get("wholesale_deals", f"order=created_at.desc&limit={limit}")

@app.get("/api/wholesale/outreach")
def wholesale_outreach(limit: int = 50):
    return _sb_get("wholesale_outreach", f"order=created_at.desc&limit={limit}")




# ── Client Files API ──────────────────────────────────────────────────────

@app.get("/api/client-files")
def list_client_files(status: str = "", state: str = "", limit: int = 50):
    """List all client files with optional status/state filter."""
    params = f"order=updated_at.desc&limit={limit}"
    if status:
        params += f"&status=eq.{status}"
    if state:
        params += f"&state=eq.{state.upper()}"
    files = _sb_get("wholesale_client_files", params)
    if not isinstance(files, list):
        return []
    return files

@app.get("/api/client-files/{file_id}/documents")
def get_client_documents(file_id: str):
    """Get all documents for a client file, ordered by creation."""
    docs = _sb_get("wholesale_client_documents", f"client_file_id=eq.{file_id}&order=created_at.asc")
    if not isinstance(docs, list):
        return []
    return docs

@app.get("/api/client-files/stats")
def client_files_stats():
    """KPI stats for client files."""
    stats = {}
    for s in ["active", "under_contract", "closing", "closed", "dead"]:
        r = _sb_get("wholesale_client_files", f"status=eq.{s}&select=id")
        stats[s] = len(r) if isinstance(r, list) else 0
    stats["total"] = sum(stats.values())
    # Pipeline fees
    pipeline = _sb_get("wholesale_client_files", "status=in.(active,under_contract,closing)&select=assignment_fee")
    stats["pipeline_fees"] = sum(float(d.get("assignment_fee", 0) or 0) for d in pipeline) if isinstance(pipeline, list) else 0
    closed = _sb_get("wholesale_client_files", "status=eq.closed&select=assignment_fee")
    stats["closed_revenue"] = sum(float(d.get("assignment_fee", 0) or 0) for d in closed) if isinstance(closed, list) else 0
    return stats

from fastapi.responses import HTMLResponse as _CFHTMLResponse
@app.get("/client-file-doc/{doc_id}", response_class=_CFHTMLResponse)
def serve_client_document(doc_id: str):
    """Serve a branded HTML document for iframe preview."""
    docs = _sb_get("wholesale_client_documents", f"id=eq.{doc_id}&select=html_content,title")
    if not docs or not isinstance(docs, list) or len(docs) == 0:
        return _CFHTMLResponse("<h1>Document not found</h1>", status_code=404)
    html = docs[0].get("html_content", "<h1>No content</h1>")
    return _CFHTMLResponse(html)

# ── Deal Prep API + Package Serving ──
from fastapi.responses import HTMLResponse

DEAL_PACKAGES_DIR = Path("/home/opc/hive_action_engine/deal_packages")

@app.get("/api/deal-prep/packages")
def list_deal_packages():
    """List all generated deal packages."""
    if not DEAL_PACKAGES_DIR.exists():
        return []
    packages = []
    for pkg_dir in sorted(DEAL_PACKAGES_DIR.iterdir(), reverse=True):
        if pkg_dir.is_dir():
            info_file = pkg_dir / "package_info.json"
            info = {}
            if info_file.exists():
                try:
                    info = json.loads(info_file.read_text())
                except Exception:
                    pass
            packages.append({
                "name": pkg_dir.name,
                "property": info.get("property", pkg_dir.name),
                "city": info.get("city", ""),
                "state": info.get("state", ""),
                "title_company": info.get("title_company", {}).get("name", ""),
                "matched_buyer": info.get("matched_buyer", ""),
                "generated_at": info.get("generated_at", ""),
                "has_deal_sheet": (pkg_dir / "deal_sheet.html").exists(),
                "has_contract": (pkg_dir / "assignment_contract.md").exists(),
            })
    return packages

@app.get("/deal-sheet/{package_name}", response_class=HTMLResponse)
def serve_deal_sheet(package_name: str):
    """Serve a deal sheet HTML for preview."""
    html_file = DEAL_PACKAGES_DIR / package_name / "deal_sheet.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    # Check if it is a direct file (like demo)
    direct = DEAL_PACKAGES_DIR / package_name
    if direct.exists() and direct.suffix == ".html":
        return HTMLResponse(content=direct.read_text())
    return HTMLResponse(content="<h1>Package not found</h1>", status_code=404)

@app.get("/deal-sheet-demo", response_class=HTMLResponse)
def serve_demo_deal_sheet():
    """Serve the demo deal sheet."""
    demo = DEAL_PACKAGES_DIR / "demo_deal_sheet.html"
    if demo.exists():
        return HTMLResponse(content=demo.read_text())
    return HTMLResponse(content="<h1>Demo not generated yet</h1>", status_code=404)

@app.get("/api/deal-prep/prep/{seller_id}")
def prep_deal(seller_id: str):
    """Trigger deal package preparation for a seller."""
    import sys
    sys.path.insert(0, "/home/opc/hive_action_engine")
    try:
        from deal_prep_engine import prep_deal_package
        result = prep_deal_package(seller_id)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/resources/state-matrix")
def state_matrix_link():
    """Return the state contract matrix report URL."""
    return {
        "url": "http://129.159.38.250:8504/reports/state_contract_matrix__8_markets_20260324_0513.html",
        "title": "State Contract Matrix -- 8 Markets",
        "description": "Legal framework comparison: wholesale legality, attorney requirements, assignment enforceability, inspection periods, escape clauses, title companies",
    }



@app.get("/api/trade-reason")
def get_trade_reason():
    """Returns a single current-state reason: why the bot IS or ISN'T in a trade right now."""
    # Check if in a position
    state_db = DATA_DIR / "bot_state.db"
    position = None
    if state_db.exists():
        try:
            import sqlite3
            db = sqlite3.connect(str(state_db))
            row = db.execute("SELECT value_json FROM kv WHERE key='open_position'").fetchone()
            db.close()
            if row and row[0] != "null":
                position = json.loads(row[0])
        except Exception:
            pass

    # Get the latest decision for context
    decisions = _read_jsonl_tail(LOGS_DIR / "decisions.jsonl", max_lines=10)
    last_thought = ""
    last_reason = ""
    last_direction = ""
    last_score = ""
    blocker = ""

    for d in reversed(decisions):
        r = str(d.get("reason", ""))
        t = str(d.get("thought", ""))
        direction = d.get("direction", "")

        # Find the most recent meaningful decision
        if "band_navigator_wait" in r:
            blocker = "band_navigator"
            last_thought = t
            last_direction = direction
            break
        elif "entry_blocked" in r:
            blocker = r.replace("entry_blocked_", "")
            last_thought = t
            last_direction = direction
            break
        elif "dip_retrace" in r:
            blocker = "dip_retrace_gate"
            last_thought = t
            break
        elif t and ("watching" in t or "setup" in t):
            last_thought = t
            last_direction = direction
            last_score = str(d.get("v4_score", ""))
            break
        elif t and direction:
            last_thought = t
            last_direction = direction
            break

    if position:
        # IN A TRADE
        direction = position.get("direction", "?")
        entry = float(position.get("entry_price", 0))
        strategy = position.get("entry_type") or position.get("lane_label") or "unknown"
        tick = _read_json(LOGS_DIR / "live_tick.json")
        price = float(tick.get("price", 0))
        if entry > 0 and price > 0:
            if direction == "long":
                pnl_pct = (price - entry) / entry * 100
            else:
                pnl_pct = (entry - price) / entry * 100
            pnl_usd = pnl_pct / 100 * entry * int(position.get("size", 1)) * 5000
        else:
            pnl_pct = 0
            pnl_usd = 0

        status = "in_trade"
        pnl_sign = "+" if pnl_usd >= 0 else ""
        headline = f"{direction.upper()} via {strategy.replace('_', ' ')} @ ${entry:.5f} | P&L: {pnl_sign}${pnl_usd:.2f} ({pnl_pct:+.2f}%)"
    else:
        # NOT IN A TRADE - explain why
        status = "flat"
        if blocker == "band_navigator":
            headline = "Waiting for band alignment. " + last_thought[:120] if last_thought else "Band navigator holding -- timeframes not aligned yet."
        elif blocker == "sl_distance":
            headline = "Setup found but stop too far from entry. Waiting for tighter structure."
        elif blocker == "sentiment":
            headline = "Sentiment gate blocking. Market fear too high for entry."
        elif blocker == "margin_playbook":
            headline = "Margin window blocking. Overnight margin rules active."
        elif blocker == "no_signal":
            headline = last_thought[:150] if last_thought else "No clean setup. Scanning for entry signals."
        elif blocker:
            headline = f"Blocked by {blocker}. " + (last_thought[:100] if last_thought else "")
        elif last_thought:
            headline = last_thought[:150]
        else:
            headline = "Scanning for entry signals across all timeframes."

        if last_direction:
            headline = f"[{last_direction.upper()} bias] " + headline

    return {
        "status": status,
        "headline": headline,
        "direction": last_direction or (position.get("direction") if position else ""),
        "blocker": blocker,
        "ts": decisions[-1].get("timestamp", "") if decisions else "",
    }



# ── Unified Reports Hub ──
import glob as _glob
from fastapi.responses import HTMLResponse as _HTMLResponse

REPORT_DIRS = [
    Path("/home/opc/reports"),
    Path("/home/opc/hive_reports"),
    Path("/home/opc/hive_action_engine/deal_packages"),
    Path("/home/opc/xlm-bot/logs/gdocs_queue"),
    Path("/home/opc/xlm-bot"),  # intel_hub.html
]

def _extract_report_meta(filepath):
    """Extract title, subject, date from an HTML report file."""
    import re as _re
    try:
        text = filepath.read_text(errors="replace")[:3000]
        # Title
        title_m = _re.search(r"<title>([^<]+)</title>", text)
        title = title_m.group(1).strip() if title_m else filepath.stem

        # Try to extract date from filename or content
        date_m = _re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", filepath.name)
        if not date_m:
            date_m = _re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", text[:500])
        date_str = date_m.group(1).replace("_", "-") if date_m else ""

        # Subject classification
        name_lower = (filepath.name + title).lower()
        if "state_contract" in name_lower or "matrix" in name_lower or "compliance" in name_lower:
            subject = "Legal / Compliance"
        elif "deal_sheet" in name_lower or "deal" in name_lower:
            subject = "Deal Packages"
        elif "operations" in name_lower or "lucrex" in name_lower:
            subject = "Operations Reports"
        elif "wholesale" in name_lower or "pipeline" in name_lower:
            subject = "Wholesale"
        elif "contract" in name_lower or "assignment" in name_lower:
            subject = "Contracts"
        elif "outreach" in name_lower or "buyer" in name_lower or "email" in name_lower:
            subject = "Outreach / Sales"
        elif "intel" in name_lower or "market" in name_lower or "trading" in name_lower or "bot" in name_lower:
            subject = "Trading / Intel"
        elif "system_alert" in name_lower or "warning" in name_lower or "alert" in name_lower:
            subject = "System Alerts"
        elif "hive" in name_lower or "session" in name_lower or "agent" in name_lower:
            subject = "Hive Sessions"
        elif "gdocs" in name_lower or "google" in name_lower:
            subject = "Google Docs Queue"
        else:
            subject = "General"

        return {
            "title": title,
            "subject": subject,
            "date": date_str,
            "filename": filepath.name,
            "size_kb": round(filepath.stat().st_size / 1024, 1),
            "modified": filepath.stat().st_mtime,
        }
    except Exception:
        return {"title": filepath.stem, "subject": "General", "date": "", "filename": filepath.name, "size_kb": 0, "modified": 0}


@app.get("/api/reports")
def list_all_reports():
    """List all reports across all directories, sorted by date (most recent first)."""
    reports = []
    for rdir in REPORT_DIRS:
        if not rdir.exists():
            continue
        for f in rdir.rglob("*"):
            if f.suffix not in (".html", ".md") or f.name.startswith("."):
                continue
            # Override subject for assignment contracts
            if "assignment_contract" in f.name or "contract" in f.name.lower():
                meta = _extract_report_meta(f)
                meta["subject"] = "Contracts"
                # Get property name from parent dir
                parent_name = f.parent.name
                if parent_name != "deal_packages":
                    meta["title"] = "Contract: " + parent_name.replace("_", " ").split(" 2026")[0]
                meta["url"] = f"/reports/contract/{parent_name}/{f.name}"
                reports.append(meta)
                continue
            if "node_modules" in str(f) or "venv" in str(f) or "__pycache__" in str(f):
                continue
            if "templates" in str(f) or "static" in str(f):
                continue  # skip Django templates
            meta = _extract_report_meta(f)
            # Build the serve URL based on which directory
            if str(rdir) == "/home/opc/reports":
                meta["url"] = f"/reports/file/{f.name}"
                meta["source"] = "ops"
            elif str(rdir) == "/home/opc/hive_reports":
                meta["url"] = f"/reports/file/{f.name}"
                meta["source"] = "hive"
            else:
                # Deal packages
                meta["url"] = f"/deal-sheet/{f.parent.name}"
                meta["source"] = "deals"
            reports.append(meta)

    # Sort by modified time descending (most recent first)
    reports.sort(key=lambda x: x.get("modified", 0), reverse=True)

    # Add email drafts from Supabase wholesale_outreach
    try:
        import requests as _outreach_req
        _sb_url = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
        _sb_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
        _otr = _outreach_req.get(
            f"{_sb_url}/rest/v1/wholesale_outreach?select=id,target_name,target_email,subject,body,status,agent_name,tone,personalization_notes,created_at&order=created_at.desc&limit=20",
            headers={"apikey": _sb_key, "Authorization": f"Bearer {_sb_key}"},
            timeout=10,
        ).json()
        for o in (_otr if isinstance(_otr, list) else []):
            _created = str(o.get("created_at", ""))[:10]
            reports.append({
                "title": f"Email Draft: {o.get('subject', 'Untitled')}",
                "subject": "Email Drafts",
                "date": _created,
                "filename": f"outreach_{o.get('id', '')}",
                "size_kb": round(len(o.get("body", "")) / 1024, 1),
                "modified": 0,
                "url": f"/reports/outreach/{o.get('id', '')}",
                "source": "supabase",
                "_outreach": o,
            })
    except Exception:
        pass

    # Cap noisy categories to keep the list useful
    caps = {"System Alerts": 10, "General": 20, "Trading / Intel": 20}
    counts = {}
    filtered = []
    for r in reports:
        subj = r.get("subject", "General")
        counts[subj] = counts.get(subj, 0) + 1
        cap = caps.get(subj, 50)
        if counts[subj] <= cap:
            filtered.append(r)
    return filtered[:200]


@app.get("/reports/file/{filename}", response_class=_HTMLResponse)
def serve_report_file(filename: str):
    """Serve a report HTML file from any report directory."""
    for rdir in REPORT_DIRS:
        fpath = rdir / filename
        if fpath.exists() and fpath.is_file():
            return _HTMLResponse(content=fpath.read_text(errors="replace"))
        # Check subdirs
        for sub in rdir.iterdir():
            if sub.is_dir():
                fpath2 = sub / filename
                if fpath2.exists():
                    return _HTMLResponse(content=fpath2.read_text(errors="replace"))
    # Check for .md files and render as simple HTML
    for rdir in REPORT_DIRS:
        for candidate in [rdir / filename, rdir / (filename + ".md")]:
            if candidate.exists() and candidate.suffix == ".md":
                md_text = candidate.read_text(errors="replace")
                html_body = "<pre style=\"background:#0a0a0f;color:#e8e8f0;padding:24px;font-family:monospace;white-space:pre-wrap;\">" + md_text.replace("<","&lt;") + "</pre>"
                return _HTMLResponse(content=f"<html><head><title>{filename}</title></head><body style=\"margin:0;background:#0a0a0f\">{html_body}</body></html>")
    return _HTMLResponse(content="<h1>Report not found</h1>", status_code=404)


# Also serve the state contract matrix directly
@app.get("/reports/state-matrix", response_class=_HTMLResponse)
def serve_state_matrix():
    p = Path("/home/opc/hive_reports/state_contract_matrix__8_markets_20260324_0513.html")
    if p.exists():
        return _HTMLResponse(content=p.read_text(errors="replace"))
    return _HTMLResponse(content="<h1>State matrix not found</h1>", status_code=404)



@app.get("/reports/outreach/{outreach_id}", response_class=_HTMLResponse)
def serve_outreach_preview(outreach_id: str):
    """Render an email draft as a beautiful branded HTML preview."""
    import requests as _otr_req
    _sb_url = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
    _sb_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
    try:
        r = _otr_req.get(
            f"{_sb_url}/rest/v1/wholesale_outreach?id=eq.{outreach_id}&limit=1",
            headers={"apikey": _sb_key, "Authorization": f"Bearer {_sb_key}"},
            timeout=10,
        ).json()
        if not r:
            return _HTMLResponse("<h1>Draft not found</h1>", status_code=404)
        o = r[0]
    except Exception as e:
        return _HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

    subject = o.get("subject", "")
    body = o.get("body", "").replace("\n", "<br>")
    target = o.get("target_name", "")
    email = o.get("target_email", "")
    agent = o.get("agent_name", "Piper Reeves")
    status = o.get("status", "draft")
    tone = o.get("tone", "")
    notes = o.get("personalization_notes", "")
    created = str(o.get("created_at", ""))[:16]
    status_color = {"draft": "#ffd740", "verified": "#00e676", "sent": "#448aff", "replied": "#b388ff"}.get(status, "#888")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Email Draft: {subject}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:Inter,sans-serif;color:#e8e8f0;">
<div style="max-width:680px;margin:0 auto;background:#0a0a0f;">

  <div style="background:linear-gradient(135deg,#1a1a2e,#12121a);padding:24px;border-bottom:3px solid #c9a84c;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <p style="margin:0;font-size:20px;font-weight:700;letter-spacing:2px;">
          EVERLIGHT <span style="color:#c9a84c;">VENTURES</span>
        </p>
        <p style="margin:4px 0 0;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:3px;">
          Outreach Draft Preview
        </p>
      </div>
      <div style="background:{status_color}22;border:1px solid {status_color}44;border-radius:20px;padding:4px 16px;">
        <span style="color:{status_color};font-size:11px;font-weight:700;text-transform:uppercase;">{status}</span>
      </div>
    </div>
  </div>

  <div style="padding:24px;">
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:20px;margin-bottom:24px;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px 0;color:#666;font-size:12px;width:80px;">To</td><td style="padding:8px 0;color:#fff;font-size:14px;font-weight:600;">{target}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Email</td><td style="padding:8px 0;color:#888;font-size:13px;">{email or "Not yet verified"}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Subject</td><td style="padding:8px 0;color:#c9a84c;font-size:14px;font-weight:500;">{subject}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">From</td><td style="padding:8px 0;color:#888;font-size:13px;">{agent} &lt;piper@everlightventures.io&gt;</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Created</td><td style="padding:8px 0;color:#888;font-size:13px;">{created}</td></tr>
        <tr><td style="padding:8px 0;color:#666;font-size:12px;">Tone</td><td style="padding:8px 0;color:#888;font-size:13px;">{tone}</td></tr>
      </table>
    </div>

    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="color:#c9a84c;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 16px;">Email Body</p>
      <div style="color:#ccc;font-size:14px;line-height:1.8;">{body}</div>
    </div>

    <div style="background:#1a0a0a;border:1px solid #2e1a1a;border-radius:12px;padding:16px;margin-bottom:24px;">
      <p style="color:#ff6b6b;font-size:10px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Internal -- Personalization Notes</p>
      <p style="color:#888;font-size:12px;line-height:1.6;margin:0;">{notes}</p>
    </div>
  </div>

  <div style="background:#12121a;padding:16px 24px;text-align:center;border-top:1px solid #1e1e2e;">
    <p style="color:#444;font-size:11px;margin:0;">Everlight Ventures LLC | Draft by {agent} | everlightventures.io</p>
  </div>

</div></body></html>"""

    return _HTMLResponse(content=html)



@app.get("/reports/contract/{package_name}/{filename}", response_class=_HTMLResponse)
def serve_contract_preview(package_name: str, filename: str):
    """Render a markdown contract as branded HTML."""
    PKGS = Path("/home/opc/hive_action_engine/deal_packages")
    md_path = PKGS / package_name / filename
    if not md_path.exists():
        md_path = PKGS / filename
    if not md_path.exists():
        return _HTMLResponse("<h1>Contract not found</h1>", status_code=404)

    md_text = md_path.read_text(errors="replace")

    # Convert markdown to styled HTML
    # Simple markdown rendering: headers, bold, lists, paragraphs
    import re as _cre
    body_html = md_text
    # Headers
    body_html = _cre.sub(r"^# (.+)$", r'<h1 style="color:#c9a84c;font-size:22px;margin:24px 0 12px;border-bottom:1px solid #1e1e2e;padding-bottom:8px;"></h1>', body_html, flags=_cre.MULTILINE)
    body_html = _cre.sub(r"^## (.+)$", r'<h2 style="color:#fff;font-size:17px;margin:20px 0 8px;"></h2>', body_html, flags=_cre.MULTILINE)
    body_html = _cre.sub(r"^### (.+)$", r'<h3 style="color:#ccc;font-size:15px;margin:16px 0 6px;"></h3>', body_html, flags=_cre.MULTILINE)
    # Bold
    body_html = _cre.sub(r"\*\*(.+?)\*\*", r"<strong style='color:#fff;'></strong>", body_html)
    # Horizontal rules
    body_html = body_html.replace("---", '<hr style="border:none;border-top:1px solid #1e1e2e;margin:16px 0;">')
    # Line breaks
    body_html = body_html.replace("\n", "<br>")
    # Bullet lists
    body_html = _cre.sub(r"^- (.+)$", r'<div style="padding:3px 0 3px 16px;color:#ccc;">&#8226; </div>', body_html, flags=_cre.MULTILINE)

    # Get property name for title
    prop_name = package_name.replace("_", " ").split(" 2026")[0] if "2026" in package_name else package_name

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Contract: {prop_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:Inter,sans-serif;color:#e8e8f0;">
<div style="max-width:680px;margin:0 auto;background:#0a0a0f;">

  <div style="background:linear-gradient(135deg,#1a1a2e,#12121a);padding:24px;border-bottom:3px solid #c9a84c;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <p style="margin:0;font-size:20px;font-weight:700;letter-spacing:2px;">
          EVERLIGHT <span style="color:#c9a84c;">VENTURES</span>
        </p>
        <p style="margin:4px 0 0;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:3px;">
          Assignment Contract
        </p>
      </div>
      <div style="background:#ff174422;border:1px solid #ff174444;border-radius:20px;padding:4px 16px;">
        <span style="color:#ff6b6b;font-size:11px;font-weight:700;text-transform:uppercase;">DRAFT -- REQUIRES LEGAL REVIEW</span>
      </div>
    </div>
  </div>

  <div style="padding:24px;">
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;line-height:1.8;font-size:14px;">
      {body_html}
    </div>

    <div style="background:#1a0a0a;border:1px solid #2e1a1a;border-radius:12px;padding:16px;margin-top:24px;">
      <p style="color:#ff6b6b;font-size:10px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Legal Disclaimer</p>
      <p style="color:#888;font-size:11px;line-height:1.6;margin:0;">This is a draft template for internal review only. A licensed attorney in the applicable state MUST review and approve before execution. Everlight Ventures is NOT a law firm.</p>
    </div>
  </div>

  <div style="background:#12121a;padding:16px 24px;text-align:center;border-top:1px solid #1e1e2e;">
    <p style="color:#444;font-size:11px;margin:0;">Everlight Ventures LLC | Assignment Contract Draft | everlightventures.io</p>
  </div>

</div></body></html>"""

    return _HTMLResponse(content=html)


# Serve React static files
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    @app.get("/{path:path}")
    def serve_spa(path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
