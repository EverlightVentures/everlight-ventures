#!/usr/bin/env python3
"""
EVERLIGHT VENTURES - Crypto Trading Platform
Enterprise-Grade Trading Dashboard v2.1
"""

import streamlit as st
import pandas as pd
import json
import subprocess
import signal
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from collections import deque
import re
from zoneinfo import ZoneInfo

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import requests
except ImportError:
    st.error("pip install requests")
    st.stop()

# Import trade logger
import sys
sys.path.insert(0, str(Path(__file__).parent))
from utils.trade_logger import TradeLogger
import streamlit.components.v1 as components

# ============ Page Config ============
st.set_page_config(
    page_title="EVERLIGHT VENTURES | Trading Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize trade logger
trade_logger = TradeLogger()

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ============ Custom CSS - Onyx POS Style ============
st.markdown("""
<style>
    /* Import clean font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }

    /* Dark sleek background with subtle glow */
    .stApp {
        background:
          radial-gradient(1200px 800px at 10% -20%, rgba(16,185,129,0.08), transparent 60%),
          radial-gradient(900px 600px at 90% 0%, rgba(59,130,246,0.08), transparent 55%),
          #0f0f0f !important;
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background: repeating-linear-gradient(
          180deg,
          rgba(255,255,255,0.02) 0px,
          rgba(255,255,255,0.02) 1px,
          transparent 2px,
          transparent 4px
        );
        opacity: 0.25;
        mix-blend-mode: soft-light;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Main header - minimal */
    .main-header {
        background: #1a1a1a;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        border: 1px solid #2a2a2a;
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 1.75rem;
        margin: 0;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    .main-header h1 span { color: #10b981; }
    .main-header p {
        color: #6b7280;
        margin: 4px 0 0 0;
        font-size: 0.875rem;
        font-weight: 400;
    }

    /* Metric cards - flat design */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #6b7280 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500 !important;
    }
    div[data-testid="stMetric"] {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

    /* Colors */
    .profit { color: #10b981 !important; }
    .loss { color: #ef4444 !important; }

    /* Info cards - clean flat */
    .info-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .info-card div { color: #9ca3af; font-size: 0.875rem; line-height: 1.6; }
    .info-card b { color: #ffffff; font-weight: 500; }

    /* Feed cards */
    .feed-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        transition: background 0.2s;
    }
    .feed-card:hover { background: #222222; }

    /* Tags - minimal pills */
    .tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 500;
        background: #262626;
        color: #10b981;
        margin-right: 6px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .badge-ready { background: rgba(16,185,129,0.15); color: #10b981; }
    .badge-warmup { background: rgba(245,158,11,0.15); color: #f59e0b; }
    .badge-confluence { background: rgba(59,130,246,0.15); color: #60a5fa; }
    .badge-wait { background: rgba(107,114,128,0.2); color: #9ca3af; }

    /* Sidebar - clean */
    [data-testid="stSidebar"] {
        background: #141414 !important;
        border-right: 1px solid #2a2a2a;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] { color: #9ca3af; }

    /* Top navigation bar */
    .top-nav {
        position: sticky;
        top: 0;
        z-index: 1000;
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        padding: 12px 16px;
        margin: 0 0 16px 0;
        background: rgba(15, 15, 15, 0.9);
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        backdrop-filter: blur(8px);
    }
    .top-nav a {
        color: #9ca3af;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px solid transparent;
        transition: all 0.2s;
    }
    .top-nav a:hover {
        color: #ffffff;
        background: #1a1a1a;
        border-color: #2a2a2a;
    }
    .top-nav a.active {
        color: #0f0f0f;
        background: #10b981;
        border-color: #10b981;
    }
    .ticker-strip {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        border-top: 1px solid rgba(255,255,255,0.06);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding: 6px 0;
        margin-top: 12px;
    }
    .ticker-strip span {
        display: inline-block;
        padding-left: 100%;
        animation: ticker 18s linear infinite;
        color: #9ca3af;
        font-size: 0.78rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }
    .market-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .market-open { background: rgba(16,185,129,0.15); color: #10b981; }
    .market-pre { background: rgba(96,165,250,0.15); color: #60a5fa; }
    .market-after { background: rgba(245,158,11,0.15); color: #f59e0b; }
    .market-closed { background: rgba(107,114,128,0.2); color: #9ca3af; }
    .bell {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: currentColor;
        box-shadow: 0 0 8px currentColor;
        animation: bellPulse 1.4s ease-in-out infinite;
    }
    @keyframes bellPulse {
        0% { transform: scale(1); opacity: 0.7; }
        50% { transform: scale(1.4); opacity: 1; }
        100% { transform: scale(1); opacity: 0.7; }
    }

    /* Buttons - accent color */
    .stButton > button {
        background: #10b981 !important;
        color: #000000 !important;
        font-weight: 600;
        border: none !important;
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
        font-size: 0.875rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #059669 !important;
        transform: translateY(-1px);
    }
    .stButton > button:disabled {
        background: #374151 !important;
        color: #6b7280 !important;
    }

    /* Live status indicator */
    .status-live {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        50% { opacity: 0.8; box-shadow: 0 0 0 4px rgba(16, 185, 129, 0); }
    }

    /* Trade status */
    .trade-win { background: rgba(16, 185, 129, 0.08); border-left: 3px solid #10b981; }
    .trade-loss { background: rgba(239, 68, 68, 0.08); border-left: 3px solid #ef4444; }

    /* Glass cards + KPI tiles */
    .glass-card {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        backdrop-filter: blur(6px);
    }
    .pulse-glow {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        color: #0f0f0f;
        background: #10b981;
        box-shadow: 0 0 12px rgba(16,185,129,0.6);
        animation: pulseGlow 1.6s ease-in-out infinite;
        font-weight: 700;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .pulse-glow-blue {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        color: #0b1020;
        background: #60a5fa;
        box-shadow: 0 0 12px rgba(96,165,250,0.6);
        animation: pulseGlowBlue 1.8s ease-in-out infinite;
        font-weight: 700;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .pulse-glow-amber {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        color: #1a1200;
        background: #f59e0b;
        box-shadow: 0 0 12px rgba(245,158,11,0.6);
        animation: pulseGlowAmber 2.0s ease-in-out infinite;
        font-weight: 700;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 6px rgba(16,185,129,0.35); transform: scale(1); }
        50% { box-shadow: 0 0 16px rgba(16,185,129,0.9); transform: scale(1.03); }
        100% { box-shadow: 0 0 6px rgba(16,185,129,0.35); transform: scale(1); }
    }
    @keyframes pulseGlowBlue {
        0% { box-shadow: 0 0 6px rgba(96,165,250,0.35); transform: scale(1); }
        50% { box-shadow: 0 0 16px rgba(96,165,250,0.9); transform: scale(1.03); }
        100% { box-shadow: 0 0 6px rgba(96,165,250,0.35); transform: scale(1); }
    }
    @keyframes pulseGlowAmber {
        0% { box-shadow: 0 0 6px rgba(245,158,11,0.35); transform: scale(1); }
        50% { box-shadow: 0 0 16px rgba(245,158,11,0.9); transform: scale(1.03); }
        100% { box-shadow: 0 0 6px rgba(245,158,11,0.35); transform: scale(1); }
    }
    .section-title {
        color: #e5e7eb;
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.4px;
    }
    .kpi {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.06));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px 16px;
    }
    .kpi-label { color: #9ca3af; font-size: 0.75rem; letter-spacing: 0.8px; text-transform: uppercase; }
    .kpi-value { color: #ffffff; font-size: 1.35rem; font-weight: 700; }

    /* Dividers */
    hr { border-color: #2a2a2a !important; margin: 1.5rem 0 !important; }

    /* Select boxes */
    .stSelectbox > div > div {
        background: #1a1a1a !important;
        border-color: #2a2a2a !important;
        border-radius: 8px !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1a1a1a;
        border-radius: 8px;
        border: 1px solid #2a2a2a;
        color: #9ca3af;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: #10b981 !important;
        color: #000000 !important;
        border-color: #10b981 !important;
    }

    /* DataFrames */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Sliders */
    .stSlider > div > div > div { background: #10b981 !important; }

    /* Radio buttons in sidebar */
    .stRadio > div { gap: 4px; }
    .stRadio label {
        background: transparent !important;
        padding: 10px 16px !important;
        border-radius: 8px;
        transition: background 0.2s;
    }
    .stRadio label:hover { background: #1a1a1a !important; }
    .stRadio label[data-checked="true"] {
        background: #1a1a1a !important;
        border-left: 2px solid #10b981;
    }

    /* Price ticker cards */
    .ticker-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .ticker-symbol { color: #6b7280; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; }
    .ticker-price { color: #ffffff; font-size: 1.25rem; font-weight: 600; margin: 4px 0; }
    .ticker-change { font-size: 0.875rem; font-weight: 500; padding: 2px 8px; border-radius: 4px; }
    .ticker-up { color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .ticker-down { color: #ef4444; background: rgba(239, 68, 68, 0.1); }
</style>
""", unsafe_allow_html=True)


# ============ Data Functions ============

@st.cache_data(ttl=15)
def get_price(pair: str) -> float:
    try:
        url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return float(response.json()["data"]["amount"])
    except:
        pass
    return 0

@st.cache_data(ttl=30)
def get_24h_stats(pair: str) -> dict:
    try:
        url = f"https://api.exchange.coinbase.com/products/{pair}/stats"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            open_price = float(data.get("open", 0))
            last_price = float(data.get("last", 0))
            change = ((last_price - open_price) / open_price * 100) if open_price else 0
            return {"price": last_price, "change": change, "high": float(data.get("high", 0)),
                   "low": float(data.get("low", 0)), "volume": float(data.get("volume", 0))}
    except:
        pass
    return {"price": 0, "change": 0, "high": 0, "low": 0, "volume": 0}

@st.cache_data(ttl=60)
def get_candles(pair: str, granularity: int = 300) -> pd.DataFrame:
    try:
        url = f"https://api.exchange.coinbase.com/products/{pair}/candles"
        response = requests.get(url, params={"granularity": granularity}, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json(), columns=["time", "low", "high", "open", "close", "volume"])
            df["time"] = pd.to_datetime(df["time"], unit="s")
            return df.sort_values("time")
    except:
        pass
    return pd.DataFrame()

# ============ Technical Indicators ============

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate EMA"""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_ema_ribbon(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate EMA ribbon (20, 50, 100, 200)"""
    periods = [20, 50, 100, 200]
    for p in periods:
        df[f'ema_{p}'] = calculate_ema(df['close'], p)
    return df

def calculate_drawdown(equity_series: pd.Series) -> pd.Series:
    """Calculate drawdown from equity curve"""
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100
    return drawdown.fillna(0)


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculate VWAP for a OHLCV dataframe."""
    if df.empty or "volume" not in df.columns:
        return pd.Series(dtype=float)
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"].fillna(0)
    vwap = (typical * vol).cumsum() / vol.cumsum().replace(0, np.nan)
    return vwap.fillna(method="ffill")


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Calculate MACD line, signal line, and histogram."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def build_account_growth(trades: list, starting_capital: float) -> pd.DataFrame:
    """Build equity curve from closed trades."""
    if not trades:
        return pd.DataFrame()

    rows = []
    for t in trades:
        pnl = t.get("pnl_usd")
        if pnl is None:
            continue
        ts = t.get("exit_time") or t.get("entry_time") or ""
        rows.append({"timestamp": ts, "pnl_usd": pnl})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if df.empty:
        return pd.DataFrame()

    df["equity"] = float(starting_capital) + df["pnl_usd"].fillna(0).cumsum()
    return df


def tv_symbol_for_pair(pair: str) -> str:
    base = (pair or "").split("-")[0].upper()
    if base == "BNB":
        return "BINANCE:BNBUSDT"
    return f"COINBASE:{base}USD"


def render_tradingview_widget(symbol: str, interval: str = "60", height: int = 520):
    widget_html = f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {{
        "symbol": "{symbol}",
        "interval": "{interval}",
        "timezone": "America/Los_Angeles",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "details": true,
        "hotlist": false,
        "calendar": false,
        "support_host": "https://www.tradingview.com"
      }}
      </script>
    </div>
    """
    components.html(widget_html, height=height, scrolling=False)


def get_recent_errors(log_path: Path, max_lines: int = 200) -> str:
    """Extract the most recent error-like line from a log file."""
    try:
        tail = tail_file(log_path, lines=max_lines)
        if not tail:
            return ""
        lines = tail.splitlines()
        for line in reversed(lines):
            if "Traceback" in line or "ERROR" in line or "Exception" in line:
                return line.strip()
        return ""
    except Exception:
        return ""


def render_debug_status(telemetry: pd.DataFrame, config: dict):
    """Lightweight debug status panel (non-intrusive)."""
    st.markdown("### Debug Status")
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    last_ts = telemetry["timestamp"].max() if not telemetry.empty and "timestamp" in telemetry.columns else None
    freshness = None
    if last_ts is not None:
        try:
            freshness = now - last_ts.tz_convert("America/Los_Angeles")
        except Exception:
            freshness = None
    bot_log = Path(__file__).parent / "logs" / f"bot_{datetime.now():%Y%m%d}.log"
    dash_log = Path(__file__).parent / "logs" / "dashboard.log"
    bot_err = get_recent_errors(bot_log)
    dash_err = get_recent_errors(dash_log)

    if "debug_start_ts" not in st.session_state:
        st.session_state["debug_start_ts"] = now.isoformat()
    start_ts = pd.to_datetime(st.session_state["debug_start_ts"], errors="coerce")
    uptime = None
    if not pd.isna(start_ts):
        try:
            uptime = now - start_ts.tz_localize(None)
        except Exception:
            uptime = None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Telemetry Freshness", f"{int(freshness.total_seconds())}s" if freshness else "—")
    with c2:
        st.metric("Dashboard Uptime", f"{int(uptime.total_seconds())}s" if uptime else "—")
    with c3:
        st.metric("Bot Log Error", "OK" if not bot_err else "CHECK")
    with c4:
        st.metric("Dashboard Log Error", "OK" if not dash_err else "CHECK")

    if bot_err or dash_err:
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        if bot_err:
            st.markdown(f"<div style='color:#ef4444; font-size:0.8rem;'><b>Bot:</b> {bot_err}</div>", unsafe_allow_html=True)
        if dash_err:
            st.markdown(f"<div style='color:#f59e0b; font-size:0.8rem;'><b>Dashboard:</b> {dash_err}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

def get_liquidation_distance(entry_price: float, current_price: float,
                              leverage: int, side: str) -> float:
    """Calculate distance to liquidation as percentage"""
    if leverage <= 0:
        return 100  # No leverage, no liquidation risk
    if side.lower() in ("buy", "long"):
        liq_price = entry_price * (1 - 1/leverage)
        if current_price <= liq_price:
            return 0
        return (current_price - liq_price) / current_price * 100
    else:
        liq_price = entry_price * (1 + 1/leverage)
        if current_price >= liq_price:
            return 0
        return (liq_price - current_price) / current_price * 100

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}

def save_config(config: dict):
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def is_bot_running() -> bool:
    """Check if trading bot is running"""
    try:
        result = subprocess.run(["pgrep", "-f", "bot.py"], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


def tail_file(path: Path, lines: int = 100) -> str:
    if not path.exists():
        return ""
    dq = deque(maxlen=lines)
    with open(path, "r") as f:
        for line in f:
            dq.append(line.rstrip("\n"))
    return "\n".join(dq)

def parse_bot_log(lines: str) -> pd.DataFrame:
    records = []
    if not lines:
        return pd.DataFrame()
    for line in lines.splitlines():
        try:
            if "Best opportunity:" in line:
                # Example: Best opportunity: BTC-USD (score: 65.0, R:R 1.33, trend: bullish)
                m = re.search(r"Best opportunity:\s+([A-Z\-]+)\s+\(score:\s+([0-9.]+),\s+R:R\s+([0-9.]+),\s+trend:\s+([a-zA-Z]+)\)", line)
                if m:
                    records.append({
                        "type": "best_opportunity",
                        "pair": m.group(1),
                        "score": float(m.group(2)),
                        "rr": float(m.group(3)),
                        "trend": m.group(4).lower()
                    })
            elif "Selected" in line and "score=" in line and "R:R=" in line:
                # Example: Selected BTC-USD: score=65.0, R:R=1.33, upside=5.99%
                m = re.search(r"Selected\s+([A-Z\-]+):\s+score=([0-9.]+),\s+R:R=([0-9.]+),\s+upside=([0-9.]+)%", line)
                if m:
                    records.append({
                        "type": "selected",
                        "pair": m.group(1),
                        "score": float(m.group(2)),
                        "rr": float(m.group(3)),
                        "upside": float(m.group(4))
                    })
            elif "Position sizing:" in line:
                # Example: Position sizing: $9.93 (micro tier, 10% of $99.35 available)
                m = re.search(r"Position sizing:\s+\$([0-9.]+)\s+\(([^,]+),\s+([0-9.]+)%\s+of\s+\$([0-9.]+)\s+available\)", line)
                if m:
                    records.append({
                        "type": "sizing",
                        "size": float(m.group(1)),
                        "tier": m.group(2),
                        "pct": float(m.group(3)),
                        "available": float(m.group(4))
                    })
        except Exception:
            continue
    return pd.DataFrame(records)

def latest_sizing_from_log(log_df: pd.DataFrame) -> dict | None:
    if log_df is None or log_df.empty:
        return None
    df = log_df[log_df["type"] == "sizing"]
    if df.empty:
        return None
    row = df.iloc[-1]
    return {
        "size": safe_num(row.get("size"), None),
        "tier": row.get("tier"),
        "pct": safe_num(row.get("pct"), None),
        "available": safe_num(row.get("available"), None),
    }


def load_telemetry(limit: int = 200) -> pd.DataFrame:
    path = Path(__file__).parent / "logs" / "telemetry.jsonl"
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with open(path, "r") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        # Display in Pacific Time
        try:
            df["timestamp"] = df["timestamp"].dt.tz_convert("America/Los_Angeles")
        except Exception:
            pass
    return df.tail(limit)

def format_metric(value, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "--"
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return "--"

def format_price(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "--"
    try:
        val = float(value)
    except Exception:
        return "--"
    if val >= 1000:
        return f"{val:,.2f}"
    if val >= 1:
        return f"{val:,.4f}"
    if val >= 0.1:
        return f"{val:,.5f}"
    return f"{val:,.6f}"

def safe_num(value, default=0.0):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return float(value)
    except Exception:
        return default

def safe_int(value, default=0):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return int(value)
    except Exception:
        return default

@st.cache_data(ttl=3600)
def _coingecko_symbol_map() -> dict:
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250, "page": 1, "sparkline": "false"}
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            mapping = {}
            for coin in data:
                symbol = (coin.get("symbol") or "").upper()
                cid = coin.get("id")
                if symbol and cid and symbol not in mapping:
                    mapping[symbol] = cid
            return mapping
    except Exception:
        pass
    return {}

@st.cache_data(ttl=3600)
def _coingecko_market_chart_range(coin_id: str, from_ts: int, to_ts: int) -> dict:
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        params = {"vs_currency": "usd", "from": from_ts, "to": to_ts}
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}

@st.cache_data(ttl=3600)
def _coingecko_supply_info(coin_id: str) -> dict:
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {"localization": "false", "tickers": "false", "market_data": "true", "community_data": "false", "developer_data": "false", "sparkline": "false"}
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json().get("market_data", {})
            return {
                "circulating_supply": data.get("circulating_supply"),
                "total_supply": data.get("total_supply"),
                "market_cap": (data.get("market_cap") or {}).get("usd")
            }
    except Exception:
        pass
    return {}

def _nearest_by_ts(series: list, target_ts: int) -> float:
    if not series:
        return None
    # series: [[ts_ms, value], ...]
    best = min(series, key=lambda x: abs(int(x[0]) - target_ts))
    return best[1] if best else None

def _compute_hilo(market_chart: dict, days: int) -> dict:
    prices = market_chart.get("prices", [])
    if not prices:
        return {}
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    window = [p for p in prices if int(p[0]) >= cutoff] or prices
    hi = max(window, key=lambda x: x[1])
    lo = min(window, key=lambda x: x[1])
    return {
        "high_price": hi[1],
        "high_ts": hi[0],
        "low_price": lo[1],
        "low_ts": lo[0]
    }

def _fmt_cap(val: float) -> str:
    if val is None:
        return "--"
    try:
        v = float(val)
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"
    except Exception:
        return "--"
def get_warmup_cache_status() -> dict:
    cache_dir = Path(__file__).parent / "logs" / "warmup_cache"
    if not cache_dir.exists():
        return {}
    status = {}
    for path in cache_dir.glob("*.json"):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            pair = path.stem.replace("_", "-")
            ts = data.get("timestamps", [])
            last_ts = ts[-1] if ts else None
            status[pair] = {
                "count": len(data.get("prices", [])),
                "last": last_ts
            }
        except Exception:
            continue
    return status

def get_traditional_market_status() -> dict:
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    is_weekday = now.weekday() < 5
    pre_open = now.replace(hour=4, minute=0, second=0, microsecond=0)
    regular_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    regular_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    after_close = now.replace(hour=20, minute=0, second=0, microsecond=0)

    if not is_weekday:
        session = "CLOSED"
    elif pre_open <= now < regular_open:
        session = "PRE‑MARKET"
    elif regular_open <= now <= regular_close:
        session = "OPEN"
    elif regular_close < now <= after_close:
        session = "AFTER‑HOURS"
    else:
        session = "CLOSED"

    return {
        "session": session,
        "time": now.strftime("%I:%M %p ET").lstrip("0")
    }
def _avg_cycle_seconds(telemetry: pd.DataFrame, pair: str) -> float:
    try:
        df = telemetry[telemetry["pair"] == pair].sort_values("timestamp").tail(30)
        if df.shape[0] < 2:
            return 0.0
        diffs = df["timestamp"].diff().dropna().dt.total_seconds()
        return float(diffs.mean()) if not diffs.empty else 0.0
    except Exception:
        return 0.0

def _estimate_trades_today(telemetry: pd.DataFrame, config: dict) -> int | None:
    try:
        tz = ZoneInfo("America/Los_Angeles")
        now = datetime.now(tz)
        today = now.date()
        risk_caps = config.get("risk_caps", {})
        mins_rr = risk_caps.get("min_risk_reward", 1.5)
        mins_conf = risk_caps.get("min_confluence", 3)
        safety_pct = float(risk_caps.get("projected_trades_safety_pct", 50))
        cap = risk_caps.get("projected_trades_cap")
        df = telemetry.copy()
        df = df[df["timestamp"].dt.tz_convert(tz).dt.date == today]
        df = df[df["signal_action"].isin(["buy", "sell", "long", "short"])]
        if "risk_reward" in df.columns:
            df = df[pd.to_numeric(df["risk_reward"], errors="coerce") >= mins_rr]
        if "confluence_count" in df.columns:
            conf = pd.to_numeric(df["confluence_count"], errors="coerce")
        else:
            conf = pd.Series([float("nan")] * len(df), index=df.index)
        if "signal_reason" in df.columns:
            parsed = df["signal_reason"].apply(lambda r: parse_confluence_from_reason(str(r) if r is not None else ""))
            parsed_conf = parsed.apply(lambda v: v[0] if v else None)
            conf = conf.fillna(parsed_conf)
        df = df[conf >= mins_conf]
        last_hours = df[df["timestamp"] >= (now - timedelta(hours=2))]
        rate_per_hour = len(last_hours) / 2 if len(last_hours) else 0
        hours_left = max(0, 24 - now.hour - (now.minute / 60.0))
        proj = int(round(rate_per_hour * hours_left * (max(0.0, min(safety_pct, 100.0)) / 100.0)))
        if cap is not None:
            try:
                proj = min(proj, int(cap))
            except Exception:
                pass
        return proj if proj > 0 else None
    except Exception:
        return None

def render_lobby_ticket(telemetry: pd.DataFrame, config: dict):
    st.markdown("### Trade Lobby")
    if telemetry.empty:
        st.info("Waiting for telemetry...")
        return

    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    selected = latest[latest.get("is_selected", False) == True]
    row = selected.iloc[0] if not selected.empty else latest.iloc[0]
    log_path = Path(__file__).parent / "logs" / f"bot_{datetime.now():%Y%m%d}.log"
    log_tail = tail_file(log_path, lines=300)
    log_df = parse_bot_log(log_tail)
    sizing_log = latest_sizing_from_log(log_df)

    pair = row.get("pair", "—")
    direction = str(row.get("signal_action", "hold")).upper()
    dp = safe_num(row.get("data_points"), 0)
    md = safe_num(row.get("min_data"), 0)
    dp_int = safe_int(dp, None)
    md_int = safe_int(md, None)
    dp_display = min(dp_int, md_int) if md_int and dp_int is not None else dp_int
    remaining = max(0, md_int - dp_int) if md_int and dp_int is not None else 0
    rr = row.get("risk_reward")
    reason = str(row.get("signal_reason", "") or "")
    conf = row.get("confluence_count")
    if conf is None or (isinstance(conf, float) and pd.isna(conf)):
        parsed_conf = parse_confluence_from_reason(reason)
        conf = parsed_conf[0] if parsed_conf else row.get("confluence_score")
    score = row.get("opportunity_score")
    win_prob = calculate_win_probability(safe_num(score, 0), safe_num(rr, 0), safe_num(conf, 0))

    avg_cycle = _avg_cycle_seconds(telemetry, pair)
    eta_sec = int(remaining * avg_cycle) if avg_cycle and remaining > 0 else 0
    eta_display = "READY" if eta_sec == 0 else f"{eta_sec//60}m {eta_sec%60}s"

    # Queue-style status line for ETA reasoning
    missing_summary = summarize_missing_signals(reason) if reason else ""
    conf_needed = max(0, 3 - int(conf)) if conf is not None and not pd.isna(conf) else None
    queue_bits = []
    if remaining > 0 and dp_display is not None and md_int is not None:
        queue_bits.append(f"{dp_display}/{md_int} data pulls")
    if conf_needed is not None and conf_needed > 0:
        queue_bits.append(f"{conf_needed} signals needed")
    elif conf_needed == 0:
        queue_bits.append("signals locked")
    if "momentum not aligned" in reason.lower():
        queue_bits.append("momentum syncing")
    if "volume too low" in reason.lower():
        queue_bits.append("volume scan")
    if missing_summary:
        queue_bits.append(missing_summary.replace("Needs: ", "loading "))
    queue_line = " • ".join(queue_bits) if queue_bits else "waiting for next signal tick"

    status = "TRADE‑READY" if remaining == 0 else "HUNTING" if dp > 0 else "WARMING UP"
    status_color = "#10b981" if status == "TRADE‑READY" else "#f59e0b" if status == "HUNTING" else "#6b7280"
    if status == "TRADE‑READY":
        status_label = f"<span class='pulse-glow'>{status}</span>"
    elif status == "HUNTING":
        status_label = f"<span class='pulse-glow-amber'>{status}</span>"
    else:
        status_label = f"<span class='pulse-glow-blue'>{status}</span>"
    proj_trades = _estimate_trades_today(telemetry, config)
    trades_done = trade_logger.get_today_stats().get("trades", 0)
    trade_track = f"{trades_done}/{proj_trades}" if proj_trades is not None else f"{trades_done}/--"
    size_preview = safe_num(row.get("position_size_usd_preview"), None)
    if size_preview is None:
        sizing_cfg = config.get("position_sizing", {})
        min_entry = config.get("min_entry", {})
        avail_preview = safe_num(row.get("available_preview"), None)
        if avail_preview is None and sizing_log:
            avail_preview = sizing_log.get("available")
        if sizing_cfg.get("mode") == "fixed_percent" and avail_preview is not None:
            size_preview = avail_preview * float(sizing_cfg.get("percent", 0))
        if size_preview is None or size_preview <= 0:
            size_preview = safe_num(min_entry.get("min_size_usd"), None)
    if (size_preview is None or size_preview <= 0) and sizing_log:
        size_preview = sizing_log.get("size")
    tp_pct = safe_num(config.get("strategy", {}).get("take_profit_percent"), 0.0)
    sl_pct = safe_num(config.get("strategy", {}).get("stop_loss_percent"), 0.0)
    expected_per_trade = None
    if size_preview and win_prob is not None:
        expected_per_trade = size_preview * ((tp_pct / 100) * win_prob - (sl_pct / 100) * (1 - win_prob))
    expected_total = None
    if expected_per_trade is not None and proj_trades:
        expected_total = expected_per_trade * proj_trades
    expected_disp = f"${expected_total:,.2f} (≈${expected_per_trade:,.2f}/trade)" if expected_total is not None else "--"

    spot_mode = row.get("perps_enabled", False) is False
    if spot_mode:
        dir_label = f"{pair} • {direction} • SPOT"
    else:
        dir_label = f"{pair} • {direction}"
    st.markdown(f"""
    <div class="info-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="color:#ffffff; font-weight:600;">{dir_label}</div>
            <div style="color:{status_color}; font-weight:700;">{status_label}</div>
        </div>
        <div style="margin-top:6px; color:#6b7280; font-size:0.8rem;">
            ETA: <b>{eta_display}</b> • Warmup {dp_display if dp_display is not None else '--'}/{md_int if md_int is not None else '--'} • Confluence {format_metric(conf,1)} • R:R {format_metric(rr,2)}
        </div>
        <div style="margin-top:4px; color:#94a3b8; font-size:0.8rem;">
            Queue: {queue_line}
        </div>
        <div style="margin-top:6px; color:#6b7280; font-size:0.8rem;">
            Projected trades today (safe): <b>{proj_trades if proj_trades is not None else '--'}</b> • Progress: <b>{trade_track}</b> • Win Odds: <b>{win_prob*100:.0f}%</b>
        </div>
        <div style="margin-top:4px; color:#6b7280; font-size:0.8rem;">
            Anticipated total profit (safe): <b>{expected_disp}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_entry_timer(telemetry: pd.DataFrame):
    """Countdown-style ETA for next entry on dashboard."""
    if telemetry.empty:
        return
    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    selected = latest[latest.get("is_selected", False) == True]
    row = selected.iloc[0] if not selected.empty else latest.iloc[0]

    pair = row.get("pair", "—")
    dp = safe_num(row.get("data_points"), 0)
    md = safe_num(row.get("min_data"), 0)
    dp_int = safe_int(dp, None)
    md_int = safe_int(md, None)
    remaining = max(0, md_int - dp_int) if md_int and dp_int is not None else 0
    avg_cycle = _avg_cycle_seconds(telemetry, pair)
    eta_sec = int(remaining * avg_cycle) if avg_cycle and remaining > 0 else 0
    eta_display = "READY" if eta_sec == 0 else f"{eta_sec//60}m {eta_sec%60}s"
    status = "TRADE‑READY" if remaining == 0 else "HUNTING" if dp > 0 else "WARMING UP"
    status_class = "pulse-glow" if status == "TRADE‑READY" else "pulse-glow-amber" if status == "HUNTING" else "pulse-glow-blue"

    st.markdown(f"""
    <div class="info-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="color:#ffffff; font-weight:600;">Entry Timer • {pair}</div>
            <div class="{status_class}">{status}</div>
        </div>
        <div style="margin-top:6px; color:#e5e7eb; font-size:1.2rem; font-weight:700;">
            ETA: {eta_display}
        </div>
        <div style="margin-top:4px; color:#6b7280; font-size:0.85rem;">
            Data pulls: {dp_int if dp_int is not None else '--'}/{md_int if md_int is not None else '--'} • Remaining: {remaining}
        </div>
    </div>
    """, unsafe_allow_html=True)

def start_bot():
    """Start the trading bot"""
    bot_path = Path(__file__).parent / "bot.py"
    log_path = Path(__file__).parent / "logs" / "bot_live.log"
    subprocess.Popen(
        ["python3", str(bot_path)],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

def stop_bot():
    """Stop the trading bot"""
    subprocess.run(["pkill", "-f", "bot.py"], capture_output=True)

def run_backtest(pair: str, days: int, leverage: int, stop_loss: float, take_profit: float,
                 ema_fast: int, ema_slow: int, rsi_low: int, rsi_high: int) -> dict:
    try:
        from backtester import Backtester, DataFetcher
        candles = DataFetcher.get_historical_prices(pair, days, "5min")
        if not candles:
            return None
        config = {"initial_balance_usd": 1000, "leverage": leverage,
                 "commission_percent": 0.1, "slippage_percent": 0.05}
        strategy = {"stop_loss_percent": stop_loss, "take_profit_percent": take_profit,
                   "ema_fast": ema_fast, "ema_slow": ema_slow,
                   "rsi_entry_low": rsi_low, "rsi_entry_high": rsi_high}
        bt = Backtester(config)
        result = bt.run(candles, strategy, pair)
        return {"result": result, "equity_curve": bt.equity_curve, "trades": result.trades}
    except Exception as e:
        st.error(f"Backtest error: {e}")
        return None


# ============ Mission Control Helpers ============

def parse_signal_components(reason: str) -> dict:
    """Extract individual signal strengths from reason string"""
    signals = {
        "ema": 0.0,
        "rsi": 0.0,
        "fib": 0.0,
        "key_level": 0.0,
        "volume": 0.0,
        "breakout": 0.0,
        "vwap": 0.0,
        "momentum": 0.0,
        "macd": 0.0,
        "liquidation": 0.0
    }
    if not reason:
        return signals

    # Parse patterns like "ema_alignment:0.7" or "key_level:0.6"
    patterns = {
        "ema": r"ema[_\w]*:([0-9.]+)",
        "rsi": r"rsi:([0-9.]+)",
        "fib": r"fib\w*:([0-9.]+)",
        "key_level": r"key_level:([0-9.]+)",
        "volume": r"volume[_\w]*:([0-9.]+)",
        "breakout": r"breakout[_\w]*:([0-9.]+)",
        "vwap": r"vwap:([0-9.]+)",
        "momentum": r"momentum:([0-9.]+)",
        "macd": r"macd:([0-9.]+)",
        "liquidation": r"liquidation[_\w]*:([0-9.]+)"
    }

    reason_lower = reason.lower()
    for sig, pattern in patterns.items():
        match = re.search(pattern, reason_lower)
        if match:
            signals[sig] = float(match.group(1))
        elif sig in reason_lower:
            signals[sig] = 0.5  # Mark as present but unknown strength

    return signals


def extract_breakout_timeframes(reason: str) -> list:
    """Extract breakout timeframe tags from reason string."""
    if not reason:
        return []
    tfs = []
    for match in re.findall(r"breakout_(?:fast|confirmed)_(\\w+)", reason.lower()):
        tfs.append(match)
    return sorted(set(tfs))


def safe_int(value, default=0):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(float(value))
    except Exception:
        return default

def summarize_missing_signals(reason: str) -> str:
    if not reason:
        return "No signal details"
    reason_lower = reason.lower()
    missing = []
    if "no signals" in reason_lower or "insufficient confluence" in reason_lower:
        if "rsi" not in reason_lower:
            missing.append("RSI")
        if "macd" not in reason_lower:
            missing.append("MACD")
        if "ema" not in reason_lower:
            missing.append("EMA")
        if "volume" not in reason_lower:
            missing.append("Volume")
        if "key_level" not in reason_lower and "level" not in reason_lower:
            missing.append("Key Level")
        if "breakout" not in reason_lower:
            missing.append("Breakout")
        if "vwap" not in reason_lower:
            missing.append("VWAP")
        if "momentum" not in reason_lower:
            missing.append("Momentum")
    if not missing:
        return "Waiting for signal confirmation"
    return "Needs: " + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else "")

def parse_confluence_from_reason(reason: str) -> tuple | None:
    if not reason:
        return None
    match = re.search(r"\\((\\d+)\\s*/\\s*(\\d+)\\)", reason)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"(\\d+)\\s+signals", reason.lower())
    if match:
        return int(match.group(1)), 3
    return None

def calculate_win_probability(opportunity_score: float, risk_reward: float, confluence: float) -> float:
    """Estimate win probability from factors"""
    if not opportunity_score or not risk_reward:
        return 0.0

    # Base probability from opportunity score (0-100 -> 0.3-0.7)
    base = 0.3 + (opportunity_score / 100) * 0.4

    # Boost for good R:R
    if risk_reward >= 2.0:
        base += 0.1
    elif risk_reward >= 1.5:
        base += 0.05

    # Boost for high confluence
    if confluence and confluence >= 2.0:
        base += 0.1
    elif confluence and confluence >= 1.5:
        base += 0.05

    return min(base, 0.85)  # Cap at 85%

def get_anticipated_entry(telemetry_df: pd.DataFrame) -> dict:
    """Analyze latest data to predict next entry"""
    if telemetry_df.empty:
        return None

    # Get latest record for selected pair
    latest = telemetry_df.sort_values("timestamp").tail(10)
    selected = latest[latest.get("is_selected", False) == True]

    if selected.empty:
        selected = latest

    last = selected.iloc[-1] if not selected.empty else latest.iloc[-1]

    reason = last.get("signal_reason", "")
    action = last.get("signal_action", "hold")

    # Determine what's blocking the trade
    waiting_for = "Unknown"
    if "Collecting data" in reason:
        match = re.search(r"\((\d+)/(\d+)\)", reason)
        if match:
            waiting_for = f"Data collection ({match.group(1)}/{match.group(2)})"
    elif "Insufficient confluence" in reason:
        match = re.search(r"\((\d+)/(\d+)\)", reason)
        if match:
            waiting_for = f"More signals ({match.group(1)}/{match.group(2)} confluence)"
    elif "momentum" in reason.lower():
        waiting_for = "Momentum alignment"
    elif "volume" in reason.lower():
        waiting_for = "Volume spike"
    elif action in ("buy", "sell"):
        waiting_for = "Execution pending"

    return {
        "pair": last.get("pair", ""),
        "direction": action.upper() if action != "hold" else "PENDING",
        "price": last.get("price", 0),
        "opportunity_score": last.get("opportunity_score", 0),
        "risk_reward": last.get("risk_reward", 0),
        "stop_loss": last.get("stop_loss"),
        "take_profit": last.get("take_profit"),
        "waiting_for": waiting_for,
        "trend": last.get("trend", "neutral")
    }

def count_skipped_opportunities(telemetry_df: pd.DataFrame) -> dict:
    """Count and categorize skipped trades"""
    if telemetry_df.empty:
        return {"total": 0, "categories": {}, "recent": []}

    holds = telemetry_df[telemetry_df["signal_action"] == "hold"]

    categories = {
        "Insufficient Confluence": 0,
        "Momentum Rejection": 0,
        "Low Volume": 0,
        "Warming Up": 0,
        "Other": 0
    }

    recent = []
    for _, row in holds.tail(100).iterrows():
        reason = row.get("signal_reason", "")
        category = "Other"

        if "Insufficient confluence" in reason:
            category = "Insufficient Confluence"
        elif "momentum" in reason.lower():
            category = "Momentum Rejection"
        elif "volume" in reason.lower():
            category = "Low Volume"
        elif "Collecting data" in reason or "warmup" in reason.lower():
            category = "Warming Up"

        categories[category] += 1

        if len(recent) < 10:
            recent.append({
                "time": row.get("timestamp"),
                "pair": row.get("pair", ""),
                "reason": reason[:80] + "..." if len(reason) > 80 else reason,
                "category": category
            })

    return {
        "total": len(holds),
        "categories": categories,
        "recent": list(reversed(recent))
    }


# ============ Components ============

def render_header():
    market = get_traditional_market_status()
    if market["session"] == "OPEN":
        cls = "market-open"
    elif market["session"] == "PRE‑MARKET":
        cls = "market-pre"
    elif market["session"] == "AFTER‑HOURS":
        cls = "market-after"
    else:
        cls = "market-closed"
    st.markdown(f"""
    <div class="main-header">
        <h1><span>EVERLIGHT</span> VENTURES</h1>
        <p>Algorithmic Trading Platform</p>
        <div style="margin-top:8px;">
            <span class="market-badge {cls}">
                <span class="bell"></span>{market["session"]} • {market["time"]}
            </span>
        </div>
        <div class="ticker-strip"><span>LIVE MARKETS • REAL‑TIME SIGNALS • RISK‑AWARE EXECUTION • EVERLIGHT VENTURES •</span></div>
    </div>
    """, unsafe_allow_html=True)

def render_price_ticker(pairs: list):
    cols = st.columns(len(pairs))
    for i, pair in enumerate(pairs):
        stats = get_24h_stats(pair)
        price = stats["price"] or get_price(pair)
        change = stats["change"]
        with cols[i]:
            symbol = pair.split("-")[0]
            change_class = "ticker-up" if change >= 0 else "ticker-down"
            arrow = "+" if change >= 0 else ""
            st.markdown(f"""
            <div class="ticker-card">
                <div class="ticker-symbol">{symbol}</div>
                <div class="ticker-price">${price:,.2f}</div>
                <div class="ticker-change {change_class}">{arrow}{change:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

def render_activity_console(telemetry: pd.DataFrame):
    st.markdown("### Backend Activity Console")
    if telemetry.empty:
        st.info("No telemetry yet.")
        return

    df = telemetry.copy().tail(300)
    df["time"] = df["timestamp"].dt.tz_convert("America/Los_Angeles").dt.strftime("%H:%M:%S")
    df["pair"] = df["pair"].fillna("")
    df["action"] = df["signal_action"].fillna("hold").str.upper()
    df["score"] = df["opportunity_score"].apply(lambda v: format_metric(v, 1))
    df["rr"] = df["risk_reward"].apply(lambda v: format_metric(v, 2))
    df["conf"] = df["confluence_count"].combine_first(df["confluence_score"]).apply(lambda v: format_metric(v, 1))
    df["data"] = df.apply(
        lambda r: f"{int(r['data_points'])}/{int(r['min_data'])}"
        if pd.notna(r.get("data_points")) and pd.notna(r.get("min_data")) else "--",
        axis=1
    )
    df["reason"] = df["signal_reason"].fillna("")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Events", len(df))
    with k2:
        st.metric("Pairs", df["pair"].nunique())
    with k3:
        st.metric("Avg Score", f"{pd.to_numeric(df['score'], errors='coerce').mean():.1f}")
    with k4:
        st.metric("Avg R:R", f"{pd.to_numeric(df['rr'], errors='coerce').mean():.2f}")

    st.dataframe(
        df[["time", "pair", "action", "score", "rr", "conf", "data", "reason"]].iloc[::-1],
        use_container_width=True,
        hide_index=True,
        height=320
    )

    if HAS_PLOTLY:
        st.markdown("### Activity Patterns")
        c1, c2 = st.columns(2)
        with c1:
            action_counts = df["action"].value_counts()
            fig = go.Figure(data=[go.Bar(x=action_counts.index, y=action_counts.values, marker_color="#10b981")])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            pair_counts = df["pair"].value_counts().head(8)
            fig = go.Figure(data=[go.Bar(x=pair_counts.index, y=pair_counts.values, marker_color="#58a6ff")])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Timing + Quality")
        d1, d2 = st.columns(2)
        with d1:
            df_time = df.copy()
            df_time["hour"] = df_time["timestamp"].dt.tz_convert("America/Los_Angeles").dt.hour
            hour_counts = df_time["hour"].value_counts().sort_index()
            fig = go.Figure(data=[go.Bar(x=hour_counts.index, y=hour_counts.values, marker_color="#f59e0b")])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220,
                              xaxis_title="Hour (PT)", yaxis_title="Events")
            st.plotly_chart(fig, use_container_width=True)
        with d2:
            score_vals = pd.to_numeric(df["score"], errors="coerce").dropna()
            fig = go.Figure(data=[go.Histogram(x=score_vals, nbinsx=12, marker_color="#10b981")])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220,
                              xaxis_title="Score", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Rejection Reasons")
        holds = df[df["action"] == "HOLD"]
        if not holds.empty:
            reason_counts = holds["reason"].fillna("").str.slice(0, 40).value_counts().head(8)
            fig = go.Figure(data=[go.Bar(x=reason_counts.index, y=reason_counts.values, marker_color="#6b7280")])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240,
                              xaxis_title="Reason", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

def render_key_levels_overview(telemetry: pd.DataFrame):
    st.markdown("### Key Levels (Y/M/W/D)")
    if telemetry.empty:
        st.info("No telemetry yet.")
        return

    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    selected = latest[latest.get("is_selected", False) == True]
    row = selected.iloc[0] if not selected.empty else latest.iloc[0]

    price = safe_num(row.get("price"), 0)
    symbol = str(row.get("pair", "—")).split("-")[0].upper()
    cg_map = _coingecko_symbol_map()
    coin_id = cg_map.get(symbol)
    market_chart = {}
    supply = {}
    if coin_id:
        start = datetime(2016, 7, 9, tzinfo=timezone.utc)
        market_chart = _coingecko_market_chart_range(coin_id, int(start.timestamp()), int(datetime.now(timezone.utc).timestamp()))
        supply = _coingecko_supply_info(coin_id)

    levels = [
        ("Yearly", 365),
        ("Monthly", 30),
        ("Weekly", 7),
        ("Daily", 1),
    ]

    cols = st.columns(4)
    for i, (label, days) in enumerate(levels):
        hilo = _compute_hilo(market_chart, days) if market_chart else {}
        low_v = hilo.get("low_price")
        high_v = hilo.get("high_price")
        low_ts = hilo.get("low_ts")
        high_ts = hilo.get("high_ts")
        low_cap = _nearest_by_ts(market_chart.get("market_caps", []), low_ts) if market_chart else None
        high_cap = _nearest_by_ts(market_chart.get("market_caps", []), high_ts) if market_chart else None
        with cols[i % 4]:
            st.markdown(
                f"<div class='info-card'>"
                f"<div><b>{label}</b> • {symbol}</div>"
                f"<div>Low: {format_metric(low_v, 2)} • High: {format_metric(high_v, 2)}</div>"
                f"<div>Low Cap: {_fmt_cap(low_cap)} • High Cap: {_fmt_cap(high_cap)}</div>"
                f"<div>Supply: {_fmt_cap(supply.get('circulating_supply'))} (current)</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            if HAS_PLOTLY and low_v is not None and high_v is not None and price:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[low_v, high_v],
                    y=[0, 0],
                    mode="lines",
                    line=dict(color="#6b7280", width=8)
                ))
                fig.add_trace(go.Scatter(
                    x=[price],
                    y=[0],
                    mode="markers",
                    marker=dict(color="#10b981", size=10)
                ))
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=120,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False)
                )
                st.plotly_chart(fig, use_container_width=True)


