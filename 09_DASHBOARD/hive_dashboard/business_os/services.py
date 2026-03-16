import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import requests
from django.db.models import Count, Sum
from django.utils import timezone

from .models import BusinessAlert, BusinessEvent, RevenueStream

logger = logging.getLogger(__name__)

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs" / "business_os"
EVENT_LOG = LOG_DIR / "events.jsonl"
ALERT_LOG = LOG_DIR / "alerts.jsonl"
TRADING_WATCHTOWER_STATUS = LOG_DIR / "trading_watchtower_status.json"
BLACKJACK_WATCHTOWER_STATUS = LOG_DIR / "blackjack_watchtower_status.json"
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://jdqqmsmwmbsnlnstyavl.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("SUPABASE_ANON_KEY")
    or os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMs"
        "ImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
    )
)

DEFAULT_STREAMS = [
    {
        "slug": "hive_mind_saas",
        "name": "Hive Mind SaaS",
        "owner_agent": "saas_growth",
        "category": "recurring_saas",
        "status": "pilot",
        "monthly_target_usd": Decimal("3000.00"),
        "notes": "Chief-of-staff product with session, webhook, and audit value.",
    },
    {
        "slug": "broker_os",
        "name": "Broker OS",
        "owner_agent": "32_deal_closer",
        "category": "deal_fees",
        "status": "pilot",
        "monthly_target_usd": Decimal("2500.00"),
        "notes": "B2B matchmaking, finder fees, and invoiced commissions.",
    },
    {
        "slug": "onyx_pos",
        "name": "Onyx POS",
        "owner_agent": "engineering_foreman",
        "category": "vertical_saas",
        "status": "building",
        "monthly_target_usd": Decimal("1500.00"),
        "notes": "POS and retail ops subscriptions.",
    },
    {
        "slug": "daily_gear_drop",
        "name": "Daily Gear Drop",
        "owner_agent": "distribution_ops",
        "category": "affiliate_commerce",
        "status": "pilot",
        "monthly_target_usd": Decimal("800.00"),
        "notes": "Affiliate drop engine for everlightventures.io and related surfaces.",
    },
    {
        "slug": "digital_products",
        "name": "Digital Products",
        "owner_agent": "writer",
        "category": "one_time_sales",
        "status": "building",
        "monthly_target_usd": Decimal("1000.00"),
        "notes": "Prompt packs, templates, operating playbooks, and downloadable tools.",
    },
    {
        "slug": "publishing_media",
        "name": "Publishing and Media",
        "owner_agent": "content_director",
        "category": "catalog_revenue",
        "status": "active",
        "monthly_target_usd": Decimal("1200.00"),
        "notes": "Books, audiobooks, samples, and long-tail distribution.",
    },
    {
        "slug": "ai_services",
        "name": "AI Implementation Services",
        "owner_agent": "chief_operator",
        "category": "services",
        "status": "building",
        "monthly_target_usd": Decimal("4000.00"),
        "notes": "Setup, advisory, automation builds, and retained support.",
    },
    {
        "slug": "trading_intelligence",
        "name": "Trading Intelligence",
        "owner_agent": "trading_risk",
        "category": "data_product",
        "status": "pilot",
        "monthly_target_usd": Decimal("900.00"),
        "notes": "Sell analytics, reporting, and dashboards, not autonomous trading promises.",
    },
    {
        "slug": "blackjack_arcade",
        "name": "Blackjack Arcade",
        "owner_agent": "arcade_operator",
        "category": "gaming_iap",
        "status": "pilot",
        "monthly_target_usd": Decimal("2500.00"),
        "notes": "Social casino revenue from blackjack, VIP, and digital currency packs.",
    },
]


def _runtime_pair_score(data_dir: Path, logs_dir: Path) -> int:
    score = 0
    for path in (
        logs_dir / "dashboard_snapshot.json",
        logs_dir / "decisions.jsonl",
        logs_dir / "live_tick.json",
        data_dir / "market_brief.json",
        data_dir / "state.json",
    ):
        try:
            if path.exists():
                score = max(score, int(path.stat().st_mtime_ns))
        except OSError:
            continue
    return score


def _resolve_xlm_runtime_dirs() -> tuple[Path, Path]:
    base = WORKSPACE / "06_DEVELOPMENT" / "xlm_bot"
    pairs = [
        (base / "data", base / "logs"),
        (base / "data_trend", base / "logs_trend"),
        (base / "data_mr", base / "logs_mr"),
    ]
    best_data, best_logs = pairs[0]
    best_score = -1
    for data_dir, logs_dir in pairs:
        score = _runtime_pair_score(data_dir, logs_dir)
        if score > best_score:
            best_score = score
            best_data, best_logs = data_dir, logs_dir
    return best_data, best_logs


def _write_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        logger.debug("JSON read failed for %s", path)
    return {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    tmp.replace(path)


def _minutes_old(ts_value: str) -> float | None:
    if not ts_value:
        return None
    try:
        parsed = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return round((timezone.now() - parsed).total_seconds() / 60.0, 1)
    except Exception:
        return None


def _brief_age_minutes(path: Path) -> float | None:
    wrapper = _read_json(path)
    if not wrapper:
        return None
    return _minutes_old(str(wrapper.get("timestamp") or ""))


def _supabase_headers() -> dict[str, str] | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
    }


