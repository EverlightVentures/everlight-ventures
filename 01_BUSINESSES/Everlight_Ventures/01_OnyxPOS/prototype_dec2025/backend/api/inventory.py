"""
Inventory API
- List items
- Add/Edit/Delete items
- Search and filter
- Low stock alerts
"""
import csv
import io
import json
import re
import sys
import os
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from models import Item
from sqlalchemy import or_
import openpyxl
import xlrd

# Add services to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.sku_generator import SKUGenerator

inventory_bp = Blueprint("inventory", __name__)
IMPORT_FIELDS = [
    "sku",
    "name",
    "description",
    "category",
    "sell_price",
    "cost_price",
    "stock_on_hand",
    "reorder_point",
    "reorder_quantity",
    "supplier_name",
    "supplier_sku",
    "barcode",
]

REQUIRED_FIELDS = {"sku", "name", "sell_price"}
INT_FIELDS = {"stock_on_hand", "reorder_point", "reorder_quantity"}
DECIMAL_FIELDS = {"sell_price", "cost_price"}

FIELD_SYNONYMS = {
    "sku": ["sku", "item sku", "product sku", "item code", "product code", "code"],
    "name": ["name", "product name", "item name", "title"],
    "description": ["description", "desc", "details"],
    "category": ["category", "type", "department"],
    "sell_price": ["sell price", "sale price", "price", "retail price"],
    "cost_price": ["cost price", "cost", "unit cost", "wholesale"],
    "stock_on_hand": ["stock", "on hand", "stock on hand", "qty", "quantity", "inventory"],
    "reorder_point": ["reorder point", "reorder level", "min stock", "min qty"],
    "reorder_quantity": ["reorder quantity", "reorder qty", "reorder amount"],
    "supplier_name": ["supplier", "vendor", "supplier name", "vendor name"],
    "supplier_sku": ["supplier sku", "vendor sku", "supplier code", "vendor code"],
    "barcode": ["barcode", "upc", "ean", "isbn"],
}


def _normalize_header(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _auto_map_columns(headers):
    normalized = [_normalize_header(h) for h in headers]
    mapping = {}
    used_indexes = set()

    for field in IMPORT_FIELDS:
        candidates = []
        for idx, header in enumerate(normalized):
            for synonym in FIELD_SYNONYMS.get(field, []):
                syn = _normalize_header(synonym)
                if header == syn or syn in header or header in syn:
                    candidates.append(idx)
                    break
        for idx in candidates:
            if idx not in used_indexes:
                mapping[field] = headers[idx]
                used_indexes.add(idx)
                break

    return mapping


def _coerce_value(field, value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
    else:
        text = str(value).strip()

    if field in DECIMAL_FIELDS:
        text = text.replace("$", "").replace(",", "")
        return float(text)
    if field in INT_FIELDS:
        text = text.replace(",", "")
        return int(float(text))

    return text


def _read_csv(file_bytes):
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    data_rows = rows[1:]
    return headers, data_rows


def _read_xlsx(file_bytes):
    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(h or "").strip() for h in rows[0]]
    data_rows = [list(row) for row in rows[1:]]
    return headers, data_rows


def _read_xls(file_bytes):
    book = xlrd.open_workbook(file_contents=file_bytes)
    sheet = book.sheet_by_index(0)
    headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]
    data_rows = [
        [sheet.cell_value(row, col) for col in range(sheet.ncols)]
        for row in range(1, sheet.nrows)
    ]
    return headers, data_rows


def _parse_import_file(file_storage):
    filename = (file_storage.filename or "").lower()
    file_bytes = file_storage.read()
    if filename.endswith(".csv"):
        return _read_csv(file_bytes)
    if filename.endswith(".xlsx"):
        return _read_xlsx(file_bytes)
    if filename.endswith(".xls"):
        return _read_xls(file_bytes)
    raise ValueError("Unsupported file type. Use CSV or Excel (.xls/.xlsx).")


def _map_row(headers, row, mapping):
    data = {}
    header_index = {h: idx for idx, h in enumerate(headers)}
    for field, column in mapping.items():
        idx = header_index.get(column)
        if idx is None or idx >= len(row):
            data[field] = None
            continue
        data[field] = _coerce_value(field, row[idx])
    return data


def _is_empty_row(row):
    return all(str(value).strip() == "" for value in row if value is not None)


