# OnyxPOS Implementation Audit & Checklist

## Executive Summary

**Status**: 85% Complete - Core functionality ready, needs automation layer + marketing

**What We Have**:
- ✅ Multi-tenant architecture with tenant isolation
- ✅ Stripe Billing integration (subscriptions + webhooks)
- ✅ GMV tracking and calculation
- ✅ Capped pricing model ($39/$89/$299 with variable fee caps)
- ✅ Full POS functionality (inventory, sales, analytics)
- ✅ Self-diagnosing support system with error codes
- ✅ Mobile app (React Native/Expo) - UI complete
- ✅ Web frontend with pricing calculator
- ✅ Role-based access control

**What's Missing**:
- ⚠️ Monthly GMV billing automation (cron job)
- ⚠️ Access gating middleware (suspend if past_due)
- ⚠️ Dunning logic (retry payment, grace period)
- ⚠️ Stripe metered billing for GMV fees
- ⚠️ Email notifications (payment failed, trial ending, etc.)
- ⚠️ Audit logs for billing events
- ⚠️ Nursery & Smoke Shop specific landing pages
- ⚠️ In-app onboarding flow

---

## 1. Multi-Tenant Architecture ✅

### Status: COMPLETE

**Database Models** (`backend/models.py`):
- ✅ Tenant model with subscription tracking
- ✅ User model with roles (owner, manager, cashier, laborer)
- ✅ Tenant isolation on all queries
- ✅ GMV fields: `gmv_current_month`, `gmv_last_month`, `usage_fee_current_month`
- ✅ Subscription fields: `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`
- ✅ Trial tracking: `trial_ends_at`, `trial_days_remaining`

**Subscription Statuses**:
- ✅ `trial` - 14-day free trial
- ✅ `active` - Paid and current
- ✅ `past_due` - Payment failed
- ✅ `suspended` - Access revoked
- ✅ `canceled` - Subscription ended

**Files**:
- `backend/models.py` (lines 24-198)
- `backend/database.py`

---

## 2. Stripe Billing Integration ⚠️ MOSTLY COMPLETE

### Status: 75% - Missing Metered Billing

**What Works**:
- ✅ Stripe Checkout for subscriptions
- ✅ Customer Portal for self-service
- ✅ Webhook handlers for:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

**What's Missing**:
- ❌ Metered billing setup for GMV fees
- ❌ Usage record submission to Stripe
- ❌ Idempotency keys for usage events

**Files**:
- `backend/api/stripe_billing.py` (complete for subscriptions)
- `backend/api/billing_gmv.py` (calculation only, not Stripe integration)

**Fix Required**:
1. Create Stripe metered price for each tier
2. Add `/billing/record-usage` endpoint
3. Update monthly billing job to submit usage to Stripe

---

## 3. Pricing Model ✅ COMPLETE

### Status: COMPLETE - Matches Spec

**Tiers** (defined in `models.py` lines 124-164):

**Tier 1 - Starter**:
- Monthly: $39
- GMV Fee: 0.15%
- Variable Cap: $149
- Max Total: $188/mo

**Tier 2 - Growth**:
- Monthly: $89
- GMV Fee: 0.10%
- Variable Cap: $199
- Max Total: $288/mo

**Tier 3 - Scale**:
- Monthly: $299
- GMV Fee: 0%
- Variable Cap: $0
- Max Total: $299/mo (flat)

**Methods**:
- ✅ `get_monthly_subscription_fee()`
- ✅ `get_platform_fee_percent()`
- ✅ `get_variable_fee_cap()`
- ✅ `calculate_usage_fee(gmv)` - applies cap
- ✅ `get_total_monthly_cost()`
- ✅ `get_breakeven_gmv(compare_tier)` - shows when to upgrade

---

## 4. Monthly GMV Billing ❌ MISSING

### Status: NOT IMPLEMENTED

