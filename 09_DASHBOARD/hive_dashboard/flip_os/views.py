"""
Flip OS -- Django Views
Dashboard, inventory management, intel feed, and API endpoints.
"""
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from hive_dashboard.supabase_client import supabase_rest, supabase_rest_rows

logger = logging.getLogger(__name__)

STORAGE_RENT = 60.00


# ---------------------------------------------------------------------------
# DASHBOARD -- Main overview
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def dashboard(request):
    today = date.today()
    first_of_month = today.replace(day=1)

    # Fetch data from Supabase
    intel_recent = supabase_rest_rows("flip_intel", {
        "select": "*",
        "order": "found_date.desc",
        "limit": "20",
    })

    inventory = supabase_rest_rows("flip_inventory", {
        "select": "*",
        "order": "created_at.desc",
    })

    sold_month = [i for i in inventory if i.get("status") == "sold"
                  and i.get("sold_date", "") >= first_of_month.isoformat()]
    in_storage = [i for i in inventory if i.get("status") == "in_storage"]
    listed = [i for i in inventory if i.get("status") == "listed"]

    # P&L
    total_revenue = sum(float(s.get("sold_price") or 0) for s in sold_month)
    total_cost = sum(float(s.get("buy_price") or 0) for s in sold_month)
    total_profit = sum(float(s.get("net_profit") or 0) for s in sold_month)
    net_after_rent = total_profit - STORAGE_RENT
    inventory_value = sum(float(i.get("est_sell_price") or 0) for i in in_storage)

    # GO items
    go_items = [i for i in intel_recent
                if i.get("demand_score", 0) >= 70
                and float(i.get("est_resale") or 0) >= 20
                and not i.get("acted_on")]

    # Stale items
    stale = []
    for item in in_storage:
        bd = item.get("buy_date")
        if bd:
            days = (today - date.fromisoformat(bd)).days
            if days > 14:
                stale.append({**item, "days_held": days})

    # Latest brief
    briefs = supabase_rest_rows("flip_daily_brief", {
        "select": "*",
        "order": "brief_date.desc",
        "limit": "1",
    })
    latest_brief = briefs[0] if briefs else None

    context = {
        "intel_recent": intel_recent[:10],
        "go_items": go_items,
        "in_storage": in_storage,
        "listed": listed,
        "sold_month": sold_month,
        "stale": stale,
        "stats": {
            "items_in_storage": len(in_storage),
            "items_listed": len(listed),
            "items_sold": len(sold_month),
            "inventory_value": inventory_value,
            "revenue": total_revenue,
            "cost": total_cost,
            "profit": total_profit,
            "rent": STORAGE_RENT,
            "net": net_after_rent,
        },
        "latest_brief": latest_brief,
    }
    return render(request, "flip_os/dashboard.html", context)


# ---------------------------------------------------------------------------
# INTEL LIST -- All scraped items
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def intel_list(request):
    items = supabase_rest_rows("flip_intel", {
        "select": "*",
        "order": "demand_score.desc,found_date.desc",
        "limit": "100",
    })
    return render(request, "flip_os/intel_list.html", {"items": items})


# ---------------------------------------------------------------------------
# INVENTORY LIST
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def inventory_list(request):
    status_filter = request.GET.get("status", "")
    params = {"select": "*", "order": "created_at.desc", "limit": "200"}
    if status_filter:
        params["status"] = f"eq.{status_filter}"
    items = supabase_rest_rows("flip_inventory", params)
    return render(request, "flip_os/inventory_list.html", {
        "items": items, "status_filter": status_filter,
    })


# ---------------------------------------------------------------------------
# INVENTORY ADD
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def inventory_add(request):
    if request.method == "POST":
        row = {
            "item_name": request.POST.get("item_name", "").strip(),
            "item_sku": request.POST.get("item_sku", "").strip() or None,
            "category": request.POST.get("category", "unknown"),
            "condition": request.POST.get("condition", "new"),
            "buy_price": float(request.POST.get("buy_price", "0.01")),
            "buy_source": request.POST.get("buy_source", "home_depot"),
            "buy_date": request.POST.get("buy_date", date.today().isoformat()),
            "est_sell_price": float(request.POST.get("est_sell_price", "0") or "0"),
            "storage_location": request.POST.get("storage_location", "unit_a"),
            "notes": request.POST.get("notes", "").strip() or None,
            "status": "in_storage",
        }
        # Link to intel if provided
        intel_id = request.POST.get("intel_id")
        if intel_id:
            row["intel_id"] = int(intel_id)

        try:
            supabase_rest("flip_inventory", method="POST", data=row)
            return redirect("flip_os:dashboard")
        except Exception as e:
            logger.error("Failed to add inventory item: %s", e)
            return render(request, "flip_os/inventory_add.html", {"error": str(e), "form": row})

    # Pre-fill from intel item if ?intel_id=N
    prefill = {}
    intel_id = request.GET.get("intel_id")
    if intel_id:
        intel = supabase_rest_rows("flip_intel", {"select": "*", "id": f"eq.{intel_id}"})
        if intel:
            i = intel[0]
            prefill = {
                "intel_id": i["id"],
                "item_name": i.get("item_name", ""),
                "item_sku": i.get("item_sku", ""),
                "category": i.get("category", "unknown"),
                "buy_price": "0.01" if i.get("penny_confirmed") else str(i.get("clearance_price") or "0.01"),
                "est_sell_price": str(i.get("est_resale") or ""),
            }

    return render(request, "flip_os/inventory_add.html", {"form": prefill})


