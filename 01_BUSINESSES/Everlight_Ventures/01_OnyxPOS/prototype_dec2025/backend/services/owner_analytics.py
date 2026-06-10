"""
Owner Intelligence Analytics Service
Premium dashboards for business owners - profit, labor, inventory insights
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from models import Transaction, TransactionItem, Item, User, Tenant, TimeClockEntry
from models_inventory_advanced import InventoryLot, TransactionItemLot
from decimal import Decimal


class OwnerAnalytics:
    """Premium analytics for owner-tier users"""

    @staticmethod
    def get_profit_analysis(db, tenant_id, start_date=None, end_date=None):
        """
        Calculate profit margins using FIFO COGS
        Returns revenue, COGS, gross profit, margin %
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get all transactions in period
        transactions = db.query(Transaction).filter(
            and_(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.payment_status == 'completed'
            )
        ).all()

        total_revenue = sum(float(t.total_amount) for t in transactions)
        total_cogs = 0
        transaction_count = len(transactions)

        # Calculate COGS from transaction items
        for txn in transactions:
            items = db.query(TransactionItem).filter_by(transaction_id=txn.id).all()
            for item in items:
                # Use FIFO-calculated cost if available, otherwise unit_cost
                item_cogs = float(item.unit_cost or 0) * item.quantity
                total_cogs += item_cogs

        gross_profit = total_revenue - total_cogs
        margin_percent = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'revenue': round(total_revenue, 2),
            'cogs': round(total_cogs, 2),
            'gross_profit': round(gross_profit, 2),
            'margin_percent': round(margin_percent, 2),
            'transaction_count': transaction_count,
            'avg_transaction': round(total_revenue / transaction_count, 2) if transaction_count > 0 else 0
        }

    @staticmethod
    def get_top_items_by_profit(db, tenant_id, limit=10, start_date=None, end_date=None):
        """
        Get top/bottom items by profit margin
        Uses FIFO COGS for accurate margins
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get all transaction items in period
        txn_items = db.query(TransactionItem).join(Transaction).filter(
            and_(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.payment_status == 'completed'
            )
        ).all()

        # Aggregate by item
        item_stats = {}
        for txn_item in txn_items:
            item_id = txn_item.item_id
            if item_id not in item_stats:
                item_stats[item_id] = {
                    'item_id': item_id,
                    'sku': txn_item.sku,
                    'name': txn_item.item_name,
                    'quantity_sold': 0,
                    'revenue': 0,
                    'cogs': 0
                }

            revenue = float(txn_item.line_total)
            cogs = float(txn_item.unit_cost or 0) * txn_item.quantity

            item_stats[item_id]['quantity_sold'] += txn_item.quantity
            item_stats[item_id]['revenue'] += revenue
            item_stats[item_id]['cogs'] += cogs

        # Calculate margins and sort
        items_with_margin = []
        for stats in item_stats.values():
            profit = stats['revenue'] - stats['cogs']
            margin = (profit / stats['revenue'] * 100) if stats['revenue'] > 0 else 0

            items_with_margin.append({
                **stats,
                'profit': round(profit, 2),
                'margin_percent': round(margin, 2),
                'revenue': round(stats['revenue'], 2),
                'cogs': round(stats['cogs'], 2)
            })

        # Sort by profit descending
        items_with_margin.sort(key=lambda x: x['profit'], reverse=True)

        return {
            'top_performers': items_with_margin[:limit],
            'bottom_performers': items_with_margin[-limit:] if len(items_with_margin) > limit else []
        }

    @staticmethod
    def get_labor_analysis(db, tenant_id, start_date=None, end_date=None):
        """
        Calculate labor costs and productivity metrics
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get all time clock entries in period
        time_entries = db.query(TimeClockEntry).join(User).filter(
            and_(
                User.tenant_id == tenant_id,
                TimeClockEntry.clock_in >= start_date,
                TimeClockEntry.clock_in <= end_date,
                TimeClockEntry.clock_out.isnot(None)
            )
        ).all()

        total_hours = 0
        total_labor_cost = 0
        overtime_hours = 0
        overtime_cost = 0
        employee_stats = {}

        for entry in time_entries:
            user = db.query(User).filter_by(id=entry.user_id).first()
            if not user:
                continue

            # Calculate hours from clock_in and clock_out
            if entry.clock_in and entry.clock_out:
                time_diff = entry.clock_out - entry.clock_in
                hours = time_diff.total_seconds() / 3600
                # Subtract break time if any
                break_hours = float(entry.break_minutes or 0) / 60
                hours = max(0, hours - break_hours)
            else:
                hours = 0

            regular_rate = float(user.hourly_rate or 0)

            # Calculate regular vs overtime
            if hours > 40:
                reg_hours = 40
                ot_hours = hours - 40
            else:
                reg_hours = hours
                ot_hours = 0

            reg_cost = reg_hours * regular_rate
            ot_cost = ot_hours * regular_rate * 1.5

            total_hours += hours
            total_labor_cost += (reg_cost + ot_cost)
            overtime_hours += ot_hours
            overtime_cost += ot_cost

            # Track per employee
            if user.id not in employee_stats:
                employee_stats[user.id] = {
                    'employee_id': user.id,
                    'name': user.full_name,
                    'hours': 0,
                    'cost': 0,
                    'overtime_hours': 0
                }

            employee_stats[user.id]['hours'] += hours
            employee_stats[user.id]['cost'] += (reg_cost + ot_cost)
            employee_stats[user.id]['overtime_hours'] += ot_hours

        # Get revenue for same period
        revenue_query = db.query(func.sum(Transaction.total_amount)).filter(
            and_(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.payment_status == 'completed'
            )
        ).scalar()

        total_revenue = float(revenue_query or 0)
        labor_cost_percent = (total_labor_cost / total_revenue * 100) if total_revenue > 0 else 0

        # Format employee stats
        employees = [
            {
                **stats,
                'hours': round(stats['hours'], 2),
                'cost': round(stats['cost'], 2),
                'overtime_hours': round(stats['overtime_hours'], 2),
                'cost_per_hour': round(stats['cost'] / stats['hours'], 2) if stats['hours'] > 0 else 0
            }
            for stats in employee_stats.values()
        ]
        employees.sort(key=lambda x: x['cost'], reverse=True)

        # Determine status
        if labor_cost_percent < 25:
            status = 'excellent'
            message = 'Labor cost is well optimized'
        elif labor_cost_percent < 30:
            status = 'good'
            message = 'Labor cost is within industry standards'
        elif labor_cost_percent < 35:
            status = 'warning'
            message = 'Labor cost is high - consider optimization'
        else:
            status = 'critical'
            message = 'Labor cost is critically high - immediate action needed'

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'total_hours': round(total_hours, 2),
            'total_labor_cost': round(total_labor_cost, 2),
            'overtime_hours': round(overtime_hours, 2),
            'overtime_cost': round(overtime_cost, 2),
            'revenue': round(total_revenue, 2),
            'labor_cost_percent': round(labor_cost_percent, 2),
            'status': status,
            'message': message,
            'target_range': '25-30%',
            'employees': employees,
            'avg_hourly_cost': round(total_labor_cost / total_hours, 2) if total_hours > 0 else 0,
            'revenue_per_labor_hour': round(total_revenue / total_hours, 2) if total_hours > 0 else 0
        }

    @staticmethod
    def get_inventory_valuation(db, tenant_id):
        """
        Calculate total inventory value using FIFO cost basis
        Identify dead stock and turnover rates
        """
        # Get all items with current stock
        items = db.query(Item).filter(
            and_(
                Item.tenant_id == tenant_id,
                Item.is_active == True
            )
        ).all()

        total_value = 0
        total_quantity = 0
        items_data = []

        for item in items:
            # Get FIFO lots for this item
            lots = db.query(InventoryLot).filter(
                and_(
                    InventoryLot.tenant_id == tenant_id,
                    InventoryLot.item_id == item.id,
                    InventoryLot.quantity > 0
                )
            ).all()

            item_value = sum(lot.quantity * float(lot.cost_per_unit) for lot in lots)
            item_quantity = sum(lot.quantity for lot in lots)

            # Get sales in last 90 days
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            sales_query = db.query(func.sum(TransactionItem.quantity)).join(Transaction).filter(
                and_(
                    TransactionItem.item_id == item.id,
                    Transaction.tenant_id == tenant_id,
                    Transaction.transaction_date >= ninety_days_ago,
                    Transaction.payment_status == 'completed'
                )
            ).scalar()

            quantity_sold_90d = int(sales_query or 0)

            # Calculate turnover (how many times inventory sold in 90 days)
            turnover = (quantity_sold_90d / item_quantity) if item_quantity > 0 else 0

            # Days of inventory remaining
            daily_sales = quantity_sold_90d / 90 if quantity_sold_90d > 0 else 0
            days_remaining = (item_quantity / daily_sales) if daily_sales > 0 else 999

            items_data.append({
                'item_id': item.id,
                'sku': item.sku,
                'name': item.name,
                'quantity': item_quantity,
                'value': round(item_value, 2),
                'avg_cost': round(item_value / item_quantity, 2) if item_quantity > 0 else 0,
                'sold_90d': quantity_sold_90d,
                'turnover_rate': round(turnover, 2),
                'days_remaining': int(days_remaining) if days_remaining < 999 else None,
                'status': 'dead' if quantity_sold_90d == 0 else 'slow' if turnover < 1 else 'active'
            })

            total_value += item_value
            total_quantity += item_quantity

        # Sort for insights
        dead_stock = [i for i in items_data if i['status'] == 'dead']
        slow_movers = [i for i in items_data if i['status'] == 'slow']

        # Top value items
        items_data.sort(key=lambda x: x['value'], reverse=True)
        top_value = items_data[:10]

        return {
            'total_value': round(total_value, 2),
            'total_quantity': total_quantity,
            'unique_items': len(items_data),
            'avg_item_value': round(total_value / len(items_data), 2) if items_data else 0,
            'dead_stock_count': len(dead_stock),
            'dead_stock_value': round(sum(i['value'] for i in dead_stock), 2),
            'slow_movers_count': len(slow_movers),
            'top_value_items': top_value,
            'dead_stock_items': dead_stock,
            'slow_movers': slow_movers[:10]
        }

    @staticmethod
    def get_executive_summary(db, tenant_id):
        """
        Complete executive summary for owner homepage
        Combines all key metrics
        """
        # Today vs Yesterday
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        today_revenue = db.query(func.sum(Transaction.total_amount)).filter(
            and_(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= today,
                Transaction.payment_status == 'completed'
            )
        ).scalar() or 0

        yesterday_revenue = db.query(func.sum(Transaction.total_amount)).filter(
            and_(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= yesterday,
                Transaction.transaction_date < today,
                Transaction.payment_status == 'completed'
            )
        ).scalar() or 0

        # This week profit
        week_profit = OwnerAnalytics.get_profit_analysis(db, tenant_id, week_ago, datetime.utcnow())

        # Labor status
        labor = OwnerAnalytics.get_labor_analysis(db, tenant_id, week_ago, datetime.utcnow())

        # Inventory
        inventory = OwnerAnalytics.get_inventory_valuation(db, tenant_id)

        # Action items
        action_items = []

        if labor['labor_cost_percent'] > 30:
            action_items.append({
                'priority': 'high',
                'category': 'labor',
                'message': f"Labor cost at {labor['labor_cost_percent']}% - target is 25-30%",
                'action': 'Review schedules and optimize staffing'
            })

        if inventory['dead_stock_count'] > 0:
            action_items.append({
                'priority': 'medium',
                'category': 'inventory',
                'message': f"{inventory['dead_stock_count']} items with no sales in 90 days",
                'action': 'Consider markdowns or discontinuing slow items'
            })

        if week_profit['margin_percent'] < 40:
            action_items.append({
                'priority': 'medium',
                'category': 'profit',
                'message': f"Gross margin at {week_profit['margin_percent']}%",
                'action': 'Review pricing and supplier costs'
            })

        return {
            'today': {
                'revenue': round(float(today_revenue), 2),
                'vs_yesterday': round(float(today_revenue) - float(yesterday_revenue), 2),
                'vs_yesterday_percent': round(((float(today_revenue) - float(yesterday_revenue)) / float(yesterday_revenue) * 100), 2) if yesterday_revenue > 0 else 0
            },
            'this_week': {
                'revenue': week_profit['revenue'],
                'profit': week_profit['gross_profit'],
                'margin_percent': week_profit['margin_percent'],
                'transaction_count': week_profit['transaction_count']
            },
            'labor': {
                'cost_percent': labor['labor_cost_percent'],
                'status': labor['status'],
                'total_cost': labor['total_labor_cost']
            },
            'inventory': {
                'total_value': inventory['total_value'],
                'dead_stock_count': inventory['dead_stock_count']
            },
            'action_items': action_items
        }
