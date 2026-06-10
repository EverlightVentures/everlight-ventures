# Railway Deployment - Quick Start

## Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub (recommended)
3. Verify email

## Step 2: Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub
4. Select your OnyxPOS repository
5. Railway will detect the Python app

## Step 3: Add PostgreSQL Database

1. In your Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway automatically sets `DATABASE_URL` environment variable
4. Wait for PostgreSQL to provision (~30 seconds)

## Step 4: Configure Environment Variables

Click on your service → "Variables" tab → Add these:

```bash
# Flask Environment
FLASK_ENV=production
SECRET_KEY=your-secret-key-here-64-chars-random
JWT_SECRET_KEY=your-jwt-secret-here-64-chars-random

# Stripe (get from Stripe Dashboard → Developers → API Keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (we'll add this after webhook setup)

# Stripe Price IDs (we'll add these later when we create metered prices)
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_ENTERPRISE=price_...

# Email (optional for now - can test without)
SENDGRID_API_KEY=SG...
FROM_EMAIL=noreply@onyxpos.com

# CORS
CORS_ORIGINS=http://localhost:5173,https://your-frontend.vercel.app

# App URLs (Railway will provide the domain)
APP_URL=https://your-app.railway.app
FRONTEND_URL=http://localhost:5173
```

**To generate secure secrets:**
```bash
# In terminal
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Step 5: Deploy

1. Railway will automatically deploy when you push to main branch
2. OR click "Deploy" button in Railway dashboard
3. Wait for build (~2-5 minutes)
4. Check logs for errors

## Step 6: Run Database Migrations

Once deployed, go to your service → "Deployments" → Click latest deployment → "View Logs"

Then add this to your `Procfile`:

```
release: python database.py
web: gunicorn --bind 0.0.0.0:$PORT app:app --workers 2 --threads 4 --timeout 60
```

Railway will run the `release` command before starting the web server.

## Step 7: Get Your API URL

1. In Railway project → Settings → "Domains"
2. Railway generates: `https://your-app-production-XXXX.railway.app`
3. Copy this URL - you'll use it for Stripe webhooks and mobile app

## Step 8: Test Health Endpoint

```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00",
  "version": "1.0.0"
}
```

## Step 9: Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. Endpoint URL: `https://your-app.railway.app/api/v1/billing/webhook`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the "Signing secret" (starts with `whsec_`)
6. Add to Railway env vars as `STRIPE_WEBHOOK_SECRET`

## Step 10: Test Registration

```bash
curl -X POST https://your-app.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Test Store",
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

Should return access token and user data.

## Troubleshooting

### "Database connection failed"
- Check that PostgreSQL is running
- Verify DATABASE_URL is set correctly
- Look for `postgres://` (should be `postgresql://` for SQLAlchemy 2.0)

### "Module not found"
- Check requirements.txt has all dependencies
- Railway might be caching old build - try "Redeploy"

### "502 Bad Gateway"
- Check app logs for Python errors
- Verify Procfile has correct gunicorn command
- Check PORT is being used correctly

### Webhook errors
- Test webhook with Stripe CLI first
- Verify signature secret is correct
- Check logs for webhook handler errors

## Next Steps

1. Update mobile app API URL to use Railway URL
2. Configure Stripe metered prices
3. Test end-to-end billing flow
4. Set up cron jobs for monthly billing

---

**Your backend is now deployed! 🚀**
