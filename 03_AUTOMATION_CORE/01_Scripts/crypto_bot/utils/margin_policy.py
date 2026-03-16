from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Any, Optional


@dataclass(frozen=True)
class PolicyDecision:
    tier: str  # SAFE/WARNING/DANGER/LIQUIDATION/UNKNOWN
    actions: list[str]
    reasons: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        if isinstance(x, dict) and "value" in x:
            x = x.get("value")
        v = float(x)
        # Reject NaN/inf.
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except Exception:
        return None


def _find_key_recursive(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            got = _find_key_recursive(v, key)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for it in obj:
            got = _find_key_recursive(it, key)
            if got is not None:
                return got
    return None


def _extract_margin_metrics(balance_summary: dict) -> dict[str, Any]:
    """
    Best-effort extractor for Coinbase CFM balance summary fields.

    Coinbase can vary field names; we keep this tolerant so the guard keeps running even
    if the API response shape changes slightly.
    """
    bs = balance_summary or {}
    root = bs.get("balance_summary") if isinstance(bs, dict) else {}
    root = root if isinstance(root, dict) else {}

    total_funds = (
        root.get("total_funds_for_margin")
        or root.get("total_usd_balance")
        or root.get("total_funds")
        or _find_key_recursive(bs, "total_funds_for_margin")
        or _find_key_recursive(bs, "total_usd_balance")
        or _find_key_recursive(bs, "total_funds")
    )

    intraday_measure = root.get("intraday_margin_window_measure") or _find_key_recursive(bs, "intraday_margin_window_measure") or {}
    overnight_measure = root.get("overnight_margin_window_measure") or _find_key_recursive(bs, "overnight_margin_window_measure") or {}

    mm_req = (
        root.get("maintenance_margin_requirement")
        or root.get("maintenance_margin")
        or (intraday_measure.get("maintenance_margin") if isinstance(intraday_measure, dict) else None)
        or _find_key_recursive(bs, "maintenance_margin_requirement")
        or _find_key_recursive(bs, "maintenance_margin")
    )

    mr_intraday = (
        root.get("intraday_margin_ratio")
        or root.get("intraday_margin_ratio_value")
        or root.get("intraday_margin_health")
        or (intraday_measure.get("margin_ratio") if isinstance(intraday_measure, dict) else None)
        or _find_key_recursive(bs, "intraday_margin_ratio")
        or _find_key_recursive(bs, "intraday_margin_health")
    )
    mr_overnight = (
        root.get("overnight_margin_ratio")
        or root.get("overnight_margin_ratio_value")
        or root.get("overnight_margin_health")
        or (overnight_measure.get("margin_ratio") if isinstance(overnight_measure, dict) else None)
        or _find_key_recursive(bs, "overnight_margin_ratio")
        or _find_key_recursive(bs, "overnight_margin_health")
    )

    mm_req_v = _num(mm_req)
    total_funds_v = _num(total_funds)
    mr_i_v = _num(mr_intraday)
    mr_o_v = _num(mr_overnight)

    computed_from = None
    if total_funds_v and total_funds_v > 0:
        try:
            if mr_i_v is None and isinstance(intraday_measure, dict) and intraday_measure.get("maintenance_margin") is not None:
                mm_i = _num(intraday_measure.get("maintenance_margin"))
                if mm_i is not None:
                    mr_i_v = mm_i / total_funds_v
                    computed_from = "intraday_maintenance_margin/total_usd_balance"
            if mr_o_v is None and isinstance(overnight_measure, dict) and overnight_measure.get("maintenance_margin") is not None:
                mm_o = _num(overnight_measure.get("maintenance_margin"))
                if mm_o is not None:
                    mr_o_v = mm_o / total_funds_v
                    computed_from = computed_from or "overnight_maintenance_margin/total_usd_balance"
        except Exception:
            pass

    if mr_i_v is None and mm_req_v is not None and total_funds_v and total_funds_v > 0:
        mr_i_v = mm_req_v / total_funds_v
        computed_from = computed_from or "maintenance_margin/total_usd_balance"

    return {
        "maintenance_margin_requirement": mm_req_v,
        "total_funds_for_margin": total_funds_v,
        "mr_intraday": mr_i_v,
        "mr_overnight": mr_o_v,
        "mr_computed_from": computed_from,
    }


def _now_et(now_utc: datetime) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return now_utc


def _cutoff_dt_et(now_et: datetime, cutoff: time) -> datetime:
    return now_et.replace(hour=cutoff.hour, minute=cutoff.minute, second=0, microsecond=0)


def evaluate_margin_policy(
    balance_summary: dict,
    *,
    now_utc: datetime,
    cutoff_et: time = time(16, 0),
    pre_cutoff_minutes: int = 30,
    safe_lt: float = 0.80,
    warning_lt: float = 0.90,
    danger_lt: float = 0.95,
    liquidation_gte: float = 1.00,
) -> PolicyDecision:
    """
    Coinbase-style margin ratio policy (cross margin):
      MR = maintenance_margin_requirement / total_funds_for_margin
      MR >= 1.0 => liquidation begins
    """
    metrics = _extract_margin_metrics(balance_summary or {})
    now_et = _now_et(now_utc)
    cutoff = _cutoff_dt_et(now_et, cutoff_et)
    if now_et > cutoff:
        cutoff = cutoff + timedelta(days=1)
    mins_to_cutoff = int((cutoff - now_et).total_seconds() // 60)

    mr_i = metrics.get("mr_intraday")
    mr_o = metrics.get("mr_overnight")
    reasons: list[str] = []

    if mr_i is None and mr_o is None:
        reasons.append("missing_margin_ratio_fields")
        return PolicyDecision(
            tier="UNKNOWN",
            actions=["ALLOW_ENTRY"],
            reasons=reasons,
            metrics={
                **metrics,
                "now_et": now_et.isoformat(),
                "cutoff_et": cutoff_et.strftime("%H:%M"),
                "mins_to_cutoff": mins_to_cutoff,
            },
        )

    # Intraday window is typically 08:00-16:00 ET; outside of that, overnight applies.
    intraday_start = time(8, 0)
    intraday_end = cutoff_et
    t_et = now_et.timetz().replace(tzinfo=None)
    overnight_active = (t_et < intraday_start) or (t_et >= intraday_end)

    active_mr = None
    active_label = "intraday"
    if overnight_active:
        active_mr = mr_o if mr_o is not None else mr_i
        active_label = "overnight" if mr_o is not None else "intraday"
        reasons.append("overnight_window_active")
    else:
        active_mr = mr_i if mr_i is not None else mr_o

    # If within pre-cutoff window, use the worse of intraday/overnight.
    if (not overnight_active) and mins_to_cutoff <= int(pre_cutoff_minutes or 0):
        if mr_o is not None and (active_mr is None or mr_o > active_mr):
            active_mr = mr_o
            active_label = "overnight"
            reasons.append("pre_cutoff_using_overnight_risk")

    if active_mr is None:
        active_mr = mr_i if mr_i is not None else mr_o

    tier = "SAFE"
    if active_mr is None:
        tier = "UNKNOWN"
    elif active_mr >= liquidation_gte:
        tier = "LIQUIDATION"
    elif active_mr >= warning_lt:
        tier = "DANGER"
    elif active_mr >= safe_lt:
        tier = "WARNING"

    actions: list[str] = []
    if tier in ("SAFE", "UNKNOWN"):
        actions.append("ALLOW_ENTRY")
    if tier in ("WARNING", "DANGER", "LIQUIDATION"):
        actions.append("BLOCK_ENTRY")
    if tier in ("DANGER", "LIQUIDATION"):
        actions += ["REDUCE_ONLY", "CANCEL_OPEN_ORDERS"]
    if active_mr is not None and active_mr >= danger_lt:
        actions.append("DE_RISK")
    if tier == "LIQUIDATION":
        actions += ["EXIT_ALL", "HALT_TRADING"]

    if mins_to_cutoff <= int(pre_cutoff_minutes or 0):
        reasons.append(f"cutoff_soon_{mins_to_cutoff}m")

    return PolicyDecision(
        tier=tier,
        actions=list(dict.fromkeys(actions)),
        reasons=reasons,
        metrics={
            **metrics,
            "active_mr": active_mr,
            "active_mr_source": active_label,
            "now_et": now_et.isoformat(),
            "cutoff_et": cutoff_et.strftime("%H:%M"),
            "mins_to_cutoff": mins_to_cutoff,
        },
    )

