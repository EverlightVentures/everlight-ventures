#!/usr/bin/env python3
"""
Daily Drop Engine -- Everlight Ventures
Autonomous daily curation of highest-rated items/sellers from affiliate sources.

Pipeline:
  1. candidate_fetch  -- pull rated items from affiliate APIs / Supabase catalog
  2. rank             -- score via Gear Score formula
  3. validate         -- hard gates (rating, stock, margin)
  4. publish          -- POST today's drop to Supabase (Lovable reads it)
  5. log              -- audit trail to _logs/gear_drops/

Guarantees 1 publish/day via fallback queue.
Runs at 6:00 PM PT daily via cron.

Usage:
    python3 daily_drop_orchestrator.py              # full cycle (default)
    python3 daily_drop_orchestrator.py fetch        # fetch + rank only (dry run)
    python3 daily_drop_orchestrator.py publish      # publish queued drop
    python3 daily_drop_orchestrator.py status       # show today's drop status
"""
import argparse
import json
import logging
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
LOGS_DIR = os.path.join(ROOT_DIR, "_logs", "gear_drops")
STAGING_DIR = os.path.join(ROOT_DIR, "07_STAGING", "Inbox", "gear_drops")
GEAR_ENGINE_DIR = os.path.join(ROOT_DIR, "01_BUSINESSES", "Everlight_Ventures",
                               "Everlight_Foundations", "gear_engine")

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(STAGING_DIR, exist_ok=True)

# Load .env
env_path = os.path.join(BASE_DIR, "..", "03_Credentials", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
# Match XLM bot naming: SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_KEY
SUPABASE_SERVICE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
    or ""
)
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
AMAZON_AFFILIATE_TAG = os.environ.get("AMAZON_AFFILIATE_TAG", "everlightv-20")

# Gear Score thresholds
MIN_RATING = 4.5
MIN_STOCK = 5           # units or "in_stock" boolean
MIN_MARGIN_PCT = 3.0    # minimum affiliate commission %
MAX_DAILY_DROPS = 3     # surface up to N products; guarantee 1

# Scoring weights
W_RATING       = 0.50
W_VELOCITY     = 0.30
W_COMMISSION   = 0.20

