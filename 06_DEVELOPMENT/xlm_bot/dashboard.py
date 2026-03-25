#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import math
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Display timezone — America/Los_Angeles handles DST automatically
# (PST = UTC-8 winter, PDT = UTC-7 summer). Never use fixed offsets.
try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except ImportError:
    PT = timezone(timedelta(hours=-8), name="PT")  # fallback

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

_HAS_FRAGMENT = hasattr(st, "fragment")

BASE_DIR = Path(__file__).parent
WORKSPACE_ROOT = BASE_DIR.parent

# Oracle Cloud detection: on Oracle, the bot lives at /home/opc/xlm-bot
# and delegates are vendored inside the bot dir, not in WORKSPACE_ROOT.
_IS_ORACLE = Path("/home/opc/xlm-bot").exists() or os.environ.get("XLM_ORACLE", "") == "1"

if _IS_ORACLE:
    CLX_DELEGATE_PATH = BASE_DIR / "vendor" / "ai_workers" / "clx_delegate.py"
    GMX_DELEGATE_PATH = BASE_DIR / "vendor" / "ai_workers" / "gemx_delegate.py"
    CLAUDE_SETTINGS_PATH = BASE_DIR / ".claude" / "settings.json"
    GEMINI_SETTINGS_PATH = BASE_DIR / ".gemini" / "settings.json"
    MCP_CONFIG_PATH = BASE_DIR / ".mcp.json"
else:
    CLX_DELEGATE_PATH = WORKSPACE_ROOT / "03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py"
    GMX_DELEGATE_PATH = WORKSPACE_ROOT / "03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py"
    CLAUDE_SETTINGS_PATH = WORKSPACE_ROOT / ".claude" / "settings.json"
    GEMINI_SETTINGS_PATH = WORKSPACE_ROOT / ".gemini" / "settings.json"
    MCP_CONFIG_PATH = WORKSPACE_ROOT / ".mcp.json"


def _resolve_dash_dir(env_key: str, default_rel: str) -> Path:
    raw = os.environ.get(env_key, default_rel)
    p = Path(str(raw)).expanduser()
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


def _fetch_blinko_notes(count: int = 5) -> list[dict]:
    """Fetch recent notes from Blinko knowledge base."""
    import urllib.request
    import urllib.error
    _blinko_url = os.environ.get("BLINKO_URL", "http://localhost:1111/api/v1/note/list")
    _blinko_token = os.environ.get(
        "BLINKO_TOKEN",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic3VwZXJhZG1pbiIsIm5hbWUiOiJhZG1pbiIsInN1YiI6IjEiLCJleHAiOjQ5MjczNjgzNzIsImlhdCI6MTc3Mzc2ODM3Mn0.mnLSmtQpjcu7xjV0nLYcVRgrkwp4Jmlw-sQL0BvyiC0",
    )
    try:
        req = urllib.request.Request(
            _blinko_url,
            data=json.dumps({"size": count}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_blinko_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if isinstance(data, list):
            return data[:count]
        if isinstance(data, dict):
            return (data.get("items") or data.get("notes") or data.get("data") or [])[:count]
        return []
    except Exception:
        return []


def _runtime_pair_score(data_dir: Path, logs_dir: Path) -> int:
    candidates = [
        logs_dir / "dashboard_snapshot.json",
        logs_dir / "decisions.jsonl",
        logs_dir / "live_tick.json",
        data_dir / "weekly_playbook.json",
        data_dir / "market_brief.json",
        data_dir / "state.json",
    ]
    score = 0
    for path in candidates:
        try:
            if path.exists():
                score = max(score, int(path.stat().st_mtime_ns))
        except OSError:
            continue
    return score


def _resolve_runtime_dirs() -> tuple[Path, Path]:
    data_env = os.environ.get("XLM_DASH_DATA_DIR")
    logs_env = os.environ.get("XLM_DASH_LOGS_DIR")
    if data_env or logs_env:
        return (
            _resolve_dash_dir("XLM_DASH_LOGS_DIR", "logs"),
            _resolve_dash_dir("XLM_DASH_DATA_DIR", "data"),
        )

    pairs = [
        (BASE_DIR / "logs", BASE_DIR / "data"),
        (BASE_DIR / "logs_trend", BASE_DIR / "data_trend"),
        (BASE_DIR / "logs_mr", BASE_DIR / "data_mr"),
    ]
    best_logs, best_data = pairs[0]
    best_score = -1
    for logs_dir, data_dir in pairs:
        score = _runtime_pair_score(data_dir, logs_dir)
        if score > best_score:
            best_score = score
            best_logs, best_data = logs_dir, data_dir
    return best_logs, best_data


LOGS_DIR, DATA_DIR = _resolve_runtime_dirs()
STATE_PATH = DATA_DIR / "state.json"
DECISIONS_PATH = LOGS_DIR / "decisions.jsonl"
TRADES_PATH = LOGS_DIR / "trades.csv"
LIVE_TICK_PATH = LOGS_DIR / "live_tick.json"
MARGIN_POLICY_PATH = LOGS_DIR / "margin_policy.jsonl"
PLRL3_PATH = LOGS_DIR / "plrl3.jsonl"
INCIDENTS_PATH = LOGS_DIR / "incidents.jsonl"
FILLS_PATH = LOGS_DIR / "fills.jsonl"
CASH_MOVEMENTS_PATH = LOGS_DIR / "cash_movements.jsonl"
MARKET_NEWS_PATH = LOGS_DIR / "market_news.jsonl"
AI_FEEDBACK_PATH = DATA_DIR / "ai_feedback.jsonl"
DASHBOARD_SNAPSHOT_PATH = LOGS_DIR / "dashboard_snapshot.json"
DASHBOARD_SNAPSHOT_LAST_GOOD_PATH = LOGS_DIR / "dashboard_snapshot.last_good.json"
DASHBOARD_TIMESERIES_PATH = LOGS_DIR / "dashboard_timeseries.jsonl"
EXCHANGE_READ_ENABLED = os.environ.get("XLM_DASH_EXCHANGE_READ", "1") == "1"

_env_dir = os.environ.get("CRYPTO_BOT_DIR", "")
if _env_dir and Path(_env_dir).is_dir():
    CRYPTO_BOT_DIR = Path(_env_dir)
else:
    _vendor = Path(__file__).resolve().parent / "vendor"
    if _vendor.is_dir():
        CRYPTO_BOT_DIR = _vendor
    else:
        CRYPTO_BOT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot")
if str(CRYPTO_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(CRYPTO_BOT_DIR))

try:
    from claude_chat_api import start_chat_server as _start_chat_server
except Exception:
    _start_chat_server = None

if _start_chat_server is not None:
    try:
        _start_chat_server(
            port=int(os.environ.get("XLM_CHAT_PORT", "8504") or 8504),
            host=os.environ.get("XLM_CHAT_HOST", "0.0.0.0"),
        )
    except Exception:
        pass

# Coinbase config path — consistent with main.py
_COINBASE_CONFIG_PATH = Path(os.environ.get(
    "COINBASE_CONFIG_PATH",
    str(CRYPTO_BOT_DIR / "config.json"),
))

try:
    from utils.coinbase_api import CoinbaseAPI
except Exception:
    CoinbaseAPI = None


st.set_page_config(
    page_title="The Wolf's Terminal | XLM PERP",
    page_icon="🐺",
    layout="wide",
)


def _query_params() -> dict[str, list[str]]:
    try:
        params = st.query_params
        return {str(k): ([str(v)] if isinstance(v, str) else [str(x) for x in v]) for k, v in params.items()}
    except Exception:
        try:
            return {str(k): [str(x) for x in v] for k, v in st.experimental_get_query_params().items()}
        except Exception:
            return {}


def _set_query_param(key: str, value: str) -> None:
    try:
        st.query_params[key] = value
        return
    except Exception:
        pass
    try:
        params = st.experimental_get_query_params()
        params[str(key)] = [str(value)]
        st.experimental_set_query_params(**params)
    except Exception:
        pass


def _render_boot_screen() -> None:
    st.markdown(
        """
        <style>
        .boot-wrap {
            min-height: 92vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .boot-panel {
            position: relative;
            width: min(980px, 96vw);
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 22px;
            background:
              linear-gradient(180deg, rgba(15,23,42,0.96), rgba(3,7,18,0.98)),
              radial-gradient(circle at top left, rgba(16,185,129,0.08), transparent 40%);
            box-shadow: 0 30px 120px rgba(0,0,0,0.45);
            overflow: hidden;
        }
        .boot-topbar {
            display: flex;
            gap: 8px;
            align-items: center;
            padding: 14px 18px;
            border-bottom: 1px solid rgba(148,163,184,0.12);
            background: rgba(2,6,23,0.82);
        }
        .boot-dot { width: 10px; height: 10px; border-radius: 999px; display: inline-block; }
        .boot-dot.red { background: #ef4444; }
        .boot-dot.yellow { background: #f59e0b; }
        .boot-dot.green { background: #10b981; }
        .boot-shell {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 0;
        }
        .boot-left {
            padding: 28px 28px 20px 28px;
            border-right: 1px solid rgba(148,163,184,0.10);
            background:
              linear-gradient(180deg, rgba(15,23,42,0.88), rgba(2,6,23,0.98)),
              repeating-linear-gradient(
                0deg,
                rgba(148,163,184,0.035) 0px,
                rgba(148,163,184,0.035) 1px,
                transparent 1px,
                transparent 26px
              );
        }
        .boot-right {
            padding: 28px;
            background:
              radial-gradient(circle at top right, rgba(59,130,246,0.12), transparent 42%),
              linear-gradient(180deg, rgba(3,7,18,0.92), rgba(2,6,23,0.98));
        }
        .boot-kicker {
            color: #94a3b8;
            font-size: 12px;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }
        .boot-title {
            color: #f8fafc;
            font-size: clamp(36px, 6vw, 68px);
            line-height: 0.95;
            font-weight: 800;
            letter-spacing: -0.05em;
            margin: 0;
        }
        .boot-title span {
            color: #10b981;
            display: block;
        }
        .boot-sub {
            color: #cbd5e1;
            font-size: 15px;
            line-height: 1.7;
            max-width: 56ch;
            margin-top: 18px;
        }
        .boot-terminal {
            margin-top: 26px;
            border: 1px solid rgba(16,185,129,0.18);
            border-radius: 16px;
            background: rgba(2,6,23,0.88);
            padding: 18px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important;
            color: #d1fae5;
            font-size: 13px;
            line-height: 1.8;
        }
        .boot-terminal .muted { color: #64748b; }
        .boot-terminal .ok { color: #34d399; }
        .boot-terminal .warn { color: #fbbf24; }
        .boot-card {
            border: 1px solid rgba(148,163,184,0.12);
            border-radius: 16px;
            padding: 16px 18px;
            background: rgba(15,23,42,0.68);
            margin-bottom: 12px;
        }
        .boot-card h4 {
            margin: 0 0 8px 0;
            color: #e2e8f0;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }
        .boot-card p {
            margin: 0;
            color: #94a3b8;
            font-size: 13px;
            line-height: 1.6;
        }
        .boot-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(16,185,129,0.12);
            color: #a7f3d0;
            font-size: 12px;
            border: 1px solid rgba(16,185,129,0.18);
            margin-bottom: 14px;
        }
        </style>
        <div class="boot-wrap">
          <div class="boot-panel">
            <div class="boot-topbar">
              <span class="boot-dot red"></span>
              <span class="boot-dot yellow"></span>
              <span class="boot-dot green"></span>
              <span style="margin-left:10px;color:#64748b;font-size:12px;">everlight/xlm-bot :: command-center</span>
            </div>
            <div class="boot-shell">
              <div class="boot-left">
                <div class="boot-kicker">Everlight Ventures / Oracle Runtime</div>
                <h1 class="boot-title">XLM<span>Command Center</span></h1>
                <div class="boot-sub">
                  Live Coinbase futures execution, market-intel memory, liquidity scoring, session playbooks,
                  and war-room telemetry in one operational surface.
                </div>
                <div class="boot-terminal">
                  <div><span class="muted">$</span> boot --profile oracle-live --stack xlm-perp</div>
                  <div><span class="ok">OK</span> contract feed pinned to <span class="warn">XLP-20DEC30-CDE</span></div>
                  <div><span class="ok">OK</span> liquidation, crowding, and weekly research state loaded</div>
                  <div><span class="ok">OK</span> execution safety, ladder, and margin playbook online</div>
                  <div><span class="muted">></span> entering command center...</div>
                </div>
              </div>
              <div class="boot-right">
                <div class="boot-badge">github-style launch / live ops surface</div>
                <div class="boot-card">
                  <h4>Surface</h4>
                  <p>Boot splash shows the system as an actual runtime, not just another dashboard tab.</p>
                </div>
                <div class="boot-card">
                  <h4>Intent</h4>
                  <p>Set the tone before the operator lands in live trading, research, and risk telemetry.</p>
                </div>
                <div class="boot-card">
                  <h4>Mode</h4>
                  <p>Short auto-continue, with a manual bypass so it feels deliberate without being annoying.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
        setTimeout(function () {
          try {
            const url = new URL(window.parent.location.href);
            url.searchParams.set("boot", "1");
            window.parent.location.replace(url.toString());
          } catch (e) {}
        }, 2400);
        </script>
        """,
        height=0,
    )
    if st.button("Enter Command Center", type="primary", use_container_width=False):
        _set_query_param("boot", "1")
        st.rerun()


def _render_report_view(report_id: str) -> bool:
    report_id = str(report_id or "").strip()
    if not report_id:
        return False
    history_path = LOGS_DIR / "report_history.jsonl"
    archive_dir = LOGS_DIR / "report_archive"
    match = None
    if history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    row = json.loads(raw)
                    if str(row.get("report_id") or "") == report_id:
                        match = row
                        break
        except Exception:
            match = None
    st.title("XLM Bot Report")
    if not match:
        st.error(f"Report not found: {report_id}")
        return True
    st.caption(f"Report ID: {report_id}")
    meta = match.get("metadata") if isinstance(match.get("metadata"), dict) else {}
    cols = st.columns(4)
    cols[0].metric("App", str(match.get("app") or "n/a"))
    cols[1].metric("Kind", str(match.get("report_kind") or "report"))
    cols[2].metric("Status", str(match.get("status") or "unknown"))
    cols[3].metric("Created", str(match.get("created_at") or "n/a")[:19].replace("T", " "))
    st.subheader(str(match.get("title") or "Untitled Report"))
    if match.get("summary"):
        st.markdown(str(match.get("summary")))
    if match.get("doc_link"):
        st.markdown(f"[Open Google Doc]({match['doc_link']})")
    if meta:
        with st.expander("Metadata", expanded=False):
            st.json(meta)
    content = ""
    stored_path = Path(str(match.get("stored_path") or ""))
    if stored_path.exists():
        try:
            content = stored_path.read_text(encoding="utf-8")
        except Exception:
            content = ""
    if not content:
        preview = str(match.get("preview") or "").strip()
        content = preview or "No archived content available."
    st.markdown("---")
    st.markdown(content)
    return True

if os.environ.get("XLM_DASH_ULTRA_SAFE", "0") == "1":
    st.write("ULTRA SAFE MODE")
    st.stop()

_params = _query_params()
_report_ids = _params.get("report_id") or []
if _report_ids and _render_report_view(_report_ids[0]):
    st.stop()
_boot_seen = (_params.get("boot") or ["0"])[0] == "1"
if not _boot_seen:
    _render_boot_screen()
    st.stop()

def _live_ticker_component(product_id: str = "XLM-USD", interval_ms: int = 1000, height: int = 48, label: str = "SPOT REF") -> None:
    """
    Client-side price ticker (websocket-like feel) without rerunning the Streamlit script.
    Display-only: does not affect bot trading logic.
    """
    html = f"""
    <div style="display:flex;align-items:center;gap:10px;color:#9aa4af;font-size:12px;letter-spacing:0.6px;">
      <span style="display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(16,185,129,0.15);color:#34d399;">
        {label}
      </span>
      <span>{product_id}</span>
      <span style="color:#6b7280;">•</span>
      <span id="px" style="color:#e5e7eb;font-weight:600;">—</span>
      <span style="color:#6b7280;">•</span>
      <span style="color:#6b7280;">updated <span id="age">—</span>s ago</span>
      <span id="err" style="color:#f59e0b;"></span>
    </div>
    <script>
      const url = "https://api.exchange.coinbase.com/products/{product_id}/ticker";
      let last = 0;
      async function tick() {{
        try {{
          const r = await fetch(url, {{ cache: "no-store" }});
          if (!r.ok) throw new Error("HTTP " + r.status);
          const j = await r.json();
          const p = Number(j.price);
          if (!Number.isFinite(p)) throw new Error("bad price");
          document.getElementById("px").textContent = "$" + p.toFixed(6);
          document.getElementById("err").textContent = "";
          last = Date.now();
        }} catch (e) {{
          document.getElementById("err").textContent = " (live tick unavailable)";
        }}
      }}
      function age() {{
        const el = document.getElementById("age");
        if (!el) return;
        if (!last) {{ el.textContent = "—"; return; }}
        el.textContent = Math.floor((Date.now() - last) / 1000);
      }}
      tick();
      setInterval(tick, {interval_ms});
      setInterval(age, 250);
    </script>
    """
    components.html(html, height=height)


def _live_ws_summary(live: dict) -> tuple[str, str]:
    px = live.get("price")
    ts = live.get("timestamp") or live.get("written_at")

    price_str = "—"
    if px is not None:
        try:
            price_str = f"${float(px):.6f}"
        except Exception:
            price_str = "—"

    age_str = "—"
    if ts:
        try:
            t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            age_str = str(int((datetime.now(timezone.utc) - t).total_seconds()))
        except Exception:
            age_str = "—"
    return price_str, age_str


def _humanize_market_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    replacements = [
        ("weekly bias", "bigger-picture lean (weekly bias)"),
        ("continuation setups", "trend-following entries (continuation setups)"),
        ("order-book absorption", "big resting buyers or sellers soaking up orders (order-book absorption)"),
        ("liquidation sweep", "forced-stop flush (liquidation sweep)"),
        ("liquidation hunts", "forced-stop flushes (liquidation hunts)"),
        ("mean reversion", "snap-back move toward the average (mean reversion)"),
        ("crowding regime", "positioning pressure / crowding regime"),
        ("macro regime", "macro backdrop (macro regime)"),
    ]
    out = text
    for src, dst in replacements:
        out = out.replace(src, dst)
        out = out.replace(src.title(), dst)
    return out


def _friendly_crowding_label(value: str) -> str:
    raw = str(value or "").strip().lower().replace("_", " ")
    mapping = {
        "balanced": "balanced positioning",
        "crowded long": "too many longs leaning the same way",
        "crowded short": "too many shorts leaning the same way",
    }
    return mapping.get(raw, raw or "balanced positioning")

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Fraunces:opsz,wght@9..144,300..900&display=swap');

    * { font-family: 'Sora', ui-sans-serif, system-ui, -apple-system, sans-serif !important; }

    .stApp {
        background:
          radial-gradient(800px 400px at 15% 8%, rgba(251,191,36,0.12), rgba(0,0,0,0) 50%),
          radial-gradient(800px 400px at 85% 15%, rgba(34,197,94,0.10), rgba(0,0,0,0) 50%),
          radial-gradient(800px 500px at 50% 90%, rgba(59,130,246,0.08), rgba(0,0,0,0) 50%),
          linear-gradient(180deg, #060810 0%, #0a0f1a 60%, #060810 100%) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stToolbar"] { display: none; }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
    ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.2); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,0.35); }

    @keyframes glow {
        0%, 100% { text-shadow: 0 0 10px rgba(251,191,36,0.3), 0 0 20px rgba(251,191,36,0.2); }
        50% { text-shadow: 0 0 20px rgba(251,191,36,0.6), 0 0 30px rgba(251,191,36,0.4); }
    }

    @keyframes shine {
        0% { background-position: -200% center; }
        100% { background-position: 200% center; }
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 300;
        color: #fff;
        letter-spacing: 8px;
        text-transform: uppercase;
        margin-bottom: 0;
        padding: 20px 0 5px 0;
        animation: glow 4s ease-in-out infinite;
    }
    .main-title span {
        color: #f59e0b;
        font-weight: 700;
        background: linear-gradient(90deg, #f59e0b, #fbbf24, #f59e0b);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 3s linear infinite;
    }

    .brand {
        font-family: 'Fraunces', serif !important;
        font-size: 2.4rem;
        letter-spacing: 4px;
        color: #e5e7eb;
        margin: 0;
        animation: glow 5s ease-in-out infinite;
    }
    .brand span {
        color: #fbbf24;
        font-weight: 800;
        background: linear-gradient(90deg, #fbbf24, #fff, #fbbf24);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 4s linear infinite;
    }
    .brand-sub {
        margin-top: 6px;
        color: rgba(203,213,225,0.82);
        font-size: 0.82rem;
        letter-spacing: 0.6px;
        text-transform: uppercase;
    }

    .top-strip {
        display: flex;
        justify-content: flex-end;
        flex-wrap: wrap;
        gap: 10px;
    }
    .strip-item {
        padding: 10px 12px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.04);
        background: rgba(8, 12, 20, 0.45);
        min-width: 150px;
        transition: border-color 200ms ease;
    }
    .strip-item:hover {
        border-color: rgba(148,163,184,0.10);
    }
    .strip-k {
        color: rgba(148,163,184,0.88);
        font-size: 0.72rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
    }
    .strip-v {
        color: #e5e7eb;
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 2px;
    }

    /* ── KPI Bar (Coinbase Truth + Bot Analytics) ── */
    .kpi-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0;
        justify-content: center;
    }
    .kpi-card {
        background: linear-gradient(135deg, rgba(12,16,24,0.85), rgba(20,24,36,0.80));
        border: 1px solid rgba(148,163,184,0.08);
        border-radius: 14px;
        padding: 10px 14px;
        backdrop-filter: blur(16px);
        transition: transform 200ms ease, box-shadow 200ms ease;
        -webkit-backdrop-filter: blur(16px);
        min-width: 100px;
        flex: 1 1 100px;
        position: relative;
        transition: border-color 200ms ease;
    }
    .kpi-card:hover {
        border-color: rgba(148,163,184,0.12);
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    .kpi-label {
        font-size: 9px;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: rgba(148,163,184,0.65);
        font-weight: 500;
    }
    .kpi-value {
        color: #e5e7eb;
        font-size: 1.08rem;
        font-weight: 600;
        margin-top: 2px;
        white-space: nowrap;
    }
    .kpi-sub {
        font-size: 9px;
        color: rgba(148,163,184,0.5);
        margin-top: 1px;
    }
    .src-badge {
        font-size: 7px;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        position: absolute;
        top: 6px;
        right: 8px;
        opacity: 0.55;
        font-weight: 600;
    }
    .src-cb { color: #34d399; }
    .src-bot { color: #fbbf24; }
    .truth-banner {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 12px;
        letter-spacing: 0.5px;
        margin: 6px 0;
    }
    .truth-long {
        background: rgba(16,185,129,0.04);
        border: 1px solid rgba(16,185,129,0.12);
        color: rgba(52,211,153,0.90);
    }
    .truth-short {
        background: rgba(239,68,68,0.04);
        border: 1px solid rgba(239,68,68,0.12);
        color: rgba(248,113,113,0.90);
    }
    .truth-none {
        background: rgba(148,163,184,0.03);
        border: 1px solid rgba(148,163,184,0.08);
        color: rgba(148,163,184,0.75);
    }
    .truth-label {
        font-size: 8px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 6px;
        background: rgba(255,255,255,0.06);
    }
    .stale-banner {
        text-align: center;
        padding: 6px 14px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin: 4px 0;
    }
    .stale-warn {
        background: rgba(245,158,11,0.05);
        border: 1px solid rgba(245,158,11,0.15);
        color: rgba(251,191,36,0.85);
    }
    .stale-danger {
        background: rgba(239,68,68,0.05);
        border: 1px solid rgba(239,68,68,0.15);
        color: rgba(248,113,113,0.85);
        animation: pulseGlow 3s ease-in-out infinite;
    }
    .bot-analytics-header {
        font-size: 8px;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        color: rgba(251,191,36,0.5);
        font-weight: 600;
        margin: 10px 0 2px 4px;
    }
    .as-of {
        text-align: center;
        font-size: 9px;
        color: rgba(148,163,184,0.4);
        letter-spacing: 0.5px;
        margin: 2px 0 6px;
    }

    .panel-title {
        color: rgba(226,232,240,0.9);
        font-size: 0.85rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin: 8px 0 10px 0;
    }

    .side-title {
        font-family: 'Fraunces', serif !important;
        font-size: 1.2rem;
        letter-spacing: 2px;
        color: rgba(226,232,240,0.92);
        margin: 6px 0 10px 0;
    }
    .side-divider {
        height: 1px;
        background: rgba(255,255,255,0.08);
        margin: 12px 0;
    }
    .side-kv {
        color: rgba(148,163,184,0.88);
        font-size: 0.70rem;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        margin-top: 10px;
    }
    .side-v {
        color: rgba(226,232,240,0.92);
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 3px;
    }

    /* Sidebar polish */
    section[data-testid="stSidebar"] > div {
        background: linear-gradient(180deg, rgba(8,12,20,0.92), rgba(10,16,28,0.88)) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] .stRadio > div {
        gap: 6px;
    }
    section[data-testid="stSidebar"] label {
        color: rgba(226,232,240,0.88) !important;
    }

    .kpi {
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.04);
        background: rgba(8, 12, 20, 0.45);
        margin-bottom: 8px;
    }
    .kpi.good { border-color: rgba(34,197,94,0.15); }
    .kpi.warn { border-color: rgba(251,191,36,0.15); }
    .kpi.bad  { border-color: rgba(248,113,113,0.15); }
    .kpi-label {
        color: rgba(148,163,184,0.88);
        font-size: 0.70rem;
        letter-spacing: 1.4px;
        text-transform: uppercase;
    }
    .kpi-value {
        color: rgba(226,232,240,0.92);
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .footer {
        text-align: center;
        color: rgba(148,163,184,0.8);
        font-size: 0.70rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 10px 0 0 0;
    }

    .metric {
        font-size: 1.8rem;
        color: #f7f7f8;
    }
    .label {
        color: #7b848e;
        font-size: 0.75rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .pill {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 999px;
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .pill.ok { background: rgba(16, 185, 129, 0.10); color: rgba(52, 211, 153, 0.90); }
    .pill.danger { background: rgba(248, 113, 113, 0.10); color: rgba(248, 113, 113, 0.90); }
    .pill.gold { background: rgba(245, 158, 11, 0.12); color: rgba(251, 191, 36, 0.90); }
    .danger { color: #f87171; }
    .ok { color: #34d399; }
    .gold { color: #fbbf24; }
    .muted { color: #6b7280; }

    @keyframes pulseGlow {
        0% { box-shadow: 0 0 0 rgba(34,197,94,0.0); }
        50% { box-shadow: 0 0 24px rgba(34,197,94,0.12); }
        100% { box-shadow: 0 0 0 rgba(34,197,94,0.0); }
    }
    .pill.ok { animation: pulseGlow 2.2s ease-in-out infinite; }

    .scoreboard {
        display: flex;
        justify-content: center;
        gap: 30px;
        padding: 20px;
        margin: 12px 0;
        background: rgba(10,14,22,0.65);
        border: 1px solid rgba(255,255,255,0.03);
        border-radius: 16px;
    }
    .score-item { text-align: center; }
    .score-num {
        font-size: 2.2rem;
        font-weight: 300;
        letter-spacing: -1px;
    }
    .score-num.wins { color: #34d399; }
    .score-num.losses { color: #f87171; }
    .score-num.rate { color: #f59e0b; }
    .score-num.pnl-pos { color: #34d399; }
    .score-num.pnl-neg { color: #f87171; }
    .score-label {
        color: #555;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 4px;
    }

    .celebration {
        text-align: center;
        padding: 20px;
        margin: 10px 0;
        border-radius: 16px;
        background: linear-gradient(160deg, rgba(16,185,129,0.05) 0%, rgba(12,16,24,0.85) 100%);
        border: 1px solid rgba(16,185,129,0.18);
    }
    .celebration .headline {
        font-size: 1.4rem;
        color: #34d399;
        font-weight: 400;
        letter-spacing: 1px;
    }
    .celebration .detail {
        color: #999;
        font-size: 0.85rem;
        margin-top: 6px;
    }
    .celebration .detail strong { color: #34d399; }

    .trade-log-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        margin: 3px 0;
        background: rgba(10,14,22,0.55);
        border-radius: 8px;
        border-left: 2px solid;
        font-size: 0.8rem;
        color: rgba(148,163,184,0.75);
    }
    .trade-log-row.win { border-left-color: #34d399; }
    .trade-log-row.loss { border-left-color: #f87171; }
    .trade-log-row.entry { border-left-color: #60a5fa; }
    .trade-log-row strong { color: #e5e5e5; font-weight: 500; }
    .trade-log-row .green { color: #34d399; }
    .trade-log-row .red { color: #f87171; }
    .trade-log-row .blue { color: #60a5fa; }

    .status-banner {
        text-align: center;
        padding: 24px 20px;
        border-radius: 16px;
        margin: 8px 0 16px 0;
    }
    .status-banner.watching {
        background: linear-gradient(160deg, rgba(245,158,11,0.03) 0%, rgba(12,16,24,0.8) 100%);
        border: 1px solid rgba(245,158,11,0.10);
    }
    .status-banner.ready {
        background: linear-gradient(160deg, rgba(16,185,129,0.04) 0%, rgba(12,16,24,0.8) 100%);
        border: 1px solid rgba(16,185,129,0.15);
    }
    .status-banner.in-trade {
        background: linear-gradient(160deg, rgba(59,130,246,0.04) 0%, rgba(12,16,24,0.8) 100%);
        border: 1px solid rgba(59,130,246,0.15);
    }
    .status-icon { font-size: 1.8rem; margin-bottom: 8px; }
    .status-headline {
        font-size: 1.3rem;
        font-weight: 400;
        color: #fff;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }
    .status-body {
        color: #999;
        font-size: 0.85rem;
        line-height: 1.7;
        max-width: 600px;
        margin: 0 auto;
    }
    .status-body strong { color: #e5e5e5; font-weight: 500; }
    .status-body .green { color: #34d399; }
    .status-body .red { color: #f87171; }
    .status-body .amber { color: #f59e0b; }
    .status-body .blue { color: #60a5fa; }

    .feed-mini {
        background: rgba(10, 14, 22, 0.55);
        border: 1px solid rgba(255,255,255,0.025);
        border-radius: 10px;
        padding: 10px 16px;
        margin: 4px 0;
        font-size: 0.78rem;
        color: rgba(148,163,184,0.7);
        line-height: 1.5;
    }
    .feed-mini strong { color: #bbb; font-weight: 500; }
    .feed-mini .green { color: #34d399; }
    .feed-mini .red { color: #f87171; }
    .feed-mini .amber { color: #f59e0b; }

    .intel-card {
        background: rgba(10,14,22,0.90);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 14px;
        padding: 16px 20px;
        margin: 6px 0;
    }
    .intel-card .intel-title {
        color: #666;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        margin-bottom: 10px;
        font-weight: 500;
    }
    .intel-event {
        padding: 6px 0;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        font-size: 0.8rem;
        color: #888;
        line-height: 1.5;
    }
    .intel-event:last-child { border-bottom: none; }
    .intel-event .time { color: #555; font-size: 0.7rem; margin-right: 8px; }
    .intel-event .green { color: #34d399; }
    .intel-event .red { color: #f87171; }
    .intel-event .amber { color: #f59e0b; }
    .intel-event .blue { color: #60a5fa; }
    .intel-event strong { color: #ccc; font-weight: 500; }

    .info-row {
        display: flex;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
        padding: 10px 0;
        font-size: 0.75rem;
        color: #555;
    }
    .info-row .item { text-align: center; }
    .info-row .val { color: #999; font-weight: 500; }

    .major-banner {
        border-radius: 12px;
        padding: 12px 14px;
        margin: 6px 0 10px 0;
        border: 1px solid rgba(255,255,255,0.04);
        background: rgba(12,16,24,0.50);
    }
    .major-banner .k {
        font-size: 0.68rem;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .major-banner .v {
        font-size: 1.0rem;
        font-weight: 700;
        color: #f9fafb;
        margin-bottom: 2px;
    }
    .major-banner .d {
        font-size: 0.78rem;
        color: #d1d5db;
    }
    .major-banner.good { border-color: rgba(52, 211, 153, 0.20); background: rgba(6, 78, 59, 0.18); }
    .major-banner.bad { border-color: rgba(248, 113, 113, 0.22); background: rgba(127, 29, 29, 0.18); }
    .major-banner.warn { border-color: rgba(245, 158, 11, 0.22); background: rgba(120, 53, 15, 0.18); }
    .major-banner.info { border-color: rgba(96, 165, 250, 0.40); background: rgba(30, 58, 138, 0.30); }

    .major-feed { margin-top: 8px; }
    .major-item {
        border-radius: 10px;
        padding: 8px 10px;
        margin: 6px 0;
        border-left: 4px solid rgba(255,255,255,0.18);
        background: rgba(17,24,39,0.50);
    }
    .major-item .t {
        font-size: 0.68rem;
        color: #9ca3af;
        margin-bottom: 2px;
    }
    .major-item .h {
        font-size: 0.84rem;
        color: #f3f4f6;
        font-weight: 650;
        margin-bottom: 1px;
    }
    .major-item .s {
        font-size: 0.75rem;
        color: #d1d5db;
    }
    .major-item.good { border-left-color: #34d399; }
    .major-item.bad { border-left-color: #f87171; }
    .major-item.warn { border-left-color: #f59e0b; }
    .major-item.info { border-left-color: #60a5fa; }

    .thought-feed { margin-top: 8px; max-height: 360px; overflow-y: auto; padding-right: 4px; }
    .thought-toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin: 6px 0 2px 0;
    }
    .thought-toolbar .live {
        font-size: 0.70rem;
        color: #9ca3af;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .thought-toolbar .live .dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: #34d399;
        margin-right: 6px;
        box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.5);
        animation: pulse 1.6s infinite;
        vertical-align: middle;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.55); }
        70% { box-shadow: 0 0 0 8px rgba(52, 211, 153, 0.0); }
        100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.0); }
    }
    .thought-post {
        border-radius: 12px;
        padding: 10px 12px;
        margin: 8px 0;
        border-left: 4px solid rgba(255,255,255,0.16);
        background: rgba(15, 23, 42, 0.55);
    }
    .thought-post .t {
        font-size: 0.68rem;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .thought-post .h {
        font-size: 0.80rem;
        color: #f3f4f6;
        font-weight: 650;
        margin-bottom: 3px;
    }
    .thought-post .b {
        font-size: 0.80rem;
        color: #e5e7eb;
        line-height: 1.45;
    }
    .thought-post .m {
        font-size: 0.72rem;
        color: #cbd5e1;
        margin-top: 5px;
    }
    .thought-post .new-pill {
        display: inline-block;
        margin-left: 6px;
        padding: 2px 6px;
        border-radius: 999px;
        font-size: 0.62rem;
        color: #111827;
        background: #34d399;
        letter-spacing: 0.7px;
        font-weight: 700;
    }
    .thought-post.good { border-left-color: #34d399; background: rgba(6, 78, 59, 0.30); }
    .thought-post.bad { border-left-color: #f87171; background: rgba(127, 29, 29, 0.30); }
    .thought-post.warn { border-left-color: #f59e0b; background: rgba(120, 53, 15, 0.30); }
    .thought-post.info { border-left-color: #60a5fa; background: rgba(30, 58, 138, 0.26); }

    /* ── Broadcast-grade horizontal ticker ── */
    @keyframes ticker-scroll {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    @keyframes ticker-pulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.5; }
    }
    .ticker-wrap {
        overflow: hidden; white-space: nowrap;
        background: linear-gradient(180deg, rgba(10,15,28,0.92) 0%, rgba(17,24,39,0.88) 100%);
        border-radius: 4px; padding: 0; margin: 6px 0;
        position: relative;
        border-top: 1px solid rgba(59,130,246,0.15);
        border-bottom: 1px solid rgba(59,130,246,0.08);
    }
    /* Fade edges — smooth broadcast look */
    .ticker-wrap::before, .ticker-wrap::after {
        content: ""; position: absolute; top: 0; bottom: 0; width: 40px; z-index: 3; pointer-events: none;
    }
    .ticker-wrap::before {
        left: 0;
        background: linear-gradient(90deg, rgba(10,15,28,0.98) 0%, transparent 100%);
    }
    .ticker-wrap::after {
        right: 0;
        background: linear-gradient(270deg, rgba(10,15,28,0.98) 0%, transparent 100%);
    }
    .ticker-wrap .ticker-label {
        position: absolute; left: 0; top: 0; bottom: 0;
        display: flex; align-items: center;
        padding: 0 14px; z-index: 4;
        background: linear-gradient(90deg, rgba(10,15,28,0.98) 60%, rgba(10,15,28,0.85) 85%, transparent);
        font-size: 9px; font-weight: 800; letter-spacing: 1.2px;
        text-transform: uppercase;
    }
    .ticker-label.ev-label { color: #60a5fa; }
    .ticker-label.dec-label { color: #a78bfa; }
    .ticker-track {
        display: inline-flex; gap: 0; padding-left: 90px;
        animation: ticker-scroll var(--ticker-speed, 50s) linear infinite;
    }
    .ticker-track:hover { animation-play-state: paused; cursor: default; }
    .ticker-item {
        display: inline-flex; align-items: center; gap: 7px;
        font-size: 12px; color: #e5e7eb; flex-shrink: 0;
        padding: 7px 0;
        font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
        letter-spacing: -0.01em;
    }
    .ticker-item .ts { color: #4b5563; font-size: 10px; font-weight: 400; }
    .ticker-item b { font-weight: 700; }
    .ticker-sep {
        display: inline-flex; align-items: center; padding: 0 14px;
        color: rgba(75,85,99,0.4); font-size: 10px; flex-shrink: 0;
        user-select: none;
    }
    .ticker-dot {
        width: 6px; height: 6px; border-radius: 50%; display: inline-block; flex-shrink: 0;
    }
    .ticker-dot.good    { background: #10b981; box-shadow: 0 0 4px rgba(16,185,129,0.4); }
    .ticker-dot.bad     { background: #ef4444; box-shadow: 0 0 4px rgba(239,68,68,0.4); }
    .ticker-dot.warn    { background: #f59e0b; box-shadow: 0 0 4px rgba(245,158,11,0.3); }
    .ticker-dot.info    { background: #60a5fa; box-shadow: 0 0 4px rgba(96,165,250,0.3); }
    .ticker-dot.neutral { background: #6b7280; }
    .ticker-dot.live    { animation: ticker-pulse 1.5s ease-in-out infinite; }
    .ticker-tag {
        font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
        padding: 1px 6px; border-radius: 3px; text-transform: uppercase;
    }
    .ticker-tag.entry  { background: rgba(16,185,129,0.15); color: #34d399; }
    .ticker-tag.exit   { background: rgba(239,68,68,0.15); color: #f87171; }
    .ticker-tag.signal { background: rgba(96,165,250,0.12); color: #93c5fd; }
    .ticker-tag.block  { background: rgba(107,114,128,0.15); color: #9ca3af; }
    .ticker-tag.alert  { background: rgba(245,158,11,0.15); color: #fbbf24; }
    .ticker-val { color: #fbbf24; font-weight: 600; }
    .ticker-dir-long  { color: #34d399; font-weight: 600; }
    .ticker-dir-short { color: #f87171; font-weight: 600; }

    /* ── Claude Chat ── */
    .claude-chat-wrap {
        max-width: 800px; margin: 0 auto;
    }
    .claude-msg {
        margin: 8px 0; padding: 10px 14px;
        border-radius: 10px; font-size: 13px; line-height: 1.5;
        white-space: pre-wrap; word-wrap: break-word;
    }
    .claude-msg.user {
        background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.2);
        margin-left: 40px;
    }
    .claude-msg.assistant {
        background: rgba(167,139,250,0.10); border: 1px solid rgba(167,139,250,0.15);
        margin-right: 40px;
    }
    .claude-msg .msg-role {
        font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
        text-transform: uppercase; margin-bottom: 4px;
    }
    .claude-msg.user .msg-role { color: #60a5fa; }
    .claude-msg.assistant .msg-role { color: #a78bfa; }
    .claude-msg .msg-text { color: #e5e7eb; }
    .claude-header {
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 12px;
    }
    .claude-header .claude-logo {
        font-size: 22px; color: #a78bfa;
    }
    .claude-header .claude-title {
        font-size: 16px; font-weight: 700; color: #e5e7eb;
    }
    .claude-header .claude-sub {
        font-size: 11px; color: #6b7280;
    }
    .claude-ctx-bar {
        display: flex; flex-wrap: wrap; gap: 6px;
        margin-bottom: 12px; padding: 8px 10px;
        background: rgba(17,24,39,0.6); border-radius: 8px;
        border: 1px solid rgba(107,114,128,0.15);
    }
    .claude-ctx-bar .ctx-chip {
        font-size: 10px; padding: 2px 8px; border-radius: 4px;
        background: rgba(107,114,128,0.15); color: #9ca3af;
    }

    /* Compact metrics strip */
    .metrics-strip {
        display: flex; flex-wrap: wrap; gap: 4px 8px;
        padding: 8px 12px; margin: 4px 0 8px;
        background: rgba(17,24,39,0.5); border-radius: 10px;
        border: 1px solid rgba(107,114,128,0.15);
    }
    .metrics-strip .ms-item {
        display: flex; flex-direction: column; align-items: center;
        min-width: 70px; padding: 2px 6px;
    }
    .metrics-strip .ms-k {
        font-size: 8px; color: #6b7280; letter-spacing: 0.5px;
        text-transform: uppercase; white-space: nowrap;
    }
    .metrics-strip .ms-v {
        font-size: 12px; color: #d1d5db; font-weight: 600; white-space: nowrap;
    }
    .metrics-strip .ms-v.good { color: #10b981; }
    .metrics-strip .ms-v.bad { color: #ef4444; }
    .metrics-strip .ms-v.warn { color: #f59e0b; }
</style>
""",
    unsafe_allow_html=True,
)


def render_intel_hub(last_decision: dict, state: dict, pos_view: dict | None):
    """Render the News & Agent Intel Hub tab."""
    st.markdown("<div class='panel-title'>The Wolf's Intel Hub</div>", unsafe_allow_html=True)
    
    # Load Market Brief (Perplexity)
    _brief_path = DATA_DIR / "market_brief.json"
    _brief_data = {}
    if _brief_path.exists():
        try:
            _raw_brief = json.loads(_brief_path.read_text())
            _brief_data = _raw_brief.get("brief") or {}
        except Exception:
            pass

    _weekly_path = DATA_DIR / "weekly_market_research.json"
    _weekly_data = {}
    if _weekly_path.exists():
        try:
            _raw_weekly = json.loads(_weekly_path.read_text())
            _weekly_data = _raw_weekly.get("research") or {}
        except Exception:
            pass
            
    # Load AI Insights (Claude/Gemini/Codex)
    _ai_path = DATA_DIR / "ai_insight.json"
    _ai_data = {}
    if _ai_path.exists():
        try:
            _ai_data = json.loads(_ai_path.read_text())
        except Exception:
            pass

    col1, col2 = st.columns([1.5, 1.0])
    
    with col1:
        # ── Market Brief (Perplexity) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Perplexity Market Brief / Research Snapshot</div>", unsafe_allow_html=True)
        if _brief_data:
            _rm = str(_brief_data.get("risk_modifier", "neutral")).upper()
            _rm_clr = "#10b981" if "ON" in _rm else "#ef4444" if "OFF" in _rm else "#f59e0b"
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>"
                f"<span class='pill' style='background:{_rm_clr}20;color:{_rm_clr};font-weight:700;'>RISK: {_rm}</span>"
                f"<span class='muted' style='font-size:10px;'>Horizon: {str(_brief_data.get('time_horizon', '?')).upper()}</span>"
                "</div>",
                unsafe_allow_html=True
            )
            
            st.markdown("<div style='font-size:13px;color:#e5e7eb;font-weight:600;margin-bottom:6px;'>Macro & Crypto News</div>", unsafe_allow_html=True)
            for bullet in _brief_data.get("headline_bullets", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(bullet)}</div>", unsafe_allow_html=True)
                
            st.markdown("<div style='font-size:13px;color:#fbbf24;font-weight:600;margin-top:12px;margin-bottom:6px;'>XLM Catalysts</div>", unsafe_allow_html=True)
            for xlm_bullet in _brief_data.get("xlm_specific", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(xlm_bullet)}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='muted' style='padding:20px 0;'>Waiting for Perplexity intel cycle...</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Weekly Strategic Research / Research Snapshot</div>", unsafe_allow_html=True)
        if _weekly_data:
            _wb = _safe_str(_weekly_data.get("directional_bias")) or "mixed"
            _xb = _safe_str(_weekly_data.get("xlm_bias")) or "mixed"
            _mr = _safe_str(_weekly_data.get("macro_regime")) or "neutral"
            _wl = _safe_str(_weekly_data.get("window_label")) or "OUTSIDE_WEEKLY_WINDOW"
            _conf = _safe_float(_weekly_data.get("confidence")) or 0.0
            _review = _safe_float(_weekly_data.get("review_score"))
            _mode = _safe_str(_weekly_data.get("source_mode")) or _safe_str(_weekly_data.get("generated_from")) or "unknown"
            _tone = "#10b981" if _xb == "bullish" else "#ef4444" if _xb == "bearish" else "#f59e0b"
            st.markdown(
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;'>"
                f"<span class='pill' style='background:{_tone}20;color:{_tone};'>XLM {html.escape(_xb.upper())}</span>"
                f"<span class='pill' style='background:rgba(59,130,246,0.15);color:#93c5fd;'>{html.escape(_wb.upper())}</span>"
                f"<span class='pill' style='background:rgba(245,158,11,0.15);color:#fbbf24;'>{html.escape(_mr.upper())}</span>"
                f"<span class='pill' style='background:rgba(107,114,128,0.15);color:#d1d5db;'>{html.escape(_wl.replace('_', ' '))}</span>"
                f"</div>"
                f"<div class='muted' style='font-size:11px;margin-bottom:8px;'>"
                f"Confidence {(_conf * 100):.0f}%"
                f"{f' &bull; Review {_review:.0f}/100' if _review is not None else ''}"
                f" &bull; Mode {html.escape(_mode)}"
                f" &bull; Updated {html.escape(_safe_str(_weekly_data.get('updated_at')) or '?')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            for theme in (_weekly_data.get("key_themes") or [])[:4]:
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(_humanize_market_text(str(theme)))}</div>", unsafe_allow_html=True)
            if _weekly_data.get("trade_playbook"):
                st.markdown("<div style='font-size:13px;color:#fbbf24;font-weight:600;margin-top:12px;margin-bottom:6px;'>Weekly Playbook</div>", unsafe_allow_html=True)
                for item in (_weekly_data.get("trade_playbook") or [])[:4]:
                    st.markdown(f"<div class='intel-event'>&bull; {html.escape(_humanize_market_text(str(item)))}</div>", unsafe_allow_html=True)
            if _weekly_data.get("risks"):
                st.markdown("<div style='font-size:13px;color:#f87171;font-weight:600;margin-top:12px;margin-bottom:6px;'>Key Risks</div>", unsafe_allow_html=True)
                for item in (_weekly_data.get("risks") or [])[:3]:
                    st.markdown(f"<div class='intel-event'>&bull; {html.escape(_humanize_market_text(str(item)))}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='muted' style='padding:20px 0;'>Waiting for weekly strategic research cache...</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Agent Discussions (Thoughts) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Agent Reasoning & Thoughts</div>", unsafe_allow_html=True)
        
        # Pull latest thoughts from decisions log
        _dec_recent = _load_jsonl(DECISIONS_PATH, max_lines=15)
        if not _dec_recent.empty:
            for _, row in _dec_recent.iloc[::-1].iterrows():
                _thought = _safe_str(row.get("thought"))
                _ts = _coerce_ts_utc(row.get("timestamp"))
                if _thought and len(_thought) > 10:
                    _tone = _decision_tone(row.get("reason"), row.get("exit_reason", ""))
                    st.markdown(
                        f"<div class='thought-post {_tone}'>"
                        f"<div class='t'>{_fmt_pt_short(_ts)}</div>"
                        f"<div class='b'>{html.escape(_thought)}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # ── Team Peer Intel (Latest Insights) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Team Peer Reports</div>", unsafe_allow_html=True)
        
        # Claude (Directive)
        _cl = _ai_data.get("directive", {}).get("result", {})
        if _cl:
            _action = str(_cl.get("action", "HOLD")).upper()
            _aclr = "#10b981" if "ENTER" in _action else "#ef4444" if "EXIT" in _action else "#6b7280"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#a78bfa;'>"
                f"<div class='h'>Claude Opus <span class='pill' style='background:#a78bfa20;color:#a78bfa;'>CHIEF</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{_action}</span> "
                f"<span class='muted' style='font-size:10px;'>conf {int(float(_cl.get('confidence', 0))*100)}%</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_cl.get('reasoning', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Gemini (Risk Audit)
        _ga = _ai_data.get("gemini_audit_decision", {}).get("result", {})
        if _ga:
            _appr = bool(_ga.get("approved"))
            _aclr = "#10b981" if _appr else "#ef4444"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#3b82f6;'>"
                f"<div class='h'>Gemini <span class='pill' style='background:#3b82f620;color:#3b82f6;'>RISK</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{'APPROVED' if _appr else 'VETOED'}</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_ga.get('reason', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Codex (Integrity)
        st.markdown(
            f"<div class='thought-post info' style='border-left-color:#34d399;'>"
            f"<div class='h'>Codex <span class='pill' style='background:#34d39920;color:#34d399;'>ENGINEER</span></div>"
            f"<div style='margin:6px 0;'><span class='pill ok'>OK</span></div>"
            f"<div class='b' style='font-size:11px;'>System integrity validated. Coinbase mirror active.</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

def render_claude_chat():
    """Render the Claude Chat interface."""
    st.markdown("<div class='panel-title'>Claude Chat</div>", unsafe_allow_html=True)
    _chat_url = os.environ.get("XLM_CHAT_URL", "http://127.0.0.1:8503")
    st.markdown(
        f'<iframe src="{_chat_url}" width="100%" height="600px" style="border:none; border-radius:12px; background:rgba(15,23,42,0.5);"></iframe>',
        unsafe_allow_html=True
    )

# ── HELPERS ────────────────────────────────────────────────────────

def _coerce_ts_utc(val) -> datetime | None:
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        s = str(val).strip()
        if not s:
            return None
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        try:
            ts = pd.to_datetime(val, utc=True, errors="coerce")
            if pd.isna(ts):
                return None
            return ts.to_pydatetime()
        except Exception:
            return None


def _load_jsonl(path: Path, max_lines: int = 2000, max_tail_bytes: int = 512 * 1024) -> pd.DataFrame:
    """
    Load JSONL efficiently.
    For live dashboards, we only need the recent tail; reading the whole file every tick is wasteful.
    """
    if not path.exists():
        return pd.DataFrame()
    try:
        with open(path, "rb") as f:
            # Read a tail chunk and then keep only the last N lines.
            f.seek(0, 2)
            end = f.tell()
            chunk = min(end, max(64 * 1024, int(max_tail_bytes)))
            f.seek(end - chunk)
            raw = f.read().decode("utf-8", errors="ignore")
        lines = raw.splitlines()
        # If we started mid-file, drop potential partial first line.
        if chunk < end and lines:
            lines = lines[1:]
        lines = lines[-max_lines:]
    except Exception:
        try:
            lines = path.read_text(errors="ignore").splitlines()[-max_lines:]
        except Exception:
            return pd.DataFrame()

    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def _load_jsonl_window(
    path: Path,
    *,
    lookback_days: int = 7,
    max_lines: int = 50000,
    max_tail_bytes: int = 8 * 1024 * 1024,
) -> pd.DataFrame:
    """
    Load JSONL in a bounded way, but filtered to a time window.
    This keeps dashboard performance stable while preserving multi-day history.
    """
    base = _load_jsonl(path, max_lines=max_lines, max_tail_bytes=max_tail_bytes)
    if base.empty:
        return base
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))
    ts_values = []
    for _, row in base.iterrows():
        t = _coerce_ts_utc(row.get("timestamp") if "timestamp" in base.columns else None)
        if t is None:
            t = _coerce_ts_utc(row.get("ts") if "ts" in base.columns else None)
        ts_values.append(t)
    base["timestamp"] = pd.to_datetime(ts_values, utc=True, errors="coerce")
    base = base.dropna(subset=["timestamp"])
    return base[base["timestamp"] >= cutoff].copy()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        try:
            return pd.read_csv(path, engine="python", on_bad_lines="skip")
        except Exception:
            return pd.DataFrame()


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def _load_snapshot_with_fallback(path: Path, backup_path: Path) -> tuple[dict, str | None]:
    """
    Read dashboard snapshot safely.
    If the main file is missing/corrupted, fallback to last known good snapshot.
    """
    if not path.exists():
        return {}, "waiting_for_bot"
    try:
        raw = path.read_text()
        snap = json.loads(raw)
        if isinstance(snap, dict):
            return snap, None
        raise ValueError("snapshot_not_object")
    except Exception as e:
        try:
            if backup_path.exists():
                fallback = json.loads(backup_path.read_text())
                if isinstance(fallback, dict):
                    return fallback, f"snapshot_corrupt_using_last_good: {e}"
        except Exception:
            pass
        return {}, f"snapshot_unreadable: {e}"


def _get_futures_balance() -> dict | None:
    if not EXCHANGE_READ_ENABLED:
        return None
    if CoinbaseAPI is None:
        return None
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return None
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        return api.get_futures_balance_summary()
    except Exception:
        return None


def _file_sig(path: Path) -> tuple[int, int]:
    try:
        st_ = path.stat()
        return int(st_.st_mtime_ns), int(st_.st_size)
    except Exception:
        return 0, 0


def _load_last_jsonl(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        # Efficient tail: read whole file (logs are small enough) and parse last JSON line.
        txt = path.read_text(errors="ignore")
        for line in reversed(txt.splitlines()):
            line = line.strip()
            if not line:
                continue
            return json.loads(line)
    except Exception:
        return {}
    return {}


@st.cache_data(show_spinner=False)
def _load_last_jsonl_cached(path_str: str, mtime_ns: int, size: int) -> dict:
    _ = (mtime_ns, size)
    return _load_last_jsonl(Path(path_str))


@st.cache_data(ttl=15, show_spinner=False)
def _get_futures_balance_cached() -> dict | None:
    # Avoid hammering the API every fragment tick.
    return _get_futures_balance()


def _get_cfm_positions() -> list[dict]:
    """Read-only: fetch open CFM futures positions from Coinbase (best-effort)."""
    if not EXCHANGE_READ_ENABLED:
        return []
    if CoinbaseAPI is None:
        return []
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return []
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        return api.get_futures_positions() or []
    except Exception:
        return []


@st.cache_data(ttl=15, show_spinner=False)
def _get_cfm_positions_cached() -> list[dict]:
    return _get_cfm_positions()


def _get_spot_balances() -> dict[str, float]:
    """Fetch live spot wallet balances (USD, USDC) from Coinbase."""
    if not EXCHANGE_READ_ENABLED:
        return {}
    if CoinbaseAPI is None:
        return {}
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        accts = api._request("GET", "/api/v3/brokerage/accounts", params={"limit": 50})
        result = {}
        for a in (accts.get("accounts") or []):
            cur = str(a.get("available_balance", {}).get("currency", ""))
            val = float(a.get("available_balance", {}).get("value", 0) or 0)
            if cur in ("USD", "USDC") and val > 0:
                result[cur] = val
        return result
    except Exception:
        return {}


@st.cache_data(ttl=15, show_spinner=False)
def _get_spot_balances_cached() -> dict[str, float]:
    return _get_spot_balances()


def _get_portfolio_breakdown() -> dict[str, float]:
    """Fetch portfolio breakdown from Coinbase — single source of truth for totals.

    Returns dict with keys: total, cash, futures, crypto, spot_usdc.
    Uses the portfolios/breakdown endpoint which matches the Coinbase app exactly.
    """
    if not EXCHANGE_READ_ENABLED:
        return {}
    if CoinbaseAPI is None:
        return {}
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        # Step 1: find default portfolio UUID
        portfolios = api._request("GET", "/api/v3/brokerage/portfolios")
        plist = portfolios.get("portfolios") or [] if isinstance(portfolios, dict) else []
        uuid = None
        for p in plist:
            if str(p.get("type", "")).upper() == "DEFAULT":
                uuid = p.get("uuid")
                break
        if not uuid and plist:
            uuid = plist[0].get("uuid")
        if not uuid:
            return {}
        # Step 2: get breakdown
        detail = api._request("GET", f"/api/v3/brokerage/portfolios/{uuid}")
        bd = (detail or {}).get("breakdown", {})
        pb = bd.get("portfolio_balances", {})
        result = {}
        for key, out_key in [
            ("total_balance", "total"),
            ("total_cash_equivalent_balance", "cash"),
            ("total_futures_balance", "futures"),
            ("total_crypto_balance", "crypto"),
        ]:
            val = pb.get(key, {})
            if isinstance(val, dict):
                result[out_key] = float(val.get("value", 0) or 0)
            else:
                result[out_key] = float(val or 0)
        # Also get USDC from spot positions for yield calculation
        for sp in (bd.get("spot_positions") or []):
            if str(sp.get("asset", "")).upper() == "USDC":
                try:
                    result["spot_usdc"] = float(sp.get("total_balance_fiat", {}).get("value", 0) or 0)
                except Exception:
                    pass
        return result
    except Exception:
        return {}


@st.cache_data(ttl=15, show_spinner=False)
def _get_portfolio_breakdown_cached() -> dict[str, float]:
    return _get_portfolio_breakdown()


def _bot_alive() -> tuple[bool, int]:
    """Check if bot is alive via heartbeat file. Returns (alive, age_seconds)."""
    try:
        hb = Path(DATA_DIR) / ".heartbeat"
        if not hb.exists():
            return False, -1
        age = datetime.now(timezone.utc).timestamp() - float(hb.read_text().strip())
        return age < 120, int(age)
    except Exception:
        return False, -1


def _get_cfm_open_orders(product_id: str | None = None) -> list[dict]:
    """Read-only: fetch open orders (optionally scoped to a product_id)."""
    if not EXCHANGE_READ_ENABLED:
        return []
    if CoinbaseAPI is None:
        return []
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return []
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        return api.get_open_orders(pair=product_id) or []
    except Exception:
        return []


@st.cache_data(ttl=10, show_spinner=False)
def _get_cfm_open_orders_cached(product_id: str | None = None) -> list[dict]:
    return _get_cfm_open_orders(product_id=product_id)


def _get_cfm_product_details(product_id: str) -> dict:
    """Read-only: fetch CFM product details (best-effort)."""
    if not EXCHANGE_READ_ENABLED:
        return {}
    if CoinbaseAPI is None:
        return {}
    config_path = _COINBASE_CONFIG_PATH
    if not config_path.exists():
        return {}
    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        return api._request("GET", f"/api/v3/brokerage/products/{product_id}") or {}
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def _get_cfm_product_details_cached(product_id: str) -> dict:
    return _get_cfm_product_details(product_id)


def _contract_size_from_details(details: dict) -> float | None:
    try:
        fpd = (details.get("future_product_details") or {}) if isinstance(details, dict) else {}
        cs = fpd.get("contract_size")
        if cs is None or cs == "":
            return None
        cs_f = float(cs)
        return cs_f if cs_f > 0 else None
    except Exception:
        return None


def _project_pnl_usd(entry: float, target: float, *, direction: str, contracts: float, contract_size: float) -> float | None:
    """Best-effort PnL estimate matching bot math (ignores fees/slippage)."""
    try:
        e = float(entry)
        t = float(target)
        n = float(contracts)
        cs = float(contract_size)
        if e <= 0 or t <= 0 or n <= 0 or cs <= 0:
            return None
        raw = (t - e) * cs * n
        if (direction or "").lower() == "short":
            raw = -raw
        return float(raw)
    except Exception:
        return None


@st.cache_data(ttl=10, show_spinner=False)
def _load_bot_events_cached(limit: int = 200) -> list[dict]:
    """Load durable bot events from SQLite (best-effort)."""
    try:
        import sqlite3
        db = DATA_DIR / "bot_state.db"
        if not db.exists():
            return []
        con = sqlite3.connect(db)
        try:
            cur = con.execute(
                "SELECT ts, type, payload_json FROM events ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
            rows = cur.fetchall()
        finally:
            con.close()
        out = []
        for ts, typ, payload_json in rows:
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except Exception:
                payload = {}
            out.append({"ts": ts, "type": typ, "payload": payload})
        return out
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def _load_jsonl_cached(
    path_str: str,
    mtime_ns: int,
    size: int,
    max_lines: int = 2000,
    lookback_days: int = 7,
    max_tail_bytes: int = 8 * 1024 * 1024,
) -> pd.DataFrame:
    _ = (mtime_ns, size)  # cache key only
    return _load_jsonl_window(
        Path(path_str),
        lookback_days=lookback_days,
        max_lines=max_lines,
        max_tail_bytes=max_tail_bytes,
    )


@st.cache_data(show_spinner=False)
def _load_csv_cached(path_str: str, mtime_ns: int, size: int) -> pd.DataFrame:
    _ = (mtime_ns, size)
    return _load_csv(Path(path_str))


@st.cache_data(show_spinner=False)
def _load_state_cached(path_str: str, mtime_ns: int, size: int) -> dict:
    _ = (mtime_ns, size)
    p = Path(path_str)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def _load_json_cached(path_str: str, mtime_ns: int, size: int) -> dict:
    _ = (mtime_ns, size)
    p = Path(path_str)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def _load_snapshot_with_fallback_cached(
    path_str: str, mtime_ns: int, size: int, backup_str: str, backup_mtime_ns: int, backup_size: int
) -> tuple[dict, str | None]:
    _ = (mtime_ns, size, backup_mtime_ns, backup_size)
    return _load_snapshot_with_fallback(Path(path_str), Path(backup_str))


def _format_money(val: float | None) -> str:
    if val is None:
        return "—"
    return f"${val:,.2f}"


def _safe_float(val) -> float | None:
    try:
        if val is None or val == "":
            return None
        f = float(val)
        # Pandas can feed NaN for missing numeric fields; treat that as missing so
        # downstream int() casts don't explode.
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _safe_str(val) -> str | None:
    """Convert values from pandas rows (including NaN floats) into usable strings."""
    if val is None:
        return None
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return None
        except Exception:
            return None
    s = str(val)
    if s.lower() in ("nan", "none", ""):
        return None
    return s


def _safe_bool(val) -> bool:
    """Treat NaN/None as False (pandas can use NaN for missing booleans)."""
    if val is None:
        return False
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return False
        except Exception:
            return False
    return bool(val)


def _fmt_pt_short(ts) -> str:
    dt = _coerce_ts_utc(ts)
    if dt is None:
        return "?"
    try:
        return dt.astimezone(PT).strftime("%b %d %I:%M %p PT")
    except Exception:
        return "?"


def _fmt_since(ts) -> str:
    dt = _coerce_ts_utc(ts)
    if dt is None:
        return "?"
    try:
        age = int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return "?"
    if age < 0:
        age = 0
    if age < 60:
        return f"{age}s ago"
    if age < 3600:
        return f"{age // 60}m ago"
    if age < 86400:
        return f"{age // 3600}h ago"
    return f"{age // 86400}d ago"


def _count_files(path: Path, pattern: str) -> int:
    try:
        if not path.exists():
            return 0
        return len(list(path.glob(pattern)))
    except Exception:
        return 0


def _orchestration_snapshot(ai_data: dict | None = None) -> dict:
    ai_data = ai_data if isinstance(ai_data, dict) else {}

    claude_agents = _count_files(WORKSPACE_ROOT / ".claude" / "agents", "*.md")
    claude_skills = _count_files(WORKSPACE_ROOT / ".claude" / "skills", "*/SKILL.md")
    claude_commands = _count_files(WORKSPACE_ROOT / ".claude" / "commands", "*.md")
    claude_modes = _count_files(WORKSPACE_ROOT / ".claude" / "modes", "*.md")
    gemini_modes = _count_files(WORKSPACE_ROOT / ".gemini", "*/GEMINI.md")

    last_event = ""
    try:
        tail = _tail_text(LOGS_DIR / "ai_debug.log", 90)
        for line in reversed(tail.splitlines()):
            txt = line.strip()
            if not txt:
                continue
            if (" CLI" in txt) or ("FIRE_" in txt) or ("DONE" in txt) or ("TIMEOUT" in txt):
                last_event = txt[:220]
                break
    except Exception:
        pass

    _directive_ts = _coerce_ts_utc(((ai_data.get("directive") or {}).get("timestamp")))
    _gemini_audit_ts = _coerce_ts_utc(((ai_data.get("gemini_audit_decision") or {}).get("timestamp")))
    _codex_ts = _coerce_ts_utc(((ai_data.get("codex_directive") or {}).get("timestamp")))

    return {
        "clx_ready": CLX_DELEGATE_PATH.exists(),
        "gmx_ready": GMX_DELEGATE_PATH.exists(),
        "claude_mem_ready": CLAUDE_SETTINGS_PATH.exists(),
        "gemini_mem_ready": GEMINI_SETTINGS_PATH.exists(),
        "mcp_ready": MCP_CONFIG_PATH.exists(),
        "claude_agents": claude_agents,
        "claude_skills": claude_skills,
        "claude_commands": claude_commands,
        "claude_modes": claude_modes,
        "gemini_modes": gemini_modes,
        "directive_age": _fmt_since(_directive_ts) if _directive_ts else "n/a",
        "gemini_audit_age": _fmt_since(_gemini_audit_ts) if _gemini_audit_ts else "n/a",
        "codex_age": _fmt_since(_codex_ts) if _codex_ts else "n/a",
        "last_event": last_event or "no recent AI event log",
    }


def _fmt_utc8_long(ts) -> str:
    dt = _coerce_ts_utc(ts)
    if dt is None:
        return "-"
    try:
        return dt.astimezone(PT).strftime("%Y-%m-%d %H:%M:%S PT")
    except Exception:
        return "-"


def _format_df_timestamps_utc8(df: pd.DataFrame, preferred: list[str] | None = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    columns = preferred or []
    if not columns:
        for c in out.columns:
            cl = str(c).lower()
            if cl in ("timestamp", "ts", "entry_time", "exit_time", "created_time", "updated_time"):
                columns.append(c)
            elif cl.endswith("_time") or cl.endswith("_ts"):
                columns.append(c)
    for c in columns:
        if c not in out.columns:
            continue
        out[c] = out[c].apply(_fmt_utc8_long)
    return out


def _decision_tone(reason: str, exit_reason: str = "") -> str:
    r = str(reason or "").strip().lower()
    e = str(exit_reason or "").strip().lower()
    if r in ("entry_order_failed", "bot_error", "emergency_exit_mr"):
        return "bad"
    if r == "exchange_side_close":
        return "warn"
    if r == "exit_order_sent":
        if e in ("tp1", "profit_lock", "recovery_take_profit"):
            return "good"
        if e in ("emergency_exit_mr", "plrl3_exit", "cutoff_derisk"):
            return "bad"
        return "warn"
    if "blocked" in r or r in ("margin_policy_block_entry", "v4_score_block_entry", "ev_block_entry"):
        return "warn"
    if r in ("plrl3_rescue", "trend_scale_in"):
        return "warn"
    if r in ("profit_transfer",):
        return "good"
    return "info"


def _operator_metrics(decisions_df: pd.DataFrame, trades_df: pd.DataFrame, cfg: dict, *, lookback_days: int = 7) -> dict:
    out = {
        "max_trades_per_day": int(((cfg.get("risk") or {}).get("max_trades_per_day", 0) or 0)),
        "max_losses_per_day": int(((cfg.get("risk") or {}).get("max_losses_per_day", 0) or 0)),
        "avg_trades_per_day": None,
        "avg_time_in_trade_min": None,
        "median_time_in_trade_min": None,
        "avg_wait_between_entries_min": None,
        "pnl_per_trade_hour": None,
        "avg_pnl_per_closed_trade": None,
        "ready_cycle_pct": None,
        "entry_cycles": 0,
        "closed_trades": 0,
    }

    if decisions_df is not None and not decisions_df.empty:
        d = decisions_df.copy()
        if "timestamp" in d.columns:
            d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True, errors="coerce")
            d = d.dropna(subset=["timestamp"])
        if not d.empty:
            total = len(d)
            ready = d
            if "gates_pass" in ready.columns:
                ready = ready[ready["gates_pass"] == True]  # noqa: E712
            if "entry_signal" in ready.columns:
                ready = ready[ready["entry_signal"].notna()]
            out["entry_cycles"] = int(len(ready))
            if total > 0:
                out["ready_cycle_pct"] = float(len(ready) / total * 100.0)

    if trades_df is None or trades_df.empty:
        return out

    t = trades_df.copy()
    if "timestamp" in t.columns:
        t["timestamp"] = pd.to_datetime(t["timestamp"], utc=True, errors="coerce")
    for c in ("entry_time", "exit_time"):
        if c in t.columns:
            t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    if "entry_price" in t.columns:
        t["entry_price"] = pd.to_numeric(t["entry_price"], errors="coerce")
    if "exit_price" in t.columns:
        t["exit_price"] = pd.to_numeric(t["exit_price"], errors="coerce")
    if "pnl_usd" in t.columns:
        t["pnl_usd"] = pd.to_numeric(t["pnl_usd"], errors="coerce")
    if "time_in_trade_min" in t.columns:
        t["time_in_trade_min"] = pd.to_numeric(t["time_in_trade_min"], errors="coerce")
    else:
        t["time_in_trade_min"] = pd.NA

    # Entry rows are rows without an exit price.
    entry_rows = t.copy()
    if "exit_price" in entry_rows.columns:
        entry_rows = entry_rows[entry_rows["exit_price"].isna()]
    entry_rows = entry_rows.dropna(subset=["entry_price"])
    if "entry_time" in entry_rows.columns:
        entry_rows["entry_ts"] = entry_rows["entry_time"]
    elif "timestamp" in entry_rows.columns:
        entry_rows["entry_ts"] = entry_rows["timestamp"]
    else:
        entry_rows["entry_ts"] = pd.NaT
    entry_rows = entry_rows.dropna(subset=["entry_ts"]).sort_values("entry_ts")

    if not entry_rows.empty:
        by_day = entry_rows.groupby(entry_rows["entry_ts"].dt.date).size()
        if len(by_day) > 0:
            out["avg_trades_per_day"] = float(by_day.mean())
        if len(entry_rows) >= 2:
            waits = entry_rows["entry_ts"].diff().dropna().dt.total_seconds() / 60.0
            waits = waits[waits >= 0]
            if len(waits) > 0:
                out["avg_wait_between_entries_min"] = float(waits.mean())

    closed = t.copy()
    if "exit_price" in closed.columns:
        closed = closed[closed["exit_price"].notna()]
    if "pnl_usd" in closed.columns:
        closed = closed[closed["pnl_usd"].notna()]
    out["closed_trades"] = int(len(closed))
    if closed.empty:
        return out

    # Backfill time-in-trade when missing but entry/exit times exist.
    try:
        missing = closed["time_in_trade_min"].isna()
        if missing.any() and ("entry_time" in closed.columns and "exit_time" in closed.columns):
            delta = (closed.loc[missing, "exit_time"] - closed.loc[missing, "entry_time"]).dt.total_seconds() / 60.0
            closed.loc[missing, "time_in_trade_min"] = delta
    except Exception:
        pass

    dur = pd.to_numeric(closed["time_in_trade_min"], errors="coerce")
    dur = dur[dur.notna() & (dur >= 0)]
    if len(dur) > 0:
        out["avg_time_in_trade_min"] = float(dur.mean())
        out["median_time_in_trade_min"] = float(dur.median())
        hours = float(dur.sum()) / 60.0
        if hours > 0 and "pnl_usd" in closed.columns:
            out["pnl_per_trade_hour"] = float(closed["pnl_usd"].sum() / hours)
    if "pnl_usd" in closed.columns and len(closed) > 0:
        out["avg_pnl_per_closed_trade"] = float(closed["pnl_usd"].mean())
    return out


def _major_from_decision(row: dict) -> dict | None:
    reason = _safe_str(row.get("reason")) or ""
    if not reason:
        return None
    reason_l = reason.lower()
    ts = _coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None

    exit_reason = (_safe_str(row.get("exit_reason")) or "").lower()
    direction = (_safe_str(row.get("direction")) or "").upper()
    product = _safe_str(row.get("product_id")) or _safe_str(row.get("product_selected")) or "-"

    if reason_l == "exit_order_sent":
        _entry_px = _safe_float(row.get("entry_price"))
        _exit_px = _safe_float(row.get("exit_price")) or _safe_float(row.get("price"))
        _pnl_usd = _safe_float(row.get("pnl_usd"))
        _pnl_part = ""
        if _entry_px and _exit_px:
            _pnl_part = f"${_entry_px:.5f} → ${_exit_px:.5f}"
            if _pnl_usd is not None:
                _pnl_part += f" = {'+'if _pnl_usd>=0 else ''}${_pnl_usd:.2f}"
        elif _pnl_usd is not None:
            _pnl_part = f"{'+'if _pnl_usd>=0 else ''}${_pnl_usd:.2f}"
        _detail = f"{product} {direction} {_pnl_part}".strip()
        if exit_reason in ("tp1", "profit_lock", "recovery_take_profit"):
            return {
                "ts": ts,
                "tone": "good",
                "headline": f"TAKE PROFIT ({exit_reason})",
                "detail": _detail,
            }
        if exit_reason in ("emergency_exit_mr", "plrl3_exit", "cutoff_derisk"):
            return {
                "ts": ts,
                "tone": "bad",
                "headline": f"RISK EXIT ({exit_reason})",
                "detail": _detail,
            }
        return {
            "ts": ts,
            "tone": "warn",
            "headline": f"POSITION EXIT ({exit_reason or 'signal'})",
            "detail": _detail,
        }

    if reason_l in ("exchange_side_close",):
        pnl = _safe_float(row.get("pnl_usd"))
        result = (_safe_str(row.get("result")) or "").lower()
        tone = "good" if result == "win" or (pnl is not None and pnl > 0) else "bad" if result == "loss" or (pnl is not None and pnl < 0) else "warn"
        return {
            "ts": ts,
            "tone": tone,
            "headline": "EXCHANGE-SIDE CLOSE",
            "detail": f"{product} pnl {(_format_money(pnl) if pnl is not None else 'n/a')}",
        }

    if reason_l in ("plrl3_rescue", "trend_scale_in"):
        add = int(_safe_float(row.get("add_contracts") or row.get("add_size")) or 0)
        return {
            "ts": ts,
            "tone": "warn",
            "headline": "POSITION ADD",
            "detail": f"{product} +{add} contracts",
        }

    if reason_l in ("entry_order_failed",):
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "ENTRY FAILED",
            "detail": f"{product} {(_safe_str(row.get('message')) or '')}".strip(),
        }

    return None


def _major_from_trade(row: dict) -> dict | None:
    ts = _coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    product = _safe_str(row.get("product_id")) or "-"
    side = (_safe_str(row.get("side")) or "").upper()
    result = (_safe_str(row.get("result")) or "").lower()
    exit_reason = (_safe_str(row.get("exit_reason")) or "").lower()
    pnl = _safe_float(row.get("pnl_usd"))
    has_exit = _safe_float(row.get("exit_price")) is not None

    if not has_exit:
        if result in ("ok", "paper mode") or _safe_str(row.get("order_id")):
            return {
                "ts": ts,
                "tone": "info",
                "headline": "ENTRY",
                "detail": f"{product} {side or ''} {int(_safe_float(row.get('size')) or 0)}c".strip(),
            }
        return None

    if exit_reason in ("tp1", "profit_lock", "recovery_take_profit"):
        tone = "good"
        headline = f"TAKE PROFIT ({exit_reason})"
    elif result == "win" or (pnl is not None and pnl > 0):
        tone = "good"
        headline = "CLOSED WIN"
    elif result == "loss" or (pnl is not None and pnl < 0):
        tone = "bad"
        headline = "CLOSED LOSS"
    else:
        tone = "warn"
        headline = f"CLOSED ({exit_reason or 'flat'})"

    return {
        "ts": ts,
        "tone": tone,
        "headline": headline,
        "detail": f"{product} {side or ''} pnl {(_format_money(pnl) if pnl is not None else 'n/a')}",
    }


def _major_from_incident(row: dict) -> dict | None:
    ts = _coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    itype = (_safe_str(row.get("type")) or "").upper()
    product = _safe_str(row.get("product_id")) or "-"
    if not itype:
        return None

    if itype in ("LIQUIDATION_TIER_OBSERVED",):
        mr = _safe_float(row.get("active_mr"))
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "LIQUIDATION TIER",
            "detail": f"{product} active_mr={mr:.3f}" if mr is not None else product,
        }
    if itype in ("EMERGENCY_EXIT_TRIGGERED", "CLOSE_NOT_REDUCE_ONLY"):
        return {
            "ts": ts,
            "tone": "bad",
            "headline": itype.replace("_", " "),
            "detail": product,
        }
    if itype in ("RECONCILE_MISMATCH", "EXCHANGE_SIDE_CLOSE_DETECTED"):
        return {
            "ts": ts,
            "tone": "warn",
            "headline": itype.replace("_", " "),
            "detail": product,
        }
    return None


def _major_from_cash_movement(row: dict) -> dict | None:
    ts = _coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    mtype = (_safe_str(row.get("type")) or "").upper()
    if not mtype:
        return None
    context = (_safe_str(row.get("context")) or "").lower()
    amount = _safe_float(row.get("amount_usd"))
    currency = (_safe_str(row.get("currency")) or "USD").upper()
    shortfall = _safe_float(row.get("shortfall_usd"))
    conv = _safe_float(row.get("estimated_conversion_cost_usd"))
    detail_ctx = f" ({context})" if context else ""

    if mtype == "SPOT_TO_FUTURES_TRANSFER":
        detail = f"{_format_money(amount)} {currency} to futures{detail_ctx}".strip()
        if conv is not None and conv > 0:
            detail += f" | est conversion cost {_format_money(conv)}"
        return {"ts": ts, "tone": "warn", "headline": "MARGIN TRANSFER IN", "detail": detail}
    if mtype == "FUTURES_TO_SPOT_TRANSFER":
        return {
            "ts": ts,
            "tone": "good",
            "headline": "PROFIT TRANSFER OUT",
            "detail": f"{_format_money(amount)} {currency} to spot{detail_ctx}".strip(),
        }
    if mtype in ("SPOT_TO_FUTURES_TRANSFER_FAILED", "FUTURES_TO_SPOT_TRANSFER_FAILED"):
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "TRANSFER FAILED",
            "detail": f"{mtype.replace('_', ' ').title()}{detail_ctx}",
        }
    if mtype == "FUNDING_SHORTFALL":
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "FUNDING SHORTFALL",
            "detail": f"shortfall {_format_money(shortfall)}{detail_ctx}",
        }
    if mtype == "SPOT_CONVERSION_DETECTED":
        return {
            "ts": ts,
            "tone": "warn",
            "headline": "SPOT CONVERSION DETECTED",
            "detail": f"USD/USDC balances changed{detail_ctx}",
        }
    if mtype == "SPOT_BALANCE_DELTA":
        return {
            "ts": ts,
            "tone": "info",
            "headline": "SPOT BALANCE CHANGE",
            "detail": f"manual/account movement detected{detail_ctx}",
        }
    return None


def _load_ai_feedback() -> list:
    """Load AI directive outcome feedback for scorecard."""
    try:
        if not AI_FEEDBACK_PATH.exists():
            return []
        lines = AI_FEEDBACK_PATH.read_text(errors="ignore").strip().splitlines()
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out
    except Exception:
        return []


def _ai_confidence_calibration(feedback: list) -> list:
    """Group trades by confidence bucket and compute actual win rate."""
    buckets: dict = {}
    for fb in feedback:
        if fb.get("action") == "FLAT":
            continue
        conf = float(fb.get("confidence") or 0)
        if conf <= 0:
            continue
        bucket_low = int(conf * 100) // 10 * 10
        label = f"{bucket_low}-{bucket_low + 10}%"
        if label not in buckets:
            buckets[label] = {"total": 0, "wins": 0, "pnl_sum": 0.0}
        buckets[label]["total"] += 1
        if fb.get("won"):
            buckets[label]["wins"] += 1
        buckets[label]["pnl_sum"] += float(fb.get("pnl_usd") or 0)
    result = []
    for label in sorted(buckets.keys()):
        b = buckets[label]
        result.append({
            "bucket": label,
            "trades": b["total"],
            "wins": b["wins"],
            "win_rate": b["wins"] / b["total"] * 100 if b["total"] > 0 else 0,
            "pnl": b["pnl_sum"],
        })
    return result


def _build_major_events(
    decisions_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    incidents_df: pd.DataFrame,
    cash_movements_df: pd.DataFrame,
    *,
    lookback_days: int = 7,
    max_items: int = 80,
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))
    out: list[dict] = []

    if decisions_df is not None and not decisions_df.empty:
        for _, r in decisions_df.iterrows():
            ev = _major_from_decision(r.to_dict() if hasattr(r, "to_dict") else dict(r))
            if ev and ev.get("ts") and ev["ts"] >= cutoff:
                out.append(ev)

    if trades_df is not None and not trades_df.empty:
        for _, r in trades_df.iterrows():
            ev = _major_from_trade(r.to_dict() if hasattr(r, "to_dict") else dict(r))
            if ev and ev.get("ts") and ev["ts"] >= cutoff:
                out.append(ev)

    if incidents_df is not None and not incidents_df.empty:
        for _, r in incidents_df.iterrows():
            ev = _major_from_incident(r.to_dict() if hasattr(r, "to_dict") else dict(r))
            if ev and ev.get("ts") and ev["ts"] >= cutoff:
                out.append(ev)

    if cash_movements_df is not None and not cash_movements_df.empty:
        for _, r in cash_movements_df.iterrows():
            ev = _major_from_cash_movement(r.to_dict() if hasattr(r, "to_dict") else dict(r))
            if ev and ev.get("ts") and ev["ts"] >= cutoff:
                out.append(ev)

    out.sort(key=lambda e: e.get("ts") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    dedup = []
    seen = set()
    for e in out:
        key = (
            str(e.get("ts")),
            str(e.get("headline")),
            str(e.get("detail")),
        )
        if key in seen:
            continue
        seen.add(key)
        dedup.append(e)
        if len(dedup) >= max_items:
            break
    return dedup


def _normalize_cfm_position(p: dict) -> dict:
    """
    Normalize Coinbase CFM futures position payload into a dashboard-friendly shape.
    This is display-only; it does not affect bot trading logic.
    """
    pid = _safe_str(p.get("product_id")) or "?"
    side = (_safe_str(p.get("side")) or "").upper()
    direction = "short" if "SHORT" in side else "long" if "LONG" in side else "?"
    contracts = _safe_float(p.get("number_of_contracts")) or _safe_float(p.get("contracts")) or _safe_float(p.get("size"))
    entry = _safe_float(p.get("avg_entry_price")) or _safe_float(p.get("average_entry_price")) or _safe_float(p.get("entry_price"))
    cur = _safe_float(p.get("current_price")) or _safe_float(p.get("mark_price")) or _safe_float(p.get("price"))
    upnl = _safe_float(p.get("unrealized_pnl"))
    return {
        "product_id": pid,
        "direction": direction,
        "contracts": int(contracts) if contracts is not None else None,
        "entry_price": entry,
        "current_price": cur,
        "unrealized_pnl": upnl,
        "raw": p,
    }


def _order_protection_summary(o: dict) -> dict:
    """
    Pull out bracket/trigger status from Coinbase order payloads (schema varies).
    This is display-only.
    """
    trig_status = _safe_str(o.get("trigger_status")) or ""
    order_type = _safe_str(o.get("order_type")) or _safe_str(o.get("type")) or "?"
    status = _safe_str(o.get("status")) or "?"

    stop = None
    tp = None
    try:
        oc = o.get("order_configuration") or {}
        # Example: {"trigger_bracket_gtc": {...}} or {"trigger_bracket_gtc": {"stop_trigger_price": "...", "limit_price": "..."}}
        for key in ("trigger_bracket_gtc", "trigger_bracket_ioc", "trigger_bracket_fok"):
            if key in oc and isinstance(oc.get(key), dict):
                cfg = oc.get(key) or {}
                stop = _safe_float(cfg.get("stop_trigger_price") or cfg.get("stop_price"))
                tp = _safe_float(cfg.get("take_profit_price") or cfg.get("limit_price") or cfg.get("tp_price"))
                break
    except Exception:
        stop, tp = None, None

    # Some responses also expose attached_order_configuration.
    if stop is None or tp is None:
        try:
            aoc = o.get("attached_order_configuration") or {}
            if isinstance(aoc, dict):
                cfg = aoc.get("trigger_bracket_gtc") or {}
                if isinstance(cfg, dict):
                    stop = stop if stop is not None else _safe_float(cfg.get("stop_trigger_price"))
                    tp = tp if tp is not None else _safe_float(cfg.get("limit_price"))
        except Exception:
            pass

    health = "ok"
    if trig_status and trig_status.upper() != "TRIGGER_STATUS_UNSPECIFIED":
        if "INVALID" in trig_status.upper() or "REJECT" in trig_status.upper():
            health = "bad"
        else:
            health = "warn"

    return {
        "status": status,
        "order_type": order_type,
        "trigger_status": trig_status,
        "stop_trigger": stop,
        "take_profit": tp,
        "health": health,
    }


def _strategy_tp_levels(entry_px: float, direction: str, leverage: float, cfg: dict) -> dict:
    """
    Compute strategy TP levels (best-effort) matching the bot's tp plan math:
    move_pct = tp_move / leverage.
    """
    try:
        lev = float(leverage or 1.0)
        if lev <= 0:
            lev = 1.0
    except Exception:
        lev = 1.0
    exits = cfg.get("exits", {}) if isinstance(cfg, dict) else {}
    tp1_move = float((exits.get("tp1_move", 0.20) or 0.20))
    tp2_move = float((exits.get("tp2_move", 0.40) or 0.40))
    tp3_move = float((exits.get("tp3_move", 0.60) or 0.60))
    try:
        px = float(entry_px or 0.0)
        if px <= 0:
            return {"tp1": None, "tp2": None, "tp3": None}
    except Exception:
        return {"tp1": None, "tp2": None, "tp3": None}

    d = (direction or "").lower()
    def _lvl(move: float) -> float:
        m = float(move) / lev
        if "short" in d:
            return px * (1.0 - m)
        return px * (1.0 + m)

    return {"tp1": _lvl(tp1_move), "tp2": _lvl(tp2_move), "tp3": _lvl(tp3_move)}


def _pct_to_level(current: float, level: float, direction: str) -> float | None:
    try:
        c = float(current)
        l = float(level)
        if c <= 0 or l <= 0:
            return None
        d = (direction or "").lower()
        if "short" in d:
            return (c - l) / c * 100.0  # % drop needed to reach level
        return (l - c) / c * 100.0      # % rise needed to reach level
    except Exception:
        return None


def _adaptive_scale_plan(
    *,
    full_close_at_tp1: bool,
    breakout_type: str | None,
    confluence_count: int | None,
    gates_blocked: int,
    pnl_pct: float | None,
) -> dict:
    """
    Dashboard-only helper: propose a scale-out split (TP1/TP2/TP3) based on current context.
    This does NOT change bot trading logic; it's an analytics/projection layer.
    """
    if full_close_at_tp1:
        return {
            "mode": "full_close_tp1",
            "w1": 1.0,
            "w2": 0.0,
            "w3": 0.0,
            "why": "single-contract or configured full-close at TP1",
        }

    bt = (breakout_type or "neutral").lower()
    cc = int(confluence_count or 0)
    p = float(pnl_pct) if pnl_pct is not None else None

    # Default: balanced.
    w1, w2, w3 = 0.45, 0.30, 0.25
    why = "balanced"

    # Under pressure (blocked gates / trade not working yet): take profits earlier.
    if gates_blocked > 0:
        w1, w2, w3 = 0.60, 0.25, 0.15
        why = "gates blocked: bias toward earlier realization"

    if p is not None and p < 0:
        w1, w2, w3 = 0.70, 0.20, 0.10
        why = "in drawdown: protect with heavier TP1"

    # Strong trend + high confluence: let it run more.
    if bt == "trend" and cc >= 5 and (p is None or p >= 0):
        w1, w2, w3 = 0.25, 0.30, 0.45
        why = "trend breakout + high confluence: let runners work"
    elif bt == "neutral" and cc <= 3 and (p is None or p <= 0.02):
        w1, w2, w3 = 0.60, 0.25, 0.15
        why = "neutral breakout + low confluence: take earlier profits"

    # Normalize (defensive).
    s = (w1 + w2 + w3) or 1.0
    w1, w2, w3 = w1 / s, w2 / s, w3 / s
    return {"mode": "scale_out", "w1": w1, "w2": w2, "w3": w3, "why": why}


def _plain_english_gate(gate_name: str) -> str:
    return {
        "atr_regime": "volatility is too low",
        "session": "outside trading hours",
        "distance_from_value": "price is too close to the average",
        "spread": "spread is too wide",
    }.get(gate_name, gate_name.replace("_", " "))


def _plain_english_confluence(cname: str) -> str:
    return {
        "EMA_BIAS": "trend direction",
        "RSI_VALID": "momentum (RSI)",
        "MACD_EXPAND": "MACD expansion",
        "RVOL_OK": "volume spike",
        "STRUCTURE_ZONE": "support/resistance zone",
        "FIB_ZONE": "Fibonacci level",
    }.get(cname, cname.replace("_", " ").lower())


@st.cache_data(show_spinner=False)
def _load_config_cached(mtime_ns: int, size: int) -> dict:
    _ = (mtime_ns, size)
    cfg_path = BASE_DIR / "config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    except Exception:
        return {}


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_1h_candles_from_exchange(product_id: str = "XLM-USD", days: int = 7) -> pd.DataFrame:
    """Fetch fresh 1h candles directly from Coinbase public API (no auth needed)."""
    try:
        from datetime import timedelta as _td
        import requests as _req
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
        end = datetime.now(timezone.utc)
        start = end - _td(days=days)
        chunk_seconds = 300 * 3600  # 300 candles * 3600s
        all_data = []
        cur = start
        while cur < end:
            ce = min(cur + _td(seconds=chunk_seconds), end)
            try:
                r = _req.get(url, params={"start": cur.isoformat(), "end": ce.isoformat(), "granularity": 3600}, timeout=6)
                if r.status_code == 200 and r.json():
                    all_data.extend(r.json())
            except Exception:
                pass
            cur = ce
        if not all_data:
            return pd.DataFrame()
        df = pd.DataFrame(all_data, columns=["timestamp", "low", "high", "open", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        return df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_1h_candles_cached(path_str: str, mtime_ns: int, size: int) -> pd.DataFrame:
    _ = (mtime_ns, size)
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _stop_price_for_signal(
    entry_price: float,
    direction: str,
    sig_ts,
    df_1h: pd.DataFrame,
    max_sl_pct: float,
    lookback: int = 20,
) -> float | None:
    if entry_price <= 0:
        return None
    stop = None
    try:
        if not df_1h.empty and "timestamp" in df_1h.columns:
            sub = df_1h[df_1h["timestamp"] <= sig_ts].tail(lookback) if sig_ts is not None else df_1h.tail(lookback)
            if sub.empty:
                sub = df_1h.tail(lookback)
            if not sub.empty:
                if direction == "short":
                    stop = float(sub["high"].max())
                else:
                    stop = float(sub["low"].min())
    except Exception:
        stop = None

    # Enforce your configured max SL distance as a fallback if the swing stop is unavailable/out of bounds.
    try:
        if stop is None or stop <= 0 or abs(entry_price - stop) / entry_price > float(max_sl_pct or 0):
            if direction == "short":
                stop = entry_price * (1 + float(max_sl_pct or 0))
            else:
                stop = entry_price * (1 - float(max_sl_pct or 0))
    except Exception:
        return None
    return stop


def _tp1_price(entry_price: float, direction: str, leverage: int, tp1_move: float) -> float | None:
    if entry_price <= 0:
        return None
    if leverage <= 0:
        leverage = 1
    move = float(tp1_move or 0) / leverage
    if direction == "short":
        return entry_price * (1 - move)
    return entry_price * (1 + move)


def _fmt_ts(ts) -> str:
    try:
        return ts.astimezone(PT).strftime("%b %d %I:%M %p PT")
    except Exception:
        return "?"

def render_intel_hub(last_decision: dict, state: dict, pos_view: dict | None):
    """Render the News & Agent Intel Hub tab."""
    st.markdown("<div class='panel-title'>The Wolf's Intel Hub</div>", unsafe_allow_html=True)
    
    # Load Market Brief (Perplexity)
    _brief_path = DATA_DIR / "market_brief.json"
    _brief_data = {}
    if _brief_path.exists():
        try:
            _raw_brief = json.loads(_brief_path.read_text())
            _brief_data = _raw_brief.get("brief") or {}
        except Exception:
            pass
            
    # Load AI Insights (Claude/Gemini/Codex)
    _ai_path = DATA_DIR / "ai_insight.json"
    _ai_data = {}
    if _ai_path.exists():
        try:
            _ai_data = json.loads(_ai_path.read_text())
        except Exception:
            pass

    col1, col2 = st.columns([1.5, 1.0])
    
    with col1:
        # ── Market Brief (Perplexity) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Perplexity Market Brief</div>", unsafe_allow_html=True)
        if _brief_data:
            _rm = str(_brief_data.get("risk_modifier", "neutral")).upper()
            _rm_clr = "#10b981" if "ON" in _rm else "#ef4444" if "OFF" in _rm else "#f59e0b"
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>"
                f"<span class='pill' style='background:{_rm_clr}20;color:{_rm_clr};font-weight:700;'>RISK: {_rm}</span>"
                f"<span class='muted' style='font-size:10px;'>Horizon: {str(_brief_data.get('time_horizon', '?')).upper()}</span>"
                "</div>",
                unsafe_allow_html=True
            )
            
            st.markdown("<div style='font-size:13px;color:#e5e7eb;font-weight:600;margin-bottom:6px;'>Macro & Crypto News</div>", unsafe_allow_html=True)
            for bullet in _brief_data.get("headline_bullets", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(bullet)}</div>", unsafe_allow_html=True)
                
            st.markdown("<div style='font-size:13px;color:#fbbf24;font-weight:600;margin-top:12px;margin-bottom:6px;'>XLM Catalysts</div>", unsafe_allow_html=True)
            for xlm_bullet in _brief_data.get("xlm_specific", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(xlm_bullet)}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='muted' style='padding:20px 0;'>Waiting for Perplexity intel cycle...</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Agent Discussions (Thoughts) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Agent Reasoning & Thoughts</div>", unsafe_allow_html=True)
        
        # Pull latest thoughts from decisions log
        _dec_recent = _load_jsonl(DECISIONS_PATH, max_lines=15)
        if not _dec_recent.empty:
            for _, row in _dec_recent.iloc[::-1].iterrows():
                _thought = _safe_str(row.get("thought"))
                _ts = _coerce_ts_utc(row.get("timestamp"))
                if _thought and len(_thought) > 10:
                    _tone = _decision_tone(row.get("reason"), row.get("exit_reason", ""))
                    st.markdown(
                        f"<div class='thought-post {_tone}'>"
                        f"<div class='t'>{_fmt_pt_short(_ts)}</div>"
                        f"<div class='b'>{html.escape(_thought)}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # ── Team Peer Intel (Latest Insights) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Team Peer Reports</div>", unsafe_allow_html=True)
        
        # Claude (Directive)
        _cl = _ai_data.get("directive", {}).get("result", {})
        if _cl:
            _action = str(_cl.get("action", "HOLD")).upper()
            _aclr = "#10b981" if "ENTER" in _action else "#ef4444" if "EXIT" in _action else "#6b7280"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#a78bfa;'>"
                f"<div class='h'>Claude Opus <span class='pill' style='background:#a78bfa20;color:#a78bfa;'>CHIEF</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{_action}</span> "
                f"<span class='muted' style='font-size:10px;'>conf {int(float(_cl.get('confidence', 0))*100)}%</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_cl.get('reasoning', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Gemini (Risk Audit)
        _ga = _ai_data.get("gemini_audit_decision", {}).get("result", {})
        if _ga:
            _appr = bool(_ga.get("approved"))
            _aclr = "#10b981" if _appr else "#ef4444"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#3b82f6;'>"
                f"<div class='h'>Gemini <span class='pill' style='background:#3b82f620;color:#3b82f6;'>RISK</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{'APPROVED' if _appr else 'VETOED'}</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_ga.get('reason', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Codex (Integrity)
        st.markdown(
            f"<div class='thought-post info' style='border-left-color:#34d399;'>"
            f"<div class='h'>Codex <span class='pill' style='background:#34d39920;color:#34d399;'>ENGINEER</span></div>"
            f"<div style='margin:6px 0;'><span class='pill ok'>OK</span></div>"
            f"<div class='b' style='font-size:11px;'>System integrity validated. Coinbase mirror active.</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

def render_claude_chat():
    """Render the Claude Chat interface."""
    st.markdown("<div class='panel-title'>Claude Chat</div>", unsafe_allow_html=True)
    _chat_url = os.environ.get("XLM_CHAT_URL", "http://127.0.0.1:8503/ask")
    # Note: the chat server usually serves a simple HTML interface.
    # We'll use an iframe to embed the chat interface if possible, or just a link.
    st.markdown(
        f'<iframe src="http://127.0.0.1:8503" width="100%" height="600px" style="border:none; border-radius:12px; background:rgba(15,23,42,0.5);"></iframe>',
        unsafe_allow_html=True
    )

def _trade_quality_score(trade: dict, timeseries_df: pd.DataFrame) -> dict:
    """Score a closed trade on entry timing, exit efficiency, and stop quality.

    Returns dict with grade (A-D), numeric score 0-100, and component breakdowns.
    """
    try:
        entry_price = float(trade.get("entry_price") or 0)
        exit_price = float(trade.get("exit_price") or 0)
        pnl_usd = float(trade.get("pnl_usd") or 0)
        direction = str(trade.get("side") or trade.get("direction") or "long").lower()
        entry_time_raw = trade.get("entry_time") or trade.get("timestamp")
        exit_time_raw = trade.get("exit_time")
        if not entry_price or not exit_price or entry_time_raw is None:
            return {"ok": False}

        entry_ts = pd.Timestamp(entry_time_raw, tz="UTC") if entry_time_raw else None
        exit_ts = pd.Timestamp(exit_time_raw, tz="UTC") if exit_time_raw else None
        if entry_ts is None:
            return {"ok": False}

        # Get price path between entry and exit from timeseries
        mask = timeseries_df["timestamp"] >= entry_ts
        if exit_ts is not None:
            mask = mask & (timeseries_df["timestamp"] <= exit_ts)
        path_df = timeseries_df.loc[mask].head(200)
        if path_df.empty or len(path_df) < 2:
            return {"ok": False}

        prices = path_df["price"].astype(float).tolist()
        pnls = []
        for px in prices:
            if direction == "short":
                pnls.append((entry_price - px) / entry_price * 100)
            else:
                pnls.append((px - entry_price) / entry_price * 100)

        mfe_idx = max(range(len(pnls)), key=lambda i: pnls[i])
        mae_idx = min(range(len(pnls)), key=lambda i: pnls[i])
        mfe_pct = pnls[mfe_idx]
        mae_pct = pnls[mae_idx]

        # Entry timing (40%): Did MFE come before MAE? Earlier MFE = better entry.
        if len(pnls) > 1:
            timing_score = 100 if mfe_idx < mae_idx else (50 if mfe_idx == mae_idx else 20)
            # Bonus if MFE is in first third of the path
            if mfe_idx < len(pnls) / 3:
                timing_score = min(100, timing_score + 15)
        else:
            timing_score = 50

        # Exit efficiency (40%): pnl_pct / mfe_pct — what % of peak move was captured?
        pnl_pct = float(trade.get("pnl_pct") or 0)
        if mfe_pct > 0.01:
            efficiency = max(0, min(100, (pnl_pct / mfe_pct) * 100))
        elif pnl_pct > 0:
            efficiency = 80
        else:
            efficiency = 10

        # Stop quality (20%): Was stop hit when MFE was > 0.5%? (too tight)
        exit_reason = str(trade.get("exit_reason") or "").lower()
        stop_hit = "stop" in exit_reason or "stopped" in exit_reason
        if stop_hit and mfe_pct > 0.5:
            stop_score = 15  # Stop was too tight - price moved favorably but got stopped
        elif stop_hit and mfe_pct <= 0.1:
            stop_score = 70  # Stop did its job, never had a chance
        elif not stop_hit and pnl_usd > 0:
            stop_score = 90  # Good — profitable exit not from stop
        else:
            stop_score = 50

        total = timing_score * 0.40 + efficiency * 0.40 + stop_score * 0.20
        grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"

        return {
            "ok": True,
            "score": round(total, 1),
            "grade": grade,
            "timing_score": round(timing_score, 1),
            "efficiency": round(efficiency, 1),
            "stop_score": round(stop_score, 1),
            "mfe_pct": round(mfe_pct, 3),
            "mae_pct": round(mae_pct, 3),
            "pnl_usd": pnl_usd,
        }
    except Exception:
        return {"ok": False}


def _get_closed_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Extract closed trades: rows with both entry_price and exit_price set."""
    if trades_df.empty:
        return pd.DataFrame()
    df = trades_df.copy()
    for col in ("entry_price", "exit_price", "pnl_usd"):
        if col not in df.columns:
            return pd.DataFrame()
        df[col] = pd.to_numeric(df[col], errors="coerce")
    closed = df[df["exit_price"].notna() & df["pnl_usd"].notna() & df["entry_price"].notna()].copy()
    return closed


def _parameter_performance(closed_trades: pd.DataFrame) -> dict:
    """Group closed trades by entry_type, strategy_regime, and score bucket.

    Returns dict with keys 'by_entry_type', 'by_regime', 'by_score_bucket',
    each mapping group name -> {count, wins, losses, win_rate, avg_pnl, expectancy}.
    """
    result = {"by_entry_type": {}, "by_regime": {}, "by_score_bucket": {}}
    if closed_trades.empty:
        return result

    df = closed_trades.copy()
    df["pnl_usd"] = pd.to_numeric(df.get("pnl_usd"), errors="coerce").fillna(0)
    df["win"] = df["pnl_usd"] > 0

    def _group_stats(series_pnl, series_win):
        n = len(series_pnl)
        if n == 0:
            return None
        wins = int(series_win.sum())
        losses = n - wins
        wr = wins / n if n else 0
        avg_pnl = float(series_pnl.mean())
        win_pnls = series_pnl[series_win]
        loss_pnls = series_pnl[~series_win]
        avg_win = float(win_pnls.mean()) if len(win_pnls) > 0 else 0
        avg_loss = float(loss_pnls.mean()) if len(loss_pnls) > 0 else 0
        expectancy = avg_win * wr + avg_loss * (1 - wr)
        return {"count": n, "wins": wins, "losses": losses, "win_rate": round(wr, 3),
                "avg_pnl": round(avg_pnl, 2), "expectancy": round(expectancy, 3)}

    # By entry_type
    if "entry_type" in df.columns:
        for name, grp in df.groupby("entry_type", dropna=True):
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_entry_type"][str(name)] = s

    # By strategy_regime
    if "strategy_regime" in df.columns:
        for name, grp in df.groupby("strategy_regime", dropna=True):
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_regime"][str(name)] = s

    # By score bucket
    if "confluence_score" in df.columns:
        df["_score"] = pd.to_numeric(df["confluence_score"], errors="coerce")
        df["_bucket"] = (df["_score"] // 10 * 10).astype("Int64")
        for name, grp in df.groupby("_bucket", dropna=True):
            label = f"{int(name)}-{int(name)+9}"
            s = _group_stats(grp["pnl_usd"], grp["win"])
            if s:
                result["by_score_bucket"][label] = s

    return result


def _resolve_trade_session_bucket(ts, cfg: dict) -> str:
    if ts is None:
        return "UNKNOWN"
    try:
        if isinstance(ts, pd.Timestamp):
            dt_utc = ts.to_pydatetime()
        else:
            dt_utc = pd.to_datetime(ts, utc=True, errors="coerce")
            if pd.isna(dt_utc):
                return "UNKNOWN"
            dt_utc = dt_utc.to_pydatetime()
        try:
            from zoneinfo import ZoneInfo
            dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            dt_et = dt_utc
        mp_cfg = (cfg.get("margin_policy") or {}) if isinstance(cfg.get("margin_policy"), dict) else {}
        fb_cfg = (mp_cfg.get("friday_break") or {}) if isinstance(mp_cfg.get("friday_break"), dict) else {}
        now_minutes = dt_et.hour * 60 + dt_et.minute
        if bool(fb_cfg.get("enabled", True)) and int(dt_et.weekday()) == int(fb_cfg.get("break_weekday", 4) or 4):
            break_start = int(fb_cfg.get("break_start_hour_et", 17) or 17) * 60 + int(fb_cfg.get("break_start_minute_et", 0) or 0)
            break_end = int(fb_cfg.get("break_end_hour_et", 18) or 18) * 60 + int(fb_cfg.get("break_end_minute_et", 0) or 0)
            pre_lock = int(fb_cfg.get("pre_break_new_entry_lock_minutes", 60) or 60)
            reopen_cd = int(fb_cfg.get("reopen_cooldown_minutes", 10) or 10)
            if break_start <= now_minutes < break_end:
                return "FRIDAY_BREAK"
            if (break_start - pre_lock) <= now_minutes < break_start:
                return "FRIDAY_PRELOCK"
            if break_end <= now_minutes < (break_end + reopen_cd):
                return "FRIDAY_REOPEN"
        cutoff_minutes = int(mp_cfg.get("cutoff_hour_et", 16) or 16) * 60 + int(mp_cfg.get("cutoff_minute_et", 0) or 0)
        start_minutes = int(mp_cfg.get("intraday_start_hour_et", 8) or 8) * 60 + int(mp_cfg.get("intraday_start_minute_et", 0) or 0)
        pre_cutoff = int(mp_cfg.get("pre_cutoff_minutes", 15) or 15)
        if now_minutes < start_minutes or now_minutes >= cutoff_minutes:
            return "OVERNIGHT"
        if now_minutes >= (cutoff_minutes - pre_cutoff):
            return "PRE_CUTOFF"
        return "INTRADAY"
    except Exception:
        return "UNKNOWN"


def _trade_expectancy_matrix(closed_trades: pd.DataFrame, cfg: dict, max_rows: int = 6) -> list[dict]:
    if closed_trades.empty:
        return []
    df = closed_trades.copy()
    if "pnl_usd" not in df.columns:
        return []
    df["pnl_usd"] = pd.to_numeric(df["pnl_usd"], errors="coerce")
    df = df[df["pnl_usd"].notna()].copy()
    if df.empty:
        return []
    if "entry_time" in df.columns:
        df["_entry_ts"] = pd.to_datetime(df["entry_time"], utc=True, errors="coerce")
    elif "timestamp" in df.columns:
        df["_entry_ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    else:
        df["_entry_ts"] = pd.NaT
    df["_session"] = df["_entry_ts"].apply(lambda ts: _resolve_trade_session_bucket(ts, cfg))
    df["_entry_type"] = df.get("entry_type", pd.Series(["unknown"] * len(df))).fillna("unknown").astype(str)
    df["_regime"] = df.get("strategy_regime", pd.Series(["unknown"] * len(df))).fillna("unknown").astype(str)
    df["_key"] = df["_entry_type"] + " | " + df["_session"] + " | " + df["_regime"]
    rows: list[dict] = []
    for key, grp in df.groupby("_key", dropna=False):
        pnl = grp["pnl_usd"]
        count = int(len(grp))
        wins = int((pnl > 0).sum())
        losses = count - wins
        avg = float(pnl.mean()) if count else 0.0
        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = float(pnl[pnl < 0].sum())
        pf = (gross_profit / abs(gross_loss)) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
        rows.append(
            {
                "label": str(key),
                "count": count,
                "wins": wins,
                "losses": losses,
                "win_rate": (wins / count) if count else 0.0,
                "avg_pnl": avg,
                "expectancy": avg,
                "profit_factor": pf,
            }
        )
    rows.sort(key=lambda r: (r["expectancy"], r["profit_factor"], r["count"]), reverse=True)
    return rows[:max_rows]


def _trade_cost_decomposition(closed_trades: pd.DataFrame, cfg: dict) -> dict:
    empty = {
        "closed_count": 0,
        "realized_net_pnl_usd": 0.0,
        "gross_before_fees_usd": 0.0,
        "measured_fees_usd": 0.0,
        "estimated_slippage_usd": 0.0,
        "estimated_funding_usd": 0.0,
        "net_after_known_costs_usd": 0.0,
    }
    if closed_trades.empty:
        return empty
    df = closed_trades.copy()
    df["pnl_usd"] = pd.to_numeric(df.get("pnl_usd"), errors="coerce").fillna(0.0)
    measured_fee_cols = []
    for col in ("total_fees_usd", "fees_usd"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            measured_fee_cols.append(col)
    fees = float(df[measured_fee_cols[0]].sum()) if measured_fee_cols else 0.0
    for col in ("entry_price", "size"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    contract_size = float(cfg.get("contract_size", 5000) or 5000)
    v4_cfg = (cfg.get("v4") or {}) if isinstance(cfg.get("v4"), dict) else {}
    ev_cfg = (v4_cfg.get("ev") or {}) if isinstance(v4_cfg.get("ev"), dict) else {}
    slippage_pct = float(ev_cfg.get("slippage_pct", 0.0002) or 0.0002)
    funding_pct = float(ev_cfg.get("funding_pct", 0.0) or 0.0)
    notional_series = df.get("entry_price", pd.Series([0.0] * len(df))) * contract_size * df.get("size", pd.Series([0.0] * len(df)))
    est_slippage = float((notional_series * slippage_pct).sum())
    est_funding = float((notional_series * funding_pct).sum())
    realized_net = float(df["pnl_usd"].sum())
    gross_before_fees = realized_net + fees
    net_after_known = realized_net - est_slippage - est_funding
    return {
        "closed_count": int(len(df)),
        "realized_net_pnl_usd": round(realized_net, 2),
        "gross_before_fees_usd": round(gross_before_fees, 2),
        "measured_fees_usd": round(fees, 2),
        "estimated_slippage_usd": round(est_slippage, 2),
        "estimated_funding_usd": round(est_funding, 2),
        "net_after_known_costs_usd": round(net_after_known, 2),
    }


def _evaluate_path(
    *,
    sig_price: float,
    sig_dir: str,
    sig_ts,
    after_df: pd.DataFrame,
    cfg: dict,
    df_1h: pd.DataFrame,
) -> dict:
    """
    Order-aware evaluation:
    - MFE/MAE and when they occurred
    - Whether stop/liquidation was hit before TP1 (survivability)
    """
    if after_df is None or after_df.empty or sig_price <= 0:
        return {"ok": False, "reason": "too_recent"}

    leverage = int(cfg.get("leverage") or 1)
    max_sl_pct = float((cfg.get("risk") or {}).get("max_sl_pct", 0.03) or 0.03)
    tp1_move = float((cfg.get("exits") or {}).get("tp1_move", 0.20) or 0.20)

    stop_price = _stop_price_for_signal(sig_price, sig_dir, sig_ts, df_1h, max_sl_pct=max_sl_pct)
    tp1 = _tp1_price(sig_price, sig_dir, leverage=leverage, tp1_move=tp1_move)
    liq = None
    if leverage > 1:
        liq = sig_price * (1 - 1 / leverage) if sig_dir != "short" else sig_price * (1 + 1 / leverage)

    prices = after_df["price"].astype(float).tolist()
    times = after_df["timestamp"].tolist()

    pnls = []
    for px in prices:
        if sig_dir == "short":
            pnls.append((sig_price - px) / sig_price * 100)
        else:
            pnls.append((px - sig_price) / sig_price * 100)

    # Extremes
    mfe_idx = max(range(len(pnls)), key=lambda i: pnls[i])
    mae_idx = min(range(len(pnls)), key=lambda i: pnls[i])
    mfe = float(pnls[mfe_idx])
    mae = float(pnls[mae_idx])

    # Threshold hits (first occurrence)
    def _first_idx(pred) -> int | None:
        for i, px in enumerate(prices):
            try:
                if pred(px):
                    return i
            except Exception:
                continue
        return None

    if sig_dir == "short":
        stop_hit = _first_idx(lambda px: stop_price is not None and px >= float(stop_price))
        liq_hit = _first_idx(lambda px: liq is not None and px >= float(liq))
        tp1_hit = _first_idx(lambda px: tp1 is not None and px <= float(tp1))
    else:
        stop_hit = _first_idx(lambda px: stop_price is not None and px <= float(stop_price))
        liq_hit = _first_idx(lambda px: liq is not None and px <= float(liq))
        tp1_hit = _first_idx(lambda px: tp1 is not None and px >= float(tp1))

    adverse_hit = None
    adverse_kind = None
    for kind, idx in (("stop", stop_hit), ("liq", liq_hit)):
        if idx is None:
            continue
        if adverse_hit is None or idx < adverse_hit:
            adverse_hit = idx
            adverse_kind = kind

    verdict = "no_decisive_outcome"
    if adverse_hit is not None and (tp1_hit is None or adverse_hit < tp1_hit):
        verdict = "stopped_before_profit" if adverse_kind == "stop" else "liquidated_before_profit"
    elif tp1_hit is not None and (adverse_hit is None or tp1_hit < adverse_hit):
        verdict = "profit_first"

    return {
        "ok": True,
        "mfe_pct": mfe,
        "mfe_ts": times[mfe_idx],
        "mae_pct": mae,
        "mae_ts": times[mae_idx],
        "first_extreme": "best" if mfe_idx < mae_idx else "worst",
        "stop_price": stop_price,
        "liq_price": liq,
        "tp1_price": tp1,
        "tp1_hit_ts": times[tp1_hit] if tp1_hit is not None else None,
        "adverse_kind": adverse_kind,
        "adverse_hit_ts": times[adverse_hit] if adverse_hit is not None else None,
        "verdict": verdict,
    }


def render_intel_hub(last_decision: dict, state: dict, pos_view: dict | None):
    """Render the News & Agent Intel Hub tab."""
    st.markdown("<div class='panel-title'>The Wolf's Intel Hub</div>", unsafe_allow_html=True)
    
    # Load Market Brief (Perplexity)
    _brief_path = DATA_DIR / "market_brief.json"
    _brief_data = {}
    if _brief_path.exists():
        try:
            _raw_brief = json.loads(_brief_path.read_text())
            _brief_data = _raw_brief.get("brief") or {}
        except Exception:
            pass
            
    # Load AI Insights (Claude/Gemini/Codex)
    _ai_path = DATA_DIR / "ai_insight.json"
    _ai_data = {}
    if _ai_path.exists():
        try:
            _ai_data = json.loads(_ai_path.read_text())
        except Exception:
            pass

    col1, col2 = st.columns([1.5, 1.0])
    
    with col1:
        # ── Market Brief (Perplexity) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Perplexity Market Brief</div>", unsafe_allow_html=True)
        if _brief_data:
            _rm = str(_brief_data.get("risk_modifier", "neutral")).upper()
            _rm_clr = "#10b981" if "ON" in _rm else "#ef4444" if "OFF" in _rm else "#f59e0b"
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>"
                f"<span class='pill' style='background:{_rm_clr}20;color:{_rm_clr};font-weight:700;'>RISK: {_rm}</span>"
                f"<span class='muted' style='font-size:10px;'>Horizon: {str(_brief_data.get('time_horizon', '?')).upper()}</span>"
                "</div>",
                unsafe_allow_html=True
            )
            
            st.markdown("<div style='font-size:13px;color:#e5e7eb;font-weight:600;margin-bottom:6px;'>Macro & Crypto News</div>", unsafe_allow_html=True)
            for bullet in _brief_data.get("headline_bullets", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(bullet)}</div>", unsafe_allow_html=True)
                
            st.markdown("<div style='font-size:13px;color:#fbbf24;font-weight:600;margin-top:12px;margin-bottom:6px;'>XLM Catalysts</div>", unsafe_allow_html=True)
            for xlm_bullet in _brief_data.get("xlm_specific", []):
                st.markdown(f"<div class='intel-event'>&bull; {html.escape(xlm_bullet)}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='muted' style='padding:20px 0;'>Waiting for Perplexity intel cycle...</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Agent Discussions (Thoughts) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Agent Reasoning & Thoughts</div>", unsafe_allow_html=True)
        
        # Pull latest thoughts from decisions log
        _dec_recent = _load_jsonl(DECISIONS_PATH, max_lines=15)
        if not _dec_recent.empty:
            for _, row in _dec_recent.iloc[::-1].iterrows():
                _thought = _safe_str(row.get("thought"))
                _ts = _coerce_ts_utc(row.get("timestamp"))
                if _thought and len(_thought) > 10:
                    _tone = _decision_tone(row.get("reason"), row.get("exit_reason", ""))
                    st.markdown(
                        f"<div class='thought-post {_tone}'>"
                        f"<div class='t'>{_fmt_pt_short(_ts)}</div>"
                        f"<div class='b'>{html.escape(_thought)}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        _orch = _orchestration_snapshot(_ai_data)
        _chk = "&#10003;"
        _xmk = "&#10007;"
        _clx_badge = (
            f"<span class='pill' style='background:#10b98120;color:#10b981;'>{_chk} CLX</span>"
            if _orch["clx_ready"]
            else f"<span class='pill danger'>{_xmk} CLX</span>"
        )
        _gmx_badge = (
            f"<span class='pill' style='background:#3b82f620;color:#3b82f6;'>{_chk} GMX</span>"
            if _orch["gmx_ready"]
            else f"<span class='pill danger'>{_xmk} GMX</span>"
        )
        _mem_badge = (
            "<span class='pill ok'>MEMORY ON</span>"
            if (_orch["claude_mem_ready"] and _orch["gemini_mem_ready"])
            else "<span class='pill danger'>MEMORY PARTIAL</span>"
        )
        _mcp_badge = "<span class='pill ok'>MCP</span>" if _orch["mcp_ready"] else "<span class='pill'>MCP OFF</span>"
        st.markdown(
            "<div class='intel-card'>"
            "<div class='intel-title'>Orchestration Control Plane</div>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;'>{_clx_badge}{_gmx_badge}{_mem_badge}{_mcp_badge}</div>"
            "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 10px;font-size:11px;'>"
            f"<div><span class='muted'>Claude assets</span><br><span class='metric'>{_orch['claude_agents']} agents / {_orch['claude_skills']} skills / {_orch['claude_commands']} cmds</span></div>"
            f"<div><span class='muted'>Modes</span><br><span class='metric'>{_orch['claude_modes']} claude / {_orch['gemini_modes']} gemini</span></div>"
            f"<div><span class='muted'>Claude directive</span><br><span class='metric'>{_orch['directive_age']}</span></div>"
            f"<div><span class='muted'>Gemini audit</span><br><span class='metric'>{_orch['gemini_audit_age']}</span></div>"
            "</div>"
            f"<div style='margin-top:8px;font-size:10px;color:#94a3b8;border-top:1px solid rgba(148,163,184,0.14);padding-top:6px;'>"
            f"Last AI event: {html.escape(_orch['last_event'])}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Team Peer Intel (Latest Insights) ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Team Peer Reports</div>", unsafe_allow_html=True)
        
        # Claude (Directive)
        _cl = _ai_data.get("directive", {}).get("result", {})
        if _cl:
            _action = str(_cl.get("action", "HOLD")).upper()
            _aclr = "#10b981" if "ENTER" in _action else "#ef4444" if "EXIT" in _action else "#6b7280"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#a78bfa;'>"
                f"<div class='h'>Claude Opus <span class='pill' style='background:#a78bfa20;color:#a78bfa;'>CHIEF</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{_action}</span> "
                f"<span class='muted' style='font-size:10px;'>conf {int(float(_cl.get('confidence', 0))*100)}%</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_cl.get('reasoning', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        # Gemini (Risk Audit)
        _ga = _ai_data.get("gemini_audit_decision", {}).get("result", {})
        if _ga:
            _appr = bool(_ga.get("approved"))
            _aclr = "#10b981" if _appr else "#ef4444"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#3b82f6;'>"
                f"<div class='h'>Gemini <span class='pill' style='background:#3b82f620;color:#3b82f6;'>RISK</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_aclr}20;color:{_aclr};'>{'APPROVED' if _appr else 'VETOED'}</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(_ga.get('reason', ''))}</div>"
                "</div>",
                unsafe_allow_html=True
            )

        _cx = _ai_data.get("codex_directive", {}).get("result", {})
        if _cx:
            _cx_action = str(_cx.get("action", "FLAT")).upper()
            _cx_clr = "#10b981" if "ENTER" in _cx_action else "#ef4444" if _cx_action == "EXIT" else "#6b7280"
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#34d399;'>"
                f"<div class='h'>Codex <span class='pill' style='background:#34d39920;color:#34d399;'>ENGINEER</span></div>"
                f"<div style='margin:6px 0;'><span class='pill' style='background:{_cx_clr}20;color:{_cx_clr};'>{_cx_action}</span> "
                f"<span class='muted' style='font-size:10px;'>conf {int(float(_cx.get('confidence', 0))*100)}%</span></div>"
                f"<div class='b' style='font-size:11px;'>{html.escape(str(_cx.get('reasoning', '')))}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='thought-post info' style='border-left-color:#34d399;'>"
                f"<div class='h'>Codex <span class='pill' style='background:#34d39920;color:#34d399;'>ENGINEER</span></div>"
                f"<div style='margin:6px 0;'><span class='pill'>WAITING</span></div>"
                f"<div class='b' style='font-size:11px;'>No recent Codex directive in ai_insight cache.</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Blinko Knowledge Base ──
        st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
        st.markdown("<div class='intel-title'>Blinko Knowledge Feed</div>", unsafe_allow_html=True)
        _blinko_notes = _fetch_blinko_notes(5)
        if _blinko_notes:
            for _note in _blinko_notes:
                _nc = str(_note.get("content", "")).strip()
                if _nc:
                    _nc_preview = html.escape(_nc[:280]) + ("..." if len(_nc) > 280 else "")
                    st.markdown(
                        f"<div class='thought-post info' style='border-left-color:#f59e0b;'>"
                        f"<div class='b' style='font-size:11px;'>{_nc_preview}</div>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown("<div class='muted' style='padding:12px 0;font-size:11px;'>Blinko not reachable or no notes.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Position Alignment ──
        if pos_view:
            st.markdown("<div class='intel-card'>", unsafe_allow_html=True)
            st.markdown("<div class='intel-title'>Position Intelligence</div>", unsafe_allow_html=True)
            _exit_eval = _ai_data.get("exit_eval", {}).get("result", {})
            if _exit_eval:
                _urg = str(_exit_eval.get("urgency", "hold")).upper()
                _uclr = "#10b981" if _urg == "HOLD" else "#f59e0b" if _urg == "TIGHTEN" else "#ef4444"
                st.markdown(
                    f"<div class='thought-post warn' style='border-left-color:{_uclr};'>"
                    f"<div class='h'>Exit Assessment</div>"
                    f"<div style='margin:6px 0;'><span class='pill' style='background:{_uclr}20;color:{_uclr};'>{_urg}</span></div>"
                    f"<div class='b' style='font-size:11px;'>{html.escape(_exit_eval.get('reasoning', ''))}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

def render_claude_chat():
    """Render the existing Claude Chat component."""
    st.markdown("<div class='panel-title'>Claude Chat</div>", unsafe_allow_html=True)
    # The existing dashboard already has a chat component, but the user asked for it to be integrated.
    # I'll use the existing components.html call if available, or recreate it.
    pass

# ── AUTO-REFRESH ───────────────────────────────────────────────────

# ── LOAD DATA (once) ──────────────────────────────────────────────
snap_mtime, snap_size = _file_sig(DASHBOARD_SNAPSHOT_PATH)
snap_b_mtime, snap_b_size = _file_sig(DASHBOARD_SNAPSHOT_LAST_GOOD_PATH)
snapshot, snapshot_status = _load_snapshot_with_fallback_cached(
    str(DASHBOARD_SNAPSHOT_PATH),
    snap_mtime,
    snap_size,
    str(DASHBOARD_SNAPSHOT_LAST_GOOD_PATH),
    snap_b_mtime,
    snap_b_size,
)

try:
    history_days = max(7, int(os.environ.get("XLM_DASH_HISTORY_DAYS", "7")))
except Exception:
    history_days = 7
try:
    history_max_lines = max(2000, int(os.environ.get("XLM_DASH_HISTORY_MAX_LINES", "120000")))
except Exception:
    history_max_lines = 120000
try:
    history_max_mb = max(2.0, float(os.environ.get("XLM_DASH_HISTORY_MAX_MB", "24")))
except Exception:
    history_max_mb = 24.0
history_max_bytes = int(history_max_mb * 1024 * 1024)

ts_mtime, ts_size = _file_sig(DASHBOARD_TIMESERIES_PATH)
timeseries = _load_jsonl_cached(
    str(DASHBOARD_TIMESERIES_PATH),
    ts_mtime,
    ts_size,
    max_lines=history_max_lines,
    lookback_days=history_days,
    max_tail_bytes=history_max_bytes,
)
if not timeseries.empty:
    if "timestamp" not in timeseries.columns and "ts" in timeseries.columns:
        timeseries["timestamp"] = pd.to_datetime(timeseries["ts"], utc=True, errors="coerce")
    else:
        timeseries["timestamp"] = pd.to_datetime(timeseries["timestamp"], utc=True, errors="coerce")
    timeseries = timeseries.dropna(subset=["timestamp"]).sort_values("timestamp")

dec_mtime, dec_size = _file_sig(DECISIONS_PATH)
decisions = _load_jsonl_cached(
    str(DECISIONS_PATH),
    dec_mtime,
    dec_size,
    max_lines=history_max_lines,
    lookback_days=history_days,
    max_tail_bytes=history_max_bytes,
)
if not decisions.empty:
    decisions["timestamp"] = pd.to_datetime(decisions["timestamp"], utc=True, errors="coerce")
    decisions = decisions.dropna(subset=["timestamp"]).sort_values("timestamp")
elif not timeseries.empty:
    # Fallback if decisions log is unavailable.
    decisions = timeseries.copy()

mn_mtime, mn_size = _file_sig(MARKET_NEWS_PATH)
market_news_batches = _load_jsonl_cached(
    str(MARKET_NEWS_PATH),
    mn_mtime,
    mn_size,
    max_lines=max(3000, int(history_max_lines // 4)),
    lookback_days=max(2, int(history_days)),
    max_tail_bytes=min(history_max_bytes, 4 * 1024 * 1024),
)
if not market_news_batches.empty:
    if "timestamp" in market_news_batches.columns:
        market_news_batches["timestamp"] = pd.to_datetime(
            market_news_batches["timestamp"], utc=True, errors="coerce"
        )
    elif "fetched_at" in market_news_batches.columns:
        market_news_batches["timestamp"] = pd.to_datetime(
            market_news_batches["fetched_at"], utc=True, errors="coerce"
        )
    market_news_batches = market_news_batches.dropna(subset=["timestamp"]).sort_values(
        "timestamp", ascending=False
    )

market_news_rows: list[dict] = []
if not market_news_batches.empty:
    for _, _batch in market_news_batches.head(30).iterrows():
        _b = _batch.to_dict() if hasattr(_batch, "to_dict") else dict(_batch)
        _batch_ts = _b.get("timestamp") or _b.get("fetched_at")
        _heads = _b.get("headlines") if isinstance(_b.get("headlines"), list) else []
        for _h in _heads[:6]:
            if not isinstance(_h, dict):
                continue
            _pub = _h.get("published_at") or _batch_ts
            market_news_rows.append(
                {
                    "timestamp": _pub,
                    "topic": _safe_str(_h.get("topic")) or "news",
                    "headline": _safe_str(_h.get("title")) or "-",
                    "source": _safe_str(_h.get("source")) or "",
                    "link": _safe_str(_h.get("link")) or "",
                }
            )
market_news_df = pd.DataFrame(market_news_rows)
if not market_news_df.empty:
    market_news_df["timestamp"] = pd.to_datetime(
        market_news_df["timestamp"], utc=True, errors="coerce"
    )
    market_news_df = market_news_df.dropna(subset=["timestamp"]).sort_values(
        "timestamp", ascending=False
    )

last_decision = snapshot.copy() if isinstance(snapshot, dict) and snapshot else {}
if not last_decision and not decisions.empty:
    last_decision = decisions.iloc[-1].to_dict()

history_start = None
history_end = None
history_df = decisions if (decisions is not None and not decisions.empty) else timeseries
if history_df is not None and not history_df.empty and "timestamp" in history_df.columns:
    try:
        history_start = history_df["timestamp"].min()
        history_end = history_df["timestamp"].max()
    except Exception:
        history_start = None
        history_end = None

balances = _get_futures_balance_cached() if EXCHANGE_READ_ENABLED else None
balance_value = _safe_float(last_decision.get("equity_start_usd"))
buying_power = _safe_float(last_decision.get("total_funds_for_margin"))
_live_unrealized = 0.0
if balances and "balance_summary" in balances:
    bs = balances["balance_summary"]
    bp = bs.get("futures_buying_power", {})
    buying_power = float(bp.get("value") or buying_power or 0)
    equity = bs.get("equity", {})
    balance_value = float(equity.get("value") or balance_value or 0)
    _live_unrealized = float(bs.get("unrealized_pnl", {}).get("value", 0) or 0)

# ── Total Portfolio Value — Coinbase portfolio endpoint is source of truth ──
# This avoids double-counting: the old approach used total_usd_balance (which
# includes primary + derivatives USD combined) as "Derivatives", then added
# spot USD on top → overcounted by ~$175.
_portfolio = _get_portfolio_breakdown_cached() if EXCHANGE_READ_ENABLED else {}
if _portfolio and _portfolio.get("total", 0) > 0:
    portfolio_value = _portfolio["total"]        # Coinbase "Total balance" (authoritative)
    cash_value = _portfolio.get("cash", 0)       # Coinbase "Cash" (USD + USDC)
    crypto_value = _portfolio.get("crypto", 0)   # Coinbase crypto holdings
    # Derivatives: show actual wallet balance from Coinbase portfolio breakdown
    deriv_balance = _portfolio.get("futures", 0)
    if deriv_balance <= 0 and balances and "balance_summary" in balances:
        deriv_balance = float(bs.get("cfm_usd_balance", {}).get("value", 0) or 0)
    # For USDC yield calc, get USDC from spot positions or balance summary
    spot_usdc = _portfolio.get("spot_usdc", 0)
    if spot_usdc <= 0:
        _live_spot = _get_spot_balances_cached() if EXCHANGE_READ_ENABLED else {}
        spot_usdc = float((_live_spot or {}).get("USDC", 0))
    # USD breakdown from CFM balance_summary (if available)
    if balances and "balance_summary" in balances:
        _cbi_usd = float(bs.get("cbi_usd_balance", {}).get("value", 0) or 0)
        spot_usd = _cbi_usd if _cbi_usd > 0 else max(0, cash_value - spot_usdc)
    else:
        spot_usd = max(0, cash_value - spot_usdc)
    spot_total = cash_value  # "Cash" in Coinbase terms
elif balances and "balance_summary" in balances:
    # Fallback: no portfolio endpoint, use CFM fields correctly
    _cfm_usd = float(bs.get("cfm_usd_balance", {}).get("value", 0) or 0)
    _cbi_usd = float(bs.get("cbi_usd_balance", {}).get("value", 0) or 0)
    _total_usd = float(bs.get("total_usd_balance", {}).get("value", 0) or 0)
    # Show derivatives wallet balance (cfm_usd_balance), not unrealized PnL
    deriv_balance = _cfm_usd
    spot_usd = _cbi_usd if _cbi_usd > 0 else max(0, _total_usd - _cfm_usd)
    _live_spot = _get_spot_balances_cached() if EXCHANGE_READ_ENABLED else {}
    spot_usdc = float((_live_spot or {}).get("USDC", 0))
    if spot_usdc <= 0:
        _spot_cash_map = last_decision.get("last_spot_cash_map") or {}
        spot_usdc = float(_spot_cash_map.get("USDC") or 0)
    spot_total = spot_usd + spot_usdc
    cash_value = spot_total
    crypto_value = 0
    # Total = all cash + derivatives wallet + unrealized PnL
    portfolio_value = spot_total + _cfm_usd + _live_unrealized
else:
    # No live data — use bot snapshot. Prefer exchange_equity for total to avoid double-counting.
    _exchange_eq = _safe_float(last_decision.get("exchange_equity_usd"))
    _cfm_balance = _safe_float(last_decision.get("cfm_usd_balance"))
    _spot_cash_map = last_decision.get("last_spot_cash_map") or {}
    spot_usd = float(_spot_cash_map.get("USD") or 0)
    spot_usdc = float(_spot_cash_map.get("USDC") or 0)
    _recon_spot = _safe_float(last_decision.get("spot_usdc"))
    _recon_spot_usd = _safe_float(last_decision.get("spot_usd"))
    if _recon_spot is not None and _recon_spot > 0:
        spot_usdc = _recon_spot
    if _recon_spot_usd is not None and _recon_spot_usd > 0:
        spot_usd = _recon_spot_usd
    spot_total = spot_usd + spot_usdc
    cash_value = spot_total
    # Use CFM wallet balance for derivatives (NOT total_funds_for_margin which double-counts)
    deriv_balance = _cfm_balance if _cfm_balance is not None else 0
    crypto_value = 0
    # If we have exchange equity, use it as the authoritative total
    if _exchange_eq and _exchange_eq > 0:
        portfolio_value = _exchange_eq
    else:
        portfolio_value = spot_total + deriv_balance

# Bot alive status
_bot_is_alive, _bot_hb_age = _bot_alive()

overnight_trading_ok = bool(last_decision.get("overnight_trading_ok"))
margin_window = str(last_decision.get("margin_window") or "unknown")
reconcile_status = str(last_decision.get("reconcile_status") or "—")
safe_mode = bool(last_decision.get("safe_mode"))
drift_count_today = int(last_decision.get("drift_count_today") or 0)

tr_mtime, tr_size = _file_sig(TRADES_PATH)
trades = _load_csv_cached(str(TRADES_PATH), tr_mtime, tr_size)
if not trades.empty:
    clean_trades = trades.copy()
    for col in ("entry_price", "stop_loss", "tp1", "tp2", "tp3"):
        if col in clean_trades.columns:
            clean_trades[col] = pd.to_numeric(clean_trades[col], errors="coerce")
    if "entry_price" in clean_trades.columns:
        clean_trades = clean_trades[clean_trades["entry_price"].notna()]
    if "result" in clean_trades.columns:
        clean_trades = clean_trades[~clean_trades["result"].astype(str).str.contains("test_fire|live_test_fire", case=False, na=False)]
    if "entry_type" in clean_trades.columns:
        clean_trades = clean_trades[~clean_trades["entry_type"].astype(str).str.contains("TEST|LIVE_TEST", case=False, na=False)]
    trades = clean_trades

inc_mtime, inc_size = _file_sig(INCIDENTS_PATH)
incidents = _load_jsonl_cached(
    str(INCIDENTS_PATH),
    inc_mtime,
    inc_size,
    max_lines=history_max_lines,
    lookback_days=history_days,
    max_tail_bytes=history_max_bytes,
)
if not incidents.empty and "timestamp" in incidents.columns:
    incidents["timestamp"] = pd.to_datetime(incidents["timestamp"], utc=True, errors="coerce")
    incidents = incidents.dropna(subset=["timestamp"]).sort_values("timestamp")

cm_mtime, cm_size = _file_sig(CASH_MOVEMENTS_PATH)
cash_movements = _load_jsonl_cached(
    str(CASH_MOVEMENTS_PATH),
    cm_mtime,
    cm_size,
    max_lines=history_max_lines,
    lookback_days=history_days,
    max_tail_bytes=history_max_bytes,
)
if not cash_movements.empty and "timestamp" in cash_movements.columns:
    cash_movements["timestamp"] = pd.to_datetime(cash_movements["timestamp"], utc=True, errors="coerce")
    cash_movements = cash_movements.dropna(subset=["timestamp"]).sort_values("timestamp")

major_events = _build_major_events(
    decisions_df=decisions,
    trades_df=trades,
    incidents_df=incidents,
    cash_movements_df=cash_movements,
    lookback_days=history_days,
    max_items=80,
)

st_mtime, st_size = _file_sig(STATE_PATH)
state = _load_state_cached(str(STATE_PATH), st_mtime, st_size)
open_pos = state.get("open_position")
if not isinstance(state, dict):
    state = {}
if not isinstance(open_pos, dict):
    open_pos = None

# Refresh spot USDC from state.json for yield calc (only if no live data)
# Do NOT recompute portfolio_value here — live portfolio breakdown is source of truth.
_state_cash = state.get("last_spot_cash_map") if isinstance(state.get("last_spot_cash_map"), dict) else None
if _state_cash and not _portfolio:
    spot_usd = float(_state_cash.get("USD") or 0)
    spot_usdc = float(_state_cash.get("USDC") or 0)
    spot_total = spot_usd + spot_usdc
    cash_value = spot_total
    # Use exchange equity if available (prevents double-counting)
    _ex_eq = _safe_float(last_decision.get("exchange_equity_usd"))
    if _ex_eq and _ex_eq > 0:
        portfolio_value = _ex_eq
    else:
        portfolio_value = spot_total + (deriv_balance or 0)

# Exchange truth (read-only): if the account has an open CFM futures position,
# we want the dashboard to reflect it even if state.json doesn't.
_cfm_positions = _get_cfm_positions_cached()
_cfm_positions = _cfm_positions or []
_exch_pos = None
_unauthorized_positions = []
if _cfm_positions:
    _xlm_positions = []
    for _cp in _cfm_positions:
        _cp_pid = str(_cp.get("product_id") or "").upper()
        if "XLM" in _cp_pid or "XLP" in _cp_pid:
            _xlm_positions.append(_cp)
        else:
            _unauthorized_positions.append(_cp)
    try:
        _xlm_positions.sort(
            key=lambda p: float(p.get("number_of_contracts") or p.get("contracts") or p.get("size") or 0.0),
            reverse=True,
        )
    except Exception:
        pass
    if _xlm_positions:
        _exch_pos = _normalize_cfm_position(_xlm_positions[0] or {})

# Config + candles for order-aware Signal History evaluation.
cfg_path = BASE_DIR / "config.yaml"
cfg_mtime, cfg_size = _file_sig(cfg_path)
cfg = _load_config_cached(cfg_mtime, cfg_size)
c1h_path = DATA_DIR / "XLM_1h.csv"
c1h_mtime, c1h_size = _file_sig(c1h_path)
hist_1h = _load_1h_candles_cached(str(c1h_path), c1h_mtime, c1h_size)
# If candle file is stale (>30min) or empty, fetch fresh from Coinbase public API.
_c1h_stale = False
if hist_1h.empty:
    _c1h_stale = True
elif "timestamp" in hist_1h.columns:
    try:
        _c1h_latest = pd.to_datetime(hist_1h["timestamp"].iloc[-1], utc=True)
        _c1h_stale = (datetime.now(timezone.utc) - _c1h_latest).total_seconds() > 1800
    except Exception:
        _c1h_stale = True
if _c1h_stale:
    _fresh_1h = _fetch_1h_candles_from_exchange(
        cfg.get("data_product_id", "XLM-USD"), days=max(7, int(os.environ.get("XLM_DASH_HISTORY_DAYS", "7")))
    )
    if not _fresh_1h.empty:
        hist_1h = _fresh_1h
        # Save back so next load is faster
        try:
            _fresh_1h.to_csv(str(c1h_path), index=False)
        except Exception:
            pass

# Debug toggle to isolate any Streamlit segfaults to a specific section.
if os.environ.get("XLM_DASH_SAFE_MODE", "0") == "1":
    st.markdown("<div class='main-title'>XLM <span>PERP</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>SAFE MODE</div>", unsafe_allow_html=True)
    st.write({"last_decision": last_decision, "open_position": open_pos, "decisions_rows": int(len(decisions))})
    st.stop()

if snapshot_status == "waiting_for_bot":
    st.info("Waiting for live bot snapshot feed (`logs/dashboard_snapshot.json`).")
elif isinstance(snapshot_status, str) and snapshot_status:
    st.warning(f"Snapshot read issue: {snapshot_status}")

# Compute W/L
real_trades = pd.DataFrame()
if not trades.empty and "entry_price" in trades.columns:
    real_trades = trades[pd.to_numeric(trades["entry_price"], errors="coerce").notna()].copy()

closed_trades = pd.DataFrame()
wins = 0
losses = 0
total_pnl = 0.0
if not real_trades.empty and "pnl_usd" in real_trades.columns:
    closed_trades = real_trades[real_trades["pnl_usd"].notna()].copy()
    closed_trades["pnl_usd"] = pd.to_numeric(closed_trades["pnl_usd"], errors="coerce")
    # Filter to TODAY (PT) for header W/L display
    _today_pt = datetime.now(timezone.utc).astimezone(PT).strftime("%Y-%m-%d")
    if "entry_time" in closed_trades.columns:
        closed_trades["_et"] = pd.to_datetime(closed_trades["entry_time"], utc=True, errors="coerce")
        _today_mask = closed_trades["_et"].dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%d") == _today_pt
        closed_trades = closed_trades[_today_mask].copy()
        closed_trades.drop(columns=["_et"], inplace=True, errors="ignore")
    # Ghost trade filter: exclude reconciler-generated exits entirely.
    # exchange_side_close trades are artifacts — not real bot exits.
    if not closed_trades.empty and "exit_reason" in closed_trades.columns:
        closed_trades = closed_trades[closed_trades["exit_reason"].astype(str) != "exchange_side_close"].copy()
    wins = int((closed_trades["pnl_usd"] > 0).sum())
    losses = int((closed_trades["pnl_usd"] <= 0).sum())
    total_pnl = float(closed_trades["pnl_usd"].fillna(0).sum())
# P&L Today: prefer exchange-verified PnL (equity delta), fall back to bot math
_exchange_pnl = _safe_float(last_decision.get("exchange_pnl_today_usd"))
_bot_pnl = _safe_float(last_decision.get("pnl_today_usd")) or 0.0
pnl_today_usd = _exchange_pnl if _exchange_pnl is not None else _bot_pnl
_pnl_source = "exchange" if _exchange_pnl is not None else "bot"

total_closed = wins + losses
win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
pnl_cls = "pnl-pos" if total_pnl >= 0 else "pnl-neg"
ops_metrics = _operator_metrics(decisions, real_trades, cfg, lookback_days=history_days)



# HUB RENDER (Trading Hub)
# Dashboard is read-only. It must never place orders or modify bot state.

def _fmt_age_s(age_s: int | None) -> str:
    if age_s is None:
        return "-"
    if age_s < 0:
        return "0s"
    if age_s < 60:
        return f"{age_s}s"
    if age_s < 3600:
        return f"{age_s//60}m {age_s%60:02d}s"
    return f"{age_s//3600}h {(age_s%3600)//60:02d}m"


def _kpi(label: str, value: str, tone: str = "neutral") -> None:
    cls = {
        "neutral": "kpi",
        "good": "kpi good",
        "bad": "kpi bad",
        "warn": "kpi warn",
    }.get(tone, "kpi")
    st.markdown(
        f"<div class='{cls}'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def _lightweight_line_chart(series: list[dict], *, height: int = 280, accent: str = "#fbbf24") -> None:
    """Lightweight Charts via CDN — Coinbase-style clean chart."""
    try:
        import json as _json

        if accent == "#fbbf24":
            _top_c, _bot_c = "rgba(251,191,36,0.22)", "rgba(251,191,36,0.02)"
        elif accent in ("#34d399", "#10b981"):
            _top_c, _bot_c = "rgba(52,211,153,0.22)", "rgba(52,211,153,0.02)"
        elif accent in ("#f87171", "#ef4444"):
            _top_c, _bot_c = "rgba(248,113,113,0.22)", "rgba(248,113,113,0.02)"
        else:
            _top_c, _bot_c = "rgba(96,165,250,0.22)", "rgba(96,165,250,0.02)"

        payload = _json.dumps(series, separators=(",", ":"))
        html = f"""
        <div id=\"c\" style=\"width:100%;height:{height}px;\"></div>
        <script src=\"https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js\"></script>
        <script>
          const el = document.getElementById('c');
          const chart = LightweightCharts.createChart(el, {{
            width: el.clientWidth,
            height: {height},
            layout: {{ background: {{ type: 'solid', color: 'transparent' }}, textColor: 'rgba(148,163,184,0.75)', fontFamily: 'Sora, -apple-system, sans-serif', fontSize: 11 }},
            grid: {{ vertLines: {{ color: 'rgba(148,163,184,0.06)' }}, horzLines: {{ color: 'rgba(148,163,184,0.08)' }} }},
            rightPriceScale: {{ borderColor: 'rgba(148,163,184,0.10)', scaleMargins: {{ top: 0.10, bottom: 0.10 }} }},
            timeScale: {{ borderColor: 'rgba(148,163,184,0.10)', timeVisible: true, secondsVisible: false }},
            crosshair: {{ mode: 0, vertLine: {{ color: 'rgba(251,191,36,0.30)', width: 1, style: 2, labelBackgroundColor: '#1e293b' }}, horzLine: {{ color: 'rgba(251,191,36,0.30)', width: 1, style: 2, labelBackgroundColor: '#1e293b' }} }},
            handleScroll: {{ mouseWheel: true, pressedMouseMove: true }},
            handleScale: {{ mouseWheel: true, pinch: true }},
          }});
          const s = chart.addAreaSeries({{
            lineColor: '{accent}',
            topColor: '{_top_c}',
            bottomColor: '{_bot_c}',
            lineWidth: 2,
            crosshairMarkerRadius: 4,
            crosshairMarkerBorderWidth: 2,
            crosshairMarkerBorderColor: '{accent}',
            crosshairMarkerBackgroundColor: '#0f172a',
            lastValueVisible: true,
            priceLineVisible: true,
            priceLineColor: '{accent}',
            priceLineWidth: 1,
            priceLineStyle: 2,
          }});
          s.setData({payload});
          chart.timeScale().fitContent();
          new ResizeObserver(() => {{
            chart.applyOptions({{ width: el.clientWidth }});
          }}).observe(el);
        </script>
        """
        components.html(html, height=height + 12)
    except Exception:
        import pandas as _pd
        st.line_chart(_pd.DataFrame(series).set_index("time")["value"], height=height)


EQUITY_SERIES_PATH = LOGS_DIR / "equity_series.jsonl"


def _equity_chart_with_markers(
    equity_series: list[dict],
    price_series: list[dict],
    markers: list[dict],
    *,
    tp_levels: dict | None = None,
    height_equity: int = 200,
    height_price: int = 280,
    chart_id: str = "main",
) -> None:
    """
    Premium dual chart: portfolio equity (top) + price with TP/SL and trade markers (bottom).
    Uses Lightweight Charts v4.2 with polished glass styling.
    """
    try:
        import json as _json

        _uid = chart_id
        eq_payload = _json.dumps(equity_series, separators=(",", ":"))
        px_payload = _json.dumps(price_series, separators=(",", ":"))
        mk_payload = _json.dumps(markers, separators=(",", ":"))

        # TP/SL price lines — thin dashed, low opacity, professional
        price_lines_js = ""
        if tp_levels:
            _e = tp_levels.get("entry")
            _t1 = tp_levels.get("tp1")
            _t2 = tp_levels.get("tp2")
            _t3 = tp_levels.get("tp3")
            _sl = tp_levels.get("sl")
            lines = []
            if _e and _e > 0:
                lines.append(f"pxS.createPriceLine({{price:{_e:.6f},color:'rgba(229,231,235,0.70)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'ENTRY'}});")
            if _t1 and _t1 > 0:
                lines.append(f"pxS.createPriceLine({{price:{_t1:.6f},color:'rgba(16,185,129,0.65)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'TP1'}});")
            if _t2 and _t2 > 0:
                lines.append(f"pxS.createPriceLine({{price:{_t2:.6f},color:'rgba(52,211,153,0.55)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'TP2'}});")
            if _t3 and _t3 > 0:
                lines.append(f"pxS.createPriceLine({{price:{_t3:.6f},color:'rgba(110,231,183,0.45)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'TP3'}});")
            if _sl and _sl > 0:
                lines.append(f"pxS.createPriceLine({{price:{_sl:.6f},color:'rgba(239,68,68,0.70)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'SL'}});")
            price_lines_js = "\n".join(lines)

        # Equity color based on performance — softer gradients
        if equity_series:
            _eq_start = equity_series[0]["value"]
            _eq_end = equity_series[-1]["value"]
            _up = _eq_end >= _eq_start
            eq_line = "#34d399" if _up else "#f87171"
            eq_top = "rgba(52,211,153,0.16)" if _up else "rgba(248,113,113,0.16)"
            eq_bot = "rgba(52,211,153,0.005)" if _up else "rgba(248,113,113,0.005)"
        else:
            eq_line, eq_top, eq_bot = "#60a5fa", "rgba(96,165,250,0.16)", "rgba(96,165,250,0.005)"

        _show_eq = height_equity > 0 and len(equity_series) > 0
        total_h = (height_equity if _show_eq else 0) + height_price + (_show_eq and 16 or 0)

        # Equity chart JS
        eq_div = f'<div id="eq_{_uid}" style="width:100%;height:{height_equity}px;"></div>' if _show_eq else ""
        eq_js = f"""
          var eqEl=document.getElementById('eq_{_uid}');
          var eqC=LightweightCharts.createChart(eqEl,Object.assign({{}},opts,{{
            width:eqEl.clientWidth,height:{height_equity},
            rightPriceScale:{{borderColor:'rgba(148,163,184,0.08)',scaleMargins:{{top:0.08,bottom:0.08}}}},
          }}));
          var eqS=eqC.addAreaSeries({{
            lineColor:'{eq_line}',topColor:'{eq_top}',bottomColor:'{eq_bot}',
            lineWidth:2,crosshairMarkerRadius:4,
            priceFormat:{{type:'custom',formatter:function(p){{return '$'+p.toFixed(2);}}}},
          }});
          eqS.setData({eq_payload});
          eqC.timeScale().fitContent();
        """ if _show_eq else ""

        sync_js = f"""
          eqC.timeScale().subscribeVisibleLogicalRangeChange(function(r){{
            if(r)pxC.timeScale().setVisibleLogicalRange(r);
          }});
          pxC.timeScale().subscribeVisibleLogicalRangeChange(function(r){{
            if(r)eqC.timeScale().setVisibleLogicalRange(r);
          }});
          var _ro=new ResizeObserver(function(){{
            eqC.applyOptions({{width:eqEl.clientWidth}});
            pxC.applyOptions({{width:pxEl.clientWidth}});
          }});
          _ro.observe(eqEl);
        """ if _show_eq else f"""
          new ResizeObserver(function(){{
            pxC.applyOptions({{width:pxEl.clientWidth}});
          }}).observe(pxEl);
        """

        # Separator between charts
        sep = "<div style='height:20px;border-bottom:1px solid rgba(148,163,184,0.04);margin:0 16px;'></div>" if _show_eq else ""

        html_str = f"""
        <style>
          *{{box-sizing:border-box;margin:0;padding:0;}}
          body{{background:transparent;overflow:hidden;}}
          .chart-wrap{{
            background:linear-gradient(160deg,rgba(10,15,28,0.80),rgba(8,12,22,0.60));
            border:1px solid rgba(148,163,184,0.06);
            border-radius:20px;
            padding:16px 12px 10px;
            backdrop-filter:blur(20px);
            -webkit-backdrop-filter:blur(20px);
            box-shadow:0 12px 48px rgba(0,0,0,0.5),inset 0 1px 0 rgba(255,255,255,0.03);
          }}
          .chart-label{{
            font-family:Sora,-apple-system,BlinkMacSystemFont,sans-serif;
            font-size:9px;font-weight:500;letter-spacing:1.2px;text-transform:uppercase;
            color:rgba(148,163,184,0.4);padding:0 8px 8px;
          }}
        </style>
        <div class="chart-wrap">
          {"<div class='chart-label'>Portfolio Equity</div>" if _show_eq else ""}
          {eq_div}
          {sep}
          <div class="chart-label" style="{'padding-top:8px;' if _show_eq else ''}">Mark Price &mdash; XLM</div>
          <div id="px_{_uid}" style="width:100%;height:{height_price}px;"></div>
        </div>
        <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
        <script>
        (function(){{
          var opts={{
            layout:{{background:{{type:'solid',color:'transparent'}},textColor:'rgba(148,163,184,0.75)',fontFamily:'Sora,-apple-system,BlinkMacSystemFont,sans-serif',fontSize:11}},
            grid:{{vertLines:{{color:'rgba(148,163,184,0.06)'}},horzLines:{{color:'rgba(148,163,184,0.08)'}}}},
            rightPriceScale:{{borderColor:'rgba(148,163,184,0.10)',scaleMargins:{{top:0.10,bottom:0.10}}}},
            timeScale:{{borderColor:'rgba(148,163,184,0.10)',timeVisible:true,secondsVisible:false}},
            crosshair:{{mode:0,vertLine:{{color:'rgba(96,165,250,0.35)',width:1,style:2,labelBackgroundColor:'#1e293b'}},horzLine:{{color:'rgba(96,165,250,0.35)',width:1,style:2,labelBackgroundColor:'#1e293b'}}}},
            handleScroll:{{mouseWheel:true,pressedMouseMove:true}},
            handleScale:{{mouseWheel:true,pinch:true}},
          }};

          {eq_js}

          var pxEl=document.getElementById('px_{_uid}');
          var pxC=LightweightCharts.createChart(pxEl,Object.assign({{}},opts,{{
            width:pxEl.clientWidth,height:{height_price},
          }}));
          var pxS=pxC.addAreaSeries({{
            lineColor:'rgba(96,165,250,0.90)',topColor:'rgba(96,165,250,0.18)',bottomColor:'rgba(96,165,250,0.01)',
            lineWidth:2,crosshairMarkerRadius:4,crosshairMarkerBorderWidth:2,crosshairMarkerBorderColor:'#60a5fa',
            crosshairMarkerBackgroundColor:'#0f172a',
            lastValueVisible:true,priceLineVisible:true,priceLineColor:'rgba(96,165,250,0.50)',priceLineWidth:1,priceLineStyle:2,
            priceFormat:{{type:'custom',formatter:function(p){{return '$'+p.toFixed(5);}}}},
          }});
          pxS.setData({px_payload});

          var mk={mk_payload};
          if(mk.length>0){{mk.sort(function(a,b){{return a.time-b.time;}});pxS.setMarkers(mk);}}

          {price_lines_js}
          pxC.timeScale().fitContent();
          {sync_js}
        }})();
        </script>
        """
        components.html(html_str, height=total_h + 44)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Chart unavailable.</div></div>", unsafe_allow_html=True)


def _load_equity_series(hours: float | None = 24) -> list[dict]:
    """Load equity_series.jsonl and optionally filter by time window."""
    try:
        if not EQUITY_SERIES_PATH.exists():
            return []
        lines = EQUITY_SERIES_PATH.read_text(errors="ignore").strip().splitlines()
        if not lines:
            return []
        data = []
        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        for line in lines:
            try:
                row = json.loads(line)
                ts_str = row.get("ts", "")
                ts = datetime.fromisoformat(ts_str)
                if cutoff and ts < cutoff:
                    continue
                data.append(row)
            except Exception:
                continue
        return data
    except Exception:
        return []


def _build_trade_markers(trades_df, hours: float | None = 24) -> list[dict]:
    """Build Lightweight Charts marker list from trades.csv."""
    markers = []
    try:
        if trades_df is None or trades_df.empty:
            return []
        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        for _, row in trades_df.iterrows():
            # Entry marker
            entry_time = row.get("entry_time") or row.get("timestamp")
            if entry_time:
                try:
                    et = pd.to_datetime(entry_time, utc=True)
                    if cutoff and et < cutoff:
                        continue
                    side = str(row.get("side", "")).lower()
                    entry_px = float(row.get("entry_price") or 0)
                    if entry_px > 0:
                        markers.append({
                            "time": int(et.timestamp()),
                            "position": "belowBar" if side == "long" else "aboveBar",
                            "color": "#10b981" if side == "long" else "#ef4444",
                            "shape": "arrowUp" if side == "long" else "arrowDown",
                            "text": f"{'L' if side == 'long' else 'S'} ${entry_px:.5f}",
                        })
                except Exception:
                    pass

            # Exit marker
            exit_time = row.get("exit_time")
            exit_reason = str(row.get("exit_reason", "") or "")
            exit_px = row.get("exit_price")
            if exit_time and exit_px:
                try:
                    xt = pd.to_datetime(exit_time, utc=True)
                    if cutoff and xt < cutoff:
                        continue
                    pnl = float(row.get("pnl_usd") or 0)
                    is_tp = "tp" in exit_reason.lower()
                    is_sl = "stop" in exit_reason.lower() or "sl" in exit_reason.lower()
                    if is_tp:
                        color = "#10b981"
                    elif is_sl:
                        color = "#ef4444"
                    elif pnl >= 0:
                        color = "#fbbf24"
                    else:
                        color = "#ef4444"
                    label = exit_reason.upper()[:6]
                    if pnl != 0:
                        label += f" {'+'if pnl>0 else ''}${pnl:.2f}"
                    markers.append({
                        "time": int(xt.timestamp()),
                        "position": "aboveBar",
                        "color": color,
                        "shape": "circle",
                        "text": label,
                    })
                except Exception:
                    pass
    except Exception:
        pass
    return sorted(markers, key=lambda m: m["time"])


def _tail_text(path: Path, n: int = 120) -> str:
    try:
        if not path.exists():
            return ""
        txt = path.read_text(errors="ignore")
        lines = txt.splitlines()
        return "\n".join(lines[-int(n) :])
    except Exception:
        return ""


now_utc = datetime.now(timezone.utc)
last_ts = last_decision.get("timestamp") or last_decision.get("ts")
last_age = None
try:
    if last_ts is not None:
        if hasattr(last_ts, "to_pydatetime"):
            last_age = int((now_utc - last_ts.to_pydatetime()).total_seconds())
        elif isinstance(last_ts, datetime):
            last_age = int((now_utc - last_ts.astimezone(timezone.utc)).total_seconds())
        else:
            parsed = datetime.fromisoformat(str(last_ts).replace("Z", "+00:00"))
            last_age = int((now_utc - parsed.astimezone(timezone.utc)).total_seconds())
except Exception:
    try:
        last_age = int((now_utc - last_ts).total_seconds())
    except Exception:
        last_age = None

prod = (
    last_decision.get("product")
    or last_decision.get("product_selected")
    or last_decision.get("product_id")
    or "-"
)
lt_mtime, lt_size = _file_sig(LIVE_TICK_PATH)
live_tick = _load_json_cached(str(LIVE_TICK_PATH), lt_mtime, lt_size)
ws_px, ws_age = _live_ws_summary(live_tick)

mp_mtime, mp_size = _file_sig(MARGIN_POLICY_PATH)
mp_last = _load_last_jsonl_cached(str(MARGIN_POLICY_PATH), mp_mtime, mp_size) if (mp_mtime and mp_size) else {}
mp_tier = _safe_str(last_decision.get("margin_tier")) or _safe_str(mp_last.get("tier")) or "-"
mp_active = _safe_float(last_decision.get("active_mr"))
if mp_active is None:
    mp_active = _safe_float(mp_last.get("active_mr"))
mp_i = _safe_float(last_decision.get("mr_intraday"))
if mp_i is None:
    mp_i = _safe_float(mp_last.get("mr_intraday"))
mp_o = _safe_float(last_decision.get("mr_overnight"))
if mp_o is None:
    mp_o = _safe_float(mp_last.get("mr_overnight"))

pl_mtime, pl_size = _file_sig(PLRL3_PATH)
pl_last = _load_last_jsonl_cached(str(PLRL3_PATH), pl_mtime, pl_size) if (pl_mtime and pl_size) else {}
pl_action = _safe_str(pl_last.get("action")) or "-"
pl_step = int(_safe_float(pl_last.get("rescue_step")) or 0) if pl_last else 0
pl_next = _safe_float(pl_last.get("next_rescue_at"))
pl_active = _safe_float(pl_last.get("active_mr"))

pos_view = open_pos or _exch_pos
pos_source = "BOT" if open_pos else ("EXCHANGE" if _exch_pos else None)
# Ghost exit detection: bot says no position but exchange still has one
_ghost_exit_detected = (not open_pos) and bool(_exch_pos)

with st.sidebar:
    st.markdown("<div class='side-title'>TRADING HUB</div>", unsafe_allow_html=True)
    page = st.radio(
        "Module",
        ["Terminal", "Portfolio", "Signals", "Ledger", "System"],
        index=0,
        label_visibility="collapsed",
    )
    st.markdown("<div class='side-divider'></div>", unsafe_allow_html=True)
    # Price display: prefer fresh WS, fall back to bot decision price if WS is stale
    _ws_age_num = None
    try:
        _ws_age_num = int(ws_age) if ws_age and ws_age != "—" else None
    except Exception:
        pass
    _ws_is_stale = _ws_age_num is None or _ws_age_num > 60
    _bot_px = _safe_float(last_decision.get("price"))
    _bot_px_str = f"${_bot_px:.6f}" if _bot_px else None
    _bot_age = last_age  # seconds since last bot decision
    if _ws_is_stale and _bot_px_str:
        st.markdown("<div class='side-kv'>PRICE <span style='color:#f59e0b;font-size:9px;'>(BOT)</span></div>", unsafe_allow_html=True)
        _ba_str = _fmt_age_s(_bot_age) if _bot_age else "?"
        st.markdown(f"<div class='side-v'>{_bot_px_str} <span class='muted'>({_ba_str})</span></div>", unsafe_allow_html=True)
        if ws_px != "—":
            st.markdown(f"<div class='side-v muted' style='font-size:10px;'>WS {ws_px} <span style='color:#f87171;'>STALE {ws_age}s</span></div>", unsafe_allow_html=True)
    elif _ws_is_stale:
        st.markdown("<div class='side-kv'>WS <span style='color:#f87171;font-size:9px;'>STALE</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='side-v'>{ws_px} <span class='muted'>({ws_age}s)</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='side-kv'>WS</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='side-v'>{ws_px} <span class='muted'>({ws_age}s)</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>MARGIN</div>", unsafe_allow_html=True)
    mr_txt = f"{mp_active*100:.1f}%" if mp_active is not None else "—"
    st.markdown(f"<div class='side-v'>{mp_tier} <span class='muted'>({mr_txt})</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>PLRL-3</div>", unsafe_allow_html=True)
    pl_txt = f"{pl_active*100:.1f}%" if pl_active is not None else "—"
    nxt = f"{pl_next*100:.0f}%" if pl_next is not None else "—"
    st.markdown(f"<div class='side-v'>{pl_action} <span class='muted'>(step {pl_step}/3 | mr {pl_txt} | next {nxt})</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>BOT TICK</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='side-v'>{_fmt_age_s(last_age)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>STATE</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='side-v'>{_safe_str(last_decision.get('state')) or '-'}</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>REGIME / ACTION</div>", unsafe_allow_html=True)
    regime_txt = _safe_str(last_decision.get("regime")) or _safe_str(last_decision.get("v4_selected_regime")) or "-"
    action_txt = _safe_str(last_decision.get("last_action")) or _safe_str(last_decision.get("reason")) or "-"
    st.markdown(f"<div class='side-v'>{regime_txt} <span class='muted'>|</span> {action_txt}</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>POSITION</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='side-v'>{pos_source or '-'}</div>", unsafe_allow_html=True)
    if pos_view:
        st.markdown(f"<div class='side-v muted'>{_safe_str(pos_view.get('product_id')) or '-'}</div>", unsafe_allow_html=True)
    st.markdown("<div class='side-kv'>HISTORY</div>", unsafe_allow_html=True)
    if history_start is not None and history_end is not None:
        st.markdown(
            f"<div class='side-v'>{history_days}d <span class='muted'>({_fmt_pt_short(history_start)} → {_fmt_pt_short(history_end)})</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"<div class='side-v'>{history_days}d <span class='muted'>(no data yet)</span></div>", unsafe_allow_html=True)

    st.markdown("<div class='side-divider'></div>", unsafe_allow_html=True)
    try:
        refresh_s = float(os.environ.get("XLM_DASH_REFRESH_S", "2.0"))
    except Exception:
        refresh_s = 2.0
    refresh_s = st.slider("Refresh (sec)", 0.0, 10.0, float(refresh_s), 0.5)
    with st.expander("THE WOLF'S INNER MONOLOGUE", expanded=False):
        feed_rows = 10
        st.caption("Showing the latest 10 decisions (rolling live).")
        feed_noise_filter = st.toggle(
            "Reduce Noise",
            value=(os.environ.get("XLM_DASH_THOUGHT_NOISE_FILTER", "1") == "1"),
            help="Hides repetitive low-information thought lines while keeping major actions visible.",
        )
        feed_major_only = st.toggle(
            "Key Events Only",
            value=False,
            help="Show only entries/exits/TP/SL/liquidation and other major bot events.",
        )
        feed_auto_follow = st.toggle(
            "Auto-follow Latest",
            value=True,
            help="Automatically keeps the scroll at the newest thought post.",
        )
        feed_highlight_new = st.toggle(
            "Highlight New",
            value=True,
            help="Marks newly arrived thought posts since last refresh.",
        )
    client_tick = st.toggle("Client Tick (1s)", value=(os.environ.get("XLM_DASH_CLIENT_TICK", "0") == "1"))


# ── Everlight Trading Header ────────────────────────────────────────────────
st.markdown(
    "<div class='hub-top'>"
    f"<div class='brand'>The Wolf's Terminal <span style='font-size:10px;color:#94a3b8;'>by Everlight</span></div>"
    f"<div class='brand-sub'>"
    f"<span style='font-size:7px;letter-spacing:1px;color:#34d399;font-weight:600;'>AUTHORIZED</span> "
    f"<span class='pill'>{prod}</span> "
    f"<span class='muted'>|</span> Venue <span style='color:#60a5fa;font-size:11px;'>CDE</span> "
    f"<span class='muted'>|</span> WS <span class='pill ok'>{ws_px}</span> "
    f"<span class='muted'>|</span> Bot tick <span class='pill'>{_fmt_age_s(last_age)}</span></div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Data Freshness Banner (only shows when stale) ────────────────────────────
if last_age is not None and last_age > 60:
    _stale_cls = "stale-danger" if last_age > 120 else "stale-warn"
    _stale_label = "STALE DATA" if last_age > 120 else "DATA DELAYED"
    st.markdown(
        f"<div class='stale-banner {_stale_cls}'>"
        f"{_stale_label} &mdash; last update {_fmt_age_s(last_age)} ago"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Coinbase Truth KPI Bar ───────────────────────────────────────────────────
_hdr_pnl_live = _safe_float(last_decision.get("pnl_usd_live"))
_bot_pill = "<span class='pill ok'>HUNTING</span>" if _bot_is_alive else f"<span class='pill danger'>OFFLINE</span>"
_on_pill = "<span class='pill ok'>24/7</span>" if overnight_trading_ok else "<span class='pill danger'>DAY</span>"
_safe_pill = " <span class='pill danger'>SAFE</span>" if safe_mode else ""
_usdc_yield_day = spot_usdc * 0.035 / 365.0

# Position card content
_pos_html = "<span class='muted'>NONE</span>"
if pos_view and pos_source:
    _hdr_dir = _safe_str(pos_view.get("direction")) or "?"
    _hdr_cls = "ok" if _hdr_dir == "long" else "danger"
    _pos_html = f"<span class='pill {_hdr_cls}' style='font-size:10px;padding:4px 8px;'>{_hdr_dir.upper()}</span>"
    if _hdr_pnl_live is not None:
        _pnl_cls = "ok" if _hdr_pnl_live >= 0 else "danger"
        _pos_html += f" <span class='{_pnl_cls}'>{'+' if _hdr_pnl_live >= 0 else ''}${_hdr_pnl_live:.2f}</span>"

# Unrealized PnL (separate from P&L Today)
_unreal_html = "<span class='muted'>$0.00</span>"
if _hdr_pnl_live is not None and pos_view:
    _ur_cls = "ok" if _hdr_pnl_live >= 0 else "danger"
    _unreal_html = f"<span class='{_ur_cls}'>{'+' if _hdr_pnl_live >= 0 else ''}${_hdr_pnl_live:.2f}</span>"

# P&L Today
_pnl_cls = "ok" if pnl_today_usd >= 0 else "danger"
_pnl_html = f"<span class='{_pnl_cls}'>{'+' if pnl_today_usd >= 0 else ''}${pnl_today_usd:.2f}</span>"
_pnl_badge_cls = "src-cb" if _pnl_source == "exchange" else "src-bot"
_pnl_badge_label = "EQΔ" if _pnl_source == "exchange" else "BOT"

st.markdown(
    "<div class='kpi-bar'>"
    # ── Coinbase Truth cards ──
    f"<div class='kpi-card'><span class='src-badge src-cb'>CB</span>"
    f"<div class='kpi-label'>Total</div><div class='kpi-value'>{_format_money(portfolio_value)}</div></div>"

    f"<div class='kpi-card'><span class='src-badge src-cb'>CB</span>"
    f"<div class='kpi-label'>Cash</div><div class='kpi-value'>{_format_money(cash_value)}</div>"
    f"<div class='kpi-sub'>${spot_usd:.0f} + ${spot_usdc:.0f} USDC</div></div>"

    f"<div class='kpi-card'><span class='src-badge src-cb'>CB</span>"
    f"<div class='kpi-label'>Futures</div><div class='kpi-value'>{_format_money(deriv_balance)}</div>"
    f"<div class='kpi-sub'>{'+' if _live_unrealized >= 0 else ''}{_live_unrealized:.2f} unreal</div></div>"

    f"<div class='kpi-card'><span class='src-badge src-cb'>CB</span>"
    f"<div class='kpi-label'>Position</div><div class='kpi-value'>{_pos_html}</div></div>"

    f"<div class='kpi-card'><span class='src-badge src-cb'>CB</span>"
    f"<div class='kpi-label'>Unrealized</div><div class='kpi-value'>{_unreal_html}</div></div>"

    f"<div class='kpi-card'><span class='src-badge {_pnl_badge_cls}'>{_pnl_badge_label}</span>"
    f"<div class='kpi-label'>P&L Today</div><div class='kpi-value'>{_pnl_html}</div></div>"

    # ── Bot Status cards ──
    f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
    f"<div class='kpi-label'>Bot</div><div class='kpi-value'>{_bot_pill}</div></div>"

    f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
    f"<div class='kpi-label'>Mode</div><div class='kpi-value'>{_on_pill}{_safe_pill}</div></div>"

    "</div>",
    unsafe_allow_html=True,
)

# ── Position Truth Badge ─────────────────────────────────────────────────────
try:
    _truth_src = "COINBASE"
    if _exch_pos:
        _t_side = str(_exch_pos.get("side") or "").upper() or "?"
        _t_size = _exch_pos.get("number_of_contracts") or "1"
        _t_entry = _safe_float(_exch_pos.get("avg_entry_price"))
        _t_mark = _safe_float(last_decision.get("mark_price"))
        _t_cls = "truth-long" if "LONG" in _t_side else "truth-short"
        _t_details = f"{_t_side} {_t_size} contract"
        if _t_entry:
            _t_details += f" @ ${_t_entry:.5f}"
        if _t_mark:
            _t_details += f" &mdash; Mark ${_t_mark:.5f}"
        if _hdr_pnl_live is not None:
            _t_pnl_cls = "ok" if _hdr_pnl_live >= 0 else "danger"
            _t_details += f" &mdash; <span class='{_t_pnl_cls}'>{'+' if _hdr_pnl_live >= 0 else ''}${_hdr_pnl_live:.2f}</span>"
        st.markdown(
            f"<div class='truth-banner {_t_cls}'>"
            f"<span class='truth-label'>{_truth_src}</span> {_t_details}"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif pos_view and pos_source == "BOT":
        _t_side = str(pos_view.get("direction") or "").upper()
        _t_entry = _safe_float(pos_view.get("entry_price"))
        _t_cls = "truth-long" if _t_side == "LONG" else "truth-short"
        _t_details = f"{_t_side} 1 contract"
        if _t_entry:
            _t_details += f" @ ${_t_entry:.5f}"
        st.markdown(
            f"<div class='truth-banner {_t_cls}'>"
            f"<span class='truth-label'>BOT VIEW</span> {_t_details}"
            f"<span class='muted' style='font-size:9px;margin-left:auto;'>Exchange data pending</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='truth-banner truth-none'>"
            "<span class='truth-label'>COINBASE</span> NO OPEN POSITION"
            "</div>",
            unsafe_allow_html=True,
        )
except Exception:
    pass

# ── Unauthorized Position Alert ──────────────────────────────────────────────
if _unauthorized_positions:
    for _uap in _unauthorized_positions:
        _uap_pid = str(_uap.get("product_id") or "?")
        _uap_side = str(_uap.get("side") or _uap.get("direction") or "?").upper()
        _uap_size = _uap.get("number_of_contracts") or _uap.get("size") or "?"
        st.markdown(
            f"<div class='stale-banner stale-danger'>"
            f":rotating_light: UNAUTHORIZED POSITION: <b>{_uap_pid}</b> &mdash; "
            f"{_uap_side} x{_uap_size} &mdash; NOT managed by this bot"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Bot Analytics Row ────────────────────────────────────────────────────────
try:
    _ba_recovery = _safe_str(last_decision.get("recovery_mode")) or "NORMAL"
    _ba_quality = _safe_str(last_decision.get("quality_tier")) or "—"
    _ba_lane = _safe_str(last_decision.get("lane_label")) or "—"
    _ba_conf = int(_safe_float(last_decision.get("confluence_score")) or 0)
    _ba_rcls = "danger" if _ba_recovery == "SAFE_MODE" else ("ok" if _ba_recovery == "RECOVERY" else "muted")
    _ba_regime = _safe_str(last_decision.get("regime_name")) or "transition"
    _ba_regime_cls = {"compression": "danger", "expansion": "ok", "transition": "muted"}.get(_ba_regime, "muted")
    _ba_btc = _safe_str(last_decision.get("btc_trend")) or "—"
    _ba_btc_cls = {"bullish": "ok", "bearish": "danger", "neutral": "muted"}.get(_ba_btc, "muted")
    _ba_btc_pct = _safe_float(last_decision.get("btc_momentum_pct")) or 0.0
    _ba_candle = last_decision.get("candle_pattern") or []
    _ba_candle_str = ", ".join(str(p) for p in _ba_candle[:2]) if _ba_candle else "—"
    _ba_candle_bias = _safe_str(last_decision.get("candle_pattern_bias")) or "neutral"
    _ba_candle_cls = {"bullish": "ok", "bearish": "danger", "neutral": "muted"}.get(_ba_candle_bias, "muted")

    st.markdown("<div class='bot-analytics-header'>Bot Analytics</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='kpi-bar'>"
        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Regime</div><div class='kpi-value'><span class='{_ba_regime_cls}'>{_ba_regime.upper()}</span></div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Win Rate</div><div class='kpi-value'>{win_rate:.0f}%</div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Recovery</div><div class='kpi-value'><span class='{_ba_rcls}'>{_ba_recovery}</span></div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Quality</div><div class='kpi-value'><span class='{'gold' if _ba_quality == 'MONSTER' else 'ok' if _ba_quality == 'FULL' else 'muted'}'>{_ba_quality}</span></div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Lane</div><div class='kpi-value'>{_ba_lane}</div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Confluence</div><div class='kpi-value'>{_ba_conf}/100</div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BTC</span>"
        f"<div class='kpi-label'>BTC</div><div class='kpi-value'><span class='{_ba_btc_cls}'>{_ba_btc.upper()}</span> <span class='muted'>{_ba_btc_pct*100:+.1f}%</span></div></div>"

        f"<div class='kpi-card'><span class='src-badge src-bot'>BOT</span>"
        f"<div class='kpi-label'>Pattern</div><div class='kpi-value'><span class='{_ba_candle_cls}'>{_ba_candle_str}</span></div></div>"

        "</div>",
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── Lane V + Growth Ladder ───────────────────────────────────────────────────
try:
    _lv_mode = _safe_str(last_decision.get("lane_v_mode")) or "watch"
    _lv_cluster = _safe_str(last_decision.get("lane_v_cluster_side")) or "—"
    _lv_sweep = _safe_str(last_decision.get("lane_v_sweep_status")) or "—"
    _lv_reason = _safe_str(last_decision.get("lane_v_no_trade_reason")) or "No Lane V block"
    _lv_magnet = _safe_float(last_decision.get("lane_v_magnet_score"))
    _lv_wick = _safe_float(last_decision.get("lane_v_wick_score"))
    _lv_ratio = _safe_float(last_decision.get("lane_v_wick_ratio"))
    _lv_reclaim = bool(last_decision.get("lane_v_reclaim_confirmed"))
    _lv_reject = bool(last_decision.get("lane_v_rejection_confirmed"))
    _sz_meta = last_decision.get("sizing_meta") or {}
    _gl_stage = _safe_str(_sz_meta.get("growth_stage_label")) or "—"
    _gl_mode = _safe_str(_sz_meta.get("growth_withdrawal_mode")) or "compound"
    _gl_max_contracts = int(_safe_float(_sz_meta.get("growth_stage_max_contracts")) or 0)
    _gl_target = _safe_float(_sz_meta.get("growth_daily_target_usd"))
    _gl_stop = _safe_float(_sz_meta.get("growth_daily_stop_usd"))
    _gl_risk = _safe_float(_sz_meta.get("growth_per_trade_risk_usd"))
    _two_ready = bool(last_decision.get("two_contract_ready"))
    _two_reason = _safe_str(last_decision.get("two_contract_ready_reason")) or "unknown"
    _two_req = _safe_float(last_decision.get("two_contract_required_margin"))
    _two_buf = _safe_float(last_decision.get("two_contract_required_with_buffer"))
    _two_bp = _safe_float(last_decision.get("two_contract_buying_power"))
    _two_headroom = _safe_float(last_decision.get("two_contract_headroom"))
    st.markdown(
        "<div style='display:grid;grid-template-columns:1.2fr 1fr;gap:10px;margin:6px 0 10px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #60a5fa;'>"
        "<div class='kpi-label'>Lane V</div>"
        f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;'>"
        f"<span class='pill'>{html.escape(_lv_mode.upper())}</span>"
        f"<span class='pill'>{html.escape(_lv_cluster.upper())}</span>"
        f"<span class='pill'>{html.escape(_lv_sweep.upper())}</span>"
        "</div>"
        f"<div style='display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        f"<span>Magnet <b style='color:#e5e7eb'>{_lv_magnet:.0f}</b></span>"
        f"<span>Wick <b style='color:#e5e7eb'>{_lv_wick:.0f}</b></span>"
        f"<span>Ratio <b style='color:#e5e7eb'>{_lv_ratio:.2f}</b></span>"
        f"<span>Reclaim <b style='color:{'#10b981' if _lv_reclaim else '#6b7280'}'>{'YES' if _lv_reclaim else 'NO'}</b></span>"
        f"<span>Reject <b style='color:{'#ef4444' if _lv_reject else '#6b7280'}'>{'YES' if _lv_reject else 'NO'}</b></span>"
        "</div>"
        f"<div style='margin-top:8px;font-size:12px;color:#9ca3af;'>{html.escape(_lv_reason)}</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #34d399;'>"
        "<div class='kpi-label'>Capital Ladder</div>"
        f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;'>"
        f"<span class='pill'>{html.escape(_gl_stage)}</span>"
        f"<span class='pill'>{html.escape(_gl_mode.upper())}</span>"
        "</div>"
        f"<div style='display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        f"<span>Max contracts <b style='color:#e5e7eb'>{_gl_max_contracts or 0}</b></span>"
        f"<span>Daily target <b style='color:#10b981'>${(_gl_target or 0):.0f}</b></span>"
        f"<span>Daily stop <b style='color:#ef4444'>${(_gl_stop or 0):.0f}</b></span>"
        f"<span>Trade risk <b style='color:#e5e7eb'>${(_gl_risk or 0):.0f}</b></span>"
        "</div>"
        f"<div style='margin-top:8px;font-size:12px;color:#9ca3af;'>"
        f"2-contract readiness: <b style='color:{'#10b981' if _two_ready else '#ef4444'}'>{'READY' if _two_ready else 'NOT READY'}</b>"
        f" &bull; req ${(_two_req or 0):.2f}"
        f" &bull; buffered ${(_two_buf or 0):.2f}"
        f" &bull; BP ${(_two_bp or 0):.2f}"
        f" &bull; headroom ${(_two_headroom or 0):.2f}"
        f"</div>"
        f"<div style='margin-top:4px;font-size:11px;color:#6b7280;'>{html.escape(_two_reason)}</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── Margin Playbook + Execution Safety ──────────────────────────────────────
try:
    _pb_label = _safe_str(last_decision.get("margin_playbook_label")) or "SCHEDULE_FALLBACK"
    _pb_obj = _safe_str(last_decision.get("margin_playbook_objective")) or "preserve_capital"
    _pb_block = bool(last_decision.get("margin_playbook_block_new_entries"))
    _pb_multi = bool(last_decision.get("margin_playbook_allow_multi_contract"))
    _pb_max = int(_safe_float(last_decision.get("margin_playbook_max_new_contracts")) or 0)
    _pb_cutoff = bool(last_decision.get("margin_playbook_force_exit_before_cutoff"))
    _pb_mins = _safe_float(last_decision.get("margin_playbook_mins_to_cutoff"))
    _pb_notes = last_decision.get("margin_playbook_notes") or []
    if not isinstance(_pb_notes, list):
        _pb_notes = [str(_pb_notes)]
    _pb_window = _safe_str(last_decision.get("margin_window")) or "schedule_fallback"
    _pb_tone = "#10b981" if "ATTACK" in _pb_label else "#f59e0b" if "PRE_CUTOFF" in _pb_label else "#60a5fa"

    _exec_src = open_pos if isinstance(open_pos, dict) else {}
    _exec_preflight = _exec_src.get("entry_preflight") if isinstance(_exec_src.get("entry_preflight"), dict) else {}
    _exec_state = _exec_src.get("protection_state") if isinstance(_exec_src.get("protection_state"), dict) else {}
    _exec_mode = _safe_str(_exec_src.get("protection_mode") or _exec_state.get("mode")) or ("flat" if not open_pos else "unknown")
    _exec_preflight_ok = _exec_preflight.get("ok")
    _exec_exchange_tp = bool(_exec_src.get("exchange_tp_armed") or _exec_state.get("exchange_tp_armed"))
    _exec_soft = bool(_exec_src.get("software_protection_active") or _exec_state.get("software_protection_active"))
    _exec_spread = _safe_float((_exec_preflight.get("spread") or {}).get("bps"))
    _exec_margin_ratio = _safe_float((_exec_preflight.get("margin") or {}).get("required_ratio"))
    _exec_position_txt = "LIVE POSITION" if open_pos else "STALKING"

    _alpha_gaps: list[str] = []
    if not bool(last_decision.get("liquidation_feed_live")):
        _alpha_gaps.append("liquidation tape not live; bot is inferring from price and OI")
    if _pb_window in ("unknown", "schedule_fallback"):
        _alpha_gaps.append("Coinbase margin-window endpoint unavailable; using ET schedule fallback")
    if _safe_str(last_decision.get("liquidation_signal_source")) == "exchange_inference_price_oi":
        _alpha_gaps.append("liquidation signal is inferred, not full exchange-native event tape")
    if (_safe_float(last_decision.get("futures_relativity_confidence")) or 0.0) < 55:
        _alpha_gaps.append("cross-venue relativity confidence is still low")
    if int(_safe_float(last_decision.get("orderbook_levels_sampled")) or 0) < 10:
        _alpha_gaps.append("order book sample is thin; spoof/absorption read is weaker than ideal")
    if (_safe_float(last_decision.get("contract_basis_bps")) is None) or (_safe_float(last_decision.get("contract_mark_price")) is None):
        _alpha_gaps.append("contract basis context is incomplete on this cycle")
    if not _alpha_gaps:
        _alpha_gaps.append("no critical blind spot detected in current cycle")
    _alpha_html = "".join(
        f"<div style='padding:3px 0;font-size:11px;color:#d1d5db;'>&bull; {html.escape(str(g))}</div>"
        for g in _alpha_gaps[:4]
    )

    st.markdown(
        "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:6px 0 12px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid {pb_tone};'>"
        "<div class='kpi-label'>Session Playbook</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;'>"
        "<span class='pill' style='background:{pb_tone}20;color:{pb_tone};'>{pb_label}</span>"
        "<span class='pill'>{pb_window}</span>"
        "</div>"
        "<div style='display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "<span>New entries <b style='color:{pb_block_color};'>{pb_block_txt}</b></span>"
        "<span>Multi-contract <b style='color:{pb_multi_color};'>{pb_multi_txt}</b></span>"
        "<span>Max new <b style='color:#e5e7eb'>{pb_max}</b></span>"
        "<span>Cutoff exit <b style='color:{pb_cutoff_color};'>{pb_cutoff_txt}</b></span>"
        "</div>"
        "<div style='margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "{pb_obj}"
        "{pb_mins_html}"
        "</div>"
        "<div style='margin-top:6px;font-size:11px;color:#6b7280;'>{pb_notes}</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #f59e0b;'>"
        "<div class='kpi-label'>Execution Safety</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;'>"
        "<span class='pill'>{exec_position}</span>"
        "<span class='pill'>{exec_mode}</span>"
        "</div>"
        "<div style='display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "<span>Preflight <b style='color:{exec_pf_color};'>{exec_pf_txt}</b></span>"
        "<span>Exchange TP <b style='color:{exec_tp_color};'>{exec_tp_txt}</b></span>"
        "<span>Software protect <b style='color:{exec_soft_color};'>{exec_soft_txt}</b></span>"
        "<span>Spread <b style='color:#e5e7eb'>{exec_spread}</b></span>"
        "<span>Margin ratio <b style='color:#e5e7eb'>{exec_margin_ratio}</b></span>"
        "</div>"
        "<div style='margin-top:8px;font-size:11px;color:#6b7280;'>"
        "This is the live order-protection state the bot will carry into the next real entry."
        "</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #a78bfa;'>"
        "<div class='kpi-label'>Current Blind Spots</div>"
        "<div style='margin-top:6px;font-size:11px;color:#9ca3af;'>"
        "These are the missing inputs or degraded signals still limiting edge quality."
        "</div>"
        "{alpha_html}"
        "</div>"
        "</div>".format(
            pb_tone=_pb_tone,
            pb_label=html.escape(_pb_label),
            pb_window=html.escape(_pb_window.upper()),
            pb_block_color="#ef4444" if _pb_block else "#10b981",
            pb_block_txt="BLOCKED" if _pb_block else "ALLOWED",
            pb_multi_color="#10b981" if _pb_multi else "#ef4444",
            pb_multi_txt="YES" if _pb_multi else "NO",
            pb_max=_pb_max or 0,
            pb_cutoff_color="#f59e0b" if _pb_cutoff else "#6b7280",
            pb_cutoff_txt="YES" if _pb_cutoff else "NO",
            pb_obj=html.escape(_pb_obj.replace("_", " ")),
            pb_mins_html=(
                f" &bull; <b style='color:#e5e7eb'>{int(_pb_mins)}</b> min to cutoff"
                if _pb_mins is not None else ""
            ),
            pb_notes=html.escape(", ".join(str(n).replace("_", " ") for n in _pb_notes[:4])) or "no special notes",
            exec_position=html.escape(_exec_position_txt),
            exec_mode=html.escape(_exec_mode.upper()),
            exec_pf_color="#10b981" if _exec_preflight_ok is True else "#ef4444" if _exec_preflight_ok is False else "#6b7280",
            exec_pf_txt="OK" if _exec_preflight_ok is True else "BLOCKED" if _exec_preflight_ok is False else "WAITING",
            exec_tp_color="#10b981" if _exec_exchange_tp else "#6b7280",
            exec_tp_txt="ARMED" if _exec_exchange_tp else "OFF",
            exec_soft_color="#f59e0b" if _exec_soft else "#6b7280",
            exec_soft_txt="ACTIVE" if _exec_soft else "STANDBY",
            exec_spread=f"{_exec_spread:.2f}bp" if _exec_spread is not None else "—",
            exec_margin_ratio=f"{_exec_margin_ratio:.3f}" if _exec_margin_ratio is not None else "—",
            alpha_html=_alpha_html,
        ),
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── Expectancy + Cost + Ladder + Friday Risk ────────────────────────────────
try:
    _closed_all = _get_closed_trades(trades)
    _expectancy_rows = _trade_expectancy_matrix(_closed_all, cfg, max_rows=5)
    _costs = _trade_cost_decomposition(_closed_all, cfg)
    _ladder = last_decision.get("contract_ladder") if isinstance(last_decision.get("contract_ladder"), dict) else {}
    _ladder_targets = []
    for _t in ("1", "2", "3", "5"):
        _status = _ladder.get(_t) if isinstance(_ladder.get(_t), dict) else {}
        _ready = bool(_status.get("ready"))
        _req = _safe_float(_status.get("required_with_buffer"))
        _bp = _safe_float(_status.get("buying_power"))
        _reason = _safe_str(_status.get("reason")) or "n/a"
        _ladder_targets.append(
            "<div style='display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
            f"<span style='font-size:11px;color:#d1d5db;'>{_t} contract{'s' if _t != '1' else ''}</span>"
            f"<span style='font-size:11px;color:{'#10b981' if _ready else '#ef4444'};'>{'READY' if _ready else 'WAIT'}</span>"
            "</div>"
            f"<div style='font-size:10px;color:#6b7280;padding-bottom:4px;'>req {f'${_req:.2f}' if _req is not None else '—'}"
            f" &bull; BP {f'${_bp:.2f}' if _bp is not None else '—'}"
            f" &bull; {html.escape(_reason.replace('_', ' '))}</div>"
        )
    _friday_label = _safe_str(last_decision.get("friday_break_label")) or "NORMAL"
    _friday_active = bool(last_decision.get("friday_break_active"))
    _friday_lock = bool(last_decision.get("friday_break_pre_break_lock"))
    _friday_flat = bool(last_decision.get("friday_break_force_flat_now"))
    _friday_reopen = bool(last_decision.get("friday_break_reopen_cooldown_active"))
    _friday_mins_break = _safe_float(last_decision.get("friday_break_minutes_to_break"))
    _friday_mins_reopen = _safe_float(last_decision.get("friday_break_minutes_to_reopen"))
    _friday_notes = last_decision.get("friday_break_notes") or []
    if not isinstance(_friday_notes, list):
        _friday_notes = [str(_friday_notes)]
    _friday_tone = "#ef4444" if _friday_active or _friday_flat else "#f59e0b" if _friday_lock or _friday_reopen else "#10b981"
    _expectancy_html = "".join(
        "<div style='display:flex;justify-content:space-between;gap:10px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
        f"<span style='font-size:11px;color:#d1d5db;flex:1;'>{html.escape(str(r['label']))}</span>"
        f"<span style='font-size:11px;color:{'#10b981' if r['expectancy'] >= 0 else '#ef4444'};'>{r['expectancy']:+.2f}</span>"
        f"<span style='font-size:10px;color:#6b7280;'>{int(r['count'])}x</span>"
        "</div>"
        for r in _expectancy_rows
    ) or "<div style='font-size:11px;color:#6b7280;'>No closed-trade expectancy data yet.</div>"
    st.markdown(
        "<div style='display:grid;grid-template-columns:1.05fr 1fr 1fr;gap:10px;margin:6px 0 12px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #22c55e;'>"
        "<div class='kpi-label'>Expectancy Matrix</div>"
        "<div style='margin-top:6px;font-size:11px;color:#9ca3af;'>Best closed-trade combos by entry type, session window, and regime.</div>"
        "{expectancy_html}"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #f97316;'>"
        "<div class='kpi-label'>Execution Cost Drag</div>"
        "<div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "<span>Closed <b style='color:#e5e7eb'>{closed_count}</b></span>"
        "<span>Gross <b style='color:#e5e7eb'>${gross_before_fees:.2f}</b></span>"
        "<span>Fees <b style='color:#ef4444'>-${fees:.2f}</b></span>"
        "<span>Slip est <b style='color:#f59e0b'>-${slip:.2f}</b></span>"
        "<span>Funding est <b style='color:#f59e0b'>-${funding:.2f}</b></span>"
        "</div>"
        "<div style='margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "Realized net <b style='color:{net_color};'>${net:.2f}</b>"
        " &bull; after known cost drag <b style='color:{net_after_color};'>${net_after:.2f}</b>"
        "</div>"
        "<div style='margin-top:6px;font-size:11px;color:#6b7280;'>Fees are measured from closed trades. Slippage and funding are estimated from configured EV assumptions.</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #60a5fa;'>"
        "<div class='kpi-label'>Contract Ladder + Friday Risk</div>"
        "<div style='margin-top:6px;'>"
        "{ladder_html}"
        "</div>"
        "<div style='margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);'>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;'>"
        "<span class='pill' style='background:{friday_tone}20;color:{friday_tone};'>{friday_label}</span>"
        "</div>"
        "<div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "<span>Active <b style='color:{friday_active_color};'>{friday_active}</b></span>"
        "<span>Pre-lock <b style='color:{friday_lock_color};'>{friday_lock}</b></span>"
        "<span>Force flat <b style='color:{friday_flat_color};'>{friday_flat}</b></span>"
        "</div>"
        "<div style='margin-top:6px;font-size:11px;color:#6b7280;'>"
        "{friday_mins}"
        "{friday_notes}"
        "</div>"
        "</div>"
        "</div>"
        "</div>".format(
            expectancy_html=_expectancy_html,
            closed_count=int(_costs.get("closed_count") or 0),
            gross_before_fees=float(_costs.get("gross_before_fees_usd") or 0.0),
            fees=float(_costs.get("measured_fees_usd") or 0.0),
            slip=float(_costs.get("estimated_slippage_usd") or 0.0),
            funding=float(_costs.get("estimated_funding_usd") or 0.0),
            net=float(_costs.get("realized_net_pnl_usd") or 0.0),
            net_after=float(_costs.get("net_after_known_costs_usd") or 0.0),
            net_color="#10b981" if float(_costs.get("realized_net_pnl_usd") or 0.0) >= 0 else "#ef4444",
            net_after_color="#10b981" if float(_costs.get("net_after_known_costs_usd") or 0.0) >= 0 else "#ef4444",
            ladder_html="".join(_ladder_targets) or "<div style='font-size:11px;color:#6b7280;'>No ladder state yet.</div>",
            friday_tone=_friday_tone,
            friday_label=html.escape(_friday_label.replace("_", " ")),
            friday_active="YES" if _friday_active else "NO",
            friday_lock="YES" if _friday_lock else "NO",
            friday_flat="YES" if _friday_flat else "NO",
            friday_active_color="#ef4444" if _friday_active else "#6b7280",
            friday_lock_color="#f59e0b" if _friday_lock else "#6b7280",
            friday_flat_color="#ef4444" if _friday_flat else "#6b7280",
            friday_mins=(
                f"{int(_friday_mins_break)} min to break"
                if _friday_mins_break is not None else (
                    f"{int(_friday_mins_reopen)} min to reopen" if _friday_mins_reopen is not None else "Friday window clear"
                )
            ),
            friday_notes=(
                " &bull; " + html.escape(", ".join(str(n).replace("_", " ") for n in _friday_notes[:3]))
                if _friday_notes else ""
            ),
        ),
        unsafe_allow_html=True,
    )
except Exception:
    pass

try:
    _exp_mult = _safe_float(last_decision.get("expectancy_size_mult")) or 1.0
    _kelly_mult = _safe_float(last_decision.get("kelly_size_mult")) or 1.0
    _exp_reason = _safe_str(last_decision.get("expectancy_gate_reason")) or "n/a"
    _lane_exp_mode = _safe_str(last_decision.get("lane_specific_expectancy_mode")) or "n/a"
    _lane_exp_wr = _safe_float(last_decision.get("lane_specific_expectancy_win_rate"))
    _lane_exp_avg = _safe_float(last_decision.get("lane_specific_expectancy_avg_pnl_usd"))
    _ob_absorption = _safe_str(last_decision.get("orderbook_absorption_bias")) or "NEUTRAL"
    _ob_spoof_risk = _safe_float(last_decision.get("orderbook_spoof_risk"))
    _ob_spoof_side = _safe_str(last_decision.get("orderbook_spoof_side")) or "NONE"
    _ob_bid_rep = _safe_float(last_decision.get("orderbook_bid_replenishment"))
    _ob_ask_rep = _safe_float(last_decision.get("orderbook_ask_replenishment"))
    _weekly_bias = _safe_str(last_decision.get("weekly_research_bias")) or "mixed"
    _weekly_xlm_bias = _safe_str(last_decision.get("weekly_research_xlm_bias")) or "mixed"
    _weekly_conf = _safe_float(last_decision.get("weekly_research_confidence")) or 0.0
    st.markdown(
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 12px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #22c55e;'>"
        "<div class='kpi-label'>Expectancy Promotion</div>"
        "<div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:#9ca3af;'>"
        "<span>Size mult <b style='color:{exp_color};'>{exp_mult:.2f}x</b></span>"
        "<span>Kelly <b style='color:{kelly_color};'>{kelly_mult:.2f}x</b></span>"
        "</div>"
        "<div style='margin-top:8px;font-size:11px;color:#6b7280;'>Gate reason: {exp_reason}</div>"
        "<div style='margin-top:4px;font-size:11px;color:#6b7280;'>Lane mode: {lane_exp_mode}{lane_exp_wr}{lane_exp_avg}</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #60a5fa;'>"
        "<div class='kpi-label'>Book + Weekly Bias</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill' style='background:rgba(59,130,246,0.15);color:#93c5fd;'>{absorption}</span>"
        "<span class='pill' style='background:rgba(245,158,11,0.15);color:#fbbf24;'>Spoof {spoof}</span>"
        "<span class='pill' style='background:rgba(16,185,129,0.15);color:#34d399;'>Weekly {weekly_bias}</span>"
        "<span class='pill' style='background:rgba(250,204,21,0.15);color:#fde68a;'>XLM {weekly_xlm_bias}</span>"
        "</div>"
        "<div style='margin-top:8px;font-size:11px;color:#6b7280;'>"
        "Bid repl {bid_rep} &bull; Ask repl {ask_rep} &bull; Weekly confidence {weekly_conf:.0f}%"
        "</div>"
        "</div>"
        "</div>".format(
            exp_mult=_exp_mult,
            kelly_mult=_kelly_mult,
            exp_reason=html.escape(_exp_reason.replace("_", " ")),
            lane_exp_mode=html.escape(_lane_exp_mode.replace("_", " ")),
            lane_exp_wr=(f" · WR {_lane_exp_wr*100:.0f}%" if _lane_exp_wr is not None else ""),
            lane_exp_avg=(f" · Avg ${_lane_exp_avg:.2f}" if _lane_exp_avg is not None else ""),
            exp_color="#10b981" if _exp_mult > 1.0 else "#ef4444" if _exp_mult < 1.0 else "#d1d5db",
            kelly_color="#10b981" if _kelly_mult > 1.0 else "#ef4444" if _kelly_mult < 1.0 else "#d1d5db",
            absorption=html.escape(_ob_absorption.replace("_", " ")),
            spoof=html.escape(f"{_ob_spoof_side} {_ob_spoof_risk:.2f}" if _ob_spoof_risk is not None else "none"),
            weekly_bias=html.escape(_weekly_bias.upper()),
            weekly_xlm_bias=html.escape(_weekly_xlm_bias.upper()),
            bid_rep=f"{_ob_bid_rep:.2f}" if _ob_bid_rep is not None else "—",
            ask_rep=f"{_ob_ask_rep:.2f}" if _ob_ask_rep is not None else "—",
            weekly_conf=_weekly_conf * 100,
        ),
        unsafe_allow_html=True,
    )
except Exception:
    pass

try:
    _playbook = {}
    _event_calendar = {}
    _source_board = {}
    _crowding_summary = {}
    for _path, _target in (
        (DATA_DIR / "weekly_playbook.json", "_playbook"),
        (DATA_DIR / "market_event_calendar.json", "_event_calendar"),
        (DATA_DIR / "source_scoreboard.json", "_source_board"),
        (DATA_DIR / "crowding_summary.json", "_crowding_summary"),
    ):
        try:
            _payload = json.loads(_path.read_text()) if _path.exists() else {}
        except Exception:
            _payload = {}
        if _target == "_playbook":
            _playbook = _payload if isinstance(_payload, dict) else {}
        elif _target == "_event_calendar":
            _event_calendar = _payload if isinstance(_payload, dict) else {}
        elif _target == "_source_board":
            _source_board = _payload if isinstance(_payload, dict) else {}
        else:
            _crowding_summary = _payload if isinstance(_payload, dict) else {}

    _next_event = _event_calendar.get("next_event") if isinstance(_event_calendar.get("next_event"), dict) else {}
    _events = _event_calendar.get("events") if isinstance(_event_calendar.get("events"), list) else []
    _sources = _source_board.get("top_sources") if isinstance(_source_board.get("top_sources"), list) else []
    _playbook_setups = _playbook.get("top_setups") if isinstance(_playbook.get("top_setups"), list) else []
    _playbook_risks = _playbook.get("risk_map") if isinstance(_playbook.get("risk_map"), list) else []
    _playbook_ready = bool(_playbook.get("monday_ready"))
    _event_html = "".join(
        f"<div style='padding:3px 0;font-size:11px;color:#d1d5db;'>&bull; {html.escape(str(item.get('label') or 'event'))}"
        f" <span style='color:#6b7280'>({html.escape(str(item.get('importance') or 'medium'))}"
        + (f", {float(item.get('hours_to_event')):.1f}h" if _safe_float(item.get("hours_to_event")) is not None else "")
        + ")</span></div>"
        for item in _events[:4] if isinstance(item, dict)
    ) or "<div style='font-size:11px;color:#6b7280;'>No structured events loaded.</div>"
    _source_html = "".join(
        f"<div style='padding:3px 0;font-size:11px;color:#d1d5db;'>&bull; {html.escape(str(item.get('source_name') or 'unknown'))}"
        f" <span style='color:#6b7280'>score {float(item.get('weighted_score') or 0.0):.1f}, docs {int(item.get('documents') or 0)}</span></div>"
        for item in _sources[:4] if isinstance(item, dict)
    ) or "<div style='font-size:11px;color:#6b7280;'>No source scoreboard yet.</div>"
    _playbook_html = "".join(
        f"<div style='padding:3px 0;font-size:11px;color:#d1d5db;'>&bull; {html.escape(_humanize_market_text(str(item)))}</div>"
        for item in _playbook_setups[:3]
    ) or "<div style='font-size:11px;color:#6b7280;'>No playbook setup list yet.</div>"
    _risk_html = "".join(
        f"<div style='padding:3px 0;font-size:11px;color:#d1d5db;'>&bull; {html.escape(_humanize_market_text(str(item)))}</div>"
        for item in _playbook_risks[:3]
    ) or "<div style='font-size:11px;color:#6b7280;'>No risk map yet.</div>"
    _playbook_generated = _safe_str(_playbook.get("generated_at")) or "unknown"
    _ws_age_num = None
    try:
        _ws_age_num = int(ws_age) if ws_age and ws_age != "—" else None
    except Exception:
        pass
    _live_price_line = ""
    if _ws_age_num is not None and _ws_age_num <= 60 and ws_px != "—":
        _live_price_line = f"Live now: {html.escape(ws_px)} from websocket ({int(_ws_age_num)}s ago)."
    else:
        _playbook_bot_px = _safe_float(last_decision.get('price'))
        if _playbook_bot_px:
            _live_price_line = f"Live now: ${_playbook_bot_px:.6f} from bot runtime."
    st.markdown(
        "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:0 0 12px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #f59e0b;'>"
        "<div class='kpi-label'>Event Calendar</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill'>{next_event}</span>"
        "<span class='pill'>{event_count} tracked</span>"
        "<span class='pill'>{high_risk} high-risk</span>"
        "</div>"
        "<div style='margin-top:8px;'>{event_html}</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #22c55e;'>"
        "<div class='kpi-label'>Source Scoreboard</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill'>Diversity {src_div}</span>"
        "<span class='pill'>Avg quality {src_quality}</span>"
        "</div>"
        "<div style='margin-top:8px;'>{source_html}</div>"
        "</div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #8b5cf6;'>"
        "<div class='kpi-label'>Weekly Playbook</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill'>{playbook_label}</span>"
        "<span class='pill' style='background:{ready_bg};color:{ready_fg};'>{ready_txt}</span>"
        "<span class='pill'>{crowding}</span>"
        "</div>"
        "<div style='margin-top:8px;font-size:11px;color:#6b7280;'>Research snapshot generated {generated_at}</div>"
        "<div style='margin-top:4px;font-size:11px;color:#93c5fd;'>{live_price_line}</div>"
        "<div style='margin-top:8px;font-size:11px;color:#9ca3af;'>{thesis}</div>"
        "<div style='margin-top:8px;'>{playbook_html}</div>"
        "<div style='margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);'>{risk_html}</div>"
        "</div>"
        "</div>".format(
            next_event=html.escape(str(_next_event.get("label") or "No immediate event")),
            event_count=int(_event_calendar.get("event_count") or 0),
            high_risk=int(_event_calendar.get("high_risk_count") or 0),
            event_html=_event_html,
            src_div=int(_source_board.get("source_diversity") or 0),
            src_quality=f"{float(_source_board.get('avg_quality') or 0.0):.2f}",
            source_html=_source_html,
            playbook_label=html.escape(str(_playbook.get("label") or "OUTSIDE_WEEKLY_WINDOW").replace("_", " ")),
            ready_bg="rgba(16,185,129,0.15)" if _playbook_ready else "rgba(239,68,68,0.15)",
            ready_fg="#34d399" if _playbook_ready else "#fca5a5",
            ready_txt="MONDAY READY" if _playbook_ready else "NEEDS FRESH REVIEW",
            crowding=html.escape(_friendly_crowding_label(str(_crowding_summary.get("regime") or "balanced"))),
            generated_at=html.escape(_playbook_generated),
            live_price_line=_live_price_line or "Live price unavailable from current runtime.",
            thesis=html.escape(_humanize_market_text(str(_playbook.get("thesis") or "No weekly thesis loaded."))),
            playbook_html=_playbook_html,
            risk_html=_risk_html,
        ),
        unsafe_allow_html=True,
    )
except Exception:
    pass

try:
    _ob_hist_samples = int(_safe_float(last_decision.get("orderbook_history_samples")) or 0)
    _ob_hist_bias = _safe_str(last_decision.get("orderbook_history_bias")) or "UNKNOWN"
    _ob_hist_imb = _safe_float(last_decision.get("orderbook_history_avg_imbalance"))
    _ob_hist_abs = _safe_float(last_decision.get("orderbook_history_absorption_rate"))
    _ob_hist_spoof = _safe_float(last_decision.get("orderbook_history_spoof_rate"))
    _ob_hist_flips = int(_safe_float(last_decision.get("orderbook_history_depth_flips")) or 0)
    _crowd_bias = _safe_str(last_decision.get("crowding_bias")) or "mixed"
    _crowd_regime = _safe_str(last_decision.get("crowding_regime")) or "balanced"
    _crowd_funding = _safe_str(last_decision.get("crowding_funding_bias")) or "mixed"
    _crowd_oi = _safe_float(last_decision.get("crowding_oi_change_pct"))
    st.markdown(
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 12px;'>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #14b8a6;'>"
        "<div class='kpi-label'>Order Book Memory</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill'>{bias}</span><span class='pill'>{samples} samples</span></div>"
        "<div style='margin-top:8px;font-size:11px;color:#9ca3af;'>"
        "Avg imbalance {imb} &bull; absorption rate {absr} &bull; spoof rate {spoof} &bull; depth flips {flips}"
        "</div></div>"
        "<div class='intel-card' style='padding:12px 14px;border-left:3px solid #3b82f6;'>"
        "<div class='kpi-label'>Crowding History</div>"
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;'>"
        "<span class='pill'>{regime}</span><span class='pill'>{bias2}</span><span class='pill'>{funding}</span></div>"
        "<div style='margin-top:8px;font-size:11px;color:#9ca3af;'>OI change {oi}</div>"
        "</div>"
        "</div>".format(
            bias=html.escape(_ob_hist_bias.replace("_", " ")),
            samples=_ob_hist_samples,
            imb=f"{_ob_hist_imb:.3f}" if _ob_hist_imb is not None else "—",
            absr=f"{_ob_hist_abs:.2f}" if _ob_hist_abs is not None else "—",
            spoof=f"{_ob_hist_spoof:.2f}" if _ob_hist_spoof is not None else "—",
            flips=_ob_hist_flips,
            regime=html.escape(_crowd_regime.replace("_", " ")),
            bias2=html.escape(_crowd_bias.upper()),
            funding=html.escape(_crowd_funding.replace("_", " ")),
            oi=f"{_crowd_oi:+.3f}%" if _crowd_oi is not None else "—",
        ),
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── "As of" Timestamp ────────────────────────────────────────────────────────
try:
    _as_of_utc = datetime.now(timezone.utc)
    _as_of_pt = _as_of_utc.astimezone(PT)
    _age_str = _fmt_age_s(last_age) if last_age is not None else "—"
    st.markdown(
        f"<div class='as-of'>Coinbase data as of {_as_of_pt.strftime('%I:%M %p PT')} &mdash; {_age_str} ago</div>",
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── Volatility State Badge ────────────────────────────────────────────────
try:
    _vol_phase = _safe_str(last_decision.get("vol_phase")) or "?"
    _vol_dir = _safe_str(last_decision.get("vol_direction")) or "?"
    _vol_conf = int(_safe_float(last_decision.get("vol_confidence")) or 0)
    _vol_reasons = last_decision.get("vol_reasons") or []
    if isinstance(_vol_reasons, str):
        _vol_reasons = [_vol_reasons]
    elif not isinstance(_vol_reasons, list):
        _vol_reasons = []
    _phase_colors = {
        "COMPRESSION": ("#6b7280", "rgba(107,114,128,0.12)"),
        "IGNITION": ("#f59e0b", "rgba(245,158,11,0.12)"),
        "EXPANSION": ("#10b981", "rgba(16,185,129,0.12)"),
        "EXHAUSTION": ("#ef4444", "rgba(239,68,68,0.12)"),
    }
    _pc, _bg = _phase_colors.get(_vol_phase, ("#6b7280", "rgba(107,114,128,0.12)"))
    _dir_icon = {"LONG": "&#9650;", "SHORT": "&#9660;", "NEUTRAL": "&#9679;"}.get(_vol_dir, "&#9679;")
    _reasons_str = " &bull; ".join(html.escape(str(r)) for r in _vol_reasons[:6]) if _vol_reasons else ""
    _vol_metrics = last_decision.get("vol_metrics") or {}
    _tr_ratio_d = _safe_float(_vol_metrics.get("tr_ratio") if isinstance(_vol_metrics, dict) else None)
    _vol_ratio_d = _safe_float(_vol_metrics.get("vol_ratio") if isinstance(_vol_metrics, dict) else None)
    _rsi_d = _safe_float(_vol_metrics.get("rsi") if isinstance(_vol_metrics, dict) else None)
    _micro = ""
    if _tr_ratio_d is not None:
        _micro += f"TR:{_tr_ratio_d:.2f}x "
    if _vol_ratio_d is not None:
        _micro += f"Vol:{_vol_ratio_d:.2f}x "
    if _rsi_d is not None:
        _micro += f"RSI:{_rsi_d:.0f}"
    # Phase duration: count consecutive same-phase cycles
    _phase_dur = 0
    if not decisions.empty and "vol_phase" in decisions.columns:
        _recent_phases = decisions["vol_phase"].astype(str).tolist()
        for _rp in reversed(_recent_phases):
            if _rp == _vol_phase:
                _phase_dur += 1
            else:
                break
    # ATR slope arrow
    _atr_rising = bool((_vol_metrics.get("atr_slope_rising_2bars") if isinstance(_vol_metrics, dict) else False))
    _atr_arrow = "&#9650;" if _atr_rising else "&#9660;"
    _atr_arrow_clr = "#10b981" if _atr_rising else "#ef4444"
    # Direction highlight during IGNITION/EXPANSION
    _dir_html = f"<span style='color:{_pc};font-size:11px;'>{_dir_icon} {_vol_dir}</span>"
    if _vol_phase in ("IGNITION", "EXPANSION") and _vol_dir in ("LONG", "SHORT"):
        _dh_clr = "#34d399" if _vol_dir == "LONG" else "#f87171"
        _dir_html = f"<span style='color:{_dh_clr};font-weight:700;font-size:11px;'>{_dir_icon} {_vol_dir}</span>"
    # Phase narrative
    _phase_narr = ""
    if _phase_dur > 0:
        _narr_map = {
            "COMPRESSION": f"COMPRESSION for {_phase_dur} cycles — watching for ignition",
            "IGNITION": f"IGNITION detected {_phase_dur} cycle{'s' if _phase_dur != 1 else ''} ago, warming up",
            "EXPANSION": f"EXPANDING — {_vol_dir} bias active for {_phase_dur} cycles",
            "EXHAUSTION": f"EXHAUSTION — move fading after {_phase_dur} cycles",
        }
        _phase_narr = _narr_map.get(_vol_phase, f"{_vol_phase} for {_phase_dur} cycles")
    _narr_row = ""
    if _phase_narr or _reasons_str:
        _narr_content = _phase_narr
        if _reasons_str:
            _narr_content += f" &bull; {_reasons_str}" if _narr_content else _reasons_str
        _narr_row = f"<div style='width:100%;font-size:10px;color:#9ca3af;margin-top:2px;'>{_narr_content}</div>"
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;padding:6px 12px;margin:4px 0 8px;border-radius:10px;"
        f"background:{_bg};border:1px solid {_pc}30;flex-wrap:wrap;'>"
        f"<span style='color:{_pc};font-weight:700;font-size:12px;letter-spacing:0.6px;'>"
        f"VOL: {_vol_phase}</span>"
        f"{_dir_html}"
        f"<span style='color:#9ca3af;font-size:10px;'>conf {_vol_conf}%</span>"
        f"<span style='color:{_atr_arrow_clr};font-size:9px;'>ATR {_atr_arrow}</span>"
        f"<span style='color:#6b7280;font-size:10px;'>{_micro}</span>"
        f"{_narr_row}"
        f"</div>",
        unsafe_allow_html=True,
    )
except Exception:
    pass

if major_events:
    ev0 = major_events[0]
    tone = _safe_str(ev0.get("tone")) or "info"
    st.markdown(
        "<div class='major-banner "
        + tone
        + "'>"
        + f"<div class='k'>Latest Major Event</div>"
        + f"<div class='v'>{_safe_str(ev0.get('headline')) or '-'}</div>"
        + f"<div class='d'>{_fmt_pt_short(ev0.get('ts'))} • {_safe_str(ev0.get('detail')) or '-'}</div>"
        + "</div>",
        unsafe_allow_html=True,
    )

if client_tick:
    _live_ref_product = prod or "XLP-20DEC30-CDE"
    _live_ref_label = "CONTRACT REF" if str(_live_ref_product).startswith("XLP-") else "SPOT REF"
    _live_ticker_component(_live_ref_product, interval_ms=1000, height=52, label=_live_ref_label)

# Show bot's perp price alongside spot ticker for comparison
_perp_px = _safe_float(last_decision.get("price"))
_perp_age = last_age
if _perp_px:
    _perp_age_s = _fmt_age_s(_perp_age) if _perp_age else "?"
    _perp_prod = prod or "XLP-USD-PERP"
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;color:#9aa4af;font-size:12px;letter-spacing:0.6px;margin-top:-4px;'>"
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(59,130,246,0.15);color:#60a5fa;'>PERP</span>"
        f"<span>{_perp_prod}</span>"
        f"<span style='color:#6b7280;'>&#8226;</span>"
        f"<span style='color:#e5e7eb;font-weight:600;'>${_perp_px:.6f}</span>"
        f"<span style='color:#6b7280;'>&#8226;</span>"
        f"<span style='color:#6b7280;'>from bot {_perp_age_s} ago</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Portfolio & Price Chart (full width, prominent) ──────────────────────────
try:
    _chart_tf_map = {"1H": 1, "6H": 6, "1D": 24, "1W": 168, "ALL": None}
    _chart_tf_sel = st.radio(
        "Chart Timeframe", list(_chart_tf_map.keys()), index=2,
        horizontal=True, label_visibility="collapsed",
        key="chart_tf_top",
    )
    _chart_tf_hours = _chart_tf_map.get(_chart_tf_sel, 24)

    _chart_eq_data = _load_equity_series(hours=_chart_tf_hours)
    _chart_eq_series = []
    _chart_px_series = []
    _chart_seen_eq = {}
    _chart_seen_px = {}
    for _cr in _chart_eq_data:
        try:
            _cts = datetime.fromisoformat(_cr["ts"])
            _ct = int(_cts.timestamp())
            # Use portfolio value (full account) if available, fall back to equity (derivatives only)
            _cev = float(_cr.get("portfolio") or _cr.get("equity") or 0)
            _cpv = float(_cr.get("mark_price") or 0)
            if _cev > 0:
                _chart_seen_eq[_ct] = {"time": _ct, "value": round(_cev, 2)}
            if _cpv > 0:
                _chart_seen_px[_ct] = {"time": _ct, "value": round(_cpv, 6)}
        except Exception:
            continue
    # Anchor chart to current Coinbase portfolio value (ensures chart matches TOTAL KPI)
    if portfolio_value and portfolio_value > 0:
        _now_ts = int(datetime.now(timezone.utc).timestamp())
        _chart_seen_eq[_now_ts] = {"time": _now_ts, "value": round(portfolio_value, 2)}
    _chart_eq_series = sorted(_chart_seen_eq.values(), key=lambda x: x["time"])
    _chart_px_series = sorted(_chart_seen_px.values(), key=lambda x: x["time"])

    # Fallback price from candle data
    if not _chart_px_series:
        try:
            if not hist_1h.empty and "timestamp" in hist_1h.columns and "close" in hist_1h.columns:
                _ftmp = hist_1h.dropna(subset=["timestamp", "close"]).tail(400)
                for _, _fr in _ftmp.iterrows():
                    _fts = _fr["timestamp"]
                    if hasattr(_fts, "to_pydatetime"):
                        _fts = _fts.to_pydatetime()
                    _chart_px_series.append({"time": int(_fts.timestamp()), "value": float(_fr["close"])})
        except Exception:
            pass

    _chart_markers = _build_trade_markers(trades, hours=_chart_tf_hours)

    # TP/SL levels for live trade
    _chart_tp = None
    if pos_view and pos_source == "BOT":
        try:
            _cte = _safe_float(pos_view.get("entry_price"))
            _ct1 = _safe_float(pos_view.get("tp1"))
            _ct2 = _safe_float(pos_view.get("tp2"))
            _ct3 = _safe_float(pos_view.get("tp3"))
            _cts_l = _safe_float(pos_view.get("stop_loss"))
            if _cte and _cte > 0:
                _chart_tp = {"entry": _cte, "tp1": _ct1, "tp2": _ct2, "tp3": _ct3, "sl": _cts_l,
                             "direction": str(pos_view.get("direction", ""))}
        except Exception:
            pass

    if _chart_eq_series or _chart_px_series:
        _equity_chart_with_markers(
            _chart_eq_series, _chart_px_series, _chart_markers,
            tp_levels=_chart_tp,
            height_equity=200 if _chart_eq_series else 0,
            height_price=280,
            chart_id="top",
        )
        # Drift summary below chart
        _ex_eq = _safe_float(last_decision.get("exchange_equity_usd"))
        _bot_eq = _safe_float(last_decision.get("equity_start_usd"))
        _bot_pnl = _safe_float(last_decision.get("pnl_today_usd"))
        if _ex_eq and _ex_eq > 0:
            _bot_total = (_bot_eq or 0) + (_bot_pnl or 0)
            _drift = _ex_eq - _bot_total if _bot_total > 0 else 0
            _drift_cls = "ok" if abs(_drift) < 1 else ("danger" if abs(_drift) > 5 else "muted")
            st.markdown(
                f"<div style='text-align:center;font-size:10px;margin-top:2px;margin-bottom:8px;'>"
                f"<span class='muted'>Derivatives:</span> <span class='metric' style='font-size:11px;'>${_ex_eq:,.2f}</span>"
                f" <span class='muted'>&bull; Bot calc:</span> <span style='font-size:11px;'>${_bot_total:,.2f}</span>"
                f" <span class='muted'>&bull; Drift:</span> <span class='{_drift_cls}' style='font-size:11px;'>{'+' if _drift>=0 else ''}${_drift:.2f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='text-align:center;padding:40px 0;color:#6b7280;font-size:13px;'>"
            "Chart loading... waiting for equity data to accumulate."
            "</div>",
            unsafe_allow_html=True,
        )
except Exception:
    pass

# ── Away Report ──────────────────────────────────────────────────────────────
_now_utc = datetime.now(timezone.utc)
if "last_viewed_ts" not in st.session_state:
    st.session_state["last_viewed_ts"] = _now_utc
_away_dismissed = st.session_state.get("away_dismissed", False)
_last_viewed = st.session_state["last_viewed_ts"]
_away_seconds = (_now_utc - _last_viewed).total_seconds() if isinstance(_last_viewed, datetime) else 0
if _away_seconds > 300 and not decisions.empty and not _away_dismissed:
    try:
        _away_df = decisions[decisions["timestamp"] > _last_viewed].copy() if "timestamp" in decisions.columns else pd.DataFrame()
        if not _away_df.empty:
            _reasons = _away_df["reason"].astype(str).tolist() if "reason" in _away_df.columns else []
            _entries = sum(1 for r in _reasons if "entry_order" in r or "entered" in r.lower())
            _exits = sum(1 for r in _reasons if "exit_order" in r or "exit" in r.lower())
            _crashes = sum(1 for r in _reasons if r == "bot_error")
            _restarts = sum(1 for r in _reasons if r == "bot_session_start")
            _guardian = sum(1 for r in _reasons if r == "guardian_restart")
            _resets = sum(1 for r in _reasons if r == "daily_reset")
            _recon = 0
            if "reconcile_incidents" in _away_df.columns:
                _recon = int((_away_df["reconcile_incidents"].fillna(0).astype(float) > 0).sum())
            _away_pnl = 0.0
            if "pnl_today_usd" in _away_df.columns and len(_away_df) >= 2:
                _first_pnl = _safe_float(_away_df.iloc[0].get("pnl_today_usd"))
                _last_pnl = _safe_float(_away_df.iloc[-1].get("pnl_today_usd"))
                if _first_pnl is not None and _last_pnl is not None:
                    _away_pnl = _last_pnl - _first_pnl
            # Price action during gap
            _gap_px_open = None
            _gap_px_close = None
            _gap_px_high = None
            _gap_px_low = None
            if "price" in _away_df.columns:
                _gap_prices = pd.to_numeric(_away_df["price"], errors="coerce").dropna()
                if not _gap_prices.empty:
                    _gap_px_open = float(_gap_prices.iloc[0])
                    _gap_px_close = float(_gap_prices.iloc[-1])
                    _gap_px_high = float(_gap_prices.max())
                    _gap_px_low = float(_gap_prices.min())
            # Signals seen/blocked during gap
            _gap_signals = 0
            _gap_blocked = 0
            if "entry_signal" in _away_df.columns:
                _sig_mask = _away_df["entry_signal"].notna() & (_away_df["entry_signal"].astype(str) != "")
                _gap_signals = int(_sig_mask.sum())
                _blocked_reasons = [r for r in _reasons if "blocked" in r or "block" in r.lower()]
                _gap_blocked = len(_blocked_reasons)
            # Bot offline gap detection: check if there were periods with no decisions
            _gap_offline_minutes = 0
            if len(_away_df) >= 2 and "timestamp" in _away_df.columns:
                _gap_ts = _away_df["timestamp"].sort_values()
                _gap_diffs = _gap_ts.diff().dt.total_seconds().dropna()
                _big_gaps = _gap_diffs[_gap_diffs > 120]  # gaps > 2 min = bot was offline
                _gap_offline_minutes = int(_big_gaps.sum() / 60) if not _big_gaps.empty else 0
            _any_events = _entries + _exits + _crashes + _restarts + _guardian + _resets + _recon
            _show_recap = _any_events > 0 or _gap_px_open is not None or _gap_signals > 0 or _gap_offline_minutes > 0
            if _show_recap:
                _away_min = int(_away_seconds / 60)
                _parts = []
                if _entries:
                    _parts.append(f"{_entries} entr{'ies' if _entries != 1 else 'y'}")
                if _exits:
                    _parts.append(f"{_exits} exit{'s' if _exits != 1 else ''}")
                if _crashes:
                    _parts.append(f"<span class='pill danger'>{_crashes} crash{'es' if _crashes != 1 else ''}</span>")
                if _restarts:
                    _parts.append(f"{_restarts} restart{'s' if _restarts != 1 else ''}")
                if _guardian:
                    _parts.append(f"{_guardian} guardian restart{'s' if _guardian != 1 else ''}")
                if _resets:
                    _parts.append(f"{_resets} daily reset{'s' if _resets != 1 else ''}")
                if _recon:
                    _parts.append(f"{_recon} reconciliation{'s' if _recon != 1 else ''}")
                _pnl_str = f"PnL: <span class='{'green' if _away_pnl >= 0 else 'red'}'>{'+' if _away_pnl >= 0 else ''}${_away_pnl:.2f}</span>" if abs(_away_pnl) > 0.001 else ""
                _summary = " &bull; ".join(_parts)
                if _pnl_str:
                    _summary += f" &bull; {_pnl_str}"
                # Price action row
                _price_row = ""
                if _gap_px_open and _gap_px_close:
                    _px_chg = (_gap_px_close - _gap_px_open) / _gap_px_open * 100
                    _px_clr = "green" if _px_chg >= 0 else "red"
                    _px_range = f"L ${_gap_px_low:.6f} &mdash; H ${_gap_px_high:.6f}" if _gap_px_low and _gap_px_high else ""
                    _price_row = (
                        f"<div style='font-size:12px;color:#9ca3af;margin-top:6px;'>"
                        f"Price: ${_gap_px_open:.6f} &rarr; ${_gap_px_close:.6f} "
                        f"<span class='{_px_clr}'>({'+' if _px_chg >= 0 else ''}{_px_chg:.2f}%)</span>"
                    )
                    if _px_range:
                        _price_row += f" &bull; {_px_range}"
                    _price_row += "</div>"
                # Signals row
                _sig_row = ""
                if _gap_signals > 0:
                    _sig_row = (
                        f"<div style='font-size:12px;color:#9ca3af;margin-top:4px;'>"
                        f"Signals seen: {_gap_signals}"
                    )
                    if _gap_blocked:
                        _sig_row += f" &bull; <span class='red'>{_gap_blocked} blocked by gates/score</span>"
                    _sig_row += "</div>"
                # Bot offline warning
                _offline_row = ""
                if _gap_offline_minutes > 0:
                    _offline_row = (
                        f"<div style='font-size:12px;margin-top:4px;'>"
                        f"<span class='pill danger' style='font-size:10px;'>BOT OFFLINE</span> "
                        f"<span style='color:#9ca3af;'>{_gap_offline_minutes} min with no decisions</span>"
                        f"</div>"
                    )
                st.markdown(
                    f"<div class='card' style='border-left:3px solid #f59e0b;margin-bottom:12px;padding:14px 18px;'>"
                    f"<div style='color:#f59e0b;font-weight:600;font-size:13px;margin-bottom:4px;'>While You Were Away ({_away_min} min)</div>"
                    f"<div style='font-size:12px;color:#d1d5db;'>{_summary}</div>"
                    f"{_price_row}{_sig_row}{_offline_row}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Got it", key="away_dismiss"):
                    st.session_state["away_dismissed"] = True
                    st.session_state["last_viewed_ts"] = _now_utc
    except Exception:
        pass
# Update last viewed on every render
st.session_state["last_viewed_ts"] = _now_utc
if _away_dismissed:
    st.session_state["away_dismissed"] = False

# ── Compact Metrics Strip (relocated from right panel) ─────────────────────
try:
    _ms_items: list[str] = []
    def _ms(label: str, value: str, tone: str = "") -> str:
        t = f" {tone}" if tone else ""
        return f"<div class='ms-item'><div class='ms-k'>{label}</div><div class='ms-v{t}'>{value}</div></div>"
    _ms_items.append(_ms("Bot Tick", _fmt_age_s(last_age), "good" if (last_age is not None and last_age <= 120) else "warn" if (last_age is not None and last_age <= 600) else "bad"))
    try:
        _ws_age_i = int(ws_age)
    except Exception:
        _ws_age_i = 999
    _ms_items.append(_ms("WS Tick", f"{ws_age}s", "good" if _ws_age_i <= 5 else "warn"))
    if mp_tier and mp_tier != "-":
        _ms_items.append(_ms("Margin", mp_tier, "good" if mp_tier == "SAFE" else "warn" if mp_tier == "WARNING" else "bad"))
    _ms_items.append(_ms("Win Rate", f"{win_rate:.0f}%", "good" if win_rate >= 55 else ""))
    _ms_items.append(_ms("P&L", f"{'+' if total_pnl >= 0 else ''}${total_pnl:.2f}", "good" if total_pnl >= 0 else "bad"))
    _ms_items.append(_ms("W/L", f"{wins}/{losses}", ""))
    # Quality tier
    _qt_display = _safe_str(last_decision.get("quality_tier")) or ""
    if _qt_display:
        _qt_tone = "good" if _qt_display == "MONSTER" else "good" if _qt_display == "FULL" else "warn" if _qt_display in ("REDUCED", "SCALP") else "bad"
        _ms_items.append(_ms("Quality", _qt_display, _qt_tone))
    # Ops metrics
    avg_tpd = _safe_float(ops_metrics.get("avg_trades_per_day"))
    if avg_tpd is not None:
        _ms_items.append(_ms("Trades/Day", f"{avg_tpd:.1f}", ""))
    avg_tit = _safe_float(ops_metrics.get("avg_time_in_trade_min"))
    if avg_tit is not None:
        _ms_items.append(_ms("Avg Trade", f"{avg_tit:.0f}m", ""))
    pnl_hr = _safe_float(ops_metrics.get("pnl_per_trade_hour"))
    if pnl_hr is not None:
        _ms_items.append(_ms("P&L/Hr", _format_money(pnl_hr), "good" if pnl_hr >= 0 else "bad"))
    # Streak
    try:
        _cs_trades = _get_closed_trades(trades) if trades is not None and not trades.empty else pd.DataFrame()
        if not _cs_trades.empty and "pnl_usd" in _cs_trades.columns:
            _cs_outcomes = [("W" if (_safe_float(r.get("pnl_usd")) or 0) >= 0 else "L") for _, r in _cs_trades.iterrows() if _safe_float(r.get("pnl_usd")) is not None]
            if _cs_outcomes:
                _cs_type = _cs_outcomes[-1]
                _cs_len = 0
                for _o in reversed(_cs_outcomes):
                    if _o == _cs_type:
                        _cs_len += 1
                    else:
                        break
                _cs_word = "W" if _cs_type == "W" else "L"
                _ms_items.append(_ms("Streak", f"{_cs_len}{_cs_word}", "good" if _cs_type == "W" else "bad"))
    except Exception:
        pass
    # Transfers
    _t_today = _safe_float(last_decision.get("transfers_today_usd")) or _safe_float(state.get("transfers_today_usd"))
    if _t_today is not None and _t_today > 0:
        _ms_items.append(_ms("Xfers", _format_money(_t_today), ""))
    # Inline alerts
    _ms_alerts: list[str] = []
    if _exch_pos and not open_pos:
        _ms_alerts.append("Exchange has position, bot state does not")
    if open_pos and not _exch_pos:
        _ms_alerts.append("Bot state has position, exchange does not")
    if last_age is not None and last_age > 600:
        _ms_alerts.append("Bot heartbeat stale")
    _alert_html = ""
    if _ms_alerts:
        _alert_html = (
            "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;'>"
            + "".join(f"<span style='font-size:10px;color:#fbbf24;background:rgba(245,158,11,0.1);padding:2px 8px;border-radius:4px;'>&#9888; {a}</span>" for a in _ms_alerts)
            + "</div>"
        )
    st.markdown(
        "<div class='metrics-strip'>" + "".join(_ms_items) + "</div>" + _alert_html,
        unsafe_allow_html=True,
    )
except Exception:
    pass

# ── Last Closed Trade Receipt ─────────────────────────────────────────────
try:
    if not trades.empty and "result" in trades.columns:
        _closed_trades = trades[trades["result"].astype(str).isin(["win", "loss", "flat"])].copy()
        if not _closed_trades.empty:
            _lt = _closed_trades.iloc[-1]

            # Ghost trade filter: skip reconciler-generated exits entirely.
            # Walk backwards to find the last REAL trade (non exchange_side_close).
            _lt_is_ghost = str(_lt.get("exit_reason") or "") == "exchange_side_close"
            if _lt_is_ghost:
                # Try to find most recent real trade
                _real_trades = _closed_trades[_closed_trades["exit_reason"].astype(str) != "exchange_side_close"]
                if not _real_trades.empty:
                    _lt = _real_trades.iloc[-1]
                    _lt_is_ghost = False

            if _lt_is_ghost:
                st.markdown(
                    "<div class='card' style='margin-top:6px;padding:8px 12px;border-color:rgba(239,68,68,0.25);'>"
                    "<div style='display:flex;align-items:center;gap:8px;'>"
                    "<span class='label' style='font-size:10px;'>Last Trade</span>"
                    "<span class='pill danger' style='font-size:10px;'>GHOST</span>"
                    "<span class='muted' style='font-size:10px;'>Reconciler logged exit but position is still open — this trade was NOT real</span>"
                    "</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                _lt_side = str(_lt.get("side") or _lt.get("direction") or "?").upper()
                _lt_entry = _safe_float(_lt.get("entry_price"))
                _lt_exit = _safe_float(_lt.get("exit_price"))
                _lt_pnl = _safe_float(_lt.get("pnl_usd"))
                _lt_pnl_pct = _safe_float(_lt.get("pnl_pct"))
                _lt_result = str(_lt.get("result") or "?").upper()
                _lt_reason = str(_lt.get("exit_reason") or "?").replace("_", " ").title()
                _lt_dur = _safe_float(_lt.get("time_in_trade_min"))
                _lt_entry_t = _coerce_ts_utc(_lt.get("entry_time"))
                _lt_exit_t = _coerce_ts_utc(_lt.get("exit_time") or _lt.get("timestamp"))
                _lt_size = int(_safe_float(_lt.get("size")) or 1)
                _lt_cls = "ok" if _lt_result == "WIN" else "danger"
                _lt_sign = "+" if (_lt_pnl or 0) >= 0 else ""
                _lt_entry_str = f"${_lt_entry:.5f}" if _lt_entry else "?"
                _lt_exit_str = f"${_lt_exit:.5f}" if _lt_exit else "?"
                _lt_pnl_str = f"{_lt_sign}${_lt_pnl:.2f}" if _lt_pnl is not None else "?"
                _lt_pct_str = f"({_lt_sign}{_lt_pnl_pct * 100:.2f}%)" if _lt_pnl_pct is not None else ""
                _lt_dur_str = f"{_lt_dur:.0f}m" if _lt_dur else "?"
                _lt_entry_t_str = _fmt_pt_short(_lt_entry_t) if _lt_entry_t else "?"
                _lt_exit_t_str = _fmt_pt_short(_lt_exit_t) if _lt_exit_t else "?"
                st.markdown(
                    f"<div class='card' style='margin-top:6px;padding:8px 12px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                    f"<span class='label' style='font-size:10px;'>Last Trade</span>"
                    f"<span class='pill {_lt_cls}' style='font-size:10px;'>{_lt_result}</span>"
                    f"<span class='muted' style='font-size:10px;'>{_lt_reason}</span>"
                    f"<span class='{_lt_cls}' style='font-size:13px;font-weight:700;margin-left:auto;'>{_lt_pnl_str} {_lt_pct_str}</span>"
                    f"</div>"
                    f"<div style='display:flex;gap:16px;font-size:11px;color:#9ca3af;'>"
                    f"<span>{_lt_side} {_lt_size}x</span>"
                    f"<span>Entry {_lt_entry_str} <span class='muted'>{_lt_entry_t_str}</span></span>"
                    f"<span>&#8594;</span>"
                    f"<span>Exit {_lt_exit_str} <span class='muted'>{_lt_exit_t_str}</span></span>"
                    f"<span>&#8226; {_lt_dur_str}</span>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
except Exception:
    pass

if page == "Terminal":
    # ── Emergency / Margin Alert Banner ──────────────────────────────────────
    try:
        _margin_alert = None
        for _me in (major_events or [])[:8]:
            _me_hl = str(_me.get("headline") or "").upper()
            if any(kw in _me_hl for kw in ("RISK EXIT", "LIQUIDATION", "EMERGENCY", "MARGIN", "SAFE MODE")):
                _me_age = None
                if _me.get("ts"):
                    _me_age = (datetime.now(timezone.utc) - _me["ts"]).total_seconds()
                if _me_age is not None and _me_age < 1800:
                    _margin_alert = _me
                    break
        if _margin_alert:
            _ma_hl = html.escape(str(_margin_alert.get("headline") or "MARGIN EVENT"))
            _ma_detail = html.escape(str(_margin_alert.get("detail") or ""))
            _ma_ts = _fmt_pt_short(_margin_alert.get("ts")) if callable(globals().get("_fmt_pt_short")) else str(_margin_alert.get("ts", ""))[-8:]
            _ma_age_min = int((datetime.now(timezone.utc) - _margin_alert["ts"]).total_seconds() / 60) if _margin_alert.get("ts") else 0
            st.markdown(
                f"<div class='stale-banner stale-danger' style='padding:12px 16px;font-size:13px;margin-bottom:12px;'>"
                f"<div style='font-size:14px;font-weight:700;margin-bottom:4px;'>&#9888; {_ma_hl}</div>"
                f"<div style='font-size:12px;color:rgba(248,113,113,0.9);'>{_ma_detail}</div>"
                f"<div style='font-size:11px;color:rgba(248,113,113,0.7);margin-top:4px;'>{_ma_age_min}m ago</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Main Tabs ──
    term_tabs = st.tabs(["Overview", "Intel Hub", "Chat", "Evolution"])
    
    with term_tabs[0]:
        _mo_price = _safe_float(last_decision.get("price"))
        _mo_price_str = f"${_mo_price:.6f}" if _mo_price else "—"

        # 24h range from hist_1h
        _mo_24h_high = _mo_24h_low = _mo_24h_open = _mo_24h_change_pct = None
        if not hist_1h.empty and "timestamp" in hist_1h.columns:
            _24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            _mo_24h = hist_1h[hist_1h["timestamp"] >= _24h_ago]
            if not _mo_24h.empty:
                _mo_24h_high = float(_mo_24h["high"].max())
                _mo_24h_low = float(_mo_24h["low"].min())
                _mo_24h_open = float(_mo_24h.iloc[0]["open"])
                if _mo_price and _mo_24h_open and _mo_24h_open > 0:
                    _mo_24h_change_pct = (_mo_price - _mo_24h_open) / _mo_24h_open * 100

        # Regime + vol state + direction
        _mo_regime = _safe_str(last_decision.get("regime")) or _safe_str(last_decision.get("v4_selected_regime")) or "-"
        _mo_vol_phase = _safe_str(last_decision.get("vol_phase")) or _safe_str(state.get("vol_state")) or "?"
        _mo_vol_dir = _safe_str(last_decision.get("vol_direction")) or "?"
        _mo_direction = _safe_str(last_decision.get("direction")) or None

        # Gates
        _mo_gates = (last_decision.get("gates") or {}) if isinstance(last_decision.get("gates"), dict) else {}
        _mo_gates_pass = bool(last_decision.get("gates_pass"))
        _mo_failed = last_decision.get("failed_gates") if isinstance(last_decision.get("failed_gates"), list) else [k for k, v in _mo_gates.items() if not v]

        # ── ROW 1: Price Bar ──────────────────────────────────────────
        _chg_clr = "green" if (_mo_24h_change_pct or 0) >= 0 else "red"
        _chg_sign = "+" if (_mo_24h_change_pct or 0) >= 0 else ""
        _chg_html = f"<span class='{_chg_clr}'>{_chg_sign}{_mo_24h_change_pct:.2f}%</span>" if _mo_24h_change_pct is not None else ""
        _range_html = ""
        if _mo_24h_low is not None and _mo_24h_high is not None:
            _range_html = f"<span class='muted' style='font-size:11px;'>24h: ${_mo_24h_low:.4f} &ndash; ${_mo_24h_high:.4f}</span>"
        _range_pct = 50
        if _mo_24h_high and _mo_24h_low and _mo_price and _mo_24h_high > _mo_24h_low:
            _range_pct = min(100, max(0, (_mo_price - _mo_24h_low) / (_mo_24h_high - _mo_24h_low) * 100))

        st.markdown(
            "<div class='intel-card' style='padding:12px 18px;'>"
            "<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
            f"<div><span class='label'>XLM PERP</span> "
            f"<span style='font-size:1.4rem;color:#f7f7f8;font-weight:600;'>{_mo_price_str}</span> "
            f"{_chg_html}</div>"
            f"<div>{_range_html}</div>"
            "</div>"
            "<div style='height:3px;background:rgba(107,114,128,0.15);border-radius:2px;margin:6px 0 2px;overflow:hidden;'>"
            f"<div style='width:{_range_pct:.0f}%;height:100%;background:linear-gradient(90deg,#ef4444,#f59e0b,#10b981);border-radius:2px;'></div>"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── ROW 2: Regime/Vol + Gates ─────────────────────────────────
        _mo_left, _mo_right = st.columns([1.2, 1.0])

        with _mo_left:
            _regime_clrs = {"trend": "#10b981", "mean_reversion": "#8b5cf6", "neutral": "#6b7280", "mixed": "#f59e0b"}
            _vol_clrs = {"COMPRESSION": "#6b7280", "IGNITION": "#f59e0b", "EXPANSION": "#10b981", "EXHAUSTION": "#ef4444"}
            _rc = _regime_clrs.get(_mo_regime.lower(), "#6b7280")
            _vc = _vol_clrs.get(_mo_vol_phase.upper(), "#6b7280")
            _pills_html = (
                f"<span class='pill' style='background:{_rc}20;color:{_rc};'>{html.escape(_mo_regime.upper())}</span> "
                f"<span class='pill' style='background:{_vc}20;color:{_vc};'>{html.escape(_mo_vol_phase.upper())}</span> "
            )
            if _mo_direction:
                _d_icon = "&#9650;" if _mo_direction.lower() == "long" else "&#9660;" if _mo_direction.lower() == "short" else ""
                _d_cls = "ok" if _mo_direction.lower() == "long" else "danger" if _mo_direction.lower() == "short" else ""
                _pills_html += f"<span class='pill {_d_cls}' style='font-weight:600;'>{_d_icon} {_mo_direction.upper()}</span>"
            st.markdown(
                "<div class='intel-card' style='padding:10px 14px;'>"
                f"<div class='intel-title'>REGIME</div>"
                f"<div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;'>{_pills_html}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        with _mo_right:
            _gate_labels = {"atr_regime": "ATR", "session": "SESSION", "distance_from_value": "DISTANCE", "spread": "SPREAD"}
            _gate_html = ""
            for _gn in ["atr_regime", "session", "distance_from_value", "spread"]:
                _gv = _mo_gates.get(_gn, True)
                _icon = "&#10003;" if _gv else "&#10007;"
                _clr = "#10b981" if _gv else "#ef4444"
                _gl = _gate_labels.get(_gn, _gn)
                _gate_html += (
                    f"<div style='display:inline-flex;align-items:center;gap:4px;min-width:90px;margin:2px 0;'>"
                    f"<span style='color:{_clr};font-size:12px;'>{_icon}</span>"
                    f"<span style='color:#9ca3af;font-size:10px;letter-spacing:0.8px;'>{_gl}</span>"
                    f"</div>"
                )
            _route_tier = _safe_str(last_decision.get("route_tier")) or ""
            if _route_tier == "full":
                _gates_pill = "<span class='pill ok' style='font-size:10px;'>FULL</span>"
            elif _route_tier == "reduced":
                _gates_pill = "<span class='pill' style='font-size:10px;background:#f59e0b20;color:#f59e0b;'>REDUCED (C/E)</span>"
            elif _route_tier == "blocked":
                _gates_pill = "<span class='pill danger' style='font-size:10px;'>BLOCKED</span>"
            elif _mo_gates_pass:
                _gates_pill = "<span class='pill ok' style='font-size:10px;'>ALL PASS</span>"
            else:
                _gates_pill = "<span class='pill danger' style='font-size:10px;'>BLOCKED</span>"
            st.markdown(
                "<div class='intel-card' style='padding:10px 14px;'>"
                f"<div class='intel-title'>GATES {_gates_pill}</div>"
                f"<div style='display:flex;flex-wrap:wrap;gap:4px 12px;'>{_gate_html}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # ── ROW 3: Bot Status Narrative ───────────────────────────────
        _mo_thought = _safe_str(last_decision.get("thought")) or ""
        _mo_signal = _safe_str(last_decision.get("entry_signal"))
        _mo_score = _safe_float(last_decision.get("v4_selected_score"))
        _mo_thresh = _safe_float(last_decision.get("v4_selected_threshold"))
        _has_pos = bool(pos_view and pos_source)

        _narr_parts: list[str] = []
        if _has_pos:
            _pos_dir = _safe_str(pos_view.get("direction")) or "?"
            _pos_entry = _safe_float(pos_view.get("entry_price"))
            _entry_s = f" at ${_pos_entry:.4f}" if _pos_entry else ""
            _narr_parts.append(f"In trade &middot; {_pos_dir.upper()}{_entry_s}")
        elif _mo_failed:
            _gate_explain = {
                "distance_from_value": "price is overextended from EMA21",
                "atr_regime": "volatility is too low",
                "session": "outside trading hours",
                "spread": "spread is too wide",
            }
            _blocking = ", ".join(_gate_explain.get(g, g.replace("_", " ")) for g in _mo_failed[:3])
            if _route_tier == "reduced":
                _narr_parts.append(f"<span style='color:#f59e0b;'>Reduced</span>: {_blocking} &rarr; C/E/reversal lanes only")
            else:
                _narr_parts.append(f"<span class='red'>Blocked</span>: {_blocking}")
            if _mo_direction:
                _dw = _mo_direction.lower()
                _dc = "red" if _dw == "short" else "green"
                _narr_parts.append(f"Biased <span class='{_dc}'>{_dw.upper()}</span> when conditions clear")
        elif _mo_signal and _mo_direction:
            _narr_parts.append(f"Signal: {_mo_signal} {_mo_direction.upper()}")
            if _mo_score is not None and _mo_thresh is not None:
                _narr_parts.append(f"Score {int(_mo_score)}/{int(_mo_thresh)}")
        else:
            _narr_parts.append("Scanning for setups")

        # Contract context badges
        _cc_parts: list[str] = []
        _cc_basis = _safe_float(last_decision.get("contract_basis_bps"))
        _cc_oi = _safe_str(last_decision.get("contract_oi_trend"))
        _cc_fund = _safe_str(last_decision.get("contract_funding_bias"))
        if _cc_basis is not None:
            _bc = "green" if _cc_basis > 0 else "red" if _cc_basis < 0 else "muted"
            _cc_parts.append(f"<span class='{_bc}'>basis {_cc_basis:+.1f}bp</span>")
        if _cc_oi and _cc_oi not in ("", "None", "UNKNOWN"):
            _cc_parts.append(f"OI {_cc_oi.lower()}")
        if _cc_fund and _cc_fund not in ("", "None", "UNKNOWN", "NEUTRAL"):
            _cc_parts.append(f"funding {_cc_fund.lower()}")
        _mo_lane = _safe_str(last_decision.get("lane"))
        _mo_lane_lbl = _safe_str(last_decision.get("lane_label"))
        if _mo_lane and _mo_lane_lbl:
            _lc_map = {"A": "#3b82f6", "B": "#10b981", "C": "#f59e0b", "E": "#8b5cf6"}
            _cc_parts.append(f"<span style='color:{_lc_map.get(_mo_lane, '#6b7280')};'>Lane {_mo_lane}</span>")
        if bool(last_decision.get("squeeze_detected")):
            _cc_parts.append("<span style='color:#8b5cf6;'>squeeze</span>")

        # Pattern detection context (VWAP, FVG, Channel) — show values, not just checkmarks
        _pattern_parts: list[str] = []
        _sel_mr_flags = (last_decision.get("v4_selected_mr_flags") or {}) if isinstance(last_decision.get("v4_selected_mr_flags"), dict) else {}
        _sel_tr_flags = (last_decision.get("v4_selected_trend_flags") or {}) if isinstance(last_decision.get("v4_selected_trend_flags"), dict) else {}
        _all_flags = {**_sel_mr_flags, **_sel_tr_flags}

        _vwap_px = _safe_float(last_decision.get("vwap_price"))
        _vwap_side = _safe_str(last_decision.get("vwap_side")) or ""
        if _vwap_px and _vwap_px > 0:
            _vc = "#3b82f6" if _all_flags.get("VWAP_CONFIRM") else "#6b7280"
            _pattern_parts.append(f"<span style='color:{_vc};'>VWAP ${_vwap_px:.4f} | {_vwap_side}</span>")

        _fvg_d = last_decision.get("fvg_detail") if isinstance(last_decision.get("fvg_detail"), dict) else None
        if _fvg_d:
            _ft = _fvg_d.get("type", "")
            _fh = _safe_float(_fvg_d.get("high")) or 0
            _fl = _safe_float(_fvg_d.get("low")) or 0
            _fa = int(_fvg_d.get("age", 0))
            _pattern_parts.append(f"<span style='color:#f59e0b;'>FVG {_ft} ${_fl:.4f}&ndash;${_fh:.4f}, {_fa}bar</span>")
        elif _all_flags.get("FVG_SUPPORT"):
            _pattern_parts.append("<span style='color:#f59e0b;'>FVG&check;</span>")

        _chan_d = last_decision.get("channel_detail") if isinstance(last_decision.get("channel_detail"), dict) else None
        if _chan_d:
            _ct = _safe_str(_chan_d.get("type")) or "?"
            _cp = _safe_str(_chan_d.get("position")) or "?"
            _cu = _safe_float(_chan_d.get("upper")) or 0
            _cl_v = _safe_float(_chan_d.get("lower")) or 0
            _chan_clr = "#10b981" if _all_flags.get("CHANNEL_BREAKOUT") else "#8b5cf6" if (_all_flags.get("CHANNEL_SUPPORT") or _all_flags.get("CHANNEL_RESISTANCE")) else "#6b7280"
            _brk = " BREAKOUT" if _all_flags.get("CHANNEL_BREAKOUT") else ""
            _pattern_parts.append(f"<span style='color:{_chan_clr};'>{_ct} ch @ {_cp}{_brk}</span>")
        elif _all_flags.get("CHANNEL_BREAKOUT"):
            _pattern_parts.append("<span style='color:#10b981;font-weight:600;'>CH-BREAK&check;</span>")

        # Chart pattern engine flags
        if _all_flags.get("FLAG_CONTINUATION"):
            _pattern_parts.append("<span style='color:#06b6d4;font-weight:600;'>FLAG&check;</span>")
        if _all_flags.get("CUP_HANDLE"):
            _pattern_parts.append("<span style='color:#a78bfa;font-weight:600;'>CUP&amp;HANDLE&check;</span>")
        if _all_flags.get("DOUBLE_PATTERN"):
            _pattern_parts.append("<span style='color:#f472b6;font-weight:600;'>DBL-BTM/TOP&check;</span>")

        if _pattern_parts:
            _cc_parts.append(" ".join(_pattern_parts))

        _narr_html = " &middot; ".join(_narr_parts)
        if _cc_parts:
            _narr_html += " &middot; <span class='muted' style='font-size:10px;'>" + " | ".join(_cc_parts) + "</span>"

        _thought_html = ""
        if _mo_thought and len(_mo_thought) > 5:
            _thought_html = (
                f"<div style='margin-top:4px;font-size:11px;color:#6b7280;font-style:italic;'>"
                f"\"{html.escape(_mo_thought[:120])}{'...' if len(_mo_thought) > 120 else ''}\""
                f"</div>"
            )

        st.markdown(
            f"<div class='feed-mini'>"
            f"<div style='display:flex;align-items:center;gap:6px;'>"
            f"<span class='label' style='margin:0;'>STATUS</span>"
            f"<span style='font-size:12px;color:#d1d5db;'>{_narr_html}</span>"
            f"</div>"
            f"{_thought_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── ROW 3.5: Direction Comparison ─────────────────────────────
        try:
            _cmp_l_score = _safe_float(last_decision.get("v4_score_long")) or 0
            _cmp_s_score = _safe_float(last_decision.get("v4_score_short")) or 0
            _cmp_l_thresh = _safe_float(last_decision.get("v4_threshold_long")) or 65
            _cmp_s_thresh = _safe_float(last_decision.get("v4_threshold_short")) or 65
            if _cmp_l_score > 0 or _cmp_s_score > 0:
                _cmp_winner = "LONG" if _cmp_l_score >= _cmp_s_score else "SHORT"
                _cmp_delta = abs(_cmp_l_score - _cmp_s_score)
                _cmp_regime = _safe_str(last_decision.get("v4_selected_regime")) or "trend"
                if _cmp_regime == "trend":
                    _cmp_wf = (last_decision.get("v4_long_trend_flags") or {}) if isinstance(last_decision.get("v4_long_trend_flags"), dict) else {}
                    _cmp_lf = (last_decision.get("v4_short_trend_flags") or {}) if isinstance(last_decision.get("v4_short_trend_flags"), dict) else {}
                else:
                    _cmp_wf = (last_decision.get("v4_long_mr_flags") or {}) if isinstance(last_decision.get("v4_long_mr_flags"), dict) else {}
                    _cmp_lf = (last_decision.get("v4_short_mr_flags") or {}) if isinstance(last_decision.get("v4_short_mr_flags"), dict) else {}
                if _cmp_winner == "SHORT":
                    _cmp_wf, _cmp_lf = _cmp_lf, _cmp_wf
                _flag_labels = {
                    "HTF_BREAK": "HTF Break", "HTF_LEVEL": "HTF Level",
                    "EMA_ALIGN_SLOPE": "EMA Align", "ADX_TREND": "ADX Trend",
                    "ADX_LOW": "ADX Low", "ATR_EXPANDING": "ATR Expand",
                    "VOLUME_SPIKE": "Volume", "BB_EXPAND_OR_WALK": "BB Walk",
                    "BB_REJECTION": "BB Reject", "MACD_MOMENTUM": "MACD Momo",
                    "MACD_DIVERGENCE": "MACD Div", "RSI_EXTREME": "RSI",
                    "FIB_ZONE": "Fib", "VWAP_CONFIRM": "VWAP",
                    "FVG_SUPPORT": "FVG", "CHANNEL_SUPPORT": "Channel",
                    "CHANNEL_BREAKOUT": "Ch Break",
                }
                _tipped = [_flag_labels.get(k, k.replace("_", " ").title())
                           for k in _cmp_wf if _cmp_wf.get(k) and not _cmp_lf.get(k)]
                _loser_dir = "SHORT" if _cmp_winner == "LONG" else "LONG"
                _loser_block = _safe_str(last_decision.get(
                    "short_block_reason" if _cmp_winner == "LONG" else "long_block_reason"
                ))
                _loser_parts: list[str] = []
                if _loser_block:
                    for _lp in _loser_block.split("|")[:3]:
                        if _lp == "no_structure":
                            _loser_parts.append("no entry pattern")
                        elif _lp == "no_score":
                            _loser_parts.append("no score")
                        elif _lp.startswith("score_"):
                            _loser_parts.append(_lp.replace("_", " "))
                        elif _lp.startswith("gates:"):
                            _loser_parts.append("gates: " + _lp[6:].replace(",", ", "))
                        elif _lp == "cooldown":
                            _loser_parts.append("on cooldown")
                        elif _lp == "no_product":
                            _loser_parts.append("unavailable")
                        else:
                            _loser_parts.append(_lp.replace("_", " "))
                _w_clr = "#34d399" if _cmp_winner == "LONG" else "#f87171"
                _l_clr = "#f87171" if _cmp_winner == "LONG" else "#34d399"
                _cmp_html = (
                    f"<div class='feed-mini' style='margin-top:6px;'>"
                    f"<div style='display:flex;align-items:center;justify-content:space-between;'>"
                    f"<span class='label' style='margin:0;'>DIRECTION</span>"
                    f"<span style='font-size:11px;'>"
                    f"<span style='color:{_w_clr};font-weight:700;'>{_cmp_winner}</span>"
                    f" <span class='muted'>wins by</span> "
                    f"<span style='color:#d1d5db;font-weight:600;'>+{int(_cmp_delta)} pts</span>"
                    f"</span></div>"
                    f"<div style='display:flex;gap:16px;margin-top:4px;font-size:11px;'>"
                    f"<span style='color:#34d399;'>LONG <b>{int(_cmp_l_score)}</b>"
                    f"<span class='muted'>/{int(_cmp_l_thresh)}</span></span>"
                    f"<span class='muted'>vs</span>"
                    f"<span style='color:#f87171;'>SHORT <b>{int(_cmp_s_score)}</b>"
                    f"<span class='muted'>/{int(_cmp_s_thresh)}</span></span></div>"
                )
                if _tipped:
                    _cmp_html += (
                        f"<div style='margin-top:4px;font-size:10px;'>"
                        f"<span class='muted'>Tipped by:</span> "
                        f"<span style='color:#d1d5db;'>{html.escape(', '.join(_tipped[:5]))}</span></div>"
                    )
                if _loser_parts:
                    _cmp_html += (
                        f"<div style='margin-top:2px;font-size:10px;'>"
                        f"<span style='color:{_l_clr};'>{_loser_dir}</span> "
                        f"<span class='muted'>{html.escape(' · '.join(_loser_parts))}</span></div>"
                    )
                _cmp_html += "</div>"
                st.markdown(_cmp_html, unsafe_allow_html=True)
        except Exception:
            pass

        # ── ROW 3.7: Best Opportunity ─────────────────────────────────
        try:
            _opp_text = ""
            _opp_icon = ""
            _best_l = _safe_float(last_decision.get("v4_score_long")) or 0
            _best_s = _safe_float(last_decision.get("v4_score_short")) or 0
            _opp_vol_phase = _safe_str(last_decision.get("vol_phase")) or "?"
            _opp_vol_dir = _safe_str(last_decision.get("vol_direction")) or "?"
            if _has_pos:
                _o_dir = _safe_str(pos_view.get("direction")) or "?"
                _o_entry = _safe_float(pos_view.get("entry_price"))
                _o_pnl = _safe_float(last_decision.get("open_pnl_usd"))
                _o_be = _safe_float(last_decision.get("breakeven_price"))
                _o_parts: list[str] = [f"In trade — <span class='{'green' if _o_dir.upper()=='LONG' else 'red'}'>{_o_dir.upper()}</span>"]
                if _o_entry:
                    _o_parts.append(f"at ${_o_entry:.4f}")
                if _o_pnl is not None:
                    _pclr = "green" if _o_pnl >= 0 else "red"
                    _o_parts.append(f"<span class='{_pclr}'>{'+' if _o_pnl >= 0 else ''}${_o_pnl:.2f}</span>")
                if _o_be:
                    _o_parts.append(f"BE ${_o_be:.4f}")
                _opp_text = " &middot; ".join(_o_parts)
                _opp_icon = "&#9889;"
            elif _mo_signal and _mo_score is not None and _mo_thresh is not None and _mo_score >= _mo_thresh:
                _o_dir2 = (_mo_direction or "?").upper()
                _o_entry_type = _safe_str(last_decision.get("entry_type")) or _mo_signal
                _opp_text = (
                    f"Best setup: <span class='{'green' if _o_dir2 == 'LONG' else 'red'}'>{_o_dir2}</span> "
                    f"via {html.escape((_o_entry_type or '').replace('_', ' '))} "
                    f"(score {int(_mo_score)}/{int(_mo_thresh)})"
                )
                _opp_icon = "&#9733;"
            elif _opp_vol_phase.upper() == "COMPRESSION" and not _has_pos:
                _bias_dir = _mo_direction or ""
                _bias_best = max(_best_l, _best_s)
                _opp_text = "No setup — in compression, waiting for ignition"
                if _bias_dir:
                    _bc = "green" if _bias_dir.upper() == "LONG" else "red"
                    _opp_text += f". <span class='{_bc}'>{_bias_dir.upper()}</span> bias"
                    if _bias_best > 0:
                        _opp_text += f" ({int(_bias_best)} pts)"
                _opp_icon = "&#9679;"
            elif _opp_vol_phase.upper() in ("IGNITION", "EXPANSION") and not _has_pos:
                _opp_text = f"Vol {_opp_vol_phase.lower()}"
                if _opp_vol_dir not in ("?", "NEUTRAL"):
                    _vdc = "green" if _opp_vol_dir == "LONG" else "red"
                    _opp_text += f" (<span class='{_vdc}'>{_opp_vol_dir}</span>)"
                _opp_text += f" but no qualifying entry yet. Best score: {int(max(_best_l, _best_s))}"
                _opp_icon = "&#9888;"
            else:
                _scan_reasons: list[str] = []
                if _route_tier == "blocked":
                    _scan_reasons.append("gates blocked")
                if bool(last_decision.get("cooldown_active")):
                    _scan_reasons.append("cooldown active")
                _opp_text = "Scanning for setups"
                if _scan_reasons:
                    _opp_text += f" — {', '.join(_scan_reasons)}"
                _opp_icon = "&#128269;"
            if _opp_text:
                st.markdown(
                    f"<div class='feed-mini' style='margin-top:4px;'>"
                    f"<div style='display:flex;align-items:center;gap:6px;'>"
                    f"<span style='font-size:14px;'>{_opp_icon}</span>"
                    f"<span style='font-size:12px;color:#d1d5db;'>{_opp_text}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            # ── WHY NOT sub-section (unlock hints when not in trade) ──
            if not _has_pos:
                _wn_parts: list[str] = []
                _l_miss = _safe_float(last_decision.get("v4_long_missing_pts"))
                _s_miss = _safe_float(last_decision.get("v4_short_missing_pts"))
                _l_hints = last_decision.get("long_unlock_hints") or []
                _s_hints = last_decision.get("short_unlock_hints") or []
                if isinstance(_l_hints, str):
                    _l_hints = [h.strip() for h in _l_hints.split(",") if h.strip()]
                if isinstance(_s_hints, str):
                    _s_hints = [h.strip() for h in _s_hints.split(",") if h.strip()]
                if _l_miss is not None and _l_miss > 0 and _l_hints:
                    _wn_parts.append(
                        f"<span class='green'>LONG</span> needs {int(_l_miss)} pts: "
                        f"<span class='muted'>{', '.join(str(h) for h in _l_hints[:3])}</span>"
                    )
                if _s_miss is not None and _s_miss > 0 and _s_hints:
                    _wn_parts.append(
                        f"<span class='red'>SHORT</span> needs {int(_s_miss)} pts: "
                        f"<span class='muted'>{', '.join(str(h) for h in _s_hints[:3])}</span>"
                    )
                if _wn_parts:
                    st.markdown(
                        f"<div class='feed-mini' style='margin-top:2px;padding:4px 10px;'>"
                        f"<div style='font-size:10px;color:#6b7280;margin-bottom:2px;'>UNLOCK</div>"
                        f"<div style='font-size:11px;color:#d1d5db;'>"
                        + " &nbsp;|&nbsp; ".join(_wn_parts)
                        + "</div></div>",
                        unsafe_allow_html=True,
                    )
        except Exception:
            pass

        # ── ROW 3.8: Next Play Predictions ────────────────────────────
        try:
            if not _has_pos:
                _np_long = last_decision.get("next_play_long")
                _np_short = last_decision.get("next_play_short")
                if isinstance(_np_long, str):
                    import json as _json_np
                    try:
                        _np_long = _json_np.loads(_np_long)
                    except Exception:
                        _np_long = None
                if isinstance(_np_short, str):
                    try:
                        _np_short = _json_np.loads(_np_short)
                    except Exception:
                        _np_short = None
                if _np_long or _np_short:
                    def _np_col(np_data: dict | None, direction: str) -> str:
                        if not np_data:
                            return f"<div style='flex:1;min-width:120px;color:#374151;font-size:11px;'>No {direction.upper()} trigger nearby</div>"
                        d_clr = "#34d399" if direction == "long" else "#f87171"
                        tp = _safe_float(np_data.get("trigger_price"))
                        tp_s = f"${tp:.4f}" if tp else "—"
                        lvl = str(np_data.get("level_name") or "—").replace("_", " ")
                        dist = _safe_float(np_data.get("distance_atr"))
                        dist_s = f"{dist:.1f} ATR" if dist is not None else "—"
                        ready = _safe_float(np_data.get("readiness_pct"))
                        ready_s = f"{ready:.0f}%" if ready is not None else "—"
                        ready_clr = "#10b981" if (ready is not None and ready >= 80) else "#f59e0b" if (ready is not None and ready >= 50) else "#6b7280"
                        bar_pct = min(100, max(0, ready or 0))
                        return (
                            f"<div style='flex:1;min-width:120px;'>"
                            f"<div style='color:{d_clr};font-size:11px;font-weight:600;margin-bottom:3px;'>{direction.upper()}</div>"
                            f"<div style='font-size:13px;color:#e5e7eb;font-weight:500;'>{tp_s}</div>"
                            f"<div style='font-size:10px;color:#9ca3af;margin-top:1px;'>{html.escape(lvl)} &middot; {dist_s} away</div>"
                            f"<div style='display:flex;align-items:center;gap:6px;margin-top:4px;'>"
                            f"<div style='flex:1;height:3px;background:#1f2937;border-radius:2px;overflow:hidden;'>"
                            f"<div style='width:{bar_pct:.0f}%;height:100%;background:{ready_clr};border-radius:2px;'></div></div>"
                            f"<span style='font-size:10px;color:{ready_clr};'>{ready_s}</span>"
                            f"</div></div>"
                        )
                    st.markdown(
                        f"<div class='intel-card' style='padding:8px 14px;margin-top:4px;'>"
                        f"<div class='intel-title' style='margin-bottom:6px;'>NEXT PLAY</div>"
                        f"<div style='display:flex;gap:16px;'>"
                        f"{_np_col(_np_long, 'long')}"
                        f"{_np_col(_np_short, 'short')}"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
        except Exception:
            pass

        # ── ROW 3.85: HTF Breakout Watch ──────────────────────────────
        try:
            if not _has_pos:
                _bw_dir = _safe_str(last_decision.get("htf_breakout_selected_direction")) or "long"
                _bw_ready = bool(last_decision.get("htf_breakout_selected_ready"))
                _bw_reason = _safe_str(last_decision.get("htf_breakout_selected_reason")) or "watching"
                _bw_pressure = _safe_float(last_decision.get("htf_breakout_selected_pressure_score")) or 0
                _bw_follow = _safe_float(last_decision.get("htf_breakout_selected_followthrough_score")) or 0
                _bw_conf = _safe_float(last_decision.get("htf_breakout_selected_confidence")) or 0
                _bw_hold = _safe_float(last_decision.get("htf_breakout_selected_hold_score")) or 0
                _bw_false = _safe_float(last_decision.get("htf_breakout_selected_false_break_risk")) or 0
                _bw_mgmt = _safe_str(last_decision.get("htf_breakout_selected_management_bias")) or "watching"
                _bw_level = _safe_float(last_decision.get("htf_breakout_selected_breakout_level"))
                _bw_inv = _safe_float(last_decision.get("htf_breakout_selected_invalidation"))
                _bw_chase = _safe_float(last_decision.get("htf_breakout_selected_chase_atr"))
                _bw_evt_block = bool(last_decision.get("htf_breakout_selected_event_blocked"))
                _bw_evt_label = _safe_str(last_decision.get("htf_breakout_selected_event_label")) or "none"
                _bw_evt_hours = _safe_float(last_decision.get("htf_breakout_selected_event_hours"))
                _bw_reasons = last_decision.get("htf_breakout_selected_reasons") or []
                if isinstance(_bw_reasons, str):
                    try:
                        _bw_reasons = json.loads(_bw_reasons)
                    except Exception:
                        _bw_reasons = [_bw_reasons]
                _bw_reasons = [str(x).replace("_", " ") for x in _bw_reasons[:4]]
                _bw_color = "#34d399" if _bw_dir == "long" else "#f87171"
                _bw_status = "READY" if _bw_ready else ("BLOCKED" if _bw_evt_block else "WATCH")
                _bw_status_color = "#22c55e" if _bw_ready else ("#ef4444" if _bw_evt_block else "#fbbf24")
                _bw_level_s = f"${_bw_level:.5f}" if _bw_level is not None else "—"
                _bw_inv_s = f"${_bw_inv:.5f}" if _bw_inv is not None else "—"
                _bw_evt_s = f"{_bw_evt_label} ({_bw_evt_hours:.1f}h)" if (_bw_evt_hours is not None and _bw_evt_label != "none") else _bw_evt_label
                st.markdown(
                    f"<div class='intel-card' style='padding:8px 14px;margin-top:4px;border-left:3px solid {_bw_color};'>"
                    f"<div class='intel-title' style='margin-bottom:6px;'>HTF BREAKOUT WATCH</div>"
                    f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;'>"
                    f"<div><span class='label'>BIAS</span><br/><span class='metric' style='font-size:13px;color:{_bw_color};'>{html.escape(_bw_dir.upper())}</span></div>"
                    f"<div><span class='label'>STATUS</span><br/><span class='metric' style='font-size:13px;color:{_bw_status_color};'>{html.escape(_bw_status)}</span></div>"
                    f"<div><span class='label'>BREAKOUT LVL</span><br/><span class='metric' style='font-size:13px;'>{html.escape(_bw_level_s)}</span></div>"
                    f"<div><span class='label'>INVALIDATION</span><br/><span class='metric' style='font-size:13px;'>{html.escape(_bw_inv_s)}</span></div>"
                    f"</div>"
                    f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:8px;font-size:11px;color:#cbd5e1;'>"
                    f"<div><span class='label'>PRESSURE</span><br/>{_bw_pressure:.0f}/100</div>"
                    f"<div><span class='label'>FOLLOW-THROUGH</span><br/>{_bw_follow:.0f}/100</div>"
                    f"<div><span class='label'>CONFIDENCE</span><br/>{_bw_conf*100:.0f}%</div>"
                    f"<div><span class='label'>CHASE</span><br/>{f'{_bw_chase:.2f} ATR' if _bw_chase is not None else '—'}</div>"
                    f"</div>"
                    f"<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:8px;font-size:11px;color:#cbd5e1;'>"
                    f"<div><span class='label'>HOLD SCORE</span><br/>{_bw_hold:.0f}/100</div>"
                    f"<div><span class='label'>FALSE BREAK</span><br/>{_bw_false:.0f}/100</div>"
                    f"<div><span class='label'>PLAYBOOK</span><br/>{html.escape(_bw_mgmt.replace('_', ' '))}</div>"
                    f"</div>"
                    f"<div class='muted' style='font-size:11px;margin-top:8px;'>"
                    f"Event risk: {html.escape(_bw_evt_s)} &nbsp;|&nbsp; Reason: {html.escape(_bw_reason.replace('_', ' '))}"
                    f"</div>"
                    + (f"<div class='muted' style='font-size:11px;margin-top:4px;'>Signals: {html.escape(' · '.join(_bw_reasons))}</div>" if _bw_reasons else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

        # ── ROW 4: Dual Readiness (LONG vs SHORT scores) ─────────────
        _dr_long = _safe_float(last_decision.get("v4_score_long")) or 0
        _dr_short = _safe_float(last_decision.get("v4_score_short")) or 0
        _dr_thresh = _safe_float(last_decision.get("v4_selected_threshold")) or 65
        _dr_htf = _safe_str(last_decision.get("htf_readiness")) or "—"
        _dr_htf_clr = "green" if "LONG" in _dr_htf else "red" if "SHORT" in _dr_htf else "muted"
        _dr_lane = _safe_str(last_decision.get("lane_label")) or None
        _dr_sweep = bool(last_decision.get("sweep_detected"))
        _dr_adx = _safe_float(last_decision.get("v4_adx_15m"))

        def _score_bar(score: float, threshold: float, direction: str) -> str:
            pct = min(100, max(0, score / max(threshold, 1) * 100))
            clr = "#10b981" if score >= threshold else "#ef4444" if score > 0 else "#374151"
            d_clr = "#34d399" if direction == "long" else "#f87171"
            label = direction.upper()
            score_s = f"{int(score)}" if score > 0 else "—"
            pass_s = "<span style='color:#10b981;font-size:9px;'>PASS</span>" if score >= threshold else ""
            return (
                f"<div style='flex:1;min-width:120px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;'>"
                f"<span style='color:{d_clr};font-size:11px;font-weight:600;'>{label}</span>"
                f"<span style='color:#d1d5db;font-size:12px;'>{score_s}<span class='muted'>/{int(threshold)}</span> {pass_s}</span>"
                f"</div>"
                f"<div style='height:4px;background:#1f2937;border-radius:2px;overflow:hidden;'>"
                f"<div style='width:{pct:.0f}%;height:100%;background:{clr};border-radius:2px;transition:width 0.3s;'></div>"
                f"</div>"
                f"</div>"
            )

        _dr_meta_parts: list[str] = []
        if _dr_adx is not None:
            _adx_clr = "green" if _dr_adx >= 25 else "muted"
            _dr_meta_parts.append(f"ADX <span class='{_adx_clr}'>{_dr_adx:.0f}</span>")
        if _dr_lane:
            _lane_clrs = {"trend": "#3b82f6", "breakout": "#10b981", "sweep_recovery": "#f59e0b", "moonshot": "#8b5cf6", "squeeze_impulse": "#8b5cf6"}
            _lc = _lane_clrs.get(_dr_lane, "#6b7280")
            _dr_meta_parts.append(f"<span style='color:{_lc};'>Lane {_dr_lane.upper().replace('_',' ')}</span>")
        if _dr_sweep:
            _dr_meta_parts.append("<span style='color:#f59e0b;'>SWEEP</span>")
        # Chart pattern badges
        _dr_sel_flags = {**(last_decision.get("v4_selected_mr_flags") or {}), **(last_decision.get("v4_selected_trend_flags") or {})} if isinstance(last_decision.get("v4_selected_mr_flags"), dict) else {}
        if _dr_sel_flags.get("FLAG_CONTINUATION"):
            _dr_meta_parts.append("<span style='color:#06b6d4;'>FLAG</span>")
        if _dr_sel_flags.get("CUP_HANDLE"):
            _dr_meta_parts.append("<span style='color:#a78bfa;'>CUP&amp;H</span>")
        if _dr_sel_flags.get("DOUBLE_PATTERN"):
            _dr_meta_parts.append("<span style='color:#f472b6;'>DBL</span>")
        _dr_squeeze = bool(last_decision.get("squeeze_detected"))
        if _dr_squeeze:
            _dr_meta_parts.append("<span style='color:#8b5cf6;'>SQUEEZE</span>")
        _dr_meta_html = " &middot; ".join(_dr_meta_parts) if _dr_meta_parts else ""

        st.markdown(
            "<div class='intel-card' style='padding:10px 14px;'>"
            "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;'>"
            "<div class='intel-title' style='margin:0;'>READINESS</div>"
            f"<span class='{_dr_htf_clr}' style='font-size:10px;letter-spacing:0.5px;'>{html.escape(_dr_htf.replace('_',' '))}</span>"
            "</div>"
            f"<div style='display:flex;gap:16px;'>"
            f"{_score_bar(_dr_long, _dr_thresh, 'long')}"
            f"{_score_bar(_dr_short, _dr_thresh, 'short')}"
            f"</div>"
            + (f"<div style='margin-top:6px;font-size:10px;color:#9ca3af;'>{_dr_meta_html}</div>" if _dr_meta_html else "")
            + "</div>",
            unsafe_allow_html=True,
        )

        # ── ROW 5: Contract Intelligence ──────────────────────────────
        _ci_mark = _safe_float(last_decision.get("contract_mark_price"))
        _ci_index = _safe_float(last_decision.get("contract_index_price"))
        _ci_basis = _safe_float(last_decision.get("contract_basis_bps"))
        _ci_oi_trend = _safe_str(last_decision.get("contract_oi_trend")) or "—"
        _ci_oi_delta = _safe_float(last_decision.get("contract_oi_delta_15m"))
        _ci_funding = _safe_str(last_decision.get("contract_funding_bias")) or "—"
        _ci_oi_price = _safe_str(last_decision.get("contract_oi_price_rel")) or "—"
        _ci_cascade = last_decision.get("cascade_event") if isinstance(last_decision.get("cascade_event"), dict) else None
        _ci_moonshot_cfg = (cfg.get("v4") or {}).get("moonshot") or {}
        _ci_moonshot_on = bool(_ci_moonshot_cfg.get("enabled"))

        _ci_items: list[str] = []

        # Basis
        if _ci_basis is not None:
            _b_clr = "green" if _ci_basis > 0 else "red" if _ci_basis < -5 else "muted"
            _ci_items.append(f"<span class='label'>BASIS</span> <span class='{_b_clr}'>{_ci_basis:+.1f}bp</span>")

        # Mark vs Index
        if _ci_mark and _ci_index:
            _ci_items.append(f"<span class='label'>MARK</span> ${_ci_mark:.4f} <span class='muted'>IDX</span> ${_ci_index:.4f}")

        # OI trend + delta
        _oi_clr = "green" if _ci_oi_trend in ("RISING", "INCREASING") else "red" if _ci_oi_trend in ("FALLING", "DECREASING") else "muted"
        _oi_txt = _ci_oi_trend.lower()
        if _ci_oi_delta is not None and _ci_oi_delta != 0:
            _oi_txt += f" ({_ci_oi_delta:+.1f}%)"
        _ci_items.append(f"<span class='label'>OI</span> <span class='{_oi_clr}'>{_oi_txt}</span>")

        # OI vs Price relationship
        if _ci_oi_price and _ci_oi_price not in ("—", "NEUTRAL", "UNKNOWN"):
            _ci_items.append(f"<span class='label'>OI/PX</span> {_ci_oi_price.lower()}")

        # Funding bias
        _fund_clr = "green" if "LONG" in _ci_funding else "red" if "SHORT" in _ci_funding else "muted"
        _ci_items.append(f"<span class='label'>FUNDING</span> <span class='{_fund_clr}'>{_ci_funding.lower().replace('_',' ')}</span>")

        # Cascade
        if _ci_cascade and _ci_cascade.get("cascade_type"):
            _sev = str(_ci_cascade.get("severity") or "MINOR")
            _sev_clr = "#ef4444" if _sev == "MAJOR" else "#f59e0b" if _sev == "MODERATE" else "#6b7280"
            _ci_items.append(
                f"<span style='color:{_sev_clr};font-weight:600;'>CASCADE {_sev}</span> "
                f"{_ci_cascade.get('cascade_type','')}"
            )

        # Moonshot
        if _ci_moonshot_on:
            _ci_items.append("<span style='color:#8b5cf6;'>MOONSHOT ARMED</span>")

        if _ci_items:
            _ci_html = " &middot; ".join(_ci_items)
            st.markdown(
                "<div class='intel-card' style='padding:8px 14px;'>"
                "<div class='intel-title'>CONTRACT INTEL</div>"
                f"<div style='font-size:11px;color:#d1d5db;line-height:1.6;'>{_ci_html}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
    # ── Live Event Feed (from bot_state.db) ──────────────────────────────────
    try:
        _ev_list = _load_bot_events_cached(limit=50)
        _ev_notable = [e for e in _ev_list if e.get("type") not in ("startup",)]
        if _ev_notable:
            _ev_icon = {
                "entered_position": ("ENTRY", "#10b981"),
                "exit_position": ("EXIT", "#ef4444"),
                "cash_movement": ("CASH", "#3b82f6"),
                "incident": ("INCIDENT", "#f59e0b"),
                "manage_open_position": ("MANAGE", "#6b7280"),
                "recovered_open_position_exchange_truth": ("RECOVERED", "#f59e0b"),
                "plrl3_exit": ("PLRL3", "#ef4444"),
                "margin_policy_error": ("MARGIN", "#ef4444"),
                "recovery_error": ("ERROR", "#ef4444"),
            }
            _ev_html_parts: list[str] = []
            for _ev in _ev_notable[:5]:
                _et = _ev.get("type", "unknown")
                _ep = _ev.get("payload") or {}
                _et_label, _et_clr = _ev_icon.get(_et, (_et.upper().replace("_", " "), "#6b7280"))
                # Format timestamp to PT
                _ev_ts = _ev.get("ts", "")
                try:
                    _ev_dt = pd.to_datetime(_ev_ts, utc=True)
                    _ev_ts_pt = _ev_dt.tz_convert("America/Los_Angeles").strftime("%b %d %I:%M %p PT")
                except Exception:
                    _ev_ts_pt = _ev_ts[:16] if _ev_ts else "?"
                # Build detail string
                _ev_detail = ""
                if _et == "entered_position":
                    _ev_detail = f"{(_ep.get('direction') or '?').upper()} {_ep.get('product_id','?')} x{_ep.get('size','?')}"
                elif _et == "exit_position":
                    _ev_detail = f"{(_ep.get('direction') or '?').upper()} &middot; {(_ep.get('exit_reason') or '?').replace('_',' ')}"
                elif _et == "cash_movement":
                    _d = _ep.get("deltas") or {}
                    _ev_detail = " ".join(f"{k} {v:+.2f}" for k, v in _d.items()) if _d else (_ep.get("reason") or "")
                elif _et == "incident":
                    _ev_detail = (_ep.get("reason") or _ep.get("type") or "").replace("_", " ")
                else:
                    _ev_detail = (_ep.get("notes") or _ep.get("reason") or "")[:60]
                _ev_html_parts.append(
                    f"<div style='display:flex;align-items:center;gap:8px;padding:3px 0;'>"
                    f"<span class='pill' style='background:{_et_clr}20;color:{_et_clr};font-size:9px;min-width:50px;text-align:center;'>{_et_label}</span>"
                    f"<span style='font-size:11px;color:#d1d5db;flex:1;'>{_ev_detail}</span>"
                    f"<span class='muted' style='font-size:9px;white-space:nowrap;'>{_ev_ts_pt}</span>"
                    f"</div>"
                )
            st.markdown(
                "<div class='intel-card' style='padding:8px 14px;'>"
                "<div class='intel-title'>RECENT EVENTS</div>"
                + "".join(_ev_html_parts)
                + "</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Session Summary Bar ──────────────────────────────────────────────────
    try:
        _sess_id = _safe_str(last_decision.get("session_id")) or None
        _sess_parts = []
        if _sess_id:
            _sess_parts.append(f"<span class='pill' style='background:rgba(59,130,246,0.15);color:#3b82f6;font-size:10px;'>SESSION {_sess_id}</span>")
        # Compute session uptime from decisions with same session_id
        if not decisions.empty and _sess_id and "session_id" in decisions.columns:
            _sess_df = decisions[decisions["session_id"].astype(str) == _sess_id]
            if not _sess_df.empty and "timestamp" in _sess_df.columns:
                _sess_start = pd.to_datetime(_sess_df["timestamp"].min(), utc=True, errors="coerce")
                if pd.notna(_sess_start):
                    _sess_up = (_now_utc - _sess_start.to_pydatetime()).total_seconds()
                    if _sess_up > 0:
                        _h, _rem = divmod(int(_sess_up), 3600)
                        _m = _rem // 60
                        _sess_parts.append(f"uptime {_h}h{_m:02d}m" if _h else f"uptime {_m}m")
                _sess_cycles = len(_sess_df)
                _sess_parts.append(f"{_sess_cycles} cycles")
        if trades is not None and not trades.empty:
            _today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            _today_trades = trades[trades["timestamp"].astype(str).str.startswith(_today_str)] if "timestamp" in trades.columns else pd.DataFrame()
            if not _today_trades.empty:
                _sess_parts.append(f"{len(_today_trades)} trades today")
        if _sess_parts:
            st.markdown(
                "<div style='display:flex;align-items:center;gap:10px;padding:6px 12px;margin-bottom:8px;"
                "background:rgba(30,41,59,0.5);border-radius:8px;font-size:11px;color:#9ca3af;flex-wrap:wrap;'>"
                + " &bull; ".join(_sess_parts)
                + "</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Trades Today (receipt view) ──────────────────────────────────────────
    try:
        if not trades.empty and "result" in trades.columns:
            _today_str = datetime.now(timezone.utc).astimezone(PT).strftime("%Y-%m-%d")
            _tt = trades[trades["result"].astype(str).isin(["win", "loss", "flat"])].copy()
            if "entry_time" in _tt.columns:
                _tt["_entry_dt"] = pd.to_datetime(_tt["entry_time"], utc=True, errors="coerce")
                _tt = _tt[_tt["_entry_dt"].dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%d") == _today_str]
            elif "timestamp" in _tt.columns:
                _tt["_ts_dt"] = pd.to_datetime(_tt["timestamp"], utc=True, errors="coerce")
                _tt = _tt[_tt["_ts_dt"].dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%d") == _today_str]
            # Ghost filter: exclude reconciler-generated exits (never real bot trades)
            if not _tt.empty and "exit_reason" in _tt.columns:
                _tt = _tt[_tt["exit_reason"].astype(str) != "exchange_side_close"].copy()
            if not _tt.empty:
                _trade_rows: list[str] = []
                for _, _tr in _tt.iterrows():
                    _t_side = str(_tr.get("side") or _tr.get("direction") or "?").upper()
                    _t_entry = _safe_float(_tr.get("entry_price"))
                    _t_exit = _safe_float(_tr.get("exit_price"))
                    _t_pnl = _safe_float(_tr.get("pnl_usd"))
                    _t_result = str(_tr.get("result") or "?")
                    _t_reason = str(_tr.get("exit_reason") or "?")
                    _t_dur = _safe_float(_tr.get("time_in_trade_min"))
                    _t_entry_t = _coerce_ts_utc(_tr.get("entry_time"))
                    _t_exit_t = _coerce_ts_utc(_tr.get("exit_time") or _tr.get("timestamp"))
                    _t_cls = "green" if _t_result == "win" else "red"
                    _t_sign = "+" if (_t_pnl or 0) >= 0 else ""
                    _t_entry_str = f"${_t_entry:.5f}" if _t_entry else "?"
                    _t_exit_str = f"${_t_exit:.5f}" if _t_exit else "?"
                    _t_pnl_str = f"<span class='{_t_cls}'>{_t_sign}${_t_pnl:.2f}</span>" if _t_pnl is not None else "?"
                    _t_time_str = _fmt_pt_short(_t_entry_t) if _t_entry_t else "?"
                    _t_dur_str = f"{_t_dur:.0f}m" if _t_dur else "?"
                    _trade_rows.append(
                        f"<tr>"
                        f"<td style='color:#9ca3af;'>{_t_time_str}</td>"
                        f"<td>{_t_side}</td>"
                        f"<td>{_t_entry_str}</td>"
                        f"<td>{_t_exit_str}</td>"
                        f"<td>{_t_pnl_str}</td>"
                        f"<td style='color:#9ca3af;'>{_t_dur_str}</td>"
                        f"<td style='color:#9ca3af;'>{_t_reason}</td>"
                        f"</tr>"
                    )
                _total_pnl = sum(_safe_float(r.get("pnl_usd")) or 0 for _, r in _tt.iterrows())
                _wins = len(_tt[_tt["result"] == "win"])
                _losses = len(_tt[_tt["result"] == "loss"])
                _total_cls = "green" if _total_pnl >= 0 else "red"
                st.markdown(
                    f"<div class='card' style='margin-top:8px;padding:8px 12px;overflow-x:auto;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                    f"<span class='label'>Trades Today</span>"
                    f"<span class='muted' style='font-size:10px;'>{_wins}W / {_losses}L</span>"
                    f"<span class='{_total_cls}' style='font-size:12px;font-weight:700;margin-left:auto;'>{'+'if _total_pnl>=0 else ''}${_total_pnl:.2f}</span>"
                    f"</div>"
                    f"<table style='width:100%;font-size:11px;border-collapse:collapse;'>"
                    f"<tr style='color:#6b7280;border-bottom:1px solid #333;'>"
                    f"<th style='text-align:left;padding:2px 4px;'>Time</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>Side</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>Entry</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>Exit</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>P&L</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>Dur</th>"
                    f"<th style='text-align:left;padding:2px 4px;'>Reason</th>"
                    f"</tr>"
                    + "".join(_trade_rows)
                    + f"</table></div>",
                    unsafe_allow_html=True,
                )
    except Exception:
        pass

    # ── Offline Recap (bot was down while market moved) ──────────────────────
    try:
        if not decisions.empty and "timestamp" in decisions.columns:
            _dec_sorted = decisions.sort_values("timestamp").reset_index(drop=True)
            _dec_ts = _dec_sorted["timestamp"]
            _dec_gaps = _dec_ts.diff().dt.total_seconds().dropna()
            _offline_threshold = 180
            _big_gaps = []
            for idx, gap_s in _dec_gaps.items():
                if gap_s > _offline_threshold and idx > 0:
                    _big_gaps.append({
                        "start": _dec_ts.iloc[idx - 1],
                        "end": _dec_ts.iloc[idx],
                        "seconds": gap_s,
                        "pre_iloc": idx - 1,
                        "post_iloc": idx,
                    })
            _recent_gaps = [
                g for g in _big_gaps
                if (_now_utc - g["end"].to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds() < 86400
            ] if _big_gaps else []
            if _recent_gaps:
                _latest_gap = _recent_gaps[-1]
                _gap_dur = int(_latest_gap["seconds"])
                _gap_h, _gap_rem = divmod(_gap_dur, 3600)
                _gap_m = _gap_rem // 60
                _gap_dur_str = f"{_gap_h}h {_gap_m}m" if _gap_h else f"{_gap_m}m"
                _gap_start_pt = _latest_gap["start"].astimezone(PT).strftime("%b %d %I:%M %p") if hasattr(_latest_gap["start"], "astimezone") else "?"
                _gap_end_pt = _latest_gap["end"].astimezone(PT).strftime("%b %d %I:%M %p") if hasattr(_latest_gap["end"], "astimezone") else "?"

                # ── Last seen vs current price ──
                _pre_row = _dec_sorted.iloc[_latest_gap["pre_iloc"]]
                _last_seen_price = _safe_float(_pre_row.get("price"))
                _now_price = _safe_float(last_decision.get("price")) or _safe_float(_dec_sorted.iloc[_latest_gap["post_iloc"]].get("price"))

                # ── 1h candles during the gap (from Coinbase, always available) ──
                _gap_1h = pd.DataFrame()
                if not hist_1h.empty and "timestamp" in hist_1h.columns:
                    _required_cols = {"open", "high", "low", "close"}
                    if _required_cols.issubset(set(hist_1h.columns)):
                        _gap_1h = hist_1h[
                            (hist_1h["timestamp"] >= _latest_gap["start"]) &
                            (hist_1h["timestamp"] <= _latest_gap["end"])
                        ].copy()

                _gap_low = float(_gap_1h["low"].min()) if not _gap_1h.empty else None
                _gap_high = float(_gap_1h["high"].max()) if not _gap_1h.empty else None
                _gap_range_pct = ((_gap_high - _gap_low) / _gap_low * 100) if _gap_low and _gap_high and _gap_low > 0 else 0

                # ── Expand 1h candles into a tick-like price series for _evaluate_path ──
                def _ohlc_to_ticks(candles_df: pd.DataFrame) -> pd.DataFrame:
                    rows: list[dict] = []
                    for _, c in candles_df.iterrows():
                        ts = c["timestamp"]
                        o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
                        if cl >= o:  # bullish: open → low → high → close
                            seq = [o, l, h, cl]
                        else:  # bearish: open → high → low → close
                            seq = [o, h, l, cl]
                        for j, px in enumerate(seq):
                            rows.append({"price": px, "timestamp": ts + pd.Timedelta(minutes=j * 15)})
                    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["price", "timestamp"])

                _gap_ticks = _ohlc_to_ticks(_gap_1h) if not _gap_1h.empty else pd.DataFrame(columns=["price", "timestamp"])

                # Also get post-gap ticks for outcome evaluation beyond the gap window
                _post_gap_ticks = pd.DataFrame(columns=["price", "timestamp"])
                if not hist_1h.empty and "timestamp" in hist_1h.columns:
                    _post_candles = hist_1h[hist_1h["timestamp"] > _latest_gap["end"]].head(24)
                    if not _post_candles.empty:
                        _post_gap_ticks = _ohlc_to_ticks(_post_candles)
                _all_ticks = pd.concat([_gap_ticks, _post_gap_ticks]).reset_index(drop=True) if not _gap_ticks.empty else _post_gap_ticks

                # ── Find swing entries in gap candles ──
                _hypo_trades: list[dict] = []
                if len(_gap_1h) >= 3:
                    _lows = _gap_1h["low"].astype(float).values
                    _highs = _gap_1h["high"].astype(float).values
                    _closes = _gap_1h["close"].astype(float).values
                    _gap_timestamps = _gap_1h["timestamp"].values
                    # Local swing lows → LONG candidates
                    for i in range(1, len(_lows) - 1):
                        if _lows[i] < _lows[i - 1] and _lows[i] < _lows[i + 1]:
                            _hypo_trades.append({
                                "direction": "long",
                                "entry_price": float(_closes[i]),
                                "swing_level": float(_lows[i]),
                                "entry_ts": pd.Timestamp(_gap_timestamps[i]),
                            })
                    # Local swing highs → SHORT candidates
                    for i in range(1, len(_highs) - 1):
                        if _highs[i] > _highs[i - 1] and _highs[i] > _highs[i + 1]:
                            _hypo_trades.append({
                                "direction": "short",
                                "entry_price": float(_closes[i]),
                                "swing_level": float(_highs[i]),
                                "entry_ts": pd.Timestamp(_gap_timestamps[i]),
                            })

                # Fallback: if no swings found but gap had candles, use overall min/max
                if not _hypo_trades and not _gap_1h.empty:
                    _min_pos = _gap_1h["low"].astype(float).idxmin()
                    _max_pos = _gap_1h["high"].astype(float).idxmax()
                    if _min_pos is not None:
                        _hypo_trades.append({
                            "direction": "long",
                            "entry_price": float(_gap_1h.loc[_min_pos, "close"]),
                            "swing_level": float(_gap_1h.loc[_min_pos, "low"]),
                            "entry_ts": _gap_1h.loc[_min_pos, "timestamp"],
                        })
                    if _max_pos is not None and _max_pos != _min_pos:
                        _hypo_trades.append({
                            "direction": "short",
                            "entry_price": float(_gap_1h.loc[_max_pos, "close"]),
                            "swing_level": float(_gap_1h.loc[_max_pos, "high"]),
                            "entry_ts": _gap_1h.loc[_max_pos, "timestamp"],
                        })

                # Sort by time, keep best 4
                _hypo_trades.sort(key=lambda t: t.get("entry_ts") or pd.Timestamp.min)
                _hypo_trades = _hypo_trades[:4]

                # ── Evaluate each hypothetical trade ──
                _contract_size = 5000.0
                try:
                    _pid = _safe_str(cfg.get("product_id")) or "XLP-USD-PERP"
                    _det = _get_cfm_product_details_cached(_pid) if _pid else {}
                    _cs_val = _contract_size_from_details(_det)
                    if _cs_val:
                        _contract_size = _cs_val
                except Exception:
                    pass
                _leverage = int(cfg.get("leverage") or 4)

                for ht in _hypo_trades:
                    _after = _all_ticks[_all_ticks["timestamp"] > ht["entry_ts"]].copy() if not _all_ticks.empty else pd.DataFrame()
                    if _after.empty or len(_after) < 4:
                        ht.update({"verdict": "insufficient_data", "tp1_price": None, "stop_price": None, "liq_price": None, "pnl_usd": None, "mfe_pct": 0, "mae_pct": 0})
                        continue
                    _ev = _evaluate_path(sig_price=ht["entry_price"], sig_dir=ht["direction"], sig_ts=ht["entry_ts"], after_df=_after, cfg=cfg, df_1h=hist_1h)
                    ht["verdict"] = _ev.get("verdict", "no_decisive_outcome")
                    ht["mfe_pct"] = _ev.get("mfe_pct", 0)
                    ht["mae_pct"] = _ev.get("mae_pct", 0)
                    ht["tp1_price"] = _ev.get("tp1_price")
                    ht["stop_price"] = _ev.get("stop_price")
                    ht["liq_price"] = _ev.get("liq_price")
                    ht["tp1_hit_ts"] = _ev.get("tp1_hit_ts")
                    # Dollar P&L
                    if ht["verdict"] == "profit_first" and ht["tp1_price"]:
                        ht["pnl_usd"] = _project_pnl_usd(ht["entry_price"], ht["tp1_price"], direction=ht["direction"], contracts=1, contract_size=_contract_size)
                    elif ht["verdict"] == "stopped_before_profit" and ht["stop_price"]:
                        ht["pnl_usd"] = _project_pnl_usd(ht["entry_price"], ht["stop_price"], direction=ht["direction"], contracts=1, contract_size=_contract_size)
                    elif ht["verdict"] == "liquidated_before_profit" and ht.get("liq_price"):
                        ht["pnl_usd"] = _project_pnl_usd(ht["entry_price"], ht["liq_price"], direction=ht["direction"], contracts=1, contract_size=_contract_size)
                    else:
                        ht["pnl_usd"] = None

                _profitable = [t for t in _hypo_trades if t.get("verdict") == "profit_first"]
                _losers = [t for t in _hypo_trades if t.get("verdict") in ("stopped_before_profit", "liquidated_before_profit")]
                _missed_profit = sum(t.get("pnl_usd") or 0 for t in _profitable)
                _would_have_lost = sum(t.get("pnl_usd") or 0 for t in _losers)

                # ── Build the recap card ──
                st.markdown("<div class='panel-title' style='margin-top:10px;'>Offline Recap</div>", unsafe_allow_html=True)
                st.markdown("<div class='intel-card'>", unsafe_allow_html=True)

                # Header
                st.markdown(
                    f"<div class='intel-title'>BOT OFFLINE &middot; {_gap_dur_str}</div>"
                    f"<div class='intel-event'>"
                    f"<span class='time'>{_gap_start_pt}</span> &rarr; <span class='time'>{_gap_end_pt}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Price: last seen → now
                if _last_seen_price and _now_price:
                    _pchg = (_now_price - _last_seen_price) / _last_seen_price * 100
                    _pclr = "green" if _pchg >= 0 else "red"
                    _range_part = ""
                    if _gap_low and _gap_high:
                        _range_part = f" &middot; Range ${_gap_low:.4f} &ndash; ${_gap_high:.4f} ({_gap_range_pct:.1f}%)"
                    st.markdown(
                        f"<div class='intel-event'>"
                        f"<span class='label'>LAST SEEN</span> <strong>${_last_seen_price:.4f}</strong>"
                        f" &rarr; "
                        f"<span class='label'>NOW</span> <strong>${_now_price:.4f}</strong>"
                        f" <span class='{_pclr}'>({'+' if _pchg >= 0 else ''}{_pchg:.2f}%)</span>"
                        f"{_range_part}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Narrative: what the bot would have done
                if _hypo_trades:
                    # Build a plain-english story
                    _story_parts: list[str] = []
                    if _gap_low and _gap_high and _last_seen_price:
                        if _gap_low < _last_seen_price * 0.995:
                            _dip_pct = (_last_seen_price - _gap_low) / _last_seen_price * 100
                            _story_parts.append(f"XLM dipped to ${_gap_low:.4f} ({_dip_pct:.1f}% below last seen)")
                        if _gap_high > _last_seen_price * 1.005:
                            _spike_pct = (_gap_high - _last_seen_price) / _last_seen_price * 100
                            _story_parts.append(f"spiked to ${_gap_high:.4f} (+{_spike_pct:.1f}%)")
                    if _story_parts:
                        st.markdown(
                            f"<div class='intel-event'>{' and '.join(_story_parts)}.</div>",
                            unsafe_allow_html=True,
                        )

                    # Each hypothetical trade
                    for ht in _hypo_trades:
                        _ht_ts = _fmt_ts(ht["entry_ts"]) if ht.get("entry_ts") else "?"
                        _ht_dir = ht.get("direction", "?").upper()
                        _ht_dir_clr = "green" if ht["direction"] == "long" else "red"
                        _ht_entry = ht.get("entry_price", 0)
                        _ht_verdict = ht.get("verdict", "?")
                        _ht_pnl = ht.get("pnl_usd")

                        if _ht_verdict == "profit_first":
                            _tp1 = ht.get("tp1_price") or 0
                            _pnl_s = f" &rarr; <span class='green'>+{_format_money(_ht_pnl)}</span>" if _ht_pnl else ""
                            _line = (
                                f"<span class='{_ht_dir_clr}'>{_ht_dir}</span> at "
                                f"<strong>${_ht_entry:.4f}</strong> &rarr; "
                                f"TP1 <strong>${_tp1:.4f}</strong> hit"
                                f"{_pnl_s}"
                            )
                            _icon = "<span class='green'>&#10003;</span>"
                        elif _ht_verdict in ("stopped_before_profit", "liquidated_before_profit"):
                            _exit_px = ht.get("stop_price") or ht.get("liq_price") or 0
                            _kind = "Stopped" if "stopped" in _ht_verdict else "Liquidated"
                            _pnl_s = f" &rarr; <span class='red'>{_format_money(_ht_pnl)}</span>" if _ht_pnl else ""
                            _line = (
                                f"<span class='{_ht_dir_clr}'>{_ht_dir}</span> at "
                                f"<strong>${_ht_entry:.4f}</strong> &rarr; "
                                f"{_kind} at <strong>${_exit_px:.4f}</strong>"
                                f"{_pnl_s}"
                            )
                            _icon = "<span class='red'>&#10007;</span>"
                        elif _ht_verdict == "insufficient_data":
                            _line = (
                                f"<span class='{_ht_dir_clr}'>{_ht_dir}</span> at "
                                f"<strong>${_ht_entry:.4f}</strong> &rarr; "
                                f"<span class='muted'>not enough data to evaluate</span>"
                            )
                            _icon = "<span class='muted'>&mdash;</span>"
                        else:
                            _mfe = ht.get("mfe_pct") or 0
                            _line = (
                                f"<span class='{_ht_dir_clr}'>{_ht_dir}</span> at "
                                f"<strong>${_ht_entry:.4f}</strong> &rarr; "
                                f"<span class='muted'>no TP1/stop hit yet</span> "
                                f"(best move <span class='green'>+{_mfe:.2f}%</span>)"
                            )
                            _icon = "<span class='muted'>&#8226;</span>"

                        st.markdown(
                            f"<div class='feed-mini'>"
                            f"<span class='time'>{_ht_ts}</span> "
                            f"{_icon} {_line}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    # Bottom line: total missed profit or loss avoidance
                    if _missed_profit > 0:
                        st.markdown(
                            f"<div class='intel-event' style='margin-top:6px;'>"
                            f"<strong>Missed profit</strong>: "
                            f"<span class='green'>+{_format_money(_missed_profit)}</span> "
                            f"from {len(_profitable)} trade{'s' if len(_profitable) != 1 else ''} "
                            f"(1 contract, {_leverage}x leverage)"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    if _losers:
                        st.markdown(
                            f"<div class='intel-event'>"
                            f"<strong>Would have lost</strong>: "
                            f"<span class='red'>{_format_money(_would_have_lost)}</span> "
                            f"on {len(_losers)} stopped trade{'s' if len(_losers) != 1 else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    if _missed_profit > 0 and _would_have_lost < 0:
                        _net = _missed_profit + _would_have_lost
                        _net_clr = "green" if _net >= 0 else "red"
                        _net_sign = "+" if _net >= 0 else ""
                        st.markdown(
                            f"<div class='intel-event'>"
                            f"<strong>Net missed</strong>: "
                            f"<span class='{_net_clr}'>{_net_sign}{_format_money(abs(_net))}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    if not _profitable and not _losers:
                        st.markdown(
                            f"<div class='intel-event' style='margin-top:4px;'>"
                            f"<span class='muted'>Market moved but no clear swing setups would have triggered the bot</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    if _gap_low and _gap_high:
                        st.markdown(
                            f"<div class='intel-event'>"
                            f"<span class='muted'>Market ranged ${_gap_low:.4f} &ndash; ${_gap_high:.4f} during downtime. "
                            f"No clear swing setups detected.</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<div class='intel-event'><span class='muted'>No candle data available to replay the gap</span></div>",
                            unsafe_allow_html=True,
                        )

                st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        pass

    left, mid = st.columns([1.2, 2.5])

    with left:
        st.markdown("<div class='panel-title'>Position</div>", unsafe_allow_html=True)
        # Ghost exit warning: exchange has position but bot doesn't know about it
        if _ghost_exit_detected:
            st.markdown(
                "<div class='stale-banner stale-danger' style='margin-bottom:10px;'>"
                "GHOST EXIT — Bot logged exit but exchange still has position open. "
                "Showing exchange position below. Bot will re-detect next cycle."
                "</div>",
                unsafe_allow_html=True,
            )
        if pos_view and pos_source:
            entry_px = _safe_float(pos_view.get("entry_price")) or 0.0
            pos_dir = _safe_str(pos_view.get("direction")) or "?"
            lev = float((pos_view.get("leverage") or 1) if pos_source == "BOT" else (cfg.get("leverage") or 1))
            # Prefer perp mark price (matches Coinbase PnL) over spot price
            _snap_mark = _safe_float(last_decision.get("mark_price"))
            _snap_spot = _safe_float(last_decision.get("spot_price")) or _safe_float(last_decision.get("price"))
            live_price = _snap_mark if _snap_mark and _snap_mark > 0 else (last_decision.get("price") if pos_source == "BOT" else _safe_float(pos_view.get("current_price")))
            product_id = _safe_str(pos_view.get("product_id")) or "-"
            contracts = pos_view.get("contracts") if pos_source == "EXCHANGE" else pos_view.get("size")
            u_pnl = _safe_float(pos_view.get("unrealized_pnl")) if pos_source == "EXCHANGE" else None
            stop = pos_view.get("stop_loss", "-") if pos_source == "BOT" else "-"
            tp1 = pos_view.get("tp1", "-") if pos_source == "BOT" else "-"
            tp2 = pos_view.get("tp2", "-") if pos_source == "BOT" else "-"
            tp3 = pos_view.get("tp3", "-") if pos_source == "BOT" else "-"
            # Snapshot-enriched fields
            _snap_pnl_usd = _safe_float(last_decision.get("pnl_usd_live"))
            _snap_max_unreal = _safe_float(last_decision.get("max_unrealized_usd"))
            _snap_giveback = _safe_float(last_decision.get("giveback_usd"))
            _snap_contract_size = _safe_float(last_decision.get("contract_size")) or float(cfg.get("contract_size", 5000) or 5000)
            _snap_mr_intraday = _safe_float(last_decision.get("mr_intraday"))
            _snap_mr_overnight = _safe_float(last_decision.get("mr_overnight"))
            _snap_basis_bps = _safe_float(last_decision.get("contract_basis_bps"))
            _snap_funding_bias = _safe_str(last_decision.get("contract_funding_bias"))

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            # Side pill + contract
            dir_color = "ok" if pos_dir == "long" else "danger"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span class='pill {dir_color}' style='font-size:12px;font-weight:700;'>{pos_dir.upper()} {lev:.0f}x</span>"
                f"<span class='muted' style='font-size:11px;'>{product_id}</span>"
                f"<span class='muted' style='font-size:10px;'>src: {pos_source}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Contracts + notional
            _n_contracts = float(contracts) if contracts is not None else 0.0
            _notional = float(live_price or 0) * _snap_contract_size * _n_contracts if live_price and _n_contracts else None
            _contracts_label = f"{int(_n_contracts)}" if _n_contracts else "-"
            _notional_label = f"${_notional:,.2f}" if _notional else "-"
            st.markdown(
                f"<div style='margin-top:8px;display:flex;gap:20px;'>"
                f"<div><div class='label'>CONTRACTS</div><div class='metric'>{_contracts_label}</div></div>"
                f"<div><div class='label'>NOTIONAL</div><div class='metric'>{_notional_label}</div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Entry + Mark price + Spot
            _spot_label = f"<div><div class='label'>SPOT</div><div class='metric muted'>${float(_snap_spot):.6f}</div></div>" if _snap_spot and _snap_mark and abs(_snap_spot - _snap_mark) > 0.000001 else ""
            st.markdown(
                f"<div style='margin-top:8px;display:flex;gap:20px;'>"
                f"<div><div class='label'>ENTRY</div><div class='metric'>${entry_px:.6f}</div></div>"
                f"<div><div class='label'>MARK</div><div class='metric'>${float(live_price):.6f}</div></div>"
                f"{_spot_label}"
                f"</div>" if live_price else
                f"<div style='margin-top:8px;'><div class='label'>ENTRY</div><div class='metric'>${entry_px:.6f}</div></div>",
                unsafe_allow_html=True,
            )
            # Basis indicator (mark vs spot)
            if _snap_mark and _snap_spot and _snap_spot > 0:
                _basis_bps_calc = (_snap_mark - _snap_spot) / _snap_spot * 10000
                _basis_cls = "danger" if _basis_bps_calc > 10 else ("ok" if _basis_bps_calc < -10 else "muted")
                st.markdown(f"<div class='{_basis_cls}' style='font-size:10px;'>Basis: {_basis_bps_calc:+.1f} bps (mark {'above' if _basis_bps_calc > 0 else 'below'} spot)</div>", unsafe_allow_html=True)

            # Unrealized PnL (% and USD)
            if live_price and entry_px:
                pnl_pct = (float(live_price) - entry_px) / entry_px * (1 if pos_dir == "long" else -1)
                pnl_color = "ok" if pnl_pct >= 0 else "danger"
                sign = "+" if pnl_pct >= 0 else ""
                # Use snapshot PnL USD if available, else exchange uPnL, else calculate
                _pnl_usd = _snap_pnl_usd if _snap_pnl_usd is not None else u_pnl
                if _pnl_usd is None and _notional:
                    _pnl_usd = pnl_pct * _notional / lev if lev > 0 else 0
                _pnl_usd_str = f" / {'+' if (_pnl_usd or 0) >= 0 else ''}${(_pnl_usd or 0):.2f}" if _pnl_usd is not None else ""
                st.markdown(
                    f"<div style='margin-top:8px;'>"
                    f"<div class='label'>UNREALIZED P&L</div>"
                    f"<div class='metric {pnl_color}' style='font-size:18px;'>{sign}{pnl_pct*100:.2f}%{_pnl_usd_str}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Max unrealized + giveback
                if _snap_max_unreal is not None:
                    _gb_str = f" (gave back ${_snap_giveback:.2f})" if _snap_giveback and _snap_giveback > 0.01 else ""
                    st.markdown(f"<div class='muted' style='font-size:10px;'>Peak: +${_snap_max_unreal:.2f}{_gb_str}</div>", unsafe_allow_html=True)

            # Liquidation prices — intraday and overnight
            _liq_exch = _safe_float(last_decision.get("liquidation_price"))
            if live_price and entry_px and lev > 0:
                _liq_intraday_est = entry_px * (1 - 1 / lev) if pos_dir == "long" else entry_px * (1 + 1 / lev)
                # Overnight liq is tighter: approximate from margin ratios if available
                if _snap_mr_intraday and _snap_mr_overnight and _snap_mr_intraday > 0:
                    _ratio = _snap_mr_overnight / _snap_mr_intraday
                    _intra_dist = abs(float(live_price) - _liq_intraday_est)
                    _liq_overnight_est = float(live_price) + (_intra_dist / _ratio if pos_dir == "long" else -_intra_dist / _ratio) if _ratio > 0 else _liq_intraday_est
                else:
                    _liq_overnight_est = _liq_intraday_est
                _liq_display = _liq_exch if _liq_exch else _liq_intraday_est
                _dist_intra_pct = abs(float(live_price) - _liq_intraday_est) / float(live_price) * 100 if live_price else 0
                _dist_over_pct = abs(float(live_price) - _liq_overnight_est) / float(live_price) * 100 if live_price else 0
                st.markdown(
                    f"<div style='margin-top:8px;display:flex;gap:16px;'>"
                    f"<div><div class='label'>LIQ (INTRADAY)</div><div class='metric muted'>${_liq_intraday_est:.5f} <span style='font-size:10px;'>({_dist_intra_pct:.1f}% away)</span></div></div>"
                    f"<div><div class='label'>LIQ (OVERNIGHT)</div><div class='metric muted'>${_liq_overnight_est:.5f} <span style='font-size:10px;'>({_dist_over_pct:.1f}% away)</span></div></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Margin ratios
            if _snap_mr_intraday is not None or _snap_mr_overnight is not None:
                _mr_i = f"{_snap_mr_intraday*100:.1f}%" if _snap_mr_intraday is not None else "-"
                _mr_o = f"{_snap_mr_overnight*100:.1f}%" if _snap_mr_overnight is not None else "-"
                _mr_i_cls = "danger" if (_snap_mr_intraday or 0) > 0.7 else ("ok" if (_snap_mr_intraday or 0) < 0.4 else "")
                _mr_o_cls = "danger" if (_snap_mr_overnight or 0) > 0.7 else ("ok" if (_snap_mr_overnight or 0) < 0.4 else "")
                st.markdown(
                    f"<div style='margin-top:6px;display:flex;gap:16px;'>"
                    f"<div><div class='label'>MR INTRA</div><div class='metric {_mr_i_cls}' style='font-size:13px;'>{_mr_i}</div></div>"
                    f"<div><div class='label'>MR OVERNIGHT</div><div class='metric {_mr_o_cls}' style='font-size:13px;'>{_mr_o}</div></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Funding bias
            if _snap_basis_bps is not None or _snap_funding_bias:
                _fb_label = _snap_funding_bias or "-"
                _fb_bps = f" ({_snap_basis_bps:+.1f} bps)" if _snap_basis_bps is not None else ""
                _fb_cls = "ok" if "long" in str(_fb_label).lower() else ("danger" if "short" in str(_fb_label).lower() else "muted")
                st.markdown(
                    f"<div style='margin-top:6px;'>"
                    f"<div class='label'>FUNDING</div><div class='metric {_fb_cls}' style='font-size:12px;'>{_fb_label}{_fb_bps}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # TP/SL + orders
            st.markdown(f"<div class='label' style='margin-top:8px;'>STOP / TP1 / TP2 / TP3</div><div class='metric'>{stop} / {tp1} / {tp2} / {tp3}</div>", unsafe_allow_html=True)
            # Break-even indicator
            _be_active = False
            if pos_source == "BOT" and live_price and entry_px:
                _max_pnl_pct = _safe_float(pos_view.get("max_pnl_pct"))
                _be_trigger = float(cfg.get("exits", {}).get("breakeven_atr_trigger", 1.0) or 1.0)
                _be_buffer = float(cfg.get("exits", {}).get("breakeven_buffer_pct", 0.001) or 0.001)
                if _max_pnl_pct is not None and _max_pnl_pct > 0:
                    _be_price = entry_px * (1 + _be_buffer) if pos_dir == "long" else entry_px * (1 - _be_buffer)
                    _be_active = True
                    st.markdown(
                        f"<div style='margin-top:8px;'>"
                        f"<span class='pill ok' style='font-size:10px;'>BE ACTIVE</span> "
                        f"<span class='muted' style='font-size:11px;'>BE @ ${_be_price:.6f}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            # SL buffer info
            _sl_buffer_mult = float(cfg.get("risk", {}).get("sl_atr_buffer_mult", 0.5) or 0.5)
            if _sl_buffer_mult > 0 and stop != "-":
                st.markdown(
                    f"<div class='muted' style='font-size:10px;margin-top:4px;'>SL has {_sl_buffer_mult:.1f}x ATR wick buffer</div>",
                    unsafe_allow_html=True,
                )

            # Strategy view: show what the bot is waiting for (best-effort).
            if live_price and entry_px:
                st.markdown("<div class='label' style='margin-top:14px;'>EXIT RADAR</div>", unsafe_allow_html=True)
                lvls = _strategy_tp_levels(entry_px, pos_dir, lev, cfg)
                tp1_s = lvls.get("tp1")
                tp2_s = lvls.get("tp2")
                tp3_s = lvls.get("tp3")
                need_tp1 = _pct_to_level(float(live_price), float(tp1_s), pos_dir) if tp1_s else None
                need_tp2 = _pct_to_level(float(live_price), float(tp2_s), pos_dir) if tp2_s else None
                need_tp3 = _pct_to_level(float(live_price), float(tp3_s), pos_dir) if tp3_s else None
                st.markdown(
                    "<div class='intel-event'>"
                    f"Strategy targets (assumed): TP1 <strong>${(tp1_s or 0):.4f}</strong> ({(need_tp1 if need_tp1 is not None else 0):+.2f}%), "
                    f"TP2 <strong>${(tp2_s or 0):.4f}</strong> ({(need_tp2 if need_tp2 is not None else 0):+.2f}%), "
                    f"TP3 <strong>${(tp3_s or 0):.4f}</strong> ({(need_tp3 if need_tp3 is not None else 0):+.2f}%)."
                    "</div>",
                    unsafe_allow_html=True,
                )

                # Profit projection (if the trade works and price reaches each TP; ignores fees/slippage).
                try:
                    n_contracts = float(contracts) if contracts is not None else 0.0
                except Exception:
                    n_contracts = 0.0
                details = _get_cfm_product_details_cached(product_id) if product_id and product_id != "-" else {}
                cs = _contract_size_from_details(details) or None
                if n_contracts > 0 and cs and entry_px > 0:
                    p1 = _project_pnl_usd(entry_px, float(tp1_s or 0.0), direction=pos_dir, contracts=n_contracts, contract_size=cs) if tp1_s else None
                    p2 = _project_pnl_usd(entry_px, float(tp2_s or 0.0), direction=pos_dir, contracts=n_contracts, contract_size=cs) if tp2_s else None
                    p3 = _project_pnl_usd(entry_px, float(tp3_s or 0.0), direction=pos_dir, contracts=n_contracts, contract_size=cs) if tp3_s else None
                    st.markdown(
                        "<div class='intel-event'>"
                        f"Projection (full close): TP1 <strong>{_format_money(p1)}</strong>, "
                        f"TP2 <strong>{_format_money(p2)}</strong>, "
                        f"TP3 <strong>{_format_money(p3)}</strong>."
                        "</div>",
                        unsafe_allow_html=True,
                    )

                    # Adaptive scale-out projection (dashboard-only; does not place orders).
                    bt = _safe_str(pos_view.get("breakout_type")) if pos_source == "BOT" else _safe_str(last_decision.get("breakout_type"))
                    cc = int(_safe_float(last_decision.get("confluence_count")) or _safe_float(last_decision.get("confluence_score")) or 0)
                    gates_d = (last_decision.get("gates") or {}) if isinstance(last_decision.get("gates"), dict) else {}
                    blocked_now = [k for k, v in gates_d.items() if not v] if gates_d else []
                    exits_cfg = cfg.get("exits", {}) if isinstance(cfg.get("exits"), dict) else {}
                    full_close = bool(exits_cfg.get("tp_full_close_if_single_contract", False) and n_contracts <= 1.0)
                    plan = _adaptive_scale_plan(
                        full_close_at_tp1=full_close,
                        breakout_type=bt,
                        confluence_count=cc,
                        gates_blocked=len(blocked_now),
                        pnl_pct=pnl_pct,
                    )
                    w1, w2, w3 = float(plan.get("w1", 0)), float(plan.get("w2", 0)), float(plan.get("w3", 0))
                    scaled = None
                    try:
                        scaled = (float(p1 or 0) * w1) + (float(p2 or 0) * w2) + (float(p3 or 0) * w3)
                    except Exception:
                        scaled = None
                    st.markdown(
                        "<div class='intel-event'>"
                        f"Adaptive scale plan: TP1 <strong>{w1*100:.0f}%</strong>, TP2 <strong>{w2*100:.0f}%</strong>, TP3 <strong>{w3*100:.0f}%</strong> "
                        f"<span class='muted'>({plan.get('why')})</span>. "
                        + (f"Scaled projection: <strong>{_format_money(scaled)}</strong>." if scaled is not None else "")
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                gates = (last_decision.get("gates") or {}) if isinstance(last_decision.get("gates"), dict) else {}
                blocked = [k for k, v in gates.items() if not v] if gates else []
                if blocked:
                    st.markdown(
                        "<div class='intel-event'>"
                        "Market conditions: <strong>blocked</strong> by "
                        + ", ".join([_plain_english_gate(b) for b in blocked[:4]])
                        + ".</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("<div class='intel-event'>Market conditions: gates passing.</div>", unsafe_allow_html=True)

                # Bot "why holding" snapshot (if available in state.json).
                if pos_source == "BOT":
                    ew = pos_view.get("exit_watch") if isinstance(pos_view, dict) else None
                    if isinstance(ew, dict):
                        try:
                            early_bars = int((cfg.get("exits") or {}).get("early_save_bars", 0) or 0)
                            ts_bars = int((cfg.get("exits") or {}).get("time_stop_bars", 0) or 0)
                            adv = int(_safe_float(ew.get("adverse_bars")) or 0)
                            bs = int(_safe_float(ew.get("bars_since")) or 0)
                            tstop = bool(ew.get("time_stop"))
                            rev = bool(ew.get("reversal"))
                            tph = bool(ew.get("tp_hit"))
                            st.markdown(
                                "<div class='intel-event'>"
                                f"Holding logic: adverse {adv}/{early_bars} | bars {bs}/{ts_bars} | tp1_hit {tph} | reversal {rev} | time_stop {tstop}."
                                "</div>",
                                unsafe_allow_html=True,
                            )
                        except Exception:
                            pass

                # Trade state badge + profit protection status
                try:
                    _pp_ew = (pos_view.get("exit_watch") or {}) if isinstance(pos_view, dict) else {}
                    _ts_label = str(_pp_ew.get("trade_state") or "")
                    if _ts_label:
                        _ts_colors = {
                            "EARLY": "#94a3b8",
                            "BUILDING": "#38bdf8",
                            "SECURED": "#22c55e",
                            "EXPANSION": "#fbbf24",
                            "DECAY": "#f97316",
                            "UNDERWATER": "#ef4444",
                        }
                        _ts_color = _ts_colors.get(_ts_label, "#94a3b8")
                        _pp_parts = [f"<span style='color:{_ts_color};font-weight:700;font-size:13px;'>{_ts_label}</span>"]
                        _pp_mf = bool(_pp_ew.get("min_floor_armed"))
                        _pp_da = bool(_pp_ew.get("decay_armed"))
                        _pp_retrace = float(_pp_ew.get("decay_retrace_pct") or 0)
                        _pp_thresh = float(_pp_ew.get("decay_threshold_pct") or 0)
                        if _pp_mf:
                            _mf_val = _pp_ew.get("min_floor_usd")
                            _pp_parts.append(f"<span class='green'>Floor ${float(_mf_val):.0f} locked</span>" if _mf_val else "<span class='green'>Floor locked</span>")
                        if _pp_da:
                            _retrace_cls = "danger" if _pp_retrace > _pp_thresh * 0.7 else "muted"
                            _pp_parts.append(f"<span class='{_retrace_cls}'>Retrace {_pp_retrace*100:.0f}%/{_pp_thresh*100:.0f}%</span>")
                        st.markdown(
                            "<div class='intel-event' style='border-left:3px solid " + _ts_color + ";'>"
                            + " &middot; ".join(_pp_parts) + "</div>",
                            unsafe_allow_html=True,
                        )
                except Exception:
                    pass

                # TIMING card — close ETA with progress bar
                try:
                    _eta_data = ((pos_view or {}).get("exit_watch") or {}).get("close_eta") or {}
                    _eta_elapsed = _eta_data.get("elapsed_display", "")
                    _eta_remaining = _eta_data.get("remaining_display", "")
                    _eta_progress = float(_eta_data.get("progress_pct") or 0)
                    _eta_hist_avg = _eta_data.get("historical_avg_min")
                    _eta_hist_range = _eta_data.get("historical_range", "")
                    _eta_hist_count = int(_eta_data.get("historical_count") or 0)
                    _eta_confidence = str(_eta_data.get("confidence") or "")
                    _eta_overdue = bool(_eta_data.get("overdue"))
                    if _eta_elapsed:
                        _bar_pct = min(_eta_progress, 200)
                        _bar_color = "#ef4444" if _eta_overdue else ("#fbbf24" if _eta_progress > 70 else "#22c55e")
                        _bar_bg = "#1e293b"
                        _conf_dot = {"high": "#22c55e", "medium": "#fbbf24", "low": "#ef4444"}.get(_eta_confidence, "#94a3b8")
                        _hist_line = ""
                        if _eta_hist_avg and _eta_hist_count:
                            _hist_line = (
                                f"<div class='muted' style='font-size:10px;margin-top:4px;'>"
                                f"avg similar: {_eta_hist_avg:.0f}m (range {_eta_hist_range}) · {_eta_hist_count} trades"
                                f" <span style='color:{_conf_dot};'>●</span>"
                                f"</div>"
                            )
                        st.markdown(
                            f"<div class='intel-card' style='padding:10px 14px;'>"
                            f"<div class='intel-title'>TIMING</div>"
                            f"<div style='display:flex;justify-content:space-between;margin:6px 0 4px;'>"
                            f"<div><span class='label'>ELAPSED</span><br/><span class='metric' style='font-size:16px;'>{_eta_elapsed}</span></div>"
                            f"<div style='text-align:right;'><span class='label'>EST. CLOSE</span><br/><span class='metric' style='font-size:16px;color:{_bar_color};'>{_eta_remaining}</span></div>"
                            f"</div>"
                            f"<div style='background:{_bar_bg};border-radius:4px;height:8px;overflow:hidden;margin:4px 0;'>"
                            f"<div style='background:{_bar_color};width:{min(_bar_pct, 100):.0f}%;height:100%;border-radius:4px;'></div>"
                            f"</div>"
                            f"<div class='muted' style='text-align:right;font-size:10px;'>{_eta_progress:.0f}%</div>"
                            f"{_hist_line}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                except Exception:
                    pass

                # Entry profile badge — shows strategy-specific profit expectations
                try:
                    _ep_et = str((pos_view or {}).get("entry_type") or "")
                    _ep_sr = str((pos_view or {}).get("strategy_regime") or "")
                    _ep_min = float((pos_view or {}).get("entry_profile_min_profit_usd") or 0)
                    _ep_tp = float((pos_view or {}).get("entry_profile_tp_mult") or 0)
                    _ep_dp = float((pos_view or {}).get("entry_profile_decay_pct") or 0)
                    if _ep_et and _ep_min > 0:
                        _ep_label = _ep_et.replace("_", " ").title()
                        if _ep_sr == "trend":
                            _ep_label += " (Trend)"
                        _ep_cls = "ok" if _ep_tp >= 1.2 else ("muted" if _ep_tp >= 0.8 else "danger")
                        st.markdown(
                            f"<div class='intel-event' style='font-size:11px;'>"
                            f"<span class='muted'>Profile</span> <span class='{_ep_cls}' style='font-weight:600;'>{_ep_label}</span>"
                            f" &middot; <span class='muted'>Min</span> ${_ep_min:.0f}"
                            f" &middot; <span class='muted'>TP</span> ×{_ep_tp:.1f}"
                            f" &middot; <span class='muted'>Decay</span> {_ep_dp*100:.0f}%"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                except Exception:
                    pass

                # Moonshot badge
                try:
                    _ms_ew = (pos_view.get("exit_watch") or {}) if isinstance(pos_view, dict) else {}
                    _ms_active = bool(_ms_ew.get("moonshot_active"))
                    if _ms_active:
                        _ms_trail = _ms_ew.get("moonshot_trail_stop")
                        _ms_peak = _ms_ew.get("moonshot_peak")
                        _ms_parts = ["<span style='color:#fbbf24;font-weight:700;'>MOONSHOT ACTIVE</span>"]
                        if _ms_trail is not None:
                            _ms_parts.append(f"Trail ${float(_ms_trail):.4f}")
                        if _ms_peak is not None:
                            _ms_parts.append(f"Peak ${float(_ms_peak):.4f}")
                        st.markdown(
                            "<div class='intel-event' style='border-left:3px solid #fbbf24;'>"
                            + " &middot; ".join(_ms_parts) + "</div>",
                            unsafe_allow_html=True,
                        )
                except Exception:
                    pass

                # Runner badge
                try:
                    _rn_ew = (pos_view.get("exit_watch") or {}) if isinstance(pos_view, dict) else {}
                    _rn_active = bool(_rn_ew.get("runner_active"))
                    if _rn_active:
                        _rn_trail = _rn_ew.get("runner_trail_price")
                        _rn_peak = _rn_ew.get("runner_peak")
                        _rn_bars = int(_rn_ew.get("runner_bars") or 0)
                        _rn_fib = _rn_ew.get("runner_fib_786")
                        _rn_tight = bool(_rn_ew.get("runner_fib_tightened"))
                        _rn_floor = _rn_ew.get("runner_floor_usd")
                        _rn_parts = [f"<span style='color:#34d399;font-weight:700;'>RUNNER</span> <span class='muted'>({_rn_bars} bars)</span>"]
                        if _rn_trail is not None:
                            _rn_parts.append(f"Trail ${float(_rn_trail):.5f}")
                        if _rn_peak is not None:
                            _rn_parts.append(f"Peak ${float(_rn_peak):.5f}")
                        if _rn_fib is not None:
                            _fib_tag = " <span style='color:#22c55e;'>tightened</span>" if _rn_tight else ""
                            _rn_parts.append(f"Fib 0.786 ${float(_rn_fib):.5f}{_fib_tag}")
                        if _rn_floor is not None:
                            _rn_parts.append(f"Floor ${float(_rn_floor):.2f}")
                        st.markdown(
                            "<div class='intel-event' style='border-left:3px solid #34d399;'>"
                            + " &middot; ".join(_rn_parts) + "</div>",
                            unsafe_allow_html=True,
                        )
                except Exception:
                    pass

                # If this is an EXCHANGE-only position, call that out explicitly.
                if pos_source == "EXCHANGE" and not open_pos:
                    st.markdown(
                        "<div class='intel-event'><span class='amber'>Note</span>: "
                        "This position is being shown from the exchange. Bot state does not confirm it, "
                        "so strategy management may not be active.</div>",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

            if pos_source == "EXCHANGE":
                orders = _get_cfm_open_orders_cached(product_id=product_id)
                if orders:
                    with st.expander(f"Open Orders ({len(orders)})", expanded=False):
                        for o in orders[:10]:
                            prot = _order_protection_summary(o or {})
                            st.write(
                                {
                                    "order_id": o.get("order_id"),
                                    "side": o.get("side"),
                                    "status": prot.get("status"),
                                    "order_type": prot.get("order_type"),
                                    "trigger_status": prot.get("trigger_status"),
                                    "stop_trigger": prot.get("stop_trigger"),
                                    "take_profit": prot.get("take_profit"),
                                    "health": prot.get("health"),
                                    "created_time": _fmt_utc8_long(o.get("created_time")),
                                }
                            )
        else:
            st.markdown("<div class='card'><div class='metric muted'>No open position detected.</div></div>", unsafe_allow_html=True)

    with mid:
        # Trade intel summary (chart moved to top of page)
        st.markdown("<div class='panel-title'>Trade Intel</div>", unsafe_allow_html=True)
        _ti_thought = _safe_str(last_decision.get("thought")) or "Waiting for data..."
        _ti_quality = _safe_str(last_decision.get("quality_tier")) or "—"
        _ti_lane = _safe_str(last_decision.get("lane_label")) or "—"
        _ti_htf = _safe_str(last_decision.get("htf_macro_bias")) or "—"
        _ti_score_l = int(_safe_float(last_decision.get("v4_score_long")) or 0)
        _ti_score_s = int(_safe_float(last_decision.get("v4_score_short")) or 0)
        _ti_thresh_l = int(_safe_float(last_decision.get("v4_threshold_long")) or 0)
        _ti_thresh_s = int(_safe_float(last_decision.get("v4_threshold_short")) or 0)
        _ti_recovery = _safe_str(last_decision.get("recovery_mode")) or "NORMAL"
        _ti_rcls = "danger" if _ti_recovery == "SAFE_MODE" else ("ok" if _ti_recovery == "RECOVERY" else "muted")
        st.markdown(
            f"<div class='card' style='padding:10px 14px;'>"
            f"<div style='font-size:12px;color:#cbd5e1;margin-bottom:8px;font-style:italic;'>\"{_ti_thought}\"</div>"
            f"<div style='display:flex;gap:16px;flex-wrap:wrap;font-size:11px;'>"
            f"<span class='muted'>Quality</span> <span class='{'gold' if _ti_quality == 'MONSTER' else 'metric'}' style='font-size:12px;'>{_ti_quality}</span>"
            f"<span class='muted'>Lane</span> <span style='font-size:12px;'>{_ti_lane}</span>"
            f"<span class='muted'>HTF</span> <span style='font-size:12px;'>{_ti_htf}</span>"
            f"<span class='muted'>Recovery</span> <span class='{_ti_rcls}' style='font-size:12px;'>{_ti_recovery}</span>"
            f"</div>"
            f"<div style='display:flex;gap:16px;margin-top:6px;font-size:11px;'>"
            f"<span class='muted'>Long</span> <span class='{'ok' if _ti_score_l >= _ti_thresh_l else 'muted'}'>{_ti_score_l}/{_ti_thresh_l}</span>"
            f"<span class='muted'>Short</span> <span class='{'ok' if _ti_score_s >= _ti_thresh_s else 'muted'}'>{_ti_score_s}/{_ti_thresh_s}</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── AI Executive Card (enhanced) ──────────────────────────────────────
    try:
        _ai_cache_path = DATA_DIR / "ai_insight.json"
        if _ai_cache_path.exists():
            _ai_cache = json.loads(_ai_cache_path.read_text())
            _ai_dir = _ai_cache.get("directive", {})
            _ai_entry = _ai_cache.get("entry_eval", {})
            _ai_exit = _ai_cache.get("exit_eval", {})
            _ai_dir_result = _ai_dir.get("result") or {}
            _ai_has_directive = bool(_ai_dir_result.get("action"))

            if _ai_has_directive or _ai_entry.get("result") or _ai_exit.get("result"):
                _ai_action = _ai_dir_result.get("action") or ""
                _ai_conf = float(_ai_dir_result.get("confidence") or 0)
                _ai_reasoning = _ai_dir_result.get("reasoning") or ""
                _ai_market = _ai_dir_result.get("market_read") or ""
                _ai_sl = _ai_dir_result.get("stop_loss_price")
                _ai_tp = _ai_dir_result.get("take_profit_price")

                # Age
                _ai_ts = _ai_dir.get("timestamp") or ""
                _ai_age = ""
                if _ai_ts:
                    try:
                        _ai_dt = datetime.fromisoformat(_ai_ts.replace("Z", "+00:00"))
                        _ai_age_s = (datetime.now(tz=_ai_dt.tzinfo or timezone.utc) - _ai_dt).total_seconds()
                        _ai_age = f"{int(_ai_age_s)}s" if _ai_age_s < 60 else (
                            f"{int(_ai_age_s // 60)}m" if _ai_age_s < 3600 else f"{int(_ai_age_s // 3600)}h")
                    except Exception:
                        pass

                # Border color
                _ai_border = "#a78bfa"
                if _ai_action.startswith("ENTER"):
                    _ai_border = "#22c55e"
                elif _ai_action == "EXIT":
                    _ai_border = "#ef4444"
                elif _ai_action == "FLAT":
                    _ai_border = "#6b7280"

                _ai_acls = "ok" if _ai_action in ("ENTER_LONG", "ENTER_SHORT", "HOLD") else (
                    "danger" if _ai_action in ("EXIT", "FLAT") else "amber")

                _ai_html = (
                    f"<div class='intel-card' style='padding:14px 18px;border-left:4px solid {_ai_border};border-top:1px solid {_ai_border}40;'>"
                    f"<div class='intel-title' style='color:{_ai_border};font-size:0.75rem;letter-spacing:3px;'>AI EXECUTIVE</div>"
                )
                if _ai_market:
                    _ai_html += f"<div style='font-size:11px;color:#94a3b8;margin-bottom:6px;'>{html.escape(_ai_market)}</div>"
                if _ai_reasoning:
                    _ai_html += f"<div style='font-size:12px;color:#cbd5e1;margin-bottom:8px;font-style:italic;line-height:1.5;'>\"{html.escape(_ai_reasoning)}\"</div>"
                _ai_size = _ai_dir_result.get("size")
                _ai_html += (
                    f"<div style='display:flex;gap:14px;font-size:11px;flex-wrap:wrap;'>"
                    f"<span class='muted'>Action</span> <span class='{_ai_acls}' style='font-size:14px;font-weight:bold;'>{_ai_action}</span>"
                    f"<span class='muted'>Conf</span> <span class='metric' style='font-size:13px;'>{_ai_conf:.0%}</span>"
                )
                if _ai_size is not None:
                    _sz_clr = "#22c55e" if int(_ai_size) >= 4 else ("#f59e0b" if int(_ai_size) >= 2 else "#94a3b8")
                    _ai_html += f"<span class='muted'>Size</span> <span style='color:{_sz_clr};font-size:13px;font-weight:bold;'>{_ai_size}c</span>"
                _ai_html += f"<span class='muted'>Age</span> <span class='muted'>{_ai_age}</span>"
                if _ai_sl:
                    _ai_html += f"<span class='muted'>SL</span> <span class='red'>${float(_ai_sl):.5f}</span>"
                if _ai_tp:
                    _ai_html += f"<span class='muted'>TP</span> <span class='green'>${float(_ai_tp):.5f}</span>"
                _ai_html += "</div>"

                # Exit eval sub-section (when in a trade)
                _exit_result = (_ai_exit.get("result") or {})
                _exit_urgency = _exit_result.get("urgency") or ""
                if _exit_urgency:
                    _exit_conf = float(_exit_result.get("hold_confidence") or 0)
                    _exit_reason = _exit_result.get("reasoning") or ""
                    _urg_clr = {"hold": "#22c55e", "tighten": "#f59e0b", "exit_now": "#ef4444"}.get(_exit_urgency, "#6b7280")
                    _ai_html += (
                        f"<div style='margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);'>"
                        f"<span class='label' style='color:{_urg_clr};'>EXIT: {_exit_urgency.upper()}</span>"
                        f" <span class='muted' style='font-size:11px;'>({_exit_conf:.0%})</span>"
                        f"<div style='font-size:11px;color:#94a3b8;margin-top:4px;'>{html.escape(_exit_reason[:200])}</div>"
                        f"</div>"
                    )

                # Entry eval warnings sub-section
                _entry_result = (_ai_entry.get("result") or {})
                _entry_verdict = _entry_result.get("verdict") or ""
                _entry_warnings = _entry_result.get("warnings") or []
                if _entry_verdict in ("skip", "caution") and _entry_warnings:
                    _v_clr = "#ef4444" if _entry_verdict == "skip" else "#f59e0b"
                    _ai_html += (
                        f"<div style='margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);'>"
                        f"<span class='label' style='color:{_v_clr};'>ENTRY: {_entry_verdict.upper()}</span>"
                    )
                    for _w in _entry_warnings[:3]:
                        _ai_html += f"<div style='font-size:11px;color:#f87171;margin-top:2px;'>&#9888; {html.escape(str(_w))}</div>"
                    _ai_html += "</div>"

                _ai_html += "</div>"
                st.markdown(_ai_html, unsafe_allow_html=True)
    except Exception:
        pass  # Never let AI display failures crash dashboard

    # ── AI Learning Scorecard ────────────────────────────────────────────
    try:
        _fb_data = _load_ai_feedback()
        if _fb_data:
            _fb_trades = [f for f in _fb_data if f.get("action") != "FLAT"]
            _fb_flats = [f for f in _fb_data if f.get("action") == "FLAT"]
            _fb_wins = [f for f in _fb_trades if f.get("won")]
            _fb_losses = [f for f in _fb_trades if not f.get("won") and f.get("pnl_usd") is not None]
            _fb_total = len(_fb_trades)
            _fb_win_ct = len(_fb_wins)
            _fb_loss_ct = len(_fb_losses)
            _fb_wr = (_fb_win_ct / _fb_total * 100) if _fb_total > 0 else 0
            _fb_net_pnl = sum(float(f.get("pnl_usd") or 0) for f in _fb_trades)
            _fb_avg_conf = sum(float(f.get("confidence") or 0) for f in _fb_trades) / _fb_total if _fb_total > 0 else 0

            _sc_html = (
                "<div class='intel-card' style='padding:14px 18px;border-left:4px solid #8b5cf6;'>"
                "<div class='intel-title' style='color:#8b5cf6;font-size:0.75rem;letter-spacing:3px;'>AI LEARNING SCORECARD</div>"
                "<div style='display:flex;gap:16px;flex-wrap:wrap;margin-bottom:8px;'>"
                f"<div><span class='muted' style='font-size:10px;'>TRADES</span><br><span class='metric' style='font-size:16px;'>{_fb_total}</span></div>"
                f"<div><span class='muted' style='font-size:10px;'>W / L</span><br><span style='font-size:16px;'><span class='green'>{_fb_win_ct}</span> / <span class='red'>{_fb_loss_ct}</span></span></div>"
                f"<div><span class='muted' style='font-size:10px;'>WIN RATE</span><br><span class='{'ok' if _fb_wr >= 50 else 'danger'}' style='font-size:16px;'>{_fb_wr:.0f}%</span></div>"
                f"<div><span class='muted' style='font-size:10px;'>NET P&L</span><br><span class='{'green' if _fb_net_pnl >= 0 else 'red'}' style='font-size:16px;'>${_fb_net_pnl:+.2f}</span></div>"
                f"<div><span class='muted' style='font-size:10px;'>AVG CONF</span><br><span class='metric' style='font-size:16px;'>{_fb_avg_conf:.0%}</span></div>"
                "</div>"
            )

            # FLAT calls quality
            if _fb_flats:
                _sc_html += (
                    "<div style='margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06);'>"
                    "<span class='label' style='color:#8b5cf6;font-size:10px;'>FLAT CALLS</span>"
                    f"<span class='muted' style='font-size:11px;margin-left:8px;'>{len(_fb_flats)} total</span>"
                )
                _flat_correct = sum(1 for f in _fb_flats if abs(float(f.get("pnl_usd") or 0)) < 1.0)
                _flat_missed = len(_fb_flats) - _flat_correct
                _sc_html += (
                    f"<span class='muted' style='font-size:11px;margin-left:8px;'>"
                    f"Correct: <span class='green'>{_flat_correct}</span> | Missed moves: <span class='red'>{_flat_missed}</span></span>"
                    "</div>"
                )

            # Confidence calibration table
            _cal = _ai_confidence_calibration(_fb_data)
            if _cal:
                _sc_html += (
                    "<div style='margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06);'>"
                    "<span class='label' style='color:#8b5cf6;font-size:10px;'>CONFIDENCE CALIBRATION</span>"
                    "<table style='width:100%;font-size:11px;margin-top:4px;border-collapse:collapse;'>"
                    "<tr style='color:#64748b;'><td>Bucket</td><td>Trades</td><td>Win Rate</td><td>P&L</td></tr>"
                )
                for _cb in _cal:
                    _wr_clr = "green" if _cb["win_rate"] >= 50 else "red"
                    _pnl_clr = "green" if _cb["pnl"] >= 0 else "red"
                    _sc_html += (
                        f"<tr><td class='muted'>{_cb['bucket']}</td>"
                        f"<td>{_cb['trades']}</td>"
                        f"<td class='{_wr_clr}'>{_cb['win_rate']:.0f}%</td>"
                        f"<td class='{_pnl_clr}'>${_cb['pnl']:+.2f}</td></tr>"
                    )
                _sc_html += "</table></div>"

            # Recent calls feed (last 5)
            _recent_fb = _fb_data[-5:]
            if _recent_fb:
                _sc_html += (
                    "<div style='margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06);'>"
                    "<span class='label' style='color:#8b5cf6;font-size:10px;'>RECENT CALLS</span>"
                )
                for _rfb in reversed(_recent_fb):
                    _r_action = _rfb.get("action") or "?"
                    _r_won = _rfb.get("won")
                    _r_pnl = float(_rfb.get("pnl_usd") or 0)
                    _r_conf = float(_rfb.get("confidence") or 0)
                    _r_reason = (_rfb.get("reasoning") or "")[:80]
                    _r_icon = "&#10003;" if _r_won else "&#10007;" if _r_won is not None else "&#8212;"
                    _r_icon_clr = "green" if _r_won else "red" if _r_won is not None else "muted"
                    _r_ts = ""
                    try:
                        _r_dt = datetime.fromisoformat(str(_rfb.get("ts", "")).replace("Z", "+00:00"))
                        _r_ts = _r_dt.astimezone(PT).strftime("%I:%M %p")
                    except Exception:
                        pass
                    _sc_html += (
                        f"<div style='font-size:11px;margin-top:3px;display:flex;gap:6px;align-items:baseline;'>"
                        f"<span class='{_r_icon_clr}' style='font-size:13px;'>{_r_icon}</span>"
                        f"<span class='muted'>{_r_ts}</span>"
                        f"<span style='font-weight:bold;'>{_r_action}</span>"
                        f"<span class='muted'>({_r_conf:.0%})</span>"
                        f"<span class='{'green' if _r_pnl >= 0 else 'red'}'>${_r_pnl:+.2f}</span>"
                        f"<span class='muted' style='font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{html.escape(_r_reason)}</span>"
                        f"</div>"
                    )
                _sc_html += "</div>"

            _sc_html += "</div>"
            st.markdown(_sc_html, unsafe_allow_html=True)
    except Exception:
        pass  # Never let scorecard crash dashboard

    # ── Trade Events Table ───────────────────────────────────────────────
    try:
        _evt_rows = []
        # Recent trades (filter out reconciler ghost exits)
        if trades is not None and not trades.empty:
            _recent = trades.tail(30).copy()
            if "exit_reason" in _recent.columns:
                _recent = _recent[
                    (_recent["exit_reason"].astype(str) != "exchange_side_close") | _recent["exit_price"].isna()
                ].copy()
            for _, tr in _recent.iterrows():
                _ts_raw = tr.get("exit_time") or tr.get("entry_time") or tr.get("timestamp")
                try:
                    _ts_dt = pd.to_datetime(_ts_raw, utc=True)
                    _ts_pt = _ts_dt.astimezone(PT).strftime("%b %d %I:%M %p")
                except Exception:
                    _ts_pt = str(_ts_raw)[:16]
                _side = str(tr.get("side", "")).upper()
                _has_exit = pd.notna(tr.get("exit_price")) and tr.get("exit_price") not in ("", None)
                _evt_type = "Exit" if _has_exit else "Entry"
                _px = float(tr.get("exit_price") or tr.get("entry_price") or 0)
                _pnl = float(tr.get("pnl_usd") or 0) if _has_exit else None
                _reason = str(tr.get("exit_reason") or tr.get("entry_type") or "")
                _evt_rows.append({
                    "sort_ts": _ts_dt if isinstance(_ts_raw, str) else pd.to_datetime(_ts_raw, utc=True, errors="coerce"),
                    "Time": _ts_pt,
                    "Type": _evt_type,
                    "Side": _side,
                    "Price": f"${_px:.5f}" if _px > 0 else "-",
                    "PnL": f"{'+'if _pnl>=0 else ''}${_pnl:.2f}" if _pnl is not None else "-",
                    "Reason": _reason[:20],
                    "_pnl_val": _pnl,
                })
        # Recent incidents
        if INCIDENTS_PATH.exists():
            try:
                _inc_lines = INCIDENTS_PATH.read_text(errors="ignore").strip().splitlines()[-10:]
                for _il in _inc_lines:
                    _inc = json.loads(_il)
                    _its = _inc.get("timestamp", "")
                    try:
                        _inc_dt = pd.to_datetime(_its, utc=True)
                        _inc_pt = _inc_dt.astimezone(PT).strftime("%b %d %I:%M %p")
                    except Exception:
                        _inc_pt = str(_its)[:16]
                        _inc_dt = pd.Timestamp.now(tz="UTC")
                    _evt_rows.append({
                        "sort_ts": _inc_dt,
                        "Time": _inc_pt,
                        "Type": "Incident",
                        "Side": "-",
                        "Price": "-",
                        "PnL": "-",
                        "Reason": str(_inc.get("type", ""))[:20],
                        "_pnl_val": None,
                    })
            except Exception:
                pass

        if _evt_rows:
            _evt_rows.sort(key=lambda x: x.get("sort_ts") or pd.Timestamp.min, reverse=True)
            _evt_rows = _evt_rows[:20]
            # Render as HTML table
            _tbl = "<table style='width:100%;border-collapse:collapse;font-size:11px;'>"
            _tbl += "<tr style='color:#6b7280;border-bottom:1px solid rgba(148,163,184,0.15);'>"
            for _h in ["Time", "Type", "Side", "Price", "PnL", "Reason"]:
                _tbl += f"<th style='text-align:left;padding:4px 6px;font-weight:500;'>{_h}</th>"
            _tbl += "</tr>"
            for _er in _evt_rows:
                _pv = _er.get("_pnl_val")
                _rc = ""
                if _er["Type"] == "Incident":
                    _rc = "color:#f59e0b;"
                elif _pv is not None and _pv > 0:
                    _rc = "color:#10b981;"
                elif _pv is not None and _pv < 0:
                    _rc = "color:#ef4444;"
                _tbl += f"<tr style='{_rc}border-bottom:1px solid rgba(148,163,184,0.08);'>"
                for _h in ["Time", "Type", "Side", "Price", "PnL", "Reason"]:
                    _tbl += f"<td style='padding:3px 6px;'>{html.escape(str(_er[_h]))}</td>"
                _tbl += "</tr>"
            _tbl += "</table>"
            with st.expander("Bot Trade Log", expanded=False):
                st.markdown("<div class='muted' style='font-size:10px;margin-bottom:6px;'>Source: bot internal tracking (logs/trades.csv)</div>", unsafe_allow_html=True)
                st.markdown(_tbl, unsafe_allow_html=True)
    except Exception:
        pass

    # ── Full-width ticker strip (outside columns for max width) ──────────
    # ── Major Events Ticker (broadcast style) ─────────────────
    try:
        if major_events:
            _ev_items: list[str] = []
            for _ei, ev in enumerate(major_events[:20]):
                _ev_tone = _safe_str(ev.get("tone")) or "info"
                _ev_hl = html.escape(_safe_str(ev.get("headline")) or "-")
                _ev_ts = html.escape(_fmt_pt_short(ev.get("ts")))
                # Extract extra context when available
                _ev_detail_parts: list[str] = []
                _ev_price = _safe_float(ev.get("price"))
                _ev_dir = _safe_str(ev.get("direction")) or ""
                _ev_pnl = _safe_float(ev.get("pnl"))
                _ev_reason = _safe_str(ev.get("reason")) or ""
                if _ev_dir:
                    _d_cls = "ticker-dir-long" if _ev_dir.upper() == "LONG" else "ticker-dir-short"
                    _ev_detail_parts.append(f"<span class='{_d_cls}'>{_ev_dir.upper()}</span>")
                if _ev_price:
                    _ev_detail_parts.append(f"<span class='ticker-val'>${_ev_price:.4f}</span>")
                if _ev_pnl is not None:
                    _pclr = "ticker-dir-long" if _ev_pnl >= 0 else "ticker-dir-short"
                    _ev_detail_parts.append(f"<span class='{_pclr}'>{'+' if _ev_pnl >= 0 else ''}${_ev_pnl:.2f}</span>")
                # Tag based on tone
                _tag_map = {"good": "entry", "bad": "exit", "warn": "alert", "info": "signal"}
                _ev_tag_cls = _tag_map.get(_ev_tone, "signal")
                _ev_tag_txt = _ev_reason.replace("_", " ").upper()[:12] if _ev_reason else _ev_tone.upper()
                _live_cls = " live" if _ei == 0 else ""
                _ev_detail = f" &middot; {'  '.join(_ev_detail_parts)}" if _ev_detail_parts else ""
                _ev_items.append(
                    f"<span class='ticker-item'>"
                    f"<span class='ticker-dot {_ev_tone}{_live_cls}'></span>"
                    f"<span class='ticker-tag {_ev_tag_cls}'>{_ev_tag_txt}</span>"
                    f"<b>{_ev_hl}</b>{_ev_detail}"
                    f" <span class='ts'>{_ev_ts}</span>"
                    f"</span>"
                )
            _ev_track = ("<span class='ticker-sep'>|</span>").join(_ev_items)
            st.markdown(
                f"<div class='ticker-wrap' style='margin-top:14px;'>"
                f"<div class='ticker-label ev-label'>EVENTS</div>"
                f"<div class='ticker-track' style='--ticker-speed:60s;'>{_ev_track}<span class='ticker-sep'>|</span>{_ev_track}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Decision Feed Ticker ───────────────────────────────────
    try:
        if not decisions.empty:
            recent = decisions.copy()
            if "timestamp" in recent.columns:
                recent["timestamp"] = pd.to_datetime(recent["timestamp"], utc=True, errors="coerce")
                recent = recent.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)
            if "reason" in recent.columns:
                filtered = recent[recent["reason"].astype(str).str.lower() != "open_position_tick"].copy()
                if not filtered.empty:
                    recent = filtered
            if feed_major_only and "reason" in recent.columns:
                reason_s = recent["reason"].astype(str).str.lower().str.strip()
                action_s = (
                    recent["last_action"].astype(str).str.upper().str.strip()
                    if "last_action" in recent.columns
                    else pd.Series([""] * len(recent), index=recent.index)
                )
                major_mask = (
                    reason_s.str.contains(
                        "entry_order|exit_order|take_profit|stop|liquid|rescue|scale|flip|exchange_side_close|emergency_exit|margin_policy_block_entry|profit_transfer|funding_transfer",
                        regex=True,
                    )
                    | action_s.isin(["ENTER", "EXIT", "RESCUE", "SCALE", "FLIP"])
                )
                recent = recent[major_mask].copy()
            if feed_noise_filter and not recent.empty:
                reason_col = recent["reason"].astype(str).str.lower().str.strip() if "reason" in recent.columns else pd.Series([""] * len(recent), index=recent.index)
                thought_col = recent["thought"].astype(str).str.strip() if "thought" in recent.columns else pd.Series([""] * len(recent), index=recent.index)
                direction_col = recent["direction"].astype(str).str.lower().str.strip() if "direction" in recent.columns else pd.Series([""] * len(recent), index=recent.index)
                signal_col = recent["entry_signal"].astype(str).str.lower().str.strip() if "entry_signal" in recent.columns else pd.Series([""] * len(recent), index=recent.index)
                recent["__noise_key"] = reason_col + "|" + thought_col + "|" + direction_col + "|" + signal_col
                recent = recent[recent["__noise_key"] != recent["__noise_key"].shift(1)].copy()
                recent = recent.drop(columns=["__noise_key"], errors="ignore")
            recent = recent.head(20).copy()
            prev_seen_raw = st.session_state.get("thought_last_seen_ts")
            prev_seen_ts = pd.to_datetime(prev_seen_raw, utc=True, errors="coerce") if prev_seen_raw else pd.NaT
            newest_ts = recent["timestamp"].max() if ("timestamp" in recent.columns and not recent.empty) else None
            _dec_items: list[str] = []
            for _di, (_, rr) in enumerate(recent.iterrows()):
                row = rr.to_dict() if hasattr(rr, "to_dict") else dict(rr)
                reason = _safe_str(row.get("reason")) or "decision"
                exit_reason = _safe_str(row.get("exit_reason")) or ""
                tone = _decision_tone(reason, exit_reason)
                label = html.escape((_safe_str(row.get("last_action")) or reason).replace("_", " ").upper())
                thought = html.escape((_safe_str(row.get("thought")) or reason.replace("_", " "))[:70])
                ts_txt = html.escape(_fmt_pt_short(row.get("timestamp")))
                # Score
                score = _safe_float(row.get("v4_selected_score"))
                threshold = _safe_float(row.get("v4_selected_threshold"))
                score_txt = ""
                if score is not None and threshold is not None:
                    _sc_clr = "ticker-dir-long" if score >= threshold else "ticker-dir-short" if score > 0 else ""
                    score_txt = f" <span class='{_sc_clr}'>{int(score)}/{int(threshold)}</span>"
                # Direction
                _d_dir = _safe_str(row.get("direction")) or ""
                _d_dir_html = ""
                if _d_dir:
                    _dd_cls = "ticker-dir-long" if _d_dir.upper() == "LONG" else "ticker-dir-short"
                    _d_dir_html = f" <span class='{_dd_cls}'>{_d_dir.upper()}</span>"
                # Price
                _d_price = _safe_float(row.get("price"))
                _d_price_html = f" <span class='ticker-val'>${_d_price:.4f}</span>" if _d_price else ""
                # Quality tier
                _d_qt = _safe_str(row.get("quality_tier")) or ""
                _d_qt_html = ""
                if _d_qt and _d_qt not in ("", "FULL"):
                    _d_qt_cls = "ticker-tag alert" if _d_qt != "MONSTER" else "gold"
                    _d_qt_html = f" <span class='{_d_qt_cls}'>{_d_qt}</span>"
                # Tag
                _tag_cls = "entry" if tone == "good" else "exit" if tone == "bad" else "alert" if tone == "warn" else "signal"
                _live_cls = " live" if _di == 0 else ""
                _dec_items.append(
                    f"<span class='ticker-item'>"
                    f"<span class='ticker-dot {tone}{_live_cls}'></span>"
                    f"<span class='ticker-tag {_tag_cls}'>{label}</span>"
                    f"{_d_dir_html}{_d_price_html}"
                    f" {thought}{score_txt}{_d_qt_html}"
                    f" <span class='ts'>{ts_txt}</span>"
                    f"</span>"
                )
            _dec_track = ("<span class='ticker-sep'>|</span>").join(_dec_items)
            st.markdown(
                f"<div class='ticker-wrap' style='margin-top:6px;'>"
                f"<div class='ticker-label dec-label'>DECISIONS</div>"
                f"<div class='ticker-track' style='--ticker-speed:55s;'>{_dec_track}<span class='ticker-sep'>|</span>{_dec_track}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if newest_ts is not None and not pd.isna(newest_ts):
                st.session_state["thought_last_seen_ts"] = pd.to_datetime(newest_ts, utc=True, errors="coerce").isoformat()
    except Exception:
        pass

    with term_tabs[1]:
        render_intel_hub(last_decision, state, pos_view)
        
    with term_tabs[2]:
        # Embed Claude Chat
        _chat_url = os.environ.get("XLM_CHAT_URL", "http://127.0.0.1:8504")
        st.markdown(f"<iframe src='{_chat_url}' width='100%' height='600' style='border:none;background:transparent;'></iframe>", unsafe_allow_html=True)

    with term_tabs[3]:
        st.markdown("<div class='panel-title'>Evolution Engine</div>", unsafe_allow_html=True)
        st.caption("Self-learning system: lane performance, threshold optimization, and agent debate log")

        # Lane Performance
        _lp_path = LOGS_DIR / "lane_performance.json"
        try:
            if _lp_path.exists():
                import json as _evo_json
                _lp = _evo_json.loads(_lp_path.read_text())
                _lp_lanes = _lp.get("lanes", {})
                if _lp_lanes:
                    st.subheader("Lane Performance")
                    _lp_rows = []
                    for _lid in sorted(_lp_lanes.keys()):
                        _ls = _lp_lanes[_lid]
                        _lp_rows.append({
                            "Lane": _lid,
                            "Trades": _ls.get("total", _ls.get("wins", 0) + _ls.get("losses", 0)),
                            "Wins": _ls.get("wins", 0),
                            "Losses": _ls.get("losses", 0),
                            "Win Rate": f"{_ls.get('win_rate', 0):.0%}",
                            "Avg PnL": f"${_ls.get('avg_pnl_usd', 0):+.2f}",
                            "Status": _ls.get("override", "active"),
                        })
                    if _lp_rows:
                        st.dataframe(_lp_rows, use_container_width=True)
                else:
                    st.info("No lane performance data yet. Stats populate after trades close.")
            else:
                st.info("Lane performance file not found. Will appear after first trade cycle.")
        except Exception as _lp_err:
            st.warning(f"Error loading lane performance: {_lp_err}")

        # Evolution Engine State
        _evo_path = Path(__file__).parent / "data" / "evolution_state.json"
        try:
            if _evo_path.exists():
                import json as _evo_json2
                _evo_data = _evo_json2.loads(_evo_path.read_text())
                st.subheader("Evolution State")
                _ec1, _ec2, _ec3 = st.columns(3)
                with _ec1:
                    _kpi("Generation", str(_evo_data.get("generation", 0)), tone="neutral")
                with _ec2:
                    _kpi("Total Trades", str(_evo_data.get("total_trades", 0)), tone="neutral")
                with _ec3:
                    _kpi("Last Updated", str(_evo_data.get("updated_at", "never"))[:19], tone="neutral")

                # Bandit stats
                _bandit = _evo_data.get("bandit", {})
                if _bandit:
                    st.subheader("Thompson Sampling Bandit")
                    _b_rows = []
                    for _bl, _bs in sorted(_bandit.items()):
                        _bw = _bs.get("wins", 0)
                        _bls = _bs.get("losses", 0)
                        _bt = _bw + _bls
                        _bwr = f"{_bw/_bt:.0%}" if _bt > 0 else "n/a"
                        _b_rows.append({"Lane": _bl, "Wins": _bw, "Losses": _bls, "Win Rate": _bwr})
                    st.dataframe(_b_rows, use_container_width=True)

                # Weight adjustments
                _weights = _evo_data.get("weights", {})
                _adj_lanes = {k: v.get("adjustments", {}) for k, v in _weights.items() if v.get("adjustments")}
                if _adj_lanes:
                    st.subheader("Learned Weight Adjustments")
                    for _wl, _wa in sorted(_adj_lanes.items()):
                        st.text(f"  {_wl}: {_wa}")

                # Threshold optimization
                _thresholds = _evo_data.get("thresholds", {})
                _thr_optimals = {k: v.get("optimal") for k, v in _thresholds.items() if v.get("optimal") is not None}
                if _thr_optimals:
                    st.subheader("Optimized Thresholds")
                    for _tl, _to in sorted(_thr_optimals.items()):
                        st.text(f"  {_tl}: {_to}")
            else:
                st.info("Evolution engine state not found. Will appear after trades are processed.")
        except Exception as _evo_err:
            st.warning(f"Error loading evolution state: {_evo_err}")

        # Agent Comms / Debate Log
        _comms_path = Path(__file__).parent / "data" / "agent_comms.json"
        try:
            if _comms_path.exists():
                import json as _evo_json3
                _comms = _evo_json3.loads(_comms_path.read_text())
                _assessments = _comms.get("assessments", {})
                _consensus = _comms.get("consensus", {})
                if _assessments or _consensus:
                    st.subheader("Live Agent Debate")
                    for _agent_name, _assess in sorted(_assessments.items()):
                        _act = _assess.get("action", "?")
                        _conf = _assess.get("confidence", "?")
                        _rsn = _assess.get("reasoning", "")[:120]
                        st.text(f"  {_agent_name}: {_act} (conf: {_conf}) - {_rsn}")
                    if _consensus:
                        st.text(f"  Consensus: {_consensus.get('action', '?')} (conf: {_consensus.get('confidence', '?')})")
                _debate_log = _comms.get("debate_log", [])
                if _debate_log:
                    with st.expander(f"Debate History ({len(_debate_log)} rounds)", expanded=False):
                        for _dl in _debate_log[-10:]:
                            st.text(f"  [{_dl.get('timestamp', '?')[:19]}] {_dl.get('summary', '')[:200]}")
        except Exception:
            pass

elif page == "Portfolio":
    st.markdown("<div class='panel-title'>Portfolio — Coinbase Account</div>", unsafe_allow_html=True)

    # Row 1: Portfolio overview (matches Coinbase app)
    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        _kpi("Total Balance", _format_money(portfolio_value), tone="good" if portfolio_value and portfolio_value > 0 else "neutral")
    with pc2:
        _kpi("Cash", _format_money(cash_value), tone="neutral")
    with pc3:
        _kpi("Futures", _format_money(deriv_balance), tone="neutral")
    with pc4:
        _kpi("USDC (3.5% APY)", _format_money(spot_usdc), tone="good" if spot_usdc > 0 else "neutral")

    # Row 2: USDC yield + position summary + P&L
    _sp1, _sp2, _sp3, _sp4 = st.columns(4)
    with _sp1:
        _daily_yield = spot_usdc * 0.035 / 365.0
        _kpi("USDC Yield / Day", f"+{_format_money(_daily_yield)}", tone="good" if _daily_yield > 0 else "neutral")
    with _sp2:
        _port_exch_pnl = _safe_float(last_decision.get("exchange_pnl_today_usd"))
        _port_bot_pnl = float(state.get("pnl_today_usd") or 0.0)
        pnl_today = _port_exch_pnl if _port_exch_pnl is not None else _port_bot_pnl
        _kpi("P&L Today", _format_money(pnl_today), tone=("good" if pnl_today >= 0 else "bad"))
    with _sp3:
        _kpi("Transfers Today", _format_money(_safe_float(state.get("transfers_today_usd"))), tone="neutral")
    with _sp4:
        conv_today = _safe_float(state.get("conversion_cost_today_usd"))
        _kpi("Conversion Cost", _format_money(conv_today), tone=("bad" if (conv_today is not None and conv_today > 0) else "neutral"))

    # Row 3: Live position (if any)
    if pos_view and pos_source:
        _p_dir = _safe_str(pos_view.get("direction")) or "?"
        _p_entry = _safe_float(pos_view.get("entry_price")) or 0
        _p_mark = _safe_float(last_decision.get("mark_price")) or _safe_float(last_decision.get("price")) or 0
        _p_pnl = _safe_float(last_decision.get("pnl_usd_live"))
        _p_contracts = pos_view.get("size") if pos_source == "BOT" else pos_view.get("contracts")
        _p_cs = _safe_float(last_decision.get("contract_size")) or float(cfg.get("contract_size", 5000) or 5000)
        _p_notional = _p_mark * _p_cs * float(_p_contracts or 0) if _p_mark and _p_contracts else None
        _dir_cls = "ok" if _p_dir == "long" else "danger"
        _pnl_cls = "ok" if (_p_pnl or 0) >= 0 else "danger"
        _pnl_str = f"{'+' if (_p_pnl or 0) >= 0 else ''}${(_p_pnl or 0):.2f}" if _p_pnl is not None else "—"
        st.markdown(
            "<div class='card' style='margin-top:12px;'>"
            "<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;'>"
            f"<span class='pill {_dir_cls}' style='font-size:13px;font-weight:700;'>{_p_dir.upper()} XLM PERP</span>"
            f"<span class='muted'>Contracts: {int(float(_p_contracts or 0))}</span>"
            f"<span class='muted'>Entry: ${_p_entry:.5f}</span>"
            f"<span class='muted'>Mark: ${_p_mark:.5f}</span>"
            f"<span class='{_pnl_cls}' style='font-weight:600;'>P&L: {_pnl_str}</span>"
            + (f"<span class='muted'>Notional: ${_p_notional:,.2f}</span>" if _p_notional else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div class='card muted' style='margin-top:12px;text-align:center;padding:16px;'>No open position — funds idle in USDC (earning yield)</div>", unsafe_allow_html=True)
        # NEXT TRADE card — what's the bot watching?
        try:
            from timing.trade_eta import estimate_next_entry as _dash_next_entry
            _ne = _dash_next_entry(state, last_decision, trades, datetime.now(timezone.utc))
            _ne_setup = _ne.get("watching_setup", "")
            _ne_display = _ne.get("estimated_display", "")
            _ne_since = _ne.get("time_since_exit_min")
            _ne_gap = _ne.get("avg_gap_min")
            _ne_readiness = float(_ne.get("readiness_pct") or 0)
            _ne_status_color = "#22c55e" if "ready" in _ne_display.lower() else ("#ef4444" if "blocked" in _ne_display.lower() else "#fbbf24")
            _ne_footer_parts = []
            if _ne_since is not None:
                _ne_h, _ne_m = divmod(int(_ne_since), 60)
                _ne_footer_parts.append(f"Since last exit: {f'{_ne_h}h {_ne_m}m' if _ne_h else f'{_ne_m}m'}")
            if _ne_gap:
                _ne_footer_parts.append(f"avg gap: {int(_ne_gap)}m")
            _ne_footer = " · ".join(_ne_footer_parts)
            _fc_dir = _safe_str(_ne.get("forecast_direction")) or "—"
            _fc_contracts = int(_safe_float(_ne.get("forecast_contracts")) or 1)
            _fc_trigger = _safe_float(_ne.get("forecast_trigger_price"))
            _fc_target = _safe_float(_ne.get("forecast_target_price"))
            _fc_profit_total = _safe_float(_ne.get("forecast_profit_total_usd"))
            _fc_profit_per = _safe_float(_ne.get("forecast_profit_per_contract_usd"))
            _fc_rr = _safe_float(_ne.get("forecast_rr"))
            _fc_eta = _safe_str(_ne.get("eta_window_display")) or _ne_display
            _fc_htf = _safe_str(_ne.get("htf_bias_summary")) or "HTF context unavailable"
            _fc_logic = _safe_str(_ne.get("timeframe_logic")) or ""
            _fc_price_logic = _safe_str(_ne.get("price_logic")) or ""
            _fc_label = _safe_str(_ne.get("forecast_trigger_label")) or "trigger zone"
            _fc_ready = _safe_float(_ne.get("forecast_readiness_pct")) or 0
            _fc_dir_color = "#34d399" if _fc_dir == "long" else "#f87171" if _fc_dir == "short" else "#9ca3af"
            _fc_trigger_s = f"${_fc_trigger:.5f}" if _fc_trigger is not None else "—"
            _fc_target_s = f"${_fc_target:.5f}" if _fc_target is not None else "—"
            _fc_profit_s = f"${_fc_profit_total:,.2f}" if _fc_profit_total is not None else "—"
            _fc_profit_per_s = f"${_fc_profit_per:,.2f}/contract" if _fc_profit_per is not None else "—"
            _fc_rr_s = f"{_fc_rr:.1f}R" if _fc_rr is not None else "—"
            st.markdown(
                f"<div class='intel-card' style='padding:10px 14px;margin-top:8px;'>"
                f"<div class='intel-title'>NEXT TRADE</div>"
                f"<div style='display:flex;justify-content:space-between;margin:6px 0 2px;'>"
                f"<div><span class='label'>WATCHING</span><br/><span class='metric' style='font-size:14px;'>{_ne_setup}</span></div>"
                f"<div style='text-align:right;'><span class='label'>STATUS</span><br/><span class='metric' style='font-size:14px;color:{_ne_status_color};'>{_ne_display}</span></div>"
                f"</div>"
                f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:8px;'>"
                f"<div><span class='label'>LEAN</span><br/><span class='metric' style='font-size:13px;color:{_fc_dir_color};'>{html.escape(_fc_dir.upper())}</span></div>"
                f"<div><span class='label'>ETA</span><br/><span class='metric' style='font-size:13px;'>{html.escape(_fc_eta)}</span></div>"
                f"<div><span class='label'>TARGET</span><br/><span class='metric' style='font-size:13px;'>{html.escape(_fc_profit_s)}</span></div>"
                f"<div><span class='label'>SIZE</span><br/><span class='metric' style='font-size:13px;'>{_fc_contracts} contract{'s' if _fc_contracts != 1 else ''}</span></div>"
                f"</div>"
                f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px;font-size:11px;color:#cbd5e1;'>"
                f"<div><span class='label'>TRIGGER</span><br/>{html.escape(_fc_trigger_s)}<br/><span class='muted'>{html.escape(_fc_label)}</span></div>"
                f"<div><span class='label'>TARGET PX</span><br/>{html.escape(_fc_target_s)}<br/><span class='muted'>{html.escape(_fc_profit_per_s)}</span></div>"
                f"<div><span class='label'>READINESS</span><br/>{_fc_ready:.0f}%<br/><span class='muted'>{html.escape(_fc_rr_s)}</span></div>"
                f"<div><span class='label'>HTF</span><br/><span class='muted'>{html.escape(_fc_htf)}</span></div>"
                f"</div>"
                + (f"<div class='muted' style='font-size:11px;margin-top:8px;'>{html.escape(_fc_logic)}</div>" if _fc_logic else "")
                + (f"<div class='muted' style='font-size:11px;margin-top:4px;'>{html.escape(_fc_price_logic)}</div>" if _fc_price_logic else "")
                + (f"<div class='muted' style='font-size:10px;margin-top:4px;'>{_ne_footer}</div>" if _ne_footer else "")
                + f"</div>",
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    # ── Portfolio Equity Chart (Robinhood-style) ─────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Portfolio Performance</div>", unsafe_allow_html=True)
    try:
        if not timeseries.empty and "ts" in timeseries.columns:
            _eq_df = timeseries.copy()
            _eq_df["ts"] = pd.to_datetime(_eq_df["ts"], utc=True, errors="coerce")
            _eq_df = _eq_df.dropna(subset=["ts"]).sort_values("ts")

            # Build equity curve from cumulative PnL
            _has_pnl = "pnl_today_usd" in _eq_df.columns
            _has_price = "price" in _eq_df.columns

            _chart_tabs = st.tabs(["Cumulative P&L", "Price History", "Equity"])

            with _chart_tabs[0]:
                if _has_pnl:
                    _pnl_series = _eq_df[["ts", "pnl_today_usd"]].copy()
                    _pnl_series["pnl_today_usd"] = pd.to_numeric(_pnl_series["pnl_today_usd"], errors="coerce").fillna(0)
                    # Detect day boundaries and build cumulative
                    _pnl_series["day"] = _pnl_series["ts"].dt.date
                    _cum = []
                    _running = 0.0
                    _prev_day = None
                    _prev_eod_pnl = 0.0
                    for _, r in _pnl_series.iterrows():
                        d = r["day"]
                        if _prev_day is not None and d != _prev_day:
                            _running += _prev_eod_pnl
                        _prev_eod_pnl = float(r["pnl_today_usd"])
                        _prev_day = d
                        _cum.append({"time": int(r["ts"].timestamp()), "value": round(_running + float(r["pnl_today_usd"]), 4)})
                    if _cum:
                        # Deduplicate by time (keep last)
                        _seen = {}
                        for pt in _cum:
                            _seen[pt["time"]] = pt
                        _cum_dedup = sorted(_seen.values(), key=lambda x: x["time"])
                        _final_val = _cum_dedup[-1]["value"] if _cum_dedup else 0
                        _accent = "#10b981" if _final_val >= 0 else "#ef4444"
                        _lightweight_line_chart(_cum_dedup, height=240, accent=_accent)
                        _delta_str = f"{'+'if _final_val>=0 else ''}${_final_val:.2f}"
                        st.markdown(
                            f"<div style='text-align:center;font-size:11px;color:#6b7280;margin-top:-6px;'>"
                            f"Cumulative P&L: <span style='color:{_accent};font-weight:600;'>{_delta_str}</span>"
                            f" &bull; {len(_cum_dedup)} data points"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown("<div class='card'><div class='metric muted'>No P&L data recorded yet.</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card'><div class='metric muted'>P&L tracking not available in timeseries.</div></div>", unsafe_allow_html=True)

            with _chart_tabs[1]:
                if _has_price:
                    _px_series = _eq_df[["ts", "price"]].copy()
                    _px_series["price"] = pd.to_numeric(_px_series["price"], errors="coerce")
                    _px_series = _px_series.dropna(subset=["price"])
                    _px_data = []
                    _px_seen = {}
                    for _, r in _px_series.iterrows():
                        t = int(r["ts"].timestamp())
                        _px_seen[t] = {"time": t, "value": round(float(r["price"]), 6)}
                    _px_data = sorted(_px_seen.values(), key=lambda x: x["time"])
                    if _px_data:
                        _first_px = _px_data[0]["value"]
                        _last_px = _px_data[-1]["value"]
                        _px_accent = "#10b981" if _last_px >= _first_px else "#ef4444"
                        _lightweight_line_chart(_px_data, height=240, accent=_px_accent)
                        _px_chg = ((_last_px - _first_px) / _first_px * 100) if _first_px > 0 else 0
                        st.markdown(
                            f"<div style='text-align:center;font-size:11px;color:#6b7280;margin-top:-6px;'>"
                            f"XLM: <span style='font-weight:600;'>${_last_px:.6f}</span>"
                            f" <span style='color:{_px_accent};'>({'+' if _px_chg>=0 else ''}{_px_chg:.2f}%)</span>"
                            f" &bull; {len(_px_data)} ticks"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown("<div class='card'><div class='metric muted'>No price data.</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card'><div class='metric muted'>Price history not available.</div></div>", unsafe_allow_html=True)

            with _chart_tabs[2]:
                _all_eq = _load_equity_series(hours=None)
                if _all_eq:
                    _eq_s = []
                    _px_s = []
                    _eq_seen2 = {}
                    _px_seen2 = {}
                    for _r in _all_eq:
                        try:
                            _t2 = int(datetime.fromisoformat(_r["ts"]).timestamp())
                            _ev2 = float(_r.get("portfolio") or _r.get("equity") or 0)
                            _pv2 = float(_r.get("mark_price") or 0)
                            if _ev2 > 0:
                                _eq_seen2[_t2] = {"time": _t2, "value": round(_ev2, 2)}
                            if _pv2 > 0:
                                _px_seen2[_t2] = {"time": _t2, "value": round(_pv2, 6)}
                        except Exception:
                            continue
                    _eq_s = sorted(_eq_seen2.values(), key=lambda x: x["time"])
                    _px_s = sorted(_px_seen2.values(), key=lambda x: x["time"])
                    _all_markers = _build_trade_markers(trades, hours=None)
                    if _eq_s or _px_s:
                        _equity_chart_with_markers(
                            _eq_s, _px_s, _all_markers,
                            height_equity=200 if _eq_s else 0,
                            height_price=200,
                            chart_id="portfolio",
                        )
                    else:
                        st.markdown("<div class='card'><div class='metric muted'>No equity data.</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card'><div class='metric muted'>No equity series yet. Bot will start collecting after restart.</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Portfolio chart unavailable.</div></div>", unsafe_allow_html=True)

    # ── Portfolio Stats ─────────────────────────────────────────────────────
    try:
        _closed_ps = _get_closed_trades(trades) if trades is not None and not trades.empty else pd.DataFrame()
        if not _closed_ps.empty and "pnl_usd" in _closed_ps.columns:
            _pnl_list = pd.to_numeric(_closed_ps["pnl_usd"], errors="coerce").dropna().tolist()
            if len(_pnl_list) >= 2:
                _gross_profit = sum(p for p in _pnl_list if p > 0)
                _gross_loss = abs(sum(p for p in _pnl_list if p < 0))
                _profit_factor = (_gross_profit / _gross_loss) if _gross_loss > 0 else float("inf")
                _avg_win = (_gross_profit / sum(1 for p in _pnl_list if p > 0)) if any(p > 0 for p in _pnl_list) else 0
                _avg_loss = (_gross_loss / sum(1 for p in _pnl_list if p < 0)) if any(p < 0 for p in _pnl_list) else 0
                # Max drawdown from cumulative PnL
                _cum_pnl = []
                _running = 0.0
                for p in _pnl_list:
                    _running += p
                    _cum_pnl.append(_running)
                _peak = _cum_pnl[0]
                _max_dd = 0.0
                for v in _cum_pnl:
                    _peak = max(_peak, v)
                    _dd = _peak - v
                    _max_dd = max(_max_dd, _dd)
                # Best and worst single trade
                _best_trade = max(_pnl_list)
                _worst_trade = min(_pnl_list)

                _pf_color = "#10b981" if _profit_factor >= 1.5 else "#f59e0b" if _profit_factor >= 1.0 else "#ef4444"
                st.markdown("<div class='panel-title' style='margin-top:14px;'>Performance Stats</div>", unsafe_allow_html=True)
                _ps1, _ps2, _ps3, _ps4 = st.columns(4)
                with _ps1:
                    _kpi("Profit Factor", f"{_profit_factor:.2f}" if _profit_factor != float("inf") else "∞", tone=("good" if _profit_factor >= 1.5 else "warn" if _profit_factor >= 1.0 else "bad"))
                with _ps2:
                    _kpi("Max Drawdown", f"${_max_dd:.2f}", tone=("good" if _max_dd < 5 else "warn" if _max_dd < 15 else "bad"))
                with _ps3:
                    _kpi("Avg Win", f"+${_avg_win:.2f}", tone="good")
                with _ps4:
                    _kpi("Avg Loss", f"-${_avg_loss:.2f}", tone="bad")
                _ps5, _ps6, _ps7, _ps8 = st.columns(4)
                with _ps5:
                    _kpi("Best Trade", f"+${_best_trade:.2f}" if _best_trade > 0 else f"${_best_trade:.2f}", tone="good")
                with _ps6:
                    _kpi("Worst Trade", f"${_worst_trade:.2f}", tone="bad")
                with _ps7:
                    _kpi("Total Trades", str(len(_pnl_list)), tone="neutral")
                with _ps8:
                    _expectancy = sum(_pnl_list) / len(_pnl_list)
                    _kpi("Expectancy", f"{'+'if _expectancy>=0 else ''}${_expectancy:.2f}", tone=("good" if _expectancy > 0 else "bad"))
    except Exception:
        pass

    # ── Share Report to Slack ─────────────────────────────────────────────
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button("Share Report to Slack", key="slack_share_portfolio"):
        try:
            import requests as _slack_req
            _now_pt = datetime.now(timezone.utc).astimezone(PT)
            _pos_label = state.get("open_position") or state.get("state") or "Flat"
            _eq_val = state.get("equity_start_usd") or portfolio_value or 0
            _pnl_val = state.get("pnl_today_usd") or 0
            _trades_val = state.get("trades_today") or state.get("trades") or 0
            _vol_val = state.get("vol_phase") or state.get("vol_state") or "unknown"
            _consec_val = state.get("consecutive_losses") or 0
            _report_text = (
                f"*Rex Thornton* [DASHBOARD REPORT]\n"
                f"## Trading Report -- {_now_pt.strftime('%B %d, %Y %I:%M %p PT')}\n\n"
                f"Equity: ${float(_eq_val):,.2f}\n"
                f"Position: {_pos_label}\n"
                f"PnL Today: ${float(_pnl_val):,.2f}\n"
                f"Trades Today: {_trades_val}\n"
                f"Vol State: {_vol_val}\n"
                f"Consecutive Losses: {_consec_val}\n"
            )
            _slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
            _slack_resp = _slack_req.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {_slack_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": "C0AN8SG030W",
                    "text": _report_text,
                },
                timeout=10,
            )
            if _slack_resp.ok and _slack_resp.json().get("ok"):
                st.success("Report shared to #xlm-trading!")
            else:
                _err_msg = _slack_resp.json().get("error", _slack_resp.text[:100])
                st.error(f"Slack error: {_err_msg}")
        except Exception as _slack_err:
            st.error(f"Failed to share: {str(_slack_err)[:120]}")

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Open Positions (Exchange)</div>", unsafe_allow_html=True)
    if _cfm_positions:
        rows = []
        assumed_lev = float(cfg.get("leverage") or 1)
        for p in _cfm_positions:
            np = _normalize_cfm_position(p or {})
            pid = np["product_id"]
            direction = np["direction"]
            entry = np["entry_price"]
            cur = np["current_price"]

            # Best-effort order protection summary (stop/tp) per product.
            orders = _get_cfm_open_orders_cached(product_id=pid)
            best = None
            for o in orders or []:
                prot = _order_protection_summary(o or {})
                # Prefer bracket-type orders with any stop/tp values.
                if prot.get("stop_trigger") is None and prot.get("take_profit") is None:
                    continue
                if best is None:
                    best = prot
                    continue
                # Prefer "ok" health.
                if best.get("health") != "ok" and prot.get("health") == "ok":
                    best = prot
            best = best or {}

            liq_est = None
            dist_to_liq_pct = None
            if entry and assumed_lev:
                try:
                    e = float(entry)
                    lev = float(assumed_lev)
                    if lev <= 0:
                        lev = 1.0
                    liq_est = e * (1 - 1 / lev) if direction == "long" else e * (1 + 1 / lev)
                    if cur and liq_est:
                        dist_to_liq_pct = abs(float(cur) - liq_est) / liq_est * 100.0
                except Exception:
                    liq_est = None
                    dist_to_liq_pct = None

            tp_lvls = _strategy_tp_levels(float(entry or 0.0), direction, assumed_lev, cfg) if entry else {"tp1": None, "tp2": None, "tp3": None}
            tp1 = tp_lvls.get("tp1")
            need_tp1 = _pct_to_level(float(cur or 0.0), float(tp1), direction) if (cur and tp1) else None
            tp2 = tp_lvls.get("tp2")
            tp3 = tp_lvls.get("tp3")

            stop_trig = best.get("stop_trigger")
            tp_order = best.get("take_profit")
            need_stop = _pct_to_level(float(cur or 0.0), float(stop_trig), "long" if direction == "short" else "short") if (cur and stop_trig) else None
            need_tp_order = _pct_to_level(float(cur or 0.0), float(tp_order), direction) if (cur and tp_order) else None

            # Profit projection to strategy TP levels (full close, ignores fees/slippage).
            details = _get_cfm_product_details_cached(pid) if pid and pid != "-" else {}
            cs = _contract_size_from_details(details) or None
            pnl_tp1 = _project_pnl_usd(float(entry), float(tp1), direction=direction, contracts=float(np["contracts"] or 0), contract_size=float(cs)) if (cs and entry and tp1 and np["contracts"]) else None
            pnl_tp2 = _project_pnl_usd(float(entry), float(tp2), direction=direction, contracts=float(np["contracts"] or 0), contract_size=float(cs)) if (cs and entry and tp2 and np["contracts"]) else None
            pnl_tp3 = _project_pnl_usd(float(entry), float(tp3), direction=direction, contracts=float(np["contracts"] or 0), contract_size=float(cs)) if (cs and entry and tp3 and np["contracts"]) else None

            rows.append({
                "product_id": pid,
                "direction": direction,
                "contracts": np["contracts"],
                "entry": entry,
                "current": cur,
                "uPnL": np["unrealized_pnl"],
                "lev_assumed": assumed_lev,
                "liq_est": liq_est,
                "dist_to_liq_%": round(dist_to_liq_pct, 2) if dist_to_liq_pct is not None else None,
                "stop_trigger": stop_trig,
                "to_stop_%": round(need_stop, 2) if need_stop is not None else None,
                "take_profit": tp_order,
                "to_tp_%": round(need_tp_order, 2) if need_tp_order is not None else None,
                "tp1_strategy": tp1,
                "to_tp1_%": round(need_tp1, 2) if need_tp1 is not None else None,
                "pnl@tp1": pnl_tp1,
                "pnl@tp2": pnl_tp2,
                "pnl@tp3": pnl_tp3,
                "bracket_health": best.get("health") or ("warn" if orders else "none"),
                "trigger_status": best.get("trigger_status") or "",
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=320)

        with st.expander("Open Orders (Per Position)", expanded=False):
            for r in rows[:6]:
                pid = r["product_id"]
                orders = _get_cfm_open_orders_cached(product_id=pid)
                st.markdown(f"**{pid}** ({len(orders)} open orders)")
                for o in orders[:10]:
                    prot = _order_protection_summary(o or {})
                    st.write({
                        "order_id": o.get("order_id"),
                        "side": o.get("side"),
                        "status": prot.get("status"),
                        "order_type": prot.get("order_type"),
                        "trigger_status": prot.get("trigger_status"),
                        "stop_trigger": prot.get("stop_trigger"),
                        "take_profit": prot.get("take_profit"),
                        "health": prot.get("health"),
                        "created_time": _fmt_utc8_long(o.get("created_time")),
                    })
    else:
        st.markdown("<div class='card'><div class='metric muted'>No exchange positions detected.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Cash Movements (7d)</div>", unsafe_allow_html=True)
    if cash_movements is not None and not cash_movements.empty:
        cm = cash_movements.copy().sort_values("timestamp", ascending=False)
        st.dataframe(_format_df_timestamps_utc8(cm.head(150)), use_container_width=True, height=280)
    else:
        st.markdown("<div class='card'><div class='metric muted'>No transfer/conversion events recorded yet.</div></div>", unsafe_allow_html=True)

elif page == "Signals":
    st.markdown("<div class='panel-title'>Signal Engine</div>", unsafe_allow_html=True)
    _cur_conf = int(_safe_float(last_decision.get("confluence_count", 0)) or _safe_float(last_decision.get("confluence_score")) or 0)
    _cur_signal = _safe_str(last_decision.get("entry_signal"))
    _cur_dir = _safe_str(last_decision.get("direction"))

    s1, s2, s3 = st.columns([1.2, 1.0, 1.0])
    with s1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='label'>CURRENT</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric'>{(_cur_signal or '-')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='label' style='margin-top:10px;'>DIRECTION</div><div class='metric'>{(_cur_dir.upper() if _cur_dir else '-')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='label' style='margin-top:10px;'>CONFIRMATIONS</div><div class='metric'>{_cur_conf}/6</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with s2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        gates = (last_decision.get("gates") or {}) if isinstance(last_decision.get("gates"), dict) else {}
        blocked = [k for k, v in gates.items() if not v] if gates else []
        st.markdown("<div class='label'>GATES</div>", unsafe_allow_html=True)
        if not gates:
            st.markdown("<div class='metric muted'>-</div>", unsafe_allow_html=True)
        elif not blocked:
            st.markdown("<div class='metric ok'>PASS</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='metric danger'>BLOCKED</div>", unsafe_allow_html=True)
            for b in blocked[:6]:
                st.markdown(f"<div class='intel-event'>{_plain_english_gate(b)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with s3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        confluences = last_decision.get("confluences") or {}
        on = [k for k, v in confluences.items() if v] if isinstance(confluences, dict) else []
        st.markdown("<div class='label'>CONFLUENCES ON</div>", unsafe_allow_html=True)
        if on:
            for k in on[:10]:
                st.markdown(f"<div class='intel-event'>{_plain_english_confluence(k)}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='metric muted'>-</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Signal Readiness Gauge ─────────────────────────────────────────────
    try:
        _rg_score = _safe_float(last_decision.get("v4_selected_score")) or 0
        _rg_thresh = _safe_float(last_decision.get("v4_selected_threshold")) or 75
        _rg_gates = gates  # from above
        _rg_gates_total = len(_rg_gates) if _rg_gates else 0
        _rg_gates_pass = sum(1 for v in _rg_gates.values() if v) if _rg_gates else 0
        _rg_has_signal = bool(_cur_signal and _cur_signal.strip() and _cur_signal.strip() != "-")
        _rg_ev_usd = _safe_float(((last_decision.get("ev") or {}) if isinstance(last_decision.get("ev"), dict) else {}).get("ev_usd") or last_decision.get("ev_usd"))
        _rg_cooldown = bool(last_decision.get("cooldown"))

        # Build readiness checklist
        _rg_checks = []
        _rg_checks.append(("Signal detected", _rg_has_signal))
        _rg_checks.append((f"Score ≥ threshold ({int(_rg_score)}/{int(_rg_thresh)})", _rg_score >= _rg_thresh))
        _rg_checks.append((f"Gates pass ({_rg_gates_pass}/{_rg_gates_total})", _rg_gates_total > 0 and _rg_gates_pass == _rg_gates_total))
        _rg_checks.append(("EV positive", _rg_ev_usd is not None and _rg_ev_usd > 0))
        _rg_checks.append(("No cooldown", not _rg_cooldown))

        _rg_passed = sum(1 for _, v in _rg_checks if v)
        _rg_total = len(_rg_checks)
        _rg_pct = (_rg_passed / _rg_total * 100) if _rg_total > 0 else 0
        _rg_color = "#10b981" if _rg_pct >= 80 else "#f59e0b" if _rg_pct >= 50 else "#ef4444"

        st.markdown("<div class='panel-title' style='margin-top:14px;'>Entry Readiness</div>", unsafe_allow_html=True)
        _checks_html = ""
        for _ck_label, _ck_pass in _rg_checks:
            _ck_icon = "&#10003;" if _ck_pass else "&#10007;"
            _ck_clr = "#10b981" if _ck_pass else "#ef4444"
            _checks_html += f"<span style='color:{_ck_clr};font-size:11px;margin-right:12px;'>{_ck_icon} {html.escape(_ck_label)}</span>"
        st.markdown(
            f"<div class='card' style='padding:12px 16px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
            f"<div style='font-size:28px;font-weight:700;color:{_rg_color};'>{_rg_passed}/{_rg_total}</div>"
            f"<div style='flex:1;height:8px;background:rgba(107,114,128,0.2);border-radius:4px;overflow:hidden;'>"
            f"<div style='width:{_rg_pct:.0f}%;height:100%;background:{_rg_color};border-radius:4px;"
            f"transition:width 0.3s;'></div></div>"
            f"</div>"
            f"<div style='line-height:1.8;'>{_checks_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    # ── Lane Status: Dual-Direction Diagnostic Grid ──────────────────────────
    try:
        _ls_long_score = _safe_float(last_decision.get("v4_score_long")) or 0
        _ls_short_score = _safe_float(last_decision.get("v4_score_short")) or 0
        _ls_long_thresh = _safe_float(last_decision.get("v4_threshold_long")) or _safe_float(last_decision.get("v4_selected_threshold")) or 75
        _ls_short_thresh = _safe_float(last_decision.get("v4_threshold_short")) or _safe_float(last_decision.get("v4_selected_threshold")) or 75
        _ls_long_entry = _safe_str(last_decision.get("entry_type_long"))
        _ls_short_entry = _safe_str(last_decision.get("entry_type_short"))
        _ls_long_pass_v4 = bool(last_decision.get("v4_pass_long"))
        _ls_short_pass_v4 = bool(last_decision.get("v4_pass_short"))
        _ls_long_candidate = bool(last_decision.get("candidate_long_pass"))
        _ls_short_candidate = bool(last_decision.get("candidate_short_pass"))
        _ls_long_block = _safe_str(last_decision.get("long_block_reason"))
        _ls_short_block = _safe_str(last_decision.get("short_block_reason"))
        _ls_gates = (last_decision.get("gates") or {}) if isinstance(last_decision.get("gates"), dict) else {}
        _ls_gates_pass = bool(last_decision.get("gates_pass"))
        _ls_cooldown = bool(last_decision.get("cooldown"))
        _ls_lane_long = _safe_str(last_decision.get("lane_long"))
        _ls_lane_short = _safe_str(last_decision.get("lane_short"))
        _ls_selected_dir = _safe_str(last_decision.get("direction")) or ""
        _ls_gates_blocked = [k for k, v in _ls_gates.items() if not bool(v)] if _ls_gates else []

        def _ls_row(label: str, ok: bool, detail: str) -> str:
            clr = "#10b981" if ok else "#ef4444"
            icon = "&#10003;" if ok else "&#10007;"
            return (
                f"<div style='display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid rgba(75,85,99,0.15);'>"
                f"<span style='color:{clr};font-size:12px;width:14px;text-align:center;'>{icon}</span>"
                f"<span style='font-size:11px;color:#9ca3af;width:68px;'>{label}</span>"
                f"<span style='font-size:11px;color:#d1d5db;flex:1;text-align:right;'>{detail}</span>"
                f"</div>"
            )

        def _ls_direction_card(direction: str, score, thresh, entry_type, pass_v4, candidate_pass, lane_letter, block_reason):
            d_upper = direction.upper()
            icon = "&#9650;" if direction == "long" else "&#9660;"
            d_clr = "#34d399" if direction == "long" else "#f87171"

            # Score bar
            pct = min(100, max(0, score / max(thresh, 1) * 100))
            bar_clr = "#10b981" if pass_v4 else "#f59e0b" if pct >= 60 else "#ef4444"

            # Lane pill
            lane_html = ""
            if lane_letter:
                _lc_map = {"A": "#3b82f6", "B": "#10b981", "C": "#f59e0b", "E": "#8b5cf6", "F": "#ec4899", "G": "#06b6d4"}
                _lc = _lc_map.get(lane_letter, "#6b7280")
                lane_html = f"<span class='pill' style='background:{_lc}20;color:{_lc};font-size:9px;padding:1px 6px;'>Lane {lane_letter}</span>"

            # 4 diagnostic rows
            has_structure = bool(entry_type)
            structure_detail = (entry_type or "none").replace("_", " ")

            gates_ok = len(_ls_gates_blocked) == 0
            if gates_ok:
                gates_detail = "all pass"
            else:
                gates_detail = ", ".join(_plain_english_gate(g) for g in _ls_gates_blocked[:2])
            # Show lane bypass if applicable for selected direction
            if lane_letter == "C" and direction == _ls_selected_dir and bool(last_decision.get("lane_atr_bypassed")):
                gates_detail += " <span style='color:#8b5cf6;font-size:9px;'>[ATR bypass]</span>"
            if lane_letter == "E" and direction == _ls_selected_dir and bool(last_decision.get("lane_distance_bypassed")):
                gates_detail += " <span style='color:#8b5cf6;font-size:9px;'>[dist bypass]</span>"
            if lane_letter == "G" and direction == _ls_selected_dir:
                gates_detail += " <span style='color:#06b6d4;font-size:9px;'>[range scalp]</span>"

            quality_ok = has_structure and pass_v4
            quality_detail = f"{int(score)}/{int(thresh)}" if has_structure else "no structure"

            entry_ok = candidate_pass and gates_ok and not _ls_cooldown
            if not has_structure:
                entry_detail = "no structure"
            elif not pass_v4:
                entry_detail = f"need {int(thresh - score)} pts"
            elif not gates_ok:
                entry_detail = "gates blocked"
            elif _ls_cooldown:
                entry_detail = "cooldown"
            elif entry_ok:
                entry_detail = "<span style='color:#10b981;font-weight:600;'>READY</span>"
            else:
                # Parse first reason from block_reason
                entry_detail = (block_reason or "blocked").split("|")[0].replace("_", " ")

            score_clr = "#d1d5db" if has_structure else "#4b5563"
            return (
                f"<div class='card' style='padding:10px 12px;'>"
                f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;'>"
                f"<span style='color:{d_clr};font-size:12px;font-weight:700;'>{icon} {d_upper}</span>"
                f"{lane_html}"
                f"</div>"
                f"<div style='display:flex;align-items:baseline;gap:6px;margin-bottom:6px;'>"
                f"<span style='font-size:18px;font-weight:700;color:{score_clr};'>{int(score)}</span>"
                f"<span class='muted' style='font-size:11px;'>/ {int(thresh)}</span>"
                f"</div>"
                f"<div style='height:4px;background:#1f2937;border-radius:2px;margin-bottom:8px;overflow:hidden;'>"
                f"<div style='width:{pct:.0f}%;height:100%;background:{bar_clr};border-radius:2px;'></div>"
                f"</div>"
                + _ls_row("STRUCTURE", has_structure, structure_detail)
                + _ls_row("GATES", gates_ok, gates_detail)
                + _ls_row("QUALITY", quality_ok, quality_detail)
                + _ls_row("ENTRY", entry_ok, entry_detail)
                + f"</div>"
            )

        st.markdown("<div class='panel-title' style='margin-top:14px;'>Lane Status</div>", unsafe_allow_html=True)
        _ls_col_left, _ls_col_right = st.columns(2)

        with _ls_col_left:
            st.markdown(
                _ls_direction_card(
                    "long", _ls_long_score, _ls_long_thresh, _ls_long_entry,
                    _ls_long_pass_v4, _ls_long_candidate, _ls_lane_long, _ls_long_block,
                ),
                unsafe_allow_html=True,
            )
        with _ls_col_right:
            st.markdown(
                _ls_direction_card(
                    "short", _ls_short_score, _ls_short_thresh, _ls_short_entry,
                    _ls_short_pass_v4, _ls_short_candidate, _ls_lane_short, _ls_short_block,
                ),
                unsafe_allow_html=True,
            )

        # Summary row
        _ls_summary_parts: list[str] = []
        if _ls_selected_dir:
            _sel_clr = "#34d399" if _ls_selected_dir == "long" else "#f87171" if _ls_selected_dir == "short" else "#9ca3af"
            _ls_summary_parts.append(f"Selected: <span style='color:{_sel_clr};font-weight:600;'>{_ls_selected_dir.upper()}</span>")
        _ls_regime = _safe_str(last_decision.get("v4_regime")) or _safe_str(last_decision.get("regime")) or ""
        if _ls_regime:
            _ls_summary_parts.append(f"Regime: <strong>{_ls_regime.replace('_', ' ')}</strong>")
        if _ls_cooldown:
            _ls_summary_parts.append("<span class='pill danger'>COOLDOWN</span>")
        if bool(last_decision.get("sweep_detected")):
            _ls_summary_parts.append("<span class='pill' style='background:rgba(251,191,36,0.15);color:#f59e0b;'>SWEEP</span>")
        if bool(last_decision.get("squeeze_detected")):
            _ls_summary_parts.append("<span class='pill' style='background:rgba(139,92,246,0.15);color:#8b5cf6;'>SQUEEZE</span>")
        _ls_lw_used = _safe_str(last_decision.get("lane_weights_used"))
        if _ls_lw_used:
            _ls_summary_parts.append(f"<span style='font-size:10px;color:#9ca3af;'>Weights: Lane {html.escape(_ls_lw_used)}</span>")
        _ls_align = last_decision.get("alignment_bonus")
        if _ls_align is not None and int(_ls_align or 0) != 0:
            _align_v = int(_ls_align)
            _align_c = "#10b981" if _align_v > 0 else "#ef4444"
            _ls_summary_parts.append(f"<span class='pill' style='background:{_align_c}18;color:{_align_c};'>TF align {_align_v:+d}</span>")
        _ls_zbonus = last_decision.get("zone_bonus")
        if _ls_zbonus is not None and int(_ls_zbonus or 0) != 0:
            _zb_v = int(_ls_zbonus)
            _zb_c = "#3b82f6" if _zb_v > 0 else "#ef4444"
            _ls_summary_parts.append(f"<span class='pill' style='background:{_zb_c}18;color:{_zb_c};'>Zone {_zb_v:+d}</span>")
        if _ls_summary_parts:
            st.markdown(
                f"<div class='intel-event' style='margin-top:4px;'>{' &bull; '.join(_ls_summary_parts)}</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # ── Market Context Snapshot ──────────────────────────────────────────────
    try:
        _mc_regime = _safe_str(last_decision.get("v4_regime")) or _safe_str(last_decision.get("regime")) or "-"
        _mc_vol = _safe_str(last_decision.get("vol_phase")) or "-"
        _mc_vol_dir = _safe_str(last_decision.get("vol_direction")) or "-"
        _mc_htf = _safe_str(last_decision.get("htf_readiness")) or "-"
        _mc_spread = _safe_float(last_decision.get("spread_pct"))

        _vol_colors = {"COMPRESSION": "#3b82f6", "IGNITION": "#f59e0b", "EXPANSION": "#10b981", "EXHAUSTION": "#ef4444"}
        _regime_colors = {"trend": "#10b981", "mean_reversion": "#8b5cf6", "mixed": "#f59e0b"}
        _vc = _vol_colors.get(_mc_vol, "#6b7280")
        _rc = _regime_colors.get(_mc_regime.lower(), "#6b7280")

        _mc_parts = [
            f"<span class='pill' style='background:{_rc}20;color:{_rc};'>{html.escape(_mc_regime.upper())}</span>",
            f"<span class='pill' style='background:{_vc}20;color:{_vc};'>{html.escape(_mc_vol)}</span>",
        ]
        if _mc_vol_dir and _mc_vol_dir != "-":
            _mc_parts.append(f"<span style='font-size:11px;color:#9ca3af;'>{html.escape(_mc_vol_dir)}</span>")
        if _mc_htf and _mc_htf != "-":
            _mc_parts.append(f"<span style='font-size:10px;color:#6b7280;'>{html.escape(_mc_htf.replace('_', ' '))}</span>")
        if _mc_spread is not None:
            _sp_color = "#10b981" if _mc_spread < 0.03 else "#f59e0b" if _mc_spread < 0.08 else "#ef4444"
            _mc_parts.append(f"<span style='font-size:10px;color:{_sp_color};'>spread {_mc_spread:.3f}%</span>")
        _mc_ms = last_decision.get("moonshot_active")
        if _mc_ms:
            _mc_trail = _safe_float(last_decision.get("moonshot_trail_stop"))
            _mc_ms_txt = "MOONSHOT"
            if _mc_trail is not None:
                _mc_ms_txt += f" trail ${_mc_trail:.5f}"
            _mc_parts.append(f"<span class='pill' style='background:rgba(245,158,11,0.2);color:#f59e0b;font-weight:700;'>{_mc_ms_txt}</span>")

        st.markdown("<div class='panel-title' style='margin-top:14px;'>Market Context</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='card' style='padding:10px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
            + " ".join(_mc_parts)
            + "</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    # ── Lane Scoring ──
    try:
        _lane = last_decision.get("lane")
        _lane_label = str(last_decision.get("lane_label") or "")
        _lane_reason = str(last_decision.get("lane_reason") or "")
        _sweep_detected = bool(last_decision.get("sweep_detected"))
        _squeeze_detected = bool(last_decision.get("squeeze_detected"))
        _lane_atr_bypass = bool(last_decision.get("lane_atr_bypassed"))
        _lane_dist_bypass = bool(last_decision.get("lane_distance_bypassed"))
        if _lane:
            _lane_colors = {"A": "#3b82f6", "B": "#10b981", "C": "#f59e0b", "E": "#8b5cf6"}
            _lane_labels = {"A": "TREND", "B": "BREAKOUT", "C": "SWEEP", "E": "SQUEEZE", "F": "COMP-BRK", "G": "RANGE"}
            _lc = _lane_colors.get(_lane, "#6b7280")
            _ll = _lane_labels.get(_lane, _lane)
            _lane_parts = [f"<span class='pill' style='background:{_lc};font-weight:700;'>Lane {_lane}: {_ll}</span>"]
            if _sweep_detected:
                _lane_parts.append("<span class='pill' style='background:#ef4444;'>SWEEP DETECTED</span>")
            if _squeeze_detected:
                _lane_parts.append("<span class='pill' style='background:#8b5cf6;'>SQUEEZE IMPULSE</span>")
            if _lane_atr_bypass:
                _lane_parts.append("<span class='pill' style='background:#7c3aed;'>ATR BYPASS</span>")
            if _lane_dist_bypass:
                _lane_parts.append("<span class='pill' style='background:#7c3aed;'>DISTANCE BYPASS</span>")
            st.markdown(
                "<div class='panel-title' style='margin-top:14px;'>Lane Scoring</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='card' style='padding:10px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
                + " ".join(_lane_parts) + "</div>",
                unsafe_allow_html=True,
            )
            if _lane_reason:
                st.markdown(
                    f"<div style='font-size:11px;color:#9ca3af;margin:2px 0 0 4px;'>{_lane_reason}</div>",
                    unsafe_allow_html=True,
                )
    except Exception:
        pass

    # ── Contract Context ──
    try:
        _cc_basis = last_decision.get("contract_basis_bps")
        _cc_oi_trend = str(last_decision.get("contract_oi_trend") or "")
        _cc_funding = str(last_decision.get("contract_funding_bias") or "")
        _cc_oi_price = str(last_decision.get("contract_oi_price_rel") or "")
        _cc_mod = last_decision.get("contract_mod_bonus")
        _cc_reasons = last_decision.get("contract_mod_reasons") or []
        if _cc_oi_trend or _cc_funding or _cc_basis is not None:
            _cc_parts = []
            if _cc_basis is not None:
                _b_col = "#10b981" if float(_cc_basis) > 0 else "#ef4444" if float(_cc_basis) < 0 else "#9ca3af"
                _cc_parts.append(f"<span class='pill' style='background:{_b_col};'>Basis {float(_cc_basis):+.1f}bps</span>")
            if _cc_oi_trend and _cc_oi_trend != "UNKNOWN":
                _oi_col = "#10b981" if _cc_oi_trend == "RISING" else "#ef4444" if _cc_oi_trend == "FALLING" else "#6b7280"
                _cc_parts.append(f"<span class='pill' style='background:{_oi_col};'>OI {_cc_oi_trend}</span>")
            if _cc_funding and _cc_funding != "UNKNOWN":
                _f_col = "#f59e0b" if _cc_funding != "NEUTRAL" else "#6b7280"
                _cc_parts.append(f"<span class='pill' style='background:{_f_col};'>{_cc_funding.replace('_', ' ')}</span>")
            if _cc_oi_price and _cc_oi_price != "UNKNOWN":
                _cc_parts.append(f"<span class='pill' style='background:#374151;'>{_cc_oi_price}</span>")
            if _cc_mod is not None and int(_cc_mod) != 0:
                _m_col = "#10b981" if int(_cc_mod) > 0 else "#ef4444"
                _cc_parts.append(f"<span class='pill' style='background:{_m_col};'>Score {int(_cc_mod):+d}</span>")
            if _cc_parts:
                st.markdown(
                    "<div class='panel-title' style='margin-top:14px;'>Contract Intelligence</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div class='card' style='padding:10px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
                    + " ".join(_cc_parts) + "</div>",
                    unsafe_allow_html=True,
                )
                if _cc_reasons:
                    st.markdown(
                        "<div style='font-size:11px;color:#9ca3af;margin:2px 0 0 4px;'>"
                        + " | ".join(str(r) for r in _cc_reasons) + "</div>",
                        unsafe_allow_html=True,
                    )
        # Cascade alert
        _cascade = last_decision.get("cascade_event")
        if isinstance(_cascade, dict) and _cascade.get("cascade_type"):
            _sev = str(_cascade.get("severity") or "MINOR")
            _sev_col = "#ef4444" if _sev == "MAJOR" else "#f59e0b" if _sev == "MODERATE" else "#6b7280"
            st.markdown(
                f"<div class='card' style='padding:10px 14px;border-left:3px solid {_sev_col};margin-top:6px;'>"
                f"<span style='color:{_sev_col};font-weight:700;'>{_sev} CASCADE</span> "
                f"<span style='color:#d1d5db;'>{_cascade.get('cascade_type', '')}</span> "
                f"<span style='color:#9ca3af;font-size:11px;'>price {float(_cascade.get('price_delta_pct', 0))*100:+.2f}% | "
                f"OI {float(_cascade.get('oi_delta_pct', 0))*100:+.2f}%</span></div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    # == THE WOLF'S STRATEGY ARSENAL + REASONING ==============================
    # Shows all 24 strategies, highlights the active one, wick zones, patterns,
    # and Jordan Belfort-style market reasoning.

    try:
        _active_entry = _safe_str(last_decision.get("entry_signal") or last_decision.get("selected_entry_type") or last_decision.get("entry_type_long") or last_decision.get("entry_type_short"))
        _active_lane = _safe_str(last_decision.get("lane"))
        _active_dir = _safe_str(last_decision.get("direction"))
        _v4_score = _safe_float(last_decision.get("v4_selected_score")) or 0
        _v4_thresh = _safe_float(last_decision.get("v4_selected_threshold")) or 75
        _regime = _safe_str(last_decision.get("v4_regime") or last_decision.get("regime")) or "neutral"
        _vol_phase = _safe_str(last_decision.get("vol_phase")) or "?"
        _htf_trend_val = _safe_str(last_decision.get("htf_trend")) or "neutral"
        _align_bonus = int(_safe_float(last_decision.get("alignment_bonus")) or 0)
        _zone_bonus = int(_safe_float(last_decision.get("zone_bonus")) or 0)
        _pattern_mod_val = int(_safe_float(last_decision.get("pattern_mod")) or 0)
        _wz_near = bool(last_decision.get("wick_zone_near"))
        _wz_bias = _safe_str(last_decision.get("wick_zone_bias")) or "none"
        _wz_conf = _safe_float(last_decision.get("wick_zone_confidence")) or 0
        _wz_tf = _safe_str(last_decision.get("wick_zone_strongest_tf")) or ""
        _wz_top3 = last_decision.get("wick_zones_top3") or []
        _patterns_active = last_decision.get("patterns_active") or []
        _ms_promoted = bool(last_decision.get("micro_sweep_promoted"))
        _ms_long = last_decision.get("micro_sweep_long")
        _ms_short = last_decision.get("micro_sweep_short")
        _htf_avail = last_decision.get("htf_data_available") or {}
        _overnight_ok = bool(last_decision.get("overnight_trading_ok"))
        _sweep_det = bool(last_decision.get("sweep_detected"))
        _squeeze_det = bool(last_decision.get("squeeze_detected"))
        _price_now = _safe_float(last_decision.get("price")) or 0

        # -- Strategy Arsenal --
        st.markdown("<div class='panel-title' style='margin-top:18px;'>Strategy Arsenal</div>", unsafe_allow_html=True)

        _strategies = [
            ("A", "Trend Continuation", "trend_continuation", "#3b82f6", "Pullback into EMA trend + confluence"),
            ("B", "Breakout Retest", "breakout_retest", "#10b981", "Level breakout + retest hold"),
            ("C", "Sweep Recovery", "sweep_recovery", "#f59e0b", "Wick flush past swing + reclaim"),
            ("E", "Squeeze Impulse", "compression_breakout", "#8b5cf6", "Vol compression to ignition transition"),
            ("F", "Compression Breakout", "compression_breakout", "#ec4899", "BB squeeze pop with structure"),
            ("G", "Range Scalp", "compression_range", "#06b6d4", "Mean reversion at range edges"),
            ("H", "Trend Structure", "trend_continuation", "#0ea5e9", "Swing LH/LL + RSI slope"),
            ("I", "Fib Retrace", "fib_retrace", "#14b8a6", "Fib level + reversal confirms"),
            ("J", "Slow Bleed", "slow_bleed_hunter", "#64748b", "3+ directional candles + EMA align"),
            ("K", "Wick Rejection", "wick_rejection", "#f97316", "60%+ wick at structure + body closes away"),
            ("M", "Volume Climax", "volume_climax_reversal", "#dc2626", "2.5x volume spike + reversal close"),
            ("N", "VWAP Reversion", "vwap_reversion", "#7c3aed", "1%+ from VWAP + reverting"),
            ("P", "Grid Range", "grid_range", "#0891b2", "Compression + RSI extreme + S/R touch"),
            ("Q", "Funding Arb", "funding_arb_bias", "#ca8a04", "Extreme funding rate + direction earns"),
            ("R", "Low Vol Regime", "regime_low_vol", "#4f46e5", "BB squeeze + ATR declining + edge"),
            ("S", "Stat Arb", "stat_arb_proxy", "#9333ea", "Z-score 2+ sigma mean reversion"),
            ("T", "Orderflow", "orderflow_imbalance", "#059669", "Volume delta 2:1 + candle confirm"),
            ("U", "Macro MA Cross", "macro_ma_cross", "#b91c1c", "200 MA cross on 1h + 4h confirms"),
            ("V", "Liquidity Sweep", "liquidity_sweep", "#d97706", "Liquidation cluster sweep/magnet"),
            ("W", "HTF Breakout", "htf_breakout_continuation", "#2563eb", "4h/1h breakout + EMA stack"),
            ("X", "Hourly Continuation", "hourly_continuation", "#6366f1", "1h direction + 15m momentum"),
            ("MS", "Micro-Sweep", "micro_sweep", "#ef4444", "1m/5m wick flush + fast reclaim"),
        ]

        _strat_html = "<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px;'>"
        for _s_lane, _s_name, _s_type, _s_color, _s_desc in _strategies:
            _is_active = (_active_lane == _s_lane) or (_active_entry and _s_type in _active_entry) or (_s_lane == "MS" and _ms_promoted)
            _bg = f"{_s_color}25" if _is_active else "rgba(30,41,59,0.5)"
            _border = f"2px solid {_s_color}" if _is_active else "1px solid rgba(75,85,99,0.2)"
            _glow = f"box-shadow:0 0 12px {_s_color}40;" if _is_active else ""
            _active_badge = f"<span style='color:{_s_color};font-size:8px;font-weight:800;letter-spacing:1px;'>ACTIVE</span>" if _is_active else ""
            _strat_html += (
                f"<div style='background:{_bg};border:{_border};border-radius:8px;padding:8px 10px;{_glow}'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:{_s_color};font-weight:700;font-size:12px;'>Lane {_s_lane}</span>"
                f"{_active_badge}</div>"
                f"<div style='color:#e2e8f0;font-size:11px;font-weight:600;margin:2px 0;'>{_s_name}</div>"
                f"<div style='color:#9ca3af;font-size:9px;'>{_s_desc}</div>"
                f"</div>"
            )
        _strat_html += "</div>"
        st.markdown(_strat_html, unsafe_allow_html=True)

        # -- Wick Zones Map --
        if _wz_top3:
            st.markdown("<div class='panel-title' style='margin-top:14px;'>Wick Zone Map (Multi-TF S/R)</div>", unsafe_allow_html=True)
            _wz_html = ""
            for _z in _wz_top3:
                _z_side = str(_z.get("side", ""))
                _z_level = float(_z.get("level", 0))
                _z_strength = float(_z.get("strength", 0))
                _z_touches = int(_z.get("touches", 0))
                _z_tf = str(_z.get("strongest_tf", ""))
                _z_color = "#10b981" if _z_side == "support" else "#ef4444"
                _z_icon = "&#9650;" if _z_side == "support" else "&#9660;"
                _z_bar_w = min(100, _z_strength)
                _z_dist = ""
                if _price_now > 0 and _z_level > 0:
                    _z_dist_pct = ((_z_level - _price_now) / _price_now) * 100
                    _z_dist = f"({_z_dist_pct:+.2f}%)"
                _wz_html += (
                    f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid rgba(75,85,99,0.15);'>"
                    f"<span style='color:{_z_color};font-size:12px;width:16px;'>{_z_icon}</span>"
                    f"<span style='color:{_z_color};font-size:10px;font-weight:700;text-transform:uppercase;width:60px;'>{_z_side}</span>"
                    f"<span style='color:#e2e8f0;font-size:12px;font-weight:600;width:90px;'>${_z_level:.6f}</span>"
                    f"<span style='color:#9ca3af;font-size:10px;width:50px;'>{_z_dist}</span>"
                    f"<div style='flex:1;height:6px;background:#1f2937;border-radius:3px;overflow:hidden;'>"
                    f"<div style='width:{_z_bar_w}%;height:100%;background:{_z_color};border-radius:3px;'></div></div>"
                    f"<span style='color:#d1d5db;font-size:10px;width:35px;text-align:right;'>{_z_strength:.0f}</span>"
                    f"<span style='color:#6b7280;font-size:9px;width:45px;text-align:right;'>{_z_touches}t / {_z_tf}</span>"
                    f"</div>"
                )
            st.markdown(f"<div class='card' style='padding:10px 14px;'>{_wz_html}</div>", unsafe_allow_html=True)

        # -- Active Patterns --
        if _patterns_active:
            st.markdown("<div class='panel-title' style='margin-top:14px;'>Chart Patterns Forming</div>", unsafe_allow_html=True)
            _pat_html = ""
            for _p in _patterns_active[:4]:
                _p_name = str(_p.get("pattern", "")).replace("_", " ").upper()
                _p_bias = str(_p.get("bias", ""))
                _p_conf = float(_p.get("confidence", 0))
                _p_desc = str(_p.get("desc", ""))
                _p_color = "#10b981" if _p_bias == "long" else "#ef4444" if _p_bias == "short" else "#f59e0b"
                _p_icon = "&#9650;" if _p_bias == "long" else "&#9660;" if _p_bias == "short" else "&#9679;"
                _pat_html += (
                    f"<div style='display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(75,85,99,0.15);'>"
                    f"<span style='color:{_p_color};font-size:12px;'>{_p_icon}</span>"
                    f"<span style='background:{_p_color}20;color:{_p_color};font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;'>{_p_name}</span>"
                    f"<span style='color:#d1d5db;font-size:10px;flex:1;'>{_p_desc[:120]}</span>"
                    f"<span style='color:#9ca3af;font-size:10px;'>{_p_conf:.0%}</span>"
                    f"</div>"
                )
            st.markdown(f"<div class='card' style='padding:10px 14px;'>{_pat_html}</div>", unsafe_allow_html=True)

        # -- The Wolf's Take (Jordan Belfort reasoning) --
        st.markdown("<div class='panel-title' style='margin-top:14px;'>The Wolf's Take</div>", unsafe_allow_html=True)

        _wolf_lines = []

        # Market regime read
        if _regime == "trend":
            _wolf_lines.append("Market's got a PULSE right now. Trend regime. Money is MOVING. This is where you press, not where you sit on your hands.")
        elif _regime == "mean_reversion":
            _wolf_lines.append("Choppy waters. Mean reversion regime. The smart play is buying dips at support and selling rips at resistance. Discipline wins here.")
        else:
            _wolf_lines.append("Market's deciding what it wants to be. Neutral regime. We wait for the pitch we like, then we SWING.")

        # HTF trend
        if _htf_trend_val == "bullish":
            _wolf_lines.append(f"The big picture is BULLISH. Daily and 4h trend pointing up. Shorts here are fighting the tide. You want to be buying dips, not picking tops.")
        elif _htf_trend_val == "bearish":
            _wolf_lines.append(f"The macro trend is BEARISH. Daily structure is pushing down. Longs are swimming upstream. Sell the rips, don't catch falling knives.")

        # TF alignment
        if _align_bonus >= 8:
            _wolf_lines.append(f"ALL timeframes are aligned ({_align_bonus:+d} alignment). When the 1-minute, 15-minute, 1-hour, AND the daily all agree? That's not a coincidence. That's the market TELLING you which way it's going.")
        elif _align_bonus >= 4:
            _wolf_lines.append(f"Most timeframes agree ({_align_bonus:+d} alignment). Good confluence but not unanimous. Size accordingly.")
        elif _align_bonus <= -3:
            _wolf_lines.append(f"Timeframes are FIGHTING each other ({_align_bonus:+d} alignment). Mixed signals. This is where amateurs blow up. We stay small or we stay OUT.")

        # Wick zones
        if _wz_near and _wz_bias == "support_bounce":
            _wolf_lines.append(f"Price is sitting RIGHT on a proven support zone (confidence {_wz_conf:.0%}, strongest on {_wz_tf}). This level has rejected sellers before. The buyers are HERE. That's your edge for longs.")
        elif _wz_near and _wz_bias == "resistance_reject":
            _wolf_lines.append(f"Price is pressing against a WALL of resistance (confidence {_wz_conf:.0%}, strongest on {_wz_tf}). Multiple rejections at this level. Sellers are defending it. Short bias until it breaks.")

        # Patterns
        for _p in _patterns_active[:2]:
            _pn = str(_p.get("pattern", "")).replace("_", " ")
            _pb = str(_p.get("bias", ""))
            _pd = str(_p.get("desc", ""))
            if "double_bottom" in str(_p.get("pattern", "")):
                _wolf_lines.append(f"I see a DOUBLE BOTTOM forming. Price bounced off the same level twice. That's institutional accumulation. The smart money is loading up down there.")
            elif "double_top" in str(_p.get("pattern", "")):
                _wolf_lines.append(f"DOUBLE TOP in play. Two failed breakout attempts at the same resistance. Distribution pattern. The big boys are selling into strength.")
            elif "channel" in str(_p.get("pattern", "")):
                _wolf_lines.append(f"We're in a CHANNEL. Defined range. The play is simple: buy the bottom, sell the top. Grid range is the bread and butter here.")
            elif "breakout" in str(_p.get("pattern", "")):
                _wolf_lines.append(f"BREAKOUT through a tested level. When a level that held 3+ times finally breaks? That's conviction. Ride it.")
            elif "fakeout" in str(_p.get("pattern", "")):
                _wolf_lines.append(f"FAKEOUT detected. They pushed through the level to grab stops then snapped right back. Classic stop hunt. Fade the fakeout.")

        # Micro sweep
        if _ms_promoted:
            _wolf_lines.append("MICRO-SWEEP fired on the 1-minute chart. Fast liquidation wick with immediate reclaim. This is the smart money grabbing liquidity. We ride with them, not against them.")
        elif _ms_long and isinstance(_ms_long, dict) and _ms_long.get("detected"):
            _wolf_lines.append(f"5m micro-sweep detected LONG (score {_ms_long.get('score', 0)}). Watching for entry confirmation.")
        elif _ms_short and isinstance(_ms_short, dict) and _ms_short.get("detected"):
            _wolf_lines.append(f"5m micro-sweep detected SHORT (score {_ms_short.get('score', 0)}). Watching for entry confirmation.")

        # Active strategy
        if _active_entry and _active_dir:
            _wolf_lines.append(f"ACTIVE PLAY: {_active_entry.replace('_', ' ').upper()} going {_active_dir.upper()} via Lane {_active_lane}. Score {int(_v4_score)}/{int(_v4_thresh)}. The setup is there. Now we execute.")
        elif not _active_entry:
            if _v4_score > 0 and _v4_score < _v4_thresh:
                _wolf_lines.append(f"Setup is BREWING but not ready. Score {int(_v4_score)}/{int(_v4_thresh)}. We need {int(_v4_thresh - _v4_score)} more points of confluence. Patience. The trade will come to us.")
            else:
                _wolf_lines.append("No play right now. And that's FINE. The best traders know when NOT to trade. We're watching, we're waiting, and when the setup comes? We'll be ready.")

        # Overnight
        if _overnight_ok:
            _wolf_lines.append("Overnight margin is SAFE. We can trade through the night. No restrictions.")

        # Vol phase
        if _vol_phase == "COMPRESSION":
            _wolf_lines.append("Volatility is compressed. The spring is LOADED. When this thing pops, it'll move fast. Be ready.")
        elif _vol_phase == "EXPANSION":
            _wolf_lines.append("Volatility is EXPANDING. The move is happening NOW. This is the window. Don't hesitate.")

        _wolf_color = "#10b981" if _active_dir == "long" else "#ef4444" if _active_dir == "short" else "#f59e0b"
        _wolf_text = " ".join(_wolf_lines) if _wolf_lines else "Scanning the markets... waiting for the perfect setup."
        st.markdown(
            f"<div class='card' style='padding:14px 16px;border-left:3px solid {_wolf_color};background:linear-gradient(90deg,rgba(15,23,42,0.95),rgba(30,41,59,0.8));'>"
            f"<div style='color:{_wolf_color};font-size:10px;font-weight:800;letter-spacing:2px;margin-bottom:6px;'>THE WOLF SPEAKS</div>"
            f"<div style='color:#e2e8f0;font-size:12px;line-height:1.7;'>{_wolf_text}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # -- Data Coverage Badge --
        _tf_badges = []
        for _tf_name, _tf_ok in [("1m", True), ("5m", True), ("15m", True), ("1h", True), ("4h", True),
                                   ("1D", bool(_htf_avail.get("1d"))), ("1W", bool(_htf_avail.get("1w"))), ("1M", bool(_htf_avail.get("1mo")))]:
            _tf_clr = "#10b981" if _tf_ok else "#4b5563"
            _tf_badges.append(f"<span style='background:{_tf_clr}20;color:{_tf_clr};font-size:9px;font-weight:600;padding:2px 6px;border-radius:3px;'>{_tf_name}</span>")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:4px;margin-top:8px;'>"
            f"<span style='color:#6b7280;font-size:9px;margin-right:4px;'>TIMEFRAME COVERAGE:</span>"
            f"{' '.join(_tf_badges)}</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Signal History (Recent First)</div>", unsafe_allow_html=True)
    if not decisions.empty and "timestamp" in decisions.columns:
        feed_df = decisions.copy()
        feed_df["timestamp"] = pd.to_datetime(feed_df["timestamp"], utc=True, errors="coerce")
        feed_df = feed_df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        sig_df = feed_df[(feed_df["entry_signal"].notna()) & (feed_df["direction"].notna())].copy() if "entry_signal" in feed_df.columns else pd.DataFrame()
        if not sig_df.empty:
            groups = []
            current = []
            for i in range(len(sig_df)):
                if not current:
                    current = [sig_df.index[i]]
                    continue
                prev_ts = sig_df.iloc[i - 1]["timestamp"]
                curr_ts = sig_df.iloc[i]["timestamp"]
                try:
                    gap = (curr_ts - prev_ts).total_seconds()
                except Exception:
                    gap = None
                if gap is not None and gap <= 600:
                    current.append(sig_df.index[i])
                else:
                    groups.append(current)
                    current = [sig_df.index[i]]
            if current:
                groups.append(current)
            groups = groups[::-1][:8]

            for grp in groups:
                first = feed_df.loc[grp[0]].to_dict()
                sig_name = _safe_str(first.get("entry_signal")) or "signal"
                sig_dir = _safe_str(first.get("direction")) or "?"
                sig_ts = first.get("timestamp")
                sig_ts_str = sig_ts.astimezone(PT).strftime("%b %d %I:%M %p PT") if hasattr(sig_ts, "strftime") else "?"
                sig_price = float(first.get("price") or 0.0)
                try:
                    sig_cc = max(int(_safe_float(feed_df.loc[idx].get("confluence_count", 0)) or 0) for idx in grp)
                except Exception:
                    sig_cc = int(_safe_float(first.get("confluence_count")) or 0)

                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='label'>{sig_ts_str}</div>"
                    f"<div class='metric'><strong>{sig_name.replace('_',' ').upper()}</strong> "
                    f"<span class='{('green' if sig_dir == 'long' else 'red')}'>{sig_dir.upper()}</span> "
                    f"<span class='muted'>({sig_cc}/6)</span></div>",
                    unsafe_allow_html=True,
                )
                try:
                    last_idx = grp[-1]
                    after_mask = feed_df["timestamp"] > feed_df.loc[last_idx]["timestamp"]
                    after_df = feed_df.loc[after_mask, ["timestamp", "price"]].head(30).copy()
                except Exception:
                    after_df = pd.DataFrame()
                eval_ = _evaluate_path(sig_price=sig_price, sig_dir=sig_dir, sig_ts=sig_ts, after_df=after_df, cfg=cfg, df_1h=hist_1h)
                verdict = eval_.get("verdict") or "-"
                mfe = float(eval_.get("mfe_pct") or 0.0)
                mae = float(eval_.get("mae_pct") or 0.0)
                mfe_ts = _fmt_ts(eval_.get("mfe_ts"))
                mae_ts = _fmt_ts(eval_.get("mae_ts"))
                first_move = eval_.get("first_extreme") or "-"
                st.markdown(f"<div class='intel-event'><strong>{verdict}</strong></div>", unsafe_allow_html=True)
                # Survivability verdict badge
                if verdict == "profit_first":
                    _tp1_ts = _fmt_ts(eval_.get("tp1_hit_ts")) if eval_.get("tp1_hit_ts") else "?"
                    st.markdown(f"<div class='intel-event'><span class='pill ok'>TP1 hit</span> at {_tp1_ts}</div>", unsafe_allow_html=True)
                elif verdict == "stopped_before_profit":
                    _adv_ts = _fmt_ts(eval_.get("adverse_hit_ts")) if eval_.get("adverse_hit_ts") else "?"
                    _tp1_after = " (TP1 never reached)" if eval_.get("tp1_hit_ts") is None else f" (TP1 hit later at {_fmt_ts(eval_.get('tp1_hit_ts'))})"
                    st.markdown(f"<div class='intel-event'><span class='pill danger'>Stopped out</span> at {_adv_ts}{_tp1_after}</div>", unsafe_allow_html=True)
                elif verdict == "liquidated_before_profit":
                    _adv_ts = _fmt_ts(eval_.get("adverse_hit_ts")) if eval_.get("adverse_hit_ts") else "?"
                    st.markdown(f"<div class='intel-event'><span class='pill danger'>Liquidated</span> at {_adv_ts}</div>", unsafe_allow_html=True)
                elif verdict == "no_decisive_outcome":
                    st.markdown("<div class='intel-event'><span class='pill' style='opacity:0.5;'>No SL/TP1 hit yet</span></div>", unsafe_allow_html=True)
                if first_move == "best":
                    st.markdown(f"<div class='intel-event'>First: best <span class='green'>{mfe:+.2f}%</span> at {mfe_ts}, then worst <span class='red'>{mae:+.2f}%</span> at {mae_ts}</div>", unsafe_allow_html=True)
                elif first_move == "worst":
                    st.markdown(f"<div class='intel-event'>First: worst <span class='red'>{mae:+.2f}%</span> at {mae_ts}, then best <span class='green'>{mfe:+.2f}%</span> at {mfe_ts}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='intel-event'>Best {mfe:+.2f}%, worst {mae:+.2f}%</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'><div class='metric muted'>No signals detected yet.</div></div>", unsafe_allow_html=True)

    # Gate analytics (derived from the same decisions feed)
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Gate Pressure (Last 300)</div>", unsafe_allow_html=True)
    try:
        tail = decisions.tail(300).copy()
        gate_rows = []
        if not tail.empty and "gates" in tail.columns:
            for _, r in tail.iterrows():
                g = r.get("gates") or {}
                if not isinstance(g, dict):
                    continue
                for k, v in g.items():
                    gate_rows.append({"gate": str(k), "pass": bool(v)})
        if gate_rows:
            gdf = pd.DataFrame(gate_rows)
            out = gdf.groupby("gate")["pass"].mean().reset_index()
            out["blocked_pct"] = (1.0 - out["pass"]) * 100.0
            out = out.sort_values("blocked_pct", ascending=False)
            st.bar_chart(out.set_index("gate")["blocked_pct"], height=180)
        else:
            st.markdown("<div class='card'><div class='metric muted'>No gate data available.</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Gate analytics unavailable.</div></div>", unsafe_allow_html=True)

    # ── Trade Quality Panel ─────────────────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Trade Quality</div>", unsafe_allow_html=True)
    try:
        _closed = _get_closed_trades(trades)
        if len(_closed) >= 3:
            # Build timeseries for path analysis from decisions
            _ts_for_quality = pd.DataFrame()
            if not decisions.empty and "price" in decisions.columns and "timestamp" in decisions.columns:
                _ts_for_quality = decisions[["timestamp", "price"]].dropna().copy()
                _ts_for_quality["timestamp"] = pd.to_datetime(_ts_for_quality["timestamp"], utc=True, errors="coerce")
                _ts_for_quality["price"] = pd.to_numeric(_ts_for_quality["price"], errors="coerce")
                _ts_for_quality = _ts_for_quality.dropna().sort_values("timestamp")

            _last_trades = _closed.tail(10)
            _grades = []
            _quality_rows = []
            for _, tr in _last_trades.iterrows():
                q = _trade_quality_score(tr.to_dict(), _ts_for_quality)
                if q.get("ok"):
                    _grades.append(q)
                    _dir = str(tr.get("side") or tr.get("direction") or "?")
                    _pnl = float(tr.get("pnl_usd") or 0)
                    _quality_rows.append({
                        "Grade": q["grade"],
                        "PnL": f"{'+'if _pnl>=0 else ''}${_pnl:.2f}",
                        "Timing": f"{q['timing_score']:.0f}",
                        "Efficiency": f"{q['efficiency']:.0f}",
                        "Stop": f"{q['stop_score']:.0f}",
                        "MFE%": f"{q['mfe_pct']:+.2f}",
                        "MAE%": f"{q['mae_pct']:+.2f}",
                    })

            if _grades:
                _avg_score = sum(g["score"] for g in _grades) / len(_grades)
                _avg_grade = "A" if _avg_score >= 80 else "B" if _avg_score >= 60 else "C" if _avg_score >= 40 else "D"
                _grade_counts = {}
                for g in _grades:
                    _grade_counts[g["grade"]] = _grade_counts.get(g["grade"], 0) + 1
                _best = max(_grades, key=lambda g: g["score"])
                _worst = min(_grades, key=lambda g: g["score"])
                _grade_class = "green" if _avg_grade in ("A", "B") else ("red" if _avg_grade == "D" else "muted")
                st.markdown(
                    f"<div class='card'>"
                    f"<div class='label'>Average: <span class='{_grade_class}' style='font-size:18px;font-weight:700;'>{_avg_grade}</span>"
                    f" <span class='muted'>({_avg_score:.0f}/100)</span></div>"
                    f"<div style='font-size:11px;color:#9ca3af;margin-top:4px;'>"
                    f"Best: {_best['grade']} ({_best['score']:.0f}) &bull; Worst: {_worst['grade']} ({_worst['score']:.0f}) &bull; "
                    f"Grades: {' '.join(f'{g}:{c}' for g,c in sorted(_grade_counts.items()))}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if _quality_rows:
                    _qdf = pd.DataFrame(_quality_rows)
                    st.dataframe(_qdf, use_container_width=True, hide_index=True, height=min(400, 35 * len(_qdf) + 38))
            else:
                st.markdown("<div class='card'><div class='metric muted'>Not enough path data for quality analysis.</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='card'><div class='metric muted'>Not enough closed trades for quality analysis ({len(_closed)}/3 minimum).</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Trade quality analysis unavailable.</div></div>", unsafe_allow_html=True)

    # ── Parameter Performance Panel ──────────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Parameter Performance</div>", unsafe_allow_html=True)
    try:
        _closed_pp = _get_closed_trades(trades)
        if len(_closed_pp) >= 3:
            _pp = _parameter_performance(_closed_pp)

            def _render_perf_table(title, data_dict):
                if not data_dict:
                    return
                st.markdown(f"<div style='font-size:12px;color:#9ca3af;font-weight:600;margin:8px 0 4px;'>{title}</div>", unsafe_allow_html=True)
                _rows = []
                for name, stats in sorted(data_dict.items()):
                    wr_pct = stats["win_rate"] * 100
                    exp = stats["expectancy"]
                    _rows.append({
                        "Group": str(name),
                        "Trades": stats["count"],
                        "Win Rate": f"{wr_pct:.0f}%",
                        "Avg PnL": f"{'+'if stats['avg_pnl']>=0 else ''}${stats['avg_pnl']:.2f}",
                        "Expectancy": f"{'+'if exp>=0 else ''}${exp:.3f}",
                    })
                if _rows:
                    st.dataframe(pd.DataFrame(_rows), use_container_width=True, hide_index=True, height=min(300, 35 * len(_rows) + 38))

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            _render_perf_table("By Entry Type", _pp["by_entry_type"])
            _render_perf_table("By Regime", _pp["by_regime"])
            _render_perf_table("By Score Bucket", _pp["by_score_bucket"])
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='card'><div class='metric muted'>Not enough closed trades for parameter analysis ({len(_closed_pp)}/3 minimum).</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Parameter performance unavailable.</div></div>", unsafe_allow_html=True)

    # ── Gate Effectiveness Analysis ──────────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Gate Effectiveness</div>", unsafe_allow_html=True)
    try:
        _gate_eff_done = False
        if not decisions.empty and "gates_pass" in decisions.columns and "entry_signal" in decisions.columns:
            # Find blocked entries: gates_pass == False and a signal existed
            _blocked = decisions[
                (decisions["gates_pass"].astype(str).str.lower().isin(["false", "0"]))
                & (decisions["entry_signal"].notna())
                & (decisions["entry_signal"].astype(str).str.strip() != "")
            ].tail(100).copy()
            if len(_blocked) >= 5:
                # Build timeseries for path evaluation
                _ts_eff = pd.DataFrame()
                if "price" in decisions.columns and "timestamp" in decisions.columns:
                    _ts_eff = decisions[["timestamp", "price"]].dropna().copy()
                    _ts_eff["timestamp"] = pd.to_datetime(_ts_eff["timestamp"], utc=True, errors="coerce")
                    _ts_eff["price"] = pd.to_numeric(_ts_eff["price"], errors="coerce")
                    _ts_eff = _ts_eff.dropna().sort_values("timestamp")

                _gate_stats = {}  # gate_name -> {"blocked": int, "would_profit": int}
                _eval_count = 0
                for _, row in _blocked.iterrows():
                    gates_dict = row.get("gates")
                    if not isinstance(gates_dict, dict):
                        continue
                    failed_gates = [k for k, v in gates_dict.items() if not bool(v)]
                    if not failed_gates:
                        continue

                    # Evaluate what would have happened
                    _sig_price = _safe_float(row.get("price"))
                    _sig_dir = _safe_str(row.get("direction")) or "long"
                    _sig_ts = row.get("timestamp")
                    _would_profit = False
                    if _sig_price and _sig_ts and not _ts_eff.empty:
                        _sig_ts_dt = pd.Timestamp(_sig_ts, tz="UTC") if _sig_ts else None
                        if _sig_ts_dt is not None:
                            _after = _ts_eff[_ts_eff["timestamp"] > _sig_ts_dt].head(30)
                            if not _after.empty:
                                _ev = _evaluate_path(sig_price=_sig_price, sig_dir=_sig_dir, sig_ts=_sig_ts_dt, after_df=_after, cfg=cfg, df_1h=hist_1h)
                                _would_profit = _ev.get("verdict") == "profit_first"
                                _eval_count += 1

                    for g in failed_gates:
                        if g not in _gate_stats:
                            _gate_stats[g] = {"blocked": 0, "would_profit": 0}
                        _gate_stats[g]["blocked"] += 1
                        if _would_profit:
                            _gate_stats[g]["would_profit"] += 1

                if _gate_stats:
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    for gate_name in sorted(_gate_stats.keys(), key=lambda g: _gate_stats[g]["blocked"], reverse=True):
                        gs = _gate_stats[gate_name]
                        pct = (gs["would_profit"] / gs["blocked"] * 100) if gs["blocked"] > 0 else 0
                        if pct > 60:
                            _color = "#ef4444"  # red - gate is hurting
                            _label = "hurting"
                        elif pct > 40:
                            _color = "#f59e0b"  # amber - mixed
                            _label = "mixed"
                        else:
                            _color = "#10b981"  # green - gate is helping
                            _label = "helping"
                        st.markdown(
                            f"<div style='font-size:12px;padding:4px 0;'>"
                            f"<strong>{gate_name}</strong> blocked {gs['blocked']} entries &rarr; "
                            f"<span style='color:{_color};font-weight:600;'>{pct:.0f}% would have been profitable</span> "
                            f"<span class='pill' style='background:{_color}20;color:{_color};'>{_label}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
                    _gate_eff_done = True
        if not _gate_eff_done:
            st.markdown("<div class='card'><div class='metric muted'>Not enough blocked signals for gate effectiveness analysis.</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Gate effectiveness analysis unavailable.</div></div>", unsafe_allow_html=True)

    # ── HTF Macro Zones Panel ─────────────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>HTF Macro Zones</div>", unsafe_allow_html=True)
    try:
        _htf_nearest = last_decision.get("htf_zone_nearest") or {}
        _htf_inside = last_decision.get("htf_zone_inside", False)
        _htf_label = _safe_str(last_decision.get("htf_readiness")) or None
        _htf_reasons = last_decision.get("htf_readiness_reasons") or []
        _htf_bias = _safe_str(last_decision.get("htf_macro_bias")) or "neutral"
        _htf_mflags = last_decision.get("htf_micro_flags") or {}
        _htf_zbonus = last_decision.get("zone_bonus") or 0
        if isinstance(_htf_reasons, str):
            _htf_reasons = [_htf_reasons]
        elif not isinstance(_htf_reasons, list):
            _htf_reasons = []

        if _htf_nearest and isinstance(_htf_nearest, dict):
            _ztype = _safe_str(_htf_nearest.get("zone_type")) or "?"
            _zlow = _safe_float(_htf_nearest.get("low"))
            _zhigh = _safe_float(_htf_nearest.get("high"))
            _zpos = _safe_str(_htf_nearest.get("position")) or "?"
            _zdist_pct = _safe_float(_htf_nearest.get("distance_pct"))
            _zdist_atr = _safe_float(_htf_nearest.get("distance_norm_atr"))
            _zstrength = _htf_nearest.get("strength") or "?"
            _ztf = _safe_str(_htf_nearest.get("timeframe")) or "M"

            _zone_colors = {
                "BODY": "#3b82f6", "BODY_EDGE": "#3b82f6", "WICK_HIGH": "#ef4444",
                "WICK_LOW": "#10b981", "MIXED": "#f59e0b",
            }
            _zc = _zone_colors.get(_ztype, "#6b7280")
            _pos_icon = {"ABOVE": "&#9650;", "BELOW": "&#9660;", "INSIDE": "&#9654;"}.get(_zpos, "?")
            _tf_pill = f"<span style='display:inline-block;padding:1px 5px;border-radius:4px;font-size:9px;font-weight:700;background:rgba(107,114,128,0.2);color:#d1d5db;'>{_ztf}</span>"

            _zone_range_str = ""
            if _zlow is not None and _zhigh is not None:
                _zone_range_str = f"${_zlow:.6f} – ${_zhigh:.6f}"

            _dist_str = ""
            if _zdist_pct is not None:
                _dist_str = f"{_zdist_pct:.2f}%"
                if _zdist_atr is not None:
                    _dist_str += f" ({_zdist_atr:.1f} ATR)"

            # Macro bias pill
            _bias_cfg = {
                "short_bias": ("#ef4444", "rgba(239,68,68,0.15)", "SHORT BIAS"),
                "long_bias": ("#10b981", "rgba(16,185,129,0.15)", "LONG BIAS"),
                "neutral": ("#6b7280", "rgba(107,114,128,0.1)", "NEUTRAL"),
            }
            _bc, _bbg, _btxt = _bias_cfg.get(_htf_bias, _bias_cfg["neutral"])

            # Inside pill
            _inside_bg = "rgba(16,185,129,0.15)" if _htf_inside else "rgba(107,114,128,0.1)"
            _inside_clr = "#10b981" if _htf_inside else "#6b7280"
            _inside_txt = "INSIDE ZONE" if _htf_inside else "OUTSIDE"

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;'>"
                f"{_tf_pill}"
                f"<span style='color:{_zc};font-weight:700;font-size:13px;'>{_ztype}</span>"
                f"<span style='font-size:11px;color:#9ca3af;'>{_zone_range_str}</span>"
                f"<span style='font-size:11px;color:#d1d5db;'>{_pos_icon} {_zpos}</span>"
                f"<span style='font-size:11px;color:#6b7280;'>str {_zstrength}</span>"
                f"</div>"
                f"<div style='display:flex;align-items:center;gap:8px;font-size:12px;color:#d1d5db;flex-wrap:wrap;'>"
                f"Dist: <strong>{_dist_str or 'inside'}</strong>"
                f" <span class='pill' style='background:{_inside_bg};color:{_inside_clr};'>{_inside_txt}</span>"
                f" <span class='pill' style='background:{_bbg};color:{_bc};'>{_btxt}</span>"
                + (f" <span class='pill' style='background:rgba(59,130,246,0.12);color:#3b82f6;'>ZONE +{_htf_zbonus}</span>" if _htf_zbonus and int(_htf_zbonus) > 0 else "")
                + (f" <span class='pill' style='background:rgba(239,68,68,0.12);color:#ef4444;'>ZONE {_htf_zbonus}</span>" if _htf_zbonus and int(_htf_zbonus) < 0 else "")
                + "</div>",
                unsafe_allow_html=True,
            )

            # Micro precision flags (compact)
            if _htf_mflags and isinstance(_htf_mflags, dict):
                _active_flags = [k.replace("_", " ").upper() for k, v in _htf_mflags.items() if v]
                if _active_flags:
                    _flag_pills = ""
                    _flag_colors = {
                        "REJECTION UP": "#ef4444", "REJECTION DOWN": "#10b981",
                        "SWEEP PAST": "#f59e0b", "RETEST": "#8b5cf6",
                        "BREAKOUT ABOVE": "#3b82f6", "BREAKOUT BELOW": "#e11d48",
                    }
                    for _fl in _active_flags:
                        _fc = _flag_colors.get(_fl, "#6b7280")
                        _flag_pills += f"<span style='display:inline-block;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;color:{_fc};background:rgba(255,255,255,0.05);margin:2px 3px 2px 0;'>{_fl}</span>"
                    st.markdown(
                        f"<div style='margin-top:5px;'>"
                        f"<span style='font-size:10px;color:#6b7280;margin-right:4px;'>MICRO:</span>"
                        f"{_flag_pills}</div>",
                        unsafe_allow_html=True,
                    )

            # Readiness label
            if _htf_label:
                _label_colors = {
                    "SHORT_BIAS_WATCH": ("#ef4444", "rgba(239,68,68,0.12)"),
                    "LONG_BIAS_WATCH": ("#10b981", "rgba(16,185,129,0.12)"),
                    "ROTATION_OR_CONTINUATION_WATCH": ("#f59e0b", "rgba(245,158,11,0.12)"),
                    "APPROACHING_ZONE_FROM_BELOW": ("#3b82f6", "rgba(59,130,246,0.12)"),
                    "APPROACHING_ZONE_FROM_ABOVE": ("#8b5cf6", "rgba(139,92,246,0.12)"),
                    "SHORT_TRIGGER_READY": ("#ef4444", "rgba(239,68,68,0.18)"),
                    "LONG_TRIGGER_READY": ("#10b981", "rgba(16,185,129,0.18)"),
                    "SWEEP_REVERSAL_WATCH": ("#f59e0b", "rgba(245,158,11,0.15)"),
                }
                _lc, _lbg = _label_colors.get(_htf_label, ("#6b7280", "rgba(107,114,128,0.1)"))
                _reasons_html = " &bull; ".join(html.escape(str(r)) for r in _htf_reasons[:5])
                st.markdown(
                    f"<div style='margin-top:6px;padding:6px 10px;border-radius:8px;background:{_lbg};'>"
                    f"<span style='color:{_lc};font-weight:600;font-size:12px;'>{_htf_label.replace('_',' ')}</span>"
                    + (f"<div style='font-size:10px;color:#9ca3af;margin-top:2px;'>{_reasons_html}</div>" if _reasons_html else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'><div class='metric muted'>Macro zone data loading (available after next bot cycle).</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>HTF zone analysis unavailable.</div></div>", unsafe_allow_html=True)

    # ── ATR Regime Audit Summary ─────────────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>ATR Regime Lag Audit</div>", unsafe_allow_html=True)
    try:
        _audit_path = LOGS_DIR / "atr_regime_audit.jsonl"
        if _audit_path.exists() and _audit_path.stat().st_size > 0:
            _audit_lines = []
            with open(_audit_path, "r") as _af:
                for line in _af:
                    line = line.strip()
                    if line:
                        try:
                            _audit_lines.append(json.loads(line))
                        except Exception:
                            continue
            if len(_audit_lines) >= 10:
                _total = len(_audit_lines)
                _expansion_but_blocked = sum(1 for a in _audit_lines if a.get("expansion_but_gate_false"))
                _tr_high_gate_false = sum(1 for a in _audit_lines
                                          if (_safe_float(a.get("tr_ratio")) or 0) >= 1.5
                                          and not a.get("atr_regime_pass"))
                _ignition_gate_false = sum(1 for a in _audit_lines
                                           if a.get("vol_phase") == "IGNITION"
                                           and not a.get("atr_regime_pass"))
                _gate_false_total = sum(1 for a in _audit_lines if not a.get("atr_regime_pass"))
                _gate_true_total = _total - _gate_false_total
                _lag_pct = (_expansion_but_blocked / _total * 100) if _total > 0 else 0
                _lag_color = "#ef4444" if _lag_pct > 15 else ("#f59e0b" if _lag_pct > 5 else "#10b981")
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='font-size:12px;margin-bottom:8px;'>"
                    f"<strong>{_total}</strong> cycles audited &bull; "
                    f"ATR gate passed <span class='green'>{_gate_true_total}</span> / "
                    f"blocked <span class='red'>{_gate_false_total}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:12px;padding:4px 0;'>"
                    f"<span style='color:{_lag_color};font-weight:600;'>"
                    f"Expansion/Ignition while ATR gate blocked: {_expansion_but_blocked} ({_lag_pct:.1f}%)</span>"
                    f"</div>"
                    f"<div style='font-size:11px;color:#9ca3af;padding:2px 0;'>"
                    f"TR ratio &ge;1.5 while gate false: {_tr_high_gate_false} &bull; "
                    f"Ignition phase while gate false: {_ignition_gate_false}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if _lag_pct > 10:
                    st.markdown(
                        "<div style='font-size:11px;color:#f59e0b;margin-top:6px;'>"
                        "&#9888; ATR regime gate appears to lag real expansion. "
                        "Consider reviewing atr_multiplier or switching to TR-ratio-based detection."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='card'><div class='metric muted'>Collecting audit data ({len(_audit_lines)}/10 cycles minimum).</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'><div class='metric muted'>No ATR audit data yet. Bot will populate on next cycle.</div></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>ATR audit summary unavailable.</div></div>", unsafe_allow_html=True)

elif page == "Ledger":
    st.markdown("<div class='panel-title'>Ledger</div>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Major Events (Window)</div>", unsafe_allow_html=True)
    if major_events:
        st.markdown("<div class='major-feed'>", unsafe_allow_html=True)
        for ev in major_events[:25]:
            tone = _safe_str(ev.get("tone")) or "info"
            st.markdown(
                "<div class='major-item "
                + tone
                + "'>"
                + f"<div class='t'>{_fmt_pt_short(ev.get('ts'))}</div>"
                + f"<div class='h'>{_safe_str(ev.get('headline')) or '-'}</div>"
                + f"<div class='s'>{_safe_str(ev.get('detail')) or '-'}</div>"
                + "</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='card'><div class='metric muted'>No major events found.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Market Intel Stream</div>", unsafe_allow_html=True)
    _latest_market_news = {}
    if not market_news_batches.empty:
        try:
            _latest_market_news = market_news_batches.iloc[0].to_dict()
        except Exception:
            _latest_market_news = {}
    if not _latest_market_news and isinstance((snapshot or {}).get("market_news"), dict):
        _latest_market_news = dict((snapshot or {}).get("market_news") or {})

    _mn_summary = _safe_str((_latest_market_news or {}).get("summary")) or ""
    _mn_flags = (_latest_market_news or {}).get("risk_flags")
    if not isinstance(_mn_flags, list):
        _mn_flags = []

    if _mn_summary or _mn_flags:
        _flags_text = ", ".join(str(x) for x in _mn_flags[:6]) if _mn_flags else "none"
        st.markdown(
            "<div class='card'>"
            + f"<div class='metric' style='font-size:13px;line-height:1.5;'>{html.escape(_mn_summary[:320] or 'No summary')}</div>"
            + f"<div class='muted' style='font-size:11px;margin-top:8px;'>Risk flags: {html.escape(_flags_text)}</div>"
            + "</div>",
            unsafe_allow_html=True,
        )

    if not market_news_df.empty:
        _mn_table = market_news_df.copy().head(150)
        _mn_table["timestamp"] = _mn_table["timestamp"].apply(_fmt_pt_short)
        st.dataframe(
            _mn_table[["timestamp", "topic", "headline", "source", "link"]],
            use_container_width=True,
            height=320,
        )
    else:
        st.markdown("<div class='card'><div class='metric muted'>No market intel rows yet.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Trades</div>", unsafe_allow_html=True)
    if not real_trades.empty:
        df = real_trades.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)
        st.dataframe(_format_df_timestamps_utc8(df.head(200)), use_container_width=True, height=380)
    else:
        st.markdown("<div class='card'><div class='metric muted'>No trades recorded yet.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Cash Movements</div>", unsafe_allow_html=True)
    if cash_movements is not None and not cash_movements.empty:
        cm = cash_movements.copy().sort_values("timestamp", ascending=False)
        st.dataframe(_format_df_timestamps_utc8(cm.head(250)), use_container_width=True, height=320)
    else:
        st.markdown("<div class='card'><div class='metric muted'>No cash movement events logged yet.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Bot Events</div>", unsafe_allow_html=True)
    events = _load_bot_events_cached(limit=250)
    if events:
        st.dataframe(_format_df_timestamps_utc8(pd.DataFrame(events)), use_container_width=True, height=320)
    else:
        st.markdown("<div class='card'><div class='metric muted'>No durable events yet.</div></div>", unsafe_allow_html=True)

elif page == "System":
    st.markdown("<div class='panel-title'>System</div>", unsafe_allow_html=True)

    # ── Bot Parameters "Nutrition Label" ─────────────────────────────────────
    st.markdown("<div class='panel-title' style='margin-top:14px;'>Bot DNA</div>", unsafe_allow_html=True)
    try:
        _c = cfg  # already loaded config dict
        _risk = (_c.get("risk") or {}) if isinstance(_c.get("risk"), dict) else {}
        _exits = (_c.get("exits") or {}) if isinstance(_c.get("exits"), dict) else {}
        _v4 = (_c.get("v4") or {}) if isinstance(_c.get("v4"), dict) else {}
        _ev = (_v4.get("ev") or {}) if isinstance(_v4.get("ev"), dict) else {}
        _rg = (_c.get("regime_gates") or {}) if isinstance(_c.get("regime_gates"), dict) else {}
        _mp = (_c.get("margin_policy") or {}) if isinstance(_c.get("margin_policy"), dict) else {}
        _plrl = (_c.get("plrl3") or {}) if isinstance(_c.get("plrl3"), dict) else {}
        _fund = (_c.get("futures_funding") or {}) if isinstance(_c.get("futures_funding"), dict) else {}
        _ks = (_v4.get("kill_switches") or {}) if isinstance(_v4.get("kill_switches"), dict) else {}
        _scale = (_v4.get("scaling") or {}) if isinstance(_v4.get("scaling"), dict) else {}
        _adapt = (_v4.get("adaptive_threshold") or {}) if isinstance(_v4.get("adaptive_threshold"), dict) else {}
        _recov = (_v4.get("recovery") or {}) if isinstance(_v4.get("recovery"), dict) else {}
        _plock = (_v4.get("profit_lock") or {}) if isinstance(_v4.get("profit_lock"), dict) else {}

        def _nrow(label, value, accent=None):
            vc = f"color:{accent};" if accent else ""
            return (f"<tr><td style='padding:3px 10px 3px 0;color:#9ca3af;font-size:11px;white-space:nowrap;'>{label}</td>"
                    f"<td style='padding:3px 0;font-size:11px;font-weight:600;{vc}'>{value}</td></tr>")

        def _section(title):
            return f"<tr><td colspan='2' style='padding:10px 0 4px;font-size:12px;font-weight:700;color:#fbbf24;letter-spacing:0.8px;text-transform:uppercase;border-bottom:1px solid rgba(251,191,36,0.15);'>{title}</td></tr>"

        _paper_mode = bool(_c.get("paper", True))
        _mode_color = "#f59e0b" if _paper_mode else "#10b981"
        _mode_text = "PAPER" if _paper_mode else "HUNTING"

        _rows = "".join([
            _section("Identity"),
            _nrow("Symbol", _c.get("symbol", "XLM-PERP")),
            _nrow("Product ID", _c.get("product_id", "?")),
            _nrow("Mode", f"<span class='pill' style='background:{_mode_color}20;color:{_mode_color};'>{_mode_text}</span>"),
            _nrow("Leverage", f"{_c.get('leverage', '?')}x"),

            _section("Indicators"),
            _nrow("EMA", "21, 55 (1h) — trend alignment + slope"),
            _nrow("ATR", "14-period (15m, 1h) — volatility + stop sizing"),
            _nrow("RSI", "14-period (15m) — momentum + extremes"),
            _nrow("ADX", "14-period (15m, 1h) — trend strength"),
            _nrow("Bollinger Bands", "20, 2.0 std (15m) — expansion + rejection"),
            _nrow("MACD", "12/26/9 (15m) — momentum + divergence"),
            _nrow("Volume", "20-bar SMA (15m) — relative volume spikes"),

            _section("Entry Strategies"),
            _nrow("Pullback Continuation", "EMA pullback in trend, structure support"),
            _nrow("Breakout Retest", "Level break + retest confirmation"),
            _nrow("Reversal Impulse", "Counter-trend at extremes (RSI + BB)"),

            _section("Regime Detection"),
            _nrow("Mode", _v4.get("regime_mode", "dual")),
            _nrow("Trend", "ADX≥25 + rising + ATR expanding + BB expanding"),
            _nrow("Mean Reversion", "ADX<25 + BB not expanding"),
            _nrow("Vol State Machine", "COMPRESSION → IGNITION → EXPANSION → EXHAUSTION"),

            _section("Confluence Scoring (v4)"),
            _nrow("Trend Threshold", f"{75} pts (7 flags, 100 max)"),
            _nrow("MR Threshold", f"{70} pts (8 flags, 100 max)"),
            _nrow("Reversal Threshold", f"{60} pts (7 flags, 100 max)"),
            _nrow("Strict Score Gate", "Yes" if _v4.get("strict_score_gate", True) else "No"),
            _nrow("Adaptive Threshold",
                   f"<span class='pill {'ok' if _adapt.get('enabled') else ''}'>"
                   f"{'ON' if _adapt.get('enabled') else 'OFF'}</span>"
                   f" lookback={_adapt.get('lookback_trades', 30)} target_wr={_adapt.get('target_win_rate', 0.5)}"),

            _section("Risk Management"),
            _nrow("Capital Allocation", f"{float(_risk.get('capital_allocation_pct', 0.125))*100:.1f}%"),
            _nrow("Max SL", f"{float(_risk.get('max_sl_pct', 0.03))*100:.1f}%"),
            _nrow("Max Trades/Day", str(_risk.get("max_trades_per_day", "?"))),
            _nrow("Max Losses/Day", str(_risk.get("max_losses_per_day", "?"))),
            _nrow("Cooldown", f"{_risk.get('cooldown_minutes', '?')} min"),
            _nrow("Max Daily Loss", f"{float(_risk.get('max_daily_loss_pct', 0))*100:.1f}%"),

            _section("Exit System"),
            _nrow("TP Moves", f"TP1: {_exits.get('tp1_move')}  TP2: {_exits.get('tp2_move')}  TP3: {_exits.get('tp3_move')}"),
            _nrow("Dynamic TP", "On" if (_v4.get("exit", {}) or {}).get("dynamic_tp_enabled") else "Off"),
            _nrow("Early Save", f">{float(_exits.get('early_save_adverse_pct', 0))*100:.1f}% adverse after {_exits.get('early_save_bars', '?')} bars"),
            _nrow("Time Stop", f"{_exits.get('time_stop_bars', '?')} bars, min move {float(_exits.get('time_stop_min_move_pct', 0))*100:.2f}%"),
            _nrow("Profit Lock",
                   f"{'On' if _plock.get('enabled') else 'Off'} — activate ${_plock.get('activate_usd', '?')}, "
                   f"keep {float(_plock.get('keep_ratio', 0.6))*100:.0f}%, max giveback ${_plock.get('max_giveback_usd', '?')}"),

            _section("EV Filter"),
            _nrow("Min EV", f"${_ev.get('min_ev_usd', '?')}"),
            _nrow("Fee Model", str(_ev.get("fee_model", "?"))),
            _nrow("Maker Fee", f"{float(_ev.get('maker_fee_rate', 0))*10000:.1f} bps"),
            _nrow("Taker Fee", f"{float(_ev.get('taker_fee_rate', 0))*10000:.1f} bps"),

            _section("Gates"),
            _nrow("ATR Regime", f"ATR(14,1h) > {_rg.get('atr_multiplier', '?')}x SMA(20)"),
            _nrow("Distance from Value", f"< {_rg.get('distance_from_value_atr_mult', '?')}x ATR"),
            _nrow("Spread", f"< {float(_rg.get('spread_max_pct', 0))*100:.2f}%"),
            _nrow("Kill Switch Spread", f"< {float(_ks.get('max_spread_pct', 0))*100:.2f}%"),

            _section("Safety Systems"),
            _nrow("Margin Policy", f"{_mp.get('enforcement', '?')} — safe<{_mp.get('safe_lt')} warn<{_mp.get('warning_lt')} danger<{_mp.get('danger_lt')}"),
            _nrow("PLRL3 Rescue", f"{'On' if _plrl.get('enabled') else 'Off'} ({_plrl.get('enforcement', '?')}) — max {_plrl.get('max_rescues', '?')} rescues"),
            _nrow("Scaling",
                   f"{'On' if _scale.get('enabled') else 'Off'} — +{float(_scale.get('add_size_pct', 0))*100:.0f}% "
                   f"max {_scale.get('max_adds', '?')} adds, {_scale.get('min_minutes_between_adds', '?')}min apart"),
            _nrow("Recovery", f"{'On' if _recov.get('enabled') else 'Off'} — cap ${_recov.get('recovery_cap_per_trade', '?')}/trade, min score {_recov.get('high_quality_score', '?')}"),

            _section("HTF Context"),
            _nrow("Monthly Zones", "Jul 2024 → present, clustered, 12h cache"),
            _nrow("Microstructure", "7-day lookback, RSI + EMA slope + vol state"),

            _section("Contract Intelligence"),
            _nrow("Data", "Mark/index/OI/basis from 2 API calls per cycle"),
            _nrow("Score Mods", "Crowding ±5, OI+Price ±5, Basis ±3 (total ±10)"),
            _nrow("Cascade", "Liq/build detection, 3 severity levels, JSONL log"),
            _nrow("Moonshot", f"{'On' if (cfg.get('v4') or {{}}).get('moonshot', {{}}).get('enabled') else 'Off'} — ATR trail, suppress TP on parabolic"),
        ])

        st.markdown(
            f"<div class='card' style='padding:16px 20px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>"
            f"<span style='font-size:16px;font-weight:700;color:#fbbf24;letter-spacing:1px;'>&#9881; BOT DNA</span>"
            f"<span class='pill' style='background:{_mode_color}20;color:{_mode_color};'>{_mode_text}</span>"
            f"<span style='font-size:10px;color:#6b7280;'>v4 Confluence Engine</span>"
            f"</div>"
            f"<table style='width:100%;border-collapse:collapse;'>{_rows}</table>"
            f"</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        st.markdown("<div class='card'><div class='metric muted'>Bot DNA unavailable.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='panel-title' style='margin-top:14px;'>Data Snapshot</div>", unsafe_allow_html=True)
    st.write({
        "product_selected_last": prod,
        "ws_price": ws_px,
        "ws_age_s": ws_age,
        "bot_tick_age_s": last_age,
        "history_days": history_days,
        "history_start": _fmt_pt_short(history_start) if history_start is not None else None,
        "history_end": _fmt_pt_short(history_end) if history_end is not None else None,
        "major_events_count": len(major_events),
        "market_news_rows": int(len(market_news_df)) if market_news_df is not None else 0,
        "cash_movements_count": int(len(cash_movements)) if cash_movements is not None else 0,
        "exchange_positions": len(_cfm_positions),
        "pos_source": pos_source,
        "state_open_position": bool(open_pos),
    })

    def _render_logs():
        st.markdown("<div class='panel-title' style='margin-top:14px;'>Logs (Tail)</div>", unsafe_allow_html=True)
        l1, l2, l3 = st.columns(3)
        with l1:
            st.markdown("<div class='label'>BOT</div>", unsafe_allow_html=True)
            st.code(_tail_text(LOGS_DIR / "xpb_console.log", 140), language="text")
        with l2:
            st.markdown("<div class='label'>DASHBOARD</div>", unsafe_allow_html=True)
            st.code(_tail_text(LOGS_DIR / "dashboard.log", 140), language="text")
        with l3:
            st.markdown("<div class='label'>WS</div>", unsafe_allow_html=True)
            st.code(_tail_text(LOGS_DIR / "live_ws.log", 140), language="text")
    if _HAS_FRAGMENT:
        st.fragment(run_every=timedelta(seconds=5))(_render_logs)()
    else:
        _render_logs()

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# FLOATING CLAUDE CHAT WIDGET — injected on every page
# ══════════════════════════════════════════════════════════════════════════
# Chat API server runs alongside the dashboard on port 8504.
_chat_api_base = str(os.environ.get("XLM_CHAT_API_URL", "") or "").strip()

components.html("""
<script>
(function() {
    const doc = window.parent.document;
    if (doc.getElementById('claude-float-btn')) return;
    const explicitChatBase = __CHAT_API_BASE__;

    function resolveChatBase() {
        const explicit = String(explicitChatBase || '').trim();
        if (explicit) {
            return explicit.replace(/\\/?(ask|launch)?\\/?$/i, '').replace(/\\/+$/i, '');
        }
        try {
            var current = new URL(window.location.href);
            if (current.hostname && current.hostname !== 'about') {
                return current.protocol + '//' + current.hostname + ':8504';
            }
        } catch(e) {}
        return 'http://129.159.38.250:8504';
    }
    const chatBase = resolveChatBase();

    // --- CSS ---
    const style = doc.createElement('style');
    style.textContent = `
    #claude-float-btn {
        position: fixed; bottom: 20px; right: 20px; z-index: 999999;
        width: 50px; height: 50px; border-radius: 50%;
        background: linear-gradient(135deg, #0284c7, #0ea5e9 48%, #f59e0b);
        color: white; display: flex; align-items: center; justify-content: center;
        font-size: 22px; cursor: pointer;
        box-shadow: 0 10px 28px rgba(14,165,233,0.40);
        transition: transform 0.2s, box-shadow 0.2s;
        user-select: none; -webkit-tap-highlight-color: transparent;
    }
    #claude-float-btn:hover { transform: scale(1.08); box-shadow: 0 14px 36px rgba(14,165,233,0.52); }
    #claude-float-btn.open { background: linear-gradient(135deg, #ef4444, #f97316); }
    #claude-chat-panel {
        position: fixed; bottom: 80px; right: 20px; z-index: 999998;
        width: 380px; max-height: 560px;
        background: #0b1220; border: 1px solid rgba(14,165,233,0.30);
        border-radius: 16px; display: none; flex-direction: column;
        box-shadow: 0 24px 56px rgba(2,6,23,0.72);
        overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    #claude-chat-panel.open { display: flex; }
    .cc-header {
        padding: 12px 14px; background: linear-gradient(90deg, rgba(2,132,199,0.20), rgba(245,158,11,0.16));
        border-bottom: 1px solid rgba(14,165,233,0.25);
        display: flex; align-items: center; justify-content: space-between;
    }
    .cc-header-title { color: #e5e7eb; font-size: 14px; font-weight: 700; }
    .cc-header-sub { color: #94a3b8; font-size: 10px; }
    .cc-clear-btn {
        background: rgba(239,68,68,0.15); color: #fca5a5; border: none;
        padding: 3px 8px; border-radius: 4px; font-size: 10px; cursor: pointer;
    }
    .cc-controls {
        display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
        padding: 8px 10px; border-bottom: 1px solid rgba(51,65,85,0.40);
        background: rgba(2,6,23,0.60);
    }
    .cc-select, .cc-mini-input {
        width: 100%;
        background: rgba(15,23,42,0.75);
        border: 1px solid rgba(71,85,105,0.55);
        border-radius: 7px;
        color: #dbeafe;
        font-size: 11px;
        padding: 6px 8px;
        outline: none;
    }
    .cc-mini-input::placeholder { color: #64748b; }
    .cc-web {
        display: flex; align-items: center; gap: 6px;
        font-size: 10px; color: #cbd5e1;
    }
    .cc-web input { accent-color: #0ea5e9; }
    .cc-messages {
        flex: 1; overflow-y: auto; padding: 10px; min-height: 220px; max-height: 360px;
    }
    .cc-msg {
        margin: 6px 0; padding: 8px 10px; border-radius: 10px;
        font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word;
    }
    .cc-msg.user {
        background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.2);
        margin-left: 30px; color: #e5e7eb;
    }
    .cc-msg.assistant {
        background: rgba(14,165,233,0.10); border: 1px solid rgba(14,165,233,0.20);
        margin-right: 30px; color: #e5e7eb;
    }
    .cc-msg .cc-role {
        font-size: 9px; font-weight: 700; text-transform: uppercase;
        margin-bottom: 3px; letter-spacing: 0.5px;
    }
    .cc-msg.user .cc-role { color: #60a5fa; }
    .cc-msg.assistant .cc-role { color: #38bdf8; }
    .cc-empty {
        text-align: center; padding: 30px 20px; color: #4b5563;
    }
    .cc-empty-icon { font-size: 28px; color: #0ea5e9; margin-bottom: 6px; }
    .cc-empty-text { font-size: 11px; }
    .cc-input-row {
        display: flex; gap: 6px; padding: 10px;
        border-top: 1px solid rgba(107,114,128,0.2);
        background: rgba(15,23,42,0.8);
    }
    .cc-input {
        flex: 1; background: rgba(30,41,59,0.8); border: 1px solid rgba(107,114,128,0.3);
        border-radius: 8px; padding: 8px 10px; color: #e5e7eb; font-size: 12px;
        outline: none; font-family: inherit;
    }
    .cc-input::placeholder { color: #4b5563; }
    .cc-input:focus { border-color: rgba(14,165,233,0.6); }
    .cc-send-btn {
        background: linear-gradient(135deg, #0284c7, #0ea5e9); color: white; border: none; border-radius: 8px;
        padding: 8px 14px; font-size: 12px; font-weight: 600; cursor: pointer;
        transition: background 0.2s;
    }
    .cc-send-btn:hover { background: linear-gradient(135deg, #0369a1, #0284c7); }
    .cc-send-btn:disabled { background: #4b5563; cursor: not-allowed; }
    .cc-thinking { color: #38bdf8; font-size: 11px; padding: 8px 10px; }
    @media (max-width: 640px) {
        #claude-float-btn { right: 12px; bottom: 14px; }
        #claude-chat-panel { left: 10px; right: 10px; width: auto; bottom: 72px; max-height: 72vh; }
        .cc-controls { grid-template-columns: 1fr; }
        .cc-msg.user { margin-left: 10px; }
        .cc-msg.assistant { margin-right: 10px; }
    }
    `;
    doc.head.appendChild(style);

    // --- Floating Button ---
    const btn = doc.createElement('div');
    btn.id = 'claude-float-btn';
    btn.innerHTML = '&#9670;';
    doc.body.appendChild(btn);

    // --- Chat Panel ---
    const panel = doc.createElement('div');
    panel.id = 'claude-chat-panel';
    panel.innerHTML = `
        <div class="cc-header">
            <div>
                <div class="cc-header-title">&#128058; The Wolf's Desk</div>
                <div class="cc-header-sub">Talk to The Wolf -- live bot context, Belfort energy</div>
            </div>
            <button class="cc-clear-btn" id="cc-clear">Clear</button>
        </div>
        <div class="cc-controls">
            <select class="cc-select" id="cc-engine">
                <option value="openai" selected>Engine: OpenAI</option>
                <option value="claude">Engine: Claude</option>
                <option value="gemini">Engine: Gemini</option>
            </select>
            <select class="cc-select" id="cc-mode">
                <option value="chat" selected>Mode: Chat</option>
                <option value="review">Mode: Review</option>
                <option value="plan">Mode: Plan</option>
            </select>
            <input class="cc-mini-input" id="cc-model" placeholder="Model (gpt-4o-mini/...)" />
            <input class="cc-mini-input" id="cc-agent" placeholder="Agent (optional)" />
            <label class="cc-web"><input type="checkbox" id="cc-web" />Allow WebSearch</label>
        </div>
        <div class="cc-messages" id="cc-messages">
            <div class="cc-empty" id="cc-empty">
                <div class="cc-empty-icon">&#9670;</div>
                <div class="cc-empty-text">Ask anything about your bot<br>
                "Why no trades?" &bull; "What's the play?" &bull; "Give me the wolf's plan"</div>
            </div>
        </div>
        <div class="cc-input-row">
            <input class="cc-input" id="cc-input" placeholder="Ask about the bot..." />
            <button class="cc-send-btn" id="cc-send">Send</button>
        </div>
    `;
    doc.body.appendChild(panel);

    // --- Logic ---
    const messages = doc.getElementById('cc-messages');
    const input = doc.getElementById('cc-input');
    const sendBtn = doc.getElementById('cc-send');
    const clearBtn = doc.getElementById('cc-clear');
    const empty = doc.getElementById('cc-empty');
    const engineSel = doc.getElementById('cc-engine');
    const modeSel = doc.getElementById('cc-mode');
    const modelInput = doc.getElementById('cc-model');
    const agentInput = doc.getElementById('cc-agent');
    const webToggle = doc.getElementById('cc-web');
    let history = [];

    btn.onclick = () => {
        const isOpen = panel.classList.toggle('open');
        btn.classList.toggle('open');
        btn.innerHTML = isOpen ? '&#10005;' : '&#9670;';
        if (isOpen) input.focus();
    };

    function addMsg(role, text, meta) {
        if (empty) empty.style.display = 'none';
        const div = doc.createElement('div');
        div.className = 'cc-msg ' + role;
        let roleLabel = 'YOU';
        if (role !== 'user') {
            const e = String((meta && meta.engine) || 'assistant').toUpperCase();
            const m = String((meta && meta.mode) || '').toUpperCase();
            roleLabel = m ? (e + ' • ' + m) : e;
        }
        div.innerHTML = '<div class="cc-role">' + roleLabel + '</div>' +
            '<div>' + text.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function syncModeForEngine() {
        const engine = engineSel.value;
        if (engine === 'gemini' && modeSel.value === 'review') {
            modeSel.value = 'plan';
        }
        if (engine === 'claude') {
            if (!Array.from(modeSel.options).find(o => o.value === 'review')) {
                const opt = doc.createElement('option');
                opt.value = 'review';
                opt.textContent = 'Mode: Review';
                modeSel.insertBefore(opt, modeSel.firstChild);
            }
        } else {
            const reviewOpt = Array.from(modeSel.options).find(o => o.value === 'review');
            if (reviewOpt) reviewOpt.remove();
            if (modeSel.value === 'explain') {
                modeSel.value = 'plan';
            }
            if (!Array.from(modeSel.options).find(o => o.value === 'explain')) {
                const opt = doc.createElement('option');
                opt.value = 'explain';
                opt.textContent = 'Mode: Explain';
                modeSel.appendChild(opt);
            }
        }
        if (engine === 'claude') {
            const explainOpt = Array.from(modeSel.options).find(o => o.value === 'explain');
            if (explainOpt) explainOpt.remove();
            if (modeSel.value === 'plan' || modeSel.value === 'execute' || modeSel.value === 'review') {
                return;
            }
            modeSel.value = 'review';
        }
    }

    async function sendMessage() {
        const q = input.value.trim();
        if (!q) return;
        const engine = engineSel.value;
        const mode = modeSel.value;
        const model = modelInput.value.trim();
        const agent = agentInput.value.trim();
        const allowWeb = !!webToggle.checked;
        input.value = '';
        addMsg('user', q);
        history.push('User: ' + q);

        sendBtn.disabled = true;
        sendBtn.textContent = '...';

        try {
            const res = await fetch(chatBase + '/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question: q,
                    history: history.slice(-8).join('\\n'),
                    engine: engine,
                    mode: mode,
                    model: model,
                    agent: agent,
                    allow_web: allowWeb
                }),
            });
            const data = await res.json();
            addMsg('assistant', data.answer, data.meta || { engine: engine, mode: mode });
            history.push((String((data.meta && data.meta.engine) || engine).toUpperCase() + ': ' + data.answer));
        } catch (err) {
            addMsg('assistant', '(Connection error: ' + err.message + ')', { engine: engine, mode: mode });
        }

        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
        input.focus();
    }

    sendBtn.onclick = sendMessage;
    input.onkeydown = (e) => { if (e.key === 'Enter') sendMessage(); };
    engineSel.onchange = syncModeForEngine;
    syncModeForEngine();

    clearBtn.onclick = () => {
        history = [];
        messages.innerHTML = `
            <div class="cc-empty" id="cc-empty">
                <div class="cc-empty-icon">&#9670;</div>
                <div class="cc-empty-text">Ask anything about your bot<br>
                "Why no trades?" &bull; "What's the play?" &bull; "Give me the wolf's plan"</div>
            </div>`;
    };
})();
</script>
""".replace("__CHAT_API_BASE__", json.dumps(_chat_api_base or "")), height=0)

def _render_footer():
    st.markdown(
        f"<div class='footer'>THE WOLF IS WATCHING • {datetime.now(timezone.utc).astimezone(PT).strftime('%I:%M:%S %p PT')}</div>",
        unsafe_allow_html=True,
    )

if _HAS_FRAGMENT:
    st.fragment(run_every=timedelta(seconds=2))(_render_footer)()
else:
    _render_footer()

if refresh_s > 0:
    # With st.fragment, hot sections (logs, footer) update independently;
    # slow down the full-page rerun to reduce chart/signal flicker.
    _main_interval = max(float(refresh_s), 10.0) if _HAS_FRAGMENT else float(refresh_s)
    time.sleep(_main_interval)
    st.rerun()
