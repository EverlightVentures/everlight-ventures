# Onyx POS -- Next Project Plan
**Verdict Date**: 2026-02-27 | **Status**: SELECTED -- Fastest to Market

---

## Verdict: Onyx POS Wins

### Ground-Truth Audit Results

| Product | What It Is | Code State | Deployed? | Time to Sellable MVP |
|---|---|---|---|---|
| **Onyx POS (MGN)** | Python POS for small retail/nursery | 2,566 lines, working beta | YES -- live at MGN (Nov-Dec 2025 data) | **4-6 weeks** |
| **Alley Kings** | Unity mobile game (Clash Royale clone) | C# scripts only, no assets/art/scenes | NO -- needs full Unity project | 6-12+ months |
| **Onyx POS brand** | Same codebase as MGN, in 01_OnyxPOS folder | 2,038 lines partial refactor | NO -- needs multi-tenant | 4-6 weeks |

**Onyx POS wins.** It's already been in production at a real business. MGN IS the first customer. The product just needs to be stripped of MGN-specific hardcoding and turned into a generic, sellable SaaS POS.

Alley Kings is a Unity game -- different market, requires $99/yr Apple Developer account, App Store approval, full visual asset pipeline, and game-market distribution. Way too long a runway.

---

## What Onyx POS Already Has (Skip Building These)

- [x] Sales transaction flow
- [x] Inventory management
- [x] Employee management + time clock
- [x] Receipts (text/print)
- [x] Daily reports / audit logs
- [x] Payroll module
- [x] Role-based access (owner vs employee)
- [x] Remote access via ngrok
- [x] Start/stop scripts (START_POS.sh, STOP_POS.sh)
- [x] One live reference customer (Mountain Gardens Nursery)

---

## What Needs To Be Built / Done

### Phase 1: Codebase Cleanup (Week 1-2)
- [ ] **De-MGN the code** -- remove all "Mountain Gardens Nursery" hardcoded strings
- [ ] **Config file** -- business name, address, tax rate, logo all in `config.json`
- [ ] **Multi-tenant scaffold** -- each customer gets their own data directory/DB
- [ ] **Web UI** -- confirm browser-based Flask/Streamlit works (not just local terminal)
- [ ] **`.env` / secrets** -- no hardcoded passwords, API keys
- [ ] **Requirements.txt / Dockerfile** -- so any machine can run it in 5 minutes

### Phase 2: Payments + Accounts (Week 2-3)
- [ ] **Stripe account** -- create at stripe.com (free to create, 2.9% + $0.30/tx)
  - Needed for: subscription billing of SaaS customers
  - Optional: Stripe Terminal for in-store card payments
- [ ] **Payment processor for POS transactions** -- options:
  - Stripe Terminal (card readers $299)
  - Square (free reader, but separate ecosystem)
  - Start: cash + manual card entry to keep it simple
- [ ] **Stripe subscription tiers** (see Pricing below)

### Phase 3: Infrastructure (Week 2-3)
- [ ] **Domain** -- register `onyxpos.com` or `tryonyxpos.com` (~$12/yr on Namecheap)
- [ ] **Hosting** -- DigitalOcean Droplet ($6/mo) or Oracle Always Free (current preference)
- [ ] **Database** -- SQLite for MVP, PostgreSQL for multi-tenant scale
- [ ] **SSL cert** -- Let's Encrypt via Certbot (free)
- [ ] **Backups** -- daily backup of customer data dirs

### Phase 4: Launch Assets (Week 3-4)
- [ ] **Landing page** -- pain hook, demo video, pricing, "Get Started" CTA
- [ ] **Demo environment** -- sandbox login with fake data for prospects
- [ ] **Pricing page** -- see Pricing section below
- [ ] **Onboarding doc** -- "How to get started in 30 min" PDF/page
- [ ] **Privacy policy + Terms of Service** -- use a generator (Termly, free tier)

