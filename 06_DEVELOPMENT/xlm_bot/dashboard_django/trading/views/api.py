"""HTMX polling endpoints -- return HTML partials or JSON for live updates."""
import json
from django.http import JsonResponse
from django.template.loader import render_to_string

from trading.services import file_reader, exchange, formatters, events, market, position


def _html(request, template, context):
    """Render a partial template to HTTP response."""
    from django.http import HttpResponse
    html = render_to_string(template, context, request=request)
    return HttpResponse(html)


def sidebar_status(request):
    """Sidebar bot metrics: price, margin, tick age, position."""
    snap = file_reader.load_snapshot()
    state = file_reader.load_state()
    alive, bot_age_s = file_reader.bot_alive()
    balance = exchange.get_futures_balance()
    positions = exchange.get_cfm_positions()
    norm_pos = position.normalize_cfm_position(positions[0]) if positions else None
    return _html(request, "trading/partials/sidebar_status.html", {
        "snap": snap, "state": state, "balance": balance, "norm_position": norm_pos,
        "bot_alive": alive, "bot_age_s": bot_age_s,
    })


def kpi_bar(request):
    """Top KPI cards: total balance, cash, futures, position, unrealized, PnL."""
    balance = exchange.get_futures_balance()
    portfolio_raw = exchange.get_portfolio_breakdown()
    spot_raw = exchange.get_spot_balances()
    snap = file_reader.load_snapshot()
    positions = exchange.get_cfm_positions()
    norm_pos = position.normalize_cfm_position(positions[0]) if positions else None
    alive, _ = file_reader.bot_alive()
    portfolio = {
        "total_balance": portfolio_raw.get("total", 0),
        "cash_total": portfolio_raw.get("cash", 0),
        "crypto_total": portfolio_raw.get("crypto", 0),
        "futures_total": portfolio_raw.get("futures", 0),
        "usd_balance": spot_raw.get("USD", 0),
        "usdc_balance": spot_raw.get("USDC", 0),
    }
    return _html(request, "trading/partials/kpi_bar.html", {
        "balance": balance, "portfolio": portfolio, "snap": snap,
        "norm_position": norm_pos, "bot_alive": alive,
    })


def position_badge(request):
    """Position truth badge from exchange."""
    positions = exchange.get_cfm_positions()
    norm_pos = position.normalize_cfm_position(positions[0]) if positions else None
    return _html(request, "trading/partials/position_badge.html", {
        "norm_position": norm_pos,
    })


def thought_feed(request):
    """Latest 10 decisions for thought feed."""
    decisions = file_reader.load_decisions(limit=10)
    return _html(request, "trading/partials/thought_feed.html", {
        "decisions": decisions,
    })


def bot_analytics(request):
    """Bot analytics row: regime, win rate, recovery, quality."""
    snap = file_reader.load_snapshot()
    return _html(request, "trading/partials/bot_analytics.html", {
        "snap": snap,
    })


def trade_log(request):
    """Recent trades table."""
    trades_df = file_reader.load_trades()
    return _html(request, "trading/partials/trade_log.html", {
        "trades_df": trades_df,
    })


def equity_data(request):
    """Equity + price series JSON for chart rendering."""
    series = market.load_equity_series()
    return JsonResponse({"series": series})


def signals_current(request):
    """Current signal badge."""
    snap = file_reader.load_snapshot()
    return _html(request, "trading/partials/signals_current.html", {
        "snap": snap,
    })


def major_events(request):
    """Major events feed."""
    decisions = file_reader.load_decisions(limit=80)
    trades_df = file_reader.load_trades()
    incidents = file_reader.load_incidents()
    cash_moves = file_reader.load_cash_movements()
    evts = events.build_major_events(decisions, trades_df, incidents, cash_moves)
    return _html(request, "trading/partials/events_feed.html", {
        "major_events": evts,
    })


def logs_tail(request):
    """Log tail for System page."""
    log_type = request.GET.get("type", "bot")
    lines = file_reader.tail_log(log_type, n=50)
    return _html(request, "trading/partials/logs_tail.html", {
        "log_lines": lines, "log_type": log_type,
    })
