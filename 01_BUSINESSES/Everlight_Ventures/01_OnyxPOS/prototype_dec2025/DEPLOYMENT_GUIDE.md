# OnyxPOS Production Deployment Guide

Complete guide to deploying OnyxPOS to production on Railway (backend) and Vercel (frontend).

## Prerequisites

- ✅ GitHub account
- ✅ Railway account (https://railway.app)
- ✅ Vercel account (https://vercel.com)
- ✅ Stripe account (for payments)
- ✅ Resend account (for emails)
- ✅ Domain name (optional but recommended)

## Part 1: Database Setup (Railway PostgreSQL)

### 1. Create PostgreSQL Database

1. Go to [Railway](https://railway.app) and create a new project
2. Click **"+ New"** → **"Database"** → **"PostgreSQL"**
3. Wait for database to provision (~30 seconds)
4. Click on the PostgreSQL service
5. Go to **"Variables"** tab
6. Copy the `DATABASE_URL` value (starts with `postgresql://`)

**Save this URL - you'll need it for the backend!**

## Part 2: Backend Deployment (Railway)

### 1. Push Code to GitHub

```bash
cd backend
git init
git add .
git commit -m "Initial commit - OnyxPOS backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/onyxpos-backend.git
git push -u origin main
```

### 2. Deploy to Railway

1. Go to [Railway](https://railway.app/new)
2. Click **"Deploy from GitHub repo"**
3. Select your `onyxpos-backend` repository
4. Railway will auto-detect the Flask app

### 3. Configure Environment Variables

In Railway, go to **Variables** tab and add:

```bash
# Flask
SECRET_KEY=<generate-random-string-64-chars>
JWT_SECRET_KEY=<generate-random-string-64-chars>
FLASK_ENV=production

# Database (from Part 1)
DATABASE_URL=<your-railway-postgres-url>

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_ENTERPRISE=price_...

# Coinbase Commerce
COINBASE_COMMERCE_API_KEY=...
COINBASE_COMMERCE_WEBHOOK_SECRET=...

# Resend Email
RESEND_API_KEY=re_...
FROM_EMAIL="OnyxPOS <onboarding@onyxpos.com>"
REPLY_TO_EMAIL="support@onyxpos.com"

# CORS (add frontend URL later)
CORS_ORIGINS=https://onyxpos.vercel.app
```

**To generate secret keys:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Connect Database to Backend

1. In Railway, click the **"Connect"** button between PostgreSQL and your backend service
2. This automatically adds the DATABASE_URL variable
3. Backend will redeploy automatically

### 5. Run Database Migrations

Once deployed, open Railway **"Deployments"** → **"View Logs"** to ensure:
- ✅ Database tables created successfully
- ✅ No migration errors
- ✅ Server started on port

### 6. Get Your Backend URL

1. Go to **"Settings"** tab in Railway
2. Under **"Domains"**, click **"Generate Domain"**
3. Copy the URL (e.g., `https://onyxpos-backend.up.railway.app`)

**Save this URL - you'll need it for the frontend!**

## Part 3: Frontend Deployment (Vercel)

### 1. Update API Configuration

In `frontend/src/utils/api.js`, update:

```javascript
const API_BASE_URL = process.env.VITE_API_URL || 'https://your-backend.up.railway.app/api/v1';
```

### 2. Push Code to GitHub

```bash
cd frontend
git init
git add .
git commit -m "Initial commit - OnyxPOS frontend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/onyxpos-frontend.git
git push -u origin main
```

### 3. Deploy to Vercel

1. Go to [Vercel](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your `onyxpos-frontend` repository
4. Configure:
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 4. Set Environment Variables

In Vercel **"Settings"** → **"Environment Variables"**, add:

```
VITE_API_URL=https://your-backend.up.railway.app/api/v1
```

### 5. Deploy

1. Click **"Deploy"**
2. Wait for build to complete (~2 minutes)
3. Get your frontend URL (e.g., `https://onyxpos.vercel.app`)

### 6. Update CORS in Backend

Go back to Railway backend and update the `CORS_ORIGINS` variable:

```
CORS_ORIGINS=https://onyxpos.vercel.app,https://onyxpos.com
```

Backend will redeploy automatically.

## Part 4: Custom Domain Setup (Optional)

### Backend Domain (api.onyxpos.com)

**In Railway:**

1. Go to backend **"Settings"** → **"Domains"**
2. Click **"Add Domain"**
3. Enter: `api.onyxpos.com`
4. Add the CNAME record to your DNS:
   - **Type**: CNAME
   - **Name**: api
   - **Value**: <railway-provided-value>

**In Backend Variables:**

Update CORS to include new domain:

```
CORS_ORIGINS=https://app.onyxpos.com,https://onyxpos.com
```

### Frontend Domain (app.onyxpos.com)

**In Vercel:**

1. Go to **"Settings"** → **"Domains"**
2. Click **"Add"**
3. Enter: `app.onyxpos.com`
4. Add the DNS records shown (A record or CNAME)

**In Frontend Environment:**

Update API URL:

```
VITE_API_URL=https://api.onyxpos.com/api/v1
```

## Part 5: Third-Party Service Setup

### Stripe Setup

1. **Create Products & Prices:**
   - Go to Stripe Dashboard → Products
   - Create 3 products: Starter ($29), Professional ($79), Enterprise ($199)
   - Copy the price IDs and add to backend env vars

2. **Setup Webhooks:**
   - Go to Developers → Webhooks
   - Add endpoint: `https://api.onyxpos.com/api/v1/billing/webhook`
   - Select events:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Copy webhook secret to backend env

### Coinbase Commerce Setup

1. **Create Account:**
   - Go to https://commerce.coinbase.com
   - Create API key
   - Add to backend env vars

2. **Setup Webhook:**
   - Go to Settings → Webhooks
   - Add: `https://api.onyxpos.com/api/v1/crypto/webhook`
   - Copy shared secret to backend env

### Resend Email Setup

1. **Verify Domain:**
   - Go to Resend Dashboard → Domains
   - Add domain: `onyxpos.com`
   - Add DNS records (SPF, DKIM, DMARC)
   - Wait for verification

2. **Create API Key:**
   - Go to API Keys → Create
   - Copy key to backend env

## Part 6: Mobile App Deployment

### iOS App Store

1. Build with EAS:

```bash
cd mobile
npm install -g eas-cli
eas build --platform ios
```

2. Download IPA from EAS
3. Upload to App Store Connect
4. Submit for review

### Google Play Store

1. Build AAB:

```bash
eas build --platform android
```

2. Download AAB from EAS
3. Upload to Play Console
4. Submit for review

## Part 7: Monitoring & Maintenance

### Railway Monitoring

- **Logs**: Railway → Deployments → View Logs
- **Metrics**: CPU, Memory, Network usage
- **Alerts**: Set up email alerts for crashes

### Vercel Monitoring

- **Analytics**: Track page views, performance
- **Speed Insights**: Monitor Core Web Vitals
- **Error Tracking**: View runtime errors

### Database Backups

Railway PostgreSQL includes automatic backups:
- **Frequency**: Daily
- **Retention**: 7 days
- **Manual Backup**: Railway → PostgreSQL → Backups

### Uptime Monitoring

Use a service like:
- **Better Uptime** (free for 1 monitor)
- **UptimeRobot** (free for 50 monitors)
- **Pingdom**

Monitor:
- `https://api.onyxpos.com/health`
- `https://app.onyxpos.com`

## Part 8: Security Checklist

- ✅ HTTPS enabled (automatic on Railway & Vercel)
- ✅ Environment variables set (not hardcoded)
- ✅ CORS configured properly
- ✅ Database password is strong
- ✅ JWT secrets are random & long
- ✅ Stripe webhook signatures verified
- ✅ Rate limiting enabled (optional)
- ✅ SQL injection protection (using ORM)
- ✅ XSS protection headers set

## Part 9: Cost Estimation

### Railway (Backend + Database)

- **Starter Plan**: $5/month
  - 500 hours execution
  - $0.000463/GB-hour memory
  - $0.10/GB storage

**Estimated**: $10-20/month for 1-100 customers

### Vercel (Frontend)

- **Free Plan**: $0
  - 100 GB bandwidth
  - Unlimited deployments

**Estimated**: $0-20/month (free until you hit limits)

### Third-Party Services

- **Stripe**: 2.9% + $0.30 per transaction
- **Coinbase Commerce**: 1% per crypto transaction
- **Resend**: $20/month for 100K emails

**Total Monthly Cost**: ~$30-60 for initial launch

## Part 10: Launch Checklist

Before going live:

- ✅ Test registration flow
- ✅ Test login/logout
- ✅ Create test product
- ✅ Make test sale
- ✅ Test card payment (Stripe test mode)
- ✅ Test crypto payment (Coinbase test mode)
- ✅ Verify email delivery
- ✅ Test mobile app
- ✅ Check all analytics/charts
- ✅ Test subscription upgrade
- ✅ Test low stock alerts
- ✅ Review error logs
- ✅ Set up monitoring
- ✅ Create backup plan

## Troubleshooting

### Backend won't start

- Check Railway logs for errors
- Verify DATABASE_URL is correct
- Ensure all required env vars are set

### Frontend can't connect to backend

- Check CORS_ORIGINS includes frontend URL
- Verify VITE_API_URL is correct
- Check browser console for errors

### Database connection failed

- Ensure PostgreSQL service is running
- Check DATABASE_URL format
- Verify database exists

### Emails not sending

- Check RESEND_API_KEY is valid
- Verify domain is verified in Resend
- Check backend logs for email errors

## Support

- 📧 Email: support@onyxpos.com
- 📚 Docs: https://docs.onyxpos.com
- 💬 Discord: https://discord.gg/onyxpos

## Next Steps

After deployment:

1. **Test everything** in production
2. **Invite beta users** (10-20 businesses)
3. **Gather feedback** and fix issues
4. **Launch marketing campaign**
5. **Scale infrastructure** as needed

Good luck with your launch! 🚀
