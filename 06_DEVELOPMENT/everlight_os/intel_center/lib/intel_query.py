"""
intel_query.py -- Python facade over the Everlight Intel Center resource catalog.

Per HARD LAW memory `feedback_tool_search_first_before_paid_api.md` (2026-05-13):
agents MUST query this layer before reaching for a paid API or LLM call when a
free repo / tool can solve the task.

Usage:
    from intel_query import search, search_by_capability, list_categories, get_resource

    # Free-form text search
    hits = search("image generation", limit=5)

    # Capability-based pre-flight check
    hits = search_by_capability("generate slide deck", limit=3)

    # Browse
    cats = list_categories()
    res = get_resource("EIC-0001")

Surface 2: every result has a `dashboard_url` field for the resource's actual
endpoint or repo URL, so an agent can hand-off directly.

Surface 3: same logic is exposed via HTTP at /intel/* through the HTTP bridge
on :2701 (server-less, no new service needed -- bridge auto-picks up).
"""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

DB = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/database/everlight_resources.sqlite")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


@lru_cache(maxsize=1)
def list_categories() -> list[dict]:
    """Return all categories with row counts."""
    with _conn() as c:
        rows = c.execute(
            "SELECT category, COUNT(*) AS n FROM resources GROUP BY category ORDER BY n DESC"
        ).fetchall()
    return [{"category": r["category"], "count": r["n"]} for r in rows]