**Required**:
1. **Cron Job** - Run at end of month (1st at 00:00 UTC)
2. **Logic**:
   - Query all active tenants
   - Calculate GMV usage fee for month
   - Submit usage record to Stripe (if metered)
   - Roll GMV counters (`gmv_current_month` → `gmv_last_month`)
   - Reset `gmv_current_month = 0`
   - Update `last_gmv_reset = now()`
3. **Idempotency** - Track processed months to avoid double-billing

**Files Needed**:
- `backend/jobs/monthly_billing.py` (NEW)
- `backend/cron_scheduler.py` (NEW)
- OR Railway cron configuration

**Priority**: HIGH - Critical for revenue

---

## 5. Dunning & Access Gating ❌ MISSING

### Status: NOT IMPLEMENTED

**Dunning Rules** (Standard SaaS):
- Day 1: Payment fails → status = `past_due`
- Day 1-7: Retry payment automatically (Stripe Smart Retries)
- Day 7: Send "Past Due" email
- Day 10: Grace period ends → status = `suspended`, access gated
- Day 30: Auto-cancel → status = `canceled`

**Access Gating Middleware**:
```python
@app.before_request
def check_subscription_status():
    if g.tenant_id:
        tenant = g.db.query(Tenant).filter_by(id=g.tenant_id).first()
        if tenant.subscription_status in ['suspended', 'canceled']:
            if request.path not in ['/billing', '/settings']:
                return jsonify({'error': 'Subscription suspended'}), 402
```

**Files Needed**:
- `backend/middleware/subscription_guard.py` (NEW)
- Update `app.py` to register middleware
- `backend/jobs/dunning_check.py` (NEW) - Daily job to enforce grace periods

**Priority**: HIGH - Critical for cash flow

---

## 6. Email Notifications ❌ MISSING

### Status: NOT IMPLEMENTED

**Required Emails**:
1. **Trial Expiring** - 3 days before trial ends
2. **Payment Failed** - Immediately when invoice fails
3. **Past Due Warning** - Day 7 of past_due
4. **Account Suspended** - When access revoked
5. **Payment Succeeded** - Confirmation + receipt
6. **Welcome Email** - On signup
7. **Abandoned Trial** - Day 5 if no first sale

**Service**: Use SendGrid or AWS SES

**Files Needed**:
- `backend/services/email.py` (NEW)
- `backend/templates/emails/*.html` (NEW)

**Priority**: MEDIUM - Can launch without, but reduces churn

---

## 7. Audit Logs ❌ MISSING

### Status: PARTIAL - Have diagnostics events, not billing audit

**Needed**:
- Table: `billing_audit_log`
- Fields: `tenant_id`, `event_type`, `amount`, `stripe_event_id`, `metadata`, `created_at`
- Events to log:
  - Subscription created/updated/canceled
  - Payment succeeded/failed
  - GMV usage recorded
  - Account suspended/reactivated
  - Plan changed

**Files Needed**:
- Add `BillingAuditLog` model to `models.py`
- Update webhook handlers to log events

**Priority**: MEDIUM - Important for debugging billing issues

---

## 8. Diagnostics & Support ✅ COMPLETE

### Status: COMPLETE

**What We Have**:
- ✅ Structured error codes (E001-E045)
- ✅ Error documentation with fixes
- ✅ `/diagnostics/health` - System health check
- ✅ `/diagnostics/recent-events` - Event log
- ✅ `/diagnostics/generate-report` - One-click report
- ✅ `/diagnostics/suggested-fixes` - AI-ready error resolution

**Files**:
- `backend/api/diagnostics.py` (lines 1-700+)

**AI Support Integration**:
- Ready for AI assistant to consume error codes
- Structured format for automated resolution
- Escalation path defined

---

## 9. Mobile App ✅ UI COMPLETE

### Status: 95% - Needs backend deployment + testing

**Screens Built**:
- ✅ Login
- ✅ Register
- ✅ Dashboard (stats + quick actions)
- ✅ Sales Terminal (POS interface)
- ✅ Inventory Management
- ✅ Sales/Reports
- ✅ Settings

