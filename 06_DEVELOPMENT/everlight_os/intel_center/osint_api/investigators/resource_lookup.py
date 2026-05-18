"""
resource_lookup -- surface relevant 745-catalog resources for a target.

This investigator doesn't HTTP-call anything new. It queries the local
Intel Center resource database for sources that match the target's kind +
likely topic (state, address vs person vs company), and surfaces them as
"Additional research sources" in the OSINT report.

This is how the 745 catalogued resources become USEFUL inside the live
investigation flow -- not just static directory entries.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from ._common import now_ms

NAME = "Catalogued Sources"
DOMAINS: list[str] = []  # zero HTTP -- this is a local lookup
WHEN = ["*"]

DB = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/database/everlight_resources.sqlite")
LIVE_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/live_log.sqlite")


def _live_active_set() -> set[str]:
    if not LIVE_LOG.exists():
        return set()
    con = sqlite3.connect(LIVE_LOG)
    try:
        rows = con.execute(
            "SELECT domain FROM live_pulls WHERE last_status_code BETWEEN 200 AND 399"
        ).fetchall()
        return {r[0].lower() for r in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        con.close()


# Map target kind -> categories most useful for that kind
KIND_TO_CATEGORIES = {
    "person":  ["OSINT & Investigation", "Maps & Geospatial",
                 "Education & Training", "Decision Intelligence"],
    "company": ["OSINT & Investigation", "Trading & Finance",
                 "Legal & Compliance", "News & Journalism",
                 "Decision Intelligence", "Economics & Markets"],
    "domain":  ["OSINT & Investigation", "Cybersecurity",
                 "APIs & Developer Tools", "AI & Automation"],
    "address": ["Maps & Geospatial", "Real Estate & Property",
                 "Weather & Disaster Intel", "Legal & Compliance"],
    "email":   ["OSINT & Investigation", "Cybersecurity"],
    "phone":   ["OSINT & Investigation"],
    "*":       ["OSINT & Investigation", "Decision Intelligence",
                 "News & Journalism"],
}


def _detect_kind(target: str) -> str:
    from ._common import detect_kind
    try:
        return detect_kind(target)
    except Exception:
        return "*"


async def run(target: str, http) -> dict:
    """No HTTP. Pure local lookup against the 745-catalog. Always fast (<50ms)."""
    t0 = now_ms()
    findings = []
    raw = {}

    kind = _detect_kind(target)
    cats = KIND_TO_CATEGORIES.get(kind, KIND_TO_CATEGORIES["*"])
    live = _live_active_set()

    if not DB.exists():
        return {"ok": False, "findings": [], "raw": {"error": "resources.sqlite missing"},
                "elapsed_ms": now_ms() - t0, "investigator": NAME,
                "investigator_id": "resource_lookup"}

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = []
    try:
        # Per-category fetch -- ensures all categories represented (not just the first
        # alphabetically eaten by a global LIMIT).
        for cat in cats:
            cat_rows = con.execute(
                """SELECT domain, name, category, purpose, agent_owner, verified_status, url
                   FROM resources WHERE category = ? AND domain != ''
                   ORDER BY domain LIMIT 20""",
                (cat,),
            ).fetchall()
            rows.extend(cat_rows)
    except sqlite3.OperationalError as e:
        con.close()
        return {"ok": False, "findings": [], "raw": {"error": str(e)},
                "elapsed_ms": now_ms() - t0, "investigator": NAME,
                "investigator_id": "resource_lookup"}
    con.close()

    # Group by category, take top 3 live ones per category
    by_cat: dict[str, list] = {}
    for r in rows:
        d = (r["domain"] or "").lower()
        by_cat.setdefault(r["category"], []).append({
            "domain": d, "name": r["name"], "purpose": r["purpose"],
            "agent_owner": r["agent_owner"], "url": r["url"] or f"https://{d}",
            "is_live": d in live,
        })

    # Per-category top 3 live, then INTERLEAVE across categories so the operator
    # sees a balanced research-source mix (not 12 Decision Intelligence in a row).
    per_cat_lists = {}
    for cat in cats:
        items = by_cat.get(cat, [])
        per_cat_lists[cat] = sorted(items, key=lambda x: (not x["is_live"], x["domain"]))[:3]
    # Round-robin interleave
    interleaved = []
    max_per = max((len(v) for v in per_cat_lists.values()), default=0)
    for i in range(max_per):
        for cat in cats:
            if i < len(per_cat_lists.get(cat, [])):
                interleaved.append((cat, per_cat_lists[cat][i]))

    for cat, r in interleaved[:12]:
        live_chip = " · verified live" if r["is_live"] else " · catalogued only"
        findings.append({
            "label": cat,
            "value": f"{r['name']} — {r['purpose']}{live_chip}",
            "url": r["url"],
            "investigator_meta": {
                "agent_owner": r["agent_owner"],
                "is_live": r["is_live"],
                "search_hint": f"Research '{target}' via {cat}",
            },
        })

    raw["total_matched"] = len(rows)
    raw["categories_used"] = cats
    raw["kind"] = kind

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "resource_lookup",
    }
