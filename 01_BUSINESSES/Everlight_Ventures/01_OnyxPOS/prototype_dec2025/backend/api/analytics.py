"""
Analytics API
- Dashboard metrics
- Sales trends
- Inventory analytics
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models import Transaction, TransactionItem, Item
from sqlalchemy import func
from datetime import datetime, timedelta

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard_metrics():
    """
    Get dashboard metrics for today and MTD
    """
    try:
        tenant_id = g.tenant_id
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Today's sales
        today_sales = g.db.query(
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.total_amount).label("revenue")
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_date >= today_start,
            Transaction.payment_status == "completed"
        ).first()

        # Month-to-date sales
        mtd_sales = g.db.query(
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.total_amount).label("revenue")
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_date >= month_start,
            Transaction.payment_status == "completed"
        ).first()

        # Low stock count
        low_stock_count = g.db.query(Item).filter(
            Item.tenant_id == tenant_id,
            Item.is_active == True,
            Item.stock_on_hand <= Item.reorder_point
        ).count()

        # Total inventory value
        inventory_value = g.db.query(
            func.sum(Item.stock_on_hand * Item.sell_price)
        ).filter(
            Item.tenant_id == tenant_id,
            Item.is_active == True
        ).scalar()

        return jsonify({
            "today": {
                "revenue": float(today_sales.revenue or 0),
                "transaction_count": today_sales.count or 0
            },
            "month_to_date": {
                "revenue": float(mtd_sales.revenue or 0),
                "transaction_count": mtd_sales.count or 0
            },
            "inventory": {
                "low_stock_count": low_stock_count,
                "total_value": float(inventory_value or 0)
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/sales-trend", methods=["GET"])
@jwt_required()
def sales_trend():
    """
    Get sales trend for last N days
    """
    try:
        tenant_id = g.tenant_id
        days = request.args.get("days", 30, type=int)

        start_date = datetime.utcnow() - timedelta(days=days)

        # Daily sales grouped by date
        daily_sales = g.db.query(
            func.date(Transaction.transaction_date).label("date"),
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.total_amount).label("revenue")
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_date >= start_date,
            Transaction.payment_status == "completed"
        ).group_by(
            func.date(Transaction.transaction_date)
        ).order_by(
            func.date(Transaction.transaction_date)
        ).all()

        return jsonify({
            "trend": [{
                "date": str(day.date),
                "revenue": float(day.revenue or 0),
                "transaction_count": day.count or 0
            } for day in daily_sales]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/top-selling", methods=["GET"])
@jwt_required()
def top_selling():
    """
    Get top selling items
    """
    try:
        tenant_id = g.tenant_id
        limit = request.args.get("limit", 10, type=int)
        days = request.args.get("days", 30, type=int)

        start_date = datetime.utcnow() - timedelta(days=days)

        # Top selling items
        top_items = g.db.query(
            TransactionItem.item_name,
            func.sum(TransactionItem.quantity).label("total_quantity"),
            func.sum(TransactionItem.line_total).label("total_revenue")
        ).join(
            Transaction
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_date >= start_date,
            Transaction.payment_status == "completed"
        ).group_by(
            TransactionItem.item_name
        ).order_by(
            func.sum(TransactionItem.quantity).desc()
        ).limit(limit).all()

        return jsonify({
            "top_selling": [{
                "item_name": item.item_name,
                "quantity_sold": int(item.total_quantity),
                "revenue": float(item.total_revenue)
            } for item in top_items]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
