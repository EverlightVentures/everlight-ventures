"""
OnyxPOS Database Models
Multi-tenant SaaS architecture with tenant isolation
"""
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime,
    Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import bcrypt

Base = declarative_base()


def generate_uuid():
    """Generate UUID as string"""
    return str(uuid.uuid4())


class Tenant(Base):
    """Business/Organization - Top level entity"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Business Info
    business_name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False, index=True)
    owner_email = Column(String(255), nullable=False)

    # Subscription
    plan_tier = Column(
        String(50),
        default="starter",
        nullable=False
    )
    subscription_status = Column(
        String(50),
        default="trial",
        nullable=False
    )
    stripe_customer_id = Column(String(255), index=True)
    stripe_subscription_id = Column(String(255))
    trial_ends_at = Column(DateTime)
    current_period_end = Column(DateTime)

    # GMV (Gross Merchandise Value) tracking for usage-based fees
    gmv_current_month = Column(Numeric(12, 2), default=0)  # Total sales volume this month
    gmv_last_month = Column(Numeric(12, 2), default=0)
    usage_fee_current_month = Column(Numeric(10, 2), default=0)  # Calculated usage fee
    last_gmv_reset = Column(DateTime)  # When GMV was last reset (monthly)

    # Stripe Connect (for platform fees)
    stripe_account_id = Column(String(255), index=True)  # Connected Account ID
    stripe_account_status = Column(String(50))  # pending, active, rejected
    platform_fee_percent = Column(Numeric(5, 2))  # Platform fee % (e.g., 2.50 for 2.5%)

    # Gusto Integration (self-service payroll)
    gusto_api_token = Column(Text)  # Encrypted API token
    gusto_company_uuid = Column(String(255))  # Gusto company UUID
    gusto_status = Column(String(50))  # not_connected, pending_verification, connected, disconnected
    gusto_connected_at = Column(DateTime)

    # Settings
    timezone = Column(String(100), default="America/Los_Angeles")
    currency = Column(String(10), default="USD")
    tax_rate = Column(Numeric(5, 4), default=0.0725)
    business_phone = Column(String(50))
    business_address = Column(Text)
    logo_url = Column(Text)

    # Usage tracking
    transaction_count_current_month = Column(Integer, default=0)
    user_count = Column(Integer, default=0)
    location_count = Column(Integer, default=1)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="tenant", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="tenant", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            plan_tier.in_(["core", "growth", "prime", "onyxpos_core", "onyxpayroll", "onyxos_bundle", "starter", "scale", "starter_commission", "pro_commission"]),
            name="valid_plan_tier"
        ),
        CheckConstraint(
            subscription_status.in_(["trial", "active", "past_due", "canceled", "suspended"]),
            name="valid_subscription_status"
        ),
    )

    def __repr__(self):
        return f"<Tenant {self.business_name} ({self.subdomain})>"

    @property
    def is_trial(self):
        """Check if tenant is on trial"""
        return self.subscription_status == "trial"

    @property
    def is_active(self):
        """Check if tenant subscription is active"""
        return self.subscription_status in ["trial", "active"]

    @property
    def trial_days_remaining(self):
        """Calculate remaining trial days"""
        if not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)

    def get_platform_fee_percent(self):
        """
        Get GMV-based fee percentage based on plan tier

        Commission-Based Pricing (New Model):
        - starter_commission: 5% commission + $29.99/mo
        - pro_commission: 1% commission + $99.99/mo

        Flat Pricing (Legacy):
        - onyxpos_core, onyxpayroll, onyxos_bundle: No commission
        """
        if self.platform_fee_percent is not None:
            return float(self.platform_fee_percent)

        # Commission-based tiers
        commission_map = {
            "starter_commission": 5.00,  # 5% of GMV
            "pro_commission": 1.00,      # 1% of GMV
        }

        if self.plan_tier in commission_map:
            return commission_map[self.plan_tier]

        # Flat pricing tiers - no commission
        return 0.00

    def get_variable_fee_cap(self):
        """Get variable fee cap - OnyxOS uses flat pricing"""
        return 0.00  # No variable fees in new pricing model

    def get_monthly_subscription_fee(self):
        """Get monthly subscription fee based on plan tier"""
        fee_map = {
            # New OnyxPOS Pricing (Dec 2025)
            "core": 119.00,      # Core: $119/mo + platform fees
            "growth": 249.00,    # Growth: $249/mo + platform fees
            "prime": 399.00,     # Prime: $399/mo + platform fees

            # Commission-Based Pricing (Legacy)
            "starter_commission": 29.99,
            "pro_commission": 99.99,

            # Flat Pricing (Legacy)
            "onyxpos_core": 249.00,
            "onyxpayroll": 149.00,
            "onyxos_bundle": 400.00,

            # Legacy tiers for backward compatibility
            "starter": 119.00,   # Map to core
            "scale": 399.00      # Map to prime
        }
        return fee_map.get(self.plan_tier, 119.00)  # Default to core pricing

    def calculate_usage_fee(self, gmv_amount=None):
        """
        Calculate platform fee based on tiered GMV structure

        Tiered Platform Fee:
        - 10% on first $10,000
        - 5% on $10,001 to $50,000
        - 1% on everything over $50,000
        - Minimum $1,000/month platform fee
        """
        gmv = gmv_amount if gmv_amount is not None else float(self.gmv_current_month or 0)

        # Legacy commission-based tiers use simple percentage
        if self.plan_tier in ["starter_commission", "pro_commission"]:
            fee_percent = self.get_platform_fee_percent()
            usage_fee = gmv * (fee_percent / 100)
            cap = self.get_variable_fee_cap()
            if cap > 0:
                usage_fee = min(usage_fee, cap)
            return round(usage_fee, 2)

        # New tiered platform fee calculation
        platform_fee = 0.0

        # First $10k at 10%
        if gmv > 0:
            tier1 = min(gmv, 10000)
            platform_fee += tier1 * 0.10

        # Next $40k ($10k-$50k) at 5%
        if gmv > 10000:
            tier2 = min(gmv - 10000, 40000)
            platform_fee += tier2 * 0.05

        # Everything over $50k at 1%
        if gmv > 50000:
            tier3 = gmv - 50000
            platform_fee += tier3 * 0.01

        # Apply minimum $1,000/month platform fee
        platform_fee = max(platform_fee, 1000.00)

        return round(platform_fee, 2)

    def get_total_monthly_cost(self):
        """Get total monthly cost (subscription + usage fee)"""
        return self.get_monthly_subscription_fee() + self.calculate_usage_fee()

    def get_device_limit(self):
        """
        Get device limit based on plan tier

        Returns:
            int: Maximum number of devices allowed (0 = unlimited)
        """
        device_limits = {
            # New pricing tiers
            "core": 2,         # 2 devices, team of 6
            "growth": 6,       # 6 devices, team of 15
            "prime": 0,        # Unlimited devices

            # Legacy tiers
            "starter": 2,
            "starter_commission": 2,
            "pro_commission": 6,
            "onyxpos_core": 6,
            "onyxos_bundle": 0,
            "scale": 0
        }
        return device_limits.get(self.plan_tier, 2)

    def get_team_size_limit(self):
        """
        Get team size limit based on plan tier

        Returns:
            int: Maximum number of team members (0 = unlimited)
        """
        team_limits = {
            # New pricing tiers
            "core": 6,         # Team of 6
            "growth": 15,      # Team of 15
            "prime": 0,        # Unlimited team

            # Legacy tiers
            "starter": 6,
            "starter_commission": 6,
            "pro_commission": 15,
            "onyxpos_core": 15,
            "onyxos_bundle": 0,
            "scale": 0
        }
        return team_limits.get(self.plan_tier, 6)

    def get_breakeven_gmv(self, compare_to_tier=None):
        """Calculate GMV break-even point vs another tier"""
        if not compare_to_tier:
            return None

        # Map of tier order
        tier_order = ["starter", "growth", "scale"]
        if self.plan_tier not in tier_order or compare_to_tier not in tier_order:
            return None

        current_idx = tier_order.index(self.plan_tier)
        compare_idx = tier_order.index(compare_to_tier)

        if compare_idx <= current_idx:
            return None  # Only compare to higher tiers

        # Calculate break-even: monthly_current + gmv * fee_current = monthly_compare + gmv * fee_compare
        # Solving for gmv: (monthly_compare - monthly_current) / (fee_current - fee_compare)

        fee_current = self.get_platform_fee_percent() / 100

        temp_tenant = Tenant(plan_tier=compare_to_tier)
        monthly_compare = temp_tenant.get_monthly_subscription_fee()
        fee_compare = temp_tenant.get_platform_fee_percent() / 100

        monthly_current = self.get_monthly_subscription_fee()

        if fee_current == fee_compare:
            return None  # No break-even if fees are the same

        breakeven = (monthly_compare - monthly_current) / (fee_current - fee_compare)
        return max(0, breakeven) if breakeven > 0 else None


class User(Base):
    """Users (Employees) within a tenant"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Authentication
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    pin_code = Column(String(10))  # Quick POS login

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50))

    # Role & Permissions
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)

    # Employment
    hourly_rate = Column(Numeric(10, 2))
    salary = Column(Numeric(10, 2))
    pay_type = Column(String(20))  # hourly, salary

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            role.in_(["owner", "manager", "cashier", "laborer"]),
            name="valid_role"
        ),
        Index("idx_user_email_tenant", "tenant_id", "email", unique=True),
    )

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password):
        """Verify password"""
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )

    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"


