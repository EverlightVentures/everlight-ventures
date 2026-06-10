"""
Billing & GMV API
- Get GMV statistics
- Calculate projected costs
- Get plan recommendations
- View pricing tiers
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models import Tenant
from services.gmv_tracker import GMVTracker

billing_gmv_bp = Blueprint("billing_gmv", __name__)


@billing_gmv_bp.route("/gmv-stats", methods=["GET"])
@jwt_required()
def get_gmv_stats():
    """
    Get GMV statistics and billing information for current tenant
    """
    try:
        tenant_id = g.tenant_id
        stats = GMVTracker.get_gmv_stats(tenant_id)

        if not stats:
            return jsonify({"error": "Could not retrieve GMV stats"}), 500

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@billing_gmv_bp.route("/projected-cost", methods=["GET"])
@jwt_required()
def get_projected_cost():
    """
    Get projected monthly cost based on current GMV trend
    Optional query param: ?projected_gmv=50000
    """
    try:
        tenant_id = g.tenant_id
        projected_gmv = request.args.get("projected_gmv", type=float)

        projection = GMVTracker.calculate_projected_monthly_cost(tenant_id, projected_gmv)

        if not projection:
            return jsonify({"error": "Could not calculate projection"}), 500

        return jsonify(projection), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@billing_gmv_bp.route("/plan-recommendation", methods=["GET"])
@jwt_required()
def get_plan_recommendation():
    """
    Get plan upgrade recommendation based on GMV
    """
    try:
        tenant_id = g.tenant_id
        recommendation = GMVTracker.recommend_plan_upgrade(tenant_id)

        if not recommendation:
            return jsonify({
                "has_recommendation": False,
                "message": "Your current plan is optimal for your sales volume"
            }), 200

        return jsonify({
            "has_recommendation": True,
            "recommendation": recommendation
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@billing_gmv_bp.route("/pricing-tiers", methods=["GET"])
def get_pricing_tiers():
    """
    Get all pricing tier information (public endpoint)
    OnyxOS Commission-Based Pricing Model (New Default)
    """
    try:
        tiers = [
            {
                "tier": "starter_commission",
                "name": "OnyxOS Starter",
                "best_for": "New entrepreneurs just getting started",
                "monthly_fee": 29.99,
                "commission": 5.0,  # 5% of sales
                "pricing_model": "commission",
                "annual_discount": 0.10,  # 10% prepay discount
                "annual_price": 323.89,  # $29.99 * 12 * 0.9
                "features": {
                    "headline": "Affordable POS for first-time business owners",
                    "included": [
                        "Unlimited transactions",
                        "FIFO/COGS inventory tracking",
                        "Owner profit dashboards",
                        "Real-time analytics & reporting",
                        "Multi-payment support (cash, card)",
                        "Mobile PWA (works on any device)",
                        "CSV/Excel import/export",
                        "Time clock & scheduling",
                        "Onboarding wizard",
                        "Industry templates (coffee, boutique, salon)",
                        "Contextual help & tooltips",
                        "Business education via AI"
                    ],
                    "limits": {
                        "locations": 1,
                        "users": "Unlimited",
                        "transactions": "Unlimited"
                    }
                },
                "commission_note": "5% platform fee on all sales processed through OnyxPOS"
            },
            {
                "tier": "pro_commission",
                "name": "OnyxOS Pro",
                "best_for": "Growing businesses doing $10k+/month in sales",
                "monthly_fee": 99.99,
                "commission": 1.0,  # 1% of sales
                "pricing_model": "commission",
                "annual_discount": 0.10,
                "annual_price": 1079.89,  # $99.99 * 12 * 0.9
                "features": {
                    "headline": "Everything in Starter + lower commission rate",
                    "included": [
                        "Everything in Starter",
                        "Shopify integration (sync inventory & orders)",
                        "Square payment processing",
                        "Gusto payroll integration",
                        "QuickBooks sync (daily sales)",
                        "OnyxAI business assistant",
                        "Weekly owner digest emails",
                        "Priority support",
                        "Training mode for employees",
                        "Advanced reporting"
                    ],
                    "limits": {
                        "locations": 1,
                        "users": "Unlimited",
                        "transactions": "Unlimited"
                    }
                },
                "commission_note": "Only 1% platform fee on all sales - best for high volume"
            },
            {
                "tier": "onyxpos_core",
                "name": "OnyxPOS Enterprise (Flat Fee)",
                "best_for": "High-volume businesses wanting flat pricing",
                "monthly_fee": 249.00,
                "commission": 0.0,  # No commission
                "pricing_model": "flat",
                "annual_discount": 0.10,  # 10% prepay discount
                "annual_price": 2688.00,  # $249 * 12 * 0.9
                "features": {
                    "headline": "Premium POS with no commission fees",
                    "included": [
                        "Everything in Pro",
                        "No platform fees (0% commission)",
                        "Unlimited transactions",
                        "FIFO/COGS inventory tracking",
                        "Owner profit dashboards",
                        "Real-time analytics & reporting",
                        "Multi-payment support (cash, card, crypto)",
                        "Mobile apps (iOS + Android)",
                        "CSV/Excel import/export",
                        "Self-diagnosing support system",
                        "Time clock & scheduling",
                        "Basic payroll calculations"
                    ],
                    "limits": {
                        "locations": 1,
                        "users": "Unlimited",
                        "transactions": "Unlimited"
                    }
                },
                "commission_note": "No commission fees - best for businesses doing $25k+/month"
            },
            {
                "tier": "onyxpayroll",
                "name": "OnyxPayroll Add-On",
                "best_for": "Full payroll management with Gusto integration",
                "monthly_fee": 149.00,
                "annual_discount": 0.10,
                "annual_price": 1608.00,  # $149 * 12 * 0.9
                "requires": "onyxpos_core",  # Must have POS Core
                "features": {
                    "headline": "Owner-only payroll with compliance",
                    "included": [
                        "Gusto integration (self-service setup)",
                        "Automated hours tracking from time clock",
                        "Owner approval workflow",
                        "Payroll run creation & preview",
                        "Tax calculations (via Gusto)",
                        "W-2 generation (via Gusto)",
                        "Labor cost analytics",
                        "Overtime tracking",
                        "Compliance engine"
                    ],
                    "limits": {
                        "employees": "Unlimited"
                    },
                    "note": "Requires Gusto account (you pay Gusto directly, typically $40/mo + $6/employee)"
                }
            },
            {
                "tier": "onyxos_bundle",
                "name": "OnyxOS Bundle",
                "best_for": "Complete operating system for business owners",
                "monthly_fee": 400.00,
                "annual_discount": 0.10,
                "annual_price": 4320.00,  # $400 * 12 * 0.9
                "savings": 48.00,  # Save $4/mo vs buying separately ($249 + $149 = $398)
                "features": {
                    "headline": "OnyxPOS + OnyxPayroll + Premium Features",
                    "included": [
                        "Everything in OnyxPOS Core",
                        "Everything in OnyxPayroll",
                        "Owner intelligence dashboards",
                        "Profit margin analysis (FIFO-based)",
                        "Labor cost optimization",
                        "Inventory valuation reports",
                        "Dead stock alerts",
                        "Weekly owner digest emails",
                        "Priority onboarding (7-14 days)",
                        "Migration assistance"
                    ],
                    "limits": {
                        "locations": 1,
                        "users": "Unlimited",
                        "employees": "Unlimited",
                        "transactions": "Unlimited"
                    },
                    "contract": "Annual contract required"
                }
            }
        ]

        return jsonify({"tiers": tiers}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@billing_gmv_bp.route("/calculate-cost", methods=["POST"])
def calculate_cost_for_gmv():
    """
    Calculate total monthly cost for a given GMV and tier (public endpoint)
    Request body: { "tier": "starter", "gmv": 50000 }
    """
    try:
        data = request.json
        tier = data.get("tier", "starter")
        gmv = data.get("gmv", 0)

        if tier not in ["starter", "growth", "scale"]:
            return jsonify({"error": "Invalid tier"}), 400

        # Create temporary tenant to use pricing methods
        temp_tenant = Tenant(plan_tier=tier)
        monthly_fee = temp_tenant.get_monthly_subscription_fee()
        gmv_fee_percent = temp_tenant.get_platform_fee_percent()
        fee_cap = temp_tenant.get_variable_fee_cap()

        # Calculate usage fee before cap
        uncapped_usage_fee = gmv * (gmv_fee_percent / 100)
        usage_fee = temp_tenant.calculate_usage_fee(gmv)
        cap_reached = uncapped_usage_fee > fee_cap if fee_cap > 0 else False

        total_cost = monthly_fee + usage_fee

        # Calculate all tiers for comparison
        all_costs = []
        for t in ["starter", "growth", "scale"]:
            temp = Tenant(plan_tier=t)
            t_monthly = temp.get_monthly_subscription_fee()
            t_usage = temp.calculate_usage_fee(gmv)
            t_cap = temp.get_variable_fee_cap()
            t_percent = temp.get_platform_fee_percent()
            t_uncapped = gmv * (t_percent / 100)
            t_total = t_monthly + t_usage
            all_costs.append({
                "tier": t,
                "monthly_fee": float(t_monthly),
                "usage_fee": t_usage,
                "usage_fee_percent": t_percent,
                "usage_fee_cap": t_cap,
                "cap_reached": t_uncapped > t_cap if t_cap > 0 else False,
                "total_cost": t_total
            })

        # Find cheapest tier
        cheapest = min(all_costs, key=lambda x: x["total_cost"])

        return jsonify({
            "tier": tier,
            "gmv": gmv,
            "monthly_subscription_fee": float(monthly_fee),
            "gmv_fee_percent": gmv_fee_percent,
            "usage_fee": usage_fee,
            "usage_fee_cap": fee_cap,
            "cap_reached": cap_reached,
            "savings_from_cap": round(uncapped_usage_fee - usage_fee, 2) if cap_reached else 0,
            "total_monthly_cost": total_cost,
            "all_tiers_comparison": all_costs,
            "recommended_tier": cheapest["tier"],
            "recommended_tier_cost": cheapest["total_cost"],
            "potential_savings": total_cost - cheapest["total_cost"] if tier != cheapest["tier"] else 0
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@billing_gmv_bp.route("/breakeven-calculator", methods=["GET"])
def get_breakeven_points():
    """
    Get break-even GMV points between tiers (public endpoint)
    """
    try:
        starter = Tenant(plan_tier="starter")
        growth = Tenant(plan_tier="growth")
        scale = Tenant(plan_tier="scale")

        # Starter vs Growth: (99 - 49) / (0.0035 - 0.0020) = 50 / 0.0015 = 33,333
        starter_vs_growth = starter.get_breakeven_gmv("growth")

        # Growth vs Scale: (249 - 99) / (0.0020 - 0.0000) = 150 / 0.0020 = 75,000
        growth_vs_scale = growth.get_breakeven_gmv("scale")

        # Starter vs Scale
        starter_vs_scale = starter.get_breakeven_gmv("scale")

        return jsonify({
            "breakeven_points": {
                "starter_vs_growth": {
                    "gmv": starter_vs_growth,
                    "description": f"At ${starter_vs_growth:,.0f}/mo GMV, Starter and Growth cost the same. Above this, Growth is cheaper."
                },
                "growth_vs_scale": {
                    "gmv": growth_vs_scale,
                    "description": f"At ${growth_vs_scale:,.0f}/mo GMV, Growth and Scale cost the same. Above this, Scale is cheaper."
                },
                "starter_vs_scale": {
                    "gmv": starter_vs_scale,
                    "description": f"At ${starter_vs_scale:,.0f}/mo GMV, Starter and Scale cost the same."
                }
            },
            "guidance": {
                "under_33k": "Starter plan is most cost-effective",
                "33k_to_75k": "Growth plan is most cost-effective",
                "above_75k": "Scale plan is most cost-effective (no GMV fees!)"
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