# ============ Pages ============

def page_dashboard():
    render_header()

    # Auto-refresh for real-time updates
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        refresh_rate = st.selectbox("Refresh", [5, 10, 15, 30], index=1, label_visibility="collapsed")
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=refresh_rate * 1000, key="dashboard_refresh")

    pairs = ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"]
    render_price_ticker(pairs)

    st.divider()

    # Bot status and controls
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    config = load_config()
    capital = config.get("account", {}).get("starting_capital_usd", 2000)

    with col1:
        st.metric("CAPITAL", f"${capital:,}")
    with col2:
        today_stats = trade_logger.get_today_stats()
        pnl = today_stats["pnl"]
        delta_color = "normal" if pnl >= 0 else "inverse"
        st.metric("TODAY P&L", f"${pnl:+,.2f}")
    with col3:
        st.metric("TRADES", today_stats["trades"])
    with col4:
        total_stats = trade_logger.get_total_stats()
        st.metric("TOTAL P&L", f"${total_stats['total_pnl']:+,.2f}")
    with col5:
        running = is_bot_running()
        status = "LIVE" if running else "OFFLINE"
        st.metric("STATUS", status)
    with col6:
        market = get_traditional_market_status()
        st.markdown(f"<div class='info-card'><div style='color:#6b7280; font-size:0.7rem;'>NYSE</div><div class='market-badge market-{'open' if market['session']=='OPEN' else 'pre' if market['session']=='PRE‑MARKET' else 'after' if market['session']=='AFTER‑HOURS' else 'closed'}'>{market['session']} • {market['time']}</div></div>", unsafe_allow_html=True)

    st.divider()

    st.markdown("### Account Growth (Snapshot)")
    trades_all = trade_logger.get_all_trades()
    growth_df = build_account_growth(trades_all, capital)
    gcol1, gcol2 = st.columns([3, 1])
    with gcol1:
        if not growth_df.empty and HAS_PLOTLY:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=growth_df["timestamp"],
                y=growth_df["equity"],
                mode="lines",
                line=dict(color="#10b981", width=2)
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(15,15,15,0.5)',
                height=180,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(showgrid=False, visible=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig, use_container_width=True)
        elif not growth_df.empty:
            st.line_chart(growth_df.set_index("timestamp")["equity"])
        else:
            st.info("Equity curve will appear after the first closed trade.")
    with gcol2:
        if not growth_df.empty:
            latest_equity = float(growth_df["equity"].iloc[-1])
            total_return = latest_equity - float(capital)
            total_return_pct = (total_return / float(capital) * 100) if capital else 0
            st.metric("Equity", f"${latest_equity:,.2f}")
            st.metric("Total P&L", f"${total_return:,.2f}", f"{total_return_pct:.2f}%")
        else:
            st.metric("Equity", f"${capital:,.2f}")
            st.metric("Total P&L", "$0.00")

    st.divider()

    cache_status = get_warmup_cache_status()
    if cache_status:
        st.markdown("### Warmup Cache")
        pairs = sorted(cache_status.keys())
        cols = st.columns(min(4, len(pairs)))
        for i, p in enumerate(pairs):
            info = cache_status[p]
            last_ts = info.get("last")
            cols[i % 4].markdown(f"""
            <div class="info-card">
                <div><b>{p}</b></div>
                <div>Cached: {info.get('count', 0)} points</div>
                <div>Last: {last_ts if last_ts else '—'}</div>
            </div>
            """, unsafe_allow_html=True)

    render_lobby_ticket(load_telemetry(limit=400), config)
    render_entry_timer(load_telemetry(limit=400))

    st.divider()

    st.markdown("### Confluence Position Ladder")
    st.markdown("""
    <div class="info-card">
        <div><b>🔹 3/3 confluence (confirmation)</b></div>
        <div>15–20% position • 2× leverage • ~2–3% account risk</div>
        <div style="margin-top:8px;"><b>🔹 4/4 confluence</b></div>
        <div>20–25% position • 2× leverage • ~3–4% account risk max</div>
        <div style="margin-top:8px;"><b>🔹 Confirmed breakout + volume expansion</b></div>
        <div>25–30% position • 2× leverage • ~4% account risk max</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Bot controls
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Start Bot", type="primary", use_container_width=True, disabled=is_bot_running()):
            start_bot()
            st.success("Bot started")
            time.sleep(1)
            st.rerun()

    with col2:
        if st.button("Stop Bot", use_container_width=True, disabled=not is_bot_running()):
            stop_bot()
            st.warning("Bot stopped")
            time.sleep(1)
            st.rerun()

    with col3:
        sandbox = config.get("exchange", {}).get("sandbox", True)
        mode = "SANDBOX" if sandbox else "LIVE"
        mode_color = "#f59e0b" if sandbox else "#10b981"
        st.markdown(f'<div style="background: {mode_color}15; color: {mode_color}; padding: 10px 16px; border-radius: 8px; font-weight: 500; font-size: 0.875rem; text-align: center;">{mode}</div>', unsafe_allow_html=True)

    st.divider()

    # Chart
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_pair = st.selectbox("Select Pair", pairs)
        df = get_candles(selected_pair)

        if not df.empty and HAS_PLOTLY:
            show_vwap = st.checkbox("Show VWAP", value=True)
            show_key_levels = st.checkbox("Show Recent High/Low", value=True)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                              row_heights=[0.75, 0.25])

            fig.add_trace(go.Candlestick(
                x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
                increasing_line_color='#10b981', decreasing_line_color='#ef4444'
            ), row=1, col=1)

            # Overlay entries/exits from trade history
            trades = [t for t in trade_logger.get_all_trades() if t.get("pair") == selected_pair]
            if trades:
                entry_times = []
                entry_prices = []
                entry_colors = []
                exit_times = []
                exit_prices = []
                exit_colors = []
                for t in trades:
                    et = t.get("entry_time")
                    ep = t.get("entry_price")
                    if et and ep:
                        entry_times.append(pd.to_datetime(et, errors="coerce"))
                        entry_prices.append(float(ep))
                        entry_colors.append("#10b981" if t.get("side") == "buy" else "#ef4444")
                    xt = t.get("exit_time")
                    xp = t.get("exit_price")
                    if xt and xp:
                        exit_times.append(pd.to_datetime(xt, errors="coerce"))
                        exit_prices.append(float(xp))
                        exit_colors.append("#3b82f6" if (t.get("pnl_usd", 0) or 0) >= 0 else "#f59e0b")

                if entry_times:
                    fig.add_trace(go.Scatter(
                        x=entry_times,
                        y=entry_prices,
                        mode="markers",
                        marker=dict(symbol="triangle-up", size=10, color=entry_colors),
                        name="Entry"
                    ), row=1, col=1)
                if exit_times:
                    fig.add_trace(go.Scatter(
                        x=exit_times,
                        y=exit_prices,
                        mode="markers",
                        marker=dict(symbol="triangle-down", size=10, color=exit_colors),
                        name="Exit"
                    ), row=1, col=1)

            colors = ['#10b981' if c >= o else '#ef4444' for c, o in zip(df["close"], df["open"])]
            fig.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, opacity=0.7), row=2, col=1)

            if show_vwap:
                vwap = calculate_vwap(df)
                if not vwap.empty:
                    fig.add_trace(go.Scatter(
                        x=df["time"], y=vwap,
                        line=dict(color="#58a6ff", width=1.5),
                        name="VWAP"
                    ), row=1, col=1)

            if show_key_levels:
                recent_high = df["high"].tail(20).max()
                recent_low = df["low"].tail(20).min()
                fig.add_hline(y=recent_high, row=1, col=1, line_dash="dot",
                              line_color="#ef4444", annotation_text="20-bar High")
                fig.add_hline(y=recent_low, row=1, col=1, line_dash="dot",
                              line_color="#10b981", annotation_text="20-bar Low")

            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(13,17,23,0.8)', height=650, showlegend=True,
                            xaxis_rangeslider_visible=False, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # RSI Chart
            st.markdown("### RSI Indicator")
            df['rsi'] = calculate_rsi(df['close'])

            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(
                x=df['time'], y=df['rsi'],
                line=dict(color='#58a6ff', width=2),
                name='RSI(14)'
            ))

            # Overbought/oversold zones
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef4444",
                              annotation_text="Overbought")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="#10b981",
                              annotation_text="Oversold")
            fig_rsi.add_hrect(y0=30, y1=70, fillcolor="rgba(16, 185, 129, 0.05)",
                              line_width=0)

            fig_rsi.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(13,17,23,0.8)',
                height=220,
                yaxis=dict(range=[0, 100]),
                showlegend=False
            )
            st.plotly_chart(fig_rsi, use_container_width=True)

            # EMA Ribbon Chart
            st.markdown("### EMA Ribbon")
            df_ema = calculate_ema_ribbon(df.copy())

            fig_ema = go.Figure()
            fig_ema.add_trace(go.Scatter(
                x=df_ema['time'], y=df_ema['close'],
                line=dict(color='#ffffff', width=2),
                name='Price'
            ))

            ema_colors = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0']
            for i, period in enumerate([20, 50, 100, 200]):
                if f'ema_{period}' in df_ema.columns:
                    fig_ema.add_trace(go.Scatter(
                        x=df_ema['time'], y=df_ema[f'ema_{period}'],
                        line=dict(color=ema_colors[i], width=1),
                        name=f'EMA {period}'
                    ))

            fig_ema.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(13,17,23,0.8)',
                height=320,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_ema, use_container_width=True)

            # MACD Chart
            st.markdown("### MACD")
            macd_df = calculate_macd(df["close"])
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(
                x=df["time"], y=macd_df["macd"],
                line=dict(color="#f59e0b", width=2), name="MACD"
            ))
            fig_macd.add_trace(go.Scatter(
                x=df["time"], y=macd_df["signal"],
                line=dict(color="#58a6ff", width=1.5), name="Signal"
            ))
            fig_macd.add_trace(go.Bar(
                x=df["time"], y=macd_df["hist"],
                marker_color="#10b981", opacity=0.5, name="Hist"
            ))
            fig_macd.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(13,17,23,0.8)',
                height=220,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_macd, use_container_width=True)

    with col2:
        st.markdown("### Open Positions")
        open_trades = trade_logger.get_open_trades()

        if open_trades:
            for t in open_trades:
                current = get_price(t["pair"])
                leverage = t.get("leverage", 1) or 1
                if t["side"] == "buy":
                    pnl_pct = (current - t["entry_price"]) / t["entry_price"] * 100 * leverage
                else:
                    pnl_pct = (t["entry_price"] - current) / t["entry_price"] * 100 * leverage

                color = "#10b981" if pnl_pct >= 0 else "#ef4444"

                # Calculate liquidation distance
                liq_distance = get_liquidation_distance(t["entry_price"], current, leverage, t["side"])
                if liq_distance > 10:
                    liq_color = "#10b981"
                    liq_status = "SAFE"
                elif liq_distance > 5:
                    liq_color = "#f59e0b"
                    liq_status = "CAUTION"
                else:
                    liq_color = "#ef4444"
                    liq_status = "DANGER"

                st.markdown(f"""
                <div class="info-card" style="border-left: 3px solid {color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="color: #ffffff; font-weight: 600;">{t['pair']}</div>
                        <div style="color: {color}; font-weight: 600;">{pnl_pct:+.2f}%</div>
                    </div>
                    <div style="color: #6b7280; font-size: 0.8rem; margin-top: 4px;">
                        {t['side'].upper()} @ ${t['entry_price']:,.2f} | {leverage}x
                    </div>
                    <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #6b7280; font-size: 0.7rem;">LIQ DISTANCE</span>
                        <span style="color: {liq_color}; font-size: 0.8rem; font-weight: 500;">{liq_distance:.1f}% {liq_status}</span>
                    </div>
                    <div style="margin-top: 4px; height: 4px; background: #2a2a2a; border-radius: 2px; overflow: hidden;">
                        <div style="width: {min(liq_distance * 5, 100)}%; height: 100%; background: {liq_color};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No open positions")

        st.markdown("### Today's Stats")
        today = trade_logger.get_today_stats()
        win_rate = (today["wins"] / today["trades"] * 100) if today["trades"] > 0 else 0

        st.markdown(f"""
        <div class="info-card">
            <div>Trades: <b>{today['trades']}</b></div>
            <div>Wins: <b style="color: #10b981;">{today['wins']}</b></div>
            <div>Losses: <b style="color: #ef4444;">{today['losses']}</b></div>
            <div>Win Rate: <b>{win_rate:.0f}%</b></div>
        </div>
        """, unsafe_allow_html=True)

    # Live Trade Feed - Full width section
    st.divider()
    st.markdown("### Live Trade Feed")

    # Get recent trades from log
    all_trades = trade_logger.get_all_trades()
    recent_trades = sorted(all_trades, key=lambda x: x.get("entry_time", ""), reverse=True)[:10]

    if recent_trades:
        for t in recent_trades:
            status = t.get("status", "OPEN")
            pnl = t.get("pnl_usd", 0) or 0
            is_open = status == "OPEN"

            if is_open:
                current = get_price(t["pair"])
                if t["side"] == "buy":
                    pnl_pct = (current - t["entry_price"]) / t["entry_price"] * 100 * t.get("leverage", 1)
                else:
                    pnl_pct = (t["entry_price"] - current) / t["entry_price"] * 100 * t.get("leverage", 1)
                status_color = "#58a6ff"
                status_text = "OPEN"
            else:
                pnl_pct = t.get("pnl_percent", 0) or 0
                status_color = "#10b981" if pnl >= 0 else "#ef4444"
                status_text = "WIN" if pnl > 0 else "LOSS"

            entry_time = t.get("entry_time", "")[:16].replace("T", " ") if t.get("entry_time") else ""

            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid {status_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #ffffff; font-weight: 600;">{t['pair']}</span>
                        <span style="color: #6b7280; margin-left: 8px;">{t['side'].upper()}</span>
                        <span style="color: #4b5563; margin-left: 8px; font-size: 0.8rem;">{entry_time}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: {status_color}; font-weight: 600;">{status_text}</span>
                        <span style="color: {'#10b981' if pnl_pct >= 0 else '#ef4444'}; margin-left: 12px;">{pnl_pct:+.2f}%</span>
                    </div>
                </div>
                <div style="color: #6b7280; font-size: 0.8rem; margin-top: 4px;">
                    Entry: ${t['entry_price']:,.2f} | Size: ${t.get('size_usd', 0):,.0f} | {t.get('leverage', 1)}x | {t.get('strategy', 'N/A')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No trades yet. Start the bot to begin trading.")

    # Backend activity console
    st.divider()
    telemetry = load_telemetry(limit=800)
    render_activity_console(telemetry)
    st.divider()
    render_key_levels_overview(telemetry)
    st.divider()
    render_debug_status(telemetry, load_config())


def page_how_it_works():
    render_header()
    st.markdown("## How This Bot Works")

    st.markdown("""
    <div class="info-card">
        <div style="font-size:0.95rem; color:#e5e7eb; line-height:1.5;">
            This system is a multi‑timeframe confluence bot. It does not enter on a single indicator.
            It waits for <b>3 confluences</b> (minimum) and then sizes up as confluence increases.
            The bot runs 24/7 and logs every decision to telemetry so the dashboard can explain
            <i>why</i> it is holding or entering.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Data Flow")
    st.markdown("""
    <div class="info-card">
        <div>• Price, volume, and indicators are sampled continuously.</div>
        <div>• Warmup cache persists across restarts (no reset of data pulls).</div>
        <div>• Best pair is selected each cycle based on opportunity score + R:R.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Confluence Engine (Minimum = 3)")
    st.markdown("""
    <div class="info-card">
        <div><b>Core Signals:</b> EMA alignment, RSI, MACD, VWAP, Fibonacci, Key Levels, Volume, Breakout.</div>
        <div><b>Breakout Logic:</b></div>
        <div>• <b>Fast breakout</b> counts when price closes beyond the previous candle high/low (0.3%) with volume ≥ 1.5× the 20‑period average.</div>
        <div>• <b>Confirmed breakout</b> counts after two closes beyond dominant levels with volume ≥ 1.5× the 20‑period average.</div>
        <div><b>Result:</b> More confluences = larger position size (capped by risk limits).</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Risk Controls + Sizing")
    cfg = load_config()
    risk_caps = cfg.get("risk_caps", {})
    pos_scale = cfg.get("position_scaling", {})
    lev_cfg = cfg.get("leverage", {})
    st.markdown(f"""
    <div class="info-card">
        <div>• Max leverage: <b>{risk_caps.get('max_leverage', '—')}x</b></div>
        <div>• Max position: <b>{risk_caps.get('max_position_percent', '—')}%</b></div>
        <div>• Min R:R: <b>{risk_caps.get('min_risk_reward', '—')}</b></div>
        <div>• Min confluence: <b>{risk_caps.get('min_confluence', '—')}</b></div>
        <div>• Position scaling: <b>{'ON' if pos_scale.get('enabled') else 'OFF'}</b> (confluence + R:R weighted)</div>
        <div>• Dynamic leverage map: <b>{lev_cfg.get('rr_to_leverage', '—')}</b></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Trade Lifecycle")
    st.markdown("""
    <div class="info-card">
        <div>1) Bot evaluates all pairs and picks the best opportunity.</div>
        <div>2) If ≥ 3 confluences pass + momentum/volume rules, it signals entry.</div>
        <div>3) Order is sent to Coinbase (perps enabled if configured).</div>
        <div>4) Trade appears in your Coinbase open positions once executed.</div>
        <div>5) Exits are managed via TP/SL, breakout extension rules, and trailing logic.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### How You’ll Know a Trade Triggered")
    st.markdown("""
    <div class="info-card">
        <div>• Bot log shows: <b>Signal → Order placed → Filled</b>.</div>
        <div>• Dashboard Live Feed shows a new OPEN trade.</div>
        <div>• Coinbase shows a new open position/order in your perps account.</div>
    </div>
    """, unsafe_allow_html=True)


def page_live():
    render_header()
    st.markdown("## Live Monitor")

    refresh_sec = st.slider("Auto-refresh (seconds)", 2, 30, 5)
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=refresh_sec * 1000, key="live_refresh")
    else:
        st.caption("Install `streamlit-autorefresh` for auto-refresh. Manual refresh works. Times shown are Pacific Time.")

    running = is_bot_running()
    st.metric("Bot Status", "RUNNING" if running else "STOPPED")

    telemetry = load_telemetry(limit=800)
    last = telemetry.iloc[-1] if not telemetry.empty else None
    config = load_config()
    risk_caps = config.get("risk_caps", {})
    log_path = Path(__file__).parent / "logs" / f"bot_{datetime.now():%Y%m%d}.log"
    log_tail = tail_file(log_path, lines=300)
    log_df = parse_bot_log(log_tail)
    sizing_log = latest_sizing_from_log(log_df)
    # Add timestamps for log-derived data using current time window as fallback
    if not log_df.empty and "timestamp" not in log_df.columns:
        log_df["timestamp"] = datetime.now(ZoneInfo("America/Los_Angeles"))

    col1, col2, col3, col4, col5 = st.columns(5)
    if last is not None:
        with col1:
            st.markdown(f"<div class='kpi'><div class='kpi-label'>Pair</div><div class='kpi-value'>{last.get('pair','')}</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='kpi'><div class='kpi-label'>Price</div><div class='kpi-value'>${last.get('price',0):,.2f}</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='kpi'><div class='kpi-label'>Score</div><div class='kpi-value'>{last.get('opportunity_score',0):.1f}</div></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='kpi'><div class='kpi-label'>R:R</div><div class='kpi-value'>{last.get('risk_reward',0):.2f}</div></div>", unsafe_allow_html=True)
        with col5:
            st.markdown(f"<div class='kpi'><div class='kpi-label'>Trend</div><div class='kpi-value'>{str(last.get('trend','')).upper()}</div></div>", unsafe_allow_html=True)

        dp = last.get("data_points")
        md = last.get("min_data")
        dp_int = safe_int(dp, None)
        md_int = safe_int(md, None)
        if dp_int is not None and md_int is not None:
            st.caption(f"Signal: {last.get('signal_action', 'hold')} • {last.get('signal_reason', '')} • Data: {dp_int}/{md_int}")
        else:
            st.caption(f"Signal: {last.get('signal_action', 'hold')} • {last.get('signal_reason', '')}")

        if dp_int is not None and md_int:
            pct = min(100, int((dp_int / md_int) * 100))
            st.progress(pct / 100.0)
            st.caption(f"Warmup progress: {pct}%")

        anticipated = get_anticipated_entry(telemetry)
        if anticipated:
            remaining = None
            if dp_int is not None and md_int is not None:
                remaining = max(0, md_int - dp_int)
            reason = last.get("signal_reason", "")
            conf = last.get("confluence_score")
            if conf is None or (isinstance(conf, float) and pd.isna(conf)):
                parsed_conf = parse_confluence_from_reason(str(reason) if reason is not None else "")
                conf = parsed_conf[0] if parsed_conf else conf
            missing = summarize_missing_signals(reason)
            st.markdown(f"""
            <div class="info-card">
                <div><b>Entry Readiness</b> – {anticipated['pair']} • {anticipated['direction']} • {anticipated['waiting_for']}</div>
                <div>Data: {dp_int if dp_int is not None else "-"} / {md_int if md_int is not None else "-"} • Remaining: {remaining if remaining is not None else "-"}</div>
                <div>Confluence: {conf if conf is not None else "-"} • R:R: {anticipated['risk_reward']:.2f}</div>
                <div>{missing}</div>
            </div>
            """, unsafe_allow_html=True)

        # Trade economics (from telemetry preview if available)
        lev = last.get("leverage_preview")
        size = last.get("position_size_usd_preview")
        max_risk = last.get("max_risk_usd_preview")
        notional = last.get("leverage_adjusted_preview")
        tier = last.get("tier_preview")
        perps_enabled = last.get("perps_enabled", False)
        if (size is None or (isinstance(size, float) and pd.isna(size))) and sizing_log:
            size = sizing_log.get("size")
        if (tier is None or (isinstance(tier, float) and pd.isna(tier))) and sizing_log:
            tier = sizing_log.get("tier")
        lev_int = safe_int(lev, None)
        if perps_enabled is False:
            lev_label = "SPOT"
            lev_int = None
            notional = size
        else:
            lev_label = f"{lev_int}x" if lev_int is not None else "—"
        if size is not None and max_risk is not None:
            st.markdown(f"""
            <div class="info-card">
                <div><b>Trade Economics (Preview)</b> – Leverage {lev_label} • Tier {tier if tier else "-"}</div>
                <div>Position Size: ${float(size):,.2f} • Notional: ${float(notional) if notional is not None else float(size):,.2f}</div>
                <div>Max Risk (after saves): ${float(max_risk):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("Trade economics preview appears after the bot logs sizing for the selected pair.")

        # Risk dashboard + pre-trade checklist
        min_rr = risk_caps.get("min_risk_reward", None)
        min_conf = risk_caps.get("min_confluence", None)
        max_lev = risk_caps.get("max_leverage", None)
        max_pos_pct = risk_caps.get("max_position_percent", None)

        st.markdown("### Risk Dashboard")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Max Leverage", f"{max_lev}x" if max_lev else "—")
        with c2:
            st.metric("Max Position %", f"{max_pos_pct}%" if max_pos_pct else "—")
        with c3:
            st.metric("Min R:R", f"{min_rr:.2f}" if min_rr else "—")
        with c4:
            st.metric("Min Confluence", f"{min_conf}" if min_conf else "—")
        with c5:
            st.metric("Paper Trading", "OFF")

        st.markdown("### Confluence Position Monitor")
        st.markdown("""
        <div class="info-card">
            <div><b>Minimum Entry:</b> 3/3 confluence + momentum + volume</div>
            <div><b>Aggressive Entry:</b> 2 signals + RR ≥ 2.5 + momentum + volume (fast breakout counts as +1)</div>
            <div><b>Fast breakout:</b> close above prior candle high/low (0.3%) with volume ≥ 1.5×</div>
            <div><b>Confirmed breakout:</b> two closes beyond dominant level with volume ≥ 1.5×</div>
            <div><b>Momentum soft‑gate:</b> if ≥ 3 confluence and RR ≥ 1.5, entry allowed even if momentum is mixed</div>
            <div><b>Scaling:</b> more confluence → larger position (capped by max position %)</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Pre-Trade Checklist")
        checks = []
        if dp is not None and md is not None:
            dp_i = safe_int(dp, 0)
            md_i = safe_int(md, 0)
            checks.append(("Data ready", dp_i >= md_i if md_i else False))
        rr = last.get("risk_reward")
        if min_rr is not None and rr is not None:
            checks.append(("R:R meets minimum", float(rr) >= float(min_rr)))
        conf_count = last.get("confluence_count")
        conf_score = last.get("confluence_score")
        if min_conf is not None:
            conf_count_i = safe_int(conf_count, None)
            if conf_count_i is not None:
                checks.append(("Confluence count", conf_count_i >= safe_int(min_conf, 0)))
            elif conf_score is not None and not pd.isna(conf_score):
                checks.append(("Confluence score", float(conf_score) >= float(min_conf)))
        if max_lev is not None and lev is not None:
            checks.append(("Leverage within cap", float(lev) <= float(max_lev)))
        if max_pos_pct is not None and size is not None:
            available = last.get("available_preview")
            if available:
                cap_amt = float(available) * (float(max_pos_pct) / 100.0)
                checks.append(("Position size within cap", float(size) <= cap_amt))
        if last.get("signal_action") in ("buy", "sell", "long", "short"):
            checks.append(("Signal present", True))
        else:
            checks.append(("Signal present", False))

        for label, ok in checks:
            color = "#10b981" if ok else "#f59e0b"
            status = "PASS" if ok else "WAIT"
            st.markdown(f"<div class='info-card'><div><b>{label}</b> – <span style='color:{color}; font-weight:600;'>{status}</span></div></div>", unsafe_allow_html=True)

        st.markdown("### Confluence Position Ladder")
        st.markdown("""
        <div class="info-card">
            <div><b>🔹 2/3 confluence (anticipation)</b></div>
            <div>5–10% position • 2× leverage • ~1–2% account risk</div>
            <div style="margin-top:8px;"><b>🔹 3/3 confluence (confirmation)</b></div>
            <div>15–20% position • 2× leverage • ~2–3% account risk</div>
            <div style="margin-top:8px;"><b>🔹 4/4 or breakout + volume expansion</b></div>
            <div>20–25% position • 2× leverage • ~3–4% account risk max</div>
        </div>
        """, unsafe_allow_html=True)

        render_lobby_ticket(telemetry, load_config())
    else:
        st.info("No telemetry yet. Start the bot and wait for data pings.")

    st.divider()

    # Opportunity Score Gauges by Pair
    st.markdown("### Live Opportunity Scores")
    if not telemetry.empty:
        latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
        gauge_cols = st.columns(min(4, len(latest)))
        for i, (_, row) in enumerate(latest.iterrows()):
            with gauge_cols[i % 4]:
                score = row.get("opportunity_score", 0) or 0
                rr = row.get("risk_reward", 0) or 0
                trend = row.get("trend", "neutral")

                if score >= 70:
                    score_color = "#10b981"
                elif score >= 50:
                    score_color = "#f59e0b"
                else:
                    score_color = "#6b7280"

                st.markdown(f"""
                <div class="ticker-card">
                    <div class="ticker-symbol">{row.get('pair', '')}</div>
                    <div style="font-size: 2rem; font-weight: 700; color: {score_color};">{score:.0f}</div>
                    <div style="color: #6b7280; font-size: 0.8rem;">R:R {rr:.2f} | {trend}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Waiting for telemetry data...")

    st.divider()

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Live Price + Score")
        if not telemetry.empty and HAS_PLOTLY:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                row_heights=[0.7, 0.3])
            fig.add_trace(go.Scatter(
                x=telemetry["timestamp"], y=telemetry["price"],
                line=dict(color="#10b981", width=2), name="Price"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=telemetry["timestamp"], y=telemetry["opportunity_score"],
                line=dict(color="#58a6ff", width=1.5), name="Score"
            ), row=2, col=1)
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(13,17,23,0.8)', height=420, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Signal Mix")
            actions = telemetry["signal_action"].fillna("hold").value_counts()
            fig = go.Figure(data=[go.Pie(
                labels=actions.index.tolist(),
                values=actions.values.tolist(),
                hole=0.5,
                marker_colors=['#10b981', '#ef4444', '#58a6ff', '#f59e0b']
            )])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                              height=260, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Signal Quality Trend
            st.markdown("### Signal Quality Trend")
            if "opportunity_score" in telemetry.columns:
                df_quality = telemetry.copy()
                df_quality = df_quality.set_index("timestamp")
                try:
                    hourly = df_quality.resample("1H").agg({
                        "opportunity_score": "mean",
                        "risk_reward": "mean"
                    }).dropna()

                    if not hourly.empty:
                        fig_qual = go.Figure()
                        fig_qual.add_trace(go.Scatter(
                            x=hourly.index,
                            y=hourly["opportunity_score"],
                            mode="lines+markers",
                            line=dict(color="#10b981", width=2),
                            name="Avg Score"
                        ))
                        fig_qual.add_trace(go.Scatter(
                            x=hourly.index,
                            y=hourly["risk_reward"] * 20,
                            mode="lines",
                            line=dict(color="#58a6ff", width=1, dash="dash"),
                            name="R:R (scaled)"
                        ))
                        fig_qual.update_layout(
                            template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(13,17,23,0.8)',
                            height=250,
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02)
                        )
                        st.plotly_chart(fig_qual, use_container_width=True)
                except Exception:
                    pass

            # Filter Rejection Breakdown
            if "signal_reason" in telemetry.columns:
                st.markdown("### Signal Rejections")
                holds = telemetry[telemetry["signal_action"] == "hold"]["signal_reason"]
                reason_counts = holds.value_counts().head(8)

                if not reason_counts.empty:
                    fig_rej = go.Figure(data=[go.Pie(
                        labels=[r[:25] + "..." if len(r) > 25 else r for r in reason_counts.index.tolist()],
                        values=reason_counts.values.tolist(),
                        hole=0.5,
                        marker_colors=['#374151', '#4b5563', '#6b7280', '#9ca3af', '#d1d5db', '#e5e7eb', '#f3f4f6', '#f9fafb']
                    )])
                    fig_rej.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        height=280,
                        showlegend=False
                    )
                    st.plotly_chart(fig_rej, use_container_width=True)

            if "rr" in log_df.columns and not log_df.empty:
                st.markdown("### Risk:Reward Over Time")
                df_rr = log_df[log_df["type"].isin(["best_opportunity", "selected"])].tail(200).reset_index(drop=True)
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=df_rr["rr"], mode="lines+markers",
                    line=dict(color="#f59e0b", width=2)
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=260)
                st.plotly_chart(fig, use_container_width=True)

            if "score" in log_df.columns and not log_df.empty:
                st.markdown("### Score Distribution")
                df_sc = log_df[log_df["type"].isin(["best_opportunity", "selected"])].tail(300)
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=df_sc["score"], nbinsx=12, marker_color="#58a6ff"))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=260)
                st.plotly_chart(fig, use_container_width=True)

            if "upside" in log_df.columns and not log_df.empty:
                st.markdown("### Upside Distribution")
                df_up = log_df[log_df["type"].isin(["selected"])].tail(300)
                if not df_up.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(x=df_up["upside"], nbinsx=12, marker_color="#10b981"))
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=260)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Telemetry chart will appear once data is available.")

    with col2:
        st.markdown("### Active Signal")
        if last is not None:
            setups = ", ".join(last.get("setups", []) or [])
            st.markdown(f"""
            <div class="info-card">
                <div><b>Action:</b> {last.get("signal_action", "hold")}</div>
                <div><b>Reason:</b> {last.get("signal_reason", "")}</div>
                <div><b>Confluence:</b> {last.get("confluence_score", "")}</div>
                <div><b>Setups:</b> {setups if setups else "-"}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No signal data yet.")

        st.markdown("### Universe")
        if last is not None and last.get("universe"):
            st.markdown(f"<div class='info-card'>{', '.join(last.get('universe'))}</div>", unsafe_allow_html=True)
        else:
            st.info("Universe not yet loaded.")

        st.markdown("### Data Pull Progress")
        if last is not None and last.get("data_points") is not None and last.get("min_data") is not None:
            st.progress(min(1.0, float(last.get("data_points")) / float(last.get("min_data"))))
        else:
            st.info("No data pull stats yet.")

        st.markdown("### Data Pulls by Pair")
        if not telemetry.empty and {"pair", "data_points", "min_data"}.issubset(telemetry.columns):
            latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
            latest["progress"] = (latest["data_points"] / latest["min_data"]).fillna(0).clip(0, 1)
            latest["progress_pct"] = (latest["progress"] * 100).round(0).astype(int)
            cols = ["pair", "data_points", "min_data", "progress_pct", "signal_action", "risk_reward"]
            view = latest[cols].rename(columns={
                "pair": "Pair",
                "data_points": "Data",
                "min_data": "Min",
                "progress_pct": "Progress %",
                "signal_action": "Signal",
                "risk_reward": "R:R"
            })
            st.dataframe(view, use_container_width=True, hide_index=True)
        else:
            st.info("Waiting on per-pair telemetry.")

        st.markdown("### Open Positions")
        open_trades = trade_logger.get_open_trades()
        if open_trades:
            for t in open_trades:
                current = get_price(t["pair"])
                if t["side"] == "buy":
                    pnl_pct = (current - t["entry_price"]) / t["entry_price"] * 100 * t["leverage"]
                else:
                    pnl_pct = (t["entry_price"] - current) / t["entry_price"] * 100 * t["leverage"]
                color = "#10b981" if pnl_pct >= 0 else "#ef4444"
                st.markdown(f"""
                <div class="info-card">
                    <div style="color: #ffffff; font-weight: 600;">{t['pair']}</div>
                    <div style="color: #8b949e; font-size: 0.9em;">{t['side'].upper()} @ ${t['entry_price']:,.2f}</div>
                    <div style="color: {color}; font-size: 1.1em; margin-top: 5px;">{pnl_pct:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No open positions")

    st.divider()

    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### Live Trade Timeline")
        trades = trade_logger.get_all_trades()
        if trades:
            df = pd.DataFrame(trades)
            df["entry_time"] = pd.to_datetime(df["entry_time"])
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["entry_time"],
                    y=df["pair"],
                    mode="markers",
                    marker=dict(color="#10b981", size=8),
                    text=df["id"]
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                                  height=280, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades logged yet.")

    with col2:
        st.markdown("### Strategy Snapshot")
        config = load_config()
        strat = config.get("strategy", {})
        info = [
            f"EMA: {strat.get('ema_periods', [20,50,100,200])}",
            f"RSI: {strat.get('rsi_oversold', 25)} / {strat.get('rsi_overbought', 75)}",
            f"Min Confluence: {strat.get('min_confluence_signals', 3)}",
            f"Vol Spike: {strat.get('volume_spike_threshold', 1.5)}x",
            f"Breakouts: {'ON' if strat.get('breakout_zones', {}).get('enabled', True) else 'OFF'}",
            f"Liquidation Zones: {'ON' if strat.get('liquidation_zones', {}).get('enabled', True) else 'OFF'}"
        ]
        st.markdown(f"<div class='info-card'>{'<br/>'.join(info)}</div>", unsafe_allow_html=True)

        st.markdown("### Pair Frequency")
        if not log_df.empty and "pair" in log_df.columns:
            freq = log_df[log_df["type"].isin(["best_opportunity", "selected"])]["pair"].value_counts()
            if HAS_PLOTLY:
                fig = go.Figure([go.Bar(x=freq.index, y=freq.values, marker_color="#58a6ff")])
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pair frequency data yet.")

        if not log_df.empty and "trend" in log_df.columns:
            st.markdown("### Trend Bias")
            trend_counts = log_df[log_df["type"].isin(["best_opportunity"])]["trend"].value_counts()
            if HAS_PLOTLY and not trend_counts.empty:
                fig = go.Figure(data=[go.Pie(
                    labels=trend_counts.index.tolist(),
                    values=trend_counts.values.tolist(),
                    hole=0.55,
                    marker_colors=['#10b981', '#ef4444', '#58a6ff']
                )])
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        if not log_df.empty and {"score", "rr"}.issubset(log_df.columns):
            st.markdown("### Score vs R:R")
            df_sr = log_df[log_df["type"].isin(["best_opportunity", "selected"])].tail(300)
            if HAS_PLOTLY and not df_sr.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_sr["score"],
                    y=df_sr["rr"],
                    mode="markers",
                    marker=dict(color="#f59e0b", size=8, opacity=0.8),
                    text=df_sr.get("pair")
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=260,
                                  xaxis_title="Score", yaxis_title="R:R")
                st.plotly_chart(fig, use_container_width=True)

        if not telemetry.empty and {"pair", "timestamp"}.issubset(telemetry.columns):
            st.markdown("### Pair Heatmap")
            with st.expander("What is a heat map?"):
                st.markdown(
                    "- A heat map shows **intensity** using color.\n"
                    "- Darker/brighter cells mean **more activity**.\n"
                    "- Use it to spot **which pairs** are most active and **when**."
                )
            df_h = telemetry.copy()
            cutoff = pd.Timestamp.now(tz="America/Los_Angeles") - timedelta(hours=3)
            df_h = df_h[df_h["timestamp"] >= cutoff]
            if not df_h.empty:
                df_h["bucket"] = df_h["timestamp"].dt.floor("10min")
                heat = pd.crosstab(df_h["pair"], df_h["bucket"])
                if HAS_PLOTLY:
                    fig = go.Figure(data=go.Heatmap(
                        z=heat.values,
                        x=heat.columns.astype(str),
                        y=heat.index.tolist(),
                        colorscale="Viridis"
                    ))
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=300,
                                      xaxis_title="Time Bucket", yaxis_title="Pair")
                    st.plotly_chart(fig, use_container_width=True)

            if not df_h.empty and {"pair", "opportunity_score"}.issubset(df_h.columns) and HAS_PLOTLY:
                st.markdown("### Score Heatmap (Avg Score by Pair & Time)")
                df_h["bucket"] = df_h["timestamp"].dt.floor("10min")
                pivot = df_h.pivot_table(index="pair", columns="bucket", values="opportunity_score", aggfunc="mean").fillna(0)
                fig = go.Figure(data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns.astype(str),
                    y=pivot.index.tolist(),
                    colorscale="Turbo",
                    colorbar=dict(title="Avg Score")
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=300,
                                  xaxis_title="Time Bucket", yaxis_title="Pair")
                st.plotly_chart(fig, use_container_width=True)

        if not log_df.empty and {"score", "rr", "upside"}.issubset(log_df.columns):
            st.markdown("### Signal Correlation")
            df_corr = log_df[log_df["type"].isin(["selected"])][["score", "rr", "upside"]].tail(400)
            if not df_corr.empty and HAS_PLOTLY:
                corr = df_corr.corr().round(2)
                fig = go.Figure(data=go.Heatmap(
                    z=corr.values,
                    x=corr.columns.tolist(),
                    y=corr.index.tolist(),
                    colorscale="RdYlGn",
                    zmin=-1, zmax=1
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=260)
                st.plotly_chart(fig, use_container_width=True)

        if not telemetry.empty and {"pair", "opportunity_score"}.issubset(telemetry.columns):
            st.markdown("### Momentum")
            pairs = telemetry["pair"].dropna().unique().tolist()[:6]
            cols = st.columns(3)
            for i, p in enumerate(pairs):
                df_p = telemetry[telemetry["pair"] == p].tail(40)
                if df_p.empty or not HAS_PLOTLY:
                    continue
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_p["timestamp"], y=df_p["opportunity_score"],
                    mode="lines", line=dict(color="#10b981", width=2)
                ))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                                  height=120, margin=dict(l=10, r=10, t=10, b=10),
                                  xaxis=dict(visible=False), yaxis=dict(visible=False))
                cols[i % 3].markdown(f"**{p}**")
                cols[i % 3].plotly_chart(fig, use_container_width=True)

        if not log_df.empty and {"pair", "score", "rr"}.issubset(log_df.columns):
            st.markdown("### Entry Quality")
            df_rank = log_df[log_df["type"].isin(["selected"])].tail(300)
            if not df_rank.empty:
                agg = df_rank.groupby("pair").agg(
                    avg_score=("score", "mean"),
                    avg_rr=("rr", "mean"),
                    avg_upside=("upside", "mean")
                ).reset_index()
                agg["quality"] = (agg["avg_score"] * 0.6 + agg["avg_rr"] * 0.4).round(2)
                agg = agg.sort_values("quality", ascending=False)
                st.dataframe(agg, use_container_width=True, hide_index=True)

        st.markdown("### Activity Console")
        if not telemetry.empty:
            df = telemetry.copy().tail(400)
            df["time"] = df["timestamp"].dt.tz_convert("America/Los_Angeles").dt.strftime("%H:%M:%S")
            df["pair"] = df["pair"].fillna("")
            df["action"] = df["signal_action"].fillna("hold").str.upper()
            df["score"] = df["opportunity_score"].apply(lambda v: format_metric(v, 1))
            df["rr"] = df["risk_reward"].apply(lambda v: format_metric(v, 2))
            df["conf"] = df["confluence_count"].combine_first(df["confluence_score"]).apply(lambda v: format_metric(v, 1))
            df["data"] = df.apply(lambda r: f"{int(r['data_points'])}/{int(r['min_data'])}" if pd.notna(r.get("data_points")) and pd.notna(r.get("min_data")) else "--", axis=1)
            df["reason"] = df["signal_reason"].fillna("")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                pairs = ["All"] + sorted(df["pair"].unique().tolist())
                pair_filter = st.selectbox("Pair", pairs, index=0)
            with col_b:
                actions = ["All"] + sorted(df["action"].unique().tolist())
                action_filter = st.selectbox("Action", actions, index=0)
            with col_c:
                min_score = st.slider("Min Score", 0, 100, 0)

            df_view = df.copy()
            if pair_filter != "All":
                df_view = df_view[df_view["pair"] == pair_filter]
            if action_filter != "All":
                df_view = df_view[df_view["action"] == action_filter]
            try:
                df_score = telemetry.copy()
                df_score["opportunity_score"] = pd.to_numeric(df_score["opportunity_score"], errors="coerce")
                df_view = df_view[pd.to_numeric(df_view["score"], errors="coerce") >= min_score]
            except Exception:
                pass

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Events", len(df_view))
            with k2:
                st.metric("Pairs", df_view["pair"].nunique())
            with k3:
                st.metric("Avg Score", f"{pd.to_numeric(df_view['score'], errors='coerce').mean():.1f}")
            with k4:
                st.metric("Avg R:R", f"{pd.to_numeric(df_view['rr'], errors='coerce').mean():.2f}")

            st.dataframe(
                df_view[["time", "pair", "action", "score", "rr", "conf", "data", "reason"]].iloc[::-1],
                use_container_width=True,
                hide_index=True,
                height=360
            )

            if HAS_PLOTLY:
                st.markdown("### Activity Patterns")
                c1, c2 = st.columns(2)
                with c1:
                    action_counts = df["action"].value_counts()
                    fig = go.Figure(data=[go.Bar(x=action_counts.index, y=action_counts.values, marker_color="#10b981")])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Timing + Quality")
                d1, d2 = st.columns(2)
                with d1:
                    df_time = df.copy()
                    df_time["hour"] = df_time["timestamp"].dt.tz_convert("America/Los_Angeles").dt.hour
                    hour_counts = df_time["hour"].value_counts().sort_index()
                    fig = go.Figure(data=[go.Bar(x=hour_counts.index, y=hour_counts.values, marker_color="#f59e0b")])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220,
                                      xaxis_title="Hour (PT)", yaxis_title="Events")
                    st.plotly_chart(fig, use_container_width=True)
                with d2:
                    score_vals = pd.to_numeric(df["score"], errors="coerce").dropna()
                    fig = go.Figure(data=[go.Histogram(x=score_vals, nbinsx=12, marker_color="#10b981")])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220,
                                      xaxis_title="Score", yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Rejection Reasons")
                holds = df[df["action"] == "HOLD"]
                if not holds.empty:
                    reason_counts = holds["reason"].fillna("").str.slice(0, 40).value_counts().head(8)
                    fig = go.Figure(data=[go.Bar(x=reason_counts.index, y=reason_counts.values, marker_color="#6b7280")])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240,
                                      xaxis_title="Reason", yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    pair_counts = df["pair"].value_counts().head(8)
                    fig = go.Figure(data=[go.Bar(x=pair_counts.index, y=pair_counts.values, marker_color="#58a6ff")])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=240)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No telemetry feed yet.")

        st.markdown("### Bot Log")
        tail = tail_file(log_path, lines=120)
        if tail:
            st.code(tail, language="text")
        else:
            st.info("No log data yet.")


