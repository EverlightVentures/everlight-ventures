-- Hive Mind tables for private dashboard on Lovable
-- Django hive_dashboard pushes session data here via supabase_client.py

-- User profiles for role-based access
create table if not exists user_profiles (
  id uuid references auth.users primary key,
  role text default 'user',
  display_name text,
  created_at timestamptz default now()
);
alter table user_profiles enable row level security;
create policy "Users can read own profile" on user_profiles for select using (auth.uid() = id);
create policy "Owner can read all profiles" on user_profiles for select using (
  (select role from user_profiles where id = auth.uid()) = 'owner'
);

-- Hive sessions (pushed from Django hive_dashboard)
create table if not exists hive_sessions (
  id uuid primary key default gen_random_uuid(),
  session_id text unique not null,
  query text not null,
  managers_engaged text[] default '{}',
  status text default 'running',
  created_at timestamptz default now(),
  completed_at timestamptz,
  combined_summary text,
  token_cost numeric default 0,
  routing_category text
);
alter table hive_sessions enable row level security;
create policy "Owner can read all sessions" on hive_sessions for select using (
  (select role from user_profiles where id = auth.uid()) = 'owner'
);
create policy "Service can insert sessions" on hive_sessions for insert with check (true);
create policy "Service can update sessions" on hive_sessions for update using (true);

-- Individual agent reports within a session
create table if not exists hive_agent_reports (
  id uuid primary key default gen_random_uuid(),
  session_id text references hive_sessions(session_id),
  agent_name text not null,
  agent_role text,
  report_text text,
  tokens_used integer default 0,
  duration_ms integer default 0,
  created_at timestamptz default now()
);
alter table hive_agent_reports enable row level security;
create policy "Owner can read reports" on hive_agent_reports for select using (
  (select role from user_profiles where id = auth.uid()) = 'owner'
);
create policy "Service can insert reports" on hive_agent_reports for insert with check (true);

-- Agent health status (pushed periodically)
create table if not exists hive_agent_status (
  id uuid primary key default gen_random_uuid(),
  agent_name text unique not null,
  agent_type text not null,
  status text default 'idle',
  last_active timestamptz default now(),
  tasks_completed integer default 0,
  current_task text
);
alter table hive_agent_status enable row level security;
create policy "Owner can read status" on hive_agent_status for select using (
  (select role from user_profiles where id = auth.uid()) = 'owner'
);
create policy "Service can upsert status" on hive_agent_status for all using (true);