def _read_supabase_rows(table: str, *, params: dict[str, str]) -> list[dict]:
    headers = _supabase_headers()
    if not headers:
        return []
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            params=params,
            timeout=4,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        logger.debug("Supabase read failed for %s: %s", table, exc)
        return []


def _read_live_trading_supabase() -> tuple[dict, dict, dict]:
    live_row = {}
    feature = {}
    trade_label = {}

    live_rows = _read_supabase_rows(
        "xlm_bot_metrics",
        params={"select": "*", "id": "eq.1", "limit": "1"},
    )
    if live_rows:
        live_row = live_rows[0]

    feature_rows = _read_supabase_rows(
        "xlm_bot_feature_snapshots",
        params={"select": "*", "order": "ts.desc", "limit": "1"},
    )
    if feature_rows:
        feature = feature_rows[0]

    trade_rows = _read_supabase_rows(
        "xlm_bot_trade_labels",
        params={"select": "*", "order": "ts.desc", "limit": "1"},
    )
    if trade_rows:
        trade_label = trade_rows[0]

    return live_row, feature, trade_label


def _choose_trade_payload(local_payload: dict, remote_payload: dict) -> dict:
    local_age = _minutes_old(str(local_payload.get("ts") or ""))
    remote_age = _minutes_old(str(remote_payload.get("ts") or ""))
    if remote_payload and (local_age is None or (remote_age is not None and remote_age <= local_age)):
        return remote_payload
    return local_payload or remote_payload or {}


def _read_recent_trading_reports(limit: int = 6) -> list[dict]:
    rows = _read_supabase_rows(
        "xlm_bot_report_history",
        params={"select": "*", "order": "created_at.desc", "limit": str(limit)},
    )
    return rows if isinstance(rows, list) else []


