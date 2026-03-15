# Lovable Prompt: HIM Gear Drop Integration on everlightventures.io

## Task
Add the HIM Gear Drop feature to the `/him-loadout` page on everlightventures.io.
Pull today's drop from the Supabase `daily_drops` table and display it with a countdown to the next drop.

---

## Supabase Table: `daily_drops`

Create this table in Supabase if it does not exist:

```sql
create table if not exists daily_drops (
  id text primary key,
  drop_date date not null,
  product_id text,
  title text not null,
  description text,
  image_url text,
  affiliate_url text not null,
  seller text,
  rating numeric(3,2),
  gear_score numeric(5,2),
  commission_pct numeric(4,2),
  drop_time_pt timestamptz,
  published boolean default true,
  source text default 'supabase',
  created_at timestamptz default now()
);

-- RLS: public read only
alter table daily_drops enable row level security;
create policy "Public read daily_drops" on daily_drops for select using (true);

-- Index for today's drop
create index on daily_drops (drop_date desc, published);
```

Also create the catalog table for the orchestrator to pull from:

```sql
create table if not exists gear_catalog (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  image_url text,
  url text not null,
  seller text,
  rating numeric(3,2) default 4.5,
  sales_velocity integer default 100,
  commission_pct numeric(4,2) default 4.0,
  stock integer default 100,
  active boolean default true,
  category text,
  source text default 'manual',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
alter table gear_catalog enable row level security;
create policy "Public read gear_catalog" on gear_catalog for select using (active = true);
```

---

## Frontend Component: Daily Drop Widget

Add to `/him-loadout` page. The component should:

1. **Fetch today's drop** from Supabase on page load:
   ```js
   const today = new Date().toISOString().split('T')[0]
   const { data } = await supabase
     .from('daily_drops')
     .select('*')
     .eq('drop_date', today)
     .eq('published', true)
     .order('gear_score', { ascending: false })
     .limit(3)
   ```

2. **Display each drop card** with:
   - Product image (full-width, aspect ratio 4:3)
   - "TODAY'S DROP" badge (gold/amber, top-left)
   - Star rating (e.g. 4.8 stars)
   - Gear Score badge (e.g. "Score: 87")
   - Title (bold, 1.5rem)
   - Seller name (muted, small)
   - Description (2-3 lines, muted)
   - "GET THIS GEAR" CTA button (full-width, Everlight brand color)
     - links to affiliate_url, target="_blank", rel="noopener noreferrer sponsored"

3. **Countdown timer** to next drop:
   - Shows "Next drop in: HH:MM:SS" counting down to 6:00 PM PT
   - After 6 PM: shows "New drop coming soon..."

4. **Empty state**: If no drop today, show "Check back at 6 PM PT for today's drop."

---

## Style Notes
- Match Everlight dark theme (bg: #0a0a0a or current site dark)
- Gold accent: #D4AF37
- CTA button: gradient from brand purple to gold, or solid brand primary
- Card: subtle border, rounded-xl, hover lift effect
- "TODAY'S DROP" badge: uppercase, amber/gold background, dark text

---

## Navigation
- Add "Gear Drop" link to `/him-loadout` sub-nav
- Or surface the top drop on the main `/him-loadout` hero as "Today's Pick"

---

## Affiliate Disclosure
Add this text below the drop cards (required by FTC):
> As an affiliate, Everlight Ventures may earn a commission from qualifying purchases at no extra cost to you.

---

## Integration with Autonomous System
The backend Python orchestrator (`daily_drop_orchestrator.py`) runs daily at 6 PM PT
and pushes new items to the `daily_drops` table automatically.
The Lovable frontend just needs to read from Supabase -- no backend calls needed.
