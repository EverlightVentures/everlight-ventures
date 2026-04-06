"""
Pipeline Integration API -- connects ML models to Everlight business systems.

Provides simple function calls that broker_daily_orchestrator.py,
wholesale_hive_pipeline.py, and the XLM bot can use to get ML predictions.

All functions are designed to be called from any Python script:
    from neuromorphic.pipeline_api import score_lead, predict_trade, should_outreach

Free & open source: scikit-learn, numpy, joblib.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure neuromorphic package is importable
_pkg_dir = Path(__file__).parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

from ml_models import get_toolkit
from brain_policy import recommend_match_priority, recommend_outreach, recommend_reply_action

log = logging.getLogger(__name__)


def score_lead(lead: dict) -> float:
    """Score a broker lead 0-100. Drop-in for broker pipeline.

    Args:
        lead: Dict with keys like budget, urgency, company_size, etc.

    Returns:
        Score 0-100 (higher = better lead)
    """
    toolkit = get_toolkit()
    return toolkit.score_lead(lead)


def predict_trade(trade_data: dict) -> dict:
    """Predict trade outcome. Drop-in for XLM bot.

    Args:
        trade_data: Dict with keys like v4_score, rsi, trend_strength, etc.

    Returns:
        Dict with prediction (win/loss), confidence, win_probability
    """
    toolkit = get_toolkit()
    return toolkit.predict_trade(trade_data)


def should_outreach(lead_context: dict) -> dict:
    """Decide if outreach should happen now. Drop-in for broker orchestrator.

    Args:
        lead_context: Dict with lead_score, days_since_contact, etc.

    Returns:
        Dict with should_outreach (bool), confidence
    """
    toolkit = get_toolkit()
    ml_decision = toolkit.should_outreach(lead_context)
    policy = recommend_outreach(lead_context, ml_decision=ml_decision)
    final_should_outreach = bool(
        ml_decision.get("should_outreach", True)
        and policy.get("action") != "pause"
    )
    if policy.get("action") == "send_now":
        final_should_outreach = True
    elif policy.get("action") == "defer":
        final_should_outreach = False
    result = dict(ml_decision)
    result.update({
        "should_outreach": final_should_outreach,
        "brain_policy": policy,
        "followup_delay_days": policy.get("followup_delay_days", 0),
        "reason": policy.get("action", result.get("reason", "brain_policy")),
    })
    return result


def predict_conversion(deal: dict) -> float:
    """Predict consulting deal conversion probability.

    Args:
        deal: Dict with lead_source, discovery_score, etc.

    Returns:
        Probability 0-1
    """
    toolkit = get_toolkit()
    return toolkit.predict_conversion(deal)


def train_from_trades_csv(csv_path: str | Path) -> dict:
    """Train the trade predictor from a trades.csv file.

    Call this periodically (e.g., daily) to retrain on latest data.
    """
    toolkit = get_toolkit()
    return toolkit._train_trade_model(Path(csv_path))


def train_from_leads_json(json_path: str | Path) -> dict:
    """Train the lead scorer from a leads JSON file."""
    toolkit = get_toolkit()
    return toolkit._train_lead_model(Path(json_path))


def get_ml_status() -> dict:
    """Get status of all ML models."""
    toolkit = get_toolkit()
    return toolkit.get_all_status()


def score_lead_with_policy(lead: dict) -> dict:
    """Lead score with transcript-derived policy metadata."""
    ml_score = score_lead(lead)
    context = dict(lead)
    context["match_score"] = ml_score
    context["lead_intent"] = lead.get("intent", "warm")
    context["budget_signal"] = _normalize_budget(lead)
    context["category_fit"] = 1.0 if lead.get("categories_needed") else 0.5
    policy = recommend_match_priority(context)
    adjustment = (policy["priority_score"] - 0.5) * 20.0
    return {
        "ml_score": ml_score,
        "brain_adjustment": round(adjustment, 2),
        "final_score": round(max(0.0, min(100.0, ml_score + adjustment)), 2),
        "brain_policy": policy,
    }


def recommend_reply_path(classification: str, reply_analysis: dict | None = None, context: dict | None = None) -> dict:
    """Expose transcript-derived reply escalation guidance."""
    return recommend_reply_action(classification, reply_analysis=reply_analysis, context=context)


def _normalize_budget(lead: dict) -> float:
    budget = 0.0
    for key in ("budget_max", "budget_min", "budget"):
        value = lead.get(key)
        if value is not None:
            try:
                budget = max(budget, float(value))
            except Exception:
                continue
    return max(0.0, min(1.0, budget / 50000.0))


# CLI interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Everlight ML Pipeline API")
    parser.add_argument("command", choices=["status", "score-lead", "predict-trade", "train-trades"])
    parser.add_argument("--data", type=str, help="JSON data or file path")
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(get_ml_status(), indent=2, default=str))

    elif args.command == "score-lead":
        data = json.loads(args.data) if args.data else {"budget": 20000, "urgency": 0.7}
        print(f"Lead score: {score_lead(data):.1f}")

    elif args.command == "predict-trade":
        data = json.loads(args.data) if args.data else {"v4_score": 65, "rsi": 45, "rr_ratio": 2.0}
        print(json.dumps(predict_trade(data), indent=2, default=str))

    elif args.command == "train-trades":
        if not args.data:
            print("Error: --data must be path to trades.csv")
            sys.exit(1)
        print(json.dumps(train_from_trades_csv(args.data), indent=2, default=str))
