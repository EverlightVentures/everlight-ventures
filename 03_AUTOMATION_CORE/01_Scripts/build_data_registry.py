#!/usr/bin/env python3
"""
build_data_registry.py -- Centralized data layer index.

Rich (2026-05-13): "all the information needs to be centralized too. So if
need to like rag notes and spreadsheets and folders and drives like all of
that data should be an essential database at a very basic level."

This is the index. Doesn't move bytes -- just renders one branded HTML page
that lists every data store, its location, last write, row count / size, and
who/what writes to it. So Rich can SEE the data layer.

Output: 09_DASHBOARD/reports/DATA_REGISTRY.html
       01_BUSINESSES/Everlight_Ventures/_audits/data_registry.json (machine-readable)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
from env_loader import load_env  # noqa: E402
load_env()
from report_template import render_report  # noqa: E402

OUT_HTML = ROOT / "09_DASHBOARD" / "reports" / "DATA_REGISTRY.html"
OUT_JSON = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "_audits" / "data_registry.json"

# Skip noisy / temp paths
SKIP_PARTS = {".git", "node_modules", "__pycache__", "venv", ".venv", ".cache",
              ".next", "dist", "build", ".turbo", ".parcel-cache",
              "Theme", "08_BACKUPS", "Mountain Gardens Nursery POS",
              "vantaris", "everlightventures"}

EXTS_KIND = {
    ".db": "sqlite",
    ".sqlite": "sqlite",
    ".sqlite3": "sqlite",
    ".jsonl": "jsonl",
}


def is_skipped(p: Path) -> bool:
    parts = set(p.parts)
    return any(s in parts for s in SKIP_PARTS)


def walk_root() -> list[tuple[str, Path]]:
    """Single os.walk pass; pruning skips at the directory level (much faster than glob)."""
    found: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_PARTS and not d.startswith(".") or d in {".claude"}]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            kind = EXTS_KIND.get(ext)
            if kind:
                found.append((kind, Path(dirpath) / fn))
                continue
            # Catch a few hand-picked JSON/CSV registries by name
            low = fn.lower()
            if low.endswith(".json") and ("registry" in low or "_db" in low or low in {"leads_db.json", "buyers_db.json"}):
                found.append(("json", Path(dirpath) / fn))
            elif low.endswith(".csv") and ("registry" in low or "_db" in low):
                found.append(("csv", Path(dirpath) / fn))
    return found


def file_meta(p: Path) -> dict:
    try:
        st = p.stat()
        return {
            "size_bytes": st.st_size,
            "size_human": fmt_size(st.st_size),
            "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        }
    except Exception:
        return {}


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def sqlite_meta(p: Path) -> dict:
    try:
        c = sqlite3.connect(p)
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        counts = {}
        total = 0
        for t in tables[:30]:
            try:
                n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                counts[t] = n
                total += n
            except Exception:
                pass
        return {"tables": len(tables), "rows_total": total, "top_tables": dict(sorted(counts.items(), key=lambda x: -x[1])[:5])}
    except Exception as e:
        return {"error": str(e)[:80]}


def jsonl_meta(p: Path) -> dict:
    try:
        with p.open("rb") as f:
            count = sum(1 for _ in f)
        return {"lines": count}
    except Exception as e:
        return {"error": str(e)[:80]}


def csv_meta(p: Path) -> dict:
    try:
        with p.open("rb") as f:
            count = sum(1 for _ in f)
        return {"lines": count}
    except Exception as e:
        return {"error": str(e)[:80]}


def json_meta(p: Path) -> dict:
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(j, list):
            return {"records": len(j), "type": "list"}
        if isinstance(j, dict):
            return {"keys": len(j), "type": "object", "top_keys": list(j.keys())[:5]}
        return {"type": type(j).__name__}
    except Exception as e:
        return {"error": str(e)[:80]}


def categorize(rel: str) -> str:
    """Bucket a path under a logical data category."""
    r = rel.lower()
    if "blinko" in r:
        return "Memory / Knowledge"
    if "intel_center" in r or "everlight_intel" in r:
        return "Memory / Knowledge"
    if "wholesale" in r or "broker" in r:
        return "Wholesale + Broker Pipeline"
    if "xlm" in r or "trading" in r or "bot" in r:
        return "Trading"
    if "deal_execution" in r or "audit" in r:
        return "Audit Chains"
    if "_logs" in r:
        return "Operational Logs"
    if "blackjack" in r or "vantaris" in r or "alley_kingz" in r or "arcade" in r:
        return "Gaming / Apps"
    if "leads" in r or "outreach" in r or "buyers" in r or "sellers" in r:
        return "Lead + Buyer Data"
    if "session" in r or "hive" in r:
        return "Hive Sessions"
    if "compliance" in r or "dnc" in r:
        return "Compliance"
    if "content" in r or "publishing" in r:
        return "Content"
    if "field_ops" in r:
        return "Field Ops"
    return "Other"


CAT_COLORS = {
    "Memory / Knowledge": "#7ec699",
    "Wholesale + Broker Pipeline": "#D4AF37",
    "Trading": "#ff9f6b",
    "Audit Chains": "#a8a3ff",
    "Operational Logs": "#888",
    "Gaming / Apps": "#c39bff",
    "Lead + Buyer Data": "#6bafff",
    "Hive Sessions": "#ffd76b",
    "Compliance": "#ff6b6b",
    "Content": "#ff6b9f",
    "Field Ops": "#9fffb2",
    "Other": "#666",
}


def collect() -> list[dict]:
    rows: list[dict] = []
    found = walk_root()
    for kind, p in found:
        if is_skipped(p):
            continue
        rel = str(p.relative_to(ROOT))
        meta = file_meta(p)
        # Cap heavy reads: only crack open SQLite/JSONL/CSV/JSON if file < 50MB
        if meta.get("size_bytes", 0) < 50 * 1024 * 1024:
            try:
                if kind == "sqlite":
                    meta.update(sqlite_meta(p))
                elif kind == "jsonl":
                    meta.update(jsonl_meta(p))
                elif kind == "csv":
                    meta.update(csv_meta(p))
                elif kind == "json":
                    meta.update(json_meta(p))
            except Exception as e:
                meta["error"] = str(e)[:80]
        else:
            meta["note"] = "size>50MB, skipped row count"
        rows.append({
            "path": rel,
            "name": p.name,
            "kind": kind,
            "category": categorize(rel),
            "meta": meta,
        })
    rows.sort(key=lambda r: (r["category"], -r["meta"].get("size_bytes", 0)))
    return rows


def render_card(r: dict) -> str:
    color = CAT_COLORS.get(r["category"], "#D4AF37")
    meta = r["meta"]
    size = meta.get("size_human", "?")
    mtime = meta.get("mtime", "?")[:19]
    detail_bits = []
    if "rows_total" in meta:
        detail_bits.append(f"{meta['rows_total']:,} rows / {meta.get('tables',0)} tables")
    if "lines" in meta:
        detail_bits.append(f"{meta['lines']:,} lines")
    if "records" in meta:
        detail_bits.append(f"{meta['records']:,} records")
    if "keys" in meta:
        detail_bits.append(f"{meta['keys']} top-level keys")
    if "error" in meta:
        detail_bits.append(f"<span style='color:#ff6b6b;'>err: {meta['error']}</span>")
    detail = " &middot; ".join(detail_bits) or "—"
    top_tables = ""
    if meta.get("top_tables"):
        top_tables = "<div style='color:#888;font-size:11px;font-family:JetBrains Mono,monospace;margin-top:4px;'>"
        top_tables += " &middot; ".join(f"{t}={n}" for t, n in meta["top_tables"].items())
        top_tables += "</div>"
    return f"""