def page_market_wall():
    render_header()
    st.markdown("## 🧱 Market Wall")

    telemetry = load_telemetry(limit=1500)
    if telemetry.empty:
        st.info("No telemetry yet. Start the bot to populate the wall.")
        return

    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    pairs = latest["pair"].tolist()

    cols = st.columns(3)
    for i, pair in enumerate(pairs):
        row = latest[latest["pair"] == pair].iloc[0]
        price = row.get("price", None)
        score = row.get("opportunity_score", None)
        rr = row.get("risk_reward", None)
        trend = str(row.get("trend", ""))
        dp = safe_num(row.get("data_points"), 0)
        md = safe_num(row.get("min_data"), 220)
        md_int = max(0, safe_int(md, 0))
        dp_int = max(0, safe_int(dp, 0))
        dp_display = min(dp_int, md_int) if md_int else dp_int
        action = row.get("signal_action", "hold")
        reason = row.get("signal_reason", "")
        conf = row.get("confluence_score")
        conf_count = row.get("confluence_count")
        setups_val = row.get("setups")
        if isinstance(setups_val, list):
            setups = ", ".join([str(s) for s in setups_val if s])
        elif isinstance(setups_val, str):
            setups = setups_val
        else:
            setups = ""
        tf_breakouts = extract_breakout_timeframes(reason)
        progress = 0.0
        if md_int:
            try:
                progress = min(1.0, max(0.0, float(dp_int) / float(md_int)))
            except Exception:
                progress = 0.0
        progress_pct = int(round(progress * 100))
        remaining = max(0, md_int - dp_int) if md_int else None

        readiness = "Waiting for filters"
        if isinstance(reason, str) and "Collecting data" in reason:
            readiness = f"Warming up ({dp_int}/{md_int})" if md_int > 0 else "Warming up"
        elif isinstance(reason, str) and "Insufficient confluence" in reason:
            match = re.search(r"\\((\\d+)/(\\d+)\\)", reason)
            if match:
                needed = max(0, int(match.group(2)) - int(match.group(1)))
                readiness = f"Confluence {match.group(1)}/{match.group(2)} (needs {needed})"
            else:
                readiness = "Confluence building"
        elif action in ("buy", "sell", "long", "short"):
            readiness = f"Entry signal: {str(action).upper()}"

        badge_class = "badge-wait"
        if action in ("buy", "sell", "long", "short"):
            badge_class = "badge-ready"
        elif isinstance(reason, str) and "Collecting data" in reason:
            badge_class = "badge-warmup"
        elif isinstance(reason, str) and "Insufficient confluence" in reason:
            badge_class = "badge-confluence"
        selected_tag = "<span class='pulse-glow-blue'>SELECTED</span>" if row.get("is_selected") else ""
        conf_value = conf_count if conf_count is not None and not pd.isna(conf_count) else conf
        if conf_value is None or (isinstance(conf_value, float) and pd.isna(conf_value)):
            parsed_conf = parse_confluence_from_reason(reason)
            conf_value = parsed_conf[0] if parsed_conf else conf_value
        score_disp = format_metric(score, 1)
        rr_disp = format_metric(rr, 2)
        conf_disp = format_metric(conf_value, 1)
        has_metrics = any(v != "--" for v in (score_disp, rr_disp, conf_disp))
        if has_metrics:
            signal_line = f"<span class='pulse-glow'>⚡ READY</span> Score {score_disp} • R:R {rr_disp} • Conf {conf_disp}"
        else:
            signal_line = f"<span class='pulse-glow-amber'>LOADING</span> {progress_pct}% loaded"
        breakout_label = ", ".join(tf_breakouts) if tf_breakouts else "—"

        with cols[i % 3]:
            st.markdown(f"""
            <div class="glass-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:600; color:#ffffff;">{pair}</div>
                    <div style="color:#10b981; font-size:0.8rem;">{trend.upper()}</div>
                </div>
                <div style="margin-top:6px;">
                    <span class="tag {badge_class}">{readiness}</span>
                    {selected_tag}
                </div>
                <div style="font-size:1.3rem; color:#ffffff; margin-top:6px;">${format_price(price)}</div>
                <div style="color:#9ca3af; font-size:0.85rem; margin-top:4px;">
                    {signal_line}
                </div>
                <div style="color:#6b7280; font-size:0.75rem; margin-top:6px;">Data {dp_display}/{md_int if md_int else 0} • {str(action).upper() if action else 'HOLD'}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                    <div style="color:#6b7280; font-size:0.72rem;">Progress {progress_pct}%</div>
                    <div style="color:#6b7280; font-size:0.72rem;">{dp_display}/{md_int if md_int else 0}</div>
                </div>
                <div style="height:6px; background:#1f2937; border-radius:999px; overflow:hidden; margin-top:4px;">
                    <div style="width:{progress_pct}%; height:100%; background:#10b981;"></div>
                </div>
                <div style="color:#f59e0b; font-size:0.72rem; margin-top:6px;">{readiness}{f" • {remaining} pulls left" if remaining is not None else ""}</div>
                <div style="color:#6b7280; font-size:0.72rem; margin-top:4px;">{summarize_missing_signals(reason)}</div>
                <div style="color:#6b7280; font-size:0.72rem; margin-top:6px;">{reason}</div>
                <div style="color:#3b82f6; font-size:0.72rem; margin-top:4px;">TF Breakouts: {breakout_label}</div>
                <div style="color:#10b981; font-size:0.72rem; margin-top:2px;">{setups}</div>
            </div>
            """, unsafe_allow_html=True)

            if HAS_PLOTLY:
                df_p = telemetry[telemetry["pair"] == pair].tail(40)
                if not df_p.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_p["timestamp"], y=df_p["opportunity_score"],
                        mode="lines", line=dict(color="#10b981", width=2)
                    ))
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                                      height=120, margin=dict(l=10, r=10, t=10, b=10),
                                      xaxis=dict(visible=False), yaxis=dict(visible=False))
                    st.plotly_chart(fig, use_container_width=True)


