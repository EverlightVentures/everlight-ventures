from django.views.generic import TemplateView

from trading.services import file_reader, analytics


class SignalsView(TemplateView):
    template_name = "trading/signals/page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "signals"

        # Decisions contain signal data
        ctx["decisions"] = file_reader.load_decisions(limit=300)

        # Trades for quality scoring
        trades_df = file_reader.load_trades()
        ctx["trades_df"] = trades_df

        # Config for gate analysis
        ctx["config"] = file_reader.load_config()

        # Closed trades for parameter performance
        closed = analytics.get_closed_trades(trades_df)
        ctx["closed_trades"] = closed
        ctx["param_perf"] = analytics.parameter_performance(closed)

        # Snapshot for current signal
        ctx["snap"] = file_reader.load_snapshot()

        # Gate pressure (compute pass rates from decisions)
        gate_pressure = []
        gate_names = [
            ("atr_regime", "Volatility"),
            ("session", "Session"),
            ("distance_from_value", "Distance"),
            ("spread", "Spread"),
            ("margin", "Margin"),
            ("cooldown", "Cooldown"),
        ]
        decisions = ctx["decisions"]
        total = len(decisions) if decisions else 0
        for gname, glabel in gate_names:
            if total > 0:
                passes = sum(
                    1 for d in decisions
                    if isinstance(d.get("gates"), dict) and d["gates"].get(gname, True)
                )
                rate = round(passes / total * 100, 1)
            else:
                rate = None
            gate_pressure.append({"name": gname, "label": glabel, "pass_rate": rate})
        ctx["gate_pressure_list"] = gate_pressure

        return ctx
