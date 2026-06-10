# Everlight Ventures - Architecture Documentation

## Overview

Everlight Ventures is a multi-tenant SaaS platform built with a modern, scalable architecture. This document details the technical architecture, design decisions, and patterns used throughout the application.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client (Browser)                     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Sign In    │  │  Dashboard   │  │   Contacts   │      │
│  │     Page     │  │     Page     │  │     Page     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Next.js App Router                       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Server Components (SSR)                  │   │
│  │  • Authentication checks                              │   │
│  │  • Data fetching                                      │   │
│  │  • Authorization logic                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   API Routes                          │   │
│  │  /api/auth/*        - Authentication                  │   │
│  │  /api/projects/*    - Project management              │   │
│  │  /api/contacts/*    - Contact management              │   │
│  │  /api/campaigns/*   - Campaign management             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Prisma ORM
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       PostgreSQL Database                    │
│                                                               │
│  • Users & Authentication                                    │
│  • Projects & Memberships (Multi-tenant)                     │
│  • Contacts                                                   │
│  • Campaigns & Recipients                                    │
│  • Activity Logs                                             │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Tenant Architecture

### Tenancy Model

Everlight uses a **Project-based multi-tenancy** model where:

1. **Project = Tenant**: Each project is an isolated tenant
2. **Users can belong to multiple tenants** via ProjectMember table
3. **Data isolation**: All resources (contacts, campaigns) are scoped to projectId
4. **Row-level security**: Enforced at application layer via authorization checks

### Data Isolation Strategy

```typescript
// Every query includes project authorization
const contacts = await prisma.contact.findMany({
  where: {
    projectId: authorizedProjectId, // ✅ Always included
  },
});
```

### Benefits

- ✅ Simple to implement and maintain
- ✅ Cost-effective (single database)
- ✅ Easy to query across tenants (analytics)
- ✅ Good performance with proper indexing
- ⚠️ Requires careful authorization logic

### Alternative Architectures Considered

1. **Database-per-tenant**: More isolated but complex to manage
2. **Schema-per-tenant**: Middle ground, considered if scaling issues arise
3. **Shared-everything**: Not suitable for SaaS

## Authentication & Authorization

### Authentication Flow

```
User Sign In
    ↓
NextAuth.js validates credentials
    ↓
JWT token created with user ID
    ↓
Token stored in HTTP-only cookie
    ↓
Server validates JWT on each request
```

### Authorization Pattern

```typescript
// 1. Get current user from session
const session = await getServerSession(authOptions);
if (!session?.user?.id) {
  return unauthorized();
}

// 2. Verify project access
const project = await getProjectBySlug(slug, session.user.id);
if (!project) {
  return notFound();
}

// 3. Check role permissions
if (project.role === 'VIEWER' && operation === 'WRITE') {
  return forbidden();
}

// 4. Execute authorized operation
await performOperation(project.id);
```

### Role-Based Access Control (RBAC)

| Role   | Read | Write | Delete | Invite Members |
|--------|------|-------|--------|----------------|
| OWNER  | ✅   | ✅    | ✅     | ✅             |
| EDITOR | ✅   | ✅    | ✅     | ❌             |
| VIEWER | ✅   | ❌    | ❌     | ❌             |

Implemented in: `apps/web/src/lib/session.ts`

## Database Schema Design

### Core Principles

1. **Normalization**: 3NF for most tables
2. **Denormalization**: Activity log contains duplicate data for performance
3. **Soft deletes**: Not implemented (hard deletes with cascade)
4. **Audit trail**: Activity table logs all important actions

### Key Relationships

```
User ──────< ProjectMember >────── Project
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
                Contact           Campaign          Activity
                    │                 │
                    └────< CampaignRecipient >────┘
```

### Indexing Strategy

All foreign keys are indexed:
```prisma
@@index([projectId])
@@index([userId])
@@index([email])
```

Composite unique constraints for preventing duplicates:
```prisma
@@unique([projectId, email])  // No duplicate emails per project
@@unique([projectId, userId]) // No duplicate memberships
```

## API Design

### RESTful Conventions

```
GET    /api/projects/:slug              - Get project
POST   /api/projects                    - Create project
GET    /api/projects/:slug/contacts     - List contacts
POST   /api/projects/:slug/contacts     - Create contact
POST   /api/projects/:slug/contacts/import - Bulk import
```

### Error Handling

All API routes return consistent error format:

```json
{
  "error": "Human-readable message",
  "details": [/* validation errors */]
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (not logged in)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

### Input Validation

Using Zod schemas for type-safe validation:

```typescript
const createContactSchema = z.object({
  email: z.string().email(),
  firstName: z.string().optional(),
  // ...
});

const data = createContactSchema.parse(body);
```