def page_journal():
    """Trade journal / history"""
    render_header()

    # Auto-refresh for live trade updates
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        if st.button("Refresh", use_container_width=True):
            st.rerun()
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=30000, key="journal_refresh")  # 30 sec refresh

    st.markdown("## Trade Journal")

    # Stats overview
    stats = trade_logger.get_total_stats()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Trades", stats["total_trades"])
    with col2:
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    with col3:
        color = "normal" if stats["total_pnl"] >= 0 else "inverse"
        st.metric("Total P&L", f"${stats['total_pnl']:+,.2f}")
    with col4:
        st.metric("Avg Win", f"${stats['avg_win']:+,.2f}")
    with col5:
        st.metric("Avg Loss", f"${stats['avg_loss']:,.2f}")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Trade History", "Daily P&L", "Analytics"])

    with tab1:
        st.markdown("### Recent Trades")

        closed_trades = trade_logger.get_closed_trades(limit=50)

        if closed_trades:
            trades_data = []
            for t in closed_trades:
                pnl = t.get("pnl_usd", 0) or 0
                icon = "+" if pnl > 0 else "-"

                trades_data.append({
                    "Status": icon,
                    "Pair": t["pair"],
                    "Side": t["side"].upper(),
                    "Entry Time": t["entry_time"][:16].replace("T", " ") if t["entry_time"] else "",
                    "Entry $": f"${t['entry_price']:,.2f}",
                    "Exit $": f"${t['exit_price']:,.2f}" if t["exit_price"] else "-",
                    "P&L": f"${pnl:+,.2f}",
                    "P&L %": f"{t.get('pnl_percent', 0):+.2f}%",
                    "Reason": t.get("exit_reason", ""),
                    "Strategy": t.get("strategy", "")
                })

            df = pd.DataFrame(trades_data)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)

            # Export button
            csv = df.to_csv(index=False)
            st.download_button("Export CSV", csv, "trade_history.csv", "text/csv")
        else:
            st.info("No closed trades yet. Start the bot to begin trading!")

        # Open trades
        st.markdown("### Open Positions")
        open_trades = trade_logger.get_open_trades()

        if open_trades:
            open_data = []
            for t in open_trades:
                current = get_price(t["pair"])
                if t["side"] == "buy":
                    unrealized = (current - t["entry_price"]) / t["entry_price"] * 100 * t["leverage"]
                else:
                    unrealized = (t["entry_price"] - current) / t["entry_price"] * 100 * t["leverage"]

                open_data.append({
                    "Pair": t["pair"],
                    "Side": t["side"].upper(),
                    "Entry": f"${t['entry_price']:,.2f}",
                    "Current": f"${current:,.2f}",
                    "Size": f"${t['size_usd']:,.0f}",
                    "Leverage": f"{t['leverage']}x",
                    "Unrealized": f"{unrealized:+.2f}%",
                    "Stop Loss": f"${t['stop_loss']:,.2f}",
                    "Take Profit": f"${t['take_profit']:,.2f}"
                })

            st.dataframe(pd.DataFrame(open_data), use_container_width=True, hide_index=True)
        else:
            st.info("No open positions")

    with tab2:
        st.markdown("### Daily P&L History")

        daily_pnl = trade_logger.get_daily_pnl()

        if daily_pnl:
            # Convert to DataFrame
            df = pd.DataFrame([
                {"Date": date, "P&L": data["pnl"], "Trades": data["trades"],
                 "Wins": data["wins"], "Losses": data["losses"]}
                for date, data in sorted(daily_pnl.items())
            ])

            # Chart
            if HAS_PLOTLY:
                colors = ['#10b981' if x >= 0 else '#ef4444' for x in df["P&L"]]

                fig = go.Figure()
                fig.add_trace(go.Bar(x=df["Date"], y=df["P&L"], marker_color=colors))
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    title="Daily P&L",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

            # Cumulative P&L
            df["Cumulative"] = df["P&L"].cumsum()

            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df["Date"], y=df["Cumulative"],
                    mode='lines+markers',
                    line=dict(color='#10b981', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(0,255,136,0.1)'
                ))
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    title="Cumulative P&L",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)

            # Table
            display_df = df.copy()
            display_df["P&L"] = display_df["P&L"].apply(lambda x: f"${x:+,.2f}")
            display_df["Cumulative"] = display_df["Cumulative"].apply(lambda x: f"${x:+,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No daily P&L data yet")

    with tab3:
        st.markdown("### Performance Analytics")

        if stats["total_trades"] > 0:
            col1, col2 = st.columns(2)

            with col1:
                # Win/Loss pie
                if HAS_PLOTLY:
                    fig = go.Figure(data=[go.Pie(
                        labels=['Wins', 'Losses'],
                        values=[stats['wins'], stats['losses']],
                        hole=0.5,
                        marker_colors=['#10b981', '#ef4444']
                    )])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                                    title="Win/Loss Distribution", height=300)
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Key metrics
                st.markdown(f"""
                <div class="info-card">
                    <h4>Key Metrics</h4>
                    <p>Best Trade: <b style="color: #10b981;">${stats['best_trade']:+,.2f}</b></p>
                    <p>Worst Trade: <b style="color: #ef4444;">${stats['worst_trade']:,.2f}</b></p>
                    <p>Profit Factor: <b>{abs(stats['avg_win']/stats['avg_loss']) if stats['avg_loss'] != 0 else 0:.2f}</b></p>
                </div>
                """, unsafe_allow_html=True)

            # Trade distribution by strategy
            all_trades = trade_logger.get_all_trades()
            if all_trades:
                strategies = {}
                for t in all_trades:
                    s = t.get("strategy", "unknown")
                    if s not in strategies:
                        strategies[s] = {"trades": 0, "pnl": 0}
                    strategies[s]["trades"] += 1
                    strategies[s]["pnl"] += t.get("pnl_usd", 0) or 0

                if strategies and HAS_PLOTLY:
                    strat_df = pd.DataFrame([
                        {"Strategy": k, "Trades": v["trades"], "P&L": v["pnl"]}
                        for k, v in strategies.items()
                    ])

                    fig = px.bar(strat_df, x="Strategy", y="P&L", title="P&L by Strategy",
                               color="P&L", color_continuous_scale=["#ef4444", "#ffd93d", "#10b981"])
                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True)

                # Win Rate by Setup
                st.markdown("### Win Rate by Setup")
                setup_stats = {}
                for t in all_trades:
                    strategy = t.get("strategy", "unknown")
                    pnl = t.get("pnl_usd") or 0

                    if strategy not in setup_stats:
                        setup_stats[strategy] = {"wins": 0, "losses": 0}

                    if pnl > 0:
                        setup_stats[strategy]["wins"] += 1
                    elif pnl < 0:
                        setup_stats[strategy]["losses"] += 1

                if setup_stats and HAS_PLOTLY:
                    df_setups = pd.DataFrame([
                        {
                            "Setup": k,
                            "Win Rate": v["wins"] / (v["wins"] + v["losses"]) * 100 if (v["wins"] + v["losses"]) > 0 else 0,
                            "Trades": v["wins"] + v["losses"]
                        }
                        for k, v in setup_stats.items()
                        if (v["wins"] + v["losses"]) > 0
                    ])

                    if not df_setups.empty:
                        fig_wr = go.Figure()
                        fig_wr.add_trace(go.Bar(
                            x=df_setups["Setup"],
                            y=df_setups["Win Rate"],
                            marker_color=['#10b981' if wr >= 50 else '#ef4444' for wr in df_setups["Win Rate"]],
                            text=[f"{wr:.0f}%" for wr in df_setups["Win Rate"]],
                            textposition="outside"
                        ))
                        fig_wr.add_hline(y=50, line_dash="dash", line_color="#6b7280",
                                         annotation_text="50% Breakeven")
                        fig_wr.update_layout(
                            template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=300,
                            yaxis_title="Win Rate %",
                            yaxis_range=[0, 100]
                        )
                        st.plotly_chart(fig_wr, use_container_width=True)

                # Drawdown Waterfall
                st.markdown("### Drawdown Analysis")
                df_trades = pd.DataFrame(all_trades)
                if 'pnl_usd' in df_trades.columns:
                    df_trades['cumulative_pnl'] = df_trades['pnl_usd'].fillna(0).cumsum()
                    df_trades['drawdown'] = calculate_drawdown(df_trades['cumulative_pnl'])

                    if HAS_PLOTLY and not df_trades.empty:
                        fig_dd = go.Figure()
                        fig_dd.add_trace(go.Scatter(
                            x=list(range(len(df_trades))),
                            y=df_trades['drawdown'],
                            fill='tozeroy',
                            fillcolor='rgba(239, 68, 68, 0.3)',
                            line=dict(color='#ef4444', width=2),
                            name='Drawdown'
                        ))

                        max_dd = df_trades['drawdown'].min()
                        max_dd_idx = df_trades['drawdown'].idxmin() if not df_trades['drawdown'].isna().all() else 0
                        if max_dd < 0:
                            fig_dd.add_annotation(
                                x=max_dd_idx, y=max_dd,
                                text=f"Max DD: {max_dd:.1f}%",
                                showarrow=True, arrowhead=2,
                                font=dict(color="#ef4444")
                            )

                        fig_dd.update_layout(
                            template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=280,
                            yaxis_title="Drawdown %",
                            xaxis_title="Trade #"
                        )
                        st.plotly_chart(fig_dd, use_container_width=True)
        else:
            st.info("Need more trades for analytics")


