# LOVABLE PROMPT: Private Hive Mind Dashboard (Auth-Gated)

Paste everything below into Lovable. This adds a private, auth-gated /hivemind route that gives the site owner a live view of AI Hive Mind sessions, war room deliberations, and agent status -- all reading from Supabase.

**Supabase URL:** `https://jdqqmsmwmbsnlnstyavl.supabase.co`
**Anon Key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

---

## ACCESS CONTROL

This route is PRIVATE. Only authenticated users with `role = 'owner'` in the `user_profiles` table can access it.

- If not authenticated: redirect to /login
- If authenticated but not owner: show "Access Denied" page
- Add a `user_profiles` table if it doesn't exist:
  ```sql
  create table if not exists user_profiles (
    id uuid references auth.users primary key,
    role text default 'user',
    display_name text,
    created_at timestamptz default now()
  );
  alter table user_profiles enable row level security;
  create policy "Users can read own profile" on user_profiles for select using (auth.uid() = id);
  create policy "Owner can read all" on user_profiles for select using (
    (select role from user_profiles where id = auth.uid()) = 'owner'
  );
  ```

---

## SUPABASE TABLES NEEDED

Create these tables for the Hive Mind data (the local Django dashboard will push data here):

```sql
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
```

---

## PAGE LAYOUT: /hivemind

### Header
- Title: "Hive Mind" in the Everlight brand font
- Subtitle: "AI Operations Center" in muted text
- Status indicator: green dot + "Online" if any agent was active in the last 5 minutes, yellow "Idle" otherwise

### Section 1: Agent Status Grid (top)

A horizontal row of 4 agent cards, one for each AI:

| Card | Agent | Color |
|------|-------|-------|
| 1 | Claude (Chief Operator) | Purple (#8B5CF6) |
| 2 | Gemini (Logistics Commander) | Blue (#3B82F6) |
| 3 | Codex (Engineering Foreman) | Green (#10B981) |
| 4 | Perplexity (Intelligence Anchor) | Orange (#F59E0B) |

Each card shows:
- Agent name + role
- Status badge (Active/Idle/Offline) with colored dot
- "Last active: X min ago" timestamp
- Tasks completed count
- Current task (if active)

Read from `hive_agent_status` table, refresh every 30 seconds.

### Section 2: Recent Sessions (main content)

A vertical list of session cards, most recent first. Load from `hive_sessions` table.

Each session card:
- **Query text** as the title (bold, truncated to 100 chars with expand)
- **Routing category** pill badge (Trading, Content, Engineering, etc.)
- **Managers engaged** shown as small colored dots matching the agent colors above
- **Status** badge: Running (yellow pulse), Completed (green), Failed (red)
- **Timestamp** in relative format ("2 hours ago")
- **Token cost** in small muted text
- Click to expand and show the combined_summary + individual agent reports

Expanded view:
- Combined summary in a card with subtle border
- Tabs for each agent's individual report (pulled from `hive_agent_reports`)
- Each agent tab shows their report text in markdown format
- Duration and token count per agent

### Section 3: Quick Stats Bar (bottom)

Horizontal stat bar:
- Total sessions (all time)
- Sessions today
- Total tokens used today
- Average session duration
- Most active agent (by tasks_completed)

---

## DESIGN NOTES

- Use the existing Everlight dark theme (dark bg, subtle glass effects, gold accents)
- Cards should have the same glass/blur treatment as the rest of the site
- Responsive: on mobile, agent cards stack 2x2, sessions go full-width
- Add a "Refresh" button in the top right that reloads all data
- Add auto-refresh toggle (default: on, 30-second interval)
- Loading states: skeleton cards while data loads
- Empty state: "No sessions yet. Launch a query from the War Room to get started."

---

## NAVIGATION

- Add "Hive Mind" to the main nav menu, but ONLY show it to authenticated owner users
- Use a brain/neural network icon for the nav item
- Position it after the Dashboard link in the nav order
