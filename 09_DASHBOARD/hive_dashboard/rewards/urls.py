from django.urls import path
from rewards import views

app_name = "rewards"

urlpatterns = [
    # Public API
    path("api/account/<str:email>/", views.api_account, name="api_account"),
    path("api/login/", views.api_daily_login, name="api_daily_login"),
    path("api/referral/apply/", views.api_referral_apply, name="api_referral_apply"),
    path("api/comp/redeem/", views.api_redeem_comp, name="api_redeem_comp"),

    # Referral landing page
    path("join/<str:code>/", views.referral_landing, name="referral_landing"),

    # Staff ops
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/comp/<int:comp_id>/fulfill/", views.admin_fulfill_comp, name="admin_fulfill_comp"),
]
