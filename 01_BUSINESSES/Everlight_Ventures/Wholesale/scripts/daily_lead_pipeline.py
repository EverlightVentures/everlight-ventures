#!/usr/bin/env python3
"""
daily_lead_pipeline.py -- Autonomous Memphis wholesale lead intake.

Chains existing tools into one daily pass:
  1. Read parcels from Wholesale/owner_downloads/parsed/*.json
  2. Filter to Chris's buy-box (config/chris_buy_box.json)
  3. Skip-trace top candidates via skip_trace_free.py
  4. Score via rex_lead_scorer_v2.score_lead()
  5. Run OSINT deep-dive on top-N (seller_intel_deepdive.py)
  6. Generate pitch hooks via pitch_tailor.tailor_for_seller()
  7. Render branded HTML report to 09_DASHBOARD/reports/daily_leads/
  8. Post top-10 to #ft-hunters via branded_slack

Cron: 0 3 * * * python3 /mnt/sdcard/.../daily_lead_pipeline.py
Memory rule: feedback_reuse_existing_infra_first.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
PARSED_DIR = WH / "owner_downloads" / "parsed"
CONFIG_PATH = WH / "config" / "chris_buy_box.json"
REPORT_DIR = ROOT / "09_DASHBOARD" / "reports" / "daily_leads"
LOG_PATH = ROOT / "_logs" / "daily_lead_pipeline.log"

# Make existing modules importable
sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent"))
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts"))
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
sys.path.insert(0, str(ROOT / "06_DEVELOPMENT/everlight_os/intel_center"))


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def load_buy_box() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open() as f:
        return json.load(f)


def load_parcels() -> list[dict]:
    parcels = []
    if not PARSED_DIR.exists():
        return parcels
    for p in sorted(PARSED_DIR.glob("*.json")):
        try:
            with p.open() as f:
                j = json.load(f)
            j["_source_file"] = p.name
            parcels.append(j)
        except Exception as e:
            _log(f"  skip {p.name}: {e}")
    return parcels


def apply_buy_box_filter(parcels: list[dict], box: dict) -> list[dict]:
    """Drop parcels that fail any hard buy-box rule. Keep soft preferences as ranking signals only."""
    if not box:
        return parcels
    geo = box.get("geography", {})
    prop = box.get("property", {})
    bt = box.get("back_tax", {})
    zips = set(geo.get("zips", []))
    classes = set(prop.get("property_class", []))
    exclude_vacant = bool(prop.get("exclude_vacant_lot", True))
    min_app = prop.get("min_appraisal_usd", 0)
    max_app = prop.get("max_appraisal_usd", 10_000_000)
    bt_max = bt.get("max_usd", 10_000_000)

    out = []
    for p in parcels:
        # zip filter (soft if owner_mailing_zip != property zip; use property zip)
        addr_zip = (p.get("owner_mailing_zip") or "").strip()
        if zips and addr_zip and addr_zip not in zips:
            continue
        # property class
        cls = (p.get("property_class") or "").upper()
        if classes and cls and cls not in classes:
            continue
        # exclude vacant lot
        if exclude_vacant and p.get("is_vacant_lot"):
            continue
        # appraisal band
        app = p.get("total_appraisal_usd") or 0
        if app and (app < min_app or app > max_app):
            continue
        # back-tax band (data may not be parsed yet; only drop if known + over)
        bt_est = p.get("back_tax_estimate") or 0
        if bt_est and bt_est > bt_max:
            continue
        out.append(p)
    return out


def parcel_to_scorer_lead(parcel: dict) -> dict:
    """Adapt parsed-parcel schema to rex_lead_scorer_v2 expected lead schema."""
    return {
        "parcel_id": parcel.get("parcel_id"),
        "address": parcel.get("property_address_full") or parcel.get("property_address"),
        "owner_name": parcel.get("owner_name"),
        "absentee_owner": parcel.get("absentee_owner"),
        "is_vacant_lot": parcel.get("is_vacant_lot"),
        "year_built": parcel.get("build_year_proxy"),
        "last_sale_year": parcel.get("last_sale_year"),
        "last_sale_price_usd": parcel.get("last_sale_price_usd"),
        "total_appraisal_usd": parcel.get("total_appraisal_usd"),
        "owner_mailing_state": parcel.get("owner_mailing_state"),
        "owner_mailing_city": parcel.get("owner_mailing_city"),
        "owner_mailing_zip": parcel.get("owner_mailing_zip"),
        "chris_check": parcel.get("chris_check", {}),
        "phone": parcel.get("phone"),
        "email": parcel.get("email"),
    }


def score_all(parcels: list[dict]) -> list[dict]:
    """Attach score + tier to each parcel using rex_lead_scorer_v2 if available."""
    try:
        from rex_lead_scorer_v2 import score_lead, classify  # type: ignore
    except Exception as e:
        _log(f"  rex_lead_scorer_v2 unavailable: {e}; using zero scores")
        for p in parcels:
            p["_score"] = 0
            p["_tier"] = "UNSCORED"
        return parcels

    for p in parcels:
        try:
            lead = parcel_to_scorer_lead(p)
            s = score_lead(lead)
            p["_score"] = int(s)
            p["_tier"] = classify(int(s))
        except Exception as e:
            _log(f"  score fail {p.get('parcel_id')}: {e}")
            p["_score"] = 0
            p["_tier"] = "ERROR"
    return parcels


def run_skip_trace(top_n: int, dry_run: bool) -> None:
    """Delegate to existing skip_trace_free.py with --limit."""
    if dry_run:
        _log(f"  dry-run: would skip-trace top {top_n}")
        return
    script = ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "skip_trace_free.py"
    if not script.exists():
        _log(f"  skip_trace_free.py not found at {script}; skipping")
        return
    cmd = ["python3", str(script), "--limit", str(top_n), "--state", "TN"]
    _log(f"  exec: {' '.join(cmd)}")
    try:
        rc = subprocess.run(cmd, timeout=60 * 30, check=False).returncode
        _log(f"  skip-trace rc={rc}")
    except subprocess.TimeoutExpired:
        _log("  skip-trace timed out at 30 min")


def run_intel_deepdive(parcel: dict, dry_run: bool) -> dict | None:
    """Run seller_intel_deepdive.py for one parcel; return intel dict if produced."""
    pid = parcel.get("parcel_id")
    if not pid:
        return None
    intel_path = WH / "seller_intel" / pid.replace(" ", "_") / "intel.json"
    if intel_path.exists():
        try:
            with intel_path.open() as f:
                return json.load(f)
        except Exception:
            pass
    if dry_run:
        _log(f"  dry-run: would deepdive {pid}")
        return None
    script = ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "seller_intel_deepdive.py"
    if not script.exists():
        return None
    try:
        subprocess.run(["python3", str(script), "--parcel", pid], timeout=120, check=False)
        if intel_path.exists():
            with intel_path.open() as f:
                return json.load(f)
    except Exception as e:
        _log(f"  deepdive fail {pid}: {e}")
    return None


def tailor_pitch(parcel: dict, intel: dict | None) -> dict | None:
    """Call pitch_tailor.tailor_for_seller() if intel is present."""
    if not intel:
        return None
    try:
        from osint_api.pitch_tailor import tailor_for_seller  # type: ignore
        lead = parcel_to_scorer_lead(parcel)
        return tailor_for_seller(intel, lead, None)
    except Exception as e:
        _log(f"  pitch_tailor fail {parcel.get('parcel_id')}: {e}")
        return None


def render_html_report(date_str: str, ranked: list[dict]) -> Path:
    """Render branded HTML via report_template.render_report and save."""
    try:
        from report_template import render_report  # type: ignore
    except Exception as e:
        _log(f"  report_template unavailable: {e}")
        return None

    rows = []
    for i, p in enumerate(ranked[:25], 1):
        addr = p.get("property_address_full") or p.get("property_address") or "?"
        owner = p.get("owner_name") or "?"
        cls = p.get("property_class") or "?"
        app = p.get("total_appraisal_usd") or 0
        tier = p.get("_tier", "?")
        score = p.get("_score", 0)
        pitch = p.get("_pitch", {}) or {}
        hook = pitch.get("hook_line") or "(no hook)"
        rows.append(
            f"<tr><td>{i}</td><td>{addr}</td><td>{owner}</td>"
            f"<td>{cls}</td><td>${app:,}</td><td>{score}</td>"
            f"<td><strong>{tier}</strong></td><td>{hook}</td></tr>"
        )
    table = (
        "<table style='width:100%;border-collapse:collapse;font-size:14px;'>"
        "<thead><tr style='background:#1a1a1a;'>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>#</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Property</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Owner</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Class</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Appraisal</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Score</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Tier</th>"
        "<th align='left' style='padding:8px;border-bottom:2px solid #D4A843;'>Pitch hook</th>"
        "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )
    summary_html = (
        f"<p><strong>Date:</strong> {date_str}</p>"
        f"<p><strong>Total parcels scanned:</strong> {len(ranked)}</p>"
        f"<p><strong>Top {min(25, len(ranked))} after buy-box filter + rex_lead_scorer_v2 ranking:</strong></p>"
        + table
    )
    html = render_report(
        title=f"Memphis Daily Leads -- {date_str}",
        content_html=summary_html,
        agent_name="Rex Blackwell",
        agent_title="Acquisitions Scout, TN/Memphis",
        agent_email="rex@everlightventures.io",
    )
    out = REPORT_DIR / f"{date_str}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    _log(f"  wrote report {out}")
    return out


def post_to_slack(date_str: str, ranked: list[dict], report_path: Path, dry_run: bool) -> None:
    if dry_run:
        _log("  dry-run: would post to #ft-hunters")
        return
    try:
        from branded_slack import post_branded_slack  # type: ignore
    except Exception as e:
        _log(f"  branded_slack unavailable: {e}")
        return
    top = ranked[:10]
    lines = []
    for i, p in enumerate(top, 1):
        addr = p.get("property_address_full") or p.get("property_address") or "?"
        tier = p.get("_tier", "?")
        score = p.get("_score", 0)
        lines.append(f"{i}. {addr} -- score {score} {tier}")
    body = "\n".join(lines) or "no leads passed buy-box today"
    report_url = f"http://127.0.0.1:2200/reports/daily_leads/{date_str}.html"
    try:
        post_branded_slack(
            channel="#ft-hunters",
            title=f"Memphis Daily Leads -- {date_str}",
            summary=f"{len(ranked)} parcels scanned; top {len(top)} below.",
            body=body,
            report_url=report_url,
            agent_name="Rex Blackwell",
            agent_title="Acquisitions Scout",
            category="deal",
        )
        _log("  posted to #ft-hunters")
    except Exception as e:
        _log(f"  slack post fail: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Memphis daily lead pipeline")
    ap.add_argument("--dry-run", action="store_true", help="no subprocess, no slack")
    ap.add_argument("--top-skip-trace", type=int, default=100)
    ap.add_argument("--top-intel", type=int, default=50)
    ap.add_argument("--top-pitch", type=int, default=25)
    args = ap.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")
    _log(f"=== daily_lead_pipeline.py START {date_str} dry_run={args.dry_run} ===")

    box = load_buy_box()
    if not box:
        _log("  ERROR: no chris_buy_box.json config -- abort")
        return 2

    parcels = load_parcels()
    _log(f"  loaded {len(parcels)} parcels from {PARSED_DIR}")

    filtered = apply_buy_box_filter(parcels, box)
    _log(f"  {len(filtered)} parcels passed buy-box filter")

    # Skip-trace top N candidates (delegate to existing tool)
    run_skip_trace(args.top_skip_trace, args.dry_run)

    scored = score_all(filtered)
    scored.sort(key=lambda p: p.get("_score", 0), reverse=True)
    _log(f"  scored {len(scored)} parcels; top score = {scored[0].get('_score', 0) if scored else 0}")

    # OSINT + pitch hook for top-N
    for p in scored[: args.top_intel]:
        intel = run_intel_deepdive(p, args.dry_run)
        if intel:
            pitch = tailor_pitch(p, intel)
            if pitch:
                p["_pitch"] = pitch

    report_path = render_html_report(date_str, scored)
    if report_path:
        post_to_slack(date_str, scored, report_path, args.dry_run)

    _log(f"=== daily_lead_pipeline.py DONE -- {len(scored)} ranked, top tier: "
         f"{scored[0].get('_tier', '?') if scored else 'n/a'} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
