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
    path("api/public/lead/",          views.public_submit_lead,           name="public_submit_lead"),
    path("api/public/offer/",         views.public_submit_offer,          name="public_submit_offer"),
    path("api/public/property-lead/", views.public_submit_property_lead,  name="public_submit_property_lead"),

    # Wholesale pipeline
    path("wholesale/",                              views.wholesale_dashboard,    name="wholesale_dashboard"),
    path("api/import-leads/",                       views.api_import_leads,       name="api_import_leads"),
    path("api/score-lead/<uuid:lead_id>/",          views.api_score_lead,         name="api_score_lead"),
    path("api/match-buyers/<uuid:lead_id>/",        views.api_match_buyers,       name="api_match_buyers"),
    path("api/outreach/<uuid:lead_id>/",            views.api_generate_outreach,  name="api_generate_outreach"),
    path("api/piper-outreach/<uuid:lead_id>/",      views.api_piper_outreach,     name="api_piper_outreach"),

    # Event webhooks (called by n8n, Gmail monitor, external systems)
    path("webhook/email-reply/",                    views.webhook_email_reply,     name="webhook_email_reply"),
    path("webhook/deal-advance/",                   views.webhook_deal_advance,    name="webhook_deal_advance"),
    path("webhook/event/",                          views.webhook_event_trigger,   name="webhook_event_trigger"),

    # Deal pipeline stage APIs
    path("api/deal/<uuid:deal_id>/history/",        views.api_deal_history,        name="api_deal_history"),

    # Public: investor buyer signup (no auth)
    path("investor-signup/",                        views.public_investor_signup,  name="public_investor_signup"),

    # Client Files: A-to-Z deal document management
    path("client-files/",                                      views.client_files_dashboard,         name="client_files"),
    path("client-files/<uuid:file_id>/",                       views.client_file_detail,             name="client_file_detail"),
    path("client-files/doc/<uuid:doc_id>/preview/",            views.client_file_document_preview,   name="client_doc_preview"),
    path("api/client-file/create/<uuid:lead_id>/",             views.api_create_client_file,         name="api_create_client_file"),
    path("api/client-file/<uuid:file_id>/document/",           views.api_generate_document,          name="api_generate_document"),
    path("api/client-file/<uuid:file_id>/status/",             views.api_update_client_file_status,  name="api_update_client_file_status"),
]
