# XLM Dashboard: Streamlit to Django Migration

## Context
The XLM trading bot dashboard is an 8,596-line Streamlit monolith (`xlm_bot/dashboard.py`). Streamlit's full-page-rerun model is limiting for a real-time trading command center. Converting to Django gives proper routing, HTMX partial updates, and visual parity with the existing Hive Mind luxury theme at `09_DASHBOARD/hive_dashboard/`.

## Architecture Decisions
- **Standalone Django project** at `xlm_bot/dashboard_django/`
- **Port the Hive luxury theme** (gold/dark glassmorphism, Inter + Playfair Display fonts)
- **HTMX polling** (2-5s) for live data (replaces Streamlit auto-rerun)
- **Lightweight Charts** for financial charts + **Chart.js** for analytics
- **File-based data layer** (same as current: state.json, trades.csv, JSONL logs, Coinbase API)
- **Django LocMemCache** replaces `@st.cache_data` using `file_sig()` keys
- **No database models** (all data from files + API, SQLite only for Django internals)
- **Same port** (8502) and env vars as current dashboard

## Project Structure

```
xlm_bot/dashboard_django/
    manage.py
    requirements.txt
    start.sh
    xlm_dashboard/                    # Django settings package
        settings.py, urls.py, wsgi.py
    trading/                          # Single Django app
        apps.py, urls.py, middleware.py, context_processors.py
        views/
            terminal.py               # Terminal (Overview, Intel Hub, Chat, Evolution)
            portfolio.py              # Portfolio page
            signals.py                # Signals page
            ledger.py                 # Ledger page
            system.py                 # System page
            api.py                    # JSON/HTML endpoints for HTMX polling
        services/                     # Data layer (ports 40+ helpers from dashboard.py)
            file_reader.py            # JSONL/CSV/state/snapshot loading + cache
            exchange.py               # Coinbase API wrappers (15s TTL cache)
            formatters.py             # Money/time/NaN-safe formatting
            analytics.py              # Trade quality, parameter performance
            events.py                 # Major event builder
            position.py               # Position normalization, TP levels, orders
            market.py                 # Orchestration, AI feedback, equity series
        templatetags/
            trading_tags.py           # Filters: money, pnl_color, direction_badge, etc.
        static/trading/
            css/theme.css             # Shared luxury theme (from Hive base.html CSS vars)
            js/ticker.js, lightweight.js, charts.js, common.js
        templates/trading/
            base.html                 # Sidebar + topbar + content shell
            partials/                 # Reusable: kpi_bar, position_badge, bot_analytics
            terminal/                 # page.html + overview/intel/chat/evolution
            portfolio/                # page.html + partials/
            signals/                  # page.html + partials/
            ledger/                   # page.html + partials/
            system/                   # page.html + partials/
```

## Pages (all 5)

| Page | Sub-tabs | Key Content |
|------|----------|-------------|
| **Terminal** | Overview, Intel Hub, Chat, Evolution | Price bar, regime/vol badges, gates, direction scores, readiness bars, contract intel, events, AI directives, chat iframe, quality scorecard |
| **Portfolio** | -- | Account KPIs, spot balances, equity/price charts, open positions, cash movements |
| **Signals** | -- | Current signal, signal history, gate pressure, quality scores, param performance, HTF zones |
| **Ledger** | -- | Major events feed (80 items/7d), market intel, trades CSV, cash movements, bot events |
| **System** | -- | Bot DNA config viewer, data snapshot JSON, log tails |

## HTMX Polling Endpoints

| Endpoint | Rate | Returns |
|----------|------|---------|
| `/api/sidebar-status/` | 5s | HTML partial - sidebar bot metrics |
| `/api/kpi-bar/` | 5s | HTML partial - top KPI cards |
| `/api/position-badge/` | 5s | HTML partial - position truth |
| `/api/thought-feed/` | 5s | HTML partial - decision feed |
| `/api/bot-analytics/` | 10s | HTML partial - regime/win rate |
| `/api/trade-log/` | 10s | HTML partial - recent trades |
| `/api/equity-data/` | 30s | JSON - chart data |
| `/api/major-events/` | 15s | HTML partial - events feed |
| `/api/signals-current/` | 5s | HTML partial - signal badge |
| `/api/logs-tail/` | 5s | HTML partial - log viewer |

## Implementation Phases

### Phase 1: Skeleton + Theme
- Create Django project: manage.py, settings.py, urls.py, wsgi.py
- Create `trading` app: apps.py, urls.py
- Port Hive luxury theme CSS into `static/trading/css/theme.css`
- Build `base.html` with sidebar nav (Terminal, Portfolio, Signals, Ledger, System)
- Empty TerminalView renders themed shell
- **Verify**: page renders on :8502

### Phase 2: Data Layer (services/)
- Port 40+ helpers into 7 service modules (file_reader, exchange, formatters, analytics, events, position, market)
- Replace `@st.cache_data` with Django LocMemCache + file_sig keys
- **Verify**: management command loads state.json

### Phase 3: Template Tags + Context Processors
- `trading_tags.py`: money, pnl_color, direction_badge, status_badge, duration_fmt, regime_color, etc.
- `context_processors.py`: bot status, price, position for sidebar
- **Verify**: sidebar shows live bot status

### Phase 4: Terminal Page
- Full Terminal with all 4 sub-tabs via HTMX tab switching
- Overview: KPI bar, position badge, regime badges, gates, direction scores, readiness bars, contract intel, events
- Intel Hub: market brief, agent thoughts, team reports
- Chat: iframe
- Evolution: quality scorecard, param perf
- **Verify**: Terminal matches Streamlit feature-for-feature

### Phase 5: HTMX Polling
- Create `api.py` with all polling endpoints
- Wire `hx-get`/`hx-trigger` into templates
- **Verify**: KPIs, position, thoughts auto-update every 5s

### Phase 6: Portfolio Page
- Account KPIs, spot balances, equity+price charts (Lightweight Charts), positions, cash movements
- **Verify**: charts render with live data

### Phase 7: Signals Page
- Current signal, history, gate pressure, quality, param perf, gate effectiveness, HTF zones, ATR audit
- **Verify**: signal data populates

### Phase 8: Ledger Page
- Major events (80 items/7d), market intel stream, trades table, cash movements, bot events
- **Verify**: event feed works

### Phase 9: System Page
- Bot DNA config YAML viewer, data snapshot JSON, log tails
- **Verify**: config renders

### Phase 10: Charts + Polish
- Lightweight Charts dual panel (equity + price + trade markers + TP/SL lines)
- Chart.js analytics charts
- Responsive breakpoints, loading indicators
- Update `xdr-fg` start script
- **Verify**: all charts work, mobile collapses properly

## Key Source Files
- `xlm_bot/dashboard.py` -- 8,596-line source monolith to decompose
- `09_DASHBOARD/hive_dashboard/hive/templates/hive/base.html` -- theme CSS to port
- `09_DASHBOARD/hive_dashboard/hive/views.py` -- Django view patterns (HTMX, partial rendering)
- `09_DASHBOARD/hive_dashboard/hive/templatetags/hive_tags.py` -- tag patterns to extend
- `xlm_bot/vendor/utils/coinbase_api.py` -- API client to import

## Verification
1. `cd xlm_bot/dashboard_django && python manage.py runserver 0.0.0.0:8502`
2. Open browser -- see Terminal with live KPIs, position, charts
3. Navigate all 5 pages -- each renders with data
4. Watch HTMX polling -- updates without full page reload
5. Compare with Streamlit dashboard -- feature parity
