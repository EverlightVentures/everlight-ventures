"""Runtime policy layer derived from the Ai_Brain transcript corpus."""
from __future__ import annotations

from datetime import datetime
from typing import Any

try:
    from .brain_knowledge import get_ai_brain_status
except ImportError:
    from brain_knowledge import get_ai_brain_status


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_percent(value: Any) -> float:
    raw = _safe_float(value)
    if raw > 1:
        raw = raw / 100.0
    return _clamp(raw)


def _topic_count(status: dict[str, Any], topic_name: str) -> int:
    for item in status.get("top_topics") or []:
        if item.get("topic") == topic_name:
            return int(item.get("count") or 0)
    return 0


def policy_snapshot(refresh: bool = False) -> dict[str, Any]:
    status = get_ai_brain_status(refresh=refresh)
    traits = status.get("cognitive_profile") or {}
    adaptability = _normalize_percent(traits.get("adaptability", 0))
    emotional = _normalize_percent(traits.get("emotional_regulation", 0))
    decisive = _normalize_percent(traits.get("decisiveness", 0))
    logical = _normalize_percent(traits.get("logical_rigor", 0))
    self_healing = _normalize_percent(traits.get("self_healing", 0))

    event_sensing = _clamp(
        (_topic_count(status, "event_based_sensing") / max(_topic_count(status, "spiking_control"), 1)) * 0.8
        + decisive * 0.2
    )
    plasticity = _clamp((adaptability * 0.6) + (self_healing * 0.4))
    continual_learning = _clamp((adaptability * 0.7) + (logical * 0.3))

    return {
        "knowledge_mode": status.get("knowledge_mode", "knowledge pending"),
        "state_regulation_score": emotional,
        "plasticity_score": plasticity,
        "self_healing_score": self_healing,
        "decisive_score": decisive,
        "logical_score": logical,
        "event_sensing_score": event_sensing,
        "continual_learning_score": continual_learning,
        "top_topics": status.get("top_topics") or [],
        "last_refreshed_at": datetime.utcnow().isoformat(),
    }


