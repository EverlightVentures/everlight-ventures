"""Global context injected into every template."""
from datetime import datetime, timezone, timedelta
from trading.services import file_reader, exchange, formatters

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except ImportError:
    PT = timezone(timedelta(hours=-8))


def trading_globals(request):
    """Provide sidebar + header data to all templates."""
    snap = file_reader.load_snapshot()
    state = file_reader.load_state()

    # Bot alive check -- returns (bool, age_seconds)
    alive, bot_age_s = file_reader.bot_alive()

    # Current time in PT
    now_pt = datetime.now(PT)

    # Price from snapshot
    price = None
    if isinstance(snap, dict):
        price = snap.get("mark_price") or snap.get("last_price")
        if price:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = None

    # Staleness check -- warn if snapshot is older than 5 minutes
    snap_stale = False
    snap_age_s = None
    if isinstance(snap, dict) and snap.get("timestamp"):
        try:
            from trading.services.file_reader import _coerce_ts_utc
            snap_ts = _coerce_ts_utc(snap["timestamp"])
            if snap_ts:
                snap_age_s = int((datetime.now(timezone.utc) - snap_ts).total_seconds())
                snap_stale = snap_age_s > 300
        except Exception:
            pass

    return {
        "now_pt": now_pt,
        "bot_alive": alive,
        "bot_age_s": bot_age_s,
        "current_price": price,
        "bot_state": state,
        "snap_stale": snap_stale,
        "snap_age_s": snap_age_s,
        "app_name": "Belfort Terminal",
        "app_version": "2.1-wolf",
    }