# ---------------------------------------------------------------------------
# INVENTORY EDIT
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def inventory_edit(request, item_id):
    items = supabase_rest_rows("flip_inventory", {"select": "*", "id": f"eq.{item_id}"})
    if not items:
        return redirect("flip_os:inventory_list")
    item = items[0]

    if request.method == "POST":
        updates = {
            "item_name": request.POST.get("item_name", item["item_name"]),
            "category": request.POST.get("category", item.get("category")),
            "est_sell_price": float(request.POST.get("est_sell_price") or 0),
            "listed_price": float(request.POST.get("listed_price") or 0) or None,
            "status": request.POST.get("status", item["status"]),
            "storage_location": request.POST.get("storage_location", item.get("storage_location")),
            "notes": request.POST.get("notes", ""),
        }
        # If status changed to listed, set listed_date
        if updates["status"] == "listed" and item["status"] != "listed":
            updates["listed_date"] = date.today().isoformat()
            listed_on = request.POST.getlist("listed_on")
            if listed_on:
                updates["listed_on"] = listed_on

        try:
            supabase_rest("flip_inventory", method="PATCH",
                          data=updates, params={"id": f"eq.{item_id}"})
            return redirect("flip_os:dashboard")
        except Exception as e:
            logger.error("Failed to update item %d: %s", item_id, e)

    return render(request, "flip_os/inventory_edit.html", {"item": item})


# ---------------------------------------------------------------------------
# MARK SOLD
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
@csrf_exempt
def inventory_mark_sold(request, item_id):
    if request.method == "POST":
        sold_price = float(request.POST.get("sold_price", 0))
        sold_platform = request.POST.get("sold_platform", "fb_marketplace")
        shipping = float(request.POST.get("shipping_cost", 0) or 0)
        fees = float(request.POST.get("fees", 0) or 0)

        updates = {
            "status": "sold",
            "sold_price": sold_price,
            "sold_date": date.today().isoformat(),
            "sold_platform": sold_platform,
            "shipping_cost": shipping,
            "fees": fees,
        }
        try:
            supabase_rest("flip_inventory", method="PATCH",
                          data=updates, params={"id": f"eq.{item_id}"})
        except Exception as e:
            logger.error("Failed to mark sold %d: %s", item_id, e)

    return redirect("flip_os:dashboard")


# ---------------------------------------------------------------------------
# LATEST BRIEF
# ---------------------------------------------------------------------------

@login_required
@staff_member_required
def latest_brief(request):
    briefs = supabase_rest_rows("flip_daily_brief", {
        "select": "*",
        "order": "brief_date.desc",
        "limit": "7",
    })
    return render(request, "flip_os/brief.html", {"briefs": briefs})


# ---------------------------------------------------------------------------
# JSON APIs (for React dashboard / mobile)
# ---------------------------------------------------------------------------

@require_GET
def api_intel(request):
    items = supabase_rest_rows("flip_intel", {
        "select": "*",
        "order": "demand_score.desc",
        "limit": request.GET.get("limit", "50"),
    })
    return JsonResponse({"items": items}, safe=False)

@require_GET
def api_inventory(request):
    params = {"select": "*", "order": "created_at.desc", "limit": "200"}
    status = request.GET.get("status")
    if status:
        params["status"] = f"eq.{status}"
    items = supabase_rest_rows("flip_inventory", params)
    return JsonResponse({"items": items}, safe=False)

@require_GET
def api_stats(request):
    today = date.today()
    first_of_month = today.replace(day=1)
    inventory = supabase_rest_rows("flip_inventory", {"select": "*"})

    sold = [i for i in inventory if i.get("status") == "sold"
            and i.get("sold_date", "") >= first_of_month.isoformat()]
    in_storage = [i for i in inventory if i.get("status") == "in_storage"]
    listed = [i for i in inventory if i.get("status") == "listed"]

    return JsonResponse({
        "in_storage": len(in_storage),
        "listed": len(listed),
        "sold_this_month": len(sold),
        "inventory_value": sum(float(i.get("est_sell_price") or 0) for i in in_storage),
        "revenue_this_month": sum(float(s.get("sold_price") or 0) for s in sold),
        "profit_this_month": sum(float(s.get("net_profit") or 0) for s in sold),
        "net_after_rent": sum(float(s.get("net_profit") or 0) for s in sold) - STORAGE_RENT,
    })
