"""
Sales API
- Create transactions
- List transactions
- Receipt generation
- Stripe payment processing with platform fees
- GMV tracking for usage-based billing
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from models import Transaction, TransactionItem, Item, Tenant
from services.gmv_tracker import GMVTracker
from datetime import datetime, timedelta
import uuid
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

sales_bp = Blueprint("sales", __name__)


def generate_transaction_number():
    """Generate unique transaction number"""
    now = datetime.utcnow()
    return f"TXN-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"


@sales_bp.route("", methods=["POST"])
@jwt_required()
def create_transaction():
    """
    Create new sales transaction
    Decrements inventory stock automatically
    """
    try:
        tenant_id = g.tenant_id
        user_id = g.user_id
        data = request.json

        # Validate required fields
        if not data.get("items") or len(data["items"]) == 0:
            return jsonify({"error": "At least one item is required"}), 400

        if not data.get("payment_method"):
            return jsonify({"error": "Payment method is required"}), 400

        # Calculate totals
        subtotal = 0
        line_items = []

        for item_data in data["items"]:
            # Get item from database
            item = g.db.query(Item).filter_by(
                id=item_data["item_id"],
                tenant_id=tenant_id
            ).first()

            if not item:
                return jsonify({"error": f"Item not found: {item_data['item_id']}"}), 404

            # Check stock
            quantity = item_data["quantity"]
            if item.stock_on_hand < quantity:
                return jsonify({
                    "error": f"Insufficient stock for {item.name}. Available: {item.stock_on_hand}"
                }), 400

            # Calculate line total
            unit_price = item_data.get("price", item.sell_price)
            discount = item_data.get("discount", 0)
            line_total = (float(unit_price) * quantity) - float(discount)

            subtotal += line_total

            line_items.append({
                "item": item,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount,
                "line_total": line_total
            })

        # Calculate tax
        tax_amount = data.get("tax_amount", subtotal * 0.0725)  # Default 7.25%
        discount_amount = data.get("discount_amount", 0)
        total_amount = subtotal + float(tax_amount) - float(discount_amount)

        # Create transaction
        transaction = Transaction(
            tenant_id=tenant_id,
            transaction_number=generate_transaction_number(),
            transaction_date=datetime.utcnow(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            payment_method=data["payment_method"],
            payment_status="completed",
            cashier_id=user_id,
            customer_name=data.get("customer_name"),
            customer_email=data.get("customer_email"),
            customer_phone=data.get("customer_phone"),
            notes=data.get("notes")
        )
        g.db.add(transaction)
        g.db.flush()  # Get transaction ID

        # Create line items and update stock with FIFO allocation
        from services.fifo_calculator import FIFOCalculator

        for line_data in line_items:
            item = line_data["item"]
            quantity = line_data["quantity"]

            # Try FIFO allocation first
            allocations, total_cogs, fifo_success = FIFOCalculator.allocate_sale(
                db=g.db,
                tenant_id=tenant_id,
                item_id=item.id,
                quantity_needed=quantity
            )

            # Use FIFO cost if available, otherwise fall back to item cost_price
            if fifo_success:
                actual_unit_cost = total_cogs / quantity
                # Apply lot allocation
                FIFOCalculator.apply_allocation(g.db, allocations)
            else:
                # Fallback to simple cost price if no lots
                actual_unit_cost = float(item.cost_price or 0)

            # Create line item with actual FIFO cost
            line_item = TransactionItem(
                transaction_id=transaction.id,
                item_id=item.id,
                sku=item.sku,
                item_name=item.name,
                unit_price=line_data["unit_price"],
                quantity=quantity,
                discount_amount=line_data["discount"],
                line_total=line_data["line_total"],
                unit_cost=actual_unit_cost
            )
            g.db.add(line_item)
            g.db.flush()  # Get line_item ID for lot tracking

            # Record which lots were used (FIFO audit trail)
            if fifo_success:
                FIFOCalculator.record_transaction_lots(g.db, line_item.id, allocations)

            # Decrement stock (lots already decremented if FIFO used)
            if not fifo_success:
                item.stock_on_hand -= quantity

            # Ensure item is added to session
            g.db.add(item)

        # Capture transaction data before commit
        txn_data = {
            "id": transaction.id,
            "transaction_number": transaction.transaction_number,
            "total_amount": float(transaction.total_amount),
            "payment_method": transaction.payment_method
        }

        g.db.commit()

        # Track GMV for usage-based billing (do this after commit)
        try:
            GMVTracker.record_sale(tenant_id, total_amount)
        except Exception as gmv_error:
            # Log but don't fail the transaction
            print(f"GMV tracking error: {gmv_error}")

        return jsonify({
            "message": "Transaction created successfully",
            "transaction": txn_data
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@sales_bp.route("/process-card-payment", methods=["POST"])
@jwt_required()
def process_card_payment():
    """
    Process credit card payment through Stripe with platform fees
    This is where YOU make money! 💰
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        # Get tenant
        tenant = g.db.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        # Check if tenant has Stripe Connect account
        if not tenant.stripe_account_id or tenant.stripe_account_status != "active":
            return jsonify({
                "error": "Stripe account not connected. Please connect your Stripe account in Settings."
            }), 403

        # Get amount and payment method ID from frontend
        amount = data.get("amount")  # In dollars
        payment_method_id = data.get("payment_method_id")  # From Stripe.js

        if not amount or not payment_method_id:
            return jsonify({"error": "Amount and payment method required"}), 400

        # Calculate platform fee
        platform_fee_percent = tenant.get_platform_fee_percent()
        amount_cents = int(float(amount) * 100)  # Convert to cents
        platform_fee_cents = int(amount_cents * (platform_fee_percent / 100))

        # Create payment intent with platform fee
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                payment_method=payment_method_id,
                confirm=True,
                application_fee_amount=platform_fee_cents,  # YOUR PROFIT!
                stripe_account=tenant.stripe_account_id,  # Merchant's account
                description=f"POS Transaction - {tenant.business_name}",
                metadata={
                    "tenant_id": tenant_id,
                    "platform_fee_percent": str(platform_fee_percent)
                }
            )

            # Calculate fee breakdown
            stripe_fee = amount_cents * 0.029 + 30  # Stripe's ~2.9% + 30¢
            merchant_receives = amount_cents - platform_fee_cents - int(stripe_fee)

            return jsonify({
                "success": True,
                "payment_intent_id": payment_intent.id,
                "status": payment_intent.status,
                "amount_charged": amount,
                "breakdown": {
                    "total": float(amount),
                    "stripe_fee": round(stripe_fee / 100, 2),
                    "platform_fee": round(platform_fee_cents / 100, 2),
                    "merchant_receives": round(merchant_receives / 100, 2),
                    "platform_fee_percent": platform_fee_percent
                }
            }), 200

        except stripe.error.CardError as e:
            return jsonify({
                "error": "Card declined",
                "message": e.user_message
            }), 400

        except stripe.error.StripeError as e:
            return jsonify({"error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sales_bp.route("", methods=["GET"])
@jwt_required()
def list_transactions():
    """
    List transactions for tenant
    Supports date filtering and pagination
    """
    try:
        tenant_id = g.tenant_id

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        # Date filters
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        # Build query
        query = g.db.query(Transaction).filter_by(tenant_id=tenant_id)

        if start_date:
            query = query.filter(Transaction.transaction_date >= datetime.fromisoformat(start_date))

        if end_date:
            query = query.filter(Transaction.transaction_date <= datetime.fromisoformat(end_date))

        # Order by date (newest first)
        query = query.order_by(Transaction.transaction_date.desc())

        # Paginate
        offset = (page - 1) * per_page
        total = query.count()
        transactions = query.limit(per_page).offset(offset).all()

        return jsonify({
            "transactions": [{
                "id": txn.id,
                "transaction_number": txn.transaction_number,
                "transaction_date": txn.transaction_date.isoformat(),
                "total_amount": float(txn.total_amount),
                "payment_method": txn.payment_method,
                "customer_name": txn.customer_name,
                "item_count": len(txn.line_items)
            } for txn in transactions],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sales_bp.route("/<transaction_id>", methods=["GET"])
@jwt_required()
def get_transaction(transaction_id):
    """Get transaction details with line items"""
    try:
        tenant_id = g.tenant_id
        transaction = g.db.query(Transaction).filter_by(
            id=transaction_id,
            tenant_id=tenant_id
        ).first()

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        return jsonify({
            "transaction": {
                "id": transaction.id,
                "transaction_number": transaction.transaction_number,
                "transaction_date": transaction.transaction_date.isoformat(),
                "subtotal": float(transaction.subtotal),
                "tax_amount": float(transaction.tax_amount),
                "discount_amount": float(transaction.discount_amount),
                "total_amount": float(transaction.total_amount),
                "payment_method": transaction.payment_method,
                "payment_status": transaction.payment_status,
                "customer_name": transaction.customer_name,
                "customer_email": transaction.customer_email,
                "customer_phone": transaction.customer_phone,
                "notes": transaction.notes,
                "items": [{
                    "sku": item.sku,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "discount_amount": float(item.discount_amount),
                    "line_total": float(item.line_total)
                } for item in transaction.line_items]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