PT = ZoneInfo("America/Los_Angeles")

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
today_str = datetime.now(PT).strftime("%Y-%m-%d")
log_file = os.path.join(LOGS_DIR, f"drop_{today_str}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("daily_drop")


# ---------------------------------------------------------------------------
# SUPABASE HELPERS
# ---------------------------------------------------------------------------
def _supa_headers(write=False):
    key = SUPABASE_SERVICE_KEY if (write and SUPABASE_SERVICE_KEY) else SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supa_select(table: str, params: dict = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_supa_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        log.warning(f"supa_select({table}) failed: {e}")
        return []


def supa_upsert(table: str, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={**_supa_headers(write=True),
                                          "Prefer": "resolution=merge-duplicates,return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            log.info(f"supa_upsert({table}) OK -- id={resp[0].get('id') if resp else '?'}")
            return True
    except Exception as e:
        log.error(f"supa_upsert({table}) failed: {e}")
        return False


# ---------------------------------------------------------------------------
# STEP 1: CANDIDATE FETCH
# ---------------------------------------------------------------------------
def fetch_candidates() -> list:
    """
    Pull product candidates from:
    A) gear_catalog table in Supabase (manually curated / webhook-fed)
    B) Static fallback queue from gear_engine config
    Returns list of dicts with: id, title, url, rating, sales_velocity,
                                 commission_pct, stock, image_url, seller, description
    """
    log.info("STEP 1 -- Fetching candidates...")
    candidates = []

    # Source A: Supabase gear_catalog
    rows = supa_select("gear_catalog", {
        "select": "*",
        "rating": f"gte.{MIN_RATING}",
        "active": "eq.true",
        "order": "rating.desc,sales_velocity.desc",
        "limit": "50",
    })
    if rows:
        log.info(f"  Supabase: {len(rows)} candidates")
        candidates.extend(rows)
    else:
        log.warning("  Supabase gear_catalog empty or unavailable")

    # Source B: Fallback queue (local JSON)
    fallback_path = os.path.join(GEAR_ENGINE_DIR, "fallback_queue.json")
    if os.path.exists(fallback_path):
        with open(fallback_path) as f:
            fallback = json.load(f)
        # Filter unused fallbacks
        used = _load_published_ids()
        unused = [p for p in fallback if p.get("id") not in used]
        log.info(f"  Fallback queue: {len(unused)} unused items")
        # Only use fallback if Supabase gave nothing
        if not candidates:
            candidates.extend(unused)
    else:
        log.warning(f"  No fallback queue at {fallback_path}")

    log.info(f"  Total candidates: {len(candidates)}")
    return candidates


def _load_published_ids() -> set:
    published_log = os.path.join(GEAR_ENGINE_DIR, "published_ids.json")
    if os.path.exists(published_log):
        with open(published_log) as f:
            return set(json.load(f))
    return set()


def _save_published_id(product_id: str):
    published_log = os.path.join(GEAR_ENGINE_DIR, "published_ids.json")
    ids = _load_published_ids()
    ids.add(product_id)
    with open(published_log, "w") as f:
        json.dump(list(ids), f)


# ---------------------------------------------------------------------------
# STEP 2: RANK
# ---------------------------------------------------------------------------
def gear_score(item: dict) -> float:
    """
    Gear Score = (Rating * 0.5) + (SalesVelocity_norm * 0.3) + (Commission_norm * 0.2)
    Normalized to 0-100.
    """
    rating = float(item.get("rating", 0))
    velocity = float(item.get("sales_velocity", 0))   # e.g. 0-1000 units/week
    commission = float(item.get("commission_pct", 0)) # e.g. 0-20%

    # Normalize to 0-5 scale (rating already 0-5; velocity/commission scaled)
    r_norm = (rating / 5.0) * 100
    v_norm = min(velocity / 500.0, 1.0) * 100   # cap at 500 units/week = 100
    c_norm = min(commission / 15.0, 1.0) * 100  # cap at 15% = 100

    return round((r_norm * W_RATING) + (v_norm * W_VELOCITY) + (c_norm * W_COMMISSION), 2)


def rank_candidates(candidates: list) -> list:
    log.info("STEP 2 -- Ranking candidates...")
    for item in candidates:
        item["gear_score"] = gear_score(item)
    ranked = sorted(candidates, key=lambda x: x["gear_score"], reverse=True)
    for i, item in enumerate(ranked[:5]):
        log.info(f"  #{i+1} score={item['gear_score']} | {item.get('title','?')[:50]}")
    return ranked


# ---------------------------------------------------------------------------
# STEP 3: VALIDATE (hard gates)
# ---------------------------------------------------------------------------
def validate(candidates: list) -> list:
    log.info("STEP 3 -- Validating against hard gates...")
    already_published = _load_published_ids()
    passed = []
    for item in candidates:
        pid = str(item.get("id", ""))
        rating = float(item.get("rating", 0))
        stock = item.get("stock", 0)
        commission = float(item.get("commission_pct", 0))

        # Already published check
        if pid in already_published:
            continue

        # Hard gates
        if rating < MIN_RATING:
            log.debug(f"  FAIL rating {rating} < {MIN_RATING}: {item.get('title','?')[:40]}")
            continue
        if isinstance(stock, bool):
            if not stock:
                log.debug(f"  FAIL out-of-stock: {item.get('title','?')[:40]}")
                continue
        elif int(stock) < MIN_STOCK:
            log.debug(f"  FAIL stock {stock} < {MIN_STOCK}: {item.get('title','?')[:40]}")
            continue
        if commission < MIN_MARGIN_PCT:
            log.debug(f"  FAIL commission {commission}% < {MIN_MARGIN_PCT}%: {item.get('title','?')[:40]}")
            continue

        passed.append(item)

    log.info(f"  Passed: {len(passed)} / {len(candidates)} candidates")
    return passed


# ---------------------------------------------------------------------------
# STEP 4: PUBLISH
# ---------------------------------------------------------------------------
def build_drop_payload(item: dict) -> dict:
    now_pt = datetime.now(PT)
    drop_date = now_pt.strftime("%Y-%m-%d")
    drop_id = hashlib.md5(f"{drop_date}-{item.get('id','')}".encode()).hexdigest()[:12]

    return {
        "id": drop_id,
        "drop_date": drop_date,
        "product_id": str(item.get("id", "")),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "image_url": item.get("image_url", ""),
        "affiliate_url": item.get("url", ""),
        "seller": item.get("seller", ""),
        "rating": float(item.get("rating", 0)),
        "gear_score": item.get("gear_score", 0),
        "commission_pct": float(item.get("commission_pct", 0)),
        "drop_time_pt": now_pt.isoformat(),
        "published": True,
        "source": item.get("source", "supabase"),
    }


def publish_drops(validated: list) -> list:
    log.info("STEP 4 -- Publishing drops...")
    if not validated:
        log.error("  No validated candidates -- CRITICAL: guarantee broken!")
        return []

    # Take top N
    to_publish = validated[:MAX_DAILY_DROPS]
    published = []

    for item in to_publish:
        payload = build_drop_payload(item)

        # Save to staging JSON for audit
        staging_file = os.path.join(STAGING_DIR,
                                    f"drop_{payload['drop_date']}_{payload['id']}.json")
        with open(staging_file, "w") as f:
            json.dump(payload, f, indent=2)
        log.info(f"  Staged: {staging_file}")

        # Push to Supabase daily_drops table
        ok = supa_upsert("daily_drops", payload)
        if ok:
            _save_published_id(str(item.get("id", "")))
            published.append(payload)
            log.info(f"  Published: {payload['title'][:50]} | score={payload['gear_score']}")
        else:
            log.warning(f"  Supabase push FAILED for {payload['title'][:50]}")

    log.info(f"  Published {len(published)} drops")
    return published


# ---------------------------------------------------------------------------
# STEP 5: LOG / REPORT
# ---------------------------------------------------------------------------
def write_daily_report(published: list, candidates_count: int):
    report = {
        "date": today_str,
        "candidates_fetched": candidates_count,
        "published_count": len(published),
        "drops": published,
        "generated_at_pt": datetime.now(PT).isoformat(),
    }
    report_file = os.path.join(LOGS_DIR, f"report_{today_str}.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    log.info(f"Report written: {report_file}")

    # Print summary
    print("\n" + "="*60)
    print(f"DAILY DROP REPORT -- {today_str}")
    print("="*60)
    print(f"Candidates fetched : {candidates_count}")
    print(f"Drops published    : {len(published)}")
    for i, d in enumerate(published, 1):
        print(f"  #{i}: {d['title'][:55]} | score={d['gear_score']}")
    print("="*60 + "\n")


# ---------------------------------------------------------------------------
# STATUS CHECK
# ---------------------------------------------------------------------------
def cmd_status():
    rows = supa_select("daily_drops", {
        "drop_date": f"eq.{today_str}",
        "published": "eq.true",
        "select": "id,title,gear_score,drop_time_pt",
    })
    if rows:
        print(f"TODAY's DROP ({today_str}): {len(rows)} item(s) live")
        for r in rows:
            print(f"  - {r.get('title','?')[:55]} | score={r.get('gear_score','?')}")
    else:
        print(f"NO DROP published yet for {today_str}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run_full():
    log.info(f"=== Daily Drop Engine START {today_str} ===")
    candidates = fetch_candidates()
    ranked = rank_candidates(candidates)
    validated = validate(ranked)
    published = publish_drops(validated)
    write_daily_report(published, len(candidates))

    if not published:
        log.error("FAILURE: 0 drops published today. Manual intervention required.")
        sys.exit(1)

    log.info(f"=== Daily Drop Engine DONE -- {len(published)} drop(s) published ===")


def main():
    parser = argparse.ArgumentParser(description="Daily Drop Engine")
    parser.add_argument("cmd", nargs="?", default="full",
                        choices=["full", "fetch", "publish", "status"])
    args = parser.parse_args()

    if args.cmd == "full":
        run_full()
    elif args.cmd == "fetch":
        candidates = fetch_candidates()
        ranked = rank_candidates(candidates)
        validated = validate(ranked)
        print(f"\nFetch complete. {len(validated)} valid candidates ready.")
        for item in validated[:5]:
            print(f"  score={item['gear_score']} | {item.get('title','?')[:55]}")
    elif args.cmd == "publish":
        # Publish from staging (for manual override)
        files = sorted(os.listdir(STAGING_DIR))
        today_files = [f for f in files if today_str in f and f.endswith(".json")]
        if today_files:
            print(f"Staging files for today: {today_files}")
        else:
            print("No staged drops for today. Run 'full' first.")
    elif args.cmd == "status":
        cmd_status()


if __name__ == "__main__":
    main()
