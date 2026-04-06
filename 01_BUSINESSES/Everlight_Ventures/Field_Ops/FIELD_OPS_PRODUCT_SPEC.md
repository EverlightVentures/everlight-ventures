# Everlight Field Ops -- Product Specification & Business Plan
# Version: 1.0 | Date: 2026-03-24
# Status: SCOPED -- Ready for Phase 1 Build
# Owner: Road Harper (SaaS PM, Codex Labs)
# Contributors: Atlas Vega (Architecture), Slate Mercer (Strategic Modeling),
#   Chart Dawson (Analytics), Justine Park (Compliance), Forge (Codex Labs TL),
#   Penny Bright (Revenue Model), Cash Moreno (Commission Audit)

---

## 1. Product Overview

**Name:** Everlight Field Ops
**Tagline:** "Eyes and hands on the ground for AI agents"
**Slug:** `field-ops`
**URL:** everlightventures.io/field-ops

**Positioning:**
Everlight Field Ops is a verticalized field task marketplace purpose-built for B2B
proof-based work. It connects AI agents and businesses with verified local humans
who execute real-world tasks -- retail shelf audits, property checks, delivery
confirmations, errand runs -- and return structured proof (photos, GPS stamps,
receipts, signed confirmations).

**What this is NOT:**
- Not a generic gig marketplace (no TaskRabbit-style home repair)
- Not a delivery service (no food, no packages -- those are commoditized)
- Not a freelance platform (no ongoing employment, no creative work)

**What this IS:**
- A proof-based field verification layer for AI systems
- A B2B-first marketplace where every task has a defined proof schema
- An API-native platform where AI agents can dispatch humans programmatically
- A trust engine where location verification, photo proof, and rating systems
  create reliability that AI agents can depend on

**The Core Insight:**
AI agents are getting extremely capable at planning, reasoning, and coordinating.
But they cannot walk into a store, take a photo of a shelf, check if a solar panel
fits on a roof, or confirm a package was delivered to the right address. There is
a growing gap between what AI can plan and what AI can physically verify. Field Ops
fills that gap.

---

## 2. Target Verticals (Launch Order)

### Vertical 1: Retail / Shelf Verification (Launch)
- **Buyer:** Amazon FBA sellers, CPG brand managers, retail analytics firms
- **Task examples:** "Go to Walmart on 5th Ave, photograph the cereal aisle, confirm
  our product is on shelf at eye level, note price tag"
- **Proof type:** Geotagged photos + structured data form
- **Why first:** Highest frequency, lowest risk, easiest to standardize, large
  existing market ($2B+ retail audit industry)
- **Average task value:** $15-40
- **ICP:** Amazon sellers doing $50k+/yr who need shelf presence verified across
  multiple retail locations. Brand managers at CPG companies with 50+ SKUs in
  regional distribution.

### Vertical 2: Property / Solar Site Checks (Month 2)
- **Buyer:** Real estate investors, solar installers, insurance adjusters, appraisers
- **Task examples:** "Drive to 123 Oak St, photograph all four sides of the house,
  note roof condition, check if south-facing roof has shade obstructions"
- **Proof type:** Geotagged photos + checklist + measurements
- **Why second:** High value per task, growing solar/RE markets, clear proof schema
- **Average task value:** $30-75
- **ICP:** Solar installation companies doing 50+ installs/yr who need pre-site
  qualification. Real estate investors managing 20+ properties remotely.

### Vertical 3: Local Logistics (Month 3)
- **Buyer:** E-commerce sellers, law firms, small businesses
- **Task examples:** "Pick up signed documents from 456 Elm St, photograph the
  signed page, deliver to FedEx drop-off, photograph the receipt"
- **Proof type:** Chain-of-custody photos + receipts + GPS trail
- **Why third:** Broadest market, but hardest to standardize -- needs V1/V2 learnings
- **Average task value:** $20-60
- **ICP:** Law firms needing local document handling. E-commerce sellers needing
  return verification.

### Vertical 4: Event Verification (Month 4)
- **Buyer:** Marketing agencies, event companies, franchise owners
- **Task examples:** "Confirm our flyers are posted at these 10 locations, photograph
  each one, note foot traffic estimate"
- **Proof type:** Geotagged photos + timestamp + notes
- **Why fourth:** Seasonal demand, lower frequency -- good expansion vertical
- **Average task value:** $10-25
- **ICP:** Marketing agencies managing local campaigns for 10+ clients. Franchise
  operations needing field compliance checks.

---

## 3. Two-Sided Marketplace Design

### 3A. Supply Side: Field Ops Workers

**Profile Fields:**
- Full name, profile photo, bio
- Skills (multi-select from controlled list): retail_audit, property_check,
  delivery, errand, event_verification, photography, driving
- Location (lat/lng center point)
- Service radius (miles, default 15, max 50)
- Rate card: base rate per task type, hourly rate, mileage rate
- Availability: weekly schedule blocks + on-demand toggle
- Equipment: smartphone (required), vehicle (optional), camera (optional)
- Languages spoken

**Verification Tiers:**

| Tier | Cost | Requirements | Benefits |
|------|------|-------------|----------|
| Basic | Free | Email + phone verified, profile complete | Can accept up to 5 tasks/week, standard matching |
| Verified | $9.99/mo | Government ID check (Stripe Identity), background check, profile review | Unlimited tasks, priority matching, "Verified" badge, higher visibility, access to premium tasks |
| Pro | $24.99/mo | Everything in Verified + completed 50+ tasks with 4.5+ rating | Top-of-queue matching, featured profile, early access to high-value tasks, dedicated support |

