#!/usr/bin/env python3
"""
Broker OS MCP Server - Everlight Ventures

Replaces ALL third-party services with self-hosted tools:
  - Product Hunt / Apollo / lead gen -> built-in public web scraping (RSS, public APIs)
  - FirstPromoter -> built-in commission tracking via Django broker_ops
  - SMTP services -> built-in email via Python smtplib
  - Cron services -> built-in scheduler via APScheduler-style loop
  - Agreement templates -> built-in doc generator

Transport: stdio (for Claude Code integration)
"""
import asyncio
import csv
import io
import json
import logging
import os
import re
import smtplib
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import Resource, ResourceTemplate, TextContent, TextResourceContents, Tool

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Auto-load .env from credentials vault
_ENV_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

WORKSPACE     = Path(os.environ.get("WORKSPACE", "/mnt/sdcard/AA_MY_DRIVE"))
DJANGO_URL    = os.environ.get("DJANGO_URL", "http://127.0.0.1:8504")
LOG_DIR       = WORKSPACE / "_logs" / "broker_ops"
STAGING_INBOX = WORKSPACE / "07_STAGING" / "Inbox"
CRON_DB       = LOG_DIR / "scheduler.db"
DJANGO_DB     = WORKSPACE / "09_DASHBOARD" / "hive_dashboard" / "db.sqlite3"

# SMTP (set via env vars)
SMTP_HOST     = os.environ.get("SMTP_HOST", "")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER     = os.environ.get("SMTP_USER", "")
SMTP_PASS     = os.environ.get("SMTP_PASS", "")
SMTP_FROM     = os.environ.get("SMTP_FROM", "broker@everlightventures.io")

# Warm-up tracking
WARMUP_DB     = LOG_DIR / "warmup.db"

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [BROKER-MCP] %(levelname)s %(message)s"
)
log = logging.getLogger("broker_mcp")

LOG_DIR.mkdir(parents=True, exist_ok=True)

server = Server("broker-os")


def _db_rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if not DJANGO_DB.exists():
        return []
    conn = sqlite3.connect(DJANGO_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _db_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    rows = _db_rows(query, params)
    return rows[0] if rows else {}


def _json_resource(uri: str, payload: dict[str, Any]) -> list[TextResourceContents]:
    return [
        TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(payload, indent=2, default=str),
        )
    ]


def _resource_error(uri: str, message: str) -> list[TextResourceContents]:
    return _json_resource(uri, {"error": message})

# ---------------------------------------------------------------------------
# Relevance keywords
# ---------------------------------------------------------------------------

RELEVANT_KW = [
    "ai", "saas", "automation", "workflow", "api", "agent", "gpt",
    "productivity", "analytics", "dashboard", "crm", "integration",
    "stripe", "supabase", "django", "python", "no-code", "low-code",
    "fintech", "compliance", "b2b", "startup", "llm", "chatbot",
    "devtools", "infrastructure", "cloud", "security", "data",
]


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in RELEVANT_KW)