## Frontend Architecture

### Server vs Client Components

**Server Components** (default):
- Dashboard pages
- Data fetching
- Authentication checks
- Better performance, smaller bundles

**Client Components** (`'use client'`):
- Forms with state
- Interactive tables
- Search functionality
- Event handlers

### Data Flow

```
1. User navigates to page
2. Server Component fetches data
3. Data passed as props to Client Components
4. User interacts → Client calls API
5. API updates database
6. router.refresh() triggers re-fetch
7. UI updates with new data
```

### State Management

- **No global state library needed** (yet)
- Server state: React Server Components
- Client state: React useState/useReducer
- URL state: Next.js router
- Form state: Native forms + react-hook-form (ready to add)

## Campaign Sending Architecture

### Current Implementation (Dev Mode)

```
1. User clicks "Send Campaign"
2. API creates CampaignRecipient records
3. Campaign status → SENDING
4. For each contact:
   - Log to console (dev mode)
   - Mark as SENT
5. Campaign status → SENT
6. Log activity
```

### Production-Ready Design

```typescript
// Location: apps/web/src/app/api/projects/[slug]/campaigns/[id]/send/route.ts

// Replace this:
console.log(`📧 Sending to: ${contact.email}`);

// With this:
await emailService.send({
  to: contact.email,
  from: process.env.EMAIL_FROM,
  subject: campaign.subject,
  html: campaign.htmlContent,
  text: campaign.textContent,
  tags: {
    campaignId: campaign.id,
    contactId: contact.id,
  },
});
```

### Recommended Email Services

1. **Resend** - Developer-friendly, great API
2. **Postmark** - Reliable, excellent deliverability
3. **SendGrid** - Scalable, feature-rich
4. **AWS SES** - Cost-effective at scale

### Webhook Integration (Future)

For tracking opens, clicks, bounces:

```typescript
// POST /api/webhooks/email
export async function POST(req: Request) {
  const event = await req.json();

  if (event.type === 'delivered') {
    await prisma.campaignRecipient.update({
      where: { id: event.recipientId },
      data: {
        status: 'DELIVERED',
        deliveredAt: new Date(),
      },
    });
  }
}
```

## CSV Import Architecture

### Processing Flow

```
1. User uploads CSV file
2. PapaParse parses in browser
3. Preview shown (first 5 rows)
4. User confirms import
5. POST to /api/projects/:slug/contacts/import
6. Server validates each row
7. Upsert contacts (update if exists)
8. Create activity log
9. Return success count
```

### Error Handling

```typescript
const results = await Promise.allSettled(
  contacts.map(async (contact) => {
    // Will not fail entire import if one contact fails
    return prisma.contact.upsert(/*...*/);
  })
);

const successful = results.filter(r => r.status === 'fulfilled').length;
const failed = results.filter(r => r.status === 'rejected').length;
```

### Performance Considerations

- **Batch size**: Currently unlimited, consider batching for 10k+ contacts
- **Transaction**: Not wrapped in transaction (partial success is OK)
- **Validation**: Happens per-row, could be optimized with bulk validation

## Monorepo Architecture

### Package Structure

```
packages/
├── db/           # Database layer
│   ├── Prisma client
│   ├── Schema
│   └── Seed scripts
├── ui/           # Shared components
│   ├── Button, Card, etc.
│   ├── Tailwind config
│   └── Type definitions
└── ai/           # AI integrations
    └── Stub functions
```

### Benefits

1. **Code Sharing**: Import `@everlight/db` in any app
2. **Type Safety**: TypeScript across entire monorepo
3. **Build Optimization**: Turbo builds only changed packages
4. **Version Sync**: All packages use same dependencies

### Workspace Configuration

```json
{
  "workspaces": ["apps/*", "packages/*"]
}
```

Enables:
- `npm install` in root installs all dependencies
- Packages can import from each other
- Hoisted dependencies reduce disk usage

## Performance Optimization

### Current Optimizations

1. **Database**:
   - Indexes on all foreign keys
   - `select` only needed fields
   - `include` to reduce queries

2. **Frontend**:
   - Server Components for static content
   - Client Components only when needed
   - Next.js automatic code splitting

3. **API**:
   - Parallel queries with Promise.all()
   - Database connection pooling (Prisma)

### Future Optimizations

1. **Caching**:
   - Redis for session caching
   - React Query for client cache
   - CDN for static assets

2. **Database**:
   - Read replicas for heavy queries
   - Materialized views for analytics
   - Connection pooling with PgBouncer

3. **Frontend**:
   - Image optimization with next/image
   - Font optimization
   - Pagination for large lists

## Security

### Implemented

✅ **Authentication**:
- Bcrypt password hashing (cost factor 10)
- JWT tokens in HTTP-only cookies
- Secure session management