**Navigation**:
- ✅ React Navigation setup
- ✅ Auth flow (token-based)
- ✅ Stack navigator

**API Integration**:
- ✅ Axios client configured
- ✅ AsyncStorage for tokens
- ✅ All API methods: auth, inventory, sales, analytics, billing

**Files**:
- `onyxpos-mobile/src/screens/*.js` (7 screens)
- `onyxpos-mobile/src/services/api.js`
- `onyxpos-mobile/App.js`

**Next Steps**:
1. Test with backend running
2. Build APK (Android)
3. Build IPA (iOS)
4. Submit to stores

---

## 10. Web Frontend ✅ COMPLETE

### Status: COMPLETE

**Landing Page**:
- ✅ Hero section with capped pricing messaging
- ✅ Features grid (9 features)
- ✅ **Interactive pricing calculator** - Live GMV slider
- ✅ Comparison table (OnyxPOS vs Traditional)
- ✅ CTA section
- ✅ Footer

**Pricing Calculator Features**:
- ✅ GMV slider ($0-$500k)
- ✅ Real-time cost calculation for all 3 tiers
- ✅ Cap indicator + savings display
- ✅ Break-even math visible
- ✅ Mobile responsive

**Tech Stack**:
- ✅ Vite + React
- ✅ Tailwind CSS
- ✅ Dark theme

**Files**:
- `onyxpos-web/src/components/*.jsx` (5 components)
- `onyxpos-web/src/App.jsx`

**Missing**:
- ❌ Nursery-specific landing page
- ❌ Smoke shop ("Specialty Retail") landing page
- ❌ SEO optimization
- ❌ Google Analytics

---

## 11. Marketing ❌ NOT IMPLEMENTED

### Status: 0% - Generic landing page only

**Required for Launch**:

**A. Nursery Landing Page**:
- Headline: "POS Built for Nurseries & Garden Centers"
- Features: Plant inventory tracking, seasonal pricing, weather-resistant hardware
- Case study: "How [Nursery] saved $X on POS fees"
- Images: Plants, greenhouses, outdoor POS

**B. Specialty Retail Landing Page** (Smoke Shop Safe):
- Headline: "Compliance-Ready POS for Specialty Retail"
- Features: Age verification, compliance reporting, inventory controls
- NO vape/tobacco imagery
- Use "Specialty Retail POS" terminology
- Images: Generic retail, clean store interior

**C. Ad Angles** (5 each):

**Nurseries**:
1. "Stop overpaying for POS fees that grow with your sales"
2. "Track 10,000+ plants with $39/mo (capped at $188)"
3. "Weatherproof POS for outdoor garden centers"
4. "Seasonal pricing automation for nurseries"
5. "Free 14-day trial - First sale in 15 minutes"

**Specialty Retail**:
1. "Compliance-ready POS without enterprise pricing"
2. "Know your max POS cost before you commit"
3. "Inventory tracking built for specialty retail"
4. "From $39/mo - No per-transaction fees"
5. "14-day free trial - Setup in minutes"

**D. Email Sequences**:
- ❌ 5-email abandoned trial sequence
- ❌ 7-email onboarding sequence
- ❌ Re-engagement campaign

**Priority**: HIGH - Needed before paid ads

---

## 12. In-App Onboarding ❌ MISSING

### Status: NOT IMPLEMENTED

**Goal**: First sale in 15 minutes

**Onboarding Steps** (Modal overlay):
1. "Add your first product" → Link to Inventory
2. "Make a test sale" → Link to Sales Terminal
3. "Connect payment method" → Link to Settings
4. "Invite team members" → Link to Users
5. "Set up tax rate" → Link to Settings

**Progress Indicator**:
- Show 0/5, 1/5, etc.
- Celebrate when complete

**Files Needed**:
- `onyxpos-mobile/src/components/OnboardingModal.jsx` (NEW)
- `onyxpos-mobile/src/hooks/useOnboarding.js` (NEW)

