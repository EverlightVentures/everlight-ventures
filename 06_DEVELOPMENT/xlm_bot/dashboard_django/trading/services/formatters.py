"""
Formatter service -- pure functions for display formatting.

No caching needed; these are stateless transformations.
All timezone display uses America/Los_Angeles (auto-DST).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pandas as pd

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except ImportError:
    PT = timezone(timedelta(hours=-8), name="PT")  # fallback


# ---------------------------------------------------------------------------
# Money / numeric formatting
# ---------------------------------------------------------------------------

def format_money(val) -> str:
    """Format a number as '$1,234.56', or return '--' for None/NaN."""
    if val is None:
        return "\u2014"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "\u2014"
        return f"${f:,.2f}"
    except (TypeError, ValueError):
        return "\u2014"


def safe_float(val, default: float = 0.0) -> float:
    """NaN/None-safe float conversion."""
    try:
        if val is None or val == "":
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def safe_str(val, default: str = "") -> str:
    """NaN/None-safe string conversion."""
    if val is None:
        return default
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return default
        except Exception:
            return default
    s = str(val)
    if s.lower() in ("nan", "none", ""):
        return default
    return s


def safe_bool(val, default: bool = False) -> bool:
    """Treat NaN/None as False."""
    if val is None:
        return default
    if isinstance(val, float):
        try:
            if math.isnan(val) or math.isinf(val):
                return default
        except Exception:
            return default
    return bool(val)


# ---------------------------------------------------------------------------
# Timestamp formatting
# ---------------------------------------------------------------------------

def coerce_ts_utc(val) -> datetime | None:
    """Parse any timestamp string/number to UTC datetime."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        s = str(val).strip()
        if not s:
            return None
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        try:
            ts = pd.to_datetime(val, utc=True, errors="coerce")
            if pd.isna(ts):
                return None
            return ts.to_pydatetime()
        except Exception:
            return None


def fmt_pt_short(ts) -> str:
    """Format timestamp as 'Feb 26 10:30 AM PT'."""
    dt = coerce_ts_utc(ts)
    if dt is None:
        return "?"
    try:
        return dt.astimezone(PT).strftime("%b %d %I:%M %p PT")
    except Exception:
        return "?"


def fmt_since(ts) -> str:
    """Relative time like '5m ago', '2h ago'."""
    dt = coerce_ts_utc(ts)
    if dt is None:
        return "?"
    try:
        age = int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return "?"
    if age < 0:
        age = 0
    if age < 60:
        return f"{age}s ago"
    if age < 3600:
        return f"{age // 60}m ago"
    if age < 86400:
        return f"{age // 3600}h ago"
    return f"{age // 86400}d ago"


def fmt_age_s(age_s: int | None) -> str:
    """Format seconds as '2m 30s'."""
    if age_s is None:
        return "-"
    if age_s < 0:
        return "0s"
    if age_s < 60:
        return f"{age_s}s"
    if age_s < 3600:
        return f"{age_s // 60}m {age_s % 60:02d}s"
    return f"{age_s // 3600}h {(age_s % 3600) // 60:02d}m"


# ---------------------------------------------------------------------------
# CSS class helpers (for templates)
# ---------------------------------------------------------------------------

def pnl_class(val) -> str:
    """Return 'ok' for positive, 'danger' for negative, '' for zero/None."""
    try:
        f = float(val)
        if math.isnan(f):
            return ""
        if f > 0:
            return "ok"
        if f < 0:
            return "danger"
    except (TypeError, ValueError):
        pass
    return ""


def direction_class(direction) -> str:
    """Return 'ok' for long, 'danger' for short."""
    d = str(direction or "").lower()
    if "long" in d:
        return "ok"
    if "short" in d:
        return "danger"
    return ""
