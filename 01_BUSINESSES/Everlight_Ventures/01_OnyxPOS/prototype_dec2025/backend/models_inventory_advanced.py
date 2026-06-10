"""
Advanced Inventory Management Models
Categories, Suppliers, Stock Adjustments, Purchase Orders
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime,
    Text, ForeignKey, CheckConstraint, Index
)
from models import Base, generate_uuid
from sqlalchemy.orm import relationship


class Category(Base):
    """Product Categories with hierarchy support"""
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Category Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    slug = Column(String(255))  # URL-friendly name

    # Hierarchy
    parent_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"))

    # Display
    sort_order = Column(Integer, default=0)
    color = Column(String(50))  # Hex color code
    icon = Column(String(100))  # Icon identifier
    image_url = Column(Text)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="subcategories")

    # Constraints
    __table_args__ = (
        Index("idx_category_tenant", "tenant_id", "name"),
        Index("idx_category_slug_tenant", "tenant_id", "slug", unique=True),
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Supplier(Base):
    """Supplier/Vendor Management"""
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic Info
    name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    code = Column(String(100))  # Supplier code/ID

    # Contact
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))

    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))

    # Business Terms
    payment_terms = Column(String(100))  # e.g., "Net 30", "COD"
    minimum_order_value = Column(Numeric(10, 2))
    lead_time_days = Column(Integer)  # Days until delivery

    # Financial
    account_number = Column(String(100))
    tax_id = Column(String(100))

    # Status
    is_active = Column(Boolean, default=True)
    rating = Column(Integer)  # 1-5 star rating

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Constraints
    __table_args__ = (
        Index("idx_supplier_code_tenant", "tenant_id", "code", unique=True),
    )

    def __repr__(self):
        return f"<Supplier {self.name}>"


class StockAdjustment(Base):
    """Track all inventory stock changes"""
    __tablename__ = "stock_adjustments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # Adjustment Details
    adjustment_type = Column(String(50), nullable=False)  # purchase, sale, damage, theft, recount, return
    quantity_before = Column(Integer, nullable=False)
    quantity_change = Column(Integer, nullable=False)  # Can be negative
    quantity_after = Column(Integer, nullable=False)

    # Cost Impact
    unit_cost = Column(Numeric(10, 2))
    total_cost = Column(Numeric(10, 2))

    # Reference
    reference_number = Column(String(100))  # PO number, transaction ID, etc.
    reference_type = Column(String(50))  # purchase_order, transaction, manual

    # Who & When
    adjusted_by_user_id = Column(String(36), ForeignKey("users.id"))
    adjustment_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Reason
    reason = Column(String(255))
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            adjustment_type.in_([
                "purchase", "sale", "damage", "theft", "recount",
                "return", "transfer_in", "transfer_out", "other"
            ]),
            name="valid_adjustment_type"
        ),
        Index("idx_stock_adjustment_item", "tenant_id", "item_id"),
        Index("idx_stock_adjustment_date", "tenant_id", "adjustment_date"),
    )

    def __repr__(self):
        return f"<StockAdjustment {self.adjustment_type}: {self.quantity_change}>"


class PurchaseOrder(Base):
    """Purchase Orders from Suppliers"""
    __tablename__ = "purchase_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), index=True)

    # PO Details
    po_number = Column(String(100), nullable=False)
    po_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)

    # Status
    status = Column(String(50), default="draft", nullable=False)  # draft, sent, confirmed, received, canceled

    # Amounts
    subtotal = Column(Numeric(10, 2), default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    shipping_cost = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), default=0)

    # Payment
    payment_status = Column(String(50), default="unpaid")  # unpaid, partial, paid
    payment_method = Column(String(50))
    payment_terms = Column(String(100))

    # Created/Modified by
    created_by_user_id = Column(String(36), ForeignKey("users.id"))
    approved_by_user_id = Column(String(36), ForeignKey("users.id"))
    received_by_user_id = Column(String(36), ForeignKey("users.id"))

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Relationships
    line_items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_(["draft", "sent", "confirmed", "partial", "received", "canceled"]),
            name="valid_po_status"
        ),
        CheckConstraint(
            payment_status.in_(["unpaid", "partial", "paid"]),
            name="valid_payment_status"
        ),
        Index("idx_po_number_tenant", "tenant_id", "po_number", unique=True),
        Index("idx_po_status", "tenant_id", "status"),
    )

    def __repr__(self):
        return f"<PurchaseOrder {self.po_number}: ${self.total_amount}>"


class PurchaseOrderItem(Base):
    """Line items in a Purchase Order"""
    __tablename__ = "purchase_order_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    purchase_order_id = Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id"))

    # Item Details
    sku = Column(String(100), nullable=False)
    item_name = Column(String(255), nullable=False)

    # Quantities
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)

    # Pricing
    unit_cost = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="line_items")

    def __repr__(self):
        return f"<PurchaseOrderItem {self.sku} x{self.quantity_ordered}>"

    @property
    def quantity_pending(self):
        """Calculate quantity still pending"""
        return self.quantity_ordered - self.quantity_received


class InventoryLot(Base):
    """
    Inventory Lot Tracking for FIFO/COGS Calculation
    Tracks batches of inventory with specific costs
    """
    __tablename__ = "inventory_lots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # Lot Details
    lot_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_per_unit = Column(Numeric(10, 2), nullable=False)

    # Dates
    received_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiration_date = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index("idx_lots_tenant", "tenant_id"),
        Index("idx_lots_item", "item_id"),
        Index("idx_lots_item_received", "item_id", "received_date"),
    )

    def __repr__(self):
        return f"<InventoryLot {self.lot_number}: {self.quantity} units @ ${self.cost_per_unit}>"

    @property
    def total_cost(self):
        """Calculate total cost of this lot"""
        return float(self.quantity) * float(self.cost_per_unit)

    @property
    def is_expired(self):
        """Check if lot is expired"""
        if not self.expiration_date:
            return False
        return datetime.utcnow() > self.expiration_date


class TransactionItemLot(Base):
    """
    Junction table tracking which lots were used for each transaction item
    Enables complete FIFO/COGS audit trail
    """
    __tablename__ = "transaction_item_lots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_item_id = Column(String(36), ForeignKey("transaction_items.id", ondelete="CASCADE"), nullable=False, index=True)
    lot_id = Column(String(36), ForeignKey("inventory_lots.id"), nullable=False, index=True)

    # Allocation Details
    quantity_used = Column(Integer, nullable=False)
    cost_per_unit = Column(Numeric(10, 2), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        Index("idx_txn_item_lots", "transaction_item_id"),
        Index("idx_lot_allocations", "lot_id"),
    )

    def __repr__(self):
        return f"<TransactionItemLot: {self.quantity_used} units @ ${self.cost_per_unit}>"
