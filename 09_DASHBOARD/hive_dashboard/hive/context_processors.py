from django.utils import timezone
from .models import HiveSession, Agent


def hive_globals(request):
    """Global context available in every template."""
    return {
        'total_sessions': HiveSession.objects.count(),
        'active_agents': Agent.objects.active().count(),
        'now_pt': timezone.now(),
        'app_version': '1.0.0',
        'app_name': 'Hive Mind',
    }
