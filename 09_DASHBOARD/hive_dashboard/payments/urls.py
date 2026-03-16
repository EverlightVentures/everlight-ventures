from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.revenue_dashboard, name="dashboard"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("api/summary/", views.api_revenue_summary, name="api_summary"),
]
