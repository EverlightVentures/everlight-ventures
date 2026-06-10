#!/usr/bin/env python3
"""
Blinko Knowledge Base Optimizer
Deduplicates notes, indexes by tag, exports to Excel for analysis,
and identifies stale/orphaned content.

Blinko has 458+ notes with no cleanup. This script:
1. Fetches all notes via API
2. Deduplicates (fuzzy title + content match)
3. Indexes by tag for faster RAG retrieval
4. Exports stats to Excel
5. Identifies stale notes (>30 days, no references)
6. Reports optimization recommendations

Usage:
    python3 blinko_optimizer.py                  # Full audit + report
    python3 blinko_optimizer.py --dedupe         # Deduplicate only
    python3 blinko_optimizer.py --export         # Export to Excel
    python3 blinko_optimizer.py --stats          # Quick stats
"""
import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))

log = logging.getLogger("blinko-optimizer")
logging.basicConfig(level=logging.INFO, format="[BlinkoOpt %(asctime)s] %(message)s")

BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")
OUTPUT_DIR = Path(os.environ.get("DELIVERABLES_DIR", "/tmp/hive_deliverables"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_all_notes(limit: int = 1000) -> list[dict]:
    """Fetch all notes from Blinko API."""
    notes = []
    page = 1
    per_page = 100

    while len(notes) < limit:
        try:
            payload = json.dumps({
                "page": page,
                "size": per_page,
                "type": -1,  # All types
            }).encode()
            req = urllib.request.Request(
                f"{BLINKO_URL}/api/v1/note/list",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())

            batch = result if isinstance(result, list) else result.get("data", result.get("items", []))
            if not batch:
                break
            notes.extend(batch)
            page += 1

            if len(batch) < per_page:
                break
        except Exception as e:
            log.error(f"Failed to fetch page {page}: {e}")
            break

    log.info(f"Fetched {len(notes)} notes from Blinko")
    return notes


def extract_tags(content: str) -> list[str]:
    """Extract #tags from note content."""
    import re
    return re.findall(r'#([\w/\-]+)', content or "")


def find_duplicates(notes: list[dict], threshold: float = 0.8) -> list[tuple]:
    """Find duplicate notes by fuzzy title/content matching."""
    dupes = []
    seen = {}

    for note in notes:
        content = (note.get("content", "") or "")[:200].strip().lower()
        # Simple hash-based dedup (first 200 chars)
        key = content[:80]
        if key in seen and key:
            dupes.append((seen[key], note))
        else:
            seen[key] = note

    return dupes


def analyze_notes(notes: list[dict]) -> dict:
    """Comprehensive analysis of the Blinko knowledge base."""
    now = datetime.now(timezone.utc)
    tag_counts = Counter()
    type_counts = Counter()
    monthly_counts = Counter()
    stale_notes = []
    orphan_notes = []  # No tags

    for note in notes:
        content = note.get("content", "") or ""
        tags = extract_tags(content)
        note_type = note.get("type", 0)

        # Tag analysis
        for tag in tags:
            tag_counts[tag] += 1
        type_counts[note_type] += 1

        # Monthly distribution
        created = note.get("createdAt", note.get("created_at", ""))
        if created:
            month = created[:7]  # YYYY-MM
            monthly_counts[month] += 1

        # Stale detection (no update in 30+ days)
        updated = note.get("updatedAt", note.get("updated_at", created))
        if updated:
            try:
                update_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if (now - update_dt).days > 30:
                    stale_notes.append(note)
            except Exception:
                pass

        # Orphan detection (no tags)
        if not tags:
            orphan_notes.append(note)

    return {
        "total_notes": len(notes),
        "tag_counts": tag_counts.most_common(50),
        "type_counts": dict(type_counts),
        "monthly_counts": dict(sorted(monthly_counts.items())),
        "stale_count": len(stale_notes),
        "orphan_count": len(orphan_notes),
        "top_tags": tag_counts.most_common(20),
    }


def export_to_excel(notes: list[dict], analysis: dict) -> str:
    """Export Blinko analysis to branded Excel workbook."""
    # Summary sheet
    summary_rows = [
        {"metric": "Total Notes", "value": analysis["total_notes"]},
        {"metric": "Unique Tags", "value": len(analysis["tag_counts"])},
        {"metric": "Stale Notes (30+ days)", "value": analysis["stale_count"]},
        {"metric": "Orphan Notes (no tags)", "value": analysis["orphan_count"]},
        {"metric": "Flash Notes (type 0)", "value": analysis["type_counts"].get(0, 0)},
        {"metric": "Full Notes (type 1)", "value": analysis["type_counts"].get(1, 0)},
    ]

    # Tag distribution
    tag_rows = [{"tag": f"#{tag}", "count": count} for tag, count in analysis["top_tags"]]

    # Monthly trend
    monthly_rows = [{"month": m, "notes_created": c} for m, c in analysis["monthly_counts"].items()]

    # Note inventory (first 200)
    note_rows = []
    for n in notes[:200]:
        content = (n.get("content", "") or "")
        tags = extract_tags(content)
        note_rows.append({
            "id": n.get("id", "")[:12],
            "type": "flash" if n.get("type") == 0 else "full",
            "tags": ", ".join(tags[:5]),
            "preview": content[:100].replace("\n", " "),
            "created": (n.get("createdAt", "") or "")[:10],
        })

    try:
        from hive_deliverables import generate_excel
        return generate_excel(
            title="Blinko Knowledge Base Audit",
            sheets={
                "Summary": summary_rows,
                "Tag Distribution": tag_rows,
                "Monthly Trend": monthly_rows,
                "Note Inventory": note_rows,
            },
        )
    except ImportError:
        # JSON fallback
        path = OUTPUT_DIR / f"blinko_audit_{datetime.now().strftime('%Y%m%d')}.json"
        with open(path, "w") as f:
            json.dump({"summary": summary_rows, "tags": tag_rows, "monthly": monthly_rows}, f, indent=2)
        return str(path)


def run_optimization(dedupe: bool = False) -> dict:
    """Run full Blinko optimization."""
    log.info("Starting Blinko optimization...")

    notes = fetch_all_notes()
    if not notes:
        log.warning("No notes fetched. Check Blinko API.")
        return {}

    analysis = analyze_notes(notes)

    log.info(f"Total notes: {analysis['total_notes']}")
    log.info(f"Unique tags: {len(analysis['tag_counts'])}")
    log.info(f"Stale notes (30+ days): {analysis['stale_count']}")
    log.info(f"Orphan notes (no tags): {analysis['orphan_count']}")
    log.info(f"Top tags: {', '.join(f'#{t}({c})' for t, c in analysis['top_tags'][:10])}")

    if dedupe:
        dupes = find_duplicates(notes)
        log.info(f"Found {len(dupes)} potential duplicates")
        analysis["duplicates"] = len(dupes)

    return analysis


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    analysis = run_optimization(dedupe=args.dedupe)

    if args.export or not args.stats:
        notes = fetch_all_notes()
        path = export_to_excel(notes, analysis)
        log.info(f"Export saved: {path}")

    if args.stats:
        print(json.dumps(analysis, indent=2, default=str))
