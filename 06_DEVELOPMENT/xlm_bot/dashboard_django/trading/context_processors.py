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

    return {
        "now_pt": now_pt,
        "bot_alive": alive,
        "bot_age_s": bot_age_s,
        "current_price": price,
        "bot_state": state,
        "app_name": "XLM PERP",
        "app_version": "2.0",
    }
