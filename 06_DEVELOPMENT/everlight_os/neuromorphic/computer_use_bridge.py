"""
Computer Use Bridge -- autonomous web actions for the broker pipeline.

Sends tasks to the Computer Use container (Xvfb + Firefox + Claude API)
for autonomous web research: property lookups, form fills, prospect research.

The container runs on Oracle at port 8501 (when exposed).

Uses: Claude Computer Use API (needs ANTHROPIC_API_KEY in container env).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

COMPUTER_USE_URL = os.environ.get("COMPUTER_USE_URL", "http://localhost:8501")


def send_task(task: str, context: dict | None = None, timeout: int = 120) -> dict:
    """Send a task to the Computer Use agent.

    Args:
        task: Natural language description of what to do
        context: Optional context (URLs, search terms, etc.)
        timeout: Max seconds to wait

    Returns:
        Dict with result, screenshots, extracted_data
    """
    payload = {
        "task": task,
        "context": context or {},
    }

    try:
        req = urllib.request.Request(
            f"{COMPUTER_USE_URL}/api/task",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f"Computer Use task failed: {e}")
        return {"error": str(e), "status": "failed"}


def research_property(address: str, county: str = "") -> dict:
    """Look up property details using Computer Use agent.

    The agent will:
    1. Navigate to the county assessor website
    2. Search for the property address
    3. Extract: owner name, assessed value, tax info, sale history
    """
    task = (
        f"Research this property: {address}"
        + (f" in {county} county" if county else "")
        + ". Find the county assessor website, look up the property, "
        + "and extract: owner name, assessed value, tax status, last sale date and price."
    )
    return send_task(task, context={"type": "property_research", "address": address})


def research_prospect(company_name: str, website: str = "") -> dict:
    """Research a prospect company using Computer Use agent.

    The agent will:
    1. Visit the company website
    2. Find key contacts, company size, tech stack
    3. Look for pain points and AI readiness signals
    """
    task = (
        f"Research this company: {company_name}"
        + (f" (website: {website})" if website else "")
        + ". Find: key decision makers, company size, what technology they use, "
        + "any pain points related to automation or AI. Check LinkedIn if available."
    )
    return send_task(task, context={"type": "prospect_research", "company": company_name})


def fill_form(url: str, fields: dict) -> dict:
    """Fill a web form using Computer Use agent.

    Args:
        url: The form URL
        fields: Dict of field_name -> value to fill
    """
    field_desc = ", ".join(f"{k}: {v}" for k, v in fields.items())
    task = f"Go to {url} and fill the form with these values: {field_desc}. Submit the form."
    return send_task(task, context={"type": "form_fill", "url": url, "fields": fields})


def get_status() -> dict:
    """Check if Computer Use agent is available."""
    try:
        req = urllib.request.Request(f"{COMPUTER_USE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"available": True, "status": json.loads(resp.read())}
    except Exception:
        return {"available": False, "url": COMPUTER_USE_URL}
