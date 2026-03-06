from django.views.generic import TemplateView

from trading.services import file_reader, events


class LedgerView(TemplateView):
    template_name = "trading/ledger/page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "ledger"

        decisions = file_reader.load_decisions(limit=300)
        trades_df = file_reader.load_trades()
        incidents = file_reader.load_incidents()
        cash_moves = file_reader.load_cash_movements()

        ctx["major_events"] = events.build_major_events(
            decisions, trades_df, incidents, cash_moves
        )
        ctx["trades_df"] = trades_df
        ctx["cash_movements"] = cash_moves

        # Convert trades DataFrame to list of dicts for template iteration
        if trades_df is not None and not trades_df.empty:
            ctx["trades_list"] = trades_df.to_dict("records")[::-1]  # newest first
        else:
            ctx["trades_list"] = []

        # Market news: JSONL may contain full market-brief objects with nested
        # headlines, or individual news items.  Flatten to a list of items that
        # each have at least a headline/title.
        raw_news = file_reader.load_market_news()
        news_items = []
        for item in raw_news:
            if "headline" in item or "title" in item:
                news_items.append(item)
            elif "headlines" in item and isinstance(item["headlines"], list):
                for h in item["headlines"]:
                    if isinstance(h, dict):
                        news_items.append(h)
        ctx["market_news"] = news_items

        return ctx