<div class='datacard' data-cat='{r['category'].lower()}' data-name='{r['name'].lower()}'
     style='background:#0d0d0d;border-left:3px solid {color};padding:12px 16px;border-radius:0 3px 3px 0;'>
  <div style='display:flex;justify-content:space-between;align-items:baseline;'>
    <div style='font-family:Playfair Display,serif;color:#E8E8E8;font-size:14px;font-weight:600;'>{r['name']}</div>
    <span style='color:{color};font-size:10px;text-transform:uppercase;letter-spacing:1px;'>{r['kind']} &middot; {size}</span>
  </div>
  <div style='color:#666;font-size:11px;font-family:JetBrains Mono,monospace;margin-top:4px;'>{r['path']}</div>
  <div style='color:#aaa;font-size:12px;margin-top:6px;'>{detail}</div>
  {top_tables}
  <div style='color:#666;font-size:11px;margin-top:6px;'>last write {mtime}</div>
</div>
"""


def main() -> int:
    rows = collect()
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    cats_sorted = sorted(by_cat.keys(), key=lambda c: -len(by_cat[c]))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "stores": rows}, indent=2), encoding="utf-8")

    total = len(rows)
    total_size = sum(r["meta"].get("size_bytes", 0) for r in rows)

    strip = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0 24px;'>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Stores</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{total}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Categories</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{len(by_cat)}</div>
  </div>
  <div style='background:#1a1a1a;padding:14px 18px;border-left:3px solid #D4AF37;'>
    <div style='color:#888;font-size:11px;text-transform:uppercase;'>Total Size</div>
    <div style='color:#E8E8E8;font-size:28px;font-family:Playfair Display,serif;'>{fmt_size(total_size)}</div>
  </div>
</div>

<div style='margin:12px 0;'>
  <input id='datasearch' type='text' placeholder='Search stores -- name, path, category'
         style='width:100%;padding:14px 16px;background:#0d0d0d;color:#E8E8E8;border:1px solid #2a2a2a;
                border-left:3px solid #D4AF37;font-family:Inter,sans-serif;font-size:15px;'>
</div>
"""

    sections = []
    for cat in cats_sorted:
        c = CAT_COLORS.get(cat, "#D4AF37")
        sections.append(f"""
<section class='datasection' data-cat='{cat.lower()}' style='margin-top:32px;'>
  <h2 style='font-family:Playfair Display,serif;color:{c};font-size:22px;margin:0 0 10px;border-bottom:1px solid #2a2a2a;padding-bottom:6px;'>
    {cat} <span style='color:#666;font-size:13px;font-family:Inter,sans-serif;'>({len(by_cat[cat])})</span>
  </h2>
  <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:12px;'>
    {''.join(render_card(r) for r in by_cat[cat])}
  </div>
</section>
""")

    js = """
<script>
(function() {
  const box = document.getElementById('datasearch');
  const cards = document.querySelectorAll('.datacard');
  const sections = document.querySelectorAll('.datasection');
  box.addEventListener('input', () => {
    const q = (box.value || '').toLowerCase().trim();
    cards.forEach(c => {
      const t = (c.textContent || '').toLowerCase();
      c.style.display = (!q || t.includes(q)) ? '' : 'none';
    });
    sections.forEach(s => {
      s.style.display = Array.from(s.querySelectorAll('.datacard')).some(c => c.style.display !== 'none') ? '' : 'none';
    });
  });
})();
</script>
"""

    body = f"""
<p style='color:#888;font-size:14px;'>
Every internal data store. SQLite DBs, JSONL audit logs, CSV registries,
JSON registries. Auto-discovered via filesystem walk.
Counterpart to the <a href='SERVICES_REGISTRY.html' style='color:#D4AF37;'>Services Registry</a> (which catalogs external APIs).
</p>
{strip}
{''.join(sections)}
{js}
<p style='color:#666;font-size:12px;margin-top:32px;'>
Machine-readable mirror at <code style='background:#1a1a1a;color:#D4AF37;padding:2px 6px;'>01_BUSINESSES/Everlight_Ventures/_audits/data_registry.json</code>.
Re-render: <code style='background:#1a1a1a;color:#D4AF37;padding:2px 6px;'>python3 03_AUTOMATION_CORE/01_Scripts/build_data_registry.py</code>.
</p>
"""
    html = render_report(
        title="Data Registry -- Internal Stores",
        content_html=body,
        agent_name="Hive Mind",
        agent_title="Data Layer Index",
    )
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes)")
    print(f"  {total} stores / {len(by_cat)} categories / {fmt_size(total_size)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
