from django.views.generic import TemplateView

from trading.services import file_reader, exchange, market


class PortfolioView(TemplateView):
    template_name = "trading/portfolio/page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "portfolio"

        # Account data
        balance = exchange.get_futures_balance()
        portfolio_raw = exchange.get_portfolio_breakdown()
        spot_raw = exchange.get_spot_balances()
        ctx["balance"] = balance
        ctx["positions"] = exchange.get_cfm_positions()

        # Normalize portfolio keys for template
        ctx["portfolio"] = {
            "total_balance": portfolio_raw.get("total", 0),
            "cash_total": portfolio_raw.get("cash", 0),
            "crypto_total": portfolio_raw.get("crypto", 0),
            "futures_total": portfolio_raw.get("futures", 0),
            "usd_balance": spot_raw.get("USD", 0),
            "usdc_balance": spot_raw.get("USDC", 0),
        }

        # Normalize spot balances for template
        usd = spot_raw.get("USD", 0)
        usdc = spot_raw.get("USDC", 0)
        ctx["spot_balances"] = {
            "usd": usd,
            "usdc": usdc,
            "total": usd + usdc,
            "daily_yield": usdc * 0.035 / 365,
        } if spot_raw else {}

        # Cash movements
        ctx["cash_movements"] = file_reader.load_cash_movements()

        # Equity series for charts
        ctx["equity_series"] = market.load_equity_series()

        # Trades for P&L chart
        ctx["trades_df"] = file_reader.load_trades()

        return ctx
