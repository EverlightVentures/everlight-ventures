from django.urls import path
from . import views

app_name = 'blackjack'

urlpatterns = [
    # Game
    path('', views.game_view, name='game'),
    path('auth/', views.register_view, name='auth'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),

    # OAuth providers
    path('oauth/google/', views.google_login, name='google_login'),
    path('oauth/google/callback/', views.google_callback, name='google_callback'),
    path('oauth/facebook/', views.facebook_login, name='facebook_login'),
    path('oauth/facebook/callback/', views.facebook_callback, name='facebook_callback'),

    # API
    path('api/profile/', views.api_profile, name='api_profile'),
    path('api/deal/', views.api_deal, name='api_deal'),
    path('api/action/', views.api_action, name='api_action'),
    path('api/result/', views.api_result, name='api_result'),
    path('api/ad-reward/', views.api_ad_reward, name='api_ad_reward'),
    path('api/avatar/', views.api_update_avatar, name='api_avatar'),
    path('api/shop/', views.api_shop_items, name='api_shop'),
    path('api/purchase/', views.api_purchase_cosmetic, name='api_purchase'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
    path('api/history/', views.api_history, name='api_history'),
]