def page_backtest():
    render_header()
    st.markdown("## Strategy Backtester")

    col1, col2, col3 = st.columns(3)

    with col1:
        pair = st.selectbox("Trading Pair", ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"])
        days = st.slider("Days", 7, 60, 14)
        leverage = st.slider("Leverage", 1, 10, 4)

    with col2:
        stop_loss = st.slider("Stop Loss %", 0.3, 3.0, 0.5, 0.1)
        take_profit = st.slider("Take Profit %", 0.5, 5.0, 2.0, 0.1)
        st.markdown(f"**R:R Ratio:** {take_profit/stop_loss:.1f}:1")

    with col3:
        ema_fast = st.slider("EMA Fast", 5, 20, 13)
        ema_slow = st.slider("EMA Slow", 15, 50, 21)
        rsi_low = st.slider("RSI Low", 20, 40, 30)
        rsi_high = st.slider("RSI High", 50, 80, 60)

    if st.button("Run Backtest", type="primary", use_container_width=True):
        with st.spinner("Running..."):
            data = run_backtest(pair, days, leverage, stop_loss, take_profit, ema_fast, ema_slow, rsi_low, rsi_high)

        if data:
            result = data["result"]
            st.success("Complete")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total P&L", f"${result.total_pnl:,.2f}")
            with col2:
                st.metric("Win Rate", f"{result.win_rate:.1f}%")
            with col3:
                st.metric("Daily Avg", f"${result.daily_avg_pnl:.2f}")
            with col4:
                st.metric("Max DD", f"{result.max_drawdown:.1f}%")

            if result.daily_avg_pnl >= 200:
                st.success("Meets $200/day target")
            elif result.daily_avg_pnl > 0:
                st.warning(f"⚠️ ${200 - result.daily_avg_pnl:.2f}/day below target")

            if data["equity_curve"] and HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=data["equity_curve"], fill='tozeroy',
                                        line=dict(color='#10b981'), fillcolor='rgba(0,255,136,0.1)'))
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig, use_container_width=True)