class Item(Base):
    """Inventory Items"""
    __tablename__ = "items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Identification
    sku = Column(String(100), nullable=False)
    barcode = Column(String(100))
    qr_code = Column(Text)

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))

    # Pricing
    cost_price = Column(Numeric(10, 2))
    sell_price = Column(Numeric(10, 2), nullable=False)
    markup_percentage = Column(Numeric(5, 2))

    # Stock
    stock_on_hand = Column(Integer, default=0)
    reorder_point = Column(Integer, default=0)
    reorder_quantity = Column(Integer)

    # Supplier
    supplier_name = Column(String(255))
    supplier_sku = Column(String(100))

    # Metadata
    is_active = Column(Boolean, default=True)
    image_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", back_populates="items")

    # Constraints
    __table_args__ = (
        Index("idx_item_sku_tenant", "tenant_id", "sku", unique=True),
        Index("idx_item_barcode_tenant", "tenant_id", "barcode"),
        Index("idx_item_category_tenant", "tenant_id", "category"),
    )

    def __repr__(self):
        return f"<Item {self.sku}: {self.name}>"

    @property
    def is_low_stock(self):
        """Check if item is below reorder point"""
        return self.stock_on_hand <= self.reorder_point

    @property
    def profit_margin(self):
        """Calculate profit margin"""
        if not self.cost_price or self.cost_price == 0:
            return 0
        return ((self.sell_price - self.cost_price) / self.cost_price) * 100


