from django.urls import path
from . import views

app_name = "funnel"

urlpatterns = [
    path("consulting/", views.consulting_landing, name="consulting_landing"),
    path("onyx/", views.onyx_landing, name="onyx_landing"),
    path("hivemind/", views.hivemind_landing, name="hivemind_landing"),
    path("dashboard/", views.dashboard_landing, name="dashboard_landing"),
    path("capture/", views.capture_lead, name="capture_lead"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("stats/", views.funnel_stats, name="stats"),
]
