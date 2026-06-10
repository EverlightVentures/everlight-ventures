"""zillow_loader -- pull Zillow public ZHVI + ZORI data by ZIP code.

Why this exists
---------------
Hard-coding 3 zip codes does not scale. Zillow Research publishes free,
public CSV files of their Home Value Index (ZHVI) and Observed Rent Index
(ZORI) for every ZIP in the country. No API key required. Updated monthly.

This module downloads, caches, and queries those files so any property in
any compliant state gets real numbers.

Data files (public, no auth)
----------------------------
  ZHVI by ZIP (Single-Family + Condo, mid-tier 33-67%):
    https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv

  ZORI by ZIP (Single-Family + Condo + Multifamily):
    https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv

Cache location
--------------
  /home/opc/wholesale/pitches/data/zhvi_zip.csv
  /home/opc/wholesale/pitches/data/zori_zip.csv
  Refreshed if older than 30 days.

Public API
----------
    from zillow_loader import zhvi_for_zip, zori_for_zip, refresh_if_stale

    refresh_if_stale()
    val = zhvi_for_zip("30311")
    # -> {"value": 235000, "yoy_pct": 4.6, "3yr_pct": 31.2, "data_quarter": "2026-Q1"}
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("zillow_loader")

ZHVI_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"

WORKSPACE_CANDIDATES = [
    Path("/home/opc/wholesale/pitches/data"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches/data"),
]


def _data_dir() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.parent.exists():
            p.mkdir(parents=True, exist_ok=True)
            return p
    fallback = Path("/tmp/zillow_data")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


ZHVI_CSV = _data_dir() / "zhvi_zip.csv"
ZORI_CSV = _data_dir() / "zori_zip.csv"


def _download(url: str, dest: Path, timeout: int = 60) -> bool:
    """Stream-download a Zillow CSV to disk."""
    try:
        req = Request(url, headers={"User-Agent": "EverlightWholesale/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        dest.write_bytes(data)
        log.info("downloaded %s (%d bytes)", url, len(data))
        return True
    except (HTTPError, URLError, TimeoutError) as exc:
        log.warning("zillow download failed (%s): %s", url, exc)
        return False
    except Exception as exc:
        log.warning("zillow download exception: %s", exc)
        return False


def _is_stale(path: Path, days: int = 30) -> bool:
    if not path.exists():
        return True
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return age > timedelta(days=days)


def refresh_if_stale(force: bool = False) -> dict:
    """Refresh both CSVs if older than 30 days. Returns status."""
    out = {"zhvi": False, "zori": False}
    if force or _is_stale(ZHVI_CSV):
        out["zhvi"] = _download(ZHVI_URL, ZHVI_CSV)
    if force or _is_stale(ZORI_CSV):
        out["zori"] = _download(ZORI_URL, ZORI_CSV)
    return out


def _read_csv_for_zip(path: Path, zip_code: str) -> Optional[dict[str, str]]:
    """Find the row matching this ZIP. Returns dict or None."""
    if not path.exists():
        return None
    z = (zip_code or "").strip().lstrip("0")
    z_padded = z.zfill(5)
    try:
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rz = (row.get("RegionName", "") or "").strip().lstrip("0").zfill(5)
                if rz == z_padded:
                    return row
    except Exception as exc:
        log.warning("csv read failed: %s", exc)
    return None


def _date_columns(row: dict[str, str]) -> list[str]:
    """Zillow CSVs put dates as column headers like '2026-03-31'."""
    return sorted([k for k in row.keys() if len(k) == 10 and k[4] == "-" and k[7] == "-"])


def _latest_value(row: dict[str, str]) -> tuple[Optional[float], Optional[str]]:
    """Find the most recent non-empty data point."""
    cols = _date_columns(row)
    for c in reversed(cols):
        v = (row.get(c) or "").strip()
        if v:
            try:
                return float(v), c
            except ValueError:
                continue
    return None, None


def _value_at_offset(row: dict[str, str], months_back: int) -> Optional[float]:
    """Value from N months ago (vs the latest)."""
    cols = _date_columns(row)
    if not cols:
        return None
    cols = list(reversed(cols))
    if months_back >= len(cols):
        return None
    v = (row.get(cols[months_back]) or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def zhvi_for_zip(zip_code: str) -> Optional[dict]:
    """Return dict with median home value, YoY %, 3yr %, and data quarter."""
    row = _read_csv_for_zip(ZHVI_CSV, zip_code)
    if not row:
        return None
    latest, latest_col = _latest_value(row)
    if not latest:
        return None
    yoy = _value_at_offset(row, 12)
    three_yr = _value_at_offset(row, 36)
    yoy_pct = ((latest - yoy) / yoy * 100) if yoy else None
    three_yr_pct = ((latest - three_yr) / three_yr * 100) if three_yr else None
    five_yr = _value_at_offset(row, 60)
    five_yr_pct = ((latest - five_yr) / five_yr * 100) if five_yr else None
    return {
        "zip": zip_code,
        "city": row.get("City", ""),
        "state": row.get("State", ""),
        "metro": row.get("Metro", ""),
        "county": row.get("CountyName", ""),
        "median_home_value": int(latest),
        "median_home_value_yoy_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
        "median_home_value_3yr_pct": round(three_yr_pct, 2) if three_yr_pct is not None else None,
        "median_home_value_5yr_pct": round(five_yr_pct, 2) if five_yr_pct is not None else None,
        "data_as_of": latest_col,
        "source": "Zillow ZHVI public",
    }


def zori_for_zip(zip_code: str) -> Optional[dict]:
    """Return dict with median rent, YoY %, data quarter."""
    row = _read_csv_for_zip(ZORI_CSV, zip_code)
    if not row:
        return None
    latest, latest_col = _latest_value(row)
    if not latest:
        return None
    yoy = _value_at_offset(row, 12)
    yoy_pct = ((latest - yoy) / yoy * 100) if yoy else None
    return {
        "zip": zip_code,
        "median_rent_index": int(latest),
        "median_rent_yoy_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
        "data_as_of": latest_col,
        "source": "Zillow ZORI public",
    }


def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("refresh")
    pq = sub.add_parser("query")
    pq.add_argument("--zip", required=True)
    sub.add_parser("status")

    args = ap.parse_args()

    if args.cmd == "refresh":
        print(json.dumps(refresh_if_stale(force=True), indent=2))
        return 0
    if args.cmd == "query":
        zhvi = zhvi_for_zip(args.zip)
        zori = zori_for_zip(args.zip)
        print(json.dumps({"zhvi": zhvi, "zori": zori}, indent=2))
        return 0
    if args.cmd == "status":
        print(json.dumps({
            "zhvi_csv_exists": ZHVI_CSV.exists(),
            "zhvi_csv_size": ZHVI_CSV.stat().st_size if ZHVI_CSV.exists() else 0,
            "zhvi_age_days": (datetime.now(timezone.utc) - datetime.fromtimestamp(ZHVI_CSV.stat().st_mtime, tz=timezone.utc)).days if ZHVI_CSV.exists() else None,
            "zori_csv_exists": ZORI_CSV.exists(),
            "zori_csv_size": ZORI_CSV.stat().st_size if ZORI_CSV.exists() else 0,
        }, indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
