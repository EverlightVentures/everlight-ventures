"""
SaaS Factory — Spec pack writer.
Generates all 9 spec documents for Phase 0.
Each function is independently callable for retries.
"""

from pathlib import Path
from typing import Dict
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text

_SYSTEM = (
    "You are an experienced SaaS product manager writing formal specification documents. "
    "Use clear markdown with headers. Be specific and actionable. No filler."
)


def _ctx(scope: dict, stack: dict) -> str:
    """Build shared context block injected into every spec prompt."""
    return f"""Product: {scope.get('product_name', 'Unknown')}
One-liner: {scope.get('one_liner', '')}
Problem: {scope.get('problem', '')}
Solution: {scope.get('solution', '')}
ICP: {scope.get('icp', '')}
Revenue model: {scope.get('revenue_model', '')}
MVP scope: {scope.get('mvp_scope', '')}
Stack: {stack.get('summary', 'TBD')}"""


def _parse_json(raw: str) -> str:
    """Strip code fences from AI response."""
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean = "\n".join(lines)
    return clean


def write_prd(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "01_PRD.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a Product Requirements Document (PRD) with:
# {scope.get('product_name', 'Product')} — PRD

## Problem Statement
## Product Vision
## Goals & Success Metrics (3-5 measurable KPIs)
## Non-Goals (what this product explicitly does NOT do)
## User Personas (2-3 personas with name, role, pain point, goal)
## Core Feature List (MVP phase — numbered, prioritized)
## Out of Scope for MVP
## Open Questions

Be specific. Include measurable success metrics."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.5, max_tokens=2500)))
    return str(path)


def write_user_stories(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "02_USER_STORIES.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write user stories in standard format: "As a [persona], I want [goal], so that [benefit]."

# User Stories

For each major feature area, write 3-5 user stories.
Include: Story ID, Priority (P0/P1/P2), Acceptance Criteria (3-5 bullet points per story).
Group by feature area with ## headers.
Cover: onboarding, core workflow, billing, settings, and any domain-specific flows."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.5, max_tokens=2500)))
    return str(path)


def write_acceptance_criteria(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "03_ACCEPTANCE_CRITERIA.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a formal Acceptance Criteria document.

# Acceptance Criteria

For each P0 user story, provide detailed Given/When/Then criteria.
Also include:
## Definition of Done (project-wide checklist)
## QA Checklist (what must pass before each feature ships)
## Edge Cases to Test"""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.4, max_tokens=2000)))
    return str(path)


def write_nonfunctional_requirements(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "04_NONFUNCTIONAL_REQUIREMENTS.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a Non-Functional Requirements document covering:

# Non-Functional Requirements

## Performance (response time targets, throughput)
## Scalability (user growth targets, data volume)
## Security (auth, data encryption, OWASP top 10 applicability)
## Availability & Reliability (uptime SLA, error budget)
## Compliance (GDPR, SOC2, CCPA — which apply and why)
## Accessibility (WCAG level target)
## Observability (logging, alerting, tracing requirements)

Be specific with numbers where possible."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.4, max_tokens=2000)))
    return str(path)


def write_data_model(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "05_DATA_MODEL.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Design the database schema.

# Data Model

For each entity:
- Table name
- All columns with types, constraints, indexes
- Relationships (FK, one-to-many, many-to-many)
- Notes on soft deletes, timestamps, multi-tenancy

Use markdown tables for columns. Include an Entity Relationship summary.
Cover all entities needed for the MVP scope."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.4, max_tokens=2500)))
    return str(path)


def write_api_spec(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "06_API_SPEC.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write an API specification document.

# API Specification

## Auth Strategy (JWT, session cookies, API keys — which and why)
## Base URL convention

For each endpoint group:
| Method | Path | Description | Auth required | Request body | Response |

Cover: auth flows, core resource CRUD, webhooks (if any), error response format.
Include example request/response JSON snippets for the 3 most important endpoints."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.4, max_tokens=2500)))
    return str(path)


def write_ui_map(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "07_UI_MAP.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a UI Map / Information Architecture document.

# UI Map

## Page Inventory (every page/route in the MVP)
For each page: URL path, purpose, key components, access level (public/auth)

## Navigation Structure (sidebar, navbar — what links to what)
## Key User Flows (step-by-step, e.g. Signup > Onboarding > First Value Moment)
## Component Inventory (list reusable components needed)
## Empty States (what does each page show with no data?)
## Responsive Strategy (mobile-first or desktop-first, key breakpoints)"""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.5, max_tokens=2000)))
    return str(path)


def write_risk_register(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "08_RISK_REGISTER.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a Risk Register.

# Risk Register

Use a markdown table with columns:
| ID | Risk | Category | Likelihood (H/M/L) | Impact (H/M/L) | Mitigation | Owner |

Categories: Technical, Market, Legal/Compliance, Operational, Financial.
Include 10-15 risks covering: build risks, churn risk, regulatory, competitor, cost overrun, security breach.
After the table, write a ## Risk Summary with the top 3 highest-priority risks and action plan."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.4, max_tokens=1800)))
    return str(path)


def write_roadmap(scope: dict, stack: dict, spec_dir: Path) -> str:
    path = spec_dir / "09_ROADMAP.md"
    if path.exists():
        return str(path)
    ctx = _ctx(scope, stack)
    prompt = f"""{ctx}

Write a product roadmap.

# Product Roadmap

## Phase 0 — Spec & Design (current)
## Phase 1 — MVP Build (target: 4-8 weeks)
  - Week-by-week milestones
  - Definition of "shippable MVP"
## Phase 2 — Launch (target: 2 weeks post-build)
  - Launch checklist items
  - First 10 users acquisition plan
## Phase 3 — Growth (3-6 months post-launch)
  - Feature additions based on user feedback
  - Revenue targets and expansion features
## Phase 4 — Scale (6-12 months)
  - Team hiring plan
  - Infrastructure scaling milestones

Include a success metric for each phase."""
    write_text(path, _parse_json(call_openai(prompt, system=_SYSTEM, temperature=0.5, max_tokens=2000)))
    return str(path)


def write_all_spec_docs(scope: dict, stack: dict, project_dir: Path) -> Dict[str, str]:
    """
    Generate all 9 spec documents.
    Returns dict of {doc_name: file_path}.
    Idempotent — skips any doc that already exists.
    """
    spec_dir = project_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)

    return {
        "01_PRD": write_prd(scope, stack, spec_dir),
        "02_USER_STORIES": write_user_stories(scope, stack, spec_dir),
        "03_ACCEPTANCE_CRITERIA": write_acceptance_criteria(scope, stack, spec_dir),
        "04_NONFUNCTIONAL_REQUIREMENTS": write_nonfunctional_requirements(scope, stack, spec_dir),
        "05_DATA_MODEL": write_data_model(scope, stack, spec_dir),
        "06_API_SPEC": write_api_spec(scope, stack, spec_dir),
        "07_UI_MAP": write_ui_map(scope, stack, spec_dir),
        "08_RISK_REGISTER": write_risk_register(scope, stack, spec_dir),
        "09_ROADMAP": write_roadmap(scope, stack, spec_dir),
    }
