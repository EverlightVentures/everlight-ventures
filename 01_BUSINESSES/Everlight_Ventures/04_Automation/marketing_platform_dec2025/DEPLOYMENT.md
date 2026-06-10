# Deployment Guide

This guide covers deploying Everlight Ventures to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Deploy to Vercel](#deploy-to-vercel)
- [Deploy to Railway](#deploy-to-railway)
- [Deploy to AWS](#deploy-to-aws)
- [Database Setup](#database-setup)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)

## Prerequisites

- Production database (PostgreSQL)
- Email service account (for magic links)
- Domain name (optional)
- Git repository

## Environment Variables

Required environment variables for production:

```bash
# Database
DATABASE_URL="postgresql://user:password@host:5432/database?sslmode=require"

# NextAuth
NEXTAUTH_URL="https://yourdomain.com"
NEXTAUTH_SECRET="<generate-with-openssl-rand-base64-32>"

# Email (for magic links)
EMAIL_SERVER_HOST="smtp.sendgrid.net"
EMAIL_SERVER_PORT="587"
EMAIL_SERVER_USER="apikey"
EMAIL_SERVER_PASSWORD="<your-sendgrid-api-key>"
EMAIL_FROM="noreply@yourdomain.com"

# Node
NODE_ENV="production"
```

### Generate Secrets

```bash
# Generate NEXTAUTH_SECRET
openssl rand -base64 32
```

## Deploy to Vercel

### Step 1: Connect Repository

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your Git repository
4. Select "everlight-ventures" repository

### Step 2: Configure Project

```
Framework Preset: Next.js
Root Directory: apps/web
Build Command: cd ../.. && npm run build
Install Command: cd ../.. && npm install
Output Directory: .next
```

### Step 3: Environment Variables

Add all environment variables from above in Vercel dashboard:
- Settings → Environment Variables
- Add each variable
- Make sure to select all environments (Production, Preview, Development)

### Step 4: Deploy

1. Click "Deploy"
2. Wait for build to complete
3. Visit your deployment URL

### Step 5: Run Migrations

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Run migrations
vercel env pull .env.production
DATABASE_URL=<your-production-db-url> npm run db:migrate:deploy
```

### Custom Domain

1. Go to Settings → Domains
2. Add your domain
3. Configure DNS records as instructed
4. Update NEXTAUTH_URL environment variable

## Deploy to Railway

### Step 1: Create Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository

### Step 2: Add PostgreSQL

1. Click "New Service"
2. Select "Database" → "PostgreSQL"
3. Wait for provisioning
4. Copy DATABASE_URL from environment variables

### Step 3: Configure Application

1. Click on your application service
2. Go to Settings → Environment
3. Add all environment variables
4. Use Railway's PostgreSQL DATABASE_URL

### Step 4: Configure Build

Add to railway.toml:

```toml
[build]
builder = "nixpacks"
buildCommand = "npm install && npm run db:generate && npm run build"

[deploy]
startCommand = "cd apps/web && npm run start"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

### Step 5: Deploy

1. Railway will auto-deploy on push
2. Visit the generated URL
3. Configure custom domain if needed

## Deploy to AWS

### Using AWS Amplify

1. Go to AWS Amplify Console
2. Connect repository
3. Configure build settings:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm install
           - npm run db:generate
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: apps/web/.next
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
   ```
4. Add environment variables
5. Deploy

### Using EC2 + RDS

1. **Set up RDS PostgreSQL**
   - Create RDS PostgreSQL instance
   - Note connection details
   - Configure security groups

2. **Set up EC2**
   ```bash
   # Install Node.js
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs

   # Install PM2
   sudo npm install -g pm2

   # Clone repository
   git clone <your-repo>
   cd everlight-ventures

   # Install dependencies
   npm install

   # Set up environment
   cp .env.example .env
   # Edit .env with production values

   # Run migrations
   npm run db:migrate:deploy

   # Build
   npm run build

   # Start with PM2
   cd apps/web
   pm2 start npm --name "everlight" -- start
   pm2 save
   pm2 startup
   ```

3. **Set up Nginx** (reverse proxy)
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. **Set up SSL** with Let's Encrypt
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

## Database Setup

### Neon (Recommended for Vercel)

1. Sign up at [neon.tech](https://neon.tech)
2. Create new project
3. Copy connection string
4. Add to DATABASE_URL
5. Run migrations:
   ```bash
   DATABASE_URL=<your-neon-url> npm run db:migrate:deploy
   ```

### Supabase

1. Sign up at [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → Database
4. Copy connection string (use "Connection pooling" for production)
5. Add to DATABASE_URL
6. Run migrations

### AWS RDS

1. Create RDS PostgreSQL instance
2. Configure security group
3. Note endpoint and credentials
4. Connection string format:
   ```
   postgresql://username:password@endpoint:5432/database?sslmode=require
   ```
5. Run migrations

## Post-Deployment

### 1. Verify Deployment

```bash
# Check health endpoint
curl https://yourdomain.com/api/health

# Expected response:
# {"status":"ok","database":"connected","timestamp":"..."}
```

### 2. Create First User

1. Visit https://yourdomain.com/auth/signin
2. Sign up with email/password
3. Create first project
4. Verify email (if configured)

### 3. Configure Email Service

For magic links to work, configure email service:

**SendGrid**:
```bash
EMAIL_SERVER_HOST="smtp.sendgrid.net"
EMAIL_SERVER_PORT="587"
EMAIL_SERVER_USER="apikey"
EMAIL_SERVER_PASSWORD="<sendgrid-api-key>"
```

**AWS SES**:
```bash
EMAIL_SERVER_HOST="email-smtp.us-east-1.amazonaws.com"
EMAIL_SERVER_PORT="587"
EMAIL_SERVER_USER="<aws-access-key-id>"
EMAIL_SERVER_PASSWORD="<smtp-password>"
```

**Resend** (for campaigns):
- Sign up at [resend.com](https://resend.com)
- Get API key
- Integrate in campaign send route

### 4. Set Up Monitoring

#### Vercel Analytics
- Enable in dashboard: Settings → Analytics

#### Sentry (Error Tracking)
```bash
npm install @sentry/nextjs

# Add to next.config.js
const { withSentryConfig } = require('@sentry/nextjs');

# Set SENTRY_DSN environment variable
```

#### Uptime Monitoring
Use services like:
- UptimeRobot
- Pingdom
- StatusCake

Monitor: `https://yourdomain.com/api/health`

### 5. Set Up Backups

#### Automated Database Backups

**Neon**: Automatic backups included

**Supabase**: Automatic backups included

**RDS**: Enable automated backups
```bash
aws rds modify-db-instance \
  --db-instance-identifier mydb \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00"
```

**Manual Backup**:
```bash
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

### 6. Security Checklist

- [ ] HTTPS enabled (SSL certificate)
- [ ] Environment variables secured
- [ ] Database uses SSL
- [ ] Strong NEXTAUTH_SECRET
- [ ] Email verification enabled
- [ ] Rate limiting configured
- [ ] CORS configured properly
- [ ] Security headers set
- [ ] Regular dependency updates

### 7. Performance Optimization

- [ ] Enable Vercel Edge Functions for API routes
- [ ] Configure CDN for static assets
- [ ] Set up database connection pooling
- [ ] Enable compression
- [ ] Configure caching headers
- [ ] Monitor database query performance

## Monitoring

### Application Monitoring

1. **Vercel Analytics**
   - Web Vitals
   - Page performance
   - Function invocations

2. **Database Monitoring**
   - Connection pool usage
   - Query performance
   - Database size

3. **Error Tracking**
   - Set up Sentry or similar
   - Monitor error rates
   - Set up alerts

### Health Checks

Set up automated health checks:

```bash
# Uptime monitor
curl https://yourdomain.com/api/health

# Database connectivity
# Monitor response time and "database": "connected"
```

### Alerts

Set up alerts for:
- API errors (> 1% error rate)
- Response time (> 2s)
- Database connection failures
- Disk space usage (> 80%)

## Rollback

If deployment fails:

### Vercel
1. Go to Deployments
2. Find last working deployment
3. Click "..." → "Promote to Production"

### Railway
1. Go to Deployments
2. Click on previous deployment
3. Click "Redeploy"

### AWS/EC2
```bash
# Revert to previous version
git checkout <previous-commit>
npm install
npm run build
pm2 restart everlight
```

## Troubleshooting

### Build Fails

**Issue**: Prisma client not generated
```bash
# Solution: Add to build command
npm run db:generate && npm run build
```

**Issue**: Environment variables not found
```bash
# Solution: Check environment variables are set in deployment platform
```

### Database Connection Fails

**Issue**: SSL mode required
```bash
# Solution: Add to DATABASE_URL
?sslmode=require
```

**Issue**: Connection pooling
```bash
# Solution: Use connection pooling for serverless
?pgbouncer=true&connection_limit=1
```

### Email Not Sending

**Issue**: Magic links not working
```bash
# Solution: Check email service credentials
# Verify EMAIL_SERVER_* variables are set correctly
# Test with your email provider's test mode first
```

## Cost Estimates

### Hobby/Small Scale (< 1000 users)
- Vercel: Free tier (Hobby)
- Database: Neon Free tier
- Email: SendGrid Free tier (100 emails/day)
- **Total**: $0/month

### Small Business (< 10k users)
- Vercel: Pro ($20/month)
- Database: Neon Scale ($20/month)
- Email: SendGrid Essentials ($15/month)
- **Total**: ~$55/month

### Growth (< 100k users)
- Vercel: Pro ($20/month)
- Database: Neon Pro ($50/month)
- Email: SendGrid Pro ($90/month)
- Monitoring: Sentry ($26/month)
- **Total**: ~$186/month

## Support

For deployment issues:
- Check [ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- Check [README.md](./README.md)
- Open an issue on GitHub
- Check deployment platform documentation

---

**Deployed successfully?** Don't forget to:
1. Set up monitoring
2. Configure backups
3. Test all features
4. Document any custom configuration