class Transaction(Base):
    """Sales Transactions"""
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transaction Details
    transaction_number = Column(String(100), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)

    # Payment
    payment_method = Column(String(50), nullable=False)
    payment_status = Column(String(50), default="completed")

    # Crypto payment details (future)
    crypto_currency = Column(String(10))
    crypto_amount = Column(Numeric(18, 8))
    crypto_tx_hash = Column(String(255))
    crypto_exchange_rate = Column(Numeric(18, 2))

    # Customer info (optional)
    customer_name = Column(String(255))
    customer_email = Column(String(255))
    customer_phone = Column(String(50))

    # Staff
    cashier_id = Column(String(36), ForeignKey("users.id"))

    # Receipt
    receipt_printed = Column(Boolean, default=False)
    receipt_emailed = Column(Boolean, default=False)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="transactions")
    line_items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            payment_method.in_(["cash", "card", "crypto", "other"]),
            name="valid_payment_method"
        ),
        CheckConstraint(
            payment_status.in_(["pending", "completed", "refunded"]),
            name="valid_payment_status"
        ),
        Index("idx_transaction_number_tenant", "tenant_id", "transaction_number", unique=True),
        Index("idx_transaction_date_tenant", "tenant_id", "transaction_date"),
    )

    def __repr__(self):
        return f"<Transaction {self.transaction_number}: ${self.total_amount}>"


class TransactionItem(Base):
    """Line items within a transaction"""
    __tablename__ = "transaction_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id"))

    # Item details (snapshot at time of sale)
    sku = Column(String(100), nullable=False)
    item_name = Column(String(255), nullable=False)

    # Pricing
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    line_total = Column(Numeric(10, 2), nullable=False)

    # Cost (for profit calculation)
    unit_cost = Column(Numeric(10, 2))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="line_items")

    def __repr__(self):
        return f"<TransactionItem {self.sku} x{self.quantity}>"

    @property
    def profit(self):
        """Calculate profit for this line item"""
        if not self.unit_cost:
            return 0
        return (self.unit_price - self.unit_cost) * self.quantity