def _guess_category(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["computer vision", "opencv", "image recognition", "face detection",
                              "object detection", "ocr", "image processing", "visual inspection",
                              "defect detection", "receipt scan"]):
        return "computer_vision"
    if any(k in t for k in ["fintech", "compliance", "stripe", "payment", "bank", "crypto"]):
        return "fintech"
    if any(k in t for k in ["health", "hipaa", "clinic", "medical"]):
        return "healthtech"
    if any(k in t for k in ["marketing", "seo", "social", "content", "email"]):
        return "marketing"
    if any(k in t for k in ["logistic", "shipping", "supply"]):
        return "logistics"
    if any(k in t for k in ["real estate", "property", "wholesale", "mls"]):
        return "real_estate"
    if any(k in t for k in ["ai", "gpt", "agent", "llm", "automation", "saas"]):
        return "ai_saas"
    if any(k in t for k in ["dev", "api", "backend", "frontend", "code"]):
        return "dev_service"
    if any(k in t for k in ["website", "domain", "landing page"]):
        return "website"
    return "other"


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    # === LEAD/OFFER SOURCING (replaces Product Hunt API token, Apollo, etc) ===
    Tool(
        name="scout_hacker_news",
        description="Scrape Hacker News 'Show HN' posts via public Algolia API. No auth needed. Returns AI/SaaS relevant products as potential offers.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'saas ai automation')", "default": "saas ai automation"},
                "limit": {"type": "integer", "description": "Max results", "default": 30},
            },
        },
    ),
    Tool(
        name="scout_product_hunt_rss",
        description="Scrape Product Hunt newest posts via public RSS feed. No API token needed. Returns products as potential offers.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    ),
    Tool(
        name="scout_indiehackers_rss",
        description="Scrape IndieHackers RSS feed for new SaaS/tool launches. No auth needed.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
        },
    ),
    Tool(
        name="scout_github_trending",
        description="Scrape GitHub trending repos (public page) for dev tools and SaaS projects.",
        inputSchema={
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "Filter by language (python, javascript, etc)", "default": ""},
                "since": {"type": "string", "description": "daily, weekly, or monthly", "default": "weekly"},
            },
        },
    ),
    Tool(
        name="scout_devto",
        description="Search DEV.to public API for SaaS/AI/startup articles and product launches. No auth needed.",
        inputSchema={
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Tag to search (saas, ai, startup, etc)", "default": "saas"},
                "limit": {"type": "integer", "default": 25},
            },
        },
    ),
    Tool(
        name="web_scrape_public",
        description="Fetch and extract text from any public URL. For scouting product pages, blog posts, company info.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "extract_emails": {"type": "boolean", "description": "Also extract email addresses from page", "default": False},
            },
            "required": ["url"],
        },
    ),

    # === DJANGO BROKER OPS (replaces FirstPromoter, commission tracking) ===
    Tool(
        name="broker_ingest_offer",
        description="Add a seller's product/service to the Broker OS offer catalog via Django API.",
        inputSchema={
            "type": "object",
            "properties": {
                "seller_name": {"type": "string"},
                "seller_email": {"type": "string", "default": ""},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string", "enum": ["ai_saas", "computer_vision", "dev_service", "fintech", "healthtech", "marketing", "logistics", "real_estate", "website", "other"], "default": "ai_saas"},
                "keywords": {"type": "array", "items": {"type": "string"}, "default": []},
                "price_min": {"type": "number", "default": 0},
                "price_max": {"type": "number", "default": 0},
                "commission_pct": {"type": "number", "default": 20.0},
                "source": {"type": "string", "default": "mcp_scout"},
                "source_url": {"type": "string", "default": ""},
            },
            "required": ["seller_name", "title", "description"],
        },
    ),
    Tool(
        name="broker_ingest_lead",
        description="Add a buyer lead to the Broker OS pipeline via Django API.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "default": ""},
                "company": {"type": "string", "default": ""},
                "role": {"type": "string", "default": ""},
                "need_description": {"type": "string"},
                "categories_needed": {"type": "array", "items": {"type": "string"}, "default": []},
                "budget_min": {"type": "number", "default": 0},
                "budget_max": {"type": "number", "default": 0},
                "intent": {"type": "string", "enum": ["hot", "warm", "cold"], "default": "warm"},
                "lead_source": {"type": "string", "default": "mcp_scout"},
            },
            "required": ["name", "need_description"],
        },
    ),
    Tool(
        name="broker_run_matching",
        description="Run the AI matching engine to pair offers with leads. Returns scored matches.",
        inputSchema={
            "type": "object",
            "properties": {
                "min_score": {"type": "number", "default": 40.0},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
    ),
    Tool(
        name="broker_approve_match",
        description="Approve a match and create a deal with specified value.",
        inputSchema={
            "type": "object",
            "properties": {
                "match_id": {"type": "string", "description": "UUID of the BrokerMatch"},
                "deal_value": {"type": "number", "description": "Total deal value in USD"},
                "notes": {"type": "string", "default": ""},
            },
            "required": ["match_id", "deal_value"],
        },
    ),
    Tool(
        name="broker_close_deal",
        description="Close a deal as won or lost.",
        inputSchema={
            "type": "object",
            "properties": {
                "deal_id": {"type": "string", "description": "UUID of the Deal"},
                "won": {"type": "boolean", "default": True},
            },
            "required": ["deal_id"],
        },
    ),
    Tool(
        name="broker_status",
        description="Get full Broker OS pipeline status: offers, leads, matches, deals, commissions.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="broker_commission_report",
        description="Get commission summary: earned, pending, paid, unpaid balance.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # === EMAIL / OUTREACH (replaces SMTP services) ===
    Tool(
        name="email_send",
        description="Send an email via configured SMTP. Tracks warm-up limits. Requires SMTP env vars.",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string", "description": "Plain text body"},
                "html_body": {"type": "string", "description": "Optional HTML body", "default": ""},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="email_warmup_status",
        description="Check email sending limits and warm-up progress for the configured domain.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="email_draft_outreach",
        description="Generate a personalized outreach email draft (seller intro or buyer intro). Does NOT send.",
        inputSchema={
            "type": "object",
            "properties": {
                "template": {"type": "string", "enum": ["seller_intro", "buyer_intro", "followup", "breakup"]},
                "recipient_name": {"type": "string"},
                "product_name": {"type": "string", "default": ""},
                "company_name": {"type": "string", "default": ""},
                "source": {"type": "string", "default": ""},
                "need": {"type": "string", "default": ""},
                "custom_hook": {"type": "string", "description": "Personalized opening line", "default": ""},
            },
            "required": ["template", "recipient_name"],
        },
    ),

    # === AGREEMENT GENERATOR (replaces lawyer for templates) ===
    Tool(
        name="generate_finder_agreement",
        description="Generate a finder fee agreement template for a specific deal. Outputs markdown.",
        inputSchema={
            "type": "object",
            "properties": {
                "finder_name": {"type": "string", "default": "Everlight Ventures"},
                "finder_entity": {"type": "string", "default": "Everlight Logistics LLC"},
                "client_name": {"type": "string"},
                "client_company": {"type": "string", "default": ""},
                "commission_pct": {"type": "number", "default": 20.0},
                "deal_description": {"type": "string"},
                "payment_terms": {"type": "string", "default": "Net 30 from close date"},
                "duration_months": {"type": "integer", "default": 12},
            },
            "required": ["client_name", "deal_description"],
        },
    ),

    # === SCHEDULER (replaces cron services) ===
    Tool(
        name="scheduler_add_job",
        description="Schedule a recurring broker pipeline job (ingest, match, report).",
        inputSchema={
            "type": "object",
            "properties": {
                "job_name": {"type": "string", "description": "Unique name for this job"},
                "command": {"type": "string", "description": "Shell command to run"},
                "schedule": {"type": "string", "description": "Cron expression (e.g. '0 6 * * *' for 6AM daily)"},
                "enabled": {"type": "boolean", "default": True},
            },
            "required": ["job_name", "command", "schedule"],
        },
    ),
    Tool(
        name="scheduler_list_jobs",
        description="List all scheduled broker pipeline jobs.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="scheduler_remove_job",
        description="Remove a scheduled job by name.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_name": {"type": "string"},
            },
            "required": ["job_name"],
        },
    ),
    Tool(
        name="scheduler_install_crontab",
        description="Write all enabled jobs to the system crontab. Makes schedules persistent.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # === ANALYTICS (replaces dashboards) ===
    Tool(
        name="broker_kpi_snapshot",
        description="Generate a full KPI snapshot: funnel metrics, conversion rates, revenue forecast.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # === BULK OPERATIONS ===
    Tool(
        name="bulk_scout_all_sources",
        description="Run all scouts (HN, Reddit, GitHub trending, IndieHackers) in one call. Returns combined results.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit_per_source": {"type": "integer", "default": 15},
                "auto_ingest": {"type": "boolean", "description": "Auto-POST results to Django broker_ops", "default": False},
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            name="Broker Pipeline Status",
            title="Broker Pipeline Status",
            uri="broker://pipeline/status",
            description="Live broker pipeline counts, commission totals, and open opportunities.",
            mimeType="application/json",
        ),
        Resource(
            name="Business Revenue Streams",
            title="Business Revenue Streams",
            uri="broker://business/revenue/streams",
            description="Tracked revenue streams from the Business OS ledger.",
            mimeType="application/json",
        ),
        Resource(
            name="Recent Business Events",
            title="Recent Business Events",
            uri="broker://business/events/recent",
            description="Most recent structured business events for the OS control plane.",
            mimeType="application/json",
        ),
        Resource(
            name="Open Business Alerts",
            title="Open Business Alerts",
            uri="broker://business/alerts/open",
            description="Current open incidents and approvals from the Business OS ledger.",
            mimeType="application/json",
        ),
        Resource(
            name="Pending Broker Matches",
            title="Pending Broker Matches",
            uri="broker://matches/pending",
            description="Top pending and approved broker matches waiting on action.",
            mimeType="application/json",
        ),
        Resource(
            name="Active Broker Deals",
            title="Active Broker Deals",
            uri="broker://deals/active",
            description="Current broker deals and commission exposure.",
            mimeType="application/json",
        ),
    ]


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            name="Broker Match Detail",
            title="Broker Match Detail",
            uriTemplate="broker://match/{id}",
            description="Detailed broker match record by UUID.",
            mimeType="application/json",
        ),
        ResourceTemplate(
            name="Broker Deal Detail",
            title="Broker Deal Detail",
            uriTemplate="broker://deal/{id}",
            description="Detailed broker deal record by UUID.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: Any) -> list[TextResourceContents]:
    uri_str = str(uri)

    try:
        if uri_str == "broker://pipeline/status":
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "offers": _db_one(
                    """
                    SELECT
                      COUNT(*) AS total,
                      SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active
                    FROM broker_ops_offerlisting
                    """
                ),
                "leads": _db_one(
                    """
                    SELECT
                      COUNT(*) AS total,
                      SUM(CASE WHEN intent = 'hot' AND unsubscribed = 0 THEN 1 ELSE 0 END) AS hot
                    FROM broker_ops_leadprofile
                    """
                ),
                "matches": _db_one(
                    """
                    SELECT
                      COUNT(*) AS total,
                      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                      SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved
                    FROM broker_ops_brokermatch
                    """
                ),
                "deals": _db_one(
                    """
                    SELECT
                      COUNT(*) AS total,
                      SUM(CASE WHEN stage = 'closed_won' THEN 1 ELSE 0 END) AS closed_won,
                      SUM(CASE WHEN stage IN ('intro', 'negotiating', 'contracted', 'active') THEN 1 ELSE 0 END) AS active
                    FROM broker_ops_deal
                    """
                ),
                "commissions": _db_one(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN record_type = 'earned' THEN amount ELSE 0 END), 0) AS earned_total,
                      COALESCE(SUM(CASE WHEN record_type = 'paid' THEN amount ELSE 0 END), 0) AS paid_total,
                      COALESCE(SUM(CASE WHEN record_type = 'pending' THEN amount ELSE 0 END), 0) AS pending_total
                    FROM broker_ops_commissionrecord
                    """
                ),
            }
            return _json_resource(uri_str, payload)

        if uri_str == "broker://business/revenue/streams":
            rows = _db_rows(
                """
                SELECT slug, name, owner_agent, category, status, monthly_target_usd,
                       mrr_usd, cash_today_usd, cash_30d_usd, pending_pipeline_usd,
                       last_event_at, notes
                FROM business_os_revenuestream
                ORDER BY name ASC
                """
            )
            return _json_resource(uri_str, {"count": len(rows), "streams": rows})

        if uri_str == "broker://business/events/recent":
            rows = _db_rows(
                """
                SELECT created_at, event_type, source, entity_type, entity_id, status,
                       priority, revenue_impact_usd, requires_approval, owner_agent, summary
                FROM business_os_businessevent
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
            return _json_resource(uri_str, {"count": len(rows), "events": rows})

        if uri_str == "broker://business/alerts/open":
            rows = _db_rows(
                """
                SELECT created_at, severity, state, source, summary, detail, entity_type,
                       entity_id, requires_approval
                FROM business_os_businessalert
                WHERE state = 'open'
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
            return _json_resource(uri_str, {"count": len(rows), "alerts": rows})

        if uri_str == "broker://matches/pending":
            rows = _db_rows(
                """
                SELECT
                  m.id,
                  m.match_score,
                  m.status,
                  m.created_at,
                  o.title AS offer_title,
                  l.name AS lead_name,
                  l.company AS lead_company
                FROM broker_ops_brokermatch m
                LEFT JOIN broker_ops_offerlisting o ON o.id = m.offer_id
                LEFT JOIN broker_ops_leadprofile l ON l.id = m.lead_id
                WHERE m.status IN ('pending', 'approved')
                ORDER BY m.match_score DESC, m.created_at DESC
                LIMIT 20
                """
            )
            return _json_resource(uri_str, {"count": len(rows), "matches": rows})

        if uri_str == "broker://deals/active":
            rows = _db_rows(
                """
                SELECT
                  d.id,
                  d.stage,
                  d.deal_value,
                  d.commission_due,
                  d.created_at,
                  o.title AS offer_title,
                  l.name AS lead_name
                FROM broker_ops_deal d
                LEFT JOIN broker_ops_offerlisting o ON o.id = d.offer_id
                LEFT JOIN broker_ops_leadprofile l ON l.id = d.lead_id
                ORDER BY d.created_at DESC
                LIMIT 20
                """
            )
            return _json_resource(uri_str, {"count": len(rows), "deals": rows})

        if uri_str.startswith("broker://match/"):
            match_id = uri_str.rsplit("/", 1)[-1]
            row = _db_one(
                """
                SELECT
                  m.id, m.match_score, m.match_reasoning, m.status, m.outreach_sent_at,
                  m.outreach_channel, m.outreach_template, m.created_at,
                  o.title AS offer_title, o.category AS offer_category, o.seller_name,
                  l.name AS lead_name, l.company AS lead_company, l.email AS lead_email,
                  l.intent AS lead_intent
                FROM broker_ops_brokermatch m
                LEFT JOIN broker_ops_offerlisting o ON o.id = m.offer_id
                LEFT JOIN broker_ops_leadprofile l ON l.id = m.lead_id
                WHERE m.id = ?
                """,
                (match_id,),
            )
            if not row:
                return _resource_error(uri_str, f"Match {match_id} not found")
            return _json_resource(uri_str, row)

        if uri_str.startswith("broker://deal/"):
            deal_id = uri_str.rsplit("/", 1)[-1]
            row = _db_one(
                """
                SELECT
                  d.id, d.stage, d.deal_value, d.commission_pct, d.commission_due,
                  d.stripe_invoice_id, d.started_at, d.closed_at, d.created_at,
                  o.title AS offer_title, o.seller_name,
                  l.name AS lead_name, l.email AS lead_email
                FROM broker_ops_deal d
                LEFT JOIN broker_ops_offerlisting o ON o.id = d.offer_id
                LEFT JOIN broker_ops_leadprofile l ON l.id = d.lead_id
                WHERE d.id = ?
                """,
                (deal_id,),
            )
            if not row:
                return _resource_error(uri_str, f"Deal {deal_id} not found")
            row["commissions"] = _db_rows(
                """
                SELECT record_type, amount, currency, description, stripe_invoice_id, created_at
                FROM broker_ops_commissionrecord
                WHERE deal_id = ?
                ORDER BY created_at DESC
                """,
                (deal_id,),
            )
            return _json_resource(uri_str, row)
    except Exception as exc:
        log.exception("Resource read failed")
        return _resource_error(uri_str, str(exc))

    return _resource_error(uri_str, f"Unknown resource: {uri_str}")


@server.call_tool()
async def handle_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        log.exception(f"Tool {name} failed")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def _dispatch(name: str, args: dict) -> dict:
    handlers = {
        "scout_hacker_news":       _scout_hn,
        "scout_product_hunt_rss":  _scout_ph_rss,
        "scout_indiehackers_rss":  _scout_ih_rss,
        "scout_github_trending":   _scout_github,
        "scout_devto":             _scout_devto,
        "web_scrape_public":       _web_scrape,
        "broker_ingest_offer":     _broker_ingest_offer,
        "broker_ingest_lead":      _broker_ingest_lead,
        "broker_run_matching":     _broker_run_matching,
        "broker_approve_match":    _broker_approve_match,
        "broker_close_deal":       _broker_close_deal,
        "broker_status":           _broker_status,
        "broker_commission_report": _broker_commission_report,
        "email_send":              _email_send,
        "email_warmup_status":     _email_warmup_status,
        "email_draft_outreach":    _email_draft_outreach,
        "generate_finder_agreement": _gen_agreement,
        "scheduler_add_job":       _sched_add,
        "scheduler_list_jobs":     _sched_list,
        "scheduler_remove_job":    _sched_remove,
        "scheduler_install_crontab": _sched_install_cron,
        "broker_kpi_snapshot":     _broker_kpi,
        "bulk_scout_all_sources":  _bulk_scout,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    return await handler(args)


# ---------------------------------------------------------------------------
# SCOUTS: public web scraping (no API keys needed)
# ---------------------------------------------------------------------------

async def _scout_hn(args: dict) -> dict:
    query = args.get("query", "saas ai automation")
    limit = min(args.get("limit", 30), 100)
    url = "https://hn.algolia.com/api/v1/search"
    params = {"query": query, "tags": "show_hn", "hitsPerPage": limit}

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        hits = r.json().get("hits", [])

    results = []
    for h in hits:
        title = h.get("title", "")
        text = h.get("story_text", "") or ""
        if not _is_relevant(f"{title} {text}"):
            continue
        results.append({
            "title": title,
            "url": h.get("url", ""),
            "author": h.get("author", ""),
            "points": h.get("points", 0),
            "created": h.get("created_at", ""),
            "category": _guess_category(f"{title} {text}"),
            "source": "hacker_news",
        })

    return {"source": "hacker_news", "query": query, "count": len(results), "results": results}


async def _scout_ph_rss(args: dict) -> dict:
    limit = min(args.get("limit", 20), 50)
    url = "https://www.producthunt.com/feed"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "EverLightBot/1.0 (RSS Reader)"})

    results = []
    try:
        root = ET.fromstring(r.text)
        items = root.findall(".//item")[:limit]
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            if not _is_relevant(f"{title} {desc}"):
                continue
            results.append({
                "title": title,
                "url": link,
                "description": desc[:300],
                "category": _guess_category(f"{title} {desc}"),
                "source": "product_hunt_rss",
            })
    except ET.ParseError:
        return {"source": "product_hunt_rss", "error": "RSS parse failed", "count": 0, "results": []}

    return {"source": "product_hunt_rss", "count": len(results), "results": results}


async def _scout_ih_rss(args: dict) -> dict:
    limit = min(args.get("limit", 20), 50)
    url = "https://www.indiehackers.com/feed.xml"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "EverLightBot/1.0"})

    results = []
    try:
        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        for item in items[:limit]:
            title = (item.findtext("title") or item.findtext("atom:title", ns) or "").strip()
            link_el = item.find("link") or item.find("atom:link", ns)
            link = ""
            if link_el is not None:
                link = link_el.text or link_el.get("href", "")
            desc_el = item.find("description") or item.find("atom:summary", ns)
            desc = (desc_el.text or "") if desc_el is not None else ""
            if not _is_relevant(f"{title} {desc}"):
                continue
            results.append({
                "title": title,
                "url": link,
                "description": desc[:300],
                "category": _guess_category(f"{title} {desc}"),
                "source": "indiehackers",
            })
    except ET.ParseError:
        return {"source": "indiehackers", "error": "RSS parse failed", "count": 0, "results": []}

    return {"source": "indiehackers", "count": len(results), "results": results}


async def _scout_github(args: dict) -> dict:
    lang = args.get("language", "")
    since = args.get("since", "weekly")

    # Use GitHub search API (public, no auth, 10 req/min)
    # Find recently created repos with stars, filtered by topic
    date_map = {"daily": 1, "weekly": 7, "monthly": 30}
    days = date_map.get(since, 7)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    query = f"stars:>5 created:>{cutoff}"
    if lang:
        query += f" language:{lang}"
    # Add SaaS/AI relevance terms
    query += " (saas OR ai OR automation OR api OR devtools OR agent)"

    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": 30}

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "EverLightBot/1.0"
        })

    results = []
    try:
        items = r.json().get("items", [])
        for repo in items:
            name = repo.get("full_name", "")
            desc = repo.get("description", "") or ""
            if not _is_relevant(f"{name} {desc}"):
                continue
            results.append({
                "repo": name,
                "url": repo.get("html_url", ""),
                "description": desc[:200],
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language", ""),
                "topics": repo.get("topics", [])[:5],
                "category": _guess_category(f"{name} {desc}"),
                "source": "github_trending",
            })
    except Exception:
        return {"source": "github_trending", "error": "API parse failed", "count": 0, "results": []}

    return {"source": "github_trending", "language": lang, "since": since, "count": len(results), "results": results}


async def _scout_devto(args: dict) -> dict:
    tag = args.get("tag", "saas")
    limit = min(args.get("limit", 25), 50)

    url = "https://dev.to/api/articles"
    params = {"tag": tag, "per_page": limit, "top": 7}  # top posts from last 7 days

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params, headers={"User-Agent": "EverLightBot/1.0"})

    results = []
    try:
        articles = r.json()
        for a in articles:
            title = a.get("title", "")
            desc = a.get("description", "")
            combined = f"{title} {desc}"
            if not _is_relevant(combined):
                continue
            results.append({
                "title": title,
                "url": a.get("url", ""),
                "author": a.get("user", {}).get("name", ""),
                "reactions": a.get("public_reactions_count", 0),
                "description": desc[:200],
                "tags": a.get("tag_list", []),
                "category": _guess_category(combined),
                "source": "devto",
            })
    except Exception:
        return {"source": "devto", "error": "parse failed", "count": 0, "results": []}

    return {"source": "devto", "tag": tag, "count": len(results), "results": results}


async def _web_scrape(args: dict) -> dict:
    url = args["url"]
    extract_emails = args.get("extract_emails", False)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "EverLightBot/1.0"})

    # Strip HTML tags for plain text
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()[:5000]

    result = {"url": url, "text": text, "status_code": r.status_code}

    if extract_emails:
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)))
        result["emails"] = emails[:20]

    return result


# ---------------------------------------------------------------------------
# DJANGO BROKER OPS API
# ---------------------------------------------------------------------------

async def _django_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{DJANGO_URL}{path}", json=payload)
        return r.json()


async def _django_get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{DJANGO_URL}{path}", params=params)
        return r.json()


async def _broker_ingest_offer(args: dict) -> dict:
    return await _django_post("/broker/api/ingest/offer/", args)


async def _broker_ingest_lead(args: dict) -> dict:
    return await _django_post("/broker/api/ingest/lead/", args)


async def _broker_run_matching(args: dict) -> dict:
    min_score = args.get("min_score", 40.0)
    dry_run = "true" if args.get("dry_run", False) else "false"
    return await _django_get("/broker/api/match/run/", {"min_score": min_score, "dry_run": dry_run})


async def _broker_approve_match(args: dict) -> dict:
    mid = args["match_id"]
    return await _django_post(f"/broker/api/match/{mid}/approve/", {
        "deal_value": args["deal_value"],
        "notes": args.get("notes", ""),
    })


async def _broker_close_deal(args: dict) -> dict:
    did = args["deal_id"]
    return await _django_post(f"/broker/api/deal/{did}/close/", {"won": args.get("won", True)})


async def _broker_status(args: dict) -> dict:
    try:
        commissions = await _django_get("/broker/api/commissions/")
    except Exception:
        commissions = {"error": "Django not running"}

    # Also count from filesystem logs
    log_files = sorted(LOG_DIR.glob("match_run_*.json"))
    last_run = None
    if log_files:
        with open(log_files[-1]) as f:
            last_run = json.load(f)

    return {
        "commissions": commissions,
        "last_match_run": last_run.get("timestamp") if last_run else "never",
        "last_match_count": last_run.get("count") if last_run else 0,
        "log_dir": str(LOG_DIR),
    }


async def _broker_commission_report(args: dict) -> dict:
    return await _django_get("/broker/api/commissions/")


async def _broker_kpi(args: dict) -> dict:
    try:
        status = await _django_get("/broker/api/commissions/")
    except Exception:
        status = {}

    kpi_files = sorted(LOG_DIR.glob("kpi_*.json"))
    history = []
    for f in kpi_files[-7:]:
        with open(f) as fh:
            history.append(json.load(fh))

    return {"current": status, "recent_snapshots": history}


# ---------------------------------------------------------------------------
# EMAIL / OUTREACH
# ---------------------------------------------------------------------------

def _init_warmup_db():
    db = sqlite3.connect(str(WARMUP_DB))
    db.execute("""
        CREATE TABLE IF NOT EXISTS sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT,
            status TEXT DEFAULT 'sent'
        )
    """)
    db.commit()
    return db


async def _email_send(args: dict) -> dict:
    if not SMTP_HOST:
        return {"error": "SMTP not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars."}

    # Check warm-up limits
    db = _init_warmup_db()
    today = datetime.now().strftime("%Y-%m-%d")
    count_today = db.execute("SELECT COUNT(*) FROM sends WHERE sent_at LIKE ?", (f"{today}%",)).fetchone()[0]

    # Warm-up schedule: week 1=5/day, week 2=10/day, week 3=15/day, week 4+=20/day
    first_send = db.execute("SELECT MIN(sent_at) FROM sends").fetchone()[0]
    if first_send:
        days_active = (datetime.now() - datetime.fromisoformat(first_send)).days
    else:
        days_active = 0

    if days_active < 7:
        daily_limit = 5
    elif days_active < 14:
        daily_limit = 10
    elif days_active < 21:
        daily_limit = 15
    else:
        daily_limit = 20

    if count_today >= daily_limit:
        db.close()
        return {"error": f"Daily limit reached ({count_today}/{daily_limit}). Domain warm-up in progress (day {days_active})."}

    # Send
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = args["to"]
        msg["Subject"] = args["subject"]
        msg["Reply-To"] = os.environ.get("BROKER_REPLY_TO", "sage@everlightventures.io")
        msg.attach(MIMEText(args["body"], "plain"))
        if args.get("html_body"):
            msg.attach(MIMEText(args["html_body"], "html"))

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)

        db.execute("INSERT INTO sends (sent_at, recipient, subject) VALUES (?,?,?)",
                    (datetime.now().isoformat(), args["to"], args["subject"]))
        db.commit()
        db.close()

        return {"ok": True, "sent_to": args["to"], "sends_today": count_today + 1, "daily_limit": daily_limit}
    except Exception as e:
        db.close()
        return {"error": f"SMTP send failed: {e}"}


async def _email_warmup_status(args: dict) -> dict:
    db = _init_warmup_db()
    today = datetime.now().strftime("%Y-%m-%d")
    count_today = db.execute("SELECT COUNT(*) FROM sends WHERE sent_at LIKE ?", (f"{today}%",)).fetchone()[0]
    total_sent = db.execute("SELECT COUNT(*) FROM sends").fetchone()[0]
    first_send = db.execute("SELECT MIN(sent_at) FROM sends").fetchone()[0]

    days_active = 0
    if first_send:
        days_active = (datetime.now() - datetime.fromisoformat(first_send)).days

    if days_active < 7:
        daily_limit = 5
        phase = "Week 1 (5/day)"
    elif days_active < 14:
        daily_limit = 10
        phase = "Week 2 (10/day)"
    elif days_active < 21:
        daily_limit = 15
        phase = "Week 3 (15/day)"
    else:
        daily_limit = 20
        phase = "Fully warmed (20/day)"

    db.close()
    return {
        "smtp_configured": bool(SMTP_HOST),
        "smtp_host": SMTP_HOST or "NOT SET",
        "from_address": SMTP_FROM,
        "days_active": days_active,
        "warmup_phase": phase,
        "daily_limit": daily_limit,
        "sent_today": count_today,
        "remaining_today": max(0, daily_limit - count_today),
        "total_sent_all_time": total_sent,
    }


OUTREACH_TEMPLATES = {
    "seller_intro": (
        "Hi {recipient_name},\n\n"
        "I came across {product_name} on {source} and it caught my eye. "
        "I work with B2B startups and SMBs who are actively looking for tools like yours.\n\n"
        "Would you be open to a referral arrangement? I bring qualified buyers directly to you - "
        "you only pay a commission on closed deals. No upfront cost, no risk.\n\n"
        "Happy to share more details if you're interested.\n\n"
        "Best,\nEverlight Ventures\neverlightventures.io"
    ),
    "buyer_intro": (
        "Hi {recipient_name},\n\n"
        "I specialize in connecting {company_name} teams with vetted {need} solutions. "
        "{custom_hook}\n\n"
        "I have a few options that may fit your requirements and budget. "
        "Worth a quick 10-minute intro call?\n\n"
        "Best,\nEverlight Ventures\neverlightventures.io"
    ),
    "followup": (
        "Hi {recipient_name},\n\n"
        "Just following up on my note from last week. "
        "I still have some great {need} options that could help {company_name}.\n\n"
        "Let me know if this week works for a quick chat.\n\n"
        "Best,\nEverlight Ventures"
    ),
    "breakup": (
        "Hi {recipient_name},\n\n"
        "I've reached out a couple times about {need} solutions for {company_name}. "
        "I don't want to be a pest, so this will be my last note.\n\n"
        "If timing changes, I'm always happy to help. Just reply to this email.\n\n"
        "All the best,\nEverlight Ventures"
    ),
}


async def _email_draft_outreach(args: dict) -> dict:
    template_key = args["template"]
    template = OUTREACH_TEMPLATES.get(template_key, "")
    if not template:
        return {"error": f"Unknown template: {template_key}"}

    draft = template.format(
        recipient_name=args.get("recipient_name", "there"),
        product_name=args.get("product_name", "your product"),
        company_name=args.get("company_name", "your team"),
        source=args.get("source", "the web"),
        need=args.get("need", "SaaS/AI"),
        custom_hook=args.get("custom_hook", ""),
    )

    return {"template": template_key, "draft": draft, "note": "Review and edit before sending. This is a DRAFT only."}


# ---------------------------------------------------------------------------
# AGREEMENT GENERATOR
# ---------------------------------------------------------------------------

async def _gen_agreement(args: dict) -> dict:
    today = datetime.now().strftime("%B %d, %Y")
    finder = args.get("finder_name", "Everlight Ventures")
    entity = args.get("finder_entity", "Everlight Logistics LLC")
    client = args["client_name"]
    company = args.get("client_company", client)
    pct = args.get("commission_pct", 20.0)
    desc = args["deal_description"]
    terms = args.get("payment_terms", "Net 30 from close date")
    duration = args.get("duration_months", 12)

    agreement = f"""# FINDER FEE AGREEMENT

**Date:** {today}

**Between:**
- **Finder:** {entity} (d/b/a {finder})
- **Client:** {client} ({company})

## 1. SCOPE

Finder agrees to introduce Client to qualified buyers/partners for the following:

> {desc}

## 2. COMPENSATION

Client agrees to pay Finder a fee of **{pct}%** of the gross transaction value
for any deal closed with an introduction made by Finder.

- Payment due: {terms}
- Commission applies to initial transaction and any renewals/expansions
  within {duration} months of the original introduction
- Payment via Stripe invoice or bank transfer

## 3. TERM

This agreement is effective for **{duration} months** from the date above.
Introductions made during this period remain compensable even if the deal
closes after expiration.

## 4. FINDER'S ROLE

Finder's role is LIMITED to introductions only. Finder does NOT:
- Negotiate terms on behalf of either party
- Handle client funds or securities
- Provide investment advice
- Act as a broker-dealer

## 5. NON-CIRCUMVENTION

Client agrees not to circumvent Finder by dealing directly with introduced
parties without Finder's knowledge and commission payment.

## 6. CONFIDENTIALITY

Both parties agree to keep the terms of this agreement confidential.

## 7. GOVERNING LAW

This agreement is governed by the laws of the State of ____________.

## SIGNATURES

**Finder:** {entity}

Signature: ________________________  Date: __________

**Client:** {company}

Signature: ________________________  Date: __________

---
*Generated by Everlight Ventures Broker OS. This is a template - consult
legal counsel before execution for deals involving securities or regulated industries.*
"""

    # Save to file
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', client)[:30]
    filepath = LOG_DIR / f"agreement_{safe_name}_{datetime.now().strftime('%Y%m%d')}.md"
    filepath.write_text(agreement)

    return {"agreement": agreement, "saved_to": str(filepath)}


# ---------------------------------------------------------------------------
# SCHEDULER
# ---------------------------------------------------------------------------

def _init_sched_db():
    db = sqlite3.connect(str(CRON_DB))
    db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            name TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            schedule TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    return db


async def _sched_add(args: dict) -> dict:
    db = _init_sched_db()
    db.execute(
        "INSERT OR REPLACE INTO jobs (name, command, schedule, enabled) VALUES (?,?,?,?)",
        (args["job_name"], args["command"], args["schedule"], 1 if args.get("enabled", True) else 0)
    )
    db.commit()
    db.close()
    return {"ok": True, "job": args["job_name"], "schedule": args["schedule"]}


async def _sched_list(args: dict) -> dict:
    db = _init_sched_db()
    jobs = db.execute("SELECT name, command, schedule, enabled, created_at FROM jobs").fetchall()
    db.close()
    return {"jobs": [
        {"name": j[0], "command": j[1], "schedule": j[2], "enabled": bool(j[3]), "created_at": j[4]}
        for j in jobs
    ]}


async def _sched_remove(args: dict) -> dict:
    db = _init_sched_db()
    db.execute("DELETE FROM jobs WHERE name=?", (args["job_name"],))
    db.commit()
    db.close()
    return {"ok": True, "removed": args["job_name"]}


async def _sched_install_cron(args: dict) -> dict:
    db = _init_sched_db()
    jobs = db.execute("SELECT name, command, schedule FROM jobs WHERE enabled=1").fetchall()
    db.close()

    if not jobs:
        return {"error": "No enabled jobs to install"}

    lines = ["# Broker OS Crontab - Auto-generated by MCP server"]
    for name, cmd, sched in jobs:
        lines.append(f"{sched} {cmd}  # {name}")
    lines.append("")

    cron_content = "\n".join(lines)

    # Write to temp file and install
    cron_file = LOG_DIR / "broker_crontab"
    cron_file.write_text(cron_content)

    import subprocess
    try:
        # Merge with existing crontab
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing_lines = existing.stdout.strip().split("\n") if existing.returncode == 0 else []
        # Remove old broker lines
        cleaned = [l for l in existing_lines if "# Broker OS" not in l and "broker_run" not in l and "broker_ingest" not in l]
        final = "\n".join(cleaned + lines)
        subprocess.run(["crontab", "-"], input=final, text=True, check=True)
        return {"ok": True, "jobs_installed": len(jobs), "crontab_file": str(cron_file), "content": cron_content}
    except Exception as e:
        return {"error": f"Crontab install failed: {e}", "manual_file": str(cron_file), "content": cron_content}


# ---------------------------------------------------------------------------
# BULK SCOUT
# ---------------------------------------------------------------------------

async def _bulk_scout(args: dict) -> dict:
    limit = args.get("limit_per_source", 15)
    auto_ingest = args.get("auto_ingest", False)

    results = {}
    total = 0

    scouts = [
        ("hacker_news", _scout_hn, {"query": "saas ai automation startup", "limit": limit}),
        ("devto_saas", _scout_devto, {"tag": "saas", "limit": limit}),
        ("devto_ai", _scout_devto, {"tag": "ai", "limit": limit}),
        ("github_trending", _scout_github, {"since": "weekly", "limit": limit}),
        ("indiehackers", _scout_ih_rss, {"limit": limit}),
        ("product_hunt", _scout_ph_rss, {"limit": limit}),
    ]

    for name, handler, scout_args in scouts:
        try:
            r = await handler(scout_args)
            results[name] = r
            total += r.get("count", 0)
        except Exception as e:
            results[name] = {"error": str(e), "count": 0}

    ingested = 0
    if auto_ingest:
        for source_name, source_data in results.items():
            for item in source_data.get("results", []):
                try:
                    payload = {
                        "seller_name": item.get("author", item.get("repo", "Unknown")),
                        "seller_email": "",
                        "title": item.get("title", item.get("repo", "")),
                        "description": item.get("description", item.get("title", "")),
                        "category": item.get("category", "ai_saas"),
                        "keywords": [],
                        "source": item.get("source", source_name),
                        "source_url": item.get("url", ""),
                        "commission_pct": 20.0,
                        "status": "draft",
                    }
                    await _django_post("/broker/api/ingest/offer/", payload)
                    ingested += 1
                except Exception:
                    pass

    # Save run log
    log_path = LOG_DIR / f"bulk_scout_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json"
    with open(log_path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "total_found": total, "ingested": ingested, "sources": list(results.keys())}, f, indent=2)

    return {"total_found": total, "ingested": ingested, "by_source": {k: v.get("count", 0) for k, v in results.items()}, "log": str(log_path)}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

async def main():
    from mcp.server.stdio import stdio_server

    log.info("Broker OS MCP server starting...")
    log.info(f"Django API: {DJANGO_URL}")
    log.info(f"Log dir: {LOG_DIR}")
    log.info(f"SMTP: {'configured' if SMTP_HOST else 'NOT configured'}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
