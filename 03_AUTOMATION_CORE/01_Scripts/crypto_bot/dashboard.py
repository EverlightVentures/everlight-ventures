#!/usr/bin/env python3
"""
CDE_BOT - Trading Hub Dashboard
Clean, Real-Time, Futures + Spot visibility (Coinbase)
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
    page_title="CDE_BOT | Trading Hub",
    page_icon="CDE",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============ Paths ============
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
PID_PATH = BASE_DIR / "data" / "bot.pid"
DB_PID_PATH = BASE_DIR / "data" / "dashboard.pid"
LOG_PATH = BASE_DIR / "logs" / "bot_console.log"
ENTRY_PRICES_PATH = BASE_DIR / "data" / "entry_prices.json"
TELEMETRY_PATH = BASE_DIR / "logs" / "telemetry.jsonl"
MARGIN_POLICY_PATH = BASE_DIR / "logs" / "margin_policy.jsonl"
PLRL3_PATH = BASE_DIR / "logs" / "plrl3.jsonl"

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

def _tail_lines(path: Path, *, max_lines: int = 200, max_bytes: int = 200_000) -> list[str]:
    """Fast tail without reading entire file (safe for large JSONL like telemetry.jsonl)."""
    try:
        if not path.exists():
            return []
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - int(max_bytes))
            f.seek(start)
            data = f.read().decode("utf-8", errors="replace")
        lines = data.splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def _read_jsonl_tail(path: Path, *, max_items: int = 50) -> list[dict]:
    out: list[dict] = []
    for line in _tail_lines(path, max_lines=max_items * 3):
        line = (line or "").strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out[-max_items:]


def _cfm_product_to_pair(product_id: str) -> str | None:
    if not product_id:
        return None
    prefix = str(product_id).split("-")[0]
    prefix_map = {
        "BIP": "BTC",
        "ETP": "ETH",
        "SLP": "SOL",
        "AVP": "AVAX",
        "DOP": "DOGE",
        "LNP": "LINK",
        "LCP": "LTC",
        "ADP": "ADA",
        "SHP": "SHIB",
        "HEP": "HBAR",
        "SUP": "SUI",
        "XLP": "XLM",
        "POP": "DOT",
        "XPP": "XRP",
    }
    base = prefix_map.get(prefix)
    return f"{base}-USD" if base else None

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
    # Fallback: detect bot.py process if pid file is stale.
    # We validate by checking if the process has our bot_console.log open.
    try:
        output = subprocess.check_output(["ps", "-eo", "pid,cmd"], text=True)
        for line in output.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) != 2:
                continue
            pid_s, cmd = parts
            if "python3 bot.py" not in cmd and "crypto_bot/bot.py" not in cmd:
                continue
            try:
                pid = int(pid_s)
            except Exception:
                continue

            try:
                fd_dir = Path(f"/proc/{pid}/fd")
                for fd in fd_dir.iterdir():
                    try:
                        target = os.readlink(fd)
                    except Exception:
                        continue
                    if str(LOG_PATH) in str(target):
                        return True
            except Exception:
                continue
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


@st.cache_data(ttl=2)
def get_cfm_positions() -> list[dict]:
    """Get CFM futures positions (if enabled)."""
    api = get_api()
    if not api:
        return []
    try:
        cfg = load_config()
        exch = cfg.get("exchange", {}) or {}
        ps = cfg.get("perps_short", {}) or {}
        cfm_enabled = str(exch.get("futures_type", "") or "").lower() == "cfm" or (
            bool(ps.get("enabled")) and str(ps.get("futures_type", "") or "").lower() == "cfm"
        )
        if not cfm_enabled:
            return []
        return api.get_futures_positions() or []
    except Exception:
        return []


@st.cache_data(ttl=2)
def get_cfm_balance_summary() -> dict:
    api = get_api()
    if not api:
        return {}
    try:
        return api.get_futures_balance_summary() or {}
    except Exception:
        return {}


def get_latest_margin_policy() -> dict | None:
    items = _read_jsonl_tail(MARGIN_POLICY_PATH, max_items=5)
    return items[-1] if items else None


def get_latest_plrl3() -> dict | None:
    items = _read_jsonl_tail(PLRL3_PATH, max_items=10)
    return items[-1] if items else None

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
        subprocess.run(["bash", "cb", "start"], cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(1)
        return is_bot_running()
    except Exception as e:
        st.error(f"Failed to start bot: {e}")
        return False

def stop_bot():
    """Stop the trading bot"""
    try:
        subprocess.run(["bash", "cb", "stop"], cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(1)
        return not is_bot_running()
    except:
        pass
    return False


# ============ UI Components ============

def render_header():
    """Render the main header"""
    st.markdown("""
        <div class="main-title">CDE<span>_BOT</span></div>
        <div class="subtitle">Trading Hub: Futures (CFM) + Spot</div>
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

    # Futures (CFM)
    cfm_positions = get_cfm_positions()
    if cfm_positions:
        cfg = load_config()
        rev = cfg.get("cfm_reversal", {}) or {}
        min_profit = float(rev.get("min_lock_profit_usd", 2.0) or 2.0)
        min_conf = int(rev.get("min_confluence", 4) or 4)
        exit_min_conf = int(rev.get("exit_min_confluence", min_conf) or min_conf)
        flip_on = bool(rev.get("flip_enabled", True))

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">FUTURES (CFM)</div>', unsafe_allow_html=True)

        for fp in cfm_positions:
            product_id = fp.get("product_id") or fp.get("productId") or fp.get("symbol") or ""
            side = str(fp.get("side") or "").upper() or "?"
            try:
                contracts = float(
                    fp.get("number_of_contracts")
                    or fp.get("contracts")
                    or fp.get("size")
                    or fp.get("base_size")
                    or fp.get("position_size")
                    or 0
                )
            except Exception:
                contracts = 0.0
            try:
                entry = float(fp.get("entry_price") or fp.get("avg_entry_price") or fp.get("average_entry_price") or 0)
            except Exception:
                entry = 0.0

            pair = _cfm_product_to_pair(str(product_id)) or ""
            mark = get_current_price(pair) if pair else 0.0

            # Best-effort unrealized PnL fields if present.
            upnl = None
            for k in ("unrealized_pnl", "unrealizedPnL", "unrealized_pnl_usd", "unrealized_profit_loss"):
                if k in fp:
                    try:
                        upnl = float(fp.get(k) or 0)
                    except Exception:
                        upnl = None
                    break

            pnl_class = "neutral"
            if upnl is not None:
                pnl_class = "profit" if upnl > 0 else ("loss" if upnl < 0 else "neutral")

            tel = load_last_telemetry_for_pair(pair) if pair else {}
            sig_action = str(tel.get("signal_action") or "hold").lower()
            sig_reason = str(tel.get("signal_reason") or "")
            try:
                conf = int(tel.get("confluence_count")) if tel.get("confluence_count") is not None else None
            except Exception:
                conf = None

            is_short = ("SELL" in side) or ("SHORT" in side)
            opposite = "buy" if is_short else "sell"
            profit_lock_ready = bool(upnl is not None and float(upnl) >= float(min_profit))
            reversal_ready = bool(sig_action == opposite and (conf is None or conf >= min_conf))

            st.markdown(
                f"""
                <div class="position-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div class="position-symbol">{product_id}</div>
                            <div class="position-amount">{side} • {contracts:.4f} contracts • {pair or 'n/a'}</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="position-value">${mark:,.4f}</div>
                            <div class="position-pnl {pnl_class}">{'' if upnl is None else f'${upnl:,.2f} uPnL'}</div>
                        </div>
                    </div>
                    <div style="margin-top:10px; color:#666; font-size:0.8rem; display:flex; justify-content:space-between;">
                        <span>Entry: ${entry:,.4f}</span>
                        <span>Mark: ${mark:,.4f}</span>
                    </div>
                    <div style="margin-top:10px; color:#6b7280; font-size:0.8rem;">
                        Profit-lock: {min_profit:.2f} USD • Reversal requires: {opposite.upper()} with conf ≥ {exit_min_conf} • Flip: {'ON' if flip_on else 'OFF'}
                    </div>
                    <div style="margin-top:6px; color:#9aa0a6; font-size:0.8rem;">
                        Last signal: {pair} → {sig_action.upper()} {f'({conf}/6)' if conf is not None else ''} {('- ' + sig_reason) if sig_reason else ''}
                    </div>
                    <div style="margin-top:6px; color:{'#10b981' if (profit_lock_ready and reversal_ready) else '#6b7280'}; font-size:0.85rem; font-weight:600;">
                        {'EXIT ARMED (profit lock + reversal confirmed)' if (profit_lock_ready and reversal_ready) else ('Profit lock ready; waiting on reversal confirm' if profit_lock_ready else 'Holding; profit lock not reached yet')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div class="glass-card" style="text-align: center; padding: 18px; color: #444;">
                No open CFM futures positions detected
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Spot
    st.markdown('<div class="section-header">SPOT</div>', unsafe_allow_html=True)
    if not positions:
        st.markdown(
            """
            <div style="text-align: center; padding: 22px; color: #444;">
                No spot positions
            </div>
            """,
            unsafe_allow_html=True,
        )
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
    items = _read_jsonl_tail(TELEMETRY_PATH, max_items=5)
    return items[-1] if items else {}

def load_last_telemetry_for_pair(pair: str) -> dict:
    """Return the most recent telemetry record for a specific pair (best-effort)."""
    pair = (pair or "").strip()
    if not pair:
        return {}
    for rec in reversed(_read_jsonl_tail(TELEMETRY_PATH, max_items=250)):
        try:
            if str(rec.get("pair") or "") == pair:
                return rec
        except Exception:
            continue
    return {}

def render_summary_cards(balances: dict):
    total = balances.get("total_usd", 0)
    cfm_positions = get_cfm_positions()
    current_cfm = cfm_positions[0] if cfm_positions else {}
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
        if current_cfm:
            product_id = current_cfm.get("product_id") or current_cfm.get("productId") or current_cfm.get("symbol") or "—"
            side = str(current_cfm.get("side") or "").upper() or "?"
            try:
                contracts = float(
                    current_cfm.get("number_of_contracts")
                    or current_cfm.get("contracts")
                    or current_cfm.get("size")
                    or current_cfm.get("base_size")
                    or current_cfm.get("position_size")
                    or 0
                )
            except Exception:
                contracts = 0.0
            pair = _cfm_product_to_pair(str(product_id)) or ""
            upnl = None
            for k in ("unrealized_pnl", "unrealizedPnL", "unrealized_pnl_usd", "unrealized_profit_loss"):
                if k in current_cfm:
                    try:
                        upnl = float(current_cfm.get(k) or 0)
                    except Exception:
                        upnl = None
                    break
            upnl_txt = f"${upnl:,.2f} uPnL" if upnl is not None else ""
            st.markdown(f"""
            <div class="glass-card">
                <div style="color:#9aa0a6; font-size:0.75rem;">CURRENT POSITION (CFM)</div>
                <div style="color:#fff; font-size:1.1rem;">{product_id} {side}</div>
                <div style="color:#6b7280; font-size:0.8rem;">{contracts:.4f} contracts • {pair or 'n/a'} • {upnl_txt}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
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

    def _parse_ts(s: str) -> datetime | None:
        s = (s or "").strip()
        if not s:
            return None
        # bot_console format: "YYYY-mm-dd HH:MM:SS,ms"
        try:
            if "," in s and " " in s:
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S,%f")
        except Exception:
            pass
        # jsonl iso: "...Z"
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except Exception:
            return None

    events: list[dict] = []

    # Bot console
    for line in _tail_lines(LOG_PATH, max_lines=80):
        parsed = parse_log_line(line)
        ts = _parse_ts(parsed.get("time") or "")
        events.append(
            {
                "ts": ts or datetime.min,
                "time": (parsed.get("time") or "").split(",")[0].split(" ")[-1] if parsed.get("time") else "",
                "source": "bot",
                "level": parsed.get("level") or "INFO",
                "message": parsed.get("message") or "",
            }
        )

    # Margin policy + PLRL-3 (JSONL)
    for rec in _read_jsonl_tail(MARGIN_POLICY_PATH, max_items=15):
        metrics = rec.get("metrics") or {}
        tier = rec.get("tier") or "UNKNOWN"
        mr = metrics.get("active_mr")
        src = metrics.get("active_mr_source")
        ts = _parse_ts(rec.get("ts") or rec.get("timestamp") or "")
        msg = f"MarginPolicy {tier} (MR={mr} src={src})"
        events.append({"ts": ts or datetime.min, "time": "", "source": "margin", "level": "INFO", "message": msg})

    for rec in _read_jsonl_tail(PLRL3_PATH, max_items=25):
        action = rec.get("action") or "n/a"
        pid = rec.get("product_id") or ""
        step = rec.get("rescue_step")
        addc = rec.get("add_contracts")
        ts = _parse_ts(rec.get("ts") or rec.get("timestamp") or "")
        msg = f"PLRL-3 {action} {pid} step={step} add={addc}"
        events.append({"ts": ts or datetime.min, "time": "", "source": "plrl3", "level": "INFO", "message": msg})

    # Selected-pair telemetry (very light, tail only)
    for rec in _read_jsonl_tail(TELEMETRY_PATH, max_items=40):
        if not rec.get("is_selected"):
            continue
        action = rec.get("signal_action") or "hold"
        if action == "hold":
            continue
        ts = _parse_ts(rec.get("timestamp") or "")
        msg = f"Signal {rec.get('pair')} -> {action} ({rec.get('signal_reason')})"
        events.append({"ts": ts or datetime.min, "time": "", "source": "signal", "level": "INFO", "message": msg})

    events = [e for e in events if e.get("message")]
    events.sort(key=lambda e: e["ts"], reverse=True)

    if not events:
        st.markdown(
            """
            <div class="activity-log">
                <span class="info">No recent activity</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    log_html = []
    for e in events[:30]:
        msg = str(e.get("message") or "")
        src = str(e.get("source") or "info")
        level = str(e.get("level") or "INFO")

        style_class = "info"
        if src in ("signal",):
            style_class = "signal"
        if src in ("margin", "plrl3"):
            style_class = "success"
        if "ERROR" in level or "failed" in msg.lower():
            style_class = "error"
        if len(msg) > 110:
            msg = msg[:110] + "..."

        ts = e.get("ts")
        time_short = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) and ts != datetime.min else ""
        log_html.append(f'<div><span class="time">{time_short}</span> <span class="{style_class}">{msg}</span></div>')

    st.markdown(
        f"""
        <div class="activity-log">
            {''.join(log_html)}
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">RISK</div>', unsafe_allow_html=True)

    mp = get_latest_margin_policy()
    pl = get_latest_plrl3()

    r1, r2 = st.columns(2)
    with r1:
        if mp:
            tier = (mp.get("tier") or "UNKNOWN")
            active_mr = None
            try:
                active_mr = float((mp.get("metrics") or {}).get("active_mr"))
            except Exception:
                active_mr = None
            st.metric("Margin Tier", str(tier), f"MR {active_mr:.3f}" if active_mr is not None else "")
        else:
            st.metric("Margin Tier", "n/a")
    with r2:
        if pl:
            action = pl.get("action") or "n/a"
            step = pl.get("rescue_step")
            try:
                step = int(step)
            except Exception:
                step = None
            st.metric("PLRL-3", str(action), f"step {step}" if step is not None else "")
        else:
            st.metric("PLRL-3", "n/a")

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
    # Auto-refresh for near-real-time feel (Streamlit reruns; cache_data keeps API calls bounded).
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=2000, key="datarefresh")
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
            CDE_BOT © 2026
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
