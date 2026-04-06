# Broker OS -- Overview

*Last Updated: 2026-03-13*

## What Is Broker OS?

Broker OS is an autonomous B2B SaaS matchmaking platform built under Everlight Ventures. It connects businesses that need services with vetted providers -- acting as an AI-powered deal broker that runs 24/7 with minimal human intervention.

The system ingests leads, qualifies them, matches buyer to seller, and facilitates the introduction -- all orchestrated by AI agents and automated workflows.

## Revenue Model

- **Finder fee**: 15-30% commission on each matched deal
- **Target**: 5 deals/month at ~$5k average deal size = $5k/mo base revenue
- Revenue scales with deal volume and average deal size -- no cap on upside

## Key Components

| Component | Tech | Purpose |
|-----------|------|---------|
| Django broker_ops app | Django (in hive_dashboard) | Deal pipeline, CRM, matching engine |
| Daily Orchestrator | Python cron script | Automated daily lead processing & outreach |
| Lovable frontend | React/Lovable | Public-facing intake forms & client portal |
| Supabase | Postgres + Auth | Data layer & real-time sync |
| Gmail / ImprovMX | Email | Outreach & notifications via broker@everlightventures.io |
| Slack | Webhooks | Deal alerts, status updates, team notifications |

## File Routing

| Content Type | Save To |
|-------------|---------|
| Business docs & plans | `01_BUSINESSES/Everlight_Ventures/Broker_OS/` |
| Broker scripts | `03_AUTOMATION_CORE/01_Scripts/broker_*.py` |
| Django app code | `09_DASHBOARD/hive_dashboard/broker_ops/` |
| MCP server | `06_DEVELOPMENT/mcp_servers/broker_os/` |

## Status

MVP launched 2026-03-12. Core pipeline operational -- Daily Orchestrator running, Gmail integration active, Slack notifications wired up.
