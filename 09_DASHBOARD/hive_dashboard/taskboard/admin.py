from django.contrib import admin
from .models import TaskTemplate, TaskItem


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "icon", "created_at"]
    list_filter = ["category"]
    search_fields = ["name"]


@admin.register(TaskItem)
class TaskItemAdmin(admin.ModelAdmin):
    list_display = ["title", "template", "status", "priority", "source_agent", "target_agent", "created_at"]
    list_filter = ["status", "priority", "template__category"]
    search_fields = ["title", "batch_id"]
