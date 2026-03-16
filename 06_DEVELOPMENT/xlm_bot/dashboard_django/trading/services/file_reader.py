"""
File reader service -- cached file I/O for state, config, logs, trades.

All file paths resolve from Django settings (settings.XLM_DATA_DIR, settings.XLM_LOGS_DIR).
Replaces @st.cache_data with Django LocMemCache keyed on (mtime_ns, size).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.cache import cache

DATA_DIR: Path = settings.XLM_DATA_DIR
LOGS_DIR: Path = settings.XLM_LOGS_DIR


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def file_sig(path: Path) -> tuple[int, int]:
    """Return (mtime_ns, size) for cache-key invalidation."""
    try:
        st_ = path.stat()
        return int(st_.st_mtime_ns), int(st_.st_size)
    except OSError:
        return (0, 0)


def _cached_file_load(path: Path, loader_fn, prefix: str = "fl", timeout: int = 120):
    """Generic cache-around-file pattern. Invalidates when file changes."""
    sig = file_sig(path)
    key = f"{prefix}_{path.name}_{sig[0]}_{sig[1]}"
    result = cache.get(key)
    if result is None:
        result = loader_fn(path)
        cache.set(key, result, timeout=timeout)
    return result


# ---------------------------------------------------------------------------
# Core loaders (uncached, called via _cached_file_load)
# ---------------------------------------------------------------------------

def _load_jsonl_raw(
    path: Path,
    max_lines: int = 2000,
    max_tail_bytes: int = 512 * 1024,
) -> list[dict]:
    """Tail-read a JSONL file efficiently. Returns list of dicts."""
    if not path.exists():
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            end = f.tell()
            chunk = min(end, max(64 * 1024, int(max_tail_bytes)))
            f.seek(end - chunk)
            raw = f.read().decode("utf-8", errors="ignore")
        lines = raw.splitlines()
        # Drop potential partial first line when starting mid-file.
        if chunk < end and lines:
            lines = lines[1:]
        lines = lines[-max_lines:]
    except Exception:
        try:
            lines = path.read_text(errors="ignore").splitlines()[-max_lines:]
        except Exception:
            return []

    rows: list[dict] = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _coerce_ts_utc(val) -> datetime | None:
    """Parse any timestamp representation to UTC datetime."""
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_jsonl(
    path: Path,
    max_lines: int | None = None,
    max_tail_bytes: int | None = None,
) -> list[dict]:
    """Load JSONL file with tail-read optimisation. Cached on file signature."""
    ml = max_lines or 2000
    mtb = max_tail_bytes or (512 * 1024)

    sig = file_sig(path)
    key = f"jsonl_{path.name}_{sig[0]}_{sig[1]}_{ml}"
    result = cache.get(key)
    if result is None:
        result = _load_jsonl_raw(path, max_lines=ml, max_tail_bytes=mtb)
        cache.set(key, result, timeout=120)
    return result


def load_jsonl_window(
    path: Path,
    lookback_days: int = 7,
    max_lines: int | None = None,
) -> list[dict]:
    """Load JSONL filtered to a time window. Returns list of dicts."""
    ml = max_lines or 50000
    rows = load_jsonl(path, max_lines=ml, max_tail_bytes=8 * 1024 * 1024)
    if not rows:
        return rows
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))
    filtered: list[dict] = []
    for row in rows:
        t = _coerce_ts_utc(row.get("timestamp") or row.get("ts"))
        if t is not None and t >= cutoff:
            filtered.append(row)
    return filtered


def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV as DataFrame. Cached on file signature."""
    def _loader(p: Path) -> pd.DataFrame:
        if not p.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(p)
        except Exception:
            try:
                return pd.read_csv(p, engine="python", on_bad_lines="skip")
            except Exception:
                return pd.DataFrame()
    return _cached_file_load(path, _loader, prefix="csv")