def require_role(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        from functools import wraps
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


@inventory_bp.route("", methods=["GET"])
@jwt_required()
def list_items():
    """
    List all inventory items for tenant
    Supports search, filtering, and pagination
    """
    try:
        tenant_id = g.tenant_id

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        # Search
        search = request.args.get("search", "").strip()

        # Filters
        category = request.args.get("category")
        low_stock_only = request.args.get("low_stock", "false").lower() == "true"

        # Build query
        query = g.db.query(Item).filter_by(tenant_id=tenant_id, is_active=True)

        if search:
            query = query.filter(
                or_(
                    Item.name.ilike(f"%{search}%"),
                    Item.sku.ilike(f"%{search}%"),
                    Item.barcode.ilike(f"%{search}%")
                )
            )

        if category:
            query = query.filter_by(category=category)

        if low_stock_only:
            query = query.filter(Item.stock_on_hand <= Item.reorder_point)

        # Order by name
        query = query.order_by(Item.name)

        # Paginate
        offset = (page - 1) * per_page
        total = query.count()
        items = query.limit(per_page).offset(offset).all()

        return jsonify({
            "items": [{
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "category": item.category,
                "sell_price": float(item.sell_price),
                "cost_price": float(item.cost_price) if item.cost_price else None,
                "stock_on_hand": item.stock_on_hand,
                "reorder_point": item.reorder_point,
                "is_low_stock": item.is_low_stock,
                "barcode": item.barcode,
                "image_url": item.image_url
            } for item in items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/<item_id>", methods=["GET"])
@jwt_required()
def get_item(item_id):
    """Get single item by ID"""
    try:
        tenant_id = g.tenant_id
        item = g.db.query(Item).filter_by(id=item_id, tenant_id=tenant_id).first()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        return jsonify({
            "item": {
                "id": item.id,
                "sku": item.sku,
                "barcode": item.barcode,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "sell_price": float(item.sell_price),
                "cost_price": float(item.cost_price) if item.cost_price else None,
                "markup_percentage": float(item.markup_percentage) if item.markup_percentage else None,
                "stock_on_hand": item.stock_on_hand,
                "reorder_point": item.reorder_point,
                "reorder_quantity": item.reorder_quantity,
                "supplier_name": item.supplier_name,
                "supplier_sku": item.supplier_sku,
                "is_active": item.is_active,
                "image_url": item.image_url,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("", methods=["POST"])
@jwt_required()
@require_role("owner", "manager")
def create_item():
    """Create new inventory item with auto-generated SKU"""
    try:
        tenant_id = g.tenant_id
        data = request.json

        # Validate required fields (SKU is now optional - will be auto-generated)
        if not data.get("name") or not data.get("sell_price"):
            return jsonify({"error": "Name and sell_price are required"}), 400

        # Auto-generate SKU if not provided
        if not data.get("sku"):
            generated_sku = SKUGenerator.generate_sku(
                tenant_id=tenant_id,
                item_name=data["name"],
                category=data.get("category")
            )
            data["sku"] = generated_sku
            sku_auto_generated = True
        else:
            sku_auto_generated = False

            # Check if manually provided SKU already exists
            existing = g.db.query(Item).filter_by(tenant_id=tenant_id, sku=data["sku"]).first()
            if existing:
                return jsonify({"error": "SKU already exists"}), 409

        # Create item
        item = Item(
            tenant_id=tenant_id,
            sku=data["sku"],
            barcode=data.get("barcode"),
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            sell_price=data["sell_price"],
            cost_price=data.get("cost_price"),
            stock_on_hand=data.get("stock_on_hand", 0),
            reorder_point=data.get("reorder_point", 0),
            reorder_quantity=data.get("reorder_quantity"),
            supplier_name=data.get("supplier_name"),
            supplier_sku=data.get("supplier_sku"),
            image_url=data.get("image_url")
        )

        g.db.add(item)
        g.db.commit()

        return jsonify({
            "message": "Item created successfully",
            "item": {
                "id": item.id,
                "sku": item.sku,
                "sku_auto_generated": sku_auto_generated,
                "name": item.name,
                "sell_price": float(item.sell_price)
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/<item_id>", methods=["PATCH"])
@jwt_required()
@require_role("owner", "manager")
def update_item(item_id):
    """Update inventory item"""
    try:
        tenant_id = g.tenant_id
        item = g.db.query(Item).filter_by(id=item_id, tenant_id=tenant_id).first()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        data = request.json

        # Update fields
        updatable_fields = [
            "name", "description", "category", "sell_price", "cost_price",
            "stock_on_hand", "reorder_point", "reorder_quantity",
            "supplier_name", "supplier_sku", "barcode", "image_url", "is_active"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(item, field, data[field])

        g.db.commit()

        return jsonify({
            "message": "Item updated successfully",
            "item": {
                "id": item.id,
                "sku": item.sku,
                "name": item.name
            }
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/<item_id>", methods=["DELETE"])
@jwt_required()
@require_role("owner", "manager")
def delete_item(item_id):
    """Delete (soft delete) inventory item"""
    try:
        tenant_id = g.tenant_id
        item = g.db.query(Item).filter_by(id=item_id, tenant_id=tenant_id).first()

        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Soft delete
        item.is_active = False
        g.db.commit()

        return jsonify({"message": "Item deleted successfully"}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/low-stock", methods=["GET"])
@jwt_required()
def low_stock():
    """Get items below reorder point"""
    try:
        tenant_id = g.tenant_id

        items = g.db.query(Item).filter(
            Item.tenant_id == tenant_id,
            Item.is_active == True,
            Item.stock_on_hand <= Item.reorder_point
        ).order_by(Item.stock_on_hand).all()

        return jsonify({
            "low_stock_items": [{
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "stock_on_hand": item.stock_on_hand,
                "reorder_point": item.reorder_point,
                "reorder_quantity": item.reorder_quantity
            } for item in items],
            "count": len(items)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/import/debug", methods=["POST", "GET"])
@jwt_required()
def import_debug():
    """Debug endpoint to check JWT and permissions"""
    try:
        from flask import request
        jwt_data = get_jwt()
        return jsonify({
            "jwt_data": jwt_data,
            "headers": dict(request.headers),
            "tenant_id": g.tenant_id,
            "user_id": g.user_id,
            "role": jwt_data.get("role"),
            "method": request.method,
            "content_type": request.content_type
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/import/preview", methods=["POST"])
@jwt_required()
@require_role("owner", "manager", "cashier", "laborer")
def preview_import():
    """Preview inventory import with auto-mapped fields."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        headers, rows = _parse_import_file(file)
        if not headers:
            return jsonify({"error": "File has no headers"}), 400

        mapping = _auto_map_columns(headers)
        missing_required = [field for field in REQUIRED_FIELDS if field not in mapping]

        preview_rows = []
        total_rows = 0
        for idx, row in enumerate(rows, start=2):
            if _is_empty_row(row):
                continue
            total_rows += 1
            if len(preview_rows) < 20:
                mapped = _map_row(headers, row, mapping)
                preview_rows.append({
                    "row": idx,
                    "data": mapped
                })

        return jsonify({
            "columns": headers,
            "suggested_mapping": mapping,
            "missing_required_fields": missing_required,
            "preview_rows": preview_rows,
            "total_rows": total_rows
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_bp.route("/import/confirm", methods=["POST"])
@jwt_required()
@require_role("owner", "manager", "cashier", "laborer")
def confirm_import():
    """Import inventory items with provided or auto mapping."""
    try:
        tenant_id = g.tenant_id

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        headers, rows = _parse_import_file(file)
        if not headers:
            return jsonify({"error": "File has no headers"}), 400

        mapping_raw = request.form.get("mapping")
        if mapping_raw:
            mapping = json.loads(mapping_raw)
        else:
            mapping = _auto_map_columns(headers)

        missing_required = [field for field in REQUIRED_FIELDS if field not in mapping]
        if missing_required:
            return jsonify({
                "error": "Missing required fields",
                "missing_required_fields": missing_required
            }), 400

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            if _is_empty_row(row):
                continue

            data = _map_row(headers, row, mapping)

            if not data.get("sku") or not data.get("name") or data.get("sell_price") is None:
                skipped += 1
                errors.append(f"Row {idx}: Missing required fields")
                continue

            existing_item = g.db.query(Item).filter_by(
                tenant_id=tenant_id,
                sku=data["sku"]
            ).first()

            if existing_item:
                for field, value in data.items():
                    if field in IMPORT_FIELDS and value is not None:
                        setattr(existing_item, field, value)
                updated += 1
            else:
                item = Item(
                    tenant_id=tenant_id,
                    sku=data["sku"],
                    name=data["name"],
                    description=data.get("description"),
                    category=data.get("category"),
                    sell_price=data["sell_price"],
                    cost_price=data.get("cost_price"),
                    stock_on_hand=data.get("stock_on_hand", 0) or 0,
                    reorder_point=data.get("reorder_point", 0) or 0,
                    reorder_quantity=data.get("reorder_quantity"),
                    supplier_name=data.get("supplier_name"),
                    supplier_sku=data.get("supplier_sku"),
                    barcode=data.get("barcode"),
                )
                g.db.add(item)
                created += 1

        g.db.commit()

        return jsonify({
            "message": "Import completed",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500
