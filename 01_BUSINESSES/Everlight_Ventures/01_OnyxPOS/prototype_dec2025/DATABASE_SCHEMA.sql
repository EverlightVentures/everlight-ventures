-- =====================================================
-- OnyxPOS Multi-Tenant Database Schema
-- PostgreSQL 15+
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- CORE TENANT TABLES
-- =====================================================

-- Tenants (Business Accounts)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    owner_email VARCHAR(255) NOT NULL,

    -- Subscription
    plan_tier VARCHAR(50) DEFAULT 'starter', -- starter, professional, enterprise
    subscription_status VARCHAR(50) DEFAULT 'trial', -- trial, active, past_due, canceled
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    trial_ends_at TIMESTAMP,
    current_period_end TIMESTAMP,

    -- Settings
    timezone VARCHAR(100) DEFAULT 'America/Los_Angeles',
    currency VARCHAR(10) DEFAULT 'USD',
    tax_rate DECIMAL(5,4) DEFAULT 0.0725,
    business_phone VARCHAR(50),
    business_address TEXT,
    logo_url TEXT,

    -- Usage tracking
    transaction_count_current_month INTEGER DEFAULT 0,
    user_count INTEGER DEFAULT 0,
    location_count INTEGER DEFAULT 1,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,

    -- Indexes
    CONSTRAINT valid_plan CHECK (plan_tier IN ('starter', 'professional', 'enterprise')),
    CONSTRAINT valid_status CHECK (subscription_status IN ('trial', 'active', 'past_due', 'canceled', 'suspended'))
);

CREATE INDEX idx_tenants_subdomain ON tenants(subdomain);
CREATE INDEX idx_tenants_stripe_customer ON tenants(stripe_customer_id);
CREATE INDEX idx_tenants_status ON tenants(subscription_status);

-- =====================================================
-- USER MANAGEMENT
-- =====================================================

-- Users (Employees/Staff)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Authentication
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    pin_code VARCHAR(10), -- For quick POS login

    -- Profile
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(50),

    -- Role & Permissions
    role VARCHAR(50) NOT NULL, -- owner, manager, cashier, laborer
    is_active BOOLEAN DEFAULT true,

    -- Time tracking
    hourly_rate DECIMAL(10,2),
    salary DECIMAL(10,2),
    pay_type VARCHAR(20), -- hourly, salary

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    deleted_at TIMESTAMP,

    -- Constraints
    CONSTRAINT users_email_tenant_unique UNIQUE (tenant_id, email),
    CONSTRAINT valid_role CHECK (role IN ('owner', 'manager', 'cashier', 'laborer'))
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(tenant_id, role);

-- =====================================================
-- INVENTORY MANAGEMENT
-- =====================================================

-- Items (Products/Inventory)
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identification
    sku VARCHAR(100) NOT NULL,
    barcode VARCHAR(100),
    qr_code TEXT,

    -- Basic Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),

    -- Pricing
    cost_price DECIMAL(10,2),
    sell_price DECIMAL(10,2) NOT NULL,
    markup_percentage DECIMAL(5,2),

    -- Stock
    stock_on_hand INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 0,
    reorder_quantity INTEGER,

    -- Supplier
    supplier_name VARCHAR(255),
    supplier_sku VARCHAR(100),

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,

    -- Constraints
    CONSTRAINT items_sku_tenant_unique UNIQUE (tenant_id, sku)
);

CREATE INDEX idx_items_tenant ON items(tenant_id);
CREATE INDEX idx_items_sku ON items(tenant_id, sku);
CREATE INDEX idx_items_barcode ON items(tenant_id, barcode);
CREATE INDEX idx_items_category ON items(tenant_id, category);
CREATE INDEX idx_items_low_stock ON items(tenant_id, stock_on_hand) WHERE stock_on_hand <= reorder_point;

-- Inventory Lots (For tracking batches)
CREATE TABLE inventory_lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,

    -- Lot Details
    lot_number VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    cost_per_unit DECIMAL(10,2),

    -- Dates
    received_date DATE NOT NULL,
    expiration_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT lots_number_tenant_unique UNIQUE (tenant_id, lot_number)
);

CREATE INDEX idx_lots_tenant ON inventory_lots(tenant_id);
CREATE INDEX idx_lots_item ON inventory_lots(item_id);

-- =====================================================
-- SALES & TRANSACTIONS
-- =====================================================

-- Transactions (Sales)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Transaction Details
    transaction_number VARCHAR(100) NOT NULL,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Amounts
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,

    -- Payment
    payment_method VARCHAR(50) NOT NULL, -- cash, card, crypto, other
    payment_status VARCHAR(50) DEFAULT 'completed', -- pending, completed, refunded

    -- Crypto payment details (if applicable)
    crypto_currency VARCHAR(10), -- BTC, ETH, USDC
    crypto_amount DECIMAL(18,8),
    crypto_tx_hash VARCHAR(255),
    crypto_exchange_rate DECIMAL(18,2),

    -- Customer info (optional)
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),

    -- Staff
    cashier_id UUID REFERENCES users(id),

    -- Receipt
    receipt_printed BOOLEAN DEFAULT false,
    receipt_emailed BOOLEAN DEFAULT false,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_payment_method CHECK (payment_method IN ('cash', 'card', 'crypto', 'other')),
    CONSTRAINT valid_payment_status CHECK (payment_status IN ('pending', 'completed', 'refunded'))
);