def page_analytics():
    """Comprehensive analytics and data visualization"""
    render_header()

    # Auto-refresh
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=5000, key="analytics_refresh")

    st.markdown("## Analytics Dashboard")

    telemetry = load_telemetry(limit=2000)

    if telemetry.empty:
        st.info("No telemetry data yet. Start the bot to collect data.")
        return

    # ========== Data Collection Progress ==========
    st.markdown("### Data Collection Progress (220 Required)")

    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    progress_cols = st.columns(len(latest) if len(latest) <= 4 else 4)

    for i, (_, row) in enumerate(latest.iterrows()):
        with progress_cols[i % 4]:
            pair = row.get("pair", "")
            data_points = row.get("data_points") or 0
            min_data = row.get("min_data") or 220
            progress = min(data_points / min_data * 100, 100) if min_data > 0 else 0
            ready = data_points >= min_data

            color = "#10b981" if ready else "#f59e0b" if progress >= 50 else "#ef4444"
            status = "READY" if ready else f"{progress:.0f}%"
            status_label = (
                "<span class='pulse-glow'>READY</span>"
                if ready
                else f"<span class='pulse-glow-amber'>{status}</span>"
            )

            st.markdown(f"""
            <div class="info-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #ffffff; font-weight: 600;">{pair}</span>
                    <span style="color: {color}; font-weight: 600;">{status_label}</span>
                </div>
                <div style="color: #6b7280; font-size: 0.8rem;">{int(data_points)} / {int(min_data)} data points</div>
                <div style="margin-top: 8px; height: 6px; background: #2a2a2a; border-radius: 3px; overflow: hidden;">
                    <div style="width: {progress}%; height: 100%; background: {color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ========== Confluence Breakdown ==========
    st.markdown("### Confluence Signal Analysis")

    tab1, tab2, tab3, tab4 = st.tabs(["Signal Matrix", "Signal Distribution", "Score Trends", "Rejection Analysis"])

    with tab1:
        st.markdown("#### Live Signal Matrix")
        # Parse signal reasons to extract individual signals
        signal_data = []
        for _, row in latest.iterrows():
            reason = row.get("signal_reason", "") or ""
            pair = row.get("pair", "")
            action = row.get("signal_action", "hold")

            # Extract signal components from reason
            signals = {
                "pair": pair,
                "action": action,
                "ema": "ema" in reason.lower(),
                "rsi": "rsi" in reason.lower(),
                "fib": "fibonacci" in reason.lower() or "fib" in reason.lower(),
                "volume": "volume" in reason.lower(),
                "key_level": "key_level" in reason.lower() or "level" in reason.lower(),
                "breakout": "breakout" in reason.lower(),
                "momentum": "momentum" in reason.lower(),
                "vwap": "vwap" in reason.lower(),
                "macd": "macd" in reason.lower(),
                "liquidation": "liquidation" in reason.lower()
            }
            signal_data.append(signals)

        if signal_data:
            df_signals = pd.DataFrame(signal_data)
            # Create visual matrix
            cols = st.columns(len(df_signals))
            signal_names = ["ema", "rsi", "fib", "volume", "key_level", "breakout", "momentum", "vwap", "macd"]

            for i, row in df_signals.iterrows():
                with cols[i]:
                    action_color = "#10b981" if row["action"] == "buy" else "#ef4444" if row["action"] == "sell" else "#6b7280"
                    st.markdown(f"""
                    <div class="info-card">
                        <div style="color: #ffffff; font-weight: 600; margin-bottom: 8px;">{row['pair']}</div>
                        <div style="color: {action_color}; font-weight: 600; margin-bottom: 12px;">{row['action'].upper()}</div>
                    """, unsafe_allow_html=True)
                    for sig in signal_names:
                        active = row.get(sig, False)
                        icon_color = "#10b981" if active else "#3a3a3a"
                        st.markdown(f"<div style='color: {icon_color}; font-size: 0.75rem;'>{'[X]' if active else '[ ]'} {sig.upper()}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("#### Signal Type Distribution")
        if HAS_PLOTLY:
            # Count signal occurrences in all telemetry
            signal_counts = {
                "EMA Alignment": telemetry["signal_reason"].str.contains("ema", case=False, na=False).sum(),
                "RSI": telemetry["signal_reason"].str.contains("rsi", case=False, na=False).sum(),
                "Fibonacci": telemetry["signal_reason"].str.contains("fib", case=False, na=False).sum(),
                "Key Level": telemetry["signal_reason"].str.contains("key_level|level", case=False, na=False).sum(),
                "Volume": telemetry["signal_reason"].str.contains("volume", case=False, na=False).sum(),
                "Momentum": telemetry["signal_reason"].str.contains("momentum", case=False, na=False).sum(),
                "Breakout": telemetry["signal_reason"].str.contains("breakout", case=False, na=False).sum(),
                "VWAP": telemetry["signal_reason"].str.contains("vwap", case=False, na=False).sum(),
            }

            col1, col2 = st.columns(2)

            with col1:
                fig = go.Figure(data=[go.Pie(
                    labels=list(signal_counts.keys()),
                    values=list(signal_counts.values()),
                    hole=0.5,
                    marker_colors=['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']
                )])
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350, title="Signal Type Mix")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = go.Figure([go.Bar(
                    x=list(signal_counts.values()),
                    y=list(signal_counts.keys()),
                    orientation='h',
                    marker_color='#10b981'
                )])
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350, title="Signal Frequency")
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("#### Opportunity Score Trends")
        if HAS_PLOTLY:
            # Score over time by pair
            for pair in telemetry["pair"].unique():
                pair_data = telemetry[telemetry["pair"] == pair].tail(100)
                if not pair_data.empty and pair_data["opportunity_score"].notna().any():
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                                       row_heights=[0.6, 0.4])

                    # Opportunity Score
                    fig.add_trace(go.Scatter(
                        x=pair_data["timestamp"], y=pair_data["opportunity_score"],
                        line=dict(color="#10b981", width=2), name="Score", fill='tozeroy'
                    ), row=1, col=1)

                    # Confluence Score
                    if "confluence_score" in pair_data.columns:
                        fig.add_trace(go.Scatter(
                            x=pair_data["timestamp"], y=pair_data["confluence_score"],
                            line=dict(color="#3b82f6", width=2), name="Confluence"
                        ), row=2, col=1)

                    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)',
                                     height=280, title=f"{pair} - Score Trend", showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.markdown("#### Signal Rejection Analysis")
        # Analyze why signals were rejected
        holds = telemetry[telemetry["signal_action"] == "hold"]
        if not holds.empty:
            rejection_reasons = {}
            for reason in holds["signal_reason"].dropna():
                if "Insufficient confluence" in reason:
                    rejection_reasons["Insufficient Confluence"] = rejection_reasons.get("Insufficient Confluence", 0) + 1
                elif "momentum" in reason.lower():
                    rejection_reasons["Momentum Not Aligned"] = rejection_reasons.get("Momentum Not Aligned", 0) + 1
                elif "volume" in reason.lower():
                    rejection_reasons["Low Volume"] = rejection_reasons.get("Low Volume", 0) + 1
                elif "data" in reason.lower() or "warmup" in reason.lower():
                    rejection_reasons["Warming Up"] = rejection_reasons.get("Warming Up", 0) + 1
                else:
                    rejection_reasons["Other"] = rejection_reasons.get("Other", 0) + 1

            if rejection_reasons and HAS_PLOTLY:
                fig = go.Figure(data=[go.Pie(
                    labels=list(rejection_reasons.keys()),
                    values=list(rejection_reasons.values()),
                    hole=0.55,
                    marker_colors=['#ef4444', '#f59e0b', '#3b82f6', '#6b7280', '#8b5cf6']
                )])
                fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350, title="Why Signals Were Rejected")
                st.plotly_chart(fig, use_container_width=True)

            # Show recent rejection details
            st.markdown("#### Recent Hold Reasons")
            recent_holds = holds.tail(10)[["timestamp", "pair", "signal_reason"]].copy()
            recent_holds["timestamp"] = pd.to_datetime(recent_holds["timestamp"]).dt.strftime("%H:%M:%S")
            recent_holds.columns = ["Time", "Pair", "Reason"]
            st.dataframe(recent_holds, use_container_width=True, hide_index=True)

    st.divider()

    # ========== Technical Indicators ==========
    st.markdown("### Technical Indicator Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### RSI Values")
        for _, row in latest.iterrows():
            reason = row.get("signal_reason", "") or ""
            rsi_match = re.search(r'RSI[:\s]+(\d+)', reason, re.IGNORECASE)
            rsi_val = int(rsi_match.group(1)) if rsi_match else 50

            if rsi_val <= 30:
                rsi_color = "#10b981"
                rsi_label = "OVERSOLD"
            elif rsi_val >= 70:
                rsi_color = "#ef4444"
                rsi_label = "OVERBOUGHT"
            else:
                rsi_color = "#6b7280"
                rsi_label = "NEUTRAL"

            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #ffffff;">{row.get('pair', '')}</span>
                    <span style="color: {rsi_color}; font-weight: 600;">{rsi_val} {rsi_label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### Trend Direction")
        for _, row in latest.iterrows():
            trend = row.get("trend") or "neutral"
            if trend == "bullish":
                trend_color = "#10b981"
                trend_icon = "UP"
            elif trend == "bearish":
                trend_color = "#ef4444"
                trend_icon = "DOWN"
            else:
                trend_color = "#6b7280"
                trend_icon = "FLAT"

            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #ffffff;">{row.get('pair', '')}</span>
                    <span style="color: {trend_color}; font-weight: 600;">{trend_icon}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("#### Risk:Reward")
        for _, row in latest.iterrows():
            rr = row.get("risk_reward") or 0
            if rr >= 2:
                rr_color = "#10b981"
            elif rr >= 1:
                rr_color = "#f59e0b"
            else:
                rr_color = "#ef4444"

            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #ffffff;">{row.get('pair', '')}</span>
                    <span style="color: {rr_color}; font-weight: 600;">{rr:.2f}:1</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ========== Raw Data Explorer ==========
    st.markdown("### Raw Telemetry Data")
    with st.expander("Show Latest Telemetry Records"):
        display_cols = ["timestamp", "pair", "price", "opportunity_score", "risk_reward",
                       "trend", "data_points", "min_data", "signal_action", "signal_reason",
                       "confluence_score", "is_selected"]
        available_cols = [c for c in display_cols if c in telemetry.columns]
        st.dataframe(telemetry[available_cols].tail(50), use_container_width=True, hide_index=True)


def page_mission_control():
    """Mission Control - Comprehensive real-time bot monitoring"""
    render_header()

    # Auto-refresh
    if HAS_AUTOREFRESH:
        st_autorefresh(interval=5000, key="mission_control_refresh")

    st.markdown("## Mission Control")

    telemetry = load_telemetry(limit=2000)
    config = load_config()

    if telemetry.empty:
        st.warning("No telemetry data yet. Start the bot to begin monitoring.")
        return

    render_lobby_ticket(telemetry, config)
    render_entry_timer(telemetry)
    st.divider()

    # Get latest data per pair
    latest = telemetry.sort_values("timestamp").groupby("pair").tail(1)
    all_pairs = latest["pair"].unique().tolist()

    # ========== SECTION 1: STATUS BAR ==========
    st.markdown("### System Status")

    running = is_bot_running()
    mode = "LIVE" if not config.get("exchange", {}).get("sandbox", True) else "SANDBOX"
    balance = config.get("account", {}).get("starting_capital_usd", 0)
    open_trades = trade_logger.get_open_trades()
    position_status = f"{len(open_trades)} OPEN" if open_trades else "NO POSITION"

    # Check overall data readiness
    data_ready_count = sum(1 for _, r in latest.iterrows() if (r.get("data_points") or 0) >= (r.get("min_data") or 220))
    total_pairs = len(latest)

    # Get latest signal info
    selected_row = telemetry[telemetry.get("is_selected", False) == True].tail(1)
    if selected_row.empty:
        selected_row = telemetry.tail(1)
    last_signal = selected_row.iloc[0] if not selected_row.empty else {}

    signal_count = 0
    if last_signal.get("signal_reason"):
        match = re.search(r"\((\d+)\s*signals", last_signal.get("signal_reason", ""))
        if match:
            signal_count = int(match.group(1))

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        bot_color = "#10b981" if running else "#ef4444"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">BOT</div><div style="color: {bot_color}; font-size: 1.2rem; font-weight: 600;">{"LIVE" if running else "OFFLINE"}</div></div>', unsafe_allow_html=True)
    with col2:
        mode_color = "#f59e0b" if mode == "SANDBOX" else "#10b981"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">MODE</div><div style="color: {mode_color}; font-size: 1.2rem; font-weight: 600;">{mode}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">BALANCE</div><div style="color: #ffffff; font-size: 1.2rem; font-weight: 600;">${balance:,.2f}</div></div>', unsafe_allow_html=True)
    with col4:
        pos_color = "#10b981" if open_trades else "#6b7280"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">POSITION</div><div style="color: {pos_color}; font-size: 1.2rem; font-weight: 600;">{position_status}</div></div>', unsafe_allow_html=True)
    with col5:
        data_color = "#10b981" if data_ready_count == total_pairs else "#f59e0b"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">DATA</div><div style="color: {data_color}; font-size: 1.2rem; font-weight: 600;">{data_ready_count}/{total_pairs} READY</div></div>', unsafe_allow_html=True)
    with col6:
        sig_color = "#10b981" if signal_count >= 3 else "#f59e0b" if signal_count >= 2 else "#6b7280"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">SIGNALS</div><div style="color: {sig_color}; font-size: 1.2rem; font-weight: 600;">{signal_count}/3</div></div>', unsafe_allow_html=True)
    with col7:
        perps_enabled = last_signal.get("perps_enabled", False)
        intx_ok = last_signal.get("intx_available", None)
        if perps_enabled and intx_ok is False:
            p_color = "#ef4444"
            p_text = "INTX OFF"
        elif perps_enabled:
            p_color = "#10b981"
            p_text = "PERPS ON"
        else:
            p_color = "#6b7280"
            p_text = "PERPS OFF"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">PERPS</div><div style="color: {p_color}; font-size: 1.2rem; font-weight: 600;">{p_text}</div></div>', unsafe_allow_html=True)
    with col8:
        market = get_traditional_market_status()
        cls = "market-open" if market["session"] == "OPEN" else "market-pre" if market["session"] == "PRE‑MARKET" else "market-after" if market["session"] == "AFTER‑HOURS" else "market-closed"
        st.markdown(f'<div class="info-card"><div style="color: #6b7280; font-size: 0.7rem;">NYSE</div><div class="market-badge {cls}">{market["session"]} • {market["time"]}</div></div>', unsafe_allow_html=True)

    st.divider()

    # ========== ACCOUNT GROWTH ==========
    st.markdown("### Account Growth")
    trades = trade_logger.get_all_trades()
    starting_capital = config.get("account", {}).get("starting_capital_usd", 0)
    growth_df = build_account_growth(trades, starting_capital)

    if growth_df.empty:
        st.info("No closed trades yet. Equity curve will appear once trades close.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            if HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=growth_df["timestamp"],
                    y=growth_df["equity"],
                    mode="lines",
                    line=dict(color="#10b981", width=2),
                    name="Equity"
                ))
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(15,15,15,0.5)',
                    height=260,
                    margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(growth_df.set_index("timestamp")["equity"])
        with col2:
            latest_equity = float(growth_df["equity"].iloc[-1])
            total_return = (latest_equity - float(starting_capital))
            total_return_pct = (total_return / float(starting_capital) * 100) if starting_capital else 0
            drawdown = calculate_drawdown(growth_df["equity"])
            max_dd = float(drawdown.min()) if not drawdown.empty else 0
            st.metric("Equity", f"${latest_equity:,.2f}")
            st.metric("Total P&L", f"${total_return:,.2f}", f"{total_return_pct:.2f}%")
            st.metric("Max Drawdown", f"{max_dd:.2f}%")

    st.divider()

    # ========== MARKET CHARTS (TRADINGVIEW) ==========
    st.markdown("### Market Charts (TradingView)")
    interval = st.radio(
        "Timeframe",
        ["1", "5", "15", "30", "60", "240", "D", "W"],
        index=4,
        horizontal=True
    )
    tabs = st.tabs([p.replace("-USD", "") for p in all_pairs]) if all_pairs else []
    for idx, pair in enumerate(all_pairs):
        if idx >= len(tabs):
            break
        with tabs[idx]:
            symbol = tv_symbol_for_pair(pair)
            render_tradingview_widget(symbol, interval=interval, height=520)

    st.divider()

    # ========== SECTION 2: DATA COLLECTION PROGRESS ==========
    st.markdown("### Data Collection Progress")

    col1, col2 = st.columns([2, 3])

    with col1:
        status_label = ""
        for _, row in latest.iterrows():
            pair = row.get("pair", "")
            data_points = row.get("data_points") or 0
            min_data = row.get("min_data") or 220
            try:
                md_int = max(1, int(min_data)) if min_data else 0
            except Exception:
                md_int = 0
            try:
                dp_int = max(0, int(data_points))
            except Exception:
                dp_int = 0
            progress = min(dp_int / md_int * 100, 100) if md_int > 0 else 0
            ready = dp_int >= md_int if md_int else False

            color = "#10b981" if ready else "#f59e0b" if progress >= 50 else "#ef4444"
            status = "READY" if ready else f"{progress:.0f}%"
            status_label = (
                "<span class='pulse-glow'>READY</span>"
                if ready
                else f"<span class='pulse-glow-amber'>{status}</span>"
            )

            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #ffffff; font-weight: 600;">{pair}</span>
                    <span style="color: {color}; font-weight: 600;">{dp_int}/{md_int if md_int else 0} {status_label}</span>
                </div>
                <div style="height: 8px; background: #2a2a2a; border-radius: 4px; overflow: hidden;">
                    <div style="width: {progress}%; height: 100%; background: {color}; transition: width 0.3s;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Data collection over time chart
        if HAS_PLOTLY and "data_points" in telemetry.columns:
            fig = go.Figure()
            for pair in all_pairs:
                pair_data = telemetry[telemetry["pair"] == pair].tail(100)
                if not pair_data.empty:
                    fig.add_trace(go.Scatter(
                        x=pair_data["timestamp"],
                        y=pair_data["data_points"],
                        name=pair,
                        mode='lines'
                    ))
            fig.add_hline(y=220, line_dash="dash", line_color="#10b981", annotation_text="Ready (220)")
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(15,15,15,0.5)',
                height=250,
                title="Data Collection Over Time",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== SECTION 3: CONFLUENCE SIGNAL MATRIX ==========
    st.markdown("### Confluence Signal Matrix")

    view_mode = st.radio("View", ["Dot Grid", "Heatmap"], horizontal=True, label_visibility="collapsed")

    signal_types = ["ema", "rsi", "fib", "key_level", "volume", "breakout", "vwap", "momentum"]
    signal_labels = ["EMA", "RSI", "Fibonacci", "Key Level", "Volume", "Breakout", "VWAP", "Momentum"]

    # Build signal matrix
    matrix_data = []
    for _, row in latest.iterrows():
        signals = parse_signal_components(row.get("signal_reason", ""))
        matrix_data.append(signals)

    if view_mode == "Dot Grid":
        # Create HTML table
        header = "<tr><th style='padding: 8px; color: #6b7280;'>Signal</th>"
        for pair in all_pairs:
            header += f"<th style='padding: 8px; color: #ffffff;'>{pair.split('-')[0]}</th>"
        header += "<th style='padding: 8px; color: #6b7280;'>Total Active</th></tr>"

        rows_html = ""
        for i, sig in enumerate(signal_types):
            rows_html += f"<tr><td style='padding: 8px; color: #ffffff;'>{signal_labels[i]}</td>"
            active_count = 0
            for j, _ in enumerate(all_pairs):
                val = matrix_data[j].get(sig, 0) if j < len(matrix_data) else 0
                if val > 0:
                    active_count += 1
                    color = "#10b981" if val >= 0.5 else "#f59e0b"
                    rows_html += f"<td style='padding: 8px; text-align: center;'><span style='color: {color}; font-size: 1.2rem;'>●</span></td>"
                else:
                    rows_html += "<td style='padding: 8px; text-align: center;'><span style='color: #3a3a3a; font-size: 1.2rem;'>○</span></td>"
            rows_html += f"<td style='padding: 8px; text-align: center; color: #10b981;'>{active_count}/{len(all_pairs)}</td></tr>"

        # Totals row
        rows_html += "<tr style='border-top: 1px solid #3a3a3a;'><td style='padding: 8px; color: #6b7280; font-weight: 600;'>TOTAL</td>"
        for j, _ in enumerate(all_pairs):
            total = sum(1 for sig in signal_types if j < len(matrix_data) and matrix_data[j].get(sig, 0) > 0)
            color = "#10b981" if total >= 3 else "#f59e0b" if total >= 2 else "#6b7280"
            rows_html += f"<td style='padding: 8px; text-align: center; color: {color}; font-weight: 600;'>{total}/{len(signal_types)}</td>"
        rows_html += "<td></td></tr>"

        st.markdown(f"""
        <div style="overflow-x: auto;">
            <table style="width: 100%; background: #1a1a1a; border-radius: 8px; border-collapse: collapse;">
                {header}
                {rows_html}
            </table>
        </div>
        """, unsafe_allow_html=True)

    else:  # Heatmap
        if HAS_PLOTLY:
            z_data = []
            for sig in signal_types:
                row_data = []
                for j, _ in enumerate(all_pairs):
                    val = matrix_data[j].get(sig, 0) if j < len(matrix_data) else 0
                    row_data.append(val)
                z_data.append(row_data)

            fig = go.Figure(data=go.Heatmap(
                z=z_data,
                x=[p.split('-')[0] for p in all_pairs],
                y=signal_labels,
                colorscale=[[0, '#1a1a1a'], [0.5, '#f59e0b'], [1, '#10b981']],
                showscale=True,
                colorbar=dict(title="Strength")
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                height=350,
                title="Signal Strength by Pair"
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ========== SECTION 4: DECISION PIPELINE ==========
    st.markdown("### Decision Pipeline")

    # Analyze current state
    last_action = last_signal.get("signal_action", "hold")
    last_reason = last_signal.get("signal_reason", "")
    data_ok = data_ready_count == total_pairs
    confluence_ok = signal_count >= 3
    momentum_ok = "momentum" not in last_reason.lower() or "aligned" in last_reason.lower()
    volume_ok = "volume too low" not in last_reason.lower()

    def status_icon(ok):
        return ("✓", "#10b981") if ok else ("○", "#ef4444")

    data_icon, data_color = status_icon(data_ok)
    conf_icon, conf_color = status_icon(confluence_ok)
    mom_icon, mom_color = status_icon(momentum_ok)
    vol_icon, vol_color = status_icon(volume_ok)

    if last_action in ("buy", "sell"):
        exec_icon, exec_color = "✓", "#10b981"
        exec_text = last_action.upper()
    else:
        exec_icon, exec_color = "○", "#6b7280"
        exec_text = "WAIT"

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; background: #1a1a1a; padding: 20px; border-radius: 12px; flex-wrap: wrap; gap: 10px;">
        <div style="text-align: center; min-width: 100px;">
            <div style="color: {data_color}; font-size: 2rem;">{data_icon}</div>
            <div style="color: #ffffff; font-weight: 600;">DATA</div>
            <div style="color: #6b7280; font-size: 0.8rem;">{data_ready_count}/{total_pairs} ready</div>
        </div>
        <div style="color: #3a3a3a; font-size: 1.5rem;">→</div>
        <div style="text-align: center; min-width: 100px;">
            <div style="color: {conf_color}; font-size: 2rem;">{conf_icon}</div>
            <div style="color: #ffffff; font-weight: 600;">CONFLUENCE</div>
            <div style="color: #6b7280; font-size: 0.8rem;">{signal_count}/3 signals</div>
        </div>
        <div style="color: #3a3a3a; font-size: 1.5rem;">→</div>
        <div style="text-align: center; min-width: 100px;">
            <div style="color: {mom_color}; font-size: 2rem;">{mom_icon}</div>
            <div style="color: #ffffff; font-weight: 600;">MOMENTUM</div>
            <div style="color: #6b7280; font-size: 0.8rem;">RSI/MACD/VWAP</div>
        </div>
        <div style="color: #3a3a3a; font-size: 1.5rem;">→</div>
        <div style="text-align: center; min-width: 100px;">
            <div style="color: {vol_color}; font-size: 2rem;">{vol_icon}</div>
            <div style="color: #ffffff; font-weight: 600;">VOLUME</div>
            <div style="color: #6b7280; font-size: 0.8rem;">1.5x spike</div>
        </div>
        <div style="color: #3a3a3a; font-size: 1.5rem;">→</div>
        <div style="text-align: center; min-width: 100px; background: {exec_color}22; padding: 10px; border-radius: 8px;">
            <div style="color: {exec_color}; font-size: 2rem;">{exec_icon}</div>
            <div style="color: {exec_color}; font-weight: 600;">{exec_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ========== SECTION 5 & 6: OPPORTUNITY GAUGES + SKIPPED ==========
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Opportunity Scores")
        gauge_cols = st.columns(min(4, len(all_pairs)))

        for i, (_, row) in enumerate(latest.iterrows()):
            with gauge_cols[i % 4]:
                opp_score = row.get("opportunity_score") or 0
                rr = row.get("risk_reward") or 0
                conf = row.get("confluence_score") or 0
                win_prob = calculate_win_probability(opp_score, rr, conf)

                if HAS_PLOTLY:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=opp_score,
                        title={'text': row.get('pair', '').split('-')[0], 'font': {'color': '#ffffff'}},
                        number={'suffix': '', 'font': {'color': '#ffffff'}},
                        gauge={
                            'axis': {'range': [0, 100], 'tickcolor': '#6b7280'},
                            'bar': {'color': '#10b981'},
                            'bgcolor': '#2a2a2a',
                            'bordercolor': '#3a3a3a',
                            'steps': [
                                {'range': [0, 50], 'color': '#1a1a1a'},
                                {'range': [50, 70], 'color': '#2a2a2a'},
                                {'range': [70, 100], 'color': '#1a3a1a'}
                            ],
                            'threshold': {
                                'line': {'color': '#f59e0b', 'width': 2},
                                'thickness': 0.75,
                                'value': 70
                            }
                        }
                    ))
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        font={'color': '#ffffff'},
                        height=180,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown(f"""
                <div style="text-align: center; margin-top: -10px;">
                    <span style="color: #6b7280;">R:R</span> <span style="color: #10b981; font-weight: 600;">{rr:.2f}</span>
                    <span style="color: #6b7280; margin-left: 10px;">Win</span> <span style="color: #3b82f6; font-weight: 600;">{win_prob*100:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Skipped Opportunities")
        skipped = count_skipped_opportunities(telemetry)

        st.metric("Total Skipped", skipped["total"])

        if skipped["categories"] and HAS_PLOTLY:
            cats = {k: v for k, v in skipped["categories"].items() if v > 0}
            if cats:
                fig = go.Figure(data=[go.Pie(
                    labels=list(cats.keys()),
                    values=list(cats.values()),
                    hole=0.5,
                    marker_colors=['#ef4444', '#f59e0b', '#3b82f6', '#6b7280', '#8b5cf6']
                )])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=200,
                    showlegend=True,
                    legend=dict(font=dict(color='#ffffff', size=10))
                )
                st.plotly_chart(fig, use_container_width=True)

        if skipped["recent"]:
            st.markdown("**Recent:**")
            for item in skipped["recent"][:5]:
                time_str = item["time"].strftime("%H:%M:%S") if hasattr(item["time"], "strftime") else str(item["time"])[:8]
                st.markdown(f"<div style='color: #6b7280; font-size: 0.8rem;'>{time_str} {item['pair']} - {item['category']}</div>", unsafe_allow_html=True)

    st.divider()

    # ========== SECTION 7: ANTICIPATED ENTRY ==========
    st.markdown("### Anticipated Entry")

    anticipated = get_anticipated_entry(telemetry)
    if anticipated:
        dir_color = "#10b981" if anticipated["direction"] == "BUY" else "#ef4444" if anticipated["direction"] == "SELL" else "#6b7280"

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div class="info-card">
                <div style="color: #6b7280; font-size: 0.8rem;">PAIR</div>
                <div style="color: #ffffff; font-size: 1.5rem; font-weight: 600;">{anticipated['pair']}</div>
                <div style="color: {dir_color}; font-weight: 600; margin-top: 8px;">{anticipated['direction']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="info-card">
                <div style="color: #6b7280; font-size: 0.8rem;">CURRENT PRICE</div>
                <div style="color: #ffffff; font-size: 1.5rem; font-weight: 600;">${anticipated['price']:,.2f}</div>
                <div style="color: #6b7280; margin-top: 8px;">Trend: {anticipated['trend']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="info-card">
                <div style="color: #6b7280; font-size: 0.8rem;">WAITING FOR</div>
                <div style="color: #f59e0b; font-size: 1.1rem; font-weight: 500;">{anticipated['waiting_for']}</div>
            </div>
            """, unsafe_allow_html=True)

        if anticipated.get("stop_loss") and anticipated.get("take_profit"):
            st.markdown(f"""
            <div style="background: #1a1a1a; padding: 12px; border-radius: 8px; margin-top: 10px;">
                <span style="color: #6b7280;">Stop Loss:</span> <span style="color: #ef4444;">${anticipated['stop_loss']:,.2f}</span>
                <span style="color: #6b7280; margin-left: 20px;">Take Profit:</span> <span style="color: #10b981;">${anticipated['take_profit']:,.2f}</span>
                <span style="color: #6b7280; margin-left: 20px;">R:R:</span> <span style="color: #ffffff;">{anticipated['risk_reward']:.2f}:1</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ========== SECTION 8: PATTERN ANALYSIS ==========
    st.markdown("### Historical Patterns")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Signal Action Distribution")
        if HAS_PLOTLY:
            action_counts = telemetry["signal_action"].value_counts()
            fig = go.Figure(data=[go.Bar(
                x=action_counts.index,
                y=action_counts.values,
                marker_color=['#10b981' if x == 'buy' else '#ef4444' if x == 'sell' else '#6b7280' for x in action_counts.index]
            )])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                height=250
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Confluence Score Trend")
        if HAS_PLOTLY and "confluence_score" in telemetry.columns:
            conf_data = telemetry[telemetry["confluence_score"].notna()].tail(100)
            if not conf_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=conf_data["timestamp"],
                    y=conf_data["confluence_score"],
                    fill='tozeroy',
                    line=dict(color='#10b981')
                ))
                fig.add_hline(y=1.5, line_dash="dash", line_color="#f59e0b", annotation_text="Min Required")
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=250
                )
                st.plotly_chart(fig, use_container_width=True)


