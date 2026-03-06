from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from typing import Any, Optional


@dataclass(frozen=True)
class PLRLDecision:
    strategy: str
    action: str  # HOLD/RESCUE/EXIT/NO_RESCUE/UNKNOWN
    rescue_step: int
    max_rescues: int
    next_rescue_at: float | None
    fail_at: float
    add_contracts: int
    projected_mr_intraday: float | None
    projected_mr_overnight: float | None
    mr_intraday: float | None
    mr_overnight: float | None
    active_mr: float | None
    active_window: str  # intraday/overnight/unknown
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        if isinstance(x, dict) and "value" in x:
            x = x.get("value")
        v = float(x)
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except Exception:
        return None


def _now_et(now_utc: datetime) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return now_utc


def _cutoff_dt_et(now_et: datetime, cutoff: time) -> datetime:
    return now_et.replace(hour=cutoff.hour, minute=cutoff.minute, second=0, microsecond=0)


def _window_active(now_utc: datetime, cutoff_et: time = time(16, 0)) -> str:
    now_et = _now_et(now_utc)
    t = now_et.timetz().replace(tzinfo=None)
    if t < time(8, 0) or t >= cutoff_et:
        return "overnight"
    return "intraday"


def _extract_window_measures(balance_summary: dict) -> dict[str, Any]:
    bs = balance_summary or {}
    root = bs.get("balance_summary") if isinstance(bs, dict) else {}
    root = root if isinstance(root, dict) else {}

    intraday = root.get("intraday_margin_window_measure") or {}
    overnight = root.get("overnight_margin_window_measure") or {}
    total_usd = root.get("total_usd_balance") or root.get("total_funds_for_margin")

    im_i = _num(intraday.get("initial_margin") if isinstance(intraday, dict) else None)
    mm_i = _num(intraday.get("maintenance_margin") if isinstance(intraday, dict) else None)
    im_o = _num(overnight.get("initial_margin") if isinstance(overnight, dict) else None)
    mm_o = _num(overnight.get("maintenance_margin") if isinstance(overnight, dict) else None)
    c = _num(total_usd)

    def _factor(mm: float | None, im: float | None) -> float:
        if mm is None or im is None or im <= 0:
            return 1.0
        f = mm / im
        if f <= 0 or f != f:
            return 1.0
        return max(0.25, min(1.0, f))

    return {
        "total_funds_for_margin": c,
        "intraday": {"initial_margin": im_i, "maintenance_margin": mm_i, "mm_factor": _factor(mm_i, im_i)},
        "overnight": {"initial_margin": im_o, "maintenance_margin": mm_o, "mm_factor": _factor(mm_o, im_o)},
    }


def _margin_rate_from_product(details: dict, *, direction: str, window: str) -> float | None:
    fpd = (details or {}).get("future_product_details") or {}
    d = (direction or "").lower()
    side_key = "short_margin_rate" if "short" in d else "long_margin_rate"
    rate_obj = fpd.get("intraday_margin_rate") if window == "intraday" else fpd.get("overnight_margin_rate")
    if not isinstance(rate_obj, dict):
        return None
    return _num(rate_obj.get(side_key))


def _contract_size(details: dict) -> float | None:
    fpd = (details or {}).get("future_product_details") or {}
    return _num(fpd.get("contract_size"))


def _project_mr_after_add(
    *,
    balance_summary: dict,
    product_details: dict,
    direction: str,
    price: float,
    add_contracts: int,
) -> tuple[float | None, float | None]:
    meas = _extract_window_measures(balance_summary or {})
    c = meas.get("total_funds_for_margin")
    if not c or c <= 0:
        return None, None

    cs = _contract_size(product_details or {})
    if not cs or cs <= 0 or add_contracts <= 0 or price <= 0:
        return None, None

    notional = float(price) * float(cs) * float(add_contracts)

    out = []
    for w in ("intraday", "overnight"):
        m = meas.get(w) or {}
        mm_cur = _num((m or {}).get("maintenance_margin"))
        factor = float((m or {}).get("mm_factor") or 1.0)
        rate = _margin_rate_from_product(product_details or {}, direction=direction, window=w)
        if mm_cur is None or rate is None:
            out.append(None)
            continue
        initial_req = notional * float(rate)
        mm_add = initial_req * factor
        mr = (mm_cur + mm_add) / float(c)
        out.append(mr)
    return out[0], out[1]


