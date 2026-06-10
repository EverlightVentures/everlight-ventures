# Everlight Ventures

A multi-tenant SaaS platform for managing contacts and newsletter campaigns. Built with Next.js, Prisma, and PostgreSQL.

## Features

- **Authentication**: Email/password and magic link authentication
- **Multi-tenant Projects**: Create and manage multiple projects with role-based access (Owner, Editor, Viewer)
- **Contacts Management**: CRUD operations with CSV import support
- **Newsletter Campaigns**: Create and send email campaigns to subscribed contacts
- **Dashboard**: KPI cards showing contacts, campaigns, and recent activity
- **AI-Ready**: Stub AI orchestration package ready for future integrations

## Architecture

This is a monorepo using npm workspaces and Turbo:

```
everlight-ventures/
├── apps/
│   └── web/              # Next.js application
├── packages/
│   ├── db/               # Prisma schema and client
│   ├── ui/               # Shared Tailwind UI components
│   └── ai/               # AI orchestration stubs
└── docs/                 # Documentation
```

## Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0
- PostgreSQL database

## Getting Started

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd everlight-ventures
npm install
```

### 2. Set up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure your database and authentication settings:

- `DATABASE_URL`: Your PostgreSQL connection string
- `NEXTAUTH_SECRET`: Generate with `openssl rand -base64 32`
- Email settings are optional for development (magic links will log to console)

### 3. Set up Database

```bash
# Generate Prisma client
npm run db:generate

# Push schema to database (for development)
npm run db:push

# Or run migrations (for production)
npm run db:migrate

# Seed demo data (optional)
cd packages/db && npm run seed
```

### 4. Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### 5. Demo Credentials

If you ran the seed script, you can log in with:

- Email: `demo@everlight.dev`
- Password: `demo123`

## Available Scripts

### Root Scripts

- `npm run dev` - Start all apps in development mode
- `npm run build` - Build all apps for production
- `npm run lint` - Lint all apps
- `npm run test` - Run tests
- `npm run clean` - Clean all build artifacts and node_modules

### Database Scripts

- `npm run db:generate` - Generate Prisma client
- `npm run db:push` - Push schema changes to database (dev)
- `npm run db:migrate` - Run migrations (prod)
- `npm run db:studio` - Open Prisma Studio

## Project Structure

### Apps

#### `apps/web` - Next.js Application

- **App Router**: Using Next.js 15 app directory
- **Authentication**: NextAuth.js with credentials and email providers
- **API Routes**: RESTful API for projects, contacts, and campaigns
- **Pages**:
  - `/` - Redirects to dashboard or sign in
  - `/auth/signin` - Authentication page
  - `/dashboard` - Project list or redirect to single project
  - `/projects/:slug` - Project dashboard with KPIs
  - `/projects/:slug/contacts` - Contacts list and management
  - `/projects/:slug/campaigns` - Campaign management

### Packages

#### `packages/db` - Database Layer

- **Prisma Schema**: Multi-tenant data model
- **Models**: User, Project, ProjectMember, Contact, Campaign, Activity
- **Seed Script**: Demo data for development

#### `packages/ui` - Shared UI Components

- Button, Card, Input, Label, Badge, Table
- Tailwind CSS with class-variance-authority
- Fully typed with TypeScript

#### `packages/ai` - AI Orchestration

- Stub implementations ready for integration
- `generateCompletion()` - General text completion
- `generateEmailContent()` - Email content generation
- `enrichContact()` - Contact data enrichment

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/[...nextauth]` - NextAuth endpoints

### Projects

- `POST /api/projects` - Create new project
- `GET /api/projects/:slug/...` - Project-scoped endpoints

### Contacts

- `POST /api/projects/:slug/contacts` - Create contact
- `POST /api/projects/:slug/contacts/import` - Import contacts from CSV

### Campaigns

- `POST /api/projects/:slug/campaigns` - Create campaign
- `POST /api/projects/:slug/campaigns/:id/send` - Send campaign

### Health Check

- `GET /api/health` - Health check endpoint

## Multi-Tenant Architecture

The platform uses a multi-tenant design where:

1. Each **Project** is a tenant
2. Users can be members of multiple projects
3. Membership roles (OWNER, EDITOR, VIEWER) control access
4. All data (contacts, campaigns) is scoped to a project

## Email Campaign System

Campaigns are structured to make swapping email providers easy:

1. Create campaign as DRAFT
2. Send campaign triggers:
   - Creates `CampaignRecipient` records
   - Updates status to SENDING
   - In dev: logs to console
   - In prod: integrate with Resend/Postmark/SendGrid
3. Track delivery status per recipient

To integrate a real email service, modify:
- `apps/web/src/app/api/projects/[slug]/campaigns/[id]/send/route.ts`

## CSV Import

The contacts import feature supports CSV files with these columns:

- `email` (required)
- `firstName`
- `lastName`
- `company`
- `phone`
- `tags` (comma-separated)

Additional columns are stored in the `customData` JSON field.

## Production Deployment

### Environment Variables

Set all environment variables from `.env.example` in your deployment platform.

### Database Migrations

```bash
npm run db:migrate:deploy
```

### Build

```bash
npm run build
cd apps/web
npm run start
```

### Recommended Platforms

- **Vercel**: Optimal for Next.js
- **Railway/Render**: For full-stack with PostgreSQL
- **AWS/GCP**: For enterprise deployments

## Development

### Adding a New Feature

1. Update Prisma schema if needed (`packages/db/schema.prisma`)
2. Run `npm run db:generate` to update client
3. Create API routes in `apps/web/src/app/api/`
4. Create UI pages in `apps/web/src/app/`
5. Use shared components from `@everlight/ui`

### Testing

Health check endpoint for automated testing:

```bash
curl http://localhost:3000/api/health
```

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.
