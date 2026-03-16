from django.views.generic import TemplateView

from trading.services import file_reader


class SystemView(TemplateView):
    template_name = "trading/system/page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_page"] = "system"
        ctx["config"] = file_reader.load_config()
        ctx["snap"] = file_reader.load_snapshot()
        ctx["state"] = file_reader.load_state()
        return ctx
