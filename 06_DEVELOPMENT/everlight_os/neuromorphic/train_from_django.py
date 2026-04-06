"""Train ML models from real Django broker data on Oracle.

Run on Oracle: cd /home/opc/hive_django && python3 /home/opc/06_DEVELOPMENT/everlight_os/neuromorphic/train_from_django.py
"""
import os
import sys
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

# Add Django project to path
sys.path.insert(0, "/home/opc/hive_django")
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from broker_ops.models import LeadProfile, OutreachSequence
from django.db.models import Count
import numpy as np
from ml_models import get_toolkit


def train_lead_scorer():
    """Train LeadScorer on real broker lead data."""
    scored_leads = LeadProfile.objects.annotate(
        match_count=Count("matches")
    ).values(
        "id", "company", "intent", "budget_min", "budget_max",
        "company_size", "categories_needed", "lead_source", "match_count"
    )

    X_list = []
    y_list = []
    intent_map = {"hot": 0.9, "warm": 0.6, "cold": 0.3}

    for lead in scored_leads:
        budget = float(lead.get("budget_max") or lead.get("budget_min") or 0)
        intent = intent_map.get(str(lead.get("intent", "warm")).lower(), 0.5)
        matches = int(lead.get("match_count", 0))

        # Composite score: intent + budget + match activity
        score = min((intent * 40) + min(budget / 1000, 30) + min(matches * 2, 30), 100)

        cats = str(lead.get("categories_needed", "")).lower()
        is_tech = 1 if any(t in cats for t in ["saas", "tech", "software", "ai", "automation"]) else 0

        source = str(lead.get("lead_source", "")).lower()
        source_score = 0.8 if "referral" in source else 0.5 if "inbound" in source else 0.3

        features = [
            min(budget / 50000, 1.0),
            intent,
            min(float(lead.get("company_size") or 10) / 1000, 1.0),
            is_tech,
            0,
            intent * 0.8,
            0.3,
            0.4,
            intent * 0.7,
            source_score,
        ]
        X_list.append(features)
        y_list.append(score)

    X = np.array(X_list)
    y = np.array(y_list)
    print(f"LeadScorer: {len(X)} samples, score range {y.min():.1f}-{y.max():.1f}")

    if len(X) >= 10:
        toolkit = get_toolkit()
        metrics = toolkit.lead_scorer.train(X, y)
        print(f"  Trained: {json.dumps(metrics, default=str)}")
        return metrics
    return {"error": "insufficient_data"}


def train_outreach_optimizer():
    """Train OutreachOptimizer on real outreach sequence data."""
    seqs = OutreachSequence.objects.select_related("match").all()
    print(f"OutreachOptimizer: {seqs.count()} sequences found")

    if seqs.count() < 10:
        print("  Not enough data")
        return {"error": "insufficient_data"}

    intent_map = {"hot": 0.9, "warm": 0.6, "cold": 0.3}
    X_list = []
    y_list = []

    for seq in seqs:
        try:
            match = getattr(seq, "match", None)
            lead = getattr(match, "lead", None) if match else None
            intent = 0.5
            if lead and hasattr(lead, "intent"):
                intent = intent_map.get(str(lead.intent or "warm").lower(), 0.5)

            step = int(getattr(seq, "step_number", getattr(seq, "step", 1)) or 1)
            replied = 1 if getattr(seq, "replied_at", None) else 0

            features = [
                0.5,                           # lead_score placeholder
                min(step * 3, 30) / 30,        # days_since_contact proxy
                min(step, 7) / 7,              # total_touches
                0.0,                           # last_reply_sentiment
                0.4,                           # hour_of_day
                0.4,                           # day_of_week
                intent,                        # industry_match proxy
                min(step * 0.15, 0.8),         # deal_stage
            ]
            X_list.append(features)
            y_list.append(replied)
        except Exception:
            continue

    X = np.array(X_list)
    y = np.array(y_list)
    reply_rate = y.mean() * 100
    print(f"  {len(X)} valid samples, reply rate: {reply_rate:.1f}%")

    if len(X) >= 10:
        toolkit = get_toolkit()
        metrics = toolkit.outreach_optimizer.train(X, y)
        print(f"  Trained: {json.dumps(metrics, default=str)}")
        return metrics
    return {"error": "insufficient_valid_data"}


if __name__ == "__main__":
    print("=== Training ML Models from Django Data ===\n")
    train_lead_scorer()
    print()
    train_outreach_optimizer()

    print("\n=== Final Model Status ===")
    toolkit = get_toolkit()
    for name, s in toolkit.get_all_status().items():
        t = "TRAINED" if s["is_trained"] else "pending"
        print(f"  {name}: {t}")
