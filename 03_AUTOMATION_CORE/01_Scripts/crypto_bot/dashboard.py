#!/usr/bin/env python3
"""
EVERLIGHT VENTURES - Spot Trading Dashboard
Clean, Modern, Real-Time
"""

import streamlit as st
import pandas as pd
import json
import csv
import subprocess
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

# Optional imports
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ============ Page Config ============
st.set_page_config(
    page_title="EVERLIGHT | Spot Trading",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ Paths ============
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
PID_PATH = BASE_DIR / "data" / "bot.pid"
LOG_PATH = BASE_DIR / "logs" / "bot_console.log"
ENTRY_PRICES_PATH = BASE_DIR / "data" / "entry_prices.json"

# ============ Elegant Dark CSS ============
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', -apple-system, sans-serif !important; }

    /* Luxury dark theme */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #111111 50%, #0d0d0d 100%) !important;
    }

    /* Hide Streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stToolbar"] { display: none; }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #1a1a1a; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #444; }

    /* Main title */
    .main-title {
        font-size: 2rem;
        font-weight: 300;
        color: #fff;
        letter-spacing: 8px;
        text-transform: uppercase;
        margin-bottom: 0;
        padding: 20px 0 5px 0;
    }
    .main-title span {
        color: #38bdf8;
        font-weight: 600;
    }
    .subtitle {
        color: #555;
        font-size: 0.75rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 30px;
    }

    /* Glass card effect */
    .glass-card {
        background: rgba(20, 20, 20, 0.8);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 24px;
        margin: 10px 0;
    }

    /* Balance display */
    .balance-container {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(145deg, rgba(16,185,129,0.1) 0%, rgba(20,20,20,0.9) 100%);
        border: 1px solid rgba(16,185,129,0.2);
        border-radius: 20px;
        margin: 20px 0;
    }
    .balance-label {
        color: #666;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .balance-value {
        color: #fff;
        font-size: 3.5rem;
        font-weight: 300;
        letter-spacing: -2px;
    }
    .balance-value .currency {
        color: #10b981;
        font-size: 2rem;
    }

    /* Position cards */
    .position-card {
        background: rgba(25, 25, 25, 0.9);
        border: 1px solid #222;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    .position-card:hover {
        border-color: #333;
        transform: translateY(-2px);
    }
    .position-symbol {
        font-size: 1.1rem;
        font-weight: 600;
        color: #fff;
    }
    .position-amount {
        color: #888;
        font-size: 0.85rem;
    }
    .position-value {
        font-size: 1.3rem;
        font-weight: 500;
    }
    .position-pnl {
        font-size: 0.9rem;
        font-weight: 500;
    }
    .profit { color: #10b981 !important; }
    .loss { color: #ef4444 !important; }
    .neutral { color: #888 !important; }

    /* Status indicator */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }
    .status-dot.online { background: #10b981; box-shadow: 0 0 10px #10b981; }
    .status-dot.offline { background: #ef4444; animation: none; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Metric styling */
    [data-testid="stMetric"] {
        background: rgba(25, 25, 25, 0.9);
        border: 1px solid #222;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 500 !important;
        color: #fff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
        color: #666 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    [data-testid="stMetricDelta"] > div {
        font-size: 0.8rem !important;
    }

    /* Activity log */
    .activity-log {
        background: rgba(15, 15, 15, 0.9);
        border: 1px solid #1a1a1a;
        border-radius: 12px;
        padding: 16px;
        font-family: 'SF Mono', 'Fira Code', monospace !important;
        font-size: 0.75rem;
        color: #888;
        max-height: 300px;
        overflow-y: auto;
        line-height: 1.8;
    }
    .activity-log .time { color: #444; }
    .activity-log .info { color: #888; }
    .activity-log .success { color: #10b981; }
    .activity-log .error { color: #ef4444; }
    .activity-log .signal { color: #f59e0b; }

    /* Section headers */
    .section-header {
        color: #fff;
        font-size: 0.9rem;
        font-weight: 500;
        letter-spacing: 1px;
        margin: 30px 0 15px 0;
        padding-bottom: 10px;
        border-bottom: 1px solid #222;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(16,185,129,0.3) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        color: #666;
        font-size: 0.8rem;
        letter-spacing: 1px;
        padding: 12px 24px;
    }
    .stTabs [aria-selected="true"] {
        color: #10b981 !important;
        border-bottom: 2px solid #10b981;
    }

    /* Hide default header padding */
    .block-container { padding-top: 2rem; }

    /* Price ticker */
    .price-ticker {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(25,25,25,0.8);
        border-radius: 8px;
        font-size: 0.85rem;
    }
    .ticker-symbol { color: #fff; font-weight: 500; }
    .ticker-price { color: #888; }
    .ticker-change.up { color: #10b981; }
    .ticker-change.down { color: #ef4444; }
</style>
""", unsafe_allow_html=True)


# ============ Helper Functions ============

def load_config() -> dict:
    """Load bot configuration"""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except:
        return {}

def is_bot_running() -> bool:
    """Check if bot process is running"""
    try:
        if PID_PATH.exists():
            pid = int(PID_PATH.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True
    except:
        pass
    # Fallback: detect bot.py process if pid file is stale
    try:
        output = subprocess.check_output(["ps", "-eo", "pid,cmd"], text=True)
        for line in output.splitlines():
            if "python bot.py" in line or "bot.py" in line and "crypto_bot" in line:
                return True
    except Exception:
        pass
    return False

def get_api():
    """Get Coinbase API instance"""
    try:
        from utils.coinbase_api import CoinbaseAPI
        config = load_config()
        exch = config.get("exchange", {})
        return CoinbaseAPI(
            exch.get("api_key", ""),
            exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=exch.get("use_perpetuals", False),
        )
    except Exception as e:
        return None

@st.cache_data(ttl=10)
def get_account_balances() -> dict:
    """Get all account balances from Coinbase"""
    api = get_api()
    if not api:
        return {"total_usd": 0, "positions": [], "cash": {"USD": 0, "USDC": 0}}

    try:
        accounts = api.get_accounts() or []
        positions = []
        cash = {"USD": 0, "USDC": 0}
        total_usd = 0

        for acc in accounts:
            currency = acc.get("currency", "")
            bal = acc.get("available_balance", {})
            amount = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)

            if amount <= 0:
                continue

            if currency in ("USD", "USDC"):
                cash[currency] = amount
                total_usd += amount
            else:
                # Get current price
                price = api.get_current_price(f"{currency}-USD") or 0
                value_usd = amount * price if price else 0

                if value_usd >= 1:  # Only show if worth $1+
                    positions.append({
                        "currency": currency,
                        "amount": amount,
                        "price": price,
                        "value_usd": value_usd
                    })
                    total_usd += value_usd

        return {
            "total_usd": total_usd,
            "positions": sorted(positions, key=lambda x: x["value_usd"], reverse=True),
            "cash": cash
        }
    except Exception as e:
        st.error(f"Error fetching balances: {e}")
        return {"total_usd": 0, "positions": [], "cash": {"USD": 0, "USDC": 0}}

def get_entry_prices() -> dict:
    """Load entry prices for P/L calculation"""
    try:
        if ENTRY_PRICES_PATH.exists():
            with open(ENTRY_PRICES_PATH) as f:
                return json.load(f)
    except:
        pass
    return {}

@st.cache_data(ttl=5)
def get_current_price(pair: str) -> float:
    """Get current price for a pair"""
    api = get_api()
    if api:
        return api.get_current_price(pair) or 0
    return 0

def get_recent_logs(lines: int = 50) -> list:
    """Get recent bot log entries"""
    try:
        if LOG_PATH.exists():
            with open(LOG_PATH) as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
    except:
        pass
    return []

def parse_log_line(line: str) -> dict:
    """Parse a log line into components"""
    try:
        # Format: 2026-02-02 15:44:41,739 | INFO | Message
        parts = line.split(" | ", 2)
        if len(parts) >= 3:
            timestamp = parts[0].strip()
            level = parts[1].strip()
            message = parts[2].strip()
            return {"time": timestamp, "level": level, "message": message}
    except:
        pass
    return {"time": "", "level": "INFO", "message": line.strip()}

def start_bot():
    """Start the trading bot"""
    try:
        subprocess.Popen(
            ["nohup", "python3", "bot.py"],
            stdout=open(LOG_PATH, "a"),
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            start_new_session=True
        )
        time.sleep(2)
        return True
    except Exception as e:
        st.error(f"Failed to start bot: {e}")
        return False

def stop_bot():
    """Stop the trading bot"""
    try:
        if PID_PATH.exists():
            pid = int(PID_PATH.read_text().strip())
            os.kill(pid, 15)  # SIGTERM
            time.sleep(1)
            return True
    except:
        pass
    return False


# ============ UI Components ============

def render_header():
    """Render the main header"""
    st.markdown("""
        <div class="main-title">EVER<span>LIGHT</span></div>
        <div class="subtitle">Spot Trading Terminal</div>
    """, unsafe_allow_html=True)

def render_bot_status():
    """Render bot status indicator"""
    running = is_bot_running()
    status_class = "online" if running else "offline"
    status_text = "LIVE" if running else "OFFLINE"

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; padding: 10px 0;">
                <span class="status-dot {status_class}"></span>
                <span style="color: {'#10b981' if running else '#ef4444'}; font-weight: 500; letter-spacing: 1px;">
                    {status_text}
                </span>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        if running:
            if st.button("⏹ Stop", key="stop_btn"):
                stop_bot()
                st.rerun()
        else:
            if st.button("▶ Start", key="start_btn"):
                start_bot()
                st.rerun()

    with col3:
        if st.button("🔄 Refresh", key="refresh_btn"):
            st.cache_data.clear()
            st.rerun()

def render_balance_card(balances: dict):
    """Render the main balance display"""
    total = balances.get("total_usd", 0)
    cash = balances.get("cash", {})

    # Format total with commas
    total_formatted = f"{total:,.2f}"

    st.markdown(f"""
        <div class="balance-container">
            <div class="balance-label">Total Portfolio Value</div>
            <div class="balance-value">
                <span class="currency">$</span>{total_formatted}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Cash breakdown
    col1, col2 = st.columns(2)
    with col1:
        st.metric("USD Cash", f"${cash.get('USD', 0):,.2f}")
    with col2:
        st.metric("USDC", f"${cash.get('USDC', 0):,.2f}")

def render_positions(balances: dict):
    """Render current positions"""
    positions = balances.get("positions", [])
    entry_prices = get_entry_prices()

    st.markdown('<div class="section-header">POSITIONS</div>', unsafe_allow_html=True)

    if not positions:
        st.markdown("""
            <div style="text-align: center; padding: 40px; color: #444;">
                No open positions
            </div>
        """, unsafe_allow_html=True)
        return

    for pos in positions:
        currency = pos["currency"]
        amount = pos["amount"]
        price = pos["price"]
        value = pos["value_usd"]

        # Calculate P/L if we have entry price
        pair = f"{currency}-USD"
        entry = entry_prices.get(pair)
        if isinstance(entry, dict):
            entry = entry.get("price")

        pnl_pct = 0
        pnl_class = "neutral"
        if entry and entry > 0:
            pnl_pct = ((price - entry) / entry) * 100
            pnl_class = "profit" if pnl_pct >= 0 else "loss"

        pnl_sign = "+" if pnl_pct >= 0 else ""

        st.markdown(f"""
            <div class="position-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="position-symbol">{currency}</div>
                        <div class="position-amount">{amount:.6f} @ ${price:,.4f}</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="position-value">${value:,.2f}</div>
                        <div class="position-pnl {pnl_class}">{pnl_sign}{pnl_pct:.2f}%</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def load_open_trades() -> list:
    path = Path(__file__).parent / "logs" / "trade_history.csv"
    if not path.exists():
        return []
    try:
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            return [r for r in reader if r.get("status") == "OPEN"]
    except Exception:
        return []

def load_last_decision() -> dict:
    path = Path(__file__).parent / "logs" / "telemetry.jsonl"
    if not path.exists():
        return {}
    try:
        lines = path.read_text().splitlines()
        for line in reversed(lines):
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj:
                return obj
    except Exception:
        pass
    return {}

def render_summary_cards(balances: dict):
    total = balances.get("total_usd", 0)
    trades = load_open_trades()
    current = trades[0] if trades else {}
    last_decision = load_last_decision()
    st.markdown('<div class="section-header">OVERVIEW</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div style="color:#9aa0a6; font-size:0.75rem;">PORTFOLIO</div>
            <div style="color:#fff; font-size:1.6rem;">${total:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div style="color:#9aa0a6; font-size:0.75rem;">CURRENT TRADE</div>
            <div style="color:#fff; font-size:1.1rem;">{current.get('pair','—')} {current.get('side','').upper()}</div>
            <div style="color:#6b7280; font-size:0.8rem;">Entry {current.get('entry_price','—')} • SL {current.get('stop_loss','—')} • TP {current.get('take_profit','—')}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div style="color:#9aa0a6; font-size:0.75rem;">LAST DECISION</div>
            <div style="color:#fff; font-size:1.1rem;">{last_decision.get('pair','—')}</div>
            <div style="color:#6b7280; font-size:0.8rem;">{last_decision.get('signal_reason','—')}</div>
        </div>
        """, unsafe_allow_html=True)

def render_trade_plan():
    """Render open trades with entry/SL/TP from trade log."""
    trades = load_open_trades()
    st.markdown('<div class="section-header">TRADE PLAN</div>', unsafe_allow_html=True)
    if not trades:
        st.markdown("<div style='color:#444;'>No open trades logged.</div>", unsafe_allow_html=True)
        return
    for t in trades:
        st.markdown(f"""
            <div class="glass-card">
                <div style="display:flex; justify-content:space-between;">
                    <div style="color:#fff; font-weight:600;">{t.get('pair')}</div>
                    <div style="color:#10b981;">{t.get('side','').upper()}</div>
                </div>
                <div style="color:#9aa0a6; margin-top:6px;">Entry: {t.get('entry_price')} • SL: {t.get('stop_loss')} • TP: {t.get('take_profit')}</div>
                <div style="color:#6b7280; margin-top:4px;">Opened: {t.get('entry_time')}</div>
            </div>
        """, unsafe_allow_html=True)

def render_activity_log():
    """Render recent activity log"""
    st.markdown('<div class="section-header">ACTIVITY</div>', unsafe_allow_html=True)

    logs = get_recent_logs(30)

    if not logs:
        st.markdown("""
            <div class="activity-log">
                <span class="info">No recent activity</span>
            </div>
        """, unsafe_allow_html=True)
        return

    log_html = []
    for line in reversed(logs[-20:]):  # Show last 20, newest first
        parsed = parse_log_line(line)
        msg = parsed["message"]

        # Determine style based on content
        style_class = "info"
        if "ERROR" in parsed["level"] or "FAILED" in msg:
            style_class = "error"
        elif "BUY" in msg or "SELL" in msg or "Signal" in msg:
            style_class = "signal"
        elif "✅" in msg or "profit" in msg.lower() or "HOLDING" in msg:
            style_class = "success"

        # Truncate long messages
        if len(msg) > 100:
            msg = msg[:100] + "..."

        time_part = parsed["time"].split(",")[0] if parsed["time"] else ""
        time_short = time_part.split(" ")[-1] if " " in time_part else time_part

        log_html.append(f'<div><span class="time">{time_short}</span> <span class="{style_class}">{msg}</span></div>')

    st.markdown(f"""
        <div class="activity-log">
            {''.join(log_html)}
        </div>
    """, unsafe_allow_html=True)

def render_quick_stats(balances: dict):
    """Render quick statistics"""
    config = load_config()
    positions = balances.get("positions", [])

    # Get config values
    trade_size_pct = config.get("position_sizing", {}).get("percent", 0.10)
    total = balances.get("total_usd", 0)
    trade_size = total * trade_size_pct

    st.markdown('<div class="section-header">SETTINGS</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Trade Size", f"${trade_size:.2f}", f"{trade_size_pct*100:.0f}%")

    with col2:
        st.metric("Open Positions", len(positions), f"/ 10 max")

    with col3:
        min_profit = config.get("exit_strategy", {}).get("min_profit_percent", 7)
        st.metric("Profit Target", f"{min_profit}%")

    with col4:
        mode = "LIVE" if is_bot_running() else "STOPPED"
        st.metric("Mode", mode)

def render_market_prices():
    """Render live market prices for tracked pairs"""
    config = load_config()
    universe = config.get("universe", {})
    symbols = universe.get("include_symbols", ["BTC", "ETH", "XRP", "SOL"])[:8]

    st.markdown('<div class="section-header">MARKETS</div>', unsafe_allow_html=True)

    cols = st.columns(4)

    for i, symbol in enumerate(symbols):
        pair = f"{symbol}-USD"
        price = get_current_price(pair)

        with cols[i % 4]:
            st.markdown(f"""
                <div class="price-ticker">
                    <span class="ticker-symbol">{symbol}</span>
                    <span class="ticker-price">${price:,.4f}</span>
                </div>
            """, unsafe_allow_html=True)


# ============ Main App ============

def main():
    # Auto-refresh every 15 seconds
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=15000, key="datarefresh")
    except ImportError:
        pass

    # Header
    render_header()

    # Bot status
    render_bot_status()

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        # Balance card
        balances = get_account_balances()
        render_balance_card(balances)
        render_summary_cards(balances)

        # Positions
        render_positions(balances)
        render_trade_plan()

    with col2:
        # Quick stats
        render_quick_stats(balances)

        # Activity log
        render_activity_log()

    # Market prices at bottom
    st.markdown("<br>", unsafe_allow_html=True)
    render_market_prices()

    # Footer
    st.markdown("""
        <div style="text-align: center; padding: 40px 0 20px 0; color: #333; font-size: 0.7rem; letter-spacing: 2px;">
            EVERLIGHT VENTURES © 2026
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