**Worker App (Mobile-First):**
- Push notifications for nearby task matches
- In-app camera with auto-geotagging and timestamp overlay
- GPS tracking during active tasks (opt-in, visible to client)
- Proof upload with structured form fields per task type
- Earnings dashboard with payout history
- Rating and review management
- Availability calendar
- Built with React Native or Expo for iOS + Android

**Worker Onboarding Flow:**
1. Download app / visit field-ops worker signup page
2. Create account (email + phone)
3. Complete profile (skills, location, radius, rate card)
4. Upload profile photo
5. Accept terms of service
6. (Optional) Upgrade to Verified -- triggers Stripe Identity flow
7. Start receiving task matches

### 3B. Demand Side: AI Agents + Businesses

**Integration Methods (in priority order):**

1. **REST API** (primary): Standard RESTful endpoints with API key auth.
   AI agents call `POST /tasks` to create, `GET /tasks/{id}` to check status,
   receive webhook callbacks on state changes.

2. **MCP Server** (secondary): Model Context Protocol server package that any
   Claude, LangChain, or CrewAI agent can install. Exposes Field Ops as native
   tools the agent can call conversationally.

3. **Business Dashboard** (manual): Web UI at everlightventures.io/field-ops/dashboard
   for businesses that want to post tasks manually, review proof, approve payouts.

4. **Zapier / n8n Integration** (future): Triggers and actions for no-code workflows.

**API Tiers:**

| Tier | Price | Included Tasks | Overage | Features |
|------|-------|---------------|---------|----------|
| Starter | $49/mo | 50 tasks | $1.50/task | REST API, webhooks, basic dashboard |
| Growth | $149/mo | 500 tasks | $1.00/task | Everything in Starter + MCP server, priority matching, dedicated support |
| Enterprise | Custom | Custom | Negotiated | SLA, custom proof schemas, bulk pricing, account manager |

**Business Onboarding Flow:**
1. Sign up at everlightventures.io/field-ops
2. Create organization profile
3. Add payment method (Stripe)
4. Choose API tier
5. Generate API key
6. Read docs, make first API call or post first task via dashboard
7. Review proof, approve payout

---

## 4. Core Workflow

```
TASK LIFECYCLE:

  [1] TASK_POSTED
       |
       | Client creates task via API/dashboard
       | System validates: location, budget, proof schema
       |
  [2] WORKER_MATCHED
       |
       | System finds workers: location radius + skills + availability + rating
       | Sends push notification to top 5 matches
       | First-accept model (first qualified worker to accept gets it)
       |
  [3] TASK_ACCEPTED
       |
       | Worker confirms acceptance
       | Client notified
       | Clock starts (task has max_duration, default 4 hours)
       |
  [4] TASK_IN_PROGRESS
       |
       | Worker travels to location
       | GPS tracking active (if opted in)
       | Worker can message client through in-app chat
       |
  [5] PROOF_UPLOADED
       |
       | Worker submits proof: photos, form data, notes
       | System validates: GPS match, photo metadata, completeness
       | AI validation layer: Claude checks proof against task requirements
       |
  [6] PROOF_VALIDATED
       |
       | Auto-approved if AI confidence > 95%
       | Flagged for human review if AI confidence 70-95%
       | Rejected if AI confidence < 70% (worker can resubmit)
       | Client has 24-hour review window for manual override
       |
  [7] PAYOUT_RELEASED
       |
       | If approved: funds released to worker via Stripe Connect
       | Platform fee deducted
       | Both parties prompted to leave review
       | Task archived

  [X] DISPUTE FLOW (branching from any stage after acceptance):
       Worker or client raises dispute -> 48-hour resolution window ->
       Lucrex ops team reviews evidence -> ruling issued -> payout adjusted
```

**Task States (enum):**
`draft` | `posted` | `matching` | `accepted` | `in_progress` | `proof_submitted` |
`proof_validated` | `completed` | `disputed` | `cancelled` | `expired`

**Proof Types (per vertical):**

| Vertical | Required Proof | Validation Method |
|----------|---------------|-------------------|
| Retail Audit | 3+ geotagged photos, structured form (product name, shelf position, price, stock level) | GPS within 100m of target, EXIF timestamp within task window, Claude vision analysis |
| Property Check | 4+ exterior photos (N/S/E/W), roof photo, checklist | GPS within 200m, photo angle diversity check, completeness validation |
| Local Logistics | Pickup photo, delivery photo, receipt/signature photo, GPS trail | Chain-of-custody GPS trail, timestamp sequence validation |
| Event Verification | 1+ photo per location, foot traffic estimate, notes | GPS at each listed location, timestamp within window |

---

## 5. Revenue Model

### Revenue Streams

**Stream 1: Platform Take Rate (Primary)**
- 18% on completed tasks (split: 15% platform + 3% payment processing)
- Applied to the gross task value before worker payout
- Example: $40 retail audit task -> $7.20 platform fee -> $32.80 to worker
- Projected: 70% of total revenue

**Stream 2: API Subscriptions (Secondary)**
- Starter: $49/mo (50 tasks included)
- Growth: $149/mo (500 tasks included)
- Enterprise: Custom ($500-2000/mo)
- Projected: 15% of total revenue

**Stream 3: Worker Subscriptions (Tertiary)**
- Verified: $9.99/mo
- Pro: $24.99/mo
- Projected: 8% of total revenue

**Stream 4: Express Payout (Margin)**
- Standard payout: 3 business days (free)
- Express payout: Instant via Stripe Instant Payouts ($1.50 flat fee)
- Projected: 4% of total revenue

**Stream 5: Premium Placement (Future)**
- Workers can boost their profile visibility: $4.99/week
- Projected: 3% of total revenue

### Unit Economics