def compute_initial_contracts_plrl3(
    *,
    balance_summary: dict,
    product_details: dict,
    direction: str,
    price: float,
    mr_max_allowed: float,
    total_multiplier: int,
) -> tuple[int, dict[str, Any]]:
    """
    Compute an initial contract count sized for the worst-case ladder (initial + rescues).

    Interprets the sizing law as a maintenance-margin budget:
      budget_mm = total_funds_for_margin * mr_max_allowed / total_multiplier
      initial_contracts <= floor(budget_mm / mm_per_contract_worst_window)
    """
    meas = _extract_window_measures(balance_summary or {})
    c = meas.get("total_funds_for_margin")
    notes: list[str] = []
    if not c or c <= 0:
        return 0, {"notes": ["missing_total_funds_for_margin"]}

    cs = _contract_size(product_details or {})
    if not cs or cs <= 0 or price <= 0:
        return 0, {"notes": ["missing_contract_size_or_price"]}

    budget_mm = float(c) * float(mr_max_allowed) / float(max(1, int(total_multiplier or 1)))
    notional_1 = float(price) * float(cs) * 1.0

    mm_per: dict[str, float | None] = {}
    for w in ("intraday", "overnight"):
        m = meas.get(w) or {}
        factor = float((m or {}).get("mm_factor") or 1.0)
        rate = _margin_rate_from_product(product_details or {}, direction=direction, window=w)
        if rate is None:
            mm_per[w] = None
            continue
        initial_req = notional_1 * float(rate)
        mm_per[w] = initial_req * factor

    candidates = [v for v in mm_per.values() if isinstance(v, (int, float)) and v and v > 0]
    if not candidates:
        return 0, {"notes": ["missing_margin_rates"], "budget_mm": budget_mm, "mm_per_contract": mm_per}
    worst = max(candidates)
    if worst <= 0:
        return 0, {"notes": ["bad_mm_per_contract"], "budget_mm": budget_mm, "mm_per_contract": mm_per}

    initial = int(budget_mm // worst)
    if initial <= 0:
        notes.append("budget_too_small_for_1_contract")
    return max(0, initial), {
        "notes": notes,
        "budget_mm": budget_mm,
        "mm_per_contract": mm_per,
        "worst_mm_per_contract": worst,
    }


def evaluate_plrl3(
    *,
    balance_summary: dict,
    product_details: dict,
    direction: str,
    price: float,
    initial_contracts: int,
    rescue_step: int,
    max_rescues: int,
    mr_triggers: list[float],
    add_multipliers: list[int],
    fail_mr: float,
    max_projected_mr: float,
    overnight_guard_mr: float,
    now_utc: datetime,
    cutoff_et: time = time(16, 0),
    disable_rescues_pre_cutoff_min: int = 30,
    allow_rescues: bool = True,
) -> PLRLDecision:
    notes: list[str] = []
    meas = _extract_window_measures(balance_summary or {})
    c = meas.get("total_funds_for_margin")

    mr_i = None
    mr_o = None
    try:
        if c and c > 0:
            mm_i = _num((meas.get("intraday") or {}).get("maintenance_margin"))
            mm_o = _num((meas.get("overnight") or {}).get("maintenance_margin"))
            mr_i = (mm_i / c) if (mm_i is not None) else None
            mr_o = (mm_o / c) if (mm_o is not None) else None
    except Exception:
        mr_i, mr_o = None, None

    window = _window_active(now_utc, cutoff_et=cutoff_et) if now_utc else "unknown"
    active_mr = mr_o if window == "overnight" else mr_i
    if active_mr is None:
        active_mr = mr_i if mr_i is not None else mr_o
        window = "unknown"

    # Pre-cutoff disable rule (intraday only).
    now_et = _now_et(now_utc)
    cutoff = _cutoff_dt_et(now_et, cutoff_et)
    if now_et > cutoff:
        cutoff = cutoff + timedelta(days=1)
    mins_to_cutoff = int((cutoff - now_et).total_seconds() // 60)
    if window != "overnight" and mins_to_cutoff <= int(disable_rescues_pre_cutoff_min or 0):
        allow_rescues = False
        notes.append(f"rescues_disabled_pre_cutoff_{mins_to_cutoff}m")

    if active_mr is None:
        return PLRLDecision(
            strategy="PLRL-3",
            action="UNKNOWN",
            rescue_step=int(rescue_step or 0),
            max_rescues=int(max_rescues or 0),
            next_rescue_at=None,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=None,
            active_window=window,
            notes=notes + ["missing_active_mr"],
        )

    if active_mr >= float(fail_mr):
        return PLRLDecision(
            strategy="PLRL-3",
            action="EXIT",
            rescue_step=int(rescue_step or 0),
            max_rescues=int(max_rescues or 0),
            next_rescue_at=None,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + ["fail_mr_reached"],
        )

    step = int(rescue_step or 0)
    if step >= int(max_rescues or 0):
        return PLRLDecision(
            strategy="PLRL-3",
            action="HOLD",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=None,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + ["max_rescues_used"],
        )

    next_at = None
    try:
        next_at = float(mr_triggers[step]) if step < len(mr_triggers) else None
    except Exception:
        next_at = None

    if not allow_rescues:
        return PLRLDecision(
            strategy="PLRL-3",
            action="NO_RESCUE",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=next_at,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + ["rescues_disabled"],
        )

    if next_at is None or active_mr < next_at:
        return PLRLDecision(
            strategy="PLRL-3",
            action="HOLD",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=next_at,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes,
        )

    mult = None
    try:
        mult = int(add_multipliers[step]) if step < len(add_multipliers) else None
    except Exception:
        mult = None
    if mult is None or mult <= 0:
        return PLRLDecision(
            strategy="PLRL-3",
            action="UNKNOWN",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=next_at,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + ["missing_add_multiplier"],
        )

    try:
        init_c = int(initial_contracts or 0)
    except Exception:
        init_c = 0
    if init_c <= 0:
        return PLRLDecision(
            strategy="PLRL-3",
            action="UNKNOWN",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=next_at,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=None,
            projected_mr_overnight=None,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + ["missing_initial_contracts"],
        )

    add_contracts = int(init_c * mult)
    proj_i, proj_o = _project_mr_after_add(
        balance_summary=balance_summary,
        product_details=product_details,
        direction=direction,
        price=price,
        add_contracts=add_contracts,
    )

    guard_notes = []
    if proj_i is not None and proj_i >= float(max_projected_mr):
        guard_notes.append("projected_intraday_too_high")
    if proj_o is not None:
        if window == "overnight":
            if proj_o >= float(max_projected_mr):
                guard_notes.append("projected_overnight_too_high")
        else:
            if proj_o >= float(overnight_guard_mr):
                guard_notes.append("projected_overnight_guard_hit")

    if guard_notes:
        return PLRLDecision(
            strategy="PLRL-3",
            action="EXIT",
            rescue_step=step,
            max_rescues=int(max_rescues or 0),
            next_rescue_at=next_at,
            fail_at=float(fail_mr),
            add_contracts=0,
            projected_mr_intraday=proj_i,
            projected_mr_overnight=proj_o,
            mr_intraday=mr_i,
            mr_overnight=mr_o,
            active_mr=float(active_mr),
            active_window=window,
            notes=notes + guard_notes,
        )

    return PLRLDecision(
        strategy="PLRL-3",
        action="RESCUE",
        rescue_step=step,
        max_rescues=int(max_rescues or 0),
        next_rescue_at=next_at,
        fail_at=float(fail_mr),
        add_contracts=int(add_contracts),
        projected_mr_intraday=proj_i,
        projected_mr_overnight=proj_o,
        mr_intraday=mr_i,
        mr_overnight=mr_o,
        active_mr=float(active_mr),
        active_window=window,
        notes=notes + ["triggered"],
    )

