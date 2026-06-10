"""
Inventory Lots API
Manage FIFO/COGS lot tracking
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models import Item
from models_inventory_advanced import InventoryLot
from services.fifo_calculator import FIFOCalculator
from datetime import datetime
from sqlalchemy import and_

lots_bp = Blueprint("lots", __name__)


def require_role(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        from functools import wraps
        from flask_jwt_extended import get_jwt
        @wraps(f)
        def decorated_function(*args, **kwargs):
            jwt_data = get_jwt()
            user_role = jwt_data.get("role")

            # Check if role is null/missing
            if user_role is None:
                return jsonify({
                    "error": "Invalid account - please log out and log back in",
                    "code": "INVALID_ROLE"
                }), 401

            if user_role not in allowed_roles:
                return jsonify({
                    "error": f"Insufficient permissions. Required: {', '.join(allowed_roles)}. Your role: {user_role}",
                    "code": "INSUFFICIENT_PERMISSIONS"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@lots_bp.route("", methods=["GET"])
@jwt_required()
@require_role("owner", "manager")
def list_lots():
    """
    List all inventory lots for the tenant
    Optional query params: item_id, active_only
    """
    try:
        tenant_id = g.tenant_id
        item_id = request.args.get("item_id")
        active_only = request.args.get("active_only", "true").lower() == "true"

        query = g.db.query(InventoryLot).filter_by(tenant_id=tenant_id)

        if item_id:
            query = query.filter_by(item_id=item_id)

        if active_only:
            query = query.filter(InventoryLot.quantity > 0)

        lots = query.order_by(InventoryLot.received_date.desc()).all()

        return jsonify({
            "lots": [
                {
                    "id": lot.id,
                    "item_id": lot.item_id,
                    "lot_number": lot.lot_number,
                    "quantity": lot.quantity,
                    "cost_per_unit": float(lot.cost_per_unit),
                    "total_cost": lot.total_cost,
                    "received_date": lot.received_date.isoformat(),
                    "expiration_date": lot.expiration_date.isoformat() if lot.expiration_date else None,
                    "is_expired": lot.is_expired,
                    "created_at": lot.created_at.isoformat()
                }
                for lot in lots
            ],
            "count": len(lots)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lots_bp.route("", methods=["POST"])
@jwt_required()
@require_role("owner", "manager")
def create_lot():
    """
    Create a new inventory lot
    Used when receiving inventory from suppliers
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        # Validate required fields
        required_fields = ["item_id", "lot_number", "quantity", "cost_per_unit"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Verify item exists and belongs to tenant
        item = g.db.query(Item).filter_by(
            id=data["item_id"],
            tenant_id=tenant_id
        ).first()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Parse dates
        received_date = None
        if data.get("received_date"):
            received_date = datetime.fromisoformat(data["received_date"].replace('Z', '+00:00'))

        expiration_date = None
        if data.get("expiration_date"):
            expiration_date = datetime.fromisoformat(data["expiration_date"].replace('Z', '+00:00'))

        # Create lot using service
        lot = FIFOCalculator.create_lot(
            db=g.db,
            tenant_id=tenant_id,
            item_id=data["item_id"],
            lot_number=data["lot_number"],
            quantity=int(data["quantity"]),
            cost_per_unit=float(data["cost_per_unit"]),
            received_date=received_date,
            expiration_date=expiration_date
        )

        # Update item stock
        item.stock_on_hand += lot.quantity
        g.db.add(item)

        g.db.commit()

        return jsonify({
            "message": "Lot created successfully",
            "lot": {
                "id": lot.id,
                "item_id": lot.item_id,
                "lot_number": lot.lot_number,
                "quantity": lot.quantity,
                "cost_per_unit": float(lot.cost_per_unit),
                "total_cost": lot.total_cost,
                "received_date": lot.received_date.isoformat(),
                "expiration_date": lot.expiration_date.isoformat() if lot.expiration_date else None
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@lots_bp.route("/<lot_id>", methods=["GET"])
@jwt_required()
@require_role("owner", "manager")
def get_lot(lot_id):
    """Get details of a specific lot"""
    try:
        tenant_id = g.tenant_id

        lot = g.db.query(InventoryLot).filter_by(
            id=lot_id,
            tenant_id=tenant_id
        ).first()

        if not lot:
            return jsonify({"error": "Lot not found"}), 404

        return jsonify({
            "id": lot.id,
            "item_id": lot.item_id,
            "lot_number": lot.lot_number,
            "quantity": lot.quantity,
            "cost_per_unit": float(lot.cost_per_unit),
            "total_cost": lot.total_cost,
            "received_date": lot.received_date.isoformat(),
            "expiration_date": lot.expiration_date.isoformat() if lot.expiration_date else None,
            "is_expired": lot.is_expired,
            "created_at": lot.created_at.isoformat(),
            "updated_at": lot.updated_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lots_bp.route("/<lot_id>", methods=["PATCH"])
@jwt_required()
@require_role("owner", "manager")
def update_lot(lot_id):
    """
    Update lot details
    Allows adjusting quantity for corrections/damages
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        lot = g.db.query(InventoryLot).filter_by(
            id=lot_id,
            tenant_id=tenant_id
        ).first()

        if not lot:
            return jsonify({"error": "Lot not found"}), 404

        # Track quantity change for item stock update
        old_quantity = lot.quantity

        # Update allowed fields
        if "quantity" in data:
            lot.quantity = int(data["quantity"])

        if "cost_per_unit" in data:
            lot.cost_per_unit = float(data["cost_per_unit"])

        if "expiration_date" in data:
            if data["expiration_date"]:
                lot.expiration_date = datetime.fromisoformat(data["expiration_date"].replace('Z', '+00:00'))
            else:
                lot.expiration_date = None

        # Update item stock if quantity changed
        if lot.quantity != old_quantity:
            item = g.db.query(Item).filter_by(id=lot.item_id).first()
            if item:
                quantity_diff = lot.quantity - old_quantity
                item.stock_on_hand += quantity_diff
                g.db.add(item)

        g.db.add(lot)
        g.db.commit()

        return jsonify({
            "message": "Lot updated successfully",
            "lot": {
                "id": lot.id,
                "quantity": lot.quantity,
                "cost_per_unit": float(lot.cost_per_unit),
                "total_cost": lot.total_cost
            }
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@lots_bp.route("/item/<item_id>/summary", methods=["GET"])
@jwt_required()
@require_role("owner", "manager", "cashier")
def get_item_lot_summary(item_id):
    """
    Get FIFO/COGS summary for an item
    Shows all lots, total value, average cost
    """
    try:
        tenant_id = g.tenant_id

        # Verify item exists
        item = g.db.query(Item).filter_by(
            id=item_id,
            tenant_id=tenant_id
        ).first()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Get lot summary
        summary = FIFOCalculator.get_lot_summary(g.db, tenant_id, item_id)

        return jsonify({
            "item_id": item_id,
            "item_name": item.name,
            "item_sku": item.sku,
            "stock_on_hand": item.stock_on_hand,
            **summary
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lots_bp.route("/item/<item_id>/cogs-preview", methods=["POST"])
@jwt_required()
@require_role("owner", "manager", "cashier")
def preview_cogs(item_id):
    """
    Preview COGS calculation for a potential sale
    Does NOT actually allocate inventory
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        if "quantity" not in data:
            return jsonify({"error": "Missing required field: quantity"}), 400

        quantity = int(data["quantity"])

        # Get FIFO allocation preview
        allocations, total_cogs, success = FIFOCalculator.allocate_sale(
            db=g.db,
            tenant_id=tenant_id,
            item_id=item_id,
            quantity_needed=quantity
        )

        if not success:
            return jsonify({
                "error": "Insufficient inventory in lots",
                "message": "Not enough inventory allocated to lots to fulfill this sale"
            }), 400

        avg_cost = total_cogs / quantity if quantity > 0 else 0

        return jsonify({
            "item_id": item_id,
            "quantity": quantity,
            "total_cogs": round(total_cogs, 2),
            "average_cost_per_unit": round(avg_cost, 2),
            "allocations": [
                {
                    "lot_number": alloc["lot_number"],
                    "quantity": alloc["quantity"],
                    "cost_per_unit": round(alloc["cost_per_unit"], 2),
                    "total_cost": round(alloc["total_cost"], 2)
                }
                for alloc in allocations
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