**Average Task Value (Blended):** $35
**Platform Take (18%):** $6.30/task
**Variable Cost per Task:**
- Payment processing (Stripe): ~$1.05 (3%)
- Proof storage (Supabase): ~$0.02
- AI validation (Claude API): ~$0.05
- Support allocation: ~$0.30
- **Total variable cost:** ~$1.42/task
- **Gross margin per task:** $4.88 (77.5% gross margin on platform fee)

**Break-even Analysis:**
- Fixed costs (Month 1): ~$500/mo (infra, domains, Stripe fees)
- Break-even at: ~103 completed tasks/month
- At 200 tasks/month: ~$476/mo profit before marketing spend

### Pricing Hypothesis
The 18% take rate is competitive with:
- TaskRabbit: 15% service fee (but charges client, not split)
- Uber: 25-30% take rate
- Fiverr: 20% seller fee
- Upwork: 10-20% sliding scale

At $35 average task value, 18% is $6.30 -- low enough that workers feel fairly
compensated, high enough to build a real business.

---

## 6. Tech Stack

### Architecture Overview

```
                    +------------------+
                    |   React/Vite (Cloudflare Pages) Site   |
                    | /field-ops       |
                    | (landing + dash) |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    Supabase      |
                    | Auth | DB | Store|
                    | RLS policies     |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------v---------+         +--------v---------+
     |   FastAPI on      |         |   MCP Server     |
     |   Oracle E5       |         |   (npm package)  |
     |   REST endpoints  |         |   Claude/agents  |
     +--------+---------+         +------------------+
              |
     +--------v---------+
     |   Stripe Connect  |
     |   Marketplace     |
     |   Payouts         |
     +------------------+
```