def _collect_trading_watchtower_data() -> dict:
    data_dir, logs_dir = _resolve_xlm_runtime_dirs()
    snapshot_path = logs_dir / "dashboard_snapshot.json"
    pulse_path = data_dir / "market_pulse.json"
    brief_path = data_dir / "market_brief.json"
    feature_path = data_dir / "feature_snapshot_latest.json"
    trade_label_path = data_dir / "trade_label_latest.json"
    live_tick_path = logs_dir / "live_tick.json"

    snapshot = _read_json(snapshot_path)
    feature = _read_json(feature_path)
    trade_label = _read_json(trade_label_path)
    live_tick = _read_json(live_tick_path)
    pulse_wrapper = _read_json(pulse_path)
    pulse = pulse_wrapper.get("pulse") if isinstance(pulse_wrapper.get("pulse"), dict) else {}
    pulse_components = pulse.get("components") if isinstance(pulse.get("components"), dict) else {}

    live_row, live_feature, live_trade = _read_live_trading_supabase()
    local_snapshot_age = _minutes_old(str(snapshot.get("ts") or ""))
    live_snapshot_age = _minutes_old(str(live_row.get("generated_at") or ""))
    if live_row and (local_snapshot_age is None or (live_snapshot_age is not None and live_snapshot_age < local_snapshot_age)):
        snapshot = {
            **snapshot,
            **{
                "ts": live_row.get("generated_at"),
                "state": live_row.get("bot_state"),
                "direction": live_row.get("position_side"),
                "entry_signal": live_row.get("entry_signal"),
                "quality_tier": live_row.get("quality_tier"),
                "route_tier": live_row.get("route_tier"),
                "last_action": live_row.get("latest_decision_reason"),
                "gates_pass": live_feature.get("gates_pass") if live_feature else snapshot.get("gates_pass"),
            },
        }

    local_feature_age = _minutes_old(str(feature.get("ts") or ""))
    live_feature_age = _minutes_old(str(live_feature.get("ts") or ""))
    if live_feature and (local_feature_age is None or (live_feature_age is not None and live_feature_age <= local_feature_age)):
        feature = {**feature, **live_feature}

    if live_row:
        for key, source_key in {
            "bot_state": "bot_state",
            "quality_tier": "quality_tier",
            "route_tier": "route_tier",
            "entry_signal": "entry_signal",
            "reason": "latest_decision_reason",
            "pulse_regime": "pulse_regime",
            "pulse_health": "pulse_health",
            "tick_health": "tick_health",
            "tick_age_sec": "tick_age_sec",
            "brief_age_min": "brief_age_min",
            "ai_action": "ai_action",
            "ai_confidence": "ai_confidence",
        }.items():
            if feature.get(key) in (None, "") and live_row.get(source_key) not in (None, ""):
                feature[key] = live_row.get(source_key)

    trade_label = _choose_trade_payload(trade_label, live_trade)

    snapshot_age_min = _minutes_old(str(snapshot.get("ts") or live_row.get("generated_at") or ""))
    decision_age_min = _minutes_old(str(feature.get("ts") or "")) or snapshot_age_min
    pulse_regime = str(feature.get("pulse_regime") or pulse.get("regime") or live_row.get("pulse_regime") or "unknown")
    pulse_health = feature.get("pulse_health")
    if pulse_health is None:
        pulse_health = pulse.get("health_score") if pulse else live_row.get("pulse_health")
    tick_health = str(feature.get("tick_health") or pulse_components.get("tick_health") or live_row.get("tick_health") or "unknown")
    tick_age_sec = feature.get("tick_age_sec")
    if tick_age_sec is None:
        tick_age_sec = pulse_components.get("tick_age_sec") if pulse_components else live_row.get("tick_age_sec")
    brief_age_min = feature.get("brief_age_min")
    if brief_age_min is None:
        brief_age_min = live_row.get("brief_age_min")
    if brief_age_min is None:
        brief_age_min = _brief_age_minutes(brief_path)
    if brief_age_min is None:
        brief_age_min = pulse_components.get("brief_age_min")
    sentiment_stale = bool(
        feature.get("sentiment_stale")
        if feature.get("sentiment_stale") is not None
        else pulse_components.get("sentiment_stale")
    )

    data_quality_status = "healthy"
    quality_flags: list[str] = []
    if pulse_regime == "danger":
        data_quality_status = "degraded"
        quality_flags.append("pulse danger")
    if tick_health in {"dead", "stale"}:
        data_quality_status = "degraded"
        quality_flags.append(f"tick {tick_health}")
    if (snapshot_age_min or 0) >= 60:
        data_quality_status = "degraded"
        quality_flags.append("snapshot stale")
    if brief_age_min is not None and float(brief_age_min or 0) >= 45:
        data_quality_status = "degraded"
        quality_flags.append("brief stale")
    if sentiment_stale:
        quality_flags.append("sentiment stale")
    if str(live_row.get("data_quality_status") or "").lower() == "degraded" and data_quality_status != "degraded":
        data_quality_status = "degraded"
        quality_flags.append("supabase degraded")

    return {
        "data_quality_status": data_quality_status,
        "quality_flags": quality_flags,
        "runtime_data_dir": str(data_dir.name),
        "runtime_logs_dir": str(logs_dir.name),
        "bot_state": snapshot.get("state") or feature.get("bot_state") or live_row.get("bot_state") or "unknown",
        "price": (
            live_tick.get("price")
            or snapshot.get("price")
            or feature.get("price")
            or feature.get("live_tick_price")
        ),
        "price_ts": live_tick.get("timestamp") or live_tick.get("written_at") or snapshot.get("ts"),
        "direction": snapshot.get("direction") or feature.get("direction") or live_row.get("position_side"),
        "entry_signal": snapshot.get("entry_signal") or feature.get("entry_signal") or live_row.get("entry_signal"),
        "quality_tier": snapshot.get("quality_tier") or feature.get("quality_tier") or live_row.get("quality_tier"),
        "route_tier": feature.get("route_tier") or snapshot.get("route_tier") or live_row.get("route_tier"),
        "decision_reason": feature.get("reason") or live_row.get("latest_decision_reason") or snapshot.get("last_action"),
        "decision_age_min": decision_age_min,
        "snapshot_age_min": snapshot_age_min,
        "pulse_regime": pulse_regime,
        "pulse_health": pulse_health,
        "tick_health": tick_health,
        "tick_age_sec": tick_age_sec,
        "brief_age_min": brief_age_min,
        "sentiment_stale": sentiment_stale,
        "gates_pass": feature.get("gates_pass") if feature.get("gates_pass") is not None else snapshot.get("gates_pass"),
        "ai_action": feature.get("ai_action") or live_row.get("ai_action"),
        "ai_confidence": feature.get("ai_confidence") or live_row.get("ai_confidence"),
        "last_trade": trade_label if trade_label else None,
        "telemetry_source": "supabase" if live_row else "local",
        "public_system_state": live_row.get("public_system_state"),
        "public_setup_state": live_row.get("public_setup_state"),
        "public_market_climate": live_row.get("public_market_climate"),
        "public_tick_status": live_row.get("public_tick_status"),
        "public_data_status": live_row.get("public_data_status"),
        "public_decision_label": live_row.get("public_decision_label"),
        "public_pressure_note": live_row.get("public_pressure_note"),
        "public_status_blurb": live_row.get("public_status_blurb"),
        "public_decision_age_label": live_row.get("public_decision_age_label"),
        "public_brief_age_label": live_row.get("public_brief_age_label"),
        "public_price_age_label": live_row.get("public_price_age_label"),
    }


