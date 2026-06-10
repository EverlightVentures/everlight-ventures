"""
Owner Dashboard API
Premium analytics endpoints for business owners
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from datetime import datetime, timedelta
from services.owner_analytics import OwnerAnalytics

dashboard_bp = Blueprint("owner_dashboard", __name__)


def require_owner(f):
    """Decorator to require owner role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        jwt_data = get_jwt()
        if jwt_data.get('role') != 'owner':
            return jsonify({'error': 'Owner access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


@dashboard_bp.route("/executive-summary", methods=["GET"])
@jwt_required()
@require_owner
def get_executive_summary():
    """
    Get complete executive summary for owner homepage
    Shows today's performance, weekly trends, labor status, action items
    """
    try:
        tenant_id = g.tenant_id
        summary = OwnerAnalytics.get_executive_summary(g.db, tenant_id)

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/profit-analysis", methods=["GET"])
@jwt_required()
@require_owner
def get_profit_analysis():
    """
    Get profit margin analysis with FIFO COGS
    Query params: start_date, end_date (ISO format)
    """
    try:
        tenant_id = g.tenant_id

        # Parse date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        analysis = OwnerAnalytics.get_profit_analysis(
            db=g.db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify(analysis), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/top-items", methods=["GET"])
@jwt_required()
@require_owner
def get_top_items():
    """
    Get top performing items by profit margin
    Query params: limit, start_date, end_date
    """
    try:
        tenant_id = g.tenant_id
        limit = int(request.args.get('limit', 10))

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        items = OwnerAnalytics.get_top_items_by_profit(
            db=g.db,
            tenant_id=tenant_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify(items), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/labor-analysis", methods=["GET"])
@jwt_required()
@require_owner
def get_labor_analysis():
    """
    Get labor cost analysis and productivity metrics
    Query params: start_date, end_date
    """
    try:
        tenant_id = g.tenant_id

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        analysis = OwnerAnalytics.get_labor_analysis(
            db=g.db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify(analysis), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/inventory-valuation", methods=["GET"])
@jwt_required()
@require_owner
def get_inventory_valuation():
    """
    Get inventory valuation using FIFO cost basis
    Includes dead stock analysis and turnover rates
    """
    try:
        tenant_id = g.tenant_id

        valuation = OwnerAnalytics.get_inventory_valuation(g.db, tenant_id)

        return jsonify(valuation), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/profit-trend", methods=["GET"])
@jwt_required()
@require_owner
def get_profit_trend():
    """
    Get profit trend over last 30 days (day by day)
    Returns daily revenue, COGS, profit for charting
    """
    try:
        tenant_id = g.tenant_id
        days = int(request.args.get('days', 30))

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Calculate profit for each day
        daily_data = []
        current = start_date

        while current <= end_date:
            day_end = current + timedelta(days=1)

            day_analysis = OwnerAnalytics.get_profit_analysis(
                db=g.db,
                tenant_id=tenant_id,
                start_date=current,
                end_date=day_end
            )

            daily_data.append({
                'date': current.strftime('%Y-%m-%d'),
                'revenue': day_analysis['revenue'],
                'cogs': day_analysis['cogs'],
                'profit': day_analysis['gross_profit'],
                'margin_percent': day_analysis['margin_percent'],
                'transactions': day_analysis['transaction_count']
            })

            current = day_end

        return jsonify({
            'period_days': days,
            'daily_data': daily_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/labor-trend", methods=["GET"])
@jwt_required()
@require_owner
def get_labor_trend():
    """
    Get labor cost % trend over time
    Returns weekly labor cost percentage for charting
    """
    try:
        tenant_id = g.tenant_id
        weeks = int(request.args.get('weeks', 12))

        end_date = datetime.utcnow()
        weekly_data = []

        for i in range(weeks):
            week_end = end_date - timedelta(days=i*7)
            week_start = week_end - timedelta(days=7)

            week_analysis = OwnerAnalytics.get_labor_analysis(
                db=g.db,
                tenant_id=tenant_id,
                start_date=week_start,
                end_date=week_end
            )

            weekly_data.insert(0, {
                'week_ending': week_end.strftime('%Y-%m-%d'),
                'labor_cost_percent': week_analysis['labor_cost_percent'],
                'total_hours': week_analysis['total_hours'],
                'total_cost': week_analysis['total_labor_cost'],
                'revenue': week_analysis['revenue'],
                'status': week_analysis['status']
            })

        return jsonify({
            'weeks': weeks,
            'weekly_data': weekly_data,
            'target_range': '25-30%'
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
