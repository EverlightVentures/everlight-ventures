from django.contrib import admin
from django.urls import path, include
from funnel.views import dashboard_landing, hivemind_landing, onyx_landing

urlpatterns = [
    path('admin/', admin.site.urls),
    path('os/', include('business_os.urls')),
    path('taskboard/', include('taskboard.urls')),
    path('payments/', include('payments.urls')),
    path('funnel/', include('funnel.urls')),
    path('onyx/', onyx_landing, name='onyx_shortcut'),
    path('hivemind/', hivemind_landing, name='hivemind_shortcut'),
    path('dashboard/', dashboard_landing, name='dashboard_shortcut'),
    path('blackjack/', include('blackjack.urls', namespace='blackjack')),
    path('rewards/', include('rewards.urls', namespace='rewards')),
    path('broker/', include('broker_ops.urls', namespace='broker_ops')),
    path('', include('hive.urls')),
]