def _collect_blackjack_watchtower_data() -> dict:
    try:
        from blackjack.catalog import resolve_gem_package_config
        from blackjack.checkout_bridge import bridge_enabled as blackjack_bridge_enabled
        from blackjack.checkout_bridge import package_checkout_ready
        from blackjack.models import AdRewardLog, GameSession, GemPackage, GemPurchase, PlayerProfile
    except Exception as exc:
        logger.debug("Blackjack watchtower skipped: %s", exc)
        return {
            "data_quality_status": "unknown",
            "quality_flags": ["blackjack app unavailable"],
            "stream_status": "pilot",
            "integrity_mode": "unknown",
            "monetization_status": "unknown",
        }

    now = timezone.now()
    today = now.date()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    hour_ago = now - timedelta(hours=1)

    settled_sessions = GameSession.objects.exclude(outcome="")
    sessions_today = settled_sessions.filter(played_at__date=today)
    sessions_24h = settled_sessions.filter(played_at__gte=day_ago)
    sessions_1h = settled_sessions.filter(played_at__gte=hour_ago)
    last_session = settled_sessions.order_by("-played_at").first()

    total_players = PlayerProfile.objects.count()
    active_players_24h = PlayerProfile.objects.filter(last_played__gte=day_ago).count()
    active_players_7d = PlayerProfile.objects.filter(last_played__gte=week_ago).count()
    vip_players = PlayerProfile.objects.filter(is_vip=True).count()
    ad_rewards_today = (
        AdRewardLog.objects.filter(reward_date=today).aggregate(total=Sum("chips_awarded"))["total"]
        or 0
    )
    ad_reward_claims_today = AdRewardLog.objects.filter(reward_date=today).count()
    active_packages = [
        package
        for package in GemPackage.objects.filter(is_active=True).order_by("price_usd")
        if resolve_gem_package_config(package).get("is_active", True)
    ]
    active_gem_packages = len(active_packages)
    stripe_ready_packages = sum(
        1 for package in active_packages if package_checkout_ready(package)
    )
    paid_purchases = GemPurchase.objects.filter(status="paid")
    purchases_today = paid_purchases.filter(verified_at__date=today)
    purchases_30d = paid_purchases.filter(verified_at__gte=month_ago)
    gem_revenue_today_cents = purchases_today.aggregate(total=Sum("amount_cents"))["total"] or 0
    gem_revenue_30d_cents = purchases_30d.aggregate(total=Sum("amount_cents"))["total"] or 0
    gem_purchases_today = purchases_today.count()
    wagered_today = sessions_today.aggregate(total=Sum("bet_chips"))["total"] or 0
    chips_delta_today = sessions_today.aggregate(total=Sum("chips_delta"))["total"] or 0
    integrity_rejections_today = BusinessEvent.objects.filter(
        source="blackjack",
        status="failed",
        event_type__in=[
            "blackjack_duplicate_settlement",
            "blackjack_result_invalid_payload",
            "blackjack_result_value_mismatch",
            "blackjack_result_outcome_mismatch",
        ],
        created_at__date=today,
    ).count()

    total_sessions = settled_sessions.count()
    server_auth_sessions = settled_sessions.exclude(shoe_seed="").exclude(action_log=[]).count()
    legacy_sessions = max(0, total_sessions - server_auth_sessions)
    checkout_configured = blackjack_bridge_enabled() or bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())

    if total_sessions == 0:
        integrity_mode = "provisioned"
    elif legacy_sessions == 0:
        integrity_mode = "server_authoritative"
    else:
        integrity_mode = "mixed"

    monetization_status = "ready"
    if not checkout_configured or stripe_ready_packages == 0:
        monetization_status = "not_ready"
    elif stripe_ready_packages < active_gem_packages:
        monetization_status = "partial"
    data_quality_status = "healthy"
    quality_flags: list[str] = []

    if total_players and not sessions_24h.exists():
        data_quality_status = "degraded"
        quality_flags.append("no settled hands in 24h")
    if not checkout_configured:
        data_quality_status = "degraded"
        quality_flags.append("checkout bridge not configured")
    if stripe_ready_packages < active_gem_packages:
        data_quality_status = "degraded"
        quality_flags.append("some gem packages are not checkout-ready")
    if integrity_rejections_today:
        data_quality_status = "degraded"
        quality_flags.append(f"{integrity_rejections_today} settlement rejection(s) today")
    if integrity_mode == "mixed":
        data_quality_status = "degraded"
        quality_flags.append(f"{legacy_sessions} legacy hand(s) missing server-auth metadata")

    stream_status = "pilot"
    if sessions_24h.exists():
        stream_status = "active"
    elif total_players:
        stream_status = "watch"
    if data_quality_status == "degraded" and stream_status != "pilot":
        stream_status = "watch"

    return {
        "generated_at": now.isoformat(),
        "data_quality_status": data_quality_status,
        "quality_flags": quality_flags,
        "stream_status": stream_status,
        "integrity_mode": integrity_mode,
        "monetization_status": monetization_status,
        "total_players": total_players,
        "active_players_24h": active_players_24h,
        "active_players_7d": active_players_7d,
        "hands_today": sessions_today.count(),
        "hands_24h": sessions_24h.count(),
        "hands_1h": sessions_1h.count(),
        "wagered_today": wagered_today,
        "chips_delta_today": chips_delta_today,
        "ad_rewards_today": ad_rewards_today,
        "ad_reward_claims_today": ad_reward_claims_today,
        "vip_players": vip_players,
        "active_gem_packages": active_gem_packages,
        "stripe_ready_packages": stripe_ready_packages,
        "checkout_configured": checkout_configured,
        "gem_purchases_today": gem_purchases_today,
        "gem_revenue_today_usd": round(gem_revenue_today_cents / 100, 2),
        "gem_revenue_30d_usd": round(gem_revenue_30d_cents / 100, 2),
        "integrity_rejections_today": integrity_rejections_today,
        "last_hand": (
            {
                "played_at": last_session.played_at.isoformat(),
                "outcome": last_session.outcome,
                "chips_delta": last_session.chips_delta,
                "bet_chips": last_session.bet_chips,
                "player_value": last_session.player_value,
                "dealer_value": last_session.dealer_value,
            }
            if last_session
            else None
        ),
        "controls": [
            "duplicate settlement blocked",
            "server-authoritative shoe and action log",
            (
                "Supabase Stripe checkout bridge"
                if blackjack_bridge_enabled()
                else "native Stripe checkout verification"
            ) if checkout_configured else "Stripe checkout awaiting live bridge",
        ],
    }