class TimeClockEntry(Base):
    """Employee time clock entries"""
    __tablename__ = "time_clock_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Clock times
    clock_in = Column(DateTime, nullable=False, index=True)
    clock_out = Column(DateTime)

    # Break tracking
    break_start = Column(DateTime)
    break_end = Column(DateTime)
    break_minutes = Column(Numeric(10, 2), default=0)

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index("idx_timeclock_user_tenant", "tenant_id", "user_id"),
        Index("idx_timeclock_date_tenant", "tenant_id", "clock_in"),
    )

    def __repr__(self):
        return f"<TimeClockEntry {self.user_id} {self.clock_in}>"


class Schedule(Base):
    """Employee work schedule"""
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Schedule details
    date = Column(DateTime, nullable=False, index=True)
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)    # HH:MM format

    # Additional info
    notes = Column(Text)
    is_confirmed = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        Index("idx_schedule_date_tenant", "tenant_id", "date"),
        Index("idx_schedule_employee_tenant", "tenant_id", "employee_id"),
    )

    def __repr__(self):
        return f"<Schedule {self.employee_id} {self.date} {self.start_time}-{self.end_time}>"


class Task(Base):
    """Asana-style task management system"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Task details
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="to_do", nullable=False)  # to_do, in_progress, completed, blocked
    priority = Column(String(20), default="medium")  # low, medium, high, urgent

    # Assignment
    assigned_to = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    # Dates
    due_date = Column(DateTime, index=True)
    start_date = Column(DateTime)
    completed_at = Column(DateTime)

    # Organization
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True)  # For subtasks
    tags = Column(Text)  # Comma-separated tags

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    # Relationships
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")
    creator = relationship("User", foreign_keys=[created_by], backref="created_tasks")
    subtasks = relationship("Task", backref="parent_task", remote_side=[id], cascade="all, delete-orphan", single_parent=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_(["to_do", "in_progress", "completed", "blocked", "cancelled"]),
            name="valid_task_status"
        ),
        CheckConstraint(
            priority.in_(["low", "medium", "high", "urgent"]),
            name="valid_task_priority"
        ),
        Index("idx_task_tenant_status", "tenant_id", "status"),
        Index("idx_task_assigned_user", "tenant_id", "assigned_to"),
        Index("idx_task_due_date", "tenant_id", "due_date"),
    )

    def __repr__(self):
        return f"<Task {self.title} ({self.status})>"


class Project(Base):
    """Project container for grouping tasks"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Project details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7))  # Hex color code
    status = Column(String(50), default="active")  # active, on_hold, completed, archived

    # Owner
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Dates
    start_date = Column(DateTime)
    target_end_date = Column(DateTime)
    completed_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    owner = relationship("User", backref="owned_projects")

    # Constraints
    __table_args__ = (
        Index("idx_project_tenant", "tenant_id"),
    )

    def __repr__(self):
        return f"<Project {self.name}>"


# Add project relationship to Task
Task.project = relationship("Project", back_populates="tasks")


