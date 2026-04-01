"""
Blinko knowledge-base integration -- fetch recent trading notes/rules.

Blinko runs at http://localhost:1111 on Oracle Cloud.
API: POST /api/v1/note/list  with {"size": N} and Bearer auth.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from django.core.cache import cache

logger = logging.getLogger(__name__)

BLINKO_BASE_URL = "http://localhost:1111"
BLINKO_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoic3VwZXJhZG1pbiIsIm5hbWUiOiJhZG1pbiIsInN1YiI6IjEiLCJleHAiOjQ5MjczNjgzNzIsImlhdCI6MTc3Mzc2ODM3Mn0."
    "mnLSmtQpjcu7xjV0nLYcVRgrkwp4Jmlw-sQL0BvyiC0"
)

CACHE_KEY = "blinko_notes"
CACHE_TIMEOUT = 120  # 2 minutes


def fetch_notes(size: int = 5) -> list[dict]:
    """Fetch recent notes from Blinko. Returns list of note dicts.

    Each note has: content, createdAt, updatedAt, tags (if present).
    Returns empty list on any failure (never crashes the dashboard).
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        import urllib.request
        import urllib.error

        url = f"{BLINKO_BASE_URL}/api/v1/note/list"
        payload = json.dumps({"size": size}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {BLINKO_TOKEN}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Blinko returns notes in various formats; normalize
        notes = []
        items = data if isinstance(data, list) else data.get("items", data.get("notes", []))
        for item in items[:size]:
            if not isinstance(item, dict):
                continue
            notes.append({
                "content": item.get("content", ""),
                "created": item.get("createdAt", item.get("created_at", "")),
                "updated": item.get("updatedAt", item.get("updated_at", "")),
                "tags": item.get("tags", []),
            })

        cache.set(CACHE_KEY, notes, timeout=CACHE_TIMEOUT)
        return notes

    except Exception as e:
        logger.debug("Blinko fetch failed: %s", e)
        cache.set(CACHE_KEY, [], timeout=30)  # short cache on failure
        return []
