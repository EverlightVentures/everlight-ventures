from django.views.generic import TemplateView

from trading.services import file_reader, exchange, formatters, events, position, market


def _is_htmx(request):
    return getattr(request, "htmx", False)


class TerminalView(TemplateView):
    template_name = "trading/terminal/page.html"

    _tab_templates = {
        "overview": "trading/terminal/overview.html",
        "intel": "trading/terminal/intel_hub.html",
        "chat": "trading/terminal/chat.html",
        "evolution": "trading/terminal/evolution.html",
    }

    def get_template_names(self):
        tab = self.request.GET.get("tab", "overview")
        if _is_htmx(self.request) and tab in self._tab_templates:
            return [self._tab_templates[tab]]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "terminal"
        ctx["active_tab"] = self.request.GET.get("tab", "overview")

        # Load snapshot + state
        snap = file_reader.load_snapshot()
        state = file_reader.load_state()
        cfg = file_reader.load_config()
        ctx["snap"] = snap
        ctx["state"] = state
        ctx["config"] = cfg

        # Decisions (latest 80)
        ctx["decisions"] = file_reader.load_decisions(limit=80)

        # Trades today
        trades_df = file_reader.load_trades()
        ctx["trades_df"] = trades_df

        # Exchange data
        ctx["balance"] = exchange.get_futures_balance()
        ctx["positions"] = exchange.get_cfm_positions()
        ctx["portfolio"] = exchange.get_portfolio_breakdown()
        ctx["open_orders"] = exchange.get_cfm_open_orders()

        # AI data
        ctx["ai_insight"] = file_reader.load_json_file("ai_insight.json", data_dir=True)
        ctx["market_brief"] = file_reader.load_json_file("market_brief.json", data_dir=True)

        # Build major events
        incidents = file_reader.load_incidents()
        cash_moves = file_reader.load_cash_movements()
        ctx["major_events"] = events.build_major_events(
            ctx["decisions"], trades_df, incidents, cash_moves
        )

        # Position normalization
        if ctx["positions"]:
            ctx["norm_position"] = position.normalize_cfm_position(ctx["positions"][0])
        else:
            ctx["norm_position"] = None

        # Operator metrics
        ctx["op_metrics"] = market.operator_metrics(ctx["decisions"], trades_df, cfg)

        return ctx
