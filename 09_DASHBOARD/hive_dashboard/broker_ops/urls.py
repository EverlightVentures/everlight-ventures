from django.urls import path
from . import views

app_name = "broker_ops"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Ingest APIs (called by pipeline scripts)
    path("api/ingest/lead/",  views.api_ingest_lead,  name="api_ingest_lead"),
    path("api/ingest/offer/", views.api_ingest_offer, name="api_ingest_offer"),

    # Matching
    path("api/match/run/",                     views.api_run_matching,   name="api_run_matching"),
    path("api/match/<uuid:match_id>/approve/", views.api_approve_match,  name="api_approve_match"),

    # Deals
    path("api/deal/<uuid:deal_id>/close/",    views.api_close_deal,         name="api_close_deal"),
    path("api/deal/<uuid:deal_id>/contract/", views.api_generate_contract,  name="api_generate_contract"),

    # Stripe payment integration
    path("api/deal/<uuid:deal_id>/invoice/",        views.api_create_invoice,  name="api_create_invoice"),
    path("api/deal/<uuid:deal_id>/checkout/",       views.api_create_checkout, name="api_create_checkout"),
    path("api/deal/<uuid:deal_id>/payment-status/", views.api_check_payment,   name="api_check_payment"),
    path("webhook/stripe/",                         views.stripe_webhook,      name="stripe_webhook"),

    # Reporting
    path("api/commissions/", views.api_commission_summary, name="api_commission_summary"),

    # Public endpoints (no auth - for Lovable site forms)
    path("api/public/lead/",  views.public_submit_lead,  name="public_submit_lead"),
    path("api/public/offer/", views.public_submit_offer, name="public_submit_offer"),
]