def ensure_default_streams() -> None:
    for stream in DEFAULT_STREAMS:
        RevenueStream.objects.get_or_create(
            slug=stream["slug"],
            defaults=stream,
        )


def upsert_revenue_stream(slug: str, **updates) -> RevenueStream:
    ensure_default_streams()
    stream = RevenueStream.objects.get(slug=slug)
    for key, value in updates.items():
        setattr(stream, key, value)
    if not stream.last_event_at:
        stream.last_event_at = timezone.now()
    stream.save()
    return stream


def record_event(
    event_type: str,
    source: str,
    summary: str,
    *,
    entity_type: str = "",
    entity_id: str = "",
    status: str = "info",
    priority: str = "medium",
    revenue_impact_usd=Decimal("0.00"),
    requires_approval: bool = False,
    owner_agent: str = "",
    payload: dict | None = None,
) -> BusinessEvent:
    payload = payload or {}
    event = BusinessEvent.objects.create(
        event_type=event_type,
        source=source,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        priority=priority,
        revenue_impact_usd=revenue_impact_usd,
        requires_approval=requires_approval,
        owner_agent=owner_agent,
        summary=summary,
        payload=payload,
    )
    _write_jsonl(
        EVENT_LOG,
        {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "source": event.source,
            "status": event.status,
            "priority": event.priority,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "revenue_impact_usd": str(event.revenue_impact_usd),
            "requires_approval": event.requires_approval,
            "summary": event.summary,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        },
    )
    return event


def record_alert(
    summary: str,
    *,
    source: str,
    detail: str = "",
    severity: str = "warning",
    state: str = "open",
    alert_key: str = "",
    entity_type: str = "",
    entity_id: str = "",
    requires_approval: bool = False,
    payload: dict | None = None,
    related_event: BusinessEvent | None = None,
) -> BusinessAlert:
    payload = payload or {}
    if alert_key:
        existing = BusinessAlert.objects.filter(alert_key=alert_key, state="open").first()
        if existing:
            existing.summary = summary or existing.summary
            existing.detail = detail or existing.detail
            existing.severity = severity or existing.severity
            existing.payload = payload or existing.payload
            existing.requires_approval = requires_approval
            existing.related_event = related_event or existing.related_event
            existing.save(
                update_fields=[
                    "summary",
                    "detail",
                    "severity",
                    "payload",
                    "requires_approval",
                    "related_event",
                ]
            )
            return existing

    alert = BusinessAlert.objects.create(
        alert_key=alert_key,
        severity=severity,
        state=state,
        source=source,
        summary=summary,
        detail=detail,
        entity_type=entity_type,
        entity_id=entity_id,
        requires_approval=requires_approval,
        payload=payload,
        related_event=related_event,
    )
    _write_jsonl(
        ALERT_LOG,
        {
            "severity": alert.severity,
            "state": alert.state,
            "source": alert.source,
            "summary": alert.summary,
            "detail": alert.detail,
            "entity_type": alert.entity_type,
            "entity_id": alert.entity_id,
            "requires_approval": alert.requires_approval,
            "created_at": alert.created_at.isoformat(),
        },
    )
    return alert


def resolve_alert(alert_key: str) -> None:
    now = timezone.now()
    BusinessAlert.objects.filter(alert_key=alert_key, state__in=["open", "acknowledged"]).update(
        state="resolved",
        resolved_at=now,
    )