### Stack Detail

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Landing Page** | React/Vite (Cloudflare Pages) | everlightventures.io/field-ops -- worker signup, business signup, marketing |
| **Worker App** | Expo (React Native) | iOS + Android, camera, GPS, push notifications |
| **Business Dashboard** | React/Vite (Cloudflare Pages) or Next.js | Task management, proof review, analytics |
| **Auth** | Supabase Auth | Email/password + OAuth (Google, Apple for mobile) |
| **Database** | Supabase PostgreSQL | All core tables, RLS policies per role |
| **File Storage** | Supabase Storage | Proof photos/videos, max 10MB per file, 50MB per task |
| **API** | FastAPI on Oracle E5 (129.159.38.250) | REST endpoints, webhook dispatch, matching engine |
| **Agent Integration** | MCP Server (TypeScript) | npm package: @everlight/field-ops-mcp |
| **Payments** | Stripe Connect (Standard) | Marketplace mode, platform takes fee, workers get direct deposit |
| **Identity Verification** | Stripe Identity | For Verified/Pro worker tiers |
| **Geolocation** | Mapbox | Geocoding, radius matching, map display in dashboard |
| **Proof Validation AI** | Claude API (Haiku for speed) | Vision analysis of proof photos, structured output |
| **Ops Dashboard** | Django (existing hive_dashboard) | New "Field Ops" tab at :8504, task monitoring, dispute queue |
| **Alerts** | Slack (#field-ops channel) | Task disputes, high-value completions, fraud flags |
| **Background Jobs** | Supabase Edge Functions or Oracle cron | Matching, expiration, payout triggers |
| **Monitoring** | Existing Oracle watchdog | Health checks on FastAPI service |

### Infrastructure Cost Estimate (Month 1)

| Service | Cost |
|---------|------|
| Supabase (Free tier) | $0 |
| Oracle E5 (existing) | $0 (already running) |
| Stripe Connect | 2.9% + $0.30 per transaction (pass-through) |
| Mapbox (Free tier: 100k requests) | $0 |
| Claude API (Haiku, proof validation) | ~$10/mo at launch volume |
| React/Vite (Cloudflare Pages) (existing plan) | $0 |
| Expo (free tier) | $0 |
| Domain (field-ops subdirectory) | $0 |
| **Total new infrastructure cost** | **~$10/mo** |

We are building this on existing infrastructure. Almost zero incremental cost at
launch. This is the advantage of having Oracle, Supabase, and Stripe already wired.

---

## 7. Database Schema (Supabase)

### Table: `fo_workers`
```sql
CREATE TABLE fo_workers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  bio TEXT,
  profile_photo_url TEXT,
  skills TEXT[] NOT NULL DEFAULT '{}',
  -- skills enum values: retail_audit, property_check, delivery, errand,
  -- event_verification, photography, driving
  location GEOGRAPHY(POINT, 4326) NOT NULL,
  location_address TEXT,
  service_radius_miles INTEGER NOT NULL DEFAULT 15 CHECK (service_radius_miles BETWEEN 1 AND 50),
  rate_base NUMERIC(8,2) NOT NULL DEFAULT 20.00,
  rate_hourly NUMERIC(8,2),
  rate_mileage NUMERIC(4,2),
  availability JSONB DEFAULT '{}',
  -- {"mon": ["09:00-17:00"], "tue": ["09:00-17:00"], ...}
  on_demand BOOLEAN DEFAULT false,
  equipment TEXT[] DEFAULT '{}',
  languages TEXT[] DEFAULT '{en}',
  verification_tier TEXT NOT NULL DEFAULT 'basic'
    CHECK (verification_tier IN ('basic', 'verified', 'pro')),
  stripe_identity_id TEXT,
  stripe_connect_id TEXT,
  background_check_status TEXT DEFAULT 'pending'
    CHECK (background_check_status IN ('pending', 'passed', 'failed', 'not_required')),
  rating_avg NUMERIC(3,2) DEFAULT 0.00,
  rating_count INTEGER DEFAULT 0,
  tasks_completed INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_workers_location ON fo_workers USING GIST (location);
CREATE INDEX idx_fo_workers_skills ON fo_workers USING GIN (skills);
CREATE INDEX idx_fo_workers_tier ON fo_workers (verification_tier);
CREATE INDEX idx_fo_workers_active ON fo_workers (is_active) WHERE is_active = true;
```

### Table: `fo_tasks`
```sql
CREATE TABLE fo_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  posted_by UUID NOT NULL, -- references org or user
  posted_by_type TEXT NOT NULL CHECK (posted_by_type IN ('user', 'org', 'api')),
  api_key_id UUID REFERENCES fo_api_keys(id),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  vertical TEXT NOT NULL
    CHECK (vertical IN ('retail_audit', 'property_check', 'local_logistics', 'event_verification')),
  location GEOGRAPHY(POINT, 4326) NOT NULL,
  location_address TEXT NOT NULL,
  proof_schema JSONB NOT NULL DEFAULT '{}',
  -- Example: {"photos_min": 3, "geotagged": true, "form_fields": ["product_name", "shelf_position", "price"]}
  budget NUMERIC(8,2) NOT NULL CHECK (budget >= 5.00),
  max_duration_hours INTEGER NOT NULL DEFAULT 4 CHECK (max_duration_hours BETWEEN 1 AND 48),
  required_skills TEXT[] DEFAULT '{}',
  required_tier TEXT DEFAULT 'basic'
    CHECK (required_tier IN ('basic', 'verified', 'pro')),
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'posted', 'matching', 'accepted', 'in_progress',
      'proof_submitted', 'proof_validated', 'completed', 'disputed', 'cancelled', 'expired')),
  matched_worker_ids UUID[] DEFAULT '{}',
  expires_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_tasks_location ON fo_tasks USING GIST (location);
CREATE INDEX idx_fo_tasks_status ON fo_tasks (status);
CREATE INDEX idx_fo_tasks_vertical ON fo_tasks (vertical);
CREATE INDEX idx_fo_tasks_posted_by ON fo_tasks (posted_by);
```

### Table: `fo_bookings`
```sql
CREATE TABLE fo_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES fo_tasks(id) ON DELETE CASCADE,
  worker_id UUID NOT NULL REFERENCES fo_workers(id),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'accepted', 'in_progress', 'proof_submitted',
      'proof_validated', 'completed', 'disputed', 'cancelled')),
  accepted_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  proof_submitted_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  proof_urls TEXT[] DEFAULT '{}',
  proof_data JSONB DEFAULT '{}',
  -- Structured proof: form field responses, measurements, notes
  gps_trail JSONB DEFAULT '[]',
  -- Array of {lat, lng, timestamp} points during task
  ai_validation_score NUMERIC(5,2),
  ai_validation_notes TEXT,
  human_review_required BOOLEAN DEFAULT false,
  human_review_by UUID,
  human_review_at TIMESTAMPTZ,
  payout_amount NUMERIC(8,2),
  platform_fee NUMERIC(8,2),
  worker_rating INTEGER CHECK (worker_rating BETWEEN 1 AND 5),
  client_rating INTEGER CHECK (client_rating BETWEEN 1 AND 5),
  dispute_reason TEXT,
  dispute_resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_bookings_task ON fo_bookings (task_id);
CREATE INDEX idx_fo_bookings_worker ON fo_bookings (worker_id);
CREATE INDEX idx_fo_bookings_status ON fo_bookings (status);
```

### Table: `fo_payments`
```sql
CREATE TABLE fo_payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES fo_bookings(id),
  stripe_payment_intent_id TEXT,
  stripe_transfer_id TEXT,
  gross_amount NUMERIC(8,2) NOT NULL,
  platform_fee NUMERIC(8,2) NOT NULL,
  stripe_fee NUMERIC(8,2) NOT NULL,
  worker_payout NUMERIC(8,2) NOT NULL,
  express_payout_fee NUMERIC(8,2) DEFAULT 0.00,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'authorized', 'captured', 'transferred', 'failed', 'refunded')),
  payout_method TEXT DEFAULT 'standard'
    CHECK (payout_method IN ('standard', 'express')),
  payout_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_payments_booking ON fo_payments (booking_id);
CREATE INDEX idx_fo_payments_status ON fo_payments (status);
```

### Table: `fo_reviews`
```sql
CREATE TABLE fo_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES fo_bookings(id),
  reviewer_id UUID NOT NULL,
  reviewer_type TEXT NOT NULL CHECK (reviewer_type IN ('worker', 'client')),
  reviewee_id UUID NOT NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_reviews_booking ON fo_reviews (booking_id);
CREATE INDEX idx_fo_reviews_reviewee ON fo_reviews (reviewee_id);
```

### Table: `fo_api_keys`
```sql
CREATE TABLE fo_api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  org_name TEXT,
  key_hash TEXT NOT NULL UNIQUE,
  key_prefix TEXT NOT NULL, -- first 8 chars for display: "fo_live_abc..."
  tier TEXT NOT NULL DEFAULT 'starter'
    CHECK (tier IN ('starter', 'growth', 'enterprise')),
  tasks_included INTEGER NOT NULL DEFAULT 50,
  tasks_used_this_period INTEGER DEFAULT 0,
  period_start TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fo_api_keys_hash ON fo_api_keys (key_hash);
CREATE INDEX idx_fo_api_keys_user ON fo_api_keys (user_id);
```

### Table: `fo_orgs`
```sql
CREATE TABLE fo_orgs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_id UUID NOT NULL REFERENCES auth.users(id),
  stripe_customer_id TEXT,
  subscription_tier TEXT DEFAULT 'starter'
    CHECK (subscription_tier IN ('starter', 'growth', 'enterprise')),
  subscription_status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Row Level Security (RLS) Policies
```sql
-- Workers can read/update their own profile
ALTER TABLE fo_workers ENABLE ROW LEVEL SECURITY;
CREATE POLICY workers_own ON fo_workers
  FOR ALL USING (user_id = auth.uid());
CREATE POLICY workers_public_read ON fo_workers
  FOR SELECT USING (is_active = true);

-- Tasks visible to all authenticated users, editable by poster
ALTER TABLE fo_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tasks_read ON fo_tasks
  FOR SELECT USING (true);
CREATE POLICY tasks_write ON fo_tasks
  FOR ALL USING (posted_by = auth.uid());

-- Bookings visible to involved parties
ALTER TABLE fo_bookings ENABLE ROW LEVEL SECURITY;
CREATE POLICY bookings_access ON fo_bookings
  FOR ALL USING (
    worker_id IN (SELECT id FROM fo_workers WHERE user_id = auth.uid())
    OR task_id IN (SELECT id FROM fo_tasks WHERE posted_by = auth.uid())
  );
```

---

## 8. REST API Endpoints

### Authentication
All API calls require header: `Authorization: Bearer fo_live_<key>`

### Endpoints

```
# Workers
GET    /api/v1/workers/search?skills=retail_audit&lat=34.05&lng=-118.24&radius=10&max_rate=30
GET    /api/v1/workers/{worker_id}

# Tasks
POST   /api/v1/tasks
GET    /api/v1/tasks/{task_id}
PATCH  /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}
GET    /api/v1/tasks?status=posted&vertical=retail_audit

