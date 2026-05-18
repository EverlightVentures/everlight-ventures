#!/usr/bin/env python3
"""
Build 09_Dashboard/data.js from the Intel Center SQLite database.

Output schema (window.INTEL = ...):
{
  meta: {generated, total, categories, agents, in_use, in_use_pct},
  categories: [{name, count, used, fetchable, department, agent_owner}],
  agents:     [{name, slug, count, used, categories: [...]}],
  resources:  [{id, domain, url, name, category, purpose, agent_owner,
                department, verified_status, in_use, evidence}],
  audit_top:  [{domain, files}],     // top-used resources
  fetchable_topics: {kw: category},  // for the Live Feeds page
}
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "database" / "everlight_resources.sqlite"
CFG = ROOT / "config" / "categories.yaml"
OUT = ROOT / "09_Dashboard" / "data.js"
AUDIT = ROOT / "logs" / "audit_latest.json"

cfg = yaml.safe_load(CFG.read_text())
fetchable_set = set(cfg.get("fetchable_categories", []))
fetchable_topics = {
    "news": "News & Journalism",
    "weather": "Weather & Disaster Intel",
    "space": "Space & Science",
    "finance": "Trading & Finance",
    "osint": "OSINT & Investigation",
    "health": "Health & Environment",
    "markets": "Economics & Markets",
    "aviation": "Aviation & Maritime",
}

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# Audit lookup (may not exist if user hasn't run audit)
audit_map: dict[str, tuple[int, str]] = {}
try:
    for r in con.execute("SELECT domain, in_use, evidence FROM audit"):
        audit_map[r["domain"]] = (r["in_use"], r["evidence"] or "")
except sqlite3.OperationalError:
    pass

# Live-active lookup -- domains that have been actually HTTP-fetched (cache/live_log.sqlite)
LIVE_LOG = ROOT / "cache" / "live_log.sqlite"
live_map: dict[str, dict] = {}
if LIVE_LOG.exists():
    lcon = sqlite3.connect(LIVE_LOG)
    lcon.row_factory = sqlite3.Row
    try:
        for r in lcon.execute("""
            SELECT domain, last_success, success_count, last_status_code, last_bytes
            FROM live_pulls
        """):
            live_map[r["domain"]] = {
                "last_success": r["last_success"],
                "success_count": r["success_count"] or 0,
                "last_status": r["last_status_code"],
                "last_bytes": r["last_bytes"] or 0,
            }
    except sqlite3.OperationalError:
        pass
    lcon.close()

# Cached articles per domain (from intel pull)
ARTICLES_DB = ROOT / "cache" / "articles.sqlite"
articles_by_domain: dict[str, list[dict]] = {}
articles_total = 0
if ARTICLES_DB.exists():
    artcon = sqlite3.connect(ARTICLES_DB)
    artcon.row_factory = sqlite3.Row
    try:
        for row in artcon.execute("SELECT domain, title, url, published, summary, fetched_at FROM articles ORDER BY id DESC"):
            articles_by_domain.setdefault(row["domain"], []).append({
                "title": row["title"], "url": row["url"],
                "published": row["published"], "summary": row["summary"],
                "fetched_at": row["fetched_at"],
            })
            articles_total += 1
    except sqlite3.OperationalError:
        pass
    artcon.close()

# Resources -- now includes use_case + setup_steps + cached articles
resources = []
for r in con.execute("""
    SELECT id, domain, url, name, category, purpose, agent_owner,
           department, verified_status, tags, source_type, last_checked,
           use_case, setup_steps
    FROM resources
    ORDER BY category, domain