def load_state() -> dict:
    """Parse DATA_DIR/state.json."""
    p = DATA_DIR / "state.json"
    def _loader(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return _cached_file_load(p, _loader, prefix="state")


def load_snapshot() -> dict:
    """Load dashboard_snapshot.json with .last_good fallback.

    Returns snapshot dict (with optional ``_snap_status`` key on error).
    """
    path = LOGS_DIR / "dashboard_snapshot.json"
    backup = LOGS_DIR / "dashboard_snapshot.last_good.json"

    sig = file_sig(path)
    bsig = file_sig(backup)
    key = f"snap_{sig[0]}_{sig[1]}_{bsig[0]}_{bsig[1]}"
    result = cache.get(key)
    if result is not None:
        return result

    if not path.exists():
        result = {"_snap_status": "waiting_for_bot"}
    else:
        try:
            raw = path.read_text()
            snap = json.loads(raw)
            if isinstance(snap, dict):
                result = snap
            else:
                raise ValueError("snapshot_not_object")
        except Exception as e:
            try:
                if backup.exists():
                    fallback = json.loads(backup.read_text())
                    if isinstance(fallback, dict):
                        fallback["_snap_status"] = f"snapshot_corrupt_using_last_good: {e}"
                        result = fallback
                    else:
                        result = {"_snap_status": f"snapshot_unreadable: {e}"}
                else:
                    result = {"_snap_status": f"snapshot_unreadable: {e}"}
            except Exception:
                result = {"_snap_status": f"snapshot_unreadable: {e}"}

    cache.set(key, result, timeout=120)
    return result


def load_config() -> dict:
    """Parse config.yaml from the bot root (DATA_DIR/..)."""
    cfg_path = DATA_DIR.parent / "config.yaml"
    def _loader(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            import yaml
            return yaml.safe_load(path.read_text()) or {}
        except Exception:
            return {}
    return _cached_file_load(cfg_path, _loader, prefix="cfg")


def load_json_file(name: str, data_dir: bool = True) -> dict:
    """Load an arbitrary JSON file from DATA_DIR or LOGS_DIR."""
    base = DATA_DIR if data_dir else LOGS_DIR
    p = base / name
    def _loader(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return _cached_file_load(p, _loader, prefix="jf")


def load_decisions(limit: int = 80) -> list[dict]:
    """Load LOGS_DIR/decisions.jsonl (most recent `limit` lines)."""
    return load_jsonl(LOGS_DIR / "decisions.jsonl", max_lines=limit)


def load_trades() -> pd.DataFrame:
    """Load LOGS_DIR/trades.csv as a DataFrame."""
    return load_csv(LOGS_DIR / "trades.csv")


def load_incidents() -> list[dict]:
    """Load LOGS_DIR/incidents.jsonl."""
    return load_jsonl(LOGS_DIR / "incidents.jsonl", max_lines=500)


def load_cash_movements() -> list[dict]:
    """Load LOGS_DIR/cash_movements.jsonl."""
    return load_jsonl(LOGS_DIR / "cash_movements.jsonl", max_lines=500)


def load_market_news() -> list[dict]:
    """Load LOGS_DIR/market_news.jsonl."""
    return load_jsonl(LOGS_DIR / "market_news.jsonl", max_lines=200)


def bot_alive() -> tuple[bool, int]:
    """Check .heartbeat file age. Returns (alive, age_seconds).

    Bot is considered alive if heartbeat is < 120 seconds old.
    """
    try:
        hb = DATA_DIR / ".heartbeat"
        if not hb.exists():
            return False, -1
        age = datetime.now(timezone.utc).timestamp() - float(hb.read_text().strip())
        return age < 120, int(age)
    except Exception:
        return False, -1


def tail_log(log_type: str, n: int = 50) -> list[str]:
    """Return the last *n* lines from a log file.

    *log_type* is a bare name like ``"bot"`` or ``"ai_debug"``; the
    function appends ``.log`` and looks in LOGS_DIR.
    """
    name = log_type if "." in log_type else f"{log_type}.log"
    path = LOGS_DIR / name
    try:
        if not path.exists():
            return []
        txt = path.read_text(errors="ignore")
        lines = txt.splitlines()
        return lines[-int(n):]
    except Exception:
        return []