# Bookings
POST   /api/v1/bookings                    # {task_id, worker_id}
GET    /api/v1/bookings/{booking_id}
PATCH  /api/v1/bookings/{booking_id}       # Update status, submit proof
GET    /api/v1/bookings?task_id=xxx

# Payments
POST   /api/v1/payments/{booking_id}/release
GET    /api/v1/payments/{booking_id}

# Webhooks (client registers callback URL)
POST   /api/v1/webhooks
GET    /api/v1/webhooks
DELETE /api/v1/webhooks/{webhook_id}
```

### Webhook Events
```json
{
  "event": "task.worker_matched",
  "data": { "task_id": "...", "worker_id": "...", "worker_name": "...", "eta_minutes": 25 }
}

{
  "event": "booking.proof_submitted",
  "data": { "booking_id": "...", "proof_urls": [...], "proof_data": {...} }
}

{
  "event": "booking.completed",
  "data": { "booking_id": "...", "ai_validation_score": 97.5, "payout_amount": 32.80 }
}

{
  "event": "booking.disputed",
  "data": { "booking_id": "...", "reason": "...", "resolution_deadline": "2026-04-01T00:00:00Z" }
}
```

### Example: AI Agent Creates a Retail Audit Task
```python
import requests

API_KEY = "fo_live_abc123..."
BASE = "https://api.everlightventures.io/field-ops/v1"

# 1. Create task
task = requests.post(f"{BASE}/tasks", headers={"Authorization": f"Bearer {API_KEY}"}, json={
    "title": "Verify Acme Cereal shelf placement at Target #4521",
    "description": "Go to Target store #4521, find the cereal aisle, photograph Acme Crunch box placement. Note: shelf position (eye/mid/bottom), facing count, price tag.",
    "vertical": "retail_audit",
    "location_address": "1234 Main St, Los Angeles, CA 90012",
    "budget": 25.00,
    "max_duration_hours": 4,
    "proof_schema": {
        "photos_min": 3,
        "geotagged": True,
        "form_fields": [
            {"name": "shelf_position", "type": "select", "options": ["eye_level", "mid", "bottom", "endcap", "not_found"]},
            {"name": "facing_count", "type": "number"},
            {"name": "price", "type": "currency"},
            {"name": "stock_level", "type": "select", "options": ["full", "partial", "low", "out_of_stock"]}
        ]
    },
    "required_tier": "verified"
}).json()

task_id = task["id"]

# 2. System auto-matches worker, sends webhook when accepted
# 3. Worker completes task, submits proof
# 4. Webhook fires with proof data
# 5. Auto-approve or review
# 6. Release payment
requests.post(f"{BASE}/payments/{booking_id}/release",
    headers={"Authorization": f"Bearer {API_KEY}"})
```

---

## 9. MCP Server Tools

Package: `@everlight/field-ops-mcp`

```typescript
// MCP Tool Definitions

