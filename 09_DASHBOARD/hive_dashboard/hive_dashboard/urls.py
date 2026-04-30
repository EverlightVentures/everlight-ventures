from django.contrib import admin
from django.urls import path, include
from funnel.views import dashboard_landing, hivemind_landing, onyx_landing
from broker_ops import consent_views

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
    path('flip/', include('flip_os.urls', namespace='flip_os')),
    # Public PEWC (TCPA) consent capture -- intentionally at root, no auth.
    path('consent/<str:token>/', consent_views.consent_form, name='consent_form'),
    path('consent/revoke/<str:token>/', consent_views.consent_revoke, name='consent_revoke'),
    path('consent/api/invite/', consent_views.consent_invite_create, name='consent_invite_create'),
    path('', include('hive.urls')),
]