def search(query: str, limit: int = 5, category: str | None = None) -> list[dict]:
    """Token-OR search across name + purpose + use_case + tags + raw_text.

    Splits the query into words (>=3 chars), then ranks resources by how many
    distinct words match. Matches a resource if ANY token appears in any
    indexed column.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    tokens = [t for t in re.findall(r"[a-z0-9]{3,}", q)
              if t not in {"the", "and", "for", "with", "need", "want", "use", "have"}]
    if not tokens:
        tokens = [q]

    # Build a multi-LIKE OR clause across columns, accumulating per-row match count
    cols = ("name", "purpose", "use_case", "tags", "raw_text", "notes")
    score_terms = []
    score_params: list[Any] = []
    for tok in tokens:
        pat = f"%{tok}%"
        per_token_or = " OR ".join(f"LOWER({c}) LIKE ?" for c in cols)
        score_terms.append(f"(CASE WHEN ({per_token_or}) THEN 1 ELSE 0 END)")
        score_params.extend([pat] * len(cols))
    score_expr = " + ".join(score_terms)

    # Score expression appears in both SELECT and WHERE; same params used twice
    where_extra = ""
    extra_params: list[Any] = []
    if category:
        where_extra = " AND category = ?"
        extra_params.append(category)

    sql = (f"SELECT *, ({score_expr}) AS _score FROM resources "
           f"WHERE ({score_expr}) > 0{where_extra} "
           "ORDER BY _score DESC, "
           "  CASE verified_status WHEN 'checked' THEN 0 ELSE 1 END, "
           "  CAST(COALESCE(NULLIF(priority_score, ''), '0') AS INTEGER) DESC "
           "LIMIT ?")
    final_params = score_params + score_params + extra_params + [limit]

    with _conn() as c:
        rows = c.execute(sql, final_params).fetchall()
    return [_row_to_dict(r) for r in rows]


# Map of capability keywords -> canonical category hints. The keywords agents
# might pass in their task summary. Used to narrow search to the right cat.
CAPABILITY_HINTS = {
    "image": "Content Creation",
    "img": "Content Creation",
    "photo": "Content Creation",
    "slide": "Content Creation",
    "deck": "Content Creation",
    "presentation": "Content Creation",
    "video": "Content Creation",
    "voice": "Content Creation",
    "audio": "Content Creation",
    "research": "Decision Intelligence",
    "paper": "Decision Intelligence",
    "academic": "Decision Intelligence",
    "rss": "News & Journalism",
    "feed": "News & Journalism",
    "news": "News & Journalism",
    "skip trace": "OSINT & Investigation",
    "skip-trace": "OSINT & Investigation",
    "owner": "OSINT & Investigation",
    "phone": "OSINT & Investigation",
    "people": "OSINT & Investigation",
    "trade": "Trading & Finance",
    "trading": "Trading & Finance",
    "market": "Trading & Finance",
    "stock": "Trading & Finance",
    "crypto": "Trading & Finance",
    "brain": "Space & Science",
    "neuron": "Space & Science",
    "biology": "Health & Environment",
    "weather": "Weather & Disaster Intel",
    "disaster": "Weather & Disaster Intel",
    "map": "Maps & Geospatial",
    "geo": "Maps & Geospatial",
    "agent": "AI & Automation",
    "llm": "AI & Automation",
    "api": "APIs & Developer Tools",
    "ecommerce": "eCommerce & Product Research",
    "shop": "eCommerce & Product Research",
    "real estate": "Real Estate & Property",
    "property": "Real Estate & Property",
    "legal": "Legal & Compliance",
    "compliance": "Legal & Compliance",
}


def search_by_capability(task_summary: str, limit: int = 5) -> list[dict]:
    """The MAIN entry point per the doctrine.

    Given a free-text task summary ("I need to generate an image of X" or
    "find owner phone for parcel Y"), return up to `limit` resources most
    likely to solve it without any paid API call.

    Heuristic:
      1. Scan the task for capability keywords; if any match, narrow by that
         category.
      2. Fallback: free-form search over all categories.
    """
    summary = (task_summary or "").lower()
    matched_cat = None
    for kw, cat in CAPABILITY_HINTS.items():
        if kw in summary:
            matched_cat = cat
            break

    # Extract content words for the actual search
    content_words = [w for w in re.findall(r"[A-Za-z]{3,}", summary)
                     if w not in {"the", "and", "for", "with", "need", "want", "use", "have"}]
    query_text = " ".join(content_words[:8]) if content_words else summary

    if matched_cat:
        results = search(query_text, limit=limit, category=matched_cat)
        if results:
            return results
    # Fallback: cross-category
    return search(query_text, limit=limit)


def get_resource(resource_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
    return _row_to_dict(row) if row else None


# ── HTTP bridge integration ─────────────────────────────────────────────────
# The MCP HTTP bridge at 06_DEVELOPMENT/mcp_servers/http_bridge.py auto-loads
# any module that exposes a `_dispatch(name, args)` function. We expose ours so
# the bridge surfaces /tool/intel/{search,search_by_capability,list_categories}.

def _dispatch(name: str, args: dict) -> dict:
    """Dispatcher for HTTP bridge auto-pickup."""
    args = args or {}
    if name == "intel_search":
        return {"results": search(
            query=args.get("query", ""),
            limit=int(args.get("limit", 5) or 5),
            category=args.get("category"),
        )}
    if name == "intel_search_by_capability":
        return {"results": search_by_capability(
            task_summary=args.get("task", "") or args.get("summary", ""),
            limit=int(args.get("limit", 5) or 5),
        )}
    if name == "intel_list_categories":
        return {"categories": list_categories()}
    if name == "intel_get":
        return {"resource": get_resource(args.get("id", ""))}
    return {"error": "unknown_tool", "tool": name, "available": [
        "intel_search", "intel_search_by_capability", "intel_list_categories", "intel_get"]}


TOOLS = [
    {"name": "intel_search", "description": "Free-form search across the 745 Intel Center resources."},
    {"name": "intel_search_by_capability", "description": "Pre-flight: given a task summary, find free resources that solve it (tool-search-first doctrine)."},
    {"name": "intel_list_categories", "description": "List all categories with row counts."},
    {"name": "intel_get", "description": "Get a single resource by id (e.g. EIC-0001)."},
]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(f"# Search for: {q!r}")
        for r in search_by_capability(q, limit=5):
            print(f"  - {r['name']}  ({r['category']})  cost={r['cost_level']}")
            print(f"    use_case: {(r.get('use_case') or '')[:140]}")
    else:
        cats = list_categories()
        print(f"# {sum(c['count'] for c in cats)} resources / {len(cats)} categories")
        for c in cats:
            print(f"  {c['count']:>4}  {c['category']}")