tools: [
  {
    name: "search_workers",
    description: "Search for available Field Ops workers by skills, location, and rate",
    inputSchema: {
      type: "object",
      properties: {
        skills: { type: "array", items: { type: "string" }, description: "Required skills" },
        latitude: { type: "number", description: "Search center latitude" },
        longitude: { type: "number", description: "Search center longitude" },
        radius_miles: { type: "number", description: "Search radius in miles", default: 15 },
        max_rate: { type: "number", description: "Maximum base rate per task" },
        min_tier: { type: "string", enum: ["basic", "verified", "pro"] },
        min_rating: { type: "number", description: "Minimum rating (1-5)" }
      },
      required: ["skills", "latitude", "longitude"]
    }
  },
  {
    name: "get_worker",
    description: "Get detailed profile for a specific Field Ops worker",
    inputSchema: {
      type: "object",
      properties: {
        worker_id: { type: "string", description: "Worker UUID" }
      },
      required: ["worker_id"]
    }
  },
  {
    name: "create_task",
    description: "Create a new field task for a human worker to complete",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        description: { type: "string" },
        vertical: { type: "string", enum: ["retail_audit", "property_check", "local_logistics", "event_verification"] },
        location_address: { type: "string" },
        budget: { type: "number", minimum: 5 },
        max_duration_hours: { type: "number", default: 4 },
        proof_schema: { type: "object" },
        required_tier: { type: "string", enum: ["basic", "verified", "pro"], default: "basic" }
      },
      required: ["title", "description", "vertical", "location_address", "budget"]
    }
  },
  {
    name: "book_worker",
    description: "Book a specific worker for a task",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        worker_id: { type: "string" }
      },
      required: ["task_id", "worker_id"]
    }
  },
  {
    name: "get_task",
    description: "Get task details and current status",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" }
      },
      required: ["task_id"]
    }
  },
  {
    name: "get_booking",
    description: "Get booking details including proof data and validation status",
    inputSchema: {
      type: "object",
      properties: {
        booking_id: { type: "string" }
      },
      required: ["booking_id"]
    }
  },
  {
    name: "release_payment",
    description: "Approve and release payment for a completed booking",
    inputSchema: {
      type: "object",
      properties: {
        booking_id: { type: "string" }
      },
      required: ["booking_id"]
    }
  },
  {
    name: "list_my_tasks",
    description: "List all tasks posted by the authenticated account",
    inputSchema: {
      type: "object",
      properties: {
        status: { type: "string" },
        limit: { type: "number", default: 20 },
        offset: { type: "number", default: 0 }
      }
    }
  }
]
```

**Installation for AI Agents:**
```bash
# Claude Desktop / MCP-compatible agents
npx @everlight/field-ops-mcp --api-key fo_live_abc123
```

**Usage in Claude:**
"Search for verified workers near downtown LA who can do retail audits for under $30"
-> Claude calls `search_workers(skills=["retail_audit"], latitude=34.05, longitude=-118.24, max_rate=30, min_tier="verified")`

---

## 10. MVP Timeline (4-Week Sprint)

### Week 1: Foundation (Schema + Signup + Landing)
**Owner:** Forge (Codex Labs TL) + Atlas Vega (Architecture)

| Day | Deliverable |
|-----|------------|
| Mon | Supabase migration: all 7 tables + indexes + RLS policies |
| Tue | React/Vite (Cloudflare Pages) landing page: /field-ops with hero, value props, worker signup form, business waitlist |
| Wed | Worker signup flow: Supabase Auth + profile creation + skill selection |
| Thu | Business signup flow: org creation + Stripe customer + API key generation |
| Fri | Seed data: 10 test workers, 5 test tasks, proof schema templates per vertical |

**Exit Criteria:** Workers can sign up, businesses can get API keys, schema is live.

### Week 2: Core Loop (Tasks + Matching + Proof)
**Owner:** Forge + Gears Tanaka (Workflow)

| Day | Deliverable |
|-----|------------|
| Mon | FastAPI service on Oracle E5: POST/GET tasks, auth middleware |
| Tue | Matching engine: geospatial query (PostGIS on Supabase), skill filter, availability check |
| Wed | Worker notification system: Supabase Edge Function triggers push to matched workers |
| Thu | Proof upload flow: Supabase Storage integration, EXIF metadata extraction, GPS validation |
| Fri | AI proof validation: Claude Haiku vision endpoint, confidence scoring, auto-approve logic |

**Exit Criteria:** Full task lifecycle works end-to-end in test environment.

### Week 3: Money (Stripe + Payouts + API)
**Owner:** Forge + Cash Moreno (Commission Audit) + Shield Navarro (Financial Safeguard)

| Day | Deliverable |
|-----|------------|
| Mon | Stripe Connect onboarding flow for workers (Standard accounts) |
| Tue | Payment capture on task creation (hold funds), release on completion |
| Wed | Platform fee calculation, worker payout via Stripe Transfer |
| Thu | Express payout option (Stripe Instant Payouts), payout dashboard for workers |
| Fri | REST API hardening: rate limiting, error handling, webhook dispatch |

**Exit Criteria:** Real money flows. Worker gets paid. Platform takes its cut.

### Week 4: Integration + Polish + Launch
**Owner:** Full team

| Day | Deliverable |
|-----|------------|
| Mon | MCP server package: TypeScript, all 8 tools, npm publish |
| Tue | Business dashboard on React/Vite (Cloudflare Pages): task list, proof review, analytics |
| Wed | Django ops integration: Field Ops tab, dispute queue, revenue metrics |
| Thu | Slack alerts: #field-ops channel, dispute notifications, daily summary |
| Fri | Launch: Product Hunt listing prepared, docs site live, first 10 beta businesses invited |

**Exit Criteria:** Product is live, API works, MCP server installable, first real tasks flowing.

---

## 11. Go-to-Market Strategy

### Phase 1: Beta Launch (Week 4-6)
- **Invite 10 beta businesses** from existing Everlight network + Broker OS leads
- **Recruit 50 workers** in 3 metro areas: Los Angeles, Phoenix, Dallas
  (warm climates = more outdoor tasks, lower barrier to field work)
- **Pricing:** Free API tier for beta businesses (50 tasks, no monthly fee)
- **Goal:** 100 completed tasks, 4.5+ average satisfaction

### Phase 2: Public Launch (Week 7-8)
- **Product Hunt launch:** "The API that gives AI agents real-world hands"
- **Hacker News:** "Show HN: Field Ops -- hire verified humans from your AI agent"
- **Content marketing:**
  - Blog: "Why AI Needs Humans on the Ground" (Nora Blaine + Vera Lux)
  - Blog: "How I Built a Retail Audit Bot That Actually Walks Into Stores"
  - Twitter/X thread: Live demo of Claude agent dispatching a Field Ops worker
  - YouTube: Screen recording of full lifecycle -- agent creates task, worker completes, proof validated
- **Developer outreach:**
  - LangChain community Discord
  - CrewAI community
  - Claude MCP tool directory
  - r/LocalLLaMA, r/ChatGPT, r/artificial

### Phase 3: Vertical Expansion (Month 2-3)
- **Amazon seller groups:** Facebook groups (100k+ members), Amazon seller forums
  - Hook: "Verify your product is actually on the shelf -- from your AI dashboard"
- **Solar companies:** Solar industry LinkedIn groups, solar installer conferences
  - Hook: "Pre-qualify every site before you roll a truck"
- **Property managers:** BiggerPockets, real estate investor meetups
  - Hook: "Eyes on your property anywhere in the country, on demand"

### Phase 4: Partnership (Month 3-6)
- **AI agent framework partnerships:**
  - Official LangChain tool integration
  - CrewAI tool marketplace listing
  - Anthropic MCP tool directory listing
- **Marketplace partnerships:**
  - Amazon Seller Central integration (future)
  - Zillow/Redfin partnership for property checks (future)

### Viral Mechanics
- Workers earn referral bonus ($10) for each new worker who completes 5 tasks
- Businesses earn $50 API credit for each referred business
- "Powered by Everlight Field Ops" watermark on proof photos (optional, free tier)

---

## 12. Revenue Projections

### Conservative Model

| Month | Workers | Active Businesses | Tasks/Mo | Avg Task Value | GMV | Platform Rev (18%) | API Subs | Worker Subs | Express Payouts | Total Revenue |
|-------|---------|------------------|----------|---------------|-----|-------------------|----------|-------------|----------------|---------------|
| 1 | 50 | 10 | 80 | $30 | $2,400 | $432 | $0 (beta) | $50 | $20 | **$502** |
| 2 | 150 | 25 | 250 | $32 | $8,000 | $1,440 | $490 | $150 | $60 | **$2,140** |
| 3 | 400 | 50 | 600 | $33 | $19,800 | $3,564 | $1,470 | $400 | $140 | **$5,574** |
| 4 | 700 | 80 | 1,200 | $34 | $40,800 | $7,344 | $2,940 | $700 | $280 | **$11,264** |
| 5 | 1,000 | 120 | 2,000 | $35 | $70,000 | $12,600 | $4,900 | $1,000 | $460 | **$18,960** |
| 6 | 1,500 | 180 | 3,500 | $35 | $122,500 | $22,050 | $7,350 | $1,500 | $800 | **$31,700** |
| 9 | 4,000 | 400 | 10,000 | $36 | $360,000 | $64,800 | $15,000 | $4,000 | $2,200 | **$86,000** |
| 12 | 8,000 | 800 | 25,000 | $37 | $925,000 | $166,500 | $30,000 | $8,000 | $5,500 | **$210,000** |

### Key Assumptions
- Worker activation rate: 40% of registered workers complete 1+ task/month
- Business retention: 85% month-over-month after first completed task
- Average tasks per active business: 8/month (Starter) to 25/month (Growth)
- Verified worker conversion: 30% of active workers upgrade to paid tier
- Express payout usage: 20% of payouts use express option

### Path to $10k/mo (Everlight Revenue Target)
At Month 4, Field Ops alone could hit $11k/mo. Combined with existing revenue
streams (Onyx POS, Broker OS, Publishing, XLM Bot), this accelerates the
$10k/mo target significantly.

---

## 13. Risk Mitigation

### Risk 1: Worker Safety
- **Mitigation:** Task category restrictions (no entry into private residences without
  client present, no tasks after 10 PM, no tasks requiring specialized equipment
  without verified credentials)
- **Protocol:** Workers can cancel any task that feels unsafe without rating penalty.
  Emergency button in app calls 911 + alerts ops team.
- **Insurance:** Require workers to acknowledge independent contractor status.
  Explore platform liability insurance ($500-1000/yr) after launch validation.
- **Owner:** Justine Park (Compliance)

### Risk 2: Proof Fraud
- **Mitigation:** Multi-layer validation:
  1. EXIF metadata check (GPS, timestamp, device)
  2. Claude vision analysis (does the photo match the task description?)
  3. Cross-reference: GPS trail must show worker traveled to task location
  4. Random human spot-checks on 5% of completed tasks
- **Escalation:** Three failed validations = account suspended for review
- **Owner:** Shield Navarro (Financial Safeguard)

### Risk 3: Marketplace Chicken-and-Egg
- **Mitigation:** Seed supply side first in 3 cities. Use Craigslist, local Facebook
  groups, and gig worker communities to recruit initial 50 workers before opening
  demand side. Guarantee minimum earnings ($50) for first 5 completed tasks to
  incentivize early workers.
- **Owner:** Piper Reeves (Outreach) + Hammer Knox (Follow-up)

### Risk 4: Payment Disputes
- **Mitigation:** Escrow model -- funds held until proof validated. 24-hour review
  window for clients. Structured dispute process:
  1. Either party raises dispute
  2. 48-hour resolution window
  3. Ops team reviews all evidence (proof photos, GPS data, messages)
  4. Ruling issued, funds redistributed
  5. Appeal process: second review by different ops member
- **Owner:** Cash Moreno (Commission Audit)

### Risk 5: Legal / Contractor Classification
- **Mitigation:** Workers are independent contractors, not employees. Platform does
  not control how/when they work -- only provides matching. Legal review of ToS
  by state (California AB5 implications: workers choose tasks, set rates, use own
  equipment = likely pass ABC test). Include arbitration clause.
- **Action:** Consult employment attorney before launch ($500-1000).
- **Owner:** Justine Park (Compliance)

### Risk 6: Low Task Quality
- **Mitigation:** Proof schema enforcement (minimum photos, required fields,
  GPS validation). Rating system with consequences: workers below 3.5 rating
  after 10 tasks are deactivated. Onboarding includes task completion tutorial
  with sample proof submission.
- **Owner:** Quinn Sharp (QA Gate)

### Risk 7: Competitive Entry
- **Mitigation:** First-mover advantage in AI-agent-to-human vertical. MCP server
  integration creates switching costs. Build network effects: more workers = faster
  matching = better client experience = more clients = more tasks = more workers.
  Vertical specialization (proof schemas, validation AI) creates defensibility
  that generic platforms cannot easily replicate.
- **Owner:** Slate Mercer (Strategic Modeling)

---

## 14. Competitive Advantage

### Why Everlight Wins This

**1. Existing Infrastructure (Zero Cold Start)**
We already have:
- Supabase project (auth, DB, storage) -- no new accounts needed
- Oracle E5 server (FastAPI deployment) -- no new infra cost
- Stripe integration (payments wired) -- no new payment setup
- Django ops dashboard (monitoring) -- just add a tab
- Slack alerting (real-time ops) -- just add a channel
- Claude API access (AI validation) -- already integrated
- React/Vite (Cloudflare Pages) site (landing pages) -- just add a route
- MCP development experience (built broker-os MCP) -- pattern exists

**Estimated time saved vs. greenfield:** 3-4 weeks.

**2. AI-Native from Day One**
Unlike TaskRabbit, Thumbtack, or even RentAHuman.ai, Field Ops is built
API-first and MCP-first. AI agents are not an afterthought -- they are the
primary customer. The proof validation layer uses Claude vision, not manual
review. The matching engine is designed for programmatic access, not human
browsing. This is a platform AI agents want to use.

**3. Vertical Focus = Faster Trust**
Generic gig platforms serve everyone and optimize for no one. Field Ops
serves four specific verticals with custom proof schemas, validation logic,
and onboarding flows for each. A retail audit task has different requirements
than a property check -- and our platform knows the difference.

**4. B2B First = Better Economics**
Consumer gig platforms fight for $10-20 tasks with razor-thin margins.
B2B field verification commands $25-75/task with enterprise clients who
pay monthly subscriptions and submit hundreds of tasks. Higher LTV, lower
churn, better unit economics.

**5. Hive Mind Integration**
Field Ops is not a standalone product. It plugs into the Everlight ecosystem:
- Broker OS can dispatch field verification as part of deal due diligence
- Content Factory can use field workers for location-based content capture
- AI Consulting clients can integrate Field Ops into their AI workflows
- The Hive Mind itself can dispatch workers through MCP tools

**6. Proof Validation Moat**
Over time, we accumulate thousands of validated proof submissions. This
training data improves our AI validation accuracy, reducing fraud and
manual review costs. Competitors starting later cannot replicate this
data advantage.

---

## 15. Success Metrics

### North Star Metric
**Completed Tasks per Month** -- this is the single number that drives everything.
More completed tasks = more revenue, more data, more network effects.

### Leading Indicators
| Metric | Week 1 Target | Month 1 Target | Month 3 Target |
|--------|--------------|----------------|----------------|
| Registered workers | 20 | 50 | 400 |
| Active workers (1+ task/mo) | 5 | 20 | 160 |
| Registered businesses | 5 | 10 | 50 |
| Tasks posted | 10 | 80 | 600 |
| Tasks completed | 5 | 60 | 500 |
| Completion rate | 50% | 75% | 85% |
| Avg AI validation score | N/A | 80+ | 90+ |
| Worker satisfaction (NPS) | N/A | 30+ | 50+ |
| Client satisfaction (NPS) | N/A | 40+ | 60+ |

### Lagging Indicators
| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| Monthly revenue | $500 | $5,500 | $31,700 |
| Gross margin | 70% | 75% | 78% |
| Worker churn (monthly) | 30% | 20% | 15% |
| Business churn (monthly) | 25% | 15% | 10% |
| Avg time to match | 2 hours | 45 min | 15 min |
| Avg time to completion | 6 hours | 4 hours | 3 hours |
| Dispute rate | 10% | 5% | 2% |

---

## 16. Scope Decision: Viable = TRUE

**Product:** Everlight Field Ops
**Viable:** YES
**Confidence:** HIGH

**Rationale (Road Harper):**
This passes all Phase 0 gate criteria:
1. Clear ICP with willingness to pay (Amazon sellers, solar companies, property managers)
2. Revenue model with multiple streams and healthy unit economics (77.5% gross margin)
3. Defensible moat (AI-native, vertical proof schemas, data advantage)
4. Buildable on existing infrastructure (near-zero incremental infra cost)
5. 4-week MVP timeline is aggressive but achievable with existing team
6. Path to $10k/mo within 4 months aligns with Everlight revenue targets
7. Natural ecosystem integration with Broker OS, AI Consulting, and Hive Mind

**Biggest Risk:** Marketplace chicken-and-egg. Mitigated by seeding supply
side first in 3 cities with guaranteed minimum earnings.

**Recommendation:** Proceed to Phase 1 build. Start Week 1 sprint immediately.

---

*Filed by Road Harper, SaaS PM, Codex Labs*
*Reviewed by: Atlas Vega (Architecture), Slate Mercer (Strategy), Justine Park (Compliance), Cash Moreno (Revenue)*
*Approved by: Marcus Cole (Chief Operator)*
*For: Lucrex, King of Divine Light*