✅ **Authorization**:
- Project-level access control
- Role-based permissions
- Server-side verification

✅ **Input Validation**:
- Zod schema validation
- SQL injection prevention (Prisma)
- XSS prevention (React escaping)

✅ **CSRF Protection**:
- NextAuth built-in CSRF tokens
- SameSite cookie policy

### To Implement

⚠️ **Rate Limiting**:
```typescript
// Add middleware for API routes
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
```

⚠️ **Email Verification**:
- Verify email addresses on signup
- Prevent spam accounts

⚠️ **2FA**:
- TOTP-based 2FA
- Backup codes

## Monitoring & Observability

### Health Check

```bash
GET /api/health

Response:
{
  "status": "ok",
  "timestamp": "2025-12-26T10:00:00.000Z",
  "database": "connected",
  "version": "0.1.0"
}
```

### Recommended Monitoring

1. **Application Monitoring**:
   - Sentry for error tracking
   - Vercel Analytics for performance
   - LogRocket for session replay

2. **Database Monitoring**:
   - Query performance
   - Connection pool usage
   - Slow query log

3. **Business Metrics**:
   - Sign-ups per day
   - Campaigns sent
   - Active projects

## Deployment Architecture

### Recommended Setup

```
┌─────────────────────────────────────────┐
│           Vercel (Next.js App)          │
│  • Automatic deployments from git       │
│  • Edge functions                       │
│  • CDN for static assets                │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         Neon / Supabase (PostgreSQL)    │
│  • Managed database                     │
│  • Automatic backups                    │
│  • Connection pooling                   │
└─────────────────────────────────────────┘
```

### Environment Separation

```
Development → Preview → Production
  │            │          │
  └── Local    └── Staging └── Live
      DB           DB          DB
```

## Scaling Considerations

### Current Capacity

With current architecture:
- **Projects**: Millions (limited by database)
- **Contacts per project**: 100k+ (add pagination)
- **Campaigns per day**: 1000s (with email service)

### Vertical Scaling

1. Upgrade database instance
2. Increase Vercel compute limits
3. Add read replicas

### Horizontal Scaling

1. **Database Sharding**:
   - Shard by projectId
   - Each shard handles subset of projects

2. **Microservices**:
   - Campaign sending service
   - Email tracking service
   - Analytics service

3. **Message Queue**:
   - Bull/BullMQ for background jobs
   - Redis for job queue
   - Separate workers for sending

## Extension Points

### Adding New Features

The architecture supports easy extension:

1. **New Data Models**:
   - Add to Prisma schema
   - Generate client
   - Create API routes
   - Build UI pages

2. **New API Endpoints**:
   - Follow existing patterns in `apps/web/src/app/api/`
   - Use Zod validation
   - Implement authorization

3. **New UI Components**:
   - Add to `packages/ui/`
   - Follow existing patterns
   - Export from index

### AI Integration

The `packages/ai` stub is ready:

```typescript
import { AI } from '@everlight/ai';

// Generate email content
const { html, text } = await AI.generateEmailContent({
  subject: 'Product Update',
  tone: 'professional',
  purpose: 'Announce new features',
});

// Enrich contact
const enrichedData = await AI.enrichContact('user@example.com');
```

Just implement the functions with real AI API calls.

## Testing Strategy (Recommended)

### Unit Tests

```typescript
// packages/db/__tests__/user.test.ts
describe('User model', () => {
  it('should hash password on creation', async () => {
    const user = await createUser({ email, password });
    expect(user.passwordHash).not.toBe(password);
  });
});
```

### Integration Tests

```typescript
// apps/web/__tests__/api/contacts.test.ts
describe('POST /api/projects/:slug/contacts', () => {
  it('should create contact with valid data', async () => {
    const res = await fetch('/api/projects/test/contacts', {
      method: 'POST',
      body: JSON.stringify({ email: 'test@example.com' }),
    });
    expect(res.status).toBe(200);
  });
});
```

### E2E Tests

```typescript
// e2e/campaign-flow.spec.ts
test('create and send campaign', async ({ page }) => {
  await page.goto('/projects/test/campaigns/new');
  await page.fill('input[name="subject"]', 'Test Campaign');
  await page.click('button[type="submit"]');
  await page.click('text=Send');
  await expect(page).toHaveURL(/campaigns$/);
});
```

## Conclusion

This architecture provides:

✅ **Scalability**: Multi-tenant design supports growth
✅ **Maintainability**: Clear separation of concerns
✅ **Performance**: Optimized queries and rendering
✅ **Security**: Defense in depth
✅ **Developer Experience**: Type-safe, well-structured code
✅ **Extensibility**: Easy to add new features

The foundation is solid for building the "Lovable-but-better" website builder vision.
