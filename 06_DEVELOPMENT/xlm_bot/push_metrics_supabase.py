#!/usr/bin/env python3
from __future__ import annotations

"""Push XLM bot metrics to Supabase for the everlightventures.io /dashboard page.

Runs on Oracle via cron every minute alongside export_metrics.py:
  * * * * * cd /home/opc/xlm-bot && venv/bin/python push_metrics_supabase.py

Supabase table: xlm_bot_metrics (upsert by row id=1 -- single live row)
Supabase table: xlm_bot_trades (append -- timeseries for equity curve)

Env vars (set in /home/opc/xlm-bot/.env or cron environment):
  SUPABASE_URL       -- https://jdqqmsmwmbsnlnstyavl.supabase.co
  SUPABASE_ANON_KEY  -- eyJ... (anon key)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from public_watchtower import build_public_watchtower_fields

# --- Config ---
BASE = Path(os.environ.get("CRYPTO_BOT_DIR", os.path.dirname(os.path.abspath(__file__))))
METRICS_FILE = BASE / "data" / "metrics.json"
TRADES_CSV = BASE / "logs" / "trades.csv"
LAST_PUSH_FILE = BASE / "data" / "last_supabase_push.json"
FEATURE_LATEST_FILE = BASE / "data" / "feature_snapshot_latest.json"
TRADE_LABELS_FILE = BASE / "logs" / "trade_labels.jsonl"
REPORT_HISTORY_FILE = BASE / "logs" / "report_history.jsonl"
MARKET_INTEL_STATE_FILE = BASE / "data" / "market_intel_state.json"
MARKET_INTEL_RUNS_FILE = BASE / "logs" / "market_intel_runs.jsonl"
MARKET_INTEL_DOCUMENTS_FILE = BASE / "logs" / "market_intel_documents.jsonl"
MARKET_INTEL_CLAIMS_FILE = BASE / "logs" / "market_intel_claims.jsonl"

def _load_runtime_env() -> dict[str, str]:
    values: dict[str, str] = {}
    runtime_env = Path(os.environ.get("RUNTIME_ENV_FILE", BASE / "secrets" / "runtime.env"))
    try:
        if runtime_env.exists():
            for raw in runtime_env.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except Exception:
        pass
    return values

RUNTIME_ENV = _load_runtime_env()

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    RUNTIME_ENV.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
)
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or RUNTIME_ENV.get("SUPABASE_SERVICE_ROLE_KEY")
    or RUNTIME_ENV.get("SUPABASE_SECRET_KEY")
    or os.environ.get("SUPABASE_KEY")
    or os.environ.get(
        "SUPABASE_ANON_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
    )
)

# Daily profit goals
DAILY_TARGET_USD = 100.0
DAILY_FLOOR_USD  = 25.0

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}


def _minutes_old(ts_value: str) -> float | None:
    if not ts_value:
        return None
    try:
        parsed = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - parsed).total_seconds() / 60.0, 1)
    except Exception:
        return None


def load_metrics() -> dict:
    try:
        return json.loads(METRICS_FILE.read_text())
    except Exception as e:
        print(f"[push] Failed to load metrics.json: {e}")
        return {}


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text())
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def load_last_push() -> dict:
    try:
        return json.loads(LAST_PUSH_FILE.read_text())
    except Exception:
        return {}


def save_last_push(data: dict) -> None:
    try:
        LAST_PUSH_FILE.write_text(json.dumps(data, default=str))
    except Exception:
        pass


def load_feature_latest() -> dict:
    return load_json(FEATURE_LATEST_FILE)


def build_live_row(metrics: dict, feature: dict | None = None) -> dict:
    """Build the single live-state row for xlm_bot_metrics."""
    feature = feature or {}
    pnl = float(metrics.get("exchange_pnl_today_usd") or metrics.get("pnl_today_usd") or 0)
    floor_hit = pnl >= DAILY_FLOOR_USD
    target_hit = pnl >= DAILY_TARGET_USD
    goal_pct = round(min(pnl / DAILY_TARGET_USD, 1.0) * 100, 1) if DAILY_TARGET_USD > 0 else 0

    # Sentiment gate status from sentiment_cache if available
    sentiment_score = None
    sentiment_label = "unknown"
    try:
        sc = BASE / "data" / "sentiment_cache.json"
        if sc.exists():
            sc_data = json.loads(sc.read_text())
            sentiment_score = sc_data.get("score")
            sentiment_label = sc_data.get("classification", "unknown")
    except Exception:
        pass

    data_quality_status = "healthy"
    if str(feature.get("tick_health") or "").lower() in {"dead", "stale"}:
        data_quality_status = "degraded"
    if str(feature.get("pulse_regime") or "").lower() == "danger":
        data_quality_status = "degraded"
    if feature.get("brief_age_min") not in (None, "") and float(feature.get("brief_age_min") or 0) >= 45:
        data_quality_status = "degraded"

    row = {
        "id": 1,  # single upsert row
        "generated_at": metrics.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "heartbeat_age_s": metrics.get("heartbeat_age_s"),
        "bot_alive": metrics.get("bot_alive", False),
        "session_id": metrics.get("session_id", "unknown"),
        "day": metrics.get("day"),
        "equity_usd": metrics.get("exchange_equity_usd") or metrics.get("equity_start_usd", 0),
        "pnl_today_usd": round(pnl, 2),
        "net_pnl_today_usd": round(float(metrics.get("net_pnl_after_fees_usd") or pnl), 2),
        "trades_today": metrics.get("trades_today", 0),
        "wins": metrics.get("wins", 0),
        "losses": metrics.get("losses", 0),
        "win_rate_pct": metrics.get("win_rate_pct", 0),
        "total_fees_usd": metrics.get("total_fees_usd", 0),
        "vol_state": metrics.get("vol_state", "unknown"),
        "recovery_mode": metrics.get("recovery_mode", "NORMAL"),
        "open_position": metrics.get("open_position", False),
        "position_side": metrics.get("position_side"),
        "safe_mode": metrics.get("safe_mode", False),
        "consecutive_losses": metrics.get("consecutive_losses", 0),
        "consecutive_wins": metrics.get("consecutive_wins", 0),
        "spot_usdc": metrics.get("spot_usdc", 0),
        # Daily goal fields for /dashboard display
        "daily_target_usd": DAILY_TARGET_USD,
        "daily_floor_usd": DAILY_FLOOR_USD,
        "floor_hit": floor_hit,
        "target_hit": target_hit,
        "goal_progress_pct": goal_pct,
        # Market sentiment
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "bot_state": metrics.get("bot_state") or feature.get("bot_state"),
        "quality_tier": metrics.get("quality_tier") or feature.get("quality_tier"),
        "route_tier": metrics.get("route_tier") or feature.get("route_tier"),
        "entry_signal": metrics.get("entry_signal") or feature.get("entry_signal"),
        "latest_decision_reason": metrics.get("latest_decision_reason") or feature.get("reason"),
        "signal_product_id": metrics.get("signal_product_id") or feature.get("signal_product_id"),
        "spot_reference_product_id": metrics.get("spot_reference_product_id") or feature.get("spot_reference_product_id"),
        "contract_mark_price": metrics.get("contract_mark_price") or feature.get("contract_mark_price"),
        "contract_price_change_24h_pct": metrics.get("contract_price_change_24h_pct") or feature.get("contract_price_change_24h_pct"),
        "orderbook_depth_bias": metrics.get("orderbook_depth_bias") or feature.get("orderbook_depth_bias"),
        "orderbook_imbalance": metrics.get("orderbook_imbalance") or feature.get("orderbook_imbalance"),
        "orderbook_spread_bps": metrics.get("orderbook_spread_bps") or feature.get("orderbook_spread_bps"),
        "liquidation_signal_source": metrics.get("liquidation_signal_source") or feature.get("liquidation_signal_source"),
        "liquidation_feed_live": metrics.get("liquidation_feed_live") if metrics.get("liquidation_feed_live") is not None else feature.get("liquidation_feed_live"),
        "liquidation_bias": metrics.get("liquidation_bias") or feature.get("liquidation_bias"),
        "liquidation_events_5m": metrics.get("liquidation_events_5m") or feature.get("liquidation_events_5m"),
        "liquidation_notional_5m_usd": metrics.get("liquidation_notional_5m_usd") or feature.get("liquidation_notional_5m_usd"),
        "futures_relativity_bias": metrics.get("futures_relativity_bias") or feature.get("futures_relativity_bias"),
        "futures_relativity_confidence": metrics.get("futures_relativity_confidence") or feature.get("futures_relativity_confidence"),
        "cross_venue_oi_change_pct": metrics.get("cross_venue_oi_change_pct") or feature.get("cross_venue_oi_change_pct"),
        "cross_venue_funding_bias": metrics.get("cross_venue_funding_bias") or feature.get("cross_venue_funding_bias"),
        "pulse_regime": metrics.get("pulse_regime") or feature.get("pulse_regime"),
        "pulse_health": metrics.get("pulse_health") or feature.get("pulse_health"),
        "tick_health": metrics.get("tick_health") or feature.get("tick_health"),
        "tick_age_sec": metrics.get("tick_age_sec") or feature.get("tick_age_sec"),
        "brief_age_min": metrics.get("brief_age_min") or feature.get("brief_age_min"),
        "news_risk": metrics.get("news_risk") or feature.get("news_risk"),
        "ai_action": metrics.get("ai_action") or feature.get("ai_action"),
        "ai_confidence": metrics.get("ai_confidence") or feature.get("ai_confidence"),
        "data_quality_status": data_quality_status,
    }
    row.update(
        build_public_watchtower_fields(
            {
                **row,
                "decision_reason": row.get("latest_decision_reason"),
                "decision_age_min": _minutes_old(str(feature.get("ts") or row.get("generated_at") or "")),
                "price_ts": row.get("generated_at"),
            }
        )
    )
    return row


def upsert_live_metrics(row: dict) -> bool:
    """Upsert the single live metrics row."""
    url = f"{SUPABASE_URL}/rest/v1/xlm_bot_metrics"
    payload = dict(row)
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if resp.status_code in (200, 201):
            return True
        if any(key.startswith("public_") for key in payload):
            legacy_payload = {key: value for key, value in payload.items() if not key.startswith("public_")}
            retry = requests.post(url, headers=HEADERS, json=legacy_payload, timeout=10)
            if retry.status_code in (200, 201):
                print("[push] upsert succeeded after dropping public_* fields; Supabase schema is not updated yet")
                return True
        print(f"[push] upsert failed {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[push] upsert error: {e}")
        return False


def append_timeseries(row: dict) -> bool:
    """Append a timeseries snapshot for the equity curve chart.
    Only pushes once per minute to avoid flooding.
    """
    last = load_last_push()
    last_ts = float(last.get("timeseries_ts", 0))
    if time.time() - last_ts < 55:
        return True  # skip, pushed recently

    ts_row = {
        "ts": row["generated_at"],
        "pnl_today_usd": row["pnl_today_usd"],
        "equity_usd": row["equity_usd"],
        "trades_today": row["trades_today"],
        "win_rate_pct": row["win_rate_pct"],
        "sentiment_score": row.get("sentiment_score"),
    }

    url = f"{SUPABASE_URL}/rest/v1/xlm_bot_timeseries"
    try:
        resp = requests.post(
            url,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=ts_row,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            last["timeseries_ts"] = time.time()
            save_last_push(last)
            return True
        print(f"[push] timeseries failed {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[push] timeseries error: {e}")
        return False


def append_feature_snapshot(feature: dict) -> bool:
    if not feature:
        return True
    last = load_last_push()
    if str(last.get("feature_ts") or "") == str(feature.get("ts") or ""):
        return True

    url = f"{SUPABASE_URL}/rest/v1/xlm_bot_feature_snapshots"
    try:
        resp = requests.post(
            url,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=feature,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            last["feature_ts"] = feature.get("ts")
            save_last_push(last)
            return True
        print(f"[push] feature snapshot failed {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[push] feature snapshot error: {e}")
        return False


def append_trade_labels() -> tuple[bool, int]:
    if not TRADE_LABELS_FILE.exists():
        return True, 0

    last = load_last_push()
    last_ts = str(last.get("trade_label_ts") or "")
    last_label_id = str(last.get("trade_label_id") or "")
    pending: list[dict] = []
    try:
        with TRADE_LABELS_FILE.open() as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                ts = str(row.get("ts") or "")
                label_id = str(row.get("label_id") or "")
                if not label_id:
                    continue
                if ts < last_ts:
                    continue
                if ts == last_ts and label_id <= last_label_id:
                    continue
                pending.append(row)
    except Exception as e:
        print(f"[push] trade label read error: {e}")
        return False, 0

    if not pending:
        return True, 0

    url = f"{SUPABASE_URL}/rest/v1/xlm_bot_trade_labels"
    try:
        resp = requests.post(
            url,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=pending,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            newest = pending[-1]
            last["trade_label_ts"] = newest.get("ts")
            last["trade_label_id"] = newest.get("label_id")
            save_last_push(last)
            return True, len(pending)
        print(f"[push] trade labels failed {resp.status_code}: {resp.text[:200]}")
        return False, 0
    except Exception as e:
        print(f"[push] trade labels error: {e}")
        return False, 0


def append_report_history() -> tuple[bool, int]:
    if not REPORT_HISTORY_FILE.exists():
        return True, 0

    last = load_last_push()
    last_ts = str(last.get("report_history_ts") or "")
    last_report_id = str(last.get("report_history_id") or "")
    pending: list[dict] = []
    try:
        with REPORT_HISTORY_FILE.open() as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                created_at = str(row.get("created_at") or "")
                report_id = str(row.get("report_id") or "")
                if not report_id:
                    continue
                if created_at < last_ts:
                    continue
                if created_at == last_ts and report_id <= last_report_id:
                    continue
                pending.append(row)
    except Exception as e:
        print(f"[push] report history read error: {e}")
        return False, 0

    if not pending:
        return True, 0

    url = f"{SUPABASE_URL}/rest/v1/xlm_bot_report_history"
    try:
        resp = requests.post(
            url,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=pending,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            newest = pending[-1]
            last["report_history_ts"] = newest.get("created_at")
            last["report_history_id"] = newest.get("report_id")
            save_last_push(last)
            return True, len(pending)
        print(f"[push] report history failed {resp.status_code}: {resp.text[:200]}")
        return False, 0
    except Exception as e:
        print(f"[push] report history error: {e}")
        return False, 0


def upsert_market_intel_state() -> tuple[bool, int]:
    if not MARKET_INTEL_STATE_FILE.exists():
        return True, 0
    payload = load_json(MARKET_INTEL_STATE_FILE)
    if not payload:
        return True, 0

    rows: list[dict] = []
    for key in ("intraday", "weekly"):
        state = payload.get(key)
        if not isinstance(state, dict):
            continue
        rows.append(
            {
                "state_key": key,
                "generated_at": state.get("generated_at") or payload.get("generated_at"),
                "research_kind": state.get("research_kind") or key,
                "source_mode": state.get("source_mode"),
                "macro_regime": state.get("macro_regime"),
                "directional_bias": state.get("directional_bias"),
                "xlm_bias": state.get("xlm_bias"),
                "confidence": state.get("confidence"),
                "review_score": state.get("review_score"),
                "summary": state.get("summary"),
                "window_label": state.get("window_label"),
                "payload": state.get("payload") or {},
            }
        )
    if not rows:
        return True, 0

    url = f"{SUPABASE_URL}/rest/v1/xlm_market_intel_state"
    try:
        resp = requests.post(url, headers=HEADERS, json=rows, timeout=10)
        if resp.status_code in (200, 201):
            return True, len(rows)
        print(f"[push] market intel state failed {resp.status_code}: {resp.text[:200]}")
        return False, 0
    except Exception as e:
        print(f"[push] market intel state error: {e}")
        return False, 0


def _append_jsonl_table(file_path: Path, *, table_name: str, last_ts_key: str, last_id_key: str, ts_field: str, id_field: str) -> tuple[bool, int]:
    if not file_path.exists():
        return True, 0

    last = load_last_push()
    last_ts = str(last.get(last_ts_key) or "")
    last_id = str(last.get(last_id_key) or "")
    pending_map: dict[str, dict] = {}
    try:
        with file_path.open() as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                row_ts = str(row.get(ts_field) or "")
                row_id = str(row.get(id_field) or "")
                if not row_id:
                    continue
                if row_ts < last_ts:
                    continue
                if row_ts == last_ts and row_id <= last_id:
                    continue
                existing = pending_map.get(row_id)
                if existing is None:
                    pending_map[row_id] = row
                    continue
                existing_ts = str(existing.get(ts_field) or "")
                if row_ts > existing_ts:
                    pending_map[row_id] = row
    except Exception as e:
        print(f"[push] {table_name} read error: {e}")
        return False, 0

    pending = sorted(
        pending_map.values(),
        key=lambda item: (str(item.get(ts_field) or ""), str(item.get(id_field) or "")),
    )

    if not pending:
        return True, 0

    url = f"{SUPABASE_URL}/rest/v1/{table_name}?on_conflict={id_field}"
    try:
        resp = requests.post(
            url,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=pending,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            newest = pending[-1]
            last[last_ts_key] = newest.get(ts_field)
            last[last_id_key] = newest.get(id_field)
            save_last_push(last)
            return True, len(pending)
        print(f"[push] {table_name} failed {resp.status_code}: {resp.text[:200]}")
        return False, 0
    except Exception as e:
        print(f"[push] {table_name} error: {e}")
        return False, 0


def append_market_intel_runs() -> tuple[bool, int]:
    return _append_jsonl_table(
        MARKET_INTEL_RUNS_FILE,
        table_name="xlm_market_intel_runs",
        last_ts_key="market_intel_run_ts",
        last_id_key="market_intel_run_id",
        ts_field="generated_at",
        id_field="run_id",
    )


def append_market_intel_documents() -> tuple[bool, int]:
    return _append_jsonl_table(
        MARKET_INTEL_DOCUMENTS_FILE,
        table_name="xlm_market_intel_documents",
        last_ts_key="market_intel_doc_ts",
        last_id_key="market_intel_doc_id",
        ts_field="collected_at",
        id_field="document_id",
    )


def append_market_intel_claims() -> tuple[bool, int]:
    return _append_jsonl_table(
        MARKET_INTEL_CLAIMS_FILE,
        table_name="xlm_market_intel_claims",
        last_ts_key="market_intel_claim_ts",
        last_id_key="market_intel_claim_id",
        ts_field="generated_at",
        id_field="claim_id",
    )


def run_push() -> int:
    metrics = load_metrics()
    if not metrics:
        print("[push] No metrics to push")
        return 1

    feature = load_feature_latest()
    row = build_live_row(metrics, feature)
    ok = upsert_live_metrics(row)
    ts_ok = append_timeseries(row)
    feature_ok = append_feature_snapshot(feature)
    labels_ok, label_count = append_trade_labels()
    reports_ok, report_count = append_report_history()
    intel_state_ok, intel_state_count = upsert_market_intel_state()
    intel_runs_ok, intel_run_count = append_market_intel_runs()
    intel_docs_ok, intel_doc_count = append_market_intel_documents()
    intel_claims_ok, intel_claim_count = append_market_intel_claims()

    pnl = row["pnl_today_usd"]
    print(
        f"[push] PnL=${pnl:.2f} | Goal {row['goal_progress_pct']}% | "
        f"Pulse: {row.get('pulse_regime')} ({row.get('pulse_health')}) | "
        f"Live: {'OK' if ok else 'FAIL'} | Timeseries: {'OK' if ts_ok else 'skip/FAIL'} | "
        f"Feature: {'OK' if feature_ok else 'FAIL'} | Labels: {label_count if labels_ok else 'FAIL'} | "
        f"Reports: {report_count if reports_ok else 'FAIL'} | "
        f"IntelState: {intel_state_count if intel_state_ok else 'FAIL'} | "
        f"IntelRuns: {intel_run_count if intel_runs_ok else 'FAIL'} | "
        f"IntelDocs: {intel_doc_count if intel_docs_ok else 'FAIL'} | "
        f"IntelClaims: {intel_claim_count if intel_claims_ok else 'FAIL'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run_push())