### Phase 5: First Sales (Week 4-6)
- [ ] **Outreach list** -- 20 small retail businesses (nurseries, boutiques, food trucks, barbershops)
- [ ] **Demo script** -- 15 min Zoom demo flow
- [ ] **Pilot offer** -- first 3 customers free for 60 days in exchange for testimonial + feedback
- [ ] **Referral incentive** -- 1 free month for each paid referral

---

## Pricing Model

| Tier | Price/mo | What's Included |
|---|---|---|
| **Starter** | $49/mo | 1 location, up to 3 employees, basic reports |
| **Growth** | $99/mo | 1 location, unlimited employees, payroll, advanced reports |
| **Multi-Site** | $199/mo | Up to 5 locations, all features |

Goal: 10 customers at $99/mo = $990 MRR. 50 = $4,950 MRR.

---

## Target ICP (Ideal Customer Profile)

**Who buys this:**
- Small retail shops with 1-3 locations
- 2-10 employees
- Currently using pen+paper, Excel, or an overpriced legacy POS
- Budget-conscious but needs real inventory + time clock + reports
- Nurseries, plant shops, boutiques, food trucks, pop-ups, barbershops

**Pain they feel:**
- Square/Clover cost too much ($60-$200/mo + hardware)
- QuickBooks is overkill and too complicated
- They lose inventory, miss payroll hours, can't see daily reports easily

**Differentiator**: Simple. Python-based. Affordable. Can run on any old laptop or tablet.

---

## Accounts You Need to Create

| Account | Why | Est. Cost | Action |
|---|---|---|---|
| **Stripe** | SaaS subscription billing | Free + 2.9% + $0.30/tx | stripe.com -> Create account |
| **Domain** | onyxpos.com or similar | ~$12/yr | Namecheap or Cloudflare |
| **DigitalOcean** (or Oracle) | Host the app | $0-6/mo | digitalocean.com |
| **GitHub** | Code repo + CI/CD | Free | github.com |
| **Postmark or Resend** | Transactional email (receipts, alerts) | Free tier | postmarkapp.com |
| **Notion or Google Workspace** | Docs, onboarding materials | Free | notion.so |
| **Calendly** | Book demos | Free tier | calendly.com |
| **Loom** | Record demo videos | Free tier | loom.com |

**NOT needed yet**: Apple Developer ($99/yr), Google Play ($25 one-time), Zendesk, Salesforce, etc.

---

## 30-Day Sprint Schedule

| Week | Focus | Deliverable |
|---|---|---|
| Week 1 | Code cleanup + config | Config-driven POS, no MGN hardcoding |
| Week 2 | Docker + hosting + domain | Live demo environment at onyxpos.com |
| Week 3 | Stripe billing + landing page | Customers can sign up and pay |
| Week 4 | Outreach + pilot program | 3 pilot customers onboarded |
| Week 5-6 | Iterate on feedback | v1.1 with top requested fixes |

---

## Risk Flags

- **Payments integration**: Cash-only MVP is fine for first pilots. Don't block launch on card hardware.
- **Support burden**: At $49-99/mo, you can't afford 2hr/day support per customer. Build good docs and onboarding first.
- **PCI compliance**: If you handle card data directly, you need PCI-DSS. Use Stripe to offload this entirely.
- **Tax compliance**: Different states have different sales tax rules. Start in CA only, use a simple config.
- **MGN data privacy**: Don't expose MGN's real sales/employee data in the demo environment.

---

## Alley Kings -- Status: DEFERRED

Alley Kings (ArenaAdvance) is a Unity mobile game. It requires:
- Full Unity visual asset pipeline (sprites, animations, art, sound)
- iOS: $99/yr Apple Developer account + App Store review (1-4 weeks)
- Android: $25 one-time Google Play + review process
- Game marketing is very different from B2B SaaS (discoverability is brutal)
- 6-12+ months to something submittable

**Do not start Alley Kings until Onyx POS has 10+ paying customers.**

---

*Generated by Claude Chief Operator | Hive Mind session b2c0bee0 | 2026-02-27*
