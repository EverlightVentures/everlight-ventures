# Everlight Ventures - Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- Node.js >= 18.0.0
- PostgreSQL database (local or cloud)
- npm >= 9.0.0

## Option A: Automated Setup (Recommended)

```bash
# 1. Run setup script
bash scripts/setup.sh

# 2. Edit .env and set your DATABASE_URL
nano .env  # or use your favorite editor

# 3. Push database schema
npm run db:push

# 4. (Optional) Seed demo data
cd packages/db && npm run seed && cd ../..

# 5. Start development server
npm run dev
```

Visit http://localhost:3000

Demo login: `demo@everlight.dev` / `demo123` (if you ran seed)

## Option B: Manual Setup

```bash
# 1. Install dependencies
npm install

# 2. Create environment file
cp .env.example .env

# 3. Edit .env and configure:
#    - DATABASE_URL: Your PostgreSQL connection string
#    - NEXTAUTH_SECRET: Generate with: openssl rand -base64 32

# 4. Generate Prisma client
npm run db:generate

# 5. Push schema to database
npm run db:push

# 6. (Optional) Seed demo data
cd packages/db && npm run seed && cd ../..

# 7. Start development server
npm run dev
```

## Quick PostgreSQL Setup

### Option 1: Docker (Easiest)

```bash
docker run --name everlight-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=everlight_dev \
  -p 5432:5432 \
  -d postgres:16

# Use this DATABASE_URL in .env:
# DATABASE_URL="postgresql://postgres:postgres@localhost:5432/everlight_dev"
```

### Option 2: Cloud (Neon)

1. Sign up at https://neon.tech
2. Create a new project
3. Copy the connection string to DATABASE_URL in .env

### Option 3: Cloud (Supabase)

1. Sign up at https://supabase.com
2. Create a new project
3. Go to Settings → Database → Connection string
4. Copy the connection string to DATABASE_URL in .env

## Verify Installation

```bash
# Check health endpoint
curl http://localhost:3000/api/health

# Expected response:
# {"status":"ok","timestamp":"...","database":"connected","version":"0.1.0"}
```

## First Steps

1. **Create an account**: Visit http://localhost:3000/auth/signin
2. **Create a project**: Click "Create Project"
3. **Add contacts**:
   - Manually: Click "Add Contact"
   - Bulk: Click "Import CSV" (see sample below)
4. **Create a campaign**: Go to Campaigns → Create Campaign
5. **Send campaign**: Open campaign → Send (check console logs)

## Sample CSV for Import

Create a file `contacts.csv`:

```csv
email,firstName,lastName,company,tags
alice@example.com,Alice,Anderson,Acme Corp,"vip,customer"
bob@example.com,Bob,Builder,BuildCo,prospect
carol@example.com,Carol,Chen,TechStart,customer
```

## Common Issues

### Database connection failed

**Error**: `Can't reach database server`

**Solution**:
- Check PostgreSQL is running: `docker ps` or `pg_isready`
- Verify DATABASE_URL in .env is correct
- Check firewall rules if using cloud database

### Port 3000 already in use

**Error**: `Port 3000 is already in use`

**Solution**:
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use a different port
PORT=3001 npm run dev
```

### Prisma client not generated

**Error**: `Cannot find module '@prisma/client'`

**Solution**:
```bash
npm run db:generate
```

## Available Commands

```bash
# Development
npm run dev              # Start dev server (all packages)
npm run build            # Build for production
npm run start            # Start production server

# Database
npm run db:generate      # Generate Prisma client
npm run db:push          # Push schema to database (dev)
npm run db:migrate       # Run migrations (production)
npm run db:studio        # Open Prisma Studio GUI

# Utilities
npm run lint             # Lint all packages
npm run clean            # Clean build artifacts
```

## Project Structure

```
everlight-ventures/
├── apps/web/           → Next.js application
├── packages/
│   ├── db/             → Prisma + database
│   ├── ui/             → Shared components
│   └── ai/             → AI stubs
├── docs/               → Documentation
├── .env                → Your environment variables (gitignored)
├── .env.example        → Template for .env
└── README.md           → Full documentation
```

## Next Steps

- 📖 Read [README.md](./README.md) for full documentation
- 🏗️ Read [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for technical details
- 📋 Read [docs/BUILD_REPORT.md](./docs/BUILD_REPORT.md) for what was built

## Need Help?

- Check [README.md](./README.md) for detailed setup instructions
- Check [docs/BUILD_REPORT.md](./docs/BUILD_REPORT.md) for troubleshooting
- Open an issue on GitHub

## Security Note

⚠️ **For production deployment**:
- Generate a new NEXTAUTH_SECRET: `openssl rand -base64 32`
- Use a secure DATABASE_URL with strong password
- Set up proper email service for magic links
- Enable SSL/TLS for database connections
- Review [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) security section

---

**Happy building!** 🚀
