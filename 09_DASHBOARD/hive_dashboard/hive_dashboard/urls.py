from django.contrib import admin
from django.urls import path, include
from funnel.views import onyx_landing, hivemind_landing

urlpatterns = [
    path('admin/', admin.site.urls),
    path('taskboard/', include('taskboard.urls')),
    path('payments/', include('payments.urls')),
    path('funnel/', include('funnel.urls')),
    path('onyx/', onyx_landing, name='onyx_shortcut'),
    path('hivemind/', hivemind_landing, name='hivemind_shortcut'),
    path('', include('hive.urls')),
]
