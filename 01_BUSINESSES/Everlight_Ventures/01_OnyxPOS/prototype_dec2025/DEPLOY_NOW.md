# 🚀 Deploy OnyxPOS Backend - Step by Step

## ✅ Pre-Deployment Checklist (COMPLETE)

All files are ready:
- ✅ Backend code complete
- ✅ Billing automation implemented  
- ✅ Access gating middleware active
- ✅ Email notifications ready
- ✅ Database migrations configured
- ✅ Railway deployment files created
- ✅ Testing scripts prepared

---

## 📋 What You'll Need

1. **GitHub Account** (free)
2. **Railway Account** (free tier available) - https://railway.app
3. **Stripe Test Keys** (from your Stripe Dashboard)

**Optional for now:**
- SendGrid API key (for emails - can add later)
- Custom domain (can use Railway's free domain)

---

## 🎯 Deployment Steps (30 minutes)

### Step 1: Push to GitHub (5 minutes)

```bash
cd "/home/mgn/Projects/Mountain Gardens Nursery POS"

# Initialize git if not already done
git init

# Add all files
git add backend/
git add onyxpos-mobile/
git add onyxpos-web/
git add *.md

# Commit
git commit -m "feat: Complete OnyxPOS implementation with billing automation"

# Add remote (create repo on GitHub first)
git remote add origin https://github.com/YOUR-USERNAME/onyxpos.git

# Push
git push -u origin main
```

---

### Step 2: Create Railway Project (5 minutes)

1. Go to https://railway.app
2. Click "Login" → Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your OnyxPOS repository
6. Railway will auto-detect the backend directory

---

### Step 3: Add PostgreSQL Database (2 minutes)

1. In Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"  
3. Railway automatically sets `DATABASE_URL` environment variable
4. Wait 30 seconds for provisioning

---

### Step 4: Configure Environment Variables (10 minutes)

Click on your backend service → "Variables" tab

**Required Variables:**

```bash
# Flask
FLASK_ENV=production
SECRET_KEY=Fp5mEDVt6JRYDCprKwsPj5BV2F68OZOU5X-rn7lBpOIuuYgZJe805rZZt50m5AjLiNFZJI2EnEAQut0KkUMyxg
JWT_SECRET_KEY=hLT5D82PY4nljO8cbd_JgxosSOy6asJ6MSeZgC3JzB8mq8Xwq_b95gYb_7u7MgkIxyaBC3Efzux2TG3MzwJpIw

# Stripe Test Keys (from Stripe Dashboard → Developers → API Keys)
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Stripe Webhook (add after Step 6)
STRIPE_WEBHOOK_SECRET=whsec_... 

# Stripe Price IDs (add later when you create metered prices)
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_ENTERPRISE=price_...
```

**Optional (can add later):**
```bash
SENDGRID_API_KEY=SG...
FROM_EMAIL=noreply@onyxpos.com
```

---

### Step 5: Deploy! (5 minutes)

Railway will automatically:
1. Install dependencies from `requirements.txt`
2. Run database migrations (`release: python database.py`)
3. Start gunicorn web server
4. Assign a public URL

**Watch the deployment:**
- Click on your service
- Go to "Deployments" tab
- Watch the build logs

**Look for:**
```
✅ Database initialized successfully!
✅ Gunicorn starting on port XXXX
```

---

### Step 6: Get Your API URL (1 minute)

1. Go to Settings → "Domains"
2. Railway provides: `https://onyxpos-production-XXXX.railway.app`
3. **Copy this URL** - you'll need it!

---

### Step 7: Configure Stripe Webhook (5 minutes)

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "+ Add endpoint"
3. **Endpoint URL**: `https://your-railway-url.railway.app/api/v1/billing/webhook`
4. **Select events to listen to**:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
5. Click "Add endpoint"
6. **Copy the Signing Secret** (starts with `whsec_`)
7. Add to Railway env vars as `STRIPE_WEBHOOK_SECRET`

---

### Step 8: Test Your API! (5 minutes)

Run the test script:

```bash
cd "/home/mgn/Projects/Mountain Gardens Nursery POS/backend"
./test_api.sh https://your-railway-url.railway.app
```

This will test:
- ✅ Health check
- ✅ Registration
- ✅ Login
- ✅ Protected endpoints
- ✅ Inventory creation
- ✅ Billing endpoints

**Expected output:**
```
=========================================
  Testing OnyxPOS API
=========================================

1️⃣  Testing Health Endpoint...
  ✅ Health check passed

2️⃣  Testing API Root...
  ✅ API root accessible

3️⃣  Testing Registration...
  ✅ Registration successful
  
... (more tests)

✅ API Testing Complete!
```

---

## 🎉 Success! What's Next?

Your backend is now live at: `https://your-railway-url.railway.app`

### Immediate Next Steps:

1. **Update Mobile App API URL**:
   ```javascript
   // onyxpos-mobile/src/config/constants.js
   export const API_URL = __DEV__
     ? 'http://localhost:5000/api/v1'
     : 'https://your-railway-url.railway.app/api/v1';
   ```

2. **Update Web Frontend API URL** (if using):
   ```javascript
   // onyxpos-web/.env
   VITE_API_URL=https://your-railway-url.railway.app/api/v1
   ```

3. **Test End-to-End Flow**:
   - Sign up via mobile app/web
   - Create inventory items
   - Make a test sale
   - Check dashboard analytics

---

## 📊 Monitoring Your Deployment

### View Logs:
Railway Dashboard → Your Service → "Logs" tab

### Check Database:
Railway Dashboard → PostgreSQL → "Data" tab

### Monitor Requests:
Railway Dashboard → Your Service → "Metrics" tab

---

## 🐛 Troubleshooting

### "502 Bad Gateway"
**Check:** App logs for Python errors
**Fix:** Verify all dependencies in requirements.txt

### "Database connection failed"
**Check:** DATABASE_URL is set correctly  
**Fix:** Should start with `postgresql://` not `postgres://`

### "Module not found"
**Check:** requirements.txt has the module
**Fix:** Redeploy (Railway → "Redeploy")

### Webhook not working
**Check:** Stripe Dashboard → Webhooks → Event log
**Fix:** Verify signing secret is correct in env vars

---

## 💰 Costs

**Railway Free Tier:**
- $5 credit per month
- Enough for development/testing
- Upgrade to $5/month for production

**Total to run OnyxPOS:**
- Railway: $5-20/month (based on usage)
- Stripe: Free (only pay on transactions)
- SendGrid: Free (up to 12k emails/month)

---

## 🔐 Security Checklist

Before going live with real customers:

- [ ] Change SECRET_KEY and JWT_SECRET_KEY to new random values
- [ ] Use Stripe live keys (not test keys)
- [ ] Set up custom domain with SSL
- [ ] Enable Stripe webhook signature verification
- [ ] Review CORS_ORIGINS (only allow your domains)
- [ ] Set up error monitoring (Sentry)
- [ ] Configure email properly (SendGrid)
- [ ] Set up database backups (Railway auto-backs up)

---

## 📞 Need Help?

1. Check Railway logs first
2. Check Stripe Dashboard → Events
3. Review DEPLOYMENT_GUIDE.md for detailed troubleshooting
4. Test with the provided test script

---

**Ready to deploy? Follow Step 1 above!** 🚀
