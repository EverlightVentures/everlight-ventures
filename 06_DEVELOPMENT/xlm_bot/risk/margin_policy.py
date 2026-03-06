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
        # reject NaN/inf
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

    We intentionally avoid hard-coding a single schema because Coinbase can vary field names.
    """
    bs = balance_summary or {}
    root = bs.get("balance_summary") if isinstance(bs, dict) else {}
    root = root if isinstance(root, dict) else {}

    # Total funds for margin: Coinbase CFM uses "total_usd_balance" in the balance summary.
    total_funds = (
        root.get("total_funds_for_margin")
        or root.get("total_usd_balance")
        or root.get("total_funds")
        or _find_key_recursive(bs, "total_funds_for_margin")
        or _find_key_recursive(bs, "total_usd_balance")
        or _find_key_recursive(bs, "total_funds")
    )

    # Maintenance margin requirement: often exposed via margin window measures.
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

    # If MR isn't directly provided, compute from window measures when possible.
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

    # Final fallback: if we only have a single maintenance margin requirement, compute a single MR.
    if mr_i_v is None and mm_req_v is not None and total_funds_v and total_funds_v > 0:
        mr_i_v = mm_req_v / total_funds_v
        computed_from = computed_from or "maintenance_margin/total_usd_balance"

    # CFM wallet balance (derivatives only, NOT total_usd which includes primary)
    cfm_usd = root.get("cfm_usd_balance") or _find_key_recursive(bs, "cfm_usd_balance")
    cfm_usd_v = _num(cfm_usd)

    return {
        "maintenance_margin_requirement": mm_req_v,
        "total_funds_for_margin": total_funds_v,
        "cfm_usd_balance": cfm_usd_v,
        "mr_intraday": mr_i_v,
        "mr_overnight": mr_o_v,
        "mr_computed_from": computed_from,
    }


def _now_et(now_utc: datetime) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        # If tz data is missing, fall back to UTC while still functioning.
        return now_utc


def _cutoff_dt_et(now_et: datetime, cutoff: time) -> datetime:
    return now_et.replace(hour=cutoff.hour, minute=cutoff.minute, second=0, microsecond=0)


def evaluate_margin_policy(
    balance_summary: dict,
    *,
    now_utc: datetime,
    cutoff_et: time = time(16, 0),
    intraday_start_et: time = time(8, 0),
    pre_cutoff_minutes: int = 30,
    safe_lt: float = 0.80,
    warning_lt: float = 0.90,
    danger_lt: float = 0.95,
    liquidation_gte: float = 1.00,
) -> PolicyDecision:
    """
    Coinbase CDE cross-margin policy.

    Coinbase CDE intraday window: 8:00 AM ET → 4:00 PM ET (8 hrs) = 5 AM-1 PM PT.
    Overnight: 4:00 PM ET → 8:00 AM ET (16 hrs) = 1 PM-5 AM PT — higher margin.
    Cutoff = 4:00 PM ET (1:00 PM PT). Intraday resumes at 8:00 AM ET (5:00 AM PT).

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
                "margin_window": "unknown",
            },
        )

    # Determine which window is active.
    #
    # Coinbase CDE: intraday 8AM-4PM ET (5AM-1PM PT) = 8 hrs.
    # Overnight: 4PM-8AM ET (1PM-5AM PT) = 16 hrs — higher margin requirements.
    t_et = now_et.timetz().replace(tzinfo=None)
    intraday_end = cutoff_et

    # Handle both cases: normal (start < end) and midnight wrap (start > end).
    if intraday_start_et > intraday_end:
        overnight_active = (t_et >= intraday_end) and (t_et < intraday_start_et)
    else:
        overnight_active = (t_et < intraday_start_et) or (t_et >= intraday_end)

    # Determine "active risk".
    active_mr = None
    active_label = "intraday"
    if overnight_active:
        active_mr = mr_o if mr_o is not None else mr_i
        active_label = "overnight" if mr_o is not None else "intraday"
        reasons.append("overnight_window_active")
    else:
        active_mr = mr_i if mr_i is not None else mr_o

    # If within pre-cutoff window, use the worse of intraday/overnight as the effective risk.
    if (not overnight_active) and mins_to_cutoff <= pre_cutoff_minutes:
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

    if mins_to_cutoff <= pre_cutoff_minutes:
        reasons.append(f"cutoff_soon_{mins_to_cutoff}m")

    margin_window = "overnight" if overnight_active else ("pre_cutoff" if mins_to_cutoff <= pre_cutoff_minutes else "intraday")
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
            "intraday_start_et": intraday_start_et.strftime("%H:%M"),
            "mins_to_cutoff": mins_to_cutoff,
            "margin_window": margin_window,
        },
    )