CREATE INDEX idx_transactions_tenant ON transactions(tenant_id);
CREATE INDEX idx_transactions_date ON transactions(tenant_id, transaction_date);
CREATE INDEX idx_transactions_cashier ON transactions(cashier_id);
CREATE INDEX idx_transactions_number ON transactions(tenant_id, transaction_number);

-- Transaction Line Items
CREATE TABLE transaction_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    item_id UUID REFERENCES items(id),

    -- Item details (snapshot at time of sale)
    sku VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,

    -- Pricing
    unit_price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    line_total DECIMAL(10,2) NOT NULL,

    -- Cost (for profit calculation)
    unit_cost DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transaction_items_transaction ON transaction_items(transaction_id);
CREATE INDEX idx_transaction_items_item ON transaction_items(item_id);

-- =====================================================
-- TIME TRACKING
-- =====================================================

-- Time Clock Punches
CREATE TABLE time_punches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Punch Details
    punch_type VARCHAR(20) NOT NULL, -- clock_in, clock_out, break_start, break_end
    punch_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Location (optional)
    location VARCHAR(255),
    ip_address VARCHAR(50),

    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_punch_type CHECK (punch_type IN ('clock_in', 'clock_out', 'break_start', 'break_end'))
);

CREATE INDEX idx_punches_tenant ON time_punches(tenant_id);
CREATE INDEX idx_punches_user ON time_punches(user_id);
CREATE INDEX idx_punches_date ON time_punches(tenant_id, punch_time);

-- =====================================================
-- TASK MANAGEMENT
-- =====================================================

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Task Details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, urgent
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, canceled

    -- Assignment
    assigned_to UUID REFERENCES users(id),
    assigned_by UUID REFERENCES users(id),

    -- Dates
    due_date DATE,
    completed_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    CONSTRAINT valid_task_status CHECK (status IN ('pending', 'in_progress', 'completed', 'canceled'))
);

CREATE INDEX idx_tasks_tenant ON tasks(tenant_id);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to, status);
CREATE INDEX idx_tasks_due_date ON tasks(tenant_id, due_date);

-- =====================================================
-- NOTIFICATIONS
-- =====================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification Details
    type VARCHAR(50) NOT NULL, -- task, timeoff, system, low_stock, etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Status
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,

    -- Links
    action_url TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_tenant ON notifications(tenant_id);

-- =====================================================
-- SUBSCRIPTION & BILLING
-- =====================================================

-- Subscription History
CREATE TABLE subscription_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Subscription Details
    plan_tier VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,

    -- Stripe Info
    stripe_subscription_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),

    -- Amounts
    amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',

    -- Period
    period_start TIMESTAMP,
    period_end TIMESTAMP,

    -- Event
    event_type VARCHAR(50), -- created, upgraded, downgraded, canceled, renewed

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscription_history_tenant ON subscription_history(tenant_id);

-- =====================================================
-- ANALYTICS & REPORTING (Materialized Views)
-- =====================================================

-- Daily Sales Summary (for faster reporting)
CREATE MATERIALIZED VIEW daily_sales_summary AS
SELECT
    tenant_id,
    DATE(transaction_date) as sale_date,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    SUM(tax_amount) as total_tax,
    AVG(total_amount) as avg_transaction_value,
    COUNT(DISTINCT cashier_id) as unique_cashiers
FROM transactions
WHERE payment_status = 'completed'
GROUP BY tenant_id, DATE(transaction_date);

CREATE UNIQUE INDEX idx_daily_sales_tenant_date ON daily_sales_summary(tenant_id, sale_date);

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_daily_sales()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_summary;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- ROW LEVEL SECURITY (Tenant Isolation)
-- =====================================================

-- Enable RLS on all tenant tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_lots ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_punches ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Create policy function to get current tenant
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID AS $$
    SELECT current_setting('app.current_tenant_id', true)::UUID;
$$ LANGUAGE SQL STABLE;

-- Example RLS policy (repeat for each table)
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON items
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation ON transactions
    USING (tenant_id = current_tenant_id());

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA (for testing)
-- =====================================================

-- Insert sample tenant
INSERT INTO tenants (business_name, subdomain, owner_email, plan_tier, subscription_status)
VALUES
    ('Demo Coffee Shop', 'demo', 'demo@onyxpos.com', 'professional', 'trial');

-- Get the tenant ID for use in subsequent inserts
-- You would do this programmatically in your app