def page_settings():
    render_header()
    st.markdown("## Settings")

    config = load_config()

    tab1, tab2, tab3 = st.tabs(["API", "Risk", "Notifications"])

    with tab1:
        api_key = st.text_input("Coinbase API Key", value=config.get("exchange", {}).get("api_key", ""), type="password")
        api_secret = st.text_input("Coinbase API Secret", value=config.get("exchange", {}).get("api_secret", ""), type="password")
        sandbox = st.toggle("Sandbox Mode", value=config.get("exchange", {}).get("sandbox", True))

    with tab2:
        max_daily_loss = st.number_input("Max Daily Loss ($)", value=config.get("risk_management", {}).get("max_daily_loss_usd", 150))
        max_positions = st.number_input("Max Positions", value=config.get("risk_management", {}).get("max_open_positions", 4))
        use_trailing = st.toggle("Trailing Stops", value=config.get("risk_management", {}).get("use_trailing_stops", True))

    with tab3:
        slack_webhook = st.text_input("Slack Webhook", value=config.get("notifications", {}).get("slack_webhook_url", ""), type="password")

    if st.button("Save", type="primary"):
        config.setdefault("exchange", {})
        config.setdefault("risk_management", {})
        config.setdefault("notifications", {})

        config["exchange"]["api_key"] = api_key
        config["exchange"]["api_secret"] = api_secret
        config["exchange"]["sandbox"] = sandbox
        config["risk_management"]["max_daily_loss_usd"] = max_daily_loss
        config["risk_management"]["max_open_positions"] = max_positions
        config["risk_management"]["use_trailing_stops"] = use_trailing
        config["notifications"]["slack_webhook_url"] = slack_webhook

        save_config(config)
        st.success("Saved")

