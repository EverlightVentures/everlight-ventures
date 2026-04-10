from django.apps import AppConfig


class BrokerOpsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "broker_ops"
    verbose_name = "Broker OS"

    def ready(self):
        import broker_ops.signals  # noqa: F401 -- register signal handlers
