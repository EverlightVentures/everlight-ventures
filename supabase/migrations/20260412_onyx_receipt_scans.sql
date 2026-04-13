-- ============================================================
-- ONYX POS -- Receipt Scanner Add-On
-- Leo Marchetti (SF-009) -- AI/CV Lead
-- Smart Scanner: $29/mo add-on for receipt digitization
-- ============================================================

-- Receipt scan results
create table if not exists public.onyx_receipt_scans (
    id uuid primary key default uuid_generate_v4(),
    tenant_id uuid not null references public.onyx_tenants(id) on delete cascade,
    employee_id uuid references public.onyx_employees(id),
    -- Scan data
    raw_image_url text,
    extracted_data jsonb not null default '{}',
    raw_ocr_text text,
    confidence_score numeric(3,2) default 0.00,
    -- Classification
    scan_type text default 'receipt' check (scan_type in ('receipt', 'invoice', 'label', 'other')),
    status text default 'completed' check (status in ('processing', 'completed', 'failed', 'reviewed')),
    -- If linked to an existing transaction
    linked_transaction_id uuid references public.onyx_transactions(id),
    -- Metadata
    notes text,
    created_at timestamptz default now()
);

-- Indexes
create index if not exists idx_onyx_receipt_scans_tenant
    on public.onyx_receipt_scans(tenant_id, created_at desc);

-- RLS
alter table public.onyx_receipt_scans enable row level security;

create policy "tenant_isolation" on public.onyx_receipt_scans
    for all using (tenant_id in (
        select id from public.onyx_tenants where owner_user_id = auth.uid()
    ));

create policy "service_role_bypass" on public.onyx_receipt_scans
    for all using (auth.role() = 'service_role');

-- Add scanner plan flag to tenants
alter table public.onyx_tenants
    add column if not exists scanner_enabled boolean default false,
    add column if not exists scanner_stripe_subscription_id text,
    add column if not exists monthly_scan_count integer default 0,
    add column if not exists monthly_scan_limit integer default 10;
-- Free tier: 10 scans/mo. Paid ($29/mo): unlimited.
