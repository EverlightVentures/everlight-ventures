from django.urls import path

from . import views

app_name = "business_os"

urlpatterns = [
    path("", views.BusinessOSDashboardView.as_view(), name="dashboard"),
    path("api/snapshot/", views.api_snapshot, name="api_snapshot"),
]

