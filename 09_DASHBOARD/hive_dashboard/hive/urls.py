"""
Hive Mind Dashboard - URL Configuration
"""
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'hive'

urlpatterns = [
    # Pages
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('sessions/', views.SessionListView.as_view(), name='sessions'),
    path(
        'sessions/<str:session_id>/',
        views.SessionDetailView.as_view(),
        name='session_detail',
    ),
    path('agents/', views.AgentListView.as_view(), name='agents'),
    path(
        'agents/<int:pk>/',
        views.AgentDetailView.as_view(),
        name='agent_detail',
    ),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('launch/', csrf_exempt(views.LaunchQueryView.as_view()), name='launch'),
    path('events/', views.EventsView.as_view(), name='events'),

    # API / AJAX endpoints
    path(
        'api/session/<str:session_id>/status/',
        views.api_session_status,
        name='api_session_status',
    ),
    path('api/live-feed/', views.api_live_feed, name='api_live_feed'),
    path(
        'api/poll/<str:session_id>/',
        views.api_poll_session,
        name='api_poll_session',
    ),
    path(
        'api/session/<str:session_id>/export/',
        views.api_export_session,
        name='api_export_session',
    ),
    path('api/bot-intel/', views.api_bot_intel, name='api_bot_intel'),
    path(
        'api/upload-analyze/',
        csrf_exempt(views.api_upload_analyze),
        name='api_upload_analyze',
    ),
]
