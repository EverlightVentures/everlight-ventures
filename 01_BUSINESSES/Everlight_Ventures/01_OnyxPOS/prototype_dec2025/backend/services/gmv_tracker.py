"""
GMV (Gross Merchandise Value) Tracking Service
Tracks sales volume for usage-based billing
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func
from models import Tenant, Transaction
from database import Session


class GMVTracker:
    """Service for tracking and calculating GMV for usage-based fees"""

    @staticmethod
    def record_sale(tenant_id: str, sale_amount: Decimal):
        """
        Record a sale and update tenant's GMV
        Called automatically when a transaction is created
        """
        session = Session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return False

            # Initialize GMV tracking if needed
            if not tenant.last_gmv_reset:
                tenant.last_gmv_reset = datetime.utcnow()
                tenant.gmv_current_month = Decimal('0')

            # Check if we need to reset for a new month
            GMVTracker.check_and_reset_monthly(tenant)

            # Add to current month GMV
            current_gmv = tenant.gmv_current_month or Decimal('0')
            tenant.gmv_current_month = current_gmv + Decimal(str(sale_amount))

            # Recalculate usage fee
            tenant.usage_fee_current_month = tenant.calculate_usage_fee()

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            print(f"Error recording GMV: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def check_and_reset_monthly(tenant: Tenant):
        """
        Check if month has changed and reset GMV tracking
        This would typically run as a scheduled job
        """
        if not tenant.last_gmv_reset:
            tenant.last_gmv_reset = datetime.utcnow()
            return

        now = datetime.utcnow()
        last_reset = tenant.last_gmv_reset

        # Check if we're in a new month
        if now.month != last_reset.month or now.year != last_reset.year:
            # Save last month's GMV
            tenant.gmv_last_month = tenant.gmv_current_month or Decimal('0')

            # Reset current month
            tenant.gmv_current_month = Decimal('0')
            tenant.usage_fee_current_month = Decimal('0')
            tenant.last_gmv_reset = now

    @staticmethod
    def get_gmv_stats(tenant_id: str):
        """Get GMV statistics for a tenant"""
        session = Session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None

            # Calculate month-to-date GMV from actual transactions
            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1)

            mtd_gmv = session.query(func.sum(Transaction.total_amount)).filter(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= month_start,
                Transaction.payment_status == 'completed'
            ).scalar() or Decimal('0')

            # Calculate last month's GMV
            if now.month == 1:
                last_month_start = datetime(now.year - 1, 12, 1)
                last_month_end = datetime(now.year, 1, 1)
            else:
                last_month_start = datetime(now.year, now.month - 1, 1)
                last_month_end = datetime(now.year, now.month, 1)

            last_month_gmv = session.query(func.sum(Transaction.total_amount)).filter(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= last_month_start,
                Transaction.transaction_date < last_month_end,
                Transaction.payment_status == 'completed'
            ).scalar() or Decimal('0')

            # Get pricing info
            plan_tier = tenant.plan_tier
            monthly_fee = tenant.get_monthly_subscription_fee()
            usage_fee_percent = tenant.get_platform_fee_percent()
            usage_fee_amount = tenant.calculate_usage_fee(float(mtd_gmv))
            total_cost = monthly_fee + usage_fee_amount

            # Calculate break-even points
            breakevens = {}
            if plan_tier == "starter":
                breakevens["growth"] = tenant.get_breakeven_gmv("growth")
                breakevens["scale"] = tenant.get_breakeven_gmv("scale")
            elif plan_tier == "growth":
                breakevens["scale"] = tenant.get_breakeven_gmv("scale")

            return {
                "current_month_gmv": float(mtd_gmv),
                "last_month_gmv": float(last_month_gmv),
                "plan_tier": plan_tier,
                "monthly_subscription_fee": float(monthly_fee),
                "usage_fee_percent": usage_fee_percent,
                "usage_fee_amount": usage_fee_amount,
                "total_monthly_cost": total_cost,
                "breakeven_points": breakevens,
                "days_in_month": now.day,
                "total_days_in_month": (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31
            }

        except Exception as e:
            print(f"Error getting GMV stats: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def calculate_projected_monthly_cost(tenant_id: str, projected_gmv: float = None):
        """
        Calculate projected monthly cost based on current GMV trend
        or a specific projected GMV amount
        """
        session = Session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None

            if projected_gmv is None:
                # Calculate projection based on current trend
                stats = GMVTracker.get_gmv_stats(tenant_id)
                if not stats:
                    return None

                days_elapsed = stats["days_in_month"]
                total_days = stats["total_days_in_month"]
                current_gmv = stats["current_month_gmv"]

                if days_elapsed > 0:
                    daily_average = current_gmv / days_elapsed
                    projected_gmv = daily_average * total_days
                else:
                    projected_gmv = 0

            monthly_fee = tenant.get_monthly_subscription_fee()
            usage_fee = tenant.calculate_usage_fee(projected_gmv)

            return {
                "projected_gmv": round(projected_gmv, 2),
                "monthly_subscription_fee": float(monthly_fee),
                "projected_usage_fee": usage_fee,
                "projected_total_cost": float(monthly_fee) + usage_fee,
                "plan_tier": tenant.plan_tier
            }

        except Exception as e:
            print(f"Error calculating projected cost: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def recommend_plan_upgrade(tenant_id: str):
        """
        Analyze tenant's GMV and recommend if they should upgrade
        Returns None if no upgrade recommended, or tier name if upgrade beneficial
        """
        session = Session()
        try:
            tenant = session.query(Tenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None

            current_tier = tenant.plan_tier
            stats = GMVTracker.get_gmv_stats(tenant_id)

            if not stats:
                return None

            current_gmv = stats["current_month_gmv"]
            current_cost = stats["total_monthly_cost"]

            # Check if upgrade to next tier would save money
            recommendations = []

            if current_tier == "starter":
                # Check growth tier
                growth_breakeven = tenant.get_breakeven_gmv("growth")
                if growth_breakeven and current_gmv > growth_breakeven * 0.8:  # 80% of breakeven
                    temp_tenant = Tenant(plan_tier="growth")
                    growth_cost = temp_tenant.get_monthly_subscription_fee() + temp_tenant.calculate_usage_fee(current_gmv)

                    if growth_cost < current_cost:
                        recommendations.append({
                            "tier": "growth",
                            "current_cost": current_cost,
                            "new_cost": growth_cost,
                            "savings": current_cost - growth_cost,
                            "reason": f"Your GMV of ${current_gmv:,.2f} exceeds the break-even point"
                        })

                # Check scale tier
                scale_breakeven = tenant.get_breakeven_gmv("scale")
                if scale_breakeven and current_gmv > scale_breakeven * 0.8:
                    temp_tenant = Tenant(plan_tier="scale")
                    scale_cost = temp_tenant.get_monthly_subscription_fee()  # No usage fee for scale

                    if scale_cost < current_cost:
                        recommendations.append({
                            "tier": "scale",
                            "current_cost": current_cost,
                            "new_cost": scale_cost,
                            "savings": current_cost - scale_cost,
                            "reason": f"Your GMV of ${current_gmv:,.2f} exceeds the break-even point for Scale plan"
                        })

            elif current_tier == "growth":
                # Check scale tier
                scale_breakeven = tenant.get_breakeven_gmv("scale")
                if scale_breakeven and current_gmv > scale_breakeven * 0.8:
                    temp_tenant = Tenant(plan_tier="scale")
                    scale_cost = temp_tenant.get_monthly_subscription_fee()

                    if scale_cost < current_cost:
                        recommendations.append({
                            "tier": "scale",
                            "current_cost": current_cost,
                            "new_cost": scale_cost,
                            "savings": current_cost - scale_cost,
                            "reason": f"Your GMV of ${current_gmv:,.2f} exceeds the break-even point for Scale plan"
                        })

            # Return the best recommendation (highest savings)
            if recommendations:
                return max(recommendations, key=lambda x: x["savings"])

            return None

        except Exception as e:
            print(f"Error recommending plan: {e}")
            return None
        finally:
            session.close()
