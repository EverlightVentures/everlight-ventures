from django.urls import path
from . import views

app_name = "funnel"

urlpatterns = [
    path("onyx/", views.onyx_landing, name="onyx_landing"),
    path("hivemind/", views.hivemind_landing, name="hivemind_landing"),
    path("capture/", views.capture_lead, name="capture_lead"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("stats/", views.funnel_stats, name="stats"),
]