**Priority**: MEDIUM - Reduces churn significantly

---

## Missing Components Summary

### CRITICAL (Must-Have for Launch):
1. ✅ **Monthly GMV Billing Job** - Without this, no revenue from GMV fees
2. ✅ **Access Gating Middleware** - Without this, suspended tenants keep using
3. ✅ **Stripe Metered Billing** - To actually charge GMV fees
4. ✅ **Marketing Landing Pages** - To run paid ads
5. ✅ **Payment Failed Email** - To reduce involuntary churn

### HIGH Priority (Launch Week 1):
6. ✅ **Dunning Jobs** - Automate suspension/cancellation
7. ✅ **Trial Expiring Email** - Convert trials to paid
8. ✅ **Billing Audit Log** - Debug billing issues

### MEDIUM Priority (Month 1):
9. In-App Onboarding - Improve activation
10. Email Sequences - Reduce churn
11. SEO Optimization - Organic traffic

---

## Recommended Implementation Order

**Week 1 - Critical Path**:
1. Implement access gating middleware (2 hours)
2. Create monthly GMV billing job (4 hours)
3. Set up Stripe metered billing (3 hours)
4. Implement dunning logic (3 hours)
5. Add payment failed email (2 hours)

**Week 2 - Marketing Prep**:
6. Create nursery landing page (4 hours)
7. Create specialty retail landing page (4 hours)
8. Write ad copy + angles (3 hours)
9. Set up Google Analytics (1 hour)
10. SEO optimization (3 hours)

**Week 3 - Mobile Launch**:
11. Test mobile app with backend (4 hours)
12. Fix bugs (8 hours)
13. Build APK/IPA (2 hours)
14. Submit to app stores (2 hours)

**Week 4 - Polish**:
15. In-app onboarding (6 hours)
16. Email sequences (4 hours)
17. Billing audit log (3 hours)
18. Load testing (3 hours)

---

## Solo Founder Risk Checklist

**Top 10 Failure Points + Mitigations**:

1. **⚠️ GMV Billing Fails Silently**
   - Risk: Lose revenue, never notice
   - Fix: Add monitoring alert if job doesn't run
   - Fix: Daily reconciliation report

2. **⚠️ Stripe Webhook Fails**
   - Risk: Subscription status out of sync
   - Fix: Idempotency keys on all webhook handlers
   - Fix: Daily sync job to reconcile Stripe vs DB

3. **⚠️ Suspended Tenant Still Has Access**
   - Risk: Free riders, lost revenue
   - Fix: Implement access gating middleware ASAP
   - Fix: Test with suspended tenant before launch

4. **⚠️ Double Billing**
   - Risk: Charge customer twice, refund hassle
   - Fix: Idempotency on usage record submission
   - Fix: Track billing_month in tenant record

5. **⚠️ Trial Abuse**
   - Risk: Users keep signing up for trials
   - Fix: Email verification required
   - Fix: Block disposable email domains
   - Fix: Require credit card for trial (optional)

6. **⚠️ Payment Method Expires**
   - Risk: Involuntary churn
   - Fix: Email 7 days before card expires
   - Fix: Link to update billing in Stripe Portal

7. **⚠️ No Email Deliverability**
   - Risk: Critical emails never arrive
   - Fix: Set up SPF/DKIM/DMARC records
   - Fix: Warm up SendGrid sender reputation
   - Fix: Monitor bounce rate

8. **⚠️ Database Outage During Billing**
   - Risk: Miss billing run, lose revenue
   - Fix: Idempotent billing job that can re-run
   - Fix: Keep billing_processed_months log

9. **⚠️ Surge Pricing (Stripe Rate Limits)**
   - Risk: 1000+ tenants bill at once, hit API limits
   - Fix: Stagger billing over 24 hours (random offset)
   - Fix: Exponential backoff on Stripe API calls

