from django.urls import path
from . import views
from .views import api

app_name = "trading"

urlpatterns = [
    # Pages
    path("", views.TerminalView.as_view(), name="terminal"),
    path("portfolio/", views.PortfolioView.as_view(), name="portfolio"),
    path("signals/", views.SignalsView.as_view(), name="signals"),
    path("ledger/", views.LedgerView.as_view(), name="ledger"),
    path("system/", views.SystemView.as_view(), name="system"),

    # HTMX polling endpoints
    path("api/sidebar-status/", api.sidebar_status, name="api_sidebar_status"),
    path("api/kpi-bar/", api.kpi_bar, name="api_kpi_bar"),
    path("api/position-badge/", api.position_badge, name="api_position_badge"),
    path("api/thought-feed/", api.thought_feed, name="api_thought_feed"),
    path("api/bot-analytics/", api.bot_analytics, name="api_bot_analytics"),
    path("api/trade-log/", api.trade_log, name="api_trade_log"),
    path("api/equity-data/", api.equity_data, name="api_equity_data"),
    path("api/signals-current/", api.signals_current, name="api_signals_current"),
    path("api/major-events/", api.major_events, name="api_major_events"),
    path("api/logs-tail/", api.logs_tail, name="api_logs_tail"),
]
