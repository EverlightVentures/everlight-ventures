# Everlight Field Ops -- Landing Page Spec for React/Vite (Cloudflare Pages)
## Route: everlightventures.io/field-ops
## Framework: PAS (Problem-Agitate-Solve)
## Last Updated: 2026-03-24
## Author: Rocket Kim (Codex Labs) with Piper Reeves (Content), Filter Banks (Pricing), Justine Voss (Compliance)

---

## 1. Hero Section

**Background:** Split-screen layout. Left side: a smartphone showing a push notification "New Task: Shelf Audit at Target -- $35 -- 0.8 mi away" with a map pin. Right side: a worker in a store aisle holding up a phone, capturing a photo of a product shelf. Overlay gradient from dark left to bright right. Everlight gold accent line separating the two panels.

**Headline (H1):**
Your AI Needs Hands on the Ground

**Subheadline (H2):**
Hire verified local humans for field tasks. Proof-based. API-ready. Pay on completion.

**CTA Buttons (side by side, equal weight):**

| Button | Label | Style | Destination |
|--------|-------|-------|-------------|
| Primary Left | I Want to Work | Solid gold (#D4A843), white text | /field-ops/worker-signup |
| Primary Right | I Need Field Ops | Solid dark (#1A1A2E), gold text | /field-ops/business-signup |

**Social Proof Bar (below CTAs):**
"Launching Spring 2026 -- 500+ workers already on the waitlist across 12 cities"

---

## 2. Problem Section (PAS -- Problem)

**Section Header:** The Last Mile is Still a Human Mile

**Body Copy:**
Your AI can research, analyze, write, and plan. But it cannot walk into a store, take a photo of a shelf, or confirm a delivery arrived intact. Remote work solved the office -- but the physical world still needs boots on the ground.

Businesses spend thousands on travel, contractors, and guesswork for tasks that a local human could complete in 30 minutes with proof.

---

## 3. Agitate Section (PAS -- Agitate)

**Section Header:** Current Options Are Broken

**Three pain-point cards (icon + short text):**

1. **Gig platforms are bloated** -- You do not need an app with 47 categories. You need one verified person, one task, one proof photo.
2. **Freelancer marketplaces are slow** -- Posting a job, vetting applicants, negotiating rates, waiting days. For a 20-minute errand.
3. **AI agents hit a wall** -- Your agent can plan the task but cannot execute it. There is no API for "go check if the sign is up."

---

## 4. How It Works (PAS -- Solve, 3 Columns)

**Section Header:** Three Steps. Real-World Results.

### Column 1: Post a Task
**Icon:** Clipboard with plus sign
**Body:** Describe what needs doing. Set location, proof type (photo, video, receipt, signature), and budget. Our REST API and MCP tools let AI agents post tasks programmatically -- no human in the loop required.

### Column 2: Worker Matches
**Icon:** Location pin with checkmark
**Body:** Verified local humans accept your task. Matched by proximity, skills, and rating. Average acceptance time: under 15 minutes in active markets. You see their profile, rating, and verification level before they start.

### Column 3: Proof and Pay
**Icon:** Camera shutter with dollar sign
**Body:** Worker completes the task and uploads proof -- photo, video, receipt scan, or GPS-stamped check-in. You review and approve. Payment releases from escrow. Dispute? Our resolution team handles it within 24 hours.

---

## 5. Use Cases (4 Cards)

**Section Header:** What Can Field Ops Handle?

### Card 1: Retail Verification
**Icon:** Shopping cart with magnifying glass
**Image:** Store aisle with phone overlay showing "Shelf Audit Complete"
**Body:** Shelf checks, product availability, competitor pricing photos, planogram compliance, out-of-stock verification. Perfect for Amazon sellers, CPG brands, and retail analytics companies.
**Tag:** Most Popular

### Card 2: Property and Site Checks
**Icon:** House with camera
**Image:** Worker photographing a rooftop from ground level
**Body:** Solar site surveys, rental walkarounds, construction progress documentation, vacancy verification, curb appeal assessment. Insurance adjusters, solar installers, and property managers use this daily.

### Card 3: Local Logistics
**Icon:** Package with route line
**Image:** Worker holding a receipt next to a delivered package
**Body:** Pickup and dropoff, receipt capture, line-standing, errand execution, document delivery. When shipping is too slow and couriers are too expensive for a single local task.

### Card 4: Event Verification
**Icon:** Calendar with camera
**Image:** Flyer posted on a community board, phone capturing it
**Body:** Flyer posting confirmation, venue readiness checks, attendance proof, signage verification. Event organizers and marketing agencies confirm execution without sending their own team.

---

## 6. For AI Agents Section

**Section Header:** Built for the Agent Economy

**Body:**
Your AI agent should not stop at "I recommend someone checks the site." It should check the site. Everlight Field Ops gives your agent a REST API and an MCP server to search workers, post tasks, track completion, and release payments -- all programmatically.

**Code Snippet (dark background, syntax highlighted):**

```json
// MCP Tool: post_field_task
{
  "tool": "everlight_field_ops.post_task",
  "params": {
    "title": "Verify storefront signage at 412 Main St",
    "location": { "lat": 37.7749, "lng": -122.4194 },
    "proof_type": "photo",
    "budget_usd": 25.00,
    "deadline_hours": 4,
    "instructions": "Take a clear photo of the front signage from across the street. Include the full storefront in frame."
  }
}

// Response
{
  "task_id": "ft_8x92kLm",
  "status": "matching",
  "estimated_match_time_min": 12,
  "worker_pool_nearby": 8
}
```

**Sub-features (3 small icons inline):**

| Feature | Description |
|---------|-------------|
| REST API | Full CRUD on tasks, workers, payments. OpenAPI 3.0 spec. |
| MCP Server | Drop into Claude, Cursor, or any MCP-compatible agent. |
| Webhooks | Real-time status updates: matched, in-progress, proof-submitted, completed. |

**CTA:** "Read the API Docs" (links to /field-ops/developers)

---

## 7. Pricing Section

**Section Header:** Simple Pricing. No Surprises.

### Worker Tiers

| Tier | Price | Includes |
|------|-------|----------|
| Free Worker | $0/mo | Accept tasks, earn per-completion, basic profile |
| Verified Worker | $9.99/mo | Priority task placement, unlimited bounty access, verified ID badge, faster payouts (next-day vs. weekly) |

### Business Tiers

| Tier | Price | Tasks/mo | API Access | Support |
|------|-------|----------|------------|---------|
| Starter | $49/mo | 50 | REST API | Email (48h) |
| Growth | $149/mo | 500 | REST API + MCP + Webhooks | Priority email (24h) |
| Enterprise | Custom | Unlimited | Full API + dedicated MCP server + SLA | Dedicated account manager |

### Platform Fee
15% on every completed task. Deducted from payment before worker payout. No hidden fees. No surge pricing.

**Example Math (callout box):**
"You post a $40 shelf audit. Worker completes it. Platform takes $6 (15%). Worker receives $34. You pay $40 + your subscription. That is it."

**CTA:** "Start Free" (business signup) | "Join as a Worker" (worker signup)

---

## 8. Trust and Safety Section

**Section Header:** Built on Proof, Not Promises

**Body:**
Every worker can be identity-verified. Every task requires proof of completion. Every payment is held in escrow until you approve the work. If something goes wrong, our dispute resolution team responds within 24 hours.

**Trust Badges (4 icons in a row):**

| Badge | Label |
|-------|-------|
| Shield with lock | Stripe-Secured Payments |
| Camera | Photo/Video Proof Required |
| Map pin with check | GPS Location Verification |
| Scale of justice | 24-Hour Dispute Resolution |

**Additional trust signals:**
- "Workers undergo ID verification via Stripe Identity"
- "All proof media is timestamped and GPS-tagged"
- "Escrow holds funds until task is approved or auto-released after 48h review window"
- "Platform maintains a 4.8-star average worker rating"

---

## 9. Testimonial / Social Proof Section (Pre-Launch)

**Section Header:** Early Access Partners

**Placeholder cards (3):**
- "We used Field Ops to verify 200 retail locations in a weekend. Nothing else comes close." -- [Beta Partner, CPG Brand]
- "Our AI agent posts site checks automatically. We went from 3-day turnaround to same-day." -- [Beta Partner, Solar Company]
- "I made $600 in my first week doing errands and photo tasks near my house." -- [Beta Worker, Austin TX]

*Note: Replace with real testimonials once beta completes.*

---

## 10. CTA Footer Section

**Section Header:** Get in Early

**Two-column layout:**

### Left Column: Worker Signup
**Header:** Start Earning
**Form Fields:**
- Full Name (text)
- Email (email)
- City (text with autocomplete)
- Skills (multi-select: photography, driving, retail experience, construction, general errands)
- Submit: "Join the Worker Waitlist"

### Right Column: Business / Agent Signup
**Header:** Get Field Ops for Your Team
**Form Fields:**
- Company Name (text)
- Work Email (email)
- Estimated Monthly Tasks (dropdown: 1-50, 51-200, 201-500, 500+)
- Use Case (dropdown: Retail, Property, Logistics, Events, AI Agent Integration, Other)
- Submit: "Request Early Access"

**Bottom Banner:**
"Launching Spring 2026. Early access members get 60 days free on any business plan."

---

## 11. SEO Metadata

```json
{
  "title": "Everlight Field Ops | Hire Verified Humans for AI-Powered Field Tasks",
  "description": "Post field tasks, match with verified local workers, get photo/video proof on completion. REST API and MCP tools for AI agents. Pay only on completion.",
  "og_title": "Your AI Needs Hands on the Ground",
  "og_description": "Hire verified local humans for retail audits, property checks, deliveries, and errands. Proof-based. API-ready.",
  "og_image": "field-ops-hero-split-screen.jpg",
  "canonical": "https://everlightventures.io/field-ops",
  "keywords": [
    "field task marketplace",
    "hire local workers",
    "AI agent field tasks",
    "retail audit service",
    "property check service",
    "proof-based task platform",
    "MCP tools field work",
    "gig economy API",
    "field verification service",
    "Everlight Field Ops"
  ]
}
```

---

## 12. Technical Notes for React/Vite (Cloudflare Pages) Implementation

- **Route:** /field-ops (add to React/Vite (Cloudflare Pages) router alongside existing tabs)
- **Supabase tables needed:** field_ops_waitlist_workers, field_ops_waitlist_businesses
- **Form submissions:** Insert into Supabase, trigger confirmation email via Resend
- **Analytics events:** field_ops_hero_cta_click, field_ops_worker_signup, field_ops_business_signup, field_ops_pricing_view
- **Responsive:** Mobile-first. Hero section stacks vertically on mobile. Pricing table scrolls horizontally.
- **Animations:** Subtle fade-in on scroll for each section. Code snippet has typing animation on first view.
- **Color scheme:** Consistent with Everlight brand -- dark backgrounds (#1A1A2E), gold accents (#D4A843), white text.

---

*Prepared by Rocket Kim (GTM, Codex Labs) with input from Piper Reeves (copy), Filter Banks (pricing model), and Justine Voss (compliance review on escrow and dispute language). Review with legal before publishing trust/safety claims.*
