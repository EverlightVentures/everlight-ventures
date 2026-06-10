# How You Get Paid - OnyxPOS Revenue Flow

## 💰 The Simple Answer

When a customer subscribes to OnyxPOS for $249/mo (or $149 or $400):
1. **Stripe charges their credit card automatically every month**
2. **Money goes directly to YOUR Stripe account**
3. **Stripe pays you out to your bank account** (daily or weekly)
4. **You keep the money** (minus Stripe's 2.9% + 30¢ fee)

That's it. You get paid automatically. No invoicing, no chasing payments.

---

## 🔄 Two Different Stripe Accounts (Don't Get Confused!)

### Your Stripe Account (Collecting Subscription Fees)
- **Purpose:** Customers pay YOU for using OnyxPOS software
- **What it charges:** $249/mo, $149/mo, or $400/mo subscriptions
- **Who sets it up:** YOU (one time, before launch)
- **Revenue:** All subscription revenue from all customers
- **Stripe fee:** 2.9% + $0.30 per transaction (standard Stripe fee)

**Example:** Customer pays $249/mo → Stripe takes $7.52 → You get $241.48

### Customer's Stripe Account (Processing Their Sales)
- **Purpose:** Customer's retail customers pay THEM for products
- **What it charges:** Whatever the customer is selling (coffee, clothes, etc.)
- **Who sets it up:** THE CUSTOMER (in their own POS settings)
- **Revenue:** Customer keeps 100% of their sales
- **Stripe fee:** Customer pays their own Stripe fees (2.9% + $0.30)

**Example:** Customer sells a $50 shirt → Their Stripe takes $1.75 → Customer gets $48.25

**YOU NEVER TOUCH CUSTOMER SALES MONEY.** They use their own Stripe account for sales.

---

## 📊 Step-by-Step: How Money Flows

### When a Customer Signs Up

**Day 1 - Customer Registers:**
```
Customer → OnyxPOS → Clicks "Start 14-Day Trial"
```
- No payment required yet
- They get full access to try everything

**Day 14 - Trial Ends:**
```
OnyxPOS → Stripe Checkout → Customer Enters Card
```
- Customer sees Stripe checkout page
- Enters credit card (Visa, Mastercard, Amex, etc.)
- Agrees to $249/mo subscription

**Day 14 - First Charge:**
```
Stripe → Charges Customer's Card → $249.00
Stripe → Takes Fee → $7.52 (2.9% + $0.30)
Stripe → Deposits to Your Bank → $241.48
```

**Every Month After:**
```
1st of Month → Stripe Auto-Charges → $249.00
Stripe → Deposits to Your Bank → $241.48 (after fees)
```

### Automatic, Recurring Revenue

- Stripe handles **everything automatically**
- You don't send invoices
- You don't chase payments
- Customers can't "forget" to pay
- If their card fails, Stripe retries automatically
- You get email notifications for all payments

---

## 💳 Setting Up YOUR Stripe Account (One-Time Setup)

### Step 1: Create Stripe Account
```
1. Go to https://stripe.com
2. Click "Start now" (free)
3. Enter your business info:
   - Business name (e.g., "OnyxOS LLC" or your name)
   - Email
   - Country (USA)
   - Business type (Individual or LLC)
4. Verify your identity (government ID)
5. Add your bank account for payouts
```

### Step 2: Get Your API Keys
```
1. Log into Stripe Dashboard
2. Go to Developers > API keys
3. Copy two keys:
   - Publishable key: pk_live_...
   - Secret key: sk_live_...
```

### Step 3: Add Keys to OnyxPOS Backend
```
Edit backend/.env:

STRIPE_SECRET_KEY=sk_live_YOUR_SECRET_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_PUBLISHABLE_KEY_HERE
```

### Step 4: Create Subscription Products in Stripe
```
1. Stripe Dashboard > Products > Create Product
2. Create three products:

Product 1:
  Name: OnyxPOS Core
  Price: $249/month
  Billing: Recurring monthly
  → Copy Price ID: price_1ABC...

Product 2:
  Name: OnyxPayroll
  Price: $149/month
  Billing: Recurring monthly
  → Copy Price ID: price_2DEF...

Product 3:
  Name: OnyxOS Bundle
  Price: $400/month
  Billing: Recurring monthly
  → Copy Price ID: price_3GHI...
```

### Step 5: Add Price IDs to Backend
```
Edit backend/.env:

STRIPE_PRICE_ONYXPOS_CORE=price_1ABC...
STRIPE_PRICE_ONYXPAYROLL=price_2DEF...
STRIPE_PRICE_ONYXOS_BUNDLE=price_3GHI...
```

### Step 6: Set Up Webhooks (So You Know When Payments Happen)
```
1. Stripe Dashboard > Developers > Webhooks
2. Click "Add endpoint"
3. URL: https://api.onyxpos.com/api/v1/billing/webhook
4. Select events:
   - checkout.session.completed
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_succeeded
   - invoice.payment_failed
5. Copy webhook signing secret: whsec_...
```

### Step 7: Add Webhook Secret to Backend
```
Edit backend/.env:

STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
```

**Done!** You're ready to accept payments.

---

## 📈 Revenue Calculations

### Per Customer Revenue (Monthly)

| Plan | Customer Pays | Stripe Fee | You Get |
|------|---------------|------------|---------|
| OnyxPOS Core | $249.00 | $7.52 | $241.48 |
| OnyxPayroll | $149.00 | $4.62 | $144.38 |
| OnyxOS Bundle | $400.00 | $11.90 | $388.10 |

### Annual Revenue Projections

**10 Customers at $400/mo:**
- Monthly: $4,000 - $119 (Stripe) = **$3,881/mo**
- Annual: **$46,572/year**

**50 Customers at $400/mo:**
- Monthly: $20,000 - $595 (Stripe) = **$19,405/mo**
- Annual: **$232,860/year**

**100 Customers at $400/mo:**
- Monthly: $40,000 - $1,190 (Stripe) = **$38,810/mo**
- Annual: **$465,720/year**

### Annual Prepay Discount (10% Off)

If customers prepay annually, they save 10%:
- OnyxOS Bundle: $400 x 12 = $4,800
- With 10% discount: $4,320/year
- You charge: $4,320 upfront
- Stripe fee (one charge): $125.58 + $0.30 = $125.88
- You get: **$4,194.12 upfront**

Better cash flow for you!

---

## 🔔 How You'll Know When You Get Paid

### Stripe Email Notifications
You'll get emails for:
- ✅ New customer signed up
- ✅ Payment succeeded ($249 from John's Coffee Shop)
- ✅ Payment failed (card declined - Stripe auto-retries)
- ✅ Customer canceled subscription
- ✅ Payout sent to your bank ($3,881.00)

### Stripe Dashboard
Check anytime:
- Total revenue this month
- Active subscribers count
- Failed payments
- Upcoming charges
- Payout schedule

### Your Bank Account
- Money shows up automatically
- Default: Weekly payouts (every Friday)
- Or: Daily payouts (if you enable it)

---

## 🛡️ What If Customer Doesn't Pay?

Stripe handles this automatically:

**Scenario 1: Card Declined**
```
Day 1: Stripe tries to charge
Day 1: Card declined (insufficient funds)
Day 3: Stripe retries automatically
Day 5: Stripe retries again
Day 7: Stripe sends "payment failed" email to customer
```

**Your backend automatically:**
- Sets `subscription_status = "past_due"`
- Blocks their access to OnyxPOS
- Sends email: "Payment failed - update card"

**Scenario 2: Customer Updates Card**
```
Customer → Stripe Portal → Updates Card
Stripe → Charges Successfully
Backend → Sets subscription_status = "active"
Customer → Regains Access
```

**Scenario 3: Customer Never Pays**
```
Day 14: Final retry fails
Stripe → Cancels Subscription
Backend → Deletes their data (or archives it)
```

**You never have to chase payments.** Stripe handles everything.

---

## 📊 Tracking Your Revenue

### Option 1: Stripe Dashboard
- Go to https://dashboard.stripe.com
- See real-time revenue, customers, charts

### Option 2: Build OnyxPOS Owner Dashboard (For You)
Create yourself a "God Mode" dashboard in OnyxPOS:
- Total MRR (Monthly Recurring Revenue)
- Customer count
- Churn rate
- Lifetime value

### Option 3: Connect to QuickBooks/Xero
- Stripe integrates with accounting software
- Automatic revenue tracking
- Tax reporting

---

## 🚨 Common Questions

### Q: Do I need a business entity (LLC)?
**A:** Not required to start. You can use Stripe as an individual. But get an LLC later for liability protection.

### Q: Do I pay taxes on this revenue?
**A:** Yes. Stripe sends you a 1099-K at year-end if you make $600+. Report it as business income.

### Q: Can customers use PayPal instead of credit card?
**A:** Not by default. But you can enable it in Stripe settings.

### Q: What if I want to refund a customer?
**A:** Stripe Dashboard > Payments > Find payment > Refund. Takes 5-10 days.

### Q: Do I need merchant services?
**A:** No. Stripe IS the merchant services. That's what the 2.9% + 30¢ covers.

### Q: What if customer disputes a charge?
**A:** Stripe handles disputes. They email you. You respond with proof of service (screenshots of customer using OnyxPOS). Stripe decides.

### Q: Can I change prices later?
**A:** Yes. Create new price in Stripe. Grandfather existing customers or migrate them.

---

## ✅ Pre-Launch Checklist

Before you can accept payments:
- [ ] Create Stripe account
- [ ] Verify identity (government ID)
- [ ] Add bank account for payouts
- [ ] Get API keys (pk_live_... and sk_live_...)
- [ ] Create 3 products in Stripe ($249, $149, $400)
- [ ] Get price IDs (price_...)
- [ ] Add all keys to backend/.env
- [ ] Set up webhook endpoint
- [ ] Test with Stripe test mode first (pk_test_... and sk_test_...)
- [ ] Use test card: 4242 4242 4242 4242
- [ ] Switch to live mode when ready

---

## 🎯 Bottom Line

**You get paid automatically every month via Stripe.**

- Customer signs up → Stripe charges them → Money goes to your bank
- No invoicing
- No payment chasing
- No complicated billing
- Just pure SaaS revenue

**Your only job:** Build great software. Stripe handles the money.

---

## Support

**Stripe Support:** https://support.stripe.com (24/7 live chat)
**Stripe Docs:** https://stripe.com/docs
**Test Your Setup:** https://stripe.com/docs/testing

You're selling software. Stripe collects the money. Simple as that. 💰