def recommend_match_priority(context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    snapshot = policy_snapshot()
    decisive = snapshot["decisive_score"]
    logical = snapshot["logical_score"]
    plasticity = snapshot["plasticity_score"]

    match_score = _normalize_percent(context.get("match_score", 0))
    intent_boost = {"hot": 1.0, "warm": 0.65, "cold": 0.35}.get(str(context.get("lead_intent", "warm")).lower(), 0.5)
    budget_signal = _clamp(_safe_float(context.get("budget_signal", 0.5)))
    category_fit = _clamp(_safe_float(context.get("category_fit", 0.5)))

    priority_score = _clamp(
        (match_score * 0.45)
        + (intent_boost * 0.2)
        + (budget_signal * 0.1)
        + (category_fit * 0.1)
        + (decisive * 0.1)
        + (logical * 0.05)
    )
    learning_mode = "exploit" if priority_score >= 0.72 else "explore" if plasticity >= 0.65 else "stabilize"

    return {
        "priority_score": round(priority_score, 4),
        "priority_band": "critical" if priority_score >= 0.8 else "high" if priority_score >= 0.65 else "normal",
        "learning_mode": learning_mode,
        "brain_policy": snapshot,
    }


def recommend_outreach(context: dict[str, Any] | None = None, ml_decision: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    ml_decision = ml_decision or {}
    snapshot = policy_snapshot()

    state_reg = snapshot["state_regulation_score"]
    self_healing = snapshot["self_healing_score"]
    decisive = snapshot["decisive_score"]
    logical = snapshot["logical_score"]
    event_sensing = snapshot["event_sensing_score"]
    plasticity = snapshot["plasticity_score"]

    lead_score = _normalize_percent(context.get("lead_score", 0))
    urgency = _clamp(_safe_float(context.get("urgency", 0.4)))
    days_since_contact = _safe_float(context.get("days_since_contact", 3))
    total_touches = _safe_float(context.get("total_touches", 1))
    sentiment = _clamp((_safe_float(context.get("last_reply_sentiment", 0)) + 1.0) / 2.0)
    industry_match = _clamp(_safe_float(context.get("industry_match", 0.5)))
    recent_bounces = _safe_float(context.get("recent_bounces", 0))
    recent_unsubscribes = _safe_float(context.get("recent_unsubscribes", 0))
    recent_failures = _safe_float(context.get("recent_failures", 0))
    ml_send = 1.0 if ml_decision.get("should_outreach") else 0.0
    ml_conf = _clamp(_safe_float(ml_decision.get("confidence", 0.5)))

    recovery_load = _clamp((recent_bounces * 0.2) + (recent_unsubscribes * 0.25) + (recent_failures * 0.15))
    self_healing_mode = recovery_load > (0.65 - (self_healing * 0.3))
    wait_signal = _clamp((days_since_contact / 10.0) + (0.05 * total_touches))

    send_pressure = _clamp(
        (lead_score * 0.24)
        + (urgency * 0.16)
        + (industry_match * 0.1)
        + (wait_signal * 0.1)
        + (decisive * 0.12)
        + (logical * 0.08)
        + (state_reg * 0.06)
        + (event_sensing * 0.04)
        + (plasticity * 0.04)
        + (ml_send * 0.04)
        + (ml_conf * 0.02)
        + (sentiment * 0.05)
        - (recovery_load * 0.18)
    )

    if self_healing_mode and recovery_load > 0.75:
        action = "pause"
        should_send_now = False
        followup_delay_days = 7
    elif send_pressure >= 0.7:
        action = "send_now"
        should_send_now = True
        followup_delay_days = 0
    elif send_pressure >= 0.5:
        action = "review_then_send"
        should_send_now = bool(ml_decision.get("should_outreach", True))
        followup_delay_days = 1
    else:
        action = "defer"
        should_send_now = False
        followup_delay_days = 3 if days_since_contact < 7 else 2

    focus = {
        "trading": round((snapshot["logical_score"] * 0.45) + (snapshot["decisive_score"] * 0.25), 4),
        "broker": round((send_pressure * 0.6) + (plasticity * 0.2) + (event_sensing * 0.2), 4),
        "consulting": round((state_reg * 0.5) + (logical * 0.3) + (industry_match * 0.2), 4),
    }

    return {
        "should_send_now": should_send_now,
        "action": action,
        "send_pressure": round(send_pressure, 4),
        "followup_delay_days": int(followup_delay_days),
        "self_healing_mode": self_healing_mode,
        "recovery_load": round(recovery_load, 4),
        "attention_allocation": focus,
        "brain_policy": snapshot,
    }


def recommend_reply_action(
    classification: str,
    reply_analysis: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reply_analysis = reply_analysis or {}
    context = context or {}
    snapshot = policy_snapshot()

    sentiment = _safe_float(reply_analysis.get("reply_sentiment", 0.0))
    urgency = _clamp(_safe_float(reply_analysis.get("urgency", 0.0)))
    objections = set(reply_analysis.get("objections") or [])
    interested = bool(reply_analysis.get("is_interested")) or classification == "interested"

    decisive = snapshot["decisive_score"]
    logical = snapshot["logical_score"]
    state_reg = snapshot["state_regulation_score"]
    self_healing = snapshot["self_healing_score"]

    escalation_score = _clamp(
        (0.4 if interested else 0.0)
        + (0.18 * urgency)
        + (0.16 * decisive)
        + (0.12 * logical)
        + (0.08 * state_reg)
        - (0.1 if "budget" in objections else 0.0)
        - (0.1 if "timing" in objections else 0.0)
        + max(0.0, sentiment) * 0.15
    )

    if classification == "unsubscribe":
        action = "pause_outreach"
        priority = "low"
    elif classification == "bounce":
        action = "repair_contact_path"
        priority = "normal" if self_healing >= 0.5 else "low"
    elif interested and escalation_score >= 0.72:
        action = "dispatch_now"
        priority = "critical"
    elif interested:
        action = "send_proposal"
        priority = "high"
    elif "authority" in objections:
        action = "request_intro_to_decision_maker"
        priority = "high"
    elif "budget" in objections:
        action = "send_roi_case_study"
        priority = "normal"
    elif "timing" in objections:
        action = "schedule_followup_30d"
        priority = "normal"
    elif sentiment < -0.35:
        action = "cooldown_and_review"
        priority = "normal"
    else:
        action = reply_analysis.get("next_action", "follow_up_3d")
        priority = "normal"

    return {
        "recommended_action": action,
        "priority": priority,
        "escalation_score": round(escalation_score, 4),
        "brain_policy": snapshot,
    }