10. **⚠️ Support Overwhelm**
   - Risk: 1-person can't handle 100+ support tickets
   - Fix: AI-first support with diagnostics
   - Fix: In-app knowledge base
   - Fix: Community forum (users help users)

---

## Files Audit

### Existing Files (Backend):
```
backend/
├── app.py ✅
├── models.py ✅
├── database.py ✅
├── config.py ✅
├── api/
│   ├── auth.py ✅
│   ├── inventory.py ✅
│   ├── sales.py ✅
│   ├── analytics.py ✅
│   ├── stripe_billing.py ✅
│   ├── billing_gmv.py ✅
│   ├── diagnostics.py ✅
│   └── (others) ✅
```

### Missing Files (Backend):
```
backend/
├── jobs/ ❌
│   ├── __init__.py
│   ├── monthly_billing.py (CRITICAL)
│   ├── dunning_check.py (CRITICAL)
│   └── trial_reminders.py
├── middleware/ ❌
│   ├── __init__.py
│   └── subscription_guard.py (CRITICAL)
├── services/ ❌
│   ├── __init__.py
│   ├── email.py
│   └── stripe_metered.py (CRITICAL)
├── templates/ ❌
│   └── emails/
│       ├── payment_failed.html
│       ├── trial_expiring.html
│       └── welcome.html
└── cron_scheduler.py ❌ (or Railway cron.yaml)
```

### Existing Files (Mobile):
```
onyxpos-mobile/
├── App.js ✅
├── src/
│   ├── screens/ ✅ (7 screens)
│   ├── services/api.js ✅
│   ├── config/constants.js ✅
│   └── components/ (empty)
```

### Missing Files (Mobile):
```
onyxpos-mobile/
└── src/
    └── components/
        ├── OnboardingModal.jsx ❌
        └── SubscriptionBanner.jsx ❌
```

### Existing Files (Web):
```
onyxpos-web/
├── src/
│   ├── App.jsx ✅
│   ├── components/
│   │   ├── Hero.jsx ✅
│   │   ├── Features.jsx ✅
│   │   ├── PricingCalculator.jsx ✅
│   │   ├── CTA.jsx ✅
│   │   └── Footer.jsx ✅
```

### Missing Files (Web):
```
onyxpos-web/
└── src/
    └── pages/ ❌
        ├── NurseryLanding.jsx
        ├── SpecialtyRetailLanding.jsx
        └── ThankYou.jsx
```

---

## Deployment Checklist

### Environment Variables Needed:
```bash
# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_... (metered)
STRIPE_PRICE_GROWTH=price_... (metered)
STRIPE_PRICE_SCALE=price_... (metered)

# Database
DATABASE_URL=postgresql://...

# Email
SENDGRID_API_KEY=SG...
FROM_EMAIL=noreply@onyxpos.com

# App
JWT_SECRET_KEY=...
FLASK_ENV=production
CORS_ORIGINS=https://app.onyxpos.com,https://onyxpos.com
```

### Railway Deploy:
1. Create PostgreSQL database
2. Set environment variables
3. Deploy backend
4. Run migrations: `flask db upgrade`
5. Set up cron jobs in Railway
6. Configure domain + SSL

### Vercel Deploy (Web):
1. Connect GitHub repo
2. Build command: `npm run build`
3. Output directory: `dist`
4. Environment variables: (none needed)
5. Configure domain

---

## Next Immediate Actions

**To make fully functional before mobile app build:**

1. **Implement Access Gating** (30 min)
2. **Create Monthly Billing Job** (2 hours)
3. **Add Stripe Metered Usage** (2 hours)
4. **Implement Dunning Logic** (2 hours)
5. **Test End-to-End Billing Flow** (1 hour)

Total: ~7 hours to production-ready backend

**Then**:
6. Build mobile app
7. Create marketing landing pages
8. Deploy to Railway
9. Submit apps
10. Launch! 🚀

---

**Status**: Ready to implement missing pieces. All architectural decisions made, pricing finalized, UI complete.
