-- ============================================================
-- STARK AI SYSTEM -- Supabase Schema
-- Voice-first AI command center with tiered access
-- ============================================================

-- User profiles with tier system (extends auth.users)
create table if not exists stark_profiles (
  id uuid references auth.users on delete cascade primary key,
  tier text not null default 'client' check (tier in ('god', 'client', 'public')),
  display_name text,
  voice_enabled boolean default true,
  preferred_voice text default 'f6pM8mPp5ODaRZDE6oTq',  -- Jeremy (Lucrex default)
  voice_speed float default 1.0,
  theme text default 'dark',
  command_count int default 0,
  last_active_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Command history (every interaction logged)
create table if not exists stark_commands (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  session_id uuid,
  input_text text not null,
  category text not null default 'questions',
  response_text text,
  agents_used text[] default '{}',
  voice_used text,             -- voice_id used for TTS
  audio_duration_ms int,
  tier_at_time text not null,  -- snapshot of user tier when command ran
  latency_ms int,              -- total processing time
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- Voice sessions (groups of commands in one conversation)
create table if not exists stark_sessions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  mode text default 'text' check (mode in ('text', 'voice', 'mixed')),
  command_count int default 0,
  started_at timestamptz default now(),
  ended_at timestamptz,
  summary text,
  metadata jsonb default '{}'
);

-- Agent activity log (tracks what agents did per command)
create table if not exists stark_agent_activity (
  id uuid default gen_random_uuid() primary key,
  command_id uuid references stark_commands on delete cascade,
  agent_name text not null,
  action text not null,           -- 'dispatched', 'responded', 'delegated', 'error'
  response_fragment text,         -- what this agent contributed
  voice_id text,                  -- voice used if agent spoke
  latency_ms int,
  created_at timestamptz default now()
);

-- Indexes for fast queries
create index if not exists idx_stark_commands_user on stark_commands(user_id, created_at desc);
create index if not exists idx_stark_commands_session on stark_commands(session_id);
create index if not exists idx_stark_commands_category on stark_commands(category);
create index if not exists idx_stark_sessions_user on stark_sessions(user_id, started_at desc);
create index if not exists idx_stark_agent_activity_cmd on stark_agent_activity(command_id);

-- RLS Policies
alter table stark_profiles enable row level security;
alter table stark_commands enable row level security;
alter table stark_sessions enable row level security;
alter table stark_agent_activity enable row level security;

-- Profiles: users read own, god reads all, service writes
create policy "Users read own profile" on stark_profiles
  for select using (auth.uid() = id);
create policy "God reads all profiles" on stark_profiles
  for select using (
    (select tier from stark_profiles where id = auth.uid()) = 'god'
  );
create policy "Users update own profile" on stark_profiles
  for update using (auth.uid() = id);
create policy "Service inserts profiles" on stark_profiles
  for insert with check (true);

-- Commands: users read own, god reads all, service writes
create policy "Users read own commands" on stark_commands
  for select using (auth.uid() = user_id);
create policy "God reads all commands" on stark_commands
  for select using (
    (select tier from stark_profiles where id = auth.uid()) = 'god'
  );
create policy "Service inserts commands" on stark_commands
  for insert with check (true);

-- Sessions: users read own, god reads all
create policy "Users read own sessions" on stark_sessions
  for select using (auth.uid() = user_id);
create policy "God reads all sessions" on stark_sessions
  for select using (
    (select tier from stark_profiles where id = auth.uid()) = 'god'
  );
create policy "Service manages sessions" on stark_sessions
  for all with check (true);

-- Agent activity: inherits from command access
create policy "Users read own agent activity" on stark_agent_activity
  for select using (
    command_id in (select id from stark_commands where user_id = auth.uid())
  );
create policy "Service manages agent activity" on stark_agent_activity
  for all with check (true);

-- Function: auto-increment command count on profile
create or replace function stark_increment_command_count()
returns trigger as $$
begin
  update stark_profiles
  set command_count = command_count + 1,
      last_active_at = now(),
      updated_at = now()
  where id = NEW.user_id;
  return NEW;
end;
$$ language plpgsql security definer;

create trigger trg_stark_command_count
  after insert on stark_commands
  for each row execute function stark_increment_command_count();

-- Function: auto-increment session command count
create or replace function stark_increment_session_count()
returns trigger as $$
begin
  if NEW.session_id is not null then
    update stark_sessions
    set command_count = command_count + 1
    where id = NEW.session_id;
  end if;
  return NEW;
end;
$$ language plpgsql security definer;

create trigger trg_stark_session_count
  after insert on stark_commands
  for each row execute function stark_increment_session_count();
