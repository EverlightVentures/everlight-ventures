"""
Advanced Inventory Management API
- Categories
- Suppliers
- Stock Adjustments
- Purchase Orders
- Low Stock Alerts
- Bulk Import/Export
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required
from models_inventory_advanced import Category, Supplier, StockAdjustment, PurchaseOrder, PurchaseOrderItem
from models import Item
from datetime import datetime
from sqlalchemy import or_, func, desc
import csv
import io

inventory_advanced_bp = Blueprint('inventory_advanced', __name__)


# ============================================================================
# CATEGORIES
# ============================================================================

@inventory_advanced_bp.route('/categories', methods=['GET'])
@jwt_required()
def list_categories():
    """Get all categories"""
    try:
        tenant_id = g.tenant_id

        categories = g.db.query(Category).filter_by(
            tenant_id=tenant_id,
            is_active=True
        ).order_by(Category.sort_order, Category.name).all()

        return jsonify({
            'categories': [{
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'slug': cat.slug,
                'parent_id': cat.parent_id,
                'sort_order': cat.sort_order,
                'color': cat.color,
                'icon': cat.icon,
                'image_url': cat.image_url,
            } for cat in categories]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_advanced_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_category():
    """Create new category"""
    try:
        tenant_id = g.tenant_id
        data = request.json

        category = Category(
            tenant_id=tenant_id,
            name=data['name'],
            description=data.get('description'),
            slug=data.get('slug', data['name'].lower().replace(' ', '-')),
            parent_id=data.get('parent_id'),
            sort_order=data.get('sort_order', 0),
            color=data.get('color'),
            icon=data.get('icon'),
        )

        g.db.add(category)
        g.db.commit()

        return jsonify({
            'message': 'Category created',
            'category_id': category.id
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SUPPLIERS
# ============================================================================

@inventory_advanced_bp.route('/suppliers', methods=['GET'])
@jwt_required()
def list_suppliers():
    """Get all suppliers"""
    try:
        tenant_id = g.tenant_id

        suppliers = g.db.query(Supplier).filter_by(
            tenant_id=tenant_id,
            is_active=True
        ).order_by(Supplier.name).all()

        return jsonify({
            'suppliers': [{
                'id': sup.id,
                'name': sup.name,
                'company_name': sup.company_name,
                'code': sup.code,
                'contact_person': sup.contact_person,
                'email': sup.email,
                'phone': sup.phone,
                'payment_terms': sup.payment_terms,
                'lead_time_days': sup.lead_time_days,
                'rating': sup.rating,
            } for sup in suppliers]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_advanced_bp.route('/suppliers', methods=['POST'])
@jwt_required()
def create_supplier():
    """Create new supplier"""
    try:
        tenant_id = g.tenant_id
        data = request.json

        supplier = Supplier(
            tenant_id=tenant_id,
            name=data['name'],
            company_name=data.get('company_name'),
            code=data.get('code'),
            contact_person=data.get('contact_person'),
            email=data.get('email'),
            phone=data.get('phone'),
            website=data.get('website'),
            address_line1=data.get('address_line1'),
            city=data.get('city'),
            state=data.get('state'),
            postal_code=data.get('postal_code'),
            country=data.get('country'),
            payment_terms=data.get('payment_terms'),
            minimum_order_value=data.get('minimum_order_value'),
            lead_time_days=data.get('lead_time_days'),
            notes=data.get('notes'),
        )

        g.db.add(supplier)
        g.db.commit()

        return jsonify({
            'message': 'Supplier created',
            'supplier_id': supplier.id
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STOCK ADJUSTMENTS
# ============================================================================

@inventory_advanced_bp.route('/stock-adjustments', methods=['GET'])
@jwt_required()
def list_stock_adjustments():
    """Get stock adjustment history"""
    try:
        tenant_id = g.tenant_id
        item_id = request.args.get('item_id')
        limit = int(request.args.get('limit', 100))

        query = g.db.query(StockAdjustment).filter_by(tenant_id=tenant_id)

        if item_id:
            query = query.filter_by(item_id=item_id)

        adjustments = query.order_by(
            desc(StockAdjustment.adjustment_date)
        ).limit(limit).all()

        return jsonify({
            'adjustments': [{
                'id': adj.id,
                'item_id': adj.item_id,
                'adjustment_type': adj.adjustment_type,
                'quantity_before': adj.quantity_before,
                'quantity_change': adj.quantity_change,
                'quantity_after': adj.quantity_after,
                'unit_cost': float(adj.unit_cost) if adj.unit_cost else None,
                'total_cost': float(adj.total_cost) if adj.total_cost else None,
                'reference_number': adj.reference_number,
                'reason': adj.reason,
                'adjustment_date': adj.adjustment_date.isoformat(),
            } for adj in adjustments]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_advanced_bp.route('/stock-adjustments', methods=['POST'])
@jwt_required()
def create_stock_adjustment():
    """Create manual stock adjustment"""
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        data = request.json

        # Get item
        item = g.db.query(Item).filter_by(
            id=data['item_id'],
            tenant_id=tenant_id
        ).first()

        if not item:
            return jsonify({'error': 'Item not found'}), 404

        # Create adjustment
        quantity_before = item.stock_on_hand
        quantity_change = int(data['quantity_change'])
        quantity_after = quantity_before + quantity_change

        adjustment = StockAdjustment(
            tenant_id=tenant_id,
            item_id=item.id,
            adjustment_type=data.get('adjustment_type', 'other'),
            quantity_before=quantity_before,
            quantity_change=quantity_change,
            quantity_after=quantity_after,
            unit_cost=data.get('unit_cost'),
            total_cost=data.get('unit_cost', 0) * abs(quantity_change) if data.get('unit_cost') else None,
            reference_number=data.get('reference_number'),
            reference_type='manual',
            adjusted_by_user_id=user_id,
            reason=data.get('reason'),
            notes=data.get('notes'),
        )

        # Update item stock
        item.stock_on_hand = quantity_after

        g.db.add(adjustment)
        g.db.commit()

        return jsonify({
            'message': 'Stock adjusted',
            'adjustment_id': adjustment.id,
            'new_stock': quantity_after
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PURCHASE ORDERS
# ============================================================================

@inventory_advanced_bp.route('/purchase-orders', methods=['GET'])
@jwt_required()
def list_purchase_orders():
    """Get all purchase orders"""
    try:
        tenant_id = g.tenant_id
        status = request.args.get('status')

        query = g.db.query(PurchaseOrder).filter_by(tenant_id=tenant_id)

        if status:
            query = query.filter_by(status=status)

        pos = query.order_by(desc(PurchaseOrder.po_date)).all()

        return jsonify({
            'purchase_orders': [{
                'id': po.id,
                'po_number': po.po_number,
                'supplier_id': po.supplier_id,
                'po_date': po.po_date.isoformat(),
                'expected_delivery_date': po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
                'status': po.status,
                'total_amount': float(po.total_amount),
                'payment_status': po.payment_status,
            } for po in pos]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_advanced_bp.route('/purchase-orders', methods=['POST'])
@jwt_required()
def create_purchase_order():
    """Create new purchase order"""
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        data = request.json

        # Generate PO number
        po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create PO
        po = PurchaseOrder(
            tenant_id=tenant_id,
            supplier_id=data.get('supplier_id'),
            po_number=po_number,
            expected_delivery_date=datetime.fromisoformat(data['expected_delivery_date']) if data.get('expected_delivery_date') else None,
            payment_terms=data.get('payment_terms'),
            notes=data.get('notes'),
            created_by_user_id=user_id,
        )

        # Add line items
        subtotal = 0
        for line_data in data.get('line_items', []):
            item = g.db.query(Item).filter_by(
                id=line_data['item_id'],
                tenant_id=tenant_id
            ).first()

            if not item:
                continue

            line_total = float(line_data['unit_cost']) * int(line_data['quantity_ordered'])
            subtotal += line_total

            po_item = PurchaseOrderItem(
                purchase_order=po,
                item_id=item.id,
                sku=item.sku,
                item_name=item.name,
                quantity_ordered=line_data['quantity_ordered'],
                unit_cost=line_data['unit_cost'],
                line_total=line_total,
            )
            g.db.add(po_item)

        # Calculate totals
        tax_amount = subtotal * 0.0725 if data.get('include_tax') else 0
        shipping_cost = float(data.get('shipping_cost', 0))
        total_amount = subtotal + tax_amount + shipping_cost

        po.subtotal = subtotal
        po.tax_amount = tax_amount
        po.shipping_cost = shipping_cost
        po.total_amount = total_amount

        g.db.add(po)
        g.db.commit()

        return jsonify({
            'message': 'Purchase order created',
            'po_id': po.id,
            'po_number': po.po_number
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# LOW STOCK ALERTS
# ============================================================================

@inventory_advanced_bp.route('/low-stock', methods=['GET'])
@jwt_required()
def get_low_stock_items():
    """Get items below reorder point"""
    try:
        tenant_id = g.tenant_id

        low_stock_items = g.db.query(Item).filter(
            Item.tenant_id == tenant_id,
            Item.is_active == True,
            Item.stock_on_hand <= Item.reorder_point
        ).order_by(Item.stock_on_hand).all()

        return jsonify({
            'low_stock_items': [{
                'id': item.id,
                'sku': item.sku,
                'name': item.name,
                'stock_on_hand': item.stock_on_hand,
                'reorder_point': item.reorder_point,
                'reorder_quantity': item.reorder_quantity,
                'supplier_name': item.supplier_name,
                'sell_price': float(item.sell_price),
            } for item in low_stock_items],
            'total_count': len(low_stock_items)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# BULK IMPORT/EXPORT
# ============================================================================

@inventory_advanced_bp.route('/inventory/export', methods=['GET'])
@jwt_required()
def export_inventory():
    """Export inventory to CSV"""
    try:
        tenant_id = g.tenant_id

        items = g.db.query(Item).filter_by(
            tenant_id=tenant_id,
            is_active=True
        ).all()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'SKU', 'Name', 'Description', 'Category',
            'Cost Price', 'Sell Price', 'Stock On Hand',
            'Reorder Point', 'Reorder Quantity', 'Supplier'
        ])

        # Data
        for item in items:
            writer.writerow([
                item.sku,
                item.name,
                item.description or '',
                item.category or '',
                float(item.cost_price) if item.cost_price else 0,
                float(item.sell_price),
                item.stock_on_hand,
                item.reorder_point,
                item.reorder_quantity or 0,
                item.supplier_name or '',
            ])

        csv_data = output.getvalue()

        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=inventory_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        }

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_advanced_bp.route('/inventory/import', methods=['POST'])
@jwt_required()
def import_inventory():
    """Import inventory from CSV"""
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id

        # Get CSV file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        csv_data = file.read().decode('utf-8')

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))

        imported = 0
        updated = 0
        errors = []

        for row in reader:
            try:
                # Check if item exists
                existing_item = g.db.query(Item).filter_by(
                    tenant_id=tenant_id,
                    sku=row['SKU']
                ).first()

                if existing_item:
                    # Update existing
                    existing_item.name = row['Name']
                    existing_item.description = row.get('Description')
                    existing_item.category = row.get('Category')
                    existing_item.cost_price = float(row.get('Cost Price', 0)) if row.get('Cost Price') else None
                    existing_item.sell_price = float(row['Sell Price'])
                    existing_item.stock_on_hand = int(row.get('Stock On Hand', 0))
                    existing_item.reorder_point = int(row.get('Reorder Point', 0))
                    existing_item.reorder_quantity = int(row.get('Reorder Quantity', 0)) if row.get('Reorder Quantity') else None
                    existing_item.supplier_name = row.get('Supplier')
                    updated += 1
                else:
                    # Create new
                    item = Item(
                        tenant_id=tenant_id,
                        sku=row['SKU'],
                        name=row['Name'],
                        description=row.get('Description'),
                        category=row.get('Category'),
                        cost_price=float(row.get('Cost Price', 0)) if row.get('Cost Price') else None,
                        sell_price=float(row['Sell Price']),
                        stock_on_hand=int(row.get('Stock On Hand', 0)),
                        reorder_point=int(row.get('Reorder Point', 0)),
                        reorder_quantity=int(row.get('Reorder Quantity', 0)) if row.get('Reorder Quantity') else None,
                        supplier_name=row.get('Supplier'),
                    )
                    g.db.add(item)
                    imported += 1

            except Exception as e:
                errors.append(f"Row {reader.line_num}: {str(e)}")

        g.db.commit()

        return jsonify({
            'message': 'Import completed',
            'imported': imported,
            'updated': updated,
            'errors': errors
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({'error': str(e)}), 500
