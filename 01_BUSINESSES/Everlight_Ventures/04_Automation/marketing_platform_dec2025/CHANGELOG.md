# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Email service integration (Resend/Postmark)
- Email campaign analytics (opens, clicks)
- Contact segmentation
- Campaign templates
- Two-factor authentication
- Team collaboration features
- API access for integrations
- Webhook support

## [0.1.0] - 2025-12-26

### Added
- Initial MVP release
- User authentication (email/password + magic link)
- Multi-tenant project system
- Role-based access control (OWNER, EDITOR, VIEWER)
- Contact management (CRUD operations)
- CSV contact import with preview
- Newsletter campaign creation
- Campaign sending (dev mode with console logging)
- Dashboard with KPI cards
- Activity feed
- Health check endpoint
- Prisma + PostgreSQL database setup
- Shared UI component library
- AI orchestration stubs
- Comprehensive documentation
- Development tools (Makefile, Docker Compose, setup script)

### Technical
- Next.js 15 with App Router
- TypeScript strict mode
- Prisma ORM with PostgreSQL
- NextAuth.js for authentication
- Tailwind CSS for styling
- Turborepo monorepo setup
- npm workspaces

[Unreleased]: https://github.com/yourusername/everlight-ventures/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/everlight-ventures/releases/tag/v0.1.0
