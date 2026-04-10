-- ============================================================
-- ONYX POS -- Full SaaS Schema
-- Amara Osei (SF-007) -- Backend Architect
-- 7 core tables + RLS for multi-tenancy
-- ============================================================

-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- ============================================================
-- 1. TENANTS (businesses using Onyx POS)
-- ============================================================
create table if not exists public.onyx_tenants (
    id uuid primary key default uuid_generate_v4(),
    business_name text not null,
    address_line1 text,
    address_line2 text,
    phone text,
    slogan text,
    tax_rate numeric(5,4) not null default 0.0825,
    currency text not null default 'USD',
    timezone text not null default 'America/Los_Angeles',
    -- Labor law config (state-specific)
    meal_break_hours numeric(3,1) default 5.0,
    rest_break_hours numeric(3,1) default 4.0,
    overtime_hours numeric(3,1) default 8.0,
    min_time_off_notice_days integer default 14,
    -- Subscription
    stripe_customer_id text,
    stripe_subscription_id text,
    plan text default 'starter' check (plan in ('starter', 'growth', 'multi_site', 'trial')),
    plan_status text default 'trialing' check (plan_status in ('trialing', 'active', 'past_due', 'canceled')),
    trial_ends_at timestamptz default (now() + interval '60 days'),
    -- Metadata
    owner_user_id uuid references auth.users(id),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ============================================================
-- 2. PRODUCTS / CATEGORIES (configurable per tenant)
-- ============================================================
create table if not exists public.onyx_categories (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    name text not null,
    parent_id uuid references public.onyx_categories(id),
    sort_order integer default 0,
    created_at timestamptz default now()
);

create table if not exists public.onyx_products (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    category_id uuid references public.onyx_categories(id),
    name text not null,
    description text,
    unit_price numeric(10,2) not null default 0.00,
    sku text,
    stock_quantity integer,
    reorder_point integer default 5,
    is_active boolean default true,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ============================================================
-- 3. EMPLOYEES
-- ============================================================
create table if not exists public.onyx_employees (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    user_id uuid references auth.users(id),
    employee_number serial,
    full_name text not null,
    role text not null default 'employee' check (role in ('owner', 'manager', 'employee')),
    pin_hash text,
    phone text,
    email text,
    emergency_contact text,
    hourly_rate numeric(8,2),
    status text default 'active' check (status in ('active', 'inactive', 'terminated')),
    hire_date date default current_date,
    notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ============================================================
-- 4. SALES TRANSACTIONS (header)
-- ============================================================
create table if not exists public.onyx_transactions (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid references public.onyx_employees(id),
    transaction_number serial,
    subtotal numeric(10,2) not null default 0.00,
    tax_rate numeric(5,4) not null,
    tax_amount numeric(10,2) not null default 0.00,
    total numeric(10,2) not null default 0.00,
    payment_method text not null default 'cash' check (payment_method in ('cash', 'card', 'other')),
    amount_received numeric(10,2),
    change_due numeric(10,2),
    receipt_number text,
    notes text,
    voided boolean default false,
    created_at timestamptz default now()
);

-- ============================================================
-- 5. SALE LINE ITEMS (detail)
-- ============================================================
create table if not exists public.onyx_line_items (
    id uuid primary key default uuid_generate_v4(),
    transaction_id uuid not null references public.onyx_transactions(id) on delete cascade,
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    product_id uuid references public.onyx_products(id),
    product_name text not null,
    category_name text,
    quantity integer not null default 1,
    unit_price numeric(10,2) not null,
    subtotal numeric(10,2) not null,
    tax_amount numeric(10,2) not null default 0.00,
    line_total numeric(10,2) not null,
    notes text,
    created_at timestamptz default now()
);

-- ============================================================
-- 6. TIME PUNCHES (clock in/out/break)
-- ============================================================
create table if not exists public.onyx_time_punches (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid not null references public.onyx_employees(id),
    punch_type text not null check (punch_type in ('clock_in', 'clock_out', 'break_start', 'break_end', 'lunch_start', 'lunch_end')),
    punched_at timestamptz not null default now(),
    hours_worked numeric(5,2),
    overtime_hours numeric(5,2),
    notes text,
    created_at timestamptz default now()
);

-- ============================================================
-- 7. TIME OFF REQUESTS
-- ============================================================
create table if not exists public.onyx_time_off (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid not null references public.onyx_employees(id),
    start_date date not null,
    end_date date not null,
    total_days integer not null,
    reason text,
    status text default 'pending' check (status in ('pending', 'approved', 'denied')),
    manager_notes text,
    approved_by uuid references public.onyx_employees(id),
    approved_at timestamptz,
    created_at timestamptz default now()
);

-- ============================================================
-- 8. AI CHAT HISTORY (for "Ask your POS anything")
-- ============================================================
create table if not exists public.onyx_chat_history (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid references public.onyx_employees(id),
    user_message text not null,
    ai_response text not null,
    tokens_used integer,
    created_at timestamptz default now()
);

-- ============================================================
-- INDEXES
-- ============================================================
create index if not exists idx_onyx_products_tenant on public.onyx_products(tenant_id);
create index if not exists idx_onyx_employees_tenant on public.onyx_employees(tenant_id);
create index if not exists idx_onyx_transactions_tenant on public.onyx_transactions(tenant_id);
create index if not exists idx_onyx_transactions_created on public.onyx_transactions(tenant_id, created_at);
create index if not exists idx_onyx_line_items_tx on public.onyx_line_items(transaction_id);
create index if not exists idx_onyx_time_punches_employee on public.onyx_time_punches(tenant_id, employee_id, punched_at);
create index if not exists idx_onyx_time_off_employee on public.onyx_time_off(tenant_id, employee_id);
create index if not exists idx_onyx_categories_tenant on public.onyx_categories(tenant_id);

-- ============================================================
-- ROW LEVEL SECURITY (multi-tenancy isolation)
-- ============================================================
alter table public.onyx_tenants enable row level security;
alter table public.onyx_categories enable row level security;
alter table public.onyx_products enable row level security;
alter table public.onyx_employees enable row level security;
alter table public.onyx_transactions enable row level security;
alter table public.onyx_line_items enable row level security;
alter table public.onyx_time_punches enable row level security;
alter table public.onyx_time_off enable row level security;
alter table public.onyx_chat_history enable row level security;

-- Tenant isolation: users can only see their own tenant's data
-- The tenant_id is stored in the user's JWT metadata
create policy "tenant_isolation" on public.onyx_tenants
    for all using (owner_user_id = auth.uid());

create policy "tenant_isolation" on public.onyx_categories
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_products
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_employees
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_transactions
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_line_items
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_time_punches
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_time_off
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

create policy "tenant_isolation" on public.onyx_chat_history
    for all using (tenant_id in (select id from public.onyx_tenants where owner_user_id = auth.uid()));

-- Service role bypass for API backend
create policy "service_role_bypass" on public.onyx_tenants
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_categories
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_products
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_employees
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_transactions
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_line_items
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_time_punches
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_time_off
    for all using (auth.role() = 'service_role');
create policy "service_role_bypass" on public.onyx_chat_history
    for all using (auth.role() = 'service_role');

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================
create or replace function public.onyx_set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_updated_at before update on public.onyx_tenants
    for each row execute function public.onyx_set_updated_at();
create trigger set_updated_at before update on public.onyx_products
    for each row execute function public.onyx_set_updated_at();
create trigger set_updated_at before update on public.onyx_employees
    for each row execute function public.onyx_set_updated_at();