def _sync_broker_stream() -> None:
    try:
        from broker_ops.models import BrokerMatch, CommissionRecord, Deal, LeadProfile, OfferListing
        from broker_ops.services import get_commission_summary
    except Exception as exc:
        logger.debug("Broker OS sync skipped: %s", exc)
        return

    summary = get_commission_summary()
    today = timezone.now().date()
    month_ago = timezone.now() - timedelta(days=30)
    earned_today = (
        CommissionRecord.objects.filter(record_type="earned", created_at__date=today)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    earned_30d = (
        CommissionRecord.objects.filter(record_type="earned", created_at__gte=month_ago)
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    pending_pipeline = (
        Deal.objects.filter(stage__in=["intro", "negotiating", "contracted", "active"])
        .aggregate(total=Sum("commission_due"))["total"]
        or Decimal("0.00")
    )
    pending_matches = BrokerMatch.objects.filter(status__in=["pending", "approved"]).count()
    hot_leads = LeadProfile.objects.filter(intent="hot", unsubscribed=False).count()
    active_offers = OfferListing.objects.filter(status="active").count()
    status = "active" if pending_matches or pending_pipeline else "pilot"

    upsert_revenue_stream(
        "broker_os",
        status=status,
        cash_today_usd=earned_today,
        cash_30d_usd=earned_30d,
        pending_pipeline_usd=pending_pipeline,
        mrr_usd=Decimal("0.00"),
        last_event_at=timezone.now(),
        metadata={
            "active_offers": active_offers,
            "hot_leads": hot_leads,
            "pending_matches": pending_matches,
            "closed_won": summary.get("closed_won", 0),
            "active_deals": summary.get("active_deals", 0),
        },
        notes=(
            f"{active_offers} active offers, {hot_leads} hot leads, "
            f"{pending_matches} open matches, ${summary.get('unpaid_balance', 0):.2f} unpaid balance."
        ),
    )


def _sync_hive_stream() -> None:
    try:
        from hive.models import HiveSession
    except Exception as exc:
        logger.debug("Hive stream sync skipped: %s", exc)
        return

    now = timezone.now()
    last_session = HiveSession.objects.order_by("-created_at").first()
    recent_sessions = HiveSession.objects.filter(created_at__gte=now - timedelta(days=7)).count()
    last_event_at = last_session.created_at if last_session else None
    status = "active" if recent_sessions else "pilot"
    notes = f"{recent_sessions} hive sessions in the last 7 days."
    upsert_revenue_stream(
        "hive_mind_saas",
        status=status,
        last_event_at=last_event_at,
        metadata={"recent_sessions_7d": recent_sessions},
        notes=notes,
    )


def _sync_trading_stream() -> None:
    report = WORKSPACE / "09_DASHBOARD" / "reports" / "profit_scoreboard.md"
    cash_today = Decimal("0.00")
    if report.exists():
        text = report.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "**Net PnL:" in line:
                cleaned = line.split("$")[-1].replace("*", "").strip()
                try:
                    cash_today = Decimal(cleaned.replace("+", ""))
                except Exception:
                    cash_today = Decimal("0.00")
                break

    watchtower = _collect_trading_watchtower_data()
    bot_state = str(watchtower.get("bot_state") or "unknown")
    quality_tier = str(watchtower.get("quality_tier") or "")
    pulse_regime = str(watchtower.get("pulse_regime") or "unknown")
    pulse_health = int(watchtower.get("pulse_health") or 0)
    tick_health = str(watchtower.get("tick_health") or "unknown")
    sentiment_stale = bool(watchtower.get("sentiment_stale"))
    brief_age_min = watchtower.get("brief_age_min")
    decision_reason = str(watchtower.get("decision_reason") or "")
    route_tier = str(watchtower.get("route_tier") or "")
    snapshot_age_min = watchtower.get("snapshot_age_min")
    data_quality_status = str(watchtower.get("data_quality_status") or "healthy")
    last_trade = watchtower.get("last_trade") or {}

    status = "pilot"
    if data_quality_status == "degraded":
        status = "watch"
    elif bot_state in {"READY", "IN_TRADE", "IN_TRADE_EXITING"}:
        status = "active"

    notes_parts = [
        f"Bot state: {bot_state}",
        f"Pulse: {pulse_regime or 'unknown'} ({pulse_health})",
    ]
    if quality_tier:
        notes_parts.append(f"Quality tier: {quality_tier}")
    if route_tier:
        notes_parts.append(f"Route tier: {route_tier}")
    if snapshot_age_min is not None:
        notes_parts.append(f"Snapshot age: {snapshot_age_min}m")
    if brief_age_min is not None:
        notes_parts.append(f"Brief age: {brief_age_min}m")
    if tick_health and tick_health != "unknown":
        notes_parts.append(f"Tick: {tick_health}")
    if decision_reason:
        notes_parts.append(f"Decision: {decision_reason}")

    upsert_revenue_stream(
        "trading_intelligence",
        status=status,
        cash_today_usd=cash_today,
        cash_30d_usd=cash_today,
        last_event_at=timezone.now(),
        metadata={
            "bot_state": bot_state,
            "quality_tier": quality_tier,
            "pulse_regime": pulse_regime,
            "pulse_health": pulse_health,
            "tick_health": tick_health,
            "snapshot_age_min": snapshot_age_min,
            "brief_age_min": brief_age_min,
            "sentiment_stale": sentiment_stale,
            "gates_pass": watchtower.get("gates_pass"),
            "entry_signal": watchtower.get("entry_signal"),
            "route_tier": route_tier,
            "decision_reason": decision_reason,
            "data_quality_status": data_quality_status,
            "last_trade_status": last_trade.get("status"),
            "last_trade_pnl_usd": last_trade.get("pnl_usd"),
            "telemetry_source": watchtower.get("telemetry_source"),
        },
        notes=" | ".join(notes_parts),
    )

    if data_quality_status == "degraded":
        degraded_severity = "error" if tick_health == "dead" or (snapshot_age_min or 0) >= 60 else "warning"
        record_alert(
            summary="XLM bot health degraded",
            source="xlm_bot",
            severity=degraded_severity,
            alert_key="xlm_bot:health:degraded",
            entity_type="workflow",
            entity_id="xlm_bot",
            detail="Pulse danger, stale brief, dead tick, or stale snapshot detected in xlm_bot telemetry.",
            payload={
                "pulse_regime": pulse_regime,
                "pulse_health": pulse_health,
                "tick_health": tick_health,
                "snapshot_age_min": snapshot_age_min,
                "brief_age_min": brief_age_min,
                "decision_reason": decision_reason,
                "telemetry_source": watchtower.get("telemetry_source"),
            },
        )
    else:
        resolve_alert("xlm_bot:health:degraded")


def _sync_blackjack_stream() -> None:
    watchtower = _collect_blackjack_watchtower_data()
    vip_players = int(watchtower.get("vip_players") or 0)
    hands_24h = int(watchtower.get("hands_24h") or 0)
    active_gem_packages = int(watchtower.get("active_gem_packages") or 0)
    stripe_ready_packages = int(watchtower.get("stripe_ready_packages") or 0)
    integrity_rejections_today = int(watchtower.get("integrity_rejections_today") or 0)
    gem_revenue_today_usd = Decimal(str(watchtower.get("gem_revenue_today_usd") or 0))
    gem_revenue_30d_usd = Decimal(str(watchtower.get("gem_revenue_30d_usd") or 0))
    gem_purchases_today = int(watchtower.get("gem_purchases_today") or 0)
    checkout_configured = bool(watchtower.get("checkout_configured"))

    notes_parts = [
        f"Players 24h: {watchtower.get('active_players_24h', 0)}",
        f"Hands 24h: {hands_24h}",
        f"Packages: {stripe_ready_packages}/{active_gem_packages} Stripe-ready",
        f"Integrity: {watchtower.get('integrity_mode')}",
        f"Gem sales today: ${gem_revenue_today_usd}",
    ]
    if watchtower.get("quality_flags"):
        notes_parts.append("Flags: " + ", ".join(watchtower["quality_flags"]))

    upsert_revenue_stream(
        "blackjack_arcade",
        status=watchtower.get("stream_status") or "pilot",
        cash_today_usd=gem_revenue_today_usd,
        cash_30d_usd=gem_revenue_30d_usd,
        mrr_usd=Decimal("4.99") * vip_players,
        pending_pipeline_usd=Decimal("0.00"),
        last_event_at=timezone.now(),
        metadata={
            "data_quality_status": watchtower.get("data_quality_status"),
            "integrity_mode": watchtower.get("integrity_mode"),
            "monetization_status": watchtower.get("monetization_status"),
            "hands_today": watchtower.get("hands_today"),
            "hands_24h": hands_24h,
            "hands_1h": watchtower.get("hands_1h"),
            "active_players_24h": watchtower.get("active_players_24h"),
            "active_players_7d": watchtower.get("active_players_7d"),
            "wagered_today": watchtower.get("wagered_today"),
            "chips_delta_today": watchtower.get("chips_delta_today"),
            "ad_rewards_today": watchtower.get("ad_rewards_today"),
            "ad_reward_claims_today": watchtower.get("ad_reward_claims_today"),
            "vip_players": vip_players,
            "stripe_ready_packages": stripe_ready_packages,
            "checkout_configured": checkout_configured,
            "gem_purchases_today": gem_purchases_today,
            "gem_revenue_today_usd": float(gem_revenue_today_usd),
            "gem_revenue_30d_usd": float(gem_revenue_30d_usd),
            "integrity_rejections_today": integrity_rejections_today,
            "controls": watchtower.get("controls"),
        },
        notes=" | ".join(notes_parts),
    )

    if watchtower.get("integrity_mode") == "mixed":
        record_alert(
            summary="Blackjack settlement is not fully server-authoritative",
            source="blackjack",
            severity="warning",
            alert_key="blackjack:integrity:client_auth",
            entity_type="game",
            entity_id="blackjack",
            detail=(
                "Blackjack now has server-auth gameplay, but some historical sessions still lack the "
                "shoe/action-log metadata expected by the watchtower."
            ),
            payload={"controls": watchtower.get("controls", [])},
        )
    else:
        resolve_alert("blackjack:integrity:client_auth")

    if (not checkout_configured) or stripe_ready_packages < active_gem_packages:
        record_alert(
            summary="Blackjack monetization is not Stripe-ready",
            source="blackjack",
            severity="warning",
            alert_key="blackjack:monetization:not_ready",
            entity_type="game",
            entity_id="blackjack",
            detail=(
                "Stripe checkout is not fully ready for blackjack gem packs. "
                f"Configured secret: {'yes' if checkout_configured else 'no'}. "
                f"Checkout-ready packages: {stripe_ready_packages} of {active_gem_packages}."
            ),
        )
    else:
        resolve_alert("blackjack:monetization:not_ready")

    if integrity_rejections_today > 0:
        record_alert(
            summary="Blackjack settlement rejections detected",
            source="blackjack",
            severity="error" if integrity_rejections_today >= 3 else "warning",
            alert_key="blackjack:integrity:rejections",
            entity_type="game",
            entity_id="blackjack",
            detail=f"{integrity_rejections_today} invalid or duplicate settlement attempt(s) were blocked today.",
            payload={"integrity_rejections_today": integrity_rejections_today},
        )
    else:
        resolve_alert("blackjack:integrity:rejections")

    if int(watchtower.get("total_players") or 0) > 0 and hands_24h == 0:
        record_alert(
            summary="Blackjack traffic is stalled",
            source="blackjack",
            severity="warning",
            alert_key="blackjack:traffic:stalled",
            entity_type="game",
            entity_id="blackjack",
            detail="Registered players exist, but there have been no settled blackjack hands in the last 24 hours.",
        )
    else:
        resolve_alert("blackjack:traffic:stalled")


def get_trading_watchtower() -> dict:
    ensure_default_streams()
    _sync_trading_stream()
    stream = RevenueStream.objects.filter(slug="trading_intelligence").first()
    open_alert = (
        BusinessAlert.objects.filter(alert_key="xlm_bot:health:degraded", state="open")
        .order_by("-created_at")
        .first()
    )
    watchtower = _collect_trading_watchtower_data()
    watchtower["stream_status"] = stream.status if stream else "pilot"
    watchtower["open_alert"] = (
        {
            "severity": open_alert.severity,
            "summary": open_alert.summary,
            "detail": open_alert.detail,
            "created_at": open_alert.created_at.isoformat(),
        }
        if open_alert
        else None
    )
    _write_json(TRADING_WATCHTOWER_STATUS, watchtower)
    return watchtower


def get_blackjack_watchtower() -> dict:
    ensure_default_streams()
    _sync_blackjack_stream()
    stream = RevenueStream.objects.filter(slug="blackjack_arcade").first()
    open_alerts = BusinessAlert.objects.filter(source="blackjack", state="open").order_by("-created_at")[:4]
    watchtower = _collect_blackjack_watchtower_data()
    watchtower["stream_status"] = stream.status if stream else watchtower.get("stream_status") or "pilot"
    watchtower["open_alerts"] = [
        {
            "severity": alert.severity,
            "summary": alert.summary,
            "detail": alert.detail,
            "created_at": alert.created_at.isoformat(),
        }
        for alert in open_alerts
    ]
    _write_json(BLACKJACK_WATCHTOWER_STATUS, watchtower)
    return watchtower


def refresh_business_os() -> None:
    ensure_default_streams()
    _sync_broker_stream()
    _sync_hive_stream()
    get_trading_watchtower()
    get_blackjack_watchtower()


def get_ceo_snapshot() -> dict:
    refresh_business_os()

    now = timezone.now()
    today = now.date()
    events_today = BusinessEvent.objects.filter(created_at__date=today)
    cash_today = (
        RevenueStream.objects.aggregate(total=Sum("cash_today_usd"))["total"]
        or Decimal("0.00")
    )
    mrr = RevenueStream.objects.aggregate(total=Sum("mrr_usd"))["total"] or Decimal("0.00")
    affiliate_today = (
        RevenueStream.objects.filter(category="affiliate_commerce")
        .aggregate(total=Sum("cash_today_usd"))["total"]
        or Decimal("0.00")
    )
    pending_pipeline = (
        RevenueStream.objects.aggregate(total=Sum("pending_pipeline_usd"))["total"]
        or Decimal("0.00")
    )
    open_alerts = BusinessAlert.objects.filter(state="open")
    open_approvals = BusinessEvent.objects.filter(requires_approval=True, approved_at__isnull=True)

    status_counts = RevenueStream.objects.values("status").annotate(count=Count("id"))
    recent_events = BusinessEvent.objects.order_by("-created_at")[:12]
    recent_alerts = open_alerts.order_by("-created_at")[:10]
    streams = RevenueStream.objects.order_by("name")
    trading_watchtower = get_trading_watchtower()
    blackjack_watchtower = get_blackjack_watchtower()
    trading_reports = _read_recent_trading_reports()

    return {
        "cash_today": cash_today,
        "mrr_total": mrr,
        "affiliate_today": affiliate_today,
        "pending_pipeline": pending_pipeline,
        "failed_workflows": events_today.filter(status="failed").count(),
        "open_approvals": open_approvals.count(),
        "active_incidents": open_alerts.filter(severity__in=["error", "critical"]).count(),
        "events_today": events_today.count(),
        "recent_events": recent_events,
        "recent_alerts": recent_alerts,
        "streams": streams,
        "status_counts": {row["status"]: row["count"] for row in status_counts},
        "trading_watchtower": trading_watchtower,
        "blackjack_watchtower": blackjack_watchtower,
        "trading_reports": trading_reports,
    }