class TaskComment(Base):
    """Comments on tasks"""
    __tablename__ = "task_comments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Comment content
    content = Column(Text, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("Task", backref="comments")
    user = relationship("User", backref="task_comments")

    def __repr__(self):
        return f"<TaskComment {self.task_id}>"


class DeviceSession(Base):
    """Track device sessions for multi-device access control"""
    __tablename__ = "device_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Device identification
    device_id = Column(String(255), nullable=False, index=True)  # Unique device identifier
    device_name = Column(String(255))  # User-friendly name (e.g., "iPhone 12", "iPad Pro")
    device_type = Column(String(50))  # mobile, tablet, desktop, pos_terminal
    platform = Column(String(50))  # ios, android, web, windows, macos

    # Device fingerprint
    user_agent = Column(Text)
    ip_address = Column(String(50))
    fingerprint = Column(Text)  # Browser/device fingerprint hash

    # Session management
    is_active = Column(Boolean, default=True, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", backref="device_sessions")
    user = relationship("User", backref="device_sessions")

    # Constraints
    __table_args__ = (
        Index("idx_device_tenant_user", "tenant_id", "user_id"),
        Index("idx_device_active", "tenant_id", "is_active"),
    )

    def __repr__(self):
        return f"<DeviceSession {self.device_name} - {self.user_id}>"


class ChannelIntegration(Base):
    """Track third-party channel integrations (DoorDash, UberEats, etc.)"""
    __tablename__ = "channel_integrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Channel info
    channel = Column(String(50), nullable=False)  # doordash, ubereats, grubhub, instacart
    channel_display_name = Column(String(100))

    # OAuth credentials (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)

    # Channel-specific IDs
    merchant_id = Column(String(255))  # Channel's merchant/store ID
    store_id = Column(String(255))     # Channel's store ID

    # Connection status
    status = Column(String(50), default="pending")  # pending, active, disconnected, error
    is_active = Column(Boolean, default=True)

    # Menu sync
    last_menu_sync_at = Column(DateTime)
    menu_sync_enabled = Column(Boolean, default=True)

    # Order sync
    last_order_sync_at = Column(DateTime)
    order_sync_enabled = Column(Boolean, default=True)

    # Webhook
    webhook_secret = Column(String(255))  # For validating webhooks

    # Settings
    settings = Column(Text)  # JSON settings specific to each channel

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    connected_at = Column(DateTime)
    disconnected_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", backref="channel_integrations")

    # Constraints
    __table_args__ = (
        Index("idx_channel_tenant", "tenant_id", "channel"),
        CheckConstraint(
            channel.in_(["doordash", "ubereats", "grubhub", "instacart"]),
            name="valid_channel"
        ),
        CheckConstraint(
            status.in_(["pending", "active", "disconnected", "error"]),
            name="valid_integration_status"
        ),
    )

    def __repr__(self):
        return f"<ChannelIntegration {self.channel} - {self.tenant_id}>"


class ChannelOrder(Base):
    """Orders received from delivery channels"""
    __tablename__ = "channel_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_id = Column(String(36), ForeignKey("channel_integrations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Channel order details
    channel = Column(String(50), nullable=False)
    channel_order_id = Column(String(255), nullable=False, index=True)  # External order ID
    channel_order_number = Column(String(100))  # Human-readable order number

    # Order info
    customer_name = Column(String(255))
    customer_phone = Column(String(50))
    delivery_address = Column(Text)

    # Order status
    status = Column(String(50), default="pending")  # pending, confirmed, preparing, ready, picked_up, delivered, cancelled

    # Items (JSON)
    items = Column(Text, nullable=False)  # JSON array of order items

    # Pricing
    subtotal = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    delivery_fee = Column(Numeric(10, 2), default=0)
    service_fee = Column(Numeric(10, 2), default=0)
    tip = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)

    # Platform fees (what channel charges us)
    platform_commission = Column(Numeric(10, 2), default=0)  # DoorDash/UberEats commission
    platform_commission_percent = Column(Numeric(5, 2), default=0)
    net_payout = Column(Numeric(10, 2), default=0)  # What we actually receive

    # Delivery info
    scheduled_pickup_time = Column(DateTime)
    scheduled_delivery_time = Column(DateTime)
    actual_pickup_time = Column(DateTime)
    actual_delivery_time = Column(DateTime)

    # Internal transaction ID (if created in our system)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Raw webhook data
    raw_data = Column(Text)  # Store original webhook payload for debugging

    # Relationships
    tenant = relationship("Tenant", backref="channel_orders")
    integration = relationship("ChannelIntegration", backref="orders")

    # Constraints
    __table_args__ = (
        Index("idx_channel_order_tenant", "tenant_id", "channel_order_id"),
        Index("idx_channel_order_status", "tenant_id", "status"),
    )

    def __repr__(self):
        return f"<ChannelOrder {self.channel} - {self.channel_order_id}>"


# ============================================================================
# ADDITIONAL MODELS FOR ENHANCED FEATURES
# ============================================================================

class PayrollPeriod(Base):
    """Track payroll periods and when they've been processed"""
    __tablename__ = "payroll_periods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")
    total_amount = Column(Numeric(12, 2), default=0)
    total_hours = Column(Numeric(10, 2), default=0)
    run_date = Column(DateTime)
    run_by_user_id = Column(String(36), ForeignKey("users.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PayrollPeriod {self.period_start} to {self.period_end}: ${self.total_amount}>"
