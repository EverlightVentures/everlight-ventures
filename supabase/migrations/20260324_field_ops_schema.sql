-- =============================================================================
-- Everlight Field Ops -- AI-to-Human Field Task Marketplace
-- Migration: 20260324_field_ops_schema.sql
-- =============================================================================

-- Enable PostGIS if not already enabled
create extension if not exists postgis;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Workers: field operatives who complete tasks
create table if not exists public.field_ops_workers (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    full_name text not null,
    email text not null,
    phone text,
    bio text,
    skills text[] default '{}',
    location geography(Point, 4326),
    city text,
    state text,
    radius_miles integer default 25,
    hourly_rate numeric(10,2),
    per_task_rate numeric(10,2),
    verified boolean default false,
    verification_tier text default 'basic'
        check (verification_tier in ('basic', 'verified', 'premium')),
    stripe_account_id text,
    rating numeric(3,2) default 0,
    total_tasks_completed integer default 0,
    available boolean default true,
    profile_photo_url text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Tasks: posted by humans, agents, or API integrations
create table if not exists public.field_ops_tasks (
    id uuid primary key default gen_random_uuid(),
    posted_by uuid references auth.users(id) on delete set null,
    posted_by_type text default 'human'
        check (posted_by_type in ('human', 'agent', 'api')),
    title text not null,
    description text not null,
    category text not null
        check (category in (
            'retail_audit', 'property_check', 'delivery', 'photography',
            'errand', 'verification', 'logistics', 'other'
        )),
    location geography(Point, 4326),
    address text,
    city text,
    state text,
    radius_miles integer default 10,
    proof_required text[] default '{photo}',
    budget numeric(10,2) not null check (budget > 0),
    status text default 'open'
        check (status in (
            'open', 'matched', 'in_progress', 'proof_submitted',
            'completed', 'disputed', 'cancelled'
        )),
    deadline timestamptz,
    metadata jsonb default '{}',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Bookings: worker assigned to a task
create table if not exists public.field_ops_bookings (
    id uuid primary key default gen_random_uuid(),
    task_id uuid not null references public.field_ops_tasks(id) on delete cascade,
    worker_id uuid not null references public.field_ops_workers(id) on delete cascade,
    status text default 'pending'
        check (status in (
            'pending', 'accepted', 'in_progress', 'proof_submitted',
            'completed', 'disputed', 'cancelled'
        )),
    proof_urls text[] default '{}',
    proof_notes text,
    proof_validated boolean default false,
    proof_validated_by text check (proof_validated_by in ('ai', 'admin', 'auto')),
    started_at timestamptz,
    completed_at timestamptz,
    payout_amount numeric(10,2),
    platform_fee numeric(10,2),
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Payments: financial transactions for completed bookings
create table if not exists public.field_ops_payments (
    id uuid primary key default gen_random_uuid(),
    booking_id uuid not null references public.field_ops_bookings(id) on delete cascade,
    stripe_payment_intent_id text,
    stripe_transfer_id text,
    amount numeric(10,2) not null check (amount > 0),
    platform_fee numeric(10,2) not null check (platform_fee >= 0),
    worker_payout numeric(10,2) not null check (worker_payout >= 0),
    payment_method text default 'stripe'
        check (payment_method in ('stripe', 'usdc', 'manual')),
    status text default 'pending'
        check (status in ('pending', 'held', 'released', 'refunded', 'disputed')),
    created_at timestamptz default now()
);

-- Reviews: post-task ratings
create table if not exists public.field_ops_reviews (
    id uuid primary key default gen_random_uuid(),
    booking_id uuid not null references public.field_ops_bookings(id) on delete cascade,
    reviewer_id uuid not null references auth.users(id) on delete cascade,
    reviewee_worker_id uuid not null references public.field_ops_workers(id) on delete cascade,
    rating integer not null check (rating >= 1 and rating <= 5),
    comment text,
    created_at timestamptz default now(),
    constraint field_ops_reviews_one_per_booking unique (booking_id, reviewer_id)
);

-- API Keys: for programmatic access (agents, integrations)
create table if not exists public.field_ops_api_keys (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    key_hash text not null unique,
    key_prefix text not null,
    tier text default 'free'
        check (tier in ('free', 'starter', 'business', 'enterprise')),
    monthly_limit integer default 50,
    usage_count integer default 0,
    usage_reset_at timestamptz default now() + interval '30 days',
    active boolean default true,
    created_at timestamptz default now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Workers indexes
create index if not exists idx_field_ops_workers_location
    on public.field_ops_workers using gist (location);
create index if not exists idx_field_ops_workers_skills
    on public.field_ops_workers using gin (skills);
create index if not exists idx_field_ops_workers_city
    on public.field_ops_workers (city);
create index if not exists idx_field_ops_workers_verified
    on public.field_ops_workers (verified);
create index if not exists idx_field_ops_workers_available
    on public.field_ops_workers (available);
create index if not exists idx_field_ops_workers_user_id
    on public.field_ops_workers (user_id);

-- Tasks indexes
create index if not exists idx_field_ops_tasks_location
    on public.field_ops_tasks using gist (location);
create index if not exists idx_field_ops_tasks_status
    on public.field_ops_tasks (status);
create index if not exists idx_field_ops_tasks_category
    on public.field_ops_tasks (category);
create index if not exists idx_field_ops_tasks_city
    on public.field_ops_tasks (city);
create index if not exists idx_field_ops_tasks_posted_by
    on public.field_ops_tasks (posted_by);

-- Bookings indexes
create index if not exists idx_field_ops_bookings_task_id
    on public.field_ops_bookings (task_id);
create index if not exists idx_field_ops_bookings_worker_id
    on public.field_ops_bookings (worker_id);
create index if not exists idx_field_ops_bookings_status
    on public.field_ops_bookings (status);

-- API Keys indexes
create index if not exists idx_field_ops_api_keys_key_hash
    on public.field_ops_api_keys (key_hash);
create index if not exists idx_field_ops_api_keys_user_id
    on public.field_ops_api_keys (user_id);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

alter table public.field_ops_workers enable row level security;
alter table public.field_ops_tasks enable row level security;
alter table public.field_ops_bookings enable row level security;
alter table public.field_ops_payments enable row level security;
alter table public.field_ops_reviews enable row level security;
alter table public.field_ops_api_keys enable row level security;

-- Workers: anyone can read, only owner can update
create policy "field_ops_workers_select"
    on public.field_ops_workers for select
    using (true);

create policy "field_ops_workers_insert"
    on public.field_ops_workers for insert
    with check (auth.uid() = user_id);

create policy "field_ops_workers_update"
    on public.field_ops_workers for update
    using (auth.uid() = user_id);

create policy "field_ops_workers_delete"
    on public.field_ops_workers for delete
    using (auth.uid() = user_id);

-- Tasks: anyone can read open tasks, only poster can update
create policy "field_ops_tasks_select"
    on public.field_ops_tasks for select
    using (status = 'open' or auth.uid() = posted_by);

create policy "field_ops_tasks_insert"
    on public.field_ops_tasks for insert
    with check (auth.uid() = posted_by);

create policy "field_ops_tasks_update"
    on public.field_ops_tasks for update
    using (auth.uid() = posted_by);

create policy "field_ops_tasks_delete"
    on public.field_ops_tasks for delete
    using (auth.uid() = posted_by);

-- Bookings: only involved parties can read/update
create policy "field_ops_bookings_select"
    on public.field_ops_bookings for select
    using (
        auth.uid() in (
            select user_id from public.field_ops_workers where id = worker_id
        )
        or auth.uid() in (
            select posted_by from public.field_ops_tasks where id = task_id
        )
    );

create policy "field_ops_bookings_insert"
    on public.field_ops_bookings for insert
    with check (
        auth.uid() in (
            select user_id from public.field_ops_workers where id = worker_id
        )
        or auth.uid() in (
            select posted_by from public.field_ops_tasks where id = task_id
        )
    );

create policy "field_ops_bookings_update"
    on public.field_ops_bookings for update
    using (
        auth.uid() in (
            select user_id from public.field_ops_workers where id = worker_id
        )
        or auth.uid() in (
            select posted_by from public.field_ops_tasks where id = task_id
        )
    );

-- Payments: only involved parties can read
create policy "field_ops_payments_select"
    on public.field_ops_payments for select
    using (
        auth.uid() in (
            select w.user_id
            from public.field_ops_bookings b
            join public.field_ops_workers w on w.id = b.worker_id
            where b.id = booking_id
        )
        or auth.uid() in (
            select t.posted_by
            from public.field_ops_bookings b
            join public.field_ops_tasks t on t.id = b.task_id
            where b.id = booking_id
        )
    );

-- Reviews: anyone can read, only reviewer can insert
create policy "field_ops_reviews_select"
    on public.field_ops_reviews for select
    using (true);

create policy "field_ops_reviews_insert"
    on public.field_ops_reviews for insert
    with check (auth.uid() = reviewer_id);

-- API Keys: only owner can read/manage
create policy "field_ops_api_keys_select"
    on public.field_ops_api_keys for select
    using (auth.uid() = user_id);

create policy "field_ops_api_keys_insert"
    on public.field_ops_api_keys for insert
    with check (auth.uid() = user_id);

create policy "field_ops_api_keys_update"
    on public.field_ops_api_keys for update
    using (auth.uid() = user_id);

create policy "field_ops_api_keys_delete"
    on public.field_ops_api_keys for delete
    using (auth.uid() = user_id);

-- =============================================================================
-- SERVICE ROLE BYPASS (for edge functions using service_role key)
-- =============================================================================

-- Allow service role full access to all field_ops tables
create policy "field_ops_workers_service"
    on public.field_ops_workers for all
    using (auth.role() = 'service_role');

create policy "field_ops_tasks_service"
    on public.field_ops_tasks for all
    using (auth.role() = 'service_role');

create policy "field_ops_bookings_service"
    on public.field_ops_bookings for all
    using (auth.role() = 'service_role');

create policy "field_ops_payments_service"
    on public.field_ops_payments for all
    using (auth.role() = 'service_role');

create policy "field_ops_reviews_service"
    on public.field_ops_reviews for all
    using (auth.role() = 'service_role');

create policy "field_ops_api_keys_service"
    on public.field_ops_api_keys for all
    using (auth.role() = 'service_role');

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Search workers near a location filtered by skill
create or replace function public.search_workers_nearby(
    lat double precision,
    lng double precision,
    radius_miles integer default 25,
    skill_filter text default null
)
returns table (
    id uuid,
    full_name text,
    email text,
    phone text,
    bio text,
    skills text[],
    city text,
    state text,
    hourly_rate numeric,
    per_task_rate numeric,
    verified boolean,
    verification_tier text,
    rating numeric,
    total_tasks_completed integer,
    profile_photo_url text,
    distance_miles double precision
)
language sql stable
as $$
    select
        w.id,
        w.full_name,
        w.email,
        w.phone,
        w.bio,
        w.skills,
        w.city,
        w.state,
        w.hourly_rate,
        w.per_task_rate,
        w.verified,
        w.verification_tier,
        w.rating,
        w.total_tasks_completed,
        w.profile_photo_url,
        round(
            (st_distance(
                w.location,
                st_setsrid(st_makepoint(lng, lat), 4326)::geography
            ) / 1609.344)::numeric, 2
        )::double precision as distance_miles
    from public.field_ops_workers w
    where w.available = true
      and w.location is not null
      and st_dwithin(
            w.location,
            st_setsrid(st_makepoint(lng, lat), 4326)::geography,
            radius_miles * 1609.344
          )
      and (skill_filter is null or skill_filter = any(w.skills))
    order by distance_miles asc, w.rating desc
    limit 50;
$$;

-- Match top 10 workers to a specific task by proximity + rating + skill overlap
create or replace function public.match_task_to_workers(
    p_task_id uuid
)
returns table (
    worker_id uuid,
    full_name text,
    skills text[],
    city text,
    state text,
    rating numeric,
    total_tasks_completed integer,
    distance_miles double precision,
    skill_overlap integer,
    match_score double precision
)
language sql stable
as $$
    with task as (
        select t.location, t.radius_miles, t.category
        from public.field_ops_tasks t
        where t.id = p_task_id
    )
    select
        w.id as worker_id,
        w.full_name,
        w.skills,
        w.city,
        w.state,
        w.rating,
        w.total_tasks_completed,
        round(
            (st_distance(
                w.location,
                task.location
            ) / 1609.344)::numeric, 2
        )::double precision as distance_miles,
        (select count(*)::integer
         from unnest(w.skills) s
         where s = task.category
        ) as skill_overlap,
        -- Score: 40% proximity (inverse distance), 30% rating, 30% skill match
        (
            (1.0 - least(
                st_distance(w.location, task.location) / 1609.344
                / nullif(task.radius_miles, 0)::double precision,
                1.0
            )) * 40.0
            + (coalesce(w.rating, 0)::double precision / 5.0) * 30.0
            + (case when task.category = any(w.skills) then 30.0 else 0.0 end)
        ) as match_score
    from public.field_ops_workers w, task
    where w.available = true
      and w.location is not null
      and st_dwithin(
            w.location,
            task.location,
            task.radius_miles * 1609.344
          )
    order by match_score desc, distance_miles asc
    limit 10;
$$;

-- =============================================================================
-- TRIGGERS: auto-update updated_at
-- =============================================================================

create or replace function public.field_ops_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger field_ops_workers_updated_at
    before update on public.field_ops_workers
    for each row execute function public.field_ops_set_updated_at();

create trigger field_ops_tasks_updated_at
    before update on public.field_ops_tasks
    for each row execute function public.field_ops_set_updated_at();

create trigger field_ops_bookings_updated_at
    before update on public.field_ops_bookings
    for each row execute function public.field_ops_set_updated_at();

-- =============================================================================
-- TRIGGER: auto-update worker rating after review
-- =============================================================================

create or replace function public.field_ops_update_worker_rating()
returns trigger
language plpgsql
as $$
begin
    update public.field_ops_workers
    set rating = (
        select round(avg(r.rating)::numeric, 2)
        from public.field_ops_reviews r
        where r.reviewee_worker_id = new.reviewee_worker_id
    )
    where id = new.reviewee_worker_id;
    return new;
end;
$$;

create trigger field_ops_reviews_update_rating
    after insert on public.field_ops_reviews
    for each row execute function public.field_ops_update_worker_rating();

-- =============================================================================
-- TRIGGER: increment worker task count on booking completion
-- =============================================================================

create or replace function public.field_ops_increment_task_count()
returns trigger
language plpgsql
as $$
begin
    if new.status = 'completed' and (old.status is null or old.status <> 'completed') then
        update public.field_ops_workers
        set total_tasks_completed = total_tasks_completed + 1
        where id = new.worker_id;
    end if;
    return new;
end;
$$;

create trigger field_ops_bookings_task_count
    after update on public.field_ops_bookings
    for each row execute function public.field_ops_increment_task_count();

-- Waitlist tables for pre-launch signups
CREATE TABLE IF NOT EXISTS field_ops_waitlist_workers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name text NOT NULL,
  email text NOT NULL UNIQUE,
  city text,
  skills text[],
  created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS field_ops_waitlist_businesses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company text NOT NULL,
  email text NOT NULL UNIQUE,
  monthly_volume text,
  use_case text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE field_ops_waitlist_workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_ops_waitlist_businesses ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts (waitlist signups don't require auth)
CREATE POLICY "Anyone can join worker waitlist" ON field_ops_waitlist_workers FOR INSERT WITH CHECK (true);
CREATE POLICY "Anyone can join business waitlist" ON field_ops_waitlist_businesses FOR INSERT WITH CHECK (true);
