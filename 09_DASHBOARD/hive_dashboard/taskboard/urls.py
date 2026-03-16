from django.urls import path
from . import views

app_name = "taskboard"

urlpatterns = [
    # Dashboard
    path("", views.board, name="board"),
    path("nerve-center/", views.nerve_center, name="nerve_center"),

    # Task actions
    path("task/<int:task_id>/", views.task_form, name="task_form"),
    path("task/<int:task_id>/submit/", views.task_submit, name="task_submit"),
    path("task/<int:task_id>/skip/", views.task_skip, name="task_skip"),
    path("task/<int:task_id>/block/", views.task_block, name="task_block"),

    # AI API endpoints
    path("api/create/", views.api_create_tasks, name="api_create"),
    path("api/completed/", views.api_retrieve_completed, name="api_completed"),
    path("api/status/", views.api_status, name="api_status"),
]