def page_whats_new():
    render_header()
    st.markdown("## What's New")
    st.markdown("""
    <div class="info-card">
        <div><b>Telemetry</b> – Per-cycle pings for every coin, including data pulls, score, R:R, trend, signal reason, setups, universe, and selected pair.</div>
        <div><b>Live Monitor</b> – News-feed style updates + a full analytics wall (pie, bar, histograms, heatmaps, scatter).</div>
        <div><b>Trade Tracking</b> – Entries, exits, and margin adds saved to history files for full lifecycle review.</div>
        <div><b>Universe</b> – Top-5 market cap + top-5 volume (CoinGecko) filtered to Coinbase pairs.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Files Created")
    st.code(
        "logs/telemetry.jsonl\nlogs/trade_history.json\nlogs/trade_history.csv",
        language="text"
    )

    st.markdown("### Quick Start")
    st.code(
        "cb restart\n"
        "/tmp/crypto_bot_venv/bin/python -m streamlit run "
        "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/dashboard.py",
        language="bash"
    )


# ============ Main ============

def main():
    pages = {
        "Dashboard": page_dashboard,
        "Live Monitor": page_live,
        "Mission Control": page_mission_control,
        "Market Wall": page_market_wall,
        "Analytics": page_analytics,
        "Trade Journal": page_journal,
        "How It Works": page_how_it_works,
        "Backtest": page_backtest,
        "What's New": page_whats_new,
        "Settings": page_settings
    }

    # Top navigation with query-params (stable across reruns)
    if "nav" not in st.session_state:
        st.session_state.nav = "Dashboard"

    param_page = st.query_params.get("page", None)
    if isinstance(param_page, list):
        param_page = param_page[0] if param_page else None
    if param_page in pages:
        st.session_state.nav = param_page

    nav_links = []
    for name in pages.keys():
        active = "active" if name == st.session_state.nav else ""
        nav_links.append(f"<a class='{active}' href='?page={name}' target='_self'>{name}</a>")
    st.markdown("<div class='top-nav'>" + "".join(nav_links) + "</div>", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
        <div style="padding: 24px 0 16px 0;">
            <div style="color: #10b981; font-size: 0.7rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;">EVERLIGHT</div>
            <div style="color: #ffffff; font-size: 1.1rem; font-weight: 500; margin-top: 2px;">Trading Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Sidebar reserved for status only (navigation is in the top menu bar)

        # Bot status
        running = is_bot_running()
        if running:
            st.markdown('<div style="display: flex; align-items: center;"><div class="status-live"></div><span style="color: #10b981; font-size: 0.8rem; font-weight: 500;">LIVE</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color: #6b7280; font-size: 0.8rem;">OFFLINE</div>', unsafe_allow_html=True)

        st.divider()

        price = get_price("BTC-USD")
        st.markdown(f"""
        <div style="color: #6b7280; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;">Bitcoin</div>
        <div style="color: #ffffff; font-size: 1rem; font-weight: 500;">${price:,.2f}</div>
        """, unsafe_allow_html=True)

    pages[st.session_state.nav]()


if __name__ == "__main__":
    main()
