"""Custom template tags and filters for the XLM Trading Dashboard."""
from datetime import datetime, timezone, timedelta
from django import template
from django.utils.safestring import mark_safe

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except ImportError:
    PT = timezone(timedelta(hours=-8))

register = template.Library()


# ── Value formatting ──

@register.filter(name="money")
def money(val):
    """Format as USD: $1,234.56 or '--'."""
    if val is None:
        return "--"
    try:
        v = float(val)
        if abs(v) >= 1000:
            return f"${v:,.2f}"
        return f"${v:.2f}"
    except (ValueError, TypeError):
        return "--"


@register.filter(name="money_signed")
def money_signed(val):
    """Format as signed USD: +$12.34 / -$5.67."""
    if val is None:
        return "--"
    try:
        v = float(val)
        sign = "+" if v >= 0 else ""
        if abs(v) >= 1000:
            return f"{sign}${v:,.2f}"
        return f"{sign}${v:.2f}"
    except (ValueError, TypeError):
        return "--"


@register.filter(name="pct")
def pct(val):
    """Format as percentage: 72.5%."""
    if val is None:
        return "--"
    try:
        return f"{float(val):.1f}%"
    except (ValueError, TypeError):
        return "--"


@register.filter(name="price6")
def price6(val):
    """Format price with 6 decimals: $0.161234."""
    if val is None:
        return "--"
    try:
        return f"${float(val):.6f}"
    except (ValueError, TypeError):
        return "--"


# ── CSS class helpers ──

@register.filter(name="pnl_color")
def pnl_color(val):
    """Return CSS class based on P&L value: 'ok', 'danger', or ''."""
    try:
        v = float(val)
        if v > 0:
            return "ok"
        elif v < 0:
            return "danger"
    except (ValueError, TypeError):
        pass
    return ""


@register.filter(name="direction_color")
def direction_color(val):
    """Return CSS class for direction: 'ok' for long, 'danger' for short."""
    s = str(val).lower().strip()
    if s in ("long", "buy"):
        return "ok"
    elif s in ("short", "sell"):
        return "danger"
    return ""


@register.filter(name="tone_class")
def tone_class(val):
    """Map tone string to CSS class."""
    mapping = {"good": "ok", "bad": "danger", "warn": "gold", "info": "blue"}
    return mapping.get(str(val).lower(), "")


@register.filter(name="regime_color")
def regime_color(val):
    """Map volatility regime to color class."""
    s = str(val).lower()
    if "expansion" in s:
        return "danger"
    elif "compression" in s:
        return "ok"
    elif "transition" in s:
        return "gold"
    return ""


# ── Badge/pill rendering ──

@register.filter(name="direction_badge")
def direction_badge(val):
    """Render a colored pill for LONG/SHORT."""
    s = str(val).upper().strip()
    if s in ("LONG", "BUY"):
        return mark_safe('<span class="pill ok">LONG</span>')
    elif s in ("SHORT", "SELL"):
        return mark_safe('<span class="pill danger">SHORT</span>')
    return mark_safe('<span class="pill">FLAT</span>')


@register.filter(name="status_badge")
def status_badge(val):
    """Render a status pill: LIVE, OFFLINE, etc."""
    s = str(val).upper().strip()
    color_map = {
        "LIVE": "ok", "ONLINE": "ok", "ACTIVE": "ok",
        "OFFLINE": "danger", "DEAD": "danger", "ERROR": "danger",
        "IDLE": "gold", "WATCHING": "gold", "COOLDOWN": "gold",
    }
    cls = color_map.get(s, "")
    return mark_safe(f'<span class="pill {cls}">{s}</span>')


@register.filter(name="gate_badge")
def gate_badge(val):
    """Render gate pass/fail badge."""
    v = str(val).lower()
    if v in ("true", "pass", "1", "yes"):
        return mark_safe('<span style="color:#34d399;">&#10003;</span>')
    return mark_safe('<span style="color:#f87171;">&#10007;</span>')


# ── Time formatting ──

@register.filter(name="pt_short")
def pt_short(val):
    """Format datetime to 'Feb 26 10:30 AM PT'."""
    if not val:
        return "--"
    try:
        if isinstance(val, str):
            val = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        local = val.astimezone(PT)
        return local.strftime("%b %d %I:%M %p PT")
    except Exception:
        return "--"


@register.filter(name="since")
def since(val):
    """Format as relative time: '5m ago'."""
    if not val:
        return "--"
    try:
        if isinstance(val, str):
            val = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - val
        secs = int(delta.total_seconds())
        if secs < 0:
            return "just now"
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return "--"


@register.filter(name="duration_fmt")
def duration_fmt(val):
    """Format seconds as '2m 15s' or '12.3s'."""
    if val is None:
        return "--"
    try:
        s = float(val)
        if s < 60:
            return f"{s:.1f}s"
        m = int(s // 60)
        remaining = int(s % 60)
        return f"{m}m {remaining}s"
    except (ValueError, TypeError):
        return "--"


@register.filter(name="pct_bar_width")
def pct_bar_width(val):
    """Convert 0-100 to CSS width string."""
    try:
        v = max(0, min(100, float(val)))
        return f"{v:.1f}%"
    except (ValueError, TypeError):
        return "0%"


# ── Safe value extraction ──

@register.filter(name="safe_float")
def safe_float_filter(val):
    """NaN/None-safe float."""
    if val is None:
        return 0.0
    try:
        import math
        v = float(val)
        return 0.0 if math.isnan(v) else v
    except (ValueError, TypeError):
        return 0.0


@register.filter(name="json_pretty")
def json_pretty(val):
    """Render dict/list as formatted JSON in a pre block."""
    import json as _json
    try:
        if isinstance(val, str):
            val = _json.loads(val)
        text = _json.dumps(val, indent=2, default=str)
        return mark_safe(f'<pre style="color:#d1d5db;font-size:12px;overflow-x:auto;">{text}</pre>')
    except Exception:
        return mark_safe(f"<pre>{val}</pre>")


# ── Gate / Confluence plain English ──

@register.filter(name="gate_plain")
def gate_plain(val):
    """Human-readable gate name."""
    mapping = {
        "atr": "Volatility too low",
        "atr_regime": "Volatility regime mismatch",
        "session": "Outside trading session",
        "distance": "Too far from value zone",
        "spread": "Spread too wide",
        "cooldown": "Post-loss cooldown active",
        "margin": "Insufficient margin",
        "daily_loss": "Daily loss limit reached",
        "daily_trades": "Daily trade cap reached",
    }
    return mapping.get(str(val).lower(), str(val))


@register.filter(name="confluence_plain")
def confluence_plain(val):
    """Human-readable confluence flag."""
    mapping = {
        "rsi_bullish": "RSI bullish momentum",
        "rsi_bearish": "RSI bearish momentum",
        "macd_bullish": "MACD bullish crossover",
        "macd_bearish": "MACD bearish crossover",
        "volume_surge": "Volume surge detected",
        "trend_aligned": "Aligned with trend",
        "structure_support": "Near support zone",
        "structure_resistance": "Near resistance zone",
    }
    return mapping.get(str(val).lower(), str(val))
