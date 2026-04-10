from django.urls import path
from . import views

app_name = "flip_os"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("intel/", views.intel_list, name="intel_list"),
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/add/", views.inventory_add, name="inventory_add"),
    path("inventory/<int:item_id>/edit/", views.inventory_edit, name="inventory_edit"),
    path("inventory/<int:item_id>/sell/", views.inventory_mark_sold, name="inventory_mark_sold"),
    path("brief/", views.latest_brief, name="latest_brief"),
    path("api/intel/", views.api_intel, name="api_intel"),
    path("api/inventory/", views.api_inventory, name="api_inventory"),
    path("api/stats/", views.api_stats, name="api_stats"),
]