"""):
    in_use, evidence = audit_map.get(r["domain"], (0, ""))
    arts = articles_by_domain.get(r["domain"], [])
    live = live_map.get(r["domain"])
    resources.append({
        "id": r["id"], "domain": r["domain"], "url": r["url"],
        "name": r["name"], "category": r["category"],
        "purpose": r["purpose"], "agent_owner": r["agent_owner"],
        "department": r["department"], "verified_status": r["verified_status"],
        "tags": r["tags"], "source_type": r["source_type"],
        "last_checked": r["last_checked"],
        "use_case": r["use_case"] or "",
        "setup_steps": r["setup_steps"] or "",
        "in_use": bool(in_use), "evidence": evidence,
        "live_active": bool(live and live["last_success"]),
        "live_status": live["last_status"] if live else None,
        "live_count": live["success_count"] if live else 0,
        "article_count": len(arts),
        "articles": arts[:8],
    })

# Category aggregation
cat_rows = []
for cat in sorted({r["category"] for r in resources}):
    cat_resources = [r for r in resources if r["category"] == cat]
    used = sum(1 for r in cat_resources if r["in_use"])
    live = sum(1 for r in cat_resources if r["live_active"])
    cat_rows.append({
        "name": cat,
        "count": len(cat_resources),
        "used": used,
        "live": live,
        "fetchable": cat in fetchable_set,
        "department": cat_resources[0]["department"] if cat_resources else "",
        "agent_owner": cat_resources[0]["agent_owner"] if cat_resources else "",
    })
cat_rows.sort(key=lambda c: -c["count"])

# Agent aggregation
agent_rows = []
for agent in sorted({r["agent_owner"] for r in resources if r["agent_owner"]}):
    a_resources = [r for r in resources if r["agent_owner"] == agent]
    used = sum(1 for r in a_resources if r["in_use"])
    cats = sorted({r["category"] for r in a_resources})
    slug = "".join(c.lower() if c.isalnum() else "_" for c in agent).strip("_")
    agent_rows.append({
        "name": agent,
        "slug": slug,
        "count": len(a_resources),
        "used": used,
        "categories": cats,
    })
agent_rows.sort(key=lambda a: -a["count"])

# Audit summary
in_use_count = sum(1 for r in resources if r["in_use"])
live_active_count = sum(1 for r in resources if r["live_active"])

# Domain status breakdown (live / auth_gated / dead / etc)
try:
    sys.path.insert(0, str(ROOT))
    from osint_api.domain_status import status_map as _ds_map, stats as _ds_stats
    domain_status = _ds_map()
    domain_status_breakdown = _ds_stats()
except Exception:
    domain_status = {}
    domain_status_breakdown = {"live": 0, "auth_gated": 0, "rate_limited": 0, "dead": 0, "untested": 0}

# Attach status per resource
for r in resources:
    r["domain_status"] = domain_status.get((r.get("domain") or "").lower(), "untested")

# Usage telemetry (from investigations + live_pulls + leads_db)
from datetime import timedelta
usage = {
    "investigations": {"total": 0, "last_7d": 0, "by_trigger": {}, "top_targets": []},
    "pulls": {"total": 0, "by_trigger": {}, "timeline_24h": {}},
    "leads": {"enriched": 0, "total": 0},
}
INVESTIGATIONS_DB = ROOT / "cache" / "investigations.sqlite"
LIVE_LOG_DB = ROOT / "cache" / "live_log.sqlite"
LEADS_DB = ROOT.parent / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "leads_db.sqlite"
now = datetime.now()
cutoff_7d = (now - timedelta(days=7)).isoformat()
cutoff_24h = now - timedelta(hours=24)

if INVESTIGATIONS_DB.exists():
    ic = sqlite3.connect(INVESTIGATIONS_DB)
    try:
        usage["investigations"]["total"] = ic.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
        usage["investigations"]["last_7d"] = ic.execute(
            "SELECT COUNT(*) FROM investigations WHERE started_at >= ?", (cutoff_7d,)
        ).fetchone()[0]
        for row in ic.execute("SELECT COALESCE(triggered_by, '(legacy)'), COUNT(*) FROM investigations GROUP BY 1 ORDER BY 2 DESC"):
            usage["investigations"]["by_trigger"][row[0]] = row[1]
        usage["investigations"]["top_targets"] = [
            {"target": t, "count": n}
            for t, n in ic.execute("SELECT target, COUNT(*) FROM investigations GROUP BY target ORDER BY 2 DESC LIMIT 10")
        ]
    except sqlite3.OperationalError:
        pass
    ic.close()

if LIVE_LOG_DB.exists():
    lc = sqlite3.connect(LIVE_LOG_DB)
    try:
        usage["pulls"]["total"] = lc.execute("SELECT COUNT(*) FROM live_pulls").fetchone()[0]
        for row in lc.execute("SELECT COALESCE(last_triggered_by, '(legacy)'), COUNT(*) FROM live_pulls GROUP BY 1 ORDER BY 2 DESC LIMIT 15"):
            usage["pulls"]["by_trigger"][row[0]] = row[1]
        for row in lc.execute("SELECT last_attempt FROM live_pulls WHERE last_attempt IS NOT NULL"):
            try:
                ts_obj = datetime.fromisoformat(row[0])
                if ts_obj >= cutoff_24h:
                    bucket = ts_obj.strftime("%H:00")
                    usage["pulls"]["timeline_24h"][bucket] = usage["pulls"]["timeline_24h"].get(bucket, 0) + 1
            except (ValueError, TypeError):
                pass
    except sqlite3.OperationalError:
        pass
    lc.close()

if LEADS_DB.exists():
    try:
        wc = sqlite3.connect(LEADS_DB)
        usage["leads"]["total"] = wc.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        usage["leads"]["enriched"] = wc.execute(
            "SELECT COUNT(*) FROM leads WHERE intel_enrichment_json IS NOT NULL"
        ).fetchone()[0]
        wc.close()
    except sqlite3.OperationalError:
        pass

# ============================================================================
# CLIENTS -- per-target rollup of every investigation ever run
# ============================================================================
clients: list[dict] = []
if INVESTIGATIONS_DB.exists():
    ic = sqlite3.connect(INVESTIGATIONS_DB)
    ic.row_factory = sqlite3.Row

    # Per-target state lookup from compliance_log (latest non-null wins)
    state_by_target: dict[str, str] = {}
    if (ROOT / "cache" / "compliance.sqlite").exists():
        cc = sqlite3.connect(ROOT / "cache" / "compliance.sqlite")
        try:
            for r in cc.execute(
                "SELECT target, state FROM compliance_log "
                "WHERE state IS NOT NULL AND state != '' ORDER BY ts ASC"
            ):
                if r[0]:
                    state_by_target[r[0]] = r[1]
        except sqlite3.OperationalError:
            pass
        cc.close()

    # DNC lookup from leads_db.opted_out_emails / dnc_list (best effort)
    dnc_targets: set[str] = set()
    if LEADS_DB.exists():
        try:
            wc = sqlite3.connect(LEADS_DB)
            wc.row_factory = sqlite3.Row
            for tbl in ("dnc_list", "opted_out_emails"):
                try:
                    for r in wc.execute(f"SELECT * FROM {tbl}"):
                        rd = dict(r)
                        for key in ("target", "name", "owner_name", "full_name", "email"):
                            v = rd.get(key)
                            if v:
                                dnc_targets.add(str(v).strip().lower())
                except sqlite3.OperationalError:
                    pass
            wc.close()
        except sqlite3.OperationalError:
            pass

    # Group by target -- latest investigation_id wins (max started_at)
    try:
        rows = list(ic.execute("""
            SELECT id, target, kind, started_at, finished_at, elapsed_ms,
                   total_findings, investigators_run, file_path,
                   triggered_by, lead_id, verification_summary, business_purpose
            FROM investigations
            ORDER BY started_at DESC
        """))
    except sqlite3.OperationalError:
        rows = []

    by_target: dict[str, dict] = {}
    for r in rows:
        rd = dict(r)
        target = rd["target"] or "(unknown)"
        if target not in by_target:
            by_target[target] = {
                "first_seen": rd["started_at"],
                "last_seen": rd["started_at"],
                "latest": rd,
                "count": 0,
                "verified_findings": 0,
                "raw_findings": 0,
            }
        bucket = by_target[target]
        bucket["count"] += 1
        bucket["raw_findings"] += int(rd["total_findings"] or 0)
        # Track first_seen as earliest, last_seen as latest
        if (rd["started_at"] or "") < (bucket["first_seen"] or ""):
            bucket["first_seen"] = rd["started_at"]
        if (rd["started_at"] or "") > (bucket["last_seen"] or ""):
            bucket["last_seen"] = rd["started_at"]
            bucket["latest"] = rd
        # Pull verified count from verification_summary JSON
        vs = rd.get("verification_summary")
        if vs:
            try:
                vs_obj = json.loads(vs)
                bucket["verified_findings"] += int(vs_obj.get("verified", 0) or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    # Pull dnc_blocked authoritatively from each latest investigation's JSON file
    # (set by orchestrator preflight against Wholesale/compliance/dnc_list.json)
    for target, bucket in by_target.items():
        latest = bucket["latest"]
        inv_id = latest["id"]
        kind = latest["kind"] or "person"
        st = state_by_target.get(target, "")

        # Authoritative DNC: read the latest investigation JSON for this target
        dnc_blocked = target.strip().lower() in dnc_targets
        try:
            file_path = latest.get("file_path")
            if file_path and Path(file_path).exists():
                inv_data = json.loads(Path(file_path).read_text())
                if inv_data.get("dnc_blocked"):
                    dnc_blocked = True
        except (json.JSONDecodeError, OSError):
            pass

        clients.append({
            "id": inv_id,
            "target": target,
            "kind": kind,
            "first_seen": bucket["first_seen"],
            "last_seen": bucket["last_seen"],
            "investigation_count": bucket["count"],
            "verified_findings": bucket["verified_findings"],
            "raw_findings": bucket["raw_findings"],
            "dnc_blocked": dnc_blocked,
            "state": st,
            "tags": ["dnc"] if dnc_blocked else [],
            "report_url": f"http://127.0.0.1:2301/report/{inv_id}",
            "snapshot_url": f"http://127.0.0.1:2300/cache/reports/{inv_id}.html",
        })

    ic.close()

# Sort newest-first
clients.sort(key=lambda c: c["last_seen"] or "", reverse=True)

# Reports: one row PER INVESTIGATION (not deduped by target). Searchable.
reports = []
if INVESTIGATIONS_DB.exists():
    try:
        ic2 = sqlite3.connect(INVESTIGATIONS_DB)
        ic2.row_factory = sqlite3.Row
        for r in ic2.execute("""
            SELECT id, target, kind, started_at, finished_at, elapsed_ms,
                   total_findings, investigators_run, file_path,
                   triggered_by, lead_id, verification_summary, business_purpose
            FROM investigations ORDER BY started_at DESC
        """):
            rd = dict(r)
            verified = 0
            try:
                vs_obj = json.loads(rd.get("verification_summary") or "{}")
                verified = int(vs_obj.get("verified", 0) or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            # Pull DNC + state from the full investigation JSON if available
            dnc_blocked = False
            state_ctx = ""
            try:
                fp = rd.get("file_path")
                if fp and Path(fp).exists():
                    inv_data = json.loads(Path(fp).read_text())
                    dnc_blocked = bool(inv_data.get("dnc_blocked"))
                    state_ctx = (inv_data.get("verify_context") or {}).get("state", "") or ""
            except (json.JSONDecodeError, OSError):
                pass
            reports.append({
                "id": rd["id"],
                "target": rd["target"] or "(unknown)",
                "kind": rd["kind"] or "unknown",
                "started_at": rd["started_at"] or "",
                "elapsed_ms": rd["elapsed_ms"] or 0,
                "raw_findings": rd["total_findings"] or 0,
                "verified_findings": verified,
                "investigators_run": rd["investigators_run"] or 0,
                "triggered_by": rd["triggered_by"] or "(legacy)",
                "lead_id": rd["lead_id"],
                "business_purpose": rd["business_purpose"] or "",
                "state": state_ctx,
                "dnc_blocked": dnc_blocked,
                "report_url": f"http://127.0.0.1:2301/report/{rd['id']}",
                "snapshot_url": f"http://127.0.0.1:2300/cache/reports/{rd['id']}.html",
            })
        ic2.close()
    except sqlite3.OperationalError:
        pass

audit_top = []
if AUDIT.exists():
    audit_payload = json.loads(AUDIT.read_text())
    audit_top = [{"domain": d, "files": n} for d, n in audit_payload.get("top_used", [])]

meta = {
    "generated": datetime.now().strftime("%Y-%m-%d %H:%M PT"),
    "total": len(resources),
    "categories": len(cat_rows),
    "agents": len(agent_rows),
    "in_use": in_use_count,
    "in_use_pct": round(in_use_count * 100 / max(len(resources), 1), 1),
    "live_active": live_active_count,
    "live_active_pct": round(live_active_count * 100 / max(len(resources), 1), 1),
    "articles_total": articles_total,
    "sources_with_articles": len(articles_by_domain),
    "domain_status_breakdown": domain_status_breakdown,
}

payload = {
    "meta": meta,
    "categories": cat_rows,
    "agents": agent_rows,
    "resources": resources,
    "audit_top": audit_top,
    "fetchable_topics": fetchable_topics,
    "usage": usage,
    "clients": clients,
    "reports": reports,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("/* Generated by rebuild_data.py -- do not edit by hand. */\n"
               f"window.INTEL = {json.dumps(payload, indent=2)};\n")
print(f"[INTEL DASH] wrote {OUT.relative_to(ROOT)} -- "
      f"{meta['total']} resources, {meta['categories']} categories, "
      f"{meta['agents']} agents, {in_use_count} in use ({meta['in_use_pct']}%)")
